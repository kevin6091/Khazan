// Owned, isolated PIE only. Temporary geometry/damage literals below are test fixtures,
// never original-game values. No CDO, Montage, DataAsset, map or package is saved.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboAttackAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "AI/KZMonsterAIController.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "KZGameplayTags.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UnrealType.h"

namespace
{
struct FCollisionActorSnapshot
{
 TWeakObjectPtr<AKZCharacter> Actor;
 FTransform Transform;
 FVector Velocity;
 EMovementMode MovementMode = MOVE_None;
 uint8 CustomMode = 0;
 float HP = 0, MaxHP = 0, Stamina = 0, MaxStamina = 0, Radius = 0, HalfHeight = 0;
 ECollisionEnabled::Type Collision = ECollisionEnabled::NoCollision;
 FCollisionResponseContainer Responses;
 bool RunningAI = false, ActivePerception = false;
};

struct FAttackCollisionCase
{
 FString Name;
 FKZComboNode Node;
 FVector TargetOffset = FVector(150, 0, 0);
 float InitialHP = 100, InitialStamina = 50;
 float ExpectedHP = 0, ExpectedStamina = 0;
 float CancelAt = -1, ObserveTime = 0;
 bool Oversized = false;
 int32 ExpectedHits = 0;
};

class FPlayerAttackCollisionCommand : public IAutomationLatentCommand
{
public:
 FPlayerAttackCollisionCommand(FAutomationTestBase* InTest, AKZPlayer* InPlayer)
  : Test(InTest), Player(InPlayer), ASC(Cast<UKZAbilitySystemComponent>(InPlayer->GetAbilitySystemComponent())),
    Deadline(FPlatformTime::Seconds() + 600.0)
 {
  Initialize();
 }
 ~FPlayerAttackCollisionCommand() { Cleanup(); }

 bool Update() override
 {
  if (Failed || !Player.IsValid() || !ASC.IsValid() || !Target.IsValid() || FPlatformTime::Seconds() > Deadline)
  {
   if (!Failed) Test->AddError(TEXT("Player attack collision fixture expired or timed out"));
   Cleanup(); return true;
  }
  const float Now = Player->GetWorld()->GetTimeSeconds();
  if (!RunningCase)
  {
   if (CaseIndex == Cases.Num())
   {
    Test->AddInfo(FString::Printf(TEXT("PlayerAttackCollision all cases complete: %d, authored multi-hit target was oversized; controlled range targets used normal capsule"), Cases.Num()));
    Cleanup(); return true;
   }
   if (!StartCase(Cases[CaseIndex], Now)) { Cleanup(); return true; }
   return false;
  }
  const FAttackCollisionCase& C = Cases[CaseIndex];
  if (Attack->IsActive() && !FMath::IsNearlyEqual(LastObservedTime, Now))
  {
   float Begin = 0, End = 0; C.Node.Montage->GetSectionStartAndEndTime(C.Node.Montage->GetSectionIndex(C.Node.SectionName), Begin, End);
   const float LocalTime = Player->GetMesh()->GetAnimInstance()->Montage_GetPosition(C.Node.Montage) - Begin;
   if (C.Node.AttackWindows.ContainsByPredicate([LocalTime](const FKZAttackCollisionWindow& W) { return LocalTime >= W.StartTime && LocalTime <= W.EndTime; })) ++ActiveWindowFrames;
   LastObservedTime = Now;
  }
  if (!Canceled && C.CancelAt >= 0 && Now >= CaseStart + C.CancelAt)
  {
   ASC->CancelAbilityHandle(AttackHandle); Canceled = true;
   Test->TestFalse(TEXT("Cancellation ends attack execution"), Attack->IsActive());
  }
  if (Now < CaseStart + C.ObserveTime) return false;
  UAbilitySystemComponent* Victim = Target->GetAbilitySystemComponent();
  const float HPDelta = C.InitialHP - Victim->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
  const float StaminaDelta = C.InitialStamina - Victim->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
  Test->TestTrue(*FString::Printf(TEXT("%s HP delta"), *C.Name), FMath::IsNearlyEqual(HPDelta, C.ExpectedHP, .001f));
  Test->TestTrue(*FString::Printf(TEXT("%s stamina delta"), *C.Name), FMath::IsNearlyEqual(StaminaDelta, C.ExpectedStamina, .001f));
  Test->TestEqual(*FString::Printf(TEXT("%s accepted HP effects"), *C.Name), HPChanges, C.ExpectedHits);
  if (CaseIndex == 0) Test->TestTrue(TEXT("Dedup observed across multiple actual active Montage frames"), ActiveWindowFrames > 1);
  Test->AddInfo(FString::Printf(TEXT("PlayerAttackCollision case=%s HP=%g expected=%g Stamina=%g expected=%g HPChanges=%d expectedHits=%d oversized=%d canceled=%d"),
   *C.Name, HPDelta, C.ExpectedHP, StaminaDelta, C.ExpectedStamina, HPChanges, C.ExpectedHits, C.Oversized, Canceled));
  Capturing = false; ASC->CancelAbilityHandle(AttackHandle); RunningCase = false; ++CaseIndex;
  return false;
 }

private:
 void Fail(const FString& Message) { Test->AddError(Message); Failed = true; }

 FCollisionActorSnapshot Snapshot(AKZCharacter* A)
 {
  FCollisionActorSnapshot S;
  S.Actor = A; S.Transform = A->GetActorTransform();
  UCharacterMovementComponent* Move = A->GetCharacterMovement();
  S.Velocity = Move->Velocity; S.MovementMode = Move->MovementMode; S.CustomMode = Move->CustomMovementMode;
  UAbilitySystemComponent* AASC = A->GetAbilitySystemComponent();
  S.HP = AASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()); S.MaxHP = AASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute());
  S.Stamina = AASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()); S.MaxStamina = AASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute());
  A->GetCapsuleComponent()->GetUnscaledCapsuleSize(S.Radius, S.HalfHeight);
  S.Collision = A->GetCapsuleComponent()->GetCollisionEnabled(); S.Responses = A->GetCapsuleComponent()->GetCollisionResponseToChannels();
  if (AKZMonsterAIController* AI = Cast<AKZMonsterAIController>(A->GetController()))
  {
   S.RunningAI = AI->GetStateTreeComponent()->IsRunning(); S.ActivePerception = AI->GetPerceptionComponent()->IsActive();
   AI->GetStateTreeComponent()->StopLogic(TEXT("Isolated player attack collision fixture")); AI->StopMovement(); AI->GetPerceptionComponent()->Deactivate();
  }
  FGameplayTagContainer Action; Action.AddTag(KZGameplayTags::Ability_Action); AASC->CancelAbilities(&Action);
  Move->StopMovementImmediately(); Move->DisableMovement();
  A->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
  return S;
 }

 void Initialize()
 {
  if (!ASC.IsValid() || !Player->HasAuthority()) { Fail(TEXT("Player collision fixture needs authoritative standalone Player")); return; }
  for (FActiveGameplayEffectHandle Effect : ASC->GetActiveEffects(FGameplayEffectQuery())) SavedPlayerEffects.Add(Effect);
  for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
  {
   const UKZComboAttackAbility* CDO = Cast<UKZComboAttackAbility>(Spec.Ability);
   if (CDO && CDO->GetEntryNodeId().ToString().Contains(TEXT("WeakAttack01")))
   {
    AttackHandle = Spec.Handle; Attack = Cast<UKZComboAttackAbility>(Spec.GetPrimaryInstance()); break;
   }
  }
  if (!Attack.IsValid()) { Fail(TEXT("Granted concrete WeakAttack01 primary instance is missing")); return; }
  SavedDefinition = Attack->GetComboDefinition(); SavedEntry = Attack->GetEntryNodeId();
  DefinitionProperty = FindFProperty<FObjectPropertyBase>(Attack->GetClass(), TEXT("ComboDefinition"));
  EntryProperty = FindFProperty<FNameProperty>(Attack->GetClass(), TEXT("EntryNodeId"));
  CostProperty = FindFProperty<FClassProperty>(Attack->GetClass(), TEXT("CostGameplayEffectClass"));
  NodesProperty = SavedDefinition ? FindFProperty<FArrayProperty>(SavedDefinition->GetClass(), TEXT("Nodes")) : nullptr;
  if (!SavedDefinition || !DefinitionProperty || !EntryProperty || !CostProperty || !NodesProperty || !SavedDefinition->GetAttackDamageEffect())
  { Fail(TEXT("Authored collision Definition/damage GE/reflection fields are missing")); return; }
  SavedCost = CostProperty->GetObjectPropertyValue_InContainer(Attack.Get());
  const TArray<FKZComboNode>& Authored = *NodesProperty->ContainerPtrToValuePtr<TArray<FKZComboNode>>(SavedDefinition);
  const FKZComboNode* Base = SavedDefinition->FindNode(SavedEntry);
  if (!Base || !Base->Montage) { Fail(TEXT("Fixture base entry Montage is missing")); return; }
  int32 WindowCount = 0, KeyCount = 0, AttackNodes = 0;
  TSet<FName> Names;
  bool HasSpinning = false, HasOverFury = false;
  for (const FKZComboNode& N : Authored)
  {
   Test->TestTrue(TEXT("Authored node id unique/nonempty"), !N.NodeId.IsNone() && !Names.Contains(N.NodeId)); Names.Add(N.NodeId);
   Test->TestTrue(TEXT("Authored node playable"), N.Montage && N.Montage->GetSectionIndex(N.SectionName) != INDEX_NONE);
   Test->TestFalse(TEXT("Authored collision mapping finite"), N.CollisionToActor.ContainsNaN());
   if (N.AttackWindows.IsEmpty()) continue;
   ++AttackNodes;
   for (const FKZAttackCollisionWindow& W : N.AttackWindows)
   {
    ++WindowCount; KeyCount += W.Keys.Num();
    Test->TestTrue(TEXT("Authored window finite/nonnegative interval"), FMath::IsFinite(W.StartTime) && FMath::IsFinite(W.EndTime) && W.StartTime >= 0 && W.EndTime >= W.StartTime);
    Test->TestTrue(TEXT("Authored positive extent and nonempty original/tuning provenance"), !W.Extent.ContainsNaN() && W.Extent.GetMin() > 0 && !W.Source.IsEmpty());
    Test->TestTrue(TEXT("Authored finite editor damage"), FMath::IsFinite(W.HPDamage) && W.HPDamage >= 0 && FMath::IsFinite(W.StaminaDamage) && W.StaminaDamage >= 0);
    Test->TestTrue(TEXT("Authored window has baked keys"), !W.Keys.IsEmpty());
    float Previous = -1;
    for (const FKZAttackCollisionKey& K : W.Keys)
    {
     Test->TestTrue(TEXT("Authored baked key ordered/in-window/finite"), FMath::IsFinite(K.Time) && K.Time >= Previous && K.Time >= W.StartTime - .001f && K.Time <= W.EndTime + .001f && !K.Center.ContainsNaN() && !K.Rotation.ContainsNaN()); Previous = K.Time;
     GeometryBound = FMath::Max(GeometryBound, static_cast<float>(N.CollisionToActor.TransformPosition(K.Center).Size() + W.Extent.Size() * N.CollisionToActor.GetScale3D().GetAbsMax()));
    }
   }
   if (N.NodeId.ToString().Contains(TEXT("Spinning")) || N.NodeId.ToString().Contains(TEXT("OverFury")))
   {
    FAttackCollisionCase C; C.Name = TEXT("Authored_") + N.NodeId.ToString(); C.Node = N; C.Node.CommandEdges.Reset(); C.Oversized = true;
    TSet<FName> Groups;
    for (const FKZAttackCollisionWindow& W : C.Node.AttackWindows)
    {
     C.ObserveTime = FMath::Max(C.ObserveTime, W.EndTime);
     if (!W.HitGroup.IsNone() && Groups.Contains(W.HitGroup)) continue;
     if (!W.HitGroup.IsNone()) Groups.Add(W.HitGroup);
     C.ExpectedHP += W.HPDamage; C.ExpectedStamina += W.StaminaDamage; C.ExpectedHits += W.HPDamage > 0 ? 1 : 0;
    }
    C.InitialHP = C.ExpectedHP + 100; C.InitialStamina = C.ExpectedStamina + 50; C.ObserveTime += .4f;
    AuthoredCases.Add(C);
    HasSpinning |= N.NodeId.ToString().Contains(TEXT("Spinning")); HasOverFury |= N.NodeId.ToString().Contains(TEXT("OverFury"));
   }
  }
  Test->TestTrue(TEXT("All-node audit includes attack data and debug draw"), AttackNodes > 0 && WindowCount > 0 && KeyCount >= WindowCount && SavedDefinition->ShouldDrawAttackCollision());
  Test->TestTrue(TEXT("Authored multi-hit coverage includes Spinning and OverFury"), HasSpinning && HasOverFury);
  Test->AddInfo(FString::Printf(TEXT("PlayerAttackCollision authored coverage nodes=%d attackNodes=%d windows=%d keys=%d multiHitNodes=%d debug=%d"), Authored.Num(), AttackNodes, WindowCount, KeyCount, AuthoredCases.Num(), SavedDefinition->ShouldDrawAttackCollision()));
  Fixture.Reset(DuplicateObject<UKZComboDefinitionData>(SavedDefinition, GetTransientPackage()));
  SavedPlayer = Snapshot(Player.Get()); ASC->ClearComboCommands(); Player->HandleInputMoveReleased();
  TSet<FString> Families;
  for (TActorIterator<AKZMonster> It(Player->GetWorld()); It; ++It)
  {
   AKZMonster* M = *It;
   UAbilitySystemComponent* MASC = M->GetAbilitySystemComponent();
   if (!MASC || !MASC->GetSet<UKZAttributeSet>()) continue;
   const FString Path = M->GetCharacterDefinition() ? M->GetCharacterDefinition()->GetPathName() : TEXT("");
   for (const FString Family : {FString(TEXT("Swordsman")), FString(TEXT("SwordShield")), FString(TEXT("HeavySwordsman")), FString(TEXT("HalberdElite"))})
   {
    if (!Path.Contains(TEXT("/Monsters/") + Family + TEXT("/"))) continue;
    const float ExpectedHP = Family == TEXT("Swordsman") || Family == TEXT("SwordShield") ? 100.f : 200.f;
    Test->TestEqual(*FString::Printf(TEXT("Initialized %s MaxHP"), *Family), MASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()), ExpectedHP);
    Test->TestEqual(*FString::Printf(TEXT("Initialized %s HP"), *Family), MASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()), ExpectedHP);
    Test->TestEqual(*FString::Printf(TEXT("Initialized %s MaxStamina"), *Family), MASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()), 50.f);
    Test->TestEqual(*FString::Printf(TEXT("Initialized %s Stamina"), *Family), MASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()), 50.f);
    Families.Add(Family); if (Family == TEXT("Swordsman") && !Target.IsValid()) Target = M;
   }
   SavedMonsters.Add(Snapshot(M));
   M->SetActorLocation(SavedPlayer.Transform.GetLocation() + FVector(20000 + SavedMonsters.Num() * 1000, 20000, 0), false, nullptr, ETeleportType::TeleportPhysics);
  }
  if (Families.Num() != 4 || !Target.IsValid()) { Fail(TEXT("Real initialized four monster families are required")); return; }
  HPDelegate = Target->GetAbilitySystemComponent()->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).AddRaw(this, &FPlayerAttackCollisionCommand::OnHP);
  float Begin = 0, End = 0; Base->Montage->GetSectionStartAndEndTime(Base->Montage->GetSectionIndex(Base->SectionName), Begin, End);
  const float Duration = End - Begin;
  if (Duration <= .3f) { Fail(TEXT("Real base Montage section is too short for fixture timing")); return; }
  AddControlled(*Base, Duration);
  Cases.Append(AuthoredCases);
  CostProperty->SetObjectPropertyValue_InContainer(Attack.Get(), nullptr);
  AbilityDataChanged = true;
 }

 FKZAttackCollisionWindow Window(float Start, float End, EKZAttackCollisionShape Shape, FName Group = NAME_None)
 {
  FKZAttackCollisionWindow W; W.StartTime = Start; W.EndTime = End; W.Shape = Shape; W.Extent = FVector(30, 30, 40);
  W.HPDamage = 7; W.StaminaDamage = 3; W.HitGroup = Group; W.Source = TEXT("Development integration fixture; not original-game metadata");
  FKZAttackCollisionKey K; K.Time = Start; K.Center = FVector(150, 0, 0); W.Keys.Add(K); K.Time = End; W.Keys.Add(K); return W;
 }

 void AddControlled(const FKZComboNode& Base, float D)
 {
  auto Add = [&](const TCHAR* Name, TArray<FKZAttackCollisionWindow> Windows, float HP, float Stamina, int32 Hits)
  {
   FAttackCollisionCase C; C.Name = Name; C.Node = Base; C.Node.NodeId = TEXT("CollisionFixture"); C.Node.CommandEdges.Reset();
   C.Node.CollisionToActor = FTransform::Identity; C.Node.AttackWindows = MoveTemp(Windows); C.ExpectedHP = HP; C.ExpectedStamina = Stamina; C.ExpectedHits = Hits;
   for (const FKZAttackCollisionWindow& W : C.Node.AttackWindows) C.ObserveTime = FMath::Max(C.ObserveTime, W.EndTime);
   C.ObserveTime += .4f; Cases.Add(C);
  };
  Add(TEXT("Normal_Box_Multiframe_Once"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Box)}, 7, 3, 1);
  Add(TEXT("SameGroup_TwoWindows_Once"), {Window(D * .1f, D * .3f, EKZAttackCollisionShape::Box, TEXT("Shared")), Window(D * .45f, D * .7f, EKZAttackCollisionShape::Box, TEXT("Shared"))}, 7, 3, 1);
  Add(TEXT("SeparateWindows_TwoHits"), {Window(D * .1f, D * .3f, EKZAttackCollisionShape::Box), Window(D * .45f, D * .7f, EKZAttackCollisionShape::Box)}, 14, 6, 2);
  Add(TEXT("Normal_Box_Outside_Miss"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Box)}, 0, 0, 0); Cases.Last().TargetOffset = FVector(1000, 0, 0);
  Add(TEXT("Normal_Cylinder_Hit"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Cylinder)}, 7, 3, 1);
  Add(TEXT("Normal_Cylinder_Outside_Miss"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Cylinder)}, 0, 0, 0); Cases.Last().TargetOffset = FVector(1000, 0, 0);
  Add(TEXT("Normal_Sphere_Hit"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Sphere)}, 7, 3, 1);
  Add(TEXT("Normal_Sphere_Outside_Miss"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Sphere)}, 0, 0, 0); Cases.Last().TargetOffset = FVector(1000, 0, 0);
  Add(TEXT("Numeric_HP0_NoHit"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Box)}, 0, 0, 0); Cases.Last().InitialHP = 0;
  Add(TEXT("HP_Stamina_LowerClamp"), {Window(D * .1f, D * .65f, EKZAttackCollisionShape::Box)}, 5, 2, 1); Cases.Last().InitialHP = 5; Cases.Last().InitialStamina = 2;
  Add(TEXT("Cancel_Before_LateWindow"), {Window(D * .05f, D * .2f, EKZAttackCollisionShape::Box), Window(D * .8f, D * .95f, EKZAttackCollisionShape::Box)}, 7, 3, 1); Cases.Last().CancelAt = D * .4f;
 }

 bool StartCase(const FAttackCollisionCase& C, float Now)
 {
  Capturing = false; ASC->CancelAbilityHandle(AttackHandle); ASC->ClearComboCommands();
  TArray<FKZComboNode>& Nodes = *NodesProperty->ContainerPtrToValuePtr<TArray<FKZComboNode>>(Fixture.Get()); Nodes = {C.Node};
  DefinitionProperty->SetObjectPropertyValue_InContainer(Attack.Get(), Fixture.Get()); EntryProperty->SetPropertyValue_InContainer(Attack.Get(), C.Node.NodeId);
  Player->SetActorTransform(SavedPlayer.Transform, false, nullptr, ETeleportType::TeleportPhysics);
  Target->GetCapsuleComponent()->SetCapsuleSize(C.Oversized ? GeometryBound + 200 : NormalRadius(), C.Oversized ? GeometryBound + 200 : NormalHalfHeight(), true);
  Target->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
  Target->SetActorLocation(SavedPlayer.Transform.TransformPosition(C.TargetOffset), false, nullptr, ETeleportType::TeleportPhysics);
  UAbilitySystemComponent* Victim = Target->GetAbilitySystemComponent();
  Victim->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), FMath::Max(C.InitialHP, 100.f));
  Victim->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(), FMath::Max(C.InitialStamina, 50.f));
  Victim->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), C.InitialHP); Victim->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), C.InitialStamina);
  HPChanges = 0; ActiveWindowFrames = 0; LastObservedTime = -1; Canceled = false; Capturing = true; CaseStart = Now;
  if (!ASC->TryActivateAbility(AttackHandle) || !Attack->IsActive()) { Fail(TEXT("Real engine attack activation failed: ") + C.Name); return false; }
  Test->TestTrue(TEXT("Attack uses real authored Montage"), Attack->GetCurrentMontage() == C.Node.Montage.Get());
  RunningCase = true; return true;
 }

 float NormalRadius() const { for (const FCollisionActorSnapshot& S : SavedMonsters) if (S.Actor.Get() == Target.Get()) return S.Radius; return 0; }
 float NormalHalfHeight() const { for (const FCollisionActorSnapshot& S : SavedMonsters) if (S.Actor.Get() == Target.Get()) return S.HalfHeight; return 0; }
 void OnHP(const FOnAttributeChangeData& Data) { if (Capturing && Data.NewValue < Data.OldValue) ++HPChanges; }

 void Restore(const FCollisionActorSnapshot& S)
 {
  AKZCharacter* A = S.Actor.Get(); if (!A) return;
  UAbilitySystemComponent* AASC = A->GetAbilitySystemComponent();
  AASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), S.MaxHP); AASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), S.HP);
  AASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(), S.MaxStamina); AASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), S.Stamina);
  A->GetCapsuleComponent()->SetCapsuleSize(S.Radius, S.HalfHeight, true); A->GetCapsuleComponent()->SetCollisionEnabled(S.Collision); A->GetCapsuleComponent()->SetCollisionResponseToChannels(S.Responses);
  A->SetActorTransform(S.Transform, false, nullptr, ETeleportType::TeleportPhysics);
  A->GetCharacterMovement()->SetMovementMode(S.MovementMode, S.CustomMode); A->GetCharacterMovement()->Velocity = S.Velocity;
  if (AKZMonsterAIController* AI = Cast<AKZMonsterAIController>(A->GetController()))
  { if (S.ActivePerception) AI->GetPerceptionComponent()->Activate(); if (S.RunningAI) AI->GetStateTreeComponent()->RestartLogic(); }
 }

 void Cleanup()
 {
  if (Cleaned) return; Cleaned = true; Capturing = false;
  if (ASC.IsValid()) ASC->CancelAbilityHandle(AttackHandle);
  if (Target.IsValid() && HPDelegate.IsValid()) Target->GetAbilitySystemComponent()->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(HPDelegate);
  if (Attack.IsValid() && AbilityDataChanged && DefinitionProperty && EntryProperty)
  {
   DefinitionProperty->SetObjectPropertyValue_InContainer(Attack.Get(), const_cast<UKZComboDefinitionData*>(SavedDefinition)); EntryProperty->SetPropertyValue_InContainer(Attack.Get(), SavedEntry);
   if (CostProperty) CostProperty->SetObjectPropertyValue_InContainer(Attack.Get(), SavedCost);
   Test->TestTrue(TEXT("Fixture restores original Ability Definition and Entry"), Attack->GetComboDefinition() == SavedDefinition && Attack->GetEntryNodeId() == SavedEntry);
  }
  // Existing Action End effects (e.g. recovery delay) can outlive a canceled
  // fixture montage. Remove only newly created handles; preserve initial GEs.
  if (ASC.IsValid())
   for (FActiveGameplayEffectHandle Effect : ASC->GetActiveEffects(FGameplayEffectQuery()))
    if (!SavedPlayerEffects.Contains(Effect)) ASC->RemoveActiveGameplayEffect(Effect);
  for (const FCollisionActorSnapshot& S : SavedMonsters) Restore(S);
  if (SavedPlayer.Actor.IsValid()) Restore(SavedPlayer);
  Fixture.Reset();
 }

 FAutomationTestBase* Test;
 TWeakObjectPtr<AKZPlayer> Player;
 TWeakObjectPtr<UKZAbilitySystemComponent> ASC;
 TWeakObjectPtr<UKZComboAttackAbility> Attack;
 TWeakObjectPtr<AKZMonster> Target;
 const UKZComboDefinitionData* SavedDefinition = nullptr;
 UObject* SavedCost = nullptr;
 FName SavedEntry;
 FGameplayAbilitySpecHandle AttackHandle;
 FObjectPropertyBase* DefinitionProperty = nullptr;
 FNameProperty* EntryProperty = nullptr;
 FClassProperty* CostProperty = nullptr;
 FArrayProperty* NodesProperty = nullptr;
 TStrongObjectPtr<UKZComboDefinitionData> Fixture;
 FCollisionActorSnapshot SavedPlayer;
 TArray<FCollisionActorSnapshot> SavedMonsters;
 TArray<FAttackCollisionCase> Cases, AuthoredCases;
 TSet<FActiveGameplayEffectHandle> SavedPlayerEffects;
 FDelegateHandle HPDelegate;
 double Deadline;
 float CaseStart = 0, GeometryBound = 0, LastObservedTime = -1;
 int32 CaseIndex = 0, HPChanges = 0, ActiveWindowFrames = 0;
 bool Failed = false, RunningCase = false, Capturing = false, Canceled = false, Cleaned = false, AbilityDataChanged = false;
};

class FWaitForPlayerAttackCollisionPIE : public IAutomationLatentCommand
{
public:
 explicit FWaitForPlayerAttackCollisionPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 45.0) {}
 bool Update() override
 {
  for (const FWorldContext& C : GEngine->GetWorldContexts())
  {
   if (C.WorldType != EWorldType::PIE || !C.World() || !C.World()->HasBegunPlay()) continue;
   for (TActorIterator<AKZPlayer> It(C.World()); It; ++It)
    if (It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance() && It->GetCharacterMovement()->IsMovingOnGround())
    { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FPlayerAttackCollisionCommand>(Test, *It)); return true; }
  }
  if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Start owned DevMap PIE after PlayerAttackCollision test started")); return true; }
  return false;
 }
private:
 FAutomationTestBase* Test; double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerAttackCollisionPIE, "Khazan.Combat.PlayerAttackCollision.PIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerAttackCollisionPIE::RunTest(const FString& Parameters)
{
 FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForPlayerAttackCollisionPIE>(this)); return true;
}
#endif
