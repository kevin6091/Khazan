

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "KhazanGameInstance.generated.h"

/**
 * 
 */
UCLASS()
class KHAZAN_API UKhazanGameInstance : public UGameInstance
{
	GENERATED_BODY()
	
public:
	UKhazanGameInstance(const FObjectInitializer& ObjectInitializer);
	
public:
	virtual void Init() override;
	virtual void Shutdown() override;
};
