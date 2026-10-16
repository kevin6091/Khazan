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


UENUM(BlueprintType)
enum class EKZUnawareRoutineRole : uint8 { Solo, Talk01, Talk02 };

/** Already-granted ComboAction: a looping wait section and its matching discovery End. */
USTRUCT(BlueprintType)
struct FKZUnawareRoutine
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Animation")
	FName Name = NAME_None;
	UPROPERTY(EditAnywhere, Category = "Animation")
	EKZUnawareRoutineRole Role = EKZUnawareRoutineRole::Solo;
	UPROPERTY(EditAnywhere, Category = "Animation")
	TSubclassOf<class UGameplayAbility> AbilityClass;
};

UCLASS(BlueprintType)
class KHAZAN_API UKZCharacterDefinitionData : public UDataAsset
{
	GENERATED_BODY()

public:
	const FKZLocomotionConfig& GetLocomotionConfig() const;
	const TArray<FKZUnawareRoutine>& GetUnawareRoutines() const { return UnawareRoutines; }
	const TArray<FKZInitialAbilityGrant>& GetInitialAbilityGrants() const;
	const TArray<TSubclassOf<class UGameplayEffect>>& GetInitialEffects() const;
	
private:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Locomotion",
		meta = (AllowPrivateAccess = "true"))
	FKZLocomotionConfig LocomotionConfig;

	UPROPERTY(EditAnywhere, Category = "Character|Unaware", meta = (TitleProperty = "{Name} [{Role}]"))
	TArray<FKZUnawareRoutine> UnawareRoutines;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Abilities",
	meta = (AllowPrivateAccess = "true", TitleProperty = "{AbilityClass} [{InputTag}]"))
	TArray<FKZInitialAbilityGrant> InitialAbilityGrants;
	
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Ability")
	TArray<TSubclassOf<class UGameplayEffect>> InitialEffects;
};
