

#pragma once

#include "CoreMinimal.h"
#include "Character/KhazanCharacter.h"
#include "KhazanMonster.generated.h"

/**
 * 
 */
UCLASS()
class KHAZAN_API AKhazanMonster : public AKhazanCharacter
{
	GENERATED_BODY()

public:
	AKhazanMonster();
	
protected:
	virtual void BeginPlay() override;
	
public:
	virtual void Tick(float DeltaSeconds) override;
};
