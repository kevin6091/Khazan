


#include "Character/KZMonster.h"

#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "AI/KZMonsterAIController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Abilities/GameplayAbility.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "AbilitySystemComponent.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Ability/KZHitReactionAbility.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "Attribute/KZAttributeSet.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"
#include "TimerManager.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifyQueue.h"
#include "Animation/AnimNotifyLibrary.h"
#include "Animation/ActiveMontageInstanceScope.h"
#include "Animation/AnimationInstanceScope.h"
#include "Materials/MaterialInstance.h"
#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "LogChannels.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "Components/MeshComponent.h"
#include "Environment/KZSnowDeformation.h"
#include "EngineUtils.h"

AKZMonster::AKZMonster()
{
	AIControllerClass = AKZMonsterAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	GetCharacterMovement()->GetNavMovementProperties()->bUseAccelerationForPaths = true;
	// AI supplies a bounded desired yaw during attacks; preserve the montage's root motion too.
	GetCharacterMovement()->bAllowPhysicsRotationDuringAnimRootMotion = true;
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	GetMesh()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	LockOnTargetPoint = CreateDefaultSubobject<USceneComponent>(TEXT("LockOnTargetPoint"));
	
	LockOnTargetPoint->SetupAttachment(GetCapsuleComponent());
	static ConstructorHelpers::FObjectFinder<UParticleSystem> Blood(TEXT("/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference"));
	HitBloodEffect = Blood.Object;
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> BloodDecal(TEXT("/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround"));
	HitBloodDecalMaterial = BloodDecal.Object;
	static ConstructorHelpers::FObjectFinder<UParticleSystem> Ash(TEXT("/Game/_Art/Effects/Combat/Blood/FP_Monster_DeathAsh"));
	DeathAshEffect = Ash.Object;
}

void AKZMonster::BeginPlay()
{
	Super::BeginPlay();
	// Blueprint collision profiles and modular parts are initialized by now.
	// Preserve world/attack collision; only the spring-arm probe ignores monsters.
	TInlineComponentArray<UPrimitiveComponent*> Primitives(this);
	for (UPrimitiveComponent* Primitive : Primitives)
	{
		Primitive->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
		// Preserve blocking hits, but a combatant is never a step or landing floor.
		Primitive->CanCharacterStepUpOn = ECB_No;
		Primitive->SetWalkableSlopeOverride(FWalkableSlopeOverride(WalkableSlope_Unwalkable, 0.f));
	}
	// The HeavySwordsman uses the existing empty pose carrier and three modular parts.
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(this);
	for (USkeletalMeshComponent* Part : Meshes)
	{
		if (Part != GetMesh() && Part->ComponentHasTag(TEXT("MonsterBodyPart")))
		{
			// CopyPose parts evaluate their own cloth/hair post-process physics.
			if (Part->GetAnimClass())
			{
				Part->SetLeaderPoseComponent(nullptr);
				Part->AddTickPrerequisiteComponent(GetMesh());
				// Modular skeletons omit anatomy bones; use the complete parent's collision.
				if (UPhysicsAsset* BodyPhysics = GetMesh()->GetPhysicsAsset())
					Part->AddClothCollisionSource(GetMesh(), BodyPhysics);
			}
			else Part->SetLeaderPoseComponent(GetMesh(), true, false);
		}
	}
	BindCombatAttributes();
	if (GetNetMode() != NM_DedicatedServer)
	{
		// Finish incomplete editor on-demand shader maps before combat, rather than during a hit.
		// Cooked builds already contain these shaders; the engine's shared material cache owns the work.
		TArray<UMaterialInterface*> BloodMaterials;
		BloodMaterials.Add(HitBloodDecalMaterial);
		if (HitBloodEffect)
			for (const auto& Emitter : HitBloodEffect->Emitters)
				if (Emitter)
					for (const auto& LOD : Emitter->LODLevels)
						if (LOD && LOD->bEnabled && LOD->RequiredModule)
							BloodMaterials.AddUnique(LOD->RequiredModule->Material.Get());
		for (UMaterialInterface* Material : BloodMaterials)
			if (Material) Material->EnsureIsComplete();
	}
}

void AKZMonster::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	if (HasActorBegunPlay()) BindCombatAttributes();
}

void AKZMonster::UnPossessed()
{
	ClearMonsterVisuals();
	CancelDeathPresentation();
	UnbindCombatAttributes();
	if (UKZExhaustionAbility* Ability = GetActiveExhaustionAbility())
		GetAbilitySystemComponent()->CancelAbilityHandle(Ability->GetCurrentAbilitySpecHandle());
	Super::UnPossessed();
}

void AKZMonster::EndPlay(const EEndPlayReason::Type Reason)
{
	ClearMonsterVisuals();
	CancelDeathPresentation();
	UnbindCombatAttributes();
	if (UKZExhaustionAbility* Ability = GetActiveExhaustionAbility())
		GetAbilitySystemComponent()->CancelAbilityHandle(Ability->GetCurrentAbilitySpecHandle());
	if (UAbilitySystemComponent* ASC = GetAbilitySystemComponent(); ASC && DeadStateHandle.IsValid())
		ASC->RemoveActiveGameplayEffect(DeadStateHandle);
	GetLocomotionComponent()->ReleaseMovementConstraint(DeadMovementHandle);
	Super::EndPlay(Reason);
}

void AKZMonster::BindCombatAttributes()
{
	if (!HasAuthority() || !GetController() || BoundCombatASC.IsValid() || !GetCharacterDefinition() ||
		!GetCharacterDefinition()->GetMonsterStaminaSettings().bEnabled) return;
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	BoundCombatASC = ASC;
	HealthChangedHandle = ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute())
		.AddUObject(this, &ThisClass::HandleCombatAttributeChanged);
	StaminaChangedHandle = ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute())
		.AddUObject(this, &ThisClass::HandleCombatAttributeChanged);
	RequestCombatStateRefresh();
}

void AKZMonster::UnbindCombatAttributes()
{
	if (UAbilitySystemComponent* ASC = BoundCombatASC.Get())
	{
		ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(HealthChangedHandle);
		ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).Remove(StaminaChangedHandle);
	}
	HealthChangedHandle.Reset();
	StaminaChangedHandle.Reset();
	BoundCombatASC.Reset();
	GetWorldTimerManager().ClearTimer(CombatRefreshTimer);
}

void AKZMonster::HandleCombatAttributeChanged(const FOnAttributeChangeData&)
{
	RequestCombatStateRefresh();
}

void AKZMonster::RequestCombatStateRefresh()
{
	if (!BoundCombatASC.IsValid() || !GetController() || !HasActorBegunPlay() ||
		GetWorldTimerManager().TimerExists(CombatRefreshTimer)) return;
	// Coalesce all modifiers of a hit before choosing death/exhaustion, regardless of modifier order.
	CombatRefreshTimer = GetWorldTimerManager().SetTimerForNextTick(this, &ThisClass::RefreshCombatState);
}

UKZExhaustionAbility* AKZMonster::GetActiveExhaustionAbility() const
{
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	if (!ASC) return nullptr;
	FScopedAbilityListLock Lock(*ASC);
	for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		if (Spec.IsActive())
			if (UKZExhaustionAbility* Ability = Cast<UKZExhaustionAbility>(Spec.GetPrimaryInstance())) return Ability;
	return nullptr;
}

bool AKZMonster::IsCombatIncapacitated() const
{
	const UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	return ASC && GetCharacterDefinition() && GetCharacterDefinition()->GetMonsterStaminaSettings().bEnabled &&
		(ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) || ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) ||
		 ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting) ||
		 ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f ||
		 ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) <= 0.f);
}

void AKZMonster::RefreshCombatState()
{
	CombatRefreshTimer.Invalidate();
	UAbilitySystemComponent* ASC = BoundCombatASC.Get();
	if (!ASC || !GetController() || !GetCharacterDefinition()) return;
	const FKZMonsterStaminaSettings& Settings = GetCharacterDefinition()->GetMonsterStaminaSettings();
	UKZExhaustionAbility* Exhaustion = GetActiveExhaustionAbility();
	if (ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)
	{
		FGameplayTagContainer Hits;
		Hits.AddTag(KZGameplayTags::Ability_Reaction_Hit);
		ASC->CancelAbilities(&Hits);
		if (!DeadStateHandle.IsValid() && Settings.DeadStateEffect)
		{
			const FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Settings.DeadStateEffect, 1.f, ASC->MakeEffectContext());
			if (Spec.IsValid()) DeadStateHandle = ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
		}
		if (!DeadMovementHandle.IsValid())
		{
			FKZMovementConstraint Constraint;
			Constraint.bOverrideRotationMode = true;
			Constraint.RotationModeOverride = EKZRotationMode::VelocityDirection;
			Constraint.DebugName = TEXT("MonsterDead");
			DeadMovementHandle = GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
			FGameplayTagContainer Actions;
			Actions.AddTag(KZGameplayTags::Ability_Action);
			ASC->CancelAbilities(&Actions);
		}
		// A lethal paired attack must finish its victim reaction before freezing the corpse.
		if (!Exhaustion || !Exhaustion->HasBrutalPartner())
		{
			if (Exhaustion) ASC->CancelAbilityHandle(Exhaustion->GetCurrentAbilitySpecHandle());
			FinishDeathPresentation();
		}
		else Exhaustion->UpdateLethalBrutalPose();
		return;
	}
	if (ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) > 0.f || Exhaustion) return;
	FGameplayTagContainer Hits;
	Hits.AddTag(KZGameplayTags::Ability_Reaction_Hit);
	ASC->CancelAbilities(&Hits);
	FScopedAbilityListLock Lock(*ASC);
	for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		if (Spec.Ability && Spec.Ability->IsA<UKZExhaustionAbility>())
		{
			ASC->TryActivateAbility(Spec.Handle);
			break;
		}
}

void AKZMonster::FinishDeathPresentation(const bool bPlayDeathAnimation)
{
	if (GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f) return;
	if (DeathPresentationInstanceId != INDEX_NONE || GetMesh()->bPauseAnims) return; // Active/frozen presentation prevents replay.
	if (!bPlayDeathAnimation)
	{
		FreezeDeathPresentation(true); // Completed lethal pair hands off its existing terminal material receipts.
		return;
	}
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	UAnimMontage* Montage = GetCharacterDefinition() ?
		GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage.Get() : nullptr;
	ClearMonsterVisuals(); // Death entry is a presentation context replacement, after gameplay cancellation.
	if (bPlayDeathAnimation && IsValid(Anim) && IsValid(Montage))
	{
		GetMesh()->bPauseAnims = false;
		if (Anim->Montage_Play(Montage) > 0.f)
		{
			if (FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage))
			{
				DeathPresentationAnim = Anim;
				DeathPresentationMontage = Montage;
				DeathPresentationInstanceId = Instance->GetInstanceID();
				FOnMontageEnded End;
				End.BindUObject(this, &ThisClass::HandleDeathPresentationEnded);
				Anim->Montage_SetEndDelegate(End, Montage);
				return;
			}
		}
	}
	FreezeDeathPresentation();
}

void AKZMonster::ClearDeathPresentationBinding()
{
	if (UAnimInstance* Anim = DeathPresentationAnim.Get())
		if (FAnimMontageInstance* Instance = Anim->GetMontageInstanceForID(DeathPresentationInstanceId))
			Instance->OnMontageEnded.Unbind();
	DeathPresentationAnim.Reset();
	DeathPresentationMontage.Reset();
	DeathPresentationInstanceId = INDEX_NONE;
}

void AKZMonster::CancelDeathPresentation()
{
	UAnimInstance* Anim = DeathPresentationAnim.Get();
	UAnimMontage* Montage = DeathPresentationMontage.Get();
	FAnimMontageInstance* Instance = Anim ? Anim->GetMontageInstanceForID(DeathPresentationInstanceId) : nullptr;
	const bool bOwnsInstance = Instance && Montage && Instance->Montage == Montage;
	ClearDeathPresentationBinding(); // Unbind/reset before Stop can invoke an ending callback.
	if (bOwnsInstance)
	{
		Instance->Stop(Montage->BlendOut); // Exact owned instance, with its authored engine blend-out.
		if (GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)
			GetMesh()->bPauseAnims = true;
	}
}

void AKZMonster::HandleDeathPresentationEnded(UAnimMontage* Montage, bool bInterrupted)
{
	if (Montage != DeathPresentationMontage.Get()) return;
	if (bInterrupted)
	{
		// An interrupted montage has no terminal corpse pose. Retry through the
		// existing coalesced HP/Dead path, outside the engine's end-delegate dispatch.
		ClearDeathPresentationBinding();
		RequestCombatStateRefresh();
		return;
	}
	FreezeDeathPresentation(true);
}

void AKZMonster::FreezeDeathPresentation(const bool bKeepTerminalMaterials)
{
	// Source execution curves describe a terminal dissolve. Keep only that exact
	// death execution's material transaction; paused animation cannot end other FX.
	TArray<FMonsterVisualReceipt> Previous = MoveTemp(MonsterVisuals);
	MonsterVisuals.Reset();
	for (int32 Index = Previous.Num() - 1; Index >= 0; --Index)
		if (bKeepTerminalMaterials && CanHoldDeathVisualMaterials(Previous[Index]))
		{
			FMonsterVisualReceipt Held = MoveTemp(Previous[Index]);
			Previous.RemoveAt(Index);
			Held.bNotifyEnded = Held.bTerminalMaterialHold = true;
			if (Held.PairedMaterialOwner.IsValid()) Held.bCorpseMaterialOwner = true;
			ReleaseMonsterVisual(Held, false, true);
			Held.Components.Reset();
			MonsterVisuals.Add(MoveTemp(Held));
		}
	for (int32 Index = Previous.Num() - 1; Index >= 0; --Index)
	{
		RestoreVisualMaterials(Previous[Index]);RestoreVisualBindings(Previous[Index]);
		ReleaseMonsterVisual(Previous[Index], false, true);
	}
	if (MonsterVisuals.IsEmpty()) ClearDeathPresentationBinding();
	else if (UAnimInstance* Anim = DeathPresentationAnim.Get())
		if (FAnimMontageInstance* Instance = Anim->GetMontageInstanceForID(DeathPresentationInstanceId))
			Instance->OnMontageEnded.Unbind(); // Retain exact instance ownership until cancellation/EndPlay.
	if (GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)
	{
		GetMesh()->bPauseAnims = true;
		BeginDeathDissolve();
	}
}

void AKZMonster::PlayHitBlood(AActor* Attacker, const FVector& Contact)
{
	if (GetNetMode() == NM_DedicatedServer || !HitBloodEffect || !GetMesh()) return;
	// The six delivered meshes have no PhysicsAsset. A chest bone lies inside the body.
	// Use the existing damage receiver capsule's surface and eject toward the attacker.
	FVector Direction = IsValid(Attacker) ? (Attacker->GetActorLocation() - Contact).GetSafeNormal2D() : GetActorForwardVector();
	if (Direction.IsNearlyZero()) Direction = GetActorForwardVector();
	const UCapsuleComponent* Capsule = GetCapsuleComponent();
	const float Radius = Capsule->GetScaledCapsuleRadius();
	const FVector Axis = Capsule->GetUpVector() * (Capsule->GetScaledCapsuleHalfHeight() - Radius);
	const FVector Centre = FMath::ClosestPointOnSegment(Contact, Capsule->GetComponentLocation() - Axis, Capsule->GetComponentLocation() + Axis);
	const FVector Point = Centre + Direction * Radius;
	if (UParticleSystemComponent* Blood = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), HitBloodEffect,
		FTransform(Direction.Rotation(), Point), true, EPSCPoolMethod::None, true))
	{
		Blood->ComponentTags.Add(TEXT("KZMonsterHitBlood")); // Finite world particles own their drain.
		Blood->ComponentTags.AddUnique(GetFName());
	}
	if (!HitBloodDecalMaterial || HitBloodDecalSize.GetMin() <= 0.f || HitBloodDecalFadeSeconds <= 0.f) return;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterHitBloodGround), true, this);
	if (IsValid(Attacker)) Query.AddIgnoredActor(Attacker);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FRandomStream Scatter(static_cast<int32>(GetUniqueID() ^ GFrameCounter));
	const int32 Count = FMath::Clamp(HitBloodDecalScatterCount, 0, 16);
	for (int32 Index = 0; Index <= Count; ++Index)
	{
		FVector TracePoint = Point;
		FVector StainDirection = Direction;
		FVector ProjectionSize = HitBloodDecalSize;
		if (Index > 0)
		{
			// One sample per sector gives full-circle coverage without stacking
			// all six satellite stains along the direction of the accepted hit.
			const double Angle = UE_TWO_PI * (Index - 1 + Scatter.FRand()) / Count;
			StainDirection = FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0);
			TracePoint += StainDirection * Scatter.FRandRange(
				FMath::Max(0., HitBloodDecalScatterDistance.X), FMath::Max(0., HitBloodDecalScatterDistance.Y));
			FHitResult Obstacle;
			if (GetWorld()->LineTraceSingleByObjectType(Obstacle, Point, TracePoint, Objects, Query)) continue;
			const double SizeScale = Scatter.FRandRange(FMath::Max(0., HitBloodDecalScatterScale.X), FMath::Max(0., HitBloodDecalScatterScale.Y));
			if (SizeScale <= 0.) continue;
			ProjectionSize.Y *= SizeScale;
			ProjectionSize.Z *= SizeScale;
		}
		FHitResult Ground;
		if (!GetWorld()->LineTraceSingleByObjectType(Ground, TracePoint, TracePoint - FVector::UpVector * HitBloodGroundTraceDistance, Objects, Query) ||
			Ground.ImpactNormal.Z < GetCharacterMovement()->GetWalkableFloorZ()) continue;
		FVector Tangent = FVector::VectorPlaneProject(StainDirection, Ground.ImpactNormal).GetSafeNormal();
		if (Tangent.IsNearlyZero()) Tangent = FVector::VectorPlaneProject(GetActorForwardVector(), Ground.ImpactNormal).GetSafeNormal();
		const FRotator Rotation = FRotationMatrix::MakeFromXZ(-Ground.ImpactNormal, Tangent).Rotator();
		FVector ProjectionPoint = Ground.ImpactPoint;
		for (TActorIterator<AKZSnowDeformation> It(GetWorld()); It; ++It)
		{
			double SnowHeight = 0;
			if (!It->GetSnowSurfaceHeight(Ground, SnowHeight)) continue;
			ProjectionPoint += Ground.ImpactNormal * SnowHeight;
			double LayerExtent = SnowHeight;
			for (const FKZSnowSurfaceSamples& Profile : It->SurfaceContactSamples)
				LayerExtent = FMath::Max(LayerExtent, double(Profile.DepthReferenceCm + Profile.RimHeightCm));
			ProjectionSize.X += LayerExtent;
			break;
		}
		if (UDecalComponent* Decal = UGameplayStatics::SpawnDecalAtLocation(GetWorld(), HitBloodDecalMaterial,
			ProjectionSize, ProjectionPoint, Rotation))
		{
			Decal->ComponentTags.Add(TEXT("KZMonsterHitBloodGround"));
			Decal->ComponentTags.AddUnique(GetFName());
			if (UMaterialInstanceDynamic* Material = Decal->CreateDynamicMaterialInstance())
			{
				Material->SetScalarParameterValue(TEXT("BloodMaskChannel"), Decal->GetUniqueID() % 3);
				Material->SetScalarParameterValue(TEXT("BloodWalkableFloorZ"), GetCharacterMovement()->GetWalkableFloorZ());
			}
			Decal->SetFadeOut(HitBloodDecalHoldSeconds, HitBloodDecalFadeSeconds, false);
		}
	}
}

void AKZMonster::BeginDeathDissolve()
{
	if (DeathDissolveElapsed >= 0.f || GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f) return;
	ClearMonsterVisuals(); // Finished execution transfers to the universal corpse presentation.
	ClearDeathPresentationBinding();
	DeathDissolveElapsed = 0.f;
	TInlineComponentArray<UMeshComponent*> Meshes(this);
	for (UMeshComponent* BodyMesh : Meshes)
		for (int32 Slot = 0; Slot < BodyMesh->GetNumMaterials(); ++Slot)
			if (UMaterialInstanceDynamic* MID = BodyMesh->CreateDynamicMaterialInstance(Slot))
			{
				MID->SetScalarParameterValue(TEXT("KZDeathProgress"), 0.f);
				DeathMaterials.Add(MID);
			}
	if (GetNetMode() != NM_DedicatedServer && DeathAshEffect)
	{
		// Actual posed body anchors spread ash over humanoid and giant bodies without a fixed-size box.
		for (const FName Bone : {FName(TEXT("Bip001-Spine2")), FName(TEXT("Bip001-Head")),
			FName(TEXT("Bip001-Pelvis")), FName(TEXT("Bip001-L-Hand")), FName(TEXT("Bip001-R-Hand")),
			FName(TEXT("Bip001-L-Calf")), FName(TEXT("Bip001-R-Calf"))})
			if (GetMesh()->DoesSocketExist(Bone))
				if (UParticleSystemComponent* Ash = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), DeathAshEffect,
					GetMesh()->GetSocketLocation(Bone), FRotator::ZeroRotator, FVector::OneVector, true))
				{
					Ash->ComponentTags.Add(TEXT("KZMonsterDeathAsh"));
					Ash->ComponentTags.AddUnique(GetFName());
				}
	}
}

bool AKZMonster::ReportAttackParried(AActor* Defender)
{
	if (!HasAuthority() || !IsValid(Defender) || !GetCharacterDefinition()) return false;
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	const FKZMonsterStaminaSettings& Settings = GetCharacterDefinition()->GetMonsterStaminaSettings();
	if (!Settings.bEnabled || !Settings.DamageEffect || !FMath::IsFinite(Settings.ParryStaminaDamage) ||
		Settings.ParryStaminaDamage <= 0.f || ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f) return false;
	FGameplayEffectContextHandle Context = ASC->MakeEffectContext();
	Context.AddInstigator(Defender, Defender);
	const FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Settings.DamageEffect, 1.f, Context);
	if (!Spec.IsValid()) return false;
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), 0.f);
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")), -Settings.ParryStaminaDamage);
	const bool bApplied=ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()).WasSuccessfullyApplied();
	if (bApplied)
		if (auto* Pattern=Cast<UKZMonsterPatternAbility>(ASC->GetAnimatingAbility())) Pattern->ReportPatternEvent(EKZPatternEvent::Parried);
	return bApplied;
}

bool AKZMonster::TrySystemGuard(const float StaminaDamage, AActor* Attacker)
{
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	if (!HasAuthority() || !IsValid(Attacker) || !ASC || !GetCharacterDefinition() ||
		!FMath::IsFinite(StaminaDamage) || StaminaDamage < 0.f || (IsCombatIncapacitated() &&
		!ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting))) return false;
	const FKZHitReactionSettings& Reaction = GetCharacterDefinition()->GetHitReactionSettings();
	const FKZMonsterStaminaSettings& Stamina = GetCharacterDefinition()->GetMonsterStaminaSettings();
	if (!Reaction.bSystemGuardOnLockOn || !Stamina.DamageEffect ||
		ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f ||
		ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) <= 0.f ||
		ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) ||
		ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted)) return false;
	const FVector ToAttacker = (Attacker->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
	const float HalfAngle = FMath::Clamp(Reaction.SystemGuardFrontAngle, 0.f, 360.f) * .5f;
	if (ToAttacker.IsNearlyZero() || !FMath::IsFinite(HalfAngle) ||
		FVector::DotProduct(GetActorForwardVector().GetSafeNormal2D(), ToAttacker) + UE_KINDA_SMALL_NUMBER <
		FMath::Cos(FMath::DegreesToRadians(HalfAngle))) return false;
	bool bShieldReaction = false, bAction = false, bAttackGuard = false;
	{
		FScopedAbilityListLock Lock(*ASC);
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		{
			if (!Spec.IsActive()) continue;
			if (const UKZHitReactionAbility* Hit = Cast<UKZHitReactionAbility>(Spec.GetPrimaryInstance()))
				bShieldReaction |= Hit->IsShieldReaction();
			if (Spec.Ability && Spec.Ability->GetAssetTags().HasTag(KZGameplayTags::Ability_Action))
			{
				bAction = true;
				if (const UKZComboActionAbility* Combo = Cast<UKZComboActionAbility>(Spec.GetPrimaryInstance()))
					bAttackGuard |= Combo->IsInSystemGuardWindow();
			}
		}
	}
	const AKZMonsterAIController* AI = Cast<AKZMonsterAIController>(GetController());
	// Ordinary pre-detection movement is Normal in the source. Attack guard is only its authored window.
	if (!bShieldReaction && !(bAction ? bAttackGuard : (AI && IsValid(AI->GetBattleTarget())))) return false;
	if (ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting) && !bShieldReaction) return false;
	FGameplayEffectContextHandle Context = ASC->MakeEffectContext();
	Context.AddInstigator(Attacker, Attacker);
	const FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Stamina.DamageEffect, 1.f, Context);
	if (!Spec.IsValid()) return false;
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), 0.f);
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")), -StaminaDamage);
	if (!ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()).WasSuccessfullyApplied()) return false;
	if (ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f &&
		ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) > 0.f)
	{
		FGameplayEventData Event;
		Event.EventTag = KZGameplayTags::Event_Combat_ShieldBlock;
		Event.Instigator = Attacker;
		Event.Target = this;
		ASC->HandleGameplayEvent(Event.EventTag, &Event);
	}
	RequestCombatStateRefresh();
	return true;
}

void AKZMonster::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (UKZExhaustionAbility* Exhaustion = GetActiveExhaustionAbility(); Exhaustion && Exhaustion->HasBrutalPartner())
		Exhaustion->UpdateLethalBrutalPose();
	if (DeathDissolveElapsed >= 0.f)
	{
		DeathDissolveElapsed += DeltaSeconds;
		const float Progress = DeathDissolveSeconds > 0.f ? FMath::Clamp(DeathDissolveElapsed / DeathDissolveSeconds, 0.f, 1.f) : 1.f;
		for (UMaterialInstanceDynamic* MID : DeathMaterials) if (MID) MID->SetScalarParameterValue(TEXT("KZDeathProgress"), Progress);
		if (Progress >= 1.f) { Destroy(); return; } // Target/UI/AI release through existing EndPlay ownership.
	}
	if (DeathPresentationInstanceId != INDEX_NONE && !GetMesh()->bPauseAnims)
	{
		UAnimInstance* Anim = DeathPresentationAnim.Get();
		FAnimMontageInstance* Instance = Anim ? Anim->GetMontageInstanceForID(DeathPresentationInstanceId) : nullptr;
		// Finite no-auto-blend death montage holds its final pose. Engine clamps
		// the final section and sets bPlaying=false; no guessed duration/timer.
		if (!Instance || Instance->IsStopped())
		{
			ClearDeathPresentationBinding();
			RequestCombatStateRefresh();
		}
		else if (!Instance->IsPlaying()) FreezeDeathPresentation(true);
	}
	for (int32 Index = MonsterVisuals.Num() - 1; Index >= 0; --Index)
	{
		FMonsterVisualReceipt& Receipt = MonsterVisuals[Index];
		const UKZAnimNotifyState_MonsterVisual* Data = Receipt.Data.Get();
		const bool bKeepTerminal = Receipt.bTerminalMaterialHold && CanHoldDeathVisualMaterials(Receipt);
		if (!Receipt.Mesh.IsValid() || !Receipt.AnimInstance.IsValid() ||
			Receipt.Mesh->GetAnimInstance() != Receipt.AnimInstance.Get() || (Receipt.Mesh->bPauseAnims && !bKeepTerminal) || !Data ||
			(Receipt.bTerminalMaterialHold && !bKeepTerminal) ||
			(Receipt.MontageInstanceId != INDEX_NONE && !bKeepTerminal &&
			 !Receipt.AnimInstance->GetMontageInstanceForID(Receipt.MontageInstanceId)))
		{
			FMonsterVisualReceipt Previous = MoveTemp(Receipt);
			MonsterVisuals.RemoveAt(Index);
			RestoreVisualMaterials(Previous);
			RestoreVisualBindings(Previous);
			ReleaseMonsterVisual(Previous, false, true);
			continue;
		}
		if (Receipt.bNotifyEnded && !bKeepTerminal && Receipt.FadeStartTime < 0.f &&
			!Receipt.Components.ContainsByPredicate([](const auto& Weak) {return Weak.IsValid();}))
		{
			MonsterVisuals.RemoveAt(Index);
			continue;
		}
		if (Receipt.FadeStartTime >= 0.f && Data->Effect)
		{
			const float Blend = Data->Effect->TrailBlendTime;
			const float Elapsed = GetWorld()->GetTimeSeconds() - Receipt.FadeStartTime;
			const float Weight = Blend > 0.f ? FMath::Clamp(1.f - Elapsed / Blend, 0.f, 1.f) : 0.f;
			for (const auto& Weak : Receipt.Components)
				if (UStaticMeshComponent* Trail = Cast<UStaticMeshComponent>(Weak.Get()))
					for (int32 Slot = 0; Slot < Trail->GetNumMaterials(); ++Slot)
						if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(Trail->GetMaterial(Slot)))
							if (!Data->Effect->TrailIntensityParameter.IsNone()) MID->SetScalarParameterValue(
								Data->Effect->TrailIntensityParameter, Data->Effect->TrailIntensity * Weight);
			if (Weight <= 0.f)
			{
				FMonsterVisualReceipt Previous = MoveTemp(Receipt);
				MonsterVisuals.RemoveAt(Index);
				ReleaseMonsterVisual(Previous, true, true);
			}
		}
	}
}

AKZMonster* AKZMonster::GetTalkPartner() const
{
	AKZMonster* Partner = TalkPartner.Get();
	if (!IsValid(Partner) || Partner == this || Partner->TalkPartner != this ||
		Partner->bSecondTalkRole == bSecondTalkRole || bPatrolWhenUnaware || Partner->bPatrolWhenUnaware ||
		!Cast<AKZMonsterAIController>(GetController()) || !Cast<AKZMonsterAIController>(Partner->GetController())) return nullptr;
	const UKZCharacterDefinitionData* Definition = GetCharacterDefinition();
	const UKZCharacterDefinitionData* OtherDefinition = Partner->GetCharacterDefinition();
	if (!Definition || !OtherDefinition) return nullptr;
	const EKZUnawareRoutineRole RoutineRole = bSecondTalkRole ? EKZUnawareRoutineRole::Talk02 : EKZUnawareRoutineRole::Talk01;
	const EKZUnawareRoutineRole OtherRole = bSecondTalkRole ? EKZUnawareRoutineRole::Talk01 : EKZUnawareRoutineRole::Talk02;
	if (!Definition->GetUnawareRoutines().ContainsByPredicate([RoutineRole](const FKZUnawareRoutine& R) { return R.Role == RoutineRole && R.AbilityClass; }) ||
		!OtherDefinition->GetUnawareRoutines().ContainsByPredicate([OtherRole](const FKZUnawareRoutine& R) { return R.Role == OtherRole && R.AbilityClass; })) return nullptr;
	return Partner;
}

bool AKZMonster::HasActiveTalkLoop() const
{
	const UKZCharacterDefinitionData* Definition = GetCharacterDefinition();
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	if (!Definition || !ASC) return false;
	for (const FKZUnawareRoutine& Routine : Definition->GetUnawareRoutines())
	{
		if (Routine.Role == EKZUnawareRoutineRole::Solo) continue;
		const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(Routine.AbilityClass);
		const UKZComboActionAbility* Ability = Spec ? Cast<UKZComboActionAbility>(Spec->GetPrimaryInstance()) : nullptr;
		if (Spec && Spec->IsActive() && Ability && Ability->GetCurrentNodeId() == TEXT("Loop")) return true;
	}
	return false;
}

const FKZUnawareRoutine* AKZMonster::ResolveUnawareRoutine(bool bAllowTalk) const
{
	const UKZCharacterDefinitionData* Definition = GetCharacterDefinition();
	if (!Definition) return nullptr;
	AKZMonster* Partner = bAllowTalk ? GetTalkPartner() : nullptr;
	if (Partner)
	{
		const AKZMonsterAIController* OtherAI = CastChecked<AKZMonsterAIController>(Partner->GetController());
		const UAbilitySystemComponent* OtherASC = Partner->GetAbilitySystemComponent();
		// A partner in a solo routine, an End, or combat cannot start a conversation.
		if (OtherAI->GetBattleTarget() || (OtherASC && !Partner->HasActiveTalkLoop() &&
			OtherASC->GetActivatableAbilities().ContainsByPredicate([](const FGameplayAbilitySpec& S) { return S.IsActive(); }))) Partner = nullptr;
	}
	const EKZUnawareRoutineRole RoutineRole = Partner ? (bSecondTalkRole ? EKZUnawareRoutineRole::Talk02 : EKZUnawareRoutineRole::Talk01) : EKZUnawareRoutineRole::Solo;
	TArray<const FKZUnawareRoutine*> Candidates;
	for (const FKZUnawareRoutine& Routine : Definition->GetUnawareRoutines())
	{
		if (Routine.Role != RoutineRole || !Routine.AbilityClass) continue;
		if (RoutineRole == EKZUnawareRoutineRole::Solo && Routine.Name == UnawareRoutineName) return &Routine;
		Candidates.Add(&Routine);
	}
	return Candidates.IsEmpty() ? nullptr : Candidates[FMath::RandHelper(Candidates.Num())];
}


void AKZMonster::BeginMonsterVisual(const UKZAnimNotifyState_MonsterVisual& Data,
	USkeletalMeshComponent* InMesh, const FAnimNotifyEventReference& Reference)
{
	check(IsInGameThread());
	const int32 Id = Reference.GetNotifyInstanceID();
	if (!IsValid(InMesh) || InMesh->GetOwner() != this || !InMesh->GetAnimInstance() || InMesh->bPauseAnims ||
		Id == INDEX_NONE || GetNetMode() == NM_DedicatedServer ||
		(Data.Effect && Data.Effect->bOnAttackSuccessed)) return;
	const FName Scalar = Data.ScalarParameterName.IsNone() ? Data.ScalarCurveName : Data.ScalarParameterName;
	const bool bExecutionMaterial = !Data.MaterialOverrides.IsEmpty() &&
		(Scalar == TEXT("Execution") || Scalar == TEXT("ExecutionO") || Data.VectorParameterName == TEXT("ExecutionOffset_radius"));
	UKZExhaustionAbility* PairedOwner = bExecutionMaterial ? GetActiveExhaustionAbility() : nullptr;
	// Project Brutal damage can be nonlethal. Its death-only source dissolve must
	// not hide a surviving victim; direct source previews have no paired owner.
	if (PairedOwner && PairedOwner->HasBrutalPartner() &&
		GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f) return;
	if (MonsterVisuals.ContainsByPredicate([InMesh, Id](const FMonsterVisualReceipt& R)
		{ return R.Mesh == InMesh && R.NotifyId == Id; })) return;
	FMonsterVisualReceipt Receipt;
	Receipt.Mesh = InMesh;
	Receipt.AnimInstance = InMesh->GetAnimInstance();
	Receipt.Data = &Data;
	Receipt.NotifyId = Id;
	if (PairedOwner && PairedOwner->HasBrutalPartner()) Receipt.PairedMaterialOwner = PairedOwner;
	Receipt.Source = Reference.GetSourceObject();
	if (const auto* Context = Reference.GetContextData<UE::Anim::FAnimNotifyMontageInstanceContext>())
		Receipt.MontageInstanceId = Context->MontageInstanceID;
	if (const auto* Context = Reference.GetContextData<UE::Anim::FAnimNotifyAssetPlayerInstanceContext>())
		Receipt.AssetPlayerInstanceId = Context->AssetPlayerInstanceID;
	Receipt.StartTime = GetWorld()->GetTimeSeconds();
	Receipt.LatestSourceTime = Reference.GetCurrentAnimationTime();
	// Notifies precede this frame's pose finalization. Spawn once from the final pose below.
	TInlineComponentArray<USkeletalMeshComponent*> VisualMeshes(this);
	for (USkeletalMeshComponent* VisualMesh : VisualMeshes)
	{
		if (VisualMesh != InMesh && !VisualMesh->ComponentHasTag(TEXT("MonsterBodyPart"))) continue;
		const auto AcquireBinding = [&](const int32 Slot, UMaterialInterface* Replacement)
		{
			UMaterialInterface* Current = Slot == INDEX_NONE ? VisualMesh->GetOverlayMaterial() : VisualMesh->GetMaterial(Slot);
			FVisualMaterialBinding Binding;
			Binding.MeshComponent = VisualMesh; Binding.Slot = Slot; Binding.Baseline.Reset(Current);
			for (const FMonsterVisualReceipt& Active : MonsterVisuals)
				for (const FVisualMaterialBinding& Prior : Active.MaterialBindings)
					if (Prior.MeshComponent == VisualMesh && Prior.Slot == Slot && Current == Prior.Installed.Get())
					{
						Binding.Baseline.Reset(Prior.Baseline.Get());
						if (Prior.Installed.IsValid() && Prior.Installed->Parent == Replacement) Binding.Installed = Prior.Installed;
					}
			if (!Binding.Installed.IsValid())
			{
#if WITH_EDITOR
				// Editor on-demand compilation can leave the first overlay invisible.
				// Finish the existing shader resource before installing its first MID.
				Replacement->EnsureIsComplete();
#endif
				Binding.Installed = UMaterialInstanceDynamic::Create(Replacement, VisualMesh);
				// Current NON-V3 textures/colors remain the baseline while the
				// reconstructed parent consumes the original execution curves.
				if (Slot != INDEX_NONE && Binding.Baseline.IsValid())
					Binding.Installed->CopyMaterialUniformParameters(Binding.Baseline.Get());
			}
			if (Slot == INDEX_NONE) VisualMesh->SetOverlayMaterial(Binding.Installed.Get());
			else VisualMesh->SetMaterial(Slot, Binding.Installed.Get());
			Receipt.MaterialBindings.Add(Binding);
		};
		if (Data.MaterialOverlay) AcquireBinding(INDEX_NONE, Data.MaterialOverlay);
		for (int32 Slot = 0; Slot < VisualMesh->GetNumMaterials(); ++Slot)
		{
			for (const FKZMonsterVisualMaterialOverride& Override : Data.MaterialOverrides)
			{
				if (!Override.SourceMaterial || !Override.ReplacementMaterial) continue;
				UMaterialInterface* Source = VisualMesh->GetMaterial(Slot);
				// A prior transaction's earliest baseline retains source identity for concurrent states.
				for (const FMonsterVisualReceipt& Active : MonsterVisuals)
					for (const FVisualMaterialBinding& Prior : Active.MaterialBindings)
						if (Prior.MeshComponent == VisualMesh && Prior.Slot == Slot && Source == Prior.Installed.Get()) Source = Prior.Baseline.Get();
				if (const UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(Source)) Source = MID->Parent;
				if (Source == Override.SourceMaterial) {AcquireBinding(Slot, Override.ReplacementMaterial);break;}
			}
		}
	}
	const FName ScalarName = Data.ScalarParameterName.IsNone() ? Data.ScalarCurveName : Data.ScalarParameterName;
	const auto AddWrite = [&](UMaterialInstanceDynamic* MID, FName Parameter, bool bVector)
	{
		if (!MID || Parameter.IsNone()) return;
		FVisualMaterialWrite Write; Write.Material = MID; Write.Parameter = Parameter; Write.bVector = bVector;
		const bool bExists = bVector ? MID->GetVectorParameterValue(FMaterialParameterInfo(Parameter), Write.VectorBaseline) :
			MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter), Write.ScalarBaseline);
		if (!bExists) return;
		// Every overlapping receipt carries the first baseline, not the prior owner's override.
		for (const FMonsterVisualReceipt& Active : MonsterVisuals)
			for (const FVisualMaterialWrite& Prior : Active.MaterialWrites)
				if (Prior.Material == MID && Prior.Parameter == Parameter && Prior.bVector == bVector)
				{
					Write.VectorBaseline = Prior.VectorBaseline; Write.ScalarBaseline = Prior.ScalarBaseline;
				}
		Write.LastVector = Write.VectorBaseline; Write.LastScalar = Write.ScalarBaseline;
		Receipt.MaterialWrites.Add(Write);
	};
	if (!ScalarName.IsNone() || (!Data.BoneName.IsNone() && !Data.VectorParameterName.IsNone()))
	{
		for (int32 Slot = 0; Slot < InMesh->GetNumMaterials(); ++Slot)
		{
			UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(InMesh->GetMaterial(Slot));
			if (!MID) MID = InMesh->CreateDynamicMaterialInstance(Slot);
			AddWrite(MID, ScalarName, false);
			if (InMesh->DoesSocketExist(Data.BoneName)) AddWrite(MID, Data.VectorParameterName, true);
		}
	}
	for (const FVisualMaterialBinding& Binding : Receipt.MaterialBindings)
		if (Binding.Slot == INDEX_NONE) AddWrite(Binding.Installed.Get(), ScalarName, false);

	MonsterVisuals.Add(MoveTemp(Receipt)); // Install ownership before first PSC activation/callback.
	TickMonsterVisual(Data, InMesh, Reference);
	if (Data.Effect)
	{
		MonsterVisuals.Last().InitialPoseHandle = InMesh->RegisterOnBoneTransformsFinalizedDelegate(
			FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateWeakLambda(this, [this, WeakMesh = TWeakObjectPtr<USkeletalMeshComponent>(InMesh), Id]()
			{
				// Unregister can release this executing functor. Copy captures first; Spawn may reenter/resize receipts.
				const TWeakObjectPtr<AKZMonster> Owner(this);
				const TWeakObjectPtr<USkeletalMeshComponent> PoseMesh = WeakMesh;
				const int32 NotifyId = Id;
				const auto FindPending = [Owner, PoseMesh, NotifyId]() -> FMonsterVisualReceipt*
				{ return Owner.IsValid() ? Owner->MonsterVisuals.FindByPredicate([PoseMesh, NotifyId](const FMonsterVisualReceipt& R) { return R.Mesh == PoseMesh && R.NotifyId == NotifyId; }) : nullptr; };
				FMonsterVisualReceipt* Pending = FindPending();
				if (!Pending || !PoseMesh.IsValid()) return;
				const UKZAnimNotify_CombatEffect* Effect = Pending->Data.IsValid() ? Pending->Data->Effect.Get() : nullptr;
				if (!Effect || Pending->bNotifyEnded || PoseMesh->GetAnimInstance() != Pending->AnimInstance.Get()) return;
				const float NotifyTime = Pending->LatestSourceTime;
				const bool bCorrectEachPose = Effect->bUseSourceCorrection && Effect->bUseCorrectionCurves && !Effect->bSpawnOnFloor;
				if (!bCorrectEachPose)
				{
					const FDelegateHandle Handle = Pending->InitialPoseHandle; Pending->InitialPoseHandle.Reset();
					PoseMesh->UnregisterOnBoneTransformsFinalizedDelegate(Handle);
				}
				if (Pending->Components.IsEmpty())
				{
					USceneComponent* Component = UKZAnimNotify_CombatEffect::SpawnComponent(*Effect, PoseMesh.Get(), false, 0.f, NotifyTime);
					if (!Component) return;
					Pending = FindPending();
					if (!Pending || Pending->bNotifyEnded || !PoseMesh.IsValid() || PoseMesh->GetAnimInstance() != Pending->AnimInstance.Get()) { Component->DestroyComponent(); return; }
					Component->ComponentTags.AddUnique(Owner->GetFName()); Pending->Components.Add(Component);
					if (Effect->bDeepSnowTrail) Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
					if (Effect->bUseSourceCorrection)
					{
						FTransform Anchor = PoseMesh->GetSocketTransform(Effect->CorrectionBoneName, RTS_World); Anchor.SetScale3D(FVector::OneVector);
						FTransform Geometry = Component->GetComponentTransform(); Geometry.SetScale3D(FVector::OneVector);
						Pending->CorrectionLocal = Geometry.GetRelativeTransform(Anchor) * Effect->SampleSourceCorrection(NotifyTime);
					}
					if (UFXSystemComponent* FX = Cast<UFXSystemComponent>(Component)) FX->Activate(true);
				}
				Pending = FindPending();
				if (bCorrectEachPose && Pending && !Pending->bNotifyEnded)
				{
					FTransform Anchor = PoseMesh->GetSocketTransform(Effect->CorrectionBoneName, RTS_World); Anchor.SetScale3D(FVector::OneVector);
					FTransform Transform = Pending->CorrectionLocal * Effect->SampleSourceCorrection(NotifyTime).Inverse() * Anchor;
					Transform.SetScale3D(Effect->Scale3D * (Effect->bUseWorldParticleUnits ? FVector::OneVector : PoseMesh->GetComponentScale().GetAbs()));
					for (const auto& Weak : Pending->Components) if (USceneComponent* Component = Weak.Get()) Component->SetWorldTransform(Transform);
				}
			}));
	}
	if (!Data.bAnimationContextBoundary) UE_LOG(LogAbility, Display, TEXT("MonsterVisual Begin Actor=%s Event=%s NotifyID=%d Components=%d SourceTime=%f"),
		*GetName(), Data.Effect ? *Data.Effect->EventId.ToString() : *Data.ScalarCurveName.ToString(), Id,
		MonsterVisuals.Last().Components.Num(), Reference.GetCurrentAnimationTime());
}

void AKZMonster::TickMonsterVisual(const UKZAnimNotifyState_MonsterVisual& Data,
	USkeletalMeshComponent* InMesh, const FAnimNotifyEventReference& Reference)
{
	check(IsInGameThread());
	FMonsterVisualReceipt* Receipt = MonsterVisuals.FindByPredicate([InMesh, &Reference](const FMonsterVisualReceipt& R)
		{ return R.Mesh == InMesh && R.NotifyId == Reference.GetNotifyInstanceID() && !R.bNotifyEnded; });
	if (!Receipt || Receipt->AnimInstance.Get() != InMesh->GetAnimInstance()) return;
	const float SourceTime = Reference.GetCurrentAnimationTime();
	Receipt->LatestSourceTime = SourceTime; // Bone-dependent correction runs after the current pose, not last frame's pose.
	if (Data.Effect && Data.Effect->bDeepSnowTrail && Data.Effect->TrailMesh && Data.Effect->TrailCreateCount > 1)
	{
		// Explicit render adapter: source CreateCount stamps are uniformly sampled
		// across the exact notify window, not recovered virtual-texture game code.
		const float Duration = Data.Effect->WindowEndTime - Data.Effect->WindowStartTime;
		const int32 Wanted = Duration > 0.f ? FMath::Clamp(1 + FMath::FloorToInt(
			(SourceTime - Data.Effect->WindowStartTime) / Duration * Data.Effect->TrailCreateCount), 1, Data.Effect->TrailCreateCount) : 1;
		while (Receipt->Components.Num() < Wanted)
		{
			USceneComponent* Stamp = UKZAnimNotify_CombatEffect::SpawnComponent(*Data.Effect, InMesh, false, 0.f, SourceTime);
			if (!Stamp) break;
			Stamp->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
			Stamp->ComponentTags.AddUnique(GetFName());
			Receipt->Components.Add(Stamp);
		}
	}
	for (FVisualMaterialWrite& Write : Receipt->MaterialWrites)
	{
		UMaterialInstanceDynamic* MID = Write.Material.Get(); if (!MID) continue;
		if (Write.bVector)
		{
			// Raw source names are exact; world XYZ and preservation of radius alpha
			// are the documented adapter because original native executable is unavailable.
			const FVector Bone = InMesh->GetSocketLocation(Data.BoneName);
			Write.LastVector = FLinearColor(Bone.X, Bone.Y, Bone.Z, Write.VectorBaseline.A);
			MID->SetVectorParameterValue(Write.Parameter, Write.LastVector);
		}
		else
		{
			Write.LastScalar = Data.bUseScalarCurve ? Data.ScalarCurve.GetRichCurveConst()->Eval(SourceTime) :
				InMesh->GetAnimInstance()->GetCurveValue(Data.ScalarCurveName);
			MID->SetScalarParameterValue(Write.Parameter, Write.LastScalar);
		}
	}
}

void AKZMonster::RestoreVisualMaterials(const FMonsterVisualReceipt& Receipt)
{
	for (const FVisualMaterialWrite& Write : Receipt.MaterialWrites)
	{
		UMaterialInstanceDynamic* MID = Write.Material.Get(); if (!MID) continue;
		const FVisualMaterialWrite* Remaining = nullptr;
		for (const FMonsterVisualReceipt& Active : MonsterVisuals)
			for (const FVisualMaterialWrite& Other : Active.MaterialWrites)
				if (Other.Material == MID && Other.Parameter == Write.Parameter && Other.bVector == Write.bVector) Remaining = &Other;
		if (Write.bVector)
		{
			FLinearColor Current;
			if (MID->GetVectorParameterValue(FMaterialParameterInfo(Write.Parameter), Current) && Current.Equals(Write.LastVector))
				MID->SetVectorParameterValue(Write.Parameter, Remaining ? Remaining->LastVector : Write.VectorBaseline);
		}
		else
		{
			float Current = 0.f;
			if (MID->GetScalarParameterValue(FMaterialParameterInfo(Write.Parameter), Current) && FMath::IsNearlyEqual(Current, Write.LastScalar))
				MID->SetScalarParameterValue(Write.Parameter, Remaining ? Remaining->LastScalar : Write.ScalarBaseline);
		}
	}
}

void AKZMonster::ReleaseMonsterVisual(FMonsterVisualReceipt& Receipt, const bool bReachedEnd, const bool bForce)
{
	if (Receipt.InitialPoseHandle.IsValid() && Receipt.Mesh.IsValid()) Receipt.Mesh->UnregisterOnBoneTransformsFinalizedDelegate(Receipt.InitialPoseHandle);
	Receipt.InitialPoseHandle.Reset();
	const UKZAnimNotify_CombatEffect* Effect = Receipt.Data.IsValid() ? Receipt.Data->Effect.Get() : nullptr;
	for (const auto& Weak : Receipt.Components)
	{
		USceneComponent* Component = Weak.Get(); if (!Component) continue;
		if (Effect && Effect->OnNotifyEndDeattach) Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
		const bool bKill = !Effect || (!bReachedEnd && Effect->bDestroyOnAnimEnd) ||
			(bForce && Cast<UDecalComponent>(Component) && Effect->DecalLifeSpan <= 0.f) ||
			(bReachedEnd && Effect->bDestroyOnNotifyEnd && !Effect->bDestroyOnNotifyEndDeactived);
		if (bKill || Cast<UStaticMeshComponent>(Component)) Component->DestroyComponent();
		else if (UParticleSystemComponent* Particle = Cast<UParticleSystemComponent>(Component))
		{
			if (bForce || !bReachedEnd || Effect->bDestroyOnNotifyEnd) Particle->DeactivateSystem();
			else if (Particle->Template && Particle->Template->IsLooping()) Particle->DeactivateSystem();
		}
		else if (UNiagaraComponent* Niagara = Cast<UNiagaraComponent>(Component))
		{
			if (bForce || !bReachedEnd || Effect->bDestroyOnNotifyEnd ||
				(Niagara->GetAsset() && Niagara->GetAsset()->IsLooping())) Niagara->Deactivate();
		}
		// Finite particles drain; decals retain exact engine source lifespan unless explicitly killed.
	}
}

void AKZMonster::EndMonsterVisual(USkeletalMeshComponent* InMesh, const int32 NotifyId, const bool bReachedEnd)
{
	check(IsInGameThread());
	const int32 Index = MonsterVisuals.IndexOfByPredicate([InMesh, NotifyId](const FMonsterVisualReceipt& R)
		{ return R.Mesh == InMesh && R.NotifyId == NotifyId && !R.bNotifyEnded; });
	if (Index == INDEX_NONE) return;
	FMonsterVisualReceipt Previous = MoveTemp(MonsterVisuals[Index]);
	MonsterVisuals.RemoveAt(Index);
	if (bReachedEnd && CanHoldDeathVisualMaterials(Previous))
	{
		Previous.bNotifyEnded = Previous.bTerminalMaterialHold = true;
		ReleaseMonsterVisual(Previous, false, true);Previous.Components.Reset();
		MonsterVisuals.Add(MoveTemp(Previous));
		return;
	}
	RestoreVisualMaterials(Previous);
	RestoreVisualBindings(Previous);
	Previous.MaterialWrites.Reset(); Previous.MaterialBindings.Reset();
	Previous.bNotifyEnded = true;
	const UKZAnimNotify_CombatEffect* Effect = Previous.Data.IsValid() ? Previous.Data->Effect.Get() : nullptr;
	if (!bReachedEnd || !Effect) {ReleaseMonsterVisual(Previous, false, false);return;}
	if (Effect->TrailMesh && Effect->TrailBlendTime > 0.f)
	{
		Previous.FadeStartTime = GetWorld()->GetTimeSeconds();
	}
	else if (Effect->bDestroyOnNotifyEnd)
	{
		ReleaseMonsterVisual(Previous, true, false);
	}
	else if (Effect->OnNotifyEndDeattach)
	{
		for (const auto& Weak : Previous.Components) if (USceneComponent* Component = Weak.Get())
			Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
	}
	// Ended windows retain only weak resource receipts until the real source context
	// ends. In particular bDestroyOnAnimEnd must still kill a naturally surviving tail.
	Previous.Components.RemoveAll([](const auto& Weak) {return !Weak.IsValid();});
	if (!Previous.Components.IsEmpty()) MonsterVisuals.Add(MoveTemp(Previous));
}

void AKZMonster::EndMonsterVisualContext(USkeletalMeshComponent* InMesh, const FAnimNotifyEventReference& Reference)
{
	check(IsInGameThread());
	const auto* MontageContext = Reference.GetContextData<UE::Anim::FAnimNotifyMontageInstanceContext>();
	const auto* AssetContext = Reference.GetContextData<UE::Anim::FAnimNotifyAssetPlayerInstanceContext>();
	for (int32 Index = MonsterVisuals.Num() - 1; Index >= 0; --Index)
	{
		const FMonsterVisualReceipt& Active = MonsterVisuals[Index];
		if (Active.Mesh != InMesh || Active.Source.Get() != Reference.GetSourceObject() ||
			(MontageContext && Active.MontageInstanceId != MontageContext->MontageInstanceID) ||
			(AssetContext && Active.AssetPlayerInstanceId != AssetContext->AssetPlayerInstanceID)) continue;
		// The completed pair already transferred this exact transaction. Its old
		// montage task's ending callback cannot revoke the frozen corpse owner.
		if (Active.bCorpseMaterialOwner && CanHoldDeathVisualMaterials(Active)) continue;
		FMonsterVisualReceipt Previous = MoveTemp(MonsterVisuals[Index]);
		MonsterVisuals.RemoveAt(Index);
		if (UAnimNotifyLibrary::NotifyStateReachedEnd(Reference) && CanHoldDeathVisualMaterials(Previous))
		{
			Previous.bNotifyEnded = Previous.bTerminalMaterialHold = true;
			ReleaseMonsterVisual(Previous, false, true);Previous.Components.Reset();
			MonsterVisuals.Add(MoveTemp(Previous));
			continue;
		}
		RestoreVisualMaterials(Previous);RestoreVisualBindings(Previous);
		ReleaseMonsterVisual(Previous, false, false); // Actual animation end policy, not window end.
	}
}

bool AKZMonster::CanHoldDeathVisualMaterials(const FMonsterVisualReceipt& Receipt) const
{
	const UKZAnimNotifyState_MonsterVisual* Data = Receipt.Data.Get();
	if (!Data || Data->MaterialOverrides.IsEmpty() ||
		(Receipt.MaterialBindings.IsEmpty() && Receipt.MaterialWrites.IsEmpty()) ||
		!Receipt.Mesh.IsValid() || !Receipt.AnimInstance.IsValid() || Receipt.NotifyId == INDEX_NONE ||
		Receipt.Mesh->GetAnimInstance() != Receipt.AnimInstance.Get() || Receipt.MontageInstanceId == INDEX_NONE ||
		GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f) return false;
	// These are the exact original Apes execution consumer names, not a general
	// policy for arbitrary material states on dead actors.
	const FName Scalar = Data->ScalarParameterName.IsNone() ? Data->ScalarCurveName : Data->ScalarParameterName;
	if (Scalar != TEXT("Execution") && Scalar != TEXT("ExecutionO") &&
		Data->VectorParameterName != TEXT("ExecutionOffset_radius")) return false;
	if (Receipt.bCorpseMaterialOwner) return Receipt.Mesh->bPauseAnims;
	if (UKZExhaustionAbility* PairedOwner = Receipt.PairedMaterialOwner.Get())
	{
		if (!PairedOwner->IsActive() || PairedOwner != GetActiveExhaustionAbility() || PairedOwner->IsAvailableForBrutalAttack()) return false;
		const FKZMonsterStaminaSettings& Settings = GetCharacterDefinition()->GetMonsterStaminaSettings();
		UAnimMontage* Current = PairedOwner->GetCurrentMontage();
		if (Current && Current != Settings.BrutalFrontVictimMontage && Current != Settings.BrutalBackVictimMontage) return false;
		// Keep the exact naturally ended execution receipt while the two real
		// partners complete. Cancelled window/context callbacks still restore it.
		return PairedOwner->HasBrutalPartner() || Receipt.bNotifyEnded;
	}
	if (Receipt.AnimInstance != DeathPresentationAnim || Receipt.MontageInstanceId != DeathPresentationInstanceId) return false;
	UAnimInstance* Anim = DeathPresentationAnim.Get();
	const FAnimMontageInstance* Instance = Anim ? Anim->GetMontageInstanceForID(DeathPresentationInstanceId) : nullptr;
	return Instance && Instance->Montage == DeathPresentationMontage.Get() && !Instance->IsStopped();
}

void AKZMonster::RestoreVisualBindings(const FMonsterVisualReceipt& Receipt)
{
	for (const FVisualMaterialBinding& Binding : Receipt.MaterialBindings)
	{
		USkeletalMeshComponent* VisualMesh = Binding.MeshComponent.Get(); if (!VisualMesh) continue;
		UMaterialInterface* Current = Binding.Slot == INDEX_NONE ? VisualMesh->GetOverlayMaterial() : VisualMesh->GetMaterial(Binding.Slot);
		if (Current != Binding.Installed.Get()) continue; // A foreign material change owns its current value.
		UMaterialInterface* Restore = Binding.Baseline.Get();
		for (const FMonsterVisualReceipt& Active : MonsterVisuals)
			for (const FVisualMaterialBinding& Other : Active.MaterialBindings)
				if (Other.MeshComponent == VisualMesh && Other.Slot == Binding.Slot) Restore = Other.Installed.Get();
		if (Binding.Slot == INDEX_NONE) VisualMesh->SetOverlayMaterial(Restore);
		else VisualMesh->SetMaterial(Binding.Slot, Restore);
	}
}

void AKZMonster::ClearMonsterVisuals()
{
	check(IsInGameThread());
	TArray<FMonsterVisualReceipt> Previous = MoveTemp(MonsterVisuals);
	MonsterVisuals.Reset();
	// Reverse write order restores the common first baseline and preserves unrelated external writes.
	for (int32 Index = Previous.Num() - 1; Index >= 0; --Index)
	{
		RestoreVisualMaterials(Previous[Index]);
		RestoreVisualBindings(Previous[Index]);
		ReleaseMonsterVisual(Previous[Index], false, true);
	}
}
