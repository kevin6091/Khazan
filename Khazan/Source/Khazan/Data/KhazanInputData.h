

#pragma once

#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "KhazanInputData.generated.h"

class UInputAction;
class UInputMappingContext;

USTRUCT()
struct FKhazanInputAction
{
	GENERATED_BODY()
	
public:
	UPROPERTY(EditDefaultsOnly)
	FGameplayTag InputTag = FGameplayTag::EmptyTag;
	
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UInputAction> InputAction = nullptr;
};

UCLASS()
class KHAZAN_API UKhazanInputData : public UDataAsset
{
	GENERATED_BODY()
	
public:
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UInputMappingContext> InputMappingContext;
	
	UPROPERTY(EditDefaultsOnly)
	TArray<FKhazanInputAction> InputActions;
};
