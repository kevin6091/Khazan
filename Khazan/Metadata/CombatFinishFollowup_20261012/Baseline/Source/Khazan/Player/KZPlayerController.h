

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "KZPlayerController.generated.h"

struct FGameplayTag;
struct FInputActionValue;

enum class EKZComboCommandPhase : uint8;

UCLASS()
class KHAZAN_API AKZPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AKZPlayerController(const FObjectInitializer& ObjectInitializer);
	UPROPERTY(EditDefaultsOnly, Category = "KZ|UI")
	TSubclassOf<class UKZCombatHUDWidget> CombatHUDClass;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "KZ|UI")
	TObjectPtr<UKZCombatHUDWidget> CombatHUD;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void SetupInputComponent() override;

private:
	class UKZAbilitySystemComponent* GetKZAbilitySystemComponent() const;

	void RouteAttackInput(const FGameplayTag& InputTag, const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase);
	void SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase);

	void AbilityInputTagPressed(const FGameplayTag& InputTag);
	void AbilityInputTagReleased(const FGameplayTag& InputTag);
	void AbilityInputTagCanceled(const FGameplayTag& InputTag);

	void Input_MoveStarted(const FInputActionValue& InputValue);
	void Input_Move(const FInputActionValue& InputValue);
	void Input_MoveReleased(const FInputActionValue& InputValue);

	void Input_Sprint(const FInputActionValue& InputValue);
	void Input_SprintReleased(const FInputActionValue& InputValue);
	void Input_SprintCanceled(const FInputActionValue& InputValue);

	void Input_TurnCamera(const FInputActionValue& InputValue);
	
	void Input_LockOnStarted(const FInputActionValue& InputValue);
	
	void Input_WeakAttackStarted(const FInputActionValue&);
	void Input_WeakAttackCompleted(const FInputActionValue&);
	void Input_WeakAttackCanceled(const FInputActionValue&);

	void Input_StrongAttackStarted(const FInputActionValue&);
	void Input_StrongAttackCompleted(const FInputActionValue&);
	void Input_StrongAttackCanceled(const FInputActionValue&);

	void Input_DodgeStarted(const FInputActionValue&);
	void Input_DodgeCompleted(const FInputActionValue&);
	void Input_DodgeCanceled(const FInputActionValue&);

	void Input_GuardPressed(const FInputActionValue&);
	void Input_GuardCompleted(const FInputActionValue&);
	void Input_GuardCanceled(const FInputActionValue&);

	void Input_HealStarted(const FInputActionValue&);
	void Input_HealCompleted(const FInputActionValue&);
	void Input_HealCanceled(const FInputActionValue&);

	void Input_BrutalAttackStarted(const FInputActionValue&);
	void Input_BrutalAttackCompleted(const FInputActionValue&);
	void Input_BrutalAttackCanceled(const FInputActionValue&);
	
	void Input_RBStarted(const FInputActionValue&);
	void Input_RBCompleted(const FInputActionValue&);
	void Input_RBCanceled(const FInputActionValue&);
protected:

};
