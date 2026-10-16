// Work-only second authoring step. Requires the first StaminaAuthor helper in the same editor module.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Abilities/GameplayAbility.h"
#include "Character/KZMonster.h"
#include "Animation/KZAnimInstance.h"
#include "Data/KZAssetData.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZGameplayTags.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/Skeleton.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_Slot.h"
#include "AnimGraphNode_Inertialization.h"
#include "Factories/AnimBlueprintFactory.h"
#include "Components/CapsuleComponent.h"
#include "Components/MeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphSchema.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UObject/UnrealType.h"
#include "Editor.h"

// Reuse the first helper's selected clone/raw/Root/rate audit and public package-save implementation.
namespace KZMonsterStaminaAuthor
{
bool Save(UObject* Object);
UAnimSequence* CloneClip(const FString& Source, const FString& Destination);
extern TArray<TSharedPtr<FJsonValue>> ClipAudits;
}

namespace KZMonsterStaminaBodiesAuthor
{
using FObject = TSharedPtr<FJsonObject>;
const FString WorkRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/");
TArray<FString> SavedPackages;
bool Save(UObject* Object)
{
	if (!KZMonsterStaminaAuthor::Save(Object)) return false;
	SavedPackages.AddUnique(Object->GetOutermost()->GetName()); return true;
}
template<class T> T* Field(UObject* Owner, FName Name)
{
	FProperty* Property = Owner ? FindFProperty<FProperty>(Owner->GetClass(), Name) : nullptr;
	return Property ? Property->ContainerPtrToValuePtr<T>(Owner) : nullptr;
}
template<class T> T* Node(UEdGraph* Graph, int32 X)
{
	T* Result = NewObject<T>(Graph, NAME_None, RF_Transactional); Result->CreateNewGuid(); Result->NodePosX = X;
	Graph->AddNode(Result, false, false); Result->PostPlacedNewNode(); return Result;
}
UAnimBlueprint* AnimationBP(const FString& Family, USkeletalMesh* Body, UAnimSequence* Idle)
{
	const FString Path = TEXT("/Game/Monsters/") + Family + TEXT("/Animations/ABP_") + Family;
	UAnimBlueprint* BP = LoadObject<UAnimBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn);
	if (!BP)
	{
		UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>(); Factory->ParentClass = UKZAnimInstance::StaticClass();
		Factory->TargetSkeleton = Idle->GetSkeleton(); Factory->PreviewSkeletalMesh = Body;
		BP = Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), CreatePackage(*Path),
			*FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
		if (BP) FAssetRegistryModule::AssetCreated(BP);
	}
	if (!BP || BP->ParentClass != UKZAnimInstance::StaticClass() || BP->TargetSkeleton != Idle->GetSkeleton()) return nullptr;
	TArray<UEdGraph*> Graphs; BP->GetAllGraphs(Graphs); UEdGraph* Graph = nullptr;
	for (UEdGraph* Candidate : Graphs) if (Candidate->GetFName() == TEXT("AnimGraph")) Graph = Candidate;
	if (!Graph) return nullptr; UAnimGraphNode_Root* Root = nullptr;
	for (UEdGraphNode* Existing : TArray<TObjectPtr<UEdGraphNode>>(Graph->Nodes))
	{
		if (auto* Candidate = Cast<UAnimGraphNode_Root>(Existing)) { Root = Candidate; Root->BreakAllNodeLinks(); }
		else Graph->RemoveNode(Existing);
	}
	if (!Root) return nullptr;
	auto* Player = Node<UAnimGraphNode_SequencePlayer>(Graph, -600); Player->SetAnimationAsset(Idle);
	Player->Node.SetLoopAnimation(true);
	// Set the editable authoring field; runtime SetPlayRate requires allocated anim-node instance data.
	FindFProperty<FFloatProperty>(FAnimNode_SequencePlayer::StaticStruct(), TEXT("PlayRate"))->SetPropertyValue_InContainer(&Player->Node, 1.f);
	Player->AllocateDefaultPins();
	auto* Slot = Node<UAnimGraphNode_Slot>(Graph, -350); Slot->Node.SlotName = TEXT("DefaultSlot"); Slot->Node.bAlwaysUpdateSourcePose = true; Slot->AllocateDefaultPins();
	auto* Inertia = Node<UAnimGraphNode_Inertialization>(Graph, -100); Inertia->AllocateDefaultPins();
	const UEdGraphSchema* Schema = Graph->GetSchema();
	auto Connect = [Schema](UEdGraphNode* A, FName Out, UEdGraphNode* B, FName In)
	{
		UEdGraphPin* From = A->FindPin(Out); UEdGraphPin* To = B->FindPin(In);
		return From && To && Schema->TryCreateConnection(From, To);
	};
	if (!Connect(Player, TEXT("Pose"), Slot, TEXT("Source")) || !Connect(Slot, TEXT("Pose"), Inertia, TEXT("Source")) || !Connect(Inertia, TEXT("Pose"), Root, TEXT("Result"))) return nullptr;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
	if (!BP->GeneratedClass || BP->Status == BS_Error) return nullptr;
	BP->GeneratedClass->GetDefaultObject<UKZAnimInstance>()->SetRootMotionMode(ERootMotionMode::RootMotionFromMontagesOnly);
	return Save(BP) ? BP : nullptr;
}
UBlueprint* ActorBP(const FString& Path)
{
	if (UBlueprint* Existing = LoadObject<UBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing->ParentClass == AKZMonster::StaticClass() ? Existing : nullptr;
	UBlueprint* BP = FKismetEditorUtilities::CreateBlueprint(AKZMonster::StaticClass(), CreatePackage(*Path),
		*FPackageName::GetLongPackageAssetName(Path), BPTYPE_Normal);
	if (BP) FAssetRegistryModule::AssetCreated(BP); return BP;
}
TArray<TSharedPtr<FJsonValue>> RegistryRows(const TMap<FName, FAssetSet>& Groups)
{
	TArray<TSharedPtr<FJsonValue>> Rows;
	for (const auto& Pair : Groups) for (const FAssetEntry& Entry : Pair.Value.AssetEntries)
	{
		FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("group"), Pair.Key.ToString());
		Row->SetStringField(TEXT("tag"), Entry.AssetName.ToString()); Row->SetStringField(TEXT("asset"), Entry.AssetPath.ToString());
		TArray<TSharedPtr<FJsonValue>> Labels; for (FGameplayTag Label : Entry.AssetLabels) Labels.Add(MakeShared<FJsonValueString>(Label.ToString()));
		Row->SetArrayField(TEXT("labels"), Labels); Rows.Add(MakeShared<FJsonValueObject>(Row));
	}
	return Rows;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterStaminaBodiesAuthorTest, "Khazan.Monster.StaminaBodiesAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterStaminaBodiesAuthorTest::RunTest(const FString& Parameters)
{
	using namespace KZMonsterStaminaBodiesAuthor;
	if (!FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()), WorkRoot) || !GEditor || GEditor->PlayWorld)
	{ AddError(TEXT("BodiesAuthor requires the exact isolated Work editor, without PIE.")); return false; }
	SavedPackages.Reset(); const int32 CloneAuditStart = KZMonsterStaminaAuthor::ClipAudits.Num();
	const FString AuditPath = FPaths::ProjectDir() / TEXT("Metadata/MonsterStamina_20261008/BodyAudit.json"); FString AuditText; FObject Audit;
	if (!FFileHelper::LoadFileToString(AuditText, *AuditPath) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(AuditText), Audit) || !Audit.IsValid() || !Audit->GetBoolField(TEXT("success")))
	{ AddError(TEXT("Successful saved Work BodyAudit.json is required.")); return false; }
	UKZAssetData* Registry = LoadObject<UKZAssetData>(nullptr, TEXT("/Game/Data/PDA_AssetData"));
	auto* Groups = Field<TMap<FName, FAssetSet>>(Registry, TEXT("AssetGroupNameToSet"));
	if (!TestNotNull(TEXT("Current PDA registry groups"), Groups)) return false;
	const auto RegistryBefore = RegistryRows(*Groups); TArray<TSharedPtr<FJsonValue>> Rows;
	const TCHAR* Families[] = {TEXT("ApesStoneHandElite"), TEXT("Yetuga")};
	const TCHAR* IdleSources[] = {
		TEXT("/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Locomotion/Locomotion_Stand_F_Original_Variant02"),
		TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Locomotion/Locomotion_Stand_F")};
	// Direct original CB CollisionCylinder overrides, not mesh arm/head bounds-derived capsule guesses.
	const float CapsuleRadius[] = {99.f, 150.f}; const float CapsuleHalfHeight[] = {240.f, 265.f};
	const FVector SourceMeshLocations[] = {FVector(-50, 0, -240), FVector(0, 0.000031, -265)};
	const FRotator SourceMeshRotations[] = {FRotator(0, -90, 0), FRotator(0, -90, 0)};
	const TCHAR* OriginalCB[] = {
		TEXT("BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/Base_Setting/CB_ApesStoneHand_E"),
		TEXT("BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Base_Setting/CB_Yetuga")};
	// Validate both visual assemblies and initialized Definitions before creating packages.
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(Families); ++Index)
	{
		const FString Name = Families[Index]; const FString Base = TEXT("/Game/Monsters/") + Name;
		UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *(Base + TEXT("/Data/DA_Character_") + Name));
		if (!TestTrue(TEXT("First author step must initialize both family stamina settings"), Definition && Definition->GetMonsterStaminaSettings().bEnabled)) return false;
		const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(*FString(TEXT("AssetData.CharacterDefinition.") + Name), false);
		if (!TestTrue(TEXT("Native family Definition tag is registered"), Tag.IsValid())) return false;
	}
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(Families); ++Index)
	{
		const FString Name = Families[Index]; const FString Base = TEXT("/Game/Monsters/") + Name;
		FObject Evidence;
		for (const auto& Value : Audit->GetArrayField(TEXT("rows"))) if (Value->AsObject()->GetStringField(TEXT("family")) == Name) Evidence = Value->AsObject();
		if (!TestTrue(TEXT("Exactly selected family Body evidence"), Evidence.IsValid() && Evidence->GetArrayField(TEXT("components")).Num() == 1)) return false;
		UBlueprint* Art = LoadObject<UBlueprint>(nullptr, *Evidence->GetStringField(TEXT("visual_bp")));
		if (!TestTrue(TEXT("Original Art SCS available"), Art && Art->SimpleConstructionScript)) return false;
		USkeletalMeshComponent* Body = nullptr;
		for (USCS_Node* Candidate : Art->SimpleConstructionScript->GetAllNodes()) if (Candidate->GetVariableName() == TEXT("EnemyBody")) Body = Cast<USkeletalMeshComponent>(Candidate->ComponentTemplate);
		if (!TestTrue(TEXT("Current Art Body matches saved audit"), Body && Body->GetSkeletalMeshAsset() && Body->GetSkeletalMeshAsset()->GetPathName() == Evidence->GetArrayField(TEXT("components"))[0]->AsObject()->GetStringField(TEXT("mesh")))) return false;
		USkeletalMesh* MeshAsset = Body->GetSkeletalMeshAsset(); const FTransform OriginalBodyTransform = Body->GetRelativeTransform();
		const FString IdleDestination = Base + TEXT("/Animations/InGame/Idle/") + FPackageName::GetLongPackageAssetName(IdleSources[Index]);
		UAnimSequence* Idle = KZMonsterStaminaAuthor::CloneClip(IdleSources[Index], IdleDestination);
		if (!TestTrue(TEXT("Preserved own-skeleton InGame idle copy"), Idle && Idle->GetSkeleton() == MeshAsset->GetSkeleton() && Idle->GetSkeleton()->ContainsSlotName(TEXT("DefaultSlot")))) return false;
		SavedPackages.AddUnique(IdleDestination);
		UAnimBlueprint* ABP = AnimationBP(Name, MeshAsset, Idle); if (!TestNotNull(TEXT("Minimal native idle/slot/inertia ABP"), ABP)) return false;
		const FString GameplayPath = TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Name;
		UBlueprint* BP = ActorBP(GameplayPath); AKZMonster* CDO = BP && BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject<AKZMonster>() : nullptr;
		if (!TestNotNull(TEXT("Independent AKZMonster gameplay BP"), CDO)) return false;
		FGameplayTag* DefinitionTagField = Field<FGameplayTag>(CDO, TEXT("CharacterDefinitionAssetName")); if (!DefinitionTagField) return false;
		const FGameplayTag DefinitionTag = FGameplayTag::RequestGameplayTag(*FString(TEXT("AssetData.CharacterDefinition.") + Name)); *DefinitionTagField = DefinitionTag;
		// No AI/attack-pattern expansion. Base native perception/controller remains; the StateTree reference is None.
		if (!TestTrue(TEXT("No existing pattern/StateTree overwritten"), !CDO->GetAIStateTree() && !CDO->GetAlertAbility() && CDO->GetAttackAbilities().IsEmpty())) return false;
		CDO->GetCapsuleComponent()->SetCapsuleSize(CapsuleRadius[Index], CapsuleHalfHeight[Index]);
		USkeletalMeshComponent* Mesh = CDO->GetMesh(); Mesh->SetSkeletalMeshAsset(MeshAsset);
		Mesh->SetRelativeLocation(SourceMeshLocations[Index]); Mesh->SetRelativeRotation(SourceMeshRotations[Index]);
		Mesh->SetRelativeScale3D(Body->GetRelativeScale3D()); // Current visual scale1, not Apes original CharacterScale.8/BoneMod reconstruction.
		Mesh->SetAnimInstanceClass(ABP->GeneratedClass); Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		for (int32 Material = 0; Material < Body->GetNumMaterials(); ++Material) Mesh->SetMaterial(Material, Body->GetMaterial(Material));
		int32 Parts = 0;
		for (USCS_Node* Old : Art->SimpleConstructionScript->GetAllNodes())
		{
			if (Old->GetVariableName() == TEXT("EnemyBody") || !Cast<UMeshComponent>(Old->ComponentTemplate)) continue;
			USCS_Node* Part = BP->SimpleConstructionScript->FindSCSNode(Old->GetVariableName());
			if (!Part) { Part = BP->SimpleConstructionScript->CreateNode(Old->ComponentClass, Old->GetVariableName()); BP->SimpleConstructionScript->AddNode(Part); }
			UEngine::CopyPropertiesForUnrelatedObjects(Old->ComponentTemplate, Part->ComponentTemplate);
			Part->AttachToName = Old->AttachToName; Part->SetParent(Mesh);
			if (auto* SkeletalPart = Cast<USkeletalMeshComponent>(Part->ComponentTemplate); SkeletalPart && SkeletalPart->GetSkeletalMeshAsset() && SkeletalPart->GetSkeletalMeshAsset()->GetSkeleton() == MeshAsset->GetSkeleton()) SkeletalPart->ComponentTags.AddUnique(TEXT("MonsterBodyPart"));
			++Parts;
		}
		// The existing lock-on point uses capsule-local source mesh bounds origin; no new target component.
		const FBoxSphereBounds Bounds = MeshAsset->GetBounds();
		const FVector BoundsAnchor = Mesh->GetRelativeTransform().TransformPosition(Bounds.Origin);
		const_cast<USceneComponent*>(CDO->GetLockOnTargetPoint())->SetRelativeLocation(BoundsAnchor);
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
		if (!TestTrue(TEXT("Gameplay BP compiled"), BP->GeneratedClass && BP->Status != BS_Error) || !TestTrue(TEXT("Save selected gameplay BP"), Save(BP))) return false;
		CDO = BP->GeneratedClass->GetDefaultObject<AKZMonster>();
		if (!TestTrue(TEXT("Saved CDO capsule/tag/root presentation configured"), CDO->GetCapsuleComponent()->GetUnscaledCapsuleRadius() == CapsuleRadius[Index] && CDO->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() == CapsuleHalfHeight[Index] && *Field<FGameplayTag>(CDO, TEXT("CharacterDefinitionAssetName")) == DefinitionTag && CDO->GetMesh()->GetSkeletalMeshAsset() == MeshAsset && CDO->GetMesh()->GetRelativeScale3D() == Body->GetRelativeScale3D() && CDO->GetMesh()->GetAnimClass() == ABP->GeneratedClass)) return false;
		FAssetSet& Set = Groups->FindOrAdd(TEXT("MonsterDefinitions"));
		FAssetEntry* Existing = Set.AssetEntries.FindByPredicate([DefinitionTag](const FAssetEntry& Entry) { return Entry.AssetName == DefinitionTag; });
		const FString DefinitionPath = Base + TEXT("/Data/DA_Character_") + Name;
		UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *DefinitionPath);
		if (Existing)
		{ if (!TestTrue(TEXT("Preserve existing same-tag registry entry"), Existing->AssetPath == FSoftObjectPath(Definition))) return false; }
		else { FAssetEntry Entry; Entry.AssetName = DefinitionTag; Entry.AssetPath = FSoftObjectPath(Definition); Entry.AssetLabels = {KZGameplayTags::AssetLabel_Preload}; Set.AssetEntries.Add(Entry); }
		FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("family"), Name); Row->SetObjectField(TEXT("body_audit_evidence"), Evidence);
		Row->SetStringField(TEXT("gameplay_bp"), GameplayPath); Row->SetStringField(TEXT("animation_bp"), ABP->GetPathName()); Row->SetStringField(TEXT("idle_copy"), IdleDestination);
		Row->SetStringField(TEXT("definition"), DefinitionPath); Row->SetStringField(TEXT("definition_tag"), DefinitionTag.ToString());
		Row->SetNumberField(TEXT("capsule_radius_cm"), CapsuleRadius[Index]); Row->SetNumberField(TEXT("capsule_half_height_cm"), CapsuleHalfHeight[Index]);
		Row->SetStringField(TEXT("original_cb_package"), OriginalCB[Index]); Row->SetStringField(TEXT("original_zip_entry"), FString(OriginalCB[Index]) + TEXT(".json"));
		Row->SetStringField(TEXT("capsule_source_fields"), TEXT("CollisionCylinder.Properties.CapsuleRadius / CapsuleHalfHeight; CharacterMesh0.Properties.RelativeLocation / RelativeRotation"));
		Row->SetNumberField(TEXT("capsule_export_index_zero_based"), 2); Row->SetNumberField(TEXT("mesh_export_index_zero_based"), Index == 0 ? 63 : 57);
		Row->SetStringField(TEXT("original_source_file"), Index == 0 ? TEXT("Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip") : TEXT("Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/CB_Yetuga.json"));
		Row->SetStringField(TEXT("original_source_sha256"), Index == 0 ? TEXT("c45c7fdf5fb0c6f3896bf6811b49f1348086a391e4c0984d50110673c00906f4") : TEXT("96fa15bd72e8d9a00ac760194271c5e46283a74916d54909e5fa125bba97c71a"));
		if (Index == 0) Row->SetStringField(TEXT("matching_early_package"), TEXT("BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/Base_Setting/CB_ApesStoneHand_E_Early; same capsule and CharacterMesh0 overrides; Default__CB Scale=.8 export1 in both."));
		Row->SetStringField(TEXT("units_and_scale_condition"), TEXT("Direct unscaled component parameters in cm/degree. Current gameplay actor scale1 and visual Body scale1 reuse are project adaptations; source CharacterScale/BoneMod runtime effects are not claimed reconstructed."));
		Row->SetStringField(TEXT("mesh_relative_location"), CDO->GetMesh()->GetRelativeLocation().ToString()); Row->SetStringField(TEXT("mesh_relative_rotation"), CDO->GetMesh()->GetRelativeRotation().ToString()); Row->SetStringField(TEXT("mesh_relative_scale"), CDO->GetMesh()->GetRelativeScale3D().ToString());
		Row->SetStringField(TEXT("gameplay_actor_scale"), CDO->GetActorScale3D().ToString());
		Row->SetStringField(TEXT("scale_provenance"), Index == 0 ? TEXT("Original Apes Standard/Early Default__CB Scale=.8. Current visual Body scale1 reused separately; CharacterScale/BoneMod not reconstructed.") : TEXT("Current visual Body scale1 reused; Yetuga .8 is not confirmed in this selected source export."));
		Row->SetStringField(TEXT("lock_on_anchor_policy"), TEXT("Current imported mesh bounds origin transformed by the authored capsule-local mesh transform; derived presentation anchor, not original target metadata."));
		Row->SetStringField(TEXT("lock_on_anchor_capsule_local"), BoundsAnchor.ToString()); Row->SetNumberField(TEXT("copied_visual_parts"), Parts);
		Row->SetStringField(TEXT("anim_graph"), TEXT("Native UKZAnimInstance: looping Idle(rate1)->DefaultSlot->Inertialization->Output; RootMotionFromMontagesOnly."));
		Row->SetBoolField(TEXT("art_body_transform_unchanged"), Body->GetRelativeTransform().Equals(OriginalBodyTransform, 0)); Rows.Add(MakeShared<FJsonValueObject>(Row));
	}
	if (!TestTrue(TEXT("Save PDA append-only registry"), Save(Registry)) || !TestEqual(TEXT("Exactly two bodies"), Rows.Num(), 2)) return false;
	FObject Report = MakeShared<FJsonObject>(); Report->SetStringField(TEXT("status"), TEXT("AuthoredInWorkOnly_NoPIE")); Report->SetStringField(TEXT("body_audit"), AuditPath);
	Report->SetStringField(TEXT("scope"), TEXT("2 independent gameplay BPs,2 native ABPs,2 preserved InGame idle copies,PDA2 entries append. No map,AI patterns,Art BP,original Skeleton,Definition or runtime Source writes."));
	Report->SetArrayField(TEXT("registry_before"), RegistryBefore); Report->SetArrayField(TEXT("registry_after"), RegistryRows(*Groups)); Report->SetArrayField(TEXT("families"), Rows);
	Report->SetStringField(TEXT("registry_comparison_contract"), TEXT("Compare group/tag/path/label sets, not array order: existing PDA PreSave sorts group keys and rebuilds its existing lookup maps."));
	TArray<TSharedPtr<FJsonValue>> Clones; for (int32 Index = CloneAuditStart; Index < KZMonsterStaminaAuthor::ClipAudits.Num(); ++Index) Clones.Add(KZMonsterStaminaAuthor::ClipAudits[Index]); Report->SetArrayField(TEXT("idle_copy_audits"), Clones);
	TArray<TSharedPtr<FJsonValue>> Packages; for (const FString& Path : SavedPackages) Packages.Add(MakeShared<FJsonValueString>(Path)); Report->SetArrayField(TEXT("saved_packages"), Packages);
	FString Text; FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
	const FString OutputPath = FPaths::ProjectSavedDir() / TEXT("MonsterStamina/BodiesAuthoring.json"); IFileManager::Get().MakeDirectory(*FPaths::GetPath(OutputPath), true);
	return TestTrue(TEXT("Save selected body authoring receipt"), FFileHelper::SaveStringToFile(Text, *OutputPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM));
}
#endif
