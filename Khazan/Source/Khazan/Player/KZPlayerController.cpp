


#include "KZPlayerController.h"

#include "InputAction.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/Pawn.h"
#include "InputActionValue.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "KZGameplayTags.h"
#include "Character/KZCharacter.h"
#include "Character/KZPlayer.h"
#include "Data/KZInputData.h"
#include "System/KZAssetManager.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboTypes.h"

AKZPlayerController::AKZPlayerController(const FObjectInitializer& ObjectInitializer)
	:Super(ObjectInitializer)
{
}

void AKZPlayerController::BeginPlay()
{
	Super::BeginPlay();

	if (const UKZInputData* InputData = UKZAssetManager::GetAssetByName<UKZInputData>(KZGameplayTags::AssetData_InputData))
	{

		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = GetLocalPlayer()->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
		{
			Subsystem->AddMappingContext(InputData->InputMappingContext, 0);
		}
	}
}

void AKZPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();

	if (const UKZInputData* InputData = UKZAssetManager::GetAssetByName<UKZInputData>(KZGameplayTags::AssetData_InputData))
	{
		UEnhancedInputComponent* EnhancedInputComponent = CastChecked<UEnhancedInputComponent>(InputComponent);

		auto MoveAction = InputData->FindInputActionByTag(KZGameplayTags::Input_Action_Move);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Started, this, &ThisClass::Input_MoveStarted);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ThisClass::Input_Move);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Completed, this, &ThisClass::Input_MoveReleased);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Canceled, this, &ThisClass::Input_MoveReleased);

		auto SprintAction = InputData->FindInputActionByTag(KZGameplayTags::Input_Action_Sprint);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Started, this, &ThisClass::Input_Sprint);
		EnhancedInputComponent->BindAction( SprintAction, ETriggerEvent::Completed, this, &ThisClass::Input_SprintReleased);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Canceled, this, &ThisClass::Input_SprintCanceled);

		auto TurnCameraAction = InputData->FindInputActionByTag(KZGameplayTags::Input_Action_Turn);
		EnhancedInputComponent->BindAction(TurnCameraAction, ETriggerEvent::Triggered, this, &ThisClass::Input_TurnCamera);

		auto WeakAttackAction = InputData->FindInputActionByTag(KZGameplayTags::Input_Action_X);
		EnhancedInputComponent->BindAction(WeakAttackAction, ETriggerEvent::Started, this, &ThisClass::Input_WeakAttackStarted);
		EnhancedInputComponent->BindAction(WeakAttackAction, ETriggerEvent::Completed, this, &ThisClass::Input_WeakAttackCompleted);
		EnhancedInputComponent->BindAction(WeakAttackAction, ETriggerEvent::Canceled, this, &ThisClass::Input_WeakAttackCanceled);

		auto StrongAttackAction = InputData->FindInputActionByTag(KZGameplayTags::Input_Action_Y);
		EnhancedInputComponent->BindAction(StrongAttackAction, ETriggerEvent::Started, this, &ThisClass::Input_StrongAttackStarted);
		EnhancedInputComponent->BindAction(StrongAttackAction, ETriggerEvent::Completed, this, &ThisClass::Input_StrongAttackCompleted);
		EnhancedInputComponent->BindAction(StrongAttackAction, ETriggerEvent::Canceled, this, &ThisClass::Input_StrongAttackCanceled);
	}
}

#pragma region WeakAttack

void AKZPlayerController::Input_WeakAttackStarted(const FInputActionValue&)
{
	RouteAttackInput( KZGameplayTags::Input_Action_X,
		KZGameplayTags::Command_Player_Attack_X,
		EKZComboCommandPhase::Begin);
}

void AKZPlayerController::Input_WeakAttackCompleted(const FInputActionValue&)
{
	RouteAttackInput( KZGameplayTags::Input_Action_X,
		KZGameplayTags::Command_Player_Attack_X,
		EKZComboCommandPhase::Release);
}

void AKZPlayerController::Input_WeakAttackCanceled(const FInputActionValue&)
{
	RouteAttackInput( KZGameplayTags::Input_Action_X,
		KZGameplayTags::Command_Player_Attack_X,
		EKZComboCommandPhase::Cancel);
}

#pragma endregion

#pragma region StrongAttack

void AKZPlayerController::Input_StrongAttackStarted(const FInputActionValue&)
{
	RouteAttackInput(KZGameplayTags::Input_Action_Y,
		KZGameplayTags::Command_Player_Attack_Y,
		EKZComboCommandPhase::Begin);
}

void AKZPlayerController::Input_StrongAttackCompleted(const FInputActionValue&)
{
	RouteAttackInput(KZGameplayTags::Input_Action_Y,
		KZGameplayTags::Command_Player_Attack_Y,
		EKZComboCommandPhase::Release);}

void AKZPlayerController::Input_StrongAttackCanceled(const FInputActionValue&)
{
	RouteAttackInput(KZGameplayTags::Input_Action_Y,
		KZGameplayTags::Command_Player_Attack_Y,
		EKZComboCommandPhase::Cancel);
}

#pragma endregion

#pragma region Input_Move

void AKZPlayerController::Input_MoveStarted(const FInputActionValue& InputValue)
{

}

void AKZPlayerController::Input_Move(const FInputActionValue& InputValue)
{
	if (AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn()))
	{
		PlayerCharacter->HandleInputMove(InputValue.Get<FVector2D>(), GetControlRotation());
	}

	UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent();

	if (!IsValid(ASC))
	{
		return;
	}

	FGameplayEventData Payload;
	ASC->HandleGameplayEvent(KZGameplayTags::Input_Action_Move, &Payload);
}

void AKZPlayerController::Input_MoveReleased(const FInputActionValue& InputValue)
{
	if (AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn()))
	{
		PlayerCharacter->HandleInputMoveReleased();
	}
}

#pragma endregion

#pragma region Input_Sprint

void AKZPlayerController::Input_Sprint(const FInputActionValue& InputValue)
{
	if (AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn()))
	{
		PlayerCharacter->HandleInputSprint();
	}
}

void AKZPlayerController::Input_SprintReleased(const FInputActionValue& InputValue)
{
	if (AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn()))
	{
		PlayerCharacter->HandleInputSprintReleased();
	}
}

void AKZPlayerController::Input_SprintCanceled(const FInputActionValue& InputValue)
{
	if (AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn()))
	{
		PlayerCharacter->HandleInputSprintCanceled();
	}
}

#pragma endregion

void AKZPlayerController::Input_TurnCamera(const FInputActionValue& InputValue)
{
	const FVector2D Val = InputValue.Get<FVector2D>();
	AddYawInput(Val.X);
	AddPitchInput(Val.Y);
}

UKZAbilitySystemComponent* AKZPlayerController::GetKZAbilitySystemComponent() const
{
	const AKZCharacter* ControlledCharacter = Cast<AKZCharacter>(GetPawn());

	if (!IsValid(ControlledCharacter))
	{
		return nullptr;
	}

	return Cast<UKZAbilitySystemComponent>(ControlledCharacter->GetAbilitySystemComponent());
}

void AKZPlayerController::RouteAttackInput(const FGameplayTag& InputTag, const FGameplayTag& CommandTag,
	EKZComboCommandPhase CommandPhase)
{
	// InputTag는 어떤 Ability Spec이 버튼을 소유하는지 찾는다.
	// CommandTag는 실행 중인 Combo Graph가 어떤 Edge를 검사할지 정한다.
	switch (CommandPhase)
	{
	case EKZComboCommandPhase::Begin:
		AbilityInputTagPressed(InputTag);
		SubmitComboCommand(CommandTag, CommandPhase);
		break;

	case EKZComboCommandPhase::Release:
		// generic release task가 Ability를 끝내기 전에 graph가 Release를 소비한다.
		SubmitComboCommand(CommandTag, CommandPhase);
		AbilityInputTagReleased(InputTag);
		break;

	case EKZComboCommandPhase::Cancel:
		// Ability 취소 전에 held/pending을 먼저 정리한다.
		SubmitComboCommand(CommandTag, CommandPhase);
		AbilityInputTagCanceled(InputTag);
		break;

	default:
		return;
	}
}

void AKZPlayerController::SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase)
{
	if (UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent())
	{
		ASC->SubmitComboCommand(CommandTag, CommandPhase);
	}
}

void AKZPlayerController::AbilityInputTagPressed(const FGameplayTag& InputTag)
{
	if (UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent())
	{
		ASC->AbilityInputTagPressed(InputTag);
	}
}

void AKZPlayerController::AbilityInputTagReleased(const FGameplayTag& InputTag)
{
	if (UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent())
	{
		ASC->AbilityInputTagReleased(InputTag);
	}
}

void AKZPlayerController::AbilityInputTagCanceled(const FGameplayTag& InputTag)
{
	if (UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent())
	{
		ASC->AbilityInputTagCanceled(InputTag);
	}
}
