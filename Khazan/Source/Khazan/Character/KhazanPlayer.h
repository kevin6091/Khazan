

#pragma once

#include "CoreMinimal.h"
#include "Character/KhazanCharacter.h"
#include "KhazanPlayer.generated.h"

UCLASS()
class KHAZAN_API AKhazanPlayer : public AKhazanCharacter
{
	GENERATED_BODY()
	
public:
	AKhazanPlayer();

protected:
	virtual void BeginPlay() override;

public:	
	virtual void Tick(float DeltaTime) override;
	
public:
	void HandleInputMove(const FVector2D& MovementInput, const FRotator& ControlRotation);
	void HandleInputMoveReleased();
	
	void HandleInputSprint();
	void HandleInputSprintReleased();
	void HandleInputSprintCanceled();

	void RefreshLocomotionGait();
	
protected:
	UPROPERTY(Category = Character, VisibleAnywhere, BlueprintReadOnly)
	TObjectPtr<class USpringArmComponent> SpringArm;

	UPROPERTY(Category = Character, VisibleAnywhere, BlueprintReadOnly)
	TObjectPtr<class UCameraComponent> Camera;
	
	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Speed", meta = (ClampMin = "0.0"))
	float WalkSpeed = 170.f;

	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Speed", meta = (ClampMin = "0.0"))
	float RunSpeed = 470.f;

	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Speed", meta = (ClampMin = "0.0"))
	float SprintSpeed = 600.f;

	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float RunInputThreshold = 0.6f;

	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float MoveInputDeadZone = 0.1f;

	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input")
	bool bToggleSprint = true;

private:
	bool bSprintRequested = false;

};
