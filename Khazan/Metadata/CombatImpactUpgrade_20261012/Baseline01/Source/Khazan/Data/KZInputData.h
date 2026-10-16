

#pragma once

#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "KZInputData.generated.h"

class UInputAction;
class UInputMappingContext;

USTRUCT()
struct FKZInputAction
{
	GENERATED_BODY()

public:
	UPROPERTY(EditDefaultsOnly)
	FGameplayTag InputTag = FGameplayTag::EmptyTag;

	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UInputAction> InputAction = nullptr;
};

UCLASS()
class KHAZAN_API UKZInputData : public UDataAsset
{
	GENERATED_BODY()

public:
	const UInputAction* FindInputActionByTag(const FGameplayTag& InputTag) const;

public:
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UInputMappingContext> InputMappingContext;

	UPROPERTY(EditDefaultsOnly)
	TArray<FKZInputAction> InputActions;
};
