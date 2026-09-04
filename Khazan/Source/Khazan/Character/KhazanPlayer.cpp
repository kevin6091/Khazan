#include "Character/KhazanPlayer.h"

#include "Camera/CameraComponent.h"
#include "Component/KhazanLocomotionComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"

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
}

void AKhazanPlayer::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
}

void AKhazanPlayer::HandleInputMove(const FVector2D& MovementInput, const FRotator& ControlRotation)
{
	const FRotator YawRotation(0.f,ControlRotation.Yaw, 0.f);
	const FVector Forward = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
	const FVector Right = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);
	
	const FVector WorldInput = Forward * MovementInput.X + Right * MovementInput.Y;
	
	GetLocomotionComponent()->SetMoveInputWorld(WorldInput);
	AddMovementInput(Forward, MovementInput.X);
	AddMovementInput(Right, MovementInput.Y);
}

void AKhazanPlayer::HandleInputMoveReleased()
{
	GetLocomotionComponent()->ClearMoveInput();
}
