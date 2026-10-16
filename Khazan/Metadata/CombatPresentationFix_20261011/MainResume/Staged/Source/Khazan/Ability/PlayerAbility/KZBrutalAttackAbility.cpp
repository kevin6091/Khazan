#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"

#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Character/Component/KZLockOnComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"
#include "TimerManager.h"

UKZBrutalAttackAbility::UKZBrutalAttackAbility()
{
	FGameplayTagContainer Tags;
	Tags.AddTag(KZGameplayTags::Ability_Action_BrutalAttack);
	SetAssetTags(Tags);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_Movement_Input);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_StaminaRegen);
}

AKZMonster* UKZBrutalAttackAbility::FindBrutalTarget(const FGameplayAbilityActorInfo* Info) const
{
	const AKZPlayer* Player = Info ? Cast<AKZPlayer>(Info->AvatarActor.Get()) : nullptr;
	if (!Player || !Player->HasAuthority() || !Player->GetCharacterMovement()->IsMovingOnGround()) return nullptr;
	AKZMonster* Best = nullptr;
	const UKZLockOnComponent* LockOn = Player->FindComponentByClass<UKZLockOnComponent>();
	const AKZMonster* LockedTarget = LockOn ? LockOn->GetCurrentTarget() : nullptr;
	double BestDistance = TNumericLimits<double>::Max();
	for (TActorIterator<AKZMonster> It(Player->GetWorld()); It; ++It)
	{
		AKZMonster* Monster = *It;
		UKZExhaustionAbility* Exhaustion = Monster->GetActiveExhaustionAbility();
		if (!Exhaustion || !Exhaustion->IsAvailableForBrutalAttack() || !Monster->GetCharacterDefinition()) continue;
		const FKZMonsterStaminaSettings& Settings = Monster->GetCharacterDefinition()->GetMonsterStaminaSettings();
		const FVector ToTarget = Monster->GetActorLocation() - Player->GetActorLocation();
		const double Distance = ToTarget.Size();
		// Project targeting policy: nearest eligible visible target in the player's forward half-space.
		if (!FMath::IsFinite(Settings.BrutalAttackRange) || Distance > Settings.BrutalAttackRange ||
			FVector::DotProduct(Player->GetActorForwardVector(), ToTarget.GetSafeNormal2D()) < 0.f) continue;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(BrutalTargetVisibility), false, Player);
		Params.AddIgnoredActor(Monster);
		if (Player->GetWorld()->LineTraceTestByChannel(Player->GetActorLocation(), Monster->GetActorLocation(), ECC_Visibility, Params)) continue;
		// The indicator and B execution share the same eligible locked target.
		if (Monster == LockedTarget) return Monster;
		if (Distance < BestDistance) { Best = Monster; BestDistance = Distance; }
	}
	return Best;
}

bool UKZBrutalAttackAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
	const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* Relevant) const
{
	return Super::CanActivateAbility(Handle, Info, SourceTags, TargetTags, Relevant) && FindBrutalTarget(Info);
}

void UKZBrutalAttackAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
	FGameplayAbilityActivationInfo Activation, const FGameplayEventData* Event)
{
	Super::ActivateAbility(Handle, Info, Activation, Event);
	AKZPlayer* Player = Info ? Cast<AKZPlayer>(Info->AvatarActor.Get()) : nullptr;
	AKZMonster* Monster = FindBrutalTarget(Info);
	UKZExhaustionAbility* Exhaustion = Monster ? Monster->GetActiveExhaustionAbility() : nullptr;
	if (!Player || !Monster || !Exhaustion)
	{
		EndAbility(Handle, Info, Activation, true, true);
		return;
	}
	const FKZMonsterStaminaSettings& Settings = Monster->GetCharacterDefinition()->GetMonsterStaminaSettings();
	const bool bFromBack = FVector::DotProduct(Monster->GetActorForwardVector(), Player->GetActorLocation() - Monster->GetActorLocation()) < 0.f;
	UAnimMontage* Montage = bFromBack ? Settings.BrutalBackPlayerMontage : Settings.BrutalFrontPlayerMontage;
	UAnimInstance* Anim = Player->GetMesh()->GetAnimInstance();
	const float CapsuleDistance = Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float Spacing = FMath::Max(CapsuleDistance, Settings.BrutalAlignmentDistance);
	const FVector TargetForward = Monster->GetActorForwardVector().GetSafeNormal2D();
	FVector StartLocation = Monster->GetActorLocation() + TargetForward * (bFromBack ? -Spacing : Spacing);
	StartLocation.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(BrutalAlignment), false, Player);
	Params.AddIgnoredActor(Monster);
	if (!Montage || !Anim || !Settings.DamageEffect || !FMath::IsFinite(Settings.BrutalHPDamage) || Settings.BrutalHPDamage < 0.f ||
		Player->GetWorld()->OverlapBlockingTestByChannel(StartLocation, FQuat::Identity, Player->GetCapsuleComponent()->GetCollisionObjectType(),
			FCollisionShape::MakeCapsule(Player->GetCapsuleComponent()->GetScaledCapsuleRadius(), Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Params) ||
		!CommitAbility(Handle, Info, Activation) || !Exhaustion->ClaimBrutalAttack(this, bFromBack))
	{
		EndAbility(Handle, Info, Activation, true, true);
		return;
	}
	Target = Monster;
	VictimAbility = Exhaustion;
	bFirstReactionSent = bSecondReactionSent = bMontageCompleted = false;
	bConfirmedEffectHitObserved = false;
	PlayedConfirmedEffects.Reset();
	ClearCombatEffects();
	FKZMovementConstraint Constraint;
	Constraint.bOverrideRotationMode = true;
	Constraint.RotationModeOverride = EKZRotationMode::VelocityDirection;
	Constraint.DebugName = TEXT("BrutalAttack");
	MovementHandle = Player->GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
	if (!IsActive())
	{
		Player->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
		MovementHandle.Reset();
		return;
	}
	if (!MovementHandle.IsValid()) { HandleMontageAborted(); return; }
	Player->GetCharacterMovement()->StopMovementImmediately();
	AlignmentStart = Player->GetActorLocation();
	AlignmentDestination = StartLocation;
	AlignmentStartRotation = Player->GetActorQuat();
	AlignmentDestinationRotation = (bFromBack ? TargetForward : -TargetForward).Rotation().Quaternion();
	AlignmentSeconds = FMath::IsFinite(Settings.BrutalAlignmentSeconds) ? FMath::Max(Settings.BrutalAlignmentSeconds, 0.f) : 0.f;
	PlayingMontage = Montage;
	BoundAnimInstance = Anim;
	// Alignment owns actor placement through montage completion, including its
	// blend-out tail. Keep pose/root extraction, discard only root travel/yaw.
	PreviousRootMotionMode = Anim->RootMotionMode;
	bOwnsRootMotionMode = PreviousRootMotionMode != ERootMotionMode::IgnoreRootMotion;
	if (bOwnsRootMotionMode) Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Anim->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotify);
	Anim->OnPlayMontageNotifyEnd.AddUniqueDynamic(this, &ThisClass::HandleMontageNotify);
	ResetInputEnd();
	Anim->RequestMontageInertialization(Montage, Montage->BlendIn.GetBlendTime(), nullptr);
	MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(this, TEXT("BrutalAttack"), Montage, 1.f, NAME_None, true);
	if (!MontageTask) { HandleMontageAborted(); return; }
	MontageTask->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	MontageTask->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	MontageTask->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	MontageTask->ReadyForActivation();
	if (IsActive())
	{
		if (const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage)) MontageInstanceId = Instance->GetInstanceID();
		AlignmentTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &ThisClass::UpdateAlignment);
	}
}

void UKZBrutalAttackAbility::UpdateAlignment()
{
	AKZPlayer* Player = Cast<AKZPlayer>(GetAvatarActorFromActorInfo());
	AKZMonster* Monster = Target.Get();
	UAnimInstance* Anim = BoundAnimInstance.Get();
	const FAnimMontageInstance* Instance = Anim && PlayingMontage ? Anim->GetActiveInstanceForMontage(PlayingMontage) : nullptr;
	if (!IsActive() || !Player || !Monster || !Instance || Instance->GetInstanceID() != MontageInstanceId ||
		!VictimAbility.IsValid() || !VictimAbility->IsActive()) { HandleMontageAborted(); return; }
	// Original Grapple_Start MoveTo_4 Notify[6].LinkValue=.03356, BlendOption=CubicInOut.
	// Start has dilation1, so this marker is already current montage seconds, not mesh-scaled time.
	const float Time = Anim->Montage_GetPosition(PlayingMontage) - .03356f;
	if (Time < 0.f)
	{
		AlignmentTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &ThisClass::UpdateAlignment);
		return;
	}
	const float Alpha = AlignmentSeconds > 0.f ? FMath::Clamp(Time / AlignmentSeconds, 0.f, 1.f) : 1.f;
	const float Ease = FMath::InterpEaseInOut(0.f, 1.f, Alpha, 3.f); // Cubic exponent is a mathematical constant.
	// An exhaustion pose can still have one already-extracted movement update at
	// claim time. Align against the live victim, rather than its pre-claim capsule.
	const float CapsuleDistance = Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float Spacing = FMath::Max(CapsuleDistance, Monster->GetCharacterDefinition()->GetMonsterStaminaSettings().BrutalAlignmentDistance);
	AlignmentDestination = Monster->GetActorLocation() - AlignmentDestinationRotation.GetForwardVector() * Spacing;
	AlignmentDestination.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Position = FMath::Lerp(AlignmentStart, AlignmentDestination, Ease);
	UCharacterMovementComponent* Movement = Player->GetCharacterMovement();
	const int32 AlignmentInstance = MontageInstanceId;
	const TWeakObjectPtr<AKZMonster> AlignmentTarget = Target;
	FHitResult Hit;
	Movement->SafeMoveUpdatedComponent(Position - Player->GetActorLocation(),
		FQuat::Slerp(AlignmentStartRotation, AlignmentDestinationRotation, Ease), true, Hit);
	if (!IsActive() || MontageInstanceId != AlignmentInstance || Target != AlignmentTarget) return;
	// Original bStopMoveOnBlocking=true. No teleport through a wall or forced sweep fallback.
	if (Hit.IsValidBlockingHit()) { HandleMontageAborted(); return; }
	if (Alpha < 1.f)
		AlignmentTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &ThisClass::UpdateAlignment);
	else AlignmentTimer.Invalidate();
}

void UKZBrutalAttackAbility::HandleMontageNotify(FName Name, const FBranchingPointNotifyPayload& Payload)
{
	if (!IsActive() || Payload.MontageInstanceID != MontageInstanceId || Payload.SequenceAsset != PlayingMontage) return;
	const FGameplayAbilityActorInfo* EffectActorInfo = GetCurrentActorInfo();
	UAnimInstance* Anim = BoundAnimInstance.Get();
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	const FAnimMontageInstance* Instance = IsValid(Anim) ? Anim->GetActiveInstanceForMontage(PlayingMontage) : nullptr;
	if (!EffectActorInfo || !IsValid(Payload.SkelMeshComponent) || !IsValid(ASC) ||
		!ASC->IsAnimatingAbility(this) || !Instance || Instance->GetInstanceID() != Payload.MontageInstanceID ||
		Payload.SkelMeshComponent->GetOwner() != EffectActorInfo->AvatarActor.Get() ||
		Payload.SkelMeshComponent->GetAnimInstance() != Anim || EffectActorInfo->GetAnimInstance() != Anim) return;
	if (const UKZAnimNotify_CombatEffect* Effect = Payload.NotifyEvent
		? Cast<UKZAnimNotify_CombatEffect>(Payload.NotifyEvent->Notify.Get()) : nullptr)
	{
		// Data children share one engine marker. Preserve an equal-time original
		// BrutalHit name and process its gameplay callback after feedback.
		for (const bool bEnding : {true, false})
		{
			const auto ProcessEffect = [this, &Payload, bEnding](const UKZAnimNotify_CombatEffect* Entry)
			{
				if (!IsActive() || !IsValid(Entry) || Entry->EventId.IsNone() || Entry->bEndEvent != bEnding) return;
				if (bEnding) StopCombatEffect(Entry->EventId, Payload.MontageInstanceID);
				else StartBrutalCombatEffect(*Entry, Payload);
			};
			ProcessEffect(Effect);
			for (const UKZAnimNotify_CombatEffect* Child : Effect->BatchedEffects) ProcessEffect(Child);
		}
	}
	if (!IsActive()) return;
	UKZExhaustionAbility* Exhaustion = VictimAbility.Get();
	AKZMonster* Monster = Target.Get();
	if (!Exhaustion || !Exhaustion->IsActive() || !Monster) { HandleMontageAborted(); return; }
	if (Name == TEXT("BrutalHit1") && !bFirstReactionSent)
	{
		bFirstReactionSent = true;
		if (!Exhaustion->PlayBrutalReaction(1)) HandleMontageAborted();
	}
	else if (Name == TEXT("BrutalHit2") && bFirstReactionSent && !bSecondReactionSent)
	{
		bSecondReactionSent = true;
		if (!Exhaustion->PlayBrutalReaction(2)) { HandleMontageAborted(); return; }
		const FKZMonsterStaminaSettings& Settings = Monster->GetCharacterDefinition()->GetMonsterStaminaSettings();
		UAbilitySystemComponent* Source = GetAbilitySystemComponentFromActorInfo();
		if (!Source || !Monster->GetAbilitySystemComponent()) { HandleMontageAborted(); return; }
		FGameplayEffectContextHandle Context = Source->MakeEffectContext();
		Context.AddInstigator(GetAvatarActorFromActorInfo(), GetAvatarActorFromActorInfo());
		const FGameplayEffectSpecHandle Spec = Source->MakeOutgoingSpec(Settings.DamageEffect, GetAbilityLevel(), Context);
		if (!Spec.IsValid()) { HandleMontageAborted(); return; }
		Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), -Settings.BrutalHPDamage);
		Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")), 0.f);
		// Applying a GE can synchronously cancel and restart this InstancedPerActor
		// object. Capture only the existing owner identities; no extra execution state.
		const TWeakObjectPtr<UAnimMontage> HitMontage = PlayingMontage;
		const int32 HitInstanceId = MontageInstanceId;
		const TWeakObjectPtr<AKZMonster> HitTarget = Monster;
		const TWeakObjectPtr<UKZExhaustionAbility> HitVictim = VictimAbility;
		const TWeakObjectPtr<AActor> HitAvatar = GetAvatarActorFromActorInfo();
		const TWeakObjectPtr<UAbilitySystemComponent> HitASC = Source;
		const TWeakObjectPtr<UAbilitySystemComponent> HitTargetASC = Monster->GetAbilitySystemComponent();
		const TWeakObjectPtr<UAnimInstance> HitAnim = Anim;
		const FActiveGameplayEffectHandle Result = Source->ApplyGameplayEffectSpecToTarget(*Spec.Data.Get(), HitTargetASC.Get());
		const FAnimMontageInstance* CurrentInstance = HitAnim.IsValid() && HitMontage.IsValid()
			? HitAnim->GetActiveInstanceForMontage(HitMontage.Get()) : nullptr;
		if (!IsActive() || PlayingMontage != HitMontage.Get() || MontageInstanceId != HitInstanceId ||
			Target != HitTarget || VictimAbility != HitVictim || GetAvatarActorFromActorInfo() != HitAvatar.Get() ||
			GetAbilitySystemComponentFromActorInfo() != HitASC.Get() || BoundAnimInstance != HitAnim ||
			!HitTarget.IsValid() || HitTarget->GetAbilitySystemComponent() != HitTargetASC.Get() ||
			!CurrentInstance || CurrentInstance->GetInstanceID() != HitInstanceId) return;
		if (!Result.WasSuccessfullyApplied()) { HandleMontageAborted(); return; }
		if (IsActive() && Settings.BrutalHPDamage > 0.f)
		{
			// Presentation adapter: only this existing accepted negative-HP producer
			// confirms blood. A paired reaction or the product's unassigned HP0
			// never fabricates a successful damaging hit. Original BattleEffectIndex
			// linkage is unavailable; later source windows share this execution hit.
			bConfirmedEffectHitObserved = true;
			const float HitTime = Payload.NotifyEvent ? Payload.NotifyEvent->GetTriggerTime() : Anim->Montage_GetPosition(PlayingMontage);
			const float CurrentTime = Anim->Montage_GetPosition(PlayingMontage);
			for (FAnimNotifyEvent& Event : HitMontage->Notifies)
			{
				const UKZAnimNotify_CombatEffect* Parent = Cast<UKZAnimNotify_CombatEffect>(Event.Notify.Get());
				if (!Parent) continue;
				const auto RecoverEffect = [this, &Payload, HitTime, CurrentTime, &Event, HitMontage, HitInstanceId](const UKZAnimNotify_CombatEffect* Entry)
				{
					if (!IsActive() || PlayingMontage != HitMontage.Get() || MontageInstanceId != HitInstanceId ||
						!IsValid(Entry) || Entry->bEndEvent || !Entry->bOnAttackSuccessed || Entry->EventId.IsNone() ||
						HitTime < Entry->WindowStartTime || HitTime > Entry->WindowEndTime) return;
					FBranchingPointNotifyPayload EffectPayload(Payload.SkelMeshComponent, HitMontage.Get(), &Event, HitInstanceId);
					const float Duration = CurrentTime >= Entry->WindowEndTime
						? Entry->WindowEndTime - Entry->WindowStartTime : 0.f;
					StartBrutalCombatEffect(*Entry, EffectPayload, Duration);
				};
				RecoverEffect(Parent);
				for (const UKZAnimNotify_CombatEffect* Child : Parent->BatchedEffects) RecoverEffect(Child);
			}
		}
	}
}


void UKZBrutalAttackAbility::StartBrutalCombatEffect(const UKZAnimNotify_CombatEffect& Effect,
	const FBranchingPointNotifyPayload& Payload, const float RecoveredWindowDuration)
{
	if (!IsActive() || Payload.MontageInstanceID != MontageInstanceId || Payload.SequenceAsset != PlayingMontage ||
		(Effect.bOnAttackSuccessed && (!bConfirmedEffectHitObserved || PlayedConfirmedEffects.Contains(Effect.EventId)))) return;
	StartCombatEffect(Effect, Payload, Effect.bOnAttackSuccessed && bConfirmedEffectHitObserved, RecoveredWindowDuration);
	if (Effect.bOnAttackSuccessed && ActiveCombatEffects.ContainsByPredicate(
		[&Effect, &Payload](const FActiveCombatEffect& Record)
		{
			return Record.Component.IsValid() && Record.EventId == Effect.EventId && Record.MontageInstanceId == Payload.MontageInstanceID;
		})) PlayedConfirmedEffects.Add(Effect.EventId);
}

void UKZBrutalAttackAbility::HandleMontageCompleted()
{
	bMontageCompleted = bFirstReactionSent && bSecondReactionSent;
	EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, !bMontageCompleted);
}

void UKZBrutalAttackAbility::HandleMontageAborted()
{
	if (IsActive()) EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, true);
}

void UKZBrutalAttackAbility::AbortFromVictim(const UKZExhaustionAbility* NotifyingVictim)
{
	// InstancedPerActor can already be running against another victim when the old reaction ends.
	if (NotifyingVictim && VictimAbility.Get() == NotifyingVictim) HandleMontageAborted();
}

void UKZBrutalAttackAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
	FGameplayAbilityActivationInfo Activation, bool bReplicate, bool bCancelled)
{
	if (!IsActive()) return;
	const bool bPairWasCancelled = bCancelled || !bMontageCompleted;
	if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(AlignmentTimer);
	TWeakObjectPtr<UKZExhaustionAbility> Exhaustion = VictimAbility;
	VictimAbility.Reset();
	ClearCombatEffects(!bPairWasCancelled);
	PlayedConfirmedEffects.Reset();
	bConfirmedEffectHitObserved = false;
	if (UAnimInstance* Anim = BoundAnimInstance.Get())
	{
		const bool bRestoreRootMotion = bOwnsRootMotionMode;
		bOwnsRootMotionMode = false;
		if (bRestoreRootMotion && Anim->RootMotionMode == ERootMotionMode::IgnoreRootMotion)
			Anim->SetRootMotionMode(PreviousRootMotionMode);
		Anim->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotify);
		Anim->OnPlayMontageNotifyEnd.RemoveDynamic(this, &ThisClass::HandleMontageNotify);
	}
	BoundAnimInstance.Reset();
	bOwnsRootMotionMode = false;
	if (MontageTask)
	{
		MontageTask->OnCompleted.RemoveAll(this);
		MontageTask->OnInterrupted.RemoveAll(this);
		MontageTask->OnCancelled.RemoveAll(this);
		MontageTask->EndTask();
		MontageTask = nullptr;
	}
	if (UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo(); ASC && ASC->IsAnimatingAbility(this) &&
		ASC->GetCurrentMontage() == PlayingMontage && (bCancelled || !bMontageCompleted)) ASC->CurrentMontageStop();
	if (AKZPlayer* Player = Cast<AKZPlayer>(GetAvatarActorFromActorInfo())) Player->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
	Target.Reset();
	PlayingMontage = nullptr;
	MontageInstanceId = INDEX_NONE;
	Super::EndAbility(Handle, Info, Activation, bReplicate, bCancelled);
	if (Exhaustion.IsValid() && Exhaustion->IsActive()) Exhaustion->NotifyBrutalAttackerFinished(bPairWasCancelled);
}
