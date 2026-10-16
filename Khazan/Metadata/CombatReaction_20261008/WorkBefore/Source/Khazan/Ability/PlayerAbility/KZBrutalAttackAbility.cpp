#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"

#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"

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
			Distance >= BestDistance || FVector::DotProduct(Player->GetActorForwardVector(), ToTarget.GetSafeNormal2D()) < 0.f) continue;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(BrutalTargetVisibility), false, Player);
		Params.AddIgnoredActor(Monster);
		if (Player->GetWorld()->LineTraceTestByChannel(Player->GetActorLocation(), Monster->GetActorLocation(), ECC_Visibility, Params)) continue;
		Best = Monster;
		BestDistance = Distance;
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
	Player->SetActorLocationAndRotation(StartLocation, (bFromBack ? TargetForward : -TargetForward).Rotation(), false, nullptr, ETeleportType::TeleportPhysics);
	PlayingMontage = Montage;
	BoundAnimInstance = Anim;
	Anim->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotify);
	ResetInputEnd();
	Anim->RequestMontageInertialization(Montage, Montage->BlendIn.GetBlendTime(), nullptr);
	MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(this, TEXT("BrutalAttack"), Montage, 1.f, NAME_None, true);
	if (!MontageTask) { HandleMontageAborted(); return; }
	MontageTask->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	MontageTask->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	MontageTask->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	MontageTask->ReadyForActivation();
	if (IsActive())
		if (const FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage)) MontageInstanceId = Instance->GetInstanceID();
}

void UKZBrutalAttackAbility::HandleMontageNotify(FName Name, const FBranchingPointNotifyPayload& Payload)
{
	if (!IsActive() || Payload.MontageInstanceID != MontageInstanceId || Payload.SequenceAsset != PlayingMontage) return;
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
		if (!Source->ApplyGameplayEffectSpecToTarget(*Spec.Data.Get(), Monster->GetAbilitySystemComponent()).WasSuccessfullyApplied()) HandleMontageAborted();
	}
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
	TWeakObjectPtr<UKZExhaustionAbility> Exhaustion = VictimAbility;
	VictimAbility.Reset();
	if (UAnimInstance* Anim = BoundAnimInstance.Get()) Anim->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotify);
	BoundAnimInstance.Reset();
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
