

#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "Delegates/Delegate.h"
#include "KhazanLocomotionComponent.generated.h"

class UAbilitySystemComponent;
class UKhazanLocomotionComponent;

/**
 * 현재 Pawn의 원시 이동 의도를 쓸 수 있는 C++ 전용 권한 증표다.
 * Owner는 발급한 LocomotionComponent이고, Id는 그 컴포넌트의 현재 intent source를 식별한다.
 * 한 LocomotionComponent에는 동시에 하나의 intent source만 활성화된다.
 */
struct KHAZAN_API FKhazanLocomotionIntentHandle
{
public:
	// 발급자가 아직 살아 있고 식별자가 채워졌는지만 검사한다.
	// 현재 활성 token인지 여부는 IsMoveIntentHandleActive()로 검사한다.
	bool IsValid() const
	{
		return Owner.IsValid() && Id.IsValid();
	}

	// 이 handle 값만 비운다. 활성 intent source를 종료하려면 EndMoveIntentSource()를 호출해야 한다.
	void Reset()
	{
		Owner.Reset();
		Id.Invalidate();
	}

private:
	// 외부 호출자가 Owner와 Id를 임의로 만들지 못하게 하고 발급자인 Component만 접근한다.
	friend class UKhazanLocomotionComponent;

	// handle을 발급하고 활성 여부를 판정하는 Component의 약한 참조다. Character의 ASC Owner와는 무관하다.
	TWeakObjectPtr<UKhazanLocomotionComponent> Owner;
	// BeginMoveIntentSource()가 발급한 세대 식별자다. 새 source가 시작되면 이전 Id는 stale이 된다.
	FGuid Id;
};

/**
 * 활성 이동 제약 한 건을 다시 찾아 개별 해제하기 위한 영수증이다.
 * 여러 제약이 동시에 존재할 수 있으며, 각 acquire 호출은 서로 다른 Id를 받는다.
 * Blueprint Ability와 시험 Probe도 보관할 수 있도록 BlueprintType USTRUCT로 선언한다.
 */
USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanMovementConstraintHandle
{
	GENERATED_BODY()

public:
	// 발급자가 살아 있고 식별자가 채워졌는지 검사한다. Id가 현재 map에 남아 있는지는 Release에서 확인한다.
	bool IsValid() const
	{
		return Owner.IsValid() && Id.IsValid();
	}

	// 이 handle 값만 비운다. 실제 제약을 제거하려면 ReleaseMovementConstraint()를 호출해야 한다.
	void Reset()
	{
		Owner.Reset();
		Id.Invalidate();
	}

private:
	// 발급자인 Component만 private 영수증 값을 채우고 검사할 수 있다.
	friend class UKhazanLocomotionComponent;

	// 이 제약을 등록한 장부의 소유자다. 제약을 요청한 Source와는 다른 개념이다.
	UPROPERTY(Transient)
	TWeakObjectPtr<UKhazanLocomotionComponent> Owner;

	// ActiveConstraints map에서 제약 한 건을 찾는 키다.
	UPROPERTY(Transient)
	FGuid Id;
};

// ASC Block 태그의 허용 경계가 바뀔 때 다시 계산한 입력 허용값을 전달하는 native 이벤트 타입이다.
DECLARE_MULTICAST_DELEGATE_OneParam(FKhazanMovementInputPermissionChanged, bool /* bMovementAllowed */);

// Tick 없이 config, intent, constraint, tag 변화에 반응해 이동 정책을 계산하는 공통 컴포넌트다.
UCLASS(ClassGroup = (Khazan), meta = (BlueprintSpawnableComponent))
class KHAZAN_API UKhazanLocomotionComponent : public UActorComponent
{
	GENERATED_BODY()
	
public:
	UKhazanLocomotionComponent();

	// CharacterDefinition에서 받은 설정을 검증하고 이 Pawn 수명의 런타임 복사본으로 보관한다.
	// 활성 intent source나 constraint가 존재하는 동안에는 기준 설정 교체를 거절한다.
	bool InitializeMovementConfig(const FKhazanLocomotionConfig& InConfig);

	// 현재 Controller 한 명을 Source로 등록하고 원시 Intent 작성 권한을 발급한다.
	// SourceType은 Player/AI 진단 분류이고, 실제 권한은 반환된 handle이 나타낸다.
	// 새 source를 시작하면 기존 token은 stale이 되고 Intent는 Config 기본값으로 Reset된다.
	FKhazanLocomotionIntentHandle BeginLocomotionIntentSource(UObject* Source, EKhazanLocomotionIntentSource SourceType);

	// 전달된 handle이 현재 source의 token일 때만 source와 Id를 종료하고 Intent를 기본값으로 Reset한다.
	// Player에서는 Pawn 입력 어댑터가, AI에서는 AIController가 자신의 handle을 전달한다.
	void EndLocomotionIntentSource(FKhazanLocomotionIntentHandle& Handle);

	// ItentHandle이 현재 활성화된 Handle인지 확인
	bool IsActiveLocomotionIntentHandle(const FKhazanLocomotionIntentHandle& Handle) const;
	
	// 유효한 token을 가진 Player 입력 어댑터 또는 AI 이동 경로가 월드 평면 방향과 세기를 기록한다.
	// 이동 허용 여부와 무관하게 raw intent를 보존하며, stale handle이면 false를 반환한다.
	bool SetMoveInputWorld(const FKhazanLocomotionIntentHandle& Handle, const FVector& Input);

	// 실제 입력 Released, 경로 종료, UnPossess에서 raw 방향과 세기만 0으로 만든다.
	bool ClearMoveInput(const FKhazanLocomotionIntentHandle& Handle);

	// 현재 source가 원하는 Walk/Run/Sprint를 기록하고 최종 Policy를 다시 계산한다.
	bool SetRequestedGait(const FKhazanLocomotionIntentHandle& Handle, EKhazanGait Gait);

	// source의 요청 gait를 CharacterDefinition의 DefaultRequestedGait로 되돌리고 Policy를 다시 계산한다.
	bool ResetRequestedGaitToDefault(const FKhazanLocomotionIntentHandle& Handle);

	// Controller가 원하는 회전 모드를 기록한다. Ability 등이 회전을 강제할 때는 Constraint의 override를 사용한다.
	bool SetRequestedRotationMode(const FKhazanLocomotionIntentHandle& Handle, EKhazanRotationMode Mode);

	// Source 하나가 기여하는 제약을 ActiveConstraints에 저장, 새 GUID로 등록하고 Policy를 다시 계산한다.
	// Source는 진단과 orphan 방어용 weak identity이며, 반환 handle의 Id가 실제 개별 해제 키다.
	UFUNCTION(BlueprintCallable, Category = "Khazan|Locomotion")
	FKhazanMovementConstraintHandle AcquireMovementConstraint(UObject* Source, const FKhazanMovementConstraint& Constraint);

	// 이 Component가 발급한 GUID 한 건만 제거하고 남은 모든 원인으로 Policy를 다시 계산한다.
	// 제약을 실제로 제거했거나 같은 장부에서 이미 사라진 Id임을 확인하면 전달받은 handle도 Reset한다.
	// 다른 Component가 발급한 handle은 건드리지 않고 false를 반환한다.
	UFUNCTION(BlueprintCallable, Category = "Khazan|Locomotion")
	bool ReleaseMovementConstraint(UPARAM(ref) FKhazanMovementConstraintHandle& Handle);

	// Config, ASC tag projection, 현재 intent source, Pawn의 엔진 입력 차단을 합친 최종 출력 gate다.
	// Game Thread에서 Player AddMovementInput과 CMC, AI 경로가 사용한다.
	bool IsMovementInputAllowed() const;

	// C++ Game Thread에서 즉시 읽기 위한 raw Intent의 const 참조다. Anim worker에 보관하지 않는다.
	const FKhazanLocomotionIntent& GetLocomotionIntent() const
	{
		return Intent;
	}

	// C++ Game Thread에서 즉시 읽기 위한 파생 Policy의 const 참조다. 외부에서 수정할 수 없다.
	const FKhazanResolvedMovementPolicy& GetResolvedMovementPolicy() const
	{
		return ResolvedPolicy;
	}

	// Blueprint/Probe가 원본을 수정하지 않고 관측하도록 raw Intent 복사본을 반환한다.
	UFUNCTION(BlueprintPure, Category = "Khazan|Locomotion")
	FKhazanLocomotionIntent GetLocomotionIntentSnapshot() const
	{
		return Intent;
	}

	// Blueprint/Probe가 현재 해결 결과를 관측하도록 ResolvedPolicy 복사본을 반환한다.
	UFUNCTION(BlueprintPure, Category = "Khazan|Locomotion")
	FKhazanResolvedMovementPolicy GetResolvedMovementPolicySnapshot() const
	{
		return ResolvedPolicy;
	}

	// 기존 C++ 소비자를 위한 편의 조회다. 별도 계산 없이 Policy에 저장된 최종 gait를 반환한다.
	EKhazanGait GetResolvedGait() const
	{
		return ResolvedPolicy.ResolvedGait;
	}

	// native 구독자가 callback을 등록·해제할 수 있도록 이 Component가 소유한 delegate를 반환한다.
	FKhazanMovementInputPermissionChanged& OnMovementInputPermissionChanged()
	{
		return MovementInputPermissionChanged;
	}

protected:
	// Character의 ASC를 찾아 Block.Movement.Input tag 이벤트를 구독하고 현재 count를 즉시 동기화한다.
	virtual void BeginPlay() override;

	// 외부 delegate 구독을 먼저 해제한 뒤 이 Component가 소유한 runtime 상태와 cache를 정리한다.
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	// ActiveConstraints map에 저장되는 제약 한 건의 내부 runtime record다.
	struct FActiveMovementConstraint
	{
		// 제약을 만든 원인의 약한 참조다. 진단과 소멸한 source의 orphan 제거에 사용한다.
		TWeakObjectPtr<UObject> Source;
		// 요청 시 전달받은 제약 값의 독립 복사본이다.
		FKhazanMovementConstraint Constraint;
		// 회전 priority가 같을 때 나중에 획득한 제약을 고르기 위한 Pawn 수명 내 순서다.
		uint64 AcquireOrder = 0;
	};
	
	// raw Intent 전체를 초기화하고, 유효한 Config가 있으면 기본 gait와 회전 요청을 다시 적용한다.
	void ResetIntentToConfigDefaults();
	// Config, Intent, 활성 Constraint, tag projection에서 새 Policy를 계산하고 CMC에 적용한다.
	void RebuildAndApplyMovementPolicy();
	// 해결된 속도·가감속·회전 정책을 CharacterMovementComponent에 쓰는 유일한 공통 경로다.
	void ApplyMovementPolicyToCharacter();
	// 현재 ASC tag count를 다시 읽어 허용 projection을 갱신하고 경계 변화 이벤트를 방송한다.
	void RefreshMovementPermission();
	// ASC의 Block.Movement.Input 0↔비0 알림을 받아 RefreshMovementPermission()으로 전달한다.
	void HandleMovementBlockChanged(const FGameplayTag Tag, int32 NewCount);

private:
	// 현재 Character 소유 ASC의 관측용 약한 참조다. Component가 ASC 수명을 연장하지 않는다.
	UPROPERTY(Transient)
	TWeakObjectPtr<UAbilitySystemComponent> ObservedAbilitySystemComponent;

	// 이 Component가 ASC tag delegate에 등록한 callback 한 건의 해제 영수증이다.
	FDelegateHandle MovementBlockChangedHandle;

	// ASC Block 태그의 0↔비0 경계에서 다시 계산한 입력 허용값을 방송한다.
	// AIController가 자신의 구독 handle을 보관한다.
	FKhazanMovementInputPermissionChanged MovementInputPermissionChanged;

	// CharacterDefinition에서 검증 후 복사한 이 Pawn의 읽기 전용 이동 기준값이다.
	FKhazanLocomotionConfig MovementConfig;

	// InitializeMovementConfig()가 성공했는지 나타내며, false일 때 write/출력을 fail closed로 거절한다.
	bool bHasValidMovementConfig = false;

	// 현재 source의 허용 전 원시 방향·세기·gait·회전 요청이다. 유효한 intent token만 수정한다.
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Locomotion", meta = (AllowPrivateAccess = "true"))
	FKhazanLocomotionIntent Intent;

	// Config, Intent, Constraints, ASC tag를 합친 파생 cache다.
	// RefreshMovementPermission()이 tag projection을 작성하고,
	// RebuildAndApplyMovementPolicy()가 이를 보존하며 gait·rotation·speed 결과를 작성한다.
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Locomotion", meta = (AllowPrivateAccess = "true"))
	FKhazanResolvedMovementPolicy ResolvedPolicy;

	// 현재 intent 권한의 실제 원인 Controller다. weak이므로 Controller 수명을 연장하지 않는다.
	TWeakObjectPtr<UObject> ActiveIntentSource;
	// 현재 intent 세대의 GUID다. 새 source 발급과 종료로 과거 handle을 무효화한다.
	FGuid ActiveIntentId;

	// 현재 source가 Player인지 AI인지 표시하는 진단용 분류다. 권한 검사의 원본은 아니다.
	UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion", meta = (AllowPrivateAccess = "true"))
	EKhazanLocomotionIntentSource ActiveIntentSourceType = EKhazanLocomotionIntentSource::None;

	// GUID별 활성 제약 장부다. 각 acquire 호출자가 보관한 handle 한 건만 독립적으로 해제한다.
	TMap<FGuid, FActiveMovementConstraint> ActiveConstraints;
	// 같은 rotation priority에서 최신 acquire를 선택하기 위한 단조 증가 순서다.
	uint64 NextConstraintAcquireOrder = 0;
};
