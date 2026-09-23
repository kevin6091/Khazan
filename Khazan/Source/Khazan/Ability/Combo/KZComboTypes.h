#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "KZComboTypes.generated.h"

UENUM(BlueprintType)
enum class EKZComboCommandPhase : uint8
{

	// Player가 버튼을 누름, AI가 해당 공격 의도를 시작함, 해당 command를 held 상태로 만듦
	Begin,
	// Player가 정상적으로 버튼을 놓음, AI가 차지를 해제하기로 결정함, release edge를 선택할 수 있음
	Release,
	// Mapping Context 상실, AI 계획 취소, Possess 변경이나 action abort, held/pending 상태만 정리하며 공격 edge를 실행하지 않음
	Cancel
};

struct FKZComboCommand
{
	FKZComboCommand(const FGameplayTag& InCommandTag, const EKZComboCommandPhase InPhase)
		: CommandTag(InCommandTag), Phase(InPhase)
	{
	}

	FGameplayTag CommandTag;
	EKZComboCommandPhase Phase;
};