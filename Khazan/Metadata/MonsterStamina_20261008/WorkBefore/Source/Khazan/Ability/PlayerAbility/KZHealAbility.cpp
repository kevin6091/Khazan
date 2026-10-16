#include "Ability/PlayerAbility/KZHealAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZCharacter.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KZGameplayTags.h"

UKZHealAbility::UKZHealAbility()
{
	SetAssetTags(FGameplayTagContainer(KZGameplayTags::Ability_Action_Heal));
}

bool UKZHealAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const
{
	if (!Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags) || !ActorInfo ||
		!HealMontage || !DrawMontage || !HealEffect || !ActorInfo->GetAnimInstance())
	{
		return false;
	}
	const AKZCharacter* Character = Cast<AKZCharacter>(ActorInfo->AvatarActor.Get());
	const UAbilitySystemComponent* ASC = ActorInfo->AbilitySystemComponent.Get();
	return Character && Character->GetLocomotionComponent() && Character->GetCharacterMovement()->IsMovingOnGround() &&
		ASC && ASC->GetSet<UKZAttributeSet>() && ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f;
}

void UKZHealAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
	bHealApplied = false;
	ActiveMontageInstanceId = INDEX_NONE;
	ResetInputEnd();
	if (!CommitAbility(Handle, ActorInfo, ActivationInfo))
	{
		HandleMontageAborted();
		return;
	}
	AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo());
	FKZMovementConstraint Constraint;
	Constraint.MaxAllowedGait = EKZGait::Walk;
	Constraint.DebugName = TEXT("Heal");
	MovementHandle = Character->GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
	if (!IsActive())
	{
		Character->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
		return;
	}
	BoundAnimInstance = ActorInfo->GetAnimInstance();
	if (!MovementHandle.IsValid() || !BoundAnimInstance.IsValid())
	{
		HandleMontageAborted();
		return;
	}
	BoundAnimInstance->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotify);
	PlayHealMontage(HealMontage);
}

void UKZHealAbility::PlayHealMontage(UAnimMontage* Montage)
{
	ActiveMontageInstanceId = INDEX_NONE;
	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
		this, TEXT("HealMontage"), Montage);
	if (!Task)
	{
		HandleMontageAborted();
		return;
	}
	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->ReadyForActivation();
	if (IsActive() && BoundAnimInstance.IsValid())
	{
		if (const FAnimMontageInstance* Instance = BoundAnimInstance->GetActiveInstanceForMontage(Montage))
		{
			ActiveMontageInstanceId = Instance->GetInstanceID();
		}
	}
}

void UKZHealAbility::HandleMontageNotify(FName NotifyName, const FBranchingPointNotifyPayload& Payload)
{
	if (!IsActive() || Payload.SequenceAsset != GetCurrentMontage() || Payload.MontageInstanceID != ActiveMontageInstanceId)
	{
		return;
	}
	if (NotifyName == TEXT("WeaponStow"))
	{
		if (!StoreWeapons()) HandleMontageAborted();
	}
	else if (NotifyName == TEXT("WeaponDraw"))
	{
		RestoreWeapons();
	}
	else if (NotifyName == TEXT("HealStart") && BoundAnimInstance.IsValid())
	{
		// Reuse this montage's configured blend time at the Stow -> Heal segment boundary.
		BoundAnimInstance->RequestMontageInertialization(HealMontage, HealMontage->BlendIn.GetBlendTime(), nullptr);
	}
	else if (NotifyName == TEXT("Heal") && !bHealApplied)
	{
		FGameplayEffectSpecHandle Spec = MakeOutgoingGameplayEffectSpec(HealEffect);
		bHealApplied = true; // Set before applying: attribute callbacks may cancel this execution.
		if (!Spec.IsValid() || !ApplyGameplayEffectSpecToOwner(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(),
			GetCurrentActivationInfo(), Spec).WasSuccessfullyApplied())
		{
			HandleMontageAborted();
		}
	}
}

void UKZHealAbility::HandleMontageCompleted()
{
	if (!IsActive()) return;
	if (!HasInputEnded())
	{
		PlayHealMontage(DrawMontage);
		if (IsActive())
		{
			if (AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo()))
				Character->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
			SetInputEnded(); // Existing Action cancel rules now allow immediate combat takeover.
		}
		return;
	}
	EndAbility(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(), GetCurrentActivationInfo(), false, false);
}

bool UKZHealAbility::StoreWeapons()
{
	if (!StoredWeapons.IsEmpty()) return true;
	const AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo());
	USkeletalMeshComponent* Mesh = Character ? Character->GetMesh() : nullptr;
	if (!Mesh || !Mesh->DoesSocketExist(LeftBackSocket) || !Mesh->DoesSocketExist(RightBackSocket)) return false;
	// Snapshot both hands before reattachment changes the parent's child list.
	for (USceneComponent* Child : Mesh->GetAttachChildren())
	{
		if (!Child || (Child->GetAttachSocketName() != TEXT("Weapon_L") && Child->GetAttachSocketName() != TEXT("Weapon_R"))) continue;
		StoredWeapons.Add({Child, Mesh, Child->GetAttachSocketName(), Child->GetRelativeTransform()});
	}
	if (StoredWeapons.Num() != 2)
	{
		StoredWeapons.Reset();
		return false;
	}
	for (const FStoredWeapon& Weapon : StoredWeapons)
	{
		USceneComponent* Component = Weapon.Component.Get();
		const FName Socket = Weapon.HandSocket == TEXT("Weapon_L") ? LeftBackSocket : RightBackSocket;
		if (!Component || !Component->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetIncludingScale, Socket)) return false;
		Component->SetRelativeScale3D(Weapon.RelativeTransform.GetScale3D());
	}
	return true;
}

void UKZHealAbility::RestoreWeapons()
{
	for (const FStoredWeapon& Weapon : StoredWeapons)
	{
		if (USceneComponent* Component = Weapon.Component.Get(); Component && Weapon.Parent.IsValid())
		{
			Component->AttachToComponent(Weapon.Parent.Get(), FAttachmentTransformRules::KeepRelativeTransform, Weapon.HandSocket);
			Component->SetRelativeTransform(Weapon.RelativeTransform);
		}
	}
	StoredWeapons.Reset();
}

void UKZHealAbility::HandleMontageAborted()
{
	if (IsActive()) EndAbility(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(), GetCurrentActivationInfo(), false, true);
}

void UKZHealAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
	const TWeakObjectPtr<UAnimInstance> EndingAnim = BoundAnimInstance;
	const int32 EndingInstanceId = ActiveMontageInstanceId;
	if (BoundAnimInstance.IsValid())
	{
		BoundAnimInstance->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotify);
	}
	BoundAnimInstance.Reset();
	ActiveMontageInstanceId = INDEX_NONE;
	bHealApplied = false;
	RestoreWeapons();
	if (AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo()))
	{
		Character->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
	}
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
	// Task teardown first prevents notify/cancel reentry. Stop only this old instance, never the incoming montage.
	if (bWasCancelled && EndingAnim.IsValid())
		if (FAnimMontageInstance* Instance = EndingAnim->GetMontageInstanceForID(EndingInstanceId))
			Instance->Stop(FAlphaBlend(0.f));
}
