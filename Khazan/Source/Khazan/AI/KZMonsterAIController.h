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
struct FGameplayEffectSpec;
class UAbilitySystemComponent;
struct FActiveGameplayEffectHandle;

/** Perception/focus/navigation adapter. StateTree selects behaviour; GAS owns actions. */
UCLASS()
class KHAZAN_API AKZMonsterAIController : public AAIController
{
	GENERATED_BODY()
public:
	AKZMonsterAIController();
	virtual void Tick(float DeltaSeconds) override;
	virtual FRotator GetDesiredRotation() const override;
	AKZMonster* GetMonster() const;
	UFUNCTION(BlueprintPure, Category = "Monster|AI")
	AActor* GetBattleTarget() const { return BattleTarget.Get(); }
	UStateTreeAIComponent* GetStateTreeComponent() const { return StateTreeComponent; }
	bool IsPatternReady(FName Skill) const;
	bool ShouldChooseRangedPattern() const;
	void RecordPatternFinished(FName Skill);
	void AddPatternCooldown(FName Skill,float Seconds);
	bool HasPendingDamagePassive() const;
	FName TakePendingDamagePassive();

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
	bool TryDirectPursuit(const FVector& Goal, bool bPathFailed = false);
	void StopRequestedMove();
	float GetTargetDistance() const;
	bool NeedsAlert() const;
	bool CanChooseAttack() const;
	const struct FKZMonsterSkillChoice* SelectCombatPattern(bool bChoose) const;
	void HandleMovementPermissionChanged(bool bAllowed);
	void HandleAcceptedDamage(UAbilitySystemComponent* Target, const FGameplayEffectSpec& Spec, FActiveGameplayEffectHandle Handle);
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
	// Navigation resource owned by the selected movement task; Stop/Exit clears it.
	TOptional<FVector> DirectMoveGoal;
	float NextAttackAt = 0.f;
	TMap<FName, float> PatternReadyAt;
	float EncounterStartedAt = -1.f;
	// One selection result is shared by the source tree's paired true/false
	// gates in this frame. This is an AI choice receipt, not gameplay state.
	mutable uint64 RangedChoiceFrame = MAX_uint64;
	mutable bool bRangedChoice = false;
	FDelegateHandle DamagePassiveHandle;
	TWeakObjectPtr<UAbilitySystemComponent> PassiveASC;
	TArray<float> RecentDamageTimes;
	FName PendingDamageSkill;
	float PendingDamageUntil = 0.f;
	// Ownership of our StateTree pause request, not a copy of the ASC incapacitation state.
	bool bPausedForCombatReaction = false;
};
