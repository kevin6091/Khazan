#include "Ability/MonsterAbility/KZExhaustionAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZMonster.h"
#include "Components/CapsuleComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "KZGameplayTags.h"

namespace KZExhaustion
{
	const FName Start(TEXT("Start"));
	const FName Loop(TEXT("Loop"));
	const FName End(TEXT("End"));
	const FName Damage1(TEXT("Damage1"));
	const FName Damage2(TEXT("Damage2"));
}

UKZExhaustionAbility::UKZExhaustionAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalOnly;
	FGameplayTagContainer Tags;
	Tags.AddTag(KZGameplayTags::Ability_Reaction_Exhaustion);
	SetAssetTags(Tags); // Reaction is outside Ability.Action, so an attack cannot block forced exhaustion.
	ActivationOwnedTags.AddTag(KZGameplayTags::State_Exhausted);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_Movement_Input);
	ActivationOwnedTags.AddTag(KZGameplayTags::Block_StaminaRegen);
	BlockAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);
	CancelAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);
	ActivationBlockedTags.AddTag(KZGameplayTags::State_Dead);
}

AKZMonster* UKZExhaustionAbility::GetMonster() const
{
	return Cast<AKZMonster>(GetAvatarActorFromActorInfo());
}

const FKZMonsterStaminaSettings* UKZExhaustionAbility::GetSettings() const
{
	const AKZMonster* Monster = GetMonster();
	const UKZCharacterDefinitionData* Definition = Monster ? Monster->GetCharacterDefinition() : nullptr;
	return Definition ? &Definition->GetMonsterStaminaSettings() : nullptr;
}

bool UKZExhaustionAbility::IsAlive() const
{
	const UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	const UKZAttributeSet* Attributes = ASC ? ASC->GetSet<UKZAttributeSet>() : nullptr;
	return Attributes && Attributes->GetHP() > 0.f && !ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead);
}

bool UKZExhaustionAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const
{
	if (!Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags) || !ActorInfo)
		return false;
	const AKZMonster* Monster = Cast<AKZMonster>(ActorInfo->AvatarActor.Get());
	const UKZCharacterDefinitionData* Definition = Monster ? Monster->GetCharacterDefinition() : nullptr;
	const UKZAttributeSet* Attributes = ActorInfo->AbilitySystemComponent.IsValid()
		? ActorInfo->AbilitySystemComponent->GetSet<UKZAttributeSet>() : nullptr;
	if (!Definition || !Attributes || !ActorInfo->GetAnimInstance() || !Monster->GetLocomotionComponent() ||
		!Monster->HasAuthority() || !Monster->GetWorld() || Attributes->GetHP() <= 0.f || Attributes->GetStamina() > 0.f)
		return false;
	const FKZMonsterStaminaSettings& Settings = Definition->GetMonsterStaminaSettings();
	return Settings.bEnabled && FMath::IsFinite(Settings.ExhaustionSeconds) && Settings.ExhaustionSeconds >= 0.f &&
		Settings.ExhaustionMontage && Settings.ExhaustionMontage->GetSectionIndex(KZExhaustion::Start) != INDEX_NONE &&
		Settings.ExhaustionMontage->GetSectionIndex(KZExhaustion::Loop) != INDEX_NONE &&
		Settings.ExhaustionMontage->GetSectionIndex(KZExhaustion::End) != INDEX_NONE;
}

void UKZExhaustionAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
	ReleaseBrutalMovementIgnore();
	BrutalPartner.Reset();
	bFromBack = bAttackerCompleted = bVictimCompleted = bEnding = false;
	CurrentPhase = EPhase::None;
	BoundAnimInstance = ActorInfo ? ActorInfo->GetAnimInstance() : nullptr;
	AKZMonster* Monster = GetMonster();
	const FKZMonsterStaminaSettings* Settings = GetSettings();
	if (!Monster || !Settings || !BoundAnimInstance.IsValid() || !IsAlive() ||
		!CommitAbility(Handle, ActorInfo, ActivationInfo))
	{
		FinishAbility(true);
		return;
	}
	FKZMovementConstraint Constraint;
	Constraint.bOverrideRotationMode = true;
	Constraint.RotationModeOverride = EKZRotationMode::VelocityDirection;
	Constraint.DebugName = TEXT("Exhaustion");
	MovementHandle = Monster->GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
	if (!IsActive())
	{
		// A permission callback can end the Ability before Acquire returns its new handle.
		Monster->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
		MovementHandle.Reset();
		return;
	}
	if (!MovementHandle.IsValid())
	{
		FinishAbility(true);
		return;
	}
	// The authored duration includes Start. Zero deliberately has no expiry timer.
	if (Settings->ExhaustionSeconds > 0.f)
		GetWorld()->GetTimerManager().SetTimer(RecoveryTimer, this, &ThisClass::HandleRecoveryTimeout, Settings->ExhaustionSeconds, false);
	PlaySection(Settings->ExhaustionMontage, KZExhaustion::Start, EPhase::Start);
}

bool UKZExhaustionAbility::IsAvailableForBrutalAttack() const
{
	const UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	const UKZAttributeSet* Attributes = ASC ? ASC->GetSet<UKZAttributeSet>() : nullptr;
	return IsActive() && !bEnding && IsAlive() && Attributes && Attributes->GetStamina() <= 0.f &&
		!HasBrutalPartner() && (CurrentPhase == EPhase::Start || CurrentPhase == EPhase::Loop);
}

bool UKZExhaustionAbility::ClaimBrutalAttack(UKZBrutalAttackAbility* Attacker, const bool bAttackFromBack)
{
	if (!IsAvailableForBrutalAttack() || !IsValid(Attacker) || !Attacker->IsActive()) return false;
	const FKZMonsterStaminaSettings* Settings = GetSettings();
	UAnimMontage* Montage = Settings ? (bAttackFromBack ? Settings->BrutalBackVictimMontage.Get() : Settings->BrutalFrontVictimMontage.Get()) : nullptr;
	if (!Montage || Montage->GetSectionIndex(KZExhaustion::Damage1) == INDEX_NONE ||
		Montage->GetSectionIndex(KZExhaustion::Damage2) == INDEX_NONE) return false;
	ACharacter* AttackerPawn = Cast<ACharacter>(Attacker->GetAvatarActorFromActorInfo());
	AKZMonster* VictimPawn = GetMonster();
	UCapsuleComponent* AttackerCapsule = AttackerPawn ? AttackerPawn->GetCapsuleComponent() : nullptr;
	UCapsuleComponent* VictimCapsule = VictimPawn ? VictimPawn->GetCapsuleComponent() : nullptr;
	if (!IsValid(AttackerCapsule) || !IsValid(VictimCapsule) || AttackerPawn == VictimPawn) return false;
	BrutalPartner = Attacker;
	BrutalAttackerPawn = AttackerPawn;
	BrutalVictimPawn = VictimPawn;
	// Claim freezes the actor anchor immediately, including the still-playing
	// exhaustion Start/Loop; paired limbs continue to animate normally.
	if (UAnimInstance* Anim = BoundAnimInstance.Get())
	{
		PreviousBrutalRootMotionMode = Anim->RootMotionMode;
		bOwnsBrutalRootMotionMode = PreviousBrutalRootMotionMode != ERootMotionMode::IgnoreRootMotion;
		if (bOwnsBrutalRootMotionMode) Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	}
	// Component sweep ignores are directional. Preserve entries owned by other callers.
	bAddedAttackerMoveIgnore = !AttackerCapsule->GetMoveIgnoreActors().Contains(VictimPawn);
	bAddedVictimMoveIgnore = !VictimCapsule->GetMoveIgnoreActors().Contains(AttackerPawn);
	if (bAddedAttackerMoveIgnore) AttackerCapsule->IgnoreActorWhenMoving(VictimPawn, true);
	if (bAddedVictimMoveIgnore) VictimCapsule->IgnoreActorWhenMoving(AttackerPawn, true);
	bFromBack = bAttackFromBack;
	bAttackerCompleted = bVictimCompleted = false;
	GetWorld()->GetTimerManager().PauseTimer(RecoveryTimer);
	return true; // Keep the existing Start/Loop until the player's first hit point.
}

bool UKZExhaustionAbility::PlayBrutalReaction(const uint8 Phase)
{
	if (!IsActive() || bEnding || !HasBrutalPartner() ||
		(Phase != 1 && Phase != 2) || (Phase == 1 && CurrentPhase != EPhase::Start && CurrentPhase != EPhase::Loop) ||
		(Phase == 2 && CurrentPhase != EPhase::Brutal1)) return false;
	const FKZMonsterStaminaSettings* Settings = GetSettings();
	UAnimMontage* Montage = Settings ? (bFromBack ? Settings->BrutalBackVictimMontage.Get() : Settings->BrutalFrontVictimMontage.Get()) : nullptr;
	return PlaySection(Montage, Phase == 1 ? KZExhaustion::Damage1 : KZExhaustion::Damage2,
		Phase == 1 ? EPhase::Brutal1 : EPhase::Brutal2);
}

bool UKZExhaustionAbility::PlaySection(UAnimMontage* Montage, const FName Section, const EPhase Phase)
{
	if (!IsActive() || bEnding || !BoundAnimInstance.IsValid() || !Montage || Montage->GetSectionIndex(Section) == INDEX_NONE)
	{
		FinishAbility(true);
		return false;
	}
	ClearMontageTask(false);
	BoundAnimInstance->RequestMontageInertialization(Montage, Montage->BlendIn.GetBlendTime(), nullptr);
	CurrentPhase = Phase;
	PlayingMontage = Montage;
	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
		this, TEXT("ExhaustionMontage"), Montage, 1.f, Section, true, 1.f, 0.f, true);
	if (!Task)
	{
		FinishAbility(true);
		return false;
	}
	MontageTask = Task;
	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->ReadyForActivation();
	if (IsActive() && MontageTask == Task && (Phase == EPhase::Start || Phase == EPhase::Loop))
	{
		// Stay in the real falling/looping groggy pose until the existing recovery
		// timer or Brutal claim transitions it. Replaying the montage after each
		// auto blend-out inserted the locomotion pose between groggy loops.
		BoundAnimInstance->Montage_SetNextSection(KZExhaustion::Start, KZExhaustion::Loop, Montage);
		BoundAnimInstance->Montage_SetNextSection(KZExhaustion::Loop, KZExhaustion::Loop, Montage);
	}
	return IsActive() && MontageTask == Task;
}

void UKZExhaustionAbility::ClearMontageTask(const bool bStopMontage)
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
	if (bStopMontage && ASC && ASC->IsAnimatingAbility(this) && GetCurrentMontage() == PlayingMontage.Get())
		ASC->CurrentMontageStop(); // Engine default uses the montage's authored blend-out, not a new tuning value.
	PlayingMontage = nullptr;
}

void UKZExhaustionAbility::HandleMontageCompleted()
{
	const EPhase CompletedPhase = CurrentPhase;
	ClearMontageTask(false);
	if (!IsActive() || bEnding) return;
	if (CompletedPhase == EPhase::Start || CompletedPhase == EPhase::Loop)
	{
		const FKZMonsterStaminaSettings* Settings = GetSettings();
		PlaySection(Settings ? Settings->ExhaustionMontage.Get() : nullptr, KZExhaustion::Loop, EPhase::Loop);
	}
	else if (CompletedPhase == EPhase::Brutal2)
	{
		bVictimCompleted = true;
		CompleteBrutalPair();
	}
	else if (CompletedPhase == EPhase::End)
	{
		if (!IsAlive()) { FinishDeath(false); return; }
		UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
		const float MaxStamina = ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute());
		if (!FMath::IsFinite(MaxStamina)) { FinishAbility(true); return; }
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), MaxStamina);
		FinishAbility(false);
	}
	// Damage1 completion deliberately retains the pair and never starts recovery.
}

void UKZExhaustionAbility::NotifyBrutalAttackerFinished(const bool bWasCancelled)
{
	if (!IsActive() || bEnding || !HasBrutalPartner()) return;
	if (bWasCancelled || CurrentPhase != EPhase::Brutal2)
	{
		CancelBrutalPair(false); // The attacker is already inside its EndAbility.
		return;
	}
	bAttackerCompleted = true;
	CompleteBrutalPair();
}

void UKZExhaustionAbility::UpdateLethalBrutalPose()
{
	if (!IsActive() || bEnding || IsAlive() || !HasBrutalPartner() ||
		CurrentPhase != EPhase::Brutal2 || bVictimCompleted || !BoundAnimInstance.IsValid()) return;
	FAnimMontageInstance* Instance = BoundAnimInstance->GetActiveInstanceForMontage(PlayingMontage);
	if (!Instance || Instance->IsStopped()) return; // Cancellation keeps its existing recovery/death cleanup.
	// Only this lethal execution holds its last source pose. Waiting for the
	// ordinary task's blend-out completion would freeze the already-returned idle.
	// The shared montage asset and every nonlethal recovery keep auto blend-out.
	Instance->bEnableAutoBlendOut = false;
	if (!Instance->IsPlaying()) HandleMontageCompleted();
}

void UKZExhaustionAbility::CompleteBrutalPair()
{
	if (!IsActive() || bEnding || !bAttackerCompleted || !bVictimCompleted) return;
	BrutalPartner.Reset();
	ReleaseBrutalMovementIgnore();
	if (!IsAlive()) { FinishDeath(false); return; }
	BeginRecovery();
}

void UKZExhaustionAbility::CancelBrutalPair(const bool bAbortAttacker)
{
	UKZBrutalAttackAbility* Attacker = BrutalPartner.Get();
	BrutalPartner.Reset(); // Break the notification cycle before invoking the other owner.
	ReleaseBrutalMovementIgnore();
	bAttackerCompleted = bVictimCompleted = false;
	if (bAbortAttacker && Attacker) Attacker->AbortFromVictim(this);
	if (!IsActive() || bEnding) return;
	if (!IsAlive()) { FinishDeath(true); return; }
	const FKZMonsterStaminaSettings* Settings = GetSettings();
	if (PlaySection(Settings ? Settings->ExhaustionMontage.Get() : nullptr, KZExhaustion::Loop, EPhase::Loop))
		GetWorld()->GetTimerManager().UnPauseTimer(RecoveryTimer); // Resume the remaining authored time.
}

void UKZExhaustionAbility::ReleaseBrutalMovementIgnore()
{
	const bool bRestoreRootMotion = bOwnsBrutalRootMotionMode;
	bOwnsBrutalRootMotionMode = false;
	if (UAnimInstance* Anim = BoundAnimInstance.Get(); bRestoreRootMotion && Anim &&
		Anim->RootMotionMode == ERootMotionMode::IgnoreRootMotion)
		Anim->SetRootMotionMode(PreviousBrutalRootMotionMode);
	const TWeakObjectPtr<ACharacter> AttackerPawn = BrutalAttackerPawn;
	const TWeakObjectPtr<AKZMonster> VictimPawn = BrutalVictimPawn;
	const bool bRemoveAttackerIgnore = bAddedAttackerMoveIgnore;
	const bool bRemoveVictimIgnore = bAddedVictimMoveIgnore;
	BrutalAttackerPawn.Reset();
	BrutalVictimPawn.Reset();
	bAddedAttackerMoveIgnore = bAddedVictimMoveIgnore = false;
	// Pending-destroy pawns may still have a registered capsule during EndPlay.
	// Serial-checked weak lookup permits removing only our old pair entry, never a new avatar's.
	ACharacter* OriginalAttacker = AttackerPawn.Get(true);
	AKZMonster* OriginalVictim = VictimPawn.Get(true);
	if (!OriginalAttacker || !OriginalVictim) return;
	if (bRemoveAttackerIgnore)
		if (UCapsuleComponent* Capsule = OriginalAttacker->GetCapsuleComponent()) Capsule->IgnoreActorWhenMoving(OriginalVictim, false);
	if (bRemoveVictimIgnore)
		if (UCapsuleComponent* Capsule = OriginalVictim->GetCapsuleComponent()) Capsule->IgnoreActorWhenMoving(OriginalAttacker, false);
}

void UKZExhaustionAbility::HandleMontageAborted()
{
	if (!IsActive() || bEnding) return;
	if (HasBrutalPartner()) CancelBrutalPair(true);
	else FinishAbility(true);
}

void UKZExhaustionAbility::HandleRecoveryTimeout()
{
	if (IsActive() && !bEnding && !HasBrutalPartner()) BeginRecovery();
}

void UKZExhaustionAbility::BeginRecovery()
{
	if (!IsActive() || bEnding || HasBrutalPartner() || CurrentPhase == EPhase::End) return;
	GetWorld()->GetTimerManager().ClearTimer(RecoveryTimer);
	if (!IsAlive()) { FinishDeath(false); return; }
	const FKZMonsterStaminaSettings* Settings = GetSettings();
	PlaySection(Settings ? Settings->ExhaustionMontage.Get() : nullptr, KZExhaustion::End, EPhase::End);
}

void UKZExhaustionAbility::FinishAbility(const bool bWasCancelled)
{
	if (IsActive() && !bEnding)
		EndAbility(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(), GetCurrentActivationInfo(), false, bWasCancelled);
}

void UKZExhaustionAbility::FinishDeath(const bool bWasCancelled)
{
	TWeakObjectPtr<AKZMonster> Monster = GetMonster();
	FinishAbility(bWasCancelled);
	// The paired Damage2 pose ends the execution, but it is not a death animation.
	// Release its montage first, then enter the monster's authored death montage.
	if (Monster.IsValid()) Monster->FinishDeathPresentation();
}

void UKZExhaustionAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
	if (!IsActive() || bEnding) return;
	bEnding = true;
	TWeakObjectPtr<AKZMonster> Monster = GetMonster();
	UKZBrutalAttackAbility* Attacker = BrutalPartner.Get();
	BrutalPartner.Reset();
	ReleaseBrutalMovementIgnore();
	if (Attacker) Attacker->AbortFromVictim(this);
	if (UWorld* World = GetWorld()) World->GetTimerManager().ClearTimer(RecoveryTimer);
	ClearMontageTask(true);
	if (Monster.IsValid() && Monster->GetLocomotionComponent())
		Monster->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
	MovementHandle.Reset();
	BoundAnimInstance.Reset();
	CurrentPhase = EPhase::None;
	bFromBack = bAttackerCompleted = bVictimCompleted = false;
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
	bEnding = false;
	if (Monster.IsValid()) Monster->RequestCombatStateRefresh();
}
