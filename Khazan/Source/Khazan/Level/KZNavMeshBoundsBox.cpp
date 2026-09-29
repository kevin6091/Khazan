#include "Level/KZNavMeshBoundsBox.h"

#include "Components/BoxComponent.h"

AKZNavMeshBoundsBox::AKZNavMeshBoundsBox(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	SourceBounds = CreateDefaultSubobject<UBoxComponent>(TEXT("SourceBounds"));
	SourceBounds->SetupAttachment(GetRootComponent());
	SourceBounds->SetBoxExtent(FVector(100.0));
	SourceBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SourceBounds->SetGenerateOverlapEvents(false);
	SourceBounds->SetCanEverAffectNavigation(false);
	SourceBounds->SetVisibility(false, true);
	SourceBounds->SetHiddenInGame(true);
}
