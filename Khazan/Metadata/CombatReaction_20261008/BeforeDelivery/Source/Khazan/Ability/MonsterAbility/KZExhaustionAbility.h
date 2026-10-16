#pragma once

#include "CoreMinimal.h"
#include "Ability/KZGameplayAbility.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "TimerManager.h"
#include "KZExhaustionAbility.generated.h"

class AKZMonster;
class UKZBrutalAttackAbility;
class UAbilityTask_PlayMontageAndWait;
class UAnimInstance;
class UAnimMontage;
struct FKZMonsterStaminaSettings;

/** Owns the victim's exhaustion, paired reactions, and recovery after both completions. */
UCLASS()
class KHAZAN_API UKZExhaustionAbility : public UKZGameplayAbility
{
	GENERATED_BODY()
public:
	UKZExhaustionAbility();
	bool IsAvailableForBrutalAttack() const;
	bool ClaimBrutalAttack(UKZBrutalAttackAbility* Attacker, bool bFromBack);
	bool PlayBrutalReaction(uint8 Phase);
	void NotifyBrutalAttackerFinished(bool bWasCancelled);
	bool HasBrutalPartner() const { return BrutalPartner.IsValid(); }

protected:
	virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayTagContainer* SourceTags = nullptr, const FGameplayTagContainer* TargetTags = nullptr,
		FGameplayTagContainer* OptionalRelevantTags = nullptr) const override;
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;

private:
	// Local montage execution phase, not another source of shared gameplay state.
	enum class EPhase : uint8 { None, Start, Loop, Brutal1, Brutal2, End };
	AKZMonster* GetMonster() const;
	const FKZMonsterStaminaSettings* GetSettings() const;
	bool IsAlive() const;
	bool PlaySection(UAnimMontage* Montage, FName Section, EPhase Phase);
	void ClearMontageTask(bool bStopMontage);
	void BeginRecovery();
	void CompleteBrutalPair();
	void CancelBrutalPair(bool bAbortAttacker);
	void FinishAbility(bool bWasCancelled);
	void FinishDeath(bool bWasCancelled);
	UFUNCTION() void HandleMontageCompleted();
	UFUNCTION() void HandleMontageAborted();
	void HandleRecoveryTimeout();

	UPROPERTY(Transient) TObjectPtr<UAbilityTask_PlayMontageAndWait> MontageTask;
	UPROPERTY(Transient) TObjectPtr<UAnimMontage> PlayingMontage;
	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;
	TWeakObjectPtr<UKZBrutalAttackAbility> BrutalPartner;
	FKZMovementConstraintHandle MovementHandle;
	FTimerHandle RecoveryTimer;
	EPhase CurrentPhase = EPhase::None;
	bool bFromBack = false;
	bool bAttackerCompleted = false;
	bool bVictimCompleted = false;
	bool bEnding = false;
};
