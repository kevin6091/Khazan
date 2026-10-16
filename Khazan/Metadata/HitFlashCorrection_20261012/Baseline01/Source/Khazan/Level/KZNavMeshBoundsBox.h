#pragma once

#include "CoreMinimal.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "KZNavMeshBoundsBox.generated.h"

class UBoxComponent;

/**
 * Box-backed navigation bounds used to reproduce source nav regions without
 * depending on editor-only BSP brush creation.
 */
UCLASS()
class KHAZAN_API AKZNavMeshBoundsBox : public ANavMeshBoundsVolume
{
	GENERATED_BODY()

public:
	AKZNavMeshBoundsBox(const FObjectInitializer& ObjectInitializer);

private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "KZ|Navigation", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UBoxComponent> SourceBounds;
};
