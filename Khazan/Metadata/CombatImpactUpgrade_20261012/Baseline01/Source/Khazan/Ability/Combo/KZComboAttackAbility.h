

#pragma once

#include "CoreMinimal.h"
#include "KZComboActionAbility.h"
#include "KZComboAttackAbility.generated.h"

// 콤보 데이터를 읽어 몽타주와 다음 공격 전환을 실행하는 공통 Ability다.
UCLASS(Abstract, Blueprintable)
class KHAZAN_API UKZComboAttackAbility : public UKZComboActionAbility
{
	GENERATED_BODY()

public:
	// 공격 공통 태그와 실행 방식을 설정한다.
	UKZComboAttackAbility();
};
