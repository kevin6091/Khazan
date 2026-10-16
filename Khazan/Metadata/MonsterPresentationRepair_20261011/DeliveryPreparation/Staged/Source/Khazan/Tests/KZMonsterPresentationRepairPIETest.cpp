// Development-only full attack occurrence / corpse presentation regression.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "AI/KZMonsterAIController.h"
#include "Components/StateTreeAIComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/MeshComponent.h"
#include "Components/DecalComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimNotifyQueue.h"
#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"
#include "ParticleEmitterInstances.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Attribute/KZAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "UnrealClient.h"
#include "UObject/UObjectIterator.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "ImageUtils.h"
#include "Editor.h"
#include "Settings/LevelEditorPlaySettings.h"
namespace KZMonsterRepairQA
{
const TCHAR* Families[]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
struct FCase {FString Asset,Family;};
class FRun:public IAutomationLatentCommand
{
public:
 FRun(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),Deadline(FPlatformTime::Seconds()+1100.){}
 ~FRun()override{Cleanup();}
 bool Update()override
 {
  if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Monster repair actual PIE watchdog"));return Finish();}
  UWorld* W=Player->GetWorld();float Now=W->GetTimeSeconds();
  if(Camera.IsValid()){auto* PC=CastChecked<APlayerController>(Player->GetController());PC->SetViewTarget(Camera.Get());PC->PlayerCameraManager->UpdateCamera(0);}
  if(Phase==0)
  {
   FString TSV;const FString Dir=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_REPAIR_OUT"));
   if(!FFileHelper::LoadFileToString(TSV,*(Dir/TEXT("AttackCases.tsv")))){Test->AddError(TEXT("Full frozen198 attack cases required"));return Finish();}
   TArray<FString> Lines;TSV.ParseIntoArrayLines(Lines);for(const FString& Line:Lines){TArray<FString> C;Line.ParseIntoArray(C,TEXT("\t"));if(C.Num()==2)Cases.Add({C[0],C[1]});}
   if(!Test->TestEqual(TEXT("Every saved attack asset covered"),Cases.Num(),198))return Finish();
   for(TActorIterator<AKZMonster> It(W);It;++It){OriginalVisibility.Add(*It,It->IsHidden());It->SetActorHiddenInGame(true);It->GetAbilitySystemComponent()->CancelAllAbilities();if(auto* AI=Cast<AAIController>(It->GetController()))if(AI->BrainComponent)AI->BrainComponent->PauseLogic(TEXT("Owned visual QA"));}
   Player->GetAbilitySystemComponent()->CancelAllAbilities();Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorHiddenInGame(true);
   APlayerController* PC=CastChecked<APlayerController>(Player->GetController());SavedView=PC->GetViewTarget();
   const FVector Forward=Player->GetActorForwardVector(),Origin=Player->GetActorLocation();
   Camera=W->SpawnActor<ACameraActor>(Origin-Forward*300+FVector(0,0,160),(Origin+Forward*350+FVector(0,0,50)-(Origin-Forward*300+FVector(0,0,160))).Rotation());
   Camera->GetCameraComponent()->SetFieldOfView(65);PC->SetViewTarget(Camera.Get());
   for(const TCHAR* F:Families)
   {
    FString Path=FString(TEXT("/Game/Bluprints/Monsters/BP_Monster_"))+F+TEXT(".BP_Monster_")+F+TEXT("_C");UClass* C=LoadClass<AKZMonster>(nullptr,*Path);if(!C)return Finish();
    FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* M=W->SpawnActor<AKZMonster>(C,Origin+Forward*350,FRotator::ZeroRotator,Params);if(!M)return Finish();
    if(auto* AI=Cast<AKZMonsterAIController>(M->GetController())){AI->GetStateTreeComponent()->StopLogic(TEXT("Owned full occurrence QA"));AI->StopMovement();}
    M->GetAbilitySystemComponent()->CancelAllAbilities();M->GetCharacterMovement()->DisableMovement();M->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FVector L=M->GetActorLocation();L.Z=Origin.Z-Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+M->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();M->SetActorLocation(L);M->SetActorRotation(Player->GetActorRotation());
    M->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;M->GetMesh()->bSuppressNotifyEventDispatch=true;M->GetMesh()->SetComponentTickEnabled(false);M->GetController()->SetActorTickEnabled(false);M->SetActorHiddenInGame(true);Monsters.Add(M);ByFamily.Add(F,M);
    Test->TestTrue(TEXT("Animated chest socket is saved for every family"),M->GetMesh()->DoesSocketExist(M->CombatReticleSocket));Test->TestNotNull(TEXT("Blood assigned to actual Monster"),M->HitBloodEffect.Get());Test->TestNotNull(TEXT("Ash assigned to actual Monster"),M->DeathAshEffect.Get());
   }
   Phase=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_REPAIR_QUICK_VISUAL"))==TEXT("1")?4:1;return false;
  }
  if(Phase==1)
  {
   if(CaseIndex>=Cases.Num()){Phase=4;return false;}
   const FCase& C=Cases[CaseIndex];Current=ByFamily.FindChecked(C.Family);Sequence=LoadObject<UAnimSequence>(nullptr,*C.Asset);if(!Sequence.IsValid()){Test->AddError(C.Asset);return Finish();}
   for(auto& M:Monsters)if(M.IsValid())M->SetActorHiddenInGame(M!=Current);
   const FVector Centre=Current->GetActorLocation();const float Half=Current->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   const FVector View=Centre+Player->GetActorForwardVector()*(Half*2/FMath::Tan(FMath::DegreesToRadians(32.5f)))+FVector(0,0,Half*.2f);
   Camera->SetActorLocationAndRotation(View,(Centre-View).Rotation());CastChecked<APlayerController>(Player->GetController())->SetViewTarget(Camera.Get());
   Current->GetMesh()->PlayAnimation(Sequence.Get(),false);Current->GetMesh()->GetSingleNodeInstance()->SetPlaying(false);EventIndex=0;Phase=2;return false;
  }
  if(Phase==2)
  {
   auto* M=Current.Get();auto* Seq=Sequence.Get();M->ClearMonsterVisuals();
   while(EventIndex<Seq->Notifies.Num()&&!Cast<UKZAnimNotifyState_MonsterVisual>(Seq->Notifies[EventIndex].NotifyStateClass.Get()))++EventIndex;
   if(EventIndex>=Seq->Notifies.Num()){++CaseIndex;Phase=1;return false;}
   const FAnimNotifyEvent& E=Seq->Notifies[EventIndex];State=Cast<UKZAnimNotifyState_MonsterVisual>(E.NotifyStateClass.Get());
   if(!State.IsValid()||State->bAnimationContextBoundary){++EventIndex;return false;}
   ++Occurrences;
   if(!State->Effect){++EventIndex;return false;} // Explicit blood decal suppression / material-only states.
   auto* Mesh=M->GetMesh();auto* Single=Mesh->GetSingleNodeInstance();
   const float Before=FMath::Max(0.f,E.GetTriggerTime()-.2f);Single->SetPositionWithPreviousTime(Before,Before,false);Mesh->TickAnimation(0,false);Mesh->RefreshBoneTransforms();M->ClearMonsterVisuals();
   FAnimNotifyEventReference Ref(&E,Seq);Ref.SetNotifyInstanceID(1000000+Occurrences);M->BeginMonsterVisual(*State.Get(),Mesh,Ref);
   Test->TestFalse(TEXT("No attack particle is activated from the stale pose"),HasEvent(M,State->Effect->EventId));
   SampleTime=FMath::Clamp(E.GetTriggerTime()+FMath::Min(.04f,E.GetDuration()*.5f),0.f,Seq->GetPlayLength());
   Single->SetPositionWithPreviousTime(SampleTime,SampleTime,false);Mesh->TickAnimation(0,false);Mesh->RefreshBoneTransforms();Start=Now;Phase=3;return false;
  }
  if(Phase==3)
  {
   if(Now-Start<.05f)return false;
   AKZMonster* M=Current.Get();const auto* FX=State->Effect.Get();auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("asset"),Cases[CaseIndex].Asset);Row->SetStringField(TEXT("event"),FX->EventId.ToString());Row->SetStringField(TEXT("socket"),FX->SourceSocket.ToString());Row->SetNumberField(TEXT("sample_time"),SampleTime);
   int32 Count=0;
   auto* PC=CastChecked<APlayerController>(Player->GetController());Test->TestTrue(TEXT("Review camera is this player's actual view target"),PC->GetViewTarget()==Camera.Get());Row->SetStringField(TEXT("camera_world"),PC->PlayerCameraManager->GetCameraLocation().ToString());Row->SetStringField(TEXT("requested_camera_world"),Camera->GetActorLocation().ToString());
   for(TObjectIterator<USceneComponent> It;It;++It)if(USceneComponent* C=*It;C->GetWorld()==W&&C->IsRegistered()&&C->IsActive()&&C->ComponentHasTag(M->GetFName())&&C->ComponentHasTag(FX->EventId)&&(!Cast<UParticleSystemComponent>(C)||!CastChecked<UParticleSystemComponent>(C)->bWasDeactivated))
   {
    ++Count;Test->TestFalse(TEXT("Every source attack component has a finite transform"),C->GetComponentTransform().ContainsNaN());
    if(auto* PSC=Cast<UParticleSystemComponent>(C)){const bool bSourceResource=FX->SurfaceRoutes.IsEmpty()?PSC->Template==FX->ParticleTemplate:FX->SurfaceRoutes.ContainsByPredicate([PSC](const FKZCombatEffectSurfaceRoute& R){return R.ParticleTemplate==PSC->Template;});Test->TestTrue(*FString::Printf(TEXT("Original particle resource identity %s -> %s"),*FX->EventId.ToString(),*GetPathNameSafe(PSC->Template)),bSourceResource);}
    if(!FX->bUseSourceCorrection&&!FX->bSpawnOnFloor&&!FX->bDeepSnowTrail&&FX->RelativeLocationRandomMin==FX->RelativeLocationRandomMax&&FX->RelativeRotationRandomMin==FX->RelativeRotationRandomMax)
    {
     FTransform Anchor=M->GetMesh()->GetSocketTransform(FX->SourceSocket,RTS_World);Anchor.SetScale3D(FVector::OneVector);
     FTransform Expected=FTransform(FX->RelativeRotation+FX->RelativeRotationRandomMin,FX->RelativeLocation+FX->RelativeLocationRandomMin)*Anchor;
     const double CM=FVector::Distance(Expected.GetLocation(),C->GetComponentLocation());const double Deg=FMath::RadiansToDegrees(Expected.GetRotation().AngularDistance(C->GetComponentQuat()));Row->SetNumberField(TEXT("offset_error_cm"),CM);Row->SetNumberField(TEXT("angle_error_deg"),Deg);
     Test->TestTrue(TEXT("Final evaluated source socket position and orientation"),CM<.1&&Deg<.1);
    }
   }
   if(FX->ParticleTemplate&&!FX->bWinterOnly&&!FX->bOnAttackSuccessed&&!FX->bSpawnOnFloor&&FX->SurfaceRoutes.IsEmpty())Test->TestTrue(TEXT("Every unconditional attack source particle activates"),Count>0);
   Row->SetNumberField(TEXT("components"),Count);Rows.Add(MakeShared<FJsonValueObject>(Row));
   const FString CaptureKey=Cases[CaseIndex].Asset;
   if(Count&& !Captured.Contains(CaptureKey)){Captured.Add(CaptureKey);Capture(TEXT("Attack_")+Cases[CaseIndex].Family+TEXT("_")+Sequence->GetName());}
   ++EventIndex;Phase=2;return false;
  }
  if(Phase==4)
  {
   if(DeathIndex>=Monsters.Num())return Finish();Current=Monsters[DeathIndex];auto* M=Current.Get();
   for(auto& Other:Monsters)if(Other.IsValid())Other->SetActorHiddenInGame(Other!=Current);
   const FVector Centre=M->GetActorLocation();const float Half=M->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();const FVector View=Centre+Player->GetActorForwardVector()*(Half*2/FMath::Tan(FMath::DegreesToRadians(32.5f)));Camera->SetActorLocationAndRotation(View,(Centre-View).Rotation());
   M->GetMesh()->bSuppressNotifyEventDispatch=false;M->GetMesh()->SetComponentTickEnabled(true);CastChecked<APlayerController>(Player->GetController())->SetViewTarget(Camera.Get());
   M->ClearMonsterVisuals();M->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);M->GetMesh()->SetAnimInstanceClass(M->GetClass()->GetDefaultObject<AKZMonster>()->GetMesh()->GetAnimClass());
   M->PlayHitBlood(Player.Get(),M->GetMesh()->GetSocketLocation(M->CombatReticleSocket));Start=Now;Phase=6;return false;
  }
  if(Phase==6)
  {
   if(Now-Start<.12f)return false;Capture(TEXT("Blood_")+FString(Families[DeathIndex]));auto* M=Current.Get();
   Test->TestTrue(TEXT("Blood emits actual live physical particles"),ParticleCount(M,TEXT("KZMonsterHitBlood"))>0);
   M->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),0.f);M->FinishDeathPresentation(DeathIndex%2==0);Start=Now;DeathSampled=false;LateDeathSampled=false;Phase=5;return false;
  }
  if(Phase==5)
  {
   auto* M=Current.Get();if(!M){Test->TestTrue(TEXT("Death emitted a progressive material phase before destruction"),DeathSampled);++DeathIndex;Phase=4;return false;}
   TInlineComponentArray<UMeshComponent*> Meshes(M);float Progress=0;int32 Supported=0;
   for(auto* Part:Meshes)for(int32 I=0;I<Part->GetNumMaterials();++I)if(auto* MID=Cast<UMaterialInstanceDynamic>(Part->GetMaterial(I))){float V=0;if(MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("KZDeathProgress")),V)){++Supported;Progress=FMath::Max(Progress,V);}}
   if(Progress>.35f&&!DeathSampled){DeathSampled=true;Test->TestTrue(TEXT("Every corpse has dissolving body/weapon material consumers"),Supported>0);Test->TestTrue(TEXT("Black ash emits actual live particles"),ParticleCount(M,TEXT("KZMonsterDeathAsh"))>0);Capture(TEXT("DeathAsh_")+FString(Families[DeathIndex]));}
   if(Progress>.75f&&!LateDeathSampled){LateDeathSampled=true;Capture(TEXT("LateDeathAsh_")+FString(Families[DeathIndex]));}
   if(Now-Start>30.f){Test->AddError(TEXT("Dead monster did not dissolve and despawn"));return Finish();}return false;
  }
  return false;
 }
private:
 int32 ParticleCount(AKZMonster* M,FName Tag){int32 Count=0;for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==M->GetWorld()&&It->ComponentHasTag(M->GetFName())&&It->ComponentHasTag(Tag))for(auto* E:It->EmitterInstances)if(E)Count+=E->ActiveParticles;Test->AddInfo(FString::Printf(TEXT("Actual presentation Actor=%s effect=%s liveParticles=%d"),*M->GetName(),*Tag.ToString(),Count));return Count;}
 bool HasEvent(AKZMonster* M,FName ID){for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==M->GetWorld()&&It->ComponentHasTag(M->GetFName())&&It->ComponentHasTag(ID)&&It->IsActive()&&!It->bWasDeactivated)return true;return false;}
 void Capture(const FString& N)
 {
  auto* VC=CastChecked<APlayerController>(Player->GetController())->GetLocalPlayer()->ViewportClient.Get();FViewport* V=VC?VC->Viewport:nullptr;
  TArray<FColor> Pixels;if(!V||!V->ReadPixels(Pixels)){Test->AddError(TEXT("Actual PIE render target readback failed"));return;}
  const FIntPoint Size=V->GetSizeXY();TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Size.X,Size.Y,Pixels,PNG);
  FFileHelper::SaveArrayToFile(PNG,*FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_REPAIR_OUT")),N+TEXT(".png")));
 }
 bool Finish(){auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("status"),Test->HasAnyErrors()?TEXT("failed"):TEXT("passed"));R->SetNumberField(TEXT("attack_assets"),CaseIndex);R->SetNumberField(TEXT("source_occurrences"),Occurrences);R->SetNumberField(TEXT("death_families"),DeathIndex);R->SetArrayField(TEXT("attack_events"),Rows);FString Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_REPAIR_OUT"))/TEXT("Runtime.json")));Cleanup();return true;}
 void Cleanup(){if(Cleaned)return;Cleaned=true;for(auto& M:Monsters)if(M.IsValid())M->Destroy();if(Player.IsValid()){Player->SetActorHiddenInGame(false);if(auto* PC=Cast<APlayerController>(Player->GetController()))PC->SetViewTarget(SavedView.Get());}if(Camera.IsValid())Camera->Destroy();for(const auto& P:OriginalVisibility)if(P.Key.IsValid()){P.Key->SetActorHiddenInGame(P.Value);if(auto* AI=Cast<AAIController>(P.Key->GetController()))if(AI->BrainComponent)AI->BrainComponent->ResumeLogic(TEXT("Owned visual QA complete"));}}
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;double Deadline;TArray<FCase> Cases;TArray<TWeakObjectPtr<AKZMonster>> Monsters;TMap<FString,TWeakObjectPtr<AKZMonster>> ByFamily;TMap<TWeakObjectPtr<AKZMonster>,bool> OriginalVisibility;TWeakObjectPtr<AKZMonster> Current;TWeakObjectPtr<UAnimSequence> Sequence;TWeakObjectPtr<UKZAnimNotifyState_MonsterVisual> State;TWeakObjectPtr<ACameraActor> Camera;TWeakObjectPtr<AActor> SavedView;TSet<FString> Captured;TArray<TSharedPtr<FJsonValue>> Rows;int32 Phase=0,CaseIndex=0,EventIndex=0,Occurrences=0,DeathIndex=0;float Start=0,SampleTime=0;bool DeathSampled=false,LateDeathSampled=false,Cleaned=false;
};
class FWait:public IAutomationLatentCommand
{
public:explicit FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60){}
 bool Update()override{if(!Requested){Requested=true;auto* S=GetMutableDefault<ULevelEditorPlaySettings>();S->NewWindowWidth=1600;S->NewWindowHeight=900;FRequestPlaySessionParams P;P.EditorPlaySettings=S;GEditor->RequestPlaySession(P);}for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Actual player PIE missing"));return true;}return false;}
private:FAutomationTestBase* Test;double Deadline;bool Requested=false;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterRepairPIE,"Khazan.MonsterRepair.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterRepairPIE::RunTest(const FString&){const auto* D=LoadObject<UKZCharacterDefinitionData>(nullptr,TEXT("/Game/Data/Character/DA_CharacterDefinition_Player.DA_CharacterDefinition_Player"));if(!D)return false;int32 Blank=0;for(const auto& G:D->GetInitialAbilityGrants())if(!G.AbilityClass&&G.InputTag==FGameplayTag::EmptyTag)++Blank;if(Blank)AddExpectedError(TEXT("BP_Player_C_0 has an InitialAbilityGrant with no AbilityClass in DA_CharacterDefinition_Player (InputTag: None)."),EAutomationExpectedErrorFlags::Contains,Blank,false);FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZMonsterRepairQA::FWait>(this));return true;}
#endif
