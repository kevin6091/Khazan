#include "Animation/Notifies/KZAnimNotify_PlayAudio.h"

#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Character/Component/KZLockOnComponent.h"
#include "Character/KZMonster.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void UKZAnimNotify_PlayAudio::Notify(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
	const FAnimNotifyEventReference& Reference)
{
	Play(Mesh);
}

UAudioComponent* UKZAnimNotify_PlayAudio::Play(USkeletalMeshComponent* Mesh, const FName Occurrence) const
{
	check(IsInGameThread());
	UWorld* World = IsValid(Mesh) ? Mesh->GetWorld() : nullptr;
	AActor* Owner = IsValid(Mesh) ? Mesh->GetOwner() : nullptr;
	if (!IsValid(Owner) || !IsValid(World) || !World->IsGameWorld() ||
		World->GetNetMode() == NM_DedicatedServer) return nullptr;
	if (bOnlyForLocalOrLockedTarget)
	{
		const APawn* LocalPawn = UGameplayStatics::GetPlayerPawn(World, 0);
		const UKZLockOnComponent* Lock = LocalPawn ? LocalPawn->FindComponentByClass<UKZLockOnComponent>() : nullptr;
		if (Owner != LocalPawn && (!Lock || Lock->GetCurrentTarget() != Owner)) return nullptr;
	}
	if (!StopSounds.IsEmpty())
	{
		TInlineComponentArray<UAudioComponent*> Components(Owner);
		for (UAudioComponent* Component : Components)
			if (IsValid(Component) && Component->ComponentHasTag(TEXT("KZOriginalAudio")) &&
				Component->ComponentHasTag(Mesh->GetFName()) && StopSounds.Contains(Component->Sound))
			{
				if (StopFadeSeconds > 0.f) Component->FadeOut(StopFadeSeconds, 0.f);
				else Component->Stop();
			}
	}
	if (!IsValid(Sound)) return nullptr;
	// Imported skeletons retain source bone names. An unavailable optional source
	// anchor uses the actual mesh origin; it never suppresses the entire action sound.
	const FName Socket = Mesh->DoesSocketExist(AttachName) ? AttachName : NAME_None;
	const FVector Location = Mesh->GetSocketLocation(Socket);
	UAudioComponent* Audio = NewObject<UAudioComponent>(Owner);
	Audio->bAutoActivate = false;
	Audio->bAutoDestroy = true;
	Audio->bStopWhenOwnerDestroyed = true;
	Audio->SetSound(Sound);
	Audio->SetWorldLocation(Location);
	if (bFollow) Audio->SetupAttachment(Mesh, Socket);
	Audio->ComponentTags.Add(TEXT("KZOriginalAudio"));
	if (!Occurrence.IsNone()) Audio->ComponentTags.Add(Occurrence);
	Audio->ComponentTags.Add(Mesh->GetFName());
	Audio->RegisterComponentWithWorld(World);
	Audio->SetWorldLocation(Location);
	if (bGroundMaterialSwitch)
	{
		EPhysicalSurface Surface = SurfaceType_Default;
		const ACharacter* Character = Cast<ACharacter>(Owner);
		const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
		if (Movement && Movement->IsMovingOnGround())
		{
			const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
			FVector Start = Location;
			Start.Z = Character->GetActorLocation().Z;
			const FVector End = Start - FVector::UpVector *
				(Capsule->GetScaledCapsuleHalfHeight() + Movement->MaxStepHeight);
			FCollisionQueryParams Query(SCENE_QUERY_STAT(KZAudioSurface), false, Owner);
			Query.bReturnPhysicalMaterial = true;
			FHitResult Hit;
			if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Query))
			{
				if (Hit.PhysMaterial.IsValid()) Surface = Hit.PhysMaterial->SurfaceType;
				// Current aggregate snow geometry already carries this tag. This is
				// the same project deep-snow adapter as the existing visual presenter.
				if (Hit.GetComponent() && Hit.GetComponent()->ComponentHasTag(TEXT("HeinMachSnowSurface")))
					Surface = SurfaceType13;
			}
		}
		Audio->SetIntParameter(TEXT("KZPhysicalSurface"), int32(Surface));
		// Source CAkLayerCntr297639475 has duplicate keys at230. The author
		// supplies that threshold, rather than scattering a tuning literal here.
		Audio->SetIntParameter(TEXT("KZFootstepBand"),
			FootstepSpeedThreshold > 0.f && Owner->GetVelocity().Size2D() >= FootstepSpeedThreshold ? 1 : 0);
	}
	Audio->Play(); // Parameters/ownership are installed before the first mixer command.
	UE_LOG(LogTemp, Verbose, TEXT("KZAudio Play Owner=%s Sound=%s Source=%s"),
		*Owner->GetName(), *Sound->GetPathName(), *SourcePackage);
	return Audio;
}
