

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
	
protected:
	UPROPERTY(Category = Character, VisibleAnywhere, BlueprintReadOnly)
	TObjectPtr<class USpringArmComponent> SpringArm;

	UPROPERTY(Category = Character, VisibleAnywhere, BlueprintReadOnly)
	TObjectPtr<class UCameraComponent> Camera;

};
