#pragma once
#include "CoreMinimal.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "KZMonsterPatternAbility.generated.h"

/** Owns original SB conditional steps while the existing StateTree waits for this GAS execution. */
UCLASS(Blueprintable)
class KHAZAN_API UKZMonsterPatternAbility : public UKZComboActionAbility
{
	GENERATED_BODY()
public:
	UKZMonsterPatternAbility();
	// Existing combat-result producer calls this only after an accepted result.
	void ReportPatternEvent(EKZPatternEvent Event);
	uint32 GetPatternRun() const { return PatternRun; }
	void RegisterSkillObject(class AKZMonsterSkillObject* Object,uint32 Run);
protected:
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;
	virtual void ProcessMontageNotify(FName NotifyName) override;
	virtual void RecordAcceptedAttackHit(AActor* Target, float MontageTime) override;
	virtual float GetNodeTransitionBlendSeconds(const FKZComboNode& Target) const override;
private:
	bool ResolveEvent(EKZPatternEvent Event, FName Notify = NAME_None);
	bool EnterPatternNode(FName Node);
	void TickPattern();
	float NodeTime() const;
	void RunActions(EKZPatternEvent Event, FName Notify=NAME_None);
	bool BeginCapture(class AKZCharacter* Victim,FName Socket);
	void ReleaseCapture();
	void UpdatePatternMovement();
	void ClearPatternMovement();
	UFUNCTION() void HandleWorldCollision(AActor* Self, AActor* Other, FVector Impulse, const FHitResult& Hit);
	FTimerHandle PatternTimer;
	FName PendingNextNode = NAME_None;
	FName ExecutingSkill = NAME_None;
	TWeakObjectPtr<class AKZMonster> BoundMonster;
	bool bNodeHitObserved = false;
	bool bPendingHitEvent = false;
	bool bPendingStepStart = true;
	TWeakObjectPtr<class AKZCharacter> PendingCapture;
	TWeakObjectPtr<class AKZCharacter> CapturedTarget;
	FActiveGameplayEffectHandle CaptureEffectHandle;
	uint8 CapturedMovementMode = 0;
	bool bAddedVictimIgnore=false,bAddedCasterIgnore=false;
	TWeakObjectPtr<class USceneComponent> CaptureOriginalParent;
	FName CaptureOriginalSocket;
	UPROPERTY(Transient) TObjectPtr<class UPhysicsHandleComponent> CapturePhysics;
	FName CapturedRagdollBone;
	FTransform CaptureMeshRelativeTransform;
	TMap<int32,int32> ActionCounts;
	TArray<TWeakObjectPtr<class AKZMonsterSkillObject>> SkillObjects;
	uint32 PatternRun=0; // Resource ownership only: old launched objects never join a later activation.
	UPROPERTY(EditDefaultsOnly,Category="Monster Pattern") TSubclassOf<class UGameplayEffect> CaptureEffect;
	uint16 MovementSourceId=0;
	int32 MovementWindow=INDEX_NONE,MovementLoop=INDEX_NONE;
	uint8 PreviousRootMotionMode=0;
	bool bOwnsRootMotionMode=false;
};
