

#pragma once

#include "CoreMinimal.h"
#include "KhazanLocomotionType.generated.h"

UENUM(BlueprintType)
enum class EKhazanGait : uint8
{
	Walk,
	Run,
	Sprint
};

UENUM(BlueprintType)
enum class EKhazanRotationMode : uint8
{
	VelocityDirection,
	LookingDirection,
	LockOn
};

enum class EKhazanLocomotionMode : uint8
{
	Grounded,
	InAir
};

USTRUCT(BlueprintType)
struct FKhazanLocomotionIntent
{
	GENERATED_BODY()
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	FVector MoveInputWorld = FVector::ZeroVector;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	float InputAmount = 0.f;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanGait TargetGait = EKhazanGait::Run;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanGait MaxAllowedGait = EKhazanGait::Run;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	bool bMovementAllowed = true;
};
