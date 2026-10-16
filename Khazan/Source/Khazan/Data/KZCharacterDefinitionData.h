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

UENUM(BlueprintType)
enum class EKZHitReactionType : uint8
{
	None,
	Short,
	Knockback,
	Launch,
	// Fixed front victim pose when configured; otherwise retains Knockback.
	VictimFront
};

/** Serialized original target/status gates. Evaluated on GT by AI/Ability only. */
USTRUCT(BlueprintType)
struct FKZCombatPatternCondition
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) float MinDistance = 0.f;
	UPROPERTY(EditAnywhere) float MaxDistance = 0.f; // zero: no distance limit
	UPROPERTY(EditAnywhere) float BaseYaw = 0.f;
	UPROPERTY(EditAnywhere) float LeftYaw = 180.f;
	UPROPERTY(EditAnywhere) float RightYaw = 180.f;
	UPROPERTY(EditAnywhere) float MinHeight = -1.e9f;
	UPROPERTY(EditAnywhere) float MaxHeight = 1.e9f;
	UPROPERTY(EditAnywhere) float MaxHP = -1.f; // negative: no HP gate
	UPROPERTY(EditAnywhere) bool bHPIsRatio = false;
	UPROPERTY(EditAnywhere) float MinStamina = 0.f;
	UPROPERTY(EditAnywhere) float MaxStamina = -1.f; // negative: no upper gate
	UPROPERTY(EditAnywhere) float WallCheckYaw = 0.f;
	UPROPERTY(EditAnywhere) float WallCheckDistance = 0.f;
	UPROPERTY(EditAnywhere) bool bRequireClearWall = true;
	UPROPERTY(EditAnywhere) bool bInvertTarget = false;
	bool Matches(const class AKZCharacter* Owner, const AActor* Target) const;
};

/** Presentation pools. Direction comes from a random variant, never the incoming attack angle. */
USTRUCT(BlueprintType)
struct FKZHitReactionSettings
{
	GENERATED_BODY()
	// Optional recipient material feedback; only accepted HP-damage producers
	// consume it. Authored native family mapping is documented, not inferred by GAS.
	UPROPERTY(EditAnywhere, Category = "Reaction|Audio")
	TObjectPtr<class USoundBase> ImpactSound;
	// Optional finite approved-hit burst. No effect is inferred from montage time.
	UPROPERTY(EditAnywhere, Category = "Reaction|VFX")
	TObjectPtr<class UParticleSystem> ImpactEffect;
	UPROPERTY(EditAnywhere, Category = "Reaction")
	TArray<TObjectPtr<class UAnimMontage>> ShortHits;
	// Nonempty: ordinary hits use additive presentation only, never the blocking Hit Ability.
	// Author no-root-motion local-space additive montages in KZHitReactionGroup/KZHitReaction.
	UPROPERTY(EditAnywhere, Category = "Reaction|Additive")
	TArray<TObjectPtr<UAnimMontage>> AdditiveHits;
	UPROPERTY(EditAnywhere, Category = "Reaction")
	TArray<TObjectPtr<UAnimMontage>> Knockbacks;
	UPROPERTY(EditAnywhere, Category = "Reaction")
	TArray<TObjectPtr<UAnimMontage>> Launches;
	// StrongCombo's fixed unpaired reaction. Assigned only on humanoid definitions;
	// the existing victim montage is reused without its paired root travel.
	UPROPERTY(EditAnywhere, Category = "Reaction")
	TObjectPtr<UAnimMontage> VictimFront;
	// Temporary project tuning for authored in-place hit clips; not original metadata distances.
	// The engine RootMotionSource uses world cm. Duration comes from the authored reaction section chain.
	UPROPERTY(EditAnywhere, Category = "Reaction|Movement", meta = (ClampMin = "0", Units = "cm"))
	float KnockbackDistance = 250.f;
	// Optional normalized distance-over-time profile; current monster curve is
	// assistant TEMP tuning, not recovered original curve keys.
	UPROPERTY(EditAnywhere, Category = "Reaction|Movement")
	TObjectPtr<class UCurveFloat> KnockbackTimeMappingCurve;
	UPROPERTY(EditAnywhere, Category = "Reaction|Movement", meta = (ClampMin = "0", Units = "cm"))
	float LaunchDistance = 120.f;
	UPROPERTY(EditAnywhere, Category = "Reaction|Movement", meta = (ClampMin = "0", Units = "cm"))
	float LaunchHeight = 150.f;
	UPROPERTY(EditAnywhere, Category = "Shield")
	TArray<TObjectPtr<UAnimMontage>> ShieldBlocks;
	UPROPERTY(EditAnywhere, Category = "Shield")
	bool bSystemGuardOnLockOn = false;
	// Original LockOnMoveInfoMap[Battle].SystemGuardFrontAngle=180; consumed here as a full cone.
	UPROPERTY(EditAnywhere, Category = "Shield", meta = (ClampMin = "0", ClampMax = "360", Units = "deg"))
	float SystemGuardFrontAngle = 180.f;
};

/** Monster-only policy. Resources remain on the ASC; these are editable data, not runtime state. */
USTRUCT(BlueprintType)
struct FKZPartWeakBox
{
	GENERATED_BODY()
	// Original CB xxDamageBoxComponent Group1 SCS attachment and relative transform.
	UPROPERTY(EditAnywhere, Category = "Part Destruction") FName Bone = NAME_None;
	UPROPERTY(EditAnywhere, Category = "Part Destruction") FVector RelativeLocation = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, Category = "Part Destruction") FRotator RelativeRotation = FRotator::ZeroRotator;
	UPROPERTY(EditAnywhere, Category = "Part Destruction") FVector RelativeScale = FVector::OneVector;
};

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
	// Original CS PartDestruction[Group1].Durability. Native damage conversion is unknown.
	UPROPERTY(EditAnywhere, Category = "Part Destruction", meta = (ClampMin = "0"))
	float PartGroup1Durability = 0.f;
	// Temporary project adapter: accepted attack HP damage * this value fills Group1 durability.
	UPROPERTY(EditAnywhere, Category = "Part Destruction", meta = (ClampMin = "0"))
	float PartGroup1DamageScale = 0.f;
	// TEMP: original xxDamageBoxComponent base extent is absent from CB export.
	UPROPERTY(EditAnywhere, Category = "Part Destruction", meta = (ClampMin = "0", Units = "cm"))
	float PartGroup1BaseHalfExtentCm = 32.f;
	// Original CB Group1 weak-point locations; box base half extent is a documented adapter.
	UPROPERTY(EditAnywhere, Category = "Part Destruction")
	TArray<FKZPartWeakBox> PartGroup1WeakBoxes;
	UPROPERTY(EditAnywhere, Category = "Part Destruction")
	TObjectPtr<UAnimMontage> PartGroup1GroggyMontage;
	// Optional finite death presentation. Default direction selection is an authoring adapter.
	// Gameplay death remains the existing ASC policy, outside this presentation receipt.
	UPROPERTY(EditAnywhere, Category = "Death")
	TObjectPtr<UAnimMontage> DeathPresentationMontage;
	// TEMP presentation blend requested for execution victim -> death. The
	// existing inertializer blends the last posed body into the death montage.
	UPROPERTY(EditAnywhere, Category = "Death", meta = (ClampMin = "0", Units = "s"))
	float DeathTransitionBlendSeconds = 0.24f;
	// Unassigned damage starts at zero until the user chooses it; never inferred from raw damage ratios.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0"))
	float BrutalHPDamage = 0.f;
	// Original native distance is unknown. Asset-authored temporary distances are recorded in the report.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0", Units = "cm"))
	float BrutalAttackRange = 0.f;
	// Zero derives the minimum non-overlapping distance from the two live capsule radii.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0", Units = "cm"))
	float BrutalAlignmentDistance = 0.f;
	// Original Grapple Start MoveTo duration .433283 s, CubicInOut; existing capsule spacing remains the target.
	UPROPERTY(EditAnywhere, Category = "Brutal Attack", meta = (ClampMin = "0", Units = "s"))
	float BrutalAlignmentSeconds = 0.433283f;
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
	const FKZHitReactionSettings& GetHitReactionSettings() const { return HitReactions; }
	class UStateTree* GetOriginalPatternStateTree() const { return OriginalPatternStateTree; }
	
private:
	// Owns original-pattern AI also for legacy placed Pawn AI overrides.
	UPROPERTY(EditAnywhere, Category = "Character|AI")
	TObjectPtr<class UStateTree> OriginalPatternStateTree;
	UPROPERTY(EditAnywhere, Category = "Character|Hit Reactions")
	FKZHitReactionSettings HitReactions;

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
