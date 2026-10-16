


#include "Ability/PlayerAbility/KZDodgeAbility.h"

#include "KZGameplayTags.h"
#include "AbilitySystemComponent.h"
#include "Character/KZPlayer.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "TimerManager.h"
#include "LogChannels.h"

UKZDodgeAbility::UKZDodgeAbility()
{
	// GAS가 이 Ability를 공격 행동으로 구분할 때 쓰는 태그다.
	FGameplayTagContainer AssetTags;
	AssetTags.AddTag(KZGameplayTags::Ability_Action_Dodge);
	SetAssetTags(AssetTags);
}

void UKZDodgeAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
	const uint32 Execution = ++DodgeExecution;
	bSuccessFeedbackPlayed = false;
	Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData);
	if (!IsActive() || DodgeExecution != Execution) return;
	AKZPlayer* Player = ActorInfo ? Cast<AKZPlayer>(ActorInfo->AvatarActor.Get()) : nullptr;
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	if (!Player || !ASC || !GetWorld()) return;
	if (FMath::IsFinite(InvulnerabilitySeconds) && InvulnerabilitySeconds > 0.f)
	{
		InvulnerableUntil = double(GetWorld()->GetTimeSeconds()) + double(InvulnerabilitySeconds);
		bOwnsInvulnerabilityTag = true;
		ASC->AddLooseGameplayTag(KZGameplayTags::State_Invulnerable);
		if (!IsActive() || DodgeExecution != Execution) return;
		GetWorld()->GetTimerManager().SetTimer(InvulnerabilityTimer, this, &ThisClass::ClearInvulnerability, InvulnerabilitySeconds, false);
	}
	if (DodgeEffect && GetWorld()->GetNetMode() != NM_DedicatedServer)
	{
		const FNiagaraVariable ScaleParameter(FNiagaraTypeDefinition::GetFloatDef(), TEXT("User.Scale_All"));
		const bool bUserScale = DodgeEffect->GetExposedParameters().IndexOf(ScaleParameter) != INDEX_NONE;
		// Eight directions are mathematical actor-relative 45-degree sectors.
		DodgeComponent = UNiagaraFunctionLibrary::SpawnSystemAttached(DodgeEffect, Player->GetRootComponent(), NAME_None,
			FVector(0, 0, -Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), FRotator(0, int32(DodgeDirection) * 45., 0),
			FVector(bUserScale ? 1.f : DodgeEffectScale), EAttachLocation::KeepRelativeOffset, true, ENCPoolMethod::None, false, false);
		if (DodgeComponent.IsValid())
		{
			if (bUserScale) DodgeComponent->SetVariableFloat(TEXT("User.Scale_All"), DodgeEffect->GetExposedParameters().GetParameterValue<float>(ScaleParameter) * DodgeEffectScale);
			DodgeComponent->Activate(true);
		}
	}
}

bool UKZDodgeAbility::IsInvulnerableNow() const
{
	// An expiration timer runs at frame boundaries; this deadline also rejects
	// an overlap after .1 s in the frame before the tag-removal callback runs.
	return IsActive() && bOwnsInvulnerabilityTag && GetWorld() &&
		double(GetWorld()->GetTimeSeconds()) < InvulnerableUntil;
}

bool UKZDodgeAbility::TryAvoidHit(AActor* Attacker, const FVector& Contact)
{
	if (!IsInvulnerableNow()) return false;
	if (!bSuccessFeedbackPlayed)
	{
		bSuccessFeedbackPlayed = true; // Consume before feedback callbacks; at most one cue per dodge.
		AActor* Avatar = GetAvatarActorFromActorInfo();
		if (IsValid(Avatar) && GetWorld()->GetNetMode() != NM_DedicatedServer)
		{
			if (SuccessSound) UGameplayStatics::SpawnSoundAtLocation(Avatar, SuccessSound, Avatar->GetActorLocation());
			FVector EffectLocation = Avatar->GetActorLocation();
			if (const AKZPlayer* Player = Cast<AKZPlayer>(Avatar)) EffectLocation.Z -= Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			if (SuccessEffect)
			{
				const FNiagaraVariable ScaleParameter(FNiagaraTypeDefinition::GetFloatDef(), TEXT("User.Scale_All"));
				const bool bUserScale = SuccessEffect->GetExposedParameters().IndexOf(ScaleParameter) != INDEX_NONE;
				SuccessComponent = UNiagaraFunctionLibrary::SpawnSystemAtLocation(Avatar, SuccessEffect,
					EffectLocation, Avatar->GetActorRotation(), FVector(bUserScale ? 1.f : SuccessEffectScale), true, false, ENCPoolMethod::None, false);
				if (SuccessComponent.IsValid())
				{
					if (bUserScale) SuccessComponent->SetVariableFloat(TEXT("User.Scale_All"), SuccessEffect->GetExposedParameters().GetParameterValue<float>(ScaleParameter) * SuccessEffectScale);
					SuccessComponent->Activate(true);
				}
			}
		}
		UE_LOG(LogAbility, Log, TEXT("DodgeAvoid owner=%s attacker=%s execution=%u contact=%s"),
			*GetNameSafe(Avatar), *GetNameSafe(Attacker), DodgeExecution, *Contact.ToString());
	}
	return true;
}

void UKZDodgeAbility::ClearInvulnerability()
{
	if (UWorld* World = GetWorld()) World->GetTimerManager().ClearTimer(InvulnerabilityTimer);
	InvulnerableUntil = 0.;
	if (!bOwnsInvulnerabilityTag) return;
	bOwnsInvulnerabilityTag = false;
	if (UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo())
		ASC->RemoveLooseGameplayTag(KZGameplayTags::State_Invulnerable); // Our one contribution only.
}

void UKZDodgeAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo,
	FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
	++DodgeExecution;
	ClearInvulnerability();
	if (DodgeComponent.IsValid()) DodgeComponent->Deactivate();
	if (SuccessComponent.IsValid()) SuccessComponent->Deactivate();
	DodgeComponent.Reset(); SuccessComponent.Reset();
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}
