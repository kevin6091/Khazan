// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "KhazanCharacter.generated.h"

class UKhazanLocomotionComponent;

UCLASS()
class KHAZAN_API AKhazanCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AKhazanCharacter();

	UKhazanLocomotionComponent* GetLocomotionComponent() const
	{
		return LocomotionComponent;
	}
	
protected:
	virtual void BeginPlay() override;

public:	
	virtual void Tick(float DeltaTime) override;
	
private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character|Locomotion", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UKhazanLocomotionComponent> LocomotionComponent;
};
