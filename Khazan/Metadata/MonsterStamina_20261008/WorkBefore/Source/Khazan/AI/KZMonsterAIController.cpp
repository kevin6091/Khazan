#include "AI/KZMonsterAIController.h"

#include "Character/KZMonster.h"
#include "Character/KZPlayer.h"
#include "Components/StateTreeAIComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Sight.h"
#include "Perception/AISense_Sight.h"
#include "Engine/World.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Kismet/KismetMathLibrary.h"

AKZMonsterAIController::AKZMonsterAIController()
{
	PrimaryActorTick.bCanEverTick = true;
	bAllowStrafe = true;
	StateTreeComponent = CreateDefaultSubobject<UStateTreeAIComponent>(TEXT("MonsterStateTree"));
	StateTreeComponent->SetStartLogicAutomatically(false);
	BrainComponent = StateTreeComponent;
	MonsterPerception = CreateDefaultSubobject<UAIPerceptionComponent>(TEXT("MonsterPerception"));
	SetPerceptionComponent(*MonsterPerception);
	SightConfig = CreateDefaultSubobject<UAISenseConfig_Sight>(TEXT("MonsterSight"));
	SightConfig->DetectionByAffiliation.bDetectEnemies = true;
	SightConfig->DetectionByAffiliation.bDetectFriendlies = true;
	SightConfig->DetectionByAffiliation.bDetectNeutrals = true;
	MonsterPerception->ConfigureSense(*SightConfig);
	MonsterPerception->SetDominantSense(UAISense_Sight::StaticClass());
	MonsterPerception->OnTargetPerceptionUpdated.AddDynamic(this, &ThisClass::HandleTargetPerception);
}

AKZMonster* AKZMonsterAIController::GetMonster() const { return Cast<AKZMonster>(GetPawn()); }

FRotator AKZMonsterAIController::GetDesiredRotation() const
{
	const AKZMonster* Monster = GetMonster();
	const AActor* Target = BattleTarget.Get();
	const UKZLocomotionComponent* Locomotion = BoundLocomotion.Get();
	if (!Monster || !Target || !Locomotion ||
		Locomotion->GetResolvedMovementPolicy().ResolvedRotationMode != EKZRotationMode::LockOn)
	{
		return Super::GetDesiredRotation();
	}

	const FRotator BodyRotation = Monster->GetActorRotation();
	const FVector ToTarget = (Target->GetActorLocation() - Monster->GetActorLocation()).GetSafeNormal2D();
	if (ToTarget.IsNearlyZero()) return BodyRotation;
	FRotator Desired(0.f, UKismetMathLibrary::FindLookAtRotation(Monster->GetActorLocation(), Target->GetActorLocation()).Yaw, 0.f);
	const UAbilitySystemComponent* ASC = Monster->GetAbilitySystemComponent();
	const UKZComboActionAbility* Attack = ASC ? Cast<UKZComboActionAbility>(ASC->GetAnimatingAbility()) : nullptr;
	if (!Attack || !Attack->IsActive() || !Monster->GetAttackAbilities().Contains(Attack->GetClass()))
	{
		// Unaware/alert root turns keep their authored rotation. Ordinary combat movement faces the live target.
		return Monster->GetCharacterMovement()->HasAnimRootMotion() ? BodyRotation : Desired;
	}

	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	const UAnimInstance* Anim = Monster->GetMesh()->GetAnimInstance();
	const UAnimMontage* Montage = Anim ? Anim->GetCurrentActiveMontage() : nullptr;
	bool bPreparing = Attack->IsApproachingComboTransition(Settings.AttackPreparationSeconds);
	if (Montage)
	{
		const float Position = Anim->Montage_GetPosition(Montage);
		const int32 Section = Montage->GetSectionIndexFromPosition(Position);
		const float PlayRate = Anim->Montage_GetEffectivePlayRate(Montage);
		bPreparing |= Section != INDEX_NONE && PlayRate > 0.f &&
			(Position - Montage->GetAnimCompositeSection(Section).GetTime()) / PlayRate < Settings.AttackPreparationSeconds;
	}
	const float Rate = bPreparing ? Settings.ComboReaimYawRate : Settings.AttackTrackingYawRate;
	// Wrap-safe constant angular speed, no capsule snap and no replacement of locomotion RotationRate.
	Desired.Yaw = UKismetMathLibrary::FixedTurn(BodyRotation.Yaw, Desired.Yaw, FMath::Max(0.f, Rate) * GetWorld()->GetDeltaSeconds());
	return Desired;
}

void AKZMonsterAIController::BeginPlay()
{
	Super::BeginPlay();
	StartMonsterLogic();
}

void AKZMonsterAIController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	HomeLocation = InPawn->GetActorLocation();
	if (HasActorBegunPlay()) StartMonsterLogic();
}

void AKZMonsterAIController::StartMonsterLogic()
{
	AKZMonster* Monster = GetMonster();
	if (!Monster || !HasAuthority() || BoundLocomotion.IsValid() || !Monster->GetAIStateTree() || !Monster->GetCharacterDefinition()) return;
	UKZLocomotionComponent* Locomotion = Monster->GetLocomotionComponent();
	IntentHandle = Locomotion->BeginLocomotionIntentSource(this, EKZLocomotionIntentSource::AIController);
	if (!IntentHandle.IsValid()) return;
	BoundLocomotion = Locomotion;
	MovementPermissionHandle = Locomotion->OnMovementInputPermissionChanged().AddUObject(this, &ThisClass::HandleMovementPermissionChanged);
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	SightConfig->SightRadius = Settings.SightRadius;
	SightConfig->LoseSightRadius = FMath::Max(Settings.SightRadius, Settings.LoseSightRadius);
	SightConfig->PeripheralVisionAngleDegrees = Settings.PeripheralVisionHalfAngle;
	// MaxAge governs the sensory record; an acquired BattleTarget persists independently.
	SightConfig->SetMaxAge(Settings.TargetMemorySeconds);
	MonsterPerception->ConfigureSense(*SightConfig);
	MonsterPerception->RequestStimuliListenerUpdate();
	StateTreeComponent->SetStateTree(Monster->GetAIStateTree());
	StateTreeComponent->StartLogic();
}

void AKZMonsterAIController::ReleaseMonsterLogic()
{
	StateTreeComponent->StopLogic(TEXT("Monster controller lifetime ended"));
	StopRequestedMove();
	if (UKZLocomotionComponent* Locomotion = BoundLocomotion.Get())
	{
		Locomotion->OnMovementInputPermissionChanged().Remove(MovementPermissionHandle);
		Locomotion->EndLocomotionIntentSource(IntentHandle);
	}
	MovementPermissionHandle.Reset();
	IntentHandle.Reset();
	BoundLocomotion.Reset();
	BattleTarget.Reset();
	AlertedTarget.Reset();
	LastAttackClass.Reset();
	NextAttackAt = 0.f;
	ClearFocus(EAIFocusPriority::Gameplay);
}

void AKZMonsterAIController::OnUnPossess()
{
	ReleaseMonsterLogic();
	Super::OnUnPossess();
}

void AKZMonsterAIController::EndPlay(const EEndPlayReason::Type Reason)
{
	ReleaseMonsterLogic();
	Super::EndPlay(Reason);
}

void AKZMonsterAIController::HandleTargetPerception(AActor* Actor, FAIStimulus Stimulus)
{
	const AKZPlayer* Player = Cast<AKZPlayer>(Actor);
	if (!Player || !Player->IsPlayerControlled() || !GetMonster()) return;
	if (Stimulus.WasSuccessfullySensed())
	{
		if (!BattleTarget.IsValid() || BattleTarget == Actor)
		{
			BattleTarget = Actor;
			SetFocus(Actor, EAIFocusPriority::Gameplay);
			if (AKZMonster* Partner = GetMonster()->GetTalkPartner(); Partner && GetMonster()->HasActiveTalkLoop() && Partner->HasActiveTalkLoop())
			{
				if (AKZMonsterAIController* OtherAI = Cast<AKZMonsterAIController>(Partner->GetController()); OtherAI && !OtherAI->BattleTarget.IsValid())
				{
					OtherAI->BattleTarget = Actor;
					OtherAI->SetFocus(Actor, EAIFocusPriority::Gameplay);
				}
			}
		}
	}
	// Sight loss ends the sensory observation, not the encounter with this valid player.
}

void AKZMonsterAIController::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// APawn can auto-possess inside Super::PostInitializeComponents, before Definition initialization.
	if (!BoundLocomotion.IsValid()) StartMonsterLogic();
	const AKZMonster* Monster = GetMonster();
	if (!Monster) return;
	if (!BattleTarget.IsValid())
	{
		BattleTarget.Reset();
		AlertedTarget.Reset();
		ClearFocus(EAIFocusPriority::Gameplay);
	}
	else SetFocus(BattleTarget.Get(), EAIFocusPriority::Gameplay);
	MirrorNavigationIntent();
}

float AKZMonsterAIController::GetTargetDistance() const
{
	return BattleTarget.IsValid() && GetPawn() ? FVector::Dist2D(GetPawn()->GetActorLocation(), BattleTarget->GetActorLocation()) : TNumericLimits<float>::Max();
}

bool AKZMonsterAIController::NeedsAlert() const { return BattleTarget.IsValid() && BattleTarget != AlertedTarget; }

bool AKZMonsterAIController::CanChooseAttack() const
{
	const AKZMonster* Monster = GetMonster();
	if (!Monster || !BattleTarget.IsValid() || NeedsAlert() || GetWorld()->GetTimeSeconds() < NextAttackAt) return false;
	const FKZMonsterAISettings& Settings = Monster->GetAISettings();
	const FVector Direction = (BattleTarget->GetActorLocation() - Monster->GetActorLocation()).GetSafeNormal2D();
	return GetTargetDistance() <= Settings.AttackDistance &&
		FVector::DotProduct(Monster->GetActorForwardVector(), Direction) >= FMath::Cos(FMath::DegreesToRadians(Settings.AttackFacingHalfAngle));
}

void AKZMonsterAIController::SetMovementPolicy(EKZGait Gait, EKZRotationMode Mode)
{
	if (UKZLocomotionComponent* Locomotion = BoundLocomotion.Get())
	{
		Locomotion->SetRequestedGait(IntentHandle, Gait);
		Locomotion->SetRequestedRotationMode(IntentHandle, Mode);
	}
}

void AKZMonsterAIController::MirrorNavigationIntent()
{
	UKZLocomotionComponent* Locomotion = BoundLocomotion.Get();
	if (!Locomotion || !GetPawn()) return;
	if (!Locomotion->IsMovementInputAllowed()) { StopRequestedMove(); return; }
	const UPathFollowingComponent* Path = GetPathFollowingComponent();
	if (Path && Path->GetStatus() == EPathFollowingStatus::Moving)
	{
		Locomotion->SetMoveInputWorld(IntentHandle, (Path->GetCurrentTargetLocation() - GetPawn()->GetActorLocation()).GetSafeNormal2D());
	}
	else Locomotion->ClearMoveInput(IntentHandle);
}

void AKZMonsterAIController::StopRequestedMove()
{
	StopMovement();
	if (UKZLocomotionComponent* Locomotion = BoundLocomotion.Get()) Locomotion->ClearMoveInput(IntentHandle);
}

void AKZMonsterAIController::HandleMovementPermissionChanged(bool bAllowed)
{
	if (!bAllowed) StopRequestedMove();
}
