

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

/**
 * 로코모션 enum의 지원 범위와 gait 제한 순서를 정의하는 공통 규칙이다.
 *
 * Config 검증과 LocomotionComponent가 같은 규칙을 사용한다.
 * 상태를 보관하지 않으며 Game Thread 전용 함수도 아니다.
 */
namespace KhazanLocomotion
{
	// enum 저장 숫자와 별개인 현재 gameplay gait 제한 순서를 반환한다.
	// 지원하지 않는 값에는 INDEX_NONE을 반환한다.
	KHAZAN_API int32 GetGaitRestrictionRank(const EKhazanGait Gait);

	// 현재 로코모션 계약에서 처리할 수 있는 gait인지 확인한다.
	KHAZAN_API bool IsSupportedGait(const EKhazanGait Gait);

	// 현재 로코모션 계약에서 처리할 수 있는 회전 모드인지 확인한다.
	KHAZAN_API bool IsSupportedRotationMode(const EKhazanRotationMode Mode);
}


// 누가 Intent를 작성했는지
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
	EKhazanGait DefaultRequestedGait = EKhazanGait::Walk;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
	EKhazanGait DefaultMaxAllowedGait = EKhazanGait::Sprint;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
	EKhazanRotationMode DefaultRequestedRotationMode = EKhazanRotationMode::VelocityDirection;

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
	EKhazanGait RequestedGait = EKhazanGait::Walk;
	
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
	EKhazanRotationMode RotationModeOverride = EKhazanRotationMode::VelocityDirection;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion", meta = (EditCondition = "bOverrideRotationMode"))
	int32 RotationModeOverridePriority = 0;

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
	EKhazanRotationMode ResolvedRotationMode = EKhazanRotationMode::VelocityDirection;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
	float MaxWalkSpeed = 0.f;
};
