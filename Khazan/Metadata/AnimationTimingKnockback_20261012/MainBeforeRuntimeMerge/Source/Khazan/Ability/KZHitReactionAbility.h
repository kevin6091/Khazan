#pragma once

#include "CoreMinimal.h"
#include "Ability/KZGameplayAbility.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimEnums.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Engine/EngineTypes.h"
#include "KZHitReactionAbility.generated.h"

class AKZCharacter;
class UAbilityTask_PlayMontageAndWait;
class UAbilityTask_ApplyRootMotionJumpForce;
class UAnimInstance;
class UAnimMontage;
class UCharacterMovementComponent;

/** Owns one forced hit/shield reaction and its authored montage chain. */
UCLASS()
class KHAZAN_API UKZHitReactionAbility : public UKZGameplayAbility
{
	GENERATED_BODY()

public:
	UKZHitReactionAbility();
	bool IsShieldReaction() const;
	bool IsGroundHitReaction() const;

protected:
	virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayTagContainer* SourceTags = nullptr, const FGameplayTagContainer* TargetTags = nullptr,
		FGameplayTagContainer* OptionalRelevantTags = nullptr) const override;
	virtual bool ShouldAbilityRespondToEvent(const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayEventData* Payload) const override;
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;

private:
	// Assistant TEMP, requested short player control lock; not original timing.
	// Only Player damage uses it. Monster/shield authored chains keep their lifetime.
	UPROPERTY(EditDefaultsOnly, Category = "Reaction|Player", meta = (ClampMin = "0", Units = "s"))
	float PlayerControlLockSeconds = 0.1f;
	FTimerHandle PlayerControlTimer;
	void FinishPlayerControlLock();
	UAnimMontage* SelectMontage(const FGameplayAbilityActorInfo* ActorInfo, FGameplayTag Event, bool bRandom) const;
	void RestoreMovementMode();
	void RestoreRootMotionMode();
	void ClearMotionTask();
	void ClearMontageTask();
	void FinishAbility(bool bWasCancelled);
	UFUNCTION() void HandleMontageCompleted();
	UFUNCTION() void HandleMontageAborted();
	UFUNCTION() void HandleMotionFinished();
	UFUNCTION() void HandleMontageNotify(FName NotifyName, const FBranchingPointNotifyPayload& Payload);

	UPROPERTY(Transient) TObjectPtr<UAbilityTask_PlayMontageAndWait> MontageTask;
	UPROPERTY(Transient) TObjectPtr<UAbilityTask_ApplyRootMotionJumpForce> MotionTask;
	UPROPERTY(Transient) TObjectPtr<UAnimMontage> PlayingMontage;
	TWeakObjectPtr<AKZCharacter> BoundCharacter;
	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;
	TWeakObjectPtr<UCharacterMovementComponent> BoundMovement;
	FKZMovementConstraintHandle MovementHandle;
	FGameplayTag CurrentEvent;
	int32 MontageInstanceId = INDEX_NONE;
	// Invalidates setup returning from synchronous cancellation/retrigger callbacks.
	uint32 ExecutionSerial = 0;
	EMovementMode PreviousMovementMode = MOVE_None;
	uint8 PreviousCustomMovementMode = 0;
	bool bOwnsFlyingMode = false;
	ERootMotionMode::Type PreviousRootMotionMode = ERootMotionMode::NoRootMotionExtraction;
	bool bOwnsRootMotionMode = false;
	bool bEnding = false;
};
