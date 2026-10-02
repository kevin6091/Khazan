#pragma once

#include "CoreMinimal.h"
#include "AbilitySystemComponent.h"
#include "Ability/Combo/KZComboTypes.h"
#include "GameplayTagContainer.h"
#include "KZAbilitySystemComponent.generated.h"

class UKZComboDefinitionData;

// 입력 태그로 Ability를 찾고 콤보 명령을 전달하는 프로젝트 ASC다.
UCLASS()
class KHAZAN_API UKZAbilitySystemComponent : public UAbilitySystemComponent
{
	GENERATED_BODY()

public:
	// 다른 granted Combo Ability가 이 Definition의 EntryNode를 시작점으로 쓰는지 찾는다.
	bool HasComboEntry(const UKZComboDefinitionData* Definition, FName EntryNodeId,	FGameplayAbilitySpecHandle IgnoreHandle);

	// 위 조건에 맞는 Spec 하나를 찾아 InputPressed 상태를 넘기고 활성화한다.
	bool TryActivateComboEntry(
		const UKZComboDefinitionData* Definition,
		FName EntryNodeId,
		FGameplayAbilitySpecHandle IgnoreHandle,
		bool bInputPressed);
	
	// 활성 콤보 Ability들에게 공격 명령 한 건을 알린다.
	DECLARE_EVENT_OneParam(UKZAbilitySystemComponent, FOnComboCommand, const FKZComboCommand&);

	// 버튼을 누른 입력을 해당 Input Tag의 Ability Spec에 전달한다.
	void AbilityInputTagPressed(const FGameplayTag& InputTag, FGameplayAbilitySpecHandle RequestedHandle = FGameplayAbilitySpecHandle());
	// 버튼을 뗀 입력을 해당 Input Tag의 Ability Spec에 전달한다.
	void AbilityInputTagReleased(const FGameplayTag& InputTag);

	// 취소된 입력은 눌림 상태만 정리한다.
	void AbilityInputTagCanceled(const FGameplayTag& InputTag);

	// Begin/Release/Cancel로 held 목록을 갱신한 뒤 현재 Combo Ability에 바로 알린다.
	void SubmitComboCommand(const FGameplayTag& CommandTag, EKZComboCommandPhase Phase);
	
	// 콤보 Ability가 명령 수신을 연결할 때 사용한다.
	FOnComboCommand& OnComboCommand()
	{
		return ComboCommandEvent;
	}
	
	// 이 명령 버튼이 지금도 눌려 있는지 확인한다.
	bool IsComboCommandHeld(const FGameplayTag& CommandTag) const
	{
		return HeldComboCommands.HasTagExact(CommandTag);
	}

	// Notify가 현재 눌린 모든 명령을 검사할 때 읽는다. 호출자는 수정할 수 없다.
	const FGameplayTagContainer& GetHeldComboCommands() const
	{
		return HeldComboCommands;
	}

	// UnPossess/EndPlay에서 정상 Release 공격을 만들지 않고 모두 정리한다.
	void ClearComboCommands();

private:
	// SubmitComboCommand가 방송하는 내부 이벤트다.
	FOnComboCommand ComboCommandEvent;
	
	// Pawn 입력 수명 동안 현재 눌려 있는 논리 공격 명령이다.
	FGameplayTagContainer HeldComboCommands;
};
