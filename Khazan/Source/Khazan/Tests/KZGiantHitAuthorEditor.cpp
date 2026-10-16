#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/Skeleton.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_Slot.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphSchema.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
namespace KZGiantHitAuthor
{
const FName SlotName(TEXT("KZHitReaction")), GroupName(TEXT("KZHitReactionGroup"));
bool Save(UObject* Object)
{
 Object->MarkPackageDirty(); UPackage* Package=Object->GetOutermost();
 FSavePackageArgs Args; Args.TopLevelFlags=RF_Public|RF_Standalone; Args.Error=GWarn;
 return UPackage::SavePackage(Package,Object,*FPackageName::LongPackageNameToFilename(Package->GetName(),FPackageName::GetAssetPackageExtension()),Args);
}
template<class T>T* Clone(T* Original,const FString& Destination)
{
 if (LoadObject<T>(nullptr,*Destination,nullptr,LOAD_NoWarn)) return nullptr;
 T* Copy=Cast<T>(StaticDuplicateObject(Original,CreatePackage(*Destination),*FPackageName::GetLongPackageAssetName(Destination)));
 if(Copy){Copy->SetFlags(RF_Public|RF_Standalone);FAssetRegistryModule::AssetCreated(Copy);} return Copy;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantHitAuthor,"Khazan.GiantHit.Author",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZGiantHitAuthor::RunTest(const FString&)
{
 using namespace KZGiantHitAuthor;
 if(!TestTrue(TEXT("Writes only isolated task project"),FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_GiantHitOverlayWork_20261013/Khazan"))))return false;
 const FString Families[]={TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
 const FString Art[]={TEXT("Shared/Elites/ApesStoneHandElite"),TEXT("HeinMach/Bosses/Yetuga")};
 const FString Directions[]={TEXT("L"),TEXT("R"),TEXT("D"),TEXT("U")};
 TArray<TSharedPtr<FJsonValue>> Rows;
 for(int32 Family=0;Family<2;++Family)
 {
  const FString Base=TEXT("/Game/Monsters/")+Families[Family];
  UAnimBlueprint* BP=LoadObject<UAnimBlueprint>(nullptr,*(Base+TEXT("/Animations/ABP_")+Families[Family]));
  UKZCharacterDefinitionData* Definition=LoadObject<UKZCharacterDefinitionData>(nullptr,*(Base+TEXT("/Data/DA_Character_")+Families[Family]));
  if(!TestTrue(TEXT("Current giant ABP and Definition"),BP&&BP->TargetSkeleton&&Definition))return false;
  USkeleton* Skeleton=BP->TargetSkeleton;
  Skeleton->Modify(); Skeleton->RegisterSlotNode(SlotName); Skeleton->SetSlotGroupName(SlotName,GroupName);
  UEdGraph* Graph=nullptr;TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs);
  for(UEdGraph* G:Graphs)if(G->GetFName()==TEXT("AnimGraph"))Graph=G;
  if(!TestNotNull(TEXT("Current AnimGraph"),Graph))return false;
  UAnimGraphNode_Root* Root=nullptr;UAnimGraphNode_Slot* HitSlot=nullptr;
  for(UEdGraphNode* N:Graph->Nodes)
  {
   if(auto* R=Cast<UAnimGraphNode_Root>(N))Root=R;
   if(auto* S=Cast<UAnimGraphNode_Slot>(N);S&&S->Node.SlotName==SlotName)HitSlot=S;
  }
  if(!TestTrue(TEXT("Additive slot is a new small graph extension"),Root&&!HitSlot))return false;
  UEdGraphPin* Result=Root->FindPin(TEXT("Result"));
  if(!TestTrue(TEXT("Preserve existing graph upstream of output"),Result&&Result->LinkedTo.Num()==1))return false;
  UEdGraphPin* Upstream=Result->LinkedTo[0];
  HitSlot=NewObject<UAnimGraphNode_Slot>(Graph);Graph->AddNode(HitSlot,false,false);HitSlot->CreateNewGuid();HitSlot->PostPlacedNewNode();
  HitSlot->Node.SlotName=SlotName;HitSlot->Node.bAlwaysUpdateSourcePose=true;HitSlot->AllocateDefaultPins();
  HitSlot->NodePosX=Root->NodePosX-200;HitSlot->NodePosY=Root->NodePosY;
  Result->BreakAllPinLinks();
  if(!TestTrue(TEXT("Independent additive slot follows existing action pose"),
   Graph->GetSchema()->TryCreateConnection(Upstream,HitSlot->FindPin(TEXT("Source")))&&Graph->GetSchema()->TryCreateConnection(HitSlot->FindPin(TEXT("Pose")),Result)))return false;
  FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);
  if(!TestTrue(TEXT("Both original pose graph and additive graph compile"),BP->GeneratedClass&&BP->Status!=BS_Error))return false;
  FKZHitReactionSettings& Settings=const_cast<FKZHitReactionSettings&>(Definition->GetHitReactionSettings());
  if(!TestTrue(TEXT("No prior additive settings overwritten"),Settings.AdditiveHits.IsEmpty()))return false;
  for(const FString& Direction:Directions)
  {
   const FString ClipName=TEXT("Damage_Normal_")+Direction+TEXT("_F");
   UAnimSequence* Original=LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/_Art/Enemies/")+Art[Family]+TEXT("/Animations/Damage/")+ClipName));
   UAnimMontage* Template=LoadObject<UAnimMontage>(nullptr,*(Base+TEXT("/Animations/Reaction/Montages/AM_")+Families[Family]+TEXT("_Hit_")+ClipName));
   if(!TestTrue(TEXT("Exact current original normal hit and authored template"),Original&&Template&&Original->GetSkeleton()==Skeleton))return false;
   const FString Destination=Base+TEXT("/Animations/Reaction/Additive/A_")+Families[Family]+TEXT("_HitAdditive_")+Direction;
   UAnimSequence* Clip=Clone(Original,Destination);
   UAnimMontage* Montage=Clone(Template,Base+TEXT("/Animations/Reaction/Additive/AM_")+Families[Family]+TEXT("_HitAdditive_")+Direction);
   if(!TestTrue(TEXT("New game-facing copies, originals untouched"),Clip&&Montage))return false;
   Clip->AdditiveAnimType=AAT_LocalSpaceBase;Clip->RefPoseType=ABPT_LocalAnimFrame;Clip->RefFrameIndex=0;Clip->RefPoseSeq=nullptr;
   Clip->bEnableRootMotion=false;Clip->bForceRootLock=true;Clip->RootMotionRootLock=ERootMotionRootLock::AnimFirstFrame;
   Clip->Notifies.Reset();Clip->PostEditChange();Clip->CacheDerivedDataForCurrentPlatform();
   Montage->Notifies.Reset();Montage->SlotAnimTracks.SetNum(1);auto& Track=Montage->SlotAnimTracks[0];Track.SlotName=SlotName;Track.AnimTrack.AnimSegments.SetNum(1);
   auto& Segment=Track.AnimTrack.AnimSegments[0];Segment.SetAnimReference(Clip);Segment.StartPos=0.f;Segment.AnimStartTime=0.f;Segment.AnimEndTime=Clip->GetPlayLength();Segment.AnimPlayRate=1.f;Segment.LoopingCount=1;
   // Original AB_ApesStoneHand_E / AB_Yetuga CDO xxAnimGraphNode_AdditiveBlend.BlendTime=[.1,.1], Linear.
   // Adapter maps the custom node's enter/exit transition time onto engine montage blending.
   Montage->BlendIn.SetBlendTime(.1f);Montage->BlendOut.SetBlendTime(.1f);Montage->BlendIn.SetBlendOption(EAlphaBlendOption::Linear);Montage->BlendOut.SetBlendOption(EAlphaBlendOption::Linear);
   Montage->bEnableRootMotionTranslation=false;Montage->bEnableRootMotionRotation=false;Montage->PostEditChange();
   if(!TestTrue(TEXT("Additive no-root-motion overlay in its own group"),Montage->IsValidAdditive()&&!Montage->HasRootMotion()&&Montage->GetGroupName()==GroupName))return false;
   if(!TestTrue(TEXT("Frame count/rate/length are preserved"),Clip->GetDataModel()->GetNumberOfFrames()==Original->GetDataModel()->GetNumberOfFrames()&&Clip->GetDataModel()->GetFrameRate()==Original->GetDataModel()->GetFrameRate()&&Clip->GetPlayLength()==Original->GetPlayLength()&&Clip->RateScale==Original->RateScale))return false;
   Settings.AdditiveHits.Add(Montage);
   if(!TestTrue(TEXT("Save additive clip/montage"),Save(Clip)&&Save(Montage)))return false;
   auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Families[Family]);Row->SetStringField(TEXT("source"),Original->GetPathName());Row->SetStringField(TEXT("clip"),Clip->GetPathName());Row->SetStringField(TEXT("montage"),Montage->GetPathName());
   Row->SetNumberField(TEXT("length"),Clip->GetPlayLength());Row->SetNumberField(TEXT("frames"),Clip->GetDataModel()->GetNumberOfFrames());Row->SetStringField(TEXT("fps"),Clip->GetDataModel()->GetFrameRate().ToPrettyText().ToString());
   Row->SetNumberField(TEXT("blend_in"),Montage->BlendIn.GetBlendTime());Row->SetNumberField(TEXT("blend_out"),Montage->BlendOut.GetBlendTime());
   Row->SetStringField(TEXT("additive_provenance"),TEXT("Project presentation adapter: local delta relative to own imported first frame; raw original has no explicit additive fields. Not original native blend graph proof."));Rows.Add(MakeShared<FJsonValueObject>(Row));
  }
  if(!TestTrue(TEXT("Save exactly target skeleton, graph and pool"),Save(Skeleton)&&Save(BP)&&Save(Definition)))return false;
 }
 auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("clips"),Rows);Report->SetStringField(TEXT("graph"),TEXT("Existing pose chain -> KZHitReaction slot (independent group, automatic local additive accumulation) -> output"));
 FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
 const FString Out=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_OUT"));
 return TestTrue(TEXT("Write authoring provenance"),FFileHelper::SaveStringToFile(Text,*(Out/TEXT("Authoring.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM));
}
#endif