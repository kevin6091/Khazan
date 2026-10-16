// Native PIE stimuli below are transient test values, not gameplay defaults.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/App.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/KZHitReactionAbility.h"
#include "Ability/PlayerAbility/KZDodgeAbility.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "Attribute/KZAttributeSet.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "KZGameplayTags.h"

namespace KZRecoveryQA
{
class FRun : public IAutomationLatentCommand
{
public:
	FRun(FAutomationTestBase* T,AKZPlayer* P):Test(T),Player(P),ASC(Cast<UKZAbilitySystemComponent>(P->GetAbilitySystemComponent())),Until(FPlatformTime::Seconds()+120.)
	{
		Fixed=FApp::UseFixedTimeStep(); Delta=FApp::GetFixedDeltaTime(); FApp::SetUseFixedTimeStep(true); FApp::SetFixedDeltaTime(.005);
		for(TActorIterator<AKZMonster> It(P->GetWorld());It;++It) if(auto* AI=Cast<AAIController>(It->GetController());AI&&AI->BrainComponent) { AI->BrainComponent->PauseLogic(TEXT("Recovery fixture")); Paused.Add(AI); }
		for(const auto& S:ASC->GetActivatableAbilities()) if(Cast<UKZDodgeAbility>(S.Ability)) { DodgeHandle=S.Handle; break; }
		ASC->AddLooseGameplayTag(KZGameplayTags::Block_StaminaRegen);
	}
	~FRun() override { Cleanup(); }
	bool Update() override
	{
		if(!Player.IsValid()||!ASC.IsValid()||FPlatformTime::Seconds()>Until) { Test->AddError(TEXT("Recovery fixture timeout")); Cleanup(); return true; }
		if(Index>=6) { Test->AddInfo(TEXT("RECOVERY_CASES_COMPLETE")); Cleanup(); return true; }
		const float Now=Player->GetWorld()->GetTimeSeconds();
		if(Stage==0)
		{
			ASC->CancelAllAbilities(); ASC->ClearComboCommands(); Player->HandleInputMoveReleased();
			Player->SetActorLocationAndRotation(FVector(-4000,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),FRotator::ZeroRotator);
			Player->GetCharacterMovement()->StopMovementImmediately(); Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
			ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(),100); ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),100);
			const FGameplayTag Events[]={KZGameplayTags::Event_Combat_Hit_Short,KZGameplayTags::Event_Combat_Hit_Knockback,KZGameplayTags::Event_Combat_Hit_Launch};
			Event=Events[Index%3]; SendHit(); Start=Now; Stage=1;
			Test->TestTrue(TEXT("Reaction starts and owns input lock"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting)&&!Player->GetLocomotionComponent()->IsMovementInputAllowed());
			Test->TestFalse(TEXT("Dodge blocked inside initial hit lock"),ASC->TryActivateAbility(DodgeHandle)); return false;
		}
		if(Stage==1)
		{
			if(Index>=3 && Now-Start>=.075f && !Retriggered) { SendHit(); Retriggered=true; LastHit=Now; }
			if(Index>=3 && Now-Start>=.115f && Now-LastHit<.095f)
				Test->TestTrue(TEXT("Old timer cannot unlock retriggered hit"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
			const float HitAge=Now-(Retriggered?LastHit:Start); if(HitAge<.12f) return false;
			Test->TestFalse(TEXT("Hit state cleared promptly after last hit"),ASC->HasMatchingGameplayTag(KZGameplayTags::State_HitReacting));
			Test->TestTrue(TEXT("Movement permission restored after last hit"),Player->GetLocomotionComponent()->IsMovementInputAllowed());
			Test->TestTrue(TEXT("Reaction restores ordinary ground/air CMC physics"),Player->GetCharacterMovement()->MovementMode==MOVE_Walking || Player->GetCharacterMovement()->MovementMode==MOVE_Falling);
			// Use the actual input router for the next action; no direct montage playback.
			if(Index%2==0) ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_A,DodgeHandle);
			const auto* Spec=ASC->FindAbilitySpecFromHandle(DodgeHandle); const auto* Dodge=Spec?Cast<UKZDodgeAbility>(Spec->GetPrimaryInstance()):nullptr;
			if(Index%2==0) Test->TestTrue(TEXT("Next input starts a real invulnerable Dodge"),Dodge&&Dodge->IsActive()&&Dodge->IsInvulnerableNow());
			Test->AddInfo(FString::Printf(TEXT("RECOVERY_CASE index=%d event=%s hitAge=%g mode=%d"),Index,*Event.ToString(),HitAge,int32(Player->GetCharacterMovement()->MovementMode)));
			ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_A); ASC->CancelAllAbilities();
			Player->HandleInputMove(FVector2D(1,0),FRotator::ZeroRotator); MoveStart=Player->GetActorLocation(); Start=Now; Stage=2; return false;
		}
		Player->HandleInputMove(FVector2D(1,0),FRotator::ZeroRotator);
		if(Now-Start<.08f) return false;
		if(Index%2==1) Test->TestTrue(TEXT("Real CMC consumes movement input after recovery"),FVector::Dist2D(Player->GetActorLocation(),MoveStart)>.1f);
		Player->HandleInputMoveReleased(); ++Index; Stage=0; Retriggered=false; return false;
	}
private:
	void SendHit() { FGameplayEventData Payload; Payload.EventTag=Event; Payload.Target=Player.Get(); ASC->HandleGameplayEvent(Event,&Payload); }
	void Cleanup()
	{
		if(Cleaned)return; Cleaned=true;
		if(ASC.IsValid()) { ASC->CancelAllAbilities(); ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_A); ASC->RemoveLooseGameplayTag(KZGameplayTags::Block_StaminaRegen); }
		if(Player.IsValid())Player->HandleInputMoveReleased();
		for(auto AI:Paused)if(AI.IsValid()&&AI->BrainComponent)AI->BrainComponent->ResumeLogic(TEXT("Recovery complete"));
		FApp::SetUseFixedTimeStep(Fixed); FApp::SetFixedDeltaTime(Delta);
	}
	FAutomationTestBase* Test; TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<UKZAbilitySystemComponent> ASC;
	TArray<TWeakObjectPtr<AAIController>> Paused; FGameplayAbilitySpecHandle DodgeHandle; FGameplayTag Event; FVector MoveStart;
	double Until,Delta=0; float Start=0,LastHit=0; int32 Index=0,Stage=0; bool Fixed=false,Cleaned=false,Retriggered=false;
};
class FWait : public IAutomationLatentCommand
{
public:FWait(FAutomationTestBase* T):Test(T),Until(FPlatformTime::Seconds()+90.){}
	bool Update() override
	{
		for(const auto& C:GEngine->GetWorldContexts())if(C.WorldType==EWorldType::PIE&&C.World()&&C.World()->HasBegunPlay())
			for(TActorIterator<AKZPlayer> It(C.World());It;++It)if(It->IsPlayerControlled()&&It->GetMesh()->GetAnimInstance()) { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FRun>(Test,*It)); return true; }
		if(FPlatformTime::Seconds()>Until){Test->AddError(TEXT("No owned recovery PIE"));return true;} return false;
	}
private:FAutomationTestBase* Test;double Until;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZBeastRecovery,"Khazan.BeastDodge.RecoveryPIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZBeastRecovery::RunTest(const FString&) { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZRecoveryQA::FWait>(this)); return true; }
#endif
