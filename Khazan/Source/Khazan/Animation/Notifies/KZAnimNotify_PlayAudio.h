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
	// Presentation-only trim on top of the original bank gain. Defaults preserve
	// existing recipes; the scoped humanoid authoring report owns TEMP mix values.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio|Mix", meta = (ClampMin = "0"))
	float VolumeMultiplier = 1.f;
	// A finite one-shot can finish after its corpse is destroyed. Loops still stop
	// with their owner and explicit source stop/window rules remain authoritative.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio|Mix")
	bool bPreserveFiniteTailOnOwnerDestroyed = false;
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
