# InGame 로코모션 3단계 — Idle / WalkRun / SprintLoop와 재생 선택

## 2026-09-07 범위와 현재 기준

사용자는 2단계 테스트를 완료했다고 보고했다. 이번에는 현재 소스/로드된 ABP를 읽고 다음 구현 절차를 설명한다. 어시스턴트가 C++/BP/시퀀스를 직접 변경하거나 빌드/PIE로 재검증한 것은 아니다.

현재 확인:

- Player의 입력 크기 보존, 이동 방향 GetSafeNormal2D, 요청/허용 gait에 따른 MaxWalkSpeed 적용이 반영됐다.
- 현재 입력 시작 함수 이름은 `HandleInputSprint`이며 Controller의 Started 이벤트와 맞게 연결돼 있다. 이전 예제의 Started 접미사로 다시 바꿀 필요 없다.
- BP_KhazanPlayer 기본값은 Walk 170, Run 470, Sprint 600, RunInputThreshold 0.6, MoveInputDeadZone 0.1, bToggleSprint true다. 현재 구현값이라는 뜻이며 최종 튜닝 확정을 대신하지 않는다.
- 실제 Intent의 TargetGait 기본값은 Walk, MaxAllowedGait는 Sprint다. AnimInstance에 bUseSprint 계산/초기화가 있고 일반 Start 요청은 false다.
- ABP Walk/Run은 각각 DAS_Khazan_Walk_Loop / DAS_Khazan_Run_Loop을 사용하며 둘 다 Sync Group Locomotion, Can Be Leader다. Sprint Player는 아직 없다.
- Idle/Airborne_TEMP와 Stop 두 Player에는 InGame 밖 참조가 남아 있다.
- 현재 Stop→Locomotion의 Can Enter Transition은 연결 없이 false다. Stop→Idle은 Automatic Rule=true, crossfade 0.08초다. 그래프에 남은 과거 ErrorMsg 문자열만으로 현재 Compile 실패를 단정하지 않고 실제 핀/옵션을 읽어 구분했다.

3단계 목표는 기본 pose 분기, loop 동기화, 공중 분리, 재입력 경로다. Walk/Run Start를 만들지 않는다. SprintStart는 5단계에서 삽입한다. Stop 상태/원샷 완주 정책은 보존하되 LF/RF·Sprint Stop 선택과 유효 길이는 4단계에서 완성한다. 예제의 새 220/190 cm/s, 0.10/0.15초는 튜닝 시작값이다.

## 1. 왜 그 클래스에 두는가

| 소유자 | 데이터/함수 | 이유 |
| --- | --- | --- |
| PlayerController | Input_Move / Input_Sprint 등 | 장치 이벤트를 현재 조종 Pawn에 전달한다. 애니메이션 세트나 물리 속도를 결정하지 않는다. |
| KhazanPlayer | bSprintRequested, bToggleSprint, RunInputThreshold, HandleInputSprint, RefreshLocomotionGait, 현재 속도 설정값 | 플레이어 입력을 조종 중인 몸체의 이동 요구로 해석한다. AI는 L3/토글을 알 필요가 없다. |
| LocomotionComponent | Intent, TargetGait, MaxAllowedGait, GetResolvedGait | 입력 장치와 무관한 요청/허용 계약이다. 나중에 NPC도 같은 계약을 사용할 수 있다. |
| CharacterMovementComponent | Velocity, Acceleration, MaxWalkSpeed, MovementMode | 충돌, 가감속, 실제 이동을 소유한다. 애니메이션이 업데이트되지 않아도 이동 규칙은 유지돼야 한다. |
| KhazanAnimInstance | GroundSpeed, bIsGrounded, bUseRun, bUseSprint, bShouldWalkRun, bShouldSprintLoop, RunEnterSpeed/RunExitSpeed | 움직임을 어떤 pose로 보여줄지 판단하는 애니메이션 관측값/선택 정책이다. Player에게 ABP 상태 이름을 알릴 필요가 없다. |
| ABP_Player | 상태 그래프, 시퀀스 참조, 재생 시간, 블렌드 시간, Sync Group | 어떤 pose를 얼마나 섞고 어떤 원샷을 언제 끝내는지 소유한다. 별도의 C++ 재생 시계를 만들지 않는다. |

Player의 `RunInputThreshold = 0.6`은 단위 없는 입력 기준이고 AnimInstance의 `RunEnterSpeed = 220`은 cm/s 시각 선택 기준이다. 둘이 다른 이유는 요청과 실측 속도가 다르기 때문이다. Run을 요청한 직후 GroundSpeed=80이면 Run 목표 속도로 가속 중이면서 Walk pose를 잠깐 사용할 수 있다.

Run 애니메이션을 교체해서 자연스러운 시각 전환 속도가 바뀌었다고 물리 RunSpeed=470이나 L3 정책이 바뀌어서는 안 된다. 반대로 AnimInstance가 교체/재초기화되었다고 Sprint 버튼 요청이 사라지면 안 된다. 변경 이유와 수명이 다른 값을 분리하는 기준이다.

현재 속도 숫자를 Player에 둔 것은 현 단계의 플레이어 이동 튜닝을 함께 관리하기 위함이다. NPC와 공유하는 속도 프로필이 실제로 필요해지면 공용 Locomotion 설정/컴포넌트로 이동할 수 있지만 이번에는 이동하지 않는다.

이번 수정 대상은 KhazanAnimInstance.h/.cpp와 ABP_Player다. Player.h/.cpp, Controller, GameplayTag, InputData, snapshot 구조에 새 선언을 추가하지 않는다.

## 2. 목표 그래프

```text
AnimGraph
└─ 기존 Locomotion State Machine → 기존 Slot → Output Pose
   ├─ Grounded
   │  └─ GroundedLocomotion
   │     ├─ Idle
   │     ├─ WalkRun       (현재 내부 Locomotion 상태를 재사용)
   │     ├─ SprintLoop    (이번에 추가)
   │     └─ Stop          (기존 상태 보존, 4단계에서 완성)
   └─ Airborne_TEMP       (InGame Idle을 쓰는 임시 공중 pose)
```

상태 이름 WalkRun과 C++ 변수 bShouldWalkRun은 자동으로 연결되지 않는다. 전이 그래프에서 직접 변수 Get을 Can Enter Transition에 연결해야 한다. C++ bool은 진입 조건이고 ABP가 실제 상태/시간/블렌드를 소유한다.

## 3. KhazanAnimInstance.h에 추가할 선언

기존 private 함수 선언들 옆에 다음을 추가한다.

```cpp
void UpdateLocomotionSelection_AnyThread();
```

- `void`: 반환값 대신 AnimInstance의 파생 멤버들을 갱신한다.
- `UpdateLocomotionSelection`: pose 및 전이 선택에 사용할 조건을 정리한다. 시퀀스를 재생하는 함수가 아니다.
- `AnyThread`: 호출될 수 있는 문맥을 표시하는 이름이다. 이름만으로 병렬 실행되거나 안전해지지 않는다. Actor/Component를 읽지 않고 이미 수집된 값만 사용한다.
- 매개변수 없음: 현재 AnimInstance가 계산한 GroundSpeed, bHasMovementInput, ResolvedGait 등을 사용한다. 시간 누적/보간 함수가 아니므로 DeltaSeconds도 필요 없다.
- `private`: 내부 업데이트 순서에서만 호출한다. Player/Controller/BP가 임의 시점에 호출하는 API가 아니므로 UFUNCTION이나 BlueprintCallable도 추가하지 않는다.

protected의 기존 파생 변수 영역에 아래 두 변수를 추가한다.

```cpp
UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Movement")
bool bIsGrounded = false;

UPROPERTY(Transient, BlueprintReadOnly, Category = "Animation|Locomotion|Transition")
bool bShouldSprintLoop = false;
```

- bIsGrounded: snapshot의 MovementMode가 Walking/NavWalking인지다. 애니메이션의 지상 분기를 위한 관측값이다. 수영/비행도 '낙하 아님'이므로 !bIsFalling과 같다고 정의하지 않는다.
- bShouldSprintLoop: 현재 지상 이동 요청을 SprintLoop로 보여줄 조건이다. bUseSprint와 달리 지상/입력까지 반영한다.
- Transient: 계산 결과를 저장 설정값으로 직렬화하지 않는다.
- BlueprintReadOnly: ABP에 Get으로 노출한다. Event Graph에서 Set으로 다시 계산하지 않는다.
- Category: 에디터 정리용이다. 실제 실행 순서나 thread를 바꾸지 않는다.
- false: 아직 유효한 snapshot을 받지 않았을 때 기본값이다.

같은 protected 영역의 튜닝 변수들 옆에 다음을 추가한다.

```cpp
UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Animation|Locomotion|Tuning", meta = (ClampMin = "0.0"))
float RunEnterSpeed = 220.f;

UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Animation|Locomotion|Tuning", meta = (ClampMin = "0.0"))
float RunExitSpeed = 190.f;
```

- RunEnterSpeed: 현재 Walk pose 선택 중일 때 Run pose로 넘어갈 실측 속도.
- RunExitSpeed: 현재 Run pose 선택 중일 때 Walk pose로 돌아갈 실측 속도.
- 단위는 cm/s다. MaxWalkSpeed에 대입하지 않는다.
- EditDefaultsOnly: ABP_Player의 Class Defaults에서 튜닝한다. Player BP가 아니라 AnimInstance 자식 BP의 기본값이다.
- BlueprintReadOnly: 필요할 때 읽을 수 있으나 그래프 Set으로 소유권을 분산하지 않는다.
- ClampMin은 에디터 입력 메타데이터이지 C++ 런타임 검증은 아니다. 이번 기본값은 `170 < 190 < 220 < 470`이고 RunExitSpeed < RunEnterSpeed를 유지해야 한다.
- 기존 RunStopSelectionSpeed=315는 Stop 종류 선택 기준이다. 이 둘과 책임이 다르므로 재사용하거나 이름만 바꾸지 않는다.

bUseRun/bUseSprint/bShouldWalkRun/bIsStopping/bShouldBeIdle은 이미 있으므로 중복 선언하지 않는다. 새 값을 snapshot 구조체에 추가할 필요도 없다. MovementMode와 속도/의도 자료가 이미 있기 때문이다.

## 4. 새 선택 함수와 히스테리시스

KhazanAnimInstance.cpp에 다음 함수를 추가한다.

```cpp
void UKhazanAnimInstance::UpdateLocomotionSelection_AnyThread()
{
    bUseSprint = ResolvedGait == EKhazanGait::Sprint;

    if (!bIsMoving)
    {
        bUseRun = false;
    }
    else if (bUseRun)
    {
        bUseRun = GroundSpeed > RunExitSpeed;
    }
    else
    {
        bUseRun = GroundSpeed >= RunEnterSpeed;
    }

    const bool bWantsGroundedMovement = bIsGrounded && bHasMovementInput;

    bShouldWalkRun = bWantsGroundedMovement && !bUseSprint;
    bShouldSprintLoop = bWantsGroundedMovement && bUseSprint;

    bIsStopping = bIsGrounded && !bHasMovementInput && bIsMoving;
    bShouldBeIdle = bIsGrounded && !bHasMovementInput && !bIsMoving;
}
```

코드 순서별 의미:

1. `bUseSprint = ... == Sprint`: 이번 프레임 허용 gait가 Sprint인지 비교한다. Player의 private bSprintRequested를 읽지 않는다. 요청이 있어도 게임플레이 상한이 Run이면 false여야 하기 때문이다.
2. `if (!bIsMoving)`: 수평 속도가 기존 움직임 기준인 3 cm/s 이하라면 Run pose 선택 기억을 지운다. 정지 후 다음 출발이 이전 Run 선택 때문에 시작부터 Run으로 보이지 않게 한다.
3. `else if (bUseRun)`: 대입 전의 멤버값, 즉 직전 업데이트의 선택을 검사한다. 별도 bWasUsingRun 변수가 필요 없다.
4. `GroundSpeed > RunExitSpeed`: Run을 사용하던 중에는 190을 초과하는 동안 유지하고 190 이하에서 해제한다.
5. 마지막 else: 현재 Walk 선택 중이다. 220 이상일 때 Run으로 바꾼다.
6. 비교 결과는 bool이고 대입으로 다음 업데이트까지 기억된다. bUseRun을 함수 첫 줄에서 항상 false로 초기화하면 이 기억이 사라져 히스테리시스가 동작하지 않는다.
7. `const bool bWantsGroundedMovement`: 지상이며 유효한 이동 입력이 있는지다. `&&`는 AND다. 두 전이 조건에서만 공유하는 이번 호출의 중간 결과이므로 지역 const bool이면 충분하다. BP가 직접 읽지 않으므로 UPROPERTY가 아니다.
8. `bShouldWalkRun`: 지상 이동 요청이며 Sprint 모드가 아닐 때다. Walk/Run 중 실제 어떤 pose를 사용할지는 bUseRun이 결정한다.
9. `bShouldSprintLoop`: 지상 이동 요청이며 Sprint 모드일 때다. 같은 요청이 WalkRun과 SprintLoop를 동시에 허용하지 않게 두 조건을 반대로 나눈다.
10. `bIsStopping`: 지상, 입력 없음, 잔여 속도 있음이라는 관측 조건이다. ABP가 지금 Stop 상태라는 뜻이나 Stop 애니메이션이 끝났다는 뜻이 아니다.
11. `bShouldBeIdle`: 지상, 입력 없음, 잔여 속도 없음이다. 이 bool이 true라고 ABP의 모든 원샷을 강제로 끝내지는 않는다. 어떤 전이에서 사용할지는 그래프가 정한다.

### 숫자로 보는 히스테리시스

| 직전 선택 | GroundSpeed | 이번 선택 |
| --- | ---: | --- |
| Walk | 170 | Walk |
| Walk | 200 | Walk |
| Walk | 220 | Run |
| Run | 205 | Run |
| Run | 191 | Run |
| Run | 190 | Walk |
| Walk | 200 | Walk |

190~220 사이에서는 직전 선택을 유지한다. 이처럼 들어갈 기준과 나올 기준을 다르게 두는 것을 히스테리시스라고 한다. 기존 GroundSpeed > 170 하나만 쓰면 Walk 최대 속도 경계의 작은 오차에도 Run이 켜질 수 있다. 새 220/190은 그 경계에서 여유를 두는 시각 튜닝값이다. 실제 Walk 170 / Run 470 제어는 바뀌지 않는다.

### 이번 입력 우선 정책

기존 bShouldWalkRun에는 bIsMoving도 필요했다. 이번 bWantsGroundedMovement는 입력이 들어온 첫 프레임에 아직 속도가 0이어도 지상 이동 pose 진입을 허용한다. Walk/Run에 Start 원샷이 없는 이번 설계에서 입력 응답을 우선한 선택이다.

이 선택은 엔진의 의무 규칙이 아니다. 벽에 막혀 속도가 0인데 입력을 유지하면 이동 pose가 재생될 수 있다. 벽 전용 동작, 외력/행동 잠금, 수영/비행의 그래프는 이번 지상/낙하 단계의 범위가 아니다. 이 조건을 임의로 바꿀 때는 Idle/Stop/이동의 조건 공백도 함께 검토한다.

| 지상 | 입력 | 잔여 속도 | Sprint gait | 기본 조건 |
| --- | --- | --- | --- | --- |
| true | true | 무관 | false | bShouldWalkRun |
| true | true | 무관 | true | bShouldSprintLoop |
| true | false | true | 무관 | bIsStopping |
| true | false | false | 무관 | bShouldBeIdle |
| false | 무관 | 무관 | 무관 | 위 지상 조건 모두 false |

bUseRun과 bUseSprint는 동시에 true일 수 있다. bUseRun은 WalkRun 내부 두 pose의 선택값이고 bUseSprint는 gait 정보이기 때문이다. 서로 배타적이어야 하는 것은 bShouldWalkRun과 bShouldSprintLoop다.

## 5. 기존 UpdateKinematics_AnyThread에서 호출 순서 연결

현재 함수 안의 bShouldWalkRun/bIsStopping/bShouldBeIdle/bUseRun/bUseSprint 계산은 새 함수가 소유한다. 예전 대입을 남겨 두고 새 함수 뒤에서 다시 덮어쓰지 않는다. 현재 함수 전체를 다음 형태로 정리한다.

```cpp
void UKhazanAnimInstance::UpdateKinematics_AnyThread(
    const FKhazanAnimGameThreadData& Snapshot,
    float DeltaSeconds)
{
    (void)DeltaSeconds;

    VelocityWorld = Snapshot.VelocityWorld;
    AccelerationWorld = Snapshot.AccelerationWorld;
    InputAmount = FMath::Clamp(Snapshot.InputAmount, 0.f, 1.f);

    const FRotator ActorYawRotation(0.f, Snapshot.ActorRotation.Yaw, 0.f);
    VelocityLocal = UKismetMathLibrary::LessLess_VectorRotator(
        VelocityWorld, ActorYawRotation);

    GroundSpeed = static_cast<float>(VelocityWorld.Size2D());

    bIsGrounded =
        Snapshot.MovementMode == MOVE_Walking ||
        Snapshot.MovementMode == MOVE_NavWalking;

    bIsFalling = Snapshot.MovementMode == MOVE_Falling;

    bHasMovementInput =
        Snapshot.bMovementAllowed && InputAmount > MovementInputThreshold;

    bIsMoving = GroundSpeed > MovingSpeedThreshold;

    if (bIsMoving)
    {
        MovementDirectionAngle = static_cast<float>(
            UKismetMathLibrary::DegAtan2(VelocityLocal.Y, VelocityLocal.X));
    }
    else
    {
        MovementDirectionAngle = 0.f;
    }

    ResolvedGait = Snapshot.ResolvedGait;
    RotationMode = Snapshot.RotationMode;

    UpdateLocomotionSelection_AnyThread();
    UpdateTransitionData_AnyThread();
}
```

아래 설명을 코드의 순서대로 각 줄에 대응시켜 읽는다.

1. Snapshot은 기존 GameThread 복사본을 const 참조로 읽는다. 여기서 Player/CMC를 다시 가져오지 않는다.
2. `(void)DeltaSeconds`는 현재 초 단위 누적/보간을 하지 않으므로 미사용 매개변수를 명시적으로 무시한다. DeltaSeconds를 0으로 바꾸는 코드가 아니다.
3. VelocityWorld/AccelerationWorld 대입은 이번 관측값을 복사한다. 가속도에서 원래 스틱 기울기를 복원하지 않는다.
4. Clamp는 InputAmount를 0~1로 제한한다. 물리 속도 Clamp가 아니다.
5. ActorYawRotation은 Pitch/Roll을 제외한 Actor 수평 회전이다. Player에서 카메라 기준 입력을 만들 때의 ControlRotation과 역할이 다르다.
6. LessLess_VectorRotator는 월드 속도에 Actor Yaw의 역회전을 적용해 Actor 기준 속도를 구한다. 세계 동쪽으로 이동한다는 사실을 캐릭터 앞/옆/뒤로 해석한다.
7. Size2D는 sqrt(Vx²+Vy²), 따라서 낙하 속도 Vz는 GroundSpeed에 포함하지 않는다. static_cast<float>는 프로젝트 float 데이터로의 명시 변환이다.
8. Walking 또는 NavWalking이면 bIsGrounded=true다. `||`는 OR다. 이미 snapshot에 MovementMode가 있어 새 raw bool이나 GT UObject 접근이 필요 없다.
9. Falling 비교는 기존 낙하 분기를 유지한다. !bIsFalling을 지상 정의로 사용하지 않는다.
10. bHasMovementInput은 프로젝트가 허용한 유효 입력, bIsMoving은 실측 수평 움직임이다. 입력 없이 감속 중일 수 있으므로 서로 대체하지 않는다.
11. DegAtan2(LocalY, LocalX)는 현재 이동 속도의 Actor 정면 대비 각도를 도 단위로 구한다. 새 회전 요청각이나 카메라 방향각이 아니므로 기존 의미를 유지한다. 속도가 작으면 방향이 불안정하므로 0으로 둔다.
12. 이번 프레임 ResolvedGait/RotationMode를 복사한 후 새 선택 함수를 호출한다. 복사 전에 호출하면 지난 gait로 선택할 수 있다.
13. 마지막 UpdateTransitionData는 기존 입력 해제 감지와 Stop 선택 기억을 갱신한다. 새 함수가 이번 bIsStopping을 만든 뒤 호출해야 한다. 순서는 `관측값 → pose/전이 조건 → 기존 진입 이력`이다.

NativeUpdateAnimation/NativeThreadSafeUpdateAnimation/GatherGameThreadData는 다시 만들지 않는다. 새 함수 이름만 선언해 두면 엔진이 자동 호출하는 것이 아니므로 마지막 두 호출의 순서를 직접 연결해야 한다.

## 6. ResetDerivedData_AnyThread 초기화

기존 bool 초기화 영역에 두 줄을 추가한다.

```cpp
bIsGrounded = false;
bShouldSprintLoop = false;
```

기존 bUseRun/bUseSprint/bShouldWalkRun 초기화는 유지한다. 현재 bShouldWalkRun=false가 중복돼 있으므로 한 번만 남겨도 된다. 이 함수는 무효 snapshot/재초기화 시 이전 캐릭터의 파생 결과가 남는 것을 막는다.

RunEnterSpeed/RunExitSpeed는 여기서 220/190으로 다시 대입하지 않는다. 설정값은 ABP Class Defaults를 존중해야 한다. 초기화할 것은 매 프레임 계산되는 상태이지 사용자가 고른 튜닝값이 아니다.

기존 UpdateTransitionData_AnyThread의 bShouldPlayStart=false와 Stop 이력은 유지한다. 이번 단계에서 SprintStart 재생 요청이나 StopGait/StopFoot 필드를 더하지 않는다.

## 7. C++ 반영과 ABP 기본값

1. 새 함수 선언/정의와 호출, 새 변수 선언/초기화를 모두 작성한다. 기존 KismetMathLibrary와 EngineTypes include를 사용할 수 있어 별도 include나 새 C++ 클래스는 필요 없다.
2. 작업한 소스와 에셋을 저장한다. UPROPERTY 추가가 있으므로 에디터 종료 후 KhazanEditor / Development Editor / Win64 빌드와 재실행을 권장한다. 이번 설명에서 어시스턴트가 빌드한 것은 아니다.
3. `/Game/_Art/Kazan/Character/Bluprints/ABP_Player`를 열고 Class Settings에서 Parent Class가 KhazanAnimInstance인지 확인한다.
4. Class Defaults의 Animation / Locomotion / Tuning에서 Run Enter Speed=220, Run Exit Speed=190을 설정한다. BP_KhazanPlayer의 물리 속도 설정 화면과 구분한다.
5. My Blueprint에 상속 변수가 보이지 않으면 패널의 표시 옵션에서 Show Inherited Variables를 켠다. 검색에서 Grounded, Should Sprint Loop, Use Run 등을 찾는다. UPROPERTY의 b 접두사는 표시 이름에서 빠지고 단어 사이에 공백이 들어갈 수 있다.
6. 같은 이름의 Blueprint 변수를 새로 만들지 않는다. C++ 멤버의 Get을 사용한다. 같은 표시 이름의 별도 BP 변수를 만들면 C++이 갱신한 값과 다른 값을 읽을 수 있다.
7. Event Graph에 Cast/GetVelocity/Set 변수 계산을 새로 넣지 않는다. 기존 C++ snapshot 경로가 계산하므로 그래프는 결과를 소비한다.

## 8. 기존 WalkRun과 새 SprintLoop 구성

### 8-1. 정확한 그래프 위치

1. ABP의 AnimGraph에서 기존 `Locomotion` State Machine을 더블클릭한다.
2. Grounded 상태를 더블클릭한다.
3. 내부 `GroundedLocomotion` State Machine을 더블클릭한다.
4. 현재 Idle / Locomotion / Stop 상태가 보인다. 여기서 내부 Locomotion 상태를 선택해 F2 또는 이름 편집으로 `WalkRun`으로 바꾼다. 외부 State Machine의 Locomotion 이름을 바꾸는 것이 아니다.
5. 이 이름 변경은 읽기 편하게 하려는 것이며 기능의 필수 조건은 아니다. 기존 이름을 유지하면 아래 WalkRun 지시를 기존 내부 Locomotion 상태에 적용한다.

### 8-2. WalkRun 내부

현재 두 Sequence Player와 Blend Poses by bool을 유지한다. 새 Blend Space를 만들거나 BS_DAS_Player_WalkRun/BlendSpace1D로 강제 교체하지 않는다.

```text
DAS_Khazan_Walk_Loop ──→ False Pose ┐
                                  ├─ Blend Poses by bool → State Output Pose
DAS_Khazan_Run_Loop  ──→ True Pose  ┘
Get bUseRun          ──→ Active Value
```

1. Walk Player의 Sequence가 `InGame/DAS/Locomotion/Walk/DAS_Khazan_Walk_Loop`인지 확인한다.
2. Run Player의 Sequence가 `InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Loop`인지 확인한다. 이번 기준에는 이미 새 복사본이 연결돼 있다.
3. Bool Blend의 False Pose에 Walk, True Pose에 Run을 연결한다. 화면의 위아래 위치보다 핀 이름을 기준으로 한다.
4. 우클릭으로 C++ `bUseRun`의 Get 노드를 찾아 Active Value에 연결한다. Set이나 별도 속도 비교 노드를 넣지 않는다.
5. True/False Blend Time은 현재의 0.10초를 기준으로 유지한다. bool이 바뀌는 순간 목표 pose가 달라지고 실제 가중치는 그 시간에 걸쳐 바뀐다.
6. Transition Type은 Standard Blend, Blend Type은 현재 Hermite Cubic을 기준으로 시작한다. 아직 Inertialization 노드가 없는 그래프에서 타입만 Inertialization으로 바꾸지 않는다.
7. UE 5.8의 Bool Blend에는 `Child Upate Mode`라는 표기로 보일 수 있는 옵션이 있다. 로컬 엔진 프로퍼티 이름은 실제로 ChildUpateMode이며 기본값 Default다. Default는 비활성 자식을 매번 업데이트하지 않고 활성 변경만으로 강제 리셋하지 않는 방식이다. 이번 loop에는 Default를 유지한다.
8. 예전 버전의 Reset Child on Activation 체크박스와 이 옵션을 혼동하지 않는다. 5.8에서는 ResetChildOnActivate와 AlwaysTickChildren도 별도 선택지지만 이번에는 선택하지 않는다.

이유: bUseRun은 목표 pose만 고른다. 0.10초의 실제 보간과 두 pose 재생은 노드가 한다. AnimInstance에 BlendAlpha 누적 시계를 추가할 이유가 없다. 입력 요청 Run과 실제 속도의 차이 때문에 bUseRun을 `ResolvedGait == Run`으로 무조건 바꾸지 않는다.

### 8-3. SprintLoop 상태

1. GroundedLocomotion의 빈 공간을 우클릭하고 Add State로 `SprintLoop`를 만든다.
2. SprintLoop를 더블클릭한다.
3. Content Browser에서 정확히 다음 시퀀스를 상태 내부 그래프로 끌어 넣는다.

```text
/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Loop
```

4. 생성된 노드가 Sequence Player인지 확인하고 pose 출력 핀을 State Output Pose에 연결한다. Sequence Evaluator를 선택해 Explicit Time으로 직접 재생 시간을 관리하는 단계가 아니다.
5. Loop Animation=true, Play Rate=1.0, Start Position=0을 기준으로 둔다. Start Position 0은 초기 기준이며 동기화가 적용될 때 항상 실제 재생을 0에서 시작한다는 강제 규칙은 아니다.
6. 이 상태에 SprintStart 시퀀스나 Montage를 넣지 않는다. 5단계에서 이 상태 앞에 SprintStart를 삽입한다.

### 8-4. 세 loop의 Sync 설정

Walk/Run은 이미 설정되어 있으므로 확인하고 새 Sprint Player에도 적용한다.

| Player 설정 | 값 | 역할 |
| --- | --- | --- |
| Method | Sync Group | 이름 기반 그룹 동기화 사용 |
| Group Name | Locomotion | 세 loop를 같은 그룹에 포함 |
| Group Role | Can Be Leader | 가중치에 따라 기준 재생 노드가 될 수 있음 |
| Loop Animation | true | 순환 재생 |
| Play Rate | 1.0 | 원래 타이밍을 비교 기준으로 사용 |

Group Name은 재생 노드의 그룹 이름이고 LeftFoot/RightFoot은 시퀀스의 접촉 사건 이름이다. 편집 트랙 LocomotionSync와도 역할이 다르다. 세 이름을 동일 문자열로 바꾸지 않는다.

Walk에는 2개, Run에는 12개, Sprint에는 16개의 marker가 있다. 주기 수가 다르다는 이유로 긴 loop를 자르거나 marker 이름에 번호를 붙이지 않는다. 같은 접촉 의미 사이의 상대적인 위상으로 동기화한다. 실제 경계와 Leader 교체의 자연스러움은 양방향 전환으로 검증해야 한다.

WalkRun/SprintLoop 상태의 Always Reset on Entry는 현재 loop 방식처럼 false를 기준으로 둔다. UE 5.8에서 이것은 빠른 재진입 시 남아 있는 활성 상태를 무조건 강제 리셋하지 않겠다는 의미다. 완전히 비활성화된 상태의 나중 재진입까지 영구히 이전 재생 시간을 보관한다는 보장은 아니다. 현재 마커 위상과 재초기화는 엔진이 처리하며 C++에 재생 시간을 따로 보관하지 않는다.

## 9. InGame 참조만 남기기

### Idle와 공중 임시 pose

1. Idle 상태의 Sequence를 다음으로 교체한다.

```text
/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Idle/CA_P_Kazan_DualAxeSword_Off_Stand
```

2. Loop Animation=true, Play Rate=1, Method=Do Not Sync를 기준으로 둔다. Idle에 보행 marker가 없으므로 loop 그룹에 억지로 넣지 않는다.
3. 외부 Locomotion State Machine의 Airborne_TEMP를 열고 같은 InGame Idle로 교체한다. 기존 Loop Animation=false는 true로 바꿔 긴 공중 체류에서 끝 프레임에 멈추는 임시 문제를 피한다.
4. 이것은 점프/낙하 애니메이션 완성이 아니라 InGame만 사용하는 명시적인 임시 pose다. 외부 시퀀스를 가져오지 않는다.

### 기존 Stop의 참조와 임시 한계

기존 Stop 내부 Bool Blend와 bUseRunStop을 보존한다. 밖의 RT 시퀀스 두 개만 다음 InGame 후보로 연결한다.

| 핀 | InGame/DAS/Locomotion 아래 후보 |
| --- | --- |
| False Pose | Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_LF |
| True Pose | Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_LF |

두 Player의 Loop Animation=false, Play Rate=1, Method=Do Not Sync를 사용한다. Stop 상태 자체의 Always Reset on Entry는 true로 두어 중단 후 빠르게 다시 Stop에 들어갈 때도 원샷을 다시 초기화하게 한다. 이 상태 설정과 Bool Blend의 Child Update Mode는 서로 다른 범위다.

두 후보를 표적 확인한 결과 길이는 각각 10.375초다. Run Stop의 root 표본에는 Y 이동이 있고 Enable Root Motion/Force Root Lock은 현재 false다. 따라서 단순히 Root Motion 추출만 꺼두면 메시가 캡슐 안에서 root 애니메이션을 따라 이동할 수 있다.

현재 CMC 중심 인플레이스 방식으로 이 Run Stop을 임시 사용할 때는 해당 InGame 시퀀스만 열어 Enable Root Motion=false, Force Root Lock=true, Root Motion Root Lock=Ref Pose로 설정하고 시작 자세/오프셋을 미리보기로 확인한다. 이것은 root 트랙을 삭제하거나 프레임을 자르는 작업이 아니다. Walk Stop root 표본은 정지 상태였고, 다른 Start/Turn에 같은 설정을 일괄 적용하지 않는다.

이번에는 아직 다음이 완성되지 않는다.

- LF/RF 지지 발 선택.
- 실제 Sprint 전용 Stop 선택: 현재 bUseRunStop 기반 Run Stop이 임시 경로다.
- 긴 후보의 유효 구간/정지 마무리와 자연스러운 완료 시점.
- 새 입력의 짧은 탭에서 이전 유효 속도를 보존해 Stop을 선택하는 처리.

현재 Stop→Idle의 자동 종료를 보존하면 raw 후보 때문에 약 10.375초 길이의 Stop 상태가 유지될 수 있다. 제어는 아래 재입력 전이가 중단할 수 있어야 한다. 이 길이를 해결하려고 임의로 Play Rate를 올리거나 끝 프레임을 정하지 않고, 4단계에서 실제 자세/발/마무리를 검사해 유효 구간을 결정한다. GroundSpeed가 0이 됐다는 이유만으로 기존 원샷 완주 정책을 제거하지 않는다.

## 10. 상태 전이 연결

### 전이 하나를 만드는 정확한 작업

1. GroundedLocomotion으로 돌아와 출발 상태의 테두리에서 도착 상태로 드래그한다.
2. 생성된 화살표가 출발→도착인지 확인한다. 반대 방향은 별도 화살표다.
3. 화살표를 더블클릭해 Transition Rule을 연다.
4. 아래 표의 C++ bool Get 노드를 만들고 빨간 bool 출력 핀을 Result의 Can Enter Transition에 연결한다.
5. 상태 그래프로 돌아와 화살표를 선택하고 Details의 Duration, Priority Order, Automatic Rule을 확인한다. 조건 계산은 전이 내부, 블렌드 시간/우선순위는 화살표 Details다.
6. 이미 화살표가 있다면 중복으로 만들지 않고 기존 Rule을 교체한다. 특히 현재 비어 있는 Stop→Locomotion을 연결한다.

### 지상 전이표

| 출발 | 도착 | 조건 | Duration 예시 | Priority |
| --- | --- | --- | ---: | ---: |
| Idle | WalkRun | bShouldWalkRun | 0.10 | 2 |
| Idle | SprintLoop | bShouldSprintLoop | 0.10 | 1 |
| Idle | Stop | bIsStopping | 0.10 | 3 |
| WalkRun | SprintLoop | bShouldSprintLoop | 0.15 | 1 |
| WalkRun | Stop | bIsStopping | 0.10 | 3 |
| WalkRun | Idle | bShouldBeIdle | 0.10 | 4 |
| SprintLoop | WalkRun | bShouldWalkRun | 0.15 | 2 |
| SprintLoop | Stop | bIsStopping | 0.10 | 3 |
| SprintLoop | Idle | bShouldBeIdle | 0.10 | 4 |
| Stop | SprintLoop | bShouldSprintLoop | 0.10 | 1 |
| Stop | WalkRun | bShouldWalkRun | 0.10 | 2 |
| Stop | Idle | 기존 Automatic Rule 유지 | 0.08 | 4 |

위 Stop→Idle의 조건은 기존 Automatic Rule을 유지한다는 뜻이다. 그 행에 bShouldBeIdle만 연결해 속도 0에서 원샷을 바로 끝내지 않는다. Automatic Rule은 relevant player의 남은 재생 시간과 설정한 종료 기준을 엔진이 평가한다. 현재 기본 AutomaticRuleTriggerTime의 음수 기준에서는 crossfade 길이를 고려해 종료 블렌드를 시작한다. 4단계에서 선택 클립의 유효 길이와 종료 정책을 정교하게 맞춘다.

그 외 bool 전이에는 Automatic Rule Based on Sequence Player in State=false를 사용한다. 루프의 끝 시간을 기다리는 것이 아니라 입력/관측 조건으로 이동하기 때문이다. Sync Group Name to Require Valid Markers Rule은 None으로 둔다. 이것은 Player의 Sync Group 설정과 다른 진입 제한 옵션이다.

모든 전이는 Standard Blend / 현재 Hermite Cubic을 기준으로 시작한다. Inertialization은 8단계에서 별도 검증하며 현재 Slot 앞뒤에 새 노드를 무조건 넣지 않는다.

Duration=0.15는 전이를 시작하기 전에 0.15초 기다리라는 뜻이 아니다. 조건이 충족되면 전이가 시작되고 그 시간에 걸쳐 pose 가중치가 바뀐다. 경과 시간 t, 전체 시간 T일 때 진행률 u=clamp(t/T, 0, 1)이고, Blend Mode가 u를 가중치 곡선으로 바꾼다. 물리 이동 속도는 이 시간으로 계산하지 않는다.

Priority는 작은 값이 먼저다. Stop에서 재입력으로 이동하는 두 전이를 자동 Idle 종료보다 앞에 둔다. 일반 지상 bool 조건은 서로 배타적이지만 원샷 자동 종료와 재입력은 같은 프레임에 성립할 수 있기 때문이다. 구멍 난 조건을 우선순위 숫자로만 덮는 방식으로 사용하지 않는다.

### 직접 경로가 필요한 이유

- Idle→SprintLoop: 정지 상태에서 L3 요청이 유효한 첫 이동을 받는다. 지금은 loop 직결이며 5단계에서 SprintStart를 앞에 삽입한다.
- SprintLoop→WalkRun: L3 요청이 해제돼도 스틱이 유지되면 정지가 아니라 일반 이동으로 돌아가야 한다.
- Stop→WalkRun / SprintLoop: 정지 클립이 끝나기 전에도 재입력을 받는다. 현재 연결 안 된 Stop→Locomotion을 이 조건으로 완성한다.
- WalkRun/SprintLoop→Idle: 낮은 프레임레이트나 아주 짧은 입력으로 입력 해제와 속도 0이 같은 snapshot에 들어와 bIsStopping을 관측하지 못해도 이동 loop에 갇히지 않게 한다. 짧은 탭의 Stop 재생 품질은 4단계에서 이전 속도 자료로 개선한다.
- Idle→Stop: 착지 후 지상 그래프가 Idle로 초기화됐는데 입력 없이 잔여 수평 속도가 있는 경우 등의 경로 공백을 막는다. 외력/피격용 정식 애니메이션까지 해결한 규칙은 아니다.

### 공중 분리

바깥 Locomotion State Machine으로 돌아가 다음 두 화살표를 확인한다.

| 출발 | 도착 | 조건 | Duration 기준 |
| --- | --- | --- | ---: |
| Grounded | Airborne_TEMP | bIsFalling | 기존 0.10 |
| Airborne_TEMP | Grounded | bIsGrounded | 기존 0.15 |

현재 복귀 규칙의 !bIsFalling은 bIsGrounded Get으로 바꾼다. 물에 들어가거나 비행 모드가 되는 것을 '착지'라고 가정하지 않기 위함이다. 이번 그래프는 Walking/NavWalking/Falling 범위이며 다른 MovementMode용 pose는 별도 설계 대상이다.

두 State Machine의 현재 Max Transitions Per Frame=3, Skip First Update Transition=true, Reinitialize on Becoming Relevant=true는 유지한다. 안쪽 Entry는 Idle에 연결한다. 지상 그래프가 재초기화될 때 현재 이동 요청이 있으면 초기 전이 규칙으로 적절한 이동 상태를 선택한다. 물리/gait를 별도 BeginPlay 이벤트로 ABP에 밀어 넣지 않는다.

## 11. 성능과 소유권 확인

변수 Get을 사용하면 AnimGraph의 member access 최적화에 적합한 형태가 된다. Class Settings의 Warn About Blueprint Usage를 켜고 Compile 결과를 확인할 수 있다. 지원되는 Player/Blend 노드의 번개 아이콘은 해당 접근 경로의 최적화 표시이지 전체 캐릭터가 무조건 워커 스레드에서 실행되거나 비용이 0이라는 뜻은 아니다.

이번 방식은 BP 연산이 무조건 느리다는 주장에 기반하지 않는다. 간단한 bool 부정 등도 최적화 가능한 경우가 있다. 여기서는 사용자의 C++ 파생 데이터 방식을 유지하고 계산의 작성 위치를 한 곳으로 모은다. pose 평가와 blending 자체의 비용은 여전히 있다.

Player가 GetMesh()->GetAnimInstance()로 bool을 Set하는 경로를 추가하지 않는다. AnimInstance가 GT snapshot을 수집한 뒤 자신의 AnyThread 계산 순서에서 갱신한다. 이벤트 그래프/Player/AnimInstance가 같은 필드의 값을 서로 덮어쓰지 않게 한다.

## 12. 검증 순서와 완료 기준

1. C++ 빌드와 ABP Compile/Save를 수행한다. 빈 전이, 없는 변수, 원치 않는 Blueprint 호출 경고를 확인한다. 과거에 저장된 ErrorMsg 문자열과 지금 Compile 결과를 구분한다.
2. PIE에서 ABP Debug Filter를 실제 플레이어로 선택한다. Preview Instance/Class Defaults의 값을 런타임 값으로 오해하지 않는다.
3. GroundSpeed, bHasMovementInput, bIsGrounded, bUseRun, bUseSprint, bShouldWalkRun, bShouldSprintLoop, bIsStopping, bShouldBeIdle을 관찰한다. 상태 그래프의 활성 상태/가중치도 함께 본다.

| 테스트 | 기대 결과 |
| --- | --- |
| 입력 없는 지상 | Idle; 이동 조건 false |
| 약한 스틱, L3 없음 | WalkRun의 Walk pose, 물리 목표 170 |
| 큰 스틱, L3 없음 | WalkRun; 실제 속도 220 이상에서 Run 선택, 물리 목표 470 |
| Run에서 스틱 낮추기 | 목표 170으로 감속, 190 이하에서 Walk 선택 |
| 스틱 유지 중 L3 요청 | SprintLoop로 전이, Sprint loop marker 그룹 참여 |
| Sprint 요청 해제, 스틱 유지 | Stop/Idle을 거치지 않고 WalkRun 복귀 |
| Idle에서 L3 요청 후 이동 | 이번 단계는 SprintLoop 직결; Start는 아직 없음 |
| 이동 입력 해제 | 잔여 속도 있으면 Stop, 같은 snapshot에 이미 멈췄으면 Idle 직접 경로 |
| Stop 도중 일반 이동 재입력 | Stop 종료까지 기다리지 않고 WalkRun 진입 |
| Stop 도중 Sprint 재입력 | SprintLoop 진입; 5단계에서 Start 삽입 |
| 지상 어느 상태에서든 낙하 | 외부 Airborne_TEMP 분기 |
| 이동 입력 유지한 착지 | Grounded 복귀 후 현재 요청에 맞는 이동 상태 |
| 빠른 L3 토글/방향 재입력 | 상태 전이 반복에 갇히지 않고 loop 재동기화 |

Walk→Run과 Run→Walk, Run→Sprint와 Sprint→Run을 각각 여러 보행 위상에서 확인한다. marker가 같은 발 의미로 맞는지, 같은 발이 연속으로 툭 튀는지, Leader 교체 시 재생 속도가 튀는지 본다. 서로 다른 주기 수 자체는 실패 사유가 아니다. marker만으로 foot sliding이 완전히 사라져야 한다고 요구하지 않는다.

Blueprint Watch에서 GroundSpeed=200일 때 bUseRun이 상황에 따라 다를 수 있다. 상승 중 Walk에서 온 200은 false, 감소 중 Run에서 온 200은 true가 의도한 히스테리시스다. ABP가 Stop 원샷을 마무리하는 동안 bShouldBeIdle=true가 될 수도 있다. C++의 조건과 현재 재생 상태가 같은 개념이 아니기 때문이다.

3단계 완료는 기본 지상 loop/동기화/공중 분리와 재입력 경로까지다. 긴 Stop 완주 시간, Sprint Stop 선택, LF/RF, SprintStart, Turn, Foot IK/Stride Warping을 완료로 판단하지 않는다. 다음 4단계에서는 InGame Stop 원샷의 유효 구간과 진입 속도/gait/발 선택을 다룬다.

## 13. 근거와 이번 검증 범위

- [Epic State Machines](https://dev.epicgames.com/documentation/en-us/unreal-engine/state-machines-in-unreal-engine): 상태/전이 구조와 초기화 설정.
- [Epic Transition Rules](https://dev.epicgames.com/documentation/en-us/unreal-engine/transition-rules-in-unreal-engine): bool 조건, Priority Order, Automatic Rule, crossfade, Inertialization 노드 요구.
- [Epic Blend Nodes](https://dev.epicgames.com/documentation/unreal-engine/animation-blueprint-blend-nodes-in-unreal-engine?lang=en-US): Bool Blend의 True/False pose와 Blend Time.
- [Epic Sync Groups](https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine?lang=en-US): 공통 marker와 여러 보행 주기의 동기화.
- [Epic Animation Optimization](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-optimization-in-unreal-engine): member access Fast Path와 Blueprint 사용 확인.
- [Epic Root Motion](https://dev.epicgames.com/documentation/en-us/unreal-engine/root-motion-in-unreal-engine): 추출 비활성 상태의 root 이동과 Force Root Lock.
- 로컬 UE 5.8 AnimNode_BlendListBase.h/.cpp: ChildUpateMode enum과 Default/ResetChildOnActivate/AlwaysTickChildren 동작을 확인했다.
- 로컬 UE 5.8 AnimNode_StateMachine.cpp: 비활성 상태 재진입 또는 Always Reset 설정에서 초기화되는 조건을 확인했다. false를 영구 재생 시간 보존으로 설명하지 않는다.

표적 감사 자료: `Saved/ImportReports/Khazan_InGame_Step3_Baseline_20260907.json`.

제안된 지상/입력/움직임/Sprint bool 16조합에서 지상 조건이 하나만 선택되는지와 220/190 경계의 계산 예를 독립적으로 확인했다. 이것은 C++ 빌드/UE 런타임 검증이 아닌 논리식 검사다. 사용자 보고인 2단계 테스트 완료와 어시스턴트의 읽기 전용 소스/그래프 확인을 구분하며 3단계 구현/빌드/PIE는 사용자 수행 후 검증한다.
