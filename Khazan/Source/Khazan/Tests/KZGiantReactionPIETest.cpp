#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "EngineUtils.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "AI/KZMonsterAIController.h"
#include "Components/StateTreeAIComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZGameplayTags.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Camera/CameraActor.h"
#include "GameFramework/PlayerController.h"
#include "UnrealClient.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "HAL/PlatformMisc.h"

namespace KZGiantReactionQA
{
class FRun final : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* InTest, AKZPlayer* InPlayer)
		: Test(InTest), Player(InPlayer), Deadline(FPlatformTime::Seconds() + 180.)
	{
		APlayerController* PC = InPlayer->GetController<APlayerController>();
		SavedViewTarget = PC ? PC->GetViewTarget() : nullptr;
		Camera = InPlayer->GetWorld()->SpawnActor<ACameraActor>();
		if (PC && Camera.IsValid()) PC->SetViewTarget(Camera.Get());
		Floor = InPlayer->GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0, 0, 10000), FRotator::ZeroRotator);
		Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
		Floor->SetActorScale3D(FVector(40, 40, .2));
		Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	}
	~FRun() { Cleanup(); }
	bool Update() override
	{
		if (!Player.IsValid() || FPlatformTime::Seconds() > Deadline)
		{
			Test->AddError(TEXT("GiantReaction PIE watchdog")); Cleanup(); return true;
		}
		if (Family == 2) { Save(); Cleanup(); return true; }
		UWorld* World = Player->GetWorld();
		if (Stage == 0)
		{
			const FString Name = Family == 0 ? TEXT("ApesStoneHandElite") : TEXT("Yetuga");
			UClass* Class = LoadClass<AKZMonster>(nullptr,
				*(TEXT("/Game/Bluprints/Monsters/BP_Monster_") + Name + TEXT(".BP_Monster_") + Name + TEXT("_C")));
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Target = World->SpawnActor<AKZMonster>(Class, FVector(0, 0, 10300), FRotator::ZeroRotator, Params);
			if (!Test->TestNotNull(TEXT("Real monster spawned"), Target.Get())) { Cleanup(); return true; }
			Target->SpawnDefaultController();
			if (auto* AI = Cast<AKZMonsterAIController>(Target->GetController()))
				AI->GetStateTreeComponent()->StopLogic(TEXT("Owned part-break QA"));
			Target->GetAbilitySystemComponent()->CancelAllAbilities();
			Target->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
			FVector Ground = Target->GetActorLocation();
			Ground.Z = 10010.f + Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + UCharacterMovementComponent::MIN_FLOOR_DIST;
			Target->SetActorLocation(Ground);
			Target->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
			Camera->SetActorLocation(Ground + FVector(850, -750, 280));
			Camera->SetActorRotation((Ground + FVector(0, 0, 170) - Camera->GetActorLocation()).Rotation());
			Stage = 1; Start = World->GetTimeSeconds(); return false;
		}
		UAbilitySystemComponent* ASC = Target->GetAbilitySystemComponent();
		const FKZMonsterStaminaSettings& Settings = Target->GetCharacterDefinition()->GetMonsterStaminaSettings();
		if (Stage == 1)
		{
			if (World->GetTimeSeconds() - Start < .2f) return false;
			ASC->CancelAllAbilities();
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()));
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));
			TInlineComponentArray<UBoxComponent*> Boxes(Target.Get());
			for (UBoxComponent* Box : Boxes) if (Target->IsPartGroup1WeakBox(Box)) WeakBoxes.Add(Box);
			Test->TestEqual(TEXT("Exact Group1 source weak-box count"), WeakBoxes.Num(), Family == 0 ? 2 : 3);
			Test->TestEqual(TEXT("Original Group1 raw durability"), Settings.PartGroup1Durability, Family == 0 ? 1.f : 350.f);
			Test->TestEqual(TEXT("Explicit temporary attack conversion"), Settings.PartGroup1DamageScale, 20.f);
			Test->TestEqual(TEXT("Explicit temporary weak-box base half extent (cm)"), Settings.PartGroup1BaseHalfExtentCm, 32.f);
			Test->TestNotNull(TEXT("PartGroggy montage"), Settings.PartGroup1GroggyMontage.Get());
			for (UBoxComponent* Box : WeakBoxes)
			{
				Test->TestTrue(TEXT("Attached to authored source bone"), Box->GetAttachSocketName() != NAME_None &&
					Target->GetMesh()->GetBoneIndex(Box->GetAttachSocketName()) != INDEX_NONE);
				TArray<FOverlapResult> Hits;
				World->OverlapMultiByObjectType(Hits, Box->GetComponentLocation(), Box->GetComponentQuat(),
					FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeSphere(8.f));
				Test->TestTrue(TEXT("Player attack Pawn-object query can hit actual weak box"),
					Hits.ContainsByPredicate([Box](const FOverlapResult& Hit) { return Hit.GetComponent() == Box; }));
			}
			const bool First = Target->ReportPartGroup1Hit(10.f, Player.Get());
			PartRootStart = Target->GetActorLocation();
			MaxPartRootTravel = 0.f;
			const UAnimSequence* RootClip = Cast<UAnimSequence>(Settings.PartGroup1GroggyMontage->SlotAnimTracks[0].AnimTrack.AnimSegments[0].GetAnimReference());
			ExpectedPartRootTravel = RootClip ? RootClip->ExtractRootMotionFromRange(0.f, RootClip->GetPlayLength(), FAnimExtractContext(0., true)).GetTranslation().Size2D() : 0.f;
			Test->TestEqual(TEXT("Source threshold and temporary conversion gate first weak hit"), First, Family == 0);
			if (Family == 1)
			{
				Test->TestFalse(TEXT("Yetuga action remains before Group1 break"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
				Test->TestTrue(TEXT("Second accepted weak hit reaches original threshold"), Target->ReportPartGroup1Hit(10.f, Player.Get()));
			}
			Test->TestTrue(TEXT("Part break owns existing blocking HitReaction Ability"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
			Test->TestTrue(TEXT("Exact PartGroggy montage plays"), Target->GetMesh()->GetAnimInstance()->Montage_IsPlaying(Settings.PartGroup1GroggyMontage));
			Test->TestFalse(TEXT("MaxDestructionNum one prevents repeat"), Target->ReportPartGroup1Hit(10.f, Player.Get()));
			for (UBoxComponent* Box : WeakBoxes)
				Test->TestEqual(TEXT("Broken Group1 box stops query collision"), Box->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
			Start = World->GetTimeSeconds(); Stage = 2; return false;
		}
		if (Stage == 2)
		{
			MaxPartRootTravel = FMath::Max(MaxPartRootTravel, float(FVector::Dist2D(PartRootStart, Target->GetActorLocation())));
			const float CaptureTimes[] = {.25f, .7f, 1.35f, 1.8f};
			if (CaptureIndex < UE_ARRAY_COUNT(CaptureTimes) &&
				World->GetTimeSeconds() - Start >= CaptureTimes[CaptureIndex])
			{
				const FString Out = FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_OUT"));
				FScreenshotRequest::RequestScreenshot(Out / FString::Printf(TEXT("PartGroggy_%d_%d.png"), Family, CaptureIndex++), false, false);
			}
			if (World->GetTimeSeconds() - Start < Settings.PartGroup1GroggyMontage->GetPlayLength() + .5f) return false;
			Test->TestFalse(TEXT("Part reaction releases HitReacting at montage end"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
			Test->TestTrue(TEXT("Part-break extracted root travel actually moves the capsule"), ExpectedPartRootTravel > UE_SMALL_NUMBER && MaxPartRootTravel > ExpectedPartRootTravel * .5f);
			auto Row = MakeShared<FJsonObject>();
			Row->SetStringField(TEXT("family"), Family == 0 ? TEXT("ApesStoneHandElite") : TEXT("Yetuga"));
			Row->SetNumberField(TEXT("weak_box_count"), WeakBoxes.Num());
			Row->SetNumberField(TEXT("montage_seconds"), Settings.PartGroup1GroggyMontage->GetPlayLength());
			Row->SetNumberField(TEXT("part_root_extraction_cm"), ExpectedPartRootTravel);
			Row->SetNumberField(TEXT("part_capsule_travel_cm"), MaxPartRootTravel);
			Rows.Add(MakeShared<FJsonValueObject>(Row));
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), 0.f);
			Start = World->GetTimeSeconds(); GroggySamples = 0; SawGroggyStart = SawGroggyLoop = false; Stage = 3; return false;
		}
		if (Stage == 3)
		{
			if (World->GetTimeSeconds() - Start < .15f) return false;
			UAnimInstance* Anim = Target->GetMesh()->GetAnimInstance();
			UKZExhaustionAbility* Exhaustion = Target->GetActiveExhaustionAbility();
			const FName Section = Anim->Montage_GetCurrentSection(Settings.ExhaustionMontage);
			SawGroggyStart |= Section == TEXT("Start");
			SawGroggyLoop |= Section == TEXT("Loop");
			if (World->GetTimeSeconds() - Start < Settings.ExhaustionSeconds - .1f)
			{
				++GroggySamples;
				Test->TestTrue(TEXT("Stamina-zero groggy never falls back to locomotion between loops"), Exhaustion && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) && Anim->Montage_IsPlaying(Settings.ExhaustionMontage) && (Section == TEXT("Start") || Section == TEXT("Loop")));
				return false;
			}
			Test->TestTrue(TEXT("Real source groggy falling Start and continuous Loop both evaluated"), SawGroggyStart && SawGroggyLoop && GroggySamples > 1);
			Rows.Last()->AsObject()->SetNumberField(TEXT("groggy_continuous_samples"), GroggySamples);
			Stage = 4; return false;
		}
		if (Stage == 4)
		{
			if (World->GetTimeSeconds() - Start < Settings.ExhaustionSeconds + Settings.ExhaustionMontage->GetPlayLength()) return false;
			Test->TestFalse(TEXT("Groggy End restores control without an indefinite loop"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
			Target->Destroy(); Target.Reset(); WeakBoxes.Reset(); ++Family; Stage = 0; CaptureIndex = 0; return false;
		}
		return false;
	}
private:
	void Save()
	{
		auto Report = MakeShared<FJsonObject>(); Report->SetArrayField(TEXT("cases"), Rows);
		FString Text; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
		const FString Out = FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_PHYSICS_OUT"));
		FFileHelper::SaveStringToFile(Text, *(Out / TEXT("PIE.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}
	void Cleanup()
	{
		if (Target.IsValid()) Target->Destroy();
		if (Floor.IsValid()) Floor->Destroy();
		if (Player.IsValid())
			if (APlayerController* PC = Player->GetController<APlayerController>())
				PC->SetViewTarget(SavedViewTarget.IsValid() ? SavedViewTarget.Get() : Player.Get());
		if (Camera.IsValid()) Camera->Destroy();
	}
	FAutomationTestBase* Test;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<AKZMonster> Target;
	TWeakObjectPtr<AStaticMeshActor> Floor;
	TWeakObjectPtr<ACameraActor> Camera;
	TWeakObjectPtr<AActor> SavedViewTarget;
	TArray<UBoxComponent*> WeakBoxes;
	TArray<TSharedPtr<FJsonValue>> Rows;
	double Deadline;
	int32 Family = 0, Stage = 0;
	float Start = 0.f;
	int32 CaptureIndex = 0;
	FVector PartRootStart = FVector::ZeroVector;
	float MaxPartRootTravel = 0.f, ExpectedPartRootTravel = 0.f;
	int32 GroggySamples = 0;
	bool SawGroggyStart = false, SawGroggyLoop = false;
};
class FWait final : public IAutomationLatentCommand
{
public:
	FWait(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 90.) {}
	bool Update() override
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
			if (Context.WorldType == EWorldType::PIE && Context.World() && Context.World()->HasBegunPlay())
				for (TActorIterator<AKZPlayer> It(Context.World()); It; ++It)
					if (It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance())
					{
						FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test, *It));
						return true;
					}
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("No task-owned PIE world")); return true; }
		return false;
	}
private:
	FAutomationTestBase* Test;
	double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantReactionPIE, "Khazan.GiantReaction.PIE",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZGiantReactionPIE::RunTest(const FString&)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZGiantReactionQA::FWait>(this));
	return true;
}
#endif
