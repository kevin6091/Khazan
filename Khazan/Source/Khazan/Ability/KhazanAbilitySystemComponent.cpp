#include "Ability/KhazanAbilitySystemComponent.h"

#include "GameplayAbilitySpec.h"

bool UKhazanAbilitySystemComponent::TryActivateAbilitiesByInputTag(
	const FGameplayTag& InputTag)
{
	if (!InputTag.IsValid())
	{
		return false;
	}

	FScopedAbilityListLock AbilityListLock(*this);
	bool bActivatedAnyAbility = false;

	for (const FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		if (!AbilitySpec.Ability ||
			!AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
		{
			continue;
		}

		if (TryActivateAbility(AbilitySpec.Handle))
		{
			bActivatedAnyAbility = true;
		}
	}

	return bActivatedAnyAbility;
}