// Development-only integration test. Run Automation RunTests Khazan.Guard.PIE on DevMap,
// then start PIE once the worker reports it is waiting (Automation closes the previous PIE).
// Calls native gameplay entry points; this does not verify physical keyboard/gamepad input or visual quality.
#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/KZActionAbility.h"
#include "Ability/PlayerAbility/KZGuardAbility.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNodeBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZPlayer.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "EnhancedInputComponent.h"
#include "InputAction.h"
#include "Data/KZInputData.h"
#include "System/KZAssetManager.h"
#include "GameFramework/Controller.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KZGameplayTags.h"
#include "UObject/UnrealType.h"

namespace
{
// Geometric test cases in actor-local degrees, not gameplay thresholds.
const float GuardTestAngles[] = {0.f, 45.f, 90.f, 135.f, 180.f, -135.f, -90.f, -45.f, 179.f, -179.f, 90.f, -90.f};
const TCHAR* GuardTestDirections[] = {TEXT("F"), TEXT("RF"), TEXT("R"), TEXT("RB"), TEXT("B"), TEXT("LB"), TEXT("L"), TEXT("LF"), TEXT("B"), TEXT("B"), TEXT("R"), TEXT("L")};

class FGuardPIECommand : public IAutomationLatentCommand
{
public:
	FGuardPIECommand(FAutomationTestBase* InTest, AKZPlayer* InPlayer)
		: Test(InTest), Player(InPlayer), ASC(Cast<UKZAbilitySystemComponent>(InPlayer->GetAbilitySystemComponent()))
	{
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		{
			if (Cast<UKZGuardAbility>(Spec.Ability))
			{
				GuardHandle = Spec.Handle;
			}
		}
		SavedStamina = ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
		SavedRotation = Player->GetActorRotation();
		SavedControlRotation = Player->GetController()->GetControlRotation();
		Deadline = FPlatformTime::Seconds() + 30.0; // Test watchdog, not gameplay tuning.
	}

	virtual bool Update() override
	{
		if (!Player.IsValid() || !ASC.IsValid() || FPlatformTime::Seconds() > Deadline)
		{
			Test->AddError(TEXT("Guard PIE world expired or did not advance."));
			Cleanup();
			return true;
		}
		const double Now = Player->GetWorld()->GetTimeSeconds();
		if (bDispatchHeldGuard)
		{
			bObservedPrecedingWindow |= PrecedingAction.IsValid() && (!PrecedingAction->IsActive() || PrecedingAction->HasInputEnded());
			if (!DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered))
			{
				Test->AddError(TEXT("Guard has no native Controller Triggered binding."));
				Cleanup();
				return true;
			}
		}
		if (Now < NextTime)
		{
			return false;
		}
		auto Check = [this](const TCHAR* Label, bool Value) { Test->TestTrue(Label, Value); };
		UAnimInstance* Anim = Player->GetMesh()->GetAnimInstance();
		switch (Stage++)
		{
		case 0:
			if (!GuardHandle.IsValid())
			{
				Test->AddError(TEXT("Player has no granted Guard Ability."));
				return true;
			}
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));
			Baseline = ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
			Player->HandleInputMoveReleased();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			Guard = Cast<UKZGuardAbility>(ASC->FindAbilitySpecFromHandle(GuardHandle)->GetPrimaryInstance());
			Check(TEXT("Press activates Guard and state tag"), Guard.IsValid() && Guard->IsActive() && Guarding());
			if (!Guard.IsValid() || !Guard->IsActive())
			{
				Cleanup();
				return true;
			}
			Check(TEXT("Activation is free"), ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) == Baseline);
			TestGuardMontage = Guard->GetCurrentMontage();
			Check(TEXT("Start blocks actions before InputEnd"), Guard.IsValid() && !Guard->HasInputEnded());
			Check(TEXT("Guard caps gait at Walk"), Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == EKZGait::Walk);
			Check(TEXT("Invalid/too expensive hits are rejected"), !ASC->TryGuardHit(0.f) && !ASC->TryGuardHit(-1.f) && !ASC->TryGuardHit(Baseline * 2.f));
			NextTime = Now + 0.5;
			break;
		case 1:
			Check(TEXT("Held Guard survives Start completion"), Guard.IsValid() && Guard->IsActive() && Guarding() && Guard->HasInputEnded());
			Check(TEXT("Holding Guard is free"), ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) == Baseline);
			Check(TEXT("Anim snapshot sees Guard"), AnimBool(TEXT("bIsGuarding")));
			{
				FKZMovementConstraint Constraint;
				Constraint.bOverrideRotationMode = true;
				Constraint.RotationModeOverride = EKZRotationMode::LockOn;
				Constraint.RotationModeOverridePriority = 1;
				Constraint.DebugName = TEXT("GuardPIETest");
				RotationHandle = Player->GetLocomotionComponent()->AcquireMovementConstraint(Guard.Get(), Constraint);
			}
			DirectionIndex = 0;
			SetDirection();
			NextTime = Now + 0.25; // Observer margin beyond the existing 0.1s pose transition.
			break;
		case 2:
			Check(TEXT("LockOn Guard direction uses current movement input"), FMath::Abs(FMath::FindDeltaAngleDegrees(AnimFloat(TEXT("GuardMovementDirectionAngle")), GuardTestAngles[DirectionIndex])) < 1.f);
			CheckGuardMotion(GuardTestDirections[DirectionIndex], DirectionIndex == 8 || DirectionIndex == 9 ? 44.f / 45.f : 1.f);
			if (++DirectionIndex < UE_ARRAY_COUNT(GuardTestAngles))
			{
				--Stage;
				SetDirection();
			}
			else
			{
				Player->GetLocomotionComponent()->ReleaseMovementConstraint(RotationHandle);
				Player->HandleInputMove(FVector2D(0.f, -1.f), FRotator::ZeroRotator);
			}
			NextTime = Now + 0.25;
			break;
		case 3:
			Check(TEXT("Non-LockOn Guard selects F"), AnimFloat(TEXT("GuardMovementDirectionAngle")) == 0.f);
			CheckGuardMotion(TEXT("F"));
			Player->HandleInputMoveReleased();
			NextTime = Now + 0.25;
			break;
		case 4:
			CheckGuardMotion(nullptr);
			{
				// Variable attack-owned test cost: no fixed gameplay Guard cost is introduced.
				const float HitCost = Baseline / 16.f;
				for (int32 Hit = 0; Hit < 3; ++Hit)
				{
					const float Before = ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
					Check(TEXT("Held Guard accepts a hit including repeated success reaction"), ASC->TryGuardHit(HitCost));
					Check(TEXT("Success deducts exactly attack-provided stamina damage"), FMath::IsNearlyEqual(ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()), Before - HitCost));
					const FName Section = Guard->GetCurrentActorInfo()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage());
					Check(TEXT("Success selects F/L/R"), Section == TEXT("Suc_F") || Section == TEXT("Suc_L") || Section == TEXT("Suc_R"));
					Test->AddInfo(FString::Printf(TEXT("Success section: %s"), *Section.ToString()));
				}
			}
			Check(TEXT("Success blocks stamina regeneration temporarily"), ASC->HasMatchingGameplayTag(KZGameplayTags::Delay_StaminaRegen));
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Release immediately removes defense"), !Guarding() && !ASC->TryGuardHit(1.f));
			NextTime = Now + 0.8;
			break;
		case 5:
			Check(TEXT("Release during success advances to End with early InputEnd"), Guard->IsActive() && Guard->HasInputEnded() && Guard->GetCurrentActorInfo()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage()) == TEXT("End"));
			Check(TEXT("Release clears guard pose and Walk limit"), !AnimBool(TEXT("bIsGuarding")) && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait != EKZGait::Walk);
			Player->HandleInputMove(FVector2D(1.f,0.f), Player->GetController()->GetControlRotation());
			ASC->HandleGameplayEvent(KZGameplayTags::Input_Action_Move, &MovePayload);
			Check(TEXT("Movement cancels End recovery after InputEnd"), !Guard->IsActive());
			Player->HandleInputMoveReleased();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			NextTime = Now + 0.5;
			break;
		case 6:
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_X);
			Check(TEXT("Attack can replace held Guard after InputEnd"), !Guard->IsActive() && !Guarding());
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_X);
			CancelActions();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Tap immediately clears defense"), !Guarding());
			NextTime = Now + 0.6;
			break;
		case 7:
			Check(TEXT("Tap queues End at Start InputEnd"), Guard->IsActive() && Guard->HasInputEnded() && Guard->GetCurrentActorInfo()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage()) == TEXT("End"));
			CancelActions();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			ASC->AbilityInputTagCanceled(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Input Cancel cleans Guard without End"), !Guard->IsActive() && !Guarding());
			NextTime = Now + 0.6;
			break;
		case 8:
			Check(TEXT("Late callbacks do not restore state; delay expires"), !Guarding() && !ASC->HasMatchingGameplayTag(KZGameplayTags::Delay_StaminaRegen));
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			NextTime = Now + 0.5;
			break;
		case 9:
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			NextTime = Now + 2.85; // Authored End duration 2.6s plus blend/observer margin; test only.
			break;
		case 10:
			Check(TEXT("End naturally completes without movement"), !Guard->IsActive() && !Guarding());
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Guard reactivates after natural End"), Guard->IsActive() && Guarding());
			{
				AController* Controller = Player->GetController();
				Controller->UnPossess();
				Check(TEXT("UnPossess cancels Guard and clears its movement handle"), !Guard->IsActive() && !Guarding() && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait != EKZGait::Walk);
				Controller->Possess(Player.Get());
			}
			NextTime = Now + 0.25;
			break;
		case 11:
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Player->HandleInputMove(FVector2D(1.f, 0.f), Player->GetController()->GetControlRotation());
			Baseline = ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Moving press skips Start and opens action window"), Guard->IsActive() && Guarding() && Guard->HasInputEnded() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			Check(TEXT("Moving press preserves free Guard and Walk limit"), ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) == Baseline && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == EKZGait::Walk);
			DirectionIndex = 0;
			Test->AddInfo(TEXT("GuardMovementPolicy: moving press -> held Guard, no Start montage."));
			NextTime = Now + 0.25;
			break;
		case 12:
			CheckGuardMotion(TEXT("F"));
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Moving release skips End and clears own handles immediately"), !Guard->IsActive() && !Guarding() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()) && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait != EKZGait::Walk);
			NextTime = Now + 0.25;
			break;
		case 13:
			{
				// Normal Walk/Run/Sprint players belong to the existing Locomotion Sync Group.
				Anim->GetUngroupedActivePlayersRead(); // Wait for parallel animation work before reading both lists.
				const FAnimGroupInstance* Group = Anim->GetSyncGroupMapRead().Find(TEXT("Locomotion"));
				const FAnimTickRecord* Base = Group ? Group->ActivePlayers.FindByPredicate([](const FAnimTickRecord& Record)
				{
					return Record.SourceAsset && !Record.SourceAsset->GetName().Contains(TEXT("Guard")) && Record.EffectiveBlendWeight > 0.99f;
				}) : nullptr;
				Check(TEXT("Moving release reaches actual base locomotion output"), !AnimBool(TEXT("bIsGuarding")) && Base);
				if (Base) Test->AddInfo(FString::Printf(TEXT("GuardMovementPolicy BaseOutput: group=Locomotion clip=%s nodeWeight=%.6f"), *GetNameSafe(Base->SourceAsset), Base->EffectiveBlendWeight));
			}
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Moving tap plays neither Start nor End"), !Guard->IsActive() && !Guarding() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			Player->HandleInputMoveReleased();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Stationary press still starts Start before InputEnd"), Guard->IsActive() && !Guard->HasInputEnded() && Anim->Montage_GetCurrentSection(TestGuardMontage.Get()) == TEXT("Start"));
			Player->HandleInputMove(FVector2D(1.f, 0.f), Player->GetController()->GetControlRotation());
			ASC->HandleGameplayEvent(KZGameplayTags::Input_Action_Move, &MovePayload);
			Check(TEXT("Movement before Start InputEnd stops montage but preserves held Guard"), Guard->IsActive() && Guarding() && Guard->HasInputEnded() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			Test->AddInfo(TEXT("GuardMovementPolicy: moving release -> base output; moving tap skips both; early Start movement preserves Guard."));
			NextTime = Now + 0.25;
			break;
		case 14:
			CheckGuardMotion(TEXT("F"));
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Player->HandleInputMoveReleased();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			NextTime = Now + 0.5;
			break;
		case 15:
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Stationary release still plays End before InputEnd"), Guard->IsActive() && !Guard->HasInputEnded() && Anim->Montage_GetCurrentSection(TestGuardMontage.Get()) == TEXT("End"));
			Player->HandleInputMove(FVector2D(1.f, 0.f), Player->GetController()->GetControlRotation());
			ASC->HandleGameplayEvent(KZGameplayTags::Input_Action_Move, &MovePayload);
			Check(TEXT("Movement before End InputEnd finishes immediately"), !Guard->IsActive() && !Guarding() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			Test->AddInfo(TEXT("GuardMovementPolicy: stationary End interrupted by movement before InputEnd."));
			NextTime = Now + 0.25;
			break;
		case 16:
			Check(TEXT("Stopped End callbacks cannot restore Guard"), !Guard->IsActive() && !Guarding());
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			{
				const float Before = ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
				const float HitCost = Baseline / 16.f;
				Check(TEXT("Moving held Guard still accepts success reaction"), ASC->TryGuardHit(HitCost));
				Check(TEXT("Moving success preserves attack-owned cost"), FMath::IsNearlyEqual(ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()), Before - HitCost));
			}
			ASC->HandleGameplayEvent(KZGameplayTags::Input_Action_Move, &MovePayload);
			Check(TEXT("Held movement does not skip success reaction"), Guard->IsActive() && Guarding() && Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()) && Anim->Montage_GetCurrentSection(TestGuardMontage.Get()).ToString().StartsWith(TEXT("Suc_")));
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Moving release during success skips End without restoring defense"), !Guard->IsActive() && !Guarding() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			Test->AddInfo(TEXT("GuardMovementPolicy: held Suc survives movement; moving release exits without End."));
			NextTime = Now + 0.6;
			break;
		case 17:
			Check(TEXT("Success callbacks and regen delay clean up after moving release"), !Guard->IsActive() && !Guarding() && !ASC->HasMatchingGameplayTag(KZGameplayTags::Delay_StaminaRegen));
			Player->HandleInputMoveReleased();
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
			Check(TEXT("Stationary tap still waits at Start"), Guard->IsActive() && !Guard->HasInputEnded());
			Player->HandleInputMove(FVector2D(1.f, 0.f), Player->GetController()->GetControlRotation());
			ASC->HandleGameplayEvent(KZGameplayTags::Input_Action_Move, &MovePayload);
			Check(TEXT("Movement after early stationary release skips queued End"), !Guard->IsActive() && !Guarding() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			NextTime = Now + 0.25;
			break;
		case 18:
			Check(TEXT("Skipped sections leave no late state or Guard movement limit"), !Guard->IsActive() && !Guarding() && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait != EKZGait::Walk);
			Test->AddInfo(TEXT("GuardMovementPolicy: all movement transitions and late-callback cleanup checked."));
			Player->HandleInputMoveReleased();
			NextTime = Now + 0.25;
			break;
		case 19:
			if (!BeginPrecedingAction(KZGameplayTags::Input_Action_X)) { Cleanup(); return true; }
			bDispatchHeldGuard = true;
			Check(TEXT("Controller dispatches held Guard while another action blocks it"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered) && !Guard->IsActive() && !Guarding() && PrecedingAction->IsActive());
			break;
		case 20:
			if (!Guard->IsActive()) { --Stage; break; }
			Check(TEXT("Held Guard automatically activates when WeakAttack permits transition"), Guarding() && bObservedPrecedingWindow && !PrecedingAction->IsActive() && ASC->FindAbilitySpecFromHandle(GuardHandle)->InputPressed);
			Test->AddInfo(TEXT("GuardHeldInput: Controller Triggered retries after WeakAttack window, without a second press."));
			NextTime = Now + 0.5;
			break;
		case 21:
			Check(TEXT("Continuous Triggered does not restart held Guard after InputEnd"), Guard->IsActive() && Guarding() && Guard->HasInputEnded() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			if (!BeginPrecedingAction(KZGameplayTags::Input_Action_X)) { Cleanup(); return true; }
			Check(TEXT("Attack can replace held Guard and block its immediate return"), !Guard->IsActive() && !Guarding() && DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered) && !Guard->IsActive());
			break;
		case 22:
			if (!Guard->IsActive()) { --Stage; break; }
			Check(TEXT("Same held input restores Guard after an intervening attack"), Guarding() && bObservedPrecedingWindow && !PrecedingAction->IsActive());
			NextTime = Now + 0.5;
			break;
		case 23:
			bDispatchHeldGuard = false;
			Check(TEXT("Controller Completed releases Guard"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Completed) && !Guarding());
			CancelActions();
			if (!BeginPrecedingAction(KZGameplayTags::Input_Action_X)) { Cleanup(); return true; }
			Check(TEXT("Guard remains blocked before early release"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered) && !Guard->IsActive());
			Check(TEXT("Controller receives release before recovery window"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Completed));
			break;
		case 24:
			if (PrecedingAction->IsActive() && !PrecedingAction->HasInputEnded()) { --Stage; break; }
			Check(TEXT("Released input does not activate Guard later"), !Guard->IsActive() && !Guarding() && !ASC->FindAbilitySpecFromHandle(GuardHandle)->InputPressed);
			CancelActions();
			if (!BeginPrecedingAction(KZGameplayTags::Input_Action_X)) { Cleanup(); return true; }
			Check(TEXT("Guard remains blocked before early cancel"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered) && !Guard->IsActive());
			Check(TEXT("Controller receives cancel before recovery window"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Canceled));
			break;
		case 25:
			if (PrecedingAction->IsActive() && !PrecedingAction->HasInputEnded()) { --Stage; break; }
			Check(TEXT("Canceled input does not activate Guard later"), !Guard->IsActive() && !Guarding() && !ASC->FindAbilitySpecFromHandle(GuardHandle)->InputPressed);
			CancelActions();
			if (!BeginPrecedingAction(KZGameplayTags::Input_Action_A)) { Cleanup(); return true; }
			bDispatchHeldGuard = true;
			Check(TEXT("Controller cannot activate Guard before Dodge window"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered) && !Guard->IsActive());
			Test->AddInfo(TEXT("GuardHeldInput: intervening attack return, early release and early cancel checked."));
			break;
		case 26:
			if (!Guard->IsActive()) { --Stage; break; }
			Check(TEXT("Held Guard automatically activates after Dodge permits transition"), Guarding() && bObservedPrecedingWindow && !PrecedingAction->IsActive());
			NextTime = Now + 0.5;
			break;
		case 27:
			Check(TEXT("Held Guard after Dodge settles without repeated Start"), Guard->IsActive() && Guarding() && Guard->HasInputEnded() && !Anim->GetActiveInstanceForMontage(TestGuardMontage.Get()));
			bDispatchHeldGuard = false;
			Check(TEXT("Controller Canceled clears active held Guard"), DispatchInput(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Canceled) && !Guard->IsActive() && !Guarding());
			Test->AddInfo(TEXT("GuardHeldInput: native Controller callback hold/retry/no-restart and cleanup checked."));
			Cleanup();
			return true;
		}
		return false;
	}

private:
	bool DispatchInput(const FGameplayTag& InputTag, ETriggerEvent Event)
	{
		const UKZInputData* Data = UKZAssetManager::GetAssetByName<UKZInputData>(KZGameplayTags::AssetData_InputData);
		const UInputAction* Action = Data ? Data->FindInputActionByTag(InputTag) : nullptr;
		const UEnhancedInputComponent* Input = Player->GetController() ? Cast<UEnhancedInputComponent>(Player->GetController()->InputComponent) : nullptr;
		if (!Action || !Input) return false;
		for (const TUniquePtr<FEnhancedInputActionEventBinding>& Binding : Input->GetActionEventBindings())
		{
			if (Binding->GetAction() == Action && Binding->GetTriggerEvent() == Event)
			{
				// Invoke the real bound private Controller callback through the public engine binding API.
				Binding->Execute(FInputActionInstance(Action));
				return true;
			}
		}
		return false;
	}
	bool BeginPrecedingAction(const FGameplayTag& InputTag)
	{
		PrecedingAction.Reset();
		bObservedPrecedingWindow = false;
		if (!DispatchInput(InputTag, ETriggerEvent::Started) || !DispatchInput(InputTag, ETriggerEvent::Completed)) return Test->TestTrue(TEXT("Preceding action Controller bindings exist"), false);
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		{
			if (Spec.IsActive() && Spec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
			{
				PrecedingAction = Cast<UKZActionAbility>(Spec.GetPrimaryInstance());
				break;
			}
		}
		return Test->TestTrue(TEXT("Preceding action starts before its InputEnd"), PrecedingAction.IsValid() && !PrecedingAction->HasInputEnded());
	}
	bool Guarding() const { return ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding); }
	bool AnimBool(FName Name) const { const UAnimInstance* Anim = Player->GetMesh()->GetAnimInstance(); const FBoolProperty* P = FindFProperty<FBoolProperty>(Anim->GetClass(),Name); return P && P->GetPropertyValue_InContainer(Anim); }
	float AnimFloat(FName Name) const { const UAnimInstance* Anim = Player->GetMesh()->GetAnimInstance(); const FFloatProperty* P = FindFProperty<FFloatProperty>(Anim->GetClass(),Name); return P ? P->GetPropertyValue_InContainer(Anim) : MAX_flt; }
	void SetDirection()
	{
		const FRotator ActorYaw(0.f, DirectionIndex == 11 ? 90.f : 0.f, 0.f);
		const FRotator CameraYaw(0.f, DirectionIndex == 10 ? 90.f : 0.f, 0.f);
		const float InputAngle = FMath::DegreesToRadians(DirectionIndex >= 10 ? 0.f : GuardTestAngles[DirectionIndex]);
		Player->SetActorRotation(ActorYaw);
		// Hold the fixture actor's facing while input is converted using the specified camera yaw.
		Player->GetController()->SetControlRotation(ActorYaw);
		Player->HandleInputMove(FVector2D(FMath::Cos(InputAngle), FMath::Sin(InputAngle)), CameraYaw);
	}
	void CheckGuardMotion(const TCHAR* Direction, float ExpectedWeight = 1.f)
	{
		USkeletalMeshComponent* Mesh = Player->GetMesh();
		UAnimInstance* Anim = Mesh->GetAnimInstance();
		// Public read accessor waits for parallel animation work. The tick record points to the
		// real playing node's sample cache; this does not independently calculate BS weights.
		const TArray<FAnimTickRecord>& Records = Anim->GetUngroupedActivePlayersRead();
		const FString ExpectedName = Direction ? FString::Printf(TEXT("Player_Guard_Wark_%s"), Direction) : TEXT("Player_Guard_Loop");
		const FString Label = FString::Printf(TEXT("Guard motion %s (case %d)"), *ExpectedName, DirectionIndex);
		const FAnimTickRecord* Active = Records.FindByPredicate([Direction](const FAnimTickRecord& Record)
		{
			return Record.SourceAsset && Record.SourceAsset->GetName() == (Direction ? TEXT("BS_DAS_Player_Guard") : TEXT("Player_Guard_Loop"));
		});
		if (!Test->TestNotNull(*Label, Active)) return;
		Test->TestTrue(*(Label + TEXT(" contributes to output")), Active->EffectiveBlendWeight > 0.99f && Active->bLooping);
		UAnimSequence* Sequence = nullptr;
		float SampleTime = 0.f;
		if (Direction)
		{
			const TArray<FBlendSampleData>* Samples = Active->BlendSpace.BlendSampleDataCache;
			if (!Test->TestNotNull(*(Label + TEXT(" sample cache")), Samples)) return;
			float SelectedWeight = 0.f, TotalWeight = 0.f;
			for (const FBlendSampleData& Sample : *Samples)
			{
				TotalWeight += Sample.TotalWeight;
				Test->AddInfo(FString::Printf(TEXT("GuardSample case=%d input=%.3f nodeWeight=%.6f clip=%s weight=%.6f time=%.6f previous=%.6f"),
					DirectionIndex, Active->BlendSpace.BlendSpacePositionX, Active->EffectiveBlendWeight, *GetNameSafe(Sample.Animation), Sample.TotalWeight, Sample.Time, Sample.PreviousTime));
				if (Sample.Animation && Sample.Animation->GetName() == ExpectedName)
				{
					SelectedWeight += Sample.TotalWeight;
					Sequence = Sample.Animation;
					SampleTime = Sample.Time;
					Test->TestTrue(*(Label + TEXT(" playback advances")), Sample.DeltaTimeRecord.Delta > 0.f && Sample.Time != Sample.DeltaTimeRecord.GetPrevious());
				}
			}
			// Numerical comparison tolerances only; these do not tune gameplay/animation assets.
			Test->TestTrue(*(Label + TEXT(" actual clip weight")), FMath::IsNearlyEqual(SelectedWeight, ExpectedWeight, 0.001f));
			Test->TestTrue(*(Label + TEXT(" normalized weights")), FMath::IsNearlyEqual(TotalWeight, 1.f, 0.001f));
		}
		else
		{
			Sequence = Cast<UAnimSequence>(Active->SourceAsset);
			SampleTime = Active->TimeAccumulator ? *Active->TimeAccumulator : 0.f;
		}
		if (!Test->TestNotNull(*(Label + TEXT(" playing sequence")), Sequence)) return;
		if (ExpectedWeight != 1.f) return; // Seam cases intentionally blend two different clips.

		// Compare the evaluated mesh to this compressed sequence at the node's actual time,
		// with the same required bones/retargeting/root-lock policy. No actor/mesh scale changes.
		FMemMark Mark(FMemStack::Get());
		FPoseContext Expected(Anim->GetRequiredBones());
		Expected.ResetToRefPose();
		FAnimationPoseData PoseData(Expected);
		Sequence->GetAnimationPose(PoseData, FAnimExtractContext(SampleTime, false));
		const TArray<FTransform> Actual = Mesh->GetBoneSpaceTransforms();
		double MaxPositionError = 0.0, MaxAngleError = 0.0, MaxScaleError = 0.0;
		for (const FCompactPoseBoneIndex Bone : Expected.Pose.ForEachBoneIndex())
		{
			const int32 MeshIndex = Expected.Pose.GetBoneContainer().MakeMeshPoseIndex(Bone).GetInt();
			if (!Actual.IsValidIndex(MeshIndex)) { Test->AddError(Label + TEXT(" missing mesh bone")); return; }
			MaxPositionError = FMath::Max(MaxPositionError, FVector::Distance(Actual[MeshIndex].GetTranslation(), Expected.Pose[Bone].GetTranslation()));
			// AngularDistance assumes unit quaternions; float pose storage can introduce length error.
			MaxAngleError = FMath::Max(MaxAngleError, FMath::RadiansToDegrees(Actual[MeshIndex].GetRotation().GetNormalized().AngularDistance(Expected.Pose[Bone].GetRotation().GetNormalized())));
			MaxScaleError = FMath::Max(MaxScaleError, FVector::Distance(Actual[MeshIndex].GetScale3D(), Expected.Pose[Bone].GetScale3D()));
		}
		Test->AddInfo(FString::Printf(TEXT("GuardPose clip=%s time=%.6f bones=%d maxLocalPosition=%.9f maxAngleDegrees=%.9f maxScale=%.9f"),
			*ExpectedName, SampleTime, Expected.Pose.GetNumBones(), MaxPositionError, MaxAngleError, MaxScaleError));
		Test->TestTrue(*(Label + TEXT(" evaluated mesh matches playing clip")), MaxPositionError < 0.01 && MaxAngleError < 0.02 && MaxScaleError < 0.0001);
	}
	void CancelActions() { FGameplayTagContainer Tags(KZGameplayTags::Ability_Action); ASC->CancelAbilities(&Tags); ASC->ClearComboCommands(); }
	void Cleanup()
	{
		bDispatchHeldGuard = false;
		if (ASC.IsValid()) { CancelActions(); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),SavedStamina); }
		if (Player.IsValid()) { Player->HandleInputMoveReleased(); Player->GetLocomotionComponent()->ReleaseMovementConstraint(RotationHandle); Player->SetActorRotation(SavedRotation); if (Player->GetController()) Player->GetController()->SetControlRotation(SavedControlRotation); }
	}
	FAutomationTestBase* Test;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<UKZAbilitySystemComponent> ASC;
	TWeakObjectPtr<UKZGuardAbility> Guard;
	TWeakObjectPtr<UKZActionAbility> PrecedingAction;
	TWeakObjectPtr<UAnimMontage> TestGuardMontage;
	FGameplayAbilitySpecHandle GuardHandle;
	FKZMovementConstraintHandle RotationHandle;
	FGameplayEventData MovePayload;
	FRotator SavedRotation, SavedControlRotation;
	float SavedStamina = 0.f, Baseline = 0.f;
	double Deadline = 0.0, NextTime = 0.0;
	int32 Stage = 0, DirectionIndex = 0;
	bool bDispatchHeldGuard = false, bObservedPrecedingWindow = false;
};

class FWaitForGuardPIE : public IAutomationLatentCommand
{
public:
	explicit FWaitForGuardPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 30.0) {}
	virtual bool Update() override
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			if (Context.WorldType != EWorldType::PIE || !Context.World() || !Context.World()->HasBegunPlay()) continue;
			for (TActorIterator<AKZPlayer> It(Context.World()); It; ++It)
			{
				if (It->IsPlayerControlled() && It->GetCharacterMovement()->IsMovingOnGround() &&
					It->GetAbilitySystemComponent() && It->GetMesh()->GetAnimInstance())
				{
					FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FGuardPIECommand>(Test,*It));
					return true;
				}
			}
		}
		if (FPlatformTime::Seconds() > Deadline)
		{
			Test->AddError(TEXT("Guard test waiting for PIE timed out. Start PIE on DevMap after Test Started."));
			return true;
		}
		return false;
	}
private:
	FAutomationTestBase* Test;
	double Deadline;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGuardPIETest, "Khazan.Guard.PIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZGuardPIETest::RunTest(const FString& Parameters)
{
	// DevMap now contains configured AI monsters; missing Definition errors are regressions.
	AddInfo(TEXT("Guard test waiting for PIE: start PIE now on DevMap."));
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForGuardPIE>(this));
	return true;
}

#endif
