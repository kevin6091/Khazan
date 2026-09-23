

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Character/Locomotion/KZLocomotionType.h"
#include "Engine/EngineTypes.h"
#include "KZAnimInstance.generated.h"

class AKZCharacter;
class UCharacterMovementComponent;

struct FKZAnimGameThreadData
{
	bool bValid = false;

	FRotator ActorRotation = FRotator::ZeroRotator;

	FVector VelocityWorld = FVector::ZeroVector;
	FVector AccelerationWorld = FVector::ZeroVector;
	FVector MoveInputWorld = FVector::ZeroVector;

	float InputAmount = 0.f;
	float MaxAcceleration = 0.f;
	float MaxBrakingDeceleration = 0.f;

	TEnumAsByte<EMovementMode> MovementMode = MOVE_None;

	EKZGait RequestedGait = EKZGait::Run;
	EKZGait MaxAllowedGait = EKZGait::Run;
	EKZGait ResolvedGait = EKZGait::Run;

	EKZRotationMode RotationMode = EKZRotationMode::VelocityDirection;

	bool bMovementAllowed = true;
};

class UKZLocomotionComponent;

UCLASS()
class KHAZAN_API UKZAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	UKZAnimInstance(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());

public:
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUninitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	virtual void NativeThreadSafeUpdateAnimation(float DeltaSeconds) override;

private:
	void CacheReferences_GameThread();
	void GatherGameThreadData();
	void ResetDerivedData_AnyThread();
	void UpdateKinematics_AnyThread(const FKZAnimGameThreadData& Snapshot, float DeltaSeconds);
	void UpdateTransitionData_AnyThread();
	void UpdateLocomotionSelection_AnyThread();
	EKZFoot SelectStopEntryFoot_AnyThread() const;

protected:
	UPROPERTY(Transient)
	TObjectPtr<UKZLocomotionComponent> LocomotionComponent;

	FKZAnimGameThreadData GameThreadData;

	// 이동 관련 계산된 값들. 여기서 계산하고, BP로 보여주기만 할거임
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	TObjectPtr<AKZCharacter> Character;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	TObjectPtr<UCharacterMovementComponent> MovementComponent;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	FVector VelocityWorld;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	FVector VelocityLocal;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	FVector AccelerationWorld;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	float GroundSpeed = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	float MovementDirectionAngle = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	float InputAmount = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bIsGrounded = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bHasMovementInput = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bIsMoving = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bIsStopping = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bIsFalling = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bShouldWalkRun = false; // 현재 Walk Run 을 재생해야하냐

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	bool bShouldSprint = false; // 현재 Sprint를 재생해야하냐

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	EKZGait ResolvedGait = EKZGait::Run;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	EKZRotationMode RotationMode = EKZRotationMode::VelocityDirection;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Movement")
	EKZGait LocomotionGait = EKZGait::Walk;

	// 트랜지션 강제Idle/Start/Stop
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	bool bShouldBeIdle = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	bool bShouldPlayStart = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	EKZGait StopGait = EKZGait::Walk;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	EKZFoot StopEntryFoot = EKZFoot::None;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	float StopEntrySpeed = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	bool bShouldEnterStop = false;

	// 튜닝, 속성 값들
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Animation|Locomotion|Tuning", meta = (ClampMin = "0.0"))
	float RunEnterSpeed = 220.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Animation|Locomotion|Tuning", meta = (ClampMin = "0.0"))
	float RunExitSpeed = 190.f;

private:
	bool bHasPreviousKinematicFrame = false;
	bool bWasMoving = false;
	bool bHadGroundedMovementInput = false;
	float PreviousGroundSpeed = 0.f;
	EKZGait PreviousLocomotionGait = EKZGait::Walk;
};
