


#include "KZGameplayTags.h"

namespace KZGameplayTags
{
#pragma region InputAction Tags

	// Move
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Move, "Input.Action.Move");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Sprint, "Input.Action.Sprint");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Turn, "Input.Action.Turn");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Jump, "Input.Action.Jump");

	// Attack
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_X, "Input.Action.X");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Y, "Input.Action.Y");

#pragma endregion

#pragma region Command Tags

	UE_DEFINE_GAMEPLAY_TAG(Command_Player_Attack_X, "Command.Player.Attack.X");

	UE_DEFINE_GAMEPLAY_TAG(Command_Player_Attack_Y, "Command.Player.Attack.Y");

#pragma endregion

#pragma region Ability Tags

	UE_DEFINE_GAMEPLAY_TAG(Ability_Action, "Ability.Action");
	UE_DEFINE_GAMEPLAY_TAG(Ability_Action_Attack, "Ability.Action.Attack");

#pragma endregion

	// AssetData Tags
	UE_DEFINE_GAMEPLAY_TAG(AssetData_InputData, "AssetData.InputData");
	UE_DEFINE_GAMEPLAY_TAG(AssetData_CharacterDefinition_Player, "AssetData.CharacterDefinition.Player");

	// AssetLabel Tags
	UE_DEFINE_GAMEPLAY_TAG(AssetLabel_Preload, "AssetLabel.Preload");


	// Block Tags
	UE_DEFINE_GAMEPLAY_TAG(Block_Movement_Input, "Block.Movement.Input");
	UE_DEFINE_GAMEPLAY_TAG(Block_StaminaRegen, "Block.StaminaRegen");
	
	// Delay Tags
	UE_DEFINE_GAMEPLAY_TAG(Delay_StaminaRegen, "Delay.StaminaRegen");

#pragma region Unlock Tags

	UE_DEFINE_GAMEPLAY_TAG(Unlock_Skill_DAS_WeakAttack05, "Unlock.Skill.DAS.WeakAttack05");

#pragma endregion
}
