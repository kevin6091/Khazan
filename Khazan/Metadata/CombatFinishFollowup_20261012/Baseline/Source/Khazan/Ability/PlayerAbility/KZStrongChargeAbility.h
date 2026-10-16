#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboAttackAbility.h"
#include "KZStrongChargeAbility.generated.h"

// 차지 성공/실패 분기는 Combo Definition의 Edge가 맡는다.
// 이 클래스에는 StrongCharge 전용 상태나 하드코딩된 전환을 두지 않는다.
UCLASS()
class KHAZAN_API UKZStrongChargeAbility : public UKZComboAttackAbility
{
	GENERATED_BODY()
};
