

#pragma once

#include "CoreMinimal.h"
#include "Ability/KZGameplayAbility.h"
#include "Ability/Combo/KZComboTypes.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "KZComboAttackAbility.generated.h"

class UAbilityTask_PlayMontageAndWait;
class UAnimInstance;
class UKZComboDefinitionData;

struct FKZComboCommandEdge;
struct FKZComboNode;

// 현재 공격이 콤보 입력을 어떻게 받을지 나타낸다.
enum class EKZComboWindowPhase : uint8
{
	// 콤보 입력을 받지 않는다.
	Closed,

	// 입력을 한 번 저장하고 ComboCommit을 기다린다.
	OpenToCommit,

	// 입력이 들어오면 바로 다음 공격으로 넘어간다.
	CommitToEnd
};

// 콤보 데이터를 읽어 몽타주와 다음 공격 전환을 실행하는 공통 Ability다.
UCLASS(Abstract, Blueprintable)
class KHAZAN_API UKZComboAttackAbility : public UKZGameplayAbility
{
	GENERATED_BODY()

public:
	// 공격 공통 태그와 실행 방식을 설정한다.
	UKZComboAttackAbility();

protected:
	// 시작 노드를 확인하고 첫 공격 몽타주를 재생한다.
	virtual void ActivateAbility(
		FGameplayAbilitySpecHandle Handle,
		const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo,
		const FGameplayEventData* TriggerEventData) override;

	// 입력과 몽타주 연결을 끊고 이번 공격 상태를 정리한다.
	virtual void EndAbility(
		FGameplayAbilitySpecHandle Handle,
		const FGameplayAbilityActorInfo* ActorInfo,
		FGameplayAbilityActivationInfo ActivationInfo,
		bool bReplicateEndAbility,
		bool bWasCancelled) override;

private:
	// 몽타주가 자연스럽게 끝났을 때 Ability를 끝낸다.
	UFUNCTION()
	void HandleMontageCompleted();

	// 몽타주가 취소되거나 끊겼을 때 Ability를 취소 상태로 끝낸다.
	UFUNCTION()
	void HandleMontageAborted();

	// ComboInputOpen, ComboCommit, ComboInputEnd 노티파이를 처리한다.
	UFUNCTION()
	void HandleMontageNotifyBegin(FName NotifyName, const FBranchingPointNotifyPayload& Payload);

	// 이동 가능 구간에서 이동 입력이 오면 공격을 끝낸다.
	UFUNCTION()
	void HandleMoveInput(FGameplayEventData Payload);

	// ASC가 보낸 공격 명령을 현재 콤보 상태에 맞게 처리한다.
	void HandleComboCommand(const FKZComboCommand& Command);

	// 시작 노드의 몽타주와 섹션을 재생한다.
	bool StartEntryMontage();

	// 노드의 몽타주와 섹션이 실제로 재생 가능한지 확인한다.
	bool IsNodePlayable(const FKZComboNode& Node) const;

	// 현재 재생 중인 콤보 몽타주에서 온 노티파이인지 확인한다.
	bool IsNotifyFromCurrentMontage(const FBranchingPointNotifyPayload& Payload) const;

	// 현재 노드에서 명령과 조건이 모두 맞는 전환을 찾는다.
	const FKZComboCommandEdge* FindMatchingCommandEdge(const FKZComboCommand& Command) const;

	// 저장해 둔 입력을 다시 검사하고 다음 노드로 전환한다.
	bool CommitPendingCommand();

	// 같은 몽타주의 다른 공격 섹션으로 이동한다.
	bool TransitionToNode(FName TargetNodeId);

	// ASC의 콤보 명령을 받기 시작한다.
	void BindComboCommandDelegate();

	// ASC의 콤보 명령을 더 이상 받지 않는다.
	void UnbindComboCommandDelegate();

	// 몽타주의 노티파이를 받기 시작한다.
	void BindMontageNotifyDelegate(UAnimInstance* AnimInstance);

	// 몽타주의 노티파이를 더 이상 받지 않는다.
	void UnbindMontageNotifyDelegate();

	// 저장해 둔 콤보 입력 한 건을 지운다.
	void ClearPendingCommand();

	// 이번 실행에서 사용한 콤보 상태를 초기값으로 되돌린다.
	void ResetRuntimeState();

	// 현재 Ability가 실행 중일 때만 안전하게 끝낸다.
	void FinishAbility(bool bWasCancelled);

private:
	// 노드와 전환 규칙이 들어 있는 콤보 데이터다.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Combo")
	TObjectPtr<UKZComboDefinitionData> ComboDefinition = nullptr;

	// Ability가 시작할 첫 노드 이름이다.
	UPROPERTY(EditDefaultsOnly, Category = "KZ|Combo")
	FName EntryNodeId = NAME_None;

	// 다음 공격 섹션으로 넘어갈 때 사용할 관성화 시간이다.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "KZ|Combo|Animation",
		meta = (AllowPrivateAccess = "true", ClampMin = "0.0", Units = "s"))
	float ComboTransitionInertializationDuration = 0.08f;

	// 공격을 끊고 이동으로 돌아갈 때 사용할 관성화 시간이다.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "KZ|Combo|Animation",
		meta = (AllowPrivateAccess = "true", ClampMin = "0.0", Units = "s"))
	float LocomotionExitInertializationDuration = 0.24f;

	// 현재 몽타주 재생을 관리하는 Ability Task다.
	UPROPERTY(Transient)
	TObjectPtr<UAbilityTask_PlayMontageAndWait> ActiveMontageTask = nullptr;

	// 노티파이를 연결한 AnimInstance다.
	TWeakObjectPtr<UAnimInstance> BoundAnimInstance;

	// ASC 콤보 명령 연결을 해제할 때 사용하는 번호다.
	FDelegateHandle ComboCommandDelegateHandle;

	// 현재 누르고 있는 공격 명령들이다.
	FGameplayTagContainer HeldCommands;

	// ComboCommit까지 기다리는 입력 한 건이다.
	FGameplayTag PendingCommandTag;

	// 저장된 입력이 누르기인지 떼기인지 나타낸다.
	EKZComboCommandPhase PendingCommandPhase = EKZComboCommandPhase::Begin;

	// 지금 재생 중인 공격 노드 이름이다.
	FName CurrentNodeId = NAME_None;

	// 현재 콤보 입력 구간이다.
	EKZComboWindowPhase ComboWindowPhase = EKZComboWindowPhase::Closed;

	// true면 이동 입력으로 현재 공격을 끝낼 수 있다.
	bool bCanExitToLocomotion = false;
};
