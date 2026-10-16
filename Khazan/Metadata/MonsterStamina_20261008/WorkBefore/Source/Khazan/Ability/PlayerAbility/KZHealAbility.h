#pragma once

#include "CoreMinimal.h"
#include "Ability/KZActionAbility.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZHealAbility.generated.h"

class UAnimMontage;
class USceneComponent;

UCLASS()
class KHAZAN_API UKZHealAbility : public UKZActionAbility
{
	GENERATED_BODY()

public:
	UKZHealAbility();

protected:
	virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayTagContainer* SourceTags = nullptr, const FGameplayTagContainer* TargetTags = nullptr,
		FGameplayTagContainer* OptionalRelevantTags = nullptr) const override;
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;

private:
	bool StoreWeapons();
	void RestoreWeapons();
	void PlayHealMontage(UAnimMontage* Montage);
	UFUNCTION()
	void HandleMontageNotify(FName NotifyName, const FBranchingPointNotifyPayload& Payload);
	UFUNCTION()
	void HandleMontageCompleted();
	UFUNCTION()
	void HandleMontageAborted();

	UPROPERTY(EditDefaultsOnly, Category = "KZ|Heal")
	TObjectPtr<UAnimMontage> HealMontage;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Heal")
	TObjectPtr<UAnimMontage> DrawMontage;
	// Instant HP modifier. The GE owns the user-selected recovery amount.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Heal")
	TSubclassOf<UGameplayEffect> HealEffect;
	// Existing Player socket offsets. These are presentation attachment names, not equipment state.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Heal")
	FName LeftBackSocket = TEXT("Weapon_L_BackPack소켓");
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Heal")
	FName RightBackSocket = TEXT("Weapon_R_BackPack소켓");

	struct FStoredWeapon
	{
		TWeakObjectPtr<USceneComponent> Component;
		TWeakObjectPtr<USceneComponent> Parent;
		FName HandSocket;
		FTransform RelativeTransform;
	};
	// Only attachments changed by this execution; original scale/offsets survive every exit.
	TArray<FStoredWeapon> StoredWeapons;

	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;
	FKZMovementConstraintHandle MovementHandle;
	int32 ActiveMontageInstanceId = INDEX_NONE;
	// Execution-local once guard; HP itself remains solely in the AttributeSet.
	bool bHealApplied = false;
};
