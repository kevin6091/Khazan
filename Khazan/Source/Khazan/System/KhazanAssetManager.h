

#pragma once

#include "CoreMinimal.h"
#include "Engine/AssetManager.h"
#include "KhazanAssetManager.generated.h"

UCLASS()
class KHAZAN_API UKhazanAssetManager : public UAssetManager
{
	GENERATED_BODY()
	
public:
	UKhazanAssetManager();
	
	static UKhazanAssetManager& Get();
};
