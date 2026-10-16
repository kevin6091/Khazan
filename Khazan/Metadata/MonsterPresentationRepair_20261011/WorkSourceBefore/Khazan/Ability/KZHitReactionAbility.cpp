#include "Ability/KZHitReactionAbility.h"

#include "Abilities/GameplayAbilityTriggerType.h"
#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_ApplyRootMotionJumpForce.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZCharacter.h"
#include "Character/KZMonster.h"
#include "Data/KZCharacterDefinitionData.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/RootMotionSource.h"
#include "KZGameplayTags.h"

UKZHitReactionAbility::UKZHitReactionAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalOnly;
	bRetriggerInstancedAbility = true;
	FGameplayTagContainer Tags;
	Tags.AddTag(KZGameplayTags::Ability_Reaction_Hit);
	SetAssetTags(Tags);
	ActivationOwnedTags.AddTag(KZGameplayTags::State_HitReacting);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_Movement_Input);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_StaminaRegen);
	BlockAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);
	CancelAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);
	ActivationBlockedTags.AddTag(KZGameplayTags::State_Dead);
	ActivationBlockedTags.AddTag(KZGameplayTags::State_Exhausted);
	const FGameplayTag Events[] = {KZGameplayTags::Event_Combat_Hit_Short,
		KZGameplayTags::Event_Combat_Hit_Knockback, KZGameplayTags::Event_Combat_Hit_Launch,
		KZGameplayTags::Event_Combat_ShieldBlock};
	for (const FGameplayTag Event : Events)
	{
		FAbilityTriggerData Trigger;
		Trigger.TriggerTag = Event;
		Trigger.TriggerSource = EGameplayAbilityTriggerSource::GameplayEvent;
		AbilityTriggers.Add(Trigger);
	}
}

bool UKZHitReactionAbility::IsShieldReaction() const
{
	return IsActive() && !bEnding && CurrentEvent == KZGameplayTags::Event_Combat_ShieldBlock;
}

UAnimMontage* UKZHitReactionAbility::SelectMontage(const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayTag Event, const bool bRandom) const
{
	const AKZCharacter* Character = ActorInfo ? Cast<AKZCharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
	const UKZCharacterDefinitionData* Definition = Character ? Character->GetCharacterDefinition() : nullptr;
	if (!Definition) return nullptr;
	const FKZHitReactionSettings& Settings = Definition->GetHitReactionSettings();
	const TArray<TObjectPtr<UAnimMontage>>* Pool = nullptr;
	if (Event == KZGameplayTags::Event_Combat_Hit_Short) Pool = &Settings.ShortHits;
	else if (Event == KZGameplayTags::Event_Combat_Hit_Knockback) Pool = &Settings.Knockbacks;
	else if (Event == KZGameplayTags::Event_Combat_Hit_Launch) Pool = &Settings.Launches;
	else if (Event == KZGameplayTags::Event_Combat_ShieldBlock) Pool = &Settings.ShieldBlocks;
	if (!Pool) return nullptr;
	int32 Count = 0;
	for (const TObjectPtr<UAnimMontage>& Montage : *Pool) if (IsValid(Montage.Get())) ++Count;
	if (Count == 0 && Pool != &Settings.ShortHits)
	{
		Pool = &Settings.ShortHits;
		for (const TObjectPtr<UAnimMontage>& Montage : *Pool) if (IsValid(Montage.Get())) ++Count;
	}
	if (Count == 0) return nullptr;
	int32 Index = bRandom ? FMath::RandHelper(Count) : 0;
	for (const TObjectPtr<UAnimMontage>& Montage : *Pool)
		if (IsValid(Montage.Get()) && Index-- == 0) return Montage.Get();
	return nullptr;
}

bool UKZHitReactionAbility::ShouldAbilityRespondToEvent(const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayEventData* Payload) const
{
	return Payload && !bEnding && Super::ShouldAbilityRespondToEvent(ActorInfo, Payload) &&
		SelectMontage(ActorInfo, Payload->EventTag, false);
}

bool UKZHitReactionAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags,
	const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const
{
	if (bEnding || !Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags) || !ActorInfo)
		return false;
	const AKZCharacter* Character = Cast<AKZCharacter>(ActorInfo->AvatarActor.Get());
	const UAbilitySystemComponent* ASC = ActorInfo->AbilitySystemComponent.Get();
	const UKZAttributeSet* Attributes = ASC ? ASC->GetSet<UKZAttributeSet>() : nullptr;
	if (!Character || !Character->GetCharacterDefinition() || !Character->GetLocomotionComponent() ||
		!Character->GetCharacterMovement() || !ActorInfo->GetAnimInstance() || !Attributes ||
		!FMath::IsFinite(Attributes->GetHP()) || Attributes->GetHP() <= 0.f ||
		ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) ||
		ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted)) return false;
	if (Cast<AKZMonster>(Character) &&
		(!FMath::IsFinite(Attributes->GetStamina()) || Attributes->GetStamina() <= 0.f)) return false;
	return SelectMontage(ActorInfo, KZGameplayTags::Event_Combat_Hit_Short, false) ||
		SelectMontage(ActorInfo, KZGameplayTags::Event_Combat_Hit_Knockback, false) ||
		SelectMontage(ActorInfo, KZGameplayTags::Event_Combat_Hit_Launch, false) ||
		SelectMontage(ActorInfo, KZGameplayTags::Event_Combat_ShieldBlock, false);
}

void UKZHitReactionAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo, FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	const uint32 Serial = ++ExecutionSerial;
	Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData);
	if (!IsActive() || ExecutionSerial != Serial) return;
	AKZCharacter* Character = ActorInfo ? Cast<AKZCharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
	CurrentEvent = TriggerEventData ? TriggerEventData->EventTag : FGameplayTag();
	PlayingMontage = SelectMontage(ActorInfo, CurrentEvent, true);
	BoundCharacter = Character;
	BoundAnimInstance = ActorInfo ? ActorInfo->GetAnimInstance() : nullptr;
	BoundMovement = Character ? Character->GetCharacterMovement() : nullptr;
	MontageInstanceId = INDEX_NONE;
	if (!Character || !PlayingMontage || !BoundAnimInstance.IsValid() || !BoundMovement.IsValid() ||
		!Character->GetLocomotionComponent())
	{
		FinishAbility(true);
		return;
	}
	const bool bCommitted = CommitAbility(Handle, ActorInfo, ActivationInfo);
	if (!IsActive() || ExecutionSerial != Serial) return;
	if (!bCommitted) { FinishAbility(true); return; }
	FKZMovementConstraint Constraint;
	Constraint.bOverrideRotationMode = true;
	Constraint.RotationModeOverride = EKZRotationMode::VelocityDirection;
	Constraint.DebugName = TEXT("HitReaction");
	FKZMovementConstraintHandle AcquiredHandle = Character->GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
	if (!IsActive() || ExecutionSerial != Serial)
	{
		Character->GetLocomotionComponent()->ReleaseMovementConstraint(AcquiredHandle);
		return;
	}
	MovementHandle = AcquiredHandle;
	if (!MovementHandle.IsValid()) { FinishAbility(true); return; }
	BoundMovement->StopMovementImmediately();
	if (!IsActive() || ExecutionSerial != Serial) return;
	const bool bLaunch = CurrentEvent == KZGameplayTags::Event_Combat_Hit_Launch;
	const bool bForcedChain = (bLaunch || CurrentEvent == KZGameplayTags::Event_Combat_Hit_Knockback) &&
		(PlayingMontage->GetSectionIndex(TEXT("Up")) != INDEX_NONE || PlayingMontage->GetSectionIndex(TEXT("Air")) != INDEX_NONE ||
		 PlayingMontage->GetSectionIndex(TEXT("Down")) != INDEX_NONE);
	// A body's unsupported Launch selects a Short/Hit montage, without acquiring a physics task/mode.
	const bool bCanOwnFlying = BoundMovement->MovementMode == MOVE_Walking || BoundMovement->MovementMode == MOVE_NavWalking ||
		BoundMovement->MovementMode == MOVE_Falling;
	if (bForcedChain && bLaunch && PlayingMontage->GetSectionIndex(TEXT("Up")) != INDEX_NONE && bCanOwnFlying)
	{
		PreviousMovementMode = BoundMovement->MovementMode;
		PreviousCustomMovementMode = BoundMovement->CustomMovementMode;
		bOwnsFlyingMode = true;
		BoundMovement->SetMovementMode(MOVE_Flying);
		if (!IsActive() || ExecutionSerial != Serial) return;
	}
	UAnimInstance* Anim = BoundAnimInstance.Get();
	Anim->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotify);
	Anim->RequestMontageInertialization(PlayingMontage, PlayingMontage->BlendIn.GetBlendTime(), nullptr);
	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
		this, TEXT("HitReaction"), PlayingMontage, 1.f, NAME_None, true, 1.f, 0.f, true);
	if (!Task) { FinishAbility(true); return; }
	MontageTask = Task;
	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->ReadyForActivation();
	if (!IsActive() || ExecutionSerial != Serial || MontageTask != Task) return;
	const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(PlayingMontage);
	if (!Instance) { FinishAbility(true); return; }
	MontageInstanceId = Instance->GetInstanceID();
	if (bForcedChain)
	{
		const FKZHitReactionSettings& Settings = Character->GetCharacterDefinition()->GetHitReactionSettings();
		const float Distance = bLaunch ? Settings.LaunchDistance : Settings.KnockbackDistance;
		const float Height = bLaunch ? Settings.LaunchHeight : 0.f;
		const float Start = Instance->GetPosition(), Rate = Instance->GetPlayRate() * PlayingMontage->RateScale;
		float End = 0.f;
		for (const FAnimNotifyEvent& Notify : PlayingMontage->Notifies)
			if (Notify.NotifyName == TEXT("HitLand") && Notify.GetTime() > Start && (End <= Start || Notify.GetTime() < End)) End = Notify.GetTime();
		if (End <= Start)
		{
			const int32 Getup = PlayingMontage->GetSectionIndex(TEXT("Getup"));
			if (Getup != INDEX_NONE) End = PlayingMontage->GetAnimCompositeSection(Getup).GetTime();
		}
		if (!FMath::IsFinite(Distance) || Distance < 0.f || !FMath::IsFinite(Height) || Height < 0.f ||
			!FMath::IsFinite(Start) || !FMath::IsFinite(End) || !FMath::IsFinite(Rate) || Rate <= 0.f || End <= Start) { FinishAbility(true); return; }
		// These authored Air poses are in-place. Settings are explicitly temporary world-cm tuning;
		// only the current montage's time to HitLand/Getup supplies the duration, never DownLoop hold time.
		const float Duration = (End - Start) / Rate;
		if (!FMath::IsFinite(Duration) || Duration <= 0.f) { FinishAbility(true); return; }
		FVector Direction = -Character->GetActorForwardVector();
		if (TriggerEventData && IsValid(TriggerEventData->Instigator.Get()))
		{
			const FVector Away = (Character->GetActorLocation() - TriggerEventData->Instigator->GetActorLocation()).GetSafeNormal2D();
			if (!Away.IsNearlyZero()) Direction = Away;
		}
		Direction.Z = 0.f;
		// Physical push direction is independent of the random pose variant. No mesh .01 scaling.
		PreviousRootMotionMode = Anim->RootMotionMode;
		if (PreviousRootMotionMode != ERootMotionMode::IgnoreRootMotion)
		{
			bOwnsRootMotionMode = true;
			Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
			if (!IsActive() || ExecutionSerial != Serial) return;
		}
		UAbilityTask_ApplyRootMotionJumpForce* Force = UAbilityTask_ApplyRootMotionJumpForce::ApplyRootMotionJumpForce(
			this, TEXT("HitReactionMotion"), Direction.Rotation(), Distance, Height, Duration, 0.f, false,
			ERootMotionFinishVelocityMode::SetVelocity, FVector::ZeroVector, 0.f, nullptr, nullptr);
		// The engine factory applies its RootMotionSource synchronously, before ReadyForActivation.
		if (!IsActive() || ExecutionSerial != Serial) { if (Force) Force->EndTask(); return; }
		if (!Force) { FinishAbility(true); return; }
		MotionTask = Force;
		Force->OnFinish.AddDynamic(this, &ThisClass::HandleMotionFinished);
		Force->ReadyForActivation();
		if (!IsActive() || ExecutionSerial != Serial || MotionTask != Force) return;
	}
	if (AKZMonster* Monster = Cast<AKZMonster>(Character)) Monster->RequestCombatStateRefresh();
}

void UKZHitReactionAbility::ClearMotionTask()
{
	UAbilityTask_ApplyRootMotionJumpForce* Task = MotionTask;
	MotionTask = nullptr;
	if (Task)
	{
		Task->OnFinish.RemoveDynamic(this, &ThisClass::HandleMotionFinished);
		Task->EndTask(); // Engine OnDestroy removes only this task's source ID and Landed delegate.
	}
}

void UKZHitReactionAbility::RestoreRootMotionMode()
{
	if (!bOwnsRootMotionMode) return;
	bOwnsRootMotionMode = false;
	if (UAnimInstance* Anim = BoundAnimInstance.Get(); Anim && Anim->RootMotionMode == ERootMotionMode::IgnoreRootMotion)
		Anim->SetRootMotionMode(PreviousRootMotionMode);
}

void UKZHitReactionAbility::HandleMotionFinished()
{
	if (!IsActive() || bEnding || !MotionTask) return;
	const uint32 Serial = ExecutionSerial;
	ClearMotionTask();
	if (!IsActive() || ExecutionSerial != Serial) return;
	RestoreRootMotionMode();
	if (!IsActive() || ExecutionSerial != Serial) return;
	RestoreMovementMode();
	// The complete recovery montage task still owns Ability completion.
}

void UKZHitReactionAbility::RestoreMovementMode()
{
	if (!bOwnsFlyingMode) return;
	bOwnsFlyingMode = false; // Clear ownership before the synchronous movement-mode callback.
	UCharacterMovementComponent* Movement = BoundMovement.Get();
	AKZCharacter* Character = BoundCharacter.Get();
	if (!Movement || !Character || Movement->MovementMode != MOVE_Flying) return;
	FFindFloorResult Floor;
	Movement->FindFloor(Character->GetActorLocation(), Floor, false);
	const bool bPriorGroundMode = PreviousMovementMode == MOVE_Walking || PreviousMovementMode == MOVE_NavWalking;
	if (bPriorGroundMode && Floor.IsWalkableFloor() && Floor.GetDistanceToFloor() <= UCharacterMovementComponent::MAX_FLOOR_DIST)
		Movement->SetMovementMode(PreviousMovementMode, PreviousCustomMovementMode);
	else
		Movement->SetMovementMode(MOVE_Falling);
}

void UKZHitReactionAbility::HandleMontageNotify(FName NotifyName, const FBranchingPointNotifyPayload& Payload)
{
	if (!IsActive() || bEnding || NotifyName != TEXT("HitLand") ||
		Payload.MontageInstanceID != MontageInstanceId || Payload.SequenceAsset != PlayingMontage.Get()) return;
	const FGameplayAbilityActorInfo* Info = GetCurrentActorInfo();
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	UAnimInstance* Anim = BoundAnimInstance.Get();
	if (!Info || !Anim || Info->AvatarActor.Get() != BoundCharacter.Get() || Info->GetAnimInstance() != Anim ||
		Payload.SkelMeshComponent != (Anim ? Anim->GetSkelMeshComponent() : nullptr) ||
		!ASC || !ASC->IsAnimatingAbility(this) || GetCurrentMontage() != PlayingMontage.Get()) return;
	const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(PlayingMontage);
	if (!Instance || Instance->GetInstanceID() != MontageInstanceId) return;
	const uint32 Serial = ExecutionSerial;
	ClearMotionTask();
	if (!IsActive() || ExecutionSerial != Serial) return;
	RestoreRootMotionMode();
	if (!IsActive() || ExecutionSerial != Serial) return;
	RestoreMovementMode();
}

void UKZHitReactionAbility::ClearMontageTask()
{
	UAbilityTask_PlayMontageAndWait* Task = MontageTask;
	MontageTask = nullptr;
	if (Task)
	{
		Task->OnCompleted.RemoveDynamic(this, &ThisClass::HandleMontageCompleted);
		Task->OnInterrupted.RemoveDynamic(this, &ThisClass::HandleMontageAborted);
		Task->OnCancelled.RemoveDynamic(this, &ThisClass::HandleMontageAborted);
		Task->EndTask();
	}
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	if (ASC && ASC->IsAnimatingAbility(this) && GetCurrentMontage() == PlayingMontage.Get()) ASC->CurrentMontageStop();
	PlayingMontage = nullptr;
}

void UKZHitReactionAbility::HandleMontageCompleted() { FinishAbility(false); }
void UKZHitReactionAbility::HandleMontageAborted() { FinishAbility(true); }

void UKZHitReactionAbility::FinishAbility(const bool bWasCancelled)
{
	if (IsActive() && !bEnding)
		EndAbility(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(), GetCurrentActivationInfo(), false, bWasCancelled);
}

void UKZHitReactionAbility::EndAbility(FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo, FGameplayAbilityActivationInfo ActivationInfo,
	bool bReplicateEndAbility, bool bWasCancelled)
{
	if (!IsActive() || bEnding) return;
	bEnding = true;
	++ExecutionSerial;
	TWeakObjectPtr<AKZMonster> Monster = Cast<AKZMonster>(BoundCharacter.Get());
	if (BoundAnimInstance.IsValid())
		BoundAnimInstance->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotify);
	ClearMontageTask();
	ClearMotionTask();
	RestoreRootMotionMode();
	RestoreMovementMode();
	if (BoundCharacter.IsValid() && BoundCharacter->GetLocomotionComponent())
		BoundCharacter->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
	MovementHandle.Reset();
	BoundCharacter.Reset();
	BoundAnimInstance.Reset();
	BoundMovement.Reset();
	CurrentEvent = FGameplayTag();
	MontageInstanceId = INDEX_NONE;
	PreviousMovementMode = MOVE_None;
	PreviousCustomMovementMode = 0;
	PreviousRootMotionMode = ERootMotionMode::NoRootMotionExtraction;
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
	bEnding = false;
	if (Monster.IsValid()) Monster->RequestCombatStateRefresh();
}
