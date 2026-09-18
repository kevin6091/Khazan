

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "KhazanPlayerController.generated.h"

struct FGameplayTag;
struct FInputActionValue;

/**
 * 
 */
UCLASS()
class KHAZAN_API AKhazanPlayerController : public APlayerController
{
	GENERATED_BODY()
	
public:
	AKhazanPlayerController(const FObjectInitializer& ObjectInitializer);

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

private:
	class UKhazanAbilitySystemComponent* GetKhazanAbilitySystemComponent() const;
	
	void AbilityInputTagPressed(const FGameplayTag& InputTag);
	void AbilityInputTagReleased(const FGameplayTag& InputTag);
	
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
