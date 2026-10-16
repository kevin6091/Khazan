#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "UI/KZCombatHUDWidget.h"
#include "Player/KZPlayerController.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Character/Component/KZLockOnComponent.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/CapsuleComponent.h"
#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Components/SkeletalMeshComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "KZGameplayTags.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "Editor.h"
#include "Settings/LevelEditorPlaySettings.h"

namespace KZCombatUIQA
{
struct FOriginal
{
	TWeakObjectPtr<AKZCharacter> Actor;
	FTransform Transform;
	float HP = 0, Stamina = 0, MaxHP = 0, MaxStamina = 0;
};
class FRun : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* InTest, AKZPlayer* InPlayer) : Test(InTest), Player(InPlayer), Controller(Cast<AKZPlayerController>(InPlayer->GetController())), Deadline(FPlatformTime::Seconds() + 90.) {}
	~FRun() override { Cleanup(); }
	bool Update() override
	{
		if (!Player.IsValid() || FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Combat UI lost actor or timed out")); return Finish(); }
		AKZPlayer* P = Player.Get(); UWorld* W = P->GetWorld(); const float Now = W->GetTimeSeconds();
		AKZPlayerController* PC = Controller.Get();
		UKZCombatHUDWidget* HUD = PC ? PC->CombatHUD.Get() : nullptr;
		if (!HUD) { Test->AddError(TEXT("Actual player controller did not create the native combat HUD")); return Finish(); }
		if (Phase == 0)
		{
			Test->TestTrue(TEXT("Actual local viewport owns exactly the configured HUD"), HUD->IsInViewport() && PC->IsLocalController() && HUD->GetClass() == PC->CombatHUDClass);
			Test->AddInfo(FString::Printf(TEXT("COMBAT_UI_ACTUAL_HUD_CLASS %s"), *HUD->GetClass()->GetPathName()));
			SavedView = PC->GetViewTarget(); SavedControl = PC->GetControlRotation();
			Save(P); P->HandleInputMoveReleased(); P->GetAbilitySystemComponent()->CancelAllAbilities();
			for (TActorIterator<AKZMonster> It(W); It; ++It)
			{
				Save(*It); if (AAIController* AI = Cast<AAIController>(It->GetController())) if (AI->BrainComponent) AI->BrainComponent->PauseLogic(TEXT("Task-owned UI fixture"));
				It->GetAbilitySystemComponent()->CancelAllAbilities();
				It->GetCharacterMovement()->StopMovementImmediately();
				if (It->bUseBossCombatHUD) Boss = *It;
				else if (!Normal.IsValid() || It->GetClass()->GetName().Contains(TEXT("HalberdElite"))) Normal = *It;
			}
			if (!Test->TestTrue(TEXT("Main DevMap has regular and actual Yetuga boss BP"), Normal.IsValid() && Boss.IsValid())) return Finish();
			Test->TestTrue(TEXT("Damage and chest-reticle visual fixture includes the requested HalberdElite"), Normal->GetClass()->GetName().Contains(TEXT("HalberdElite")));
			Test->TestEqual(TEXT("Yetuga configured boss label"), Boss->CombatDisplayName.ToString(), FString(TEXT("예투가")));
			for (const FOriginal& S : Saved)
				if (auto* M = Cast<AKZMonster>(S.Actor.Get()))
				{
					Test->TestTrue(TEXT("Saved BP targets its actual mesh head bone"), !M->CombatGaugeHeadBone.IsNone() && M->GetMesh()->DoesSocketExist(M->CombatGaugeHeadBone));
					Test->TestTrue(TEXT("Every monster family has an actual chest socket"), M->CombatReticleSocket == TEXT("UI_Chest") && M->GetMesh()->DoesSocketExist(M->CombatReticleSocket));
				}
			const FVector Origin = P->GetActorLocation(); const FVector Forward = P->GetActorForwardVector();
			const FVector Right = P->GetActorRightVector();
			// Keep the visual subjects unobstructed; unrelated saved monsters otherwise overlap their gauges/reticle.
			for (int32 Index = 0; Index < Saved.Num(); ++Index)
				if (AKZCharacter* Other = Saved[Index].Actor.Get(); Other && Other != P && Other != Normal.Get() && Other != Boss.Get())
					Other->SetActorLocation(Origin + Right * (20000.f + Index * 1000.f), false, nullptr, ETeleportType::TeleportPhysics);
			// QA-only layout on existing test floor, not product placement or original-game numbers.
			Normal->SetActorLocation(Origin + Forward * 500.f - Right * 150.f, false, nullptr, ETeleportType::TeleportPhysics);
			Boss->SetActorLocation(Origin + Forward * 900.f + Right * 200.f, false, nullptr, ETeleportType::TeleportPhysics);
			Camera = W->SpawnActor<ACameraActor>(Origin - Forward * 600.f + FVector(0, 0, 450.f), (Origin + Forward * 600.f - (Origin - Forward * 600.f + FVector(0, 0, 450.f))).Rotation());
			PC->SetViewTarget(Camera.Get());
			Start = Now; Phase = 1; return false;
		}
		if (Phase == 1)
		{
			if (Now - Start < .6f) return false;
			CheckRatios(HUD, TEXT("Initial"));
			Test->TestTrue(TEXT("Boss has a top HUD and no overhead duplicate"), HUD->WidgetTree->FindWidget(TEXT("BossGauge"))->GetVisibility() != ESlateVisibility::Collapsed);
			Test->TestTrue(TEXT("Imported normal lock-on UI material is assigned"), CastChecked<UImage>(HUD->WidgetTree->FindWidget(TEXT("LockOn")))->GetBrush().GetResourceObject() != nullptr);
			const FSlateFontInfo BossFont = CastChecked<UTextBlock>(HUD->WidgetTree->FindWidget(TEXT("BossGauge_Name")))->GetFont();
			Test->TestTrue(TEXT("Boss label uses extracted original Medium font"), BossFont.CompositeFont.IsValid() && BossFont.CompositeFont->DefaultTypeface.Fonts.Num() == 1 && BossFont.CompositeFont->DefaultTypeface.Fonts[0].Font.GetFontFaceAsset() && BossFont.TypefaceFontName == FName(TEXT("Medium")));
			Capture(TEXT("01_Player_Monster_Yetuga"));
			for (AKZCharacter* A : { static_cast<AKZCharacter*>(P), static_cast<AKZCharacter*>(Normal.Get()), static_cast<AKZCharacter*>(Boss.Get()) }) SetRatios(A, .4f, .45f);
			Start = Now; Phase = 2; return false;
		}
		if (Phase == 2)
		{
			if (Now - Start < .08f) return false;
			if (!bIntermediateChecked) for (AKZCharacter* A : { static_cast<AKZCharacter*>(P), static_cast<AKZCharacter*>(Normal.Get()), static_cast<AKZCharacter*>(Boss.Get()) })
			{
				Test->TestTrue(TEXT("HP immediately shows actual damage"), FMath::IsNearlyEqual(HUD->GetDisplayedHPRatio(A), .4f));
				Test->TestTrue(TEXT("Stamina immediately shows actual damage"), FMath::IsNearlyEqual(HUD->GetDisplayedStaminaRatio(A), .45f));
			}
			bIntermediateChecked = true;
			if (Now - Start < 1.8f) return false;
			CheckRatios(HUD, TEXT("Damage settled")); Capture(TEXT("02_DamagedGauges"));
			for (AKZCharacter* A : { static_cast<AKZCharacter*>(P), static_cast<AKZCharacter*>(Normal.Get()), static_cast<AKZCharacter*>(Boss.Get()) }) SetRatios(A, .85f, .9f);
			Start = Now; bIntermediateChecked = false; Phase = 3; return false;
		}
		if (Phase == 3)
		{
			if (Now - Start < .08f) return false;
			if (!bIntermediateChecked) for (AKZCharacter* A : { static_cast<AKZCharacter*>(P), static_cast<AKZCharacter*>(Normal.Get()), static_cast<AKZCharacter*>(Boss.Get()) })
			{
				Test->TestTrue(TEXT("HP recovery is immediately visible"), FMath::IsNearlyEqual(HUD->GetDisplayedHPRatio(A), .85f));
				Test->TestTrue(TEXT("Stamina recovery is immediately visible"), FMath::IsNearlyEqual(HUD->GetDisplayedStaminaRatio(A), .9f));
			}
			bIntermediateChecked = true;
			if (Now - Start < 1.8f) return false;
			CheckRatios(HUD, TEXT("Recovery settled"));
			PC->SetViewTarget(P);
			const float Spacing = P->GetCapsuleComponent()->GetScaledCapsuleRadius() + Normal->GetCapsuleComponent()->GetScaledCapsuleRadius() + 15.f;
			P->SetActorLocation(Normal->GetActorLocation() - Normal->GetActorForwardVector() * Spacing + FVector(0, 0, P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Normal->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
			P->SetActorRotation(Normal->GetActorForwardVector().Rotation()); PC->SetControlRotation(P->GetActorRotation());
			P->GetCharacterMovement()->StopMovementImmediately(); P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
			Start = Now; Phase = 4; return false;
		}
		if (Phase == 4)
		{
			if (Now - Start < .6f) return false;
			LockOn = P->FindComponentByClass<UKZLockOnComponent>();
			if (!Test->TestNotNull(TEXT("Existing targeting component"), LockOn.Get())) return Finish();
			LockOn->StopLockOn(); LockOn->ToggleLockOn();
			if (!Test->TestNotNull(TEXT("Actual toggle acquires a monster"), LockOn->GetCurrentTarget())) return Finish();
			Test->TestEqual(TEXT("Actual toggle acquires the unobstructed HalberdElite visual subject"), LockOn->GetCurrentTarget(), Normal.Get());
			Normal = LockOn->GetCurrentTarget();
			Start = Now; Phase = 5; return false;
		}
		if (Phase == 5)
		{
			if (Now - Start < .25f) return false;
			Test->TestEqual(TEXT("HUD follows exact component target"), HUD->GetReticleTarget(), LockOn->GetCurrentTarget());
			Test->TestTrue(TEXT("Actual saved chest socket exists"), Normal->GetMesh()->DoesSocketExist(Normal->CombatReticleSocket));
			Test->TestTrue(TEXT("The unobstructed normal lock-on reticle is visible"), HUD->WidgetTree->FindWidget(TEXT("TargetReticle"))->GetVisibility() != ESlateVisibility::Collapsed);
			FVector2D Position; UWidgetLayoutLibrary::ProjectWorldLocationToWidgetPosition(PC, Normal->GetMesh()->GetSocketLocation(Normal->CombatReticleSocket), Position, true);
			const FVector2D Actual = CastChecked<UCanvasPanelSlot>(HUD->WidgetTree->FindWidget(TEXT("TargetReticle"))->Slot)->GetPosition();
			Test->TestTrue(TEXT("Reticle follows the current posed chest socket with DPI removed"), FVector2D::Distance(Position, Actual) < 2.f);
			Capture(TEXT("03_ActualLockOn"));
			Normal->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), 0.f);
			Start = Now; Phase = 6; return false;
		}
		if (Phase == 6)
		{
			UKZExhaustionAbility* Exhaustion = Normal->GetActiveExhaustionAbility();
			if (!Exhaustion || !Exhaustion->IsAvailableForBrutalAttack()) { if (Now - Start > 4.f) { Test->AddError(TEXT("Real exhaustion never became available")); return Finish(); } return false; }
			if (Now - Start < .3f) return false;
			FGameplayAbilitySpec* Spec = nullptr;
			for (FGameplayAbilitySpec& S : P->GetAbilitySystemComponent()->GetActivatableAbilities()) if (Cast<UKZBrutalAttackAbility>(S.Ability)) { Spec = &S; break; }
			if (!Test->TestNotNull(TEXT("Actual granted Brutal Ability"), Spec)) return Finish();
			Test->TestTrue(TEXT("Granted Brutal is bound to actual B input"), Spec->GetDynamicSpecSourceTags().HasTagExact(KZGameplayTags::Input_Action_B));
			Test->TestEqual(TEXT("Ability selects the same eligible locked target as UI"), CastChecked<UKZBrutalAttackAbility>(Spec->Ability)->FindBrutalTarget(P->GetAbilitySystemComponent()->AbilityActorInfo.Get()), Normal.Get());
			Test->TestTrue(TEXT("Real CanActivate gate switches HUD to B"), HUD->IsBrutalIndicatorShown());
			Capture(TEXT("04_BrutalAvailable_B"));
			// Stay on screen one frame so the captured B state precedes real execution.
			BrutalHandle = Spec->Handle; Start = Now; Phase = 7; return false;
		}
		if (Phase == 7)
		{
			if (Now - Start < .25f) return false;
			Test->TestTrue(TEXT("Existing granted Ability activates with the indicated target"), P->GetAbilitySystemComponent()->TryActivateAbility(BrutalHandle));
			Start = Now; Phase = 8; return false;
		}
		if (Phase == 8)
		{
			if (Now - Start < .2f) return false;
			Test->TestFalse(TEXT("Active paired attack cannot keep offering B"), HUD->IsBrutalIndicatorShown());
			P->GetAbilitySystemComponent()->CancelAbilityHandle(BrutalHandle); LockOn->StopLockOn();
			Start = Now; Phase = 9; return false;
		}
		if (Phase == 9)
		{
			if (Now - Start < .3f) return false;
			Normal->GetAbilitySystemComponent()->CancelAllAbilities(); SetRatios(Normal.Get(), 1.f, 1.f);
			Start = Now; Phase = 10; return false;
		}
		if (Phase == 10)
		{
			if (Now - Start < .3f) return false;
			Test->TestNull(TEXT("Unlock and no available attack clears the marker"), HUD->GetReticleTarget());
			Test->TestFalse(TEXT("Cancelled availability no stale B"), HUD->IsBrutalIndicatorShown());
			// Disposable actual monster lifecycle, never destroy an existing map actor.
			Transient = W->SpawnActor<AKZMonster>(Normal->GetClass(), Normal->GetActorLocation() + FVector(1000, 0, 0), FRotator::ZeroRotator);
			Start = Now; Phase = 11; return false;
		}
		if (Phase == 11)
		{
			if (Now - Start < .5f) return false;
			if (!Test->TestTrue(TEXT("Disposable actor gauge initializes from actual HP"), Transient.IsValid() && HUD->GetDisplayedHPRatio(Transient.Get()) > .9f)) return Finish();
			Transient->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), 0.f);
			Start = Now; Phase = 12; return false;
		}
		if (Phase == 12)
		{
			if (Now - Start < .1f) return false;
			if (!bLethalChecked) { Test->TestEqual(TEXT("Lethal HP immediately reads zero"), HUD->GetDisplayedHPRatio(Transient.Get()), 0.f); bLethalChecked = true; }
			if (Now - Start < 1.8f) return false;
			Transient->Destroy(); Start = Now; Phase = 13; return false;
		}
		if (Phase == 13)
		{
			if (Now - Start < .5f) return false;
			Test->TestTrue(TEXT("HUD survives actor destruction and discovery cleanup"), HUD->IsInViewport());
			P->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), 0.f);
			P->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(), 0.f);
			Start = Now; Phase = 14; return false;
		}
		if (Phase == 14)
		{
			if (Now - Start < 1.8f) return false;
			Test->TestTrue(TEXT("Zero maxima yield finite empty gauges"), FMath::IsFinite(HUD->GetDisplayedHPRatio(P)) && HUD->GetDisplayedHPRatio(P) < .025f && FMath::IsFinite(HUD->GetDisplayedStaminaRatio(P)) && HUD->GetDisplayedStaminaRatio(P) < .025f);
			PC->UnPossess(); Start = Now; Phase = 15; return false;
		}
		if (Phase == 15)
		{
			if (Now - Start < .25f) return false;
			Test->TestEqual(TEXT("No pawn hides player gauge"), HUD->WidgetTree->FindWidget(TEXT("PlayerGauge"))->GetVisibility(), ESlateVisibility::Collapsed);
			Test->TestEqual(TEXT("No pawn hides boss gauge"), HUD->WidgetTree->FindWidget(TEXT("BossGauge"))->GetVisibility(), ESlateVisibility::Collapsed);
			Test->TestNull(TEXT("No pawn clears targeting UI"), HUD->GetReticleTarget());
			PC->Possess(P); Start = Now; Phase = 16; return false;
		}
		if (Phase == 16)
		{
			if (Now - Start < .25f) return false;
			Test->TestTrue(TEXT("Repossess reuses controller-owned HUD without duplication"), PC->CombatHUD == HUD && HUD->WidgetTree->FindWidget(TEXT("PlayerGauge"))->GetVisibility() != ESlateVisibility::Collapsed);
			Test->AddInfo(TEXT("COMBAT_UI_REAL_PIE_CHECKS_COMPLETE")); return Finish();
		}
		return false;
	}
private:
	void Save(AKZCharacter* A) { auto* ASC=A->GetAbilitySystemComponent(); Saved.Add({A, A->GetActorTransform(), ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()), ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute())}); ASC->AddLooseGameplayTag(KZGameplayTags::Block_StaminaRegen); }
	void SetRatios(AKZCharacter* A, float HP, float ST) { auto* ASC=A->GetAbilitySystemComponent(); ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), HP*ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute())); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), ST*ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute())); }
	void CheckRatios(UKZCombatHUDWidget* HUD, const TCHAR* Context)
	{
		for (AKZCharacter* A : { static_cast<AKZCharacter*>(Player.Get()), static_cast<AKZCharacter*>(Normal.Get()), static_cast<AKZCharacter*>(Boss.Get()) })
		{
			auto* ASC=A->GetAbilitySystemComponent();
			Test->TestTrue(FString::Printf(TEXT("%s HP reads actual ASC: %s"), Context,*A->GetName()), FMath::IsNearlyEqual(HUD->GetDisplayedHPRatio(A), ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())/ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()), .025f));
			Test->TestTrue(FString::Printf(TEXT("%s Stamina reads actual ASC: %s"), Context,*A->GetName()), FMath::IsNearlyEqual(HUD->GetDisplayedStaminaRatio(A), ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute())/ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()), .025f));
		}
	}
	void Capture(const TCHAR* Name)
	{
		auto* Viewport=Controller->GetLocalPlayer()->ViewportClient.Get();TArray<FColor> Pixels;FIntVector Size=FIntVector::ZeroValue;
		if(!Viewport||!Viewport->GetWindow().IsValid()||!FSlateApplication::Get().TakeScreenshot(Viewport->GetWindow().ToSharedRef(),Pixels,Size)){Test->AddError(TEXT("Owned game UI window screenshot failed"));return;}
		TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Size.X,Size.Y,Pixels,PNG);FFileHelper::SaveArrayToFile(PNG,*FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_COMBAT_UI_OUTPUT")),FString(Name)+TEXT(".png")));
	}
	void Cleanup()
	{
		if (bCleaned) return; bCleaned=true;
		if (LockOn.IsValid()) LockOn->StopLockOn();
		for (const FOriginal& S : Saved) if (AKZCharacter* A=S.Actor.Get()) { auto* ASC=A->GetAbilitySystemComponent(); ASC->CancelAllAbilities(); ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),S.MaxHP); ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(),S.MaxStamina); ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),S.HP); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),S.Stamina); ASC->RemoveLooseGameplayTag(KZGameplayTags::Block_StaminaRegen); A->SetActorTransform(S.Transform,false,nullptr,ETeleportType::TeleportPhysics); if(auto* AI=Cast<AAIController>(A->GetController())) if(AI->BrainComponent) AI->BrainComponent->ResumeLogic(TEXT("UI fixture complete")); }
		if(Player.IsValid() && Controller.IsValid()) { if(Controller->GetPawn()!=Player.Get())Controller->Possess(Player.Get());Controller->SetViewTarget(SavedView.Get());Controller->SetControlRotation(SavedControl); }
		if(Camera.IsValid())Camera->Destroy();if(Transient.IsValid())Transient->Destroy();
	}
	bool Finish() { Cleanup(); return true; }
	FAutomationTestBase* Test; TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<AKZPlayerController> Controller;
	TWeakObjectPtr<AKZMonster> Normal,Boss,Transient; TWeakObjectPtr<UKZLockOnComponent> LockOn;
	TWeakObjectPtr<ACameraActor> Camera; TWeakObjectPtr<AActor> SavedView; FRotator SavedControl;
	TArray<FOriginal> Saved; FGameplayAbilitySpecHandle BrutalHandle; double Deadline; float Start=0;int32 Phase=0;bool bCleaned=false,bIntermediateChecked=false,bLethalChecked=false;
};
class FWait : public IAutomationLatentCommand
{
public:
	explicit FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
	bool Update() override
	{
		if(!Requested){Requested=true;auto* S=GetMutableDefault<ULevelEditorPlaySettings>();S->NewWindowWidth=1600;S->NewWindowHeight=900;FRequestPlaySessionParams P;P.EditorPlaySettings=S;GEditor->RequestPlaySession(P);}
		for(const FWorldContext& C:GEngine->GetWorldContexts()) if(C.WorldType==EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It) if(It->IsPlayerControlled() && It->GetCharacterMovement()->IsMovingOnGround()) { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true; }
		if(FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Start owned Main DevMap PIE"));return true; }return false;
	}
private:FAutomationTestBase* Test;double Deadline;bool Requested=false;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatUIPIE, "Khazan.CombatUI.PIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZCombatUIPIE::RunTest(const FString& Parameters)
{
	const auto* D=LoadObject<UKZCharacterDefinitionData>(nullptr,TEXT("/Game/Data/Character/DA_CharacterDefinition_Player.DA_CharacterDefinition_Player"));
	if(!TestNotNull(TEXT("Actual saved player definition"),D))return false;
	int32 Blank=0;for(const auto& G:D->GetInitialAbilityGrants())if(!G.AbilityClass && G.InputTag==FGameplayTag::EmptyTag)++Blank;
	if(Blank)AddExpectedError(TEXT("BP_Player_C_0 has an InitialAbilityGrant with no AbilityClass in DA_CharacterDefinition_Player (InputTag: None)."),EAutomationExpectedErrorFlags::Contains,Blank,false);
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZCombatUIQA::FWait>(this));return true;
}
#endif
