#include "Animation/Notifies/KZAnimNotifyState_MonsterVisual.h"
#include "Character/KZMonster.h"
#include "Animation/Notifies/KZAnimNotify_CombatEffect.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimNotifyQueue.h"
#include "Animation/AnimNotifyLibrary.h"

UKZAnimNotifyState_MonsterVisual::UKZAnimNotifyState_MonsterVisual()
{
	// Engine default matching also supports BlendSpace/SingleNode paths without source-instance context.
}

void UKZAnimNotifyState_MonsterVisual::NotifyBegin(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, float TotalDuration, const FAnimNotifyEventReference& Reference)
{
	if (AKZMonster* Monster = IsValid(Mesh) ? Cast<AKZMonster>(Mesh->GetOwner()) : nullptr)
		Monster->BeginMonsterVisual(*this, Mesh, Reference);
}

void UKZAnimNotifyState_MonsterVisual::NotifyTick(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, float DeltaSeconds, const FAnimNotifyEventReference& Reference)
{
	if (AKZMonster* Monster = IsValid(Mesh) ? Cast<AKZMonster>(Mesh->GetOwner()) : nullptr)
		Monster->TickMonsterVisual(*this, Mesh, Reference);
}

void UKZAnimNotifyState_MonsterVisual::NotifyEnd(USkeletalMeshComponent* Mesh,
	UAnimSequenceBase* Animation, const FAnimNotifyEventReference& Reference)
{

	if (AKZMonster* Monster = IsValid(Mesh) ? Cast<AKZMonster>(Mesh->GetOwner()) : nullptr)
	{
		if (bAnimationContextBoundary) Monster->EndMonsterVisualContext(Mesh, Reference);
		else Monster->EndMonsterVisual(Mesh, Reference.GetNotifyInstanceID(), UAnimNotifyLibrary::NotifyStateReachedEnd(Reference));
	}
}
