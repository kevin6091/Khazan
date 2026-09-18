#include "Ability/KhazanAbilitySystemComponent.h"

#include "GameplayAbilitySpec.h"
#include "Abilities/GameplayAbility.h"

void UKhazanAbilitySystemComponent::AbilityInputTagPressed(const FGameplayTag& InputTag)
{
	if (!InputTag.IsValid())
	{
		return;
	}
	
	// Spec 순회 동안 Ability활성, 종료가 변경을 일으키는걸 방지
	FScopedAbilityListLock AbilityListLock(*this);
	
	for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		// 정확히 같은 태그를 가진 Spec만 선택
		if (!AbilitySpec.Ability || !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
		{
			continue;
		}
		
		AbilitySpec.InputPressed = true;
		
		// 첫 클릭 처리
		if (!AbilitySpec.IsActive())
		{
			TryActivateAbility(AbilitySpec.Handle);
			continue;
		}
			
		AbilitySpecInputPressed(AbilitySpec);
		
		if (!AbilitySpec.IsActive())
		{
			continue;
		}

		UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance();
		
		if (!ensureMsgf(IsValid(PrimaryInstance), TEXT("Input-routed Ability must use InstancedPerActor. Ability=%s"),
		*GetNameSafe(AbilitySpec.Ability)))
		{
			continue;
		}

		// 미래의 UAbilityTask_WaitInputPress delegate 깨움 
		InvokeReplicatedEvent(EAbilityGenericReplicatedEvent::InputPressed, 
			AbilitySpec.Handle, 
			PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());
	}
}

void UKhazanAbilitySystemComponent::AbilityInputTagReleased(const FGameplayTag& InputTag)
{
	if (!InputTag.IsValid())
	{
		return;
	}

	FScopedAbilityListLock AbilityListLock(*this);

	for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		if (!AbilitySpec.Ability || !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
		{
			continue;
		}

		AbilitySpec.InputPressed = false;

		if (!AbilitySpec.IsActive())
		{
			continue;
		}

		AbilitySpecInputReleased(AbilitySpec);

		if (!AbilitySpec.IsActive())
		{
			continue;
		}
		
		UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance();

		if (!ensureMsgf(IsValid(PrimaryInstance), TEXT("Input-routed Ability must use InstancedPerActor. Ability=%s"),
			*GetNameSafe(AbilitySpec.Ability)))
		{
			continue;
		}
		
		InvokeReplicatedEvent(
			EAbilityGenericReplicatedEvent::InputReleased,
			AbilitySpec.Handle,
			PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());
	}
}