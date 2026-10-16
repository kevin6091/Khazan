#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/PlayerAbility/KZFallAbility.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Misc/App.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/UnrealType.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "AI/KZMonsterAIController.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Character/Component/KZLockOnComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/RootMotionSource.h"
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
	FGiantFallCommand(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),Deadline(FPlatformTime::Seconds()+300.)
	{
		OutputDirectory=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_GIANT_FALL_OUTPUT"));
		if(OutputDirectory.IsEmpty())OutputDirectory=FPaths::ProjectDir()/TEXT("Metadata/GiantCombatFall_20261011");
	}
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
			{Seen.Add(Evidence.Left(Evidence.Find(TEXT(" mode="))));Test->AddInfo(Evidence);FScreenshotRequest::RequestScreenshot(OutputDirectory/FString::Printf(TEXT("Fall_%d_%d_%s.png"),Round,ActiveFall->IsPlungeAttack(),*ActiveFall->GetCurrentNodeId().ToString()),false,false);}
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
		struct FCase{const TCHAR* Family;const TCHAR* Skill;const TCHAR* Entry;float Distance;int32 Kind;bool bKillCaptor=false;};
		// Distances/times below are isolated test stimuli, not gameplay defaults.
		static const FCase Cases[]={
			{TEXT("ApesStoneHandElite"),TEXT("NormalAtk02"),TEXT("NormalAtk02_Step1"),300,0},
			{TEXT("ApesStoneHandElite"),TEXT("NormalAtk02"),TEXT("NormalAtk02_Step1"),1200,1},
			{TEXT("Yetuga"),TEXT("DempseyRoll"),TEXT("DempseyRoll_Step2"),1200,2},
			{TEXT("ApesStoneHandElite"),TEXT("FastMove"),TEXT("FastMove_Step1"),1100,3},
			{TEXT("ApesStoneHandElite"),TEXT("FastBall"),TEXT("FastBall_Step1"),1500,4},
			{TEXT("Yetuga"),TEXT("FastBall"),TEXT("FastBall_Step1"),1500,4},
			{TEXT("Yetuga"),TEXT("IceBreath"),TEXT("IceBreath_Step2"),1500,5},
			{TEXT("Yetuga"),TEXT("CloseGrab"),TEXT("CloseGrab_Step1"),300,6},
			{TEXT("ApesStoneHandElite"),TEXT("Dodge_A"),TEXT("Dodge_A_Step8"),300,7},
			{TEXT("ApesStoneHandElite"),TEXT("Level_DashAtk_New"),TEXT("Level_DashAtk_New_Step8"),300,7},
			{TEXT("Yetuga"),TEXT("CloseGrab"),TEXT("CloseGrab_Step1"),300,7},
			{TEXT("Yetuga"),TEXT("RushGrab"),TEXT("RushGrab_Step5"),300,7},
			{TEXT("Yetuga"),TEXT("CloseGrab"),TEXT("CloseGrab_Step1"),300,6,true},
			{TEXT("Yetuga"),TEXT("Armageddon"),TEXT("Armageddon_Step3"),300,8}
		};
		if(PatternCase>=UE_ARRAY_COUNT(Cases))return Finish();
		const auto& C=Cases[PatternCase];UWorld* W=P->GetWorld();
		const bool bYetugaCapture = FCString::Strcmp(C.Family,TEXT("Yetuga"))==0 && (C.Kind==6 || C.Kind==7);
		UKZLockOnComponent* LockOn=P->FindComponentByClass<UKZLockOnComponent>();
		if(PatternCleanup)
		{
			// CMC removes a source marked for removal during its following movement tick.
			if(C.bKillCaptor)
			{
				// HasRootMotionSources also includes the newly started death montage.
				const auto& Group=PatternMonster->GetCharacterMovement()->CurrentRootMotion;
				for(const auto* List:{&Group.RootMotionSources,&Group.PendingAddRootMotionSources})
					for(const auto& Source:*List)if(Source.IsValid() && Source->InstanceName==TEXT("OriginalPatternMoveTo"))
						Test->TestTrue(TEXT("Dead captor has released its own pattern movement"),Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval));
			}
			else Test->TestFalse(TEXT("Owned RootMotionSource removed on the next CMC tick"),PatternMonster->GetCharacterMovement()->HasRootMotionSources());
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
			ObservedStep2=EarlyParry=LateParry=ObservedProjectile=ProjectileMoved=ObservedTrail=ObservedCapture=false;
			ObservedHeldSuccess=ObservedVictimMontage=ObservedPausedHold=ObservedCaptureAlignment=ObservedLandingHit=ObservedArmageddonFollowup=false;MaxVictimMontagePosition=0.f;LaunchedObject.Reset();
			bCaptureLockChecked=false;
			if(bYetugaCapture)P->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),2000.f); // QA-only survival stimulus.
		}
		AKZMonster* M=PatternMonster.Get();auto* AI=CastChecked<AKZMonsterAIController>(M->GetController());
		auto* ASC=CastChecked<UKZAbilitySystemComponent>(M->GetAbilitySystemComponent());
		if((C.Kind!=7 && C.Kind!=8) || !PatternStarted)
			P->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),bYetugaCapture?2000.f:200.f);
		if(!ObservedCapture && C.Kind!=3 && P->GetAttachParentActor()!=PatternMonster.Get())
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
			if(bYetugaCapture)Test->TestTrue(TEXT("Yetuga is locked before the actual capture attempt"),LockOn && LockOn->StartLockOn(M));
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
		if((C.Kind==6 || C.Kind==7) && A && A->IsActive() && !ObservedCapture)
		{
			const FKZComboNode* N=A->GetComboDefinition()->FindNode(Node);
			if(N && !N->AttackWindows.IsEmpty())
			{
				const auto& Window=N->AttackWindows[0];
				const FTransform Collision=N->CollisionToActor*M->GetActorTransform();
				const FVector Point=Collision.TransformPosition(Window.Keys[0].Center);
				if(P->GetAttachParentActor()!=M)
					P->SetActorLocation(FVector(Point.X,Point.Y,C.Kind==7?Point.Z:92.f),false,nullptr,ETeleportType::TeleportPhysics);
			}
			ObservedCapture=P->GetAttachParentActor()==M;
		}
		if(bYetugaCapture && ObservedCapture && !bCaptureLockChecked)
		{
			bCaptureLockChecked=true;
			Test->TestFalse(TEXT("Successful Yetuga grab immediately releases LockOn"),LockOn->IsLockedOn());
			Test->TestFalse(TEXT("Player cannot re-lock while attached by the grab"),LockOn->StartLockOn(M));
			LockOn->ToggleLockOn();
			Test->TestFalse(TEXT("Manual toggle cannot re-lock during the grab"),LockOn->IsLockedOn());
		}
		if(C.Kind==7 && ObservedCapture && A && A->IsActive())
		{
			const bool bSuccess=Node==TEXT("Dodge_A_Step10") || Node==TEXT("Dodge_A_Step11") ||
				Node==TEXT("Level_DashAtk_New_Step10") || Node==TEXT("Level_DashAtk_New_Step11") ||
				Node==TEXT("CloseGrab_Step3") || Node==TEXT("CloseGrab_Step4") || Node==TEXT("CloseGrab_Step5") ||
				Node==TEXT("RushGrab_Step2") || Node==TEXT("RushGrab_Step4");
			if(bSuccess && P->GetAttachParentActor()==M)
			{
				ObservedHeldSuccess=true;
				const FName TargetSocket=FCString::Strcmp(C.Family,TEXT("Yetuga"))==0?TEXT("Hold_Spine"):TEXT("Bip001-Spine");
				ObservedCaptureAlignment|=P->GetMesh()->DoesSocketExist(TargetSocket) &&
					FVector::Dist(M->GetMesh()->GetSocketLocation(TEXT("Weapon_L")),P->GetMesh()->GetSocketLocation(TargetSocket))<1.f;
			}
			if(UAnimInstance* VictimAnim=P->GetMesh()->GetAnimInstance())
				if(UAnimMontage* VictimMontage=VictimAnim->GetCurrentActiveMontage();VictimMontage && VictimMontage->GetOuter()==GetTransientPackage())
				{
					ObservedVictimMontage=true;
					MaxVictimMontagePosition=FMath::Max(MaxVictimMontagePosition,VictimAnim->Montage_GetPosition(VictimMontage));
					ObservedPausedHold|=!VictimAnim->Montage_IsPlaying(VictimMontage) &&
						FMath::IsNearlyEqual(VictimAnim->Montage_GetPosition(VictimMontage),39.f/30.f,.02f);
				}
		}
		if(C.Kind==8 && PatternStarted)
		{
			ObservedLandingHit|=P->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())<200.f;
			ObservedArmageddonFollowup|=Node==TEXT("RushGrab_Step5");
		}
		const bool Done=C.Kind==2?LateParry:C.Kind==3?(Node!=C.Entry || !A->IsActive()):C.Kind==4?ProjectileMoved:C.Kind==5?ObservedTrail:C.Kind==6?ObservedCapture:C.Kind==7?ObservedCapture && !A->IsActive():C.Kind==8?ObservedLandingHit && ObservedArmageddonFollowup:!A->IsActive();
		if(!Done && Now-Start<=16.f)return false;
		if(!Done)Test->AddError(FString::Printf(TEXT("Pattern fixture timed out: %d %s %s node=%s"),PatternCase,C.Family,C.Skill,*Node.ToString()));
		if(C.Kind==0)Test->TestTrue(TEXT("Near original condition continues NormalAtk02 Step2"),ObservedStep2);
		if(C.Kind==1)Test->TestFalse(TEXT("Far original condition omits NormalAtk02 Step2"),ObservedStep2);
		if(C.Kind==3)Test->TestTrue(TEXT("Source MoveTo physically advances character"),FVector::Dist2D(InitialMonsterLocation,M->GetActorLocation())>M->GetCapsuleComponent()->GetScaledCapsuleRadius());
		if(C.Kind==4)Test->TestTrue(TEXT("Original held rock releases and physically travels"),ObservedProjectile&&ProjectileMoved);
		if(C.Kind==6)Test->TestTrue(TEXT("Accepted native collision establishes captured target"),ObservedCapture);
		if(C.Kind==7)
		{
			Test->TestTrue(TEXT("Original grab kept its victim through a success node"),ObservedHeldSuccess);
			Test->TestTrue(TEXT("Original hand-to-victim socket stays aligned through success"),ObservedCaptureAlignment);
			Test->TestTrue(TEXT("Player source hold animation played while captured"),ObservedVictimMontage);
			Test->TestTrue(TEXT("Player reached the final source sample, or the grab released within its final frame"),ObservedPausedHold || MaxVictimMontagePosition>=38.f/30.f);
			Test->TestTrue(TEXT("Full grab follow-up released its own attachment"),P->GetAttachParentActor()!=M);
		}
		if(C.Kind==8)
		{
			Test->TestTrue(TEXT("Armageddon landing applied the saved radial hit"),ObservedLandingHit);
			Test->TestTrue(TEXT("Armageddon reached its original RushGrab follow-up"),ObservedArmageddonFollowup);
		}
		if(C.bKillCaptor)ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),0.f);
		if(A && A->IsActive())ASC->CancelAbilityHandle(A->GetCurrentAbilitySpecHandle());
		if(bYetugaCapture)
		{
			Test->TestTrue(TEXT("Actual capture reached the lock suspension assertions"),bCaptureLockChecked);
			if(C.bKillCaptor)Test->TestFalse(TEXT("Capture cleanup never re-locks a dead Yetuga"),LockOn->IsLockedOn());
			else Test->TestEqual(TEXT("Completed/cancelled capture re-locks the same living Yetuga"),LockOn->GetCurrentTarget(),M);
			LockOn->StopLockOn();
		}
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
		FString Out;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Out));FFileHelper::SaveStringToFile(Out,*(OutputDirectory/TEXT("PIEResult.json")));return true;
	}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TArray<TWeakObjectPtr<AKZMonster>> Giants;TSet<FString> Seen;
	TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;
	double Deadline;float Start=0;int32 Stage=0,Round=0,GiantIndex=0;
	bool SawFall=false,SawNormalLand=false,SawPlunge=false,SawPlungeLand=false,ReleasedX=false,Placed=false,SawSight=false,SawRoar=false;
	TWeakObjectPtr<ACameraActor> ReviewCamera;
	TWeakObjectPtr<AKZMonster> PatternMonster;TWeakObjectPtr<UKZMonsterPatternAbility> Pattern;
	FVector InitialMonsterLocation;int32 PatternCase=0;
	TWeakObjectPtr<AKZMonsterSkillObject> LaunchedObject;FVector LaunchLocation;
	bool PatternStarted=false,PatternCleanup=false,ObservedStep2=false,EarlyParry=false,LateParry=false,ObservedProjectile=false,ProjectileMoved=false,ObservedTrail=false,ObservedCapture=false,ObservedHeldSuccess=false,ObservedVictimMontage=false,ObservedPausedHold=false,ObservedCaptureAlignment=false,ObservedLandingHit=false,ObservedArmageddonFollowup=false;
	float MaxVictimMontagePosition=0.f;
	bool bCaptureLockChecked=false;
	FString OutputDirectory;
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
namespace KZGiantCombatQA
{
class FRun final : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* InTest, AKZPlayer* InPlayer) : Test(InTest), Player(InPlayer), Deadline(FPlatformTime::Seconds()+180.)
	{
		Fixed=FApp::UseFixedTimeStep(); Delta=FApp::GetFixedDeltaTime(); FApp::SetUseFixedTimeStep(true); FApp::SetFixedDeltaTime(1./60.);
		SavedPlayer=InPlayer->GetActorTransform(); SavedMode=InPlayer->GetCharacterMovement()->MovementMode;
		for(TActorIterator<AKZMonster> It(InPlayer->GetWorld());It;++It)
			if(auto* OtherAI=Cast<AKZMonsterAIController>(It->GetController());OtherAI&&!OtherAI->GetStateTreeComponent()->IsPaused())
			{ OtherAI->GetStateTreeComponent()->PauseLogic(TEXT("Owned giant far-combat QA")); Paused.Add(OtherAI); }
		Floor=InPlayer->GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,20000),FRotator::ZeroRotator);
		Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
		Floor->SetActorScale3D(FVector(160,160,.2)); Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	}
	~FRun() override {Cleanup();}
	bool Update() override
	{
		if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Giant far-combat watchdog"));Cleanup();return true;}
		if(Family==2){Test->AddInfo(TEXT("GIANT_COMBAT_FEEL_COMPLETE 2 families: distant pursuit, Armageddon, actual long-range capture"));Cleanup();return true;}
		AKZPlayer* P=Player.Get(); UWorld* W=P->GetWorld(); const float Now=W->GetTimeSeconds();
		if(Stage==0)
		{
			Name=Family==0?TEXT("ApesStoneHandElite"):TEXT("Yetuga");
			UClass* Class=LoadClass<AKZMonster>(nullptr,*FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),*Name,*Name));
			FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Monster=W->SpawnActor<AKZMonster>(Class,FVector(0,0,20300),FRotator::ZeroRotator,Params);
			if(!Test->TestNotNull(TEXT("Real giant BP at a floor outside baked navmesh"),Monster.Get())){Cleanup();return true;}
			AI=Cast<AKZMonsterAIController>(Monster->GetController());
			if(!Test->TestNotNull(TEXT("Real StateTree AI controller"),AI.Get())){Cleanup();return true;}
			Monster->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
			ResetActors(300.f); SavedChance=Monster->GetAISettings().RangedPatternChance;
			const_cast<FKZMonsterAISettings&>(Monster->GetAISettings()).RangedPatternChance=0.f; // QA zero-chance boundary only.
			Start=Now;Stage=1;return false;
		}
		if(Stage==1)
		{
			if(AI->GetBattleTarget()!=P)
			{if(Now-Start<20.f)return false;Test->AddError(TEXT("Real perception did not acquire nearby player"));Cleanup();return true;}
			PlacePlayer(4500.f); FarStart=Monster->GetActorLocation(); Start=Now;SawPursuit=SawFarAttack=false;Stage=2;return false;
		}
		if(Stage==2)
		{
			const auto* Pattern=Cast<UKZMonsterPatternAbility>(Monster->GetAbilitySystemComponent()->GetAnimatingAbility());
			SawFarAttack|=Pattern&&Pattern->IsActive()&&!Pattern->GetCurrentNodeId().ToString().StartsWith(TEXT("Roar"));
			SawPursuit|=AI->GetMoveStatus()==EPathFollowingStatus::Moving || Monster->GetLocomotionComponent()->GetLocomotionIntent().InputAmount>0.f;
			if(Now-Start<12.f)return false;
			Test->TestTrue(TEXT("Acquired target persists at long range"),AI->GetBattleTarget()==P);
			Test->TestTrue(TEXT("Retreat beyond baked navmesh leads to movement or a new attack"),SawFarAttack || (SawPursuit&&FVector::Dist2D(FarStart,Monster->GetActorLocation())>100.f));
			Test->AddInfo(FString::Printf(TEXT("GIANT_FAR_PURSUIT %s moving=%d attack=%d travel=%g state=%s"),*Name,SawPursuit,SawFarAttack,FVector::Dist2D(FarStart,Monster->GetActorLocation()),*AI->GetStateTreeComponent()->GetDebugInfoString()));
			const auto* CMC=Monster->GetCharacterMovement();const auto* Anim=Monster->GetMesh()->GetAnimInstance();
			Test->AddInfo(FString::Printf(TEXT("GIANT_PURSUIT_RUNTIME %s mode=%d maxSpeed=%g velocity=%s requested=%s rootMode=%d root=%d activeMontage=%s intent=%s"),
				*Name,int32(CMC->MovementMode),CMC->MaxWalkSpeed,*CMC->Velocity.ToString(),*CMC->RequestedVelocity.ToString(),int32(Anim->RootMotionMode.GetValue()),CMC->HasAnimRootMotion(),*GetNameSafe(Anim->GetCurrentActiveMontage()),*Monster->GetLocomotionComponent()->GetLocomotionIntent().MoveInputWorld.ToString()));
			if(Family==1)
			{
				const_cast<FKZMonsterAISettings&>(Monster->GetAISettings()).RangedPatternChance=1.f; // QA certain boundary, retain saved 0.3 default.
				Monster->GetAbilitySystemComponent()->CancelAllAbilities();ResetActors(4500.f);AI->GetStateTreeComponent()->RestartLogic();Start=Now;Stage=3;return false;
			}
			Stage=4;
		}
		if(Stage==3)
		{
			const auto* Pattern=Cast<UKZMonsterPatternAbility>(Monster->GetAbilitySystemComponent()->GetAnimatingAbility());
			if(Pattern&&Pattern->IsActive()&&Pattern->GetCurrentNodeId().ToString().StartsWith(TEXT("Armageddon")))
			{Test->AddInfo(TEXT("GIANT_FAR_ARMAGEDDON real full-HP SourceGate/StateTree entry at 4500 cm"));Stage=4;}
			else if(Now-Start<20.f)return false;
			else {Test->AddError(TEXT("Far Armageddon did not enter through real StateTree"));Stage=4;}
		}
		if(Stage==4)
		{
			AI->GetStateTreeComponent()->StopLogic(TEXT("Owned actual capture reach QA"));Monster->GetAbilitySystemComponent()->CancelAllAbilities();ResetActors(2000.f);
			const FString Skill=Family==0?TEXT("Level_DashAtk_New"):TEXT("RushGrab");
			UClass* Class=LoadClass<UKZMonsterPatternAbility>(nullptr,*FString::Printf(TEXT("/Game/Monsters/%s/Abilities/GA_Original_%s.GA_Original_%s_C"),*Name,*Skill,*Skill));
			auto* ASC=Monster->GetAbilitySystemComponent();FGameplayAbilitySpec* Spec=ASC->FindAbilitySpecFromClass(Class);
			Capture=Spec?Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance()):nullptr;
			if(!Test->TestNotNull(TEXT("Actual granted capture ability"),Capture.Get())){Cleanup();return true;}
			EntryProperty=FindFProperty<FNameProperty>(Capture->GetClass(),TEXT("EntryNodeId"));
			SavedEntry=EntryProperty->GetPropertyValue_InContainer(Capture.Get());
			EntryProperty->SetPropertyValue_InContainer(Capture.Get(),Family==0?FName(TEXT("Level_DashAtk_New_Step8")):FName(TEXT("RushGrab_Step5")));
			if(!Test->TestTrue(TEXT("Real long-range grab activates"),ASC->TryActivateAbility(Spec->Handle))){Cleanup();return true;}
			CaptureStart=Monster->GetActorLocation();Start=Now;Stage=5;return false;
		}
		if(Stage==5)
		{
			const float Travel=FVector::Dist2D(CaptureStart,Monster->GetActorLocation());
			const bool Held=P->GetAttachParentActor()==Monster.Get();
			if(!Held&&Now-Start<6.f&&Capture->IsActive())return false;
			Test->TestTrue(TEXT("A stationary distant player is reached by actual capture collision, without QA teleport to the hand"),Held);
			Test->TestTrue(TEXT("Grab capsule traveled beyond source short clamp"),Travel>500.f);
			Test->AddInfo(FString::Printf(TEXT("GIANT_LONG_CAPTURE %s travel=%g held=%d node=%s"),*Name,Travel,Held,*Capture->GetCurrentNodeId().ToString()));
			Monster->GetAbilitySystemComponent()->CancelAllAbilities();RestoreEntry();Monster->Destroy();Monster.Reset();AI.Reset();++Family;Stage=0;return false;
		}
		return false;
	}
private:
	void PlacePlayer(float Distance)
	{
		Player->SetActorLocation(FVector(Distance,0,20010.f+Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST));
		Player->GetCharacterMovement()->StopMovementImmediately();Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	}
	void ResetActors(float Distance)
	{
		Player->HandleInputMoveReleased();Player->GetAbilitySystemComponent()->CancelAllAbilities();
		Player->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),1000.f);
		Player->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),1000.f);
		Monster->SetActorLocationAndRotation(FVector(0,0,20010.f+Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST),FRotator::ZeroRotator);
		Monster->GetCharacterMovement()->StopMovementImmediately();Monster->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
		Monster->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),1000.f);
		Monster->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),1000.f);PlacePlayer(Distance);
	}
	void RestoreEntry(){if(Capture.IsValid()&&EntryProperty)EntryProperty->SetPropertyValue_InContainer(Capture.Get(),SavedEntry);Capture.Reset();EntryProperty=nullptr;}
	void Cleanup()
	{
		if(Cleaned)return;Cleaned=true;RestoreEntry();if(Monster.IsValid())Monster->Destroy();if(Floor.IsValid())Floor->Destroy();
		if(Player.IsValid()){Player->GetAbilitySystemComponent()->CancelAllAbilities();Player->SetActorTransform(SavedPlayer);Player->GetCharacterMovement()->SetMovementMode(SavedMode);}
		for(auto Controller:Paused)if(Controller.IsValid())Controller->GetStateTreeComponent()->ResumeLogic(TEXT("Owned giant far-combat QA complete"));
		FApp::SetUseFixedTimeStep(Fixed);FApp::SetFixedDeltaTime(Delta);
	}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Monster;TWeakObjectPtr<AKZMonsterAIController> AI;
	TWeakObjectPtr<AStaticMeshActor> Floor;TWeakObjectPtr<UKZMonsterPatternAbility> Capture;TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;
	FNameProperty* EntryProperty=nullptr;FName SavedEntry;FTransform SavedPlayer;EMovementMode SavedMode=MOVE_Walking;
	FVector FarStart,CaptureStart;FString Name;double Deadline,Delta;float Start=0.f,SavedChance=0.f;
	int32 Stage=0,Family=0;bool Fixed=false,SawPursuit=false,SawFarAttack=false,Cleaned=false;
};
class FWait final : public IAutomationLatentCommand
{
public:FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
	bool Update() override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetMesh()->GetAnimInstance())
			{FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("No owned PIE for giant far-combat"));return true;}return false;
	}
	FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantCombatFeelPIETest,"Khazan.GiantCombatFeel.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZGiantCombatFeelPIETest::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZGiantCombatQA::FWait>(this));return true;}
#endif
