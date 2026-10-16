

#pragma once

#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "KZAttributeSet.generated.h"

UCLASS()
class KHAZAN_API UKZAttributeSet : public UAttributeSet
{
	GENERATED_BODY()

public:
	ATTRIBUTE_ACCESSORS_BASIC(UKZAttributeSet, HP)
	ATTRIBUTE_ACCESSORS_BASIC(UKZAttributeSet, MaxHP)
	ATTRIBUTE_ACCESSORS_BASIC(UKZAttributeSet, Stamina)
	ATTRIBUTE_ACCESSORS_BASIC(UKZAttributeSet, MaxStamina)

	virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;

	virtual void PreAttributeBaseChange(const FGameplayAttribute& Attribute, float& NewValue) const override;

	virtual void PostAttributeChange(const FGameplayAttribute& Attribute, float OldValue, float NewValue) override;

	virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;

private:
	void ClampValue(const FGameplayAttribute& Attribute, float& NewValue) const;

	UPROPERTY(BlueprintReadOnly, Category = "KZ|Health", meta = (AllowPrivateAccess = "true"))
	FGameplayAttributeData HP;

	UPROPERTY(BlueprintReadOnly, Category = "KZ|Health", meta = (AllowPrivateAccess = "true"))
	FGameplayAttributeData MaxHP;

	UPROPERTY(BlueprintReadOnly, Category = "KZ|Stamina", meta = (AllowPrivateAccess = "true"))
	FGameplayAttributeData Stamina;

	UPROPERTY(BlueprintReadOnly, Category = "KZ|Stamina", meta = (AllowPrivateAccess = "true"))
	FGameplayAttributeData MaxStamina;
};
