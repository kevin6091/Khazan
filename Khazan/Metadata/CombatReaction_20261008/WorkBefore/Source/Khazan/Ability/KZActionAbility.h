

#pragma once

#include "CoreMinimal.h"
#include "Ability/KZGameplayAbility.h"
#include "KZActionAbility.generated.h"

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
	
private:
	bool bInputEnded = false;
};
