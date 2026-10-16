

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "KZGameInstance.generated.h"

/**
 *
 */
UCLASS()
class KHAZAN_API UKZGameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	UKZGameInstance(const FObjectInitializer& ObjectInitializer);

public:
	virtual void Init() override;
	virtual void Shutdown() override;
};
