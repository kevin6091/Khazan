

#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "KZDodgeAbility.generated.h"

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
	
	EKZDodgeDirection GetDodgeDirection() const
	{
		return DodgeDirection;
	}
	
private:
	UPROPERTY(EditDefaultsOnly, Category = "Dodge")
	EKZDodgeDirection DodgeDirection = EKZDodgeDirection::F;
};