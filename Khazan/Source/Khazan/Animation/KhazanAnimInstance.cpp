


#include "Animation/KhazanAnimInstance.h"

#include "LogChannels.h"
#include "Character/KhazanCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Character/Component/KhazanLocomotionComponent.h"
#include "Kismet/KismetMathLibrary.h"
#include "Animation/AnimationAsset.h"

namespace
{
	constexpr float MovementInputThreshold = 0.01f;
	constexpr float MovingSpeedThreshold = 3.f;
	const FName LocomotionSyncGroupName(TEXT("Locomotion"));
	const FName LeftFootMarkerName(TEXT("LeftFoot"));
	const FName RightFootMarkerName(TEXT("RightFoot"));
}

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

void UKhazanAnimInstance::UpdateKinematics_AnyThread(const FKhazanAnimGameThreadData& Snapshot, float DeltaSeconds)
{
	(void)DeltaSeconds;
	
	// 실제 이동 벡터. MovementComponent에서 가져온거
	VelocityWorld = Snapshot.VelocityWorld;
	// 실제 가속도. MovementComponent에서 가져온거
	AccelerationWorld = Snapshot.AccelerationWorld;
	// Input기반 0~1범위
	InputAmount = FMath::Clamp(Snapshot.InputAmount, 0.f, 1.f);
	
	// 캐릭터의 XY축 회전각
	const FRotator ActorYawRotation(0.f,Snapshot.ActorRotation.Yaw, 0.f);
	
	// VelocityWorld에 Yaw 역회전을 걸어, 캐릭터 기준의 방향을 확인.
	VelocityLocal = UKismetMathLibrary::LessLess_VectorRotator(VelocityWorld, ActorYawRotation);
	
	// 실제 이동속도.  
	GroundSpeed = static_cast<float>(VelocityWorld.Size2D());
	
	// 땅에 있는지.
	bIsGrounded = Snapshot.MovementMode == MOVE_Walking || Snapshot.MovementMode == MOVE_NavWalking;
	
	// 공중에 있는지.
	bIsFalling = Snapshot.MovementMode == MOVE_Falling;
	
	// "유효한" 이동 Input을 가졌는지. 이동이 허락되지않으면 false.
	bHasMovementInput = Snapshot.bMovementAllowed && InputAmount > MovementInputThreshold;
	
	// 움직이는 중인지. Input말고도 다른 요인으로도 움직인다면 true.
	bIsMoving = GroundSpeed > MovingSpeedThreshold;
	
	if (bIsMoving) // 이동 중일 때, 캐릭터 정면기준 이동 방향의 각도. 
	{
		// 앞쪽: 약 0도. 오른쪽: 약 +90도. 왼쪽: 약 -90도.
		MovementDirectionAngle = 
			static_cast<float>(UKismetMathLibrary::DegAtan2(VelocityLocal.Y, VelocityLocal.X));
	}
	else
	{
		MovementDirectionAngle = 0.f;
	}
	
	ResolvedGait = Snapshot.ResolvedGait;
	RotationMode = Snapshot.RotationMode;
	
	// 여러 프로퍼티를 통해 Idle Walk Run Sprint를 판단한다.
	UpdateLocomotionSelection_AnyThread();
	
	// 상태를 모두 계산 한 후에 트랜지션을 계산한다.
	UpdateTransitionData_AnyThread();
}

// Locomotion Start/Stop을 위한 트랜지션 데이터 계산
void UKhazanAnimInstance::UpdateTransitionData_AnyThread()
{
	bShouldPlayStart = false;
	bShouldEnterStop = false;
	
	if (bHasPreviousKinematicFrame)
	{
		const bool bJustLostGroundedMovementInput = bHadGroundedMovementInput && !bHasMovementInput;

		bShouldEnterStop = bIsGrounded && bJustLostGroundedMovementInput && (bWasMoving || bIsMoving);

		if (bShouldEnterStop)
		{
			StopEntrySpeed = FMath::Max(PreviousGroundSpeed, GroundSpeed);

			StopGait = PreviousLocomotionGait;
			StopEntryFoot = SelectStopEntryFoot_AnyThread();
		}
	}
	
	bHasPreviousKinematicFrame = true;
	bWasMoving = bIsMoving;
	bHadGroundedMovementInput = bIsGrounded && bHasMovementInput;
	PreviousGroundSpeed = GroundSpeed;
	PreviousLocomotionGait = LocomotionGait;
}

// Locomotion의 Gait를 선택한다.
void UKhazanAnimInstance::UpdateLocomotionSelection_AnyThread()
{
	const bool bHasGroundedMovementInput = bIsGrounded && bHasMovementInput;
	if (bHasGroundedMovementInput)
	{
		if (ResolvedGait == EKhazanGait::Sprint)
		{
			LocomotionGait = EKhazanGait::Sprint;
		}
		else if (!bIsMoving)
		{
			LocomotionGait = EKhazanGait::Walk;
		}
		else if (LocomotionGait != EKhazanGait::Walk)
		{
			LocomotionGait = GroundSpeed > RunExitSpeed ? EKhazanGait::Run : EKhazanGait::Walk;
		}
		else
		{
			LocomotionGait = GroundSpeed >= RunEnterSpeed ? EKhazanGait::Run : EKhazanGait::Walk;
		}
	}
	
	// 지상 이동 명령인데, Gait가 Sprint가 아니다. -> WalkRun 
	bShouldWalkRun = bHasGroundedMovementInput && LocomotionGait != EKhazanGait::Sprint;
	// 지상 이동 + Gait는 Sprint -> Sprint 해야함.
	bShouldSprint = bHasGroundedMovementInput && LocomotionGait == EKhazanGait::Sprint;
	// 지상이고 입력은 없지만 움직이는 중 -> 멈추고 있다.
	bIsStopping = bIsGrounded && !bHasMovementInput && bIsMoving;

	// 지상이고 입력 없고 움직이도 않는다 -> Idle 해야함.
	bShouldBeIdle = bIsGrounded && !bHasMovementInput && !bIsMoving;
}

EKhazanFoot UKhazanAnimInstance::SelectStopEntryFoot_AnyThread() const
{
	const FMarkerSyncAnimPosition Position = GetSyncGroupPosition(LocomotionSyncGroupName);
	
	const bool bLeftToRight =  
		Position.PreviousMarkerName == LeftFootMarkerName &&  
		Position.NextMarkerName == RightFootMarkerName;

	const bool bRightToLeft =
		Position.PreviousMarkerName == RightFootMarkerName &&
		Position.NextMarkerName == LeftFootMarkerName;
	
	const float Alpha = Position.PositionBetweenMarkers;
	
	// 예외 처리
	if ((!bLeftToRight && !bRightToLeft) ||
		!FMath::IsFinite(Alpha) ||
		Alpha < 0.f || Alpha > 1.f)
	{
		return EKhazanFoot::None;
	}
	
	const FName ClosestMarkerName = Alpha <= 0.5f ? Position.PreviousMarkerName : Position.NextMarkerName;
	
	return ClosestMarkerName == LeftFootMarkerName ? EKhazanFoot::Left : EKhazanFoot::Right;
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

	NewData.TargetGait = Intent.RequestedGait;

	NewData.MaxAllowedGait = Intent.MaxAllowedGait;

	NewData.ResolvedGait = LocomotionComponent->GetResolvedGait();

	NewData.RotationMode = Intent.RotationMode;

	NewData.bMovementAllowed = LocomotionComponent->IsMovementInputAllowed();
	
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
	bIsGrounded = false;
	bShouldSprint = false;
	
	bShouldBeIdle = false;
	bShouldWalkRun = false;
	bShouldPlayStart = false;

	bHasPreviousKinematicFrame = false;
	bWasMoving = false;
	
	LocomotionGait = EKhazanGait::Walk;
	StopGait = EKhazanGait::Walk;
	StopEntryFoot = EKhazanFoot::None;
	StopEntrySpeed = 0.f;
	bShouldEnterStop = false;
	bHadGroundedMovementInput = false;
	PreviousGroundSpeed = 0.f;
	PreviousLocomotionGait = EKhazanGait::Walk;
	
	ResolvedGait = EKhazanGait::Run;
	RotationMode = EKhazanRotationMode::VelocityDirection;
}

