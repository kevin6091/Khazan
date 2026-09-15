#include "Data/KhazanCharacterDefinitionData.h"

const FKhazanLocomotionConfig& UKhazanCharacterDefinitionData::GetLocomotionConfig() const
{
	return LocomotionConfig;
}

const TArray<FKhazanInitialAbilityGrant>&
UKhazanCharacterDefinitionData::GetInitialAbilityGrants() const
{
	return InitialAbilityGrants;
}