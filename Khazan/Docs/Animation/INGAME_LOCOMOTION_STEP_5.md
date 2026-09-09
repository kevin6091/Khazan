# InGame 로코모션 5단계: SprintStart

## 2026-09-08 안내 범위와 선행 조건

이 문서는 사용자가 따라 구현할 설계/예제다. 아래 C++와 ABP 변경은 어시스턴트가 적용하지 않았다. 현재 Stop 검증은 새 UBT 빌드와 Walk/Run/Sprint의 실제 C++ 진입 데이터 확인까지 완료했다. 이후 확장 PIE 검사와 화면 검증은 디버거/캡처 통신 중단으로 완료하지 못했다. 실행 상태 복구 및 미완료 Stop 확인을 먼저 마친다. 정확한 중단/정리 절차는 `Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md`의 2026-09-08 섹션을 따른다.

현재 준비할 것은 **저속·전방 Sprint 출발 한 개**다. 방향별 Start와 주행 중 가속 Start는 이 기본형 검증 뒤에 확장한다. Walk/Run 자체의 Start를 추가하는 단계가 아니다. Run에서 Sprint로 바뀔 때 정지 출발용 시퀀스를 무조건 재생하지 않는다.

모든 런타임 시퀀스는 `/Game/_Art/Kazan/Animation/InGame` 안에 둔다. CMC가 실제 이동을 담당하고 Start 시퀀스가 끝날 때까지 입력/속도를 막지 않는다.

## 5-1. 먼저 사용할 Start를 검토한다

현재 `InGame/DAS/Locomotion/Sprint`에 존재하는 전방 후보는 다음과 같다.

- `CA_P_Kazan_DualAxeSword_Sprint_Start`
- `CA_P_Kazan_DualAxeSword_Sprint_F_Start_TEST`
- `CA_P_Kazan_DualAxeSword_Sprint_Start_F_LF`
- `CA_P_Kazan_DualAxeSword_Sprint_Start_F_RF`

파일 존재는 확인했지만 이번 중단 전에는 현재 포즈/길이/접촉 적합성까지 새로 확정하지 못했다. `_TEST`, `_LF`, `_RF`라는 문자열만으로 실제 용도를 확정하지 않는다. 기존 감사의 249프레임/10.375초도 현재 모든 후보의 검증 완료 길이로 복사하지 않는다.

1. Content Browser에서 위 InGame 폴더를 열고 후보를 하나씩 더블클릭한다.
2. 재생을 멈추고 0번 프레임의 골반, 무릎, 지지발, 몸의 기울기를 본다. Idle에서 출발하는 자세인지, 이미 달리다가 가속하는 자세인지 구분한다.
3. 미리보기 속도를 0.25배 정도로 낮추고 전체를 본다. 옆/뒤로 재정렬하거나 제자리 회전을 크게 포함한 후보는 이번 직진 기본형에서 제외한다. 미리보기 배속과 저장되는 Rate Scale은 다르다.
4. 마지막에는 정상 Sprint loop와 연결될 수 있는 보행 자세가 있어야 한다. 의미 있는 발 교차/상체 동작을 끝낸 뒤의 정지된 tail만 제거한다. 끝 프레임 숫자는 실제 포즈를 보고 정한다.
5. 적합한 원본을 **같은 InGame Sprint 폴더에 복사**하여 `DAS_Khazan_Sprint_Start_F`로 준비한다. 이 이름은 이번에 준비할 역할명이지 현재 존재/검증 완료된 에셋이라는 뜻이 아니다. 원본 후보는 보존한다.
6. 시퀀스 길이, 첫/마지막 포즈, 최상위 본의 스케일, 골반 높이를 loop와 비교한다. 방향이나 가속 성격이 맞지 않는 클립을 이름만 바꾸어 채택하지 않는다.

### Root Lock에서 꼭 구분할 점

현재 스켈레톤 계층은 `C_P_Kazan → Root → Bip001`이다. Force Root Lock이 고정하는 것은 **실제 최상위 루트 본**이다. 이름이 Root인 자식 본의 애니메이션까지 재귀적으로 지우는 기능은 아니다.

- 현재 정책은 Start도 CMC 구동 인플레이스다. Enable Root Motion=false를 유지한다.
- 최상위에 이동이 정리된 작업본이라면 Force Root Lock=true, Ref Pose를 기본 비교값으로 사용한다. Start/loop 사이에 크기·높이·기준 위치가 튀지 않는지 확인한다.
- 최상위는 고정돼 있는데 자식 Root가 전진하는 후보라면 체크박스만으로 인플레이스가 완성되지 않는다. Stop에서 검증한 최상위 이동 합성 방식처럼 별도의 안전한 베이크/변환 검증이 선행되어야 한다.
- Root 본/전체 본 트랙을 삭제해서 해결하지 않는다. 이전 Stop 변환의 수학/검증 기준은 `STOP_ROOT_TRANSFER_2026-09-08.md`를 참고하되, 그 스크립트의 Stop 대상 목록에 새 Start를 임의 대입해 실행하지 않는다.
- 적합한 인플레이스 Start가 준비되지 않았다면 현재 Sprint loop 직접 진입을 유지한다. 이 문서의 ABP 연결은 자산 준비 후 진행한다.

### Start의 Sync 설정

첫 기능 검증은 Sequence Player를 Do Not Sync로 두고 전이 응답/중복 재생을 확인한다. 단일 출발 시퀀스를 0초부터 시작하는 것이 우선이다.

실제로 loop와 의미가 맞는 좌우 접촉 구간을 확보한 경우에만 LeftFoot/RightFoot 마커를 배치하고 별도로 sync를 검증한다. 이때 Start는 Locomotion 그룹/Always Leader/Override Position When Joining as Leader=true, loop는 Can Be Leader라는 구성이 후속 후보다. 마커가 한 개 있거나 마지막 접촉 이후 구간이라는 이유만으로 완전한 위상 대응을 보장하지 않는다. 무의미한 좌우 마커를 만들어 넣지 않는다.

## 5-2. 클래스별 책임

| 대상 | 이번 역할 | 변경 여부와 이유 |
| --- | --- | --- |
| PlayerController | L3/Move 입력을 Player에 전달 | 이미 연결돼 있으므로 새 Start 명령을 추가하지 않음 |
| KhazanPlayer | L3 요청, Walk/Run/Sprint 목표 속도 | 이미 실제 테스트한 정책을 유지; 시퀀스 종료를 기다리게 만들지 않음 |
| LocomotionComponent | 요청/허용 gait와 이동 의도 | 기존 Intent를 그대로 사용 |
| CharacterMovementComponent | 가속, 감속, 충돌, 실제 이동 | 애니메이션의 재생 길이가 물리 속도를 결정하지 않음 |
| KhazanAnimInstance | 허용된 Sprint 요청의 새 진입을 감지하고 시각적 Start 적용 여부 판단 | 이전 프레임 비교와 진입 기록을 추가 |
| ABP_Player | SprintStart 진입, 원샷 재생, 완료/중단/loop 복귀 | 실제 재생 시간과 현재 state는 ABP가 소유 |

`bShouldSprint`는 '현재 지상에서 Sprint 이동을 원하는가'라는 지속 조건이다. Start 중에도 true일 수 있다. `bShouldPlayStart`는 '이번 애니메이션 update에 새 Sprint 출발을 제안하는가'라는 일회성 조건으로 기존 변수를 재사용한다. 둘은 중복된 gait 저장소가 아니다.

## 5-3. KhazanAnimInstance.h

### 기존 함수 선언을 교체한다

```cpp
void UpdateTransitionData_AnyThread(
    const FKhazanAnimGameThreadData& Snapshot);
```

- 기존 무인자 선언을 위 선언으로 **교체**한다. 같은 이름의 두 선언을 남기는 것이 아니다.
- `void`: 반환값 대신 AnimInstance의 전이 데이터를 갱신한다.
- `const`: 전달된 원시 스냅샷을 수정하지 않는다.
- `&`: 이미 복사해 둔 로컬 Snapshot을 또 전체 복사하지 않고 읽는다. 이 호출 안에서만 사용하며 참조를 멤버에 저장하지 않는다.
- Snapshot이 필요한 이유는 입력 월드 방향과 Actor 회전으로 **요청 방향각**을 계산하기 위해서다. 기존 MovementDirectionAngle은 현재 속도 방향각이므로 대체할 수 없다.

### protected의 전이 데이터에 추가한다

```cpp
UPROPERTY(Transient, BlueprintReadOnly,
    Category = "Animation|Locomotion|Transition")
float SprintStartEntrySpeed = 0.f;

UPROPERTY(Transient, BlueprintReadOnly,
    Category = "Animation|Locomotion|Transition")
float SprintStartEntryAngle = 0.f;
```

- `SprintStartEntrySpeed`: 새 지상 Sprint 요청을 감지한 순간의 보수적인 진입 속도, cm/s다. 매 프레임 속도가 아니라 그 요청의 기록이다.
- `SprintStartEntryAngle`: 그 순간 Actor 정면에 대한 입력 방향의 yaw 차이, degree다. 양/음 부호는 우/좌를 나타낸다.
- `Transient`: 실행 중 관측값을 저장 에셋의 상태처럼 보존하지 않는다.
- `BlueprintReadOnly`: BP가 표시/소비할 수 있으나 BP에서 임의로 덮어쓰게 하지 않는다.
- `0.f`: float 초기값이다. 실제 진입 기록은 새 요청 때 덮어쓴다.
- Start를 재생하지 않고 loop로 fallback한 요청의 값도 기록된다. 디버깅 시 왜 허용 범위 밖이었는지 확인할 수 있다.

### protected의 튜닝 값에 추가한다

```cpp
UPROPERTY(EditDefaultsOnly, BlueprintReadOnly,
    Category = "Animation|Locomotion|Tuning",
    meta = (ClampMin = "0.0"))
float SprintStartMaxEntrySpeed = 220.f;

UPROPERTY(EditDefaultsOnly, BlueprintReadOnly,
    Category = "Animation|Locomotion|Tuning",
    meta = (ClampMin = "0.0", ClampMax = "180.0"))
float SprintStartMaxEntryAngle = 45.f;
```

- 220 cm/s와 45도는 **이 기본형을 시험하기 위한 예시**다. 아직 검토하지 않은 Start에 최적이라고 검증한 값이 아니다.
- 속도 상한은 정지 출발용 클립을 이미 빠르게 달리는 몸에 끼워 넣지 않기 위한 적용 범위다. CMC의 MaxWalkSpeed를 제한하지 않는다.
- 각도 상한은 직진 출발 시퀀스를 큰 측면/후방 요청에 사용하지 않기 위한 범위다. 이번에는 범위를 벗어나면 Sprint loop로 즉시 이동한다.
- `EditDefaultsOnly`: ABP Class Defaults에서 캐릭터별 기본값을 조정한다. 개별 Actor 인스턴스마다 저장할 값은 아니다.
- `ClampMin/ClampMax`는 에디터 편집 범위다. C++ 실행 중 모든 대입을 자동 검증하는 장치가 아니다.

### private의 이력에 추가한다

```cpp
bool bHadGroundedSprintRequest = false;
bool bWasGrounded = false;
```

- 첫 변수는 **이전 애니메이션 update**의 '지상 + 이동 입력 + 허용된 Sprint 요청'을 저장한다. 이것과 현재 값을 비교해 false→true만 감지한다.
- 둘째 변수는 이전 update에도 지상이었는지 저장한다. 공중에서 Sprint 입력을 유지하고 착지한 것을 새로운 지상 출발로 오해하지 않게 한다.
- 기존 `bHadGroundedMovementInput`은 지상+이동 입력을 저장한다. Idle에는 입력이 없으므로 이것만으로 이전 지상 여부를 알 수 없다.
- 둘 다 BP가 소비할 값이 아닌 비교용 구현 상세라 private이며 UPROPERTY도 필요하지 않다. UObject 포인터가 아닌 단순 bool이다.
- 이력 소유자는 AnimInstance다. Player에 애니메이션 프레임 이력을 넣으면 입력 처리와 화면 재생의 갱신 주기를 혼합하게 된다.

## 5-4. cpp의 호출 한 줄을 바꾼다

`UpdateKinematics_AnyThread` 마지막의 기존 호출을 다음으로 바꾼다.

```cpp
UpdateTransitionData_AnyThread(Snapshot);
```

속도/지상 여부/gait 선택 계산 **이후**에 호출한다. 현재 값이 준비되기 전에 전이를 계산하면 이전 프레임의 사실과 현재 원시 데이터를 섞게 된다. 게임 스레드에서 수집한 UObject를 이 함수 안에서 다시 조회하지 않는다.

## 5-5. 전이 함수 전체 예제

현재 Stop 계산을 보존한 교체 예제다. Player/Controller에서 이 함수를 호출하지 않는다.

```cpp
void UKhazanAnimInstance::UpdateTransitionData_AnyThread(
    const FKhazanAnimGameThreadData& Snapshot)
{
    bShouldPlayStart = false;
    bShouldEnterStop = false;

    const bool bHasGroundedSprintRequest =
        bIsGrounded &&
        bHasMovementInput &&
        ResolvedGait == EKhazanGait::Sprint;

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
            StopEntrySpeed = FMath::Max(PreviousGroundSpeed, GroundSpeed);
            StopGait = PreviousLocomotionGait;
            StopEntryFoot = SelectStopEntryFoot_AnyThread();
        }

        const bool bJustRequestedGroundedSprint =
            bHasGroundedSprintRequest && !bHadGroundedSprintRequest;

        if (bJustRequestedGroundedSprint && bWasGrounded)
        {
            SprintStartEntrySpeed =
                FMath::Max(PreviousGroundSpeed, GroundSpeed);

            const FRotator InputRotation =
                UKismetMathLibrary::MakeRotFromX(Snapshot.MoveInputWorld);

            const FRotator ActorYawRotation(
                0.f, Snapshot.ActorRotation.Yaw, 0.f);

            SprintStartEntryAngle = static_cast<float>(
                UKismetMathLibrary::NormalizedDeltaRotator(
                    InputRotation, ActorYawRotation).Yaw);

            bShouldPlayStart =
                SprintStartEntrySpeed <= SprintStartMaxEntrySpeed &&
                FMath::Abs(SprintStartEntryAngle) <= SprintStartMaxEntryAngle;
        }
    }

    bHasPreviousKinematicFrame = true;
    bWasMoving = bIsMoving;
    bHadGroundedMovementInput = bIsGrounded && bHasMovementInput;
    PreviousGroundSpeed = GroundSpeed;
    PreviousLocomotionGait = LocomotionGait;
    bHadGroundedSprintRequest = bHasGroundedSprintRequest;
    bWasGrounded = bIsGrounded;
}
```

### 코드 문장별 의미

1. 함수 정의의 클래스 이름/매개변수 형식을 헤더와 일치시킨다. 기존 무인자 구현을 남기지 않는다.
2. `bShouldPlayStart=false`: 지난 update의 일회성 요청을 지운다. Start state를 강제로 종료하는 코드가 아니다.
3. `bShouldEnterStop=false`: 같은 이유로 Stop 진입 신호도 초기화한다. Stop의 재생 진행은 ABP가 계속 담당한다.
4. `bHasGroundedSprintRequest`: 세 조건이 모두 참인 현재의 지속 요청이다. `&&`는 모두 만족해야 true이며 앞 조건이 false이면 뒤 조건 평가를 생략할 수 있다.
5. `ResolvedGait == Sprint`: 실제 허용 상한이 반영된 요청만 인정한다. L3를 누르지 않았는데 속도가 높다는 이유로 Start를 재생하지 않는다.
6. `if (bHasPreviousKinematicFrame)`: 초기값을 실제 과거 프레임처럼 비교하지 않는다. 첫 유효 update에서는 기준 이력만 준비하고 직접 loop 진입은 기존 경로가 처리한다.
7. `bHadGroundedMovementInput && !bHasMovementInput`: 이전의 지상 입력이 이번에는 없어졌는지 확인한다. `!`는 bool 부정이다.
8. Stop의 세 조건과 `bWasMoving || bIsMoving`은 현재 검증한 정책을 유지한다. `||` 때문에 이번 속도가 이미 0이어도 직전 움직임으로 진입할 수 있다.
9. StopEntrySpeed의 Max는 두 값 중 큰 값을 취해 해제 update의 감속 손실을 보완한다. 미래 제동 거리를 예측하는 식은 아니다.
10. StopGait/StopEntryFoot은 해당 진입 때 고정한다. Sprint의 Foot 값은 기록되어도 단일 Sprint Stop 분기에서는 시퀀스 선택에 사용하지 않는다.
11. `bHasGroundedSprintRequest && !bHadGroundedSprintRequest`: 현재 true/이전 false일 때만 새 요청이다. 이전 true/현재 true인 유지 입력에서는 false다.
12. `&& bWasGrounded`: 착지로 인해 지속 요청이 false→true가 된 경우를 제외한다. 공중 처리는 바깥 state machine의 분기를 유지한다.
13. SprintStartEntrySpeed의 Max는 직전 또는 현재가 이미 빠르면 정지 출발을 피하기 위한 보수적인 검사다. 예를 들어 470→430이면 470으로 검사한다.
14. `MakeRotFromX`: 입력 벡터 방향을 X축(정면)으로 바라보는 회전을 만든다. 이 경로는 유효 입력이 있을 때만 실행한다. 현재 Intent는 평면 입력이므로 회전에서 yaw가 필요한 정보다.
15. `ActorYawRotation(0, Yaw, 0)`: 캐릭터 회전의 pitch/roll을 빼고 수평 정면만 사용한다. 땅의 기울기를 요청 방향각으로 섞지 않는다.
16. `NormalizedDeltaRotator(InputRotation, ActorYawRotation)`: 입력 yaw에서 Actor yaw를 뺀 최소 회전 차이를 얻는다. 179도와 -179도를 단순 차이 358도로 해석하지 않는다.
17. `.Yaw`: Rotator의 수평 회전 성분만 선택한다.
18. `static_cast<float>`: 회전에서 얻은 스칼라를 멤버 float 형식으로 명시적으로 변환한다.
19. `FMath::Abs`: 직진 범위 검사에는 왼쪽 -30도와 오른쪽 +30도를 같은 크기 30도로 취급한다. 방향별 선택을 구현할 때는 원래 부호 있는 EntryAngle을 사용한다.
20. 마지막 `bShouldPlayStart` 대입: 속도와 방향이 준비된 단일 클립 범위 안일 때만 이번 Start 진입을 허용한다. 범위 밖에서도 기존 bShouldSprint는 true여서 loop fallback이 가능하다.
21. 마지막 이력 대입들은 **모든 비교가 끝난 뒤** 수행한다. 앞에서 현재 값으로 덮어쓰면 현재와 현재를 비교하여 edge가 사라진다.
22. 새 이력 두 개도 같은 위치에서 저장한다. Start가 재생되지 않은 Sprint 요청도 이력상 소비된다. 그 상태에서 속도/각도만 변했다고 뒤늦게 Start가 튀어나오지 않는다.

### 수치 예시

| 상황 | 과거 요청→현재 요청 | 진입 속도/각도 예 | 결과 |
| --- | --- | --- | --- |
| 지상 Idle에서 전방 Sprint | false→true | 0→30 cm/s, 0도 | Start 후보 |
| Walk 중 L3 | false→true | 170→200 cm/s, 10도 | Start 후보 |
| 이미 Run 중 L3 | false→true | 470→500 cm/s | 이번 기본형에서는 Sprint loop 직접 진입 |
| Sprint 유지 중 벽에 막힘 | true→true | 600→0 | Start 재발행 안 함 |
| 공중 Sprint 입력 유지 후 착지 | false→true, 이전 지상=false | 임의 | Start 재발행 안 함 |
| 지상에서 반대 방향 Sprint | false→true | 저속, 160도 | 직진 Start 제외, loop fallback |

이 예제는 현재 ABP가 매 프레임 관련 지상 전이를 평가하는 기본 경로를 전제로 한다. 미래에 URO/애니메이션 update 생략/액션에 의한 장시간 graph 비활성화를 도입하면 짧은 pulse를 소비하지 못할 수 있다. 그때 request ID/acknowledgement 또는 상태 진입 콜백을 설계한다. 지금 bool pulse만으로 임의의 비동기 상황까지 exactly-once가 보장된다고 주장하지 않는다.

## 5-6. ResetDerivedData_AnyThread

기존 Reset 함수에 다음 네 줄을 추가한다. 기존 bShouldPlayStart=false는 그대로 둔다.

```cpp
SprintStartEntrySpeed = 0.f;
SprintStartEntryAngle = 0.f;
bHadGroundedSprintRequest = false;
bWasGrounded = false;
```

앞의 두 줄은 이전 Pawn의 표시용 진입 기록을 지우고, 뒤의 두 줄은 이전 인스턴스의 비교 이력을 지운다. Initialize/Uninitialize/invalid snapshot 경로에서 공통으로 사용한다. MaxEntrySpeed/MaxEntryAngle 같은 튜닝 값은 reset하지 않는다. reset 때 기본값을 강제로 대입하면 ABP Class Defaults에서 바꾼 설정을 지워버릴 수 있다.

## 5-7. 빌드 순서

이번에는 헤더 프로퍼티를 추가한다. Live Coding 성공만으로 클래스 기본값/반영/재인스턴싱까지 모두 검증됐다고 보지 않는다.

1. 현재 멈춘 검사 세션부터 위 연속성 문서 절차로 정리한다.
2. 자신의 작업을 저장한 뒤 Editor를 정상 종료한다.
3. KhazanEditor Win64 Development를 빌드한다.
4. Editor를 다시 열고 ABP_Player의 새 속성/변수들이 보이는지 확인한다.
5. ABP 연결 뒤 Compile하고 Compiler Results의 실제 최신 오류를 확인한다. 과거 로그/노드의 오래된 오류 메시지와 새 컴파일 결과를 구분한다.

## 5-8. ABP에 SprintStart를 만든다

경로는 `ABP_Player → AnimGraph → 바깥 Locomotion → Grounded → GroundedLocomotion`이다. 현재 Sprint 상태 이름을 SprintLoop로 바꿀 필요는 없다.

1. GroundedLocomotion 빈 곳에서 Add State를 선택하고 `SprintStart`라고 한다.
2. state 노드를 선택해 Always Reset on Entry=true로 설정한다. 새 출발 때 이전 재생 위치를 이어받지 않도록 한다.
3. SprintStart 내부로 들어가 준비를 완료한 `DAS_Khazan_Sprint_Start_F`를 끌어 Sequence Player를 만든다.
4. Player Pose를 State Result의 Result Pose에 연결한다.
5. Loop Animation=false: 출발을 무한 반복하지 않는다.
6. Start Position=0: 검토한 시퀀스의 처음부터 시작한다.
7. Play Rate=1: 먼저 원래 시퀀스 시간으로 기능을 검사한다. 가속/거리 조정은 나중에 한다.
8. 첫 검증의 Method=Do Not Sync: 없는 접촉 위상을 억지로 상속하지 않는다. 이 설정만으로 발 연결이 완벽해지는 것은 아니다.
9. 기존 GroundedLocomotion 출력 뒤의 Inertialization 연결과 바깥 Airborne_TEMP 분기를 보존한다. 이번 새 전이는 우선 Standard Blend로 개별 설정한다. 노드가 있다는 이유만으로 모든 전이가 자동으로 Inertialization이 되는 것은 아니다.

### 진입 전이

전이 화살표를 더블클릭해 AnimInstance 변수 Get을 Result의 Can Enter Transition에 직접 연결한다. 별도 Event Graph 계산이나 Montage Play를 만들지 않는다. 우선순위의 작은 숫자가 먼저 검사된다. 같은 출발 state 안에서 정한다.

| 출발 | 도착 | 조건 | Priority | 시험 Blend Duration |
| --- | --- | --- | ---: | ---: |
| Idle | Stop | bShouldEnterStop | 1 | 기존값 보존 |
| Idle | SprintStart | bShouldPlayStart | 2 | 0.10 s |
| Idle | Sprint | bShouldSprint | 3 | 기존값 보존 |
| Idle | WalkRun | bShouldWalkRun | 4 | 기존값 보존 |
| WalkRun | Stop | bShouldEnterStop | 1 | 기존값 보존 |
| WalkRun | SprintStart | bShouldPlayStart | 2 | 0.10 s |
| WalkRun | Sprint | bShouldSprint | 3 | 기존값 보존 |
| WalkRun | Idle | bShouldBeIdle | 4 | 기존값 보존 |
| Stop | SprintStart | bShouldPlayStart | 1 | 0.10 s |
| Stop | Sprint | bShouldSprint | 2 | 기존값 보존 |
| Stop | WalkRun | bShouldWalkRun | 3 | 기존값 보존 |
| Stop | Idle | 기존 원샷 완료 규칙 | 4 | 기존값 보존 |

- 새 화살표는 Idle/WalkRun/Stop→SprintStart 세 개다. 기존 화살표는 버리지 않고 조건과 우선순위를 검토한다.
- Start 요청이 true인 프레임에는 bShouldSprint도 true다. Start 전이가 직접 Sprint 전이보다 먼저 검사되어야 한다.
- Start 조건이 false인 고속/큰 방향각에서는 직접 Sprint 전이가 fallback이다.
- Stop에서 재입력이 오면 원샷 완료보다 새 입력을 먼저 처리한다.
- Start를 새로 만들었다고 Sprint→SprintStart 또는 SprintStart→SprintStart 전이를 추가하지 않는다.

### SprintStart의 종료/중단 전이

| 도착 | 조건/설정 | Priority | 시험 Blend Duration |
| --- | --- | ---: | ---: |
| Stop | bShouldEnterStop | 1 | 0.10 s |
| WalkRun | bShouldWalkRun | 2 | 0.10 s |
| Idle | bShouldBeIdle | 3 | 0.10 s |
| Sprint | Automatic Rule Based on Sequence Player in State=true, Trigger Time=-1 | 4 | 0.10 s |

1. Start 도중 이동 입력을 놓으면 Stop 진입 데이터를 기존 함수가 만든다. Start가 끝날 때까지 조작을 막지 않는다.
2. L3만 해제하고 이동은 유지하면 WalkRun 조건이 참이 되어 Start를 중단한다.
3. 출발 직후 아직 움직이지 못한 상태에서 입력을 취소하면 Stop 조건은 거짓일 수 있다. Idle 경로가 안전한 취소 경로다.
4. 모두 아니고 Start가 끝나면 Sprint loop로 전이한다.
5. SprintStart→Sprint에 bShouldSprint만 연결하면 Start 진입 때 이미 참이라 원샷을 곧바로 빠져나올 수 있다. 원샷 완료는 남은 재생 시간/Automatic Rule로 처리한다.
6. Trigger Time=-1은 이 전이의 Crossfade Duration을 기준으로 끝 근처에 전이를 시작하는 설정이다. 음수 시간만큼 기다리는 C++ 타이머가 아니다. 예를 들어 실제 길이 0.8초, rate 1, duration 0.1초라면 끝 약 0.1초 전부터 연결되는 것을 예상해 확인한다.
7. bShouldPlayStart가 다음 update에서 false가 되었다는 이유로 Start를 끝내는 화살표는 만들지 않는다. 그 변수는 입장 신호다.
8. 공중 진입은 기존 상위 Grounded→Airborne_TEMP 경로가 처리한다. 각 지상 상태마다 같은 공중 논리를 복사하지 않는다.

## 5-9. 구현 후 확인할 순서

1. Idle→Walk/Run: Start가 나오지 않는지 확인한다.
2. 저속 전방 이동 중 L3: SprintStart가 한 번 나오고 Sprint로 끝나는지 확인한다.
3. L3/Sprint 입력 유지 5초 이상: Start 반복이 없는지 확인한다.
4. Run 470에서 L3: 이번 저속 기본형에서는 Start 없이 Sprint loop로 가는 것이 정상이다. 나중에 주행 중 가속 시퀀스를 준비해 확장한다.
5. Start 초반/중간/끝에서 이동 입력 해제: Stop 또는 아직 미이동이면 Idle로 나와야 한다.
6. Start 중 L3만 해제: 입력은 유지되므로 WalkRun으로 나와야 한다.
7. Stop 초반과 후반에서 저속 전방 Sprint 재입력: 원샷 종료를 기다리지 않아야 한다.
8. Start 중 점프/낙하와 Sprint를 유지한 착지: 상위 공중 경로가 적용되고 착지만으로 Start가 다시 나오지 않아야 한다.
9. 저프레임/벽 접촉: 속도가 떨어지는 것만으로 Start가 반복되지 않아야 한다. 아주 짧은 입력이 관측 update 사이에 사라지는 경우는 별도 테스트 항목이다.
10. 발 튐 검토: 상태/클립 선택, root 기준 포즈, 실제 CMC 속도와 authored 보폭, 전이/마커를 순서대로 분리한다. Sync Marker와 Root Lock을 Foot IK처럼 취급하지 않는다.

정적 예제식과 사용자 구현 후 실제 빌드/ABP/PIE 검증은 다르다. 이 안내만으로 SprintStart 완료를 기록하지 않는다.

## 근거

- [Epic Transition Rules](https://dev.epicgames.com/documentation/en-us/unreal-engine/transition-rules-in-unreal-engine): 전이 우선순위, 시간 기반 원샷 종료 설정.
- [Epic Blend Nodes](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-blend-nodes-in-unreal-engine): enum 선택과 Standard/Inertialization 구분.
- 로컬 UE 5.8 AnimInstance.cpp/AnimInstanceProxy.cpp: 상태 머신 조회의 실제 anim-node index 의미. 이번 검증 도구 사고의 잘못된 0/1 추측을 재사용하지 않는다.
- 현재 KhazanAnimInstance/Player/LocomotionComponent: 데이터 소유 및 기존 Stop/Sprint 입력 정책.

## 2026-09-08 사용자 결정으로 이 단계 적용 취소

- 사용자가 Sprint를 포함한 모든 Start 모션을 제외하기로 확정했다. 이 문서의 SprintStart 변수/함수/에셋/ABP 예제는 더 이상 적용 대상이 아니다.
- 예제를 작성했다는 사실은 실제 구현 완료를 의미하지 않는다. 현재 C++는 bShouldPlayStart=false이며 이를 Start 진입 요청으로 다시 활성화하지 않는다.
- 현재 데이터 계약과 다음 작업의 기준은 [LOCOMOTION_CURRENT_IMPLEMENTATION.md](LOCOMOTION_CURRENT_IMPLEMENTATION.md)다. 다음 구현 주제는 기존 번호 6단계 Turn이다.
- 기존 설명은 날짜별 기록 보존 규칙에 따라 남기며, 이번에 게임 코드나 에셋을 변경하지 않았다.
