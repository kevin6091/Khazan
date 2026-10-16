#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Curves/CurveFloat.h"
#include "KZAnimNotifyState_MonsterVisual.generated.h"

class UKZAnimNotify_CombatEffect;
class UMaterialInterface;

USTRUCT(BlueprintType)
struct FKZMonsterVisualMaterialOverride
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TObjectPtr<UMaterialInterface> SourceMaterial = nullptr;
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TObjectPtr<UMaterialInterface> ReplacementMaterial = nullptr;
};

// Immutable authored occurrence. Runtime resources belong to the actual Monster.
UCLASS(EditInlineNew, meta = (DisplayName = "KZ Monster Visual"))
class KHAZAN_API UKZAnimNotifyState_MonsterVisual : public UAnimNotifyState
{
	GENERATED_BODY()
public:
	UKZAnimNotifyState_MonsterVisual();
	virtual void NotifyBegin(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
		float TotalDuration, const FAnimNotifyEventReference& Reference) override;
	virtual void NotifyTick(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
		float DeltaSeconds, const FAnimNotifyEventReference& Reference) override;
	virtual void NotifyEnd(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
		const FAnimNotifyEventReference& Reference) override;

	// Technical full-clip lifetime adapter. No gameplay state or source visual event.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Lifetime")
	bool bAnimationContextBoundary = false;
	// xxAnimNotifyState_CameraMod is an independent original presentation window.
	// These fields are raw source values (cm, Hz, seconds); no VFX receipt is made.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera")
	bool bSourceCameraShake = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera")
	FName CameraEventId = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "cm"))
	FVector CameraAmplitudeCm = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "Hz"))
	FVector CameraFrequencyHz = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "deg"))
	float CameraFOVAmplitudeDegrees = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "Hz"))
	float CameraFOVFrequencyHz = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera")
	float CameraShakeScale = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera")
	float CameraFinalScale = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "s"))
	float CameraFadeInSeconds = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "s"))
	float CameraFadeOutSeconds = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "cm"))
	float CameraNearRadiusCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera", meta = (Units = "cm"))
	float CameraFarRadiusCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Camera")
	FName CameraDistanceBone = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	TObjectPtr<UMaterialInterface> MaterialOverlay = nullptr;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	TArray<FKZMonsterVisualMaterialOverride> MaterialOverrides;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Instanced, Category = "Monster Visual")
	TObjectPtr<UKZAnimNotify_CombatEffect> Effect;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	FName BoneName = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	FName VectorParameterName = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	FName ScalarCurveName = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	FName ScalarParameterName = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	bool bUseScalarCurve = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Monster Visual|Material")
	FRuntimeFloatCurve ScalarCurve;
};
