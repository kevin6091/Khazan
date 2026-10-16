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
#include "Camera/PlayerCameraManager.h"
#include "Character/KZMonster.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "NiagaraDataInterfaceCurve.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "UObject/UnrealType.h"
#if WITH_EDITOR
#include "Animation/AnimMontage.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "ScopedTransaction.h"
#endif

namespace
{
void ConfigureWeaponSlashNiagara(UNiagaraComponent* Niagara)
{
	Niagara->SetVariableFloat(TEXT("User.Rotation"), 0.f);
	Niagara->SetVariableFloat(TEXT("User.ScaleLerp"), 0.f);
	for (const auto& Parameter : {TPair<FName,float>(TEXT("User.CurveRotation"),0.f), TPair<FName,float>(TEXT("User.CurveScale"),1.f)})
		if (auto* Curve = UNiagaraFunctionLibrary::GetDataInterface<UNiagaraDataInterfaceCurve>(Niagara, Parameter.Key))
		{
			if (!Curve->IsIn(Niagara))
			{
				Curve = DuplicateObject<UNiagaraDataInterfaceCurve>(Curve, Niagara);
				Niagara->GetOverrideParameters().SetDataInterface(Curve,
					FNiagaraVariable(FNiagaraTypeDefinition(UNiagaraDataInterfaceCurve::StaticClass()), Parameter.Key));
			}
			Curve->Curve.Reset(); Curve->Curve.AddKey(0.f,Parameter.Value); Curve->Curve.AddKey(1.f,Parameter.Value);
			// Both overrides are constant. UpdateLUT is editor-only; the engine's
			// one-sample LUT represents the same constants in cooked CPU/GPU effects.
			Curve->UpdateTimeRanges();
			Curve->SetDefaultLUT();
			if (const FArrayProperty* LUT = FindFProperty<FArrayProperty>(Curve->GetClass(), TEXT("ShaderLUT")))
			{
				for (float& Value : *LUT->ContainerPtrToValuePtr<TArray<float>>(Curve)) Value = Parameter.Value;
				Curve->MarkRenderDataDirty();
			}
		}
}
}

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

FTransform UKZAnimNotify_CombatEffect::SampleSequencerTransform(const float MontageTime) const
{
	const auto Evaluate = [MontageTime](const FRuntimeVectorCurve& Curve, const FVector& Default)
	{
		FVector Value = Default;
		for (int32 Axis = 0; Axis < 3; ++Axis)
			if (const FRichCurve* Keys = Curve.GetRichCurveConst(Axis); Keys && Keys->GetNumKeys() > 0)
				Value[Axis] = Keys->Eval(MontageTime);
		return Value;
	};
	return FTransform(FRotator::MakeFromEuler(Evaluate(SequencerRotation, FVector::ZeroVector)),
		Evaluate(SequencerTranslation, FVector::ZeroVector), Evaluate(SequencerScale, FVector::OneVector));
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

	const FName AnchorSocket = Effect.bUseSequencerTransform ? NAME_None : Effect.bUseSourceCorrection ? Effect.CorrectionBoneName : Effect.SourceSocket;
	if (!Effect.bUseSequencerTransform && ((!Effect.SourceSocket.IsNone() && !Mesh->DoesSocketExist(Effect.SourceSocket)) ||
		(Effect.bUseSourceCorrection && (AnchorSocket.IsNone() || !Mesh->DoesSocketExist(AnchorSocket))))
	)
	{
		return nullptr;
	}

	// Original particle geometry and offsets are already centimetres. Remove the
	// mesh/socket scale from the anchor, rather than assuming a literal .01 scale.
	FTransform AnchorWorld = Mesh->GetSocketTransform(AnchorSocket, RTS_World);
	AnchorWorld.SetScale3D(FVector::OneVector);
	const bool bMonster = Mesh->GetOwner()->IsA<AKZMonster>();
	// Imported Cascade data uses model units; requested Niagara systems use UE cm.
	const FVector PresentationScale = bMonster && !Effect.NiagaraTemplate ? Mesh->GetComponentScale().GetAbs() : FVector::OneVector;
	if ((bMonster || Effect.NiagaraTemplate) && AnchorSocket.IsNone())
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
	EffectWorld.SetScale3D(Effect.Scale3D * (Effect.bUseWorldParticleUnits ? FVector::OneVector : PresentationScale));
	if (Effect.bUseSequencerTransform)
		EffectWorld = Effect.SampleSequencerTransform(SourceTime) * Mesh->GetOwner()->GetActorTransform();

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
	if (Effect.bFaceCameraOutsideMeshBounds && !bTrail && !bDecal)
	{
		if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(World, 0))
		{
			const FVector Facing = (Camera->GetCameraLocation() - EffectWorld.GetLocation()).GetSafeNormal();
			if (!Facing.IsNearlyZero())
			{
				const FBoxSphereBounds& Bounds = Mesh->Bounds;
				const float Front = FVector::DotProduct(Bounds.Origin - EffectWorld.GetLocation(), Facing) +
					FVector::DotProduct(Bounds.BoxExtent, Facing.GetAbs());
				EffectWorld.AddToTranslation(Facing * FMath::Max(0.f, Front));
				EffectWorld.SetRotation(FRotationMatrix::MakeFromXZ(Facing, FVector::UpVector).ToQuat());
			}
		}
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
		if (!Effect.bUseSequencerTransform && Effect.bAttached && !Effect.bOnlyStartAttach)
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

	Component->SetAbsolute(false, Effect.bAbsoluteRotation || Effect.bFaceCameraOutsideMeshBounds, true);
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
		if (Effect.bAlignToWeaponSweep)
		{
			// The editor preview and runtime use the same component-owned shader overrides.
			ConfigureWeaponSlashNiagara(Niagara);
		}
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

#if WITH_EDITOR
void UKZAnimNotify_CombatEffect::ConfigureSequencerPreview(UNiagaraComponent* Component, const bool bWeaponSlash)
{
	if (IsValid(Component) && bWeaponSlash) ConfigureWeaponSlashNiagara(Component);
}

FString UKZAnimNotify_CombatEffect::ApplySequencerEdits(UAnimMontage* Montage, const FString& EditsJSON)
{
	TSharedPtr<FJsonObject> Root;
	if (!Montage || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(EditsJSON), Root))
		return TEXT("Invalid montage or Sequencer edit data.");
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	const TArray<TSharedPtr<FJsonValue>>* Managed = nullptr;
	if (!Root->TryGetArrayField(TEXT("effects"), Rows) || !Root->TryGetArrayField(TEXT("managed_ids"), Managed))
		return TEXT("Missing effects or managed IDs.");
	TSet<FName> ManagedIds;
	for (const auto& Value : *Managed) ManagedIds.Add(FName(*Value->AsString()));
	if (ManagedIds.Contains(NAME_None)) return TEXT("Empty effect ID.");
	TMap<FName, UKZAnimNotify_CombatEffect*> Existing;
	for (FAnimNotifyEvent& Event : Montage->Notifies)
		if (auto* Parent = Cast<UKZAnimNotify_CombatEffect>(Event.Notify))
		{
			if (!Parent->bEndEvent) Existing.Add(Parent->EventId, Parent);
			for (const auto& Child : Parent->BatchedEffects)
				if (Child && !Child->bEndEvent) Existing.Add(Child->EventId, Child);
		}
	struct FEdit
	{
		FName Id;
		UNiagaraSystem* System = nullptr;
		UKZAnimNotify_CombatEffect* Previous = nullptr;
		float Start = 0.f, End = 0.f;
		bool bDrain = false;
		TArray<float> Times;
		TArray<FVector> Locations, Rotations, Scales;
	};
	TArray<FEdit> Edits;
	TSet<FName> Seen;
	for (const auto& Value : *Rows)
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		FString Id, Asset;
		double Start, End;
		const TArray<TSharedPtr<FJsonValue>>* Keys = nullptr;
		if (!Row || !Row->TryGetStringField(TEXT("id"), Id) || !Row->TryGetStringField(TEXT("system"), Asset) ||
			!Row->TryGetNumberField(TEXT("start"), Start) || !Row->TryGetNumberField(TEXT("end"), End) ||
			!Row->TryGetArrayField(TEXT("keys"), Keys) || Keys->IsEmpty() || !FMath::IsFinite(Start) ||
			!FMath::IsFinite(End) || Start < 0. || End <= Start || End > Montage->GetPlayLength())
			return TEXT("Invalid effect interval or transform keys.");
		FEdit& Edit = Edits.AddDefaulted_GetRef();
		Edit.Id = FName(*Id); Edit.Start = Start; Edit.End = End;
		Row->TryGetBoolField(TEXT("drain"), Edit.bDrain);
		if (!ManagedIds.Contains(Edit.Id) || Seen.Contains(Edit.Id)) return TEXT("Duplicate or unmanaged effect ID.");
		Seen.Add(Edit.Id);
		Edit.Previous = Existing.FindRef(Edit.Id);
		if (Edit.Previous && !Edit.Previous->NiagaraTemplate) return TEXT("This tool edits Niagara effects only.");
		if (!Edit.Previous && !Id.StartsWith(TEXT("KZSequencer_"))) return TEXT("New effect IDs must originate from the Sequencer tool.");
		Edit.System = LoadObject<UNiagaraSystem>(nullptr, *Asset);
		if (!Edit.System) return TEXT("Niagara system could not be loaded.");
		for (const auto& KeyValue : *Keys)
		{
			const auto Key = KeyValue->AsObject();
			double Time;
			FVector Location, Rotation, Scale;
			const auto ReadVector = [&Key](const TCHAR* Field, FVector& Vector)
			{
				const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
				if (!Key || !Key->TryGetArrayField(Field, Array) || Array->Num() != 3) return false;
				for (int32 Axis = 0; Axis < 3; ++Axis)
					if (!(*Array)[Axis]->TryGetNumber(Vector[Axis]) || !FMath::IsFinite(Vector[Axis])) return false;
				return true;
			};
			if (!Key || !Key->TryGetNumberField(TEXT("time"), Time) || !FMath::IsFinite(Time) ||
				(!Edit.Times.IsEmpty() && Time <= Edit.Times.Last()) ||
				!ReadVector(TEXT("location"), Location) || !ReadVector(TEXT("rotation"), Rotation) || !ReadVector(TEXT("scale"), Scale))
				return TEXT("Transform keys must be finite and strictly ordered.");
			Edit.Times.Add(Time); Edit.Locations.Add(Location); Edit.Rotations.Add(Rotation); Edit.Scales.Add(Scale);
		}
		for (const FAnimNotifyEvent& Event : Montage->Notifies)
			if (Event.MontageTickType == EMontageNotifyTickType::BranchingPoint &&
				!Cast<UKZAnimNotify_CombatEffect>(Event.Notify) &&
				(FMath::IsNearlyEqual(Event.GetTime(), Edit.Start) || FMath::IsNearlyEqual(Event.GetTime(), Edit.End)))
				return TEXT("Effect boundary coincides with a gameplay branching point; move that boundary in Sequencer.");
	}
	for (const FName Id : ManagedIds)
		if (auto* Previous = Existing.FindRef(Id); Previous && !Previous->NiagaraTemplate)
			return TEXT("Managed IDs include a non-Niagara source effect.");

	const FScopedTransaction Transaction(NSLOCTEXT("Khazan", "ApplyCombatVFXSequence", "Apply Sequencer combat VFX"));
	Montage->Modify();
	// Clone before detaching data children. Other effects, clocks, audio and GUIDs stay in place.
	TArray<UKZAnimNotify_CombatEffect*> Begins;
	for (const FEdit& Edit : Edits)
	{
		auto* Data = Edit.Previous ? DuplicateObject<UKZAnimNotify_CombatEffect>(Edit.Previous, Montage) :
			NewObject<UKZAnimNotify_CombatEffect>(Montage, NAME_None, RF_Transactional);
		Data->BatchedEffects.Reset(); Data->EventId = Edit.Id; Data->bEndEvent = false;
		Data->NiagaraTemplate = Edit.System; Data->bUseSequencerTransform = true;
		Data->WindowStartTime = Edit.Start; Data->WindowEndTime = Edit.End;
		Data->bDestroyOnAnimEnd = true; Data->bDestroyOnNotifyEnd = true;
		Data->bDestroyOnNotifyEndDeactived = Edit.bDrain;
		FRuntimeVectorCurve* Curves[] = {&Data->SequencerTranslation, &Data->SequencerRotation, &Data->SequencerScale};
		const TArray<FVector>* Values[] = {&Edit.Locations, &Edit.Rotations, &Edit.Scales};
		for (int32 Curve = 0; Curve < 3; ++Curve)
			for (int32 Axis = 0; Axis < 3; ++Axis)
			{
				FRichCurve* Keys = Curves[Curve]->GetRichCurve(Axis); Keys->Reset();
				for (int32 Index = 0; Index < Edit.Times.Num(); ++Index)
					Keys->SetKeyInterpMode(Keys->AddKey(Edit.Times[Index], (*Values[Curve])[Index][Axis]), RCIM_Linear);
			}
		Begins.Add(Data);
	}
	for (int32 Index = Montage->Notifies.Num() - 1; Index >= 0; --Index)
		if (auto* Parent = Cast<UKZAnimNotify_CombatEffect>(Montage->Notifies[Index].Notify))
		{
			Parent->Modify();
			Parent->BatchedEffects.RemoveAll([&ManagedIds](const auto& Child) { return Child && ManagedIds.Contains(Child->EventId); });
			if (ManagedIds.Contains(Parent->EventId))
			{
				if (Parent->BatchedEffects.IsEmpty()) Montage->Notifies.RemoveAt(Index);
				else { Parent->EventId = NAME_None; Parent->NiagaraTemplate = nullptr; }
			}
		}
	const auto AddBoundary = [Montage](UKZAnimNotify_CombatEffect* Data, float Time)
	{
		for (FAnimNotifyEvent& Event : Montage->Notifies)
			if (FMath::IsNearlyEqual(Event.GetTime(), Time))
				if (auto* Parent = Cast<UKZAnimNotify_CombatEffect>(Event.Notify))
				{ Parent->Modify(); Parent->BatchedEffects.Add(Data); return; }
		FAnimNotifyEvent& Event = Montage->Notifies.AddDefaulted_GetRef();
		Event.Link(Montage, Time);
		Event.TriggerTimeOffset = GetTriggerTimeOffsetForType(Montage->CalculateOffsetForNotify(Time));
		Event.Notify = Data; Event.NotifyName = TEXT("KZCombatEffect");
		Event.MontageTickType = EMontageNotifyTickType::BranchingPoint;
		Event.Guid = FGuid::NewGuid();
	};
	for (auto* Begin : Begins)
	{
		AddBoundary(Begin, Begin->WindowStartTime);
		auto* End = DuplicateObject<UKZAnimNotify_CombatEffect>(Begin, Montage);
		End->bEndEvent = true;
		AddBoundary(End, End->WindowEndTime);
	}
	Montage->SortNotifies(); Montage->RefreshCacheData(); Montage->MarkPackageDirty();
	return FString();
}
#endif
