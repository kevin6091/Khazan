#include "AI/KZMonsterStateTreeNodes.h"

#include "AI/KZMonsterAIController.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Character/KZMonster.h"
#include "Data/KZCharacterDefinitionData.h"
#include "StateTreeExecutionContext.h"
#include "NavigationSystem.h"
#include "Navigation/PathFollowingComponent.h"
#include "KZGameplayTags.h"
#include "Engine/World.h"

bool FKZMonsterStateTreeCondition::TestCondition(FStateTreeExecutionContext& Context) const
{
	const AKZMonsterAIController* AI = Context.GetInstanceData(*this).AIController;
	const AKZMonster* Monster = AI ? AI->GetMonster() : nullptr;
	if (!Monster) return false;
	switch (Condition)
	{
	case EKZMonsterCondition::NoTarget: return !AI->GetBattleTarget();
	case EKZMonsterCondition::WantsPatrol: return !AI->GetBattleTarget() && Monster->ShouldPatrolWhenUnaware();
	case EKZMonsterCondition::NeedsAlert: return AI->NeedsAlert();
	case EKZMonsterCondition::NeedsChase: return AI->GetBattleTarget() && !AI->NeedsAlert() && AI->GetTargetDistance() > Monster->GetAISettings().EngageDistance;
	case EKZMonsterCondition::CanAttack: return AI->CanChooseAttack();
	case EKZMonsterCondition::HasTarget: return AI->GetBattleTarget() != nullptr;
	default: return false;
	}
}

EStateTreeRunStatus FKZMonsterStateTreeTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
	FInstanceDataType& Data = Context.GetInstanceData(*this);
	AKZMonsterAIController* AI = Data.AIController;
	AKZMonster* Monster = AI ? AI->GetMonster() : nullptr;
	if (!Monster) return EStateTreeRunStatus::Failed;
	AI->StopRequestedMove();
	Data.AbilityHandle = FGameplayAbilitySpecHandle();
	Data.bContinueCombo = false;
	Data.bEndingIdle = false;
	Data.TalkPartner.Reset();
	Data.RetryAt = 0.f;
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	Data.TimeRemaining = Task == EKZMonsterTask::Chase ? Settings.ChaseReactionSeconds : 0.f;
	AI->SetMovementPolicy(Task == EKZMonsterTask::Chase ? EKZGait::Run : EKZGait::Walk,
		Task == EKZMonsterTask::Idle || Task == EKZMonsterTask::Patrol ? EKZRotationMode::VelocityDirection : EKZRotationMode::LockOn);
	if (Task == EKZMonsterTask::Idle)
	{
		UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		const FKZUnawareRoutine* Routine = Monster->ResolveUnawareRoutine();
		if (Routine && ASC && Routine->Role != EKZUnawareRoutineRole::Solo)
		{
			AKZMonster* Partner = Monster->GetTalkPartner();
			const FKZUnawareRoutine* OtherRoutine = Partner ? Partner->ResolveUnawareRoutine() : nullptr;
			UAbilitySystemComponent* OtherASC = Partner ? Partner->GetAbilitySystemComponent() : nullptr;
			FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(Routine->AbilityClass);
			FGameplayAbilitySpec* OtherSpec = OtherASC && OtherRoutine && OtherRoutine->Role != EKZUnawareRoutineRole::Solo ? OtherASC->FindAbilitySpecFromClass(OtherRoutine->AbilityClass) : nullptr;
			const bool bWasActive = Spec && Spec->IsActive();
			// Start both granted abilities in this game-thread turn; the peer task adopts its active spec.
			const bool bBothStarted = Spec && OtherSpec && (bWasActive || ASC->TryActivateAbility(Spec->Handle)) &&
				(OtherSpec->IsActive() || OtherASC->TryActivateAbility(OtherSpec->Handle));
			if (!bBothStarted)
			{
				if (Spec && !bWasActive && Spec->IsActive()) ASC->CancelAbilityHandle(Spec->Handle);
				Routine = Monster->ResolveUnawareRoutine(false);
			}
		}
		if (Routine)
		{
			FGameplayAbilitySpec* Spec = ASC ? ASC->FindAbilitySpecFromClass(Routine->AbilityClass) : nullptr;
			if (Spec && (Spec->IsActive() || ASC->TryActivateAbility(Spec->Handle)))
			{
				Data.AbilityHandle = Spec->Handle;
				if (Routine->Role != EKZUnawareRoutineRole::Solo) Data.TalkPartner = Monster->GetTalkPartner();
			}
		}
	}
	else if (Task == EKZMonsterTask::Patrol)
	{
		Data.TimeRemaining = FMath::FRandRange(Settings.IdleSeconds.X, Settings.IdleSeconds.Y);
		Data.MoveGoal = Monster->GetActorLocation();
		if (FVector::DistSquared2D(Monster->GetActorLocation(), AI->HomeLocation) > FMath::Square(Settings.PatrolRadius)) Data.MoveGoal = AI->HomeLocation;
		else if (FMath::FRand() < Settings.PatrolChance)
		{
			FNavLocation Point;
			if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Monster->GetWorld()))
				if (Nav->GetRandomReachablePointInRadius(AI->HomeLocation, Settings.PatrolRadius, Point)) Data.MoveGoal = Point.Location;
		}
	}
	else if (Task == EKZMonsterTask::Standoff)
	{
		Data.TimeRemaining = FMath::FRandRange(Settings.StandoffSeconds.X, Settings.StandoffSeconds.Y);
		Data.StrafeSign = FMath::RandRange(-1, 1); // Left / pause / right: temporary equal choice.
		// Retain a valid local goal even if the player leaves before the first task tick.
		Data.MoveGoal = Monster->GetActorLocation();
		// Resolve and request this chosen local movement before the first normal tick.
		return Tick(Context, 0.f);
	}
	else if (Task == EKZMonsterTask::Alert || Task == EKZMonsterTask::Attack)
	{
		UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		if (!ASC) return EStateTreeRunStatus::Failed;
		TSubclassOf<UGameplayAbility> AbilityClass = Monster->GetAlertAbility();
		if (Task == EKZMonsterTask::Alert) AI->AlertedTarget = AI->BattleTarget;
		else
		{
			TArray<TSubclassOf<UGameplayAbility>> Candidates = Monster->GetAttackAbilities();
			if (Candidates.Num() > 1) Candidates.Remove(AI->LastAttackClass.Get());
			if (Candidates.IsEmpty()) return EStateTreeRunStatus::Failed;
			AbilityClass = Candidates[FMath::RandHelper(Candidates.Num())];
			Data.bContinueCombo = FMath::FRand() < Settings.ContinueComboChance;
		}
		FGameplayAbilitySpec* Spec = AbilityClass ? ASC->FindAbilitySpecFromClass(AbilityClass) : nullptr;
		if (!Spec || !ASC->TryActivateAbility(Spec->Handle))
		{
			AI->NextAttackAt = Monster->GetWorld()->GetTimeSeconds() + Settings.PathRetrySeconds;
			return Task == EKZMonsterTask::Alert ? EStateTreeRunStatus::Succeeded : EStateTreeRunStatus::Failed;
		}
		Data.AbilityHandle = Spec->Handle;
		if (Task == EKZMonsterTask::Attack)
		{
			AI->LastAttackClass = AbilityClass.Get();
			if (Data.bContinueCombo) ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Begin);
		}
	}
	return EStateTreeRunStatus::Running;
}

EStateTreeRunStatus FKZMonsterStateTreeTask::Tick(FStateTreeExecutionContext& Context, float DeltaSeconds) const
{
	FInstanceDataType& Data = Context.GetInstanceData(*this);
	AKZMonsterAIController* AI = Data.AIController;
	AKZMonster* Monster = AI ? AI->GetMonster() : nullptr;
	if (!Monster) return EStateTreeRunStatus::Failed;
	AActor* Target = AI->GetBattleTarget();
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	const float Now = Monster->GetWorld()->GetTimeSeconds();
	if (Task == EKZMonsterTask::Idle)
	{
		UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		const FGameplayAbilitySpec* Spec = ASC ? ASC->FindAbilitySpecFromHandle(Data.AbilityHandle) : nullptr;
		if (!Spec || !Spec->IsActive())
		{
			if (Data.bEndingIdle && Target) AI->AlertedTarget = Target;
			return Target || Data.AbilityHandle.IsValid() ? EStateTreeRunStatus::Succeeded : EStateTreeRunStatus::Running;
		}
		const bool bPartnerLost = Data.TalkPartner.IsStale() || (Data.TalkPartner.IsValid() &&
			(Monster->GetTalkPartner() != Data.TalkPartner.Get() || !Data.TalkPartner->HasActiveTalkLoop()));
		if (!Data.bEndingIdle && (Target || bPartnerLost))
		{
			Data.bEndingIdle = true;
			if (Target) AI->SetMovementPolicy(EKZGait::Walk, EKZRotationMode::LockOn);
			// Release edges already run immediately in ComboAction, including in a closed input window.
			ASC->SubmitComboCommand(KZGameplayTags::Command_AI_Alert, EKZComboCommandPhase::Begin);
			ASC->SubmitComboCommand(KZGameplayTags::Command_AI_Alert, EKZComboCommandPhase::Release);
		}
		return EStateTreeRunStatus::Running;
	}
	else if (Task == EKZMonsterTask::Patrol)
	{
		if (Target) return EStateTreeRunStatus::Succeeded;
		Data.TimeRemaining -= DeltaSeconds;
		if (Data.TimeRemaining <= 0.f) return EStateTreeRunStatus::Succeeded;
	}
	else if (!Target) return EStateTreeRunStatus::Succeeded;
	else if (Task == EKZMonsterTask::Alert || Task == EKZMonsterTask::Attack)
	{
		const UAbilitySystemComponent* ASC = Monster->GetAbilitySystemComponent();
		const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(Data.AbilityHandle);
		return Spec && Spec->IsActive() ? EStateTreeRunStatus::Running : EStateTreeRunStatus::Succeeded;
	}
	else if (Task == EKZMonsterTask::Chase)
	{
		if (AI->GetTargetDistance() <= Settings.EngageDistance) return EStateTreeRunStatus::Succeeded;
		Data.TimeRemaining = FMath::Max(0.f, Data.TimeRemaining - DeltaSeconds);
		if (Data.TimeRemaining > 0.f) return EStateTreeRunStatus::Running;
	}
	else if (Task == EKZMonsterTask::Standoff)
	{
		// Finish this selected left/pause/right interval before Root chooses attack or chase.
		Data.TimeRemaining -= DeltaSeconds;
		if (Data.TimeRemaining <= 0.f) return EStateTreeRunStatus::Succeeded;
		// Outside the engagement band, finish the previous local goal rather than follow a moving ring.
		if (Now >= Data.RetryAt && AI->GetTargetDistance() <= Settings.EngageDistance)
		{
			const FVector Away = (Monster->GetActorLocation() - Target->GetActorLocation()).GetSafeNormal2D();
			const bool bCorrectDistance = FMath::Abs(AI->GetTargetDistance() - Settings.PreferredDistance) > Settings.DistanceTolerance;
			if (!bCorrectDistance && Data.StrafeSign == 0) { AI->StopRequestedMove(); return EStateTreeRunStatus::Running; }
			const FVector Tangent(-Away.Y, Away.X, 0.f);
			const FVector RingDirection = (Away * Settings.PreferredDistance + Tangent * Data.StrafeSign * Settings.StrafeStepDistance).GetSafeNormal2D();
			Data.MoveGoal = Target->GetActorLocation() + RingDirection * Settings.PreferredDistance;
		}
	}
	UKZLocomotionComponent* Locomotion = Monster->GetLocomotionComponent();
	if (!Locomotion->IsMovementInputAllowed()) { AI->StopRequestedMove(); return EStateTreeRunStatus::Running; }
	const bool bRefreshStandoff = Task == EKZMonsterTask::Standoff && Now >= Data.RetryAt && AI->GetTargetDistance() <= Settings.EngageDistance;
	if (Now >= Data.RetryAt && (AI->GetMoveStatus() != EPathFollowingStatus::Moving || bRefreshStandoff))
	{
		FAIMoveRequest Request;
		if (Task == EKZMonsterTask::Chase)
		{
			Request.SetGoalActor(Target);
			Request.SetAcceptanceRadius(FMath::Max(0.f, Settings.EngageDistance - Settings.DistanceTolerance));
		}
		else
		{
			Request.SetGoalLocation(Data.MoveGoal);
			Request.SetAcceptanceRadius(Settings.MoveAcceptanceRadius);
		}
		Request.SetReachTestIncludesAgentRadius(false);
		Request.SetReachTestIncludesGoalRadius(false);
		Request.SetAllowPartialPath(false);
		Request.SetCanStrafe(Task != EKZMonsterTask::Patrol);
		AI->MoveTo(Request);
		Data.RetryAt = Now + (Task == EKZMonsterTask::Standoff ? Settings.StandoffGoalRefreshSeconds : Settings.PathRetrySeconds);
	}
	AI->MirrorNavigationIntent();
	return EStateTreeRunStatus::Running;
}

void FKZMonsterStateTreeTask::ExitState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
	FInstanceDataType& Data = Context.GetInstanceData(*this);
	AKZMonsterAIController* AI = Data.AIController;
	AKZMonster* Monster = AI ? AI->GetMonster() : nullptr;
	if (!AI) return;
	AI->StopRequestedMove();
	if (!Monster) return;
	if (UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent()))
	{
		if (Data.bContinueCombo) ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Cancel);
		if (Task == EKZMonsterTask::Idle) ASC->SubmitComboCommand(KZGameplayTags::Command_AI_Alert, EKZComboCommandPhase::Cancel);
		if (Data.AbilityHandle.IsValid()) ASC->CancelAbilityHandle(Data.AbilityHandle);
	}
	if (Task == EKZMonsterTask::Attack)
	{
		const FVector2D Interval = Monster->GetAISettings().AttackIntervalSeconds;
		AI->NextAttackAt = Monster->GetWorld()->GetTimeSeconds() + FMath::FRandRange(Interval.X, Interval.Y);
	}
	Data.AbilityHandle = FGameplayAbilitySpecHandle();
	Data.bContinueCombo = false;
	Data.TalkPartner.Reset();
}
