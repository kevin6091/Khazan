#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZMonsterAIController.generated.h"

class AKZMonster;
class UAIPerceptionComponent;
class UAISenseConfig_Sight;
class UStateTreeAIComponent;
struct FAIStimulus;

/** Perception/focus/navigation adapter. StateTree selects behaviour; GAS owns actions. */
UCLASS()
class KHAZAN_API AKZMonsterAIController : public AAIController
{
	GENERATED_BODY()
public:
	AKZMonsterAIController();
	virtual void Tick(float DeltaSeconds) override;
	AKZMonster* GetMonster() const;
	UFUNCTION(BlueprintPure, Category = "Monster|AI")
	AActor* GetBattleTarget() const { return BattleTarget.Get(); }
	UStateTreeAIComponent* GetStateTreeComponent() const { return StateTreeComponent; }

protected:
	virtual void BeginPlay() override;
	virtual void OnPossess(APawn* InPawn) override;
	virtual void OnUnPossess() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	friend struct FKZMonsterStateTreeTask;
	friend struct FKZMonsterStateTreeCondition;
	void StartMonsterLogic();
	void ReleaseMonsterLogic();
	void SetMovementPolicy(EKZGait Gait, EKZRotationMode RotationMode);
	void MirrorNavigationIntent();
	void StopRequestedMove();
	float GetTargetDistance() const;
	bool NeedsAlert() const;
	bool CanChooseAttack() const;
	void HandleMovementPermissionChanged(bool bAllowed);
	UFUNCTION()
	void HandleTargetPerception(AActor* Actor, FAIStimulus Stimulus);

	UPROPERTY(VisibleAnywhere, Category = "AI")
	TObjectPtr<UStateTreeAIComponent> StateTreeComponent;
	UPROPERTY(VisibleAnywhere, Category = "AI")
	TObjectPtr<UAIPerceptionComponent> MonsterPerception;
	UPROPERTY()
	TObjectPtr<UAISenseConfig_Sight> SightConfig;
	TWeakObjectPtr<AActor> BattleTarget;
	TWeakObjectPtr<AActor> AlertedTarget;
	TWeakObjectPtr<UClass> LastAttackClass;
	TWeakObjectPtr<UKZLocomotionComponent> BoundLocomotion;
	FKZLocomotionIntentHandle IntentHandle;
	FDelegateHandle MovementPermissionHandle;
	FVector HomeLocation = FVector::ZeroVector;
	float NextAttackAt = 0.f;
};
