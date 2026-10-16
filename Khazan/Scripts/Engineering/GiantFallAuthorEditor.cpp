// Exact source plan -> existing GAS/StateTree assets. Private authoring only.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "Ability/PlayerAbility/KZFallAbility.h"
#include "Character/KZPlayer.h"
#include "Engine/StaticMeshActor.h"
#include "GameFramework/PlayerStart.h"
#include "Components/StaticMeshComponent.h"
#include "InputMappingContext.h"
#include "InputAction.h"
#include "GameplayEffect.h"
#include "Curves/CurveVector.h"
#include "Curves/CurveFloat.h"
#include "GameplayEffectComponents/BlockAbilityTagsGameplayEffectComponent.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"

namespace KZGiantFallAuthor
{
TMap<FName,FName> CoincidentNotifyAliases;
using namespace KZMonsterAuthor;
using J = TSharedPtr<FJsonObject>;
double Number(J Object, const TCHAR* Field, double Default = 0) { double V; return Object && Object->TryGetNumberField(Field,V) ? V : Default; }
FString String(J Object, const TCHAR* Field, const FString& Default = TEXT("")) { FString V; return Object && Object->TryGetStringField(Field,V) ? V : Default; }
bool Bool(J Object, const TCHAR* Field, bool Default = false) { bool V; return Object && Object->TryGetBoolField(Field,V) ? V : Default; }
FVector Vector(J P){return FVector(Number(P,TEXT("X")),Number(P,TEXT("Y")),Number(P,TEXT("Z")));}
FKZAttackCollisionWindow Collision(J W)
{
	FKZAttackCollisionWindow Result;Result.StartTime=Number(W,TEXT("start"));Result.EndTime=Number(W,TEXT("end"));Result.HitGroup=*String(W,TEXT("group"));
	const FString Shape=String(W,TEXT("shape"));Result.Shape=Shape==TEXT("Cylinder")?EKZAttackCollisionShape::Cylinder:Shape==TEXT("Sphere")?EKZAttackCollisionShape::Sphere:EKZAttackCollisionShape::Box;
	Result.Extent=Vector(W->GetObjectField(TEXT("extent")));Result.HPDamage=Number(W,TEXT("hp"));Result.StaminaDamage=Number(W,TEXT("stamina"));Result.bBlockable=Bool(W,TEXT("blockable"));
	Result.bBeginsCapture=Bool(W,TEXT("capture"));Result.HitReaction=Result.bBeginsCapture?EKZHitReactionType::None:EKZHitReactionType::Short;
	Result.Source=String(W,TEXT("source"))+TEXT("; baked model cm; editable existing project absolute damage policy, not original damage scale");
	for(const auto& KV:W->GetArrayField(TEXT("keys")))
	{J K=KV->AsObject(),R=K->GetObjectField(TEXT("rotation"));FKZAttackCollisionKey Key;Key.Time=Number(K,TEXT("time"));Key.Center=Vector(K->GetObjectField(TEXT("center")));Key.Rotation=FRotator(Number(R,TEXT("Pitch")),Number(R,TEXT("Yaw")),Number(R,TEXT("Roll")));Result.Keys.Add(Key);}
	return Result;
}
FKZCombatPatternCondition Gate(J P)
{
	FKZCombatPatternCondition C;
	C.MinDistance=Number(P,TEXT("min")); C.MaxDistance=Number(P,TEXT("max"));
	C.BaseYaw=Number(P,TEXT("yaw")); C.LeftYaw=Number(P,TEXT("left"),180); C.RightYaw=Number(P,TEXT("right"),180);
	C.MinHeight=Number(P,TEXT("height_min"),-1.e9); C.MaxHeight=Number(P,TEXT("height_max"),1.e9);
	C.bInvertTarget=Bool(P,TEXT("invert"));
	C.WallCheckYaw=Number(P,TEXT("wall_angle")); C.WallCheckDistance=Number(P,TEXT("wall_distance")); C.bRequireClearWall=Bool(P,TEXT("wall_clear"),true);
	const TArray<TSharedPtr<FJsonValue>>* Statuses;
	if (P->TryGetArrayField(TEXT("statuses"),Statuses)) for (const auto& V:*Statuses)
	{
		J S=V->AsObject(); const FString Type=String(S,TEXT("StatusCheckType"));
		if (Type.EndsWith(TEXT("HealthPoint"))) { C.MaxHP=Number(S,TEXT("Value")); C.bHPIsRatio=Bool(S,TEXT("bCompareRate")); }
		if (Type.EndsWith(TEXT("Stamina"))) C.MinStamina=Number(S,TEXT("Value"));
	}
	return C;
}
void Notify(UAnimMontage* M, float Time, FName Name)
{
	if(M->Notifies.ContainsByPredicate([Time,Name](const FAnimNotifyEvent& E){return E.NotifyName==Name && FMath::IsNearlyEqual(E.GetTime(),Time);}))return;
	// UE permits only one branching point at a timestamp. Source event indices
	// on the same node share its marker, while keeping all actions/conditions.
	FString Prefix,Index;Name.ToString().Split(TEXT("_"),&Prefix,&Index,ESearchCase::CaseSensitive,ESearchDir::FromEnd);
	if(Name.ToString().StartsWith(TEXT("Pattern_")))
		for(const auto& E:M->Notifies)if(E.NotifyName.ToString().StartsWith(Prefix+TEXT("_")) && FMath::IsNearlyEqual(E.GetTime(),Time))
		{CoincidentNotifyAliases.Add(Name,E.NotifyName);return;}
	auto* N=NewObject<UAnimNotify_PlayMontageNotify>(M,NAME_None,RF_Transactional);
	Value<FName>(N,TEXT("NotifyName"))=Name;
	FAnimNotifyEvent E; E.Notify=N; E.NotifyName=Name; E.MontageTickType=EMontageNotifyTickType::BranchingPoint;
	E.Guid=FGuid::NewGuid(); E.Link(M,Time); M->Notifies.Add(E);
}
void Finalize(UAnimMontage* M, FSlotAnimationTrack& Track, float Length, float Blend)
{
	M->SlotAnimTracks={Track}; M->BlendIn.SetBlendTime(Blend); M->BlendOut.SetBlendTime(Blend);
	M->BlendOutTriggerTime=0.f; M->GetController().SetFrameRate(FFrameRate(30,1),false);
	M->GetController().SetNumberOfFrames(FFrameRate(30,1).AsFrameTime(Length).CeilToFrame(),false);
	M->SortNotifies(); M->RefreshCacheData(); M->PostEditChange();
}
void Segment(UAnimMontage* M,FSlotAnimationTrack& Track,UAnimSequence* Clip,FName Section,float Start,float End,float Rate,float& Position)
{
	M->SetSkeleton(Clip->GetSkeleton());
	FAnimSegment S; S.SetAnimReference(Clip); S.StartPos=Position; S.AnimStartTime=Start; S.AnimEndTime=End; S.AnimPlayRate=Rate; S.LoopingCount=1;
	Track.AnimTrack.AnimSegments.Add(S);
	FCompositeSection CS; CS.SectionName=Section; CS.NextSectionName=NAME_None; CS.Link(M,Position); M->CompositeSections.Add(CS);
	Position+=S.GetLength();
}
void AddBranches(FKZComboNode& N,J Row,UAnimMontage* M,float Position,float Rate)
{
	for (const auto& BV:Row->GetArrayField(TEXT("branches")))
	{
		J B=BV->AsObject(); if (!Bool(B,TEXT("enabled"))) continue;
		FKZMonsterPatternBranch Branch; Branch.Notify=*FString(TEXT("Pattern_")+N.NodeId.ToString()+TEXT("_")+String(B,TEXT("event")));
		Branch.TargetNode=*String(B,TEXT("target")); Branch.bDeferUntilStepEnd=Bool(B,TEXT("deferred"));
		Branch.bCheckCooldown=Bool(B,TEXT("cooldown")); Branch.Weight=Number(B,TEXT("weight"),1); Branch.Source=String(B,TEXT("source"));
		const FString Trigger=String(B,TEXT("trigger"));
		if (Trigger==TEXT("AnimationNotifyTick") || Trigger==TEXT("AnimationNotifyStartEnd")) Branch.Event=EKZPatternEvent::Tick;
		else if (Trigger==TEXT("StartSubState")) Branch.Event=EKZPatternEvent::StepStart;
		else if (Trigger==TEXT("EndSubState")) Branch.Notify=TEXT("Pattern_EndSubState");
		else if (Trigger==TEXT("OnAttack") || Trigger==TEXT("AttackSuccess")) Branch.Event=EKZPatternEvent::ConfirmedHit;
		else if (Trigger==TEXT("ConfirmedHit")) Branch.Event=EKZPatternEvent::ConfirmedHit;
		else if (Trigger==TEXT("Parried")) Branch.Event=EKZPatternEvent::Parried;
		else if (Trigger==TEXT("HoldingSuccess")) Branch.Event=EKZPatternEvent::HoldingSuccess;
		else if (Trigger==TEXT("Landed")) Branch.Event=EKZPatternEvent::Landed;
		else if (Trigger.Contains(TEXT("Collision"))) Branch.Event=EKZPatternEvent::Collision;
		else if (Trigger!=TEXT("AnimationNotifyStart")) continue; // Unknown native events are never made unconditional.
		for (const auto& CV:B->GetArrayField(TEXT("checks")))
		{
			J Check=CV->AsObject(); const FString Kind=String(Check,TEXT("kind"));
			if (Kind==TEXT("parried")) { Branch.Event=EKZPatternEvent::Parried; continue; }
			if (Kind==TEXT("confirmed_hit")) { Branch.bRequireConfirmedHit=true; continue; }
			if (Kind==TEXT("holding")) { Branch.Event=EKZPatternEvent::HoldingSuccess; continue; }
			if (Kind==TEXT("target")) Branch.Conditions.Add(Gate(Check));
			if (Kind==TEXT("random")) Branch.Probability*=Number(Check,TEXT("chance"),1);
			if (Kind==TEXT("status"))
			{
				FKZCombatPatternCondition C; J Raw=Check->GetObjectField(TEXT("raw"));
				if (String(Raw,TEXT("DynamicStatus")).EndsWith(TEXT("HealthPoint")))
				{ C.bHPIsRatio=Bool(Raw,TEXT("bUseRatio")); C.MaxHP=Number(Raw,C.bHPIsRatio?TEXT("RatioValue"):TEXT("Value")); }
				else if(String(Raw,TEXT("DynamicStatus")).EndsWith(TEXT("Stamina"))) C.MaxStamina=Number(Raw,TEXT("Value"));
				Branch.Conditions.Add(C);
			}
			if (Kind==TEXT("wall"))
			{
				J Raw=Check->GetObjectField(TEXT("raw")); const TArray<TSharedPtr<FJsonValue>>* Directions;
				if (Raw->TryGetArrayField(TEXT("Directions"),Directions)) for (const auto& DV:*Directions)
				{
					J D=DV->AsObject(); FKZCombatPatternCondition C;
					const FString Direction=String(D,TEXT("Key")); C.WallCheckYaw=Direction.EndsWith(TEXT("Back"))?180.f:Direction.EndsWith(TEXT("Left"))?-90.f:Direction.EndsWith(TEXT("Right"))?90.f:0.f;
					C.WallCheckDistance=Number(Raw,TEXT("DirectionCheckDistance"),-1); C.bRequireClearWall=String(D,TEXT("Value")).EndsWith(TEXT("Fail")); Branch.Conditions.Add(C);
					if(C.WallCheckDistance<0)Branch.Source+=TEXT("; provisional omitted native wall distance: current capsule diameter");
				}
			}
		}
		if(Trigger==TEXT("AnimationNotifyTick") || Trigger==TEXT("AnimationNotifyStartEnd") || Branch.Event==EKZPatternEvent::Parried)
		{
			for(const auto& WV:B->GetArrayField(TEXT("windows"))){J W=WV->AsObject();Branch.ActiveWindows.Add(FVector2D(Number(W,TEXT("start"))/Rate,Number(W,TEXT("end"))/Rate));}
			if(Branch.ActiveWindows.IsEmpty())continue;
		}
		N.PatternBranches.Add(Branch);
		if (Branch.Event==EKZPatternEvent::Animation && Trigger==TEXT("AnimationNotifyStart"))
			for (const auto& Time:B->GetArrayField(TEXT("times"))) Notify(M,Position+Time->AsNumber()/Rate,Branch.Notify);
	}
}
void AddActions(FKZComboNode& N,J Row,UAnimMontage* M,float Position,float Rate)
{
	for(const auto& AV:Row->GetArrayField(TEXT("actions")))
	{
		J A=AV->AsObject(),Raw=A->GetObjectField(TEXT("raw")),Spawn=A->GetObjectField(TEXT("spawn"));FKZMonsterPatternAction Action;
		const FString Type=String(A,TEXT("type")),Trigger=String(A,TEXT("trigger"));
		Action.Source=String(A,TEXT("source"));Action.Notify=*FString(TEXT("Pattern_")+N.NodeId.ToString()+TEXT("_")+String(A,TEXT("event")));
		Action.MaxCount=Number(A,TEXT("max_count"),1);
		for(const auto& W:A->GetArrayField(TEXT("windows")))Action.ActiveWindows.Add(FVector2D(Number(W->AsObject(),TEXT("start"))/Rate,Number(W->AsObject(),TEXT("end"))/Rate));
		if(Trigger==TEXT("StartSubState") || Trigger==TEXT("StepStart"))Action.Event=EKZPatternEvent::StepStart;
		else if(Trigger==TEXT("ConfirmedHit"))Action.Event=EKZPatternEvent::ConfirmedHit;
		else if(Trigger==TEXT("Timer")){Action.Event=EKZPatternEvent::Tick;Action.Interval=Number(A,TEXT("timer"));}
		else if(Trigger!=TEXT("AnimationNotifyStart"))continue;
		if(Type==TEXT("xxHoldingStartFunc"))
		{
			Action.Action=EKZPatternAction::Capture;J Hold=Raw->GetObjectField(TEXT("HoldAttachInfo"));Action.Socket=*String(Hold,TEXT("AttachSocketName"));Action.CaptureTargetSocket=*String(Hold,TEXT("TargetSocketName"));
			if(Hold->HasField(TEXT("RagdollInfo"))){J R=Hold->GetObjectField(TEXT("RagdollInfo"));Action.RagdollBone=*String(R,TEXT("RagdollBoneName"));Action.PhysicsBlendWeight=Number(R,TEXT("PhysicsBlendWeight"),1.f);Action.Source+=TEXT("; current physics asset + engine handle adapter; omitted blend weight uses temporary 1.0");}
		}
		else if(Type==TEXT("xxFuncSkillObjectSpawn"))
		{
			Action.ObjectId=*String(A,TEXT("object"));Action.Action=String(Raw,TEXT("SkillActionType")).EndsWith(TEXT("Spawn"))?EKZPatternAction::SpawnObject:EKZPatternAction::ShootObject;
			const TSharedPtr<FJsonObject>* Hold;
			if(Spawn->TryGetObjectField(TEXT("SpawnAndHoldInfo"),Hold)){Action.Socket=*String(*Hold,TEXT("SocketName"));const TSharedPtr<FJsonObject>* Offset;if((*Hold)->TryGetObjectField(TEXT("BoneOffsetLocation"),Offset))Action.Offset=Vector(*Offset);}
			else{const TSharedPtr<FJsonObject>* Socket;if(Spawn->TryGetObjectField(TEXT("SocketInfo"),Socket))Action.Socket=*String(*Socket,TEXT("SocketName"));}
			if(Spawn->HasField(TEXT("BoneOffsetLocation")))Action.Offset+=Vector(Spawn->GetObjectField(TEXT("BoneOffsetLocation")));
			if(Spawn->HasField(TEXT("Location")))Action.Offset+=Vector(Spawn->GetObjectField(TEXT("Location")));
			Action.bSpawnOnFloor=Bool(Spawn,TEXT("bUseSpawnFloor"));
			const TSharedPtr<FJsonObject>* Aim;if(Spawn->TryGetObjectField(TEXT("AimShootInfo"),Aim))Action.bFlatAim=!Bool(*Aim,TEXT("bUsePitchRotator"));
			if(Action.bSpawnOnFloor)Action.bFlatAim=true;
		}
		else if(Type==TEXT("xxTargetDirectAttack")){Action.Action=EKZPatternAction::DirectDamage;Action.HPDamage=10;Action.StaminaDamage=5;} // Existing explicit temporary project damage policy, editable on this action.
		else if(Type==TEXT("xxSimpleSkillEventFuncSkillCoolTime"))
		{Action.Action=EKZPatternAction::AddCooldown;Action.CooldownSeconds=Number(Raw,TEXT("AddValue"));FString Skill=String(Raw->GetObjectField(TEXT("SelectSkill")),TEXT("AssetPathName"));FString Left;Skill.Split(TEXT("."),&Left,&Skill,ESearchCase::CaseSensitive,ESearchDir::FromEnd);Skill.RemoveFromStart(TEXT("SI_Yetuga_"));Action.TargetSkill=*Skill;}
		else if(Type==TEXT("xxSimpleSkillFunc_ChangeTargetSkill") && String(Raw,TEXT("ChangeStepType")).EndsWith(TEXT("Step8")))Action.Action=EKZPatternAction::DestroyObjects;
		else continue;
		N.PatternActions.Add(Action);
		if(Action.Event==EKZPatternEvent::Animation)for(const auto& T:A->GetArrayField(TEXT("times")))Notify(M,Position+T->AsNumber()/Rate,Action.Notify);
	}
}
void AddMoves(const FString& Base,FKZComboNode& N,J Row)
{
	const TArray<TSharedPtr<FJsonValue>>* Moves;if(!Row->TryGetArrayField(TEXT("moves"),Moves))return;
	for(int32 I=0;I<Moves->Num();++I)
	{
		J M=(*Moves)[I]->AsObject();FKZMonsterPatternMove Move;Move.Window=FVector2D(Number(M,TEXT("start")),Number(M,TEXT("end")));
		Move.Destination=Vector(M->GetObjectField(TEXT("destination")));Move.bTraceTarget=Bool(M,TEXT("target"));Move.TargetMin=Number(M,TEXT("target_min"));Move.TargetMax=Number(M,TEXT("target_max"));Move.TargetOffset=Number(M,TEXT("target_offset"));Move.StopDistance=Number(M,TEXT("stop_distance"));Move.Source=String(M,TEXT("source"))+TEXT("; ")+String(M,TEXT("conversion"));
		J Curves=M->GetObjectField(TEXT("curve"));
		if(Curves->HasField(TEXT("FloatCurves")))
		{
			const FString Path=Base+TEXT("/Data/CV_Move_")+N.NodeId.ToString()+FString::FromInt(I);
			UCurveFloat* Time=Asset<UCurveFloat>(Path+TEXT("_Time"));Time->FloatCurve.Reset();
			UCurveVector* Offset=Asset<UCurveVector>(Path+TEXT("_Offset"));
			for(int32 Axis=0;Axis<3;++Axis)
			{
				Offset->FloatCurves[Axis].Reset();FRichCurve& Target=Axis?Offset->FloatCurves[Axis]:Time->FloatCurve;
				const FString Field=Axis?FString::Printf(TEXT("FloatCurves[%d]"),Axis):TEXT("FloatCurves");const TSharedPtr<FJsonObject>* C;if(!Curves->TryGetObjectField(Field,C))continue;
				const auto& Keys=(*C)->GetArrayField(TEXT("Keys"));if(Keys.IsEmpty())continue;
				const float First=Number(Keys[0]->AsObject(),TEXT("Value")),Last=Number(Keys.Last()->AsObject(),TEXT("Value"));
				const float Scale=Axis?Move.Destination[Axis]:FMath::IsNearlyEqual(First,Last)?1.f:1.f/(Last-First);
				for(const auto& KV:Keys){J K=KV->AsObject();auto H=Target.AddKey(Number(K,TEXT("Time")),(Number(K,TEXT("Value"))-First)*Scale);auto& Key=Target.GetKey(H);Key.InterpMode=String(K,TEXT("InterpMode")).EndsWith(TEXT("Cubic"))?RCIM_Cubic:RCIM_Linear;Key.TangentMode=RCTM_User;Key.ArriveTangent=Number(K,TEXT("ArriveTangent"))*Scale;Key.LeaveTangent=Number(K,TEXT("LeaveTangent"))*Scale;}
			}
			Save(Time);Save(Offset);Move.TimeCurve=Time;Move.OffsetCurve=Offset;Move.Destination.Y=Move.Destination.Z=0.f;
		}
		N.PatternMoves.Add(Move);
	}
}
void Objects(const FString& Base,UKZComboDefinitionData* D,J Plan)
{
	auto& Definitions=Value<TArray<FKZMonsterPatternObject>>(D,TEXT("PatternObjects"));Definitions.Reset();
	for(const auto& OV:Plan->GetArrayField(TEXT("objects")))
	{
		J O=OV->AsObject();FKZMonsterPatternObject Data;Data.Id=*String(O,TEXT("id"));Data.Source=String(O,TEXT("source"));
		Data.Radius=Number(O,TEXT("radius"));Data.LifeSeconds=Number(O,TEXT("life"));Data.Scale=Number(O,TEXT("scale"),1);Data.MovementSeconds=Number(O,TEXT("move_seconds"));Data.LinearSpeed=Number(O,TEXT("linear_speed"));
		Data.DestructionRadius=Number(O,TEXT("destruction_radius"));
		Data.HPDamage=Number(O,TEXT("damage_hp"));Data.StaminaDamage=Number(O,TEXT("damage_stamina"));Data.bField=Bool(O,TEXT("field"));Data.bDestroyOnAbilityEnd=Bool(O,TEXT("end_with_ability"));Data.bKeepEndVelocity=Bool(O,TEXT("keep_end_velocity"));
		Data.TrailObjectId=*String(O,TEXT("trail_object"));Data.TrailInterval=Number(O,TEXT("trail_interval"));Data.TrailMaxCount=Number(O,TEXT("trail_count"));
		if(O->HasField(TEXT("field_extent")))Data.FieldExtent=Vector(O->GetObjectField(TEXT("field_extent")));
		for(const auto& P:O->GetObjectField(TEXT("animations"))->Values)Data.Animations.Add(*P.Key,LoadObject<UAnimSequence>(nullptr,*P.Value->AsString()));
		if(String(O,TEXT("mesh_source")).EndsWith(TEXT("C_I_YetugaRock_Small")))Data.Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga_IceRock"));
		else if(Data.Id.ToString().Contains(TEXT("Apes")))Data.StaticMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		J Curves=O->GetObjectField(TEXT("curve"));if(!Curves->Values.IsEmpty())
		{
			UCurveVector* Curve=Asset<UCurveVector>(Base+TEXT("/Data/CV_")+Data.Id.ToString());
			for(int32 Axis=0;Axis<3;++Axis)
			{
				Curve->FloatCurves[Axis].Reset();const FString Field=Axis?FString::Printf(TEXT("FloatCurves[%d]"),Axis):TEXT("FloatCurves");
				for(const auto& KV:Curves->GetObjectField(Field)->GetArrayField(TEXT("Keys")))
				{
					J K=KV->AsObject();FKeyHandle Handle=Curve->FloatCurves[Axis].AddKey(Number(K,TEXT("Time")),Number(K,TEXT("Value")));FRichCurveKey& Key=Curve->FloatCurves[Axis].GetKey(Handle);
					Key.InterpMode=String(K,TEXT("InterpMode")).EndsWith(TEXT("Cubic"))?RCIM_Cubic:RCIM_Linear;Key.TangentMode=RCTM_User;Key.ArriveTangent=Number(K,TEXT("ArriveTangent"));Key.LeaveTangent=Number(K,TEXT("LeaveTangent"));
				}
			}
			Save(Curve);Data.MovementCurve=Curve;Data.CurveScale=Vector(O->GetObjectField(TEXT("curve_scale")));
		}
		Definitions.Add(Data);
	}
}
UGameplayEffect* HoldEffect()
{
	UBlueprint* BP=Blueprint(TEXT("/Game/Monsters/AI/GE_MonsterCapture"),UGameplayEffect::StaticClass());auto* Effect=BP->GeneratedClass->GetDefaultObject<UGameplayEffect>();
	Effect->DurationPolicy=EGameplayEffectDurationType::Infinite;FInheritedTagContainer Tags;Tags.AddTag(KZGameplayTags::State_HitReacting);Tags.AddTag(KZGameplayTags::Block_Movement_Input);
	Effect->FindOrAddComponent<UTargetTagsGameplayEffectComponent>().SetAndApplyTargetTagChanges(Tags);
	FInheritedTagContainer Blocks;Blocks.AddTag(KZGameplayTags::Ability_Action);Blocks.AddTag(KZGameplayTags::Ability_Reaction_Hit);
	Effect->FindOrAddComponent<UBlockAbilityTagsGameplayEffectComponent>().SetAndApplyBlockedAbilityTagChanges(Blocks);
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);Save(BP);return BP->GeneratedClass->GetDefaultObject<UGameplayEffect>();
}
UBlueprint* GiantAnimations(const FString& Family,AKZMonster* CDO,UKZCharacterDefinitionData* Definition,J Plan)
{
	const FString Folder=TEXT("/Game/Monsters/")+Family+TEXT("/Animations/");
	UAnimBlueprint* BP=LoadObject<UAnimBlueprint>(nullptr,*(Folder+TEXT("ABP_")+Family)); if (!BP) return nullptr;
	// Resolve by source mapping, never by a misleading Attack/Damage filename alone.
	TMap<FString,UAnimSequence*> Clips;
	for (const auto& V:Plan->GetArrayField(TEXT("locomotion")))
	{ J R=V->AsObject(); Clips.Add(String(R,TEXT("key")),LoadObject<UAnimSequence>(nullptr,*String(R,TEXT("asset")))); }
	for (const TCHAR* Key:{TEXT("idle"),TEXT("run"),TEXT("F"),TEXT("B"),TEXT("L"),TEXT("R")}) if (!Clips.FindRef(Key)) return nullptr;
	const FAnimExtractContext Context(0.,true);
	float Walk=Clips[TEXT("F")]->ExtractRootMotionFromRange(0.f,Clips[TEXT("F")]->GetPlayLength(),Context).GetTranslation().Size2D()/Clips[TEXT("F")]->GetPlayLength();
	float Run=Clips[TEXT("run")]->ExtractRootMotionFromRange(0.f,Clips[TEXT("run")]->GetPlayLength(),Context).GetTranslation().Size2D()/Clips[TEXT("run")]->GetPlayLength();
	// Native curve/model units are not proved. Derived current cm displacement; editable fallback is explicit temporary tuning.
	if (Walk<=UE_SMALL_NUMBER) Walk=Value<FKZLocomotionConfig>(Definition,TEXT("LocomotionConfig")).WalkSpeed;
	if (Run<=Walk) Run=Value<FKZLocomotionConfig>(Definition,TEXT("LocomotionConfig")).RunSpeed;
	auto& Config=Value<FKZLocomotionConfig>(Definition,TEXT("LocomotionConfig")); Config.WalkSpeed=Walk; Config.RunSpeed=Run; Config.SprintSpeed=FMath::Max(Config.SprintSpeed,Run); Save(Definition);
	UBlendSpace* BS=Asset<UBlendSpace>(Folder+TEXT("BS_OriginalCombat_")+Family); BS->SetSkeleton(CDO->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton());
	Value<TArray<FBlendSample>>(BS,TEXT("SampleData")).Reset();
	auto* Params=FindFProperty<FStructProperty>(BS->GetClass(),TEXT("BlendParameters"))->ContainerPtrToValuePtr<FBlendParameter>(BS);
	Params[0].DisplayName=TEXT("Direction"); Params[0].Min=-180;Params[0].Max=180;Params[0].GridNum=8;Params[0].bWrapInput=true;
	Params[1].DisplayName=TEXT("Speed");Params[1].Min=0;Params[1].Max=Run;Params[1].GridNum=4;
	const TCHAR* Directions[]={TEXT("B"),TEXT("L"),TEXT("F"),TEXT("R"),TEXT("B")};
	for (int32 I=0;I<5;++I)
	{
		const float Angle=-180.f+I*90.f;
		BS->AddSample(Clips[TEXT("idle")],FVector(Angle,0,0)); BS->AddSample(Clips[Directions[I]],FVector(Angle,Walk,0));
		BS->AddSample(Clips[TEXT("run")],FVector(Angle,Run,0));
	}
	BS->TargetWeightInterpolationSpeedPerSec=0.f; BS->ValidateSampleData(); BS->ResampleData(); Save(BS);
	TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs); UEdGraph* Graph=*Graphs.FindByPredicate([](UEdGraph* G){return G->GetFName()==TEXT("AnimGraph");});
	UAnimGraphNode_Root* Root=nullptr;
	for (UEdGraphNode* N:TArray<TObjectPtr<UEdGraphNode>>(Graph->Nodes)) { if (auto* R=Cast<UAnimGraphNode_Root>(N)){Root=R;R->BreakAllNodeLinks();}else Graph->RemoveNode(N); }
	auto* Player=Node<UAnimGraphNode_BlendSpacePlayer>(Graph,-500,0);Player->SetAnimationAsset(BS);Player->AllocateDefaultPins();
	auto* Slot=Node<UAnimGraphNode_Slot>(Graph,-250,0);Slot->Node.SlotName=TEXT("DefaultSlot");Slot->Node.bAlwaysUpdateSourcePose=true;Slot->AllocateDefaultPins();
	auto* Inertia=Node<UAnimGraphNode_Inertialization>(Graph,0,0);Inertia->AllocateDefaultPins();
	auto* Speed=Getter(Graph,TEXT("GroundSpeed"),-700,120);auto* Angle=Getter(Graph,TEXT("MovementDirectionAngle"),-700,250);
	const UEdGraphSchema* Schema=Graph->GetSchema();
	auto Connect=[Schema](UEdGraphNode* A,FName AP,UEdGraphNode* B,FName BP){return Schema->TryCreateConnection(A->FindPin(AP),B->FindPin(BP));};
	if (!Connect(Speed,TEXT("GroundSpeed"),Player,TEXT("Y")) || !Connect(Angle,TEXT("MovementDirectionAngle"),Player,TEXT("X")) ||
		!Connect(Player,TEXT("Pose"),Slot,TEXT("Source")) || !Connect(Slot,TEXT("Pose"),Inertia,TEXT("Source")) || !Connect(Inertia,TEXT("Pose"),Root,TEXT("Result"))) return nullptr;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);
	BP->GeneratedClass->GetDefaultObject<UKZAnimInstance>()->SetRootMotionMode(ERootMotionMode::RootMotionFromMontagesOnly); Save(BP);
	return BP;
}
bool Family(J Plan)
{
	const FString Name=String(Plan,TEXT("family")),Base=TEXT("/Game/Monsters/")+Name;
	UBlueprint* BodyBP=LoadObject<UBlueprint>(nullptr,*(TEXT("/Game/Bluprints/Monsters/BP_Monster_")+Name));
	AKZMonster* Body=BodyBP->GeneratedClass->GetDefaultObject<AKZMonster>();
	UKZCharacterDefinitionData* Character=LoadObject<UKZCharacterDefinitionData>(nullptr,*(Base+TEXT("/Data/DA_Character_")+Name));
	if (!Character) return false;
	UAnimMontage* Montage=Asset<UAnimMontage>(Base+TEXT("/Animations/AM_OriginalPatterns_")+Name);
	UKZComboDefinitionData* Combo=Asset<UKZComboDefinitionData>(Base+TEXT("/Data/DA_OriginalPatterns_")+Name);
	Montage->CompositeSections.Reset();Montage->Notifies.Reset();FSlotAnimationTrack Track;Track.SlotName=TEXT("DefaultSlot");float Position=0;
	CoincidentNotifyAliases.Reset();
	auto& Nodes=Value<TArray<FKZComboNode>>(Combo,TEXT("Nodes"));Nodes.Reset();
	for (const auto& NV:Plan->GetArrayField(TEXT("nodes")))
	{
		J Row=NV->AsObject();UAnimSequence* Clip=LoadObject<UAnimSequence>(nullptr,*String(Row,TEXT("asset")));if (!Clip) return false;
		FKZComboNode N;N.NodeId=*String(Row,TEXT("id"));N.SectionName=N.NodeId;N.Montage=Montage;
		N.PatternSkill=*String(Row,TEXT("skill"));N.AutomaticNextNode=*String(Row,TEXT("next"));
		N.PatternBlendSeconds=Number(Row,TEXT("blend"),.2); // Serialized AnimBlendAlpha -> seconds is the documented engine adapter, not proved native units.
		const float Start=Position,Rate=Number(Row,TEXT("rate"),1);
		Segment(Montage,Track,Clip,N.NodeId,0,Clip->GetPlayLength(),Rate,Position);
		const int32 Loops=FMath::Max(1,int32(Number(Row,TEXT("loops"),1)));
		Track.AnimTrack.AnimSegments.Last().LoopingCount=Loops;
		Position=Start+Track.AnimTrack.AnimSegments.Last().GetLength();
		AddBranches(N,Row,Montage,Start,Rate);
		N.CollisionToActor=FTransform(Body->GetMesh()->GetRelativeLocation());
		for(const auto& WV:Row->GetArrayField(TEXT("attack_windows")))N.AttackWindows.Add(Collision(WV->AsObject()));
		AddActions(N,Row,Montage,Start,Rate);
		AddMoves(Base,N,Row);
		// Ability owns node changes/end. Self-next prevents premature montage auto-blend before the final marker.
		Montage->CompositeSections.Last().NextSectionName=N.SectionName;
		Notify(Montage,Start+FMath::Min(float(Number(Row,TEXT("next_time")))/Rate,Position-Start-1.f/30.f),*FString(TEXT("PatternNext_")+N.NodeId.ToString()));
		Nodes.Add(N);
	}
	for(auto& N:Nodes)
	{
		for(auto& B:N.PatternBranches)if(const FName* Alias=CoincidentNotifyAliases.Find(B.Notify))B.Notify=*Alias;
		for(auto& A:N.PatternActions)if(const FName* Alias=CoincidentNotifyAliases.Find(A.Notify))A.Notify=*Alias;
	}
	for(auto& E:Montage->Notifies)if(const FName* Alias=CoincidentNotifyAliases.Find(E.NotifyName))
	{E.NotifyName=*Alias;if(auto* N=Cast<UAnimNotify_PlayMontageNotify>(E.Notify))Value<FName>(N,TEXT("NotifyName"))=*Alias;}
	ObjectProperty(Combo,TEXT("AttackDamageEffect"),LoadClass<UGameplayEffect>(nullptr,TEXT("/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C")));
	Objects(Base,Combo,Plan);Finalize(Montage,Track,Position,.2f);Save(Montage);Save(Combo);
	TMap<FString,UClass*> Abilities; TMap<FString,J> SkillData;UGameplayEffect* Capture=HoldEffect();
	auto& Grants=Value<TArray<FKZInitialAbilityGrant>>(Character,TEXT("InitialAbilityGrants"));
	Grants.RemoveAll([Base](const auto& G){return G.AbilityClass && G.AbilityClass->GetPathName().StartsWith(Base+TEXT("/Abilities/GA_Original_"));});
	for (const auto& SV:Plan->GetArrayField(TEXT("skills")))
	{
		J S=SV->AsObject();const FString Id=String(S,TEXT("id"));SkillData.Add(Id,S);
		UBlueprint* BP=Blueprint(Base+TEXT("/Abilities/GA_Original_")+Id,UKZMonsterPatternAbility::StaticClass());
		UObject* CDO=BP->GeneratedClass->GetDefaultObject(); ObjectProperty(CDO,TEXT("ComboDefinition"),Combo);Value<FName>(CDO,TEXT("EntryNodeId"))=*String(S,TEXT("entry"));ObjectProperty(CDO,TEXT("CaptureEffect"),Capture->GetClass());
		FloatProperty(CDO,TEXT("ComboTransitionInertializationDuration"),.2f);FloatProperty(CDO,TEXT("LocomotionExitInertializationDuration"),.2f);
		FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);if (BP->Status==BS_Error || !Save(BP)) return false;
		Abilities.Add(Id,BP->GeneratedClass);FKZInitialAbilityGrant G;G.AbilityClass=BP->GeneratedClass;Grants.Add(G);
	}
	auto& Choices=Value<TArray<FKZMonsterSkillChoice>>(Body,TEXT("CombatPatterns"));Choices.Reset();
	for (const auto& CV:Plan->GetArrayField(TEXT("candidates")))
	{
		J C=CV->AsObject(); const FString Skill=String(C,TEXT("skill"));if (!Abilities.Contains(Skill)) continue;
		FKZMonsterSkillChoice R;R.Skill=*Skill;R.Ability=Abilities[Skill];R.Weight=Number(C,TEXT("weight"));R.Condition=Gate(C);R.Source=String(C,TEXT("provenance"));
		R.EndCooldown=Number(SkillData[Skill],TEXT("end_cooldown"));R.BattleStartCooldown=Number(SkillData[Skill],TEXT("start_cooldown"));Choices.Add(R);
	}
	// Cooldown-only rows also cover forced follow-up/level skills; weight zero keeps them out of random AI candidates.
	for (const auto& P:SkillData) if (!Choices.ContainsByPredicate([&P](const auto& R){return R.Skill==*P.Key;}))
	{ FKZMonsterSkillChoice R;R.Skill=*P.Key;R.Ability=Abilities[P.Key];R.EndCooldown=Number(P.Value,TEXT("end_cooldown"));R.BattleStartCooldown=Number(P.Value,TEXT("start_cooldown"));Choices.Add(R); }
	Value<bool>(Body,TEXT("bOrderedCombatPatterns"))=Bool(Plan,TEXT("ordered"));
	Value<TSubclassOf<UGameplayAbility>>(Body,TEXT("AlertAbility"))=Abilities.FindRef(TEXT("Roar"));
	auto& Attacks=Value<TArray<TSubclassOf<UGameplayAbility>>>(Body,TEXT("AttackAbilities"));Attacks.Reset();for (const auto& P:Abilities) if (P.Key!=TEXT("Roar")) Attacks.Add(P.Value);
	ObjectProperty(Body,TEXT("AIStateTree"),Tree());
	FKZMonsterAISettings& Settings=Value<FKZMonsterAISettings>(Body,TEXT("AISettings"));
	const TSharedPtr<FJsonObject>* Recognition;
	if(Plan->TryGetObjectField(TEXT("recognition"),Recognition) && Recognition->IsValid())
	{Settings.SightRadius=Number(*Recognition,TEXT("SightRange"),Settings.SightRadius);Settings.LoseSightRadius=Settings.SightRadius;Settings.PeripheralVisionHalfAngle=Number(*Recognition,TEXT("SightYaw"),Settings.PeripheralVisionHalfAngle*2)/2;}
	// Apes source omits RecognitionValue: retain the existing explicitly temporary perception CDO settings.
	Settings.AttackIntervalSeconds=FVector2D(1,1); // AP source Wait=1 s; Yetuga temporary adapter pause, no proven original Wait.
	Settings.StandoffSeconds=FVector2D(Name==TEXT("Yetuga")?1.67f:1.8f); // Original serialized LockOnMove time.
	Settings.bBackwardStandoff=Name==TEXT("Yetuga");Settings.StandoffDirectionWeights=Settings.bBackwardStandoff?FVector(2,2,1):FVector::OneVector;
	Settings.EngageDistance=800;Settings.PreferredDistance=400;Settings.AttackDistance=400;
	Save(Character); if (!GiantAnimations(Name,Body,Character,Plan)) return false;
	FBlueprintEditorUtils::MarkBlueprintAsModified(BodyBP);FKismetEditorUtilities::CompileBlueprint(BodyBP);return BodyBP->Status!=BS_Error && Save(BodyBP);
}
bool PlayerFall(J Plan)
{
	const FString Base=TEXT("/Game/_Art/Player/Animation/InGame/DAS/");
	UKZCharacterDefinitionData* Character=LoadObject<UKZCharacterDefinitionData>(nullptr,TEXT("/Game/Data/Character/DA_CharacterDefinition_Player"));if (!Character) return false;
	auto& Grants=Value<TArray<FKZInitialAbilityGrant>>(Character,TEXT("InitialAbilityGrants"));
	Grants.RemoveAll([](const auto& G){return G.AbilityClass && G.AbilityClass->IsChildOf(UKZFallAbility::StaticClass());});
	for (bool Plunge:{false,true})
	{
		const FString Folder=Base+(Plunge?TEXT("FallAttack/"):TEXT("Fall/"));
		UAnimMontage* M=Asset<UAnimMontage>(Folder+(Plunge?TEXT("AM_DAS_FallAttack"):TEXT("AM_DAS_Fall")));
		UKZComboDefinitionData* D=Asset<UKZComboDefinitionData>(Folder+(Plunge?TEXT("DA_DAS_FallAttack"):TEXT("DA_DAS_Fall")));
		M->CompositeSections.Reset();M->Notifies.Reset();FSlotAnimationTrack Track;Track.SlotName=TEXT("DefaultSlot");float Position=0;
		if (Plunge)
		{
			UAnimSequence* Clip=LoadObject<UAnimSequence>(nullptr,*(Folder+TEXT("CA_P_Kazan_DualAxeSword_Com_FallAtk")));if (!Clip) return false;
			Segment(M,Track,Clip,TEXT("Start"),0,.273f,.5f,Position);Notify(M,Position-1.f/30.f,TEXT("FallLoop"));
			Segment(M,Track,Clip,TEXT("Loop"),.273f,.29f,.005f,Position);
			const float LandingStart=Position;
			Segment(M,Track,Clip,TEXT("Land"),.29f,2.7333333f,1,Position);Notify(M,LandingStart+.42649162f,TEXT("InputEnd"));
		}
		else
		{
			const TCHAR* Names[]={TEXT("CA_P_Kazan_DualAxeSword_Fall_Start"),TEXT("CA_P_Kazan_DualAxeSword_Fall_Loop"),TEXT("CA_P_Kazan_DualAxeSword_Fall_End")};
			const FName Sections[]={TEXT("Start"),TEXT("Loop"),TEXT("Land")};
			for (int32 I=0;I<3;++I) {UAnimSequence* Clip=LoadObject<UAnimSequence>(nullptr,*(Folder+Names[I]));if(!Clip)return false;Segment(M,Track,Clip,Sections[I],0,Clip->GetPlayLength(),1,Position);if (I==0)Notify(M,Position-1.f/30.f,TEXT("FallLoop"));}
		}
		M->CompositeSections[0].NextSectionName=TEXT("Loop");M->CompositeSections[1].NextSectionName=TEXT("Loop");Finalize(M,Track,Position,.2f);
		auto& Nodes=Value<TArray<FKZComboNode>>(D,TEXT("Nodes"));Nodes.Reset();for (const FName Id:{FName(TEXT("Start")),FName(TEXT("Loop")),FName(TEXT("Land"))}){FKZComboNode N;N.NodeId=Id;N.SectionName=Id;N.Montage=M;Nodes.Add(N);}
		if(Plunge)
		{
			const FKZComboNode* Reference=nullptr;
			for(const auto& G:Grants)if(G.InputTag==KZGameplayTags::Input_Action_X && G.AbilityClass)
				if(const auto* Ability=Cast<UKZComboActionAbility>(G.AbilityClass->GetDefaultObject()))
					if(Ability->GetComboDefinition()){Reference=Ability->GetComboDefinition()->FindNode(Ability->GetEntryNodeId());if(Reference && !Reference->AttackWindows.IsEmpty())break;}
			if(!Reference || Reference->AttackWindows.IsEmpty())return false;
			FKZComboNode& Land=Nodes.Last();Land.CollisionToActor=Reference->CollisionToActor;
			for(const auto& WV:Plan->GetArrayField(TEXT("plunge_windows")))
			{auto Window=Collision(WV->AsObject());Window.HPDamage=Reference->AttackWindows[0].HPDamage;Window.StaminaDamage=Reference->AttackWindows[0].StaminaDamage;Window.Source+=TEXT("; temporary damage copied from current ground-X entry, editable; Player mesh .01 unchanged");Land.AttackWindows.Add(Window);}
			ObjectProperty(D,TEXT("AttackDamageEffect"),LoadClass<UGameplayEffect>(nullptr,TEXT("/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C")));
		}

		Save(M);Save(D);
		UBlueprint* BP=Blueprint(Folder+(Plunge?TEXT("GA_DAS_FallAttack"):TEXT("GA_DAS_Fall")),UKZFallAbility::StaticClass());
		UObject* CDO=BP->GeneratedClass->GetDefaultObject();ObjectProperty(CDO,TEXT("ComboDefinition"),D);Value<FName>(CDO,TEXT("EntryNodeId"))=TEXT("Start");Value<bool>(CDO,TEXT("bPlungeAttack"))=Plunge;
		if(Plunge)
		{
			CastChecked<UGameplayAbility>(CDO)->EditorGetAssetTags()=FGameplayTagContainer(KZGameplayTags::Ability_Action_Attack);
			Value<FGameplayTagContainer>(CDO,TEXT("BlockAbilitiesWithTag")).AddTag(KZGameplayTags::Ability_Action);
			Value<FGameplayTagContainer>(CDO,TEXT("CancelAbilitiesWithTag")).AddTag(KZGameplayTags::Ability_Action);
			Value<FGameplayTagContainer>(CDO,TEXT("ActivationOwnedTags")).AddTag(KZGameplayTags::Block_Movement_Input);
		}
		FBlueprintEditorUtils::MarkBlueprintAsModified(BP);FKismetEditorUtilities::CompileBlueprint(BP);if(BP->Status==BS_Error||!Save(BP))return false;
		FKZInitialAbilityGrant G;G.AbilityClass=BP->GeneratedClass;if(Plunge)G.InputTag=KZGameplayTags::Input_Action_X;Grants.Add(G);
	}
	Save(Character);
	// Existing Airborne_TEMP uses a placeholder. Replace only its sequence asset; preserve all graph connections.
	UAnimBlueprint* ABP=LoadObject<UAnimBlueprint>(nullptr,TEXT("/Game/_Art/Player/Character/Bluprints/ABP_Player"));
	TArray<UEdGraph*> Graphs;ABP->GetAllGraphs(Graphs);int32 Replaced=0;
	for(UEdGraph* Graph:Graphs)if(Graph->GetName().Contains(TEXT("Airborne")))for(UEdGraphNode* Node:Graph->Nodes)if(auto* Player=Cast<UAnimGraphNode_SequencePlayer>(Node))
	{Player->SetAnimationAsset(LoadObject<UAnimSequence>(nullptr,*(Base+TEXT("Fall/CA_P_Kazan_DualAxeSword_Fall_Loop"))));++Replaced;}
	if(Replaced){FBlueprintEditorUtils::MarkBlueprintAsModified(ABP);FKismetEditorUtilities::CompileBlueprint(ABP);Save(ABP);}
	UInputMappingContext* IMC=LoadObject<UInputMappingContext>(nullptr,TEXT("/Game/Input/IMC_Default"));
	UInputAction* Jump=LoadObject<UInputAction>(nullptr,TEXT("/Game/Input/Locomotion/IA_Jump"));if(IMC&&Jump){IMC->UnmapAllKeysFromAction(Jump);Save(IMC);}
	return true;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZGiantFallAuthorTest,"Khazan.GiantFall.Author",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZGiantFallAuthorTest::RunTest(const FString&)
{
	using namespace KZGiantFallAuthor;
	if(!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("Khazan_GiantFallWork_20261011"))||!GEditor||GEditor->PlayWorld){AddError(TEXT("Authoring is restricted to the owned isolated editor outside PIE"));return false;}
	FString Text;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()+TEXT("Metadata/GiantCombatFall_20261011/AuthoringPlan.json")));J Plan;
	if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Plan))return false;
	ChangedAssets.Reset();for(const auto& F:Plan->GetArrayField(TEXT("families")))if(!TestTrue(TEXT("Source-backed giant family assets"),Family(F->AsObject())))return false;
	if(!TestTrue(TEXT("Existing InGame fall/plunge assets connected"),PlayerFall(Plan)))return false;
	UWorld* World=GEditor->GetEditorWorldContext().World();AStaticMeshActor* Platform=nullptr;APlayerStart* Start=nullptr;
	for(TActorIterator<AKZMonster> I(World);I;++I)
	{
		const AKZMonster* Defaults=I->GetClass()->GetDefaultObject<AKZMonster>();
		if(Defaults->GetCombatPatterns().IsEmpty())continue;
		// Placed legacy actors had an empty per-instance array after the CDO gained new pattern rows.
		Value<TArray<FKZMonsterSkillChoice>>(*I,TEXT("CombatPatterns"))=Defaults->GetCombatPatterns();
		Value<bool>(*I,TEXT("bOrderedCombatPatterns"))=Defaults->UsesOrderedPatterns();
		Value<FKZMonsterAISettings>(*I,TEXT("AISettings"))=Defaults->GetAISettings();
		Value<TSubclassOf<UGameplayAbility>>(*I,TEXT("AlertAbility"))=Defaults->GetAlertAbility();
		Value<TArray<TSubclassOf<UGameplayAbility>>>(*I,TEXT("AttackAbilities"))=Defaults->GetAttackAbilities();
	}
	for(TActorIterator<AStaticMeshActor> I(World);I;++I)if(I->GetActorLabel()==TEXT("DevTest_FallPlatform"))Platform=*I;
	for(TActorIterator<APlayerStart> I(World);I;++I)Start=*I;
	if(!Start){AddError(TEXT("DevMap PlayerStart missing"));return false;}
	if(!Platform)Platform=World->SpawnActor<AStaticMeshActor>();
	Platform->SetActorLabel(TEXT("DevTest_FallPlatform"));Platform->SetFolderPath(TEXT("DevMap/FallingTest"));
	Platform->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Platform->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	// Temporary DevMap fixture, 12 m high x12 m x8 m. It is not an original level dimension.
	Platform->SetActorScale3D(FVector(12,8,12));Platform->SetActorLocation(FVector(0,0,600));
	Start->SetActorLocation(FVector(-350,0,1292));Start->SetActorRotation(FRotator::ZeroRotator);
	if(!TestTrue(TEXT("Save DevMap platform/start without changing existing actor roster"),FEditorFileUtils::SaveLevel(World->GetCurrentLevel())))return false;
	J Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Assets;for(const FString& Path:ChangedAssets)Assets.Add(MakeShared<FJsonValueString>(Path));Report->SetArrayField(TEXT("saved_packages"),Assets);
	Report->SetStringField(TEXT("map"),World->GetOutermost()->GetName());Report->SetNumberField(TEXT("platform_height_cm"),1200);Report->SetStringField(TEXT("status"),TEXT("Saved authoring; build/runtime/original-native parity tracked separately"));
	FString Out;FJsonSerializer::Serialize(Report.ToSharedRef(),TJsonWriterFactory<>::Create(&Out));FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectDir()+TEXT("Metadata/GiantCombatFall_20261011/AuthoringReport.json")));
	return true;
}
#endif
