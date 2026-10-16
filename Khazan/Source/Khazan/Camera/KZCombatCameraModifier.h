#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraModifier.h"
#include "KZCombatCameraModifier.generated.h"

class APlayerController;
class USkeletalMeshComponent;

// Original xxCameraMod_Shake values stay in the notify/Guard data. This is the
// local, finite camera adapter for the unrecovered custom game modifier.
UCLASS()
class KHAZAN_API UKZCombatCameraModifier : public UCameraModifier
{
	GENERATED_BODY()
public:
	static UKZCombatCameraModifier* GetOrCreate(APlayerController* Controller);

	void StartSourceShake(USkeletalMeshComponent* SourceMesh, int32 NotifyInstanceId, FName EventId,
		float ActiveSeconds, FVector RawAmplitudeCm, FVector RawFrequencyHz,
		float RawFOVAmplitudeDegrees, float RawFOVFrequencyHz, float SourceScale, float FinalScale,
		float FadeInSeconds, float FadeOutSeconds, float NearRadiusCm, float FarRadiusCm,
		FName DistanceBone = NAME_None);
	void EndSourceShake(USkeletalMeshComponent* SourceMesh, int32 NotifyInstanceId);

	// An approved parry outlives the Guard Ability; the modifier expires it.
	void StartParryShake(float ActiveSeconds, FVector RawAmplitudeCm, FVector RawFrequencyHz,
		float RawFOVAmplitudeDegrees, float RawFOVFrequencyHz, float FinalScale,
		float FadeInSeconds, float FadeOutSeconds);
	int32 GetActiveParryShakeCount() const;
	int32 GetActiveSourceShakeCount() const;
	int32 GetActiveSourceShakeCountForMesh(const USkeletalMeshComponent* Mesh) const;
	FVector GetLastLocalTranslation() const { return LastLocalTranslation; }

protected:
	virtual void ModifyCamera(float DeltaTime, FVector ViewLocation, FRotator ViewRotation, float FOV,
		FVector& NewViewLocation, FRotator& NewViewRotation, float& NewFOV) override;

private:
	struct FActiveShake
	{
		TWeakObjectPtr<USkeletalMeshComponent> SourceMesh;
		int32 NotifyInstanceId = INDEX_NONE;
		FName EventId;
		FName DistanceBone;
		FVector AmplitudeCm = FVector::ZeroVector;
		FVector ReleaseTranslation = FVector::ZeroVector;
		float FOVAmplitudeDegrees = 0.f;
		float ReleaseFOVDegrees = 0.f;
		float LastAppliedStrength = 0.f;
		float RiseSeconds = 0.f;
		float ReturnSeconds = 0.f;
		float ImpulseIntervalSeconds = 0.f;
		float NearRadiusCm = 0.f;
		float FarRadiusCm = 0.f;
		double StartTime = 0.;
		double ActiveEndTime = 0.;
		double ReleaseTime = -1.;
		float FadeOutSeconds = 0.f;
		bool bParry = false;
	};

	void BeginRelease(FActiveShake& Shake, double Now);
	void ConfigureImpulse(FActiveShake& Shake, float FrequencyHz, float FadeInSeconds, float FadeOutSeconds);
	float SampleImpulse(const FActiveShake& Shake, double Now) const;
	TArray<FActiveShake> ActiveShakes;
	FVector LastLocalTranslation = FVector::ZeroVector;
	uint32 ImpulseSerial = 0;

	// Assistant TEMP display tunings: original custom modifier executable and
	// source randomization policy are unavailable. These never alter raw data.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary")
	float PerEventAmplitudeVariation = 0.12f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary")
	float CrossAxisFraction = 0.06f;
	// User-requested linear force/return. TEMP display seconds/rate; source
	// high-frequency sine values remain saved on the producers, not sampled directly.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary", meta = (ClampMin = "0.001", Units = "s"))
	float MinimumImpulseRiseSeconds = 0.08f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary", meta = (ClampMin = "0.001", Units = "s"))
	float MinimumImpulseReturnSeconds = 0.16f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary", meta = (ClampMin = "0.001", Units = "Hz"))
	float MaximumImpulseRateHz = 4.f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary", meta = (Units = "cm"))
	float MaxCombinedTranslationCm = 90.f;
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Camera|Temporary", meta = (Units = "deg"))
	float MaxCombinedFOVDegrees = 2.f;
};
