


#include "System/KhazanAssetManager.h"	
#include "LogChannels.h"

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
