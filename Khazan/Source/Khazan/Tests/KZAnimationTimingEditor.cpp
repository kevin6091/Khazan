#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/AnimDataNotifications.h"
#include "MovieScene.h"
#include "MovieSceneSequence.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Misc/SecureHash.h"
#include "UObject/UnrealType.h"
#include "UObject/SavePackage.h"
#include "UObject/MetaData.h"
#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"

namespace KZTimingEditor
{
void ScaleCurveClock(FRichCurve& Curve,double Factor)
{
	for(auto It=Curve.GetKeyHandleIterator();It;++It)
	{
		FRichCurveKey& K=Curve.GetKey(*It);
		const auto Weight=[Factor](float Slope,float W){return float(W*FMath::Sqrt(Factor*Factor+double(Slope)*Slope)/FMath::Sqrt(1.+double(Slope)*Slope));};
		K.ArriveTangentWeight=Weight(K.ArriveTangent,K.ArriveTangentWeight);K.LeaveTangentWeight=Weight(K.LeaveTangent,K.LeaveTangentWeight);
		K.Time*=Factor;K.ArriveTangent/=Factor;K.LeaveTangent/=Factor;
	}
}
void ScaleEffectClock(UKZAnimNotify_CombatEffect* Effect,double Factor)
{
	if(!Effect)return;Effect->WindowStartTime*=Factor;Effect->WindowEndTime*=Factor;
	for(FRuntimeVectorCurve* C:{&Effect->SourceCorrectionTranslation,&Effect->SourceCorrectionRotation,&Effect->SourceCorrectionScale})
		for(int32 Axis=0;Axis<3;++Axis)ScaleCurveClock(*C->GetRichCurve(Axis),Factor);
}
FString BoneKeys(IAnimationDataModel* Model, int64& Keys)
{
	FMD5 Hash; TArray<FName> Names; Model->GetBoneTrackNames(Names); Keys=0;
	for (FName Name:Names)
	{
		const FString Text=Name.ToString(); FTCHARToUTF8 Utf(*Text);
		Hash.Update(reinterpret_cast<const uint8*>(Utf.Get()),Utf.Length());
		Model->IterateBoneKeys(Name,[&](const FVector3f& P,const FQuat4f& Q,const FVector3f S,const FFrameNumber& Frame)
		{
			Hash.Update(reinterpret_cast<const uint8*>(&Frame.Value),sizeof(Frame.Value));
			Hash.Update(reinterpret_cast<const uint8*>(&P),sizeof(P));
			Hash.Update(reinterpret_cast<const uint8*>(&Q),sizeof(Q));
			Hash.Update(reinterpret_cast<const uint8*>(&S),sizeof(S)); ++Keys; return true;
		});
	}
	uint8 Digest[16];Hash.Final(Digest);return BytesToHex(Digest,16);
}
bool Save(UObject* Object)
{
	FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;Args.SaveFlags=SAVE_NoError;
	const FString File=FPackageName::LongPackageNameToFilename(Object->GetPackage()->GetName(),FPackageName::GetAssetPackageExtension());
	return UPackage::SavePackage(Object->GetPackage(),Object,*File,Args);
}
TSharedPtr<FJsonObject> NotifyContract(const FAnimNotifyEvent& N)
{
	auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("name"),N.NotifyName.ToString());
	FString Guid;FindFProperty<FStructProperty>(FAnimNotifyEvent::StaticStruct(),TEXT("Guid"))->ExportText_InContainer(0,Guid,&N,&N,nullptr,PPF_None);
	R->SetStringField(TEXT("guid"),Guid);R->SetNumberField(TEXT("time"),N.GetTime());R->SetNumberField(TEXT("duration"),N.GetDuration());
	return R;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZAnimationTimingAuthor,"Khazan.AnimationTiming.NormalizeFPS",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZAnimationTimingAuthor::RunTest(const FString&)
{
	using namespace KZTimingEditor;
	const FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir());
	if (!Root.Contains(TEXT("Khazan_SlamDistortWork_20261012"))) {AddError(TEXT("Author is private-workspace only"));return false;}
	const FString PlanPath=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_TIMING_PLAN"));
	const FString Out=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_OUT"));
	const bool bMontagesOnly=!FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_TIMING_MONTAGE_ONLY")).IsEmpty();
	FString Text;TSharedPtr<FJsonObject> Plan;
	if (!FFileHelper::LoadFileToString(Text,*PlanPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan))return false;
	const TArray<TSharedPtr<FJsonValue>>& Rows=Plan->GetArrayField(TEXT("sequences"));
	TMap<FString,UAnimSequence*> Sequences;TMap<FString,double> Factors;
	TMap<FString,UAnimMontage*> Montages;
	// Load dependents on the old clock first, avoiding PostLoad's automatic full-range repair.
	for (const auto& Value:Plan->GetArrayField(TEXT("montages")))
	{
		const FString Path=Value->AsObject()->GetStringField(TEXT("asset"));
		UAnimMontage* M=LoadObject<UAnimMontage>(nullptr,*Path);if(!M)return false;Montages.Add(Path,M);
	}
	// Validate the complete scope before any write. These assets have no float/transform curves or attributes.
	for (const auto& Value:Rows)
	{
		const auto Row=Value->AsObject();const FString Path=Row->GetStringField(TEXT("asset"));
		UAnimSequence* S=LoadObject<UAnimSequence>(nullptr,*Path);IAnimationDataModel* Model=S?S->GetDataModel():nullptr;
		if (!Model||Model->GetNumberOfFloatCurves()||Model->GetNumberOfTransformCurves()||Model->GetNumberOfAttributes())
		{AddError(TEXT("Unsupported model data: ")+Path);return false;}
		const auto& FPS=Row->GetArrayField(TEXT("fps"));
		const FFrameRate ExpectedRate=bMontagesOnly?FFrameRate(int32(Row->GetNumberField(TEXT("target_fps"))),1):FFrameRate(int32(FPS[0]->AsNumber()),int32(FPS[1]->AsNumber()));
		if (Model->GetFrameRate()!=ExpectedRate ||
			Model->GetNumberOfFrames()!=int32(Row->GetNumberField(TEXT("frames"))))
		{AddError(TEXT("Stale clock plan: ")+Path);return false;}
		UMovieSceneSequence* MovieSequence=Cast<UMovieSceneSequence>(S->GetDataModelInterface().GetObject());
		if (MovieSequence)
		{
			if (!MovieSequence->GetMovieScene()||MovieSequence->GetMovieScene()->GetTickResolution()!=Model->GetFrameRate())
			{AddError(TEXT("Non-uniform channel clock: ")+Path);return false;}
		}
		else if (!FindFProperty<FStructProperty>(S->GetDataModelInterface().GetObject()->GetClass(),TEXT("FrameRate")))
		{AddError(TEXT("Unsupported clock owner: ")+Path);return false;}
		Sequences.Add(Path,S);Factors.Add(Path,Row->GetNumberField(TEXT("time_scale")));
		for(const FAnimNotifyEvent& N:S->Notifies)
		{
			const auto* Visual=Cast<UKZAnimNotifyState_MonsterVisual>(N.NotifyStateClass);
			if(Visual&&Visual->ScalarCurve.ExternalCurve){AddError(TEXT("Shared external scalar clock: ")+Path);return false;}
			const auto* Effect=Visual?Visual->Effect.Get():Cast<UKZAnimNotify_CombatEffect>(N.Notify);
			if(Effect&&(Effect->SourceCorrectionTranslation.ExternalCurve||Effect->SourceCorrectionRotation.ExternalCurve||Effect->SourceCorrectionScale.ExternalCurve))
			{AddError(TEXT("Shared external correction clock: ")+Path);return false;}
		}
	}
	TArray<TSharedPtr<FJsonValue>> Results;
	if(bMontagesOnly)
	{
		FString PreviousText;TSharedPtr<FJsonObject> PreviousReport;
		const FString PreviousPath=FPaths::GetPath(PlanPath)/TEXT("Author03/NativeAuthor.json");
		if(!FFileHelper::LoadFileToString(PreviousText,*PreviousPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PreviousText),PreviousReport))return false;
		Results=PreviousReport->GetArrayField(TEXT("sequences"));
	}
	for (const auto& Value:Rows)
	{
		if(bMontagesOnly)break;
		const auto Row=Value->AsObject();const FString Path=Row->GetStringField(TEXT("asset"));
		UAnimSequence* S=Sequences[Path];IAnimationDataModel* Model=S->GetDataModel();
		const double Factor=Factors[Path],OldLength=S->GetPlayLength();const float OldRate=S->RateScale;
		const FFrameRate OldFPS=Model->GetFrameRate(),TargetFPS(int32(Row->GetNumberField(TEXT("target_fps"))),1);
		const int32 Frames=Model->GetNumberOfFrames();int64 BeforeKeys=0,AfterKeys=0;
		const FString Before=BoneKeys(Model,BeforeKeys);
		TArray<TPair<float,float>> NotifyTimes;
		for (const FAnimNotifyEvent& N:S->Notifies)NotifyTimes.Emplace(N.GetTime(),N.GetDuration());
		S->GetController().OpenBracket(FText::FromString(TEXT("Normalize clock without resampling bone keys")),false);
		if (UMovieSceneSequence* MovieSequence=Cast<UMovieSceneSequence>(S->GetDataModelInterface().GetObject()))
		{
			// Frame-index channel keys/range remain untouched; only their clock unit changes.
			UMovieScene* Movie=MovieSequence->GetMovieScene();Movie->SetDisplayRate(TargetFPS);Movie->SetTickResolutionDirectly(TargetFPS);
		}
		else
		{
			UObject* ModelObject=S->GetDataModelInterface().GetObject();
			*FindFProperty<FStructProperty>(ModelObject->GetClass(),TEXT("FrameRate"))->ContainerPtrToValuePtr<FFrameRate>(ModelObject)=TargetFPS;
		}
		S->RateScale=float(double(OldRate)*Factor);
		FindFProperty<FFloatProperty>(S->GetClass(),TEXT("SequenceLength"))->SetPropertyValue_InContainer(S,float(Model->GetPlayLength()));
		FStructProperty* PlatformProperty=FindFProperty<FStructProperty>(S->GetClass(),TEXT("PlatformTargetFrameRate"));
		FPerPlatformFrameRate* Platform=PlatformProperty->ContainerPtrToValuePtr<FPerPlatformFrameRate>(S);
		Platform->Default=TargetFPS;
		for(auto& Override:Platform->PerPlatform)Override.Value=TargetFPS;
		// Notify and rebuild derived data through the controller on the now-compatible
		// clock. Its current == target conversion keeps every frame index/range intact.
		S->GetController().SetFrameRate(TargetFPS,false);
		S->GetController().CloseBracket(false);
		TSet<UObject*> MappedPayloads;
		for (int32 I=0;I<S->Notifies.Num();++I)
		{
			FAnimNotifyEvent& N=S->Notifies[I];N.SetTime(float(NotifyTimes[I].Key*Factor));
			N.SetDuration(float(NotifyTimes[I].Value*Factor));
			N.TriggerTimeOffset*=Factor;N.EndTriggerTimeOffset*=Factor;
			if(auto* Visual=Cast<UKZAnimNotifyState_MonsterVisual>(N.NotifyStateClass);Visual&&!MappedPayloads.Contains(Visual))
			{
				MappedPayloads.Add(Visual);ScaleCurveClock(*Visual->ScalarCurve.GetRichCurve(),Factor);
				if(Visual->Effect&&!MappedPayloads.Contains(Visual->Effect)){MappedPayloads.Add(Visual->Effect);ScaleEffectClock(Visual->Effect,Factor);}
			}
			if(auto* Effect=Cast<UKZAnimNotify_CombatEffect>(N.Notify);Effect&&!MappedPayloads.Contains(Effect))
			{MappedPayloads.Add(Effect);ScaleEffectClock(Effect,Factor);}
		}
		for (FAnimSyncMarker& Marker:S->AuthoredSyncMarkers)Marker.Time*=Factor;
		S->RefreshCacheData();
		const FString After=BoneKeys(Model,AfterKeys);
		if (Before!=After || BeforeKeys!=AfterKeys || Model->GetNumberOfFrames()!=Frames || Model->GetFrameRate()!=TargetFPS)
		{AddError(TEXT("Bone keys changed: ")+Path);return false;}
		const double DurationError=FMath::Abs(S->GetPlayLength()/S->RateScale-OldLength/OldRate);
		if (DurationError>0.00002){AddError(TEXT("Effective duration changed: ")+Path);return false;}
		S->GetPackage()->GetMetaData().SetValue(S,TEXT("IntegerFPSRepair"),*FString::Printf(TEXT("20261012; %d/%d -> %d/1; unchanged frame-index keys; local time scale %.12g; RateScale %.9g -> %.9g; original baked timing preserved"),OldFPS.Numerator,OldFPS.Denominator,TargetFPS.Numerator,Factor,OldRate,S->RateScale));
		if (!Save(S)){AddError(TEXT("Save failed: ")+Path);return false;}
		auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("asset"),Path);R->SetStringField(TEXT("bone_key_hash_before"),Before);R->SetStringField(TEXT("bone_key_hash_after"),After);
		R->SetNumberField(TEXT("bone_keys"),BeforeKeys);R->SetNumberField(TEXT("effective_duration_error"),DurationError);
		R->SetNumberField(TEXT("old_seconds"),OldLength);R->SetNumberField(TEXT("new_seconds"),S->GetPlayLength());R->SetNumberField(TEXT("new_rate_scale"),S->RateScale);
		TArray<TSharedPtr<FJsonValue>> Notifies;for(const auto& N:S->Notifies)Notifies.Add(MakeShared<FJsonValueObject>(NotifyContract(N)));R->SetArrayField(TEXT("notifies"),Notifies);
		Results.Add(MakeShared<FJsonValueObject>(R));
	}
	TArray<TSharedPtr<FJsonValue>> MontageResults;
	for (const auto& Value:Plan->GetArrayField(TEXT("montages")))
	{
		const auto Row=Value->AsObject();const FString Path=Row->GetStringField(TEXT("asset"));
		UAnimMontage* M=Montages[Path];if (!M)return false;
		TArray<float> SectionTimes,NotifyTimes,NotifyDurations;
		for(const auto& S:M->CompositeSections)SectionTimes.Add(S.GetTime());
		for(const auto& N:M->Notifies){NotifyTimes.Add(N.GetTime());NotifyDurations.Add(N.GetDuration());}
		const double OldLength=Row->GetNumberField(TEXT("seconds"));
		int32 SegmentIndex=0;const auto& OriginalSegments=Row->GetArrayField(TEXT("segments"));
		for(FSlotAnimationTrack& Track:M->SlotAnimTracks)
			for(FAnimSegment& Segment:Track.AnimTrack.AnimSegments)
			{
				const auto Original=OriginalSegments[SegmentIndex++]->AsObject();
				const double* Found=Factors.Find(Original->GetStringField(TEXT("asset")));const double Factor=Found?*Found:1.;
				Segment.StartPos=Original->GetNumberField(TEXT("start"));Segment.AnimStartTime=Original->GetNumberField(TEXT("anim_start"))*Factor;Segment.AnimEndTime=Original->GetNumberField(TEXT("anim_end"))*Factor;
				Segment.AnimPlayRate=Original->GetNumberField(TEXT("anim_rate"));Segment.LoopingCount=int32(Original->GetNumberField(TEXT("loops")));Segment.UpdateCachedPlayLength();
			}
		FindFProperty<FFloatProperty>(M->GetClass(),TEXT("SequenceLength"))->SetPropertyValue_InContainer(M,float(OldLength));
		M->PostEditChange();M->RefreshCacheData();M->UpdateLinkableElements();
		// Keep the existing montage model's precision clock. Its actual displayed
		// sampling rate now derives from the integer-rate sequence references.
		for(int32 I=0;I<SectionTimes.Num();++I)M->CompositeSections[I].SetTime(SectionTimes[I]);
		for(int32 I=0;I<NotifyTimes.Num();++I){M->Notifies[I].SetTime(NotifyTimes[I]);M->Notifies[I].SetDuration(NotifyDurations[I]);}
		M->RefreshCacheData();
		if (M->GetSamplingFrameRate().Denominator!=1 || M->GetSamplingFrameRate().Numerator>60 || FMath::Abs(M->GetPlayLength()-OldLength)>0.0001)
		{AddError(TEXT("Montage timing not preserved: ")+Path);return false;}
		if (!Save(M))return false;
		auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("asset"),Path);R->SetNumberField(TEXT("sampling_fps"),M->GetSamplingFrameRate().AsDecimal());
		R->SetNumberField(TEXT("duration_error"),FMath::Abs(M->GetPlayLength()-OldLength));MontageResults.Add(MakeShared<FJsonValueObject>(R));
	}
	auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("success"),true);Report->SetArrayField(TEXT("sequences"),Results);Report->SetArrayField(TEXT("montages"),MontageResults);
	FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(Out/TEXT("NativeAuthor.json")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZAnimationTimingSaved,"Khazan.AnimationTiming.SavedAudit",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZAnimationTimingSaved::RunTest(const FString&)
{
	using namespace KZTimingEditor;
	const FString Main=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_TIMING_MAIN")),Out=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_OUT"));
	const FString Base=Main/TEXT("Metadata/AnimationTimingKnockback_20261012");
	const auto Read=[](const FString& P){FString S;TSharedPtr<FJsonObject> O;FFileHelper::LoadFileToString(S,*P);FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),O);return O;};
	const auto Author=Read(Base/TEXT("AuthorFinal/NativeAuthor.json")),Plan=Read(Base/TEXT("Plan.json")),Inventory=Read(Base/TEXT("SamplingBefore01/Inventory.json"));
	if(!Author||!Plan||!Inventory)return false;
	int64 Keys=0;double MaximumDurationError=0.;TArray<TSharedPtr<FJsonValue>> Montages;
	for(const auto& V:Author->GetArrayField(TEXT("sequences")))
	{
		const auto R=V->AsObject();const FString Path=R->GetStringField(TEXT("asset"));UAnimSequence* S=LoadObject<UAnimSequence>(nullptr,*Path);if(!S)return false;
		int64 Count=0;const FString Hash=BoneKeys(S->GetDataModel(),Count);Keys+=Count;
		if(Hash!=R->GetStringField(TEXT("bone_key_hash_before"))||S->GetDataModel()->GetFrameRate().Denominator!=1||S->GetSamplingFrameRate().Denominator!=1)
		{AddError(TEXT("Saved bone keys/clock mismatch: ")+Path);return false;}
		const auto& Expected=R->GetArrayField(TEXT("notifies"));if(Expected.Num()!=S->Notifies.Num())return false;
		for(int32 I=0;I<S->Notifies.Num();++I)
		{
			const auto Actual=NotifyContract(S->Notifies[I]),N=Expected[I]->AsObject();
			if(Actual->GetStringField(TEXT("guid"))!=N->GetStringField(TEXT("guid"))||Actual->GetStringField(TEXT("name"))!=N->GetStringField(TEXT("name"))||
				FMath::Abs(Actual->GetNumberField(TEXT("time"))-N->GetNumberField(TEXT("time")))>0.00001||FMath::Abs(Actual->GetNumberField(TEXT("duration"))-N->GetNumberField(TEXT("duration")))>0.00001)
			{AddError(TEXT("Saved notify mismatch: ")+Path);return false;}
		}
	}
	for(const auto& V:Inventory->GetArrayField(TEXT("composites")))
	{
		const auto R=V->AsObject();const FString Path=R->GetStringField(TEXT("asset"));UAnimMontage* M=LoadObject<UAnimMontage>(nullptr,*Path);if(!M)return false;
		const FFrameRate FPS=M->GetSamplingFrameRate();const double Error=FMath::Abs(M->GetPlayLength()-R->GetNumberField(TEXT("seconds")));MaximumDurationError=FMath::Max(MaximumDurationError,Error);
		if(FPS.Denominator!=1||FPS.AsDecimal()>=100000.||Error>0.0001){AddError(TEXT("Saved montage clock/duration mismatch: ")+Path);return false;}
		auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("asset"),Path);Item->SetNumberField(TEXT("fps"),FPS.AsDecimal());Item->SetNumberField(TEXT("display_frames"),M->GetNumberOfSampledKeys());Montages.Add(MakeShared<FJsonValueObject>(Item));
	}
	auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("success"),true);Report->SetNumberField(TEXT("unchanged_bone_keys"),Keys);Report->SetNumberField(TEXT("maximum_montage_duration_error"),MaximumDurationError);Report->SetArrayField(TEXT("montages"),Montages);
	FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(Out/TEXT("SavedAudit.json")));return true;
}
#endif
