


#include "KhazanPlayerController.h"
#include "GameFramework/Pawn.h"
#include "InputActionValue.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"

AKhazanPlayerController::AKhazanPlayerController(const FObjectInitializer& ObjectInitializer)
	:Super(ObjectInitializer)
{
}

void AKhazanPlayerController::BeginPlay()
{
	Super::BeginPlay();

	if (auto* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Subsystem->AddMappingContext(InputMappingContext, 0);
	}
}

void AKhazanPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();

	if (auto* EnhancedInputComponent = Cast<UEnhancedInputComponent>(InputComponent))
	{
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ThisClass::Input_Move);
		EnhancedInputComponent->BindAction(TurnAction, ETriggerEvent::Triggered, this, &ThisClass::Input_Turn);
	}
}

void AKhazanPlayerController::Input_Move(const FInputActionValue& InputValue)
{
	const FVector2D MovementVector = InputValue.Get<FVector2D>();

	const FRotator Rotator = GetControlRotation();
	const FVector ForwardDir = FRotationMatrix(FRotator(0.f,Rotator.Yaw,0.f)).GetUnitAxis(EAxis::X);
	const FVector RightDir   = FRotationMatrix(FRotator(0.f,Rotator.Yaw,0.f)).GetUnitAxis(EAxis::Y);
	
	GetPawn()->AddMovementInput(ForwardDir, MovementVector.X);
	GetPawn()->AddMovementInput(RightDir,  MovementVector.Y);
}

void AKhazanPlayerController::Input_Turn(const FInputActionValue& InputValue)
{
	const FVector2D Val = InputValue.Get<FVector2D>();
	AddYawInput(Val.X);
	AddPitchInput(-Val.Y);
}
