// Isolated editor authoring only. Copy this file into the Work editor module; never product Source.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "Character/KZMonster.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZGameplayTags.h"
#include "GameplayEffect.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "Engine/Blueprint.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "HAL/FileManager.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "Editor.h"

namespace KZMonsterStaminaAuthor
{
using FObject = TSharedPtr<FJsonObject>;
const FString WorkRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/");
TArray<FString> SavedPackages;
TArray<TSharedPtr<FJsonValue>> ClipAudits, MontageAudits, DefinitionAudits, AttackAudits, SkeletonAudits;

// The small public Save/Blueprint patterns are reused from MonsterAuthorEditor.cpp.
bool Save(UObject* Object)
{
	if (!Object) return false;
	UPackage* Package = Object->GetOutermost();
	Package->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	const bool Saved = UPackage::SavePackage(Package, Object,
		*FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
	if (Saved) SavedPackages.AddUnique(Package->GetName());
	return Saved;
}
template<class T> T* Asset(const FString& Path)
{
	if (T* Existing = LoadObject<T>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing;
	T* Result = NewObject<T>(CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path),
		RF_Public | RF_Standalone | RF_Transactional);
	FAssetRegistryModule::AssetCreated(Result);
	return Result;
}
UBlueprint* Blueprint(const FString& Path)
{
	if (UBlueprint* Existing = LoadObject<UBlueprint>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing;
	UBlueprint* Result = FKismetEditorUtilities::CreateBlueprint(UGameplayEffect::StaticClass(), CreatePackage(*Path),
		*FPackageName::GetLongPackageAssetName(Path), BPTYPE_Normal);
	if (Result) FAssetRegistryModule::AssetCreated(Result);
	return Result;
}
template<class T> T* Field(UObject* Owner, FName Name)
{
	FProperty* Property = Owner ? FindFProperty<FProperty>(Owner->GetClass(), Name) : nullptr;
	return Property ? Property->ContainerPtrToValuePtr<T>(Owner) : nullptr;
}
FString ObjectPath(const UObject* Object) { return Object ? Object->GetPathName() : TEXT("None"); }
TSharedPtr<FJsonValue> Json(const FObject& Object) { return MakeShared<FJsonValueObject>(Object); }
TArray<TSharedPtr<FJsonValue>> Paths(const TArray<FString>& Values)
{
	TArray<TSharedPtr<FJsonValue>> Result;
	for (const FString& Value : Values) Result.Add(MakeShared<FJsonValueString>(Value));
	return Result;
}

// Model transforms are uncompressed source data. Hash components explicitly, without FTransform padding.
FString RawBoneHash(UAnimSequence* Clip)
{
	const IAnimationDataModel* Model = Clip ? Clip->GetDataModel() : nullptr;
	if (!Model) return FString();
	FMD5 Hash; TArray<FName> Names; Model->GetBoneTrackNames(Names);
	for (FName Name : Names)
	{
		FTCHARToUTF8 Encoded(*Name.ToString()); Hash.Update(reinterpret_cast<const uint8*>(Encoded.Get()), Encoded.Length());
		TArray<FTransform> Transforms; Model->GetBoneTrackTransforms(Name, Transforms);
		for (const FTransform& Transform : Transforms)
		{
			const FVector P = Transform.GetTranslation(), S = Transform.GetScale3D(); const FQuat Q = Transform.GetRotation();
			const double Components[] = {P.X, P.Y, P.Z, Q.X, Q.Y, Q.Z, Q.W, S.X, S.Y, S.Z};
			Hash.Update(reinterpret_cast<const uint8*>(Components), sizeof(Components));
		}
	}
	uint8 Digest[16]; Hash.Final(Digest); return BytesToHex(Digest, 16).ToLower();
}
FObject ClipOptions(UAnimSequence* Clip)
{
	FObject Row = MakeShared<FJsonObject>(); const IAnimationDataModel* Model = Clip->GetDataModel();
	Row->SetStringField(TEXT("asset"), Clip->GetPathName()); Row->SetStringField(TEXT("raw_bone_transform_md5"), RawBoneHash(Clip));
	Row->SetNumberField(TEXT("seconds"), Clip->GetPlayLength()); Row->SetNumberField(TEXT("rate_scale"), Clip->RateScale);
	Row->SetBoolField(TEXT("enable_root_motion"), Clip->bEnableRootMotion); Row->SetBoolField(TEXT("force_root_lock"), Clip->bForceRootLock);
	Row->SetBoolField(TEXT("normalized_root_motion_scale"), Clip->bUseNormalizedRootMotionScale);
	Row->SetNumberField(TEXT("root_lock_enum"), static_cast<uint8>(Clip->RootMotionRootLock));
	Row->SetStringField(TEXT("skeleton"), ObjectPath(Clip->GetSkeleton()));
	Row->SetStringField(TEXT("root_bone"), Clip->GetSkeleton()->GetReferenceSkeleton().GetBoneName(0).ToString());
	Row->SetNumberField(TEXT("frames"), Model->GetNumberOfFrames()); Row->SetNumberField(TEXT("keys"), Model->GetNumberOfKeys());
	Row->SetNumberField(TEXT("fps_numerator"), Model->GetFrameRate().Numerator); Row->SetNumberField(TEXT("fps_denominator"), Model->GetFrameRate().Denominator);
	Row->SetNumberField(TEXT("bone_tracks"), Model->GetNumBoneTracks()); Row->SetNumberField(TEXT("notify_count"), Clip->Notifies.Num());
	return Row;
}
bool SameClip(const FObject& A, const FObject& B)
{
	for (const TCHAR* Key : {TEXT("raw_bone_transform_md5"), TEXT("skeleton"), TEXT("root_bone")})
		if (A->GetStringField(Key) != B->GetStringField(Key)) return false;
	for (const TCHAR* Key : {TEXT("seconds"), TEXT("rate_scale"), TEXT("root_lock_enum"), TEXT("frames"), TEXT("keys"), TEXT("fps_numerator"), TEXT("fps_denominator"), TEXT("bone_tracks"), TEXT("notify_count")})
		if (A->GetNumberField(Key) != B->GetNumberField(Key)) return false;
	return A->GetBoolField(TEXT("enable_root_motion")) == B->GetBoolField(TEXT("enable_root_motion")) && A->GetBoolField(TEXT("force_root_lock")) == B->GetBoolField(TEXT("force_root_lock")) && A->GetBoolField(TEXT("normalized_root_motion_scale")) == B->GetBoolField(TEXT("normalized_root_motion_scale"));
}
UAnimSequence* CloneClip(const FString& Source, const FString& Destination)
{
	UAnimSequence* Original = LoadObject<UAnimSequence>(nullptr, *Source);
	if (!Original || !Original->GetDataModel() || !Original->GetSkeleton() || Original->GetSkeleton()->GetReferenceSkeleton().GetNum() == 0) return nullptr;
	const FObject Before = ClipOptions(Original);
	UAnimSequence* Copy = LoadObject<UAnimSequence>(nullptr, *Destination, nullptr, LOAD_NoWarn);
	if (!Copy)
	{
		Copy = DuplicateObject<UAnimSequence>(Original, CreatePackage(*Destination), *FPackageName::GetLongPackageAssetName(Destination));
		Copy->SetFlags(RF_Public | RF_Standalone | RF_Transactional); FAssetRegistryModule::AssetCreated(Copy);
	}
	if (!Copy->GetDataModel() || !Copy->GetSkeleton()) return nullptr;
	FObject After = ClipOptions(Copy); const bool Preserved = SameClip(Before, After) && SameClip(Before, ClipOptions(Original));
	FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("source"), Source); Row->SetStringField(TEXT("destination"), Destination);
	Row->SetObjectField(TEXT("source_options"), Before); Row->SetObjectField(TEXT("copy_options"), After); Row->SetBoolField(TEXT("raw_root_rate_preserved"), Preserved);
	ClipAudits.Add(Json(Row));
	if (!Preserved || !Save(Copy)) return nullptr;
	return Copy;
}
void PointNotify(UAnimMontage* Montage, FName Name, float Time)
{
	UAnimNotify_PlayMontageNotify* Notify = NewObject<UAnimNotify_PlayMontageNotify>(Montage, Name, RF_Transactional);
	FindFProperty<FNameProperty>(Notify->GetClass(), TEXT("NotifyName"))->SetPropertyValue_InContainer(Notify, Name);
	FAnimNotifyEvent Event; Event.NotifyName = Name; Event.Notify = Notify; Event.Guid = FGuid::NewGuid();
	Event.MontageTickType = EMontageNotifyTickType::BranchingPoint; Event.Link(Montage, Time); Montage->Notifies.Add(Event);
}
UAnimMontage* Montage(const FString& Path, const TArray<UAnimSequence*>& Clips, const TArray<FName>& Names,
	const TArray<FName>& Links, float BlendIn, float BlendOut, UAnimMontage* PlayerTemplate = nullptr,
	const TArray<TSharedPtr<FJsonValue>>* DamageStages = nullptr, bool bVictimBlendReuse = false)
{
	if (Clips.IsEmpty() || Clips.Num() != Names.Num() || Clips.Num() != Links.Num() || Clips.ContainsByPredicate([](UAnimSequence* Clip) { return !Clip || !Clip->GetDataModel(); })) return nullptr;
	USkeleton* Skeleton = Clips[0]->GetSkeleton();
	// Do not mutate shared original skeletons; their existing DefaultSlot must be reusable.
	if (!Skeleton || !Skeleton->ContainsSlotName(TEXT("DefaultSlot"))) return nullptr;
	UAnimMontage* Result = Asset<UAnimMontage>(Path); Result->SetSkeleton(Skeleton);
	Result->CompositeSections.Reset(); Result->Notifies.Reset(); FSlotAnimationTrack Track; Track.SlotName = TEXT("DefaultSlot");
	float Position = 0.f; TArray<float> Starts;
	for (int32 Index = 0; Index < Clips.Num(); ++Index)
	{
		if (Clips[Index]->GetSkeleton() != Skeleton) return nullptr;
		Starts.Add(Position); FAnimSegment Segment; Segment.SetAnimReference(Clips[Index]); Segment.StartPos = Position;
		Segment.AnimStartTime = 0.f; Segment.AnimEndTime = Clips[Index]->GetPlayLength(); Segment.AnimPlayRate = 1.f; Segment.LoopingCount = 1;
		Track.AnimTrack.AnimSegments.Add(Segment); FCompositeSection Section; Section.SectionName = Names[Index]; Section.NextSectionName = Links[Index];
		Section.Link(Result, Position); Result->CompositeSections.Add(Section); Position += Segment.GetLength();
	}
	Result->SlotAnimTracks = {Track}; Result->RateScale = 1.f;
	if (PlayerTemplate)
	{
		Result->BlendIn = PlayerTemplate->BlendIn; Result->BlendOut = PlayerTemplate->BlendOut;
		Result->BlendModeIn = PlayerTemplate->BlendModeIn; Result->BlendModeOut = PlayerTemplate->BlendModeOut;
		Result->BlendProfileIn = PlayerTemplate->BlendProfileIn; Result->BlendProfileOut = PlayerTemplate->BlendProfileOut;
		Result->BlendOutTriggerTime = PlayerTemplate->BlendOutTriggerTime; Result->bEnableAutoBlendOut = PlayerTemplate->bEnableAutoBlendOut;
	}
	else { Result->BlendIn.SetBlendTime(BlendIn); Result->BlendOut.SetBlendTime(BlendOut); Result->BlendOutTriggerTime = 0.f; Result->bEnableAutoBlendOut = true; }
	const FFrameRate Rate = Clips[0]->GetDataModel()->GetFrameRate();
	Result->GetController().SetFrameRate(Rate, false); Result->GetController().SetNumberOfFrames(Rate.AsFrameTime(Position).RoundToFrame(), false);
	FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("asset"), Path); Row->SetNumberField(TEXT("seconds"), Position);
	Row->SetNumberField(TEXT("blend_in_seconds"), Result->BlendIn.GetBlendTime()); Row->SetNumberField(TEXT("blend_out_seconds"), Result->BlendOut.GetBlendTime());
	Row->SetStringField(TEXT("blend_provenance"), PlayerTemplate ? TEXT("Existing WeakAttack template expression reused; not an original-game verified blend.") : bVictimBlendReuse ? TEXT("Project presentation reuse of the exhaustion AP Start/End blends; paired-victim native blend is unconfirmed.") : TEXT("Original AP Start/EndAnimBlendTime. AP Loop blend recorded in source plan; native section transition is not a separate Montage blend."));
	Row->SetStringField(TEXT("blend_template"), ObjectPath(PlayerTemplate)); TArray<TSharedPtr<FJsonValue>> Sections, Events;
	for (int32 Index = 0; Index < Names.Num(); ++Index)
	{
		FObject Section = MakeShared<FJsonObject>(); Section->SetStringField(TEXT("name"), Names[Index].ToString()); Section->SetStringField(TEXT("next"), Links[Index].ToString());
		Section->SetStringField(TEXT("clip"), Clips[Index]->GetPathName()); Section->SetNumberField(TEXT("start_seconds"), Starts[Index]); Sections.Add(Json(Section));
	}
	if (DamageStages)
	{
		for (int32 Index = 0; Index < DamageStages->Num(); ++Index)
		{
			FObject Stage = (*DamageStages)[Index]->AsObject(); const FString SectionName = Stage->GetStringField(TEXT("player_section"));
			const int32 SectionIndex = Names.IndexOfByKey(FName(*SectionName)); if (SectionIndex == INDEX_NONE) return nullptr;
			const float Time = Starts[SectionIndex] + Stage->GetNumberField(TEXT("derived_local_start_seconds"));
			const FName NotifyName = Index == 0 ? FName(TEXT("BrutalHit1")) : FName(TEXT("BrutalHit2")); PointNotify(Result, NotifyName, Time);
			FObject Event = MakeShared<FJsonObject>(); Event->SetStringField(TEXT("name"), NotifyName.ToString()); Event->SetNumberField(TEXT("time_seconds"), Time);
			Event->SetObjectField(TEXT("source_mapping"), Stage); Events.Add(Json(Event));
		}
	}
	Row->SetArrayField(TEXT("sections"), Sections); Row->SetArrayField(TEXT("notifies"), Events); MontageAudits.Add(Json(Row));
	Result->SortNotifies(); Result->PostEditChange(); Result->RefreshCacheData();
	return Save(Result) ? Result : nullptr;
}
UClass* TagEffect(const FString& Path, const FGameplayTagContainer& Tags)
{
	UBlueprint* BP = Blueprint(Path); if (!BP || !BP->GeneratedClass) return nullptr;
	UGameplayEffect* Effect = BP->GeneratedClass->GetDefaultObject<UGameplayEffect>(); Effect->DurationPolicy = EGameplayEffectDurationType::Infinite;
	Effect->Modifiers.Reset(); FInheritedTagContainer Changes;
	for (const FGameplayTag& Tag : Tags) Changes.AddTag(Tag);
	Effect->FindOrAddComponent<UTargetTagsGameplayEffectComponent>().SetAndApplyTargetTagChanges(Changes);
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP); FKismetEditorUtilities::CompileBlueprint(BP);
	if (!BP->GeneratedClass || BP->Status == BS_Error || !Save(BP)) return nullptr;
	Effect = BP->GeneratedClass->GetDefaultObject<UGameplayEffect>();
	return Effect->DurationPolicy == EGameplayEffectDurationType::Infinite && Effect->GetGrantedTags() == Tags ? BP->GeneratedClass.Get() : nullptr;
}
bool Grant(UKZCharacterDefinitionData* Definition, UClass* Class, FGameplayTag Input)
{
	auto* Grants = Field<TArray<FKZInitialAbilityGrant>>(Definition, TEXT("InitialAbilityGrants")); if (!Grants) return false;
	if (const FKZInitialAbilityGrant* Existing = Grants->FindByPredicate([Class](const FKZInitialAbilityGrant& G) { return G.AbilityClass == Class; })) return Existing->InputTag == Input;
	FKZInitialAbilityGrant Entry; Entry.AbilityClass = Class; Entry.InputTag = Input; Grants->Add(Entry); return true;
}
bool AuditAttacks(const FString& Family)
{
	UBlueprint* MonsterBP = LoadObject<UBlueprint>(nullptr, *(TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Family));
	AKZMonster* Monster = MonsterBP && MonsterBP->GeneratedClass ? MonsterBP->GeneratedClass->GetDefaultObject<AKZMonster>() : nullptr;
	if (!Monster) return false;
	for (TSubclassOf<UGameplayAbility> Class : Monster->GetAttackAbilities())
	{
		UBlueprint* BP = Class ? Cast<UBlueprint>(Class->ClassGeneratedBy) : nullptr; if (!BP || !BP->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/") + Family + TEXT("/Abilities/"))) return false;
		UGameplayAbility* CDO = Class->GetDefaultObject<UGameplayAbility>();
		FObjectPropertyBase* Cost = FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("CostGameplayEffectClass"));
		FObjectPropertyBase* OnEnd = FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("OnEndAbilityGameplayEffect")); if (!Cost || !OnEnd) return false;
		FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("family"), Family); Row->SetStringField(TEXT("ability"), Class->GetPathName());
		Row->SetStringField(TEXT("cost_before"), ObjectPath(Cost->GetObjectPropertyValue_InContainer(CDO))); Row->SetStringField(TEXT("on_end_before"), ObjectPath(OnEnd->GetObjectPropertyValue_InContainer(CDO)));
		const bool Changed = Cost->GetObjectPropertyValue_InContainer(CDO) || OnEnd->GetObjectPropertyValue_InContainer(CDO);
		if (Changed)
		{
			Cost->SetObjectPropertyValue_InContainer(CDO, nullptr); OnEnd->SetObjectPropertyValue_InContainer(CDO, nullptr);
			FBlueprintEditorUtils::MarkBlueprintAsModified(BP); FKismetEditorUtilities::CompileBlueprint(BP); if (BP->Status == BS_Error || !Save(BP)) return false;
		}
		CDO = BP->GeneratedClass->GetDefaultObject<UGameplayAbility>();
		Cost = FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("CostGameplayEffectClass"));
		OnEnd = FindFProperty<FObjectPropertyBase>(CDO->GetClass(), TEXT("OnEndAbilityGameplayEffect"));
		if (!Cost || !OnEnd) return false;
		Row->SetBoolField(TEXT("changed"), Changed);
		Row->SetStringField(TEXT("cost_after"), ObjectPath(Cost->GetObjectPropertyValue_InContainer(CDO))); Row->SetStringField(TEXT("on_end_after"), ObjectPath(OnEnd->GetObjectPropertyValue_InContainer(CDO))); AttackAudits.Add(Json(Row));
		if (Cost->GetObjectPropertyValue_InContainer(CDO) || OnEnd->GetObjectPropertyValue_InContainer(CDO)) return false;
	}
	return true;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterStaminaAuthorTest, "Khazan.Monster.StaminaAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterStaminaAuthorTest::RunTest(const FString& Parameters)
{
	using namespace KZMonsterStaminaAuthor;
	if (!FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()), WorkRoot) || !GEditor || GEditor->PlayWorld)
	{ AddError(TEXT("StaminaAuthor requires the exact isolated MonsterWork editor, with no PIE.")); return false; }
	SavedPackages.Reset(); ClipAudits.Reset(); MontageAudits.Reset(); DefinitionAudits.Reset(); AttackAudits.Reset(); SkeletonAudits.Reset();
	const FString PlanPath = FPaths::ProjectDir() / TEXT("Metadata/MonsterStamina_20261008/AnimationPlan.json"); FString PlanText; FObject Plan;
	if (!FFileHelper::LoadFileToString(PlanText, *PlanPath) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PlanText), Plan) || !Plan.IsValid())
	{ AddError(TEXT("Copy the saved AnimationPlan.json to Work Metadata before authoring.")); return false; }
	if (!TestEqual(TEXT("Six planned families"), Plan->GetArrayField(TEXT("families")).Num(), 6) || !TestEqual(TEXT("Five Player copies"), Plan->GetArrayField(TEXT("player_clips")).Num(), 5)) return false;
	const FString PlayerFolder = TEXT("/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/");
	const FString TemplatePath = TEXT("/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo");
	UAnimMontage* PlayerTemplate = LoadObject<UAnimMontage>(nullptr, *TemplatePath);
	UKZCharacterDefinitionData* PlayerDefinition = LoadObject<UKZCharacterDefinitionData>(nullptr, TEXT("/Game/Data/Character/DA_CharacterDefinition_Player"));
	UClass* DamageEffect = LoadClass<UGameplayEffect>(nullptr, TEXT("/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C"));
	if (!TestNotNull(TEXT("Current Player blend template"), PlayerTemplate) || !TestNotNull(TEXT("Player Definition"), PlayerDefinition) || !TestNotNull(TEXT("Existing generic damage GE"), DamageEffect)) return false;
	// Preflight the narrowly selected sources and Definitions before any package save.
	const TCHAR* HumanFamilies[] = {TEXT("Swordsman"), TEXT("SwordShield"), TEXT("HeavySwordsman"), TEXT("HalberdElite")};
	const int32 HumanCounts[] = {5, 3, 7, 20};
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(HumanFamilies); ++Index)
	{
		const FString Name = HumanFamilies[Index];
		UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *(TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Name));
		AKZMonster* CDO = BP && BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject<AKZMonster>() : nullptr;
		if (!TestNotNull(TEXT("Current human gameplay CDO"), CDO) || !TestEqual(*Name, CDO->GetAttackAbilities().Num(), HumanCounts[Index])) return false;
		TSet<UClass*> UniqueClasses;
		for (TSubclassOf<UGameplayAbility> Class : CDO->GetAttackAbilities())
		{
			UBlueprint* AttackBP = Class ? Cast<UBlueprint>(Class->ClassGeneratedBy) : nullptr;
			if (!TestTrue(TEXT("Only current unique family Attack BPs"), AttackBP && !UniqueClasses.Contains(Class.Get()) && AttackBP->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/") + Name + TEXT("/Abilities/")))) return false;
			UniqueClasses.Add(Class.Get());
		}
	}
	TArray<FString> Sources;
	for (const auto& Value : Plan->GetArrayField(TEXT("player_clips"))) Sources.AddUnique(Value->AsObject()->GetStringField(TEXT("current_path")));
	for (const auto& Value : Plan->GetArrayField(TEXT("families")))
	{
		FObject Family = Value->AsObject(); const FString Name = Family->GetStringField(TEXT("family"));
		if (!TestNotNull(*Name, LoadObject<UKZCharacterDefinitionData>(nullptr, *(TEXT("/Game/Monsters/") + Name + TEXT("/Data/DA_Character_") + Name)))) return false;
		for (const auto& Section : Family->GetObjectField(TEXT("exhaustion"))->GetArrayField(TEXT("sections"))) Sources.AddUnique(Section->AsObject()->GetObjectField(TEXT("clip"))->GetStringField(TEXT("current_path")));
		for (const auto& Direction : Family->GetArrayField(TEXT("brutal_victim"))) for (const auto& Section : Direction->AsObject()->GetArrayField(TEXT("sections"))) Sources.AddUnique(Section->AsObject()->GetObjectField(TEXT("clip"))->GetStringField(TEXT("current_path")));
	}
	TSet<USkeleton*> MissingSlots;
	for (const FString& Source : Sources)
	{
		UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *Source);
		if (!TestTrue(*Source, Clip && Clip->GetDataModel() && Clip->GetSkeleton())) return false;
		if (!Clip->GetSkeleton()->ContainsSlotName(TEXT("DefaultSlot"))) MissingSlots.Add(Clip->GetSkeleton());
	}
	for (USkeleton* Skeleton : MissingSlots)
	{
		// Art-only skeletons have never needed a montage slot. Register only the actual new consumer's slot.
		const FReferenceSkeleton Before = Skeleton->GetReferenceSkeleton();
		FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("asset"), Skeleton->GetPathName());
		Row->SetNumberField(TEXT("groups_before"), Skeleton->GetSlotGroups().Num());
		if (!Skeleton->RegisterSlotNode(TEXT("DefaultSlot")) || !Save(Skeleton)) return false;
		const FReferenceSkeleton& After = Skeleton->GetReferenceSkeleton(); bool Same = Before.GetNum() == After.GetNum();
		for (int32 Bone = 0; Same && Bone < Before.GetNum(); ++Bone)
			Same = Before.GetBoneName(Bone) == After.GetBoneName(Bone) && Before.GetParentIndex(Bone) == After.GetParentIndex(Bone) && Before.GetRefBonePose()[Bone].Equals(After.GetRefBonePose()[Bone], 0);
		Row->SetBoolField(TEXT("reference_bones_and_pose_preserved"), Same);
		Row->SetStringField(TEXT("added_slot"), TEXT("DefaultSlot")); Row->SetNumberField(TEXT("groups_after"), Skeleton->GetSlotGroups().Num());
		SkeletonAudits.Add(Json(Row)); if (!TestTrue(TEXT("Slot registration preserves all reference bones and poses"), Same)) return false;
	}
	FGameplayTagContainer DeadTags; DeadTags.AddTag(KZGameplayTags::State_Dead); DeadTags.AddTag(KZGameplayTags::Block_Movement_Input);
	FGameplayTagContainer PolicyTags; PolicyTags.AddTag(KZGameplayTags::Block_StaminaRegen);
	UClass* DeadEffect = TagEffect(TEXT("/Game/Monsters/Effects/GE_DeadState"), DeadTags);
	UClass* PolicyEffect = TagEffect(TEXT("/Game/Monsters/Effects/GE_MonsterStaminaPolicy"), PolicyTags);
	if (!TestNotNull(TEXT("Dead state Infinite GE"), DeadEffect) || !TestNotNull(TEXT("Monster no-regen Infinite GE"), PolicyEffect)) return false;
	TMap<FString, UAnimSequence*> PlayerCopies;
	for (const auto& Value : Plan->GetArrayField(TEXT("player_clips")))
	{
		FObject Entry = Value->AsObject(); const FString Destination = Entry->GetStringField(TEXT("proposed_duplicate_path"));
		if (!Destination.StartsWith(PlayerFolder)) { AddError(TEXT("Plan Player destination escapes BrutalAttack folder.")); return false; }
		UAnimSequence* Copy = CloneClip(Entry->GetStringField(TEXT("current_path")), Destination); if (!TestNotNull(*Destination, Copy)) return false; PlayerCopies.Add(Destination, Copy);
	}
	UAnimMontage* FrontPlayer = nullptr; UAnimMontage* BackPlayer = nullptr;
	for (const auto& Value : Plan->GetArrayField(TEXT("player_front_back_montages")))
	{
		FObject Direction = Value->AsObject(); TArray<UAnimSequence*> Clips; TArray<FName> Names, Links;
		const auto& Sections = Direction->GetArrayField(TEXT("sections_proposed"));
		for (int32 Index = 0; Index < Sections.Num(); ++Index)
		{
			FObject Section = Sections[Index]->AsObject(); Clips.Add(PlayerCopies.FindRef(Section->GetStringField(TEXT("planned_duplicate_path"))));
			Names.Add(*Section->GetStringField(TEXT("section"))); Links.Add(Index + 1 < Sections.Num() ? FName(*Sections[Index + 1]->AsObject()->GetStringField(TEXT("section"))) : NAME_None);
		}
		UAnimMontage* Result = Montage(PlayerFolder + TEXT("AM_DAS_Brutal") + Direction->GetStringField(TEXT("direction")), Clips, Names, Links, 0.f, 0.f, PlayerTemplate, &Direction->GetArrayField(TEXT("damage_stages")));
		if (!TestNotNull(TEXT("Player paired montage"), Result) || !TestEqual(TEXT("Exactly two native Brutal point notifies"), Result->Notifies.Num(), 2)) return false;
		if (Direction->GetStringField(TEXT("direction")) == TEXT("Front")) FrontPlayer = Result; else BackPlayer = Result;
	}
	if (!TestNotNull(TEXT("Front Player montage"), FrontPlayer) || !TestNotNull(TEXT("Back Player montage"), BackPlayer)) return false;
	for (const auto& Value : Plan->GetArrayField(TEXT("families")))
	{
		FObject Family = Value->AsObject(); const FString Name = Family->GetStringField(TEXT("family")); const FString Base = TEXT("/Game/Monsters/") + Name;
		TArray<UAnimSequence*> ExhaustClips; TArray<float> Blends;
		for (const auto& ValueSection : Family->GetObjectField(TEXT("exhaustion"))->GetArrayField(TEXT("sections")))
		{
			FObject Section = ValueSection->AsObject(); const FString Source = Section->GetObjectField(TEXT("clip"))->GetStringField(TEXT("current_path"));
			UAnimSequence* Copy = CloneClip(Source, Base + TEXT("/Animations/InGame/Damage/") + FPackageName::GetLongPackageAssetName(Source));
			if (!TestNotNull(*Source, Copy)) return false; ExhaustClips.Add(Copy); Blends.Add(Section->GetNumberField(TEXT("source_blend_seconds")));
		}
		UAnimMontage* Exhaust = Montage(Base + TEXT("/Animations/AM_Exhaustion"), ExhaustClips, {TEXT("Start"), TEXT("Loop"), TEXT("End")}, {TEXT("Loop"), TEXT("Loop"), NAME_None}, Blends[0], Blends[2]);
		UAnimMontage* FrontVictim = nullptr; UAnimMontage* BackVictim = nullptr;
		if (!TestNotNull(TEXT("Exhaustion montage"), Exhaust)) return false;
		for (const auto& ValueDirection : Family->GetArrayField(TEXT("brutal_victim")))
		{
			FObject Direction = ValueDirection->AsObject(); TArray<UAnimSequence*> Clips;
			for (const auto& ValueSection : Direction->GetArrayField(TEXT("sections")))
			{
				const FString Source = ValueSection->AsObject()->GetObjectField(TEXT("clip"))->GetStringField(TEXT("current_path"));
				UAnimSequence* Copy = CloneClip(Source, Base + TEXT("/Animations/InGame/Damage/") + FPackageName::GetLongPackageAssetName(Source)); if (!TestNotNull(*Source, Copy)) return false; Clips.Add(Copy);
			}
			// Reuse AP presentation blend for this new victim montage; AP does not encode paired Montage blend.
			UAnimMontage* Result = Montage(Base + TEXT("/Animations/AM_BrutalVictim") + Direction->GetStringField(TEXT("direction")), Clips, {TEXT("Damage1"), TEXT("Damage2")}, {NAME_None, NAME_None}, Blends[0], Blends[2], nullptr, nullptr, true);
			if (!TestNotNull(TEXT("Victim paired montage"), Result)) return false;
			if (Direction->GetStringField(TEXT("direction")) == TEXT("Front")) FrontVictim = Result; else BackVictim = Result;
		}
		UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *(Base + TEXT("/Data/DA_Character_") + Name));
		auto* Settings = Field<FKZMonsterStaminaSettings>(Definition, TEXT("MonsterStamina")); auto* Effects = Field<TArray<TSubclassOf<UGameplayEffect>>>(Definition, TEXT("InitialEffects"));
		if (!Settings || !Effects) { AddError(TEXT("Current Definition stamina/effect fields missing.")); return false; }
		FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("family"), Name); Row->SetObjectField(TEXT("ap_source"), Family->GetObjectField(TEXT("ap_source")));
		Row->SetNumberField(TEXT("initial_effect_count_before"), Effects->Num()); Row->SetNumberField(TEXT("initial_grant_count_before"), Definition->GetInitialAbilityGrants().Num());
		Settings->bEnabled = true; Settings->ParryStaminaDamage = 5.f; // Explicit user decision.
		Settings->ExhaustionSeconds = Name == TEXT("Yetuga") ? 8.f : 5.f; // Original CS exhaustion policy, source research cached separately.
		Settings->BrutalHPDamage = 0.f; // Unassigned user damage; raw original ratios are not HP.
		Settings->BrutalAttackRange = Name == TEXT("Yetuga") ? 400.f : Name == TEXT("ApesStoneHandElite") ? 260.f : 180.f; // Explicit temporary project cm ranges.
		Settings->BrutalAlignmentDistance = 0.f; // Native derives actual capsule radii; no mesh/Root scale compensation.
		Settings->ExhaustionMontage = Exhaust; Settings->BrutalFrontPlayerMontage = FrontPlayer; Settings->BrutalBackPlayerMontage = BackPlayer;
		Settings->BrutalFrontVictimMontage = FrontVictim; Settings->BrutalBackVictimMontage = BackVictim; Settings->DamageEffect = DamageEffect; Settings->DeadStateEffect = DeadEffect;
		Effects->AddUnique(PolicyEffect); if (!Grant(Definition, UKZExhaustionAbility::StaticClass(), FGameplayTag()) || !TestTrue(TEXT("Save family Definition"), Save(Definition))) return false;
		Row->SetNumberField(TEXT("initial_effect_count_after"), Effects->Num()); Row->SetNumberField(TEXT("initial_grant_count_after"), Definition->GetInitialAbilityGrants().Num());
		Row->SetNumberField(TEXT("parry_damage"), Settings->ParryStaminaDamage); Row->SetNumberField(TEXT("exhaustion_seconds"), Settings->ExhaustionSeconds); Row->SetNumberField(TEXT("brutal_hp_damage"), Settings->BrutalHPDamage);
		Row->SetNumberField(TEXT("brutal_range_cm"), Settings->BrutalAttackRange); Row->SetNumberField(TEXT("alignment_distance_cm"), Settings->BrutalAlignmentDistance);
		Row->SetArrayField(TEXT("ap_blend_seconds_start_loop_end"), {MakeShared<FJsonValueNumber>(Blends[0]), MakeShared<FJsonValueNumber>(Blends[1]), MakeShared<FJsonValueNumber>(Blends[2])}); DefinitionAudits.Add(Json(Row));
		if (Name != TEXT("ApesStoneHandElite") && Name != TEXT("Yetuga") && !TestTrue(TEXT("Monster attack cost/regen audit"), AuditAttacks(Name))) return false;
	}
	const int32 PlayerGrantsBefore = PlayerDefinition->GetInitialAbilityGrants().Num();
	if (!TestTrue(TEXT("Append native Brutal input X grant"), Grant(PlayerDefinition, UKZBrutalAttackAbility::StaticClass(), KZGameplayTags::Input_Action_X)) || !TestTrue(TEXT("Save Player Definition"), Save(PlayerDefinition)) || !TestEqual(TEXT("All 35 Monster Attack BPs audited"), AttackAudits.Num(), 35) || !TestEqual(TEXT("47 sequence copies audited"), ClipAudits.Num(), 47) || !TestEqual(TEXT("20 authored montages"), MontageAudits.Num(), 20)) return false;
	FObject Report = MakeShared<FJsonObject>(); Report->SetStringField(TEXT("status"), TEXT("AuthoredInWorkOnly_NoPIE")); Report->SetStringField(TEXT("project"), FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()));
	Report->SetStringField(TEXT("animation_plan"), PlanPath); Report->SetStringField(TEXT("source_plan_schema"), Plan->GetStringField(TEXT("schema")));
	Report->SetStringField(TEXT("numeric_provenance"), TEXT("Parry 5 is user decision; duration 5/8 original CS research; Brutal HP0 unassigned; range180/260/400 cm temporary project tuning; alignment0 derives live capsule radii. Player template and victim AP-blend reuse are project presentation choices."));
	Report->SetStringField(TEXT("exhaustion_link_contract"), TEXT("Start->Loop; Loop->Loop; End->None. Runtime timer explicitly starts End; no finite Loop completion callback is assumed."));
	Report->SetStringField(TEXT("deferred"), TEXT("Apes/Yetuga gameplay BP/ABP/registry, death/recovery clips: not created by this tool."));
	Report->SetArrayField(TEXT("saved_packages"), Paths(SavedPackages)); Report->SetArrayField(TEXT("clip_audits"), ClipAudits); Report->SetArrayField(TEXT("montage_audits"), MontageAudits); Report->SetArrayField(TEXT("definition_audits"), DefinitionAudits); Report->SetArrayField(TEXT("monster_attack_audits"), AttackAudits);
	Report->SetArrayField(TEXT("skeleton_slot_audits"), SkeletonAudits);
	Report->SetNumberField(TEXT("player_grant_count_before"), PlayerGrantsBefore); Report->SetNumberField(TEXT("player_grant_count_after"), PlayerDefinition->GetInitialAbilityGrants().Num());
	FString Output; FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Output));
	const FString OutputPath = FPaths::ProjectSavedDir() / TEXT("MonsterStamina/Authoring.json"); IFileManager::Get().MakeDirectory(*FPaths::GetPath(OutputPath), true);
	return TestTrue(TEXT("Save scoped authoring receipt"), FFileHelper::SaveStringToFile(Output, *OutputPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM));
}
#endif
