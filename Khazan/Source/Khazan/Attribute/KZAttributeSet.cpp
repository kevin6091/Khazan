
#include "Attribute/KZAttributeSet.h"

#include "GameplayEffectExtension.h"
#include "LogChannels.h"

void UKZAttributeSet::PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue)
{
	Super::PreAttributeChange(Attribute, NewValue);
	ClampValue(Attribute, NewValue);
}

void UKZAttributeSet::PreAttributeBaseChange(const FGameplayAttribute& Attribute, float& NewValue) const
{
	Super::PreAttributeBaseChange(Attribute, NewValue);
	ClampValue(Attribute, NewValue);
	
	if (Attribute == GetStaminaAttribute() && !FMath::IsNearlyEqual(NewValue, GetStamina()))
	{
		UE_LOG(LogAttribute, Log, TEXT("%s : Stamina Change %.1f "), *GetOwningActor()->GetName(), NewValue - GetStamina());
	}
}

void UKZAttributeSet::PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data)
{
	Super::PostGameplayEffectExecute(Data);
	
	const FGameplayAttribute& Attribute = Data.EvaluatedData.Attribute;

	if (Attribute == GetMaxStaminaAttribute())
	{
		SetStamina(FMath::Clamp(GetStamina(), 0.f, GetMaxStamina()));
		return;
	}

	if (Attribute == GetStaminaAttribute())
	{
		SetStamina(FMath::Clamp(GetStamina(), 0.f, FMath::Max(0.f, GetMaxStamina())));
		UE_LOG(LogAttribute, Log, TEXT("%s : Stamina = %.1f "), *GetOwningActor()->GetName(), GetStamina());
	}
}

void UKZAttributeSet::ClampValue(const FGameplayAttribute& Attribute, float& NewValue) const
{
	if (Attribute == GetMaxStaminaAttribute())
	{
		NewValue = FMath::Max(0.f, NewValue);
		return;
	}

	if (Attribute == GetStaminaAttribute())
	{
		const float SafeMax = FMath::Max(0.f, GetMaxStamina());
		NewValue = FMath::Clamp(NewValue, 0.f, SafeMax);
	}
}
