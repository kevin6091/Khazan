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

/** Monster-only policy. Resources remain on the ASC; these are editable data, not runtime state. */
USTRUCT(BlueprintType)
struct FKZMonsterStaminaSettings
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Stamina")
	bool bEnabled = false;
	// User decision: successful parry removes 5; this is not an original-game value.
	UPROPERTY(EditAnywhere, Category = "Stamina", meta = (ClampMin = "0"))
	float ParryStaminaDamage = 5.f;
	// Authored from the original CS: human four/Apes 5 s, Yetuga 8 s. Zero waits for a Brutal Attack.
	UPROPERTY(EditAnywhere, Category = "Exhaustion", meta = (ClampMin = "0", Units = "s"))
	float ExhaustionSeconds = 0.f;
	UPROPERTY(EditAnywhere, Category = "Exhaustion")
	TObjectPtr<class UAnimMontage> ExhaustionMontage;
	// Unassigned damage starts at zero until the user chooses it; never inferred from raw damage ratios.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0"))
	float BrutalHPDamage = 0.f;
	// Original native distance is unknown. Asset-authored temporary distances are recorded in the report.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0", Units = "cm"))
	float BrutalAttackRange = 0.f;
	// Zero derives the minimum non-overlapping distance from the two live capsule radii.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0", Units = "cm"))
	float BrutalAlignmentDistance = 0.f;
	UPROPERTY(EditAnywhere, Category = "Brutal Attack")
	TObjectPtr<UAnimMontage> BrutalFrontPlayerMontage;
	UPROPERTY(EditAnywhere, Category = "Brutal Attack")
	TObjectPtr<UAnimMontage> BrutalBackPlayerMontage;
	UPROPERTY(EditAnywhere, Category = "Brutal Attack")
	TObjectPtr<UAnimMontage> BrutalFrontVictimMontage;
	UPROPERTY(EditAnywhere, Category = "Brutal Attack")
	TObjectPtr<UAnimMontage> BrutalBackVictimMontage;
	// Shared instant HP/Stamina damage GE; SetByCaller names match the existing Combo damage contract.
	UPROPERTY(EditAnywhere, Category = "Effects")
	TSubclassOf<class UGameplayEffect> DamageEffect;
	UPROPERTY(EditAnywhere, Category = "Effects")
	TSubclassOf<UGameplayEffect> DeadStateEffect;
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
	const FKZMonsterStaminaSettings& GetMonsterStaminaSettings() const { return MonsterStamina; }
	
private:
	UPROPERTY(EditAnywhere, Category = "Character|Monster Stamina")
	FKZMonsterStaminaSettings MonsterStamina;

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
