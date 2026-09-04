


#include "KhazanGameInstance.h"
#include "KhazanAssetManager.h"

UKhazanGameInstance::UKhazanGameInstance(const FObjectInitializer& ObjectInitializer)
	:Super(ObjectInitializer)
{
}

void UKhazanGameInstance::Init()
{
	Super::Init();
	
	UKhazanAssetManager::Initialize();
}

void UKhazanGameInstance::Shutdown()
{
	Super::Shutdown();
}
