# InGame 로코모션 마이그레이션

## 2026-09-07 사용자가 확정한 기준

- 런타임에서 선택하는 Animation Sequence는 `/Game/_Art/Kazan/Animation/InGame` 아래에 있는 것만 사용한다. 현재 대상 세트는 `DAS/Locomotion`이다.
- Walk와 Run은 별도의 Start 모션을 사용하지 않는다. Idle에서 해당 이동 loop로 블렌드한다.
- Start 모션은 Sprint에만 사용한다. Sprint라는 이름의 클립을 Run Start 역할에 배정하지 않는다.
- Stop, Moving Turn, Turn In Place는 구현 범위에 포함한다.
- 새로 복사한 시퀀스의 현재 프레임과 마커를 기준으로 준비한다. 긴 loop의 여러 보행 주기를 보존하며, 유효한 상체·무기·자세 변화를 단일 주기로 축약하지 않는다.
- 실제 이동은 CharacterMovementComponent, 원시 데이터 수집과 파생 계산은 C++, pose 재생·블렌딩·상태 전이는 Anim Blueprint가 담당한다.
- 작업 방식은 **설계/문서는 어시스턴트가 작성하고, C++/ABP/애니메이션 에셋은 사용자가 설명을 따라 구현**하는 방식이다. 설명에는 변수의 의미, 함수의 책임, 각 코드 줄과 연산의 이유를 포함한다.
- 이 문서를 이후 마이그레이션의 정본으로 사용한다. 아래 단계 번호는 이 문서 안에서만 해석한다.

## 2026-09-07 확인한 실제 기준선

UE 5.8.2에 연결해 `InGame` 경로의 Asset Registry와 로드된 에셋을 읽었다. 기존 저장 리포트에는 새 복사본 정보가 없어 이 경로만 다시 조사했다.

상세 재사용 리포트: `Saved/ImportReports/Khazan_InGame_Locomotion_Audit_20260907.json`.

| 항목 | 확인 결과 |
| --- | --- |
| InGame 에셋 | 64개: Animation Sequence 62개, Level Sequence 2개 |
| Animation Sequence 구성 | 일반 DAS 37개, LockOn 25개 |
| Sync Marker가 있는 Animation Sequence | 0개 / 62개 |
| 공통 Skeleton | `/Game/_Art/Kazan/Character/Meshs/SK_Khazan` |
| 기본 Walk | `Walk/DAS_Khazan_Walk_Loop`: 33프레임 구간, 1.375초 |
| 기본 Run | `Run/CA_P_Kazan_DualAxeSword_Run_F`: 119프레임 구간, 약 4.958333초 |
| 기본 Sprint | `Sprint/DAS_Khazan_Sprint_Loop`: 119프레임 구간, 약 4.958333초 |
| 기본 Idle 후보 | `Idle/CA_P_Kazan_DualAxeSword_Off_Stand`: 249프레임 구간, 10.375초 |
| 위 기본 loop 3개 | 유효 프레임레이트 24 fps, Rate Scale 1, Root Motion 비활성, Force Root Lock 비활성 |
| ABP 기본 이동 | Walk/Run Sequence Player 두 개를 `Blend Poses by bool`로 선택 |
| ABP 동기화 | 위 두 Player 모두 `Method = Do Not Sync`, Group Name 없음 |
| ABP 상태 | Grounded 내부 Idle / Locomotion / Stop, 바깥에 Airborne_TEMP |

`frame_span`은 현재 API에서 얻은 프레임 구간 수다. 0번부터 33번까지 키가 있으면 키 개수는 34개지만 길이는 33 / 24 = 1.375초다. 마지막 프레임 번호, 키 개수, 초 단위를 혼용하지 않는다.

현재 ABP의 Idle와 Airborne_TEMP는 `RT_DAS_Idle`, Stop의 두 Player는 `RT_DAS_Walk_Stop_LF`, `RT_DAS_Run_Stop_LF`를 참조한다. 이 세 에셋은 InGame 밖이므로 새 그래프를 연결할 때 반드시 교체한다. 단순 파일 이름 검색 외에 Sequence Player, Blend Space sample, Slot에서 재생하는 Montage의 segment와 Linked Layer 참조도 확인한다.

현재 소스에서는 다음 항목을 후속 단계에서 맞춰야 한다.

- `KhazanAnimInstance.cpp`: `bShouldPlayStart = bJustStartedMoving && ResolvedGait != EKhazanGait::Walk;`는 Run도 허용하므로 Sprint 전용 규칙과 맞지 않는다.
- `bUseRun`은 현재 `GroundSpeed > 170`으로 계산한다. 과거 설명의 `IsWalking`이라는 심볼이 현재 코드에도 있다고 가정하지 않는다. 그래프가 직접 읽는 파생 bool을 유지하는 원칙은 그대로 사용한다.
- `KhazanPlayer.cpp`: 이동 입력에 170/470을 곱해 AddMovementInput에 넘긴다. 입력 세기와 cm/s 이동 속도를 분리해야 한다.
- `MaxAllowedGait`의 기본값은 Run이다. 현재 입력 바인딩에는 Sprint 요청을 만드는 경로가 없으며, Sprint 단계에서는 요청과 허용 상한을 함께 연결해야 한다.
- `GameThreadData → UpdateKinematics_AnyThread` 구조는 이미 존재한다. 같은 기반 코드를 다시 만드는 단계로 돌아가지 않는다.
- `KhazanGameMode.cpp`는 현재 Cog 창 등록을 담당한다. 이 로코모션의 데이터 계산이나 pose 선택을 GameMode로 옮기지 않는다.

이번 확인은 메타데이터, 그래프 프로퍼티와 기본 loop의 대표 RAW 본 위치 비교까지다. 실제 접지 프레임, 전체 회전/속도/curve의 연속성, BP Compile, 빌드와 PIE는 아직 이번 기준으로 통과했다고 기록하지 않는다.

## 전체 구현 순서

| 단계 | 목적 | 준비/수정 대상 | 완료 기준 |
| --- | --- | --- | --- |
| 1 | 기본 에셋 선정, 루프 범위 확인, 접지 Sync Marker 준비 | InGame의 Idle 후보와 Walk/Run/Sprint loop, 공통 Skeleton | loop 3개의 유효 구간과 경계 검토, 모든 보행 주기에 같은 의미의 LeftFoot/RightFoot 배치, 저장 후 재확인 |
| 2 | 입력·속도·gait와 AnimInstance 데이터 계약 정리 | KhazanPlayer.h/.cpp, KhazanPlayerController.h/.cpp, 기존 LocomotionType/LocomotionComponent, KhazanAnimInstance.h/.cpp | 입력은 무차원 0~1, 속도는 cm/s; Sprint 요청/허용이 작동; 일반 Start 요청 제거; AnyThread는 snapshot 값만 소비 |
| 3 | Start 없는 기본 이동과 동기화 구성 | ABP_Player의 Idle / WalkRun / SprintLoop / 공중 분기 | Idle→Walk/Run 직결, loop 동기화, 모든 연결된 기본 pose가 InGame 참조, 잘못된 Blueprint 계산 없이 데이터 소비 |
| 4 | Stop의 시퀀스 준비와 발에 맞는 전환 | InGame Walk/Run/Sprint Stop, AnimInstance Stop 선택 데이터, ABP Stop | 이동 입력 해제 때 속도/gait/발 상태를 고정; LF/RF 선택 검증; 감속 및 정지 동작 완주; 재입력으로 중단 가능 |
| 5 | Sprint 전용 Start | InGame Sprint Start와 방향별 후보, AnimInstance Sprint 진입 데이터, ABP SprintStart | Sprint 진입 요청을 한 번 소비하고 loop로 복귀; Walk/Run Start 없음; 입력 해제/Sprint 해제/공중 진입 중단 처리 |
| 6 | Turn In Place와 Moving Turn | InGame Walk/Run/Sprint Turn, 입력 방향각과 회전 데이터, 캐릭터 회전 정책, ABP Turn | 좌우와 각도별 선택; 회전 적용 중복 없음; 동일 입력으로 무한 재진입 없음; Stop/이동/공중 복귀 |
| 7 | LockOn 확장 | InGame/LockOn의 Walk/Run 8방향 loop와 Sprint 전이, RotationMode, 방향/속도 Blend Space | 방향각 기준이 일치하고 모든 방향 marker 동기화; LockOn에서도 Start는 Sprint에만 사용 |
| 8 | 최종 속도·전이·액션 통합 검증 | 이동 튜닝, play rate, Inertialization, Slot, 필요 시 IK/Stride Warping | 입력 응답, 접지, 단기 탭, 저프레임, 제동, 회전, 공중 전이, 폴더 밖 참조 검사 통과 |

각 단계는 사용자가 구현한 결과를 확인한 뒤 다음 단계의 구체적인 코드와 그래프를 설명한다. 데이터 세트 교체만 필요하면 같은 그래프를 재사용하고, 무기/자세별 그래프 구조가 달라질 때 Linked Anim Layer를 추가한다. 현재 InGame에 없는 Guard/Flow 애니메이션을 외부 경로에서 가져와 범위를 넓히지 않는다.

### 상태 전이의 목표

| 출발 상태/조건 | 다음 상태 | 설계 의도 |
| --- | --- | --- |
| Idle + Walk 또는 Run 입력 | WalkRun | 출발 원샷 없이 입력에 바로 반응 |
| Idle 또는 WalkRun + 유효한 Sprint 진입 요청 | SprintStart → SprintLoop | Sprint 전용 출발을 한 번 재생; 정지 출발과 주행 중 가속 진입의 클립 적합성은 별도 확인 |
| SprintLoop + Sprint 해제, 이동 입력 유지 | WalkRun | Sprint 해제와 이동 입력 해제를 구분 |
| WalkRun/SprintLoop + 이동 입력 해제 | Stop → Idle | 진입 시 제동 정보를 고정하고 원샷을 재생 |
| Stop + 이동 재입력 | WalkRun 또는 SprintStart | 정지 클립 종료까지 조작을 막지 않음 |
| 이동 중 큰 입력 방향 변경 | MovingTurn → 이동 loop | 속도 방향과 새 의도 방향의 차이를 사용 |
| 저속/정지 + 명시적인 재정렬 목표 | TurnInPlace → Idle 또는 이동 loop | 자유 시점의 카메라 회전만으로 캐릭터를 강제로 돌리지 않음 |
| 지상 상태 + 공중 진입 | Airborne | Stop/Start/Turn보다 상위에서 공중을 분리 |

공중 전용 시퀀스는 현재 이 InGame 세트에서 확인되지 않았다. 준비 전에는 InGame Idle 등을 명시적인 임시 pose로만 사용하고, 점프/낙하 애니메이션까지 완성됐다고 보지 않는다.

### 각 후속 단계에서 지킬 데이터 계약

2단계에서 입력 벡터의 크기는 조작 의도이고 `MaxWalkSpeed` 등은 물리 속도 제한이다. `ResolvedGait`는 허용된 요청 gait이며 실측 속도 구간과 동일한 뜻이 아니다. `bUseRun` 같은 그래프 소비 값은 실측 속도/히스테리시스 또는 선택 정책에 따라 따로 계산한다. 게임 스레드에서 Actor/Movement/LocomotionComponent를 읽고, AnyThread는 값 복사본에서 속도·각도를 계산한다. 함수 이름에 ThreadSafe를 붙이는 것만으로 UObject 접근이 안전해지는 것은 아니다.

3단계에서는 현재 Bool 기반 Walk/Run 분기를 먼저 재사용할 수 있다. 연속적인 속도 샘플 블렌딩을 추가할 경우 일반 Blend Space의 속도축만 사용하고, 이름은 사용자가 정한 `BS_DAS_Player_WalkRun`을 유지한다. Blend Space 1D로 강제 교체하지 않는다. 현재 ABP에 Blend Space가 이미 연결돼 있다고 전제하지 않는다.

4단계에서는 `StopGait`, `StopEntrySpeed`, `StopFoot` 같은 진입 스냅샷을 한 번 결정한다. 제동 중 GroundSpeed가 내려가도 Run Stop이 Walk Stop으로 중간에 바뀌지 않게 한다. 입력이 사라진 한 프레임에 이미 속도가 0이 될 수 있으므로 직전 유효 속도도 보관한다. `GroundSpeed == 0`만으로 Stop 원샷을 즉시 끝내지 않고, 원샷의 종료/블렌드 시점과 재입력을 별도로 처리한다. LF/RF는 파일 이름만 믿지 말고 실제 첫 지지 자세로 매핑한다. Sync Marker는 재생 위상을 맞추며 Stop 클립을 자동으로 골라주지는 않는다. 현재 평가 중인 그룹과 직전 평가 결과를 구분해 엔진의 마커 상태를 소비하고, C++에서 별도 재생 시계를 누적해 위상을 복제하지 않는다.

5단계에서는 `bShouldPlaySprintStart`의 의미를 '유효한 Sprint 진입 요청'으로 정의한다. 단순히 `ResolvedGait == Sprint`인 매 프레임 참으로 만들지 않는다. 정지 출발과 Run→Sprint 진입 모두 후보지만, Start 클립을 실제로 검토해 각 상황에 적합한 것을 배정한다. 입력 방향/진입 gait/선택 클립은 진입 순간 고정하고 요청은 한 번 소비한다. Sprint 루프에서 속도가 낮아졌다고 Start를 다시 재생하지 않는다.

6단계에서는 기존 `MovementDirectionAngle`을 Turn 요청각으로 재사용하지 않는다. 이것은 Actor 정면에 대한 현재 Velocity 각도다. MovingTurn은 평면의 현재 이동 방향과 새 입력 방향을 비교해야 한다. 정지 시에는 속도 방향이 정의되지 않으므로 캐릭터 정면/마지막 유효 방향을 별도로 사용한다. `bOrientRotationToMovement`의 자동 회전, 직접 Actor 회전, 시퀀스 root 회전이 중복 적용되지 않도록 한 번의 회전 정책을 정한다. 표적 확인한 Walk StandTurn에는 실제 root 회전이 있다. 회전 원샷의 원래 회전 곡선을 보존해 분석하고, 인플레이스 재생 시 캐릭터 회전으로 반영할 타이밍과 각도 정책을 검증한다.

## 1단계: 기본 에셋과 Sync Marker 준비

### 1-1. 이번에 사용할 에셋을 고정한다

다음 경로는 모두 `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/` 기준이다. 기존 복사본을 사용하며 또 다른 런타임 폴더를 만들지 않는다.

| 역할 | 상대 경로 | 이번 처리 |
| --- | --- | --- |
| Idle | `Idle/CA_P_Kazan_DualAxeSword_Off_Stand` | 기본 대기 후보로 재생/끝 경계를 확인; 이동 loop용 발 marker는 넣지 않음 |
| Walk loop | `Walk/DAS_Khazan_Walk_Loop` | 유효 구간과 한 주기의 좌우 접촉을 확인 |
| Run loop | `Run/CA_P_Kazan_DualAxeSword_Run_F` | 긴 유효 반복 구간을 보존하고 모든 접촉을 확인 |
| Sprint loop | `Sprint/DAS_Khazan_Sprint_Loop` | 모든 접촉과 전체 상체/무기 주기 확인 |

`Sprint/CA_P_Kazan_DualAxeSword_Sprint_F`도 있지만 기본 루프로는 사용자 가공 이름인 `DAS_Khazan_Sprint_Loop`을 선택한다. 비슷한 이름의 두 시퀀스를 섞어 편집하거나 참조하지 않는다. Run은 현재 이름을 유지한다. 여기서 역할명을 부여하는 것은 에셋 Rename 명령이 아니다.

`Driving_CA_P_...` 두 개의 클래스는 LevelSequence다. ABP Sequence Player에 연결할 Animation Sequence 목록에 넣지 않는다.

이 단계에서는 새 C++ 타입이나 변수가 필요하지 않다. 이후 읽을 '발 접촉 시간' 자체가 아직 없으므로 먼저 시퀀스 데이터의 의미를 확정한다.

### 1-2. 시퀀스 길이와 재생 범위를 확인한다

1. Content Browser에서 위의 정확한 InGame 경로를 열고 시퀀스를 더블클릭한다.
2. Asset Details에서 Skeleton이 `SK_Khazan`인지 확인한다.
3. Rate Scale을 1.0 기준으로 확인하고, 시퀀스의 끝 프레임과 길이를 기록한다. 에디터 미리보기 배속은 0.25배 등으로 낮춰도 된다. 미리보기 배속과 저장되는 Rate Scale은 서로 다른 설정이다.
4. 타임라인을 프레임 단위로 보며 전체 구간을 재생한다. 마지막에 발뿐 아니라 골반, 가슴, 머리, 손과 무기가 멈춘 채 오래 유지되는 구간이 있는지 확인한다.
5. loop의 끝→처음 연결도 반복해서 본다. 자세가 비슷한지와 이동하는 방향/속도까지 자연스러운지를 함께 확인한다.

24 fps에서 프레임 간 시간은 `1 / 24 = 0.0416667초`다. 시간은 `t = f / 24`로 계산한다. 예를 들어 48번 프레임은 2초다. 이는 현재 에셋을 읽어 확인한 값이며 다른 시퀀스에도 무조건 24를 적용하는 규칙이 아니다.

현재 Run의 119프레임 구간을 20프레임으로 축약하지 않는다. 현재 Sprint도 60프레임으로 축약하지 않는다. 여러 보행 주기 동안 상체나 무기 자세가 변할 수 있으므로 긴 유효 구간을 보존한다. PSA 샘플 수만으로 '모든 주기가 완전히 같다'고 판정하지 않는다.

표적 RAW 본 위치 비교에서는 Walk와 Sprint의 시작/끝 대표 본 위치가 일치했다. Run은 일치하지 않았다. 이 사실만으로 Run의 loop가 깨졌다고 확정할 수는 없다. 마지막 키가 다음 루프 직전의 정상 샘플일 수도 있어 끝의 여러 프레임→처음 여러 프레임의 위치·회전·속도를 함께 확인해야 한다. Sync Marker로 이 경계 문제가 자동 수정되지는 않는다.

고정 Tail이 실제로 확인된 경우에만 남길 마지막 프레임을 결정한다. UE 5.8의 프레임 타임라인 우클릭 메뉴에는 `Remove frames in range ...`가 있으며, 뒤쪽 범위를 제거하는 항목의 숫자가 의도한 범위인지 확인하고 실행한다. 앞쪽 제거 메뉴와 혼동하지 않는다. 제거 전후 원샷의 마무리 자세와 loop 경계를 비교한다. 시퀀스가 249프레임이라는 이유만으로 자르지 않으며, 이전 변환본의 `NumRawFrames - 2` 공식을 새 복사본에 일괄 적용하지 않는다.

자르거나 재베이크할 작업은 marker를 넣기 전에 끝낸다. 이후 구간이 바뀌면 이미 기록한 접촉 시간이 달라질 수 있다.

### 1-3. 기본 loop의 root 정책을 확인한다

이번 세 기본 loop는 RAW 평가에서 root의 이동이 없었다. 다음 설정은 이 세 loop를 캡슐 이동에 맞춰 재생하기 위한 기준이다.

| 설정 | 기본 loop 값 | 이유 |
| --- | --- | --- |
| Enable Root Motion | false | 실제 이동은 CharacterMovementComponent가 담당 |
| Force Root Lock | true | Root Motion 추출을 꺼도 root를 기준 위치에 고정 |
| Root Motion Root Lock | Ref Pose | 세 loop에 공통 기준 root를 사용 |
| Rate Scale | 1.0 | 원래 타이밍에서 접촉을 검토 |

각 설정을 적용한 뒤 발 높이와 캐릭터 오프셋이 달라지지 않는지 미리보기로 확인한다. 골반의 상하 운동은 보행 자체이므로 고정하지 않는다. root를 고정하는 것은 발을 지면의 월드 좌표에 고정하는 Foot IK가 아니다.

Stop/Turn/SprintStart에는 이 세 loop의 설정을 일괄 복사하지 않는다. 그 시퀀스를 연결하는 단계에서 root 이동/회전과 시작 오프셋을 먼저 검사하고, 인플레이스 pose와 실제 캐릭터 이동·회전을 함께 맞춘다. 특히 Turn의 root 회전을 고정했다면 애니메이션만으로 캡슐이 회전할 것이라고 기대하면 안 된다.

### 1-4. LeftFoot와 RightFoot의 의미를 정한다

- `LeftFoot`: 캐릭터 자신의 왼발이 내려와 지지하기 시작하는 시점.
- `RightFoot`: 캐릭터 자신의 오른발이 내려와 지지하기 시작하는 시점.
- 기준은 해당 시퀀스를 보는 화면의 좌우가 아니다. Skeleton의 `bip001-l-foot`, `bip001-r-foot`를 확인한다.
- Sync Marker는 '이 시간은 왼발/오른발 접촉이다'라는 타이밍 표지다. 발을 고정하는 기능, 발소리 이벤트, Stop 선택 함수가 아니다.

발이 가장 낮은 순간과 지지를 시작하는 순간은 다를 수 있다. 발목 높이만 보지 말고 발바닥과 발끝, 내려오는 흐름, 체중이 실리는 자세를 함께 본다. 인플레이스 애니메이션의 지지발은 메시 기준으로 뒤로 움직일 수 있다. 메시 공간에서 발의 속도가 0인 프레임만 접지로 고르는 규칙은 사용하지 않는다.

모든 clip에서 같은 사건을 같은 이름으로 표시해야 한다. Walk에는 지지 시작을, Run에는 공중 최고점을 `LeftFoot`으로 쓰면 이름만 같고 의미가 달라진다.

### 1-5. 에디터에서 Sync Marker를 추가한다

먼저 Walk 한 개에 다음 순서를 적용한다.

1. 재생을 멈추고 타임라인의 Notifies 영역을 연다. 영역이 숨겨져 있으면 Animation Sequence Editor의 Timeline/Notifies 트랙 표시를 확인한다.
2. Notifies 헤더의 트랙 추가 기능으로 트랙을 하나 추가하고 `LocomotionSync`로 이름을 정한다. 트랙은 marker를 정리하는 행이다.
3. 0.25배 미리보기와 프레임 단위 이동으로 왼발이 지지하기 시작하는 프레임을 찾는다.
4. 그 시간의 트랙 빈 공간에서 우클릭하고 **Add Sync Marker → New Sync Marker…**로 `LeftFoot`을 추가한다. 이미 Skeleton에 이름이 등록되어 있으면 기존 `LeftFoot` 항목을 선택한다.
5. 오른발 지지 시작에도 같은 방식으로 `RightFoot`을 추가한다.
6. marker의 시간/프레임 위치를 다시 확인한다. 프레임 스냅을 켜고 의도한 프레임에 위치시킨다. 접촉 순간만 표시하며 지지 구간의 모든 프레임에 marker를 만들지 않는다.
7. 시퀀스를 저장한다. 새 marker 이름을 등록해 Skeleton도 수정 상태라면 `SK_Khazan`도 저장한다.
8. 에셋을 다시 열어 marker가 남아 있는지 확인하고, 다음 Run/Sprint에서는 같은 이름을 재사용한다.

`Add Notify → New Notify`에서 이름만 LeftFoot으로 만드는 것은 목적에 맞지 않는다. 일반 Notify의 발소리/이벤트와 Sync Marker의 동기화 역할을 구별한다. Skeleton에 LeftFoot이라는 이름이 남아 있어도 새 복사본의 타임라인에 접촉 위치가 자동으로 채워지지는 않는다.

`LocomotionSync`는 에디터 트랙 이름이고, 3단계에서 지정할 Sync Group 이름 `Locomotion`은 재생 노드를 묶는 이름이다. 두 이름의 문자열이 같아야 하는 관계는 없다. 동기화에 사용되는 공통 marker 이름은 `LeftFoot`, `RightFoot`이다.

### 1-6. 긴 Run/Sprint에는 반복되는 접촉을 모두 넣는다

짧은 Walk의 한 보행 주기라면 보통 LeftFoot/RightFoot 한 쌍이다. 긴 Run/Sprint에는 실제 접촉 수만큼 다음 순서가 반복되어야 한다.

```text
LeftFoot → RightFoot → LeftFoot → RightFoot → ... → 루프 경계
```

`LeftFoot1`, `LeftFoot2`처럼 주기별 다른 이름을 만들지 않는다. 같은 의미의 접촉은 같은 이름을 반복한다. loop 끝과 시작이 같은 시점의 중복 키라면 그 접촉을 두 번 세지 않는다. 지지 중간에 두 번 표기하거나 공중 구간에 표기하지 않는다.

현재 RAW 발 높이를 이용한 표적 검사에서는 아래 구간이 관찰됐다. **접지 확정값이 아니라 미리보기로 찾을 때 참고할 후보**다.

| 시퀀스 | 관찰 | 사용 방법 |
| --- | --- | --- |
| Walk | 왼발 높이의 국소 최소가 여러 개여서 자동 판별이 모호; 오른발은 24 부근에도 최소 | 발바닥/발끝을 직접 보고 지지 시작을 결정 |
| Run | 왼발 높이 최소 9, 29, 49, 69, 89, 109; 오른발은 각 주기마다 15/17 부근 후보 | 보행 약 6주기 후보; 실제 지지 시작은 최소 높이보다 앞설 수 있음 |
| Sprint | 왼발 높이 최소 4, 19, 34, 49, 64, 79, 94, 109; 오른발 11, 26, 41, 56, 71, 86, 101, 116 | 보행 약 8주기 후보; 각 접촉을 미리보기로 검토 |

따라서 현재 길이가 유지되고 관찰과 실제 지지가 일치한다면 Run은 약 12개, Sprint는 약 16개의 marker가 예상된다. 개수를 맞추려고 배치하지 말고 실제 접촉을 먼저 결정한다. 이 후보는 오래된 marker 프레임을 복사한 결과가 아니라 현재 InGame pose에서 측정한 높이 최소다.

### 1-7. 동기화 계산을 이해한다

다음 숫자는 원리를 설명하는 가상 예시이며 실제 InGame 에셋에 입력할 프레임이 아니다.

```text
Walk: LeftFoot 8, RightFoot 24, 현재 16
Run:  LeftFoot 48, RightFoot 58
```

Walk의 두 marker 사이 진행 비율은 `alpha = (16 - 8) / (24 - 8) = 0.5`다. Run의 대응 구간에서 같은 비율의 지점은 `48 + (58 - 48) × 0.5 = 53`이다.

이 계산은 전체 clip의 50%를 일치시키는 것과 다르다. 긴 Run의 여러 보행 주기 중 현재의 LeftFoot/RightFoot 사이를 맞추는 의미다. 실제 UE는 loop 경계, 현재 marker 쌍, Leader/Follower와 통과한 marker도 함께 처리한다. 이 예시 공식을 C++의 별도 위상 시계로 구현하지 않는다.

Marker가 시퀀스에 있어도 현재 ABP의 `Method = Do Not Sync` 상태에서는 노드 사이 동기화가 켜지지 않는다. 3단계에서 Walk/Run Player에 `Method = Sync Group`, `Group Name = Locomotion`, `Group Role = Can Be Leader`를 설정한다. Sprint loop도 같은 의미로 합류한다. Idle와 비순환 원샷을 무조건 같은 그룹에 넣지 않는다.

Blend Space를 사용하면 sample 내부 marker 동기화의 `Allow Marker Based Sync`와 재생 노드 간 Sync Group 설정을 구분해 확인한다. 다중 주기 loop에서 marker 중복은 가능하지만 시작/끝과 Leader 교체의 연속성까지 자동 보증되는 것은 아니므로 Walk↔Run↔Sprint 전환을 양방향으로 검증한다.

### 1-8. 짧은 읽기 전용 검사 함수로 저장 결과를 확인한다

이 코드는 선택 사항인 에디터 검사용 Python이다. 게임의 AnimInstance에서 매 프레임 실행하지 않는다. 시퀀스와 Skeleton에 값을 쓰지 않는다.

사용자가 `Scripts/Animation/inspect_ingame_sequence.py` 파일을 만들고 아래 코드를 작성한다. UE의 `Tools → Execute Python Script`에서 실행한다. 메뉴 명칭은 에디터 언어에 따라 다를 수 있으며 PythonScriptPlugin이 필요하다. 현재 프로젝트에는 활성화되어 있다.

```python
import unreal

INGAME_ROOT = "/Game/_Art/Kazan/Animation/InGame/"

def inspect_sequence(asset_path):
    if not asset_path.startswith(INGAME_ROOT):
        raise ValueError("Animation Sequence must be under InGame")

    sequence = unreal.load_asset(asset_path)
    if not isinstance(sequence, unreal.AnimSequence):
        raise TypeError("Expected an Animation Sequence")

    duration = float(sequence.get_play_length())
    frame_span = int(unreal.AnimationLibrary.get_num_frames(sequence))
    fps = frame_span / duration if duration > 0.0 else 0.0
    markers = unreal.AnimationLibrary.get_animation_sync_markers(sequence)

    print(f"{sequence.get_name()}: {duration:.6f}s, {fps:.3f}fps, markers={len(markers)}")

    for marker in sorted(markers, key=lambda item: float(item.get_editor_property("time"))):
        name = str(marker.get_editor_property("marker_name"))
        time = float(marker.get_editor_property("time"))
        frame = round(time * fps)
        print(f"  {name}: frame={frame}, time={time:.6f}s")

inspect_sequence(INGAME_ROOT + "DAS/Locomotion/Walk/DAS_Khazan_Walk_Loop")
inspect_sequence(INGAME_ROOT + "DAS/Locomotion/Run/CA_P_Kazan_DualAxeSword_Run_F")
inspect_sequence(INGAME_ROOT + "DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Loop")
```

검사 코드의 각 줄은 다음 의미다.

- `import unreal`: 에디터의 Unreal Python API를 사용한다.
- `INGAME_ROOT`: 이번에 허용하는 시퀀스 경로의 접두사다. 끝의 `/`가 있어 `InGameBackup` 같은 다른 폴더를 잘못 허용하지 않는다.
- `def inspect_sequence(asset_path)`: 경로 하나를 받아 시퀀스 길이와 marker 목록을 출력하는 함수를 정의한다. 세 에셋에 같은 검사 코드를 재사용한다.
- `if not ...startswith(...)`: 경로가 InGame 아래인지 검사한다. 이름이 같더라도 폴더 밖이면 오류로 중단한다.
- `raise ValueError(...)`: 잘못된 경로를 조용히 통과시키지 않고 원인을 표시한다.
- `sequence = unreal.load_asset(...)`: 경로로 에셋을 로드해 객체를 얻는다. 복제하거나 저장하지 않는다.
- `if not isinstance(...)`: 로드 실패 또는 `Driving_*` LevelSequence 등 다른 클래스를 걸러낸다.
- `raise TypeError(...)`: Animation Sequence가 아니면 어떤 종류를 기대했는지 출력한다.
- `duration`: 시퀀스의 길이를 초 단위 실수로 보관한다.
- `frame_span`: 현재 AnimationLibrary가 반환한 프레임 구간 수를 정수로 보관한다.
- `fps = frame_span / duration if ...`: 프레임 구간 수를 초로 나눠 현재 시간축의 프레임레이트를 구한다. 길이가 0이면 0을 사용해 0으로 나누는 오류를 피한다.
- `markers = ...get_animation_sync_markers(...)`: 일반 Notify가 아닌 Sync Marker 배열을 읽는다.
- 첫 `print`: 에셋 이름, 길이, fps, marker 개수를 보여준다. `.6f`는 소수점 아래 6자리, `.3f`는 3자리이며 `len(markers)`는 개수다.
- `for ... sorted(..., key=lambda ...)`: marker 시간을 정렬 기준으로 삼아 처음부터 끝 순서로 한 개씩 검사한다. `lambda item`은 각 항목의 time만 꺼내는 작은 함수다. 원본 marker 배열이나 에셋을 수정하지 않는다.
- `name`: marker 이름을 읽어 일반 문자열로 바꾼다.
- `time`: marker가 위치한 초를 읽는다.
- `frame = round(time * fps)`: 초에 초당 프레임 수를 곱해 프레임 위치를 얻는다. 저장된 부동소수점의 작은 오차가 있어 가장 가까운 정수로 반올림한다.
- 두 번째 `print`: 이름·프레임·초를 한 줄씩 표시한다.
- 마지막 세 호출: 허용 루트 문자열과 각 상대 경로를 이어 붙여 Walk, Run, Sprint를 차례대로 검사한다. `+`는 여기서 숫자 덧셈이 아니라 문자열 연결이다.

이 함수의 출력은 marker 위치가 존재하고 저장됐는지 확인하는 자료다. 실제 발이 닿는지, root 설정이 적절한지, loop가 자연스러운지까지 판정하는 검사는 아니다. 편집을 마쳤으면 에셋을 저장하고 다시 열어 목록을 확인한다.

### 1-9. 이번 단계 완료 기준

- 사용할 Idle / Walk / Run / Sprint 시퀀스 경로가 InGame 안에서 고정돼 있다.
- loop 세 개의 전체 구간과 끝→처음 연결을 확인했고, 확인되지 않은 Tail이나 의미 있는 주기를 임의로 제거하지 않았다.
- loop 세 개에 같은 의미의 LeftFoot/RightFoot marker를 배치했다. 다중 주기 시퀀스의 후반 접촉도 빠뜨리지 않았다.
- 적용한 loop root 설정이 원래 보행 자세를 깨지 않는다.
- 시퀀스와 필요 시 Skeleton을 저장했고 다시 열어 marker 위치를 확인했다.
- Stop/Turn/SprintStart 후보는 InGame 안에 존재하는 것으로만 목록을 잡았으며, 각 원샷의 상세 편집은 4/5/6단계에서 한다.

1단계 완료는 에셋의 준비 상태를 뜻한다. 실제 ABP의 동기화와 Stop 선택이 작동한다는 의미는 아니다. 다음은 이미 있는 C++ 입력/스냅샷 구조를 새 gait 정책에 맞추는 2단계다.

## 후속 단계에 사용할 원샷 후보

공통 루트는 `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/`이다. 여기서 후보는 존재를 확인했다는 뜻이고, 최종 유효 길이/발 선택/루트 정책을 검증했다는 뜻은 아니다.

| 역할 | 후보 |
| --- | --- |
| Walk Stop LF/RF | `Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_LF`, `Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_RF` |
| Run Stop LF/RF | `Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_LF`, `Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_RF` |
| Sprint Stop | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_Stop_F`, `Sprint/CA_P_Kazan_DualAxeSword_Sprint_Stop_F_02` |
| Sprint 기본 Start | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_Start` |
| Sprint 전방 발별 후보 | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_Start_F_LF`, `Sprint/CA_P_Kazan_DualAxeSword_Sprint_Start_F_RF` |
| Sprint 방향별 Start | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_{B,BL,BR,FL,FR,L,R}_Start` |
| Walk 제자리 180 Turn | `Walk/CA_P_Kazan_DualAxeSword_Walk_StandTurn_{L,R}_180` |
| Run 제자리/이동 180 Turn | `Run/CA_P_Kazan_DualAxeSword_Run_{StandTurn,MovingTurn}_{L,R}_180` |
| Sprint 이동 90/180 Turn | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_{L,R}_{90,180}` |

중괄호는 문서에서 여러 실제 파일을 묶어 쓴 표기이며 에셋 경로에 그대로 입력하지 않는다. `_02`를 오른발 변형이라고 가정하지 않는다. LockOn의 `_LF_1` 등은 방향 토큰일 수 있으므로 Free Locomotion Stop의 LF/RF 발 이름과 혼동하지 않는다. `_TEST`, `_Hard`는 기본 그래프에 자동으로 포함하지 않는다. 사용 시 역할을 별도로 확인한다.

## 엔진 기능 근거

- [Epic: Sync Groups](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-sync-groups-in-unreal-engine): 그룹의 Leader/Follower, 공통 marker, 동기화 Method.
- [Epic: Animation Notifies](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-notifies-in-unreal-engine): Sync Marker 생성, Skeleton 이름 저장, 타임라인 프레임 위치.
- [Epic: Root Motion](https://dev.epicgames.com/documentation/en-us/unreal-engine/root-motion-in-unreal-engine): Enable Root Motion, Force Root Lock, Root Motion Root Lock의 의미.
- [Epic: Blend Spaces in Animation Blueprints](https://dev.epicgames.com/documentation/en-us/unreal-engine/blend-spaces-in-animation-blueprints-in-unreal-engine): 참조형 Player와 ABP 내부 Blend Space Graph의 차이.
- UE 5.8 로컬 `Engine/Source/Runtime/Engine/Classes/Animation/BlendSpace.h`: `bAllowMarkerBasedSync`, `bShouldMatchSyncPhases` 프로퍼티를 확인했다.

프로젝트 애셋에 관한 수치는 위의 로컬 감사 리포트에서 확인했다. 문서 작성 중 C++, Blueprint, Animation Sequence, Skeleton을 수정하거나 저장하지 않았다.

### 2026-09-07 문서/검사 예제 검증

- 1-8의 Python 코드를 문서에서 그대로 추출해 현재 UE 5.8.2 에디터에서 실행했다. 세 시퀀스 로드와 길이/fps/marker 개수 출력이 성공했으며, 현재 marker 개수는 각각 0이다.
- `Tools → Execute Python Script...` 메뉴는 로컬 UE 5.8 `PythonScriptPlugin.cpp`의 `LevelEditor.MainMenu.Tools` 등록으로 확인했다.
- 감사 리포트의 64개 에셋 경로가 모두 파일시스템에 존재함을 확인했다. 이 중 Animation Sequence는 62개이며, ABP의 InGame 밖 고유 시퀀스 참조는 3개다.
- 변경된 기존 문서에 대해 `git diff --check`를 통과했다. 이번 결과는 사용자 구현 완료나 런타임 동작 검증을 의미하지 않는다.

## 2026-09-07 입력 정책 확정: 스틱 2단 고정 속도와 L3 Sprint

사용자는 왼쪽 스틱의 기울기로 Walk/Run 두 가지 속도 모드를 고르고, Sprint는 L3 버튼을 눌렀을 때만 가능하도록 요청했다. 이후 2단계와 5단계는 아래 정책을 따른다.

| 조건 | 기본 이동 모드 | 설정할 속도 |
| --- | --- | --- |
| 유효 입력 없음 / 데드존 안 | 이동 입력 중단 | 기존 감속으로 정지 |
| 유효 입력 있음, Run 임계값 미만, Sprint 요청 없음 | Walk | 170 cm/s |
| Run 임계값 이상, Sprint 요청 없음 | Run | 470 cm/s |
| 유효 이동 입력 + L3에 의해 생성된 Sprint 요청 + 게임플레이 허용 | Sprint | SprintSpeed; 수치는 아직 미정 |

- 스틱을 끝까지 밀어도 L3에 의한 요청이 없으면 Sprint로 진입하지 않는다.
- Walk/Run의 속도는 스틱 기울기에 연속 비례시키지 않는다. 같은 모드 안에서는 목표 속도가 각각 170/470으로 일정하다.
- 고정 속도는 CharacterMovementComponent의 목표/최대 이동 속도를 뜻한다. 기존 MaxAcceleration/Braking에 의한 가감속, 충돌과 공중/전이 상태의 속도 변화는 계속 처리한다. 매 프레임 Velocity를 강제로 170/470 크기로 덮어쓰는 방식은 이번 계획에 포함하지 않는다.
- Run 임계값은 아직 사용자 확정 수치가 없다. 설명에 사용하는 0.6 등은 예시다. 데드존 처리 후, 방향 정규화 전에 측정한 0~1 입력 크기를 기준으로 비교한다.
- L3의 유지 방식(한 번 눌러 유지하는 토글 / 누르는 동안 유지)은 별도 선택 사항이다. 현재 답변 대기 상태이며 어느 쪽도 확정된 사용자 정책으로 기록하지 않는다. SprintSpeed도 임의로 600/750 등으로 확정하지 않는다.

### 입력의 크기, 방향, 속도를 각각 보관하는 이유

```text
IA_Move의 Axis2D 값
    → 데드존과 축 처리
    → 정규화 전 기울기 크기: Walk/Run 선택 및 Intent.InputAmount
    → 정규화한 월드 방향: AddMovementInput(Direction, 1.0)

L3 입력
    → Sprint 요청 상태
    → 이동 입력 및 게임플레이 허용 여부와 결합

선택/허용된 gait
    → CharacterMovementComponent.MaxWalkSpeed = 170 / 470 / SprintSpeed
```

`Intent.MoveInputWorld`에는 크기가 남은 월드 입력을 전달해 `SetMoveInputWorld()`가 InputAmount를 보존하게 한다. `AddMovementInput()`에는 유효 입력이 있을 때만 단위 방향과 ScaleValue 1을 전달한다. 두 소비자에게 서로 다른 크기의 벡터를 주는 것은 의도적이다. 하나는 조작 의도를 기록하고, 다른 하나는 선택된 속도 모드로 이동하도록 한다.

예를 들어 입력 크기가 0.2여도 Walk가 선택되면 이동 컴포넌트에는 크기 1의 입력을 전달하고 MaxWalkSpeed를 170으로 설정한다. 이때 목표 속도는 170 × 0.2가 아닌 170이다. Intent.InputAmount는 여전히 0.2로 남아야 한다.

입력을 먼저 정규화한 다음 Run 임계값을 비교하면 모든 유효 입력의 크기가 1이 되어 Walk/Run을 구분할 수 없다. 순서는 기울기 측정 → gait 선택 → 이동용 방향 정규화다. 데드존 안의 입력은 정규화하지 않고 이동 입력을 중단한다. 카메라 기준 축 변환은 현재 `MovementInput.X = Forward`, `MovementInput.Y = Right` 계약을 기준으로 검토한다.

### 현재 소스에서 확인한 차이

`KhazanPlayer::HandleInputMove()`에는 다음 코드가 있다.

```cpp
if (MovementInput.Length() <= 170.f)
{
    ResultMovement.Normalize();
    ResultMovement *= 170.f;
}
else if (MovementInput.Length() > 170.f)
{
    ResultMovement.Normalize();
    ResultMovement *= 470.f;
}
```

이 코드는 입력의 무차원 크기를 속도 수치 170과 비교한다. 확인한 IA_Move는 Axis2D이며 action modifier가 없고, IMC_Default의 Move 기본 매핑에는 Swizzle만 있었다. 따라서 현재 설정의 스틱 입력 크기에 170을 Run 임계값으로 사용할 수 없다. `Normalize()` 뒤의 170/470 곱셈도 입력 ScaleValue를 크게 만들 뿐 실제 목표 속도를 지정하지 않는다.

로컬 UE 5.8의 `ScaleInputAcceleration()`은 입력 크기를 최대 1로 제한하고 MaxAcceleration을 곱한다. 그 결과 170과 470처럼 이미 1을 넘은 입력은 같은 최대 입력으로 처리된다. 실제 Walk/Run 고정 속도는 이동 컴포넌트의 MaxWalkSpeed로 적용한다. 이 변수는 이름에 Walk가 있어도 지상에서 달리는 속도 제한에도 사용된다.

현재 LocomotionComponent도 `SetMoveInputWorld()`에서 벡터를 최대 길이 1로 제한한다. 따라서 크기 170/470인 벡터를 여기에 넘기면 원래 기울기 크기가 사라진다. 사용자 의도인 고정 속도는 유지하면서, 입력 세기와 이동 속도를 서로 다른 데이터로 전달하도록 고친다.

### 2단계에 추가할 변수/역할

| 이름 | 용도 | 확정 여부 |
| --- | --- | --- |
| WalkSpeed | Walk 최대 속도 | 170 cm/s 확정 |
| RunSpeed | Run 최대 속도 | 470 cm/s 확정 |
| SprintSpeed | Sprint 최대 속도 | 수치 미정 |
| RunInputThreshold | 스틱 크기로 Walk/Run 선택 | 수치 미정; 0~1 기준 |
| InputAmount | 데드존 처리 후의 조작 크기 | 기존 Intent 값 보존 |
| MoveDirection | 이동 컴포넌트에 전달할 평면 단위 방향 | 유효 입력일 때만 사용 |
| bSprintRequested | L3로 만들어진 Sprint 의도 | 토글/홀드의 저장 방식은 선택 후 확정 |
| TargetGait / ResolvedGait | 요청 gait와 게임플레이 상한 반영 결과 | 기존 구조 활용 |

걷기/달리기 요청이 바뀌어도 ABP는 GroundSpeed와 입력 여부를 함께 소비한다. 정지 클립은 입력 해제 시의 속도/모드/발을 고정해 선택하며, 속도가 임계값을 내려갔다고 재생 중인 Stop을 교체하지 않는다. 스틱의 모드 변경 자체는 Start 재생 요청이 아니다.

### L3 연결 준비

- `IA_Sprint`: Digital(bool) Input Action으로 준비한다.
- `IMC_Default`: `Gamepad Left Thumbstick Button`에 연결한다. 엔진 키는 `EKeys::Gamepad_LeftThumbstick`이며 PlayStation 표시명이 L3다. `Gamepad_Left2D`는 스틱 기울기 축이므로 서로 구분한다.
- `KhazanGameplayTags.h/.cpp`: `Input_Action_Sprint` / `Input.Action.Sprint`를 추가하는 계획이다.
- 기존 `KhazanInputData`의 InputActions 목록에 해당 tag와 IA_Sprint를 연결해야 한다. 현재 코드가 이 목록으로 액션을 조회하므로 IMC만 추가해서는 충분하지 않다.
- PlayerController는 L3 이벤트를 Player에게 전달하고, Player/Locomotion 계층이 이동 여부와 게임플레이 허용 조건을 반영한다.
- 현재 MaxAllowedGait 기본값 Run은 Sprint를 차단한다. 일반 상태의 허용 상한과 L3 요청을 별도로 관리한다. L3가 게임플레이 제한을 강제로 Sprint까지 풀어서는 안 된다.
- 스틱 입력이 변하지 않은 상태에서 L3를 눌러도 gait/속도가 갱신되도록 공통 갱신 경로를 사용한다. 이동 입력 콜백만으로 Sprint 변화를 처리하지 않는다.

### 이번 변경 범위와 검증

입력 정책과 후속 구현 계획을 문서에 추가했다. 사용자가 직접 구현하는 진행 방식에 따라 C++/IMC/IA/ABP는 수정하지 않았다. 확인 범위는 현재 소스, IA_Move/IMC_Default 프로퍼티, UE 5.8 이동 입력 처리와 L3 키 정의다. 컨트롤러의 실제 런타임 입력값이나 PIE 고정 속도는 이번에 측정하지 않았다.

## 2026-09-07 사용자 구현 재검토: loop marker와 HandleInputMove

앞선 기준선은 당시의 기록으로 보존하며, 현재 상태는 이 섹션을 우선한다.

- 사용자가 새로 만든 기본 Run은 `Run/DAS_Khazan_Run_Loop`이다. 기존 `CA_P_Kazan_DualAxeSword_Run_F`와 길이는 같고 새 loop에만 marker 12개가 있다. 이후 기본 Run 참조와 1-8 검사 예제의 Run 경로는 새 복사본을 사용한다.
- Walk/Run/Sprint의 Sync Marker는 각각 2/12/16개다. 이름 LeftFoot/RightFoot, 시간 범위, 시간 증가 순서, 루프 경계까지의 좌우 교대가 일치한다. 길이는 1.375/4.958333/4.958333초, 프레임 구간 수는 33/119/119로 긴 유효 구간이 유지돼 있다.
- 접촉 시점의 시각 검증, 전체 loop 경계의 자세/속도 연속성, 디스크 저장 후 새 프로세스 재확인은 완료 판정에 포함하지 않았다. 실제 marker 시간에는 최대 약 0.057프레임의 정수 프레임 대비 차이가 있으나 그 자체로 잘못된 배치라고 판정하지 않는다.
- 세 loop는 Enable Root Motion=false, Force Root Lock=false, Root Lock=Ref Pose, Rate Scale=1이다. 대표 root 표본은 정지 상태다. 이전 Force Root Lock=true 제안은 공통 root 고정 정책이며 false 자체를 이 정지 root loop의 필수 수정 오류로 취급하지 않는다.
- 최신 HandleInputMove는 `<= 0.6`에서 MaxWalkSpeed=170, `> 0.6`에서 470으로 바뀌었다. 이전의 입력 크기와 속도 수치 혼용은 이 부분에서 교정됐다. 이후 예제는 사용자의 현재 0.6 경계를 유지한다.
- 남은 문제: AddMovementInput(WorldInput, 1)에서 WorldInput을 정규화하지 않아 아날로그 기울기가 실제 가속/입력 속도에 남는다. Intent에는 원래 크기를 보존하고 CMC에는 단위 방향을 전달해야 한다. SetTargetGait/ResolvedGait와 실제 MaxWalkSpeed를 함께 갱신하고 프로젝트의 이동 허용 조건도 입력 전달 전에 반영해야 한다.
- ABP의 Run Player는 아직 marker 없는 CA_P 원본을 참조하며 Walk/Run 모두 Do Not Sync다. 시퀀스 marker 추가 완료와 ABP 동기화 적용 완료는 다르다. InGame 밖 Idle/Stop 참조도 남아 있다.
- 상세 2단계 구현 가이드: [INGAME_LOCOMOTION_STEP_2.md](INGAME_LOCOMOTION_STEP_2.md). 선언/함수/연산 설명, L3 태그·Controller 바인딩·IA/IMC/DA 설정, 기존 AnyThread snapshot 소비, Start 정책 정리, 에디터 검증 순서를 포함한다.
- 가이드의 SprintSpeed=600, dead zone=0.1, 토글 기본값 true는 설명용 제안이다. Sprint 속도와 토글/홀드를 사용자 확정값으로 기록하지 않는다. 실제 조작은 BP 기본값에서 선택할 수 있도록 안내한다.
- 다음 완료 목표는 정본 2단계의 입력/물리/gait 계약이다. 3단계에서 SprintLoop와 지상 이동 분기를 함께 연결하며, SprintStart는 5단계까지 별도 작업이다.
- 재사용 자료: `Saved/ImportReports/Khazan_InGame_LoopMarkers_Audit_20260907.json`. 이번에는 문서/리포트만 추가했고 C++·BP·입력/애니메이션 에셋은 변경하지 않았다. 제시 코드의 빌드, BP Compile, PIE와 실기기 입력 테스트는 아직 수행하지 않았다.

## 2026-09-07 2단계 사용자 테스트 완료 보고와 3단계 안내

- 사용자가 2단계 테스트 완료를 보고했다. 현재 소스에서 원래 입력 크기 보존/정규화 이동, 요청·허용 gait→속도, Sprint 입력, AnimInstance bUseSprint 전달과 일반 Start false를 확인했다. 어시스턴트가 직접 빌드/PIE로 재검증한 기록과는 구분한다.
- 현재 사용자 함수 이름은 HandleInputSprint다. Started 바인딩과 맞게 연결돼 있어 이름을 이전 예제로 되돌리지 않는다. BP 기본값은 Walk/Run/Sprint=170/470/600, threshold=0.6, dead zone=0.1, toggle=true다.
- ABP Walk/Run은 새 DAS_Khazan_*_Loop와 Sync Group Locomotion을 사용한다. 이전 Do Not Sync/Run 원본 참조 지적은 현재 두 Player에는 해당하지 않는다. SprintLoop 상태 추가와 InGame 밖 Idle/Stop 참조 교체가 남아 있다.
- 다음 상세 절차: [INGAME_LOCOMOTION_STEP_3.md](INGAME_LOCOMOTION_STEP_3.md). 각 클래스의 책임과 변수 배치 이유, AnimInstance 파생 함수/히스테리시스, 그래프 노드·핀·전이·Sync·초기화 설정을 설명한다. Player에 애니메이션 상태를 더 넣거나 C++ 재생 시계를 만들지 않는다.
- 제안 추가는 AnimInstance의 bIsGrounded, bShouldSprintLoop, RunEnterSpeed/RunExitSpeed와 UpdateLocomotionSelection_AnyThread다. 220/190 cm/s는 시각 전환 예시이며 물리 170/470을 변경하지 않는다.
- 현재 Stop→Locomotion 조건 핀은 비어 있다. 3단계에서 Stop→WalkRun/SprintLoop 재입력 경로를 연결하고 기존 Stop→Idle 자동 원샷 종료는 보존한다. 새 InGame Stop 후보는 각각 10.375초이며 유효 길이/발/Sprint Stop은 4단계에서 완성한다.
- Run Stop의 root 이동 표본을 확인했다. 해당 시퀀스에만 인플레이스 root lock 설정과 미리보기 확인을 안내하며 Start/Turn을 일괄 잠그거나 프레임을 임의 삭제하지 않는다.
- 3단계는 Standard Blend를 기준으로 한다. UE 5.8의 Bool Blend ChildUpateMode=Default 및 상태 재진입 초기화 의미를 로컬 엔진 소스로 확인했다. false인 Always Reset on Entry를 영구 시간 보존으로 설명하지 않는다.
- 자료: `Saved/ImportReports/Khazan_InGame_Step3_Baseline_20260907.json`. 16개 bool 조합/히스테리시스 계산 예는 논리식 수준에서 확인했다. 3단계 소스/에셋 구현과 빌드·Compile·PIE는 사용자 적용 후 검증 대상이며 이번에는 문서/감사 자료만 추가했다.

## 2026-09-07 4단계 상세 가이드와 선택 데이터 정리

- 다음 절차는 [INGAME_LOCOMOTION_STEP_4.md](INGAME_LOCOMOTION_STEP_4.md)다. 현재 사용자 상태 이름 WalkRun/Sprint와 bShouldSprint를 유지한다.
- 배타적인 선택은 기존 EKhazanGait로 표현한다. LocomotionGait는 loop 선택, StopGait는 직전 loop 선택을 고정한 Stop 진입 데이터다. 독립적인 사실과 전이 predicate는 bool로 남긴다.
- Stop 진입 요청은 지상 입력 상실과 직전/현재 이동 이력으로 판정한다. 현재 bIsStopping과 분리해 release snapshot에서 이미 속도가 0인 경우도 처리한다. StopEntrySpeed/Foot/Gait는 한 번 저장하며 ABP가 원샷 시간을 소유한다.
- 엔진의 최근 완료 marker 결과로 접촉 기준발 후보를 고르되 실제 지지발 판독이라고 보지 않는다. LF/RF 초입 pose와 Sprint _02 역할을 검증하고, Stop→Move에는 진입 Foot가 아니라 진행 중인 Stop의 sync 위상을 사용한다.
- Stop marker/역할 준비 후 Sync Group Locomotion / Always Leader / UE 5.8 leader position override를 검증한다. marker 없는 긴 Stop, 마지막 접촉 이후 Idle 정착 구간, 물리 제동/foot sliding은 별도로 검증한다.
- 이번에는 사용자가 적용할 설명/문서/읽기 전용 감사만 수행했다. C++/ABP/Animation Sequence 수정 및 새 빌드/PIE는 수행하지 않았다.

## 2026-09-08 4단계 Sprint 단일 클립 반영

- 사용자 확인에 따라 Sprint Stop은 1개를 사용한다. Walk/Run은 LF/RF 분기, Sprint는 StopGait의 Sprint pin에 단일 Sequence Player를 직접 연결한다. 여섯 Stop을 반드시 준비한다는 전제는 적용하지 않는다.
- StopEntryFoot는 Walk/Run 선택용이며 Sprint의 단일 선택에 필수 입력이 아니다. 단일 시퀀스에도 실제 발 접촉 마커를 넣어 재입력 동기화에 활용할 수 있지만 반대 발 초입 pose를 생성해 주는 것은 아니다.
- Root Motion 적용 여부는 root 이동 키의 존재가 아니라 캡슐 제동의 이동량을 무엇으로 결정할지에 따라 선택한다. 현재 단계에는 CMC 제동과 인플레이스 Stop(root lock)을 권장한다. 현재 에셋 설정을 변경한 기록이나 사용자가 Root Motion 정책을 최종 확정한 기록은 아니다.
- 세부 절차는 INGAME_LOCOMOTION_STEP_4.md의 2026-09-08 섹션이 앞선 Sprint 두 발 전제보다 우선한다. 이번에는 설명/문서만 변경했다.

## 2026-09-08 Stop 마커 적용 범위 보충

- 모든 Stop에 LeftFoot/RightFoot을 강제로 배치하는 것이 아니라, loop와 대응하는 실제 접촉 위상이 있는 클립에 marker sync를 적용한다.
- 실제 양발 동시 착지/정착은 같은 시각의 좌우 Sync Marker 또는 가짜 시간차로 표현하지 않는다. 필요할 때만 별도 Notify/접지 curve로 기록한다.
- 교대 위상이 없는 단일 Stop은 Do Not Sync와 일반 전이를 기준으로 연결하고, 초반/후반 재입력을 검증한다. 상세 기준은 INGAME_LOCOMOTION_STEP_4.md의 양발 동시 착지 보충을 따른다.

## 2026-09-08 Stop 부분 검증 이후 5단계 준비

- 사용자 정책 확정: Stop은 Root Lock을 이용한 인플레이스로 운용하며 실제 이동/제동은 CMC가 담당한다. 실제 확인한 Run/Sprint Stop은 Force Root Lock=true이고 Walk Stop 두 개는 false이므로 설정과 root 변위를 구분해 재확인한다.
- 최신 소스의 Stop 이력 조건은 올바르다. 새 UBT 빌드 성공 및 PIE C++ 중단점에서 Walk/Run/Sprint의 진입 Gait와 속도 170/470/600 보존을 확인했다. 추가 입력/ABP 완주/발 시각 검증은 도구 중단으로 미완료다. 이 기록을 4단계 전체 통과로 해석하지 않는다.
- 다음 사용자 구현 가이드는 [INGAME_LOCOMOTION_STEP_5.md](INGAME_LOCOMOTION_STEP_5.md)다. 최초 적용 범위를 저속·전방 SprintStart 하나로 좁혀 원샷의 진입/종료/중단을 먼저 검증한다. 고속 Run→Sprint는 적합한 주행 중 가속 클립을 준비하기 전까지 기존 Sprint 직접 진입을 유지한다. 방향별 Start는 후속 확장이다.
- 기존 bShouldPlayStart를 Sprint 진입 pulse로 재사용하고, AnimInstance에 이전 지상 Sprint 요청/이전 지상 여부 및 진입 속도/입력 방향각을 추가하는 예제를 제공한다. Player/Controller/CMC의 입력과 실제 이동 정책은 유지한다. 예제 속도/각도 220 cm/s/45도는 튜닝 출발점이며 자산 적합성을 검증한 최종 수치가 아니다.
- Start 후보의 포즈/현재 길이/최상위와 자식 root 처리가 아직 검증되지 않았으므로 에셋 준비를 선행한다. Force Root Lock만으로 자식 Root의 이동까지 사라진다고 가정하지 않는다.
- 어시스턴트는 진단 스크립트/리포트/설명 문서만 추가했다. 실제 C++/ABP/시퀀스는 변경하지 않았다. 멈춘 검사 세션의 정리와 정확한 재개는 Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md의 2026-09-08 기록을 따른다.

## 2026-09-08 현행 정본과 모든 Start 제외 — 이후 적용 순서

- 현재 구현/변수/함수의 정본은 [LOCOMOTION_CURRENT_IMPLEMENTATION.md](LOCOMOTION_CURRENT_IMPLEMENTATION.md)다. 이 문서의 앞선 단계 설명을 현재 구현 완료 상태로 읽지 않는다.
- 사용자 확정: Walk/Run/Sprint 모두 Start 시퀀스를 사용하지 않는다. SprintStart를 다시 구현하지 않고 Idle/Stop의 유효 Sprint 입력은 Sprint loop로 직접 연결한다.
- 기존 번호는 이전 설명 링크와의 대응을 위해 보존한다. 5단계는 취소이며 재개 대상이 아니다.

| 기존 단계 | 현재 처리 |
| --- | --- |
| 1~3 에셋/입력/loop | 사용자 구현과 검증 기록을 새 정본 기준으로 유지. 과거의 없는 변수/marker 상태로 되돌리지 않음. |
| 4 Stop | 현재 enum/진입 스냅샷/Walk·Run LF/RF/Sprint 단일 구조 유지. 실제 부분 검증과 남은 시각 검증을 구분. |
| 5 SprintStart | 취소. 모든 Start 제외. |
| 6 Turn | 다음 설명/구현 주제. 현재 정본 정리 후 재개하며 새 Turn 데이터/그래프는 아직 미구현. |
| 7 LockOn | 후속 범위. 이 단계에서도 Start를 자동 재도입하지 않음. |
| 8 품질/통합 | 발 접촉, 제동/회전, 재입력/공중/낮은 FPS 등의 후속 검증. |

이번 변경은 문서뿐이다. Turn 설계 중 언급한 미확정 후보 변수/콜백을 사용자가 적용한 코드로 기록하지 않는다. 실행 검사 재개가 필요할 때만 Engineering continuity의 미회수 세션 정리 절차를 따른다.
