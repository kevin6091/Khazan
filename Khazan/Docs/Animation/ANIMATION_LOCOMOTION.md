# Khazan Locomotion

> 캐릭터 이동 애니메이션의 에셋 규칙, 런타임 구조, 검증 기준을 함께 관리하는 전용 문서다.
> 코드 수정 전에는 이 문서와 `Docs/Engineering/UE5_ENGINEERING_RULES.md`만 먼저 확인한다.

## 2026-09-02 구현 상태

- [완료] `Idle → Walk → Run`과 역방향 전환을 `UKhazanAnimInstance`에서 제어한다.
- [완료] 출발·정지 시 LF/RF 위상을 선택하고 Walk/Run 전환 시 루프 위상을 유지한다.
- [완료] 이동 중 90/180도 방향 전환과 정지 상태 180도 Turn을 원샷으로 재생한다.
- [완료] 현재 무기는 `DualAxeSword`이며 무기별 데이터는 `UKhazanLocomotionProfile`로 분리했다.
- [완료] `Hard` 접미사 애니메이션은 런타임 에셋과 프로필에서 제외했다.
- [완료] 정적 에셋/ABP 감사와 8.875초 PIE 입력 추적을 통과했다.

## 기준 에셋

| 역할 | 경로 |
| --- | --- |
| AnimInstance C++ | `Source/Khazan/Animation/KhazanAnimInstance.h/.cpp` |
| 무기 프로필 타입 | `Source/Khazan/Animation/KhazanLocomotionProfile.h` |
| Animation Blueprint | `/Game/_Art/Kazan/Character/Bluprints/ABP_Player` |
| DualAxeSword 프로필 | `/Game/_Art/Kazan/Animation/Locomotion/Profiles/DA_Locomotion_DualAxeSword` |
| 추출 원본 | `/Game/_Art/Kazan/Animation/Weapons/DualAxeSword/Shared/Locomotion` |
| 런타임 정리본 | `/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword` |
| 원작 이동 영상 | `C:\Users\user\Desktop\Locomotion.mp4` |

`ABP_Player`의 기본 흐름은 `fallback Idle State Machine → DefaultSlot → Output Pose`다. C++ 컨트롤러가 `DefaultSlot`에 Dynamic Montage를 재생하고, 프로필 또는 클립이 없을 때만 fallback Idle이 보인다.

## 원작 영상 분석

- 파일: H.264, 1920×1080, 30 fps, 39.5초, 1,185 frame.
- 분석 산출물: `Saved/LocomotionAnalysis`의 contact sheet와 구간 frame.
- 관찰 결과: 낮은 아날로그 입력은 무게 중심 이동이 느린 Walk, 최대 입력은 Run으로 이어진다. 입력 해제에는 별도 제동 자세가 있고 급격한 90/180도 입력에는 일반 방향 보간과 구분되는 pivot 동작이 있다.
- 영상은 타이밍·상태 선택 참고 자료이며, 에셋의 실제 유효 frame과 발 접촉 위상은 추출 애니메이션을 기준으로 결정했다.

## FModel 애니메이션 네이밍 규칙

| 토큰 | 해석 | 현재 처리 |
| --- | --- | --- |
| `CA_P_Kazan` | 카잔 플레이어 Character Animation | 주인공 locomotion 후보 |
| `DualAxeSword` | 무기/자세군 | 현재 기본 프로필 |
| `Walk_F`, `Run_F` | 전방 Walk/Run loop | 속도에 맞춰 반복 재생 |
| `Sprint_Start_F_LF/RF` | 왼발/오른발 리드 Run 출발 | 현재 발 위상에 따라 선택 |
| `ReturnIdle_Walk/Run_F_LF/RF` | Walk/Run에서 Idle로 복귀 | 정지 순간의 발 위상에 따라 선택 |
| `StandTurn_L/R_180` | 제자리 좌/우 180도 회전 | 저속 또는 Walk pivot에 사용 |
| `MovingTurn_L/R_90/180` | 이동 중 좌/우 급회전 | Run 중 각도 기준으로 선택 |
| `Bridge` | 상태 간 연결 클립 | 유효 길이가 충분할 때만 사용 |
| `Hard` | 특수/피로 계열 후보 | 현재 범위에서 항상 제외 |

`LF/RF`는 단순 파일 variant가 아니라 출발·정지 시 어느 발이 지지/선행하는지 나타내는 선택 키로 취급한다. `L/R`은 회전 방향이다.

## 추출본 정리와 유효 구간

FModel/변환 원본은 모두 249 frame, 10.375초로 들어왔지만 다수 클립 뒤에 고정 pose tail이 있었다. 원본은 보존하고 런타임 복사본만 다음 길이로 잘랐다.

| 런타임 에셋 | frame | 길이 |
| --- | ---: | ---: |
| `RT_DAS_Idle` | 249 | 10.375 s |
| `RT_DAS_Walk_Loop` | 33 | 1.375 s |
| `RT_DAS_Run_Loop` | 20 | 0.833 s |
| `RT_DAS_Walk_Start` | 2 | 0.083 s |
| `RT_DAS_Run_Start_LF/RF` | 14 / 17 | 0.583 / 0.708 s |
| `RT_DAS_Walk_Stop_LF/RF` | 23 / 23 | 0.958 / 0.958 s |
| `RT_DAS_Run_Stop_LF/RF` | 19 / 19 | 0.792 / 0.792 s |
| `RT_DAS_TurnInPlace_L/R_180` | 14 / 14 | 0.583 / 0.583 s |
| `RT_DAS_MovingTurn_L/R_90` | 12 / 12 | 0.500 / 0.500 s |
| `RT_DAS_MovingTurn_L/R_180` | 11 / 11 | 0.458 / 0.458 s |

- 모든 런타임 클립은 Root Motion 비활성, Force Root Lock 활성이다. 실제 이동은 `CharacterMovementComponent`가 담당한다.
- 원본에 Notify/Sync Marker가 없어서 런타임 Walk/Run loop에 `LeftFoot`, `RightFoot` marker를 추가했다.
- `RT_DAS_Walk_Start`는 0.12초 미만이므로 현재 C++이 의도적으로 건너뛰고 Walk loop로 바로 진입한다.

## 런타임 상태 구조

| 상태 | 진입 조건 | 종료/다음 상태 |
| --- | --- | --- |
| `Idle` | 이동 입력 없음 | 입력 시 Start 또는 Walk/Run |
| `Start` | 유효한 출발 클립 존재 | 원샷 종료 후 동일 발 위상의 loop |
| `Walk` | 이동 입력, Run 진입 속도 미만 | Run, Stop 또는 Turn |
| `Run` | 속도 300 cm/s 이상 | 240 cm/s 미만이면 Walk; 입력 해제 시 Stop |
| `Stop` | 이동 입력 해제 | 정지 원샷 후 Idle; 재입력 시 즉시 이동 |
| `TurnInPlace` | 입력 방향 차이 65도 이상, 속도 100 cm/s 미만 | 원샷 후 목표 gait loop |
| `MovingTurn` | Run 중 65도 이상 방향 변경 | 135도 미만은 90, 이상은 180 클립 |
| `Airborne` | `CharacterMovementComponent::IsFalling()` | 착지 시 Idle 또는 현재 gait loop |

- Run 진입/이탈은 300/240 cm/s hysteresis를 사용해 임계점 떨림을 막는다.
- Walk/Run 기준 속도는 170/470 cm/s이며 play rate는 `speed/reference`를 0.75–1.30으로 제한한다.
- loop/one-shot/stop blend는 각각 0.14/0.10/0.16초다.
- 방향 변경은 `LastTravelDirection`과 현재 가속 입력의 yaw 차이를 `UKismetMathLibrary::NormalizedDeltaRotator`로 계산한다.
- 직전 이동 의도를 즉시 갱신하므로 같은 180도 입력을 유지할 때 pivot이 반복 재생되지 않는다. 재트리거 쿨다운은 0.3초다.

## LF/RF 발 위상

| Gait | Left contact | Right contact |
| --- | ---: | ---: |
| Walk | 0.242 | 0.697 |
| Run | 0.400 | 0.850 |

현재 loop의 정규화 phase와 두 contact phase의 원형 거리를 비교해 가까운 발을 `FootLead`로 선택한다. 정지 시 이 값으로 LF/RF stop을 고르고, Walk↔Run 및 원샷 복귀 시 선택한 contact phase부터 새 loop를 시작한다.

## 무기 모듈화

현재 구조는 상태 로직을 복제하지 않고 `UKhazanLocomotionProfile` Data Asset만 교체한다. 대검 추가 절차는 다음과 같다.

1. 대검 원본에서 같은 역할의 Idle/loop/start/stop/turn 클립을 정리한다.
2. `/Game/_Art/Kazan/Animation/Locomotion/Runtime/GreatSword`에 런타임 복사본을 만든다.
3. `DA_Locomotion_GreatSword`를 생성해 클립, 속도, 발 phase, turn threshold를 설정한다.
4. 무기 장착 시 `SetLocomotionProfile()`로 프로필을 바꾼다.
5. 동일한 정적 감사와 PIE 입력 추적을 새 프로필에 실행한다.

무기마다 상체 overlay, additive 또는 전혀 다른 상태 흐름이 필요해질 때만 Linked Anim Layer/Linked Anim Graph를 추가한다. 이 경우 공통 base layer가 이동 데이터와 gait/phase를 계산하고, 무기별 layer interface가 Idle/Locomotion/Turn pose만 반환하도록 구성한다.

## Motion Matching 대안

현재는 전통 State 제어를 선택했다. 추출본이 방향별 연속 pose set이 아니라 소수의 전방 loop/원샷이고, 고정 tail과 curve/notify 부재가 있어 지금 Pose Search DB를 만들면 검색 품질을 보장할 수 없기 때문이다.

향후 충분한 방향·속도 클립을 확보하면 다음 순서로 전환한다.

1. Pose Search Schema에 trajectory, facing, velocity, pose/foot 채널을 구성한다.
2. 고정 tail 제거와 LF/RF contact curve/marker 보강 후 무기별 Pose Search Database를 만든다.
3. Chooser로 장착 무기에 맞는 DB를 선택한다.
4. continuing-pose bias와 LF/RF phase cost를 설정하고 90/180 turn clip에 trajectory sample을 제공한다.
5. Motion Matching 출력 뒤 Inertialization을 적용하고 stop/turn foot sliding을 PIE trace로 검증한다.

## 재생성 및 검증

| 목적 | 스크립트/리포트 |
| --- | --- |
| 런타임 clip, profile, ABP 구성 | `Scripts/Animation/build_dual_axe_locomotion_assets.py` |
| 정적 감사 | `Scripts/Animation/audit_khazan_locomotion.py` → `Saved/ImportReports/Khazan_Locomotion_Audit.json` |
| PIE 상태 추적 | `Scripts/Animation/run_locomotion_pie_trace.py` → `Saved/ImportReports/Khazan_Locomotion_PIE_Trace.json` |
| 빌드 provenance | `Saved/ImportReports/Khazan_DualAxe_Locomotion_Build.json` |

2026-09-02 검증 기준:

- 런타임 클립 16개 존재, frame/root-lock/Hard 제외 검사 통과.
- `ABP_Player` compile up-to-date, parent `UKhazanAnimInstance`, `DefaultSlot` 1개, profile CDO 연결 확인.
- PIE 관찰 상태: `IDLE, START, WALK, RUN, MOVING_TURN, STOP`.
- PIE 관찰 발: `LEFT, RIGHT` 모두 확인.
- PIE 관찰 turn: `RT_DAS_MovingTurn_R_90`, `RT_DAS_MovingTurn_R_180` 확인, held-input 중복 재생 없음.

## 현재 의도적 제약

- `Hard` 동작과 스태미나 고갈 상태는 미구현이다.
- Airborne은 상태 격리만 하며 Jump/Fall/Land 전용 pose는 후속 작업이다.
- 현재 추출 후보에 Walk 90도 moving-turn이 없어 Walk의 큰 방향 변경은 StandTurn 180을 사용한다.
- 원본 영상과 추출 데이터가 추가되기 전에는 임의 보간 클립이나 Motion Matching DB를 생성하지 않는다.

## 2026-09-03 명령형 로코모션 롤백과 현재 기준선

> 이 섹션은 2026-09-02 구현 기록을 삭제하지 않고 보존하되, 그 구현을 더 이상 현재 런타임 정본으로 취급하지 않는다는 점을 명시한다.

### 롤백 결과

- [소스 롤백 완료] `UKhazanAnimInstance`에서 `Idle`, `Start`, `Walk`, `Run`, `Stop`, `TurnInPlace`, `MovingTurn`, `Airborne`을 직접 선택하던 상태 제어를 제거했다.
- [소스 롤백 완료] LF/RF 수동 발 위상, 방향각 기반 클립 선택, `PlaySlotAnimationAsDynamicMontage()` 기반 로코모션 재생을 제거했다.
- [제거 확인] `Source/Khazan/Animation/KhazanLocomotionProfile.h`와 `/Game/_Art/Kazan/Animation/Locomotion/Profiles/DA_Locomotion_DualAxeSword`는 현재 존재하지 않는다.
- [보존] `/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword`의 `RT_DAS_*` 애니메이션 16개는 다음 구조에서 재평가할 원본 데이터로 남겼다. 보존 자체가 현재 런타임 사용을 의미하지는 않는다.
- [보존] `/Game/_Art/Kazan/Character/Bluprints/ABP_Player` 에셋은 남아 있다. 롤백 후 Editor에서의 그래프 재검토와 Compile/PIE 검증은 아직 완료로 판정하지 않는다.

### 현재 `UKhazanAnimInstance` 데이터

| 항목 | 현재 동작 |
| --- | --- |
| `Character`, `MovementComponent` | `NativeInitializeAnimation()`에서 소유 Pawn과 이동 컴포넌트를 캐시한다. |
| `Velocity` | `NativeUpdateAnimation()`에서 `MovementComponent->Velocity`를 복사한다. |
| `GroundSpeed` | `Velocity.Size2D()`로 계산한다. |
| `bShouldMove` | 평면 속도가 3 cm/s보다 크고 현재 가속도가 0이 아닐 때 참이다. |
| `bIsFalling` | `CharacterMovementComponent::IsFalling()` 값을 복사한다. |
| `Acceleration` | 프로퍼티 선언은 남아 있으나 현재 `.cpp`에서는 값을 갱신하지 않는다. 다음 데이터 계약 단계 전까지 유효한 런타임 값으로 사용하지 않는다. |

현재 구현에는 gait, locomotion mode, 이동 의도, trajectory, 회전 의도, 무기별 애니메이션 세트 선택, Motion Matching, Chooser, Linked Anim Graph/Layer가 없다. `NativeThreadSafeUpdateAnimation()`도 아직 사용하지 않는다.

### 구형 자동화와 리포트의 지위

- `Scripts/Animation/build_dual_axe_locomotion_assets.py`는 제거된 `UKhazanLocomotionProfile`과 프로필 에셋을 다시 생성하는 구형 구현용 스크립트다. 새 구조로 교체하기 전에는 실행하지 않는다.
- `Scripts/Animation/audit_khazan_locomotion.py`와 `run_locomotion_pie_trace.py`도 구형 상태/프로필 구조를 검사하므로 현재 기준의 검증 도구가 아니다.
- `Saved/ImportReports/Khazan_Locomotion_*.json`과 `Khazan_DualAxe_Locomotion_Build.json`은 2026-09-02 구현의 이력 자료이며, 롤백된 현재 상태의 통과 증거로 사용하지 않는다.

### 다음 마이그레이션 단계

1. Gameplay C++에서 이동 입력 의도, 이동 모드, 목표 gait처럼 게임플레이 권한이 필요한 값의 명확한 데이터 계약을 정의한다.
2. `UKhazanAnimInstance`는 게임 스레드에서 필요한 UObject 값을 짧은 스냅샷으로 수집하고, 파생 계산은 thread-safe 경로에서 수행하도록 책임을 분리한다.
3. ABP는 스냅샷을 소비해 pose를 생성하며, 로코모션을 C++ Dynamic Montage로 강제 재생하지 않는다. Slot/Montage는 공격·회피·피격 같은 액션 계층에 남긴다.
4. 방향·속도·전이 클립 품질과 수량을 먼저 감사한 뒤 Pose Search Schema/Database와 Motion Matching을 도입한다.
5. 무기별 차이가 데이터 세트뿐이면 Chooser/데이터 선택으로 처리하고, 그래프 구조까지 다를 때만 Linked Anim Graph/Layer로 모듈화한다.

### 검증 상태

- 2026-09-03 정적 확인: 롤백된 `KhazanAnimInstance.h/.cpp`, 프로필 소스 부재, 프로필 에셋 부재, 런타임 클립 16개와 `ABP_Player` 존재를 확인했다.
- 검증 대기: 롤백된 최신 소스를 기준으로 한 비-Live-Coding 전체 UBT 빌드, `ABP_Player` Compile, PIE 기본 이동 확인.

## 2026-09-03 DAS 인플레이스 로코모션 현재 정본

### 채택한 런타임 구조

- 캐릭터의 실제 월드 이동은 `CharacterMovementComponent`와 캡슐이 담당한다. 로코모션 애니메이션은 캡슐을 끌고 가지 않는 인플레이스 재생을 기본으로 한다.
- Gameplay C++은 이동 허용 여부, 입력 의도, 목표 gait, 이동 모드처럼 게임플레이 권한이 필요한 값을 결정한다.
- `UKhazanAnimInstance`는 게임 스레드에서 UObject 기반 원시 값을 짧은 스냅샷으로 수집하고, 속도·방향·이동 여부 같은 파생 값은 thread-safe update에서 계산해 Anim Graph에 제공한다.
- Anim Blueprint는 State Machine, Blend Space, Sync Marker와 Inertialization으로 최종 pose를 만든다. 일반 로코모션을 C++에서 Dynamic Montage로 강제 재생하지 않는다.
- 현재 DAS 원본은 핵심 loop의 root가 제자리이고 Motion Matching용 연속 trajectory 데이터베이스가 아니므로, 기본 해법은 데이터 기반 State Machine과 Blend Space다. Motion Matching은 충분한 방향별 root/trajectory 데이터가 별도로 확보된 뒤 다시 평가한다.
- 무기별 차이가 애니메이션 세트뿐이면 같은 그래프에서 데이터 또는 Chooser로 선택한다. 상태 흐름이나 overlay 구조까지 다를 때만 Linked Anim Layer/Linked Anim Graph로 분리한다.

### 준비된 런타임 애니메이션 라이브러리

원본 범위는 Dual Axe Sword 아래에서 package path에 `Locomotion`이 포함된 `AnimSequence`다. 이름에 이동 단어가 들어가더라도 공격·스킬·장착 등 다른 문맥에 있는 17개 에셋은 이 라이브러리에 섞지 않았다.

| 그룹 | 런타임 경로 | 수량 | 주 용도 |
| --- | --- | ---: | --- |
| Base | `/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword` | 45 | 자유 이동 Idle, Walk, Run, Sprint, Start, Stop, Turn |
| LockOn | `.../DualAxeSword/LockOn` | 25 | 타깃 고정 상태의 방향별 Walk/Run과 전이 |
| Guard | `.../DualAxeSword/Guard` | 16 | 가드 자세의 8방향 이동 세트 |
| Flow | `.../DualAxeSword/Flow` | 21 | Flow 자세의 Idle, 8방향 이동과 전이 |
| 합계 |  | 107 | Idle 11, loop 45, Start 20, Stop 19, Turn 12 |

- 모든 런타임 이름은 `RT_DAS_*` 형식이다. 대표 이름은 `RT_DAS_Idle`, `RT_DAS_Walk_Loop`, `RT_DAS_Run_Loop`, `RT_DAS_Sprint_Loop`, `RT_DAS_LockOn_Walk_F_Loop`, `RT_DAS_Guard_Walk_F_Loop`, `RT_DAS_Flow_Walk_F_Loop`이다.
- 원본 107개는 원래 package와 249-frame import 상태로 보존했다. 잘라내기, Sync Marker, root 정책은 런타임 복사본에만 적용했다.
- 런타임 에셋에는 `Khazan.SourceAnimation`과 `Khazan.LocomotionRole` metadata가 있어 원본과 역할을 자동으로 추적할 수 있다.

### 프레임 정리 기준

- 프로젝트의 DAS 소스는 모두 24 fps, 249-frame 길이로 들어와 있지만 원본 PSA의 실제 구간은 클립마다 다르다. 따라서 249라는 공통 길이를 유효 동작 길이로 간주하지 않는다.
- 일반 클립은 PSA의 `NumRawFrames - 2`에 해당하는 마지막 고유 import key까지 남기고 뒤의 고정 padding을 잘랐다. 마지막 한 sample이 중복되는 현재 변환 특성까지 반영한 기준이다.
- `Run`과 `Run_Hard`는 반복 take에서 처음 완성되는 20-frame 보행 주기만 남겼다.
- `Sprint`는 다리만 보고 너무 짧게 자르면 상체 주기가 끊기므로 처음 완성되는 60-frame 전신 주기를 남겼다.
- `RT_DAS_Idle`과 `RT_DAS_Idle_Hard`는 원본 PSA가 현재 FBX보다 각각 14 frame 더 길다. 없는 pose를 임의 생성하지 않고 현재 FBX의 249 frame을 그대로 사용하며, 원본과 완전히 같은 장주기 loop가 필요하면 두 클립만 올바른 범위로 다시 export해야 한다.

### Root와 발 동기화 정책

- 런타임 107개는 `Enable Root Motion = false`, `Force Root Lock = true`, `Root Motion Root Lock = Ref Pose`다.
- 45개 순환 loop의 root는 실제로 제자리임을 검사했다. Start, Stop, Turn 계열 19개에는 authored root track 이동이 있지만 추출을 끄고 root lock을 적용해 인플레이스 전이로 사용한다. root track에 키가 있다는 사실과 Root Motion으로 캡슐을 이동시키는 것은 구분한다.
- 순환 loop 45개에 `LeftFoot`과 `RightFoot` Sync Marker 총 96개를 넣었다. Sprint 한 개는 긴 전신 주기 때문에 좌우 contact가 각각 네 번이며, 나머지 loop는 좌우 한 번씩이다.
- marker track 이름은 `LocomotionSync`다. 이는 에셋 편집용 track 이름이고, Anim Graph의 Sync Group 이름은 별도로 `Locomotion`으로 설정한다.
- contact는 UE의 `FootstepAnimEventsModifier`로 120 Hz 평가한 뒤 중복 접촉을 합치고 실제 import rate인 24 fps frame에 스냅했다. Base Walk, Hard Walk, Run, Hard Run, Sprint는 눈으로 확인한 기준 frame을 고정해 자동 재생성 시에도 같은 위상을 유지한다.
- Start, Stop, Turn 같은 one-shot에는 순환 marker를 억지로 넣지 않았다. loop 간 보폭 위상 동기화와 one-shot 전이 선택은 서로 다른 책임으로 유지한다.

### Anim Blueprint 연결 기준

1. Grounded State Machine은 최소한 `Idle`, `Start`, `Locomotion`, `Stop`, `Pivot`으로 나눈다. 낙하 pose가 준비되면 별도의 `Airborne` 상위 분기를 둔다.
2. 자유 이동 Base 세트는 방향별 지속 loop가 아니라 전방 Walk/Run/Sprint가 핵심이므로 우선 속도축 1D Blend Space로 구성한다. 없는 측면 loop를 회전 보간으로 꾸며 2D 세트처럼 사용하지 않는다.
3. LockOn은 Walk와 Run에 방향별 pose가 있으므로 방향각과 속도를 축으로 하는 2D Blend Space가 적합하다.
4. Guard와 Flow는 각각 독립된 자세와 8방향 이동 세트를 사용한다. 같은 이동 계산을 공유하되 pose 선택 데이터는 Base/LockOn과 분리한다.
5. 순환 Sequence Player 또는 Blend Space sample은 Sync Group `Locomotion`에 넣고 Marker Based Sync를 사용한다. Start/Stop/Turn one-shot은 필요할 때 그룹 밖에서 재생하고 전환 끝에 loop로 합류시킨다.
6. 상태 전환의 pose 이음에는 Inertialization을 사용한다. 발 미끄러짐은 Sync Marker만으로 모두 해결되는 문제가 아니므로 최종 이동 속도, play rate, 가속·감속과 필요 시 Stride Warping을 함께 조정한다.
7. 공격, 회피, 피격처럼 gameplay action이 pose를 점유하는 경우에만 Slot/Montage 계층을 사용한다.

현재 완료 범위는 AnimSequence 라이브러리 준비까지다. Blend Space 생성, `ABP_Player`의 State Machine 연결과 PIE 체감 조정은 다음 구현 범위이며, 이번 정리에서 C++과 Anim Blueprint 그래프는 변경하지 않았다.

### 재생성과 검증 자료

| 목적 | 스크립트 | 결과 리포트 |
| --- | --- | --- |
| 프로젝트 DAS 로코모션 조사 | `Scripts/Animation/survey_das_locomotion_assets.py` | `Saved/ImportReports/Khazan_DAS_Locomotion_SourceSurvey.json` |
| 원본 PSA 길이 복구 | `Scripts/Animation/extract_das_psa_metadata.py` | `Saved/ImportReports/Khazan_DAS_PSA_SourceMetadata.json` |
| loop 발 접촉 분석 | `Scripts/Animation/analyze_das_loop_contacts.py` | `Saved/ImportReports/Khazan_DAS_Locomotion_LoopContacts.json` |
| 런타임 복사본 생성·정리 | `Scripts/Animation/build_das_locomotion_runtime_library.py` | `Saved/ImportReports/Khazan_DAS_Locomotion_RuntimeBuild.json` |
| fresh-process 정적 감사 | `Scripts/Animation/audit_das_locomotion_runtime_library.py` | `Saved/ImportReports/Khazan_DAS_Locomotion_RuntimeAudit.json` |

- 최신 감사: runtime 107/107, source 107/107, 오류 0, 경고 2다.
- 경고 2개는 위의 Base Idle 두 클립에 부족한 원본 14 frame이며, 다른 naming, skeleton, trim, root, marker, metadata 검사는 모두 통과했다.
- 작업 전 런타임 바이너리 백업은 `Saved/ArtBackups/DAS_Locomotion_Runtime_Before_2026-09-03`에 있다.

## 2026-09-07 InGame 전용 로코모션 현재 기준

- 사용자 확정: 런타임 Animation Sequence는 `/Game/_Art/Kazan/Animation/InGame` 아래만 사용한다. Walk/Run Start는 사용하지 않고 Sprint에만 Start 모션을 사용한다. Stop, Moving Turn, Turn In Place는 구현한다.
- 이후 단계 설명과 구현 기준은 [INGAME_LOCOMOTION_MIGRATION.md](INGAME_LOCOMOTION_MIGRATION.md)를 따른다. 이 새 문서에는 현행 계획과 1단계의 에셋/마커 준비 절차, 검사 함수의 줄별 설명을 기록했다.
- 사용자가 직접 C++/ABP/에셋을 구현하고 어시스턴트가 자세히 설명하는 진행 방식을 유지한다. 이번 요청에서 어시스턴트가 변경한 것은 문서와 읽기 전용 감사 결과뿐이다.
- 현재 에디터에서 InGame 에셋 64개를 확인했다: Animation Sequence 62개, Level Sequence 2개. 62개 시퀀스 모두 Sync Marker가 0개다. 새 복사본은 이전 라이브러리의 marker 준비 완료 상태를 이어받았다고 보지 않는다.
- 기본 loop 선택은 `Walk/DAS_Khazan_Walk_Loop`, `Run/CA_P_Kazan_DualAxeSword_Run_F`, `Sprint/DAS_Khazan_Sprint_Loop`이다. 각각 33/119/119프레임 구간, 1.375/4.958333/4.958333초, 24 fps다. 긴 Run/Sprint는 여러 유효 주기를 보존하며 개별 접촉을 다시 확인한다.
- 현재 ABP는 Walk/Run 두 Sequence Player를 Bool로 블렌드하며 둘 다 Do Not Sync다. Idle/Airborne_TEMP와 Stop에는 아직 InGame 밖 시퀀스 참조가 있어 그래프 전환 과정에서 교체해야 한다.
- Run의 시작/끝 대표 RAW 본 위치가 다르므로 loop 경계를 시각적으로 확인한다. 이 위치 차이만으로 결함을 확정하지 않는다. 미리보기 접지, 전체 pose/속도 연속성, BP Compile/빌드/PIE는 이번에 완료로 기록하지 않는다.
- 재사용 감사: `Saved/ImportReports/Khazan_InGame_Locomotion_Audit_20260907.json`. InGame에 없는 무기/자세별 시퀀스를 이전 폴더에서 자동으로 가져오지 않는다.

### 2026-09-07 L3 Sprint / Walk 170 / Run 470 입력 정책

- 사용자 확정: 왼쪽 스틱에 유효 입력이 있으면 Walk 170 cm/s, 기울기가 Run 임계값을 넘으면 Run 470 cm/s로 목표 속도를 고정한다. 같은 gait 안에서 스틱 기울기에 따라 연속적으로 속도를 바꾸지 않는다.
- Sprint는 L3 버튼으로 생성한 요청이 있을 때만 허용한다. 스틱 최대 기울기만으로 Sprint로 전환하지 않는다. Walk/Run에는 Start가 없고 Sprint에만 Start를 사용하는 정책은 그대로다.
- 입력 크기는 gait 선택과 Intent 데이터로 보존하고, 실제 이동에는 정규화한 방향과 ScaleValue 1을 사용한다. 170/470은 입력에 곱하지 않고 CharacterMovementComponent의 MaxWalkSpeed에 적용한다. 기존 가감속은 유지한다.
- Run 임계값, Sprint 속도, L3 토글/홀드 방식은 아직 사용자 확정 전이다. 상세 설명과 이후 2단계의 추가 변수/액션 경로는 `INGAME_LOCOMOTION_MIGRATION.md`의 같은 날짜 입력 정책 섹션에 기록했다.

### 2026-09-07 사용자 loop marker 검토와 2단계 설명

- 현재 기본 Run은 새 `InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Loop`이다. Walk/Run/Sprint marker 2/12/16개와 공통 이름/시간 범위/좌우 교대를 확인했다. 이전 marker 0개 기준선은 이 세 복사본의 현재 상태가 아니다.
- 현재 ABP는 Run의 marker 없는 CA_P 원본을 계속 참조하고 Walk/Run 동기화가 꺼져 있다. InGame 밖 Idle/Stop 참조도 남아 있어 그래프 3단계 완료는 아니다.
- 최신 Player는 0.6 경계의 170/470 MaxWalkSpeed 분기를 구현했으나 CMC에 전달할 벡터 정규화와 요청/허용 gait 연결이 남아 있다. 순수 입력 크기는 Intent에 보존한다.
- 다음 사용자 구현 가이드는 [INGAME_LOCOMOTION_STEP_2.md](INGAME_LOCOMOTION_STEP_2.md)다. 현행 계획만 다루며 이전 C++ 상태 재생 제어를 복원하지 않는다.
- 감사 리포트: `Saved/ImportReports/Khazan_InGame_LoopMarkers_Audit_20260907.json`. 접지 시각 검증, 새 프로세스 저장 검증, 제시 코드의 빌드/BP Compile/PIE는 완료로 기록하지 않는다. 어시스턴트는 이번에 C++나 에셋을 수정하지 않았다.

### 2026-09-07 3단계 사용자 구현 가이드

- 사용자가 2단계 테스트 완료를 보고했다. 최신 소스의 입력/속도/gait 연결과 ABP Walk/Run의 새 loop 및 Sync Group Locomotion 설정을 읽기 전용으로 확인했다.
- [INGAME_LOCOMOTION_STEP_3.md](INGAME_LOCOMOTION_STEP_3.md)에 Idle/WalkRun/SprintLoop, 현재 Stop 보존/재입력, InGame 참조 정리, 공중 임시 분기와 클래스별 데이터 소유 이유를 설명했다.
- 새 C++ 제안은 AnimInstance의 시각 선택 조건과 220/190 cm/s 히스테리시스다. Player의 L3 정책/물리 170/470을 변경하지 않는다. 원시 snapshot 구조는 재작성하지 않는다.
- Stop 원샷의 긴 10.375초 후보, LF/RF/Sprint 선택, Run Stop root와 제동 품질은 구분해서 기록한다. 일반 loop와 재입력 경로 완료를 Stop 품질 완료로 혼동하지 않는다.
- 이번 작업은 설명/문서/표적 감사 자료 작성이며 C++/에셋을 변경하지 않았다. 3단계 구현/빌드/PIE는 아직 대기다. 감사: `Saved/ImportReports/Khazan_InGame_Step3_Baseline_20260907.json`.


## 2026-09-07 Stop 진입 데이터 / enum 선택 / 발 동기화 4단계 안내

- 사용자 3단계 적용을 현재 소스와 ABP에서 읽기 전용으로 확인했다. 상태 이름은 WalkRun/Sprint/Stop이며 bShouldSprint를 사용한다. Stop→WalkRun/Sprint 재입력은 이미 연결되어 있다.
- bUseRunStop은 release edge에서만 갱신하는 마지막 선택값이다. 조건 밖 로그는 현재 GroundSpeed와 과거 선택을 함께 출력한다. 실제 ABP 임계값은 315였고 기존 로그에 600/false→504/true, 이후 0/true가 관찰되었다. release/인스턴스 식별자가 없는 로그로 개별 재현의 실행 분기를 단정하지 않는다.
- [INGAME_LOCOMOTION_STEP_4.md](INGAME_LOCOMOTION_STEP_4.md)에 StopGait/StopEntrySpeed/StopEntryFoot 진입 고정, 직전 속도/지상 입력 이력, enum loop 선택, 독립 bool 전이 조건, LF/RF 후보 매핑과 양방향 sync 절차를 작성했다.
- 입력 없는 감속 중 loop 선택도 유지해 outgoing Run이 속도 0에서 Walk로 바뀌는 것을 피한다. Stop 진입은 bIsStopping과 분리하며 물리 정지 후 원샷 종료/재입력은 ABP가 소유한다.
- 현재 DAS Walk/Run Stop LF는 각각 40/95프레임 구간이고 나머지 RF/Sprint 네 후보는 249프레임 구간이다. 여섯 후보 모두 marker 0개이며 Sprint _02의 반대 발 매핑은 시각 검증 전이다. 현재 길이/사용자 편집을 덮어쓰지 않았다.
- 원시 소스/에셋 수정 없이 문서와 표적 감사 결과만 작성했다. 제안식 14개 시나리오 계산은 빌드/BP Compile/PIE/접지 검증이 아니다.

## 2026-09-08 Sprint 단일 Stop과 root 정책 안내

- 사용자 확인: Sprint Stop은 좌우 발 variant가 아닌 단일 클립으로 사용한다. Walk/Run만 LF/RF 선택을 유지하며 Stop graph는 기본 5 Player 구성이다. Sprint 분기에 Foot enum blend를 요구하지 않는다.
- 현재 Sprint 작업본은 DAS_Khazan_Sprint_Stop_LF, 114프레임 구간/4.75초, marker 0개다. 이름의 LF를 실제 발별 세트 존재의 근거로 보지 않는다. 중립 이름 DAS_Khazan_Sprint_Stop을 권장하되 Rename/복사/삭제는 수행하지 않았다.
- ABP Root Motion Mode는 Montages Only이며 작업본 Enable Root Motion/Force Root Lock은 모두 false다. root local Y 이동 표본을 확인했지만 실제 캡슐 거리와 동일시하지 않는다.
- 현재 단계 권장안은 CMC 제동 유지 + Stop 작업본 Root Motion=false/Force Root Lock=true/Ref Pose 우선 비교다. 원본 root track은 보존한다. authored Stop 이동을 실제 게임플레이 거리로 사용할 경우에만 별도 Root Motion 제동/재입력/스케일 정책을 검증한다.
- 상세 설명과 단일 Sprint 연결, root 설정 비교 및 현재 소스 선행 교정은 INGAME_LOCOMOTION_STEP_4.md의 2026-09-08 섹션을 따른다. 코드 조건 반전 진단 기록은 Engineering 프로젝트 상태에도 분리했다.
- 이번 변경은 설명 문서뿐이다. C++/ABP/시퀀스 수정 및 새 빌드/PIE는 수행하지 않았다.

## 2026-09-08 본 삭제로 손상된 InGame 작업본 8개 복구 완료

- InGame AnimSequence 63개 중 DAS 작업본 8개에서 root 외 225개 본 트랙이 삭제된 상태를 확인했다. 나머지 55개와 대응 Weapons 원본은 226개 트랙을 유지했다.
- 정상 원본에서 누락 트랙만 복구하여 작업본 8개를 저장했다. 기존 root 키 전체, 현재 잘라둔 길이, Walk/Run/Sprint Sync Marker 2/12/16개와 기타 설정을 보존했다. SK_Khazan/SKM_Khazan과 ABP/C++는 수정하지 않았다.
- 별도 프로세스의 전체 RAW 본/프레임 비교, root hash/marker/설정 보존 및 compressed pose 발 동작 검사가 8/8 통과했다. 보호 대상 Content 61개도 백업과 SHA-256이 같다. 최종 commandlet exit 0, 오류 0이다.
- Sprint Stop은 이번 시작 시점에 249프레임 구간/10.375초로 저장되어 있었다. 직전 기록의 114프레임 구간/4.75초와 달라 길이를 질문했으며, 답변 전에는 현재 길이를 유지했다. 이전 4.75초 tail 편집까지 복구했다고 간주하지 않는다.
- 현재 복구 계층은 C_P_Kazan(scale 100) → Root → Bip001이다. Root 최상위 변경은 별도 메시/스켈레톤과 애니메이션을 함께 변환하고 검증하는 후속 작업이다.
- 상세 결과/백업/원본 매핑/재검증 명령: [SKELETON_RECOVERY_2026-09-08.md](SKELETON_RECOVERY_2026-09-08.md). 새 PIE 전이/접지 품질 검증은 이번 범위에서 수행하지 않았다.

## 2026-09-08 사용자 Control Rig loop 끝 프레임 편집 복원

- 사용자가 Walk/Run/Sprint loop의 첫 프레임 키를 마지막 프레임에 복사해 Bake했음을 확인했다. 앞선 본 트랙 원본 복구는 이 사용자 포즈 편집을 재현하지 못했다.
- DAS_Khazan_Walk_Loop은 0→33, Run_Loop/Sprint_Loop은 0→119로 첫 포즈를 마지막 sample에 복사한 결과를 실제 시퀀스에 적용하고 저장했다. 길이 1.375/4.958333/4.958333초, 마커 2/12/16개와 설정은 유지했다.
- 별도 프로세스에서 226개 본의 RAW/압축 포즈 처음·끝 차이 0, 끝 직전까지 중간 프레임 보존 검사를 3/3 통과했다. 보호 대상 파일 66개는 SHA-256이 같다. 최종 commandlet exit 0/오류 0.
- 현재 검증 정본은 Saved/ImportReports/Khazan_DAS_LoopClosure_verify_20260908.json이다. 앞선 SkeletonRecovery source-equality 검사는 끝 프레임 수동 편집 이전의 이력으로 남긴다.
- 백업/오차/재검증 절차와 정확한 범위는 SKELETON_RECOVERY_2026-09-08.md의 추가 복구 섹션을 따른다. 외부 Control Rig 편집 이력 자체를 복원한 것은 아니며 Stop/C++/ABP/스켈레톤/메시는 수정하지 않았다.

## 2026-09-08 Stop _New의 C_P_Kazan Root 트랙 Bake

- 사용자 요청대로 InGame Run/DAS_Khazan_Run_Stop_LF_New, Run/DAS_Khazan_Run_Stop_RF_New, Sprint/DAS_Khazan_Sprint_Stop_New를 원본 복사로 생성했다.
- 원본은 각각 95/91/114프레임 구간(3.958333/3.791667/4.75초), 24 fps다. Sync Marker 0개와 길이/설정을 그대로 보존했다. 이전 기록의 RF/Sprint 길이로 되돌리지 않았다.
- C_P_Kazan의 scale 100을 포함해 Root의 움직임을 최상위 본으로 합성하고 Root 애니메이션 트랙만 제거했다. 본 계층은 유지하며 Root는 reference pose로 고정된다.
- 기타 225개 본의 Control Rig 채널 2,025개는 키 시간/값/탄젠트까지 동일하다. 원본/다른 InGame/Skeleton/Mesh/ABP/AnimInstance를 포함한 보호 파일 71개는 SHA-256이 같다.
- 별도 프로세스에서 세 저장본의 RAW/압축 포즈 및 속성/채널 보존 검증을 3/3 통과했다. Root Motion 활성화, 정규화 scale, Root Lock 등 옵션은 원본값을 유지했다. Enable Root Motion은 false이며 게임 내 이동 활성화/거리 검증은 수행하지 않았다.
- 상세 변환식/결과/백업/검증 정본: [STOP_ROOT_TRANSFER_2026-09-08.md](STOP_ROOT_TRANSFER_2026-09-08.md), Saved/ImportReports/Khazan_DAS_StopRootTransfer_verify_20260908.json.

## 2026-09-08 Stop 마커와 양발 동시 착지 기준

- Stop Sync Marker는 현재 loop와 공통 의미의 접촉 위상으로 동기화할 때 적용한다. 모든 Stop에 좌우 두 마커를 강제로 요구하지 않는다.
- 양발이 지면에 있는 상태와 두 발이 같은 순간 새로 착지하는 사건을 구분한다. 한 발이 이미 지지하고 다른 발이 새로 닿으면 새로 닿은 발의 접촉만 기록한다.
- 실제 동시 착지에 LeftFoot/RightFoot을 같은 시각으로 겹치거나 가짜 한 프레임 차이를 만들지 않는다. BothFeet Sync Marker만 추가해도 기존 loop와 자동 동기화되지 않으며 현재 C++ 좌우 쌍 해석도 이를 처리하지 않는다.
- 양발 착지 이벤트/접지 구간이 필요하면 선택적인 Anim Notify 또는 좌우 독립 Animation Curve로 표현한다. 이름만 추가해 전이/IK가 구현되는 것은 아니다. 양발 착지와 Stop 완료 시점도 구분한다.
- 순환 보행 위상이 없는 Stop은 Do Not Sync + 일반 전이/재입력을 기준으로 먼저 확인한다. 대응 마커가 있는 Stop도 마지막 접촉 이후 정착 구간의 재입력 품질을 따로 검사한다.
- 상세: INGAME_LOCOMOTION_STEP_4.md의 같은 날짜 양발 착지 보충. 이번에는 문서만 추가했으며 특정 프레임의 접지 포즈 재검증이나 C++/ABP/에셋 변경은 수행하지 않았다.

## 2026-09-08 현재 Stop 검증 범위와 5단계 준비

- 실제 현재 Stop은 InGame의 Walk LF/RF, Run LF/RF, Sprint 단일 시퀀스 5개를 참조한다. Stop state Always Reset on Entry=true, 모두 Loop=false. Sprint에는 단일 Default Pose만 가진 Foot enum 노드가 있지만 좌우 시퀀스 두 개를 사용하는 구조는 아니다.
- Run LF/Run RF/Sprint Stop의 Force Root Lock=true, Enable Root Motion=false, Ref Pose를 확인했다. Walk LF/RF Stop은 Force Root Lock=false다. 이 설정 차이만으로 Walk root가 실제 이동한다고 단정하지 않는다. 전체 top/child root 변위 확인은 남았다. ABP Root Motion Mode는 Montages Only다.
- 현재 Stop 길이/marker 수: Walk LF 1.666667초/3, Walk RF 1.666667초/1, Run LF 3.708333초/1, Run RF 3.791667초/2, Sprint 4.75초/1. 한쪽 marker 하나만 있는 시퀀스를 좌우 순환 위상이 완전히 동기화된 것으로 기록하지 않는다. 모두 Locomotion/AlwaysLeader/Leader Joining Override=true로 설정되어 있어 비순환 Stop의 그룹 정책은 후속 시각 검증 항목이다.
- loop 마커 2/12/16과 InGame 참조를 확인했다. GroundedLocomotion 출력 뒤 Inertialization 노드가 연결돼 있다. 이전 Message Log의 누락 오류만으로 현재 노드가 없다고 판단하지 않는다.
- 새 빌드와 실제 C++ Walk/Run/Sprint Stop 진입 데이터 확인은 Engineering 프로젝트 상태를 따른다. 추가 PIE 입력 검사와 viewport 관찰은 도구/디버거 응답 중단으로 완료하지 못했고 발 튐 원인도 확정하지 않았다. 사용자가 보고한 체감 품질과 어시스턴트의 완료 검증 범위를 구분한다.
- [INGAME_LOCOMOTION_STEP_5.md](INGAME_LOCOMOTION_STEP_5.md)에 다음 저속·전방 SprintStart 기본형, 원본 보존/자산 준비, 실제 최상위 C_P_Kazan과 자식 Root 구분, 변수/함수의 줄별 의미, 상태 전이와 중단 규칙을 작성했다. 코드/에셋은 사용자가 적용할 예제이며 이번에 구현하거나 런타임 통과시킨 것이 아니다.
- 현재 실행 정리/재개는 Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md의 2026-09-08 섹션을 먼저 따른다. 테스트 리포트: Saved/ImportReports/Khazan_InGame_Stop_Verification_20260908.json.

## 2026-09-08 현재 구현 정본 통합과 Start 전면 제외

- 사용자 요청으로 [LOCOMOTION_CURRENT_IMPLEMENTATION.md](LOCOMOTION_CURRENT_IMPLEMENTATION.md)를 새 정본으로 추가했다. 이후 로코모션 작업은 Router 다음에 이 정본을 먼저 읽는다. 이 문서의 앞선 구현 기록은 삭제하지 않고 이력/상세 근거로 보존한다.
- 새 정본은 현재 소스를 재확인해 클래스 책임, Intent/snapshot/파생/Stop 진입/이력 변수, 함수와 갱신 순서, 마지막 ABP/시퀀스 관측값, 실제 검증과 미확정 항목을 구분했다.
- 사용자 최신 결정: Sprint를 포함한 모든 Start 모션을 사용하지 않는다. 앞선 SprintStart 제안은 취소됐고 현재 bShouldPlayStart=false를 유지한다. 다음 구현 주제는 Turn이다.
- 현재 실제 심볼은 LocomotionGait, StopGait, StopEntryFoot, bShouldSprint, MovementDirectionAngle이다. 과거 bool 선택 변수와 가이드의 임시 이름을 현재 구현으로 재사용하지 않는다.
- 이번에는 문서와 선행 읽기 규칙만 변경했다. C++/ABP/시퀀스 수정, 새 빌드/PIE, 중단된 검사 세션 복구는 수행하지 않았다. 마지막 에셋 관측과 새 소스 확인을 같은 검증 수준으로 기록하지 않는다.
