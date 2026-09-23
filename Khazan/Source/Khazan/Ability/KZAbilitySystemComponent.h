#pragma once

#include "CoreMinimal.h"
#include "AbilitySystemComponent.h"
#include "Ability/Combo/KZComboTypes.h"
#include "GameplayTagContainer.h"
#include "KZAbilitySystemComponent.generated.h"

// 입력 태그로 Ability를 찾고 콤보 명령을 전달하는 프로젝트 ASC다.
UCLASS()
class KHAZAN_API UKZAbilitySystemComponent : public UAbilitySystemComponent
{
	GENERATED_BODY()

public:
	// 활성 콤보 Ability들에게 공격 명령 한 건을 알린다.
	DECLARE_EVENT_OneParam(UKZAbilitySystemComponent, FOnComboCommand, const FKZComboCommand&);

	// 버튼을 누른 입력을 해당 Input Tag의 Ability Spec에 전달한다.
	void AbilityInputTagPressed(const FGameplayTag& InputTag);

	// 버튼을 뗀 입력을 해당 Input Tag의 Ability Spec에 전달한다.
	void AbilityInputTagReleased(const FGameplayTag& InputTag);

	// 취소된 입력은 눌림 상태만 정리한다.
	void AbilityInputTagCanceled(const FGameplayTag& InputTag);

	// 같은 Input Tag를 가진 비활성 Ability 하나를 실행한다.
	bool TryActivateAbilityByInputTag(const FGameplayTag& InputTag);

	// 공격 명령을 저장하지 않고 현재 구독자에게 바로 보낸다.
	void SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase Phase);

	// 콤보 Ability가 명령 수신을 연결할 때 사용한다.
	FOnComboCommand& OnComboCommand()
	{
		return ComboCommandEvent;
	}

private:
	// SubmitComboCommand가 방송하는 내부 이벤트다.
	FOnComboCommand ComboCommandEvent;
};
