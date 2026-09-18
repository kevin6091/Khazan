#include "Ability/KhazanWeakAttackAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_WaitGameplayEvent.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "GameFramework/Character.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"

namespace KhazanWeakAttackAbilityPrivate
{
	const FName MontageTaskName(TEXT("WeakAttackComboMontage"));
	
	const FName ComboInputOpenNotifyName(TEXT("ComboInputOpen"));
	const FName ComboCommitNotifyName(TEXT("ComboCommit"));
	const FName ComboInputEndNotifyName(TEXT("ComboInputEnd"));
	
	const FName ComboSectionNames[]
	{
		TEXT("Attack01"),
		TEXT("Attack02"),
		TEXT("Attack03"),
		TEXT("Attack04"),
		TEXT("Attack05")
	};
	
	constexpr int32 ComboSectionCount = UE_ARRAY_COUNT(ComboSectionNames);
	constexpr int32 Attack01Index = 0;
	constexpr int32 Attack05Index = 4;
	
	bool IsValidComboStepIndex(const int32 ComboStepIndex)
	{
		return
			ComboStepIndex >= 0 &&
			ComboStepIndex < ComboSectionCount;
	}
}

UKhazanWeakAttackAbility::UKhazanWeakAttackAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
}

void UKhazanWeakAttackAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	UnbindMontageNotifyDelegate();
	ResetRuntimeState();
	
	ACharacter* Character = ActorInfo ? Cast<ACharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
	UAnimInstance* AnimInstance = ActorInfo ? ActorInfo->GetAnimInstance() : nullptr;
	
	const auto HasComboSection = [this](const int32 ComboStepIndex)
	{
		return IsValid(WeakAttackMontage) &&
		KhazanWeakAttackAbilityPrivate::IsValidComboStepIndex(ComboStepIndex) &&
		WeakAttackMontage->GetSectionIndex(KhazanWeakAttackAbilityPrivate::ComboSectionNames[ComboStepIndex]) != INDEX_NONE;	
	};
	
	if (!IsValid(Character) || !IsValid(AnimInstance) || 
		!HasComboSection(0) || 
		!HasComboSection(1) ||
		!HasComboSection(2) ||
		!HasComboSection(3) || 
		!HasComboSection(4))
	{
		UE_LOG(LogAbility, Error, TEXT( "%s could not start %s. " "Character=%s, AnimInstance=%s, " "Montage=%s,"
			" Attack01=%s, Attack02=%s, Attack03=%s. Attack04=%s, Attack05=%s."),
			*GetNameSafe(ActorInfo ? ActorInfo->AvatarActor.Get() : nullptr),
			*GetNameSafe(GetClass()),
			*GetNameSafe(Character),
			*GetNameSafe(AnimInstance),
			*GetNameSafe(WeakAttackMontage),
			HasComboSection(0) ? TEXT("valid") : TEXT("missing"),
			HasComboSection(1) ? TEXT("valid") : TEXT("missing"),
			HasComboSection(2) ? TEXT("valid") : TEXT("missing"),
			HasComboSection(3) ? TEXT("valid") : TEXT("missing"),
			HasComboSection(4) ? TEXT("valid") : TEXT("missing"));

		EndAbility(SpecHandle, ActorInfo, ActivationInfo, true, true);

		return;
	}
	
	if (!CommitAbility(SpecHandle, ActorInfo, ActivationInfo))
	{
		EndAbility(SpecHandle, ActorInfo, ActivationInfo, true, true);
		return;
	}
	
	// MoveStart 입력 받기위한 이벤트Task
	UAbilityTask_WaitGameplayEvent* MoveStartedTask = UAbilityTask_WaitGameplayEvent::WaitGameplayEvent(
		this,
		KhazanGameplayTags::Input_Action_Move,
		nullptr,
		false,
		true);

	if (!IsValid(MoveStartedTask))
	{
		FinishAbility(true);
		return;
	}

	// 콜백 함수 등록
	MoveStartedTask->EventReceived.AddDynamic(this, &ThisClass::HandleMoveInputStarted);
	// 활성화
	MoveStartedTask->ReadyForActivation();
	
	BindMontageNotifyDelegate(AnimInstance);
	
	if (!StartWeakAttackMontage())
	{
		return;
	}

	// Test
	UE_LOG(LogAbility, Log, TEXT("%s started %s at section %s."),
	*GetNameSafe(Character),
	*GetNameSafe(GetClass()),
	*KhazanWeakAttackAbilityPrivate::ComboSectionNames[0].ToString());
}

void UKhazanWeakAttackAbility::InputPressed(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo)
{
	if (!IsActive())
	{
		return;
	}

	SubmitComboInput(KhazanGameplayTags::Input_Action_WeakAttack);
}



bool UKhazanWeakAttackAbility::StartWeakAttackMontage()
{
	if (!IsActive() || !IsValid(WeakAttackMontage) || !BoundAnimInstance.IsValid() || IsValid(ActiveMontageTask))
	{
		UE_LOG(LogAbility, Error, TEXT("%s could not start the WeakAttack montage."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return false;
	}
	
	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait:: CreatePlayMontageAndWaitProxy(
					this,
					KhazanWeakAttackAbilityPrivate::MontageTaskName,
					WeakAttackMontage,
					1.f,
					KhazanWeakAttackAbilityPrivate::ComboSectionNames[0],
					true,
					1.f,
					0.f,
					true);
	
	if (!IsValid(Task))
	{
		UE_LOG(LogAbility, Error, TEXT("%s failed to create the WeakAttack montage task."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return false;
	}
	
	ActiveMontageTask = Task;
	
	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	
	// Attack01을 현재 실행 중인 콤보 타수로 확정한다.
	CurrentComboStepIndex = KhazanWeakAttackAbilityPrivate::Attack01Index;
	
	Task->ReadyForActivation();
	
	return IsActive() && ActiveMontageTask == Task;
}

void UKhazanWeakAttackAbility::SubmitComboInput(const FGameplayTag& InputTag)
{
	if (!bAcceptingComboInput || BufferedInputTag.IsValid() || !InputTag.MatchesTagExact(KhazanGameplayTags::Input_Action_WeakAttack))
	{
		return;
	}

	const int32 NextComboStepIndex = CurrentComboStepIndex + 1;

	if (!CanEnterComboStep(NextComboStepIndex))
	{
		return;
	}

	BufferedInputTag = InputTag;
	
	if (bComboCommitReached)
	{
		TryCommitBufferedTransition();
	}
}

bool UKhazanWeakAttackAbility::TryCommitBufferedTransition()
{
	bAcceptingComboInput = false;
	bComboCommitReached = false;
	
	if (!IsActive() || !BufferedInputTag.IsValid())
	{
		return false;
	}

	const FGameplayTag InputToConsume = BufferedInputTag;

	BufferedInputTag = FGameplayTag();

	if (!InputToConsume.MatchesTagExact(KhazanGameplayTags::Input_Action_WeakAttack))
	{
		return false;
	}

	if (!KhazanWeakAttackAbilityPrivate::IsValidComboStepIndex(CurrentComboStepIndex))
	{
		return false;
	}

	const int32 NextComboStepIndex = CurrentComboStepIndex + 1;

	if (!CanEnterComboStep(NextComboStepIndex))
	{
		return false;
	}

	UAbilitySystemComponent* AbilitySystemComponent = GetAbilitySystemComponentFromActorInfo();

	UAnimInstance* AnimInstance = GetCurrentActorInfo() ? 
	GetCurrentActorInfo()->GetAnimInstance() : nullptr;

	if (!IsValid(AbilitySystemComponent) ||
		!IsValid(AnimInstance) ||
		!AbilitySystemComponent->IsAnimatingAbility(this) ||
		GetCurrentMontage() != WeakAttackMontage.Get())
	{
		return false;
	}

	const int32 PreviousComboStepIndex = CurrentComboStepIndex;

	CurrentComboStepIndex = NextComboStepIndex;
	bCanCancelToLocomotion = false;
	
	if (ComboSectionInertializationDuration > 0.f)
	{
		AnimInstance->RequestMontageInertialization(WeakAttackMontage, ComboSectionInertializationDuration, nullptr);
	}

	MontageJumpToSection(KhazanWeakAttackAbilityPrivate::ComboSectionNames[CurrentComboStepIndex]);

	UE_LOG(LogAbility, Log, TEXT("%s transitioned WeakAttack %s -> %s."),
		*GetNameSafe(GetAvatarActorFromActorInfo()),
		*KhazanWeakAttackAbilityPrivate::ComboSectionNames[PreviousComboStepIndex].ToString(),
		*KhazanWeakAttackAbilityPrivate::ComboSectionNames[CurrentComboStepIndex].ToString());

	return true;
}

bool UKhazanWeakAttackAbility::CanEnterComboStep(const int32 ComboStepIndex) const
{
	if (!KhazanWeakAttackAbilityPrivate::IsValidComboStepIndex(ComboStepIndex) ||
		!IsValid(WeakAttackMontage) ||
		WeakAttackMontage->GetSectionIndex(KhazanWeakAttackAbilityPrivate::ComboSectionNames[ComboStepIndex]) == INDEX_NONE)
	{
		return false;
	}

	if (ComboStepIndex != KhazanWeakAttackAbilityPrivate::Attack05Index)
	{
		return true;
	}

	UAbilitySystemComponent* AbilitySystemComponent = GetAbilitySystemComponentFromActorInfo();

	return IsValid(AbilitySystemComponent) &&
		AbilitySystemComponent->HasMatchingGameplayTag(KhazanGameplayTags::Unlock_Skill_DAS_WeakAttack05);
}

void UKhazanWeakAttackAbility::HandleMontageNotifyBegin(const FName NotifyName, const FBranchingPointNotifyPayload& BranchingPointPayload)
{
	if (!IsActive() || !IsNotifyFromWeakAttackMontage(BranchingPointPayload))
	{
		return;
	}

	if (NotifyName == KhazanWeakAttackAbilityPrivate::ComboInputOpenNotifyName)
	{
		BufferedInputTag = FGameplayTag();
		bAcceptingComboInput = true;
		bComboCommitReached = false;
		bCanCancelToLocomotion = false;
		
		return;
	}

	if (NotifyName == KhazanWeakAttackAbilityPrivate::ComboCommitNotifyName)
	{
		if (!bAcceptingComboInput)
		{
			return;
		}

		bComboCommitReached = true;

		if (BufferedInputTag.IsValid())
		{
			TryCommitBufferedTransition();
		}

		return;
	}
	
	if (NotifyName == KhazanWeakAttackAbilityPrivate::ComboInputEndNotifyName)
	{
		BufferedInputTag = FGameplayTag();
		bAcceptingComboInput = false;
		bComboCommitReached = false;
		bCanCancelToLocomotion = true;
	}
}

bool UKhazanWeakAttackAbility::IsNotifyFromWeakAttackMontage(const FBranchingPointNotifyPayload& BranchingPointPayload) const
{
	return BranchingPointPayload.SequenceAsset ==
			WeakAttackMontage.Get() &&
			GetCurrentMontage() == WeakAttackMontage.Get();
}

void UKhazanWeakAttackAbility::BindMontageNotifyDelegate(UAnimInstance* AnimInstance)
{
	UnbindMontageNotifyDelegate();

	if (!IsValid(AnimInstance))
	{
		return;
	}

	BoundAnimInstance = AnimInstance;

	AnimInstance->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotifyBegin);
}

void UKhazanWeakAttackAbility::UnbindMontageNotifyDelegate()
{
	if (UAnimInstance* AnimInstance = BoundAnimInstance.Get())
	{
		AnimInstance->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotifyBegin);
	}

	BoundAnimInstance.Reset();
}

void UKhazanWeakAttackAbility::ResetRuntimeState()
{
	CurrentComboStepIndex = INDEX_NONE;
	BufferedInputTag = FGameplayTag();
	bAcceptingComboInput = false;
	bComboCommitReached = false;
	bCanCancelToLocomotion = false;
}

void UKhazanWeakAttackAbility::HandleMontageCompleted()
{
	ActiveMontageTask = nullptr;
	FinishAbility(false);
}

void UKhazanWeakAttackAbility::HandleMontageAborted()
{
	ActiveMontageTask = nullptr;
	FinishAbility(true);
}

void UKhazanWeakAttackAbility::EndAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const bool bReplicateEndAbility,
	const bool bWasCancelled)
{
	UnbindMontageNotifyDelegate();
	ResetRuntimeState();

	Super::EndAbility(SpecHandle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);

	ActiveMontageTask = nullptr;
}

void UKhazanWeakAttackAbility::FinishAbility(const bool bWasCancelled)
{
	if (!IsActive())
	{
		return;
	}

	EndAbility(GetCurrentAbilitySpecHandle(),
		GetCurrentActorInfo(),
		GetCurrentActivationInfo(),
		/* bReplicateEndAbility */ true,
		bWasCancelled);
}

void UKhazanWeakAttackAbility::HandleMoveInputStarted(FGameplayEventData Payload)
{
	(void)Payload;

	if (!IsActive() || !bCanCancelToLocomotion)
	{
		return;
	}

	FinishAbility(true);}