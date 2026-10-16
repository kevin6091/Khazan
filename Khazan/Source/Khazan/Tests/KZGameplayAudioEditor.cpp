#if WITH_EDITOR
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundWave.h"
#include "Sound/ReverbEffect.h"
#include "Sound/SoundSubmix.h"
#include "Sound/SoundNode.h"
#include "Sound/SoundNodeRandom.h"
#include "Sound/SoundNodeWavePlayer.h"
#include "Sound/SoundNodeDelay.h"
#include "Sound/SoundNodeLooping.h"
#include "Sound/SoundNodeModulator.h"
#include "Sound/SoundNodeEnveloper.h"
#include "Sound/SoundAttenuation.h"
#include "Curves/CurveFloat.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/Notifies/KZAnimNotify_PlayAudio.h"
#include "Animation/Notifies/KZAnimNotifyState_PlayAudio.h"
#include "Misc/PackageName.h"
#include "UObject/UnrealType.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "AudioDevice.h"
#include "AudioThread.h"
#include "ActiveSound.h"
#include "Settings/LevelEditorMiscSettings.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "UObject/SavePackage.h"

// Save reviewable binding packages without asking a different editor to release
// its file handles. The caller compares hashes before replacing unlocked files.
static FAutoConsoleCommand KZSaveAudioBindingCopy(
	TEXT("KZ.Audio.SaveBindingCopy"),TEXT("Save an audio binding copy under the task report directory."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if(Args.Num()!=2 || !Args[0].StartsWith(TEXT("/Game/")))return;
		const FString Root=FPaths::ConvertRelativePathToFull(Args[1]);
		if(!Root.StartsWith(FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("ImportReports/GameplayAudio_20261011/"))))return;
		UKZComboDefinitionData* Data=LoadObject<UKZComboDefinitionData>(nullptr,*Args[0]);if(!Data)return;
		const FString Filename=Root/(Args[0].RightChop(6)+TEXT(".uasset"));
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename),true);
		FSavePackageArgs Save;Save.TopLevelFlags=RF_Public|RF_Standalone;Save.SaveFlags=SAVE_NoError;
		const bool bSaved=UPackage::SavePackage(Data->GetPackage(),Data,*Filename,Save);
		UE_LOG(LogTemp,Display,TEXT("KZAUDIO_BINDING_COPY %s Saved=%d"),*Args[0],bSaved);
	}));

static FAutoConsoleCommand KZMountAudioBindingCopies(
	TEXT("KZ.Audio.MountBindingCopies"),TEXT("Mount prepared audio bindings for a read-only fresh-process audit."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if(Args.Num()==1)FPackageName::RegisterMountPoint(TEXT("/KZAudioBindingStage/"),Args[0]/TEXT(""));
	}));

// Editor-only finalization for the actual imported cue graph. Python can assign
// FirstNode/ChildNodes, but UE deliberately hides the editor AllNodes cache.
static FAutoConsoleCommand KZFinalizeAudioCues(
	TEXT("KZ.Audio.FinalizeCues"), TEXT("Rebuild editor graph/cache for the authored original sound cues."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if (Args.Num() != 1) return;
		FString Text;
		TSharedPtr<FJsonObject> Plan;
		if (!FFileHelper::LoadFileToString(Text, *Args[0]) ||
			!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Plan)) return;
		const TArray<TSharedPtr<FJsonValue>>* Cues = nullptr;
		if (!Plan->TryGetArrayField(TEXT("cue_paths"), Cues)) return;
		int32 Count = 0;
		for (const auto& Row : *Cues)
		{
			const FString Path = Row->AsString();
			if (!Path.StartsWith(TEXT("/Game/Audio/Original/"))) continue;
			USoundCue* Cue = LoadObject<USoundCue>(nullptr, *Path);
			if (!Cue || !Cue->FirstNode) continue;
			UE_LOG(LogTemp, Display, TEXT("KZAudio Finalizing=%s"), *Path);
			TArray<USoundNode*> Nodes;
			// Graph links visit every child, while the engine's runtime helper
			// intentionally visits only MaxChildNodes. Audit the complete authored
			// tree before creating editor links, including unreachable children.
			TArray<USoundNode*> Pending { Cue->FirstNode };
			bool bValid = true;
			while (!Pending.IsEmpty())
			{
				USoundNode* Node = Pending.Pop();
				if (!Node || Nodes.Contains(Node)) continue;
				Nodes.Add(Node);
				if (Node->ChildNodes.Num() > Node->GetMaxChildNodes())
				{
					UE_LOG(LogTemp, Error, TEXT("KZAudio ChildLimit Cue=%s Node=%s Num=%d Max=%d"),
						*Path, *Node->GetClass()->GetName(), Node->ChildNodes.Num(), Node->GetMaxChildNodes());
					bValid = false;
				}
				for (USoundNode* Child : Node->ChildNodes) if (Child) Pending.Add(Child);
			}
			if (!bValid) continue;
			Cue->AllNodes.Reset();
			// Reauthoring must remove obsolete graph nodes too. Reusing their pins
			// can retain a former node type/child count after a recipe correction.
			Cue->SoundCueGraph = nullptr;
			Cue->CreateGraph();
			for (USoundNode* Node : Nodes)
			{
				// SoundWave is a transient cache. The engine setter also stores the
				// persistent SoundWaveAssetPtr used by PostLoad/streaming/cooking.
				if (auto* Wave = Cast<USoundNodeWavePlayer>(Node))
					if (Wave->GetSoundWave()) Wave->SetSoundWave(Wave->GetSoundWave());
				Cue->AllNodes.Add(Node);
				Node->GraphNode = nullptr;
				Cue->SetupSoundNode(Node, false);
				if (USoundNodeRandom* Random = Cast<USoundNodeRandom>(Node))
				{
					check(Random->Weights.Num() == Random->ChildNodes.Num());
					Random->HasBeenUsed.Init(false, Random->ChildNodes.Num());
					Random->NumRandomUsed = 0;
				}
			}
			Cue->LinkGraphNodesFromSoundNodes();
			Cue->CacheAggregateValues();
			Cue->MarkPackageDirty();
			++Count;
		}
		UE_LOG(LogTemp, Display, TEXT("KZAudio FinalizedCues=%d Requested=%d"), Count, Cues->Num());
	}));

static FAutoConsoleCommand KZBuildAmbientWrappers(
	TEXT("KZ.Audio.BuildAmbientWrappers"), TEXT("Rebuild only task-owned native ambient wrappers from saved source cues."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if (Args.Num()!=1) return;
		FString Text;TSharedPtr<FJsonObject> Plan;
		if (!FFileHelper::LoadFileToString(Text,*Args[0]) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan)) return;
		int32 Count=0;
		for (const auto& V:Plan->GetArrayField(TEXT("wrappers")))
		{
			const auto R=V->AsObject();const FString TargetPath=R->GetStringField(TEXT("target"));
			if (!TargetPath.StartsWith(TEXT("/Game/Audio/Original/Environment/"))) continue;
			auto* Source=LoadObject<USoundCue>(nullptr,*R->GetStringField(TEXT("source")));
			auto* Target=LoadObject<USoundCue>(nullptr,*TargetPath);
			if (!Source || !Target || !Source->FirstNode) continue;
			// Duplicate the containing cue so its whole owned graph is copied.
			// Moving that owned node set retains only original SoundWave references.
			auto* Copy=DuplicateObject<USoundCue>(Source,GetTransientPackage());
			for (USoundNode* Node:Copy->AllNodes)
				if (Node)
				{
					const FName Name=MakeUniqueObjectName(Target,Node->GetClass(),TEXT("KZARebuilt"));
					Node->Rename(*Name.ToString(),Target,REN_DontCreateRedirectors|REN_ForceNoResetLoaders);
				}
			Target->FirstNode=Copy->FirstNode;Target->AttenuationOverrides=Source->AttenuationOverrides;
			Target->bOverrideAttenuation=Source->bOverrideAttenuation;Target->AttenuationSettings=Source->AttenuationSettings;
			Target->SoundSubmixObject=Source->SoundSubmixObject;
			if (R->GetBoolField(TEXT("repeat")))
			{
				auto* Delay=NewObject<USoundNodeDelay>(Target);Delay->ChildNodes.Add(Target->FirstNode);
				Delay->DelayMin=R->GetNumberField(TEXT("delay_min"));Delay->DelayMax=R->GetNumberField(TEXT("delay_max"));
				auto* Loop=NewObject<USoundNodeLooping>(Target);Loop->ChildNodes.Add(Delay);Loop->bLoopIndefinitely=true;Target->FirstNode=Loop;
			}
			if (R->GetBoolField(TEXT("fire")))
			{
				auto* Mod=NewObject<USoundNodeModulator>(Target);Mod->ChildNodes.Add(Target->FirstNode);
				Mod->PitchMin=R->GetNumberField(TEXT("pitch_min"));Mod->PitchMax=R->GetNumberField(TEXT("pitch_max"));
				Mod->VolumeMin=Mod->VolumeMax=R->GetNumberField(TEXT("gain"));Target->FirstNode=Mod;
			}
			Target->VirtualizationMode=EVirtualizationMode::Restart;Target->MarkPackageDirty();++Count;
		}
		UE_LOG(LogTemp,Display,TEXT("KZAudio AmbientWrappers=%d"),Count);
	}));

// Inline native curves avoid hundreds of duplicate attenuation assets. All
// authored points and fallback provenance remain in SpatialAudioPlan01.json.
static FAutoConsoleCommand KZApplyAudioSpatial(
	TEXT("KZ.Audio.ApplySpatialPlan"), TEXT("Apply source radius/volume curves to original cues."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if (Args.Num()!=1) return;
		FString Text;TSharedPtr<FJsonObject> Plan;
		if (!FFileHelper::LoadFileToString(Text,*Args[0]) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan)) return;
		int32 Count=0;
		for (const auto& V:Plan->GetArrayField(TEXT("cues")))
		{
			const auto Row=V->AsObject();const FString Path=Row->GetStringField(TEXT("cue"));
			if (!Path.StartsWith(TEXT("/Game/Audio/Original/"))) continue;
			USoundCue* Cue=LoadObject<USoundCue>(nullptr,*Path);if (!Cue) continue;
			const float Radius=Row->GetNumberField(TEXT("max_distance_cm"));
			Cue->bOverrideAttenuation=true;Cue->AttenuationSettings=nullptr;
			auto& A=Cue->AttenuationOverrides;A=FSoundAttenuationSettings();
			A.bAttenuate=Radius>0.f;A.bSpatialize=Row->GetBoolField(TEXT("spatialize"));
			A.AttenuationShape=EAttenuationShape::Sphere;A.AttenuationShapeExtents=FVector::ZeroVector;A.FalloffDistance=Radius;
			A.DistanceAlgorithm=EAttenuationDistanceModel::Linear;
			const TSharedPtr<FJsonObject>* Curve=nullptr;
			if (Radius>0.f && Row->TryGetObjectField(TEXT("selected_curve"),Curve) && Curve && Curve->IsValid())
			{
				A.DistanceAlgorithm=EAttenuationDistanceModel::Custom;
				FRichCurve* Native=A.CustomAttenuationCurve.GetRichCurve();Native->Reset();
				for (const auto& K:(*Curve)->GetArrayField(TEXT("keys")))
				{
					const auto Key=K->AsObject();const FKeyHandle Handle=Native->AddKey(Key->GetNumberField(TEXT("distance_cm"))/Radius,Key->GetNumberField(TEXT("gain")));
					Native->SetKeyInterpMode(Handle,Key->GetIntegerField(TEXT("source_interp"))==9?RCIM_Constant:RCIM_Linear);
				}
			}
			const auto Reverb=Row->GetObjectField(TEXT("temporary_reverb_send"));
			A.bEnableReverbSend=true;A.ReverbWetLevelMin=Reverb->GetNumberField(TEXT("min"));A.ReverbWetLevelMax=Reverb->GetNumberField(TEXT("max"));
			A.ReverbDistanceMin=0.f;A.ReverbDistanceMax=Radius;
			if (Cue->IsLooping()) Cue->VirtualizationMode=EVirtualizationMode::Restart;
			Cue->CacheAggregateValues();Cue->MarkPackageDirty();++Count;
		}
		UE_LOG(LogTemp,Display,TEXT("KZAudio SpatialCues=%d Requested=%d"),Count,Plan->GetArrayField(TEXT("cues")).Num());
	}));

// Fresh saved-package verification, including the pre-audio animation backup.
// This command only reads assets; no graph finalization or package save occurs.
static FAutoConsoleCommand KZAuditSavedAudio(
	TEXT("KZ.Audio.AuditSaved"),TEXT("Audit persistent wave references and preservation of animation data."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if(Args.Num()!=1)return;
		FString Text;TSharedPtr<FJsonObject> Plan;
		if(!FFileHelper::LoadFileToString(Text,*Args[0]) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan))return;
		TSharedRef<FJsonObject> Result=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> CueRows,AnimRows;
		bool bSuccess=true;int32 WaveCount=0;
		for(const auto& Value:Plan->GetArrayField(TEXT("cues")))
		{
			const FString Path=Value->AsString();USoundCue* Cue=LoadObject<USoundCue>(nullptr,*Path);
			TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("asset"),Path);
			TArray<USoundNode*> Seen,Pending;int32 Waves=0;bool bValid=Cue && Cue->FirstNode;
			if(bValid)Pending.Add(Cue->FirstNode);
			while(!Pending.IsEmpty())
			{
				USoundNode* Node=Pending.Pop();if(!Node || Seen.Contains(Node))continue;Seen.Add(Node);
				bValid &= Node->GetOuter()==Cue && Node->ChildNodes.Num()<=Node->GetMaxChildNodes();
				if(USoundNodeWavePlayer* Wave=Cast<USoundNodeWavePlayer>(Node))
				{
					FSoftObjectProperty* Property=FindFProperty<FSoftObjectProperty>(Wave->GetClass(),TEXT("SoundWaveAssetPtr"));
					const FSoftObjectPath Stored=Property?Property->GetPropertyValue_InContainer(Wave).ToSoftObjectPath():FSoftObjectPath();
					USoundWave* Media=Cast<USoundWave>(Stored.TryLoad());
					bValid &= Media && Media->Duration>0.f && Media->NumChannels>0;
					++Waves;
				}
				for(USoundNode* Child:Node->ChildNodes)if(Child)Pending.Add(Child);
			}
			Row->SetBoolField(TEXT("persistent_graph_valid"),bValid);Row->SetNumberField(TEXT("nodes"),Seen.Num());Row->SetNumberField(TEXT("wave_players"),Waves);
			bSuccess &= bValid;WaveCount+=Waves;CueRows.Add(MakeShared<FJsonValueObject>(Row));
		}
		const FString Backup=Plan->GetStringField(TEXT("backup_content"));
		FPackageName::RegisterMountPoint(TEXT("/KZAudioBefore/"),Backup/TEXT(""));
		for(const auto& Value:Plan->GetArrayField(TEXT("sequences")))
		{
			const FString Path=Value->AsString(),OldPath=Path.Replace(TEXT("/Game/"),TEXT("/KZAudioBefore/"));
			UAnimSequence* Current=LoadObject<UAnimSequence>(nullptr,*Path);UAnimSequence* Before=LoadObject<UAnimSequence>(nullptr,*OldPath);
			TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("asset"),Path);
			bool bPose=false,bNotifies=false;
			if(Current && Before && Current->GetDataModel() && Before->GetDataModel())
			{
				Row->SetStringField(TEXT("before_model_guid"),Before->GetDataModel()->GenerateGuid().ToString());
				Row->SetStringField(TEXT("current_model_guid"),Current->GetDataModel()->GenerateGuid().ToString());
				bPose=Before->GetDataModel()->GenerateGuid()==Current->GetDataModel()->GenerateGuid() &&
					Before->RateScale==Current->RateScale && Before->bEnableRootMotion==Current->bEnableRootMotion &&
					Before->RootMotionRootLock==Current->RootMotionRootLock && Before->bForceRootLock==Current->bForceRootLock &&
					Before->bUseNormalizedRootMotionScale==Current->bUseNormalizedRootMotionScale;
				auto NonAudio=[](UAnimSequence* Sequence)
				{
					TArray<FString> Events;
					for(const FAnimNotifyEvent& Notify:Sequence->Notifies)
					{
						if((Notify.Notify && Notify.Notify->IsA<UKZAnimNotify_PlayAudio>()) ||
							(Notify.NotifyStateClass && Notify.NotifyStateClass->IsA<UKZAnimNotifyState_PlayAudio>()))continue;
						FString Event;FAnimNotifyEvent::StaticStruct()->ExportText(Event,&Notify,nullptr,Sequence,PPF_None,nullptr);
						Events.Add(Event.Replace(TEXT("/KZAudioBefore/"),TEXT("/Game/")));
					}
					return Events;
				};
				bNotifies=NonAudio(Before)==NonAudio(Current);
			}
			Row->SetBoolField(TEXT("pose_curve_rate_root_preserved"),bPose);Row->SetBoolField(TEXT("non_audio_notifies_preserved"),bNotifies);
			bSuccess &= bPose && bNotifies;AnimRows.Add(MakeShared<FJsonValueObject>(Row));
		}
		FPackageName::UnRegisterMountPoint(TEXT("/KZAudioBefore/"),Backup/TEXT(""));
		Result->SetBoolField(TEXT("success"),bSuccess);Result->SetNumberField(TEXT("package_saves"),0);Result->SetNumberField(TEXT("wave_players"),WaveCount);
		Result->SetArrayField(TEXT("cues"),CueRows);Result->SetArrayField(TEXT("sequences"),AnimRows);
		FString Output;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*Plan->GetStringField(TEXT("output")));
		UE_LOG(LogTemp,Display,TEXT("KZAUDIO_SAVED Success=%d Cues=%d Sequences=%d WavePlayers=%d"),bSuccess,CueRows.Num(),AnimRows.Num(),WaveCount);
	}));
// Python cannot write the protected Notifies array. Earlier duplicate contacts
// can sit outside KZAudio, so clear only these two classes, retaining every
// gameplay/VFX notify object, GUID, field and clock for scoped reauthoring.
static FAutoConsoleCommand KZAudioClearNotifyClasses(
	TEXT("KZ.Audio.ClearNotifyClasses"),TEXT("Clear existing audio notify classes in one loaded sequence; never saves."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if(Args.Num()!=1)return;
		UAnimSequence* Sequence=LoadObject<UAnimSequence>(nullptr,*Args[0]);if(!Sequence)return;
		Sequence->Modify();
		Sequence->Notifies.RemoveAll([](const FAnimNotifyEvent& E)
		{
			return Cast<UKZAnimNotify_PlayAudio>(E.Notify) || Cast<UKZAnimNotifyState_PlayAudio>(E.NotifyStateClass);
		});
		Sequence->RefreshCacheData();Sequence->MarkPackageDirty();
	}));
static FAutoConsoleCommand KZAudioSourcePlayFades(
	TEXT("KZ.Audio.ApplyPlayFades"),TEXT("Apply original CAkActionPlay linear fade envelopes."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if(Args.Num()!=1)return;FString Text;TSharedPtr<FJsonObject> Plan;
		if(!FFileHelper::LoadFileToString(Text,*Args[0]) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan))return;
		for(const auto& Value:Plan->GetArrayField(TEXT("fades")))
		{
			const auto Row=Value->AsObject();USoundCue* Cue=LoadObject<USoundCue>(nullptr,*Row->GetStringField(TEXT("cue")));
			if(!Cue || !Cue->FirstNode)continue;
			TSet<FString> TargetMedia;for(const auto& Media:Row->GetArrayField(TEXT("target_media")))TargetMedia.Add(Media->AsString());
			TFunction<TSet<FString>(USoundNode*)> Signature=[&Signature](USoundNode* Node)
			{
				TSet<FString> Media;if(!Node)return Media;
				if(USoundNodeWavePlayer* Player=Cast<USoundNodeWavePlayer>(Node))
					if(USoundWave* Wave=Player->GetSoundWave())
					{
						TArray<FString> Parts;Wave->GetName().ParseIntoArray(Parts,TEXT("_"));
						if(Parts.Num()>1 && Parts[1].IsNumeric())Media.Add(Parts[1]);
					}
				for(USoundNode* Child:Node->ChildNodes)Media.Append(Signature(Child));return Media;
			};
			TObjectPtr<USoundNode>* Match=nullptr;
			TFunction<void(TObjectPtr<USoundNode>&)> Find=[&](TObjectPtr<USoundNode>& Link)
			{
				if(!Link || Match)return;
				if(Signature(Link).Includes(TargetMedia) && Signature(Link).Num()==TargetMedia.Num()){Match=&Link;return;}
				for(auto& Child:Link->ChildNodes)Find(Child);
			};
			Find(Cue->FirstNode);
			if(!Match){UE_LOG(LogTemp,Error,TEXT("KZAUDIO_FADE Missing source target subtree Cue=%s Target=%s"),*Cue->GetPathName(),*Row->GetStringField(TEXT("target")));continue;}
			const FString Prefix=TEXT("KZAOriginalPlayFade_Target")+Row->GetStringField(TEXT("target"));
			USoundNodeEnveloper* Envelope=Cast<USoundNodeEnveloper>(*Match);
			if(!Envelope || !Envelope->GetName().StartsWith(Prefix))
			{
				Envelope=NewObject<USoundNodeEnveloper>(Cue,MakeUniqueObjectName(Cue,USoundNodeEnveloper::StaticClass(),FName(*Prefix)));
				Envelope->ChildNodes.Add(*Match);*Match=Envelope;
			}
			Envelope->bLoop=false;Envelope->bLoopIndefinitely=false;
			FRichCurve* Volume=Envelope->VolumeCurve.GetRichCurve();Volume->Reset();
			Volume->SetKeyInterpMode(Volume->AddKey(0.f,0.f),RCIM_Linear);
			Volume->SetKeyInterpMode(Volume->AddKey(Row->GetNumberField(TEXT("seconds")),1.f),RCIM_Linear);
			const int32 Curve=Row->GetIntegerField(TEXT("curve_id"));
			if(Curve!=4)
				// Temporary UE shape adapter: source Log1/Exp1 equations are not
				// available. This sampling count is a technical curve representation.
				for(int32 I=1;I<16;++I)
				{
					const float T=float(I)/16.f;
					Volume->SetKeyInterpMode(Volume->AddKey(T*Row->GetNumberField(TEXT("seconds")),Curve==2?FMath::Sqrt(T):T*T),RCIM_Linear);
				}
			Cue->CacheAggregateValues();Cue->MarkPackageDirty();
			UE_LOG(LogTemp,Display,TEXT("KZAUDIO_FADE Cue=%s Target=%s Seconds=%f Curve=%d"),*Cue->GetPathName(),*Row->GetStringField(TEXT("target")),Row->GetNumberField(TEXT("seconds")),Curve);
		}
	}));

static FAutoConsoleCommand KZAudioOwnedBackground(
	TEXT("KZ.Audio.AllowBackground"),TEXT("Set the in-memory editor background-audio flag for the owned fixture, without saving settings."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		static TOptional<bool> Saved;
		if(Args.Num()!=1)return;
		if(Args[0]==TEXT("restore")){if(Saved.IsSet())GetMutableDefault<ULevelEditorMiscSettings>()->bAllowBackgroundAudio=Saved.GetValue();Saved.Reset();return;}
		if(!Saved.IsSet())Saved=GetDefault<ULevelEditorMiscSettings>()->bAllowBackgroundAudio;
		GetMutableDefault<ULevelEditorMiscSettings>()->bAllowBackgroundAudio=Args[0]==TEXT("1");
	}));

static FAutoConsoleCommand KZCaptureAudioFixture(
	TEXT("KZ.Audio.Capture"),TEXT("Capture the actual PIE device without retaining a Python World wrapper across automation GC."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		static FAudioDeviceHandle Device;static TStrongObjectPtr<USoundSubmix> Submix;
		if(Args.Num()!=3 || !GEngine)return;
		if(Args[0]==TEXT("start"))
		{
			for(const FWorldContext& Context:GEngine->GetWorldContexts())
				if(Context.WorldType==EWorldType::PIE && Context.World() && Context.World()->HasBegunPlay())
				{
					Device=Context.World()->GetAudioDevice();Submix.Reset(LoadObject<USoundSubmix>(nullptr,TEXT("/Game/Audio/Original/Settings/SM_Original")));
					if(Device && Submix.IsValid())Submix->StartRecordingOutput(static_cast<FAudioDevice*>(Device),300.f);return;
				}
		}
		else if(Args[0]==TEXT("stop"))
		{
			if(Device && Submix.IsValid())Submix->StopRecordingOutput(static_cast<FAudioDevice*>(Device),EAudioRecordingExportType::WavFile,Args[1],Args[2]);
			Submix.Reset();Device=FAudioDeviceHandle();
		}
	}));

static FAutoConsoleCommand KZInspectAudioDevice(
	TEXT("KZ.Audio.InspectDevice"),TEXT("Read the owned PIE listener, routing, reverb and voice state."),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if(Args.Num()!=1 || !GEngine)return;
		for(const FWorldContext& Context:GEngine->GetWorldContexts())
		{
			if(Context.WorldType!=EWorldType::PIE || !Context.World())continue;
			FAudioDeviceHandle Device=Context.World()->GetAudioDevice();if(!Device)continue;
			TSharedRef<FJsonObject> Result=MakeShared<FJsonObject>();
			Result->SetNumberField(TEXT("device"),Device->DeviceID);
			Result->SetStringField(TEXT("reverb_effect"),Device->GetCurrentReverbEffect()?Device->GetCurrentReverbEffect()->GetPathName():TEXT(""));
			const FString Output=Args[0];
			FAudioThread::RunCommandOnAudioThread([Device,Result,Output]()
			{
				Result->SetBoolField(TEXT("muted"),Device->IsAudioDeviceMuted());Result->SetNumberField(TEXT("primary_gain"),Device->GetPrimaryVolume());
				Result->SetNumberField(TEXT("active_sounds"),Device->GetActiveSounds().Num());
				TArray<TSharedPtr<FJsonValue>> Sounds;
				for(const FActiveSound* Sound:Device->GetActiveSounds())
					if(Sound && Sound->GetSound())Sounds.Add(MakeShared<FJsonValueString>(Sound->GetSound()->GetPathName()));
				Result->SetArrayField(TEXT("sound_paths"),Sounds);
				TArray<TSharedPtr<FJsonValue>> Listeners;
				for(const FListener& Listener:Device->GetListeners())
				{
					const FVector Location=Listener.Transform.GetTranslation();TArray<TSharedPtr<FJsonValue>> Coordinates;
					for(int32 I=0;I<3;++I)Coordinates.Add(MakeShared<FJsonValueNumber>(Location[I]));
					Listeners.Add(MakeShared<FJsonValueArray>(Coordinates));
				}
				Result->SetArrayField(TEXT("listeners_cm"),Listeners);
				FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Output);
			});
			return;
		}
	}));
#endif
