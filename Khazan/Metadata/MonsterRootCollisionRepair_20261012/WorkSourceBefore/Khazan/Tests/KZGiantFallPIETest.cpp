#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/PlayerAbility/KZFallAbility.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "AI/KZMonsterAIController.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Attribute/KZAttributeSet.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EnhancedPlayerInput.h"
#include "KZGameplayTags.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "Camera/CameraActor.h"
#include "UObject/UnrealType.h"

namespace
{
class FGiantFallCommand : public IAutomationLatentCommand
{
public:
	FGiantFallCommand(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),Deadline(FPlatformTime::Seconds()+300.){}
	bool Update() override
	{
		if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Owned DevMap GiantFall test timed out"));return Finish();}
		AKZPlayer* P=Player.Get();UWorld* W=P->GetWorld();const float Now=W->GetTimeSeconds();
		auto* ASC=CastChecked<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent());
		if(ReviewCamera.IsValid())
		{
			const FVector Location=P->GetActorLocation()+FVector(-600,-300,300); // Test-only review camera; no saved player-camera settings changed.
			ReviewCamera->SetActorLocation(Location);ReviewCamera->SetActorRotation((P->GetActorLocation()-Location).Rotation());
		}
		UKZFallAbility* ActiveFall=nullptr;
		for(const FGameplayAbilitySpec& Spec:ASC->GetActivatableAbilities())if(Spec.IsActive())if(auto* F=Cast<UKZFallAbility>(Spec.GetPrimaryInstance()))ActiveFall=F;
		if(ActiveFall)
		{
			const FString Evidence=FString::Printf(TEXT("round=%d plunge=%d node=%s mode=%d z=%.2f"),Round,ActiveFall->IsPlungeAttack(),*ActiveFall->GetCurrentNodeId().ToString(),int32(P->GetCharacterMovement()->MovementMode),P->GetActorLocation().Z);
			if(!Seen.Contains(Evidence.Left(Evidence.Find(TEXT(" mode=")))))
			{Seen.Add(Evidence.Left(Evidence.Find(TEXT(" mode="))));Test->AddInfo(Evidence);FScreenshotRequest::RequestScreenshot(FPaths::ProjectDir()+FString::Printf(TEXT("Metadata/GiantCombatFall_20261011/Fall_%d_%d_%s.png"),Round,ActiveFall->IsPlungeAttack(),*ActiveFall->GetCurrentNodeId().ToString()),false,false);}
			if(ActiveFall->IsPlungeAttack()) { SawPlunge=true;SawPlungeLand|=ActiveFall->GetCurrentNodeId()==TEXT("Land"); }
			else { SawFall=true;SawNormalLand|=ActiveFall->GetCurrentNodeId()==TEXT("Land"); }
		}
		if(Stage==0)
		{
			if(!P->GetCharacterMovement()->IsMovingOnGround())return false;
			Test->TestTrue(TEXT("Player starts on elevated saved DevMap platform"),P->GetActorLocation().Z>1200.f);
			for(TActorIterator<AKZMonster> It(W);It;++It)if(auto* AI=Cast<AKZMonsterAIController>(It->GetController())){Paused.Add(AI);AI->GetStateTreeComponent()->StopLogic(TEXT("Owned falling fixture isolation"));}
			Start=Now;Stage=1;Round=0;
			ReviewCamera=W->SpawnActor<ACameraActor>();P->GetController<APlayerController>()->SetViewTarget(ReviewCamera.Get());
		}
		if(Stage==1)
		{
			// Native input adapter drives actual CMC physics off the saved platform. No Python movement.
			P->HandleInputMove(FVector2D(1,0),FRotator::ZeroRotator);
			if(P->GetCharacterMovement()->IsFalling())
			{
				P->HandleInputMoveReleased();Start=Now;Stage=2;
				if(Round==1)
				{
					// Real EnhancedInput gamepad-X key, through the current PlayerController binding.
					P->GetController<APlayerController>()->InputKey(FInputKeyParams(EKeys::Gamepad_FaceButton_Left,IE_Pressed,1.0,true));
				}
			}
			return false;
		}
		if(Stage==2)
		{
			if(Round==1 && !ReleasedX && Now-Start>.1f)
			{P->GetController<APlayerController>()->InputKey(FInputKeyParams(EKeys::Gamepad_FaceButton_Left,IE_Released,0.0,true));ReleasedX=true;}
			if(!P->GetCharacterMovement()->IsMovingOnGround()||ActiveFall)return false;
			if(Round==0)
			{
				Test->TestTrue(TEXT("Natural falling pose and actual CMC landing observed"),SawFall&&SawNormalLand);
				P->SetActorLocation(FVector(-350,0,1292),false,nullptr,ETeleportType::TeleportPhysics);
				P->GetCharacterMovement()->Velocity=FVector::ZeroVector;P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
				Round=1;Stage=1;Start=Now;return false;
			}
			Test->TestTrue(TEXT("Physical gamepad X routed to plunge and stayed active through landing after release"),SawPlunge&&SawPlungeLand&&ReleasedX);
			bool B=false;for(const FGameplayAbilitySpec& S:ASC->GetActivatableAbilities())if(Cast<UKZBrutalAttackAbility>(S.Ability))B|=S.GetDynamicSpecSourceTags().HasTagExact(KZGameplayTags::Input_Action_B);
			Test->TestTrue(TEXT("Brutal input remains B"),B);
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_X);Stage=3;Start=Now;return false;
		}
		if(Stage==3)
		{
			const UGameplayAbility* Action=ASC->GetAnimatingAbility();
			Test->TestTrue(TEXT("Ground X resumes existing ordinary attack"),Action && !Cast<UKZFallAbility>(Action));
			if(Action) ASC->CancelAbilityHandle(Action->GetCurrentAbilitySpecHandle());
			int32 Count=0;for(TActorIterator<AKZMonster> It(W);It;++It)if(!It->GetCombatPatterns().IsEmpty())++Count;
			Test->TestEqual(TEXT("Both saved DevMap giants have original StateTree pattern rows"),Count,2);
			Stage=4;Start=Now;return false;
		}
		if(Stage==4)
		{
			if(GiantIndex>=2){Stage=5;Start=Now;return false;}
			if(!Placed)
			{
				const FString Family=GiantIndex==0?TEXT("ApesStoneHandElite"):TEXT("Yetuga");
				UClass* Class=LoadClass<AKZMonster>(nullptr,*(TEXT("/Game/Bluprints/Monsters/BP_Monster_")+Family+TEXT(".BP_Monster_")+Family+TEXT("_C")));
				FActorSpawnParameters Parameters;Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				Giants.Add(W->SpawnActor<AKZMonster>(Class,FVector(-8000,GiantIndex==0?-8000:8000,GiantIndex==0?240:265),FRotator(0,180,0),Parameters));
			}
			AKZMonster* M=Giants[GiantIndex].Get();if(!M){Test->AddError(TEXT("Missing giant"));return Finish();}
			if(!Placed)
			{
				// Fixture placement only, native GT. The monster acquires the real player via Sight.
				P->SetActorLocation(M->GetActorLocation()+FVector(-300,0,92-M->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
				P->GetCharacterMovement()->Velocity=FVector::ZeroVector;P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
				P->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),200.f);
				Start=Now;Placed=true;
			}
			auto* AI=Cast<AKZMonsterAIController>(M->GetController());
			if(AI && AI->GetBattleTarget()==P)SawSight=true;
			auto* Action=Cast<UKZMonsterPatternAbility>(M->GetAbilitySystemComponent()->GetAnimatingAbility());
			if(Action && Action->GetCurrentNodeId().ToString().StartsWith(TEXT("Roar")))SawRoar=true;
			if(Action && !Action->GetCurrentNodeId().ToString().StartsWith(TEXT("Roar")))
			{
				Test->TestTrue(TEXT("Original giant alert then autonomous StateTree attack"),SawSight&&SawRoar);
				Test->AddInfo(FString::Printf(TEXT("Giant %s state=%s node=%s"),*M->GetName(),*AI->GetStateTreeComponent()->GetDebugInfoString(),*Action->GetCurrentNodeId().ToString()));
				M->Destroy();
				++GiantIndex;Placed=false;SawSight=false;SawRoar=false;return false;
			}
			if(Now-Start>30.f){Test->AddError(FString::Printf(TEXT("Giant never attacked after original alert: %s"),*M->GetName()));++GiantIndex;Placed=false;}
			return false;
		}
		if(Stage==5)return UpdatePatterns(P,Now);
		return false;
	}
private:
	bool UpdatePatterns(AKZPlayer* P,float Now)
	{
		struct FCase{const TCHAR* Family;const TCHAR* Skill;const TCHAR* Entry;float Distance;int32 Kind;};
		// Distances/times below are isolated test stimuli, not gameplay defaults.
		static const FCase Cases[]={
			{TEXT("ApesStoneHandElite"),TEXT("NormalAtk02"),TEXT("NormalAtk02_Step1"),300,0},
			{TEXT("ApesStoneHandElite"),TEXT("NormalAtk02"),TEXT("NormalAtk02_Step1"),1200,1},
			{TEXT("Yetuga"),TEXT("DempseyRoll"),TEXT("DempseyRoll_Step2"),1200,2},
			{TEXT("ApesStoneHandElite"),TEXT("FastMove"),TEXT("FastMove_Step1"),1100,3},
			{TEXT("ApesStoneHandElite"),TEXT("FastBall"),TEXT("FastBall_Step1"),1500,4},
			{TEXT("Yetuga"),TEXT("FastBall"),TEXT("FastBall_Step1"),1500,4},
			{TEXT("Yetuga"),TEXT("IceBreath"),TEXT("IceBreath_Step2"),1500,5},
			{TEXT("Yetuga"),TEXT("CloseGrab"),TEXT("CloseGrab_Step1"),300,6}
		};
		if(PatternCase>=UE_ARRAY_COUNT(Cases))return Finish();
		const auto& C=Cases[PatternCase];UWorld* W=P->GetWorld();
		if(PatternCleanup)
		{
			// CMC removes a source marked for removal during its following movement tick.
			Test->TestFalse(TEXT("Owned RootMotionSource removed on the next CMC tick"),PatternMonster->GetCharacterMovement()->HasRootMotionSources());
			PatternMonster->Destroy();PatternMonster.Reset();Pattern.Reset();++PatternCase;PatternCleanup=false;return false;
		}
		if(!PatternMonster.IsValid())
		{
			UClass* Class=LoadClass<AKZMonster>(nullptr,*(FString(TEXT("/Game/Bluprints/Monsters/BP_Monster_"))+C.Family+TEXT(".BP_Monster_")+C.Family+TEXT("_C")));
			FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			PatternMonster=W->SpawnActor<AKZMonster>(Class,FVector(-8000,-8000,FCString::Strcmp(C.Family,TEXT("Yetuga"))==0?265:240),FRotator(0,180,0),Params);
			if(!PatternMonster.IsValid()){Test->AddError(TEXT("Pattern fixture spawn failed"));return Finish();}
			auto* AI=CastChecked<AKZMonsterAIController>(PatternMonster->GetController());AI->GetStateTreeComponent()->StopLogic(TEXT("Owned single-pattern fixture"));
			P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);Start=Now;PatternStarted=false;
			ObservedStep2=EarlyParry=LateParry=ObservedProjectile=ProjectileMoved=ObservedTrail=ObservedCapture=false;LaunchedObject.Reset();
		}
		AKZMonster* M=PatternMonster.Get();auto* AI=CastChecked<AKZMonsterAIController>(M->GetController());
		auto* ASC=CastChecked<UKZAbilitySystemComponent>(M->GetAbilitySystemComponent());
		P->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),200.f);
		if(!ObservedCapture && C.Kind!=3)
		{
			const float Distance=PatternStarted?C.Distance:FMath::Min(C.Distance,M->GetAISettings().SightRadius*.5f);
			P->SetActorLocation(M->GetActorLocation()+FVector(-Distance,0,92-M->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
			P->GetCharacterMovement()->Velocity=FVector::ZeroVector;
		}
		if(!PatternStarted)
		{
			if(C.Kind==3)P->SetActorLocation(M->GetActorLocation()+FVector(-FMath::Min(C.Distance,M->GetAISettings().SightRadius*.5f),0,92-M->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
			if(AI->GetBattleTarget()!=P){if(Now-Start>10.f){Test->AddError(TEXT("Fixture real-player Sight acquisition failed"));return Finish();}return false;}
			P->SetActorLocation(M->GetActorLocation()+FVector(-C.Distance,0,92-M->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
			UClass* Class=LoadClass<UKZMonsterPatternAbility>(nullptr,*(FString(TEXT("/Game/Monsters/"))+C.Family+TEXT("/Abilities/GA_Original_")+C.Skill+TEXT(".GA_Original_")+C.Skill+TEXT("_C")));
			FGameplayAbilitySpec* Spec=ASC->FindAbilitySpecFromClass(Class);
			if(!Spec){Test->AddError(TEXT("Source pattern grant missing"));return Finish();}
			Pattern=Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance());
			FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"))->SetPropertyValue_InContainer(Pattern.Get(),FName(C.Entry));
			AI->GetStateTreeComponent()->StopLogic(TEXT("Owned source branch fixture"));
			if(!ASC->TryActivateAbility(Spec->Handle)){Test->AddError(TEXT("Granted source pattern failed to activate"));return Finish();}
			InitialMonsterLocation=M->GetActorLocation();Start=Now;PatternStarted=true;
			Test->AddInfo(FString::Printf(TEXT("Pattern fixture %d %s %s"),PatternCase,C.Family,C.Entry));
		}
		UKZMonsterPatternAbility* A=Pattern.Get();const FName Node=A?A->GetCurrentNodeId():NAME_None;
		ObservedStep2|=Node==TEXT("NormalAtk02_Step2");
		if(C.Kind==2 && A && A->IsActive() && Node==C.Entry)
		{
			const FKZComboNode* N=A->GetComboDefinition()->FindNode(Node);UAnimInstance* Anim=M->GetMesh()->GetAnimInstance();
			const float Time=Anim->Montage_GetPosition(N->Montage)-N->Montage->CompositeSections[N->Montage->GetSectionIndex(N->SectionName)].GetTime();
			const auto* Gate=N->PatternBranches.FindByPredicate([](const auto& B){return B.Event==EKZPatternEvent::Parried;});
			if(!EarlyParry && Time>.1f)
			{EarlyParry=true;const float Before=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());Test->TestTrue(TEXT("Accepted parry outside final window"),M->ReportAttackParried(P));Test->TestEqual(TEXT("Parry decreases monster stamina by user 5"),ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()),Before-5);Test->TestEqual(TEXT("Early parry keeps the original node"),A->GetCurrentNodeId(),FName(C.Entry));}
			if(!LateParry && Gate && !Gate->ActiveWindows.IsEmpty() && Time>=Gate->ActiveWindows[0].X)
			{LateParry=true;M->ReportAttackParried(P);Test->TestEqual(TEXT("Final-window parry enters original reaction"),A->GetCurrentNodeId(),Gate->TargetNode);}
		}
		for(TActorIterator<AKZMonsterSkillObject> I(W);I;++I)if(I->GetOwner()==M)
		{
			if(I->HasLaunched() && !ObservedProjectile){ObservedProjectile=true;LaunchedObject=*I;LaunchLocation=I->GetActorLocation();}
			if(I->GetObjectId()==TEXT("COI_Yetuga_IceBreath_Field_OBJ")){ObservedTrail=true;Test->TestTrue(TEXT("Ice field placed above fixture floor"),I->GetActorLocation().Z>=0.f);}
		}
		if(LaunchedObject.IsValid())ProjectileMoved|=!LaunchedObject->GetActorLocation().Equals(LaunchLocation);
		if(C.Kind==6 && A && A->IsActive() && !ObservedCapture)
		{
			const FKZComboNode* N=A->GetComboDefinition()->FindNode(Node);
			if(N && !N->AttackWindows.IsEmpty())
			{
				const auto& Window=N->AttackWindows[0];
				const FTransform Collision=N->CollisionToActor*M->GetActorTransform();
				const FVector Point=Collision.TransformPosition(Window.Keys[0].Center);
				P->SetActorLocation(FVector(Point.X,Point.Y,92),false,nullptr,ETeleportType::TeleportPhysics);
			}
			ObservedCapture=P->GetAttachParentActor()==M;
		}
		const bool Done=C.Kind==2?LateParry:C.Kind==3?(Node!=C.Entry || !A->IsActive()):C.Kind==4?ProjectileMoved:C.Kind==5?ObservedTrail:C.Kind==6?ObservedCapture:!A->IsActive();
		if(!Done && Now-Start<=16.f)return false;
		if(!Done)Test->AddError(FString::Printf(TEXT("Pattern fixture timed out: %d %s %s node=%s"),PatternCase,C.Family,C.Skill,*Node.ToString()));
		if(C.Kind==0)Test->TestTrue(TEXT("Near original condition continues NormalAtk02 Step2"),ObservedStep2);
		if(C.Kind==1)Test->TestFalse(TEXT("Far original condition omits NormalAtk02 Step2"),ObservedStep2);
		if(C.Kind==3)Test->TestTrue(TEXT("Source MoveTo physically advances character"),FVector::Dist2D(InitialMonsterLocation,M->GetActorLocation())>M->GetCapsuleComponent()->GetScaledCapsuleRadius());
		if(C.Kind==4)Test->TestTrue(TEXT("Original held rock releases and physically travels"),ObservedProjectile&&ProjectileMoved);
		if(C.Kind==6)Test->TestTrue(TEXT("Accepted native collision establishes captured target"),ObservedCapture);
		if(A && A->IsActive())ASC->CancelAbilityHandle(A->GetCurrentAbilitySpecHandle());
		Test->TestTrue(TEXT("Cancel releases own capture attachment"),P->GetAttachParentActor()!=M);
		Test->TestFalse(TEXT("Cancel removes capture gameplay restriction"),P->GetAbilitySystemComponent()->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
		PatternCleanup=true;return false;
	}
	bool Finish()
	{
		if(Player.IsValid())Player->HandleInputMoveReleased();
		for(auto Actor:Giants)if(Actor.IsValid())Actor->Destroy();
		if(PatternMonster.IsValid())PatternMonster->Destroy();
		if(ReviewCamera.IsValid()){if(Player.IsValid())Player->GetController<APlayerController>()->SetViewTarget(Player.Get());ReviewCamera->Destroy();}
		for(auto AI:Paused)if(AI.IsValid())AI->GetStateTreeComponent()->RestartLogic();
		auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("fall"),SawFall);R->SetBoolField(TEXT("normal_landing"),SawNormalLand);
		R->SetBoolField(TEXT("plunge"),SawPlunge);R->SetBoolField(TEXT("plunge_landing"),SawPlungeLand);R->SetNumberField(TEXT("giant_count"),Giants.Num());R->SetBoolField(TEXT("passed"),!Test->HasAnyErrors());
		R->SetNumberField(TEXT("pattern_cases"),PatternCase);
		FString Out;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Out));FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectDir()+TEXT("Metadata/GiantCombatFall_20261011/PIEResult.json")));return true;
	}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TArray<TWeakObjectPtr<AKZMonster>> Giants;TSet<FString> Seen;
	TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;
	double Deadline;float Start=0;int32 Stage=0,Round=0,GiantIndex=0;
	bool SawFall=false,SawNormalLand=false,SawPlunge=false,SawPlungeLand=false,ReleasedX=false,Placed=false,SawSight=false,SawRoar=false;
	TWeakObjectPtr<ACameraActor> ReviewCamera;
	TWeakObjectPtr<AKZMonster> PatternMonster;TWeakObjectPtr<UKZMonsterPatternAbility> Pattern;
	FVector InitialMonsterLocation;int32 PatternCase=0;
	TWeakObjectPtr<AKZMonsterSkillObject> LaunchedObject;FVector LaunchLocation;
	bool PatternStarted=false,PatternCleanup=false,ObservedStep2=false,EarlyParry=false,LateParry=false,ObservedProjectile=false,ProjectileMoved=false,ObservedTrail=false,ObservedCapture=false;
};
class FWaitGiantFallPIE:public IAutomationLatentCommand
{
public:FWaitGiantFallPIE(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
	bool Update()override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetMesh()->GetAnimInstance())
			{FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FGiantFallCommand>(Test,*It));return true;}
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Start owned DevMap PIE for GiantFall test"));return true;}return false;
	}
private:FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantFallPIETest,"Khazan.GiantFall.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZGiantFallPIETest::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitGiantFallPIE>(this));return true;}
#endif
