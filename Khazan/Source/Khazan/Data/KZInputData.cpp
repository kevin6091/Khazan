#include "Data/KZInputData.h"
#include "LogChannels.h"


const UInputAction* UKZInputData::FindInputActionByTag(const FGameplayTag& InputTag) const
{
	for (const FKZInputAction& Action : InputActions)
	{
		if (Action.InputAction && Action.InputTag == InputTag)
		{
			return Action.InputAction;
		}
	}

	UE_LOG(LogDefault, Error, TEXT("Cant find InputAction for InputTag [%s]"), *InputTag.ToString());

	return nullptr;
}
