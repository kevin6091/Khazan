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
#include "GameFramework/CharacterMovementComponent.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "LogChannels.h"

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
	case EKZMonsterCondition::NeedsChase: return AI->GetBattleTarget() && !AI->NeedsAlert() && AI->GetTargetDistance() > Monster->GetAISettings().EngageDistance &&
		(Monster->GetCombatPatterns().IsEmpty() || !AI->CanChooseAttack());
	case EKZMonsterCondition::CanAttack: return AI->CanChooseAttack();
	case EKZMonsterCondition::HasTarget: return AI->GetBattleTarget() != nullptr;
	case EKZMonsterCondition::PendingDamagePassive: return AI->HasPendingDamagePassive();
	case EKZMonsterCondition::SourceGate:
	{
		// Disabled skills must take the source tree's inverted false route.
		// Rejecting both gates strands an acquired distant target in Idle.
		if (Monster->IsPatternDisabled(RequiredSkill)) return bInvert;
		FKZCombatPatternCondition Gate = SourceGate;
		const FKZMonsterAISettings& Settings = Monster->GetAISettings();
		const float Distance = AI->GetTargetDistance();
		const bool bRangedChoice = !RequiredSkill.IsNone() && RequiredSkill == Settings.RangedPatternSkill &&
			Distance >= Settings.RangedPatternDistance.X && Distance <= Settings.RangedPatternDistance.Y;
		if (bRangedChoice)
		{
			// User explicitly permits Armageddon at range, including full HP.
			// Keep the source stamina/angle/obstruction and granted-ability gates.
			Gate.MaxHP = -1.f;
			Gate.MinDistance = Settings.RangedPatternDistance.X;
			Gate.MaxDistance = Settings.RangedPatternDistance.Y;
		}
		bool bPass = Gate.Matches(Monster, AI->GetBattleTarget()) && !Monster->IsCombatIncapacitated();
		if (bPass && !RequiredSkill.IsNone()) bPass = AI->IsPatternReady(RequiredSkill);
		if (bPass && RequiredAbility)
		{
			UAbilitySystemComponent* ASC = Monster->GetAbilitySystemComponent();
			const FGameplayAbilitySpec* Spec = ASC ? ASC->FindAbilitySpecFromClass(RequiredAbility) : nullptr;
			bPass = Spec && Spec->Ability && Spec->Ability->CanActivateAbility(Spec->Handle, ASC->AbilityActorInfo.Get());
		}
		if (bPass && bRangedChoice) bPass = AI->ShouldChooseRangedPattern();
		return bInvert ? !bPass : bPass;
	}
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
	Data.NavigationRequest = Data.PatternRun = 0;
	Data.SourceMoveIndex = INDEX_NONE;
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	Data.TimeRemaining = Task == EKZMonsterTask::Chase ? Settings.ChaseReactionSeconds : 0.f;
	AI->SetMovementPolicy(Task == EKZMonsterTask::Chase ? EKZGait::Run : EKZGait::Walk,
		Task == EKZMonsterTask::Idle || Task == EKZMonsterTask::Patrol ? EKZRotationMode::VelocityDirection : EKZRotationMode::LockOn);
	if (Task == EKZMonsterTask::SourceMoveTo || Task == EKZMonsterTask::SourceLockOnMove)
	{
		if (!AI->GetBattleTarget()) return EStateTreeRunStatus::Failed;
		AI->SetMovementPolicy(SourceGait, EKZRotationMode::LockOn);
		Data.TimeRemaining = SourceMoveLimitSeconds > 0.f ? SourceMoveLimitSeconds : -1.f;
		Data.MoveGoal = AI->GetBattleTarget()->GetActorLocation();
		if (Task == EKZMonsterTask::SourceLockOnMove)
		{
			float Sum = 0.f;
			for (const auto& Move : SourceMoves) Sum += FMath::Max(0.f, Move.Rate);
			if (Sum <= 0.f) return EStateTreeRunStatus::Failed;
			float Draw = FMath::FRand() * Sum;
			for (int32 Index = 0; Index < SourceMoves.Num(); ++Index)
				if ((Draw -= FMath::Max(0.f, SourceMoves[Index].Rate)) < 0.f) { Data.SourceMoveIndex = Index; break; }
			if (!SourceMoves.IsValidIndex(Data.SourceMoveIndex)) return EStateTreeRunStatus::Failed;
			const auto& Move = SourceMoves[Data.SourceMoveIndex];
			const FVector Forward = (AI->GetBattleTarget()->GetActorLocation() - Monster->GetActorLocation()).GetSafeNormal2D();
			const FVector Right(-Forward.Y, Forward.X, 0);
			const FVector Direction = Forward * Move.LocalDirection.X + Right * Move.LocalDirection.Y;
			Data.TimeRemaining = Move.bByTime ? Move.Seconds : -1.f;
			const float Distance = Move.bByTime ? Monster->GetCharacterMovement()->MaxWalkSpeed * Move.Seconds : Move.Distance;
			Data.MoveGoal = Monster->GetActorLocation() + Direction * Distance;
		}
		UE_LOG(LogAbility, Verbose, TEXT("SourceBT enter owner=%s export=%d task=%d duration=%g"), *Monster->GetName(), SourceExport, int32(Task), Data.TimeRemaining);
		return Tick(Context, 0.f);
	}
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
		const FVector Weights=Settings.StandoffDirectionWeights.ComponentMax(FVector::ZeroVector);
		const float Choice=FMath::FRand()*(Weights.X+Weights.Y+Weights.Z);
		Data.StrafeSign=Choice<Weights.X?-1:Choice<Weights.X+Weights.Y?1:Settings.bBackwardStandoff?2:0;
		// Retain a valid local goal even if the player leaves before the first task tick.
		Data.MoveGoal = Monster->GetActorLocation();
		if(Settings.bBackwardStandoff && AI->GetBattleTarget())
		{
			const FVector Away=(Monster->GetActorLocation()-AI->GetBattleTarget()->GetActorLocation()).GetSafeNormal2D();
			const FVector Tangent(-Away.Y,Away.X,0);
			const FVector Direction=Data.StrafeSign==2?Away:Tangent*Data.StrafeSign;
			// Source bUseMoveByTime: retain one chosen direction for the full MoveTime.
			Data.MoveGoal+=Direction*Monster->GetCharacterMovement()->MaxWalkSpeed*Data.TimeRemaining;
		}
		// Resolve and request this chosen local movement before the first normal tick.
		return Tick(Context, 0.f);
	}
	else if (Task == EKZMonsterTask::Alert || Task == EKZMonsterTask::Attack || Task == EKZMonsterTask::SourceSkill)
	{
		UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		if (!ASC) return EStateTreeRunStatus::Failed;
		TSubclassOf<UGameplayAbility> AbilityClass = Monster->GetAlertAbility();
		FName SelectedSourceSkill = SourceSkill;
		if (Task == EKZMonsterTask::SourceSkill)
		{
			const FName Skill = bUsePendingDamagePassive ? AI->TakePendingDamagePassive() : SourceSkill;
			if (Monster->IsPatternDisabled(Skill)) return EStateTreeRunStatus::Failed;
			SelectedSourceSkill = Skill;
			const auto* Row = Monster->GetCombatPatterns().FindByPredicate([Skill](const auto& Choice) { return Choice.Skill == Skill; });
			AbilityClass = SourceAbility ? SourceAbility : Row ? Row->Ability : nullptr;
			if (!AbilityClass) return EStateTreeRunStatus::Failed;
		}
		else if (Task == EKZMonsterTask::Alert) AI->AlertedTarget = AI->BattleTarget;
		else
		{
			TArray<TSubclassOf<UGameplayAbility>> Candidates = Monster->GetAttackAbilities();
			if (!Monster->GetCombatPatterns().IsEmpty())
			{
				const FKZMonsterSkillChoice* Pattern = AI->SelectCombatPattern(true);
				if (!Pattern) return EStateTreeRunStatus::Failed;
				AbilityClass = Pattern->Ability;
				Data.bContinueCombo = false;
			}
			else
			{
			if (Candidates.Num() > 1) Candidates.Remove(AI->LastAttackClass.Get());
			if (Candidates.IsEmpty()) return EStateTreeRunStatus::Failed;
			AbilityClass = Candidates[FMath::RandHelper(Candidates.Num())];
			Data.bContinueCombo = FMath::FRand() < Settings.ContinueComboChance;
			}
		}
		FGameplayAbilitySpec* Spec = AbilityClass ? ASC->FindAbilitySpecFromClass(AbilityClass) : nullptr;
		if (!Spec || !ASC->TryActivateAbility(Spec->Handle))
		{
			AI->NextAttackAt = Monster->GetWorld()->GetTimeSeconds() + Settings.PathRetrySeconds;
			return Task == EKZMonsterTask::Alert ? EStateTreeRunStatus::Succeeded : EStateTreeRunStatus::Failed;
		}
		Data.AbilityHandle = Spec->Handle;
		if (auto* Pattern = Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance())) Data.PatternRun = Pattern->GetPatternRun();
		if (Task == EKZMonsterTask::SourceSkill)
		{
			const auto* Combo = Cast<UKZComboActionAbility>(Spec->GetPrimaryInstance());
			UE_LOG(LogAbility, Log, TEXT("SourceBT skill owner=%s export=%d skill=%s entry=%s run=%u"), *Monster->GetName(), SourceExport, *SelectedSourceSkill.ToString(), Combo ? *Combo->GetCurrentNodeId().ToString() : TEXT("None"), Data.PatternRun);
		}
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
	if (Task == EKZMonsterTask::SourceMoveTo || Task == EKZMonsterTask::SourceLockOnMove)
	{
		if (!Target) return EStateTreeRunStatus::Failed;
		if (Data.TimeRemaining >= 0.f)
		{
			Data.TimeRemaining = FMath::Max(0.f, Data.TimeRemaining - DeltaSeconds);
			if (Data.TimeRemaining == 0.f)
				return Task == EKZMonsterTask::SourceLockOnMove ? EStateTreeRunStatus::Succeeded : EStateTreeRunStatus::Failed;
		}
		if (Task == EKZMonsterTask::SourceMoveTo && AI->GetTargetDistance() <= SourceAcceptanceRadius) return EStateTreeRunStatus::Succeeded;
		if (Task == EKZMonsterTask::SourceLockOnMove)
		{
			const auto& Move = SourceMoves[Data.SourceMoveIndex];
			if (Move.bFinishByTargetDistance && AI->GetTargetDistance() <= Move.FinishTargetDistance) return EStateTreeRunStatus::Succeeded;
			if (!Move.bByTime && FVector::Dist2D(Monster->GetActorLocation(), Data.MoveGoal) <= SourceAcceptanceRadius) return EStateTreeRunStatus::Succeeded;
		}
		if (!Monster->GetLocomotionComponent()->IsMovementInputAllowed()) return EStateTreeRunStatus::Running;
		const FVector DesiredGoal = Task == EKZMonsterTask::SourceMoveTo ? Target->GetActorLocation() : Data.MoveGoal;
		if (AI->TryDirectPursuit(DesiredGoal)) { Data.NavigationRequest = 0; return EStateTreeRunStatus::Running; }
		if (AI->DirectMoveGoal.IsSet() && Now < Data.RetryAt)
		{
			AI->DirectMoveGoal = DesiredGoal;
			AI->MirrorNavigationIntent();
			return EStateTreeRunStatus::Running;
		}
		const bool bTargetMoved = Task == EKZMonsterTask::SourceMoveTo && FVector::Dist2D(Data.MoveGoal, Target->GetActorLocation()) >= SourceFollowUpdateDistance;
		if (Data.NavigationRequest == 0 || bTargetMoved)
		{
			if (Task == EKZMonsterTask::SourceMoveTo) Data.MoveGoal = Target->GetActorLocation();
			FAIMoveRequest Request(Data.MoveGoal);
			Request.SetAcceptanceRadius(SourceAcceptanceRadius);
			Request.SetReachTestIncludesAgentRadius(false);
			Request.SetReachTestIncludesGoalRadius(false);
			Request.SetUsePathfinding(true);
			FPathFollowingRequestResult Result = AI->MoveTo(Request);
			if (Result.Code == EPathFollowingRequestResult::Failed && Settings.bDirectPursuitWhenPathFails)
			{
				AI->TryDirectPursuit(DesiredGoal, true);
				Data.NavigationRequest = 0; Data.RetryAt = Now + Settings.PathRetrySeconds;
				return EStateTreeRunStatus::Running;
			}
			AI->DirectMoveGoal.Reset();
			if (Result.Code == EPathFollowingRequestResult::Failed) return EStateTreeRunStatus::Failed;
			if (Result.Code == EPathFollowingRequestResult::AlreadyAtGoal)
				return Task == EKZMonsterTask::SourceLockOnMove && SourceMoves[Data.SourceMoveIndex].bByTime ? EStateTreeRunStatus::Running : EStateTreeRunStatus::Succeeded;
			Data.NavigationRequest = uint32(Result.MoveId);
		}
		else if (AI->GetMoveStatus() != EPathFollowingStatus::Moving)
		{
			if (Task == EKZMonsterTask::SourceMoveTo) return EStateTreeRunStatus::Failed;
			if (!SourceMoves[Data.SourceMoveIndex].bByTime) return EStateTreeRunStatus::Succeeded;
		}
		AI->MirrorNavigationIntent();
		return EStateTreeRunStatus::Running;
	}
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
	else if (Task == EKZMonsterTask::Alert || Task == EKZMonsterTask::Attack || Task == EKZMonsterTask::SourceSkill)
	{
		const UAbilitySystemComponent* ASC = Monster->GetAbilitySystemComponent();
		const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(Data.AbilityHandle);
		if (Task == EKZMonsterTask::SourceSkill && Spec && !Spec->IsActive())
			if (const auto* Pattern = Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance()); Pattern && Pattern->WasPatternRunCancelled(Data.PatternRun))
				return EStateTreeRunStatus::Failed;
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
		if (!Settings.bBackwardStandoff && Now >= Data.RetryAt && AI->GetTargetDistance() <= Settings.EngageDistance)
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
	const bool bRefreshStandoff = Task == EKZMonsterTask::Standoff && !Settings.bBackwardStandoff && Now >= Data.RetryAt && AI->GetTargetDistance() <= Settings.EngageDistance;
	if (Task == EKZMonsterTask::Chase && AI->TryDirectPursuit(Target->GetActorLocation())) return EStateTreeRunStatus::Running;
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
		const FPathFollowingRequestResult Result = AI->MoveTo(Request);
		if (Result.Code == EPathFollowingRequestResult::Failed && Settings.bDirectPursuitWhenPathFails)
		{
			AI->TryDirectPursuit(Task == EKZMonsterTask::Chase ? Target->GetActorLocation() : Data.MoveGoal, true);
		}
		else AI->DirectMoveGoal.Reset();
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
	if (AI->DirectMoveGoal.IsSet() || Task != EKZMonsterTask::SourceMoveTo && Task != EKZMonsterTask::SourceLockOnMove ||
		Data.NavigationRequest != 0 && uint32(AI->GetCurrentMoveRequestID()) == Data.NavigationRequest) AI->StopRequestedMove();
	if (!Monster) return;
	if (UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent()))
	{
		if (Data.bContinueCombo) ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Cancel);
		if (Task == EKZMonsterTask::Idle) ASC->SubmitComboCommand(KZGameplayTags::Command_AI_Alert, EKZComboCommandPhase::Cancel);
		if (Data.AbilityHandle.IsValid())
		{
			const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(Data.AbilityHandle);
			const auto* Pattern = Spec ? Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance()) : nullptr;
			if (!Pattern || Pattern->GetPatternRun() == Data.PatternRun) ASC->CancelAbilityHandle(Data.AbilityHandle);
		}
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
