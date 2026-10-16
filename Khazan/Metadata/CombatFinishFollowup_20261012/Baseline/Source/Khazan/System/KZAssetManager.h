

#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "LogChannels.h"
#include "Data/KZAssetData.h"
#include "Engine/AssetManager.h"
#include "KZAssetManager.generated.h"

class UKZAssetData;

UCLASS()
class KHAZAN_API UKZAssetManager : public UAssetManager
{
	GENERATED_BODY()

public:
	UKZAssetManager();

	static UKZAssetManager& Get();

public:
	static void Initialize();

	template<typename AssetType>
	static AssetType* GetAssetByName(const FGameplayTag& AssetName, const bool bLoadIfMissing = true);

	static void LoadSyncByPath(const FSoftObjectPath& AssetPath);
	static void LoadSyncByName(const FGameplayTag& AssetName);
	static void LoadSyncByLabel(const FGameplayTag& Label);

	static void ReleaseByPath(const FSoftObjectPath& AssetPath);
	static void ReleaseByName(const FName& AssetName);
	static void ReleaseByLabel(const FGameplayTag& Label);
	static void ReleaseAll();

private:
	void LoadPreloadAssets();
	void AddLoadedAsset(const FName& AssetName, const UObject* Asset);

private:
	UPROPERTY()
	TObjectPtr<UKZAssetData> LoadedAssetData;

	UPROPERTY()
	TMap<FName, TObjectPtr<const UObject>> NameToLoadedAsset;

	//FCriticalSection LoadedAssetesCritical;
};

template <typename AssetType>
AssetType* UKZAssetManager::GetAssetByName(const FGameplayTag& AssetName, const bool bLoadIfMissing)
{
	UKZAssetData* AssetData = Get().LoadedAssetData;
	if (!AssetData)
	{
		UE_LOG(LogDefault, Error, TEXT("AssetData is not loaded."));
		return nullptr;
	}

	AssetType* LoadedAsset = nullptr;
	const FSoftObjectPath& AssetPath = AssetData->GetAssetPathByName(AssetName);
	if (AssetPath.IsValid())
	{
		LoadedAsset = Cast<AssetType>(AssetPath.ResolveObject());
		if (LoadedAsset == nullptr && bLoadIfMissing)
		{
			UE_LOG(LogDefault, Warning, TEXT("Attempted sync loading because asset hadn't loaded yet [%s]/"), *AssetPath.ToString());
			LoadedAsset = Cast<AssetType>(AssetPath.TryLoad());
		}
	}

	return LoadedAsset;
}
