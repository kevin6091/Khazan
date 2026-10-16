// One-shot editor authoring tool. Compiled ONLY in the isolated Heal work project,
// never in the product module. Uses public UE editor APIs, not UObject memory patches.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/PlayerAbility/KZHealAbility.h"
#include "Attribute/KZAttributeSet.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Data/KZInputData.h"
#include "KZGameplayTags.h"
#include "GameplayEffect.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputCoreTypes.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/Skeleton.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "AnimGraphNode_SaveCachedPose.h"
#include "AnimGraphNode_UseCachedPose.h"
#include "AnimGraphNode_Slot.h"
#include "AnimGraphNode_LayeredBoneBlend.h"
#include "AnimGraphNode_Inertialization.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "Editor.h"
#include "PlayInEditorDataTypes.h"
#include "LevelEditor.h"
#include "IAssetViewport.h"
#include "HAL/IConsoleManager.h"

namespace KZHealAuthor
{
FAutoConsoleCommand StartPIE(TEXT("Khazan.Heal.StartPIE"), TEXT("Start PIE only in isolated Heal work editor."),
	FConsoleCommandDelegate::CreateLambda([]
	{
		if (!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_HealWork_20261006"))) return;
		FRequestPlaySessionParams Params;
		Params.bAllowOnlineSubsystem = false;
		Params.DestinationSlateViewport = TWeakPtr<IAssetViewport>(FModuleManager::LoadModuleChecked<FLevelEditorModule>(TEXT("LevelEditor")).GetFirstActiveViewport());
		GEditor->RequestPlaySession(Params);
	}));
FAutoConsoleCommand StopPIE(TEXT("Khazan.Heal.StopPIE"), TEXT("Stop PIE only in isolated Heal work editor."),
	FConsoleCommandDelegate::CreateLambda([]
	{
		if (FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_HealWork_20261006"))) GEditor->RequestEndPlayMap();
	}));
const TCHAR* Folder = TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/");
// User choices, not original-game metadata values.
constexpr float InitialHP = 200.f;
constexpr float RecoveryHP = 100.f;
// Temporary Montage authoring choices: original sequence has no notify timing.
// Fractions of the preserved source clip, adjustable by moving the authored notifies.
constexpr float HealFraction = 0.5f;
constexpr float InputEndFraction = 0.75f;
constexpr float BlendSeconds = 0.1f; // Reuse existing Guard expression tuning; not source metadata.

bool Save(UObject* Asset)
{
	UPackage* Package = Asset->GetOutermost();
	Package->MarkPackageDirty();
	FSavePackageArgs Args;
	Args.TopLevelFlags = RF_Public | RF_Standalone;
	return UPackage::SavePackage(Package, Asset,
		*FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}

FAutoConsoleCommand RefreshMontage(TEXT("Khazan.Heal.RefreshMontage"), TEXT("Refresh the exact saved Heal montage in isolated work editor."),
	FConsoleCommandDelegate::CreateLambda([]
	{
		if (!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_HealWork_20261006"))) return;
		UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, TEXT("/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal"));
		if (Montage) { Montage->RefreshCacheData(); Save(Montage); }
	}));

UBlueprint* Blueprint(const TCHAR* Path, UClass* Parent)
{
	if (FPackageName::DoesPackageExist(Path)) return LoadObject<UBlueprint>(nullptr, Path);
	UPackage* Package = CreatePackage(Path);
	UBlueprint* BP = FKismetEditorUtilities::CreateBlueprint(Parent, Package,
		FName(*FPackageName::GetShortName(Path)), BPTYPE_Normal);
	FAssetRegistryModule::AssetCreated(BP);
	return BP;
}

template<class T> T* Node(UEdGraph* Graph, FName Name)
{
	T* Result = NewObject<T>(Graph, Name, RF_Transactional);
	Graph->AddNode(Result, false, false);
	Result->CreateNewGuid();
	Result->PostPlacedNewNode(); // Registers the required CachedPose/other AnimBlueprint extensions.
	return Result;
}
UEdGraphPin* PoseOutput(UEdGraphNode* Node)
{
	for (UEdGraphPin* Pin : Node->Pins)
		if (Pin->Direction == EGPD_Output && Pin->PinType.PinCategory == TEXT("struct")) return Pin;
	return nullptr;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZHealAuthorTest, "Khazan.Heal.Author",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZHealAuthorTest::RunTest(const FString& Parameters)
{
	using namespace KZHealAuthor;
	if (!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_HealWork_20261006")))
	{
		AddError(TEXT("Heal authoring requires the isolated work project."));
		return false;
	}
	UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *(FString(Folder) + TEXT("CA_P_Kazan_DualAxeSword_Heal_01")));
	UAnimBlueprint* ABP = LoadObject<UAnimBlueprint>(nullptr, TEXT("/Game/_Art/Player/Character/Bluprints/ABP_Player"));
	UKZInputData* Input = LoadObject<UKZInputData>(nullptr, TEXT("/Game/Data/DA_InputData"));
	UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, TEXT("/Game/Data/Character/DA_CharacterDefinition_Player"));
	if (!TestNotNull(TEXT("Heal clip"), Clip) || !TestNotNull(TEXT("ABP"), ABP) ||
		!TestNotNull(TEXT("Input data"), Input) || !TestNotNull(TEXT("Player definition"), Definition)) return false;
	USkeleton* Skeleton = Clip->GetSkeleton();
	const FName UpperBone(TEXT("bip001-spine"));
	if (!TestTrue(TEXT("Upper-body branch exists"), Skeleton->GetReferenceSkeleton().FindBoneIndex(UpperBone) != INDEX_NONE)) return false;
	const FString MontagePath = FString(Folder) + TEXT("AM_DAS_Player_Heal");
	if (FindObject<UAnimMontage>(nullptr, *(MontagePath + TEXT(".AM_DAS_Player_Heal"))))
	{
		AddError(TEXT("One-shot authoring already ran; use saved assets for audit/test."));
		return false;
	}
	Skeleton->RegisterSlotNode(TEXT("UpperBody"));
	Skeleton->SetSlotGroupName(TEXT("UpperBody"), TEXT("DefaultGroup"));
	if (!TestTrue(TEXT("Save skeleton slot"), Save(Skeleton))) return false;
	UPackage* Package = CreatePackage(*MontagePath);
	UAnimMontage* Montage = NewObject<UAnimMontage>(Package, TEXT("AM_DAS_Player_Heal"), RF_Public | RF_Standalone | RF_Transactional);
	Montage->SetSkeleton(Skeleton);
	FSlotAnimationTrack Track;
	Track.SlotName = TEXT("UpperBody");
	FAnimSegment Segment;
	Segment.SetAnimReference(Clip);
	Segment.AnimStartTime = 0.f;
	Segment.AnimEndTime = Clip->GetPlayLength();
	Segment.AnimPlayRate = 1.f;
	Segment.LoopingCount = 1;
	Track.AnimTrack.AnimSegments.Add(Segment);
	Montage->SlotAnimTracks = {Track};
	Montage->GetController().SetFrameRate(Clip->GetDataModel()->GetFrameRate(), false);
	Montage->GetController().SetNumberOfFrames(Clip->GetDataModel()->GetNumberOfFrames(), false);
	Montage->BlendIn.SetBlendTime(BlendSeconds);
	Montage->BlendOut.SetBlendTime(BlendSeconds);
	Montage->BlendOutTriggerTime = 0.f;
	FCompositeSection Section;
	Section.SectionName = TEXT("Heal");
	Section.NextSectionName = NAME_None;
	Section.Link(Montage, 0.f);
	Montage->CompositeSections.Add(Section);
	const FName Names[] = {TEXT("Heal"), TEXT("InputEnd")};
	const float Fractions[] = {HealFraction, InputEndFraction};
	for (int32 Index = 0; Index < 2; ++Index)
	{
		UAnimNotify_PlayMontageNotify* Notify = NewObject<UAnimNotify_PlayMontageNotify>(Montage, Names[Index], RF_Transactional);
		FindFProperty<FNameProperty>(Notify->GetClass(), TEXT("NotifyName"))->SetPropertyValue_InContainer(Notify, Names[Index]);
		FAnimNotifyEvent Event;
		Event.NotifyName = Names[Index];
		Event.Notify = Notify;
		Event.MontageTickType = EMontageNotifyTickType::BranchingPoint;
		Event.Guid = FGuid::NewGuid();
		Event.Link(Montage, Clip->GetPlayLength() * Fractions[Index]);
		Montage->Notifies.Add(Event);
	}
	Montage->PostEditChange();
	Montage->RefreshCacheData(); // Builds branching-point markers for the newly authored notify events.
	FAssetRegistryModule::AssetCreated(Montage);
	if (!TestTrue(TEXT("Save Heal montage"), Save(Montage))) return false;

	UBlueprint* InitBP = Blueprint(TEXT("/Game/Bluprints/AbilitySystem/Effects/GE_Init_PlayerHealth"), UGameplayEffect::StaticClass());
	UBlueprint* HealBP = Blueprint(TEXT("/Game/Bluprints/AbilitySystem/Effects/GE_Player_Heal"), UGameplayEffect::StaticClass());
	for (UBlueprint* BP : {InitBP, HealBP})
	{
		UGameplayEffect* Effect = BP->GeneratedClass->GetDefaultObject<UGameplayEffect>();
		Effect->DurationPolicy = EGameplayEffectDurationType::Instant;
		Effect->Modifiers.Reset();
		if (BP == InitBP)
		{
			FGameplayModifierInfo Max;
			Max.Attribute = UKZAttributeSet::GetMaxHPAttribute();
			Max.ModifierOp = EGameplayModOp::Override;
			Max.ModifierMagnitude = FScalableFloat(InitialHP);
			Effect->Modifiers.Add(Max); // MaxHP must initialize before the clamped HP modifier.
		}
		FGameplayModifierInfo HP;
		HP.Attribute = UKZAttributeSet::GetHPAttribute();
		HP.ModifierOp = BP == InitBP ? EGameplayModOp::Override : EGameplayModOp::AddBase;
		HP.ModifierMagnitude = FScalableFloat(BP == InitBP ? InitialHP : RecoveryHP);
		Effect->Modifiers.Add(HP);
		FKismetEditorUtilities::CompileBlueprint(BP);
		if (!TestTrue(TEXT("Save HP effect"), Save(BP))) return false;
	}
	UBlueprint* AbilityBP = Blueprint(TEXT("/Game/Bluprints/AbilitySystem/Abilities/Player/Heal/GA_Player_Heal"), UKZHealAbility::StaticClass());
	UObject* CDO = AbilityBP->GeneratedClass->GetDefaultObject();
	FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("HealMontage"))->SetObjectPropertyValue_InContainer(CDO, Montage);
	FindFProperty<FClassProperty>(CDO->GetClass(), TEXT("HealEffect"))->SetObjectPropertyValue_InContainer(CDO, HealBP->GeneratedClass);
	FKismetEditorUtilities::CompileBlueprint(AbilityBP);
	if (!TestTrue(TEXT("Save Heal ability"), Save(AbilityBP))) return false;
	const TCHAR* IAPath = TEXT("/Game/Input/IA_Heal");
	UInputAction* Action = NewObject<UInputAction>(CreatePackage(IAPath), TEXT("IA_Heal"), RF_Public | RF_Standalone | RF_Transactional);
	Action->ValueType = EInputActionValueType::Boolean;
	FAssetRegistryModule::AssetCreated(Action);
	if (!TestTrue(TEXT("Save Heal input"), Save(Action))) return false;
	UInputMappingContext* IMC = Input->InputMappingContext;
	for (const FEnhancedActionKeyMapping& Mapping : IMC->GetMappings())
		if (Mapping.Key == EKeys::Gamepad_DPad_Down) { AddError(TEXT("DPad Down is already bound.")); return false; }
	IMC->MapKey(Action, EKeys::Gamepad_DPad_Down);
	FKZInputAction Row;
	Row.InputTag = KZGameplayTags::Input_Action_Heal;
	Row.InputAction = Action;
	Input->InputActions.Add(Row);
	if (!TestTrue(TEXT("Save input mapping"), Save(IMC)) || !TestTrue(TEXT("Save input data"), Save(Input))) return false;
	FKZInitialAbilityGrant Grant;
	Grant.AbilityClass = AbilityBP->GeneratedClass;
	Grant.InputTag = KZGameplayTags::Input_Action_Heal;
	auto* Grants = FindFProperty<FArrayProperty>(Definition->GetClass(), TEXT("InitialAbilityGrants"))->ContainerPtrToValuePtr<TArray<FKZInitialAbilityGrant>>(Definition);
	Grants->Add(Grant);
	auto* Effects = FindFProperty<FArrayProperty>(Definition->GetClass(), TEXT("InitialEffects"))->ContainerPtrToValuePtr<TArray<TSubclassOf<UGameplayEffect>>>(Definition);
	Effects->Add(TSubclassOf<UGameplayEffect>(InitBP->GeneratedClass.Get()));
	if (!TestTrue(TEXT("Save player grant/initial effect"), Save(Definition))) return false;

	UEdGraph* Graph = nullptr;
	for (UEdGraph* Candidate : ABP->FunctionGraphs) if (Candidate->GetFName() == TEXT("AnimGraph")) Graph = Candidate;
	if (!TestNotNull(TEXT("Current AnimGraph"), Graph)) return false;
	UAnimGraphNode_Slot* DefaultSlot = nullptr;
	UAnimGraphNode_Inertialization* Inertia = nullptr;
	for (UEdGraphNode* Existing : Graph->Nodes)
	{
		if (auto* Slot = Cast<UAnimGraphNode_Slot>(Existing); Slot && Slot->Node.SlotName == TEXT("DefaultSlot")) DefaultSlot = Slot;
		if (auto* Node = Cast<UAnimGraphNode_Inertialization>(Existing)) Inertia = Node;
	}
	if (!TestNotNull(TEXT("Existing DefaultSlot"), DefaultSlot) || !TestNotNull(TEXT("Existing Inertialization"), Inertia)) return false;
	UEdGraphPin* DefaultOutput = PoseOutput(DefaultSlot);
	UEdGraphPin* InertiaSource = Inertia->FindPin(TEXT("Source"));
	if (!TestTrue(TEXT("Existing final slot/inertia connection"), DefaultOutput && InertiaSource && InertiaSource->LinkedTo.Contains(DefaultOutput))) return false;
	TSet<UObject*> BeforeNodes;
	for (UEdGraphNode* Existing : Graph->Nodes) BeforeNodes.Add(Existing);
	FString BeforeText;
	FEdGraphUtilities::ExportNodesToText(BeforeNodes, BeforeText);
	FFileHelper::SaveStringToFile(BeforeText, *(FPaths::ProjectSavedDir() + TEXT("HealAnimGraph_Before.txt")));
	auto* Cache = Node<UAnimGraphNode_SaveCachedPose>(Graph, TEXT("Heal_ActionBase"));
	Cache->CacheName = TEXT("ActionBase");
	Cache->AllocateDefaultPins();
	auto* Base = Node<UAnimGraphNode_UseCachedPose>(Graph, TEXT("Heal_Base"));
	Base->SaveCachedPoseNode = Cache;
	Base->AllocateDefaultPins();
	auto* SlotSource = Node<UAnimGraphNode_UseCachedPose>(Graph, TEXT("Heal_SlotSource"));
	SlotSource->SaveCachedPoseNode = Cache;
	SlotSource->AllocateDefaultPins();
	auto* UpperSlot = Node<UAnimGraphNode_Slot>(Graph, TEXT("Heal_UpperBodySlot"));
	UpperSlot->Node.SlotName = TEXT("UpperBody");
	UpperSlot->Node.bAlwaysUpdateSourcePose = true;
	UpperSlot->AllocateDefaultPins();
	auto* Layer = Node<UAnimGraphNode_LayeredBoneBlend>(Graph, TEXT("Heal_UpperBodyBlend"));
	Layer->Node.BlendMode = ELayeredBoneBlendMode::BranchFilter;
	Layer->Node.LayerSetup.SetNum(1);
	FBranchFilter Filter;
	Filter.BoneName = UpperBone;
	Filter.BlendDepth = 0; // Full weight from this branch root; pelvis/legs are excluded by hierarchy.
	Layer->Node.LayerSetup[0].BranchFilters.Add(Filter);
	Layer->Node.bMeshSpaceRotationBlend = true;
	Layer->Node.bBlendRootMotionBasedOnRootBone = true;
	Layer->AllocateDefaultPins();
	const UEdGraphSchema* Schema = Graph->GetSchema();
	Schema->BreakSinglePinLink(DefaultOutput, InertiaSource);
	const TPair<UEdGraphPin*, UEdGraphPin*> Links[] = {
		{DefaultOutput, Cache->FindPin(TEXT("Pose"))},
		{PoseOutput(Base), Layer->FindPin(TEXT("BasePose"))},
		{PoseOutput(SlotSource), UpperSlot->FindPin(TEXT("Source"))},
		{PoseOutput(UpperSlot), Layer->FindPin(TEXT("BlendPoses_0"))},
		{PoseOutput(Layer), InertiaSource}
	};
	for (const auto& Link : Links)
	{
		if (!Link.Key || !Link.Value || !Schema->TryCreateConnection(Link.Key, Link.Value))
		{
			AddError(TEXT("Failed to connect Heal upper-body graph pins."));
			return false;
		}
	}
	int32 X = DefaultSlot->NodePosX + 300;
	UEdGraphNode* AddedNodes[] = {Cache, Base, SlotSource, UpperSlot, Layer};
	for (UEdGraphNode* Added : AddedNodes)
	{
		Added->NodePosX = X;
		Added->NodePosY = Added == SlotSource || Added == UpperSlot ? 350 : 0;
		X += 250;
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(ABP);
	FKismetEditorUtilities::CompileBlueprint(ABP);
	if (!TestTrue(TEXT("ABP compiles"), ABP->Status == BS_UpToDate) || !TestTrue(TEXT("Save upper-body graph"), Save(ABP))) return false;
	TSet<UObject*> AfterNodes;
	for (UEdGraphNode* Existing : Graph->Nodes) AfterNodes.Add(Existing);
	FString AfterText;
	FEdGraphUtilities::ExportNodesToText(AfterNodes, AfterText);
	FFileHelper::SaveStringToFile(AfterText, *(FPaths::ProjectSavedDir() + TEXT("HealAnimGraph_After.txt")));
	AddInfo(FString::Printf(TEXT("HealAuthor: clip=%.9fs rate=%.6f rootMotion=%d branch=%s Heal=%.9fs InputEnd=%.9fs MaxHP=%.1f HP=%.1f Recovery=%.1f"),
		Clip->GetPlayLength(), Clip->RateScale, Clip->bEnableRootMotion, *UpperBone.ToString(),
		Clip->GetPlayLength() * HealFraction, Clip->GetPlayLength() * InputEndFraction, InitialHP, InitialHP, RecoveryHP));
	return true;
}
#endif

