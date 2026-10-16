// Development-only real saved-asset integration. No saves, gameplay hit fabrication, or AI patterns added.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "AI/KZMonsterAIController.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifyQueue.h"
#include "Animation/AnimNotifyEndDataContext.h"
#include "Animation/AnimationInstanceScope.h"
#include "Attribute/KZAttributeSet.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Environment/KZSnowDeformation.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KZGameplayTags.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "HAL/PlatformMisc.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "ImageUtils.h"
#include "UObject/ObjectKey.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectIterator.h"

namespace
{
const TCHAR* VisualFamilies[] = {TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
struct FVisualClipCase { FString Asset,Family,Category; int32 Expected=0; bool bCapture=false; };
class FMonsterVisualPIE : public IAutomationLatentCommand
{
public:
 FMonsterVisualPIE(FAutomationTestBase* InTest,AKZPlayer* InPlayer):Test(InTest),Player(InPlayer),Deadline(FPlatformTime::Seconds()+710.)
 { HP=InPlayer->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());SavedPlayerTransform=InPlayer->GetActorTransform(); PostTick=FWorldDelegates::OnWorldPostActorTick.AddRaw(this,&FMonsterVisualPIE::Observe); }
 ~FMonsterVisualPIE() override { Cleanup(); }
 bool Update() override
 {
  if(!Player.IsValid() || FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("MonsterVisual PIE exceeded710s or lost actual player"));return Finish(); }
  UWorld* World=Player->GetWorld();float Now=World->GetTimeSeconds();
  if(Phase==0)
  {
   FString TSV;const FString Path=FPaths::ProjectSavedDir()/TEXT("ImportReports/MonsterVFX_20261008/NativePlaybackCases.tsv");
   if(!Test->TestTrue(TEXT("Frozen original-derived native playback inventory exists"),FFileHelper::LoadFileToString(TSV,*Path))) return Finish();
   TArray<FString> Lines;TSV.ParseIntoArrayLines(Lines);
   for(int32 I=1;I<Lines.Num();++I) {TArray<FString> Columns;Lines[I].ParseIntoArray(Columns,TEXT("\t"),false);if(Columns.Num()!=5) {Test->AddError(TEXT("Playback TSV schema changed"));return Finish();} FVisualClipCase C;C.Asset=Columns[0];C.Family=Columns[1];C.Category=Columns[2];C.Expected=FCString::Atoi(*Columns[3]);C.bCapture=Columns[4]==TEXT("1");Cases.Add(C);}
   if(!Test->TestTrue(TEXT("Native census covers all857 current original/gameplay aliases"),Cases.Num()==857)) return Finish();
   if(!bHumanOnly) for(const FVisualClipCase& C:Cases)
   {
    UAnimSequence* Sequence=LoadObject<UAnimSequence>(nullptr,*C.Asset);
    if(!Test->TestNotNull(*FString::Printf(TEXT("Saved sequence loads %s"),*C.Asset),Sequence)) return Finish();
    int32 Count=0,Boundary=0;
    for(const FAnimNotifyEvent& E:Sequence->Notifies) if(const UKZAnimNotifyState_MonsterVisual* State=Cast<UKZAnimNotifyState_MonsterVisual>(E.NotifyStateClass.Get()))
    {
     if(State->bAnimationContextBoundary) {++Boundary;continue;}
     if(State->bSourceCameraShake) continue; // Separate original camera windows are audited by GiantCamera.
     ++Count;
     Test->TestTrue(TEXT("Visual state uses compatible engine-default matching for contextless playback"),(State->NotifyStateBehaviorFlags & uint8(EAnimNotifyStateBehaviorFlags::NoMergeOnConcurrentPlay))==0);
     Test->TestTrue(TEXT("Saved native state duration positive and within actual sequence"),E.GetDuration()>0.f && E.GetTime()>=0.f && E.GetEndTriggerTime()<=Sequence->GetPlayLength()+KINDA_SMALL_NUMBER);
     if(const UKZAnimNotify_CombatEffect* Effect=State->Effect.Get())
     {
      Test->TestTrue(TEXT("Saved source event identity/field/package retained"),!Effect->EventId.IsNone() && !Effect->SourcePackage.IsEmpty() && !Effect->SourceField.IsEmpty());
      Test->TestTrue(TEXT("Original mapped source lifetime valid"),FMath::IsFinite(Effect->WindowStartTime) && Effect->WindowEndTime>Effect->WindowStartTime);
      ConditionalTotal+=Effect->bOnAttackSuccessed?1:0;
      if(!LoopState && Effect->ParticleTemplate && Effect->ParticleTemplate->IsLooping() && !Effect->bOnAttackSuccessed && !Effect->bWinterOnly && !Effect->bSpawnOnFloor) {LoopState=State;LoopSequence=Sequence;LoopSourceOwner.Reset(Sequence);LoopFamily=C.Family;}
      if(Effect->TrailMesh) ++TrailTotal;
      if(Effect->DecalMaterial) ++DecalTotal;
      for(const auto& Route:Effect->SurfaceRoutes)
      {
       if(Route.bSuppressParticle) Test->TestNull(TEXT("Source null particle route stays explicitly suppressed"),Route.ParticleTemplate.Get());
       if(Route.bSuppressDecal) Test->TestNull(TEXT("Source null decal route stays explicitly suppressed"),Route.DecalMaterial.Get());
       if(Route.DecalMaterial) ++DecalRouteTotal;
       if(!DecalRouteState && Route.DecalMaterial) {DecalRouteState=State;DecalRouteSourceOwner.Reset(Sequence);}
      }
      if(Effect->bUseCorrectionCurves) Test->TestTrue(TEXT("Correction curve has actual source anchor"),Effect->bUseSourceCorrection && !Effect->CorrectionBoneName.IsNone());
     }
     if(!State->ScalarCurveName.IsNone() || !State->VectorParameterName.IsNone()) {++MaterialTotal;if(!MaterialState && C.Family==TEXT("ApesStoneHandElite") && C.Asset.EndsWith(TEXT("/Damage/Damage_FinalBlow")) && State->ScalarCurveName==TEXT("Execution")) {MaterialState=State;MaterialSequence=Sequence;MaterialSourceOwner.Reset(Sequence);}}
     if(C.Family==TEXT("ApesStoneHandElite") && C.Asset.EndsWith(TEXT("/Death/Death_Die_F")) && State->ScalarCurveName==TEXT("Execution")) {DeathMaterialState=State;DeathMaterialSourceOwner.Reset(Sequence);}
    }
    Test->TestEqual(*FString::Printf(TEXT("Exact authored source event readback %s"),*C.Asset),Count,C.Expected);
    Test->TestEqual(TEXT("Only clips with source events get one technical full-span lifetime boundary"),Boundary,C.Expected>0?1:0);
    SourceTotal+=Count;
    if(C.bCapture && C.Expected>0) Captures.Add(C);
   }
   Test->AddInfo(FString::Printf(TEXT("MonsterVisual saved census clips=%d events=%d conditional=%d trail=%d decal=%d material=%d captureCases=%d"),Cases.Num(),SourceTotal,ConditionalTotal,TrailTotal,DecalTotal,MaterialTotal,Captures.Num()));
   const float ExpectedHP[]={100.f,100.f,200.f,200.f,400.f,1000.f};const float ExpectedStamina[]={50.f,50.f,50.f,50.f,100.f,150.f};int32 StatIndex=0;
   for(const TCHAR* Family:VisualFamilies)
   {
    if(bHumanOnly && StatIndex>=4) break;
    FString Package=FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s"),Family);
    UClass* Class=LoadClass<AKZMonster>(nullptr,*(Package+TEXT(".")+FPaths::GetCleanFilename(Package)+TEXT("_C")));
    if(!Test->TestNotNull(TEXT("Actual saved family BP loads"),Class)) return Finish();
    FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AKZMonster* Monster=World->SpawnActor<AKZMonster>(Class,Player->GetActorTransform(),Params);
    if(!Test->TestNotNull(TEXT("Actual saved family BP initializes"),Monster)) return Finish();
    Monsters.Add(Monster);ByFamily.Add(Family,Monster);AnimClasses.Add(Monster->GetMesh()->GetAnimClass());
    StopAI(Monster);Monster->GetAbilitySystemComponent()->CancelAllAbilities();
    Monster->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Monster->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    Monster->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    FVector Staged=Player->GetActorLocation()+Player->GetActorForwardVector()*300.f; // Temporary QA camera staging only.
    Staged.Z=Player->GetActorLocation().Z-Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    Monster->SetActorLocation(Staged,false,nullptr,ETeleportType::TeleportPhysics);
    StagedTransforms.Add(Monster->GetActorTransform());Monster->SetActorHiddenInGame(true);
    Test->TestNotNull(TEXT("Family has real CharacterDefinition"),Monster->GetCharacterDefinition());
    auto* Stats=Monster->GetAbilitySystemComponent();
    Test->TestEqual(TEXT("Actual initialized family HP"),Stats->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),ExpectedHP[StatIndex]);
    Test->TestEqual(TEXT("Actual initialized family maxHP"),Stats->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()),ExpectedHP[StatIndex]);
    Test->TestEqual(TEXT("Actual initialized family Stamina"),Stats->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()),ExpectedStamina[StatIndex]);
    Test->TestEqual(TEXT("Actual initialized family maxStamina"),Stats->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()),ExpectedStamina[StatIndex]);
    Test->TestEqual(TEXT("All6 user-authored Brutal damage50 preserved"),Monster->GetCharacterDefinition()->GetMonsterStaminaSettings().BrutalHPDamage,50.f);++StatIndex;
   }
   Phase=1;return false;
  }
  if(Phase==1)
  {
   if(FamilyIndex>=4) {if(bHumanOnly) return Finish();FamilyIndex=0;Phase=3;return false;}
   AKZMonster* Monster=Monsters[FamilyIndex].Get();auto* ASC=CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
   if(AttackIndex>=Monster->GetAttackAbilities().Num()) {++FamilyIndex;AttackIndex=0;return false;}
   SetCurrent(Monster,FString::Printf(TEXT("MonsterVFX_%s_Ability_%d"),VisualFamilies[FamilyIndex],AttackIndex));
   ASC->CancelAllAbilities();ASC->ClearComboCommands();CandidateIds.Reset();ConditionalIds.Reset();SeenIds.Reset();
   FGameplayAbilitySpec* Spec=ASC->FindAbilitySpecFromClass(Monster->GetAttackAbilities()[AttackIndex]);
   if(!Test->TestNotNull(TEXT("Actual existing human attack Ability granted"),Spec)) return Finish();
   const auto* Ability=Cast<UKZComboActionAbility>(Spec->Ability);
   if(!Test->TestTrue(TEXT("Existing architecture actual attack definition valid"),Ability && Ability->GetComboDefinition())) return Finish();
   ExpectedSections.Reset();SeenSections.Reset();
   const FKZComboNode* Node=Ability->GetComboDefinition()->FindNode(Ability->GetEntryNodeId());TSet<FName> Nodes;
   while(Node && !Nodes.Contains(Node->NodeId))
   {
    Nodes.Add(Node->NodeId);ExpectedSections.Add(Node->SectionName);
    if(Node->Montage) for(const FSlotAnimationTrack& Track:Node->Montage->SlotAnimTracks) for(const FAnimSegment& Segment:Track.AnimTrack.AnimSegments)
      if(const UAnimSequence* Sequence=Cast<UAnimSequence>(Segment.GetAnimReference())) Collect(Sequence);
    Node=Node->CommandEdges.IsEmpty()?nullptr:Ability->GetComboDefinition()->FindNode(Node->CommandEdges[0].TargetNodeId);
   }
   if(!Test->TestTrue(TEXT("Real granted attack starts without fake hit"),ASC->TryActivateAbility(Spec->Handle))) return Finish();
   ActiveHandle=Spec->Handle;ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X,EKZComboCommandPhase::Begin);
   CaseDeadline=Now+30.f;Phase=2;return false;
  }
  if(Phase==2)
  {
   AKZMonster* Monster=Current.Get();auto* ASC=CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
   const FGameplayAbilitySpec* Spec=ASC->FindAbilitySpecFromHandle(ActiveHandle);
   if(UAnimInstance* Anim=Monster->GetMesh()->GetAnimInstance()) if(UAnimMontage* M=Anim->GetCurrentActiveMontage()) SeenSections.Add(Anim->Montage_GetCurrentSection(M));
   if(Spec && Spec->IsActive()) {if(Now>CaseDeadline) {Test->AddError(TEXT("Actual monster attack failed natural completion"));return Finish();}return false;}
   for(FName Section:ExpectedSections) Test->TestTrue(TEXT("Actual attack source section observed"),SeenSections.Contains(Section));
   Test->AddInfo(FString::Printf(TEXT("MonsterVisual actual Ability completed family=%s index=%d sourceEventsObserved=%d"),VisualFamilies[FamilyIndex],AttackIndex,SeenIds.Num()));
   ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X,EKZComboCommandPhase::Cancel);++AttackIndex;++AttackTotal;Phase=1;return false;
  }
  if(Phase==3)
  {
   if(CaptureIndex>=Captures.Num()) {Phase=5;return false;}
   const auto& C=Captures[CaptureIndex];AKZMonster* Monster=ByFamily.FindChecked(C.Family).Get();
   UAnimSequence* Sequence=LoadObject<UAnimSequence>(nullptr,*C.Asset);if(!Sequence) return Finish();
   SetCurrent(Monster,TEXT("MonsterVFX_")+C.Family+TEXT("_")+Sequence->GetName());
   Monster->GetAbilitySystemComponent()->CancelAllAbilities();Monster->ClearMonsterVisuals();
   CandidateIds.Reset();ConditionalIds.Reset();SeenIds.Reset();Collect(Sequence);
   for(const FAnimNotifyEvent& Event:Sequence->Notifies)
    if(const auto* State=Cast<UKZAnimNotifyState_MonsterVisual>(Event.NotifyStateClass.Get()))
     if(State->Effect && State->Effect->bWinterOnly && !WinterFixture.IsValid())
     {
      Test->TestNull(TEXT("Original winter-only breath stays suppressed without a winter owner"),UKZAnimNotify_CombatEffect::SpawnComponent(*State->Effect,Monster->GetMesh()));
      AKZSnowDeformation* Winter=World->SpawnActorDeferred<AKZSnowDeformation>(AKZSnowDeformation::StaticClass(),FTransform::Identity,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
      if(!Test->TestNotNull(TEXT("Winter positive fixture uses the existing presentation owner"),Winter)) return Finish();
      Winter->FieldResolution=128; // QA allocation budget only; no product snow settings are edited.
      Winter->SurfaceTag=TEXT("KZMonsterVisualWinterFixture"); // Do not bind any real level snow materials.
      Winter->FinishSpawning(FTransform::Identity);Winter->SetActorTickEnabled(false);WinterFixture=Winter;
     }
   bLoop=C.Category==TEXT("Idle") || C.Category==TEXT("Locomotion");
   Monster->GetMesh()->PlayAnimation(Sequence,bLoop);CurrentSequence=Sequence;
   CaseEnd=Now+Sequence->GetPlayLength()*(bLoop?2.f:1.f);CaseDeadline=CaseEnd+5.f;Phase=4;return false;
  }
  if(Phase==4)
  {
   if(Now<CaseEnd) return false;
   AKZMonster* Monster=Current.Get();UAnimSingleNodeInstance* Single=Monster->GetMesh()->GetSingleNodeInstance();
   if(!bLoop && Single && Single->IsPlaying() && Now<CaseDeadline) return false;
   Test->TestTrue(TEXT("Representative visual emitted actual source resources or actual material state"),SeenIds.Num()>0 || HasMaterial(CurrentSequence.Get()));
   Test->AddInfo(FString::Printf(TEXT("MonsterVisual Sequence family=%s clip=%s observedEvents=%d loop=%d"),*Captures[CaptureIndex].Family,*GetNameSafe(CurrentSequence.Get()),SeenIds.Num(),bLoop));
   if(Single) Single->SetPlaying(false);Monster->ClearMonsterVisuals();RestoreAnim(Monster);if(WinterFixture.IsValid()) {WinterFixture->Destroy();WinterFixture.Reset();}++CaptureIndex;Phase=3;return false;
  }
  if(Phase==5)
  {
   Test->TestEqual(TEXT("All35 existing human attack patterns completed"),AttackTotal,35);
   BoundaryFixtures();Phase=9;return false;
  }
  if(Phase==6)
  {
   if(FamilyIndex>=Monsters.Num()) {DeathCancellationFixture();return Finish();}
   AKZMonster* Monster=Monsters[FamilyIndex].Get();RestoreAnim(Monster);
   SetCurrent(Monster,FString::Printf(TEXT("MonsterVFX_%s_DeathPresentation"),VisualFamilies[FamilyIndex]));
   if(!Test->TestNotNull(TEXT("All6 authored optional source death montages exist"),Monster->GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage.Get())) return Finish();
   if(FamilyIndex==4) {DeathMaterialBaselines.Reset();for(int32 Slot=0;Slot<Monster->GetMesh()->GetNumMaterials();++Slot) DeathMaterialBaselines.Emplace(Monster->GetMesh()->GetMaterial(Slot));}
   Monster->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),0.f);
   Monster->FinishDeathPresentation();CaseDeadline=Now+Monster->GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage->GetPlayLength()+5.f;
   Phase=7;return false;
  }
  if(Phase==7)
  {
   AKZMonster* Monster=Current.Get();if(!Monster->GetMesh()->bPauseAnims && Now<CaseDeadline) return false;
   Test->TestTrue(TEXT("Real HP death completes source presentation and freezes final pose"),Monster->GetMesh()->bPauseAnims);
   Test->TestTrue(TEXT("Death keeps existing actual HP0 policy"),Monster->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())==0.f);
   if(FamilyIndex==4) {CheckTerminalDeathMaterials(Monster,true);CaseEnd=Now+1.f;Phase=8;return false;} // QA capture dwell only, not gameplay timing.
   ++FamilyIndex;Phase=6;return false;
  }
  if(Phase==8)
  {
   if(Now<CaseEnd) return false;
   AKZMonster* Monster=Current.Get();CheckTerminalDeathMaterials(Monster,false);
   AController* Controller=Monster->GetController();
   if(Test->TestNotNull(TEXT("Frozen source execution corpse still has actual cancellation owner"),Controller)) Controller->UnPossess();
   for(int32 Slot=0;Slot<DeathMaterialBaselines.Num();++Slot) Test->TestEqual(TEXT("UnPossess restores every held death material baseline"),Monster->GetMesh()->GetMaterial(Slot),DeathMaterialBaselines[Slot].Get());
   ++FamilyIndex;Phase=6;return false;
  }
  if(Phase==9)
  {
   if(PairedCase==2) {Player->GetAbilitySystemComponent()->CancelAllAbilities();Player->SetActorTransform(SavedPlayerTransform,false,nullptr,ETeleportType::TeleportPhysics);FamilyIndex=0;Phase=6;return false;}
   Player->GetAbilitySystemComponent()->CancelAllAbilities();Player->SetActorTransform(SavedPlayerTransform,false,nullptr,ETeleportType::TeleportPhysics);
   FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   AKZMonster* Victim=World->SpawnActor<AKZMonster>(Monsters[4]->GetClass(),StagedTransforms[4],P);
   if(!Test->TestNotNull(TEXT("Paired execution uses actual saved Apes BP"),Victim)) return Finish();
   ExtraActor=Victim;StopAI(Victim);Victim->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   Victim->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
   SetCurrent(Victim,FString::Printf(TEXT("MonsterVFX_ApesStoneHandElite_Paired_%s"),PairedCase==0?TEXT("Nonlethal"):TEXT("Lethal")));
   const auto& Settings=Victim->GetCharacterDefinition()->GetMonsterStaminaSettings();auto* ASC=Victim->GetAbilitySystemComponent();
   PairedBaselines.Reset();PairedHeldMaterials.Reset();PairedHeldValues.Reset();
   Test->TestEqual(TEXT("Actual paired Apes body has all five saved material slots"),Victim->GetMesh()->GetNumMaterials(),5);
   for(int32 Slot=0;Slot<Victim->GetMesh()->GetNumMaterials();++Slot)
   {
    auto* MID=Cast<UMaterialInstanceDynamic>(Victim->GetMesh()->GetMaterial(Slot));if(!MID) MID=Victim->GetMesh()->CreateDynamicMaterialInstance(Slot);
    PairedBaselines.Emplace(Victim->GetMesh()->GetMaterial(Slot));PairedHeldMaterials.Add(MID);float Value=0.f;
    Test->TestTrue(TEXT("Actual paired baseline exposes its existing execution uniform"),MID && MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Execution")),Value));PairedHeldValues.Add(Value);
   } // Snapshot the existing MIDs/uniforms; Grapple has no source execution material recipe.
   if(PairedCase==1) ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),Settings.BrutalHPDamage); // QA exact one-hit lethal threshold from current authored damage, no data tuning.
   PairedHPBefore=ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
   FGameplayEffectSpecHandle Spend=ASC->MakeOutgoingSpec(Settings.DamageEffect,1.f,ASC->MakeEffectContext());
   if(!Test->TestTrue(TEXT("Paired source fixture has real stamina damage GE"),Spend.IsValid())) return Finish();
   Spend.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),0.f);Spend.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")),-ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()));
   Test->TestTrue(TEXT("Actual GE depletes paired victim stamina"),ASC->ApplyGameplayEffectSpecToSelf(*Spend.Data.Get()).WasSuccessfullyApplied());
   CaseDeadline=Now+Settings.ExhaustionMontage->GetPlayLength()+5.f;Phase=10;return false;
  }
  if(Phase==10)
  {
   AKZMonster* Victim=Current.Get();auto* Exhaustion=Victim->GetActiveExhaustionAbility();
   if(!Exhaustion || !Exhaustion->IsAvailableForBrutalAttack()) {if(Now>CaseDeadline) {Test->AddError(TEXT("Actual Apes exhaustion did not become available for paired material QA"));return Finish();}return false;}
   const auto& Settings=Victim->GetCharacterDefinition()->GetMonsterStaminaSettings();
   const float Height=Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Victim->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   const float Minimum=FMath::Max(Player->GetCapsuleComponent()->GetScaledCapsuleRadius()+Victim->GetCapsuleComponent()->GetScaledCapsuleRadius(),Settings.BrutalAlignmentDistance);
   const float LimitSquared=FMath::Square(Settings.BrutalAttackRange)-FMath::Square(Height);
   if(!Test->TestTrue(TEXT("Actual Apes capsule fits saved Brutal interaction range"),LimitSquared>FMath::Square(Minimum))) return Finish();
   FVector Position=Victim->GetActorLocation()+Victim->GetActorForwardVector()*((Minimum+FMath::Sqrt(LimitSquared))/2.f);Position.Z+=Height; // QA geometric midpoint.
   Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorLocationAndRotation(Position,(Victim->GetActorLocation()-Position).GetSafeNormal2D().Rotation(),false,nullptr,ETeleportType::TeleportPhysics);
   auto* ASC=Cast<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent());ASC->ClearComboCommands();
   ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_B);ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_B);
   PairedBrutal=nullptr;for(const auto& Spec:ASC->GetActivatableAbilities()) if(Spec.IsActive()) if(auto* B=Cast<UKZBrutalAttackAbility>(Spec.GetPrimaryInstance())) PairedBrutal=B;
   if(!Test->TestTrue(TEXT("Actual granted player Brutal claims actual Apes exhaustion"),PairedBrutal.IsValid() && Exhaustion->HasBrutalPartner())) return Finish();
   CaseDeadline=Now+Settings.BrutalFrontPlayerMontage->GetPlayLength()+Settings.BrutalFrontVictimMontage->GetPlayLength()+Settings.ExhaustionMontage->GetPlayLength()+5.f;
   bPairedReactionSeen=false;Phase=11;return false;
  }
  if(Phase==11)
  {
   AKZMonster* Victim=Current.Get();auto* Exhaustion=Victim->GetActiveExhaustionAbility();
   if(Exhaustion && Exhaustion->HasBrutalPartner() && Victim->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())<PairedHPBefore)
   {
    if(!bPairedReactionSeen)
    {
     UAnimMontage* Actual=Exhaustion->GetCurrentMontage();const auto& Settings=Victim->GetCharacterDefinition()->GetMonsterStaminaSettings();
     Test->TestTrue(TEXT("Actual paired reaction consumes a saved victim montage"),Actual && (Actual==Settings.BrutalFrontVictimMontage || Actual==Settings.BrutalBackVictimMontage));
     CheckPairedSourceRecipes(Actual);
    }
    bPairedReactionSeen=true;
    for(int32 Slot=0;Slot<PairedBaselines.Num();++Slot) Test->TestEqual(TEXT("Actual Grapple pair preserves each existing body material during reaction"),Victim->GetMesh()->GetMaterial(Slot),PairedBaselines[Slot].Get());
   }
   if(UAnimInstance* Anim=Victim->GetMesh()->GetAnimInstance()) Test->TestTrue(TEXT("Actual paired reaction never starts a second ordinary death montage"),!Anim->Montage_IsPlaying(Victim->GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage.Get()));
   if((PairedBrutal.IsValid() && PairedBrutal->IsActive()) || (Exhaustion && Exhaustion->HasBrutalPartner())) {if(Now>CaseDeadline) {Test->AddError(TEXT("Actual paired material execution exceeded saved montage deadline"));return Finish();}return false;}
   Test->TestTrue(TEXT("Real paired source reaction observed after actual authored damage"),bPairedReactionSeen);
   if(PairedCase==0) {Test->TestTrue(TEXT("Nonlethal Apes Brutal keeps actual HP positive"),Victim->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())>0.f);CheckPairedTerminalMaterials(Victim,true);Victim->Destroy();++PairedCase;Phase=9;return false;}
   Test->TestEqual(TEXT("Lethal paired authored damage reaches actual HP0"),Victim->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),0.f);
   Test->TestTrue(TEXT("Lethal completed pair freezes existing victim pose without second death montage"),Victim->GetMesh()->bPauseAnims);
   CheckPairedTerminalMaterials(Victim,true);CaseEnd=Now+1.f;Phase=12;return false; // QA capture dwell only.
  }
  if(Phase==12)
  {
   if(Now<CaseEnd) return false;AKZMonster* Victim=Current.Get();CheckPairedTerminalMaterials(Victim,false);
   if(AController* Controller=Victim->GetController()) Controller->UnPossess();else Test->AddError(TEXT("Completed paired corpse lost real cancellation owner"));
   for(int32 Slot=0;Slot<PairedBaselines.Num();++Slot) Test->TestEqual(TEXT("Paired corpse cancellation restores actual original material slot"),Victim->GetMesh()->GetMaterial(Slot),PairedBaselines[Slot].Get());
   Victim->Destroy();++PairedCase;Phase=9;return false;
  }
  return false;
 }
private:
 void StopAI(AKZMonster* Monster) {if(auto* AI=Cast<AKZMonsterAIController>(Monster->GetController())) {if(AI->GetStateTreeComponent()) AI->GetStateTreeComponent()->StopLogic(TEXT("Owned VFX fixture"));AI->StopMovement();AI->SetActorTickEnabled(false);}}
 void RestoreAnim(AKZMonster* Monster) {int32 I=Monsters.IndexOfByPredicate([Monster](const auto& W){return W.Get()==Monster;});Monster->ClearMonsterVisuals();Monster->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);if(I!=INDEX_NONE) Monster->GetMesh()->SetAnimInstanceClass(AnimClasses[I]);}
 void SetCurrent(AKZMonster* Monster,const FString& Label)
 {
  if(Current.IsValid()) {Current->Tags.Remove(TEXT("KZMonsterVFXCapture"));Current->SetActorHiddenInGame(true);Current->GetAbilitySystemComponent()->CancelAllAbilities();Current->ClearMonsterVisuals();if(UAnimInstance* Anim=Current->GetMesh()->GetAnimInstance()) Anim->Montage_Stop(0.f);}
  Current=Monster;Monster->GetCharacterMovement()->StopMovementImmediately();
  const int32 I=Monsters.IndexOfByPredicate([Monster](const auto& W){return W.Get()==Monster;});
  if(I!=INDEX_NONE) Monster->SetActorTransform(StagedTransforms[I],false,nullptr,ETeleportType::TeleportPhysics);
  Monster->GetCharacterMovement()->SetMovementMode(MOVE_Walking);Monster->SetActorHiddenInGame(false);
  Monster->SetActorLabel(Label);Monster->Tags.AddUnique(TEXT("KZMonsterVFXCapture"));UE_LOG(LogTemp,Display,TEXT("MonsterVisual Capture Label=%s Actor=%s"),*Label,*Monster->GetName());
 }
 void Collect(const UAnimSequence* Sequence) {for(const FAnimNotifyEvent& E:Sequence->Notifies) if(const auto* State=Cast<UKZAnimNotifyState_MonsterVisual>(E.NotifyStateClass.Get())) if(State->Effect) {const auto* Effect=State->Effect.Get();if(!Effect->EventId.IsNone()) {CandidateIds.Add(Effect->EventId);if(Effect->bOnAttackSuccessed) ConditionalIds.Add(Effect->EventId);}}}
 bool HasMaterial(const UAnimSequence* Sequence) const {if(!Sequence) return false;for(const FAnimNotifyEvent& E:Sequence->Notifies) if(const auto* S=Cast<UKZAnimNotifyState_MonsterVisual>(E.NotifyStateClass.Get())) if(!S->ScalarCurveName.IsNone() || !S->VectorParameterName.IsNone() || S->MaterialOverlay) return true;return false;}
 void Observe(UWorld* World,ELevelTick,float)
 {
  if(!Current.IsValid() || World!=Current->GetWorld()) return;
  for(TObjectIterator<USceneComponent> It;It;++It) if(It->GetWorld()==World && It->ComponentHasTag(TEXT("KZCombatEffect")) && It->ComponentHasTag(Current->GetFName()))
   for(FName Id:CandidateIds) if(It->ComponentHasTag(Id)) {SeenIds.Add(Id);if(bHumanOnly)NiagaraFamilies.Add(Current->GetClass()->GetPathName());if(ConditionalIds.Contains(Id) && !ConditionalReported.Contains(Id)) {ConditionalReported.Add(Id);Test->AddError(FString::Printf(TEXT("Conditional source event spawned without actual Monster hit: %s"),*Id.ToString()));}}
  if(bHumanOnly) for(TObjectIterator<UNiagaraComponent> It;It;++It)
   if(It->GetWorld()==World && It->ComponentHasTag(Current->GetFName()) && It->ComponentHasTag(TEXT("KZCombatEffect")) && It->GetAsset())
   {
    const FString Resource=It->GetAsset()->GetPathName();const bool bSting=Resource.Contains(TEXT("KZ_SwordsMan_Sting"));
    Test->TestFalse(TEXT("Latest user contract excludes both requested Niagara systems from monsters"),Resource==TEXT("/Game/VFX/01_ARPGEssentials/KZ_Slash.KZ_Slash") || Resource==TEXT("/Game/VFX/01_ARPGEssentials/KZ_SwordsMan_Sting.KZ_SwordsMan_Sting"));
    if(!NiagaraBorn.Contains(FObjectKey(*It)))
    {
     NiagaraBorn.Add(FObjectKey(*It));Test->TestFalse(TEXT("Human Niagara transform finite"),It->GetComponentTransform().ContainsNaN());
     Test->TestTrue(TEXT("Human weapon snapshot begins in actor front"),FVector::DotProduct(It->GetComponentLocation()-Current->GetMesh()->GetComponentLocation(),Current->GetActorForwardVector())>0);
     NiagaraFamilies.Add(Current->GetClass()->GetPathName());bSawSting|=bSting;
     Test->AddInfo(FString::Printf(TEXT("HUMAN_NIAGARA_BORN family=%s resource=%s position=%s scale=%s"),*Current->GetClass()->GetPathName(),*Resource,*It->GetComponentLocation().ToString(),*It->GetComponentScale().ToString()));
    }
    const FString Key=FString(VisualFamilies[FamilyIndex])+(bSting?TEXT("_Sting"):TEXT("_Slash"));
    if(++NiagaraFrames.FindOrAdd(Key)==5)
    {
     auto* PC=Player->GetController<APlayerController>();auto* View=PC && PC->GetLocalPlayer()?PC->GetLocalPlayer()->ViewportClient.Get():nullptr;TArray<FColor> Pixels;FIntVector Size=FIntVector::ZeroValue;
     if(View && View->GetWindow().IsValid() && FSlateApplication::Get().TakeScreenshot(View->GetWindow().ToSharedRef(),Pixels,Size))
     {TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Size.X,Size.Y,Pixels,PNG);FFileHelper::SaveArrayToFile(PNG,*FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_REPAIR_OUT")),TEXT("Human_")+Key+TEXT(".png")));}
    }
   }
 }
 TArray<UParticleSystemComponent*> NewParticle(FName Id) const {TArray<UParticleSystemComponent*> Found;for(TObjectIterator<UParticleSystemComponent> It;It;++It) if(Player.IsValid() && It->GetWorld()==Player->GetWorld() && It->ComponentHasTag(Id) && !It->bWasDeactivated && It->IsActive()) Found.Add(*It);return Found;}
 void BoundaryFixtures()
 {
  AKZMonster* Monster=ByFamily.FindChecked(LoopFamily.IsEmpty()?TEXT("Swordsman"):LoopFamily).Get();RestoreAnim(Monster);
  if(Test->TestNotNull(TEXT("Actual unconditional original persistent emitter available for lifetime fixture"),LoopState))
  {
   UKZAnimNotifyState_MonsterVisual* State=const_cast<UKZAnimNotifyState_MonsterVisual*>(LoopState);
   FAnimNotifyEvent E;E.NotifyStateClass=State;FAnimNotifyEventReference A(&E,LoopSequence),B(&E,LoopSequence);A.SetNotifyInstanceID(910001);B.SetNotifyInstanceID(910002);
   const FName Id=State->Effect->EventId;int32 Before=NewParticle(Id).Num();
   State->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,A);State->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,A);
   State->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,B);
   Test->TestEqual(TEXT("Distinct forced-ID lifetime fixture owns two resources; repeated same ID idempotent"),NewParticle(Id).Num(),Before+2);
   State->NotifyEnd(Monster->GetMesh(),LoopSequence,A);Test->TestEqual(TEXT("Cancellation ends only its exact ID"),NewParticle(Id).Num(),Before+1);
   State->NotifyEnd(Monster->GetMesh(),LoopSequence,A);Test->TestEqual(TEXT("Repeated cancel does not end other ID"),NewParticle(Id).Num(),Before+1);
   Monster->ClearMonsterVisuals();Test->TestEqual(TEXT("Context/freeze cleanup stops persistent emission"),NewParticle(Id).Num(),Before);
   TStrongObjectPtr<UKZAnimNotifyState_MonsterVisual> Tail(DuplicateObject<UKZAnimNotifyState_MonsterVisual>(State,GetTransientPackage()));
   Tail->Effect=DuplicateObject<UKZAnimNotify_CombatEffect>(State->Effect,Tail.Get());Tail->Effect->bDestroyOnNotifyEnd=false;Tail->Effect->bDestroyOnAnimEnd=true;
   FAnimNotifyEvent TE;TE.NotifyStateClass=Tail.Get();FAnimNotifyEventReference T1(&TE,LoopSequence),T2(&TE,LoopSequence);
   T1.SetNotifyInstanceID(910020);T2.SetNotifyInstanceID(910021);T1.AddContextData<UE::Anim::FAnimNotifyAssetPlayerInstanceContext>(20u);T2.AddContextData<UE::Anim::FAnimNotifyAssetPlayerInstanceContext>(21u);
   Tail->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,T1);Tail->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,T2);
   T1.AddContextData<UE::Anim::FAnimNotifyEndDataContext>(true);T2.AddContextData<UE::Anim::FAnimNotifyEndDataContext>(true);
   Tail->NotifyEnd(Monster->GetMesh(),LoopSequence,T1);Tail->NotifyEnd(Monster->GetMesh(),LoopSequence,T2);
   Test->TestEqual(TEXT("Natural partial window keeps both original animation-end-owned tails"),NewParticle(Id).Num(),Before+2);
   Monster->EndMonsterVisualContext(Monster->GetMesh(),T1);Test->TestEqual(TEXT("Full-clip context end kills only matching asset-player tail"),NewParticle(Id).Num(),Before+1);
   Monster->EndMonsterVisualContext(Monster->GetMesh(),T1);Test->TestEqual(TEXT("Repeated context End preserves other concurrent source player"),NewParticle(Id).Num(),Before+1);
   Monster->EndMonsterVisualContext(Monster->GetMesh(),T2);Test->TestEqual(TEXT("Explicit source destroy-on-animation-end kills final tail"),NewParticle(Id).Num(),Before);

   TStrongObjectPtr<UKZAnimNotifyState_MonsterVisual> Conditional(DuplicateObject<UKZAnimNotifyState_MonsterVisual>(State,GetTransientPackage()));
   Conditional->Effect=DuplicateObject<UKZAnimNotify_CombatEffect>(State->Effect,Conditional.Get());Conditional->Effect->bOnAttackSuccessed=true;
   FAnimNotifyEvent CE;CE.NotifyStateClass=Conditional.Get();FAnimNotifyEventReference C(&CE,LoopSequence);C.SetNotifyInstanceID(910003);
   Conditional->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,C);Test->TestEqual(TEXT("Actual success flag cannot fabricate a Monster hit"),NewParticle(Id).Num(),Before);
   FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   AKZMonster* Other=Player->GetWorld()->SpawnActor<AKZMonster>(Monster->GetClass(),Player->GetActorTransform(),P);StopAI(Other);ExtraActor=Other;State->NotifyBegin(Monster->GetMesh(),LoopSequence,1.f,A);State->NotifyBegin(Other->GetMesh(),LoopSequence,1.f,A);
   Test->TestEqual(TEXT("Same saved notify asset and ID isolated across actual avatars"),NewParticle(Id).Num(),Before+2);
   Monster->ClearMonsterVisuals();Test->TestEqual(TEXT("One avatar cleanup preserves other avatar emitter"),NewParticle(Id).Num(),Before+1);
   Other->Destroy();Test->TestEqual(TEXT("Actual EndPlay stops its owned persistent emitter"),NewParticle(Id).Num(),Before);
  }
  if(Test->TestNotNull(TEXT("Original physical-surface decal route represented in saved native data"),DecalRouteState))
  {
   TStrongObjectPtr<UKZAnimNotify_CombatEffect> RouteEffect(DuplicateObject<UKZAnimNotify_CombatEffect>(DecalRouteState->Effect,GetTransientPackage()));
   // Transient geometry-only route fixture disables the source hit gate. No Monster gameplay hit/provenance is fabricated; saved original conditional flag remains unchanged.
   RouteEffect->bOnAttackSuccessed=false;RouteEffect->bSpawnOnFloor=false;RouteEffect->bWinterOnly=false;RouteEffect->bAttached=false;RouteEffect->SourceSocket=NAME_None;RouteEffect->bUseSourceCorrection=false;RouteEffect->ParticleTemplate=nullptr;
   RouteEffect->bOverrideSurface=true;
   FKZCombatEffectSurfaceRoute NullRoute;NullRoute.Surface=SurfaceType_Default;NullRoute.bSuppressDecal=true;
   UMaterialInterface* Blood=nullptr;for(const auto& R:RouteEffect->SurfaceRoutes) if(R.Surface==SurfaceType1 && R.DecalMaterial) {Blood=R.DecalMaterial;break;}
   Test->TestNotNull(TEXT("Exact original material route resource exists"),Blood);
   RouteEffect->DecalMaterial=Blood;RouteEffect->SurfaceRoutes={NullRoute};RouteEffect->SurfaceOverride=SurfaceType_Default;
   Test->TestNull(TEXT("Explicit default null route suppresses even a fallback field"),UKZAnimNotify_CombatEffect::SpawnComponent(*RouteEffect,Monster->GetMesh()));
   FKZCombatEffectSurfaceRoute MatRoute;MatRoute.Surface=SurfaceType1;MatRoute.DecalMaterial=Blood;RouteEffect->SurfaceRoutes.Add(MatRoute);RouteEffect->DecalMaterial=nullptr;RouteEffect->SurfaceOverride=SurfaceType1;
   USceneComponent* Spawned=UKZAnimNotify_CombatEffect::SpawnComponent(*RouteEffect,Monster->GetMesh());
   Test->TestNotNull(TEXT("Selected original material route creates actual decal without global material"),Cast<UDecalComponent>(Spawned));if(Spawned) Spawned->DestroyComponent();
   RouteEffect->SurfaceOverride=SurfaceType13;Test->TestNull(TEXT("Unlisted snow13 has no invented default emission"),UKZAnimNotify_CombatEffect::SpawnComponent(*RouteEffect,Monster->GetMesh()));
  }

  if(Test->TestNotNull(TEXT("Actual source Apes scalar material state exists"),MaterialState))
  {
   AKZMonster* Apes=ByFamily.FindChecked(TEXT("ApesStoneHandElite")).Get();RestoreAnim(Apes);
   const FName Parameter=MaterialState->ScalarParameterName.IsNone()?MaterialState->ScalarCurveName:MaterialState->ScalarParameterName;
   UMaterialInstanceDynamic* MID=Apes->GetMesh()->CreateDynamicMaterialInstance(0);float Baseline=0.f;
   if(Test->TestTrue(TEXT("Actual body material exposes original scalar consumer"),MID && MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Baseline)))
   {
    TStrongObjectPtr<UKZAnimNotifyState_MonsterVisual> First(DuplicateObject<UKZAnimNotifyState_MonsterVisual>(MaterialState,GetTransientPackage())),Second(DuplicateObject<UKZAnimNotifyState_MonsterVisual>(MaterialState,GetTransientPackage()));
    First->bUseScalarCurve=Second->bUseScalarCurve=true;First->ScalarCurve.EditorCurveData.Reset();Second->ScalarCurve.EditorCurveData.Reset();First->ScalarCurve.EditorCurveData.AddKey(0.f,1.f);Second->ScalarCurve.EditorCurveData.AddKey(0.f,2.f); // Material ownership boundary values, not gameplay tuning.
    FAnimNotifyEvent E1,E2;E1.NotifyStateClass=First.Get();E2.NotifyStateClass=Second.Get();FAnimNotifyEventReference R1(&E1,MaterialSequence),R2(&E2,MaterialSequence);R1.SetNotifyInstanceID(910010);R2.SetNotifyInstanceID(910011);
    UMaterialInterface* SavedMaterial=Apes->GetMesh()->GetMaterial(0);
    First->NotifyBegin(Apes->GetMesh(),MaterialSequence,1.f,R1);MID=Cast<UMaterialInstanceDynamic>(Apes->GetMesh()->GetMaterial(0));Second->NotifyBegin(Apes->GetMesh(),MaterialSequence,1.f,R2);float Value=0.f;MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Value);Test->TestEqual(TEXT("Concurrent final material writer takes effect"),Value,2.f);
    First->NotifyEnd(Apes->GetMesh(),MaterialSequence,R1);MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Value);Test->TestEqual(TEXT("Ending earlier material owner preserves later writer"),Value,2.f);
    Second->NotifyEnd(Apes->GetMesh(),MaterialSequence,R2);Test->TestEqual(TEXT("Last material override owner restores actual original slot"),Apes->GetMesh()->GetMaterial(0),SavedMaterial);MID=Cast<UMaterialInstanceDynamic>(Apes->GetMesh()->GetMaterial(0));MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Value);Test->TestEqual(TEXT("Final material owner restores original baseline"),Value,Baseline);
   }
  }
 }
 void DeathCancellationFixture()
 {
  FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
  AKZMonster* Victim=Player->GetWorld()->SpawnActor<AKZMonster>(Monsters[0]->GetClass(),StagedTransforms[0],P);
  if(!Test->TestNotNull(TEXT("Live corpse cancellation uses actual saved Monster BP"),Victim)) return;
  ExtraActor=Victim;StopAI(Victim);Victim->GetAbilitySystemComponent()->CancelAllAbilities();
  UAnimMontage* Death=Victim->GetCharacterDefinition()->GetMonsterStaminaSettings().DeathPresentationMontage.Get();
  if(!Test->TestNotNull(TEXT("Live corpse has saved source death montage"),Death)) return;
  Victim->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),0.f);
  Victim->FinishDeathPresentation();UAnimInstance* Anim=Victim->GetMesh()->GetAnimInstance();
  FAnimMontageInstance* Instance=Anim->GetActiveInstanceForMontage(Death);
  if(Test->TestNotNull(TEXT("Owned death presentation really starts before live UnPossess"),Instance))
  {
   const int32 ID=Instance->GetInstanceID();AController* Controller=Victim->GetController();
   if(Test->TestNotNull(TEXT("Real live corpse still possessed for cancellation boundary"),Controller)) Controller->UnPossess();
   FAnimMontageInstance* Stopped=Anim->GetMontageInstanceForID(ID);
   Test->TestTrue(TEXT("UnPossess stops only the exact owned death execution"),!Stopped || Stopped->IsStopped());
   Test->TestTrue(TEXT("Live HP0 corpse freezes after owned cancellation"),Victim->GetMesh()->bPauseAnims);
  }
  Victim->Destroy();
 }

 void CheckTerminalDeathMaterials(AKZMonster* Monster,bool bRecord)
 {
  if(!Test->TestNotNull(TEXT("Actual saved source Death_Die_F execution curve exists"),DeathMaterialState)) return;
  const FName Parameter=DeathMaterialState->ScalarParameterName.IsNone()?DeathMaterialState->ScalarCurveName:DeathMaterialState->ScalarParameterName;
  const float Expected=DeathMaterialState->ScalarCurve.GetRichCurveConst()->Eval(DeathMaterialSourceOwner->GetPlayLength());
  if(bRecord) {DeathHeldMaterials.Reset();for(int32 Slot=0;Slot<Monster->GetMesh()->GetNumMaterials();++Slot) DeathHeldMaterials.Add(Cast<UMaterialInstanceDynamic>(Monster->GetMesh()->GetMaterial(Slot)));}
  int32 Consumers=0;
  for(int32 Slot=0;Slot<DeathMaterialBaselines.Num();++Slot)
  {
   UMaterialInterface* Source=DeathMaterialBaselines[Slot].Get();if(const UMaterialInstanceDynamic* OriginalMID=Cast<UMaterialInstanceDynamic>(Source)) Source=OriginalMID->Parent.Get();
   for(const auto& Override:DeathMaterialState->MaterialOverrides) if(Source==Override.SourceMaterial)
   {
    ++Consumers;UMaterialInstanceDynamic* MID=Cast<UMaterialInstanceDynamic>(Monster->GetMesh()->GetMaterial(Slot));
    if(Test->TestNotNull(TEXT("Frozen death keeps actual source execution shader MID installed"),MID))
    {
     Test->TestTrue(TEXT("Held death MID uses authored source replacement parent"),MID->Parent==Override.ReplacementMaterial);
     if(!bRecord) Test->TestEqual(TEXT("Terminal death receipt retains exact same installed MID across frozen ticks"),MID,DeathHeldMaterials[Slot].Get());
     float Value=0.f;Test->TestTrue(TEXT("Held death shader still exposes actual source scalar consumer"),MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Value));
     Test->TestEqual(TEXT("Frozen death retains exact source terminal curve value"),Value,Expected);
    }
    break;
   }
  }
  Test->TestTrue(TEXT("Actual source death matched at least one reconstructed execution material consumer"),Consumers>0);
  Test->AddInfo(FString::Printf(TEXT("MonsterVisual TerminalDeath Actor=%s Curve=%s SourceFinal=%f Consumers=%d Recheck=%d"),*Monster->GetName(),*Parameter.ToString(),Expected,Consumers,!bRecord));
 }

 void CheckPairedSourceRecipes(UAnimMontage* Montage)
 {
  if(!Test->TestNotNull(TEXT("Actual paired source victim montage is available"),Montage)) return;
  // MaterialState belongs to the separate library Damage_FinalBlow fixture.
  // Saved Brutal victim montages consume Grapple segments, whose original exports
  // have particles but no execution recipe. Do not inject FinalBlow into this pair.
  int32 Segments=0,ExecutionRecipes=0;
  const auto CountExecution=[&](const UAnimSequenceBase* Animation)
  {
   int32 SourceStates=0,Recipes=0;
   for(const FAnimNotifyEvent& Event:Animation->Notifies)
    if(const auto* State=Cast<UKZAnimNotifyState_MonsterVisual>(Event.NotifyStateClass.Get()))
    {
     if(State->bAnimationContextBoundary) continue;++SourceStates;
     const FName Parameter=State->ScalarParameterName.IsNone()?State->ScalarCurveName:State->ScalarParameterName;
     if(!State->MaterialOverrides.IsEmpty() || Parameter==TEXT("Execution") || Parameter==TEXT("ExecutionO") || State->VectorParameterName==TEXT("ExecutionOffset_radius")) ++Recipes;
    }
   ExecutionRecipes+=Recipes;
   Test->AddInfo(FString::Printf(TEXT("MonsterVisual PairedSource Montage=%s Clip=%s SourceStates=%d ExecutionRecipes=%d SeparateFinalBlow=%s"),*Montage->GetPathName(),*Animation->GetPathName(),SourceStates,Recipes,*GetNameSafe(MaterialSequence)));
  };
  CountExecution(Montage);
  for(const FSlotAnimationTrack& Track:Montage->SlotAnimTracks)
   for(const FAnimSegment& Segment:Track.AnimTrack.AnimSegments)
   {
    UAnimSequenceBase* Animation=Segment.GetAnimReference().Get();
    if(Test->TestNotNull(TEXT("Actual paired victim montage segment has its saved source animation"),Animation)) {++Segments;CountExecution(Animation);}
   }
  Test->TestEqual(TEXT("Saved Apes Grapple victim montage retains its two actual source segments"),Segments,2);
  Test->TestEqual(TEXT("Actual Grapple victim montage and source segments contain zero execution recipes"),ExecutionRecipes,0);
 }

 void CheckPairedTerminalMaterials(AKZMonster* Monster,bool bRecord)
 {
  // This pair preserves its five original baseline MIDs. FinalBlow/ordinary death
  // replacement-parent and terminal-curve assertions are separate source consumers.
  const FName Parameter(TEXT("Execution"));
  Test->TestEqual(TEXT("Completed actual Grapple pair retains all five baseline slots"),Monster->GetMesh()->GetNumMaterials(),PairedBaselines.Num());
  for(int32 Slot=0;Slot<PairedBaselines.Num();++Slot)
  {
   Test->TestEqual(TEXT("Completed Grapple pair preserves the exact original material slot"),Monster->GetMesh()->GetMaterial(Slot),PairedBaselines[Slot].Get());
   auto* MID=Cast<UMaterialInstanceDynamic>(Monster->GetMesh()->GetMaterial(Slot));
   if(Test->TestNotNull(TEXT("Completed Grapple pair retains the actual baseline MID"),MID))
   {
    Test->TestEqual(TEXT("Actual pair keeps the same baseline MID through completion/frozen ticks"),MID,PairedHeldMaterials[Slot].Get());
    float Value=0.f;Test->TestTrue(TEXT("Actual paired baseline still exposes its original execution uniform"),MID->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Value));
    Test->TestEqual(TEXT("Grapple without execution recipes preserves the source baseline value"),Value,PairedHeldValues[Slot]);
    Test->AddInfo(FString::Printf(TEXT("MonsterVisual PairedGrappleBaseline Slot=%d Curve=%s Baseline=%f Actual=%f Frozen=%d Recheck=%d"),Slot,*Parameter.ToString(),PairedHeldValues[Slot],Value,Monster->GetMesh()->bPauseAnims,!bRecord));
   }
  }
 }

 bool Finish() {if(bHumanOnly)Test->TestEqual(TEXT("Original effects observed on all four human families"),NiagaraFamilies.Num(),4);if(Player.IsValid()) Test->TestEqual(TEXT("Monster visual testing never fabricated player HP damage"),Player->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()),HP);Test->AddInfo(FString::Printf(TEXT("MonsterVisual final sourceEvents=%d attackPatterns=%d captures=%d"),SourceTotal,AttackTotal,CaptureIndex));Cleanup();return true;}
 void Cleanup() {if(bCleaned) return;bCleaned=true;FWorldDelegates::OnWorldPostActorTick.Remove(PostTick);if(WinterFixture.IsValid()) WinterFixture->Destroy();if(ExtraActor.IsValid()) ExtraActor->Destroy();for(auto& W:Monsters) if(AKZMonster* M=W.Get()) {M->Tags.Remove(TEXT("KZMonsterVFXCapture"));M->ClearMonsterVisuals();M->Destroy();}if(Player.IsValid()) {Player->GetAbilitySystemComponent()->CancelAllAbilities();Player->SetActorTransform(SavedPlayerTransform,false,nullptr,ETeleportType::TeleportPhysics);}}
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;double Deadline;float HP=0.f,CaseEnd=0.f,CaseDeadline=0.f;FDelegateHandle PostTick;bool bCleaned=false,bLoop=false;
 TArray<FVisualClipCase> Cases,Captures;TArray<TWeakObjectPtr<AKZMonster>> Monsters;TMap<FString,TWeakObjectPtr<AKZMonster>> ByFamily;TArray<TSubclassOf<UAnimInstance>> AnimClasses;TArray<FTransform> StagedTransforms;
 TWeakObjectPtr<AKZMonster> Current,ExtraActor;FString LoopFamily;TStrongObjectPtr<UAnimSequence> LoopSourceOwner,MaterialSourceOwner;TWeakObjectPtr<UAnimSequence> CurrentSequence;const UKZAnimNotifyState_MonsterVisual* LoopState=nullptr;UAnimSequence* LoopSequence=nullptr;const UKZAnimNotifyState_MonsterVisual* MaterialState=nullptr;const UKZAnimNotifyState_MonsterVisual* DecalRouteState=nullptr;TStrongObjectPtr<UAnimSequence> DecalRouteSourceOwner;UAnimSequence* MaterialSequence=nullptr;
 TWeakObjectPtr<AKZSnowDeformation> WinterFixture;
 const UKZAnimNotifyState_MonsterVisual* DeathMaterialState=nullptr;TStrongObjectPtr<UAnimSequence> DeathMaterialSourceOwner;TArray<TStrongObjectPtr<UMaterialInterface>> DeathMaterialBaselines;TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> DeathHeldMaterials;
 FTransform SavedPlayerTransform;int32 PairedCase=0;float PairedHPBefore=0.f;bool bPairedReactionSeen=false;TWeakObjectPtr<UKZBrutalAttackAbility> PairedBrutal;TArray<TStrongObjectPtr<UMaterialInterface>> PairedBaselines;TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> PairedHeldMaterials;TArray<float> PairedHeldValues;
 const bool bHumanOnly=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_VFX_HUMAN_ONLY"))==TEXT("1");bool bSawSting=false;TSet<FObjectKey> NiagaraBorn;TSet<FString> NiagaraFamilies;TMap<FString,int32> NiagaraFrames;
 int32 Phase=0,FamilyIndex=0,AttackIndex=0,AttackTotal=0,CaptureIndex=0,SourceTotal=0,ConditionalTotal=0,TrailTotal=0,DecalTotal=0,MaterialTotal=0,DecalRouteTotal=0;FGameplayAbilitySpecHandle ActiveHandle;TSet<FName> CandidateIds,ConditionalIds,ConditionalReported,SeenIds,ExpectedSections,SeenSections;
};
class FWaitForMonsterVisualPIE : public IAutomationLatentCommand
{
public:
 explicit FWaitForMonsterVisualPIE(FAutomationTestBase* InTest):Test(InTest),Deadline(FPlatformTime::Seconds()+60.) {}
 bool Update() override
 {
  if(GEngine) for(const FWorldContext& Context:GEngine->GetWorldContexts())
   if(Context.WorldType==EWorldType::PIE && Context.World() && Context.World()->HasBegunPlay())
    for(TActorIterator<AKZPlayer> It(Context.World());It;++It)
     if(It->IsPlayerControlled() && It->GetCharacterMovement()->IsMovingOnGround() && It->GetMesh()->GetAnimInstance())
     {FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FMonsterVisualPIE>(Test,*It));return true;}
  if(FPlatformTime::Seconds()>Deadline) {Test->AddError(TEXT("Start task-owned DevMap PIE after MonsterVisual Test Started."));return true;}return false;
 }
private:FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterVisualPIETest,"Khazan.MonsterVisual.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterVisualPIETest::RunTest(const FString&)
{
 // This saved player definition has explicit blank baseline rows. Expect only
 // their exact PIE startup log, with the saved row count; malformed input grants
 // and any additional/different startup errors remain test failures.
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
 FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForMonsterVisualPIE>(this));return true;
}
#endif
