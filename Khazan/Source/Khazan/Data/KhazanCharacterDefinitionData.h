#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Engine/DataAsset.h"
#include "KhazanCharacterDefinitionData.generated.h"

UCLASS(BlueprintType)
class KHAZAN_API UKhazanCharacterDefinitionData : public UDataAsset
{
	GENERATED_BODY()

public:
	const FKhazanLocomotionConfig& GetLocomotionConfig() const;

private:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Locomotion",
		meta = (AllowPrivateAccess = "true"))
	FKhazanLocomotionConfig LocomotionConfig;
};