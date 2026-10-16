#pragma once

#include "CoreMinimal.h"
#include "Ability/KZActionAbility.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZGuardAbility.generated.h"

class UAbilityTask_PlayMontageAndWait;
class UAnimMontage;

// Start/성공/End의 유한 Montage와 held Guard의 수명을 소유한다. 유지 포즈는 기존 ABP가 재생한다.
UCLASS()
class KHAZAN_API UKZGuardAbility : public UKZActionAbility
{
	GENERATED_BODY()

public:
	UKZGuardAbility();
	bool TryGuardHit(float StaminaDamage, AActor* Attacker);

protected:
	virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayTagContainer* SourceTags = nullptr, const FGameplayTagContainer* TargetTags = nullptr,
		FGameplayTagContainer* OptionalRelevantTags = nullptr) const override;
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void InputReleased(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;

private:
	bool PlaySection(FName Section);
	bool IsGuardInputHeld() const;
	void ReleaseGuardState();
	void FinishAbility(bool bWasCancelled);

	UFUNCTION()
	void HandleMontageCompleted();
	UFUNCTION()
	void HandleMontageAborted();
	UFUNCTION()
	void HandleMontageNotify(FName NotifyName, const FBranchingPointNotifyPayload& Payload);
	UFUNCTION()
	void HandleMoveInput(FGameplayEventData Payload);

	// Sections: Start, Suc_F, Suc_L, Suc_R, End. Authored Next는 모두 None.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard")
	TObjectPtr<UAnimMontage> GuardMontage;
	// 무비용 infinite GE. held 동안 State.Guarding만 부여한다.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard")
	TSubclassOf<UGameplayEffect> GuardStateEffect;
	// Instant Stamina modifier. SetByCaller DataName=GuardStaminaDamage, 음수 magnitude.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard")
	TSubclassOf<UGameplayEffect> GuardHitStaminaEffect;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard")
	TSubclassOf<UGameplayEffect> GuardHitRecoveryDelayEffect;
	// 원작 일반 GuardSkillInfo.GuardStaminaRecoveryDelayTime = 0.5초.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard", meta = (ClampMin = "0.0", Units = "s"))
	float GuardStaminaRecoveryDelay = 0.5f;
	// 임시 표현 튜닝: 기존 Combo 이동 복귀값을 재사용. 원작 동일값 미확인.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard", meta = (ClampMin = "0.0", Units = "s"))
	float LocomotionExitInertializationDuration = 0.24f;

	UPROPERTY(Transient)
	TObjectPtr<UAbilityTask_PlayMontageAndWait> ActiveMontageTask;
	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;
	FActiveGameplayEffectHandle GuardStateHandle;
	FKZMovementConstraintHandle GuardMovementHandle;
	FName CurrentSection;
	int32 ActiveMontageInstanceId = INDEX_NONE;
};
