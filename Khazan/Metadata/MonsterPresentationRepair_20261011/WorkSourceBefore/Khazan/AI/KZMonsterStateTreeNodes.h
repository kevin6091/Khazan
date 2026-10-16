#pragma once

#include "CoreMinimal.h"
#include "Tasks/StateTreeAITask.h"
#include "Conditions/StateTreeAIConditionBase.h"
#include "GameplayAbilitySpecHandle.h"
#include "KZMonsterStateTreeNodes.generated.h"

class AKZMonsterAIController;
class AKZMonster;

/** Authoring selection only. The active StateTree state is the runtime behaviour owner. */
UENUM()
enum class EKZMonsterTask : uint8 { Idle, Alert, Chase, Standoff, Attack, Patrol };
UENUM()
enum class EKZMonsterCondition : uint8 { NoTarget, NeedsAlert, NeedsChase, CanAttack, HasTarget, WantsPatrol };

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
};
