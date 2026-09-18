

#pragma once

#include "NativeGameplayTags.h"

namespace KhazanGameplayTags
{
#pragma region InputAction Tags
	
	// Move
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Move);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Sprint);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Turn);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Jump);
	
	// Attack
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_WeakAttack);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_StrongAttack);
	
#pragma endregion

	
	// AssetData Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_InputData);
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_Khazan);
	
	// AssetLabel Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetLabel_Preload);
	
	
	// Block Tags
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Block_Movement_Input);
	
	
#pragma region Unlock Tags

	// Skill
	UE_DECLARE_GAMEPLAY_TAG_EXTERN(Unlock_Skill_DAS_WeakAttack05);

#pragma endregion
	
}
