// Focused saved-animation camera integration. No gameplay damage or asset saves.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Camera/KZCombatCameraModifier.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Animation/AnimSequence.h"
#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Paths.h"
#include "Misc/App.h"

namespace
{
struct FCameraCase
{
	const TCHAR* Family;
	const TCHAR* Asset;
	int32 ExpectedWindows;
};
const FCameraCase Cases[] = {
	{TEXT("Yetuga"), TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_NormalAtk02_01"), 1},
	{TEXT("Yetuga"), TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Idle/Idle_Social"), 1},
	{TEXT("ApesStoneHandElite"), TEXT("/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Attack/Attack_CloseGrab_Success_01_Turn"), 1},
	{TEXT("ApesStoneHandElite"), TEXT("/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Locomotion/Locomotion_Run_Loop_Composite_Variant01"), 4},
};

class FRunGiantCamera : public IAutomationLatentCommand
{
public:
	FRunGiantCamera(FAutomationTestBase* InTest, AKZPlayer* InPlayer)
		: Test(InTest), Player(InPlayer), Deadline(FPlatformTime::Seconds() + 100.) {}
	~FRunGiantCamera() override { Cleanup(); }
	bool Update() override
	{
		if (!Player.IsValid() || FPlatformTime::Seconds() > Deadline)
		{
			Test->AddError(TEXT("GiantCamera PIE lost player or exceeded task deadline"));
			return Finish();
		}
		if (Index == UE_ARRAY_COUNT(Cases)) return Finish();
		APlayerController* PC = Player->GetController<APlayerController>();
		if (!PC || !PC->PlayerCameraManager) { Test->AddError(TEXT("Local camera manager unavailable")); return Finish(); }
		UWorld* World = Player->GetWorld();
		if (!bRunning)
		{
			const FCameraCase& Case = Cases[Index];
			const FString BP = FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s"), Case.Family);
			UClass* Class = LoadClass<AKZMonster>(nullptr, *(BP + TEXT(".") + FPaths::GetCleanFilename(BP) + TEXT("_C")));
			Sequence = LoadObject<UAnimSequence>(nullptr, Case.Asset);
			if (!Test->TestNotNull(TEXT("Actual monster BP loads"), Class) || !Test->TestNotNull(TEXT("Actual source-mapped sequence loads"), Sequence.Get())) return Finish();
			int32 Windows = 0;
			FirstWindow = TNumericLimits<float>::Max();
			FadeOut = 0.f;
			for (const FAnimNotifyEvent& Event : Sequence->Notifies)
				if (const auto* State = Cast<UKZAnimNotifyState_MonsterVisual>(Event.NotifyStateClass.Get()); State && State->bSourceCameraShake)
				{
					++Windows;
					FirstWindow = FMath::Min(FirstWindow, Event.GetTime());
					FadeOut = FMath::Max(FadeOut, State->CameraFadeOutSeconds);
					Test->TestTrue(TEXT("Saved source camera window has finite times and identity"),
						!State->CameraEventId.IsNone() && Event.GetTime() >= 0.f && Event.GetDuration() > 0.f &&
						Event.GetEndTriggerTime() <= Sequence->GetPlayLength() + KINDA_SMALL_NUMBER);
				}
			if (!Test->TestEqual(TEXT("Mapped camera notify count"), Windows, Case.ExpectedWindows)) return Finish();
			FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			FVector Position = Player->GetActorLocation() + Player->GetActorForwardVector() * 300.f; // QA staging only.
			Monster = World->SpawnActor<AKZMonster>(Class, Position, Player->GetActorRotation(), Params);
			if (!Test->TestNotNull(TEXT("Real monster actor spawns"), Monster.Get())) return Finish();
			if (AAIController* AI = Cast<AAIController>(Monster->GetController()); AI && AI->BrainComponent) AI->BrainComponent->PauseLogic(TEXT("GiantCamera focused playback"));
			Monster->GetAbilitySystemComponent()->CancelAllAbilities();
			Monster->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
			Monster->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
			Monster->GetMesh()->PlayAnimation(Sequence.Get(), false);
			Modifier = UKZCombatCameraModifier::GetOrCreate(PC);
			if (!Test->TestNotNull(TEXT("Local camera modifier installed"), Modifier.Get())) return Finish();
			Start = World->GetTimeSeconds();
			const float Rate = FMath::Max(Sequence->RateScale, UE_SMALL_NUMBER);
			CaseEnd = Start + Sequence->GetPlayLength() / Rate + FadeOut + 0.3f;
			FirstObserved = -1.f;
			Samples = 0;
			MaxAxes = FVector::ZeroVector;
			bRunning = true;
			return false;
		}
		const double Now = World->GetTimeSeconds();
		const int32 Active = Modifier.IsValid() && Monster.IsValid() ? Modifier->GetActiveSourceShakeCountForMesh(Monster->GetMesh()) : 0;
		if (Active > 0)
		{
			if (FirstObserved < 0.f) FirstObserved = float(Now - Start);
			++Samples;
			const FVector Axes = Modifier->GetLastLocalTranslation().GetAbs();
			MaxAxes.X = FMath::Max(MaxAxes.X, Axes.X);
			MaxAxes.Y = FMath::Max(MaxAxes.Y, Axes.Y);
			MaxAxes.Z = FMath::Max(MaxAxes.Z, Axes.Z);
		}
		if (Now < CaseEnd) return false;
		const FCameraCase& Case = Cases[Index];
		Test->TestTrue(TEXT("Source notify reached the real local camera"), Samples > 1);
		// Asset timestamps are checked to sub-millisecond accuracy by the fresh
		// saved readback. Offscreen RHI may skip several samples while streaming;
		// it can establish arrival and non-early start, not a frame-exact onset.
		Test->TestTrue(TEXT("Source camera does not begin before the authored notify"),
			FirstObserved >= FirstWindow - 0.05f);
		Test->TestTrue(TEXT("Continuous camera translation samples all forward/right/up axes"), MaxAxes.GetMin() > UE_SMALL_NUMBER);
		Test->TestEqual(TEXT("Camera source has fully released after its authored fade"), Active, 0);
		Test->AddInfo(FString::Printf(TEXT("GIANT_CAMERA_CASE %s %s samples=%d first=%g authored=%g maxAxes=%s"),
			Case.Family, *Sequence->GetName(), Samples, FirstObserved, FirstWindow, *MaxAxes.ToString()));
		Monster->Destroy(); Monster.Reset(); Sequence.Reset(); Modifier.Reset();
		bRunning = false; ++Index;
		return false;
	}
private:
	void Cleanup() { if (Monster.IsValid()) Monster->Destroy(); Monster.Reset(); }
	bool Finish() { Cleanup(); Test->AddInfo(TEXT("GIANT_CAMERA_CASES_COMPLETE 4 attack/behavior sequences")); return true; }
	FAutomationTestBase* Test;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<AKZMonster> Monster;
	TWeakObjectPtr<UKZCombatCameraModifier> Modifier;
	TWeakObjectPtr<UAnimSequence> Sequence;
	double Deadline, Start = 0., CaseEnd = 0.;
	float FirstWindow = 0.f, FirstObserved = -1.f, FadeOut = 0.f;
	FVector MaxAxes = FVector::ZeroVector;
	int32 Index = 0, Samples = 0;
	bool bRunning = false;
};

class FWaitGiantCameraPIE : public IAutomationLatentCommand
{
public:
	FWaitGiantCameraPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 60.) {}
	bool Update() override
	{
		if (GEngine) for (const FWorldContext& Context : GEngine->GetWorldContexts())
			if (Context.WorldType == EWorldType::PIE && Context.World() && Context.World()->HasBegunPlay())
				for (TActorIterator<AKZPlayer> It(Context.World()); It; ++It)
					if (It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance())
					{ FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRunGiantCamera>(Test, *It)); return true; }
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Start task-owned PIE for GiantCamera")); return true; }
		return false;
	}
private:
	FAutomationTestBase* Test;
	double Deadline;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantCameraPIETest, "Khazan.GiantCamera.PIE",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZGiantCameraPIETest::RunTest(const FString&)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitGiantCameraPIE>(this));
	return true;
}
namespace KZLinearCameraQA
{
class FRun final : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* T, AKZPlayer* P):Test(T),Player(P),Deadline(FPlatformTime::Seconds()+30.)
	{Fixed=FApp::UseFixedTimeStep();Delta=FApp::GetFixedDeltaTime();FApp::SetUseFixedTimeStep(true);FApp::SetFixedDeltaTime(1./60.);}
	~FRun() override{FApp::SetUseFixedTimeStep(Fixed);FApp::SetFixedDeltaTime(Delta);}
	bool Update() override
	{
		if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Linear camera watchdog"));return true;}
		if(Case==4)return true;
		UWorld* World=Player->GetWorld();const float Now=World->GetTimeSeconds();
		if(!Running)
		{
			Modifier=UKZCombatCameraModifier::GetOrCreate(Player->GetController<APlayerController>());
			if(!Test->TestNotNull(TEXT("Actual local camera modifier"),Modifier.Get()))return true;
			Modifier->StartSourceShake(Player->GetMesh(),100+Case,TEXT("LinearImpulseQA"),1.1f,FVector(0,12,0),
				Case==1?FVector(0,25,0):FVector::ZeroVector,0,0,1,1,0,0,0,0);
			Start=LastTime=Now;Last=FVector::ZeroVector;Peak=MaxStepSpeed=0.f;Samples=0;SawPositive=SawNegative=Ended=Added=false;Running=true;return false;
		}
		const float Age=Now-Start;const FVector Current=Modifier->GetLastLocalTranslation();
		if(Now>LastTime)
		{
			MaxStepSpeed=FMath::Max(MaxStepSpeed,float(FVector::Distance(Current,Last)/(Now-LastTime)));
			Test->TestTrue(TEXT("Force displacement never teleports at frame boundaries or on cancellation"),FVector::Distance(Current,Last)<=400.f*(Now-LastTime)+.001f); // Independent QA speed bound, cm/s.
		}
		Last=Current;LastTime=Now;Peak=FMath::Max(Peak,float(Current.Size()));++Samples;
		SawPositive|=Current.Y>1.f;SawNegative|=Current.Y<-1.f;
		if(Case==2&&!Ended&&Age>=.05f){Modifier->EndSourceShake(Player->GetMesh(),100+Case);Ended=true;}
		if(Case==3&&!Added&&Age>=.05f)
		{
			Modifier->StartSourceShake(Player->GetMesh(),200+Case,TEXT("SecondImpulseQA"),1.1f,FVector(0,0,8),FVector::ZeroVector,0,0,1,1,0,0,0,0);
			Test->TestEqual(TEXT("A second directional force retains the first force"),Modifier->GetActiveSourceShakeCountForMesh(Player->GetMesh()),2);Added=true;
		}
		if(Age<1.8f)return false;
		Test->TestTrue(TEXT("Real camera sampled a directional push"),Samples>1&&Peak>1.f&&SawPositive);
		if(Case==1)Test->TestTrue(TEXT("Repeated forces alternate and recover, producing sustained tremor"),SawNegative);
		Test->TestTrue(TEXT("Camera returns to its original position after all force tails"),Current.IsNearlyZero(.001f));
		Test->TestEqual(TEXT("No camera events survive their finite tail"),Modifier->GetActiveSourceShakeCountForMesh(Player->GetMesh()),0);
		Test->AddInfo(FString::Printf(TEXT("LINEAR_CAMERA_CASE %d samples=%d peak=%gcm maxFrameSpeed=%gcm/s"),Case,Samples,Peak,MaxStepSpeed));
		++Case;Running=false;return false;
	}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<UKZCombatCameraModifier> Modifier;
	double Deadline,Delta;float Start=0,LastTime=0,Peak=0,MaxStepSpeed=0;FVector Last;int32 Case=0,Samples=0;
	bool Fixed=false,Running=false,SawPositive=false,SawNegative=false,Ended=false,Added=false;
};
class FWait final : public IAutomationLatentCommand
{
public:FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
	bool Update() override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetMesh()->GetAnimInstance())
			{FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("No owned PIE for linear camera"));return true;}return false;
	}
	FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZLinearCameraPIE,"Khazan.LinearCamera.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZLinearCameraPIE::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZLinearCameraQA::FWait>(this));return true;}
#endif
