#include "Data/KhazanInputData.h"
#include "LogChannels.h"


const UInputAction* UKhazanInputData::FindInputActionByTag(const FGameplayTag& InputTag) const
{
	for (const FKhazanInputAction& Action : InputActions)
	{
		if (Action.InputAction && Action.InputTag == InputTag)
		{
			return Action.InputAction;
		}
	}
	
	UE_LOG(LogDefault, Error, TEXT("Cant find InputAction for InputTag [%s]"), *InputTag.ToString());
	
	return nullptr;
}
