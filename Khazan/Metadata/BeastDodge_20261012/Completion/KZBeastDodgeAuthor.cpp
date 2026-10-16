// Task-owned editor authoring only. Removed before stock/Main delivery.
#if WITH_EDITOR
#include "AI/KZMonsterStateTreeNodes.h"
#include "AI/KZMonsterAIController.h"
#include "Abilities/GameplayAbility.h"
#include "StateTree.h"
#include "StateTreeEditorData.h"
#include "StateTreeState.h"
#include "StateTreeCompiler.h"
#include "StateTreeCompilerLog.h"
#include "Conditions/StateTreeCommonConditions.h"
#include "JsonObjectConverter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "HAL/IConsoleManager.h"
#include "UObject/SavePackage.h"
#include "AssetRegistry/AssetRegistryModule.h"

static FAutoConsoleCommand KZAuthorBeastTree(TEXT("KZ.BeastDodge.AuthorTree"), TEXT("Compile the reviewed owned StateTree plan."),
FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
{
	if (Args.Num() != 2 || !FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_BeastDodgeWork_20261012")) ||
		!Args[1].StartsWith(TEXT("/Game/Monsters/"))) return;
	FString Text;
	TSharedPtr<FJsonObject> Plan;
	if (!FFileHelper::LoadFileToString(Text, *Args[0]) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Plan)) return;
	const bool bApes = Plan->HasField(TEXT("family")) && Plan->GetStringField(TEXT("family")) == TEXT("Apes");
	UStateTree* Template = LoadObject<UStateTree>(nullptr, TEXT("/Game/Monsters/AI/ST_Monster.ST_Monster"));
	if (!Template) return;
	UPackage* Package = CreatePackage(*Args[1]);
	Package->FullyLoad();
	const FName AssetName(*FPackageName::GetLongPackageAssetName(Args[1]));
	UStateTree* Tree = DuplicateObject<UStateTree>(Template, Package, AssetName);
	UStateTreeEditorData* Data = Cast<UStateTreeEditorData>(Tree->EditorData);
	if (!Data) return;
	Data->SubTrees.Reset();
	Data->EditorBindings.Reset();
	const FStateTreeBindableStructDesc Controller = Data->FindContextData(AKZMonsterAIController::StaticClass(), TEXT("AIController"));
	UStateTreeState& Root = Data->AddRootState();
	Root.Name = TEXT("Original combat routing");
	TMap<FString, UStateTreeState*> States;
	auto AddState = [&](const FString& Id)
	{
		UStateTreeState& State = Root.AddChildState(FName(*Id));
		State.SelectionBehavior = EStateTreeStateSelectionBehavior::TryEnterState;
		States.Add(Id, &State);
		return &State;
	};
	AddState(TEXT("Bootstrap"))->SelectionBehavior = EStateTreeStateSelectionBehavior::TryFollowTransitions;
	AddState(TEXT("Idle")); AddState(TEXT("Alert")); AddState(TEXT("Passive"));
	AddState(TEXT("CombatRestart"))->SelectionBehavior = EStateTreeStateSelectionBehavior::TryFollowTransitions;
	if (bApes) { AddState(TEXT("ApesAttack")); AddState(TEXT("ApesStandoff")); AddState(TEXT("ApesChase")); }
	for (const auto& V : Plan->GetArrayField(TEXT("states"))) AddState(V->AsObject()->GetStringField(TEXT("id")));
	for (const auto& V : Plan->GetArrayField(TEXT("states")))
		if (V->AsObject()->GetStringField(TEXT("kind")) == TEXT("UseSkill")) AddState(TEXT("Execute_") + V->AsObject()->GetStringField(TEXT("id")));
	auto Bind = [&](FStateTreeEditorNode& Node)
	{
		FPropertyBindingPath Source; Source.SetStructID(Controller.ID);
		FPropertyBindingPath Target; Target.SetStructID(Node.ID); Target.FromString(TEXT("AIController"));
		Data->AddPropertyBinding(Source, Target);
	};
	auto Condition = [&](FStateTreeTransition& Transition, UStateTreeState* State, EKZMonsterCondition Kind)
	{
		auto& Node = Transition.AddConditionWithOuter<FKZMonsterStateTreeCondition>(State);
		Node.GetNode().Condition = Kind; Bind(Node);
		return &Node;
	};
	auto Link = [&](UStateTreeState* State, EStateTreeTransitionTrigger Trigger, const FString& Target)
	{
		return &State->AddTransition(Trigger, EStateTreeTransitionType::GotoState, States.FindRef(Target));
	};
	auto Task = [&](UStateTreeState* State, EKZMonsterTask Kind)
	{
		auto& Node = State->AddTask<FKZMonsterStateTreeTask>();
		Node.GetNode().Task = Kind; Bind(Node); return &Node.GetNode();
	};
	UStateTreeState* Boot = States[TEXT("Bootstrap")];
	Condition(*Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("Idle")), Boot, EKZMonsterCondition::NoTarget);
	Condition(*Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("Alert")), Boot, EKZMonsterCondition::NeedsAlert);
	Condition(*Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("Passive")), Boot, EKZMonsterCondition::PendingDamagePassive);
	if (bApes)
	{
		Condition(*Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("ApesAttack")), Boot, EKZMonsterCondition::CanAttack);
		Condition(*Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("ApesChase")), Boot, EKZMonsterCondition::NeedsChase);
		Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("ApesStandoff"));
		Task(States[TEXT("ApesAttack")], EKZMonsterTask::Attack);
		Task(States[TEXT("ApesChase")], EKZMonsterTask::Chase);
		Task(States[TEXT("ApesStandoff")], EKZMonsterTask::Standoff);
		for (const FString Id : {FString(TEXT("ApesAttack")), FString(TEXT("ApesChase")), FString(TEXT("ApesStandoff"))})
			Link(States[Id], EStateTreeTransitionTrigger::OnStateCompleted, TEXT("Bootstrap"));
		Condition(*Link(States[TEXT("ApesStandoff")], EStateTreeTransitionTrigger::OnTick, TEXT("Bootstrap")), States[TEXT("ApesStandoff")], EKZMonsterCondition::CanAttack);
	}
	else Link(Boot, EStateTreeTransitionTrigger::OnTick, TEXT("BT002"));
	Task(States[TEXT("Idle")], EKZMonsterTask::Idle);
	Condition(*Link(States[TEXT("Idle")], EStateTreeTransitionTrigger::OnTick, TEXT("Bootstrap")), States[TEXT("Idle")], EKZMonsterCondition::HasTarget);
	Task(States[TEXT("Alert")], EKZMonsterTask::Alert);
	Link(States[TEXT("Alert")], EStateTreeTransitionTrigger::OnStateCompleted, TEXT("Bootstrap"));
	FKZMonsterStateTreeTask* Passive = Task(States[TEXT("Passive")], EKZMonsterTask::SourceSkill);
	Passive->bUsePendingDamagePassive = true;
	Link(States[TEXT("Passive")], EStateTreeTransitionTrigger::OnStateCompleted, TEXT("Bootstrap"));
	Link(States[TEXT("CombatRestart")], EStateTreeTransitionTrigger::OnTick, TEXT("Bootstrap"));
	FStateTreeTransition* PassiveInterrupt = Link(&Root, EStateTreeTransitionTrigger::OnTick, TEXT("Passive"));
	PassiveInterrupt->Priority = EStateTreeTransitionPriority::High;
	Condition(*PassiveInterrupt, &Root, EKZMonsterCondition::PendingDamagePassive);
	for (const auto& Value : Plan->GetArrayField(TEXT("states")))
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		UStateTreeState* State = States[Row->GetStringField(TEXT("id"))];
		const FString Kind = Row->GetStringField(TEXT("kind"));
		const int32 Export = Row->GetIntegerField(TEXT("source_export"));
		if (Kind == TEXT("Route"))
		{
			State->SelectionBehavior = EStateTreeStateSelectionBehavior::TryFollowTransitions;
			const auto& Children = Row->GetArrayField(TEXT("children"));
			for (int32 Index = 0; Index < Children.Num(); ++Index)
			{
				FStateTreeTransition* Route = Link(State, EStateTreeTransitionTrigger::OnTick, FString::Printf(TEXT("BT%03d"), int32(Children[Index]->AsNumber())));
				if (Row->HasField(TEXT("random_threshold")) && Index == 0)
					Route->AddConditionWithOuter<FStateTreeRandomCondition>(State).GetInstanceData().Threshold = float(Row->GetNumberField(TEXT("random_threshold")));
				// Sequence advances at child completion; its first child is the entry.
				if (Row->GetStringField(TEXT("selection")) == TEXT("Composite_Sequence")) break;
			}
			continue;
		}
		auto AddGate = [&](FStateTreeTransition* Transition, bool Invert)
		{
			auto* Node = Condition(*Transition, State, EKZMonsterCondition::SourceGate);
			FKZMonsterStateTreeCondition& Gate = Node->GetNode();
			Gate.SourceExport = Export; Gate.bInvert = Invert;
			FJsonObjectConverter::JsonObjectToUStruct(Row->GetObjectField(TEXT("gate")).ToSharedRef(), &Gate.SourceGate);
			FString Skill;
			if (Row->TryGetStringField(TEXT("required_skill"), Skill)) Gate.RequiredSkill = FName(*Skill);
		};
		if (Kind == TEXT("Gate"))
		{
			State->SelectionBehavior = EStateTreeStateSelectionBehavior::TryFollowTransitions;
			AddGate(Link(State, EStateTreeTransitionTrigger::OnTick, Row->GetStringField(TEXT("true"))), false);
			AddGate(Link(State, EStateTreeTransitionTrigger::OnTick, Row->GetStringField(TEXT("false"))), true);
			continue;
		}
		UStateTreeState* ExecutionState = Kind == TEXT("UseSkill") ? States[TEXT("Execute_") + Row->GetStringField(TEXT("id"))] : State;
		FKZMonsterStateTreeTask* Action = Task(ExecutionState, Kind == TEXT("UseSkill") ? EKZMonsterTask::SourceSkill :
			Kind == TEXT("MoveTo") ? EKZMonsterTask::SourceMoveTo : EKZMonsterTask::SourceLockOnMove);
		Action->SourceExport = Export;
		if (Kind == TEXT("UseSkill"))
		{
			Action->SourceSkill = FName(*Row->GetStringField(TEXT("skill")));
			const FString ClassPath = Row->GetStringField(TEXT("ability_class"));
			Action->SourceAbility = LoadClass<UGameplayAbility>(nullptr, *ClassPath);
			// A failed selection must follow the original task's failure edge,
			// including after MoveTo completion. It must not stop the whole tree.
			State->SelectionBehavior = EStateTreeStateSelectionBehavior::TryFollowTransitions;
			auto* Node = Condition(*Link(State, EStateTreeTransitionTrigger::OnTick, TEXT("Execute_") + Row->GetStringField(TEXT("id"))), State, EKZMonsterCondition::SourceGate);
			Node->GetNode().SourceExport = Export;
			Node->GetNode().RequiredAbility = Action->SourceAbility;
			FJsonObjectConverter::JsonObjectToUStruct(Row->GetObjectField(TEXT("gate")).ToSharedRef(), &Node->GetNode().SourceGate);
			Link(State, EStateTreeTransitionTrigger::OnTick, Row->GetStringField(TEXT("failure")));
		}
		else if (Kind == TEXT("MoveTo"))
		{
			Action->SourceAcceptanceRadius = float(Row->GetNumberField(TEXT("acceptance")));
			Action->SourceMoveLimitSeconds = float(Row->GetNumberField(TEXT("limit")));
			Action->SourceFollowUpdateDistance = float(Row->GetNumberField(TEXT("follow_update_distance")));
			Action->SourceGait = Row->GetStringField(TEXT("gait")) == TEXT("Walk") ? EKZGait::Walk : EKZGait::Run;
		}
		else
		{
			Action->SourceGait = EKZGait::Walk;
			for (const auto& M : Row->GetArrayField(TEXT("move_settings")))
			{
				const auto& Raw = M->AsObject(); FKZSourceLockOnMove& Move = Action->SourceMoves.AddDefaulted_GetRef();
				const FString Direction = Raw->GetStringField(TEXT("Direction"));
				Move.LocalDirection = Direction.EndsWith(TEXT("LM_BACK")) ? FVector(-1, 0, 0) : Direction.EndsWith(TEXT("LM_LEFT")) ? FVector(0, -1, 0) : FVector(0, 1, 0);
				Move.Rate = float(Raw->GetNumberField(TEXT("Rate"))); Move.Distance = float(Raw->GetNumberField(TEXT("Dist")));
				Move.Seconds = float(Raw->GetNumberField(TEXT("MoveTime"))); Move.bByTime = Raw->GetBoolField(TEXT("bUseMoveByTime"));
				Move.bFinishByTargetDistance = Raw->GetBoolField(TEXT("bCheckFinishByTargetDist"));
				Move.FinishTargetDistance = float(Raw->GetNumberField(TEXT("FinishTargetDist")));
				Move.bDontCheckFrontNearDistance = Raw->GetBoolField(TEXT("bDontCheckFrontNearDist"));
			}
		}
		Link(ExecutionState, EStateTreeTransitionTrigger::OnStateSucceeded, Row->GetStringField(TEXT("success")));
		Link(ExecutionState, EStateTreeTransitionTrigger::OnStateFailed, Row->GetStringField(TEXT("failure")));
	}
	FStateTreeCompilerLog Log;
	FStateTreeCompiler Compiler(Log);
	if (!Compiler.Compile(*Tree)) { Log.DumpToLog(LogTemp); UE_LOG(LogTemp, Error, TEXT("Beast source StateTree compilation failed")); return; }
	FAssetRegistryModule::AssetCreated(Tree);
	Package->MarkPackageDirty();
	FSavePackageArgs Save; Save.TopLevelFlags = RF_Public | RF_Standalone;
	const FString Filename = FPackageName::LongPackageNameToFilename(Args[1], FPackageName::GetAssetPackageExtension());
	if (UPackage::SavePackage(Package, Tree, *Filename, Save))
		UE_LOG(LogTemp, Display, TEXT("BEAST_STATETREE_AUTHORED asset=%s states=%d source=121"), *Args[1], States.Num());
}));
#endif
