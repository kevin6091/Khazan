#include "Ability/KZActionAbility.h"

#include "KZGameplayTags.h"

UKZActionAbility::UKZActionAbility()
{
	// 실행 상태를 멤버로 보관하기 위해 캐릭터마다 인스턴스 하나를 사용한다.
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalOnly;

	// InputEnd 전에는 다른 Action을 막는다.
	BlockAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);

	// 새 Action이 성공적으로 시작되면 이전 Action을 취소한다.
	CancelAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);
}

void UKZActionAbility::ResetInputEnd()
{
	bInputEnded = false;

	if (IsActive())
	{
		SetShouldBlockOtherAbilities(true);
	}
}

void UKZActionAbility::SetInputEnded()
{
	if (!IsActive() || bInputEnded)
	{
		return;
	}

	bInputEnded = true;
	SetShouldBlockOtherAbilities(false);
}

void UKZActionAbility::EndAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const bool bReplicateEndAbility,
	const bool bWasCancelled)
{
	bInputEnded = false;
	
	if (OnEndAbilityGameplayEffect)
	{
		FGameplayEffectSpecHandle SpecHandle = MakeOutgoingGameplayEffectSpec(OnEndAbilityGameplayEffect);
		if (SpecHandle.IsValid())
		{
			(void) ApplyGameplayEffectSpecToOwner(Handle, ActorInfo, ActivationInfo, SpecHandle);
		}
	}	
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}
