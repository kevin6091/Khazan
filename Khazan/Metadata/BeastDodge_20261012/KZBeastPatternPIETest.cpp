// Reads compiled assets and exercises real GAS/StateTree; no saved test fixtures.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "AI/KZMonsterAIController.h"
#include "AI/KZMonsterStateTreeNodes.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Components/StateTreeAIComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "StateTree.h"
#include "UObject/UnrealType.h"
#include "KZGameplayTags.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZBeastSourceAudit,"Khazan.BeastDodge.SourceAudit",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZBeastSourceAudit::RunTest(const FString&)
{
	UStateTree* Tree=LoadObject<UStateTree>(nullptr,TEXT("/Game/Monsters/Yetuga/AI/ST_Yetuga_Original.ST_Yetuga_Original"));
	if(!TestNotNull(TEXT("Saved compiled Yetuga tree"),Tree))return false;
	TestTrue(TEXT("Yetuga compiled tree ready"),Tree->IsReadyToRun());
	FString Text; TSharedPtr<FJsonObject> Plan;
	if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()+TEXT("Metadata/BeastDodge_20261012/YetugaStateTreeAuthor.json"))) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan)) { AddError(TEXT("Reviewed source plan unavailable")); return false; }
	TMap<FName,const FCompactStateTreeState*> States;
	for(const auto& S:Tree->GetStates())States.Add(S.Name,&S);
	TMap<int32,const FKZMonsterStateTreeTask*> Tasks;
	TMultiMap<int32,const FKZMonsterStateTreeCondition*> Gates;
	for(const auto& V:Tree->GetNodes())
	{
		if(const auto* Task=V.GetPtr<FKZMonsterStateTreeTask>();Task&&Task->SourceExport>=0)Tasks.Add(Task->SourceExport,Task);
		if(const auto* Gate=V.GetPtr<FKZMonsterStateTreeCondition>();Gate&&Gate->SourceExport>=0)Gates.Add(Gate->SourceExport,Gate);
	}
	int32 Routes=0,Branches=0,Skills=0,Moves=0,LockMoves=0;
	for(const auto& Value:Plan->GetArrayField(TEXT("states")))
	{
		const auto& R=Value->AsObject(); const FString Id=R->GetStringField(TEXT("id")),Kind=R->GetStringField(TEXT("kind")); const int32 Export=R->GetIntegerField(TEXT("source_export"));
		const FCompactStateTreeState* S=States.FindRef(FName(*Id));
		if(!TestNotNull(Id+TEXT(" has a compiled runtime state"),S))continue;
		if(Kind==TEXT("Route")){++Routes;TestEqual(Id+TEXT(" traverses during selection"),S->SelectionBehavior,EStateTreeStateSelectionBehavior::TryFollowTransitions);}
		if(Kind==TEXT("Gate")){++Branches;TestEqual(Id+TEXT(" branches during selection"),S->SelectionBehavior,EStateTreeStateSelectionBehavior::TryFollowTransitions);}
		if(R->HasField(TEXT("gate")))
		{
			TArray<const FKZMonsterStateTreeCondition*> Found;Gates.MultiFind(Export,Found);
			TestEqual(Id+TEXT(" gate copies"),Found.Num(),Kind==TEXT("Gate")?2:1);
			for(const auto* Gate:Found)for(const auto& Pair:R->GetObjectField(TEXT("gate"))->Values)
			{
				const FName Field(*Pair.Key);
				if(const auto* P=FindFProperty<FFloatProperty>(FKZCombatPatternCondition::StaticStruct(),Field))TestEqual(Id+TEXT(" raw ")+Pair.Key,double(P->GetPropertyValue_InContainer(&Gate->SourceGate)),Pair.Value->AsNumber());
				else if(const auto* B=FindFProperty<FBoolProperty>(FKZCombatPatternCondition::StaticStruct(),Field))TestEqual(Id+TEXT(" raw ")+Pair.Key,B->GetPropertyValue_InContainer(&Gate->SourceGate),Pair.Value->AsBool());
				else AddError(Id+TEXT(" unmapped field ")+Pair.Key);
			}
		}
		if(Kind==TEXT("Route")||Kind==TEXT("Gate"))continue;
		const auto* Task=Tasks.FindRef(Export); if(!TestNotNull(Id+TEXT(" executable source task"),Task))continue;
		if(Kind==TEXT("UseSkill")){++Skills;TestEqual(Id+TEXT(" source skill"),Task->SourceSkill.ToString(),R->GetStringField(TEXT("skill")));TestEqual(Id+TEXT(" exact class/forced entry"),Task->SourceAbility?Task->SourceAbility->GetPathName():FString(),R->GetStringField(TEXT("ability_class")));}
		if(Kind==TEXT("MoveTo")){++Moves;TestEqual(Id+TEXT(" acceptance"),double(Task->SourceAcceptanceRadius),R->GetNumberField(TEXT("acceptance")));TestEqual(Id+TEXT(" timeout"),double(Task->SourceMoveLimitSeconds),R->GetNumberField(TEXT("limit")));TestEqual(Id+TEXT(" target refresh"),double(Task->SourceFollowUpdateDistance),R->GetNumberField(TEXT("follow_update_distance")));}
		if(Kind==TEXT("LockOnMove")){++LockMoves;TestEqual(Id+TEXT(" movement rows"),Task->SourceMoves.Num(),R->GetArrayField(TEXT("move_settings")).Num());}
		for(const auto& Pair:TArray<TPair<EStateTreeTransitionTrigger,FString>>{{EStateTreeTransitionTrigger::OnStateSucceeded,TEXT("success")},{EStateTreeTransitionTrigger::OnStateFailed,TEXT("failure")}})
		{
			bool Matched=false;for(int32 I=0;I<S->TransitionsNum;++I)if(const auto* T=Tree->GetTransitionFromIndex(S->TransitionsBegin+I);T&&T->Trigger==Pair.Key)if(const auto* Destination=Tree->GetStateFromHandle(T->State))Matched|=Destination->Name.ToString()==R->GetStringField(Pair.Value);
			TestTrue(Id+TEXT(" exact ")+Pair.Value+TEXT(" continuation"),Matched);
		}
	}
	TestEqual(TEXT("Original route count"),Routes,11);TestEqual(TEXT("Original gate count"),Branches,49);TestEqual(TEXT("Original skill count"),Skills,46);TestEqual(TEXT("Original MoveTo count"),Moves,10);TestEqual(TEXT("Original LockOnMove count"),LockMoves,5);
	UStateTree* Apes=LoadObject<UStateTree>(nullptr,TEXT("/Game/Monsters/ApesStoneHandElite/AI/ST_Apes_Original.ST_Apes_Original")); TestTrue(TEXT("Apes saved tree ready"),Apes&&Apes->IsReadyToRun());
	AddInfo(TEXT("SOURCE_AUDIT_COMPLETE: compiled original states/gates/skills/continuations"));return true;
}

namespace KZPatternQA
{
class FRun:public IAutomationLatentCommand
{
public:FRun(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),Until(FPlatformTime::Seconds()+420.)
	{
		Fixed=FApp::UseFixedTimeStep();Delta=FApp::GetFixedDeltaTime();FApp::SetUseFixedTimeStep(true);FApp::SetFixedDeltaTime(.025);
		P->HandleInputMoveReleased();P->GetAbilitySystemComponent()->CancelAllAbilities();
		for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It)if(auto* AI=Cast<AKZMonsterAIController>(It->GetController())) { AI->GetStateTreeComponent()->StopLogic(TEXT("Original pattern fixture"));Paused.Add(AI); }
	}
	~FRun()override{Cleanup();}
	bool Update()override
	{
		if(!Player.IsValid()||FPlatformTime::Seconds()>Until){Test->AddError(TEXT("Pattern fixture timeout"));Cleanup();return true;}
		if(Family>=2){Test->AddInfo(FString::Printf(TEXT("PATTERN_CASES_COMPLETE total=%d"),Total));Cleanup();return true;}
		UWorld* W=Player->GetWorld();const float Now=W->GetTimeSeconds();
		if(!Monster.IsValid())
		{
			const FString Name=Family==0?TEXT("ApesStoneHandElite"):TEXT("Yetuga");
			UClass* Class=LoadClass<AKZMonster>(nullptr,*(TEXT("/Game/Bluprints/Monsters/BP_Monster_")+Name+TEXT(".BP_Monster_")+Name+TEXT("_C")));
			FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Monster=W->SpawnActor<AKZMonster>(Class,FVector(-8000,-8000,Family==0?240:265),FRotator::ZeroRotator,Params);
			if(!Test->TestNotNull(TEXT("Original family fixture"),Monster.Get())){Cleanup();return true;}
			AI=Cast<AKZMonsterAIController>(Monster->GetController());Start=Now;Stage=0;SawRoar=false;
			auto* ASC=Monster->GetAbilitySystemComponent();Handles.Reset();
			for(const auto& S:ASC->GetActivatableAbilities())if(Cast<UKZMonsterPatternAbility>(S.Ability))Handles.Add(S.Handle);
			Test->TestEqual(TEXT("All source entries plus explicit Yetuga aliases granted"),Handles.Num(),Family==0?19:27);
			Index=0;
		}
		Player->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),1000);
		Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
		if(!Player->GetAttachParentActor())Player->SetActorLocation(Monster->GetActorLocation()+FVector(300,0,92-Monster->GetActorLocation().Z));
		auto* ASC=Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		if(Stage==0)
		{
			if(const auto* A=Cast<UKZMonsterPatternAbility>(ASC->GetAnimatingAbility()))
			{
				SawRoar|=A->GetCurrentNodeId().ToString().StartsWith(TEXT("Roar"));
				if(SawRoar&&!A->GetCurrentNodeId().ToString().StartsWith(TEXT("Roar")))
				{
					Test->TestTrue(TEXT("Real Sight/alert routes into autonomous original combat"),AI.IsValid()&&AI->GetBattleTarget()==Player.Get());
					Test->AddInfo(FString::Printf(TEXT("SOURCE_AI family=%d tree=%s node=%s"),Family,*AI->GetStateTreeComponent()->GetDebugInfoString(),*A->GetCurrentNodeId().ToString()));
					AI->GetStateTreeComponent()->StopLogic(TEXT("Inspect every granted original entry"));ASC->CancelAllAbilities();Stage=1;return false;
				}
			}
			if(Now-Start>40.f){Test->AddError(FString::Printf(TEXT("Original autonomous combat failed family=%d roar=%d state=%s"),Family,SawRoar,AI.IsValid()?*AI->GetStateTreeComponent()->GetDebugInfoString():TEXT("NoController")));Stage=1;AI->GetStateTreeComponent()->StopLogic(TEXT("Failed AI fixture"));ASC->CancelAllAbilities();}return false;
		}
		if(Stage==1)
		{
			if(Index>=Handles.Num()){Monster->Destroy();Monster.Reset();AI.Reset();++Family;return false;}
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),1000);ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),1000);
			const auto Handle=Handles[Index]; const auto* Spec=ASC->FindAbilitySpecFromHandle(Handle);Pattern=Spec?Cast<UKZMonsterPatternAbility>(Spec->GetPrimaryInstance()):nullptr;
			if(!Test->TestTrue(TEXT("Real granted source entry activates"),Pattern.IsValid()&&ASC->TryActivateAbility(Handle))){++Index;return false;}
			Test->TestEqual(TEXT("Source montage starts at authored entry"),Pattern->GetCurrentNodeId(),Pattern->GetEntryNodeId());
			Test->AddInfo(FString::Printf(TEXT("SOURCE_ENTRY family=%d class=%s node=%s"),Family,*Pattern->GetClass()->GetPathName(),*Pattern->GetCurrentNodeId().ToString()));
			Run=Pattern->GetPatternRun();Start=Now;Seen.Reset();Stage=2;return false;
		}
		if(Stage==2)
		{
			if(Pattern.IsValid()&&Pattern->IsActive())
			{
				const FName Node=Pattern->GetCurrentNodeId();if(!Seen.Contains(Node)){Seen.Add(Node);Test->TestNotNull(TEXT("Every observed step resolves to authored source data"),Pattern->GetComboDefinition()->FindNode(Node));}
				if(Now-Start<12.f)return false;
				// Looped movement/social source entries are intentionally canceled.
				ASC->CancelAbilityHandle(Handles[Index]);Test->TestTrue(TEXT("Canceled execution reports failure to source task"),Pattern->WasPatternRunCancelled(Run));
			}
			Test->TestFalse(TEXT("Pattern returns its GAS movement restriction"),ASC->HasMatchingGameplayTag(KZGameplayTags::Block_Movement_Input));
			Test->TestTrue(TEXT("Pattern releases capture attachment"),Player->GetAttachParentActor()!=Monster.Get());
			Test->AddInfo(FString::Printf(TEXT("SOURCE_END family=%d entry=%d steps=%d elapsed=%g canceled=%d"),Family,Index,Seen.Num(),Now-Start,Pattern.IsValid()&&Pattern->WasPatternRunCancelled(Run)));
			Stage=3;return false;
		}
		Test->TestFalse(TEXT("Pattern root motion cleanup reaches CMC"),Monster->GetCharacterMovement()->HasRootMotionSources());
		++Index;++Total;Stage=1;return false;
	}
private:
	void Cleanup(){if(Cleaned)return;Cleaned=true;if(Monster.IsValid())Monster->Destroy();if(Player.IsValid()){Player->HandleInputMoveReleased();Player->GetAbilitySystemComponent()->CancelAllAbilities();}for(auto C:Paused)if(C.IsValid())C->GetStateTreeComponent()->RestartLogic();FApp::SetUseFixedTimeStep(Fixed);FApp::SetFixedDeltaTime(Delta);}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Monster;TWeakObjectPtr<AKZMonsterAIController> AI;TWeakObjectPtr<UKZMonsterPatternAbility> Pattern;
	TArray<TWeakObjectPtr<AKZMonsterAIController>> Paused;TArray<FGameplayAbilitySpecHandle> Handles;TSet<FName> Seen;double Until,Delta=0;float Start=0;uint32 Run=0;int32 Family=0,Index=0,Stage=0,Total=0;bool Fixed=false,Cleaned=false,SawRoar=false;
};
class FWait:public IAutomationLatentCommand
{
public:FWait(FAutomationTestBase* T):Test(T),Until(FPlatformTime::Seconds()+90.){}
	bool Update()override{for(const auto& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetMesh()->GetAnimInstance()){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}if(FPlatformTime::Seconds()>Until){Test->AddError(TEXT("No pattern PIE"));return true;}return false;}
private:FAutomationTestBase* Test;double Until;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZBeastPatterns,"Khazan.BeastDodge.PatternsPIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZBeastPatterns::RunTest(const FString&){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZPatternQA::FWait>(this));return true;}
#endif
