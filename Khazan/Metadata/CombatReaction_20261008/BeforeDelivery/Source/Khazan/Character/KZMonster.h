

#pragma once

#include "CoreMinimal.h"
#include "Character/KZCharacter.h"
#include "GameplayEffectTypes.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZMonster.generated.h"

class USceneComponent;
class UStateTree;
class UGameplayAbility;
struct FKZUnawareRoutine;
struct FOnAttributeChangeData;
class UKZExhaustionAbility;

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
	bool IsCombatIncapacitated() const;
	UKZExhaustionAbility* GetActiveExhaustionAbility() const;
	void RequestCombatStateRefresh();
	void FinishDeathPresentation();

	const USceneComponent* GetLockOnTargetPoint() const
	{
		return LockOnTargetPoint.Get();
	}

	const FKZMonsterAISettings& GetAISettings() const { return AISettings; }
	UStateTree* GetAIStateTree() const { return AIStateTree; }
	TSubclassOf<UGameplayAbility> GetAlertAbility() const { return AlertAbility; }
	const TArray<TSubclassOf<UGameplayAbility>>& GetAttackAbilities() const { return AttackAbilities; }
	const FKZUnawareRoutine* ResolveUnawareRoutine(bool bAllowTalk = true) const;
	AKZMonster* GetTalkPartner() const;
	bool HasActiveTalkLoop() const;
	bool ShouldPatrolWhenUnaware() const { return bPatrolWhenUnaware; }
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
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
	// 이 몬스터를 LockOn할 때 카메라가 바라볼 안정적인 기준점이다.
	// 실제 상대 위치는 몬스터별 Gameplay Blueprint에서 작성한다.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LockOn", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USceneComponent> LockOnTargetPoint;
	
};
