


#include "System/KhazanAssetManager.h"	

#include "KhazanGameplayTags.h"
#include "LogChannels.h"
#include "Data/KhazanAssetData.h"

UKhazanAssetManager::UKhazanAssetManager()
	:Super()
{
}

UKhazanAssetManager& UKhazanAssetManager::Get()
{
	if (UKhazanAssetManager* Singleton = Cast<UKhazanAssetManager>(GEngine->AssetManager))
	{
		return *Singleton;
	}

	UE_LOG(LogDefault, Fatal, TEXT("Cant find UKhazanAssetManager"));
	
	return *NewObject<UKhazanAssetManager>();
}

void UKhazanAssetManager::Initialize()
{
	Get().LoadPreloadAssets();
}

void UKhazanAssetManager::LoadSyncByPath(const FSoftObjectPath& AssetPath)
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
			UE_LOG(LogDefault, Fatal, TEXT("Failed to load asset [%s]"), *AssetPath.ToString());
		}
	}
}

void UKhazanAssetManager::LoadSyncByName(const FGameplayTag& AssetName)
{
	UKhazanAssetData* AssetData = Get().LoadedAssetData;
	check(AssetData);
	
	const FSoftObjectPath& AssetPath = AssetData->GetAssetPathByName(AssetName);
	LoadSyncByPath(AssetPath);
}

void UKhazanAssetManager::LoadSyncByLabel(const FGameplayTag& Label)
{
	if (UAssetManager::IsInitialized() == false)
	{
		UE_LOG(LogDefault, Error, TEXT("AssetManager must be initialized"));
		return;
	}
	
	UKhazanAssetData* AssetData = Get().LoadedAssetData;
	check(AssetData);
	
	TArray<FSoftObjectPath> AssetPaths;
	
	const FAssetSet& AssetSet = AssetData->GetAssetSetByLabel(Label);
	for (const FAssetEntry& AssetEntry : AssetSet.AssetEntries)
	{
		const FSoftObjectPath& AssetPath = AssetEntry.AssetPath;
		LoadSyncByPath(AssetPath);
		if (AssetPath.IsValid())
		{
			AssetPaths.Emplace(AssetPath);
		}
	}
	
	GetStreamableManager().RequestSyncLoad(AssetPaths);
	
	for (const FAssetEntry& AssetEntry : AssetSet.AssetEntries)
	{
		const FSoftObjectPath& AssetPath = AssetEntry.AssetPath;
		if (AssetPath.IsValid())
		{
			if (UObject* LoadedAsset = AssetPath.ResolveObject())
			{
				Get().AddLoadedAsset(AssetEntry.AssetName.GetTagName(), LoadedAsset);
			}
			else
			{
				UE_LOG(LogDefault, Fatal, TEXT("Failed to load asset [%s]"), *AssetPath.ToString());
			}
		}
	}
}

void UKhazanAssetManager::ReleaseByPath(const FSoftObjectPath& AssetPath)
{
	FName AssetName = AssetPath.GetAssetFName();
	ReleaseByName(AssetName);
}

void UKhazanAssetManager::ReleaseByName(const FName& AssetName)
{
	UKhazanAssetManager& AssetManager = Get();
	if (AssetManager.NameToLoadedAsset.Contains(AssetName))
	{
		AssetManager.NameToLoadedAsset.Remove(AssetName);
	}
	else
	{
		UE_LOG(LogDefault, Warning, TEXT("Cant find loaded asset by assetName [%s]"), *AssetName.ToString());
	}
}

void UKhazanAssetManager::ReleaseByLabel(const FGameplayTag& Label)
{
	UKhazanAssetManager& AssetManager = Get();
	UKhazanAssetData* LoadedAssetData = AssetManager.LoadedAssetData;
	const FAssetSet& AssetSet = LoadedAssetData->GetAssetSetByLabel(Label);
	
	for (const FAssetEntry& AssetEntry : AssetSet.AssetEntries)
	{
		const FGameplayTag& AssetName = AssetEntry.AssetName;
		if (AssetManager.NameToLoadedAsset.Contains(AssetName.GetTagName()))
		{
			AssetManager.NameToLoadedAsset.Remove(AssetName.GetTagName());
		}
		else
		{
			UE_LOG(LogDefault, Warning, TEXT("Cant find loaded asset by assetName [%s]"), *AssetName.ToString());
		}
	}
}

void UKhazanAssetManager::ReleaseAll()
{
	Get().NameToLoadedAsset.Reset();
}

void UKhazanAssetManager::LoadPreloadAssets()
{
	if (LoadedAssetData)
		return;
	
	UKhazanAssetData* AssetData = nullptr;
	FPrimaryAssetType PrimaryAssetType(UKhazanAssetData::StaticClass()->GetFName());
	TSharedPtr<FStreamableHandle> Handle = LoadPrimaryAssetsWithType(PrimaryAssetType);
	if (Handle.IsValid())
	{
		Handle->WaitUntilComplete(0.f, false);
		AssetData = Cast<UKhazanAssetData>(Handle->GetLoadedAsset());
	}
	
	if (AssetData)
	{
		LoadedAssetData = AssetData;
		LoadSyncByLabel(KhazanGameplayTags::AssetLabel_Preload);
	}
	else
	{
		UE_LOG(LogDefault, Fatal, TEXT("Failed to load AssetData asset type [%s]"), *PrimaryAssetType.ToString());
	}
}

void UKhazanAssetManager::AddLoadedAsset(const FName& AssetName, const UObject* Asset)
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
