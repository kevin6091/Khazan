// Private development integration QA. No asset saves or original input/visual parity claim.
// Transient EntryNodeId changes use a live Ability instance and are always restored.
// The -1/+1 HP effects and transient notify callbacks below are boundary fixtures,
// not original damage values. HP-only effects lack real producer provenance.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Components/DecalComponent.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "AI/KZMonsterAIController.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Components/CapsuleComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "UObject/ObjectKey.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"

namespace
{
const TCHAR* Nodes[] = {TEXT("WeakAttack01"),TEXT("WeakAttack02"),TEXT("WeakAttack03"),TEXT("WeakAttack04"),TEXT("WeakAttack05"),
 TEXT("StrongAttack01"),TEXT("StrongAttack02"),TEXT("StrongAttack03"),TEXT("StrongCharge"),TEXT("StrongChargeAttack"),
 TEXT("ChargeAttack02"),TEXT("ChargeAttack03"),TEXT("DodgeAttack_F"),TEXT("DodgeAttack_R"),TEXT("DodgeAttack_B"),TEXT("DodgeAttack_L"),TEXT("SpinningAttack01"),TEXT("OverFury")};

class FCombatEffectPIE : public IAutomationLatentCommand
{
public:
 FCombatEffectPIE(FAutomationTestBase* InTest, AKZPlayer* InPlayer)
  : Test(InTest), Player(InPlayer), ASC(Cast<UKZAbilitySystemComponent>(InPlayer->GetAbilitySystemComponent())),
    SavedTransform(InPlayer->GetActorTransform()), Deadline(FPlatformTime::Seconds()+300.)
 {
  TransformObservationPath=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_ATTACK_VFX_TRANSFORM_JSONL"));
  SavedHP=ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
  SavedStamina=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
  SavedTick=InPlayer->GetMesh()->VisibilityBasedAnimTickOption;
  SavedMovement=InPlayer->GetCharacterMovement()->MovementMode;SavedCustomMovement=InPlayer->GetCharacterMovement()->CustomMovementMode;
 }
 ~FCombatEffectPIE() override { Cleanup(); }
 bool Update() override
 {
  if(!Player.IsValid() || !ASC.IsValid() || FPlatformTime::Seconds()>Deadline)
  { Test->AddError(TEXT("CombatEffect PIE expired or lost its fixture avatar"));Cleanup();return true; }
  if(Phase==0)
  {
   Player->HandleInputMoveReleased(); Cancel(ASC.Get());
   Player->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   Handle=FindWeak(ASC.Get());
   EntryProperty=FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"));
   if(!Test->TestTrue(TEXT("Authoritative granted Weak fixture and reflected live entry exist"),Player->HasAuthority() && Handle.IsValid() && EntryProperty)) return Finish();
   Refill(ASC.Get());
   if(!Test->TestTrue(TEXT("Real granted Weak activates"),ASC->TryActivateAbility(Handle))) return Finish();
   Ability=Cast<UKZComboActionAbility>(ASC->FindAbilitySpecFromHandle(Handle)->GetPrimaryInstance());
   if(!Test->TestTrue(TEXT("Fixture edits only a live per-actor Ability"),Ability.IsValid() && !Ability->HasAnyFlags(RF_ClassDefaultObject))) return Finish();
   SavedEntry=Ability->GetEntryNodeId();bSavedEntry=true;Cancel(ASC.Get());
   DamageDelegate=ASC->OnGameplayEffectAppliedDelegateToTarget.AddLambda([this](UAbilitySystemComponent*,const FGameplayEffectSpec& Spec,FActiveGameplayEffectHandle)
   { if(Spec.GetContext().GetSourceObject()==Ability.Get() && Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),false,0.f)<0.f && Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackMontageTime")),false,-1.f)>=0.f && Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackMontageInstance")),false,-1.f)>=0.f && Spec.GetSetByCallerMagnitude(FName(TEXT("KZAttackExecution")),false,-1.f)>=0.f) ++ConfirmedDamage; });
   Phase=1;
  }
  if(Phase==1)
  {
   if(NodeIndex==UE_ARRAY_COUNT(Nodes)) { Phase=3;return false; }
   Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorTransform(SavedTransform,false,nullptr,ETeleportType::TeleportPhysics);
   Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
   Before.Reset();for(TObjectIterator<UParticleSystemComponent> It;It;++It) if(It->GetWorld()==Player->GetWorld()) Before.Add(FObjectKey(*It));
   Seen.Reset();SeenSections.Reset();ConditionalIds.Reset();ExpectedSections.Reset();ConfirmedDamage=0;
   EntryProperty->SetPropertyValue_InContainer(Ability.Get(),FName(Nodes[NodeIndex]));
   const FKZComboNode* Node=Ability->GetComboDefinition()->FindNode(FName(Nodes[NodeIndex]));
   if(!Test->TestNotNull(TEXT("Current source node exists"),Node) || !Node->Montage) return Finish();
   Montage=Node->Montage;
   int32 Section=Montage->GetSectionIndex(Node->SectionName);float Start=0.f,End=0.f;
   if(!Test->TestTrue(TEXT("Entry section exists"),Section!=INDEX_NONE)) return Finish();
   Montage->GetSectionStartAndEndTime(Section,Start,End);
   while(Montage->CompositeSections.IsValidIndex(Section) && !ExpectedSections.Contains(Montage->CompositeSections[Section].SectionName))
   { ExpectedSections.Add(Montage->CompositeSections[Section].SectionName);float SectionStart=0.f,SectionEnd=0.f;Montage->GetSectionStartAndEndTime(Section,SectionStart,SectionEnd);End=FMath::Max(End,SectionEnd);Section=Montage->GetSectionIndex(Montage->CompositeSections[Section].NextSectionName); }
   CandidateIds.Reset();ObservationDefinitions.Reset();
   for(const FAnimNotifyEvent& Event:Montage->Notifies)
    if(const auto* Parent=Cast<UKZAnimNotify_CombatEffect>(Event.Notify.Get());Parent && Event.GetTime()>=Start && Event.GetTime()<End)
    {
     const auto Collect=[this](const UKZAnimNotify_CombatEffect* Effect)
     { if(Effect && !Effect->bEndEvent && !Effect->EventId.IsNone()) { CandidateIds.Add(Effect->EventId);ObservationDefinitions.Add(Effect->EventId,Effect);if(Effect->bOnAttackSuccessed) ConditionalIds.Add(Effect->EventId);if(!Template.IsValid() && Effect->ParticleTemplate) Template=Effect->ParticleTemplate; } };
     Collect(Parent);for(const auto& Child:Parent->BatchedEffects) Collect(Child.Get());
    }
   if(!Test->TestTrue(TEXT("Authored effect markers exist in this real section chain"),!CandidateIds.IsEmpty())) return Finish();
   Refill(ASC.Get());
   if(!Test->TestTrue(TEXT("Real Ability activates the selected node"),ASC->TryActivateAbility(Handle))) return Finish();
   Test->TestEqual(TEXT("Ability consumes transient entry"),Ability->GetCurrentNodeId(),FName(Nodes[NodeIndex]));
   NodeDeadline=Player->GetWorld()->GetTimeSeconds()+Montage->GetPlayLength()+5.;Phase=2;
   return false;
  }
  if(Phase==2)
  {
   if(UAnimInstance* Anim=Player->GetMesh()->GetAnimInstance())
    if(Ability->IsActive()) SeenSections.Add(Anim->Montage_GetCurrentSection(Montage.Get()));
   for(TObjectIterator<UParticleSystemComponent> It;It;++It)
    if(IsValid(*It) && It->GetWorld()==Player->GetWorld() && !Before.Contains(FObjectKey(*It)) && It->ComponentHasTag(TEXT("KZCombatEffect")))
     for(FName Id:CandidateIds) if(It->ComponentHasTag(Id))
     { ObserveTransform(*It,ObservationDefinitions.FindRef(Id));Seen.Add(Id);Test->TestTrue(TEXT("Conditional particle requires a real accepted damage callback"),!ConditionalIds.Contains(Id) || ConfirmedDamage>0); }
   if(Ability->IsActive())
   { if(Player->GetWorld()->GetTimeSeconds()>NodeDeadline) { Test->AddError(TEXT("Actual attack section never completed"));return Finish(); }return false; }
   Test->TestTrue(TEXT("Natural playback produces authored feedback"),!Seen.IsEmpty());
   for(FName Section:ExpectedSections) Test->TestTrue(TEXT("Natural automatic section observed"),SeenSections.Contains(Section));
   Test->AddInfo(FString::Printf(TEXT("CombatEffect Natural Node=%s SeenEvents=%d Sections=%d ConfirmedDamage=%d"),Nodes[NodeIndex],Seen.Num(),SeenSections.Num(),ConfirmedDamage));
   ++NodeIndex;Phase=1;return false;
  }
  if(Phase==3)
  {
   if(!Test->TestTrue(TEXT("Real authored Cascade template available"),Template.IsValid())) return Finish();
   FTransform OtherTransform=SavedTransform;OtherTransform.AddToTranslation(FVector(500,0,0));
   Other=Player->GetWorld()->SpawnActorDeferred<AKZPlayer>(Player->GetClass(),OtherTransform,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
   if(!Test->TestTrue(TEXT("Second actual player archetype created"),Other.IsValid())) return Finish();
   Other->AutoPossessPlayer=EAutoReceiveInput::Disabled;Other->AutoPossessAI=EAutoPossessAI::Disabled;Other->FinishSpawning(OtherTransform);
   if(!Test->TestTrue(TEXT("Fixture does not transfer the player controller"),Player->IsPlayerControlled() && !Other->IsPlayerControlled())) return Finish();
   Other->SetActorEnableCollision(false);Other->GetCharacterMovement()->DisableMovement();
   Other->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   OtherASC=Cast<UKZAbilitySystemComponent>(Other->GetAbilitySystemComponent());
   Phase=4;return false; // Let the second real AnimInstance initialize before activation.
  }
  if(Phase==4)
  {
   if(!Test->TestTrue(TEXT("Second avatar owns a separate ASC/AnimInstance"),OtherASC.IsValid() && OtherASC.Get()!=ASC.Get() && Other->GetMesh()->GetAnimInstance())) return Finish();
   EntryProperty->SetPropertyValue_InContainer(Ability.Get(),SavedEntry);Refill(ASC.Get());
   if(!Test->TestTrue(TEXT("Primary restarts its real attack"),ASC->TryActivateAbility(Handle))) return Finish();
   OtherHandle=FindWeak(OtherASC.Get());Refill(OtherASC.Get());
   if(!Test->TestTrue(TEXT("Second ASC starts its own real attack"),OtherHandle.IsValid() && OtherASC->TryActivateAbility(OtherHandle))) return Finish();
   Player->GetMesh()->GetAnimInstance()->Montage_Pause(Ability->GetCurrentMontage());
   OtherAbility=Cast<UKZComboActionAbility>(OtherASC->FindAbilitySpecFromHandle(OtherHandle)->GetPrimaryInstance());
   if(!Test->TestTrue(TEXT("Per-avatar Ability instance isolation"),OtherAbility.IsValid() && OtherAbility.Get()!=Ability.Get())) return Finish();
   Other->GetMesh()->GetAnimInstance()->Montage_Pause(OtherAbility->GetCurrentMontage());
   Direct.Reset(NewObject<UKZAnimNotify_CombatEffect>(GetTransientPackage()));
   Direct->EventId=TEXT("KZFX_QA_Direct");Direct->ParticleTemplate=Template.Get();Direct->bAttached=true;
   Direct->bDestroyOnNotifyEnd=true;Direct->bDestroyOnAnimEnd=true;
   Conditional.Reset(NewObject<UKZAnimNotify_CombatEffect>(GetTransientPackage()));
   Conditional->EventId=TEXT("KZFX_QA_Confirmed");Conditional->ParticleTemplate=Template.Get();Conditional->bAttached=true;
   Conditional->bOnAttackSuccessed=true;Conditional->bDestroyOnNotifyEnd=true;Conditional->bDestroyOnAnimEnd=true;
   const int32 OldId=InstanceId(Player.Get(),Ability.Get());
   Emit(Player.Get(),Ability.Get(),Direct.Get(),false,OldId,Other->GetMesh());
   Test->TestEqual(TEXT("Foreign avatar payload cannot spawn"),Count(Player.Get(),Direct->EventId),0);
   Emit(Player.Get(),Ability.Get(),Direct.Get());Emit(Player.Get(),Ability.Get(),Direct.Get());
   Test->TestEqual(TEXT("Duplicate start creates one owned component"),Count(Player.Get(),Direct->EventId),1);
   Emit(Other.Get(),OtherAbility.Get(),Direct.Get());
   Test->TestEqual(TEXT("Same shared notify has a separate second-avatar component"),Count(Other.Get(),Direct->EventId),1);
   Emit(Player.Get(),Ability.Get(),Direct.Get(),true);
   Test->TestEqual(TEXT("Paired stop closes primary component"),Count(Player.Get(),Direct->EventId),0);
   Test->TestEqual(TEXT("Primary stop does not close another avatar"),Count(Other.Get(),Direct->EventId),1);
   Emit(Player.Get(),Ability.Get(),Conditional.Get());Emit(Other.Get(),OtherAbility.Get(),Conditional.Get());
   Test->TestEqual(TEXT("Conditional animation window alone emits nothing"),Count(Player.Get(),Conditional->EventId),0);
   ApplyFixture(Player.Get(),-1.f);Test->TestEqual(TEXT("Wrong SourceObject rejected"),Count(Player.Get(),Conditional->EventId),0);
   ApplyFixture(Ability.Get(),1.f);Test->TestEqual(TEXT("Healing delta is not confirmed damage"),Count(Player.Get(),Conditional->EventId),0);
   const float BeforeHP=OtherASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
   ApplyFixture(Ability.Get(),-1.f);
   Test->TestEqual(TEXT("Fixture applies actual HP delta through GAS"),OtherASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),BeforeHP-1.f);
   Test->TestEqual(TEXT("HP-only GE without actual producer provenance emits no conditional feedback"),Count(Player.Get(),Conditional->EventId),0);
   Test->TestEqual(TEXT("Being the target does not confirm the second avatar's attack"),Count(Other.Get(),Conditional->EventId),0);
   Emit(Player.Get(),Ability.Get(),Conditional.Get(),true);ApplyFixture(Ability.Get(),-1.f);
   Test->TestEqual(TEXT("Closed source window rejects the HP-only fixture"),Count(Player.Get(),Conditional->EventId),0);
   Emit(Player.Get(),Ability.Get(),Direct.Get());Cancel(ASC.Get());
   Test->TestEqual(TEXT("Cancel destroys fixture resources owned by this activation"),Count(Player.Get(),Direct->EventId),0);
   ApplyFixture(Ability.Get(),-1.f);
   Test->TestEqual(TEXT("Canceled Ability no longer reacts to applied effects"),Count(Player.Get(),Conditional->EventId),0);
   Test->TestEqual(TEXT("Cancel leaves second avatar active"),Count(Other.Get(),Direct->EventId),1);
   Refill(ASC.Get());if(!Test->TestTrue(TEXT("Canceled attack can restart"),ASC->TryActivateAbility(Handle))) return Finish();
   Player->GetMesh()->GetAnimInstance()->Montage_Pause(Ability->GetCurrentMontage());
   Test->TestTrue(TEXT("Restart owns a new montage instance"),InstanceId(Player.Get(),Ability.Get())!=OldId);
   Emit(Player.Get(),Ability.Get(),Direct.Get(),false,OldId);
   Test->TestEqual(TEXT("Stale previous-instance callback rejected"),Count(Player.Get(),Direct->EventId),0);
   Emit(Player.Get(),Ability.Get(),Direct.Get());Test->TestEqual(TEXT("Current instance callback still works after restart"),Count(Player.Get(),Direct->EventId),1);
   Cancel(ASC.Get());Cancel(OtherASC.Get());
   Test->TestEqual(TEXT("Repeated cleanup primary"),Count(Player.Get(),Direct->EventId),0);
   Test->TestEqual(TEXT("Repeated cleanup second avatar"),Count(Other.Get(),Direct->EventId),0);
   Test->AddInfo(TEXT("CombatEffect boundary fixtures complete; HP-only fixtures are negative provenance tests, not natural weapon collision or original input parity."));
   Phase=5;return false;
  }
  if(Phase==5)
  {
   // A private real monster, positioned at an authored collision key. No GE,
   // execution provenance or original collision geometry is forged here.
   const FKZComboNode* Node=Ability->GetComboDefinition()->FindNode(TEXT("WeakAttack01"));
   const FKZAttackCollisionWindow* Window=Node?Node->AttackWindows.FindByPredicate([](const FKZAttackCollisionWindow& W){return W.HPDamage>0.f && !W.Keys.IsEmpty();}):nullptr;
   UClass* TargetClass=LoadClass<AKZMonster>(nullptr,TEXT("/Game/Bluprints/Monsters/BP_Monster_Swordsman.BP_Monster_Swordsman_C"));
   if(!Test->TestTrue(TEXT("Natural fixture uses the actual monster archetype and authored attack key"),Node && Window && TargetClass)) return Finish();
   Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorTransform(SavedTransform,false,nullptr,ETeleportType::TeleportPhysics);
   const FKZAttackCollisionKey& Key=Window->Keys[0];
   FTransform TargetTransform=FTransform(Key.Rotation,Key.Center)*Node->CollisionToActor*SavedTransform;
   TargetTransform.SetRotation(FQuat::Identity);TargetTransform.SetScale3D(FVector::OneVector);
   Target=Player->GetWorld()->SpawnActorDeferred<AKZMonster>(TargetClass,TargetTransform,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
   if(!Test->TestTrue(TEXT("Private natural-hit monster spawned"),Target.IsValid())) return Finish();
   Target->AutoPossessAI=EAutoPossessAI::Disabled;Target->AutoPossessPlayer=EAutoReceiveInput::Disabled;Target->FinishSpawning(TargetTransform);
   TargetController=Cast<AKZMonsterAIController>(Target->GetController());
   if(TargetController.IsValid())
   { TargetController->StopMovement();TargetController->GetStateTreeComponent()->StopLogic(TEXT("Private CombatEffect fixture"));if(auto* Perception=TargetController->GetPerceptionComponent()) Perception->Deactivate();TargetController->SetActorTickEnabled(false); }
   Target->GetCharacterMovement()->DisableMovement();Target->GetMesh()->bPauseAnims=true;
   Target->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Target->GetCapsuleComponent()->SetCollisionObjectType(ECC_Pawn);Target->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
   TargetASC=Cast<UKZAbilitySystemComponent>(Target->GetAbilitySystemComponent());
   if(!Test->TestTrue(TEXT("Real monster owns its initialized ASC"),TargetASC.IsValid())) return Finish();
   Cancel(TargetASC.Get());float Headroom=TargetASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute());
   for(const FKZAttackCollisionWindow& W:Node->AttackWindows) Headroom+=FMath::Max(W.HPDamage,0.f);
   TargetASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),Headroom);TargetASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),Headroom);TargetHP=Headroom;
   Phase=6;return false; // Let actual archetype initialization complete.
  }
  if(Phase==6)
  {
   const FKZComboNode* Node=Ability->GetComboDefinition()->FindNode(TEXT("WeakAttack01"));Montage=Node->Montage;
   ConditionalIds.Reset();Seen.Reset();ConfirmedDamage=0;Before.Reset();
   for(TObjectIterator<UParticleSystemComponent> It;It;++It) if(It->GetWorld()==Player->GetWorld()) Before.Add(FObjectKey(*It));
   float Start=0.f,End=0.f;Montage->GetSectionStartAndEndTime(Montage->GetSectionIndex(Node->SectionName),Start,End);
   for(const FAnimNotifyEvent& Event:Montage->Notifies)
    if(const auto* Parent=Cast<UKZAnimNotify_CombatEffect>(Event.Notify.Get());Parent && Event.GetTime()>=Start && Event.GetTime()<End)
    {
     const auto Collect=[this](const UKZAnimNotify_CombatEffect* E){if(E && !E->bEndEvent && E->bOnAttackSuccessed && !E->EventId.IsNone() && (E->ParticleTemplate || !E->SurfaceRoutes.IsEmpty())) ConditionalIds.Add(E->EventId);};
     Collect(Parent);for(const auto& Child:Parent->BatchedEffects) Collect(Child.Get());
    }
   if(!Test->TestTrue(TEXT("Weak01 has actual authored conditional Cascade feedback"),!ConditionalIds.IsEmpty())) return Finish();
   EntryProperty->SetPropertyValue_InContainer(Ability.Get(),TEXT("WeakAttack01"));Refill(ASC.Get());Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
   if(!Test->TestTrue(TEXT("Natural producer fixture activates real Weak01"),ASC->TryActivateAbility(Handle))) return Finish();
   // Freeze fixture translation only; actual montage, collision query and GE
   // producer run normally. This does not claim original movement/input parity.
   Player->GetCharacterMovement()->DisableMovement();NodeDeadline=Player->GetWorld()->GetTimeSeconds()+Montage->GetPlayLength()+5.;Phase=7;return false;
  }
  if(Phase==7)
  {
   for(TObjectIterator<UParticleSystemComponent> It;It;++It)
    if(IsValid(*It) && It->GetWorld()==Player->GetWorld() && !Before.Contains(FObjectKey(*It)) && It->ComponentHasTag(TEXT("KZCombatEffect")))
     for(FName Id:ConditionalIds) if(It->ComponentHasTag(Id)) Seen.Add(Id);
   if(Ability->IsActive())
   { if(Player->GetWorld()->GetTimeSeconds()>NodeDeadline) {Test->AddError(TEXT("Natural-hit attack did not finish"));return Finish();}return false; }
   const float AfterHP=TargetASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
   Test->TestTrue(TEXT("Authored native collision applies actual HP damage to real monster"),AfterHP<TargetHP);
   Test->TestTrue(TEXT("Actual collision producer delivers confirmed provenance"),ConfirmedDamage>0);
   Test->TestTrue(TEXT("Authored conditional feedback follows actual confirmed hit, including an earlier hit"),!Seen.IsEmpty());
   Test->AddInfo(FString::Printf(TEXT("CombatEffect NaturalHit Monster=%s HPBefore=%.3f HPAfter=%.3f ConfirmedDamage=%d ConditionalEvents=%d; stationary private target/translation fixture, no synthetic execution or input parity claim"),*Target->GetClass()->GetPathName(),TargetHP,AfterHP,ConfirmedDamage,Seen.Num()));
   Phase=8;return false;
  }
  if(Phase==8)
  {
   if(BrutalCase==5) return Finish();
   Cancel(ASC.Get());ResetTarget();
   Player->GetCharacterMovement()->SetMovementMode(SavedMovement,SavedCustomMovement);
   Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorTransform(SavedTransform,false,nullptr,ETeleportType::TeleportPhysics);
   UClass* TargetClass=LoadClass<AKZMonster>(nullptr,TEXT("/Game/Bluprints/Monsters/BP_Monster_Swordsman.BP_Monster_Swordsman_C"));
   if(!Test->TestNotNull(TEXT("Brutal uses the actual Swordsman archetype"),TargetClass)) return Finish();
   const AKZMonster* CDO=TargetClass->GetDefaultObject<AKZMonster>();
   const UKZCharacterDefinitionData* Authored=LoadObject<UKZCharacterDefinitionData>(nullptr,TEXT("/Game/Monsters/Swordsman/Data/DA_Character_Swordsman"));
   if(!Test->TestNotNull(TEXT("Brutal authored Definition is available"),Authored)) return Finish();
   const auto& Original=Authored->GetMonsterStaminaSettings();
   Test->TestEqual(TEXT("Product user-authored Brutal damage50 remains unchanged"),Original.BrutalHPDamage,50.f);
   if(!bSavedProductBrutalDamage) { SavedProductBrutalDamage=Original.BrutalHPDamage;bSavedProductBrutalDamage=true; }
   Test->TestEqual(TEXT("Product Brutal damage stays at the current authored value"),Original.BrutalHPDamage,SavedProductBrutalDamage);
   Test->TestTrue(TEXT("Current authored Brutal damage is nonnegative and finite"),FMath::IsFinite(Original.BrutalHPDamage) && Original.BrutalHPDamage>=0.f);
   FTransform Transform=SavedTransform;FVector Anchor=SavedTransform.GetLocation()+SavedTransform.GetRotation().GetForwardVector().GetSafeNormal2D()*Original.BrutalAttackRange;
   Anchor.Z+=CDO->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   Transform.SetLocation(Anchor);Transform.SetRotation(FRotator(0.f,SavedTransform.Rotator().Yaw+180.f,0.f).Quaternion());Transform.SetScale3D(FVector::OneVector);
   FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   Target=Player->GetWorld()->SpawnActor<AKZMonster>(TargetClass,Transform,Spawn);
   if(!Test->TestTrue(TEXT("Brutal victim owns initialized current native ASC and Definition"),Target.IsValid() && Target->GetCharacterDefinition()==Authored && Target->GetMesh()->GetAnimInstance())) return Finish();
   TargetASC=Cast<UKZAbilitySystemComponent>(Target->GetAbilitySystemComponent());
   if(!Test->TestNotNull(TEXT("Brutal victim ASC"),TargetASC.Get())) return Finish();
   if(!Target->GetController()) Target->SpawnDefaultController();TargetController=Cast<AKZMonsterAIController>(Target->GetController());
   if(TargetController.IsValid())
   { TargetController->Tick(0.f);TargetController->StopMovement();TargetController->GetStateTreeComponent()->StopLogic(TEXT("Private Brutal VFX fixture"));if(auto* Perception=TargetController->GetPerceptionComponent()) Perception->Deactivate();TargetController->SetActorTickEnabled(false); }
   TargetASC->CancelAllAbilities();TargetASC->ClearComboCommands();Target->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   // Negative cases are transient zero fixtures. Positive/cancel cases consume
   // current product damage (now user-authored50), never replace it with QA tuning.
   const bool bZeroFixture=BrutalCase==0 || BrutalCase==1;
   const bool bPositiveFallback=(BrutalCase==2 || BrutalCase==3) && Original.BrutalHPDamage==0.f;
   BrutalDamageMode=TEXT("authored_product");
   if(bZeroFixture || bPositiveFallback)
   {
    UKZCharacterDefinitionData* Copy=DuplicateObject<UKZCharacterDefinitionData>(Authored,GetTransientPackage());Copy->SetFlags(RF_Transient);
    FStructProperty* SettingsProperty=FindFProperty<FStructProperty>(Copy->GetClass(),TEXT("MonsterStamina"));
    FObjectPropertyBase* DefinitionProperty=FindFProperty<FObjectPropertyBase>(Target->GetClass(),TEXT("CharacterDefinition"));
    if(!Test->TestTrue(TEXT("Damage boundary fixture is limited to a transient Definition and actor pointer"),SettingsProperty && DefinitionProperty)) return Finish();
    SettingsProperty->ContainerPtrToValuePtr<FKZMonsterStaminaSettings>(Copy)->BrutalHPDamage=bZeroFixture?0.f:TargetASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())/16.f;
    DefinitionFixture.Reset(Copy);DefinitionProperty->SetObjectPropertyValue_InContainer(Target.Get(),Copy);
    BrutalDamageMode=bZeroFixture?TEXT("transient_zero_negative"):TEXT("transient_HP_over16_positive_fallback");
   }
   Test->TestEqual(TEXT("Boundary fixtures preserve the saved product Brutal damage"),Authored->GetMonsterStaminaSettings().BrutalHPDamage,SavedProductBrutalDamage);
   const auto& Settings=Target->GetCharacterDefinition()->GetMonsterStaminaSettings();
   if(BrutalCase==0)
   {
    TMap<FName,int32> Starts,Ends;int32 Particles=0,Decals=0;
    for(UAnimMontage* M:{Settings.BrutalFrontPlayerMontage.Get(),Settings.BrutalBackPlayerMontage.Get()})
     for(const FAnimNotifyEvent& E:M->Notifies) if(const auto* Parent=Cast<UKZAnimNotify_CombatEffect>(E.Notify.Get()))
     {
      const auto Audit=[&](const UKZAnimNotify_CombatEffect* N){if(!N || N->EventId.IsNone()) return;if(N->bEndEvent) ++Ends.FindOrAdd(N->EventId);else {++Starts.FindOrAdd(N->EventId);if(N->DecalMaterial) ++Decals;else ++Particles;Test->TestTrue(TEXT("Brutal source window has a positive exact serialized duration"),N->WindowEndTime>N->WindowStartTime);}};
      Audit(Parent);for(const auto& Child:Parent->BatchedEffects) Audit(Child.Get());
     }
    Test->TestEqual(TEXT("Both Brutal montages contain all original54 windows"),Starts.Num(),54);Test->TestEqual(TEXT("Brutal source particle window count"),Particles,48);Test->TestEqual(TEXT("Brutal source decal window count"),Decals,6);
    for(const auto& Pair:Starts) {Test->TestEqual(TEXT("One source start per Brutal EventId"),Pair.Value,1);Test->TestEqual(TEXT("One source end per Brutal EventId"),Ends.FindRef(Pair.Key),1);}
   }
   FGameplayEffectContextHandle Context=TargetASC->MakeEffectContext();Context.AddInstigator(Player.Get(),Player.Get());
   FGameplayEffectSpecHandle Spend=TargetASC->MakeOutgoingSpec(Settings.DamageEffect,1.f,Context);
   if(!Test->TestTrue(TEXT("Brutal fixture uses the actual authored stamina damage GE"),Spend.IsValid())) return Finish();
   Spend.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),0.f);Spend.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")),-TargetASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()));
   if(!Test->TestTrue(TEXT("Actual damage GE depletes living victim stamina"),TargetASC->ApplyGameplayEffectSpecToSelf(*Spend.Data.Get()).WasSuccessfullyApplied())) return Finish();
   NodeDeadline=Player->GetWorld()->GetTimeSeconds()+Settings.ExhaustionMontage->GetPlayLength()+5.;Phase=9;return false;
  }
  if(Phase==9)
  {
   UKZExhaustionAbility* Exhaustion=Target->GetActiveExhaustionAbility();
   if(!Exhaustion || !Exhaustion->IsAvailableForBrutalAttack())
   { if(Player->GetWorld()->GetTimeSeconds()>NodeDeadline) {Test->AddError(TEXT("Real exhaustion did not become available"));return Finish();}return false; }
   const auto& Settings=Target->GetCharacterDefinition()->GetMonsterStaminaSettings();const bool bBack=BrutalCase==1 || BrutalCase==3;
   const float Height=Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   const float Minimum=FMath::Max(Player->GetCapsuleComponent()->GetScaledCapsuleRadius()+Target->GetCapsuleComponent()->GetScaledCapsuleRadius(),Settings.BrutalAlignmentDistance);
   const float LimitSquared=FMath::Square(Settings.BrutalAttackRange)-FMath::Square(Height);
   if(!Test->TestTrue(TEXT("Live capsules fit the authored Brutal range"),LimitSquared>FMath::Square(Minimum))) return Finish();
   const float Distance=(Minimum+FMath::Sqrt(LimitSquared))/2.f; // QA geometric midpoint, no product threshold.
   FVector Position=Target->GetActorLocation()+Target->GetActorForwardVector()*(bBack?-Distance:Distance);Position.Z+=Height;
   Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorLocationAndRotation(Position,(Target->GetActorLocation()-Position).GetSafeNormal2D().Rotation(),false,nullptr,ETeleportType::TeleportPhysics);
   Montage=bBack?Settings.BrutalBackPlayerMontage.Get():Settings.BrutalFrontPlayerMontage.Get();BrutalHPBefore=TargetASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());CandidateIds.Reset();ConditionalIds.Reset();Seen.Reset();BrutalConditionalSeen.Reset();Before.Reset();BrutalDefinitions.Reset();
   for(const FAnimNotifyEvent& Event:Montage->Notifies) if(const auto* Parent=Cast<UKZAnimNotify_CombatEffect>(Event.Notify.Get()))
   {
    const auto Collect=[this](const UKZAnimNotify_CombatEffect* E){if(!E || E->bEndEvent || E->EventId.IsNone()) return;CandidateIds.Add(E->EventId);BrutalDefinitions.Add(E->EventId,E);if(E->bOnAttackSuccessed) ConditionalIds.Add(E->EventId);};Collect(Parent);for(const auto& Child:Parent->BatchedEffects) Collect(Child.Get());
   }
   for(TObjectIterator<USceneComponent> It;It;++It) if(It->GetWorld()==Player->GetWorld() && It->ComponentHasTag(TEXT("KZCombatEffect"))) Before.Add(FObjectKey(*It));
   BrutalHandle={};for(const auto& Spec:ASC->GetActivatableAbilities()) if(Cast<UKZBrutalAttackAbility>(Spec.Ability)) {BrutalHandle=Spec.Handle;Test->TestTrue(TEXT("Brutal is the real granted B consumer"),Spec.GetDynamicSpecSourceTags().HasTagExact(KZGameplayTags::Input_Action_B));}
   ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_B);ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_B);
   FGameplayAbilitySpec* Spec=ASC->FindAbilitySpecFromHandle(BrutalHandle);Brutal=Spec?Cast<UKZBrutalAttackAbility>(Spec->GetPrimaryInstance()):nullptr;
   if(!Test->TestTrue(TEXT("Actual B dispatch selects correct front/back montage and paired victim"),Spec && Spec->IsActive() && Brutal.IsValid() && Brutal->GetCurrentMontage()==Montage.Get() && Exhaustion->HasBrutalPartner())) return Finish();
   NodeDeadline=Player->GetWorld()->GetTimeSeconds()+Montage->GetPlayLength()+Settings.ExhaustionMontage->GetPlayLength()+Settings.BrutalFrontVictimMontage->GetPlayLength()+Settings.BrutalBackVictimMontage->GetPlayLength()+5.;Phase=10;return false;
  }
  if(Phase==10)
  {
   for(TObjectIterator<USceneComponent> It;It;++It)
    if(IsValid(*It) && It->GetWorld()==Player->GetWorld() && !Before.Contains(FObjectKey(*It)) && It->ComponentHasTag(TEXT("KZCombatEffect")))
     for(FName Id:CandidateIds) if(It->ComponentHasTag(Id))
     {
      Seen.Add(Id);if(ConditionalIds.Contains(Id)) BrutalConditionalSeen.Add(Id);
      const UKZAnimNotify_CombatEffect* E=BrutalDefinitions.FindRef(Id);
      if(auto* ObservedParticle=Cast<UParticleSystemComponent>(*It)) ObserveTransform(ObservedParticle,E);
      if(auto* Particle=Cast<UParticleSystemComponent>(*It);E && Particle && Particle->GetAttachParent()==Player->GetMesh())
      {
       Test->TestTrue(TEXT("Brutal attached particle preserves source world-centimetre scale"),Particle->GetComponentScale().Equals(E->Scale3D,KINDA_SMALL_NUMBER));
       if(E->RelativeLocationRandomMin==E->RelativeLocationRandomMax && E->RelativeRotationRandomMin==E->RelativeRotationRandomMax)
       {
        FTransform Local(E->RelativeRotation+E->RelativeRotationRandomMin,E->RelativeLocation+E->RelativeLocationRandomMin,FVector::OneVector);if(E->bUseSourceCorrection) Local=Local*E->SourceCorrectionTransform.Inverse();
        const FName Socket=E->bUseSourceCorrection?E->CorrectionBoneName:E->SourceSocket;const FVector SocketScale=Player->GetMesh()->GetSocketTransform(Socket,RTS_World).GetScale3D();
        Test->TestTrue(TEXT("Brutal attached source offset remains centimetres after socket-scale removal"),(Particle->GetRelativeLocation()*SocketScale).Equals(Local.GetLocation(),KINDA_SMALL_NUMBER));
       }
      }
     }
   const auto& Settings=Target->GetCharacterDefinition()->GetMonsterStaminaSettings();
   if(Settings.BrutalHPDamage==0.f) Test->TestTrue(TEXT("HP0 paired reactions never invent conditional blood"),BrutalConditionalSeen.IsEmpty());
   if(BrutalCase==4 && !Seen.IsEmpty() && Brutal->IsActive())
   {
    const auto* Instance=Player->GetMesh()->GetAnimInstance()->GetActiveInstanceForMontage(Montage.Get());
    if(!Test->TestNotNull(TEXT("Cancel/isolation uses the actual Brutal montage instance"),Instance)) return Finish();
    TStrongObjectPtr<UKZAnimNotify_CombatEffect> Fixture(DuplicateObject<UKZAnimNotify_CombatEffect>(Direct.Get(),GetTransientPackage()));Fixture->EventId=TEXT("KZFX_QA_BrutalIsolation");Fixture->bOnAttackSuccessed=false;Fixture->bEndEvent=false;Fixture->bDestroyOnAnimEnd=true;
    FAnimNotifyEvent Event;Event.Notify=Fixture.Get();
    FBranchingPointNotifyPayload WrongId(Player->GetMesh(),Montage.Get(),&Event,Instance->GetInstanceID()+1);Player->GetMesh()->GetAnimInstance()->OnPlayMontageNotifyBegin.Broadcast(TEXT("KZCombatEffect"),WrongId);
    Test->TestEqual(TEXT("Brutal rejects an obsolete/different montage instance"),Count(Player.Get(),Fixture->EventId),0);
    FBranchingPointNotifyPayload WrongAvatar(Other->GetMesh(),Montage.Get(),&Event,Instance->GetInstanceID());Player->GetMesh()->GetAnimInstance()->OnPlayMontageNotifyBegin.Broadcast(TEXT("KZCombatEffect"),WrongAvatar);
    Test->TestEqual(TEXT("Brutal rejects another avatar's mesh"),Count(Player.Get(),Fixture->EventId),0);
    FBranchingPointNotifyPayload Valid(Player->GetMesh(),Montage.Get(),&Event,Instance->GetInstanceID());Player->GetMesh()->GetAnimInstance()->OnPlayMontageNotifyBegin.Broadcast(TEXT("KZCombatEffect"),Valid);
    Test->TestEqual(TEXT("Brutal current activation owns the actual attached fixture"),Count(Player.Get(),Fixture->EventId),1);Cancel(ASC.Get());
    Test->TestEqual(TEXT("Brutal cancel clears its explicit animation-lifetime resource"),Count(Player.Get(),Fixture->EventId),0);Player->GetMesh()->GetAnimInstance()->OnPlayMontageNotifyBegin.Broadcast(TEXT("KZCombatEffect"),Valid);
    Test->TestEqual(TEXT("Canceled Brutal ignores late source marker"),Count(Player.Get(),Fixture->EventId),0);Test->TestTrue(TEXT("Cancel did not modify the other avatar"),Other.IsValid());
    Test->AddInfo(TEXT("CombatEffect Brutal cancel/current-instance/wrong-avatar/late-marker cleanup passed"));++BrutalCase;Phase=8;return false;
   }
   if(Brutal->IsActive() || Target->GetActiveExhaustionAbility())
   {if(Player->GetWorld()->GetTimeSeconds()>NodeDeadline){Test->AddError(TEXT("Natural Brutal pair did not complete"));return Finish();}return false;}
   Test->TestTrue(TEXT("Natural front/back B execution produces unconditional source particles"),!Seen.IsEmpty());
   Test->TestTrue(TEXT("Actual paired HP consequence is source configured total"),FMath::IsNearlyEqual(TargetASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),BrutalHPBefore-Settings.BrutalHPDamage,KINDA_SMALL_NUMBER));
   if(Settings.BrutalHPDamage>0.f) Test->TestTrue(TEXT("Accepted negative HP produces source conditional feedback"),!BrutalConditionalSeen.IsEmpty());
   Test->AddInfo(FString::Printf(TEXT("CombatEffect Brutal Case=%d Montage=%s HPBefore=%g HPAfter=%g ConfiguredDamage=%g AuthoredDamage=%g DamageMode=%s SeenEvents=%d ConditionalEvents=%d; source original first-hit BattleEffectIndex linkage unknown"),BrutalCase,*GetNameSafe(Montage.Get()),BrutalHPBefore,TargetASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),Settings.BrutalHPDamage,SavedProductBrutalDamage,*BrutalDamageMode,Seen.Num(),BrutalConditionalSeen.Num()));
   ++BrutalCase;Phase=8;return false;
  }
  return false;
 }
private:
 void ObserveTransform(UParticleSystemComponent* Particle,const UKZAnimNotify_CombatEffect* Effect)
 {
  if(TransformObservationPath.IsEmpty() || !IsValid(Particle) || !IsValid(Effect) ||
   !(Effect->bUseSourceCorrection || Effect->bOnlyStartAttach ||
    (Effect->ParticleTemplate && Effect->ParticleTemplate->GetFName()==FName(TEXT("FP_Kazan_Gsword_Impact_stone_01"))))) return;
  int32& Samples=TransformObservationCounts.FindOrAdd(Effect->EventId);
  if(Samples>=4) return; // Technical QA bound: first four observed frames/event, no gameplay setting.
  ++Samples;
  const auto Quote=[](FString Value)
  { Value.ReplaceInline(TEXT("\\"),TEXT("\\\\"));Value.ReplaceInline(TEXT("\""),TEXT("\\\""));Value.ReplaceInline(TEXT("\n"),TEXT("\\n"));Value.ReplaceInline(TEXT("\r"),TEXT("\\r"));return TEXT("\"")+Value+TEXT("\""); };
  const auto Vector=[](const FVector& V){return FString::Printf(TEXT("[%.17g,%.17g,%.17g]"),V.X,V.Y,V.Z);};
  const auto Transform=[&Vector](const FTransform& T)
  { const FQuat Q=T.GetRotation();return FString::Printf(TEXT("{\"translation_cm\":%s,\"quaternion_xyzw\":[%.17g,%.17g,%.17g,%.17g],\"scale\":%s}"),*Vector(T.GetLocation()),Q.X,Q.Y,Q.Z,Q.W,*Vector(T.GetScale3D())); };
  USkeletalMeshComponent* Mesh=Player->GetMesh();UAnimInstance* Anim=Mesh->GetAnimInstance();
  const FAnimMontageInstance* Instance=Anim?Anim->GetActiveInstanceForMontage(Montage.Get()):nullptr;
  const FName Anchor=Effect->bUseSourceCorrection?Effect->CorrectionBoneName:Effect->SourceSocket;
  FString Line=TEXT("{\"event_id\":")+Quote(Effect->EventId.ToString());
  Line+=TEXT(",\"montage\":")+Quote(GetPathNameSafe(Montage.Get()))+TEXT(",\"section\":")+Quote(Anim?Anim->Montage_GetCurrentSection(Montage.Get()).ToString():TEXT("None"));
  Line+=FString::Printf(TEXT(",\"world_seconds\":%.9g,\"montage_seconds\":%.9g,\"window_start_seconds\":%.9g,\"window_end_seconds\":%.9g,\"montage_instance\":%d,\"observed_frame\":%d,\"active_particles\":%d"),Player->GetWorld()->GetTimeSeconds(),Anim?Anim->Montage_GetPosition(Montage.Get()):0.f,Effect->WindowStartTime,Effect->WindowEndTime,Instance?Instance->GetInstanceID():INDEX_NONE,Samples,Particle->GetNumActiveParticles());
  Line+=TEXT(",\"component\":")+Quote(Particle->GetPathName())+TEXT(",\"template\":")+Quote(GetPathNameSafe(Particle->Template));
  Line+=TEXT(",\"source_package\":")+Quote(Effect->SourcePackage)+TEXT(",\"source_field\":")+Quote(Effect->SourceField);
  Line+=TEXT(",\"source_socket\":")+Quote(Effect->SourceSocket.ToString())+TEXT(",\"correction_bone\":")+Quote(Effect->CorrectionBoneName.ToString());
  Line+=TEXT(",\"attach_parent\":")+Quote(GetPathNameSafe(Particle->GetAttachParent()))+TEXT(",\"attach_socket\":")+Quote(Particle->GetAttachSocketName().ToString());
  Line+=FString::Printf(TEXT(",\"source_attached\":%s,\"source_only_start_attach\":%s,\"source_floor\":%s,\"source_correction\":%s,\"absolute_location\":%s,\"absolute_rotation\":%s,\"absolute_scale\":%s,\"grounded\":%s"),Effect->bAttached?TEXT("true"):TEXT("false"),Effect->bOnlyStartAttach?TEXT("true"):TEXT("false"),Effect->bSpawnOnFloor?TEXT("true"):TEXT("false"),Effect->bUseSourceCorrection?TEXT("true"):TEXT("false"),Particle->IsUsingAbsoluteLocation()?TEXT("true"):TEXT("false"),Particle->IsUsingAbsoluteRotation()?TEXT("true"):TEXT("false"),Particle->IsUsingAbsoluteScale()?TEXT("true"):TEXT("false"),Player->GetCharacterMovement()->IsMovingOnGround()?TEXT("true"):TEXT("false"));
  const auto AddTransform=[&Line,&Transform](const TCHAR* Name,const FTransform& T){Line+=TEXT(",\"")+FString(Name)+TEXT("\":")+Transform(T);};
  AddTransform(TEXT("component_world"),Particle->GetComponentTransform());
  AddTransform(TEXT("component_relative"),Particle->GetRelativeTransform());
  AddTransform(TEXT("mesh_world"),Mesh->GetComponentTransform());
  AddTransform(TEXT("actor_world"),Player->GetActorTransform());
  AddTransform(TEXT("source_socket_world"),Mesh->GetSocketTransform(Effect->SourceSocket,RTS_World));
  AddTransform(TEXT("anchor_socket_world"),Mesh->GetSocketTransform(Anchor,RTS_World));
  AddTransform(TEXT("weapon_l_world"),Mesh->GetSocketTransform(TEXT("Weapon_L"),RTS_World));
  AddTransform(TEXT("weapon_r_world"),Mesh->GetSocketTransform(TEXT("Weapon_R"),RTS_World));
  AddTransform(TEXT("source_correction_transform"),Effect->SourceCorrectionTransform);
  AddTransform(TEXT("source_effect_local"),FTransform(Effect->RelativeRotation,Effect->RelativeLocation,Effect->Scale3D));
  Line+=TEXT("}\n");
  if(!FFileHelper::SaveStringToFile(Line,*TransformObservationPath,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append))
  { Test->AddError(TEXT("Optional transform QA JSONL destination could not be appended"));TransformObservationPath.Reset(); }
 }
 void ResetTarget()
 {
  if(TargetASC.IsValid()) TargetASC->CancelAllAbilities();if(Target.IsValid()) Target->Destroy();if(TargetController.IsValid()) TargetController->Destroy();TargetASC.Reset();Target.Reset();TargetController.Reset();DefinitionFixture.Reset();
 }
 FGameplayAbilitySpecHandle FindWeak(UKZAbilitySystemComponent* Component)
 { for(const FGameplayAbilitySpec& Spec:Component->GetActivatableAbilities()) if(const auto* A=Cast<UKZComboActionAbility>(Spec.Ability);A && A->GetEntryNodeId()==FName(TEXT("WeakAttack01"))) return Spec.Handle;return {}; }
 void Refill(UKZAbilitySystemComponent* Component)
 { Component->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),Component->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute())); }
 void Cancel(UKZAbilitySystemComponent* Component)
 { if(!Component) return;FGameplayTagContainer Tags;Tags.AddTag(KZGameplayTags::Ability_Action);Component->CancelAbilities(&Tags);Component->ClearComboCommands(); }
 int32 InstanceId(AKZPlayer* Avatar,UKZComboActionAbility* A)
 { auto* I=Avatar->GetMesh()->GetAnimInstance()->GetActiveInstanceForMontage(A->GetCurrentMontage());return I?I->GetInstanceID():INDEX_NONE; }
 void Emit(AKZPlayer* Avatar,UKZComboActionAbility* A,UKZAnimNotify_CombatEffect* Effect,bool bEnd=false,int32 Id=INDEX_NONE,USkeletalMeshComponent* PayloadMesh=nullptr)
 { Effect->bEndEvent=bEnd;FAnimNotifyEvent Event;Event.Notify=Effect;FBranchingPointNotifyPayload Payload(PayloadMesh?PayloadMesh:Avatar->GetMesh(),A->GetCurrentMontage(),&Event,Id==INDEX_NONE?InstanceId(Avatar,A):Id);Avatar->GetMesh()->GetAnimInstance()->OnPlayMontageNotifyBegin.Broadcast(TEXT("KZCombatEffect"),Payload); }
 int32 Count(AKZPlayer* Avatar,FName Id)
 { int32 N=0;for(TObjectIterator<UParticleSystemComponent> It;It;++It) if(IsValid(*It) && It->GetWorld()==Avatar->GetWorld() && It->GetAttachParent()==Avatar->GetMesh() && It->ComponentHasTag(Id)) ++N;return N; }
 void ApplyFixture(UObject* Source,float Delta)
 {
  UGameplayEffect* Effect=NewObject<UGameplayEffect>(GetTransientPackage());Effect->DurationPolicy=EGameplayEffectDurationType::Instant;
  FSetByCallerFloat Caller;Caller.DataName=TEXT("KZAttackHPDamage");
  FGameplayModifierInfo Modifier;Modifier.Attribute=UKZAttributeSet::GetHPAttribute();Modifier.ModifierOp=EGameplayModOp::Additive;Modifier.ModifierMagnitude=FGameplayEffectModifierMagnitude(Caller);Effect->Modifiers.Add(Modifier);
  FGameplayEffectContextHandle Context=ASC->MakeEffectContext();Context.AddSourceObject(Source);
  FGameplayEffectSpec Spec(Effect,Context,1.f);Spec.SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),Delta);
  ASC->ApplyGameplayEffectSpecToTarget(Spec,OtherASC.Get());
 }
 bool Finish() { Cleanup();return true; }
 void Cleanup()
 {
  if(bCleaned) return;bCleaned=true;
  if(ASC.IsValid()) { if(DamageDelegate.IsValid()) ASC->OnGameplayEffectAppliedDelegateToTarget.Remove(DamageDelegate);Cancel(ASC.Get());ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),SavedHP);ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),SavedStamina); }
  if(bSavedEntry && Ability.IsValid() && EntryProperty) EntryProperty->SetPropertyValue_InContainer(Ability.Get(),SavedEntry);
  if(OtherASC.IsValid()) Cancel(OtherASC.Get());if(Other.IsValid()) Other->Destroy();
  ResetTarget();
  if(Player.IsValid()) { Player->GetMesh()->VisibilityBasedAnimTickOption=SavedTick;Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorTransform(SavedTransform,false,nullptr,ETeleportType::TeleportPhysics);Player->GetCharacterMovement()->SetMovementMode(SavedMovement,SavedCustomMovement); }
 }
 FString TransformObservationPath;TMap<FName,int32> TransformObservationCounts;TMap<FName,const UKZAnimNotify_CombatEffect*> ObservationDefinitions;
 FString BrutalDamageMode;float SavedProductBrutalDamage=0.f;bool bSavedProductBrutalDamage=false;
 FAutomationTestBase* Test;
 TWeakObjectPtr<AKZPlayer> Player,Other;
 TWeakObjectPtr<AKZMonster> Target;TWeakObjectPtr<AKZMonsterAIController> TargetController;TWeakObjectPtr<UKZAbilitySystemComponent> TargetASC;float TargetHP=0.f;
 TWeakObjectPtr<UKZAbilitySystemComponent> ASC,OtherASC;
 TWeakObjectPtr<UKZComboActionAbility> Ability,OtherAbility;
 TWeakObjectPtr<UKZBrutalAttackAbility> Brutal;FGameplayAbilitySpecHandle BrutalHandle;TStrongObjectPtr<UKZCharacterDefinitionData> DefinitionFixture;
 TMap<FName,const UKZAnimNotify_CombatEffect*> BrutalDefinitions;TSet<FName> BrutalConditionalSeen;int32 BrutalCase=0;float BrutalHPBefore=0.f;
 TWeakObjectPtr<UAnimMontage> Montage;
 TWeakObjectPtr<UParticleSystem> Template;
 TStrongObjectPtr<UKZAnimNotify_CombatEffect> Direct,Conditional;
 FGameplayAbilitySpecHandle Handle,OtherHandle;FNameProperty* EntryProperty=nullptr;FName SavedEntry;FDelegateHandle DamageDelegate;
 FTransform SavedTransform;EVisibilityBasedAnimTickOption SavedTick;EMovementMode SavedMovement=MOVE_None;uint8 SavedCustomMovement=0;float SavedHP=0,SavedStamina=0;
 TSet<FObjectKey> Before;TSet<FName> CandidateIds,ConditionalIds,Seen,ExpectedSections,SeenSections;
 double Deadline,NodeDeadline=0.;int32 Phase=0,NodeIndex=0,ConfirmedDamage=0;bool bCleaned=false,bSavedEntry=false;
};

class FWaitForCombatEffectPIE : public IAutomationLatentCommand
{
public:
 explicit FWaitForCombatEffectPIE(FAutomationTestBase* InTest):Test(InTest),Deadline(FPlatformTime::Seconds()+60.) {}
 bool Update() override
 {
  for(const FWorldContext& Context:GEngine->GetWorldContexts())
   if(Context.WorldType==EWorldType::PIE && Context.World() && Context.World()->HasBegunPlay())
    for(TActorIterator<AKZPlayer> It(Context.World());It;++It)
     if(It->IsPlayerControlled() && It->GetCharacterMovement()->IsMovingOnGround() && It->GetMesh()->GetAnimInstance())
     { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FCombatEffectPIE>(Test,*It));return true; }
  if(FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Start task-owned HeinMach PIE after CombatEffect Test Started."));return true; }return false;
 }
private:FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatEffectPIETest,"Khazan.CombatEffect.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZCombatEffectPIETest::RunTest(const FString& Parameters)
{
 // Count only saved null-class/InputTag None baseline rows. A missing Ability
 // for a real input remains a failure; no generic startup errors are suppressed.
 const auto* Definition=LoadObject<UKZCharacterDefinitionData>(nullptr,TEXT("/Game/Data/Character/DA_CharacterDefinition_Player.DA_CharacterDefinition_Player"));
 if(!TestNotNull(TEXT("Saved player definition loads before expected startup-log census"),Definition)) return false;
 int32 BlankGrantCount=0;
 for(const FKZInitialAbilityGrant& Grant:Definition->GetInitialAbilityGrants())
  if(!Grant.AbilityClass)
  {
   if(Grant.InputTag!=FGameplayTag::EmptyTag) {AddError(FString::Printf(TEXT("Saved player grant has no AbilityClass for nonempty InputTag: %s"),*Grant.InputTag.ToString()));return false;}
   ++BlankGrantCount;
  }
 if(BlankGrantCount>0) AddExpectedError(TEXT("BP_Player_C_0 has an InitialAbilityGrant with no AbilityClass in DA_CharacterDefinition_Player (InputTag: None)."),EAutomationExpectedErrorFlags::Contains,BlankGrantCount,false);
 AddInfo(FString::Printf(TEXT("Saved player blank startup grants expected exactly=%d; definition unchanged"),BlankGrantCount));
 FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForCombatEffectPIE>(this));return true;
}
#endif
