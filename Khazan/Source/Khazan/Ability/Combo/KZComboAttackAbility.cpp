#include "Ability/Combo/KZComboAttackAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_WaitGameplayEvent.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "KZGameplayTags.h"
#include "LogChannels.h"

namespace KZComboAttackAbilityPrivate
{
	// Ability Task와 몽타주 노티파이가 함께 사용하는 이름이다.
	const FName MontageTaskName(TEXT("ComboAttackMontage"));

	const FName ComboInputOpenNotifyName(TEXT("ComboInputOpen"));
	const FName ComboCommitNotifyName(TEXT("ComboCommit"));
	const FName ComboInputEndNotifyName(TEXT("ComboInputEnd"));
}

UKZComboAttackAbility::UKZComboAttackAbility()
{
	// 실행 상태를 멤버로 보관하기 위해 캐릭터마다 인스턴스 하나를 사용한다.
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;

	// 이 프로젝트는 싱글 플레이이므로 현재 로컬에서만 실행한다.
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalOnly;

	// GAS가 이 Ability를 공격 행동으로 구분할 때 쓰는 태그다.
	FGameplayTagContainer AssetTags;
	AssetTags.AddTag(KZGameplayTags::Ability_Action_Attack);
	SetAssetTags(AssetTags);

	// ComboInputEnd 전에는 다른 일반 행동이 시작되지 않게 막는다.
	BlockAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);

	// InputEnd 이후 새 행동이 시작되면 이 공격을 끝낼 수 있다.
	CancelAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);

	// 공격 중에는 이동을 막고, Ability가 끝나면 GAS가 자동으로 태그를 뺀다.
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_Movement_Input);
}

void UKZComboAttackAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	check(ActorInfo);

	// 이전 실행에서 남은 연결과 값을 먼저 지운다.
	UnbindComboCommandDelegate();
	UnbindMontageNotifyDelegate();
	ResetRuntimeState();

	UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(ActorInfo->AbilitySystemComponent.Get());

	UAnimInstance* AnimInstance = ActorInfo->GetAnimInstance();

	const FKZComboNode* EntryNode = IsValid(ComboDefinition) ? ComboDefinition->FindNode(EntryNodeId) : nullptr;

	// 데이터가 잘못됐으면 비용을 쓰기 전에 취소한다.
	if (!IsValid(ASC) || !IsValid(AnimInstance) || EntryNode == nullptr || !IsNodePlayable(*EntryNode))
	{
		UE_LOG(LogAbility, Error, TEXT("%s could not activate %s. "  "ASC=%s, AnimInstance=%s, Definition=%s, EntryNode=%s."),
			*GetNameSafe(ActorInfo->AvatarActor.Get()),
			*GetNameSafe(GetClass()),
			*GetNameSafe(ASC),
			*GetNameSafe(AnimInstance),
			*GetNameSafe(ComboDefinition),
			*EntryNodeId.ToString());

		EndAbility(Handle, ActorInfo, ActivationInfo, false, true);

		return;
	}

	// 비용과 쿨다운은 콤보 전체가 시작될 때 한 번만 확정한다.
	if (!CommitAbility(Handle, ActorInfo, ActivationInfo))
	{
		EndAbility(Handle, ActorInfo, ActivationInfo, false, true);

		return;
	}

	// 첫 공격 명령을 놓치지 않도록 시작 중에 바로 연결한다.
	BindComboCommandDelegate();

	if (!ComboCommandDelegateHandle.IsValid())
	{
		UE_LOG(LogAbility, Error, TEXT("%s failed to bind ComboCommand delegate."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return;
	}

	// 이동 이벤트는 방향값이 아니라 "지금 이동 입력 중"이라는 신호로만 쓴다.
	UAbilityTask_WaitGameplayEvent* MoveInputTask = UAbilityTask_WaitGameplayEvent::WaitGameplayEvent(
		this,
		KZGameplayTags::Input_Action_Move,
		nullptr,
		false,
		true);

	if (!IsValid(MoveInputTask))
	{
		UE_LOG(LogAbility, Error, TEXT("%s failed to create the Move input task."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return;
	}

	MoveInputTask->EventReceived.AddDynamic(this, &ThisClass::HandleMoveInput);

	MoveInputTask->ReadyForActivation();

	// 첫 프레임 노티파이도 받도록 몽타주보다 먼저 연결한다.
	BindMontageNotifyDelegate(AnimInstance);

	if (!StartEntryMontage())
	{
		return;
	}
}

bool UKZComboAttackAbility::StartEntryMontage()
{
	// 시작 노드의 몽타주를 한 번만 재생한다.
	if (!IsActive() || !IsValid(ComboDefinition) || !BoundAnimInstance.IsValid() || IsValid(ActiveMontageTask))
	{
		UE_LOG(LogAbility, Error, TEXT("%s cannot start the entry Combo montage."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return false;
	}

	const FKZComboNode* EntryNode = ComboDefinition->FindNode(EntryNodeId);

	if (EntryNode == nullptr || !IsNodePlayable(*EntryNode))
	{
		FinishAbility(true);
		return false;
	}

	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
			this,
			KZComboAttackAbilityPrivate::MontageTaskName,
			EntryNode->Montage,
			1.0f,
			EntryNode->SectionName,
			true,
			1.0f,
			0.0f,
			true);

	if (!IsValid(Task))
	{
		UE_LOG(LogAbility, Error, TEXT("%s failed to create PlayMontageAndWait."),
			*GetNameSafe(GetAvatarActorFromActorInfo()));

		FinishAbility(true);
		return false;
	}

	ActiveMontageTask = Task;

	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);

	// 첫 프레임 노티파이가 올바른 노드를 보도록 이름부터 저장한다.
	CurrentNodeId = EntryNode->NodeId;

	Task->ReadyForActivation();

	// 시작 실패 callback에서 Ability가 끝났는지도 함께 확인한다.
	return IsActive() && ActiveMontageTask == Task;
}

void UKZComboAttackAbility::HandleComboCommand(const FKZComboCommand& Command)
{
	// 누르기, 떼기, 취소에 맞춰 현재 버튼 상태를 갱신한다.
	if (!IsActive() || !Command.CommandTag.IsValid())
	{
		return;
	}

	switch (Command.Phase)
	{
	case EKZComboCommandPhase::Begin:
		// 이미 누른 버튼의 중복 Begin은 무시한다.
		if (HeldCommands.HasTagExact(Command.CommandTag))
		{
			return;
		}

		HeldCommands.AddTag(Command.CommandTag);
		break;

	case EKZComboCommandPhase::Release:
		// 먼저 누른 기록이 없는 Release는 무시한다.
		if (!HeldCommands.HasTagExact(Command.CommandTag))
		{
			return;
		}

		HeldCommands.RemoveTag(Command.CommandTag);
		break;

	case EKZComboCommandPhase::Cancel:
		// Cancel은 공격을 실행하지 않고 입력 상태만 정리한다.
		HeldCommands.RemoveTag(Command.CommandTag);

		if (PendingCommandTag.IsValid())
		{
			const FKZComboCommand PendingCommand(PendingCommandTag, PendingCommandPhase);

			if (FindMatchingCommandEdge(PendingCommand) == nullptr)
			{
				ClearPendingCommand();
			}
		}

		return;

	default:
		return;
	}

	// 창이 닫혀 있어도 눌림 상태는 기억하지만 다음 공격으로 쓰지는 않는다.
	if (ComboWindowPhase == EKZComboWindowPhase::Closed)
	{
		return;
	}

	// 연타 입력은 쌓지 않고 현재 노드에 한 건만 저장한다.
	if (PendingCommandTag.IsValid())
	{
		return;
	}

	if (FindMatchingCommandEdge(Command) == nullptr)
	{
		return;
	}

	PendingCommandTag = Command.CommandTag;
	PendingCommandPhase = Command.Phase;

	// Commit 뒤에 받은 입력은 기다리지 않고 바로 실행한다.
	if (ComboWindowPhase == EKZComboWindowPhase::CommitToEnd)
	{
		CommitPendingCommand();
	}
}

const FKZComboCommandEdge* UKZComboAttackAbility::FindMatchingCommandEdge(const FKZComboCommand& Command) const
{
	// 현재 노드에서 입력, 홀드, 해금 조건이 모두 맞는 전환을 찾는다.
	if (!IsActive() || !IsValid(ComboDefinition) || !Command.CommandTag.IsValid())
	{
		return nullptr;
	}

	const FKZComboNode* CurrentNode = ComboDefinition->FindNode(CurrentNodeId);

	const UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();

	if (CurrentNode == nullptr || !IsValid(ASC))
	{
		return nullptr;
	}

	const FGameplayTagContainer& OwnerTags = ASC->GetOwnedGameplayTags();

	// 같은 입력이 여러 개면 배열에서 먼저 나온 규칙을 사용한다.
	for (const FKZComboCommandEdge& Edge : CurrentNode->CommandEdges)
	{
		if (Edge.CommandTag != Command.CommandTag || Edge.CommandPhase != Command.Phase)
		{
			continue;
		}

		// 함께 눌러야 하는 버튼이 빠졌으면 이 규칙을 건너뛴다.
		if (!HeldCommands.HasAllExact(Edge.RequiredHeldCommands))
		{
			continue;
		}

		// 해금이나 상태 태그 조건이 맞지 않으면 건너뛴다.
		if (!Edge.OwnerTagRequirements.RequirementsMet(OwnerTags))
		{
			continue;
		}

		const FKZComboNode* TargetNode = ComboDefinition->FindNode(Edge.TargetNodeId);

		if (TargetNode == nullptr || !IsNodePlayable(*TargetNode))
		{
			continue;
		}

		return &Edge;
	}

	return nullptr;
}

bool UKZComboAttackAbility::CommitPendingCommand()
{
	// 저장한 입력이 지금도 유효하면 다음 공격으로 보낸다.
	if (!IsActive() || !PendingCommandTag.IsValid())
	{
		return false;
	}

	const FKZComboCommand PendingCommand(PendingCommandTag, PendingCommandPhase);

	// 기다리는 동안 해금이나 홀드 상태가 바뀔 수 있어 다시 검사한다.
	const FKZComboCommandEdge* Edge = FindMatchingCommandEdge(PendingCommand);

	const FName TargetNodeId = Edge != nullptr ? Edge->TargetNodeId : NAME_None;

	ClearPendingCommand();

	if (Edge == nullptr)
	{
		return false;
	}

	// 맞는 규칙을 찾았으면 목표 노드로 이동한다.
	return TransitionToNode(TargetNodeId);
}

bool UKZComboAttackAbility::TransitionToNode(const FName TargetNodeId)
{
	// 현재 몽타주 안에서 다음 공격 섹션으로 이동한다.
	if (!IsActive() || !IsValid(ComboDefinition) || TargetNodeId.IsNone())
	{
		return false;
	}

	const FKZComboNode* CurrentNode = ComboDefinition->FindNode(CurrentNodeId);
	const FKZComboNode* TargetNode = ComboDefinition->FindNode(TargetNodeId);

	if (CurrentNode == nullptr || TargetNode == nullptr || !IsNodePlayable(*TargetNode))
	{
		return false;
	}

	// 다른 몽타주로 넘어가는 전환은 아직 지원하지 않는다.
	if (CurrentNode->Montage.Get() != TargetNode->Montage.Get())
	{
		UE_LOG(LogAbility, Error, TEXT("%s rejected cross-Montage Combo edge %s -> %s."),
			*GetNameSafe(GetAvatarActorFromActorInfo()),
			*CurrentNodeId.ToString(),
			*TargetNodeId.ToString());

		return false;
	}

	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();

	UAnimInstance* AnimInstance = GetCurrentActorInfo() ? GetCurrentActorInfo()->GetAnimInstance() : nullptr;

	if (!IsValid(ASC) || !IsValid(AnimInstance) || !ASC->IsAnimatingAbility(this) || GetCurrentMontage() != CurrentNode->Montage.Get())
	{
		return false;
	}

	const FName PreviousNodeId = CurrentNodeId;

	ClearPendingCommand();
	ComboWindowPhase = EKZComboWindowPhase::Closed;
	bCanExitToLocomotion = false;

	// 새 공격의 InputEnd 전까지 다른 행동을 다시 막는다.
	SetShouldBlockOtherAbilities(true);

	if (ComboTransitionInertializationDuration > 0.0f)
	{
		AnimInstance->RequestMontageInertialization(
			CurrentNode->Montage.Get(),
			ComboTransitionInertializationDuration,
			nullptr);
	}

	// 새 섹션 첫 노티파이가 올바른 노드를 보도록 이름부터 바꾼다.
	CurrentNodeId = TargetNodeId;

	MontageJumpToSection(TargetNode->SectionName);

	UE_LOG(LogAbility, Log, TEXT("%s transitioned Combo node %s -> %s."),
		*GetNameSafe(GetAvatarActorFromActorInfo()),
		*PreviousNodeId.ToString(),
		*CurrentNodeId.ToString());

	return true;
}

void UKZComboAttackAbility::HandleMontageNotifyBegin(const FName NotifyName, const FBranchingPointNotifyPayload& Payload)
{
	// 다른 몽타주에서 온 같은 이름의 노티파이는 무시한다.
	if (!IsActive() || !IsNotifyFromCurrentMontage(Payload))
	{
		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::ComboInputOpenNotifyName)
	{
		// 새 입력 창을 열 때 이전 노드의 예약 입력을 지운다.
		ClearPendingCommand();

		ComboWindowPhase = EKZComboWindowPhase::OpenToCommit;

		bCanExitToLocomotion = false;

		SetShouldBlockOtherAbilities(true);
		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::ComboCommitNotifyName)
	{
		// Open을 지나지 않은 잘못된 Commit은 무시한다.
		if (ComboWindowPhase != EKZComboWindowPhase::OpenToCommit)
		{
			return;
		}

		// 섹션 이동 중 새 노티파이가 와도 상태가 꼬이지 않게 먼저 바꾼다.
		ComboWindowPhase = EKZComboWindowPhase::CommitToEnd;

		// 미리 눌러 둔 입력이 있으면 이 지점에서 실행한다.
		if (PendingCommandTag.IsValid())
		{
			CommitPendingCommand();
		}

		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::ComboInputEndNotifyName)
	{
		// 이 공격의 콤보 입력 구간이 끝났으므로 예약 입력을 버린다.
		ClearPendingCommand();

		ComboWindowPhase = EKZComboWindowPhase::Closed;

		bCanExitToLocomotion = true;

		// 이제 이동이나 다른 행동으로 나갈 수 있다.
		// 새 입력이 없으면 몽타주는 회수 동작까지 재생한다.
		SetShouldBlockOtherAbilities(false);
	}
}

bool UKZComboAttackAbility::IsNodePlayable(const FKZComboNode& Node) const
{
	// 노드 이름, 몽타주, 섹션이 모두 있어야 재생할 수 있다.
	return
		!Node.NodeId.IsNone() &&
		IsValid(Node.Montage) &&
		!Node.SectionName.IsNone() &&
		Node.Montage->GetSectionIndex(Node.SectionName) != INDEX_NONE;
}

bool UKZComboAttackAbility::IsNotifyFromCurrentMontage(const FBranchingPointNotifyPayload& Payload) const
{
	// 현재 노드의 몽타주와 실제 재생 중인 몽타주를 함께 확인한다.
	if (!IsValid(ComboDefinition))
	{
		return false;
	}

	const FKZComboNode* CurrentNode = ComboDefinition->FindNode(CurrentNodeId);

	return
		CurrentNode != nullptr &&
		Payload.SequenceAsset == CurrentNode->Montage.Get() &&
		GetCurrentMontage() == CurrentNode->Montage.Get();
}

void UKZComboAttackAbility::HandleMoveInput(FGameplayEventData Payload)
{
	// 이 이벤트는 값이 아니라 이동 입력이 있다는 사실만 사용한다.
	(void)Payload;

	if (!IsActive() || !bCanExitToLocomotion)
	{
		return;
	}

	UAnimInstance* AnimInstance = GetCurrentActorInfo() ? GetCurrentActorInfo()->GetAnimInstance() : nullptr;

	UAnimMontage* CurMontage = GetCurrentMontage();

	if (IsValid(AnimInstance) && IsValid(CurMontage))
	{
		// 현재 자세를 조금 남겨 로코모션 전환이 튀지 않게 한다.
		if (LocomotionExitInertializationDuration > 0.0f)
		{
			AnimInstance->RequestMontageInertialization( CurMontage, LocomotionExitInertializationDuration, nullptr);
		}

		// 자세는 관성화가 이어 주므로 몽타주는 바로 멈춘다.
		AnimInstance->Montage_Stop( 0.0f, CurMontage);
	}

	FinishAbility(true);
}

void UKZComboAttackAbility::BindComboCommandDelegate()
{
	// 중복 연결을 막고 현재 ASC에 한 번만 연결한다.
	UnbindComboCommandDelegate();

	UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo());

	if (!IsValid(ASC))
	{
		return;
	}

	ComboCommandDelegateHandle = ASC->OnComboCommand().AddUObject(this, &ThisClass::HandleComboCommand);
}

void UKZComboAttackAbility::UnbindComboCommandDelegate()
{
	// 저장한 Handle이 있을 때만 같은 이벤트에서 제거한다.
	if (!ComboCommandDelegateHandle.IsValid())
	{
		return;
	}

	if (UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo()))
	{
		ASC->OnComboCommand().Remove(ComboCommandDelegateHandle);
	}

	ComboCommandDelegateHandle.Reset();
}

void UKZComboAttackAbility::BindMontageNotifyDelegate(UAnimInstance* AnimInstance)
{
	// 이전 AnimInstance 연결을 끊고 현재 인스턴스에 연결한다.
	UnbindMontageNotifyDelegate();

	if (!IsValid(AnimInstance))
	{
		return;
	}

	BoundAnimInstance = AnimInstance;

	AnimInstance->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotifyBegin);
}

void UKZComboAttackAbility::UnbindMontageNotifyDelegate()
{
	// 연결했던 AnimInstance가 아직 살아 있으면 callback을 제거한다.
	if (UAnimInstance* AnimInstance = BoundAnimInstance.Get())
	{
		AnimInstance->OnPlayMontageNotifyBegin.RemoveDynamic(
			this,
			&ThisClass::HandleMontageNotifyBegin);
	}

	BoundAnimInstance.Reset();
}

void UKZComboAttackAbility::ClearPendingCommand()
{
	// 예약 입력이 없다는 기본 상태로 되돌린다.
	PendingCommandTag = FGameplayTag();
	PendingCommandPhase = EKZComboCommandPhase::Begin;
}

void UKZComboAttackAbility::ResetRuntimeState()
{
	// 다음 activation이 이전 콤보 상태를 이어받지 않게 모두 비운다.
	HeldCommands.Reset();
	ClearPendingCommand();

	CurrentNodeId = NAME_None;
	ComboWindowPhase = EKZComboWindowPhase::Closed;
	bCanExitToLocomotion = false;
}

void UKZComboAttackAbility::HandleMontageCompleted()
{
	// 자연 종료이므로 취소되지 않은 완료로 끝낸다.
	ActiveMontageTask = nullptr;
	FinishAbility(false);
}

void UKZComboAttackAbility::HandleMontageAborted()
{
	// 중단이나 취소는 취소된 실행으로 끝낸다.
	ActiveMontageTask = nullptr;
	FinishAbility(true);
}

void UKZComboAttackAbility::FinishAbility(const bool bWasCancelled)
{
	// 이미 끝난 Ability에 EndAbility를 다시 호출하지 않는다.
	if (!IsActive())
	{
		return;
	}

	EndAbility(
		GetCurrentAbilitySpecHandle(),
		GetCurrentActorInfo(),
		GetCurrentActivationInfo(),
		false,
		bWasCancelled);
}

void UKZComboAttackAbility::EndAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const bool bReplicateEndAbility,
	const bool bWasCancelled)
{
	// 종료 중 입력이나 노티파이가 다시 들어오지 않게 연결부터 끊는다.
	UnbindComboCommandDelegate();
	UnbindMontageNotifyDelegate();
	ResetRuntimeState();

	// 부모가 Task와 실행 중 태그를 정리한다.
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);

	ActiveMontageTask = nullptr;
}
