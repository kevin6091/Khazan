

#pragma once

#include "CoreMinimal.h"
#include "Character/KZCharacter.h"
#include "GameplayEffectTypes.h"
#include "UObject/StrongObjectPtr.h"
#include "Materials/MaterialInterface.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZMonster.generated.h"

class USceneComponent;
class UStateTree;
class UGameplayAbility;
struct FKZUnawareRoutine;
struct FOnAttributeChangeData;
class UKZExhaustionAbility;
class UKZAnimNotifyState_MonsterVisual;
class UAnimInstance;
class UAnimMontage;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UParticleSystem;
struct FAnimNotifyEventReference;

/** Several Yetuga rows may select the same skill in different distance bands. */
USTRUCT(BlueprintType)
struct FKZMonsterSkillChoice
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) FName Skill = NAME_None;
	UPROPERTY(EditAnywhere) TSubclassOf<UGameplayAbility> Ability;
	UPROPERTY(EditAnywhere) FKZCombatPatternCondition Condition;
	UPROPERTY(EditAnywhere) float Weight = 0.f;
	UPROPERTY(EditAnywhere, meta = (Units = "s")) float EndCooldown = 0.f;
	UPROPERTY(EditAnywhere, meta = (Units = "s")) float BattleStartCooldown = 0.f;
	UPROPERTY(EditAnywhere) FString Source;
};

/** Original AIData is not available. These are temporary, editable cm/s/degree settings. */
USTRUCT(BlueprintType)
struct FKZMonsterAISettings
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Perception", meta = (ClampMin = "0"))
	float SightRadius = 1400.f;
	UPROPERTY(EditAnywhere, Category = "Perception", meta = (ClampMin = "0"))
	float LoseSightRadius = 1800.f;
	UPROPERTY(EditAnywhere, Category = "Perception", meta = (ClampMin = "0", ClampMax = "180"))
	float PeripheralVisionHalfAngle = 90.f;
	UPROPERTY(EditAnywhere, Category = "Perception", meta = (ClampMin = "0"))
	float TargetMemorySeconds = 4.f;
	UPROPERTY(EditAnywhere, Category = "Perception", meta = (ClampMin = "0"))
	float PursuitLeashRadius = 3000.f;

	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0"))
	float EngageDistance = 350.f;
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0"))
	float PreferredDistance = 240.f;
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0"))
	float DistanceTolerance = 45.f;
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0"))
	float AttackDistance = 310.f;
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0", ClampMax = "180"))
	float AttackFacingHalfAngle = 45.f;
	// Temporary tuning, not original AI data. CMC combines this bounded aim with authored root yaw.
	UPROPERTY(EditAnywhere, Category = "Combat|Facing", meta = (ClampMin = "0", Units = "deg/s"))
	float AttackTrackingYawRate = 60.f;
	UPROPERTY(EditAnywhere, Category = "Combat|Facing", meta = (ClampMin = "0", Units = "deg/s"))
	float ComboReaimYawRate = 180.f;
	UPROPERTY(EditAnywhere, Category = "Combat|Facing", meta = (ClampMin = "0", Units = "s"))
	float AttackPreparationSeconds = 0.15f;
	UPROPERTY(EditAnywhere, Category = "Combat")
	// Existing temporary interval / 1.1: user requested roughly 10% more frequent attacks.
	FVector2D AttackIntervalSeconds = FVector2D(2.f / 1.1f, 4.f / 1.1f);
	UPROPERTY(EditAnywhere, Category = "Combat")
	FVector2D StandoffSeconds = FVector2D(1.f, 2.5f);
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0"))
	float StrafeStepDistance = 160.f;
	// Left/right/third choice. Human monsters retain their left/right/pause policy.
	UPROPERTY(EditAnywhere, Category = "Combat")
	FVector StandoffDirectionWeights = FVector::OneVector;
	UPROPERTY(EditAnywhere, Category = "Combat")
	bool bBackwardStandoff = false;
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0", ClampMax = "1"))
	float ContinueComboChance = 0.85f; // Temporary tuning: +10 percentage points of combo continuation.
	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0"))
	float ChaseReactionSeconds = 0.4f; // Temporary tuning: brief reaction after action completion.

	UPROPERTY(EditAnywhere, Category = "Idle", meta = (ClampMin = "0"))
	float PatrolRadius = 300.f;
	UPROPERTY(EditAnywhere, Category = "Idle")
	FVector2D IdleSeconds = FVector2D(2.f, 5.f);
	UPROPERTY(EditAnywhere, Category = "Idle", meta = (ClampMin = "0", ClampMax = "1"))
	float PatrolChance = 0.5f;
	UPROPERTY(EditAnywhere, Category = "Navigation", meta = (ClampMin = "0"))
	float MoveAcceptanceRadius = 35.f;
	UPROPERTY(EditAnywhere, Category = "Navigation", meta = (ClampMin = "0"))
	float PathRetrySeconds = 0.5f;
	UPROPERTY(EditAnywhere, Category = "Navigation", meta = (ClampMin = "0"))
	float StandoffGoalRefreshSeconds = 0.35f;
};

UCLASS()
class KHAZAN_API AKZMonster : public AKZCharacter
{
	GENERATED_BODY()

public:
	AKZMonster();

	virtual void Tick(float DeltaSeconds) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void UnPossessed() override;
	UFUNCTION(BlueprintCallable, Category = "Monster|Stamina")
	bool ReportAttackParried(AActor* Defender);
	bool TrySystemGuard(float StaminaDamage, AActor* Attacker);
	bool IsCombatIncapacitated() const;
	UKZExhaustionAbility* GetActiveExhaustionAbility() const;
	void RequestCombatStateRefresh();
	void FinishDeathPresentation(bool bPlayDeathAnimation = true);
	// Called once per accepted unblocked hit, including lethal/exhausted hits.
	void PlayHitBlood(AActor* Attacker, const FVector& Contact);
	void BeginMonsterVisual(const UKZAnimNotifyState_MonsterVisual& Data,
		USkeletalMeshComponent* InMesh, const FAnimNotifyEventReference& Reference);
	void TickMonsterVisual(const UKZAnimNotifyState_MonsterVisual& Data,
		USkeletalMeshComponent* InMesh, const FAnimNotifyEventReference& Reference);
	void EndMonsterVisual(USkeletalMeshComponent* InMesh, int32 NotifyId, bool bReachedEnd);
	void EndMonsterVisualContext(USkeletalMeshComponent* InMesh, const FAnimNotifyEventReference& Reference);
	void ClearMonsterVisuals();

	const USceneComponent* GetLockOnTargetPoint() const
	{
		return LockOnTargetPoint.Get();
	}

	const FKZMonsterAISettings& GetAISettings() const { return AISettings; }
	UStateTree* GetAIStateTree() const { return AIStateTree; }
	TSubclassOf<UGameplayAbility> GetAlertAbility() const { return AlertAbility; }
	const TArray<TSubclassOf<UGameplayAbility>>& GetAttackAbilities() const { return AttackAbilities; }
	const TArray<FKZMonsterSkillChoice>& GetCombatPatterns() const { return CombatPatterns; }
	bool UsesOrderedPatterns() const { return bOrderedCombatPatterns; }
	const FKZUnawareRoutine* ResolveUnawareRoutine(bool bAllowTalk = true) const;
	AKZMonster* GetTalkPartner() const;
	bool HasActiveTalkLoop() const;
	bool ShouldPatrolWhenUnaware() const { return bPatrolWhenUnaware; }
	// Presentation configuration only. Yetuga opts into the top-screen boss gauge in its BP.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Monster|UI")
	bool bUseBossCombatHUD = false;
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Monster|UI")
	bool bUseEliteCombatGauge = false;
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Monster|UI")
	FText CombatDisplayName;
	// Author to the mesh's actual head bone; None uses the live capsule's top.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Monster|UI")
	FName CombatGaugeHeadBone = NAME_None;
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Monster|UI")
	FName CombatReticleSocket = TEXT("UI_Chest");
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Blood") TObjectPtr<UParticleSystem> HitBloodEffect;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Blood") TObjectPtr<UMaterialInterface> HitBloodDecalMaterial;
	// Screenshot matching, assistant temporary tuning: projector depth / half width / half length, cm.
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Blood", meta = (Units = "cm"))
	FVector HitBloodDecalSize = FVector(8.f, 95.f, 150.f);
	// Finite ground evidence survives the victim's death; the engine component owns fade and destruction.
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Blood", meta = (ClampMin = "0", Units = "s"))
	float HitBloodDecalHoldSeconds = 24.f;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Blood", meta = (ClampMin = "0.01", Units = "s"))
	float HitBloodDecalFadeSeconds = 3.f;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Blood", meta = (ClampMin = "0", Units = "cm"))
	float HitBloodGroundTraceDistance = 600.f;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Death") TObjectPtr<UParticleSystem> DeathAshEffect;
	// Assistant temporary presentation duration; shared death timing was not recovered from the original.
	UPROPERTY(EditDefaultsOnly, Category = "Monster|Death", meta = (ClampMin = "0.01", Units = "s"))
	float DeathDissolveSeconds = 3.f;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	struct FVisualMaterialWrite
	{
		TWeakObjectPtr<UMaterialInstanceDynamic> Material;
		FName Parameter;
		bool bVector = false;
		float ScalarBaseline = 0.f, LastScalar = 0.f;
		FLinearColor VectorBaseline = FLinearColor::Black, LastVector = FLinearColor::Black;
	};
	struct FVisualMaterialBinding
	{
		TWeakObjectPtr<USkeletalMeshComponent> MeshComponent;
		int32 Slot = INDEX_NONE; // INDEX_NONE owns the engine overlay slot.
		TStrongObjectPtr<UMaterialInterface> Baseline;
		TWeakObjectPtr<UMaterialInstanceDynamic> Installed;
	};
	struct FMonsterVisualReceipt
	{
		TWeakObjectPtr<USkeletalMeshComponent> Mesh;
		TWeakObjectPtr<UAnimInstance> AnimInstance;
		TWeakObjectPtr<const UKZAnimNotifyState_MonsterVisual> Data;
		int32 NotifyId = INDEX_NONE;
		TWeakObjectPtr<const UObject> Source;
		int32 MontageInstanceId = INDEX_NONE;
		uint32 AssetPlayerInstanceId = uint32(INDEX_NONE);
		bool bNotifyEnded = false;
		bool bTerminalMaterialHold = false; // Exact owned death execution's final rendering transaction.
		bool bCorpseMaterialOwner = false; // Completed paired animation transferred this same transaction.
		TWeakObjectPtr<UKZExhaustionAbility> PairedMaterialOwner;
		TArray<TWeakObjectPtr<USceneComponent>> Components;
		TArray<FVisualMaterialWrite> MaterialWrites;
		TArray<FVisualMaterialBinding> MaterialBindings;
		FTransform CorrectionLocal = FTransform::Identity;
		float LatestSourceTime = 0.f; // Notify clock handed to this frame's finalized-bone callback.
		float StartTime = 0.f;
		float FadeStartTime = -1.f;
		FDelegateHandle InitialPoseHandle; // Retained through the notify only for source-correction curves.
	};
	TArray<FMonsterVisualReceipt> MonsterVisuals;
	void ReleaseMonsterVisual(FMonsterVisualReceipt& Receipt, bool bReachedEnd, bool bForce);
	void RestoreVisualMaterials(const FMonsterVisualReceipt& Receipt);
	void RestoreVisualBindings(const FMonsterVisualReceipt& Receipt);
	bool CanHoldDeathVisualMaterials(const FMonsterVisualReceipt& Receipt) const;
	TWeakObjectPtr<UAnimInstance> DeathPresentationAnim;
	TWeakObjectPtr<UAnimMontage> DeathPresentationMontage;
	int32 DeathPresentationInstanceId = INDEX_NONE;
	void HandleDeathPresentationEnded(UAnimMontage* Montage, bool bInterrupted);
	void FreezeDeathPresentation(bool bKeepTerminalMaterials = false);
	void ClearDeathPresentationBinding();
	void CancelDeathPresentation();
	void BeginDeathDissolve();
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> DeathMaterials;
	float DeathDissolveElapsed = -1.f; // This corpse presentation's lifetime only; HP/Dead remain ASC-owned.

	void BindCombatAttributes();
	void UnbindCombatAttributes();
	void HandleCombatAttributeChanged(const FOnAttributeChangeData& Change);
	void RefreshCombatState();
	TWeakObjectPtr<UAbilitySystemComponent> BoundCombatASC;
	FDelegateHandle HealthChangedHandle;
	FDelegateHandle StaminaChangedHandle;
	FTimerHandle CombatRefreshTimer;
	FActiveGameplayEffectHandle DeadStateHandle;
	FKZMovementConstraintHandle DeadMovementHandle;

	// Placement settings, not a second runtime behaviour state.
	UPROPERTY(EditInstanceOnly, Category = "Monster|Unaware")
	bool bPatrolWhenUnaware = false;
	UPROPERTY(EditInstanceOnly, Category = "Monster|Unaware", meta = (ToolTip = "None selects a random solo routine from CharacterDefinition."))
	FName UnawareRoutineName = NAME_None;
	UPROPERTY(EditInstanceOnly, Category = "Monster|Unaware")
	TObjectPtr<AKZMonster> TalkPartner;
	UPROPERTY(EditInstanceOnly, Category = "Monster|Unaware")
	bool bSecondTalkRole = false;

	UPROPERTY(EditDefaultsOnly, Category = "Monster|AI")
	FKZMonsterAISettings AISettings;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|AI")
	TObjectPtr<UStateTree> AIStateTree;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|AI")
	TSubclassOf<UGameplayAbility> AlertAbility;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|AI")
	TArray<TSubclassOf<UGameplayAbility>> AttackAbilities;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|AI|Original Patterns", meta = (TitleProperty = "{Skill} [{Source}]"))
	TArray<FKZMonsterSkillChoice> CombatPatterns;
	UPROPERTY(EditDefaultsOnly, Category = "Monster|AI|Original Patterns")
	bool bOrderedCombatPatterns = false;
	// 이 몬스터를 LockOn할 때 카메라가 바라볼 안정적인 기준점이다.
	// 실제 상대 위치는 몬스터별 Gameplay Blueprint에서 작성한다.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LockOn", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USceneComponent> LockOnTargetPoint;
	
};
