


#include "KhazanPlayerController.h"

#include "InputAction.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/Pawn.h"
#include "InputActionValue.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "KhazanGameplayTags.h"
#include "Character/KhazanCharacter.h"
#include "Character/KhazanPlayer.h"
#include "Data/KhazanInputData.h"
#include "System/KhazanAssetManager.h"
#include "Ability/KhazanAbilitySystemComponent.h"

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
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Started, this, &ThisClass::Input_MoveStarted);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ThisClass::Input_Move);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Completed, this, &ThisClass::Input_MoveReleased);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Canceled, this, &ThisClass::Input_MoveReleased);
		
		auto SprintAction = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Sprint);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Started, this, &ThisClass::Input_Sprint);
		EnhancedInputComponent->BindAction( SprintAction, ETriggerEvent::Completed, this, &ThisClass::Input_SprintReleased);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Canceled, this, &ThisClass::Input_SprintCanceled);
		
		auto TurnCameraAction = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Turn);
		EnhancedInputComponent->BindAction(TurnCameraAction, ETriggerEvent::Triggered, this, &ThisClass::Input_TurnCamera);
		
		auto WeakAttackAction = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_WeakAttack);
		EnhancedInputComponent->BindAction(WeakAttackAction, ETriggerEvent::Started, this, &ThisClass::Input_WeakAttackStarted);
		EnhancedInputComponent->BindAction(WeakAttackAction, ETriggerEvent::Completed, this, &ThisClass::Input_WeakAttackCompleted);
		EnhancedInputComponent->BindAction(WeakAttackAction, ETriggerEvent::Canceled, this, &ThisClass::Input_WeakAttackCanceled);
		
		auto StrongAttackAction = InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_StrongAttack);
		EnhancedInputComponent->BindAction(StrongAttackAction, ETriggerEvent::Started, this, &ThisClass::Input_StrongAttackStarted);
		EnhancedInputComponent->BindAction(StrongAttackAction, ETriggerEvent::Completed, this, &ThisClass::Input_StrongAttackCompleted);
		EnhancedInputComponent->BindAction(StrongAttackAction, ETriggerEvent::Canceled, this, &ThisClass::Input_StrongAttackCanceled);
	}
}

void AKhazanPlayerController::Input_WeakAttackStarted(const FInputActionValue&)
{
	AbilityInputTagPressed(KhazanGameplayTags::Input_Action_WeakAttack);
}

void AKhazanPlayerController::Input_WeakAttackCompleted(const FInputActionValue&)
{
	AbilityInputTagReleased(KhazanGameplayTags::Input_Action_WeakAttack);
}

void AKhazanPlayerController::Input_WeakAttackCanceled(const FInputActionValue&)
{
	AbilityInputTagReleased(KhazanGameplayTags::Input_Action_WeakAttack);
}

void AKhazanPlayerController::Input_StrongAttackStarted(const FInputActionValue&)
{
	AbilityInputTagPressed(KhazanGameplayTags::Input_Action_StrongAttack);
}

void AKhazanPlayerController::Input_StrongAttackCompleted(const FInputActionValue&)
{
	AbilityInputTagReleased(KhazanGameplayTags::Input_Action_StrongAttack);
}

void AKhazanPlayerController::Input_StrongAttackCanceled(const FInputActionValue&)
{
	AbilityInputTagReleased(KhazanGameplayTags::Input_Action_StrongAttack);
}

void AKhazanPlayerController::Input_MoveStarted(const FInputActionValue& InputValue)
{

}

void AKhazanPlayerController::Input_Move(const FInputActionValue& InputValue)
{
	if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
	{
		KhazanPlayer->HandleInputMove(InputValue.Get<FVector2D>(), GetControlRotation());
	}
	
	UKhazanAbilitySystemComponent* ASC = GetKhazanAbilitySystemComponent();
	
	if (!IsValid(ASC))
	{
		return;
	}
	
	FGameplayEventData Payload;
	ASC->HandleGameplayEvent(KhazanGameplayTags::Input_Action_Move, &Payload);
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

void AKhazanPlayerController::Input_TurnCamera(const FInputActionValue& InputValue)
{
	const FVector2D Val = InputValue.Get<FVector2D>();
	AddYawInput(Val.X);
	AddPitchInput(Val.Y);
}

UKhazanAbilitySystemComponent* AKhazanPlayerController::GetKhazanAbilitySystemComponent() const
{
	const AKhazanCharacter* KhazanCharacter = Cast<AKhazanCharacter>(GetPawn());

	if (!IsValid(KhazanCharacter))
	{
		return nullptr;
	}

	return Cast<UKhazanAbilitySystemComponent>(KhazanCharacter->GetAbilitySystemComponent());
}

void AKhazanPlayerController::AbilityInputTagPressed(const FGameplayTag& InputTag)
{
	if (UKhazanAbilitySystemComponent* KhazanASC = GetKhazanAbilitySystemComponent())
	{
		KhazanASC->AbilityInputTagPressed(InputTag);
	}
}

void AKhazanPlayerController::AbilityInputTagReleased(const FGameplayTag& InputTag)
{
	if (UKhazanAbilitySystemComponent* KhazanASC = GetKhazanAbilitySystemComponent())
	{
		KhazanASC->AbilityInputTagReleased(InputTag);
	}
}