// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AbilitySystemInterface.h"
#include "KhazanCharacter.generated.h"

class UKhazanLocomotionComponent;
class UAbilitySystemComponent;
class UKhazanCharacterDefinitionData;

UCLASS()
class KHAZAN_API AKhazanCharacter : public ACharacter, public IAbilitySystemInterface
{
	GENERATED_BODY()

public:
	AKhazanCharacter();
	
	UFUNCTION(BlueprintPure, Category = "Character|Locomotion")
	UKhazanLocomotionComponent* GetLocomotionComponent() const
	{
		return LocomotionComponent;
	}

	const UKhazanCharacterDefinitionData* GetCharacterDefinition() const
	{
		return CharacterDefinition;
	}
	
protected:
	virtual void BeginPlay() override;

public:	
	virtual void Tick(float DeltaTime) override;
	
	// For ASC
protected:
	// ASC Init
	virtual void PostInitializeComponents() override;
	
	// ASC와 Actor수명 연결
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	
public:
	virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;

	// Controller가 Pawn을 소유할 때 호출/ Controller가 바꼈을때
	virtual void PossessedBy(AController* NewController) override;

	// Controller의 소유가 해제될 때 호출. Pawn 빙의 해제
	virtual void UnPossessed() override;
	
private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character|AbilitySystem", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UAbilitySystemComponent> AbilitySystemComponent = nullptr;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character|Locomotion", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UKhazanLocomotionComponent> LocomotionComponent;
	
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Character|Definition", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UKhazanCharacterDefinitionData> CharacterDefinition = nullptr;
};
