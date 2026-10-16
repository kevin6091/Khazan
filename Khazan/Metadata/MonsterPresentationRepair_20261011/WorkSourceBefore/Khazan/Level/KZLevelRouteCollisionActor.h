#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KZLevelRouteCollisionActor.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class USceneComponent;

/**
 * Serialized level-boundary collision reconstructed from authored source data.
 *
 * The actor owns collision geometry only. CharacterMovementComponent remains
 * responsible for moving every player or AI character against these bounds.
 */
UCLASS()
class KHAZAN_API AKZLevelRouteCollisionActor : public AActor
{
	GENERATED_BODY()

public:
	AKZLevelRouteCollisionActor();

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "KZ|Level Route Collision")
	void ClearBoundaryInstances();

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "KZ|Level Route Collision")
	int32 AddBoundaryBox(const FVector& WorldCenter, const FRotator& WorldRotation, const FVector& HalfExtent);

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "KZ|Level Route Collision")
	void FinalizeBoundaryInstances();

	UFUNCTION(BlueprintPure, Category = "KZ|Level Route Collision")
	int32 GetBoundaryInstanceCount() const;

private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "KZ|Level Route Collision", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "KZ|Level Route Collision", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> BoundaryCollision;
};
