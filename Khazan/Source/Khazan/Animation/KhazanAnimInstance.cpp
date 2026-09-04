


#include "Animation/KhazanAnimInstance.h"

#include "LogChannels.h"
#include "Character/KhazanCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Character/Component/KhazanLocomotionComponent.h"
#include "Kismet/KismetMathLibrary.h"

UKhazanAnimInstance::UKhazanAnimInstance(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
}

void UKhazanAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();
	
	GameThreadData = FKhazanAnimGameThreadData{};
	ResetDerivedData_AnyThread();
	CacheReferences_GameThread();
	GatherGameThreadData();
}

// AnimInstance가 다른 Mesh/Pawn에 재사용되거나 제거될 때 이전 참조와 값을 삭제
void UKhazanAnimInstance::NativeUninitializeAnimation()
{
	Character = nullptr;
	MovementComponent = nullptr;
	LocomotionComponent = nullptr;

	GameThreadData = FKhazanAnimGameThreadData{};
	ResetDerivedData_AnyThread();

	Super::NativeUninitializeAnimation();
}

// GameThread 업데이트
void UKhazanAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);
	
	if (!IsValid(Character) ||
		!IsValid(MovementComponent) ||
		!IsValid(LocomotionComponent))
	{
		CacheReferences_GameThread();
	}

	GatherGameThreadData();
}

void UKhazanAnimInstance::NativeThreadSafeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeThreadSafeUpdateAnimation(DeltaSeconds);
	
	const FKhazanAnimGameThreadData Snapshot = GameThreadData;

	if (!Snapshot.bValid)
	{
		ResetDerivedData_AnyThread();
		return;
	}

	UpdateKinematics_AnyThread(Snapshot, DeltaSeconds);
}

namespace
{
	constexpr float MovementInputThreshold = 0.01f;
	constexpr float MovingSpeedThreshold = 3.f;
}

void UKhazanAnimInstance::UpdateKinematics_AnyThread(const FKhazanAnimGameThreadData& Snapshot, float DeltaSeconds)
{
	(void)DeltaSeconds;
	
	VelocityWorld = Snapshot.VelocityWorld;
	AccelerationWorld = Snapshot.AccelerationWorld;
	InputAmount = FMath::Clamp(Snapshot.InputAmount, 0.f, 1.f);
	
	const FRotator ActorYawRotation(0.f,Snapshot.ActorRotation.Yaw, 0.f);
	
	// VelocityWorld에 Yaw 역회전을 걸어, 캐릭터 기준의 방향을 확인.
	VelocityLocal = UKismetMathLibrary::LessLess_VectorRotator(VelocityWorld, ActorYawRotation);
	
	GroundSpeed = static_cast<float>(VelocityWorld.Size2D());
	
	bIsFalling = Snapshot.MovementMode == MOVE_Falling;

	bHasMovementInput = Snapshot.bMovementAllowed && InputAmount > MovementInputThreshold;

	bIsMoving = GroundSpeed > MovingSpeedThreshold;

	bShouldWalkRun = !bIsFalling && bHasMovementInput && bIsMoving;
	
	bIsStopping = !bIsFalling && bIsMoving && !bHasMovementInput;
	
	bShouldBeIdle = !bIsFalling && !bHasMovementInput && !bIsMoving;
	
	if (bIsMoving)
	{
		MovementDirectionAngle = static_cast<float>(UKismetMathLibrary::DegAtan2(VelocityLocal.Y, VelocityLocal.X));
	}
	else
	{
		MovementDirectionAngle = 0.f;
	}
	
	ResolvedGait = Snapshot.ResolvedGait;
	RotationMode = Snapshot.RotationMode;
	
	UpdateTransitionData_AnyThread();
}

// Locomotion Start/Stop을 위한 트랜지션 데이터 계산
void UKhazanAnimInstance::UpdateTransitionData_AnyThread()
{
	bShouldPlayStart = false;
	
	if (!bHasPreviousKinematicFrame)
	{
		bHasPreviousKinematicFrame = true;
		bWasMoving = bIsMoving;
		bHadMovementInput = bHasMovementInput;
		return;
	}
	
	const bool bJustStartedMoving = bShouldWalkRun && !bWasMoving;
	bShouldPlayStart = bJustStartedMoving && ResolvedGait != EKhazanGait::Walk;
	const bool bJustReleasedMovementInput = bHadMovementInput && !bHasMovementInput;
	
	if (bJustReleasedMovementInput && bIsStopping)
	{
		bUseRunStop = GroundSpeed >= RunStopSelectionSpeed;
	}
	
	bWasMoving = bIsMoving;
	bHadMovementInput = bHasMovementInput;
}

// 참조 수집
void UKhazanAnimInstance::CacheReferences_GameThread()
{
	check(IsInGameThread());
	
	Character = Cast<AKhazanCharacter>(TryGetPawnOwner());

	MovementComponent = nullptr;
	LocomotionComponent = nullptr;
	if (Character)
	{
		MovementComponent = Character->GetCharacterMovement();
		LocomotionComponent = Character->GetLocomotionComponent();
	}
}

// 워커 스레드에서 사용할 원시 데이터 수집
void UKhazanAnimInstance::GatherGameThreadData()
{
	check(IsInGameThread());
	
	FKhazanAnimGameThreadData NewData;
	
	if (!IsValid(Character) ||
	!IsValid(MovementComponent) ||
	!IsValid(LocomotionComponent))
	{
		GameThreadData = NewData;
		return;
	}
	
	const FKhazanLocomotionIntent& Intent = LocomotionComponent->GetIntent();
	
	NewData.ActorRotation = Character->GetActorRotation();

	NewData.VelocityWorld = MovementComponent->Velocity;

	NewData.AccelerationWorld = MovementComponent->GetCurrentAcceleration();

	NewData.MoveInputWorld = Intent.MoveInputWorld;

	NewData.InputAmount = Intent.InputAmount;

	NewData.MaxAcceleration = MovementComponent->GetMaxAcceleration();

	NewData.MaxBrakingDeceleration = MovementComponent->GetMaxBrakingDeceleration();

	NewData.MovementMode = MovementComponent->MovementMode;

	NewData.TargetGait = Intent.TargetGait;

	NewData.MaxAllowedGait = Intent.MaxAllowedGait;

	NewData.ResolvedGait = LocomotionComponent->GetResolvedGait();

	NewData.RotationMode = Intent.RotationMode;

	NewData.bMovementAllowed = Intent.bMovementAllowed;

	NewData.bValid = true;

	GameThreadData = NewData;
}

void UKhazanAnimInstance::ResetDerivedData_AnyThread()
{
	VelocityWorld = FVector::ZeroVector;
	VelocityLocal = FVector::ZeroVector;
	AccelerationWorld = FVector::ZeroVector;

	GroundSpeed = 0.f;
	MovementDirectionAngle = 0.f;
	InputAmount = 0.f;

	bHasMovementInput = false;
	bIsMoving = false;
	bIsStopping = false;
	bIsFalling = false;
	bShouldWalkRun = false;
	
	bShouldWalkRun = false;
	bShouldBeIdle = false;
	bShouldPlayStart = false;
	bUseRunStop = false;

	bHasPreviousKinematicFrame = false;
	bWasMoving = false;
	bHadMovementInput = false;
	
	ResolvedGait = EKhazanGait::Run;
	RotationMode = EKhazanRotationMode::VelocityDirection;
}

