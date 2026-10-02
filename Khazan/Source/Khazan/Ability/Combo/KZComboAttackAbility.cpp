#include "Ability/Combo/KZComboAttackAbility.h"

#include "KZGameplayTags.h"

UKZComboAttackAbility::UKZComboAttackAbility()
{
	// GAS가 이 Ability를 공격 행동으로 구분할 때 쓰는 태그다.
	FGameplayTagContainer AssetTags;
	AssetTags.AddTag(KZGameplayTags::Ability_Action_Attack);
	SetAssetTags(AssetTags);
}