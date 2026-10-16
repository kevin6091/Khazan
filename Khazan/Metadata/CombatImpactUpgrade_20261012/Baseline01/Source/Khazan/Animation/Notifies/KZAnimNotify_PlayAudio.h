#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "KZAnimNotify_PlayAudio.generated.h"

class UAudioComponent;
class USoundBase;

// Authored data only. Each actual actor owns its engine audio components.
UCLASS(EditInlineNew, meta = (DisplayName = "KZ Original Audio"))
class KHAZAN_API UKZAnimNotify_PlayAudio : public UAnimNotify
{

	GENERATED_BODY()
public:
	virtual void Notify(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
		const FAnimNotifyEventReference& Reference) override;
	UAudioComponent* Play(USkeletalMeshComponent* Mesh, FName Occurrence = NAME_None) const;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	TObjectPtr<USoundBase> Sound;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	FName AttachName = NAME_None;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	bool bFollow = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	bool bGroundMaterialSwitch = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio|Source")
	float FootstepSpeedThreshold = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	bool bOnlyForLocalOrLockedTarget = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	TArray<TObjectPtr<USoundBase>> StopSounds;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (Units = "s"))
	float StopFadeSeconds = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio|Source")
	FString SourcePackage;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio|Source")
	FString SourceField;
};
