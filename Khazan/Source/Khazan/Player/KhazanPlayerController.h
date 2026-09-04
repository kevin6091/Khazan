

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "KhazanPlayerController.generated.h"

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
	void Input_Move(const FInputActionValue& InputValue);
	void Input_MoveReleased(const FInputActionValue& InputValue);
	
	void Input_Turn(const FInputActionValue& InputValue);
	void Input_Jump(const FInputActionValue& InputValue);
	void Input_Attack(const FInputActionValue& InputValue);
	
protected:

};
