// Development authoring tool compiled only in the isolated Monster editor.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "UObject/SavePackage.h"
#include "UObject/ObjectRedirector.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Character/KZMonster.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZGameplayTags.h"

namespace EnemyAnimationAuthor
{
const FString Metadata = TEXT("C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/EnemyAnimationOrganization_20261007/");
bool IsWork() { return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_MonsterWork_20261006")); }
TArray<TSharedPtr<FJsonValue>> ReadArray(const TCHAR* Name)
{
	FString Text; FFileHelper::LoadFileToString(Text, *(Metadata + Name));
	TArray<TSharedPtr<FJsonValue>> Rows; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Rows); return Rows;
}
template<typename T> T& Field(UObject* Object, const TCHAR* Name)
{
	return *FindFProperty<FProperty>(Object->GetClass(), Name)->ContainerPtrToValuePtr<T>(Object);
}
bool Save(UObject* Object)
{
	UPackage* Package = Object->GetOutermost(); Package->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	return UPackage::SavePackage(Package, Object, *FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}
template<typename T> T* Asset(const FString& Path)
{
	if (T* Existing = LoadObject<T>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing;
	T* Result = NewObject<T>(CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional);
	FAssetRegistryModule::AssetCreated(Result); return Result;
}
void InputEnd(UAnimMontage* Montage, float Time)
{
	UAnimNotify_PlayMontageNotify* Notify = NewObject<UAnimNotify_PlayMontageNotify>(Montage, NAME_None, RF_Transactional);
	FindFProperty<FNameProperty>(Notify->GetClass(), TEXT("NotifyName"))->SetPropertyValue_InContainer(Notify, TEXT("InputEnd"));
	FAnimNotifyEvent Event; Event.Notify = Notify; Event.NotifyName = TEXT("InputEnd");
	Event.MontageTickType = EMontageNotifyTickType::BranchingPoint; Event.Guid = FGuid::NewGuid();
	Event.Link(Montage, Time); Montage->Notifies.Add(Event);
}
UClass* Author(const TSharedPtr<FJsonObject>& Pattern)
{
	const FString Family = Pattern->GetStringField(TEXT("family")), Id = Pattern->GetStringField(TEXT("id"));
	const FString Base = TEXT("/Game/Monsters/") + Family;
	UAnimMontage* Montage = Asset<UAnimMontage>(Base + TEXT("/Animations/Attack/Montages/Attack_") + Id);
	UKZComboDefinitionData* Definition = Asset<UKZComboDefinitionData>(Base + TEXT("/Data/DA_Combo_") + Id);
	FSlotAnimationTrack Track; Track.SlotName = TEXT("DefaultSlot");
	Montage->CompositeSections.Reset(); Montage->Notifies.Reset();
	auto& Nodes = Field<TArray<FKZComboNode>>(Definition, TEXT("Nodes")); Nodes.Reset();
	const bool Continuous = Pattern->GetBoolField(TEXT("continuous"));
	const auto& Steps = Pattern->GetArrayField(TEXT("steps")); float Position = 0.f;
	FFrameRate Grid(30, 1); // Replaced by the first imported clip's actual frame grid.
	for (int32 Index = 0; Index < Steps.Num(); ++Index)
	{
		const auto Step = Steps[Index]->AsObject(); const FString Destination = Step->GetStringField(TEXT("game_destination"));
		UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *Destination, nullptr, LOAD_NoWarn);
		if (!Clip)
		{
			UAnimSequence* Source = LoadObject<UAnimSequence>(nullptr, *Step->GetStringField(TEXT("playback")));
			if (!Source) return nullptr;
			Clip = DuplicateObject<UAnimSequence>(Source, CreatePackage(*Destination), *FPackageName::GetLongPackageAssetName(Destination));
			Clip->SetFlags(RF_Public | RF_Standalone | RF_Transactional); FAssetRegistryModule::AssetCreated(Clip);
		}
		Clip->bEnableRootMotion = true; Clip->bForceRootLock = true; Clip->RootMotionRootLock = ERootMotionRootLock::AnimFirstFrame;
		if (!Save(Clip)) return nullptr;
		Montage->SetSkeleton(Clip->GetSkeleton());
		if (Index == 0) Grid = Clip->GetDataModel()->GetFrameRate();
		FAnimSegment Segment; Segment.SetAnimReference(Clip); Segment.StartPos = Position;
		Segment.AnimStartTime = 0.f; Segment.AnimEndTime = Clip->GetPlayLength();
		Segment.AnimPlayRate = Step->GetNumberField(TEXT("anim_play_rate")); Segment.LoopingCount = 1;
		Track.AnimTrack.AnimSegments.Add(Segment);
		if (!Continuous || Index == 0)
		{
			const FName NodeName = Continuous ? FName(TEXT("Action")) : FName(*Step->GetStringField(TEXT("step")));
			FCompositeSection Section; Section.SectionName = NodeName; Section.NextSectionName = NAME_None; Section.Link(Montage, Position);
			Montage->CompositeSections.Add(Section);
			FKZComboNode Node; Node.NodeId = NodeName; Node.Montage = Montage; Node.SectionName = NodeName;
			if (!Continuous && Index + 1 < Steps.Num())
			{
				FKZComboCommandEdge Edge; Edge.CommandTag = KZGameplayTags::Command_Player_Attack_X;
				Edge.CommandPhase = EKZComboCommandPhase::InputEnd; Edge.TargetNodeId = *Step->GetStringField(TEXT("target_step")); Node.CommandEdges.Add(Edge);
				// A closed section can stop before a notify exactly on its endpoint is dispatched.
				// Preserve original earlier notifies; fallback transitions use the last sample before that boundary.
				const float LastSample = FMath::Max(0.f, Clip->GetPlayLength() - static_cast<float>(Clip->GetDataModel()->GetFrameRate().AsInterval()));
				const float Switch = FMath::Min(static_cast<float>(Step->GetNumberField(TEXT("transition_seconds"))), LastSample);
				InputEnd(Montage, Position + Switch / Segment.AnimPlayRate);
			}
			Nodes.Add(Node);
		}
		Position += Segment.GetLength();
	}
	Montage->SlotAnimTracks = {Track};
	Montage->BlendIn.SetBlendTime(Pattern->GetNumberField(TEXT("blend_in")));
	Montage->BlendOut.SetBlendTime(Pattern->GetNumberField(TEXT("blend_out"))); // Existing temporary presentation policy.
	Montage->BlendOutTriggerTime = 0.f;
	Montage->GetController().SetFrameRate(Grid, false);
	Montage->GetController().SetNumberOfFrames(Grid.AsFrameTime(Position).RoundToFrame(), false);
	Montage->SortNotifies(); Montage->RefreshCacheData();
	if (!Save(Montage) || !Save(Definition)) return nullptr;
	const FString Path = Base + TEXT("/Abilities/GA_") + Id;
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn);
	if (!BP)
	{
		BP = FKismetEditorUtilities::CreateBlueprint(UKZComboActionAbility::StaticClass(), CreatePackage(*Path),
			*FPackageName::GetLongPackageAssetName(Path), BPTYPE_Normal, UBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass());
		FAssetRegistryModule::AssetCreated(BP);
	}
	UObject* CDO = BP->GeneratedClass->GetDefaultObject();
	FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(CDO, Definition);
	Field<FName>(CDO, TEXT("EntryNodeId")) = Nodes[0].NodeId;
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
	if (BP->Status == BS_Error || !Save(BP)) return nullptr;
	return BP->GeneratedClass;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEnemyAttackExpansionAuthor, "Khazan.Monster.AttackExpansionAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FEnemyAttackExpansionAuthor::RunTest(const FString& Parameters)
{
	using namespace EnemyAnimationAuthor; if (!IsWork()) return false;
	const auto Patterns = ReadArray(TEXT("AttackExpansionPlan.json"));
	TMap<FString, TArray<UClass*>> Created;
	for (const auto& Value : Patterns)
	{
		const auto Pattern = Value->AsObject(); UClass* Class = Author(Pattern);
		if (!TestNotNull(TEXT("Finite attack author succeeded"), Class)) return false;
		Created.FindOrAdd(Pattern->GetStringField(TEXT("family"))).Add(Class);
		AddInfo(TEXT("AttackExpansion ") + Pattern->GetStringField(TEXT("family")) + TEXT("/") + Pattern->GetStringField(TEXT("id")));
	}
	for (const auto& Value : ReadArray(TEXT("AITuningPlan.json")))
	{
		const auto Policy = Value->AsObject(); const FString Family = Policy->GetStringField(TEXT("family"));
		UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *(TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Family));
		UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *(TEXT("/Game/Monsters/") + Family + TEXT("/Data/DA_Character_") + Family));
		if (!BP || !Definition) return false;
		UObject* CDO = BP->GeneratedClass->GetDefaultObject();
		auto& Attacks = Field<TArray<TSubclassOf<UGameplayAbility>>>(CDO, TEXT("AttackAbilities"));
		auto& Grants = Field<TArray<FKZInitialAbilityGrant>>(Definition, TEXT("InitialAbilityGrants"));
		for (UClass* Class : Created.FindOrAdd(Family))
		{
			Attacks.AddUnique(Class);
			if (!Grants.ContainsByPredicate([Class](const FKZInitialAbilityGrant& Grant) { return Grant.AbilityClass == Class; }))
			{ FKZInitialAbilityGrant Grant; Grant.AbilityClass = Class; Grants.Add(Grant); }
		}
		auto& Settings = Field<FKZMonsterAISettings>(CDO, TEXT("AISettings"));
		const auto& Interval = Policy->GetArrayField(TEXT("after_interval"));
		Settings.AttackIntervalSeconds = FVector2D(Interval[0]->AsNumber(), Interval[1]->AsNumber());
		Settings.ContinueComboChance = Policy->GetNumberField(TEXT("after_combo"));
		Settings.ChaseReactionSeconds = Policy->GetNumberField(TEXT("chase_reaction_seconds"));
		FBlueprintEditorUtils::MarkBlueprintAsModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
		if (!TestTrue(TEXT("Monster Blueprint compiled"), BP->Status != BS_Error) || !Save(BP) || !Save(Definition)) return false;
	}
	TestEqual(TEXT("All planned patterns authored"), Patterns.Num(), 22); return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEnemyAnimationRedirectorFixup, "Khazan.Monster.AnimationRedirectorFixup", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FEnemyAnimationRedirectorFixup::RunTest(const FString& Parameters)
{
	if (!EnemyAnimationAuthor::IsWork()) return false;
	TArray<FString> Paths; FFileHelper::LoadFileToStringArray(Paths, *FPaths::Combine(FPaths::ProjectDir(), TEXT("Saved/EnemyAnimationOrganization/OldAssets.txt")));
	TArray<UObjectRedirector*> Redirectors;
	for (const FString& Path : Paths)
		if (auto* Redirector = LoadObject<UObjectRedirector>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_NoRedirects)) Redirectors.Add(Redirector);
	FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get().FixupReferencers(Redirectors, false, ERedirectFixupMode::DeleteFixedUpRedirectors);
	AddInfo(FString::Printf(TEXT("Fixed scoped animation redirectors: %d"), Redirectors.Num())); return !HasAnyErrors();
}
#endif
