// Actual engine integration; numeric shapes/damage below are unsaved test stimuli.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/App.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/KZHitReactionAbility.h"
#include "Ability/PlayerAbility/KZDodgeAbility.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Attribute/KZAttributeSet.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Camera/CameraActor.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Animation/AnimInstance.h"
#include "UObject/UnrealType.h"
#include "UObject/StrongObjectPtr.h"
#include "KZGameplayTags.h"

namespace KZDefenseQA
{
struct FCase { const TCHAR* Name; float HitAt; int32 Kind; bool EarlyCancel; float ExpectedHP; };
const FCase Cases[] = {
	{TEXT("MeleeImmediate"),.005f,0,false,100}, {TEXT("Melee095"),.095f,0,false,100},
	{TEXT("Melee105"),.105f,0,false,93}, {TEXT("MeleeLate"),.2f,0,false,93},
	{TEXT("MeleeCanceled"),.03f,0,true,93}, {TEXT("FieldEarly"),.03f,1,false,100},
	{TEXT("FieldLate"),.12f,1,false,93}, {TEXT("SameGroupEarlyLate"),.02f,2,false,100},
	{TEXT("IndependentGroupEarlyLate"),.02f,3,false,93},
	{TEXT("ProjectileEarly"),.03f,4,false,100}, {TEXT("ProjectileLate"),.12f,4,false,93},
};
class FRun : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* T, AKZPlayer* P) : Test(T), Player(P), ASC(Cast<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent())), Deadline(FPlatformTime::Seconds()+180.)
	{
		Fixed=FApp::UseFixedTimeStep(); Delta=FApp::GetFixedDeltaTime(); FApp::SetUseFixedTimeStep(true); FApp::SetFixedDeltaTime(.005);
		Base=P->GetActorLocation(); P->HandleInputMoveReleased(); ASC->CancelAllAbilities();
		Camera=P->GetWorld()->SpawnActor<ACameraActor>();
		if(auto* Controller=P->GetController<APlayerController>()) Controller->SetViewTarget(Camera.Get());
		ASC->AddLooseGameplayTag(KZGameplayTags::Block_StaminaRegen);
		for(const auto& S:ASC->GetActivatableAbilities()) if(Cast<UKZDodgeAbility>(S.Ability)) Dodges.Add(S.Handle);
		for(TActorIterator<AKZMonster> It(P->GetWorld()); It; ++It)
		{
			if(It->GetCharacterDefinition() && It->GetCharacterDefinition()->GetPathName().Contains(TEXT("/Monsters/Swordsman/"))) AttackerClass=It->GetClass();
			Saved.Add({*It,It->GetActorTransform()}); It->SetActorLocation(Base+FVector(20000+Saved.Num()*1000,20000,0));
			if(auto* AI=Cast<AAIController>(It->GetController()); AI && AI->BrainComponent) AI->BrainComponent->PauseLogic(TEXT("Owned defense fixture"));
		}
	}
	~FRun() override { Cleanup(); }
	bool Update() override
	{
		if(!Player.IsValid() || !ASC.IsValid() || FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Defense PIE timeout")); return Finish(); }
		if(!Running)
		{
			if(Index>=UE_ARRAY_COUNT(Cases)) { LifetimeChecks(); Test->AddInfo(TEXT("DEFENSE_CASES_COMPLETE")); return Finish(); }
			if(!StartCase()) return Finish(); return false;
		}
		const auto& C=Cases[Index]; const float Age=Player->GetWorld()->GetTimeSeconds()-Start;
		if(Camera.IsValid()){const FVector Location=Player->GetActorLocation()+FVector(-400,-400,220);Camera->SetActorLocation(Location);Camera->SetActorRotation((Player->GetActorLocation()-FVector(0,0,30)-Location).Rotation());}
		if((C.Kind==1 || C.Kind==4) && !ObjectSpawned && Age>=C.HitAt)
		{
			ObjectSpawned=true;
			FKZMonsterPatternObject D; D.Id=TEXT("DefenseFixtureObject"); D.bField=C.Kind==1; D.FieldExtent=FVector(5000); D.Radius=40; D.Scale=1; D.LifeSeconds=1; D.HPDamage=7; D.StaminaDamage=8;
			Field=Player->GetWorld()->SpawnActor<AKZMonsterSkillObject>(Player->GetActorLocation(),FRotator::ZeroRotator);
			Field->Initialize(D,Attacker->GetCharacterDefinition()->GetMonsterStaminaSettings().DamageEffect,Attacker.Get(),Attacker.Get());
			if(C.Kind==4)Field->Shoot(Player.Get());
		}
		for(TObjectIterator<UAudioComponent> It;It;++It)if(!PreviousComponents.Contains(*It)&&It->GetWorld()==Player->GetWorld()&&It->GetSound()==SuccessSound.Get()&&It->IsPlaying())SawSound=true;
		for(TObjectIterator<UNiagaraComponent> It;It;++It)if(!PreviousComponents.Contains(*It)&&It->GetWorld()==Player->GetWorld()&&It->GetAsset())
		{
			SawDodgeFX|=It->GetAsset()->GetName()==TEXT("NS_Cursed_Magic_Dash1");
			SawSuccessFX|=It->GetAsset()->GetName()==TEXT("NS_Cursed_Magic_Blink1");
		}
		if(!Screenshot && (Index==0 || Index==5) && Age>=.075f)
		{Screenshot=true;const FString Folder=FPlatformMisc::GetEnvironmentVariable(TEXT("KZ_BEAST_OUT"));FScreenshotRequest::RequestScreenshot(FPaths::Combine(Folder,FString::Printf(TEXT("DodgeFeedback_%d.png"),Index)),false,false);}
		if(Age<.35f) return false;
		Test->TestTrue(FString::Printf(TEXT("%s actual incoming GE/HP result"),C.Name),FMath::IsNearlyEqual(HP(),C.ExpectedHP));
		Test->TestFalse(FString::Printf(TEXT("%s exact deadline closes immunity"),C.Name),Dodge.IsValid() && Dodge->IsInvulnerableNow());
		Test->TestEqual(TEXT("Our invulnerability tag expires"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),0);
		const bool ExpectedCue=C.HitAt<.1f&&!C.EarlyCancel;
		Test->TestTrue(TEXT("Actual Dodge Niagara component spawned"),SawDodgeFX);
		Test->TestEqual(TEXT("Successful overlap alone creates Niagara feedback"),SawSuccessFX,ExpectedCue);
		Test->TestEqual(TEXT("Successful overlap alone plays authored audio"),SawSound,ExpectedCue);
		Test->AddInfo(FString::Printf(TEXT("DEFENSE_CASE %s HP=%g worldAge=%g"),C.Name,HP(),Age));
		EndCase(); ++Index; Running=false; return false;
	}
private:
	float HP() const { return ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()); }
	bool StartCase()
	{
		if(!Test->TestEqual(TEXT("All eight saved Dodge entries granted"),Dodges.Num(),8) || !AttackerClass) return false;
		ASC->CancelAllAbilities(); ASC->ClearComboCommands(); Player->HandleInputMoveReleased();
		ObjectSpawned=SawSound=SawDodgeFX=SawSuccessFX=Screenshot=false;
		PreviousComponents.Reset();
		for(TObjectIterator<UActorComponent> It;It;++It)if(It->GetWorld()==Player->GetWorld())PreviousComponents.Add(*It);
		Player->SetActorLocationAndRotation(Base,FRotator::ZeroRotator); Player->GetCharacterMovement()->StopMovementImmediately(); Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),100); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),100);
		FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Attacker=Player->GetWorld()->SpawnActor<AKZMonster>(AttackerClass,Base+FVector(200,0,0),FRotator(0,180,0),Params);
		if(!Attacker.IsValid()) return false;
		if(auto* AI=Cast<AAIController>(Attacker->GetController()); AI && AI->BrainComponent) AI->BrainComponent->PauseLogic(TEXT("Owned defense attacker"));
		Attacker->GetCharacterMovement()->DisableMovement(); Attacker->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
		auto* MASC=Cast<UKZAbilitySystemComponent>(Attacker->GetAbilitySystemComponent()); MASC->CancelAllAbilities();
		const FGameplayAbilitySpecHandle DodgeHandle=Dodges[Index%Dodges.Num()];
		ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_A,DodgeHandle);
		Dodge=Cast<UKZDodgeAbility>(ASC->FindAbilitySpecFromHandle(DodgeHandle)->GetPrimaryInstance());
		if(!Test->TestTrue(TEXT("Actual input-routed Dodge starts immune immediately"),Dodge.IsValid() && Dodge->IsInvulnerableNow())) return false;
		const FObjectPropertyBase* SoundProperty=FindFProperty<FObjectPropertyBase>(Dodge->GetClass(),TEXT("SuccessSound"));
		SuccessSound=SoundProperty?Cast<USoundBase>(SoundProperty->GetObjectPropertyValue_InContainer(Dodge.Get())):nullptr;
		if(!Test->TestTrue(TEXT("Actual success cue is authored"),SuccessSound.IsValid()))return false;
		Start=Player->GetWorld()->GetTimeSeconds();
		const auto& C=Cases[Index]; if(C.EarlyCancel) ASC->CancelAbilityHandle(DodgeHandle);
		if(C.Kind!=1 && C.Kind!=4)
		{
			FGameplayAbilitySpecHandle Handle; UKZComboActionAbility* Attack=nullptr;
			for(const auto& S:MASC->GetActivatableAbilities())
				if(auto* A=Cast<UKZComboActionAbility>(S.GetPrimaryInstance()); A && A->GetComboDefinition() && A->GetComboDefinition()->FindNode(A->GetEntryNodeId()) && !A->GetComboDefinition()->FindNode(A->GetEntryNodeId())->AttackWindows.IsEmpty()) { Attack=A; Handle=S.Handle; break; }
			if(!Test->TestNotNull(TEXT("Actual granted attack instance"),Attack)) return false;
			Fixture.Reset(DuplicateObject<UKZComboDefinitionData>(Attack->GetComboDefinition(),GetTransientPackage()));
			FKZComboNode Node=*Attack->GetComboDefinition()->FindNode(Attack->GetEntryNodeId()); Node.CommandEdges.Reset(); Node.CollisionToActor=FTransform::Identity; Node.AttackWindows.Reset();
			auto Window=[&](float Begin,float End,FName Group)
			{
				FKZAttackCollisionWindow W; W.StartTime=Begin; W.EndTime=End; W.Shape=EKZAttackCollisionShape::Box; W.Extent=FVector(5000); W.HPDamage=7; W.StaminaDamage=8; W.bBlockable=false; W.HitGroup=Group;
				FKZAttackCollisionKey K; K.Time=Begin; K.Center=FVector(200,0,0); W.Keys.Add(K); K.Time=End; W.Keys.Add(K); return W;
			};
			Node.AttackWindows.Add(Window(C.HitAt,C.HitAt+.015f,C.Kind==2?FName(TEXT("Shared")):NAME_None));
			if(C.Kind==2 || C.Kind==3) Node.AttackWindows.Add(Window(.15f,.17f,C.Kind==2?FName(TEXT("Shared")):NAME_None));
			*FindFProperty<FArrayProperty>(Fixture->GetClass(),TEXT("Nodes"))->ContainerPtrToValuePtr<TArray<FKZComboNode>>(Fixture.Get())={Node};
			FindFProperty<FObjectPropertyBase>(Attack->GetClass(),TEXT("ComboDefinition"))->SetObjectPropertyValue_InContainer(Attack,Fixture.Get());
			FindFProperty<FClassProperty>(Attack->GetClass(),TEXT("CostGameplayEffectClass"))->SetObjectPropertyValue_InContainer(Attack,nullptr);
			if(!Test->TestTrue(TEXT("Actual montage/collision attacker starts"),MASC->TryActivateAbility(Handle))) return false;
		}
		Running=true; return true;
	}
	void LifetimeChecks()
	{
		for(const auto Handle:Dodges)
		{
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),100);
			ASC->AddLooseGameplayTag(KZGameplayTags::State_Invulnerable);
			Test->TestTrue(TEXT("Eight-direction reactivation succeeds"),ASC->TryActivateAbility(Handle));
			Test->TestEqual(TEXT("Dodge owns exactly one additional contribution"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),2);
			ASC->CancelAbilityHandle(Handle);
			Test->TestEqual(TEXT("Cancel preserves another contributor"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),1);
			ASC->RemoveLooseGameplayTag(KZGameplayTags::State_Invulnerable);
		}
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),0);
		Test->TestFalse(TEXT("Cost failure never grants immunity"),ASC->TryActivateAbility(Dodges[0]));
		Test->TestEqual(TEXT("Failure leaves no tag"),ASC->GetTagCount(KZGameplayTags::State_Invulnerable),0);
	}
	void EndCase()
	{
		ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_A); ASC->CancelAllAbilities();
		if(Field.IsValid()) Field->Destroy(); Field.Reset(); if(Attacker.IsValid()) Attacker->Destroy(); Attacker.Reset(); Fixture.Reset();
	}
	void Cleanup()
	{
		if(Cleaned) return; Cleaned=true;
		if(ASC.IsValid()) { EndCase(); ASC->RemoveLooseGameplayTag(KZGameplayTags::Block_StaminaRegen); }
		if(Camera.IsValid()){if(Player.IsValid())if(auto* C=Player->GetController<APlayerController>())C->SetViewTarget(Player.Get());Camera->Destroy();}
		for(const auto& S:Saved) if(S.Key.IsValid())
		{
			S.Key->SetActorTransform(S.Value);
			if(auto* AI=Cast<AAIController>(S.Key->GetController()); AI && AI->BrainComponent) AI->BrainComponent->ResumeLogic(TEXT("Owned defense fixture complete"));
		}
		FApp::SetUseFixedTimeStep(Fixed); FApp::SetFixedDeltaTime(Delta);
	}
	bool Finish() { Cleanup(); return true; }
	FAutomationTestBase* Test; TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<UKZAbilitySystemComponent> ASC; TWeakObjectPtr<UKZDodgeAbility> Dodge;
	TWeakObjectPtr<AKZMonster> Attacker; TWeakObjectPtr<AKZMonsterSkillObject> Field; TStrongObjectPtr<UKZComboDefinitionData> Fixture;
	TWeakObjectPtr<ACameraActor> Camera;
	TWeakObjectPtr<USoundBase> SuccessSound;
	TArray<FGameplayAbilitySpecHandle> Dodges; TArray<TPair<TWeakObjectPtr<AKZMonster>,FTransform>> Saved; UClass* AttackerClass=nullptr;
	FVector Base; float Start=0; double Deadline; int32 Index=0; bool Running=false,Cleaned=false,Fixed=false; double Delta=0;
	bool ObjectSpawned=false,SawSound=false,SawDodgeFX=false,SawSuccessFX=false,Screenshot=false;
	TSet<TWeakObjectPtr<UActorComponent>> PreviousComponents;
};
class FWait : public IAutomationLatentCommand
{
public: FWait(FAutomationTestBase* T):Test(T),Until(FPlatformTime::Seconds()+90.){}
	bool Update() override
	{
		for(const FWorldContext& C:GEngine->GetWorldContexts()) if(C.WorldType==EWorldType::PIE && C.World() && C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It) if(It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance())
				{ FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It)); return true; }
		if(FPlatformTime::Seconds()>Until) { Test->AddError(TEXT("Owned DevMap PIE not started")); return true; } return false;
	}
private: FAutomationTestBase* Test; double Until;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZBeastDodgeDefense,"Khazan.BeastDodge.DefensePIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZBeastDodgeDefense::RunTest(const FString&)
{
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZDefenseQA::FWait>(this)); return true;
}
#endif
