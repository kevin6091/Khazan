#include "Ability/KZAbilitySystemComponent.h"

#include "GameplayAbilitySpec.h"
#include "Abilities/GameplayAbility.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/KZActionAbility.h"
#include "Combo/KZComboDefinitionData.h"


bool UKZAbilitySystemComponent::HasComboEntry(const UKZComboDefinitionData* Definition, FName EntryNodeId,
                                              FGameplayAbilitySpecHandle IgnoreHandle)
{
	if (!IsValid(Definition) || EntryNodeId.IsNone())
	{
		return false;
	}

	FScopedAbilityListLock AbilityListLock(*this);

	for (const FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		if (!AbilitySpec.Ability || AbilitySpec.Handle == IgnoreHandle)
		{
			continue;
		}

		const UKZComboActionAbility* ComboActionAbility = Cast<UKZComboActionAbility>(AbilitySpec.Ability);

		if (IsValid(ComboActionAbility) &&
			ComboActionAbility->GetComboDefinition() == Definition &&
			ComboActionAbility->GetEntryNodeId() == EntryNodeId)
		{
			return true;
		}
	}

	return false;
}

bool UKZAbilitySystemComponent::TryActivateComboEntry(const UKZComboDefinitionData* Definition, FName EntryNodeId,
                                                      FGameplayAbilitySpecHandle IgnoreHandle, bool bInputPressed)
{
	if (!IsValid(Definition) || EntryNodeId.IsNone())
	{
		return false;
	}

	FScopedAbilityListLock AbilityListLock(*this);
	FGameplayAbilitySpec* TargetSpec = nullptr;

	for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		if (!AbilitySpec.Ability || AbilitySpec.Handle == IgnoreHandle)
		{
			continue;
		}

		const UKZComboActionAbility* ComboAbility = Cast<UKZComboActionAbility>(AbilitySpec.Ability);

		if (!IsValid(ComboAbility) ||
			ComboAbility->GetComboDefinition() != Definition ||
			ComboAbility->GetEntryNodeId() != EntryNodeId)
		{
			continue;
		}

		if (!ensureMsgf(TargetSpec == nullptr, TEXT("Two granted Combo Abilities use the same EntryNodeId: %s"),
		                *EntryNodeId.ToString()))
		{
			return false;
		}

		TargetSpec = &AbilitySpec;
	}

	if (TargetSpec == nullptr)
	{
		return false;
	}

	const bool bPreviousInputPressed = TargetSpec->InputPressed;
	
	const bool bHasInputBinding = !TargetSpec->GetDynamicSpecSourceTags().IsEmpty();
	
	TargetSpec->InputPressed = bInputPressed && bHasInputBinding;;

	if (TryActivateAbility(TargetSpec->Handle))
	{
		return true;
	}

	TargetSpec->InputPressed = bPreviousInputPressed;
	return false;
}

void UKZAbilitySystemComponent::AbilityInputTagPressed(const FGameplayTag& InputTag, FGameplayAbilitySpecHandle RequestedHandle)
{
	// 유효한 입력만 Ability에 전달한다.
	if (!InputTag.IsValid())
	{
		return;
	}
	{
		// 순회 중 Spec 목록이 바뀌지 않게 잠근다.
		FScopedAbilityListLock AbilityListLock(*this);

		// 이미 실행 중인 동일 입력 Spec이 입력을 계속 소유한다.
		for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
		{
			// 특정 Spec을 요청했을때. 현재 검사 중인 Spec이 그 Spec이 아니라면 Continue
			if (RequestedHandle.IsValid() && AbilitySpec.Handle != RequestedHandle)
			{
				continue;
			}
			
			// 정확히 같은 Input Tag의 Spec만 처리한다.
			if (!AbilitySpec.Ability || !AbilitySpec.IsActive() || !AbilitySpec.GetDynamicSpecSourceTags().
				HasTagExact(InputTag))
			{
				continue;
			}
			
			// PrimaryInstance가 UKZActionAbility이고 InputEnd를 지났다면
			// 아래 일반 InputPressed 전달보다 먼저 현재 실행을 취소하고 
			// 같은 Spec Handle을 새 activation으로 다시 시작해야 한다.

			// 재입력 처리.
			UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance();

			if (!ensureMsgf(IsValid(PrimaryInstance),
			                TEXT("Input-routed Ability must use InstancedPerActor. Ability=%s"),
			                *GetNameSafe(AbilitySpec.Ability)))
			{
				return;
			}

			UKZActionAbility* ActionAbility = Cast<UKZActionAbility>(PrimaryInstance);

			if (IsValid(ActionAbility) && ActionAbility->HasInputEnded())
			{
				const FGameplayAbilitySpecHandle RestartHandle = AbilitySpec.Handle;

				// 현재 실행을 취소하기 전에 새 실행 가능 여부를 확인한다.
				if (!AbilityActorInfo.IsValid() || !PrimaryInstance->CanActivateAbility(RestartHandle, AbilityActorInfo.Get()))
				{
					return;
				}
				
				// 아직 active인 이전 회수 모션 실행을 먼저 끝낸다.
				CancelAbilityHandle(RestartHandle);

				// 취소 과정에서 Spec이 제거될 수 있으므로 다시 찾는다.
				FGameplayAbilitySpec* RestartSpec = FindAbilitySpecFromHandle(RestartHandle);

				if (RestartSpec == nullptr || RestartSpec->IsActive())
				{
					return;
				}

				// 새 activation이 "버튼을 누른 상태로 시작했다"는 것을 보게 한다.
				RestartSpec->InputPressed = true;

				if (!TryActivateAbility(RestartHandle))
				{
					RestartSpec->InputPressed = false;
				}

				// 재활성화 실패 시에도 다른 동일 InputTag 후보로 넘기지 않는다.
				return;
			}

			AbilitySpec.InputPressed = true;
			AbilitySpecInputPressed(AbilitySpec);

			// InputPressed 처리 중 Ability가 끝날 수도 있다.
			if (!AbilitySpec.IsActive())
			{
				return;
			}

			if (AbilitySpec.IsActive())
			{
				InvokeReplicatedEvent(EAbilityGenericReplicatedEvent::InputPressed, AbilitySpec.Handle,
				                      PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());
			}

			// 활성 Spec 하나를 찾았으므로 비활성 후보 루프로 내려가지 않는다.
			return;
		}

		// 비활성 후보를 grant 순서대로 시도한다.
		for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
		{
			if (RequestedHandle.IsValid() && AbilitySpec.Handle != RequestedHandle)
			{
				continue;
			}
			
			if (!AbilitySpec.Ability || AbilitySpec.IsActive() || !AbilitySpec.GetDynamicSpecSourceTags().
			                                                                   HasTagExact(InputTag))
			{
				continue;
			}

			AbilitySpec.InputPressed = true;

			if (TryActivateAbility(AbilitySpec.Handle))
			{
				// 이 Spec이 이번 press의 소유자다.
				return;
			}
			// 이 후보는 활성화되지 않았으므로 소유권을 돌려놓는다.
			AbilitySpec.InputPressed = false;
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
			if (!AbilitySpec.Ability || !AbilitySpec.InputPressed ||
				!AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
			{
				continue;
			}

			AbilitySpec.InputPressed = false;

			// press 후 Ability가 먼저 끝났더라도
			// 다른 동일 InputTag Spec에 Release를 넘기면 안 된다.
			if (!AbilitySpec.IsActive())
			{
				return;
			}

			AbilitySpecInputReleased(AbilitySpec);

			// InputReleased override에서 Ability가 끝날 수 있다.
			if (!AbilitySpec.IsActive())
			{
				return;
			}

			UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance();

			if (!ensureMsgf(IsValid(PrimaryInstance),
			                TEXT("Input-routed Ability must use InstancedPerActor. Ability=%s"),
			                *GetNameSafe(AbilitySpec.Ability)))
			{
				continue;
			}

			// WaitInputRelease 같은 GAS 입력 Task에도 알려준다.
			InvokeReplicatedEvent(EAbilityGenericReplicatedEvent::InputReleased, AbilitySpec.Handle,
			                      PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());

			// 선택된 Spec 하나만 처리한다.
			return;
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

	FScopedAbilityListLock AbilityListLock(*this);

	for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		// 반드시 AbilitySpec.InputPressed가 true인 실제 입력 소유자만 선택해야 한다.
		if (!AbilitySpec.Ability ||
			!AbilitySpec.InputPressed ||
			!AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
		{
			continue;
		}

		AbilitySpec.InputPressed = false;

		if (AbilitySpec.IsActive())
		{
			// WaitInputRelease는 깨우지 않고  선택된 실행 자체를 canceled 종료한다.
			CancelAbilityHandle(AbilitySpec.Handle);
		}
		return;
	}

	return;
}

void UKZAbilitySystemComponent::SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase Phase)
{
	// ASC는 명령을 쌓지 않고 현재 활성 콤보 Ability에 바로 알린다.
	if (!CommandTag.IsValid())
	{
		return;
	}

	switch (Phase)
	{
	case EKZComboCommandPhase::Begin:
		// Started 중복은 하나의 물리 hold로 본다.
		if (HeldComboCommands.HasTagExact(CommandTag))
		{
			return;
		}

		HeldComboCommands.AddTag(CommandTag);
		break;

	case EKZComboCommandPhase::Release:
		// Begin을 받지 않은 Release는 공격 사건으로 만들지 않는다.
		if (!HeldComboCommands.HasTagExact(CommandTag))
		{
			return;
		}

		// Release Edge에서는 자기 자신이 더 이상 held가 아니어야 한다.
		HeldComboCommands.RemoveTag(CommandTag);
		break;

	case EKZComboCommandPhase::Cancel:
		// Cancel은 정상 Release Edge를 만들지 않지만 구독자 cleanup은 알린다.
		HeldComboCommands.RemoveTag(CommandTag);
		break;

	default:
		// Notify 사건은 Controller/ASC로 제출하지 않는다.
		return;
	}

	const FKZComboCommand Command(CommandTag, Phase);
	ComboCommandEvent.Broadcast(Command);
}

void UKZAbilitySystemComponent::ClearComboCommands()
{
	const FGameplayTagContainer CommandsToCancel = HeldComboCommands;

	for (const FGameplayTag& CommandTag : CommandsToCancel)
	{
		SubmitComboCommand(CommandTag, EKZComboCommandPhase::Cancel);
	}

	HeldComboCommands.Reset();

	// UnPossess 이후 이전 Pawn 입력 소유권이 Spec에 남지 않게 한다.
	FScopedAbilityListLock AbilityListLock(*this);

	for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		AbilitySpec.InputPressed = false;
	}
}
