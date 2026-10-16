#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Animation/Notifies/KZAnimNotify_PlayAudio.h"
#include "Animation/Notifies/KZAnimNotifyState_PlayAudio.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifyQueue.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Data/KZCharacterDefinitionData.h"
#include "AbilitySystemComponent.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "AudioDevice.h"
#include "AudioThread.h"
#include "Settings/LevelEditorPlaySettings.h"
#include "Settings/LevelEditorMiscSettings.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundSubmix.h"
#include "Sound/AudioSettings.h"
#include "Misc/App.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace KZAudioQA
{
class FRun : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* T, AKZPlayer* P): Test(T),Player(P),Deadline(FPlatformTime::Seconds()+120.) {}
	~FRun() override { Cleanup(); }
	bool Update() override
	{
		if (!Player.IsValid() || FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Audio PIE timeout/lost player")); return Finish(); }
		UWorld* World=Player->GetWorld(); const float Now=World->GetTimeSeconds();
		if (Phase==0)
		{
			FString Text;TSharedPtr<FJsonObject> Plan;
			if (!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()/TEXT("Saved/ImportReports/GameplayAudio_20261011/RuntimeSamples01.json"))) ||
				!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan)) { Test->AddError(TEXT("Missing audio runtime sample plan"));return Finish(); }
			Samples=Plan->GetArrayField(TEXT("samples"));Output=Plan->GetStringField(TEXT("output"));
			Submix=LoadObject<USoundSubmix>(nullptr,*Plan->GetStringField(TEXT("submix")));
			Master=Cast<USoundSubmix>(GetDefault<UAudioSettings>()->MasterSubmix.TryLoad());
			Test->TestTrue(TEXT("Actual PIE audio device exists"),bool(World->GetAudioDevice()));
			if (!Submix.IsValid() || !Master.IsValid()) { Test->AddError(TEXT("Imported/default capture submix missing"));return Finish(); }
			SavedFocus=FApp::GetUnfocusedVolumeMultiplier();FApp::SetUnfocusedVolumeMultiplier(1.f);
			SavedBackgroundAudio=GetDefault<ULevelEditorMiscSettings>()->bAllowBackgroundAudio;
			GetMutableDefault<ULevelEditorMiscSettings>()->bAllowBackgroundAudio=true;
			// Owned fixture diagnostics: inspect the real PIE device on its owning
			// audio thread. Engine PDB type information was unavailable in LLDB.
			UE_LOG(LogTemp, Display, TEXT("KZAUDIO_DEVICE GT GameSound=%d FocusGain=%f AppGain=%f Device=%u"),
				GetDefault<ULevelEditorPlaySettings>()->EnableGameSound, FApp::GetUnfocusedVolumeMultiplier(),
				FApp::GetVolumeMultiplier(), World->GetAudioDevice()->DeviceID);
			const FAudioDeviceHandle Device=World->GetAudioDevice();
			FAudioThread::RunCommandOnAudioThread([Device]()
			{
				UE_LOG(LogTemp, Display, TEXT("KZAUDIO_DEVICE AT Muted=%d TransientGain=%f PrimaryGain=%f Active=%d"),
					Device->IsAudioDeviceMuted(),Device->GetTransientPrimaryVolume(),Device->GetPrimaryVolume(),Device->GetActiveSounds().Num());
			});
			SavedLocation=Player->GetActorLocation();Player->GetCharacterMovement()->DisableMovement();Player->GetAbilitySystemComponent()->CancelAllAbilities();
			for(TActorIterator<AKZMonster> It(World);It;++It)
			{
				Monsters.Add(*It);
				if(auto* AI=Cast<AAIController>(It->GetController())) if(AI->BrainComponent) AI->BrainComponent->PauseLogic(TEXT("Owned audio fixture"));
				It->GetAbilitySystemComponent()->CancelAllAbilities();It->GetCharacterMovement()->StopMovementImmediately();
			}
			Master->StartRecordingOutput(World,60.f);bRecording=true;Phase=1;return false;
		}
		if (Phase==1)
		{
			if (Index>=Samples.Num()) { Phase=4; return false; }
			const auto Row=Samples[Index]->AsObject(); const FString Family=Row->GetStringField(TEXT("family"));
			Owner=Player.Get();
			if(Family!=TEXT("Player"))
			{
				Owner=nullptr;
				for(const auto& M:Monsters) if(M.IsValid() && M->GetCharacterDefinition() && M->GetCharacterDefinition()->GetName().Contains(Family)) { Owner=M;break; }
			}
			if(!Owner.IsValid()) { Test->AddError(TEXT("Missing actual family actor ")+Family);++Index;return false; }
			USkeletalMeshComponent* Mesh=Owner->GetMesh();UAnimInstance* Anim=Mesh->GetAnimInstance();
			UAnimSequence* Clip=LoadObject<UAnimSequence>(nullptr,*Row->GetStringField(TEXT("asset")));
			if(!Anim || !Clip) { Test->AddError(TEXT("Missing actual animation ")+Family);++Index;return false; }
			for(UAudioComponent* C:TInlineComponentArray<UAudioComponent*>(Owner.Get())) if(C->ComponentHasTag(TEXT("KZOriginalAudio"))) C->Stop();
			Seen.Reset();Start=Now;ClipSeconds=Row->GetNumberField(TEXT("seconds"));Row->TryGetBoolField(TEXT("cancel"),bCancel);
			bCancelDone=false;BaselineComponents=0;
			if(APlayerController* Controller=World->GetFirstPlayerController())Controller->SetAudioListenerOverride(nullptr,Owner->GetActorLocation(),FRotator::ZeroRotator);
			Submix->StartRecordingOutput(World,ClipSeconds+1.f);bSegmentRecording=true;
			Montage=Anim->PlaySlotAnimationAsDynamicMontage(Clip,TEXT("DefaultSlot"),0.f,0.f,1.f,1);
			if(!Montage.IsValid()) { Test->AddError(TEXT("Actual mesh rejected audio montage"));++Index;return false; }
			Phase=2;return false;
		}
		if(Phase==2)
		{
			if(!Owner.IsValid()) { Test->AddError(TEXT("Fixture owner lost"));return Finish(); }
			for(UAudioComponent* C:TInlineComponentArray<UAudioComponent*>(Owner.Get()))
				if(IsValid(C) && C->ComponentHasTag(TEXT("KZOriginalAudio")) && C->Sound && C->IsPlaying())
				{
					Seen.Add(C->Sound->GetPathName().LeftChop(C->Sound->GetName().Len()+1));
					++BaselineComponents;
				}
			const auto Row=Samples[Index]->AsObject();const auto Expected=Row->GetArrayField(TEXT("expected"));
			float First=MAX_flt;
			for(const auto& E:Expected) First=FMath::Min(First,float(E->AsObject()->GetNumberField(TEXT("start"))));
			// QA-only margins cover GT tick + async audio command dispatch, not
			// source gameplay tuning or a claim of sample-exact audio latency.
			if(bCancel && !bCancelDone && Now-Start>First+.15f) { Owner->GetMesh()->GetAnimInstance()->Montage_Stop(0.f,Montage.Get());bCancelDone=true;CancelTime=Now; }
			if((!bCancel && Now-Start>ClipSeconds+.3f) || (bCancelDone && Now-CancelTime>.3f))
			{
				Test->TestTrue(TEXT("Actual engine notify dispatched source audio ")+Row->GetStringField(TEXT("family")),BaselineComponents>0);
				if(bCancel)
				{
					for(UAudioComponent* C:TInlineComponentArray<UAudioComponent*>(Owner.Get()))
						if(IsValid(C) && C->ComponentHasTag(TEXT("KZOriginalAudio")) && C->IsPlaying())
							for(const FName Tag:C->ComponentTags) if(Tag.ToString().StartsWith(TEXT("KZAudioWindow_")))
								Test->TestFalse(TEXT("Canceled source stop window no longer plays"),C->Sound && Seen.Contains(C->Sound->GetPathName().LeftChop(C->Sound->GetName().Len()+1)));
				}
				Test->AddInfo(FString::Printf(TEXT("KZAUDIO_ACTUAL Family=%s Clip=%s Observed=%d Cancel=%d"),*Row->GetStringField(TEXT("family")),*Row->GetStringField(TEXT("asset")),Seen.Num(),bCancel));
				Submix->StopRecordingOutput(World,EAudioRecordingExportType::WavFile,Row->GetStringField(TEXT("family"))+TEXT("_")+FString::FromInt(Index),Output);bSegmentRecording=false;
				++Index;Phase=1;bCancel=false;
			}
			return false;
		}
		if(Phase==4)
		{
			// Source ambience supplies a real looping cue. Test the same stateless
			// begin/end owner path without saving a synthetic animation asset.
			LoopNotify=NewObject<UKZAnimNotifyState_PlayAudio>(Player.Get());
			LoopNotify->Playback=NewObject<UKZAnimNotify_PlayAudio>(LoopNotify.Get());
			LoopNotify->Playback->Sound=LoadObject<USoundCue>(nullptr,TEXT("/Game/Audio/Original/Events/SC_Play_Amb_M_Heinmach_Forest01"));
			LoopNotify->FadeOutSeconds=.08f;LoopNotify->bStopAtEnd=true;
			Test->TestTrue(TEXT("Imported source forest cue is looping"),LoopNotify->Playback->Sound && LoopNotify->Playback->Sound->IsLooping());
			FAnimNotifyEventReference Ref;LoopNotify->NotifyBegin(Player->GetMesh(),nullptr,1.f,Ref);LoopStart=Now;Phase=5;return false;
		}
		if(Phase==5 && Now-LoopStart>.2f)
		{
			FAnimNotifyEventReference Ref;LoopNotify->NotifyEnd(Player->GetMesh(),nullptr,Ref);LoopStart=Now;Phase=6;return false;
		}
		if(Phase==6 && Now-LoopStart>.2f)
		{
			for(UAudioComponent* C:TInlineComponentArray<UAudioComponent*>(Player.Get()))
				if(C->Sound==LoopNotify->Playback->Sound) Test->TestFalse(TEXT("Loop end cleans own audio component"),C->IsPlaying());
			Phase=7;return false;
		}
		if(Phase==7)
		{
			if(ProjectileIndex>=2)return Finish();
			const FString Family=ProjectileIndex==0?TEXT("ApesStoneHandElite"):TEXT("Yetuga");
			const FString Prefix=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_AUDIO_BINDING_COPIES")).IsEmpty()?TEXT("/Game/"):TEXT("/KZAudioBindingStage/");
			UKZComboDefinitionData* Definition=LoadObject<UKZComboDefinitionData>(nullptr,*(Prefix+TEXT("Monsters/")+Family+TEXT("/Data/DA_OriginalPatterns_")+Family));
			const FKZMonsterPatternObject* Data=Definition?Definition->GetPatternObjects().FindByPredicate([](const auto& O){return O.Id.ToString().Contains(TEXT("FastBall"));}):nullptr;
			AKZMonster* Caster=nullptr;for(const auto& M:Monsters)if(M.IsValid() && M->GetCharacterDefinition()->GetName().Contains(Family)){Caster=M.Get();break;}
			if(!Data || !Data->ProjectileSound || !Caster){Test->AddError(TEXT("Saved projectile audio/caster missing ")+Family);return Finish();}
			// QA-only geometry/tick hold isolates launch audio from an immediate
			// fixture-floor impact. The actual saved definition and Shoot/Impact
			// production methods own sound creation and cleanup.
			Projectile=World->SpawnActor<AKZMonsterSkillObject>(Player->GetActorLocation()+FVector(0,0,2000),FRotator::ZeroRotator);
			Projectile->Initialize(*Data,Definition->GetAttackDamageEffect(),Caster,nullptr);Projectile->SetActorTickEnabled(false);
			if(APlayerController* Controller=World->GetFirstPlayerController())Controller->SetAudioListenerOverride(nullptr,Projectile->GetActorLocation(),FRotator::ZeroRotator);
			Submix->StartRecordingOutput(World,2.f);bSegmentRecording=true;Projectile->Shoot(Player.Get());LoopStart=Now;Phase=8;return false;
		}
		if(Phase==8 && Now-LoopStart>.5f)
		{
			bool bAudio=false;for(UAudioComponent* C:TInlineComponentArray<UAudioComponent*>(Projectile.Get()))if(C->IsPlaying()){Flight=C;bAudio=true;}
			Test->TestTrue(TEXT("Actual Shoot creates attached original flight audio"),bAudio);
			Projectile->TriggerDestruction();Test->TestFalse(TEXT("Actual Impact stops flight audio"),Flight.IsValid() && Flight->IsPlaying());
			LoopStart=Now;Phase=9;return false;
		}
		if(Phase==9 && Now-LoopStart>.2f)
		{
			Submix->StopRecordingOutput(World,EAudioRecordingExportType::WavFile,TEXT("Projectile_")+FString::FromInt(ProjectileIndex),Output);bSegmentRecording=false;
			if(Projectile.IsValid())Projectile->Destroy();Projectile.Reset();++ProjectileIndex;Phase=7;return false;
		}
		return false;
	}
	bool Finish() { Cleanup();return true; }
	void Cleanup()
	{
		if(bCleaned)return;bCleaned=true;
		if(Projectile.IsValid())Projectile->Destroy();
		if(Player.IsValid())
		{
			if(bRecording && Master.IsValid()) Master->StopRecordingOutput(Player->GetWorld(),EAudioRecordingExportType::WavFile,TEXT("ActualGameplayAudio"),Output);
			if(bSegmentRecording && Submix.IsValid())Submix->StopRecordingOutput(Player->GetWorld(),EAudioRecordingExportType::WavFile,TEXT("InterruptedFixture"),Output);
			if(APlayerController* Controller=Player->GetWorld()->GetFirstPlayerController())Controller->ClearAudioListenerOverride();
			Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);Player->SetActorLocation(SavedLocation);
			if(Player->GetMesh()->GetAnimInstance())Player->GetMesh()->GetAnimInstance()->Montage_Stop(0.f);
		}
		for(const auto& M:Monsters) if(M.IsValid()) if(auto* AI=Cast<AAIController>(M->GetController())) if(AI->BrainComponent) AI->BrainComponent->ResumeLogic(TEXT("Owned audio fixture done"));
		FApp::SetUnfocusedVolumeMultiplier(SavedFocus);
		GetMutableDefault<ULevelEditorMiscSettings>()->bAllowBackgroundAudio=SavedBackgroundAudio;
	}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZCharacter> Owner;TArray<TWeakObjectPtr<AKZMonster>> Monsters;
	TArray<TSharedPtr<FJsonValue>> Samples;TWeakObjectPtr<USoundSubmix> Submix,Master;TWeakObjectPtr<UAnimMontage> Montage;TWeakObjectPtr<UKZAnimNotifyState_PlayAudio> LoopNotify;
	FString Output;TSet<FString> Seen;FVector SavedLocation=FVector::ZeroVector;double Deadline;float Start=0,ClipSeconds=0,CancelTime=0,LoopStart=0,SavedFocus=0;
	TWeakObjectPtr<AKZMonsterSkillObject> Projectile;TWeakObjectPtr<UAudioComponent> Flight;int32 ProjectileIndex=0;
	int32 Phase=0,Index=0,BaselineComponents=0;bool bCancel=false,bCancelDone=false,bRecording=false,bSegmentRecording=false,bCleaned=false,SavedBackgroundAudio=false;
};
class FWait : public IAutomationLatentCommand
{
public:
	FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+45.) {}
	bool Update() override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts()) if(C.WorldType==EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It) if(It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance())
			{ FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true; }
		if(FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Audio test waiting for owned PIE"));return true; }return false;
	}
	FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGameplayAudioPIE,"Khazan.Audio.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZGameplayAudioPIE::RunTest(const FString&) { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZAudioQA::FWait>(this));return true; }
#endif
