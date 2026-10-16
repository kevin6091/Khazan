#pragma once
#include "CoreMinimal.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Engine/EngineTypes.h"
#include "KZFallAbility.generated.h"

/** Fall presentation and airborne X use the existing Combo execution and actual CMC Landed event. */
UCLASS(Blueprintable)
class KHAZAN_API UKZFallAbility : public UKZComboActionAbility
{
	GENERATED_BODY()
public:
	UKZFallAbility();
	bool IsPlungeAttack() const { return bPlungeAttack; }
	virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayTagContainer* SourceTags = nullptr, const FGameplayTagContainer* TargetTags = nullptr,
		FGameplayTagContainer* OptionalRelevantTags = nullptr) const override;
protected:
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;
	virtual void ProcessMontageNotify(FName NotifyName) override;
private:
	UFUNCTION() void HandleLanded(const FHitResult& Hit);
	UPROPERTY(EditDefaultsOnly, Category = "Fall") bool bPlungeAttack = false;
	UPROPERTY(EditDefaultsOnly, Category = "Fall") FName LoopNode = TEXT("Loop");
	UPROPERTY(EditDefaultsOnly, Category = "Fall") FName LandingNode = TEXT("Land");
	TWeakObjectPtr<class ACharacter> BoundCharacter;
	TOptional<ECollisionResponse> PreviousPawnResponse;
};
