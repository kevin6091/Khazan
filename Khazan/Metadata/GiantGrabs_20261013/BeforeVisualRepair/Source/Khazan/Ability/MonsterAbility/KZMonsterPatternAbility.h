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
	bool WasPatternRunCancelled(uint32 Run) const { return CompletedRun == Run && bCompletedRunCancelled; }
	void RegisterSkillObject(class AKZMonsterSkillObject* Object,uint32 Run);
protected:
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;
	virtual void ProcessMontageNotify(FName NotifyName) override;
	virtual void RecordAcceptedAttackHit(AActor* Target, float MontageTime, bool bCaptureWindow) override;
	virtual float GetNodeTransitionBlendSeconds(const FKZComboNode& Target) const override;
private:
	FName GetCooldownSkill(FName Skill) const;
	// An exact SI alias reuses its SB while consuming its own cooldown.
	UPROPERTY(EditDefaultsOnly, Category = "Monster Pattern") FName CooldownSkillOverride;
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
	TWeakObjectPtr<class UAnimInstance> CapturedVictimAnim;
	UPROPERTY(Transient) TObjectPtr<class UAnimMontage> CapturedVictimMontage;
	bool bCapturedVictimPaused=false;
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
	uint32 CompletedRun=0; // Actual GAS completion consumed by the owning StateTree task.
	bool bCompletedRunCancelled=false;
	UPROPERTY(EditDefaultsOnly,Category="Monster Pattern") TSubclassOf<class UGameplayEffect> CaptureEffect;
	// Source player interaction sequence; the capture GE owns the input/action state.
	UPROPERTY(EditDefaultsOnly,Category="Monster Pattern|Capture") TObjectPtr<class UAnimSequenceBase> VictimCaptureAnimation;
	// Assistant temporary presentation blend, kept in one editable owner setting.
	UPROPERTY(EditDefaultsOnly,Category="Monster Pattern|Capture",meta=(ClampMin="0",Units="s")) float VictimCaptureBlendSeconds=0.12f;
	// Source-timed Recovered CA_P_Kazan_Hold_Demon: 40 evaluated frames at
	// 30 fps. Other body bones continue moving after root frame 10; hold at
	// final frame 39 instead of replaying the displaced first 10 frames.
	UPROPERTY(EditDefaultsOnly,Category="Monster Pattern|Capture",meta=(ClampMin="0",Units="s")) float VictimCaptureHoldTimeSeconds=39.f/30.f;
	uint16 MovementSourceId=0;
	int32 MovementWindow=INDEX_NONE,MovementLoop=INDEX_NONE;
	uint8 PreviousRootMotionMode=0;
	bool bOwnsRootMotionMode=false;
};
