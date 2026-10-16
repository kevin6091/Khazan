#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KZNavModifierBox.generated.h"

class UBoxComponent;
class UNavModifierComponent;

/**
 * Box-backed NavArea_Null modifier reconstructed from source volume metadata.
 *
 * The box is query-only and ignores every collision channel. It exists solely
 * to provide the authored oriented bounds to the navigation modifier.
 */
UCLASS()
class KHAZAN_API AKZNavModifierBox : public AActor
{
	GENERATED_BODY()

public:
	AKZNavModifierBox();

private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "KZ|Navigation", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UBoxComponent> SourceBounds;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "KZ|Navigation", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UNavModifierComponent> NavModifier;
};
