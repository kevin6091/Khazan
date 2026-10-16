#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "KZCombatHUDWidget.generated.h"

class AKZCharacter;
class AKZMonster;
class UCanvasPanel;
class UProgressBar;
class UImage;
class UTextBlock;

/** UI-owned observation, never an alternate gameplay resource or state. */
USTRUCT()
struct FKZCombatGaugeVisual
{
	GENERATED_BODY()
	UPROPERTY(Transient) TWeakObjectPtr<AKZCharacter> Actor;
	UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Root;
	UPROPERTY(Transient) TObjectPtr<UProgressBar> HP;
	UPROPERTY(Transient) TObjectPtr<UProgressBar> Stamina;
	UPROPERTY(Transient) TObjectPtr<UProgressBar> HPDamage;
	UPROPERTY(Transient) TObjectPtr<UProgressBar> StaminaDamage;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> Name;
	float DisplayHP = 0.f, DisplayStamina = 0.f;
	float DamageHP = 0.f, DamageStamina = 0.f;
	bool bInitialized = false;
};

/** One local presentation owner for player, overhead monsters, boss and target marker. */
UCLASS(Blueprintable)
class KHAZAN_API UKZCombatHUDWidget : public UUserWidget
{
	GENERATED_BODY()
public:
	UKZCombatHUDWidget(const FObjectInitializer& Initializer);
	// Damage trail only; current HP/ST are immediate. Original raw multiplier .35 has no recovered native formula.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Combat UI|Smoothing", meta = (ClampMin = "0", Units = "s"))
	float GaugeSmoothingSeconds = .35f;
	// Source CommonUI xxAnimatedSwitcher_Groggy.TransitionDuration=.15 seconds.
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|LockOn", meta = (ClampMin = "0", Units = "s"))
	float ReticleTransitionSeconds = .15f;
	// Temporary world-space padding above the authored head bone, in cm. No original native offset recovered.
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Overhead", meta = (Units = "cm"))
	float HeadPadding = 8.f;
	// Presentation discovery cadence only; resources and projected positions still update every frame.
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Overhead", meta = (ClampMin = "0", Units = "s"))
	float MonsterDiscoverySeconds = .25f;

	// Direct source widget sizes and canvas offsets; Slate logical pixels, DPI handled by UMG.
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Player") FVector2D PlayerHPSize = FVector2D(360, 8);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Player") FVector2D PlayerStaminaSize = FVector2D(240, 6);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Player") float PlayerBottomOffset = 100.f;
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Monster") FVector2D MonsterHPSize = FVector2D(100, 6);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Monster") FVector2D MonsterStaminaSize = FVector2D(100, 4);
	// Temporary user-requested compact frame; original W_OverheadGauge uses 180x32.
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Monster") FVector2D EliteFrameSize = FVector2D(124, 22);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Boss") FVector2D BossHPSize = FVector2D(720, 10);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Boss") FVector2D BossStaminaSize = FVector2D(720, 6);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|Boss") float BossTopOffset = 52.f;
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|LockOn") FVector2D LockOnSize = FVector2D(60, 60);
	UPROPERTY(EditDefaultsOnly, Category = "Combat UI|LockOn") FVector2D BrutalSize = FVector2D(38, 38);

	UFUNCTION(BlueprintPure, Category = "Combat UI") float GetDisplayedHPRatio(const AKZCharacter* Character) const;
	UFUNCTION(BlueprintPure, Category = "Combat UI") float GetDisplayedStaminaRatio(const AKZCharacter* Character) const;
	UFUNCTION(BlueprintPure, Category = "Combat UI") AKZMonster* GetReticleTarget() const { return ReticleTarget.Get(); }
	UFUNCTION(BlueprintPure, Category = "Combat UI") bool IsBrutalIndicatorShown() const { return bBrutalAvailable; }

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
	virtual void NativeDestruct() override;
private:
	FKZCombatGaugeVisual MakeGauge(FName Name, const FVector2D& HPSize, const FVector2D& StaminaSize, int32 Style);
	UImage* AddImage(UCanvasPanel* Parent, FName Name, UObject* Resource, FVector2D Position, FVector2D Size, FLinearColor Tint = FLinearColor::White);
	UProgressBar* AddBar(UCanvasPanel* Parent, FName Name, class UTexture2D* Texture, FVector2D Position, FVector2D Size, FLinearColor Background, FLinearColor Fill);
	void UpdateGauge(FKZCombatGaugeVisual& Gauge, float DeltaTime);
	void DiscoverMonsters();
	bool ProjectVisible(const AKZMonster* Monster, const FVector& WorldPosition, FVector2D& Position) const;
	const FKZCombatGaugeVisual* FindGauge(const AKZCharacter* Character) const;
	UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Canvas;
	UPROPERTY(Transient) FKZCombatGaugeVisual PlayerGauge;
	UPROPERTY(Transient) FKZCombatGaugeVisual BossGauge;
	UPROPERTY(Transient) TArray<FKZCombatGaugeVisual> MonsterGauges;
	UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Reticle;
	UPROPERTY(Transient) TObjectPtr<UImage> LockOnImage;
	UPROPERTY(Transient) TObjectPtr<UImage> BrutalRing;
	UPROPERTY(Transient) TObjectPtr<UImage> BrutalButton;
	UPROPERTY(Transient) TWeakObjectPtr<AKZMonster> ReticleTarget;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> HPTexture;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> StaminaTexture;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> PlayerBackground;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> GaugeCenterBackground;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> BossBackground;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> OverheadBackground;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> EliteBackground;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> BButtonTexture;
	UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> LockOnMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInterface> GaugeBackgroundMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInterface> BrutalMaterial;
	UPROPERTY(Transient) TObjectPtr<class UFontFace> SourceFontFace;
	float DiscoveryRemaining = 0.f, BrutalBlend = 0.f;
	bool bBrutalAvailable = false;
};
