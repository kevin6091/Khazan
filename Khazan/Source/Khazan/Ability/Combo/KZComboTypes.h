#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "KZComboTypes.generated.h"

UENUM(BlueprintType)
enum class EKZComboCommandPhase : uint8
{
	// 버튼을 눌렀다. ASC는 이 명령을 "누르는 중" 목록에 넣는다.
	Begin,
	// 버튼을 정상적으로 뗐다. ASC는 목록에서 뺀 뒤 Release Edge를 바로 검사한다.
	Release,
	// 입력 자체가 취소됐다. 눌림 기록만 지우고 공격 Edge는 실행하지 않는다.
	Cancel,
	// 몽타주가 "이제 다른 Action으로 바꿔도 되는 지점"에 도달했다.
	InputEnd,
	// 몽타주가 최소 차지 성공 지점에 도달했다.
	HoldCommit,
	// 몽타주가 더 기다리지 않고 차지 공격을 내보낼 지점에 도달했다.
	HoldEnd
};

UENUM(BlueprintType)
enum class EKZComboHold : uint8
{
	// 차지 성공 전후를 따지지 않는다.
	Any,
	// HoldCommit 전일 때만 맞는다.
	BeforeCommit,
	// HoldCommit을 지난 뒤에만 맞는다.
	AfterCommit
};

UENUM(BlueprintType)
enum class EKZComboMove : uint8
{
	// 이동 상태를 따지지 않는다.
	Any,
	// 정지 또는 걷기처럼 달리는 상태가 아닐 때 맞는다.
	NonRun,
	// Run 또는 Sprint일 때 맞는다.
	Run
};

// Edge를 찾을 때 사용하는 "명령 종류 + 발생한 순간" 한 건이다.
struct FKZComboCommand
{
	FKZComboCommand(const FGameplayTag& InCommandTag, const EKZComboCommandPhase InPhase)
		: CommandTag(InCommandTag), Phase(InPhase)
	{
	}

	FGameplayTag CommandTag;      // X, Y 같은 논리 공격 명령이다.
	EKZComboCommandPhase Phase;  // 누름, 뗌, InputEnd 같은 발생 시점이다.
};
