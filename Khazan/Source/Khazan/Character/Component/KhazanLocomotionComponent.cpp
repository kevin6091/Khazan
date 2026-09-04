


#include "Character/Component/KhazanLocomotionComponent.h"

UKhazanLocomotionComponent::UKhazanLocomotionComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UKhazanLocomotionComponent::SetMoveInputWorld(const FVector& Input)
{
	if (Intent.bMovementAllowed == false)
	{
		ClearMoveInput();
		return;
	}
	
	const FVector Input2D(Input.X, Input.Y, 0.f);
	
	Intent.MoveInputWorld = Input2D.GetClampedToMaxSize(1.f);
	
	Intent.InputAmount = Intent.MoveInputWorld.Size2D();
}

void UKhazanLocomotionComponent::ClearMoveInput()
{
	Intent.MoveInputWorld = FVector::ZeroVector;
	Intent.InputAmount = 0.f;
}

void UKhazanLocomotionComponent::SetTargetGait(EKhazanGait Gait)
{
	Intent.TargetGait = Gait;
}

void UKhazanLocomotionComponent::SetMaxAllowedGait(EKhazanGait Gait)
{
	Intent.MaxAllowedGait = Gait;
}

void UKhazanLocomotionComponent::SetRotationMode(EKhazanRotationMode Mode)
{
	Intent.RotationMode = Mode;
}

void UKhazanLocomotionComponent::SetMovementAllowed(bool bAllowed)
{
	Intent.bMovementAllowed = bAllowed;
	if (bAllowed == false)
	{
		ClearMoveInput();
	}
}

EKhazanGait UKhazanLocomotionComponent::GetResolvedGait() const
{
	const uint8 TargetRank =
		static_cast<uint8>(Intent.TargetGait);

	const uint8 MaxAllowedRank =
		static_cast<uint8>(Intent.MaxAllowedGait);

	return TargetRank <= MaxAllowedRank
		? Intent.TargetGait
		: Intent.MaxAllowedGait;
}
