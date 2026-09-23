

#pragma once

#include "CoreMinimal.h"
#include "Character/KZCharacter.h"
#include "KZMonster.generated.h"

/**
 *
 */
UCLASS()
class KHAZAN_API AKZMonster : public AKZCharacter
{
	GENERATED_BODY()

public:
	AKZMonster();

protected:
	virtual void BeginPlay() override;

public:
	virtual void Tick(float DeltaSeconds) override;
};
