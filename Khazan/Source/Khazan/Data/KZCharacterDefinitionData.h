#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KZLocomotionType.h"
#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "KZCharacterDefinitionData.generated.h"

/** CharacterDefinition이 초기화 때 한 번 부여할 Ability 하나. */
USTRUCT(BlueprintType)
struct KHAZAN_API FKZInitialAbilityGrant
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ability")
	TSubclassOf<class UGameplayAbility> AbilityClass = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ability",
		meta = (Categories = "Input.Action"))
	FGameplayTag InputTag = FGameplayTag::EmptyTag;
};


UCLASS(BlueprintType)
class KHAZAN_API UKZCharacterDefinitionData : public UDataAsset
{
	GENERATED_BODY()

public:
	const FKZLocomotionConfig& GetLocomotionConfig() const;
	const TArray<FKZInitialAbilityGrant>& GetInitialAbilityGrants() const;

private:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Locomotion",
		meta = (AllowPrivateAccess = "true"))
	FKZLocomotionConfig LocomotionConfig;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Abilities",
	meta = (AllowPrivateAccess = "true"))
	TArray<FKZInitialAbilityGrant> InitialAbilityGrants;
};