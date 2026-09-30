

#pragma once

#include "CoreMinimal.h"
#include "Character/KZCharacter.h"
#include "KZMonster.generated.h"

class USceneComponent;

UCLASS()
class KHAZAN_API AKZMonster : public AKZCharacter
{
	GENERATED_BODY()

public:
	AKZMonster();

	virtual void Tick(float DeltaSeconds) override;

	const USceneComponent* GetLockOnTargetPoint() const
	{
		return LockOnTargetPoint.Get();
	}
protected:
	virtual void BeginPlay() override;

private:
	// 이 몬스터를 LockOn할 때 카메라가 바라볼 안정적인 기준점이다.
	// 실제 상대 위치는 몬스터별 Gameplay Blueprint에서 작성한다.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LockOn", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USceneComponent> LockOnTargetPoint;
	
};
