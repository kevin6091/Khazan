

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "KZGameMode.generated.h"

/**
 *
 */
UCLASS()
class KHAZAN_API AKZGameMode : public AGameModeBase
{
	GENERATED_BODY()

private:
	void BeginPlay() override;
};
