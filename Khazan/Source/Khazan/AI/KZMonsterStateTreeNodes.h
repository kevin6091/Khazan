#pragma once

#include "CoreMinimal.h"
#include "Tasks/StateTreeAITask.h"
#include "Conditions/StateTreeAIConditionBase.h"
#include "GameplayAbilitySpecHandle.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZMonsterStateTreeNodes.generated.h"

class AKZMonsterAIController;
class AKZMonster;
class UGameplayAbility;

/** Authoring selection only. The active StateTree state is the runtime behaviour owner. */
UENUM()
enum class EKZMonsterTask : uint8 { Idle, Alert, Chase, Standoff, Attack, Patrol, SourceSkill, SourceMoveTo, SourceLockOnMove };
UENUM()
enum class EKZMonsterCondition : uint8 { NoTarget, NeedsAlert, NeedsChase, CanAttack, HasTarget, WantsPatrol, SourceGate, PendingDamagePassive };

USTRUCT()
struct FKZSourceLockOnMove
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) FVector LocalDirection = FVector::ZeroVector;
	UPROPERTY(EditAnywhere) float Rate = 0.f;
	UPROPERTY(EditAnywhere) float Distance = 0.f;
	UPROPERTY(EditAnywhere) float Seconds = 0.f;
	UPROPERTY(EditAnywhere) bool bByTime = false;
	UPROPERTY(EditAnywhere) bool bFinishByTargetDistance = false;
	UPROPERTY(EditAnywhere) float FinishTargetDistance = 0.f;
	UPROPERTY(EditAnywhere) bool bDontCheckFrontNearDistance = false;
};

USTRUCT()
struct FKZMonsterTaskInstanceData
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Context")
	TObjectPtr<AKZMonsterAIController> AIController;
	UPROPERTY(Transient)
	float TimeRemaining = 0.f;
	UPROPERTY(Transient)
	float RetryAt = 0.f;
	UPROPERTY(Transient)
	FVector MoveGoal = FVector::ZeroVector;
	UPROPERTY(Transient)
	int32 StrafeSign = 0;
	UPROPERTY(Transient)
	FGameplayAbilitySpecHandle AbilityHandle;
	UPROPERTY(Transient)
	bool bContinueCombo = false;
	UPROPERTY(Transient)
	bool bEndingIdle = false;
	UPROPERTY(Transient)
	TWeakObjectPtr<AKZMonster> TalkPartner;
	UPROPERTY(Transient) uint32 NavigationRequest = 0;
	UPROPERTY(Transient) uint32 PatternRun = 0;
	UPROPERTY(Transient) int32 SourceMoveIndex = INDEX_NONE;
};

USTRUCT(meta = (DisplayName = "Khazan Monster Action", Category = "Khazan|AI"))
struct KHAZAN_API FKZMonsterStateTreeTask : public FStateTreeAITaskBase
{
	GENERATED_BODY()
	using FInstanceDataType = FKZMonsterTaskInstanceData;
	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
	virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, float DeltaSeconds) const override;
	virtual void ExitState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
	UPROPERTY(EditAnywhere, Category = "Parameter")
	EKZMonsterTask Task = EKZMonsterTask::Idle;
	UPROPERTY(EditAnywhere, Category = "Source") FName SourceSkill;
	UPROPERTY(EditAnywhere, Category = "Source") TSubclassOf<UGameplayAbility> SourceAbility;
	UPROPERTY(EditAnywhere, Category = "Source") bool bUsePendingDamagePassive = false;
	UPROPERTY(EditAnywhere, Category = "Source") float SourceAcceptanceRadius = 0.f;
	UPROPERTY(EditAnywhere, Category = "Source") float SourceMoveLimitSeconds = 0.f;
	UPROPERTY(EditAnywhere, Category = "Source") float SourceFollowUpdateDistance = 0.f;
	UPROPERTY(EditAnywhere, Category = "Source") EKZGait SourceGait = EKZGait::Run;
	UPROPERTY(EditAnywhere, Category = "Source") TArray<FKZSourceLockOnMove> SourceMoves;
	UPROPERTY(EditAnywhere, Category = "Source") int32 SourceExport = INDEX_NONE;
};

USTRUCT()
struct FKZMonsterConditionInstanceData
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Context")
	TObjectPtr<AKZMonsterAIController> AIController;
};

USTRUCT(meta = (DisplayName = "Khazan Monster Decision", Category = "Khazan|AI"))
struct KHAZAN_API FKZMonsterStateTreeCondition : public FStateTreeAIConditionBase
{
	GENERATED_BODY()
	using FInstanceDataType = FKZMonsterConditionInstanceData;
	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual bool TestCondition(FStateTreeExecutionContext& Context) const override;
	UPROPERTY(EditAnywhere, Category = "Parameter")
	EKZMonsterCondition Condition = EKZMonsterCondition::HasTarget;
	UPROPERTY(EditAnywhere, Category = "Source") FKZCombatPatternCondition SourceGate;
	UPROPERTY(EditAnywhere, Category = "Source") FName RequiredSkill;
	UPROPERTY(EditAnywhere, Category = "Source") TSubclassOf<UGameplayAbility> RequiredAbility;
	UPROPERTY(EditAnywhere, Category = "Source") bool bInvert = false;
	UPROPERTY(EditAnywhere, Category = "Source") int32 SourceExport = INDEX_NONE;
};
