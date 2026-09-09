# SprintPivot 1단계 — 진행 방향과 새 입력 방향의 비교

## 2026-09-08 범위와 현재 상태

이 문서는 사용자가 직접 따라 구현하는 가이드다. 아래 C++는 **제안 코드**이며 어시스턴트가 Source에 생성/적용하지 않았다. 새 SprintPivot 동작이 이미 구현되거나 시험을 통과한 것이 아니다.

목표 동작은 `Sprint → SprintPivot(기존 Sprint Stop의 짧은 제동 구간) → 반대 방향 Sprint`다. 일반 `Stop` 상태에는 들어가지 않는다. 모든 Start 제외, Run Turn 제외, InGame 시퀀스 한정 정책을 유지한다.

현재 확인한 자료에는 “180도에 가까움”의 정확한 진입 범위, Pivot용 제동 해제 시점, 입력 중앙 통과 유예 규칙의 원작 근거가 없다. 사용자 지시대로 숫자를 임의로 채우지 않는다. **이번에 따라 구현할 부분은 방향 비교와 관측 데이터까지**이며, 실제 제동/회전/재가속은 원작 근거 확보 이후 단계다. 이 제약을 숨기고 완성된 Pivot 코드로 안내하지 않는다.

검사 근거: [준비 리포트](../../Saved/ImportReports/Khazan_SprintPivot_Preparation_20260908.json).
현재 계약: [로코모션 정본](LOCOMOTION_CURRENT_IMPLEMENTATION.md).

### 이번 직접 관측

- Editor PID 32936에서 InGame Sprint Loop와 Stop은 FrameRate 24/1, RateScale 1.25였다. 어시스턴트가 변경한 값이 아니다. 이전 RateScale 1.0 관측 이후의 현재 값이며 저장 여부/편집 주체는 단정하지 않는다.
- Sprint Stop은 114구간/4.75초, EnableRootMotion=false, ForceRootLock=true다. RateScale만으로 asset에 저장된 길이가 바뀌는 것은 아니다.
- 현재 InGame Sprint Stop/Loop와 Weapons의 Sprint Stop import에서 AnimNotify/float curve/transform curve/Editor metadata tag는 비어 있었다. 발 Sync Marker는 AnimNotify나 Pivot 해제 event와 같은 개념이 아니다.
- 원본 Sprint Stop PSA와 같은 이름의 JSON은 확인되지 않았다. 기존 PSA/SourceSurvey/Timing report를 재사용하고 해당 Character 원본 경로에서 BP/ABP/Locomotion/Sprint/Movement/Turn JSON 이름만 표적 검색했으나 일치 파일은 없었다. 원작 전체에 데이터가 없다는 결론은 아니다.
- 사용자에게 원작 Sprint/방향전환 BP·DataAsset·DataTable JSON 위치를 요청했다. PSA의 길이나 현재 발 marker를 근거 없이 Pivot 해제 시간으로 바꾸지 않는다.

## 1. 전체 구현을 나누는 이유

| 절차 | 내용 | 이번 상태 |
| --- | --- | --- |
| 방향 비교 | 현재 이동 방향과 새 입력 방향의 signed angle 계산 | 아래에서 직접 구현할 수 있는 부분 |
| 원작 수치 확인 | 진입 각도/속도 조건, 제동·회전·해제 조건과 시간 | 필요한 원본 자료 미확인 |
| gameplay Pivot | 실제 이동 입력 억제/제동, 방향 보존, 회전, 재가속, 취소 | 미구현 |
| Anim snapshot | gameplay Pivot 상태/진입 데이터의 값 전달 | 미구현 |
| ABP SprintPivot | 별도 Sequence Player로 Stop 시퀀스 일부 사용, 전이/중단 | 미구현 |
| 회귀 검증 | Sprint 유지, 중앙 통과, 일반 Stop, 공중/취소, 재진입 | 미수행 |

Root Lock된 Stop 포즈만 재생한다고 캡슐이 제동/회전하지 않는다. 일반 Stop 데이터와 Pivot을 섞거나 `ClearMoveInput`/`bMovementAllowed=false`로 Stop 진입을 위장하지 않는다.

현재 Player는 입력을 읽고 `AddMovementInput`에 바로 전달한다. 최종 Pivot의 진입 판정은 game thread에서 새 이동 명령을 적용하기 전의 진행 방향과 비교해야 한다. 현재 AnimInstance 관측만으로 물리 제동을 역으로 시작시키는 구조를 만들지 않는다.

## 2. 왜 MovementDirectionAngle을 재사용하지 않는가

- 현재 `MovementDirectionAngle`: Actor 정면에 대한 실제 속도 방향.
- 이번 `MovementInputAngle`: 실제 속도 방향에 대한 새 입력 방향.

새 입력이 뒤를 가리켜도 아직 몸/속도가 앞으로 향하면 기존 값은 정면을 나타낼 수 있다. 그래서 기존 변수의 의미를 바꾸지 않는다.

벡터를 아래처럼 정의한다.

```text
V = 실제 월드 속도의 XY 성분을 정규화한 방향
I = 월드 이동 입력의 XY 성분을 정규화한 방향

D = V · I
C = (V × I).Z
signed angle = atan2(C, D)를 도 단위로 계산
```

정규화된 두 평면 벡터에서 D는 cos(angle), C는 sin(angle)에 해당한다. 두 값을 함께 사용하면 좌/우와 앞/뒤 사분면을 구분한다. atan(C/D)는 D가 0일 때 나눗셈 문제와 사분면 모호성이 있으므로 사용하지 않는다.

정면 0도, 오른쪽 +90도, 왼쪽 -90도, 반대 ±180도는 좌표계와 기하학의 결과이며 임의 gameplay threshold가 아니다. 정확한 반대 방향에는 좌/우가 유일하게 정해지지 않는다. Sprint 단일 Pivot의 반전 정도에는 부호보다 각도의 절댓값이 중요하지만, **그 절댓값을 어디부터 Pivot으로 볼지는 아직 미확정**이다.

## 3. 사용자가 준비할 파일

| 파일 | 작업 | 이 위치의 이유 |
| --- | --- | --- |
| `Source/Khazan/Character/Locomotion/KhazanLocomotionMath.h` | 새 일반 C++ 헤더 | Player/gameplay와 AnimInstance가 공유할 수학 함수 선언 |
| `Source/Khazan/Character/Locomotion/KhazanLocomotionMath.cpp` | 새 일반 C++ 구현 | FVector 값만 받는 순수 계산. CMC/Actor/재생 상태를 건드리지 않음 |
| `Source/Khazan/Animation/KhazanAnimInstance.h` | 관측 멤버 두 개와 갱신 함수 선언 | ABP의 C++ 부모가 계산 결과를 읽기 전용으로 노출 |
| `Source/Khazan/Animation/KhazanAnimInstance.cpp` | include, 관측 갱신/호출/Reset | 기존 snapshot 및 AnyThread 흐름에서 값 계산 |

Player/Controller/LocomotionComponent/공통 gait enum은 이번 단계에서 수정하지 않는다. 공통 계산 함수를 둔 것은 나중에 Player/Locomotion의 game-thread 판정에서도 같은 수학을 사용하기 위해서다.

## 4. KhazanLocomotionMath.h

Rider에서 기존 `Character/Locomotion` 폴더에 일반 header/cpp를 추가한다. UObject 상속 클래스 생성은 필요 없다.

```cpp
#pragma once

#include "CoreMinimal.h"

namespace KhazanLocomotionMath
{
    KHAZAN_API bool TryCalculateMovementInputAngle(
        const FVector& VelocityWorld,
        const FVector& MoveInputWorld,
        float& OutAngleDegrees);
}
```

- `#pragma once`: 헤더 중복 포함으로 선언이 중복되는 것을 방지한다.
- `CoreMinimal.h`: FVector 등 UE 기본 타입을 사용한다.
- `namespace`: 함수 이름의 소속/충돌을 구분한다. Actor/Component/UObject 인스턴스를 생성하지 않으며 Tick도 없다.
- `KHAZAN_API`: Khazan 모듈의 export/import 지정이다. 기존 모듈의 UBT가 제공하며 새 모듈이 아니다.
- `bool`: 계산 가능 여부를 반환한다. Pivot 활성 상태가 아니다.
- `TryCalculate...`: 입력에 방향이 없거나 계산이 유효하지 않으면 실패할 수 있다는 계약을 이름에 드러낸다.
- 두 `const FVector&`: 호출자의 벡터를 이 함수가 수정하지 않고 참조한다. 속도는 cm/s, 이동 입력은 무차원이다. 정규화 후 방향끼리 비교한다.
- `float& OutAngleDegrees`: 성공한 signed angle을 호출자의 변수에 기록한다. 값과 성공 여부가 분리되므로 유효한 정면 0도와 무효 상태를 구분할 수 있다.
- 세미콜론은 선언의 끝, 중괄호는 namespace의 범위다.

상태나 UObject를 쓰지 않는 계산이므로 새 AnimInstance/Component 클래스를 만들지 않는다. Blueprint에서 이 계산을 직접 호출할 필요가 없으므로 UFUNCTION/BlueprintFunctionLibrary도 만들지 않는다. 이 헤더에는 UHT 대상 선언이 없어 `.generated.h`가 필요 없다.

## 5. KhazanLocomotionMath.cpp

```cpp
#include "Character/Locomotion/KhazanLocomotionMath.h"

#include "Kismet/KismetMathLibrary.h"

namespace KhazanLocomotionMath
{
    bool TryCalculateMovementInputAngle(
        const FVector& VelocityWorld,
        const FVector& MoveInputWorld,
        float& OutAngleDegrees)
    {
        OutAngleDegrees = 0.f;

        if (VelocityWorld.ContainsNaN() || MoveInputWorld.ContainsNaN())
        {
            return false;
        }

        const FVector MovementDirectionWorld = VelocityWorld.GetSafeNormal2D();
        const FVector InputDirectionWorld = MoveInputWorld.GetSafeNormal2D();

        if (MovementDirectionWorld.IsZero() || InputDirectionWorld.IsZero())
        {
            return false;
        }

        const double DirectionDot = UKismetMathLibrary::Dot_VectorVector(
            MovementDirectionWorld,
            InputDirectionWorld);

        const FVector DirectionCross = UKismetMathLibrary::Cross_VectorVector(
            MovementDirectionWorld,
            InputDirectionWorld);

        const double AngleDegrees = UKismetMathLibrary::DegAtan2(
            DirectionCross.Z,
            DirectionDot);

        if (!FMath::IsFinite(AngleDegrees))
        {
            return false;
        }

        OutAngleDegrees = static_cast<float>(AngleDegrees);
        return true;
    }
}
```

### 함수의 각 부분

1. 자기 헤더 include는 선언과 정의를 일치시킨다. Kismet 헤더는 dot/cross/각도 계산 함수의 선언을 제공한다.
2. 같은 namespace 안에 선언과 동일한 이름/인자로 정의한다. 객체를 생성해서 호출하지 않는 일반 함수다.
3. `OutAngleDegrees=0.f`는 실패 시 이전 계산값을 남기지 않는 출력 초기화다. 미확인 Pivot 각도에 임시 기본값을 지정하는 것이 아니다. 실패 반환과 반드시 함께 해석한다.
4. `ContainsNaN`은 해당 엔진 구현에서 NaN뿐 아니라 무한대도 검사한다. `||`는 둘 중 하나라도 잘못됐으면 계산을 중단한다는 뜻이다.
5. `GetSafeNormal2D`는 XY 성분의 길이를 1로 만들고 Z를 0으로 한다. 원래 FVector는 바뀌지 않는다. 속도/스틱 크기를 각도에 섞지 않기 위한 처리다.
6. 엔진 기본 정규화 안전성 검사는 너무 작은 길이를 0 방향으로 반환할 수 있다. 이는 엔진 수학 API의 수치 안전성이지 원작의 “최소 Sprint 속도”나 입력 deadzone이 아니다. 이 값으로 Pivot 진입 정책을 대신 정하지 않는다.
7. 정규화 결과 중 하나라도 `IsZero`면 비교할 방향이 없으므로 false로 반환한다. 영벡터에서 angle 0을 만들어 “정면 입력”으로 오해하지 않는다.
8. `DirectionDot`는 정규화된 V와 I의 내적이다. 같은 방향이면 1, 직각이면 0, 반대면 -1에 해당한다. 함수 반환형에 맞춰 double로 보관한다.
9. `DirectionCross`는 V에서 I 순서의 외적이다. 평면 벡터라 방향 판단에는 Z 성분을 사용한다. 인자 순서를 바꾸면 signed angle 부호가 반대가 된다.
10. `DegAtan2(DirectionCross.Z, DirectionDot)`에서 첫 인자는 sin에 해당하는 값, 둘째는 cos에 해당하는 값이다. 함수가 도 단위 결과를 주므로 다시 RadToDeg를 적용하지 않는다.
11. `FMath::IsFinite`는 최종 각도도 유효한 수인지 확인한다. 실패 시 처음 초기화한 출력과 false를 유지한다.
12. `static_cast<float>`는 double 결과를 AnimInstance에서 쓰는 float로 명시적으로 변환한다. 각도의 단위를 바꾸는 연산이 아니다.
13. 출력 기록이 끝난 뒤 true를 반환한다. 중괄호는 if/함수/namespace 범위를 각각 닫는다.

이 함수는 외부 UObject, static mutable cache, Actor 회전, 이동 허용, Montage를 변경하지 않는다. output 인자를 제외한 상태를 수정하지 않으므로 해당 값을 안전하게 소유한 호출자라면 game-thread 판정과 worker-thread 관측에서 공통으로 사용할 수 있다.

## 6. KhazanAnimInstance.h

기존 `MovementDirectionAngle` 선언은 유지한다. protected의 관측 멤버 근처에 다음을 추가한다.

```cpp
UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Turn")
float MovementInputAngle = 0.f;

UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Turn")
bool bHasValidMovementInputAngle = false;
```

| 항목 | 의도 |
| --- | --- |
| MovementInputAngle | 실제 진행 방향 기준 새 입력의 signed angle, 단위 deg. Pivot 상태/진입 threshold가 아님 |
| bHasValidMovementInputAngle | 이번 update에 비교할 두 방향이 있었는지. true가 “Pivot을 재생하라”는 뜻은 아님 |
| Transient | runtime 관측값을 튜닝/저장 설정으로 취급하지 않음 |
| BlueprintReadOnly | native에서 계산하고 ABP는 읽음. 입력/물리 판단을 BP에서 중복 계산하지 않음 |
| Category | 에디터에서 Turn 관련 관측값으로 묶음 |
| 초기 0/false | 아직 유효한 계산이 없다는 초기 상태. false일 때 각도는 판단에 쓰지 않음 |

private의 함수 선언 목록에 추가한다.

```cpp
void UpdateMovementInputAngle_AnyThread(
    const FKhazanAnimGameThreadData& Snapshot);
```

- AnimInstance가 snapshot을 애니메이션 관측값으로 가공하는 함수이므로 이 클래스에 둔다.
- `void`: 결과를 반환하지 않고 위 두 멤버에 기록한다.
- `const ...&`: 이미 전달받은 snapshot을 수정하지 않고 읽는다.
- `_AnyThread`: 호출 문맥을 표시한 프로젝트 네이밍이며 자동으로 thread safety를 제공하는 문법은 아니다.
- private인 이유: 기존 native update 경로가 호출하고 BP는 결과만 읽기 때문이다.

`FKhazanAnimGameThreadData`에는 이미 `VelocityWorld`와 `MoveInputWorld`가 있으므로 같은 데이터를 다시 추가하지 않는다. 기존 `KhazanAnimInstance.generated.h`는 include 목록의 마지막으로 유지한다.

## 7. KhazanAnimInstance.cpp

include 목록에 추가한다.

```cpp
#include "Character/Locomotion/KhazanLocomotionMath.h"
```

새 함수 정의를 기존 UpdateKinematics 함수 밖에 추가한다.

```cpp
void UKhazanAnimInstance::UpdateMovementInputAngle_AnyThread(
    const FKhazanAnimGameThreadData& Snapshot)
{
    MovementInputAngle = 0.f;
    bHasValidMovementInputAngle = false;

    if (!bIsGrounded || !bHasMovementInput || !bIsMoving)
    {
        return;
    }

    bHasValidMovementInputAngle =
        KhazanLocomotionMath::TryCalculateMovementInputAngle(
            Snapshot.VelocityWorld,
            Snapshot.MoveInputWorld,
            MovementInputAngle);
}
```

- 맨 앞 두 줄은 매 update의 관측 초기화다. 이번 frame에 입력이 없어 계산을 건너뛸 때 이전 반전 각도가 남지 않는다.
- 지상/유효 입력/이동 여부는 이미 위쪽 UpdateKinematics에서 계산한 값이다. 하나라도 만족하지 않으면 결과는 무효로 남긴다.
- 이 gate는 현행 `bHasMovementInput`/`bIsMoving` 계약을 재사용하는 것이다. 그 내부 기존 수치를 원작 검증된 Pivot threshold로 승인하는 것은 아니다.
- helper에는 Actor 정면이나 카메라 방향이 아니라 snapshot의 실제 속도와 월드 입력을 전달한다.
- `MovementInputAngle`은 output 참조로 채워지고, 성공 bool은 `bHasValidMovementInputAngle`에 저장된다.
- 이 함수 안에서 Character/MovementComponent/LocomotionComponent를 직접 읽거나 수정하지 않는다.

### 호출 위치

현재 UpdateKinematics의 사실값 계산 및 MovementDirectionAngle 계산이 끝난 뒤 아래 순서로 둔다.

```cpp
ResolvedGait = Snapshot.ResolvedGait;
RotationMode = Snapshot.RotationMode;

UpdateMovementInputAngle_AnyThread(Snapshot);

UpdateLocomotionSelection_AnyThread();
UpdateTransitionData_AnyThread();
```

기존 함수 호출을 지우거나 두 번 호출하지 않는다. 새 함수가 사용하는 지상/입력/이동 bool이 먼저 준비돼야 한다. Stop 이력 갱신 순서는 유지한다.

### Reset

기존 `ResetDerivedData_AnyThread`에 아래 두 줄도 추가한다.

```cpp
MovementInputAngle = 0.f;
bHasValidMovementInputAngle = false;
```

일반 frame 초기화와 수명주기 Reset은 목적이 다르다. invalid snapshot/해제/재초기화 경로에서는 UpdateMovementInputAngle이 호출되지 않을 수 있으므로 Reset에서도 지운다.

## 8. 에디터와 빌드 작업

1. 네 파일을 저장한다. 이번에는 Player/Stop 코드/시퀀스/ABP 전이를 수정하지 않는다.
2. 새 UPROPERTY와 cpp가 생기는 변경이므로 작업 중 에셋 저장 후 Editor를 닫고 KhazanEditor 구성을 일반 C++ 빌드하는 경로로 확인한다. 현재 Build.cs는 Core/CoreUObject/Engine 의존성이 있어 이번 helper용 새 모듈 추가가 필요 없다.
3. 빌드 성공 후 Editor에서 `/Game/_Art/Kazan/Character/Bluprints/ABP_Player`를 연다.
4. 부모 클래스가 KhazanAnimInstance인지 확인한다. My Blueprint의 상속 변수 표시를 켜고 MovementInputAngle / HasValidMovementInputAngle이 나타나는지 확인한다.
5. ABP를 Compile한다. Class Defaults의 0/false는 runtime 관측 결과가 아니다. 부모 클래스의 새 property가 보이고 Compile이 되는지를 먼저 확인하는 절차다.
6. 이번 단계에서는 SprintPivot state, transition, 임의 release notify/time, PlayRate 변경을 추가하지 않는다. 관측 데이터가 준비됐다는 것과 Pivot 동작이 완성됐다는 것을 구분한다.

## 9. 검증 방법과 한계

수학적 예상 결과:

| 진행 방향 V | 입력 방향 I | 유효성/각도 |
| --- | --- | --- |
| (1,0,0) | (1,0,0) | true / 0도 |
| (1,0,0) | (0,1,0) | true / +90도 |
| (1,0,0) | (0,-1,0) | true / -90도 |
| (1,0,0) | (-1,0,0) | true / ±180도 |
| (0,1,0) | (-1,0,0) | true / +90도 |
| 영벡터 | 유효 방향 | false |
| 유효 방향 | 영벡터 | false |

이번 어시스턴트는 위 경우와 Z 제외 사례를 포함한 8개를 Unreal Python의 대응하는 엔진 수학 함수로 확인했다. 모두 통과했다. **새 C++ helper의 빌드/호출 검증, 미세 벡터 경계/NaN의 전수 runtime 검증, Pivot PIE 검증은 아니다.**

사용자 적용 후 runtime 확인이 필요하면 Rider에서 현재 프로젝트의 Editor 프로세스에 연결하고 helper의 `OutAngleDegrees = ...` 줄에서 입력 두 방향/DirectionDot/DirectionCross.Z/AngleDegrees를 확인한다. 해당 줄 전에는 output 대입이 아직 실행되지 않았으므로 AngleDegrees를 먼저 보고 한 줄 진행 후 OutAngleDegrees를 확인한다. 새로 둔 검사 중단점만 제거하며 기존 사용자 중단점을 일괄 삭제하지 않는다.

평소 앞으로 이동 중에는 유효한 각도가 정면에 가깝고, 입력이 없으면 false가 기대된다. 그러나 빠른 반전이 AnimInstance 평가 전에 CMC에 반영되면 이미 반대로 바뀐 Velocity와 입력이 일치할 수 있다. **항상 반전 순간의 180도를 관측한다고 보장하지 않는다.** 그래서 최종 gameplay Pivot 판정은 이 helper를 Player/Locomotion의 game-thread 입력 처리에서 새 이동 명령을 적용하기 전에 사용하고, 진입 시 필요한 방향을 보존하는 다음 단계가 필요하다.

이 단계의 합격은 새 관측 멤버/수학 함수가 제대로 연결되고 기존 Stop/loop를 바꾸지 않은 것이다. Stop 포즈가 짧게 재생되는 기능까지 이번 단계의 합격 조건으로 삼지 않는다.

## 10. 다음 단계에 필요한 자료

원작의 Sprint/방향전환 관련 Blueprint, DataAsset/DataTable, 상태/전이 설정 JSON 등에서 다음을 확인해야 한다.

- “180도에 가까움”을 나누는 진입 조건과 단위.
- 제동 구간에서 반대 방향 이동/회전을 허용하는 원래 조건, event/curve 또는 시간.
- Sprint 요청과 스틱 중앙 통과, 입력 해제/재입력의 처리.
- 제동/회전/전이 배율과 재진입 제한이 있다면 해당 조건.

원작에서 전용 Turn을 쓰고 현재 프로젝트에서 Stop을 재사용하는 것이라면, 전용 Turn의 시간을 그대로 Stop에 적용할 수 있다고 단정하지 않는다. metadata만으로 새 조합의 값을 결정할 수 없다면 사용자에게 차이를 설명하고 별도 결정을 요청한다.

원작 JSON 위치를 받으면 기존 정본과 이 가이드부터 재개하고 새 함수/멤버를 사용자가 실제 구현했는지 확인한다. 이어지는 gameplay/ABP 코드를 설명할 때도 임시 숫자를 넣지 않는다.

## 기술 근거

- UE 5.8 로컬 `Engine/Source/Runtime/Engine/Classes/Kismet/KismetMathLibrary.h`: DegAtan2, Dot_VectorVector, Cross_VectorVector의 실제 선언을 확인했다.
- UE 5.8 로컬 `Engine/Source/Runtime/Core/Public/Math/Vector.h`: GetSafeNormal2D의 squared-length 검사, IsZero, ContainsNaN의 finite 검사를 확인했다.
- [Epic GetSafeNormal2D](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/TVector/GetSafeNormal2D): 평면 정규화, 작은 길이의 대체 반환, tolerance의 의미.
- 위 기술 근거는 UE 수학 API의 근거다. 원작 Pivot gameplay 수치의 근거와 혼동하지 않는다.

## 2026-09-08 후속 지시 — 원작 우선 및 명시된 임시값 허용

- 이 가이드 작성 이후 사용자가 필요한 경우 어시스턴트가 임의 수치를 선정하되 그 사실을 명시하도록 허용했다. 따라서 앞선 범위 설명과 10절의 원작 JSON 확보 전 보류/임시값 금지 조건은 더 이상 적용하지 않는다.
- 방향 비교 함수와 AnimInstance 관측만을 다룬 이 가이드의 코드 범위는 그대로다. 실제 SprintPivot 진입·제동·회전·재가속·ABP 전이는 후속 구현이며 이 정책 개정만으로 구현 완료된 것이 아니다.
- 후속 설명은 저장된 원작 metadata/report를 우선 활용하고, 필요한 근거가 없으면 선정 이유·단위·동작 영향·검증/조정 기준을 명시한 임시 튜닝값으로 진행할 수 있다. 원작 직접값/계산값/임시값을 코드 주석과 설명에서 구분하고 조정 가능한 설정에 모아 관리한다.
- 원작 자료 제공은 필수 재개 조건에서 제외한다. 후속 구현 전 사용자가 실제 추가한 helper/관측 멤버와 현재 Player/LocomotionComponent를 확인하는 절차는 유지한다.

## 2026-09-08 아키텍처 재검토 — 이 가이드의 선행 추가 절차 철회

- 사용자 요청에 따른 전체 캐릭터 아키텍처 검토로, 이 문서의 KhazanLocomotionMath.h/.cpp 생성 및 AnimInstance MovementInputAngle/유효성 멤버 선행 추가 절차는 더 이상 적용할 다음 단계가 아니다. 현재 Source에도 이 제안은 적용되어 있지 않다.
- 각도의 수학적 의미와 원시 의도/실제 속도의 구분은 유효하지만, 실제 소비와 이동 제어의 책임을 확정하기 전에 공통 파일·매 frame 관측 프로퍼티를 늘리는 순서를 철회한다. 필요한 Pivot 계산은 공통 Locomotion 제어 함수의 지역 계산에서 시작한다.
- 다음 단계는 [캐릭터 아키텍처 검토](../Engineering/CHARACTER_ARCHITECTURE_REVIEW_20260908.md)와 로코모션 정본 최신 절을 기준으로 공통 이동/액션/애니메이션 표현의 소유권을 정하는 것이다. 게임 코드와 에셋은 이번 검토에서 변경하지 않았다.

