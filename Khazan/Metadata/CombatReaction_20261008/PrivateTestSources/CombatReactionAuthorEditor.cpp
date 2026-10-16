// Temporary isolated editor author. Never copy this helper to Main/product Source.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/KZHitReactionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "Misc/ScopeExit.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "Editor.h"

namespace KZCombatReactionAuthor
{
using FObject = TSharedPtr<FJsonObject>;
const FString WorkRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/");
TArray<FString> SavedPackages;
TArray<TSharedPtr<FJsonValue>> SourceAudits, CopyAudits, MontageAudits, DefinitionAudits, GuardAudits;
TMap<FString, UAnimSequence*> Clips;
TMap<FString, FObject> SourceOptions;

TSharedPtr<FJsonValue> Json(const FObject& Object) { return MakeShared<FJsonValueObject>(Object); }
TArray<TSharedPtr<FJsonValue>> Strings(const TArray<FString>& Values)
{
	TArray<TSharedPtr<FJsonValue>> Result;
	for (const FString& Value : Values) Result.Add(MakeShared<FJsonValueString>(Value));
	return Result;
}
template<class T> T* Field(UObject* Owner, FName Name)
{
	FProperty* Property = Owner ? FindFProperty<FProperty>(Owner->GetClass(), Name) : nullptr;
	return Property ? Property->ContainerPtrToValuePtr<T>(Owner) : nullptr;
}
bool Save(UObject* Object)
{
	if (!Object) return false;
	UPackage* Package = Object->GetOutermost(); Package->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	const bool bSaved = UPackage::SavePackage(Package, Object,
		*FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
	if (bSaved) SavedPackages.AddUnique(Package->GetName());
	return bSaved;
}
template<class T> T* Asset(const FString& Path)
{
	if (T* Existing = LoadObject<T>(nullptr, *Path, nullptr, LOAD_NoWarn)) return Existing;
	T* Created = NewObject<T>(CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional);
	FAssetRegistryModule::AssetCreated(Created); return Created;
}

// Reused from MonsterStaminaAuthorEditor: explicit components, never padded FTransform bytes.
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
			const double Values[] = {P.X, P.Y, P.Z, Q.X, Q.Y, Q.Z, Q.W, S.X, S.Y, S.Z};
			Hash.Update(reinterpret_cast<const uint8*>(Values), sizeof(Values));
		}
	}
	uint8 Digest[16]; Hash.Final(Digest); return BytesToHex(Digest, 16).ToLower();
}
FObject ClipOptions(UAnimSequence* Clip)
{
	FObject Row = MakeShared<FJsonObject>(); const IAnimationDataModel* Model = Clip->GetDataModel();
	Row->SetStringField(TEXT("asset"), Clip->GetPathName()); Row->SetStringField(TEXT("raw_bone_transform_md5"), RawBoneHash(Clip));
	Row->SetStringField(TEXT("skeleton"), Clip->GetSkeleton()->GetPathName());
	const FReferenceSkeleton& Skeleton = Clip->GetSkeleton()->GetReferenceSkeleton();
	Row->SetStringField(TEXT("root_bone"), Skeleton.GetBoneName(0).ToString());
	Row->SetStringField(TEXT("root_reference_scale"), Skeleton.GetRefBonePose()[0].GetScale3D().ToString());
	TArray<FName> Tracks; Model->GetBoneTrackNames(Tracks);
	Row->SetStringField(TEXT("first_bone_track"), Tracks.IsEmpty() ? TEXT("None") : Tracks[0].ToString());
	Row->SetNumberField(TEXT("seconds"), Clip->GetPlayLength()); Row->SetNumberField(TEXT("rate_scale"), Clip->RateScale);
	Row->SetNumberField(TEXT("effective_segment_rate_at_anim_play_rate_one"), Clip->RateScale);
	Row->SetNumberField(TEXT("frames"), Model->GetNumberOfFrames()); Row->SetNumberField(TEXT("keys"), Model->GetNumberOfKeys());
	Row->SetNumberField(TEXT("fps_numerator"), Model->GetFrameRate().Numerator); Row->SetNumberField(TEXT("fps_denominator"), Model->GetFrameRate().Denominator);
	Row->SetNumberField(TEXT("bone_tracks"), Model->GetNumBoneTracks()); Row->SetNumberField(TEXT("notify_count"), Clip->Notifies.Num());
	Row->SetBoolField(TEXT("enable_root_motion"), Clip->bEnableRootMotion); Row->SetBoolField(TEXT("force_root_lock"), Clip->bForceRootLock);
	Row->SetBoolField(TEXT("normalized_root_motion_scale"), Clip->bUseNormalizedRootMotionScale);
	Row->SetNumberField(TEXT("root_lock_enum"), static_cast<uint8>(Clip->RootMotionRootLock));
	FObject Root = MakeShared<FJsonObject>(); TArray<TSharedPtr<FJsonValue>> Samples;
	double MinZ = 0.0, MaxZ = 0.0; FVector Net = FVector::ZeroVector;
	const int32 Frames = Model->GetNumberOfFrames();
	for (int32 Key = 0; Key <= Frames; ++Key)
	{
		const double Time = Frames > 0 ? Clip->GetPlayLength() * static_cast<double>(Key) / Frames : 0.0;
		const FVector P = Clip->ExtractRootMotionFromRange(0.0, Time, FAnimExtractContext(Time, true)).GetTranslation();
		MinZ = FMath::Min(MinZ, P.Z); MaxZ = FMath::Max(MaxZ, P.Z); Net = P;
		FObject Sample = MakeShared<FJsonObject>(); Sample->SetNumberField(TEXT("time_seconds"), Time);
		Sample->SetNumberField(TEXT("x"), P.X); Sample->SetNumberField(TEXT("y"), P.Y); Sample->SetNumberField(TEXT("z"), P.Z); Samples.Add(Json(Sample));
	}
	Root->SetNumberField(TEXT("min_z"), MinZ); Root->SetNumberField(TEXT("max_z"), MaxZ); Root->SetNumberField(TEXT("z_range"), MaxZ - MinZ);
	Root->SetNumberField(TEXT("net_x"), Net.X); Root->SetNumberField(TEXT("net_y"), Net.Y); Root->SetNumberField(TEXT("net_z"), Net.Z);
	Root->SetStringField(TEXT("unit"), TEXT("UE ExtractRootMotionFromRange asset-local translation; before live SkeletalMesh component/CMC conversion. Existing mesh .01 is not multiplied here."));
	Root->SetArrayField(TEXT("cumulative_per_model_key"), Samples); Row->SetObjectField(TEXT("root_motion_probe"), Root);
	return Row;
}
bool SameRawRootRate(const FObject& A, const FObject& B, bool bCompareOptions)
{
	for (const TCHAR* Key : {TEXT("raw_bone_transform_md5"), TEXT("skeleton"), TEXT("root_bone"), TEXT("root_reference_scale"), TEXT("first_bone_track")})
		if (A->GetStringField(Key) != B->GetStringField(Key)) return false;
	for (const TCHAR* Key : {TEXT("seconds"), TEXT("rate_scale"), TEXT("frames"), TEXT("keys"), TEXT("fps_numerator"), TEXT("fps_denominator"), TEXT("bone_tracks"), TEXT("notify_count")})
		if (A->GetNumberField(Key) != B->GetNumberField(Key)) return false;
	return (!bCompareOptions || (A->GetBoolField(TEXT("enable_root_motion")) == B->GetBoolField(TEXT("enable_root_motion")) &&
		A->GetBoolField(TEXT("force_root_lock")) == B->GetBoolField(TEXT("force_root_lock")) &&
		A->GetNumberField(TEXT("root_lock_enum")) == B->GetNumberField(TEXT("root_lock_enum")))) &&
		A->GetBoolField(TEXT("normalized_root_motion_scale")) == B->GetBoolField(TEXT("normalized_root_motion_scale"));
}
UAnimSequence* LoadClip(const FString& Path)
{
	if (UAnimSequence** Existing = Clips.Find(Path)) return *Existing;
	UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *Path);
	if (!Clip || !Clip->GetDataModel() || !Clip->GetSkeleton() || Clip->GetSkeleton()->GetReferenceSkeleton().GetNum() == 0 ||
		!FMath::IsFinite(Clip->RateScale) || Clip->RateScale <= 0.f || Clip->GetPlayLength() <= 0.f) return nullptr;
	FObject Options = ClipOptions(Clip); SourceOptions.Add(Path, Options); SourceAudits.Add(Json(Options));
	if (Options->GetStringField(TEXT("first_bone_track")) != Options->GetStringField(TEXT("root_bone"))) return nullptr;
	Clips.Add(Path, Clip); return Clip;
}
UAnimSequence* ClonePlayer(const FObject& Plan, UAnimSequence* RootTemplate)
{
	const FString Source = Plan->GetStringField(TEXT("source")), Destination = Plan->GetStringField(TEXT("destination"));
	if (!Destination.StartsWith(TEXT("/Game/_Art/Player/Animation/InGame/DAS/Reaction/Clips/"))) return nullptr;
	UAnimSequence* Original = LoadClip(Source); if (!Original) return nullptr;
	const FObject Before = SourceOptions.FindRef(Source);
	UAnimSequence* Copy = LoadObject<UAnimSequence>(nullptr, *Destination, nullptr, LOAD_NoWarn);
	if (!Copy)
	{
		Copy = DuplicateObject<UAnimSequence>(Original, CreatePackage(*Destination), *FPackageName::GetLongPackageAssetName(Destination));
		Copy->SetFlags(RF_Public | RF_Standalone | RF_Transactional); FAssetRegistryModule::AssetCreated(Copy);
	}
	if (!Copy || !Copy->GetDataModel() || !Copy->GetSkeleton() || !SameRawRootRate(Before, ClipOptions(Copy), false)) return nullptr;
	// Authorized presentation option on the InGame duplicate only; no root transform rewrite/rescale.
	Copy->bEnableRootMotion = true; Copy->bForceRootLock = true;
	Copy->RootMotionRootLock = RootTemplate->RootMotionRootLock; Copy->PostEditChange();
	const FObject After = ClipOptions(Copy); const bool bPreserved = SameRawRootRate(Before, After, false) && SameRawRootRate(Before, ClipOptions(Original), true);
	FObject Row = MakeShared<FJsonObject>(); Row->SetObjectField(TEXT("plan"), Plan);
	Row->SetObjectField(TEXT("source_options"), Before); Row->SetObjectField(TEXT("copy_options"), After); Row->SetBoolField(TEXT("raw_root_rate_preserved"), bPreserved);
	Row->SetStringField(TEXT("option_change"), TEXT("InGame duplicate only: bEnableRootMotion=true, bForceRootLock=true, RootMotionRootLock from actual current WeakAttack first sequence. Normalized flag/raw/root/rate/model timeline preserved."));
	Row->SetObjectField(TEXT("root_option_template"), ClipOptions(RootTemplate)); CopyAudits.Add(Json(Row));
	if (!bPreserved || !Save(Copy)) return nullptr;
	Clips.Add(Destination, Copy); return Copy;
}
void PointNotify(UAnimMontage* Montage, FName Name, float Time)
{
	UAnimNotify_PlayMontageNotify* Notify = NewObject<UAnimNotify_PlayMontageNotify>(Montage, Name, RF_Transactional);
	FindFProperty<FNameProperty>(Notify->GetClass(), TEXT("NotifyName"))->SetPropertyValue_InContainer(Notify, Name);
	FAnimNotifyEvent Event; Event.NotifyName = Name; Event.Notify = Notify; Event.Guid = FGuid::NewGuid();
	Event.MontageTickType = EMontageNotifyTickType::BranchingPoint; Event.Link(Montage, Time); Montage->Notifies.Add(Event);
}
UAnimMontage* Montage(const FObject& Plan, UAnimMontage* Template)
{
	const FString Path = Plan->GetStringField(TEXT("destination"));
	const auto& Sections = Plan->GetArrayField(TEXT("sections")); if (Sections.IsEmpty()) return nullptr;
	TArray<UAnimSequence*> Sequences;
	for (const auto& Section : Sections)
	{
		UAnimSequence* Clip = Clips.FindRef(Section->AsObject()->GetStringField(TEXT("clip")));
		if (!Clip || !Clip->bEnableRootMotion) return nullptr; Sequences.Add(Clip);
	}
	USkeleton* Skeleton = Sequences[0]->GetSkeleton();
	if (!Skeleton || !Skeleton->ContainsSlotName(TEXT("DefaultSlot"))) return nullptr;
	UAnimMontage* Result = Asset<UAnimMontage>(Path); Result->SetSkeleton(Skeleton);
	Result->CompositeSections.Reset(); Result->Notifies.Reset(); Result->RateScale = 1.f;
	FSlotAnimationTrack Track; Track.SlotName = TEXT("DefaultSlot"); float Position = 0.f;
	TArray<TSharedPtr<FJsonValue>> SectionAudits; float LandTime = -1.f;
	const FString LandSection = Plan->GetStringField(TEXT("hit_land_section"));
	for (int32 Index = 0; Index < Sections.Num(); ++Index)
	{
		if (Sequences[Index]->GetSkeleton() != Skeleton) return nullptr;
		const FObject SectionPlan = Sections[Index]->AsObject(); FAnimSegment Segment;
		Segment.SetAnimReference(Sequences[Index]); Segment.StartPos = Position; Segment.AnimStartTime = 0.f;
		double SourceEnd = Sequences[Index]->GetPlayLength();
		SectionPlan->TryGetNumberField(TEXT("source_end_seconds"), SourceEnd);
		if (!FMath::IsFinite(SourceEnd) || SourceEnd <= 0.0) return nullptr;
		// Optional montage segment crop only. Raw source keys/root/rate/sequence length are never retimed.
		Segment.AnimEndTime = FMath::Min<double>(SourceEnd, Sequences[Index]->GetPlayLength());
		Segment.AnimPlayRate = 1.f; Segment.LoopingCount = 1;
		Track.AnimTrack.AnimSegments.Add(Segment); FCompositeSection Section;
		Section.SectionName = *SectionPlan->GetStringField(TEXT("name"));
		Section.NextSectionName = Index + 1 < Sections.Num() ? FName(*Sections[Index + 1]->AsObject()->GetStringField(TEXT("name"))) : NAME_None;
		Section.Link(Result, Position); Result->CompositeSections.Add(Section);
		if (Section.SectionName.ToString() == LandSection) LandTime = Position;
		FObject Row = MakeShared<FJsonObject>(); Row->SetObjectField(TEXT("plan"), SectionPlan);
		Row->SetStringField(TEXT("next"), Section.NextSectionName.ToString()); Row->SetNumberField(TEXT("start_seconds"), Position);
		Row->SetNumberField(TEXT("segment_length_seconds"), Segment.GetLength()); Row->SetNumberField(TEXT("clip_rate_scale"), Sequences[Index]->RateScale);
		Row->SetNumberField(TEXT("source_start_seconds"), Segment.AnimStartTime); Row->SetNumberField(TEXT("source_end_seconds"), Segment.AnimEndTime);
		Row->SetNumberField(TEXT("uncropped_source_length_seconds"), Sequences[Index]->GetPlayLength());
		Row->SetBoolField(TEXT("source_segment_cropped"), Segment.AnimEndTime < Sequences[Index]->GetPlayLength());
		Row->SetNumberField(TEXT("effective_segment_rate"), Segment.GetValidPlayRate()); Row->SetNumberField(TEXT("loops"), Segment.LoopingCount);
		SectionAudits.Add(Json(Row)); Position += Segment.GetLength();
	}
	Result->SlotAnimTracks = {Track};
	Result->BlendIn = Template->BlendIn; Result->BlendOut = Template->BlendOut;
	Result->BlendModeIn = Template->BlendModeIn; Result->BlendModeOut = Template->BlendModeOut;
	Result->BlendProfileIn = Template->BlendProfileIn; Result->BlendProfileOut = Template->BlendProfileOut;
	Result->BlendOutTriggerTime = Template->BlendOutTriggerTime; Result->bEnableAutoBlendOut = true;
	const FFrameRate Rate = Sequences[0]->GetDataModel()->GetFrameRate();
	Result->GetController().SetFrameRate(Rate, false); Result->GetController().SetNumberOfFrames(Rate.AsFrameTime(Position).RoundToFrame(), false);
	if (!LandSection.IsEmpty()) { if (LandTime < 0.f) return nullptr; PointNotify(Result, TEXT("HitLand"), LandTime); }
	Result->SortNotifies(); Result->PostEditChange(); Result->RefreshCacheData();
	FObject Row = MakeShared<FJsonObject>(); Row->SetObjectField(TEXT("plan"), Plan); Row->SetArrayField(TEXT("sections"), SectionAudits);
	Row->SetStringField(TEXT("asset"), Result->GetPathName()); Row->SetStringField(TEXT("slot"), Track.SlotName.ToString());
	Row->SetNumberField(TEXT("segment_total_seconds"), Position); Row->SetNumberField(TEXT("saved_montage_seconds"), Result->GetPlayLength());
	Row->SetNumberField(TEXT("hit_land_seconds"), LandTime); Row->SetBoolField(TEXT("finite_auto_chain"), true);
	Row->SetStringField(TEXT("blend_template"), Template->GetPathName()); Row->SetStringField(TEXT("blend_provenance"), TEXT("Existing project WeakAttack template, not verified original reaction blend."));
	Row->SetNumberField(TEXT("blend_in_seconds"), Result->BlendIn.GetBlendTime()); Row->SetNumberField(TEXT("blend_out_seconds"), Result->BlendOut.GetBlendTime());
	MontageAudits.Add(Json(Row)); return Save(Result) ? Result : nullptr;
}
TArray<TObjectPtr<UAnimMontage>>* Pool(FKZHitReactionSettings* Settings, const FString& Name)
{
	if (Name == TEXT("ShortHits")) return &Settings->ShortHits;
	if (Name == TEXT("Knockbacks")) return &Settings->Knockbacks;
	if (Name == TEXT("Launches")) return &Settings->Launches;
	if (Name == TEXT("ShieldBlocks")) return &Settings->ShieldBlocks;
	return nullptr;
}
bool WriteReport(const FString& Path, const FObject& Plan, bool bSuccess, const FString& Stage)
{
	FObject Report = MakeShared<FJsonObject>(); Report->SetStringField(TEXT("schema"), TEXT("Khazan.Combat.ReactionAuthor.v1"));
	Report->SetStringField(TEXT("project"), FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()));
	Report->SetNumberField(TEXT("pid"), FPlatformProcess::GetCurrentProcessId()); Report->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601());
	Report->SetBoolField(TEXT("success"), bSuccess); Report->SetStringField(TEXT("stage"), Stage); Report->SetObjectField(TEXT("input_plan"), Plan);
	Report->SetArrayField(TEXT("saved_packages"), Strings(SavedPackages)); Report->SetArrayField(TEXT("source_clips"), SourceAudits);
	Report->SetArrayField(TEXT("player_copies"), CopyAudits); Report->SetArrayField(TEXT("montages"), MontageAudits);
	Report->SetArrayField(TEXT("definitions"), DefinitionAudits); Report->SetArrayField(TEXT("system_guard_windows"), GuardAudits);
	Report->SetBoolField(TEXT("source_raw_root_rate_edited"), false); Report->SetBoolField(TEXT("root_rescale_applied"), false);
	Report->SetStringField(TEXT("in_place_air_motion_contract"), TEXT("Actual static true-root Air poses are preserved. Native HitReactionAbility owns engine RootMotionJumpForce for non-Short chains; zero source root Z is expected and does not skip/abort an authored Air pool."));
	Report->SetBoolField(TEXT("maps_or_blueprints_or_skeletons_saved"), false);
	FString Output; FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Output));
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path), true); return FFileHelper::SaveStringToFile(Output, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatReactionAuthorTest, "Khazan.Combat.ReactionAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZCombatReactionAuthorTest::RunTest(const FString& Parameters)
{
	using namespace KZCombatReactionAuthor;
	if (!FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()), WorkRoot) || !GEditor || GEditor->PlayWorld)
	{ AddError(TEXT("ReactionAuthor requires exact isolated MonsterWork editor and no PIE.")); return false; }
	SavedPackages.Reset(); SourceAudits.Reset(); CopyAudits.Reset(); MontageAudits.Reset(); DefinitionAudits.Reset(); GuardAudits.Reset(); Clips.Reset(); SourceOptions.Reset();
	const FString PlanPath = FPaths::ProjectDir() / TEXT("Metadata/CombatReaction_20261008/ReactionAuthoringPlan.json"); FString Text; FObject Plan;
	if (!FFileHelper::LoadFileToString(Text, *PlanPath) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Plan) || !Plan.IsValid())
	{ AddError(TEXT("Stage exact ReactionAuthoringPlan.json in isolated Work Metadata.")); return false; }
	const FString Output = FPaths::ProjectSavedDir() / TEXT("CombatReaction/Authoring.json");
	bool bFinished = false; FString Stage = TEXT("Preflight");
	ON_SCOPE_EXIT { WriteReport(Output, Plan, bFinished, Stage); };
	const auto& Bodies = Plan->GetArrayField(TEXT("bodies")); const auto& Copies = Plan->GetArrayField(TEXT("player_copies"));
	if (!TestEqual(TEXT("Seven actual bodies"), Bodies.Num(), 7) || !TestEqual(TEXT("24 organized Player copies"), Copies.Num(), 24) ||
		!TestEqual(TEXT("221 exact current Enemy clips"), Plan->GetArrayField(TEXT("enemy_source_audit")).Num(), 221)) return false;
	UAnimMontage* Template = LoadObject<UAnimMontage>(nullptr, *Plan->GetStringField(TEXT("blend_template")));
	if (!TestNotNull(TEXT("Current WeakAttack blend template"), Template)) return false;
	UAnimSequence* RootTemplate = Template->SlotAnimTracks.IsEmpty() || Template->SlotAnimTracks[0].AnimTrack.AnimSegments.IsEmpty() ? nullptr :
		Cast<UAnimSequence>(Template->SlotAnimTracks[0].AnimTrack.AnimSegments[0].GetAnimReference());
	if (!TestNotNull(TEXT("Actual current WeakAttack root option sequence"), RootTemplate)) return false;
	// Preflight every specifically listed source/pool before the first save. No registry-wide scan.
	for (const auto& Value : Plan->GetArrayField(TEXT("enemy_source_audit")))
	{
		const FObject Row = Value->AsObject(); UAnimSequence* Clip = LoadClip(Row->GetStringField(TEXT("CurrentAsset")));
		if (!TestNotNull(TEXT("Exact Enemy source"), Clip) || !TestTrue(TEXT("Enemy existing root options remain enabled"), Clip && Clip->bEnableRootMotion && Clip->bForceRootLock)) return false;
	}
	for (const auto& Value : Copies) if (!TestNotNull(TEXT("Exact Player source"), LoadClip(Value->AsObject()->GetStringField(TEXT("source"))))) return false;
	for (const auto& BodyValue : Bodies)
	{
		const FObject Body = BodyValue->AsObject(); UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *Body->GetStringField(TEXT("definition")));
		if (!TestNotNull(TEXT("Existing authored Definition"), Definition) || !Field<FKZHitReactionSettings>(Definition, TEXT("HitReactions")) ||
			!Field<TArray<FKZInitialAbilityGrant>>(Definition, TEXT("InitialAbilityGrants"))) return false;
		for (const auto& MontageValue : Body->GetArrayField(TEXT("montages")))
		{
			const FObject M = MontageValue->AsObject(); const FString Destination = M->GetStringField(TEXT("destination"));
			const FString Prefix = Body->GetStringField(TEXT("body")) == TEXT("Player") ? TEXT("/Game/_Art/Player/Animation/InGame/DAS/Reaction/Montages/") :
				TEXT("/Game/Monsters/") + Body->GetStringField(TEXT("body")) + TEXT("/Animations/Reaction/Montages/");
			if (!TestTrue(TEXT("Scoped Reaction montage path"), Destination.StartsWith(Prefix))) return false;
			for (const auto& Section : M->GetArrayField(TEXT("sections")))
			{
				const FString Path = Section->AsObject()->GetStringField(TEXT("clip"));
				if (!Path.StartsWith(TEXT("/Game/_Art/Player/Animation/InGame/DAS/Reaction/Clips/")) && !TestNotNull(TEXT("Existing exact montage clip"), LoadClip(Path))) return false;
			}
		}
	}
	if (!WriteReport(FPaths::ProjectSavedDir() / TEXT("CombatReaction/SourceProbe.json"), Plan, true, TEXT("ReadOnlyActualSourcesBeforeAnySave"))) return false;
	if (FParse::Param(FCommandLine::Get(), TEXT("CombatReactionProbeOnly")))
	{ Stage = TEXT("ReadOnlySourceProbeCompleteNoAssetsSaved"); bFinished = true; return true; }
	Stage = TEXT("PlayerCopies");
	for (const auto& Value : Copies) if (!TestNotNull(TEXT("Preserved Player duplicate"), ClonePlayer(Value->AsObject(), RootTemplate))) return false;
	if (FParse::Param(FCommandLine::Get(), TEXT("CombatReactionCopiesOnly")))
	{ Stage = TEXT("CopiesAndRootProbeCompleteNoMontagesOrDefinitionsSaved"); bFinished = true; return true; }
	Stage = TEXT("MontagesAndDefinitionPools");
	for (const auto& BodyValue : Bodies)
	{
		const FObject Body = BodyValue->AsObject(); const FString Name = Body->GetStringField(TEXT("body"));
		UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *Body->GetStringField(TEXT("definition")));
		FKZHitReactionSettings* Settings = Field<FKZHitReactionSettings>(Definition, TEXT("HitReactions"));
		Settings->ShortHits.Reset(); Settings->Knockbacks.Reset(); Settings->Launches.Reset(); Settings->ShieldBlocks.Reset();
		Settings->bSystemGuardOnLockOn = Body->GetBoolField(TEXT("system_guard_on_lockon"));
		if (Settings->bSystemGuardOnLockOn) Settings->SystemGuardFrontAngle = Body->GetNumberField(TEXT("system_guard_front_angle"));
		TArray<TSharedPtr<FJsonValue>> Unsupported;
		for (const auto& Value : Body->GetArrayField(TEXT("montages")))
		{
			const FObject M = Value->AsObject();
			// Original true-root Air tracks are intentionally static: the runtime force supplies world motion.
			UAnimMontage* Authored = Montage(M, Template); TArray<TObjectPtr<UAnimMontage>>* SelectedPool = Pool(Settings, M->GetStringField(TEXT("pool")));
			if (!TestNotNull(TEXT("Finite authored montage"), Authored) || !SelectedPool) return false; SelectedPool->Add(Authored);
		}
		auto* Grants = Field<TArray<FKZInitialAbilityGrant>>(Definition, TEXT("InitialAbilityGrants"));
		const int32 Before = Grants->Num();
		FKZInitialAbilityGrant* Existing = Grants->FindByPredicate([](const FKZInitialAbilityGrant& Grant) { return Grant.AbilityClass == UKZHitReactionAbility::StaticClass(); });
		if (Existing) { if (!TestFalse(TEXT("Native event reaction grant has no input binding"), Existing->InputTag.IsValid())) return false; }
		else { FKZInitialAbilityGrant Grant; Grant.AbilityClass = UKZHitReactionAbility::StaticClass(); Grants->Add(Grant); }
		if (!TestTrue(TEXT("Short fallback pool nonempty"), !Settings->ShortHits.IsEmpty()) || !TestTrue(TEXT("Save exact Definition"), Save(Definition))) return false;
		FObject Row = MakeShared<FJsonObject>(); Row->SetStringField(TEXT("body"), Name); Row->SetStringField(TEXT("asset"), Definition->GetPathName());
		Row->SetNumberField(TEXT("grants_before"), Before); Row->SetNumberField(TEXT("grants_after"), Grants->Num());
		Row->SetStringField(TEXT("reaction_grant"), UKZHitReactionAbility::StaticClass()->GetPathName()); Row->SetArrayField(TEXT("unsupported_launch_plans"), Unsupported);
		for (const FString& PoolName : {FString(TEXT("ShortHits")), FString(TEXT("Knockbacks")), FString(TEXT("Launches")), FString(TEXT("ShieldBlocks"))})
		{
			TArray<FString> Paths; for (UAnimMontage* M : *Pool(Settings, PoolName)) Paths.Add(M->GetPathName()); Row->SetArrayField(PoolName, Strings(Paths));
		}
		Row->SetBoolField(TEXT("system_guard_on_lockon"), Settings->bSystemGuardOnLockOn); Row->SetNumberField(TEXT("system_guard_full_cone_degrees"), Settings->SystemGuardFrontAngle);
		Row->SetArrayField(TEXT("organized_unconnected_recovery_copies"), Body->GetArrayField(TEXT("unconnected_recovery_copies"))); DefinitionAudits.Add(Json(Row));
	}
	Stage = TEXT("SwordShieldComboNodeWindows"); TMap<FString, UKZComboDefinitionData*> Combos;
	for (const auto& Value : Plan->GetArrayField(TEXT("system_guard_windows")))
	{
		const FObject Row = Value->AsObject(); const FString Path = Row->GetStringField(TEXT("combo_definition"));
		UKZComboDefinitionData*& Definition = Combos.FindOrAdd(Path);
		if (!Definition)
		{
			Definition = LoadObject<UKZComboDefinitionData>(nullptr, *Path); if (!TestNotNull(TEXT("Actual SwordShield combo definition"), Definition)) return false;
			auto* Nodes = Field<TArray<FKZComboNode>>(Definition, TEXT("Nodes")); if (!Nodes) return false;
			for (FKZComboNode& Node : *Nodes) Node.SystemGuardWindows.Reset();
		}
		auto* Nodes = Field<TArray<FKZComboNode>>(Definition, TEXT("Nodes"));
		FKZComboNode* Node = Nodes->FindByPredicate([&Row](const FKZComboNode& N) { return N.NodeId == FName(*Row->GetStringField(TEXT("node_id"))); });
		if (!Node || !Node->Montage || Node->Montage->GetOutermost()->GetName() != Row->GetStringField(TEXT("montage"))) return false;
		const int32 Section = Node->Montage->GetSectionIndex(Node->SectionName); if (Section == INDEX_NONE) return false;
		const float SectionStart = Node->Montage->GetAnimCompositeSection(Section).GetTime();
		if (!TestTrue(TEXT("Saved authored montage section offset matches provenance"), FMath::IsNearlyEqual(SectionStart, static_cast<float>(Row->GetNumberField(TEXT("montage_segment_start_seconds")))))) return false;
		const FVector2D Window(Row->GetNumberField(TEXT("clipped_local_start_seconds")), Row->GetNumberField(TEXT("clipped_local_end_seconds")));
		Node->SystemGuardWindows.Add(Window); FObject Audit = MakeShared<FJsonObject>(); Audit->SetObjectField(TEXT("provenance"), Row);
		Audit->SetStringField(TEXT("definition"), Definition->GetPathName()); Audit->SetStringField(TEXT("node_id"), Node->NodeId.ToString());
		Audit->SetNumberField(TEXT("local_start_seconds"), Window.X); Audit->SetNumberField(TEXT("local_end_seconds"), Window.Y);
		Audit->SetNumberField(TEXT("actual_section_start_seconds"), SectionStart); GuardAudits.Add(Json(Audit));
	}
	for (const auto& Entry : Combos) if (!TestTrue(TEXT("Save exact SwordShield combo windows"), Save(Entry.Value))) return false;
	Stage = TEXT("SourceIntegrity");
	for (const auto& Entry : SourceOptions)
		if (!TestTrue(TEXT("Source raw/root/rate/options unchanged after author"), SameRawRootRate(Entry.Value, ClipOptions(Clips.FindRef(Entry.Key)), true))) return false;
	if (!TestEqual(TEXT("24 copies authored"), CopyAudits.Num(), 24) || !TestEqual(TEXT("Seven Definition pools authored"), DefinitionAudits.Num(), 7) ||
		!TestEqual(TEXT("Nine exact node guard provenance intervals"), GuardAudits.Num(), 9)) return false;
	Stage = TEXT("Complete"); bFinished = true; return true;
}
#endif
