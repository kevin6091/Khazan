#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "AI/KZMonsterAIController.h"
#include "Character/KZMonster.h"
#include "KZGameplayTags.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Character/KZCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffect.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/RootMotionSource.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#include "LogChannels.h"

UKZMonsterPatternAbility::UKZMonsterPatternAbility()
{
	FGameplayTagContainer Tags; Tags.AddTag(KZGameplayTags::Ability_Action_Attack); SetAssetTags(Tags);
}

void UKZMonsterPatternAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
	PendingNextNode = NAME_None;
	++PatternRun;
	bNodeHitObserved = bPendingHitEvent = false; bPendingStepStart = true;
	ActionCounts.Reset();PendingCapture.Reset();
	const FKZComboNode* Entry = GetComboDefinition() ? GetComboDefinition()->FindNode(GetEntryNodeId()) : nullptr;
	ExecutingSkill = Entry ? Entry->PatternSkill : NAME_None;
	Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData);
	if (!IsActive()) return;
	BoundMonster = Cast<AKZMonster>(GetAvatarActorFromActorInfo());
	if (AKZMonster* Monster = BoundMonster.Get()) Monster->OnActorHit.AddUniqueDynamic(this, &ThisClass::HandleWorldCollision);
	PatternTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &ThisClass::TickPattern);
}

void UKZMonsterPatternAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
	if (UWorld* World = GetWorld()) World->GetTimerManager().ClearTimer(PatternTimer);
	ClearPatternMovement();
	ReleaseCapture();PendingCapture.Reset();ActionCounts.Reset();
	for(auto Object:SkillObjects)if(Object.IsValid() && (bWasCancelled || Object->ShouldEndWithAbility()))Object->Destroy();
	SkillObjects.Reset();
	if (AKZMonster* Monster = BoundMonster.Get())
	{
		Monster->OnActorHit.RemoveDynamic(this, &ThisClass::HandleWorldCollision);
		if (AKZMonsterAIController* AI = Cast<AKZMonsterAIController>(Monster->GetController()))
			if (!ExecutingSkill.IsNone()) AI->RecordPatternFinished(ExecutingSkill);
	}
	BoundMonster.Reset(); PendingNextNode = NAME_None; ExecutingSkill = NAME_None;
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}

bool UKZMonsterPatternAbility::EnterPatternNode(FName NodeId)
{
	if (NodeId == TEXT("PatternFinish")) { FinishAbility(false); return true; }
	const FKZComboNode* Node = GetComboDefinition()->FindNode(NodeId);
	if (!Node) return false;
	ClearPatternMovement();
	if (!TransitionToNode(NodeId)) return false;
	if (ExecutingSkill != Node->PatternSkill)
	{
		ReleaseCapture();
		if (AKZMonster* Monster = BoundMonster.Get())
			if (AKZMonsterAIController* AI = Cast<AKZMonsterAIController>(Monster->GetController())) AI->RecordPatternFinished(ExecutingSkill);
		ExecutingSkill = Node->PatternSkill;
	}
	PendingNextNode = NAME_None;
	bNodeHitObserved = bPendingHitEvent = false; bPendingStepStart = true;
	ActionCounts.Reset();
	if(Node->PatternSkill==TEXT("RushGrab") && NodeId==TEXT("RushGrab_Step2"))ReleaseCapture();
	return true;
}

bool UKZMonsterPatternAbility::ResolveEvent(EKZPatternEvent Event, FName Notify)
{
	AKZMonster* Monster = BoundMonster.Get();
	AKZMonsterAIController* AI = Monster ? Cast<AKZMonsterAIController>(Monster->GetController()) : nullptr;
	const FKZComboNode* Node = GetComboDefinition() ? GetComboDefinition()->FindNode(GetCurrentNodeId()) : nullptr;
	if (!IsActive() || !Node || !AI) return false;
	TArray<const FKZMonsterPatternBranch*> Candidates;
	float Total = 0.f;
	const float Time = NodeTime();
	for (const FKZMonsterPatternBranch& Branch : Node->PatternBranches)
	{
		if (Branch.Event != Event || (Event == EKZPatternEvent::Animation && Branch.Notify != Notify) ||
			Branch.Weight <= 0.f || (Branch.bRequireConfirmedHit && !bNodeHitObserved) ||
			(!Branch.ActiveWindows.IsEmpty() && !Branch.ActiveWindows.ContainsByPredicate([Time](const FVector2D& W){return Time>=W.X && Time<=W.Y;})) ||
			Branch.Conditions.ContainsByPredicate([Monster, AI](const auto& Condition) { return !Condition.Matches(Monster, AI->GetBattleTarget()); })) continue;
		const FKZComboNode* Destination = GetComboDefinition()->FindNode(Branch.TargetNode);
		if ((!Destination && Branch.TargetNode!=TEXT("PatternFinish")) || (Branch.bCheckCooldown && Destination && !AI->IsPatternReady(Destination->PatternSkill))) continue;
		if (Branch.Probability<1.f && FMath::FRand()>=Branch.Probability) continue;
		Candidates.Add(&Branch); Total += Branch.Weight;
	}
	if (Candidates.IsEmpty()) return false;
	float Draw = FMath::FRand() * Total;
	const FKZMonsterPatternBranch* Selected = Candidates.Last();
	for (const auto* Branch : Candidates) { Draw -= Branch->Weight; if (Draw < 0.f) { Selected = Branch; break; } }
	if (Selected->bDeferUntilStepEnd) { PendingNextNode = Selected->TargetNode; return true; }
	return EnterPatternNode(Selected->TargetNode);
}

void UKZMonsterPatternAbility::ProcessMontageNotify(FName Notify)
{
	const FString Prefix=TEXT("Pattern_")+GetCurrentNodeId().ToString()+TEXT("_");
	if (Notify == *FString(TEXT("PatternNext_")+GetCurrentNodeId().ToString()))
	{
		const FName Previous=GetCurrentNodeId();
		ResolveEvent(EKZPatternEvent::Animation, TEXT("Pattern_EndSubState"));
		if(!IsActive() || GetCurrentNodeId()!=Previous)return;
		const FKZComboNode* Node = GetComboDefinition()->FindNode(GetCurrentNodeId());
		const FName Next = PendingNextNode.IsNone() && Node ? Node->AutomaticNextNode : PendingNextNode;
		if (!Next.IsNone()) EnterPatternNode(Next);
		else FinishAbility(false);
		return;
	}
	if (Notify.ToString().StartsWith(Prefix)) { RunActions(EKZPatternEvent::Animation,Notify); ResolveEvent(EKZPatternEvent::Animation, Notify); return; }
	if (Notify.ToString().StartsWith(TEXT("Pattern"))) return; // stale marker crossed by a section jump
	Super::ProcessMontageNotify(Notify);
}

void UKZMonsterPatternAbility::ReportPatternEvent(EKZPatternEvent Event) { if(IsActive()) ResolveEvent(Event); }

void UKZMonsterPatternAbility::RegisterSkillObject(AKZMonsterSkillObject* Object,uint32 Run)
{
	if(IsActive() && Run==PatternRun && Object)SkillObjects.AddUnique(Object);
}

float UKZMonsterPatternAbility::NodeTime() const
{
	const FKZComboNode* Node=GetComboDefinition()?GetComboDefinition()->FindNode(GetCurrentNodeId()):nullptr;
	UAnimInstance* Anim=GetCurrentActorInfo()?GetCurrentActorInfo()->GetAnimInstance():nullptr;
	if(!Node || !Node->Montage || !Anim) return -1.f;
	const int32 Section=Node->Montage->GetSectionIndex(Node->SectionName);
	return Section==INDEX_NONE?-1.f:Anim->Montage_GetPosition(Node->Montage)-Node->Montage->CompositeSections[Section].GetTime();
}

void UKZMonsterPatternAbility::RecordAcceptedAttackHit(AActor* Target,float MontageTime)
{
	AKZMonster* Monster=BoundMonster.Get();auto* AI=Monster?Cast<AKZMonsterAIController>(Monster->GetController()):nullptr;
	if(AI && Target==AI->GetBattleTarget())
	{
		bNodeHitObserved=true;bPendingHitEvent=true;
		const FKZComboNode* N=GetComboDefinition()->FindNode(GetCurrentNodeId());
		const float T=MontageTime-N->Montage->CompositeSections[N->Montage->GetSectionIndex(N->SectionName)].GetTime();
		if(N->AttackWindows.ContainsByPredicate([T](const auto& W){return W.bBeginsCapture && T>=W.StartTime && T<=W.EndTime;}))PendingCapture=Cast<AKZCharacter>(Target);
	}
}

void UKZMonsterPatternAbility::TickPattern()
{
	if (!IsActive()) return;
	if(PendingCapture.IsValid()){BeginCapture(PendingCapture.Get(),TEXT("Weapon_L"));PendingCapture.Reset();}
	if(bPendingStepStart){bPendingStepStart=false;RunActions(EKZPatternEvent::StepStart);ResolveEvent(EKZPatternEvent::StepStart);}
	if(bPendingHitEvent){bPendingHitEvent=false;RunActions(EKZPatternEvent::ConfirmedHit);ResolveEvent(EKZPatternEvent::ConfirmedHit);}
	if(CapturedTarget.IsValid())
	{
		if(CapturePhysics && BoundMonster.IsValid())CapturePhysics->SetTargetLocationAndRotation(BoundMonster->GetMesh()->GetSocketLocation(TEXT("Weapon_L")),BoundMonster->GetMesh()->GetSocketRotation(TEXT("Weapon_L")));
		ResolveEvent(EKZPatternEvent::HoldingSuccess);
	}
	RunActions(EKZPatternEvent::Tick);
	ResolveEvent(EKZPatternEvent::Tick);
	if(IsActive())UpdatePatternMovement();
	if (IsActive()) PatternTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &ThisClass::TickPattern);
}

void UKZMonsterPatternAbility::RunActions(EKZPatternEvent Event,FName Notify)
{
	AKZMonster* Monster=BoundMonster.Get();auto* AI=Monster?Cast<AKZMonsterAIController>(Monster->GetController()):nullptr;
	const FKZComboNode* Node=GetComboDefinition()?GetComboDefinition()->FindNode(GetCurrentNodeId()):nullptr;
	if(!IsActive() || !Node || !AI || !AI->GetBattleTarget())return;
	const FName NodeId=GetCurrentNodeId();
	for(int32 Index=0;Index<Node->PatternActions.Num() && IsActive() && GetCurrentNodeId()==NodeId;++Index)
	{
		const auto& A=Node->PatternActions[Index];int32& Count=ActionCounts.FindOrAdd(Index);
		if(A.Event!=Event || Count>=A.MaxCount || (Event==EKZPatternEvent::Animation && A.Notify!=Notify))continue;
		const float Time=NodeTime();
		const FVector2D* ActiveWindow=A.ActiveWindows.FindByPredicate([Time](const auto& W){return Time>=W.X && Time<=W.Y;});
		// A matching montage marker already supplies the exact start event. Subtracting
		// a late section's float start can round just below its local window boundary.
		if(Event!=EKZPatternEvent::Animation && !A.ActiveWindows.IsEmpty() && !ActiveWindow)continue;
		if(Event==EKZPatternEvent::Tick && (A.Interval<=0.f || Time<(ActiveWindow?ActiveWindow->X:0.f)+(Count+1)*A.Interval))continue;
		++Count;
		UE_LOG(LogAbility,Verbose,TEXT("PatternAction owner=%s node=%s notify=%s action=%d time=%g objects=%d"),*Monster->GetName(),*NodeId.ToString(),*Notify.ToString(),int32(A.Action),Time,SkillObjects.Num());
		if(A.Action==EKZPatternAction::AddCooldown){AI->AddPatternCooldown(A.TargetSkill,A.CooldownSeconds);continue;}
		if(A.Action==EKZPatternAction::DestroyObjects){const auto Objects=SkillObjects;for(auto Object:Objects)if(Object.IsValid())Object->TriggerDestruction();continue;}
		if(A.Action==EKZPatternAction::Capture){if(bNodeHitObserved)BeginCapture(Cast<AKZCharacter>(AI->GetBattleTarget()),A.Socket);continue;}
		if(A.Action==EKZPatternAction::DirectDamage)
		{
			AKZCharacter* Victim=CapturedTarget.Get();if(!Victim)continue;
			FGameplayEffectContextHandle Context=GetAbilitySystemComponentFromActorInfo()->MakeEffectContext();Context.AddSourceObject(this);
			const auto Spec=GetAbilitySystemComponentFromActorInfo()->MakeOutgoingSpec(GetComboDefinition()->GetAttackDamageEffect(),1.f,Context);
			if(Spec.IsValid()){Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),-A.HPDamage);Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")),-A.StaminaDamage);GetAbilitySystemComponentFromActorInfo()->ApplyGameplayEffectSpecToTarget(*Spec.Data.Get(),Victim->GetAbilitySystemComponent());}
			continue;
		}
		const auto* Definition=GetComboDefinition()->GetPatternObjects().FindByPredicate([&A](const auto& O){return O.Id==A.ObjectId;});
		if(!Definition)continue;
		if(A.Action==EKZPatternAction::ShootObject)
		{
			for(auto Object:SkillObjects)if(Object.IsValid() && Object->GetObjectId()==A.ObjectId && !Object->HasLaunched())Object->Shoot(AI->GetBattleTarget(),A.bFlatAim);
			continue;
		}
		const FName Socket=!A.Socket.IsNone() && !Monster->GetMesh()->DoesSocketExist(A.Socket)?FName(TEXT("Bip001-L-Hand")):A.Socket;
		FTransform Spawn=Monster->GetMesh()->GetSocketTransform(Socket);
		Spawn.AddToTranslation(Spawn.GetRotation().RotateVector(A.Offset));
		if(A.bSpawnOnFloor)
		{
			FHitResult Floor;FCollisionQueryParams Query(SCENE_QUERY_STAT(KZGiantSpawnFloor),false,Monster);
			const FVector Position=Spawn.GetLocation();
			const float Depth=FMath::Max(Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()*2,Monster->GetAISettings().SightRadius);
			const FVector TraceStart(Position.X,Position.Y,Monster->GetActorLocation().Z+Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
			if(GetWorld()->LineTraceSingleByChannel(Floor,TraceStart,TraceStart-FVector(0,0,Depth*2),ECC_Visibility,Query))
				Spawn.SetLocation(Floor.ImpactPoint+FVector(0,0,Definition->bField?Definition->FieldExtent.Z*Definition->Scale:Definition->Radius*Definition->Scale+UE_KINDA_SMALL_NUMBER));
		}
		FActorSpawnParameters Parameters;Parameters.Owner=Monster;Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		auto* Object=GetWorld()->SpawnActor<AKZMonsterSkillObject>(AKZMonsterSkillObject::StaticClass(),Spawn,Parameters);
		if(!Object)continue;
		const auto* Trail=GetComboDefinition()->GetPatternObjects().FindByPredicate([Definition](const auto& O){return O.Id==Definition->TrailObjectId;});
		Object->Initialize(*Definition,GetComboDefinition()->GetAttackDamageEffect(),Monster,this,Trail);
		if(!Definition->bField && Socket!=NAME_None && !Definition->bDestroyOnAbilityEnd)Object->AttachToComponent(Monster->GetMesh(),FAttachmentTransformRules::KeepWorldTransform,Socket);
		else Object->Shoot(AI->GetBattleTarget(),A.bFlatAim);
	}
}

float UKZMonsterPatternAbility::GetNodeTransitionBlendSeconds(const FKZComboNode& Target) const
{
	return Target.PatternBlendSeconds>=0.f?Target.PatternBlendSeconds:Super::GetNodeTransitionBlendSeconds(Target);
}

void UKZMonsterPatternAbility::ClearPatternMovement()
{
	if(AKZMonster* M=BoundMonster.Get())
	{
		if(MovementSourceId)M->GetCharacterMovement()->RemoveRootMotionSourceByID(MovementSourceId);
		if(bOwnsRootMotionMode && M->GetMesh()->GetAnimInstance() && M->GetMesh()->GetAnimInstance()->RootMotionMode==ERootMotionMode::IgnoreRootMotion)
			M->GetMesh()->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::Type(PreviousRootMotionMode));
	}
	MovementSourceId=0;MovementWindow=MovementLoop=INDEX_NONE;bOwnsRootMotionMode=false;
}

void UKZMonsterPatternAbility::UpdatePatternMovement()
{
	AKZMonster* M=BoundMonster.Get();auto* AI=M?Cast<AKZMonsterAIController>(M->GetController()):nullptr;
	const FKZComboNode* N=GetComboDefinition()->FindNode(GetCurrentNodeId());if(!M || !AI || !N || !AI->GetBattleTarget())return;
	const int32 Section=N->Montage->GetSectionIndex(N->SectionName);const FAnimSegment& Segment=N->Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[Section];
	const float Cycle=Segment.GetLength()/FMath::Max(Segment.LoopingCount,1);const float Time=NodeTime();const int32 Loop=FMath::FloorToInt(Time/Cycle);const float LocalTime=FMath::Fmod(Time,Cycle);
	int32 Index=N->PatternMoves.IndexOfByPredicate([LocalTime](const auto& Move){return LocalTime>=Move.Window.X && LocalTime<Move.Window.Y;});
	if(Index==INDEX_NONE){ClearPatternMovement();return;}
	const auto& Move=N->PatternMoves[Index];
	if(Move.StopDistance>0.f && FVector::Dist2D(M->GetActorLocation(),AI->GetBattleTarget()->GetActorLocation())<=Move.StopDistance)
	{const FName Next=N->AutomaticNextNode;ClearPatternMovement();if(!Next.IsNone())EnterPatternNode(Next);return;}
	if(MovementWindow==Index && MovementLoop==Loop)return;
	ClearPatternMovement();MovementWindow=Index;MovementLoop=Loop;
	FVector Local=Move.Destination;
	if(Move.bTraceTarget && Move.TargetMax>0.f)Local.X=FMath::Sign(Local.X)*FMath::Clamp(float(FVector::Dist2D(M->GetActorLocation(),AI->GetBattleTarget()->GetActorLocation()))-Move.TargetOffset,Move.TargetMin,Move.TargetMax);
	const FRotator Rotation=Move.bTraceTarget?(AI->GetBattleTarget()->GetActorLocation()-M->GetActorLocation()).Rotation():M->GetActorRotation();
	TSharedPtr<FRootMotionSource_MoveToDynamicForce> Source=MakeShared<FRootMotionSource_MoveToDynamicForce>();
	Source->InstanceName=TEXT("OriginalPatternMoveTo");Source->Priority=1000; // Engine AbilityTask root-motion priority, not original tuning.
	Source->AccumulateMode=ERootMotionAccumulateMode::Override;Source->StartLocation=M->GetActorLocation();Source->TargetLocation=Source->StartLocation+FRotator(0,Rotation.Yaw,0).RotateVector(Local);
	Source->InitialTargetLocation=Source->TargetLocation;Source->Duration=Move.Window.Y-LocalTime;Source->TimeMappingCurve=Move.TimeCurve;Source->PathOffsetCurve=Move.OffsetCurve;
	Source->FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::SetVelocity;Source->FinishVelocityParams.SetVelocity=FVector::ZeroVector;
	if(auto* Anim=M->GetMesh()->GetAnimInstance()){PreviousRootMotionMode=Anim->RootMotionMode;bOwnsRootMotionMode=true;Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);}
	MovementSourceId=M->GetCharacterMovement()->ApplyRootMotionSource(Source);
}

bool UKZMonsterPatternAbility::BeginCapture(AKZCharacter* Victim,FName Socket)
{
	AKZMonster* Monster=BoundMonster.Get();
	if(CapturedTarget.IsValid())return CapturedTarget==Victim;
	if(!IsActive() || !Monster || !Victim || !CaptureEffect || !Victim->GetAbilitySystemComponent())return false;
	UAbilitySystemComponent* ASC=Victim->GetAbilitySystemComponent();
	if(ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) || ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted))return false;
	FGameplayTagContainer CancelTags;CancelTags.AddTag(KZGameplayTags::Ability_Action);CancelTags.AddTag(KZGameplayTags::Ability_Reaction_Hit);
	ASC->CancelAbilities(&CancelTags);
	FGameplayEffectContextHandle Context=GetAbilitySystemComponentFromActorInfo()->MakeEffectContext();Context.AddSourceObject(this);
	const FGameplayEffectSpecHandle Spec=GetAbilitySystemComponentFromActorInfo()->MakeOutgoingSpec(CaptureEffect,1.f,Context);
	if(!Spec.IsValid())return false;
	CaptureEffectHandle=ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
	if(!CaptureEffectHandle.IsValid())return false;
	CapturedTarget=Victim;CapturedMovementMode=Victim->GetCharacterMovement()->MovementMode;Victim->GetCharacterMovement()->DisableMovement();
	if(!Monster->GetMesh()->DoesSocketExist(Socket))Socket=TEXT("Bip001-L-Hand");
	bAddedVictimIgnore=!Victim->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Monster);
	bAddedCasterIgnore=!Monster->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(Victim);
	if(bAddedVictimIgnore)Victim->GetCapsuleComponent()->IgnoreActorWhenMoving(Monster,true);
	if(bAddedCasterIgnore)Monster->GetCapsuleComponent()->IgnoreActorWhenMoving(Victim,true);
	CaptureOriginalParent=Victim->GetRootComponent()->GetAttachParent();CaptureOriginalSocket=Victim->GetRootComponent()->GetAttachSocketName();
	const FKZComboNode* Node=GetComboDefinition()->FindNode(GetCurrentNodeId());
	const auto* Capture=Node?Node->PatternActions.FindByPredicate([](const auto& Action){return Action.Action==EKZPatternAction::Capture;}):nullptr;
	const FName TargetSocket=Capture && Victim->GetMesh()->DoesSocketExist(Capture->CaptureTargetSocket)?Capture->CaptureTargetSocket:FName(TEXT("Bip001-Spine"));
	const FVector SpineOffset=Victim->GetMesh()->DoesSocketExist(TargetSocket)?Victim->GetMesh()->GetSocketLocation(TargetSocket)-Victim->GetActorLocation():FVector::ZeroVector;
	Victim->AttachToComponent(Monster->GetMesh(),FAttachmentTransformRules::SnapToTargetNotIncludingScale,Socket);
	Victim->AddActorWorldOffset(-SpineOffset);
	if(Capture && !Capture->RagdollBone.IsNone() && Victim->GetMesh()->GetPhysicsAsset() && !Victim->GetMesh()->IsAnySimulatingPhysics())
	{
		// Engine physics-handle adapter for original HoldAttachInfo.RagdollInfo.
		// Keep the current imported physics asset; the original FallDown asset is not mapped.
		CaptureMeshRelativeTransform=Victim->GetMesh()->GetRelativeTransform();CapturedRagdollBone=Capture->RagdollBone;
		Victim->GetMesh()->SetAllBodiesBelowSimulatePhysics(CapturedRagdollBone,true,true);
		Victim->GetMesh()->SetAllBodiesBelowPhysicsBlendWeight(CapturedRagdollBone,Capture->PhysicsBlendWeight,false,true);
		const FName BodyBone=Victim->GetMesh()->GetSocketBoneName(TargetSocket);
		if(Victim->GetMesh()->IsSimulatingPhysics(BodyBone))
		{
			CapturePhysics=NewObject<UPhysicsHandleComponent>(Monster);CapturePhysics->RegisterComponent();
			CapturePhysics->GrabComponentAtLocationWithRotation(Victim->GetMesh(),BodyBone,Monster->GetMesh()->GetSocketLocation(Socket),Monster->GetMesh()->GetSocketRotation(Socket));
		}
	}
	ResolveEvent(EKZPatternEvent::HoldingSuccess);return true;
}

void UKZMonsterPatternAbility::ReleaseCapture()
{
	AKZCharacter* Victim=CapturedTarget.Get();AKZMonster* Monster=BoundMonster.Get();CapturedTarget.Reset();
	if(CapturePhysics){CapturePhysics->ReleaseComponent();CapturePhysics->DestroyComponent();CapturePhysics=nullptr;}
	if(!Victim)return;
	if(!CapturedRagdollBone.IsNone())
	{
		Victim->GetMesh()->SetAllBodiesBelowSimulatePhysics(CapturedRagdollBone,false,true);
		Victim->GetMesh()->SetAllBodiesBelowPhysicsBlendWeight(CapturedRagdollBone,0.f,false,true);
		Victim->GetMesh()->SetRelativeTransform(CaptureMeshRelativeTransform);CapturedRagdollBone=NAME_None;
	}
	Victim->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	if(CaptureOriginalParent.IsValid())Victim->AttachToComponent(CaptureOriginalParent.Get(),FAttachmentTransformRules::KeepWorldTransform,CaptureOriginalSocket);
	CaptureOriginalParent.Reset();CaptureOriginalSocket=NAME_None;
	if(auto* ASC=Victim->GetAbilitySystemComponent())
	{
		ASC->RemoveActiveGameplayEffect(CaptureEffectHandle);
		if(!ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) && Victim->GetCharacterMovement()->MovementMode==MOVE_None)
			Victim->GetCharacterMovement()->SetMovementMode(EMovementMode(CapturedMovementMode));
	}
	CaptureEffectHandle.Invalidate();
	if(Monster){if(bAddedVictimIgnore)Victim->GetCapsuleComponent()->IgnoreActorWhenMoving(Monster,false);if(bAddedCasterIgnore)Monster->GetCapsuleComponent()->IgnoreActorWhenMoving(Victim,false);}
	bAddedVictimIgnore=bAddedCasterIgnore=false;
}

void UKZMonsterPatternAbility::HandleWorldCollision(AActor* Self, AActor* Other, FVector Impulse, const FHitResult& Hit)
{
	if (Other && !Other->IsA<APawn>()) ResolveEvent(EKZPatternEvent::Collision);
}
