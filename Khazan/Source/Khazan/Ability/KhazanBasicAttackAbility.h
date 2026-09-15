#pragma once

#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "KhazanBasicAttackAbility.generated.h"

UCLASS()
class KHAZAN_API UKhazanBasicAttackAbility : public UGameplayAbility
{
	GENERATED_BODY()

public:
	UKhazanBasicAttackAbility();

protected:
	virtual void ActivateAbility(
		const FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		const FGameplayEventData* TriggerEventData) override;
};