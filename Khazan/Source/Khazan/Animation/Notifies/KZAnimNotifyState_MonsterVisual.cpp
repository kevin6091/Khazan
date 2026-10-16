#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "Character/KZMonster.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimNotifyQueue.h"
#include "Animation/AnimNotifyLibrary.h"
#include "Ability/MonsterAbility/KZMonsterSkillObject.h"
#include "Camera/KZCombatCameraModifier.h"
#include "GameFramework/PlayerController.h"
#include "Player/KZPlayerController.h"
#include "Engine/World.h"

UKZAnimNotifyState_MonsterVisual::UKZAnimNotifyState_MonsterVisual()
{
	// Engine default matching also supports BlendSpace/SingleNode paths without source-instance context.
}

void UKZAnimNotifyState_MonsterVisual::NotifyBegin(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, float TotalDuration, const FAnimNotifyEventReference& Reference)
{
	if (bSourceCameraShake)
	{
		// Reuse authored impacts/landings/roars, independently of camera output settings.
		if (IsValid(Mesh) && Mesh->GetOwner() && Mesh->GetOwner()->IsA<AKZMonster>() &&
			CameraShakeScale > 0.f && CameraFinalScale > 0.f &&
			(!CameraAmplitudeCm.IsNearlyZero() || !FMath::IsNearlyZero(CameraFOVAmplitudeDegrees)))
			AKZPlayerController::PlayCombatRumble(Mesh->GetOwner(), true);
		if (IsValid(Mesh) && Mesh->GetOwner() && Mesh->GetOwner()->IsA<AKZMonster>())
			if (UWorld* World = Mesh->GetWorld(); World && World->GetNetMode() != NM_DedicatedServer)
				for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
					if (UKZCombatCameraModifier* Modifier = UKZCombatCameraModifier::GetOrCreate(It->Get()))
						Modifier->StartSourceShake(Mesh, Reference.GetNotifyInstanceID(), CameraEventId,
							TotalDuration, CameraAmplitudeCm, CameraFrequencyHz, CameraFOVAmplitudeDegrees,
							CameraFOVFrequencyHz, CameraShakeScale, CameraFinalScale, CameraFadeInSeconds,
							CameraFadeOutSeconds, CameraNearRadiusCm, CameraFarRadiusCm, CameraDistanceBone);
		return;
	}
	if (AKZMonster* Monster = IsValid(Mesh) ? Cast<AKZMonster>(Mesh->GetOwner()) : nullptr)
		Monster->BeginMonsterVisual(*this, Mesh, Reference);
	else if (AKZMonsterSkillObject* Object = IsValid(Mesh) ? Cast<AKZMonsterSkillObject>(Mesh->GetOwner()) : nullptr)
		Object->BeginVisual(*this, Mesh, Reference);
}

void UKZAnimNotifyState_MonsterVisual::NotifyTick(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, float DeltaSeconds, const FAnimNotifyEventReference& Reference)
{
	if (bSourceCameraShake) return;
	if (AKZMonster* Monster = IsValid(Mesh) ? Cast<AKZMonster>(Mesh->GetOwner()) : nullptr)
		Monster->TickMonsterVisual(*this, Mesh, Reference);
	else if (AKZMonsterSkillObject* Object = IsValid(Mesh) ? Cast<AKZMonsterSkillObject>(Mesh->GetOwner()) : nullptr)
		Object->TickVisual(Reference);
}

void UKZAnimNotifyState_MonsterVisual::NotifyEnd(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, const FAnimNotifyEventReference& Reference)
{
	if (bSourceCameraShake)
	{
		if (UWorld* World = IsValid(Mesh) ? Mesh->GetWorld() : nullptr)
			for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
				if (UKZCombatCameraModifier* Modifier = UKZCombatCameraModifier::GetOrCreate(It->Get()))
					Modifier->EndSourceShake(Mesh, Reference.GetNotifyInstanceID());
		return;
	}

	if (AKZMonster* Monster = IsValid(Mesh) ? Cast<AKZMonster>(Mesh->GetOwner()) : nullptr)
	{
		if (bAnimationContextBoundary) Monster->EndMonsterVisualContext(Mesh, Reference);
		else Monster->EndMonsterVisual(Mesh, Reference.GetNotifyInstanceID(), UAnimNotifyLibrary::NotifyStateReachedEnd(Reference));
	}
	else if (AKZMonsterSkillObject* Object = IsValid(Mesh) ? Cast<AKZMonsterSkillObject>(Mesh->GetOwner()) : nullptr)
		Object->EndVisual(bAnimationContextBoundary ? INDEX_NONE : Reference.GetNotifyInstanceID(), UAnimNotifyLibrary::NotifyStateReachedEnd(Reference));
}
