

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

#pragma endregion

	// Player, AI가 공통으로 제출하는 커맨드 의도.
#pragma region Command Tags

	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_Player_Attack_X);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Command_Player_Attack_Y);

#pragma endregion

	// 현재 실행 중인 Ability
#pragma region Ability Tags

	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Ability_Action_Attack);

#pragma endregion

	// AssetData Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_InputData);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_Player);

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
