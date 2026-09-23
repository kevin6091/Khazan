

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "KZPlayerController.generated.h"

struct FGameplayTag;
struct FInputActionValue;

enum class EKZComboCommandPhase : uint8;

UCLASS()
class KHAZAN_API AKZPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AKZPlayerController(const FObjectInitializer& ObjectInitializer);

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

private:
	class UKZAbilitySystemComponent* GetKZAbilitySystemComponent() const;

	void RouteAttackInput(const FGameplayTag& InputTag, const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase);
	void SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase);

	void AbilityInputTagPressed(const FGameplayTag& InputTag);
	void AbilityInputTagReleased(const FGameplayTag& InputTag);
	void AbilityInputTagCanceled(const FGameplayTag& InputTag);

	void Input_MoveStarted(const FInputActionValue& InputValue);
	void Input_Move(const FInputActionValue& InputValue);
	void Input_MoveReleased(const FInputActionValue& InputValue);

	void Input_Sprint(const FInputActionValue& InputValue);
	void Input_SprintReleased(const FInputActionValue& InputValue);
	void Input_SprintCanceled(const FInputActionValue& InputValue);

	void Input_TurnCamera(const FInputActionValue& InputValue);

	void Input_WeakAttackStarted(const FInputActionValue&);
	void Input_WeakAttackCompleted(const FInputActionValue&);
	void Input_WeakAttackCanceled(const FInputActionValue&);

	void Input_StrongAttackStarted(const FInputActionValue&);
	void Input_StrongAttackCompleted(const FInputActionValue&);
	void Input_StrongAttackCanceled(const FInputActionValue&);

protected:

};
