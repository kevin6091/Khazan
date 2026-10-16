#pragma once

#include "CoreMinimal.h"
#include "Ability/KZActionAbility.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZBrutalAttackAbility.generated.h"

class AKZMonster;
class UKZExhaustionAbility;
class UAbilityTask_PlayMontageAndWait;

/** Paired player action; the monster's Exhaustion Ability owns recovery after both completions. */
UCLASS()
class KHAZAN_API UKZBrutalAttackAbility : public UKZActionAbility
{
	GENERATED_BODY()
public:
	UKZBrutalAttackAbility();
	AKZMonster* FindBrutalTarget(const FGameplayAbilityActorInfo* ActorInfo) const;
	void AbortFromVictim(const UKZExhaustionAbility* NotifyingVictim);
protected:
	virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayTagContainer* SourceTags = nullptr, const FGameplayTagContainer* TargetTags = nullptr,
		FGameplayTagContainer* OptionalRelevantTags = nullptr) const override;
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;
private:
	UFUNCTION() void HandleMontageCompleted();
	UFUNCTION() void HandleMontageAborted();
	UFUNCTION() void HandleMontageNotify(FName Name, const FBranchingPointNotifyPayload& Payload);
	TWeakObjectPtr<AKZMonster> Target;
	TWeakObjectPtr<UKZExhaustionAbility> VictimAbility;
	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;
	UPROPERTY(Transient) TObjectPtr<UAbilityTask_PlayMontageAndWait> MontageTask;
	UPROPERTY(Transient) TObjectPtr<class UAnimMontage> PlayingMontage;
	FKZMovementConstraintHandle MovementHandle;
	int32 MontageInstanceId = INDEX_NONE;
	// These flags belong to this attack execution, not shared gameplay state.
	bool bFirstReactionSent = false;
	bool bSecondReactionSent = false;
	bool bMontageCompleted = false;
};
