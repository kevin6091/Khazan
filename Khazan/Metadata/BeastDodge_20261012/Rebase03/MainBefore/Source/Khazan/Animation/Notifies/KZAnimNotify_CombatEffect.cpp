#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Environment/KZSnowDeformation.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Character/KZMonster.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

UKZAnimNotify_CombatEffect::UKZAnimNotify_CombatEffect(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	NotifyName = TEXT("KZCombatEffect");
}

FTransform UKZAnimNotify_CombatEffect::SampleSourceCorrection(const float SourceTime) const
{
	if (!bUseCorrectionCurves) return SourceCorrectionTransform;
	const auto Evaluate = [SourceTime](const FRuntimeVectorCurve& Curve, const FVector& Default)
	{
		FVector Value = Default;
		for (int32 Axis = 0; Axis < 3; ++Axis)
			if (const FRichCurve* Keys = Curve.GetRichCurveConst(Axis); Keys && Keys->GetNumKeys() > 0)
				Value[Axis] = Keys->Eval(SourceTime);
		return Value;
	};
	return FTransform(FRotator::MakeFromEuler(Evaluate(SourceCorrectionRotation, FVector::ZeroVector)),
		Evaluate(SourceCorrectionTranslation, FVector::ZeroVector),
		Evaluate(SourceCorrectionScale, FVector::OneVector));
}

USceneComponent* UKZAnimNotify_CombatEffect::SpawnComponent(
	const UKZAnimNotify_CombatEffect& Effect, USkeletalMeshComponent* Mesh,
	const bool bConfirmedHit, const float RecoveredWindowDuration, const float SourceTime)
{
	check(IsInGameThread());
	UWorld* World = IsValid(Mesh) ? Mesh->GetWorld() : nullptr;
	if (!IsValid(World) || Effect.EventId.IsNone() || World->GetNetMode() == NM_DedicatedServer ||
		(Effect.bOnAttackSuccessed && !bConfirmedHit)) return nullptr;
	// The original environment-volume implementation is unavailable. Authoring
	// explicitly opts into this winter-level adapter instead of playing all bundles.
	AKZSnowDeformation* Snow = nullptr;
	if (Effect.bWinterOnly || Effect.bSpawnOnFloor || Effect.SurfaceRoutes.Num() > 0)
	{
		for (TActorIterator<AKZSnowDeformation> It(World); It; ++It)
		{
			Snow = *It;
			break;
		}
	}
	if (Effect.bWinterOnly && !IsValid(Snow))
	{
		return nullptr;
	}

	const FName AnchorSocket = Effect.bUseSourceCorrection ? Effect.CorrectionBoneName : Effect.SourceSocket;
	if ((!Effect.SourceSocket.IsNone() && !Mesh->DoesSocketExist(Effect.SourceSocket)) ||
		(Effect.bUseSourceCorrection && (AnchorSocket.IsNone() || !Mesh->DoesSocketExist(AnchorSocket))))
	{
		return nullptr;
	}

	// Original particle geometry and offsets are already centimetres. Remove the
	// mesh/socket scale from the anchor, rather than assuming a literal .01 scale.
	FTransform AnchorWorld = Mesh->GetSocketTransform(AnchorSocket, RTS_World);
	AnchorWorld.SetScale3D(FVector::OneVector);
	const bool bMonster = Mesh->GetOwner()->IsA<AKZMonster>();
	const FVector PresentationScale = bMonster ? Mesh->GetComponentScale().GetAbs() : FVector::OneVector;
	if (bMonster && AnchorSocket.IsNone())
		AnchorWorld = FTransform(Mesh->GetOwner()->GetActorQuat(), Mesh->GetComponentLocation());
	const auto SampleRange = [](double Minimum, double Maximum)
	{
		return Minimum == Maximum ? Minimum : FMath::FRandRange(Minimum, Maximum);
	};
	const FVector RelativeLocation = Effect.RelativeLocation + FVector(
		SampleRange(Effect.RelativeLocationRandomMin.X, Effect.RelativeLocationRandomMax.X),
		SampleRange(Effect.RelativeLocationRandomMin.Y, Effect.RelativeLocationRandomMax.Y),
		SampleRange(Effect.RelativeLocationRandomMin.Z, Effect.RelativeLocationRandomMax.Z));
	const FRotator RelativeRotation = Effect.RelativeRotation + FRotator(
		SampleRange(Effect.RelativeRotationRandomMin.Pitch, Effect.RelativeRotationRandomMax.Pitch),
		SampleRange(Effect.RelativeRotationRandomMin.Yaw, Effect.RelativeRotationRandomMax.Yaw),
		SampleRange(Effect.RelativeRotationRandomMin.Roll, Effect.RelativeRotationRandomMax.Roll));
	// Source random fields are interpreted as additive axis offsets. Original
	// random-vector/rotator executable code is unavailable; authoring records this.
	FTransform LocalEffect(RelativeRotation, RelativeLocation, FVector::OneVector);
	if (Effect.bUseSourceCorrection)
	{
		if (!Effect.bAttached)
		{
			// The nine current Player rows explicitly use world/top-owner coordinates.
			// Keep this source-supported ground/model basis instead of a stale bone;
			// original correction interpolation executable code remains unavailable.
			AnchorWorld = FTransform(Mesh->GetOwner()->GetActorQuat(), Mesh->GetComponentLocation());
		}
		else
		{
			// Source local * source bone inverse * actual bone. The Action owner
			// finalizes its first attached snapshot after this frame's pose evaluation.
			LocalEffect = LocalEffect * Effect.SampleSourceCorrection(SourceTime).Inverse();
		}
	}
	// Monster model-space offsets/geometry follow the live body's authored scale,
	// independently of a socket's bone scale. Player's existing centimetre adapter is unchanged.
	LocalEffect.SetTranslation(LocalEffect.GetTranslation() * PresentationScale);
	FTransform EffectWorld = LocalEffect * AnchorWorld;
	EffectWorld.SetScale3D(Effect.Scale3D * PresentationScale);

	EPhysicalSurface Surface = SurfaceType_Default;
	ACharacter* Character = Cast<ACharacter>(Mesh->GetOwner());
	UCharacterMovementComponent* Movement = IsValid(Character) ? Character->GetCharacterMovement() : nullptr;
	UCapsuleComponent* Capsule = IsValid(Character) ? Character->GetCapsuleComponent() : nullptr;
	UPhysicalMaterial* PhysicalMaterial = nullptr;
	FHitResult FloorHit;
	if (Effect.bSpawnOnFloor && (!IsValid(Movement) || !Movement->IsMovingOnGround()))
	{
		return nullptr;
	}
	if ((Effect.bSpawnOnFloor || Effect.SurfaceRoutes.Num() > 0) &&
		IsValid(Capsule) && IsValid(Movement))
	{
		// Keep the authored XY. Only the existing capsule/CMC floor range is used;
		// no arbitrary projection distance allows a midair effect to reach terrain.
		FVector TraceStart = EffectWorld.GetLocation();
		TraceStart.Z = Character->GetActorLocation().Z;
		double SnowRayBudget = 0.;
		if (IsValid(Snow))
		{
			for (const FKZSnowSurfaceSamples& Profile : Snow->SurfaceContactSamples)
			{
				SnowRayBudget = FMath::Max(SnowRayBudget, double(Profile.DepthReferenceCm) + Profile.RimHeightCm);
			}
		}
		const FVector TraceEnd = TraceStart - FVector::UpVector *
			(Capsule->GetScaledCapsuleHalfHeight() + Movement->MaxStepHeight + SnowRayBudget);
		FCollisionQueryParams Query(SCENE_QUERY_STAT(KZCombatEffectFloor), true, Character);
		Query.bReturnPhysicalMaterial = true;
		if (World->LineTraceSingleByChannel(FloorHit, TraceStart, TraceEnd, ECC_Visibility, Query))
		{
			PhysicalMaterial = FloorHit.PhysMaterial.Get();
		}
	}
	if (IsValid(PhysicalMaterial))
	{
		Surface = PhysicalMaterial->SurfaceType;
	}
	double SnowHeight = 0.;
	if (IsValid(Snow) && FloorHit.GetComponent() &&
		FloorHit.GetComponent()->ComponentHasTag(Snow->SurfaceTag) &&
		Snow->GetSnowSurfaceHeight(FloorHit, SnowHeight) && SnowHeight > 0.)
	{
		// Original WLM_HeinMach2 / PM_DeepSnow SurfaceType is 13. Mapping this
		// project's aggregate snow sample to deep snow is an explicit adapter;
		// no separate deep/thin weight profile is currently available.
		Surface = SurfaceType13;
	}
	else
	{
		SnowHeight = 0.;
	}
	if (Effect.bSpawnOnFloor)
	{
		if (!FloorHit.bBlockingHit || !Movement->IsWalkable(FloorHit))
		{
			return nullptr;
		}
		// Preserve authored rotation (including pitch); do not align it to terrain.
		FVector FloorLocation = FloorHit.ImpactPoint;
		// The existing sampler reports plane-normal centimetres. Preserve the
		// authored XY while lifting to that local plane, including current dents.
		if (FloorHit.ImpactNormal.Z > UE_DOUBLE_SMALL_NUMBER)
		{
			FloorLocation.Z += SnowHeight / FloorHit.ImpactNormal.Z;
		}
		EffectWorld.SetLocation(FloorLocation);
		if (Effect.bAbsoluteRotation)
		{
			// Opted-in impact bursts keep the actual weapon-tip XY, but spread
			// along this floor instead of inheriting the downward blade rotation.
			const FVector Forward = FVector::VectorPlaneProject(Character->GetActorForwardVector(), FloorHit.ImpactNormal).GetSafeNormal();
			EffectWorld.SetRotation(FRotationMatrix::MakeFromXZ(Forward, FloorHit.ImpactNormal).ToQuat() * Effect.RelativeRotation.Quaternion());
		}
	}
	if (Effect.bOverrideSurface)
	{
		Surface = Effect.SurfaceOverride;
	}
	UParticleSystem* ParticleTemplate = Effect.ParticleTemplate;
	UMaterialInterface* SelectedDecalMaterial = Effect.DecalMaterial;
	const FKZCombatEffectSurfaceRoute* SurfaceRoute = nullptr;
	for (const FKZCombatEffectSurfaceRoute& Route : Effect.SurfaceRoutes)
	{
		if (Route.Surface == Surface)
		{
			SurfaceRoute = &Route;
			if (Route.bSuppressParticle || IsValid(Route.ParticleTemplate))
			{
				ParticleTemplate = Route.ParticleTemplate;
			}
			if (Route.bSuppressDecal || IsValid(Route.DecalMaterial))
				SelectedDecalMaterial = Route.DecalMaterial;
			break;
		}
	}
	const bool bTrail = IsValid(Effect.TrailMesh);
	const bool bDecal = !bTrail && IsValid(SelectedDecalMaterial);
	const bool bNiagara = !bTrail && !bDecal && IsValid(Effect.NiagaraTemplate);
	if (!bDecal && !bTrail && !bNiagara && !IsValid(ParticleTemplate))
	{
		return nullptr;
	}
	if (!bDecal && !bTrail && RecoveredWindowDuration > 0.f && !Effect.bDestroyOnNotifyEnd &&
		(bNiagara ? Effect.NiagaraTemplate->IsLooping() : ParticleTemplate->IsLooping()))
	{
		// Its source End has passed and provides no kill policy. Replay finite
		// one-shots, but do not create an unbounded late continuous emitter.
		return nullptr;
	}

	USceneComponent* Component = nullptr;
	UParticleSystemComponent* Particle = nullptr;
	UDecalComponent* Decal = nullptr;
	if (bTrail)
	{
		UStaticMeshComponent* Trail = NewObject<UStaticMeshComponent>(Mesh->GetOwner());
		Trail->SetStaticMesh(Effect.TrailMesh);
		Trail->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Trail->SetCanEverAffectNavigation(false);
		// The recovered SurfaceTrailMesh/M_WriteSnowField is terrain-writer
		// geometry, not a visible white VFX sphere. Its original render-target
		// consumer is unrecovered; retain its source transform/lifetime without
		// drawing it into the scene. This is a project rendering adapter.
		Trail->SetRenderInMainPass(false);
		Trail->SetRenderInDepthPass(false);
		Trail->SetCastShadow(false);
		if (Effect.bAttached && !Effect.bOnlyStartAttach)
			Trail->SetupAttachment(Mesh, Effect.SourceSocket);
		Trail->RegisterComponentWithWorld(World);
		if (Effect.TrailMaterial) Trail->SetMaterial(0, Effect.TrailMaterial);
		for (int32 Slot = 0; Slot < Trail->GetNumMaterials(); ++Slot)
		{
			if (UMaterialInstanceDynamic* MID = Trail->CreateDynamicMaterialInstance(Slot))
				if (!Effect.TrailIntensityParameter.IsNone())
					MID->SetScalarParameterValue(Effect.TrailIntensityParameter, Effect.TrailIntensity);
		}
		Component = Trail;
	}
	else if (bDecal)
	{
		const FVector SignedSize = Effect.DecalSize + FVector(
			SampleRange(Effect.DecalSizeRandomMin.X, Effect.DecalSizeRandomMax.X),
			SampleRange(Effect.DecalSizeRandomMin.Y, Effect.DecalSizeRandomMax.Y),
			SampleRange(Effect.DecalSizeRandomMin.Z, Effect.DecalSizeRandomMax.Z));
		const FVector Size = SignedSize.GetAbs();
		if (SignedSize.ContainsNaN() || Size.GetMin() <= 0. ||
			!FMath::IsFinite(Effect.DecalLifeSpan) || Effect.DecalLifeSpan < 0.f)
		{
			return nullptr;
		}
		// Use a positive projection volume; preserve source signed dimensions as
		// transform mirroring. Original half/full-size conventions are unverified.
		EffectWorld.SetScale3D(Effect.Scale3D * PresentationScale * SignedSize.GetSignVector());
#if WITH_EDITOR
		// Finish the selected authored parent before its first editor projection.
		// Cooked builds use packaged shaders and do not perform this wait.
		SelectedDecalMaterial->EnsureIsComplete();
#endif
		if (Effect.bAttached && !Effect.bOnlyStartAttach)
		{
			const FTransform AttachmentWorld = Mesh->GetSocketTransform(Effect.SourceSocket, RTS_World);
			const FTransform AttachmentLocal = EffectWorld.GetRelativeTransform(AttachmentWorld);
			Decal = UGameplayStatics::SpawnDecalAttached(SelectedDecalMaterial, Size, Mesh, Effect.SourceSocket,
				AttachmentLocal.GetLocation(), AttachmentLocal.Rotator(), EAttachLocation::KeepRelativeOffset,
				Effect.DecalLifeSpan);
		}
		else
		{
			Decal = UGameplayStatics::SpawnDecalAtLocation(World, SelectedDecalMaterial, Size,
				EffectWorld.GetLocation(), EffectWorld.Rotator(), Effect.DecalLifeSpan);
		}
		Component = Decal;
	}
	else if (bNiagara)
	{
		// The existing execution owner installs its receipt before activation.
		if (Effect.bAttached && !Effect.bOnlyStartAttach)
		{
			const FTransform AttachmentWorld = Mesh->GetSocketTransform(Effect.SourceSocket, RTS_World);
			const FTransform AttachmentLocal = EffectWorld.GetRelativeTransform(AttachmentWorld);
			Component = UNiagaraFunctionLibrary::SpawnSystemAttached(Effect.NiagaraTemplate, Mesh, Effect.SourceSocket,
				AttachmentLocal.GetLocation(), AttachmentLocal.Rotator(), EffectWorld.GetScale3D(),
				EAttachLocation::KeepRelativeOffset, true, ENCPoolMethod::None, false, false);
		}
		else
		{
			Component = UNiagaraFunctionLibrary::SpawnSystemAtLocation(World, Effect.NiagaraTemplate,
				EffectWorld.GetLocation(), EffectWorld.Rotator(), EffectWorld.GetScale3D(),
				true, false, ENCPoolMethod::None, false);
		}
	}
	else if (Effect.bAttached && !Effect.bOnlyStartAttach)
	{
		// Convert centimetre world offsets through the actual attachment transform.
		// Its scale can vary with parts/weapon setup and is not an authored FX scale.
		const FTransform AttachmentWorld = Mesh->GetSocketTransform(Effect.SourceSocket, RTS_World);
		const FTransform AttachmentLocal = EffectWorld.GetRelativeTransform(AttachmentWorld);
		Particle = UGameplayStatics::SpawnEmitterAttached(ParticleTemplate, Mesh, Effect.SourceSocket,
			AttachmentLocal.GetLocation(), AttachmentLocal.Rotator(), Effect.Scale3D,
			EAttachLocation::KeepRelativeOffset, true, EPSCPoolMethod::None, false);
		Component = Particle;
	}
	else
	{
		Particle = UGameplayStatics::SpawnEmitterAtLocation(World, ParticleTemplate, EffectWorld,
			true, EPSCPoolMethod::None, false);
		Component = Particle;
	}
	if (!IsValid(Component))
	{
		return nullptr;
	}

	Component->SetAbsolute(false, Effect.bAbsoluteRotation, true);
	Component->SetWorldTransform(EffectWorld);
	Component->ComponentTags.AddUnique(FName(TEXT("KZCombatEffect")));
	Component->ComponentTags.AddUnique(Effect.EventId);
	if (IsValid(Particle))
	{
		Particle->SetTranslucentSortPriority(Effect.TranslucencySortPriority);
		Particle->CustomTimeDilation = Effect.CustomTimeDilation;
	}
	if (UNiagaraComponent* Niagara = Cast<UNiagaraComponent>(Component))
	{
		Niagara->SetTranslucentSortPriority(Effect.TranslucencySortPriority);
		Niagara->SetCustomTimeDilation(Effect.CustomTimeDilation);
		if (Effect.bSpawnOnFloor)
		{
			// Local-space sprite normals follow the traced floor, including slopes.
			Niagara->SetVariableVec3(TEXT("User.KZFloorNormal"),
				EffectWorld.GetRotation().UnrotateVector(FloorHit.ImpactNormal));
		}
	}
	UMaterialInstanceDynamic* DecalMaterial = IsValid(Decal) ? Decal->CreateDynamicMaterialInstance() : nullptr;
	// Global source parameters and surface-specific parameters stay separate.
	// Only the selected surface's parameters are consumed.
	const auto ApplyParameters = [Particle, DecalMaterial, &SampleRange](
		const TArray<FKZCombatEffectFloatParameter>& Parameters)
	{
		for (const FKZCombatEffectFloatParameter& Parameter : Parameters)
		{
			if (!Parameter.ParameterName.IsNone())
			{
				if (IsValid(DecalMaterial))
				{
					const float Value = Parameter.bRandomInteger
						? float(FMath::RandRange(FMath::Min(int32(Parameter.Minimum), int32(Parameter.Maximum)),
							FMath::Max(int32(Parameter.Minimum), int32(Parameter.Maximum))))
						: float(SampleRange(Parameter.Minimum, Parameter.Maximum));
					DecalMaterial->SetScalarParameterValue(Parameter.ParameterName, Value);
				}
				else if (IsValid(Particle) && Parameter.Minimum == Parameter.Maximum)
				{
					Particle->SetFloatParameter(Parameter.ParameterName, Parameter.Maximum);
				}
				else if (IsValid(Particle))
				{
					Particle->SetFloatRandParameter(Parameter.ParameterName, Parameter.Maximum, Parameter.Minimum);
				}
			}
		}
	};
	ApplyParameters(Effect.InstanceParameters);
	if (SurfaceRoute != nullptr)
	{
		ApplyParameters(SurfaceRoute->FloatParameters);
	}
	if (IsValid(DecalMaterial))
	{
		// Material evaluates recovered source curve keys on GPU; the decal's
		// engine lifespan owns destruction. No Ability tick/timer ages the decal.
		DecalMaterial->SetScalarParameterValue(FName(TEXT("KZDecalSpawnTime")), World->GetTimeSeconds());
		DecalMaterial->SetScalarParameterValue(FName(TEXT("KZDecalTimeScale")), Effect.CustomTimeDilation);
		DecalMaterial->SetScalarParameterValue(FName(TEXT("KZDecalLifeSpan")), Effect.DecalLifeSpan);
		DecalMaterial->SetScalarParameterValue(FName(TEXT("KZDecalCurveIndex")), float(Effect.DecalOpacityCurveIndex));
	}

	return Component;
}
