// Work-only development integration probe. No package save or private completion-state writes.
// Run Automation RunTests Khazan.Combat.ReactionPIE, then start the owned DevMap PIE.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/KZActionAbility.h"
#include "Ability/KZHitReactionAbility.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Ability/PlayerAbility/KZGuardAbility.h"
#include "AI/KZMonsterAIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimTypes.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/RootMotionSource.h"
#include "KZGameplayTags.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISense_Sight.h"
#include "RHIGlobals.h"
#include "UnrealClient.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UnrealType.h"

namespace KZCombatReactionPIE
{
const TCHAR* WorkRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/");
const TCHAR* Families[] = {TEXT("Swordsman"), TEXT("SwordShield"), TEXT("HeavySwordsman"),
	TEXT("HalberdElite"), TEXT("ApesStoneHandElite"), TEXT("Yetuga")};
constexpr int32 FamilyCount = static_cast<int32>(UE_ARRAY_COUNT(Families));
constexpr int32 PairCaseCount = FamilyCount * 2 + 3;
constexpr int32 CollisionCaseCount = 3;
using FObject = TSharedPtr<FJsonObject>;
FObject Object() { return MakeShared<FJsonObject>(); }
TSharedPtr<FJsonValue> Json(const FObject& Value) { return MakeShared<FJsonValueObject>(Value); }
template<typename T> T* Field(UObject* Owner, const TCHAR* Name)
{
	FProperty* Property = Owner ? Owner->GetClass()->FindPropertyByName(Name) : nullptr;
	return Property ? Property->ContainerPtrToValuePtr<T>(Owner) : nullptr;
}
FGameplayAbilitySpecHandle FindAbility(UKZAbilitySystemComponent* ASC, UClass* Class)
{
	if (ASC) for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		if (Spec.Ability && Spec.Ability->IsA(Class)) return Spec.Handle;
	return {};
}
bool Active(UKZAbilitySystemComponent* ASC, FGameplayAbilitySpecHandle Handle)
{
	const FGameplayAbilitySpec* Spec = ASC ? ASC->FindAbilitySpecFromHandle(Handle) : nullptr;
	return Spec && Spec->IsActive();
}
enum class EStage : uint8 { Init, ReactionStart, ReactionWait, Shield, ShieldExhaustion,
	GuardStart, GuardWait, GuardFinish, PairSpawn, ExhaustionWait, PairWait, CancelWait,
	CollisionStart, CollisionGuardWait, CollisionWait };
struct FReactionCase { int32 Subject; EKZHitReactionType Type; int32 Extra = 0; };
struct FSavedAI
{
	TWeakObjectPtr<AKZMonsterAIController> AI;
	bool Sight = false, Tick = false, Tree = false;
};

class FProbe : public IAutomationLatentCommand
{
public:
	FProbe(FAutomationTestBase* InTest, AKZPlayer* InPlayer) : Test(InTest), Player(InPlayer)
	{
		PlayerASC = Cast<UKZAbilitySystemComponent>(InPlayer->GetAbilitySystemComponent());
		SavedTransform = InPlayer->GetActorTransform();
		SavedControlRotation = InPlayer->GetController()->GetControlRotation();
		SavedMode = InPlayer->GetCharacterMovement()->MovementMode;
		SavedCustomMode = InPlayer->GetCharacterMovement()->CustomMovementMode;
		SavedTickOption = InPlayer->GetMesh()->VisibilityBasedAnimTickOption;
		SavedRootMotionMode = InPlayer->GetMesh()->GetAnimInstance()->RootMotionMode;
		OriginalPlayerDefinition = InPlayer->GetCharacterDefinition();
		SavedHP = Value(PlayerASC.Get(), UKZAttributeSet::GetHPAttribute());
		SavedMaxHP = Value(PlayerASC.Get(), UKZAttributeSet::GetMaxHPAttribute());
		SavedStamina = Value(PlayerASC.Get(), UKZAttributeSet::GetStaminaAttribute());
		SavedMaxStamina = Value(PlayerASC.Get(), UKZAttributeSet::GetMaxStaminaAttribute());
		for (TActorIterator<AKZMonsterAIController> It(InPlayer->GetWorld()); It; ++It)
		{
			UAIPerceptionComponent* Perception = It->GetPerceptionComponent();
			FSavedAI Saved; Saved.AI = *It; Saved.Sight = Perception && Perception->IsSenseEnabled(UAISense_Sight::StaticClass());
			Saved.Tick = It->IsActorTickEnabled(); Saved.Tree = It->GetStateTreeComponent() && It->GetStateTreeComponent()->IsRunning();
			SavedAIs.Add(Saved);
			if (Perception) Perception->SetSenseEnabled(UAISense_Sight::StaticClass(), false);
			if (Saved.Tree) It->GetStateTreeComponent()->StopLogic(TEXT("Isolated combat reaction fixture"));
			It->StopMovement(); It->SetActorTickEnabled(false);
		}
		for (int32 Subject = 0; Subject <= FamilyCount; ++Subject)
			for (EKZHitReactionType Type : {EKZHitReactionType::Short, EKZHitReactionType::Knockback, EKZHitReactionType::Launch})
				Cases.Add({Subject, Type});
		// Extra cases are QA scenarios, not gameplay categories or tuning.
		Cases.Add({0, EKZHitReactionType::Knockback, 1}); // Transient empty/null pool fallback.
		Cases.Add({1, EKZHitReactionType::Launch, 2});    // Actual Up chain; another owner changes Flying to None.
		Cases.Add({1, EKZHitReactionType::Launch, 3});    // Actual Up chain cancellation above the floor.
		for (int32 Trial = 0; Trial < 8; ++Trial) Cases.Add({0, EKZHitReactionType::Short});
		FParse::Value(FCommandLine::Get(), TEXT("KZCombatPairOnly="), PairOnlyIndex);
		CaptureScreenshots = FParse::Param(FCommandLine::Get(), TEXT("KZCombatScreenshots")) && !GUsingNullRHI;
		PostTickHandle = FWorldDelegates::OnWorldPostActorTick.AddRaw(this, &FProbe::OnPostTick);
		Enter(EStage::Init);
	}
	virtual ~FProbe() override { Cleanup(); }
	virtual bool Update() override
	{
		if (!Player.IsValid() || !PlayerASC.IsValid())
		{ Check(TEXT("Owned PIE fixture remains valid"), false); return Finish(); }
		const double Now = Player->GetWorld()->GetTimeSeconds();
		ObserveProgress();
		if (FPlatformTime::Seconds() > Deadline || Now > StageDeadline)
		{ Snapshot(TEXT("stage_watchdog")); Check(TEXT("Owned stage progresses on its real montage timeline before its QA watchdog"), false); return Finish(); }
		switch (Stage)
		{
		case EStage::Init:
			Cancel(PlayerASC.Get()); Player->HandleInputMoveReleased(); ResetPlayer();
			PlayerDefinition.Reset(DuplicateObject<UKZCharacterDefinitionData>(OriginalPlayerDefinition, GetTransientPackage()));
			if (!Check(TEXT("Player transient Definition fixture can replace only the PIE actor pointer"),
				SetDefinition(Player.Get(), PlayerDefinition.Get()))) return Finish();
			Player->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
			BrutalHandle = FindAbility(PlayerASC.Get(), UKZBrutalAttackAbility::StaticClass());
			GuardHandle = FindAbility(PlayerASC.Get(), UKZGuardAbility::StaticClass());
			if (!Check(TEXT("Player saved Definition grants native hit reaction, Guard and Brutal"),
				FindAbility(PlayerASC.Get(), UKZHitReactionAbility::StaticClass()).IsValid() && GuardHandle.IsValid() && BrutalHandle.IsValid())) return Finish();
			AuditDefinition(TEXT("Player"), OriginalPlayerDefinition, PlayerASC.Get());
			PlayerMovementBaseline = PlayerASC->GetTagCount(KZGameplayTags::Block_Movement_Input);
			PlayerRegenBaseline = PlayerASC->GetTagCount(KZGameplayTags::Block_StaminaRegen);
			PlayerForeign = ForeignConstraint(Player.Get());
			Check(TEXT("Player .01 mesh scale contract is preserved"), Player->GetMesh()->GetRelativeScale3D().Equals(FVector(.01f), UE_KINDA_SMALL_NUMBER));
			if (!Check(TEXT("Optional pair-only QA index is in the existing fifteen-pair fixture"), PairOnlyIndex == INDEX_NONE ||
				(PairOnlyIndex >= 0 && PairOnlyIndex < PairCaseCount))) return Finish();
			if (PairOnlyIndex != INDEX_NONE) { PairIndex = PairOnlyIndex; Enter(EStage::PairSpawn); }
			else Enter(EStage::ReactionStart); break;
		case EStage::ReactionStart:
			if (CaseIndex >= Cases.Num()) { ResetMonster(); if (!Spawn(1)) return Finish(); Enter(EStage::Shield); break; }
			if (!PrepareSubject(Cases[CaseIndex].Subject)) return Finish();
			if (!StartReaction(Cases[CaseIndex])) return Finish();
			Enter(EStage::ReactionWait, Montage->GetPlayLength() + 45.0); break;
		case EStage::ReactionWait:
			if (Cases[CaseIndex].Extra >= 2 && HitActive())
			{
				if (!SawFlying) return false;
				if (Cases[CaseIndex].Extra == 2)
				{
					Subject()->GetCharacterMovement()->SetMovementMode(MOVE_None);
					SubjectAnim()->SetRootMotionMode(ERootMotionMode::RootMotionFromEverything);
					SubjectASC()->CancelAbilityHandle(HitHandle);
					Check(TEXT("Reaction cancellation does not overwrite another owner's non-Flying mode"), Subject()->GetCharacterMovement()->MovementMode == MOVE_None);
					Check(TEXT("Reaction cancellation preserves another owner's replacement animation root mode"), SubjectAnim()->RootMotionMode == ERootMotionMode::RootMotionFromEverything);
				}
				else
				{
					const float Height = Subject()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
					Subject()->AddActorWorldOffset(FVector(0, 0, Height * 3.f), false, nullptr, ETeleportType::TeleportPhysics); // QA geometry only.
					SubjectASC()->CancelAbilityHandle(HitHandle);
					Check(TEXT("Airborne reaction cancellation restores Falling above a distant floor"), Subject()->GetCharacterMovement()->MovementMode == MOVE_Falling);
				}
				CheckMotionReleased(Cases[CaseIndex].Extra == 2); CheckReleased(Subject(), SubjectASC());
				SubjectAnim()->SetRootMotionMode(ReactionRootMotionMode); ++CaseIndex; Enter(EStage::ReactionStart); break;
			}
			if (HitActive()) return false;
			if (SubjectAnim()->GetMontageInstanceForID(MontageInstanceId)) return false;
			Check(TEXT("Real Task completes naturally after advancing its authored montage"), SawAdvance);
			for (FName Section : ExpectedSections) Check(*FString::Printf(TEXT("Actual bound montage timeline traverses %s"), *Section.ToString()), SeenSections.Contains(Section) || TimelineSections.Contains(Section));
			CheckReleased(Subject(), SubjectASC());
			CheckMotionReleased(false);
			if (ExpectedForce)
			{
				Check(TEXT("Actual owned RMS translates the actor in world XY, including static-root animation"), SawOwnMotion && RootMaxPlanar > UE_KINDA_SMALL_NUMBER);
				if (Cases[CaseIndex].Type == EKZHitReactionType::Launch)
					Check(TEXT("Actual Launch lifts the actor and releases force before full montage completion"), RootMaxRise > UE_KINDA_SMALL_NUMBER && SawForceFinishWhileActive);
			}
			if (ExpectedForce && Cases[CaseIndex].Type == EKZHitReactionType::Launch && Montage->GetSectionIndex(TEXT("Up")) != INDEX_NONE)
				Check(TEXT("Actual airborne chain used Flying and released its own mode at completion"), SawFlying && Subject()->GetCharacterMovement()->MovementMode != MOVE_Flying);
			Check(TEXT("World motion respects authored RMS distance/height and extracted-path/capsule QA bounds without extra scale"),
				RootMaxDisplacement <= RootPath + ExpectedMotionDistance + ExpectedMotionHeight + Subject()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() * 2.f);
			Evidence(TEXT("natural_reaction_complete")); TestPrecedence(Subject(), SubjectASC());
			++CaseIndex; Enter(EStage::ReactionStart); break;
		case EStage::Shield:
			if (!TestShield()) return Finish();
			Enter(EStage::ShieldExhaustion); break;
		case EStage::ShieldExhaustion:
			if (!Monster->GetActiveExhaustionAbility()) return false;
			Check(TEXT("Shield stamina depletion prioritizes native exhaustion over hit/shield reaction"),
				!Active(MonsterASC.Get(), FindAbility(MonsterASC.Get(), UKZHitReactionAbility::StaticClass())) &&
				MonsterASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
			MonsterASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), Value(MonsterASC.Get(), UKZAttributeSet::GetMaxStaminaAttribute()));
			MonsterASC->CancelAbilityHandle(Monster->GetActiveExhaustionAbility()->GetCurrentAbilitySpecHandle());
			ResetPlayer(); Enter(EStage::GuardStart); break;
		case EStage::GuardStart:
			Cancel(PlayerASC.Get()); ResetPlayer(); PlayerASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			if (!Check(TEXT("Saved Player Guard activates through its real input tag"), Active(PlayerASC.Get(), GuardHandle))) return Finish();
			Enter(EStage::GuardWait); break;
		case EStage::GuardWait:
			{
				UKZGuardAbility* Guard = Cast<UKZGuardAbility>(PlayerASC->FindAbilitySpecFromHandle(GuardHandle)->GetPrimaryInstance());
				if (!Guard || !Guard->HasInputEnded()) return false;
				const float Spend = Value(PlayerASC.Get(), UKZAttributeSet::GetMaxStaminaAttribute()) / 256.f; // QA-derived hit cost.
				for (int32 Trial = 0; Trial < 96 && GuardSections.Num() < 3; ++Trial)
				{
					const float Before = Value(PlayerASC.Get(), UKZAttributeSet::GetStaminaAttribute());
					if (!Check(TEXT("Real Guard success consumes an attack-provided stamina amount"), PlayerASC->TryGuardHit(Spend, Monster.Get()))) return Finish();
					FName Section = Player->GetMesh()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage());
					Check(TEXT("Guard success belongs to the existing random F/L/R sections"), Section == TEXT("Suc_F") || Section == TEXT("Suc_L") || Section == TEXT("Suc_R"));
					Check(TEXT("Guard consequence is applied once for the accepted hit"), FMath::IsNearlyEqual(Value(PlayerASC.Get(), UKZAttributeSet::GetStaminaAttribute()), Before - Spend));
					GuardSections.Add(Section);
				}
				Check(TEXT("Fixed attacker bearing can select all existing Suc_F/L/R variants"), GuardSections.Num() == 3);
				PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
				Enter(EStage::GuardFinish, Guard->GetCurrentMontage() ? Guard->GetCurrentMontage()->GetPlayLength() + 20.0 : 30.0);
			}
			break;
		case EStage::GuardFinish:
			if (Active(PlayerASC.Get(), GuardHandle)) return false;
			Check(TEXT("Guard's real End releases its state and input block"), !PlayerASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding) &&
				PlayerASC->GetTagCount(KZGameplayTags::Block_Movement_Input) == PlayerMovementBaseline);
			ResetMonster(); PairIndex = 0; Enter(EStage::PairSpawn); break;
		case EStage::PairSpawn:
			if (PairOnlyIndex != INDEX_NONE && PairIndex > PairOnlyIndex) return Finish();
			if (PairIndex >= PairCaseCount) { ResetMonster(); Enter(EStage::CollisionStart); break; }
			ResetMonster(); ResetPlayer();
			PairKind = PairIndex < FamilyCount * 2 ? 0 : PairIndex - FamilyCount * 2 + 1;
			if (!Spawn(PairKind == 0 ? PairIndex / 2 : 0)) return Finish();
			BackPair = PairKind == 0 && (PairIndex % 2 != 0);
			if (!ConfigurePair()) return Finish(); Enter(EStage::ExhaustionWait); break;
		case EStage::ExhaustionWait:
			if (!Monster->GetActiveExhaustionAbility()) return false;
			if (!BeginPair()) return Finish();
			Enter(EStage::PairWait, Settings().BrutalFrontPlayerMontage->GetPlayLength() +
				FMath::Max(Settings().BrutalFrontVictimMontage->GetPlayLength(), Settings().BrutalBackVictimMontage->GetPlayLength()) +
				Settings().ExhaustionMontage->GetPlayLength() + 30.0); break;
		case EStage::PairWait:
			if (PairKind == 1 && BrutalActive() && PairMontagePosition() >= .03356f)
			{
				PlayerASC->CancelAbilityHandle(BrutalHandle);
				if (!Check(TEXT("Approach cancellation releases attacker and retains living exhausted victim"),
					!BrutalActive() && Monster->GetActiveExhaustionAbility() && !Monster->GetActiveExhaustionAbility()->HasBrutalPartner() && Stamina() == 0.f)) return Finish();
				CancelObserveAt = Now + PairMontage->BlendOut.GetBlendTime() + Settings().BrutalAlignmentSeconds;
				CancelLocation = Player->GetActorLocation(); Enter(EStage::CancelWait); break;
			}
			if (PairKind == 2)
			{
				if (BrutalActive()) return false;
				Check(TEXT("Pawn-blocking/visibility-clear wall aborts swept approach without damage/refill"),
					Monster->GetActiveExhaustionAbility() && !Monster->GetActiveExhaustionAbility()->HasBrutalPartner() && HPDrops == 0 && Stamina() == 0.f &&
					FVector::DotProduct(Player->GetActorLocation() - WallLocation, PairForward) < 0.f);
				CheckPlayerPairReleased(); ++CompletedPairs; ++PairIndex; Enter(EStage::PairSpawn); break;
			}
			if (!BrutalActive() && Monster->GetActiveExhaustionAbility() && !Monster->GetActiveExhaustionAbility()->HasBrutalPartner())
			{
				// CompleteBrutalPair clears the claim after both tasks finish, then plays recovery End before the refill.
				UAnimInstance* Anim = Monster->GetMesh()->GetAnimInstance();
				UAnimMontage* Current = Anim->GetCurrentActiveMontage();
				const bool ActualRecoveryEnd = HP() > 0.f && Current == Settings().ExhaustionMontage &&
					Anim->Montage_GetCurrentSection(Settings().ExhaustionMontage) == TEXT("End");
				if (ActualRecoveryEnd) RememberRecoveryEnd(Anim);
				// During terminal blend-out the montage is no longer "active", while its real Task is still completing.
				const bool ObservedEndAwaitingTask = HP() > 0.f && Current == nullptr && SawRecoveryEnd && RecoveryEndInstanceId != INDEX_NONE;
				if (!ActualRecoveryEnd && !ObservedEndAwaitingTask)
				{ Snapshot(TEXT("unexpected_pair_abort")); Check(TEXT("Normal pair releases its claim into actual recovery End after its real endpoints"), false); return Finish(); }
				if (!SawClaimReleasedForRecovery)
				{ SawClaimReleasedForRecovery = true; Snapshot(TEXT("normal_pair_claim_released_for_recovery_end")); }
			}
			if (BrutalActive() || Monster->GetActiveExhaustionAbility()) return false;
			Check(TEXT("Brutal applies configured user HP50 exactly once"), FMath::IsNearlyEqual(InitialPairHP - HP(), 50.f) && HPDrops == 1);
			Check(TEXT("Paired animation stages are observed without mutating completion flags"), SawDamage1 && SawDamage2 && PairAdvanced && NoEarlyRecovery);
			Check(TEXT("Gradual approach has an intermediate position and reaches its capsule-based target"), SawIntermediate && SawAlignmentEnd && AlignmentError <= Player->GetCapsuleComponent()->GetScaledCapsuleRadius() / 20.f);
			if (PairKind == 3)
				Check(TEXT("Lethal pair retains Damage2 until normal endpoints, then freezes dead without refill"), SawDeadDuringPair && NoEarlyFreeze && HP() == 0.f && Stamina() == 0.f && Monster->GetMesh()->bPauseAnims && PositiveRefills == 0);
			else
				Check(TEXT("Living pair waits for both endpoints and actual End before one max refill"), HP() > 0.f && SawRecoveryEnd && PositiveRefills == 1 &&
					FMath::IsNearlyEqual(Stamina(), Value(MonsterASC.Get(), UKZAttributeSet::GetMaxStaminaAttribute())));
			CheckPlayerPairReleased(); Evidence(TEXT("paired_completion")); ++CompletedPairs; ++PairIndex; Enter(EStage::PairSpawn); break;
		case EStage::CancelWait:
			if (Now < CancelObserveAt) { if (!CancelStableStarted) CancelLocation = Player->GetActorLocation(); return false; }
			if (!CancelStableStarted) { CancelStableStarted = true; CancelObserveAt = Now + Settings().BrutalAlignmentSeconds * 2.f; CancelLocation = Player->GetActorLocation(); return false; }
			Check(TEXT("Cancelled approach has no late alignment timer displacement or consequence"), Player->GetActorLocation().Equals(CancelLocation, UE_KINDA_SMALL_NUMBER) && HPDrops == 0 && PositiveRefills == 0 && Stamina() == 0.f);
			CheckPlayerPairReleased(); ++CompletedPairs; ++PairIndex; Enter(EStage::PairSpawn); break;
		case EStage::CollisionStart:
			if (CollisionIndex >= CollisionCaseCount) return Finish();
			if (!PrepareCollision()) return Finish();
			if (CollisionGuarded) { PlayerASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard); Enter(EStage::CollisionGuardWait); }
			else if (!BeginCollision()) return Finish();
			break;
		case EStage::CollisionGuardWait:
			{
				const FGameplayAbilitySpec* GuardSpec = PlayerASC->FindAbilitySpecFromHandle(GuardHandle);
				const UKZGuardAbility* Guard = GuardSpec ? Cast<UKZGuardAbility>(GuardSpec->GetPrimaryInstance()) : nullptr;
				if (!Check(TEXT("Collision fixture activates the saved held Player Guard"), Guard && Guard->IsActive())) return Finish();
				if (!Guard->HasInputEnded()) return false;
				if (!BeginCollision()) return Finish();
			}
			break;
		case EStage::CollisionWait:
			if (!ObserveCollision()) return Finish();
			if (Active(MonsterASC.Get(), CollisionActionHandle)) return false;
			if (CollisionGuarded && Active(PlayerASC.Get(), GuardHandle))
			{ PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard); return false; }
			if (Active(PlayerASC.Get(), FindAbility(PlayerASC.Get(), UKZHitReactionAbility::StaticClass()))) return false;
			Check(TEXT("Real Monster query applies one saved window consequence despite its dense samples"), CollisionGuarded ?
				CollisionHPDrops == 0 && CollisionStaminaDrops == 1 && FMath::IsNearlyEqual(CollisionStaminaLoss, CollisionWindow.StaminaDamage) :
				CollisionHPDrops == 1 && FMath::IsNearlyEqual(CollisionHPLoss, CollisionWindow.HPDamage) && CollisionSawReaction);
			CheckReleased(Player.Get(), PlayerASC.Get()); Snapshot(TEXT("actual_monster_player_collision_complete"));
			RemoveCollisionDelegates(); ++CollisionIndex; Enter(EStage::CollisionStart); break;
		}
		return false;
	}

private:
	static float Value(UKZAbilitySystemComponent* ASC, FGameplayAttribute Attribute) { return ASC ? ASC->GetNumericAttribute(Attribute) : 0.f; }
	bool Check(const TCHAR* Label, bool Pass)
	{
		const FString Name = FString::Printf(TEXT("Case%d Pair%d %s"), CaseIndex, PairIndex, Label);
		Test->TestTrue(*Name, Pass); FObject Row = Object(); Row->SetStringField(TEXT("check"), Name); Row->SetBoolField(TEXT("passed"), Pass); Checks.Add(Json(Row)); return Pass;
	}
	void Enter(EStage Next, double Watchdog = 30.0)
	{
		Stage = Next; StageStarted = Player->GetWorld()->GetTimeSeconds(); StageDeadline = StageStarted + Watchdog;
		Deadline = FPlatformTime::Seconds() + 30.0; // QA no-progress wall-clock limit; advancing simulation uses source-derived stage budget.
		LastPlayerPosition = LastVictimPosition = -1.f; LastPlayerMontage.Reset(); LastVictimMontage.Reset();
	}
	void ObserveProgress()
	{
		auto Observe = [this](AKZCharacter* Character, TWeakObjectPtr<UAnimMontage>& LastMontage, float& LastPosition)
		{
			UAnimInstance* Anim = Character ? Character->GetMesh()->GetAnimInstance() : nullptr;
			UAnimMontage* Current = Anim ? Anim->GetCurrentActiveMontage() : nullptr;
			const float Position = Current ? Anim->Montage_GetPosition(Current) : -1.f;
			if (LastMontage.Get() != Current || !FMath::IsNearlyEqual(Position, LastPosition)) Deadline = FPlatformTime::Seconds() + 30.0;
			LastMontage = Current; LastPosition = Position;
		};
		Observe(Player.Get(), LastPlayerMontage, LastPlayerPosition); Observe(Monster.Get(), LastVictimMontage, LastVictimPosition);
	}
	void Snapshot(const TCHAR* Reason)
	{
		FObject Row = Object(); Row->SetStringField(TEXT("event"), Reason); Row->SetNumberField(TEXT("stage"), static_cast<int32>(Stage));
		Row->SetNumberField(TEXT("case"), CaseIndex); Row->SetNumberField(TEXT("pair"), PairIndex); Row->SetNumberField(TEXT("collision_case"), CollisionIndex);
		Row->SetNumberField(TEXT("stage_elapsed_game_seconds"), Player->GetWorld()->GetTimeSeconds() - StageStarted);
		Row->SetBoolField(TEXT("brutal_active"), BrutalActive()); Row->SetNumberField(TEXT("hp_drops"), HPDrops); Row->SetNumberField(TEXT("positive_refills"), PositiveRefills);
		Row->SetBoolField(TEXT("saw_damage1"), SawDamage1); Row->SetBoolField(TEXT("saw_damage2"), SawDamage2); Row->SetBoolField(TEXT("saw_recovery_end"), SawRecoveryEnd);
		Row->SetNumberField(TEXT("observed_recovery_end_instance_id"), RecoveryEndInstanceId);
		Row->SetBoolField(TEXT("observed_recovery_end_instance_present"), Monster.IsValid() && RecoveryEndInstanceId != INDEX_NONE && Monster->GetMesh()->GetAnimInstance()->GetMontageInstanceForID(RecoveryEndInstanceId));
		Row->SetBoolField(TEXT("exhaustion_active"), Monster.IsValid() && Monster->GetActiveExhaustionAbility());
		Row->SetBoolField(TEXT("victim_claimed"), Monster.IsValid() && Monster->GetActiveExhaustionAbility() && Monster->GetActiveExhaustionAbility()->HasBrutalPartner());
		auto Record = [&Row](AKZCharacter* Character, const TCHAR* Prefix)
		{
			if (!Character) return; UAnimInstance* Anim = Character->GetMesh()->GetAnimInstance(); UAnimMontage* Current = Anim ? Anim->GetCurrentActiveMontage() : nullptr;
			Row->SetStringField(FString(Prefix) + TEXT("_montage"), GetPathNameSafe(Current));
			Row->SetNumberField(FString(Prefix) + TEXT("_position"), Current ? Anim->Montage_GetPosition(Current) : 0.f);
			Row->SetStringField(FString(Prefix) + TEXT("_section"), Current ? Anim->Montage_GetCurrentSection(Current).ToString() : TEXT(""));
			Row->SetStringField(FString(Prefix) + TEXT("_location"), Character->GetActorLocation().ToString());
			Row->SetNumberField(FString(Prefix) + TEXT("_movement_mode"), Character->GetCharacterMovement()->MovementMode);
		};
		Record(Player.Get(), TEXT("player")); Record(Monster.Get(), TEXT("victim")); Events.Add(Json(Row));
	}
	void RememberRecoveryEnd(UAnimInstance* Anim)
	{
		if (!Anim || Anim->GetCurrentActiveMontage() != Settings().ExhaustionMontage ||
			Anim->Montage_GetCurrentSection(Settings().ExhaustionMontage) != TEXT("End")) return;
		if (const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Settings().ExhaustionMontage))
		{ RecoveryEndInstanceId = Instance->GetInstanceID(); SawRecoveryEnd = true; }
	}
	void Capture(const FString& Label, AKZCharacter* Focus, bool IncludePlayer = false)
	{
		if (!CaptureScreenshots || !Focus || CapturedLabels.Contains(Label) || FScreenshotRequest::IsScreenshotRequested()) return;
		APlayerController* Controller = Cast<APlayerController>(Player->GetController());
		if (!Controller || !Controller->PlayerCameraManager || !GEngine->GameViewport || !GEngine->GameViewport->Viewport) return;
		if (!CaptureCamera.IsValid())
		{
			OriginalViewTarget = Controller->GetViewTarget(); CaptureCamera = Player->GetWorld()->SpawnActor<ACameraActor>();
			if (!CaptureCamera.IsValid()) return;
			ScreenshotProcessedHandle = FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this, &FProbe::RestoreCaptureCamera);
		}
		FBox Bounds(ForceInit);
		auto AddVisibleBounds = [&Bounds](AKZCharacter* Character)
		{
			Bounds += Character->GetCapsuleComponent()->Bounds.GetBox();
			TInlineComponentArray<USkeletalMeshComponent*> Meshes; Character->GetComponents(Meshes);
			for (USkeletalMeshComponent* Mesh : Meshes)
				if (Mesh && Mesh->IsVisible() && !Mesh->bHiddenInGame && Mesh->GetSkeletalMeshAsset()) Bounds += Mesh->Bounds.GetBox();
		};
		AddVisibleBounds(Focus); if (IncludePlayer) AddVisibleBounds(Player.Get());
		if (!Bounds.IsValid) return;
		const FIntPoint Size = GEngine->GameViewport->Viewport->GetSizeXY(); if (Size.X <= 0 || Size.Y <= 0) return;
		const float FOV = Controller->PlayerCameraManager->GetFOVAngle();
		const double Aspect = static_cast<double>(Size.X) / Size.Y;
		const double HalfVerticalFOV = FMath::Atan(FMath::Tan(FMath::DegreesToRadians(FOV * .5)) / Aspect);
		const double FitSin = FMath::Sin(FMath::Min<double>(FMath::DegreesToRadians(FOV * .5), HalfVerticalFOV));
		if (FitSin <= UE_KINDA_SMALL_NUMBER) return;
		// QA framing comes from live bounds, viewport aspect and existing FOV; this does not tune gameplay cameras.
		const FVector Center = Bounds.GetCenter(); const double Distance = Bounds.GetExtent().Size() / FitSin;
		const FVector Direction = (Focus->GetActorRightVector() - Focus->GetActorForwardVector() + FVector::UpVector).GetSafeNormal();
		const FVector Location = Center + Direction * Distance;
		CaptureCamera->SetActorLocationAndRotation(Location, (Center - Location).Rotation());
		CaptureCamera->GetCameraComponent()->SetFieldOfView(FOV); CaptureCamera->GetCameraComponent()->SetAspectRatio(Aspect);
		CaptureCamera->GetCameraComponent()->PostProcessSettings.bOverride_MotionBlurAmount = true;
		CaptureCamera->GetCameraComponent()->PostProcessSettings.MotionBlurAmount = 0.f; // QA image clarity only, restored with the temporary view target.
		Controller->SetViewTarget(CaptureCamera.Get()); Controller->PlayerCameraManager->UpdateCamera(0.f);
		Controller->PlayerCameraManager->SetGameCameraCutThisFrame(); // Discard the gameplay view's temporal history for this temporary capture camera.
		const FString Filename = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Metadata/CombatReaction_20261008/Screenshots/") + Label + TEXT(".png"));
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true);
		FScreenshotRequest::RequestScreenshot(Filename, false, false, false, FIntRect(), true); CapturedLabels.Add(Label);
		FObject Row = Object(); Row->SetStringField(TEXT("event"), TEXT("native_rhi_screenshot_requested")); Row->SetStringField(TEXT("file"), Filename);
		Row->SetStringField(TEXT("label"), Label); Row->SetStringField(TEXT("focus_actor"), Focus->GetPathName()); Row->SetNumberField(TEXT("pair"), PairIndex); Row->SetNumberField(TEXT("case"), CaseIndex); Events.Add(Json(Row));
		Row->SetStringField(TEXT("visible_bounds_extent_cm"), Bounds.GetExtent().ToString()); Row->SetNumberField(TEXT("framing_distance_cm"), Distance);
		Row->SetStringField(TEXT("requested_camera_location"), Location.ToString()); Row->SetStringField(TEXT("actual_camera_pov_location"), Controller->PlayerCameraManager->GetCameraLocation().ToString());
		Row->SetBoolField(TEXT("temporary_camera_motion_blur_disabled"), true);
	}
	void RestoreCaptureCamera()
	{
		if (!Player.IsValid()) return; APlayerController* Controller = Cast<APlayerController>(Player->GetController());
		if (Controller && CaptureCamera.IsValid() && Controller->GetViewTarget() == CaptureCamera.Get()) Controller->SetViewTarget(OriginalViewTarget.IsValid() ? OriginalViewTarget.Get() : Player.Get());
	}
	void Cancel(UKZAbilitySystemComponent* ASC)
	{
		if (!ASC) return; FGameplayTagContainer Tags; Tags.AddTag(KZGameplayTags::Ability_Action); Tags.AddTag(KZGameplayTags::Ability_Reaction_Hit);
		ASC->CancelAbilities(&Tags); ASC->ClearComboCommands();
	}
	bool SetDefinition(AKZCharacter* Character, UKZCharacterDefinitionData* Definition)
	{
		FObjectPropertyBase* Property = Character ? FindFProperty<FObjectPropertyBase>(Character->GetClass(), TEXT("CharacterDefinition")) : nullptr;
		if (!Property || !Definition) return false;
		if (Definition->GetOutermost() == GetTransientPackage()) { Definition->ClearFlags(RF_Public | RF_Standalone); Definition->SetFlags(RF_Transient); }
		Property->SetObjectPropertyValue_InContainer(Character, Definition); return true;
	}
	FKZMovementConstraintHandle ForeignConstraint(AKZCharacter* Character)
	{
		FKZMovementConstraint Constraint; Constraint.MaxAllowedGait = EKZGait::Walk;
		Constraint.bOverrideRotationMode = true; Constraint.RotationModeOverride = EKZRotationMode::LockOn;
		Constraint.DebugName = TEXT("ReactionPIE foreign constraint"); return Character->GetLocomotionComponent()->AcquireMovementConstraint(Character, Constraint);
	}
	void ResetPlayer()
	{
		Cancel(PlayerASC.Get()); PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_X);
		PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard); Player->HandleInputMoveReleased();
		Player->GetCharacterMovement()->StopMovementImmediately(); Player->SetActorTransform(SavedTransform, false, nullptr, ETeleportType::TeleportPhysics);
		Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
		Player->GetMesh()->GetAnimInstance()->SetRootMotionMode(SavedRootMotionMode);
		PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), SavedMaxHP);
		PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), SavedMaxStamina);
	}
	void AuditDefinition(const TCHAR* Family, const UKZCharacterDefinitionData* Definition, UKZAbilitySystemComponent* ASC)
	{
		const auto& R = Definition->GetHitReactionSettings(); FObject Row = Object(); Row->SetStringField(TEXT("family"), Family);
		Row->SetStringField(TEXT("definition"), Definition->GetPathName()); Row->SetNumberField(TEXT("short"), R.ShortHits.Num());
		Row->SetNumberField(TEXT("knockback"), R.Knockbacks.Num()); Row->SetNumberField(TEXT("launch"), R.Launches.Num());
		Row->SetNumberField(TEXT("shield"), R.ShieldBlocks.Num()); Row->SetBoolField(TEXT("native_grant"), FindAbility(ASC, UKZHitReactionAbility::StaticClass()).IsValid());
		Check(TEXT("Saved Definition has a non-null short pool and native hit grant"), R.ShortHits.ContainsByPredicate([](const TObjectPtr<UAnimMontage>& M) { return IsValid(M.Get()); }) && FindAbility(ASC, UKZHitReactionAbility::StaticClass()).IsValid());
		Audits.Add(Json(Row));
	}
	bool Spawn(int32 Family)
	{
		CurrentFamily = Family;
		const FString Base = FString(TEXT("/Game/Bluprints/Monsters/BP_Monster_")) + Families[Family];
		UClass* Class = LoadClass<AKZMonster>(nullptr, *(Base + TEXT(".BP_Monster_") + Families[Family] + TEXT("_C")));
		const FString DefPath = FString(TEXT("/Game/Monsters/")) + Families[Family] + TEXT("/Data/DA_Character_") + Families[Family];
		const UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *DefPath);
		if (!Check(TEXT("Saved family BP and Definition load"), Class && Definition)) return false;
		const AKZMonster* CDO = Class->GetDefaultObject<AKZMonster>();
		Anchor = SavedTransform.GetLocation() + SavedTransform.GetRotation().GetForwardVector().GetSafeNormal2D() * Definition->GetMonsterStaminaSettings().BrutalAttackRange;
		Anchor.Z += CDO->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		AnchorRotation = FRotator(0, SavedTransform.Rotator().Yaw + 180.f, 0);
		FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Monster = Player->GetWorld()->SpawnActor<AKZMonster>(Class, Anchor, AnchorRotation, Params);
		if (!Monster.IsValid()) return Check(TEXT("Authored family actor spawns"), false);
		if (!Monster->GetController()) Monster->SpawnDefaultController();
		AI = Cast<AKZMonsterAIController>(Monster->GetController()); MonsterASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		if (!Check(TEXT("Actual family ASC/controller/Definition/AnimInstance initialize"), AI.IsValid() && MonsterASC.IsValid() && Monster->GetCharacterDefinition() == Definition && Monster->GetMesh()->GetAnimInstance())) return false;
		if (Monster->GetAIStateTree()) AI->Tick(0.f);
		else FixtureIntent = Monster->GetLocomotionComponent()->BeginLocomotionIntentSource(AI.Get(), EKZLocomotionIntentSource::AIController);
		if (AI->GetPerceptionComponent()) AI->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), false);
		if (AI->GetStateTreeComponent()->IsRunning()) AI->GetStateTreeComponent()->StopLogic(TEXT("ReactionPIE spawned fixture"));
		AI->StopMovement(); AI->SetActorTickEnabled(false); Cancel(MonsterASC.Get());
		Monster->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		MonsterDefinition.Reset(DuplicateObject<UKZCharacterDefinitionData>(Definition, GetTransientPackage()));
		if (!Check(TEXT("Family data changes are confined to a transient Definition"), SetDefinition(Monster.Get(), MonsterDefinition.Get()))) return false;
		FKZMonsterStaminaSettings* StaminaSettings = Field<FKZMonsterStaminaSettings>(MonsterDefinition.Get(), TEXT("MonsterStamina"));
		if (!Check(TEXT("Transient fixture exposes existing monster policy"), StaminaSettings != nullptr)) return false;
		StaminaSettings->ExhaustionSeconds = 0.f; // QA-only indefinite exhaustion prevents unrelated expiry while observing callbacks.
		MonsterMovementBaseline = MonsterASC->GetTagCount(KZGameplayTags::Block_Movement_Input);
		MonsterRegenBaseline = MonsterASC->GetTagCount(KZGameplayTags::Block_StaminaRegen);
		MonsterForeign = ForeignConstraint(Monster.Get()); AuditDefinition(Families[Family], Definition, MonsterASC.Get());
		return Check(TEXT("Living family fixture has positive HP/stamina and movement permission"), HP() > 0.f && Stamina() > 0.f && Monster->GetLocomotionComponent()->IsMovementInputAllowed());
	}
	AKZCharacter* Subject() const { return CurrentSubject == 0 ? static_cast<AKZCharacter*>(Player.Get()) : Monster.Get(); }
	UKZAbilitySystemComponent* SubjectASC() const { return CurrentSubject == 0 ? PlayerASC.Get() : MonsterASC.Get(); }
	UAnimInstance* SubjectAnim() const { return Subject()->GetMesh()->GetAnimInstance(); }
	bool HitActive() const { return Active(SubjectASC(), HitHandle); }
	TSharedPtr<FRootMotionSource> LiveReactionMotion() const
	{
		const FRootMotionSourceGroup& Group = Subject()->GetCharacterMovement()->CurrentRootMotion;
		for (const auto* Sources : {&Group.RootMotionSources, &Group.PendingAddRootMotionSources})
			for (const TSharedPtr<FRootMotionSource>& Source : *Sources)
				if (Source.IsValid() && Source->InstanceName == TEXT("HitReactionMotion") && !Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval)) return Source;
		return nullptr;
	}
	bool PrepareSubject(int32 SubjectIndex)
	{
		CurrentSubject = SubjectIndex; ResetPlayer();
		if (SubjectIndex == 0)
		{
			*Field<FKZHitReactionSettings>(PlayerDefinition.Get(), TEXT("HitReactions")) = OriginalPlayerDefinition->GetHitReactionSettings();
		}
		else
		{
			if (!Monster.IsValid() || CurrentFamily != SubjectIndex - 1) { ResetMonster(); if (!Spawn(SubjectIndex - 1)) return false; }
			Cancel(MonsterASC.Get()); Monster->SetActorLocationAndRotation(Anchor, AnchorRotation, false, nullptr, ETeleportType::TeleportPhysics);
			Monster->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Monster->GetCharacterMovement()->StopMovementImmediately();
		}
		return true;
	}
	const TArray<TObjectPtr<UAnimMontage>>& Pool(const FKZHitReactionSettings& Settings, EKZHitReactionType Type) const
	{ return Type == EKZHitReactionType::Launch ? Settings.Launches : Type == EKZHitReactionType::Knockback ? Settings.Knockbacks : Settings.ShortHits; }
	bool StartReaction(const FReactionCase& Case)
	{
		UKZAbilitySystemComponent* ASC = SubjectASC(); AKZCharacter* Character = Subject();
		HitHandle = FindAbility(ASC, UKZHitReactionAbility::StaticClass());
		FGameplayAbilitySpecHandle ActionHandle;
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
			if (const UKZComboActionAbility* Combo = Cast<UKZComboActionAbility>(Spec.Ability); Combo &&
				(CurrentSubject != 0 || Combo->GetEntryNodeId() == TEXT("WeakAttack01"))) { ActionHandle = Spec.Handle; break; }
		if (ActionHandle.IsValid()) Check(TEXT("An actual authored Action starts before forced reaction"), ASC->TryActivateAbility(ActionHandle));
		if (Case.Extra == 1)
		{
			auto* Settings = Field<FKZHitReactionSettings>(PlayerDefinition.Get(), TEXT("HitReactions"));
			Settings->Knockbacks.Reset(); Settings->Knockbacks.Add(nullptr); // QA only, original Definition remains intact.
		}
		ReactionStartLocation = Character->GetActorLocation(); ReactionRootMotionMode = SubjectAnim()->RootMotionMode;
		SeenSections.Reset(); TimelineSections.Reset(); ExpectedSections.Reset(); SawAdvance = SawFlying = SawOwnMotion = SawForceFinishWhileActive = false;
		RootPath = RootMaxDisplacement = RootMaxPlanar = RootMaxRise = PreviousMontagePosition = 0.f;
		Character->PlayHitReaction(Case.Type, Player.Get());
		if (!Check(TEXT("Public consequence entry activates the real native hit Ability"), HitActive())) return false;
		if (ActionHandle.IsValid())
		{
			Check(TEXT("Forced reaction cancels the preceding Action"), !Active(ASC, ActionHandle));
			Check(TEXT("Forced reaction blocks a new Action until actual completion"), !ASC->TryActivateAbility(ActionHandle));
		}
		UKZHitReactionAbility* Hit = Cast<UKZHitReactionAbility>(ASC->FindAbilitySpecFromHandle(HitHandle)->GetPrimaryInstance());
		Montage = Hit ? Hit->GetCurrentMontage() : nullptr;
		if (!Check(TEXT("Real reaction montage is non-null"), Montage != nullptr)) return false;
		const auto& Settings = Character->GetCharacterDefinition()->GetHitReactionSettings(); const auto& SelectedPool = Pool(Settings, Case.Type);
		const bool HasRequested = SelectedPool.ContainsByPredicate([](const TObjectPtr<UAnimMontage>& M) { return IsValid(M.Get()); });
		Check(TEXT("Random variant is a member of its authored category, or short fallback when empty"), (HasRequested ? SelectedPool : Settings.ShortHits).Contains(Montage.Get()));
		ExpectedForce = Case.Type != EKZHitReactionType::Short && (Montage->GetSectionIndex(TEXT("Up")) != INDEX_NONE ||
			Montage->GetSectionIndex(TEXT("Air")) != INDEX_NONE || Montage->GetSectionIndex(TEXT("Down")) != INDEX_NONE);
		ExpectedMotionDistance = ExpectedForce ? (Case.Type == EKZHitReactionType::Launch ? Settings.LaunchDistance : Settings.KnockbackDistance) : 0.f;
		ExpectedMotionHeight = ExpectedForce && Case.Type == EKZHitReactionType::Launch ? Settings.LaunchHeight : 0.f;
		const TSharedPtr<FRootMotionSource> Force = LiveReactionMotion();
		ReactionSourceId = Force.IsValid() ? Force->LocalID : static_cast<uint16>(ERootMotionSourceID::Invalid);
		Check(TEXT("Real RMS exists only for an actual Up/Air/Down knockback or launch chain"), ExpectedForce == Force.IsValid());
		if (ExpectedForce)
		{
			SawOwnMotion = Force.IsValid();
			Check(TEXT("Owned force temporarily ignores animation root motion without changing asset roots"), SubjectAnim()->RootMotionMode == ERootMotionMode::IgnoreRootMotion);
		}
		Check(TEXT("Reaction owns State/Input block and VelocityDirection without copying AI state"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting) &&
			!Character->GetLocomotionComponent()->IsMovementInputAllowed() && Character->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::VelocityDirection);
		const FAnimMontageInstance* Instance = SubjectAnim()->GetActiveInstanceForMontage(Montage.Get());
		if (!Check(TEXT("Bound real montage instance exists"), Instance != nullptr)) return false;
		// Observe the actual initial section now: a hitch can advance beyond a short Up before PostActorTick.
		SeenSections.Add(SubjectAnim()->Montage_GetCurrentSection(Montage.Get()));
		MontageInstanceId = Instance->GetInstanceID(); int32 Section = 0;
		while (Montage->CompositeSections.IsValidIndex(Section) && !ExpectedSections.Contains(Montage->CompositeSections[Section].SectionName))
		{ ExpectedSections.Add(Montage->CompositeSections[Section].SectionName); Section = Montage->GetSectionIndex(Montage->CompositeSections[Section].NextSectionName); }
		Variants.Add(Montage->GetPathName()); Evidence(TEXT("reaction_activated")); return true;
	}
	void CheckReleased(AKZCharacter* Character, UKZAbilitySystemComponent* ASC)
	{
		const bool IsPlayer = Character == Player.Get();
		Check(TEXT("Actual completion/cancel removes only reaction-owned tags and movement constraint"),
			!ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting) && ASC->GetTagCount(KZGameplayTags::Block_Movement_Input) == (IsPlayer ? PlayerMovementBaseline : MonsterMovementBaseline) &&
			ASC->GetTagCount(KZGameplayTags::Block_StaminaRegen) == (IsPlayer ? PlayerRegenBaseline : MonsterRegenBaseline) &&
			Character->GetLocomotionComponent()->IsMovementInputAllowed() && Character->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::LockOn);
	}
	void CheckMotionReleased(bool OtherRootModeOwner)
	{
		const TSharedPtr<FRootMotionSource> Force = Subject()->GetCharacterMovement()->GetRootMotionSourceByID(ReactionSourceId);
		Check(TEXT("Completion/cancel removes its own engine RMS source"), !Force.IsValid() || Force->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval));
		if (!OtherRootModeOwner) Check(TEXT("Completion/cancel restores its prior animation root-motion mode"), SubjectAnim()->RootMotionMode == ReactionRootMotionMode);
	}
	void TestPrecedence(AKZCharacter* Character, UKZAbilitySystemComponent* ASC)
	{
		const float HPBefore = Value(ASC, UKZAttributeSet::GetHPAttribute()), StaminaBefore = Value(ASC, UKZAttributeSet::GetStaminaAttribute());
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), 0.f); Character->PlayHitReaction(EKZHitReactionType::Short, Player.Get());
		Check(TEXT("Numeric HP zero rejects hit activation before any deferred death tick"), !HitActive()); ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), HPBefore);
		if (Character != Player.Get())
		{ ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), 0.f); Character->PlayHitReaction(EKZHitReactionType::Short, Player.Get()); Check(TEXT("Numeric monster stamina zero rejects hit before deferred exhaustion"), !HitActive()); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), StaminaBefore); }
		for (const FGameplayTag Tag : {FGameplayTag(KZGameplayTags::State_Dead), FGameplayTag(KZGameplayTags::State_Exhausted)})
		{ ASC->AddLooseGameplayTag(Tag); Character->PlayHitReaction(EKZHitReactionType::Short, Player.Get()); Check(TEXT("Dead/Exhausted tag blocks forced hit"), !HitActive()); ASC->RemoveLooseGameplayTag(Tag); }
	}
	bool PrepareCollision()
	{
		RemoveCollisionDelegates(); ResetMonster(); ResetPlayer(); CurrentSubject = 0;
		const int32 Family = CollisionIndex == 0 ? 0 : CollisionIndex == 1 ? 1 : 3;
		if (!Spawn(Family)) return false;
		CollisionGuarded = CollisionIndex == 1; CollisionActionHandle = {}; CollisionCombo.Reset();
		CollisionHPDrops = CollisionStaminaDrops = 0; CollisionHPLoss = CollisionStaminaLoss = 0.f;
		CollisionSawReaction = CollisionSawGuard = CollisionTargetRemoved = false;
		for (const FGameplayAbilitySpec& Spec : MonsterASC->GetActivatableAbilities())
		{
			const UKZComboActionAbility* Combo = Cast<UKZComboActionAbility>(Spec.Ability);
			const UKZComboDefinitionData* Definition = Combo ? Combo->GetComboDefinition() : nullptr;
			const FKZComboNode* Node = Definition ? Definition->FindNode(Combo->GetEntryNodeId()) : nullptr;
			if (!Node || !Node->Montage || Node->AttackWindows.Num() != 1 || !Definition->GetAttackDamageEffect()) continue;
			const FKZAttackCollisionWindow& Window = Node->AttackWindows[0];
			if (Window.Keys.IsEmpty() || Window.HPDamage <= 0.f || Window.StaminaDamage <= 0.f ||
				Window.HitReaction == EKZHitReactionType::None || CollisionGuarded && !Window.bBlockable) continue;
			// Choose a saved baked point reachable by normal standing capsules; never enlarge the collision or the Player.
			double BestHeight = TNumericLimits<double>::Max(); int32 BestKey = INDEX_NONE;
			for (int32 Index = 0; Index < Window.Keys.Num(); ++Index)
			{
				const FKZAttackCollisionKey& Key = Window.Keys[Index];
				const FTransform Pose = FTransform(Key.Rotation.Quaternion(), Key.Center) * Node->CollisionToActor * Monster->GetActorTransform();
				const double Distance = FVector::Dist2D(Pose.GetLocation(), Monster->GetActorLocation());
				const double Height = FMath::Abs(Pose.GetLocation().Z - SavedTransform.GetLocation().Z);
				if (Distance > Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius() && Height < BestHeight)
				{ BestHeight = Height; BestKey = Index; }
			}
			if (BestKey == INDEX_NONE) continue;
			CollisionActionHandle = Spec.Handle; CollisionNode = *Node; CollisionWindow = Window;
			CollisionKey = Window.Keys[BestKey]; CollisionDefinition = Definition->GetPathName(); break;
		}
		if (!Check(TEXT("Collision fixture finds a saved native entry with one actual damage window"), CollisionActionHandle.IsValid())) return false;
		PlaceCollisionTarget();
		FObject Row = Object(); Row->SetStringField(TEXT("event"), TEXT("actual_collision_fixture")); Row->SetNumberField(TEXT("collision_case"), CollisionIndex);
		Row->SetStringField(TEXT("family"), Families[Family]); Row->SetStringField(TEXT("definition"), CollisionDefinition);
		Row->SetStringField(TEXT("node"), CollisionNode.NodeId.ToString()); Row->SetStringField(TEXT("montage"), CollisionNode.Montage->GetPathName());
		Row->SetNumberField(TEXT("window_start_seconds"), CollisionWindow.StartTime); Row->SetNumberField(TEXT("window_end_seconds"), CollisionWindow.EndTime);
		Row->SetNumberField(TEXT("hp_damage"), CollisionWindow.HPDamage); Row->SetNumberField(TEXT("stamina_damage"), CollisionWindow.StaminaDamage);
		Row->SetStringField(TEXT("source"), CollisionWindow.Source); Row->SetBoolField(TEXT("guarded"), CollisionGuarded);
		Row->SetStringField(TEXT("fixture_contract"), TEXT("Normal saved capsules. Until the first authored window ends, the QA target follows one saved baked key in the actual Monster actor frame at standing floor height. This proves the real timer/query/GE/reaction path; it does not assert gameplay targeting or actor-frame calibration accuracy."));
		Events.Add(Json(Row)); return true;
	}
	void PlaceCollisionTarget()
	{
		const FTransform Pose = FTransform(CollisionKey.Rotation.Quaternion(), CollisionKey.Center) * CollisionNode.CollisionToActor * Monster->GetActorTransform();
		FVector Location = Pose.GetLocation(); Location.Z = SavedTransform.GetLocation().Z;
		const FRotator Rotation = (Monster->GetActorLocation() - Location).GetSafeNormal2D().Rotation();
		Player->SetActorLocationAndRotation(Location, Rotation, false, nullptr, ETeleportType::TeleportPhysics);
		if (Player->GetController()) Player->GetController()->SetControlRotation(Rotation);
	}
	bool BeginCollision()
	{
		CollisionHPChangedHandle = PlayerASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).AddLambda([this](const FOnAttributeChangeData& D)
		{ if (D.NewValue < D.OldValue) { ++CollisionHPDrops; CollisionHPLoss += D.OldValue - D.NewValue; } });
		CollisionStaminaChangedHandle = PlayerASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).AddLambda([this](const FOnAttributeChangeData& D)
		{ if (D.NewValue < D.OldValue) { ++CollisionStaminaDrops; CollisionStaminaLoss += D.OldValue - D.NewValue; } });
		if (!Check(TEXT("Actual saved Monster Action activates for its public collision timer"), MonsterASC->TryActivateAbility(CollisionActionHandle) && Active(MonsterASC.Get(), CollisionActionHandle))) return false;
		CollisionCombo = Cast<UKZComboActionAbility>(MonsterASC->FindAbilitySpecFromHandle(CollisionActionHandle)->GetPrimaryInstance());
		if (!Check(TEXT("Collision producer owns the actual saved entry montage"), CollisionCombo.IsValid() && CollisionCombo->GetCurrentMontage() == CollisionNode.Montage)) return false;
		CollisionNode.Montage->GetSectionStartAndEndTime(CollisionNode.Montage->GetSectionIndex(CollisionNode.SectionName), CollisionSectionStart, CollisionSectionEnd);
		Enter(EStage::CollisionWait, CollisionNode.Montage->GetPlayLength() + PlayerDefinition->GetHitReactionSettings().ShortHits[0]->GetPlayLength() + 30.0);
		return true;
	}
	bool ObserveCollision()
	{
		const FGameplayAbilitySpecHandle Handle = FindAbility(PlayerASC.Get(), UKZHitReactionAbility::StaticClass());
		if (Active(PlayerASC.Get(), Handle))
		{
			const UKZHitReactionAbility* Hit = Cast<UKZHitReactionAbility>(PlayerASC->FindAbilitySpecFromHandle(Handle)->GetPrimaryInstance());
			const auto& Settings = PlayerDefinition->GetHitReactionSettings(); const auto& Requested = Pool(Settings, CollisionWindow.HitReaction);
			const bool HasRequested = Requested.ContainsByPredicate([](const TObjectPtr<UAnimMontage>& M) { return IsValid(M.Get()); });
			if (!CollisionSawReaction && !Check(TEXT("Actual query's accepted damage selects the saved Player reaction pool"), !CollisionGuarded && Hit &&
				(HasRequested ? Requested : Settings.ShortHits).Contains(Hit->GetCurrentMontage()))) return false;
			CollisionSawReaction = true;
		}
		if (CollisionGuarded && CollisionStaminaDrops > 0 && !CollisionSawGuard)
		{
			const FGameplayAbilitySpec* Spec = PlayerASC->FindAbilitySpecFromHandle(GuardHandle);
			const UKZGuardAbility* Guard = Spec ? Cast<UKZGuardAbility>(Spec->GetPrimaryInstance()) : nullptr;
			if (!Check(TEXT("Actual blockable query produces Guard success instead of HP damage/HitReacting"), Guard && Guard->IsActive() && CollisionHPDrops == 0 &&
				!PlayerASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting))) return false;
			CollisionSawGuard = true;
		}
		return true;
	}
	void RemoveCollisionDelegates()
	{
		if (PlayerASC.IsValid())
		{
			PlayerASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(CollisionHPChangedHandle);
			PlayerASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).Remove(CollisionStaminaChangedHandle);
		}
		CollisionHPChangedHandle.Reset(); CollisionStaminaChangedHandle.Reset();
	}
	bool TestShield()
	{
		ResetPlayer(); const float BeforeHP = HP(), BeforeStamina = Stamina(), Spend = BeforeStamina / 16.f;
		if (!Check(TEXT("Unalerted ordinary SwordShield movement cannot system-guard"), !AI->GetBattleTarget() && !Monster->TrySystemGuard(Spend, Player.Get()))) return false;
		UAIPerceptionComponent* Perception = AI->GetPerceptionComponent();
		FAIStimulus Stimulus(*GetDefault<UAISense_Sight>(), 1.f, Player->GetActorLocation(), Monster->GetActorLocation());
		Perception->RegisterStimulus(Player.Get(), Stimulus); Perception->ProcessStimuli(); // Public synthetic perception fixture, not real Sight discovery proof.
		if (!Check(TEXT("Processed public perception stimulus establishes the real controller's BattleTarget"), AI->GetBattleTarget() == Player.Get())) return false;
		if (!Check(TEXT("Positive front system guard uses the real GE and native shield reaction"), Monster->TrySystemGuard(Spend, Player.Get()))) return false;
		const FGameplayAbilitySpecHandle Handle = FindAbility(MonsterASC.Get(), UKZHitReactionAbility::StaticClass());
		UKZHitReactionAbility* Hit = Cast<UKZHitReactionAbility>(MonsterASC->FindAbilitySpecFromHandle(Handle)->GetPrimaryInstance());
		if (!Check(TEXT("Shield reaction belongs to the saved ShieldBlocks pool"), Hit && Hit->IsShieldReaction() &&
			Monster->GetCharacterDefinition()->GetHitReactionSettings().ShieldBlocks.Contains(Hit->GetCurrentMontage()))) return false;
		const FAnimMontageInstance* First = Monster->GetMesh()->GetAnimInstance()->GetActiveInstanceForMontage(Hit->GetCurrentMontage()); const int32 FirstId = First ? First->GetInstanceID() : INDEX_NONE;
		Check(TEXT("Repeated shield hit can retrigger the same per-actor native Ability"), Monster->TrySystemGuard(Spend, Player.Get()) && Hit->IsShieldReaction());
		const FAnimMontageInstance* Second = Monster->GetMesh()->GetAnimInstance()->GetActiveInstanceForMontage(Hit->GetCurrentMontage());
		Check(TEXT("Repeated shield owns a fresh montage instance and applies stamina only once per hit"), Second && Second->GetInstanceID() != FirstId && FMath::IsNearlyEqual(Stamina(), BeforeStamina - Spend * 2.f) && HP() == BeforeHP);
		MonsterASC->CancelAbilityHandle(Handle);
		Player->SetActorLocation(Monster->GetActorLocation() - Monster->GetActorForwardVector() * Settings().BrutalAttackRange, false, nullptr, ETeleportType::TeleportPhysics);
		Check(TEXT("System guard rejects a rear attacker even while BattleTarget persists"), !Monster->TrySystemGuard(Spend, Player.Get())); ResetPlayer();
		Monster->PlayHitReaction(EKZHitReactionType::Short, Player.Get()); Check(TEXT("Ordinary hit reaction is not a repeatable shield guard"), !Monster->TrySystemGuard(Spend, Player.Get())); MonsterASC->CancelAbilityHandle(Handle);
		MonsterASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), Spend);
		return Check(TEXT("Accepted shield loss can reach exactly zero without HP damage"), Monster->TrySystemGuard(Spend, Player.Get()) && Stamina() == 0.f && HP() == BeforeHP);
	}
	const FKZMonsterStaminaSettings& Settings() const { return Monster->GetCharacterDefinition()->GetMonsterStaminaSettings(); }
	float HP() const { return Value(MonsterASC.Get(), UKZAttributeSet::GetHPAttribute()); }
	float Stamina() const { return Value(MonsterASC.Get(), UKZAttributeSet::GetStaminaAttribute()); }
	bool BrutalActive() const { return Active(PlayerASC.Get(), BrutalHandle); }
	float PairMontagePosition() const { return PairMontage.IsValid() ? Player->GetMesh()->GetAnimInstance()->Montage_GetPosition(PairMontage.Get()) : 0.f; }
	bool ConfigurePair()
	{
		auto* Fixture = Field<FKZMonsterStaminaSettings>(MonsterDefinition.Get(), TEXT("MonsterStamina"));
		Check(TEXT("Saved user Brutal damage50 and original approach-duration setting are present"), Fixture->BrutalHPDamage == 50.f && FMath::IsNearlyEqual(Fixture->BrutalAlignmentSeconds, .433283f));
		PairForward = SavedTransform.GetRotation().GetForwardVector().GetSafeNormal2D();
		if (PairKind == 2)
		{
			// A separate wall must fit between the initial and final capsules. Extend only this transient QA target range.
			Fixture->BrutalAttackRange = FMath::Max(Fixture->BrutalAttackRange, Player->GetCapsuleComponent()->GetScaledCapsuleRadius() * 4.f +
				Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius());
		}
		// The public target selector uses 3D center distance. Solve XY for the actual capsule height difference.
		const double HeightDifference = Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const double RangeSquared = FMath::Square(static_cast<double>(Fixture->BrutalAttackRange));
		if (!Check(TEXT("Fixture Brutal range can contain the actual capsule center height difference"), RangeSquared > FMath::Square(HeightDifference))) return false;
		const double MaximumPlanarDistance = FMath::Sqrt(RangeSquared - FMath::Square(HeightDifference));
		const double GeometryMargin = Player->GetCapsuleComponent()->GetScaledCapsuleRadius() / 20.0; // QA clearance, not gameplay range tuning.
		const double PlanarDistance = MaximumPlanarDistance - GeometryMargin;
		const double Spacing = FMath::Max<double>(Fixture->BrutalAlignmentDistance, Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius());
		if (!Check(TEXT("Fixture leaves positive approach travel inside the unchanged 3D target range"), PlanarDistance > Spacing)) return false;
		Anchor = SavedTransform.GetLocation() + PairForward * PlanarDistance; Anchor.Z += HeightDifference;
		AnchorRotation = FRotator(0, SavedTransform.Rotator().Yaw + (BackPair ? 0.f : 180.f), 0);
		Monster->SetActorLocationAndRotation(Anchor, AnchorRotation, false, nullptr, ETeleportType::TeleportPhysics);
		const float MaxHP = FMath::Max(Value(MonsterASC.Get(), UKZAttributeSet::GetMaxHPAttribute()), Fixture->BrutalHPDamage * 2.f);
		MonsterASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), MaxHP);
		MonsterASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), PairKind == 3 ? Fixture->BrutalHPDamage : MaxHP);
		MonsterASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), 0.f);
		Monster->RequestCombatStateRefresh(); CancelStableStarted = false;
		return true;
	}
	bool BeginPair()
	{
		const float Spacing = FMath::Max(Settings().BrutalAlignmentDistance, Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius());
		PairStart = Player->GetActorLocation(); AlignmentDestination = Monster->GetActorLocation() + Monster->GetActorForwardVector().GetSafeNormal2D() * (BackPair ? -Spacing : Spacing);
		AlignmentDestination.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		if (PairKind == 2)
		{
			WallLocation = (PairStart + AlignmentDestination) * .5f;
			Wall = Player->GetWorld()->SpawnActor<AActor>(); if (!Wall.IsValid()) return Check(TEXT("Transient wall fixture spawns"), false);
			UBoxComponent* Box = NewObject<UBoxComponent>(Wall.Get()); Wall->SetRootComponent(Box);
			const float Radius = Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
			Box->SetBoxExtent(FVector(Radius / 4.f, Radius * 2.f, Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() * 2.f));
			Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Box->SetCollisionObjectType(ECC_WorldStatic);
			Box->SetCollisionResponseToAllChannels(ECR_Ignore); Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block); Box->RegisterComponent();
			Wall->SetActorLocationAndRotation(WallLocation, PairForward.Rotation());
		}
		InitialPairHP = HP(); HPDrops = PositiveRefills = 0; SawDamage1 = SawDamage2 = PairAdvanced = SawIntermediate = SawAlignmentEnd = SawRecoveryEnd = SawDeadDuringPair = SawClaimReleasedForRecovery = false;
		NoEarlyRecovery = NoEarlyFreeze = true; AlignmentError = TNumericLimits<double>::Max(); VictimDamage2Id = RecoveryEndInstanceId = INDEX_NONE;
		HPChangedHandle = MonsterASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).AddLambda([this](const FOnAttributeChangeData& D) { if (D.NewValue < D.OldValue) ++HPDrops; });
		StaminaChangedHandle = MonsterASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).AddLambda([this](const FOnAttributeChangeData& D) { if (D.NewValue > D.OldValue) ++PositiveRefills; });
		PairMontage = BackPair ? Settings().BrutalBackPlayerMontage.Get() : Settings().BrutalFrontPlayerMontage.Get();
		FCollisionQueryParams Params(SCENE_QUERY_STAT(ReactionPIEFixture), false, Player.Get()); Params.AddIgnoredActor(Monster.Get());
		FHitResult VisibilityHit;
		const bool VisibilityBlocked = Player->GetWorld()->LineTraceSingleByChannel(VisibilityHit, Player->GetActorLocation(), Monster->GetActorLocation(), ECC_Visibility, Params);
		const bool DestinationBlocked = Player->GetWorld()->OverlapBlockingTestByChannel(AlignmentDestination, FQuat::Identity, Player->GetCapsuleComponent()->GetCollisionObjectType(),
			FCollisionShape::MakeCapsule(Player->GetCapsuleComponent()->GetScaledCapsuleRadius(), Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Params);
		FObject Fixture = Object(); Fixture->SetStringField(TEXT("event"), TEXT("pair_fixture_before_activation")); Fixture->SetNumberField(TEXT("pair"), PairIndex);
		Fixture->SetNumberField(TEXT("distance_3d_cm"), FVector::Dist(Player->GetActorLocation(), Monster->GetActorLocation())); Fixture->SetNumberField(TEXT("range_cm"), Settings().BrutalAttackRange);
		Fixture->SetStringField(TEXT("player_location"), Player->GetActorLocation().ToString()); Fixture->SetStringField(TEXT("victim_location"), Monster->GetActorLocation().ToString());
		Fixture->SetNumberField(TEXT("player_capsule_half_height_cm"), Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); Fixture->SetNumberField(TEXT("victim_capsule_half_height_cm"), Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
		Fixture->SetBoolField(TEXT("grounded"), Player->GetCharacterMovement()->IsMovingOnGround()); Fixture->SetBoolField(TEXT("victim_available"), Monster->GetActiveExhaustionAbility()->IsAvailableForBrutalAttack());
		Fixture->SetBoolField(TEXT("visibility_blocked"), VisibilityBlocked); Fixture->SetBoolField(TEXT("destination_blocked"), DestinationBlocked);
		Fixture->SetStringField(TEXT("visibility_blocking_actor"), IsValid(VisibilityHit.GetActor()) ? VisibilityHit.GetActor()->GetPathName() : TEXT("")); Events.Add(Json(Fixture));
		if (!Check(TEXT("Fixture positive Brutal target is grounded, available and inside the actual 3D range"), Player->GetCharacterMovement()->IsMovingOnGround() &&
			Monster->GetActiveExhaustionAbility()->IsAvailableForBrutalAttack() && FVector::Dist(Player->GetActorLocation(), Monster->GetActorLocation()) <= Settings().BrutalAttackRange)) return false;
		if (!Check(TEXT("Fixture leaves clear target visibility and a capsule-clear final alignment location"), !VisibilityBlocked && !DestinationBlocked)) return false;
		// Pair1 supplies an existing Player->Victim entry. Native pairing must retain it after removing only its own reciprocal entry.
		if (PairIndex == 1 && !Player->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Monster.Get()))
		{ Player->GetCapsuleComponent()->IgnoreActorWhenMoving(Monster.Get(), true); FixtureAddedPlayerIgnore = true; }
		PairPriorPlayerIgnore = Player->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Monster.Get());
		PairPriorVictimIgnore = Monster->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Player.Get());
		PairIgnoresPrepared = true; PairIgnoreLifetimeOK = true; PairIgnoreObserved = false;
		Fixture->SetBoolField(TEXT("player_prior_moving_ignore"), PairPriorPlayerIgnore); Fixture->SetBoolField(TEXT("victim_prior_moving_ignore"), PairPriorVictimIgnore);
		Fixture->SetBoolField(TEXT("fixture_added_preexisting_player_ignore"), FixtureAddedPlayerIgnore);
		const bool Activated = PlayerASC->TryActivateAbility(BrutalHandle);
		Fixture->SetBoolField(TEXT("activation_accepted"), Activated); Fixture->SetBoolField(TEXT("attacker_active_after_activation"), BrutalActive());
		Fixture->SetBoolField(TEXT("victim_claimed_after_activation"), Monster->GetActiveExhaustionAbility() && Monster->GetActiveExhaustionAbility()->HasBrutalPartner());
		if (!Check(TEXT("Actual Brutal activation claims the selected exhausted victim"), Activated && BrutalActive() && Monster->GetActiveExhaustionAbility() && Monster->GetActiveExhaustionAbility()->HasBrutalPartner())) return false;
		PairIgnoreObserved = Player->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Monster.Get()) &&
			Monster->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Player.Get());
		if (!Check(TEXT("Actual claim establishes reciprocal capsule moving ignores"), PairIgnoreObserved)) return false;
		Check(TEXT("Brutal activation preserves initial location instead of teleporting"), Player->GetActorLocation().Equals(PairStart, UE_KINDA_SMALL_NUMBER));
		Check(TEXT("Front/back selects the actual saved attacker montage"), Player->GetMesh()->GetAnimInstance()->GetCurrentActiveMontage() == PairMontage.Get()); return true;
	}
	void CheckPlayerPairReleased()
	{
		Check(TEXT("Pair end/cancel releases only attacker-owned tags and constraint"), !BrutalActive() &&
			PlayerASC->GetTagCount(KZGameplayTags::Block_Movement_Input) == PlayerMovementBaseline && PlayerASC->GetTagCount(KZGameplayTags::Block_StaminaRegen) == PlayerRegenBaseline &&
			Player->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::LockOn);
		if (PairIgnoresPrepared)
		{
			Check(TEXT("Actual paired execution retains reciprocal moving ignores until both reactions release the claim"), PairIgnoreLifetimeOK && PairIgnoreObserved);
			Check(TEXT("Pair end/cancel restores both pre-claim moving-ignore memberships"),
				Player->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Monster.Get()) == PairPriorPlayerIgnore &&
				Monster->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Player.Get()) == PairPriorVictimIgnore);
		}
	}
	void OnPostTick(UWorld* World, ELevelTick, float)
	{
		if (!Player.IsValid() || Player->GetWorld() != World) return;
		if (Stage == EStage::CollisionWait && Monster.IsValid())
		{
			ObserveCollision();
			const float Position = Monster->GetMesh()->GetAnimInstance()->Montage_GetPosition(CollisionNode.Montage) - CollisionSectionStart;
			if (Active(MonsterASC.Get(), CollisionActionHandle) && Position <= CollisionWindow.EndTime)
				PlaceCollisionTarget();
			else if (!CollisionTargetRemoved)
			{
				// The single window's dense samples have all run. Move only the QA target out before any later authored node.
				double Distance = 0.0; for (const FKZAttackCollisionKey& Key : CollisionWindow.Keys) Distance = FMath::Max(Distance, Key.Center.Size());
				Distance += CollisionNode.CollisionToActor.GetTranslation().Size() + CollisionWindow.Extent.Size() + Settings().BrutalAttackRange + Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
				FVector Away = Monster->GetActorLocation() - Monster->GetActorForwardVector() * Distance; Away.Z = SavedTransform.GetLocation().Z;
				Player->SetActorLocation(Away, false, nullptr, ETeleportType::TeleportPhysics); CollisionTargetRemoved = true;
			}
		}
		if (Stage == EStage::ReactionWait && Subject() && Montage.IsValid())
		{
			UAnimInstance* Anim = SubjectAnim(); const float Position = Anim->Montage_GetPosition(Montage.Get());
			if (HitActive())
			{
				SawAdvance |= Position > 0.f; SeenSections.Add(Anim->Montage_GetCurrentSection(Montage.Get()));
				const bool Flying = Subject()->GetCharacterMovement()->MovementMode == MOVE_Flying; SawFlying |= Flying;
				const TSharedPtr<FRootMotionSource> Force = Subject()->GetCharacterMovement()->GetRootMotionSourceByID(ReactionSourceId);
				const bool ForceLive = Force.IsValid() && !Force->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval);
				SawOwnMotion |= ForceLive; SawForceFinishWhileActive |= ExpectedForce && SawOwnMotion && !ForceLive;
				if (Position >= PreviousMontagePosition)
				{
					// Actual position interval in the same bound instance proves automatic short-section traversal even between rendered ticks.
					if (const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage.Get()); Instance && Instance->GetInstanceID() == MontageInstanceId)
						for (int32 Index = 0; Index < Montage->CompositeSections.Num(); ++Index)
						{ float Start, End; Montage->GetSectionStartAndEndTime(Index, Start, End); if (Position > Start && PreviousMontagePosition < End) TimelineSections.Add(Montage->CompositeSections[Index].SectionName); }
					FAnimExtractContext Context(Position, true);
					const FTransform Local = Montage->ExtractRootMotionFromTrackRange(PreviousMontagePosition, Position, Context);
					RootPath += Subject()->GetMesh()->ConvertLocalRootMotionToWorld(Local).GetTranslation().Size(); PreviousMontagePosition = Position;
				}
				const FVector Delta = Subject()->GetActorLocation() - ReactionStartLocation;
				RootMaxDisplacement = FMath::Max(RootMaxDisplacement, Delta.Size()); RootMaxPlanar = FMath::Max(RootMaxPlanar, Delta.Size2D());
				RootMaxRise = FMath::Max(RootMaxRise, Delta.Z);
				if (Position >= Montage->GetPlayLength() * .5f || ExpectedForce && RootMaxPlanar > UE_KINDA_SMALL_NUMBER)
				{
					const EKZHitReactionType Type = Cases[CaseIndex].Type;
					if (CurrentSubject == 0 && (Type != EKZHitReactionType::Launch || RootMaxRise >= ExpectedMotionHeight * .5))
						Capture(Type == EKZHitReactionType::Short ? TEXT("PlayerShort") : Type == EKZHitReactionType::Knockback ? TEXT("PlayerKnockback") : TEXT("PlayerLaunch"), Subject());
					if (CurrentSubject == 4 && Type == EKZHitReactionType::Launch && RootMaxRise >= ExpectedMotionHeight * .5) Capture(TEXT("HalberdEliteLaunch"), Subject());
					if ((CurrentSubject == 5 || CurrentSubject == 6) && Type == EKZHitReactionType::Knockback) Capture(CurrentSubject == 5 ? TEXT("ApesFallback") : TEXT("YetugaFallback"), Subject());
				}
			}
		}
		if (Stage != EStage::PairWait || !Monster.IsValid()) return;
		if (BrutalActive() || Monster->GetActiveExhaustionAbility() && Monster->GetActiveExhaustionAbility()->HasBrutalPartner())
		{
			const bool BothIgnored = Player->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Monster.Get()) &&
				Monster->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Player.Get());
			PairIgnoreObserved |= BothIgnored; PairIgnoreLifetimeOK &= BothIgnored;
		}
		UAnimInstance* VictimAnim = Monster->GetMesh()->GetAnimInstance(); UAnimMontage* VictimMontage = VictimAnim->GetCurrentActiveMontage();
		const FName Section = VictimMontage ? VictimAnim->Montage_GetCurrentSection(VictimMontage) : NAME_None;
		const UAnimMontage* ExpectedVictim = BackPair ? Settings().BrutalBackVictimMontage.Get() : Settings().BrutalFrontVictimMontage.Get();
		if (VictimMontage == ExpectedVictim)
		{
			SawDamage1 |= Section == TEXT("Damage1"); SawDamage2 |= Section == TEXT("Damage2");
			if (Section == TEXT("Damage2")) if (const FAnimMontageInstance* Instance = VictimAnim->GetActiveInstanceForMontage(VictimMontage)) VictimDamage2Id = Instance->GetInstanceID();
		}
		RememberRecoveryEnd(VictimAnim);
		const bool VictimRemaining = VictimDamage2Id != INDEX_NONE && VictimAnim->GetMontageInstanceForID(VictimDamage2Id);
		if (BrutalActive())
		{
			const float Position = PairMontagePosition(); PairAdvanced |= Position > 0.f;
			if (PairIndex == 5 && Position >= .03356f + Settings().BrutalAlignmentSeconds * .5f) Capture(TEXT("HeavyBackPairedMiddle"), Monster.Get(), true);
			const double FullDistance = FVector::Dist(PairStart, AlignmentDestination), Moved = FVector::Dist(PairStart, Player->GetActorLocation());
			if (Position >= .03356f && Position < .03356f + Settings().BrutalAlignmentSeconds)
				SawIntermediate |= Moved > UE_KINDA_SMALL_NUMBER && Moved < FullDistance - UE_KINDA_SMALL_NUMBER;
			if (!SawAlignmentEnd && Position >= .03356f + Settings().BrutalAlignmentSeconds)
			{ SawAlignmentEnd = true; AlignmentError = FVector::Dist(Player->GetActorLocation(), AlignmentDestination); }
		}
		if (BrutalActive() || VictimRemaining)
		{
			NoEarlyRecovery &= Stamina() == 0.f && !SawRecoveryEnd;
			if (HP() <= 0.f)
			{
				SawDeadDuringPair |= MonsterASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead);
				NoEarlyFreeze &= !Monster->GetMesh()->bPauseAnims && Monster->GetActiveExhaustionAbility() && Monster->GetActiveExhaustionAbility()->HasBrutalPartner();
			}
		}
	}
	void Evidence(const TCHAR* Kind)
	{
		FObject Row = Object(); Row->SetStringField(TEXT("event"), Kind); Row->SetNumberField(TEXT("case"), CaseIndex); Row->SetNumberField(TEXT("pair"), PairIndex);
		Row->SetNumberField(TEXT("subject"), CurrentSubject); Row->SetStringField(TEXT("montage"), Montage.IsValid() ? Montage->GetPathName() : TEXT(""));
		Row->SetNumberField(TEXT("extracted_world_path_cm"), RootPath); Row->SetNumberField(TEXT("observed_root_displacement_cm"), RootMaxDisplacement);
		TArray<TSharedPtr<FJsonValue>> Observed, Traversed;
		for (FName Section : SeenSections) Observed.Add(MakeShared<FJsonValueString>(Section.ToString()));
		for (FName Section : TimelineSections) Traversed.Add(MakeShared<FJsonValueString>(Section.ToString()));
		Row->SetArrayField(TEXT("sections_observed_at_sample"), Observed); Row->SetArrayField(TEXT("sections_traversed_by_actual_position_interval"), Traversed);
		Row->SetNumberField(TEXT("observed_planar_cm"), RootMaxPlanar); Row->SetNumberField(TEXT("observed_rise_cm"), RootMaxRise);
		Row->SetBoolField(TEXT("expected_owned_rms"), ExpectedForce); Row->SetBoolField(TEXT("observed_owned_rms"), SawOwnMotion);
		Row->SetNumberField(TEXT("alignment_error_cm"), AlignmentError < TNumericLimits<double>::Max() ? AlignmentError : -1.0);
		Row->SetNumberField(TEXT("hp_drops"), HPDrops); Row->SetNumberField(TEXT("positive_refills"), PositiveRefills); Events.Add(Json(Row));
	}
	void ResetMonster()
	{
		if (MonsterASC.IsValid())
		{
			MonsterASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(HPChangedHandle);
			MonsterASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).Remove(StaminaChangedHandle);
			MonsterASC->CancelAllAbilities();
		}
		HPChangedHandle.Reset(); StaminaChangedHandle.Reset();
		// Remove only the preexisting peer entry deliberately introduced by this fixture, after native cancellation cleanup.
		if (FixtureAddedPlayerIgnore && Player.IsValid() && Monster.IsValid()) Player->GetCapsuleComponent()->IgnoreActorWhenMoving(Monster.Get(), false);
		FixtureAddedPlayerIgnore = PairIgnoresPrepared = false;
		if (Wall.IsValid()) Wall->Destroy(); Wall.Reset();
		if (Monster.IsValid())
		{
			Monster->GetLocomotionComponent()->ReleaseMovementConstraint(MonsterForeign);
			if (FixtureIntent.IsValid()) Monster->GetLocomotionComponent()->EndLocomotionIntentSource(FixtureIntent);
			Monster->Destroy();
		}
		MonsterForeign.Reset(); FixtureIntent.Reset(); if (AI.IsValid()) AI->Destroy(); AI.Reset(); Monster.Reset(); MonsterASC.Reset(); MonsterDefinition.Reset();
	}
	void Cleanup()
	{
		if (Cleaned) return; Cleaned = true; FWorldDelegates::OnWorldPostActorTick.Remove(PostTickHandle);
		FScreenshotRequest::OnScreenshotRequestProcessed().Remove(ScreenshotProcessedHandle); RestoreCaptureCamera();
		if (CaptureCamera.IsValid()) CaptureCamera->Destroy(); CaptureCamera.Reset(); RemoveCollisionDelegates(); ResetMonster();
		if (PlayerASC.IsValid()) { Cancel(PlayerASC.Get()); PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard); PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_X); }
		if (Player.IsValid())
		{
			Player->GetLocomotionComponent()->ReleaseMovementConstraint(PlayerForeign); Player->HandleInputMoveReleased();
			SetDefinition(Player.Get(), const_cast<UKZCharacterDefinitionData*>(OriginalPlayerDefinition)); Player->GetMesh()->VisibilityBasedAnimTickOption = SavedTickOption;
			if (Player->GetMesh()->GetAnimInstance()) Player->GetMesh()->GetAnimInstance()->SetRootMotionMode(SavedRootMotionMode);
			Player->GetCharacterMovement()->StopMovementImmediately(); Player->SetActorTransform(SavedTransform, false, nullptr, ETeleportType::TeleportPhysics);
			Player->GetCharacterMovement()->SetMovementMode(SavedMode, SavedCustomMode); if (Player->GetController()) Player->GetController()->SetControlRotation(SavedControlRotation);
			if (PlayerASC.IsValid())
			{
				PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), SavedMaxHP); PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(), SavedMaxStamina);
				PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), SavedHP); PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), SavedStamina);
			}
		}
		PlayerDefinition.Reset();
		for (const FSavedAI& Saved : SavedAIs) if (Saved.AI.IsValid())
		{
			Saved.AI->SetActorTickEnabled(Saved.Tick); if (Saved.Tree && Saved.AI->GetStateTreeComponent()) Saved.AI->GetStateTreeComponent()->StartLogic();
			if (Saved.AI->GetPerceptionComponent()) Saved.AI->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), Saved.Sight);
		}
	}
	bool Finish()
	{
		Cleanup(); FObject Report = Object(); Report->SetBoolField(TEXT("success"), !Test->HasAnyErrors()); Report->SetStringField(TEXT("test"), TEXT("Khazan.Combat.ReactionPIE"));
		Report->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601()); Report->SetNumberField(TEXT("process_id"), FPlatformProcess::GetCurrentProcessId());
		Report->SetBoolField(TEXT("authored_assets_modified"), false); Report->SetBoolField(TEXT("private_completion_mutated"), false);
		Report->SetNumberField(TEXT("completed_reaction_cases"), CaseIndex); Report->SetNumberField(TEXT("completed_pair_cases"), CompletedPairs); Report->SetNumberField(TEXT("observed_reaction_variants"), Variants.Num());
		Report->SetNumberField(TEXT("pair_only_index"), PairOnlyIndex); Report->SetBoolField(TEXT("partial_scope"), PairOnlyIndex != INDEX_NONE); Report->SetNumberField(TEXT("completed_collision_cases"), CollisionIndex);
		Report->SetBoolField(TEXT("native_rhi_screenshots_enabled"), CaptureScreenshots); Report->SetNumberField(TEXT("native_rhi_screenshots_requested"), CapturedLabels.Num());
		Report->SetArrayField(TEXT("checks"), Checks); Report->SetArrayField(TEXT("definition_audits"), Audits); Report->SetArrayField(TEXT("evidence"), Events);
		Report->SetStringField(TEXT("limits"), TEXT("Public native gameplay entries in isolated PIE; no physical input or visual contact-quality claim. Synthetic public processed perception establishes positive shield BattleTarget, not real Sight acquisition. Original definitions are untouched; only transient copies have indefinite exhaustion/null fallback/wall-range QA settings. Current engine-extracted world path plus capsule geometry is a conservative root-scale regression bound, not original animation-source numerical equality. Guard RNG trials are QA sampling, not a gameplay probability guarantee."));
		FString Text; FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
		const FString Filename = FPaths::ProjectDir() / TEXT("Metadata/CombatReaction_20261008/NativePIE.json"); IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true);
		if (!FFileHelper::SaveStringToFile(Text, *Filename, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)) Test->AddError(TEXT("Cannot write combat reaction PIE evidence"));
		Test->AddInfo(FString(TEXT("Combat reaction native evidence: ")) + FPaths::ConvertRelativePathToFull(Filename)); return true;
	}
	FAutomationTestBase* Test; TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<UKZAbilitySystemComponent> PlayerASC, MonsterASC;
	TWeakObjectPtr<AKZMonster> Monster; TWeakObjectPtr<AKZMonsterAIController> AI; TWeakObjectPtr<AActor> Wall;
	TWeakObjectPtr<ACameraActor> CaptureCamera; TWeakObjectPtr<AActor> OriginalViewTarget; FDelegateHandle ScreenshotProcessedHandle; TSet<FString> CapturedLabels; bool CaptureScreenshots = false;
	const UKZCharacterDefinitionData* OriginalPlayerDefinition = nullptr; TStrongObjectPtr<UKZCharacterDefinitionData> PlayerDefinition, MonsterDefinition;
	FKZMovementConstraintHandle PlayerForeign, MonsterForeign; FKZLocomotionIntentHandle FixtureIntent;
	FGameplayAbilitySpecHandle BrutalHandle, GuardHandle, HitHandle; FDelegateHandle PostTickHandle, HPChangedHandle, StaminaChangedHandle;
	FGameplayAbilitySpecHandle CollisionActionHandle; FDelegateHandle CollisionHPChangedHandle, CollisionStaminaChangedHandle;
	TWeakObjectPtr<UKZComboActionAbility> CollisionCombo; FKZComboNode CollisionNode; FKZAttackCollisionWindow CollisionWindow; FKZAttackCollisionKey CollisionKey; FString CollisionDefinition;
	TWeakObjectPtr<UAnimMontage> Montage, PairMontage, LastPlayerMontage, LastVictimMontage; TArray<FReactionCase> Cases; TArray<FSavedAI> SavedAIs;
	TSet<FName> ExpectedSections, SeenSections, TimelineSections, GuardSections; TSet<FString> Variants;
	FTransform SavedTransform; FRotator SavedControlRotation, AnchorRotation; FVector Anchor, ReactionStartLocation, PairStart, AlignmentDestination, PairForward, WallLocation, CancelLocation;
	EMovementMode SavedMode = MOVE_None; uint8 SavedCustomMode = 0; EVisibilityBasedAnimTickOption SavedTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	ERootMotionMode::Type SavedRootMotionMode = ERootMotionMode::RootMotionFromMontagesOnly, ReactionRootMotionMode = ERootMotionMode::RootMotionFromMontagesOnly;
	uint16 ReactionSourceId = static_cast<uint16>(ERootMotionSourceID::Invalid);
	float SavedHP = 0, SavedMaxHP = 0, SavedStamina = 0, SavedMaxStamina = 0, PreviousMontagePosition = 0, InitialPairHP = 0, LastPlayerPosition = -1, LastVictimPosition = -1;
	double Deadline = 0, StageDeadline = 0, StageStarted = 0, RootPath = 0, RootMaxDisplacement = 0, RootMaxPlanar = 0, RootMaxRise = 0, ExpectedMotionDistance = 0, ExpectedMotionHeight = 0, AlignmentError = TNumericLimits<double>::Max(), CancelObserveAt = 0;
	int32 CaseIndex = 0, CurrentSubject = 0, CurrentFamily = INDEX_NONE, PairIndex = 0, PairKind = 0, MontageInstanceId = INDEX_NONE, VictimDamage2Id = INDEX_NONE, RecoveryEndInstanceId = INDEX_NONE;
	int32 PlayerMovementBaseline = 0, PlayerRegenBaseline = 0, MonsterMovementBaseline = 0, MonsterRegenBaseline = 0, HPDrops = 0, PositiveRefills = 0;
	int32 PairOnlyIndex = INDEX_NONE, CompletedPairs = 0, CollisionIndex = 0;
	int32 CollisionHPDrops = 0, CollisionStaminaDrops = 0; float CollisionHPLoss = 0, CollisionStaminaLoss = 0, CollisionSectionStart = 0, CollisionSectionEnd = 0;
	bool CollisionGuarded = false, CollisionSawReaction = false, CollisionSawGuard = false, CollisionTargetRemoved = false;
	EStage Stage = EStage::Init; bool Cleaned = false, SawAdvance = false, SawFlying = false, BackPair = false, CancelStableStarted = false;
	bool ExpectedForce = false, SawOwnMotion = false, SawForceFinishWhileActive = false;
	bool SawDamage1 = false, SawDamage2 = false, PairAdvanced = false, SawIntermediate = false, SawAlignmentEnd = false, SawRecoveryEnd = false;
	bool NoEarlyRecovery = true, NoEarlyFreeze = true, SawDeadDuringPair = false;
	bool SawClaimReleasedForRecovery = false;
	bool PairIgnoresPrepared = false, PairPriorPlayerIgnore = false, PairPriorVictimIgnore = false, FixtureAddedPlayerIgnore = false;
	bool PairIgnoreLifetimeOK = true, PairIgnoreObserved = false;
	TArray<TSharedPtr<FJsonValue>> Checks, Audits, Events;
};

class FWait : public IAutomationLatentCommand
{
public:
	explicit FWait(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 30.0) {}
	virtual bool Update() override
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			UWorld* World = Context.World(); if (Context.WorldType != EWorldType::PIE || !World || !World->HasBegunPlay()) continue;
			for (TActorIterator<AKZPlayer> It(World); It; ++It)
				if (It->IsPlayerControlled() && It->GetController() && It->GetCharacterDefinition() && It->GetMesh()->GetAnimInstance() &&
					It->GetCharacterMovement()->IsMovingOnGround() && Cast<UKZAbilitySystemComponent>(It->GetAbilitySystemComponent()))
				{ FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FProbe>(Test, *It)); return true; }
		}
		if (FPlatformTime::Seconds() < Deadline) return false;
		Test->AddError(TEXT("No ready possessed Player in owned Work PIE. Start PIE after TestStarted.")); return true;
	}
private: FAutomationTestBase* Test; double Deadline;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatReactionPIETest, "Khazan.Combat.ReactionPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZCombatReactionPIETest::RunTest(const FString&)
{
	if (!FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()), KZCombatReactionPIE::WorkRoot))
	{ AddError(TEXT("Combat Reaction PIE is restricted to the exact isolated MonsterWork project")); return false; }
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZCombatReactionPIE::FWait>(this)); return true;
}
#endif
