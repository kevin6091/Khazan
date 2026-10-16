#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "KZAnimNotifyState_PlayAudio.generated.h"

class UKZAnimNotify_PlayAudio;
class USoundBase;

UCLASS(EditInlineNew, meta = (DisplayName = "KZ Original Audio Window"))
class KHAZAN_API UKZAnimNotifyState_PlayAudio : public UAnimNotifyState
{

	GENERATED_BODY()
public:
	virtual void NotifyBegin(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
		float Duration, const FAnimNotifyEventReference& Reference) override;
	virtual void NotifyEnd(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
		const FAnimNotifyEventReference& Reference) override;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Instanced, Category = "Audio")
	TObjectPtr<UKZAnimNotify_PlayAudio> Playback;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	TObjectPtr<USoundBase> EndSound;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio")
	bool bStopAtEnd = false;
	// Source stop-action milliseconds converted to seconds when recovered.
	// Missing source/cancel fade is labeled provisional by the authoring report.
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (Units = "s", ClampMin = "0"))
	float FadeOutSeconds = 0.f;
};
