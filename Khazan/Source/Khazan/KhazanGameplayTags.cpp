


#include "KhazanGameplayTags.h"

namespace KhazanGameplayTags
{
#pragma region InputAction Tags
	
	// Move
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Move, "Input.Action.Move");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Sprint, "Input.Action.Sprint");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Turn, "Input.Action.Turn");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_Jump, "Input.Action.Jump");
	
	// Attack
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_WeakAttack, "Input.Action.WeakAttack");
	UE_DEFINE_GAMEPLAY_TAG(Input_Action_StrongAttack, "Input.Action.StrongAttack");
	
#pragma endregion
	
	// AssetData Tags
	UE_DEFINE_GAMEPLAY_TAG(AssetData_InputData, "AssetData.InputData");
	UE_DEFINE_GAMEPLAY_TAG(AssetData_CharacterDefinition_Khazan, "AssetData.CharacterDefinition.Khazan");
	
	// AssetLabel Tags
	UE_DEFINE_GAMEPLAY_TAG(AssetLabel_Preload, "AssetLabel.Preload");
	
	
	// Block Tags
	UE_DEFINE_GAMEPLAY_TAG(Block_Movement_Input, "Block.Movement.Input");
	
#pragma region Unlock Tags

	UE_DEFINE_GAMEPLAY_TAG(Unlock_Skill_DAS_WeakAttack05, "Unlock.Skill.DAS.WeakAttack05");

#pragma endregion
}
