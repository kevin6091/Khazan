


#include "KhazanPlayerController.h"
#include "GameFramework/Pawn.h"
#include "InputActionValue.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "KhazanGameplayTags.h"
#include "Character/KhazanCharacter.h"
#include "Character/KhazanPlayer.h"
#include "Data/KhazanInputData.h"
#include "System/KhazanAssetManager.h"

AKhazanPlayerController::AKhazanPlayerController(const FObjectInitializer& ObjectInitializer)
	:Super(ObjectInitializer)
{
}

void AKhazanPlayerController::BeginPlay()
{
	Super::BeginPlay();

	if (const UKhazanInputData* InputData = UKhazanAssetManager::GetAssetByName<UKhazanInputData>(KhazanGameplayTags::AssetData_InputData))
	{
		
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = GetLocalPlayer()->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
		{
			Subsystem->AddMappingContext(InputData->InputMappingContext, 0);
		}
	}
}

void AKhazanPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	
	if (const UKhazanInputData* InputData = UKhazanAssetManager::GetAssetByName<UKhazanInputData>(KhazanGameplayTags::AssetData_InputData))
	{
		UEnhancedInputComponent* EnhancedInputComponent = CastChecked<UEnhancedInputComponent>(InputComponent);
		
		auto MoveAction = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Move);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ThisClass::Input_Move);
		
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Completed, this, &ThisClass::Input_MoveReleased);

		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Canceled, this, &ThisClass::Input_MoveReleased);
		
		auto Action2 = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Turn);
		EnhancedInputComponent->BindAction(Action2, ETriggerEvent::Triggered, this, &ThisClass::Input_Turn);
		
		auto Action3 = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Jump);
		EnhancedInputComponent->BindAction(Action3, ETriggerEvent::Triggered, this, &ThisClass::Input_Jump);
		
		auto Action4 = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Attack);
		EnhancedInputComponent->BindAction(Action4, ETriggerEvent::Triggered, this, &ThisClass::Input_Attack);
	}
}

void AKhazanPlayerController::Input_Move(const FInputActionValue& InputValue)
{
	if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
	{
		KhazanPlayer->HandleInputMove(InputValue.Get<FVector2D>(), GetControlRotation());
	}
}

void AKhazanPlayerController::Input_MoveReleased(const FInputActionValue& InputValue)
{
	if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
	{
		KhazanPlayer->HandleInputMoveReleased();
	}
}

void AKhazanPlayerController::Input_Turn(const FInputActionValue& InputValue)
{
	const FVector2D Val = InputValue.Get<FVector2D>();
	AddYawInput(Val.X);
	AddPitchInput(-Val.Y);
}

void AKhazanPlayerController::Input_Jump(const FInputActionValue& InputValue)
{
	if (AKhazanCharacter* KhazanCharacter = Cast<AKhazanCharacter>(GetPawn()))
	{
		KhazanCharacter->Jump();
	}
}

void AKhazanPlayerController::Input_Attack(const FInputActionValue& InputValue)
{
}
