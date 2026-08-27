

#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "KhazanAssetData.generated.h"

USTRUCT()
struct FAssetEntry
{
	GENERATED_BODY()
	
public:
	UPROPERTY(EditDefaultsOnly)
	FGameplayTag AssetName;
	
	UPROPERTY(EditDefaultsOnly)
	FSoftObjectPath AssetPath;
	
	UPROPERTY(EditDefaultsOnly)
	TArray<FGameplayTag> AssetLabels;
};

USTRUCT()
struct FAssetSet
{
	GENERATED_BODY()
	
public:
	UPROPERTY(EditDefaultsOnly)
	TArray<FAssetEntry> AssetEntries;
};

UCLASS()
class KHAZAN_API UKhazanAssetData : public UPrimaryDataAsset
{
	GENERATED_BODY()
	
public:
	
private:
	UPROPERTY(EditDefaultsOnly)
	TMap<FName, FAssetSet> AssetGroupNameToSet;
};
