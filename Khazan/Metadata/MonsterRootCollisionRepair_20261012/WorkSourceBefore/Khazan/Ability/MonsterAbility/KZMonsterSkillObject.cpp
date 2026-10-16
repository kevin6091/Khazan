#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Character/KZMonster.h"
#include "Character/KZCharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Curves/CurveVector.h"
#include "Animation/AnimSequence.h"
#include "GameplayEffect.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Ability/MonsterAbility/KZMonsterPatternAbility.h"
#include "LogChannels.h"
#include "Data/KZCharacterDefinitionData.h"

AKZMonsterSkillObject::AKZMonsterSkillObject()
{
	PrimaryActorTick.bCanEverTick=true;
	Scene=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Scene);
	Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StaticVisual"));Visual->SetupAttachment(Scene);Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AnimatedVisual=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("AnimatedVisual"));AnimatedVisual->SetupAttachment(Scene);AnimatedVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AKZMonsterSkillObject::Initialize(const FKZMonsterPatternObject& Definition,TSubclassOf<UGameplayEffect> Effect,AKZMonster* OwnerMonster,UObject* Ability,const FKZMonsterPatternObject* TrailDefinition,uint32 Run)
{
	Data=Definition;DamageEffect=Effect;Caster=OwnerMonster;Source=Ability;SetOwner(OwnerMonster);Age=FlightAge=0.f;
	UE_LOG(LogAbility,Verbose,TEXT("PatternObject spawn=%s owner=%s object=%s location=%s"),*GetName(),*OwnerMonster->GetName(),*Data.Id.ToString(),*GetActorLocation().ToString());
	if(TrailDefinition)TrailData=*TrailDefinition;
	bLaunched=Data.bField;
	if(auto* Pattern=Cast<UKZMonsterPatternAbility>(Ability)){SourceRun=Run?Run:Pattern->GetPatternRun();Pattern->RegisterSkillObject(this,SourceRun);}
	SetActorScale3D(FVector(Data.Scale));
	Visual->SetStaticMesh(Data.StaticMesh);Visual->SetVisibility(Data.StaticMesh!=nullptr);
	// Engine sphere radius=50 cm. Only the missing Apes projectile model uses this explicit visual fallback.
	if(Data.StaticMesh)Visual->SetRelativeScale3D(FVector(Data.Radius/50.f));
	AnimatedVisual->SetSkeletalMeshAsset(Data.Mesh);AnimatedVisual->SetVisibility(Data.Mesh!=nullptr);
	PlayState(TEXT("Idle"));
}

void AKZMonsterSkillObject::PlayState(FName State)
{
	const auto* Found=Data.Animations.Find(State);
	UAnimSequence* Clip=Found?Found->Get():nullptr;
	if(Clip && Data.Mesh && Clip->GetSkeleton()==Data.Mesh->GetSkeleton())AnimatedVisual->PlayAnimation(Clip,State==TEXT("Idle") || State==TEXT("Move"));
}

void AKZMonsterSkillObject::Shoot(AActor* Target,bool bFlatAim)
{
	if(bLaunched || !IsValid(Target))return;
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	ShotOrigin=GetActorLocation();ShotRotation=(Target->GetActorLocation()-ShotOrigin).Rotation();
	if(bFlatAim)ShotRotation.Pitch=0.f;
	SetActorRotation(ShotRotation);bLaunched=true;FlightAge=0.f;PlayState(TEXT("Move"));
	if(Data.ProjectileSound)
		FlightAudio=UGameplayStatics::SpawnSoundAttached(Data.ProjectileSound,Scene,NAME_None,
			FVector::ZeroVector,EAttachLocation::KeepRelativeOffset,true);
	UE_LOG(LogAbility,Verbose,TEXT("PatternObject launched=%s object=%s origin=%s rotation=%s"),*GetName(),*Data.Id.ToString(),*ShotOrigin.ToString(),*ShotRotation.ToString());
}

bool AKZMonsterSkillObject::ApplyHit(AActor* Actor)
{
	AKZCharacter* Victim=Cast<AKZCharacter>(Actor);AKZMonster* OwnerMonster=Caster.Get();
	if(!Victim || !OwnerMonster || Victim==OwnerMonster || !Victim->IsPlayerControlled() || Hits.Contains(Victim) || !DamageEffect)return false;
	UAbilitySystemComponent* ASC=OwnerMonster->GetAbilitySystemComponent();auto* TargetASC=Cast<UKZAbilitySystemComponent>(Victim->GetAbilitySystemComponent());
	if(!ASC || !TargetASC)return false;
	Hits.Add(Victim); // consume before potentially reentrant Guard/HP callbacks
	USoundBase* GuardAudio=Data.GuardSound;const FVector GuardLocation=Victim->GetActorLocation();
	if(TargetASC->TryGuardHit(Data.StaminaDamage,OwnerMonster))
	{
		if(GuardAudio)UGameplayStatics::SpawnSoundAtLocation(GetWorld(),GuardAudio,GuardLocation);
		return true;
	}
	FGameplayEffectContextHandle Context=ASC->MakeEffectContext();Context.AddInstigator(OwnerMonster,this);Context.AddSourceObject(Source.Get());
	FGameplayEffectSpecHandle Spec=ASC->MakeOutgoingSpec(DamageEffect,1.f,Context);
	if(!Spec.IsValid())return false;
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")),-Data.HPDamage);
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")),-Data.StaminaDamage);
	const bool bApplied=ASC->ApplyGameplayEffectSpecToTarget(*Spec.Data.Get(),TargetASC).WasSuccessfullyApplied();
	if(bApplied && IsValid(Victim))
	{
		const UKZCharacterDefinitionData* BodyDefinition=Victim->GetCharacterDefinition();
		if(Data.HPDamage>0.f && BodyDefinition && BodyDefinition->GetHitReactionSettings().ImpactSound)
			UGameplayStatics::SpawnSoundAtLocation(Victim,BodyDefinition->GetHitReactionSettings().ImpactSound,Victim->GetActorLocation());
		Victim->PlayHitReaction(EKZHitReactionType::Short,OwnerMonster);
	}
	return bApplied;
}

void AKZMonsterSkillObject::Impact(bool bWorld,bool bExpired)
{
	if(bImpact)return;
	UE_LOG(LogAbility,Verbose,TEXT("PatternObject impact=%s world=%d expired=%d age=%g flight=%g location=%s"),*GetName(),bWorld,bExpired,Age,FlightAge,*GetActorLocation().ToString());
	const FName State=bExpired?TEXT("Expire"):bWorld?TEXT("World"):TEXT("Impact");
	bImpact=true;PlayState(State);
	if(FlightAudio.IsValid())
	{
		if(Data.ProjectileStopFadeSeconds>0.f)FlightAudio->FadeOut(Data.ProjectileStopFadeSeconds,0.f);
		else FlightAudio->Stop();
		FlightAudio.Reset();
	}
	const auto* Clip=Data.Animations.Find(State);
	RemainingImpact=Clip && Clip->Get()?Clip->Get()->GetPlayLength():0.f;
	if(RemainingImpact<=0.f)Destroy();
}

void AKZMonsterSkillObject::SpawnTrail()
{
	if(TrailData.Id.IsNone())return;
	FVector Location=GetActorLocation();FHitResult Floor;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(KZGiantFieldFloor),false,this);Params.AddIgnoredActor(Caster.Get());
	if(GetWorld()->LineTraceSingleByChannel(Floor,Location,Location-FVector(0,0,Data.LinearSpeed*Data.LifeSeconds),ECC_Visibility,Params))
		Location=Floor.ImpactPoint+FVector(0,0,TrailData.FieldExtent.Z*TrailData.Scale);
	FActorSpawnParameters Parameters;Parameters.Owner=Caster.Get();Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if(auto* Field=GetWorld()->SpawnActor<AKZMonsterSkillObject>(StaticClass(),Location,GetActorRotation(),Parameters))
		Field->Initialize(TrailData,DamageEffect,Caster.Get(),Source.Get(),nullptr,SourceRun);
}

void AKZMonsterSkillObject::TriggerDestruction()
{
	if(bImpact)return;
	if(Data.DestructionRadius>0.f)
	{
		Hits.Reset();TArray<FOverlapResult> Contacts;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(KZGiantFieldDestruction),false,this);Params.AddIgnoredActor(Caster.Get());
		GetWorld()->OverlapMultiByObjectType(Contacts,GetActorLocation(),FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(Data.DestructionRadius*Data.Scale),Params);
		for(const auto& Contact:Contacts)ApplyHit(Contact.GetActor());
	}
	Impact(true,true);
}

void AKZMonsterSkillObject::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if(!Caster.IsValid()){Destroy();return;}
	Age+=DeltaSeconds;
	if(bImpact){RemainingImpact-=DeltaSeconds;if(RemainingImpact<=0.f)Destroy();return;}
	if(Data.LifeSeconds>0.f && Age>=Data.LifeSeconds){TriggerDestruction();return;}
	if(!bLaunched && !Data.bField)return;
	if(bLaunched && Data.TrailInterval>0.f && TrailCount<Data.TrailMaxCount && FlightAge>=(TrailCount+1)*Data.TrailInterval)
	{++TrailCount;SpawnTrail();}
	FCollisionObjectQueryParams Types;Types.AddObjectTypesToQuery(ECC_Pawn);Types.AddObjectTypesToQuery(ECC_WorldStatic);Types.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(KZGiantObject),false,this);Params.AddIgnoredActor(Caster.Get());
	const FVector Previous=GetActorLocation();FVector Next=Previous;
	if(!Data.bField && Data.MovementCurve && Data.MovementSeconds>0.f)
	{
		FlightAge+=DeltaSeconds;
		const float Alpha=FlightAge/Data.MovementSeconds;
		FVector Local=(Data.MovementCurve->GetVectorValue(Alpha)-Data.MovementCurve->GetVectorValue(0.f))*Data.CurveScale;
		if(Alpha>1.f && Data.bKeepEndVelocity)
			for(int32 Axis=0;Axis<3;++Axis)if(Data.MovementCurve->FloatCurves[Axis].GetNumKeys()>0)Local[Axis]+=(Alpha-1.f)*Data.MovementCurve->FloatCurves[Axis].GetLastKey().LeaveTangent*Data.CurveScale[Axis];
		Next=ShotOrigin+ShotRotation.RotateVector(Local);
	}
	else if(!Data.bField && Data.LinearSpeed>0.f){FlightAge+=DeltaSeconds;Next=Previous+ShotRotation.Vector()*Data.LinearSpeed*DeltaSeconds;}
	TArray<FHitResult> Contacts;
	const FCollisionShape Shape=Data.bField && !Data.FieldExtent.IsNearlyZero()?FCollisionShape::MakeBox(Data.FieldExtent*Data.Scale):FCollisionShape::MakeSphere(Data.Radius*Data.Scale);
	GetWorld()->SweepMultiByObjectType(Contacts,Previous,Next,GetActorQuat(),Types,Shape,Params);
	for(const FHitResult& Hit:Contacts)
	{
		if(ApplyHit(Hit.GetActor())){if(!Data.bField){SetActorLocation(Hit.Location);Impact(false);return;}}
		else if(!Data.bField && Hit.bBlockingHit && !Cast<APawn>(Hit.GetActor())){SetActorLocation(Hit.Location);Impact(true);return;}
	}
	SetActorLocation(Next);
}
