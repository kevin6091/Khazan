#include "KZBossPortal.h"

#include "AbilitySystemComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/KZPlayer.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "KZGameplayTags.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "Sound/SoundBase.h"

AKZBossPortal::AKZBossPortal()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;
	EntryVolume = CreateDefaultSubobject<UBoxComponent>(TEXT("EntryVolume"));
	SetRootComponent(EntryVolume);
	// An unconfigured portal cannot capture a player. The level authors its actual entry bounds.
	EntryVolume->InitBoxExtent(FVector::ZeroVector);
	EntryVolume->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	EntryVolume->SetCollisionResponseToAllChannels(ECR_Ignore);
	EntryVolume->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	EntryVolume->SetGenerateOverlapEvents(true);
	EntryVolume->OnComponentBeginOverlap.AddDynamic(this, &ThisClass::OnEntry);
	PortalEffect = CreateDefaultSubobject<UNiagaraComponent>(TEXT("PortalEffect"));
	PortalEffect->SetupAttachment(EntryVolume);
	PortalEffect->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	ArenaMusic = TSoftObjectPtr<USoundBase>(FSoftObjectPath(
		TEXT("/Game/Audio/Original/Music/Yetuga/SC_YetugaBattle.SC_YetugaBattle")));
}

void AKZBossPortal::OnEntry(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent* OtherComponent,
	int32, bool, const FHitResult&)
{
	AKZPlayer* Player = Cast<AKZPlayer>(OtherActor);
	APlayerController* Controller = Player ? Cast<APlayerController>(Player->GetController()) : nullptr;
	UAbilitySystemComponent* ASC = Player ? Player->GetAbilitySystemComponent() : nullptr;
	if (Phase != ETravelPhase::Idle || !IsValid(ExitPoint) || !Player ||
		OtherComponent != Player->GetCapsuleComponent() || !Controller || !Controller->IsLocalController() ||
		!Controller->PlayerCameraManager || !ASC || ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead)) return;

	Traveller = Player;
	TravelController = Controller;
	TravelASC = ASC;
	Phase = ETravelPhase::FadingOut;
	PhaseElapsed = 0.f;
	// Engine counted locks preserve every other source's contribution on release.
	Controller->SetIgnoreMoveInput(true);
	Controller->SetIgnoreLookInput(true);
	ASC->BlockAbilitiesWithTags(FGameplayTagContainer(KZGameplayTags::Ability_Action));
	ASC->AddLooseGameplayTag(KZGameplayTags::State_Invulnerable);
	ASC->CancelAllAbilities();
	Player->StopLockOn();
	Player->HandleInputMoveReleased();
	Player->HandleInputSprintCanceled();
	Player->GetCharacterMovement()->StopMovementImmediately();
	Controller->PlayerCameraManager->StartCameraFade(0.f, 1.f, FMath::Max(0.f, FadeOutSeconds), FLinearColor::Black, true, true);
	SetActorTickEnabled(true);
}

void AKZBossPortal::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	AKZPlayer* Player = Traveller.Get();
	APlayerController* Controller = TravelController.Get();
	if (Phase == ETravelPhase::Idle) return;
	if (!Player || !Controller || Controller->GetPawn() != Player || !Controller->PlayerCameraManager ||
		!TravelASC.IsValid() || TravelASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead))
	{
		FinishTravel();
		return;
	}
	PhaseElapsed += DeltaSeconds;
	APlayerCameraManager* Camera = Controller->PlayerCameraManager;
	if (Phase == ETravelPhase::FadingOut && PhaseElapsed >= FMath::Max(0.f, FadeOutSeconds))
	{
		// Enforce opaque black before any location, rotation, or camera history changes.
		Camera->SetManualCameraFade(1.f, FLinearColor::Black, true);
		FVector Location = IsValid(ExitPoint) ? ExitPoint->GetActorLocation() : Player->GetActorLocation();
		Location.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + UCharacterMovementComponent::MIN_FLOOR_DIST;
		const FRotator Rotation(0.f, IsValid(ExitPoint) ? ExitPoint->GetActorRotation().Yaw : Player->GetActorRotation().Yaw, 0.f);
		const bool bMoved = IsValid(ExitPoint) && Player->TeleportTo(Location, Rotation);
		if (bMoved)
		{
			// Start once after actual arrival. Death, victory and leaving the arena do not stop it.
			if (!IsValid(ArenaMusicComponent) || !ArenaMusicComponent->IsPlaying())
			{
				if (USoundBase* Music = ArenaMusic.LoadSynchronous())
					ArenaMusicComponent = UGameplayStatics::SpawnSound2D(GetWorld(), Music);
				else if (!ArenaMusic.IsNull())
					UE_LOG(LogTemp, Warning, TEXT("KZ_PORTAL music missing: %s"), *ArenaMusic.ToString());
			}
			Player->GetCharacterMovement()->StopMovementImmediately();
			Controller->SetControlRotation(Rotation);
			Camera->SetGameCameraCutThisFrame();
			// Reset only the camera lag history under black, then retain the authored lag settings.
			if (USpringArmComponent* Arm = Player->FindComponentByClass<USpringArmComponent>())
			{
				const bool bLocationLag = Arm->bEnableCameraLag;
				const bool bRotationLag = Arm->bEnableCameraRotationLag;
				Arm->bEnableCameraLag = false;
				Arm->bEnableCameraRotationLag = false;
				Arm->TickComponent(0.f, LEVELTICK_All, nullptr);
				Arm->bEnableCameraLag = bLocationLag;
				Arm->bEnableCameraRotationLag = bRotationLag;
			}
		}
		UE_LOG(LogTemp, Log, TEXT("KZ_PORTAL %s -> %s moved=%d black=%.3f location=%s"),
			*GetName(), *GetNameSafe(ExitPoint), bMoved, Camera->FadeAmount, *Player->GetActorLocation().ToString());
		Phase = ETravelPhase::Black;
		PhaseElapsed = 0.f;
	}
	else if (Phase == ETravelPhase::Black && PhaseElapsed >= FMath::Max(0.f, BlackHoldSeconds))
	{
		Camera->StartCameraFade(1.f, 0.f, FMath::Max(0.f, FadeInSeconds), FLinearColor::Black, true, false);
		Phase = ETravelPhase::FadingIn;
		PhaseElapsed = 0.f;
	}
	else if (Phase == ETravelPhase::FadingIn && PhaseElapsed >= FMath::Max(0.f, FadeInSeconds)) FinishTravel();
}

void AKZBossPortal::FinishTravel()
{
	if (Phase == ETravelPhase::Idle) return;
	Phase = ETravelPhase::Idle;
	SetActorTickEnabled(false);
	if (UAbilitySystemComponent* ASC = TravelASC.Get())
	{
		ASC->UnBlockAbilitiesWithTags(FGameplayTagContainer(KZGameplayTags::Ability_Action));
		ASC->RemoveLooseGameplayTag(KZGameplayTags::State_Invulnerable);
	}
	if (APlayerController* Controller = TravelController.Get())
	{
		Controller->SetIgnoreMoveInput(false);
		Controller->SetIgnoreLookInput(false);
		if (Controller->PlayerCameraManager) Controller->PlayerCameraManager->StopCameraFade();
	}
	Traveller.Reset();
	TravelController.Reset();
	TravelASC.Reset();
}

void AKZBossPortal::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	FinishTravel();
	Super::EndPlay(EndPlayReason);
}
