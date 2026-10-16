// Development-only real gameplay-pawn secondary physics verification. Never saves assets/maps.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Camera/CameraActor.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "BoneControllers/AnimNode_RigidBody.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsSimulation.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsActorHandle.h"
#include "UObject/UnrealType.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace
{
const TCHAR* Families[]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
class FPhysicsRun final:public IAutomationLatentCommand
{
    FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Monster;
    TWeakObjectPtr<AStaticMeshActor> Floor;TWeakObjectPtr<ACameraActor> Camera;
    TArray<TSharedPtr<FJsonValue>> Rows;TMap<FString,FQuat> Previous;TMap<FString,double> Peaks,Steps;TMap<FString,int32> Contacts,Responses,SimCounts;
    FTransform SavedPlayer;float Start=0.f;int32 Family=-1,Stage=0;double Deadline=FPlatformTime::Seconds()+300.;
    bool bFinite=true;int32 Samples=0;FString Output;UAnimMontage* Attack=nullptr;FName AttackSection;TMap<FString,FString> WorstBone;TMap<FString,int32> WorstStage;
    TMap<FString,double> RenderedPeaks,PeakAges;
public:
    FPhysicsRun(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),SavedPlayer(P->GetActorTransform())
    {
        Output=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_OUT"));
        for(TActorIterator<AKZMonster> I(P->GetWorld());I;++I)if(AAIController* AI=Cast<AAIController>(I->GetController()))if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("Owned secondary physics QA"));
        Floor=P->GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,10000),FRotator::ZeroRotator);
        Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
        Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube")));
        Floor->SetActorScale3D(FVector(50,50,.2));Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        Camera=P->GetWorld()->SpawnActor<ACameraActor>();P->GetController<APlayerController>()->SetViewTarget(Camera.Get());
    }
    ~FPhysicsRun(){Cleanup();}
    void Cleanup()
    {
        if(Monster.IsValid()){Monster->GetAbilitySystemComponent()->CancelAllAbilities();Monster->Destroy();Monster.Reset();}
        if(Player.IsValid()){Player->SetActorTransform(SavedPlayer);Player->GetController<APlayerController>()->SetViewTarget(Player.Get());}
        if(Camera.IsValid()){Camera->Destroy();Camera.Reset();}if(Floor.IsValid()){Floor->Destroy();Floor.Reset();}
    }
    bool Begin()
    {
        if(Family<0 && FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_FAMILY"))==TEXT("Yetuga"))Family=4;
        if(++Family>=UE_ARRAY_COUNT(Families))return false;
        UClass* Class=LoadClass<AKZMonster>(nullptr,*FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),Families[Family],Families[Family]));
        if(!Class){Test->AddError(TEXT("Monster class missing"));return false;}
        FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Monster=Player->GetWorld()->SpawnActor<AKZMonster>(Class,FVector(0,0,10200),FRotator::ZeroRotator,Params);
        if(!Monster.IsValid())return false;
        if(AAIController* AI=Cast<AAIController>(Monster->GetController())){AI->StopMovement();if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("Owned secondary physics QA"));}
        const double H=Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        Monster->SetActorLocation(FVector(0,0,10010+H+UCharacterMovementComponent::MIN_FLOOR_DIST));Monster->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        Player->SetActorLocation(FVector(-1500,0,10010+Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST));
        Camera->SetActorLocation(Monster->GetActorLocation()+FVector(H*2.5,-H*4,H*.7));Camera->SetActorRotation((Monster->GetActorLocation()-Camera->GetActorLocation()).Rotation());
        Monster->GetAbilitySystemComponent()->CancelAllAbilities();Attack=nullptr;AttackSection=NAME_None;
        for(const auto& Spec:Monster->GetAbilitySystemComponent()->GetActivatableAbilities())
            if(auto* A=Cast<UKZComboActionAbility>(Spec.Ability.Get());A && A->GetComboDefinition())
            {
                const FArrayProperty* Property=FindFProperty<FArrayProperty>(UKZComboDefinitionData::StaticClass(),TEXT("Nodes"));
                const auto* Nodes=Property->ContainerPtrToValuePtr<TArray<FKZComboNode>>(A->GetComboDefinition());
                for(const auto& N:*Nodes)if(N.Montage && !N.AttackWindows.IsEmpty()){Attack=N.Montage;AttackSection=N.SectionName;break;}
            }
        Test->TestNotNull(TEXT("Actual authored attack montage found"),Attack);
        Previous.Reset();Peaks.Reset();Steps.Reset();Contacts.Reset();Responses.Reset();SimCounts.Reset();WorstBone.Reset();WorstStage.Reset();RenderedPeaks.Reset();PeakAges.Reset();Samples=0;bFinite=true;Stage=0;Start=Player->GetWorld()->GetTimeSeconds();return true;
    }
    void Sample()
    {
        ++Samples;TInlineComponentArray<USkeletalMeshComponent*> Meshes(Monster.Get());
        for(auto* Mesh:Meshes)
        {
            if(!Mesh->GetSkeletalMeshAsset())continue;
            Mesh->HandleExistingParallelEvaluationTask(true,true);
            Test->TestFalse(TEXT("World ragdoll stays off"),Mesh->IsSimulatingPhysics());
            for(const FTransform& T:Mesh->GetComponentSpaceTransforms())bFinite&=!T.ContainsNaN() && T.GetTranslation().Size()<10000.;
            UAnimInstance* Post=Mesh->GetPostProcessInstance();if(!Post)continue;
            const FString Key=Mesh->GetName();
            for(TFieldIterator<FStructProperty> It(Post->GetClass());It;++It)if(It->Struct==FAnimNode_RigidBody::StaticStruct())
            {
                auto* Node=It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Post);auto* Sim=Node->GetSimulation();if(!Sim)continue;
                UPhysicsAsset* PA=Node->OverridePhysicsAsset;TMap<FName,ImmediatePhysics::FActorHandle*> Named;int32 Simulated=0;
                for(int32 I=0;I<Sim->NumActors();++I){auto* A=Sim->GetActorHandle(I);Named.Add(A->GetName(),A);if(A->IsSimulated())++Simulated;
                    if(!FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_NO_CONTACT")).IsEmpty())Sim->SetHasCollision(A,false);}
                SimCounts.FindOrAdd(Key)=Simulated;
                for(UPhysicsConstraintTemplate* Joint:PA->ConstraintSetup)
                {
                    const auto& C=Joint->DefaultInstance;auto* A=Named.FindRef(C.ConstraintBone1);auto* B=Named.FindRef(C.ConstraintBone2);if(!A || !B || !A->IsSimulated())continue;
                    const FTransform F1=C.GetRefFrame(EConstraintFrame::Frame1)*A->GetWorldTransform(),F2=C.GetRefFrame(EConstraintFrame::Frame2)*B->GetWorldTransform();
                    const FQuat Q=F1.GetRelativeTransform(F2).GetRotation();const double Angle=FMath::RadiansToDegrees(Q.AngularDistance(FQuat::Identity));
                    bFinite&=FMath::IsFinite(Angle);if(Angle>Peaks.FindRef(Key)){Peaks.FindOrAdd(Key)=Angle;WorstBone.FindOrAdd(Key)=C.ConstraintBone1.ToString();WorstStage.FindOrAdd(Key)=Stage;PeakAges.FindOrAdd(Key)=Player->GetWorld()->GetTimeSeconds()-Start;}
                    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();const auto& Pose=Mesh->GetComponentSpaceTransforms();
                    const int32 Child=Ref.FindBoneIndex(C.ConstraintBone1),Parent=Ref.FindBoneIndex(C.ConstraintBone2);
                    if(Pose.IsValidIndex(Child) && Pose.IsValidIndex(Parent))
                    {
                        const FTransform ChildFrame=C.GetRefFrame(EConstraintFrame::Frame1)*Pose[Child],ParentFrame=C.GetRefFrame(EConstraintFrame::Frame2)*Pose[Parent];
                        const double RenderedAngle=FMath::RadiansToDegrees(ChildFrame.GetRelativeTransform(ParentFrame).GetRotation().AngularDistance(FQuat::Identity));
                        RenderedPeaks.FindOrAdd(Key)=FMath::Max(RenderedPeaks.FindRef(Key),RenderedAngle);
                    }
                    const FString BoneKey=Key+TEXT("/")+C.ConstraintBone1.ToString();
                    if(const FQuat* Prev=Previous.Find(BoneKey)){const double Step=FMath::RadiansToDegrees(Q.AngularDistance(*Prev));Steps.FindOrAdd(Key)=FMath::Max(Steps.FindRef(Key),Step);if(Step>.1)Responses.FindOrAdd(BoneKey)=1;}
                    Previous.Add(BoneKey,Q);
                }
                Sim->VisitCollisions([&](const ImmediatePhysics::FSimulation::FCollisionData& C){Contacts.FindOrAdd(Key)+=C.GetNumManifoldPoints();},Chaos::ECollisionVisitorFlags::VisitDefault);
            }
        }
    }
    bool FinishFamily()
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Families[Family]);Row->SetBoolField(TEXT("finite"),bFinite);Row->SetNumberField(TEXT("samples"),Samples);Row->SetStringField(TEXT("attack_montage"),GetPathNameSafe(Attack));Row->SetStringField(TEXT("attack_section"),AttackSection.ToString());
        TArray<TSharedPtr<FJsonValue>> Parts;
        for(const auto& Pair:SimCounts)
        {
            auto P=MakeShared<FJsonObject>();int32 Responding=0;for(const auto& R:Responses)if(R.Key.StartsWith(Pair.Key+TEXT("/")))Responding+=R.Value;
            P->SetStringField(TEXT("component"),Pair.Key);P->SetNumberField(TEXT("simulated"),Pair.Value);P->SetNumberField(TEXT("responding"),Responding);P->SetNumberField(TEXT("joint_peak_deg"),Peaks.FindRef(Pair.Key));P->SetNumberField(TEXT("step_peak_deg"),Steps.FindRef(Pair.Key));P->SetNumberField(TEXT("contacts"),Contacts.FindRef(Pair.Key));P->SetStringField(TEXT("worst_bone"),WorstBone.FindRef(Pair.Key));P->SetNumberField(TEXT("worst_stage"),WorstStage.FindRef(Pair.Key));Parts.Add(MakeShared<FJsonValueObject>(P));
            P->SetNumberField(TEXT("rendered_joint_peak_deg"),RenderedPeaks.FindRef(Pair.Key));
            P->SetNumberField(TEXT("peak_age_sec"),PeakAges.FindRef(Pair.Key));
            Test->TestTrue(TEXT("Secondary solver simulates real bodies"),Pair.Value>0);Test->TestTrue(TEXT("Secondary bones respond to actual motion"),Responding>0);
            // Technical bounded-motion QA, reused player cloth45 degree envelope.
            Test->TestTrue(TEXT("Secondary response stays within the player's cloth QA envelope"),Peaks.FindRef(Pair.Key)<45.);
        }
        Test->TestTrue(TEXT("At least one real secondary solver for this family"),!Parts.IsEmpty());Test->TestTrue(TEXT("All final bones finite and character scale"),bFinite);
        if(Family==2){TInlineComponentArray<USkeletalMeshComponent*> Meshes(Monster.Get());for(auto* M:Meshes)if(M->ComponentHasTag(TEXT("MonsterBodyPart"))){Test->TestTrue(TEXT("Modular armor evaluates independently"),M->LeaderPoseComponent==nullptr && M->GetAnimInstance()!=nullptr);}}
        Row->SetArrayField(TEXT("parts"),Parts);Rows.Add(MakeShared<FJsonValueObject>(Row));Monster->Destroy();Monster.Reset();return Begin();
    }
    bool Update()override
    {
        if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Secondary physics PIE watchdog"));return true;}
        if(Family<0 && !Begin())return true;if(!Monster.IsValid())return true;
        const float Age=Player->GetWorld()->GetTimeSeconds()-Start;
        Sample();
        if(Stage==0 && Age>2.f){Stage=1;}
        if(Stage==1){Monster->AddMovementInput(FVector::ForwardVector);if(Age>4.f){Stage=2;Monster->GetCharacterMovement()->StopMovementImmediately();Monster->SetActorRotation(FRotator(0,90,0));}}
        if(Stage==2 && Age>5.f){Stage=3;if(Attack){auto* Anim=Monster->GetMesh()->GetAnimInstance();Anim->Montage_Play(Attack);if(!AttackSection.IsNone())Anim->Montage_JumpToSection(AttackSection,Attack);}}
        if(Stage==3 && Age>8.f){Stage=4;Monster->GetMesh()->GetAnimInstance()->Montage_Stop(0.f);Monster->PlayHitReaction(EKZHitReactionType::Short,Player.Get());}
        if(Stage==4 && Age>10.f){Stage=5;Monster->GetAbilitySystemComponent()->CancelAllAbilities();}
        if(Stage==5 && Age>12.f)
        {
            if(FApp::CanEverRender())FScreenshotRequest::RequestScreenshot(FPaths::Combine(Output,FString::Printf(TEXT("Physics_%02d.png"),Family)),false,false);
            Stage=6;
        }
        if(Stage==6 && Age>12.5f && !FinishFamily())
        {
            auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("families"),Rows);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*FPaths::Combine(Output,TEXT("Runtime.json")));Cleanup();return true;
        }
        return false;
    }
};
class FFindPhysicsPlayer final:public IAutomationLatentCommand
{
    FAutomationTestBase* Test;double Deadline=FPlatformTime::Seconds()+90.;
public:
    FFindPhysicsPlayer(FAutomationTestBase* T):Test(T){}
    bool Update()override
    {
        for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE && C.World())for(TActorIterator<AKZPlayer> I(C.World());I;++I)if(I->GetController())
        {FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FPhysicsRun>(Test,*I));return true;}
        if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Actual PIE Player not ready"));return true;}return false;
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSecondaryPhysicsPIE,"Khazan.MonsterSecondaryPhysics.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterSecondaryPhysicsPIE::RunTest(const FString&){ADD_LATENT_AUTOMATION_COMMAND(FFindPhysicsPlayer(this));return true;}
#endif
