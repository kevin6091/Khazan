


#include "System/KZAssetManager.h"

#include "KZGameplayTags.h"
#include "LogChannels.h"
#include "Data/KZAssetData.h"

UKZAssetManager::UKZAssetManager()
	:Super()
{
}

UKZAssetManager& UKZAssetManager::Get()
{
	if (UKZAssetManager* Singleton = Cast<UKZAssetManager>(GEngine->AssetManager))
	{
		return *Singleton;
	}

	UE_LOG(LogDefault, Fatal, TEXT("Cant find UKZAssetManager"));

	return *NewObject<UKZAssetManager>();
}

void UKZAssetManager::Initialize()
{
	Get().LoadPreloadAssets();
}

void UKZAssetManager::LoadSyncByPath(const FSoftObjectPath& AssetPath)
{
	if (AssetPath.IsValid())
	{
		UObject* LoadedAsset = AssetPath.ResolveObject();
		if (LoadedAsset == nullptr)
		{
			if (UAssetManager::IsInitialized())
			{
				LoadedAsset = UAssetManager::GetStreamableManager().LoadSynchronous(AssetPath, false);
			}
			else
			{
				LoadedAsset = AssetPath.TryLoad();
			}
		}

		if (LoadedAsset)
		{
			Get().AddLoadedAsset(AssetPath.GetAssetFName(), LoadedAsset);
		}
		else
		{
			UE_LOG(LogDefault, Error, TEXT("Failed to load asset [%s]"), *AssetPath.ToString());
		}
	}
}

void UKZAssetManager::LoadSyncByName(const FGameplayTag& AssetName)
{
	UKZAssetData* AssetData = Get().LoadedAssetData;
	if (!AssetData)
	{
		UE_LOG(LogDefault, Error, TEXT("AssetData is not loaded."));
		return;
	}

	const FSoftObjectPath& AssetPath = AssetData->GetAssetPathByName(AssetName);
	LoadSyncByPath(AssetPath);
}

void UKZAssetManager::LoadSyncByLabel(const FGameplayTag& Label)
{
	if (UAssetManager::IsInitialized() == false)
	{
		UE_LOG(LogDefault, Error, TEXT("AssetManager must be initialized"));
		return;
	}

	UKZAssetData* AssetData = Get().LoadedAssetData;
	if (!AssetData)
	{
		UE_LOG(LogDefault, Error, TEXT("AssetData is not loaded."));
		return;
	}

	TArray<FSoftObjectPath> AssetPaths;

	const FAssetSet* AssetSet = AssetData->GetAssetSetByLabel(Label);
	if (!AssetSet)
	{
		return;
	}
	for (const FAssetEntry& AssetEntry : AssetSet->AssetEntries)
	{
		const FSoftObjectPath& AssetPath = AssetEntry.AssetPath;
		if (AssetPath.IsValid())
		{
			AssetPaths.Emplace(AssetPath);
		}
	}

	TSharedPtr<FStreamableHandle> Handle = GetStreamableManager().RequestSyncLoad(AssetPaths);

	for (const FAssetEntry& AssetEntry : AssetSet->AssetEntries)
	{
		const FSoftObjectPath& AssetPath = AssetEntry.AssetPath;
		if (AssetPath.IsValid())
		{
			if (UObject* LoadedAsset = AssetPath.ResolveObject())
			{
				Get().AddLoadedAsset(AssetPath.GetAssetFName(), LoadedAsset);
			}
			else
			{
				UE_LOG(LogDefault, Error, TEXT("Failed to load asset [%s]"), *AssetPath.ToString());
			}
		}
	}
}

void UKZAssetManager::ReleaseByPath(const FSoftObjectPath& AssetPath)
{
	FName AssetName = AssetPath.GetAssetFName();
	ReleaseByName(AssetName);
}

void UKZAssetManager::ReleaseByName(const FName& AssetName)
{
	UKZAssetManager& AssetManager = Get();
	if (AssetManager.NameToLoadedAsset.Contains(AssetName))
	{
		AssetManager.NameToLoadedAsset.Remove(AssetName);
	}
	else
	{
		UE_LOG(LogDefault, Warning, TEXT("Cant find loaded asset by assetName [%s]"), *AssetName.ToString());
	}
}

void UKZAssetManager::ReleaseByLabel(const FGameplayTag& Label)
{
	UKZAssetData* AssetData = Get().LoadedAssetData;
	if (!AssetData)
	{
		UE_LOG(LogDefault, Error, TEXT("AssetData is not loaded."));
		return;
	}

	const FAssetSet* AssetSet = AssetData->GetAssetSetByLabel(Label);
	if (!AssetSet)
	{
		return;
	}

	for (const FAssetEntry& AssetEntry : AssetSet->AssetEntries)
	{
		ReleaseByPath(AssetEntry.AssetPath);
	}
}

void UKZAssetManager::ReleaseAll()
{
	Get().NameToLoadedAsset.Reset();
}

void UKZAssetManager::LoadPreloadAssets()
{
	if (LoadedAssetData)
		return;

	UKZAssetData* AssetData = nullptr;
	FPrimaryAssetType PrimaryAssetType(UKZAssetData::StaticClass()->GetFName());
	TSharedPtr<FStreamableHandle> Handle = LoadPrimaryAssetsWithType(PrimaryAssetType);
	if (Handle.IsValid())
	{
		Handle->WaitUntilComplete(0.f, false);
		AssetData = Cast<UKZAssetData>(Handle->GetLoadedAsset());
	}

	if (AssetData)
	{
		LoadedAssetData = AssetData;
		LoadSyncByLabel(KZGameplayTags::AssetLabel_Preload);
	}
	else
	{
		UE_LOG(LogDefault, Error, TEXT("Failed to load AssetData asset type [%s]"), *PrimaryAssetType.ToString());
	}
}

void UKZAssetManager::AddLoadedAsset(const FName& AssetName, const UObject* Asset)
{
	if (AssetName.IsValid() && Asset)
	{
		//FScopeLock LoadedAssetsLock(&LoadedAssetsCritical);

		if (NameToLoadedAsset.Contains(AssetName) == false)
		{
			NameToLoadedAsset.Add(AssetName, Asset);
		}
	}
}
