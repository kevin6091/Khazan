// Isolated DEV geometry/positions below are test stimuli, not gameplay tuning.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "AI/KZMonsterAIController.h"
#include "Perception/AIPerceptionComponent.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Components/StateTreeAIComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Misc/SecureHash.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Attribute/KZAttributeSet.h"
#include "GameplayEffectExtension.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "UObject/UnrealType.h"
#include "UObject/StrongObjectPtr.h"
#include "KZGameplayTags.h"

namespace {
class FBodyRootPoses : public IAutomationLatentCommand
{
public:
 FBodyRootPoses(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P)
 {
  Directory=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_CONTACT_OUT"));FString Text;
  if(!FFileHelper::LoadFileToString(Text,*(Directory/TEXT("RootCases.tsv")))){Test->AddError(TEXT("Frozen actual-consumer RootCases.tsv missing"));return;}
  Text.ParseIntoArrayLines(Cases);
  for(const TCHAR* Family:{TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")})
  {
   const FString Path=FString(TEXT("/Game/Bluprints/Monsters/BP_Monster_"))+Family+TEXT(".BP_Monster_")+Family+TEXT("_C");UClass* C=LoadClass<AKZMonster>(nullptr,*Path);
   FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   auto* M=P->GetWorld()->SpawnActor<AKZMonster>(C,P->GetActorLocation()+FVector(20000,20000,10000),FRotator::ZeroRotator,Params);
   if(!M){Test->AddError(Path);continue;}Monsters.Add(Family,M);
   if(auto* Controller=Cast<AKZMonsterAIController>(M->GetController()))Controller->GetStateTreeComponent()->StopLogic(TEXT("Owned root pose QA"));
   M->GetAbilitySystemComponent()->CancelAllAbilities();M->GetCharacterMovement()->DisableMovement();M->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
   M->GetMesh()->bSuppressNotifyEventDispatch=true;M->GetMesh()->SetComponentTickEnabled(false);M->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
  }
 }
 ~FBodyRootPoses(){Cleanup();}
 bool Update()override
 {
  if(Index>=Cases.Num())
  {
   Test->AddInfo(FString::Printf(TEXT("BodyRootPose actual sequences=%d body=%d propSkipped=%d samples=%d"),Cases.Num(),Body,Props,Body*3));
   FString Text;auto Writer=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(Rows,Writer);FFileHelper::SaveStringToFile(Text,*(Directory/TEXT("RootPoses.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);Cleanup();return true;
  }
  TArray<FString> Fields;Cases[Index++].ParseIntoArray(Fields,TEXT("\t"));if(Fields.Num()!=2){Test->AddError(TEXT("Malformed actual root case"));return false;}
  auto* M=Monsters.FindRef(Fields[1]).Get();auto* Seq=LoadObject<UAnimSequence>(nullptr,*Fields[0]);
  if(!M||!Seq){Test->AddError(Fields[0]);return false;}auto* Mesh=M->GetMesh();
  if(Seq->GetSkeleton()!=Mesh->GetSkeletalMeshAsset()->GetSkeleton()){++Props;return false;}++Body;
  Mesh->PlayAnimation(Seq,false);auto* Single=Mesh->GetSingleNodeInstance();Single->SetPlaying(false);
  const FTransform Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton().GetRefBonePose()[0];const FTransform ActorBefore=M->GetActorTransform();
  auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("asset"),Fields[0]);Row->SetStringField(TEXT("family"),Fields[1]);double MaximumCM=0,MaximumDegrees=0;
  // Serialize the complete imported data model (all tracks, keys, curves, attributes),
  // independently of the root-lock asset option, and the existing notify data.
  FBufferArchive ModelBytes;FObjectAndNameAsStringProxyArchive ModelArchive(ModelBytes,false);
  Seq->GetDataModelInterface().GetObject()->Serialize(ModelArchive);FSHAHash ModelHash;FSHA1::HashBuffer(ModelBytes.GetData(),ModelBytes.Num(),ModelHash.Hash);
  Row->SetStringField(TEXT("data_model_sha1"),ModelHash.ToString());
  FBufferArchive NotifyBytes;FObjectAndNameAsStringProxyArchive NotifyArchive(NotifyBytes,false);
  for(const FAnimNotifyEvent& Event:Seq->Notifies)
  {
   FAnimNotifyEvent Copy=Event;FAnimNotifyEvent::StaticStruct()->SerializeItem(NotifyArchive,&Copy,nullptr);
   if(Event.Notify)Event.Notify->Serialize(NotifyArchive);if(Event.NotifyStateClass)Event.NotifyStateClass->Serialize(NotifyArchive);
  }
  FSHAHash NotifyHash;FSHA1::HashBuffer(NotifyBytes.GetData(),NotifyBytes.Num(),NotifyHash.Hash);Row->SetStringField(TEXT("notifies_sha1"),NotifyHash.ToString());
  for(float Time:{0.f,Seq->GetPlayLength()*.5f,Seq->GetPlayLength()})
  {
   Single->SetPositionWithPreviousTime(Time,Time,false);Mesh->TickAnimation(0,false);Mesh->RefreshBoneTransforms();
   const FTransform Root=Mesh->GetBoneTransform(0).GetRelativeTransform(Mesh->GetComponentTransform());
   MaximumCM=FMath::Max(MaximumCM,FVector::Distance(Root.GetLocation(),Ref.GetLocation()));MaximumDegrees=FMath::Max(MaximumDegrees,FMath::RadiansToDegrees(Root.GetRotation().GetNormalized().AngularDistance(Ref.GetRotation().GetNormalized())));
  }
  Row->SetNumberField(TEXT("root_offset_cm"),MaximumCM);Row->SetNumberField(TEXT("root_angle_degrees"),MaximumDegrees);Rows.Add(MakeShared<FJsonValueObject>(Row));
  // Existing compressed animation QA uses .01cm / 1e-4rad; imported RAW is stricter.
  Test->TestTrue(*FString::Printf(TEXT("Body root remains at the capsule model origin: %s offset=%gcm angle=%gdeg"),*Fields[0],MaximumCM,MaximumDegrees),MaximumCM<.01&&MaximumDegrees<FMath::RadiansToDegrees(1e-4));
  Test->TestTrue(TEXT("Pose QA never moves the actor to hide a root offset"),M->GetActorTransform().Equals(ActorBefore));return false;
 }
 void Cleanup(){if(Cleaned)return;Cleaned=true;for(auto& Pair:Monsters)if(Pair.Value.IsValid())Pair.Value->Destroy();}
private:
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;FString Directory;TArray<FString> Cases;TMap<FString,TWeakObjectPtr<AKZMonster>> Monsters;TArray<TSharedPtr<FJsonValue>> Rows;int32 Index=0,Body=0,Props=0;bool Cleaned=false;
};
class FVerticalPattern : public IAutomationLatentCommand
{
public:
 FVerticalPattern(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),Saved(P->GetActorTransform()),Deadline(FPlatformTime::Seconds()+120.)
 {
  for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It) if(auto* ExistingAI=Cast<AKZMonsterAIController>(It->GetController())) {ExistingAI->GetStateTreeComponent()->StopLogic(TEXT("Owned root/contact fixture"));Paused.Add(ExistingAI);}
  Player->HandleInputMoveReleased();
 }
 ~FVerticalPattern(){Cleanup();}
 bool Update() override
 {
  if(!Player.IsValid() || FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Vertical pattern fixture timeout"));Cleanup();return true;}
  UWorld* W=Player->GetWorld();const float Now=W->GetTimeSeconds();
  if(!Monster.IsValid())
  {
   UClass* C=LoadClass<AKZMonster>(nullptr,TEXT("/Game/Bluprints/Monsters/BP_Monster_Yetuga.BP_Monster_Yetuga_C"));
   FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   Monster=W->SpawnActor<AKZMonster>(C,FVector(-8000,-8000,265),FRotator::ZeroRotator,Params);
   if(!Monster.IsValid()){Test->AddError(TEXT("Real Yetuga spawn failed"));Cleanup();return true;}
   Monster->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   AI=Cast<AKZMonsterAIController>(Monster->GetController());if(!AI.IsValid()){Test->AddError(TEXT("Real AI missing"));Cleanup();return true;}
   AI->GetStateTreeComponent()->StopLogic(TEXT("Owned vertical pattern"));
   Player->SetActorLocation(Monster->GetActorLocation()+FVector(600,0,92-265));Player->GetCharacterMovement()->StopMovementImmediately();
   Start=Now;Initial=Monster->GetActorLocation();return false;
  }
  if(!Started)
  {
   if(AI->GetBattleTarget()!=Player.Get()){if(Now-Start>15){Test->AddError(TEXT("Real sight did not acquire player"));Cleanup();return true;}return false;}
   auto* ASC=Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
   UClass* C=LoadClass<UKZMonsterPatternAbility>(nullptr,TEXT("/Game/Monsters/Yetuga/Abilities/GA_Original_Armageddon.GA_Original_Armageddon_C"));
   FGameplayAbilitySpec* Spec=ASC->FindAbilitySpecFromClass(C);if(!Spec){Test->AddError(TEXT("Granted original Armageddon missing"));Cleanup();return true;}
   Ability=Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance());Handle=Spec->Handle;
   SavedDefinition=Ability->GetComboDefinition();SavedEntry=Ability->GetEntryNodeId();
   const FKZComboNode* Original=SavedDefinition->FindNode(TEXT("Armageddon_Step2"));if(!Original){Test->AddError(TEXT("Original jump node missing"));Cleanup();return true;}
   Definition.Reset(DuplicateObject<UKZComboDefinitionData>(SavedDefinition,GetTransientPackage()));
   FArrayProperty* Nodes=FindFProperty<FArrayProperty>(UKZComboDefinitionData::StaticClass(),TEXT("Nodes"));
   FKZComboNode Node=*Original;Node.CommandEdges.Reset();Node.PatternBranches.Reset();Node.PatternActions.Reset();Node.AttackWindows.Reset();Node.AutomaticNextNode=NAME_None;
   *Nodes->ContainerPtrToValuePtr<TArray<FKZComboNode>>(Definition.Get())={Node};
   FindFProperty<FObjectPropertyBase>(UKZComboActionAbility::StaticClass(),TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(Ability.Get(),Definition.Get());
   FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"))->SetPropertyValue_InContainer(Ability.Get(),Node.NodeId);
   if(!ASC->TryActivateAbility(Handle)){Test->AddError(TEXT("Original jump activation failed"));Cleanup();return true;}
   Start=Now;Initial=Monster->GetActorLocation();Started=true;return false;
  }
  MaximumHeight=FMath::Max(MaximumHeight,float(Monster->GetActorLocation().Z-Initial.Z));
  if(Monster->GetCharacterMovement()->HasRootMotionSources())
  {
   SawSource=true;
   if(!LoggedMode){Test->AddInfo(FString::Printf(TEXT("VerticalSource mode=%d rootMode=%d"),int32(Monster->GetCharacterMovement()->MovementMode),int32(Monster->GetMesh()->GetAnimInstance()->RootMotionMode)));LoggedMode=true;}
  }
  if(Now-Start<1.5f && Ability->IsActive())return false;
  Test->TestTrue(TEXT("Original vertical path installed a real RootMotionSource"),SawSource);
  Test->TestTrue(TEXT("800cm source jump moves the capsule vertically"),MaximumHeight>400.f);
  Test->AddInfo(FString::Printf(TEXT("VerticalSource maxCapsuleHeight=%g time=%g"),MaximumHeight,Now-Start));
  Cleanup();return true;
 }
 void Cleanup()
 {
  if(Cleaned)return;Cleaned=true;
  if(Monster.IsValid() && Handle.IsValid())Monster->GetAbilitySystemComponent()->CancelAbilityHandle(Handle);
  if(Ability.IsValid() && SavedDefinition)
  {
   FindFProperty<FObjectPropertyBase>(UKZComboActionAbility::StaticClass(),TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(Ability.Get(),const_cast<UKZComboDefinitionData*>(SavedDefinition));
   FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"))->SetPropertyValue_InContainer(Ability.Get(),SavedEntry);
  }
  if(Monster.IsValid())Monster->Destroy();
  if(Player.IsValid())Player->SetActorTransform(Saved);
  for(auto& P:Paused)if(P.IsValid())P->GetStateTreeComponent()->ResumeLogic(TEXT("Owned root/contact fixture finished"));
 }
private:
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;FTransform Saved;double Deadline;
 TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;TWeakObjectPtr<AKZMonster> Monster;TWeakObjectPtr<AKZMonsterAIController> AI;
 TWeakObjectPtr<UKZMonsterPatternAbility> Ability;FGameplayAbilitySpecHandle Handle;
 const UKZComboDefinitionData* SavedDefinition=nullptr;FName SavedEntry;TStrongObjectPtr<UKZComboDefinitionData> Definition;
 FVector Initial;float Start=0,MaximumHeight=0;bool Started=false,SawSource=false,LoggedMode=false,Cleaned=false;
};
class FMonsterContacts : public IAutomationLatentCommand
{
public:
 FMonsterContacts(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),SavedTransform(P->GetActorTransform()),Deadline(FPlatformTime::Seconds()+500.)
 {
  auto* Move=P->GetCharacterMovement();SavedMode=Move->MovementMode;SavedCustom=Move->CustomMovementMode;SavedVelocity=Move->Velocity;
  auto* ASC=P->GetAbilitySystemComponent();SavedHP=ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());SavedMaxHP=ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute());SavedStamina=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());SavedMaxStamina=ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute());
  P->HandleInputMoveReleased();Move->StopMovementImmediately();Move->DisableMovement();
  Delegate=ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).AddRaw(this,&FMonsterContacts::OnHP);
  for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It)if(auto* ExistingAI=Cast<AKZMonsterAIController>(It->GetController()))
  {if(ExistingAI->GetStateTreeComponent()->IsRunning()){Paused.Add(ExistingAI);ExistingAI->GetStateTreeComponent()->StopLogic(TEXT("Owned contact fixture"));}}
 }
 ~FMonsterContacts(){Cleanup();}
 bool Update()override
 {
  if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Six-family contact fixture timeout"));Cleanup();return true;}
  if(FamilyIndex>=6){Test->AddInfo(TEXT("MonsterContact all six families / 30 actual damage-window cases complete"));Cleanup();return true;}
  if(!Monster.IsValid()&&!SpawnFamily()){Cleanup();return true;}
  auto* ASC=Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());auto* Anim=Monster->GetMesh()->GetAnimInstance();const float WorldTime=Player->GetWorld()->GetTimeSeconds();
  if(!Running)
  {
   ASC->CancelAbilityHandle(Handle);Node=Base;Node.NodeId=TEXT("CollisionFixture");Node.CommandEdges.Reset();Node.PatternActions.Reset();Node.PatternBranches.Reset();Node.PatternMoves.Reset();Node.AutomaticNextNode=NAME_None;Node.CollisionToActor=FTransform::Identity;
   FKZAttackCollisionWindow Window;Window.StartTime=Duration*.1f;Window.EndTime=Duration*.3f;Window.Extent=FVector(30,30,40);Window.HPDamage=7;Window.StaminaDamage=3;Window.HitReaction=EKZHitReactionType::None;Window.Source=TEXT("Isolated DEV frame/geometry stimulus; not original gameplay tuning");
   FKZAttackCollisionKey Key;Key.Time=Window.StartTime;Key.Center=FVector(150,0,0);Window.Keys.Add(Key);Key.Time=Window.EndTime;Window.Keys.Add(Key);Node.AttackWindows={Window};
   *FindFProperty<FArrayProperty>(UKZComboDefinitionData::StaticClass(),TEXT("Nodes"))->ContainerPtrToValuePtr<TArray<FKZComboNode>>(Definition.Get())={Node};
   Monster->SetActorLocation(SavedTransform.GetLocation()+FVector(-5000,-5000,10000));Monster->SetActorRotation(FRotator(0,90,0));
   const float Scale=Monster->GetMesh()->GetRelativeScale3D().X;const float Radius=Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
   const float LocalX=CaseIndex==4?180.f*Scale+Radius*.8f:150.f*Scale;
   Contact=Monster->GetActorTransform().TransformPosition(FVector(LocalX,0,0));Player->SetActorLocation(CaseIndex>0&&CaseIndex<4?Monster->GetActorLocation()+FVector(1000,1000,0):Contact,false,nullptr,ETeleportType::TeleportPhysics);
   auto* Victim=Player->GetAbilitySystemComponent();Capturing=false;Victim->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),1000);Victim->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),1000);Victim->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(),1000);Victim->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),1000);
   Hits=0;Capturing=true;Entered=false;PausedAt=-1;Canceled=false;CaseStart=WorldTime;
   if(!ASC->TryActivateAbility(Handle)){Test->AddError(TEXT("Actual granted monster attack activation failed"));Cleanup();return true;}
   Running=true;return false;
  }
  const float Position=Anim->Montage_GetPosition(Node.Montage)-SectionStart;
  if(CaseIndex==2&&PausedAt<0&&Position>=Node.AttackWindows[0].EndTime)
  {Anim->Montage_SetPosition(Node.Montage,SectionStart+Node.AttackWindows[0].EndTime);Anim->Montage_Pause(Node.Montage);PausedAt=WorldTime;}
  if(CaseIndex==3&&!Canceled&&Position>=Duration*.05f){ASC->CancelAbilityHandle(Handle);Canceled=true;CancelTime=WorldTime;}
  const bool CanEnter=CaseIndex==1?Position>=Duration*.6f:CaseIndex==2?PausedAt>=0&&WorldTime>PausedAt+.3f:CaseIndex==3?Canceled&&WorldTime>CancelTime+.3f:false;
  if(CanEnter&&!Entered){Player->SetActorLocation(Contact,false,nullptr,ETeleportType::TeleportPhysics);Entered=true;}
  const bool Done=CaseIndex==2?Entered&&WorldTime>PausedAt+.6f:CaseIndex==3?Entered&&WorldTime>CancelTime+.6f:WorldTime>CaseStart+Duration+.4f;
  if(!Done)return false;
  const bool ExpectHit=CaseIndex==0||CaseIndex==4;const float Damage=1000-Player->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
  const FString Label=FString::Printf(TEXT("%s case%d"),Families[FamilyIndex],CaseIndex);
  Test->TestEqual(*(Label+TEXT(" damage effects once only inside the authored window")),Hits,ExpectHit?1:0);Test->TestEqual(*(Label+TEXT(" HP delta")),Damage,ExpectHit?7.f:0.f);
  if(CaseIndex>0&&CaseIndex<4)Test->TestTrue(*(Label+TEXT(" actually approached only after close/cancel")),Entered);
  auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Families[FamilyIndex]);Row->SetNumberField(TEXT("case"),CaseIndex);Row->SetNumberField(TEXT("hits"),Hits);Row->SetNumberField(TEXT("hp_delta"),Damage);Row->SetBoolField(TEXT("entered_late"),Entered);Row->SetNumberField(TEXT("live_body_scale"),Monster->GetMesh()->GetRelativeScale3D().X);Rows.Add(MakeShared<FJsonValueObject>(Row));
  Test->AddInfo(FString::Printf(TEXT("MonsterContact %s hits=%d HP=%g scale=%g entered=%d"),*Label,Hits,Damage,Monster->GetMesh()->GetRelativeScale3D().X,Entered));
  Capturing=false;ASC->CancelAbilityHandle(Handle);Running=false;
  // Each geometry/window case owns a fresh real attacker; original recovery effects
  // and stamina costs must not contaminate an unrelated boundary stimulus.
  ReleaseFamily();if(++CaseIndex>=5){CaseIndex=0;++FamilyIndex;}return false;
 }
 bool SpawnFamily()
 {
  const FString Path=FString(TEXT("/Game/Bluprints/Monsters/BP_Monster_"))+Families[FamilyIndex]+TEXT(".BP_Monster_")+Families[FamilyIndex]+TEXT("_C");UClass* C=LoadClass<AKZMonster>(nullptr,*Path);
  FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
  Monster=Player->GetWorld()->SpawnActor<AKZMonster>(C,SavedTransform.GetLocation()+FVector(-5000,-5000,10000),FRotator::ZeroRotator,Params);if(!Monster.IsValid()){Test->AddError(Path);return false;}
  if(auto* Controller=Cast<AKZMonsterAIController>(Monster->GetController())){Controller->GetStateTreeComponent()->StopLogic(TEXT("Owned contact fixture"));Controller->GetPerceptionComponent()->Deactivate();Controller->SetActorTickEnabled(false);} // Controller's deferred BeginPlay initialization can otherwise restart the brain.
  auto* ASC=Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());ASC->CancelAllAbilities();Monster->GetCharacterMovement()->DisableMovement();Monster->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
  for(const FGameplayAbilitySpec& Spec:ASC->GetActivatableAbilities())if(auto* Candidate=Cast<UKZComboActionAbility>(Spec.GetPrimaryInstance()))
  {const auto* D=Candidate->GetComboDefinition();const auto* N=D?D->FindNode(Candidate->GetEntryNodeId()):nullptr;if(N&&N->Montage&&!N->AttackWindows.IsEmpty()){Ability=Candidate;Handle=Spec.Handle;Base=*N;break;}}
  if(!Ability.IsValid()){Test->AddError(TEXT("Real granted attack with original windows missing"));return false;}
  SavedDefinition=Ability->GetComboDefinition();SavedEntry=Ability->GetEntryNodeId();Definition.Reset(DuplicateObject<UKZComboDefinitionData>(SavedDefinition,GetTransientPackage()));
  FindFProperty<FObjectPropertyBase>(UKZComboActionAbility::StaticClass(),TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(Ability.Get(),Definition.Get());FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"))->SetPropertyValue_InContainer(Ability.Get(),TEXT("CollisionFixture"));
  float SectionEnd=0;Base.Montage->GetSectionStartAndEndTime(Base.Montage->GetSectionIndex(Base.SectionName),SectionStart,SectionEnd);Duration=SectionEnd-SectionStart;return Duration>0;
 }
 void OnHP(const FOnAttributeChangeData& Data)
 {
  if(!Capturing||Data.NewValue>=Data.OldValue)return;++Hits;
  if(Data.GEModData){const float Sample=Data.GEModData->EffectSpec.GetSetByCallerMagnitude(FName(TEXT("KZAttackMontageTime")),false,-1);Test->TestTrue(TEXT("Monster damage producer time is inside the allowed original frame window"),Sample>=SectionStart+Node.AttackWindows[0].StartTime&&Sample<=SectionStart+Node.AttackWindows[0].EndTime);}
 }
 void ReleaseFamily()
 {
  if(Monster.IsValid())Monster->GetAbilitySystemComponent()->CancelAbilityHandle(Handle);
  if(Ability.IsValid()&&SavedDefinition){FindFProperty<FObjectPropertyBase>(UKZComboActionAbility::StaticClass(),TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(Ability.Get(),const_cast<UKZComboDefinitionData*>(SavedDefinition));FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"))->SetPropertyValue_InContainer(Ability.Get(),SavedEntry);}
  if(Monster.IsValid())Monster->Destroy();Monster.Reset();Ability.Reset();Definition.Reset();SavedDefinition=nullptr;
 }
 void Cleanup()
 {
  if(Cleaned)return;Cleaned=true;Capturing=false;ReleaseFamily();
  if(Player.IsValid()){auto* ASC=Player->GetAbilitySystemComponent();ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(Delegate);ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),SavedMaxHP);ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),SavedHP);ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(),SavedMaxStamina);ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),SavedStamina);Player->SetActorTransform(SavedTransform);Player->GetCharacterMovement()->SetMovementMode(SavedMode,SavedCustom);Player->GetCharacterMovement()->Velocity=SavedVelocity;}
  for(auto& Controller:Paused)if(Controller.IsValid())Controller->GetStateTreeComponent()->RestartLogic();
  FString Text;auto Writer=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(Rows,Writer);const FString Directory=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_CONTACT_OUT"));FFileHelper::SaveStringToFile(Text,*(Directory/TEXT("MonsterContactCases.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
 }
private:
 const TCHAR* Families[6]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;FTransform SavedTransform;EMovementMode SavedMode;uint8 SavedCustom;FVector SavedVelocity;float SavedHP,SavedMaxHP,SavedStamina,SavedMaxStamina;double Deadline;FDelegateHandle Delegate;TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;
 TWeakObjectPtr<AKZMonster> Monster;TWeakObjectPtr<UKZComboActionAbility> Ability;FGameplayAbilitySpecHandle Handle;const UKZComboDefinitionData* SavedDefinition=nullptr;FName SavedEntry;TStrongObjectPtr<UKZComboDefinitionData> Definition;FKZComboNode Base,Node;
 int32 FamilyIndex=0,CaseIndex=0,Hits=0;float Duration=0,SectionStart=0,CaseStart=0,PausedAt=-1,CancelTime=0;FVector Contact;bool Capturing=false,Running=false,Entered=false,Canceled=false,Cleaned=false;TArray<TSharedPtr<FJsonValue>> Rows;
};
class FWaitContactPIE : public IAutomationLatentCommand
{
public:FWaitContactPIE(FAutomationTestBase* T,bool InRootPoses=false,bool InContacts=false):Test(T),Deadline(FPlatformTime::Seconds()+60.),RootPoses(InRootPoses),Contacts(InContacts){}
 bool Update()override
 {
  for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
   for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance())
    {if(RootPoses)FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FBodyRootPoses>(Test,*It));else if(Contacts)FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FMonsterContacts>(Test,*It));else FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FVerticalPattern>(Test,*It));return true;}
  if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Start owned PIE"));return true;}return false;
 }
private:FAutomationTestBase* Test;double Deadline;bool RootPoses,Contacts;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZContactVerticalPIE,"Khazan.MonsterContactRepair.VerticalPattern.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZContactVerticalPIE::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitContactPIE>(this));return true;}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZContactRootPosesPIE,"Khazan.MonsterContactRepair.RootPoses.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZContactRootPosesPIE::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitContactPIE>(this,true));return true;}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZContactMonsterHitsPIE,"Khazan.MonsterContactRepair.MonsterHits.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZContactMonsterHitsPIE::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitContactPIE>(this,false,true));return true;}
#endif
