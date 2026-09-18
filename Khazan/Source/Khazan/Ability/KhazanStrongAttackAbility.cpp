#include "Ability/KhazanStrongAttackAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_WaitGameplayEvent.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "GameFramework/Character.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"

namespace KhazanStrongAttackAbilityPrivate
{
	const FName MontageTaskName(TEXT("StrongAttackComboMontage"));
	
	const FName ComboInputOpenNotifyName(TEXT("ComboInputOpen"));
	const FName ComboCommitNotifyName(TEXT("ComboCommit"));
	const FName ComboInputEndNotifyName(TEXT("ComboInputEnd"));
	
	const FName ComboSectionNames[]
	{
		TEXT("Attack01"),
		TEXT("Attack02"),
		TEXT("Attack03")
	};
	
	constexpr int32 ComboSectionCount = UE_ARRAY_COUNT(ComboSectionNames);
	constexpr int32 Attack01Index = 0;
	constexpr int32 Attack03Index = 2;
	
	bool IsValidComboStepIndex(const int32 ComboStepIndex)
	{
		return
			ComboStepIndex >= 0 &&
			ComboStepIndex < ComboSectionCount;
	}
}

UKhazanStrongAttackAbility::UKhazanStrongAttackAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
}

void UKhazanStrongAttackAbility::ActivateAbility(
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
		return IsValid(StrongAttackMontage) &&
		KhazanStrongAttackAbilityPrivate::IsValidComboStepIndex(ComboStepIndex) &&
		StrongAttackMontage->GetSectionIndex(KhazanStrongAttackAbilityPrivate::ComboSectionNames[ComboStepIndex]) != INDEX_NONE;	
	};
	
	if (!IsValid(Character) || !IsValid(AnimInstance) || 
		!HasComboSection(0) || 
		!HasComboSection(1) ||
		!HasComboSection(2))
	{
		UE_LOG(LogAbility, Error, TEXT( "%s could not start %s. " "Character=%s, AnimInstance=%s, " "Montage=%s,"
			" Attack01=%s, Attack02=%s, Attack03=%s."),
			*GetNameSafe(ActorInfo ? ActorInfo->AvatarActor.Get() : nullptr),
			*GetNameSafe(GetClass()),
			*GetNameSafe(Character),
			*GetNameSafe(AnimInstance),
			*GetNameSafe(StrongAttackMontage),
			HasComboSection(0) ? TEXT("valid") : TEXT("missing"),
			HasComboSection(1) ? TEXT("valid") : TEXT("missing"),
			HasComboSection(2) ? TEXT("valid") : TEXT("missing"));

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
	
	if (!StartStrongAttackMontage())
	{
		return;
	}

	// Test
	UE_LOG(LogAbility, Log, TEXT("%s started %s at section %s."),
	*GetNameSafe(Character),
	*GetNameSafe(GetClass()),
	*KhazanStrongAttackAbilityPrivate::ComboSectionNames[0].ToString());
}

void UKhazanStrongAttackAbility::InputPressed(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo)
{
	if (!IsActive())
	{
		return;
	}

	SubmitComboInput(KhazanGameplayTags::Input_Action_StrongAttack);
}



bool UKhazanStrongAttackAbility::StartStrongAttackMontage()
{
	if (!IsActive() || !IsValid(StrongAttackMontage) || !BoundAnimInstance.IsValid() || IsValid(ActiveMontageTask))
	{
		UE_LOG(LogAbility, Error, TEXT("%s could not start the StrongAttack montage."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return false;
	}
	
	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait:: CreatePlayMontageAndWaitProxy(
					this,
					KhazanStrongAttackAbilityPrivate::MontageTaskName,
					StrongAttackMontage,
					1.f,
					KhazanStrongAttackAbilityPrivate::ComboSectionNames[0],
					true,
					1.f,
					0.f,
					true);
	
	if (!IsValid(Task))
	{
		UE_LOG(LogAbility, Error, TEXT("%s failed to create the StrongAttack montage task."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return false;
	}
	
	ActiveMontageTask = Task;
	
	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	
	// Attack01을 현재 실행 중인 콤보 타수로 확정한다.
	CurrentComboStepIndex = KhazanStrongAttackAbilityPrivate::Attack01Index;
	
	Task->ReadyForActivation();
	
	return IsActive() && ActiveMontageTask == Task;
}

void UKhazanStrongAttackAbility::SubmitComboInput(const FGameplayTag& InputTag)
{
	if (!bAcceptingComboInput || BufferedInputTag.IsValid() || !InputTag.MatchesTagExact(KhazanGameplayTags::Input_Action_StrongAttack))
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

bool UKhazanStrongAttackAbility::TryCommitBufferedTransition()
{
	bAcceptingComboInput = false;
	bComboCommitReached = false;
	
	if (!IsActive() || !BufferedInputTag.IsValid())
	{
		return false;
	}

	const FGameplayTag InputToConsume = BufferedInputTag;

	BufferedInputTag = FGameplayTag();

	if (!InputToConsume.MatchesTagExact(KhazanGameplayTags::Input_Action_StrongAttack))
	{
		return false;
	}

	if (!KhazanStrongAttackAbilityPrivate::IsValidComboStepIndex(CurrentComboStepIndex))
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
		GetCurrentMontage() != StrongAttackMontage.Get())
	{
		return false;
	}

	const int32 PreviousComboStepIndex = CurrentComboStepIndex;

	CurrentComboStepIndex = NextComboStepIndex;
	bCanCancelToLocomotion = false;
	
	if (ComboSectionInertializationDuration > 0.f)
	{
		AnimInstance->RequestMontageInertialization(StrongAttackMontage, ComboSectionInertializationDuration, nullptr);
	}

	MontageJumpToSection(KhazanStrongAttackAbilityPrivate::ComboSectionNames[CurrentComboStepIndex]);

	UE_LOG(LogAbility, Log, TEXT("%s transitioned StrongAttack %s -> %s."),
		*GetNameSafe(GetAvatarActorFromActorInfo()),
		*KhazanStrongAttackAbilityPrivate::ComboSectionNames[PreviousComboStepIndex].ToString(),
		*KhazanStrongAttackAbilityPrivate::ComboSectionNames[CurrentComboStepIndex].ToString());

	return true;
}

bool UKhazanStrongAttackAbility::CanEnterComboStep(const int32 ComboStepIndex) const
{
	if (!KhazanStrongAttackAbilityPrivate::IsValidComboStepIndex(ComboStepIndex) ||
		!IsValid(StrongAttackMontage) ||
		StrongAttackMontage->GetSectionIndex(KhazanStrongAttackAbilityPrivate::ComboSectionNames[ComboStepIndex]) == INDEX_NONE)
	{
		return false;
	}

	if (ComboStepIndex != KhazanStrongAttackAbilityPrivate::Attack03Index)
	{
		return true;
	}

	UAbilitySystemComponent* AbilitySystemComponent = GetAbilitySystemComponentFromActorInfo();

	return IsValid(AbilitySystemComponent);
}

void UKhazanStrongAttackAbility::HandleMontageNotifyBegin(const FName NotifyName, const FBranchingPointNotifyPayload& BranchingPointPayload)
{
	if (!IsActive() || !IsNotifyFromStrongAttackMontage(BranchingPointPayload))
	{
		return;
	}

	if (NotifyName == KhazanStrongAttackAbilityPrivate::ComboInputOpenNotifyName)
	{
		BufferedInputTag = FGameplayTag();
		bAcceptingComboInput = true;
		bComboCommitReached = false;
		bCanCancelToLocomotion = false;
		
		return;
	}

	if (NotifyName == KhazanStrongAttackAbilityPrivate::ComboCommitNotifyName)
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
	
	if (NotifyName == KhazanStrongAttackAbilityPrivate::ComboInputEndNotifyName)
	{
		BufferedInputTag = FGameplayTag();
		bAcceptingComboInput = false;
		bComboCommitReached = false;
		bCanCancelToLocomotion = true;
	}
}

bool UKhazanStrongAttackAbility::IsNotifyFromStrongAttackMontage(const FBranchingPointNotifyPayload& BranchingPointPayload) const
{
	return BranchingPointPayload.SequenceAsset ==
			StrongAttackMontage.Get() &&
			GetCurrentMontage() == StrongAttackMontage.Get();
}

void UKhazanStrongAttackAbility::BindMontageNotifyDelegate(UAnimInstance* AnimInstance)
{
	UnbindMontageNotifyDelegate();

	if (!IsValid(AnimInstance))
	{
		return;
	}

	BoundAnimInstance = AnimInstance;

	AnimInstance->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotifyBegin);
}

void UKhazanStrongAttackAbility::UnbindMontageNotifyDelegate()
{
	if (UAnimInstance* AnimInstance = BoundAnimInstance.Get())
	{
		AnimInstance->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotifyBegin);
	}

	BoundAnimInstance.Reset();
}

void UKhazanStrongAttackAbility::ResetRuntimeState()
{
	CurrentComboStepIndex = INDEX_NONE;
	BufferedInputTag = FGameplayTag();
	bAcceptingComboInput = false;
	bComboCommitReached = false;
	bCanCancelToLocomotion = false;
}

void UKhazanStrongAttackAbility::HandleMontageCompleted()
{
	ActiveMontageTask = nullptr;
	FinishAbility(false);
}

void UKhazanStrongAttackAbility::HandleMontageAborted()
{
	ActiveMontageTask = nullptr;
	FinishAbility(true);
}

void UKhazanStrongAttackAbility::EndAbility(
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

void UKhazanStrongAttackAbility::FinishAbility(const bool bWasCancelled)
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

void UKhazanStrongAttackAbility::HandleMoveInputStarted(FGameplayEventData Payload)
{
	(void)Payload;

	if (!IsActive() || !bCanCancelToLocomotion)
	{
		return;
	}

	FinishAbility(true);}