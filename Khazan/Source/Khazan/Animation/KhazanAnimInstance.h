

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Engine/EngineTypes.h"
#include "KhazanAnimInstance.generated.h"

class AKhazanCharacter;
class UCharacterMovementComponent;

struct FKhazanAnimGameThreadData
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

	EKhazanGait TargetGait = EKhazanGait::Run;
	EKhazanGait MaxAllowedGait = EKhazanGait::Run;
	EKhazanGait ResolvedGait = EKhazanGait::Run;

	EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;
	
	bool bMovementAllowed = true;
};

class UKhazanLocomotionComponent;

UCLASS()
class KHAZAN_API UKhazanAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	UKhazanAnimInstance(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());

public:
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUninitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	virtual void NativeThreadSafeUpdateAnimation(float DeltaSeconds) override;

private:
	void CacheReferences_GameThread();
	void GatherGameThreadData();
	void ResetDerivedData_AnyThread();
	void UpdateKinematics_AnyThread(const FKhazanAnimGameThreadData& Snapshot, float DeltaSeconds);
	void UpdateTransitionData_AnyThread();
	
protected:
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	TObjectPtr<AKhazanCharacter> Character;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	TObjectPtr<UCharacterMovementComponent> MovementComponent;
	
	UPROPERTY(Transient)
	TObjectPtr<UKhazanLocomotionComponent> LocomotionComponent;
	
	FKhazanAnimGameThreadData GameThreadData;
	
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	FVector VelocityWorld;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	FVector VelocityLocal;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	FVector AccelerationWorld;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	float GroundSpeed = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	float MovementDirectionAngle = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	float InputAmount = 0.f;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	bool bHasMovementInput = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	bool bIsMoving = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	bool bIsStopping = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	bool bIsFalling = false;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	bool bShouldWalkRun = false;
	
	// 트랜지션 강제Idle/Start/Stop
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	bool bShouldBeIdle = false;
	
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	bool bShouldPlayStart = false;
	
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
	bool bUseRunStop = false;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Animation|Locomotion|Tuning", meta = (ClampMin = "0.0"))
	float RunStopSelectionSpeed = 315.f;
	
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	EKhazanGait ResolvedGait = EKhazanGait::Run;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
	EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;
	
private:
	bool bHasPreviousKinematicFrame = false;
	bool bWasMoving = false;
	bool bHadMovementInput = false;
};
