

#pragma once

#include "CoreMinimal.h"
#include "Character/KhazanCharacter.h"
#include "Character/Component/KhazanLocomotionComponent.h"
#include "KhazanPlayer.generated.h"

UCLASS()
class KHAZAN_API AKhazanPlayer : public AKhazanCharacter
{
	GENERATED_BODY()
	
public:
	AKhazanPlayer();

public:	
	virtual void Tick(float DeltaTime) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void UnPossessed() override;
	
public:
	// PlayerController가 전달한 장치 입력을 현재 Controller의 raw 이동 Intent로 변환한다.
	void HandleInputMove(const FVector2D& MovementInput, const FRotator& ControlRotation);
	// 실제 Move Completed/Canceled 또는 UnPossess에서 현재 Player의 방향·세기·요청 gait를 정리한다.
	void HandleInputMoveReleased();
	
	// Sprint 입력 Started에서 토글 또는 홀드 요청을 기록한다.
	void HandleInputSprint();
	// Sprint 입력 Completed에서 홀드 방식의 요청을 해제한다.
	void HandleInputSprintReleased();
	// 입력 시스템이 Sprint를 취소하면 모드와 관계없이 요청을 해제한다.
	void HandleInputSprintCanceled();

private:
	// 현재 raw 입력과 Sprint 요청으로부터 RequestedGait만 갱신한다.
	// 속도나 CMC 설정은 직접 변경하지 않는다.
	void RefreshRequestedGait();
	
protected:
	UPROPERTY(Category = Character, VisibleAnywhere, BlueprintReadOnly)
	TObjectPtr<class USpringArmComponent> SpringArm;

	UPROPERTY(Category = Character, VisibleAnywhere, BlueprintReadOnly)
	TObjectPtr<class UCameraComponent> Camera;
	
	// raw InputAmount가 이 값보다 클 때 Run을 요청한다. 정확히 같은 값이면 Walk를 요청한다.
	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float RunInputThreshold = 0.6f;
	
	// 이 값 이하의 장치 입력은 실제 입력 해제로 처리한다.
	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float MoveInputDeadZone = 0.1f;
	
	// Sprint토글 스위치. true = 토글, false = 홀드
	UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input")
	bool bToggleSprint = true;

private:
	// 현재 Controller를 Source로 LocomotionComponent가 발급한
	// 이 Pawn 수명의 raw Intent 작성 권한이다.
	FKhazanLocomotionIntentHandle PlayerIntentHandle;
	
	bool bSprintRequested = false;

};
