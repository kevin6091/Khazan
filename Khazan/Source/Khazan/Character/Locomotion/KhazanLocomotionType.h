

#pragma once

#include "CoreMinimal.h"
#include "KhazanLocomotionType.generated.h"

UENUM(BlueprintType)
enum class EKhazanGait : uint8
{
	Walk = 0,
	Run = 1,
	Sprint = 2
};

UENUM(BlueprintType)
enum class EKhazanRotationMode : uint8
{
	VelocityDirection,
	LookingDirection,
	LockOn
};

UENUM(BlueprintType)
enum class EKhazanLocomotionIntentSource : uint8
{
	None,
	PlayerController,
	AIController
};

enum class EKhazanLocomotionMode : uint8
{
	Grounded,
	InAir
};

UENUM(BlueprintType)
enum class EKhazanFoot : uint8
{
	None,
	Left,
	Right
};

// 이 캐릭터는 원래 어느 정도로 움직일 수 있는가? 캐릭터에 대한 정보.
USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanLocomotionConfig
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0.0"))
	float WalkSpeed = 170.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0.0"))
	float RunSpeed = 470.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0.0"))
	float SprintSpeed = 600.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.0"))
	float MinAnalogWalkSpeed = 15.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.0"))
	float MaxAcceleration = 1800.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.0"))
	float BrakingDecelerationWalking = 1800.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rotation")
	FRotator RotationRate = FRotator(0.f, 540.f, 0.f);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
	EKhazanGait DefaultTargetGait = EKhazanGait::Walk;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
	EKhazanGait DefaultMaxAllowedGait = EKhazanGait::Sprint;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
	EKhazanRotationMode DefaultRotationMode = EKhazanRotationMode::VelocityDirection;

	bool IsValid(FString& OutError) const;
	float GetSpeedForGait(EKhazanGait Gait) const;
};

// 현재 Controller는 무엇을 하고 싶어 하는가?
USTRUCT(BlueprintType)
struct FKhazanLocomotionIntent
{
	GENERATED_BODY()
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	FVector MoveInputWorld = FVector::ZeroVector;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	float InputAmount = 0.f;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanGait TargetGait = EKhazanGait::Walk;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanRotationMode RequestedRotationMode = EKhazanRotationMode::VelocityDirection;
};

// 하나의 원인이 기여하는 이동 제약
USTRUCT(BlueprintType)
struct FKhazanMovementConstraint
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion")
	EKhazanGait MaxAllowedGait = EKhazanGait::Sprint;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion")
	bool bOverrideRotationMode = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion", meta = (EditCondition = "bOverrideRotationMode"))
	EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion", meta = (EditCondition = "bOverrideRotationMode"))
	int32 RotationPriority = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion")
	FName DebugName = NAME_None;
};

// 모든 기본값, 요청, 제한, 태그를 합쳤을 때 실제로 무엇을 적용할 것인가? 적용할 최종 결과
USTRUCT(BlueprintType)
struct FKhazanResolvedMovementPolicy
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	bool bMovementAllowedByTags = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanGait MaxAllowedGait = EKhazanGait::Sprint;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanGait ResolvedGait = EKhazanGait::Walk;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	float MaxWalkSpeed = 0.f;
};