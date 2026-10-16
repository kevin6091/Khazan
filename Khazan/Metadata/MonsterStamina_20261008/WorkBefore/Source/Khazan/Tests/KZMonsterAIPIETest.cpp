#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "AI/KZMonsterAIController.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Attribute/KZAttributeSet.h"
#include "Components/StateTreeAIComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AnimNodeBase.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISense_Sight.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Navigation/PathFollowingComponent.h"
#include "KZGameplayTags.h"
#include "Engine/Engine.h"
#include "GameFramework/WorldSettings.h"
#include "EngineUtils.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimCurveTypes.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/UnrealType.h"
#include "HAL/FileManager.h"

namespace
{
class FMonsterPIECommand : public IAutomationLatentCommand
{
public:
	FMonsterPIECommand(FAutomationTestBase* InTest, AKZPlayer* InPlayer, const TArray<AKZMonster*>& InMonsters, bool bAttacksOnly = false)
		: Test(InTest), Player(InPlayer), SavedPlayerLocation(InPlayer->GetActorLocation()), SavedPlayerRotation(InPlayer->GetActorRotation()), Deadline(FPlatformTime::Seconds() + 900.0)
	{
		bSkipWalk = bAttacksOnly;
		for (AKZMonster* M : InMonsters)
		{
			Monsters.Add(M);
			if (auto* AI = Cast<AKZMonsterAIController>(M->GetController()))
			{
				auto* Perception = AI->GetPerceptionComponent();
				SavedSight.Add(Perception, Perception->IsSenseEnabled(UAISense_Sight::StaticClass()));
				// Other families must not discover the player during this family's QA placements.
				Perception->SetSenseEnabled(UAISense_Sight::StaticClass(), false);
			}
		}
		SavedHP = InPlayer->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
		SavedControlRotation = InPlayer->GetController()->GetControlRotation();
		FootTickHandle = FWorldDelegates::OnWorldPostActorTick.AddRaw(this, &FMonsterPIECommand::OnPostActorTick);
	}
	~FMonsterPIECommand()
	{
		RestoreSight();
		ReleaseWalkCamera();
		FWorldDelegates::OnWorldPostActorTick.Remove(FootTickHandle);
		if (Player.IsValid() && bDilationChanged) Player->GetWorld()->GetWorldSettings()->SetTimeDilation(SavedDilation);
		if (WalkConstraint.IsValid() && Monsters.IsValidIndex(MonsterIndex) && Monsters[MonsterIndex].IsValid()) Monsters[MonsterIndex]->GetLocomotionComponent()->ReleaseMovementConstraint(WalkConstraint);
	}
	virtual bool Update() override
	{
		if (!Player.IsValid() || FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Monster PIE timed out")); Cleanup(); return true; }
		const float Now = Player->GetWorld()->GetTimeSeconds();
		if (MonsterIndex >= Monsters.Num())
		{
			Test->TestEqual(TEXT("Enemy animation attacks never damage player HP"), Player->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()), SavedHP);
			Test->TestTrue(TEXT("Observed a real lateral standoff movement"), bAnyLateral);
			Cleanup(); return true;
		}
		AKZMonster* Monster = Monsters[MonsterIndex].Get();
		AKZMonsterAIController* AI = Monster ? Cast<AKZMonsterAIController>(Monster->GetController()) : nullptr;
		if (!Monster || !AI) { Test->AddError(TEXT("Missing possessed monster")); Cleanup(); return true; }
		UKZAbilitySystemComponent* ASC = CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		UAnimInstance* Anim = Monster->GetMesh()->GetAnimInstance();
		if (!Anim) { Test->AddError(TEXT("Monster mesh has no AnimInstance")); Cleanup(); return true; }
		if (Stage == 1 || Stage == 2)
		{
			const FString Debug = AI->GetStateTreeComponent()->GetDebugInfoString();
			bSawAlert |= Debug.Contains(TEXT("Alert")); bSawChase |= Debug.Contains(TEXT("Chase")); bSawAttack |= Debug.Contains(TEXT("Attack")); bSawStandoff |= Debug.Contains(TEXT("Standoff"));
			if (Stage == 2 && Debug.Contains(TEXT("Chase")))
			{
				if (!bRechaseStarted) { RechaseStart = Monster->GetActorLocation(); bRechaseStarted = true; }
				bRechaseAdvanced |= AI->GetMoveStatus() == EPathFollowingStatus::Moving && FVector::Dist2D(RechaseStart, Monster->GetActorLocation()) > 100.f;
			}
			const FVector LocalVelocity = Monster->GetActorRotation().UnrotateVector(Monster->GetVelocity());
			bAnyLateral |= Debug.Contains(TEXT("Standoff")) && FMath::Abs(LocalVelocity.Y) > 1.f;
			if (Now >= ObserveLogAt)
			{
				UE_LOG(LogTemp, Display, TEXT("MonsterObserve %s stage=%d distance=%.1f move=%d target=%s velocity=%s state=%s"),
					*Monster->GetName(), Stage, FVector::Dist2D(Monster->GetActorLocation(), Player->GetActorLocation()),
					static_cast<int32>(AI->GetMoveStatus()), *GetNameSafe(AI->GetBattleTarget()), *Monster->GetVelocity().ToString(),
					*Debug.Replace(TEXT("\n"), TEXT(" ")));
				ObserveLogAt = Now + 2.f;
			}
			if (UAnimMontage* Montage = Anim->GetCurrentActiveMontage())
			{
				const FString Section = Anim->Montage_GetCurrentSection(Montage).ToString();
				bSawAlert |= Montage->GetName().StartsWith(TEXT("Idle_")) && Section == TEXT("End");
				if (!SeenNaturalSections.Contains(Montage->GetName() + TEXT(":") + Section))
				{
					SeenNaturalSections.Add(Montage->GetName() + TEXT(":") + Section);
					Test->AddInfo(FString::Printf(TEXT("Natural AI %s state=%s montage=%s section=%s distance=%.2f"), *Monster->GetName(), *Debug.Replace(TEXT("\n"), TEXT(" ")), *Montage->GetName(), *Section, FVector::Dist2D(Monster->GetActorLocation(), Player->GetActorLocation())));
				}
			}
		}
		if (Stage == 9)
		{
			// The controller's target memory is deliberately inactive in this fixture.
			// Keep an explicit gameplay focus so Move focus cannot turn the pawn into every nav direction.
			AI->SetFocus(Player.Get());
		}
		// Wait for observed behaviour, with an upper bound; slow editor FPS cannot skip a phase.
		if (Stage == 1 && !(bSawAlert && bSawChase && bSawAttack && bSawStandoff) && Now < PatternDeadline) return false;
		if (Now < NextTime) return false;
		switch (Stage)
		{
		case 0:
		{
			Test->TestTrue(TEXT("StateTree is running"), AI->GetStateTreeComponent()->IsRunning());
			Test->TestNotNull(TEXT("Shared CharacterDefinition initialized"), Monster->GetCharacterDefinition());
			Test->TestEqual(TEXT("Initially unalerted outside sight"), AI->GetBattleTarget(), static_cast<AActor*>(nullptr));
			FNavLocation Point; UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Monster->GetWorld());
			Test->TestTrue(TEXT("Enemy spawn projects onto real DevMap navmesh"), Nav && Nav->ProjectPointToNavigation(Monster->GetActorLocation(), Point));
			TInlineComponentArray<USkeletalMeshComponent*> Meshes(Monster);
			for (USkeletalMeshComponent* Part : Meshes)
				if (Part->ComponentHasTag(TEXT("MonsterBodyPart"))) Test->TestTrue(TEXT("Existing modular armor follows animated mesh"), Part->LeaderPoseComponent.Get() == Monster->GetMesh());
			InitialEnemyLocation = Monster->GetActorLocation();
			InitialEnemyRotation = Monster->GetActorRotation();
			// Idle patrol may have rotated the pawn before this family is tested.
			// Place the real player in its current sight cone, not along an arbitrary world axis.
			FVector Location = InitialEnemyLocation + Monster->GetActorForwardVector() * 650.f;
			FNavLocation PlayerNav;
			if (!Nav || !Nav->ProjectPointToNavigation(Location, PlayerNav)) { Test->AddError(TEXT("Player sight fixture has no reachable floor")); Cleanup(); return true; }
			Location = PlayerNav.Location; Location.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			Player->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
			Player->GetCharacterMovement()->StopMovementImmediately();
			Player->GetController()->SetControlRotation(FRotator(-10.f, 180.f, 0.f)); // Test camera only.
			AI->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), true);
			AI->GetPerceptionComponent()->RequestStimuliListenerUpdate();
			bSawAlert = bSawChase = bSawAttack = bSawStandoff = false; SeenNaturalSections.Reset();
			ObserveLogAt = Now; Stage = 1; NextTime = Now; PatternDeadline = Now + 60.f; break;
		}
		case 1:
		{
			Test->TestEqual(TEXT("Sight detected the real player pawn"), AI->GetBattleTarget(), static_cast<AActor*>(Player.Get()));
			Test->TestTrue(TEXT("Observed Alert -> Chase -> Attack -> Standoff"), bSawAlert && bSawChase && bSawAttack && bSawStandoff);
			Test->TestTrue(TEXT("Navigation physically approached player"), FVector::Dist2D(InitialEnemyLocation, Monster->GetActorLocation()) > 100.f);
			Test->TestTrue(TEXT("Focus still locks onto player"), AI->GetFocusActor() == Player.Get());
			Test->TestTrue(TEXT("Attack/hold band is reached"), FVector::Dist2D(Monster->GetActorLocation(), Player->GetActorLocation()) <= Monster->GetAISettings().EngageDistance);
			FRotator View = (Monster->GetActorLocation() - Player->GetActorLocation()).Rotation();
			View.Pitch = -10.f; // Test framing only; face the actual current opponent.
			Player->GetController()->SetControlRotation(View);
			Stage = 6; NextTime = Now + 0.5f; break; // Test camera settling margin.
		}
		case 6:
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / (TEXT("Monster_") + Monster->GetClass()->GetName() + TEXT("_AI.png")), false, false);
			Stage = 7; NextTime = Now; break;
		case 7:
		{
			// RequestScreenshot is deferred until rendering. Teleport only after it is consumed.
			if (FScreenshotRequest::IsScreenshotRequested()) return false;
			// Beyond a committed root-motion lunge; reuse the configured encounter ranges for this QA placement.
			const FKZMonsterAISettings& Settings = Monster->GetAISettings();
			FVector Away; bool bReachableRetreat = false;
			UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Monster->GetWorld());
			const FVector AwayDirection = (Player->GetActorLocation() - Monster->GetActorLocation()).GetSafeNormal2D();
			for (int32 I = 0; Nav && I < 8; ++I)
			{
				const FVector Candidate = Monster->GetActorLocation() + AwayDirection.RotateAngleAxis(I * 45.f, FVector::UpVector) * (Settings.LoseSightRadius + Settings.PursuitLeashRadius);
				FNavLocation Floor;
				if (!Nav->ProjectPointToNavigation(Candidate, Floor)) continue;
				UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(Monster->GetWorld(), Monster->GetActorLocation(), Floor.Location, Monster);
				if (!Path || !Path->IsValid() || Path->IsPartial()) continue;
				Away = Floor.Location + FVector(0, 0, Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
				bReachableRetreat = true; break;
			}
			if (!Test->TestTrue(TEXT("Retreat fixture has a complete reachable nav path"), bReachableRetreat)) { Cleanup(); return true; }
			Player->SetActorLocation(Away, false, nullptr, ETeleportType::TeleportPhysics);
			bSawChase = bRechaseStarted = bRechaseAdvanced = false;
			Stage = 2; NextTime = Now + 10.f; PatternDeadline = Now + 60.f; break;
		}
		case 2:
		{
			// Root motion can carry an already committed attack towards the retreating player.
			// Allow that action to finish; the focused policy fixture tests the chase delay separately.
			if ((!bSawChase || !bRechaseAdvanced) && Now < PatternDeadline) return false;
			Test->TestTrue(TEXT("Player retreat re-enters chase"), bSawChase);
			Test->TestTrue(TEXT("Rechase navigation physically advances"), bRechaseAdvanced);
			AI->GetStateTreeComponent()->StopLogic(TEXT("Native pattern coverage after natural AI observations"));
			AI->StopMovement(); AI->GetPerceptionComponent()->Deactivate();
			ASC->CancelAllAbilities(); ASC->ClearComboCommands();
			if (bSkipWalk) { AttackIndex = 0; Stage = 3; NextTime = Now + 0.3f; break; }
			FKZMovementConstraint Walk; Walk.MaxAllowedGait = EKZGait::Walk; Walk.bOverrideRotationMode = true; Walk.RotationModeOverride = EKZRotationMode::LockOn; Walk.DebugName = TEXT("Monster directional pose test");
			WalkConstraint = Monster->GetLocomotionComponent()->AcquireMovementConstraint(AI, Walk);
			SavedDilation = Player->GetWorld()->GetWorldSettings()->TimeDilation;
			Player->GetWorld()->GetWorldSettings()->SetTimeDilation(0.25f); bDilationChanged = true; // Measurement resolution only, restored before gameplay pattern tests.
			AttackIndex = 0; DirectionIndex = 0; Stage = 8; NextTime = Now + 0.3f; break;
		}
		case 8:
		{
			// Real navigation and CMC movement; no synthetic input/velocity or Python player control.
			AI->StopMovement(); Monster->GetCharacterMovement()->StopMovementImmediately();
			Monster->SetActorLocation(FVector(0, 0, Monster->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
			Player->SetActorLocation(FVector(3500, 0, Player->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
			Monster->SetActorRotation(FRotator::ZeroRotator); AI->SetFocus(Player.Get());
			const double Angle = FMath::DegreesToRadians(DirectionIndex * 45.0); // Geometric test coverage.
			FAIMoveRequest Request; Request.SetGoalLocation(Monster->GetActorLocation() + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0) * 1000.f);
			Request.SetAcceptanceRadius(1.f); Request.SetReachTestIncludesAgentRadius(false); Request.SetCanStrafe(true);
			Test->TestTrue(TEXT("Directional pose fixture has a real nav path"), AI->MoveTo(Request).Code != EPathFollowingRequestResult::Failed);
			FootFrames.Reset(); LastFootPositions.Reset(); LastFootContacts.Reset(); LastFootTime = 0; WalkCaseAt = Now;
			Stage = 9; NextTime = Now + 2.f; break;
		}
		case 9:
			VerifyWalkingPose(Monster, Anim);
			if (DirectionIndex == 1)
			{
				// Isolated QA camera only: inspect the solved diagonal legs at a useful scale.
				if (APlayerController* PC = Cast<APlayerController>(Player->GetController()))
				{
					SavedViewTarget = PC->GetViewTarget();
					WalkCamera = Monster->GetWorld()->SpawnActor<ACameraActor>();
					const FVector View = Monster->GetActorLocation() + Monster->GetActorForwardVector()*500.f + Monster->GetActorRightVector()*220.f + FVector::UpVector*150.f;
					WalkCamera->SetActorLocation(View); WalkCamera->SetActorRotation((Monster->GetActorLocation()-View).Rotation());
					WalkCamera->GetCameraComponent()->SetFieldOfView(60.f); PC->SetViewTarget(WalkCamera.Get());
					FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / (TEXT("MonsterWalk_") + Monster->GetClass()->GetName() + TEXT("_Diagonal.png")), false, false);
					Stage = 10; NextTime = Now; break;
				}
			}
			if (++DirectionIndex < 8) { Stage = 8; NextTime = Now; }
			else { AI->StopMovement(); Monster->GetCharacterMovement()->StopMovementImmediately(); Monster->GetLocomotionComponent()->ReleaseMovementConstraint(WalkConstraint); WalkConstraint.Reset(); Player->GetWorld()->GetWorldSettings()->SetTimeDilation(SavedDilation); bDilationChanged = false; Stage = 3; NextTime = Now + 0.3f; }
			break;
		case 10:
			if (FScreenshotRequest::IsScreenshotRequested()) return false;
			ReleaseWalkCamera(); ++DirectionIndex; Stage = 8; NextTime = Now; break;
		case 3:
		{
			const auto& Attacks = Monster->GetAttackAbilities();
			if (AttackIndex >= Attacks.Num()) { Stage = 5; NextTime = Now; break; }
			// Keep every root-motion pattern on the open QA floor; never teleport during an active action.
			AI->StopMovement(); Monster->GetCharacterMovement()->StopMovementImmediately();
			Monster->SetActorLocation(FVector(0, 0, Monster->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
			Monster->SetActorRotation(FRotator::ZeroRotator); AI->SetFocus(Player.Get());
			FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(Attacks[AttackIndex]);
			if (!Test->TestNotNull(TEXT("Selected original attack is granted"), Spec)) { Cleanup(); return true; }
			const UKZComboActionAbility* Ability = CastChecked<UKZComboActionAbility>(Spec->Ability);
			ExpectedSections.Reset(); SeenSections.Reset(); bExpectedRootTravel = false; MaxAttackTravel = 0;
			const FKZComboNode* Node = Ability->GetComboDefinition()->FindNode(Ability->GetEntryNodeId());
			while (Node)
			{
				ExpectedSections.Add(Node->SectionName);
				if (Node->Montage) for (const FSlotAnimationTrack& Track : Node->Montage->SlotAnimTracks)
					for (const FAnimSegment& Segment : Track.AnimTrack.AnimSegments)
						if (const UAnimSequence* Clip = Cast<UAnimSequence>(Segment.GetAnimReference()))
						{
							Test->TestTrue(TEXT("Attack sequence enables root motion"), Clip->bEnableRootMotion);
							const FTransform Start = Clip->ExtractRootTrackTransform(FAnimExtractContext(Segment.AnimStartTime), nullptr);
							for (double Fraction : {0.5, 1.0})
								bExpectedRootTravel |= FVector::Dist2D(Start.GetTranslation(), Clip->ExtractRootTrackTransform(FAnimExtractContext(FMath::Lerp<double>(Segment.AnimStartTime, Segment.AnimEndTime, Fraction)), nullptr).GetTranslation()) > 1.f;
						}
				Node = Node->CommandEdges.IsEmpty() ? nullptr : Ability->GetComboDefinition()->FindNode(Node->CommandEdges[0].TargetNodeId);
			}
			AttackStart = Monster->GetActorLocation();
			Test->TestTrue(TEXT("NPC consumes montage root motion"), Anim->RootMotionMode == ERootMotionMode::RootMotionFromMontagesOnly);
			if (!Test->TestTrue(TEXT("Existing ComboAction activates for AI"), ASC->TryActivateAbility(Spec->Handle))) { Cleanup(); return true; }
			ActiveHandle = Spec->Handle;
			ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Begin);
			PatternDeadline = Now + 20.f; Stage = 4; NextTime = Now; break;
		}
		case 4:
		{
			FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(ActiveHandle);
			if (Spec && Spec->IsActive())
			{
				if (UAnimMontage* Montage = Anim->GetCurrentActiveMontage()) SeenSections.Add(Anim->Montage_GetCurrentSection(Montage));
				MaxAttackTravel = FMath::Max(MaxAttackTravel, FVector::Dist2D(AttackStart, Monster->GetActorLocation()));
				if (Now >= PatternDeadline) { Test->AddError(TEXT("Original pattern never completed")); Cleanup(); return true; }
				return false;
			}
			Test->TestEqual(TEXT("Original conditional combo visits every authored stage"), SeenSections.Num(), ExpectedSections.Num());
			for (FName Name : ExpectedSections) Test->TestTrue(TEXT("Original section observed"), SeenSections.Contains(Name));
			if (bExpectedRootTravel) Test->TestTrue(TEXT("Authored attack root motion physically moves the capsule"), MaxAttackTravel > 1.f);
			Test->TestFalse(TEXT("Natural end removes movement block"), ASC->HasMatchingGameplayTag(KZGameplayTags::Block_Movement_Input));
			Test->AddInfo(FString::Printf(TEXT("Pattern completed %s index=%d sections=%d rootTravelCm=%.3f expectedRootTravel=%d root=%s scale=%s"), *Monster->GetName(), AttackIndex, SeenSections.Num(), MaxAttackTravel, bExpectedRootTravel, *Monster->GetMesh()->GetBoneName(0).ToString(), *Monster->GetMesh()->GetRelativeScale3D().ToString()));
			ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Cancel);
			++AttackIndex; Stage = 3; NextTime = Now + 0.25f; break;
		}
		case 5:
		{
			const auto& Attacks = Monster->GetAttackAbilities();
			const auto* Spec = ASC->FindAbilitySpecFromClass(Attacks[0]);
			Test->TestTrue(TEXT("Cleanup fixture starts existing attack"), Spec && ASC->TryActivateAbility(Spec->Handle));
			ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Begin);
			AI->UnPossess();
			Test->TestFalse(TEXT("UnPossess cancels active action"), Spec->IsActive());
			Test->TestTrue(TEXT("UnPossess clears held combo intent"), ASC->GetHeldComboCommands().IsEmpty());
			Test->TestFalse(TEXT("UnPossess releases movement block"), ASC->HasMatchingGameplayTag(KZGameplayTags::Block_Movement_Input));
			Player->SetActorLocation(SavedPlayerLocation, false, nullptr, ETeleportType::TeleportPhysics);
			Monster->SetActorLocation(InitialEnemyLocation, false, nullptr, ETeleportType::TeleportPhysics);
			Monster->SetActorRotation(InitialEnemyRotation);
			AI->Possess(Monster); AI->GetPerceptionComponent()->Activate();
			AI->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), false);
			Test->TestTrue(TEXT("Repossess starts same StateTree"), AI->GetStateTreeComponent()->IsRunning());
			++MonsterIndex; Stage = 0; NextTime = Now + 1.f; break;
		}
		}
		return false;
	}
private:
	struct FFootFrame { int32 Bone; double Height, Slip, Speed; FVector RelativeVelocity, Movement; bool bPlanted; };
	void OnPostActorTick(UWorld* World, ELevelTick, float)
	{
		if (Stage != 9 || !Player.IsValid() || Player->GetWorld() != World || !Monsters.IsValidIndex(MonsterIndex)) return;
		AKZMonster* M = Monsters[MonsterIndex].Get(); if (!M) return;
		if (auto* AI = Cast<AKZMonsterAIController>(M->GetController())) AI->SetFocus(Player.Get());
		if (auto* Anim = M->GetMesh()->GetAnimInstance()) SampleWalkingFeet(M, Anim, World->GetTimeSeconds());
	}
	void SampleWalkingFeet(AKZMonster* M, UAnimInstance* Anim, float Now)
	{
		Anim->GetUngroupedActivePlayersRead(); // Wait for the current evaluated mesh, as in pose verification.
		USkeletalMeshComponent* Mesh = M->GetMesh(); const double Dt = Now - LastFootTime;
		for (int32 Bone = 0; Bone < Mesh->GetNumBones(); ++Bone)
		{
			const FString Name = Mesh->GetBoneName(Bone).ToString().ToLower();
			if (!Name.Contains(TEXT("foot")) || Name.Contains(TEXT("ik")) || Name.Contains(TEXT("toe")) || Name.StartsWith(TEXT("vb "))) continue;
			const FVector Point = Mesh->GetBoneLocation(Mesh->GetBoneName(Bone));
			float Contact = 2.f;
			const FName Curve = Name.Contains(TEXT("-l-")) ? TEXT("KZFootContactState_L") : TEXT("KZFootContactState_R");
			const bool bPlanted = Anim->GetCurveValue(Curve, Contact) && Contact < 1.f;
			if (LastFootTime > 0 && Dt > 0 && Now - WalkCaseAt > 0.3 && M->GetVelocity().Size2D() > 1.f)
			{
				const FVector FootVelocity = (Point - LastFootPositions.FindChecked(Bone)) / Dt;
				// The finite-difference interval is planted only if BOTH endpoint frames are planted.
				FootFrames.Add({Bone, Point.Z, FootVelocity.Size2D(), M->GetVelocity().Size2D(), FootVelocity - M->GetVelocity(), M->GetVelocity().GetSafeNormal2D(), bPlanted && LastFootContacts.FindRef(Bone)});
			}
			LastFootPositions.Add(Bone, Point);
			LastFootContacts.Add(Bone, bPlanted);
		}
		LastFootTime = Now;
	}
	void VerifyWalkingPose(AKZMonster* Monster, UAnimInstance* Anim)
	{
		const float Nominal = Monster->GetCharacterDefinition()->GetLocomotionConfig().WalkSpeed;
		const FAnimTickRecord* Active = nullptr;
		for (const FAnimTickRecord& Record : Anim->GetUngroupedActivePlayersRead())
			if (Cast<UBlendSpace>(Record.SourceAsset) && Record.SourceAsset->GetName().StartsWith(TEXT("BS_Combat_")) && Record.EffectiveBlendWeight > 0.99f) Active = &Record;
		if (!Test->TestNotNull(TEXT("Moving LockOn evaluates the combat walk player"), Active)) return;
		const TArray<FName>* MarkerNames = CastChecked<UBlendSpace>(Active->SourceAsset)->GetUniqueMarkerNames();
		Test->TestTrue(TEXT("Directional walking has both foot phase sync markers"), MarkerNames && MarkerNames->Contains(TEXT("KZLeftPlant")) && MarkerNames->Contains(TEXT("KZRightPlant")));
		Test->TestTrue(TEXT("Walk row is selected instead of Idle"), FMath::IsNearlyEqual(Active->BlendSpace.BlendSpacePositionY, Nominal, 0.01f));
		Test->TestTrue(TEXT("Each fixture actually exercises its intended actor-local direction"), FMath::Abs(FMath::FindDeltaAngleDegrees(Active->BlendSpace.BlendSpacePositionX, DirectionIndex * 45.f)) < 25.f);
		const double W = FMath::Fmod(FMath::Abs(Active->BlendSpace.BlendSpacePositionX), 90.f) / 90.0;
		const double DirectionMagnitude = FMath::Sqrt(W*W + (1.0-W)*(1.0-W));
		Test->TestTrue(TEXT("Walk rate advances with physical speed and diagonal stride correction"), Active->PlayRateMultiplier > 0.f && FMath::IsNearlyEqual(Active->PlayRateMultiplier, Monster->GetVelocity().Size2D() / (Nominal * DirectionMagnitude), 0.08f));
		const auto* Samples = Active->BlendSpace.BlendSampleDataCache;
		if (!Test->TestNotNull(TEXT("Walking has evaluated clip samples"), Samples)) return;
		float Total = 0.f; const FBlendSampleData* Dominant = nullptr;
		for (const FBlendSampleData& Sample : *Samples)
		{
			if (Sample.TotalWeight < 0.001f) continue;
			Total += Sample.TotalWeight;
			Test->TestTrue(TEXT("Every nonzero movement sample is a directional walk"), Sample.Animation && Sample.Animation->GetName().Contains(TEXT("LockOnWalk_")));
			Test->TestTrue(TEXT("Directional clip time advances"), Sample.DeltaTimeRecord.Delta > 0.f);
			if (!Dominant || Sample.TotalWeight > Dominant->TotalWeight) Dominant = &Sample;
		}
		Test->TestTrue(TEXT("Walk weights are normalized"), FMath::IsNearlyEqual(Total, 1.f, 0.001f));
		Test->AddInfo(FString::Printf(TEXT("MonsterWalkPose actor=%s case=%d speed=%.3f direction=%.3f row=%.3f rate=%.6f dominant=%s weight=%.6f"), *Monster->GetName(), DirectionIndex, Monster->GetVelocity().Size2D(), Active->BlendSpace.BlendSpacePositionX, Active->BlendSpace.BlendSpacePositionY, Active->PlayRateMultiplier, Dominant ? *GetNameSafe(Dominant->Animation) : TEXT("None"), Dominant ? Dominant->TotalWeight : 0));
		FMemMark Mark(FMemStack::Get()); FPoseContext Expected(Anim->GetRequiredBones()); Expected.ResetToRefPose();
		FAnimationPoseData PoseData(Expected); TArray<FBlendSampleData> SampleCopy = *Samples;
		CastChecked<UBlendSpace>(Active->SourceAsset)->GetAnimationPose(SampleCopy, FAnimExtractContext(0, false), PoseData);
		const auto& Actual = Monster->GetMesh()->GetBoneSpaceTransforms(); double PositionError = 0, AngleError = 0;
		for (FCompactPoseBoneIndex Bone : Expected.Pose.ForEachBoneIndex())
		{
			const int32 Index = Expected.Pose.GetBoneContainer().MakeMeshPoseIndex(Bone).GetInt();
			if (!Actual.IsValidIndex(Index)) { Test->AddError(TEXT("Walk mesh is missing a required bone")); return; }
			const FString Name = Monster->GetMesh()->GetBoneName(Index).ToString();
			// Foot Placement/Leg IK intentionally change only the pelvis and solved leg chains/targets.
			if (Name == TEXT("Bip001-Pelvis") || Name.StartsWith(TEXT("VB KZFoot_")) || Name.EndsWith(TEXT("-Thigh")) || Name.EndsWith(TEXT("-Calf")) || Name.EndsWith(TEXT("-Foot"))) continue;
			PositionError = FMath::Max(PositionError, FVector::Distance(Actual[Index].GetTranslation(), Expected.Pose[Bone].GetTranslation()));
			AngleError = FMath::Max(AngleError, FMath::RadiansToDegrees(Actual[Index].GetRotation().GetNormalized().AngularDistance(Expected.Pose[Bone].GetRotation().GetNormalized())));
		}
		Test->AddInfo(FString::Printf(TEXT("MonsterWalkMesh case=%d bones=%d maxLocalPosition=%.9f maxAngleDegrees=%.9f"), DirectionIndex, Expected.Pose.GetNumBones(), PositionError, AngleError));
		Test->TestTrue(TEXT("Uncontrolled bones preserve the evaluated moving BlendSpace pose"), PositionError < 0.02 && AngleError < 0.05);
		Test->TestFalse(TEXT("Floor-reading foot evaluator runs on the GameThread"), Anim->CanRunParallelWork());
		float Contact = 0.f;
		Test->TestTrue(TEXT("Left calculated contact curve is evaluated"), Anim->GetCurveValue(TEXT("KZFootContactState_L"), Contact));
		Test->TestTrue(TEXT("Right calculated contact curve is evaluated"), Anim->GetCurveValue(TEXT("KZFootContactState_R"), Contact));
		TArray<double> Slips, Ratios; FString CSV = TEXT("bone,height_cm,slip_cm_per_s,capsule_cm_per_s\n");
		for (const auto& Bone : LastFootPositions)
		{
			double Min = TNumericLimits<double>::Max(), Max = -TNumericLimits<double>::Max();
			for (const FFootFrame& F : FootFrames) if (F.Bone == Bone.Key) { Min = FMath::Min(Min, F.Height); Max = FMath::Max(Max, F.Height); }
			const double Band = FMath::Max(0.5, (Max-Min)*0.15); // Same documented stance-height analysis heuristic.
			for (const FFootFrame& F : FootFrames)
				if (F.Bone == Bone.Key && F.bPlanted && F.Height <= Min+Band && FVector::DotProduct(F.RelativeVelocity, F.Movement) < 0)
				{
					Slips.Add(F.Slip); Ratios.Add(F.Slip/F.Speed); CSV += FString::Printf(TEXT("%d,%.9f,%.9f,%.9f\n"), F.Bone, F.Height, F.Slip, F.Speed);
				}
		}
		if (!Slips.IsEmpty())
		{
			Slips.Sort(); Ratios.Sort();
			Test->TestTrue(TEXT("Foot contact measurement has multiple real evaluated frames"), Slips.Num() >= 3);
			// QA tolerance, not gameplay metadata: allow sub-centimetre numerical/contact-edge noise.
			Test->TestTrue(TEXT("Median planted ankle drift stays below one cm per second"), Slips[Slips.Num()/2] < 1.0);
			Test->AddInfo(FString::Printf(TEXT("MonsterFootPace actor=%s case=%d contactSamples=%d medianSlipCmPerS=%.3f medianSlipFraction=%.6f"), *Monster->GetName(), DirectionIndex, Slips.Num(), Slips[Slips.Num()/2], Ratios[Ratios.Num()/2]));
			const FString Directory = FPaths::ProjectSavedDir() / TEXT("MonsterIdle"); IFileManager::Get().MakeDirectory(*Directory, true);
			FFileHelper::SaveStringToFile(CSV, *(Directory / FString::Printf(TEXT("Foot_%s_%d.csv"), *Monster->GetClass()->GetName(), DirectionIndex)));
		}
		else Test->AddError(TEXT("Directional walk produced no measurable planted-foot frames"));
	}
	void ReleaseWalkCamera()
	{
		if (!WalkCamera.IsValid()) return;
		if (Player.IsValid())
			if (APlayerController* PC = Cast<APlayerController>(Player->GetController()))
				if (PC->GetViewTarget() == WalkCamera.Get()) PC->SetViewTarget(SavedViewTarget.IsValid() ? SavedViewTarget.Get() : Player.Get());
		WalkCamera->Destroy(); WalkCamera.Reset(); SavedViewTarget.Reset();
	}
	void RestoreSight()
	{
		for (const auto& Pair : SavedSight)
			if (auto* Perception = Pair.Key.Get()) Perception->SetSenseEnabled(UAISense_Sight::StaticClass(), Pair.Value);
		SavedSight.Reset();
	}
	void Cleanup()
	{
		ReleaseWalkCamera();
		FWorldDelegates::OnWorldPostActorTick.Remove(FootTickHandle); FootTickHandle.Reset();
		if (Player.IsValid())
		{
			if (bDilationChanged) { Player->GetWorld()->GetWorldSettings()->SetTimeDilation(SavedDilation); bDilationChanged = false; }
			Player->SetActorLocation(SavedPlayerLocation, false, nullptr, ETeleportType::TeleportPhysics);
			Player->SetActorRotation(SavedPlayerRotation);
			if (Player->GetController()) Player->GetController()->SetControlRotation(SavedControlRotation);
		}
		for (const auto& Weak : Monsters)
			if (AKZMonster* Monster = Weak.Get()) { Monster->GetAbilitySystemComponent()->CancelAllAbilities(); Monster->GetLocomotionComponent()->ReleaseMovementConstraint(WalkConstraint); }
		RestoreSight();
	}
	FAutomationTestBase* Test;
	TWeakObjectPtr<AKZPlayer> Player;
	TWeakObjectPtr<ACameraActor> WalkCamera; TWeakObjectPtr<AActor> SavedViewTarget;
	TArray<TWeakObjectPtr<AKZMonster>> Monsters;
	TMap<TWeakObjectPtr<UAIPerceptionComponent>, bool> SavedSight;
	FVector SavedPlayerLocation, InitialEnemyLocation, RechaseStart, AttackStart;
	FRotator SavedPlayerRotation, SavedControlRotation, InitialEnemyRotation;
	double Deadline;
	float SavedHP = 0, NextTime = 0, PatternDeadline = 0, ObserveLogAt = 0;
	int32 MonsterIndex = 0, AttackIndex = 0, Stage = 0, DirectionIndex = 0;
	bool bSawAlert = false, bSawChase = false, bSawAttack = false, bSawStandoff = false, bAnyLateral = false;
	FGameplayAbilitySpecHandle ActiveHandle;
	FKZMovementConstraintHandle WalkConstraint;
	TArray<FFootFrame> FootFrames; TMap<int32, FVector> LastFootPositions; TMap<int32, bool> LastFootContacts; float LastFootTime = 0, WalkCaseAt = 0;
	FDelegateHandle FootTickHandle; float SavedDilation = 1.f; bool bDilationChanged = false;
	bool bExpectedRootTravel = false; double MaxAttackTravel = 0;
	bool bSkipWalk = false;
	bool bRechaseStarted = false, bRechaseAdvanced = false;
	TSet<FName> ExpectedSections, SeenSections;
	TSet<FString> SeenNaturalSections;
};
class FWaitForMonsterPIE : public IAutomationLatentCommand
{
public:
	FWaitForMonsterPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 30.0) {}
	FWaitForMonsterPIE(FAutomationTestBase* InTest, bool bOnlyHalberd, bool bAttacksOnly = false) : FWaitForMonsterPIE(InTest) { bHalberdOnly = bOnlyHalberd; bSkipWalk = bAttacksOnly; }
	virtual bool Update() override
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			UWorld* World = Context.World(); if (Context.WorldType != EWorldType::PIE || !World || !World->HasBegunPlay()) continue;
			AKZPlayer* Player = nullptr; TArray<AKZMonster*> Monsters;
			for (TActorIterator<AKZPlayer> It(World); It; ++It) if (It->IsPlayerControlled()) Player = *It;
			for (TActorIterator<AKZMonster> It(World); It; ++It) if (It->GetActorLabel().StartsWith(TEXT("DevAI_")) && Cast<AKZMonsterAIController>(It->GetController()) && It->GetAIStateTree()) Monsters.Add(*It);
			if (!Player || Monsters.Num() != 4 || !Player->GetCharacterMovement()->IsMovingOnGround()) continue;
			if (bHalberdOnly) Monsters.RemoveAll([](const AKZMonster* M) { return !M->GetClass()->GetName().Contains(TEXT("HalberdElite")); });
			Monsters.Sort([](const AKZMonster& A, const AKZMonster& B) { return A.GetName() < B.GetName(); });
			FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FMonsterPIECommand>(Test, Player, Monsters, bSkipWalk)); return true;
		}
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Start PIE on new DevMap with four AI monsters")); return true; }
		return false;
	}
private:
	FAutomationTestBase* Test; double Deadline; bool bHalberdOnly = false, bSkipWalk = false;
};

class FMonsterWaitingPIE : public IAutomationLatentCommand
{
public:
	explicit FMonsterWaitingPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 180.0) {}
	bool Update() override
	{
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Waiting routine PIE timed out")); Restore(); return true; }
		if (!Player.IsValid())
		{
			for (const FWorldContext& Context : GEngine->GetWorldContexts())
			{
				UWorld* World = Context.World(); if (Context.WorldType != EWorldType::PIE || !World || !World->HasBegunPlay()) continue;
				for (TActorIterator<AKZPlayer> It(World); It; ++It) if (It->IsPlayerControlled()) Player = *It;
				for (TActorIterator<AKZMonster> It(World); It; ++It) Waiting.Add(It->GetActorLabel(), *It);
			}
			if (!Player.IsValid() || Waiting.Num() < 10 || !Player->GetCharacterMovement()->IsMovingOnGround()) return false;
			SavedLocation = Player->GetActorLocation();
			Left = Waiting.FindRef(TEXT("DevIdle_Talk01")); Right = Waiting.FindRef(TEXT("DevIdle_Talk02"));
			if (!Left.IsValid() || !Right.IsValid()) { Test->AddError(TEXT("DevMap talk pair is missing")); Restore(); return true; }
			Test->TestTrue(TEXT("Both mutually paired actors start Talk Loop together"), Left->HasActiveTalkLoop() && Right->HasActiveTalkLoop());
			Test->TestTrue(TEXT("Talk pair faces each other"), FVector::DotProduct(Left->GetActorForwardVector(), (Right->GetActorLocation()-Left->GetActorLocation()).GetSafeNormal2D()) > 0.99f && FVector::DotProduct(Right->GetActorForwardVector(), (Left->GetActorLocation()-Right->GetActorLocation()).GetSafeNormal2D()) > 0.99f);
			// Each fixture discovers only its selected actor; acquired encounter targets never expire.
			for (const auto& Pair : Waiting) if (Pair.Value.IsValid())
			{
				if (auto* AI = Cast<AKZMonsterAIController>(Pair.Value->GetController()))
				{
					SavedControllers.Add(Pair.Key, AI); SavedTransforms.Add(Pair.Key, Pair.Value->GetActorTransform());
					AI->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), false);
				}
			}
			for (const auto& Pair : Waiting)
			{
				if (!Pair.Value.IsValid()) continue;
				const auto* Def = Pair.Value->GetCharacterDefinition(); if (!Def) continue;
				for (const FKZUnawareRoutine& Routine : Def->GetUnawareRoutines())
				{
					const auto* Ability = Cast<UKZComboActionAbility>(Routine.AbilityClass->GetDefaultObject());
					const auto* Loop = Ability ? Ability->GetComboDefinition()->FindNode(TEXT("Loop")) : nullptr;
					Test->TestTrue(TEXT("Every authored wait has a matching Alert Release to End"), Loop && Loop->CommandEdges.Num() == 1 && Loop->CommandEdges[0].CommandTag == KZGameplayTags::Command_AI_Alert && Loop->CommandEdges[0].TargetNodeId == TEXT("End"));
				}
			}
			Phase = 0;
		}
		const float Now = Player->GetWorld()->GetTimeSeconds();
		if (Now < NextTime) return false;
		const TCHAR* Names[] = {TEXT("DevAI_Swordsman"), TEXT("DevIdle_Basic"), TEXT("DevIdle_Search"), TEXT("DevIdle_Sit")};
		const TCHAR* Routines[] = {TEXT("Guard"), TEXT("Basic"), TEXT("Search"), TEXT("Sit")};
		if (Phase == 0)
		{
			Current = Waiting.FindRef(Names[Index]);
			if (!Current.IsValid()) { Test->AddError(TEXT("Solo waiting actor is missing")); Restore(); return true; }
			auto* Anim = Current->GetMesh()->GetAnimInstance(); auto* Montage = Anim->GetCurrentActiveMontage();
			Test->TestTrue(TEXT("Unaware actor stays in its requested stationary Loop"), Montage && Montage->GetName() == FString(TEXT("Idle_")) + Routines[Index] && Anim->Montage_GetCurrentSection(Montage) == TEXT("Loop") && Current->GetVelocity().IsNearlyZero());
			StartLocation = Current->GetActorLocation(); SawEnd = false; Phase = 1; NextTime = Now;
			MovePlayerInSight(Current.Get()); return false;
		}
		if (Phase == 1)
		{
			auto* Anim = Current->GetMesh()->GetAnimInstance(); auto* Montage = Anim->GetCurrentActiveMontage();
			if (Montage && Montage->GetName().StartsWith(TEXT("Idle_")))
			{
				if (Anim->Montage_GetCurrentSection(Montage) == TEXT("End"))
				{
					SawEnd = true;
					Test->TestTrue(TEXT("Discovery End finishes before navigation approach"), CastChecked<AKZMonsterAIController>(Current->GetController())->GetMoveStatus() == EPathFollowingStatus::Idle);
				}
				return false;
			}
			Test->TestTrue(TEXT("The matching discovery End actually played"), SawEnd);
			Test->AddInfo(FString::Printf(TEXT("MonsterWaiting %s Loop -> End completed"), Routines[Index]));
			Player->SetActorLocation(SavedLocation, false, nullptr, ETeleportType::TeleportPhysics);
			// End this fixture's controller lifetime instead of relying on forgotten perception.
			CastChecked<AKZMonsterAIController>(Current->GetController())->UnPossess();
			if (++Index < UE_ARRAY_COUNT(Names)) { Phase = 0; NextTime = Now + 0.25f; return false; }
			Test->TestTrue(TEXT("Talk pair is still jointly talking before pair-loss fixture"), Left->HasActiveTalkLoop() && Right->HasActiveTalkLoop());
			RightAI = CastChecked<AKZMonsterAIController>(Right->GetController()); RightAI->UnPossess(); Phase = 2; SawEnd = false; return false;
		}
		if (Phase == 2)
		{
			auto* Anim = Left->GetMesh()->GetAnimInstance(); auto* Montage = Anim->GetCurrentActiveMontage();
			if (Montage && Montage->GetName() == TEXT("Idle_Talk01"))
			{
				SawEnd |= Anim->Montage_GetCurrentSection(Montage) == TEXT("End"); return false;
			}
			Test->TestTrue(TEXT("Losing partner ends the surviving Talk routine"), SawEnd && !Left->HasActiveTalkLoop());
			if (!Montage) return false;
			Test->TestTrue(TEXT("An unpaired actor returns to a solo routine"), Montage->GetName().StartsWith(TEXT("Idle_")));
			RightAI->Possess(Right.Get());
			// Reset only this PIE pair, then start one tree while both controllers are ready.
			auto* LeftAI = CastChecked<AKZMonsterAIController>(Left->GetController());
			LeftAI->GetStateTreeComponent()->StopLogic(TEXT("Waiting test pair reset")); RightAI->GetStateTreeComponent()->StopLogic(TEXT("Waiting test pair reset"));
			Left->GetAbilitySystemComponent()->CancelAllAbilities(); Right->GetAbilitySystemComponent()->CancelAllAbilities();
			LeftAI->GetStateTreeComponent()->StartLogic(); RightAI->GetStateTreeComponent()->StartLogic();
			Test->TestTrue(TEXT("Pair restart starts both roles in one turn"), Left->HasActiveTalkLoop() && Right->HasActiveTalkLoop());
			MovePlayerInSight(Left.Get()); Phase = 3; SawEnd = SawOtherEnd = false; return false;
		}
		auto* LeftAI = CastChecked<AKZMonsterAIController>(Left->GetController());
		auto Observe = [](AKZMonster* M) { auto* A = M->GetMesh()->GetAnimInstance(); auto* Montage = A->GetCurrentActiveMontage(); return Montage && Montage->GetName().StartsWith(TEXT("Idle_Talk")) && A->Montage_GetCurrentSection(Montage) == TEXT("End"); };
		SawEnd |= Observe(Left.Get()); SawOtherEnd |= Observe(Right.Get());
		if (!SawEnd || !SawOtherEnd) return false;
		Test->TestTrue(TEXT("Pair detection gives both actors the real player target"), LeftAI->GetBattleTarget() == Player.Get() && RightAI->GetBattleTarget() == Player.Get());
		Test->AddInfo(TEXT("MonsterWaiting Talk01/Talk02: simultaneous Loop, partner-loss End/Solo, coordinated discovery End verified")); Restore(); return true;
	}
private:
	void MovePlayerInSight(AKZMonster* M)
	{
		FNavLocation Point; auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(M->GetWorld());
		if (!Nav || !Nav->ProjectPointToNavigation(M->GetActorLocation() + M->GetActorForwardVector() * 650.f, Point)) { Test->AddError(TEXT("Waiting sight fixture has no nav floor")); return; }
		Point.Location.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		Player->SetActorLocation(Point.Location, false, nullptr, ETeleportType::TeleportPhysics); Player->GetCharacterMovement()->StopMovementImmediately();
		CastChecked<AKZMonsterAIController>(M->GetController())->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), true);
		CastChecked<AKZMonsterAIController>(M->GetController())->GetPerceptionComponent()->RequestStimuliListenerUpdate();
	}
	void Restore()
	{
		if (Player.IsValid()) Player->SetActorLocation(SavedLocation, false, nullptr, ETeleportType::TeleportPhysics);
		for (const auto& Pair : SavedControllers) if (Pair.Value.IsValid())
		{
			AKZMonster* Monster = Waiting.FindRef(Pair.Key).Get(); if (!Monster) continue;
			Pair.Value->UnPossess(); Monster->SetActorTransform(SavedTransforms[Pair.Key], false, nullptr, ETeleportType::TeleportPhysics);
			Pair.Value->GetPerceptionComponent()->ForgetAll(); Pair.Value->Possess(Monster);
			Pair.Value->GetPerceptionComponent()->SetSenseEnabled(UAISense_Sight::StaticClass(), true);
		}
		SavedControllers.Reset(); SavedTransforms.Reset();
	}
	FAutomationTestBase* Test; double Deadline; float NextTime = 0; int32 Index = 0, Phase = 0; bool SawEnd = false, SawOtherEnd = false;
	FVector SavedLocation, StartLocation;
	TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<AKZMonster> Current, Left, Right; TWeakObjectPtr<AKZMonsterAIController> RightAI;
	TMap<FString, TWeakObjectPtr<AKZMonster>> Waiting;
	TMap<FString, TWeakObjectPtr<AKZMonsterAIController>> SavedControllers;
	TMap<FString, FTransform> SavedTransforms;
};
// Focused real-StateTree regression: no synthetic AI state or player input injection.
class FMonsterCombatPolicyPIE : public IAutomationLatentCommand
{
public:
	explicit FMonsterCombatPolicyPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 300.0) {}
	~FMonsterCombatPolicyPIE() { Restore(); }
	bool Update() override
	{
		if (FPlatformTime::Seconds() > Deadline) { Test->AddError(TEXT("Combat policy PIE watchdog")); Restore(); return true; }
		if (!Player.IsValid())
		{
			for (const FWorldContext& C : GEngine->GetWorldContexts()) if (C.WorldType == EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
			{
				for (TActorIterator<AKZPlayer> It(C.World()); It; ++It) if (It->IsPlayerControlled()) Player = *It;
				if (!Player.IsValid() || !Player->GetCharacterMovement()->IsMovingOnGround()) return false;
				SavedPlayer = Player->GetActorTransform();
				for (TActorIterator<AKZMonster> It(C.World()); It; ++It) if (auto* AI = Cast<AKZMonsterAIController>(It->GetController()))
				{
					All.Add(*It); Controllers.Add(AI); SavedMonsters.Add(It->GetActorTransform());
					if (It->GetActorLabel().StartsWith(TEXT("DevAI_"))) Selected.Add(*It);
					AI->UnPossess(); AI->GetPerceptionComponent()->Deactivate(); AI->GetPerceptionComponent()->ForgetAll();
				}
				if (!Test->TestEqual(TEXT("Four original combat actors"), Selected.Num(), 4)) { Restore(); return true; }
				SampleHandle = FWorldDelegates::OnWorldPostActorTick.AddRaw(this, &FMonsterCombatPolicyPIE::Observe);
			}
			return false;
		}
		if (Index == Selected.Num()) { Restore(); return true; }
		Current = Selected[Index];
		AKZMonsterAIController* AI = Controllers[All.IndexOfByKey(Current)].Get();
		const float Now = Player->GetWorld()->GetTimeSeconds();
		const FKZMonsterAISettings& Settings = Current->GetAISettings();
		if (Stage == 0)
		{
			Player->SetActorTransform(SavedPlayer, false, nullptr, ETeleportType::TeleportPhysics);
			AI->GetPerceptionComponent()->ForgetAll(); AI->Possess(Current.Get()); AI->GetPerceptionComponent()->Activate();
			SawEnd = SawCommittedChase = SawChasePause = false; ChaseStartedAt = -1.f; AttackHandle = FGameplayAbilitySpecHandle();
			Next = Now + 1.f; Stage = 1; return false; // QA settling, not gameplay tuning.
		}
		if (Stage == 1 && Now >= Next)
		{
			const FKZUnawareRoutine* Routine = Current->ResolveUnawareRoutine();
			if (Current->GetClass()->GetName().Contains(TEXT("HeavySwordsman")) || Current->GetClass()->GetName().Contains(TEXT("HalberdElite")))
			{
				Test->TestEqual(TEXT("Fixed family has one unaware candidate"), Current->GetCharacterDefinition()->GetUnawareRoutines().Num(), 1);
				Test->TestTrue(TEXT("Fixed family chooses Basic"), Routine && Routine->Name == TEXT("Basic") && Routine->Role == EKZUnawareRoutineRole::Solo);
				UAnimMontage* M = Current->GetMesh()->GetAnimInstance()->GetCurrentActiveMontage();
				Test->TestTrue(TEXT("Fixed Basic loop is actually playing"), M && M->GetName() == TEXT("Idle_Basic") && Current->GetMesh()->GetAnimInstance()->Montage_GetCurrentSection(M) == TEXT("Loop"));
				if (M && !M->SlotAnimTracks.IsEmpty() && M->SlotAnimTracks[0].AnimTrack.AnimSegments.Num() == 2)
				{
					const FString Suffix = Current->GetClass()->GetName().Contains(TEXT("HalberdElite")) ? TEXT("02") : TEXT("03");
					Test->TestTrue(TEXT("Exact requested Loop clip"), M->SlotAnimTracks[0].AnimTrack.AnimSegments[0].GetAnimReference()->GetName().EndsWith(TEXT("Idle_Loop_") + Suffix));
					Test->TestTrue(TEXT("Exact matching End clip"), M->SlotAnimTracks[0].AnimTrack.AnimSegments[1].GetAnimReference()->GetName().EndsWith(TEXT("Idle_End_") + Suffix));
				}
			}
			FVector Near;
			if (!Project(Current->GetActorLocation() + Current->GetActorForwardVector() * (Settings.EngageDistance + Settings.PreferredDistance), Near) || !FindRetreat(Settings)) { Test->AddError(TEXT("Policy fixture requires reachable near/far floor")); Restore(); return true; }
			Player->SetActorLocation(Near, false, nullptr, ETeleportType::TeleportPhysics); Player->GetCharacterMovement()->StopMovementImmediately();
			AI->GetPerceptionComponent()->RequestStimuliListenerUpdate(); Stage = 2; Next = Now + 60.f; return false;
		}
		if (Stage == 2 && Now > Next) { Test->AddError(TEXT("Sight -> matching End -> Standoff not observed")); Restore(); return true; }
		if (Stage == 3 && Now - RetreatedAt >= Settings.TargetMemorySeconds + Settings.StandoffSeconds.Y)
		{
			Test->TestEqual(TEXT("Beyond sight memory/leash retains same valid player"), AI->GetBattleTarget(), static_cast<AActor*>(Player.Get()));
			Test->TestTrue(TEXT("Far remembered player remains focused"), AI->GetFocusActor() == Player.Get());
			Test->TestTrue(TEXT("Local action finishes before re-chase"), SawCommittedChase);
			Test->TestTrue(TEXT("Chase holds navigation during the configured reaction"), SawChasePause);
			Test->TestTrue(TEXT("Completed local action then physically pursues"), FVector::Dist2D(RetreatMonsterLocation, Current->GetActorLocation()) > Settings.DistanceTolerance);
			FVector Near;
			if (!Project(Current->GetActorLocation() + Current->GetActorForwardVector() * Settings.PreferredDistance, Near)) { Test->AddError(TEXT("Attack fixture projection failed")); Restore(); return true; }
			Player->SetActorLocation(Near, false, nullptr, ETeleportType::TeleportPhysics); Player->GetCharacterMovement()->StopMovementImmediately(); Stage = 4; Next = Now + 30.f;
		}
		if ((Stage == 4 || Stage == 5) && Now > Next) { Test->AddError(TEXT("Attack completion -> Chase not observed")); Restore(); return true; }
		if (Stage == 6)
		{
			AI->UnPossess(); AI->GetPerceptionComponent()->Deactivate(); AI->GetPerceptionComponent()->ForgetAll();
			Test->TestNull(TEXT("Controller lifetime clears encounter target"), AI->GetBattleTarget());
			Test->TestNull(TEXT("Controller lifetime clears focus"), AI->GetFocusActor());
			Test->TestFalse(TEXT("Controller lifetime stops StateTree"), AI->GetStateTreeComponent()->IsRunning());
			Test->AddInfo(FString::Printf(TEXT("CombatPolicy completed %s: fixed routine/End, committed standoff, persistent target, attack completion and re-chase"), *Current->GetClass()->GetName()));
			++Index; Stage = 0;
		}
		return false;
	}
private:
	bool Project(const FVector& Location, FVector& Out) const
	{
		FNavLocation P; auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Player->GetWorld());
		if (!Nav || !Nav->ProjectPointToNavigation(Location, P)) return false;
		Out = P.Location + FVector(0, 0, Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); return true;
	}
	bool FindRetreat(const FKZMonsterAISettings& Settings)
	{
		const FVector Home = SavedMonsters[All.IndexOfByKey(Current)].GetLocation();
		for (int32 I = 0; I < 8; ++I)
		{
			const double A = FMath::DegreesToRadians(I * 45.0); // Geometric QA candidate directions.
			if (Project(Home + FVector(FMath::Cos(A), FMath::Sin(A), 0) * (Settings.PursuitLeashRadius + Settings.LoseSightRadius), Far) && FVector::Dist2D(Home, Far) > Settings.PursuitLeashRadius) return true;
		}
		return false;
	}
	void Observe(UWorld* World, ELevelTick, float)
	{
		if (!Player.IsValid() || !Current.IsValid() || World != Player->GetWorld()) return;
		auto* AI = Cast<AKZMonsterAIController>(Current->GetController()); if (!AI) return;
		const FString State = AI->GetStateTreeComponent()->GetDebugInfoString(); const float Now = World->GetTimeSeconds();
		auto* Anim = Current->GetMesh()->GetAnimInstance(); auto* ASC = Current->GetAbilitySystemComponent();
		if (Stage == 2)
		{
			UAnimMontage* M = Anim->GetCurrentActiveMontage(); SawEnd |= M && M->GetName().StartsWith(TEXT("Idle_")) && Anim->Montage_GetCurrentSection(M) == TEXT("End");
			if (SawEnd && State.Contains(TEXT("Standoff")))
			{
				StandoffAt = RetreatedAt = Now; RetreatMonsterLocation = Current->GetActorLocation();
				Player->SetActorLocation(Far, false, nullptr, ETeleportType::TeleportPhysics); Player->GetCharacterMovement()->StopMovementImmediately(); Stage = 3;
			}
		}
		else if (Stage == 3)
		{
			Test->TestEqual(TEXT("Encounter does not forget player during retreat"), AI->GetBattleTarget(), static_cast<AActor*>(Player.Get()));
			Test->TestFalse(TEXT("Retreat never returns to unaware state"), State.Contains(TEXT("Idle")) || State.Contains(TEXT("Patrol")));
			if (State.Contains(TEXT("Chase")) && !SawCommittedChase)
			{
				Test->TestTrue(TEXT("Chase waits at least the chosen standoff minimum"), Now - StandoffAt + 2.f * World->GetDeltaSeconds() >= Current->GetAISettings().StandoffSeconds.X);
				SawCommittedChase = true;
				ChaseStartedAt = Now;
				ChaseStartLocation = Current->GetActorLocation();
			}
			if (ChaseStartedAt >= 0.f && Now - ChaseStartedAt + 2.f * World->GetDeltaSeconds() < Current->GetAISettings().ChaseReactionSeconds)
			{
				Test->TestTrue(TEXT("Reaction has no navigation request"), AI->GetMoveStatus() == EPathFollowingStatus::Idle);
				Test->TestTrue(TEXT("Reaction does not prematurely chase"), FVector::Dist2D(ChaseStartLocation, Current->GetActorLocation()) < 1.f);
				SawChasePause = true;
			}
		}
		else if (Stage == 4 && State.Contains(TEXT("Attack")))
		{
			for (const FGameplayAbilitySpec& S : ASC->GetActivatableAbilities()) if (S.IsActive() && Current->GetAttackAbilities().Contains(S.Ability->GetClass())) AttackHandle = S.Handle;
			if (AttackHandle.IsValid())
			{
				Player->SetActorLocation(Far, false, nullptr, ETeleportType::TeleportPhysics); Player->GetCharacterMovement()->StopMovementImmediately(); Stage = 5;
			}
		}
		else if (Stage == 5)
		{
			const FGameplayAbilitySpec* S = ASC->FindAbilitySpecFromHandle(AttackHandle);
			if (S && S->IsActive()) Test->TestTrue(TEXT("Retreat does not interrupt the selected attack"), State.Contains(TEXT("Attack")));
			else if (State.Contains(TEXT("Chase"))) Stage = 6;
		}
	}
	void Restore()
	{
		if (SampleHandle.IsValid()) { FWorldDelegates::OnWorldPostActorTick.Remove(SampleHandle); SampleHandle.Reset(); }
		if (Player.IsValid()) Player->SetActorTransform(SavedPlayer, false, nullptr, ETeleportType::TeleportPhysics);
		for (int32 I = 0; I < All.Num(); ++I) if (All[I].IsValid() && Controllers[I].IsValid())
		{
			Controllers[I]->UnPossess(); All[I]->SetActorTransform(SavedMonsters[I], false, nullptr, ETeleportType::TeleportPhysics);
			Controllers[I]->GetPerceptionComponent()->ForgetAll(); Controllers[I]->Possess(All[I].Get()); Controllers[I]->GetPerceptionComponent()->Activate();
		}
		All.Reset(); Controllers.Reset();
	}
	FAutomationTestBase* Test; double Deadline; TWeakObjectPtr<AKZPlayer> Player; FTransform SavedPlayer;
	TArray<TWeakObjectPtr<AKZMonster>> All, Selected; TArray<TWeakObjectPtr<AKZMonsterAIController>> Controllers; TArray<FTransform> SavedMonsters;
	TWeakObjectPtr<AKZMonster> Current; FDelegateHandle SampleHandle; int32 Index = 0, Stage = 0;
	float Next = 0, StandoffAt = 0, RetreatedAt = 0; FVector Far, RetreatMonsterLocation;
	bool SawEnd = false, SawCommittedChase = false, SawChasePause = false; FGameplayAbilitySpecHandle AttackHandle;
	float ChaseStartedAt = -1.f; FVector ChaseStartLocation;
};
}
namespace
{
// Native moving-target fixture. Only the player is moved after initial placement.
// The root-motion observer returns the existing delegate's transform unchanged.
class FMonsterFacingPIE : public IAutomationLatentCommand
{
public:
	explicit FMonsterFacingPIE(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 900.0) {}
	~FMonsterFacingPIE() { Restore(); }
	bool Update() override
	{
		if (FPlatformTime::Seconds() > Deadline) { Fail(TEXT("Facing PIE watchdog")); Restore(); return true; }
		if (!Player.IsValid())
		{
			for (const FWorldContext& C : GEngine->GetWorldContexts()) if (C.WorldType == EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
			{
				for (TActorIterator<AKZPlayer> It(C.World()); It; ++It) if (It->IsPlayerControlled()) Player = *It;
				if (!Player.IsValid() || !Player->GetCharacterMovement()->IsMovingOnGround()) return false;
				SavedPlayer = Player->GetActorTransform();
				for (TActorIterator<AKZMonster> It(C.World()); It; ++It) if (auto* InitialAI = Cast<AKZMonsterAIController>(It->GetController()))
				{
					All.Add(*It); Controllers.Add(InitialAI); SavedMonsters.Add(It->GetActorTransform());
					if (It->GetActorLabel().StartsWith(TEXT("DevAI_"))) Selected.Add(*It);
					InitialAI->UnPossess(); InitialAI->GetPerceptionComponent()->Deactivate(); InitialAI->GetPerceptionComponent()->ForgetAll();
				}
				if (!Test->TestEqual(TEXT("Facing fixture contains all four combat families"), Selected.Num(), 4)) { Restore(); return true; }
				Trace = TEXT("family,attack,time,dt,node_before,node_after,node_changed,section,montage_position,target_x,target_y,target_z,target_yaw,control_yaw_before,control_yaw_after,desired_yaw_before,desired_yaw_after,body_before,body_after,root_yaw,steering_yaw,error_before,error_after,approaching,next_node_preparation,root_samples,cmc_yaw_rate,physics_phase_valid,physics_approaching,physics_preparation,physics_node,physics_section,physics_position,physics_effective_rate\n");
				PreHandle = FWorldDelegates::OnWorldPreActorTick.AddRaw(this, &FMonsterFacingPIE::BeforeTick);
				PostHandle = FWorldDelegates::OnWorldPostActorTick.AddRaw(this, &FMonsterFacingPIE::AfterTick);
			}
			return false;
		}
		if (Index == Selected.Num())
		{
			Test->TestEqual(TEXT("Facing exercised all existing original attacks"), TotalPatterns, 35);
			Restore(); return true;
		}
		Current = Selected[Index]; AI = Controllers[All.IndexOfByKey(Current)];
		if (!Current.IsValid() || !AI.IsValid()) { Fail(TEXT("Facing fixture lost its possessed actors")); Restore(); return true; }
		const double Now = Player->GetWorld()->GetTimeSeconds();
		auto* ASC = CastChecked<UKZAbilitySystemComponent>(Current->GetAbilitySystemComponent());
		auto* CMC = Current->GetCharacterMovement();
		if (Stage == 0)
		{
			FVector Floor;
			if (!Project(FVector(0, 0, Current->GetActorLocation().Z), Floor)) { Fail(TEXT("Facing fixture needs the real open nav floor")); Restore(); return true; }
			Current->SetActorLocation(Floor, false, nullptr, ETeleportType::TeleportPhysics);
			Current->SetActorRotation(FRotator(0, 170.f, 0)); // QA geometry: exercise the +/-180 degree seam.
			AI->Possess(Current.Get()); AI->GetPerceptionComponent()->Activate();
			Bearing = 170.f; PlacePlayer(); AI->GetPerceptionComponent()->RequestStimuliListenerUpdate();
			Next = Now + 30.0; Stage = 1; return false;
		}
		if (Stage == 1)
		{
			if (Now > Next) { Fail(TEXT("Facing fixture did not acquire the real player through Sight and enter LockOn")); Restore(); return true; }
			if (AI->GetBattleTarget() != Player.Get() || AI->GetFocusActor() != Player.Get() ||
				Current->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode != EKZRotationMode::LockOn) return false;
			// Keep the acquired Controller, BattleTarget, gameplay focus and locomotion intent alive.
			AI->GetStateTreeComponent()->StopLogic(TEXT("Native facing coverage after actual Sight acquisition"));
			AI->StopMovement(); CMC->StopMovementImmediately(); ASC->CancelAllAbilities(); ASC->ClearComboCommands();
			TrackingRate = Setting(TEXT("AttackTrackingYawRate")); ReaimRate = Setting(TEXT("ComboReaimYawRate")); Preparation = Setting(TEXT("AttackPreparationSeconds"));
			if (TrackingRate <= 0 || ReaimRate <= 0 || Preparation <= 0) { Fail(TEXT("Facing requires the current positive editable attack tracking settings")); Restore(); return true; }
			Require(CMC->bAllowPhysicsRotationDuringAnimRootMotion, TEXT("Monster enables physics rotation while consuming animation root motion"));
			Require(CMC->bUseControllerDesiredRotation && !Current->bUseControllerRotationYaw, TEXT("CMC owns bounded capsule rotation"));
			SavedRootObserver = CMC->ProcessRootMotionPostConvertToWorld;
			CMC->ProcessRootMotionPostConvertToWorld.BindRaw(this, &FMonsterFacingPIE::ObserveRootMotion);
			ObservedCMC = CMC; AttackIndex = 0; SawWrap = SawSlowTracking = SawFastTracking = false; Stage = 2;
		}
		if (Stage == 2)
		{
			const auto& Attacks = Current->GetAttackAbilities();
			if (AttackIndex == Attacks.Num())
			{
				Require(SawWrap, TEXT("Family exercised a normalized target bearing across +/-180"));
				Require(SawSlowTracking, TEXT("Family steered toward a moving target during ordinary attack tracking"));
				Require(SawFastTracking, TEXT("Family observed faster preparation steering without a capsule snap"));
				Bearing = FRotator::NormalizeAxis(Current->GetActorRotation().Yaw + 25.f); PlacePlayer();
				NormalStarted = Now; NormalConverged = false; NormalRootSamples = 0; Stage = 4; return false;
			}
			FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(Attacks[AttackIndex]);
			if (!Spec || !ASC->TryActivateAbility(Spec->Handle)) { Fail(TEXT("Facing could not activate the existing granted attack")); Restore(); return true; }
			Active = Spec->Handle; Ability = Cast<UKZComboActionAbility>(Spec->GetPrimaryInstance());
			if (!Ability.IsValid()) { Fail(TEXT("Facing requires the executing ComboAction instance")); Restore(); return true; }
			Expected.Reset(); Seen.Reset(); ExpectedRootYaw = false; ObservedRootYaw = 0; PatternRootSamples = 0; PatternFrames = 0;
			const auto* Definition = Ability->GetComboDefinition(); const FKZComboNode* Node = Definition->FindNode(Ability->GetEntryNodeId());
			while (Node && !Expected.Contains(Node->NodeId))
			{
				Expected.Add(Node->NodeId);
				if (Node->Montage)
				{
					const int32 Section = Node->Montage->GetSectionIndex(Node->SectionName); float Start = 0, End = 0;
					Node->Montage->GetSectionStartAndEndTime(Section, Start, End);
					// Use the actual first-track source frame interval, mapped through the segment
					// playback rate. An authored montage can inherit an unrelated engine frame rate.
					double Interval = 0.0;
					if (!Node->Montage->SlotAnimTracks.IsEmpty())
						for (const FAnimSegment& Segment : Node->Montage->SlotAnimTracks[0].AnimTrack.AnimSegments)
						{
							const UAnimSequenceBase* Source = Segment.GetAnimReference();
							if (!Source || Segment.StartPos >= End || Segment.GetEndPos() <= Start) continue;
							const FFrameRate Sampling = Source->GetSamplingFrameRate();
							const double PlaybackRate = FMath::Abs(Segment.AnimPlayRate * Source->RateScale);
							if (Sampling.Numerator <= 0 || Sampling.Denominator <= 0 || PlaybackRate <= 0)
							{ Fail(TEXT("Original root audit requires valid source frames and segment playback rate")); continue; }
							const double SourceInterval = Sampling.AsInterval() / PlaybackRate;
							Interval = Interval > 0.0 ? FMath::Min(Interval, SourceInterval) : SourceInterval;
						}
					Require(Interval > 0.0 && End > Start, TEXT("Original root audit has a source segment in the authored section"));
					const FQuat MeshBasis = Current->GetMesh()->GetComponentQuat();
					for (double T = Start; Interval > 0 && T < End; T += Interval)
					{
						const FQuat Local = Node->Montage->ExtractRootMotionFromTrackRange(T, FMath::Min<double>(End, T + Interval), FAnimExtractContext(T)).GetRotation();
						// Same quaternion basis conversion as USkeletalMeshComponent; local roll
						// or pitch can become the capsule's world yaw on these imported assemblies.
						ExpectedRootYaw |= FMath::Abs((MeshBasis * Local * MeshBasis.Inverse()).Rotator().Yaw) > AngleTolerance;
					}
				}
				Node = Node->CommandEdges.IsEmpty() ? nullptr : Definition->FindNode(Node->CommandEdges[0].TargetNodeId);
			}
			ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Begin);
			LastNode = NAME_None; NodeStarted = Now; NextTargetChange = Now; BaseBearing = Current->GetActorRotation().Yaw; Bearing = BaseBearing; PlacePlayer(); bOffset = false; WasApproaching = false;
			PatternDeadline = Now + 30.0; Stage = 3; return false;
		}
		if (Stage == 3)
		{
			const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(Active);
			if (Spec && Spec->IsActive())
			{
				if (Now > PatternDeadline) { Fail(TEXT("Facing original held combo did not finish")); Restore(); return true; }
				return false;
			}
			for (FName Node : Expected) Require(Seen.Contains(Node), TEXT("Facing observed every existing authored combo node"));
			Require(PatternFrames > 0 && PatternRootSamples > 0, TEXT("Facing sampled capsule steering together with consumed root motion"));
			if (ExpectedRootYaw) Require(ObservedRootYaw > AngleTolerance, TEXT("Original rotating root motion remains present in CMC consumption"));
			Test->AddInfo(FString::Printf(TEXT("Facing pattern %s index=%d nodes=%d frames=%d rootSamples=%d originalYaw=%d consumedAbsRootYaw=%.3f"), *Current->GetClass()->GetName(), AttackIndex, Seen.Num(), PatternFrames, PatternRootSamples, ExpectedRootYaw, ObservedRootYaw));
			ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Cancel);
			++AttackIndex; ++TotalPatterns; Stage = 2; return false;
		}
		if (Stage == 4)
		{
			const double Allowed = Preparation + 25.0 / FMath::Max(1.f, FMath::Abs(CMC->RotationRate.Yaw)) + 1.0; // QA watchdog derived from the actual CMC rate.
			if (!NormalConverged && Now - NormalStarted < Allowed) return false;
			Require(NormalConverged, TEXT("Natural attack end returns to ordinary target-facing rotation"));
			Require(NormalRootSamples == 0, TEXT("Ordinary rotation after attack no longer consumes attack root motion"));
			Require(!ASC->HasMatchingGameplayTag(KZGameplayTags::Block_Movement_Input), TEXT("Natural attack end removes its movement block"));
			Require(ASC->GetHeldComboCommands().IsEmpty(), TEXT("Natural attack cleanup clears the QA held command"));
			Test->AddInfo(FString::Printf(TEXT("Facing family completed %s attacks=%d wrap=%d slow=%d fast=%d normal=%d"), *Current->GetClass()->GetName(), AttackIndex, SawWrap, SawSlowTracking, SawFastTracking, NormalConverged));
			ReleaseObserver(); AI->UnPossess(); AI->GetPerceptionComponent()->Deactivate(); ++Index; Stage = 0;
		}
		return false;
	}
private:
	// Test measurement tolerance and geometric stimulus, not gameplay tuning or original-game values.
	static constexpr float AngleTolerance = 0.25f;
	void Fail(const TCHAR* Message)
	{
		const FString Key = FString::Printf(TEXT("%s attack=%d: %s"), *GetNameSafe(Current.Get()), AttackIndex, Message);
		if (!Errors.Contains(Key)) { Errors.Add(Key); Test->AddError(Key); }
	}
	void Require(bool Condition, const TCHAR* Message) { if (!Condition) Fail(Message); }
	float Setting(FName Name) const
	{
		const FFloatProperty* Property = FindFProperty<FFloatProperty>(FKZMonsterAISettings::StaticStruct(), Name);
		return Property ? Property->GetPropertyValue_InContainer(&Current->GetAISettings()) : 0.f;
	}
	bool Project(const FVector& Location, FVector& Out) const
	{
		FNavLocation P; auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Player->GetWorld());
		if (!Nav || !Nav->ProjectPointToNavigation(Location, P)) return false;
		Out = P.Location + FVector(0, 0, Current->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); return true;
	}
	void PlacePlayer()
	{
		const FVector Direction = FRotator(0, Bearing, 0).Vector();
		FVector Position = Current->GetActorLocation() + Direction * Current->GetAISettings().PreferredDistance;
		Position.Z += Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Current->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		Player->SetActorLocation(Position, false, nullptr, ETeleportType::TeleportPhysics); Player->GetCharacterMovement()->StopMovementImmediately();
	}
	float TargetYaw() const { return (Player->GetActorLocation() - Current->GetActorLocation()).Rotation().Yaw; }
	FTransform ObserveRootMotion(const FTransform& Root, UCharacterMovementComponent* Movement, float Dt)
	{
		const FTransform Result = SavedRootObserver.IsBound() ? SavedRootObserver.Execute(Root, Movement, Dt) : Root;
		FrameRoot = Result.GetRotation() * FrameRoot; ++RootSamples;
		// CMC has already ticked the montage/notifies, and has not yet called PhysicsRotation.
		// Classify that actual phase instead of the previous pose seen by WorldPreActorTick.
		if (Stage == 3 && Ability.IsValid() && Ability->IsActive())
		{
			auto* Anim = Current->GetMesh()->GetAnimInstance(); UAnimMontage* Montage = Anim->GetCurrentActiveMontage();
			if (Montage)
			{
				PhysicsNode = Ability->GetCurrentNodeId(); PhysicsSection = Anim->Montage_GetCurrentSection(Montage);
				PhysicsPosition = Anim->Montage_GetPosition(Montage); PhysicsPlayRate = Anim->Montage_GetEffectivePlayRate(Montage);
				const int32 Section = Montage->GetSectionIndexFromPosition(PhysicsPosition);
				PhysicsPhaseValid = Section != INDEX_NONE && PhysicsPlayRate > 0.f;
				PhysicsApproaching = Ability->IsApproachingComboTransition(Preparation);
				PhysicsPreparing = PhysicsPhaseValid &&
					(PhysicsPosition - Montage->GetAnimCompositeSection(Section).GetTime()) / PhysicsPlayRate < Preparation;
			}
		}
		ObservedRootYaw += FMath::Abs(Result.Rotator().Yaw); return Result;
	}
	void BeforeTick(UWorld* World, ELevelTick, float Dt)
	{
		if (!Player.IsValid() || !Current.IsValid() || !AI.IsValid() || World != Player->GetWorld() || (Stage != 3 && Stage != 4)) return;
		FrameRoot = FQuat::Identity; RootSamples = 0; Before = Current->GetActorQuat(); BeforeNode = NAME_None;
		PhysicsPhaseValid = PhysicsApproaching = PhysicsPreparing = false;
		PhysicsNode = PhysicsSection = NAME_None; PhysicsPosition = PhysicsPlayRate = 0.f;
		bHaveFrame = true;
		const double Now = World->GetTimeSeconds(); bApproaching = bPreparing = false;
		if (Stage == 3 && Ability.IsValid() && Ability->IsActive())
		{
			BeforeNode = Ability->GetCurrentNodeId();
			Seen.Add(BeforeNode);
			if (BeforeNode != LastNode) { LastNode = BeforeNode; NodeStarted = Now; }
			bApproaching = Ability->IsApproachingComboTransition(Preparation);
			bPreparing = Now - NodeStarted <= Preparation;
			if (Now >= NextTargetChange || (bApproaching && !WasApproaching))
			{
				const float OldBearing = Bearing; bOffset = !bOffset; Bearing = FRotator::NormalizeAxis(BaseBearing + (bOffset ? 25.f : 0.f));
				SawWrap |= FMath::Abs(Bearing - OldBearing) > 180.f && FMath::Abs(FRotator::NormalizeAxis(Bearing - OldBearing)) <= 25.f + AngleTolerance;
				NextTargetChange = Now + Preparation; // Stimulus period uses the current editable preparation duration.
			}
			WasApproaching = bApproaching;
		}
		PlacePlayer(); BeforeTargetYaw = TargetYaw(); BeforeError = FMath::Abs(FRotator::NormalizeAxis(BeforeTargetYaw - Before.Rotator().Yaw));
		BeforeControlYaw = AI->GetControlRotation().Yaw; BeforeDesiredYaw = AI->GetDesiredRotation().Yaw;
	}
	void AfterTick(UWorld* World, ELevelTick, float Dt)
	{
		if (!Player.IsValid() || !Current.IsValid() || !AI.IsValid() || World != Player->GetWorld() || (Stage != 3 && Stage != 4) || Dt <= 0 || !bHaveFrame) return;
		bHaveFrame = false;
		Require(AI->GetBattleTarget() == Player.Get() && AI->GetFocusActor() == Player.Get(), TEXT("Acquired BattleTarget and gameplay focus survive every moving-target tick"));
		const FQuat After = Current->GetActorQuat();
		// CMC applies physics rotation first and world-space root rotation afterwards.
		// Factor the actually consumed root quaternion out; do not infer it across a section jump.
		const float Steering = FRotator::NormalizeAxis((FrameRoot.Inverse() * After).Rotator().Yaw - Before.Rotator().Yaw);
		const float Error = FMath::Abs(FRotator::NormalizeAxis(TargetYaw() - After.Rotator().Yaw));
		const bool Fast = PhysicsApproaching || PhysicsPreparing;
		if (Stage == 3)
		{
			++PatternFrames; PatternRootSamples += RootSamples;
			// A montage may naturally end inside this tick before CMC chooses ordinary rotation.
			// Do not apply an active-attack limit to that legitimate lifetime boundary.
			const bool StillActive = Ability.IsValid() && Ability->IsActive();
			if (StillActive) Require(FMath::Abs(Steering) <= FMath::Max(TrackingRate, ReaimRate) * Dt + AngleTolerance, TEXT("Attack and combo preparation steer continuously instead of snapping the capsule"));
			// Without a post-pose root sample the exact attack phase is unknown; retain the
			// maximum-rate/no-snap check, but do not guess a slower-rate classification.
			if (StillActive && PhysicsPhaseValid && !Fast && BeforeError > TrackingRate * Dt + AngleTolerance)
			{
				Require(FMath::Abs(Steering) <= TrackingRate * Dt + AngleTolerance, TEXT("Ordinary attack steering uses its configured slower rate"));
				SawSlowTracking |= FMath::Abs(Steering) > AngleTolerance;
			}
			if (StillActive && PhysicsPhaseValid && Fast) SawFastTracking |= FMath::Abs(Steering) > TrackingRate * Dt + AngleTolerance;
			if (Ability.IsValid() && Ability->IsActive()) Seen.Add(Ability->GetCurrentNodeId());
		}
		else
		{
			NormalRootSamples += RootSamples;
			Require(Current->GetCharacterMovement()->RotationRate.Yaw < 0 || FMath::Abs(Steering) <= Current->GetCharacterMovement()->RotationRate.Yaw * Dt + AngleTolerance, TEXT("Natural end respects the ordinary CMC rotation rate"));
			NormalConverged |= Error <= AngleTolerance;
		}
		auto* Anim = Current->GetMesh()->GetAnimInstance(); UAnimMontage* Montage = Anim->GetCurrentActiveMontage();
		const FVector Target = Player->GetActorLocation(); const FName Node = Ability.IsValid() && Ability->IsActive() ? Ability->GetCurrentNodeId() : NAME_None;
		Trace += FString::Printf(TEXT("%s,%d,%.6f,%.6f,%s,%s,%d,%s,%.6f,%.3f,%.3f,%.3f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%d,%d,%d,%.3f,%d,%d,%d,%s,%s,%.6f,%.6f\n"),
			*Current->GetClass()->GetName(), AttackIndex, World->GetTimeSeconds(), Dt, *BeforeNode.ToString(), *Node.ToString(), BeforeNode != Node, *Anim->Montage_GetCurrentSection(Montage).ToString(), Montage ? Anim->Montage_GetPosition(Montage) : 0.f,
			Target.X, Target.Y, Target.Z, TargetYaw(), BeforeControlYaw, AI->GetControlRotation().Yaw, BeforeDesiredYaw, AI->GetDesiredRotation().Yaw, Before.Rotator().Yaw, After.Rotator().Yaw, FrameRoot.Rotator().Yaw, Steering, BeforeError, Error, bApproaching, bPreparing, RootSamples, Current->GetCharacterMovement()->RotationRate.Yaw,
			PhysicsPhaseValid, PhysicsApproaching, PhysicsPreparing, *PhysicsNode.ToString(), *PhysicsSection.ToString(), PhysicsPosition, PhysicsPlayRate);
	}
	void ReleaseObserver()
	{
		if (ObservedCMC.IsValid()) ObservedCMC->ProcessRootMotionPostConvertToWorld = SavedRootObserver;
		ObservedCMC.Reset(); SavedRootObserver.Unbind();
	}
	void Restore()
	{
		if (PreHandle.IsValid()) { FWorldDelegates::OnWorldPreActorTick.Remove(PreHandle); PreHandle.Reset(); }
		if (PostHandle.IsValid()) { FWorldDelegates::OnWorldPostActorTick.Remove(PostHandle); PostHandle.Reset(); }
		ReleaseObserver();
		if (!Trace.IsEmpty())
		{
			const FString Folder = FPaths::ProjectSavedDir() / TEXT("MonsterAI"); IFileManager::Get().MakeDirectory(*Folder, true);
			FFileHelper::SaveStringToFile(Trace, *(Folder / TEXT("FacingPIE.csv")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM); Trace.Reset();
		}
		if (Player.IsValid()) Player->SetActorTransform(SavedPlayer, false, nullptr, ETeleportType::TeleportPhysics);
		for (int32 I = 0; I < All.Num(); ++I) if (All[I].IsValid() && Controllers[I].IsValid())
		{
			Controllers[I]->UnPossess(); All[I]->SetActorTransform(SavedMonsters[I], false, nullptr, ETeleportType::TeleportPhysics);
			Controllers[I]->GetPerceptionComponent()->ForgetAll(); Controllers[I]->Possess(All[I].Get()); Controllers[I]->GetPerceptionComponent()->Activate();
		}
		All.Reset(); Controllers.Reset();
	}
	FAutomationTestBase* Test; double Deadline, Next = 0, PatternDeadline = 0, NextTargetChange = 0, NodeStarted = 0, NormalStarted = 0;
	TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<AKZMonster> Current; TWeakObjectPtr<AKZMonsterAIController> AI; TWeakObjectPtr<UKZComboActionAbility> Ability;
	TArray<TWeakObjectPtr<AKZMonster>> All, Selected; TArray<TWeakObjectPtr<AKZMonsterAIController>> Controllers; TArray<FTransform> SavedMonsters; FTransform SavedPlayer;
	TWeakObjectPtr<UCharacterMovementComponent> ObservedCMC; FOnProcessRootMotion SavedRootObserver; FDelegateHandle PreHandle, PostHandle; FGameplayAbilitySpecHandle Active;
	FString Trace; TSet<FString> Errors; TSet<FName> Expected, Seen; FName LastNode, BeforeNode, PhysicsNode, PhysicsSection;
	FQuat Before = FQuat::Identity, FrameRoot = FQuat::Identity; float Bearing = 0, BaseBearing = 0, BeforeTargetYaw = 0, BeforeError = 0;
	float BeforeControlYaw = 0, BeforeDesiredYaw = 0;
	float PhysicsPosition = 0, PhysicsPlayRate = 0;
	float TrackingRate = 0, ReaimRate = 0, Preparation = 0; double ObservedRootYaw = 0;
	int32 Index = 0, Stage = 0, AttackIndex = 0, TotalPatterns = 0, RootSamples = 0, PatternRootSamples = 0, PatternFrames = 0, NormalRootSamples = 0;
	bool SawWrap = false, SawSlowTracking = false, SawFastTracking = false, bOffset = false, WasApproaching = false, bApproaching = false, bPreparing = false, bHaveFrame = false, ExpectedRootYaw = false, NormalConverged = false;
	bool PhysicsPhaseValid = false, PhysicsApproaching = false, PhysicsPreparing = false;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterFacingPIETest, "Khazan.Monster.FacingPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterFacingPIETest::RunTest(const FString& Parameters)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FMonsterFacingPIE>(this)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterCombatPolicyPIETest, "Khazan.Monster.CombatPolicyPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterCombatPolicyPIETest::RunTest(const FString& Parameters)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FMonsterCombatPolicyPIE>(this)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterPIETest, "Khazan.Monster.PIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterPIETest::RunTest(const FString& Parameters)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForMonsterPIE>(this)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterHalberdPIETest, "Khazan.Monster.HalberdPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterHalberdPIETest::RunTest(const FString& Parameters)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForMonsterPIE>(this, true)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterAttackPatternsTest, "Khazan.Monster.AttackPatternsPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterAttackPatternsTest::RunTest(const FString& Parameters)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForMonsterPIE>(this, false, true)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterWaitingTest, "Khazan.Monster.WaitingPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterWaitingTest::RunTest(const FString& Parameters)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FMonsterWaitingPIE>(this)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterSourceAudit, "Khazan.Monster.SourceAnimationAudit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterSourceAudit::RunTest(const FString& Parameters)
{
	if (!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_MonsterWork_20261006"))) return false;
	// Read immutable before packages under a temporary mount; never save the baseline.
	const FString Mount = TEXT("/MonsterMainAudit/");
	const FString MainContent = TEXT("C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/EnemyAnimationOrganization_20261007/Before/Content/");
	FPackageName::RegisterMountPoint(Mount, MainContent);
	TArray<FString> Pairs;
	FFileHelper::LoadFileToStringArray(Pairs, *FPaths::Combine(FPaths::ProjectDir(), TEXT("Saved/EnemyAnimationOrganization/AssetPairs.tsv")));
	int64 TransformCount = 0; int32 Checked = 0;
	for (const FString& Pair : Pairs)
	{
		FString CurrentPath, OldPath;
		if (!Pair.Split(TEXT("|"), &CurrentPath, &OldPath)) { AddError(TEXT("Malformed audit pair")); continue; }
		const FString SourcePath = Mount + OldPath.RightChop(6);
		UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *CurrentPath);
		UAnimSequence* Source = LoadObject<UAnimSequence>(nullptr, *SourcePath);
		if (!TestNotNull(TEXT("Current sequence is readable"), Clip) || !TestNotNull(TEXT("Before sequence is readable"), Source)) continue;
		Source->GetOutermost()->SetFlags(RF_Transient); Source->GetOutermost()->SetDirtyFlag(false);
		const IAnimationDataModel* A = Clip->GetDataModel(); const IAnimationDataModel* B = Source->GetDataModel();
		TestEqual(TEXT("Frame count is preserved"), A->GetNumberOfKeys(), B->GetNumberOfKeys());
		TestEqual(TEXT("Sample rate is preserved"), A->GetFrameRate(), B->GetFrameRate());
		TestEqual(TEXT("RateScale is preserved"), Clip->RateScale, Source->RateScale);
		TestEqual(TEXT("Float curve count is preserved"), A->GetFloatCurves().Num(), B->GetFloatCurves().Num());
		for (int32 Index = 0; Index < FMath::Min(A->GetFloatCurves().Num(), B->GetFloatCurves().Num()); ++Index)
			TestTrue(TEXT("Float curve keys and flags are preserved"), FFloatCurve::StaticStruct()->CompareScriptStruct(&A->GetFloatCurves()[Index], &B->GetFloatCurves()[Index], 0));
		TestEqual(TEXT("Transform curve count is preserved"), A->GetTransformCurves().Num(), B->GetTransformCurves().Num());
		for (int32 Index = 0; Index < FMath::Min(A->GetTransformCurves().Num(), B->GetTransformCurves().Num()); ++Index)
			TestTrue(TEXT("Transform curves are preserved"), FTransformCurve::StaticStruct()->CompareScriptStruct(&A->GetTransformCurves()[Index], &B->GetTransformCurves()[Index], 0));
		TestEqual(TEXT("Attribute count is preserved"), A->GetAttributes().Num(), B->GetAttributes().Num());
		for (const TCHAR* Name : {TEXT("AuthoredSyncMarkers"), TEXT("AdditiveAnimType"), TEXT("RefPoseType"), TEXT("RefFrameIndex"), TEXT("Interpolation"), TEXT("BoneCompressionSettings"), TEXT("CurveCompressionSettings")})
		{
			const FProperty* Property = FindFProperty<FProperty>(Clip->GetClass(), Name);
			TestTrue(FString(TEXT("Sequence metadata is preserved: ")) + Name, Property && Property->Identical_InContainer(Clip, Source));
		}
		TestEqual(TEXT("Notify count is preserved"), Clip->Notifies.Num(), Source->Notifies.Num());
		for (int32 Index = 0; Index < FMath::Min(Clip->Notifies.Num(), Source->Notifies.Num()); ++Index)
		{
			TestEqual(TEXT("Notify name is preserved"), Clip->Notifies[Index].NotifyName, Source->Notifies[Index].NotifyName);
			TestEqual(TEXT("Notify timing is preserved"), Clip->Notifies[Index].GetTime(), Source->Notifies[Index].GetTime());
			TestEqual(TEXT("Notify duration is preserved"), Clip->Notifies[Index].GetDuration(), Source->Notifies[Index].GetDuration());
		}
		TArray<FName> Names, CurrentNames; B->GetBoneTrackNames(Names); A->GetBoneTrackNames(CurrentNames);
		TestTrue(TEXT("Track names and order are preserved"), Names == CurrentNames);
		double MaxPosition = 0, MaxAngle = 0, MaxScale = 0;
		for (FName Bone : Names)
		{
			TArray<FTransform> Actual, Original; A->GetBoneTrackTransforms(Bone, Actual); B->GetBoneTrackTransforms(Bone, Original);
			TestEqual(TEXT("Bone key count is preserved"), Actual.Num(), Original.Num());
			for (int32 Key = 0; Key < FMath::Min(Actual.Num(), Original.Num()); ++Key)
			{
				MaxPosition = FMath::Max(MaxPosition, FVector::Distance(Actual[Key].GetTranslation(), Original[Key].GetTranslation()));
				MaxAngle = FMath::Max(MaxAngle, Actual[Key].GetRotation().GetNormalized().AngularDistance(Original[Key].GetRotation().GetNormalized()));
				MaxScale = FMath::Max(MaxScale, FVector::Distance(Actual[Key].GetScale3D(), Original[Key].GetScale3D())); ++TransformCount;
			}
		}
		TestTrue(TEXT("All raw poses are unchanged"), MaxPosition < 1.e-6 && MaxAngle < 1.e-6 && MaxScale < 1.e-6);
		TestTrue(TEXT("Requested Root Motion policy is enabled"), Clip->bEnableRootMotion && Clip->bForceRootLock && Clip->RootMotionRootLock == ERootMotionRootLock::AnimFirstFrame);
		for (float Fraction : {0.f, 0.5f, 1.f})
		{
			const float Time = Fraction * Source->GetPlayLength();
			const FAnimExtractContext Extraction(Time);
			const FTransform Actual = Clip->ExtractRootTrackTransform(Extraction, nullptr);
			const FTransform Original = Source->ExtractRootTrackTransform(Extraction, nullptr);
			// Compressed samples can differ from raw source by codec precision. Raw keys are checked above.
			// Observed codec resampling error <= 0.0061 cm; this is QA precision, not a gameplay value.
			TestTrue(TEXT("Engine root extraction preserves displacement within 0.01 cm"), FVector::Distance(Actual.GetTranslation(), Original.GetTranslation()) < 0.01);
			TestTrue(TEXT("Engine root extraction preserves rotation and scale"), Actual.GetRotation().GetNormalized().AngularDistance(Original.GetRotation().GetNormalized()) < 1.e-4 && Actual.GetScale3D().Equals(Original.GetScale3D(), 1.e-6));
		}
		++Checked;
		AddInfo(FString::Printf(TEXT("AnimationSourceAudit %s keys=%d bones=%d position=%.9f rotationRad=%.9f scale=%.9f"), *Clip->GetName(), B->GetNumberOfKeys(), Names.Num(), MaxPosition, MaxAngle, MaxScale));
	}
	FPackageName::UnRegisterMountPoint(Mount, MainContent);
	TestTrue(TEXT("Audit input contains target sequences"), Pairs.Num() > 0);
	TestEqual(TEXT("All selected sequences were inspected"), Checked, Pairs.Num());
	AddInfo(FString::Printf(TEXT("AnimationSourceAuditTotal sequences=%d rawTransforms=%lld"), Checked, TransformCount));
	return !HasAnyErrors();
}
#endif
