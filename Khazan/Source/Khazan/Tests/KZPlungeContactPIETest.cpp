#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/PlayerAbility/KZFallAbility.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Attribute/KZAttributeSet.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/App.h"

namespace KZPlungeContactQA
{
class FRun : public IAutomationLatentCommand
{
public:
 FRun(FAutomationTestBase* T, AKZPlayer* P):Test(T),Player(P),Deadline(FPlatformTime::Seconds()+90.)
 {
  Original=P->GetActorTransform(); OriginalMode=P->GetCharacterMovement()->MovementMode;
  OriginalPawn=P->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn);
  ASC=Cast<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent());
  OldHP=ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()); OldST=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
  Fixed=FApp::UseFixedTimeStep();Delta=FApp::GetFixedDeltaTime();FApp::SetUseFixedTimeStep(true);FApp::SetFixedDeltaTime(1./60.);
  for(const FGameplayAbilitySpec& S:ASC->GetActivatableAbilities())
   if(auto* A=Cast<UKZFallAbility>(S.Ability);A&&A->IsPlungeAttack()){Fall=A;Handle=S.Handle;break;}
  Floor=P->GetWorld()->SpawnActor<AStaticMeshActor>();
  Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
  Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
  Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
  Floor->SetActorLocation(FVector(0,0,9990));Floor->SetActorScale3D(FVector(30,30,.2));
 }
 ~FRun() override { Cleanup(); }
 bool Update() override
 {
  if(!Player.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Plunge contact fixture expired"));Cleanup();return true;}
  auto* P=Player.Get();auto* CMC=P->GetCharacterMovement();const float Now=P->GetWorld()->GetTimeSeconds();
  if(!Started)
  {
   ASC->CancelAllAbilities();P->HandleInputMoveReleased();ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),OldHP);ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),OldST);
   FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   UClass* Class=LoadClass<AKZMonster>(nullptr,TEXT("/Game/Bluprints/Monsters/BP_Monster_Swordsman.BP_Monster_Swordsman_C"));
   Monster=P->GetWorld()->SpawnActor<AKZMonster>(Class,FVector(0,0,10100),FRotator::ZeroRotator,Params);
   if(!Test->TestTrue(TEXT("Real granted plunge and initialized monster"),Fall.IsValid()&&Monster.IsValid())){Cleanup();return true;}
   if(auto* AI=Cast<AAIController>(Monster->GetController());AI&&AI->BrainComponent)AI->BrainComponent->PauseLogic(TEXT("Owned plunge contact"));
   Monster->GetAbilitySystemComponent()->CancelAllAbilities();Monster->GetCharacterMovement()->StopMovementImmediately();
   const float MH=Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   Monster->SetActorLocation(FVector(0,0,10000+MH));
   Test->TestFalse(TEXT("Monster cannot be a character movement base"),Monster->CanBeBaseForCharacter(P));
   P->SetActorLocationAndRotation(FVector(0,0,10000+2*MH+P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+150),FRotator::ZeroRotator);
   CMC->StopMovementImmediately();CMC->SetMovementMode(MOVE_Falling);
   if(!Test->TestTrue(TEXT("Actual falling plunge activates"),ASC->TryActivateAbility(Handle))){Cleanup();return true;}
   Fall=Cast<UKZFallAbility>(ASC->FindAbilitySpecFromHandle(Handle)->GetPrimaryInstance());
   if(!Test->TestTrue(TEXT("Activated plunge has its live execution instance"),Fall.IsValid())){Cleanup();return true;}
   Test->TestEqual(TEXT("Plunge passes pawn bodies while keeping object-query damage"),P->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn),ECR_Overlap);
   Start=Now;Started=true;return false;
  }
  if(Round==1 && Now-Start>.06f)
  {
   ASC->CancelAbilityHandle(Handle);
   Test->TestEqual(TEXT("Airborne cancellation restores original pawn collision"),P->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn),OriginalPawn);
   Test->TestFalse(TEXT("Canceled plunge ended"),Fall->IsActive());Cleanup();return true;
  }
  Test->TestFalse(TEXT("Player never uses monster as movement base"),P->GetMovementBase()&&P->GetMovementBase()->GetOwner()==Monster.Get());
  if(CMC->IsMovingOnGround() && !Fall->IsActive())
  {
   Test->TestTrue(TEXT("Plunge landed on actual ground below monster"),P->GetActorLocation().Z<10000+P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+10);
   Test->TestEqual(TEXT("Normal completion restores original pawn collision"),P->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn),OriginalPawn);
   Test->AddInfo(FString::Printf(TEXT("PLUNGE_CONTACT landed z=%g monsterZ=%g base=%s elapsed=%g"),P->GetActorLocation().Z,Monster->GetActorLocation().Z,*GetNameSafe(P->GetMovementBase()),Now-Start));
   Monster->Destroy();Monster.Reset();Round=1;Started=false;
  }
  return false;
 }
private:
 void Cleanup()
 {
  if(Cleaned)return;Cleaned=true;
  if(Player.IsValid()){ASC->CancelAllAbilities();Player->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,OriginalPawn);Player->SetActorTransform(Original);Player->GetCharacterMovement()->StopMovementImmediately();Player->GetCharacterMovement()->SetMovementMode(OriginalMode);ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),OldHP);ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),OldST);}
  if(Monster.IsValid())Monster->Destroy();if(Floor.IsValid())Floor->Destroy();FApp::SetUseFixedTimeStep(Fixed);FApp::SetFixedDeltaTime(Delta);
 }
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Monster;TWeakObjectPtr<AStaticMeshActor> Floor;TWeakObjectPtr<UKZFallAbility> Fall;TWeakObjectPtr<UKZAbilitySystemComponent> ASC;FGameplayAbilitySpecHandle Handle;
 FTransform Original;EMovementMode OriginalMode=MOVE_None;ECollisionResponse OriginalPawn=ECR_Block;float OldHP=0,OldST=0,Start=0;double Deadline,Delta;int32 Round=0;bool Fixed=false,Started=false,Cleaned=false;
};
class FWait : public IAutomationLatentCommand
{
public:explicit FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
 bool Update() override {for(const auto& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Start owned PIE for plunge contact"));return true;}return false;}
private:FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlungeContactPIE,"Khazan.CombatImpact.Plunge.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZPlungeContactPIE::RunTest(const FString& Parameters){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZPlungeContactQA::FWait>(this));return true;}
#endif
