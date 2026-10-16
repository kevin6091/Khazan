#include "Ability/PlayerAbility/KZFallAbility.h"
#include "AbilitySystemComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KZGameplayTags.h"

UKZFallAbility::UKZFallAbility()
{
	// Ordinary falling is presentation, so it owns neither movement nor combat blocking.
	ActivationOwnedTags.Reset(); BlockAbilitiesWithTag.Reset(); CancelAbilitiesWithTag.Reset();
}

bool UKZFallAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const
{
	const ACharacter* Character = ActorInfo ? Cast<ACharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
	if (!Character || !Character->GetCharacterMovement()->IsFalling()) return false;
	if (!bPlungeAttack && ActorInfo->AbilitySystemComponent->GetAnimatingAbility()) return false;
	return Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags);
}

void UKZFallAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
	BoundCharacter = ActorInfo ? Cast<ACharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
	if (ACharacter* Character = BoundCharacter.Get())
	{
		Character->LandedDelegate.AddUniqueDynamic(this, &ThisClass::HandleLanded);
		if (bPlungeAttack)
		{
			// Pass combatant bodies until landing recovery. ECC_Pawn object-query
			// damage still sees this capsule; this grants no invulnerability.
			PreviousPawnResponse = Character->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn);
			Character->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
			if (!IsActive()) return;
		}
	}
	Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData);
}

void UKZFallAbility::HandleLanded(const FHitResult& Hit)
{
	// Landed broadcasts during CMC Falling, before it selects Walking; no timer or estimated ground height.
	if (IsActive() && GetCurrentNodeId() != LandingNode && !TransitionToNode(LandingNode)) FinishAbility(true);
}

void UKZFallAbility::ProcessMontageNotify(FName Notify)
{
	if (Notify == TEXT("FallLoop")) { if (!LoopNode.IsNone()) TransitionToNode(LoopNode); return; }
	// Airborne X cannot turn a pre-impact notify into ordinary ground combo/cancel permission.
	if (bPlungeAttack && GetCurrentNodeId() != LandingNode) return;
	Super::ProcessMontageNotify(Notify);
}

void UKZFallAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
	if (ACharacter* Character = BoundCharacter.Get())
	{
		Character->LandedDelegate.RemoveDynamic(this, &ThisClass::HandleLanded);
		UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
		if (PreviousPawnResponse.IsSet() && Capsule->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Overlap)
			Capsule->SetCollisionResponseToChannel(ECC_Pawn, PreviousPawnResponse.GetValue());
	}
	PreviousPawnResponse.Reset();
	BoundCharacter.Reset();
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}
