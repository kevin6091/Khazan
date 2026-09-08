


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
		
		auto SprintAction = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Sprint);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Started, this, &ThisClass::Input_Sprint);
		EnhancedInputComponent->BindAction( SprintAction, ETriggerEvent::Completed, this, &ThisClass::Input_SprintReleased);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Canceled, this, &ThisClass::Input_SprintCanceled);
		
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

void AKhazanPlayerController::Input_Sprint(const FInputActionValue& InputValue)
{
	if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
	{
		KhazanPlayer->HandleInputSprint();
	}
}

void AKhazanPlayerController::Input_SprintReleased(const FInputActionValue& InputValue)
{
	if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
	{
		KhazanPlayer->HandleInputSprintReleased();
	}
}

void AKhazanPlayerController::Input_SprintCanceled(const FInputActionValue& InputValue)
{
	if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
	{
		KhazanPlayer->HandleInputSprintCanceled();
	}
}

void AKhazanPlayerController::Input_Turn(const FInputActionValue& InputValue)
{
	const FVector2D Val = InputValue.Get<FVector2D>();
	AddYawInput(Val.X);
	AddPitchInput(Val.Y);
}

void AKhazanPlayerController::Input_Jump(const FInputActionValue& InputValue)
{
	if (AKhazanCharacter* KhazanCharacter = Cast<AKhazanCharacter>(GetPawn()))
	{
		KhazanCharacter->Jump();
		// Test
		PlayDynamicForceFeedback(
				1.0f,     // Intensity (테스트를 위해 최대치 1.0f 권장)
				0.5f,     // Duration (0.5초)
				true,     // bAffectsLeftLarge (좌측 저주파 모터 ON)
				false,    // bAffectsLeftSmall
				false,    // bAffectsRightLarge
				true,     // bAffectsRightSmall (우측 고주파 모터 ON)
				EDynamicForceFeedbackAction::Start
			);	}
}

void AKhazanPlayerController::Input_Attack(const FInputActionValue& InputValue)
{
}
