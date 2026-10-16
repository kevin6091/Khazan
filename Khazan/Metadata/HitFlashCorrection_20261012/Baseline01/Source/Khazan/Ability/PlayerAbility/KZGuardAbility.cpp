#include "Ability/PlayerAbility/KZGuardAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_WaitGameplayEvent.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZCharacter.h"
#include "Character/KZMonster.h"
#include "Components/SkeletalMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"

namespace KZGuard
{
	const FName Start(TEXT("Start"));
	const FName End(TEXT("End"));
	const FName InputEnd(TEXT("InputEnd"));
	const FName StaminaDamage(TEXT("GuardStaminaDamage"));
	const FName SuccessSections[] = {TEXT("Suc_F"), TEXT("Suc_L"), TEXT("Suc_R")};
	const FName ParryLeft(TEXT("Parry_L"));
	const FName ParryRight(TEXT("Parry_R"));
}

UKZGuardAbility::UKZGuardAbility()
{
	FGameplayTagContainer Tags;
	Tags.AddTag(KZGameplayTags::Ability_Action_Guard);
	SetAssetTags(Tags);
}

bool UKZGuardAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const
{
	if (!Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags) || !ActorInfo ||
		!GuardMontage || !GuardStateEffect || !GuardHitStaminaEffect || !GuardHitRecoveryDelayEffect)
	{
		return false;
	}
	const AKZCharacter* Character = Cast<AKZCharacter>(ActorInfo->AvatarActor.Get());
	if (!Character || !Character->GetLocomotionComponent() || !ActorInfo->GetAnimInstance() ||
		!Character->GetCharacterMovement()->IsMovingOnGround() ||
		GuardMontage->GetSectionIndex(KZGuard::Start) == INDEX_NONE || GuardMontage->GetSectionIndex(KZGuard::End) == INDEX_NONE)
	{
		return false;
	}
	for (FName Section : KZGuard::SuccessSections)
	{
		if (GuardMontage->GetSectionIndex(Section) == INDEX_NONE)
		{
			return false;
		}
	}
	return true;
}

void UKZGuardAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
	// Guard BP의 activation Cost/Cooldown은 비어 있다. 성공 피격 비용만 TryGuardHit에서 적용한다.
	if (!CommitAbility(Handle, ActorInfo, ActivationInfo))
	{
		FinishAbility(true);
		return;
	}
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo());
	BoundAnimInstance = ActorInfo->GetAnimInstance();
	GuardStateHandle = ASC->ApplyGameplayEffectToSelf(GuardStateEffect->GetDefaultObject<UGameplayEffect>(),
		GetAbilityLevel(), ASC->MakeEffectContext());
	if (!IsActive())
	{
		ReleaseGuardState(); // GE callback이 activation을 끝냈어도 방금 반환된 handle을 남기지 않는다.
		BoundAnimInstance.Reset();
		return;
	}
	if (!GuardStateHandle.IsValid() || !BoundAnimInstance.IsValid())
	{
		FinishAbility(true);
		return;
	}
	FKZMovementConstraint Constraint;
	Constraint.MaxAllowedGait = EKZGait::Walk;
	Constraint.DebugName = TEXT("Guard");
	GuardMovementHandle = Character->GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
	if (!IsActive())
	{
		ReleaseGuardState();
		return;
	}
	BoundAnimInstance->OnPlayMontageNotifyBegin.AddUniqueDynamic(this, &ThisClass::HandleMontageNotify);

	UAbilityTask_WaitGameplayEvent* MoveTask = UAbilityTask_WaitGameplayEvent::WaitGameplayEvent(
		this, KZGameplayTags::Input_Action_Move, nullptr, false, true);
	if (!MoveTask || !GuardMovementHandle.IsValid())
	{
		FinishAbility(true);
		return;
	}
	MoveTask->EventReceived.AddDynamic(this, &ThisClass::HandleMoveInput);
	MoveTask->ReadyForActivation();
	ParryWindowEndsAt = GetWorld()->GetTimeSeconds() + FMath::Max(ParryWindowSeconds, 0.f);
	PlaySection(KZGuard::Start);
}

bool UKZGuardAbility::IsGuardInputHeld() const
{
	const UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	const FGameplayAbilitySpec* Spec = ASC ? ASC->FindAbilitySpecFromHandle(GetCurrentAbilitySpecHandle()) : nullptr;
	return Spec && Spec->InputPressed;
}

void UKZGuardAbility::InputReleased(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo)
{
	// 물리 Release 즉시 방어/Walk 제약을 해제한다. 정지 상태의 InputEnd 전이면 End를 예약한다.
	ReleaseGuardState();
	HandleMoveInput(FGameplayEventData()); // 이동 입력이 남아 있으면 InputEnd/End를 기다리지 않고 복귀한다.
	if (IsActive() && (HasInputEnded() || !ActiveMontageTask))
	{
		PlaySection(KZGuard::End);
	}
}

bool UKZGuardAbility::TryGuardHit(float StaminaDamage, AActor* Attacker, bool* OutParried)
{
	if (OutParried) *OutParried = false;
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	if (!IsActive() || !GuardStateHandle.IsValid() || !IsGuardInputHeld() || !ASC ||
		!ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding) || !ASC->GetActiveGameplayEffect(GuardStateHandle) ||
		!FMath::IsFinite(StaminaDamage) || StaminaDamage < 0.f || !ASC->GetSet<UKZAttributeSet>() ||
		ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)
	{
		return false;
	}
	AKZCharacter* Defender = Cast<AKZCharacter>(GetAvatarActorFromActorInfo());
	if (!Defender) return false;
	const FVector ToAttacker = IsValid(Attacker) ? (Attacker->GetActorLocation() - Defender->GetActorLocation()).GetSafeNormal2D() : FVector::ZeroVector;
	// Preserve the existing frontal half-space policy for melee, and apply it to
	// skill objects too. A source-less native Guard call cannot produce a parry.
	if (IsValid(Attacker) && (ToAttacker.IsNearlyZero() || FVector::DotProduct(Defender->GetActorForwardVector().GetSafeNormal2D(), ToAttacker) < 0.f)) return false;
	const FName ParrySection = FVector::DotProduct(Defender->GetActorRightVector(), ToAttacker) < 0.f ? KZGuard::ParryLeft : KZGuard::ParryRight;
	const bool bParried = IsValid(Attacker) && ParryWindowSeconds > 0.f &&
		GetWorld()->GetTimeSeconds() < ParryWindowEndsAt && GuardMontage->GetSectionIndex(ParrySection) != INDEX_NONE;
	const float CostMagnitude = StaminaDamage * (bParried ? FMath::Clamp(ParryStaminaDamageScale, 0.f, 1.f) : 1.f);
	if ((!bParried && StaminaDamage <= 0.f) || !FMath::IsFinite(CostMagnitude) ||
		ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) < CostMagnitude) return false;
	FGameplayEffectSpecHandle Cost = MakeOutgoingGameplayEffectSpec(GuardHitStaminaEffect);
	if (!Cost.IsValid())
	{
		return false;
	}
	Cost.Data->SetSetByCallerMagnitude(KZGuard::StaminaDamage, -CostMagnitude);
	Cost.Data->GetContext().AddSourceObject(Attacker);
	if (!ApplyGameplayEffectSpecToOwner(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(),
		GetCurrentActivationInfo(), Cost).WasSuccessfullyApplied())
	{
		return false;
	}
	// Publish the accepted result before any presentation/attacker callbacks.
	// Existing producers consume their HitGroup before calling this owner.
	if (OutParried) *OutParried = bParried;

	if (IsActive())
	{
		FGameplayEffectSpecHandle Delay = MakeOutgoingGameplayEffectSpec(GuardHitRecoveryDelayEffect);
		if (Delay.IsValid())
		{
			Delay.Data->SetDuration(GuardStaminaRecoveryDelay, true);
			ApplyGameplayEffectSpecToOwner(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(), GetCurrentActivationInfo(), Delay);
		}
		if (IsActive()) PlaySection(bParried ? ParrySection : KZGuard::SuccessSections[FMath::RandHelper(UE_ARRAY_COUNT(KZGuard::SuccessSections))]);
	}
	if (bParried && IsValid(Defender))
	{
		if (GetWorld()->GetNetMode() != NM_DedicatedServer)
		{
			USkeletalMeshComponent* Mesh = Defender->GetMesh();
			const FVector Location = Mesh && Mesh->DoesSocketExist(ParryEffectSocket) ? Mesh->GetSocketLocation(ParryEffectSocket) : Defender->GetActorLocation();
			if (ParryImpactEffect)
			{
				UParticleSystemComponent* Effect = Mesh && Mesh->DoesSocketExist(ParryEffectSocket)
					? UGameplayStatics::SpawnEmitterAttached(ParryImpactEffect, Mesh, ParryEffectSocket, Location,
						Defender->GetActorRotation(), FVector::OneVector, EAttachLocation::KeepWorldPosition, true)
					: UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), ParryImpactEffect, Location,
						Defender->GetActorRotation(), FVector::OneVector, true);
				if (Effect)
				{
					Effect->ComponentTags.Add(TEXT("KZParryImpact"));
					// Follow the newly evaluated weapon pose for the source .06s. Keep
					// rotation/scale absolute, then let this finite approved flash drain.
					Effect->SetAbsolute(false, true, true);
					Effect->SetWorldRotation(Defender->GetActorRotation());
					Effect->SetWorldScale3D(FVector::OneVector);
					if (ParryEffectDetachSeconds > 0.f)
					{
						FTimerHandle DetachTimer;
						GetWorld()->GetTimerManager().SetTimer(DetachTimer,
							FTimerDelegate::CreateWeakLambda(Effect, [Effect]()
							{ Effect->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform); }),
							ParryEffectDetachSeconds, false);
					}
					else Effect->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
				}
			}
			if (ParrySound) UGameplayStatics::SpawnSoundAtLocation(Defender, ParrySound, Location);
		}
		// Already owns the configured stamina loss and pattern-specific Parried
		// branches. Do not forcibly cancel every boss attack or duplicate damage.
		if (AKZMonster* Monster = Cast<AKZMonster>(Attacker)) Monster->ReportAttackParried(Defender);
	}
	// 비용을 확정한 공격은 이미 방어됐다. 후속 montage 실패/외부 cancel 때문에 HP 피해까지 중복 적용하지 않는다.
	return true;
}

bool UKZGuardAbility::PlaySection(FName Section)
{
	if (!IsActive())
	{
		return false;
	}
	if (Section == KZGuard::Start || Section == KZGuard::End)
	{
		CurrentSection = Section;
		HandleMoveInput(FGameplayEventData());
		if (!IsActive() || CurrentSection != Section)
		{
			return IsActive(); // Start 생략은 held 수명 유지, End 생략은 Ability 종료다.
		}
	}
	// 이전 task만 정리해 늦은 Completed/Interrupted를 끊는다. 새 task가 같은 Slot의 이전 재생을 blend out한다.
	if (ActiveMontageTask)
	{
		ActiveMontageTask->EndTask();
		ActiveMontageTask = nullptr;
	}
	CurrentSection = Section;
	ActiveMontageInstanceId = INDEX_NONE;
	ResetInputEnd();
	UAbilityTask_PlayMontageAndWait* Task = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
		this, TEXT("GuardMontage"), GuardMontage, 1.f, Section, true, 1.f, 0.f, true);
	if (!Task)
	{
		FinishAbility(true);
		return false;
	}
	ActiveMontageTask = Task;
	Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);
	Task->ReadyForActivation();
	if (IsActive() && ActiveMontageTask == Task && BoundAnimInstance.IsValid())
	{
		if (const FAnimMontageInstance* Instance = BoundAnimInstance->GetActiveInstanceForMontage(GuardMontage))
		{
			ActiveMontageInstanceId = Instance->GetInstanceID();
		}
	}
	return IsActive();
}

void UKZGuardAbility::HandleMontageNotify(FName NotifyName, const FBranchingPointNotifyPayload& Payload)
{
	if (!IsActive() || Payload.SequenceAsset != GuardMontage || Payload.MontageInstanceID != ActiveMontageInstanceId ||
		NotifyName != KZGuard::InputEnd)
	{
		return;
	}
	SetInputEnded();
	if (CurrentSection != KZGuard::End && !IsGuardInputHeld())
	{
		PlaySection(KZGuard::End);
	}
	else if (CurrentSection == KZGuard::End)
	{
		HandleMoveInput(FGameplayEventData());
	}
}

void UKZGuardAbility::HandleMontageCompleted()
{
	ActiveMontageTask = nullptr;
	ActiveMontageInstanceId = INDEX_NONE;
	if (CurrentSection == KZGuard::End)
	{
		FinishAbility(false);
	}
	else if (!IsGuardInputHeld())
	{
		PlaySection(KZGuard::End);
	}
	else
	{
		CurrentSection = NAME_None;
		SetInputEnded(); // 유지 포즈/8방 이동에는 회복부가 없다. 계속 다음 Action으로 교체할 수 있다.
	}
}

void UKZGuardAbility::HandleMontageAborted()
{
	FinishAbility(true);
}

void UKZGuardAbility::HandleMoveInput(FGameplayEventData Payload)
{
	if (!IsActive() || (CurrentSection != KZGuard::Start && CurrentSection != KZGuard::End && IsGuardInputHeld()))
	{
		return;
	}
	const AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo());
	const UKZLocomotionComponent* Locomotion = Character ? Character->GetLocomotionComponent() : nullptr;
	if (!Locomotion || !Locomotion->IsMovementInputAllowed() || Locomotion->GetLocomotionIntent().InputAmount <= 0.f)
	{
		return;
	}
	const bool bContinueGuard = CurrentSection == KZGuard::Start && IsGuardInputHeld();
	if (ActiveMontageTask)
	{
		// Stop보다 먼저 task를 끝내야 Interrupted가 유지 중인 Guard까지 종료하지 않는다.
		ActiveMontageTask->EndTask();
		ActiveMontageTask = nullptr;
	}
	CurrentSection = NAME_None;
	ActiveMontageInstanceId = INDEX_NONE;
	if (UAnimInstance* Anim = BoundAnimInstance.Get(); Anim && Anim->GetActiveInstanceForMontage(GuardMontage))
	{
		Anim->RequestMontageInertialization(GuardMontage, LocomotionExitInertializationDuration, nullptr);
		Anim->Montage_Stop(0.f, GuardMontage);
	}
	if (bContinueGuard)
	{
		SetInputEnded(); // Start를 건너뛰고 기존 ABP의 GuardLocomotion을 사용한다.
	}
	else
	{
		FinishAbility(true);
	}
}

void UKZGuardAbility::ReleaseGuardState()
{
	ParryWindowEndsAt = -1.0;
	if (UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo())
	{
		ASC->RemoveActiveGameplayEffect(GuardStateHandle);
	}
	GuardStateHandle.Invalidate();
	if (const AKZCharacter* Character = Cast<AKZCharacter>(GetAvatarActorFromActorInfo()))
	{
		if (UKZLocomotionComponent* Locomotion = Character->GetLocomotionComponent())
		{
			Locomotion->ReleaseMovementConstraint(GuardMovementHandle);
		}
	}
	GuardMovementHandle.Reset();
}

void UKZGuardAbility::FinishAbility(bool bWasCancelled)
{
	if (IsActive())
	{
		EndAbility(GetCurrentAbilitySpecHandle(), GetCurrentActorInfo(), GetCurrentActivationInfo(), false, bWasCancelled);
	}
}

void UKZGuardAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
	if (UAnimInstance* Anim = BoundAnimInstance.Get())
	{
		Anim->OnPlayMontageNotifyBegin.RemoveDynamic(this, &ThisClass::HandleMontageNotify);
	}
	ReleaseGuardState();
	BoundAnimInstance.Reset();
	CurrentSection = NAME_None;
	ActiveMontageInstanceId = INDEX_NONE;
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
	ActiveMontageTask = nullptr;
}
