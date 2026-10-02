


#include "Ability/PlayerAbility/KZDodgeAbility.h"

#include "KZGameplayTags.h"

UKZDodgeAbility::UKZDodgeAbility()
{
	// GAS가 이 Ability를 공격 행동으로 구분할 때 쓰는 태그다.
	FGameplayTagContainer AssetTags;
	AssetTags.AddTag(KZGameplayTags::Ability_Action_Dodge);
	SetAssetTags(AssetTags);
}
