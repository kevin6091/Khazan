// Owned PIE only. Fixture positions/waits are QA inputs, not gameplay tuning.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Environment/KZBossPortal.h"
#include "AbilitySystemComponent.h"
#include "Character/KZPlayer.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "KZGameplayTags.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"

namespace KZPortalQA
{
class FRun : public IAutomationLatentCommand
{
public:
	explicit FRun(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds()+120.) {}
	virtual ~FRun() { Cleanup(); }
	bool Update() override
	{
		if (FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Portal PIE watchdog")); Cleanup(); return true; }
		if (!Player.IsValid())
		{
			UWorld* World=nullptr;
			for (const FWorldContext& Context:GEngine->GetWorldContexts()) if(Context.WorldType==EWorldType::PIE) World=Context.World();
			if(!World) return false;
			for(TActorIterator<AKZPlayer> It(World);It;++It) if(It->IsPlayerControlled()) Player=*It;
			if(!Player.IsValid()) return false;
			for(TActorIterator<AKZBossPortal> It(World);It;++It) if(It->ExitPoint) Portal=*It;
			if(!Portal.IsValid()) {Test->AddError(TEXT("Saved HeinMach portal and destination missing"));return true;}
			Controller=Cast<APlayerController>(Player->GetController()); ASC=Player->GetAbilitySystemComponent();
			Saved=Player->GetActorTransform(); SavedControl=Controller->GetControlRotation();
			BaseInvulnerable=ASC->GetTagCount(KZGameplayTags::State_Invulnerable);
			Test->TestFalse(TEXT("Fixture begins without action block"),ASC->AreAbilityTagsBlocked(ActionTags()));
			Test->TestTrue(TEXT("Saved portal has Niagara"),Portal->PortalEffect->GetAsset()!=nullptr);
			Test->TestEqual(TEXT("Entry overlaps pawn"),Portal->EntryVolume->GetCollisionResponseToChannel(ECC_Pawn),ECR_Overlap);
			Test->TestEqual(TEXT("Entry cannot block static world"),Portal->EntryVolume->GetCollisionResponseToChannel(ECC_WorldStatic),ECR_Ignore);
			for(TActorIterator<AActor> It(World);It;++It) if(It->GetActorLabel()==TEXT("GateCube"))
			{
				Test->TestTrue(TEXT("GateCube locator hidden in game"),It->IsHidden());
				Test->TestFalse(TEXT("GateCube does not block entry"),It->GetActorEnableCollision());
			}
			const FRotator TowardPortal=(-Portal->GetActorForwardVector()).Rotation();
			Player->SetActorRotation(TowardPortal);Controller->SetControlRotation(TowardPortal);
			Move(EntryFeet()+Portal->GetActorForwardVector()*400.f);
			Next=World->GetTimeSeconds()+1.; Stage=1;
			return false;
		}
		const float Now=Player->GetWorld()->GetTimeSeconds();
		if(Now<Next) return false;
		if(Stage==1)
		{
			Shot(TEXT("Entry"));Start=Now;Source=Player->GetActorLocation();Stage=8;
		}
		if(Stage==8)
		{
			// Exercise the real Player intent -> CMC collision path into the saved portal.
			if(!Controller->PlayerCameraManager->bEnableFading)
			{
				Player->HandleInputMove(FVector2D(1,0),Controller->GetControlRotation());
				if(Now-Start>8.f){Test->AddError(TEXT("Player could not walk into the portal through the actual cave collision"));Cleanup();return true;}
				return false;
			}
			Test->AddInfo(TEXT("Actual Player locomotion walked into the saved entrance volume"));
			Test->TestTrue(TEXT("Actual capsule overlap starts fade"),Controller->PlayerCameraManager->bEnableFading);
			Test->TestTrue(TEXT("Transition blocks movement"),Controller->IsMoveInputIgnored());
			Test->TestTrue(TEXT("Transition blocks action activation"),ASC->AreAbilityTagsBlocked(ActionTags()));
			Test->TestEqual(TEXT("Transition adds exactly one invulnerability contribution"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),BaseInvulnerable+1);
			// A second real overlap cannot acquire the locks twice.
			if(FVector::Dist2D(Source,Player->GetActorLocation())<5000.f)
			{
				Move(EntryFeet()+Portal->GetActorForwardVector()*400.f);Move(EntryFeet());
			}
			Test->TestEqual(TEXT("Repeated overlap is ignored during transition"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),BaseInvulnerable+1);
			Stage=2;Start=Now;
		}
		else if(Stage==2)
		{
			APlayerCameraManager* Camera=Controller->PlayerCameraManager;
			Samples+=FString::Printf(TEXT("%.6f,%.6f,%.6f,%.6f,%.6f,%d,%d,%d\n"),Now-Start,
				Player->GetActorLocation().X,Player->GetActorLocation().Y,Player->GetActorLocation().Z,
				Camera->FadeAmount,Camera->bEnableFading,Controller->IsMoveInputIgnored(),ASC->GetTagCount(KZGameplayTags::State_Invulnerable));
			if(!HalfShot && Camera->FadeAmount>.35f && Camera->FadeAmount<.9f) { HalfShot=true; Shot(TEXT("FadeOut")); }
			if(!Moved && FVector::Dist2D(Source,Player->GetActorLocation())>5000.f)
			{
				Moved=true;
				Test->TestTrue(TEXT("Teleport occurs only at opaque black"),Camera->bEnableFading && Camera->FadeAmount>=1.f-UE_KINDA_SMALL_NUMBER);
				const double ArrivalAdjustment=FVector::Dist2D(Player->GetActorLocation(),Portal->ExitPoint->GetActorLocation());
				Test->AddInfo(FString::Printf(TEXT("Engine collision adjustment at arena arrival: %.3f cm XY"),ArrivalAdjustment));
				Test->TestTrue(TEXT("Arrival is within one capsule radius of authored feet, allowing engine encroachment adjustment"),
					ArrivalAdjustment<Player->GetCapsuleComponent()->GetScaledCapsuleRadius());
				Test->TestTrue(TEXT("Arrival control yaw matches destination"),FMath::Abs(FRotator::NormalizeAxis(Controller->GetControlRotation().Yaw-Portal->ExitPoint->GetActorRotation().Yaw))<1.f);
			}
			if(Moved && !BlackShot && Camera->FadeAmount>=1.f-UE_KINDA_SMALL_NUMBER && Now-Start>Portal->FadeOutSeconds+.06f) {BlackShot=true;Shot(TEXT("Black"));}
			if(Now-Start<Portal->FadeOutSeconds+Portal->BlackHoldSeconds+Portal->FadeInSeconds+.5f) return false;
			Test->TestTrue(TEXT("Player actually travelled to Yetuga arena"),Moved);
			Test->TestFalse(TEXT("Camera fade cleared after travel"),Camera->bEnableFading);
			CheckUnlocked();
			Test->TestFalse(TEXT("No idle portal tick"),Portal->IsActorTickEnabled());
			Test->TestTrue(TEXT("Arrival has walkable floor"),Player->GetCharacterMovement()->CurrentFloor.IsWalkableFloor());
			SafeArena=Player->GetActorLocation();
			Shot(TEXT("Arrival"));
			Portal->EntryVolume->SetGenerateOverlapEvents(false);
			// Missing destinations do not start fade or acquire input locks.
			SpawnFixture(); Move(Fixture->GetActorLocation());
			Test->TestFalse(TEXT("Missing destination cannot start transition"),Controller->PlayerCameraManager->bEnableFading);
			CheckUnlocked(); Fixture->Destroy(); Fixture.Reset();
			// An outside owner holds all the same resources before our next entry.
			Controller->SetIgnoreMoveInput(true);Controller->SetIgnoreLookInput(true);
			ASC->BlockAbilitiesWithTags(ActionTags());ASC->AddLooseGameplayTag(KZGameplayTags::State_Invulnerable);ExternalLocks=true;
			SpawnFixture(); Fixture->ExitPoint=Portal->ExitPoint;
			Move(Fixture->GetActorLocation());
			Test->TestEqual(TEXT("Portal stacks on outside invulnerability"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),BaseInvulnerable+2);
			Fixture->Destroy();Fixture.Reset();
			Test->TestTrue(TEXT("EndPlay retains outside movement lock"),Controller->IsMoveInputIgnored());
			Test->TestTrue(TEXT("EndPlay retains outside look lock"),Controller->IsLookInputIgnored());
			Test->TestTrue(TEXT("EndPlay retains outside action block"),ASC->AreAbilityTagsBlocked(ActionTags()));
			Test->TestEqual(TEXT("EndPlay removes only portal invulnerability"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),BaseInvulnerable+1);
			ReleaseExternal();CheckUnlocked();
			// Destroy the destination after entry: no teleport and a finite fade back.
			SpawnFixture();
			ExitFixture=Player->GetWorld()->SpawnActor<ATargetPoint>(Portal->ExitPoint->GetActorLocation(),FRotator::ZeroRotator);
			Fixture->ExitPoint=ExitFixture.Get();Move(Fixture->GetActorLocation());Source=Player->GetActorLocation();
			ExitFixture->Destroy();ExitFixture.Reset();Start=Now;Stage=3;
		}
		else if(Stage==3 && Now-Start>Fixture->FadeOutSeconds+Fixture->BlackHoldSeconds+Fixture->FadeInSeconds+.3f)
		{
			const double SourceAdjustment=FVector::Dist2D(Source,Player->GetActorLocation());
			Test->AddInfo(FString::Printf(TEXT("Lost destination source ground settling: %.3f cm XY"),SourceAdjustment));
			Test->TestTrue(TEXT("Lost destination keeps player at source, allowing capsule ground settling"),
				SourceAdjustment<Player->GetCapsuleComponent()->GetScaledCapsuleRadius());
			Test->TestFalse(TEXT("Failed travel clears black screen"),Controller->PlayerCameraManager->bEnableFading);
			CheckUnlocked();
			const FString Out=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PORTAL_OUT"));
			FFileHelper::SaveStringToFile(Samples, *FPaths::Combine(Out,TEXT("Runtime.csv")));
			Cleanup();return true;
		}
		return false;
	}

private:
	FGameplayTagContainer ActionTags() const {return FGameplayTagContainer(KZGameplayTags::Ability_Action);}
	FVector EntryFeet() const
	{
		FVector P=Portal->GetActorLocation();P.Z-=Portal->EntryVolume->GetScaledBoxExtent().Z;
		P.Z+=Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST;return P;
	}
	void Move(const FVector& P) {Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);}
	void SpawnFixture()
	{
		// Use the proven standing floor; repeated offsets put later fixtures in the arena cliff.
		const FVector P=SafeArena;
		Move(P+FVector(1000,0,0));
		Fixture=Player->GetWorld()->SpawnActor<AKZBossPortal>(P,FRotator::ZeroRotator);
		Fixture->EntryVolume->SetBoxExtent(FVector(80,140,160));
	}
	void CheckUnlocked()
	{
		Test->TestFalse(TEXT("Own move ignore contribution released"),Controller->IsMoveInputIgnored());
		Test->TestFalse(TEXT("Own look ignore contribution released"),Controller->IsLookInputIgnored());
		Test->TestFalse(TEXT("Own action block released"),ASC->AreAbilityTagsBlocked(ActionTags()));
		Test->TestEqual(TEXT("Own invulnerability contribution released"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),BaseInvulnerable);
	}
	void Shot(const TCHAR* Label)
	{
		if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PORTAL_CAPTURE"))!=TEXT("1"))return;
		const FString File=FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PORTAL_OUT")),FString(Label)+TEXT(".png"));
		GEngine->Exec(Player->GetWorld(),*FString::Printf(TEXT("KZ.QA.ColourShot %s"),*File));
	}
	void ReleaseExternal()
	{
		if(!ExternalLocks)return;ExternalLocks=false;
		if(Controller.IsValid()){Controller->SetIgnoreMoveInput(false);Controller->SetIgnoreLookInput(false);}
		if(ASC.IsValid()){ASC->UnBlockAbilitiesWithTags(ActionTags());ASC->RemoveLooseGameplayTag(KZGameplayTags::State_Invulnerable);}
	}
	void Cleanup()
	{
		if(Cleaned)return;Cleaned=true;
		if(Fixture.IsValid())Fixture->Destroy();if(ExitFixture.IsValid())ExitFixture->Destroy();
		ReleaseExternal();
		if(Portal.IsValid())Portal->EntryVolume->SetGenerateOverlapEvents(true);
		if(Player.IsValid()){Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorTransform(Saved,false,nullptr,ETeleportType::TeleportPhysics);}
		if(Controller.IsValid())Controller->SetControlRotation(SavedControl);
	}
	FAutomationTestBase* Test;
	double Deadline;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<APlayerController> Controller;
	TWeakObjectPtr<UAbilitySystemComponent> ASC;
	TWeakObjectPtr<AKZBossPortal> Portal,Fixture;
	TWeakObjectPtr<ATargetPoint> ExitFixture;
	FTransform Saved;
	FRotator SavedControl;
	FVector Source,SafeArena;
	FString Samples=TEXT("seconds,x,y,z,fade,fade_enabled,move_ignored,invulnerable_count\n");
	int32 Stage=0,BaseInvulnerable=0;
	float Next=0.f,Start=0.f;
	bool Moved=false,HalfShot=false,BlackShot=false,ExternalLocks=false,Cleaned=false;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZBossPortalPIE,"Khazan.Portal.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZBossPortalPIE::RunTest(const FString&)
{
	ADD_LATENT_AUTOMATION_COMMAND(KZPortalQA::FRun(this));return true;
}
#endif
