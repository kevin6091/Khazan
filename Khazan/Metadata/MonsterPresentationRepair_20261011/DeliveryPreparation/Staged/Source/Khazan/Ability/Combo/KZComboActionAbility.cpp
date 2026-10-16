#include "Ability/Combo/KZComboActionAbility.h"
#include "Data/KZCharacterDefinitionData.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_WaitGameplayEvent.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Environment/KZSnowDeformation.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffect.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "KZGameplayTags.h"
#include "LogChannels.h"
#include "Character/KZCharacter.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Character/Locomotion/KZLocomotionType.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Attribute/KZAttributeSet.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "TimerManager.h"
#include "DrawDebugHelpers.h"

namespace KZComboAttackAbilityPrivate
{
	// Ability Task와 몽타주 노티파이가 함께 사용하는 이름이다.
	const FName MontageTaskName(TEXT("ComboAttackMontage"));

	const FName InputOpenNotifyName(TEXT("InputOpen"));
	const FName CommitNotifyName(TEXT("InputCommit"));
	const FName InputEndNotifyName(TEXT("InputEnd"));
	
	const FName HoldCommitNotifyName(TEXT("HoldCommit"));
	const FName HoldEndNotifyName(TEXT("HoldEnd"));
	
	const FName JumpNotifyName(TEXT("DoJump"));
	const FName DownNotifyName(TEXT("DoDown"));
}


UKZComboActionAbility::UKZComboActionAbility()
{
	// 이 Combo Action이 실행되는 동안 이동 입력과 Stamina 회복을 차단한다.
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_Movement_Input);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_StaminaRegen);
}

bool UKZComboActionAbility::IsApproachingComboTransition(const float LeadSeconds) const
{
	const UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo());
	const UAnimInstance* Anim = BoundAnimInstance.Get();
	const FKZComboNode* Node = ComboDefinition ? ComboDefinition->FindNode(CurrentNodeId) : nullptr;
	if (!IsActive() || !ASC || !Anim || !Node || LeadSeconds <= 0.f) return false;
	bool bHasContinuation = false;
	for (const FKZComboCommandEdge& Edge : Node->CommandEdges)
	{
		if (Edge.CommandPhase == EKZComboCommandPhase::InputEnd &&
			ASC->IsComboCommandHeld(Edge.CommandTag) &&
			MatchesEdge(Edge, FKZComboCommand(Edge.CommandTag, Edge.CommandPhase)))
		{
			bHasContinuation = true;
			break;
		}
	}
	const UAnimMontage* Montage = Node->Montage.Get();
	if (!bHasContinuation || !Montage || Anim->GetCurrentActiveMontage() != Montage ||
		Anim->Montage_GetCurrentSection(Montage) != Node->SectionName) return false;
	const float Position = Anim->Montage_GetPosition(Montage);
	const float PlayRate = Anim->Montage_GetEffectivePlayRate(Montage);
	if (PlayRate <= 0.f) return false;
	const int32 Section = Montage->GetSectionIndex(Node->SectionName);
	if (Section == INDEX_NONE) return false;
	const float SectionEnd = Montage->GetAnimCompositeSection(Section).GetTime() + Montage->GetSectionLength(Section);
	for (const FAnimNotifyEvent& Notify : Montage->Notifies)
	{
		const float At = Notify.GetTriggerTime();
		if (Notify.NotifyName == KZComboAttackAbilityPrivate::InputEndNotifyName &&
			At >= Position && At < SectionEnd && (At - Position) / PlayRate <= LeadSeconds) return true;
	}
	return false;
}

bool UKZComboActionAbility::IsInSystemGuardWindow() const
{
	const FKZComboNode* Node = ComboDefinition ? ComboDefinition->FindNode(CurrentNodeId) : nullptr;
	const UAnimInstance* Anim = BoundAnimInstance.Get();
	if (!IsActive() || !Node || !Node->Montage || !Anim || Anim->GetCurrentActiveMontage() != Node->Montage ||
		Anim->Montage_GetCurrentSection(Node->Montage) != Node->SectionName) return false;
	const int32 Section = Node->Montage->GetSectionIndex(Node->SectionName);
	if (Section == INDEX_NONE) return false;
	const float Time = Anim->Montage_GetPosition(Node->Montage) - Node->Montage->GetAnimCompositeSection(Section).GetTime();
	return Node->SystemGuardWindows.ContainsByPredicate([Time](const FVector2D& Window)
	{
		return Time >= Window.X && Time <= Window.Y;
	});
}

bool UKZComboActionAbility::CanActivateAbility(
    const FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo,
    const FGameplayTagContainer* SourceTags,
    const FGameplayTagContainer* TargetTags,
    FGameplayTagContainer* OptionalRelevantTags) const
{
    if (!Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags))
    {
        return false;
    }

    if (ActorInfo == nullptr || !IsValid(ComboDefinition))
    {
        return false;
    }

    const UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(ActorInfo->AbilitySystemComponent.Get());
    const UAnimInstance* AnimInstance = ActorInfo->GetAnimInstance();
    const FKZComboNode* EntryNode = ComboDefinition->FindNode(EntryNodeId);

    return IsValid(ASC) && IsValid(AnimInstance) &&
        EntryNode != nullptr && IsNodePlayable(*EntryNode);
}

void UKZComboActionAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	check(ActorInfo);

	// 이전 실행에서 남은 연결과 값을 먼저 지운다.
	UnbindComboCommandDelegate();
	UnbindMontageNotifyDelegate();
	UnbindConfirmedHitDelegate();
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

	// 이번 activation의 비용과 쿨다운을 확정한다. local node 비용은 TransitionToNode가 따로 적용한다.
	if (!CommitAbility(Handle, ActorInfo, ActivationInfo))
	{
		EndAbility(Handle, ActorInfo, ActivationInfo, false, true);

		return;
	}

	// activation 이후 발생하는 Combo Command를 받도록 연결한다. 이전 사건을 재생하지는 않는다.
	BindConfirmedHitDelegate(ASC);
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

bool UKZComboActionAbility::StartEntryMontage()
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
	if (IsActive() && ActiveMontageTask == Task)
	{
		StartAttackCollision();
	}

	// 시작 실패 callback에서 Ability가 끝났는지도 함께 확인한다.
	return IsActive() && ActiveMontageTask == Task;
}

void UKZComboActionAbility::HandleComboCommand(const FKZComboCommand& Command)
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
		// 중복 물리 Begin은 ASC가 거르고, 여기서는 닫힌 창과 이미 찬 예약을 거른다.
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
		// Release는 Closed 상태에서도 즉시 처리한다.
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

bool UKZComboActionAbility::RunCommand(const FKZComboCommand& Command)
{
	const FKZComboCommandEdge* Edge = FindMatchingCommandEdge(Command);

	if (Edge == nullptr)
	{
		return false;
	}

	return ApplyEdge(*Edge, Command);
}

bool UKZComboActionAbility::ApplyEdge(const FKZComboCommandEdge& Edge, const FKZComboCommand& Command)
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
	UpdateAttackCollision();
	if (!IsActive()) return false;

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

bool UKZComboActionAbility::IsHoldType(const EKZComboHold Hold) const
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

bool UKZComboActionAbility::IsMoveType(const EKZComboMove Move) const
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

bool UKZComboActionAbility::MatchesEdge(const FKZComboCommandEdge& Edge, const FKZComboCommand& Command) const
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

bool UKZComboActionAbility::RunHeld(const EKZComboCommandPhase Phase)
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
		// 현재 Ability를 끝낼 수 있으므로 첫 일치 Edge의 실행 결과를 바로 반환한다.
		return ApplyEdge(Edge, Command);
	}

	return false;
}

const FKZComboCommandEdge* UKZComboActionAbility::FindMatchingCommandEdge(const FKZComboCommand& Command) const
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

bool UKZComboActionAbility::CommitPendingCommand()
{
	// InputOpen 때 저장한 Begin 한 건을 InputCommit에서 다시 검사한다.
	if (!IsActive() || !PendingCommandTag.IsValid())
	{
		return false;
	}
	
	// PendingCommandTag를 지역 변수로 복사한 뒤 지워야 한다.
	// 지역 복사본은 ClearPendingCommand 이후에도 원래 태그를 유지한다.
	const FGameplayTag CommandTag = PendingCommandTag;
	ClearPendingCommand();
	
	return RunCommand(FKZComboCommand(CommandTag, EKZComboCommandPhase::Begin));
}

bool UKZComboActionAbility::TransitionToNode(const FName TargetNodeId)
{
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

    // 현재 local 전환은 같은 Montage의 section 사이에서만 지원한다.
    if (CurrentNode->Montage.Get() != TargetNode->Montage.Get())
    {
        UE_LOG(LogAbility, Error, TEXT("%s rejected cross-Montage Combo edge %s -> %s."),
            *GetNameSafe(GetAvatarActorFromActorInfo()),
            *CurrentNodeId.ToString(),
            *TargetNodeId.ToString());
        return false;
    }

    const FGameplayAbilityActorInfo* ActorInfo = GetCurrentActorInfo();
    UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
    UAnimInstance* AnimInstance = ActorInfo ? ActorInfo->GetAnimInstance() : nullptr;

    if (ActorInfo == nullptr || !IsValid(ASC) || !IsValid(AnimInstance) ||
        !ASC->IsAnimatingAbility(this) || GetCurrentMontage() != CurrentNode->Montage.Get())
    {
        return false;
    }

    const FGameplayAbilitySpecHandle Handle = GetCurrentAbilitySpecHandle();

    // 비용 부족이면 현재 node/window/InputEnd/몽타주를 바꾸지 않는다.
    if (!CheckCost(Handle, ActorInfo))
    {
        UE_LOG(LogAbility, Log, TEXT("%s : %s -> %s Faild. Not enough cost "),
            *GetNameSafe(GetAvatarActorFromActorInfo()),
            *CurrentNodeId.ToString(),
            *TargetNodeId.ToString());
        return false;
    }

    const FName PreviousNodeId = CurrentNodeId;
    UpdateAttackCollision();
    if (!IsActive() || CurrentNodeId != PreviousNodeId) return false;
    const FGameplayAbilityActivationInfo ActivationInfo = GetCurrentActivationInfo();

    // 사용자가 적용한 local node마다 비용을 지불하는 정책을 유지한다.
    ApplyCost(Handle, ActorInfo, ActivationInfo);

    // Effect 적용 callback이 실행을 끝냈다면 이후 전환을 진행하지 않는다.
    // 이미 적용한 비용을 되돌리는 rollback 계약은 아니다.
    if (!IsActive())
    {
        return false;
    }

    ClearPendingCommand();
    ComboWindowPhase = EKZComboWindowPhase::Closed;
    bHoldCommitted = false;
    ResetInputEnd();

    const float TransitionBlend=GetNodeTransitionBlendSeconds(*TargetNode);
    if (TransitionBlend > 0.0f)
    {
        AnimInstance->RequestMontageInertialization(
            CurrentNode->Montage.Get(),
            TransitionBlend,
            nullptr);
    }

    // Jump에서 첫 Notify가 발생할 수 있으므로 목적 node를 먼저 기록한다.
    ClearCombatEffects();
    CurrentNodeId = TargetNodeId;
    StartAttackCollision();
    MontageJumpToSection(TargetNode->SectionName);

    UE_LOG(LogAbility, Log, TEXT("%s transitioned Combo node %s -> %s."),
        *GetNameSafe(GetAvatarActorFromActorInfo()),
        *PreviousNodeId.ToString(),
        *CurrentNodeId.ToString());
    return true;
}

void UKZComboActionAbility::HandleMontageNotifyBegin(const FName NotifyName, const FBranchingPointNotifyPayload& Payload)
{
	// 다른 몽타주에서 온 같은 이름의 노티파이는 무시한다.
	if (!IsActive() || !IsNotifyFromCurrentMontage(Payload))
	{
		return;
	}

	const UKZAnimNotify_CombatEffect* Effect = Payload.NotifyEvent
		? Cast<UKZAnimNotify_CombatEffect>(Payload.NotifyEvent->Notify.Get()) : nullptr;
	if (Effect != nullptr)
	{
		// This stricter resource guard does not change the existing input-notify
		// contract. Reject another pawn or an old instance of the same montage.
		USkeletalMeshComponent* Mesh = Payload.SkelMeshComponent;
		const FGameplayAbilityActorInfo* ActorInfo = GetCurrentActorInfo();
		UAnimInstance* AnimInstance = BoundAnimInstance.Get();
		UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
		FAnimMontageInstance* MontageInstance = IsValid(AnimInstance)
			? AnimInstance->GetActiveInstanceForMontage(GetCurrentMontage()) : nullptr;
		const bool bCanProcessEffects = IsValid(Mesh) && ActorInfo != nullptr &&
			Mesh->GetOwner() == ActorInfo->AvatarActor.Get() &&
			AnimInstance == Mesh->GetAnimInstance() && ActorInfo->GetAnimInstance() == AnimInstance &&
			IsValid(ASC) && ASC->IsAnimatingAbility(this) && MontageInstance != nullptr &&
			MontageInstance->GetInstanceID() == Payload.MontageInstanceID;
		if (bCanProcessEffects)
		{
			// End before Start at the same boundary. Children are data only;
			// authoring never nests batches or emits overlapping engine markers.
			for (const bool bEnding : {true, false})
			{
				const auto ProcessEffect = [this, &Payload, bEnding](const UKZAnimNotify_CombatEffect* Entry)
				{
					if (!IsActive() || !IsValid(Entry) || Entry->EventId.IsNone() || Entry->bEndEvent != bEnding)
					{
						return;
					}
					const FGameplayAbilityActorInfo* CurrentInfo = GetCurrentActorInfo();
					UAnimInstance* CurrentAnim = BoundAnimInstance.Get();
					UAbilitySystemComponent* CurrentASC = GetAbilitySystemComponentFromActorInfo();
					FAnimMontageInstance* CurrentInstance = IsValid(CurrentAnim)
						? CurrentAnim->GetActiveInstanceForMontage(GetCurrentMontage()) : nullptr;
					if (!IsValid(Payload.SkelMeshComponent) || CurrentInfo == nullptr ||
						!IsValid(CurrentASC) || !CurrentASC->IsAnimatingAbility(this) ||
						CurrentInstance == nullptr || CurrentInstance->GetInstanceID() != Payload.MontageInstanceID ||
						Payload.SkelMeshComponent->GetOwner() != CurrentInfo->AvatarActor.Get() ||
						Payload.SkelMeshComponent->GetAnimInstance() != CurrentAnim || CurrentInfo->GetAnimInstance() != CurrentAnim)
					{
						return;
					}
					if (bEnding)
					{
						StopCombatEffect(Entry->EventId, Payload.MontageInstanceID);
					}
					else
					{
						StartCombatEffect(*Entry, Payload);
					}
				};
				ProcessEffect(Effect);
				for (const UKZAnimNotify_CombatEffect* Child : Effect->BatchedEffects)
				{
					ProcessEffect(Child);
				}
			}
		}
		// If this batch replaces an equal-time old input marker, its preserved
		// NotifyName still follows the existing input path after FX processing.
		if (IsActive() && IsNotifyFromCurrentMontage(Payload))
		{
			ProcessMontageNotify(NotifyName);
		}
		return;
	}

	ProcessMontageNotify(NotifyName);
}

void UKZComboActionAbility::StartCombatEffect(
	const UKZAnimNotify_CombatEffect& Effect, const FBranchingPointNotifyPayload& Payload,
	const bool bConfirmedHit, const float RecoveredWindowDuration)
{
	if (Effect.bOnAttackSuccessed &&
		(PlayedConfirmedEffects.Contains(Effect.EventId) ||
		(!bConfirmedHit && (!bConfirmedEffectHitObserved ||
			Payload.MontageInstanceID != AttackMontageInstanceId ||
			FirstConfirmedEffectHitTime > Effect.WindowEndTime))))
	{
		return; // A real earlier hit may enable a later window in this execution.
	}
	Super::StartCombatEffect(Effect, Payload, Effect.bOnAttackSuccessed || bConfirmedHit,
		RecoveredWindowDuration);
	// Failed projection/template creation must remain retryable. Only actual
	// spawned resources count as played in this attack execution.
	if (Effect.bOnAttackSuccessed && ActiveCombatEffects.ContainsByPredicate(
		[&Effect, &Payload](const FActiveCombatEffect& Record)
		{
			return Record.Component.IsValid() && Record.EventId == Effect.EventId &&
				Record.MontageInstanceId == Payload.MontageInstanceID;
		}))
	{
		PlayedConfirmedEffects.Add(Effect.EventId);
	}
}



void UKZComboActionAbility::BindConfirmedHitDelegate(UAbilitySystemComponent* ASC)
{
	UnbindConfirmedHitDelegate();
	if (IsValid(ASC))
	{
		ConfirmedHitASC = ASC;
		ConfirmedHitDelegateHandle = ASC->OnGameplayEffectAppliedDelegateToTarget.AddUObject(
			this, &ThisClass::HandleConfirmedHit);
	}
}

void UKZComboActionAbility::UnbindConfirmedHitDelegate()
{
	const FDelegateHandle PreviousHandle = ConfirmedHitDelegateHandle;
	UAbilitySystemComponent* ASC = ConfirmedHitASC.Get();
	ConfirmedHitDelegateHandle.Reset();
	ConfirmedHitASC.Reset();
	if (IsValid(ASC) && PreviousHandle.IsValid())
	{
		ASC->OnGameplayEffectAppliedDelegateToTarget.Remove(PreviousHandle);
	}
}

void UKZComboActionAbility::HandleConfirmedHit(UAbilitySystemComponent* TargetASC,
	const FGameplayEffectSpec& Spec, FActiveGameplayEffectHandle EffectHandle)
{
	check(IsInGameThread());
	(void)EffectHandle;
	// This field is the current project's actual collision producer contract,
	// not an original-game damage value. Costs, heals and other abilities fail it.
	if (!IsActive() || !IsValid(TargetASC) || !IsValid(TargetASC->GetAvatarActor()) ||
		Spec.GetContext().GetSourceObject() != this ||
		!(Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), false, 0.f) < 0.f))
	{
		return;
	}
	const FGameplayAbilityActorInfo* ActorInfo = GetCurrentActorInfo();
	UAnimInstance* AnimInstance = BoundAnimInstance.Get();
	UAbilitySystemComponent* ASC = ConfirmedHitASC.Get();
	const FKZComboNode* Node = ComboDefinition ? ComboDefinition->FindNode(CurrentNodeId) : nullptr;
	UAnimMontage* Montage = GetCurrentMontage();
	if (!IsValid(Montage) && bNaturalAttackCollisionFlush && Node) Montage = Node->Montage;
	FAnimMontageInstance* MontageInstance = IsValid(AnimInstance)
		? AnimInstance->GetActiveInstanceForMontage(Montage) : nullptr;
	const bool bFinalFlush = bNaturalAttackCollisionFlush && ActiveMontageTask != nullptr && Node &&
		AttackMontage.Get() == Montage && Node->Montage == Montage && AttackMontageInstanceId != INDEX_NONE &&
		IsValid(ASC) && (ASC->GetAnimatingAbility() == nullptr || ASC->GetAnimatingAbility() == this);
	if (ActorInfo == nullptr || !IsValid(AnimInstance) || !IsValid(ASC) || ASC != GetAbilitySystemComponentFromActorInfo() ||
		(!bFinalFlush && (!ASC->IsAnimatingAbility(this) || MontageInstance == nullptr)) ||
		(MontageInstance != nullptr && MontageInstance->GetInstanceID() != AttackMontageInstanceId) ||
		ActorInfo->GetAnimInstance() != AnimInstance)
	{
		return;
	}
	const int32 MontageInstanceId = MontageInstance ? MontageInstance->GetInstanceID() : AttackMontageInstanceId;
	const float SampleTime = Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackMontageTime")), false, -1.f);
	const float SampleInstance = Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackMontageInstance")), false, -1.f);
	const float SampleExecution = Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackExecution")), false, -1.f);
	if (!FMath::IsFinite(SampleTime) || SampleTime < 0.f ||
		SampleInstance != float(MontageInstanceId) || SampleExecution != float(AttackExecution))
	{
		return;
	}
	if (!IsValid(Montage)) return;
	const uint32 Execution = AttackExecution;
	const FName NodeId = CurrentNodeId;
	// Original BattleEffectIndex linkage is unavailable. This presentation-only
	// adapter remembers a real HP hit for this execution/node's later windows.
	if (!bConfirmedEffectHitObserved) FirstConfirmedEffectHitTime = SampleTime;
	else FirstConfirmedEffectHitTime = FMath::Min(FirstConfirmedEffectHitTime, SampleTime);
	bConfirmedEffectHitObserved = true;
	RecordAcceptedAttackHit(TargetASC->GetAvatarActor(), SampleTime);
	const float PresentationTime = bFinalFlush ? Montage->GetPlayLength() : AnimInstance->Montage_GetPosition(Montage);
	// Authored window data survives a Begin+End crossed by one slow frame. It is
	// read at the actual producer's sampled time; no expired live-window cache.
	TArray<TWeakObjectPtr<const UKZAnimNotify_CombatEffect>> Matches;
	TSet<FName> MatchedIds;
	const auto MatchEffect = [&Matches, &MatchedIds, SampleTime, PresentationTime, this](const UKZAnimNotify_CombatEffect* Entry)
	{
		if (IsValid(Entry) && !Entry->bEndEvent && Entry->bOnAttackSuccessed && !Entry->EventId.IsNone() &&
			FMath::IsFinite(Entry->WindowStartTime) && FMath::IsFinite(Entry->WindowEndTime) &&
			FirstConfirmedEffectHitTime <= Entry->WindowEndTime &&
			((SampleTime >= Entry->WindowStartTime && SampleTime <= Entry->WindowEndTime) ||
				(FirstConfirmedEffectHitTime <= Entry->WindowStartTime && PresentationTime >= Entry->WindowStartTime)) &&
			!MatchedIds.Contains(Entry->EventId) && !PlayedConfirmedEffects.Contains(Entry->EventId))
		{
			MatchedIds.Add(Entry->EventId);
			Matches.Add(Entry);
		}
	};
	for (const FAnimNotifyEvent& NotifyEvent : Montage->Notifies)
	{
		if (const UKZAnimNotify_CombatEffect* Parent = Cast<UKZAnimNotify_CombatEffect>(NotifyEvent.Notify.Get()))
		{
			MatchEffect(Parent);
			for (const UKZAnimNotify_CombatEffect* Child : Parent->BatchedEffects)
			{
				MatchEffect(Child);
			}
		}
	}
	for (const TWeakObjectPtr<const UKZAnimNotify_CombatEffect>& Matched : Matches)
	{
		const UKZAnimNotify_CombatEffect* Effect = Matched.Get();
		const FGameplayAbilityActorInfo* EffectActorInfo = GetCurrentActorInfo();
		UAnimInstance* CurrentAnimInstance = BoundAnimInstance.Get();
		USkeletalMeshComponent* Mesh = IsValid(CurrentAnimInstance) ? CurrentAnimInstance->GetSkelMeshComponent() : nullptr;
		FAnimMontageInstance* CurrentInstance = IsValid(CurrentAnimInstance)
			? CurrentAnimInstance->GetActiveInstanceForMontage(Montage) : nullptr;
		if (!IsActive() || !IsValid(Mesh) || !IsValid(Effect) ||
			EffectActorInfo == nullptr || AttackExecution != Execution || CurrentNodeId != NodeId ||
			CurrentAnimInstance != AnimInstance ||
			(CurrentInstance != nullptr && CurrentInstance->GetInstanceID() != MontageInstanceId) ||
			(CurrentInstance == nullptr && !bFinalFlush) ||
			Mesh->GetOwner() != EffectActorInfo->AvatarActor.Get() ||
			Mesh->GetAnimInstance() != CurrentAnimInstance || EffectActorInfo->GetAnimInstance() != CurrentAnimInstance ||
			ASC != GetAbilitySystemComponentFromActorInfo() ||
			(!bFinalFlush && !ASC->IsAnimatingAbility(this)) ||
			(bFinalFlush && (!bNaturalAttackCollisionFlush || AttackMontage.Get() != Montage ||
				(ASC->GetAnimatingAbility() != nullptr && ASC->GetAnimatingAbility() != this))))
		{
			continue;
		}
		const FBranchingPointNotifyPayload Payload(Mesh, Montage, nullptr, MontageInstanceId);
		// One presentation per EventId/execution prevents the retained earlier hit
		// and its later Begin marker from duplicating the same source occurrence.
		const bool bRecoveredAfterEnd = bFinalFlush || CurrentAnimInstance->Montage_GetPosition(Montage) >= Effect->WindowEndTime;
		const float Duration = bRecoveredAfterEnd ? Effect->WindowEndTime - Effect->WindowStartTime : 0.f;
		if (bRecoveredAfterEnd && Effect->bDestroyOnNotifyEnd && !IsValid(Effect->DecalMaterial) && Duration <= 0.f)
		{
			continue; // A degenerate expired loop has no source duration to bound emission.
		}
		StartCombatEffect(*Effect, Payload, true, Duration);
	}
}



void UKZComboActionAbility::ProcessMontageNotify(FName NotifyName)
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
		// 이 callback 뒤에 처리되는 Release가 AfterCommit을 보도록
		// Edge 검사보다 먼저 상태를 바꾼다.
		bHoldCommitted = true;
		RunHeld(EKZComboCommandPhase::HoldCommit);
		return;
	}

	if (NotifyName == KZComboAttackAbilityPrivate::HoldEndNotifyName)
	{
		RunHeld(EKZComboCommandPhase::HoldEnd);
	}
	
	if (NotifyName == KZComboAttackAbilityPrivate::JumpNotifyName)
	{
		if (AKZCharacter* Character = Cast<AKZCharacter>(GetOwningActorFromActorInfo()))
		{
			if (CurrentNodeId == "SpinningAttack01")
			{
				Character->LaunchCharacter(FVector(0.f, 0.f, 800.f), false, true);
			}
			else if (CurrentNodeId == "ChargeAttack03")
			{
				Character->LaunchCharacter(FVector(0.f, 0.f, 700.f), false, true);
			}
		}
	}
	
	if (NotifyName == KZComboAttackAbilityPrivate::DownNotifyName)
	{
		if (AKZCharacter* Character = Cast<AKZCharacter>(GetOwningActorFromActorInfo()))
		{
			if (CurrentNodeId == "SpinningAttack01")
			{
				Character->LaunchCharacter(FVector(0.f, 0.f, -1000.f), false, true);	
			}
			else if (CurrentNodeId == "ChargeAttack03")
			{
				Character->LaunchCharacter(FVector(0.f, 0.f, -1500.f), false, true);
			}
		}
	}
}


bool UKZComboActionAbility::IsNodePlayable(const FKZComboNode& Node) const
{
	// 노드 이름, 몽타주, 섹션이 모두 있어야 재생할 수 있다.
	return
		!Node.NodeId.IsNone() &&
		IsValid(Node.Montage) &&
		!Node.SectionName.IsNone() &&
		Node.Montage->GetSectionIndex(Node.SectionName) != INDEX_NONE;
}

bool UKZComboActionAbility::IsNotifyFromCurrentMontage(const FBranchingPointNotifyPayload& Payload) const
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

void UKZComboActionAbility::HandleMoveInput(FGameplayEventData Payload)
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

void UKZComboActionAbility::BindComboCommandDelegate()
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

void UKZComboActionAbility::UnbindComboCommandDelegate()
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

void UKZComboActionAbility::BindMontageNotifyDelegate(UAnimInstance* AnimInstance)
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

void UKZComboActionAbility::UnbindMontageNotifyDelegate()
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

void UKZComboActionAbility::ClearPendingCommand()
{
	// 예약 입력이 없다는 기본 상태로 되돌린다.
	PendingCommandTag = FGameplayTag();
}

void UKZComboActionAbility::ResetAttackCollision()
{
	if (UWorld* World = GetWorld()) World->GetTimerManager().ClearTimer(AttackCollisionTimer);
	AttackHitTargets.Reset();
	PreviousAttackTime = 0.f;
	AttackMontageInstanceId = INDEX_NONE;
	AttackMontage.Reset();
	bConfirmedEffectHitObserved = false;
	FirstConfirmedEffectHitTime = 0.f;
	PlayedConfirmedEffects.Reset();
	++AttackExecution;
}

void UKZComboActionAbility::StartAttackCollision()
{
	ResetAttackCollision();
	AActor* Avatar = GetAvatarActorFromActorInfo();
	const FKZComboNode* Node = ComboDefinition ? ComboDefinition->FindNode(CurrentNodeId) : nullptr;
	if (!IsActive() || !IsValid(Avatar) || !Node || Node->AttackWindows.IsEmpty()) return;
	UAnimInstance* Anim = BoundAnimInstance.Get();
	const FAnimMontageInstance* Instance = IsValid(Anim)
		? Anim->GetActiveInstanceForMontage(Node->Montage) : nullptr;
	if (Instance && GetCurrentMontage() == Node->Montage)
	{
		AttackMontageInstanceId = Instance->GetInstanceID();
		AttackMontage = Node->Montage;
	}
	PreviousAttackActorTransform = Avatar->GetActorTransform();
	AttackCollisionTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &ThisClass::UpdateAttackCollision, false));
}

void UKZComboActionAbility::UpdateAttackCollision(const bool bMontageCompleted)
{
	TGuardValue<bool> NaturalFlushGuard(bNaturalAttackCollisionFlush, bMontageCompleted);
	// A normal section handoff/completion can flush us before the scheduled callback.
	if (UWorld* World = GetWorld()) World->GetTimerManager().ClearTimer(AttackCollisionTimer);
	AActor* Avatar = GetAvatarActorFromActorInfo();
	UAnimInstance* Anim = BoundAnimInstance.Get();
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	const FKZComboNode* Node = ComboDefinition ? ComboDefinition->FindNode(CurrentNodeId) : nullptr;
	if (!IsActive() || !IsValid(Avatar) || !IsValid(Anim) || !ASC || !Node ||
		Node->AttackWindows.IsEmpty() || (!bMontageCompleted && (!ASC->IsAnimatingAbility(this) || GetCurrentMontage() != Node->Montage)) ||
		(bMontageCompleted && (AttackMontage.Get() != Node->Montage || AttackMontageInstanceId == INDEX_NONE ||
			(ASC->GetAnimatingAbility() != nullptr && ASC->GetAnimatingAbility() != this)))) return;
	float SectionStart = 0.f, SectionEnd = 0.f;
	Node->Montage->GetSectionStartAndEndTime(Node->Montage->GetSectionIndex(Node->SectionName), SectionStart, SectionEnd);
	// Authored automatic NextSection chains (Spinning/Charge) retain this node's execution.
	float Time = Anim->Montage_GetPosition(Node->Montage) - SectionStart;
	// UE removes the active montage instance before dispatching OnCompleted (position then reads zero).
	// Normal completion consumes the remaining authored hit clock; interruption never takes this path.
	if (bMontageCompleted)
	{
		Time = PreviousAttackTime;
		for (const FKZAttackCollisionWindow& Window : Node->AttackWindows) Time = FMath::Max(Time, Window.EndTime);
	}
	const float Now = FMath::Clamp(Time, 0.f, Node->Montage->GetPlayLength() - SectionStart);
	const FTransform ActorTransform = Avatar->GetActorTransform();
	const uint32 Execution = AttackExecution;
	// External backward seeks do not sweep across unrelated recovery/sections.
	if (Now < PreviousAttackTime) PreviousAttackTime = Now;
	for (int32 Index = 0; Index < Node->AttackWindows.Num(); ++Index)
	{
		const FKZAttackCollisionWindow& Window = Node->AttackWindows[Index];
		if (Window.Keys.IsEmpty() || Window.EndTime < Window.StartTime ||
			Now < Window.StartTime || PreviousAttackTime > Window.EndTime) continue;
		int32 HitId = Index;
		if (!Window.HitGroup.IsNone())
		{
			for (int32 Other = 0; Other < Index; ++Other)
				if (Node->AttackWindows[Other].HitGroup == Window.HitGroup) { HitId = Other; break; }
		}
		const float Begin = FMath::Max(PreviousAttackTime, Window.StartTime);
		const float End = FMath::Min(Now, Window.EndTime);
		auto PoseAt = [&](float Time)
		{
			const FKZAttackCollisionKey* A = &Window.Keys[0];
			const FKZAttackCollisionKey* B = A;
			for (const FKZAttackCollisionKey& Key : Window.Keys)
			{
				B = &Key;
				if (Key.Time >= Time) break;
				A = &Key;
			}
			const float KeyAlpha = B->Time > A->Time ? FMath::Clamp((Time - A->Time) / (B->Time - A->Time), 0.f, 1.f) : 0.f;
			const float ActorAlpha = Now > PreviousAttackTime ? FMath::Clamp((Time - PreviousAttackTime) / (Now - PreviousAttackTime), 0.f, 1.f) : 1.f;
			FTransform Frame;
			Frame.Blend(PreviousAttackActorTransform, ActorTransform, ActorAlpha);
			return FTransform(FQuat::Slerp(A->Rotation.Quaternion(), B->Rotation.Quaternion(), KeyAlpha),
				FMath::Lerp(A->Center, B->Center, KeyAlpha)) * Node->CollisionToActor * Frame;
		};
		FVector LastCenter = PoseAt(Begin).GetLocation();
		auto Sample = [&](float Time)
		{
			const FTransform Pose = PoseAt(Time);
			const bool bContinue = QueryAttackCollision(Window, HitId, Pose, LastCenter, Execution, SectionStart + Time);
			LastCenter = Pose.GetLocation();
			return bContinue;
		};
		if (!Sample(Begin)) return;
		// Consume EVERY crossed original baked key, including windows skipped by a slow frame.
		for (const FKZAttackCollisionKey& Key : Window.Keys)
			if (Key.Time > Begin && Key.Time < End && !Sample(Key.Time)) return;
		if (End > Begin && !Sample(End)) return;
	}
	if (!IsActive() || AttackExecution != Execution) return;
	PreviousAttackTime = Now;
	PreviousAttackActorTransform = ActorTransform;
	if (!bMontageCompleted)
		AttackCollisionTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &ThisClass::UpdateAttackCollision, false));
}

bool UKZComboActionAbility::QueryAttackCollision(const FKZAttackCollisionWindow& Window, const int32 HitId,
	const FTransform& Pose, const FVector& PreviousCenter, const uint32 Execution, const float SampleMontageTime)
{
	AActor* Avatar = GetAvatarActorFromActorInfo();
	UWorld* World = GetWorld();
	const FVector Extent = Window.Extent * Pose.GetScale3D().GetAbs();
	const float Radius = FMath::Max(Extent.X, Extent.Y);
	const bool bValidSize = Window.Shape == EKZAttackCollisionShape::Sphere ? Extent.X > 0.f :
		(Window.Shape == EKZAttackCollisionShape::Cylinder ? Radius > 0.f && Extent.Z > 0.f : Extent.GetMin() > 0.f);
	if (!World || !bValidSize || Extent.ContainsNaN() || Pose.ContainsNaN()) return true;
	const FVector Center = Pose.GetLocation();
	const FQuat Rotation = Pose.GetRotation();
	const FVector QueryExtent = Window.Shape == EKZAttackCollisionShape::Cylinder ? FVector(Radius, Radius, Extent.Z) : Extent;
	const FCollisionShape Shape = Window.Shape == EKZAttackCollisionShape::Sphere ?
		FCollisionShape::MakeSphere(Extent.X) : FCollisionShape::MakeBox(QueryExtent);
	if (ComboDefinition->ShouldDrawAttackCollision())
	{
		if (Window.Shape == EKZAttackCollisionShape::Cylinder)
			DrawDebugCylinder(World, Center - Rotation.GetAxisZ() * Extent.Z, Center + Rotation.GetAxisZ() * Extent.Z,
				Radius, 24, FColor::Green, false, 0.f);
		else if (Window.Shape == EKZAttackCollisionShape::Sphere)
			DrawDebugSphere(World, Center, Extent.X, 16, FColor::Green, false, 0.f);
		else DrawDebugBox(World, Center, Extent, Rotation, FColor::Green, false, 0.f);
	}
	if (!Avatar->HasAuthority()) return true;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(KZComboAttack), false, Avatar);
	FCollisionObjectQueryParams Objects(ECC_Pawn);
	TArray<FOverlapResult> Overlaps;
	World->OverlapMultiByObjectType(Overlaps, Center, Rotation, Objects, Shape, Params);
	TSet<TWeakObjectPtr<AActor>> Candidates;
	for (const FOverlapResult& Overlap : Overlaps) Candidates.Add(Overlap.GetActor());
	// Box/sphere translations sweep between dense baked samples. Cylinder uses its exact finite shape below.
	if (Window.Shape != EKZAttackCollisionShape::Cylinder && !PreviousCenter.Equals(Center))
	{
		TArray<FHitResult> Hits;
		World->SweepMultiByObjectType(Hits, PreviousCenter, Center, Rotation, Objects, Shape, Params);
		for (const FHitResult& Hit : Hits) Candidates.Add(Hit.GetActor());
	}
	for (const TWeakObjectPtr<AActor>& Candidate : Candidates)
	{
		AKZCharacter* Recipient = Cast<AKZCharacter>(Candidate.Get());
		// Two current factions: Player hits Monster, Monster hits Player. No friendly fire.
		if (!IsValid(Recipient) || Recipient == Avatar || AttackHitTargets.FindOrAdd(HitId).Contains(Recipient) ||
			!(Avatar->IsA<AKZPlayer>() && Recipient->IsA<AKZMonster>() ||
			  Avatar->IsA<AKZMonster>() && Recipient->IsA<AKZPlayer>())) continue;
		if (Window.Shape == EKZAttackCollisionShape::Cylinder)
		{
			// UE query has no cylinder. Bounding box broadphase + finite-cylinder/capsule narrowphase.
			const UCapsuleComponent* Capsule = Recipient->GetCapsuleComponent();
			float HalfHeight, CapsuleRadius;
			Capsule->GetScaledCapsuleSize(CapsuleRadius, HalfHeight);
			const FVector Segment = Capsule->GetUpVector() * FMath::Max(HalfHeight - CapsuleRadius, 0.f);
			const FVector A = Rotation.UnrotateVector(Capsule->GetComponentLocation() - Segment - Center);
			const FVector D = Rotation.UnrotateVector(Segment * 2.f);
			auto Derivative = [&](float T)
			{
				const FVector P = A + D * T;
				const float R = FVector2D(P.X, P.Y).Size();
				const float Radial = R > Radius ? (R - Radius) * (P.X * D.X + P.Y * D.Y) / R : 0.f;
				return Radial + (FMath::Abs(P.Z) > Extent.Z ? (P.Z - FMath::Sign(P.Z) * Extent.Z) * D.Z : 0.f);
			};
			float Low = 0.f, High = 1.f;
			// Engine epsilon is numerical query precision, not a gameplay range tuning value.
			while (High - Low > UE_KINDA_SMALL_NUMBER)
			{
				const float Mid = (Low + High) * .5f;
				if (Derivative(Mid) < 0.f) Low = Mid; else High = Mid;
			}
			const FVector P = A + D * ((Low + High) * .5f);
			const float Radial = FMath::Max(FVector2D(P.X, P.Y).Size() - Radius, 0.f);
			const float Vertical = FMath::Max(FMath::Abs(P.Z) - Extent.Z, 0.f);
			if (Radial * Radial + Vertical * Vertical > CapsuleRadius * CapsuleRadius + UE_KINDA_SMALL_NUMBER) continue;
		}
		UKZAbilitySystemComponent* TargetASC = Cast<UKZAbilitySystemComponent>(Recipient->GetAbilitySystemComponent());
		const UKZAttributeSet* Attributes = TargetASC ? TargetASC->GetSet<UKZAttributeSet>() : nullptr;
		if (!Attributes || Attributes->GetMaxHP() <= 0.f || Attributes->GetHP() <= 0.f ||
			!ComboDefinition->GetAttackDamageEffect() || !FMath::IsFinite(Window.HPDamage) ||
			!FMath::IsFinite(Window.StaminaDamage) || Window.HPDamage < 0.f || Window.StaminaDamage < 0.f) continue;
		// Consume before callbacks; attribute/Guard callbacks may reenter or end this execution.
		AttackHitTargets.FindOrAdd(HitId).Add(Recipient);
		AKZMonster* ShieldMonster = Cast<AKZMonster>(Recipient);
		const bool bGuarded = Window.bBlockable && (ShieldMonster ? ShieldMonster->TrySystemGuard(Window.StaminaDamage, Avatar) :
			(FVector::DotProduct(Recipient->GetActorForwardVector(), Avatar->GetActorLocation() - Recipient->GetActorLocation()) >= 0.f &&
			 TargetASC->TryGuardHit(Window.StaminaDamage, Avatar)));
		if (!IsActive() || Execution != AttackExecution || !IsValid(Recipient)) return false;
		if (bGuarded && Window.GuardSound)
			UGameplayStatics::SpawnSoundAtLocation(Recipient, Window.GuardSound, Recipient->GetActorLocation());
		if (!bGuarded)
		{
			UAbilitySystemComponent* SourceASC = GetAbilitySystemComponentFromActorInfo();
			if (!IsValid(SourceASC)) return false;
			FGameplayEffectContextHandle Context = SourceASC->MakeEffectContext();
			Context.AddSourceObject(this);
			const FGameplayEffectSpecHandle Spec = SourceASC->MakeOutgoingSpec(ComboDefinition->GetAttackDamageEffect(), GetAbilityLevel(), Context);
			if (Spec.IsValid())
			{
				Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), -Window.HPDamage);
				Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")), -Window.StaminaDamage);
				// Technical producer identity/time, not gameplay tuning or original metadata.
				// The consumer can match effects even when this frame crossed their End.
				UAnimInstance* Anim = BoundAnimInstance.Get();
				const FAnimMontageInstance* Instance = IsValid(Anim)
					? Anim->GetActiveInstanceForMontage(GetCurrentMontage()) : nullptr;
				Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackMontageTime")), SampleMontageTime);
				Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackMontageInstance")),
					Instance ? float(Instance->GetInstanceID()) :
						float(bNaturalAttackCollisionFlush ? AttackMontageInstanceId : INDEX_NONE));
				Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackExecution")), float(Execution));
				const FActiveGameplayEffectHandle Result = SourceASC->ApplyGameplayEffectSpecToTarget(*Spec.Data, TargetASC);
				UE_LOG(LogAbility, Log, TEXT("ComboHit %s node=%s window=%d group=%s target=%s HPDamage=%g StaminaDamage=%g applied=%d"),
					*GetNameSafe(Avatar), *CurrentNodeId.ToString(), HitId, *Window.HitGroup.ToString(), *GetNameSafe(Recipient),
					Window.HPDamage, Window.StaminaDamage, Result.WasSuccessfullyApplied());
				// ApplyGE may synchronously invalidate either actor. Exhaustion/death overrides ordinary presentation.
				if (Result.WasSuccessfullyApplied() && IsValid(Recipient))
				{
					if (Window.HPDamage > 0.f && Window.ImpactSound)
						UGameplayStatics::SpawnSoundAtLocation(Recipient, Window.ImpactSound, Recipient->GetActorLocation());
					const UKZCharacterDefinitionData* BodyDefinition = Recipient->GetCharacterDefinition();
					if (Window.HPDamage > 0.f && BodyDefinition && BodyDefinition->GetHitReactionSettings().ImpactSound)
						UGameplayStatics::SpawnSoundAtLocation(Recipient, BodyDefinition->GetHitReactionSettings().ImpactSound, Recipient->GetActorLocation());
					if (AKZMonster* Victim = Cast<AKZMonster>(Recipient)) Victim->PlayHitBlood(Avatar, Center);
					Recipient->PlayHitReaction(Window.HitReaction, Avatar);
				}
			}
		}
		if (!IsActive() || Execution != AttackExecution) return false;
	}
	return true;
}

void UKZComboActionAbility::ResetRuntimeState()
{
	ResetAttackCollision();
	ClearCombatEffects();
	// 다음 activation이 이전 콤보 상태를 이어받지 않게 모두 비운다.
	ClearPendingCommand();
	CurrentNodeId = NAME_None;
	ComboWindowPhase = EKZComboWindowPhase::Closed;
	bHoldCommitted = false;
}

void UKZComboActionAbility::HandleMontageCompleted()
{
	// Consume final crossed keys before natural completion closes the execution.
	const uint32 CompletedExecution = AttackExecution;
	UpdateAttackCollision(true);
	if (!IsActive() || AttackExecution != CompletedExecution) return;
	ClearCombatEffects(true);
	// 자연 종료이므로 취소되지 않은 완료로 끝낸다.
	ActiveMontageTask = nullptr;
	FinishAbility(false);
}

void UKZComboActionAbility::HandleMontageAborted()
{
	// 중단이나 취소는 취소된 실행으로 끝낸다.
	ActiveMontageTask = nullptr;
	FinishAbility(true);
}

void UKZComboActionAbility::FinishAbility(const bool bWasCancelled)
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

void UKZComboActionAbility::EndAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const bool bReplicateEndAbility,
	const bool bWasCancelled)
{
	// 종료 중 입력이나 노티파이가 다시 들어오지 않게 연결부터 끊는다.
	UnbindComboCommandDelegate();
	UnbindMontageNotifyDelegate();
	UnbindConfirmedHitDelegate();
	ResetRuntimeState();

	// 부모가 Task와 실행 중 태그를 정리한다.
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);

	ActiveMontageTask = nullptr;
}
