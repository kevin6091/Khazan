
#include "KhazanCharacter.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "Component/KhazanLocomotionComponent.h"
#include "Components/CapsuleComponent.h"

// Sets default values
AKhazanCharacter::AKhazanCharacter()
{
 	// Set this character to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;
	LocomotionComponent = CreateDefaultSubobject<UKhazanLocomotionComponent>(TEXT("LocomotionComponent"));
}

// Called when the game starts or when spawned
void AKhazanCharacter::BeginPlay()
{
	Super::BeginPlay();
	
}
 
// Called every frame
void AKhazanCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

