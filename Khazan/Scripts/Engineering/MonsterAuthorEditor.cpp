// Compiled ONLY in the isolated work editor. Public authoring/reflection APIs.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "AI/KZMonsterAIController.h"
#include "AI/KZMonsterStateTreeNodes.h"
#include "Character/KZMonster.h"
#include "Animation/KZAnimInstance.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Data/KZAssetData.h"
#include "KZGameplayTags.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/CurveIdentifier.h"
#include "Components/CapsuleComponent.h"
#include "Components/BrushComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/World.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_BlendSpacePlayer.h"
#include "AnimGraphNode_BlendListByEnum.h"
#include "AnimGraphNode_Slot.h"
#include "AnimGraphNode_Inertialization.h"
#include "K2Node_VariableGet.h"
#include "K2Node_CallFunction.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_BlendListByBool.h"
#include "AnimGraphNode_LocalToComponentSpace.h"
#include "AnimGraphNode_ComponentToLocalSpace.h"
#include "AnimGraphNode_CopyBone.h"
#include "AnimGraph/AnimGraphNode_FootPlacement.h"
#include "AnimGraphNode_LegIK.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Factories/AnimBlueprintFactory.h"
#include "StateTree.h"
#include "StateTreeEditorData.h"
#include "StateTreeState.h"
#include "StateTreeCompiler.h"
#include "StateTreeCompilerLog.h"
#include "Components/StateTreeAIComponentSchema.h"
#include "NavigationSystem.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Builders/CubeBuilder.h"
#include "ActorFactories/ActorFactory.h"
#include "Editor.h"
#include "FileHelpers.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "EngineUtils.h"

namespace KZMonsterAuthor
{
TArray<FString> ChangedAssets;
bool IsWork() { return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_MonsterWork_20261006")); }
bool Save(UObject* Asset)
{
	UPackage* Package = Asset->GetOutermost();
	Package->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	const bool bSaved = UPackage::SavePackage(Package, Asset, *FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
	if (bSaved) ChangedAssets.AddUnique(Package->GetName());
	return bSaved;
}
template<typename T> T* Asset(const FString& Path)
{
	if (T* Existing = LoadObject<T>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing;
	T* Result = NewObject<T>(CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional);
	FAssetRegistryModule::AssetCreated(Result);
	return Result;
}
UBlueprint* Blueprint(const FString& Path, UClass* Parent)
{
	if (UBlueprint* Existing = LoadObject<UBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing;
	UBlueprint* Result = FKismetEditorUtilities::CreateBlueprint(Parent, CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), BPTYPE_Normal, UBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass());
	FAssetRegistryModule::AssetCreated(Result);
	return Result;
}
void ObjectProperty(UObject* Owner, const TCHAR* Name, UObject* Value)
{
	FindFProperty<FObjectPropertyBase>(Owner->GetClass(), Name)->SetObjectPropertyValue_InContainer(Owner, Value);
}
void FloatProperty(UObject* Owner, const TCHAR* Name, float Value)
{
	FindFProperty<FFloatProperty>(Owner->GetClass(), Name)->SetPropertyValue_InContainer(Owner, Value);
}
template<typename T> T& Value(UObject* Owner, const TCHAR* Name)
{
	return *FindFProperty<FProperty>(Owner->GetClass(), Name)->ContainerPtrToValuePtr<T>(Owner);
}
UAnimSequence* CloneClip(const FString& Family, const FString& Source)
{
	const FString Destination = TEXT("/Game/Monsters/") + Family + TEXT("/Animations/InGame/") + FPackageName::GetLongPackageAssetName(Source);
	UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *Destination, nullptr, LOAD_NoWarn);
	if (!Clip)
	{
		UAnimSequence* Original = LoadObject<UAnimSequence>(nullptr, *Source);
		if (!Original) return nullptr;
		Clip = DuplicateObject<UAnimSequence>(Original, CreatePackage(*Destination), *FPackageName::GetLongPackageAssetName(Destination));
		Clip->SetFlags(RF_Public | RF_Standalone | RF_Transactional);
		FAssetRegistryModule::AssetCreated(Clip);
	}
	// Animation-only combat: navigation drives the capsule. Preserve source poses/rate/scale.
	Clip->bEnableRootMotion = false;
	Clip->bForceRootLock = true;
	Clip->RootMotionRootLock = ERootMotionRootLock::RefPose;
	Save(Clip);
	return Clip;
}
void MontageNotify(UAnimMontage* Montage, float Time)
{
	UAnimNotify_PlayMontageNotify* Notify = NewObject<UAnimNotify_PlayMontageNotify>(Montage, NAME_None, RF_Transactional);
	FindFProperty<FNameProperty>(Notify->GetClass(), TEXT("NotifyName"))->SetPropertyValue_InContainer(Notify, TEXT("InputEnd"));
	FAnimNotifyEvent Event; Event.Notify = Notify; Event.NotifyName = TEXT("InputEnd");
	Event.MontageTickType = EMontageNotifyTickType::BranchingPoint; Event.Guid = FGuid::NewGuid(); Event.Link(Montage, Time);
	Montage->Notifies.Add(Event);
}
UClass* Ability(const FString& Family, const TSharedPtr<FJsonObject>& Pattern)
{
	const FString Id = Pattern->GetStringField(TEXT("id"));
	const FString Base = TEXT("/Game/Monsters/") + Family;
	UAnimMontage* Montage = Asset<UAnimMontage>(Base + TEXT("/Animations/AM_") + Id);
	UKZComboDefinitionData* Definition = Asset<UKZComboDefinitionData>(Base + TEXT("/Data/DA_Combo_") + Id);
	FSlotAnimationTrack Track; Track.SlotName = TEXT("DefaultSlot");
	Montage->CompositeSections.Reset(); Montage->Notifies.Reset();
	TArray<FKZComboNode>& Nodes = Value<TArray<FKZComboNode>>(Definition, TEXT("Nodes")); Nodes.Reset();
	float Position = 0.f;
	const TArray<TSharedPtr<FJsonValue>>& Steps = Pattern->GetArrayField(TEXT("steps"));
	for (const TSharedPtr<FJsonValue>& Entry : Steps)
	{
		const TSharedPtr<FJsonObject> Step = Entry->AsObject();
		UAnimSequence* Clip = CloneClip(Family, Step->GetStringField(TEXT("playback")));
		if (!Clip) return nullptr;
		Montage->SetSkeleton(Clip->GetSkeleton());
		FString StepName = Step->GetStringField(TEXT("step")); StepName.RemoveFromStart(TEXT("ESubStateStepByActiveInput::"));
		FAnimSegment Segment; Segment.SetAnimReference(Clip); Segment.StartPos = Position;
		Segment.AnimStartTime = 0.f; Segment.AnimEndTime = Clip->GetPlayLength();
		Segment.AnimPlayRate = Step->GetNumberField(TEXT("anim_play_rate")); Segment.LoopingCount = Step->GetIntegerField(TEXT("anim_loop_count"));
		Track.AnimTrack.AnimSegments.Add(Segment);
		FCompositeSection Section; Section.SectionName = *StepName; Section.NextSectionName = NAME_None; Section.Link(Montage, Position);
		Montage->CompositeSections.Add(Section);
		FKZComboNode Node; Node.NodeId = *StepName; Node.Montage = Montage; Node.SectionName = *StepName;
		double SwitchTime;
		if (Step->TryGetNumberField(TEXT("transition_seconds"), SwitchTime))
		{
			FString Next = Step->GetStringField(TEXT("target_step")); Next.RemoveFromStart(TEXT("ESubStateStepByActiveInput::"));
			FKZComboCommandEdge Edge; Edge.CommandTag = KZGameplayTags::Command_Player_Attack_X;
			Edge.CommandPhase = EKZComboCommandPhase::InputEnd; Edge.TargetNodeId = *Next; Node.CommandEdges.Add(Edge);
			MontageNotify(Montage, Position + SwitchTime / Segment.AnimPlayRate);
		}
		Nodes.Add(Node);
		Position += Segment.GetLength();
	}
	Montage->SlotAnimTracks = {Track};
	Montage->BlendIn.SetBlendTime(Steps[0]->AsObject()->GetNumberField(TEXT("blend_alpha")));
	Montage->BlendOut.SetBlendTime(0.2f); // Temporary presentation setting, documented in AuthoringPlan.
	Montage->BlendOutTriggerTime = 0.f;
	Montage->GetController().SetFrameRate(FFrameRate(30, 1), false); // Saved enemy playback grid.
	Montage->GetController().SetNumberOfFrames(FFrameRate(30, 1).AsFrameTime(Position).RoundToFrame(), false);
	Montage->SortNotifies(); Montage->RefreshCacheData();
	Save(Montage); Save(Definition);
	UBlueprint* BP = Blueprint(Base + TEXT("/Abilities/GA_") + Id, UKZComboActionAbility::StaticClass());
	UObject* CDO = BP->GeneratedClass->GetDefaultObject();
	ObjectProperty(CDO, TEXT("ComboDefinition"), Definition);
	FindFProperty<FNameProperty>(CDO->GetClass(), TEXT("EntryNodeId"))->SetPropertyValue_InContainer(CDO, Nodes[0].NodeId);
	FloatProperty(CDO, TEXT("ComboTransitionInertializationDuration"), 0.1f); // Temporary: one owner setting for node jumps.
	FloatProperty(CDO, TEXT("LocomotionExitInertializationDuration"), 0.2f); // Temporary; does not alter Player settings.
	FGameplayTagContainer Tags; Tags.AddTag(Id == TEXT("Alert") ? KZGameplayTags::Ability_Action : KZGameplayTags::Ability_Action_Attack);
	CastChecked<UGameplayAbility>(CDO)->EditorGetAssetTags() = Tags;
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP); Save(BP);
	return BP->GeneratedClass;
}
UStateTree* Tree()
{
	UStateTree* Result = Asset<UStateTree>(TEXT("/Game/Monsters/AI/ST_Monster"));
	UStateTreeEditorData* Data = NewObject<UStateTreeEditorData>(Result, NAME_None, RF_Transactional);
	Result->EditorData = Data;
	UStateTreeAIComponentSchema* Schema = NewObject<UStateTreeAIComponentSchema>(Data);
	FindFProperty<FClassProperty>(Schema->GetClass(), TEXT("AIControllerClass"))->SetPropertyValue_InContainer(Schema, AKZMonsterAIController::StaticClass());
	FindFProperty<FClassProperty>(Schema->GetClass(), TEXT("ContextActorClass"))->SetPropertyValue_InContainer(Schema, AKZMonster::StaticClass()); Schema->PostLoad(); Data->Schema = Schema;
	const FGuid ControllerId = Data->FindContextData(AKZMonsterAIController::StaticClass(), TEXT("AIController")).ID;
	UStateTreeState& Root = Data->AddRootState();
	const EKZMonsterTask Tasks[] = {EKZMonsterTask::Alert, EKZMonsterTask::Chase, EKZMonsterTask::Attack, EKZMonsterTask::Standoff, EKZMonsterTask::Patrol, EKZMonsterTask::Idle};
	const EKZMonsterCondition Conditions[] = {EKZMonsterCondition::NeedsAlert, EKZMonsterCondition::NeedsChase, EKZMonsterCondition::CanAttack, EKZMonsterCondition::HasTarget, EKZMonsterCondition::WantsPatrol, EKZMonsterCondition::NoTarget};
	const TCHAR* Names[] = {TEXT("Alert"), TEXT("Chase"), TEXT("Attack"), TEXT("Standoff"), TEXT("Patrol"), TEXT("Idle")};
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(Tasks); ++Index)
	{
		UStateTreeState& State = Root.AddChildState(Names[Index]);
		auto& Task = State.AddTask<FKZMonsterStateTreeTask>(); Task.GetNode().Task = Tasks[Index];
		auto& Condition = State.AddEnterCondition<FKZMonsterStateTreeCondition>(); Condition.GetNode().Condition = Conditions[Index];
		Data->AddPropertyBinding(FPropertyBindingPath(ControllerId), FPropertyBindingPath(Task.ID, TEXT("AIController")));
		Data->AddPropertyBinding(FPropertyBindingPath(ControllerId), FPropertyBindingPath(Condition.ID, TEXT("AIController")));
		State.AddTransition(EStateTreeTransitionTrigger::OnStateCompleted, EStateTreeTransitionType::GotoState, &Root);
	}
	FStateTreeCompilerLog Log; FStateTreeCompiler Compiler(Log);
	if (!Compiler.Compile(*Result))
	{
		for (const auto& Message : Log.ToTokenizedMessages()) UE_LOG(LogTemp, Error, TEXT("Monster StateTree: %s"), *Message->ToText().ToString());
		return nullptr;
	}
	Save(Result); return Result;
}
template<typename T> T* Node(UEdGraph* Graph, int32 X, int32 Y)
{
	T* Result = NewObject<T>(Graph); Result->CreateNewGuid(); Result->NodePosX = X; Result->NodePosY = Y;
	Graph->AddNode(Result, false, false);
	Result->PostPlacedNewNode(); // Ensures animation node bindings and compiler extensions are registered.
	return Result;
}
UK2Node_VariableGet* Getter(UEdGraph* Graph, FName Name, int32 X, int32 Y)
{
	auto* Result = Node<UK2Node_VariableGet>(Graph, X, Y);
	Result->VariableReference.SetSelfMember(Name); Result->AllocateDefaultPins(); return Result;
}
UK2Node_CallFunction* MathNode(UEdGraph* Graph, FName Function, int32 X, int32 Y)
{
	auto* Result = Node<UK2Node_CallFunction>(Graph, X, Y);
	Result->SetFromFunction(UKismetMathLibrary::StaticClass()->FindFunctionByName(Function));
	Result->AllocateDefaultPins(); return Result;
}
void ShowRate(UAnimGraphNode_Base* Player)
{
	const auto& Pins = Value<TArray<FOptionalPinFromProperty>>(Player, TEXT("ShowPinForProperties"));
	const int32 Index = Pins.IndexOfByPredicate([](const FOptionalPinFromProperty& Pin) { return Pin.PropertyName == TEXT("PlayRate"); });
	if (Index != INDEX_NONE) Player->SetPinVisibility(true, Index);
}
void InertialBlend(FAnimNode_BlendListBase& Blend)
{
	*FindFProperty<FArrayProperty>(FAnimNode_BlendListBase::StaticStruct(), TEXT("BlendTime"))->ContainerPtrToValuePtr<TArray<float>>(&Blend) = {0.2f, 0.2f};
	*FindFProperty<FEnumProperty>(FAnimNode_BlendListBase::StaticStruct(), TEXT("TransitionType"))->ContainerPtrToValuePtr<EBlendListTransitionType>(&Blend) = EBlendListTransitionType::Inertialization;
}
UAnimBlueprint* AnimationBP(const FString& Family, USkeleton* Skeleton, USkeletalMesh* Preview, const TMap<FString, UAnimSequence*>& Clips, float WalkSpeed, float RunSpeed)
{
	const FString Base = TEXT("/Game/Monsters/") + Family + TEXT("/Animations/");
	UBlendSpace* Peace = Asset<UBlendSpace>(Base + TEXT("BS_Peace_") + Family);
	UBlendSpace* Combat = Asset<UBlendSpace>(Base + TEXT("BS_Combat_") + Family);
	for (UBlendSpace* Space : {Peace, Combat})
	{
		Space->SetSkeleton(Skeleton);
		Value<TArray<FBlendSample>>(Space, TEXT("SampleData")).Reset();
		auto* Params = FindFProperty<FStructProperty>(Space->GetClass(), TEXT("BlendParameters"))->ContainerPtrToValuePtr<FBlendParameter>(Space);
		Params[0].DisplayName = TEXT("Direction"); Params[0].Min = -180.f; Params[0].Max = 180.f; Params[0].GridNum = 8; Params[0].bWrapInput = true;
		Params[1].DisplayName = TEXT("Speed"); Params[1].Min = 0.f; Params[1].Max = RunSpeed; Params[1].GridNum = 4;
		Space->TargetWeightInterpolationSpeedPerSec = 0.f; // Pose transitions use the one downstream Inertialization node.
	}
	for (int32 Index = 0; Index <= 4; ++Index)
	{
		const float Angle = -180.f + 90.f * Index;
		const TCHAR* Directions[] = {TEXT("B"), TEXT("L"), TEXT("F"), TEXT("R"), TEXT("B")};
		Peace->AddSample(Clips[TEXT("idle")], FVector(Angle, 0, 0));
		Peace->AddSample(Clips[TEXT("walk")], FVector(Angle, WalkSpeed, 0));
		Peace->AddSample(Clips[TEXT("run")], FVector(Angle, RunSpeed, 0));
		Combat->AddSample(Clips[TEXT("combat_idle")], FVector(Angle, 0, 0));
		Combat->AddSample(Clips[Directions[Index]], FVector(Angle, WalkSpeed, 0));
		Combat->AddSample(Clips[TEXT("run")], FVector(Angle, RunSpeed, 0));
	}
	for (UBlendSpace* Space : {Peace, Combat}) { Space->ValidateSampleData(); Space->ResampleData(); Save(Space); }
	const FString Path = Base + TEXT("ABP_") + Family;
	UAnimBlueprint* BP = LoadObject<UAnimBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn);
	if (!BP)
	{
		UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>(); Factory->ParentClass = UKZAnimInstance::StaticClass(); Factory->TargetSkeleton = Skeleton; Factory->PreviewSkeletalMesh = Preview;
		BP = CastChecked<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
		FAssetRegistryModule::AssetCreated(BP);
	}
	TArray<UEdGraph*> Graphs; BP->GetAllGraphs(Graphs);
	UEdGraph* Graph = *Graphs.FindByPredicate([](UEdGraph* G) { return G->GetFName() == TEXT("AnimGraph"); });
	UAnimGraphNode_Root* Root = nullptr;
	for (UEdGraphNode* N : TArray<TObjectPtr<UEdGraphNode>>(Graph->Nodes))
	{
		if (auto* R = Cast<UAnimGraphNode_Root>(N)) { Root = R; R->BreakAllNodeLinks(); }
		else Graph->RemoveNode(N);
	}
	auto* PeaceNode = Node<UAnimGraphNode_BlendSpacePlayer>(Graph, -900, -160); PeaceNode->SetAnimationAsset(Peace); PeaceNode->AllocateDefaultPins();
	auto* CombatNode = Node<UAnimGraphNode_BlendSpacePlayer>(Graph, -900, 180); CombatNode->SetAnimationAsset(Combat); CombatNode->AllocateDefaultPins();
	ShowRate(PeaceNode); ShowRate(CombatNode);
	auto* Blend = Node<UAnimGraphNode_BlendListByEnum>(Graph, -500, 0);
	ObjectProperty(Blend, TEXT("BoundEnum"), StaticEnum<EKZRotationMode>());
	Value<TArray<FName>>(Blend, TEXT("VisibleEnumEntries")) = {StaticEnum<EKZRotationMode>()->GetNameByValue(static_cast<int64>(EKZRotationMode::LockOn))};
	Blend->Node.AddPose(); // Constructor already created the default pose.
	*FindFProperty<FArrayProperty>(FAnimNode_BlendListBase::StaticStruct(), TEXT("BlendTime"))->ContainerPtrToValuePtr<TArray<float>>(&Blend->Node) = {0.2f, 0.2f};
	*FindFProperty<FEnumProperty>(FAnimNode_BlendListBase::StaticStruct(), TEXT("TransitionType"))->ContainerPtrToValuePtr<EBlendListTransitionType>(&Blend->Node) = EBlendListTransitionType::Inertialization;
	Blend->AllocateDefaultPins();
	auto* Run = Node<UAnimGraphNode_SequencePlayer>(Graph, -450, 330); Run->SetAnimationAsset(Clips[TEXT("run")]); Run->AllocateDefaultPins(); ShowRate(Run);
	auto* Stand = Node<UAnimGraphNode_SequencePlayer>(Graph, -200, 530); Stand->SetAnimationAsset(Clips[TEXT("combat_idle")]); Stand->AllocateDefaultPins();
	auto* PeaceStand = Node<UAnimGraphNode_SequencePlayer>(Graph, -500, 1050); PeaceStand->SetAnimationAsset(Clips[TEXT("idle")]); PeaceStand->AllocateDefaultPins();
	auto* Stationary = Node<UAnimGraphNode_BlendListByEnum>(Graph, -180, 1020);
	ObjectProperty(Stationary, TEXT("BoundEnum"), StaticEnum<EKZRotationMode>());
	Value<TArray<FName>>(Stationary, TEXT("VisibleEnumEntries")) = {StaticEnum<EKZRotationMode>()->GetNameByValue(static_cast<int64>(EKZRotationMode::LockOn))};
	Stationary->Node.AddPose(); InertialBlend(Stationary->Node); Stationary->AllocateDefaultPins();
	auto* Gait = Node<UAnimGraphNode_BlendListByEnum>(Graph, -180, 0);
	ObjectProperty(Gait, TEXT("BoundEnum"), StaticEnum<EKZGait>());
	Value<TArray<FName>>(Gait, TEXT("VisibleEnumEntries")) = {StaticEnum<EKZGait>()->GetNameByValue(static_cast<int64>(EKZGait::Run))};
	Gait->Node.AddPose(); InertialBlend(Gait->Node); Gait->AllocateDefaultPins();
	auto* Moving = Node<UAnimGraphNode_BlendListByBool>(Graph, 80, 0); InertialBlend(Moving->Node); Moving->AllocateDefaultPins();
	auto* Slot = Node<UAnimGraphNode_Slot>(Graph, 330, 0); Slot->Node.SlotName = TEXT("DefaultSlot"); Slot->AllocateDefaultPins();
	auto* Inertia = Node<UAnimGraphNode_Inertialization>(Graph, 580, 0); Inertia->AllocateDefaultPins();
	auto* Speed = Getter(Graph, TEXT("GroundSpeed"), -1650, -450);
	auto* Velocity = Getter(Graph, TEXT("VelocityLocal"), -1650, 20);
	auto* VectorRotation = MathNode(Graph, TEXT("Conv_VectorToRotator"), -1450, 20);
	auto* BreakRotation = MathNode(Graph, TEXT("BreakRotator"), -1250, 20);
	auto* WalkRate = MathNode(Graph, TEXT("Divide_DoubleDouble"), -1420, -460);
	auto* RunRate = MathNode(Graph, TEXT("Divide_DoubleDouble"), -1420, -300);
	WalkRate->FindPin(TEXT("B"))->DefaultValue = FString::SanitizeFloat(WalkSpeed);
	RunRate->FindPin(TEXT("B"))->DefaultValue = FString::SanitizeFloat(RunSpeed);
	auto* GaitValue = Getter(Graph, TEXT("ResolvedGait"), -430, -430);
	auto* IsMoving = Getter(Graph, TEXT("bIsMoving"), -140, -430);
	auto* Rotation = Getter(Graph, TEXT("RotationMode"), -700, -360);
	const UEdGraphSchema* Schema = Graph->GetSchema();
	auto Connect = [Schema](UEdGraphNode* A, FName APin, UEdGraphNode* B, FName BPin)
	{
		UEdGraphPin* From = A->FindPin(APin); UEdGraphPin* To = B->FindPin(BPin);
		if (!From || !To || !Schema->TryCreateConnection(From, To)) UE_LOG(LogTemp, Error, TEXT("Monster AnimGraph missing connection %s.%s -> %s.%s"), *A->GetName(), *APin.ToString(), *B->GetName(), *BPin.ToString());
	};
	Connect(Velocity, TEXT("VelocityLocal"), VectorRotation, TEXT("InVec")); Connect(VectorRotation, TEXT("ReturnValue"), BreakRotation, TEXT("InRot"));
	Connect(Speed, TEXT("GroundSpeed"), WalkRate, TEXT("A")); Connect(Speed, TEXT("GroundSpeed"), RunRate, TEXT("A"));
	// A linear blend of two orthogonal walks shortens the stride vector at diagonals.
	// w is the BlendSpace's angular weight inside a 90-degree sector, not a tuning value.
	auto* AbsAngle = MathNode(Graph, TEXT("Abs"), -1420, 660);
	auto* SectorAngle = MathNode(Graph, TEXT("Percent_FloatFloat"), -1240, 660); SectorAngle->FindPin(TEXT("B"))->DefaultValue = TEXT("90");
	auto* Fraction = MathNode(Graph, TEXT("Divide_DoubleDouble"), -1060, 660); Fraction->FindPin(TEXT("B"))->DefaultValue = TEXT("90");
	auto* Complement = MathNode(Graph, TEXT("Subtract_DoubleDouble"), -900, 740); Complement->FindPin(TEXT("A"))->DefaultValue = TEXT("1");
	auto* SquareA = MathNode(Graph, TEXT("Square"), -720, 660); auto* SquareB = MathNode(Graph, TEXT("Square"), -720, 800);
	auto* Sum = MathNode(Graph, TEXT("Add_DoubleDouble"), -540, 720); auto* Magnitude = MathNode(Graph, TEXT("Sqrt"), -350, 720);
	auto* CombatRate = MathNode(Graph, TEXT("Divide_DoubleDouble"), -110, 720);
	Connect(BreakRotation, TEXT("Yaw"), AbsAngle, TEXT("A")); Connect(AbsAngle, TEXT("ReturnValue"), SectorAngle, TEXT("A"));
	Connect(SectorAngle, TEXT("ReturnValue"), Fraction, TEXT("A")); Connect(Fraction, TEXT("ReturnValue"), Complement, TEXT("B"));
	Connect(Fraction, TEXT("ReturnValue"), SquareA, TEXT("A")); Connect(Complement, TEXT("ReturnValue"), SquareB, TEXT("A"));
	Connect(SquareA, TEXT("ReturnValue"), Sum, TEXT("A")); Connect(SquareB, TEXT("ReturnValue"), Sum, TEXT("B"));
	Connect(Sum, TEXT("ReturnValue"), Magnitude, TEXT("A")); Connect(Magnitude, TEXT("ReturnValue"), CombatRate, TEXT("B"));
	Connect(WalkRate, TEXT("ReturnValue"), CombatRate, TEXT("A"));
	for (auto* Player : {PeaceNode, CombatNode})
	{
		// Sample only the walk row. Stand is separate so its long loop cannot slow the step clock.
		Player->FindPin(TEXT("Y"))->DefaultValue = FString::SanitizeFloat(WalkSpeed);
		Connect(BreakRotation, TEXT("Yaw"), Player, TEXT("X"));
		Connect(Player == CombatNode ? CombatRate : WalkRate, TEXT("ReturnValue"), Player, TEXT("PlayRate"));
	}
	Connect(PeaceNode, TEXT("Pose"), Blend, TEXT("BlendPose_0")); Connect(CombatNode, TEXT("Pose"), Blend, TEXT("BlendPose_1"));
	Connect(Rotation, TEXT("RotationMode"), Blend, TEXT("ActiveEnumValue"));
	Connect(Blend, TEXT("Pose"), Gait, TEXT("BlendPose_0")); Connect(Run, TEXT("Pose"), Gait, TEXT("BlendPose_1"));
	Connect(GaitValue, TEXT("ResolvedGait"), Gait, TEXT("ActiveEnumValue")); Connect(RunRate, TEXT("ReturnValue"), Run, TEXT("PlayRate"));
	Connect(PeaceStand, TEXT("Pose"), Stationary, TEXT("BlendPose_0")); Connect(Stand, TEXT("Pose"), Stationary, TEXT("BlendPose_1"));
	Connect(Rotation, TEXT("RotationMode"), Stationary, TEXT("ActiveEnumValue"));
	Connect(Gait, TEXT("Pose"), Moving, TEXT("BlendPose_0")); Connect(Stationary, TEXT("Pose"), Moving, TEXT("BlendPose_1"));
	Connect(IsMoving, TEXT("bIsMoving"), Moving, TEXT("bActiveValue")); Connect(Moving, TEXT("Pose"), Slot, TEXT("Source"));
	Connect(Slot, TEXT("Pose"), Inertia, TEXT("Source")); Connect(Inertia, TEXT("Pose"), Root, TEXT("Result"));
	// Apply contact locking only to the walk branch, before Run/Stand and the action slot.
	const FReferenceSkeleton& Rig = Skeleton->GetReferenceSkeleton();
	const FName RigRoot = Rig.GetBoneName(0);
	for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
	{
		const FName Foot(*FString::Printf(TEXT("Bip001-%s-Foot"), Side));
		const FName Target(*FString::Printf(TEXT("VB KZFoot_%s"), Side));
		if (!Skeleton->GetVirtualBones().ContainsByPredicate([Target](const FVirtualBone& Bone) { return Bone.VirtualBoneName == Target; }))
			if (!Skeleton->AddNewNamedVirtualBone(RigRoot, Foot, Target)) { UE_LOG(LogTemp, Error, TEXT("Cannot add foot IK target %s"), *Target.ToString()); return BP; }
	}
	Save(Skeleton);
	auto* ToCS = Node<UAnimGraphNode_LocalToComponentSpace>(Graph, -470, 1400); ToCS->AllocateDefaultPins();
	auto* CopyL = Node<UAnimGraphNode_CopyBone>(Graph, -250, 1400);
	auto* CopyR = Node<UAnimGraphNode_CopyBone>(Graph, -20, 1400);
	auto* Plant = Node<UAnimGraphNode_FootPlacement>(Graph, 220, 1400);
	auto* IK = Node<UAnimGraphNode_LegIK>(Graph, 470, 1400);
	auto* ToLocal = Node<UAnimGraphNode_ComponentToLocalSpace>(Graph, 720, 1400); ToLocal->AllocateDefaultPins();
	for (int32 Index = 0; Index < 2; ++Index)
	{
		const TCHAR* Side = Index == 0 ? TEXT("L") : TEXT("R");
		const FName Foot(*FString::Printf(TEXT("Bip001-%s-Foot"), Side));
		const FName Target(*FString::Printf(TEXT("VB KZFoot_%s"), Side));
		auto* Copy = Index == 0 ? CopyL : CopyR;
		Copy->Node.SourceBone.BoneName = Foot; Copy->Node.TargetBone.BoneName = Target;
		Copy->Node.bCopyTranslation = Copy->Node.bCopyRotation = true; Copy->Node.ControlSpace = BCS_ComponentSpace; Copy->AllocateDefaultPins();
		FFootPlacemenLegDefinition Leg; Leg.FKFootBone.BoneName = Foot; Leg.IKFootBone.BoneName = Target;
		Leg.BallBone.BoneName = FName(*FString::Printf(TEXT("Bip001-%s-Toe0"), Side));
		Leg.SpeedCurveName = FName(*FString::Printf(TEXT("KZFootContactState_%s"), Side)); Plant->Node.LegDefinitions.Add(Leg);
		FAnimLegIKDefinition Solve; Solve.FKFootBone.BoneName = Foot; Solve.IKFootBone.BoneName = Target;
		Solve.bEnableKneeTwistCorrection = false; IK->Node.LegsDefinition.Add(Solve);
	}
	Plant->Node.PlantSpeedMode = EWarpingEvaluationMode::Manual;
	Plant->Node.PelvisBone.BoneName = TEXT("Bip001-Pelvis"); Plant->Node.IKFootRootBone.BoneName = RigRoot;
	// Technical contact mask: 0=plant, 2=flight; 1 separates the two states, not a game speed.
	Plant->Node.PlantSettings.SpeedThreshold = 1.f; Plant->Node.PlantSettings.UnalignmentSpeedThreshold = 2.f;
	Plant->Node.PlantSettings.LockType = EFootPlacementLockType::PivotAroundAnkle;
	// Halberd's diagonal plant needs the full remaining anatomical leg reach.
	// Technical tuning, not an original gameplay field: 1 uses the existing bone-chain limit.
	if (Family == TEXT("HalberdElite")) Plant->Node.PlantSettings.MaxExtensionRatio = 1.f;
	Plant->Node.TraceSettings.bDisableComplexTrace = true;
	Plant->AllocateDefaultPins(); IK->AllocateDefaultPins();
	Gait->FindPin(TEXT("BlendPose_0"))->BreakAllPinLinks();
	Connect(Blend, TEXT("Pose"), ToCS, TEXT("LocalPose"));
	Connect(ToCS, TEXT("ComponentPose"), CopyL, TEXT("ComponentPose")); Connect(CopyL, TEXT("Pose"), CopyR, TEXT("ComponentPose"));
	Connect(CopyR, TEXT("Pose"), Plant, TEXT("ComponentPose")); Connect(Plant, TEXT("Pose"), IK, TEXT("ComponentPose"));
	Connect(IK, TEXT("Pose"), ToLocal, TEXT("ComponentPose")); Connect(ToLocal, TEXT("Pose"), Gait, TEXT("BlendPose_0"));
	// UE Foot Placement owns plant memory, but its evaluator reads floor/owner data.
	// Disable parallel update/evaluation only on these NPC ABPs to honor the snapshot boundary.
	FindFProperty<FBoolProperty>(BP->GeneratedClass, TEXT("bRequiresGameThreadPoseEvaluation"))->SetPropertyValue_InContainer(BP->GeneratedClass->GetDefaultObject(), true);
	BP->bUseMultiThreadedAnimationUpdate = false;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP); Save(BP); return BP;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterAuthor, "Khazan.Monster.Author", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterAuthor::RunTest(const FString& Parameters)
{
	using namespace KZMonsterAuthor;
	if (!IsWork()) return false;
	ChangedAssets.Reset();
	FString Text; if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectDir() / TEXT("Scripts/Engineering/AuthoringPlan.json")))) return false;
	TArray<TSharedPtr<FJsonValue>> Families; if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Families)) return false;
	UStateTree* StateTree = Tree(); if (!StateTree) return false;
	UKZAssetData* Registry = LoadObject<UKZAssetData>(nullptr, TEXT("/Game/Data/PDA_AssetData")); if (!Registry) return false;
	auto& Groups = Value<TMap<FName, FAssetSet>>(Registry, TEXT("AssetGroupNameToSet"));
	FAssetSet& MonsterSet = Groups.FindOrAdd(TEXT("MonsterDefinitions")); MonsterSet.AssetEntries.Reset();
	TArray<UClass*> Classes;
	for (const auto& Entry : Families)
	{
		const auto Family = Entry->AsObject(); const FString Name = Family->GetStringField(TEXT("family"));
		UBlueprint* Art = LoadObject<UBlueprint>(nullptr, *Family->GetStringField(TEXT("art_bp")));
		USCS_Node* ArtBody = *Art->SimpleConstructionScript->GetAllNodes().FindByPredicate([](USCS_Node* N) { return N->GetVariableName() == TEXT("EnemyBody"); });
		auto* Body = CastChecked<USkeletalMeshComponent>(ArtBody->ComponentTemplate);
		TMap<FString, UAnimSequence*> Clips;
		for (const auto& Pair : Family->GetObjectField(TEXT("clips"))->Values) { UAnimSequence* Clip = CloneClip(Name, Pair.Value->AsString()); if (!Clip) return false; Clips.Add(FString(Pair.Key), Clip); }
		USkeleton* Skeleton = Clips[TEXT("idle")]->GetSkeleton();
		TestEqual(TEXT("Body rig matches animation"), Body->GetSkeletalMeshAsset()->GetSkeleton(), Skeleton);
		if (!Skeleton->ContainsSlotName(TEXT("DefaultSlot"))) { Skeleton->RegisterSlotNode(TEXT("DefaultSlot")); Save(Skeleton); }
		const auto Tuning = Family->GetObjectField(TEXT("temporary"));
		UAnimBlueprint* ABP = AnimationBP(Name, Skeleton, Body->GetSkeletalMeshAsset(), Clips, Tuning->GetNumberField(TEXT("walk_speed")), Tuning->GetNumberField(TEXT("run_speed")));
		if (ABP->Status == BS_Error) return false;
		TArray<TSubclassOf<UGameplayAbility>> Attacks;
		for (const auto& Pattern : Family->GetArrayField(TEXT("attacks"))) { UClass* Class = Ability(Name, Pattern->AsObject()); if (!Class) return false; Attacks.Add(Class); }
		UClass* Alert = Ability(Name, Family->GetObjectField(TEXT("alert"))); if (!Alert) return false;
		const FString DefinitionPath = TEXT("/Game/Monsters/") + Name + TEXT("/Data/DA_Character_") + Name;
		UKZCharacterDefinitionData* Definition = Asset<UKZCharacterDefinitionData>(DefinitionPath);
		auto& Config = Value<FKZLocomotionConfig>(Definition, TEXT("LocomotionConfig"));
		Config.WalkSpeed = Tuning->GetNumberField(TEXT("walk_speed")); Config.RunSpeed = Config.SprintSpeed = Tuning->GetNumberField(TEXT("run_speed"));
		Config.DefaultMaxAllowedGait = EKZGait::Run; Config.DefaultRequestedGait = EKZGait::Walk;
		// Existing FKZLocomotionConfig acceleration/braking/rotation defaults are preserved, unverified original values.
		auto& Grants = Value<TArray<FKZInitialAbilityGrant>>(Definition, TEXT("InitialAbilityGrants")); Grants.Reset();
		for (auto Class : Attacks) { FKZInitialAbilityGrant Grant; Grant.AbilityClass = Class; Grants.Add(Grant); }
		FKZInitialAbilityGrant AlertGrant; AlertGrant.AbilityClass = Alert; Grants.Add(AlertGrant); Save(Definition);
		FGameplayTag DefinitionTag = FGameplayTag::RequestGameplayTag(*FString(TEXT("AssetData.CharacterDefinition.") + Name));
		FAssetEntry AssetEntry; AssetEntry.AssetName = DefinitionTag; AssetEntry.AssetPath = FSoftObjectPath(Definition); AssetEntry.AssetLabels = {KZGameplayTags::AssetLabel_Preload}; MonsterSet.AssetEntries.Add(AssetEntry);
		UBlueprint* BP = Blueprint(TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Name, AKZMonster::StaticClass());
		AKZMonster* CDO = CastChecked<AKZMonster>(BP->GeneratedClass->GetDefaultObject());
		Value<FGameplayTag>(CDO, TEXT("CharacterDefinitionAssetName")) = DefinitionTag;
		ObjectProperty(CDO, TEXT("AIStateTree"), StateTree); ObjectProperty(CDO, TEXT("AlertAbility"), Alert);
		Value<TArray<TSubclassOf<UGameplayAbility>>>(CDO, TEXT("AttackAbilities")) = Attacks;
		auto& Settings = Value<FKZMonsterAISettings>(CDO, TEXT("AISettings"));
		Settings.EngageDistance = Tuning->GetNumberField(TEXT("engage_distance")); Settings.PreferredDistance = Tuning->GetNumberField(TEXT("preferred_distance")); Settings.AttackDistance = Tuning->GetNumberField(TEXT("attack_distance"));
		const float HalfHeight = Family->GetNumberField(TEXT("capsule_half_height"));
		CDO->GetCapsuleComponent()->SetCapsuleSize(Family->GetNumberField(TEXT("capsule_radius")), HalfHeight);
		USkeletalMeshComponent* Mesh = CDO->GetMesh();
		Mesh->SetSkeletalMeshAsset(Body->GetSkeletalMeshAsset()); Mesh->SetRelativeTransform(Body->GetRelativeTransform()); Mesh->AddLocalOffset(FVector(0, 0, -HalfHeight));
		Mesh->SetAnimInstanceClass(ABP->GeneratedClass); Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		for (int32 Material = 0; Material < Body->GetNumMaterials(); ++Material) Mesh->SetMaterial(Material, Body->GetMaterial(Material));
		CDO->GetCharacterMovement()->bUseRVOAvoidance = true;
		// Use existing original-art component sockets and transforms; do not reconstruct weapons.
		for (USCS_Node* Old : Art->SimpleConstructionScript->GetAllNodes())
		{
			const FString Variable = Old->GetVariableName().ToString();
			if (Variable == TEXT("EnemyBody") || Variable == TEXT("DefaultSceneRoot")) continue;
			USCS_Node* New = BP->SimpleConstructionScript->FindSCSNode(Old->GetVariableName());
			if (!New) { New = BP->SimpleConstructionScript->CreateNode(Old->ComponentClass, Old->GetVariableName()); BP->SimpleConstructionScript->AddNode(New); }
			UEngine::CopyPropertiesForUnrelatedObjects(Old->ComponentTemplate, New->ComponentTemplate);
			New->AttachToName = Old->AttachToName; New->SetParent(Mesh);
			if (Variable.StartsWith(TEXT("EnemyArmor"))) New->ComponentTemplate->ComponentTags.AddUnique(TEXT("MonsterBodyPart"));
		}
		// Component exists on KZMonster; use the same upper-body anchor height as current capsule.
		const_cast<USceneComponent*>(CDO->GetLockOnTargetPoint())->SetRelativeLocation(FVector(0, 0, HalfHeight * 0.5f)); // Temporary presentation anchor.
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
		if (!TestTrue(TEXT("Monster BP compiled"), BP->Status != BS_Error)) return false;
		Save(BP); Classes.Add(BP->GeneratedClass);
		AddInfo(FString::Printf(TEXT("Created %s: attacks=%d scale=%s capsule=%.3f rig=%s"), *Name, Attacks.Num(), *Mesh->GetRelativeScale3D().ToString(), HalfHeight, *Skeleton->GetPathName()));
	}
	Save(Registry);
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World || World->GetOutermost()->GetName() != TEXT("/Game/Maps/DevMap")) return false;
	TArray<AActor*> Remove;
	for (TActorIterator<AActor> It(World); It; ++It) if (It->GetClass()->GetPathName() == TEXT("/Game/Bluprints/TEST_Monster.TEST_Monster_C") || It->GetActorLabel().StartsWith(TEXT("DevAI_"))) Remove.Add(*It);
	for (AActor* Actor : Remove) World->EditorDestroyActor(Actor, true);
	const FVector Points[] = {FVector(1900, -1300, 0), FVector(1900, 1300, 0), FVector(-1900, 1300, 0), FVector(-1900, -1300, 0)};
	for (int32 Index = 0; Index < Classes.Num(); ++Index)
	{
		const AKZMonster* CDO = Classes[Index]->GetDefaultObject<AKZMonster>();
		FVector Location = Points[Index]; Location.Z = CDO->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
		AActor* Actor = World->SpawnActor(Classes[Index], &Location, nullptr);
		Actor->SetActorLabel(TEXT("DevAI_") + Families[Index]->AsObject()->GetStringField(TEXT("family")));
		Actor->SetFolderPath(TEXT("DevMap/Monster AI"));
	}
	ANavMeshBoundsVolume* Bounds = nullptr;
	for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It) if (It->GetActorLabel() == TEXT("DevAI_Navigation")) Bounds = *It;
	if (!Bounds)
	{
		Bounds = World->SpawnActor<ANavMeshBoundsVolume>(); Bounds->SetActorLabel(TEXT("DevAI_Navigation"));
		UCubeBuilder* Builder = NewObject<UCubeBuilder>(); Builder->X = 7800.f; Builder->Y = 7800.f; Builder->Z = 600.f;
		UActorFactory::CreateBrushForVolumeActor(Bounds, Builder);
	}
	Bounds->GetBrushComponent()->BuildSimpleBrushCollision();
	Bounds->ReregisterAllComponents();
	if (UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World)) { Navigation->OnNavigationBoundsUpdated(Bounds); Navigation->Build(); }
	World->GetOutermost()->MarkPackageDirty(); FEditorFileUtils::SaveLevel(World->PersistentLevel);
	ChangedAssets.AddUnique(TEXT("/Game/Maps/DevMap"));
	FString Output; for (const FString& Path : ChangedAssets) Output += Path + TEXT("\n");
	IFileManager::Get().MakeDirectory(*(FPaths::ProjectSavedDir() / TEXT("MonsterAI")), true);
	FFileHelper::SaveStringToFile(Output, *(FPaths::ProjectSavedDir() / TEXT("MonsterAI/ChangedAssets.txt")));
	return !HasAnyErrors();
}

// The latest main skeleton files are copied into the CLOSED work editor first.
// Add only the slot required by the new gameplay montages, preserving other edits.
namespace KZMonsterAuthor
{
float MeasureStride(UAnimSequence* Clip, const FTransform& MeshTransform, const FVector& MoveDirection, TArray<TSharedPtr<FJsonValue>>& Reports)
{
	const IAnimationDataModel* Model = Clip->GetDataModel();
	const FReferenceSkeleton& Rig = Clip->GetSkeleton()->GetReferenceSkeleton();
	TArray<int32> Feet;
	for (int32 Bone = 0; Bone < Rig.GetNum(); ++Bone)
	{
		const FString Name = Rig.GetBoneName(Bone).ToString().ToLower();
		if (Name.Contains(TEXT("foot")) && !Name.Contains(TEXT("ik")) && !Name.Contains(TEXT("toe")) && !Name.StartsWith(TEXT("vb "))) Feet.Add(Bone);
	}
	if (Feet.Num() != 2) return 0.f;
	const int32 Keys = Model->GetNumberOfKeys();
	const double Dt = Model->GetFrameRate().AsInterval();
	TArray<FVector> Positions[2];
	for (int32 Frame = 0; Frame < Keys; ++Frame)
	{
		TArray<FTransform> Component; Component.SetNum(Rig.GetNum());
		for (int32 Bone = 0; Bone < Rig.GetNum(); ++Bone)
		{
			const FName Name = Rig.GetBoneName(Bone);
			const FTransform Local = Bone > 0 && Model->IsValidBoneTrackName(Name) ? Model->GetBoneTrackTransform(Name, FFrameNumber(Frame)) : Rig.GetRefBonePose()[Bone];
			const int32 Parent = Rig.GetParentIndex(Bone);
			Component[Bone] = Parent == INDEX_NONE ? Local : Local * Component[Parent];
		}
		for (int32 Foot = 0; Foot < 2; ++Foot) Positions[Foot].Add(MeshTransform.TransformPosition(Component[Feet[Foot]].GetTranslation()));
	}
	TArray<float> ContactSpeeds; TArray<TSharedPtr<FJsonValue>> Samples, Markers;
	Clip->AuthoredSyncMarkers.RemoveAll([](const FAnimSyncMarker& M) { return M.MarkerName == TEXT("KZLeftPlant") || M.MarkerName == TEXT("KZRightPlant"); });
	for (int32 Foot = 0; Foot < 2; ++Foot)
	{
		double MinZ = TNumericLimits<double>::Max(), MaxZ = -TNumericLimits<double>::Max();
		for (const FVector& Point : Positions[Foot]) { MinZ = FMath::Min(MinZ, Point.Z); MaxZ = FMath::Max(MaxZ, Point.Z); }
		// Analysis heuristic, not original gameplay metadata: lowest 15% of foot height, minimum 0.5cm.
		const double Band = FMath::Max(0.5, (MaxZ - MinZ) * 0.15);
		// Derive one plant event per foot from the longest circular stance interval.
		// These are calculated playback markers, not original Notify timestamps.
		const int32 CycleFrames = Keys - 1; TArray<bool> Contact; Contact.SetNum(CycleFrames);
		for (int32 Frame = 0; Frame < CycleFrames; ++Frame)
		{
			const FVector V = (Positions[Foot][(Frame+1)%CycleFrames] - Positions[Foot][(Frame+CycleFrames-1)%CycleFrames]) / (2.0*Dt);
			Contact[Frame] = Positions[Foot][Frame].Z <= MinZ+Band && FVector::DotProduct(V, MoveDirection) < 0.0;
		}
		int32 PlantFrame = INDEX_NONE, Longest = 0;
		for (int32 Frame = 0; Frame < CycleFrames; ++Frame)
		{
			if (!Contact[Frame] || Contact[(Frame+CycleFrames-1)%CycleFrames]) continue;
			int32 Count = 0; while (Count < CycleFrames && Contact[(Frame+Count)%CycleFrames]) ++Count;
			if (Count > Longest) { Longest = Count; PlantFrame = Frame; }
		}
		if (PlantFrame == INDEX_NONE) return 0.f;
		// Calculated contact proxy for the engine's Manual Foot Placement input.
		// The height/projection heuristic is the same explicitly documented stride analysis.
		const FString Side = Rig.GetBoneName(Feet[Foot]).ToString().Contains(TEXT("-L-")) ? TEXT("L") : TEXT("R");
		FAnimationCurveIdentifier ContactId(FName(*(TEXT("KZFootContactState_") + Side)), ERawCurveTrackTypes::RCT_Float);
		IAnimationDataController& Controller = Clip->GetController();
		if (!Model->FindFloatCurve(ContactId)) Controller.AddCurve(ContactId, AACF_DefaultCurve, false);
		TArray<FRichCurveKey> ContactKeys;
		for (int32 Frame = 0; Frame < Keys; ++Frame)
		{
			FRichCurveKey Key(Frame*Dt, Contact[Frame%CycleFrames] ? 0.f : 2.f); Key.InterpMode = RCIM_Constant; ContactKeys.Add(Key);
		}
		Controller.SetCurveKeys(ContactId, ContactKeys, false);
		FAnimSyncMarker Marker; Marker.MarkerName = Rig.GetBoneName(Feet[Foot]).ToString().Contains(TEXT("-L-")) ? TEXT("KZLeftPlant") : TEXT("KZRightPlant");
		Marker.Time = PlantFrame*Dt; Marker.TrackIndex = 0; Marker.Guid = FGuid::NewGuid(); Clip->AuthoredSyncMarkers.Add(Marker);
		auto MarkerRow = MakeShared<FJsonObject>(); MarkerRow->SetStringField(TEXT("name"), Marker.MarkerName.ToString()); MarkerRow->SetNumberField(TEXT("frame"), PlantFrame); MarkerRow->SetNumberField(TEXT("time_seconds"), Marker.Time); MarkerRow->SetNumberField(TEXT("stance_frames"), Longest); Markers.Add(MakeShared<FJsonValueObject>(MarkerRow));
		for (int32 Frame = 1; Frame + 1 < Keys; ++Frame)
		{
			const FVector Velocity = (Positions[Foot][Frame + 1] - Positions[Foot][Frame - 1]) / (2.0 * Dt);
			const double Speed = -FVector::DotProduct(Velocity, MoveDirection) * Clip->RateScale;
			if (Positions[Foot][Frame].Z > MinZ + Band || Speed <= 0.0) continue;
			ContactSpeeds.Add(Speed);
			auto Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("bone"), Rig.GetBoneName(Feet[Foot]).ToString());
			Row->SetNumberField(TEXT("frame"), Frame); Row->SetNumberField(TEXT("stance_speed_cm_per_s"), Speed); Samples.Add(MakeShared<FJsonValueObject>(Row));
		}
	}
	if (ContactSpeeds.IsEmpty()) return 0.f;
	ContactSpeeds.Sort(); const float Speed = ContactSpeeds[ContactSpeeds.Num() / 2];
	auto Report = MakeShared<FJsonObject>(); Report->SetStringField(TEXT("clip"), Clip->GetPathName());
	Report->SetNumberField(TEXT("frame_interval_seconds"), Dt); Report->SetNumberField(TEXT("keys"), Keys);
	Report->SetStringField(TEXT("mesh_transform"), MeshTransform.ToString()); Report->SetStringField(TEXT("direction"), MoveDirection.ToString());
	Report->SetNumberField(TEXT("reference_speed_cm_per_s"), Speed); Report->SetNumberField(TEXT("analysis_contact_height_fraction"), 0.15);
	Report->SetNumberField(TEXT("analysis_minimum_contact_band_cm"), 0.5); Report->SetArrayField(TEXT("selected_samples"), Samples);
	Report->SetArrayField(TEXT("derived_sync_markers"), Markers);
	if (Clip->AnimNotifyTracks.IsEmpty()) Clip->AnimNotifyTracks.AddDefaulted();
	Clip->RefreshCacheData(); Save(Clip);
	Reports.Add(MakeShared<FJsonValueObject>(Report)); return Speed;
}
bool RepairLocomotion(TArray<TSharedPtr<FJsonValue>>& Strides)
{
	FString Text; if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectDir() / TEXT("Scripts/Engineering/AuthoringPlan.json")))) return false;
	TArray<TSharedPtr<FJsonValue>> Families; if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Families)) return false;
	for (const auto& Entry : Families)
	{
		const auto Family = Entry->AsObject(); const FString Name = Family->GetStringField(TEXT("family"));
		UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *(TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Name));
		AKZMonster* CDO = BP->GeneratedClass->GetDefaultObject<AKZMonster>();
		TMap<FString, UAnimSequence*> Clips; TMap<FString, float> Speeds;
		for (const auto& Pair : Family->GetObjectField(TEXT("clips"))->Values)
		{
			const FString Path = TEXT("/Game/Monsters/") + Name + TEXT("/Animations/InGame/") + FPackageName::GetLongPackageAssetName(Pair.Value->AsString());
			Clips.Add(FString(Pair.Key), LoadObject<UAnimSequence>(nullptr, *Path));
		}
		const TMap<FString, FVector> Directions = {{TEXT("walk"), FVector::ForwardVector}, {TEXT("run"), FVector::ForwardVector}, {TEXT("F"), FVector::ForwardVector}, {TEXT("R"), FVector::RightVector}, {TEXT("B"), -FVector::ForwardVector}, {TEXT("L"), -FVector::RightVector}};
		for (const auto& Pair : Directions)
		{
			const float Speed = MeasureStride(Clips[Pair.Key], CDO->GetMesh()->GetRelativeTransform(), Pair.Value, Strides);
			if (Speed <= 0.f) { UE_LOG(LogTemp, Error, TEXT("Cannot measure locomotion stride %s %s"), *Name, *Pair.Key); return false; }
			Speeds.Add(Pair.Key, Speed);
		}
		const float WalkSpeed = Speeds[TEXT("walk")], RunSpeed = Speeds[TEXT("run")];
		UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *(TEXT("/Game/Monsters/") + Name + TEXT("/Data/DA_Character_") + Name));
		auto& Config = Value<FKZLocomotionConfig>(Definition, TEXT("LocomotionConfig")); Config.WalkSpeed = WalkSpeed; Config.RunSpeed = Config.SprintSpeed = RunSpeed; Save(Definition);
		UAnimBlueprint* ABP = AnimationBP(Name, CDO->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton(), CDO->GetMesh()->GetSkeletalMeshAsset(), Clips, WalkSpeed, RunSpeed);
		if (ABP->Status == BS_Error) return false;
		for (bool Combat : {false, true})
		{
			UBlendSpace* Space = LoadObject<UBlendSpace>(nullptr, *(TEXT("/Game/Monsters/") + Name + TEXT("/Animations/BS_") + (Combat ? TEXT("Combat_") : TEXT("Peace_")) + Name));
			for (FBlendSample& Sample : Value<TArray<FBlendSample>>(Space, TEXT("SampleData")))
			{
				if (!FMath::IsNearlyEqual(static_cast<float>(Sample.SampleValue.Y), WalkSpeed)) continue;
				const FString Key = !Combat ? TEXT("walk") : Sample.SampleValue.X == 0.0 ? TEXT("F") : Sample.SampleValue.X == 90.0 ? TEXT("R") : Sample.SampleValue.X == -90.0 ? TEXT("L") : TEXT("B");
				Sample.RateScale = WalkSpeed / Speeds[Key];
			}
			Space->ValidateSampleData(); Space->ResampleData(); Save(Space);
		}
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP); Save(BP);
		UE_LOG(LogTemp, Display, TEXT("MonsterStride %s walk=%.3f run=%.3f"), *Name, WalkSpeed, RunSpeed);
	}
	return true;
}
void UpdateWaitingPlacement()
{
	UWorld* World = GEditor->GetEditorWorldContext().World();
	UClass* SwordClass = LoadClass<AKZMonster>(nullptr, TEXT("/Game/Bluprints/Monsters/BP_Monster_Swordsman.BP_Monster_Swordsman_C"));
	for (TActorIterator<AKZMonster> It(World); It; ++It)
		if (It->GetActorLabel() == TEXT("DevAI_Swordsman")) Value<FName>(*It, TEXT("UnawareRoutineName")) = TEXT("Guard");
	const TCHAR* Labels[] = {TEXT("Basic"), TEXT("Search"), TEXT("Sit"), TEXT("Talk01"), TEXT("Talk02"), TEXT("Patrol")};
	const FVector Points[] = {FVector(-3100,-1600,102), FVector(-3100,0,102), FVector(-3100,1600,102), FVector(3000,-500,102), FVector(3000,-250,102), FVector(3000,2600,102)};
	TArray<AKZMonster*> Actors;
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(Labels); ++Index)
	{
		const FString Label = FString(TEXT("DevIdle_")) + Labels[Index]; AKZMonster* Actor = nullptr;
		for (TActorIterator<AKZMonster> It(World); It; ++It) if (It->GetActorLabel() == Label) Actor = *It;
		if (!Actor) { Actor = World->SpawnActor<AKZMonster>(SwordClass, Points[Index], FRotator::ZeroRotator); Actor->SetActorLabel(Label); }
		Actor->SetFolderPath(TEXT("DevMap/Monster AI/Waiting"));
		Value<FName>(Actor, TEXT("UnawareRoutineName")) = Index < 3 ? FName(Labels[Index]) : NAME_None;
		Value<bool>(Actor, TEXT("bPatrolWhenUnaware")) = Index == 5;
		Actors.Add(Actor);
	}
	ObjectProperty(Actors[3], TEXT("TalkPartner"), Actors[4]); ObjectProperty(Actors[4], TEXT("TalkPartner"), Actors[3]);
	Value<bool>(Actors[3], TEXT("bSecondTalkRole")) = false; Value<bool>(Actors[4], TEXT("bSecondTalkRole")) = true;
	Actors[3]->SetActorRotation((Actors[4]->GetActorLocation() - Actors[3]->GetActorLocation()).Rotation());
	Actors[4]->SetActorRotation((Actors[3]->GetActorLocation() - Actors[4]->GetActorLocation()).Rotation());
	World->MarkPackageDirty(); FEditorFileUtils::SaveLevel(World->PersistentLevel);
	ChangedAssets.AddUnique(World->GetOutermost()->GetName());
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterUnawareAuthor, "Khazan.Monster.UnawareAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterUnawareAuthor::RunTest(const FString& Parameters)
{
	using namespace KZMonsterAuthor;
	if (!IsWork()) return false;
	ChangedAssets.Reset();
	FString Text; if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectDir() / TEXT("Scripts/Engineering/IdleAuthoringPlan.json")))) return false;
	TArray<TSharedPtr<FJsonValue>> Families; if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Families)) return false;
	for (const auto& Entry : Families)
	{
		const auto Family = Entry->AsObject(); const FString Name = Family->GetStringField(TEXT("family"));
		UKZCharacterDefinitionData* Character = LoadObject<UKZCharacterDefinitionData>(nullptr, *(TEXT("/Game/Monsters/") + Name + TEXT("/Data/DA_Character_") + Name));
		auto& Routines = Value<TArray<FKZUnawareRoutine>>(Character, TEXT("UnawareRoutines")); Routines.Reset();
		auto& Grants = Value<TArray<FKZInitialAbilityGrant>>(Character, TEXT("InitialAbilityGrants"));
		for (const auto& Item : Family->GetArrayField(TEXT("routines")))
		{
			const auto Routine = Item->AsObject(); const FString Id = TEXT("Idle_") + Routine->GetStringField(TEXT("id"));
			auto Pattern = MakeShared<FJsonObject>(); Pattern->SetStringField(TEXT("id"), Id);
			TArray<TSharedPtr<FJsonValue>> Steps;
			for (const auto& StepValue : Routine->GetArrayField(TEXT("steps")))
			{
				auto Step = MakeShared<FJsonObject>(); Step->Values = StepValue->AsObject()->Values;
				Step->SetStringField(TEXT("step"), Step->GetStringField(TEXT("phase")));
				Step->SetNumberField(TEXT("anim_play_rate"), 1.0); Step->SetNumberField(TEXT("anim_loop_count"), 1); Step->SetNumberField(TEXT("blend_alpha"), 0.2); // Existing temporary presentation setting.
				Steps.Add(MakeShared<FJsonValueObject>(Step));
			}
			Pattern->SetArrayField(TEXT("steps"), Steps); UClass* Class = Ability(Name, Pattern); if (!Class) return false;
			const FString Base = TEXT("/Game/Monsters/") + Name;
			UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, *(Base + TEXT("/Animations/AM_") + Id));
			Montage->CompositeSections[0].NextSectionName = TEXT("Loop"); Montage->RefreshCacheData(); Save(Montage);
			UKZComboDefinitionData* Combo = LoadObject<UKZComboDefinitionData>(nullptr, *(Base + TEXT("/Data/DA_Combo_") + Id));
			FKZComboCommandEdge Edge; Edge.CommandTag = KZGameplayTags::Command_AI_Alert; Edge.CommandPhase = EKZComboCommandPhase::Release; Edge.TargetNodeId = TEXT("End");
			Value<TArray<FKZComboNode>>(Combo, TEXT("Nodes"))[0].CommandEdges = {Edge}; Save(Combo);
			UBlueprint* BP = CastChecked<UBlueprint>(Class->ClassGeneratedBy); auto* AbilityCDO = CastChecked<UGameplayAbility>(Class->GetDefaultObject());
			FGameplayTagContainer Tags; Tags.AddTag(KZGameplayTags::Ability_Action); AbilityCDO->EditorGetAssetTags() = Tags;
			Value<FGameplayTagContainer>(AbilityCDO, TEXT("ActivationOwnedTags")).RemoveTag(KZGameplayTags::Block_StaminaRegen);
			FBlueprintEditorUtils::MarkBlueprintAsModified(BP); FKismetEditorUtilities::CompileBlueprint(BP); Save(BP);
			if (!Grants.ContainsByPredicate([Class](const FKZInitialAbilityGrant& G) { return G.AbilityClass == Class; })) { FKZInitialAbilityGrant Grant; Grant.AbilityClass = Class; Grants.Add(Grant); }
			FKZUnawareRoutine Result; Result.Name = *Routine->GetStringField(TEXT("id")); Result.AbilityClass = Class;
			const FString Role = Routine->GetStringField(TEXT("role")); Result.Role = Role == TEXT("Talk01") ? EKZUnawareRoutineRole::Talk01 : Role == TEXT("Talk02") ? EKZUnawareRoutineRole::Talk02 : EKZUnawareRoutineRole::Solo;
			Routines.Add(Result);
		}
		Save(Character);
	}
	if (!Tree()) return false;
	TArray<TSharedPtr<FJsonValue>> Strides; if (!RepairLocomotion(Strides)) return false;
	UpdateWaitingPlacement();
	IFileManager::Get().MakeDirectory(*(FPaths::ProjectSavedDir() / TEXT("MonsterIdle")), true);
	FString Json; FJsonSerializer::Serialize(Strides, TJsonWriterFactory<>::Create(&Json)); FFileHelper::SaveStringToFile(Json, *(FPaths::ProjectSavedDir() / TEXT("MonsterIdle/StrideAnalysis.json")));
	FString Output; for (const FString& Path : ChangedAssets) Output += Path + TEXT("\n"); FFileHelper::SaveStringToFile(Output, *(FPaths::ProjectSavedDir() / TEXT("MonsterIdle/ChangedAssets.txt")));
	return !HasAnyErrors();
}

// Add only the slot required by the new gameplay montages, preserving other edits.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSkeletonSlots, "Khazan.Monster.SkeletonSlots", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterSkeletonSlots::RunTest(const FString& Parameters)
{
	using namespace KZMonsterAuthor;
	if (!IsWork()) { AddError(TEXT("Skeleton slot authoring is isolated-work-only")); return false; }
	ChangedAssets.Reset();
	const TCHAR* Paths[] = {
		TEXT("/Game/_Art/Enemies/HeinMach/Shared/Skeletons/SKEL_EN_EmpireHuman"),
		TEXT("/Game/_Art/Enemies/HeinMach/Shared/Skeletons/SKEL_EN_C_M_Human_Elite_M_Skeleton"),
		TEXT("/Game/_Art/Enemies/HeinMach/Humanoids/HalberdElite/Meshes/Skeletons/SKEL_EN_C_M_HalberdV2")};
	for (const TCHAR* Path : Paths)
	{
		USkeleton* Skeleton = LoadObject<USkeleton>(nullptr, Path);
		if (!TestNotNull(TEXT("Existing enemy skeleton loaded"), Skeleton)) return false;
		if (!Skeleton->ContainsSlotName(TEXT("DefaultSlot"))) Skeleton->RegisterSlotNode(TEXT("DefaultSlot"));
		if (!TestTrue(TEXT("Required gameplay montage slot exists"), Skeleton->ContainsSlotName(TEXT("DefaultSlot")))) return false;
		if (!Save(Skeleton)) return false;
	}
	FString Output; for (const FString& Path : ChangedAssets) Output += Path + TEXT("\n");
	FFileHelper::SaveStringToFile(Output, *(FPaths::ProjectSavedDir() / TEXT("MonsterAI/SlotAssets.txt")));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFootAuthor, "Khazan.Monster.FootAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterFootAuthor::RunTest(const FString& Parameters)
{
	using namespace KZMonsterAuthor;
	if (!IsWork()) { AddError(TEXT("Foot authoring is isolated-work-only")); return false; }
	ChangedAssets.Reset(); TArray<TSharedPtr<FJsonValue>> Strides;
	if (!RepairLocomotion(Strides)) return false;
	FString Json; FJsonSerializer::Serialize(Strides, TJsonWriterFactory<>::Create(&Json));
	FFileHelper::SaveStringToFile(Json, *(FPaths::ProjectSavedDir() / TEXT("MonsterIdle/StrideAnalysis_FootPlacement.json")));
	FString Output; for (const FString& Path : ChangedAssets) Output += Path + TEXT("\n");
	FFileHelper::SaveStringToFile(Output, *(FPaths::ProjectSavedDir() / TEXT("MonsterIdle/FootChangedAssets.txt")));
	return !HasAnyErrors();
}
#endif

