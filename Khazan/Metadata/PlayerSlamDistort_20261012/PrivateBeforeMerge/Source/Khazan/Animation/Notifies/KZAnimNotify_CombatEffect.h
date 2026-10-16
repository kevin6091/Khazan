#pragma once

#include "CoreMinimal.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "Chaos/ChaosEngineInterface.h"
#include "Curves/CurveVector.h"
#include "KZAnimNotify_CombatEffect.generated.h"

class UParticleSystem;
class UNiagaraSystem;
class UMaterialInterface;
class UStaticMesh;
class USceneComponent;
class USkeletalMeshComponent;

USTRUCT(BlueprintType)
struct FKZCombatEffectFloatParameter
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	FName ParameterName = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	float Minimum = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	float Maximum = 0.f;

	// Decal scalar source bRandomFloat=false is sampled as an integer range.
	// Particle distribution parameters continue using their original range API.
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	bool bRandomInteger = false;
};

USTRUCT(BlueprintType)
struct FKZCombatEffectSurfaceRoute
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TEnumAsByte<EPhysicalSurface> Surface = SurfaceType_Default;

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TObjectPtr<UParticleSystem> ParticleTemplate = nullptr;
	// Source explicitly null surface route suppresses emission; not a missing asset.
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	bool bSuppressParticle = false;


	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TObjectPtr<UMaterialInterface> DecalMaterial = nullptr;
	// Explicit source Material=None is suppression, never a fallback decal.
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	bool bSuppressDecal = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TArray<FKZCombatEffectFloatParameter> FloatParameters;
};

// Data only: the inherited branching-point callback reaches the owning ComboAction.
// Unserialized source CDO defaults are unknown. The defaults here are adapter
// defaults, not verified original-game values; authoring records that distinction.
UCLASS(EditInlineNew, meta = (DisplayName = "KZ Combat Effect"))
class KHAZAN_API UKZAnimNotify_CombatEffect : public UAnimNotify_PlayMontageNotify
{
	GENERATED_BODY()
public:
	UKZAnimNotify_CombatEffect(const FObjectInitializer& ObjectInitializer);

	// Stateless renderer shared by Action and the actual Monster animation owner.
	// PSCs return inactive so their owner installs its receipt before activation.
	static USceneComponent* SpawnComponent(const UKZAnimNotify_CombatEffect& Effect,
		USkeletalMeshComponent* Mesh, bool bConfirmedHit = false,
		float RecoveredWindowDuration = 0.f, float SourceTime = 0.f);
	FTransform SampleSourceCorrection(float SourceTime) const;

	// UE supports only one branching marker per trigger time. Same-time source
	// start/end entries are data children; they never become separate markers.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Instanced, Category = "KZ|Effect")
	TArray<TObjectPtr<UKZAnimNotify_CombatEffect>> BatchedEffects;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	TObjectPtr<UParticleSystem> ParticleTemplate = nullptr;

	// Uses the same floor transform and action-owned start/end receipt as Cascade.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	TObjectPtr<UNiagaraSystem> NiagaraTemplate = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Decal")
	TObjectPtr<UMaterialInterface> DecalMaterial = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Decal", meta = (Units = "cm"))
	FVector DecalSize = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Decal", meta = (Units = "s"))
	float DecalLifeSpan = 0.f;

	// Technical material registry, not a tuning value: 0 FadeOut,
	// 1 SlowIn, 2 FastIn_SlowOut, 3 Fast. No source curve is INDEX_NONE.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Decal")
	int32 DecalOpacityCurveIndex = INDEX_NONE;

	// Source random-vector minima/maxima are additive offsets to BasedVector.
	// This interpretation and omitted source CDO defaults are recorded by authoring.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Decal")
	FVector DecalSizeRandomMin = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Decal")
	FVector DecalSizeRandomMax = FVector::ZeroVector;

	// Unique source-event occurrence, including authored segment/loop occurrence.
	// The paired start and stop must carry the same ID.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	FName EventId = NAME_None;

	// Authored absolute montage seconds, from the mapped source occurrence.
	// These data boundaries match the producer's sampled montage time on slow frames.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect", meta = (Units = "s"))
	float WindowStartTime = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect", meta = (Units = "s"))
	float WindowEndTime = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bEndEvent = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	FName SourceSocket = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect", meta = (Units = "cm"))
	FVector RelativeLocation = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect", meta = (Units = "cm"))
	FVector RelativeLocationRandomMin = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect", meta = (Units = "cm"))
	FVector RelativeLocationRandomMax = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	FRotator RelativeRotation = FRotator::ZeroRotator;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	FRotator RelativeRotationRandomMin = FRotator::ZeroRotator;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	FRotator RelativeRotationRandomMax = FRotator::ZeroRotator;

	// Explicit source Scale3D takes precedence. Only a scalar-only source is
	// authored uniformly; do not multiply a legacy scalar into explicit Scale3D.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	FVector Scale3D = FVector::OneVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	float CustomTimeDilation = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bAttached = false;

	// Adapter interpretation: anchor once at the source socket, then world-space.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bOnlyStartAttach = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool OnNotifyEndDeattach = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bAbsoluteRotation = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	int32 TranslucencySortPriority = 0;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bSpawnOnFloor = false;

	// Read-only project adapter: a snow-deformation actor identifies a winter
	// level. The original EnvVolumeBundle selection code is not available.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bWinterOnly = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bDestroyOnNotifyEnd = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bDestroyOnNotifyEndDeactived = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bDestroyOnAnimEnd = false;

	// Requires a real confirmed project HP hit in the owning attack execution.
	// Begin can consume an earlier confirmed observation; collision reset clears
	// that observation and EventId playback deduplication. Source BattleEffectIndex
	// linkage is unavailable: any HP hit in the current node is a project adapter.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bOnAttackSuccessed = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	TArray<FKZCombatEffectSurfaceRoute> SurfaceRoutes;

	// Optional authoring adapter for surfaces lacking a project PhysMaterial.
	// Disabled unless the source-to-project surface mapping is established.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	bool bOverrideSurface = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	TEnumAsByte<EPhysicalSurface> SurfaceOverride = SurfaceType_Default;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect")
	TArray<FKZCombatEffectFloatParameter> InstanceParameters;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	bool bUseSourceCorrection = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	FName CorrectionBoneName = NAME_None;

	// Optional first-snapshot anchoring is an adapter interpretation; original
	// game code has not been recovered. See the paired source package/field.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	FTransform SourceCorrectionTransform = FTransform::Identity;

	// Full recovered keys use mapped sequence-local seconds. Euler xyz are Roll/Pitch/Yaw degrees.
	// Missing source anchor remains disabled; authoring preserves the unsupported raw correction.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	bool bUseCorrectionCurves = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	FRuntimeVectorCurve SourceCorrectionTranslation;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	FRuntimeVectorCurve SourceCorrectionRotation;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Correction")
	FRuntimeVectorCurve SourceCorrectionScale;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail")
	TObjectPtr<UStaticMesh> TrailMesh = nullptr;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail")
	TObjectPtr<UMaterialInterface> TrailMaterial = nullptr;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail")
	float TrailIntensity = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail", meta = (Units = "s"))
	float TrailBlendTime = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail")
	int32 TrailCreateCount = 0;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail")
	bool bDeepSnowTrail = false;
	// Explicit material adapter name, not recovered original native behavior.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Trail")
	FName TrailIntensityParameter = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Source")
	FString SourcePackage;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KZ|Effect|Source")
	FString SourceField;
};
