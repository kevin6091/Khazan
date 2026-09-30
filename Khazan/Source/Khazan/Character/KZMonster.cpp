


#include "Character/KZMonster.h"

#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"

AKZMonster::AKZMonster()
{
	LockOnTargetPoint = CreateDefaultSubobject<USceneComponent>(TEXT("LockOnTargetPoint"));
	
	LockOnTargetPoint->SetupAttachment(GetCapsuleComponent());
}

void AKZMonster::BeginPlay()
{
	Super::BeginPlay();
}

void AKZMonster::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
}
