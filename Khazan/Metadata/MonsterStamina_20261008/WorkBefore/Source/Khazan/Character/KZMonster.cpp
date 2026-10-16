


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
