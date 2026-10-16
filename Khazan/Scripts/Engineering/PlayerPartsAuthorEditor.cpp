// Editor-only authoring helper; compiled only in the isolated PlayerParts project.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "Components/SkeletalMeshComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "UObject/UnrealType.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "Animation/AnimInstance.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_CopyPoseFromMesh.h"
#include "AnimGraphNode_RigidBody.h"
#include "AnimGraphNode_LocalToComponentSpace.h"
#include "AnimGraphNode_ComponentToLocalSpace.h"
#include "Factories/AnimBlueprintFactory.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "GameFramework/Character.h"
#include "EdGraphUtilities.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsAdapters.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsActorHandle.h"
#include "Misc/ConfigCacheIni.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "JsonObjectConverter.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/SecureHash.h"

namespace KZPlayerPartsAuthor
{
bool IsWork() { return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_PlayerPartsWork_20261007")); }
const FString Base = TEXT("/Game/_Art/Player/Character/");
FString MeshPath(const FString& Part)
{
	return Part == TEXT("Body") ? Base + TEXT("Meshs/SKM_Player") : Base + TEXT("Meshs/") + Part + TEXT("/Player_Original_") + Part;
}
bool Save(UObject* Asset)
{
	if (!IsWork() || !Asset->GetPathName().StartsWith(Base)) return false;
	UPackage* Package = Asset->GetOutermost(); Package->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	return UPackage::SavePackage(Package, Asset, *FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}
template <typename T> T* Node(UEdGraph* Graph, int32 X)
{
	T* Result = NewObject<T>(Graph); Graph->AddNode(Result); Result->CreateNewGuid(); Result->PostPlacedNewNode();
	Result->NodePosX = X; Result->AllocateDefaultPins(); return Result;
}
bool SecondaryName(FName Bone)
{
	const FString Name = Bone.ToString();
	return Name.StartsWith(TEXT("B_Cape_")) || Name.StartsWith(TEXT("B_Cloth_")) || Name.StartsWith(TEXT("B_Leather_")) || Name.StartsWith(TEXT("B_Iron_")) || (Name.StartsWith(TEXT("Hair_")) && !Name.StartsWith(TEXT("Hair_BoneRoot")));
}
bool HasBodyAncestor(UPhysicsAsset* PA, const FReferenceSkeleton& Ref, FName Bone)
{
	int32 Index = Ref.FindBoneIndex(Bone);
	while (Index > 0)
	{
		Index = Ref.GetParentIndex(Index);
		if (Index >= 0 && PA->FindBodyIndex(Ref.GetBoneName(Index)) != INDEX_NONE) return true;
	}
	return false;
}
UPhysicsAsset* WorldSimulationAsset(USkeletalMesh* Mesh, UPhysicsAsset* Source, const FString& Part)
{
	// UE 5.8 ref-pose joint creation applies imported bone scale (100) before
	// RBAN starts at component .01 * root 100 = unit world bone scale.
	// ImmediatePhysicsAdapters reconstructs geometry at the unit actor scale:
	// preserve shapes; convert ONLY joint-frame positions by 1 / imported scale.
	const FVector ImportedScale = Mesh->GetRefSkeleton().GetRefBonePose()[0].GetScale3D();
	check(ImportedScale.Equals(FVector(ImportedScale.X)) && ImportedScale.X > 0.);
	const float UnitConversion = 1.f / ImportedScale.X;
	const FString Path = Base + TEXT("Meshs/") + Part + TEXT("/Player_Original_") + Part + TEXT("_RigidBody_PhysicsAsset");
	// Rebuild from Source on each author pass, never scale an existing result twice.
	UPhysicsAsset* Result = CastChecked<UPhysicsAsset>(StaticDuplicateObject(Source, CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path)));
	FAssetRegistryModule::AssetCreated(Result);
	for (UPhysicsConstraintTemplate* Constraint : Result->ConstraintSetup)
	{
		Constraint->DefaultInstance.Pos1 *= UnitConversion; Constraint->DefaultInstance.Pos2 *= UnitConversion;
		// These Original constraints have locked linear axes; angular limits, damping
		// and collision-pair policy remain exactly as the component's source asset.
	}
	Save(Result); return Result;
}
UAnimBlueprint* PartAnimation(USkeletalMesh* Mesh, UPhysicsAsset* PA, const FString& Part, bool bSimulate)
{
	const FString Path = Base + TEXT("Bluprints/Parts/ABP_Player_Original_") + Part;
	UAnimBlueprint* BP = LoadObject<UAnimBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn);
	if (!BP)
	{
		UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
		Factory->ParentClass = UAnimInstance::StaticClass(); Factory->TargetSkeleton = Mesh->GetSkeleton(); Factory->PreviewSkeletalMesh = Mesh;
		BP = CastChecked<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
		FAssetRegistryModule::AssetCreated(BP);
	}
	TArray<UEdGraph*> Graphs; BP->GetAllGraphs(Graphs);
	UEdGraph* Graph = *Graphs.FindByPredicate([](UEdGraph* G) { return G->GetFName() == TEXT("AnimGraph"); });
	UAnimGraphNode_Root* Root = nullptr;
	for (UEdGraphNode* N : TArray<TObjectPtr<UEdGraphNode>>(Graph->Nodes))
		if (auto* R = Cast<UAnimGraphNode_Root>(N)) { Root = R; R->BreakAllNodeLinks(); } else Graph->RemoveNode(N);
	auto* Copy = Node<UAnimGraphNode_CopyPoseFromMesh>(Graph, -1100); Copy->Node.bUseAttachedParent = true;
	const UEdGraphSchema* Schema = Graph->GetSchema();
	UEdGraphPin* Last = Copy->FindPinChecked(TEXT("Pose"));
	if (bSimulate)
	{
		auto* ToComponent = Node<UAnimGraphNode_LocalToComponentSpace>(Graph, -900);
		Schema->TryCreateConnection(Last, ToComponent->FindPinChecked(TEXT("LocalPose"))); Last = ToComponent->FindPinChecked(TEXT("ComponentPose"));
		auto* Physics = Node<UAnimGraphNode_RigidBody>(Graph, -500);
		Physics->Node.OverridePhysicsAsset = WorldSimulationAsset(Mesh, PA, Part); Physics->Node.SimulationSpace = ESimulationSpace::WorldSpace;
		Schema->TryCreateConnection(Last, Physics->FindPinChecked(TEXT("ComponentPose"))); Last = Physics->FindPinChecked(TEXT("Pose"));
		auto* ToLocal = Node<UAnimGraphNode_ComponentToLocalSpace>(Graph, -100);
		Schema->TryCreateConnection(Last, ToLocal->FindPinChecked(TEXT("ComponentPose"))); Last = ToLocal->FindPinChecked(TEXT("Pose"));
	}
	Schema->TryCreateConnection(Last, Root->FindPinChecked(TEXT("Result")));
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
	Save(BP); return BP;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerPartsAudit, "Khazan.PlayerParts.Audit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerPartsAudit::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	for (const FString Part : {TEXT("Body"), TEXT("Torso"), TEXT("Shoes"), TEXT("Leg"), TEXT("Hair"), TEXT("Arm")})
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(Part));
		if (!TestNotNull(*Part, Mesh)) continue;
		UPhysicsAsset* PA = Mesh->GetPhysicsAsset();
		const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
		AddInfo(FString::Printf(TEXT("Mesh part=%s path=%s skeleton=%s physics=%s bones=%d postprocess=%s"), *Part, *Mesh->GetPathName(), *GetPathNameSafe(Mesh->GetSkeleton()), *GetPathNameSafe(PA), Ref.GetNum(), *GetPathNameSafe(Mesh->GetPostProcessAnimBlueprint())));
		TArray<FTransform> CS; CS.SetNum(Ref.GetNum());
		for (int32 Bone = 0; Bone < Ref.GetNum(); ++Bone)
		{
			const int32 Parent = Ref.GetParentIndex(Bone);
			CS[Bone] = Parent >= 0 ? Ref.GetRefBonePose()[Bone] * CS[Parent] : Ref.GetRefBonePose()[Bone];
			AddInfo(FString::Printf(TEXT("Bone part=%s index=%d name=%s parent=%d local=%s component=%s"), *Part, Bone, *Ref.GetBoneName(Bone).ToString(), Parent, *Ref.GetRefBonePose()[Bone].ToString(), *CS[Bone].ToString()));
		}
		if (!PA) continue;
		for (const USkeletalBodySetup* Body : PA->SkeletalBodySetups)
		{
			AddInfo(FString::Printf(TEXT("Body part=%s bone=%s type=%d mass=%.5f linearDamping=%.5f angularDamping=%.5f spheres=%d capsules=%d boxes=%d convex=%d"), *Part, *Body->BoneName.ToString(), int32(Body->PhysicsType), Body->DefaultInstance.GetMassOverride(), Body->DefaultInstance.LinearDamping, Body->DefaultInstance.AngularDamping, Body->AggGeom.SphereElems.Num(), Body->AggGeom.SphylElems.Num(), Body->AggGeom.BoxElems.Num(), Body->AggGeom.ConvexElems.Num()));
			for (const FKSphylElem& Shape : Body->AggGeom.SphylElems)
				AddInfo(FString::Printf(TEXT("Capsule part=%s bone=%s center=%s rotation=%s radius=%.5f length=%.5f"), *Part, *Body->BoneName.ToString(), *Shape.Center.ToString(), *Shape.Rotation.ToString(), Shape.Radius, Shape.Length));
		}
		for (const UPhysicsConstraintTemplate* Constraint : PA->ConstraintSetup)
		{
			const FConstraintInstance& C = Constraint->DefaultInstance;
			AddInfo(FString::Printf(TEXT("Constraint part=%s bone1=%s bone2=%s linear=%d/%d/%d angular=%d/%d/%d limits=%.5f/%.5f/%.5f"), *Part, *C.ConstraintBone1.ToString(), *C.ConstraintBone2.ToString(), int32(C.GetLinearXMotion()), int32(C.GetLinearYMotion()), int32(C.GetLinearZMotion()), int32(C.GetAngularSwing1Motion()), int32(C.GetAngularSwing2Motion()), int32(C.GetAngularTwistMotion()), C.GetAngularSwing1Limit(), C.GetAngularSwing2Limit(), C.GetAngularTwistLimit()));
		}
	}
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *(Base + TEXT("Bluprints/BP_Player")));
	for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
	{
		const USceneComponent* Component = Cast<USceneComponent>(Node->ComponentTemplate);
		AddInfo(FString::Printf(TEXT("Component name=%s class=%s parent=%s nativeParent=%d socket=%s transform=%s"), *Node->GetVariableName().ToString(), *Node->ComponentClass->GetName(), *Node->ParentComponentOrVariableName.ToString(), Node->bIsParentComponentNative, *Node->AttachToName.ToString(), Component ? *Component->GetRelativeTransform().ToString() : TEXT("None")));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerPartsAuthor, "Khazan.PlayerParts.Author", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerPartsAuthor::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *(Base + TEXT("Bluprints/BP_Player")));
	ACharacter* Default = BP->GeneratedClass->GetDefaultObject<ACharacter>();
	for (const FString Part : {TEXT("Torso"), TEXT("Shoes"), TEXT("Leg"), TEXT("Hair"), TEXT("Arm")})
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(Part));
		UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(Part) + TEXT("_PhysicsAsset")));
		if (!TestNotNull(*Part, Mesh) || !TestNotNull(TEXT("Original PhysicsAsset"), PA)) return false;
		PA->Modify(); int32 Simulated = 0;
		for (USkeletalBodySetup* Body : PA->SkeletalBodySetups)
		{
			Body->Modify(); const bool bSecondary = SecondaryName(Body->BoneName) && HasBodyAncestor(PA, Mesh->GetRefSkeleton(), Body->BoneName);
			Body->PhysicsType = bSecondary ? PhysType_Simulated : PhysType_Kinematic;
			Simulated += bSecondary ? 1 : 0;
		}
		Save(PA);
		UAnimBlueprint* Animation = PartAnimation(Mesh, PA, Part, Simulated > 0);
		if (!TestTrue(TEXT("Part Animation compiled"), Animation->Status == BS_UpToDate)) return false;
		USCS_Node* PartNode = BP->SimpleConstructionScript->FindSCSNode(*Part);
		if (!PartNode) { PartNode = BP->SimpleConstructionScript->CreateNode(USkeletalMeshComponent::StaticClass(), *Part); BP->SimpleConstructionScript->AddNode(PartNode); }
		PartNode->SetParent(Default->GetMesh()); PartNode->AttachToName = NAME_None;
		USkeletalMeshComponent* Component = CastChecked<USkeletalMeshComponent>(PartNode->ComponentTemplate);
		Component->SetSkeletalMesh(Mesh); Component->SetRelativeTransform(FTransform::Identity);
		Component->SetLeaderPoseComponent(nullptr); Component->SetAnimInstanceClass(Animation->GeneratedClass); Component->SetPhysicsAsset(PA);
		Component->SetSimulatePhysics(false); Component->SetCollisionProfileName(TEXT("CharacterMesh")); Component->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		Component->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		AddInfo(FString::Printf(TEXT("Author part=%s bodies=%d simulated=%d physics=%s animation=%s"), *Part, PA->SkeletalBodySetups.Num(), Simulated, *PA->GetPathName(), *Animation->GetPathName()));
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
	Default = BP->GeneratedClass->GetDefaultObject<ACharacter>();
	Default->GetMesh()->Modify(); Default->GetMesh()->SetPhysicsAsset(LoadObject<UPhysicsAsset>(nullptr, *(Base + TEXT("Meshs/Player_PhysicsAsset"))));
	Default->GetMesh()->SetSimulatePhysics(false); Default->GetMesh()->SetCollisionProfileName(TEXT("CharacterMesh")); Default->GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Default->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	TestTrue(TEXT("Player Blueprint compiled"), BP->Status == BS_UpToDate);
	return Save(BP);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerPartsCollisionAudit, "Khazan.PlayerParts.CollisionAudit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerPartsCollisionAudit::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	UPhysicsAsset* BodyAsset = LoadObject<UPhysicsAsset>(nullptr, *(Base + TEXT("Meshs/Player_PhysicsAsset")));
	for (const FString Part : {TEXT("Torso"), TEXT("Leg"), TEXT("Hair")})
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(Part));
		UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(Part) + TEXT("_RigidBody_PhysicsAsset")));
		if (!TestNotNull(TEXT("Derived PA"), PA)) return false;
		AddInfo(FString::Printf(TEXT("CollisionAudit part=%s bodies=%d ignoredPairs=%d"), *Part, PA->SkeletalBodySetups.Num(), PA->CollisionDisableTable.Num()));
		for (const USkeletalBodySetup* Body : BodyAsset->SkeletalBodySetups)
			AddInfo(FString::Printf(TEXT("BodyCoverage part=%s bone=%s inSkeleton=%d inPhysics=%d"), *Part, *Body->BoneName.ToString(), Mesh->GetRefSkeleton().FindBoneIndex(Body->BoneName) != INDEX_NONE, PA->FindBodyIndex(Body->BoneName) != INDEX_NONE));
		for (int32 Index = 0; Index < PA->SkeletalBodySetups.Num(); ++Index)
		{
			const USkeletalBodySetup* Body = PA->SkeletalBodySetups[Index];
			int32 EnabledAnatomy = 0, DisabledAnatomy = 0;
			for (int32 Other = 0; Other < PA->SkeletalBodySetups.Num(); ++Other)
				if (Other != Index && BodyAsset->FindBodyIndex(PA->SkeletalBodySetups[Other]->BoneName) != INDEX_NONE)
					(PA->IsCollisionEnabled(Index, Other) ? EnabledAnatomy : DisabledAnatomy)++;
			AddInfo(FString::Printf(TEXT("CollisionBody part=%s bone=%s type=%d response=%d collision=%d linearDamping=%.6f angularDamping=%.6f anatomyEnabled=%d anatomyDisabled=%d"), *Part, *Body->BoneName.ToString(), int32(Body->PhysicsType), int32(Body->CollisionReponse), int32(Body->DefaultInstance.GetCollisionEnabled()), Body->DefaultInstance.LinearDamping, Body->DefaultInstance.AngularDamping, EnabledAnatomy, DisabledAnatomy));
		}
		for (const UPhysicsConstraintTemplate* Constraint : PA->ConstraintSetup)
		{
			const FConstraintInstance& C = Constraint->DefaultInstance;
			float Spring = 0.f, Damping = 0.f, Limit = 0.f; C.GetAngularDriveParams(Spring, Damping, Limit);
			const auto& Saved = Constraint->GetConstraintProfilePropertiesOrDefault(NAME_None);
			AddInfo(FString::Printf(TEXT("SavedJointLimitProfile part=%s bone=%s softSwing=%d softTwist=%d defaultSoftSwing=%d defaultSoftTwist=%d"), *Part, *C.ConstraintBone1.ToString(), C.ProfileInstance.ConeLimit.bSoftConstraint, C.ProfileInstance.TwistLimit.bSoftConstraint, Saved.ConeLimit.bSoftConstraint, Saved.TwistLimit.bSoftConstraint));
			AddInfo(FString::Printf(TEXT("CollisionJoint part=%s bone1=%s bone2=%s collisionDisabled=%d limits=%.6f/%.6f/%.6f orientationDrive=%d velocityDrive=%d spring=%.6f damping=%.6f"), *Part, *C.ConstraintBone1.ToString(), *C.ConstraintBone2.ToString(), C.IsCollisionDisabled(), C.GetAngularSwing1Limit(), C.GetAngularSwing2Limit(), C.GetAngularTwistLimit(), C.IsAngularOrientationDriveEnabled(), C.IsAngularVelocityDriveEnabled(), Spring, Damping));
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerPartsCollisionAuthor, "Khazan.PlayerParts.CollisionAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerPartsCollisionAuthor::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	// Temporary presentation tuning, NOT original-game metadata values.
	// Small velocity decay (s^-1); angular freedom and spring drives are retained.
	constexpr float LinearDamping = .05f, AngularDamping = .35f;
	// Thin contact shapes (cm). RBAN recreates ALL shape collision flags, so a
	// disabled mass-only shape is unsuitable here. Preserve imported mass and
	// body-axis inertia diagonals using calculated MassOverride/InertiaTensorScale.
	constexpr float ClothContactRadius = 1.f, HairContactRadius = .75f;
	struct FMassInfo { float Mass; FVector Diagonal; FTransform CoM; };
	auto Diagonal = [](const ImmediatePhysics::FActorSetup& Setup)
	{
		FVector Result;
		for (int32 Axis = 0; Axis < 3; ++Axis)
		{
			FVector Basis = FVector::ZeroVector; Basis[Axis] = 1.;
			Result[Axis] = Setup.CoMTransform.GetRotation().RotateVector(FVector(Setup.Inertia) * Setup.CoMTransform.GetRotation().UnrotateVector(Basis))[Axis];
		}
		return Result;
	};
	auto ReleaseBodies = [](TArray<FBodyInstance*>& Bodies)
	{
		for (FBodyInstance* Body : Bodies) { if (Body->IsValidBodyInstance()) Body->TermBody(true); delete Body; }
		Bodies.Reset();
	};
	UPhysicsAsset* Anatomy = LoadObject<UPhysicsAsset>(nullptr, *(Base + TEXT("Meshs/Player_PhysicsAsset")));
	for (const FString Part : {TEXT("Torso"), TEXT("Leg"), TEXT("Hair")})
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(Part));
		UPhysicsAsset* Source = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(Part) + TEXT("_PhysicsAsset")));
		UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(Part) + TEXT("_RigidBody_PhysicsAsset")));
		if (!TestNotNull(TEXT("Existing derived PA"), PA)) return false;
		PA->Modify();
		auto* Probe = NewObject<USkeletalMeshComponent>(); Probe->SetSkeletalMesh(Mesh);
		TArray<FBodyInstance*> SourceBodies;
		Probe->InstantiatePhysicsAssetBodiesRefPose(*Source, SourceBodies);
		TMap<FName, FMassInfo> OriginalMass;
		int32 Simulated = 0;
		for (const USkeletalBodySetup* OriginalBody : Source->SkeletalBodySetups)
		{
			USkeletalBodySetup* Body = PA->SkeletalBodySetups[PA->FindBodyIndex(OriginalBody->BoneName)];
			Body->Modify(); Body->AggGeom = OriginalBody->AggGeom;
			Body->DefaultInstance.CopyBodyInstancePropertiesFrom(&OriginalBody->DefaultInstance);
			const bool bSimulated = Body->PhysicsType == PhysType_Simulated;
			Body->CollisionReponse = bSimulated ? EBodyCollisionResponse::BodyCollision_Enabled : EBodyCollisionResponse::BodyCollision_Disabled;
			if (bSimulated)
			{
				++Simulated;
				if (!TestEqual(TEXT("Single source capsule for contact/mass calculation"), Body->AggGeom.SphylElems.Num(), 1) ||
					!TestEqual(TEXT("No additional mass/collision geometry"), Body->AggGeom.SphereElems.Num() + Body->AggGeom.BoxElems.Num() + Body->AggGeom.ConvexElems.Num(), 0)) { ReleaseBodies(SourceBodies); return false; }
				const auto Before = ImmediatePhysics::MakeDynamicActorSetup(SourceBodies[Source->FindBodyIndex(Body->BoneName)], FTransform::Identity);
				OriginalMass.Add(Body->BoneName, {float(Before.Mass), Diagonal(Before), Before.CoMTransform});
				Body->DefaultInstance.SetMassOverride(float(Before.Mass), true);
				Body->DefaultInstance.InertiaTensorScale = FVector::OneVector;
				Body->DefaultInstance.LinearDamping = LinearDamping;
				Body->DefaultInstance.AngularDamping = AngularDamping;
				for (FKSphylElem& Contact : Body->AggGeom.SphylElems)
				{
					Contact.Radius = FMath::Min(Contact.Radius, Part == TEXT("Hair") ? HairContactRadius : ClothContactRadius);
					Contact.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
					Contact.SetContributeToMass(true);
				}
			}
			Body->InvalidatePhysicsData();
		}
		ReleaseBodies(SourceBodies);
		TArray<FBodyInstance*> ThinBodies;
		Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, ThinBodies);
		for (const auto& Pair : OriginalMass)
		{
			const int32 Index = PA->FindBodyIndex(Pair.Key);
			const auto Thin = ImmediatePhysics::MakeDynamicActorSetup(ThinBodies[Index], FTransform::Identity);
			const FVector OldD = Pair.Value.Diagonal, NewD = Diagonal(Thin);
			// Invert Chaos::Utilities::ScaleInertia(bScaleMass=true):
			// q_i = old second moment_i / new second moment_i = det(S) * S_i^2.
			const FVector Q = (FVector(.5 * (OldD.X + OldD.Y + OldD.Z)) - OldD) / (FVector(.5 * (NewD.X + NewD.Y + NewD.Z)) - NewD);
			const double Determinant = FMath::Pow(Q.X * Q.Y * Q.Z, 1. / 5.);
			PA->SkeletalBodySetups[Index]->DefaultInstance.InertiaTensorScale = FVector(FMath::Sqrt(Q.X / Determinant), FMath::Sqrt(Q.Y / Determinant), FMath::Sqrt(Q.Z / Determinant));
		}
		ReleaseBodies(ThinBodies);
		Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, ThinBodies);
		bool bMassValid = true;
		for (const auto& Pair : OriginalMass)
		{
			const int32 Index = PA->FindBodyIndex(Pair.Key);
			const auto Final = ImmediatePhysics::MakeDynamicActorSetup(ThinBodies[Index], FTransform::Identity);
			const FVector Error = (Diagonal(Final) - Pair.Value.Diagonal) / Pair.Value.Diagonal;
			bMassValid &= TestTrue(TEXT("Imported mass retained (relative)"), FMath::Abs(Final.Mass / Pair.Value.Mass - 1.) < .0001);
			bMassValid &= TestTrue(TEXT("Imported body-axis inertia diagonals retained (relative)"), Error.GetAbsMax() < .001);
			bMassValid &= TestTrue(TEXT("Imported center of mass retained (cm)"), Final.CoMTransform.GetLocation().Equals(Pair.Value.CoM.GetLocation(), .001));
			AddInfo(FString::Printf(TEXT("CalculatedMass part=%s bone=%s massKg=%.6f bodyInertiaKgCm2=%s inertiaRelativeError=%s scale=%s"), *Part, *Pair.Key.ToString(), double(Final.Mass), *Diagonal(Final).ToString(), *Error.ToString(), *PA->SkeletalBodySetups[Index]->DefaultInstance.InertiaTensorScale.ToString()));
		}
		ReleaseBodies(ThinBodies);
		if (!bMassValid) return false;
		// Internal fitted volumes/helper anchors overlap by design. Real skin
		// arrives through the engine's external collision source below, including
		// anatomy bones absent from a part's own skeletal-mesh reference skeleton.
		for (int32 A = 0; A < PA->SkeletalBodySetups.Num(); ++A)
			for (int32 B = A + 1; B < PA->SkeletalBodySetups.Num(); ++B)
				PA->DisableCollision(A, B);
		PA->UpdateBoundsBodiesArray();
		if (!Save(PA)) return false;
		UAnimBlueprint* Animation = LoadObject<UAnimBlueprint>(nullptr, *(Base + TEXT("Bluprints/Parts/ABP_Player_Original_") + Part));
		TArray<UEdGraph*> Graphs; Animation->GetAllGraphs(Graphs);
		int32 RigidNodes = 0;
		for (UEdGraph* Graph : Graphs)
			for (UEdGraphNode* GraphNode : Graph->Nodes)
				if (auto* Rigid = Cast<UAnimGraphNode_RigidBody>(GraphNode)) { Rigid->Node.bUseExternalClothCollision = true; ++RigidNodes; }
		if (!TestEqual(TEXT("One existing RigidBody node"), RigidNodes, 1)) return false;
		FBlueprintEditorUtils::MarkBlueprintAsModified(Animation); FKismetEditorUtilities::CompileBlueprint(Animation);
		if (!TestTrue(TEXT("External-collision ABP compiled"), Animation->Status == BS_UpToDate) || !Save(Animation)) return false;
		AddInfo(FString::Printf(TEXT("CollisionAuthor part=%s bodies=%d simulated=%d externalBodyColliders=%d linearDamping=%.3f angularDamping=%.3f contactRadiusCm=%.3f"), *Part, PA->SkeletalBodySetups.Num(), Simulated, Anatomy->SkeletalBodySetups.Num(), LinearDamping, AngularDamping, Part == TEXT("Hair") ? HairContactRadius : ClothContactRadius));
	}
	// Register the actual parent component (not a CDO/template) when this BP is
	// constructed. Engine AddClothCollisionSource deduplicates the weak source;
	// SkeletalMeshComponent/RBAN own its cache, prerequisites and teardown.
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *(Base + TEXT("Bluprints/BP_Player")));
	TArray<UEdGraph*> Graphs; BP->GetAllGraphs(Graphs);
	UEdGraph* Construction = *Graphs.FindByPredicate([](UEdGraph* G) { return G->GetFName() == TEXT("UserConstructionScript"); });
	const UEdGraphSchema* Schema = Construction->GetSchema();
	UEdGraphNode* Entry = nullptr;
	for (UEdGraphNode* GraphNode : Construction->Nodes) if (GraphNode->GetClass()->GetFName() == TEXT("K2Node_FunctionEntry")) Entry = GraphNode;
	if (!TestNotNull(TEXT("Existing construction entry"), Entry)) return false;
	UEdGraphPin* Last = Entry->FindPinChecked(TEXT("then"));
	const TArray<UEdGraphPin*> OldLinks = Last->LinkedTo;
	const FString Prefix = TEXT("PlayerPartsBodyCollider:");
	const bool bAlreadyAuthored = Construction->Nodes.ContainsByPredicate([&](UEdGraphNode* N) { return N->NodeComment == Prefix + TEXT("Torso"); });
	if (!bAlreadyAuthored)
	{
		Last->BreakAllPinLinks();
		// Use the editor's normal paste/reflection path. Direct K2 class imports
		// from this isolated Runtime module can load BlueprintGraph too early.
		auto Paste = [&](const FString& Class, const FString& Properties, int32 X, int32 Y)
		{
			const FString Text = FString::Printf(TEXT("Begin Object Class=/Script/BlueprintGraph.%s Name=\"PlayerParts_%s\"\n%s\nNodePosX=%d\nNodePosY=%d\nEnd Object\n"), *Class, *FGuid::NewGuid().ToString(EGuidFormats::Digits), *Properties, X, Y);
			TSet<UEdGraphNode*> Imported;
			FEdGraphUtilities::ImportNodesFromText(Construction, Text, Imported);
			check(Imported.Num() == 1);
			UEdGraphNode* Result = *Imported.CreateConstIterator();
			// ImportNodesFromText already calls ReconstructNode/allocates pins.
			return Result;
		};
		auto Variable = [&](FName Name, int32 X, int32 Y)
		{
			auto* V = Paste(TEXT("K2Node_VariableGet"), FString::Printf(TEXT("VariableReference=(MemberName=\"%s\",bSelfContext=True)"), *Name.ToString()), X, Y);
			V->NodeComment = Prefix + Name.ToString(); return V->FindPinChecked(Name);
		};
		UEdGraphPin* Parent = Variable(TEXT("Mesh"), 0, 300);
		int32 X = 350;
		for (const FString Part : {TEXT("Torso"), TEXT("Leg"), TEXT("Hair")})
		{
			auto* Call = Paste(TEXT("K2Node_CallFunction"), TEXT("FunctionReference=(MemberParent=\"/Script/CoreUObject.Class'/Script/Engine.SkeletalMeshComponent'\",MemberName=\"AddClothCollisionSource\")"), X, 0);
			Call->NodePosX = X; Call->NodeComment = Prefix + Part;
			if (!TestTrue(TEXT("Construction execution link"), Schema->TryCreateConnection(Last, Call->FindPinChecked(TEXT("execute"))))) return false;
			if (!TestTrue(TEXT("Part collision target link"), Schema->TryCreateConnection(Variable(*Part, X, 550), Call->FindPinChecked(TEXT("self"))))) return false;
			if (!TestTrue(TEXT("Actual parent collision source link"), Schema->TryCreateConnection(Parent, Call->FindPinChecked(TEXT("InSourceComponent"))))) return false;
			Schema->TrySetDefaultObject(*Call->FindPinChecked(TEXT("InSourcePhysicsAsset")), Anatomy);
			Last = Call->FindPinChecked(TEXT("then")); X += 400;
		}
		for (UEdGraphPin* OldLink : OldLinks) Schema->TryCreateConnection(Last, OldLink);
	}
	TSet<UObject*> ExportNodes;
	for (UEdGraphNode* N : Construction->Nodes) ExportNodes.Add(N);
	FString GraphText; FEdGraphUtilities::ExportNodesToText(ExportNodes, GraphText);
	FFileHelper::SaveStringToFile(GraphText, *(FPaths::ProjectSavedDir() / TEXT("PlayerPartsBodyCollisionConstruction.txt")));
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
	if (!TestTrue(TEXT("Body collision construction compiled"), BP->Status == BS_UpToDate)) return false;
	return Save(BP);
}

namespace KZPlayerPartsAuthor
{
TMap<int32, int32> HairInfluences(USkeletalMesh* Mesh)
{
	TMap<int32, int32> Counts;
	const FSkeletalMeshModel* Model = Mesh->GetImportedModel();
	if (!Model || Model->LODModels.IsEmpty()) return Counts;
	for (const FSkelMeshSection& Section : Model->LODModels[0].Sections)
		for (const FSoftSkinVertex& Vertex : Section.SoftVertices)
			for (int32 Influence = 0; Influence < UE_ARRAY_COUNT(Vertex.InfluenceBones); ++Influence)
				if (Vertex.InfluenceWeights[Influence] > 0 && Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[Influence]))
					++Counts.FindOrAdd(Section.BoneMap[Vertex.InfluenceBones[Influence]]);
	return Counts;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerClothAudit, "Khazan.PlayerParts.ClothAudit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerClothAudit::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	FString Report;
	for (const FString Part : {TEXT("Torso"), TEXT("Leg")})
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(Part));
		UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(Part) + TEXT("_RigidBody_PhysicsAsset")));
		if (!TestNotNull(TEXT("Existing cloth mesh"), Mesh) || !TestNotNull(TEXT("Existing cloth PhysicsAsset"), PA)) return false;
		const auto Counts = HairInfluences(Mesh);
		if (!TestTrue(TEXT("Imported cloth vertex weights available"), Counts.Num() > 0)) return false;
		const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
		int32 SecondaryBones = 0, WeightedBones = 0;
		for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
		{
			const FString Name = Ref.GetBoneName(Index).ToString();
			if (!Name.StartsWith(TEXT("B_Cape_")) && !Name.StartsWith(TEXT("B_Cloth_")) && !Name.StartsWith(TEXT("B_Leather_")) && !Name.StartsWith(TEXT("B_Iron_"))) continue;
			++SecondaryBones; WeightedBones += Counts.FindRef(Index) > 0 ? 1 : 0;
			const int32 Parent = Ref.GetParentIndex(Index), Body = PA->FindBodyIndex(Ref.GetBoneName(Index));
			const FString ParentName = Parent != INDEX_NONE ? Ref.GetBoneName(Parent).ToString() : TEXT("None");
			const FString Line = FString::Printf(TEXT("ClothBone part=%s index=%d name=%s parent=%s weightedVertices=%d currentBody=%d currentPhysicsType=%d localLengthCm=%.6f"), *Part, Index, *Name, *ParentName, Counts.FindRef(Index), Body, Body != INDEX_NONE ? int32(PA->SkeletalBodySetups[Body]->PhysicsType) : -1, Ref.GetRefBonePose()[Index].GetTranslation().Size());
			AddInfo(Line); Report += Line + TEXT("\n");
		}
		const FString Summary = FString::Printf(TEXT("ClothAudit part=%s mesh=%s physics=%s secondaryBones=%d weightedSecondaryBones=%d currentBodies=%d currentConstraints=%d"), *Part, *Mesh->GetPathName(), *PA->GetPathName(), SecondaryBones, WeightedBones, PA->SkeletalBodySetups.Num(), PA->ConstraintSetup.Num());
		AddInfo(Summary); Report += Summary + TEXT("\n");
	}
	return FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir() / TEXT("PlayerClothAudit.txt")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerHairAudit, "Khazan.PlayerParts.HairAudit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerHairAudit::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Hair")));
	UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(TEXT("Hair")) + TEXT("_RigidBody_PhysicsAsset")));
	const auto Counts = HairInfluences(Mesh);
	if (!TestTrue(TEXT("Imported hair vertex weights available"), Counts.Num() > 0)) return false;
	const auto& Ref = Mesh->GetRefSkeleton();
	FString Report;
	for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
		if (Ref.GetBoneName(Index).ToString().StartsWith(TEXT("Hair_")))
		{
			const FString Line = FString::Printf(TEXT("HairBone index=%d name=%s parent=%s weightedVertices=%d currentBody=%d localLengthCm=%.6f"), Index, *Ref.GetBoneName(Index).ToString(), *Ref.GetBoneName(Ref.GetParentIndex(Index)).ToString(), Counts.FindRef(Index), PA->FindBodyIndex(Ref.GetBoneName(Index)), Ref.GetRefBonePose()[Index].GetTranslation().Size());
			AddInfo(Line); Report += Line + TEXT("\n");
		}
	return FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir() / TEXT("PlayerHairAudit.txt")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerHairAuthor, "Khazan.PlayerParts.HairAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerHairAuthor::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	// All feel parameters are assistant-selected temporary tuning, read from one
	// isolated author INI and stored on the existing hair PhysicsAsset. Not game metadata.
	FConfigFile Settings;
	Settings.Read(FPaths::ProjectSavedDir() / TEXT("PlayerHairRefinement.ini"));
	if (!TestTrue(TEXT("Hair tuning settings present"), Settings.Num() > 0)) return false;
	float Radius = 0, Density = 0, RootOmega = 0, TipOmega = 0, RootSwing = 0, TipSwing = 0, RootTwist = 0, TipTwist = 0, LinearDamping = 0, RootDamping = 0, TipDamping = 0;
	struct FSetting { const TCHAR* Key; float* Value; };
	for (const FSetting Item : { FSetting{TEXT("ContactRadiusCm"), &Radius}, {TEXT("MassPerLengthKgPerCm"), &Density}, {TEXT("RootOmegaPerSecond"), &RootOmega}, {TEXT("TipOmegaPerSecond"), &TipOmega}, {TEXT("RootSwingDegrees"), &RootSwing}, {TEXT("TipSwingDegrees"), &TipSwing}, {TEXT("RootTwistDegrees"), &RootTwist}, {TEXT("TipTwistDegrees"), &TipTwist}, {TEXT("LinearDampingPerSecond"), &LinearDamping}, {TEXT("RootAngularDampingPerSecond"), &RootDamping}, {TEXT("TipAngularDampingPerSecond"), &TipDamping} })
		if (!TestTrue(Item.Key, Settings.GetFloat(TEXT("HairRefinement"), Item.Key, *Item.Value) && *Item.Value > 0)) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Hair")));
	UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(TEXT("Hair")) + TEXT("_RigidBody_PhysicsAsset")));
	const auto& Ref = Mesh->GetRefSkeleton();
	const auto Counts = HairInfluences(Mesh);
	if (!TestTrue(TEXT("Vertex-weight evidence before refinement"), Counts.Num() > 0)) return false;
	TSet<int32> Bones;
	for (const auto& Pair : Counts)
	{
		// Refine the existing ponytail. The two short face locks are attached
		// inside the head collider and were animation-driven in the baseline;
		// retain their CopyPose behavior rather than forcing embedded root capsules.
		int32 Anchor = Pair.Key;
		while (Anchor > 0 && Ref.GetBoneName(Anchor) != TEXT("Hair_BoneRoot_002")) Anchor = Ref.GetParentIndex(Anchor);
		if (Anchor <= 0) continue;
		int32 Index = Pair.Key;
		while (Index > 0 && SecondaryName(Ref.GetBoneName(Index)))
		{
			Bones.Add(Index); Index = Ref.GetParentIndex(Index);
		}
	}
	TArray<int32> Ordered = Bones.Array(); Ordered.Sort();
	// Unit transforms describe actual world-sized bones. Only connector translations
	// are divided by the imported wrapper scale, exactly as the existing RBAN contract.
	const double WrapperScale = Ref.GetRefBonePose()[0].GetScale3D().X;
	TArray<FTransform> Unit;
	for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
	{
		FTransform Pose = Ref.GetRefBonePose()[Index];
		if (Index > 0) Pose = Pose * Unit[Ref.GetParentIndex(Index)];
		Unit.Add(Pose);
	}
	for (FTransform& Pose : Unit) { Pose.SetTranslation(Pose.GetTranslation() / WrapperScale); Pose.SetScale3D(FVector::OneVector); }
	PA->Modify();
	PA->SkeletalBodySetups.RemoveAll([](const USkeletalBodySetup* Body) { return Body->PhysicsType == PhysType_Simulated; });
	PA->ConstraintSetup.Reset(); PA->CollisionDisableTable.Reset();
	PA->UpdateBodySetupIndexMap();
	TMap<FString, int32> ChainLengths;
	auto Chain = [&](int32 Index) { FString Name = Ref.GetBoneName(Index).ToString(); int32 Separator; Name.FindLastChar(TEXT('_'), Separator); return Name.Left(Separator); };
	for (int32 Index : Ordered) ++ChainLengths.FindOrAdd(Chain(Index));
	FString Report; double TotalMass = 0.;
	for (int32 Index : Ordered)
	{
		int32 Parent = Ref.GetParentIndex(Index), Depth = 1;
		while (Bones.Contains(Parent)) { ++Depth; Parent = Ref.GetParentIndex(Parent); }
		const float Fraction = ChainLengths[Chain(Index)] > 1 ? float(Depth - 1) / float(ChainLengths[Chain(Index)] - 1) : 0.f;
		int32 Child = INDEX_NONE;
		for (int32 Candidate = Index + 1; Candidate < Ref.GetNum(); ++Candidate)
			if (Ref.GetParentIndex(Candidate) == Index && SecondaryName(Ref.GetBoneName(Candidate))) { Child = Candidate; break; }
		// Imported bone geometry defines segment length and direction. A weighted tip
		// without an explicit end marker continues its parent's measured segment vector.
		FVector Segment = Child != INDEX_NONE ? Unit[Index].InverseTransformPosition(Unit[Child].GetLocation()) :
			Unit[Index].InverseTransformVector(Unit[Index].GetLocation() - Unit[Ref.GetParentIndex(Index)].GetLocation());
		const float Length = float(Segment.Size());
		if (!TestTrue(TEXT("Positive imported hair segment length"), Length > 2.f * Radius)) return false;
		USkeletalBodySetup* Body = NewObject<USkeletalBodySetup>(PA, NAME_None, RF_Transactional);
		Body->BoneName = Ref.GetBoneName(Index); Body->PhysicsType = PhysType_Simulated;
		Body->CollisionReponse = EBodyCollisionResponse::BodyCollision_Enabled;
		Body->DefaultInstance.LinearDamping = LinearDamping;
		Body->DefaultInstance.AngularDamping = FMath::Lerp(RootDamping, TipDamping, Fraction);
		Body->DefaultInstance.SetMassOverride(Density * Length, true);
		Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Body->DefaultInstance.InertiaTensorScale = FVector::OneVector;
		FKSphylElem Capsule; Capsule.Radius = Radius; Capsule.Length = Length - 2.f * Radius;
		Capsule.Center = Segment * .5;
		Capsule.Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Segment.GetSafeNormal()).Rotator();
		Capsule.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Body->AggGeom.SphylElems.Add(Capsule);
		Body->InvalidatePhysicsData(); PA->SkeletalBodySetups.Add(Body); PA->UpdateBodySetupIndexMap(); TotalMass += Density * Length;
		UPhysicsConstraintTemplate* Joint = NewObject<UPhysicsConstraintTemplate>(PA, NAME_None, RF_Transactional);
		FConstraintInstance& C = Joint->DefaultInstance;
		C.JointName = Body->BoneName; C.ConstraintBone1 = Body->BoneName; C.ConstraintBone2 = Ref.GetBoneName(Ref.GetParentIndex(Index));
		while (PA->FindBodyIndex(C.ConstraintBone2) == INDEX_NONE)
			C.ConstraintBone2 = Ref.GetBoneName(Ref.GetParentIndex(Ref.FindBoneIndex(C.ConstraintBone2)));
		C.SetRefFrame(EConstraintFrame::Frame1, FTransform::Identity);
		FTransform ParentFrame = Unit[Index].GetRelativeTransform(Unit[Ref.FindBoneIndex(C.ConstraintBone2)]);
		ParentFrame.SetTranslation(ParentFrame.GetTranslation() / WrapperScale);
		C.SetRefFrame(EConstraintFrame::Frame2, ParentFrame);
		C.SetLinearXMotion(LCM_Locked); C.SetLinearYMotion(LCM_Locked); C.SetLinearZMotion(LCM_Locked);
		const float Swing = FMath::Lerp(RootSwing, TipSwing, Fraction), Twist = FMath::Lerp(RootTwist, TipTwist, Fraction);
		C.SetAngularSwing1Limit(ACM_Limited, Swing); C.SetAngularSwing2Limit(ACM_Limited, Swing); C.SetAngularTwistLimit(ACM_Limited, Twist);
		C.SetDisableCollision(true); C.SetAngularDriveMode(EAngularDriveMode::SLERP);
		C.SetOrientationDriveSLERP(true); C.SetAngularVelocityDriveSLERP(true);
		C.SetAngularOrientationTarget(FQuat::Identity); C.SetAngularVelocityTarget(FVector::ZeroVector);
		const float Omega = FMath::Lerp(RootOmega, TipOmega, Fraction);
		// Acceleration spring k=omega^2, near-critical relative damping c=2*omega.
		// ImmediatePhysics uses acceleration mode, independent of imported auto-fit mass.
		C.SetAngularDriveAccelerationMode(true); C.SetAngularDriveParams(Omega * Omega, 2.f * Omega, 0.f);
		// PIE and save use the template's DEFAULT profile, not its current editor
		// instance. Synchronize it explicitly so limits/drives persist and are consumed.
		Joint->SetDefaultProfile(C);
		PA->ConstraintSetup.Add(Joint);
		const FString Line = FString::Printf(TEXT("HairRefined bone=%s parent=%s weightedVertices=%d depth=%d fraction=%.4f lengthCm=%.6f massKg=%.6f radiusCm=%.3f swingDeg=%.3f twistDeg=%.3f omegaPerSecond=%.3f spring=%.3f driveDamping=%.3f angularDamping=%.3f connector2=%s"), *Body->BoneName.ToString(), *C.ConstraintBone2.ToString(), Counts.FindRef(Index), Depth, Fraction, Length, Density * Length, Radius, Swing, Twist, Omega, Omega * Omega, 2.f * Omega, Body->DefaultInstance.AngularDamping, *C.Pos2.ToString());
		AddInfo(Line); Report += Line + TEXT("\n");
	}
	PA->UpdateBodySetupIndexMap(); PA->UpdateBoundsBodiesArray();
	// Temporary bundle-inertia conditioning: a sub-centimetre contact capsule's
	// axial inertia is much smaller than its transverse inertia and can spin/flip
	// under skin contact. Keep mass/contact geometry, raise only small inertia axes
	// to the capsule's largest principal moment. This is NOT original-game data.
	auto* Probe = NewObject<USkeletalMeshComponent>(); Probe->SetSkeletalMesh(Mesh);
	TArray<FBodyInstance*> Bodies;
	Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, Bodies);
	for (USkeletalBodySetup* Body : PA->SkeletalBodySetups)
	{
		if (Body->PhysicsType != PhysType_Simulated) continue;
		const auto Thin = ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(Body->BoneName)], FTransform::Identity);
		FVector Diagonal;
		for (int32 Axis = 0; Axis < 3; ++Axis)
		{
			FVector Basis = FVector::ZeroVector; Basis[Axis] = 1.;
			Diagonal[Axis] = Thin.CoMTransform.GetRotation().RotateVector(FVector(Thin.Inertia) * Thin.CoMTransform.GetRotation().UnrotateVector(Basis))[Axis];
		}
		const double Target = FVector(Thin.Inertia).GetMax();
		const FVector Q = FVector(.5 * Target) / (FVector(.5 * (Diagonal.X + Diagonal.Y + Diagonal.Z)) - Diagonal);
		const double Determinant = FMath::Pow(Q.X * Q.Y * Q.Z, 1. / 5.);
		Body->DefaultInstance.InertiaTensorScale = FVector(FMath::Sqrt(Q.X / Determinant), FMath::Sqrt(Q.Y / Determinant), FMath::Sqrt(Q.Z / Determinant));
		const FString Line = FString::Printf(TEXT("HairInertia bone=%s thinPrincipalKgCm2=%s targetDiagonalKgCm2=%.8f inertiaScale=%s"), *Body->BoneName.ToString(), *FVector(Thin.Inertia).ToString(), Target, *Body->DefaultInstance.InertiaTensorScale.ToString());
		AddInfo(Line); Report += Line + TEXT("\n");
	}
	for (FBodyInstance* Body : Bodies) { if (Body->IsValidBodyInstance()) Body->TermBody(true); delete Body; }
	Bodies.Reset();
	for (int32 A = 0; A < PA->SkeletalBodySetups.Num(); ++A)
		for (int32 B = A + 1; B < PA->SkeletalBodySetups.Num(); ++B) PA->DisableCollision(A, B);
	PA->RefreshPhysicsAssetChange();
	AddInfo(FString::Printf(TEXT("HairRefinement bodies=%d simulated=%d strands=%d totalMassKg=%.6f"), PA->SkeletalBodySetups.Num(), Ordered.Num(), ChainLengths.Num(), TotalMass));
	return FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir() / TEXT("PlayerHairRefinement.txt"))) && Save(PA);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerClothAuthor, "Khazan.PlayerParts.ClothAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerClothAuthor::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	// Assistant-selected temporary cloth tuning; NOT original-game metadata.
	// One isolated INI owns feel/contact settings; only the two existing cloth PAs are saved.
	FConfigFile Settings; Settings.Read(FPaths::ProjectSavedDir() / TEXT("PlayerClothRefinement.ini"));
	if (!TestTrue(TEXT("Cloth tuning settings present"), Settings.Num() > 0)) return false;
	float Radius = 0, Density = 0, RootOmega = 0, TipOmega = 0, RootSwing = 0, TipSwing = 0, RootTwist = 0, TipTwist = 0, LinearDamping = 0, RootDamping = 0, TipDamping = 0, AnchorTolerance = 0, ProjectionAngularAlpha = 0;
	struct FSetting { const TCHAR* Key; float* Value; };
	for (const FSetting Item : { FSetting{TEXT("ContactRadiusCm"), &Radius}, {TEXT("MassPerLengthKgPerCm"), &Density}, {TEXT("RootOmegaPerSecond"), &RootOmega}, {TEXT("TipOmegaPerSecond"), &TipOmega}, {TEXT("RootSwingDegrees"), &RootSwing}, {TEXT("TipSwingDegrees"), &TipSwing}, {TEXT("RootTwistDegrees"), &RootTwist}, {TEXT("TipTwistDegrees"), &TipTwist}, {TEXT("LinearDampingPerSecond"), &LinearDamping}, {TEXT("RootAngularDampingPerSecond"), &RootDamping}, {TEXT("TipAngularDampingPerSecond"), &TipDamping}, {TEXT("CoincidentAnchorToleranceCm"), &AnchorTolerance}, {TEXT("ProjectionAngularAlpha"), &ProjectionAngularAlpha} })
		if (!TestTrue(Item.Key, Settings.GetFloat(TEXT("ClothRefinement"), Item.Key, *Item.Value) && FMath::IsFinite(*Item.Value) && *Item.Value > 0)) return false;
	if (!TestTrue(TEXT("Temporary angular projection alpha does not exceed one"), ProjectionAngularAlpha <= 1.f)) return false;
	float RootSwingDegreesLeg = RootSwing;
	Settings.GetFloat(TEXT("ClothRefinement"), TEXT("RootSwingDegreesLeg"), RootSwingDegreesLeg);
	if (!TestTrue(TEXT("Positive finite temporary Leg root-clearance swing override"), FMath::IsFinite(RootSwingDegreesLeg) && RootSwingDegreesLeg > 0.f)) return false;
	bool bTrimTerminalBackwardsOverlap = false;
	if (!TestTrue(TEXT("Explicit terminal backwards-overlap policy"), Settings.GetBool(TEXT("ClothRefinement"), TEXT("TrimTerminalBackwardsOverlap"), bTrimTerminalBackwardsOverlap))) return false;
	bool bHardAngularLimits = false;
	if (!TestTrue(TEXT("Explicit temporary cloth angular-limit policy"), Settings.GetBool(TEXT("ClothRefinement"), TEXT("HardAngularLimits"), bHardAngularLimits))) return false;
	bool bParentDominates = false;
	if (!TestTrue(TEXT("Explicit temporary cloth parent-dominance policy"), Settings.GetBool(TEXT("ClothRefinement"), TEXT("ParentDominates"), bParentDominates))) return false;
	bool bUseDominantTerminalSupport = false;
	if (!TestTrue(TEXT("Explicit temporary cloth terminal ownership policy"), Settings.GetBool(TEXT("ClothRefinement"), TEXT("UseDominantTerminalSupport"), bUseDominantTerminalSupport))) return false;
	bool bRotationInvariantInertiaConditioning = false;
	if (!TestTrue(TEXT("Explicit temporary cloth principal-inertia floor policy"), Settings.GetBool(TEXT("ClothRefinement"), TEXT("RotationInvariantInertiaConditioning"), bRotationInvariantInertiaConditioning))) return false;
	bool bUseDominantClothStripBoxesLeg = false;
	if (!TestTrue(TEXT("Explicit temporary Leg dominant strip contact policy"), Settings.GetBool(TEXT("ClothRefinement"), TEXT("UseDominantClothStripBoxesLeg"), bUseDominantClothStripBoxesLeg))) return false;
	bool bUseFullDominantClothStripBoundsLeg = false;
	Settings.GetBool(TEXT("ClothRefinement"), TEXT("UseFullDominantClothStripBoundsLeg"), bUseFullDominantClothStripBoundsLeg);
	float UniformPrincipalInertiaFloorMultiplierLeg = 1.f;
	Settings.GetFloat(TEXT("ClothRefinement"), TEXT("UniformPrincipalInertiaFloorMultiplierLeg"), UniformPrincipalInertiaFloorMultiplierLeg);
	if (!TestTrue(TEXT("Positive finite temporary Leg principal-inertia floor multiplier"), FMath::IsFinite(UniformPrincipalInertiaFloorMultiplierLeg) && UniformPrincipalInertiaFloorMultiplierLeg > 0.f)) return false;
	FString AdditionalProtectedAttachmentBonesLeg;
	Settings.GetString(TEXT("ClothRefinement"), TEXT("AdditionalProtectedAttachmentBonesLeg"), AdditionalProtectedAttachmentBonesLeg);
	auto IsCloth = [](FName Bone)
	{
		const FString Name = Bone.ToString();
		return Name.StartsWith(TEXT("B_Cape_")) || Name.StartsWith(TEXT("B_Cloth_")) || Name.StartsWith(TEXT("B_Leather_")) || Name.StartsWith(TEXT("B_Iron_"));
	};
	auto IsIron = [](FName Bone) { return Bone.ToString().StartsWith(TEXT("B_Iron_")); };
	FString Report;
	USkeletalMesh* AnatomyMesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Body")));
	UPhysicsAsset* AnatomyPA = LoadObject<UPhysicsAsset>(nullptr, *(Base + TEXT("Meshs/Player_PhysicsAsset")));
	if (!TestNotNull(TEXT("Current parent anatomy mesh"), AnatomyMesh) || !TestNotNull(TEXT("Current parent anatomy PhysicsAsset"), AnatomyPA)) return false;
	const FReferenceSkeleton& AnatomyRef = AnatomyMesh->GetRefSkeleton();
	const double AnatomyWrapperScale = AnatomyRef.GetRefBonePose()[0].GetScale3D().X;
	if (!TestTrue(TEXT("Positive uniform parent anatomy wrapper scale"), FMath::IsFinite(AnatomyWrapperScale) && AnatomyWrapperScale > 0. && AnatomyRef.GetRefBonePose()[0].GetScale3D().Equals(FVector(AnatomyWrapperScale)))) return false;
	TArray<FTransform> AnatomyUnit;
	for (int32 Index = 0; Index < AnatomyRef.GetNum(); ++Index)
	{
		FTransform Pose = AnatomyRef.GetRefBonePose()[Index];
		if (Index > 0) Pose = Pose * AnatomyUnit[AnatomyRef.GetParentIndex(Index)];
		AnatomyUnit.Add(Pose);
	}
	for (FTransform& Pose : AnatomyUnit) { Pose.SetTranslation(Pose.GetTranslation() / AnatomyWrapperScale); Pose.SetScale3D(FVector::OneVector); }
	struct FAnatomyShape
	{
		enum class EType { Capsule, Sphere, Box };
		FName Bone; EType Type; FTransform UnitTransform; FVector Dimensions;
	};
	TArray<FAnatomyShape> AnatomyShapes;
	for (const USkeletalBodySetup* Body : AnatomyPA->SkeletalBodySetups)
	{
		const int32 Bone = AnatomyRef.FindBoneIndex(Body->BoneName);
		if (!TestTrue(TEXT("Anatomy collision bone exists and shapes supported"), Bone != INDEX_NONE && Body->AggGeom.GetElementCount() == Body->AggGeom.SphylElems.Num() + Body->AggGeom.SphereElems.Num() + Body->AggGeom.BoxElems.Num())) return false;
		// Geometry is already centimetres at RBAN's observed unit actor scale; only
		// reference translations remove the imported wrapper, not shape dimensions.
		for (const FKSphylElem& Shape : Body->AggGeom.SphylElems)
			AnatomyShapes.Add({Body->BoneName, FAnatomyShape::EType::Capsule, Shape.GetTransform() * AnatomyUnit[Bone], FVector(Shape.Radius, Shape.Length, 0.)});
		for (const FKSphereElem& Shape : Body->AggGeom.SphereElems)
			AnatomyShapes.Add({Body->BoneName, FAnatomyShape::EType::Sphere, Shape.GetTransform() * AnatomyUnit[Bone], FVector(Shape.Radius, 0., 0.)});
		for (const FKBoxElem& Shape : Body->AggGeom.BoxElems)
			AnatomyShapes.Add({Body->BoneName, FAnatomyShape::EType::Box, Shape.GetTransform() * AnatomyUnit[Bone], FVector(Shape.X, Shape.Y, Shape.Z)});
	}
	if (!TestTrue(TEXT("Existing parent anatomy collision shapes available"), !AnatomyShapes.IsEmpty())) return false;
	for (const FString Part : {TEXT("Torso"), TEXT("Leg")})
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(Part));
		UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(Part) + TEXT("_RigidBody_PhysicsAsset")));
		if (!TestNotNull(TEXT("Existing cloth mesh"), Mesh) || !TestNotNull(TEXT("Existing cloth PhysicsAsset"), PA)) return false;
		const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
		const auto Counts = HairInfluences(Mesh);
		if (!TestTrue(TEXT("Cloth weighted vertices available"), Counts.Num() > 0)) return false;
		const double WrapperScale = Ref.GetRefBonePose()[0].GetScale3D().X;
		if (!TestTrue(TEXT("Positive uniform imported wrapper scale"), FMath::IsFinite(WrapperScale) && WrapperScale > 0. && Ref.GetRefBonePose()[0].GetScale3D().Equals(FVector(WrapperScale)))) return false;
		TArray<FTransform> Unit;
		for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
		{
			FTransform Pose = Ref.GetRefBonePose()[Index];
			if (Index > 0) Pose = Pose * Unit[Ref.GetParentIndex(Index)];
			Unit.Add(Pose);
		}
		for (FTransform& Pose : Unit) { Pose.SetTranslation(Pose.GetTranslation() / WrapperScale); Pose.SetScale3D(FVector::OneVector); }
		TSet<int32> Bones, Kinematic;
		for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
			if (IsCloth(Ref.GetBoneName(Index))) Bones.Add(Index);
		for (const auto& Pair : Counts)
			for (int32 Index = Pair.Key; Index > 0 && IsCloth(Ref.GetBoneName(Index)); Index = Ref.GetParentIndex(Index)) Bones.Add(Index);
		TArray<int32> Ordered = Bones.Array(); Ordered.Sort();
		for (int32 Index : Ordered)
		{
			const int32 Parent = Ref.GetParentIndex(Index);
			if (!Bones.Contains(Parent) || (Part == TEXT("Leg") && Counts.FindRef(Parent) == 0 && Ref.GetRefBonePose()[Index].GetTranslation().Size() <= AnchorTolerance)) Kinematic.Add(Index);
			if (IsIron(Ref.GetBoneName(Index))) continue;
			// A connector pivot inside the skin proxy cannot be pulled outside while
			// its linear axes stay locked. Retain CopyPose at embedded/near-skin pivots;
			// descendants with clearance still simulate. Margin reuses ContactRadiusCm.
			double NearestPhi = DBL_MAX; FName NearestBone = NAME_None; FAnatomyShape::EType NearestType = FAnatomyShape::EType::Capsule;
			for (const FAnatomyShape& Shape : AnatomyShapes)
			{
				const FVector Point = Shape.UnitTransform.InverseTransformPosition(Unit[Index].GetLocation());
				double Phi = 0.;
				if (Shape.Type == FAnatomyShape::EType::Capsule)
					Phi = (Point - FVector(0., 0., FMath::Clamp(Point.Z, -.5 * Shape.Dimensions.Y, .5 * Shape.Dimensions.Y))).Size() - Shape.Dimensions.X;
				else if (Shape.Type == FAnatomyShape::EType::Sphere) Phi = Point.Size() - Shape.Dimensions.X;
				else
				{
					const FVector Offset = Point.GetAbs() - Shape.Dimensions * .5;
					Phi = FVector(FMath::Max(Offset.X, 0.), FMath::Max(Offset.Y, 0.), FMath::Max(Offset.Z, 0.)).Size() + FMath::Min(Offset.GetMax(), 0.);
				}
				if (!TestTrue(TEXT("Finite reference anatomy signed distance"), FMath::IsFinite(Phi))) return false;
				if (Phi < NearestPhi) { NearestPhi = Phi; NearestBone = Shape.Bone; NearestType = Shape.Type; }
			}
			const bool bReferenceSkinProtected = NearestPhi <= Radius;
			if (bReferenceSkinProtected) Kinematic.Add(Index);
			const FString Line = FString::Printf(TEXT("ClothPivotProtection part=%s bone=%s nearestAnatomyBone=%s nearestShapeType=%d referencePhiCm=%.6f contactMarginCm=%.3f protected=%d kinematic=%d"), *Part, *Ref.GetBoneName(Index).ToString(), *NearestBone.ToString(), int32(NearestType), NearestPhi, Radius, bReferenceSkinProtected, Kinematic.Contains(Index));
			AddInfo(Line); Report += Line + TEXT("\n");
			int32 SegmentChild = INDEX_NONE;
			for (int32 Candidate : Ordered)
				if (Ref.GetParentIndex(Candidate) == Index && (Unit[Candidate].GetLocation() - Unit[Index].GetLocation()).SizeSquared() > SMALL_NUMBER) { SegmentChild = Candidate; break; }
			if (SegmentChild != INDEX_NONE)
			{
				// Read-only geometry evidence: compare the prospective single child capsule
				// with anatomy, including its contact radius. This does not alter protection.
				const FVector Start = Unit[Index].GetLocation(), End = Unit[SegmentChild].GetLocation();
				const FVector Midpoint = (Start + End) * .5, Direction = (End - Start).GetSafeNormal();
				const double CylinderHalfLength = FMath::Max(0., .5 * (End - Start).Size() - Radius);
				const FVector AxisStart = Midpoint - Direction * CylinderHalfLength, AxisEnd = Midpoint + Direction * CylinderHalfLength;
				double MinClearance = DBL_MAX; FName SegmentAnatomy = NAME_None; const TCHAR* Method = TEXT("None");
				for (const FAnatomyShape& Shape : AnatomyShapes)
				{
					const FVector A = Shape.UnitTransform.InverseTransformPosition(AxisStart), B = Shape.UnitTransform.InverseTransformPosition(AxisEnd);
					double MinPhi = 0.; const TCHAR* ShapeMethod = TEXT("None");
					if (Shape.Type == FAnatomyShape::EType::Capsule)
					{
						FVector ClosestCloth, ClosestAnatomy;
						FMath::SegmentDistToSegmentSafe(A, B, FVector(0., 0., -.5 * Shape.Dimensions.Y), FVector(0., 0., .5 * Shape.Dimensions.Y), ClosestCloth, ClosestAnatomy);
						MinPhi = (ClosestCloth - ClosestAnatomy).Size() - Shape.Dimensions.X;
						ShapeMethod = TEXT("ExactCapsuleAxisSegmentDistance");
					}
					else if (Shape.Type == FAnatomyShape::EType::Sphere)
					{
						const FVector Delta = B - A;
						const double Fraction = Delta.SizeSquared() > 0. ? FMath::Clamp(-FVector::DotProduct(A, Delta) / Delta.SizeSquared(), 0., 1.) : 0.;
						MinPhi = (A + Delta * Fraction).Size() - Shape.Dimensions.X;
						ShapeMethod = TEXT("ExactSphereClosestSegmentPoint");
					}
					else
					{
						// The signed box distance along a segment is convex. Ternary minimization
						// is numerical (not an exact claim), terminating at the engine's double
						// small-number distance tolerance; no gameplay tuning value is introduced.
						auto BoxPhi = [&](double Fraction)
						{
							const FVector Offset = (A + (B - A) * Fraction).GetAbs() - Shape.Dimensions * .5;
							return FVector(FMath::Max(Offset.X, 0.), FMath::Max(Offset.Y, 0.), FMath::Max(Offset.Z, 0.)).Size() + FMath::Min(Offset.GetMax(), 0.);
						};
						double Low = 0., High = 1.;
						while ((High - Low) * (B - A).Size() > UE_DOUBLE_SMALL_NUMBER)
						{
							const double Left = Low + (High - Low) / 3., Right = High - (High - Low) / 3.;
							if (BoxPhi(Left) <= BoxPhi(Right)) High = Right; else Low = Left;
						}
						MinPhi = FMath::Min3(BoxPhi(0.), BoxPhi(1.), BoxPhi(.5 * (Low + High)));
						ShapeMethod = TEXT("BoxConvexNumericTernaryDoubleSmallNumberCm");
					}
					const double Clearance = MinPhi - Radius;
					if (!TestTrue(TEXT("Finite reference child capsule clearance"), FMath::IsFinite(Clearance))) return false;
					if (Clearance < MinClearance) { MinClearance = Clearance; SegmentAnatomy = Shape.Bone; Method = ShapeMethod; }
				}
				const FString SegmentLine = FString::Printf(TEXT("ClothSegmentProtection part=%s bone=%s child=%s nearestAnatomyBone=%s minClearanceCm=%.6f contactRadiusCm=%.3f boneStart=%s boneEnd=%s capsuleAxisStart=%s capsuleAxisEnd=%s method=%s boxNumericToleranceCm=%.10f kinematic=%d policyChanged=0"), *Part, *Ref.GetBoneName(Index).ToString(), *Ref.GetBoneName(SegmentChild).ToString(), *SegmentAnatomy.ToString(), MinClearance, Radius, *Start.ToString(), *End.ToString(), *AxisStart.ToString(), *AxisEnd.ToString(), Method, double(UE_DOUBLE_SMALL_NUMBER), Kinematic.Contains(Index));
				AddInfo(SegmentLine); Report += SegmentLine + TEXT("\n");
			}
		}
		if (Part == TEXT("Leg") && !AdditionalProtectedAttachmentBonesLeg.IsEmpty())
		{
			TArray<FString> PinnedNames; AdditionalProtectedAttachmentBonesLeg.ParseIntoArray(PinnedNames, TEXT(","), true);
			for (FString Name : PinnedNames)
			{
				Name.TrimStartAndEndInline(); const int32 Index = Ref.FindBoneIndex(*Name);
				if (!TestTrue(TEXT("Observed stability pin is an existing Leg non-iron cloth bone"), Index != INDEX_NONE && Bones.Contains(Index) && !IsIron(Ref.GetBoneName(Index)))) return false;
				// Temporary runtime-observation stability pin; not metadata or ref-pose embedding.
				Kinematic.Add(Index);
				const FString Line = FString::Printf(TEXT("ClothObservedRuntimePin part=%s bone=%s source=ObservedRuntimeJointFlip temporaryStabilityPin=1"), *Part, *Ref.GetBoneName(Index).ToString());
				AddInfo(Line); Report += Line + TEXT("\n");
			}
		}
		// UE CalcBoneVertInfos uses this same inverse-ref transform for bone-space fitting.
		// Imported vertex positions already include the wrapper; inverse-ref removes it.
		// Do not divide these local geometry positions by WrapperScale again.
		Mesh->CalculateInvRefMatrices();
		const TArray<FMatrix44f>& InverseRef = Mesh->GetRefBasesInvMatrix();
		const FSkeletalMeshModel* Model = Mesh->GetImportedModel();
		if (!TestTrue(TEXT("Imported cloth LOD and inverse reference matrices available"), Model && !Model->LODModels.IsEmpty() && InverseRef.Num() >= Ref.GetRawBoneNum())) return false;
		struct FWeightedPoint { FVector Position; double Weight; };
		TMap<int32, TArray<FWeightedPoint>> Points, DominantPoints;
		double RoundTripError = 0.;
		for (const FSkelMeshSection& Section : Model->LODModels[0].Sections)
			for (const FSoftSkinVertex& Vertex : Section.SoftVertices)
				for (int32 Influence = 0; Influence < UE_ARRAY_COUNT(Vertex.InfluenceBones); ++Influence)
				{
					if (Vertex.InfluenceWeights[Influence] == 0 || !Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[Influence])) continue;
					const int32 Bone = Section.BoneMap[Vertex.InfluenceBones[Influence]];
					if (!Bones.Contains(Bone)) continue;
					const FVector3f Local = InverseRef[Bone].TransformPosition(Vertex.Position);
					if (!TestTrue(TEXT("Finite bone-local weighted vertex"), !Local.ContainsNaN())) return false;
					Points.FindOrAdd(Bone).Add({FVector(Local), double(Vertex.InfluenceWeights[Influence])});
					// Dominance is the largest actual skin weight, without a tuning threshold.
					// Equal weights retain the first valid imported influence slot/bone name.
					bool bDominant = true;
					for (int32 Other = 0; Other < UE_ARRAY_COUNT(Vertex.InfluenceBones); ++Other)
						if (Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[Other]) && (Vertex.InfluenceWeights[Other] > Vertex.InfluenceWeights[Influence] || (Vertex.InfluenceWeights[Other] == Vertex.InfluenceWeights[Influence] && Other < Influence))) { bDominant = false; break; }
					if (bDominant) DominantPoints.FindOrAdd(Bone).Add({FVector(Local), double(Vertex.InfluenceWeights[Influence])});
					RoundTripError = FMath::Max(RoundTripError, double((InverseRef[Bone].Inverse().TransformPosition(Local) - Vertex.Position).Size()) / WrapperScale);
				}
		TArray<int32> Depth, Remaining; Depth.Init(0, Ref.GetNum()); Remaining.Init(0, Ref.GetNum());
		auto IsSimulated = [&](int32 Index) { return Bones.Contains(Index) && !Kinematic.Contains(Index) && !IsIron(Ref.GetBoneName(Index)); };
		for (int32 Index : Ordered)
			if (IsSimulated(Index)) { const int32 Parent = Ref.GetParentIndex(Index); Depth[Index] = IsSimulated(Parent) ? Depth[Parent] + 1 : 0; }
		for (int32 Position = Ordered.Num() - 1; Position >= 0; --Position)
		{
			const int32 Index = Ordered[Position], Parent = Ref.GetParentIndex(Index);
			if (IsSimulated(Index) && IsSimulated(Parent)) Remaining[Parent] = FMath::Max(Remaining[Parent], Remaining[Index] + 1);
		}
		PA->Modify();
		// Preserve all non-cloth kinematic setups and the existing iron dynamics exactly.
		PA->SkeletalBodySetups.RemoveAll([&](const USkeletalBodySetup* Body) { return IsCloth(Body->BoneName) && !IsIron(Body->BoneName); });
		PA->ConstraintSetup.RemoveAll([&](const UPhysicsConstraintTemplate* Joint) { return IsCloth(Joint->DefaultInstance.ConstraintBone1) && !IsIron(Joint->DefaultInstance.ConstraintBone1); });
		PA->CollisionDisableTable.Reset(); PA->UpdateBodySetupIndexMap();
		int32 Simulated = 0, Anchors = 0, PreservedIron = 0; double TotalMass = 0.;
		for (int32 Index : Ordered)
		{
			const FName BoneName = Ref.GetBoneName(Index);
			if (IsIron(BoneName))
			{
				if (!TestTrue(TEXT("Existing iron body preserved"), PA->FindBodyIndex(BoneName) != INDEX_NONE)) return false;
				++PreservedIron; continue;
			}
			USkeletalBodySetup* Body = NewObject<USkeletalBodySetup>(PA, NAME_None, RF_Transactional);
			Body->BoneName = BoneName; Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
			if (Kinematic.Contains(Index))
			{
				Body->PhysicsType = PhysType_Kinematic; Body->CollisionReponse = EBodyCollisionResponse::BodyCollision_Disabled;
				FKSphereElem Anchor; Anchor.Radius = Radius; Anchor.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Body->AggGeom.SphereElems.Add(Anchor);
				Body->InvalidatePhysicsData(); PA->SkeletalBodySetups.Add(Body); PA->UpdateBodySetupIndexMap(); ++Anchors;
				const FString Line = FString::Printf(TEXT("ClothAnchor part=%s bone=%s parent=%s weightedVertices=%d localLengthCm=%.6f toleranceCm=%.3f"), *Part, *BoneName.ToString(), *Ref.GetBoneName(Ref.GetParentIndex(Index)).ToString(), Counts.FindRef(Index), Ref.GetRefBonePose()[Index].GetTranslation().Size(), AnchorTolerance);
				AddInfo(Line); Report += Line + TEXT("\n"); continue;
			}
			++Simulated;
			const int32 Extent = Depth[Index] + Remaining[Index];
			const float Fraction = Extent > 0 ? float(Depth[Index]) / float(Extent) : 0.f;
			int32 Child = INDEX_NONE;
			FVector Segment = FVector::ZeroVector, Center = FVector::ZeroVector;
			for (int32 Candidate : Ordered)
				if (Ref.GetParentIndex(Candidate) == Index)
				{
					const FVector Measured = Unit[Index].InverseTransformPosition(Unit[Candidate].GetLocation());
					if (Measured.SizeSquared() > SMALL_NUMBER) { Child = Candidate; Segment = Measured; break; }
				}
			float Length = float(Segment.Size());
			double ProjectionMin = 0., ProjectionMax = Length, RawProjectionMin = 0.; bool bTerminalTrimmed = false;
			if (Child != INDEX_NONE) Center = Segment * .5;
			else
			{
				// A terminal capsule follows actual positive-weight mesh extent, not a guessed
				// repeat of the previous segment. The parent segment supplies direction only.
				const FVector Direction = Unit[Index].InverseTransformVector(Unit[Index].GetLocation() - Unit[Ref.GetParentIndex(Index)].GetLocation()).GetSafeNormal();
				const TArray<FWeightedPoint>* PositiveCloud = Points.Find(Index), *DominantCloud = DominantPoints.Find(Index);
				if (!TestTrue(TEXT("Weighted cloth tip cloud and measured direction available"), PositiveCloud && !PositiveCloud->IsEmpty() && !Direction.IsNearlyZero())) return false;
				const bool bUsingDominant = bUseDominantTerminalSupport && DominantCloud && !DominantCloud->IsEmpty();
				const TArray<FWeightedPoint>* Cloud = bUsingDominant ? DominantCloud : PositiveCloud;
				double AllPositiveMin = DBL_MAX, AllPositiveMax = -DBL_MAX;
				for (const FWeightedPoint& Point : *PositiveCloud)
				{
					const double Projection = FVector::DotProduct(Point.Position, Direction);
					AllPositiveMin = FMath::Min(AllPositiveMin, Projection); AllPositiveMax = FMath::Max(AllPositiveMax, Projection);
				}
				const FString SupportLine = FString::Printf(TEXT("ClothTerminalSupport part=%s bone=%s useDominantPolicy=%d geometrySource=%s dominantOwnedVertices=%d allPositiveVertices=%d allPositiveProjectionMinCm=%.6f allPositiveProjectionMaxCm=%.6f tiePolicy=FirstValidImportedInfluenceSlot"), *Part, *BoneName.ToString(), bUseDominantTerminalSupport, bUsingDominant ? TEXT("DominantSkinWeightVertices") : bUseDominantTerminalSupport ? TEXT("AllPositiveFallbackNoDominantVertices") : TEXT("AllPositiveSkinWeightVertices"), DominantCloud ? DominantCloud->Num() : 0, PositiveCloud->Num(), AllPositiveMin, AllPositiveMax);
				AddInfo(SupportLine); Report += SupportLine + TEXT("\n");
				ProjectionMin = DBL_MAX; ProjectionMax = -DBL_MAX;
				for (const FWeightedPoint& Point : *Cloud)
				{
					const double Projection = FVector::DotProduct(Point.Position, Direction);
					ProjectionMin = FMath::Min(ProjectionMin, Projection); ProjectionMax = FMath::Max(ProjectionMax, Projection);
				}
				RawProjectionMin = ProjectionMin;
				// Positive-weight support behind a terminal pivot is shared with its
				// parent. The explicit temporary policy avoids a backwards contact capsule.
				if (bTrimTerminalBackwardsOverlap) ProjectionMin = FMath::Max(0., ProjectionMin);
				bTerminalTrimmed = ProjectionMin != RawProjectionMin;
				if (!TestTrue(TEXT("Positive measured terminal extent after overlap trim"), ProjectionMax > ProjectionMin))
				{
					AddError(FString::Printf(TEXT("ClothTerminalExtentInvalid part=%s bone=%s rawProjectionMinCm=%.6f projectionMinCm=%.6f projectionMaxCm=%.6f trimEnabled=%d"), *Part, *BoneName.ToString(), RawProjectionMin, ProjectionMin, ProjectionMax, bTrimTerminalBackwardsOverlap));
					return false;
				}
				FVector WeightedCenter = FVector::ZeroVector; double WeightSum = 0.;
				for (const FWeightedPoint& Point : *Cloud)
				{
					if (bTrimTerminalBackwardsOverlap && FVector::DotProduct(Point.Position, Direction) < ProjectionMin) continue;
					WeightedCenter += Point.Position * Point.Weight; WeightSum += Point.Weight;
				}
				if (!TestTrue(TEXT("Positive weighted terminal support after overlap trim"), FMath::IsFinite(WeightSum) && WeightSum > 0.)) return false;
				WeightedCenter /= WeightSum;
				Length = float(ProjectionMax - ProjectionMin); Segment = Direction * Length;
				Center = WeightedCenter - Direction * FVector::DotProduct(WeightedCenter, Direction) + Direction * (.5 * (ProjectionMin + ProjectionMax));
			}
			if (!TestTrue(TEXT("Finite positive measured cloth geometry"), FMath::IsFinite(Length) && Length > 0.f && !Center.ContainsNaN() && !Segment.ContainsNaN())) return false;
			Body->PhysicsType = PhysType_Simulated; Body->CollisionReponse = EBodyCollisionResponse::BodyCollision_Enabled;
			Body->DefaultInstance.LinearDamping = LinearDamping; Body->DefaultInstance.AngularDamping = FMath::Lerp(RootDamping, TipDamping, Fraction);
			Body->DefaultInstance.SetMassOverride(Density * Length, true); Body->DefaultInstance.InertiaTensorScale = FVector::OneVector;
			bool bStripBox = false;
			if (Part == TEXT("Leg"))
			{
				// Temporary measured-coverage policy. Geometry stays in actual bone-local cm;
				// principal transverse support comes from dominant-owned imported vertices.
				// Keep the existing longitudinal fit, connectors and mass-per-length contract.
				const TArray<FWeightedPoint>* Cloud = DominantPoints.Find(Index);
				const FVector Direction = Segment.GetSafeNormal();
				FVector Lateral = FVector::ZeroVector, Normal = FVector::ZeroVector, StripCenter = Center;
				double Width = 0., WeightSum = 0., MeanNormal = 0., CovUU = 0., CovUV = 0., CovVV = 0.;
				double StripLength = Length, StripThickness = 2. * Radius;
				double MinX = 0., MaxX = 0., MinY = 0., MaxY = 0., MinZ = 0., MaxZ = 0.;
				if (Cloud && !Cloud->IsEmpty())
				{
					FVector U, V; Direction.FindBestAxisVectors(U, V);
					FVector Mean = FVector::ZeroVector;
					for (const FWeightedPoint& Point : *Cloud) { Mean += Point.Position * Point.Weight; WeightSum += Point.Weight; }
					if (!TestTrue(TEXT("Positive finite dominant strip support weight"), FMath::IsFinite(WeightSum) && WeightSum > 0.)) return false;
					Mean /= WeightSum;
					for (const FWeightedPoint& Point : *Cloud)
					{
						const FVector Offset = Point.Position - Mean;
						const double PU = FVector::DotProduct(Offset, U), PV = FVector::DotProduct(Offset, V);
						CovUU += Point.Weight * PU * PU; CovUV += Point.Weight * PU * PV; CovVV += Point.Weight * PV * PV;
					}
					CovUU /= WeightSum; CovUV /= WeightSum; CovVV /= WeightSum;
					if (!TestTrue(TEXT("Finite transverse dominant strip covariance"), FMath::IsFinite(CovUU) && FMath::IsFinite(CovUV) && FMath::IsFinite(CovVV))) return false;
					const double Angle = .5 * FMath::Atan2(2. * CovUV, CovUU - CovVV);
					Lateral = (U * FMath::Cos(Angle) + V * FMath::Sin(Angle)).GetSafeNormal();
					Normal = FVector::CrossProduct(Direction, Lateral).GetSafeNormal();
					MinX = MinY = MinZ = DBL_MAX; MaxX = MaxY = MaxZ = -DBL_MAX;
					for (const FWeightedPoint& Point : *Cloud)
					{
						const double PX = FVector::DotProduct(Point.Position, Direction), PY = FVector::DotProduct(Point.Position, Lateral), PZ = FVector::DotProduct(Point.Position, Normal);
						MinX = FMath::Min(MinX, PX); MaxX = FMath::Max(MaxX, PX);
						MinY = FMath::Min(MinY, PY); MaxY = FMath::Max(MaxY, PY);
						MinZ = FMath::Min(MinZ, PZ); MaxZ = FMath::Max(MaxZ, PZ);
					}
					Width = MaxY - MinY; MeanNormal = FVector::DotProduct(Mean, Normal);
					StripCenter = Direction * FVector::DotProduct(Center, Direction) + Lateral * (.5 * (MinY + MaxY)) + Normal * MeanNormal;
					if (!TestTrue(TEXT("Finite measured dominant strip fit"), FMath::IsFinite(Width) && Width >= 0. && !StripCenter.ContainsNaN() && !Lateral.IsNearlyZero() && !Normal.IsNearlyZero())) return false;
					if (bUseDominantClothStripBoxesLeg && Width > 2. * Radius)
					{
						if (bUseFullDominantClothStripBoundsLeg)
						{
							// Imported dominant support bounds; no new feel/contact tuning value.
							// Keep original segment length for mass and joint connectors.
							StripLength = FMath::Max(2. * Radius, MaxX - MinX); StripThickness = FMath::Max(2. * Radius, MaxZ - MinZ);
							StripCenter = Direction * (.5 * (MinX + MaxX)) + Lateral * (.5 * (MinY + MaxY)) + Normal * (.5 * (MinZ + MaxZ));
						}
						FKBoxElem Box; Box.X = float(StripLength); Box.Y = float(Width); Box.Z = float(StripThickness); Box.Center = StripCenter;
						Box.Rotation = FRotationMatrix::MakeFromXY(Direction, Lateral).Rotator(); Box.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
						Body->AggGeom.BoxElems.Add(Box); Center = StripCenter; bStripBox = true;
					}
				}
				const FString Line = FString::Printf(TEXT("ClothStripSupport part=%s bone=%s useDominantStripPolicy=%d useFullDominantBoundsPolicy=%d fullDominantBoundsApplied=%d shape=%s fallback=%s source=DominantSkinWeightVerticesBoneLocalCm supportCount=%d supportWeight=%.0f lengthCm=%.6f boxLengthCm=%.6f widthCm=%.6f thicknessCm=%.6f rawProjectionXMinMaxCm=%.6f/%.6f rawLateralYMinMaxCm=%.6f/%.6f rawNormalZMinMaxCm=%.6f/%.6f weightedNormalMeanCm=%.6f transverseCovarianceCm2=%.6f/%.6f/%.6f axisX=%s axisY=%s axisZ=%s proposedBoxCenter=%s actualCenter=%s"), *Part, *BoneName.ToString(), bUseDominantClothStripBoxesLeg, bUseFullDominantClothStripBoundsLeg, bStripBox && bUseFullDominantClothStripBoundsLeg, bStripBox ? TEXT("Box") : TEXT("Capsule"), bStripBox ? TEXT("None") : !bUseDominantClothStripBoxesLeg ? TEXT("DisabledByPolicy") : !Cloud || Cloud->IsEmpty() ? TEXT("NoDominantSupport") : TEXT("DominantWidthAtMostDiameter"), Cloud ? Cloud->Num() : 0, WeightSum, Length, StripLength, Width, StripThickness, MinX, MaxX, MinY, MaxY, MinZ, MaxZ, MeanNormal, CovUU, CovUV, CovVV, *Direction.ToString(), *Lateral.ToString(), *Normal.ToString(), *StripCenter.ToString(), *Center.ToString());
				AddInfo(Line); Report += Line + TEXT("\n");
			}
			if (!bStripBox)
			{
				FKSphylElem Capsule; Capsule.Radius = Radius; Capsule.Length = FMath::Max(0.f, Length - 2.f * Radius); Capsule.Center = Center;
				Capsule.Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Segment.GetSafeNormal()).Rotator(); Capsule.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
				Body->AggGeom.SphylElems.Add(Capsule);
			}
			Body->InvalidatePhysicsData(); PA->SkeletalBodySetups.Add(Body); PA->UpdateBodySetupIndexMap(); TotalMass += Density * Length;
			int32 Parent = Ref.GetParentIndex(Index);
			while (Parent >= 0 && PA->FindBodyIndex(Ref.GetBoneName(Parent)) == INDEX_NONE) Parent = Ref.GetParentIndex(Parent);
			if (!TestTrue(TEXT("Existing/new cloth parent body resolved"), Parent >= 0)) return false;
			UPhysicsConstraintTemplate* Joint = NewObject<UPhysicsConstraintTemplate>(PA, NAME_None, RF_Transactional);
			FConstraintInstance& C = Joint->DefaultInstance;
			C.JointName = BoneName; C.ConstraintBone1 = BoneName; C.ConstraintBone2 = Ref.GetBoneName(Parent);
			C.SetRefFrame(EConstraintFrame::Frame1, FTransform::Identity);
			FTransform ParentFrame = Unit[Index].GetRelativeTransform(Unit[Parent]); ParentFrame.SetTranslation(ParentFrame.GetTranslation() / WrapperScale);
			C.SetRefFrame(EConstraintFrame::Frame2, ParentFrame);
			C.SetLinearXMotion(LCM_Locked); C.SetLinearYMotion(LCM_Locked); C.SetLinearZMotion(LCM_Locked);
			// Assistant temporary root-clearance exception, NOT original-game metadata.
			// Only the first simulated Leg joints receive it; downstream limits retain the existing fit.
			const bool bLegRootClearanceOverride = Part == TEXT("Leg") && Depth[Index] == 0;
			const float Swing = bLegRootClearanceOverride ? RootSwingDegreesLeg : FMath::Lerp(RootSwing, TipSwing, Fraction);
			const float Twist = FMath::Lerp(RootTwist, TipTwist, Fraction), Omega = FMath::Lerp(RootOmega, TipOmega, Fraction);
			C.SetAngularSwing1Limit(ACM_Limited, Swing); C.SetAngularSwing2Limit(ACM_Limited, Swing); C.SetAngularTwistLimit(ACM_Limited, Twist); C.SetDisableCollision(true);
			// Explicit assistant-selected limit policy; SLERP remains the soft restoring drive.
			C.ProfileInstance.ConeLimit.bSoftConstraint = !bHardAngularLimits;
			C.ProfileInstance.TwistLimit.bSoftConstraint = !bHardAngularLimits;
			C.SetParentDominates(bParentDominates);
			C.ProfileInstance.ProjectionAngularAlpha = ProjectionAngularAlpha;
			C.SetAngularDriveMode(EAngularDriveMode::SLERP); C.SetOrientationDriveSLERP(true); C.SetAngularVelocityDriveSLERP(true);
			C.SetAngularOrientationTarget(FQuat::Identity); C.SetAngularVelocityTarget(FVector::ZeroVector);
			C.SetAngularDriveAccelerationMode(true); C.SetAngularDriveParams(Omega * Omega, 2.f * Omega, 0.f);
			Joint->SetDefaultProfile(C); PA->ConstraintSetup.Add(Joint);
			const FString Line = FString::Printf(TEXT("ClothRefined part=%s bone=%s parent=%s weightedVertices=%d depth=%d downstream=%d fraction=%.4f child=%s lengthCm=%.6f center=%s projectionMinCm=%.6f projectionMaxCm=%.6f rawProjectionMinCm=%.6f terminalBackwardTrimEnabled=%d terminalBackwardTrimApplied=%d massKg=%.6f radiusCm=%.3f swingDeg=%.3f legRootClearanceOverride=%d twistDeg=%.3f hardAngularLimits=%d parentDominates=%d projectionAngularAlpha=%.6f omegaPerSecond=%.6f spring=%.6f driveDamping=%.6f angularDamping=%.6f connector2=%s"), *Part, *BoneName.ToString(), *C.ConstraintBone2.ToString(), Counts.FindRef(Index), Depth[Index], Remaining[Index], Fraction, Child != INDEX_NONE ? *Ref.GetBoneName(Child).ToString() : TEXT("WeightedVertexExtent"), Length, *Center.ToString(), ProjectionMin, ProjectionMax, RawProjectionMin, bTrimTerminalBackwardsOverlap, bTerminalTrimmed, Density * Length, Radius, Swing, bLegRootClearanceOverride, Twist, bHardAngularLimits, bParentDominates, ProjectionAngularAlpha, Omega, Omega * Omega, 2.f * Omega, Body->DefaultInstance.AngularDamping, *C.Pos2.ToString());
			AddInfo(Line); Report += Line + TEXT("\n");
		}
		PA->UpdateBodySetupIndexMap(); PA->UpdateBoundsBodiesArray();
		auto* Probe = NewObject<USkeletalMeshComponent>(); Probe->SetSkeletalMesh(Mesh);
		TArray<FBodyInstance*> Bodies; Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, Bodies);
		bool bInertiaValid = true;
		struct FInertiaExpectation { double Mass, Target; FVector ThinPrincipal, CoMLocation; };
		TMap<FName, FInertiaExpectation> InertiaExpected;
		for (USkeletalBodySetup* Body : PA->SkeletalBodySetups)
		{
			if (Body->PhysicsType != PhysType_Simulated || IsIron(Body->BoneName)) continue;
			const auto Thin = ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(Body->BoneName)], FTransform::Identity);
			const FVector ThinPrincipal(Thin.Inertia);
			const double FloorMultiplier = bRotationInvariantInertiaConditioning && Part == TEXT("Leg") ? UniformPrincipalInertiaFloorMultiplierLeg : 1.;
			const double Target = ThinPrincipal.GetMax() * FloorMultiplier;
			if (!TestTrue(TEXT("Finite positive cloth mass and principal inertia"), FMath::IsFinite(double(Thin.Mass)) && Thin.Mass > 0. && !ThinPrincipal.ContainsNaN() && ThinPrincipal.GetMin() > 0.)) { bInertiaValid = false; break; }
			InertiaExpected.Add(Body->BoneName, {double(Thin.Mass), Target, ThinPrincipal, Thin.CoMTransform.GetLocation()});
			if (bRotationInvariantInertiaConditioning)
			{
				// Temporary minimum-principal-moment floor, NOT isotropic inertia or game metadata.
				// BodyUtils rotates to body axes before ScaleInertia. Uniform S multiplies the
				// ENTIRE tensor by S^5 when ImmediatePhysics bInertaScaleIncludeMass=true;
				// thus every eigenvalue scales equally; the temporary Leg multiplier scales
				// the minimum floor relative to thin maximum without changing mass or shape.
				Body->DefaultInstance.InertiaTensorScale = FVector(FMath::Pow(Target / ThinPrincipal.GetMin(), 1. / 5.));
			}
			else
			{
				// Retained legacy body-axis diagonal conditioning: off-diagonal terms remain,
				// so this branch does not guarantee an isotropic tensor/principal-moment floor.
				FVector Diagonal;
				for (int32 Axis = 0; Axis < 3; ++Axis)
				{
					FVector Basis = FVector::ZeroVector; Basis[Axis] = 1.;
					Diagonal[Axis] = Thin.CoMTransform.GetRotation().RotateVector(ThinPrincipal * Thin.CoMTransform.GetRotation().UnrotateVector(Basis))[Axis];
				}
				const FVector SecondMoment = FVector(.5 * (Diagonal.X + Diagonal.Y + Diagonal.Z)) - Diagonal;
				if (!TestTrue(TEXT("Finite positive cloth equivalent second moment"), !SecondMoment.ContainsNaN() && SecondMoment.GetMin() > 0.)) { bInertiaValid = false; break; }
				const FVector Q = FVector(.5 * Target) / SecondMoment;
				const double Determinant = FMath::Pow(Q.X * Q.Y * Q.Z, 1. / 5.);
				Body->DefaultInstance.InertiaTensorScale = FVector(FMath::Sqrt(Q.X / Determinant), FMath::Sqrt(Q.Y / Determinant), FMath::Sqrt(Q.Z / Determinant));
			}
			bInertiaValid &= TestTrue(TEXT("Finite positive cloth inertia conditioning"), !Body->DefaultInstance.InertiaTensorScale.ContainsNaN() && Body->DefaultInstance.InertiaTensorScale.GetMin() > 0.);
			const FString Line = FString::Printf(TEXT("ClothInertia part=%s bone=%s thinPrincipalKgCm2=%s targetMomentKgCm2=%.8f rotationInvariantPrincipalFloor=%d uniformPrincipalFloorMultiplier=%.6f inertiaScale=%s"), *Part, *Body->BoneName.ToString(), *ThinPrincipal.ToString(), Target, bRotationInvariantInertiaConditioning, FloorMultiplier, *Body->DefaultInstance.InertiaTensorScale.ToString());
			AddInfo(Line); Report += Line + TEXT("\n");
		}
		for (FBodyInstance* Body : Bodies) { if (Body->IsValidBodyInstance()) Body->TermBody(true); delete Body; }
		Bodies.Reset(); if (!bInertiaValid) return false;
		// Fresh instances consume the final stored scale. Readback verifies the actual
		// engine principal moments and mass, rather than repeating the author equation.
		Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, Bodies);
		for (const auto& Pair : InertiaExpected)
		{
			const auto Final = ImmediatePhysics::MakeDynamicActorSetup(Bodies[PA->FindBodyIndex(Pair.Key)], FTransform::Identity);
			const FVector Principal(Final.Inertia);
			const double MassError = double(Final.Mass) / Pair.Value.Mass - 1., MinimumError = Principal.GetMin() / Pair.Value.Target - 1.;
			bInertiaValid &= TestTrue(TEXT("Fresh final cloth principal moments remain finite and positive"), !Principal.ContainsNaN() && Principal.GetMin() > 0.);
			bInertiaValid &= TestTrue(TEXT("Fresh final cloth mass retained (relative)"), FMath::IsFinite(MassError) && FMath::Abs(MassError) < .001);
			bInertiaValid &= TestTrue(TEXT("Fresh final cloth center of mass retained (cm)"), Final.CoMTransform.GetLocation().Equals(Pair.Value.CoMLocation, .001));
			if (bRotationInvariantInertiaConditioning) bInertiaValid &= TestTrue(TEXT("Fresh final minimum principal inertia matches configured measured target (relative)"), FMath::IsFinite(MinimumError) && FMath::Abs(MinimumError) < .001);
			const FString Line = FString::Printf(TEXT("ClothInertiaFinal part=%s bone=%s rotationInvariantPrincipalFloor=%d thinPrincipalKgCm2=%s targetMinimumPrincipalKgCm2=%.8f actualPrincipalKgCm2=%.8f/%.8f/%.8f actualMinimumPrincipalKgCm2=%.8f actualMassKg=%.9f massRelativeError=%.9g minimumPrincipalRelativeError=%.9g actualCoM=%s"), *Part, *Pair.Key.ToString(), bRotationInvariantInertiaConditioning, *Pair.Value.ThinPrincipal.ToString(), Pair.Value.Target, Principal.X, Principal.Y, Principal.Z, Principal.GetMin(), double(Final.Mass), MassError, MinimumError, *Final.CoMTransform.GetLocation().ToString());
			AddInfo(Line); Report += Line + TEXT("\n");
		}
		for (FBodyInstance* Body : Bodies) { if (Body->IsValidBodyInstance()) Body->TermBody(true); delete Body; }
		Bodies.Reset(); if (!bInertiaValid) return false;
		for (int32 A = 0; A < PA->SkeletalBodySetups.Num(); ++A)
			for (int32 B = A + 1; B < PA->SkeletalBodySetups.Num(); ++B) PA->DisableCollision(A, B);
		PA->RefreshPhysicsAssetChange();
		const FString Summary = FString::Printf(TEXT("ClothRefinement part=%s bodies=%d refinedSimulated=%d newAnchors=%d preservedIron=%d totalRefinedMassKg=%.6f inverseRefRoundTripErrorCm=%.8f"), *Part, PA->SkeletalBodySetups.Num(), Simulated, Anchors, PreservedIron, TotalMass, RoundTripError);
		AddInfo(Summary); Report += Summary + TEXT("\n");
		if (!Save(PA)) return false;
	}
	return FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir() / TEXT("PlayerClothRefinement.txt")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerLeftShoulderSpring, "Khazan.PlayerParts.LeftShoulderSpring", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerLeftShoulderSpring::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor;
	if (!IsWork()) return false;
	// Assistant-selected temporary current-asset-relative tuning, NOT original-game metadata.
	// Only existing left-cape SLERP stiffness/damping and cone swing limits may change.
	FConfigFile Settings; Settings.Read(FPaths::ProjectSavedDir() / TEXT("LeftShoulderCloth.ini"));
	bool bApply = false; float SpringScale = 0.f;
	if (!TestTrue(TEXT("Explicit left-shoulder apply/read-only mode"), Settings.GetBool(TEXT("LeftShoulderCloth"), TEXT("Apply"), bApply)) ||
		!TestTrue(TEXT("Explicit finite positive spring scale"), Settings.GetFloat(TEXT("LeftShoulderCloth"), TEXT("SpringScale"), SpringScale) && FMath::IsFinite(SpringScale) && SpringScale > 0.f && SpringScale <= 1.f)) return false;
	const FConfigSection* Baseline = Settings.FindSection(TEXT("Baseline"));
	if (!TestTrue(TEXT("Exactly eight left-cape baseline keys"), Baseline && Baseline->Num() == 8)) return false;
	UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(TEXT("Torso")) + TEXT("_RigidBody_PhysicsAsset")));
	if (!TestNotNull(TEXT("Existing Torso derived PhysicsAsset"), PA)) return false;
	TSet<FName> TargetBones;
	for (const USkeletalBodySetup* Body : PA->SkeletalBodySetups)
		if (Body->PhysicsType == PhysType_Simulated && Body->BoneName.ToString().StartsWith(TEXT("B_Cape_")) && Body->BoneName.ToString().EndsWith(TEXT("_L_Armor001"))) TargetBones.Add(Body->BoneName);
	if (!TestEqual(TEXT("Exactly eight simulated left-cape bodies"), TargetBones.Num(), 8)) return false;
	for (const TCHAR* SectionName : {TEXT("BaselineDamping"), TEXT("BaselineSwing1"), TEXT("BaselineSwing2"), TEXT("SpringScales"), TEXT("DampingScales"), TEXT("SwingScales")})
		if (const FConfigSection* Section = Settings.FindSection(SectionName))
			for (const auto& Pair : *Section)
				if (!TestTrue(TEXT("Optional tuning keys name only targeted left-cape bones"), TargetBones.Contains(Pair.Key))) return false;
	TArray<UPhysicsConstraintTemplate*> Targets; TMap<FName, FVector4f> BaselineFields; TMap<FName, FVector3f> BoneScales; TSet<FName> Seen;
	bool bAllBaseline = true, bAllAdjusted = true;
	UScriptStruct* ProfileStruct = FConstraintProfileProperties::StaticStruct();
	for (UPhysicsConstraintTemplate* Joint : PA->ConstraintSetup)
	{
		const FConstraintInstance& C = Joint->DefaultInstance;
		if (!TargetBones.Contains(C.ConstraintBone1)) continue;
		const FString Bone = C.ConstraintBone1.ToString();
		FVector3f Scales(SpringScale, 1.f, 1.f);
		Settings.GetFloat(TEXT("SpringScales"), *Bone, Scales.X); Settings.GetFloat(TEXT("DampingScales"), *Bone, Scales.Y); Settings.GetFloat(TEXT("SwingScales"), *Bone, Scales.Z);
		if (!TestTrue(TEXT("Finite positive per-bone scales; spring and damping do not increase"), !Scales.ContainsNaN() && Scales.X > 0.f && Scales.X <= 1.f && Scales.Y > 0.f && Scales.Y <= 1.f && Scales.Z > 0.f && FMath::IsFinite(Scales.Z))) return false;
		FVector4f Expected(0.f, C.ProfileInstance.AngularDrive.SlerpDrive.Damping, C.GetAngularSwing1Limit(), C.GetAngularSwing2Limit());
		const bool bDampingBaseline = Settings.GetFloat(TEXT("BaselineDamping"), *Bone, Expected.Y);
		const bool bSwing1Baseline = Settings.GetFloat(TEXT("BaselineSwing1"), *Bone, Expected.Z), bSwing2Baseline = Settings.GetFloat(TEXT("BaselineSwing2"), *Bone, Expected.W);
		if (!TestTrue(TEXT("Unique joint with explicit spring baseline and explicit baselines for changed damping/swing"), !Seen.Contains(C.ConstraintBone1) && Settings.GetFloat(TEXT("Baseline"), *Bone, Expected.X) && (Scales.Y == 1.f || bDampingBaseline) && (Scales.Z == 1.f || (bSwing1Baseline && bSwing2Baseline)) && !Expected.ContainsNaN() && Expected.X > 0.f && Expected.Y > 0.f && Expected.Z > 0.f && Expected.W > 0.f && Expected.Z * Scales.Z <= 180.f && Expected.W * Scales.Z <= 180.f)) return false;
		const FConstraintProfileProperties& Default = Joint->GetConstraintProfilePropertiesOrDefault(NAME_None);
		if (!TestTrue(TEXT("Current and saved default profiles agree before any change"), ProfileStruct->CompareScriptStruct(&C.ProfileInstance, &Default, 0)) ||
			!TestTrue(TEXT("Existing active acceleration SLERP drive"), C.ProfileInstance.AngularDrive.AngularDriveMode == EAngularDriveMode::SLERP && C.ProfileInstance.AngularDrive.bAccelerationMode && C.ProfileInstance.AngularDrive.SlerpDrive.bEnablePositionDrive && C.ProfileInstance.AngularDrive.SlerpDrive.bEnableVelocityDrive)) return false;
		const FVector4f Actual(C.ProfileInstance.AngularDrive.SlerpDrive.Stiffness, C.ProfileInstance.AngularDrive.SlerpDrive.Damping, C.GetAngularSwing1Limit(), C.GetAngularSwing2Limit());
		bAllBaseline &= Actual == Expected; bAllAdjusted &= Actual == FVector4f(Expected.X * Scales.X, Expected.Y * Scales.Y, Expected.Z * Scales.Z, Expected.W * Scales.Z);
		Seen.Add(C.ConstraintBone1); BaselineFields.Add(C.ConstraintBone1, Expected); BoneScales.Add(C.ConstraintBone1, Scales); Targets.Add(Joint);
	}
	if (!TestEqual(TEXT("Exactly eight distinct targeted joints"), Targets.Num(), 8) ||
		!TestTrue(TEXT("All targeted fields match the exact baseline before applying; read-only also accepts the exact complete candidate"), bApply ? bAllBaseline : bAllBaseline || bAllAdjusted)) return false;
	bool bSnapshotsValid = true;
	auto Snapshot = [&](const UObject* Object) { auto Json = MakeShared<FJsonObject>(); bSnapshotsValid &= FJsonObjectConverter::UStructToJsonObject(Object->GetClass(), Object, Json); return Json; };
	auto SameJson = [](const TSharedPtr<FJsonObject>& A, const TSharedPtr<FJsonObject>& B) { return FJsonValue::CompareEqual(FJsonValueObject(A), FJsonValueObject(B)); };
	TArray<TSharedPtr<FJsonObject>> BeforeBodies, BeforeJoints; TArray<FConstraintProfileProperties> BeforeDefaults;
	for (const USkeletalBodySetup* Body : PA->SkeletalBodySetups) BeforeBodies.Add(Snapshot(Body));
	for (const UPhysicsConstraintTemplate* Joint : PA->ConstraintSetup) { BeforeJoints.Add(Snapshot(Joint)); BeforeDefaults.Add(Joint->GetConstraintProfilePropertiesOrDefault(NAME_None)); }
	const auto BeforePA = Snapshot(PA); if (!TestTrue(TEXT("Full reflected baseline snapshots exported"), bSnapshotsValid)) return false;
	auto Report = MakeShared<FJsonObject>();
	Report->SetStringField(TEXT("asset"), PA->GetPathName()); Report->SetBoolField(TEXT("apply_requested"), bApply);
	Report->SetNumberField(TEXT("spring_scale"), SpringScale); Report->SetStringField(TEXT("before_state"), bAllBaseline ? TEXT("Baseline") : TEXT("Adjusted"));
	Report->SetStringField(TEXT("numeric_source"), TEXT("Assistant temporary tuning; original-game physics values unverified."));
	Report->SetStringField(TEXT("modified_fields"), TEXT("AngularDrive.SlerpDrive.Stiffness; AngularDrive.SlerpDrive.Damping; ConeLimit.Swing1LimitDegrees; ConeLimit.Swing2LimitDegrees; saved default profile mirrors these fields only."));
	TArray<TSharedPtr<FJsonValue>> JointReports;
	if (bApply) PA->Modify();
	for (UPhysicsConstraintTemplate* Joint : Targets)
	{
		FConstraintInstance& C = Joint->DefaultInstance;
		const FConstraintInstance Before = C;
		FConstraintInstance Expected = Before;
		const FVector4f BaselineValues = BaselineFields[C.ConstraintBone1]; const FVector3f Scales = BoneScales[C.ConstraintBone1];
		if (bApply)
		{
			Expected.ProfileInstance.AngularDrive.SlerpDrive.Stiffness *= Scales.X; Expected.ProfileInstance.AngularDrive.SlerpDrive.Damping *= Scales.Y;
			Expected.ProfileInstance.ConeLimit.Swing1LimitDegrees *= Scales.Z; Expected.ProfileInstance.ConeLimit.Swing2LimitDegrees *= Scales.Z;
			Joint->Modify(); C.ProfileInstance.AngularDrive.SlerpDrive.Stiffness = Expected.ProfileInstance.AngularDrive.SlerpDrive.Stiffness; C.ProfileInstance.AngularDrive.SlerpDrive.Damping = Expected.ProfileInstance.AngularDrive.SlerpDrive.Damping;
			C.ProfileInstance.ConeLimit.Swing1LimitDegrees = Expected.ProfileInstance.ConeLimit.Swing1LimitDegrees; C.ProfileInstance.ConeLimit.Swing2LimitDegrees = Expected.ProfileInstance.ConeLimit.Swing2LimitDegrees;
			Joint->SetDefaultProfile(C);
		}
		const FConstraintProfileProperties& Default = Joint->GetConstraintProfilePropertiesOrDefault(NAME_None);
		if (!TestTrue(TEXT("Only requested SLERP coefficients and cone swing limits differ in the full constraint instance"), FConstraintInstance::StaticStruct()->CompareScriptStruct(&C, &Expected, 0)) ||
			!TestTrue(TEXT("Saved default profile contains only the expected changes"), ProfileStruct->CompareScriptStruct(&Default, &Expected.ProfileInstance, 0))) return false;
		auto Item = MakeShared<FJsonObject>(), BeforeProfile = MakeShared<FJsonObject>(), AfterProfile = MakeShared<FJsonObject>(), SavedProfile = MakeShared<FJsonObject>();
		if (!FJsonObjectConverter::UStructToJsonObject(ProfileStruct, &Before.ProfileInstance, BeforeProfile) || !FJsonObjectConverter::UStructToJsonObject(ProfileStruct, &C.ProfileInstance, AfterProfile) || !FJsonObjectConverter::UStructToJsonObject(ProfileStruct, &Default, SavedProfile)) return false;
		Item->SetStringField(TEXT("bone"), C.ConstraintBone1.ToString()); Item->SetStringField(TEXT("parent"), C.ConstraintBone2.ToString());
		Item->SetNumberField(TEXT("spring_scale"), Scales.X); Item->SetNumberField(TEXT("damping_scale"), Scales.Y); Item->SetNumberField(TEXT("swing_scale"), Scales.Z);
		Item->SetNumberField(TEXT("baseline_stiffness"), BaselineValues.X); Item->SetNumberField(TEXT("baseline_damping"), BaselineValues.Y); Item->SetNumberField(TEXT("baseline_swing1_degrees"), BaselineValues.Z); Item->SetNumberField(TEXT("baseline_swing2_degrees"), BaselineValues.W);
		Item->SetNumberField(TEXT("expected_adjusted_stiffness"), BaselineValues.X * Scales.X); Item->SetNumberField(TEXT("expected_adjusted_damping"), BaselineValues.Y * Scales.Y);
		Item->SetNumberField(TEXT("expected_adjusted_swing1_degrees"), BaselineValues.Z * Scales.Z); Item->SetNumberField(TEXT("expected_adjusted_swing2_degrees"), BaselineValues.W * Scales.Z);
		Item->SetNumberField(TEXT("before_stiffness"), Before.ProfileInstance.AngularDrive.SlerpDrive.Stiffness); Item->SetNumberField(TEXT("after_stiffness"), C.ProfileInstance.AngularDrive.SlerpDrive.Stiffness);
		Item->SetNumberField(TEXT("damping"), C.ProfileInstance.AngularDrive.SlerpDrive.Damping);
		Item->SetNumberField(TEXT("before_damping"), Before.ProfileInstance.AngularDrive.SlerpDrive.Damping); Item->SetNumberField(TEXT("after_damping"), C.ProfileInstance.AngularDrive.SlerpDrive.Damping);
		Item->SetNumberField(TEXT("before_swing1_degrees"), Before.GetAngularSwing1Limit()); Item->SetNumberField(TEXT("before_swing2_degrees"), Before.GetAngularSwing2Limit());
		Item->SetNumberField(TEXT("swing1_degrees"), C.GetAngularSwing1Limit()); Item->SetNumberField(TEXT("swing2_degrees"), C.GetAngularSwing2Limit()); Item->SetNumberField(TEXT("twist_degrees"), C.GetAngularTwistLimit());
		Item->SetObjectField(TEXT("before_profile"), BeforeProfile); Item->SetObjectField(TEXT("after_profile"), AfterProfile); Item->SetObjectField(TEXT("saved_default_profile"), SavedProfile);
		Item->SetBoolField(TEXT("full_constraint_matches_expected"), true); JointReports.Add(MakeShared<FJsonValueObject>(Item));
		AddInfo(FString::Printf(TEXT("LeftShoulderSpring bone=%s apply=%d scales=%.9f/%.9f/%.9f spring=%.9f->%.9f damping=%.9f->%.9f swing=%.6f/%.6f->%.6f/%.6f twist=%.6f"), *C.ConstraintBone1.ToString(), bApply, Scales.X, Scales.Y, Scales.Z, Before.ProfileInstance.AngularDrive.SlerpDrive.Stiffness, C.ProfileInstance.AngularDrive.SlerpDrive.Stiffness, Before.ProfileInstance.AngularDrive.SlerpDrive.Damping, C.ProfileInstance.AngularDrive.SlerpDrive.Damping, Before.GetAngularSwing1Limit(), Before.GetAngularSwing2Limit(), C.GetAngularSwing1Limit(), C.GetAngularSwing2Limit(), C.GetAngularTwistLimit()));
	}
	if (!TestTrue(TEXT("Body and constraint array counts preserved"), PA->SkeletalBodySetups.Num() == BeforeBodies.Num() && PA->ConstraintSetup.Num() == BeforeJoints.Num())) return false;
	for (int32 I = 0; I < PA->SkeletalBodySetups.Num(); ++I) if (!TestTrue(TEXT("Every reflected body field remains unchanged"), SameJson(Snapshot(PA->SkeletalBodySetups[I]), BeforeBodies[I]))) return false;
	for (int32 I = 0; I < PA->ConstraintSetup.Num(); ++I)
	{
		const UPhysicsConstraintTemplate* Joint = PA->ConstraintSetup[I]; auto Actual = Snapshot(Joint);
		if (bApply && Targets.Contains(Joint)) Actual->SetObjectField(TEXT("defaultInstance"), BeforeJoints[I]->GetObjectField(TEXT("defaultInstance")));
		if (!TestTrue(TEXT("Every reflected joint field remains unchanged except already-checked targeted instance fields"), SameJson(Actual, BeforeJoints[I])) ||
			!TestTrue(TEXT("Every untargeted saved default profile remains unchanged"), Targets.Contains(Joint) || ProfileStruct->CompareScriptStruct(&Joint->GetConstraintProfilePropertiesOrDefault(NAME_None), &BeforeDefaults[I], 0))) return false;
	}
	// Instanced constraints were fully checked above; normalize only this checked array.
	auto ActualPA = Snapshot(PA); ActualPA->SetField(TEXT("constraintSetup"), BeforePA->Values[TEXT("constraintSetup")]);
	if (!TestTrue(TEXT("PhysicsAsset settings, solver and all other reflected fields remain unchanged"), SameJson(ActualPA, BeforePA) && bSnapshotsValid)) return false;
	Report->SetBoolField(TEXT("only_approved_changes_verified"), true);
	Report->SetArrayField(TEXT("joints"), JointReports); Report->SetBoolField(TEXT("asset_saved"), bApply && Save(PA));
	if (bApply && !TestTrue(TEXT("Only Torso PhysicsAsset saved once"), Report->GetBoolField(TEXT("asset_saved")))) return false;
	Report->SetBoolField(TEXT("success"), true);
	FString Json;
	return FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json)) && FFileHelper::SaveStringToFile(Json, *(FPaths::ProjectSavedDir() / TEXT("LeftShoulderProfileAudit.json")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerIronAudit, "Khazan.PlayerParts.IronAudit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerIronAudit::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor; if (!IsWork()) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Leg"))); if (!TestNotNull(TEXT("Existing Leg mesh"), Mesh)) return false;
	auto Report = MakeShared<FJsonObject>(); TArray<TSharedPtr<FJsonValue>> Rows; bool bValid = true;
	Report->SetStringField(TEXT("mode"), TEXT("ReadOnlyOriginalImportAndDerivedUnitActorAudit")); Report->SetBoolField(TEXT("original_game_physics_verified"), false);
	USkeletalMesh* AnatomyMesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Body")));
	UPhysicsAsset* AnatomyPA = LoadObject<UPhysicsAsset>(nullptr, *(Base + TEXT("Meshs/Player_PhysicsAsset")));
	if (!TestNotNull(TEXT("Existing parent anatomy mesh"), AnatomyMesh) || !TestNotNull(TEXT("Existing parent anatomy PhysicsAsset"), AnatomyPA)) return false;
	auto UnitRefPose = [&](USkeletalMesh* Source, TArray<FTransform>& Unit)
	{
		const FReferenceSkeleton& Ref = Source->GetRefSkeleton(); const double Scale = Ref.GetRefBonePose()[0].GetScale3D().X;
		if (!TestTrue(TEXT("Finite positive uniform imported reference wrapper"), FMath::IsFinite(Scale) && Scale > 0. && Ref.GetRefBonePose()[0].GetScale3D().Equals(FVector(Scale)))) return false;
		for (int32 I = 0; I < Ref.GetNum(); ++I) { FTransform Pose = Ref.GetRefBonePose()[I]; if (I > 0) Pose = Pose * Unit[Ref.GetParentIndex(I)]; Unit.Add(Pose); }
		for (FTransform& Pose : Unit) { Pose.SetTranslation(Pose.GetTranslation() / Scale); Pose.SetScale3D(FVector::OneVector); } return true;
	};
	TArray<FTransform> Unit, AnatomyUnit; if (!UnitRefPose(Mesh, Unit) || !UnitRefPose(AnatomyMesh, AnatomyUnit)) return false;
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton(); const FReferenceSkeleton& AnatomyRef = AnatomyMesh->GetRefSkeleton();
	const int32 LegParent = Ref.FindBoneIndex(TEXT("Bip001-Pelvis")), BodyParent = AnatomyRef.FindBoneIndex(TEXT("Bip001-Pelvis"));
	if (!TestTrue(TEXT("Shared pelvis reference basis available"), LegParent != INDEX_NONE && BodyParent != INDEX_NONE)) return false;
	for (const FName Bone : {FName(TEXT("B_Iron_01_01_R_Pelvis")), FName(TEXT("B_Iron_01_01_L_Pelvis"))})
	{
		const int32 Index = Ref.FindBoneIndex(Bone); if (!TestTrue(TEXT("Iron reference bone available"), Index != INDEX_NONE)) return false;
		Unit[Index] = Unit[Index].GetRelativeTransform(Unit[LegParent]) * AnatomyUnit[BodyParent];
	}
	Report->SetStringField(TEXT("anatomy_comparison_basis"), TEXT("IronRelativeToLegPelvisAlignedToBodyPelvisReference;NotCurrentRuntimePose"));
	Mesh->CalculateInvRefMatrices(); const TArray<FMatrix44f>& InverseRef = Mesh->GetRefBasesInvMatrix(); const FSkeletalMeshModel* Model = Mesh->GetImportedModel();
	if (!TestTrue(TEXT("Imported Iron LOD0 and inverse reference matrices available"), Model && !Model->LODModels.IsEmpty() && InverseRef.Num() >= Ref.GetRawBoneNum())) return false;
	TMap<int32, TArray<FVector>> Positive, Dominant; double RoundTripError = 0.;
	for (const FSkelMeshSection& Section : Model->LODModels[0].Sections)
		for (const FSoftSkinVertex& Vertex : Section.SoftVertices)
			for (int32 Influence = 0; Influence < UE_ARRAY_COUNT(Vertex.InfluenceBones); ++Influence)
			{
				if (!Vertex.InfluenceWeights[Influence] || !Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[Influence])) continue;
				const int32 BoneIndex = Section.BoneMap[Vertex.InfluenceBones[Influence]];
				if (Ref.GetBoneName(BoneIndex) != FName(TEXT("B_Iron_01_01_R_Pelvis")) && Ref.GetBoneName(BoneIndex) != FName(TEXT("B_Iron_01_01_L_Pelvis"))) continue;
				// The existing cloth fitting contract: inverse-ref gives centimetres directly;
				// only component-space reference translations remove the wrapper scale.
				const FVector3f Local = InverseRef[BoneIndex].TransformPosition(Vertex.Position);
				if (!TestTrue(TEXT("Finite bone-local Iron support"), !Local.ContainsNaN())) return false;
				Positive.FindOrAdd(BoneIndex).Add(FVector(Local)); bool bDominant = true;
				for (int32 Other = 0; Other < UE_ARRAY_COUNT(Vertex.InfluenceBones); ++Other)
					if (Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[Other]) && (Vertex.InfluenceWeights[Other] > Vertex.InfluenceWeights[Influence] || (Vertex.InfluenceWeights[Other] == Vertex.InfluenceWeights[Influence] && Other < Influence))) { bDominant = false; break; }
				if (bDominant) Dominant.FindOrAdd(BoneIndex).Add(FVector(Local));
				RoundTripError = FMath::Max(RoundTripError, double((InverseRef[BoneIndex].Inverse().TransformPosition(Local) - Vertex.Position).Size()) / Ref.GetRefBonePose()[0].GetScale3D().X);
			}
	auto VectorField = [](const TSharedRef<FJsonObject>& Object, const TCHAR* Name, const FVector& Value)
	{
		TArray<TSharedPtr<FJsonValue>> Values; for (double Component : {Value.X, Value.Y, Value.Z}) Values.Add(MakeShared<FJsonValueNumber>(Component)); Object->SetArrayField(Name, Values);
	};
	Report->SetStringField(TEXT("support_source"), TEXT("ImportedLOD0InverseRefBoneLocalCm;Dominant=LargestWeightFirstValidInfluenceSlot;ReferenceOnlyNotRuntimeSkin"));
	Report->SetNumberField(TEXT("support_round_trip_max_error_cm"), RoundTripError); Report->SetStringField(TEXT("anatomy_asset"), AnatomyPA->GetPathName());
	for (const FString Suffix : {TEXT("_PhysicsAsset"), TEXT("_RigidBody_PhysicsAsset")})
	{
		UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(TEXT("Leg")) + Suffix)); if (!TestNotNull(TEXT("Existing Leg PhysicsAsset"), PA)) return false;
		auto* Probe = NewObject<USkeletalMeshComponent>(); Probe->SetSkeletalMesh(Mesh); TArray<FBodyInstance*> Bodies; Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, Bodies);
		for (const FName Bone : {FName(TEXT("B_Iron_01_01_R_Pelvis")), FName(TEXT("B_Iron_01_01_L_Pelvis"))})
		{
			const int32 Index = PA->FindBodyIndex(Bone); const auto* Joint = PA->ConstraintSetup.FindByPredicate([&](const UPhysicsConstraintTemplate* C) { return C->DefaultInstance.ConstraintBone1 == Bone; });
			if (!TestTrue(TEXT("Exact Iron body and joint available"), Index != INDEX_NONE && Bodies.IsValidIndex(Index) && Joint)) { bValid = false; break; }
			const USkeletalBodySetup* Body = PA->SkeletalBodySetups[Index]; FBodyInstance* BI = Bodies[Index]; const FConstraintInstance& C = (*Joint)->DefaultInstance;
			const auto Current = ImmediatePhysics::MakeDynamicActorSetup(BI, FTransform::Identity); const FVector SavedScale = BI->InertiaTensorScale;
			// Only this unregistered probe instance changes; source/derived asset settings remain untouched.
			BI->InertiaTensorScale = FVector::OneVector; const auto Unconditioned = ImmediatePhysics::MakeDynamicActorSetup(BI, FTransform::Identity); BI->InertiaTensorScale = SavedScale;
			auto Item = MakeShared<FJsonObject>(), Geometry = MakeShared<FJsonObject>(), BodySettings = MakeShared<FJsonObject>(), Profile = MakeShared<FJsonObject>(), Default = MakeShared<FJsonObject>();
			const FConstraintProfileProperties& DefaultProfile = (*Joint)->GetConstraintProfilePropertiesOrDefault(NAME_None);
			bValid &= FJsonObjectConverter::UStructToJsonObject(FKAggregateGeom::StaticStruct(), &Body->AggGeom, Geometry) && FJsonObjectConverter::UStructToJsonObject(FBodyInstance::StaticStruct(), &Body->DefaultInstance, BodySettings);
			bValid &= FJsonObjectConverter::UStructToJsonObject(FConstraintProfileProperties::StaticStruct(), &C.ProfileInstance, Profile) && FJsonObjectConverter::UStructToJsonObject(FConstraintProfileProperties::StaticStruct(), &DefaultProfile, Default);
			Item->SetStringField(TEXT("asset"), PA->GetPathName()); Item->SetStringField(TEXT("bone"), Bone.ToString()); Item->SetStringField(TEXT("parent"), C.ConstraintBone2.ToString()); Item->SetNumberField(TEXT("physics_type"), int32(Body->PhysicsType));
			Item->SetNumberField(TEXT("body_collision_response"), int32(Body->CollisionReponse)); Item->SetObjectField(TEXT("geometry_bone_local_cm"), Geometry); Item->SetObjectField(TEXT("body_settings"), BodySettings);
			Item->SetObjectField(TEXT("current_joint_profile"), Profile); Item->SetObjectField(TEXT("default_joint_profile"), Default); Item->SetBoolField(TEXT("profiles_identical"), FConstraintProfileProperties::StaticStruct()->CompareScriptStruct(&C.ProfileInstance, &DefaultProfile, 0));
			Item->SetNumberField(TEXT("current_mass_kg"), double(Current.Mass)); Item->SetNumberField(TEXT("unconditioned_mass_kg"), double(Unconditioned.Mass));
			Item->SetStringField(TEXT("current_principal_kg_cm2"), FString::Printf(TEXT("%.12g/%.12g/%.12g"), double(Current.Inertia.X), double(Current.Inertia.Y), double(Current.Inertia.Z)));
			Item->SetStringField(TEXT("unconditioned_principal_kg_cm2"), FString::Printf(TEXT("%.12g/%.12g/%.12g"), double(Unconditioned.Inertia.X), double(Unconditioned.Inertia.Y), double(Unconditioned.Inertia.Z)));
			Item->SetNumberField(TEXT("current_minimum_principal_kg_cm2"), FVector(Current.Inertia).GetMin()); Item->SetNumberField(TEXT("current_maximum_principal_kg_cm2"), FVector(Current.Inertia).GetMax());
			Item->SetStringField(TEXT("current_com"), Current.CoMTransform.ToString()); Item->SetStringField(TEXT("unconditioned_com"), Unconditioned.CoMTransform.ToString()); Item->SetStringField(TEXT("frame1"), C.GetRefFrame(EConstraintFrame::Frame1).ToString()); Item->SetStringField(TEXT("frame2"), C.GetRefFrame(EConstraintFrame::Frame2).ToString());
			const int32 BoneIndex = Ref.FindBoneIndex(Bone), ParentIndex = AnatomyRef.FindBoneIndex(C.ConstraintBone2), ParentBody = AnatomyPA->FindBodyIndex(C.ConstraintBone2);
			if (!TestTrue(TEXT("Iron single capsule and current parent single anatomy capsule available"), BoneIndex != INDEX_NONE && ParentIndex != INDEX_NONE && ParentBody != INDEX_NONE && Body->AggGeom.GetElementCount() == 1 && Body->AggGeom.SphylElems.Num() == 1 && AnatomyPA->SkeletalBodySetups[ParentBody]->AggGeom.GetElementCount() == 1 && AnatomyPA->SkeletalBodySetups[ParentBody]->AggGeom.SphylElems.Num() == 1)) { bValid = false; break; }
			const FKSphylElem& Capsule = Body->AggGeom.SphylElems[0]; const FKSphylElem& Pelvis = AnatomyPA->SkeletalBodySetups[ParentBody]->AggGeom.SphylElems[0];
			if (!TestTrue(TEXT("Positive finite reference capsule dimensions and positive Iron support"), FMath::IsFinite(Capsule.Radius) && Capsule.Radius > 0. && FMath::IsFinite(Capsule.Length) && Capsule.Length > 0. && FMath::IsFinite(Pelvis.Radius) && Pelvis.Radius > 0. && FMath::IsFinite(Pelvis.Length) && Pelvis.Length > 0. && Positive.Contains(BoneIndex) && !Positive[BoneIndex].IsEmpty())) { bValid = false; break; }
			const FTransform CapsuleLocal = Capsule.GetTransform(), CapsuleUnit = CapsuleLocal * Unit[BoneIndex], PelvisUnit = Pelvis.GetTransform() * AnatomyUnit[ParentIndex];
			const FVector AxisA = CapsuleUnit.TransformPosition(FVector(0., 0., -.5 * Capsule.Length)), AxisB = CapsuleUnit.TransformPosition(FVector(0., 0., .5 * Capsule.Length));
			FVector ClosestIron, ClosestPelvis;
			FMath::SegmentDistToSegmentSafe(AxisA, AxisB, PelvisUnit.TransformPosition(FVector(0., 0., -.5 * Pelvis.Length)), PelvisUnit.TransformPosition(FVector(0., 0., .5 * Pelvis.Length)), ClosestIron, ClosestPelvis);
			const double Clearance = (ClosestIron - ClosestPelvis).Size() - Capsule.Radius - Pelvis.Radius;
			bValid &= TestTrue(TEXT("Finite reference Iron capsule versus parent capsule clearance"), FMath::IsFinite(Clearance));
			Item->SetNumberField(TEXT("ref_capsule_parent_clearance_cm"), Clearance); Item->SetStringField(TEXT("ref_clearance_method"), TEXT("ExactCapsuleAxisSegmentDistanceMinusBothRadii;NegativeMeansOverlap"));
			Item->SetNumberField(TEXT("parent_capsule_radius_cm"), Pelvis.Radius); Item->SetNumberField(TEXT("parent_capsule_cylinder_length_cm"), Pelvis.Length); VectorField(Item, TEXT("bone_pivot_capsule_local_cm"), CapsuleLocal.InverseTransformPosition(FVector::ZeroVector));
			VectorField(Item, TEXT("ref_parent_axis_start_cm"), PelvisUnit.TransformPosition(FVector(0., 0., -.5 * Pelvis.Length))); VectorField(Item, TEXT("ref_parent_axis_end_cm"), PelvisUnit.TransformPosition(FVector(0., 0., .5 * Pelvis.Length)));
			VectorField(Item, TEXT("ref_capsule_axis_start_cm"), AxisA); VectorField(Item, TEXT("ref_capsule_axis_end_cm"), AxisB); VectorField(Item, TEXT("ref_closest_capsule_axis_point_cm"), ClosestIron); VectorField(Item, TEXT("ref_closest_parent_axis_point_cm"), ClosestPelvis);
			TArray<TSharedPtr<FJsonValue>> SupportRows;
			for (bool bDominant : {false, true})
			{
				const TArray<FVector>* Points = (bDominant ? Dominant : Positive).Find(BoneIndex); auto Support = MakeShared<FJsonObject>();
				Support->SetStringField(TEXT("selection"), bDominant ? TEXT("Dominant") : TEXT("AllPositive")); Support->SetNumberField(TEXT("count"), Points ? Points->Num() : 0);
				if (Points && !Points->IsEmpty())
				{
					FBox BoneBounds(ForceInit), CapsuleBounds(ForceInit); double MaxRadial = 0., MinCapsulePhi = DBL_MAX, MaxCapsulePhi = -DBL_MAX, MinParentPhi = DBL_MAX; int32 Covered = 0, ParentInside = 0;
					for (const FVector& Point : *Points)
					{
						const FVector Local = CapsuleLocal.InverseTransformPosition(Point), ParentLocal = PelvisUnit.InverseTransformPosition(Unit[BoneIndex].TransformPosition(Point));
						BoneBounds += Point; CapsuleBounds += Local; MaxRadial = FMath::Max(MaxRadial, FMath::Sqrt(Local.X * Local.X + Local.Y * Local.Y));
						const double Phi = (Local - FVector(0., 0., FMath::Clamp(Local.Z, -.5 * Capsule.Length, .5 * Capsule.Length))).Size() - Capsule.Radius;
						const double ParentPhi = (ParentLocal - FVector(0., 0., FMath::Clamp(ParentLocal.Z, -.5 * Pelvis.Length, .5 * Pelvis.Length))).Size() - Pelvis.Radius;
						MinCapsulePhi = FMath::Min(MinCapsulePhi, Phi); MaxCapsulePhi = FMath::Max(MaxCapsulePhi, Phi); MinParentPhi = FMath::Min(MinParentPhi, ParentPhi); Covered += Phi <= 0.; ParentInside += ParentPhi < 0.;
					}
					VectorField(Support, TEXT("bone_local_min_cm"), BoneBounds.Min); VectorField(Support, TEXT("bone_local_max_cm"), BoneBounds.Max); VectorField(Support, TEXT("capsule_local_min_cm"), CapsuleBounds.Min); VectorField(Support, TEXT("capsule_local_max_cm"), CapsuleBounds.Max);
					Support->SetNumberField(TEXT("max_capsule_axis_radial_cm"), MaxRadial); Support->SetNumberField(TEXT("capsule_phi_min_cm"), MinCapsulePhi); Support->SetNumberField(TEXT("capsule_phi_max_cm"), MaxCapsulePhi); Support->SetNumberField(TEXT("capsule_covered_vertices"), Covered);
					Support->SetNumberField(TEXT("parent_phi_min_cm"), MinParentPhi); Support->SetNumberField(TEXT("parent_inside_vertices"), ParentInside);
					Support->SetNumberField(TEXT("capsule_negative_z_extent_beyond_support_cm"), FMath::Max(0., CapsuleBounds.Min.Z + .5 * Capsule.Length + Capsule.Radius)); Support->SetNumberField(TEXT("capsule_positive_z_extent_beyond_support_cm"), FMath::Max(0., .5 * Capsule.Length + Capsule.Radius - CapsuleBounds.Max.Z));
				}
				SupportRows.Add(MakeShared<FJsonValueObject>(Support));
			}
			Item->SetArrayField(TEXT("reference_vertex_support"), SupportRows);
			bValid &= TestTrue(TEXT("Finite positive Iron mass and current principal inertia"), FMath::IsFinite(double(Current.Mass)) && Current.Mass > 0 && !FVector(Current.Inertia).ContainsNaN() && FVector(Current.Inertia).GetMin() > 0); Rows.Add(MakeShared<FJsonValueObject>(Item));
		}
		for (FBodyInstance* BI : Bodies) { if (BI->IsValidBodyInstance()) BI->TermBody(true); delete BI; } if (!bValid) return false;
	}
	Report->SetArrayField(TEXT("bodies"), Rows); Report->SetBoolField(TEXT("success"), bValid); FString Json;
	return TestEqual(TEXT("Original and derived Iron2 rows"), Rows.Num(), 4) && FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json)) && FFileHelper::SaveStringToFile(Json, *(FPaths::ProjectSavedDir() / TEXT("IronPhysicsAudit.json")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerIronContactAuthor, "Khazan.PlayerParts.IronContactAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerIronContactAuthor::RunTest(const FString& Parameters)
{
	using namespace KZPlayerPartsAuthor; if (!IsWork()) return false;
	FConfigFile Settings; Settings.Read(FPaths::ProjectSavedDir() / TEXT("IronContact.ini")); bool bApply = false;
	Settings.GetBool(TEXT("IronContact"), TEXT("Apply"), bApply); FString ExpectedSHA1, ExternalSHA256, AuditFile, Mode = TEXT("Center"); Settings.GetString(TEXT("IronContact"), TEXT("Mode"), Mode);
	if (!TestTrue(TEXT("Explicit known contact geometry mode"), Mode == TEXT("Center") || Mode == TEXT("SparseSpheres"))) return false; const bool bSparse = Mode == TEXT("SparseSpheres");
	if (!TestTrue(TEXT("Explicit native SHA1 guard, external SHA256 provenance and audit file"), Settings.GetString(TEXT("IronContact"), TEXT("BaselineSHA1"), ExpectedSHA1) && Settings.GetString(TEXT("IronContact"), TEXT("BaselineSHA256"), ExternalSHA256) && Settings.GetString(TEXT("IronContact"), TEXT("BaselineAuditFile"), AuditFile))) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Leg"))); UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, *(MeshPath(TEXT("Leg")) + TEXT("_RigidBody_PhysicsAsset")));
	USkeletalMesh* AnatomyMesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath(TEXT("Body"))); UPhysicsAsset* AnatomyPA = LoadObject<UPhysicsAsset>(nullptr, *(Base + TEXT("Meshs/Player_PhysicsAsset")));
	if (!TestNotNull(TEXT("Existing Leg mesh"), Mesh) || !TestNotNull(TEXT("Existing Leg PA"), PA) || !TestNotNull(TEXT("Existing anatomy mesh"), AnatomyMesh) || !TestNotNull(TEXT("Existing anatomy PA"), AnatomyPA)) return false;
	TArray<uint8> AssetBytes;
	if (!TestTrue(TEXT("Baseline asset bytes available"), FFileHelper::LoadFileToArray(AssetBytes, *FPackageName::LongPackageNameToFilename(PA->GetOutermost()->GetName(), FPackageName::GetAssetPackageExtension())))) return false;
	const FSHAHash Signature = FSHA1::HashBuffer(AssetBytes.GetData(), uint64(AssetBytes.Num()));
	if (!TestTrue(TEXT("Exact baseline asset SHA1 prevents compounded or stale isolated authoring"), Signature.ToString().Equals(ExpectedSHA1, ESearchCase::IgnoreCase))) return false;
	FString AuditText; TSharedPtr<FJsonObject> Baseline;
	if (!TestTrue(TEXT("Saved read-only baseline audit available"), FFileHelper::LoadFileToString(AuditText, *(FPaths::ProjectSavedDir() / AuditFile)) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(AuditText), Baseline) && Baseline.IsValid())) return false;
	auto Report = MakeShared<FJsonObject>(); TArray<TSharedPtr<FJsonValue>> Rows;
	Report->SetStringField(TEXT("asset"), PA->GetPathName()); Report->SetStringField(TEXT("before_asset_sha1_native"), Signature.ToString()); Report->SetStringField(TEXT("baseline_sha256_external_provenance"), ExternalSHA256); Report->SetBoolField(TEXT("apply_requested"), bApply);
	Report->SetStringField(TEXT("mode"), Mode); Report->SetStringField(TEXT("reference_basis"), TEXT("LegIronRelativeToLegSharedParent * BodySharedParentUnitRef; CopyPose shared-parent basis, not independent exported Leg component ref."));
	Report->SetStringField(TEXT("policy_source"), bSparse ? TEXT("Assistant temporary sparse four-sphere approximation on actual dominant support; radius reuses baseline capsule. Geometry-derived CoM/principal moments change; legacy capsule InertiaTensorScale reset to One. Mass override, damping, materials, collision, constraints and solver preserved; original-game physics unverified.") : TEXT("Assistant geometry-derived temporary repair; original-game physics unverified. Only capsule Center changes; dimensions, rotation, mass override, inertia scale, damping, materials, collision, constraints and solver preserved."));
	auto Finish = [&](bool bSuccess)
	{
		Report->SetArrayField(TEXT("bodies"), Rows); Report->SetBoolField(TEXT("success"), bSuccess); FString Json;
		const bool bWritten = FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json)) && FFileHelper::SaveStringToFile(Json, *(FPaths::ProjectSavedDir() / TEXT("IronContactAuthor.json"))); return bSuccess && bWritten;
	};
	bool bSnapshotsValid = true;
	auto Snapshot = [&](const UObject* Object)
	{
		auto Json = MakeShared<FJsonObject>(); bSnapshotsValid &= FJsonObjectConverter::UStructToJsonObject(Object->GetClass(), Object, Json); return Json;
	};
	auto SameJson = [](const TSharedPtr<FJsonObject>& A, const TSharedPtr<FJsonObject>& B) { return FJsonValue::CompareEqual(FJsonValueObject(A), FJsonValueObject(B)); };
	TArray<TSharedPtr<FJsonObject>> BeforeBodies, BeforeJoints; TArray<FConstraintProfileProperties> BeforeDefaults;
	for (const USkeletalBodySetup* Body : PA->SkeletalBodySetups) BeforeBodies.Add(Snapshot(Body));
	for (const UPhysicsConstraintTemplate* Joint : PA->ConstraintSetup) { BeforeJoints.Add(Snapshot(Joint)); BeforeDefaults.Add(Joint->GetConstraintProfilePropertiesOrDefault(NAME_None)); }
	const auto BeforePA = Snapshot(PA); if (!TestTrue(TEXT("Full reflected baseline snapshots exported"), bSnapshotsValid)) return false;
	auto UnitRefPose = [&](USkeletalMesh* Source, TArray<FTransform>& Unit)
	{
		const auto& Ref = Source->GetRefSkeleton(); const double Scale = Ref.GetRefBonePose()[0].GetScale3D().X;
		if (!TestTrue(TEXT("Finite positive uniform reference wrapper"), FMath::IsFinite(Scale) && Scale > 0. && Ref.GetRefBonePose()[0].GetScale3D().Equals(FVector(Scale)))) return false;
		for (int32 I = 0; I < Ref.GetNum(); ++I) { FTransform Pose = Ref.GetRefBonePose()[I]; if (I) Pose = Pose * Unit[Ref.GetParentIndex(I)]; Unit.Add(Pose); }
		for (FTransform& Pose : Unit) { Pose.SetTranslation(Pose.GetTranslation() / Scale); Pose.SetScale3D(FVector::OneVector); } return true;
	};
	TArray<FTransform> Unit, AnatomyUnit; if (!UnitRefPose(Mesh, Unit) || !UnitRefPose(AnatomyMesh, AnatomyUnit)) return false;
	struct FAnatomyCapsule { FName Bone; FTransform Transform; double Radius, Length; }; TArray<FAnatomyCapsule> Anatomy;
	for (const USkeletalBodySetup* Body : AnatomyPA->SkeletalBodySetups)
	{
		const int32 Index = AnatomyMesh->GetRefSkeleton().FindBoneIndex(Body->BoneName);
		if (!TestTrue(TEXT("Existing anatomy uses only supported capsules"), Index != INDEX_NONE && Body->AggGeom.GetElementCount() == Body->AggGeom.SphylElems.Num())) return false;
		for (const FKSphylElem& Capsule : Body->AggGeom.SphylElems) Anatomy.Add({Body->BoneName, Capsule.GetTransform() * AnatomyUnit[Index], Capsule.Radius, Capsule.Length});
	}
	if (!TestEqual(TEXT("All current external anatomy capsules included"), Anatomy.Num(), 18)) return false;
	const FName Right(TEXT("B_Iron_01_01_R_Pelvis")), Left(TEXT("B_Iron_01_01_L_Pelvis")); const auto& Ref = Mesh->GetRefSkeleton();
	Mesh->CalculateInvRefMatrices(); const auto& InverseRef = Mesh->GetRefBasesInvMatrix(); const FSkeletalMeshModel* Model = Mesh->GetImportedModel();
	if (!TestTrue(TEXT("Imported LOD0 inverse-reference support available"), Model && !Model->LODModels.IsEmpty() && InverseRef.Num() >= Ref.GetRawBoneNum())) return false;
	TMap<int32, TArray<FVector>> Dominant;
	for (const FSkelMeshSection& Section : Model->LODModels[0].Sections)
		for (const FSoftSkinVertex& Vertex : Section.SoftVertices)
		{
			int32 Winner = INDEX_NONE;
			for (int32 I = 0; I < UE_ARRAY_COUNT(Vertex.InfluenceBones); ++I)
				if (Vertex.InfluenceWeights[I] && Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[I]) && (Winner == INDEX_NONE || Vertex.InfluenceWeights[I] > Vertex.InfluenceWeights[Winner])) Winner = I;
			if (Winner == INDEX_NONE) continue; const int32 Index = Section.BoneMap[Vertex.InfluenceBones[Winner]];
			if (Ref.GetBoneName(Index) == Right || Ref.GetBoneName(Index) == Left) { const FVector Point(InverseRef[Index].TransformPosition(Vertex.Position)); if (!TestTrue(TEXT("Finite actual dominant support"), !Point.ContainsNaN())) return false; Dominant.FindOrAdd(Index).Add(Point); }
		}
	TMap<int32, FVector> ChosenCenters; TMap<int32, FKAggregateGeom> ExpectedGeometry;
	for (const FName Bone : {Right, Left})
	{
		const int32 BodyIndex = PA->FindBodyIndex(Bone), BoneIndex = Ref.FindBoneIndex(Bone); const auto* Joint = PA->ConstraintSetup.FindByPredicate([&](const UPhysicsConstraintTemplate* C) { return C->DefaultInstance.ConstraintBone1 == Bone; });
		if (!TestTrue(TEXT("Exact simulated colliding Iron2 with single capsule and support"), BodyIndex != INDEX_NONE && BoneIndex != INDEX_NONE && Joint && Dominant.Contains(BoneIndex) && !Dominant[BoneIndex].IsEmpty() && PA->SkeletalBodySetups[BodyIndex]->PhysicsType == PhysType_Simulated && PA->SkeletalBodySetups[BodyIndex]->CollisionReponse == EBodyCollisionResponse::BodyCollision_Enabled && PA->SkeletalBodySetups[BodyIndex]->AggGeom.GetElementCount() == 1 && PA->SkeletalBodySetups[BodyIndex]->AggGeom.SphylElems.Num() == 1)) return false;
		const USkeletalBodySetup* Body = PA->SkeletalBodySetups[BodyIndex]; const FKSphylElem& Capsule = Body->AggGeom.SphylElems[0]; const auto& C = (*Joint)->DefaultInstance; TSharedPtr<FJsonObject> Saved;
		for (const auto& Value : Baseline->GetArrayField(TEXT("bodies"))) { auto Row = Value->AsObject(); if (Row->GetStringField(TEXT("asset")) == PA->GetPathName() && Row->GetStringField(TEXT("bone")) == Bone.ToString()) Saved = Row; }
		// Compare serialized authored fields. JSON omits deprecated geometry fields,
		// so deserialized structs are unsuitable for full reflected struct identity.
		auto CurrentGeometry = MakeShared<FJsonObject>(), CurrentSettings = MakeShared<FJsonObject>(), CurrentProfile = MakeShared<FJsonObject>(), CurrentDefault = MakeShared<FJsonObject>();
		if (!TestTrue(TEXT("Exact serialized baseline geometry, body settings and current/default profiles"), Saved.IsValid() && FJsonObjectConverter::UStructToJsonObject(FKAggregateGeom::StaticStruct(), &Body->AggGeom, CurrentGeometry) && SameJson(CurrentGeometry, Saved->GetObjectField(TEXT("geometry_bone_local_cm"))) && FJsonObjectConverter::UStructToJsonObject(FBodyInstance::StaticStruct(), &Body->DefaultInstance, CurrentSettings) && SameJson(CurrentSettings, Saved->GetObjectField(TEXT("body_settings"))) && FJsonObjectConverter::UStructToJsonObject(FConstraintProfileProperties::StaticStruct(), &C.ProfileInstance, CurrentProfile) && SameJson(CurrentProfile, Saved->GetObjectField(TEXT("current_joint_profile"))) && FJsonObjectConverter::UStructToJsonObject(FConstraintProfileProperties::StaticStruct(), &(*Joint)->GetConstraintProfilePropertiesOrDefault(NAME_None), CurrentDefault) && SameJson(CurrentDefault, Saved->GetObjectField(TEXT("default_joint_profile"))))) return false;
		if (!TestTrue(TEXT("Positive preserved capsule dimensions"), Capsule.Radius > 0. && Capsule.Length > 0. && FMath::IsFinite(Capsule.Radius) && FMath::IsFinite(Capsule.Length))) return false;
		const int32 LegParent = Ref.FindBoneIndex(C.ConstraintBone2), BodyParent = AnatomyMesh->GetRefSkeleton().FindBoneIndex(C.ConstraintBone2);
		if (!TestTrue(TEXT("Iron directly attaches to the CopyPose shared parent"), LegParent != INDEX_NONE && BodyParent != INDEX_NONE && Ref.GetParentIndex(BoneIndex) == LegParent)) return false;
		const FTransform IronUnit = Unit[BoneIndex].GetRelativeTransform(Unit[LegParent]) * AnatomyUnit[BodyParent];
		auto Basis = MakeShared<FJsonObject>(); Basis->SetStringField(TEXT("leg_parent_independent_unit_ref"), Unit[LegParent].ToString()); Basis->SetStringField(TEXT("body_parent_unit_ref"), AnatomyUnit[BodyParent].ToString()); Basis->SetStringField(TEXT("iron_independent_unit_ref"), Unit[BoneIndex].ToString()); Basis->SetStringField(TEXT("iron_copy_pose_parent_aligned_unit_ref"), IronUnit.ToString());
		Basis->SetNumberField(TEXT("independent_parent_position_difference_cm"), (Unit[LegParent].GetLocation() - AnatomyUnit[BodyParent].GetLocation()).Size()); Basis->SetNumberField(TEXT("independent_parent_rotation_difference_degrees"), FMath::RadiansToDegrees(Unit[LegParent].GetRotation().AngularDistance(AnatomyUnit[BodyParent].GetRotation())));
		const TArray<FVector>& Points = Dominant[BoneIndex]; const FVector Axis = Capsule.Rotation.Quaternion().GetAxisZ(); int32 Best = INDEX_NONE, BestCovered = -1, Feasible = 0; double BestShift = DBL_MAX, BestClearance = 0.; FName BestAnatomy;
		if (bSparse)
		{
			// Four is an explicit assistant temporary approximation, not an original value.
			constexpr int32 SphereCount = 4; TArray<int32> Safe, Selected; TArray<double> Clearances; TArray<FName> NearestBones;
			for (int32 I = 0; I < Points.Num(); ++I)
			{
				const FVector WorldPoint = IronUnit.TransformPosition(Points[I]); double Clearance = DBL_MAX; FName Nearest;
				for (const auto& Shape : Anatomy) { const FVector Local = Shape.Transform.InverseTransformPosition(WorldPoint); const double Phi = (Local - FVector(0., 0., FMath::Clamp(Local.Z, -.5 * Shape.Length, .5 * Shape.Length))).Size() - Shape.Radius - Capsule.Radius; if (Phi < Clearance) { Clearance = Phi; Nearest = Shape.Bone; } }
				if (!TestTrue(TEXT("Finite exact sphere/anatomy clearance"), FMath::IsFinite(Clearance))) return false;
				if (Clearance >= 0.) { Safe.Add(I); Clearances.Add(Clearance); NearestBones.Add(Nearest); }
			}
			auto Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("bone"), Bone.ToString()); Row->SetObjectField(TEXT("reference_basis_audit"), Basis); Row->SetNumberField(TEXT("dominant_support_count"), Points.Num()); Row->SetNumberField(TEXT("safe_sphere_center_candidates"), Safe.Num()); Row->SetNumberField(TEXT("assistant_temporary_sphere_count"), SphereCount); Row->SetNumberField(TEXT("reused_contact_radius_cm"), Capsule.Radius); Rows.Add(MakeShared<FJsonValueObject>(Row));
			if (!TestTrue(TEXT("Enough actual support outside all anatomy for sparse spheres"), Safe.Num() >= SphereCount)) { Report->SetStringField(TEXT("failure"), TEXT("Insufficient safe sphere centers in shared-parent basis; asset unchanged.")); return Finish(false); }
			int32 First = 0; for (int32 I = 1; I < Safe.Num(); ++I) if (Clearances[I] < Clearances[First]) First = I; Selected.Add(First);
			while (Selected.Num() < SphereCount)
			{
				int32 Next = INDEX_NONE; double Farthest = 0.;
				for (int32 I = 0; I < Safe.Num(); ++I) { if (Selected.Contains(I)) continue; double Distance = DBL_MAX; for (int32 S : Selected) Distance = FMath::Min(Distance, (Points[Safe[I]] - Points[Safe[S]]).SizeSquared()); if (Distance > Farthest) { Farthest = Distance; Next = I; } }
				if (!TestTrue(TEXT("Sparse sphere centers are distinct actual support points"), Next != INDEX_NONE)) { Report->SetStringField(TEXT("failure"), TEXT("Insufficient distinct safe support; asset unchanged.")); return Finish(false); } Selected.Add(Next);
			}
			FKAggregateGeom Geometry = Body->AggGeom; Geometry.SphylElems.Empty(); TArray<TSharedPtr<FJsonValue>> Spheres; double MinClearance = DBL_MAX;
			for (int32 S : Selected)
			{
				FKSphereElem Sphere; Sphere.Center = Points[Safe[S]]; Sphere.Radius = Capsule.Radius; Sphere.RestOffset = Capsule.RestOffset; Sphere.SetName(Capsule.GetName()); Sphere.SetContributeToMass(Capsule.GetContributeToMass()); Sphere.SetCollisionEnabled(Capsule.GetCollisionEnabled()); Geometry.SphereElems.Add(Sphere);
				auto Item = MakeShared<FJsonObject>(); Item->SetNumberField(TEXT("actual_dominant_vertex_order"), Safe[S]); TArray<TSharedPtr<FJsonValue>> Center; for (double N : {Sphere.Center.X, Sphere.Center.Y, Sphere.Center.Z}) Center.Add(MakeShared<FJsonValueNumber>(N)); Item->SetArrayField(TEXT("center_bone_local_cm"), Center); Item->SetNumberField(TEXT("minimum_ref_anatomy_clearance_cm"), Clearances[S]); Item->SetStringField(TEXT("nearest_anatomy_bone"), NearestBones[S].ToString()); Spheres.Add(MakeShared<FJsonValueObject>(Item)); MinClearance = FMath::Min(MinClearance, Clearances[S]);
			}
			int32 Covered = 0; for (const FVector& Point : Points) { bool bCovered = false; for (const auto& Sphere : Geometry.SphereElems) bCovered |= (Point - Sphere.Center).SizeSquared() <= Sphere.Radius * Sphere.Radius; Covered += bCovered; }
			Row->SetArrayField(TEXT("spheres"), Spheres); Row->SetNumberField(TEXT("covered_dominant_vertices"), Covered); Row->SetNumberField(TEXT("minimum_ref_shape_anatomy_clearance_cm"), MinClearance); ChosenCenters.Add(BodyIndex, Points[Safe[First]]); ExpectedGeometry.Add(BodyIndex, Geometry); continue;
		}
		for (int32 Candidate = 0; Candidate < Points.Num(); ++Candidate)
		{
			const FVector Center = Points[Candidate], A = IronUnit.TransformPosition(Center - Axis * (.5 * Capsule.Length)), B = IronUnit.TransformPosition(Center + Axis * (.5 * Capsule.Length)); double Clearance = DBL_MAX; FName Nearest;
			for (const auto& Shape : Anatomy)
			{
				FVector ClosestIron, ClosestBody; FMath::SegmentDistToSegmentSafe(A, B, Shape.Transform.TransformPosition(FVector(0., 0., -.5 * Shape.Length)), Shape.Transform.TransformPosition(FVector(0., 0., .5 * Shape.Length)), ClosestIron, ClosestBody);
				const double Phi = (ClosestIron - ClosestBody).Size() - Capsule.Radius - Shape.Radius; if (Phi < Clearance) { Clearance = Phi; Nearest = Shape.Bone; }
			}
			if (!TestTrue(TEXT("Finite exact candidate capsule/anatomy clearance"), FMath::IsFinite(Clearance))) return false; if (Clearance < 0.) continue; ++Feasible;
			int32 Covered = 0; for (const FVector& Point : Points) { const FVector Delta = Point - Center; const double Along = FMath::Clamp(FVector::DotProduct(Delta, Axis), -.5 * Capsule.Length, .5 * Capsule.Length); Covered += (Delta - Axis * Along).SizeSquared() <= Capsule.Radius * Capsule.Radius; }
			const double Shift = (Center - Capsule.Center).SizeSquared(); if (Covered > BestCovered || (Covered == BestCovered && Shift < BestShift)) { Best = Candidate; BestCovered = Covered; BestShift = Shift; BestClearance = Clearance; BestAnatomy = Nearest; }
		}
		auto Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("bone"), Bone.ToString()); Row->SetObjectField(TEXT("reference_basis_audit"), Basis); Row->SetNumberField(TEXT("dominant_support_count"), Points.Num()); Row->SetNumberField(TEXT("feasible_actual_vertex_centers"), Feasible); Row->SetNumberField(TEXT("selected_vertex_order"), Best); Row->SetNumberField(TEXT("covered_dominant_vertices"), BestCovered); Rows.Add(MakeShared<FJsonValueObject>(Row));
		if (!TestTrue(TEXT("A supported capsule center clears every existing anatomy capsule; no fallback authoring"), Best != INDEX_NONE)) { Report->SetStringField(TEXT("failure"), TEXT("No feasible actual dominant vertex center; asset unchanged.")); return Finish(false); }
		ChosenCenters.Add(BodyIndex, Points[Best]); ExpectedGeometry.Add(BodyIndex, Body->AggGeom); ExpectedGeometry[BodyIndex].SphylElems[0].Center = Points[Best];
		auto VectorField = [&](const TCHAR* Name, const FVector& V) { TArray<TSharedPtr<FJsonValue>> Values; for (double N : {V.X, V.Y, V.Z}) Values.Add(MakeShared<FJsonValueNumber>(N)); Row->SetArrayField(Name, Values); };
		VectorField(TEXT("before_center_bone_local_cm"), Capsule.Center); VectorField(TEXT("candidate_center_bone_local_cm"), Points[Best]); Row->SetNumberField(TEXT("center_shift_cm"), FMath::Sqrt(BestShift)); Row->SetNumberField(TEXT("minimum_ref_shape_anatomy_clearance_cm"), BestClearance); Row->SetStringField(TEXT("nearest_anatomy_bone"), BestAnatomy.ToString());
	}
	// Read-only mode changes only a transient duplicate. Center mode retains principal
	// moments; sparse mode reports its geometry-derived CoM/inertia without that claim.
	UPhysicsAsset* CandidatePA = DuplicateObject<UPhysicsAsset>(PA, GetTransientPackage());
	for (const auto& Pair : ChosenCenters) { if (!TestTrue(TEXT("Candidate body is a distinct transient copy"), CandidatePA->SkeletalBodySetups[Pair.Key] != PA->SkeletalBodySetups[Pair.Key])) return false; CandidatePA->SkeletalBodySetups[Pair.Key]->AggGeom = ExpectedGeometry[Pair.Key]; if (bSparse) CandidatePA->SkeletalBodySetups[Pair.Key]->DefaultInstance.InertiaTensorScale = FVector::OneVector; CandidatePA->SkeletalBodySetups[Pair.Key]->InvalidatePhysicsData(); }
	auto* Probe = NewObject<USkeletalMeshComponent>(); Probe->SetSkeletalMesh(Mesh); TArray<FBodyInstance*> BeforeInstances, CandidateInstances; Probe->InstantiatePhysicsAssetBodiesRefPose(*PA, BeforeInstances); Probe->InstantiatePhysicsAssetBodiesRefPose(*CandidatePA, CandidateInstances); bool bValid = true;
	for (const auto& Value : Rows)
	{
		auto Row = Value->AsObject(); const int32 Index = PA->FindBodyIndex(FName(*Row->GetStringField(TEXT("bone")))); const auto Before = ImmediatePhysics::MakeDynamicActorSetup(BeforeInstances[Index], FTransform::Identity), After = ImmediatePhysics::MakeDynamicActorSetup(CandidateInstances[Index], FTransform::Identity);
		TArray<double> BeforeI{double(Before.Inertia.X), double(Before.Inertia.Y), double(Before.Inertia.Z)}, AfterI{double(After.Inertia.X), double(After.Inertia.Y), double(After.Inertia.Z)}; BeforeI.Sort(); AfterI.Sort(); double Error = 0.; for (int32 I = 0; I < 3; ++I) Error = FMath::Max(Error, FMath::Abs(BeforeI[I] - AfterI[I]) / BeforeI[I]);
		bValid &= TestTrue(TEXT("Fresh candidate preserves mass and remains finite; principal preservation applies only to Center mode"), FMath::IsFinite(double(After.Mass)) && After.Mass > 0. && !FVector(After.Inertia).ContainsNaN() && AfterI[0] > 0. && !After.CoMTransform.ContainsNaN() && FMath::Abs(double(After.Mass - Before.Mass)) / double(Before.Mass) <= UE_DOUBLE_KINDA_SMALL_NUMBER && (bSparse || Error <= UE_DOUBLE_KINDA_SMALL_NUMBER));
		Row->SetNumberField(TEXT("before_mass_kg"), double(Before.Mass)); Row->SetNumberField(TEXT("candidate_mass_kg"), double(After.Mass)); Row->SetNumberField(TEXT("principal_moment_relative_max_error"), Error); Row->SetNumberField(TEXT("technical_relative_tolerance"), double(UE_DOUBLE_KINDA_SMALL_NUMBER)); Row->SetStringField(TEXT("before_principal_kg_cm2"), FString::Printf(TEXT("%.12g/%.12g/%.12g"), BeforeI[0], BeforeI[1], BeforeI[2])); Row->SetStringField(TEXT("candidate_principal_kg_cm2"), FString::Printf(TEXT("%.12g/%.12g/%.12g"), AfterI[0], AfterI[1], AfterI[2])); Row->SetStringField(TEXT("before_com"), Before.CoMTransform.ToString()); Row->SetStringField(TEXT("candidate_com"), After.CoMTransform.ToString());
	}
	for (auto* BI : BeforeInstances) { if (BI->IsValidBodyInstance()) BI->TermBody(true); delete BI; } for (auto* BI : CandidateInstances) { if (BI->IsValidBodyInstance()) BI->TermBody(true); delete BI; } if (!bValid) return Finish(false);
	if (bApply) { PA->Modify(); for (const auto& Pair : ChosenCenters) { USkeletalBodySetup* Body = PA->SkeletalBodySetups[Pair.Key]; Body->Modify(); Body->AggGeom = ExpectedGeometry[Pair.Key]; if (bSparse) Body->DefaultInstance.InertiaTensorScale = FVector::OneVector; Body->InvalidatePhysicsData(); } }
	if (!TestTrue(TEXT("Body and constraint array counts preserved"), PA->SkeletalBodySetups.Num() == BeforeBodies.Num() && PA->ConstraintSetup.Num() == BeforeJoints.Num())) return Finish(false);
	for (int32 I = 0; I < PA->SkeletalBodySetups.Num(); ++I)
	{
		auto Actual = Snapshot(PA->SkeletalBodySetups[I]); if (bApply && ChosenCenters.Contains(I))
		{
			bValid &= TestTrue(TEXT("Full Iron geometry exactly matches the approved candidate"), FKAggregateGeom::StaticStruct()->CompareScriptStruct(&PA->SkeletalBodySetups[I]->AggGeom, &ExpectedGeometry[I], 0));
			Actual->SetObjectField(TEXT("aggGeom"), BeforeBodies[I]->GetObjectField(TEXT("aggGeom")));
			if (bSparse) { bValid &= TestTrue(TEXT("Only legacy inertia scale is reset"), PA->SkeletalBodySetups[I]->DefaultInstance.InertiaTensorScale == FVector::OneVector); Actual->GetObjectField(TEXT("defaultInstance"))->SetObjectField(TEXT("inertiaTensorScale"), BeforeBodies[I]->GetObjectField(TEXT("defaultInstance"))->GetObjectField(TEXT("inertiaTensorScale"))); }
		}
		bValid &= TestTrue(TEXT("Every body field unchanged after normalizing only approved Iron geometry/inertia changes"), SameJson(Actual, BeforeBodies[I]));
	}
	for (int32 I = 0; I < PA->ConstraintSetup.Num(); ++I) bValid &= TestTrue(TEXT("Every full constraint and saved default profile unchanged"), SameJson(Snapshot(PA->ConstraintSetup[I]), BeforeJoints[I]) && FConstraintProfileProperties::StaticStruct()->CompareScriptStruct(&PA->ConstraintSetup[I]->GetConstraintProfilePropertiesOrDefault(NAME_None), &BeforeDefaults[I], 0));
	// Instanced body objects are also exported inline in the asset snapshot. Their
	// complete contents were compared above, so normalize only this already-checked array.
	auto ActualPA = Snapshot(PA); ActualPA->SetField(TEXT("skeletalBodySetups"), BeforePA->Values[TEXT("skeletalBodySetups")]);
	bValid &= TestTrue(TEXT("Asset settings/solver and reflected arrays preserved"), SameJson(ActualPA, BeforePA) && bSnapshotsValid);
	Report->SetBoolField(TEXT("only_approved_changes_verified"), bValid); Report->SetNumberField(TEXT("modified_center_count"), bApply && !bSparse ? ChosenCenters.Num() : 0); Report->SetNumberField(TEXT("modified_sparse_geometry_count"), bApply && bSparse ? ChosenCenters.Num() : 0); Report->SetNumberField(TEXT("modified_inertia_scale_count"), bApply && bSparse ? ChosenCenters.Num() : 0); Report->SetBoolField(TEXT("asset_saved"), false);
	if (!bValid) return Finish(false); if (bApply) { const bool bSaved = Save(PA); Report->SetBoolField(TEXT("asset_saved"), bSaved); if (!TestTrue(TEXT("Only derived Leg PA saved once"), bSaved)) return Finish(false); }
	return Finish(true);
}
#endif
