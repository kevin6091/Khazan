#include "Ability/KZAbilitySystemComponent.h"

#include "GameplayAbilitySpec.h"
#include "Abilities/GameplayAbility.h"
#include "Abilities/GameplayAbilityTypes.h"

void UKZAbilitySystemComponent::AbilityInputTagPressed(const FGameplayTag& InputTag)
{
	// 유효한 입력만 Ability에 전달한다.
	if (!InputTag.IsValid())
	{
		return;
	}
	{
		// 순회 중 Spec 목록이 바뀌지 않게 잠근다.
		FScopedAbilityListLock AbilityListLock(*this);

		for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
		{
			// 정확히 같은 Input Tag의 Spec만 처리한다.
			if (!AbilitySpec.Ability || !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
			{
				continue;
			}

			AbilitySpec.InputPressed = true;

			// 아직 실행 중이 아니면 이 입력으로 Ability를 시작한다.
			if (!AbilitySpec.IsActive())
			{
				TryActivateAbility(AbilitySpec.Handle);
				continue;
			}

			// 이미 실행 중이면 Ability의 InputPressed()에 전달한다.
			AbilitySpecInputPressed(AbilitySpec);

			if (!AbilitySpec.IsActive())
			{
				continue;
			}

			UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance();

			if (!ensureMsgf(IsValid(PrimaryInstance),
			                TEXT("Input-routed Ability must use InstancedPerActor. Ability=%s"),
			                *GetNameSafe(AbilitySpec.Ability)))
			{
				continue;
			}

			// WaitInputPress 같은 GAS 입력 Task에도 알려준다.
			InvokeReplicatedEvent(EAbilityGenericReplicatedEvent::InputPressed,
			                      AbilitySpec.Handle,
			                      PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());
		}
	}
}

void UKZAbilitySystemComponent::AbilityInputTagReleased(const FGameplayTag& InputTag)
{
	// 버튼에서 손을 뗀 상태를 같은 Input Tag의 Spec에 전달한다.
	if (!InputTag.IsValid())
	{
		return;
	}
	{
		FScopedAbilityListLock AbilityListLock(*this);

		for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
		{
			// 실행 여부와 상관없이 눌림 상태부터 해제한다.
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

			// WaitInputRelease 같은 GAS 입력 Task에도 알려준다.
			InvokeReplicatedEvent(
				EAbilityGenericReplicatedEvent::InputReleased,
				AbilitySpec.Handle,
				PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());
		}
	}

}

void UKZAbilitySystemComponent::AbilityInputTagCanceled(const FGameplayTag& InputTag)
{
	// Canceled는 정상 Release가 아니므로 눌림 상태만 지운다.
	if (!InputTag.IsValid())
	{
		return;
	}

	{
		FScopedAbilityListLock AbilityListLock(*this);

		for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
		{
			if (!AbilitySpec.Ability ||
				!AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
			{
				continue;
			}

			AbilitySpec.InputPressed = false;
		}
	}
}

bool UKZAbilitySystemComponent::TryActivateAbilityByInputTag(const FGameplayTag& InputTag)
{
	// Input Tag로 실행 가능한 Ability 하나를 찾는다.
	if (!InputTag.IsValid())
	{
		return false;
	}

	FScopedAbilityListLock AbilityListLock(*this);

	for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		// 이미 실행 중이거나 태그가 다른 Spec은 건너뛴다.
		if (!AbilitySpec.Ability || AbilitySpec.IsActive() || !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
		{
			continue;
		}

		if (TryActivateAbility(AbilitySpec.Handle))
		{
			return true;
		}
	}

	return false;
}

void UKZAbilitySystemComponent::SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase Phase)
{
	// ASC는 명령을 쌓지 않고 현재 활성 콤보 Ability에 바로 알린다.
	if (!CommandTag.IsValid())
	{
		return;
	}

	const FKZComboCommand Command(CommandTag, Phase);

	ComboCommandEvent.Broadcast(Command);
}
