#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KZBossPortal.generated.h"

class AKZPlayer;
class APlayerController;
class UAbilitySystemComponent;
class UAudioComponent;
class UBoxComponent;
class UNiagaraComponent;
class USoundBase;

// The placed portal owns this local, same-world transition and its finite locks.
UCLASS()
class KHAZAN_API AKZBossPortal : public AActor
{
	GENERATED_BODY()

public:
	AKZBossPortal();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Portal")
	TObjectPtr<UBoxComponent> EntryVolume;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Portal")
	TObjectPtr<UNiagaraComponent> PortalEffect;

	// The destination actor marks the capsule's feet; move/rotate it in the level.
	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Portal")
	TObjectPtr<AActor> ExitPoint;

	// Original Yetuga first segment -> continuous source loop. No encounter stop rules.
	UPROPERTY(EditAnywhere, Category="Portal|Music")
	TSoftObjectPtr<USoundBase> ArenaMusic;

	// Assistant TEMP seconds, not original-game metadata. Kept editable on the placed portal.
	UPROPERTY(EditAnywhere, Category="Portal|Fade", meta=(ClampMin="0.0", Units="s"))
	float FadeOutSeconds = 0.45f;

	UPROPERTY(EditAnywhere, Category="Portal|Fade", meta=(ClampMin="0.0", Units="s"))
	float BlackHoldSeconds = 0.15f;

	UPROPERTY(EditAnywhere, Category="Portal|Fade", meta=(ClampMin="0.0", Units="s"))
	float FadeInSeconds = 0.6f;

protected:
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void OnEntry(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComponent, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	void FinishTravel();

	enum class ETravelPhase : uint8 { Idle, FadingOut, Black, FadingIn };
	ETravelPhase Phase = ETravelPhase::Idle;
	float PhaseElapsed = 0.f;
	TWeakObjectPtr<AKZPlayer> Traveller;
	TWeakObjectPtr<APlayerController> TravelController;
	TWeakObjectPtr<UAbilitySystemComponent> TravelASC;
	// Engine-owned 2D playback outlives the traveller; retained only to avoid duplicates.
	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> ArenaMusicComponent;
};
