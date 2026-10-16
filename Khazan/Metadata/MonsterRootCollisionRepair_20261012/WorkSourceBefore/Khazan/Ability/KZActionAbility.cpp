#include "Ability/KZActionAbility.h"

#include "KZGameplayTags.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "LogChannels.h"


UKZActionAbility::UKZActionAbility()
{
	// 실행 상태를 멤버로 보관하기 위해 캐릭터마다 인스턴스 하나를 사용한다.
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalOnly;

	// InputEnd 전에는 다른 Action을 막는다.
	BlockAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);

	// 새 Action이 성공적으로 시작되면 이전 Action을 취소한다.
	CancelAbilitiesWithTag.AddTag(KZGameplayTags::Ability_Action);
	ActivationBlockedTags.AddTag(KZGameplayTags::State_Exhausted);
	ActivationBlockedTags.AddTag(KZGameplayTags::State_Dead);
}

void UKZActionAbility::ResetInputEnd()
{
	bInputEnded = false;

	if (IsActive())
	{
		SetShouldBlockOtherAbilities(true);
	}
}

void UKZActionAbility::SetInputEnded()
{
	if (!IsActive() || bInputEnded)
	{
		return;
	}

	bInputEnded = true;
	SetShouldBlockOtherAbilities(false);
}

void UKZActionAbility::EndAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const bool bReplicateEndAbility,
	const bool bWasCancelled)
{
	ClearCombatEffects(!bWasCancelled);
	bInputEnded = false;
	
	if (OnEndAbilityGameplayEffect)
	{
		FGameplayEffectSpecHandle SpecHandle = MakeOutgoingGameplayEffectSpec(OnEndAbilityGameplayEffect);
		if (SpecHandle.IsValid())
		{
			(void) ApplyGameplayEffectSpecToOwner(Handle, ActorInfo, ActivationInfo, SpecHandle);
		}
	}	
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}


void UKZActionAbility::FActiveCombatEffect::UnregisterInitialPose()
{
	const FDelegateHandle PreviousHandle = InitialPoseHandle;
	InitialPoseHandle.Reset();
	if (USkeletalMeshComponent* Mesh = InitialPoseMesh.Get(); PreviousHandle.IsValid() && Mesh)
	{
		Mesh->UnregisterOnBoneTransformsFinalizedDelegate(PreviousHandle);
	}
	InitialPoseMesh.Reset();
}

void UKZActionAbility::StartCombatEffect(
	const UKZAnimNotify_CombatEffect& Effect, const FBranchingPointNotifyPayload& Payload,
	const bool bConfirmedHit, const float RecoveredWindowDuration)
{
	check(IsInGameThread());
	USkeletalMeshComponent* Mesh = Payload.SkelMeshComponent;
	UWorld* World = IsValid(Mesh) ? Mesh->GetWorld() : nullptr;
	if (!IsValid(World) || Effect.EventId.IsNone() ||
		World->GetNetMode() == NM_DedicatedServer)
	{
		return;
	}
	// Execution owners validate their montage/instance before calling this shared
	// presenter. Conditional source effects require an explicit accepted hit.
	const FGameplayAbilityActorInfo* EffectActorInfo = GetCurrentActorInfo();
	if (!IsActive() || !EffectActorInfo ||
		EffectActorInfo->AvatarActor.Get() != Mesh->GetOwner() ||
		EffectActorInfo->SkeletalMeshComponent.Get() != Mesh ||
		(Effect.bOnAttackSuccessed && !bConfirmedHit))
	{
		return;
	}

	ActiveCombatEffects.RemoveAll([](FActiveCombatEffect& Record)
	{
		if (Record.Component.IsValid()) return false;
		Record.UnregisterInitialPose();
		return true;
	});
	if (!bConfirmedHit && ActiveCombatEffects.ContainsByPredicate([&Effect, &Payload](const FActiveCombatEffect& Record)
	{
		return !Record.bNotifyEnded && Record.EventId == Effect.EventId &&
			Record.MontageInstanceId == Payload.MontageInstanceID;
	}))
	{
		return;
	}
	USceneComponent* Component = UKZAnimNotify_CombatEffect::SpawnComponent(
		Effect, Mesh, bConfirmedHit, RecoveredWindowDuration);
	if (!IsValid(Component)) return;
	UParticleSystemComponent* Particle = Cast<UParticleSystemComponent>(Component);

	FActiveCombatEffect& Record = ActiveCombatEffects.AddDefaulted_GetRef();
	Record.Component = Component;
	Record.EventId = Effect.EventId;
	Record.MontageInstanceId = Payload.MontageInstanceID;
	Record.bDestroyOnNotifyEnd = Effect.bDestroyOnNotifyEnd;
	Record.bDestroyOnNotifyEndDeactived = Effect.bDestroyOnNotifyEndDeactived;
	Record.bDestroyOnAnimEnd = Effect.bDestroyOnAnimEnd;
	Record.OnNotifyEndDeattach = Effect.OnNotifyEndDeattach;
	Record.bRecoveredAfterSourceEnd = RecoveredWindowDuration > 0.f;
	if (IsValid(Particle) && Effect.bUseSourceCorrection && Effect.bAttached &&
		!Effect.bOnlyStartAttach && !Effect.bSpawnOnFloor)
	{
		const FName AnchorSocket = Effect.CorrectionBoneName;
		FTransform InitialAnchor = Mesh->GetSocketTransform(AnchorSocket, RTS_World);
		InitialAnchor.SetScale3D(FVector::OneVector);
		// The shared factory already sampled source random offsets/correction.
		// Recover that same local snapshot rather than sampling a second time.
		FTransform LocalEffect = Component->GetComponentTransform().GetRelativeTransform(InitialAnchor);
		LocalEffect.SetScale3D(FVector::OneVector);
		// Branching notifies run before pose evaluation. Correct the first attached
		// snapshot once after FinalizeBoneTransform, using the same sampled offsets.
		const TWeakObjectPtr<UKZActionAbility> WeakAbility(this);
		const TWeakObjectPtr<USceneComponent> WeakComponent(Component);
		const TWeakObjectPtr<USkeletalMeshComponent> WeakMesh(Mesh);
		Record.InitialPoseMesh = Mesh;
		Record.InitialPoseHandle = Mesh->RegisterOnBoneTransformsFinalizedDelegate(
			FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateWeakLambda(this,
				[WeakAbility, WeakComponent, WeakMesh, LocalEffect, AnchorSocket,
					AttachSocket = Effect.SourceSocket, SourceScale = Effect.Scale3D]()
				{
					UKZActionAbility* Ability = WeakAbility.Get();
					if (!Ability) return;
					FActiveCombatEffect* Pending = Ability->ActiveCombatEffects.FindByPredicate(
						[WeakComponent](const FActiveCombatEffect& Active) { return Active.Component == WeakComponent; });
					if (!Pending) return;
					Pending->UnregisterInitialPose(); // One-shot, also when any validation below fails.
					USkeletalMeshComponent* PoseMesh = WeakMesh.Get();
					USceneComponent* PendingComponent = WeakComponent.Get();
					const FGameplayAbilityActorInfo* FinalPoseActorInfo = Ability->GetCurrentActorInfo();
					if (!Ability->IsActive() || !IsValid(PoseMesh) || !IsValid(PendingComponent) ||
						!PoseMesh->IsRegistered() || !PendingComponent->IsRegistered() ||
						!FinalPoseActorInfo || FinalPoseActorInfo->AvatarActor.Get() != PoseMesh->GetOwner() ||
						FinalPoseActorInfo->SkeletalMeshComponent.Get() != PoseMesh ||
						PendingComponent->GetAttachParent() != PoseMesh ||
						PendingComponent->GetAttachSocketName() != AttachSocket || !PoseMesh->DoesSocketExist(AnchorSocket))
					{
						return;
					}
					FTransform FinalAnchor = PoseMesh->GetSocketTransform(AnchorSocket, RTS_World);
					FinalAnchor.SetScale3D(FVector::OneVector);
					FTransform FinalWorld = LocalEffect * FinalAnchor;
					FinalWorld.SetScale3D(SourceScale);
					PendingComponent->SetWorldTransform(FinalWorld);
				}));
	}
	if (IsValid(Particle) && Effect.bDestroyOnNotifyEnd && RecoveredWindowDuration > 0.f)
	{
		// Slow-frame adapter: a recovered hit arrives after the source End marker.
		// Give its loop only the authored window duration to emit, then use the
		// source End policy. This is not an eligibility grace or original-code proof.
		const TWeakObjectPtr<UKZActionAbility> WeakAbility(this);
		const TWeakObjectPtr<USceneComponent> WeakComponent(Component);
		const bool bDeactivate = Effect.bDestroyOnNotifyEndDeactived;
		const bool bDetach = Effect.OnNotifyEndDeattach;
		FTimerDelegate EndDelegate = FTimerDelegate::CreateWeakLambda(Component,
			[WeakAbility, WeakComponent, bDeactivate, bDetach]()
			{
				if (UKZActionAbility* Ability = WeakAbility.Get())
				{
					Ability->ActiveCombatEffects.RemoveAll([WeakComponent](FActiveCombatEffect& Active)
					{
						if (Active.Component != WeakComponent) return false;
						Active.UnregisterInitialPose();
						return true;
					});
				}
				if (UParticleSystemComponent* Recovered = Cast<UParticleSystemComponent>(WeakComponent.Get()))
				{
					if (bDetach) Recovered->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
					if (bDeactivate) Recovered->DeactivateSystem();
					else Recovered->DestroyComponent();
				}
			});
		World->GetTimerManager().SetTimer(Record.RecoveredEndTimer, EndDelegate, RecoveredWindowDuration, false);
	}
	const UObject* Resource = Particle ? static_cast<UObject*>(Particle->Template) : static_cast<UObject*>(Effect.DecalMaterial.Get());
	UE_LOG(LogAbility, Verbose, TEXT("CombatEffect Spawn Event=%s MontageInstance=%d Template=%s Time=%f"),
		*Effect.EventId.ToString(), Payload.MontageInstanceID, *GetNameSafe(Resource), World->GetTimeSeconds());
	if (IsValid(Particle))
	{
		Particle->ActivateSystem(true);
	}
}


void UKZActionAbility::StopCombatEffect(const FName EventId, const int32 MontageInstanceId)
{
	check(IsInGameThread());
	TArray<FActiveCombatEffect> EndingEffects;
	for (int32 Index = ActiveCombatEffects.Num() - 1; Index >= 0; --Index)
	{
		FActiveCombatEffect& Record = ActiveCombatEffects[Index];
		if (Record.EventId != EventId || Record.MontageInstanceId != MontageInstanceId || Record.bNotifyEnded)
		{
			continue;
		}
		Record.UnregisterInitialPose();
		if (!Record.bDestroyOnNotifyEnd)
		{
			Record.bNotifyEnded = true;
			if (Record.OnNotifyEndDeattach)
			{
				EndingEffects.Add(Record);
			}
			continue; // Source policy allows natural completion after the stop marker.
		}
		EndingEffects.Add(Record);
		ActiveCombatEffects.RemoveAt(Index);
	}
	// The paired stop closes the window and every resource spawned from it.
	// Array mutation is complete before a component callback can re-enter us.
	for (const FActiveCombatEffect& Record : EndingEffects)
	{
		USceneComponent* Component = Record.Component.Get();
		if (IsValid(Component))
		{
			if (UWorld* EffectWorld = Component->GetWorld())
			{
				FTimerHandle Timer = Record.RecoveredEndTimer;
				EffectWorld->GetTimerManager().ClearTimer(Timer);
			}
			if (Record.OnNotifyEndDeattach)
			{
				Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
			}
			if (!Record.bDestroyOnNotifyEnd)
			{
				continue;
			}
			UParticleSystemComponent* Particle = Cast<UParticleSystemComponent>(Component);
			if (Record.bDestroyOnNotifyEndDeactived && IsValid(Particle))
			{
				Particle->DeactivateSystem();
			}
			else
			{
				Component->DestroyComponent();
			}
		}
	}
}


void UKZActionAbility::ClearCombatEffects(const bool bNaturalCompletion)
{
	check(IsInGameThread());
	// Detach ownership before component callbacks. Repeated cleanup is harmless.
	for (FActiveCombatEffect& Record : ActiveCombatEffects)
	{
		Record.UnregisterInitialPose();
	}
	TArray<FActiveCombatEffect> PreviousEffects = MoveTemp(ActiveCombatEffects);
	ActiveCombatEffects.Reset();
	for (const FActiveCombatEffect& Record : PreviousEffects)
	{
		if (USceneComponent* Component = Record.Component.Get())
		{
			// A confirmed final hit must reach its first PSC tick. Its component-
			// bound timer owns the authored emission duration after natural finish;
			// explicit animation destruction and cancellation never transfer it.
			if (bNaturalCompletion && Record.bRecoveredAfterSourceEnd && !Record.bDestroyOnAnimEnd)
			{
				Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
				continue;
			}
			if (UWorld* EffectWorld = Component->GetWorld())
			{
				FTimerHandle Timer = Record.RecoveredEndTimer;
				EffectWorld->GetTimerManager().ClearTimer(Timer);
			}
			if (Record.OnNotifyEndDeattach)
			{
				Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
			}
			if (Record.bDestroyOnAnimEnd)
			{
				Component->DestroyComponent();
			}
			else if (UParticleSystemComponent* Particle = Cast<UParticleSystemComponent>(Component))
			{
				Particle->DeactivateSystem(); // Stop emission; finite residual particles drain.
			}
			// Decals without an explicit kill flag keep their source engine lifespan.
		}
	}
}
