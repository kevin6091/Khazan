#include "UI/KZCombatHUDWidget.h"

#include "AbilitySystemComponent.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Attribute/KZAttributeSet.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Character/KZCharacter.h"
#include "Character/KZMonster.h"
#include "Character/Component/KZLockOnComponent.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/CapsuleComponent.h"
#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/TextBlock.h"
#include "Engine/Texture2D.h"
#include "Engine/FontFace.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameplayAbilitySpec.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
float ResourceRatio(const UAbilitySystemComponent* ASC, const FGameplayAttribute& Current, const FGameplayAttribute& Maximum)
{
	const float Max = ASC ? ASC->GetNumericAttribute(Maximum) : 0.f;
	const float Value = ASC ? ASC->GetNumericAttribute(Current) : 0.f;
	return FMath::IsFinite(Max) && Max > 0.f && FMath::IsFinite(Value) ? FMath::Clamp(Value / Max, 0.f, 1.f) : 0.f;
}

float SmoothRatio(float Display, float Target, float DeltaTime, float Seconds)
{
	// Exact exponential step: moving regeneration targets cannot restart/freeze an easing animation.
	if (!FMath::IsFinite(Seconds) || Seconds <= 0.f) return Target;
	const float Alpha = 1.f - FMath::Exp(-FMath::Max(DeltaTime, 0.f) / Seconds);
	const float Result = FMath::Lerp(Display, Target, Alpha);
	return FMath::IsNearlyEqual(Result, Target, UE_SMALL_NUMBER) ? Target : FMath::Clamp(Result, 0.f, 1.f);
}

UCanvasPanelSlot* Place(UCanvasPanel* Parent, UWidget* Child, FVector2D Position, FVector2D Size)
{
	UCanvasPanelSlot* Slot = Parent->AddChildToCanvas(Child);
	Slot->SetPosition(Position); Slot->SetSize(Size);
	return Slot;
}
}

UKZCombatHUDWidget::UKZCombatHUDWidget(const FObjectInitializer& Initializer) : Super(Initializer)
{
	// Exact extracted packages, mapped by Scripts/Art/import_combat_ui_20261011.py.
	static ConstructorHelpers::FObjectFinder<UTexture2D> HP(TEXT("/Game/UI/Combat/Textures/T_Hud_Gauge_HP_01")); HPTexture = HP.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> ST(TEXT("/Game/UI/Combat/Textures/T_Hud_Gauge_Stamina_01")); StaminaTexture = ST.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> PBG(TEXT("/Game/UI/Combat/Textures/T_Hud_Hp_Bg04")); PlayerBackground = PBG.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> CBG(TEXT("/Game/UI/Combat/Textures/T_Hud_Hp_Bg03")); GaugeCenterBackground = CBG.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> BBG(TEXT("/Game/UI/Combat/Textures/T_Hud_Hp_Bg05")); BossBackground = BBG.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> OBG(TEXT("/Game/UI/Combat/Textures/T_Hud_Gauge_HP_BG_00")); OverheadBackground = OBG.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> EBG(TEXT("/Game/UI/Combat/Textures/T_Hud_Gauge_HP_BG_Elite")); EliteBackground = EBG.Object;
	static ConstructorHelpers::FObjectFinder<UTexture2D> BT(TEXT("/Game/UI/Combat/Textures/T_Icon_XB_B")); BButtonTexture = BT.Object;
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> LM(TEXT("/Game/UI/Combat/Materials/M_UI_LockOn")); LockOnMaterial = LM.Object;
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> GB(TEXT("/Game/UI/Combat/Materials/M_UI_GaugeBackground")); GaugeBackgroundMaterial = GB.Object;
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> BM(TEXT("/Game/UI/Combat/Materials/M_UI_BrutalRing")); BrutalMaterial = BM.Object;
	static ConstructorHelpers::FObjectFinder<UFontFace> Font(TEXT("/Game/UI/Combat/Fonts/FF_DNFForgedBlade_Medium")); SourceFontFace = Font.Object;
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

UImage* UKZCombatHUDWidget::AddImage(UCanvasPanel* Parent, FName Name, UObject* Resource, FVector2D Position, FVector2D Size, FLinearColor Tint)
{
	UImage* Image = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), Name);
	FSlateBrush Brush; Brush.SetResourceObject(Resource); Brush.ImageSize = Size; Brush.DrawAs = ESlateBrushDrawType::Image;
	Image->SetBrush(Brush); Image->SetColorAndOpacity(Tint); Place(Parent, Image, Position, Size);
	return Image;
}

UProgressBar* UKZCombatHUDWidget::AddBar(UCanvasPanel* Parent, FName Name, UTexture2D* Texture, FVector2D Position, FVector2D Size, FLinearColor Background, FLinearColor Fill)
{
	UProgressBar* Bar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), Name);
	FProgressBarStyle Style;
	// Original CurBar BackgroundImage alpha is zero. Its separate gradient BG owns the empty track.
	Style.BackgroundImage.DrawAs = ESlateBrushDrawType::NoDrawType;
	Style.BackgroundImage.TintColor = FSlateColor(Background);
	Style.FillImage.SetResourceObject(Texture); Style.FillImage.DrawAs = ESlateBrushDrawType::Image;
	Style.FillImage.ImageSize = Texture ? FVector2D(Texture->GetSizeX(), Texture->GetSizeY()) : Size;
	Style.FillImage.TintColor = FSlateColor(FLinearColor::White);
	Bar->SetWidgetStyle(Style); Bar->SetFillColorAndOpacity(Fill);
	Bar->SetBarFillType(EProgressBarFillType::LeftToRight);
	Bar->SetBarFillStyle(EProgressBarFillStyle::Mask); Bar->SetBorderPadding(FVector2D::ZeroVector);
	Place(Parent, Bar, Position, Size); return Bar;
}

FKZCombatGaugeVisual UKZCombatHUDWidget::MakeGauge(FName Name, const FVector2D& HPSize, const FVector2D& STSize, int32 Style)
{
	FKZCombatGaugeVisual Gauge;
	Gauge.Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), Name);
	// WBP_BattleHUD.PlayerGaugePack padding80/6,72/4; W_Boss.BossGaugePack padding132/6,104/4.
	const float HPPadding = Style == 1 ? 80.f : Style == 2 ? 132.f : 2.f;
	const float STPadding = Style == 1 ? 72.f : Style == 2 ? 104.f : 2.f;
	const float Width = HPSize.X + HPPadding * 2.f;
	const float HPTop = Style == 0 ? 2.f : 6.f;
	const float STTop = HPTop * 2.f + HPSize.Y + 2.f + (Style == 0 ? 0.f : 4.f);
	const float Height = STTop + STSize.Y + (Style == 0 ? 2.f : 4.f);
	Place(Canvas, Gauge.Root, FVector2D::ZeroVector, FVector2D(Width, Height));
	const FString Prefix = Name.ToString();
	if (Style != 0)
	{
		const float SideHeight = Style == 1 ? 16.f : 15.f; // serialized BGSide_Size.
		UTexture2D* Texture = Style == 1 ? PlayerBackground : BossBackground;
		// Source Img_Hp_Bg/Img_Hp_Bg_1: center texture, horizontal tiling, alpha .8.
		UImage* Center = AddImage(Gauge.Root, FName(Prefix + TEXT("_FrameCenter")), GaugeCenterBackground,
			FVector2D(108, 0), FVector2D(Width - 216, SideHeight), FLinearColor(1, 1, 1, .8f));
		FSlateBrush CenterBrush = Center->GetBrush(); CenterBrush.ImageSize = FVector2D(80, SideHeight); CenterBrush.Tiling = ESlateBrushTileType::Horizontal; Center->SetBrush(CenterBrush);
		AddImage(Gauge.Root, FName(Prefix + TEXT("_FrameL")), Texture, FVector2D::ZeroVector, FVector2D(108, SideHeight));
		UImage* Right = AddImage(Gauge.Root, FName(Prefix + TEXT("_FrameR")), Texture, FVector2D(Width - 108, 0), FVector2D(108, SideHeight));
		Right->SetRenderScale(FVector2D(-1, 1));
		const float STWidth = STSize.X + STPadding * 2.f;
		const FVector2D STFramePosition((Width - STWidth) * .5f, STTop - 4.f);
		UImage* STCenter = AddImage(Gauge.Root, FName(Prefix + TEXT("_STFrameCenter")), GaugeCenterBackground,
			STFramePosition + FVector2D(108, 0), FVector2D(STWidth - 216, STSize.Y + 8.f), FLinearColor(1, 1, 1, .8f));
		STCenter->SetBrush(CenterBrush); STCenter->SetRenderScale(FVector2D(1, -1));
		UImage* STLeft = AddImage(Gauge.Root, FName(Prefix + TEXT("_STFrameL")), Texture, STFramePosition, FVector2D(108, STSize.Y + 8.f));
		STLeft->SetRenderScale(FVector2D(1, -1));
		UImage* STRight = AddImage(Gauge.Root, FName(Prefix + TEXT("_STFrameR")), Texture, STFramePosition + FVector2D(STWidth - 108, 0), FVector2D(108, STSize.Y + 8.f));
		STRight->SetRenderScale(FVector2D(-1, -1));
	}
	else AddImage(Gauge.Root, FName(Prefix + TEXT("_Frame")), OverheadBackground, FVector2D(0, -6), FVector2D(Width, 18), FLinearColor(1, 1, 1, .6f));
	const FVector2D HPPosition(HPPadding, HPTop);
	const FVector2D STPosition((Width - STSize.X) * .5f, STTop);
	AddImage(Gauge.Root, FName(Prefix + TEXT("_HPTrack")), GaugeBackgroundMaterial, HPPosition, HPSize);
	AddImage(Gauge.Root, FName(Prefix + TEXT("_STTrack")), GaugeBackgroundMaterial, STPosition, STSize);
	// Damage trails are a presentation adapter. Current resources always respond in this frame.
	Gauge.HPDamage = AddBar(Gauge.Root, FName(Prefix + TEXT("_HPDamage")), HPTexture, HPPosition, HPSize,
		FLinearColor::Transparent, FLinearColor(.947307f, .061246f, .072272f, .65098f));
	Gauge.HP = AddBar(Gauge.Root, FName(Prefix + TEXT("_HP")), HPTexture, HPPosition, HPSize, FLinearColor::Transparent, FLinearColor::White);
	// Raw linear values are used as linear colors, not hex bytes reinterpreted as linear.
	const FLinearColor STFill = Style == 2 ? FLinearColor(.364706f, .156863f, .729412f, 1) : FLinearColor::White;
	Gauge.StaminaDamage = AddBar(Gauge.Root, FName(Prefix + TEXT("_StaminaDamage")), StaminaTexture, STPosition, STSize,
		FLinearColor::Transparent, STFill.CopyWithNewOpacity(.35f));
	Gauge.Stamina = AddBar(Gauge.Root, FName(Prefix + TEXT("_Stamina")), StaminaTexture,
		STPosition, STSize, FLinearColor::Transparent, STFill);
	if (Style == 2)
	{
		Gauge.Name = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), FName(Prefix + TEXT("_Name")));
		TSharedRef<FCompositeFont> Composite = MakeShared<FCompositeFont>();
		FTypefaceEntry& Face = Composite->DefaultTypeface.Fonts.AddDefaulted_GetRef();
		Face.Name = TEXT("Medium"); Face.Font = FFontData(SourceFontFace);
		FSlateFontInfo Font(Composite, 16, TEXT("Medium"));
		Font.OutlineSettings.OutlineSize = 1; Font.OutlineSettings.OutlineColor = FLinearColor(0, 0, 0, .35f);
		Gauge.Name->SetFont(Font);
		Gauge.Name->SetColorAndOpacity(FSlateColor(FLinearColor(.887923f, .887923f, .887923f, 1)));
		Gauge.Name->SetShadowOffset(FVector2D(0, 1)); Gauge.Name->SetShadowColorAndOpacity(FLinearColor(0, 0, 0, .65f));
		Gauge.Name->SetJustification(ETextJustify::Center);
		// Source W_Boss name below gauge, horizontal padding124 and original AK_Font Medium face.
		Place(Gauge.Root, Gauge.Name, FVector2D(124, Height), FVector2D(Width - 248, 24));
	}
	Gauge.Root->SetVisibility(ESlateVisibility::Collapsed); return Gauge;
}

void UKZCombatHUDWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("WidgetTree"));
	Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("CombatCanvas"));
	WidgetTree->RootWidget = Canvas;
	PlayerGauge = MakeGauge(TEXT("PlayerGauge"), PlayerHPSize, PlayerStaminaSize, 1);
	UCanvasPanelSlot* PlayerSlot = CastChecked<UCanvasPanelSlot>(PlayerGauge.Root->Slot);
	PlayerSlot->SetAnchors(FAnchors(.5f, 1.f)); PlayerSlot->SetAlignment(FVector2D(.5f, 1)); PlayerSlot->SetPosition(FVector2D(0, -PlayerBottomOffset));
	BossGauge = MakeGauge(TEXT("BossGauge"), BossHPSize, BossStaminaSize, 2);
	UCanvasPanelSlot* BossSlot = CastChecked<UCanvasPanelSlot>(BossGauge.Root->Slot);
	BossSlot->SetAnchors(FAnchors(.5f, 0.f)); BossSlot->SetAlignment(FVector2D(.5f, 0)); BossSlot->SetPosition(FVector2D(0, BossTopOffset));
	Reticle = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("TargetReticle"));
	UCanvasPanelSlot* ReticleSlot = Place(Canvas, Reticle, FVector2D::ZeroVector, LockOnSize);
	ReticleSlot->SetAlignment(FVector2D(.5f, .5f)); ReticleSlot->SetZOrder(1);
	LockOnImage = AddImage(Reticle, TEXT("LockOn"), LockOnMaterial, FVector2D::ZeroVector, LockOnSize);
	const FVector2D BrutalPosition = (LockOnSize - BrutalSize) * .5f;
	BrutalRing = AddImage(Reticle, TEXT("BrutalRing"), BrutalMaterial, BrutalPosition, BrutalSize);
	BrutalButton = AddImage(Reticle, TEXT("BrutalB"), BButtonTexture, BrutalPosition, BrutalSize, FLinearColor(.887923f, .066626f, .066626f, 1));
	BrutalRing->SetRenderOpacity(0); BrutalButton->SetRenderOpacity(0);
	Reticle->SetVisibility(ESlateVisibility::Collapsed);
}

void UKZCombatHUDWidget::UpdateGauge(FKZCombatGaugeVisual& Gauge, float DeltaTime)
{
	const AKZCharacter* Actor = Gauge.Actor.Get();
	const UAbilitySystemComponent* ASC = Actor ? Actor->GetAbilitySystemComponent() : nullptr;
	const float HP = ResourceRatio(ASC, UKZAttributeSet::GetHPAttribute(), UKZAttributeSet::GetMaxHPAttribute());
	const float ST = ResourceRatio(ASC, UKZAttributeSet::GetStaminaAttribute(), UKZAttributeSet::GetMaxStaminaAttribute());
	Gauge.DamageHP = Gauge.bInitialized && HP < Gauge.DamageHP ? SmoothRatio(Gauge.DamageHP, HP, DeltaTime, GaugeSmoothingSeconds) : HP;
	Gauge.DamageStamina = Gauge.bInitialized && ST < Gauge.DamageStamina ? SmoothRatio(Gauge.DamageStamina, ST, DeltaTime, GaugeSmoothingSeconds) : ST;
	Gauge.DisplayHP = HP; Gauge.DisplayStamina = ST;
	Gauge.bInitialized = ASC != nullptr;
	Gauge.HP->SetPercent(Gauge.DisplayHP); Gauge.Stamina->SetPercent(Gauge.DisplayStamina);
	Gauge.HPDamage->SetPercent(Gauge.DamageHP); Gauge.StaminaDamage->SetPercent(Gauge.DamageStamina);
}

void UKZCombatHUDWidget::DiscoverMonsters()
{
	for (int32 Index = MonsterGauges.Num() - 1; Index >= 0; --Index)
		if (!MonsterGauges[Index].Actor.IsValid())
		{
			WidgetTree->RemoveWidget(MonsterGauges[Index].Root); MonsterGauges.RemoveAt(Index);
		}
	for (TActorIterator<AKZMonster> It(GetWorld()); It; ++It)
	{
		AKZMonster* Monster = *It;
		if (Monster->bUseBossCombatHUD || MonsterGauges.ContainsByPredicate([Monster](const FKZCombatGaugeVisual& G) { return G.Actor == Monster; })) continue;
		FKZCombatGaugeVisual Gauge = MakeGauge(MakeUniqueObjectName(WidgetTree, UCanvasPanel::StaticClass(), TEXT("MonsterGauge")), MonsterHPSize, MonsterStaminaSize, 0);
		Gauge.Actor = Monster;
		if (Monster->bUseEliteCombatGauge)
		{
			const FVector2D Size = CastChecked<UCanvasPanelSlot>(Gauge.Root->Slot)->GetSize();
			UImage* Frame = AddImage(Gauge.Root, MakeUniqueObjectName(WidgetTree, UImage::StaticClass(), TEXT("EliteFrame")), EliteBackground,
				FVector2D((Size.X - EliteFrameSize.X) * .5f, -6), EliteFrameSize, FLinearColor(1, 1, 1, .8f));
			CastChecked<UCanvasPanelSlot>(Frame->Slot)->SetZOrder(-1);
		}
		MonsterGauges.Add(MoveTemp(Gauge));
	}
}

bool UKZCombatHUDWidget::ProjectVisible(const AKZMonster* Monster, const FVector& WorldPosition, FVector2D& Position) const
{
	const APlayerController* PC = GetOwningPlayer();
	if (!PC || !UWidgetLayoutLibrary::ProjectWorldLocationToWidgetPosition(const_cast<APlayerController*>(PC), WorldPosition, Position, true)) return false;
	const FVector2D ViewSize = UWidgetLayoutLibrary::GetViewportSize(this) / UWidgetLayoutLibrary::GetViewportScale(this);
	if (Position.X < 0 || Position.Y < 0 || Position.X > ViewSize.X || Position.Y > ViewSize.Y) return false;
	FVector ViewLocation; FRotator ViewRotation; PC->GetPlayerViewPoint(ViewLocation, ViewRotation);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CombatHUDVisibility), false, PC->GetPawn()); Query.AddIgnoredActor(Monster);
	return !GetWorld()->LineTraceTestByChannel(ViewLocation, WorldPosition, ECC_Visibility, Query);
}

void UKZCombatHUDWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
	Super::NativeTick(Geometry, DeltaTime);
	APlayerController* PC = GetOwningPlayer();
	AKZCharacter* Player = PC ? Cast<AKZCharacter>(PC->GetPawn()) : nullptr;
	if (PlayerGauge.Actor != Player) { PlayerGauge.Actor = Player; PlayerGauge.bInitialized = false; }
	UpdateGauge(PlayerGauge, DeltaTime);
	PlayerGauge.Root->SetVisibility(Player ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	DiscoveryRemaining -= DeltaTime;
	if (DiscoveryRemaining <= 0.f) { DiscoverMonsters(); DiscoveryRemaining = FMath::Max(MonsterDiscoverySeconds, 0.f); }
	const UKZLockOnComponent* LockOn = Player ? Player->FindComponentByClass<UKZLockOnComponent>() : nullptr;
	AKZMonster* Locked = LockOn ? LockOn->GetCurrentTarget() : nullptr;
	AKZMonster* Brutal = nullptr;
	if (Player)
		if (UAbilitySystemComponent* ASC = Player->GetAbilitySystemComponent())
			for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
				if (const UKZBrutalAttackAbility* Ability = Cast<UKZBrutalAttackAbility>(Spec.Ability); Ability && !Spec.IsActive() &&
					Spec.Ability->CanActivateAbility(Spec.Handle, ASC->AbilityActorInfo.Get()))
				{ Brutal = Ability->FindBrutalTarget(ASC->AbilityActorInfo.Get()); break; }
	// Available execution remains visible without lock-on, using the Ability's exact selected target.
	AKZMonster* NewTarget = Locked ? Locked : Brutal;
	if (ReticleTarget != NewTarget) { ReticleTarget = NewTarget; BrutalBlend = 0.f; }
	bBrutalAvailable = NewTarget && NewTarget == Brutal;
	const float Step = ReticleTransitionSeconds > 0.f ? DeltaTime / ReticleTransitionSeconds : 1.f;
	BrutalBlend = FMath::Clamp(BrutalBlend + (bBrutalAvailable ? Step : -Step), 0.f, 1.f);
	LockOnImage->SetRenderOpacity(1.f - BrutalBlend); BrutalRing->SetRenderOpacity(BrutalBlend); BrutalButton->SetRenderOpacity(BrutalBlend);
	FVector2D TargetPosition = FVector2D::ZeroVector;
	const bool bTargetVisible = Player && NewTarget && NewTarget->GetMesh()->DoesSocketExist(NewTarget->CombatReticleSocket) &&
		ProjectVisible(NewTarget, NewTarget->GetMesh()->GetSocketLocation(NewTarget->CombatReticleSocket), TargetPosition);
	Reticle->SetVisibility(bTargetVisible ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (bTargetVisible) CastChecked<UCanvasPanelSlot>(Reticle->Slot)->SetPosition(TargetPosition);
	for (FKZCombatGaugeVisual& Gauge : MonsterGauges)
	{
		AKZMonster* Monster = Cast<AKZMonster>(Gauge.Actor.Get());
		UpdateGauge(Gauge, DeltaTime);
		FVector2D Position = FVector2D::ZeroVector;
		FVector Head = Monster ? Monster->GetActorLocation() + FVector(0, 0, Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()) : FVector::ZeroVector;
		if (Monster && !Monster->CombatGaugeHeadBone.IsNone() && Monster->GetMesh()->DoesSocketExist(Monster->CombatGaugeHeadBone))
			Head = Monster->GetMesh()->GetSocketLocation(Monster->CombatGaugeHeadBone);
		Head.Z += HeadPadding;
		const bool bVisible = Player && Monster && Monster->GetAbilitySystemComponent() &&
			(Monster->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) > 0.f ||
			 !FMath::IsNearlyZero(Gauge.DisplayHP, UE_KINDA_SMALL_NUMBER)) && ProjectVisible(Monster, Head, Position);
		Gauge.Root->SetVisibility(bVisible ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		if (bVisible) { UCanvasPanelSlot* GaugeSlot = CastChecked<UCanvasPanelSlot>(Gauge.Root->Slot); GaugeSlot->SetAlignment(FVector2D(.5f, 1)); GaugeSlot->SetPosition(Position); }
	}
	AKZMonster* Boss = nullptr;
	if (Player)
	{
		Boss = Locked && Locked->bUseBossCombatHUD ? Locked : Cast<AKZMonster>(BossGauge.Actor.Get());
		// Let lethal damage finish its displayed decrease before retiring the boss HUD.
		if (Boss && (!Boss->GetAbilitySystemComponent() || (Boss->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f &&
			FMath::IsNearlyZero(BossGauge.DisplayHP, UE_KINDA_SMALL_NUMBER)))) Boss = nullptr;
		if (!Boss)
		{
			double BestDistance = TNumericLimits<double>::Max();
			for (TActorIterator<AKZMonster> It(GetWorld()); It; ++It)
			{
				FVector2D Position; AKZMonster* Candidate = *It;
				if (!Candidate->bUseBossCombatHUD || !Candidate->GetAbilitySystemComponent() ||
					Candidate->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f ||
					!ProjectVisible(Candidate, Candidate->GetLockOnTargetPoint()->GetComponentLocation(), Position)) continue;
				const double Distance = FVector::DistSquared(Player->GetActorLocation(), Candidate->GetActorLocation());
				if (Distance < BestDistance) { BestDistance = Distance; Boss = Candidate; }
			}
		}
	}
	if (BossGauge.Actor != Boss) { BossGauge.Actor = Boss; BossGauge.bInitialized = false; }
	UpdateGauge(BossGauge, DeltaTime);
	BossGauge.Root->SetVisibility(Boss ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (Boss) BossGauge.Name->SetText(Boss->CombatDisplayName);
}

const FKZCombatGaugeVisual* UKZCombatHUDWidget::FindGauge(const AKZCharacter* Character) const
{
	if (!Character) return nullptr;
	if (PlayerGauge.Actor == Character) return &PlayerGauge;
	if (BossGauge.Actor == Character) return &BossGauge;
	return MonsterGauges.FindByPredicate([Character](const FKZCombatGaugeVisual& G) { return G.Actor == Character; });
}

float UKZCombatHUDWidget::GetDisplayedHPRatio(const AKZCharacter* Character) const
{
	const FKZCombatGaugeVisual* Gauge = FindGauge(Character); return Gauge ? Gauge->DisplayHP : 0.f;
}
float UKZCombatHUDWidget::GetDisplayedStaminaRatio(const AKZCharacter* Character) const
{
	const FKZCombatGaugeVisual* Gauge = FindGauge(Character); return Gauge ? Gauge->DisplayStamina : 0.f;
}
void UKZCombatHUDWidget::NativeDestruct()
{
	ReticleTarget.Reset(); MonsterGauges.Reset(); PlayerGauge.Actor.Reset(); BossGauge.Actor.Reset();
	bBrutalAvailable = false; DiscoveryRemaining = 0.f;
	Super::NativeDestruct();
}
