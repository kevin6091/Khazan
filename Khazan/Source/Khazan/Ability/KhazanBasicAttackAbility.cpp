#include "Ability/KhazanBasicAttackAbility.h"

#include "LogChannels.h"

UKhazanBasicAttackAbility::UKhazanBasicAttackAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
}

void UKhazanBasicAttackAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	if (!CommitAbility(SpecHandle, ActorInfo, ActivationInfo))
	{
		EndAbility(SpecHandle, ActorInfo, ActivationInfo, /* bReplicateEndAbility */ true, /* bWasCancelled */ true);

		return;
	}
	
	UE_LOG(LogAbility, Log, TEXT("%s activated ability %s."),
	*GetNameSafe(ActorInfo ? ActorInfo->AvatarActor.Get() : nullptr),
	*GetNameSafe(GetClass()));
	
	EndAbility(SpecHandle, ActorInfo, ActivationInfo, /* bReplicateEndAbility */ true, /* bWasCancelled */ false);
}