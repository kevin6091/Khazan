


#include "Character/Component/KhazanLocomotionComponent.h"

#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "InterchangeResult.h"
#include "Character/KhazanCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"

namespace
{
	// 검증된 두 Gait 중 제한 순위가 더 낮은 쪽을 반환한다.
	// 두 인자는 호출 전에 지원되는 값이어야 한다.
	EKhazanGait GetMoreRestrictiveGait(const EKhazanGait A, const EKhazanGait B)
	{
		const int32 RankA = KhazanLocomotion::GetGaitRestrictionRank(A);

		const int32 RankB = KhazanLocomotion::GetGaitRestrictionRank(B);

		check(RankA != INDEX_NONE && RankB != INDEX_NONE);

		return RankA <= RankB ? A : B;
	}
}

UKhazanLocomotionComponent::UKhazanLocomotionComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UKhazanLocomotionComponent::BeginPlay()
{
	Super::BeginPlay();

	ResolvedPolicy.bMovementAllowedByTags = false;

	UAbilitySystemComponent* ASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetOwner());

	if (!IsValid(ASC))
	{
		UE_LOG(LogDefault,Error,TEXT("%s requires an AbilitySystemComponent for locomotion."),*GetNameSafe(GetOwner()));
		return;
	}

	// Character가 제공하는 ASC를 관측용 weak pointer로 보관한다. ASC 수명은 Character가 소유한다.
	ObservedAbilitySystemComponent = ASC;

	// ASC가 실제로 소유한 tag delegate의 참조를 받는다. 값 복사본에 구독하면 안 된다.
	FOnGameplayEffectTagCountChanged& Event =
		ASC->RegisterGameplayTagEvent(KhazanGameplayTags::Block_Movement_Input, EGameplayTagEventType::NewOrRemoved);

	// Block 태그를 새로 부여하는 코드가 아니라, 태그 경계 변화 callback 한 건을 구독하는 코드다.
	MovementBlockChangedHandle = Event.AddUObject(this,&UKhazanLocomotionComponent::HandleMovementBlockChanged);

	// 구독 전부터 Effect가 적용됐을 수 있으므로 현재 ASC count를 즉시 다시 읽는다.
	RefreshMovementPermission();
}

bool UKhazanLocomotionComponent::InitializeMovementConfig(const FKhazanLocomotionConfig& InConfig)
{
	check(IsInGameThread());

	// 현재 intent token 또는 원인별 Constraint가 하나라도 활성화돼 있으면 기준 Config 교체를 거절한다.
	if (ActiveIntentId.IsValid() || !ActiveConstraints.IsEmpty())
	{
		UE_LOG(LogDefault, Error, TEXT("Cannot replace locomotion config while %s has active runtime owners."),
			*GetNameSafe(GetOwner()));

		return false;
	}

	FString Error;

	// 유한·비음수 수치, 속도 순서와 지원 enum 등 Config의 구조적 계약을 검사한다.
	if (!InConfig.IsValid(Error))
	{
		// 잘못된 입력을 승인된 Config처럼 사용하지 않고 모든 runtime 복사본/cache를 fail closed 상태로 비운다.
		bHasValidMovementConfig = false;
		MovementConfig = FKhazanLocomotionConfig{};
		Intent = FKhazanLocomotionIntent{};
		ResolvedPolicy = FKhazanResolvedMovementPolicy{};

		UE_LOG(LogDefault, Error, TEXT("Invalid locomotion config for %s: %s"),
			*GetNameSafe(GetOwner()), *Error);

		return false;
	}

	// 검증을 통과한 CharacterDefinition 값을 이 Pawn 수명의 runtime Config로 복사한다.
	MovementConfig = InConfig;
	// 아래 Reset 함수가 Config 기본값을 사용할 수 있도록 먼저 유효 상태로 전환한다.
	bHasValidMovementConfig = true;

	// 방향과 세기를 지우고 요청 Gait/회전 모드를 Config 기본값으로 초기화한다.
	ResetIntentToConfigDefaults();
	// 새 Config와 초기 Intent에서 Policy를 계산하고 공통 CMC 설정에 적용한다.
	RebuildAndApplyMovementPolicy();

	return true;
}

void UKhazanLocomotionComponent::ResetIntentToConfigDefaults()
{
	// raw Intent 전체를 구조체 기본값으로 초기화한다.
	// 이 대입으로 이동 방향과 입력 세기도 함께 지워진다.
	Intent = FKhazanLocomotionIntent{};

	// 유효한 CharacterDefinition Config가 준비됐을 때만
	// 캐릭터별 기본 gait와 회전 요청을 적용한다.
	if (bHasValidMovementConfig)
	{
		Intent.RequestedGait = MovementConfig.DefaultRequestedGait;

		Intent.RequestedRotationMode = MovementConfig.DefaultRequestedRotationMode;
	}
}

// IntentHandle 발급
FKhazanLocomotionIntentHandle UKhazanLocomotionComponent::BeginLocomotionIntentSource(UObject* Source, 
	EKhazanLocomotionIntentSource SourceType)
{
	check(IsInGameThread());
	
	// 기본 생성된 Handle은 Owner = null, Id = invalid인 실패 반환값.
	FKhazanLocomotionIntentHandle Handle;
	
	// Config가 준비되지 않았거나, 실제 Source가 InValid거나, SourceType이 None이면 쓰기 권한을 발급하지 않음.
	if (!bHasValidMovementConfig || !IsValid(Source) || SourceType == EKhazanLocomotionIntentSource::None)
	{
		UE_LOG(LogDefault, Error, TEXT("%s could not acquire a locomotion intent source."), 
			*GetNameSafe(GetOwner()));
		
		return Handle;
	}
	
	// 현재 raw Intent를 작성한 실제 원인 Controller의 약한 참조.
	ActiveIntentSource = Source;
	
	// 새 source 세대를 식별하는 GUID를 발급한다.
	// 이전 handle은 이 값과 달라져 즉시 stale 상태가 된다.
	ActiveIntentId = FGuid::NewGuid();
	
	// Player/AI 구분은 진단용으로 따로 기록한다.
	ActiveIntentSourceType = SourceType;
	
	// 새 Controller가 이전 Controller의 방향·세기·gait 요청을 상속하지 않게 한다.
	ResetIntentToConfigDefaults();
	
	// source 존재 여부도 최종 입력 허용 조건이므로 Policy를 다시 계산한다.
	RebuildAndApplyMovementPolicy();
	
	// 이 Handle을 어느 LocomotionComponent가 발급했는지 기록한다.
	Handle.Owner = this;
	
	// 현재 source 세대의 GUID를 Handle에 복사
	Handle.Id = ActiveIntentId;
	
	return Handle;
}

void UKhazanLocomotionComponent::EndLocomotionIntentSource(FKhazanLocomotionIntentHandle& Handle)
{
	check(IsInGameThread());
	
	// 전달된 Handle이 현재 Source의 token이 아니라면
	// 현재 Source는 건드리지 않고 전달된 Handle만 비운다.
	if (!IsActiveLocomotionIntentHandle(Handle))
	{
		Handle.Reset();
		return;
	}
	
	// 현재 Controller의 수명 표식을 먼저 제거
	ActiveIntentSource.Reset();
	ActiveIntentId.Invalidate();
	ActiveIntentSourceType = EKhazanLocomotionIntentSource::None;
	
	// 종료된 Controller의 이동 입력과 요청을 남기지 않는다.
	ResetIntentToConfigDefaults();
	
	// Active Source가 없어진 상태를 최동 Policy에 반영한다.
	RebuildAndApplyMovementPolicy();
	
	// 호출자가 보관하던 권한 증표도 비운다.
	Handle.Reset();
}

bool UKhazanLocomotionComponent::IsActiveLocomotionIntentHandle(const FKhazanLocomotionIntentHandle& Handle) const
{
	check(IsInGameThread());

	return
		Handle.Owner.Get() == this &&
		Handle.Id.IsValid() &&
		Handle.Id == ActiveIntentId &&
		ActiveIntentSource.IsValid();
}

bool UKhazanLocomotionComponent::SetMoveInputWorld(const FKhazanLocomotionIntentHandle& Handle, const FVector& Input)
{
	check(IsInGameThread());

	// 이전 Controller의 callback이나 다른 Pawn의 handle은 거절한다.
	if (!IsActiveLocomotionIntentHandle(Handle))
	{
		return false;
	}

	// 이동 의도는 지면 평면만 사용한다.
	const FVector Input2D(Input.X, Input.Y, 0.f);

	// 대각선 입력의 길이가 1을 넘지 않도록 제한한다.
	Intent.MoveInputWorld = Input2D.GetClampedToMaxSize(1.f);

	// clamp가 끝난 실제 평면 벡터의 크기를 0~1 입력 세기로 저장한다.
	Intent.InputAmount = Intent.MoveInputWorld.Size2D();

	return true;
}

bool UKhazanLocomotionComponent::ClearMoveInput(const FKhazanLocomotionIntentHandle& Handle)
{
	check(IsInGameThread());

	if (!IsActiveLocomotionIntentHandle(Handle))
	{
		return false;
	}

	// 방향과 입력 세기만 지운다.
	// TargetGait와 RequestedRotationMode는 이 함수의 책임이 아니다.
	Intent.MoveInputWorld = FVector::ZeroVector;
	Intent.InputAmount = 0.f;

	return true;
}

bool UKhazanLocomotionComponent::SetRequestedGait(const FKhazanLocomotionIntentHandle& Handle, EKhazanGait Gait)
{
	check(IsInGameThread());

	// 현재 token과 지원하는 Gait 값이 모두 유효해야 한다.
	if (!IsActiveLocomotionIntentHandle(Handle) ||
		!KhazanLocomotion::IsSupportedGait(Gait))
	{
		return false;
	}

	// 이미 같은 요청이면 성공으로 처리하되 불필요한 Policy 재계산은 생략한다.
	if (Intent.RequestedGait == Gait)
	{
		return true;
	}

	// 이것은 Controller가 원하는 gait다.
	// Constraint가 허용하는 최종 gait와는 다르다.
	Intent.RequestedGait = Gait;

	// TargetGait가 달라지면 ResolvedGait와 MaxWalkSpeed가 달라질 수 있다.
	RebuildAndApplyMovementPolicy();

	return true;
}

bool UKhazanLocomotionComponent::ResetRequestedGaitToDefault(const FKhazanLocomotionIntentHandle& Handle)
{
	check(IsInGameThread());

	if (!IsActiveLocomotionIntentHandle(Handle))
	{
		return false;
	}

	// 이미 CharacterDefinition의 기본 요청이면 성공으로 처리하고
	// 같은 Policy를 다시 계산하지 않는다.
	if (Intent.RequestedGait == MovementConfig.DefaultRequestedGait)
	{
		return true;
	}

	// 방향, 세기, 회전 요청은 보존하고 TargetGait 하나만 복구한다.
	Intent.RequestedGait = MovementConfig.DefaultRequestedGait;

	// gait 요청이 달라졌으므로 최종 gait와 속도를 다시 계산한다.
	RebuildAndApplyMovementPolicy();

	return true;
}

bool UKhazanLocomotionComponent::SetRequestedRotationMode(const FKhazanLocomotionIntentHandle& Handle, EKhazanRotationMode Mode)
{
	check(IsInGameThread());

	// 현재 token과 지원하는 회전 enum이 모두 유효해야 한다.
	if (!IsActiveLocomotionIntentHandle(Handle) ||
		!KhazanLocomotion::IsSupportedRotationMode(Mode))
	{
		return false;
	}

	// 이미 같은 요청이면 성공이며 재계산은 필요 없다.
	if (Intent.RequestedRotationMode == Mode)
	{
		return true;
	}

	// 이것은 Controller의 기본 회전 요청이다.
	// Ability의 강제 회전은 이후 Constraint override로 처리한다.
	Intent.RequestedRotationMode = Mode;

	// 회전 요청이 바뀌었으므로 최종 회전 Policy를 다시 계산한다.
	RebuildAndApplyMovementPolicy();

	return true;
}

FKhazanMovementConstraintHandle UKhazanLocomotionComponent::AcquireMovementConstraint(UObject* Source,
	const FKhazanMovementConstraint& Constraint)
{
	check(IsInGameThread());
	
	FKhazanMovementConstraintHandle Handle;
	
	const bool bIsGaitSupported = KhazanLocomotion::IsSupportedGait(Constraint.MaxAllowedGait);
	
	// 회전 override를 사용하지 않으면 저장된 RotationModeOverride 값은 소비하지 않는다.
	// override를 사용할 때만 해당 enum이 지원되는지 확인한다.
	const bool bIsRotationModeSupported = !Constraint.bOverrideRotationMode ||
		KhazanLocomotion::IsSupportedRotationMode(Constraint.RotationModeOverride);
	
	// Config, Source, Constraint가 모두 유효할 때만 새 제약을 등록한다.
	if (!bHasValidMovementConfig || !IsValid(Source) || !bIsGaitSupported || !bIsRotationModeSupported)
	{
		UE_LOG(LogDefault, Error, TEXT("Failed to Acquire Movement Constraint. Object : %s, Source : %s."),
		*GetNameSafe(GetOwner()), *GetNameSafe(Source));

		return Handle;
	}
	
	// 다음 증가에서 uint64가 0으로 wrap되는 것을 막는다.
	if (NextConstraintAcquireOrder == MAX_uint64)
	{
		UE_LOG(LogDefault, Error, TEXT("%s constraint acquire order overflow."),
			*GetNameSafe(GetOwner()));

		return Handle;
	}
	
	// 현재 ActiveConstraints와 충돌하지 않는 유효한 GUID를 만든다.
	FGuid NewId;
	
	do
	{
		NewId = FGuid::NewGuid();
	}
	while (!NewId.IsValid() || ActiveConstraints.Contains(NewId));
	
	// 외부에서 전달받은 제약과 원인 정보를 내부 runtime record로 복사한다.
	FActiveMovementConstraint ActiveConstraint;
	ActiveConstraint.Source = Source;
	ActiveConstraint.Constraint = Constraint;
	ActiveConstraint.AcquireOrder = ++NextConstraintAcquireOrder;
	
	// 새 GUID를 해제 키로 사용해 활성 제약 장부에 등록한다.
	// ActiveConstraint를 Move했으므로 지역 ActiveConstraint는 사용X
	ActiveConstraints.Add(NewId, MoveTemp(ActiveConstraint));

	// 호출자에게 이 Component와 새 GUID를 담은 해제 Handle을 발급한다.
	// Handle을 갖고있다가 같은 Component의 ReleaseMovementConstraint()에 전달해야함.
	Handle.Owner = this;
	Handle.Id = NewId;

	// 새 원인이 추가됐으므로 모든 활성 제약에서 Policy를 다시 계산한다.
	RebuildAndApplyMovementPolicy();

	return Handle;
}

bool UKhazanLocomotionComponent::ReleaseMovementConstraint(FKhazanMovementConstraintHandle& Handle)
{
	check(IsInGameThread());
	
	// 다른 Component가 발급했거나 식별자가 없는 handle은 처리하지 않는다.
	if (Handle.Owner.Get() != this || !Handle.Id.IsValid())
	{
		return false;
	}
	
	// 이 Handle의 GUID와 일치하는 제약 한 건만 Map에서 제거한다.
	// 0: 이미 해제됐거나 orphan 정리로 제거됨. 1: 정확히 한 항목 제거
	const int32 RemovedCount = ActiveConstraints.Remove(Handle.Id);
	
	// 같은 Component의 Handle이지만 이미 제거된 항목이면 
	// 현재 장부는 건드리지 않고 호출자의 stale Handle만 비운다.
	if (RemovedCount != 1)
	{
		Handle.Reset();
		return false;
	}
	
	// 정상적으로 제거가 됐으니 Handle을 비운다.
	Handle.Reset();
	
	// 제거된 원인을 제외한 나머지 Active Constraint로 Policy를 다시 계산
	RebuildAndApplyMovementPolicy();
	
	return true;
}

void UKhazanLocomotionComponent::RebuildAndApplyMovementPolicy()
{
	check(IsInGameThread());
	
	for (auto It = ActiveConstraints.CreateIterator(); It; ++It)
	{
		if (!It.Value().Source.IsValid())
		{
			UE_LOG(LogDefault, Warning, TEXT("Removing orphaned movement constraint %s from %s."),
			*It.Value().Constraint.DebugName.ToString(), *GetNameSafe(GetOwner()));
			
			It.RemoveCurrent();
		}
	}
	
	FKhazanResolvedMovementPolicy NewPolicy;
	NewPolicy.bMovementAllowedByTags = ResolvedPolicy.bMovementAllowedByTags;
	
	if (!bHasValidMovementConfig)
	{
		ResolvedPolicy = NewPolicy;
		return;
	}
	
	EKhazanGait MaxAllowedGait = MovementConfig.DefaultMaxAllowedGait;
	EKhazanRotationMode ResolvedRotationMode = Intent.RequestedRotationMode;
	
	bool bHasRotationModeOverride = false;
	int32 WinningRotationModeOverridePriority = MIN_int32;
	uint64 WinningAcquireOrder = 0;
	
	// 등록된 Constraint들을 모두 순회하며 Gait, RotationMode를 우선순위와 정책에 따라 결정한다.
	for (const TPair<FGuid, FActiveMovementConstraint>& Pair : ActiveConstraints)
	{
		// Section Gait Constraint
		const FActiveMovementConstraint& ActiveConstraint = Pair.Value;
		const FKhazanMovementConstraint& Constraint = ActiveConstraint.Constraint;

		MaxAllowedGait = GetMoreRestrictiveGait(MaxAllowedGait, Constraint.MaxAllowedGait);

		// Section RotationMode Constraint
		if (!Constraint.bOverrideRotationMode)
		{
			continue;
		}

		// 현재 Constraint의 RotationMode 우선순위가 기존 보다 높다.
		const bool bNoWinnerOrHigherPriority = 
			!bHasRotationModeOverride ||
			(Constraint.RotationModeOverridePriority > WinningRotationModeOverridePriority);

		// 현재 Constraint의 RotationMode 우선순위가 기존이랑 같다면 AcquireOrder를 비교해서 더 높은지 확인.
		const bool bSamePriorityAndLaterAcquireOrder =
			bHasRotationModeOverride &&
			(Constraint.RotationModeOverridePriority == WinningRotationModeOverridePriority) &&
			(ActiveConstraint.AcquireOrder > WinningAcquireOrder);

		// 현재 Constraint의 RotationMode 우선순위가 채택됐다면.
		// 승자의 우선순위와 Order를 저장. RotationMode도 다시 Override한다.
		if (bNoWinnerOrHigherPriority || bSamePriorityAndLaterAcquireOrder)
		{
			bHasRotationModeOverride = true;
			WinningRotationModeOverridePriority = Constraint.RotationModeOverridePriority;
			WinningAcquireOrder = ActiveConstraint.AcquireOrder;
			ResolvedRotationMode = Constraint.RotationModeOverride;
		}
	}
	
	// 순회를 모두 했으면 NewPolicy에 계산 정보를 복사
	NewPolicy.MaxAllowedGait = MaxAllowedGait;

	NewPolicy.ResolvedGait = GetMoreRestrictiveGait(Intent.RequestedGait, MaxAllowedGait);

	NewPolicy.ResolvedRotationMode = ResolvedRotationMode;

	NewPolicy.MaxWalkSpeed = MovementConfig.GetSpeedForGait(NewPolicy.ResolvedGait);

	// 멤버 Policy에 계산완료된 NewPolicy를 값복사.
	ResolvedPolicy = NewPolicy;

	// 새로운 Policy가 탄생했으니 CMC에 실제 적용.
	ApplyMovementPolicyToCharacter();
}

void UKhazanLocomotionComponent::ApplyMovementPolicyToCharacter()
{
	check(IsInGameThread());
	
	// 이 Component가 속한 Khazan Character와 그 CMC를 찾는다.
	AKhazanCharacter* Character = Cast<AKhazanCharacter>(GetOwner());
	
	UCharacterMovementComponent* CMC = Character ? Character->GetCharacterMovement() : nullptr;
	
	// 잘못된 Owner, 없는 CMC, 유효하지 않은 Config에서는
	// Character와 CMC 상태를 부분적으로 변경하지 않는다.
	if (!Character || !CMC || !bHasValidMovementConfig)
	{
		return;
	}
	
	// CharacterDefinition에서 검증·복사한 공통 이동 설정을 CMC에 적용한다.
	CMC->MinAnalogWalkSpeed = MovementConfig.MinAnalogWalkSpeed;
	CMC->MaxAcceleration = MovementConfig.MaxAcceleration;
	// 걷기 이동 모드에서 가속 입력이 없을 때 감속 성분
	CMC->BrakingDecelerationWalking = MovementConfig.BrakingDecelerationWalking;
	// 회전 속도 deg/s
	CMC->RotationRate = MovementConfig.RotationRate;
	
	// 요청 Gait와 모든 Gait Constraint를 해결해 얻은 최종 속도를 적용한다.
	CMC->MaxWalkSpeed = ResolvedPolicy.MaxWalkSpeed;
	
	// Controller 회전을 Character가 직접 복사하지 않게 한다.
	// 아래 switch에서 선택한 CMC 회전 경로와 RotationRate가 회전을 담당한다.
	Character->bUseControllerRotationPitch = false;
	Character->bUseControllerRotationYaw = false;
	Character->bUseControllerRotationRoll = false;

	// 회전 방식 설정
	switch (ResolvedPolicy.ResolvedRotationMode)
	{
	case EKhazanRotationMode::VelocityDirection:
		CMC->bOrientRotationToMovement = true;
		CMC->bUseControllerDesiredRotation = false;
		break;
	case EKhazanRotationMode::LookingDirection:
	case EKhazanRotationMode::LockOn:
		CMC->bOrientRotationToMovement = false;
		CMC->bUseControllerDesiredRotation = true;
		break;

	default:
		//잘못된 enum이 실제 적용 경계까지 들어왔음을 알림.
		checkNoEntry();
		CMC->bOrientRotationToMovement = true;
		CMC->bUseControllerDesiredRotation = false;
		break;
	}
}

void UKhazanLocomotionComponent::HandleMovementBlockChanged(const FGameplayTag Tag, int32 NewCount)
{
	// 인자를 사용하지 않음.
	// 현재 ASC의 실제 tag count를 다시 읽는 공통 경로를 호출한다.
	(void)Tag;
	(void)NewCount;
	
	RefreshMovementPermission();
}

void UKhazanLocomotionComponent::RefreshMovementPermission()
{
	check(IsInGameThread());

	// BeginPlay에서 관측 대상으로 저장한 ASC를 읽는다.
	const UAbilitySystemComponent* ASC = ObservedAbilitySystemComponent.Get();

	// 갱신 전 ASC tag projection을 보관한다.
	// 이 값은 모든 최종 gate 가 아니라 Block.Movement.Input tag 관점의 허용 여부이다.
	const bool bWasMovementAllowedByTags = ResolvedPolicy.bMovementAllowedByTags;
	
	// ASC가 살아있고 Block.Movement.Input count가 0일때만 tag관점 이동 입력이 허용된다.
	// ASC가 보유한 해당 tag의 현재 count를 조회한다.
	const bool bIsMovementAllowedByTags = ASC && ASC->GetTagCount(KhazanGameplayTags::Block_Movement_Input) == 0;
	
	// 현재 ASC tag 상태를 Resolved Policy의 읽기용 projection에 기록한다.
	ResolvedPolicy.bMovementAllowedByTags = bIsMovementAllowedByTags;
	
	if (!bIsMovementAllowedByTags)
	{
		if (APawn* Pawn = Cast<APawn>(GetOwner()))
		{
			// Block이 활성화되기 전에 Pawn에 누적됐지만
			// 아직 CMC가 소비하지 않은 이동 입력을 제거한다.
			Pawn->ConsumeMovementInputVector();
		}
	}
	
	// tag projection을 보존하면서 나머지 gait·rotation·speed Policy를
	// 현재 Config, Intent, Constraint로 다시 완성하고 CMC에 적용한다.
	RebuildAndApplyMovementPolicy();
	
	// tag projection의 허용 경계가 실제로 바뀌었을 때만 알린다.
	if (bWasMovementAllowedByTags != bIsMovementAllowedByTags)
	{
		// payload는 tag bool 하나가 아니라 Config, ASC, source, Pawn의
		// 모든 gate를 합친 현재 최종 이동 입력 허용 결과다.
		MovementInputPermissionChanged.Broadcast(IsMovementInputAllowed());
	}
}

bool UKhazanLocomotionComponent::IsMovementInputAllowed() const
{
	check(IsInGameThread());

	const APawn* Pawn = Cast<APawn>(GetOwner());

	return 
		bHasValidMovementConfig &&
		ObservedAbilitySystemComponent.IsValid() &&
		ResolvedPolicy.bMovementAllowedByTags &&
		ActiveIntentSource.IsValid() &&
		ActiveIntentId.IsValid() &&
		Pawn &&
		!Pawn->IsMoveInputIgnored();
}

void UKhazanLocomotionComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// BeginPlay에서 등록한 ASC gameplay tag callback을 먼저 해제한다.
	if (UAbilitySystemComponent* ASC = ObservedAbilitySystemComponent.Get())
	{
		if (MovementBlockChangedHandle.IsValid())
		{
			ASC->UnregisterGameplayTagEvent(
				MovementBlockChangedHandle,
				KhazanGameplayTags::Block_Movement_Input,
				EGameplayTagEventType::NewOrRemoved);
		}
	}

	// 외부 시스템에 등록한 delegate 영수증과
	// 이 Component의 permission listener들을 정리한다.
	MovementBlockChangedHandle.Reset();
	MovementInputPermissionChanged.Clear();
	ObservedAbilitySystemComponent.Reset();

	// 현재 intent source와 그 세대를 종료한다.
	// 외부에 남은 과거 intent Handle은 이후 현재 Handle로 인정되지 않는다.
	ActiveIntentSource.Reset();
	ActiveIntentId.Invalidate();
	ActiveIntentSourceType = EKhazanLocomotionIntentSource::None;

	// 모든 활성 Constraint 장부와 획득 순번을 제거한다.
	// 외부에 남은 Constraint Handle은 Component 종료 후 stale이 된다.
	ActiveConstraints.Empty();
	NextConstraintAcquireOrder = 0;

	// Config 승인 상태, runtime 복사본, raw Intent와
	// 파생 Policy를 모두 기본 상태로 되돌린다.
	bHasValidMovementConfig = false;
	MovementConfig = FKhazanLocomotionConfig{};
	Intent = FKhazanLocomotionIntent{};
	ResolvedPolicy = FKhazanResolvedMovementPolicy{};

	// 이 Component가 소유한 callback과 runtime 상태를 정리한 뒤
	// 부모 UActorComponent의 종료 처리를 마지막에 한 번 호출한다.
	Super::EndPlay(EndPlayReason);
}
