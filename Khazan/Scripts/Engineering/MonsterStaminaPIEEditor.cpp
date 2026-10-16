// Isolated Work-only integration probe. No package save, authored montage changes, or private completion writes.
// Automation RunTests Khazan.Monster.StaminaPIE, then the owned worker starts PIE on DevMap.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "StateTree.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/KZActionAbility.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Ability/PlayerAbility/KZBrutalAttackAbility.h"
#include "AI/KZMonsterAIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Attribute/KZAttributeSet.h"
#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Character/Component/KZLocomotionComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StateTreeAIComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UnrealType.h"

namespace KZMonsterStaminaPIE
{
using FObject = TSharedPtr<FJsonObject>;
const TCHAR* WorkRoot = TEXT("C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/");
const TCHAR* Families[] = {TEXT("Swordsman"), TEXT("SwordShield"), TEXT("HeavySwordsman"), TEXT("HalberdElite"), TEXT("ApesStoneHandElite"), TEXT("Yetuga")};
FObject Object() { return MakeShared<FJsonObject>(); }
TSharedPtr<FJsonValue> Json(const FObject& Value) { return MakeShared<FJsonValueObject>(Value); }
FString Path(const UObject* Value) { return Value ? Value->GetPathName() : TEXT(""); }

// Reflected writes are limited to a transient Definition fixture and its actor pointer.
// Gameplay execution/completion state is always observed through public APIs.
template<typename T> T* Field(UObject* Owner, const TCHAR* Name)
{
	FProperty* Property = Owner ? Owner->GetClass()->FindPropertyByName(Name) : nullptr;
	return Property ? Property->ContainerPtrToValuePtr<T>(Owner) : nullptr;
}

enum class EScenario : uint8 { Authored, InfiniteCancel, EndPlay, PairedDeath, UnpairedDeath };
enum class EStage : uint8 { Spawn, NoRegen, Attack, WaitExhaustion, Timeout, Pair, Infinite, CancelledInfinite, Reenter, Unpossessed, Destroyed, Dead };

class FProbe : public IAutomationLatentCommand
{
public:
	FProbe(FAutomationTestBase* InTest, AKZPlayer* InPlayer) : Test(InTest), Player(InPlayer)
	{
		PlayerASC = Cast<UKZAbilitySystemComponent>(InPlayer->GetAbilitySystemComponent());
		SavedPlayerLocation = InPlayer->GetActorLocation(); SavedPlayerRotation = InPlayer->GetActorRotation();
		SavedControlRotation = InPlayer->GetController()->GetControlRotation();
		SavedHP = PlayerASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
		SavedStamina = PlayerASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
		SavedMaxHP = PlayerASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute());
		SavedMaxStamina = PlayerASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute());
		FGameplayTagContainer Actions; Actions.AddTag(KZGameplayTags::Ability_Action); PlayerASC->CancelAbilities(&Actions);
		PlayerASC->ClearComboCommands(); InPlayer->HandleInputMoveReleased();
		PlayerMovementTagBaseline = PlayerASC->GetTagCount(KZGameplayTags::Block_Movement_Input);
		PlayerRegenTagBaseline = PlayerASC->GetTagCount(KZGameplayTags::Block_StaminaRegen);
		for (const FGameplayAbilitySpec& Spec : PlayerASC->GetActivatableAbilities())
			if (Cast<UKZBrutalAttackAbility>(Spec.Ability)) BrutalHandle = Spec.Handle;
		FKZMovementConstraint Foreign; Foreign.MaxAllowedGait = EKZGait::Walk; Foreign.bOverrideRotationMode = true;
		Foreign.RotationModeOverride = EKZRotationMode::LockOn; Foreign.DebugName = TEXT("StaminaPIE foreign player constraint");
		PlayerConstraint = InPlayer->GetLocomotionComponent()->AcquireMovementConstraint(InPlayer, Foreign);
		Deadline = FPlatformTime::Seconds() + 420.0; // QA watchdog, not a gameplay timeout.
		PostTickHandle = FWorldDelegates::OnWorldPostActorTick.AddRaw(this, &FProbe::OnPostTick);
		Enter(EStage::Spawn, 15.0);
	}
	virtual ~FProbe() override { Cleanup(); }
	virtual bool Update() override
	{
		if (!Player.IsValid() || !PlayerASC.IsValid() || FPlatformTime::Seconds() > Deadline || FPlatformTime::Seconds() > StageDeadline)
		{
			Check(TEXT("PIE fixture advances within its independent wall-clock watchdog"), false);
			return Finish();
		}
		Sample();
		const double Now = Player->GetWorld()->GetTimeSeconds();
		switch (Stage)
		{
		case EStage::Spawn:
			if (!Spawn()) return Finish();
			if (Scenario == EScenario::Authored)
			{
				const float BeforeHP = HP(), BeforeStamina = Stamina();
				const float HPSpend = BeforeHP / 16.f, StaminaSpend = BeforeStamina / 4.f; // Derived QA damage, not product tuning.
				if (!Check(TEXT("Shared damage GE applies to the real monster ASC"), Damage(HPSpend, StaminaSpend))) return Finish();
				Check(TEXT("Hit HP and stamina losses are independently attack-provided"), Near(HP(), BeforeHP - HPSpend) && Near(Stamina(), BeforeStamina - StaminaSpend));
				const float BeforeParry = Stamina(), ParryHP = HP();
				Check(TEXT("Invalid parry report has no resource consequence"), !Monster->ReportAttackParried(nullptr) && Near(Stamina(), BeforeParry) && Near(HP(), ParryHP));
				Check(TEXT("Successful parry uses this monster's editable damage"), Monster->ReportAttackParried(Player.Get()) && Near(Stamina(), FMath::Max(0.f, BeforeParry - Settings().ParryStaminaDamage)) && Near(HP(), ParryHP));
				ExpectedStamina = Stamina(); ObserveUntil = Now + 2.0; // QA observation interval; persistent policy also audited.
				Enter(EStage::NoRegen, 10.0);
			}
			else if (Scenario == EScenario::UnpairedDeath)
			{
				if (!Check(TEXT("One GE applies lethal HP and zero stamina together"), Damage(HP(), Stamina()))) return Finish();
				Enter(EStage::Dead, 10.0);
			}
			else BeginExhaustion(false);
			break;
		case EStage::NoRegen:
			bNoPassiveRegen &= Near(Stamina(), ExpectedStamina);
			if (Now < ObserveUntil) return false;
			Check(TEXT("Nonzero damaged stamina does not automatically regenerate"), bNoPassiveRegen);
			if (Monster->GetAttackAbilities().IsEmpty())
			{
				Event(TEXT("No authored attack: runtime attack-cost coverage unavailable; granted CDO audit only"));
				BeginExhaustion(true); break;
			}
			{
				FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(Monster->GetAttackAbilities()[0]);
				if (!Check(TEXT("Authored monster attack has a granted spec"), Spec != nullptr)) return Finish();
				AttackHandle = Spec->Handle; AttackStart = Monster->GetActorLocation(); AttackMontage.Reset(); bAttackAdvanced = false;
				if (!Check(TEXT("Native AI attack activation remains available below maximum stamina"), ASC->TryActivateAbility(AttackHandle))) return Finish();
				ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Begin);
				Check(TEXT("Monster attack activation consumes no stamina"), Near(Stamina(), ExpectedStamina));
				Enter(EStage::Attack, 45.0);
			}
			break;
		case EStage::Attack:
			bNoAttackCost &= Near(Stamina(), ExpectedStamina);
			if (UAnimMontage* Montage = MonsterAnim()->GetCurrentActiveMontage())
			{
				AttackMontage = Montage;
				bAttackAdvanced |= MonsterAnim()->Montage_GetPosition(Montage) > 0.f;
			}
			if (Active(ASC.Get(), AttackHandle)) return false;
			Check(TEXT("Real authored attack advances and ends naturally without stamina cost or end regen"), bAttackAdvanced && bNoAttackCost && Near(Stamina(), ExpectedStamina));
			ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X, EKZComboCommandPhase::Cancel);
			Event(TEXT("Natural attack complete")); BeginExhaustion(true);
			break;
		case EStage::WaitExhaustion:
			if (!Monster->GetActiveExhaustionAbility()) return false;
			Check(TEXT("Zero living stamina activates native exhaustion and movement constraints"), Exhaustion()->IsActive() && Stamina() == 0.f && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) && !Monster->GetLocomotionComponent()->IsMovementInputAllowed() && Monster->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::VelocityDirection);
			Check(TEXT("Unpaired reaction cannot be externally played or completed as a pair"), !Exhaustion()->PlayBrutalReaction(2) && !Exhaustion()->HasBrutalPartner());
			if (bTimeoutCase)
			{
				// Change the live attribute after activation: recovery must read the current maximum.
				ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(), OriginalMaxStamina + Settings().ParryStaminaDamage);
				Enter(EStage::Timeout, Settings().ExhaustionSeconds + Settings().ExhaustionMontage->GetPlayLength() + 15.0);
			}
			else if (Scenario == EScenario::InfiniteCancel && !bInfiniteObserved)
			{
				ObserveUntil = Now + AuthoredExhaustionSeconds + Settings().ExhaustionMontage->GetPlayLength();
				Enter(EStage::Infinite, ObserveUntil - Now + 15.0);
			}
			else if (!StartPair()) return Finish();
			break;
		case EStage::Timeout:
			if (Exhaustion())
			{
				bNoEarlyRecovery &= Stamina() == 0.f;
				if (Now < ExhaustionRequestedAt + Settings().ExhaustionSeconds)
					bNoEarlyRecovery &= MonsterAnim()->Montage_GetCurrentSection(Settings().ExhaustionMontage) != TEXT("End");
				return false;
			}
			Check(TEXT("Finite expiry waits for actual End completion then refills once to the current maximum"), bSawExhaustionEnd && bNoEarlyRecovery && PositiveStaminaChanges == 1 && Near(Stamina(), MaxStamina()));
			CheckMonsterReleased(); Event(TEXT("Finite timeout recovered")); bBack = false; BeginExhaustion(false);
			break;
		case EStage::Infinite:
			bNoEarlyRecovery &= Exhaustion() && Stamina() == 0.f && !bSawExhaustionEnd;
			if (Now < ObserveUntil) return false;
			Check(TEXT("Transient zero timeout remains exhausted beyond the original finite duration and End length"), bNoEarlyRecovery && Exhaustion() && Exhaustion()->IsAvailableForBrutalAttack());
			bInfiniteObserved = true; if (!StartPair()) return Finish(); break;
		case EStage::Pair:
			if (Scenario == EScenario::InfiniteCancel && bSawDamage1 && !bCancelObserved)
			{
				PlayerASC->CancelAbilityHandle(BrutalHandle); bCancelObserved = true;
				Check(TEXT("Attacker cancellation returns a living victim to exhaustion without refill"), Exhaustion() && !Exhaustion()->HasBrutalPartner() && Stamina() == 0.f && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
				CheckPlayerReleased(); ObserveUntil = Now + AuthoredExhaustionSeconds + Settings().ExhaustionMontage->GetPlayLength();
				bSawExhaustionEnd = false; Enter(EStage::CancelledInfinite, ObserveUntil - Now + 15.0); break;
			}
			if (Scenario == EScenario::InfiniteCancel && bReenterObserved && bSawDamage1)
			{
				ReleaseFixtureIntent();
				Controller->UnPossess();
				Check(TEXT("UnPossess cancels both owners without reviving or refilling"), !Exhaustion() && !BrutalActive() && Stamina() == 0.f && !ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
				CheckPlayerReleased(); ObserveUntil = Now + 2.0; Enter(EStage::Unpossessed, 10.0); break;
			}
			if (Scenario == EScenario::EndPlay && bSawDamage1)
			{
				ReleaseFixtureIntent();
				Monster->Destroy(); CheckPlayerReleased(); ObserveUntil = Now + 2.0; Enter(EStage::Destroyed, 10.0); break;
			}
			if (Scenario == EScenario::PairedDeath && bSawDamage2 && !bLethalApplied)
			{
				bLethalApplied = true;
				if (!Check(TEXT("External lethal fixture applies the existing damage GE during actual Damage2"), Damage(HP(), 0.f))) return Finish();
				Event(TEXT("External lethal damage during real paired motion"));
			}
			if (Exhaustion() || BrutalActive()) return false;
			if (Scenario == EScenario::PairedDeath)
			{
				Check(TEXT("Paired death waits for both real completions, freezes the final victim pose and never refills"), bSawDamage1 && bSawDamage2 && bLethalApplied && bObservedDeadDuringPair && bNoEarlyDeathFreeze && HP() == 0.f && Stamina() == 0.f && PositiveStaminaChanges == 0 && Monster->GetMesh()->bPauseAnims && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead));
				CheckPlayerReleased(); NextScenario(EScenario::UnpairedDeath, 0); break;
			}
			Check(TEXT("Native X selects the paired action; both actual hits and End complete before one refill"), bSawDamage1 && bSawDamage2 && bPlayerAdvanced && bSawExhaustionEnd && bNoEarlyRecovery && PositiveStaminaChanges == 1 && Near(Stamina(), MaxStamina()));
			Check(TEXT("Paired HP damage is the configured total applied once"), Near(HP(), PairHPBefore - Settings().BrutalHPDamage));
			if (Settings().BrutalHPDamage > 0.f) Check(TEXT("Positive configured paired damage produces an actual HP loss"), HP() < PairHPBefore);
			{ FObject Row = Object(); Stamp(Row); Row->SetStringField(TEXT("event"), TEXT("paired_hp_damage_result")); Row->SetNumberField(TEXT("hp_before"), PairHPBefore); Row->SetNumberField(TEXT("hp_after"), HP()); Row->SetNumberField(TEXT("actual_hp_loss"), PairHPBefore - HP()); Row->SetNumberField(TEXT("configured_total_hp_damage"), Settings().BrutalHPDamage); Events.Add(Json(Row)); }
			CheckMonsterReleased(); CheckPlayerReleased(); Event(TEXT("Natural pair complete"));
			if (!bBack) { bBack = true; BeginExhaustion(false); }
			else if (++Family < int32(UE_ARRAY_COUNT(Families))) { ResetActor(); Enter(EStage::Spawn, 15.0); }
			else NextScenario(EScenario::InfiniteCancel, 0);
			break;
		case EStage::CancelledInfinite:
			bNoEarlyRecovery &= Exhaustion() && Stamina() == 0.f && !bSawExhaustionEnd && !Exhaustion()->HasBrutalPartner();
			if (Now < ObserveUntil) return false;
			Check(TEXT("Cancelled infinite pair does not schedule a finite recovery"), bNoEarlyRecovery);
			if (FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(UKZExhaustionAbility::StaticClass()))
				ASC->CancelAbilityHandle(Spec->Handle);
			Check(TEXT("External exhaustion cancellation itself never refills"), !Exhaustion() && Stamina() == 0.f);
			Enter(EStage::Reenter, 10.0); break;
		case EStage::Reenter:
			if (!Exhaustion()) return false;
			Check(TEXT("Living possessed zero stamina re-enters exhaustion after cancellation"), Stamina() == 0.f && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted));
			bReenterObserved = true; if (!StartPair()) return Finish(); break;
		case EStage::Unpossessed:
			if (Now < ObserveUntil) return false;
			Check(TEXT("Unbound victim cannot reactivate exhaustion on later frames"), !Exhaustion() && Stamina() == 0.f && !Monster->GetController());
			NextScenario(EScenario::EndPlay, 0); break;
		case EStage::Destroyed:
			if (Now < ObserveUntil) return false;
			Check(TEXT("Victim EndPlay aborts player and leaves no later action or input block"), !BrutalActive() && PlayerASC->GetTagCount(KZGameplayTags::Block_Movement_Input) == PlayerMovementTagBaseline);
			NextScenario(EScenario::PairedDeath, 5); break;
		case EStage::Dead:
			if (!ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead)) return false;
			Check(TEXT("Simultaneous HP zero and stamina zero prioritizes death, never starts exhaustion or refills"), HP() == 0.f && Stamina() == 0.f && !Exhaustion() && !ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) && Monster->GetMesh()->bPauseAnims && !Monster->GetLocomotionComponent()->IsMovementInputAllowed());
			Check(TEXT("Earlier victim's late abort was ignored by a later real paired execution"), bPriorVictimAbortAttempted && bPriorVictimAbortIgnored);
			return Finish();
		}
		return false;
	}
private:
	bool Check(const TCHAR* Label, bool bValue)
	{
		const FString Qualified = FString::Printf(TEXT("%s scenario=%d back=%d: %s"), Families[FMath::Clamp(Family, 0, int32(UE_ARRAY_COUNT(Families)) - 1)], int32(Scenario), bBack, Label);
		FObject Row = Object(); Row->SetStringField(TEXT("claim"), Qualified); Row->SetBoolField(TEXT("pass"), bValue); Checks.Add(Json(Row));
		Test->TestTrue(Qualified, bValue); return bValue;
	}
	void Enter(EStage Next, double Seconds) { Stage = Next; StageDeadline = FPlatformTime::Seconds() + Seconds; Event(TEXT("Stage changed")); }
	static bool Near(float A, float B) { return FMath::IsNearlyEqual(A, B); }
	static bool Active(UKZAbilitySystemComponent* Component, FGameplayAbilitySpecHandle Handle)
	{ const FGameplayAbilitySpec* Spec = Component ? Component->FindAbilitySpecFromHandle(Handle) : nullptr; return Spec && Spec->IsActive(); }
	bool BrutalActive() const { return Active(PlayerASC.Get(), BrutalHandle); }
	UKZExhaustionAbility* Exhaustion() const { return Monster.IsValid() ? Monster->GetActiveExhaustionAbility() : nullptr; }
	UAnimInstance* MonsterAnim() const { return Monster.IsValid() ? Monster->GetMesh()->GetAnimInstance() : nullptr; }
	const FKZMonsterStaminaSettings& Settings() const { return Monster->GetCharacterDefinition()->GetMonsterStaminaSettings(); }
	float HP() const { return ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()); }
	float Stamina() const { return ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()); }
	float MaxStamina() const { return ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()); }
	bool Damage(float HPSpend, float StaminaSpend)
	{
		FGameplayEffectContextHandle Context = ASC->MakeEffectContext(); Context.AddInstigator(Player.Get(), Player.Get());
		FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Settings().DamageEffect, 1.f, Context);
		if (!Spec.IsValid()) return false;
		Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), -HPSpend);
		Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")), -StaminaSpend);
		return ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()).WasSuccessfullyApplied();
	}
	bool Spawn()
	{
		const FString BP = FString(TEXT("/Game/Bluprints/Monsters/BP_Monster_")) + Families[Family];
		const FString DefinitionPath = FString(TEXT("/Game/Monsters/")) + Families[Family] + TEXT("/Data/DA_Character_") + Families[Family];
		UClass* Class = LoadClass<AKZMonster>(nullptr, *(BP + TEXT(".BP_Monster_") + Families[Family] + TEXT("_C")));
		const UKZCharacterDefinitionData* Definition = LoadObject<UKZCharacterDefinitionData>(nullptr, *DefinitionPath);
		if (!Check(TEXT("Actual authored BP and Definition load"), Class && Definition)) return false;
		const AKZMonster* CDO = Class->GetDefaultObject<AKZMonster>();
		const float Range = Definition->GetMonsterStaminaSettings().BrutalAttackRange;
		Anchor = SavedPlayerLocation + SavedPlayerRotation.Vector().GetSafeNormal2D() * Range;
		Anchor.Z += CDO->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		AnchorRotation = FRotator(0.f, SavedPlayerRotation.Yaw + 180.f, 0.f); // Fixture geometry: face the original player position.
		FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Monster = Player->GetWorld()->SpawnActor<AKZMonster>(Class, Anchor, AnchorRotation, Params);
		if (Monster.IsValid()) { ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent()); Controller = Cast<AKZMonsterAIController>(Monster->GetController()); }
		if (!Check(TEXT("Spawned authored monster initializes its exact Definition, ASC and AnimInstance"), Monster.IsValid() && Monster->GetCharacterDefinition() == Definition && Monster->GetAbilitySystemComponent() && MonsterAnim())) return false;
		ASC = Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
		if (!Monster->GetController()) Monster->SpawnDefaultController();
		Controller = Cast<AKZMonsterAIController>(Monster->GetController());
		if (!Check(TEXT("Monster has the native controller needed for resource observation"), ASC.IsValid() && Controller.IsValid())) return false;
		const bool bHasStateTree = Monster->GetAIStateTree() != nullptr;
		if (bHasStateTree)
			Controller->Tick(0.f); // Run the existing deferred native binding after Definition initialization.
		else
		{
			// These authored actors have no autonomous AI tree. The probe owns only their actual intent-source lifetime.
			FixtureIntent = Monster->GetLocomotionComponent()->BeginLocomotionIntentSource(Controller.Get(), EKZLocomotionIntentSource::AIController);
			if (!Check(TEXT("No-StateTree fixture acquires a real controller locomotion intent handle"), FixtureIntent.IsValid())) return false;
		}
		// Stop only this temporary actor's autonomous decisions; keep possession, delegates and navigation permission callbacks.
		Controller->GetStateTreeComponent()->StopLogic(TEXT("Isolated native stamina fixture")); Controller->StopMovement(); Controller->ClearFocus(EAIFocusPriority::Gameplay); Controller->SetActorTickEnabled(false);
		ASC->CancelAllAbilities(); ASC->ClearComboCommands();
		if (!Check(TEXT("Initialized living fixture allows movement before exhaustion"), Monster->GetLocomotionComponent()->IsMovementInputAllowed())) return false;
		{ FObject Row = Object(); Stamp(Row); Row->SetStringField(TEXT("event"), TEXT("locomotion_intent_initialized")); Row->SetStringField(TEXT("ai_state_tree"), Path(Monster->GetAIStateTree())); Row->SetBoolField(TEXT("native_controller_initialization_tick"), bHasStateTree); Row->SetNumberField(TEXT("initialization_tick_seconds"), 0.f); Row->SetBoolField(TEXT("fixture_owned_intent_source_without_state_tree"), !bHasStateTree); Row->SetBoolField(TEXT("movement_allowed"), Monster->GetLocomotionComponent()->IsMovementInputAllowed()); Events.Add(Json(Row)); }
		AuthoredExhaustionSeconds = Settings().ExhaustionSeconds; OriginalMaxStamina = MaxStamina();
		if (!Check(TEXT("Authored initialization supplies positive full HP and stamina maxima"), OriginalMaxStamina > 0.f && ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()) > 0.f && Near(HP(), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute())) && Near(Stamina(), OriginalMaxStamina))) return false;
		FObject Audit = Object(); Audit->SetStringField(TEXT("family"), Families[Family]); Audit->SetStringField(TEXT("bp"), Class->GetPathName()); Audit->SetStringField(TEXT("definition"), Definition->GetPathName());
		Audit->SetNumberField(TEXT("scenario"), int32(Scenario)); Audit->SetNumberField(TEXT("authored_exhaustion_seconds"), AuthoredExhaustionSeconds); Audit->SetNumberField(TEXT("max_hp"), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute())); Audit->SetNumberField(TEXT("max_stamina"), OriginalMaxStamina);
		Audit->SetNumberField(TEXT("parry_stamina_damage"), Settings().ParryStaminaDamage); Audit->SetNumberField(TEXT("brutal_hp_damage"), Settings().BrutalHPDamage); Audit->SetNumberField(TEXT("brutal_range_cm"), Settings().BrutalAttackRange);
		Audit->SetStringField(TEXT("exhaustion_montage"), Path(Settings().ExhaustionMontage)); Audit->SetNumberField(TEXT("authored_attack_count"), Monster->GetAttackAbilities().Num()); Audit->SetBoolField(TEXT("autonomous_ai_stopped_for_spawned_fixture"), true); Audits.Add(Json(Audit));
		Audit->SetBoolField(TEXT("native_controller_initialization_tick"), bHasStateTree); Audit->SetBoolField(TEXT("fixture_owned_intent_source_without_state_tree"), !bHasStateTree); Audit->SetBoolField(TEXT("initial_movement_allowed"), Monster->GetLocomotionComponent()->IsMovementInputAllowed());
		const auto& S = Settings();
		if (!Check(TEXT("Enabled finite authored policy has all effect/montage dependencies and native exhaustion grant"), S.bEnabled && S.ExhaustionSeconds > 0.f && S.ParryStaminaDamage > 0.f && S.BrutalAttackRange > 0.f && S.BrutalHPDamage >= 0.f && S.ExhaustionMontage && S.BrutalFrontPlayerMontage && S.BrutalBackPlayerMontage && S.BrutalFrontVictimMontage && S.BrutalBackVictimMontage && S.DamageEffect && S.DeadStateEffect && ASC->FindAbilitySpecFromClass(UKZExhaustionAbility::StaticClass()))) return false;
		Check(TEXT("Persistent monster-only no-regeneration policy is present"), ASC->HasMatchingGameplayTag(KZGameplayTags::Block_StaminaRegen) && !Player->GetCharacterDefinition()->GetMonsterStaminaSettings().bEnabled);
		TArray<TSharedPtr<FJsonValue>> Actions;
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		{
			if (!Cast<UKZActionAbility>(Spec.Ability)) continue;
			const FObjectPropertyBase* OnEnd = FindFProperty<FObjectPropertyBase>(Spec.Ability->GetClass(), TEXT("OnEndAbilityGameplayEffect"));
			FObject Action = Object(); Action->SetStringField(TEXT("ability_class"), Spec.Ability->GetClass()->GetPathName()); Action->SetStringField(TEXT("cost_effect"), Path(Spec.Ability->GetCostGameplayEffect())); Action->SetBoolField(TEXT("on_end_property_present"), OnEnd != nullptr); Action->SetStringField(TEXT("on_end_effect"), OnEnd ? Path(OnEnd->GetObjectPropertyValue_InContainer(Spec.Ability)) : TEXT("")); Actions.Add(Json(Action));
			Check(*FString::Printf(TEXT("Authored Action has no attack cost or post-action regen effect: %s"), *Spec.Ability->GetClass()->GetPathName()), !Spec.Ability->GetCostGameplayEffect() && OnEnd && !OnEnd->GetObjectPropertyValue_InContainer(Spec.Ability));
		}
		Audit->SetArrayField(TEXT("granted_action_audits"), Actions);
		if (Scenario == EScenario::InfiniteCancel)
		{
			UKZCharacterDefinitionData* Copy = DuplicateObject<UKZCharacterDefinitionData>(Definition, GetTransientPackage()); Copy->SetFlags(RF_Transient);
			FKZMonsterStaminaSettings* Fixture = Field<FKZMonsterStaminaSettings>(Copy, TEXT("MonsterStamina"));
			FObjectPropertyBase* Pointer = FindFProperty<FObjectPropertyBase>(Monster->GetClass(), TEXT("CharacterDefinition"));
			if (!Check(TEXT("Transient-only zero-timeout fixture is available"), Fixture && Pointer)) return false;
			Fixture->ExhaustionSeconds = 0.f; Fixture->ParryStaminaDamage = S.ParryStaminaDamage * 2.f;
			Pointer->SetObjectPropertyValue_InContainer(Monster.Get(), Copy);
			const float Before = Stamina();
			Check(TEXT("Parry consequence reads the adjusted transient Definition, without changing authored data"), Monster->ReportAttackParried(Player.Get()) && Near(Stamina(), FMath::Max(0.f, Before - Fixture->ParryStaminaDamage)) && Definition->GetMonsterStaminaSettings().ExhaustionSeconds == AuthoredExhaustionSeconds);
			Audit->SetStringField(TEXT("fixture_definition"), Copy->GetPathName()); Audit->SetNumberField(TEXT("fixture_exhaustion_seconds"), 0.f); Audit->SetNumberField(TEXT("fixture_parry_damage"), Fixture->ParryStaminaDamage);
		}
		// Ensure the alive-pair scenario survives any currently authored total damage. This is a spawn-only attribute fixture.
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()) + Settings().BrutalHPDamage * 2.f);
		ASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()));
		FKZMovementConstraint Foreign; Foreign.MaxAllowedGait = EKZGait::Walk; Foreign.bOverrideRotationMode = true; Foreign.RotationModeOverride = EKZRotationMode::LockOn; Foreign.DebugName = TEXT("StaminaPIE foreign monster constraint");
		MonsterConstraint = Monster->GetLocomotionComponent()->AcquireMovementConstraint(Monster.Get(), Foreign);
		StaminaChangedHandle = ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).AddLambda([this](const FOnAttributeChangeData& Change)
		{
			if (bTrackRefill && Change.NewValue > Change.OldValue) ++PositiveStaminaChanges;
			FObject Row = Object(); Row->SetStringField(TEXT("event"), TEXT("stamina_attribute_change")); Row->SetNumberField(TEXT("old"), Change.OldValue); Row->SetNumberField(TEXT("new"), Change.NewValue); Stamp(Row); Events.Add(Json(Row));
		});
		bNoPassiveRegen = bNoAttackCost = true; Event(TEXT("Actual authored actor ready")); return true;
	}
	void BeginExhaustion(bool bByTimeout)
	{
		bTimeoutCase = bByTimeout; bSawExhaustionEnd = false; bNoEarlyRecovery = true; PositiveStaminaChanges = 0; bTrackRefill = true;
		ExhaustionRequestedAt = Player->GetWorld()->GetTimeSeconds();
		Check(TEXT("Damage GE depletes the current stamina without changing living HP"), Damage(0.f, Stamina()) && Stamina() == 0.f && HP() > 0.f);
		Enter(EStage::WaitExhaustion, 10.0);
	}
	bool StartPair()
	{
		const FGameplayAbilitySpec* InputSpec = PlayerASC->FindAbilitySpecFromHandle(BrutalHandle);
		if (!Check(TEXT("Player has an actual X-bound Brutal grant"), InputSpec && InputSpec->GetDynamicSpecSourceTags().HasTagExact(KZGameplayTags::Input_Action_X))) return false;
		if (Scenario == EScenario::Authored && bBack && Settings().BrutalHPDamage == 0.f)
		{
			const UKZCharacterDefinitionData* Definition = Monster->GetCharacterDefinition();
			UKZCharacterDefinitionData* Copy = DuplicateObject<UKZCharacterDefinitionData>(Definition, GetTransientPackage());
			FKZMonsterStaminaSettings* Fixture = Field<FKZMonsterStaminaSettings>(Copy, TEXT("MonsterStamina"));
			FObjectPropertyBase* Pointer = FindFProperty<FObjectPropertyBase>(Monster->GetClass(), TEXT("CharacterDefinition"));
			if (!Check(TEXT("Transient back-pair positive damage fixture is available"), Copy && Fixture && Pointer && HP() > 0.f)) return false;
			Copy->SetFlags(RF_Transient); Fixture->BrutalHPDamage = HP() / 16.f; // QA-derived HP units, not product tuning or an authored value.
			Pointer->SetObjectPropertyValue_InContainer(Monster.Get(), Copy);
			Check(TEXT("Transient back-pair damage preserves the authored zero setting"), Settings().BrutalHPDamage > 0.f && Definition->GetMonsterStaminaSettings().BrutalHPDamage == 0.f);
			FObject Row = Object(); Stamp(Row); Row->SetStringField(TEXT("event"), TEXT("transient_back_pair_positive_damage")); Row->SetStringField(TEXT("authored_definition"), Path(Definition)); Row->SetNumberField(TEXT("authored_brutal_hp_damage"), Definition->GetMonsterStaminaSettings().BrutalHPDamage); Row->SetStringField(TEXT("fixture_definition"), Path(Copy)); Row->SetNumberField(TEXT("fixture_brutal_hp_damage"), Fixture->BrutalHPDamage); Row->SetStringField(TEXT("derivation"), TEXT("current_victim_hp / 16; QA-derived HP units; transient fixture only")); Events.Add(Json(Row));
		}
		Monster->GetCharacterMovement()->StopMovementImmediately(); Monster->SetActorLocation(Anchor, false, nullptr, ETeleportType::TeleportPhysics); Monster->SetActorRotation(AnchorRotation);
		const float HeightDifference = Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const float Minimum = FMath::Max(Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + Monster->GetCapsuleComponent()->GetScaledCapsuleRadius(), Settings().BrutalAlignmentDistance);
		const float HorizontalLimitSquared = FMath::Square(Settings().BrutalAttackRange) - FMath::Square(HeightDifference);
		if (!Check(TEXT("Live capsules fit inside the authored 3D interaction range"), HorizontalLimitSquared > FMath::Square(Minimum))) return false;
		const float Distance = (Minimum + FMath::Sqrt(HorizontalLimitSquared)) / 2.f; // Midpoint for QA placement, not a new interaction threshold.
		FVector Position = Anchor + Monster->GetActorForwardVector() * (bBack ? -Distance : Distance); Position.Z += HeightDifference;
		Player->GetCharacterMovement()->StopMovementImmediately(); Player->SetActorLocation(Position, false, nullptr, ETeleportType::TeleportPhysics);
		Player->SetActorRotation((Anchor - Position).GetSafeNormal2D().Rotation());
		PairHPBefore = HP(); bSawDamage1 = bSawDamage2 = bPlayerAdvanced = false; bSawExhaustionEnd = false; bNoEarlyRecovery = bNoEarlyDeathFreeze = true; bLethalApplied = bObservedDeadDuringPair = false; CompletionOrder.Reset(); VictimDamage2InstanceId = INDEX_NONE; PositiveStaminaChanges = 0;
		ExpectedPlayerMontage = bBack ? Settings().BrutalBackPlayerMontage.Get() : Settings().BrutalFrontPlayerMontage.Get();
		ExpectedVictimMontage = bBack ? Settings().BrutalBackVictimMontage.Get() : Settings().BrutalFrontVictimMontage.Get();
		PlayerASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_X); PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_X);
		FGameplayAbilitySpec* Spec = PlayerASC->FindAbilitySpecFromHandle(BrutalHandle);
		UGameplayAbility* Instance = Spec ? Spec->GetPrimaryInstance() : nullptr;
		if (!Check(TEXT("Real ASC X dispatch activates the selected front/back paired montage and claims the exact victim"), Spec && Spec->IsActive() && Instance && Instance->GetCurrentMontage() == ExpectedPlayerMontage && Exhaustion() && Exhaustion()->HasBrutalPartner())) return false;
		if (PriorVictim.IsValid() && !bPriorVictimAbortAttempted && PriorVictim.Get() != Exhaustion())
		{
			// This is the actual previous actor's completed execution, pinned only for this regression.
			// No fabricated completion: its late public cleanup must not cancel a different victim's live pair.
			bPriorVictimAbortAttempted = true;
			UKZBrutalAttackAbility* Current = Cast<UKZBrutalAttackAbility>(Instance);
			if (Current) Current->AbortFromVictim(PriorVictim.Get());
			bPriorVictimAbortIgnored = Current && Current->IsActive() && Current->GetCurrentMontage() == ExpectedPlayerMontage && Exhaustion() && Exhaustion()->HasBrutalPartner();
			Check(TEXT("Previous actual victim cannot abort the new paired execution or change its montage"), bPriorVictimAbortIgnored);
			FObject Row = Object(); Stamp(Row); Row->SetStringField(TEXT("event"), TEXT("prior_actual_victim_late_abort")); Row->SetStringField(TEXT("prior_victim_execution"), Path(PriorVictim.Get())); Row->SetStringField(TEXT("current_victim_execution"), Path(Exhaustion())); Row->SetBoolField(TEXT("ignored"), bPriorVictimAbortIgnored); Events.Add(Json(Row));
			if (!bPriorVictimAbortIgnored) return false;
		}
		Check(TEXT("Player paired action blocks movement and forces velocity rotation"), !Player->GetLocomotionComponent()->IsMovementInputAllowed() && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::VelocityDirection);
		Enter(EStage::Pair, ExpectedPlayerMontage->GetPlayLength() + ExpectedVictimMontage->GetPlayLength() + Settings().ExhaustionMontage->GetPlayLength() + 15.0); Event(TEXT("Native X paired execution started")); return true;
	}
	void CheckMonsterReleased()
	{
		Check(TEXT("Recovery removes exhaustion/input block and restores the independently owned rotation constraint"), !Exhaustion() && !ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) && !ASC->HasMatchingGameplayTag(KZGameplayTags::Block_Movement_Input) && Monster->GetLocomotionComponent()->IsMovementInputAllowed() && Monster->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::LockOn && Monster->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == EKZGait::Walk);
		Check(TEXT("Recovery preserves the persistent monster no-regeneration policy"), ASC->HasMatchingGameplayTag(KZGameplayTags::Block_StaminaRegen));
	}
	void CheckPlayerReleased()
	{
		Check(TEXT("Player cleanup removes only its paired tags/constraint and preserves the foreign owner"), !BrutalActive() && PlayerASC->GetTagCount(KZGameplayTags::Block_Movement_Input) == PlayerMovementTagBaseline && PlayerASC->GetTagCount(KZGameplayTags::Block_StaminaRegen) == PlayerRegenTagBaseline && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode == EKZRotationMode::LockOn && Player->GetLocomotionComponent()->GetResolvedMovementPolicy().MaxAllowedGait == EKZGait::Walk);
	}
	void NextScenario(EScenario Next, int32 Index)
	{
		ResetActor(); Scenario = Next; Family = Index; bBack = false; bInfiniteObserved = bCancelObserved = bReenterObserved = false; Enter(EStage::Spawn, 15.0);
	}
	void Stamp(const FObject& Row) const
	{
		Row->SetNumberField(TEXT("world_seconds"), Player.IsValid() ? Player->GetWorld()->GetTimeSeconds() : -1.0);
		Row->SetStringField(TEXT("family"), Families[FMath::Clamp(Family, 0, int32(UE_ARRAY_COUNT(Families)) - 1)]); Row->SetNumberField(TEXT("scenario"), int32(Scenario)); Row->SetNumberField(TEXT("stage"), int32(Stage)); Row->SetBoolField(TEXT("from_back"), bBack);
	}
	void Event(const TCHAR* Name) { FObject Row = Object(); Row->SetStringField(TEXT("event"), Name); Stamp(Row); Events.Add(Json(Row)); }
	void OnPostTick(UWorld* World, ELevelTick, float) { if (Player.IsValid() && Player->GetWorld() == World) Sample(); }
	void Sample()
	{
		if (!Monster.IsValid() || !ASC.IsValid() || !MonsterAnim()) return;
		UAnimInstance* VictimAnim = MonsterAnim(); UAnimInstance* PlayerAnim = Player->GetMesh()->GetAnimInstance();
		UAnimMontage* VictimMontage = VictimAnim->GetCurrentActiveMontage(); UAnimMontage* PlayerMontage = PlayerAnim ? PlayerAnim->GetCurrentActiveMontage() : nullptr;
		const FName Section = VictimMontage ? VictimAnim->Montage_GetCurrentSection(VictimMontage) : NAME_None;
		if (VictimMontage == Settings().ExhaustionMontage && Section == TEXT("End")) bSawExhaustionEnd = true;
		if (Stage == EStage::Pair)
		{
			bSawDamage1 |= VictimMontage == ExpectedVictimMontage && Section == TEXT("Damage1");
			bSawDamage2 |= VictimMontage == ExpectedVictimMontage && Section == TEXT("Damage2");
			if (VictimMontage == ExpectedVictimMontage && Section == TEXT("Damage2"))
				if (const FAnimMontageInstance* Instance = VictimAnim->GetActiveInstanceForMontage(ExpectedVictimMontage)) VictimDamage2InstanceId = Instance->GetInstanceID();
			bPlayerAdvanced |= PlayerAnim && PlayerMontage == ExpectedPlayerMontage && PlayerAnim->Montage_GetPosition(PlayerMontage) > 0.f;
			// ActiveMontagesMap loses an entry at blend-out start. Keep the actual instance ID
			// to observe its remaining lifetime through blend-out, without replacing engine delegates.
			const bool bAttackerActive = BrutalActive();
			const bool bVictimInstanceRemaining = VictimDamage2InstanceId != INDEX_NONE && VictimAnim->GetMontageInstanceForID(VictimDamage2InstanceId) != nullptr;
			if (bSawDamage2 && VictimDamage2InstanceId != INDEX_NONE && CompletionOrder.IsEmpty())
			{
				if (!bAttackerActive && bVictimInstanceRemaining) CompletionOrder = TEXT("attacker_ability_ended_before_victim_instance_removed");
				else if (bAttackerActive && !bVictimInstanceRemaining) CompletionOrder = TEXT("victim_instance_removed_before_attacker_ability_ended");
				else if (!bAttackerActive && !bVictimInstanceRemaining) CompletionOrder = TEXT("both_endpoints_observed_in_same_sample");
				if (!CompletionOrder.IsEmpty()) { FObject Row = Object(); Row->SetStringField(TEXT("event"), TEXT("observed_public_completion_lifetimes")); Row->SetStringField(TEXT("order"), CompletionOrder); Row->SetNumberField(TEXT("victim_damage2_instance_id"), VictimDamage2InstanceId); Stamp(Row); Events.Add(Json(Row)); }
			}
			if (bAttackerActive || bVictimInstanceRemaining)
			{
				bNoEarlyRecovery &= Stamina() == 0.f && !(VictimMontage == Settings().ExhaustionMontage && Section == TEXT("End"));
				if (bLethalApplied)
				{
					bObservedDeadDuringPair |= HP() == 0.f && ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead);
					bNoEarlyDeathFreeze &= !Monster->GetMesh()->bPauseAnims && Exhaustion() && Exhaustion()->HasBrutalPartner();
				}
			}
		}
		const double Now = Player->GetWorld()->GetTimeSeconds();
		const FString Key = FString::Printf(TEXT("%d|%d|%d|%s|%s|%s|%d|%d|%d|%.6f|%.6f"), Family, int32(Scenario), int32(Stage), *Path(VictimMontage), *Section.ToString(), *Path(PlayerMontage), BrutalActive(), Exhaustion() && Exhaustion()->HasBrutalPartner(), Monster->GetMesh()->bPauseAnims, HP(), Stamina());
		if (Key == LastSampleKey && Now - LastSampleAt < 0.25) return; // Evidence sampling cadence only; gates above inspect every world tick.
		LastSampleKey = Key; LastSampleAt = Now;
		FObject Row = Object(); Stamp(Row); Row->SetStringField(TEXT("event"), TEXT("public_runtime_sample"));
		Row->SetNumberField(TEXT("hp"), HP()); Row->SetNumberField(TEXT("stamina"), Stamina()); Row->SetNumberField(TEXT("max_stamina"), MaxStamina()); Row->SetBoolField(TEXT("exhaustion_active"), Exhaustion() != nullptr); Row->SetBoolField(TEXT("paired"), Exhaustion() && Exhaustion()->HasBrutalPartner()); Row->SetBoolField(TEXT("attacker_active"), BrutalActive()); Row->SetBoolField(TEXT("victim_frozen"), Monster->GetMesh()->bPauseAnims);
		Row->SetNumberField(TEXT("victim_damage2_instance_id"), VictimDamage2InstanceId); Row->SetBoolField(TEXT("victim_damage2_instance_remaining"), VictimDamage2InstanceId != INDEX_NONE && VictimAnim->GetMontageInstanceForID(VictimDamage2InstanceId) != nullptr);
		Row->SetBoolField(TEXT("state_exhausted"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted)); Row->SetBoolField(TEXT("state_dead"), ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead)); Row->SetBoolField(TEXT("monster_movement_allowed"), Monster->GetLocomotionComponent()->IsMovementInputAllowed()); Row->SetNumberField(TEXT("monster_rotation_policy"), int32(Monster->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode)); Row->SetNumberField(TEXT("player_rotation_policy"), int32(Player->GetLocomotionComponent()->GetResolvedMovementPolicy().ResolvedRotationMode));
		Row->SetStringField(TEXT("victim_montage"), Path(VictimMontage)); Row->SetStringField(TEXT("victim_section"), Section.ToString()); Row->SetNumberField(TEXT("victim_position_seconds"), VictimMontage ? VictimAnim->Montage_GetPosition(VictimMontage) : -1.f); Row->SetStringField(TEXT("player_montage"), Path(PlayerMontage)); Row->SetNumberField(TEXT("player_position_seconds"), PlayerMontage ? PlayerAnim->Montage_GetPosition(PlayerMontage) : -1.f); Row->SetStringField(TEXT("victim_location_cm"), Monster->GetActorLocation().ToString()); Row->SetStringField(TEXT("player_location_cm"), Player->GetActorLocation().ToString()); Events.Add(Json(Row));
	}
	void ReleaseFixtureIntent()
	{
		if (FixtureIntent.IsValid() && Monster.IsValid()) Monster->GetLocomotionComponent()->EndLocomotionIntentSource(FixtureIntent);
		FixtureIntent.Reset();
	}
	void ResetActor()
	{
		if (!PriorVictim.IsValid() && ASC.IsValid())
			if (const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(UKZExhaustionAbility::StaticClass()))
				if (UKZExhaustionAbility* Actual = Cast<UKZExhaustionAbility>(Spec->GetPrimaryInstance())) PriorVictim.Reset(Actual);
		if (ASC.IsValid()) ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).Remove(StaminaChangedHandle);
		StaminaChangedHandle.Reset(); bTrackRefill = false;
		ReleaseFixtureIntent();
		if (Monster.IsValid()) { Monster->GetLocomotionComponent()->ReleaseMovementConstraint(MonsterConstraint); Monster->Destroy(); }
		MonsterConstraint.Reset(); if (Controller.IsValid()) Controller->Destroy(); Controller.Reset(); Monster.Reset(); ASC.Reset();
	}
	void Cleanup()
	{
		if (bCleaned) return; bCleaned = true; FWorldDelegates::OnWorldPostActorTick.Remove(PostTickHandle); PostTickHandle.Reset(); ResetActor();
		if (PlayerASC.IsValid())
		{
			FGameplayTagContainer Actions; Actions.AddTag(KZGameplayTags::Ability_Action); PlayerASC->CancelAbilities(&Actions);
			PlayerASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_X); PlayerASC->ClearComboCommands();
		}
		if (!Player.IsValid()) return;
		Player->GetLocomotionComponent()->ReleaseMovementConstraint(PlayerConstraint);
		Player->HandleInputMoveReleased(); Player->GetCharacterMovement()->StopMovementImmediately();
		Player->SetActorLocation(SavedPlayerLocation, false, nullptr, ETeleportType::TeleportPhysics); Player->SetActorRotation(SavedPlayerRotation);
		if (Player->GetController()) Player->GetController()->SetControlRotation(SavedControlRotation);
		if (PlayerASC.IsValid()) { PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxHPAttribute(), SavedMaxHP); PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetMaxStaminaAttribute(), SavedMaxStamina); PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetHPAttribute(), SavedHP); PlayerASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(), SavedStamina); }
		PriorVictim.Reset();
	}
	bool Finish()
	{
		Cleanup(); FObject Report = Object(); Report->SetBoolField(TEXT("success"), !Test->HasAnyErrors()); Report->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601()); Report->SetStringField(TEXT("project"), FPaths::ConvertRelativePathToFull(FPaths::ProjectDir())); Report->SetNumberField(TEXT("process_id"), FPlatformProcess::GetCurrentProcessId()); Report->SetStringField(TEXT("test"), TEXT("Khazan.Monster.StaminaPIE")); Report->SetBoolField(TEXT("completion_flags_mutated"), false); Report->SetBoolField(TEXT("authored_assets_modified"), false); Report->SetArrayField(TEXT("authored_actor_audits"), Audits); Report->SetArrayField(TEXT("checks"), Checks); Report->SetArrayField(TEXT("runtime_evidence"), Events);
		Report->SetStringField(TEXT("scope"), TEXT("Six authored BP/Definitions; real GE/parry, persistent no-regen policy, granted Action cost/end-effect audit, first real human attack per family, finite timeout, front/back X pairs. Existing StateTree controllers receive one native initialization Tick(0); no-StateTree actors use a probe-owned real locomotion intent handle, not complete autonomous AI coverage. Authored zero Brutal HP damage is replaced only in a transient back-pair Definition by current HP/16 QA damage to exercise positive native damage and duplicate detection. Actual prior-victim late-abort identity regression; transient zero-timeout/editable parry, cancel/reentry/unpossess/endplay, real-motion external lethal and simultaneous death. Completion evidence compares observed attacker Ability inactivity with captured Damage2 montage instance removal through blend-out; same-sample endpoints do not establish callback order. No engine delegates, montage timing or completion flags changed."));
		FString Text; FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
		const FString Filename = FPaths::ProjectDir() / TEXT("Metadata/MonsterStamina_20261008/NativePIE.json"); IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true);
		if (!FFileHelper::SaveStringToFile(Text, *Filename, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)) Test->AddError(TEXT("Could not preserve native stamina PIE evidence."));
		Test->AddInfo(FString(TEXT("MonsterStamina native evidence: ")) + FPaths::ConvertRelativePathToFull(Filename)); return true;
	}
	FAutomationTestBase* Test;
	TWeakObjectPtr<AKZPlayer> Player; TWeakObjectPtr<UKZAbilitySystemComponent> PlayerASC, ASC; TWeakObjectPtr<AKZMonster> Monster; TWeakObjectPtr<AKZMonsterAIController> Controller;
	TStrongObjectPtr<UKZExhaustionAbility> PriorVictim;
	FGameplayAbilitySpecHandle BrutalHandle, AttackHandle; FKZMovementConstraintHandle PlayerConstraint, MonsterConstraint; FDelegateHandle PostTickHandle, StaminaChangedHandle;
	FKZLocomotionIntentHandle FixtureIntent;
	TWeakObjectPtr<UAnimMontage> AttackMontage; UAnimMontage* ExpectedPlayerMontage = nullptr; UAnimMontage* ExpectedVictimMontage = nullptr;
	FVector SavedPlayerLocation, Anchor, AttackStart; FRotator SavedPlayerRotation, SavedControlRotation, AnchorRotation;
	float SavedHP = 0.f, SavedStamina = 0.f, SavedMaxHP = 0.f, SavedMaxStamina = 0.f, OriginalMaxStamina = 0.f, AuthoredExhaustionSeconds = 0.f, ExpectedStamina = 0.f, PairHPBefore = 0.f;
	double Deadline = 0.0, StageDeadline = 0.0, ObserveUntil = 0.0, ExhaustionRequestedAt = 0.0, LastSampleAt = -1.0;
	int32 Family = 0, PlayerMovementTagBaseline = 0, PlayerRegenTagBaseline = 0, PositiveStaminaChanges = 0, VictimDamage2InstanceId = INDEX_NONE;
	EScenario Scenario = EScenario::Authored; EStage Stage = EStage::Spawn;
	bool bBack = false, bTimeoutCase = false, bTrackRefill = false, bNoPassiveRegen = true, bNoAttackCost = true, bAttackAdvanced = false;
	bool bSawDamage1 = false, bSawDamage2 = false, bPlayerAdvanced = false, bSawExhaustionEnd = false, bNoEarlyRecovery = true, bNoEarlyDeathFreeze = true, bLethalApplied = false, bObservedDeadDuringPair = false;
	bool bInfiniteObserved = false, bCancelObserved = false, bReenterObserved = false, bCleaned = false;
	bool bPriorVictimAbortAttempted = false, bPriorVictimAbortIgnored = false;
	FString CompletionOrder, LastSampleKey; TArray<TSharedPtr<FJsonValue>> Checks, Audits, Events;
};

class FWait : public IAutomationLatentCommand
{
public:
	explicit FWait(FAutomationTestBase* InTest) : Test(InTest), Deadline(FPlatformTime::Seconds() + 30.0) {}
	virtual bool Update() override
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			UWorld* World = Context.World(); if (Context.WorldType != EWorldType::PIE || !World || !World->HasBegunPlay()) continue;
			for (TActorIterator<AKZPlayer> It(World); It; ++It)
				if (It->IsPlayerControlled() && It->GetController() && It->GetCharacterDefinition() && It->GetCharacterMovement()->IsMovingOnGround() && It->GetMesh()->GetAnimInstance() && Cast<UKZAbilitySystemComponent>(It->GetAbilitySystemComponent()))
				{ FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FProbe>(Test, *It)); return true; }
		}
		if (FPlatformTime::Seconds() < Deadline) return false;
		Test->AddError(TEXT("No ready possessed player in the owned Work PIE world. Start PIE after TestStarted.")); return true;
	}
private: FAutomationTestBase* Test; double Deadline;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZMonsterStaminaPIETest, "Khazan.Monster.StaminaPIE", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKZMonsterStaminaPIETest::RunTest(const FString& Parameters)
{
	if (!FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()), KZMonsterStaminaPIE::WorkRoot))
	{ AddError(TEXT("Monster Stamina PIE probe is restricted to the exact isolated MonsterWork project.")); return false; }
	FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<KZMonsterStaminaPIE::FWait>(this)); return true;
}
#endif
