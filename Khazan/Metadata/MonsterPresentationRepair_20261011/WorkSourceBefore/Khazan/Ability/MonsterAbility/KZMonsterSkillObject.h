#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Ability/Combo/KZComboDefinitionData.h"
#include "KZMonsterSkillObject.generated.h"

/** A launched rock/ice field outlives its caster montage. No second character AI/FSM. */
UCLASS()
class KHAZAN_API AKZMonsterSkillObject : public AActor
{
	GENERATED_BODY()
public:
	AKZMonsterSkillObject();
	void Initialize(const FKZMonsterPatternObject& Definition, TSubclassOf<class UGameplayEffect> DamageEffect,
		class AKZMonster* Caster, UObject* Source, const FKZMonsterPatternObject* TrailDefinition = nullptr,uint32 SourceRun = 0);
	void Shoot(AActor* Target, bool bFlatAim = false);
	void TriggerDestruction();
	bool HasLaunched() const { return bLaunched; }
	FName GetObjectId() const { return Data.Id; }
	bool ShouldEndWithAbility() const { return Data.bDestroyOnAbilityEnd || !bLaunched; }
	virtual void Tick(float DeltaSeconds) override;
private:
	void Impact(bool bWorld, bool bExpired = false);
	void SpawnTrail();
	bool ApplyHit(AActor* Actor);
	void PlayState(FName State);
	UPROPERTY() FKZMonsterPatternObject Data;
	UPROPERTY() FKZMonsterPatternObject TrailData;
	UPROPERTY() TSubclassOf<UGameplayEffect> DamageEffect;
	UPROPERTY() TObjectPtr<class USceneComponent> Scene;
	UPROPERTY() TObjectPtr<class UStaticMeshComponent> Visual;
	UPROPERTY() TObjectPtr<class USkeletalMeshComponent> AnimatedVisual;
	TWeakObjectPtr<class AKZMonster> Caster;
	TWeakObjectPtr<UObject> Source;
	TSet<TWeakObjectPtr<AActor>> Hits;
	FVector ShotOrigin=FVector::ZeroVector;
	FRotator ShotRotation=FRotator::ZeroRotator;
	float Age=0.f, FlightAge=0.f, RemainingImpact=0.f;
	int32 TrailCount=0;
	uint32 SourceRun=0;
	bool bLaunched=false, bImpact=false;
};
