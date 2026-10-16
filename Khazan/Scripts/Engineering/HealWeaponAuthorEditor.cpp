// Compiled only in the isolated work project. Public editor APIs; no product dependency.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "Components/SkeletalMeshComponent.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "AnimGraphNode_Slot.h"
#include "AnimGraphNode_LayeredBoneBlend.h"
#include "AnimGraphNode_UseCachedPose.h"
#include "AnimGraphNode_SaveCachedPose.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphSchema.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/IConsoleManager.h"
#include "Editor.h"
#include "PlayInEditorDataTypes.h"
#include "LevelEditor.h"
#include "IAssetViewport.h"

namespace KZHealWeaponAuthor
{
bool IsWork() { return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_HealWeaponWork_20261006")); }
FAutoConsoleCommand StartPIE(TEXT("Khazan.Heal.StartPIE"), TEXT("Work editor only"), FConsoleCommandDelegate::CreateLambda([]
{
	if (!IsWork()) return;
	FRequestPlaySessionParams Params;
	Params.bAllowOnlineSubsystem = false;
	Params.DestinationSlateViewport = TWeakPtr<IAssetViewport>(FModuleManager::LoadModuleChecked<FLevelEditorModule>(TEXT("LevelEditor")).GetFirstActiveViewport());
	GEditor->RequestPlaySession(Params);
}));
FAutoConsoleCommand StopPIE(TEXT("Khazan.Heal.StopPIE"), TEXT("Work editor only"), FConsoleCommandDelegate::CreateLambda([] { if (IsWork()) GEditor->RequestEndPlayMap(); }));

bool Save(UObject* Asset)
{
	UPackage* Package = Asset->GetOutermost();
	Package->MarkPackageDirty();
	FSavePackageArgs Args;
	Args.TopLevelFlags = RF_Public | RF_Standalone;
	return UPackage::SavePackage(Package, Asset, *FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZHealWeaponAudit, "Khazan.HealWeapon.Audit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZHealWeaponAudit::RunTest(const FString& Parameters)
{
	using namespace KZHealWeaponAuthor;
	if (!IsWork()) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/_Art/Player/Character/Meshs/SKM_Player"));
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, TEXT("/Game/_Art/Player/Character/Bluprints/BP_Player"));
	if (!Mesh || !BP) return false;
	for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
		if (const USceneComponent* Component = Cast<USceneComponent>(Node->ComponentTemplate))
			AddInfo(FString::Printf(TEXT("Attachment: name=%s parent=%s native=%d socket=%s transform=%s"), *Node->GetVariableName().ToString(),
				*Node->ParentComponentOrVariableName.ToString(), Node->bIsParentComponentNative, *Node->AttachToName.ToString(), *Component->GetRelativeTransform().ToString()));
	for (const FName Name : {FName(TEXT("Weapon_L")), FName(TEXT("Weapon_R")), FName(TEXT("Weapon_L_BackPack")), FName(TEXT("Weapon_R_BackPack")),
		FName(TEXT("Weapon_L_BackPack소켓")), FName(TEXT("Weapon_R_BackPack소켓"))})
	{
		const USkeletalMeshSocket* Socket = Mesh->FindSocket(Name);
		const int32 Bone = Mesh->GetRefSkeleton().FindBoneIndex(Name);
		AddInfo(FString::Printf(TEXT("Socket: name=%s boneIndex=%d socketBone=%s location=%s rotation=%s scale=%s"), *Name.ToString(), Bone,
			Socket ? *Socket->BoneName.ToString() : TEXT("None"), Socket ? *Socket->RelativeLocation.ToString() : TEXT("None"),
			Socket ? *Socket->RelativeRotation.ToString() : TEXT("None"), Socket ? *Socket->RelativeScale.ToString() : TEXT("None")));
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	const FName Names[] = {TEXT("Armed"), TEXT("UnArmed"), TEXT("Heal_01")};
	for (const FName Name : Names)
	{
		const FString Path = Name == TEXT("Heal_01") ? TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/") : TEXT("/Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Equip/");
		UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *(Path + TEXT("CA_P_Kazan_DualAxeSword_") + Name.ToString()));
		if (!Clip) return false;
		const IAnimationDataModel* Model = Clip->GetDataModel();
		TArray<FName> Tracks; Model->GetBoneTrackNames(Tracks);
		AddInfo(FString::Printf(TEXT("Clip: name=%s length=%.9f rate=%.9f root=%d keys=%d fps=%s"), *Name.ToString(), Clip->GetPlayLength(), Clip->RateScale, Clip->bEnableRootMotion, Model->GetNumberOfKeys(), *Model->GetFrameRate().ToPrettyText().ToString()));
		for (int32 Sample = 0; Sample <= 10; ++Sample)
		{
			TArray<FTransform> Component; Component.SetNum(Ref.GetNum());
			for (int32 Bone = 0; Bone < Ref.GetNum(); ++Bone)
			{
				const FName BoneName = Ref.GetBoneName(Bone);
				const FTransform Local = Tracks.Contains(BoneName) ? Model->EvaluateBoneTrackTransform(BoneName, FFrameTime::FromDecimal(double(Model->GetNumberOfFrames()) * Sample / 10.0), EAnimInterpolationType::Linear) : Ref.GetRefBonePose()[Bone];
				Component[Bone] = Bone > 0 ? Local * Component[Ref.GetParentIndex(Bone)] : Local;
			}
			const FTransform& L = Component[Ref.FindBoneIndex(TEXT("Weapon_L"))];
			const FTransform& R = Component[Ref.FindBoneIndex(TEXT("Weapon_R"))];
			const FTransform& BL = Component[Ref.FindBoneIndex(TEXT("Weapon_L_BackPack"))];
			const FTransform& BR = Component[Ref.FindBoneIndex(TEXT("Weapon_R_BackPack"))];
			AddInfo(FString::Printf(TEXT("EquipPose: clip=%s fraction=%.1f LeftCM=%s RightCM=%s BackLCM=%s BackRCM=%s"), *Name.ToString(), Sample / 10.f,
				*(L.GetTranslation() * .01).ToString(), *(R.GetTranslation() * .01).ToString(), *(BL.GetTranslation() * .01).ToString(), *(BR.GetTranslation() * .01).ToString()));
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZHealWeaponAuthor, "Khazan.HealWeapon.Author", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZHealWeaponAuthor::RunTest(const FString& Parameters)
{
	using namespace KZHealWeaponAuthor;
	if (!IsWork()) return false;
	UAnimSequence* Stow = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/_Art/Player/Animation/InGame/DAS/Equip/CA_P_Kazan_DualAxeSword_UnArmed"));
	UAnimSequence* Draw = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/_Art/Player/Animation/InGame/DAS/Equip/CA_P_Kazan_DualAxeSword_Armed"));
	UAnimSequence* Heal = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/CA_P_Kazan_DualAxeSword_Heal_01"));
	UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal"));
	UAnimBlueprint* ABP = LoadObject<UAnimBlueprint>(nullptr, TEXT("/Game/_Art/Player/Character/Bluprints/ABP_Player"));
	UBlueprint* GA = LoadObject<UBlueprint>(nullptr, TEXT("/Game/Bluprints/AbilitySystem/Abilities/Player/Heal/GA_Player_Heal"));
	if (!Stow || !Draw || !Heal || !Montage || !ABP || !GA) return false;
	const TCHAR* DrawPath = TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_HealDraw");
	if (FPackageName::DoesPackageExist(DrawPath)) { AddError(TEXT("One-shot author already ran; audit saved assets instead.")); return false; }
	USkeleton* Skeleton = Heal->GetSkeleton();
	const FName ArmBones[] = {TEXT("bip001-l-clavicle"), TEXT("bip001-r-clavicle")};
	for (FName Bone : ArmBones) if (!TestTrue(TEXT("Arms branch exists"), Skeleton->GetReferenceSkeleton().FindBoneIndex(Bone) != INDEX_NONE)) return false;
	Skeleton->RegisterSlotNode(TEXT("Arms"));
	Skeleton->SetSlotGroupName(TEXT("Arms"), TEXT("DefaultGroup"));
	if (!Save(Skeleton)) return false;
	UAnimMontage* DrawMontage = NewObject<UAnimMontage>(CreatePackage(DrawPath), TEXT("AM_DAS_Player_HealDraw"), RF_Public | RF_Standalone | RF_Transactional);
	DrawMontage->SetSkeleton(Skeleton);
	auto AddSegment = [](FSlotAnimationTrack& Track, UAnimSequence* Clip, float Start)
	{
		FAnimSegment Segment; Segment.SetAnimReference(Clip);
		Segment.StartPos = Start; Segment.AnimStartTime = 0.f; Segment.AnimEndTime = Clip->GetPlayLength();
		Segment.AnimPlayRate = 1.f; Segment.LoopingCount = 1;
		Track.AnimTrack.AnimSegments.Add(Segment);
	};
	FSlotAnimationTrack UpperTrack; UpperTrack.SlotName = TEXT("UpperBody");
	AddSegment(UpperTrack, Stow, 0.f); AddSegment(UpperTrack, Heal, Stow->GetPlayLength());
	Montage->SlotAnimTracks = {UpperTrack};
	Montage->CompositeSections.Reset(); Montage->Notifies.Reset();
	FCompositeSection StowSection; StowSection.SectionName = TEXT("Stow"); StowSection.NextSectionName = TEXT("Heal"); StowSection.Link(Montage, 0.f);
	FCompositeSection HealSection; HealSection.SectionName = TEXT("Heal"); HealSection.NextSectionName = NAME_None; HealSection.Link(Montage, Stow->GetPlayLength());
	Montage->CompositeSections = {StowSection, HealSection};
	Montage->GetController().SetFrameRate(Heal->GetDataModel()->GetFrameRate(), false);
	Montage->GetController().SetNumberOfFrames(Stow->GetDataModel()->GetNumberOfFrames() + Heal->GetDataModel()->GetNumberOfFrames(), false);
	FSlotAnimationTrack ArmsTrack; ArmsTrack.SlotName = TEXT("Arms"); AddSegment(ArmsTrack, Draw, 0.f);
	DrawMontage->SlotAnimTracks = {ArmsTrack};
	DrawMontage->GetController().SetFrameRate(Draw->GetDataModel()->GetFrameRate(), false);
	DrawMontage->GetController().SetNumberOfFrames(Draw->GetDataModel()->GetNumberOfFrames(), false);
	FCompositeSection DrawSection; DrawSection.SectionName = TEXT("Draw"); DrawSection.NextSectionName = NAME_None; DrawSection.Link(DrawMontage, 0.f);
	DrawMontage->CompositeSections = {DrawSection};
	DrawMontage->BlendIn = Montage->BlendIn; DrawMontage->BlendOut = Montage->BlendOut;
	DrawMontage->BlendOutTriggerTime = 0.f;
	// Temporary expression authoring, not source notify metadata. Adjust only these Montage events.
	const float StowFraction = 0.5f;
	const float DrawFraction = 0.5f;
	auto Notify = [](UAnimMontage* Target, FName Name, float Time)
	{
		UAnimNotify_PlayMontageNotify* Object = NewObject<UAnimNotify_PlayMontageNotify>(Target, Name, RF_Transactional);
		FindFProperty<FNameProperty>(Object->GetClass(), TEXT("NotifyName"))->SetPropertyValue_InContainer(Object, Name);
		FAnimNotifyEvent Event; Event.NotifyName = Name; Event.Notify = Object; Event.MontageTickType = EMontageNotifyTickType::BranchingPoint;
		Event.Guid = FGuid::NewGuid(); Event.Link(Target, Time); Target->Notifies.Add(Event);
	};
	Notify(Montage, TEXT("WeaponStow"), Stow->GetPlayLength() * StowFraction);
	Notify(Montage, TEXT("HealStart"), Stow->GetPlayLength());
	Notify(Montage, TEXT("Heal"), Stow->GetPlayLength() + Heal->GetPlayLength() * 0.5f); // Preserve previous Heal local timing.
	Notify(DrawMontage, TEXT("WeaponDraw"), Draw->GetPlayLength() * DrawFraction);
	Montage->PostEditChange(); Montage->RefreshCacheData();
	DrawMontage->PostEditChange(); DrawMontage->RefreshCacheData();
	FAssetRegistryModule::AssetCreated(DrawMontage);
	if (!Save(Montage) || !Save(DrawMontage)) return false;
	UObject* CDO = GA->GeneratedClass->GetDefaultObject();
	FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("DrawMontage"))->SetObjectPropertyValue_InContainer(CDO, DrawMontage);
	FKismetEditorUtilities::CompileBlueprint(GA);
	if (!Save(GA)) return false;
	UEdGraph* Graph = nullptr; UAnimGraphNode_LayeredBoneBlend* UpperLayer = nullptr;
	TArray<UEdGraph*> Graphs; ABP->GetAllGraphs(Graphs);
	for (UEdGraph* Candidate : Graphs) for (UEdGraphNode* Node : Candidate->Nodes)
		if (Node->GetFName() == TEXT("Heal_UpperBodyBlend")) { Graph = Candidate; UpperLayer = Cast<UAnimGraphNode_LayeredBoneBlend>(Node); }
	if (!Graph || !UpperLayer) return false;
	UEdGraphPin* UpperOutput = nullptr;
	for (UEdGraphPin* Pin : UpperLayer->Pins) if (Pin->Direction == EGPD_Output) UpperOutput = Pin;
	if (!UpperOutput || UpperOutput->LinkedTo.Num() != 1) return false;
	UEdGraphPin* Target = UpperOutput->LinkedTo[0];
	auto NewNode = [Graph]<class T>(FName Name)
	{
		T* Node = NewObject<T>(Graph, Name, RF_Transactional); Graph->AddNode(Node, false, false); Node->CreateNewGuid(); Node->PostPlacedNewNode(); return Node;
	};
	UAnimGraphNode_SaveCachedPose* Cache = NewNode.operator()<UAnimGraphNode_SaveCachedPose>(TEXT("Heal_UpperBase"));
	Cache->CacheName = TEXT("HealUpperBase"); Cache->AllocateDefaultPins();
	UAnimGraphNode_UseCachedPose* Base = NewNode.operator()<UAnimGraphNode_UseCachedPose>(TEXT("Heal_ArmsBase"));
	Base->SaveCachedPoseNode = Cache; Base->AllocateDefaultPins();
	UAnimGraphNode_UseCachedPose* Source = NewNode.operator()<UAnimGraphNode_UseCachedPose>(TEXT("Heal_ArmsSource"));
	Source->SaveCachedPoseNode = Cache; Source->AllocateDefaultPins();
	UAnimGraphNode_Slot* Slot = NewNode.operator()<UAnimGraphNode_Slot>(TEXT("Heal_ArmsSlot"));
	Slot->Node.SlotName = TEXT("Arms"); Slot->Node.bAlwaysUpdateSourcePose = true; Slot->AllocateDefaultPins();
	UAnimGraphNode_LayeredBoneBlend* Layer = NewNode.operator()<UAnimGraphNode_LayeredBoneBlend>(TEXT("Heal_ArmsBlend"));
	Layer->Node.BlendMode = ELayeredBoneBlendMode::BranchFilter; Layer->Node.LayerSetup.SetNum(1);
	for (FName Bone : ArmBones) { FBranchFilter Filter; Filter.BoneName = Bone; Filter.BlendDepth = 0; Layer->Node.LayerSetup[0].BranchFilters.Add(Filter); }
	Layer->Node.bMeshSpaceRotationBlend = false; // Arms retain local source rotations; spine/head stay entirely in base pose.
	Layer->Node.bBlendRootMotionBasedOnRootBone = true; Layer->AllocateDefaultPins();
	auto Output = [](UEdGraphNode* Node) -> UEdGraphPin* { for (UEdGraphPin* Pin : Node->Pins) if (Pin->Direction == EGPD_Output) return Pin; return nullptr; };
	const UEdGraphSchema* Schema = Graph->GetSchema(); Schema->BreakSinglePinLink(UpperOutput, Target);
	const TPair<UEdGraphPin*, UEdGraphPin*> Links[] = {{UpperOutput, Cache->FindPin(TEXT("Pose"))}, {Output(Base), Layer->FindPin(TEXT("BasePose"))},
		{Output(Source), Slot->FindPin(TEXT("Source"))}, {Output(Slot), Layer->FindPin(TEXT("BlendPoses_0"))}, {Output(Layer), Target}};
	for (const auto& Link : Links) if (!Link.Key || !Link.Value || !Schema->TryCreateConnection(Link.Key, Link.Value)) return false;
	int32 X = UpperLayer->NodePosX + 300;
	UEdGraphNode* AddedNodes[] = {Cache, Base, Source, Slot, Layer};
	for (UEdGraphNode* Node : AddedNodes) { Node->NodePosX = X; Node->NodePosY = Node == Source || Node == Slot ? 450 : 0; X += 250; }
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(ABP); FKismetEditorUtilities::CompileBlueprint(ABP);
	if (!TestTrue(TEXT("ABP compiled"), ABP->Status == BS_UpToDate) || !Save(ABP)) return false;
	AddInfo(FString::Printf(TEXT("HealWeaponAuthor: Stow=%.9f Heal=%.9f Draw=%.9f WeaponStow=%.9f HPNotify=%.9f WeaponDraw=%.9f UpperBranch=spine ArmsBranches=clavicle_L/R"),
		Stow->GetPlayLength(), Heal->GetPlayLength(), Draw->GetPlayLength(), Stow->GetPlayLength() * StowFraction, Stow->GetPlayLength() + Heal->GetPlayLength() * .5f, Draw->GetPlayLength() * DrawFraction));
	return true;
}
#endif
