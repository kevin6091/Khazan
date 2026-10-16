#include "Animation/Notifies/KZAnimNotifyState_PlayAudio.h"

#include "Animation/Notifies/KZAnimNotify_PlayAudio.h"
#include "Animation/AnimNotifyLibrary.h"
#include "Animation/AnimNotifyQueue.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void UKZAnimNotifyState_PlayAudio::NotifyBegin(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, float Duration, const FAnimNotifyEventReference& Reference)
{
	if (Playback)
		Playback->Play(Mesh, FName(*FString::Printf(TEXT("KZAudioWindow_%d"), Reference.GetNotifyInstanceID())));
}

void UKZAnimNotifyState_PlayAudio::NotifyEnd(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, const FAnimNotifyEventReference& Reference)
{
	AActor* Owner = IsValid(Mesh) ? Mesh->GetOwner() : nullptr;
	if (!IsValid(Owner) || !Playback) return;
	const FName Occurrence(*FString::Printf(TEXT("KZAudioWindow_%d"), Reference.GetNotifyInstanceID()));
	const bool bNaturalEnd = UAnimNotifyLibrary::NotifyStateReachedEnd(Reference);
	TInlineComponentArray<UAudioComponent*> Components(Owner);
	for (UAudioComponent* Audio : Components)
	{
		if (!IsValid(Audio) || !Audio->ComponentHasTag(TEXT("KZOriginalAudio")) ||
			!Audio->ComponentHasTag(Occurrence) || !Audio->ComponentHasTag(Mesh->GetFName())) continue;
		// A finite strike/voice retains its natural tail. Loops and explicit source
		// stop actions fade on both normal completion and interrupted playback.
		if (bStopAtEnd || (Audio->Sound && Audio->Sound->IsLooping()))
		{
			if (FadeOutSeconds > 0.f) Audio->FadeOut(FadeOutSeconds, 0.f);
			else Audio->Stop();
		}
	}
	if (bNaturalEnd && EndSound && Owner->GetWorld()->IsGameWorld())
		UGameplayStatics::SpawnSoundAttached(EndSound, Mesh, Playback->AttachName,
			FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true);
}
