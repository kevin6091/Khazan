#pragma once

#include "CoreMinimal.h"
#include "Ability/KZActionAbility.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZGuardAbility.generated.h"

class UAbilityTask_PlayMontageAndWait;
class UAnimMontage;
class USoundBase;
class UNiagaraSystem;
class UKZAnimNotify_CombatEffect;

// Start/성공/End의 유한 Montage와 held Guard의 수명을 소유한다. 유지 포즈는 기존 ABP가 재생한다.
UCLASS()
class KHAZAN_API UKZGuardAbility : public UKZActionAbility
{
	GENERATED_BODY()

public:
	UKZGuardAbility();
	bool TryGuardHit(float StaminaDamage, AActor* Attacker, bool* OutParried = nullptr, bool bAllowParry = true);

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
	// Original Guard_Start.Notifies[3]: [0, .292) source seconds, mapped once
	// through the current Player_Guard_Start InGame inverse_map to [0, .146).
	// The window belongs to this activation, including moving Guard that skips Start.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry", meta = (ClampMin = "0.0", Units = "s"))
	float ParryWindowSeconds = 0.146f;
	// Original GuardSkillInfo.JustGuardReduseStaminaPowerRate=.5.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float ParryStaminaDamageScale = 0.5f;
	// Copies of the existing Brutal combat particles, including their parameters
	// and finite source windows. The success contact replaces only Root offsets.
	UPROPERTY(EditDefaultsOnly, Instanced, Category = "KZ|Guard|Parry")
	TArray<TObjectPtr<UKZAnimNotify_CombatEffect>> ParryBrutalEffects;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry")
	TObjectPtr<USoundBase> ParrySound;
	// Original JustGuard camera export: Loc.Y=-100 cm/Frequency=25 Hz,
	// FOV=3 deg/Frequency=25 Hz, FinalScale=.1, total notify=.35907653 s,
	// FadeIn/Out=.17953826 s. The extra gain is explicit assistant TEMP.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (ClampMin = "0.0"))
	float ParryCameraGain = 2.f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (Units = "cm"))
	FVector ParryCameraAmplitudeCm = FVector(0.f, -100.f, 0.f);
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (Units = "Hz"))
	FVector ParryCameraFrequencyHz = FVector(0.f, 25.f, 0.f);
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (Units = "s"))
	float ParryCameraActiveSeconds = 0.17953827f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (Units = "s"))
	float ParryCameraFadeSeconds = 0.17953826f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (Units = "deg"))
	float ParryCameraFOVAmplitudeDegrees = 3.f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera", meta = (Units = "Hz"))
	float ParryCameraFOVFrequencyHz = 25.f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Camera")
	float ParryCameraFinalScale = 0.1f;
	// User-selected /Game/VFX/03_SlashHit/KZ_Parring_Distort. Its original
	// camera-facing renderers are preserved; scale/tail are editable display tuning.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Distortion")
	TObjectPtr<UNiagaraSystem> ParryBillboardDistortion;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Distortion", meta = (ClampMin = "0.0"))
	float ParryBillboardDistortionScale = 1.f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Distortion", meta = (Units = "s"))
	float ParryBillboardDistortionTailSeconds = 0.5f; // Assistant TEMP emission window; particles drain after it.
	// TEMP lifetime bound for inactive emitters that never report completion.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Guard|Parry|Distortion", meta = (ClampMin = "0", Units = "s"))
	float ParryBillboardDistortionMaxLifetimeSeconds = 2.5f;
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
	double ParryWindowEndsAt = -1.0;
};
