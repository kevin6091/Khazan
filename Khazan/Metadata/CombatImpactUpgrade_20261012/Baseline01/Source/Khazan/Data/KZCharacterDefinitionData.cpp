#include "Data/KZCharacterDefinitionData.h"

#include "Character/KZCharacter.h"
#include "AbilitySystemComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "Engine/World.h"
#include "Components/CapsuleComponent.h"

bool FKZCombatPatternCondition::Matches(const AKZCharacter* Owner, const AActor* Target) const
{
	if (!Owner || !Target) return false;
	const FVector Delta = Target->GetActorLocation() - Owner->GetActorLocation();
	const float Distance = Delta.Size2D();
	const float Yaw = FMath::FindDeltaAngleDegrees(Owner->GetActorRotation().Yaw + BaseYaw, Delta.Rotation().Yaw);
	const bool bTargetMatches = Distance >= MinDistance && (MaxDistance <= 0.f || Distance <= MaxDistance) &&
		Yaw >= -LeftYaw && Yaw <= RightYaw && Delta.Z >= MinHeight && Delta.Z <= MaxHeight;
	if (bTargetMatches == bInvertTarget) return false;
	const UAbilitySystemComponent* ASC = Owner->GetAbilitySystemComponent();
	if (!ASC) return false;
	float HP = ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute());
	if (bHPIsRatio) HP /= FMath::Max(ASC->GetNumericAttribute(UKZAttributeSet::GetMaxHPAttribute()), UE_SMALL_NUMBER);
	const float Stamina=ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute());
	if ((MaxHP >= 0.f && HP > MaxHP) || Stamina < MinStamina || (MaxStamina>=0.f && Stamina>MaxStamina)) return false;
	if (WallCheckDistance != 0.f)
	{
		FCollisionQueryParams Query(SCENE_QUERY_STAT(KZPatternWall), false, Owner);
		Query.AddIgnoredActor(Target);
		// Missing native WallCheck distance: explicitly provisional capsule-diameter probe.
		const float ProbeDistance=WallCheckDistance>0.f?WallCheckDistance:Owner->GetCapsuleComponent()->GetScaledCapsuleRadius()*2.f;
		const FVector End = Owner->GetActorLocation() + FRotator(0.f, Owner->GetActorRotation().Yaw + WallCheckYaw, 0.f).Vector() * ProbeDistance;
		const bool bWall = Owner->GetWorld()->LineTraceTestByChannel(Owner->GetActorLocation(), End, ECC_Visibility, Query);
		if (bWall == bRequireClearWall) return false;
	}
	return true;
}

const FKZLocomotionConfig& UKZCharacterDefinitionData::GetLocomotionConfig() const
{
	return LocomotionConfig;
}

const TArray<FKZInitialAbilityGrant>&
UKZCharacterDefinitionData::GetInitialAbilityGrants() const
{
	return InitialAbilityGrants;
}

const TArray<TSubclassOf<UGameplayEffect>>& UKZCharacterDefinitionData::GetInitialEffects() const
{
	return InitialEffects;
}
