#include "Level/KZNavModifierBox.h"

#include "Components/BoxComponent.h"
#include "NavModifierComponent.h"

AKZNavModifierBox::AKZNavModifierBox()
{
	PrimaryActorTick.bCanEverTick = false;
	SetCanBeDamaged(false);

	SourceBounds = CreateDefaultSubobject<UBoxComponent>(TEXT("SourceBounds"));
	SourceBounds->SetMobility(EComponentMobility::Static);
	SourceBounds->SetBoxExtent(FVector(100.0), false);
	SourceBounds->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	SourceBounds->SetCollisionResponseToAllChannels(ECR_Ignore);
	SourceBounds->SetGenerateOverlapEvents(false);
	SourceBounds->SetCanEverAffectNavigation(true);
	SourceBounds->CanCharacterStepUpOn = ECB_No;
	SourceBounds->SetVisibility(false, true);
	SourceBounds->SetHiddenInGame(true);
	SetRootComponent(SourceBounds);

	// UNavModifierComponent defaults to UNavArea_Null, matching the source
	// NavModifierVolume actors whose AreaClass property is not overridden.
	NavModifier = CreateDefaultSubobject<UNavModifierComponent>(TEXT("NavModifier"));
}
