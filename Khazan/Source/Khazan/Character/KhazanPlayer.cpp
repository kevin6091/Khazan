#include "Character/KhazanPlayer.h"

#include "Camera/CameraComponent.h"
#include "Component/KhazanLocomotionComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/KismetMathLibrary.h"

AKhazanPlayer::AKhazanPlayer()
{
	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(GetCapsuleComponent());
	SpringArm->TargetArmLength = 600.f;
	SpringArm->SetRelativeRotation(FRotator(-30,0,0));

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm);

	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* PlayerMovement = GetCharacterMovement();
	PlayerMovement->bOrientRotationToMovement = true;
	PlayerMovement->RotationRate = FRotator(0.f, 540.f, 0.f);
	PlayerMovement->MaxWalkSpeed = 600.f;
	PlayerMovement->MinAnalogWalkSpeed = 15.f;
	PlayerMovement->MaxAcceleration = 1800.f;
	PlayerMovement->BrakingDecelerationWalking = 1800.f;

	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -88.f), FRotator(0, -90, 0));
	GetMesh()->SetRelativeScale3D(FVector(0.009f, 0.009f, 0.009f));
}

void AKhazanPlayer::BeginPlay()
{
	Super::BeginPlay();
	
	if (UCharacterMovementComponent* Movement = GetCharacterMovement())
	{
		Movement->MaxWalkSpeed = WalkSpeed;
	}
}

void AKhazanPlayer::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
}

void AKhazanPlayer::UnPossessed()
{
	HandleInputMoveReleased();
	bSprintRequested = false;
	
	Super::UnPossessed();
}

void AKhazanPlayer::HandleInputMove(const FVector2D& MovementInput, const FRotator& ControlRotation)
{
	UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();

	if (!Locomotion)
	{
		return;
	}

	const float RawInputAmount = static_cast<float>(MovementInput.Length());
	
	// 원시 입력의 크기가 DeadZone보다 작으면 입력 취소.
	if (RawInputAmount <= MoveInputDeadZone)
	{
		HandleInputMoveReleased();
		return;
	}
	
	const FRotator YawRotation(0.f, ControlRotation.Yaw, 0.f);
	const FVector Forward = UKismetMathLibrary::GetForwardVector(YawRotation);
	const FVector Right = UKismetMathLibrary::GetRightVector(YawRotation);
	
	const FVector WorldInput = Forward * MovementInput.X + Right * MovementInput.Y;
	
	Locomotion->SetMoveInputWorld(WorldInput);
	
	//gait와 속도 결정하기
	RefreshLocomotionGait();
	
	if (!Locomotion->IsMovementInputAllowed())
	{
		return;
	}
	
	const FVector MoveDirection = Locomotion->GetIntent().MoveInputWorld.GetSafeNormal2D();
	AddMovementInput(MoveDirection, 1.f);
}

void AKhazanPlayer::HandleInputMoveReleased()
{
	if (UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent())
	{
		Locomotion->ClearMoveInput();
	}
	
	if (bToggleSprint)
	{
		bSprintRequested = false;
	}
}

void AKhazanPlayer::HandleInputSprint()
{
	bSprintRequested = bToggleSprint ? !bSprintRequested : true;
	RefreshLocomotionGait();
}

void AKhazanPlayer::HandleInputSprintReleased()
{
	if (!bToggleSprint)
	{
		bSprintRequested = false;
	}

	RefreshLocomotionGait();
}

void AKhazanPlayer::HandleInputSprintCanceled()
{
	bSprintRequested = false;
	RefreshLocomotionGait();
}

void AKhazanPlayer::RefreshLocomotionGait()
{
	UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	
	if (!Locomotion || !Movement)
	{
		return;
	}
	
	const FKhazanLocomotionIntent& Intent = Locomotion->GetIntent();
	
	if (Intent.InputAmount <= 0.f)
	{
		return;
	}
	
	const EKhazanGait StickGait = Intent.InputAmount > RunInputThreshold ? EKhazanGait::Run : EKhazanGait::Walk;
	
	const EKhazanGait RequestedGait = bSprintRequested 	? EKhazanGait::Sprint : StickGait;

	Locomotion->SetTargetGait(RequestedGait);

	if (!Locomotion->IsMovementInputAllowed())
	{
		return;
	}
	
	switch (Locomotion->GetResolvedGait())
	{
	case EKhazanGait::Walk:
		Movement->MaxWalkSpeed = WalkSpeed;
		break;

	case EKhazanGait::Run:
		Movement->MaxWalkSpeed = RunSpeed;
		break;

	case EKhazanGait::Sprint:
		Movement->MaxWalkSpeed = SprintSpeed;
		break;

	default:
		Movement->MaxWalkSpeed = WalkSpeed;
		break;
	}
}
