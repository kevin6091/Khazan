// Development integration test; actual Controller callbacks and CMC/mesh evaluation.
// Run Khazan.Heal.PIE on DevMap. Hardware DPad events are a separate QA step.
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/PlayerAbility/KZHealAbility.h"
#include "Ability/PlayerAbility/KZStrongAttackAbility.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZPlayer.h"
#include "Data/KZInputData.h"
#include "System/KZAssetManager.h"
#include "KZGameplayTags.h"
#include "EnhancedInputComponent.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputCoreTypes.h"
#include "GameplayEffect.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleSystem.h"
#include "ParticleEmitterInstances.h"
#include "UObject/UObjectIterator.h"
#include "Misc/FileHelper.h"

namespace
{
class FHealPIECommand : public IAutomationLatentCommand
{
public:
	FHealPIECommand(FAutomationTestBase* InTest, AKZPlayer* InPlayer)
		: Test(InTest), Player(InPlayer), ASC(Cast<UKZAbilitySystemComponent>(InPlayer->GetAbilitySystemComponent())),
		  SavedLocation(InPlayer->GetActorLocation()), SavedRotation(InPlayer->GetActorRotation()),
		  Deadline(FPlatformTime::Seconds() + 60.0)
	{
		SavedHP = ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
		SavedMax = ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute());
		SavedStamina = ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
		SavedGait = Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait;
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
			if (Cast<UKZHealAbility>(Spec.Ability)) HealHandle = Spec.Handle;
		for (USceneComponent* Child : InPlayer->GetMesh()->GetAttachChildren())
			if (Child && (Child->GetAttachSocketName() == TEXT("Weapon_L") || Child->GetAttachSocketName() == TEXT("Weapon_R")))
				Weapons.Add({Child, Child->GetAttachSocketName(), Child->GetRelativeTransform()});
		VFXOutput = FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_HEAL_VFX_OUT"));
		if (!VFXOutput.IsEmpty())
		{
			if (APlayerController* PC = InPlayer->GetController<APlayerController>())
			{
				OldView = PC->GetViewTarget();
				FActorSpawnParameters Params; Params.ObjectFlags |= RF_Transient;
				VFXCamera = InPlayer->GetWorld()->SpawnActor<ACameraActor>(Params);
				VFXCamera->GetCameraComponent()->SetFieldOfView(45.f);
				PC->SetViewTarget(VFXCamera.Get());
			}
		}
	}
	virtual bool Update() override
	{
		if (!Player.IsValid() || !ASC.IsValid() || FPlatformTime::Seconds() > Deadline)
		{
			Test->AddError(TEXT("Heal PIE expired or did not advance."));
			Cleanup();
			return true;
		}
		if (bMove) Player->HandleInputMove(FVector2D(0.5f, 0.f), FRotator::ZeroRotator);
		ObserveRecoveryVFX();
		if (Stage == 4 && !bDrawCaptured && Heal.IsValid() && Heal->HasInputEnded())
		{
			const FAnimMontageInstance* Draw = Player->GetMesh()->GetAnimInstance()->GetActiveInstanceForMontage(Heal->GetCurrentMontage());
			if (Draw && Draw->GetPosition() > 0.6f)
			{
				FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("HealWeapon_Draw.png"), false, false);
				bDrawCaptured = true;
			}
		}
		const double Now = Player->GetWorld()->GetTimeSeconds();
		if (Now < NextTime) return false;
		// A coarse editor frame can defer montage completion past the nominal observer time.
		// Dispatch draw-cancellation fixtures only after the real Heal -> Draw handoff.
		if ((Stage == 9 || Stage == 11 || Stage == 13 || Stage == 15) &&
			Heal.IsValid() && Heal->IsActive() && !Heal->HasInputEnded()) return false;
		switch (Stage++)
		{
		case 0:
			if (!Test->TestTrue(TEXT("Heal granted"), HealHandle.IsValid())) { Cleanup(); return true; }
			Test->TestEqual(TEXT("Existing two held weapons"), Weapons.Num(), 2);
			Test->TestEqual(TEXT("User initial MaxHP"), SavedMax, 200.f);
			Test->TestEqual(TEXT("User initial HP"), SavedHP, 200.f);
			{
				const UKZInputData* Data = UKZAssetManager::GetAssetByName<UKZInputData>(KZGameplayTags::AssetData_InputData);
				const UInputAction* Action = Data->FindInputActionByTag(KZGameplayTags::Input_Action_Heal);
				int32 DownMappings = 0;
				for (const FEnhancedActionKeyMapping& Mapping : Data->InputMappingContext->GetMappings())
					if (Mapping.Action == Action && Mapping.Key == EKeys::Gamepad_DPad_Down) ++DownMappings;
				Test->TestEqual(TEXT("One DPad Down Heal mapping"), DownMappings, 1);
			}
			HP(50.f);
			bMove = true;
			NextTime = Now + 0.75; // Settle the existing Idle -> Walk transition before comparing clip poses.
			break;
		case 1:
			StartHeal();
			Test->TestEqual(TEXT("No heal on activation"), Health(), 50.f);
			Test->TestTrue(TEXT("Movement stays allowed"), Player->GetLocomotionComponent()->IsMovementInputAllowed() && !ASC->HasMatchingGameplayTag(KZGameplayTags::Block_Movement_Input));
			Test->TestTrue(TEXT("Heal caps gait at Walk"), Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == EKZGait::Walk);
			NextTime = Now + 0.35; // Observer point after blend-in and before the authored Heal notify.
			break;
		case 2:
			Test->TestEqual(TEXT("HP unchanged before sip notify"), Health(), 50.f);
			Test->TestTrue(TEXT("CMC walks while drinking"), Player->GetVelocity().Size2D() > 0.f && FVector::Dist2D(Player->GetActorLocation(), SavedLocation) > 0.f);
			Dispatch(KZGameplayTags::Input_Action_X, ETriggerEvent::Started);
			Dispatch(KZGameplayTags::Input_Action_X, ETriggerEvent::Completed);
			Test->TestTrue(TEXT("Attack is blocked before Heal InputEnd"), Heal.IsValid() && Heal->IsActive());
			NextTime = Now + 1.5; // Stow 1s + sip at Heal local 0.733s.
			break;
		case 3:
			Test->TestEqual(TEXT("Heal notify restores exactly 100"), Health(), 150.f);
			CheckWeapons(true);
			CheckSplitPose(false);
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("HealWeapon_Stowed.png"), false, false);
			{
				UAnimInstance* Anim = Player->GetMesh()->GetAnimInstance();
				const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage.Get());
				if (Test->TestNotNull(TEXT("Heal montage still playing"), Instance))
				{
					FBranchingPointNotifyPayload Payload;
					Payload.SequenceAsset = Montage.Get();
					Payload.MontageInstanceID = Instance->GetInstanceID();
					Anim->OnPlayMontageNotifyBegin.Broadcast(TEXT("Heal"), Payload);
					Anim->OnPlayMontageNotifyBegin.Broadcast(TEXT("Heal"), Payload);
				}
			}
			Test->TestEqual(TEXT("Repeated sip callback cannot heal twice"), Health(), 150.f);
			Test->TestEqual(TEXT("Potion has no stamina cost"), ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()), SavedStamina);
			NextTime = Now + 1.4; // Arms are actually moving after WeaponDraw, before natural completion.
			break;
		case 4:
			Test->TestTrue(TEXT("Heal InputEnd opens action replacement"), Heal.IsValid() && Heal->HasInputEnded());
			Test->TestTrue(TEXT("Armed is the current montage"), Heal->GetCurrentMontage() && Heal->GetCurrentMontage()->GetName() == TEXT("AM_DAS_Player_HealDraw"));
			CheckWeapons(false);
			Montage = Heal->GetCurrentMontage();
			CheckSplitPose(true);
			Test->TestTrue(TEXT("Draw already released Heal Walk cap"), Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == SavedGait);
			bMove = false;
			Player->HandleInputMoveReleased();
			Dispatch(KZGameplayTags::Input_Action_X, ETriggerEvent::Started);
			Dispatch(KZGameplayTags::Input_Action_X, ETriggerEvent::Completed);
			Test->TestTrue(TEXT("Attack replaces Heal after InputEnd"), Heal.IsValid() && !Heal->IsActive());
			CheckWeapons(false);
			Test->TestTrue(TEXT("Replacement releases Walk constraint"), Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == SavedGait);
			CancelActions();
			HP(150.f);
			StartHeal();
			NextTime = Now + 3.8; // Beyond Stow + Heal + Armed and blend-out.
			break;
		case 5:
			Test->TestEqual(TEXT("Recovery is clamped at MaxHP"), Health(), 200.f);
			Test->TestTrue(TEXT("Natural completion ends Heal"), Heal.IsValid() && !Heal->IsActive());
			CheckWeapons(false);
			Test->TestTrue(TEXT("Natural completion releases Walk constraint"), Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == SavedGait);
			Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Started);
			Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Completed);
			Test->TestTrue(TEXT("Unlimited potion can still animate at full HP"), Heal->IsActive());
			Test->TestEqual(TEXT("Full HP stays capped on press"), Health(), 200.f);
			CancelActions();
			HP(50.f);
			// Canceled belongs to an unfinished input hold, never to a completed tap.
			Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Started);
			Test->TestTrue(TEXT("Canceled fixture still owns pressed input"), Heal->IsActive() && ASC->FindAbilitySpecFromHandle(HealHandle)->InputPressed);
			NextTime = Now + 0.2;
			break;
		case 6:
			Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Canceled);
			Test->TestTrue(TEXT("Cancel ends Heal and releases constraint"), !Heal->IsActive() && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == SavedGait);
			CheckWeapons(false);
			NextTime = Now + 1.5;
			break;
		case 7:
			Test->TestEqual(TEXT("Canceled before sip never heals later"), Health(), 50.f);
			StartHeal();
			NextTime = Now + 3.8;
			break;
		case 8:
			Test->TestEqual(TEXT("Unlimited potion can be used again"), Health(), 150.f);
			HP(-100.f);
			Test->TestEqual(TEXT("HP lower bound"), Health(), 0.f);
			Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Started);
			Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Completed);
			Test->TestTrue(TEXT("Heal cannot revive zero HP"), !Heal->IsActive());
			HP(1000.f);
			Test->TestEqual(TEXT("HP upper bound"), Health(), SavedMax);
			{
				UGameplayEffect* Effect = NewObject<UGameplayEffect>();
				FGameplayModifierInfo Modifier;
				Modifier.Attribute = UKZAttributeSet::GetMaxHPAttribute();
				Modifier.ModifierOp = EGameplayModOp::Override;
				Modifier.ModifierMagnitude = FScalableFloat(100.f); // Fixture-only max reduction, not a product tuning change.
				Effect->Modifiers.Add(Modifier);
				ASC->ApplyGameplayEffectToSelf(Effect, 1.f, ASC->MakeEffectContext());
			}
			Test->TestEqual(TEXT("MaxHP effect reduction also clamps HP"), Health(), 100.f);
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), 50.f);
			Test->TestEqual(TEXT("Direct MaxHP change also clamps HP"), Health(), 50.f);
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), SavedMax);
			HP(50.f);
			StartHeal();
			NextTime = Now + 2.7;
			break;
		case 9:
			CaptureDraw();
			Dispatch(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Triggered);
			Test->TestTrue(TEXT("Held Guard immediately replaces Arms draw"), !Heal->IsActive() && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding));
			Test->TestEqual(TEXT("Canceling draw retains the completed HP recovery"), Health(), 150.f);
			CheckWeapons(false);
			NextTime = Now + 0.05;
			break;
		case 10:
			CheckOldDrawStopped();
			Dispatch(KZGameplayTags::Input_Action_Guard, ETriggerEvent::Completed);
			CancelActions(); HP(50.f); StartHeal();
			NextTime = Now + 2.7;
			break;
		case 11:
			CaptureDraw();
			Dispatch(KZGameplayTags::Input_Action_A, ETriggerEvent::Started);
			Dispatch(KZGameplayTags::Input_Action_A, ETriggerEvent::Completed);
			Test->TestTrue(TEXT("Dodge immediately replaces Arms draw"), !Heal->IsActive() && ActiveInput(KZGameplayTags::Input_Action_A));
			CheckWeapons(false);
			NextTime = Now + 0.05;
			break;
		case 12:
			CheckOldDrawStopped();
			CancelActions(); HP(50.f); StartHeal();
			NextTime = Now + 2.7;
			break;
		case 13:
			CaptureDraw();
			Dispatch(KZGameplayTags::Input_Action_Y, ETriggerEvent::Started);
			Test->TestTrue(TEXT("Strong Charge takes over draw on press"), !Heal->IsActive() && ActiveInput(KZGameplayTags::Input_Action_Y));
			Dispatch(KZGameplayTags::Input_Action_Y, ETriggerEvent::Completed);
			{
				bool bStrongActive = false;
				for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
					bStrongActive |= Spec.IsActive() && Cast<UKZStrongAttackAbility>(Spec.GetPrimaryInstance()) != nullptr;
				Test->TestTrue(TEXT("Y release hands off to graph-only Strong Attack"), !Heal->IsActive() && bStrongActive);
			}
			CheckWeapons(false);
			NextTime = Now + 0.05;
			break;
		case 14:
			CheckOldDrawStopped();
			CancelActions(); HP(50.f); StartHeal();
			NextTime = Now + 2.7;
			break;
		case 15:
			CaptureDraw();
			CancelActions(); // Same ASC forced cancellation path for future hit reaction; no enemy damage fixture exists yet.
			Test->TestTrue(TEXT("Forced cancellation releases draw execution"), !Heal->IsActive());
			CheckWeapons(false);
			NextTime = Now + 0.05;
			break;
		case 16:
			CheckOldDrawStopped();
			HP(50.f); StartHeal();
			NextTime = Now + 0.85; // UnPossess with both weapons already stored, before sip.
			break;
		case 17:
			CheckWeapons(true);
			Player->GetController()->UnPossess();
			Test->TestTrue(TEXT("UnPossess cancels Heal and cleans constraint"), !Heal->IsActive() && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == SavedGait);
			CheckWeapons(false);
			NextTime = Now + 1.5;
			break;
		case 18:
			Test->TestEqual(TEXT("UnPossess cannot apply a late sip"), Health(), 50.f);
			Cleanup();
			return true;
		}
		return false;
	}
private:
	bool ActiveInput(FGameplayTag Tag) const
	{
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
			if (Spec.IsActive() && Spec.GetDynamicSpecSourceTags().HasTagExact(Tag)) return true;
		return false;
	}
	void CaptureDraw()
	{
		Test->TestTrue(TEXT("Cancellation fixture reached draw"), Heal.IsValid() && Heal->IsActive() && Heal->HasInputEnded());
		const FAnimMontageInstance* Instance = Player->GetMesh()->GetAnimInstance()->GetActiveInstanceForMontage(Heal->GetCurrentMontage());
		OldDrawId = Instance ? Instance->GetInstanceID() : INDEX_NONE;
		Test->TestTrue(TEXT("Exact draw instance captured"), OldDrawId != INDEX_NONE);
		USkeletalMeshComponent* Mesh = Player->GetMesh();
		for (const FWeapon& Weapon : Weapons)
		{
			const FName Back = Weapon.Socket == TEXT("Weapon_L") ? FName(TEXT("Weapon_L_BackPack소켓")) : FName(TEXT("Weapon_R_BackPack소켓"));
			Test->AddInfo(FString::Printf(TEXT("DrawHandContact: socket=%s time=%.6f handToBackDistanceCm=%.6f"), *Weapon.Socket.ToString(), Instance ? Instance->GetPosition() : -1.f,
				FVector::Distance(Mesh->GetSocketLocation(Weapon.Socket), Mesh->GetSocketLocation(Back))));
		}
	}
	void CheckOldDrawStopped()
	{
		const FAnimMontageInstance* Old = Player->GetMesh()->GetAnimInstance()->GetMontageInstanceForID(OldDrawId);
		Test->TestTrue(TEXT("Canceled Arms montage has zero remaining weight"), !Old || Old->GetWeight() <= ZERO_ANIMWEIGHT_THRESH);
	}
	bool Dispatch(FGameplayTag Tag, ETriggerEvent Event)
	{
		const UKZInputData* Data = UKZAssetManager::GetAssetByName<UKZInputData>(KZGameplayTags::AssetData_InputData);
		const UInputAction* Action = Data->FindInputActionByTag(Tag);
		const UEnhancedInputComponent* Input = Player->GetController() ? Cast<UEnhancedInputComponent>(Player->GetController()->InputComponent) : nullptr;
		if (Input) for (const auto& Binding : Input->GetActionEventBindings())
			if (Binding->GetAction() == Action && Binding->GetTriggerEvent() == Event)
			{
				Binding->Execute(FInputActionInstance(Action));
				return true;
			}
		Test->AddError(TEXT("Expected native Controller input binding missing."));
		return false;
	}
	void StartHeal()
	{
		Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Started);
		Dispatch(KZGameplayTags::Input_Action_Heal, ETriggerEvent::Completed); // Tap release must not cancel drinking.
		Heal = Cast<UKZHealAbility>(ASC->FindAbilitySpecFromHandle(HealHandle)->GetPrimaryInstance());
		Test->TestTrue(TEXT("Controller press starts Heal; release preserves it"), Heal.IsValid() && Heal->IsActive());
		if (Heal.IsValid()) Montage = Heal->GetCurrentMontage();
	}
	float Health() const { return ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()); }
	void HP(float Value) { ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), Value); }
	void CancelActions() { FGameplayTagContainer Tags(KZGameplayTags::Ability_Action); ASC->CancelAbilities(&Tags); ASC->ClearComboCommands(); }
	void CheckWeapons(bool bStored)
	{
		for (const FWeapon& Weapon : Weapons)
		{
			if (!Test->TestTrue(TEXT("Original weapon component lives"), Weapon.Component.IsValid())) continue;
			const USceneComponent* Component = Weapon.Component.Get();
			const FName Expected = bStored ? (Weapon.Socket == TEXT("Weapon_L") ? FName(TEXT("Weapon_L_BackPack소켓")) : FName(TEXT("Weapon_R_BackPack소켓"))) : Weapon.Socket;
			Test->TestTrue(TEXT("Weapon stays visible"), Component->IsVisible());
			Test->TestTrue(TEXT("Weapon is attached to Player mesh"), Component->GetAttachParent() == Player->GetMesh());
			Test->TestEqual(TEXT("Weapon attachment at phase checkpoint"), Component->GetAttachSocketName(), Expected);
			Test->TestTrue(TEXT("Weapon scale survives"), Component->GetRelativeScale3D().Equals(Weapon.Relative.GetScale3D()));
			if (!bStored) Test->TestTrue(TEXT("Original hand offset restored exactly"), Component->GetRelativeTransform().Equals(Weapon.Relative));
		}
	}
	void CheckSplitPose(bool bDrawing)
	{
		USkeletalMeshComponent* Mesh = Player->GetMesh();
		UAnimInstance* Anim = Mesh->GetAnimInstance();
		const FAnimTickRecord* Walking = nullptr;
		for (const auto& Group : Anim->GetSyncGroupMapRead())
			for (const FAnimTickRecord& Record : Group.Value.ActivePlayers)
				if (Record.SourceAsset && Record.SourceAsset->GetName() == TEXT("DAS_Player_Walk_Loop")) Walking = &Record;
		if (!Test->TestNotNull(TEXT("Lower-body walking node continues"), Walking)) return;
		UAnimSequence* Walk = Cast<UAnimSequence>(Walking->SourceAsset);
		const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage.Get());
		UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, bDrawing ? TEXT("/Game/_Art/Player/Animation/InGame/DAS/Equip/CA_P_Kazan_DualAxeSword_Armed") : TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/CA_P_Kazan_DualAxeSword_Heal_01"));
		if (!Test->TestNotNull(TEXT("Upper-body Heal instance"), Instance)) return;
		Test->TestTrue(TEXT("Heal has full montage weight at pose checkpoint"), FMath::IsNearlyEqual(Instance->GetWeight(), 1.f));
		FMemMark Mark(FMemStack::Get());
		FPoseContext WalkPose(Anim->GetRequiredBones()), HealPose(Anim->GetRequiredBones());
		WalkPose.ResetToRefPose(); HealPose.ResetToRefPose();
		FAnimationPoseData WalkData(WalkPose), HealData(HealPose);
		const float WalkTime = Walking->TimeAccumulator ? *Walking->TimeAccumulator : 0.f;
		Walk->GetAnimationPose(WalkData, FAnimExtractContext(WalkTime, false));
		Test->AddInfo(FString::Printf(TEXT("HealBaseWalk: clip=%s effectiveWeight=%.9f delta=%.9f"), *Walk->GetName(), Walking->EffectiveBlendWeight, Walking->DeltaTimeRecord ? Walking->DeltaTimeRecord->Delta : 0.f));
		Test->TestTrue(TEXT("Lower-body Walk has settled full weight"), FMath::IsNearlyEqual(Walking->EffectiveBlendWeight, 1.f));
		Clip->GetAnimationPose(HealData, FAnimExtractContext(Instance->GetPosition() - (bDrawing ? 0.f : 1.f), false));
		const TArray<FTransform> Actual = Mesh->GetBoneSpaceTransforms();
		const TCHAR* Bones[] = {TEXT("bip001-pelvis"), TEXT("bip001-l-thigh"), TEXT("bip001-r-thigh"), TEXT("bip001-l-calf"), TEXT("bip001-r-calf"), TEXT("bip001-l-foot"), TEXT("bip001-r-foot"), TEXT("bip001-l-hand"), TEXT("bip001-r-hand")};
		for (int32 Index = 0; Index < UE_ARRAY_COUNT(Bones); ++Index)
		{
			const int32 MeshIndex = Mesh->GetBoneIndex(Bones[Index]);
			if (!Test->TestTrue(TEXT("Pose checkpoint bone exists"), Actual.IsValidIndex(MeshIndex))) continue;
			const FCompactPoseBoneIndex Compact = WalkPose.Pose.GetBoneContainer().MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
			const FTransform& Expected = Index < 7 ? WalkPose.Pose[Compact] : HealPose.Pose[Compact];
			const double Distance = FVector::Distance(Actual[MeshIndex].GetTranslation(), Expected.GetTranslation());
			const double Angle = FMath::RadiansToDegrees(Actual[MeshIndex].GetRotation().GetNormalized().AngularDistance(Expected.GetRotation().GetNormalized()));
			Test->AddInfo(FString::Printf(TEXT("HealSplitPose: bone=%s source=%s walkTime=%.6f healTime=%.6f localPositionError=%.9f angleDegrees=%.9f"), Bones[Index], Index < 7 ? TEXT("Walk") : (bDrawing ? TEXT("Armed") : TEXT("Heal")), WalkTime, Instance->GetPosition(), Distance, Angle));
			// Numerical test tolerances only; no asset/gameplay numeric changes.
			Test->TestTrue(*(FString(Bones[Index]) + TEXT(" matches its assigned pose source")), Distance < 0.01 && Angle < 0.02);
		}
		if (bDrawing) for (const TCHAR* Bone : {TEXT("bip001-spine"), TEXT("bip001-spine1"), TEXT("bip001-spine2"), TEXT("bip001-neck"), TEXT("bip001-head")})
		{
			const int32 MeshIndex = Mesh->GetBoneIndex(Bone);
			if (!Test->TestTrue(TEXT("Torso pose checkpoint exists"), Actual.IsValidIndex(MeshIndex))) continue;
			const auto Compact = WalkPose.Pose.GetBoneContainer().MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
			const double Angle = FMath::RadiansToDegrees(Actual[MeshIndex].GetRotation().GetNormalized().AngularDistance(WalkPose.Pose[Compact].GetRotation().GetNormalized()));
			Test->AddInfo(FString::Printf(TEXT("DrawTorsoPose: bone=%s angleDegrees=%.9f"), Bone, Angle));
			Test->TestTrue(*(FString(Bone) + TEXT(" remains locomotion during Arms draw")), Actual[MeshIndex].GetTranslation().Equals(WalkPose.Pose[Compact].GetTranslation(), 0.01) && Angle < 0.02);
		}
	}
	void Cleanup()
	{
		if (ASC.IsValid()) { CancelActions(); ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), SavedMax); HP(SavedHP); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), SavedStamina); }
		if (Player.IsValid()) { Player->HandleInputMoveReleased(); Player->GetCharacterMovement()->StopMovementImmediately(); Player->SetActorLocationAndRotation(SavedLocation, SavedRotation); }
		if (!VFXOutput.IsEmpty())
		{
			Test->TestEqual(TEXT("All original recovery roles / filtered-bone adapters actually emit"), SeenVFX.Num(), 11);
			int32 Remaining = 0;
			for (TObjectIterator<UParticleSystemComponent> It; It; ++It)
				if (IsValid(*It) && Player.IsValid() && It->GetWorld() == Player->GetWorld())
					for (const FName Tag : It->ComponentTags) if (Tag.ToString().StartsWith(TEXT("KZHeal_"))) { ++Remaining; break; }
			Test->TestEqual(TEXT("Cancel removes all recovery components and pose callbacks"), Remaining, 0);
			FFileHelper::SaveStringToFile(VFXObservations, *(VFXOutput / TEXT("Runtime.ndjson")));
			if (Player.IsValid()) if (APlayerController* PC = Player->GetController<APlayerController>(); PC && OldView.IsValid()) PC->SetViewTarget(OldView.Get());
			if (VFXCamera.IsValid()) VFXCamera->Destroy();
		}
	}
	void ObserveRecoveryVFX()
	{
		if (VFXOutput.IsEmpty() || !Player.IsValid()) return;
		if (VFXCamera.IsValid())
		{
			// Preview camera only; these centimetres never enter gameplay/asset tuning.
			const FVector Aim = Player->GetActorLocation() + FVector(0,0,50);
			const FVector Eye = Aim + Player->GetActorQuat().RotateVector(FVector(180,-150,60));
			VFXCamera->SetActorLocationAndRotation(Eye,(Aim-Eye).Rotation());
		}
		for (TObjectIterator<UParticleSystemComponent> It; It; ++It)
		{
			UParticleSystemComponent* P = *It;
			if (!IsValid(P) || P->GetWorld() != Player->GetWorld() || P->GetNumActiveParticles() <= 0) continue;
			for (const FName Tag : P->ComponentTags)
			{
				if (!Tag.ToString().StartsWith(TEXT("KZHeal_"))) continue;
				Test->TestTrue(TEXT("Recovery follows actual player skeleton"), P->GetAttachParent() == Player->GetMesh() && Player->GetMesh()->DoesSocketExist(P->GetAttachSocketName()));
				Test->TestTrue(TEXT("Recovery transform remains finite"), !P->GetComponentTransform().ContainsNaN());
				const float Clock = Heal.IsValid() && Heal->GetCurrentMontage() ? Player->GetMesh()->GetAnimInstance()->Montage_GetPosition(Heal->GetCurrentMontage()) : 0.f;
				if (!SeenVFX.Contains(Tag))
				{
					SeenVFX.Add(Tag);
					VFXObservations += FString::Printf(TEXT("{\"id\":\"%s\",\"clock\":%.9g,\"particles\":%d,\"socket\":\"%s\",\"resource\":\"%s\"}\n"), *Tag.ToString(), Clock, P->GetNumActiveParticles(), *P->GetAttachSocketName().ToString(), *P->Template->GetPathName());
					for (auto* E : P->EmitterInstances)
						if (E && E->ActiveParticles > 0)
							if (const FBaseParticle* Particle = E->GetParticle(0))
								VFXObservations += FString::Printf(TEXT("{\"particle_probe\":\"%s\",\"size\":[%.9g,%.9g,%.9g],\"rgba\":[%.9g,%.9g,%.9g,%.9g],\"location\":[%.9g,%.9g,%.9g],\"component_scale\":[%.9g,%.9g,%.9g],\"relative_age\":%.9g}\n"),*Tag.ToString(),Particle->Size.X,Particle->Size.Y,Particle->Size.Z,Particle->Color.R,Particle->Color.G,Particle->Color.B,Particle->Color.A,Particle->Location.X,Particle->Location.Y,Particle->Location.Z,P->GetComponentScale().X,P->GetComponentScale().Y,P->GetComponentScale().Z,Particle->RelativeTime);
				}
				const float CaptureAt = Tag == FName(TEXT("KZHeal_2_0")) ? 1.35f : 1.95f;
				if (Clock > CaptureAt && Clock < 2.3f && !CapturedVFX.Contains(Tag))
				{
					const FVector W=P->GetComponentLocation(), B=Player->GetMesh()->GetSocketLocation(P->GetAttachSocketName());
					VFXObservations+=FString::Printf(TEXT("{\"late_probe\":\"%s\",\"clock\":%.9g,\"world\":[%.9g,%.9g,%.9g],\"bone\":[%.9g,%.9g,%.9g],\"radius\":%.9g,\"particles_flag\":%d,\"translucency_flag\":%d,\"visible\":%d}\n"),*Tag.ToString(),Clock,W.X,W.Y,W.Z,B.X,B.Y,B.Z,P->Bounds.SphereRadius,GEngine->GameViewport->EngineShowFlags.Particles,GEngine->GameViewport->EngineShowFlags.Translucency,P->IsVisible());
					for(auto* E:P->EmitterInstances)if(E && E->ActiveParticles>0)if(const FBaseParticle* Q=E->GetParticle(0))VFXObservations+=FString::Printf(TEXT("{\"late_particle\":\"%s\",\"size\":[%.9g,%.9g,%.9g],\"rgba\":[%.9g,%.9g,%.9g,%.9g],\"age\":%.9g}\n"),*Tag.ToString(),Q->Size.X,Q->Size.Y,Q->Size.Z,Q->Color.R,Q->Color.G,Q->Color.B,Q->Color.A,Q->RelativeTime);
					FScreenshotRequest::RequestScreenshot(VFXOutput / (Tag.ToString()+TEXT(".png")), false, false);
					CapturedVFX.Add(Tag);
				}
				break;
			}
		}
	}
	FAutomationTestBase* Test;
	struct FWeapon { TWeakObjectPtr<USceneComponent> Component; FName Socket; FTransform Relative; };
	TArray<FWeapon> Weapons;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<UKZAbilitySystemComponent> ASC;
	TWeakObjectPtr<UKZHealAbility> Heal;
	TWeakObjectPtr<UAnimMontage> Montage;
	FGameplayAbilitySpecHandle HealHandle;
	FVector SavedLocation;
	FRotator SavedRotation;
	EKZGait SavedGait;
	float SavedHP = 0.f, SavedMax = 0.f, SavedStamina = 0.f;
	double Deadline, NextTime = 0.0;
	int32 Stage = 0;
	int32 OldDrawId = INDEX_NONE;
	bool bMove = false;
	bool bDrawCaptured = false;
	FString VFXOutput, VFXObservations;
	TSet<FName> SeenVFX, CapturedVFX;
	TWeakObjectPtr<ACameraActor> VFXCamera;
	TWeakObjectPtr<AActor> OldView;
};

class FWaitForHealPIE : public IAutomationLatentCommand
{
public:
	explicit FWaitForHealPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 30.0) {}
	virtual bool Update() override
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			if (Context.WorldType != EWorldType::PIE || !Context.World() || !Context.World()->HasBegunPlay()) continue;
			for (TActorIterator<AKZPlayer> It(Context.World()); It; ++It)
				if (It->IsPlayerControlled() && It->GetCharacterMovement()->IsMovingOnGround() && It->GetMesh()->GetAnimInstance())
				{
					FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FHealPIECommand>(Test, *It));
					return true;
				}
		}
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Start Heal PIE after Test Started on DevMap.")); return true; }
		return false;
	}
private:
	FAutomationTestBase* Test;
	double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZHealPIETest, "Khazan.Heal.PIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZHealPIETest::RunTest(const FString& Parameters)
{
	// DevMap now contains configured AI monsters; missing Definition errors are regressions.
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForHealPIE>(this));
	return true;
}
#endif
