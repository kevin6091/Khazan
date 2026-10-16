// Integration/visual capture for the isolated editor only; never a product runtime file.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Character/KZPlayer.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "AnimNodes/AnimNode_CopyPoseFromMesh.h"
#include "BoneControllers/AnimNode_RigidBody.h"
#include "Components/SkeletalMeshComponent.h"
#include "ClothCollisionSource.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/IConsoleManager.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Engine/GameViewportClient.h"
#include "UObject/UnrealType.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsSimulation.h"
#include "Physics/ImmediatePhysics/ImmediatePhysicsActorHandle.h"
#include "Chaos/ParticleHandle.h"
#include "Chaos/Collision/CollisionVisitor.h"
#include "Chaos/Collision/CollisionConstraintAllocator.h"
#include "Chaos/Collision/PBDCollisionConstraint.h"
#include "Chaos/PBDCollisionConstraints.h"
#include "Chaos/ImplicitObject.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"

namespace KZPlayerPartsPIE
{
const TCHAR* Parts[] = {TEXT("Torso"), TEXT("Shoes"), TEXT("Leg"), TEXT("Hair"), TEXT("Arm")};
class FRun : public IAutomationLatentCommand
{
public:
	explicit FRun(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 90.) {}
	virtual bool Update() override
	{
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("PlayerParts PIE watchdog")); Cleanup(); return true; }
		if (!Player.IsValid())
		{
			for (const FWorldContext& C : GEngine->GetWorldContexts())
				if (C.WorldType == EWorldType::PIE && C.World())
					for (TActorIterator<AKZPlayer> It(C.World()); It; ++It)
						if (It->GetController()) { Player = *It; Start = C.World()->GetTimeSeconds(); break; }
			return false;
		}
		const float Time = Player->GetWorld()->GetTimeSeconds() - Start;
		if (Stage >= 3) { SampleContacts(); SampleHairMotion(); SampleClothMotion(); }
		if (bWaistJitterProbe || bWaistDisableIronContact) SampleWaistJitter(Time);
		if (Time < Next) return false;
		switch (Stage++)
		{
		case 0:
		{
			SavedControl = Player->GetController()->GetControlRotation();
			Player->GetController()->SetControlRotation(FRotator(0., Player->GetActorRotation().Yaw + 180., 0.));
			const bool bClothView = FParse::Param(FCommandLine::Get(), TEXT("PlayerClothView"));
			const bool bClothFrontView = bClothView && FParse::Param(FCommandLine::Get(), TEXT("PlayerClothFrontView"));
			if (bClothView || FParse::Param(FCommandLine::Get(), TEXT("PlayerHairCloseView")))
			{
				CameraArm = Player->FindComponentByClass<USpringArmComponent>();
				if (CameraArm.IsValid())
				{
					SavedArmLength = CameraArm->TargetArmLength; SavedSocketOffset = CameraArm->SocketOffset;
					SavedArmRotation = CameraArm->GetRelativeRotation(); SavedUsePawnControlRotation = CameraArm->bUsePawnControlRotation;
					// Isolated screenshot framing only; never saved to BP/game settings.
					// Assistant-selected temporary QA framing, not original gameplay metadata.
					CameraArm->TargetArmLength = bClothView ? 450.f : 220.f; CameraArm->SocketOffset.Z += bClothView ? 0.f : 50.f;
					// Keep the SAME control rotation/input as the baseline. Only the
					// temporary camera arm changes, so framing cannot alter facing policy.
					CameraArm->bUsePawnControlRotation = false; CameraArm->SetRelativeRotation(FRotator(-10., bClothFrontView ? 180. : 0., 0.));
					if (bClothView) Test->AddInfo(FString::Printf(TEXT("ClothQACamera temporaryAssistantFraming=1 front=%d armCm=%.3f socketAddedZCm=0 relativePitchDegrees=-10 relativeYawDegrees=%.3f gameplayControlAndInputUnchanged=1"), bClothFrontView, CameraArm->TargetArmLength, bClothFrontView ? 180. : 0.));
				}
			}
			RigidCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("p.RigidBodyNode"));
			SavedRigid = RigidCVar->GetInt(); RigidCVar->Set(0, ECVF_SetByConsole);
			if (bWaistJitterProbe)
			{
				WaistSimulationCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("p.RigidBodyNode.EnableSimulation"));
				SavedWaistSimulation = WaistSimulationCVar->GetInt(); WaistSimulationCVar->Set(0, ECVF_SetByConsole);
				Test->AddInfo(TEXT("WaistPhysicsBypass runtimeEnableSimulation=0 incomingCopyPose=1 actorStateRetained=1 resumeSettlingExcluded=1"));
			}
			ValidateComponents(); Next = Time + 1.f; break;
		}
		case 1:
			// Optional technical QA settling window; never a gameplay/asset tuning value.
			Snapshot(false); RigidCVar->Set(1, ECVF_SetByConsole); if (WaistSimulationCVar) WaistSimulationCVar->Set(1, ECVF_SetByConsole); Next = Time + (bWaistJitterProbe ? 6.f : 2.f); break;
		case 2:
			Snapshot(true);
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("PlayerOriginal_Idle.png"), false, false);
			Player->HandleInputMove(FVector2D(1., 0.), FRotator::ZeroRotator); Next = Time + 2.f; break;
		case 3:
			Snapshot(true); Player->HandleInputMove(FVector2D(0., 1.), FRotator::ZeroRotator);
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("PlayerOriginal_Moving.png"), false, false);
			Next = Time + 2.f; break;
		case 4:
			Snapshot(true); Player->HandleInputMoveReleased(); Next = Time + (bWaistJitterProbe ? 4.f : 1.f); break;
		case 5:
			Snapshot(true); CheckDynamics(); ReportContacts(); ReportHairMotion(); ReportClothMotion(); ReportWaistJitter(); Cleanup(); return true;
		}
		return false;
	}
private:
	void ValidateComponents()
	{
		Test->TestFalse(TEXT("Body component is not ragdoll"), Player->GetMesh()->IsSimulatingPhysics());
		Test->TestTrue(TEXT("Body PhysicsAsset loaded"), Player->GetMesh()->GetPhysicsAsset() != nullptr);
		for (const TCHAR* Part : Parts)
		{
			USkeletalMeshComponent* Found = nullptr;
			TArray<USkeletalMeshComponent*> Meshes; Player->GetComponents(Meshes);
			for (USkeletalMeshComponent* M : Meshes) if (M->GetFName() == FName(Part)) Found = M;
			if (!Test->TestNotNull(Part, Found)) continue;
			Components.Add(FName(Part), Found);
			Test->TestTrue(TEXT("Part attached to character mesh"), Found->GetAttachParent() == Player->GetMesh());
			Test->TestTrue(TEXT("Original part mesh"), Found->GetSkeletalMeshAsset()->GetName() == FString(TEXT("Player_Original_")) + Part);
			Test->TestTrue(TEXT("Original part PhysicsAsset"), Found->GetPhysicsAsset()->GetName() == FString(TEXT("Player_Original_")) + Part + TEXT("_PhysicsAsset"));
			Test->TestNull(TEXT("Independent part has no LeaderPose"), Found->LeaderPoseComponent.Get());
			Test->TestNotNull(TEXT("Part AnimInstance"), Found->GetAnimInstance());
			Test->TestTrue(TEXT("Scale inherits body exactly once"), Found->GetRelativeScale3D().Equals(FVector::OneVector, .0001));
			Test->AddInfo(FString::Printf(TEXT("Runtime part=%s mesh=%s physics=%s animation=%s collision=%d anyWorldSimulation=%d boundsExtent=%s"), Part, *Found->GetSkeletalMeshAsset()->GetPathName(), *Found->GetPhysicsAsset()->GetPathName(), *GetPathNameSafe(Found->GetAnimInstance()->GetClass()), int32(Found->GetCollisionEnabled()), Found->IsAnySimulatingPhysics(), *Found->Bounds.BoxExtent.ToString()));
			for (const FClothCollisionSource& Source : Found->GetClothCollisionSources())
			{
				Test->TestTrue(TEXT("Cloth source is this player's actual body component"), Source.SourceComponent.Get() == Player->GetMesh());
				Test->TestTrue(TEXT("Cloth source uses the actual body PhysicsAsset"), Source.SourcePhysicsAsset.Get() == Player->GetMesh()->GetPhysicsAsset());
			}
		}
	}
	void Snapshot(bool bPhysics)
	{
		for (const TPair<FName, TWeakObjectPtr<USkeletalMeshComponent>>& Entry : Components)
		{
			USkeletalMeshComponent* Mesh = Entry.Value.Get();
			if (!Mesh) continue;
			Mesh->HandleExistingParallelEvaluationTask(true, true);
			float MaxDifference = 0.f;
			// QA envelope derives from the parent's current bounds, not gameplay tuning.
			const float ParentEnvelope = 2.f * Player->GetMesh()->Bounds.BoxExtent.Size();
			Test->TestTrue(TEXT("Part remains within character-sized bounds"), Mesh->Bounds.BoxExtent.Size() < ParentEnvelope);
			for (const USkeletalBodySetup* Body : Mesh->GetPhysicsAsset()->SkeletalBodySetups)
			{
				const int32 Index = Mesh->GetBoneIndex(Body->BoneName);
				if (Index == INDEX_NONE) continue;
				const FTransform Local = Mesh->GetBoneTransform(Index).GetRelativeTransform(Mesh->GetComponentTransform());
				Test->TestFalse(TEXT("Part bone finite"), Local.ContainsNaN());
				const FTransform WorldBone = Mesh->GetBoneTransform(Index);
				Test->TestTrue(TEXT("Unit bone world scale preserved"), WorldBone.GetScale3D().Equals(FVector::OneVector, .001));
				Test->TestTrue(TEXT("Physics bone stays near character"), FVector::Distance(WorldBone.GetLocation(), Player->GetMesh()->GetComponentLocation()) < ParentEnvelope);
				const FString Key = Entry.Key.ToString() + TEXT("/") + Body->BoneName.ToString();
				if (!bPhysics) Baseline.Add(Key, Local);
				else if (Body->PhysicsType == PhysType_Simulated && Baseline.Contains(Key))
				{
					const float Angle = FMath::RadiansToDegrees(Local.GetRotation().AngularDistance(Baseline[Key].GetRotation()));
					MaxDifference = FMath::Max(MaxDifference, Angle);
				}
				if (Body->PhysicsType != PhysType_Simulated)
				{
					const int32 MasterIndex = Player->GetMesh()->GetBoneIndex(Body->BoneName);
					if (MasterIndex != INDEX_NONE)
					{
						const float Error = FVector::Distance(Mesh->GetBoneTransform(Index).GetLocation(), Player->GetMesh()->GetBoneTransform(MasterIndex).GetLocation());
						Test->TestTrue(TEXT("Copied anchor follows current parent pose (cm)"), Error < .1f);
					}
				}
			}
			DynamicAngles.FindOrAdd(Entry.Key) = FMath::Max(DynamicAngles.FindRef(Entry.Key), MaxDifference);
			Test->AddInfo(FString::Printf(TEXT("Pose part=%s physics=%d maxRelativeRotationDegrees=%.6f rootScale=%s boundsExtent=%s"), *Entry.Key.ToString(), bPhysics, MaxDifference, *Mesh->GetComponentSpaceTransforms()[0].GetScale3D().ToString(), *Mesh->Bounds.BoxExtent.ToString()));
			if (bPhysics)
				for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It)
					if (It->Struct == FAnimNode_RigidBody::StaticStruct())
					{
						auto* Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance());
						auto* Simulation = Rigid->GetSimulation();
						Test->TestNotNull(TEXT("RigidBody simulation exists"), Simulation);
						if (!Simulation) continue;
						int32 ExternalBodies = 0;
						TSet<int32> MatchedAnatomy;
						for (int32 ActorIndex = 0; ActorIndex < Simulation->NumActors(); ++ActorIndex)
						{
							const auto* Actor = Simulation->GetActorHandle(ActorIndex);
							if (Actor->IsSimulated()) Test->TestEqual(TEXT("One thin physical shape; no re-enabled mass-only shape"), Actor->GetParticle()->ShapesArray().Num(), 1);
							const auto* Geometry = Actor->GetParticle()->GetGeometry();
							const FVector Extent = FVector(Geometry->BoundingBox().Extents());
							Test->TestTrue(TEXT("RigidBody collision shape has character-scale dimensions"), Extent.Size() < ParentEnvelope);
							if (Actor->GetName().IsNone())
							{
								++ExternalBodies;
								const UPhysicsAsset* Anatomy = Player->GetMesh()->GetPhysicsAsset();
								int32 ClosestBody = INDEX_NONE; double Distance = TNumericLimits<double>::Max();
								for (int32 BodyIndex = 0; BodyIndex < Anatomy->SkeletalBodySetups.Num(); ++BodyIndex)
								{
									const FName Bone = Anatomy->SkeletalBodySetups[BodyIndex]->BoneName;
									const double Candidate = FVector::Distance(Actor->GetWorldTransform().GetLocation(), Player->GetMesh()->GetBoneTransform(Player->GetMesh()->GetBoneIndex(Bone)).GetLocation());
									if (Candidate < Distance) { Distance = Candidate; ClosestBody = BodyIndex; }
								}
								Test->TestTrue(TEXT("External collider follows current anatomical bone (cm)"), Distance < .1);
								Test->TestTrue(TEXT("External body is kinematic"), Actor->GetIsKinematic());
								Test->TestTrue(TEXT("External body has collision"), Actor->GetHasCollision());
								if (ClosestBody != INDEX_NONE)
								{
									MatchedAnatomy.Add(ClosestBody);
									const USkeletalBodySetup* Body = Anatomy->SkeletalBodySetups[ClosestBody];
									Test->TestTrue(TEXT("External geometry retains anatomical cm dimensions"), Extent.Equals(Body->AggGeom.CalcAABB(FTransform::Identity).GetSize(), .1));
									if (Stage == 3) Test->AddInfo(FString::Printf(TEXT("ExternalBody part=%s bone=%s dimensionsCm=%s poseErrorCm=%.6f"), *Entry.Key.ToString(), *Body->BoneName.ToString(), *Extent.ToString(), Distance));
								}
								continue;
							}
							const UPhysicsAsset* SimulationAsset = Rigid->OverridePhysicsAsset ? Rigid->OverridePhysicsAsset.Get() : Mesh->GetPhysicsAsset();
							const int32 SourceIndex = SimulationAsset->FindBodyIndex(Actor->GetName());
							Test->TestTrue(TEXT("RigidBody actor maps to saved simulation PA body"), SourceIndex != INDEX_NONE);
							if (SourceIndex != INDEX_NONE)
							{
								const FVector OriginalSize = SimulationAsset->SkeletalBodySetups[SourceIndex]->AggGeom.CalcAABB(FTransform::Identity).GetSize();
								Test->TestTrue(TEXT("RigidBody dimensions match saved PA shape (cm)"), Extent.Equals(OriginalSize, .1));
							}
							if (Stage == 3) Test->AddInfo(FString::Printf(TEXT("RigidShape part=%s bone=%s simulated=%d dimensionsCm=%s world=%s"), *Entry.Key.ToString(), *Actor->GetName().ToString(), Actor->IsSimulated(), *Extent.ToString(), *Actor->GetWorldTransform().ToString()));
						}
						if (Rigid->bUseExternalClothCollision)
						{
							Test->TestEqual(TEXT("All anatomical colliders registered exactly once"), ExternalBodies, Player->GetMesh()->GetPhysicsAsset()->SkeletalBodySetups.Num());
							Test->TestEqual(TEXT("All anatomical bones covered"), MatchedAnatomy.Num(), ExternalBodies);
							Test->TestEqual(TEXT("One actual body collision source"), Mesh->GetClothCollisionSources().Num(), 1);
						}
						if (Stage >= 3 && Stage <= 5 && FParse::Param(FCommandLine::Get(), TEXT("PlayerClothSurfaceProbe")) && (Entry.Key == FName(TEXT("Torso")) || Entry.Key == FName(TEXT("Leg")))) SampleClothSurface(Entry.Key, Mesh, Rigid, Simulation);
					}
		}
	}
	void SampleClothSurface(FName Part, USkeletalMeshComponent* Mesh, FAnimNode_RigidBody* Rigid, ImmediatePhysics::FSimulation* Simulation)
	{
		// Read the current final bone pose without GetCPUSkinnedVertices(), which
		// refreshes bones and switches render state. This is linear LOD0 skinning;
		// morph targets, material WPO, triangle interiors and sweep history are out of scope.
		const auto* RenderData = Mesh->GetSkeletalMeshRenderData();
		const auto* Weights = Mesh->GetSkinWeightBuffer(0);
		if (Rigid->SimulationSpace != ESimulationSpace::WorldSpace || !Rigid->GetPhysicsAsset() || !RenderData || !RenderData->LODRenderData.IsValidIndex(0) || !Weights) { Test->AddInfo(TEXT("ClothSurfaceProbe skipped: unavailable world-space LOD0 inputs")); return; }
		const auto& LOD = RenderData->LODRenderData[0];
		if (!LOD.StaticVertexBuffers.PositionVertexBuffer.GetVertexData() || !Weights->GetDataVertexBuffer()->GetWeightData()) { Test->AddInfo(TEXT("ClothSurfaceProbe skipped: CPU vertex inputs unavailable")); return; }
		TSet<int32> SimulatedBones;
		for (const USkeletalBodySetup* Body : Rigid->GetPhysicsAsset()->SkeletalBodySetups) if (Body->PhysicsType == PhysType_Simulated && IsClothBone(Body->BoneName)) SimulatedBones.Add(Mesh->GetBoneIndex(Body->BoneName));
		TArray<FMatrix44f> RefToLocal; Mesh->GetCurrentRefToLocalMatrices(RefToLocal, 0);
		TArray<FVector3f> Positions; USkinnedMeshComponent::ComputeSkinnedPositions(Mesh, Positions, RefToLocal, LOD, *Weights);
		TArray<int32> ColliderIndices; TArray<FTransform> ColliderWorld;
		for (int32 A = 0; A < Simulation->NumActors(); ++A) { const auto* Actor = Simulation->GetActorHandle(A); if (Actor->GetName().IsNone() && Actor->GetHasCollision() && Actor->GetParticle()->GetGeometry()) { ColliderIndices.Add(A); ColliderWorld.Add(Actor->GetWorldTransform()); } }
		if (ColliderIndices.IsEmpty()) { Test->AddInfo(TEXT("ClothSurfaceProbe skipped: no external anatomy geometry")); return; }
		const bool bReferenceRequested = Stage == 3 && FParse::Param(FCommandLine::Get(), TEXT("PlayerClothSurfaceReference"));
		bool bReferenceReady = bReferenceRequested; TArray<FTransform> ColliderReference; TSet<int32> ReferenceBodyMatches;
		const auto& AnatomyRef = Player->GetMesh()->GetSkeletalMeshAsset()->GetRefSkeleton(); TArray<FTransform> AnatomyUnit;
		if (bReferenceRequested)
		{
			const double Wrapper = AnatomyRef.GetRefBonePose()[0].GetScale3D().X;
			for (int32 B = 0; B < AnatomyRef.GetNum(); ++B) { FTransform Pose = AnatomyRef.GetRefBonePose()[B]; if (B > 0) Pose = Pose * AnatomyUnit[AnatomyRef.GetParentIndex(B)]; AnatomyUnit.Add(Pose); }
			for (FTransform& Pose : AnatomyUnit) { Pose.SetTranslation(Pose.GetTranslation() / Wrapper); Pose.SetScale3D(FVector::OneVector); }
			const auto& AnatomyBodies = Player->GetMesh()->GetPhysicsAsset()->SkeletalBodySetups;
			for (int32 C = 0; C < ColliderIndices.Num(); ++C)
			{
				int32 Matches = 0, Match = INDEX_NONE;
				for (int32 B = 0; B < AnatomyBodies.Num(); ++B) { const int32 Bone = Player->GetMesh()->GetBoneIndex(AnatomyBodies[B]->BoneName); if (Bone != INDEX_NONE && FVector::Distance(ColliderWorld[C].GetLocation(), Player->GetMesh()->GetBoneTransform(Bone).GetLocation()) < .1) { ++Matches; Match = B; } }
				if (Matches != 1 || ReferenceBodyMatches.Contains(Match)) { bReferenceReady = false; break; }
				ReferenceBodyMatches.Add(Match); ColliderReference.Add(AnatomyUnit[AnatomyRef.FindBoneIndex(AnatomyBodies[Match]->BoneName)]);
			}
			bReferenceReady &= ReferenceBodyMatches.Num() == AnatomyBodies.Num() && ColliderReference.Num() == ColliderIndices.Num();
			if (!bReferenceReady) Test->AddInfo(TEXT("ClothSurfaceReference skipped: external anatomy mapping is not unique and complete within existing 0.1cm pose tolerance"));
		}
		int32 Samples = 0, Inside = 0, WorstVertex = INDEX_NONE, WorstActor = INDEX_NONE;
		double MinimumPhi = TNumericLimits<double>::Max(), DepthSquared = 0.; bool bFinite = true; FVector WorstWorld = FVector::ZeroVector;
		int32 DominantSamples = 0, DominantInside = 0, DominantWorstVertex = INDEX_NONE, DominantWorstBone = INDEX_NONE, WorstBone = INDEX_NONE;
		uint32 WorstWeight = 0, WorstTotalWeight = 0, WorstClothWeight = 0, WorstSimClothWeight = 0, WorstTies = 0;
		double DominantMinimumPhi = TNumericLimits<double>::Max(), DominantDepthSquared = 0.;
		int32 ReferenceInside = 0, DominantReferenceInside = 0, NewlyInside = 0, DominantNewlyInside = 0; double ReferenceMinimumPhi = TNumericLimits<double>::Max(), ReferencePhiAtCurrentWorst = 0.;
		const auto& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
		for (const auto& Section : LOD.RenderSections)
			for (uint32 V = Section.BaseVertexIndex; V < Section.BaseVertexIndex + Section.NumVertices; ++V)
			{
				uint32 MaximumWeight = 0, TotalWeight = 0, ClothWeight = 0, SimClothWeight = 0, MaximumTies = 0; int32 DominantBone = INDEX_NONE;
				for (uint32 I = 0; I < Weights->GetMaxBoneInfluences(); ++I)
				{
					const uint32 B = Weights->GetBoneIndex(V, I), W = Weights->GetBoneWeight(V, I); if (!W || !Section.BoneMap.IsValidIndex(B)) continue;
					const int32 Bone = Section.BoneMap[B]; TotalWeight += W; if (IsClothBone(Ref.GetBoneName(Bone))) ClothWeight += W; if (SimulatedBones.Contains(Bone)) SimClothWeight += W;
					if (W > MaximumWeight) { MaximumWeight = W; DominantBone = Bone; MaximumTies = 1; }
					else if (W == MaximumWeight) { ++MaximumTies; DominantBone = FMath::Min(DominantBone, Bone); }
				}
				if (!SimClothWeight) continue; // Excludes attachment-only vertices; no arbitrary weight cutoff.
				const FVector World = Mesh->GetComponentTransform().TransformPosition(FVector(Positions[V]));
				double Phi = TNumericLimits<double>::Max(); int32 ClosestActor = INDEX_NONE;
				for (int32 C = 0; C < ColliderIndices.Num(); ++C)
				{
					// Chaos particle geometry uses actor local space, not center-of-mass space.
					Chaos::FVec3 Normal;
					const double Candidate = Simulation->GetActorHandle(ColliderIndices[C])->GetParticle()->GetGeometry()->PhiWithNormal(Chaos::FVec3(ColliderWorld[C].InverseTransformPosition(World)), Normal);
					bFinite &= FMath::IsFinite(Candidate);
					if (Candidate < Phi) { Phi = Candidate; ClosestActor = ColliderIndices[C]; }
				}
				bFinite &= !World.ContainsNaN(); ++Samples;
				double ReferencePhi = TNumericLimits<double>::Max();
				if (bReferenceReady)
				{
					// Imported reference vertex and body frames share unit mesh-space cm.
					const FVector ReferencePosition = FVector(LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V)) / Ref.GetRefBonePose()[0].GetScale3D().X;
					for (int32 C = 0; C < ColliderIndices.Num(); ++C) { Chaos::FVec3 Normal; ReferencePhi = FMath::Min(ReferencePhi, double(Simulation->GetActorHandle(ColliderIndices[C])->GetParticle()->GetGeometry()->PhiWithNormal(Chaos::FVec3(ColliderReference[C].InverseTransformPosition(ReferencePosition)), Normal))); }
					bFinite &= FMath::IsFinite(ReferencePhi); ReferenceMinimumPhi = FMath::Min(ReferenceMinimumPhi, ReferencePhi); if (ReferencePhi < 0.) ++ReferenceInside; if (Phi < 0. && ReferencePhi >= 0.) ++NewlyInside;
					if (SimulatedBones.Contains(DominantBone)) { if (ReferencePhi < 0.) ++DominantReferenceInside; if (Phi < 0. && ReferencePhi >= 0.) ++DominantNewlyInside; }
				}
				const double Depth = FMath::Max(0., -Phi); DepthSquared += Depth * Depth; if (Phi < 0.) ++Inside;
				if (Phi < MinimumPhi) { MinimumPhi = Phi; WorstVertex = V; WorstActor = ClosestActor; WorstWorld = World; WorstBone = DominantBone; WorstWeight = MaximumWeight; WorstTotalWeight = TotalWeight; WorstClothWeight = ClothWeight; WorstSimClothWeight = SimClothWeight; WorstTies = MaximumTies; ReferencePhiAtCurrentWorst = ReferencePhi; }
				if (SimulatedBones.Contains(DominantBone))
				{
					++DominantSamples; DominantDepthSquared += Depth * Depth; if (Phi < 0.) ++DominantInside;
					if (Phi < DominantMinimumPhi) { DominantMinimumPhi = Phi; DominantWorstVertex = V; DominantWorstBone = DominantBone; }
				}
			}
		Test->AddInfo(FString::Printf(TEXT("ClothSurfaceProbe part=%s stage=%d timeSeconds=%.6f scope=CurrentPoseLinearLOD0PositiveDirectSimulatedClothWeightsAgainstExternalAnatomyImplicitPhiCm externalActors=%d sampledVertices=%d insideVertices=%d minimumPhiCm=%.6f penetrationPeakCm=%.6f penetrationRmsAcrossSampledVerticesCm=%.6f finite=%d worstVertex=%d worstExternalActor=%d worstWorldPositionCm=%s"), *Part.ToString(), Stage, Player->GetWorld()->GetTimeSeconds(), ColliderIndices.Num(), Samples, Inside, Samples ? MinimumPhi : 0., Samples ? FMath::Max(0., -MinimumPhi) : 0., FMath::Sqrt(DepthSquared / FMath::Max(1, Samples)), bFinite, WorstVertex, WorstActor, *WorstWorld.ToString()));
		// Fractions use this vertex's observed raw weight sum, not an assumed quantization maximum.
		Test->AddInfo(FString::Printf(TEXT("ClothSurfaceWeights part=%s stage=%d dominantTiePolicy=LowestSkeletonBoneIndex worstVertex=%d worstDominantBone=%s worstDominantWeightRaw=%u worstDominantWeightFraction=%.6f worstMaximumWeightTies=%u worstTotalWeightRaw=%u worstAllClothWeightFraction=%.6f worstDirectSimClothWeightFraction=%.6f dominantDirectSimVertices=%d dominantDirectSimInsideVertices=%d dominantDirectSimMinimumPhiCm=%.6f dominantDirectSimPenetrationPeakCm=%.6f dominantDirectSimPenetrationRmsAcrossSubsetCm=%.6f dominantDirectSimWorstVertex=%d dominantDirectSimWorstBone=%s"), *Part.ToString(), Stage, WorstVertex, WorstBone != INDEX_NONE ? *Ref.GetBoneName(WorstBone).ToString() : TEXT("None"), WorstWeight, double(WorstWeight) / FMath::Max(1u, WorstTotalWeight), WorstTies, WorstTotalWeight, double(WorstClothWeight) / FMath::Max(1u, WorstTotalWeight), double(WorstSimClothWeight) / FMath::Max(1u, WorstTotalWeight), DominantSamples, DominantInside, DominantSamples ? DominantMinimumPhi : 0., DominantSamples ? FMath::Max(0., -DominantMinimumPhi) : 0., FMath::Sqrt(DominantDepthSquared / FMath::Max(1, DominantSamples)), DominantWorstVertex, DominantWorstBone != INDEX_NONE ? *Ref.GetBoneName(DominantWorstBone).ToString() : TEXT("None")));
		if (bReferenceReady) Test->AddInfo(FString::Printf(TEXT("ClothSurfaceReference part=%s stage=%d scope=ImportedLOD0ReferenceSkinAgainstSame18ProxyGeometryUnitCm uniqueMappedBodies=%d sampledVertices=%d referenceInsideVertices=%d currentInsideVertices=%d currentNewlyInsideVertices=%d referenceMinimumPhiCm=%.6f currentMinimumPhiCm=%.6f currentWorstVertex=%d referencePhiAtCurrentWorstCm=%.6f currentPhiAtCurrentWorstCm=%.6f dominantDirectSimVertices=%d dominantReferenceInsideVertices=%d dominantCurrentInsideVertices=%d dominantCurrentNewlyInsideVertices=%d finite=%d"), *Part.ToString(), Stage, ReferenceBodyMatches.Num(), Samples, ReferenceInside, Inside, NewlyInside, Samples ? ReferenceMinimumPhi : 0., Samples ? MinimumPhi : 0., WorstVertex, ReferencePhiAtCurrentWorst, Samples ? MinimumPhi : 0., DominantSamples, DominantReferenceInside, DominantInside, DominantNewlyInside, bFinite));
	}
	void SampleContacts()
	{
		for (const TPair<FName, TWeakObjectPtr<USkeletalMeshComponent>>& Entry : Components)
		{
			USkeletalMeshComponent* Mesh = Entry.Value.Get();
			if (!Mesh || !Mesh->GetAnimInstance()) continue;
			Mesh->HandleExistingParallelEvaluationTask(true, true);
			for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It)
				if (It->Struct == FAnimNode_RigidBody::StaticStruct())
				{
					auto* Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance());
					auto* Simulation = Rigid->GetSimulation(); if (!Simulation) continue;
					int32 Points = 0; double Impulse = 0.;
					Simulation->VisitCollisions([&](const ImmediatePhysics::FSimulation::FCollisionData& Contact)
					{
						Points += Contact.GetNumManifoldPoints();
						Impulse += Contact.GetCollisionAccumulatedImpulse().Size();
						for (int32 PointIndex = 0; PointIndex < Contact.GetNumManifoldPoints(); ++PointIndex)
						{
							float InitialPhi = 0.f; Chaos::FVec3 Normal, Point, Plane;
							Contact.GetManifoldPointData(PointIndex, InitialPhi, Normal, Point, Plane);
							// UE returns InitialPhi separately from contact locations transformed
							// by the current particle poses. Negative signed separation is overlap.
							const double CurrentSeparation = FVector::DotProduct(FVector(Point - Plane), FVector(Normal));
							if (!FMath::IsFinite(InitialPhi) || !FMath::IsFinite(CurrentSeparation)) { ++ContactNonFinite; continue; }
							double* InitialMinimum = ContactInitialMinimum.Find(Entry.Key);
							if (InitialMinimum) *InitialMinimum = FMath::Min(*InitialMinimum, double(InitialPhi));
							else ContactInitialMinimum.Add(Entry.Key, InitialPhi);
							double* CurrentMinimum = ContactCurrentMinimum.Find(Entry.Key);
							if (CurrentMinimum) *CurrentMinimum = FMath::Min(*CurrentMinimum, CurrentSeparation);
							else ContactCurrentMinimum.Add(Entry.Key, CurrentSeparation);
							const double Penetration = FMath::Max(0., -CurrentSeparation);
							ContactCurrentPenetrationSquared.FindOrAdd(Entry.Key) += Penetration * Penetration;
							++ContactDepthSamples.FindOrAdd(Entry.Key);
							if (Penetration > 0.) ++ContactOverlappingSamples.FindOrAdd(Entry.Key);
						}
					}, Chaos::ECollisionVisitorFlags::VisitDefault);
					ContactPoints.FindOrAdd(Entry.Key) += Points;
					ContactImpulse.FindOrAdd(Entry.Key) += Impulse;
					for (int32 ActorIndex = 0; ActorIndex < Simulation->NumActors(); ++ActorIndex)
					{
						const auto* Actor = Simulation->GetActorHandle(ActorIndex);
						if (!Actor->IsSimulated()) continue;
						if (!ObservedDamping.Contains(Entry.Key))
							Test->AddInfo(FString::Printf(TEXT("RuntimeDamping part=%s linear=%.6f angular=%.6f hasCollision=%d massKg=%.6f"), *Entry.Key.ToString(), double(Actor->GetLinearDamping()), double(Actor->GetAngularDamping()), Actor->GetHasCollision(), 1. / double(Actor->GetInverseMass())));
						ObservedDamping.Add(Entry.Key);
					}
				}
		}
	}
	// Optional test-local waist observations; phase durations are technical QA, not gameplay tuning.
	struct FWaistJitter
	{
		bool HasPrevious = false; double Time = 0., Square = 0., Peak = 0., PositionSquare = 0., ParentSquare = 0., ActorSquare = 0., Impulse = 0., DepthPeak = 0.;
		FQuat Joint, ActorJoint; FVector Position, LastStep = FVector::ZeroVector; FTransform Parent;
		TArray<double> Steps; int32 Reversals = 0, ActivePoints = 0;
	};
	void SampleWaistJitter(float Time)
	{
		auto* Mesh = Components.FindRef(FName(TEXT("Leg"))).Get(); if (!Mesh || !Mesh->GetAnimInstance()) return;
		Mesh->HandleExistingParallelEvaluationTask(true, true); // Join existing evaluation before observing or toggling its simulation.
		FAnimNode_RigidBody* Rigid = nullptr;
		for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It) if (It->Struct == FAnimNode_RigidBody::StaticStruct()) { Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance()); break; }
		if (!Rigid || !Rigid->GetPhysicsAsset()) return;
		auto* Simulation = Rigid->GetSimulation();
		TMap<FName, ImmediatePhysics::FActorHandle*> Named;
		TMap<const Chaos::FGeometryParticleHandle*, ImmediatePhysics::FActorHandle*> Actors;
		TMap<const Chaos::FGeometryParticleHandle*, int32> ActorIndices;
		if (Simulation) for (int32 I = 0; I < Simulation->NumActors(); ++I) { auto* A = Simulation->GetActorHandle(I); Named.Add(A->GetName(), A); Actors.Add(A->GetParticle(), A); ActorIndices.Add(A->GetParticle(), I); }
		if (Stage == 2 && bWaistDisableIronContact)
			for (const FName Bone : {FName(TEXT("B_Iron_01_01_R_Pelvis")), FName(TEXT("B_Iron_01_01_L_Pelvis"))})
				if (auto* A = Named.FindRef(Bone))
				{
					if (!WaistDisabledIron.Contains(Bone)) { WaistDisabledIron.Add(Bone, A->GetHasCollision()); Test->AddInfo(FString::Printf(TEXT("WaistDiagnosticIronContact bone=%s before=%d runtimeOnly=1 assetsUnchanged=1"), *Bone.ToString(), A->GetHasCollision())); }
					if (A->GetHasCollision()) Simulation->SetHasCollision(A, false); // Dirty pairs once; actor flag alone is insufficient.
				}
		const TCHAR* Phase = Stage == 1 ? TEXT("PhysicsOff") : Stage == 2 && Time >= Next - 3.f ? TEXT("IdleLate") : Stage == 5 && Time >= Next - 2.f ? TEXT("AfterReleaseLate") : nullptr;
		if (!bWaistJitterProbe || !Phase) return;
		// Read already published poses/actors only. Do not trigger another bone evaluation.
		const auto& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
		for (const USkeletalBodySetup* Body : Rigid->GetPhysicsAsset()->SkeletalBodySetups)
		{
			if (Body->PhysicsType != PhysType_Simulated) continue; // Includes the existing Iron2.
			const int32 Index = Ref.FindBoneIndex(Body->BoneName); if (Index == INDEX_NONE) continue;
			const FConstraintInstance* C = nullptr;
			for (const UPhysicsConstraintTemplate* Joint : Rigid->GetPhysicsAsset()->ConstraintSetup) if (Joint->DefaultInstance.ConstraintBone1 == Body->BoneName) { C = &Joint->DefaultInstance; break; }
			if (!C) continue;
			const int32 ParentIndex = Ref.FindBoneIndex(C->ConstraintBone2); if (ParentIndex == INDEX_NONE) continue;
			const FTransform Child = Mesh->GetBoneTransform(Index), Parent = Mesh->GetBoneTransform(ParentIndex);
			const FQuat Frame1 = C->GetRefFrame(EConstraintFrame::Frame1).GetRotation(), Frame2 = C->GetRefFrame(EConstraintFrame::Frame2).GetRotation();
			const FQuat Joint = ((Parent.GetRotation() * Frame2).Inverse() * (Child.GetRotation() * Frame1)).GetNormalized();
			const FVector Position = Child.GetRelativeTransform(Parent).GetLocation();
			auto* Actor = Named.FindRef(Body->BoneName); auto* ParentActor = Named.FindRef(C->ConstraintBone2);
			const bool ActorValid = Stage != 1 && Actor && ParentActor;
			const FQuat ActorJoint = ActorValid ? ((ParentActor->GetWorldTransform().GetRotation() * Frame2).Inverse() * (Actor->GetWorldTransform().GetRotation() * Frame1)).GetNormalized() : FQuat::Identity;
			const FString Key = FString(Phase) + TEXT("|") + Body->BoneName.ToString(); auto& M = WaistJitter.FindOrAdd(Key);
			if (M.HasPrevious && Time <= M.Time) continue; // Editor updates can repeat without another game/physics tick.
			int32 Points = 0; double MinSeparation = 0., Impulse = 0.;
			if (Stage != 1 && Actor) Actor->GetParticle()->ParticleCollisions().VisitConstCollisions([&](const Chaos::FPBDCollisionConstraint& Collision)
			{
				auto* A0 = Actors.FindRef(Collision.GetParticle0()); auto* A1 = Actors.FindRef(Collision.GetParticle1()); if (!A0 || !A1) return Chaos::ECollisionVisitorResult::Continue;
				int32 PairPoints = 0;
				for (int32 P = 0; P < Collision.NumManifoldPoints(); ++P) if (Collision.IsManifoldPointActive(P))
				{
					const auto& Contact = Collision.GetManifoldPoint(P).ContactPoint;
					const FVector Point = A0->GetWorldTransform().TransformPosition(Collision.GetShapeRelativeTransform0().TransformPosition(FVector(Contact.ShapeContactPoints[0])));
					const FVector Plane = A1->GetWorldTransform().TransformPosition(Collision.GetShapeRelativeTransform1().TransformPosition(FVector(Contact.ShapeContactPoints[1])));
					const FVector Normal = A1->GetWorldTransform().TransformVectorNoScale(Collision.GetShapeRelativeTransform1().TransformVectorNoScale(FVector(Contact.ShapeContactNormal)));
					const double Gap = FVector::DotProduct(Point - Plane, Normal); if (FMath::IsFinite(Gap)) { MinSeparation = FMath::Min(MinSeparation, Gap); ++Points; ++PairPoints; }
				}
				if (PairPoints)
				{
					const double PairImpulse = Collision.GetAccumulatedImpulse().Size(); Impulse += PairImpulse;
					auto* Other = A0 == Actor ? A1 : A0;
					const FString OtherName = Other->GetName().IsNone() ? FString::Printf(TEXT("ExternalActor%d"), ActorIndices.FindRef(Other->GetParticle())) : Other->GetName().ToString();
					const FString PairKey = Key + TEXT("|") + OtherName; WaistPairPoints.FindOrAdd(PairKey) += PairPoints; WaistPairImpulse.FindOrAdd(PairKey) += PairImpulse;
				}
				return Chaos::ECollisionVisitorResult::Continue;
			}, Chaos::ECollisionVisitorFlags::VisitDefault);
			double Step = 0., PositionStep = 0., ParentStep = 0., ParentPositionStep = 0., ActorStep = 0., Dt = 0.;
			if (M.HasPrevious && Time > M.Time)
			{
				Dt = Time - M.Time; FQuat Delta = M.Joint.Inverse() * Joint; Delta.EnforceShortestArcWith(FQuat::Identity);
				Step = FMath::RadiansToDegrees(Delta.GetAngle()); const FVector RotationStep = Delta.GetRotationAxis() * Step;
				if (FVector::DotProduct(M.LastStep, RotationStep) < 0.) ++M.Reversals; M.LastStep = RotationStep;
				PositionStep = FVector::Distance(Position, M.Position); ParentStep = FMath::RadiansToDegrees(M.Parent.GetRotation().AngularDistance(Parent.GetRotation())); ParentPositionStep = FVector::Distance(M.Parent.GetLocation(), Parent.GetLocation());
				ActorStep = ActorValid ? FMath::RadiansToDegrees(M.ActorJoint.AngularDistance(ActorJoint)) : 0.;
				M.Steps.Add(Step); M.Square += Step * Step; M.Peak = FMath::Max(M.Peak, Step); M.PositionSquare += PositionStep * PositionStep; M.ParentSquare += ParentStep * ParentStep; M.ActorSquare += ActorStep * ActorStep;
			}
			M.Impulse += Impulse; M.ActivePoints += Points; M.DepthPeak = FMath::Max(M.DepthPeak, -MinSeparation);
			WaistCsv += FString::Printf(TEXT("%s,%.9f,%.9f,%s,%s,%d,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%d,%d,%d,%.9f,%.9f,%.9f\n"), Phase, double(Time), Dt, *Body->BoneName.ToString(), *C->ConstraintBone2.ToString(), M.HasPrevious, Step, PositionStep, ParentStep, ParentPositionStep, ActorStep, Dt > 0. ? Step / Dt : 0., ActorValid ? FMath::RadiansToDegrees(Actor->GetAngularVelocity().Size()) : 0., ActorValid, Actor ? Actor->GetEnabled() : 0, Actor ? Actor->GetHasCollision() : 0, double(Points), MinSeparation, Impulse);
			M.HasPrevious = true; M.Time = Time; M.Joint = Joint; M.Position = Position; M.Parent = Parent; M.ActorJoint = ActorJoint;
		}
	}
	void ReportWaistJitter()
	{
		if (!bWaistJitterProbe) return;
		FString Label; FParse::Value(FCommandLine::Get(), TEXT("PlayerWaistProbeLabel="), Label); if (Label.IsEmpty()) Label = bWaistDisableIronContact ? TEXT("NoIronContact") : TEXT("Baseline");
		for (const TCHAR C : Label) if (!FChar::IsAlnum(C)) { Label = TEXT("InvalidLabel"); break; }
		const FString Path = FPaths::ProjectSavedDir() / (TEXT("PlayerWaistJitter_") + Label + TEXT(".csv"));
		const bool Saved = FFileHelper::SaveStringToFile(WaistCsv, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
		Test->AddInfo(FString::Printf(TEXT("WaistJitterScope label=%s csv=%s saved=%d noIronContactDiagnostic=%d idleLateSeconds=3 afterReleaseLateSeconds=2 publishedPoseOnly=1 contactDepth=CachedActivePointPlaneGapNotSkinPhi firstQuaternionExcluded=1"), *Label, *Path, Saved, bWaistDisableIronContact));
		for (auto& Entry : WaistJitter)
		{
			auto& M = Entry.Value; M.Steps.Sort(); const int32 N = M.Steps.Num(); const double Median = N ? (M.Steps[(N - 1) / 2] + M.Steps[N / 2]) * .5 : 0.;
			Test->AddInfo(FString::Printf(TEXT("WaistJitter bonePhase=%s samples=%d stepMedianDegrees=%.9f stepRmsDegrees=%.9f stepPeakDegrees=%.9f positionStepRmsCm=%.9f parentStepRmsDegrees=%.9f actorJointStepRmsDegrees=%.9f reversals=%d activeContactPoints=%d impulseSum=%.9f cachedPenetrationPeakCm=%.9f"), *Entry.Key, N, Median, FMath::Sqrt(M.Square / FMath::Max(1, N)), M.Peak, FMath::Sqrt(M.PositionSquare / FMath::Max(1, N)), FMath::Sqrt(M.ParentSquare / FMath::Max(1, N)), FMath::Sqrt(M.ActorSquare / FMath::Max(1, N)), M.Reversals, M.ActivePoints, M.Impulse, M.DepthPeak));
		}
		for (const auto& Entry : WaistPairPoints) Test->AddInfo(FString::Printf(TEXT("WaistContactPair pair=%s activePointSamples=%d impulseSum=%.9f"), *Entry.Key, Entry.Value, WaistPairImpulse.FindRef(Entry.Key)));
	}
	void RestoreWaistIronContact()
	{
		if (WaistDisabledIron.IsEmpty()) return;
		auto* Mesh = Components.FindRef(FName(TEXT("Leg"))).Get(); if (!Mesh || !Mesh->GetAnimInstance()) return;
		Mesh->HandleExistingParallelEvaluationTask(true, true);
		for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It) if (It->Struct == FAnimNode_RigidBody::StaticStruct())
			if (auto* Sim = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance())->GetSimulation())
				for (int32 I = 0; I < Sim->NumActors(); ++I) if (const bool* Original = WaistDisabledIron.Find(Sim->GetActorHandle(I)->GetName())) Sim->SetHasCollision(Sim->GetActorHandle(I), *Original);
	}
	void SampleHairMotion()
	{
		USkeletalMeshComponent* Hair = Components.FindRef(FName(TEXT("Hair"))).Get();
		if (!Hair) return;
		Hair->HandleExistingParallelEvaluationTask(true, true);
		const auto& Ref = Hair->GetSkeletalMeshAsset()->GetRefSkeleton();
		const int32 HeadIndex = Ref.FindBoneIndex(TEXT("Bip001-Head"));
		if (HairReference.IsEmpty())
		{
			for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
			{
				FTransform Pose = Ref.GetRefBonePose()[Index];
				if (Index > 0) Pose = Pose * HairReference[Ref.GetParentIndex(Index)];
				HairReference.Add(Pose);
			}
			const double Scale = Ref.GetRefBonePose()[0].GetScale3D().X;
			for (FTransform& Pose : HairReference) { Pose.SetTranslation(Pose.GetTranslation() / Scale); Pose.SetScale3D(FVector::OneVector); }
		}
		for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
		{
			const FString Name = Ref.GetBoneName(Index).ToString();
			if (!Name.StartsWith(TEXT("Hair_")) || Name.StartsWith(TEXT("Hair_BoneRoot"))) continue;
			const int32 Parent = Ref.GetParentIndex(Index);
			const FTransform Current = Hair->GetBoneTransform(Index);
			const FTransform Relative = Current.GetRelativeTransform(Hair->GetBoneTransform(Parent));
			const double Bend = FMath::RadiansToDegrees(Relative.GetRotation().AngularDistance(Ref.GetRefBonePose()[Index].GetRotation()));
			const FVector HeadPosition = Current.GetRelativeTransform(Hair->GetBoneTransform(HeadIndex)).GetLocation();
			const FVector ReferencePosition = HairReference[Index].GetRelativeTransform(HairReference[HeadIndex]).GetLocation();
			const double Displacement = FVector::Distance(HeadPosition, ReferencePosition);
			bHairFinite &= !Current.ContainsNaN() && FMath::IsFinite(Bend) && FMath::IsFinite(Displacement) && Current.GetScale3D().Equals(FVector::OneVector, .001);
			const bool bRoot = Ref.GetBoneName(Parent).ToString().StartsWith(TEXT("Hair_BoneRoot"));
			bool bTip = true;
			for (int32 Candidate = Index + 1; Candidate < Ref.GetNum(); ++Candidate) if (Ref.GetParentIndex(Candidate) == Index) { bTip = false; break; }
			if (bRoot) { ++HairRootSamples; HairRootSquared += Displacement * Displacement; HairRootPeak = FMath::Max(HairRootPeak, Displacement); }
			if (bTip) { ++HairTipSamples; HairTipSquared += Displacement * Displacement; HairTipPeak = FMath::Max(HairTipPeak, Displacement); }
			++HairBendSamples; HairBendSquared += Bend * Bend;
			if (Bend > HairBendPeak) { HairBendPeak = Bend; HairPeakBone = Name; }
			const FQuat* Previous = HairPreviousRotations.Find(Index);
			if (Previous) HairActiveJoints.Add(Index, FMath::Max(HairActiveJoints.FindRef(Index), FMath::RadiansToDegrees(Previous->AngularDistance(Relative.GetRotation()))));
			HairPreviousRotations.Add(Index, Relative.GetRotation());
		}
	}
	void ReportHairMotion()
	{
		int32 Responding = 0;
		for (const auto& Entry : HairActiveJoints) if (Entry.Value > .01) ++Responding;
		Test->TestTrue(TEXT("Hair remains responsive during movement"), Responding > 0);
		Test->TestTrue(TEXT("All refined hair bone poses stay finite and at unit world scale"), bHairFinite);
		USkeletalMeshComponent* Hair = Components.FindRef(FName(TEXT("Hair"))).Get();
		if (Hair && Hair->GetAnimInstance())
			for (TFieldIterator<FStructProperty> It(Hair->GetAnimInstance()->GetClass()); It; ++It)
				if (It->Struct == FAnimNode_RigidBody::StaticStruct())
				{
					const auto* Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Hair->GetAnimInstance());
					if (Rigid->OverridePhysicsAsset && Rigid->OverridePhysicsAsset->SkeletalBodySetups.Num() > Hair->GetPhysicsAsset()->SkeletalBodySetups.Num())
						Test->TestTrue(TEXT("Refined hair has no large joint flip (35-degree QA envelope)"), HairBendPeak < 35.);
				}
		Test->AddInfo(FString::Printf(TEXT("HairPeakJoint bone=%s bendDegrees=%.6f"), *HairPeakBone, HairBendPeak));
		Test->AddInfo(FString::Printf(TEXT("HairMotion rootSamples=%d rootRmsCm=%.6f rootPeakCm=%.6f tipSamples=%d tipRmsCm=%.6f tipPeakCm=%.6f bendRmsDegrees=%.6f bendPeakDegrees=%.6f independentlyRespondingJoints=%d"), HairRootSamples, FMath::Sqrt(HairRootSquared / FMath::Max(1, HairRootSamples)), HairRootPeak, HairTipSamples, FMath::Sqrt(HairTipSquared / FMath::Max(1, HairTipSamples)), HairTipPeak, FMath::Sqrt(HairBendSquared / FMath::Max(1, HairBendSamples)), HairBendPeak, Responding));
	}
	static bool IsClothBone(FName Bone)
	{
		const FString Name = Bone.ToString();
		// Iron retains its imported joints and is outside this cloth tuning scope.
		// Cloth angular QA covers saved simulated joints in cape/cloth/leather only.
		return Name.StartsWith(TEXT("B_Cape_")) || Name.StartsWith(TEXT("B_Cloth_")) || Name.StartsWith(TEXT("B_Leather_"));
	}
	// Test-local observations only; no additional product state or physics implementation.
	struct FShoulderFlutterMetric
	{
		int32 Samples = 0;
		double DeltaSquared = 0., DeltaPeak = 0., SpeedSquared = 0., SpeedPeak = 0., DeltaSecondsTotal = 0.;
		TSet<int32> Joints;
	};
	struct FClothMotion
	{
		TArray<FTransform> Reference;
		TMap<int32, FQuat> PreviousRotations;
		TMap<int32, double> ActiveBones;
		TMap<int32, FQuat> SecondaryPreviousRotations;
		TMap<int32, double> SecondaryActiveBones;
		TSet<int32> DirectSimulatedBones;
		TMap<int32, int32> ConstraintParents;
		TMap<int32, FQuat> ConstraintFrames1, ConstraintFrames2;
		bool bFinite = true;
		int32 BendSamples = 0, TipSamples = 0;
		double BendSquared = 0., BendPeak = 0., TipSquared = 0., TipPeak = 0.;
		double NonSimulatedRefBendPeak = 0.;
		FName PeakBone, NonSimulatedRefPeakBone;
		FString PeakActorFrameEvidence;
		double ShoulderPreviousTime = -1.;
		FShoulderFlutterMetric ShoulderFlutter[4];
	};
	void SampleClothMotion()
	{
		for (const FName Part : {FName(TEXT("Torso")), FName(TEXT("Leg"))})
		{
			USkeletalMeshComponent* Mesh = Components.FindRef(Part).Get(); if (!Mesh || !Mesh->GetAnimInstance()) continue;
			Mesh->HandleExistingParallelEvaluationTask(true, true);
			const auto& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
			FClothMotion& Motion = ClothMotion.FindOrAdd(Part);
			// Stage is sampled before the input switch: 3/4 are the two moving windows;
			// 5 is released/stopping. This opt-in reuses joint quaternions, never poses/physics.
			const bool bShoulderProbe = Part == FName(TEXT("Torso")) && (Stage == 3 || Stage == 4) && FParse::Param(FCommandLine::Get(), TEXT("PlayerShoulderMotionProbe"));
			const double ShoulderTime = bShoulderProbe ? Player->GetWorld()->GetTimeSeconds() : 0.;
			const double ShoulderDeltaSeconds = ShoulderTime - Motion.ShoulderPreviousTime;
			if (Motion.Reference.IsEmpty())
			{
				for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
				{
					FTransform Pose = Ref.GetRefBonePose()[Index];
					if (Index > 0) Pose = Pose * Motion.Reference[Ref.GetParentIndex(Index)];
					Motion.Reference.Add(Pose);
				}
				const double Scale = Ref.GetRefBonePose()[0].GetScale3D().X;
				for (FTransform& Pose : Motion.Reference) { Pose.SetTranslation(Pose.GetTranslation() / Scale); Pose.SetScale3D(FVector::OneVector); }
				const UPhysicsAsset* SimulationAsset = Mesh->GetPhysicsAsset();
				for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It)
					if (It->Struct == FAnimNode_RigidBody::StaticStruct())
					{
						const auto* Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance());
						if (Rigid->OverridePhysicsAsset) SimulationAsset = Rigid->OverridePhysicsAsset.Get();
					}
				for (const USkeletalBodySetup* Body : SimulationAsset->SkeletalBodySetups)
					if (Body->PhysicsType == PhysType_Simulated)
					{
						const int32 Index = Ref.FindBoneIndex(Body->BoneName);
						if (Index != INDEX_NONE && IsClothBone(Body->BoneName)) Motion.DirectSimulatedBones.Add(Index);
					}
				for (const UPhysicsConstraintTemplate* Template : SimulationAsset->ConstraintSetup)
				{
					const FConstraintInstance& Constraint = Template->DefaultInstance;
					const int32 Child = Ref.FindBoneIndex(Constraint.ConstraintBone1);
					const int32 Parent = Ref.FindBoneIndex(Constraint.ConstraintBone2);
					if (!Motion.DirectSimulatedBones.Contains(Child) || Parent == INDEX_NONE) continue;
					Motion.ConstraintParents.Add(Child, Parent);
					Motion.ConstraintFrames1.Add(Child, Constraint.GetRefFrame(EConstraintFrame::Frame1).GetRotation());
					Motion.ConstraintFrames2.Add(Child, Constraint.GetRefFrame(EConstraintFrame::Frame2).GetRotation());
				}
				Test->TestEqual(*(Part.ToString() + TEXT(" every simulated cloth body has a saved joint observation")), Motion.ConstraintParents.Num(), Motion.DirectSimulatedBones.Num());
			}
			for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
			{
				if (!IsClothBone(Ref.GetBoneName(Index))) continue;
				const int32 Parent = Ref.GetParentIndex(Index); if (Parent == INDEX_NONE) continue;
				int32 Anchor = Parent;
				while (Anchor != INDEX_NONE && IsClothBone(Ref.GetBoneName(Anchor))) Anchor = Ref.GetParentIndex(Anchor);
				if (Anchor == INDEX_NONE) continue;
				const FTransform Current = Mesh->GetBoneTransform(Index);
				const FTransform Relative = Current.GetRelativeTransform(Mesh->GetBoneTransform(Parent));
				const double RefBoneBend = FMath::RadiansToDegrees(Relative.GetRotation().AngularDistance(Ref.GetRefBonePose()[Index].GetRotation()));
				const FVector Position = Current.GetRelativeTransform(Mesh->GetBoneTransform(Anchor)).GetLocation();
				const FVector ReferencePosition = Motion.Reference[Index].GetRelativeTransform(Motion.Reference[Anchor]).GetLocation();
				const double Displacement = FVector::Distance(Position, ReferencePosition);
				Motion.bFinite &= !Current.ContainsNaN() && FMath::IsFinite(RefBoneBend) && FMath::IsFinite(Displacement) && Current.GetScale3D().Equals(FVector::OneVector, .001);
				bool bTip = true;
				for (int32 Candidate = Index + 1; Candidate < Ref.GetNum(); ++Candidate) if (Ref.GetParentIndex(Candidate) == Index) { bTip = false; break; }
				if (bTip) { ++Motion.TipSamples; Motion.TipSquared += Displacement * Displacement; Motion.TipPeak = FMath::Max(Motion.TipPeak, Displacement); }
				const FQuat* PreviousSecondary = Motion.SecondaryPreviousRotations.Find(Index);
				if (PreviousSecondary) Motion.SecondaryActiveBones.Add(Index, FMath::Max(Motion.SecondaryActiveBones.FindRef(Index), FMath::RadiansToDegrees(PreviousSecondary->AngularDistance(Relative.GetRotation()))));
				Motion.SecondaryPreviousRotations.Add(Index, Relative.GetRotation());
				if (!Motion.DirectSimulatedBones.Contains(Index))
				{
					// Kinematic/CopyPose/reference changes are useful context, but cannot
					// count as a simulated joint-limit violation or a physics flip.
					if (RefBoneBend > Motion.NonSimulatedRefBendPeak) { Motion.NonSimulatedRefBendPeak = RefBoneBend; Motion.NonSimulatedRefPeakBone = Ref.GetBoneName(Index); }
					continue;
				}
				const int32* JointParent = Motion.ConstraintParents.Find(Index); if (!JointParent) continue;
				// A coarse saved PA can skip immediate skeleton parents. Observe its
				// actual constraint parent and authored connector rotations instead of
				// treating immediate-parent/reference-pose animation as joint deflection.
				const FQuat Frame1World = Current.GetRotation() * Motion.ConstraintFrames1.FindChecked(Index);
				const FQuat Frame2World = Mesh->GetBoneTransform(*JointParent).GetRotation() * Motion.ConstraintFrames2.FindChecked(Index);
				const FQuat JointRelative = Frame2World.Inverse() * Frame1World;
				const double Bend = FMath::RadiansToDegrees(JointRelative.AngularDistance(FQuat::Identity));
				Motion.bFinite &= !JointRelative.ContainsNaN() && FMath::IsFinite(Bend);
				++Motion.BendSamples; Motion.BendSquared += Bend * Bend;
				if (Bend > Motion.BendPeak)
				{
					Motion.BendPeak = Bend; Motion.PeakBone = Ref.GetBoneName(Index);
					// ActorWorld is the public bone/actor frame (not CoM). Compare the same
					// saved connectors at this exact mesh peak; do not change angular QA.
					for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It) if (It->Struct == FAnimNode_RigidBody::StaticStruct())
					{
						auto* Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance());
						auto* Simulation = Rigid->GetSimulation(); if (!Simulation) continue;
						const ImmediatePhysics::FActorHandle* ChildActor = nullptr; const ImmediatePhysics::FActorHandle* ParentActor = nullptr;
						for (int32 A = 0; A < Simulation->NumActors(); ++A) { const auto* Actor = Simulation->GetActorHandle(A); if (Actor->GetName() == Ref.GetBoneName(Index)) ChildActor = Actor; if (Actor->GetName() == Ref.GetBoneName(*JointParent)) ParentActor = Actor; }
						if (!ChildActor || !ParentActor) continue;
						const FTransform ChildActorWorld = ChildActor->GetWorldTransform(), ParentActorWorld = ParentActor->GetWorldTransform(), ParentMeshWorld = Mesh->GetBoneTransform(*JointParent);
						const FQuat ChildRotation = ChildActorWorld.GetRotation(), ParentRotation = ParentActorWorld.GetRotation();
						const FQuat ActorJoint = (ParentRotation * Motion.ConstraintFrames2.FindChecked(Index)).Inverse() * (ChildRotation * Motion.ConstraintFrames1.FindChecked(Index));
						Motion.PeakActorFrameEvidence = FString::Printf(TEXT("ClothPeakActorFrames part=%s child=%s parent=%s stage=%d timeSeconds=%.6f simulationSpace=%d simulationTiming=%d allowPoseScalePropagation=%d actorJointDegrees=%.6f meshJointDegrees=%.6f childActorMeshGapDegrees=%.6f parentActorMeshGapDegrees=%.6f childActorRotation=%s parentActorRotation=%s"), *Part.ToString(), *ChildActor->GetName().ToString(), *ParentActor->GetName().ToString(), Stage, Player->GetWorld()->GetTimeSeconds(), int32(Rigid->SimulationSpace), int32(Rigid->SimulationTiming), int32(Rigid->bAllowPoseScalePropagation), FMath::RadiansToDegrees(ActorJoint.AngularDistance(FQuat::Identity)), Bend, FMath::RadiansToDegrees(ChildRotation.AngularDistance(Current.GetRotation())), FMath::RadiansToDegrees(ParentRotation.AngularDistance(Mesh->GetBoneTransform(*JointParent).GetRotation())), *ChildRotation.ToString(), *ParentRotation.ToString());
						Motion.PeakActorFrameEvidence += FString::Printf(TEXT(" childActorMeshGapCm=%.6f parentActorMeshGapCm=%.6f actorChildParentDistanceCm=%.6f meshChildParentDistanceCm=%.6f childActorPositionCm=%s parentActorPositionCm=%s childMeshPositionCm=%s parentMeshPositionCm=%s"), FVector::Distance(ChildActorWorld.GetLocation(), Current.GetLocation()), FVector::Distance(ParentActorWorld.GetLocation(), ParentMeshWorld.GetLocation()), FVector::Distance(ChildActorWorld.GetLocation(), ParentActorWorld.GetLocation()), FVector::Distance(Current.GetLocation(), ParentMeshWorld.GetLocation()), *ChildActorWorld.GetLocation().ToString(), *ParentActorWorld.GetLocation().ToString(), *Current.GetLocation().ToString(), *ParentMeshWorld.GetLocation().ToString());
						// Saved connector positions are PA-space cm inputs, not live Chaos
						// settings. Log them alongside world positions to expose scale errors.
						if (const UPhysicsAsset* Asset = Rigid->GetPhysicsAsset())
							for (const UPhysicsConstraintTemplate* Template : Asset->ConstraintSetup)
								if (Template->DefaultInstance.ConstraintBone1 == ChildActor->GetName() && Template->DefaultInstance.ConstraintBone2 == ParentActor->GetName())
									Motion.PeakActorFrameEvidence += FString::Printf(TEXT(" savedConnector1PositionCm=%s savedConnector2PositionCm=%s"), *Template->DefaultInstance.GetRefFrame(EConstraintFrame::Frame1).GetLocation().ToString(), *Template->DefaultInstance.GetRefFrame(EConstraintFrame::Frame2).GetLocation().ToString());
					}
				}
				const FQuat* Previous = Motion.PreviousRotations.Find(Index);
				// Exclude each joint's first quaternion and duplicate same-world-time updates.
				// Absolute shortest quaternion delta measures motion, not static ref-pose sag.
				if (bShoulderProbe && Previous && ShoulderDeltaSeconds > 0.)
				{
					const double DeltaDegrees = FMath::RadiansToDegrees(Previous->GetNormalized().AngularDistance(JointRelative.GetNormalized()));
					const double Speed = DeltaDegrees / ShoulderDeltaSeconds;
					if (FMath::IsFinite(DeltaDegrees) && FMath::IsFinite(Speed))
						for (const int32 Group : {0, Ref.GetBoneName(Index) == FName(TEXT("B_Cape_02_02_L_Armor001")) ? 1 : 2, Ref.GetBoneName(Index) == FName(TEXT("B_Cape_01_02_L_Armor001")) ? 3 : INDEX_NONE})
						{
							if (Group == INDEX_NONE) continue;
							auto& Metric = Motion.ShoulderFlutter[Group]; ++Metric.Samples; Metric.Joints.Add(Index);
							Metric.DeltaSquared += DeltaDegrees * DeltaDegrees; Metric.DeltaPeak = FMath::Max(Metric.DeltaPeak, DeltaDegrees);
							Metric.SpeedSquared += Speed * Speed; Metric.SpeedPeak = FMath::Max(Metric.SpeedPeak, Speed);
							Metric.DeltaSecondsTotal += ShoulderDeltaSeconds;
						}
				}
				if (Previous) Motion.ActiveBones.Add(Index, FMath::Max(Motion.ActiveBones.FindRef(Index), FMath::RadiansToDegrees(Previous->AngularDistance(JointRelative))));
				Motion.PreviousRotations.Add(Index, JointRelative);
			}
			if (bShoulderProbe) Motion.ShoulderPreviousTime = ShoulderTime;
		}
	}
	void ReportClothMotion()
	{
		for (const FName Part : {FName(TEXT("Torso")), FName(TEXT("Leg"))})
		{
			const FClothMotion* Motion = ClothMotion.Find(Part); if (!Motion) { Test->AddError(Part.ToString() + TEXT(" cloth motion not sampled")); continue; }
			int32 Responding = 0, DirectResponding = 0;
			for (const auto& Entry : Motion->SecondaryActiveBones) if (Entry.Value > .01) ++Responding;
			for (const auto& Entry : Motion->ActiveBones) if (Entry.Value > .01) ++DirectResponding;
			Test->TestTrue(*(Part.ToString() + TEXT(" secondary poses remain finite and at unit world scale")), Motion->bFinite);
			Test->TestTrue(*(Part.ToString() + TEXT(" cloth remains responsive during movement")), DirectResponding > 0);
			USkeletalMeshComponent* Mesh = Components.FindRef(Part).Get();
			for (TFieldIterator<FStructProperty> It(Mesh->GetAnimInstance()->GetClass()); It; ++It)
				if (It->Struct == FAnimNode_RigidBody::StaticStruct())
				{
					const auto* Rigid = It->ContainerPtrToValuePtr<FAnimNode_RigidBody>(Mesh->GetAnimInstance());
					if (Rigid->OverridePhysicsAsset && Rigid->OverridePhysicsAsset->SkeletalBodySetups.Num() > Mesh->GetPhysicsAsset()->SkeletalBodySetups.Num())
						Test->TestTrue(*(Part.ToString() + TEXT(" refined cloth has no large joint flip (45-degree QA envelope)")), Motion->BendPeak < 45.);
				}
			// Angular QA is saved simulated-joint frame deflection only. Tip displacement
			// deliberately still observes ALL secondary leaf bones relative to their anchor.
			Test->AddInfo(FString::Printf(TEXT("ClothMotionScope part=%s angular=SavedDirectSimulatedJointFrames tip=AllSecondaryLeafBones observedJoints=%d nonSimulatedRefBendPeakDegrees=%.6f nonSimulatedRefPeakBone=%s"), *Part.ToString(), Motion->ConstraintParents.Num(), Motion->NonSimulatedRefBendPeak, *Motion->NonSimulatedRefPeakBone.ToString()));
			if (!Motion->PeakActorFrameEvidence.IsEmpty()) Test->AddInfo(Motion->PeakActorFrameEvidence);
			if (Part == FName(TEXT("Torso")) && FParse::Param(FCommandLine::Get(), TEXT("PlayerShoulderMotionProbe")))
			{
				const TCHAR* Groups[] = {TEXT("Whole8"), TEXT("ShortPanel02_02"), TEXT("LongCloth7"), TEXT("LongProximal01_02")};
				for (int32 Group = 0; Group < 4; ++Group)
				{
					const auto& Metric = Motion->ShoulderFlutter[Group]; const int32 Count = FMath::Max(1, Metric.Samples);
					Test->AddInfo(FString::Printf(TEXT("ShoulderFlutterMetrics group=%s scope=SavedDirectSimulatedTorsoJointFrames movingStages=3,4 firstQuaternionExcluded=1 interval=BetweenAutomationSamples actualWorldElapsedSeconds=1 observedJoints=%d samples=%d deltaRmsDegrees=%.6f deltaPeakDegrees=%.6f speedRmsDegreesPerSecond=%.6f speedPeakDegreesPerSecond=%.6f meanDeltaSeconds=%.9f"), Groups[Group], Metric.Joints.Num(), Metric.Samples, FMath::Sqrt(Metric.DeltaSquared / Count), Metric.DeltaPeak, FMath::Sqrt(Metric.SpeedSquared / Count), Metric.SpeedPeak, Metric.DeltaSecondsTotal / Count));
				}
			}
			Test->AddInfo(FString::Printf(TEXT("ClothMotion part=%s bendSamples=%d bendRmsDegrees=%.6f bendPeakDegrees=%.6f peakBone=%s tipSamples=%d tipRmsCm=%.6f tipPeakCm=%.6f secondaryRespondingBones=%d directSimulatedBones=%d independentlyRespondingJoints=%d"), *Part.ToString(), Motion->BendSamples, FMath::Sqrt(Motion->BendSquared / FMath::Max(1, Motion->BendSamples)), Motion->BendPeak, *Motion->PeakBone.ToString(), Motion->TipSamples, FMath::Sqrt(Motion->TipSquared / FMath::Max(1, Motion->TipSamples)), Motion->TipPeak, Responding, Motion->DirectSimulatedBones.Num(), DirectResponding));
		}
	}
	void ReportContacts()
	{
		Test->TestEqual(TEXT("Contact manifold depth samples remain finite"), ContactNonFinite, 0);
		for (const FName Part : {FName(TEXT("Hair")), FName(TEXT("Torso")), FName(TEXT("Leg"))})
		{
			Test->AddInfo(FString::Printf(TEXT("ActualBodyContacts part=%s manifoldPoints=%d accumulatedImpulse=%.6f"), *Part.ToString(), ContactPoints.FindRef(Part), ContactImpulse.FindRef(Part)));
			// This tests collision proxies/manifold points, not all rendered garment vertices.
			Test->AddInfo(FString::Printf(TEXT("BodyContactDepth part=%s samples=%d initialPhiMinCm=%.6f initialPenetrationPeakCm=%.6f currentSignedSeparationMinCm=%.6f currentPenetrationPeakCm=%.6f currentPenetrationRmsCm=%.6f overlappingManifoldSamples=%d"), *Part.ToString(), ContactDepthSamples.FindRef(Part), ContactInitialMinimum.FindRef(Part), FMath::Max(0., -ContactInitialMinimum.FindRef(Part)), ContactCurrentMinimum.FindRef(Part), FMath::Max(0., -ContactCurrentMinimum.FindRef(Part)), FMath::Sqrt(ContactCurrentPenetrationSquared.FindRef(Part) / FMath::Max(1, ContactDepthSamples.FindRef(Part))), ContactOverlappingSamples.FindRef(Part)));
			if (Part != FName(TEXT("Torso"))) Test->TestTrue(*(Part.ToString() + TEXT(" actual character contact manifold")), ContactPoints.FindRef(Part) > 0);
			// Root attachment protection can keep the cape clear of the body for
			// this controlled sequence. Speculative manifold samples need not resolve
			// an impulse. Its collider/shape/current-pose registration is checked above.
			if (Part != FName(TEXT("Torso"))) Test->TestTrue(*(Part.ToString() + TEXT(" actual collision impulse")), ContactImpulse.FindRef(Part) > 0.);
		}
	}
	void CheckDynamics()
	{
		for (const FName Part : {FName(TEXT("Hair")), FName(TEXT("Torso")), FName(TEXT("Leg"))})
			Test->TestTrue(*(Part.ToString() + TEXT(" simulated pose differs from bypass")), DynamicAngles.FindRef(Part) > .1f);
	}
	void Cleanup()
	{
		RestoreWaistIronContact();
		if (Player.IsValid()) { Player->HandleInputMoveReleased(); Player->GetController()->SetControlRotation(SavedControl); }
		if (CameraArm.IsValid()) { CameraArm->TargetArmLength = SavedArmLength; CameraArm->SocketOffset = SavedSocketOffset; CameraArm->bUsePawnControlRotation = SavedUsePawnControlRotation; CameraArm->SetRelativeRotation(SavedArmRotation); }
		if (RigidCVar) RigidCVar->Set(SavedRigid, ECVF_SetByConsole);
		if (WaistSimulationCVar) WaistSimulationCVar->Set(SavedWaistSimulation, ECVF_SetByConsole);
	}
	FAutomationTestBase* Test;
	IConsoleVariable* WaistSimulationCVar = nullptr;
	int32 SavedWaistSimulation = 1;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<USpringArmComponent> CameraArm;
	float SavedArmLength = 0.f;
	FVector SavedSocketOffset = FVector::ZeroVector;
	FRotator SavedArmRotation = FRotator::ZeroRotator;
	bool SavedUsePawnControlRotation = false;
	TMap<FName, TWeakObjectPtr<USkeletalMeshComponent>> Components;
	TMap<FString, FTransform> Baseline;
	TMap<FName, float> DynamicAngles;
	TMap<FName, int32> ContactPoints;
	TMap<FName, double> ContactImpulse;
	TMap<FName, double> ContactInitialMinimum, ContactCurrentMinimum, ContactCurrentPenetrationSquared;
	TMap<FName, int32> ContactDepthSamples, ContactOverlappingSamples;
	int32 ContactNonFinite = 0;
	TMap<FName, FClothMotion> ClothMotion;
	bool bWaistJitterProbe = FParse::Param(FCommandLine::Get(), TEXT("PlayerWaistJitterProbe"));
	bool bWaistDisableIronContact = FParse::Param(FCommandLine::Get(), TEXT("PlayerWaistDisableIronContact"));
	TMap<FString, FWaistJitter> WaistJitter;
	TMap<FString, int32> WaistPairPoints;
	TMap<FString, double> WaistPairImpulse;
	TMap<FName, bool> WaistDisabledIron;
	FString WaistCsv = TEXT("phase,timeSeconds,deltaSeconds,bone,parent,hasPrevious,meshJointStepDegrees,parentRelativePositionStepCm,parentWorldStepDegrees,parentWorldPositionStepCm,actorJointStepDegrees,meshJointSpeedDegreesPerSecond,actorAngularSpeedDegreesPerSecond,actorValid,actorEnabled,actorHasCollision,activeContactPoints,cachedMinSeparationCm,accumulatedImpulse\n");
	TSet<FName> ObservedDamping;
	TArray<FTransform> HairReference;
	TMap<int32, FQuat> HairPreviousRotations;
	TMap<int32, double> HairActiveJoints;
	bool bHairFinite = true;
	FString HairPeakBone;
	int32 HairRootSamples = 0, HairTipSamples = 0, HairBendSamples = 0;
	double HairRootSquared = 0., HairTipSquared = 0., HairBendSquared = 0., HairRootPeak = 0., HairTipPeak = 0., HairBendPeak = 0.;
	IConsoleVariable* RigidCVar = nullptr;
	FRotator SavedControl;
	double Deadline; float Start = 0.f; float Next = 1.f; int32 Stage = 0; int32 SavedRigid = 1;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZPlayerPartsPIE, "Khazan.PlayerParts.PIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZPlayerPartsPIE::RunTest(const FString& Parameters)
{
	if (!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_PlayerPartsWork_20261007"))) return false;
	ADD_LATENT_AUTOMATION_COMMAND(KZPlayerPartsPIE::FRun(this)); return true;
}
#endif
