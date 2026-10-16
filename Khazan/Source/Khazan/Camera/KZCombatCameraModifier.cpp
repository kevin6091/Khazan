#include "Camera/KZCombatCameraModifier.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"

UKZCombatCameraModifier* UKZCombatCameraModifier::GetOrCreate(APlayerController* Controller)
{
	if (!IsValid(Controller) || !Controller->IsLocalController() || !IsValid(Controller->PlayerCameraManager)) return nullptr;
	APlayerCameraManager* Manager = Controller->PlayerCameraManager;
	if (auto* Existing = Cast<UKZCombatCameraModifier>(Manager->FindCameraModifierByClass(StaticClass()))) return Existing;
	return Cast<UKZCombatCameraModifier>(Manager->AddNewCameraModifier(StaticClass()));
}

void UKZCombatCameraModifier::StartSourceShake(USkeletalMeshComponent* SourceMesh, int32 NotifyInstanceId,
	FName EventId, float ActiveSeconds, FVector RawAmplitudeCm, FVector RawFrequencyHz,
	float RawFOVAmplitudeDegrees, float RawFOVFrequencyHz, float SourceScale, float FinalScale,
	float FadeInSeconds, float FadeOutSeconds, float NearRadiusCm, float FarRadiusCm, FName DistanceBone)
{
	if (!IsValid(SourceMesh) || !GetWorld() || ActiveSeconds <= 0.f || SourceScale <= 0.f || FinalScale <= 0.f ||
		RawAmplitudeCm.ContainsNaN() || RawFrequencyHz.ContainsNaN()) return;
	EndSourceShake(SourceMesh, NotifyInstanceId);
	FActiveShake Shake;
	Shake.SourceMesh = SourceMesh;
	Shake.NotifyInstanceId = NotifyInstanceId;
	Shake.EventId = EventId;
	Shake.DistanceBone = DistanceBone;
	Shake.AmplitudeCm = RawAmplitudeCm * SourceScale * FinalScale;
	Shake.FOVAmplitudeDegrees = RawFOVAmplitudeDegrees * SourceScale * FinalScale;
	Shake.NearRadiusCm = FMath::Max(0.f, NearRadiusCm);
	Shake.FarRadiusCm = FMath::Max(0.f, FarRadiusCm);
	Shake.StartTime = GetWorld()->GetTimeSeconds();
	Shake.ActiveEndTime = Shake.StartTime + ActiveSeconds;
	ConfigureImpulse(Shake, FMath::Max(RawFrequencyHz.GetAbsMax(), FMath::Abs(RawFOVFrequencyHz)), FadeInSeconds, FadeOutSeconds);
	ActiveShakes.Add(MoveTemp(Shake));
}

void UKZCombatCameraModifier::BeginRelease(FActiveShake& Shake, double Now)
{
	if (Shake.ReleaseTime >= 0.) return;
	// Capture the exact force position, including early cancellation. Returning
	// never resumes a sine or jumps to a different phase at Notify End.
	const float Strength = Shake.LastAppliedStrength;
	Shake.ReleaseTranslation = Shake.AmplitudeCm * Strength;
	Shake.ReleaseFOVDegrees = Shake.FOVAmplitudeDegrees * Strength;
	Shake.ReleaseTime = Now;
}

void UKZCombatCameraModifier::ConfigureImpulse(FActiveShake& Shake, float FrequencyHz, float FadeInSeconds, float FadeOutSeconds)
{
	Shake.RiseSeconds = FMath::Max(MinimumImpulseRiseSeconds, FMath::Max(0.f, FadeInSeconds));
	Shake.ReturnSeconds = FMath::Max(MinimumImpulseReturnSeconds, FMath::Max(0.f, FadeOutSeconds));
	Shake.FadeOutSeconds = Shake.ReturnSeconds;
	// A zero-frequency source is one push. Sustained sources apply repeated
	// alternating pushes; every interval contains the complete linear return.
	Shake.ImpulseIntervalSeconds = FrequencyHz > 0.f ? FMath::Max(Shake.RiseSeconds + Shake.ReturnSeconds,
		1.f / FMath::Max(UE_SMALL_NUMBER, FMath::Min(FrequencyHz, MaximumImpulseRateHz))) : 0.f;
	FRandomStream Random(int32(HashCombine(GetTypeHash(Shake.EventId), ++ImpulseSerial)));
	const float Dominant = Shake.AmplitudeCm.GetAbsMax();
	for (int32 Axis = 0; Axis < 3; ++Axis)
	{
		if (FMath::IsNearlyZero(Shake.AmplitudeCm[Axis]))
			Shake.AmplitudeCm[Axis] = Dominant * CrossAxisFraction * Random.FRandRange(0.5f, 1.f) *
				(Random.FRand() < 0.5f ? -1.f : 1.f);
		else Shake.AmplitudeCm[Axis] *= Random.FRandRange(1.f - PerEventAmplitudeVariation, 1.f + PerEventAmplitudeVariation);
	}
	Shake.FOVAmplitudeDegrees *= Random.FRandRange(1.f - PerEventAmplitudeVariation, 1.f + PerEventAmplitudeVariation);
}

float UKZCombatCameraModifier::SampleImpulse(const FActiveShake& Shake, double Now) const
{
	const double Elapsed = FMath::Max(0., Now - Shake.StartTime);
	const int32 Impulse = Shake.ImpulseIntervalSeconds > 0.f ? FMath::FloorToInt(Elapsed / Shake.ImpulseIntervalSeconds) : 0;
	const float LocalTime = float(Elapsed - Impulse * double(Shake.ImpulseIntervalSeconds));
	const float Strength = LocalTime < Shake.RiseSeconds ? LocalTime / Shake.RiseSeconds :
		1.f - FMath::Clamp((LocalTime - Shake.RiseSeconds) / Shake.ReturnSeconds, 0.f, 1.f);
	return (Impulse % 2 == 0 ? 1.f : -1.f) * Strength;
}

void UKZCombatCameraModifier::EndSourceShake(USkeletalMeshComponent* SourceMesh, int32 NotifyInstanceId)
{
	if (!GetWorld()) return;
	const double Now = GetWorld()->GetTimeSeconds();
	for (FActiveShake& Shake : ActiveShakes)
		if (!Shake.bParry && Shake.SourceMesh == SourceMesh && Shake.NotifyInstanceId == NotifyInstanceId)
			BeginRelease(Shake, Now);
}

void UKZCombatCameraModifier::StartParryShake(float ActiveSeconds, FVector RawAmplitudeCm, FVector RawFrequencyHz,
	float RawFOVAmplitudeDegrees, float RawFOVFrequencyHz, float FinalScale,
	float FadeInSeconds, float FadeOutSeconds)
{
	if (!GetWorld() || ActiveSeconds <= 0.f || FinalScale <= 0.f) return;
	FActiveShake Shake;
	Shake.bParry = true;
	Shake.EventId = TEXT("JustGuard");
	Shake.AmplitudeCm = RawAmplitudeCm * FinalScale;
	Shake.FOVAmplitudeDegrees = RawFOVAmplitudeDegrees * FinalScale;
	Shake.StartTime = GetWorld()->GetTimeSeconds();
	Shake.ActiveEndTime = Shake.StartTime + ActiveSeconds;
	ConfigureImpulse(Shake, FMath::Max(RawFrequencyHz.GetAbsMax(), FMath::Abs(RawFOVFrequencyHz)), FadeInSeconds, FadeOutSeconds);
	ActiveShakes.Add(MoveTemp(Shake));
}

int32 UKZCombatCameraModifier::GetActiveParryShakeCount() const
{
	int32 Count = 0;
	for (const FActiveShake& Shake : ActiveShakes) Count += Shake.bParry ? 1 : 0;
	return Count;
}

int32 UKZCombatCameraModifier::GetActiveSourceShakeCount() const
{
	int32 Count = 0;
	for (const FActiveShake& Shake : ActiveShakes) Count += Shake.bParry ? 0 : 1;
	return Count;
}

int32 UKZCombatCameraModifier::GetActiveSourceShakeCountForMesh(const USkeletalMeshComponent* Mesh) const
{
	int32 Count = 0;
	for (const FActiveShake& Shake : ActiveShakes)
		Count += !Shake.bParry && Shake.SourceMesh.Get() == Mesh ? 1 : 0;
	return Count;
}

void UKZCombatCameraModifier::ModifyCamera(float DeltaTime, FVector ViewLocation, FRotator ViewRotation,
	float FOV, FVector& NewViewLocation, FRotator& NewViewRotation, float& NewFOV)
{
	if (!GetWorld()) return;
	const double Now = GetWorld()->GetTimeSeconds();
	FVector LocalOffset = FVector::ZeroVector;
	float FOVOffset = 0.f;
	for (int32 Index = ActiveShakes.Num() - 1; Index >= 0; --Index)
	{
		FActiveShake& Shake = ActiveShakes[Index];
		if (Shake.ReleaseTime < 0. && Now >= Shake.ActiveEndTime) BeginRelease(Shake, Shake.ActiveEndTime);
		if (Shake.ReleaseTime < 0. && !Shake.bParry && !Shake.SourceMesh.IsValid()) BeginRelease(Shake, Now);
		if (Shake.ReleaseTime >= 0. && (Shake.FadeOutSeconds <= 0.f || Now >= Shake.ReleaseTime + Shake.FadeOutSeconds))
		{
			ActiveShakes.RemoveAtSwap(Index, 1, EAllowShrinking::No);
			continue;
		}
		float DistanceScale = 1.f;
		if (!Shake.bParry && Shake.SourceMesh.IsValid() && Shake.FarRadiusCm > 0.f)
		{
			const USkeletalMeshComponent* Source = Shake.SourceMesh.Get();
			const FVector Origin = !Shake.DistanceBone.IsNone() && Source->DoesSocketExist(Shake.DistanceBone) ?
				Source->GetSocketLocation(Shake.DistanceBone) : Source->GetComponentLocation();
			const float Distance = FVector::Distance(Origin, ViewLocation);
			DistanceScale = Shake.FarRadiusCm > Shake.NearRadiusCm ?
				1.f - FMath::Clamp((Distance - Shake.NearRadiusCm) / (Shake.FarRadiusCm - Shake.NearRadiusCm), 0.f, 1.f) :
				(Distance <= Shake.FarRadiusCm ? 1.f : 0.f);
		}
		if (Shake.ReleaseTime >= 0.)
		{
			const float Return = 1.f - FMath::Clamp(float(Now - Shake.ReleaseTime) / Shake.FadeOutSeconds, 0.f, 1.f);
			LocalOffset += Shake.ReleaseTranslation * Return;
			FOVOffset += Shake.ReleaseFOVDegrees * Return;
		}
		else
		{
			const float Strength = SampleImpulse(Shake, Now) * DistanceScale;
			Shake.LastAppliedStrength = Strength;
			LocalOffset += Shake.AmplitudeCm * Strength;
			FOVOffset += Shake.FOVAmplitudeDegrees * Strength;
		}
	}
	LocalOffset = LocalOffset.GetClampedToMaxSize(FMath::Max(0.f, MaxCombinedTranslationCm));
	LastLocalTranslation = LocalOffset;
	NewViewLocation = ViewLocation + ViewRotation.RotateVector(LocalOffset);
	NewFOV = FOV + FMath::Clamp(FOVOffset, -MaxCombinedFOVDegrees, MaxCombinedFOVDegrees);
	NewViewRotation = ViewRotation;
}
