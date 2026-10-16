

#pragma once

#include "CoreMinimal.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Components/ActorComponent.h"
#include "KZLockOnComponent.generated.h"

class AKZMonster;

UCLASS( ClassGroup=(KZ), meta=(BlueprintSpawnableComponent) )
class KHAZAN_API UKZLockOnComponent : public UActorComponent
{
	GENERATED_BODY()

public:	
	UKZLockOnComponent();

	// LockOn 은 토글로한다.
	void ToggleLockOn();
	
	// 이 컴포넌트가 취득한 제약 하나랑 현재 Target만 정리함.
	void StopLockOn();
	
	// Target이랑 제약Handle이 모두 유효할때만 true
	bool IsLockedOn() const;
	
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	// 현재 카메라에서 보이는 후보 중 화면 중앙에 가장 가까운 대상을 찾는다.
	AKZMonster* FindBestLockOnTarget() const;

	// 카메라와 타깃 지점 사이에 다른 blocking actor가 있는지 검사한다.
	bool HasClearViewToTarget(const FVector& ViewLocation, const AKZMonster* Candidate, const FVector& TargetLocation) const;

	// 선택이 끝난 유효한 몬스터를 잠그고 이동 제약을 취득한다.
	bool StartLockOn(AKZMonster* Target);

	// 현재 타깃의 3차원 지점을 향해 카메라 ControlRotation을 보간한다.
	void UpdateLockOnFacing(float DeltaTime);

private:
	// 원작 카메라 보간값은 아직 확인되지 않았다.
	// 단위는 1/s이며 첫 시작값은 12.0이다.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|LockOn", meta = (ClampMin = "0.0"))
	float LockOnViewInterpSpeed = 12.0f;

	// 원작 LockOn Pitch 한계 미확인: 임시값 20도.
	// LockOn 중 수평선 아래를 내려다볼 수 있는 최대 각도다. 위를 보는 각도는 제한하지 않는다.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|LockOn|Camera", meta = (ClampMin = "0.0", ClampMax = "89.0"))
	double MaxLookDownAngleDegrees = 40.0;

	// 타깃이 파괴됐을 때 수명을 연장하지 않도록 약한 참조를 사용한다.
	UPROPERTY(Transient)
	TWeakObjectPtr<AKZMonster> CurrentTarget;

	// 이 TargetingComponent가 취득한 이동 제약 한 건의 해제 영수증이다.
	FKZMovementConstraintHandle LockOnConstraintHandle;
};
