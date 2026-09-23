

#include "KZGameInstance.h"
#include "KZAssetManager.h"

UKZGameInstance::UKZGameInstance(const FObjectInitializer& ObjectInitializer)
	:Super(ObjectInitializer)
{
}

void UKZGameInstance::Init()
{
	Super::Init();
	UKZAssetManager::Initialize();
}

void UKZGameInstance::Shutdown()
{
	Super::Shutdown();
}
