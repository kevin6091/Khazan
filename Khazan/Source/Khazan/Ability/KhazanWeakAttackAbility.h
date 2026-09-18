#pragma once

#include "CoreMinimal.h"
#include "Ability/KhazanGameplayAbility.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "GameplayTagContainer.h"
#include "KhazanWeakAttackAbility.generated.h"

UCLASS()
class KHAZAN_API UKhazanWeakAttackAbility : public UKhazanGameplayAbility
{
	GENERATED_BODY()

public:
	UKhazanWeakAttackAbility();

protected:
	virtual void ActivateAbility(
		const FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		const FGameplayEventData* TriggerEventData) override;

	virtual void InputPressed(
		FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo) override;

	virtual void EndAbility(
		FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo,
		bool bReplicateEndAbility,
		bool bWasCancelled) override;

private:
	UFUNCTION()
	void HandleMontageCompleted();

	UFUNCTION()
	void HandleMontageAborted();

	UFUNCTION()
	void HandleMontageNotifyBegin(FName NotifyName, const FBranchingPointNotifyPayload& BranchingPointPayload);

	UFUNCTION()
	void HandleMoveInputStarted(FGameplayEventData Payload);
	
	bool StartWeakAttackMontage();

	void SubmitComboInput(const FGameplayTag& InputTag);

	bool TryCommitBufferedTransition();

	bool CanEnterComboStep(int32 ComboStepIndex) const;

	bool IsNotifyFromWeakAttackMontage(const FBranchingPointNotifyPayload& BranchingPointPayload) const;

	void BindMontageNotifyDelegate(UAnimInstance* AnimInstance);

	void UnbindMontageNotifyDelegate();

	void ResetRuntimeState();

	void FinishAbility(bool bWasCancelled);

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Khazan|WeakAttack|Animation",
		meta = (AllowPrivateAccess = "true"))
	TObjectPtr<class UAnimMontage> WeakAttackMontage = nullptr;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Khazan|WeakAttack|Animation",
		meta = (AllowPrivateAccess = "true", ClampMin = "0.0", Units = "s"))
	float ComboSectionInertializationDuration = 0.08f;

	UPROPERTY(Transient)
	TObjectPtr<class UAbilityTask_PlayMontageAndWait> ActiveMontageTask = nullptr;

	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;

	int32 CurrentComboStepIndex = INDEX_NONE;

	FGameplayTag BufferedInputTag;

	bool bAcceptingComboInput = false;

	// false: Open ~ Commit
	// true: Commit ~ End
	bool bComboCommitReached = false;
	
	bool bCanCancelToLocomotion = false;
};
