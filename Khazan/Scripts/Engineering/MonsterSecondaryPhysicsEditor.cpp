// Editor-only asset author/physics QA, compiled exclusively in the isolated work project.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "Animation/Skeleton.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_LinkedInputPose.h"
#include "AnimGraphNode_CopyPoseFromMesh.h"
#include "AnimGraphNode_RigidBody.h"
#include "AnimGraphNode_LocalToComponentSpace.h"
#include "AnimGraphNode_ComponentToLocalSpace.h"
#include "Factories/AnimBlueprintFactory.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "GameFramework/Character.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsAdapters.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsActorHandle.h"

namespace KZMonsterPhysics
{
TSharedPtr<FJsonObject> ReadPlan()
{
    FString Text; TSharedPtr<FJsonObject> Plan;
    if (FFileHelper::LoadFileToString(Text, *(FPaths::ProjectSavedDir()/TEXT("MonsterSecondaryPhysicsPlan.json"))))
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Plan);
    return Plan;
}
bool Write(const FString& Name,const TSharedPtr<FJsonObject>& Data)
{
    FString Text; return FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Text)) &&
        FFileHelper::SaveStringToFile(Text,*(FPaths::ProjectSavedDir()/Name));
}
TArray<FTransform> UnitPose(USkeletalMesh* Mesh)
{
    const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> Unit;
    const double Scale=Ref.GetRefBonePose()[0].GetScale3D().X;
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        FTransform T=Ref.GetRefBonePose()[I];if(I>0)T=T*Unit[Ref.GetParentIndex(I)];Unit.Add(T);
    }
    for(auto& T:Unit){T.SetTranslation(T.GetTranslation()/Scale);T.SetScale3D(FVector::OneVector);}
    return Unit;
}
TMap<int32,int32> Weighted(USkeletalMesh* Mesh)
{
    TMap<int32,int32> Counts;
    if(!Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty())return Counts;
    for(const auto& Section:Mesh->GetImportedModel()->LODModels[0].Sections)
        for(const auto& Vertex:Section.SoftVertices)
            for(int32 I=0;I<MAX_TOTAL_INFLUENCES;++I)
                if(Vertex.InfluenceWeights[I] && Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[I]))
                    ++Counts.FindOrAdd(Section.BoneMap[Vertex.InfluenceBones[I]]);
    return Counts;
}

// Explicit cloth/hair chains only. Unclassified facial/muscle B_* controls,
// rigid rock/ice/weapon markers retain their original animation-driven poses.
int32 Kind(FName Name,bool bGiant)
{
    const FString N=Name.ToString();
    if(N.Contains(TEXT("BoneRoot")) || N.Contains(TEXT("Dummy")) || N.Contains(TEXT("Rock")) || N.Contains(TEXT("GIB")))return 0;
    if(N.Contains(TEXT("Cloth")) || N.StartsWith(TEXT("B_Cape_")) || N.StartsWith(TEXT("SM_Cape_")) || N.StartsWith(TEXT("B_Skirt_")) || N.StartsWith(TEXT("B_Belt_")) || N.StartsWith(TEXT("B_Leather_")))return 2;
    if(N.StartsWith(TEXT("Hair_")) || N.StartsWith(TEXT("B_Hair_")) || N.StartsWith(TEXT("B_HeadHair_")))return 1;
    return 0;
}
TMap<int32,FBox> SkinBounds(USkeletalMesh* Mesh,const TArray<FTransform>& Unit)
{
    TMap<int32,FBox> Bounds;
    if(!Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty())return Bounds;
    const double Scale=Mesh->GetRefSkeleton().GetRefBonePose()[0].GetScale3D().X;
    for(const auto& Section:Mesh->GetImportedModel()->LODModels[0].Sections)
        for(const auto& V:Section.SoftVertices)
        {
            int32 Best=0;
            for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J]>V.InfluenceWeights[Best])Best=J;
            if(!V.InfluenceWeights[Best] || !Section.BoneMap.IsValidIndex(V.InfluenceBones[Best]))continue;
            const int32 Bone=Section.BoneMap[V.InfluenceBones[Best]];
            FBox* B=Bounds.Find(Bone);if(!B)B=&Bounds.Add(Bone,FBox(ForceInit));
            *B+=Unit[Bone].InverseTransformPosition(FVector(V.Position)/Scale);
        }
    return Bounds;
}
bool Save(UObject* Asset,TArray<TSharedPtr<FJsonValue>>& Saved)
{
    if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")) || !Asset->GetPathName().StartsWith(TEXT("/Game/")))return false;
    UPackage* Package=Asset->GetOutermost();Package->MarkPackageDirty();
    FSavePackageArgs A;A.TopLevelFlags=RF_Public|RF_Standalone;
    const bool bOK=UPackage::SavePackage(Package,Asset,*FPackageName::LongPackageNameToFilename(Package->GetName(),FPackageName::GetAssetPackageExtension()),A);
    if(bOK)Saved.Add(MakeShared<FJsonValueString>(Package->GetName()));return bOK;
}
template<typename T>T* Node(UEdGraph* Graph,int32 X)
{
    T* N=NewObject<T>(Graph);Graph->AddNode(N);N->CreateNewGuid();N->PostPlacedNewNode();N->NodePosX=X;N->AllocateDefaultPins();return N;
}
UAnimBlueprint* Animation(USkeletalMesh* Mesh,UPhysicsAsset* PA,bool bCopy,TArray<TSharedPtr<FJsonValue>>& Saved)
{
    const FString Path=bCopy?TEXT("/Game/Monsters/Shared/Physics/ABP_EliteParts_CopyPose"):
        FPackageName::GetLongPackagePath(Mesh->GetOutermost()->GetName())/TEXT("Physics")/(TEXT("ABP_")+Mesh->GetName()+TEXT("_Secondary"));
    if(auto* Existing=LoadObject<UAnimBlueprint>(nullptr,*Path,nullptr,LOAD_NoWarn))return Existing;
    auto* Factory=NewObject<UAnimBlueprintFactory>();Factory->ParentClass=UAnimInstance::StaticClass();Factory->TargetSkeleton=Mesh->GetSkeleton();Factory->PreviewSkeletalMesh=Mesh;
    auto* BP=Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(),CreatePackage(*Path),*FPackageName::GetLongPackageAssetName(Path),RF_Public|RF_Standalone|RF_Transactional,nullptr,GWarn));
    if(!BP)return nullptr;FAssetRegistryModule::AssetCreated(BP);
    TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs);
    UEdGraph** Found=Graphs.FindByPredicate([](UEdGraph* G){return G->GetFName()==TEXT("AnimGraph");});if(!Found)return nullptr;
    UEdGraph* G=*Found;UAnimGraphNode_Root* Root=nullptr;
    for(UEdGraphNode* N:TArray<TObjectPtr<UEdGraphNode>>(G->Nodes))if(auto* R=Cast<UAnimGraphNode_Root>(N)){Root=R;R->BreakAllNodeLinks();}else G->RemoveNode(N);
    if(!Root)return nullptr;const UEdGraphSchema* Schema=G->GetSchema();UEdGraphPin* Last=nullptr;
    if(bCopy){auto* Copy=Node<UAnimGraphNode_CopyPoseFromMesh>(G,-900);Copy->Node.bUseAttachedParent=true;Last=Copy->FindPinChecked(TEXT("Pose"));}
    else{auto* Input=Node<UAnimGraphNode_LinkedInputPose>(G,-900);Last=Input->FindPinChecked(TEXT("Pose"));}
    if(PA)
    {
        auto* CS=Node<UAnimGraphNode_LocalToComponentSpace>(G,-700);Schema->TryCreateConnection(Last,CS->FindPinChecked(TEXT("LocalPose")));
        auto* RB=Node<UAnimGraphNode_RigidBody>(G,-450);RB->Node.OverridePhysicsAsset=PA;RB->Node.SimulationSpace=ESimulationSpace::WorldSpace;
        Schema->TryCreateConnection(CS->FindPinChecked(TEXT("ComponentPose")),RB->FindPinChecked(TEXT("ComponentPose")));
        auto* LS=Node<UAnimGraphNode_ComponentToLocalSpace>(G,-200);Schema->TryCreateConnection(RB->FindPinChecked(TEXT("Pose")),LS->FindPinChecked(TEXT("ComponentPose")));Last=LS->FindPinChecked(TEXT("Pose"));
    }
    Schema->TryCreateConnection(Last,Root->FindPinChecked(TEXT("Result")));
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);
    if(BP->Status==BS_Error || !Save(BP,Saved))return nullptr;return BP;
}
FVector Vec(const TSharedPtr<FJsonObject>& O){return FVector(O->GetNumberField(TEXT("X")),O->GetNumberField(TEXT("Y")),O->GetNumberField(TEXT("Z")));}
bool OriginalAnatomy(USkeletalMesh* Mesh,UPhysicsAsset* PA,const TSharedPtr<FJsonObject>& Sources,FString& Provenance)
{
    FString Category;
    const FString Skeleton=GetPathNameSafe(Mesh->GetSkeleton());
    if(Skeleton.Contains(TEXT("Adult")) || Skeleton.Contains(TEXT("EmpireHuman")))Category=TEXT("Adult");
    else if(Skeleton.Contains(TEXT("Elite_M")))Category=TEXT("Elite");
    else if(Skeleton.Contains(TEXT("Halberd")))Category=TEXT("Halberd");
    if(Category.IsEmpty())return false;
    const auto Source=Sources->GetObjectField(Category);Provenance=Source->GetStringField(TEXT("source"));
    const auto& Ref=Mesh->GetRefSkeleton();
    for(const auto& Item:Source->GetArrayField(TEXT("bodies")))
    {
        const auto O=Item->AsObject();FName Name(*O->GetStringField(TEXT("bone")));
        if(Ref.FindBoneIndex(Name)==INDEX_NONE)continue;
        auto* Body=NewObject<USkeletalBodySetup>(PA,NAME_None,RF_Transactional);Body->BoneName=Name;Body->PhysicsType=PhysType_Kinematic;
        Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        const auto Geom=O->GetObjectField(TEXT("geometry"));const TArray<TSharedPtr<FJsonValue>>* Shapes;
        if(Geom->TryGetArrayField(TEXT("SphylElems"),Shapes))for(const auto& Shape:*Shapes)
        {
            const auto S=Shape->AsObject();FKSphylElem E;E.Center=Vec(S->GetObjectField(TEXT("Center")));
            const auto R=S->GetObjectField(TEXT("Rotation"));E.Rotation=FRotator(R->GetNumberField(TEXT("Pitch")),R->GetNumberField(TEXT("Yaw")),R->GetNumberField(TEXT("Roll")));
            E.Radius=S->GetNumberField(TEXT("Radius"));E.Length=S->GetNumberField(TEXT("Length"));E.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Body->AggGeom.SphylElems.Add(E);
        }
        if(Geom->TryGetArrayField(TEXT("SphereElems"),Shapes))for(const auto& Shape:*Shapes)
        {
            const auto S=Shape->AsObject();FKSphereElem E;E.Center=Vec(S->GetObjectField(TEXT("Center")));E.Radius=S->GetNumberField(TEXT("Radius"));Body->AggGeom.SphereElems.Add(E);
        }
        if(Body->AggGeom.GetElementCount()>0)PA->SkeletalBodySetups.Add(Body);
    }
    return PA->SkeletalBodySetups.Num()>0;
}
void FitAnatomy(USkeletalMesh* Mesh,UPhysicsAsset* PA,const TMap<int32,FBox>& Bounds,bool bGiant)
{
    const auto& Ref=Mesh->GetRefSkeleton();
    for(const auto& Pair:Bounds)
    {
        if(Kind(Ref.GetBoneName(Pair.Key),bGiant) || !Pair.Value.IsValid)continue;
        const FVector Size=Pair.Value.GetSize();int32 Axis=0;if(Size.Y>Size[Axis])Axis=1;if(Size.Z>Size[Axis])Axis=2;
        const float Radius=FMath::Min(Size[(Axis+1)%3],Size[(Axis+2)%3])*.5f;
        if(Radius<=KINDA_SMALL_NUMBER)continue;
        auto* B=NewObject<USkeletalBodySetup>(PA,NAME_None,RF_Transactional);B->BoneName=Ref.GetBoneName(Pair.Key);B->PhysicsType=PhysType_Kinematic;
        FKSphylElem E;E.Center=Pair.Value.GetCenter();E.Radius=Radius;E.Length=FMath::Max(0.f,float(Size[Axis])-2.f*Radius);
        FVector Direction=FVector::ZeroVector;Direction[Axis]=1.;E.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Direction).Rotator();B->AggGeom.SphylElems.Add(E);
        B->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);PA->SkeletalBodySetups.Add(B);
    }
}
int32 BodyAncestor(UPhysicsAsset* PA,const FReferenceSkeleton& Ref,int32 I)
{
    while(I>0){I=Ref.GetParentIndex(I);if(PA->FindBodyIndex(Ref.GetBoneName(I))!=INDEX_NONE)return I;}return INDEX_NONE;
}
UPhysicsConstraintTemplate* ReferenceJoint(UPhysicsAsset* Player,int32 Depth,int32 MaxDepth)
{
    UPhysicsConstraintTemplate* Best=nullptr;float Error=MAX_flt;
    auto ChainDepth=[&](FName Bone,FName& Root)
    {
        int32 D=0;Root=Bone;
        while(true){const int32 B=Player->FindBodyIndex(Bone);if(B==INDEX_NONE || Player->SkeletalBodySetups[B]->PhysicsType!=PhysType_Simulated)break;
            ++D;Root=Bone;auto* Parent=Player->ConstraintSetup.FindByPredicate([&](const auto& Q){return Q->DefaultInstance.ConstraintBone1==Bone;});
            if(!Parent)break;Bone=(*Parent)->DefaultInstance.ConstraintBone2;}
        return D;
    };
    for(UPhysicsConstraintTemplate* J:Player->ConstraintSetup)
    {
        const int32 Body=Player->FindBodyIndex(J->DefaultInstance.ConstraintBone1);
        if(Body==INDEX_NONE || Player->SkeletalBodySetups[Body]->PhysicsType!=PhysType_Simulated)continue;
        FName Root;const int32 D=ChainDepth(J->DefaultInstance.ConstraintBone1,Root);int32 ChainMax=D;
        for(UPhysicsConstraintTemplate* Other:Player->ConstraintSetup){FName OtherRoot;const int32 OtherD=ChainDepth(Other->DefaultInstance.ConstraintBone1,OtherRoot);if(OtherRoot==Root)ChainMax=FMath::Max(ChainMax,OtherD);}
        // Compare normalized depths calculated from the two actual skeleton chains.
        const float Fraction=ChainMax>1?float(D-1)/float(ChainMax-1):0.f;
        const float Target=MaxDepth>1?float(Depth-1)/float(MaxDepth-1):0.f;
        const float E=FMath::Abs(Fraction-Target);if(E<Error){Error=E;Best=J;}
    }
    return Best;
}
bool Secondary(USkeletalMesh* Mesh,UPhysicsAsset* PA,UPhysicsAsset* Hair,UPhysicsAsset* Cloth,TArray<TSharedPtr<FJsonValue>>& Detail)
{
    const auto& Ref=Mesh->GetRefSkeleton();const auto Unit=UnitPose(Mesh);const auto Counts=Weighted(Mesh);const auto Bounds=SkinBounds(Mesh,Unit);
    const bool bGiant=Mesh->GetName().Contains(TEXT("Yetuga"))||Mesh->GetName().Contains(TEXT("Apes"));
    const int32 AnatomyBodies=PA->SkeletalBodySetups.Num();
    TSet<int32> Selected;
    for(const auto& P:Counts)if(Kind(Ref.GetBoneName(P.Key),bGiant))
    {
        int32 I=P.Key;while(I>0 && Kind(Ref.GetBoneName(I),bGiant)){Selected.Add(I);I=Ref.GetParentIndex(I);}
    }
    TArray<int32> Ordered=Selected.Array();Ordered.Sort();PA->UpdateBodySetupIndexMap();
    // Keep unweighted attachment pivots kinematic, and introduce only real anchors.
    for(int32 I:Ordered)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        if(Selected.Contains(Parent) || PA->FindBodyIndex(Ref.GetBoneName(Parent))!=INDEX_NONE)continue;
        auto* B=NewObject<USkeletalBodySetup>(PA,NAME_None,RF_Transactional);B->BoneName=Ref.GetBoneName(Parent);B->PhysicsType=PhysType_Kinematic;
        FKSphereElem E;E.Radius=Hair->SkeletalBodySetups.Last()->AggGeom.SphylElems[0].Radius;B->AggGeom.SphereElems.Add(E);PA->SkeletalBodySetups.Add(B);PA->UpdateBodySetupIndexMap();
    }
    const double Wrapper=Ref.GetRefBonePose()[0].GetScale3D().X;
    for(int32 I:Ordered)
    {
        const int32 K=Kind(Ref.GetBoneName(I),bGiant);UPhysicsAsset* Reference=K==1?Hair:Cloth;
        int32 Depth=1,Root=I;while(Selected.Contains(Ref.GetParentIndex(Root))){++Depth;Root=Ref.GetParentIndex(Root);}
        int32 MaxDepth=Depth;for(int32 Candidate:Ordered){int32 Anc=Candidate,D=1;while(Anc>0 && Anc!=Root){Anc=Ref.GetParentIndex(Anc);++D;}if(Anc==Root)MaxDepth=FMath::Max(MaxDepth,D);}
        auto* Template=ReferenceJoint(Reference,Depth,MaxDepth);if(!Template)return false;
        const USkeletalBodySetup* RB=Reference->SkeletalBodySetups[Reference->FindBodyIndex(Template->DefaultInstance.ConstraintBone1)];
        const float Radius=RB->AggGeom.SphylElems.IsEmpty()?Hair->SkeletalBodySetups.Last()->AggGeom.SphylElems[0].Radius:RB->AggGeom.SphylElems[0].Radius;
        FVector Segment=FVector::ZeroVector;
        for(int32 Child:Ordered)if(Ref.GetParentIndex(Child)==I){Segment=Unit[I].InverseTransformPosition(Unit[Child].GetLocation());if(!Segment.IsNearlyZero())break;}
        if(Segment.IsNearlyZero())Segment=Unit[I].InverseTransformVector(Unit[I].GetLocation()-Unit[Ref.GetParentIndex(I)].GetLocation());
        const FBox* Support=Bounds.Find(I);if(Segment.IsNearlyZero() && Support)Segment=Support->GetCenter();
        const float Length=FMath::Max(float(Segment.Size()),2.f*Radius);
        if(Segment.IsNearlyZero())Segment=FVector::UpVector*Length;
        auto* B=NewObject<USkeletalBodySetup>(PA,NAME_None,RF_Transactional);B->BoneName=Ref.GetBoneName(I);
        B->PhysicsType=Counts.FindRef(I)>0?PhysType_Simulated:PhysType_Kinematic;
        B->DefaultInstance.LinearDamping=RB->DefaultInstance.LinearDamping;B->DefaultInstance.AngularDamping=RB->DefaultInstance.AngularDamping;
        // Reuse the player's mass-per-length, not the giant's anatomy mass.
        const float ReferenceLength=RB->AggGeom.SphylElems.IsEmpty()?Length:RB->AggGeom.SphylElems[0].Length+2.f*Radius;
        const float Density=RB->DefaultInstance.GetMassOverride()/ReferenceLength;
        B->DefaultInstance.SetMassOverride(Density*Length,true);B->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        FKSphylElem E;E.Radius=Radius;E.Length=Length-2.f*Radius;E.Center=Support?Support->GetCenter():Segment*.5;
        E.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Segment.GetSafeNormal()).Rotator();E.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);B->AggGeom.SphylElems.Add(E);
        PA->SkeletalBodySetups.Add(B);PA->UpdateBodySetupIndexMap();
        if(B->PhysicsType!=PhysType_Simulated)continue;
        const int32 Parent=BodyAncestor(PA,Ref,I);if(Parent==INDEX_NONE)return false;
        auto* J=NewObject<UPhysicsConstraintTemplate>(PA,NAME_None,RF_Transactional);auto& C=J->DefaultInstance;
        C.ProfileInstance=Template->DefaultInstance.ProfileInstance;C.JointName=B->BoneName;C.ConstraintBone1=B->BoneName;C.ConstraintBone2=Ref.GetBoneName(Parent);
        C.SetRefFrame(EConstraintFrame::Frame1,FTransform::Identity);FTransform F=Unit[I].GetRelativeTransform(Unit[Parent]);F.SetTranslation(F.GetTranslation()/Wrapper);C.SetRefFrame(EConstraintFrame::Frame2,F);
        C.SetDisableCollision(true);J->SetDefaultProfile(C);PA->ConstraintSetup.Add(J);
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("bone"),B->BoneName.ToString());Row->SetStringField(TEXT("kind"),K==1?TEXT("Hair"):TEXT("Cloth"));
        Row->SetStringField(TEXT("player_body"),RB->BoneName.ToString());Row->SetStringField(TEXT("player_asset"),Reference->GetPathName());
        Row->SetNumberField(TEXT("radius_cm"),Radius);Row->SetNumberField(TEXT("mass_kg"),Density*Length);Row->SetNumberField(TEXT("angular_damping"),B->DefaultInstance.AngularDamping);
        Row->SetNumberField(TEXT("swing_deg"),C.GetAngularSwing1Limit());Row->SetNumberField(TEXT("spring"),C.ProfileInstance.AngularDrive.SlerpDrive.Stiffness);Detail.Add(MakeShared<FJsonValueObject>(Row));
    }
    // Same contact-pair separation as Player: secondary/self disabled; anatomy enabled.
    for(int32 A=0;A<PA->SkeletalBodySetups.Num();++A)for(int32 B=A+1;B<PA->SkeletalBodySetups.Num();++B)
    {
        const bool SA=PA->SkeletalBodySetups[A]->PhysicsType==PhysType_Simulated,SB=PA->SkeletalBodySetups[B]->PhysicsType==PhysType_Simulated;
        if(SA==SB || (!SA && A>=AnatomyBodies) || (!SB && B>=AnatomyBodies))PA->DisableCollision(A,B);
        else PA->EnableCollision(A,B);
    }
    for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup)PA->DisableCollision(PA->FindBodyIndex(J->DefaultInstance.ConstraintBone1),PA->FindBodyIndex(J->DefaultInstance.ConstraintBone2));
    // Reuse the player's rotation-invariant thin-body inertia conditioning.
    auto* Probe=NewObject<USkeletalMeshComponent>();Probe->SetSkeletalMesh(Mesh);TArray<FBodyInstance*> Bodies;Probe->InstantiatePhysicsAssetBodiesRefPose(*PA,Bodies);
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated)
    {
        const auto Setup=ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(B->BoneName)],FTransform::Identity);
        FVector Diagonal;
        for(int32 Axis=0;Axis<3;++Axis){FVector Basis=FVector::ZeroVector;Basis[Axis]=1.;Diagonal[Axis]=Setup.CoMTransform.GetRotation().RotateVector(FVector(Setup.Inertia)*Setup.CoMTransform.GetRotation().UnrotateVector(Basis))[Axis];}
        const double Target=FVector(Setup.Inertia).GetMax();const FVector Q=FVector(.5*Target)/(FVector(.5*(Diagonal.X+Diagonal.Y+Diagonal.Z))-Diagonal);
        const double Det=FMath::Pow(Q.X*Q.Y*Q.Z,1./5.);B->DefaultInstance.InertiaTensorScale=FVector(FMath::Sqrt(Q.X/Det),FMath::Sqrt(Q.Y/Det),FMath::Sqrt(Q.Z/Det));
    }
    for(auto* B:Bodies){if(B->IsValidBodyInstance())B->TermBody(true);delete B;}
    PA->SolverSettings=Cloth->SolverSettings;PA->UpdateBoundsBodiesArray();PA->UpdateBodySetupIndexMap();return true;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSecondaryAudit,"Khazan.MonsterSecondaryPhysics.Audit",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterSecondaryAudit::RunTest(const FString& Parameters)
{
    using namespace KZMonsterPhysics;
    auto Plan=ReadPlan();if(!TestTrue(TEXT("Owned plan present"),Plan.IsValid()))return false;
    TArray<TSharedPtr<FJsonValue>> Rows;
    for(const auto& Value:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Value->AsString());
        if(!Mesh)continue;
        const auto& Ref=Mesh->GetRefSkeleton();const auto Counts=Weighted(Mesh);const auto Unit=UnitPose(Mesh);
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());
        Row->SetStringField(TEXT("skeleton"),GetPathNameSafe(Mesh->GetSkeleton()));
        Row->SetNumberField(TEXT("root_scale"),Ref.GetRefBonePose()[0].GetScale3D().X);
        TArray<TSharedPtr<FJsonValue>> Bones;
        for(int32 I=0;I<Ref.GetNum();++I)
        {
            auto Bone=MakeShared<FJsonObject>();Bone->SetStringField(TEXT("name"),Ref.GetBoneName(I).ToString());
            Bone->SetStringField(TEXT("parent"),I>0?Ref.GetBoneName(Ref.GetParentIndex(I)).ToString():TEXT("None"));
            Bone->SetNumberField(TEXT("weighted_vertices"),Counts.FindRef(I));
            Bone->SetStringField(TEXT("unit_location"),Unit[I].GetLocation().ToString());
            Bones.Add(MakeShared<FJsonValueObject>(Bone));
        }
        Row->SetArrayField(TEXT("bones"),Bones);Rows.Add(MakeShared<FJsonValueObject>(Row));
        AddInfo(FString::Printf(TEXT("MonsterPhysicsAudit %s bones=%d weighted=%d"),*Mesh->GetName(),Ref.GetNum(),Counts.Num()));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("meshes"),Rows);
    return Write(TEXT("MonsterSecondaryPhysicsAudit.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSecondaryAuthor,"Khazan.MonsterSecondaryPhysics.Author",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterSecondaryAuthor::RunTest(const FString& Parameters)
{
    using namespace KZMonsterPhysics;auto Plan=ReadPlan();if(!Plan || !FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    FString Text;TSharedPtr<FJsonObject> Sources;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectSavedDir()/TEXT("MonsterSecondaryPhysicsOriginalShapes.json")));FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Sources);if(!Sources)return false;
    auto* Hair=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/_Art/Player/Character/Meshs/Hair/Player_Original_Hair_RigidBody_PhysicsAsset"));
    auto* Cloth=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset"));if(!Hair || !Cloth)return false;
    TArray<TSharedPtr<FJsonValue>> Rows,Saved;
    for(const auto& Value:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Value->AsString());if(!Mesh)continue;
        const FString Path=FPackageName::GetLongPackagePath(Mesh->GetOutermost()->GetName())/TEXT("Physics")/(TEXT("PA_")+Mesh->GetName());
        if(LoadObject<UPhysicsAsset>(nullptr,*Path,nullptr,LOAD_NoWarn)){AddError(TEXT("Author refuses existing result; preserve before/candidate"));return false;}
        auto* PA=NewObject<UPhysicsAsset>(CreatePackage(*Path),*FPackageName::GetLongPackageAssetName(Path),RF_Public|RF_Standalone|RF_Transactional);FAssetRegistryModule::AssetCreated(PA);
        FString Provenance;const bool Original=OriginalAnatomy(Mesh,PA,Sources,Provenance);
        const bool Giant=Mesh->GetName().Contains(TEXT("Yetuga"))||Mesh->GetName().Contains(TEXT("Apes"));
        if(!Original)FitAnatomy(Mesh,PA,SkinBounds(Mesh,UnitPose(Mesh)),Giant);
        TArray<TSharedPtr<FJsonValue>> Detail;if(!Secondary(Mesh,PA,Hair,Cloth,Detail)){AddError(Mesh->GetPathName());return false;}
        if(PA->SkeletalBodySetups.IsEmpty())
        {
            // Empty pose carriers still need parent-body collision for independent parts.
            FitAnatomy(Mesh,PA,SkinBounds(Mesh,UnitPose(Mesh)),Giant);
        }
        PA->PreviewSkeletalMesh=Mesh;if(!Save(PA,Saved))return false;
        Mesh->Modify();Mesh->SetPhysicsAsset(PA);
        if(!Detail.IsEmpty()){auto* ABP=Animation(Mesh,PA,false,Saved);if(!ABP)return false;Mesh->SetPostProcessAnimBlueprint(TSubclassOf<UAnimInstance>(ABP->GeneratedClass.Get()));}
        if(!Save(Mesh,Saved))return false;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());Row->SetStringField(TEXT("physics"),PA->GetPathName());Row->SetStringField(TEXT("anatomy_source"),Original?Provenance:TEXT("Calculated from imported LOD0 dominant skin bounds; original shape unconfirmed"));
        Row->SetNumberField(TEXT("bodies"),PA->SkeletalBodySetups.Num());Row->SetArrayField(TEXT("secondary"),Detail);Rows.Add(MakeShared<FJsonValueObject>(Row));
        AddInfo(FString::Printf(TEXT("MonsterPhysicsAuthor %s bodies=%d secondary=%d"),*Mesh->GetName(),PA->SkeletalBodySetups.Num(),Detail.Num()));
    }
    for(const auto& V:Plan->GetArrayField(TEXT("blueprints")))
    {
        auto* BP=LoadObject<UBlueprint>(nullptr,*V->AsString());if(!BP)continue;
        auto* CDO=Cast<ACharacter>(BP->GeneratedClass->GetDefaultObject());if(!CDO)return false;
        CDO->GetMesh()->SetCollisionProfileName(TEXT("CharacterMesh"));CDO->GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        if(BP->GetName().Contains(TEXT("HeavySwordsman")))
            for(auto* N:BP->SimpleConstructionScript->GetAllNodes())if(auto* Component=Cast<USkeletalMeshComponent>(N->ComponentTemplate);Component && Component->ComponentHasTag(TEXT("MonsterBodyPart")))
            {
                auto* Copy=Animation(Component->GetSkeletalMeshAsset(),nullptr,true,Saved);if(!Copy)return false;
                Component->SetAnimInstanceClass(Copy->GeneratedClass);Component->SetCollisionProfileName(TEXT("CharacterMesh"));Component->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            }
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);if(BP->Status==BS_Error || !Save(BP,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("meshes"),Rows);Report->SetArrayField(TEXT("saved"),Saved);return Write(TEXT("MonsterSecondaryPhysicsAuthor.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterHeavyCollision,"Khazan.MonsterSecondaryPhysics.HeavyCollision",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterHeavyCollision::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto Plan=ReadPlan();TArray<TSharedPtr<FJsonValue>> Saved;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))if(V->AsString().Contains(TEXT("/HeavySwordsman/Parts/")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();
        if(!Mesh->GetPostProcessAnimBlueprint())continue;
        auto* BP=Cast<UAnimBlueprint>(Mesh->GetPostProcessAnimBlueprint()->ClassGeneratedBy);if(!BP)return false;
        TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs);
        for(auto* Graph:Graphs)for(UEdGraphNode* N:Graph->Nodes)if(auto* R=Cast<UAnimGraphNode_RigidBody>(N))R->Node.bUseExternalClothCollision=true;
        for(int32 A=0;A<PA->SkeletalBodySetups.Num();++A)for(int32 B=A+1;B<PA->SkeletalBodySetups.Num();++B)PA->DisableCollision(A,B);
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);
        if(!Save(BP,Saved) || !Save(PA,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);return Write(TEXT("MonsterSecondaryPhysicsHeavyCollision.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterStability,"Khazan.MonsterSecondaryPhysics.Stability",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterStability::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto Plan=ReadPlan();auto* Cloth=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset"));if(!Cloth)return false;
    const float PlayerProjection=Cloth->ConstraintSetup.Last()->DefaultInstance.ProfileInstance.ProjectionAngularAlpha;
    TArray<TSharedPtr<FJsonValue>> Saved;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();if(!PA || PA->ConstraintSetup.IsEmpty())continue;
        // Assistant technical solver adaptation for large animated anchors. Keep
        // all player spring/damping/limits and current cloth projection strength.
        PA->SolverSettings.bUseLinearJointSolver=false;
        for(UPhysicsConstraintTemplate* Joint:PA->ConstraintSetup)
        {
            auto& C=Joint->DefaultInstance;C.ProfileInstance.bUseLinearJointSolver=false;
            C.ProfileInstance.bEnableProjection=true;C.ProfileInstance.ProjectionAngularAlpha=PlayerProjection;
            Joint->SetDefaultProfile(C);
        }
        if(!Save(PA,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetNumberField(TEXT("player_projection_angular_alpha"),PlayerProjection);
    return Write(TEXT("MonsterSecondaryPhysicsStability.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterHairScope,"Khazan.MonsterSecondaryPhysics.HairScope",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterHairScope::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto Plan=ReadPlan();TArray<TSharedPtr<FJsonValue>> Saved,Changed;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!Mesh)return false;
        if(!Mesh->GetName().Contains(TEXT("Yetuga")) && !Mesh->GetName().Contains(TEXT("Apes")))continue;
        auto* PA=Mesh->GetPhysicsAsset();if(!PA || PA->ConstraintSetup.IsEmpty())continue;
        for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && !Kind(B->BoneName,true))
        {B->PhysicsType=PhysType_Kinematic;Changed.Add(MakeShared<FJsonValueString>(B->BoneName.ToString()));}
        PA->ConstraintSetup.RemoveAll([&](const UPhysicsConstraintTemplate* J){return PA->SkeletalBodySetups[PA->FindBodyIndex(J->DefaultInstance.ConstraintBone1)]->PhysicsType!=PhysType_Simulated;});
        for(int32 A=0;A<PA->SkeletalBodySetups.Num();++A)for(int32 B=A+1;B<PA->SkeletalBodySetups.Num();++B)
        {
            const auto* BA=PA->SkeletalBodySetups[A].Get();const auto* BB=PA->SkeletalBodySetups[B].Get();
            const bool SA=BA->PhysicsType==PhysType_Simulated,SB=BB->PhysicsType==PhysType_Simulated;
            if(SA==SB || (!SA && BA->BoneName.ToString().StartsWith(TEXT("B_"))) || (!SB && BB->BoneName.ToString().StartsWith(TEXT("B_"))))PA->DisableCollision(A,B);
        }
        PA->UpdateBoundsBodiesArray();if(!Save(PA,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("animation_driven_unclassified_bones"),Changed);
    return Write(TEXT("MonsterSecondaryPhysicsHairScope.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSupportGeometry,"Khazan.MonsterSecondaryPhysics.SupportGeometry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterSupportGeometry::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto Plan=ReadPlan();TArray<TSharedPtr<FJsonValue>> Saved,Rows;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();if(!PA || PA->ConstraintSetup.IsEmpty())continue;
        const auto Bounds=SkinBounds(Mesh,UnitPose(Mesh));const auto& Ref=Mesh->GetRefSkeleton();TMap<FName,double> SupportInertia;
        for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && !B->AggGeom.SphylElems.IsEmpty())
        {
            const FBox* Box=Bounds.Find(Ref.FindBoneIndex(B->BoneName));if(!Box || !Box->IsValid)continue;
            auto& E=B->AggGeom.SphylElems[0];const double OldLength=E.Length+2.*E.Radius,OldMass=B->DefaultInstance.GetMassOverride();
            const FVector Size=Box->GetSize();int32 Axis=0;if(Size.Y>Size[Axis])Axis=1;if(Size.Z>Size[Axis])Axis=2;
            const double Length=FMath::Max(OldLength,Size[Axis]);FVector Direction=FVector::ZeroVector;Direction[Axis]=1.;
            E.Center=Box->GetCenter();E.Length=Length-2.*E.Radius;E.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Direction).Rotator();
            const double Mass=OldMass*Length/OldLength;B->DefaultInstance.SetMassOverride(Mass,true);B->DefaultInstance.InertiaTensorScale=FVector::OneVector;B->InvalidatePhysicsData();
            // Calculated uniform-box inertia of the actual dominant skin support.
            // The thin contact proxy must not imply the inertia of a tiny sphere
            // at a distant pivot. Radius/player density/feel coefficients remain.
            const FVector I=Mass/12.*FVector(Size.Y*Size.Y+Size.Z*Size.Z,Size.X*Size.X+Size.Z*Size.Z,Size.X*Size.X+Size.Y*Size.Y);
            SupportInertia.Add(B->BoneName,I.GetMax());
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());Row->SetStringField(TEXT("bone"),B->BoneName.ToString());Row->SetNumberField(TEXT("old_length_cm"),OldLength);Row->SetNumberField(TEXT("support_length_cm"),Length);Row->SetNumberField(TEXT("mass_per_length_kg_cm"),OldMass/OldLength);Row->SetNumberField(TEXT("mass_kg"),Mass);Row->SetNumberField(TEXT("skin_box_max_inertia_kg_cm2"),I.GetMax());Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        auto* Probe=NewObject<USkeletalMeshComponent>();Probe->SetSkeletalMesh(Mesh);TArray<FBodyInstance*> Bodies;Probe->InstantiatePhysicsAssetBodiesRefPose(*PA,Bodies);
        for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated)
        {
            const auto Setup=ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(B->BoneName)],FTransform::Identity);FVector D;
            for(int32 Axis=0;Axis<3;++Axis){FVector Basis=FVector::ZeroVector;Basis[Axis]=1.;D[Axis]=Setup.CoMTransform.GetRotation().RotateVector(FVector(Setup.Inertia)*Setup.CoMTransform.GetRotation().UnrotateVector(Basis))[Axis];}
            const double Target=FMath::Max(double(FVector(Setup.Inertia).GetMax()),SupportInertia.FindRef(B->BoneName));
            const FVector Q=FVector(.5*Target)/(FVector(.5*(D.X+D.Y+D.Z))-D);const double Det=FMath::Pow(Q.X*Q.Y*Q.Z,1./5.);
            B->DefaultInstance.InertiaTensorScale=FVector(FMath::Sqrt(Q.X/Det),FMath::Sqrt(Q.Y/Det),FMath::Sqrt(Q.Z/Det));
        }
        for(auto* B:Bodies){if(B->IsValidBodyInstance())B->TermBody(true);delete B;}PA->UpdateBoundsBodiesArray();if(!Save(PA,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("calculated_support_geometry"),Rows);return Write(TEXT("MonsterSecondaryPhysicsSupportGeometry.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterCoordinateSpace,"Khazan.MonsterSecondaryPhysics.CoordinateSpace",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterCoordinateSpace::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto Plan=ReadPlan();TArray<TSharedPtr<FJsonValue>> Saved;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!Mesh || !Mesh->GetPostProcessAnimBlueprint())continue;
        if(!TestEqual(TEXT("Enemy reference wrapper is unit scale"),Mesh->GetRefSkeleton().GetRefBonePose()[0].GetScale3D().X,1.))return false;
        auto* BP=Cast<UAnimBlueprint>(Mesh->GetPostProcessAnimBlueprint()->ClassGeneratedBy);if(!BP)return false;TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs);
        for(auto* G:Graphs)for(UEdGraphNode* N:G->Nodes)if(auto* R=Cast<UAnimGraphNode_RigidBody>(N))R->Node.SimulationSpace=ESimulationSpace::ComponentSpace;
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);if(!Save(BP,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);return Write(TEXT("MonsterSecondaryPhysicsCoordinateSpace.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterHairProjection,"Khazan.MonsterSecondaryPhysics.HairProjection",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterHairProjection::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto Plan=ReadPlan();auto* Cloth=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset"));if(!Cloth)return false;
    const float Projection=Cloth->ConstraintSetup.Last()->DefaultInstance.ProfileInstance.ProjectionAngularAlpha;TArray<TSharedPtr<FJsonValue>> Saved;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();if(!PA || PA->ConstraintSetup.IsEmpty())continue;
        for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup){J->DefaultInstance.ProfileInstance.ProjectionAngularAlpha=Projection;J->SetDefaultProfile(J->DefaultInstance);}
        if(!Save(PA,Saved))return false;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetNumberField(TEXT("player_cloth_angular_projection"),Projection);return Write(TEXT("MonsterSecondaryPhysicsHairProjection.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterHairAnchors,"Khazan.MonsterSecondaryPhysics.HairAnchors",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterHairAnchors::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;
    auto* PA=Mesh->GetPhysicsAsset();const auto& Ref=Mesh->GetRefSkeleton();const auto Pose=UnitPose(Mesh);TArray<TSharedPtr<FJsonValue>> Rows,Saved;
    auto Endpoints=[](const FKSphylElem& E,const FTransform& T,FVector& A,FVector& B)
    {const FVector Axis=E.Rotation.RotateVector(FVector::UpVector)*(.5*E.Length);A=T.TransformPosition(E.Center-Axis);B=T.TransformPosition(E.Center+Axis);};
    for(int32 I=0;I<PA->SkeletalBodySetups.Num();++I)
    {
        const USkeletalBodySetup* B=PA->SkeletalBodySetups[I];const int32 Bone=Ref.FindBoneIndex(B->BoneName);
        if(B->PhysicsType!=PhysType_Simulated || Kind(B->BoneName,true)!=1 || B->AggGeom.SphylElems.IsEmpty())continue;
        const auto* Joint=PA->ConstraintSetup.FindByPredicate([&](const auto& C){return C->DefaultInstance.ConstraintBone1==B->BoneName;});if(!Joint)continue;
        if(PA->SkeletalBodySetups[PA->FindBodyIndex((*Joint)->DefaultInstance.ConstraintBone2)]->PhysicsType==PhysType_Simulated)continue;
        const auto& Shape=B->AggGeom.SphylElems[0];FVector A0,A1;Endpoints(Shape,Pose[Bone],A0,A1);
        for(int32 K=0;K<PA->SkeletalBodySetups.Num();++K)
        {
            const USkeletalBodySetup* Anchor=PA->SkeletalBodySetups[K];if(Anchor->PhysicsType!=PhysType_Kinematic)continue;
            const int32 Parent=Ref.FindBoneIndex(Anchor->BoneName);int32 Ancestor=Ref.GetParentIndex(Bone);while(Ancestor>0 && Ancestor!=Parent)Ancestor=Ref.GetParentIndex(Ancestor);if(Ancestor!=Parent)continue;
            for(const auto& BodyShape:Anchor->AggGeom.SphylElems)
            {
                FVector B0,B1,P0,P1;Endpoints(BodyShape,Pose[Parent],B0,B1);FMath::SegmentDistToSegmentSafe(A0,A1,B0,B1,P0,P1);
                const double Gap=FVector::Distance(P0,P1)-Shape.Radius-BodyShape.Radius;if(Gap>=0.)continue;
                PA->DisableCollision(I,K);auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("hair"),B->BoneName.ToString());Row->SetStringField(TEXT("attachment_anatomy"),Anchor->BoneName.ToString());Row->SetNumberField(TEXT("ref_overlap_cm"),-Gap);Rows.Add(MakeShared<FJsonValueObject>(Row));
            }
        }
    }
    if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("overlapping_attached_root_pairs"),Rows);return Write(TEXT("MonsterSecondaryPhysicsHairAnchors.json"),Report);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterProjectionBound,"Khazan.MonsterSecondaryPhysics.ProjectionBound",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterProjectionBound::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();TArray<TSharedPtr<FJsonValue>> Rows,Saved;
    for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup)
    {
        auto& C=J->DefaultInstance;
        if(Kind(C.ConstraintBone1,true)!=1)continue;
        // Calculated emergency solver correction threshold from the reused player
        // angular limits. Not original-game metadata; no new magic tuning literal.
        const double Bound=FVector(C.GetAngularSwing1Limit(),C.GetAngularSwing2Limit(),C.GetAngularTwistLimit()).Size();
        C.ProfileInstance.ProjectionAngularTolerance=Bound;
        // Assistant technical tuning: full angular correction for Yetuga's attached
        // single-bone fur only; player limits/spring/damping and cloth stay unchanged.
        C.ProfileInstance.ProjectionAngularAlpha=1.f;J->SetDefaultProfile(C);
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("bone"),C.ConstraintBone1.ToString());Row->SetNumberField(TEXT("angular_projection_tolerance_deg"),Bound);Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("calculated_projection_thresholds"),Rows);return Write(TEXT("MonsterSecondaryPhysicsProjectionBound.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurSupport,"Khazan.MonsterSecondaryPhysics.FurSupport",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurSupport::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));
    auto* Hair=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/_Art/Player/Character/Meshs/Hair/Player_Original_Hair_RigidBody_PhysicsAsset"));
    auto* Cloth=LoadObject<UPhysicsAsset>(nullptr,TEXT("/Game/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset"));if(!Mesh || !Hair || !Cloth)return false;
    auto* PA=Mesh->GetPhysicsAsset();const auto Bounds=SkinBounds(Mesh,UnitPose(Mesh));const auto& Ref=Mesh->GetRefSkeleton();
    TArray<TSharedPtr<FJsonValue>> Rows,Saved;TMap<FName,double> SupportInertia;
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && Kind(B->BoneName,true)==1)
    {
        const FBox* Box=Bounds.Find(Ref.FindBoneIndex(B->BoneName));if(!Box || !Box->IsValid || B->AggGeom.SphylElems.IsEmpty())continue;
        auto& E=B->AggGeom.SphylElems[0];const double OldLength=E.Length+2.*E.Radius;
        const double Density=B->DefaultInstance.GetMassOverride()/OldLength;const FVector Size=Box->GetSize();
        int32 Axis=0;if(Size.Y>Size[Axis])Axis=1;if(Size.Z>Size[Axis])Axis=2;
        // These single-bone fur tufts have no next hair joint. Head-to-tuft
        // distance is an attachment offset, not a physical strand length.
        const double Length=FMath::Max(double(Size[Axis]),2.*E.Radius);FVector Direction=FVector::ZeroVector;Direction[Axis]=1.;
        E.Center=Box->GetCenter();E.Length=Length-2.*E.Radius;E.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Direction).Rotator();
        const double Mass=Density*Length;B->DefaultInstance.SetMassOverride(Mass,true);B->DefaultInstance.InertiaTensorScale=FVector::OneVector;B->InvalidatePhysicsData();
        const FVector I=Mass/12.*FVector(Size.Y*Size.Y+Size.Z*Size.Z,Size.X*Size.X+Size.Z*Size.Z,Size.X*Size.X+Size.Y*Size.Y);SupportInertia.Add(B->BoneName,I.GetMax());
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("bone"),B->BoneName.ToString());Row->SetNumberField(TEXT("old_length_cm"),OldLength);Row->SetNumberField(TEXT("support_length_cm"),Length);Row->SetNumberField(TEXT("mass_kg"),Mass);Row->SetStringField(TEXT("support_size_cm"),Size.ToString());Row->SetStringField(TEXT("support_center_cm"),E.Center.ToString());Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup)if(Kind(J->DefaultInstance.ConstraintBone1,true)==1)
    {
        auto& C=J->DefaultInstance;auto* Reference=ReferenceJoint(Hair,1,1);if(!Reference)return false;
        C.ProfileInstance=Reference->DefaultInstance.ProfileInstance;
        C.ProfileInstance.ProjectionAngularAlpha=Cloth->ConstraintSetup.Last()->DefaultInstance.ProfileInstance.ProjectionAngularAlpha;
        J->SetDefaultProfile(C);
    }
    auto* Probe=NewObject<USkeletalMeshComponent>();Probe->SetSkeletalMesh(Mesh);TArray<FBodyInstance*> Bodies;Probe->InstantiatePhysicsAssetBodiesRefPose(*PA,Bodies);
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(const double* Support=SupportInertia.Find(B->BoneName))
    {
        const auto Setup=ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(B->BoneName)],FTransform::Identity);FVector D;
        for(int32 Axis=0;Axis<3;++Axis){FVector Basis=FVector::ZeroVector;Basis[Axis]=1.;D[Axis]=Setup.CoMTransform.GetRotation().RotateVector(FVector(Setup.Inertia)*Setup.CoMTransform.GetRotation().UnrotateVector(Basis))[Axis];}
        const double Target=FMath::Max(double(FVector(Setup.Inertia).GetMax()),*Support);const FVector Q=FVector(.5*Target)/(FVector(.5*(D.X+D.Y+D.Z))-D);const double Det=FMath::Pow(Q.X*Q.Y*Q.Z,1./5.);
        B->DefaultInstance.InertiaTensorScale=FVector(FMath::Sqrt(Q.X/Det),FMath::Sqrt(Q.Y/Det),FMath::Sqrt(Q.Z/Det));
    }
    for(auto* B:Bodies){if(B->IsValidBodyInstance())B->TermBody(true);delete B;}
    PA->UpdateBoundsBodiesArray();if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("actual_fur_support"),Rows);return Write(TEXT("MonsterSecondaryPhysicsFurSupport.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSavedPhysics,"Khazan.MonsterSecondaryPhysics.Saved",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterSavedPhysics::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;auto Plan=ReadPlan();if(!Plan)return false;TArray<TSharedPtr<FJsonValue>> Rows;
    int32 Total=0,PostProcesses=0;
    for(const auto& V:Plan->GetArrayField(TEXT("meshes")))
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*V->AsString());if(!TestNotNull(TEXT("Saved mesh"),Mesh))return false;
        auto* PA=Mesh->GetPhysicsAsset();if(!TestNotNull(TEXT("Saved PhysicsAsset"),PA))return false;
        const auto& Ref=Mesh->GetRefSkeleton();TArray<TSharedPtr<FJsonValue>> Bodies,Joints;int32 Count=0;
        for(USkeletalBodySetup* B:PA->SkeletalBodySetups)
        {
            const int32 Bone=Ref.FindBoneIndex(B->BoneName);TestTrue(TEXT("Physics body bone exists"),Bone!=INDEX_NONE);
            auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("bone"),B->BoneName.ToString());R->SetBoolField(TEXT("simulated"),B->PhysicsType==PhysType_Simulated);
            R->SetStringField(TEXT("ref_local_scale"),Ref.GetRefBonePose()[Bone].GetScale3D().ToString());
            R->SetNumberField(TEXT("linear_damping"),B->DefaultInstance.LinearDamping);R->SetNumberField(TEXT("angular_damping"),B->DefaultInstance.AngularDamping);
            R->SetNumberField(TEXT("mass_kg"),B->DefaultInstance.GetMassOverride());R->SetStringField(TEXT("inertia_scale"),B->DefaultInstance.InertiaTensorScale.ToString());
            TestTrue(TEXT("Body inertia is finite"),!B->DefaultInstance.InertiaTensorScale.ContainsNaN());
            if(B->PhysicsType==PhysType_Simulated){++Count;TestTrue(TEXT("Only explicit hair and cloth simulated"),Kind(B->BoneName,true)!=0);}
            if(!B->AggGeom.SphylElems.IsEmpty()){const auto& E=B->AggGeom.SphylElems[0];R->SetNumberField(TEXT("radius_cm"),E.Radius);R->SetNumberField(TEXT("capsule_length_cm"),E.Length+2.*E.Radius);R->SetStringField(TEXT("center_cm"),E.Center.ToString());}
            Bodies.Add(MakeShared<FJsonValueObject>(R));
        }
        for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup)
        {
            const auto& C=J->DefaultInstance;auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("bone"),C.ConstraintBone1.ToString());R->SetStringField(TEXT("parent"),C.ConstraintBone2.ToString());
            R->SetNumberField(TEXT("swing1_deg"),C.GetAngularSwing1Limit());R->SetNumberField(TEXT("swing2_deg"),C.GetAngularSwing2Limit());R->SetNumberField(TEXT("twist_deg"),C.GetAngularTwistLimit());
            R->SetNumberField(TEXT("spring"),C.ProfileInstance.AngularDrive.SlerpDrive.Stiffness);R->SetNumberField(TEXT("damping"),C.ProfileInstance.AngularDrive.SlerpDrive.Damping);
            R->SetNumberField(TEXT("angular_projection"),C.ProfileInstance.ProjectionAngularAlpha);Joints.Add(MakeShared<FJsonValueObject>(R));
            TestTrue(TEXT("Constraint parent exists"),PA->FindBodyIndex(C.ConstraintBone2)!=INDEX_NONE);
        }
        UClass* Post=Mesh->GetPostProcessAnimBlueprint().Get();TestEqual(TEXT("Secondary meshes evaluate a post-process"),Post!=nullptr,Count>0);
        if(Post){++PostProcesses;auto* BP=Cast<UAnimBlueprint>(Post->ClassGeneratedBy);TestTrue(TEXT("Saved post-process compiled"),BP && BP->Status!=BS_Error);}
        Total+=Count;auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());Row->SetStringField(TEXT("physics"),PA->GetPathName());Row->SetNumberField(TEXT("simulated"),Count);
        Row->SetBoolField(TEXT("linear_solver"),PA->SolverSettings.bUseLinearJointSolver);Row->SetNumberField(TEXT("position_iterations"),PA->SolverSettings.PositionIterations);Row->SetNumberField(TEXT("fixed_step_sec"),PA->SolverSettings.FixedTimeStep);
        Row->SetArrayField(TEXT("bodies"),Bodies);Row->SetArrayField(TEXT("joints"),Joints);Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    TestEqual(TEXT("All prepared meshes saved"),Rows.Num(),35);TestEqual(TEXT("All secondary post-processes saved"),PostProcesses,20);
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("meshes"),Rows);Report->SetNumberField(TEXT("total_simulated"),Total);return Write(TEXT("MonsterSecondaryPhysicsSaved.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurSolver,"Khazan.MonsterSecondaryPhysics.FurSolver",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurSolver::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;
    auto* PA=Mesh->GetPhysicsAsset();PA->SolverSettings.bUseLinearJointSolver=false;
    for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup){J->DefaultInstance.ProfileInstance.bUseLinearJointSolver=false;J->SetDefaultProfile(J->DefaultInstance);}
    TArray<TSharedPtr<FJsonValue>> Saved;if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);
    Report->SetStringField(TEXT("technical_adaptation"),TEXT("Yetuga only: exact nonlinear angular solve for single-bone tufts; reused player feel values and other families unchanged"));return Write(TEXT("MonsterSecondaryPhysicsFurSolver.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurContacts,"Khazan.MonsterSecondaryPhysics.FurContacts",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurContacts::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;
    auto* PA=Mesh->GetPhysicsAsset();PA->SolverSettings.bUseLinearJointSolver=true;
    for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup){J->DefaultInstance.ProfileInstance.bUseLinearJointSolver=true;J->SetDefaultProfile(J->DefaultInstance);}
    const auto& Ref=Mesh->GetRefSkeleton();const auto Pose=UnitPose(Mesh);TArray<TSharedPtr<FJsonValue>> Rows,Saved;
    auto Endpoints=[](const FKSphylElem& E,const FTransform& T,FVector& A,FVector& B){const FVector Axis=E.Rotation.RotateVector(FVector::UpVector)*(.5*E.Length);A=T.TransformPosition(E.Center-Axis);B=T.TransformPosition(E.Center+Axis);};
    for(int32 I=0;I<PA->SkeletalBodySetups.Num();++I)
    {
        const auto* Hair=PA->SkeletalBodySetups[I].Get();if(Hair->PhysicsType!=PhysType_Simulated || Kind(Hair->BoneName,true)!=1 || Hair->AggGeom.SphylElems.IsEmpty())continue;
        const int32 Bone=Ref.FindBoneIndex(Hair->BoneName);FVector A0,A1;Endpoints(Hair->AggGeom.SphylElems[0],Pose[Bone],A0,A1);
        for(int32 K=0;K<PA->SkeletalBodySetups.Num();++K)
        {
            const auto* Body=PA->SkeletalBodySetups[K].Get();if(Body->PhysicsType!=PhysType_Kinematic)continue;
            for(const auto& Shape:Body->AggGeom.SphylElems)
            {
                FVector B0,B1,P0,P1;Endpoints(Shape,Pose[Ref.FindBoneIndex(Body->BoneName)],B0,B1);FMath::SegmentDistToSegmentSafe(A0,A1,B0,B1,P0,P1);
                const double Gap=FVector::Distance(P0,P1)-Shape.Radius-Hair->AggGeom.SphylElems[0].Radius;if(Gap>=0.)continue;
                // A rigidly attached tuft already intersects this proxy in its
                // authored rest skin. Depenetrating it is incompatible with the
                // locked pivot/player angular limits. Other anatomy contacts stay.
                PA->DisableCollision(I,K);auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("hair"),Hair->BoneName.ToString());R->SetStringField(TEXT("body"),Body->BoneName.ToString());R->SetNumberField(TEXT("rest_overlap_cm"),-Gap);Rows.Add(MakeShared<FJsonValueObject>(R));
            }
        }
    }
    if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("attached_rest_overlap_pairs"),Rows);return Write(TEXT("MonsterSecondaryPhysicsFurContacts.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurTips,"Khazan.MonsterSecondaryPhysics.FurTips",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurTips::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;
    auto* PA=Mesh->GetPhysicsAsset();const auto Pose=UnitPose(Mesh);const auto Bounds=SkinBounds(Mesh,Pose);const auto& Ref=Mesh->GetRefSkeleton();TMap<int32,FVector> Tips;
    for(const auto& S:Mesh->GetImportedModel()->LODModels[0].Sections)for(const auto& V:S.SoftVertices)
    {
        int32 Best=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J]>V.InfluenceWeights[Best])Best=J;
        if(!V.InfluenceWeights[Best])continue;const int32 Bone=S.BoneMap[V.InfluenceBones[Best]];if(Kind(Ref.GetBoneName(Bone),true)!=1)continue;
        const FVector P=Pose[Bone].InverseTransformPosition(FVector(V.Position));if(!Tips.Contains(Bone) || P.SizeSquared()>Tips[Bone].SizeSquared())Tips.Add(Bone,P);
    }
    TArray<TSharedPtr<FJsonValue>> Rows,Saved;TMap<FName,double> TargetMoments;
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && Kind(B->BoneName,true)==1)
    {
        const int32 Bone=Ref.FindBoneIndex(B->BoneName);const auto* Tip=Tips.Find(Bone);const auto* Box=Bounds.Find(Bone);if(!Tip || !Box || B->AggGeom.SphylElems.IsEmpty())continue;
        const float Radius=B->AggGeom.SphylElems[0].Radius;const double Mass=B->DefaultInstance.GetMassOverride();const FVector Size=Box->GetSize();
        // A single rigid tuft needs distal contact, not a rod spanning its scalp.
        // Use an actual dominant-weight skin tip and the existing player radius.
        B->AggGeom.EmptyElements();FKSphereElem E;E.Center=*Tip;E.Radius=Radius;B->AggGeom.SphereElems.Add(E);B->DefaultInstance.InertiaTensorScale=FVector::OneVector;B->InvalidatePhysicsData();
        const FVector I=Mass/12.*FVector(Size.Y*Size.Y+Size.Z*Size.Z,Size.X*Size.X+Size.Z*Size.Z,Size.X*Size.X+Size.Y*Size.Y);TargetMoments.Add(B->BoneName,I.GetMax());
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("bone"),B->BoneName.ToString());R->SetStringField(TEXT("actual_skin_tip_cm"),Tip->ToString());R->SetNumberField(TEXT("radius_cm"),Radius);R->SetNumberField(TEXT("support_inertia_kg_cm2"),I.GetMax());Rows.Add(MakeShared<FJsonValueObject>(R));
    }
    auto* Probe=NewObject<USkeletalMeshComponent>();Probe->SetSkeletalMesh(Mesh);TArray<FBodyInstance*> Bodies;Probe->InstantiatePhysicsAssetBodiesRefPose(*PA,Bodies);
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(const double* Target=TargetMoments.Find(B->BoneName))
    {
        const auto Setup=ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(B->BoneName)],FTransform::Identity);
        B->DefaultInstance.InertiaTensorScale=FVector(FMath::Pow(*Target/FVector(Setup.Inertia).GetMin(),1./5.));
    }
    for(auto* B:Bodies){if(B->IsValidBodyInstance())B->TermBody(true);delete B;}PA->UpdateBoundsBodiesArray();if(!Save(PA,Saved))return false;
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("distal_fur_contacts"),Rows);return Write(TEXT("MonsterSecondaryPhysicsFurTips.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurHardBounds,"Khazan.MonsterSecondaryPhysics.FurHardBounds",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurHardBounds::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();TArray<TSharedPtr<FJsonValue>> Rows,Saved;
    PA->SolverSettings.bUseLinearJointSolver=false;
    for(UPhysicsConstraintTemplate* J:PA->ConstraintSetup)
    {
        auto& C=J->DefaultInstance;if(Kind(C.ConstraintBone1,true)!=1)continue;
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("bone"),C.ConstraintBone1.ToString());R->SetBoolField(TEXT("before_soft_swing"),C.ProfileInstance.ConeLimit.bSoftConstraint);R->SetBoolField(TEXT("before_soft_twist"),C.ProfileInstance.TwistLimit.bSoftConstraint);R->SetBoolField(TEXT("before_projection"),C.ProfileInstance.bEnableProjection);
        C.ProfileInstance.ConeLimit.bSoftConstraint=false;C.ProfileInstance.TwistLimit.bSoftConstraint=false;C.ProfileInstance.bUseLinearJointSolver=false;
        C.ProfileInstance.bEnableProjection=true;
        C.ProfileInstance.ProjectionAngularTolerance=FVector(C.GetAngularSwing1Limit(),C.GetAngularSwing2Limit(),C.GetAngularTwistLimit()).Size();
        // Exact hard bounds with a metadata-derived emergency angular threshold.
        // Source player spring/damping/limits remain; this is technical adaptation.
        J->SetDefaultProfile(C);Rows.Add(MakeShared<FJsonValueObject>(R));
    }
    if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("previous_policy"),Rows);return Write(TEXT("MonsterSecondaryPhysicsFurHardBounds.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurWorldSpace,"Khazan.MonsterSecondaryPhysics.FurWorldSpace",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurWorldSpace::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;
    auto* BP=Cast<UAnimBlueprint>(Mesh->GetPostProcessAnimBlueprint()->ClassGeneratedBy);if(!BP)return false;TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs);TArray<TSharedPtr<FJsonValue>> Saved;
    for(auto* G:Graphs)for(UEdGraphNode* N:G->Nodes)if(auto* R=Cast<UAnimGraphNode_RigidBody>(N))R->Node.SimulationSpace=ESimulationSpace::WorldSpace;
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);if(!Save(BP,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);return Write(TEXT("MonsterSecondaryPhysicsFurWorldSpace.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurJointInertia,"Khazan.MonsterSecondaryPhysics.FurJointInertia",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurJointInertia::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();
    auto* Probe=NewObject<USkeletalMeshComponent>();Probe->SetSkeletalMesh(Mesh);TArray<FBodyInstance*> Bodies;Probe->InstantiatePhysicsAssetBodiesRefPose(*PA,Bodies);TArray<TSharedPtr<FJsonValue>> Rows,Saved;
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && Kind(B->BoneName,true)==1)
    {
        const auto Setup=ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(B->BoneName)],FTransform::Identity);
        const double Before=FVector(Setup.Inertia).GetMin();const double ParallelAxis=Setup.Mass*Setup.CoMTransform.GetLocation().SizeSquared();
        // Calculated virtual bundle inertia about its locked attachment pivot.
        // A distal point proxy must not rotate instead of translating when the
        // animated head moves its attachment; preserve player feel and mass.
        const double Target=Before+ParallelAxis;B->DefaultInstance.InertiaTensorScale*=FMath::Pow(Target/Before,1./5.);
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("bone"),B->BoneName.ToString());R->SetNumberField(TEXT("before_inertia_kg_cm2"),Before);R->SetNumberField(TEXT("parallel_axis_floor_kg_cm2"),ParallelAxis);R->SetNumberField(TEXT("target_inertia_kg_cm2"),Target);Rows.Add(MakeShared<FJsonValueObject>(R));
    }
    for(auto* B:Bodies){if(B->IsValidBodyInstance())B->TermBody(true);delete B;}if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetArrayField(TEXT("calculated_pivot_inertia"),Rows);return Write(TEXT("MonsterSecondaryPhysicsFurJointInertia.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFurBundleStability,"Khazan.MonsterSecondaryPhysics.FurBundleStability",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterFurBundleStability::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();TArray<TSharedPtr<FJsonValue>> Saved;
    // Assistant temporary stability multiplier, not original-game metadata:
    // observed 55.36-degree attack overshoot after geometry-derived pivot inertia.
    // Reuse player spring/damping; double virtual bundle inertia, not body mass.
    constexpr double BundleInertiaMultiplier=2.;
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && Kind(B->BoneName,true)==1)B->DefaultInstance.InertiaTensorScale*=FMath::Pow(BundleInertiaMultiplier,1./5.);
    if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetNumberField(TEXT("assistant_temporary_virtual_inertia_multiplier"),BundleInertiaMultiplier);return Write(TEXT("MonsterSecondaryPhysicsFurBundleStability.json"),Report);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterGiantClothStability,"Khazan.MonsterSecondaryPhysics.GiantClothStability",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZMonsterGiantClothStability::RunTest(const FString&)
{
    using namespace KZMonsterPhysics;if(!FPaths::ProjectDir().Contains(TEXT("Khazan_PlayerPartsWork_20261007")))return false;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga"));if(!Mesh)return false;auto* PA=Mesh->GetPhysicsAsset();TArray<TSharedPtr<FJsonValue>> Saved;
    // Same assistant temporary bundle-inertia stabilization for Yetuga's four
    // large cloth bodies: RHI attack overshoot 49.67 degrees, player feel retained.
    constexpr double ClothInertiaMultiplier=2.;
    for(USkeletalBodySetup* B:PA->SkeletalBodySetups)if(B->PhysicsType==PhysType_Simulated && Kind(B->BoneName,true)==2)B->DefaultInstance.InertiaTensorScale*=FMath::Pow(ClothInertiaMultiplier,1./5.);
    if(!Save(PA,Saved))return false;auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("saved"),Saved);Report->SetNumberField(TEXT("assistant_temporary_cloth_inertia_multiplier"),ClothInertiaMultiplier);return Write(TEXT("MonsterSecondaryPhysicsGiantClothStability.json"),Report);
}
#endif
