# InGame 로코모션 2단계 — 입력 의도, 고정 속도, L3 요청 연결

## 2026-09-07 적용 범위와 진행 방식

이 문서는 `INGAME_LOCOMOTION_MIGRATION.md`의 2단계를 사용자가 직접 구현하기 위한 설명이다. 어시스턴트는 이번 검토에서 C++, Blueprint, Input Action, Animation Sequence, Skeleton을 변경하거나 저장하지 않았다. 아래 코드는 현재 구현 완료 코드가 아니라 사용자가 적용할 예제다.

확정된 정책은 InGame 시퀀스만 사용, Walk 170 / Run 470 cm/s, L3에서만 Sprint 요청 생성, Walk/Run Start 없음, Sprint 전용 Start 및 Stop/Turn 후속 구현이다. 현재 사용자 코드의 임계값은 `0.6 이하 Walk / 0.6 초과 Run`이므로 그대로 따른다.

SprintSpeed, L3 토글/홀드 방식은 아직 사용자 확정 전이다. 아래 `SprintSpeed = 600`, `bToggleSprint = true`, `MoveInputDeadZone = 0.1`은 구현과 테스트를 설명하기 위한 제안 기본값이지 확정된 게임 디자인이 아니다. 특히 600은 애니메이션에서 측정한 Sprint 속도가 아니다. 에디터에서 선택할 수 있게 분리한다.

## 1. 이번에 확인한 결과

### 기본 loop의 Sync Marker

UE 5.8.2의 로드된 에셋을 읽었다. 아래 프레임은 저장된 시간을 24 fps로 환산해 가장 가까운 프레임으로 표시했다.

| 시퀀스 | 길이 / 프레임 구간 수 | LeftFoot 프레임 | RightFoot 프레임 |
| --- | --- | --- | --- |
| Walk/DAS_Khazan_Walk_Loop | 1.375초 / 33 | 7 | 23 |
| Run/DAS_Khazan_Run_Loop | 4.958333초 / 119 | 6, 26, 46, 66, 86, 106 | 15, 35, 55, 75, 95, 115 |
| Sprint/DAS_Khazan_Sprint_Loop | 4.958333초 / 119 | 3, 18, 33, 48, 63, 78, 93, 108 | 11, 26, 41, 56, 71, 86, 101, 116 |

- 각각 2 / 12 / 16개이며 이름이 `LeftFoot`, `RightFoot`으로 일치한다.
- 시간 순서, 좌우 교대, 루프 경계에서의 좌우 교대, 시퀀스 시간 범위 내 배치는 통과했다.
- 저장 시간은 정확히 정수 프레임에 고정된 값만 있는 것은 아니다. 이번 값의 최대 차이는 약 0.057프레임, 약 0.0024초다. 그 자체가 오류는 아니며 접촉 자세를 보지 않고 일괄 이동하지 않는다.
- Run의 현재 기본 대상은 새 `DAS_Khazan_Run_Loop`이다. `CA_P_Kazan_DualAxeSword_Run_F`에는 marker가 0개다. 앞으로 검사/참조 경로를 새 복사본으로 선택한다. 예전 문서의 검사 예제에서 Run 경로 한 줄도 이 이름으로 바꿔 실행한다.
- 세 loop는 Root Motion false, Force Root Lock false, Root Lock Ref Pose, Rate Scale 1이다. 0/중간/끝의 root 표본은 이동·회전이 같았다. 이전 문서의 Force Root Lock true는 공통 고정 정책 제안이지, 정지 root를 가진 loop에서 false면 반드시 동작하지 않는다는 엔진 요구사항이 아니다.
- 이번 검사는 실제 발바닥 접촉, 전체 loop 경계의 자세/속도 연속성, 저장 후 새 에디터 프로세스에서의 유지까지 증명하지 않는다. 사용자는 시퀀스와 필요한 Skeleton을 저장하고 미리보기로 접지를 확인해야 한다.

재사용 자료: `Saved/ImportReports/Khazan_InGame_LoopMarkers_Audit_20260907.json`.

### 현재 입력 코드

`KhazanPlayer.cpp`는 이제 0.6과 비교하고 MaxWalkSpeed에 170/470을 넣는다. X를 카메라 Forward, Y를 Right에 곱해 합치는 것도 현재 IMC의 YXZ Swizzle 계약과 맞는다.

남은 핵심은 `AddMovementInput(WorldInput, 1.f)`다. WorldInput의 길이가 0.2라면 두 번째 인자가 1이어도 최종 입력 길이는 0.2다. UE의 AddMovementInput은 이 벡터를 자동으로 단위 벡터로 바꾸지 않는다. 기본 CMC 지상 이동에서는 아날로그 크기가 가속도 및 입력 속도 제한에 반영된다. 현재 기본 MinAnalogWalkSpeed 15를 가정한 단순 정상 주행 예는 `max(170 * 0.2, 15) = 34 cm/s`다. 이는 실제 PIE 속도 측정값이 아니라 엔진 소스에 따른 계산 예다.

또한 현재 Player는 `SetTargetGait()`를 호출하지 않는다. 물리 MaxWalkSpeed만 바꿔도 Intent의 gait가 자동 변경되지는 않는다. `bMovementAllowed`는 사용자 정의 정책이므로 CMC가 자동으로 읽어주는 값도 아니다. 이동 입력을 넣는 경로에서 함께 검사해야 한다.

### 현재 ABP

- `Locomotion`의 Run Player는 아직 marker가 없는 `CA_P_Kazan_DualAxeSword_Run_F`를 참조한다.
- Walk/Run Player는 모두 `Method = Do Not Sync`, `Group Name = None`이다.
- Idle/Airborne_TEMP는 InGame 밖 `RT_DAS_Idle`, Stop은 InGame 밖 `RT_DAS_Walk_Stop_LF`, `RT_DAS_Run_Stop_LF`다. InGame 전용 그래프 완료로 판정할 수 없다.
- Sprint Player/상태는 아직 없으며 현재 구조는 Sequence Player 두 개와 Bool Blend다. Blend Space가 이미 연결된 것으로 설명하지 않는다.

## 2. 이번 데이터 흐름

```text
IA_Move → PlayerController → Player
    ├─ 원래 입력 크기 → LocomotionComponent.Intent → TargetGait
    │                                           ↓ 허용 상한 적용
    │                                      ResolvedGait
    │                                       ├─ CMC.MaxWalkSpeed
    │                                       └─ AnimInstance snapshot
    └─ 단위 월드 방향 → AddMovementInput → CMC.Velocity → snapshot

IA_Sprint(L3) → Sprint 요청 bool ────────────────┘

GameThread snapshot → AnyThread 파생 데이터 → ABP
```

InputAmount는 단위 없는 조작 크기, MoveDirection은 길이 1인 방향, MaxWalkSpeed/GroundSpeed는 cm/s다. MaxWalkSpeed는 제한값이고 GroundSpeed는 실측값이므로 가속 중에는 다르다. 현재 MaxAcceleration/Braking 1800은 이번 단계에서 유지한다. AddMovementInput에 170/470이나 DeltaSeconds를 곱하지 않는다.

## 3. KhazanPlayer.h — 선언을 준비한다

현재 카메라, SpringArm, BeginPlay/Tick 선언은 유지한다. 기존 이동 함수 옆 public 영역과 protected/private 영역에 아래 항목을 추가한다. 같은 public/protected/private 블록에 합쳐도 된다.

```cpp
public:
    void HandleInputSprintStarted();
    void HandleInputSprintReleased();
    void HandleInputSprintCanceled();
    void RefreshLocomotionGait();

protected:
    UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Speed", meta = (ClampMin = "0.0"))
    float WalkSpeed = 170.f;

    UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Speed", meta = (ClampMin = "0.0"))
    float RunSpeed = 470.f;

    UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Speed", meta = (ClampMin = "0.0"))
    float SprintSpeed = 600.f;

    UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float RunInputThreshold = 0.6f;

    UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float MoveInputDeadZone = 0.1f;

    UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input")
    bool bToggleSprint = true;

private:
    bool bSprintRequested = false;
```

각 선언의 의미:

- `public`: Controller가 입력 전달 함수를 부를 수 있다. Refresh는 나중에 gameplay 허용 상한이 바뀌었을 때 즉시 재적용할 공통 진입점이기도 하다.
- `void`: 결과값을 반환하지 않고 요청 상태나 이동 설정을 갱신한다.
- `HandleInputSprintStarted`: L3 입력 시작을 처리한다. 애니메이션의 SprintStart 시퀀스를 재생하는 함수가 아니다.
- `HandleInputSprintReleased`: 정상 버튼 해제다. 홀드에서는 요청을 끄고 토글에서는 유지한다.
- `HandleInputSprintCanceled`: 취소 이벤트를 받은 경우 조작 방식과 무관하게 요청을 끈다.
- `RefreshLocomotionGait`: 스틱과 L3로 요청 gait를 계산하고 기존 상한을 적용한 뒤 속도를 설정한다. 이동 입력 자체는 추가하지 않는다.
- `protected`: 자식 클래스에서 접근할 수 있는 조정값이다. BP 노출 여부는 UPROPERTY 지정자가 별도로 결정한다.
- `UPROPERTY`: Unreal 리플렉션에 등록한다. 아래 기본값을 자식 BP Class Defaults에서 설정할 수 있게 한다.
- `EditDefaultsOnly`: 레벨에 놓인 개별 인스턴스가 아니라 클래스 기본 설정에서 조정한다.
- `Category`: Details의 정리용 경로다. `|`는 하위 분류를 나타낸다.
- `ClampMin/ClampMax`: 에디터 숫자 입력 범위를 제한하는 메타데이터다. C++에서 직접 잘못된 값을 대입하는 것까지 막아주는 런타임 검증 함수가 아니다.
- `float`: 실수형 수치다. 접미사 `f`는 float 리터럴이다.
- WalkSpeed/RunSpeed/SprintSpeed는 이동 컴포넌트에 적용할 cm/s 제한값이다. RunInputThreshold/MoveInputDeadZone는 0~1 입력 크기 기준이다.
- MoveInputDeadZone는 중심 부근 노이즈를 버리는 hard cutoff다. 범위를 0~1로 다시 늘리는 Enhanced Input Dead Zone Modifier와 달리 살아남은 크기를 재스케일하지 않는다.
- `bToggleSprint`: 조작 방식 설정이다. true는 한 번 눌러 켜고 다시 눌러 끄며, 스틱을 놓아도 취소된다. false는 L3를 누르는 동안 요청한다.
- `bSprintRequested`: 지금 사용자가 Sprint를 요청했는지다. 허용 여부나 실제 Sprint 속도 도달 여부가 아니다. ABP가 직접 참조할 필요가 없어 일반 private bool이다.
- 헤더의 `KhazanPlayer.generated.h` 아래에 새 include를 넣지 않는다. 현재 추가 선언은 기존 include로 충분하다.

## 4. KhazanPlayer.cpp — 입력을 크기와 방향으로 분리한다

프로젝트의 수학 규칙에 맞춰 다음 include를 추가한다.

```cpp
#include "Kismet/KismetMathLibrary.h"
```

기존 LocomotionComponent와 CharacterMovementComponent include는 유지한다. 이동 함수 전체를 다음 예제로 교체한다.

```cpp
void AKhazanPlayer::HandleInputMove(const FVector2D& MovementInput, const FRotator& ControlRotation)
{
    UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();
    if (!Locomotion)
    {
        return;
    }

    if (!Locomotion->GetIntent().bMovementAllowed || IsMoveInputIgnored())
    {
        HandleInputMoveReleased();
        return;
    }

    const float RawInputAmount = static_cast<float>(MovementInput.Length());
    if (RawInputAmount <= MoveInputDeadZone)
    {
        HandleInputMoveReleased();
        return;
    }

    const FRotator YawRotation(0.f, ControlRotation.Yaw, 0.f);
    const FVector Forward = UKismetMathLibrary::GetForwardVector(YawRotation);
    const FVector Right = UKismetMathLibrary::GetRightVector(YawRotation);
    const FVector WorldInput = Forward * MovementInput.X + Right * MovementInput.Y;

    Locomotion->SetMoveInputWorld(WorldInput);
    RefreshLocomotionGait();

    const FVector MoveDirection = Locomotion->GetIntent().MoveInputWorld.GetSafeNormal2D();
    AddMovementInput(MoveDirection, 1.f);
}
```

아래 설명을 위 코드의 순서대로 각 줄에 대응시켜 읽는다.

1. 함수의 `const FVector2D&` / `const FRotator&`는 전달받은 벡터/회전을 수정하지 않고 참조로 읽겠다는 뜻이다. `AKhazanPlayer::`는 이 클래스의 멤버 함수 정의라는 표시다.
2. `Locomotion = GetLocomotionComponent()`: 기존 컴포넌트 주소를 가져온다. 새 컴포넌트를 만들거나 매번 에셋을 검색하지 않는다.
3. `if (!Locomotion)`: 주소가 없으면 뒤의 `->` 접근을 하지 않는다. `return`은 현재 함수만 즉시 끝낸다.
4. `!bMovementAllowed || IsMoveInputIgnored()`: 프로젝트의 이동 금지 또는 엔진의 입력 무시 중 하나라도 참이면 이동을 받지 않는다. `!`는 부정, `||`는 OR다.
5. `HandleInputMoveReleased()`: 지난 프레임의 유효 입력이 남지 않도록 해제와 같은 정리 경로를 사용한다. 캡슐의 현재 Velocity를 0으로 만드는 명령은 아니다.
6. `RawInputAmount`: `sqrt(X*X + Y*Y)`로 현재 들어온 Axis2D의 크기를 구한다. 여기서 Raw는 방향 정규화 전이라는 뜻이며, 장치의 원시 전압이나 Modifier 이전 값이라는 뜻은 아니다.
7. `static_cast<float>`: UE5 벡터 실수 타입으로 계산한 길이를 이 코드의 float 설정값과 같은 타입으로 명시 변환한다.
8. `<= MoveInputDeadZone`: 아주 작은 입력을 방향 정규화하기 전에 버린다. 그렇지 않으면 노이즈 0.001도 크기 1인 이동 입력이 될 수 있다.
9. `YawRotation(0, Yaw, 0)`: Pitch/Roll을 제외하고 카메라 기준 수평 회전만 사용한다. 카메라를 위아래로 볼 때 이동 방향에 Z가 생기는 것을 막는다.
10. Forward/Right: 수평 회전에서 전방 X축과 우측 Y축 단위 벡터를 얻는다. 현재 FRotationMatrix 두 줄과 같은 목적이며 프로젝트 규칙에 맞춰 Kismet 수학 함수로 표현한다.
11. WorldInput: 전방 성분과 우측 성분을 합쳐 카메라 기준 입력을 월드 공간으로 바꾼다. 현재 IMC_Default의 Move 매핑에 YXZ Swizzle이 있어 이 프로젝트에서는 X=Forward, Y=Right다. 일반 튜토리얼의 반대 축 계약을 그대로 섞지 않는다.
12. `SetMoveInputWorld(WorldInput)`: 원래 크기를 담은 입력을 기록한다. 기존 함수는 Z를 제거하고 최대 길이만 1로 제한하므로 0.2는 0.2로 남는다.
13. `RefreshLocomotionGait()`: 기록한 크기와 Sprint 요청으로 이번 이동에 적용할 속도를 결정한다.
14. MoveDirection: 기록된 입력을 XY 평면의 단위 방향으로 만든다. `GetSafeNormal2D()`는 새 벡터를 반환하며 Intent 원본을 정규화해서 덮어쓰지 않는다. 0 벡터에 대한 안전 처리도 있지만 데드존 검사를 대체하지는 않는다.
15. `AddMovementInput(MoveDirection, 1.f)`: 선택한 방향으로 크기 1의 입력을 준다. `1`은 1 cm/s가 아니라 입력 배율이다. 시간 적분과 가감속은 CMC가 한다.

예: 카메라 Yaw=0, 입력=(0.2, 0)이면 WorldInput=(0.2, 0, 0), InputAmount=0.2, MoveDirection=(1, 0, 0)이다. Walk 제한 170으로 가속한다. 입력=(0.3, 0.4)이면 크기는 0.5이고 이동 방향은 (0.6, 0.8, 0)이다. 대각선이라고 더 빨라지지 않는다.

스틱 0.2와 0.5가 모두 같은 Walk 목표 속도로 이동하더라도 Intent.InputAmount는 서로 달라야 한다. 이제 CMC에 주는 유효 입력은 모두 길이 1이므로 Acceleration 크기를 역으로 읽어 원래 스틱 기울기를 복구할 수 없다.

## 5. 공통 gait/속도 갱신 함수

```cpp
void AKhazanPlayer::RefreshLocomotionGait()
{
    UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    if (!Locomotion || !Movement)
    {
        return;
    }

    const FKhazanLocomotionIntent& Intent = Locomotion->GetIntent();
    if (!Intent.bMovementAllowed || IsMoveInputIgnored() || Intent.InputAmount <= 0.f)
    {
        return;
    }

    const EKhazanGait StickGait = Intent.InputAmount > RunInputThreshold
        ? EKhazanGait::Run
        : EKhazanGait::Walk;

    const EKhazanGait RequestedGait = bSprintRequested
        ? EKhazanGait::Sprint
        : StickGait;

    Locomotion->SetTargetGait(RequestedGait);
    const EKhazanGait ResolvedGait = Locomotion->GetResolvedGait();

    switch (ResolvedGait)
    {
    case EKhazanGait::Walk:
        Movement->MaxWalkSpeed = WalkSpeed;
        break;
    case EKhazanGait::Run:
        Movement->MaxWalkSpeed = RunSpeed;
        break;
    case EKhazanGait::Sprint:
        Movement->MaxWalkSpeed = SprintSpeed;
        break;
    default:
        Movement->MaxWalkSpeed = WalkSpeed;
        break;
    }
}
```

- 앞의 두 줄은 의도 컴포넌트와 실제 이동 컴포넌트를 각각 얻는다. null 검사는 두 객체를 구분해 안전하게 접근하기 위함이다.
- `const FKhazanLocomotionIntent& Intent`: 현재 의도 데이터를 복사하지 않고 읽기 전용 참조로 사용한다. 컴포넌트의 Setter가 원본을 바꾸는 것을 금지하는 뜻은 아니다.
- 이동 금지, 입력 무시, InputAmount=0이면 갱신하지 않는다. 입력 해제 시 마지막 gait와 속도 제한을 Walk로 강제 리셋하지 않아 기존 감속과 이후 Stop 진입 데이터 처리를 방해하지 않는다. Gait 자체에 Idle을 추가하지 않는다.
- 여기의 `<= 0`은 앞의 HandleInputMove가 이미 데드존을 통과시킨 입력만 Intent에 기록한다는 계약을 이용한다.
- `조건 ? A : B`는 조건이 참이면 A, 아니면 B를 선택한다. StickGait는 0.6 초과 Run, 나머지 유효 입력 Walk다.
- RequestedGait는 L3 요청이 있을 때만 Sprint다. bSprintRequested를 스틱 크기로 true로 만드는 코드는 없다.
- `SetTargetGait`: 입력의 요구를 컴포넌트에 기록한다.
- `GetResolvedGait`: 기존 Target/MaxAllowed 비교를 그대로 사용한다. Target=Sprint, MaxAllowed=Run이면 결과는 Run이다. 현재 enum 순서 Walk=0, Run=1, Sprint=2에 기반하므로 enum 순서를 임의로 바꾸면 이 비교 의미도 바뀐다.
- switch는 결과 gait에 대응하는 속도 숫자 한 개를 고르는 표다. 애니메이션 클립이나 Start/Stop 상태를 C++에서 고르는 로직이 아니다.
- 각 `case`는 enum 값 하나, 대입은 해당 속도 제한 적용, `break`는 다른 case로 이어 실행되지 않게 switch를 끝내는 문장이다. default는 잘못된 값이 들어온 경우의 보수적 속도 fallback이다.
- 속도는 RequestedGait가 아니라 ResolvedGait로 선택해야 허용 상한이 실제 물리와 AnimInstance에 함께 반영된다.

이 함수는 Move뿐 아니라 L3 이벤트에서도 호출한다. 버튼 처리 함수에서 AddMovementInput을 다시 호출하지 않으므로 이동 입력이 중복 누적되지 않는다. 새 Tick이나 컴포넌트 Tick은 추가하지 않는다. 이후 gameplay 코드가 SetMaxAllowedGait를 바꾸고 즉시 반영해야 한다면 같은 시점에 Player의 RefreshLocomotionGait도 호출한다. 입력이 유지되는 동안의 IA_Move Triggered에서도 다시 평가된다. 이벤트 연결 없이 모든 외부 정책 변화가 자동 통지된다고 가정하지 않는다.

## 6. 이동 해제와 L3 이벤트

기존 HandleInputMoveReleased는 다음으로 교체하고 Sprint 함수 3개를 추가한다.

```cpp
void AKhazanPlayer::HandleInputMoveReleased()
{
    if (UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent())
    {
        Locomotion->ClearMoveInput();
    }

    if (bToggleSprint)
    {
        bSprintRequested = false;
    }
}

void AKhazanPlayer::HandleInputSprintStarted()
{
    bSprintRequested = bToggleSprint ? !bSprintRequested : true;
    RefreshLocomotionGait();
}

void AKhazanPlayer::HandleInputSprintReleased()
{
    if (!bToggleSprint)
    {
        bSprintRequested = false;
    }
    RefreshLocomotionGait();
}

void AKhazanPlayer::HandleInputSprintCanceled()
{
    bSprintRequested = false;
    RefreshLocomotionGait();
}
```

- `if (타입* 변수 = getter())` 형태는 포인터를 선언하고 동시에 null 여부를 검사한다. ClearMoveInput은 기존 함수대로 월드 입력과 InputAmount만 0으로 만든다. Velocity를 즉시 0으로 만들거나 MaxWalkSpeed를 0으로 만들지 않는다.
- 토글일 때 이동 입력을 놓으면 Sprint 요청을 취소한다. 홀드일 때는 L3가 아직 눌려 있는 요청을 유지하지만 InputAmount=0이므로 실제 이동 요청은 없다. 다시 스틱을 움직이면 누르고 있는 L3가 적용된다.
- Started의 `!bSprintRequested`는 false→true, true→false의 반전이다. 홀드 모드는 반전하지 않고 true로 설정한다.
- Released는 홀드만 false로 만든다. 토글에서 정상 버튼 해제로 요청을 지우면 토글로 동작하지 못한다.
- Canceled는 무조건 false다. 단, 모든 UI/possession/매핑 변경이 반드시 Canceled를 발생시킨다고 일반화하지 않는다. 입력 경로를 종료하는 gameplay 단계에서 필요하면 이 정리 함수를 명시적으로 호출한다.
- 이 제안에서는 정지 중 L3를 먼저 눌러 요청을 예약할 수 있다. 요청만으로 캐릭터가 움직이지는 않는다. 예약을 금지하려면 이후 사용자 조작 정책으로 별도 확정한다.
- Move Released가 TargetGait를 덮어쓰지 않기 때문에 정지 중 ResolvedGait가 Sprint로 남을 수 있다. 이것은 남아 있는 요청 모드 정보이며 실제 Sprint 재생/이동 여부는 bHasMovementInput 등과 함께 판정해야 한다.

## 7. 기본 허용 상한과 최초 속도

`Source/Khazan/Character/Locomotion/KhazanLocomotionType.h`의 실제 Intent 기본값 중 다음 두 줄을 사용한다. 기존 UPROPERTY는 유지한다.

```cpp
EKhazanGait TargetGait = EKhazanGait::Walk;
EKhazanGait MaxAllowedGait = EKhazanGait::Sprint;
```

TargetGait=Walk는 아직 입력하기 전 초기 요청 기준이다. MaxAllowedGait=Sprint는 정상 상태에서 Sprint까지 허용한다는 뜻이지 기본 이동을 Sprint로 만든다는 뜻이 아니다. 현재 MaxAllowedGait=Run이면 L3로 요청해도 Run이 결과가 된다. L3 처리 함수에서 상한을 Sprint로 덮어쓰면 안 된다. 스태미나/공격 등 별도 제한을 입력 버튼이 무력화하기 때문이다.

AnimInstance snapshot의 초기 enum 값을 전부 Sprint로 치환하지 않는다. 실제 데이터는 GatherGameThreadData에서 Intent와 GetResolvedGait로 복사된다.

기존 Player의 BeginPlay는 다음처럼 최초 속도를 명시한다.

```cpp
void AKhazanPlayer::BeginPlay()
{
    Super::BeginPlay();
    if (UCharacterMovementComponent* Movement = GetCharacterMovement())
    {
        Movement->MaxWalkSpeed = WalkSpeed;
    }
}
```

Super는 부모 초기화를 유지한다. 이어서 BP 기본값이 반영된 WalkSpeed를 이동 컴포넌트에 적용한다. 생성자에서 WalkSpeed를 참조하는 것만으로는 이후 자식 BP에 저장된 다른 기본값까지 반영됐다고 보장할 수 없기 때문에 시작 시점에 맞춘다. 기존 MaxAcceleration, Braking, RotationRate, 카메라/메시 설정은 바꾸지 않는다.

## 8. GameplayTag와 PlayerController

KhazanGameplayTags.h의 기존 namespace 안에 선언 한 줄을 추가한다.

```cpp
UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_Sprint);
```

KhazanGameplayTags.cpp의 같은 namespace 안에 정의 한 줄을 추가한다.

```cpp
UE_DEFINE_GAMEPLAY_TAG(Input_Action_Sprint, "Input.Action.Sprint");
```

DECLARE는 다른 C++ 파일에서도 이름을 참조할 수 있게 선언하고, DEFINE은 실제 native tag를 등록/정의한다. C++ 식별자는 밑줄, 에디터의 태그 경로는 점을 사용한다. 이 이름을 새 DataAsset 종류나 Montage 이름으로 혼동하지 않는다.

KhazanPlayerController.h의 기존 private 입력 함수들 옆에 선언한다.

```cpp
void Input_SprintStarted(const FInputActionValue& InputValue);
void Input_SprintReleased(const FInputActionValue& InputValue);
void Input_SprintCanceled(const FInputActionValue& InputValue);
```

InputValue는 Enhanced Input 콜백 시그니처를 맞춘 매개변수다. 이벤트 종류로 눌림/해제를 구별하므로 이번 본문에서는 값을 읽지 않는다.

SetupInputComponent의 InputData와 EnhancedInputComponent를 얻은 기존 if 블록 내부에 다음을 추가한다. 함수 밖이나 BeginPlay에 넣지 않는다.

```cpp
const UInputAction* SprintAction =
    InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Sprint);

if (SprintAction)
{
    EnhancedInputComponent->BindAction(
        SprintAction, ETriggerEvent::Started, this, &ThisClass::Input_SprintStarted);
    EnhancedInputComponent->BindAction(
        SprintAction, ETriggerEvent::Completed, this, &ThisClass::Input_SprintReleased);
    EnhancedInputComponent->BindAction(
        SprintAction, ETriggerEvent::Canceled, this, &ThisClass::Input_SprintCanceled);
}
```

- SprintAction은 DA_InputData의 태그→에셋 대응표에서 찾은 Input Action 포인터다.
- FindInputActionByTag는 현재 구현에서 실패 시 원인을 로그에 남기고 nullptr를 반환한다. if는 미설정된 에셋을 바인딩하지 않게 한다. 데이터 미설정을 check/CastChecked로 강제 종료시키는 검사를 새로 만들지 않는다.
- BindAction의 첫 인자는 어떤 액션, 둘째는 어떤 이벤트, this는 콜백 받을 현재 Controller, 마지막은 멤버 함수 주소다.
- `&ThisClass::...`는 그 함수를 지금 실행하는 표현이 아니라 이벤트가 왔을 때 호출할 위치를 등록하는 표현이다.
- 트리거를 추가하지 않은 Digital 액션 기준 Started는 입력 시작에 한 번 발생한다. 토글을 매 프레임 Triggered에 연결하면 누르는 동안 계속 반전되므로 사용하지 않는다.
- Completed와 Canceled를 분리해 토글의 정상 버튼 해제와 취소를 구별한다. Hold/Pressed 등 다른 Trigger를 추가하면 이벤트 의미를 다시 검토해야 한다.

Controller cpp에 세 함수 본문을 추가한다.

```cpp
void AKhazanPlayerController::Input_SprintStarted(const FInputActionValue& InputValue)
{
    if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
    {
        KhazanPlayer->HandleInputSprintStarted();
    }
}

void AKhazanPlayerController::Input_SprintReleased(const FInputActionValue& InputValue)
{
    if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
    {
        KhazanPlayer->HandleInputSprintReleased();
    }
}

void AKhazanPlayerController::Input_SprintCanceled(const FInputActionValue& InputValue)
{
    if (AKhazanPlayer* KhazanPlayer = Cast<AKhazanPlayer>(GetPawn()))
    {
        KhazanPlayer->HandleInputSprintCanceled();
    }
}
```

세 함수 모두 GetPawn으로 현재 조종 대상을 얻고 Cast로 AKhazanPlayer인지 검사한다. 아직 possession되지 않았거나 다른 Pawn이면 본문을 실행하지 않는다. 마지막 줄은 Player에게 이벤트를 전달한다. Controller는 속도 수치나 애니메이션 선택을 계산하지 않는다.

## 9. AnimInstance — 기존 snapshot을 소비한다

현재 GatherGameThreadData에는 아래 세 줄이 이미 있다. 중복 추가하지 않는다.

```cpp
NewData.TargetGait = Intent.TargetGait;
NewData.MaxAllowedGait = Intent.MaxAllowedGait;
NewData.ResolvedGait = LocomotionComponent->GetResolvedGait();
```

Player가 이제 Intent를 갱신하므로 기존 복사 경로를 통해 값이 전달된다. AnyThread 안에서 새로 GetCharacterMovement나 LocomotionComponent를 읽지 않는다.

KhazanAnimInstance.h의 bUseRun 근처에 그래프용 선택 bool을 추가한다.

```cpp
UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
bool bUseSprint = false;
```

Transient는 런타임 계산 결과를 저장용 설정값으로 직렬화하지 않겠다는 뜻이고 BlueprintReadOnly는 ABP가 읽되 Blueprint Set 노드로 값을 임의 변경하지 못하게 한다. 이름은 Sprint pose 분기를 선택할 허용 gait라는 뜻이며 실제 속도 도달이나 이동 입력 유무를 혼자 보증하지 않는다.

UpdateKinematics_AnyThread의 아래 기존 대입 바로 뒤에서 계산한다.

```cpp
ResolvedGait = Snapshot.ResolvedGait;
RotationMode = Snapshot.RotationMode;
bUseSprint = ResolvedGait == EKhazanGait::Sprint;

UpdateTransitionData_AnyThread();
```

순서는 이번 프레임의 gait 복사 → 비교 → 후속 전이 계산이다. 대입보다 앞에서 비교하면 지난 프레임 값을 볼 수 있다. `==`는 같은 enum 값인지 비교해 bool을 만든다. ABP에는 이 결과를 읽는 Get 노드를 연결한다.

ResetDerivedData_AnyThread의 bool 초기화에 다음 한 줄도 추가한다.

```cpp
bUseSprint = false;
```

유효 Pawn이 없는 미리보기나 AnimInstance 재초기화 때 이전 Sprint 상태가 남지 않게 한다.

이번 단계에서는 현재 bShouldWalkRun의 지상 이동 판정을 유지한다. 아직 Sprint 상태를 연결하기 전에 `!bUseSprint`를 여기에 넣으면 기존 유일한 이동 경로를 막을 수 있다. 3단계에서 SprintLoop 분기를 함께 만들면서 WalkRun/Sprint 진입 조건을 분리한다. bUseRun도 현재 GroundSpeed 기반 역할을 유지하고 3단계에서 전환 기준과 떨림 방지를 조정한다. ResolvedGait와 GroundSpeed가 같은 뜻이라고 바꾸지 않는다.

일반 Start 요청은 지금 중단한다. UpdateTransitionData_AnyThread에 이미 있는 `bShouldPlayStart = false;`는 유지하고 다음 두 줄은 제거한다.

```cpp
const bool bJustStartedMoving = bShouldWalkRun && !bWasMoving;
bShouldPlayStart = bJustStartedMoving && ResolvedGait != EKhazanGait::Walk;
```

이렇게 하면 Walk/Run Start 요청은 발생하지 않는다. 이번 단계에서 SprintStart까지 완성하는 것은 아니므로 `!= Walk`를 단순히 `== Sprint`로 바꾸고 완료 처리하지 않는다. 그 변경만으로는 이미 달리던 중 Run→Sprint 진입을 감지하지 못한다. 실제 SprintStart의 요청/소비/중단은 5단계에서 다룬다. 기존 Stop 계산과 bWasMoving/bHadMovementInput 기록은 이번에 재설계하지 않는다.

## 10. 에디터 설정 — 입력 에셋과 클래스 기본값

### 빌드 순서

1. 위 C++ 선언/정의의 짝을 모두 작성하고 저장한다.
2. UPROPERTY/native tag를 추가하므로 현재 작업 중인 에셋을 저장한 다음 에디터를 닫고 Rider에서 KhazanEditor / Development Editor / Win64 빌드를 권장한다. Live Coding만으로 새 반영 상태를 확정하지 않는다.
3. 빌드 성공 후 프로젝트를 다시 연다. 새 UPROPERTY와 Input.Action.Sprint 태그가 보이는지 확인한다.

### IA_Sprint 생성

1. Content Browser의 `/Game/Input`을 연다.
2. 빈 공간 우클릭 → Input → Input Action으로 생성하고 `IA_Sprint`로 이름을 지정한다.
3. 에셋을 열어 Value Type을 Digital(bool)로 설정한다. 눌림/해제만 필요하므로 Axis2D가 아니다.
4. 이 예제는 Triggers와 Modifiers를 비운 상태로 사용한다. Hold Trigger는 버튼을 계속 누르는 조작과 별개로 일정 유지 시간을 요구하는 기능이므로 임의로 추가하지 않는다.
5. 저장한다.

### IMC_Default 매핑

1. `/Game/Input/IMC_Default`를 연다. UE 5.8에서는 기본 매핑 목록이 Default Key Mappings 아래 보일 수 있다.
2. 기존 Move/Turn/Jump/Attack을 보존하고 새 Action 매핑 하나를 추가한다.
3. Action은 IA_Sprint, Key는 Gamepad Left Thumbstick Button으로 선택한다. 내부 키는 `Gamepad_LeftThumbstick`이다.
4. `Gamepad_Left2D`는 기울기 축, `Gamepad_LeftThumbstick`은 누르는 버튼이다. L3에 2D축을 배정하지 않는다.
5. Sprint 매핑에도 Triggers/Modifiers를 추가하지 않고 저장한다. 키보드 Shift 매핑은 요청한 L3 전용 정책에 없으므로 이번 예제에 추가하지 않는다.

### DA_InputData 연결

1. `/Game/Data/DA_InputData`를 연다.
2. InputMappingContext가 현재와 같이 IMC_Default인지 확인한다.
3. InputActions 배열에 항목 하나를 추가한다. 기존 4개를 지우거나 덮어쓰지 않는다.
4. InputTag에 `Input.Action.Sprint`, InputAction에 `/Game/Input/IA_Sprint`를 지정한다.
5. 저장한다. IMC는 키→액션, 이 데이터는 태그→액션을 담당하므로 둘 다 필요하다. AssetManager가 읽는 기존 DA_InputData를 갱신하는 것이지 별도 미등록 DA를 새로 만드는 과정이 아니다.

### BP_KhazanPlayer 기본값

1. `/Game/_Art/Kazan/Character/Bluprints/BP_KhazanPlayer`를 연다.
2. Class Defaults를 선택하고 새 Locomotion 카테고리를 찾는다.
3. WalkSpeed=170, RunSpeed=470, RunInputThreshold=0.6을 확인한다.
4. 설명용 테스트는 SprintSpeed=600, MoveInputDeadZone=0.1을 사용할 수 있다. 이 둘은 최종 튜닝값이 아니다. SprintSpeed는 RunSpeed보다 크게, DeadZone은 RunInputThreshold보다 작게 둔다.
5. Toggle Sprint를 켜면 토글 제안, 끄면 홀드 제안이다. 사용자 조작 디자인은 여기서 선택하며 이전에 확정된 것으로 간주하지 않는다.
6. Compile 후 Save한다. PlayerController 자식 BP와 ABP도 Compile 오류가 없는지 확인한다.
7. 현재 IA_Move에는 action modifier가 없고 Move 매핑에는 YXZ Swizzle만 있다. 이 예제에서는 Swizzle을 유지하며 데드존을 C++에서 처리한다. Enhanced Input에 Radial Dead Zone을 추가하려면 크기 재매핑과 0.6 임계값 의미를 다시 정리하고 이중 데드존을 피한다.

## 11. marker를 소비할 ABP 설정 위치

이 절은 1단계 확인의 마무리이자 3단계 그래프 준비다. 입력 2단계와 그래프 3단계를 모두 완료했다고 혼동하지 않는다.

1. `/Game/_Art/Kazan/Character/Bluprints/ABP_Player`를 연다.
2. AnimGraph의 Locomotion State Machine → Grounded → GroundedLocomotion → Locomotion 내부로 들어간다. 이름보다 Walk/Run Player 두 개가 있는 실제 그래프를 기준으로 찾는다.
3. Run Sequence Player를 선택하고 Details의 Sequence를 `Run/DAS_Khazan_Run_Loop`으로 바꾼다. 마커 없는 CA_P 원본을 그대로 두면 새 복사본의 작업이 사용되지 않는다.
4. Walk Player가 `Walk/DAS_Khazan_Walk_Loop`인지 확인한다.
5. 두 Player 각각 Sync 설정에서 Method=Sync Group, Group Name=Locomotion, Group Role=Can Be Leader를 지정한다.
6. Loop Animation=true, Play Rate=1을 기준으로 시작한다. 서로 다른 주기 수를 맞추려고 긴 Run/Sprint를 강제로 한 주기로 자르지 않는다.
7. Group Name은 재생 노드들이 공유하는 그룹, LeftFoot/RightFoot은 시퀀스의 같은 접촉 사건이다. 둘을 같은 이름으로 만들 필요는 없다. 같은 그룹에서 공통 marker가 있을 때 엔진이 marker 기반 위상을 사용한다.
8. 3단계에서 추가할 SprintLoop Player에도 같은 그룹을 설정한다. Idle이나 아직 준비하지 않은 Stop/Start에 무조건 같은 그룹을 지정하지 않는다.

기존 Bool Blend에 bUseRun을 직접 연결하는 구조는 유지한다. 이번에 BlendSpace1D로 바꾸거나 BS_DAS_Player_WalkRun을 강제로 생성하지 않는다. 이후 Blend Space를 선택할 때 사용자 지정 이름을 유지한다.

InGame 전용 기준으로 기본 그래프를 검증하기 전에는 다음 밖의 참조도 교체해야 한다. 연결할 후보는 다음과 같고, Stop의 유효 길이/지지 발 선택/완주 판단은 4단계 검증 대상이다.

| 현재 참조 위치 | InGame 후보 |
| --- | --- |
| Idle와 Airborne_TEMP의 RT_DAS_Idle | Idle/CA_P_Kazan_DualAxeSword_Off_Stand |
| Stop의 RT_DAS_Walk_Stop_LF | Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_LF |
| Stop의 RT_DAS_Run_Stop_LF | Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_LF |

Airborne_TEMP의 Idle은 공중 애니메이션 완성이 아니라 명시적인 임시 pose다. 위 후보를 배정했다고 Stop/Sprint/공중 동작이 완성된 것으로 판단하지 않는다.

## 12. 사용자가 실행할 검증

1. 에셋을 저장하고 C++ 빌드와 관련 BP Compile 오류가 없는지 확인한다.
2. PIE에서 입력을 게임 뷰포트가 받도록 포커스를 둔다.
3. 콘솔의 `showdebug enhancedinput`으로 Move Axis2D와 Sprint 디지털 액션이 기대한 키에서 들어오는지 확인한다. 이 화면 값은 Intent나 실제 속도를 대신 측정하는 값이 아니다.
4. ABP의 Debug Filter에서 실제 PIE의 플레이어 인스턴스를 선택한다. 클래스 기본값/Preview Instance를 플레이 중 데이터로 오해하지 않는다.
5. InputAmount, GroundSpeed, ResolvedGait, bUseRun, 새 bUseSprint를 확인한다. bSprintRequested 자체는 Player의 private 조작 상태라 ABP 변수 목록에 없다.

| 테스트 | 기대 결과 |
| --- | --- |
| 입력 크기 0.2 / L3 없음 | Intent는 약 0.2, gait Walk, 장애물 없는 지상에서 가속 후 약 170 |
| 입력 크기 0.5 / L3 없음 | Intent는 약 0.5, gait Walk, 동일하게 약 170 |
| 입력 크기 0.8 / L3 없음 | gait Run, 가속 후 약 470 |
| 입력 크기 1 / L3 없음 | 여전히 Run, 약 470; Sprint 아님 |
| 대각선 같은 크기 입력 | 해당 gait 목표 속도 동일 |
| 유효 입력 + L3 요청 + MaxAllowed Sprint | Resolved Sprint, 설정한 SprintSpeed |
| L3 요청 + MaxAllowed Run | Target Sprint지만 Resolved Run, 속도 470 |
| L3 해제/재누름 | 홀드/토글 설정에 따라 요청 해제; 스틱 크기의 Walk/Run으로 복귀 |
| 스틱 놓기 | InputAmount 0, 새 이동 입력 중단, 기존 감속; 순간 Velocity=0을 기대하지 않음 |
| bMovementAllowed false | 새 입력은 CMC에 전달하지 않음; 별도 root motion/넉백/이미 가진 관성까지 잠근다는 의미는 아님 |

물리 Sprint는 확인할 수 있어도 2단계 시점에는 SprintLoop 상태가 아직 없으므로 화면에 Run이 보일 수 있다. 이 차이를 입력 바인딩 실패로 오해하지 않는다. 일반 Start 요청은 false이며 SprintStart는 5단계까지 대기한다.

현재 bUseRun은 GroundSpeed > 170이므로 가속/감속 중 ResolvedGait와 다를 수 있다. 3단계에서 Walk/Run 선택 기준, 경계 떨림과 SprintLoop 분기를 함께 다듬는다. 짧은 Stop 입력 해제, LF/RF 선택, 실제 foot sliding까지 이번 2단계 완료 조건으로 섞지 않는다.

## 13. 근거와 검증 범위

- [Epic AddMovementInput](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/APawn/AddMovementInput): 월드 방향 벡터와 입력 배율의 의미.
- [Epic Enhanced Input](https://dev.epicgames.com/documentation/en-us/unreal-engine/enhanced-input-in-unreal-engine): Digital/Axis2D, Triggered/Started/Completed/Canceled, modifier와 입력 진단.
- [Epic Sync Groups](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-sync-groups-in-unreal-engine): 같은 그룹의 공통 marker, Method/Role 설정, 서로 다른 보행 주기 수의 동기화.
- 로컬 UE 5.8 CharacterMovementComponent.cpp의 ScaleInputAcceleration, ComputeAnalogInputModifier, CalcVelocity(MaxInputSpeed) 구현을 확인했다.

이번 실행 검증은 기존 소스와 에디터의 읽기 전용 에셋/그래프/입력 메타데이터 검사다. 위 구현 예제의 C++ 빌드, BP Compile, PIE 속도, L3 실기기 동작은 사용자가 적용한 뒤 검증해야 하며 현재 통과로 기록하지 않는다. 멀티플레이의 custom gait/속도 예측 및 복제는 이번 로컬 플레이어 입력 단계의 구현 범위가 아니다.
