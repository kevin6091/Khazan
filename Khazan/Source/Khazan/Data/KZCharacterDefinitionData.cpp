#include "Data/KZCharacterDefinitionData.h"

const FKZLocomotionConfig& UKZCharacterDefinitionData::GetLocomotionConfig() const
{
	return LocomotionConfig;
}

const TArray<FKZInitialAbilityGrant>&
UKZCharacterDefinitionData::GetInitialAbilityGrants() const
{
	return InitialAbilityGrants;
}