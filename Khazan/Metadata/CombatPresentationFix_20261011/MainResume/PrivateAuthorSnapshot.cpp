// Narrow private editor authoring; never included in Main runtime modules.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/Color/ParticleModuleColorOverLife.h"
#include "Particles/ParticleModuleRequired.h"
#include "Distributions/DistributionVectorConstant.h"
#include "Distributions/DistributionVectorConstantCurve.h"
#include "Distributions/DistributionVectorUniform.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatPresentationFallAuthor,"Khazan.CombatPresentation.AuthorFall",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZCombatPresentationFallAuthor::RunTest(const FString&)
{
 using namespace KZGiantFallAuthor;
 if(!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_GiantFallWork_20261011"))){AddError(TEXT("Private author root required"));return false;}
 FString Text;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()+TEXT("Metadata/CombatPresentationFix_20261011/FallPlan.json")));
 TSharedPtr<FJsonObject> Plan;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan)||!Plan)return false;
 const FString Folder=TEXT("/Game/_Art/Player/Animation/InGame/DAS/FallAttack/");
 UAnimMontage* M=LoadObject<UAnimMontage>(nullptr,*(Folder+TEXT("AM_DAS_FallAttack")));
 UAnimSequence* Clip=LoadObject<UAnimSequence>(nullptr,*(Folder+TEXT("CA_P_Kazan_DualAxeSword_Com_FallAtk")));
 UKZComboDefinitionData* Definition=LoadObject<UKZComboDefinitionData>(nullptr,*(Folder+TEXT("DA_DAS_FallAttack")));
 if(!M||!Clip||!Definition)return false;
 TestTrue(TEXT("Saved playback plan identifies the existing baked sequence"),FMath::IsNearlyEqual(Clip->GetPlayLength(),Number(Plan,TEXT("land_end")),.001f));
 const float BlendIn=M->BlendIn.GetBlendTime(),BlendOut=M->BlendOut.GetBlendTime();
 M->CompositeSections.Reset();M->Notifies.Reset();FSlotAnimationTrack Track;Track.SlotName=TEXT("DefaultSlot");float Position=0;
 Segment(M,Track,Clip,TEXT("Start"),0,Number(Plan,TEXT("start_end")),1,Position);
 Notify(M,Position-1.f/60.f,TEXT("FallLoop"));
 Segment(M,Track,Clip,TEXT("Loop"),Number(Plan,TEXT("start_end")),Number(Plan,TEXT("loop_end")),1,Position);
 const float LandStart=Position;
 Segment(M,Track,Clip,TEXT("Land"),Number(Plan,TEXT("loop_end")),Clip->GetPlayLength(),1,Position);
 Notify(M,LandStart+Number(Plan,TEXT("input_end_local")),TEXT("InputEnd"));
 M->CompositeSections[0].NextSectionName=TEXT("Loop");M->CompositeSections[1].NextSectionName=TEXT("Loop");
 Finalize(M,Track,Position,BlendIn);M->BlendOut.SetBlendTime(BlendOut);
 M->GetController().SetFrameRate(FFrameRate(60,1),false);M->GetController().SetNumberOfFrames(FFrameNumber(FMath::RoundToInt(Position*60.f)),false);M->PostEditChange();
 auto& Nodes=Value<TArray<FKZComboNode>>(Definition,TEXT("Nodes"));
 for(FKZComboNode& Node:Nodes)if(Node.NodeId==TEXT("Land"))for(FKZAttackCollisionWindow& W:Node.AttackWindows)
 {
  const float OldEnd=W.EndTime;W.EndTime=Number(Plan,TEXT("attack_end_local"));
  for(auto& Key:W.Keys)if(OldEnd>0)Key.Time*=W.EndTime/OldEnd;
  W.Source+=TEXT("; 2026-10-11 original End local time mapped to existing baked sequence; playback conversion applied once");
 }
 if(!Save(M)||!Save(Definition))return false;
 auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("passed"),!HasAnyErrors());Result->SetNumberField(TEXT("land_start"),LandStart);Result->SetNumberField(TEXT("montage_end"),Position);Result->SetNumberField(TEXT("sequence_end"),Clip->GetPlayLength());
 Result->SetStringField(TEXT("source_sequence"),Clip->GetPathName());Result->SetStringField(TEXT("policy"),TEXT("Existing baked timeline; unchanged raw animation, Player .01, damage/cost and blend settings."));
 FString Out;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Out));FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectDir()+TEXT("Metadata/CombatPresentationFix_20261011/FallAuthored.json")));return !HasAnyErrors();
}

namespace KZCombatPresentationArt
{
// Assistant temporary expression tuning requested by the user; these are not
// serialized original-game density/tint values. Engine properties remain editable.
const FVector DASTint(1.,.12,.08);
void Tint(FRawDistributionVector& Raw)
{
 if(auto* Constant=Cast<UDistributionVectorConstant>(Raw.Distribution))Constant->Constant*=DASTint;
 else if(auto* Curve=Cast<UDistributionVectorConstantCurve>(Raw.Distribution))for(auto& P:Curve->ConstantCurve.Points){P.OutVal*=DASTint;P.ArriveTangent*=DASTint;P.LeaveTangent*=DASTint;}
 else if(auto* Uniform=Cast<UDistributionVectorUniform>(Raw.Distribution)){Uniform->Min*=DASTint;Uniform->Max*=DASTint;}
 else return;
 Raw.Distribution->bIsDirty=true;Raw.Initialize();
}
void DoubleSpriteDensity(UParticleSystem* PS)
{
 for(UParticleEmitter* E:PS->Emitters)for(UParticleLODLevel* L:E->LODLevels)
  if(L && !L->TypeDataModule && L->SpawnModule)
  {
   for(auto& B:L->SpawnModule->BurstList){B.Count*=2;if(B.CountLow>0)B.CountLow*=2;}
   auto& Rate=L->SpawnModule->Rate;
   if(auto* D=Cast<UDistributionFloatConstant>(Rate.Distribution)){D->Constant*=2;D->bIsDirty=true;Rate.Initialize();}
  }
 PS->PostEditChange();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZCombatPresentationVFXAuthor,"Khazan.CombatPresentation.AuthorVFX",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZCombatPresentationVFXAuthor::RunTest(const FString&)
{
 using namespace KZMonsterAuthor;
 if(!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_GiantFallWork_20261011"))){AddError(TEXT("Private author root required"));return false;}
 TArray<FString> Changed;
 const FString Blood=TEXT("/Game/_Art/Effects/Combat/Blood/");
 UParticleSystem* Spray=LoadObject<UParticleSystem>(nullptr,*(Blood+TEXT("PP_Dmg_Blood_Trail_Sub")));
 UParticleEmitter* Physical=nullptr;
 if(Spray)for(UParticleEmitter* E:Spray->Emitters)if(E && !E->LODLevels.IsEmpty())
 {
  UParticleLODLevel* L=E->LODLevels[0];
  if(L && !L->TypeDataModule && L->RequiredModule && L->RequiredModule->Material &&
   L->RequiredModule->Material->GetPathName().Contains(TEXT("Base_DefaltParticle_Masked"))) {Physical=E;break;}
 }
 if(!Physical){AddError(TEXT("Source blood physical sprite emitter required"));return false;}
 // Reuse the original physical blood sprite, its red/black color, velocities,
 // gravity/collision and source lifetime. Do not copy its mesh-decal receiver.
 for(const TCHAR* Name:{TEXT("FP_Dmg_Blood_Base"),TEXT("FP_Dmg_Blood_Base_BK"),TEXT("FP_BloodSplit_01"),TEXT("FP_BloodSplit_02")})
 {
  UParticleSystem* Target=LoadObject<UParticleSystem>(nullptr,*(Blood+Name));if(!Target)return false;
  if(Target->Emitters.ContainsByPredicate([](const UParticleEmitter* E){return E->EmitterName==TEXT("KZ_PhysicalBloodSpray");})){AddError(TEXT("Already authored; do not multiply density again"));return false;}
  // Cascade keeps spawn/distribution modules as siblings of its emitters. A
  // whole-system engine duplicate remaps those owned objects; duplicating the
  // emitter alone leaves illegal private references to the source package.
  auto* OwnedTemplate=DuplicateObject<UParticleSystem>(Spray,Target,MakeUniqueObjectName(Target,Spray->GetClass(),TEXT("KZ_PhysicalBloodTemplate")));
  OwnedTemplate->ClearFlags(RF_Public|RF_Standalone);
  UParticleEmitter* Copy=OwnedTemplate->Emitters[Spray->Emitters.IndexOfByKey(Physical)];
  OwnedTemplate->Emitters.Reset();OwnedTemplate->Emitters.Add(Copy);
  Copy->EmitterName=TEXT("KZ_PhysicalBloodSpray");Target->Emitters.Add(Copy);Target->PostEditChange();if(!Save(Target))return false;Changed.Add(Target->GetPathName());
 }
 const FString ClonePath=TEXT("/Game/_Art/Effects/DualAxeSword/Core/FP_DAS_PlaneSlash_Enhanced");
 if(LoadObject<UParticleSystem>(nullptr,*ClonePath)){AddError(TEXT("DAS variant already exists; inspect prior author receipt"));return false;}
 UParticleSystem* Source=LoadObject<UParticleSystem>(nullptr,TEXT("/Game/_Art/Effects/Combat/Shared/FP_PlaneSlash_Base_001"));if(!Source)return false;
 UParticleSystem* DAS=DuplicateObject<UParticleSystem>(Source,CreatePackage(*ClonePath),TEXT("FP_DAS_PlaneSlash_Enhanced"));DAS->SetFlags(RF_Public|RF_Standalone);FAssetRegistryModule::AssetCreated(DAS);
 for(UParticleEmitter* E:DAS->Emitters)for(UParticleLODLevel* L:E->LODLevels)for(UParticleModule* Mod:L->Modules)if(auto* C=Cast<UParticleModuleColorOverLife>(Mod))KZCombatPresentationArt::Tint(C->ColorOverLife);
 KZCombatPresentationArt::DoubleSpriteDensity(DAS);if(!Save(DAS))return false;Changed.Add(DAS->GetPathName());
 for(const TCHAR* Name:{TEXT("FP_Kazan_Dualaxesword_flow_burst_01"),TEXT("FP_PlaneSlash_Flow_Strong"),TEXT("FP_Kazan_Dualaxesword_flow_charge_01"),TEXT("FP_Kazan_SpinningBeast_Axe_Slash_01"),TEXT("FP_Kazan_DualaxeSword_Overfury_slash_01"),TEXT("FP_Kazan_DualaxeSword_Fatalblood_slash_01")})
 {
  UParticleSystem* PS=LoadObject<UParticleSystem>(nullptr,*(FString(TEXT("/Game/_Art/Effects/DualAxeSword/Core/"))+Name));if(!PS)return false;
  KZCombatPresentationArt::DoubleSpriteDensity(PS);if(!Save(PS))return false;Changed.Add(PS->GetPathName());
 }
 // Resolve the existing eight actual montage paths from the saved source plan;
 // no new windows or guessed input/hit events are introduced.
 FString PlanText;FFileHelper::LoadFileToString(PlanText,TEXT("C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPreparedPlaybackPlan.json"));
 TSharedPtr<FJsonObject> Plan;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PlanText),Plan))return false;
 TSet<FString> Paths;for(auto& V:Plan->GetArrayField(TEXT("events")))Paths.Add(V->AsObject()->GetStringField(TEXT("montage")));
 int32 Rebound=0;
 for(const auto& Path:Paths)
 {
  UAnimMontage* M=LoadObject<UAnimMontage>(nullptr,*Path);if(!M)return false;int32 Count=0;
  for(auto& Event:M->Notifies)if(auto* Parent=Cast<UKZAnimNotify_CombatEffect>(Event.Notify.Get()))
  {
   auto Replace=[&](UKZAnimNotify_CombatEffect* N){if(N && N->ParticleTemplate==Source){N->ParticleTemplate=DAS;++Count;}};
   Replace(Parent);for(auto& N:Parent->BatchedEffects)Replace(N.Get());
  }
  if(Count){if(!Save(M))return false;Changed.Add(M->GetPathName());Rebound+=Count;}
 }
 auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),!HasAnyErrors());Report->SetNumberField(TEXT("rebound_DAS_events"),Rebound);Report->SetStringField(TEXT("origin"),TEXT("Original source emission/pose/lifetime retained; assistant temporary density/tint and reused physical spray layer, not original pixel parity."));
 TArray<TSharedPtr<FJsonValue>> Rows;for(auto& S:Changed)Rows.Add(MakeShared<FJsonValueString>(S));Report->SetArrayField(TEXT("changed_assets"),Rows);
 FString Out;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Out));FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectDir()+TEXT("Metadata/CombatPresentationFix_20261011/VFXAuthored.json")));return !HasAnyErrors();
}
#endif
