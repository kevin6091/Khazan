

#pragma once

#include "NativeGameplayTags.h"

namespace KZGameplayTags
{
#pragma region InputAction Tags

	// Move
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Move);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Sprint);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Turn);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Jump);

	// Attack
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_X);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Y);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_B);
	
	// LockOn
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_LockOn);
	
	// Dodge
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_A);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Guard);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Heal);
	
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_RB);

#pragma endregion

	// Player, AI가 공통으로 제출하는 커맨드 의도.
#pragma region Command Tags

	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_Player_Attack_X);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_Player_Attack_Y);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_Player_Dodge_A);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_Player_RB);
	
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_AI_Alert);

#pragma endregion

	// 현재 실행 중인 Ability
#pragma region Ability Tags

	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action_Attack);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action_Dodge);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action_Guard);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action_Heal);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Guarding);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Reaction_Exhaustion);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action_BrutalAttack);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Exhausted);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Dead);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Reaction_Hit);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_HitReacting);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Invulnerable);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Combat_Hit_Short);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Combat_Hit_Knockback);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Combat_Hit_Launch);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Combat_ShieldBlock);

#pragma endregion

	// AssetData Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_InputData);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_Player);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_Swordsman);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_SwordShield);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_HeavySwordsman);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_HalberdElite);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_ApesStoneHandElite);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_Yetuga);

	// AssetLabel Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetLabel_Preload);


	// Block Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Block_Movement_Input);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Block_StaminaRegen);
	
	// Delay Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Delay_StaminaRegen);


#pragma region Unlock Tags

	// Skill
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Unlock_Skill_DAS_WeakAttack05);
	

#pragma endregion

}
