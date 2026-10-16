#include "AI/KZMonsterAIController.h"
#include "Ability/KZHitReactionAbility.h"
#include "KZGameplayTags.h"

#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Components/StateTreeAIComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Sight.h"
#include "Perception/AISense_Sight.h"
#include "Engine/World.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Kismet/KismetMathLibrary.h"

AKZMonsterAIController::AKZMonsterAIController()
{
	PrimaryActorTick.bCanEverTick = true;
	bAllowStrafe = true;
	StateTreeComponent = CreateDefaultSubobject<UStateTreeAIComponent>(TEXT("MonsterStateTree"));
	StateTreeComponent->SetStartLogicAutomatically(false);
	BrainComponent = StateTreeComponent;
	MonsterPerception = CreateDefaultSubobject<UAIPerceptionComponent>(TEXT("MonsterPerception"));
	SetPerceptionComponent(*MonsterPerception);
	SightConfig = CreateDefaultSubobject<UAISenseConfig_Sight>(TEXT("MonsterSight"));
	SightConfig->DetectionByAffiliation.bDetectEnemies = true;
	SightConfig->DetectionByAffiliation.bDetectFriendlies = true;
	SightConfig->DetectionByAffiliation.bDetectNeutrals = true;
	MonsterPerception->ConfigureSense(*SightConfig);
	MonsterPerception->SetDominantSense(UAISense_Sight::StaticClass());
	MonsterPerception->OnTargetPerceptionUpdated.AddDynamic(this, &ThisClass::HandleTargetPerception);
}

AKZMonster* AKZMonsterAIController::GetMonster() const { return Cast<AKZMonster>(GetPawn()); }

FRotator AKZMonsterAIController::GetDesiredRotation() const
{
	const AKZMonster* Monster = GetMonster();
	const AActor* Target = BattleTarget.Get();
	const UKZLocomotionComponent* Locomotion = BoundLocomotion.Get();
	if (!Monster || !Target || !Locomotion ||
		Locomotion->GetResolvedMovementPolicy().ResolvedRotationMode != EKZRotationMode::LockOn)
	{
		return Super::GetDesiredRotation();
	}

	const FRotator BodyRotation = Monster->GetActorRotation();
	const FVector ToTarget = (Target->GetActorLocation() - Monster->GetActorLocation()).GetSafeNormal2D();
	if (ToTarget.IsNearlyZero()) return BodyRotation;
	FRotator Desired(0.f, UKismetMathLibrary::FindLookAtRotation(Monster->GetActorLocation(), Target->GetActorLocation()).Yaw, 0.f);
	const UAbilitySystemComponent* ASC = Monster->GetAbilitySystemComponent();
	const UKZComboActionAbility* Attack = ASC ? Cast<UKZComboActionAbility>(ASC->GetAnimatingAbility()) : nullptr;
	if (!Attack || !Attack->IsActive() || !Monster->GetAttackAbilities().Contains(Attack->GetClass()))
	{
		// Unaware/alert root turns keep their authored rotation. Ordinary combat movement faces the live target.
		return Monster->GetCharacterMovement()->HasAnimRootMotion() ? BodyRotation : Desired;
	}

	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	const UAnimInstance* Anim = Monster->GetMesh()->GetAnimInstance();
	// Presentation overlays are independent of the executing attack timeline.
	const UAnimMontage* Montage = Anim ? Attack->GetCurrentMontage() : nullptr;
	bool bPreparing = Attack->IsApproachingComboTransition(Settings.AttackPreparationSeconds);
	if (Montage)
	{
		const float Position = Anim->Montage_GetPosition(Montage);
		const int32 Section = Montage->GetSectionIndexFromPosition(Position);
		const float PlayRate = Anim->Montage_GetEffectivePlayRate(Montage);
		bPreparing |= Section != INDEX_NONE && PlayRate > 0.f &&
			(Position - Montage->GetAnimCompositeSection(Section).GetTime()) / PlayRate < Settings.AttackPreparationSeconds;
	}
	const float Rate = bPreparing ? Settings.ComboReaimYawRate : Settings.AttackTrackingYawRate;
	// Wrap-safe constant angular speed, no capsule snap and no replacement of locomotion RotationRate.
	Desired.Yaw = UKismetMathLibrary::FixedTurn(BodyRotation.Yaw, Desired.Yaw, FMath::Max(0.f, Rate) * GetWorld()->GetDeltaSeconds());
	return Desired;
}

void AKZMonsterAIController::BeginPlay()
{
	Super::BeginPlay();
	StartMonsterLogic();
}

void AKZMonsterAIController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	HomeLocation = InPawn->GetActorLocation();
	if (HasActorBegunPlay()) StartMonsterLogic();
}

void AKZMonsterAIController::StartMonsterLogic()
{
	AKZMonster* Monster = GetMonster();
	if (!Monster || !HasAuthority() || BoundLocomotion.IsValid() || !Monster->GetAIStateTree() || !Monster->GetCharacterDefinition()) return;
	UKZLocomotionComponent* Locomotion = Monster->GetLocomotionComponent();
	IntentHandle = Locomotion->BeginLocomotionIntentSource(this, EKZLocomotionIntentSource::AIController);
	if (!IntentHandle.IsValid()) return;
	BoundLocomotion = Locomotion;
	MovementPermissionHandle = Locomotion->OnMovementInputPermissionChanged().AddUObject(this, &ThisClass::HandleMovementPermissionChanged);
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	SightConfig->SightRadius = Settings.SightRadius;
	SightConfig->LoseSightRadius = FMath::Max(Settings.SightRadius, Settings.LoseSightRadius);
	SightConfig->PeripheralVisionAngleDegrees = Settings.PeripheralVisionHalfAngle;
	// MaxAge governs the sensory record; an acquired BattleTarget persists independently.
	SightConfig->SetMaxAge(Settings.TargetMemorySeconds);
	MonsterPerception->ConfigureSense(*SightConfig);
	MonsterPerception->RequestStimuliListenerUpdate();
	if (!Monster->GetDamagePassives().IsEmpty())
	{
		PassiveASC = Monster->GetAbilitySystemComponent();
		if (PassiveASC.IsValid()) DamagePassiveHandle = PassiveASC->OnGameplayEffectAppliedDelegateToSelf.AddUObject(this, &ThisClass::HandleAcceptedDamage);
	}
	StateTreeComponent->SetStateTree(Monster->GetAIStateTree());
	StateTreeComponent->StartLogic();
}

void AKZMonsterAIController::ReleaseMonsterLogic()
{
	if (PassiveASC.IsValid()) PassiveASC->OnGameplayEffectAppliedDelegateToSelf.Remove(DamagePassiveHandle);
	DamagePassiveHandle.Reset(); PassiveASC.Reset(); RecentDamageTimes.Reset(); PendingDamageSkill = NAME_None;
	StateTreeComponent->StopLogic(TEXT("Monster controller lifetime ended"));
	bPausedForCombatReaction = false;
	StopRequestedMove();
	if (UKZLocomotionComponent* Locomotion = BoundLocomotion.Get())
	{
		Locomotion->OnMovementInputPermissionChanged().Remove(MovementPermissionHandle);
		Locomotion->EndLocomotionIntentSource(IntentHandle);
	}
	MovementPermissionHandle.Reset();
	IntentHandle.Reset();
	BoundLocomotion.Reset();
	BattleTarget.Reset();
	AlertedTarget.Reset();
	LastAttackClass.Reset();
	NextAttackAt = 0.f;
	PatternReadyAt.Reset();
	EncounterStartedAt = -1.f;
	RangedChoiceFrame = MAX_uint64;
	bRangedChoice = false;
	ClearFocus(EAIFocusPriority::Gameplay);
}

void AKZMonsterAIController::OnUnPossess()
{
	ReleaseMonsterLogic();
	Super::OnUnPossess();
}

void AKZMonsterAIController::EndPlay(const EEndPlayReason::Type Reason)
{
	ReleaseMonsterLogic();
	Super::EndPlay(Reason);
}

void AKZMonsterAIController::HandleTargetPerception(AActor* Actor, FAIStimulus Stimulus)
{
	const AKZPlayer* Player = Cast<AKZPlayer>(Actor);
	if (!Player || !Player->IsPlayerControlled() || !GetMonster()) return;
	if (Stimulus.WasSuccessfullySensed())
	{
		if (!BattleTarget.IsValid() || BattleTarget == Actor)
		{
			BattleTarget = Actor;
			if (EncounterStartedAt < 0.f) EncounterStartedAt = GetWorld()->GetTimeSeconds();
			SetFocus(Actor, EAIFocusPriority::Gameplay);
			if (AKZMonster* Partner = GetMonster()->GetTalkPartner(); Partner && GetMonster()->HasActiveTalkLoop() && Partner->HasActiveTalkLoop())
			{
				if (AKZMonsterAIController* OtherAI = Cast<AKZMonsterAIController>(Partner->GetController()); OtherAI && !OtherAI->BattleTarget.IsValid())
				{
					OtherAI->BattleTarget = Actor;
					OtherAI->SetFocus(Actor, EAIFocusPriority::Gameplay);
				}
			}
		}
	}
	// Sight loss ends the sensory observation, not the encounter with this valid player.
}

void AKZMonsterAIController::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// APawn can auto-possess inside Super::PostInitializeComponents, before Definition initialization.
	if (!BoundLocomotion.IsValid()) StartMonsterLogic();
	const AKZMonster* Monster = GetMonster();
	if (!Monster) return;
	if (!PendingDamageSkill.IsNone())
	{
		UAbilitySystemComponent* ASC = Monster->GetAbilitySystemComponent();
		if (GetWorld()->GetTimeSeconds() > PendingDamageUntil || !ASC ||
			ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) || ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted))
			PendingDamageSkill = NAME_None;
		else
		{
			// Source bOnlyDamageStateCancel / GroundDamage: cancel only this
			// actual short reaction. StateTree consumes the pending SideMove.
			FScopedAbilityListLock AbilityListLock(*ASC);
			for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
				if (auto* Hit = Cast<UKZHitReactionAbility>(Spec.GetPrimaryInstance()); Hit && Hit->IsGroundHitReaction())
				{
					ASC->CancelAbilityHandle(Spec.Handle);
					break;
				}
		}
	}
	// Preserve BattleTarget while incapacitated; the ASC/resources own this policy.
	if (Monster->IsCombatIncapacitated())
	{
		if (!StateTreeComponent->IsPaused())
		{
			StateTreeComponent->PauseLogic(TEXT("Monster incapacitated"));
			bPausedForCombatReaction = StateTreeComponent->IsPaused();
		}
		StopRequestedMove();
	}
	else if (bPausedForCombatReaction)
	{
		if (StateTreeComponent->IsPaused()) StateTreeComponent->ResumeLogic(TEXT("Monster recovered"));
		bPausedForCombatReaction = false;
	}
	if (!BattleTarget.IsValid())
	{
		BattleTarget.Reset();
		AlertedTarget.Reset();
		ClearFocus(EAIFocusPriority::Gameplay);
	}
	else SetFocus(BattleTarget.Get(), EAIFocusPriority::Gameplay);
	MirrorNavigationIntent();
	if (DirectMoveGoal.IsSet() && BoundLocomotion.IsValid() && BoundLocomotion->IsMovementInputAllowed())
		GetPawn()->AddMovementInput(BoundLocomotion->GetLocomotionIntent().MoveInputWorld);
}

bool AKZMonsterAIController::HasPendingDamagePassive() const
{
	return !PendingDamageSkill.IsNone() && GetWorld() && GetWorld()->GetTimeSeconds() <= PendingDamageUntil &&
		GetMonster() && !GetMonster()->IsCombatIncapacitated();
}

FName AKZMonsterAIController::TakePendingDamagePassive()
{
	if (!HasPendingDamagePassive()) return NAME_None;
	const FName Skill = PendingDamageSkill;
	PendingDamageSkill = NAME_None;
	RecentDamageTimes.Reset(); // One accepted request consumes this history, not every tick.
	return Skill;
}

void AKZMonsterAIController::HandleAcceptedDamage(UAbilitySystemComponent* Target, const FGameplayEffectSpec& Spec, FActiveGameplayEffectHandle Handle)
{
	AKZMonster* Monster = GetMonster();
	if (!Monster || Target != PassiveASC.Get() || !BattleTarget.IsValid() ||
		Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), false, 0.f) >= 0.f ||
		Target->HasMatchingGameplayTag(KZGameplayTags::State_Dead) || Target->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted)) return;
	const float Now = GetWorld()->GetTimeSeconds();
	RecentDamageTimes.Add(Now);
	float Longest = 0.f;
	for (const auto& Row : Monster->GetDamagePassives()) Longest = FMath::Max(Longest, Row.HitWindowSeconds);
	RecentDamageTimes.RemoveAll([Now, Longest](float Time) { return Now - Time > Longest; });
	if (!PendingDamageSkill.IsNone() && Now <= PendingDamageUntil) return;
	for (const auto& Row : Monster->GetDamagePassives())
	{
		const int32 Count = RecentDamageTimes.FilterByPredicate([Now, &Row](float Time) { return Now - Time <= Row.HitWindowSeconds; }).Num();
		// Native count comparator/reset is unavailable; >= and consumed-history
		// semantics are the explicit project adapter, not a verified native claim.
		if (Count >= Row.HitCount && Row.HitCount > 0 && FMath::FRand() < Row.Chance)
		{
			PendingDamageSkill = Row.Skill;
			PendingDamageUntil = Now + Row.PendingSeconds;
			break;
		}
	}
}

float AKZMonsterAIController::GetTargetDistance() const
{
	return BattleTarget.IsValid() && GetPawn() ? FVector::Dist2D(GetPawn()->GetActorLocation(), BattleTarget->GetActorLocation()) : TNumericLimits<float>::Max();
}

bool AKZMonsterAIController::NeedsAlert() const { return BattleTarget.IsValid() && BattleTarget != AlertedTarget; }

bool AKZMonsterAIController::CanChooseAttack() const
{
	const AKZMonster* Monster = GetMonster();
	if (!Monster || !BattleTarget.IsValid() || NeedsAlert() || GetWorld()->GetTimeSeconds() < NextAttackAt) return false;
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	const FVector Direction = (BattleTarget->GetActorLocation() - Monster->GetActorLocation()).GetSafeNormal2D();
	if (!Monster->GetCombatPatterns().IsEmpty()) return SelectCombatPattern(false) != nullptr;
	return GetTargetDistance() <= Settings.AttackDistance &&
		FVector::DotProduct(Monster->GetActorForwardVector(), Direction) >= FMath::Cos(FMath::DegreesToRadians(Settings.AttackFacingHalfAngle));
}

void AKZMonsterAIController::SetMovementPolicy(EKZGait Gait, EKZRotationMode Mode)
{
	if (UKZLocomotionComponent* Locomotion = BoundLocomotion.Get())
	{
		Locomotion->SetRequestedGait(IntentHandle, Gait);
		Locomotion->SetRequestedRotationMode(IntentHandle, Mode);
	}
}

bool AKZMonsterAIController::IsPatternReady(FName Skill) const
{
	const AKZMonster* Monster = GetMonster();
	if (!Monster || Monster->IsPatternDisabled(Skill) || EncounterStartedAt < 0.f) return false;
	const FKZMonsterSkillChoice* Row = Monster->GetCombatPatterns().FindByPredicate([Skill](const auto& R) { return R.Skill == Skill; });
	const float Now = GetWorld()->GetTimeSeconds();
	const float* Ready = PatternReadyAt.Find(Skill);
	return Row && Now >= EncounterStartedAt + Row->BattleStartCooldown && (!Ready || Now >= *Ready);
}

void AKZMonsterAIController::RecordPatternFinished(FName Skill)
{
	const AKZMonster* Monster = GetMonster();
	if (!Monster) return;
	const FKZMonsterSkillChoice* Row = Monster->GetCombatPatterns().FindByPredicate([Skill](const auto& R) { return R.Skill == Skill; });
	if (Row)
	{
		const FKZMonsterAISettings& Settings = Monster->GetAISettings();
		const float Cooldown = Skill == Settings.RangedPatternSkill ? Settings.RangedPatternCooldownSeconds : Row->EndCooldown;
		PatternReadyAt.Add(Skill, GetWorld()->GetTimeSeconds() + FMath::Max(0.f, Cooldown));
	}
}

bool AKZMonsterAIController::ShouldChooseRangedPattern() const
{
	if (RangedChoiceFrame != GFrameCounter)
	{
		RangedChoiceFrame = GFrameCounter;
		const AKZMonster* Monster = GetMonster();
		bRangedChoice = Monster && FMath::FRand() < Monster->GetAISettings().RangedPatternChance;
	}
	return bRangedChoice;
}

void AKZMonsterAIController::AddPatternCooldown(FName Skill,float Seconds)
{
	float& Ready=PatternReadyAt.FindOrAdd(Skill);
	Ready=FMath::Max(Ready,GetWorld()->GetTimeSeconds())+Seconds;
}

const FKZMonsterSkillChoice* AKZMonsterAIController::SelectCombatPattern(bool bChoose) const
{
	const AKZMonster* Monster = GetMonster();
	if (!Monster || !BattleTarget.IsValid() || Monster->IsCombatIncapacitated()) return nullptr;
	TArray<const FKZMonsterSkillChoice*> Eligible;
	float TotalWeight = 0.f;
	for (const FKZMonsterSkillChoice& Row : Monster->GetCombatPatterns())
	{
		if (!Row.Ability || Row.Weight <= 0.f || !IsPatternReady(Row.Skill) || !Row.Condition.Matches(Monster, BattleTarget.Get())) continue;
		if (!bChoose || Monster->UsesOrderedPatterns()) return &Row;
		Eligible.Add(&Row); TotalWeight += Row.Weight;
	}
	// Apes Rate fields are weights. Native RNG normalization is not available.
	float Draw = FMath::FRand() * TotalWeight;
	for (const FKZMonsterSkillChoice* Row : Eligible) { Draw -= Row->Weight; if (Draw < 0.f) return Row; }
	return Eligible.IsEmpty() ? nullptr : Eligible.Last();
}

void AKZMonsterAIController::MirrorNavigationIntent()
{
	UKZLocomotionComponent* Locomotion = BoundLocomotion.Get();
	if (!Locomotion || !GetPawn()) return;
	if (!Locomotion->IsMovementInputAllowed()) { StopRequestedMove(); return; }
	if (DirectMoveGoal.IsSet())
	{
		Locomotion->SetMoveInputWorld(IntentHandle, (DirectMoveGoal.GetValue() - GetPawn()->GetActorLocation()).GetSafeNormal2D());
		return;
	}
	const UPathFollowingComponent* Path = GetPathFollowingComponent();
	if (Path && Path->GetStatus() == EPathFollowingStatus::Moving)
	{
		Locomotion->SetMoveInputWorld(IntentHandle, (Path->GetCurrentTargetLocation() - GetPawn()->GetActorLocation()).GetSafeNormal2D());
	}
	else Locomotion->ClearMoveInput(IntentHandle);
}

bool AKZMonsterAIController::TryDirectPursuit(const FVector& Goal, const bool bPathFailed)
{
	AKZMonster* Monster = GetMonster();
	if (!Monster || !Monster->GetAISettings().bDirectPursuitWhenPathFails || Goal.ContainsNaN()) return false;
	if (!bPathFailed)
	{
		UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
		const ANavigationData* Data = Nav ? Nav->GetNavDataForProps(GetNavAgentPropertiesRef(), GetNavAgentLocation()) : nullptr;
		FNavLocation Projected;
		if (Data && Nav->ProjectPointToNavigation(GetNavAgentLocation(), Projected, Data->GetDefaultQueryExtent(), Data)) return false;
	}
	// An abstract navigation path can be accepted outside the baked mesh while
	// supplying no movement input. Drive the existing Pawn/CMC input instead;
	// its normal world collision and ASC permission remain authoritative.
	if (!DirectMoveGoal.IsSet()) StopRequestedMove();
	DirectMoveGoal = Goal;
	MirrorNavigationIntent();
	return true;
}

void AKZMonsterAIController::StopRequestedMove()
{
	DirectMoveGoal.Reset();
	StopMovement();
	if (UKZLocomotionComponent* Locomotion = BoundLocomotion.Get()) Locomotion->ClearMoveInput(IntentHandle);
}

void AKZMonsterAIController::HandleMovementPermissionChanged(bool bAllowed)
{
	if (!bAllowed) StopRequestedMove();
}
