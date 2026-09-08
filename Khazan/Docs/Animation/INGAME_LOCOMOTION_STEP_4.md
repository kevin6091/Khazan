# InGame 로코모션 4단계: Stop 선택과 발 동기화

## 2026-09-07 진행 기준

이 문서는 사용자가 직접 적용할 구현 가이드다. 어시스턴트는 C++/ABP/시퀀스를 변경하지 않았다. 코드와 현재 에디터 설정/기존 로그를 읽기 전용으로 확인했으며 새 빌드, BP Compile, PIE 재현은 실행하지 않았다.

런타임 Animation Sequence는 `/Game/_Art/Kazan/Animation/InGame` 아래만 사용한다. Walk/Run Start는 없고 Sprint에만 Start를 넣는다. 이번 단계는 Stop이며 SprintStart와 Turn은 다음 단계다.

## 1. 현재 코드에서 확인한 원인

`bUseRunStop`은 현재 속도 분류가 아니라, 입력 해제 edge와 `bIsStopping`이 동시에 참일 때만 저장하는 마지막 Stop 선택값이다. 조건 밖의 매 프레임 로그는 현재 속도와 과거 선택값을 함께 출력한다.

현재 ABP CDO의 RunStopSelectionSpeed는 315, RunEnterSpeed는 220, RunExitSpeed는 190이다. 기존 로그의 필터된 순서에서 600/false 다음 504/true가 관찰되었고, 이후 0/true가 유지된다. 로그에는 인스턴스 식별자나 입력 해제 여부가 없어 개별 실패의 release 프레임/호출 순서를 확정하지 않는다. 동일 인스턴스의 동일 실행에서 실제 비교값이 470과 315라면 비교 결과는 참이다.

실제 설계 취약점은 별도다.

- 입력 해제 snapshot은 이미 감속된 속도일 수 있다.
- 입력 해제 snapshot에서 속도가 3 이하이면 bIsStopping=false라 선택하지 않는다.
- bIsStopping은 여러 프레임 유지되는 물리 관측이고, 선택 조건은 한 프레임 edge라 둘의 수명이 다르다.
- Run loop는 220부터 선택되는데 Stop은 315부터 선택되어, Run loop에서 Walk Stop으로 연결될 수 있다.
- bool 하나는 Walk/Run/Sprint 세 가지 선택을 표현하지 못한다.
- 입력을 다시 넣으면 이전 Stop 선택값이 남는 것은 정상이다. 그 값은 다음 Stop에서 덮어쓴다.

정수 출력 캐스팅은 소수점만 버리며 위 비교식에는 영향을 주지 않는다. 진단에는 %.2f와 명시적인 bool 정수 출력, release 조건을 함께 사용한다. 매 프레임 로그는 검증 후 제거한다.

## 2. 데이터의 의미와 소유 클래스

| 데이터 | 의미 | 소유 이유 |
| --- | --- | --- |
| ResolvedGait | 요청과 허용 상한을 반영한 gameplay gait | LocomotionComponent가 결정하고 AnimInstance가 snapshot으로 읽는다. |
| LocomotionGait | 이동 loop를 고르기 위한 시각적 gait | AnimInstance가 실제 속도와 히스테리시스를 해석한다. 실제 블렌드의 최대 가중치 gait라는 뜻은 아니다. |
| StopGait | 이번 Stop 직전에 선택했던 LocomotionGait | 원샷 도중 변경하면 안 되는 애니메이션 진입 데이터다. |
| StopEntrySpeed | 입력 상실 직전/현재 snapshot 속도 중 큰 값 | 이미 감속된 한 프레임 때문에 진입 정보를 잃지 않게 한다. 정확한 입력 이벤트 시각의 물리 속도를 재구성하는 값은 아니다. |
| StopEntryFoot | 이번 Stop의 접촉 기준발 선택 키 | 발 위상은 조작 정책이 아니라 애니메이션 데이터다. 실제 접지 센서값은 아니다. |
| bShouldEnterStop | 이번 애니메이션 update의 Stop 진입 요청 | 물리적 감속과 원샷 진입을 분리한다. 재생 중 플래그가 아니다. |
| bIsStopping | 지상, 유효 입력 없음, 잔여 속도 있음 | 독립적인 물리 관측 bool로 남긴다. |
| PreviousGroundSpeed / PreviousLocomotionGait | 직전 유효 애니메이션 update의 관측/선택 | AnimInstance 내부 이력으로만 필요하다. |
| bHadGroundedMovementInput / bWasMoving | 직전 update의 지상 입력/이동 여부 | release edge 및 한 프레임에 정지하는 경우를 판정한다. |

Player/Controller에는 이번에 함수를 추가하지 않는다. 게임플레이가 애니메이션 재생 상태를 소유하거나 AnyThread가 외부 Actor/컴포넌트를 다시 읽지 않게 한다. 재생 시간, 종료, 블렌드, Sync Group의 진행은 ABP/엔진이 소유한다.

배타적인 gait/발 선택은 enum, 서로 동시에 성립할 수 있는 사실과 전이 predicate는 bool을 사용한다. `bShouldWalkRun`과 현재 사용자 이름인 `bShouldSprint`는 기존 그래프의 전이 조건으로 유지한다. bUseRun/bUseSprint/bUseRunStop처럼 gait를 중복 표현하는 멤버는 아래 enum 연결이 끝나면 제거한다.

## 3. 준비할 파일

- 신규: `Source/Khazan/Animation/KhazanAnimationTypes.h` — 애니메이션 전용 발 선택 타입.
- 변경 안내: `KhazanAnimInstance.h/.cpp` — 파생 gait, Stop 진입 데이터와 이력.
- 에디터: `ABP_Player`와 InGame Stop 여섯 후보.
- 기존 `EKhazanGait`는 `KhazanLocomotionType.h`의 BlueprintType enum을 재사용한다. 같은 enum을 다시 만들거나 순서를 변경하지 않는다.

### 3-1. KhazanAnimationTypes.h

```cpp
#pragma once

#include "CoreMinimal.h"
#include "KhazanAnimationTypes.generated.h"

UENUM(BlueprintType)
enum class EKhazanFoot : uint8
{
    None,
    Left,
    Right
};
```

#pragma once는 중복 포함 방지다. CoreMinimal은 UE 기본 타입/매크로를 제공한다. generated.h는 UHT 생성 파일이며 이 헤더의 마지막 include여야 한다. BlueprintType으로 ABP enum 노드를 사용할 수 있다. uint8은 enum의 저장 기반 타입이다. None은 마커를 읽지 못했다는 의미이며 양발 접지라는 뜻이 아니다. Left/Right는 캐릭터 자신의 좌우 발이다.

### 3-2. AnimInstance.h

`#include "Animation/KhazanAnimationTypes.h"`를 기존 generated.h 앞에 추가한다.

기존 protected 영역에 추가한다.

```cpp
UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion")
EKhazanGait LocomotionGait = EKhazanGait::Walk;

UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Stop")
EKhazanGait StopGait = EKhazanGait::Walk;

UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Stop")
EKhazanFoot StopEntryFoot = EKhazanFoot::None;

UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Stop")
float StopEntrySpeed = 0.f;

UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Stop")
bool bShouldEnterStop = false;
```

Transient는 에셋 기본값으로 저장할 설정이 아닌 런타임 데이터라는 뜻이다. 네트워크 복제를 뜻하지 않는다. BlueprintReadOnly는 ABP가 읽되 일반 Set 노드로 덮어쓰지 않게 한다. Category는 에디터 표시 분류다.

기존 private 이력 세 개를 다음 다섯 개로 정리한다. 기존 이름과 중복 선언하지 않는다.

```cpp
bool bHasPreviousKinematicFrame = false;
bool bWasMoving = false;
bool bHadGroundedMovementInput = false;
float PreviousGroundSpeed = 0.f;
EKhazanGait PreviousLocomotionGait = EKhazanGait::Walk;
```

bHadMovementInput 대신 bHadGroundedMovementInput을 쓴다. 공중에서만 입력했던 이력으로 착지 순간 지상 Stop을 만들지 않기 위해서다. 이력은 그래프에 노출할 필요가 없어 UPROPERTY/BlueprintReadOnly를 붙이지 않는다.

private 함수 선언도 추가한다.

```cpp
EKhazanFoot SelectStopEntryFoot_AnyThread() const;
```

반환값은 발 선택 키다. const는 함수가 AnimInstance 멤버를 수정하지 않고 선택만 반환한다는 뜻이다. AnyThread라는 이름 자체가 스레드 안전을 보장하지는 않는다. 여기서는 엔진이 thread-safe로 제공한 sync 조회 API와 값 계산만 사용한다.

최종 제거 대상은 bUseRun, bUseSprint, bUseRunStop, RunStopSelectionSpeed, bHadMovementInput이다. cpp의 Reset/로그/대입과 ABP Get 노드 참조도 함께 정리한다. bShouldWalkRun, bShouldSprint, bIsStopping, bShouldBeIdle, RunEnterSpeed, RunExitSpeed와 기존 원시 snapshot은 유지한다.

## 4. loop 선택을 enum으로 계산한다

기존 UpdateLocomotionSelection_AnyThread를 다음 본문으로 교체한다.

```cpp
void UKhazanAnimInstance::UpdateLocomotionSelection_AnyThread()
{
    const bool bWantsGroundedMovement =
        bIsGrounded && bHasMovementInput;

    if (bWantsGroundedMovement)
    {
        if (ResolvedGait == EKhazanGait::Sprint)
        {
            LocomotionGait = EKhazanGait::Sprint;
        }
        else if (!bIsMoving)
        {
            LocomotionGait = EKhazanGait::Walk;
        }
        else if (LocomotionGait != EKhazanGait::Walk)
        {
            LocomotionGait = GroundSpeed > RunExitSpeed
                ? EKhazanGait::Run
                : EKhazanGait::Walk;
        }
        else
        {
            LocomotionGait = GroundSpeed >= RunEnterSpeed
                ? EKhazanGait::Run
                : EKhazanGait::Walk;
        }
    }

    bShouldWalkRun =
        bWantsGroundedMovement &&
        LocomotionGait != EKhazanGait::Sprint;

    bShouldSprint =
        bWantsGroundedMovement &&
        LocomotionGait == EKhazanGait::Sprint;

    bIsStopping =
        bIsGrounded && !bHasMovementInput && bIsMoving;

    bShouldBeIdle =
        bIsGrounded && !bHasMovementInput && !bIsMoving;
}
```

- bWantsGroundedMovement는 지상이며 유효한 이동 명령이 있는지를 한 번 계산한 지역 변수다.
- 이 조건이 참일 때만 loop 선택을 갱신한다. 입력 해제와 동시에 속도가 0이 되어도 outgoing Run pose를 Walk로 바꾸지 않고 Stop으로 블렌드하기 위해서다. 입력이 없으면 LocomotionGait는 마지막 loop 선택을 보관한다. Idle에서 Run/Sprint 값이 남아 있어도 실제 이동이나 그 loop의 재생을 뜻하지 않는다.
- Sprint는 현재의 L3 요청/허용 정책으로 선택한다. 아직 속도가 600에 도달하지 않았더라도 Sprint loop로 향하는 현재 정책을 유지한다.
- 움직이지 않으며 위 Sprint 조건도 아니면 다음 일반 loop 선택은 Walk로 초기화한다.
- 현재까지 보관된 LocomotionGait가 Run 또는 Sprint이면 Run 이탈 경계 190을 쓴다. 이는 이번 함수에서 아직 덮어쓰지 않은 이전 선택값이다.
- 삼항식 조건 ? 참일 때 값 : 거짓일 때 값으로 Run/Walk 하나를 저장한다.
- Walk에서 시작하면 진입 경계 220을 쓴다. 상승 중 200은 Walk, Run에서 내려오는 200은 Run이다.
- bShouldWalkRun/bShouldSprint는 서로 다른 전이의 bool 결과다. 별도의 gameplay gait 권한이 아니다.
- bIsStopping/bShouldBeIdle은 물리 관측에 근거한 조건이며 ABP의 현재 활성 상태를 직접 뜻하지 않는다.
- Stop 진입 때는 이 함수가 방금 만든 값 대신 PreviousLocomotionGait를 사용한다. release로 Sprint 요청이나 시각 선택이 달라져도 직전 정보를 보존하기 위해서다.

Sprint 요청 직후 즉시 입력을 놓는 경우에도 직전 선택이 Sprint라면 Sprint Stop을 고르는 기본 정책이다. 가중치가 가장 큰 실제 loop나 일정 최저 속도에 따라 다르게 고르는 정책은 별도 튜닝이다. 이 구현을 최대 가중치 애니메이션 판독이라고 설명하지 않는다.

## 5. Stop 요청과 진입 데이터 계산

UpdateTransitionData_AnyThread를 다음으로 교체한다.

```cpp
void UKhazanAnimInstance::UpdateTransitionData_AnyThread()
{
    bShouldPlayStart = false;
    bShouldEnterStop = false;

    if (bHasPreviousKinematicFrame)
    {
        const bool bJustLostGroundedMovementInput =
            bHadGroundedMovementInput && !bHasMovementInput;

        bShouldEnterStop =
            bIsGrounded &&
            bJustLostGroundedMovementInput &&
            (bWasMoving || bIsMoving);

        if (bShouldEnterStop)
        {
            StopEntrySpeed =
                FMath::Max(PreviousGroundSpeed, GroundSpeed);

            StopGait = PreviousLocomotionGait;
            StopEntryFoot = SelectStopEntryFoot_AnyThread();
        }
    }

    bHasPreviousKinematicFrame = true;
    bWasMoving = bIsMoving;
    bHadGroundedMovementInput =
        bIsGrounded && bHasMovementInput;
    PreviousGroundSpeed = GroundSpeed;
    PreviousLocomotionGait = LocomotionGait;
}
```

- bShouldPlayStart=false는 현재 단계에서 일반 Start를 재생하지 않는 기존 동작이다.
- bShouldEnterStop=false로 매 update 시작 시 요청 pulse를 초기화한다. StopGait/Foot/Speed를 여기서 초기화하지 않는다.
- 첫 update는 과거가 없으므로 비교하지 않고 맨 아래에서 첫 이력만 만든다.
- 직전에 지상 입력이 있었고 현재 유효 입력이 없으면 입력 상실 edge다. bMovementAllowed에 의해 유효 입력이 사라진 경우도 포함한다. 실제 버튼 release만 뜻하는 것은 아니다.
- 현재도 지상이어야 일반 지상 Stop을 요청한다.
- bWasMoving || bIsMoving은 직전 또는 현재에 실질적 이동이 있었는지다. 470→0으로 한 update에 정지해도 통과하지만 움직이지 않은 채 입력만 눌렀다 놓은 경우는 제외한다.
- Max는 두 속도 중 큰 값을 진입 관측으로 보관한다. 시간을 적분하거나 오래전 최고 속도를 유지하는 방식이 아니다. 이전 470, 현재 260이면 470이다.
- StopGait는 직전 loop 선택이다. Walk/Run 경계와 별개의 315 Stop 경계를 두지 않는다.
- StopEntryFoot는 현재 진행 중인 애니메이션 그룹의 가장 최근 완료된 tick 결과에서 후보를 읽는다.
- 마지막 다섯 대입은 반드시 판단 뒤에 실행한다. bHad...를 먼저 현재값으로 덮어쓰면 이전과 현재의 비교가 사라진다.
- 다음 frame의 bShouldEnterStop=false는 원샷 중단 명령이 아니다. 원샷 종료/재입력은 ABP가 결정한다.

이벤트가 두 애니메이션 update 사이에서 발생하고 취소되어 snapshot에 한 번도 보이지 않는 경우까지 복원하는 이벤트 큐는 아니다. 향후 URO/상위 action 상태로 전이를 의도적으로 지연한다면 요청 ID/소비 확인을 추가해야 한다. 현재 단계는 해당 지상 상태에서 즉시 전이를 검사하는 ABP를 전제로 한다.

## 6. 엔진의 마커 결과로 발 후보를 고른다

cpp에 `#include "Animation/AnimationAsset.h"`를 추가한다. FMarkerSyncAnimPosition의 실제 정의가 있는 헤더다.

기존 익명 namespace에 이름 상수를 추가한다.

```cpp
const FName LocomotionSyncGroupName(TEXT("Locomotion"));
const FName LeftFootMarkerName(TEXT("LeftFoot"));
const FName RightFootMarkerName(TEXT("RightFoot"));
```

FName은 엔진의 이름 식별자다. TEXT는 UE 문자열 리터럴을 만든다. const로 이름을 고정하며 float threshold와 달리 FName을 constexpr로 만들지 않는다. 같은 이름을 매번 문자열로 조립하지 않는다.

```cpp
EKhazanFoot UKhazanAnimInstance::SelectStopEntryFoot_AnyThread() const
{
    const FMarkerSyncAnimPosition Position =
        GetSyncGroupPosition(LocomotionSyncGroupName);

    const bool bLeftToRight =
        Position.PreviousMarkerName == LeftFootMarkerName &&
        Position.NextMarkerName == RightFootMarkerName;

    const bool bRightToLeft =
        Position.PreviousMarkerName == RightFootMarkerName &&
        Position.NextMarkerName == LeftFootMarkerName;

    const float Alpha = Position.PositionBetweenMarkers;

    if ((!bLeftToRight && !bRightToLeft) ||
        !FMath::IsFinite(Alpha) ||
        Alpha < 0.f || Alpha > 1.f)
    {
        return EKhazanFoot::None;
    }

    const FName ClosestMarkerName =
        Alpha <= 0.5f
            ? Position.PreviousMarkerName
            : Position.NextMarkerName;

    return ClosestMarkerName == LeftFootMarkerName
        ? EKhazanFoot::Left
        : EKhazanFoot::Right;
}
```

PreviousMarkerName은 직전에 지나온 마커, NextMarkerName은 다음 마커다. PositionBetweenMarkers는 이 두 마커 사이 진행률이다. 0은 이전 마커, 1은 다음 마커, 0.5는 시간상 중간이다. 전체 클립 정규화 시간이 아니므로 여러 보행 주기를 가진 Run/Sprint에도 사용한다.

좌→우 또는 우→좌인 정확한 공통 이름쌍만 인정한다. 마커가 없거나 비정상 구간이면 None을 반환한다. IsFinite는 NaN/무한대를 제외한다.

0.5 이하에서는 직전 접촉 기준, 그 뒤에는 다음 접촉 기준에 가까운 Stop 후보를 고른다. 예를 들어 Left→Right의 0.2면 Left, 0.8이면 Right다. 이는 첫 구현용 '시간상 가까운 접촉' 휴리스틱이며, 실제 지지발 판정도 모든 클립에 유일한 정답도 아니다. 파일 LF/RF의 의미를 해당 초입 접촉 자세와 매핑한 뒤 여러 위상에서 확인해야 한다. 매핑이 반대라면 에셋 연결을 바로잡고 enum의 Left/Right 의미를 뒤집지 않는다.

로컬 UE 5.8에서 UAnimInstance::GetSyncGroupPosition은 BlueprintThreadSafe로 선언되고 GetProxyOnAnyThread를 통해 read buffer를 조회한다. NativeThreadSafeUpdateAnimation은 이번 그래프/asset tick 전에 호출되므로 여기서는 직전 완료 tick 결과를 읽는다. 이것을 현재 프레임 최종 pose라고 부르지 않는다. C++에서 DeltaSeconds를 누적해 별도 보행 시계를 만들지 않는다.

StopEntryFoot는 진입 후 고정한다. Stop→Move는 이 고정값을 다시 사용하지 않고, 재입력 당시 재생 중인 Stop의 현재 marker 위상을 그룹이 전달하도록 한다.

## 7. Reset과 호출 순서

UpdateKinematics_AnyThread의 마지막 호출 순서는 유지한다.

```cpp
UpdateLocomotionSelection_AnyThread();
UpdateTransitionData_AnyThread();
```

원시 데이터/속도/지상/입력/ResolvedGait를 먼저 계산하고, 시각 선택, 진입 데이터, 마지막으로 이력 순서다. GatherGameThreadData나 Player에 Stop 필드를 추가할 필요는 없다.

ResetDerivedData_AnyThread에서 제거한 bUseRun/bUseSprint/bUseRunStop/bHadMovementInput 대입을 지운다. 다른 기존 reset은 보존하고 다음을 초기화한다.

```cpp
LocomotionGait = EKhazanGait::Walk;
StopGait = EKhazanGait::Walk;
StopEntryFoot = EKhazanFoot::None;
StopEntrySpeed = 0.f;
bShouldEnterStop = false;

bHasPreviousKinematicFrame = false;
bWasMoving = false;
bHadGroundedMovementInput = false;
PreviousGroundSpeed = 0.f;
PreviousLocomotionGait = EKhazanGait::Walk;
```

기존 bHasPreviousKinematicFrame/bWasMoving reset과 중복하지 않는다. RunEnterSpeed/RunExitSpeed 같은 튜닝 기본값은 매 update나 Reset에서 덮어쓰지 않는다.

## 8. 현재 Stop 후보와 에디터 준비

모두 InGame/DAS/Locomotion 기준이며 아래는 읽기 전용 확인값이다.

| 역할 | 현재 상대 경로 | frame 구간 / 길이 | marker |
| --- | --- | --- | --- |
| Walk LF | Walk/DAS_Khazan_Walk_Stop_LF | 40 / 1.666667 s | 0 |
| Walk RF 후보 | Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_RF | 249 / 10.375 s | 0 |
| Run LF | Run/DAS_Khazan_Run_Stop_LF | 95 / 3.958333 s | 0 |
| Run RF 후보 | Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_RF | 249 / 10.375 s | 0 |
| Sprint 후보 A | Sprint/CA_P_Kazan_DualAxeSword_Sprint_Stop_F | 249 / 10.375 s | 0 |
| Sprint 후보 B | Sprint/CA_P_Kazan_DualAxeSword_Sprint_Stop_F_02 | 249 / 10.375 s | 0 |

현재 Stop 상태는 LF 두 개만 연결돼 있고 Do Not Sync, Loop=false, Always Reset on Entry=true다. 세 loop의 Sync Group Locomotion 설정과 2/12/16개의 LeftFoot/RightFoot marker는 확인했다. 이미 변경한 LF 길이를 다시 10.375초라고 보고하지 않는다.

편집 절차:

1. 미가공 후보는 같은 InGame gait 폴더 안에서 Duplicate해 보존본과 작업본을 구분한다. 이미 있는 DAS LF를 덮어쓰거나 재복사하지 않는다.
2. Walk/Run RF 작업 이름은 DAS_Khazan_Walk_Stop_RF / DAS_Khazan_Run_Stop_RF다. Sprint 두 파일은 실제 초입 자세를 먼저 비교하고 DAS_Khazan_Sprint_Stop_LF/RF로 역할을 정한다. _02=RF라는 자동 규칙은 없다. 서로 반대 발 variant가 아니라 강도/거리 차이면 가짜 LF/RF 쌍으로 만들지 않는다.
3. 타임라인을 0.25배로 보고 프레임 단위로 확인한다. 처음의 발 접촉 기준, 제동 동작, 상체/무기가 정리되는 시점, 반복 정지 pose tail을 구분한다.
4. 꼬리를 자르는 경우 전체 몸이 더 이상 유의미하게 바뀌지 않는지 보고 결정한다. 현재 사용자가 정한 40/95를 일률적으로 더 짧게 자르지 않는다. 마지막 고유 동작까지 남기고 이후 padding만 Remove frames after 계열 편집 메뉴로 제거한 뒤 경계를 다시 재생한다. 24 fps일 때만 frame/24로 시간을 계산한다.
5. root가 움직이는 후보는 Enable Root Motion=false만으로 제자리 보장이 되지 않는다. 원래 root를 preview한 뒤 Force Root Lock 및 Root Motion Root Lock(Ref Pose/Anim First Frame)의 결과를 비교한다. 발 선택/마커 추가와 캡슐 제동은 별도 문제다.
6. 실제 좌/우 접촉 기준 프레임에 Notify 트랙의 Add Sync Marker → Existing Sync Markers → LeftFoot/RightFoot을 배치한다. Animation Notify 이벤트를 만드는 메뉴와 구분한다.
7. 처음부터 이미 접지한 발을 초입 기준으로 쓸 수는 있지만, 모든 0번 프레임이나 마지막 프레임을 무조건 같은 발 마커로 만들지 않는다. 접촉 없는 구간/Idle tail에 가상의 보행 접촉을 추가하지 않는다.
8. 실제로 존재하는 공통 마커와 해당 구간이 준비된 클립만 동기화 품질 검증으로 넘긴다. 모든 Stop이 loop처럼 좌우를 끝없이 반복해야 하는 것은 아니다. 한 발 접촉만 있거나 마지막 마커 뒤에 양발 정지 자세만 남은 구간은 loop와 같은 의미의 위상이 없을 수 있다. 그 경우 강제 marker 추가로 해결했다고 하지 않는다.

발 접촉과 Sprint variant 매핑은 이번 어시스턴트의 시각 검증 완료 항목이 아니다. 정확한 마커 frame은 사용자가 재생해서 확인해야 한다.

## 9. ABP의 enum 연결

현재 상태 이름 Idle / WalkRun / Sprint / Stop을 유지한다. SprintLoop라는 이름으로 다시 바꾸도록 강요하지 않는다. 일반 Blend Space 또는 BlendSpace1D를 새로 만들지 않는다.

### 9-1. WalkRun

1. WalkRun 안의 Blend Poses by Bool을 EKhazanGait용 Blend Poses by Enum으로 교체한다.
2. Active Enum Value에 Get LocomotionGait를 직접 연결한다.
3. 기본 Default Pose에는 Run loop를 연결하고, 노드 우클릭 Add pin for element에서 Walk만 추가해 Walk loop를 연결한다.
4. 이 구성의 Walk는 Walk pin, Run과 Sprint는 Default의 Run pose를 사용한다. Sprint pose는 외부 Sprint 상태가 담당한다. Sprint로 넘어가는 동안 outgoing WalkRun이 갑자기 Walk pose로 바뀌지 않게 Default=Run으로 한다.
5. 두 loop의 Sync Method=Sync Group, Group Name=Locomotion, Role=Can Be Leader는 유지한다. Loop=true, Rate=1, Child Update Mode=Default, 내부 blend time=0.1초부터 확인한다.

아직 그래프에 남은 bUseRun Get 노드는 제거하고 새 핀을 연결한다. 기존 Sprint 상태와 bShouldSprint 전이는 유지한다.

### 9-2. Stop

Stop 내부를 다음과 같이 만든다.

```text
Output
└─ Gait 선택: StopGait
   ├─ Default(Walk) → 발 선택: StopEntryFoot
   │                  ├─ Default(None/Left) → Walk 왼발 기준 Stop
   │                  └─ Right              → Walk 오른발 기준 Stop
   ├─ Run            → 발 선택: StopEntryFoot
   │                  ├─ Default(None/Left) → Run 왼발 기준 Stop
   │                  └─ Right              → Run 오른발 기준 Stop
   └─ Sprint         → 발 선택: StopEntryFoot
                      ├─ Default(None/Left) → Sprint 왼발 기준 Stop
                      └─ Right              → Sprint 오른발 기준 Stop
```

1. Gait 노드는 EKhazanGait의 Blend Poses by Enum이다. Default를 Walk 세트로 쓰고 Run/Sprint pin을 추가한다.
2. 각 gait에 EKhazanFoot Blend Poses by Enum을 둔다. Default는 Left 기준 클립, Right pin은 Right 기준 클립이다. None의 Left fallback은 에러 시 안전한 출력이지 정확한 발 검증 성공이 아니다.
3. 총 여섯 Sequence Player를 만든다. LF/RF라는 파일 글자보다 앞 절차에서 확인한 접촉 기준에 맞춰 연결한다. Sprint 두 개가 실제 LF/RF 쌍이 아니라면 이 연결은 아직 완료할 수 없다.
4. 모든 Stop Player는 Loop=false, Play Rate=1, Start Position=0으로 시작한다.
5. Stop 내부 enum blend time은 모두 0, Child Update Mode는 Default로 시작한다. 고정된 variant를 선택할 뿐 여러 Always Leader Stop을 동시에 섞는 구조를 만들지 않는다.
6. 바깥 상태 전이가 Move와 Stop 사이의 crossfade를 담당한다. 따라서 내부 0초가 캐릭터 전체의 무블렌드 순간 전환을 뜻하지 않는다.
7. Stop 상태의 Always Reset on Entry=true를 유지한다. 재입력 직후 다시 정지하여 이전 Stop이 아직 fade-out 중일 때도 새 Stop을 초기화하기 위한 설정이다.

### 9-3. 전이

다음 표의 값을 사용한다. Priority 숫자는 같은 출발 상태 안에서 작은 쪽이 우선이다. 수치들은 동작 확인용 시작점이며 최종 연출 튜닝값이 아니다.

| 출발 | 도착 | 조건 | Priority | blend s |
| --- | --- | --- | ---: | ---: |
| Idle | Stop | bShouldEnterStop | 1 | 0.10 |
| Idle | Sprint | bShouldSprint | 2 | 0.10 |
| Idle | WalkRun | bShouldWalkRun | 3 | 0.10 |
| WalkRun | Stop | bShouldEnterStop | 1 | 0.10 |
| WalkRun | Sprint | bShouldSprint | 2 | 0.15 |
| WalkRun | Idle | bShouldBeIdle | 3 | 0.10 |
| Sprint | Stop | bShouldEnterStop | 1 | 0.10 |
| Sprint | WalkRun | bShouldWalkRun | 2 | 0.15 |
| Sprint | Idle | bShouldBeIdle | 3 | 0.10 |
| Stop | Sprint | bShouldSprint | 1 | 0.10 |
| Stop | WalkRun | bShouldWalkRun | 2 | 0.10 |
| Stop | Idle | 기존 Automatic Rule | 3 | 0.08 |

기존 WalkRun/Sprint→Stop의 bIsStopping Get을 bShouldEnterStop으로 교체한다. 현재 없는 Idle→Stop도 추가한다. 이미 재입력이 연결된 Stop→WalkRun/Sprint 핀을 비어 있다고 다시 지적하지 않는다.

Stop 진입 요청 frame에 이미 속도가 0이면 bShouldBeIdle도 참일 수 있다. Stop 우선순위가 높으므로 먼저 원샷에 진입한다. 이 때문에 조건 bool은 현재 재생 상태 enum과 같은 것이 아니다.

Stop→Idle은 GroundSpeed=0 또는 bShouldBeIdle 직접 연결로 바꾸지 않는다. 기존 Automatic Rule Based on Sequence Player in State를 켜고 Automatic Rule Trigger Time=-1 기준으로 선택된 non-looping Player의 종료 근처에서 전이한다. 다른 조건 전이들은 Automatic Rule을 끈다. Stop→이동을 자동 종료보다 우선시해 재입력이 있으면 원샷 끝을 기다리지 않는다.

이번에는 Standard Blend를 유지하고 Transition에 Require Valid Markers 같은 제한을 걸어 입력 반응을 지연시키지 않는다. Grounded/Airborne 외부 전이는 기존 지상/낙하 조건을 유지한다.

## 10. Move→Stop / Stop→Move 동기화

두 방향 모두 pose 연속성은 중요하지만 clip 선택과 phase 동기화는 별개다.

Move→Stop에서는 입력 상실 때 StopGait/StopEntryFoot를 한 번 고른다. 두 발 variant만으로 모든 보행 위상의 pose 차이를 없애지는 못한다. 상태 crossfade와 원본 품질이 함께 필요하다.

Stop 도중에는 처음과 다른 발을 다시 디딜 수 있다. 따라서 Stop→Move를 진입 때의 StopEntryFoot만으로 맞추면 잘못될 수 있다. 재입력 당시 Stop의 marker phase를 incoming loop가 따라야 한다.

마커가 준비된 Stop Player의 시작 설정:

- Method: Sync Group
- Group Name: Locomotion
- Role: Always Leader
- Override Position When Joining Sync Group As Leader: true
- Loop Animation: false
- Start Position: 0

loop는 Locomotion / Can Be Leader / Override Position=false / Loop=true다. Idle은 Do Not Sync로 둔다.

Always Leader는 Stop이 자신의 시간으로 재생되고 겹치는 loop가 따라오게 하는 우선권이다. 로컬 UE 5.8의 Override Position 옵션은 새 Stop이 리더로 합류할 때 기존 loop의 마커 위치로 시간을 강제 이동시키는 것을 막고, 자신의 초기 위치를 기준으로 삼도록 한다. 이 정책은 Stop 도입부 보존을 우선한 선택이다. 초입 pose 차이가 크면 LF/RF 기준과 blend를 조절해야 하며 자동 완전 정합은 아니다.

Stop→Move의 Standard Blend 동안 outgoing Stop이 유효하게 참여하면 loop가 그 marker phase를 따른다. Stop이 빠진 뒤 loop가 leader를 이어받는다. Stop의 진입 Foot를 다시 수동 적용하거나 C++에서 loop 시간을 누적하지 않는다.

마커 없는 Stop을 긴 길이 그대로 그룹에 넣으면 marker sync 대신 length sync가 사용될 수 있어 위상/재생 속도를 기대와 다르게 만들 수 있다. 우선 선택/재입력만 검사하는 중에는 해당 Stop을 Do Not Sync로 두고, 마커와 매핑을 준비한 뒤 위 설정으로 바꾸어 비교한다.

마지막 접촉 이후의 정착/양발 Idle 구간은 순환 보행 phase와 동등하지 않다. 이 구간까지 정확한 발 연결을 보장한다고 하지 않는다. 후반 재입력 품질이 나쁘면 불필요한 tail/Idle 전이 시점과 접촉 기준을 먼저 검토하고, 필요한 경우 접지 curve/재진입 pose 기준을 별도 단계에서 추가한다. 허위 마커로 해결하지 않는다.

Sync Marker는 어느 발/위상인가를 연결하는 정보다. 캡슐 감속 거리와 애니메이션 보폭을 일치시키거나 발을 월드에 고정하는 IK 기능은 아니다.

## 11. bool/enum 성능 검증

enum을 쓰는 것 자체가 느리다는 근거는 없다. UE 5.8 FAnimNode_BlendListByEnum은 uint8 값으로 EnumToPoseIndex 배열을 조회해 child를 고른다. 직접 member Get→Active Enum Value 연결은 Fast Path를 활용하기에 적합한 형태다.

반면 임의의 enum 비교/함수 호출 그래프가 모두 Fast Path라는 보장은 없다. Class Settings → Optimization → Warn About Blueprint Usage를 켜고 Compile 결과와 지원 노드의 번개 표시를 확인한다. enum 비교 한 개 때문에 실질적인 성능 문제가 생긴다고 단정하지도 않는다. pose 평가, 동시에 활성화된 Player, IK, sync, 이벤트 그래프 작업과 함께 프로파일링해야 한다.

bool은 무조건 없애야 할 대상이 아니다. bHasMovementInput과 bIsMoving은 입력 없이 밀리는 상황이나 벽에 막힌 입력 등에서 서로 다른 정보를 가진다. enum으로 gait 하나를 표현하고, 필요한 전이 predicate만 bool로 파생하는 것이 이번 권장안이다.

## 12. 적용 순서와 테스트

1. 모든 작업/에셋을 저장하고 reflected enum/UPROPERTY 변경은 Editor를 닫아 전체 KhazanEditor 빌드하는 방식으로 적용한다. Live Coding만으로 구조 변경 검증을 끝내지 않는다.
2. 신규 타입/선언/함수/Reset을 일관되게 수정한다. 삭제한 bool의 C++ 참조와 매 프레임 UE_LOG를 정리한다.
3. Editor 재실행 후 ABP에서 없어진 변수의 Get 노드를 새 enum/predicate로 교체하고 Compile/Save한다. BP 핀 교체 전 PIE로 동작을 판정하지 않는다.
4. 먼저 세 gait 선택/원샷 고정/재입력을 확인하고, 이후 LF/RF와 마커 동기화를 검증한다. 미준비 Sprint variant를 완성된 연결로 기록하지 않는다.
5. 실제 PIE 플레이어를 Debug Filter로 선택한다. Preview Instance와 Class Defaults를 런타임 값으로 보지 않는다.
6. GroundSpeed, LocomotionGait, StopGait, StopEntrySpeed, StopEntryFoot, bShouldEnterStop과 활성 상태/Player 시간을 관찰한다.
7. 정상 full-speed release와 감속 중 release, 470→0 관측, Sprint→Stop→Walk/Run 재입력, Stop의 초반/중간/후반 재입력, 반복 빠른 재입력, 공중 입력 해제/착지를 각각 확인한다.
8. bShouldEnterStop은 한 update pulse, StopGait/Foot/EntrySpeed는 다음 Stop까지 유지되는 값이어야 한다. Stop 중 GroundSpeed=0은 정상이다.
9. LF/RF 각각을 여러 위상에서 확인하고, Last marker 이후 재입력도 별도로 확인한다.
10. 완료 전 Stop 길이/마커/Sync Group/Player Loop 여부와 삭제한 bool의 남은 참조를 검색한다.

제안 로직의 독립적인 14개 snapshot 시나리오 계산은 통과했다. 이것은 C++ 빌드, 실제 AnimGraph 전이, 접지 pose, 엔진 Sync 동작을 검증한 결과가 아니다.

재사용 표적 감사: `Saved/ImportReports/Khazan_InGame_Step4_Stop_Baseline_20260907.json`. 현재 에셋 metadata, ABP/로그 관찰의 한계, 제안 계산 테스트를 함께 보존했다.

## 근거

- [Epic Animation Optimization](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-optimization-in-unreal-engine): Fast Path와 Blueprint 사용 경고.
- [Epic Blend Nodes](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-blend-nodes-in-unreal-engine): enum pose 선택 노드.
- [Epic Sync Groups](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-sync-groups-in-unreal-engine): 공통 마커, 역할, non-looping 연결.
- [Epic Transition Rules](https://dev.epicgames.com/documentation/en-us/unreal-engine/transition-rules-in-unreal-engine): 전이 우선순위와 자동 종료.
- 로컬 UE 5.8 AnimationAsset.h: FMarkerSyncAnimPosition 필드와 구간 의미.
- 로컬 AnimInstance.h/.cpp, AnimInstanceProxy.cpp, AnimSync.cpp: thread-safe 조회, update/tick 순서, read buffer와 leader 위치 override.
- 로컬 AnimNode_BlendListByEnum.cpp / AnimGraphNode_BlendListByEnum.cpp: enum→pose index 조회와 노출하지 않은 enum 항목의 Default 매핑.

## 2026-09-08 Sprint 단일 Stop과 root 처리 기준

이 섹션이 앞의 Sprint LF/RF 두 클립 전제보다 우선한다. 사용자 확인에 따라 Sprint Stop은 발별 variant를 만들지 않고 단일 클립으로 사용한다. Walk/Run은 LF/RF 분기를 유지한다.

### 단일 Sprint 분기

- StopGait의 Walk/Run 출력에는 기존 EKhazanFoot 선택 노드를 사용한다.
- StopGait의 Sprint 출력에는 단일 Sequence Player를 직접 연결한다. Sprint 전용 Foot enum blend, 가짜 RF 복사본, 같은 클립을 연결한 두 발 분기를 만들지 않는다.
- 필요한 Stop Player는 기본적으로 Walk 2 + Run 2 + Sprint 1 = 5개다.
- 현재 에디터의 작업본은 /Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Stop_LF이며 114프레임 구간/4.75초다. 사용자 확인과 달리 이름만으로 LF 전용 클립이라고 해석하지 않는다.
- 정리 이름은 DAS_Khazan_Sprint_Stop을 권장하지만 이번에는 Rename하지 않았다. 현재 에디터에 남은 CA_P_Kazan_DualAxeSword_Sprint_Stop_F도 자동으로 삭제/교체하지 않았다.
- StopGait와 StopEntrySpeed의 진입 고정은 그대로 필요하다. StopEntryFoot는 Walk/Run에서만 소비해도 된다.
- 선택적으로 Sprint 진입 때 StopEntryFoot=None으로 둘 수 있다. 이때 None은 '이번 선택에서 발 구분 미사용'이며 마커 누락 진단값과 구분해 해석한다. 더 단순하게는 기존 계산을 유지하고 Sprint에서 그 값을 사용하지 않아도 된다.
- 단일 클립도 실제 좌우 접촉 마커가 있다면 Stop→Move 동기화에 활용할 수 있다. LF/RF variant의 수와 한 클립 안의 좌우 접촉 수는 다른 개념이다.
- 한 클립으로 모든 이동 위상에서 초입이 완전히 일치한다고 보장하지 않는다. 마커나 Root Motion은 없는 반대 발 초입 pose를 만들어주지 않는다. 입력을 다음 접촉까지 무조건 대기시키거나 무기 비대칭을 무시해 임의 미러링하지 않는다.

### 현재 확인한 root 설정

- ABP_Player Class Defaults Root Motion Mode: Root Motion from Montages Only.
- Sprint 작업본: Enable Root Motion=false, Force Root Lock=false, Root Motion Root Lock=Ref Pose, Sync Marker 0개.
- root track 표적 샘플: frame 0/57/114의 local translation Y는 약 11.280907/144.982300/148.860214다. 세 표본의 rotation은 identity, scale은 1이다. 전체 궤적의 품질/거리/최대값을 전수 검증한 결과는 아니다.
- 이 raw/local 수치를 실제 캡슐의 월드 cm와 동일시하지 않는다. 현재 Player mesh에는 0.009 상대 스케일이 있으며 리타깃/컴포넌트 변환을 포함한 실제 적용 거리를 따로 확인해야 한다.
- 현재 Stop 그래프에는 Walk/Run LF 두 Player만 있으며 Sprint 연결은 아직 확인된 구현 상태가 아니다.

### 권장안: 현재 단계의 Stop은 인플레이스로 유지

이것은 사용자에게 제시한 권장안이며 에셋 설정을 변경한 결과가 아니다.

1. 캡슐의 실제 이동/제동은 현재 CMC 입력·속도·마찰·제동 계산으로 유지한다.
2. 사용할 InGame Stop 작업본에서 Enable Root Motion=false, Force Root Lock=true로 평가한다.
3. Root Motion Root Lock은 우선 Ref Pose로 기존 loop/Idle과 공통 기준을 맞춰 본다. 위치/회전/크기 단절이 생기면 Anim First Frame과 비교한다. 첫 프레임이 이미 이동된 기준이면 그 오프셋이 남을 수 있다. Zero를 일괄 적용하지 않는다.
4. UE 5.8의 FRootMotionReset은 root의 transform을 선택한 기준으로 대체한다. 단순히 전진 translation 하나만 제거하는 설정으로 오해하지 않는다.
5. Force Root Lock은 평가 정책이며 원래 root track 키를 삭제하는 편집이 아니다. 원본/작업본의 이동 데이터는 보존한다.
6. ABP의 현재 Root Motion from Montages Only는 유지한다. 일반 State Machine의 Sequence Player에서 Stop을 재생하면서 Enable Root Motion 체크만 켜는 것은 캡슐을 그 궤적으로 움직이게 하는 완전한 설정이 아니다.
7. 단일 Sprint Stop은 Loop=false, Start Position=0, Rate=1, Stop state Always Reset on Entry=true로 연결한다. 마커가 아직 없으므로 우선 Do Not Sync로 선택/재입력을 검증하고, 실제 접촉 마커 준비 후 이전 섹션의 동기화 설정을 검토한다.
8. PIE의 캡슐과 메시를 함께 관찰한다. root 고정 후에도 캡슐 제동과 authored 발 궤적이 다르면 미끄러질 수 있다. Root Lock이나 Sync Marker가 물리 제동 거리를 자동으로 맞추지는 않는다.

### Root Motion을 선택할 조건과 변경 범위

Stop의 authored 제동 거리/속도 궤적을 캡슐에 실제 적용하는 것이 조작 요구라면 Root Motion도 유효한 대안이다. 애니메이션에 root 이동이 있다는 사실만으로 반드시 켜야 하는 것은 아니다.

- Root Motion을 적용해도 충돌과 이동 처리는 CMC를 거친다. 달라지는 것은 이동량의 근거다.
- 로컬 UE 5.8 CMC의 CalcVelocity는 애니메이션 Root Motion이 있으면 일반 속도 계산을 건너뛰며, 추출한 root delta / DeltaSeconds로 이동 속도를 계산하는 경로가 있다. 기존 제동 속도와 단순히 두 번 더해지는 방식으로 설명하지 않는다.
- 현재 State Machine Sequence Player를 통해 캡슐에 적용하려면 보통 Root Motion from Everything을 검토해야 한다. 별도 Montage 기반 action 정책은 다른 선택지이며 현재 일반 로코모션을 C++ Montage 강제 재생 구조로 되돌리라는 뜻이 아니다.
- 실제 진입 속도와 클립의 초기 속도, Stop→Move crossfade 중 남는 root motion, 재입력에 대한 반응, 벽/경사/낙하, 스케일/리타깃, 네트워크가 있다면 예측/복제를 함께 검증한다.
- UE 5.8 NeedsImmediateUpdate에는 bNeedsValidRootMotion && RootMotionFromEverything인 경우 즉시 Game Thread update를 요구하는 경로가 있다. NativeThreadSafeUpdateAnimation이라는 함수 이름만으로 항상 Worker Thread 실행이 보장되지 않는다. 다만 Root Motion을 켜면 무조건 성능 문제가 난다고 단정하지 않는다.
- 인플레이스 방식에서 Stop 타이밍/이동 거리 불일치가 크다면, 보존한 root 이동으로 거리 곡선을 만들고 CMC의 남은 제동 거리에 맞춰 pose/시간을 선택하는 Distance Matching을 후속 후보로 검토한다. root 데이터를 분석에 사용하는 것과 root로 캡슐을 구동하는 것은 다른 결정이다.

### 현재 소스의 선행 교정 사항

KhazanAnimInstance.cpp의 UpdateTransitionData_AnyThread에서 현재 조건은 if (!bHasPreviousKinematicFrame)이다. 내부는 이제 초기화 후 return하는 블록이 아니라 이전/현재 이력을 비교하는 블록이므로 if (bHasPreviousKinematicFrame)이어야 한다.

현재 상태에서는 첫 update에 초기값 false인 bHadGroundedMovementInput으로 검사하고, 이후 bHasPreviousKinematicFrame=true가 되면 비교를 건너뛴다. 따라서 정상적인 입력 해제에서 bShouldEnterStop이 생성되지 않는다. Root Motion 설정과 무관한 소스상 조건 반전이며 이번에는 직접 수정하지 않았다.

검증 범위: 소스, 에디터 metadata, 세 root 표본, 공식 문서/로컬 UE 5.8 구현을 읽기 전용 확인했다. 새 빌드/Compile/PIE 재현이나 C++/ABP/에셋 수정은 수행하지 않았다.

근거: [Epic Root Motion](https://dev.epicgames.com/documentation/en-us/unreal-engine/root-motion-in-unreal-engine), [Epic Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine), 로컬 UE 5.8 AnimSequence.cpp / AnimCompressionTypes.h / CharacterMovementComponent.cpp / AnimInstance.cpp.
