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
#include "Character/KZCharacter.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Character/Locomotion/KZLocomotionType.h"

namespace KZComboAttackAbilityPrivate
{
	// Ability Task와 몽타주 노티파이가 함께 사용하는 이름이다.
	const FName MontageTaskName(TEXT("ComboAttackMontage"));

	const FName InputOpenNotifyName(TEXT("InputOpen"));
	const FName CommitNotifyName(TEXT("InputCommit"));
	const FName InputEndNotifyName(TEXT("InputEnd"));
	
	const FName HoldCommitNotifyName(TEXT("HoldCommit"));
	const FName HoldEndNotifyName(TEXT("HoldEnd"));
}

UKZComboAttackAbility::UKZComboAttackAbility()
{
	// GAS가 이 Ability를 공격 행동으로 구분할 때 쓰는 태그다.
	FGameplayTagContainer AssetTags;
	AssetTags.AddTag(KZGameplayTags::Ability_Action_Attack);
	SetAssetTags(AssetTags);
	
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
	// ASC가 held 상태를 갱신한 뒤 보낸 외부 입력 사건을 현재 node에서 처리한다.
	// 이 Ability는 버튼 상태를 따로 저장하지 않는다.
	if (!IsActive() || !Command.CommandTag.IsValid())
	{
		return;
	}

	switch (Command.Phase)
	{
	case EKZComboCommandPhase::Begin:
		// 이미 누른 버튼의 중복 Begin은 무시한다.
		// Begin만 일반 Combo Buffer를 사용한다.
		if (ComboWindowPhase == EKZComboWindowPhase::Closed ||
			PendingCommandTag.IsValid() ||
			FindMatchingCommandEdge(Command) == nullptr)
		{
			return;
		}
		
		PendingCommandTag = Command.CommandTag;
		
		if (ComboWindowPhase == EKZComboWindowPhase::CommitToEnd)
		{
			CommitPendingCommand();
		}
		
		return;

	case EKZComboCommandPhase::Release:
		// Release는 Colsed 상태에서도 즉시 처리한다.
		RunCommand(Command);
		return;

	case EKZComboCommandPhase::Cancel:
		// 취소된 버튼 자체가 pending Begin이라면 무조건 버린다.
		// FindMatchingCommandEdge()는 trigger 버튼 자체가 held인지 검사하지 않으므로
		// 이 검사가 없으면 취소된 Begin이 InputCommit에서 실행될 수 있다.
		if (PendingCommandTag == Command.CommandTag)
		{
			ClearPendingCommand();
			return;
		}
		
		// 다른 버튼의 Cancel도 pending Edge의 추가 hold 조건을 깨뜨릴 수 있다.
		// 예: pending=X이고 RequiredHeldCommands={Y}일 때 Y Cancel이면 정리한다.
		if (PendingCommandTag.IsValid())
		{
			const FKZComboCommand PendingCommand(PendingCommandTag, EKZComboCommandPhase::Begin);

			if (FindMatchingCommandEdge(PendingCommand) == nullptr)
			{
				ClearPendingCommand();
			}
		}

		return;

	default:
		return;
	}
}

bool UKZComboAttackAbility::RunCommand(const FKZComboCommand& Command)
{
	const FKZComboCommandEdge* Edge = FindMatchingCommandEdge(Command);

	if (Edge == nullptr)
	{
		return false;
	}

	return ApplyEdge(*Edge, Command);
}

bool UKZComboAttackAbility::ApplyEdge(const FKZComboCommandEdge& Edge, const FKZComboCommand& Command)
{
	// TargetNodeId가 다른 granted Ability의 Entry인지 먼저 확인한다.
	// Entry가 아니면 현재 Ability 안의 일반 노드 전환으로 처리한다.
	UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo());
	
	if (!IsValid(ASC))
	{
		return false;
	}
	
	const FGameplayAbilitySpecHandle SourceHandle = GetCurrentAbilitySpecHandle();
	
	if (!ASC->HasComboEntry(ComboDefinition, Edge.TargetNodeId, SourceHandle))
	{
		// 다른 entry Ability가 없으면 현재 Ability 내부 Node다.
		return TransitionToNode(Edge.TargetNodeId);
	}
	
	const bool bWasBlocking = IsBlockingOtherAbilities();

	// StrongCharge early Release는 InputEnd 전이므로
	// source block을 잠시 풀어야 StrongAttack을 시작할 수 있다.
	if (bWasBlocking)
	{
		SetShouldBlockOtherAbilities(false);
	}
	
	const bool bInputPressed = ASC->IsComboCommandHeld(Command.CommandTag);
	
	const bool bActivated = ASC->TryActivateComboEntry(
		ComboDefinition,
		Edge.TargetNodeId,
		SourceHandle,
		bInputPressed);
	
	if (!bActivated)
	{
		if (IsActive() && bWasBlocking)
		{
			SetShouldBlockOtherAbilities(true);
		}
		
		return false;
	}
	
	// Target의 CancelAbilitiesWithTag가 source를 취소하는 것이 정상이다.
	// 잘못된 Blueprint 설정으로 source가 남았다면 여기서 정리한다.
	if (IsActive())
	{
		FinishAbility(false);
	}

	return true;
}

bool UKZComboAttackAbility::IsHoldType(const EKZComboHold Hold) const
{
	// 시간은 재지 않는다. HoldCommit Notify를 지났는지만 비교한다.
	switch (Hold)
	{
	case EKZComboHold::Any:
		return true;

	case EKZComboHold::BeforeCommit:
		return !bHoldCommitted;

	case EKZComboHold::AfterCommit:
		return bHoldCommitted;

	default:
		return false;
	}
}

bool UKZComboAttackAbility::IsMoveType(const EKZComboMove Move) const
{
	// 과거 입력을 저장하지 않고 LocomotionComponent의 현재 입력을 즉시 읽는다.
	if (Move == EKZComboMove::Any)
	{
		return true;
	}

	const AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo());
	if (!IsValid(Character))
	{
		return false;
	}

	const UKZLocomotionComponent* Locomotion = Character->GetLocomotionComponent();
	if (!IsValid(Locomotion))
	{
		return false;
	}

	const FKZLocomotionIntent& Intent =	Locomotion->GetLocomotionIntent();

	if (Intent.InputAmount <= 0.0f)
	{
		return Move == EKZComboMove::NonRun;
	}

	switch (Intent.RequestedGait)
	{
	case EKZGait::Walk:
		return Move == EKZComboMove::NonRun;

	case EKZGait::Run:
		return Move == EKZComboMove::Run;

	case EKZGait::Sprint:
		return Move == EKZComboMove::Run;

	default:
		return false;
	}
}

bool UKZComboAttackAbility::MatchesEdge(const FKZComboCommandEdge& Edge, const FKZComboCommand& Command) const
{
	if (Edge.CommandTag != Command.CommandTag || Edge.CommandPhase != Command.Phase ||
	   !IsHoldType(Edge.Hold) ||
	   !IsMoveType(Edge.Move))
	{
		return false;
	}

	const UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo());

	if (!IsValid(ASC) || 
		!ASC->GetHeldComboCommands().HasAllExact(Edge.RequiredHeldCommands) || 
		!Edge.OwnerTagRequirements.RequirementsMet(ASC->GetOwnedGameplayTags()))
	{
		return false;
	}

	const FKZComboNode* TargetNode = ComboDefinition->FindNode(Edge.TargetNodeId);

	return TargetNode != nullptr && IsNodePlayable(*TargetNode);
}

bool UKZComboAttackAbility::RunHeld(const EKZComboCommandPhase Phase)
{
	if (!IsActive() || !IsValid(ComboDefinition))
	{
		return false;
	}

	// 이 함수는 CommandTag가 없는 Montage 사건만 처리한다.
	if (Phase != EKZComboCommandPhase::InputEnd &&
		Phase != EKZComboCommandPhase::HoldCommit &&
		Phase != EKZComboCommandPhase::HoldEnd)
	{
		return false;
	}

	const UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo());

	const FKZComboNode* CurrentNode = ComboDefinition->FindNode(CurrentNodeId);

	if (!IsValid(ASC) || CurrentNode == nullptr)
	{
		return false;
	}

	const FGameplayTagContainer& HeldCommands = ASC->GetHeldComboCommands();

	// held tag 순서가 아니라 authored Edge 순서로 검사한다.
	for (const FKZComboCommandEdge& Edge :  CurrentNode->CommandEdges)
	{
		if (Edge.CommandPhase != Phase || !HeldCommands.HasTagExact(Edge.CommandTag))
		{
			continue;
		}

		const FKZComboCommand Command(Edge.CommandTag, Phase);

		if (!MatchesEdge(Edge, Command))
		{
			continue;
		}

		// ApplyEdge가 다른 node/Ability로 전환하면서
		// 현재 Ability를 끝낼 수 있으므로 성공 즉시 반환한다.
		return ApplyEdge(Edge, Command);
	}

	return false;
}

const FKZComboCommandEdge* UKZComboAttackAbility::FindMatchingCommandEdge(const FKZComboCommand& Command) const
{
	// 현재 노드의 Edge를 위에서부터 검사하고 모든 조건이 맞는 첫 Edge를 돌려준다.
	if (!IsActive() || !IsValid(ComboDefinition) || !Command.CommandTag.IsValid())
	{
		return nullptr;
	}

	const FKZComboNode* CurrentNode = ComboDefinition->FindNode(CurrentNodeId);
	if (CurrentNode == nullptr)
	{
		return nullptr;
	}
	
	for (const FKZComboCommandEdge& Edge : CurrentNode->CommandEdges)
	{
		if (MatchesEdge(Edge, Command))
		{
			return &Edge;
		}
	}

	return nullptr;
}

bool UKZComboAttackAbility::CommitPendingCommand()
{
	// InputOpen 때 저장한 Begin 한 건을 InputCommit에서 다시 검사한다.
	if (!IsActive() || !PendingCommandTag.IsValid())
	{
		return false;
	}
	
	// PendingCommandTag를 지역 변수로 복사한 뒤 지워야 한다.
	// 지금 순서는 먼저 지우므로 아래 Command에는 빈 태그가 들어간다.
	const FGameplayTag CommandTag = PendingCommandTag;
	ClearPendingCommand();
	
	return RunCommand(FKZComboCommand(CommandTag, EKZComboCommandPhase::Begin));
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
	bHoldCommitted = false;
	ResetInputEnd();
	

	if (ComboTransitionInertializationDuration > 0.0f)
	{
		AnimInstance->RequestMontageInertialization(
			CurrentNode->Montage.Get(),
			ComboTransitionInertializationDuration,
			nullptr);
	}

	// 새 섹션 첫 노티파이가 올바른 노드를 보도록 이름부터 바꾼다.
	CurrentNodeId = TargetNodeId;

	// GE_Cost 지불
	const FGameplayAbilitySpecHandle Handle = GetCurrentAbilitySpecHandle();
	const FGameplayAbilityActorInfo* ActorInfo = GetCurrentActorInfo();
	const FGameplayAbilityActivationInfo ActivationInfo = GetCurrentActivationInfo();
	if (CheckCost(Handle, ActorInfo))
	{
		ApplyCost(Handle, ActorInfo, ActivationInfo);
	}
	else
	{
		UE_LOG(LogAttribute, Log, TEXT("No Cost"));
	}
	
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

	ProcessMontageNotify(NotifyName);
}

void UKZComboAttackAbility::ProcessMontageNotify(FName NotifyName)
{
	// Input 계열은 일반 콤보 입력 창, Hold 계열은 차지 성공 구간을 다룬다.
	// 두 시간축은 서로 독립적이다.
	if (NotifyName == KZComboAttackAbilityPrivate::InputOpenNotifyName)
	{
		// 새 입력 창을 열 때 이전 노드의 예약 입력을 지운다.
		ClearPendingCommand();
		ComboWindowPhase = EKZComboWindowPhase::OpenToCommit;
		
		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::CommitNotifyName)
	{
		// Open을 지나지 않은 잘못된 Commit은 무시한다.
		if (ComboWindowPhase != EKZComboWindowPhase::OpenToCommit)
		{
			return;
		}

		// 섹션 이동 중 새 노티파이가 와도 상태가 꼬이지 않게 먼저 바꾼다.
		ComboWindowPhase = EKZComboWindowPhase::CommitToEnd;

		// 미리 눌러 둔 입력이 있으면 이 지점에서 실행한다.
		CommitPendingCommand();
		
		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::InputEndNotifyName)
	{
		// 이 공격의 콤보 입력 구간이 끝났으므로 예약 입력을 버린다.
		ClearPendingCommand();

		ComboWindowPhase = EKZComboWindowPhase::Closed;
		
		// 먼저 target Ability를 시작할 수 있게 차단을 푼다.
		SetInputEnded();
		// 그 뒤 계속 held인 입력의 handoff Edge를 검사한다.
		RunHeld(EKZComboCommandPhase::InputEnd);
		
		return;
	}
	
	if (NotifyName == KZComboAttackAbilityPrivate::HoldCommitNotifyName)
	{
		// Release가 같은 frame에 와도 이후에는 성공으로 판정하도록
		// Edge 검사보다 먼저 상태를 바꾼다.
		bHoldCommitted = true;
		RunHeld(EKZComboCommandPhase::HoldCommit);
		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::HoldEndNotifyName)
	{
		RunHeld(EKZComboCommandPhase::HoldEnd);
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

	if (!IsActive() || !HasInputEnded())
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
}

void UKZComboAttackAbility::ResetRuntimeState()
{
	// 다음 activation이 이전 콤보 상태를 이어받지 않게 모두 비운다.
	ClearPendingCommand();
	CurrentNodeId = NAME_None;
	ComboWindowPhase = EKZComboWindowPhase::Closed;
	bHoldCommitted = false;
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
