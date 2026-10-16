#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraSpriteRendererProperties.h"
#include "Misc/PackageName.h"
#include "UObject/SavePackage.h"
#include "Ability/PlayerAbility/KZFallAbility.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "AI/KZMonsterAIController.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Character/Component/KZLockOnComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Particles/ParticleSystemComponent.h"
#include "ParticleEmitterInstances.h"
#include "UObject/UObjectIterator.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EnhancedPlayerInput.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "ImageUtils.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HighResScreenshot.h"
#include "Components/StateTreeAIComponent.h"
#include "Engine/Engine.h"
#include "UnrealClient.h"
#include "KZGameplayTags.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

namespace KZCombatPresentationQA
{
class FRun final : public IAutomationLatentCommand
{
public:
 FRun(FAutomationTestBase* InTest, AKZPlayer* InPlayer):Test(InTest),Player(InPlayer),Deadline(FPlatformTime::Seconds()+600.){}
 bool Update() override
 {
  if (!Player.IsValid() || FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Combat presentation fixture timed out"));return Finish(); }
  AKZPlayer* P=Player.Get(); UWorld* W=P->GetWorld();const float Now=W->GetTimeSeconds();
  auto* ASC=CastChecked<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent());
  if (Camera.IsValid()) {FVector Focus=Victim.IsValid()?(P->GetActorLocation()+Victim->GetActorLocation())*.5:P->GetActorLocation();FVector View=Focus+(Victim.IsValid()?FVector(0,-750,250):FVector(450,-450,200));Camera->SetActorLocation(View);Camera->SetActorRotation((Focus-View).Rotation());auto* PC=P->GetController<APlayerController>();PC->SetViewTarget(Camera.Get());PC->PlayerCameraManager->UpdateCamera(0);}
  if (Stage==0)
  {
   if (!P->GetCharacterMovement()->IsMovingOnGround())return false;
   for (TActorIterator<AKZMonster> It(W);It;++It) if(auto* AI=Cast<AKZMonsterAIController>(It->GetController())) { Paused.Add(AI);AI->GetStateTreeComponent()->StopLogic(TEXT("Owned presentation QA")); }
   Camera=W->SpawnActor<ACameraActor>();P->GetController<APlayerController>()->SetViewTarget(Camera.Get());Stage=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_COMBAT_FINISH_LETHAL"))==TEXT("1")?3:1;
  }
  if (Stage==1)
  {
   P->HandleInputMove(FVector2D(1,0),FRotator::ZeroRotator);
   if (!P->GetCharacterMovement()->IsFalling())return false;
   P->HandleInputMoveReleased();P->GetController<APlayerController>()->InputKey(FInputKeyParams(EKeys::Gamepad_FaceButton_Left,IE_Pressed,1.0,true));Start=Now;Stage=2;
  }
  if (Stage==2)
  {
   if (!ReleasedX && Now-Start>.1f) {P->GetController<APlayerController>()->InputKey(FInputKeyParams(EKeys::Gamepad_FaceButton_Left,IE_Released,0.0,true));ReleasedX=true;}
   UKZFallAbility* Fall=nullptr;for (const auto& S:ASC->GetActivatableAbilities())if(S.IsActive())if(auto* F=Cast<UKZFallAbility>(S.GetPrimaryInstance()))if(F->IsPlungeAttack())Fall=F;
   if (Fall && Fall->GetCurrentNodeId()==TEXT("Land"))
   {
    if (LandTime<0) {LandTime=Now;FallMontage=Fall->GetCurrentMontage();}
   for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==W&&It->ComponentHasTag(TEXT("KZExtra_PlungeGround")))for(auto* Emitter:It->EmitterInstances)if(Emitter&&Emitter->ActiveParticles>0)GroundDebrisSeen=true;
    if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_SLAM_DISTORT_ONLY"))==TEXT("1"))
    {
     for(TObjectIterator<UNiagaraComponent> It;It;++It)
      if(It->GetWorld()==W&&It->ComponentHasTag(TEXT("KZExtra_PlungeDistort")))
      {
       if(!SeenDistort.Contains(*It))
       {
        SeenDistort.Add(*It);Test->TestNull(TEXT("Landing distortion stays in world space"),It->GetAttachParent());
        Test->TestTrue(TEXT("Landing distortion uses requested floor variant"),It->GetAsset()&&It->GetAsset()->GetName()==TEXT("NS_Player_Plunge_ParringDistort"));
        FHitResult Floor;const FVector Position=It->GetComponentLocation();FCollisionQueryParams Query(SCENE_QUERY_STAT(KZSlamDistortQA),true,P);
        const auto* CMC=P->GetCharacterMovement();const double Range=P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+CMC->MaxStepHeight;
        const bool Hit=W->LineTraceSingleByChannel(Floor,Position+FVector::UpVector*Range,Position-FVector::UpVector*Range,ECC_Visibility,Query);
        Test->TestTrue(TEXT("Landing distortion originates on the real floor"),Hit&&FMath::Abs(Position.Z-Floor.ImpactPoint.Z)<1.0);
        Test->TestTrue(TEXT("Distortion local facing lies along the floor normal"),Hit&&FVector::DotProduct(It->GetUpVector(),Floor.ImpactNormal)>.999);
        Test->TestTrue(TEXT("Floor distortion is under the landing player"),FVector::Dist2D(Position,P->GetActorLocation())<1.0);
       }
      }
    }
    if (Now>=NextSample)
    {
     const float Position=P->GetMesh()->GetAnimInstance()->Montage_GetPosition(FallMontage.Get());
     auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("time"),Now-LandTime);Row->SetNumberField(TEXT("montage_position"),Position);FallSamples.Add(MakeShared<FJsonValueObject>(Row));
     Capture(Output()+FString::Printf(TEXT("/Fall_%02d.png"),FallSamples.Num()));NextSample=Now+.12f;
    }
    return false;
   }
   if (LandTime<0 || !P->GetCharacterMovement()->IsMovingOnGround())return false;
   Test->TestTrue(TEXT("Plunge landing completes naturally through the actual landed section"),FallSamples.Num()>3);
   Test->TestTrue(TEXT("Actual plunge emits ground debris even beside the ledge wall"),GroundDebrisSeen);
   if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_SLAM_DISTORT_ONLY"))==TEXT("1"))
   {
    Test->TestEqual(TEXT("One distortion instance is emitted at actual plunge landing"),SeenDistort.Num(),1);
    for(auto Component:SeenDistort)if(Component.IsValid())Test->TestFalse(TEXT("End marker stops distortion emission"),Component->IsActive());
    return Finish();
   }
   if (FallMontage.IsValid())
   {
    const FAnimSegment& Last=FallMontage->SlotAnimTracks[0].AnimTrack.AnimSegments.Last();
    Test->TestTrue(TEXT("Landed segment includes the baked sequence's final blade/recovery pose"),FMath::IsNearlyEqual(Last.AnimEndTime,Last.GetAnimReference()->GetPlayLength(),.001f));
    Test->TestEqual(TEXT("Baked playback uses one rate conversion"),Last.AnimPlayRate,1.f);
   }
   P->HandleInputMoveReleased();Stage=3;Start=Now;
  }
  if (Stage==3)
  {
   if (Case>=12)return Finish();
   static const TCHAR* Families[]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
   Family=Families[Case/2];const bool Back=Case%2!=0;
   UClass* Class=LoadClass<AKZMonster>(nullptr,*FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),*Family,*Family));
   if (!Class) {Test->AddError(TEXT("Missing six-family paired fixture BP"));return Finish();}
   auto* CDO=CastChecked<AKZMonster>(Class->GetDefaultObject());float Height=CDO->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   Victim=W->SpawnActor<AKZMonster>(Class,FVector(-2000,6500,Height),FRotator::ZeroRotator);
   if (!Victim.IsValid())return Finish();
   if (auto* AI=Cast<AKZMonsterAIController>(Victim->GetController()))AI->GetStateTreeComponent()->StopLogic(TEXT("Owned paired fixture"));
   Height=Victim->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   Victim->SetActorLocation(FVector(-2000,6500,Height),false,nullptr,ETeleportType::TeleportPhysics);
   CapsuleSpacing=P->GetCapsuleComponent()->GetScaledCapsuleRadius()+Victim->GetCapsuleComponent()->GetScaledCapsuleRadius();
   const FVector Destination=Victim->GetActorLocation()+FVector((Back?-1:1)*(CapsuleSpacing+60.f),0,P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Height);
   P->GetCharacterMovement()->StopMovementImmediately();P->SetActorLocationAndRotation(Destination,Back?FRotator::ZeroRotator:FRotator(0,180,0),false,nullptr,ETeleportType::TeleportPhysics);
   P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
   const bool Lethal=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_COMBAT_FINISH_LETHAL"))==TEXT("1");
   ExpectedVictimPose.Reset();ExcludedContacts.Reset();bDeathMontageSeen=false;
   LastDeathPose.Reset();DeathStartedAt=-1.f;NextDeathCapture=0.f;DeathFrames=0;MaxDeathStepSpeed=0.f;LastDeathSampleAt=0.f;
   for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==W&&It->ComponentHasTag(TEXT("KZCombatEffect")))ExcludedContacts.Add(*It);
   if(Lethal)
   {
    UAnimMontage* EndMontage=Victim->GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage;
    if(!Test->TestNotNull(TEXT("Lethal Brutal victim has an authored death montage"),EndMontage))return Finish();
    const auto& Last=EndMontage->SlotAnimTracks[0].AnimTrack.AnimSegments.Last();auto* Pose=NewObject<USkeletalMeshComponent>(Victim.Get());Pose->SetSkeletalMeshAsset(Victim->GetMesh()->GetSkeletalMeshAsset());Pose->RegisterComponentWithWorld(W);Pose->SetWorldTransform(Victim->GetMesh()->GetComponentTransform());Pose->bSuppressNotifyEventDispatch=true;Pose->SetComponentTickEnabled(false);Pose->PlayAnimation(Last.GetAnimReference(),false);Pose->GetSingleNodeInstance()->SetPlaying(false);Pose->GetSingleNodeInstance()->SetPositionWithPreviousTime(Last.AnimEndTime,Last.AnimEndTime,false);Pose->TickAnimation(0,false);Pose->RefreshBoneTransforms();for(const FName Bone:PoseBones())ExpectedVictimPose.Add(Pose->GetSocketTransform(Bone,RTS_Component).GetLocation());Pose->DestroyComponent();
   }
   auto* TargetASC=Victim->GetAbilitySystemComponent();TargetASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),1000.f);TargetASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),Lethal?1.f:1000.f);TargetASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),0.f);
   Start=Now;Stage=4;return false;
  }
  if (Stage==4)
  {
   if (Now-Start<.2f)return false;
   auto* Exhaustion=Victim->GetActiveExhaustionAbility();if(!Exhaustion || !Exhaustion->IsAvailableForBrutalAttack()) {Test->AddError(TEXT("Fixture did not exhaust"));return Finish();}
   // The victim's exhaustion Start can move its capsule before B. Establish the
   // test's front/back approach relative to its live pose, not its spawn point.
   FVector Offset=Victim->GetActorForwardVector()*((Case%2?-1.f:1.f)*(CapsuleSpacing+60.f));
   Offset.Z=P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Victim->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   P->SetActorLocationAndRotation(Victim->GetActorLocation()+Offset,((Case%2)?Victim->GetActorForwardVector():-Victim->GetActorForwardVector()).Rotation(),false,nullptr,ETeleportType::TeleportPhysics);
   P->GetCharacterMovement()->StopMovementImmediately();
   PlayerRootMode=P->GetMesh()->GetAnimInstance()->RootMotionMode;
   if(auto* Lock=P->FindComponentByClass<UKZLockOnComponent>())
   {
    Lock->StopLockOn();Camera->SetActorLocation(P->GetActorLocation()-P->GetActorForwardVector()*750+FVector(0,0,250));Camera->SetActorRotation((Victim->GetLockOnTargetPoint()->GetComponentLocation()-Camera->GetActorLocation()).Rotation());P->GetController<APlayerController>()->PlayerCameraManager->UpdateCamera(0);Lock->ToggleLockOn();Test->TestEqual(TEXT("Real lock-on selects this exhausted victim before B"),Lock->GetCurrentTarget(),Victim.Get());
   }
   VictimRootMode=Victim->GetMesh()->GetAnimInstance()->RootMotionMode;
   P->GetController<APlayerController>()->InputKey(FInputKeyParams(EKeys::Gamepad_FaceButton_Right,IE_Pressed,1.0,true));
   Start=Now;NextSample=Now;MinDistance=DBL_MAX;PairSamples.Reset();
   const auto& DeathSettings=Victim->GetCharacterDefinition()->GetMonsterStaminaSettings();
   CaseDeadline=Now+DeathSettings.BrutalFrontPlayerMontage->GetPlayLength()+DeathSettings.BrutalBackPlayerMontage->GetPlayLength()+
    DeathSettings.BrutalFrontVictimMontage->GetPlayLength()+DeathSettings.BrutalBackVictimMontage->GetPlayLength()+
    DeathSettings.DeathPresentationMontage->GetPlayLength()+5.f;
   Stage=5;return false;
  }
  if (Stage==5)
  {
   if(Now>CaseDeadline){Test->AddError(TEXT("Brutal victim did not finish its authored death montage"));return Finish();}
   if(!ExpectedVictimPose.IsEmpty() && Victim.IsValid())
    if(UAnimInstance* VictimAnim=Victim->GetMesh()->GetAnimInstance())
    {
     const bool DeathPlaying=VictimAnim->Montage_IsPlaying(Victim->GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage.Get());
     bDeathMontageSeen|=DeathPlaying;
     if(DeathPlaying && DeathStartedAt<0.f)DeathStartedAt=Now;
     TArray<FVector> Pose;for(const FName Bone:PoseBones())Pose.Add(Victim->GetMesh()->GetSocketLocation(Bone));
     if(DeathPlaying && Now-DeathStartedAt<=.4f)
     {
      ++DeathFrames;
      if(LastDeathPose.Num()==Pose.Num() && Now>LastDeathSampleAt)
       for(int32 Bone=0;Bone<Pose.Num();++Bone)MaxDeathStepSpeed=FMath::Max(MaxDeathStepSpeed,float(FVector::Dist(Pose[Bone],LastDeathPose[Bone])/(Now-LastDeathSampleAt)));
      if(Now-DeathStartedAt>=NextDeathCapture)
      {Capture(Output()+FString::Printf(TEXT("/DeathJoin_%02d_%02d.png"),Case,FMath::RoundToInt(NextDeathCapture/.08f)));NextDeathCapture+=.08f;}
     }
     LastDeathPose=MoveTemp(Pose);LastDeathSampleAt=Now;
    }
   if (Now-Start>.1f && !ReleasedB) {P->GetController<APlayerController>()->InputKey(FInputKeyParams(EKeys::Gamepad_FaceButton_Right,IE_Released,0.0,true));ReleasedB=true;}
   bool Active=false;for(const auto& S:ASC->GetActivatableAbilities())if(Cast<UKZBrutalAttackAbility>(S.Ability))Active|=S.IsActive();
   if (Active)
   {
    double Distance=FVector::Dist2D(P->GetActorLocation(),Victim->GetActorLocation());if(Now-Start>.5f)MinDistance=FMath::Min(MinDistance,Distance);
    for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==W&&It->IsRegistered()&&!ExcludedContacts.Contains(*It)&&It->Template&&It->ComponentHasTag(TEXT("KZCombatEffect"))&&It->Template->GetName().StartsWith(TEXT("PP_AtkEx_Grapple")))
    {
     const FVector Chest=(P->GetActorLocation()+Victim->GetActorLocation())*.5;
     if(!SeenContacts.Contains(*It)){SeenContacts.Add(*It);ContactOffset=FMath::Max(ContactOffset,FVector::Dist2D(Chest,It->GetComponentLocation()));}
    }
    if(Now>=NextSample)
    {
     auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("time"),Now-Start);R->SetNumberField(TEXT("spacing_cm"),Distance);R->SetNumberField(TEXT("player_yaw"),P->GetActorRotation().Yaw);R->SetNumberField(TEXT("victim_yaw"),Victim->GetActorRotation().Yaw);
     R->SetStringField(TEXT("player"),P->GetActorLocation().ToString());R->SetStringField(TEXT("victim"),Victim->GetActorLocation().ToString());PairSamples.Add(MakeShared<FJsonValueObject>(R));
     Capture(Output()+FString::Printf(TEXT("/Pair_%02d_%03d.png"),Case,PairSamples.Num()));NextSample=Now+.25f;
    }
    return false;
   }
   if (Now-Start<.25f)return false;
   if (auto* Exhaustion=Victim->GetActiveExhaustionAbility();Exhaustion && Exhaustion->HasBrutalPartner())return false;
   if(!ExpectedVictimPose.IsEmpty() && !Victim->GetMesh()->bPauseAnims)return false;
   Test->TestEqual(TEXT("Completed attacker restores its actual previous root motion mode"),P->GetMesh()->GetAnimInstance()->RootMotionMode.GetValue(),PlayerRootMode);
   Test->TestEqual(TEXT("Completed victim restores its actual previous root motion mode"),Victim->GetMesh()->GetAnimInstance()->RootMotionMode.GetValue(),VictimRootMode);
   Test->TestTrue(TEXT("Actual B starts and runs the paired montage"),PairSamples.Num()>2);
   Test->TestTrue(*FString::Printf(TEXT("%s %s capsules do not penetrate after alignment (min %.2f / required %.2f cm)"),*Family,Case%2?TEXT("Back"):TEXT("Front"),MinDistance,CapsuleSpacing),!PairSamples.IsEmpty() && MinDistance<DBL_MAX && MinDistance>=CapsuleSpacing-2.f);
   auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Family);Row->SetBoolField(TEXT("back"),Case%2!=0);Row->SetNumberField(TEXT("required_spacing_cm"),CapsuleSpacing);Row->SetNumberField(TEXT("minimum_spacing_cm"),MinDistance);Row->SetArrayField(TEXT("samples"),PairSamples);Pairs.Add(MakeShared<FJsonValueObject>(Row));
   Row->SetNumberField(TEXT("previous_player_root_mode"),int32(PlayerRootMode));Row->SetNumberField(TEXT("restored_player_root_mode"),int32(P->GetMesh()->GetAnimInstance()->RootMotionMode.GetValue()));
   Row->SetNumberField(TEXT("contact_bursts"),SeenContacts.Num());Row->SetNumberField(TEXT("first_contact_offset_cm"),ContactOffset);
   Test->TestTrue(TEXT("Actual front/back contact bursts remain between the live pair"),SeenContacts.Num()>=2&&ContactOffset<2.);
   if(!ExpectedVictimPose.IsEmpty())
   {
    Test->TestTrue(TEXT("Lethal pair reaches HP0"),Victim->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())<=0.f);
    Test->TestTrue(TEXT("Lethal pair plays the victim's authored death montage"),bDeathMontageSeen);
    Test->TestTrue(TEXT("Death transition has consecutive evaluated poses"),DeathFrames>1&&FMath::IsFinite(MaxDeathStepSpeed));
    Row->SetNumberField(TEXT("death_transition_frames"),DeathFrames);Row->SetNumberField(TEXT("death_transition_max_bone_speed_cm_s"),MaxDeathStepSpeed);
    Test->TestTrue(TEXT("Lethal pair freezes corpse"),Victim->GetMesh()->bPauseAnims);double Error=0;int32 Index=0;for(const FName Bone:PoseBones())Error=FMath::Max(Error,FVector::Distance(ExpectedVictimPose[Index++],Victim->GetMesh()->GetSocketTransform(Bone,RTS_Component).GetLocation()));
    Row->SetNumberField(TEXT("death_pose_error_model_cm"),Error);Test->TestTrue(*FString::Printf(TEXT("Brutal corpse holds the authored death terminal pose %s error=%g"),*Family,Error),Error<1.);
    Capture(Output()+FString::Printf(TEXT("/Death_%02d.png"),Case));
   }
   SeenContacts.Reset();ContactOffset=0;
   Victim->Destroy();Victim.Reset();ReleasedB=false;++Case;Stage=3;return false;
  }
  return false;
 }
 static TArray<FName> PoseBones(){return {TEXT("Bip001-Pelvis"),TEXT("Bip001-Spine2"),TEXT("Bip001-Head"),TEXT("Bip001-L-Hand"),TEXT("Bip001-R-Hand")};}
 void Capture(const FString& Path)
 {
  auto* Client=Player->GetController<APlayerController>()->GetLocalPlayer()->ViewportClient.Get();FViewport* Viewport=Client?Client->Viewport:nullptr;TArray<FColor> Pixels;
  if(!Viewport||!Viewport->ReadPixels(Pixels)){Test->AddError(TEXT("Actual game viewport screenshot readback failed"));return;}const FIntPoint Size=Viewport->GetSizeXY();TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Size.X,Size.Y,Pixels,PNG);IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveArrayToFile(PNG,*Path);
 }
 FString Output() const {const FString Run=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_CLEAN_OUTPUT"));return Run.IsEmpty()?FPaths::ProjectDir()+TEXT("Metadata/CombatPresentationFix_20261011/Native"):Run+TEXT("/Native");}
 bool Finish()
 {
  if(Victim.IsValid())Victim->Destroy();
  if(Player.IsValid()){Player->HandleInputMoveReleased();Player->GetController<APlayerController>()->SetViewTarget(Player.Get());}
  if(Camera.IsValid())Camera->Destroy();for(auto AI:Paused)if(AI.IsValid())AI->GetStateTreeComponent()->StartLogic();
  auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),!Test->HasAnyErrors());R->SetArrayField(TEXT("plunge_landing"),FallSamples);R->SetArrayField(TEXT("paired_cases"),Pairs);
  FString Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));IFileManager::Get().MakeDirectory(*Output(),true);FFileHelper::SaveStringToFile(Text,*(Output()+TEXT("/Result.json")));return true;
 }
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Victim;TWeakObjectPtr<ACameraActor> Camera;TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;
 TWeakObjectPtr<UAnimMontage> FallMontage;double Deadline,MinDistance=DBL_MAX;float Start=0,LandTime=-1,NextSample=0,CapsuleSpacing=0,CaseDeadline=0;int32 Stage=0,Case=0;bool ReleasedX=false,ReleasedB=false,bDeathMontageSeen=false;FString Family;
 ERootMotionMode::Type PlayerRootMode=ERootMotionMode::NoRootMotionExtraction,VictimRootMode=ERootMotionMode::NoRootMotionExtraction;
 TArray<TSharedPtr<FJsonValue>> FallSamples,PairSamples,Pairs;
 TArray<FVector> ExpectedVictimPose;TSet<TWeakObjectPtr<UParticleSystemComponent>> SeenContacts,ExcludedContacts;double ContactOffset=0;bool GroundDebrisSeen=false;
 TSet<TWeakObjectPtr<UNiagaraComponent>> SeenDistort;
 TArray<FVector> LastDeathPose;float DeathStartedAt=-1.f,NextDeathCapture=0.f,LastDeathSampleAt=0.f,MaxDeathStepSpeed=0.f;int32 DeathFrames=0;
};
class FWait final:public IAutomationLatentCommand
{
public:FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
 bool Update() override {for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->WorldType==EWorldType::PIE)for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->GetController()){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Owned DevMap PIE did not start"));return true;}return false;}
 FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatPresentationPIETest,"Khazan.CombatPresentation.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZCombatPresentationPIETest::RunTest(const FString&) {FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZCombatPresentationQA::FWait>(this));return true;}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZSlamDistortAuthor,"Khazan.CombatPresentation.AuthorSlamDistort",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZSlamDistortAuthor::RunTest(const FString&)
{
 if(!FPaths::ProjectDir().Contains(TEXT("Khazan_SlamDistortWork_20261012")))return false;
 auto* System=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort.NS_Player_Plunge_ParringDistort"));
 if(!TestNotNull(TEXT("Owned floor variant exists"),System))return false;
 System->Modify();const FNiagaraVariable Normal(FNiagaraTypeDefinition::GetVec3Def(),TEXT("User.KZFloorNormal"));
 System->GetExposedParameters().SetParameterValue<FVector3f>(FVector3f(0,0,1),Normal,true);
 int32 Changed=0;
 for(const auto& Handle:System->GetEmitterHandles())
 {
  const FVersionedNiagaraEmitter Instance=Handle.GetInstance();const auto* Data=Instance.GetEmitterData();if(!Data)continue;
  const FString Name=Handle.GetName().ToString();
  if(!Name.StartsWith(TEXT("M_SW_distort_Sprite"))&&Name!=TEXT("Hit003"))continue;
  for(auto* Base:Data->GetRenderers())if(auto* Renderer=Cast<UNiagaraSpriteRendererProperties>(Base))
  {
   Renderer->Modify();Renderer->FacingMode=ENiagaraSpriteFacingMode::CustomFacingVector;
   Renderer->SpriteFacingBinding.SetValue(Normal.GetName(),Instance,Renderer->SourceMode);
   TestTrue(TEXT("Floor normal binds to the component user parameter"),Renderer->SpriteFacingBinding.CanBindToHostParameterMap());++Changed;
  }
 }
 TestEqual(TEXT("Three floor sprites use the explicit normal"),Changed,3);
 System->RequestCompile(false);System->WaitForCompilationComplete();System->MarkPackageDirty();
 FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;Args.SaveFlags=SAVE_NoError;
 const FString Filename=FPackageName::LongPackageNameToFilename(System->GetOutermost()->GetName(),FPackageName::GetAssetPackageExtension());
 TestTrue(TEXT("Save owned floor variant"),UPackage::SavePackage(System->GetOutermost(),System,*Filename,Args));
 return !HasAnyErrors();
}
#endif
