


#include "Character/KZMonster.h"

#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "AI/KZMonsterAIController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Abilities/GameplayAbility.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "AbilitySystemComponent.h"
#include "Ability/MonsterAbility/KZExhaustionAbility.h"
#include "Attribute/KZAttributeSet.h"
#include "GameplayEffect.h"
#include "KZGameplayTags.h"
#include "TimerManager.h"

AKZMonster::AKZMonster()
{
	AIControllerClass = AKZMonsterAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	GetCharacterMovement()->GetNavMovementProperties()->bUseAccelerationForPaths = true;
	// AI supplies a bounded desired yaw during attacks; preserve the montage's root motion too.
	GetCharacterMovement()->bAllowPhysicsRotationDuringAnimRootMotion = true;
	LockOnTargetPoint = CreateDefaultSubobject<USceneComponent>(TEXT("LockOnTargetPoint"));
	
	LockOnTargetPoint->SetupAttachment(GetCapsuleComponent());
}

void AKZMonster::BeginPlay()
{
	Super::BeginPlay();
	// The HeavySwordsman uses the existing empty pose carrier and three modular parts.
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(this);
	for (USkeletalMeshComponent* Part : Meshes)
	{
		if (Part != GetMesh() && Part->ComponentHasTag(TEXT("MonsterBodyPart")))
		{
			Part->SetLeaderPoseComponent(GetMesh(), true, false);
		}
	}
	BindCombatAttributes();
}

void AKZMonster::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	if (HasActorBegunPlay()) BindCombatAttributes();
}

void AKZMonster::UnPossessed()
{
	UnbindCombatAttributes();
	if (UKZExhaustionAbility* Ability = GetActiveExhaustionAbility())
		GetAbilitySystemComponent()->CancelAbilityHandle(Ability->GetCurrentAbilitySpecHandle());
	Super::UnPossessed();
}

void AKZMonster::EndPlay(const EEndPlayReason::Type Reason)
{
	UnbindCombatAttributes();
	if (UKZExhaustionAbility* Ability = GetActiveExhaustionAbility())
		GetAbilitySystemComponent()->CancelAbilityHandle(Ability->GetCurrentAbilitySpecHandle());
	if (UAbilitySystemComponent* ASC = GetAbilitySystemComponent(); ASC && DeadStateHandle.IsValid())
		ASC->RemoveActiveGameplayEffect(DeadStateHandle);
	GetLocomotionComponent()->ReleaseMovementConstraint(DeadMovementHandle);
	Super::EndPlay(Reason);
}

void AKZMonster::BindCombatAttributes()
{
	if (!HasAuthority() || !GetController() || BoundCombatASC.IsValid() || !GetCharacterDefinition() ||
		!GetCharacterDefinition()->GetMonsterStaminaSettings().bEnabled) return;
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	BoundCombatASC = ASC;
	HealthChangedHandle = ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute())
		.AddUObject(this, &ThisClass::HandleCombatAttributeChanged);
	StaminaChangedHandle = ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute())
		.AddUObject(this, &ThisClass::HandleCombatAttributeChanged);
	RequestCombatStateRefresh();
}

void AKZMonster::UnbindCombatAttributes()
{
	if (UAbilitySystemComponent* ASC = BoundCombatASC.Get())
	{
		ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetHPAttribute()).Remove(HealthChangedHandle);
		ASC->GetGameplayAttributeValueChangeDelegate(UKZAttributeSet::GetStaminaAttribute()).Remove(StaminaChangedHandle);
	}
	HealthChangedHandle.Reset();
	StaminaChangedHandle.Reset();
	BoundCombatASC.Reset();
	GetWorldTimerManager().ClearTimer(CombatRefreshTimer);
}

void AKZMonster::HandleCombatAttributeChanged(const FOnAttributeChangeData&)
{
	RequestCombatStateRefresh();
}

void AKZMonster::RequestCombatStateRefresh()
{
	if (!BoundCombatASC.IsValid() || !GetController() || !HasActorBegunPlay() ||
		GetWorldTimerManager().TimerExists(CombatRefreshTimer)) return;
	// Coalesce all modifiers of a hit before choosing death/exhaustion, regardless of modifier order.
	CombatRefreshTimer = GetWorldTimerManager().SetTimerForNextTick(this, &ThisClass::RefreshCombatState);
}

UKZExhaustionAbility* AKZMonster::GetActiveExhaustionAbility() const
{
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	if (!ASC) return nullptr;
	FScopedAbilityListLock Lock(*ASC);
	for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		if (Spec.IsActive())
			if (UKZExhaustionAbility* Ability = Cast<UKZExhaustionAbility>(Spec.GetPrimaryInstance())) return Ability;
	return nullptr;
}

bool AKZMonster::IsCombatIncapacitated() const
{
	const UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	return ASC && GetCharacterDefinition() && GetCharacterDefinition()->GetMonsterStaminaSettings().bEnabled &&
		(ASC->HasMatchingGameplayTag(KZGameplayTags::State_Dead) || ASC->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) ||
		 ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f ||
		 ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) <= 0.f);
}

void AKZMonster::RefreshCombatState()
{
	CombatRefreshTimer.Invalidate();
	UAbilitySystemComponent* ASC = BoundCombatASC.Get();
	if (!ASC || !GetController() || !GetCharacterDefinition()) return;
	const FKZMonsterStaminaSettings& Settings = GetCharacterDefinition()->GetMonsterStaminaSettings();
	UKZExhaustionAbility* Exhaustion = GetActiveExhaustionAbility();
	if (ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)
	{
		if (!DeadStateHandle.IsValid() && Settings.DeadStateEffect)
		{
			const FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Settings.DeadStateEffect, 1.f, ASC->MakeEffectContext());
			if (Spec.IsValid()) DeadStateHandle = ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
		}
		if (!DeadMovementHandle.IsValid())
		{
			FKZMovementConstraint Constraint;
			Constraint.bOverrideRotationMode = true;
			Constraint.RotationModeOverride = EKZRotationMode::VelocityDirection;
			Constraint.DebugName = TEXT("MonsterDead");
			DeadMovementHandle = GetLocomotionComponent()->AcquireMovementConstraint(this, Constraint);
			FGameplayTagContainer Actions;
			Actions.AddTag(KZGameplayTags::Ability_Action);
			ASC->CancelAbilities(&Actions);
		}
		// A lethal paired attack must finish its victim reaction before freezing the corpse.
		if (!Exhaustion || !Exhaustion->HasBrutalPartner())
		{
			if (Exhaustion) ASC->CancelAbilityHandle(Exhaustion->GetCurrentAbilitySpecHandle());
			FinishDeathPresentation();
		}
		return;
	}
	if (ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) > 0.f || Exhaustion) return;
	FScopedAbilityListLock Lock(*ASC);
	for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		if (Spec.Ability && Spec.Ability->IsA<UKZExhaustionAbility>())
		{
			ASC->TryActivateAbility(Spec.Handle);
			break;
		}
}

void AKZMonster::FinishDeathPresentation()
{
	if (GetAbilitySystemComponent()->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)
		GetMesh()->bPauseAnims = true;
}

bool AKZMonster::ReportAttackParried(AActor* Defender)
{
	if (!HasAuthority() || !IsValid(Defender) || !GetCharacterDefinition()) return false;
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	const FKZMonsterStaminaSettings& Settings = GetCharacterDefinition()->GetMonsterStaminaSettings();
	if (!Settings.bEnabled || !Settings.DamageEffect || !FMath::IsFinite(Settings.ParryStaminaDamage) ||
		Settings.ParryStaminaDamage <= 0.f || ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f) return false;
	FGameplayEffectContextHandle Context = ASC->MakeEffectContext();
	Context.AddInstigator(Defender, Defender);
	const FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Settings.DamageEffect, 1.f, Context);
	if (!Spec.IsValid()) return false;
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackHPDamage")), 0.f);
	Spec.Data->SetSetByCallerMagnitude(FName(TEXT("KZAttackStaminaDamage")), -Settings.ParryStaminaDamage);
	return ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get()).WasSuccessfullyApplied();
}

void AKZMonster::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
}

AKZMonster* AKZMonster::GetTalkPartner() const
{
	AKZMonster* Partner = TalkPartner.Get();
	if (!IsValid(Partner) || Partner == this || Partner->TalkPartner != this ||
		Partner->bSecondTalkRole == bSecondTalkRole || bPatrolWhenUnaware || Partner->bPatrolWhenUnaware ||
		!Cast<AKZMonsterAIController>(GetController()) || !Cast<AKZMonsterAIController>(Partner->GetController())) return nullptr;
	const UKZCharacterDefinitionData* Definition = GetCharacterDefinition();
	const UKZCharacterDefinitionData* OtherDefinition = Partner->GetCharacterDefinition();
	if (!Definition || !OtherDefinition) return nullptr;
	const EKZUnawareRoutineRole RoutineRole = bSecondTalkRole ? EKZUnawareRoutineRole::Talk02 : EKZUnawareRoutineRole::Talk01;
	const EKZUnawareRoutineRole OtherRole = bSecondTalkRole ? EKZUnawareRoutineRole::Talk01 : EKZUnawareRoutineRole::Talk02;
	if (!Definition->GetUnawareRoutines().ContainsByPredicate([RoutineRole](const FKZUnawareRoutine& R) { return R.Role == RoutineRole && R.AbilityClass; }) ||
		!OtherDefinition->GetUnawareRoutines().ContainsByPredicate([OtherRole](const FKZUnawareRoutine& R) { return R.Role == OtherRole && R.AbilityClass; })) return nullptr;
	return Partner;
}

bool AKZMonster::HasActiveTalkLoop() const
{
	const UKZCharacterDefinitionData* Definition = GetCharacterDefinition();
	UAbilitySystemComponent* ASC = GetAbilitySystemComponent();
	if (!Definition || !ASC) return false;
	for (const FKZUnawareRoutine& Routine : Definition->GetUnawareRoutines())
	{
		if (Routine.Role == EKZUnawareRoutineRole::Solo) continue;
		const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromClass(Routine.AbilityClass);
		const UKZComboActionAbility* Ability = Spec ? Cast<UKZComboActionAbility>(Spec->GetPrimaryInstance()) : nullptr;
		if (Spec && Spec->IsActive() && Ability && Ability->GetCurrentNodeId() == TEXT("Loop")) return true;
	}
	return false;
}

const FKZUnawareRoutine* AKZMonster::ResolveUnawareRoutine(bool bAllowTalk) const
{
	const UKZCharacterDefinitionData* Definition = GetCharacterDefinition();
	if (!Definition) return nullptr;
	AKZMonster* Partner = bAllowTalk ? GetTalkPartner() : nullptr;
	if (Partner)
	{
		const AKZMonsterAIController* OtherAI = CastChecked<AKZMonsterAIController>(Partner->GetController());
		const UAbilitySystemComponent* OtherASC = Partner->GetAbilitySystemComponent();
		// A partner in a solo routine, an End, or combat cannot start a conversation.
		if (OtherAI->GetBattleTarget() || (OtherASC && !Partner->HasActiveTalkLoop() &&
			OtherASC->GetActivatableAbilities().ContainsByPredicate([](const FGameplayAbilitySpec& S) { return S.IsActive(); }))) Partner = nullptr;
	}
	const EKZUnawareRoutineRole RoutineRole = Partner ? (bSecondTalkRole ? EKZUnawareRoutineRole::Talk02 : EKZUnawareRoutineRole::Talk01) : EKZUnawareRoutineRole::Solo;
	TArray<const FKZUnawareRoutine*> Candidates;
	for (const FKZUnawareRoutine& Routine : Definition->GetUnawareRoutines())
	{
		if (Routine.Role != RoutineRole || !Routine.AbilityClass) continue;
		if (RoutineRole == EKZUnawareRoutineRole::Solo && Routine.Name == UnawareRoutineName) return &Routine;
		Candidates.Add(&Routine);
	}
	return Candidates.IsEmpty() ? nullptr : Candidates[FMath::RandHelper(Candidates.Num())];
}
