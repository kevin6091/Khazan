// Development-only actual Guard/Combo/skill-object integration. All numeric
// attack shapes/damage below are unsaved test fixtures, never gameplay defaults.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/PlayerAbility/KZGuardAbility.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/KZCombatCameraModifier.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/PostProcessVolume.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "Editor.h"
#include "Settings/LevelEditorPlaySettings.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"
#include "ParticleEmitterInstances.h"
#include "ParticleHelper.h"
#include "Particles/ParticleEmitter.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UnrealType.h"
#include "UObject/UObjectIterator.h"
#include "UObject/ObjectKey.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/App.h"
#include "KZGameplayTags.h"

namespace KZParryQA
{
struct FCase
{
	const TCHAR* Name; int32 Kind; float HitAt; int32 Hits; bool Blockable; bool Rear; bool Moving;
	float PlayerHPDamage, PlayerStaminaDamage, MonsterStaminaDamage;
};
// Kinds: actual melee 0, actual field sweep 1, direct resource/lifetime checks 2.
const FCase Cases[] = {
	{TEXT("EarlyMelee"),0,.03f,1,true,false,false,0,4,5},
	{TEXT("LateMeleeNormalGuard"),0,.30f,1,true,false,false,0,8,0},
	{TEXT("Unblockable"),0,.03f,1,false,false,false,7,8,0},
	{TEXT("RearMelee"),0,.03f,1,true,true,false,7,8,0},
	{TEXT("SameHitGroupDedup"),0,.03f,2,true,false,false,0,4,5},
	{TEXT("TwoIndependentEarlyHits"),0,.03f,3,true,false,false,0,8,10},
	{TEXT("EarlyThenLateNoReopen"),0,.03f,4,true,false,false,0,12,5},
	{TEXT("MovingGuardSkipsStart"),0,.03f,1,true,false,true,0,4,5},
	{TEXT("ReleaseBeforeHit"),0,.03f,5,true,false,false,7,8,0},
	{TEXT("CancelBeforeHit"),0,.03f,6,true,false,false,7,8,0},
	{TEXT("EarlyFieldSweep"),1,.03f,1,true,false,false,0,4,5},
	{TEXT("RearFieldSweep"),1,.03f,1,true,true,false,7,8,0},
	{TEXT("LateFieldNormalGuard"),1,.30f,1,true,false,false,0,8,0},
	{TEXT("ParryTriggersExhaustion"),0,.03f,7,true,false,false,0,4,5},
	{TEXT("ResourceAndLifetime"),2,0,1,true,false,false,0,0,0},
	{TEXT("QuickReleaseRetainsParryPose"),0,.03f,8,true,false,false,0,4,5},
	{TEXT("MovingQuickReleaseRetainsParryPose"),0,.03f,8,true,false,true,0,4,5},
};
struct FSaved { TWeakObjectPtr<AKZCharacter> Actor; FTransform Transform; float HP=0,Stamina=0; EMovementMode Mode=MOVE_None; };
class FRun : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),ASC(Cast<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent())),Deadline(FPlatformTime::Seconds()+360.)
	{
		Fixed=FApp::UseFixedTimeStep();Delta=FApp::GetFixedDeltaTime();FApp::SetUseFixedTimeStep(true);FApp::SetFixedDeltaTime(1./60.);
		Save(P);Base=P->GetActorLocation();P->HandleInputMoveReleased();ASC->CancelAllAbilities();
		if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_CAMERA_FROM_SCENELOOK"))==TEXT("1"))
		{
			// Recorded PlayerStart in the same SceneLook report as the static camera.
			// Saved contains the original transform for exact QA cleanup.
			Base=FVector(12022.196342,13909.267886,223.710571);
			P->SetActorLocation(Base);
		}
		for(const auto& S:ASC->GetActivatableAbilities())if(Cast<UKZGuardAbility>(S.Ability))GuardHandle=S.Handle;
		for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It)
		{
			if(It->GetCharacterDefinition() && It->GetCharacterDefinition()->GetPathName().Contains(TEXT("/Monsters/Swordsman/")))AttackerClass=It->GetClass();
			Save(*It);It->SetActorLocation(Base+FVector(20000+Saved.Num()*1000,20000,0));
		}
		Camera=P->GetWorld()->SpawnActor<ACameraActor>();Camera->SetActorLocation(Base+FVector(250,-450,140));
		Camera->SetActorRotation((Base+FVector(30,0,25)-Camera->GetActorLocation()).Rotation());Camera->GetCameraComponent()->SetFieldOfView(55);
		if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_CAMERA_FROM_PLAYER"))==TEXT("1"))
		{
			if(const UCameraComponent* PlayerCamera=P->FindComponentByClass<UCameraComponent>())
			{
				Camera->SetActorTransform(PlayerCamera->GetComponentTransform());
				Camera->GetCameraComponent()->SetFieldOfView(PlayerCamera->FieldOfView);
				Test->AddInfo(FString::Printf(TEXT("PARRY_CAMERA_FIXTURE player component location=%s FOV=%g"),*Camera->GetActorLocation().ToString(),PlayerCamera->FieldOfView));
			}
		}
		if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_CAMERA_FROM_SCENELOOK"))==TEXT("1"))
		{
			// Recorded Player view, Metadata/SceneLook_20261012/MainHeinAfter01/Capture.json.
			// The static QA camera avoids foreground foliage at the live PlayerStart.
			Camera->SetActorLocation(FVector(11412.196342,13909.267886,307.575325));
			Camera->SetActorRotation(FRotator::ZeroRotator);
			Camera->GetCameraComponent()->SetFieldOfView(70.f);
			Test->AddInfo(TEXT("PARRY_CAMERA_FIXTURE recorded HeinMach Player view from SceneLook report"));
		}
		OldView=P->GetController<APlayerController>()->GetViewTarget();P->GetController<APlayerController>()->SetViewTarget(Camera.Get());
		HPDelegate=ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).AddLambda([this](const FOnAttributeChangeData& D){if(D.NewValue<D.OldValue)++HPHits;});
	}
	~FRun() override { Cleanup(); }
	bool Update() override
	{
		if(!Player.IsValid()||!ASC.IsValid()||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Owned Parry PIE expired"));return Finish();}
		if(!Running)
		{
			if(Index==UE_ARRAY_COUNT(Cases)){Test->AddInfo(FString::Printf(TEXT("PARRY_CASES_COMPLETE %d actual melee/field/lifetime cases"),int32(UE_ARRAY_COUNT(Cases))));return Finish();}
			if(!StartCase())return Finish();return false;
		}
		const FCase& C=Cases[Index];const float Age=Player->GetWorld()->GetTimeSeconds()-Start;
		const float CameraGain = Guard.IsValid() ? FindFProperty<FFloatProperty>(Guard->GetClass(),TEXT("ParryCameraGain"))->GetPropertyValue_InContainer(Guard.Get()) : 0.f;
		UObject* BillboardAsset = Guard.IsValid() ? FindFProperty<FObjectPropertyBase>(Guard->GetClass(),TEXT("ParryBillboardDistortion"))->GetObjectPropertyValue_InContainer(Guard.Get()) : nullptr;
		bool CameraActive=false;
		bool ScreenActive=false;
		bool DistortionActive=false;
		for(TActorIterator<APostProcessVolume> It(Player->GetWorld());It;++It)
			if(It->Tags.Contains(TEXT("KZParryScreenDistortion"))){ScreenActive=true;ObservedScreen=true;}
		if (auto* Modifier=Cast<UKZCombatCameraModifier>(Player->GetController<APlayerController>()->PlayerCameraManager->FindCameraModifierByClass(UKZCombatCameraModifier::StaticClass())))
		{
			CameraActive=Modifier->GetActiveParryShakeCount()>0;
			const FVector Axes=Modifier->GetLastLocalTranslation().GetAbs();
			MaxCameraLocalAxes.X=FMath::Max(MaxCameraLocalAxes.X,Axes.X);
			MaxCameraLocalAxes.Y=FMath::Max(MaxCameraLocalAxes.Y,Axes.Y);
			MaxCameraLocalAxes.Z=FMath::Max(MaxCameraLocalAxes.Z,Axes.Z);
		}
		for(TObjectIterator<UNiagaraComponent> It;It;++It)
			if(It->GetWorld()==Player->GetWorld()&&It->IsRegistered()&&It->IsActive()&&It->ComponentHasTag(TEXT("KZParryBillboardDistortion")))
			{DistortionActive=true;ObservedBillboardDistortion=true;}
		ObservedCamera|=CameraActive;
		if(CameraActive&&Camera.IsValid())
		{
			const APlayerCameraManager* Manager=Player->GetController<APlayerController>()->PlayerCameraManager;
			MaxCameraFOVDelta=FMath::Max(MaxCameraFOVDelta,FMath::Abs(Manager->GetFOVAngle()-Camera->GetCameraComponent()->FieldOfView));
			MaxCameraLocationDelta=FMath::Max(MaxCameraLocationDelta,FVector::Dist(Manager->GetCameraLocation(),Camera->GetActorLocation()));
		}
		if(C.Hits==8 && Age>=.055f)ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
		if(C.Hits==8 && Age>=.16f && Age<.20f)
		{
			Test->TestFalse(TEXT("Quick release removes guarding immediately"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding));
			Test->TestTrue(TEXT("Released parry remains playing until authored InputEnd"),Guard.IsValid()&&Guard->IsActive()&&Player->GetMesh()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage()).ToString().StartsWith(TEXT("Parry_")));
		}
		if(Guard.IsValid()&&Guard->IsActive())
			ObservedParry|=Player->GetMesh()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage()).ToString().StartsWith(TEXT("Parry_"));
		for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==Player->GetWorld()&&It->ComponentHasTag(TEXT("KZParryImpact")))
			if(!Seen.Contains(FObjectKey(*It))){Seen.Add(FObjectKey(*It));++Effects;}
		for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==Player->GetWorld()&&It->ComponentHasTag(TEXT("KZReceivedHitImpact")))
			if(!Seen.Contains(FObjectKey(*It))){Seen.Add(FObjectKey(*It));++ReceivedEffects;if(Index==2)Capture(TEXT("04_ActualReceivedHit"));}
		if(Index==0 && Age>=.06f && !Captured1)
		{
			Capture(TEXT("01_ActualParryImpact"));Captured1=true;
		}
		if(Index==0 && Age>=.13f && !Captured2)
		{
			for(TObjectIterator<UParticleSystemComponent> It;It;++It)
				if(It->GetWorld()==Player->GetWorld()&&It->ComponentHasTag(TEXT("KZParryImpact")))
				{
					Test->AddInfo(FString::Printf(TEXT("PARRY_RENDER Template=%s Particles=%d Location=%s"),*GetPathNameSafe(It->Template),It->GetNumActiveParticles(),*It->GetComponentLocation().ToString()));
					for(auto* E:It->EmitterInstances)if(E)
					{
						const FBaseParticle* P=E->ActiveParticles>0?E->GetParticle(0):nullptr;
						Test->AddInfo(FString::Printf(TEXT("PARRY_EMITTER %s Active=%d Size=%s Position=%s Color=%s"),*GetNameSafe(E->SpriteTemplate),E->ActiveParticles,P?*P->Size.ToString():TEXT("empty"),P?*P->Location.ToString():TEXT("empty"),P?*P->Color.ToString():TEXT("empty")));
					}
				}
			Capture(TEXT("02_ActualParryMotion"));Captured2=true;
		}
		if(Index==0 && Age>=.24f && !Captured3){Capture(TEXT("03_ActualParryEffectTail"));Captured3=true;}
		if(Index==7)Player->HandleInputMoveReleased();
		if(C.Kind==1 && !Field.IsValid() && Age>=C.HitAt)
		{
			FKZMonsterPatternObject D;D.Id=TEXT("ParryFixtureField");D.bField=true;D.FieldExtent=FVector(60,60,100);D.Scale=1;D.LifeSeconds=2;D.HPDamage=7;D.StaminaDamage=8;
			Field=Player->GetWorld()->SpawnActor<AKZMonsterSkillObject>(Player->GetActorLocation(),FRotator::ZeroRotator);
			Field->Initialize(D,Attacker->GetCharacterDefinition()->GetMonsterStaminaSettings().DamageEffect,Attacker.Get(),this->Attacker.Get());
		}
		if(Age<.85f)return false;
		// The requested original Niagara drains its own particles after emission
		// stops. Keep cases isolated until that tail ends, rather than hard-cut FX.
		if(DistortionActive && Age<5.f)return false;
		if(C.Kind!=2)
		{
			Test->TestTrue(FString::Printf(TEXT("%s actual HP result"),C.Name),FMath::IsNearlyEqual(HP(Player.Get()),100-C.PlayerHPDamage));
			Test->TestTrue(FString::Printf(TEXT("%s actual defender stamina result"),C.Name),FMath::IsNearlyEqual(Stamina(Player.Get()),50-C.PlayerStaminaDamage));
			Test->TestTrue(FString::Printf(TEXT("%s actual attacker parry stamina result"),C.Name),FMath::IsNearlyEqual(Stamina(Attacker.Get()),(C.Hits==7?5:50)-C.MonsterStaminaDamage));
			if(C.Hits==7)Test->TestTrue(TEXT("Actual parry depletion starts existing monster exhaustion"),Attacker->GetAbilitySystemComponent()->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
			const int32 Expected=C.MonsterStaminaDamage>0?int32(C.MonsterStaminaDamage/5):0;
			const FArrayProperty* BrutalData = FindFProperty<FArrayProperty>(Guard->GetClass(), TEXT("ParryBrutalEffects"));
			const int32 ParticleCount = BrutalData ? FScriptArrayHelper(BrutalData, BrutalData->ContainerPtrToValuePtr<void>(Guard.Get())).Num() : 0;
			Test->TestTrue(TEXT("Brutal combat particle copies configured"), ParticleCount > 0);
			Test->TestEqual(FString::Printf(TEXT("%s feedback matches deduplicated approved parries"),C.Name),Effects,Expected * ParticleCount);
			Test->TestEqual(FString::Printf(TEXT("%s HP hit effect count"),C.Name),HPHits,C.PlayerHPDamage>0?1:0);
			Test->TestEqual(FString::Printf(TEXT("%s accepted player damage feedback count"),C.Name),ReceivedEffects,C.PlayerHPDamage>0&&Player->GetCharacterDefinition()->GetHitReactionSettings().ImpactEffect?1:0);
			Test->TestEqual(FString::Printf(TEXT("%s camera only on approved parry"),C.Name),ObservedCamera,CameraGain>0&&Expected>0);
			Test->TestFalse(FString::Printf(TEXT("%s finite parry camera expires"),C.Name),CameraActive);
			Test->TestEqual(FString::Printf(TEXT("%s billboard distortion only on approved parry"),C.Name),ObservedBillboardDistortion,BillboardAsset&&Expected>0);
			Test->TestFalse(FString::Printf(TEXT("%s billboard distortion expires"),C.Name),DistortionActive);
			Test->TestFalse(FString::Printf(TEXT("%s old screen blur removed"),C.Name),ObservedScreen);
			Test->TestFalse(FString::Printf(TEXT("%s finite screen blur expires"),C.Name),ScreenActive);
			if(CameraGain>0&&Expected>0)
			{
				Test->TestTrue(TEXT("Linear FOV force changes actual camera output"),MaxCameraFOVDelta>UE_SMALL_NUMBER);
				Test->TestTrue(TEXT("Parry camera moves forward/right/up continuously"),MaxCameraLocalAxes.GetMin()>UE_SMALL_NUMBER);
			}
			if(Expected>0)Test->TestTrue(TEXT("Dedicated original parry section was actually evaluated"),ObservedParry);
		}
		Test->AddInfo(FString::Printf(TEXT("PARRY_CASE %s HP=%g ST=%g attackerST=%g effects=%d cameraFOVMax=%gdeg cameraLocationMax=%gcm"),C.Name,HP(Player.Get()),Stamina(Player.Get()),Stamina(Attacker.Get()),Effects,MaxCameraFOVDelta,MaxCameraLocationDelta));
		EndCase();++Index;Running=false;return false;
	}
private:
	float HP(AKZCharacter* C) const {return C->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());}
	float Stamina(AKZCharacter* C) const {return C->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());}
	void Save(AKZCharacter* C)
	{
		Saved.Add({C,C->GetActorTransform(),HP(C),Stamina(C),C->GetCharacterMovement()->MovementMode});
		C->GetAbilitySystemComponent()->AddLooseGameplayTag(KZGameplayTags::Block_StaminaRegen);C->GetAbilitySystemComponent()->CancelAllAbilities();
		if(auto* AI=Cast<AAIController>(C->GetController()))if(AI->BrainComponent)AI->BrainComponent->PauseLogic(TEXT("Owned parry fixture"));
	}
	bool StartCase()
	{
		if(!GuardHandle.IsValid()||!AttackerClass){Test->AddError(TEXT("Saved Guard and Swordsman are required"));return false;}
		const FCase& C=Cases[Index];ASC->CancelAllAbilities();ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);ASC->ClearComboCommands();Player->HandleInputMoveReleased();
		Player->SetActorLocationAndRotation(Base,FRotator::ZeroRotator);Player->GetCharacterMovement()->StopMovementImmediately();Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),100);ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),50);
		FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Attacker=Player->GetWorld()->SpawnActor<AKZMonster>(AttackerClass,Base+FVector(C.Rear?-200:200,0,0),FRotator(0,C.Rear?0:180,0),Params);if(!Attacker.IsValid())return false;
		if(auto* AI=Cast<AAIController>(Attacker->GetController()))if(AI->BrainComponent)AI->BrainComponent->PauseLogic(TEXT("Owned parry attacker"));
		Attacker->GetCharacterMovement()->DisableMovement();Attacker->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
		auto* MASC=Cast<UKZAbilitySystemComponent>(Attacker->GetAbilitySystemComponent());MASC->CancelAllAbilities();MASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),C.Hits==7?5:50);
		if(C.Moving)Player->HandleInputMove(FVector2D(0,1),FRotator::ZeroRotator);
		ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
		Guard=Cast<UKZGuardAbility>(ASC->FindAbilitySpecFromHandle(GuardHandle)->GetPrimaryInstance());
		if(!Test->TestTrue(TEXT("Real Guard activation owns held state"),Guard.IsValid()&&Guard->IsActive()&&ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding)))return false;
		Start=Player->GetWorld()->GetTimeSeconds();Seen.Reset();Effects=HPHits=ReceivedEffects=0;ObservedParry=false;ObservedCamera=false;ObservedScreen=false;ObservedBillboardDistortion=false;MaxCameraFOVDelta=MaxCameraLocationDelta=0;MaxCameraLocalAxes=FVector::ZeroVector;
		for(TObjectIterator<UParticleSystemComponent> It;It;++It)if(It->GetWorld()==Player->GetWorld())Seen.Add(FObjectKey(*It));
		if(C.Kind==2){ResourcesAndLifetime();}
		if(C.Kind==0)
		{
			FGameplayAbilitySpecHandle Handle;UKZComboActionAbility* Attack=nullptr;
			for(const auto& S:MASC->GetActivatableAbilities())
				if(auto* A=Cast<UKZComboActionAbility>(S.GetPrimaryInstance()))if(A->GetComboDefinition() && A->GetComboDefinition()->FindNode(A->GetEntryNodeId()) && !A->GetComboDefinition()->FindNode(A->GetEntryNodeId())->AttackWindows.IsEmpty()){Attack=A;Handle=S.Handle;break;}
			if(!Test->TestNotNull(TEXT("Actual granted monster attack instance"),Attack))return false;
			Fixture.Reset(DuplicateObject<UKZComboDefinitionData>(Attack->GetComboDefinition(),GetTransientPackage()));
			FKZComboNode Node=*Attack->GetComboDefinition()->FindNode(Attack->GetEntryNodeId());Node.CommandEdges.Reset();Node.CollisionToActor=FTransform::Identity;Node.AttackWindows.Reset();
			auto Window=[&](float Begin,float End,FName Group){FKZAttackCollisionWindow W;W.StartTime=Begin;W.EndTime=End;W.Shape=EKZAttackCollisionShape::Box;W.Extent=FVector(60,60,100);W.HPDamage=7;W.StaminaDamage=8;W.bBlockable=C.Blockable;W.HitGroup=Group;W.Source=TEXT("Unsaved DEV parry fixture");FKZAttackCollisionKey K;K.Time=Begin;K.Center=FVector(200,0,0);W.Keys.Add(K);K.Time=End;W.Keys.Add(K);return W;};
			Node.AttackWindows.Add(Window(C.HitAt,C.HitAt+.07f,C.Hits==2?FName(TEXT("Shared")):NAME_None));
			if(C.Hits==2||C.Hits==3)Node.AttackWindows.Add(Window(.11f,.13f,C.Hits==2?FName(TEXT("Shared")):NAME_None));
			if(C.Hits==4)Node.AttackWindows.Add(Window(.30f,.34f,NAME_None));
			*FindFProperty<FArrayProperty>(Fixture->GetClass(),TEXT("Nodes"))->ContainerPtrToValuePtr<TArray<FKZComboNode>>(Fixture.Get())={Node};
			FindFProperty<FObjectPropertyBase>(Attack->GetClass(),TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(Attack,Fixture.Get());
			FindFProperty<FClassProperty>(Attack->GetClass(),TEXT("CostGameplayEffectClass"))->SetObjectPropertyValue_InContainer(Attack,nullptr);
			if(!Test->TestTrue(TEXT("Actual monster montage task starts"),MASC->TryActivateAbility(Handle)))return false;
		}
		if(C.Hits==5)ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);
		if(C.Hits==6)ASC->CancelAbilityHandle(GuardHandle);
		Running=true;return true;
	}
	void ResourcesAndLifetime()
	{
		bool Parried=true;ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),5);
		Test->TestTrue(TEXT("Parry needs reduced cost only"),ASC->TryGuardHit(8,Attacker.Get(),Parried)&&Parried);
		Test->TestEqual(TEXT("Original one-half cost applied"),Stamina(Player.Get()),1.f);
		Test->TestFalse(TEXT("Not enough reduced cost rejects"),ASC->TryGuardHit(8,Attacker.Get(),Parried));Test->TestFalse(TEXT("Rejected out result resets"),Parried);
		Test->TestTrue(TEXT("Zero-stamina-damage HP attack can parry"),ASC->TryGuardHit(0,Attacker.Get(),Parried)&&Parried);
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),50);
		Attacker->SetActorLocation(Player->GetActorLocation()+FVector(200,-80,0));
		Test->TestTrue(TEXT("Front-left hit accepts parry"),ASC->TryGuardHit(8,Attacker.Get(),Parried)&&Parried);
		Test->TestEqual(TEXT("Front-left hit selects original left response section"),Player->GetMesh()->GetAnimInstance()->Montage_GetCurrentSection(Guard->GetCurrentMontage()),FName(TEXT("Parry_L")));
		Test->TestFalse(TEXT("Invalid negative stamina damage rejects"),ASC->TryGuardHit(-1,Attacker.Get(),Parried));
		ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);Test->TestFalse(TEXT("Release closes window immediately"),ASC->TryGuardHit(0,Attacker.Get(),Parried));
		ASC->CancelAllAbilities();Test->TestFalse(TEXT("Cancel clears Guard owned tag"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding));
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),50);ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),0);Test->TestFalse(TEXT("Dead defender cannot parry"),ASC->TryGuardHit(8,Attacker.Get(),Parried));
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),100);ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);ASC->CancelAllAbilities();
		ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
		auto* PC=Player->GetController<APlayerController>();PC->UnPossess();
		Test->TestFalse(TEXT("UnPossess clears the owned Guard tag"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding));
		Test->TestFalse(TEXT("UnPossess closes parry eligibility"),ASC->TryGuardHit(8,Attacker.Get(),Parried));
		PC->Possess(Player.Get());
		TSet<FString> Families;
		for(const FSaved& S:Saved)if(auto* M=Cast<AKZMonster>(S.Actor.Get()))
		{
			const auto* Definition=M->GetCharacterDefinition();if(!Definition||Families.Contains(Definition->GetPathName()))continue;
			Families.Add(Definition->GetPathName());const auto& Settings=Definition->GetMonsterStaminaSettings();
			const FVector BeforeLocation=M->GetActorLocation();const float BeforeStamina=Stamina(M);
			M->SetActorLocation(Player->GetActorLocation()+FVector(200,0,0));
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);ASC->CancelAllAbilities();ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),50);
			ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
			Test->TestTrue(FString::Printf(TEXT("%s actual Guard parry reaches monster"),*Definition->GetName()),ASC->TryGuardHit(8,M,Parried)&&Parried);
			Test->TestTrue(FString::Printf(TEXT("%s uses its current Definition parry damage"),*Definition->GetName()),FMath::IsNearlyEqual(Stamina(M),FMath::Max(BeforeStamina-Settings.ParryStaminaDamage,0.f)));
			M->GetAbilitySystemComponent()->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),BeforeStamina);M->SetActorLocation(BeforeLocation);
		}
		if(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_HEINMACH"))==TEXT("1"))
			Test->TestTrue(TEXT("HeinMach seeded monster family consumes actual Guard parry"),Families.Num()>=1);
		else Test->TestEqual(TEXT("All six current monster families consume actual Guard parry"),Families.Num(),6);
		ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);ASC->CancelAllAbilities();
	}
	void Capture(const TCHAR* Name)
	{
		auto* PC=Player->GetController<APlayerController>();auto* V=PC->GetLocalPlayer()->ViewportClient.Get();TArray<FColor> Pixels;FIntVector Size=FIntVector::ZeroValue;
		if(!V||!V->GetWindow().IsValid()||!FSlateApplication::Get().TakeScreenshot(V->GetWindow().ToSharedRef(),Pixels,Size)){Test->AddError(TEXT("Parry actual viewport capture failed"));return;}
		TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Size.X,Size.Y,Pixels,PNG);FFileHelper::SaveArrayToFile(PNG,*FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_OUT")),FString(Name)+TEXT(".png")));
	}
	void EndCase()
	{
		if(Field.IsValid())Field->Destroy();Field.Reset();ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_Guard);ASC->CancelAllAbilities();
		if(Attacker.IsValid())Attacker->Destroy();Attacker.Reset();Fixture.Reset();
	}
	void Cleanup()
	{
		if(Cleaned)return;Cleaned=true;if(ASC.IsValid()){ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(HPDelegate);EndCase();}
		for(const FSaved& S:Saved)if(auto* A=S.Actor.Get()){auto* AASC=A->GetAbilitySystemComponent();AASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),S.HP);AASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),S.Stamina);AASC->RemoveLooseGameplayTag(KZGameplayTags::Block_StaminaRegen);A->SetActorTransform(S.Transform);A->GetCharacterMovement()->SetMovementMode(S.Mode);if(auto* AI=Cast<AAIController>(A->GetController()))if(AI->BrainComponent)AI->BrainComponent->ResumeLogic(TEXT("Owned parry fixture complete"));}
		if(Player.IsValid())Player->GetController<APlayerController>()->SetViewTarget(OldView.Get());if(Camera.IsValid())Camera->Destroy();FApp::SetUseFixedTimeStep(Fixed);FApp::SetFixedDeltaTime(Delta);
	}
	bool Finish(){Cleanup();return true;}
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<UKZAbilitySystemComponent> ASC;TWeakObjectPtr<UKZGuardAbility> Guard;
	TWeakObjectPtr<AKZMonster> Attacker;TWeakObjectPtr<AKZMonsterSkillObject> Field;UClass* AttackerClass=nullptr;FGameplayAbilitySpecHandle GuardHandle;
	TWeakObjectPtr<ACameraActor> Camera;TWeakObjectPtr<AActor> OldView;FVector Base;TArray<FSaved> Saved;TStrongObjectPtr<UKZComboDefinitionData> Fixture;
	TSet<FObjectKey> Seen;FDelegateHandle HPDelegate;double Deadline,Delta;float Start=0;int32 Index=0,Effects=0,HPHits=0,ReceivedEffects=0;
	bool Running=false,Cleaned=false,Fixed=false,Captured1=false,Captured2=false,Captured3=false,ObservedParry=false,ObservedCamera=false,ObservedScreen=false,ObservedBillboardDistortion=false;
	float MaxCameraFOVDelta=0,MaxCameraLocationDelta=0;
	FVector MaxCameraLocalAxes=FVector::ZeroVector;
};
class FWait : public IAutomationLatentCommand
{
public:explicit FWait(FAutomationTestBase* T):Test(T),Deadline(FPlatformTime::Seconds()+60.){}
	bool Update() override
	{
		if(!Requested){Requested=true;auto* S=GetMutableDefault<ULevelEditorPlaySettings>();S->NewWindowWidth=1600;S->NewWindowHeight=900;FRequestPlaySessionParams P;P.EditorPlaySettings=S;GEditor->RequestPlaySession(P);}
		for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetCharacterMovement()->IsMovingOnGround()){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It));return true;}
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Owned DevMap PIE did not start"));return true;}return false;
	}
private:FAutomationTestBase* Test;double Deadline;bool Requested=false;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZParryPIE,"Khazan.Parry.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZParryPIE::RunTest(const FString& Parameters)
{
	const auto* D=LoadObject<UKZCharacterDefinitionData>(nullptr,TEXT("/Game/Data/Character/DA_CharacterDefinition_Player.DA_CharacterDefinition_Player"));if(!D)return false;
	int32 Blank=0;for(const auto& G:D->GetInitialAbilityGrants())if(!G.AbilityClass&&G.InputTag==FGameplayTag::EmptyTag)++Blank;
	if(Blank)AddExpectedError(TEXT("BP_Player_C_0 has an InitialAbilityGrant with no AbilityClass in DA_CharacterDefinition_Player (InputTag: None)."),EAutomationExpectedErrorFlags::Contains,Blank,false);
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZParryQA::FWait>(this));return true;
}
#endif
