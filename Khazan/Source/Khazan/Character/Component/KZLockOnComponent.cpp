#include "Character/Component/KZLockOnComponent.h"

#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "CollisionQueryParams.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"

UKZLockOnComponent::UKZLockOnComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
}

void UKZLockOnComponent::ToggleLockOn()
{
	// target, handle 중 하나라도 남아있다면 Toggle해제

	if (CurrentTarget.IsValid() || LockOnConstraintHandle.IsValid())
	{
		StopLockOn();
		return;
	}

	// LockOn이 아니므로 Toggle 활성
	if (AKZMonster* NewTarget = FindBestLockOnTarget())
	{
		StartLockOn(NewTarget);
	}
}

AKZMonster* UKZLockOnComponent::FindBestLockOnTarget() const
{
	UWorld* World = GetWorld();
	AKZPlayer* Player = Cast<AKZPlayer>(GetOwner());

	if (!World || !IsValid(Player) || !Player->IsLocallyControlled())
	{
		return nullptr;
	}

	APlayerController* PlayerController = Cast<APlayerController>(Player->GetController());

	if (!IsValid(PlayerController))
	{
		return nullptr;
	}

	int32 ViewportWidth = 0;
	int32 ViewportHeight = 0;
	PlayerController->GetViewportSize(ViewportWidth, ViewportHeight);

	if (ViewportWidth <= 0 || ViewportHeight <= 0)
	{
		return nullptr;
	}

	FVector ViewLocation;
	FRotator ViewRotation;
	PlayerController->GetPlayerViewPoint(ViewLocation, ViewRotation);

	const FVector ViewForward = ViewRotation.Vector();

	const double HalfWidth = static_cast<double>(ViewportWidth) * 0.5;
	const double HalfHeight = static_cast<double>(ViewportHeight) * 0.5;

	AKZMonster* BestTarget = nullptr;
	double BestCenterScore = TNumericLimits<double>::Max();
	double BestCameraDistanceSquared = TNumericLimits<double>::Max();

	for (TActorIterator<AKZMonster> It(World); It; ++It)
	{
		AKZMonster* CandidateMonster = *It;

		if (!IsValid(CandidateMonster) || CandidateMonster->IsHidden())
		{
			continue;
		}

		const USceneComponent* TargetPoint = CandidateMonster->GetLockOnTargetPoint();

		if (!IsValid(TargetPoint))
		{
			continue;
		}

		const FVector TargetLocation = TargetPoint->GetComponentLocation();
		const FVector ToTarget = TargetLocation - ViewLocation;

		if (ToTarget.IsNearlyZero())
		{
			continue;
		}

		// 내적이 0이하면 카메라의 옆 또는 뒤에 있다. LockOn 안함.
		if (FVector::DotProduct(ViewForward, ToTarget) <= 0.0)
		{
			continue;
		}

		FVector2D ScreenPosition;

		if (!PlayerController->ProjectWorldLocationToScreen(TargetLocation, ScreenPosition, true) ||
			ScreenPosition.X < 0.0 ||
			ScreenPosition.X > static_cast<double>(ViewportWidth) ||
			ScreenPosition.Y < 0.0 ||
			ScreenPosition.Y > static_cast<double>(ViewportHeight) ||
			!HasClearViewToTarget(ViewLocation, CandidateMonster, TargetLocation))
		{
			continue;
		}

		const double NormalizedX = (ScreenPosition.X - HalfWidth) / HalfWidth;

		const double NormalizedY = (ScreenPosition.Y - HalfHeight) / HalfHeight;

		const double CenterScore = NormalizedX * NormalizedX + NormalizedY * NormalizedY;

		const double CameraDistanceSquared = FVector::DistSquared(ViewLocation, TargetLocation);

		const bool bScoresEquivalent = FMath::IsNearlyEqual(CenterScore, BestCenterScore);

		const bool bCenterScoreIsBetter = !bScoresEquivalent && CenterScore < BestCenterScore;

		const bool bTieBreakIsBetter = bScoresEquivalent && CameraDistanceSquared < BestCameraDistanceSquared;

		if (bCenterScoreIsBetter || bTieBreakIsBetter)
		{
			BestTarget = CandidateMonster;
			BestCenterScore = CenterScore;
			BestCameraDistanceSquared = CameraDistanceSquared;
		}
	}

	return BestTarget;
}

bool UKZLockOnComponent::HasClearViewToTarget(const FVector& ViewLocation, const AKZMonster* CandidateMonster,
                                              const FVector& TargetLocation) const
{
	UWorld* World = GetWorld();

	if (!World || !IsValid(CandidateMonster))
	{
		return false;
	}

	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(KZLockOnVisibility), false);

	// 플레이어 자신의 Capsule이나 Mesh가 카메라 선을 막지 않게 한다.
	QueryParams.AddIgnoredActor(GetOwner());

	FHitResult HitResult;

	const bool bHitBlockingObject = World->LineTraceSingleByChannel(
		HitResult,
		ViewLocation,
		TargetLocation,
		ECC_Visibility,
		QueryParams);

	// 목표 지점까지 아무것도 막지 않았다.
	if (!bHitBlockingObject)
	{
		return true;
	}

	// 타깃 자신의 Capsule 또는 Mesh에 먼저 맞은 경우도 보이는 것으로 인정한다.
	return HitResult.GetActor() == CandidateMonster;
}

bool UKZLockOnComponent::StartLockOn(AKZMonster* Target)
{
	AKZPlayer* Player = Cast<AKZPlayer>(GetOwner());

	if (!IsValid(Player) ||
		!Player->IsLocallyControlled() ||
		!IsValid(Target) ||
		Target->GetWorld() != GetWorld() ||
		!IsValid(Target->GetLockOnTargetPoint()) ||
		!IsValid(Cast<APlayerController>(Player->GetController())))
	{
		return false;
	}

	UKZLocomotionComponent* Locomotion = Player->GetLocomotionComponent();

	if (!IsValid(Locomotion))
	{
		return false;
	}

	// 방어적으로 이전의 부분 상태를 먼저 정리한다.
	StopLockOn();

	FKZMovementConstraint Constraint;

	// 현재 LockOn pose 범위에는 Sprint loop가 없으므로 Run으로 제한한다.
	Constraint.MaxAllowedGait = EKZGait::Run;
	Constraint.bOverrideRotationMode = true;
	Constraint.RotationModeOverride = EKZRotationMode::LockOn;

	// 원작 gameplay 값이 아니라 현재 제약 충돌 해결용 기술 우선순위다.
	Constraint.RotationModeOverridePriority = 0;
	Constraint.DebugName = TEXT("LockOn");

	FKZMovementConstraintHandle NewHandle = Locomotion->AcquireMovementConstraint(this, Constraint);

	if (!NewHandle.IsValid())
	{
		return false;
	}

	// 제약 획득이 성공한 뒤에만 잠금 상태를 확정한다.
	CurrentTarget = Target;
	LockOnConstraintHandle = MoveTemp(NewHandle);

	SetComponentTickEnabled(true);

	return true;
}

void UKZLockOnComponent::StopLockOn()
{
	if (LockOnConstraintHandle.IsValid())
	{
		if (AKZPlayer* Player = Cast<AKZPlayer>(GetOwner()))
		{
			if (UKZLocomotionComponent* Locomotion = Player->GetLocomotionComponent())
			{
				Locomotion->ReleaseMovementConstraint(LockOnConstraintHandle);
			}
		}
	}

	// Release가 실패했거나 LocomotionComponent가 이미 종료된 경우도
	// 지역 상태는 반드시 비운다.
	LockOnConstraintHandle.Reset();
	CurrentTarget.Reset();

	SetComponentTickEnabled(false);
}

bool UKZLockOnComponent::IsLockedOn() const
{
	return CurrentTarget.IsValid() && LockOnConstraintHandle.IsValid();
}


void UKZLockOnComponent::UpdateLockOnFacing(float DeltaTime)
{
	if (!IsLockedOn())
	{
		StopLockOn();
		return;
	}

	AKZPlayer* Player = Cast<AKZPlayer>(GetOwner());
	AKZMonster* Target = CurrentTarget.Get();

	if (!IsValid(Player) || !IsValid(Target) || !Player->IsLocallyControlled())
	{
		StopLockOn();
		return;
	}

	APlayerController* PlayerController = Cast<APlayerController>(Player->GetController());

	const USceneComponent* TargetPoint = Target->GetLockOnTargetPoint();

	if (!IsValid(PlayerController) || !IsValid(TargetPoint))
	{
		StopLockOn();
		return;
	}

	const FVector TargetLocation = TargetPoint->GetComponentLocation();
	const FVector PivotLocation = Player->GetActorLocation() + FVector(0, 0, 300.f);
	const FVector ToTarget = TargetLocation - PivotLocation;

	if (ToTarget.IsNearlyZero())
	{
		return;
	}

	FRotator DesiredControlRotation = ToTarget.Rotation();
	// 높이 차(cm)가 아니라 Pitch(도)를 제한해야 가까운 거리에서도 같은 시야 한계가 유지된다.
	DesiredControlRotation.Pitch = FMath::Max(DesiredControlRotation.Pitch, -MaxLookDownAngleDegrees);
	DesiredControlRotation.Roll = 0.0f;

	const FRotator SmoothedControlRotation =
		FMath::RInterpTo(PlayerController->GetControlRotation(), DesiredControlRotation, DeltaTime, LockOnViewInterpSpeed);

	// 잠금 직전의 시선이 이미 하한보다 아래였더라도 LockOn 중에는 그 각도를 넘지 않는다.
	const double ClampedPitch = FMath::Max(
		FRotator::NormalizeAxis(SmoothedControlRotation.Pitch), -30);
	PlayerController->SetControlRotation(FRotator(ClampedPitch, SmoothedControlRotation.Yaw, 0.0f));
}

void UKZLockOnComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	UpdateLockOnFacing(DeltaTime);
}

void UKZLockOnComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopLockOn();

	Super::EndPlay(EndPlayReason);
}
