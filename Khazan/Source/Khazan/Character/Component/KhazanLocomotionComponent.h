

#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "Delegates/Delegate.h"
#include "KhazanLocomotionComponent.generated.h"

class UAbilitySystemComponent;
class UKhazanLocomotionComponent;

struct KHAZAN_API FKhazanLocomotionIntentHandle
{
public:
	bool IsValid() const
	{
		return Owner.IsValid() && Id.IsValid();
	}

	void Reset()
	{
		Owner.Reset();
		Id.Invalidate();
	}

private:
	friend class UKhazanLocomotionComponent;

	TWeakObjectPtr<UKhazanLocomotionComponent> Owner;
	FGuid Id;
};

USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanMovementConstraintHandle
{
	GENERATED_BODY()

public:
	bool IsValid() const
	{
		return Owner.IsValid() && Id.IsValid();
	}

	void Reset()
	{
		Owner.Reset();
		Id.Invalidate();
	}

private:
	friend class UKhazanLocomotionComponent;

	UPROPERTY(Transient)
	TWeakObjectPtr<UKhazanLocomotionComponent> Owner;

	UPROPERTY(Transient)
	FGuid Id;
};

DECLARE_MULTICAST_DELEGATE_OneParam(FKhazanMovementInputPermissionChanged, bool /* bMovementAllowed */);

UCLASS(ClassGroup = (Khazan), meta = (BlueprintSpawnableComponent))
class KHAZAN_API UKhazanLocomotionComponent : public UActorComponent
{
	GENERATED_BODY()
	
public:
	UKhazanLocomotionComponent();

public:
	void SetMoveInputWorld(const FVector& Input);
	void ClearMoveInput();
	
	void SetTargetGait(EKhazanGait Gait);
	void SetMaxAllowedGait(EKhazanGait Gait);
	void SetRotationMode(EKhazanRotationMode Mode);
	
	bool IsMovementInputAllowed() const;
	
	EKhazanGait GetResolvedGait() const;
	
	const FKhazanLocomotionIntent& GetIntent() const
	{
		return Intent;
	}
	
protected:
	virtual void BeginPlay() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
		
private:
	//태그 변화 알림을 받는 함수
	void HandleMovementBlockChanged(const FGameplayTag Tag, int32 NewCount);
	// 현재 ASC 값을 읽어 허용 결과 계산
	void RefreshMovementPermission();
	
private:
	UPROPERTY(Transient)
	TWeakObjectPtr<UAbilitySystemComponent> ObservedAbilitySystemComponent;

	FDelegateHandle MovementBlockChangedHandle;
	
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Locomotion", meta = (AllowPrivateAccess = "true"))
	FKhazanLocomotionIntent Intent;
};
