

#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "KZDodgeAbility.generated.h"

class UNiagaraSystem;
class UNiagaraComponent;
class USoundBase;

// 캐릭터 정면에서 오른쪽으로 도는 순서다.
// 방향 계산의 index와 이 순서가 일치해야 한다.
UENUM(BlueprintType)
enum class EKZDodgeDirection : uint8
{
	F  = 0 UMETA(DisplayName = "F"),
	RF = 1 UMETA(DisplayName = "RF"),
	R  = 2 UMETA(DisplayName = "R"),
	RB = 3 UMETA(DisplayName = "RB"),
	B  = 4 UMETA(DisplayName = "B"),
	LB = 5 UMETA(DisplayName = "LB"),
	L  = 6 UMETA(DisplayName = "L"),
	LF = 7 UMETA(DisplayName = "LF")
};

UCLASS()
class KHAZAN_API UKZDodgeAbility : public UKZComboActionAbility
{
	GENERATED_BODY()
	
public:
	UKZDodgeAbility();
	bool IsInvulnerableNow() const;
	bool OwnsInvulnerabilityTag() const { return bOwnsInvulnerabilityTag; }
	bool TryAvoidHit(AActor* Attacker, const FVector& Contact);
	
	EKZDodgeDirection GetDodgeDirection() const
	{
		return DodgeDirection;
	}
	
protected:
	virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
	virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;

private:
	void ClearInvulnerability();
	// User decision: first .1 gameplay seconds, independent of montage rate/section.
	UPROPERTY(EditDefaultsOnly, Category = "Dodge|Defense", meta = (ClampMin = "0", Units = "s"))
	float InvulnerabilitySeconds = 0.1f;
	UPROPERTY(EditDefaultsOnly, Category = "Dodge|Feedback") TObjectPtr<UNiagaraSystem> DodgeEffect;
	UPROPERTY(EditDefaultsOnly, Category = "Dodge|Feedback") TObjectPtr<UNiagaraSystem> SuccessEffect;
	UPROPERTY(EditDefaultsOnly, Category = "Dodge|Feedback") TObjectPtr<USoundBase> SuccessSound;
	// Assistant TEMP presentation scale, editable here; never an original-game value.
	UPROPERTY(EditDefaultsOnly, Category = "Dodge|Feedback", meta = (ClampMin = "0")) float DodgeEffectScale = 0.12f;
	UPROPERTY(EditDefaultsOnly, Category = "Dodge|Feedback", meta = (ClampMin = "0")) float SuccessEffectScale = 0.15f;
	FTimerHandle InvulnerabilityTimer;
	double InvulnerableUntil = 0.;
	uint32 DodgeExecution = 0;
	bool bOwnsInvulnerabilityTag = false;
	bool bSuccessFeedbackPlayed = false;
	TWeakObjectPtr<UNiagaraComponent> DodgeComponent;
	TWeakObjectPtr<UNiagaraComponent> SuccessComponent;
	UPROPERTY(EditDefaultsOnly, Category = "Dodge")
	EKZDodgeDirection DodgeDirection = EKZDodgeDirection::F;
};
