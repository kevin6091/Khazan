// Work-only montage authoring; not delivered to the product Source or Build.cs.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterCombatPolicyAuthor, "Khazan.Monster.CombatPolicyAuthor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterCombatPolicyAuthor::RunTest(const FString&)
{
	UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, TEXT("/Game/Monsters/HalberdElite/Animations/AM_Idle_Basic"));
	if (!TestNotNull(TEXT("Existing Basic montage"), Montage) || !TestEqual(TEXT("Existing Loop/End sections"), Montage->CompositeSections.Num(), 2)) return false;
	FAnimTrack& Track = Montage->SlotAnimTracks[0].AnimTrack;
	if (!TestEqual(TEXT("Existing Loop/End segments"), Track.AnimSegments.Num(), 2)) return false;
	float Position = 0.f;
	for (int32 Index = 0; Index < 2; ++Index)
	{
		const FString Phase = Index == 0 ? TEXT("Loop") : TEXT("End");
		const FString Path = TEXT("/Game/Monsters/HalberdElite/Animations/InGame/A_EN_PLAY_AC_EmpireHalberd_Basic_") + Phase + TEXT("_02");
		UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *Path);
		if (!TestNotNull(TEXT("Exact Basic02 gameplay clip"), Clip)) return false;
		FAnimSegment& Segment = Track.AnimSegments[Index];
		Segment.SetAnimReference(Clip); Segment.StartPos = Position; Segment.AnimStartTime = 0.f; Segment.AnimEndTime = Clip->GetPlayLength();
		Montage->CompositeSections[Index].Link(Montage, Position);
		Position += Segment.GetLength();
	}
	const FFrameRate FrameRate = Montage->GetDataModel()->GetFrameRate();
	Montage->GetController().SetNumberOfFrames(FrameRate.AsFrameTime(Position).RoundToFrame(), false);
	Montage->SetCompositeLength(Position); Montage->RefreshCacheData(); Montage->MarkPackageDirty();
	FSavePackageArgs Args; Args.TopLevelFlags = RF_Public | RF_Standalone;
	return TestTrue(TEXT("Save only existing Halberd Basic montage"), UPackage::SavePackage(Montage->GetPackage(), Montage, *FPackageName::LongPackageNameToFilename(Montage->GetPackage()->GetName(), FPackageName::GetAssetPackageExtension()), Args));
}
#endif
