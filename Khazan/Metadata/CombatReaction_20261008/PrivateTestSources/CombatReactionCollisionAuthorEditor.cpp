// Isolated Work editor author only. Do not deliver this helper as product Source.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Character/KZMonster.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimMontage.h"
#include "GameplayEffect.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "Editor.h"

namespace KZReactionCollisionAuthor
{
using FObject = TSharedPtr<FJsonObject>;
using FValue = TSharedPtr<FJsonValue>;
const FString WorkRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/");
const FString MainRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan/Khazan/");
const FString PlanRelative = TEXT("Metadata/CombatReaction_20261008/MonsterAttackCollisionPlan.json");
struct FNodeChange
{
	FKZComboNode* Node = nullptr;
	TArray<FKZAttackCollisionWindow> Windows;
	FTransform CollisionToActor = FTransform::Identity;
	FObject Audit;
};
struct FAssetChange
{
	UKZComboDefinitionData* Definition = nullptr;
	bool bMonster = false;
	TArray<FNodeChange> Nodes;
};
template<class T> T* Field(UObject* Owner, FName Name)
{
	FProperty* Property = Owner ? FindFProperty<FProperty>(Owner->GetClass(), Name) : nullptr;
	return Property ? Property->ContainerPtrToValuePtr<T>(Owner) : nullptr;
}
EKZHitReactionType Reaction(const FString& Name)
{
	return Name == TEXT("Launch") ? EKZHitReactionType::Launch : Name == TEXT("Knockback") ? EKZHitReactionType::Knockback : EKZHitReactionType::Short;
}
FVector Vector(const TArray<FValue>& A)
{
	return FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber());
}
FValue Json(const FObject& O) { return MakeShared<FJsonValueObject>(O); }
bool Save(UKZComboDefinitionData* Definition)
{
	UPackage* Package = Definition->GetOutermost(); Package->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	return UPackage::SavePackage(Package, Definition,
		*FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}
FObject WindowAudit(const FKZAttackCollisionWindow& Window)
{
	FObject O = MakeShared<FJsonObject>();
	O->SetNumberField(TEXT("start"), Window.StartTime); O->SetNumberField(TEXT("end"), Window.EndTime);
	O->SetNumberField(TEXT("shape_enum"), static_cast<int32>(Window.Shape)); O->SetStringField(TEXT("extent_cm"), Window.Extent.ToString());
	O->SetStringField(TEXT("hit_group"), Window.HitGroup.ToString()); O->SetNumberField(TEXT("hp_damage"), Window.HPDamage);
	O->SetNumberField(TEXT("stamina_damage"), Window.StaminaDamage); O->SetBoolField(TEXT("blockable"), Window.bBlockable);
	O->SetNumberField(TEXT("reaction_enum"), static_cast<int32>(Window.HitReaction)); O->SetNumberField(TEXT("keys"), Window.Keys.Num());
	O->SetStringField(TEXT("source"), Window.Source);
	if (!Window.Keys.IsEmpty())
	{
		O->SetNumberField(TEXT("first_key_time"), Window.Keys[0].Time); O->SetStringField(TEXT("first_center_cm"), Window.Keys[0].Center.ToString());
		O->SetStringField(TEXT("first_rotation"), Window.Keys[0].Rotation.ToString());
		O->SetNumberField(TEXT("last_key_time"), Window.Keys.Last().Time); O->SetStringField(TEXT("last_center_cm"), Window.Keys.Last().Center.ToString());
	}
	return O;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZReactionCollisionAuthorTest, "Khazan.Combat.ReactionCollisionAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZReactionCollisionAuthorTest::RunTest(const FString& Parameters)
{
	using namespace KZReactionCollisionAuthor;
	FString Project = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()); FPaths::NormalizeDirectoryName(Project);
	FString Expected = WorkRoot; FPaths::NormalizeDirectoryName(Expected);
	if (!Project.Equals(Expected, ESearchCase::IgnoreCase) || (GEditor && GEditor->PlayWorld))
	{
		AddError(TEXT("Requires exact isolated MonsterWork project, without PIE.")); return false;
	}
	FString PlanPath = WorkRoot + PlanRelative;
	if (!FPaths::FileExists(PlanPath)) PlanPath = MainRoot + PlanRelative; // Read-only cached research fallback.
	FString Text; FObject Plan;
	if (!FFileHelper::LoadFileToString(Text, *PlanPath) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Plan) || !Plan.IsValid())
	{
		AddError(TEXT("Cannot read exact collision plan.")); return false;
	}
	TSubclassOf<UGameplayEffect> DamageClass = LoadClass<UGameplayEffect>(nullptr,
		TEXT("/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C"));
	if (!DamageClass) { AddError(TEXT("Missing existing shared damage GE.")); return false; }
	TArray<FAssetChange> Pending;
	// Stage all supported windows before any asset modification. Existing montages/sequences remain read-only.
	for (const FValue& PatternValue : Plan->GetArrayField(TEXT("monster_patterns")))
	{
		const FObject Pattern = PatternValue->AsObject();
		FAssetChange Asset; Asset.bMonster = true;
		Asset.Definition = LoadObject<UKZComboDefinitionData>(nullptr, *Pattern->GetStringField(TEXT("definition")));
		auto* Nodes = Field<TArray<FKZComboNode>>(Asset.Definition, TEXT("Nodes"));
		auto* Damage = Field<TSubclassOf<UGameplayEffect>>(Asset.Definition, TEXT("AttackDamageEffect"));
		const FString Family = Pattern->GetStringField(TEXT("family"));
		const FString BP = TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Family;
		UClass* MonsterClass = LoadClass<AKZMonster>(nullptr, *(BP + TEXT(".") + FPackageName::GetLongPackageAssetName(BP) + TEXT("_C")));
		AKZMonster* Monster = MonsterClass ? MonsterClass->GetDefaultObject<AKZMonster>() : nullptr;
		if (!Nodes || !Damage || !Monster || !Monster->GetMesh() || Nodes->Num() != Pattern->GetArrayField(TEXT("nodes")).Num())
		{
			AddError(TEXT("Missing/mismatched definition or current gameplay body: ") + Pattern->GetStringField(TEXT("definition"))); return false;
		}
		for (const FValue& NodeValue : Pattern->GetArrayField(TEXT("nodes")))
		{
			const FObject PlannedNode = NodeValue->AsObject();
			const FName Id(*PlannedNode->GetStringField(TEXT("node_id")));
			FKZComboNode* Node = Nodes->FindByPredicate([Id](const FKZComboNode& Candidate) { return Candidate.NodeId == Id; });
			if (!Node || !Node->Montage || Node->Montage->GetOutermost()->GetName() != Pattern->GetStringField(TEXT("montage")) ||
				Node->SectionName != FName(*PlannedNode->GetStringField(TEXT("section_name"))))
			{
				AddError(TEXT("Current montage/node differs from cached plan: ") + Id.ToString()); return false;
			}
			const int32 Section = Node->Montage->GetSectionIndex(Node->SectionName);
			float SectionStart = 0.f, SectionEnd = 0.f;
			if (Section != INDEX_NONE) Node->Montage->GetSectionStartAndEndTime(Section, SectionStart, SectionEnd);
			if (Section == INDEX_NONE || !FMath::IsNearlyEqual(SectionStart, static_cast<float>(PlannedNode->GetNumberField(TEXT("section_start_seconds"))), .001f))
			{
				AddError(TEXT("Current section time differs from saved plan: ") + Id.ToString()); return false;
			}
			FNodeChange Change; Change.Node = Node;
			// Provisional original model/ground cm -> current capsule actor frame, matching the existing Player author contract.
			// Bounds prove source shape composition; monster actor-frame calibration remains a separate PIE check.
			Change.CollisionToActor = FTransform(FQuat::Identity, Monster->GetMesh()->GetRelativeLocation(), FVector::OneVector);
			Change.Audit = MakeShared<FJsonObject>(); Change.Audit->SetStringField(TEXT("node_id"), Id.ToString());
			Change.Audit->SetNumberField(TEXT("section_start_actual"), SectionStart);
			Change.Audit->SetNumberField(TEXT("section_end_actual"), SectionEnd);
			Change.Audit->SetArrayField(TEXT("skipped_windows"), PlannedNode->GetArrayField(TEXT("skipped_windows")));
			for (const FValue& WindowValue : PlannedNode->GetArrayField(TEXT("windows")))
			{
				const FObject W = WindowValue->AsObject(); FKZAttackCollisionWindow Window;
				Window.StartTime = W->GetNumberField(TEXT("start_time")); Window.EndTime = W->GetNumberField(TEXT("end_time"));
				const auto& Extent = W->GetArrayField(TEXT("extent"));
				if (Extent.Num() != 3 || Window.StartTime < 0.f || Window.EndTime < Window.StartTime)
				{
					AddError(TEXT("Invalid derived source window.")); return false;
				}
				Window.Shape = EKZAttackCollisionShape::Box; Window.Extent = Vector(Extent);
				Window.HitGroup = FName(*W->GetStringField(TEXT("hit_group")));
				// Explicit root-approved temporary absolute tuning, not original SI/SD damage multipliers.
				Window.HPDamage = W->GetNumberField(TEXT("hp_damage")); Window.StaminaDamage = W->GetNumberField(TEXT("stamina_damage"));
				Window.bBlockable = W->GetBoolField(TEXT("blockable")); Window.HitReaction = Reaction(W->GetStringField(TEXT("reaction")));
				Window.Source = W->GetStringField(TEXT("source"));
				for (const FValue& KeyValue : W->GetArrayField(TEXT("keys")))
				{
					const FObject K = KeyValue->AsObject(); const auto& C = K->GetArrayField(TEXT("center")); const auto& Q = K->GetArrayField(TEXT("quaternion"));
					if (C.Num() != 3 || Q.Num() != 4) { AddError(TEXT("Invalid source geometry key.")); return false; }
					FKZAttackCollisionKey Key; Key.Time = K->GetNumberField(TEXT("time")); Key.Center = Vector(C);
					Key.Rotation = FQuat(Q[0]->AsNumber(), Q[1]->AsNumber(), Q[2]->AsNumber(), Q[3]->AsNumber()).GetNormalized().Rotator();
					Window.Keys.Add(Key);
				}
				if (Window.Keys.IsEmpty()) { AddError(TEXT("Supported box has no keys.")); return false; }
				Change.Windows.Add(MoveTemp(Window));
			}
			Asset.Nodes.Add(MoveTemp(Change));
		}
		Pending.Add(MoveTemp(Asset));
	}
	FAssetChange Player; Player.Definition = LoadObject<UKZComboDefinitionData>(nullptr, *Plan->GetStringField(TEXT("player_definition")));
	auto* PlayerNodes = Field<TArray<FKZComboNode>>(Player.Definition, TEXT("Nodes"));
	if (!PlayerNodes) { AddError(TEXT("Missing current Player definition.")); return false; }
	for (const FValue& NodeValue : Plan->GetArrayField(TEXT("player_reaction_nodes")))
	{
		const FObject P = NodeValue->AsObject(); const FName Id(*P->GetStringField(TEXT("node_id")));
		FKZComboNode* Node = PlayerNodes->FindByPredicate([Id](const FKZComboNode& Candidate) { return Candidate.NodeId == Id; });
		if (!Node || Node->AttackWindows.Num() != P->GetNumberField(TEXT("expected_window_count_saved_author")))
		{
			AddError(TEXT("Player window count differs from source mapping; no mutation: ") + Id.ToString()); return false;
		}
		FNodeChange Change; Change.Node = Node; Change.Windows = Node->AttackWindows; Change.CollisionToActor = Node->CollisionToActor;
		Change.Audit = MakeShared<FJsonObject>(); Change.Audit->SetStringField(TEXT("node_id"), Id.ToString());
		Change.Audit->SetArrayField(TEXT("source_reaction_mapping"), P->GetArrayField(TEXT("windows")));
		for (const FValue& WindowValue : P->GetArrayField(TEXT("windows")))
		{
			const FObject W = WindowValue->AsObject(); const int32 Index = W->GetNumberField(TEXT("window_index"));
			if (!Change.Windows.IsValidIndex(Index)) { AddError(TEXT("Invalid Player window index.")); return false; }
			const auto& Times = W->GetArrayField(TEXT("current_window_seconds_saved_author"));
			const FKZAttackCollisionWindow& Old = Change.Windows[Index];
			if (Times.Num() != 2 || !FMath::IsNearlyEqual(Old.StartTime, static_cast<float>(Times[0]->AsNumber()), .001f) ||
				!FMath::IsNearlyEqual(Old.EndTime, static_cast<float>(Times[1]->AsNumber()), .001f))
			{
				AddError(TEXT("Player current time differs from source mapping; no mutation: ") + Id.ToString()); return false;
			}
			Change.Windows[Index].HitReaction = Reaction(W->GetStringField(TEXT("reaction")));
			if (!Change.Windows[Index].Source.Contains(TEXT("Reaction mapping20261008:")))
				Change.Windows[Index].Source += TEXT("; Reaction mapping20261008: ") + W->GetStringField(TEXT("reason")) + TEXT(" SD relation=") + W->GetStringField(TEXT("SD_relation")) + TEXT("; HP/Stamina/current geometry unchanged.");
		}
		Player.Nodes.Add(MoveTemp(Change));
	}
	Pending.Add(MoveTemp(Player));
	FObject Receipt = MakeShared<FJsonObject>(); Receipt->SetStringField(TEXT("project"), Project); Receipt->SetStringField(TEXT("plan"), PlanPath);
	Receipt->SetNumberField(TEXT("pid"), FPlatformProcess::GetCurrentProcessId()); Receipt->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601());
	Receipt->SetObjectField(TEXT("cached_plan_summary"), Plan->GetObjectField(TEXT("summary")));
	Receipt->SetStringField(TEXT("limits"), TEXT("113 supported box occurrences only;11 unsupported occurrences explicitly skipped. Geometry source composition is bounds-verified; current monster actor-frame alignment remains provisional until observed. No montage/sequence/BP writes. Player only reaction enum/provenance change; amounts/geometry/timing preserved."));
	TArray<FValue> AssetAudits; bool bSuccess = true;
	for (FAssetChange& Asset : Pending)
	{
		FObject A = MakeShared<FJsonObject>(); A->SetStringField(TEXT("definition"), Asset.Definition->GetOutermost()->GetName());
		A->SetBoolField(TEXT("monster"), Asset.bMonster); A->SetBoolField(TEXT("draw_attack_collision_preserved"), Asset.Definition->ShouldDrawAttackCollision());
		TArray<FValue> NodesAudit;
		for (FNodeChange& Change : Asset.Nodes)
		{
			Change.Node->AttackWindows = MoveTemp(Change.Windows); Change.Node->CollisionToActor = Change.CollisionToActor;
			TArray<FValue> WindowsAudit;
			for (const FKZAttackCollisionWindow& Window : Change.Node->AttackWindows) WindowsAudit.Add(Json(WindowAudit(Window)));
			Change.Audit->SetArrayField(TEXT("loaded_windows_after"), WindowsAudit);
			Change.Audit->SetStringField(TEXT("collision_to_actor"), Change.Node->CollisionToActor.ToString()); NodesAudit.Add(Json(Change.Audit));
		}
		if (Asset.bMonster) *Field<TSubclassOf<UGameplayEffect>>(Asset.Definition, TEXT("AttackDamageEffect")) = DamageClass;
		A->SetStringField(TEXT("damage_effect_loaded"), Asset.Definition->GetAttackDamageEffect() ? Asset.Definition->GetAttackDamageEffect()->GetPathName() : TEXT("None"));
		A->SetArrayField(TEXT("nodes"), NodesAudit); const bool bSaved = Save(Asset.Definition);
		A->SetBoolField(TEXT("saved"), bSaved); AssetAudits.Add(Json(A));
		if (!bSaved) { AddError(TEXT("Definition save failed: ") + Asset.Definition->GetOutermost()->GetName()); bSuccess = false; break; }
	}
	Receipt->SetBoolField(TEXT("success"), bSuccess); Receipt->SetArrayField(TEXT("assets"), AssetAudits);
	const FString Output = WorkRoot + TEXT("Saved/MonsterAI/CombatReactionCollisionAuthor.json");
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output), true);
	FString ReceiptText; FJsonSerializer::Serialize(Receipt.ToSharedRef(), TJsonWriterFactory<>::Create(&ReceiptText));
	if (!FFileHelper::SaveStringToFile(ReceiptText, *Output, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
	{
		AddError(TEXT("Receipt save failed.")); bSuccess = false;
	}
	return bSuccess;
}
#endif
