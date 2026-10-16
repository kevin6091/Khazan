#include "Level/KZLevelRouteCollisionActor.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AKZLevelRouteCollisionActor::AKZLevelRouteCollisionActor()
{
	PrimaryActorTick.bCanEverTick = false;
	SetCanBeDamaged(false);

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SceneRoot->SetMobility(EComponentMobility::Static);
	SetRootComponent(SceneRoot);

	BoundaryCollision = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("BoundaryCollision"));
	BoundaryCollision->SetupAttachment(SceneRoot);
	BoundaryCollision->SetMobility(EComponentMobility::Static);
	BoundaryCollision->SetGenerateOverlapEvents(false);
	BoundaryCollision->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	BoundaryCollision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	BoundaryCollision->SetCollisionObjectType(ECC_WorldStatic);
	BoundaryCollision->SetCollisionResponseToAllChannels(ECR_Block);
	BoundaryCollision->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	BoundaryCollision->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	BoundaryCollision->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
	BoundaryCollision->SetCollisionResponseToChannel(ECC_Destructible, ECR_Ignore);
	BoundaryCollision->CanCharacterStepUpOn = ECB_No;
	BoundaryCollision->SetCanEverAffectNavigation(true);

	BoundaryCollision->SetVisibility(false, true);
	BoundaryCollision->SetHiddenInGame(true);
	BoundaryCollision->SetCastShadow(false);
	BoundaryCollision->bCastHiddenShadow = false;
	BoundaryCollision->bRenderInMainPass = false;
	BoundaryCollision->bRenderInDepthPass = false;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMeshFinder(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMeshFinder.Succeeded())
	{
		BoundaryCollision->SetStaticMesh(CubeMeshFinder.Object);
	}
}

void AKZLevelRouteCollisionActor::ClearBoundaryInstances()
{
	BoundaryCollision->ClearInstances();
}

int32 AKZLevelRouteCollisionActor::AddBoundaryBox(
	const FVector& WorldCenter,
	const FRotator& WorldRotation,
	const FVector& HalfExtent)
{
	if (HalfExtent.X <= UE_SMALL_NUMBER ||
		HalfExtent.Y <= UE_SMALL_NUMBER ||
		HalfExtent.Z <= UE_SMALL_NUMBER)
	{
		return INDEX_NONE;
	}

	// /Engine/BasicShapes/Cube is 100 cm wide, so each local half extent is 50 cm.
	const FVector CubeScale = HalfExtent / 50.0;
	const FTransform WorldTransform(WorldRotation, WorldCenter, CubeScale);
	const FTransform RelativeTransform = WorldTransform.GetRelativeTransform(GetActorTransform());
	return BoundaryCollision->AddInstance(RelativeTransform, false);
}

void AKZLevelRouteCollisionActor::FinalizeBoundaryInstances()
{
	BoundaryCollision->BuildTreeIfOutdated(true, true);
	BoundaryCollision->MarkRenderStateDirty();
}

int32 AKZLevelRouteCollisionActor::GetBoundaryInstanceCount() const
{
	return BoundaryCollision->GetInstanceCount();
}
