#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Data/KZCharacterDefinitionData.h"
#include "KZGameplayTags.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/RootMotionSource.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "BrainComponent.h"
#include "AIController.h"
#include "Camera/CameraActor.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "ImageUtils.h"
#include "Curves/CurveFloat.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "AI/KZMonsterAIController.h"
#include "Components/StateTreeAIComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "UObject/UnrealType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZKnockbackAuthor,"Khazan.AnimationTiming.AuthorKnockback",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZKnockbackAuthor::RunTest(const FString&)
{
	if(!FPaths::ProjectDir().Contains(TEXT("Khazan_SlamDistortWork_20261012")))return false;
	const FString Path=TEXT("/Game/Data/Character/Reactions/CF_Monster_Knockback_Deceleration");
	UPackage* Package=CreatePackage(*Path);
	UCurveFloat* Curve=NewObject<UCurveFloat>(Package,TEXT("CF_Monster_Knockback_Deceleration"),RF_Public|RF_Standalone);
	// TEMP: normalized u -> 2u-u*u, chosen to brake continuously instead of a constant-speed hard stop.
	const FKeyHandle First=Curve->FloatCurve.AddKey(0.f,0.f),Last=Curve->FloatCurve.AddKey(1.f,1.f);
	for(FKeyHandle Key:{First,Last}){auto& K=Curve->FloatCurve.GetKey(Key);K.InterpMode=RCIM_Cubic;K.TangentMode=RCTM_User;}
	Curve->FloatCurve.GetKey(First).ArriveTangent=Curve->FloatCurve.GetKey(First).LeaveTangent=2.f;
	Curve->FloatCurve.GetKey(Last).ArriveTangent=Curve->FloatCurve.GetKey(Last).LeaveTangent=0.f;
	const auto Save=[](UObject* O){FSavePackageArgs A;A.TopLevelFlags=RF_Public|RF_Standalone;A.SaveFlags=SAVE_NoError;return UPackage::SavePackage(O->GetPackage(),O,*FPackageName::LongPackageNameToFilename(O->GetPackage()->GetName(),TEXT(".uasset")),A);};
	if(!Save(Curve))return false;
	for(const TCHAR* Family:{TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite")})
	{
		const FString DefinitionPath=FString::Printf(TEXT("/Game/Monsters/%s/Data/DA_Character_%s"),Family,Family);
		UKZCharacterDefinitionData* D=LoadObject<UKZCharacterDefinitionData>(nullptr,*DefinitionPath);if(!D)return false;
		const_cast<FKZHitReactionSettings&>(D->GetHitReactionSettings()).KnockbackTimeMappingCurve=Curve;
		if(!Save(D))return false;
	}
	return true;
}

namespace
{
class FKZKnockbackCommand final:public IAutomationLatentCommand
{
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Monster;
	TArray<TPair<TSubclassOf<AKZMonster>,UAnimMontage*>> Cases;
	TArray<TSharedPtr<FJsonValue>> Results,Samples;TArray<TObjectPtr<UAnimMontage>> OriginalPool;
	TWeakObjectPtr<AStaticMeshActor> Floor,Wall;TWeakObjectPtr<ACameraActor> Camera;
	FVector Origin,Previous,SavedPlayerLocation;FRotator SavedPlayerRotation;
	float Start=0.f,Land=0.f,Distance=0.f,LastSample=0.f;int32 Index=-1,NaturalCases=0;bool bStarted=false,bCaptured=false,bBaseline=false;
	double Deadline;FString Output;
public:
	FKZKnockbackCommand(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),SavedPlayerLocation(P->GetActorLocation()),SavedPlayerRotation(P->GetActorRotation()),Deadline(FPlatformTime::Seconds()+240.)
	{
		Output=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_PARRY_OUT"));bBaseline=!FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_KNOCK_BASELINE")).IsEmpty();
		for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It)if(AAIController* AI=Cast<AAIController>(It->GetController()))if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("Owned knockback fixture"));
		const FString Families[]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite"),TEXT("ApesStoneHandElite"),TEXT("Yetuga")};
		for(const FString& F:Families)
		{
			const FString DPath=FString::Printf(TEXT("/Game/Monsters/%s/Data/DA_Character_%s"),*F,*F);
			const FString BPPath=FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),*F,*F);
			UKZCharacterDefinitionData* D=LoadObject<UKZCharacterDefinitionData>(nullptr,*DPath);UClass* C=LoadClass<AKZMonster>(nullptr,*BPPath);
			if(!D||!C){Test->AddError(TEXT("Missing fixture family ")+F);continue;}
			for(UAnimMontage* M:D->GetHitReactionSettings().Knockbacks)if(M)Cases.Emplace(C,M);
		}
		NaturalCases=Cases.Num();if(NaturalCases){const auto WallCase=Cases[0];Cases.Add(WallCase);} // One real swept wall case.
		Floor=P->GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,10000),FRotator::ZeroRotator);
		Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
		Floor->SetActorScale3D(FVector(30,30,.2));Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
		Camera=P->GetWorld()->SpawnActor<ACameraActor>();P->GetController<APlayerController>()->SetViewTarget(Camera.Get());
	}
	~FKZKnockbackCommand(){Cleanup();}
	void Cleanup()
	{
		if(Monster.IsValid())
		{
			Monster->GetAbilitySystemComponent()->CancelAllAbilities();
			const_cast<FKZHitReactionSettings&>(Monster->GetCharacterDefinition()->GetHitReactionSettings()).Knockbacks=OriginalPool;
			Monster->Destroy();Monster.Reset();
		}
		if(Player.IsValid()){Player->SetActorLocationAndRotation(SavedPlayerLocation,SavedPlayerRotation);Player->GetController<APlayerController>()->SetViewTarget(Player.Get());}
		if(Camera.IsValid()){Camera->Destroy();Camera.Reset();}if(Floor.IsValid()){Floor->Destroy();Floor.Reset();}if(Wall.IsValid()){Wall->Destroy();Wall.Reset();}
	}
	bool Begin()
	{
		++Index;if(Index>=Cases.Num())return false;
		FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Monster=Player->GetWorld()->SpawnActor<AKZMonster>(Cases[Index].Key,FVector(0,0,10250),FRotator::ZeroRotator,Params);
		if(!Monster.IsValid()){Test->AddError(TEXT("Spawn failed"));return false;}
		if(AAIController* AI=Cast<AAIController>(Monster->GetController()))if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("Owned knockback fixture"));
		auto* ASC=Monster->GetAbilitySystemComponent();ASC->CancelAllAbilities();ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()));ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));
		Origin=FVector(0,0,10010+Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST);
		Monster->SetActorLocationAndRotation(Origin,FRotator::ZeroRotator);Monster->GetCharacterMovement()->SetMovementMode(MOVE_Walking);Monster->GetCharacterMovement()->StopMovementImmediately();
		Player->SetActorLocation(FVector(-400,0,10010+Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST));Player->GetCharacterMovement()->StopMovementImmediately();
		auto& Settings=const_cast<FKZHitReactionSettings&>(Monster->GetCharacterDefinition()->GetHitReactionSettings());OriginalPool=Settings.Knockbacks;Settings.Knockbacks={Cases[Index].Value};Distance=Settings.KnockbackDistance;
		Camera->SetActorLocation(Origin+FVector(250,-600,150));Camera->SetActorRotation((Origin+FVector(120,0,0)-Camera->GetActorLocation()).Rotation());
		Land=0.f;for(const auto& N:Cases[Index].Value->Notifies)if(N.NotifyName==TEXT("HitLand"))Land=N.GetTime()/Cases[Index].Value->RateScale;
		Start=Player->GetWorld()->GetTimeSeconds();LastSample=Start;Previous=Origin;Samples.Reset();bCaptured=false;
		if(Index==NaturalCases)
		{
			Wall=Player->GetWorld()->SpawnActor<AStaticMeshActor>(Origin+FVector(Monster->GetCapsuleComponent()->GetScaledCapsuleRadius()+105,0,100),FRotator::ZeroRotator);
			Wall->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);Wall->GetStaticMeshComponent()->SetStaticMesh(Floor->GetStaticMeshComponent()->GetStaticMesh());Wall->SetActorScale3D(FVector(.1,12,8));Wall->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
		}
		Monster->PlayHitReaction(EKZHitReactionType::Knockback,Player.Get());
		Test->TestTrue(TEXT("Knockback event starts the actual Ability"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));return true;
	}
	virtual bool Update()override
	{
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Knockback runtime watchdog"));return true;}
		if(!bStarted){bStarted=true;if(!Begin())return Finish();}
		if(!Monster.IsValid())return Finish();
		const float Now=Player->GetWorld()->GetTimeSeconds(),Age=Now-Start;
		const FVector Position=Monster->GetActorLocation();
		if(Now>LastSample)
		{
			auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("time"),Age);Row->SetNumberField(TEXT("x"),Position.X-Origin.X);Row->SetNumberField(TEXT("speed"),(Position.X-Previous.X)/(Now-LastSample));Row->SetNumberField(TEXT("yaw"),Monster->GetActorRotation().Yaw);Samples.Add(MakeShared<FJsonValueObject>(Row));Previous=Position;LastSample=Now;
		}
		if(!bCaptured&&Age>.3f)
		{
			bCaptured=true;TArray<FColor> Pixels;FViewport* V=GEngine&&GEngine->GameViewport?GEngine->GameViewport->Viewport:nullptr;
			if(V&&V->ReadPixels(Pixels)){TArray<uint8> PNG;const FIntPoint Size=V->GetSizeXY();FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,PNG);FFileHelper::SaveArrayToFile(PNG,*(Output/FString::Printf(TEXT("Knockback_%02d.png"),Index)));}
		}
		const bool Active=Monster->GetAbilitySystemComponent()->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting);
		if(Active&&Age<Cases[Index].Value->GetPlayLength()/Cases[Index].Value->RateScale+1.f)return false;
		Test->TestFalse(TEXT("Recovery finishes"),Active);
		if(Land>0)
		{
			if(Index==NaturalCases)Test->TestTrue(TEXT("Knockback sweeps against the wall without crossing"),Position.X-Origin.X>30.f&&Position.X-Origin.X<102.f);
			else Test->TestTrue(TEXT("Horizontal target distance retained"),FMath::Abs(Position.X-Origin.X-Distance)<12.f);
			Test->TestFalse(TEXT("Only this reaction's motion source is released"),Monster->GetCharacterMovement()->HasRootMotionSources());
			if(!bBaseline&&Index!=NaturalCases)
			{
				float Early=0.f,Late=0.f;int32 EarlyN=0,LateN=0;
				for(auto S:Samples){const auto R=S->AsObject();const double Time=R->GetNumberField(TEXT("time"));if(Time>Land*.1&&Time<Land*.35){Early+=R->GetNumberField(TEXT("speed"));++EarlyN;}if(Time>Land*.7&&Time<Land*.9){Late+=R->GetNumberField(TEXT("speed"));++LateN;}}
				Test->TestTrue(TEXT("Velocity decays before the landing stop"),EarlyN&&LateN&&Early/EarlyN>Late/LateN);
			}
		}
		if(Index==NaturalCases)
		{
			// Factories apply immediately: retrigger replaces its old source, cancel removes its new source.
			const auto PreviousMode=Monster->GetMesh()->GetAnimInstance()->RootMotionMode;
			const auto ActiveOwnSources=[this]()
			{
				int32 Count=0;const auto& Group=Monster->GetCharacterMovement()->CurrentRootMotion;
				for(const auto* List:{&Group.RootMotionSources,&Group.PendingAddRootMotionSources})
					for(const auto& Source:*List)if(Source.IsValid()&&Source->InstanceName==TEXT("HitReactionMotion")&&!Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval))++Count;
				return Count;
			};
			Monster->PlayHitReaction(EKZHitReactionType::Knockback,Player.Get());
			Test->TestEqual(TEXT("Retrigger starts its force"),ActiveOwnSources(),1);
			Monster->PlayHitReaction(EKZHitReactionType::Knockback,Player.Get());
			Test->TestEqual(TEXT("Repeated event replaces only its old force"),ActiveOwnSources(),1);
			Monster->GetAbilitySystemComponent()->CancelAllAbilities();
			Test->TestEqual(TEXT("Cancel marks/releases its own force"),ActiveOwnSources(),0);
			Test->TestFalse(TEXT("Cancel releases its hit tag"),Monster->GetAbilitySystemComponent()->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
			Test->TestTrue(TEXT("Cancel restores the prior extraction mode"),Monster->GetMesh()->GetAnimInstance()->RootMotionMode==PreviousMode);
		}
		if(!bBaseline&&Land<=0.f)Test->TestTrue(TEXT("Giant unpaired replacement stays rooted"),FMath::Abs(Position.X-Origin.X)<.01f);
		auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("montage"),Cases[Index].Value->GetPathName());Row->SetBoolField(TEXT("wall_case"),Index==NaturalCases);Row->SetNumberField(TEXT("landing_seconds"),Land);Row->SetNumberField(TEXT("displacement"),Position.X-Origin.X);Row->SetArrayField(TEXT("samples"),Samples);Results.Add(MakeShared<FJsonValueObject>(Row));
		const_cast<FKZHitReactionSettings&>(Monster->GetCharacterDefinition()->GetHitReactionSettings()).Knockbacks=OriginalPool;Monster->Destroy();Monster.Reset();
		if(Begin())return false;return Finish();
	}
	bool Finish()
	{
		auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),!Test->HasAnyErrors());Report->SetBoolField(TEXT("baseline"),bBaseline);Report->SetArrayField(TEXT("cases"),Results);
		FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(Output/TEXT("KnockbackRuntime.json")));Cleanup();return true;
	}
};
// Owned PIE fixture: run actual saved StrongCombo windows, not synthetic hit events.
// Oversized query capsules and high floor are QA geometry; no asset/CDO is modified.
class FKZStrongVictimCommand final:public IAutomationLatentCommand
{
	FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZMonster> Monster;
	TWeakObjectPtr<AAIController> Controller;TWeakObjectPtr<AStaticMeshActor> Floor;
	TWeakObjectPtr<UKZComboActionAbility> Attack;FGameplayAbilitySpecHandle Handle;FName SavedEntry;
	FNameProperty* Entry=nullptr;FTransform SavedTransform;float SavedStamina=0;
	FCollisionResponseContainer SavedResponses;TEnumAsByte<EMovementMode> SavedMode;uint8 SavedCustomMode=0;
	FDelegateHandle DamageHandle;int32 Case=0,Accepted=0,BlendOutFrames=0;bool Checked=false,Cleaned=false;
	double Deadline=FPlatformTime::Seconds()+240.;TArray<TSharedPtr<FJsonValue>> Rows;
	const FString Families[4]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite")};
public:
	FKZStrongVictimCommand(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),SavedTransform(P->GetActorTransform()),
		SavedResponses(P->GetCapsuleComponent()->GetCollisionResponseToChannels()),SavedMode(P->GetCharacterMovement()->MovementMode),SavedCustomMode(P->GetCharacterMovement()->CustomMovementMode)
	{
		auto* ASC=Cast<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent());SavedStamina=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
		ASC->CancelAllAbilities();ASC->ClearComboCommands();P->HandleInputMoveReleased();
		for(const FGameplayAbilitySpec& S:ASC->GetActivatableAbilities())
			if(const auto* A=Cast<UKZComboActionAbility>(S.Ability);A&&A->GetEntryNodeId()==TEXT("StrongAttack01")){Handle=S.Handle;break;}
		if(!Test->TestTrue(TEXT("Actual granted StrongCombo exists"),Handle.IsValid()&&ASC->TryActivateAbility(Handle)))return;
		Attack=Cast<UKZComboActionAbility>(ASC->FindAbilitySpecFromHandle(Handle)->GetPrimaryInstance());
		if(!Test->TestTrue(TEXT("Only live instanced attack is edited"),Attack.IsValid()&&!Attack->HasAnyFlags(RF_ClassDefaultObject)))return;
		SavedEntry=Attack->GetEntryNodeId();ASC->CancelAbilityHandle(Handle);Entry=FindFProperty<FNameProperty>(UKZComboActionAbility::StaticClass(),TEXT("EntryNodeId"));
		P->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
		Floor=P->GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,10000),FRotator::ZeroRotator);
		Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
		Floor->SetActorScale3D(FVector(100,100,.2));Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
		DamageHandle=ASC->OnGameplayEffectAppliedDelegateToTarget.AddLambda([this](UAbilitySystemComponent* Target,const FGameplayEffectSpec& Spec,FActiveGameplayEffectHandle)
		{if(Monster.IsValid()&&Target==Monster->GetAbilitySystemComponent()&&Spec.GetContext().GetSourceObject()==Attack.Get())++Accepted;});
	}
	~FKZStrongVictimCommand(){Cleanup();}
	void RemoveTarget()
	{if(Monster.IsValid()){Monster->GetAbilitySystemComponent()->CancelAllAbilities();Monster->Destroy();Monster.Reset();}if(Controller.IsValid()){Controller->Destroy();Controller.Reset();}}
	void Cleanup()
	{
		if(Cleaned)return;Cleaned=true;RemoveTarget();
		if(Player.IsValid())
		{
			auto* ASC=Player->GetAbilitySystemComponent();ASC->OnGameplayEffectAppliedDelegateToTarget.Remove(DamageHandle);ASC->CancelAbilityHandle(Handle);
			if(Attack.IsValid()&&Entry)Entry->SetPropertyValue_InContainer(Attack.Get(),SavedEntry);
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),SavedStamina);
			Player->SetActorTransform(SavedTransform,false,nullptr,ETeleportType::TeleportPhysics);
			Player->GetCapsuleComponent()->SetCollisionResponseToChannels(SavedResponses);Player->GetCharacterMovement()->SetMovementMode(SavedMode,SavedCustomMode);
		}
		if(Floor.IsValid()){Floor->Destroy();Floor.Reset();}
	}
	bool Finish()
	{
		auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),!Test->HasAnyErrors());Report->SetArrayField(TEXT("actual_strong_cases"),Rows);
		FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
		FFileHelper::SaveStringToFile(Json,*(FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_MONSTER_REPAIR_OUT"))/TEXT("StrongVictimRuntime.json")));Cleanup();return true;
	}
	bool Update()override
	{
		if(!Player.IsValid()||!Attack.IsValid()||!Entry||FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("Strong victim fixture invalid/timeout"));return Finish();}
		auto* ASC=Cast<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent());
		if(!Monster.IsValid())
		{
			if(Case==12)
			{
				for(const TCHAR* F:{TEXT("ApesStoneHandElite"),TEXT("Yetuga")})
				{
					UClass* C=LoadClass<AKZMonster>(nullptr,*FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),F,F));
					FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
					AKZMonster* M=Player->GetWorld()->SpawnActor<AKZMonster>(C,FVector(2500,0,10200),FRotator::ZeroRotator,Params);
					if(!Test->TestNotNull(TEXT("Giant fallback fixture"),M))continue;
					M->GetAbilitySystemComponent()->CancelAllAbilities();M->PlayHitReaction(EKZHitReactionType::VictimFront,Player.Get());
					Test->TestTrue(TEXT("Unconfigured giant retains Knockback pool"),M->GetCharacterDefinition()->GetHitReactionSettings().Knockbacks.Contains(M->GetMesh()->GetAnimInstance()->GetCurrentActiveMontage()));
					if(AController* AI=M->GetController())AI->Destroy();M->Destroy();
				}
				return Finish();
			}
			const FString Family=Families[Case/3];const FName NodeId(*FString::Printf(TEXT("StrongAttack%02d"),Case%3+1));
			const FKZComboNode* Node=Attack->GetComboDefinition()->FindNode(NodeId);if(!Test->TestNotNull(TEXT("Saved strong node"),Node))return Finish();
			float Radius=0.f;
			for(const auto& W:Node->AttackWindows)
			{
				Test->TestTrue(TEXT("Every real StrongCombo window selects VictimFront"),W.HitReaction==EKZHitReactionType::VictimFront);
				for(const auto& K:W.Keys)Radius=FMath::Max(Radius,static_cast<float>(Node->CollisionToActor.TransformPosition(K.Center).Size()+W.Extent.Size()));
			}
			UClass* C=LoadClass<AKZMonster>(nullptr,*FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),*Family,*Family));
			FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Monster=Player->GetWorld()->SpawnActor<AKZMonster>(C,FVector(150,0,10010+Radius+250),FRotator(0,Case%2?180:0,0),Params);
			if(!Test->TestTrue(TEXT("Actual humanoid initialized"),Monster.IsValid()&&Monster->GetCharacterDefinition()))return Finish();
			Controller=Cast<AAIController>(Monster->GetController());
			if(auto* AI=Cast<AKZMonsterAIController>(Controller.Get())){AI->SetActorTickEnabled(false);AI->GetStateTreeComponent()->StopLogic(TEXT("Owned StrongCombo fixture"));AI->GetStateTreeComponent()->SetComponentTickEnabled(false);AI->GetPerceptionComponent()->Deactivate();AI->StopMovement();}
			Monster->GetCapsuleComponent()->SetCapsuleSize(Radius+250,Radius+250);Monster->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
			auto* Victim=Monster->GetAbilitySystemComponent();Victim->CancelAllAbilities();
			Victim->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(),1000);Victim->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),1000);
			Victim->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(),1000);Victim->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),1000);
			Player->GetCharacterMovement()->StopMovementImmediately();Player->SetActorLocationAndRotation(FVector(0,0,10010+Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+UCharacterMovementComponent::MIN_FLOOR_DIST),FRotator::ZeroRotator,false,nullptr,ETeleportType::TeleportPhysics);Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));ASC->ClearComboCommands();
			Entry->SetPropertyValue_InContainer(Attack.Get(),NodeId);Accepted=0;Checked=false;BlendOutFrames=0;
			if(!Test->TestTrue(TEXT("Actual StrongCombo activates"),ASC->TryActivateAbility(Handle)))return Finish();return false;
		}
		if(Accepted>0)
		{
			auto* Anim=Monster->GetMesh()->GetAnimInstance();auto* Victim=Monster->GetAbilitySystemComponent();
			UAnimMontage* Expected=Monster->GetCharacterDefinition()->GetHitReactionSettings().VictimFront;
			if(Victim->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting))
			{
				// GetCurrentActiveMontage excludes blend-out instances while the Task
				// still legitimately owns its hit tag until OnCompleted.
				if(UAnimMontage* Current=Anim->GetCurrentActiveMontage())
					Test->TestTrue(*FString::Printf(TEXT("Accepted StrongCombo fixed pose: actual=%s expected=%s"),*Current->GetPathName(),*Expected->GetPathName()),Current==Expected);
				else ++BlendOutFrames;
				if(auto* I=Anim->GetActiveInstanceForMontage(Expected))
				{Test->TestTrue(TEXT("Unpaired victim disables only its montage root motion"),I->IsRootMotionDisabled());Checked=true;}
				const auto& RMS=Monster->GetCharacterMovement()->CurrentRootMotion;
				Test->TestFalse(TEXT("VictimFront acquires no Knockback/Launch motion task"),RMS.HasActiveRootMotionSources());
			}
			if(!Attack->IsActive()&&!Victim->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting))
			{
				Test->TestTrue(TEXT("Actual accepted hit was observed during fixed pose"),Checked);
				const FKZComboNode* Node=Attack->GetComboDefinition()->FindNode(FName(*FString::Printf(TEXT("StrongAttack%02d"),Case%3+1)));
				TSet<FName> Groups;int32 ExpectedHits=0;
				for(const auto& W:Node->AttackWindows){if(W.HitGroup.IsNone())++ExpectedHits;else Groups.Add(W.HitGroup);}
				Test->TestEqual(TEXT("Existing actual window/group dedup retained"),Accepted,ExpectedHits+Groups.Num());
				const auto& Settings=Monster->GetCharacterDefinition()->GetHitReactionSettings();
				Monster->PlayHitReaction(EKZHitReactionType::Short,Player.Get());Test->TestTrue(TEXT("Other short hits retain their pool"),Settings.ShortHits.Contains(Anim->GetCurrentActiveMontage()));Victim->CancelAllAbilities();
				Monster->PlayHitReaction(EKZHitReactionType::Knockback,Player.Get());Test->TestTrue(TEXT("Other Knockbacks retain their pool"),Settings.Knockbacks.Contains(Anim->GetCurrentActiveMontage()));Victim->CancelAllAbilities();
				Monster->PlayHitReaction(EKZHitReactionType::VictimFront,Player.Get());Monster->PlayHitReaction(EKZHitReactionType::VictimFront,Player.Get());
				Test->TestTrue(TEXT("Repeated front reaction retains fixed pose"),Anim->GetCurrentActiveMontage()==Settings.VictimFront);Victim->CancelAllAbilities();
				Test->TestFalse(TEXT("Cancel releases its reaction tag"),Victim->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
				auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("family"),Families[Case/3]);Row->SetStringField(TEXT("node"),Node->NodeId.ToString());Row->SetStringField(TEXT("montage"),Expected->GetPathName());Row->SetNumberField(TEXT("accepted_hits"),Accepted);Row->SetNumberField(TEXT("inactive_blend_out_frames"),BlendOutFrames);Rows.Add(MakeShared<FJsonValueObject>(Row));
				RemoveTarget();++Case;
			}
		}
		return false;
	}
};
class FKZStrongVictimFindPlayer final:public IAutomationLatentCommand
{
	FAutomationTestBase* Test;double Deadline=FPlatformTime::Seconds()+90.;
public:
	FKZStrongVictimFindPlayer(FAutomationTestBase* T):Test(T){}
	bool Update()override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE)for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->GetController()&&It->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())>0){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FKZStrongVictimCommand>(Test,*It));return true;}
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("No initialized PIE Player"));return true;}return false;
	}
};
class FKZKnockbackFindPlayer final:public IAutomationLatentCommand
{
	FAutomationTestBase* Test;double Deadline=FPlatformTime::Seconds()+90.;
public:
	FKZKnockbackFindPlayer(FAutomationTestBase* T):Test(T){}
	bool Update()override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE)for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->GetController()&&It->GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute())>0){FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FKZKnockbackCommand>(Test,*It));return true;}
		if(FPlatformTime::Seconds()>Deadline){Test->AddError(TEXT("No initialized PIE Player"));return true;}return false;
	}
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZKnockbackPIE,"Khazan.AnimationTiming.KnockbackPIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZKnockbackPIE::RunTest(const FString&){ADD_LATENT_AUTOMATION_COMMAND(FKZKnockbackFindPlayer(this));return true;}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZStrongVictimPIE,"Khazan.CombatReaction.StrongVictimFrontPIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZStrongVictimPIE::RunTest(const FString&){ADD_LATENT_AUTOMATION_COMMAND(FKZStrongVictimFindPlayer(this));return true;}
#endif
