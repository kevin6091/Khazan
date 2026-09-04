

#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Components/ActorComponent.h"
#include "KhazanLocomotionComponent.generated.h"

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
	void SetMovementAllowed(bool bAllowed);
	
	EKhazanGait GetResolvedGait() const;
	
	const FKhazanLocomotionIntent& GetIntent() const
	{
		return Intent;
	}
	
private:
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Locomotion", meta = (AllowPrivateAccess = "true"))
	FKhazanLocomotionIntent Intent;
};
