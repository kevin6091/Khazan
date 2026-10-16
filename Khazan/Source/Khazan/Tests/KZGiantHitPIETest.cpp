// Transient fixture values are QA stimuli, never original gameplay tuning.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "AI/KZMonsterAIController.h"
#include "AI/KZMonsterStateTreeNodes.h"
#include "Components/StateTreeAIComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "KZGameplayTags.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Camera/CameraActor.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "BrainComponent.h"
#include "UnrealClient.h"
#include "GameplayEffect.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "HAL/PlatformMisc.h"
namespace KZGiantHitQA
{
class FRun final:public IAutomationLatentCommand
{
public:
 FRun(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),Deadline(FPlatformTime::Seconds()+600.)
 {
  SavedPlayer=P->GetActorTransform();P->GetAbilitySystemComponent()->CancelAllAbilities();
  for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It)if(auto* AI=Cast<AKZMonsterAIController>(It->GetController())){Paused.Add(AI);AI->GetStateTreeComponent()->StopLogic(TEXT("Owned giant hit fixture"));}
  Floor=P->GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,10000),FRotator::ZeroRotator);
  Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Floor->SetActorScale3D(FVector(40,40,.2));Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
  P->SetActorLocation(FVector(-1200,0,10110));Camera=P->GetWorld()->SpawnActor<ACameraActor>();P->GetController<APlayerController>()->SetViewTarget(Camera.Get());
 }
 ~FRun(){Cleanup();}
 bool Update()override
 {
  if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Owned giant hit watchdog"));Cleanup();return true;}
  UWorld* World=Player->GetWorld();const float Now=World->GetTimeSeconds();
  if(Family>=3){SaveReport();Cleanup();return true;}
  if(!Target.IsValid()&&Stage!=3)
  {
   const FString Name=Family==0?TEXT("ApesStoneHandElite"):Family==1?TEXT("Yetuga"):TEXT("Swordsman");
   UClass* Class=LoadClass<AKZMonster>(nullptr,*(TEXT("/Game/Bluprints/Monsters/BP_Monster_")+Name+TEXT(".BP_Monster_")+Name+TEXT("_C")));
   FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   Target=World->SpawnActor<AKZMonster>(Class,FVector(0,-330,10400),FRotator::ZeroRotator,Params);
   Control=World->SpawnActor<AKZMonster>(Class,FVector(0,330,10400),FRotator::ZeroRotator,Params);
   if(!Test->TestTrue(TEXT("Real gameplay family fixtures"),Target.IsValid()&&Control.IsValid())){Cleanup();return true;}
   for(AKZMonster* M:{Target.Get(),Control.Get()})
   {
    if(!M->GetController())M->SpawnDefaultController();
    if(auto* AI=Cast<AKZMonsterAIController>(M->GetController()))AI->GetStateTreeComponent()->StopLogic(TEXT("Controlled real attack stimuli"));
    auto* A=M->GetAbilitySystemComponent();A->CancelAllAbilities();A->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),A->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()));A->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),A->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));
    FVector Ground=M->GetActorLocation();Ground.Z=10010.f+M->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST;
    M->SetActorLocation(Ground);M->GetCharacterMovement()->SetMovementMode(MOVE_Walking);M->GetCharacterMovement()->StopMovementImmediately();
    M->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   }
   OriginalPool=Target->GetCharacterDefinition()->GetHitReactionSettings().AdditiveHits;
   if(Family<2)
   {
    Test->TestEqual(TEXT("Four original normal directions configured as additive"),OriginalPool.Num(),4);
    auto& Pool=const_cast<FKZHitReactionSettings&>(Target->GetCharacterDefinition()->GetHitReactionSettings()).AdditiveHits;
    Pool={OriginalPool[Case<4?Case:2]};ExpectedOverlay=Pool[0];
   }
   else Test->TestTrue(TEXT("Human definition retains blocking reaction"),OriginalPool.IsEmpty());
   Camera->SetActorLocation(FVector(750,-850,10440));Camera->SetActorRotation((FVector(0,0,10240)-Camera->GetActorLocation()).Rotation());
   Stage=0;Start=Now;MaxPoseDelta=MaxOverlayWeight=0.f;SawRepeat=Captured=false;
   Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Name);Row->SetNumberField(TEXT("case"),Case);
   return false;
  }
  auto* ASC=Target.IsValid()?Target->GetAbilitySystemComponent():nullptr;UAnimInstance* Anim=Target.IsValid()?Target->GetMesh()->GetAnimInstance():BoundCleanupAnim.Get();
  if(Stage==0)
  {
   if(Now-Start<.2f)return false;
   // Spawn/landing can auto-start an action after the initial constructor cancellation.
   ASC->CancelAllAbilities();Control->GetAbilitySystemComponent()->CancelAllAbilities();
   FGameplayAbilitySpecHandle Chosen;float Longest=-1.f;
   for(const FGameplayAbilitySpec& Spec:ASC->GetActivatableAbilities())
    if(auto* A=Cast<UKZComboActionAbility>(Spec.GetPrimaryInstance()?Spec.GetPrimaryInstance():Spec.Ability.Get());A&&Target->GetAttackAbilities().Contains(A->GetClass()))
     if(const auto* N=A->GetComboDefinition()?A->GetComboDefinition()->FindNode(A->GetEntryNodeId()):nullptr;N&&N->Montage&&!N->AttackWindows.IsEmpty())
     {const int32 Section=N->Montage->GetSectionIndex(N->SectionName);const float Length=Section!=INDEX_NONE?N->Montage->GetSectionLength(Section):0.f;if(Length>Longest){Longest=Length;Chosen=Spec.Handle;}}
   // Human entry nodes can be preparation-only; their attack windows occur on successor nodes.
   if(!Chosen.IsValid()&&Family==2&&!Target->GetAttackAbilities().IsEmpty())
    if(const auto* Spec=ASC->FindAbilitySpecFromClass(Target->GetAttackAbilities()[0]))Chosen=Spec->Handle;
   Test->AddInfo(FString::Printf(TEXT("GIANT_HIT_BEGIN family=%d case=%d chosen=%d hp=%g st=%g"),Family,Case,Chosen.IsValid(),ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute())));
   bool Activated=Chosen.IsValid()&&ASC->TryActivateAbility(Chosen);
   if(!Activated&&Family==2)
    for(const auto& Class:Target->GetAttackAbilities())
     if(const auto* Spec=ASC->FindAbilitySpecFromClass(Class);Spec&&ASC->TryActivateAbility(Spec->Handle)){Chosen=Spec->Handle;Activated=true;break;}
   if(!Test->TestTrue(TEXT("Existing real attack activates"),Activated))
   {
    for(const auto& Class:Target->GetAttackAbilities())if(const auto* Spec=ASC->FindAbilitySpecFromClass(Class))
    {
     const auto* A=Cast<UKZComboActionAbility>(Spec->GetPrimaryInstance());const auto* N=A&&A->GetComboDefinition()?A->GetComboDefinition()->FindNode(A->GetEntryNodeId()):nullptr;
     FGameplayTagContainer Tags;ASC->GetOwnedGameplayTags(Tags);
     Test->AddInfo(FString::Printf(TEXT("HUMAN_DIAG class=%s anim=%s node=%s montage=%s section=%s playable=%d tags=%s"),*Class->GetPathName(),*GetNameSafe(Anim),N?*N->NodeId.ToString():TEXT("None"),N?*GetNameSafe(N->Montage):TEXT("None"),N?*N->SectionName.ToString():TEXT("None"),N&&N->Montage?N->Montage->GetSectionIndex(N->SectionName):INDEX_NONE,*Tags.ToStringSimple()));
    }
    SaveReport();Cleanup();return true;
   }
   Attack=Cast<UKZComboActionAbility>(ASC->GetAnimatingAbility());
   if(!Test->TestNotNull(TEXT("ASC owns actual attack Ability"),Attack.Get())){Cleanup();return true;}
   ActionMontage=Attack->GetCurrentMontage();ActionId=Anim->GetActiveInstanceForMontage(ActionMontage.Get())->GetInstanceID();
   FGameplayAbilitySpecHandle ControlHandle;
   for(const auto& Spec:Control->GetAbilitySystemComponent()->GetActivatableAbilities())if(Spec.Ability&&Spec.Ability->GetClass()==Attack->GetClass()){ControlHandle=Spec.Handle;break;}
   Test->TestTrue(TEXT("Control executes the identical actual action"),Control->GetAbilitySystemComponent()->TryActivateAbility(ControlHandle));
   Row->SetStringField(TEXT("attack_class"),Attack->GetClass()->GetPathName());Row->SetStringField(TEXT("action_montage"),ActionMontage->GetPathName());Row->SetNumberField(TEXT("action_length"),Longest);
   MoveTagCount=ASC->GetTagCount(KZGameplayTags::Block_Movement_Input);Start=Now;Stage=1;return false;
  }
  if(Stage==1)
  {
   if(Now-Start<.15f)return false;
   HPBefore=ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());STBefore=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
   const auto& Settings=Target->GetCharacterDefinition()->GetMonsterStaminaSettings();
   auto Spec=ASC->MakeOutgoingSpec(Settings.DamageEffect,1.f,ASC->MakeEffectContext());
   if(!Test->TestTrue(TEXT("Existing accepted HP/Stamina GE available"),Spec.IsValid())){Cleanup();return true;}
   Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),-1.f);Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")),-1.f);
   Test->TestTrue(TEXT("Real approved damage applies"),ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()).WasSuccessfullyApplied());
   Test->TestTrue(TEXT("HP and Stamina both decrease normally"),ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())<HPBefore&&ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute())<STBefore);
   Type=Case==11?EKZHitReactionType::None:Case==4?EKZHitReactionType::Knockback:Case==5?EKZHitReactionType::Launch:Case==6?EKZHitReactionType::VictimFront:EKZHitReactionType::Short;
   Target->PlayHitReaction(Type,Player.Get());
   if(Family==2)
   {
    Test->TestTrue(TEXT("Human normal hit still interrupts its action"),!Attack->IsActive()&&ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
    Rows.Add(MakeShared<FJsonValueObject>(Row));NextCase();return false;
   }
   FAnimMontageInstance* Overlay=Anim->GetActiveInstanceForMontage(ExpectedOverlay.Get());
   if(!Test->TestNotNull(TEXT("Independent additive montage starts"),Overlay)){Cleanup();return true;}
   OverlayId=Overlay->GetInstanceID();LastPosition=Anim->Montage_GetPosition(ActionMontage.Get());Start=Now;Stage=2;return false;
  }
  if(Stage==2)
  {
   const float Age=Now-Start;
   Test->TestTrue(TEXT("Ordinary hit never owns blocking HitReacting"),!ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
   Test->TestTrue(TEXT("Attack Ability/task and ASC montage remain owned"),Attack.IsValid()&&Attack->IsActive()&&ASC->GetAnimatingAbility()==Attack.Get()&&ASC->GetCurrentMontage()==ActionMontage.Get());
   FAnimMontageInstance* Action=Anim->GetActiveInstanceForMontage(ActionMontage.Get());
   Test->TestTrue(TEXT("No action montage restart or interruption"),Action&&Action->GetInstanceID()==ActionId&&Action->IsPlaying());
   const float Position=Anim->Montage_GetPosition(ActionMontage.Get());Test->TestTrue(TEXT("Action time advances monotonically"),Position+UE_KINDA_SMALL_NUMBER>=LastPosition);LastPosition=Position;
   Test->TestEqual(TEXT("No extra movement-input block introduced"),ASC->GetTagCount(KZGameplayTags::Block_Movement_Input),MoveTagCount);
   MaxOverlayWeight=FMath::Max(MaxOverlayWeight,Anim->GetSlotMontageGlobalWeight(TEXT("KZHitReaction")));
   const FName Bone(TEXT("Bip001-Spine2"));
   if(Target->GetMesh()->GetBoneIndex(Bone)!=INDEX_NONE)
   {
    const FQuat A=Target->GetActorQuat().Inverse()*Target->GetMesh()->GetSocketQuaternion(Bone);
    const FQuat B=Control->GetActorQuat().Inverse()*Control->GetMesh()->GetSocketQuaternion(Bone);
    MaxPoseDelta=FMath::Max(MaxPoseDelta,FMath::RadiansToDegrees(A.AngularDistance(B)));
   }
   if(!Captured&&Age>=.16f){Captured=true;Shot(TEXT("Flinch"));}
   if((Case==0||Case>=7)&&!SawRepeat&&Age>=(Case==0?.22f:.42f))
   {
    SawRepeat=true;Target->PlayHitReaction(Type,Player.Get());Target->PlayHitReaction(Type,Player.Get());
    auto* New=Anim->GetActiveInstanceForMontage(ExpectedOverlay.Get());Test->TestTrue(TEXT("Repeated hit renews overlay without renewing attack"),New&&New->GetInstanceID()!=OverlayId);OverlayId=New?New->GetInstanceID():INDEX_NONE;
   }
   if(Age<.48f)return false;
   Test->TestTrue(TEXT("Independent slot really contributes to evaluated pose"),MaxOverlayWeight>.05f&&MaxPoseDelta>.1f);
   Row->SetNumberField(TEXT("max_slot_weight"),MaxOverlayWeight);Row->SetNumberField(TEXT("max_spine_delta_degrees"),MaxPoseDelta);Row->SetBoolField(TEXT("repeated_hit"),SawRepeat);Row->SetNumberField(TEXT("last_action_position"),LastPosition);
   if(Case>=7&&Case<=10)
   {
    if(Case==7){ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),0.f);Row->SetStringField(TEXT("cleanup"),TEXT("Exhaustion"));}
    else if(Case==8){ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),0.f);Row->SetStringField(TEXT("cleanup"),TEXT("Death"));}
    else if(Case==9){Target->GetController()->UnPossess();Row->SetStringField(TEXT("cleanup"),TEXT("UnPossess"));}
    else {Target->Destroy();Row->SetStringField(TEXT("cleanup"),TEXT("EndPlay"));}
    BoundCleanupAnim=Anim;Start=Now;Stage=3;return false;
   }
   Rows.Add(MakeShared<FJsonValueObject>(Row));NextCase();return false;
  }
  if(Stage==3)
  {
   if(Now-Start<.1f)return false;
   if(auto* I=BoundCleanupAnim.IsValid()?BoundCleanupAnim->GetMontageInstanceForID(OverlayId):nullptr)Test->TestTrue(TEXT("Owned overlay stops at lifecycle boundary"),I->IsStopped());
   // Proxy slot weight is cached when death/EndPlay freezes pose evaluation; inspect actual instances.
   if(BoundCleanupAnim.IsValid())for(const auto* I:BoundCleanupAnim->MontageInstances)
    if(I&&I->Montage&&I->Montage->GetGroupName()==TEXT("KZHitReactionGroup"))
     Test->TestTrue(TEXT("Every outgoing repeat-hit instance is stopped"),I->IsStopped());
   if(Case==7)
   {
    Test->TestTrue(TEXT("ST zero still cancels real attack and enters existing groggy"),!Attack->IsActive()&&ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
    Test->TestFalse(TEXT("Exhaustion uses no ordinary hit state"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
    Shot(TEXT("Groggy"));Row->SetNumberField(TEXT("original_exhaustion_seconds"),Target->GetCharacterDefinition()->GetMonsterStaminaSettings().ExhaustionSeconds);
   }
   if(Case==8)Test->TestTrue(TEXT("HP zero prioritizes existing death and action cancellation"),!Attack->IsActive()&&ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead));
   Rows.Add(MakeShared<FJsonValueObject>(Row));NextCase();return false;
  }
  return false;
 }
private:
 void Shot(const TCHAR* Label){const FString Out=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_OUT"));FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("Family%d_Case%d_%s.png"),Family,Case,Label),false,false);}
 void NextCase()
 {
  SaveReport();
  if(Target.IsValid())const_cast<FKZHitReactionSettings&>(Target->GetCharacterDefinition()->GetHitReactionSettings()).AdditiveHits=OriginalPool;
  else if(Control.IsValid())const_cast<FKZHitReactionSettings&>(Control->GetCharacterDefinition()->GetHitReactionSettings()).AdditiveHits=OriginalPool;
  if(Target.IsValid())Target->Destroy();if(Control.IsValid())Control->Destroy();Target.Reset();Control.Reset();Attack.Reset();ExpectedOverlay.Reset();BoundCleanupAnim.Reset();
  Stage=0;++Case;if(Case>=12||Family==2){++Family;Case=0;}
 }
 void SaveReport(){auto R=MakeShared<FJsonObject>();R->SetArrayField(TEXT("cases"),Rows);FString Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));const FString Out=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_OUT"));FFileHelper::SaveStringToFile(Text,*(Out/TEXT("Native.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);}
 void Cleanup()
 {
  if(Cleaned)return;Cleaned=true;
  if(Target.IsValid())const_cast<FKZHitReactionSettings&>(Target->GetCharacterDefinition()->GetHitReactionSettings()).AdditiveHits=OriginalPool;
  else if(Control.IsValid())const_cast<FKZHitReactionSettings&>(Control->GetCharacterDefinition()->GetHitReactionSettings()).AdditiveHits=OriginalPool;
  if(Target.IsValid())Target->Destroy();if(Control.IsValid())Control->Destroy();if(Floor.IsValid())Floor->Destroy();if(Camera.IsValid())Camera->Destroy();
  if(Player.IsValid()){Player->SetActorTransform(SavedPlayer);Player->GetController<APlayerController>()->SetViewTarget(Player.Get());}
  for(auto AI:Paused)if(AI.IsValid())AI->GetStateTreeComponent()->StartLogic();
 }
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Target,Control;TWeakObjectPtr<UKZComboActionAbility> Attack;
 TWeakObjectPtr<UAnimMontage> ActionMontage,ExpectedOverlay;TWeakObjectPtr<UAnimInstance> BoundCleanupAnim;
 TWeakObjectPtr<AStaticMeshActor> Floor;TWeakObjectPtr<ACameraActor> Camera;TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;
 TArray<TObjectPtr<UAnimMontage>> OriginalPool;TArray<TSharedPtr<FJsonValue>> Rows;TSharedPtr<FJsonObject> Row;
 FTransform SavedPlayer;double Deadline;int32 Family=0,Case=0,Stage=0,ActionId=INDEX_NONE,OverlayId=INDEX_NONE,MoveTagCount=0;
 float Start=0,LastPosition=0,MaxPoseDelta=0,MaxOverlayWeight=0,HPBefore=0,STBefore=0;bool SawRepeat=false,Captured=false,Cleaned=false;EKZHitReactionType Type;
};
class FWait final:public IAutomationLatentCommand
{
public:FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+90.){}
 bool Update()override
 {
  for(const auto& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetMesh()->GetAnimInstance()){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}
  if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("No task-owned PIE player"));return true;}return false;
 }
private:FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantHitPIE,"Khazan.GiantHit.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZGiantHitPIE::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZGiantHitQA::FWait>(this));return true;}
#endif