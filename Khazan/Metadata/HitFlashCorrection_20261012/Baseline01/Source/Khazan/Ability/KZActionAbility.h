

#pragma once

#include "CoreMinimal.h"
#include "Ability/KZGameplayAbility.h"
#include "TimerManager.h"
#include "KZActionAbility.generated.h"

class UKZAnimNotify_CombatEffect;
class USceneComponent;
class USkeletalMeshComponent;
struct FBranchingPointNotifyPayload;

UCLASS(Abstract, Blueprintable)
class KHAZAN_API UKZActionAbility : public UKZGameplayAbility
{
	GENERATED_BODY()

public:
	UKZActionAbility();

	// true면 현재 몽타주가 Action 교체 허용 지점(InputEnd)을 지났다는 뜻이다.
	// 버튼 Release와는 다른 상태다.
	bool HasInputEnded() const
	{
		return bInputEnded;
	}

protected:
	virtual void EndAbility(
		FGameplayAbilitySpecHandle Handle,
		const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo,
		bool bReplicateEndAbility,
		bool bWasCancelled) override;

	// 새 Action node가 시작될 때 호출해 다시 Action 교체를 막는다.
	void ResetInputEnd();

	// 몽타주의 InputEnd Notify에 도달했을 때 호출해 Action 교체를 허용한다.
	void SetInputEnded();

	// 어빌리티가 종료될 때 자동으로 적용할 GameplayEffect
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Effects")
	TSubclassOf<UGameplayEffect> OnEndAbilityGameplayEffect;
	
	// Shared presentation lifetime for Combo and Brutal. Each execution owner
	// validates montage/instance and confirms its own gameplay hit.
	void StartCombatEffect(const UKZAnimNotify_CombatEffect& Effect,
		const FBranchingPointNotifyPayload& Payload, bool bConfirmedHit = false,
		float RecoveredWindowDuration = 0.f);
	void StopCombatEffect(FName EventId, int32 MontageInstanceId);
	void ClearCombatEffects(bool bNaturalCompletion = false);

	// Actual spawned resources belong to this Ability activation, never to the
	// shared notify asset. An ended finite effect can keep draining naturally.
	struct FActiveCombatEffect
	{
		TWeakObjectPtr<USceneComponent> Component;
		TWeakObjectPtr<USkeletalMeshComponent> InitialPoseMesh;
		FDelegateHandle InitialPoseHandle;
		void UnregisterInitialPose();
		FName EventId;
		int32 MontageInstanceId = INDEX_NONE;
		bool bDestroyOnNotifyEnd = false;
		bool bDestroyOnNotifyEndDeactived = false;
		bool bDestroyOnAnimEnd = false;
		bool OnNotifyEndDeattach = false;
		bool bNotifyEnded = false;
		bool bRecoveredAfterSourceEnd = false;
		FTimerHandle RecoveredEndTimer;
	};
	TArray<FActiveCombatEffect> ActiveCombatEffects;

private:
	bool bInputEnded = false;
};
