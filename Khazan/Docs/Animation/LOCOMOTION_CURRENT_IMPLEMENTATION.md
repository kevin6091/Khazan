# Khazan 로코모션 현재 구현 정본

## 2026-09-08 기준선과 문서 사용 규칙

이 문서는 **현재 함께 구현한 로코모션의 데이터 계약과 실제 구현 상태**를 정리한다. 이후 로코모션 작업은 `0_DOCUMENT_ROUTER.md` 다음에 이 문서를 먼저 읽는다. 설명용 제안 코드, 과거 상태, 실제 파일, 런타임 검증 결과를 서로 혼동하지 않는다.

- 이번 기준선은 현재 C++ 파일을 다시 읽고, 기존의 표적 에셋/ABP 감사 및 검증 리포트와 대조해 작성했다. 이번 문서 정리에서 Editor를 다시 실행하거나 BP/에셋을 새로 검사하지 않았다.
- 현재 C++에 관한 기술은 이번 소스 확인 기준이다. ABP/시퀀스 정보는 아래에 명시한 **마지막 검사 시점의 관측값**이며, 현재 Editor의 미저장 상태까지 보장하지 않는다.
- 사용자 최신 요구사항이 설계 방향을 결정한다. 현재 구현 여부는 실제 소스/그래프가 증명하고, 실행 성공 여부는 해당 버전의 테스트가 증명한다. 문서만으로 구현이나 테스트 완료를 선언하지 않는다.
- 문서와 소스가 다르면 차이를 먼저 설명한다. 문서에 맞춘다는 이유로 사용자의 코드, 변수 이름, 에셋 편집을 자동으로 되돌리지 않는다.
- 기존 `ANIMATION_LOCOMOTION.md`와 단계별 가이드는 상세 설명/과거 관측 자료다. 현재 상태 판단에서는 이 정본과 그 이후에 추가된 날짜별 변경 계약을 우선한다.
- 이후 변경은 이 문서 하단에 날짜별로 추가한다. 바뀐 변수/함수, 의미, 작성자·소비자, 변경 이유, 구현 여부, 검증 범위, 다음 작업을 함께 적는다. 같은 날짜에는 변경 제목/순서로 선후 관계를 분명히 한다.
- 사용자가 설명을 요청하면 어시스턴트는 설명하고 사용자가 구현한다. 코드/ABP/에셋 직접 수정은 별도 요청 범위에서만 수행한다. 이번 요청은 문서 정리와 프로젝트 내 추가다.

## 1. 확정된 방향과 현재 단계

| 항목 | 현재 계약 |
| --- | --- |
| 런타임 시퀀스 범위 | `/Game/_Art/Kazan/Animation/InGame` 아래만 사용한다. 현재 기본 세트는 `DAS/Locomotion`이다. |
| Start | **Walk, Run, Sprint 모두 Start 모션을 사용하지 않는다.** L3 Sprint에도 Start를 추가하지 않는다. 이후 LockOn 확장에서도 Start를 자동으로 다시 도입하지 않는다. |
| 기본 이동 | Idle에서 WalkRun 또는 Sprint loop로 직접 진입한다. |
| Stop | Walk LF/RF, Run LF/RF, Sprint 단일 Stop을 사용한다. |
| Turn | 다음 구현 주제다. 현재 C++에는 Turn 선택/진입/종료 데이터가 구현돼 있지 않다. 이동 중 Turn과 제자리 Turn의 조건·회전 정책은 구현 전에 구분한다. |
| 실제 이동/제동 | `UCharacterMovementComponent`가 담당한다. Stop은 사용자가 Root Lock 기반 인플레이스 운용을 선택했다. |
| 입력 속도 정책 | 유효한 작은 스틱 입력은 Walk 목표 170 cm/s, Run 임계값을 넘으면 Run 목표 470 cm/s. Sprint는 L3 요청이 있어야 한다. |
| 현재 C++ 기본값 | Run 입력 경계 0.6, 입력 dead zone 0.1, Sprint 목표 600 cm/s, L3 토글 방식이다. 숫자/토글은 편집 가능한 현재 기본값이지 엔진의 보편 규칙이 아니다. |
| 애니메이션 구조 | Gameplay 입력/허용 → CMC → 게임 스레드 snapshot → AnyThread 파생 값 → ABP State Machine/Sequence Player. |
| Motion Matching | 현재 구현하지 않았고 현행 마이그레이션의 선행 조건도 아니다. |
| Blend Space | 사용자가 지정한 이름은 `BS_DAS_Player_WalkRun`이다. Blend Space 1D로 강제 교체하지 않는다. 마지막 그래프 관측은 Sequence Player + enum 선택이며, 이름을 지정했다는 이유로 Blend Space가 실제 연결돼 있다고 기록하지 않는다. |
| 무기 확장 | 현재 데이터 계약을 유지한다. Linked Anim Layer/Graph, Chooser, 무기별 데이터 세트의 구체적 적용은 아직 구현 완료가 아니다. |

기존 단계 번호는 참조 혼선을 막기 위해 보존한다. **4단계 Stop 다음에 기존 5단계 SprintStart는 취소하고 6단계 Turn으로 이동한다.** `INGAME_LOCOMOTION_STEP_5.md`의 Start 구현 예제는 적용 대상이 아니다. 중단된 Turn 설명 중 언급된 후보 enum, 상태 진입 콜백 등도 아직 합의·구현된 계약으로 편입하지 않는다.

## 2. 파일과 클래스의 책임

| 파일/클래스 | 책임과 이 위치에 두는 이유 | 여기에서 하지 않는 일 |
| --- | --- | --- |
| `Source/Khazan/Player/KhazanPlayerController.h/.cpp` / `AKhazanPlayerController` | Enhanced Input 이벤트를 받고 현재 조종 Pawn에 전달한다. 입력 장치/소유 플레이어에 가까운 계층이다. | Stop 발 선택, 시퀀스 재생, AnimInstance의 속도 판정. |
| `Source/Khazan/Character/KhazanCharacter.h/.cpp` / `AKhazanCharacter` | 공통 Character 기반에서 LocomotionComponent를 생성하고 getter로 제공한다. 애니메이션은 Player 구체 타입 대신 이 공통 타입을 캐시한다. | L3 토글, 시퀀스 시간 제어. |
| `Source/Khazan/Character/KhazanPlayer.h/.cpp` / `AKhazanPlayer` | 사람의 스틱/L3 입력을 게임 이동 의도로 해석하고 gait별 물리 속도를 적용한다. | Walk/Run Stop 클립 선택, 발 위상, ABP 상태를 직접 재생. |
| `Source/Khazan/Character/Locomotion/KhazanLocomotionType.h` | 여러 클래스가 공유하는 enum과 입력 의도 구조체를 정의한다. 서로를 include하지 않고 공통 의미를 공유하는 계약이다. | Tick, 입력 이벤트 처리, 애니메이션 재생. |
| `Source/Khazan/Character/Component/KhazanLocomotionComponent.h/.cpp` / `UKhazanLocomotionComponent` | 요청/허용 gait와 평면 이동 의도를 보관한다. Player와 AnimInstance 사이의 공통 gameplay 데이터 창구다. | CMC 속도 적분, 최종 pose 선택, 프레임마다 애니메이션 시간 누적. |
| 엔진 `UCharacterMovementComponent` | 입력으로 실제 속도, 가감속, 충돌, MovementMode와 캐릭터 회전을 계산한다. | DAS 시퀀스나 LF/RF 선택. |
| `Source/Khazan/Animation/KhazanAnimInstance.h/.cpp` / `UKhazanAnimInstance` | 원시 관측값을 모아 애니메이션에 필요한 사실·선택·진입 데이터를 계산한다. Stop 선택은 시각 표현이므로 여기에 있다. | AnyThread에서 Actor/CMC를 직접 변경하거나 일반 로코모션 몽타주를 강제 재생. |
| `/Game/_Art/Kazan/Character/Bluprints/ABP_Player` | 실제 상태 진입, Sequence Player 시간, enum pose 선택, 블렌드와 sync를 담당한다. | 스틱 처리, L3 허용 판단, gameplay 물리 속도를 다시 계산. |
| `Source/Khazan/Data/KhazanInputData.h/.cpp`, `Source/Khazan/KhazanGameplayTags.h/.cpp` | 입력 태그를 실제 InputAction에 연결한다. 애니메이션 상태 enum과 입력 식별자를 분리한다. | Locomotion state 선택. |

`KhazanGameMode.cpp`는 현재 Cog 창 등록 등 GameMode 역할이다. 특정 캐릭터의 이동 의도나 Stop/Turn 선택을 이 클래스에 추가하지 않는다.

`AKhazanCharacter`의 생성자는 `CreateDefaultSubobject<UKhazanLocomotionComponent>("LocomotionComponent")`로 캐릭터가 소유하는 공통 컴포넌트를 만든다. private `LocomotionComponent`는 VisibleAnywhere/BlueprintReadOnly인 TObjectPtr이며, `GetLocomotionComponent() const`가 이 포인터를 반환한다. 반환 시 새 컴포넌트를 만들거나 데이터를 복사하는 getter가 아니다. Character의 BeginPlay/Tick은 현재 Super만 호출한다. 공통 컴포넌트 소유권은 Character에, L3 해석은 Player에 둔 이유를 구분한다.

### 데이터 흐름

```text
InputAction / Mapping Context
    ↓ Controller: 이벤트 전달
Player: 입력 크기 보존, L3 요청, gait → MaxWalkSpeed
    ├─ LocomotionComponent.Intent: 원하는 방향/크기/허용 정책
    └─ AddMovementInput(단위 방향, 1): 실제 이동 입력
               ↓
CharacterMovementComponent: 실제 Velocity / Acceleration / MovementMode
               ↓ Game Thread에서 값 수집
FKhazanAnimGameThreadData: UObject 대신 전달하는 값 snapshot
               ↓ 애니메이션 update 문맥
UKhazanAnimInstance: 운동학 → loop 선택 → Stop 진입 데이터 → 이력 저장
               ↓
ABP_Player: 상태 전이 / pose 선택 / 재생 시간 / sync / 블렌딩
```

이 그림은 책임/데이터 의존성이다. 임의 Actor Tick과 모든 애니메이션 작업의 절대적인 전역 실행 순서를 약속하는 그림은 아니다.

## 3. 입력과 gameplay 데이터 계약

### 3-1. 공통 enum

| 타입 | 현재 값 | 실제 용도/주의점 |
| --- | --- | --- |
| `EKhazanGait : uint8` | Walk=0, Run=1, Sprint=2 | 요청, 허용 상한, loop/Stop 선택에 같은 어휘를 사용한다. `GetResolvedGait()`가 숫자 순위를 비교하므로 순서를 무심코 바꾸지 않는다. `UENUM(BlueprintType)`이다. |
| `EKhazanRotationMode : uint8` | VelocityDirection, LookingDirection, LockOn | 회전 정책을 표현할 타입이다. 현재 Intent → snapshot → AnimInstance로 전달된다. enum 선언과 setter만으로 LookingDirection/LockOn 회전이 구현되지는 않는다. |
| `EKhazanLocomotionMode : uint8` | Grounded, InAir | 선언은 있으나 현재 소스에서 사용처를 확인하지 못했다. `UENUM(BlueprintType)`도 붙어 있지 않다. 현재 지상/공중 판정은 CMC `MovementMode`와 bool을 사용한다. |
| `EKhazanFoot : uint8` | None, Left, Right | Stop 진입의 발 후보다. None은 계산 불가능/유효한 좌우 마커 쌍 없음이며, 양발 동시 착지나 임의의 왼발을 의미하지 않는다. |

배타적인 선택은 enum, 서로 독립적인 사실과 전이 조건은 bool을 사용한다. `LocomotionGait`와 `bHasMovementInput`은 서로 대체 관계가 아니다. enum과 소수의 전이 bool을 함께 쓰는 현재 구성을 모든 선택별 bool로 다시 풀지 않는다. 이 구조의 성능을 숫자로 비교한 프로젝트 벤치마크는 없다.

### 3-2. `FKhazanLocomotionIntent` — 무엇을 원하는가

이 구조체는 LocomotionComponent의 `Intent` 멤버에 저장된다. `GetIntent()`는 `const` 참조를 반환한다. 호출자가 setter를 거치지 않고 변경하지 못하게 하는 것이며, 이 참조를 worker thread에서 계속 읽어도 안전하다는 의미는 아니다.

| 변수 | 기본값/단위 | 작성과 소비 | 의미 |
| --- | --- | --- | --- |
| `MoveInputWorld` | ZeroVector, 무차원 월드 벡터 | `SetMoveInputWorld()` → Player의 단위 방향, Anim snapshot | Z=0, 길이 최대 1. 입력 크기를 포함한 의도이며 실제 Velocity가 아니다. |
| `InputAmount` | 0, 0~1 | 위 setter에서 벡터 `Size2D()` → Player gait/Anim 입력 판정 | 입력 크기. km/h나 cm/s가 아니다. |
| `TargetGait` | Walk | Player `RefreshLocomotionGait()` → `GetResolvedGait()` | 스틱과 L3가 요청한 gait. |
| `MaxAllowedGait` | Sprint | `SetMaxAllowedGait()` → `GetResolvedGait()` | gameplay가 허용하는 상한. L3가 이 제한을 무시하지 않는다. |
| `RotationMode` | VelocityDirection | `SetRotationMode()` → snapshot/AnimInstance | 회전 의도/정책 식별자. 현재 setter가 CMC 회전 옵션까지 바꾸지는 않는다. |
| `bMovementAllowed` | true | `SetMovementAllowed()` → Player gate/Anim gate | 프로젝트의 이동 허용 정책. CMC의 모든 이동/외력을 자동 정지시키는 엔진 스위치가 아니다. |

`Intent` 자체는 `UPROPERTY(Transient, BlueprintReadOnly, ... AllowPrivateAccess="true")`다. 런타임 보관/관측용이며 영구 설정 데이터와 구분한다.

### 3-3. LocomotionComponent 함수

| 함수 | 현재 동작 | 보존할 의미 |
| --- | --- | --- |
| 생성자 | `bCanEverTick=false` | 입력/정책 setter가 값을 갱신하므로 별도 Tick을 돌리지 않는다. |
| `SetMoveInputWorld(const FVector& Input)` | 허용되지 않으면 Clear 후 return. `(X,Y,0)`을 만들고 `GetClampedToMaxSize(1)`로 저장한 뒤 `Size2D()`를 입력량으로 저장. | 길이 상한을 제한하는 것이지 모든 작은 입력을 길이 1로 정규화하는 함수가 아니다. |
| `ClearMoveInput()` | 방향/크기만 0으로 만든다. | TargetGait, MaxAllowedGait, RotationMode를 초기화하지 않는다. |
| `SetTargetGait()` | 요청 gait 저장. | CMC MaxWalkSpeed를 직접 변경하지 않는다. |
| `SetMaxAllowedGait()` | 허용 상한 저장. | 이 setter만 호출했다고 Player 속도가 즉시 새로 적용되는 것은 아니다. |
| `SetRotationMode()` | enum 저장. | 캐릭터를 직접 회전시키지 않는다. |
| `SetMovementAllowed()` | bool 저장. false이면 ClearMoveInput. | Velocity를 강제로 0으로 만들거나 `DisableMovement()`를 호출하지 않는다. |
| `GetResolvedGait() const` | Target와 MaxAllowed를 uint8 순위로 비교하고 더 낮은 쪽의 enum 반환. | 허용된 요청이다. 실측 속도에서 추론한 gait가 아니다. |
| `GetIntent() const` | 저장된 Intent의 const 참조 반환. | AnimInstance는 GT에서 필요한 필드를 값으로 복사한다. |

현재 `SetMaxAllowedGait()` 변경 후 실제 속도 적용은 `RefreshLocomotionGait()` 호출 시점에 이루어진다. 이 함수는 Player Tick에서 매번 호출되는 함수가 아니다. 나중에 스태미나/피격 등의 제한을 추가할 때 현재 호출 계약을 확인한다.

### 3-4. Player 변수와 물리 기본값

| 변수 | 현재 C++ 기본값 | 용도와 소유 이유 |
| --- | --- | --- |
| `WalkSpeed` | 170 cm/s | Walk 선택 시 CMC MaxWalkSpeed. 플레이어 조작/이동 튜닝이다. |
| `RunSpeed` | 470 cm/s | Run 선택 시 CMC MaxWalkSpeed. |
| `SprintSpeed` | 600 cm/s | L3 요청이 허용된 Sprint의 MaxWalkSpeed. |
| `RunInputThreshold` | 0.6 | `Intent.InputAmount > 0.6`이면 Run. 정확히 0.6은 Walk다. |
| `MoveInputDeadZone` | 0.1 | `MovementInput.Length() <= 0.1`이면 입력 해제로 취급한다. |
| `bToggleSprint` | true | L3 Started마다 요청을 반전한다. false이면 누르는 동안 요청한다. |
| `bSprintRequested` | false | 개인 입력 상태. 허용된 gait나 현재 Sprint pose 자체가 아니다. private 런타임 bool이다. |
| `SpringArm`, `Camera` | subobject | 시점 장치. SpringArm 길이 600, C++ 상대 Pitch -30. 시퀀스 선택과 무관하다. |

속도/입력 튜닝 값은 `EditDefaultsOnly`이므로 BP 기본값이 C++ 초기값을 덮을 수 있다. 실제 튜닝 결과를 기록할 때 C++ 선언만 보지 말고 BP CDO/인스턴스 값도 구분한다.

현재 Player 생성자의 CMC 설정은 OrientRotationToMovement=true, RotationRate=(0,540,0) deg/s, MaxWalkSpeed=600, MinAnalogWalkSpeed=15, MaxAcceleration=1800, BrakingDecelerationWalking=1800이다. BeginPlay에서 MaxWalkSpeed를 WalkSpeed로 설정한다. 이후 유효 입력에서 선택 gait 속도를 적용한다.

Controller 회전의 Pitch/Yaw/Roll 직접 사용은 모두 false다. 현재 자동 회전은 CMC 경로다. 메시 상대 변환은 위치 `(0,0,-88)`, Yaw `-90`, 균일 Scale `0.009`다. AnimInstance의 방향각 기준은 이 메시의 로컬 축이 아니라 **Actor의 정면 축**이다.

### 3-5. `HandleInputMove()`의 계산 순서

1. LocomotionComponent가 없으면 반환한다.
2. 프로젝트 `bMovementAllowed`가 false이거나 엔진 `IsMoveInputIgnored()`가 true이면 `HandleInputMoveReleased()` 후 반환한다.
3. `RawInputAmount = float(MovementInput.Length())`로 스틱 크기를 읽는다. dead zone 이하면 같은 해제 경로로 빠진다.
4. `FRotator(0, ControlRotation.Yaw, 0)`으로 카메라/컨트롤러의 수평 방향만 사용한다. Pitch 때문에 전방 입력이 위/아래로 향하지 않게 한다.
5. `GetForwardVector()`와 `GetRightVector()`로 월드 평면 기준 두 축을 만든다.
6. `WorldInput = Forward * MovementInput.X + Right * MovementInput.Y`로 합성한다. **현재 Player가 받는 action 값에서는 X가 전후, Y가 좌우**다. IMC의 Swizzle 이전 물리 스틱 축과 혼동하지 않는다.
7. `SetMoveInputWorld(WorldInput)`으로 크기를 포함한 의도를 먼저 저장한다.
8. `RefreshLocomotionGait()`가 저장된 크기와 L3 요청으로 MaxWalkSpeed를 정한다.
9. `Intent.MoveInputWorld.GetSafeNormal2D()`로 CMC에 보낼 방향만 단위 벡터로 만든다.
10. `AddMovementInput(MoveDirection, 1.f)`로 이동 입력을 보낸다. 170/470/600을 입력 벡터에 곱하지 않는다.

예를 들어 입력 크기 0.3과 0.5는 서로 다른 Intent 값으로 보존되지만 모두 Walk 목표 170을 사용한다. 입력 크기 0.8은 Run 목표 470이다. 유효한 L3 요청이 있으면 요청 gait는 Sprint지만 MaxAllowedGait가 Run이면 실제 적용 gait는 Run이다.

**고정 속도 모드는 목표 속도 구간을 고정하는 정책이다.** 가속 시작, 제동, 충돌, 외력 중에도 실측 `GroundSpeed`가 항상 정확히 170/470/600이라는 뜻은 아니다.

### 3-6. Player의 나머지 함수

| 함수 | 현재 동작 |
| --- | --- |
| 생성자 | 카메라/스프링암, CMC, 메시 기본 변환 구성. |
| `BeginPlay()` | Super 이후 CMC가 있으면 MaxWalkSpeed=WalkSpeed. |
| `Tick()` | Super만 호출한다. 로코모션 선택/재생 시간 계산은 없다. |
| `HandleInputMoveReleased()` | Intent 방향/크기를 지운다. 토글 모드이면 Sprint 요청도 false. TargetGait/MaxWalkSpeed를 즉시 Walk로 덮지 않는다. |
| `HandleInputSprint()` | 토글이면 `!bSprintRequested`, 홀드이면 true로 설정하고 Refresh 호출. Started에 연결된다. |
| `HandleInputSprintReleased()` | 홀드 모드일 때만 요청 false. 이후 Refresh 호출. |
| `HandleInputSprintCanceled()` | 모드와 관계없이 요청 false 후 Refresh 호출. |
| `RefreshLocomotionGait()` | 컴포넌트/CMC/허용/엔진 입력 무시/입력량을 검사한다. 스틱 Walk/Run → L3 Sprint 요청 → SetTargetGait → GetResolvedGait → MaxWalkSpeed 순서다. |

입력이 없으면 Refresh는 조기에 반환한다. 그래서 L3를 눌렀다는 사실만으로 제자리에서 Sprint loop를 재생하지 않는다. 홀드 모드에서 L3를 계속 누른 채 이동 입력만 놓으면 요청은 유지될 수 있다. 토글 모드에서는 이동 해제가 요청을 끈다.

### 3-7. Controller와 입력 에셋 연결

| 이벤트/함수 | 실제 전달 |
| --- | --- |
| `BeginPlay()` | InputData의 MappingContext를 LocalPlayer EnhancedInput subsystem에 우선순위 0으로 추가. |
| `SetupInputComponent()` | InputData에서 태그로 Action을 찾고 아래 바인딩을 구성. |
| Move Triggered → `Input_Move()` | FVector2D 값과 ControlRotation을 Player `HandleInputMove()`에 전달. |
| Move Completed/Canceled → `Input_MoveReleased()` | Player `HandleInputMoveReleased()` 호출. |
| Sprint Started → `Input_Sprint()` | Player `HandleInputSprint()` 호출. |
| Sprint Completed → `Input_SprintReleased()` | Player `HandleInputSprintReleased()` 호출. |
| Sprint Canceled → `Input_SprintCanceled()` | Player `HandleInputSprintCanceled()` 호출. |
| Turn Triggered → `Input_Turn()` | `AddYawInput(X)`, `AddPitchInput(Y)`로 **시점 입력** 처리. 이 이름은 MovingTurn/TurnInPlace 애니메이션 구현을 뜻하지 않는다. |
| Jump Triggered → `Input_Jump()` | Character::Jump 호출. 현재 코드에는 테스트용 0.5초 ForceFeedback도 있다. 공중 전용 pose 구현과는 별개다. |
| Attack Triggered → `Input_Attack()` | 현재 함수 본문은 비어 있다. |

입력 native tag는 `Input.Action.Move`, `Input.Action.Sprint`, `Input.Action.Turn`이다. 입력 Data Asset은 `/Game/Data/DA_InputData`, 관련 Action은 `/Game/Input/Locomotion/IA_Move`, `IA_Sprint`, `IA_Turn`이다. L3 요구사항은 `Gamepad_LeftThumbstick` 매핑이다. 이전 action 주입 테스트는 물리 L3와 IMC Swizzle 자체를 검증한 테스트가 아니다.

`FKhazanInputAction.InputTag/InputAction`은 식별자와 실제 에셋의 한 쌍이다. `UKhazanInputData.InputMappingContext/InputActions`가 설정을 보관하고 `FindInputActionByTag()`가 유효한 Action과 같은 태그를 찾아 반환한다. 없으면 오류 로그와 nullptr을 반환한다. 입력 에셋의 현재 저장/미저장 매핑 전체를 이번 문서 작업에서 재검사하지 않았다.

## 4. AnimInstance: 원시 관측값과 파생 값

### 4-1. 참조와 생명주기

| 멤버/함수 | 역할 |
| --- | --- |
| `Character` | `TryGetPawnOwner()`를 AKhazanCharacter로 Cast한 캐시. ActorRotation과 CMC/LocomotionComponent를 얻는 GT 접근점이다. |
| `MovementComponent` | 실제 속도/가속도/MovementMode 관측용 CMC 캐시. |
| `LocomotionComponent` | gameplay Intent/ResolvedGait 관측용 캐시. |
| `GameThreadData` | 다음 애니메이션 계산에 전달할 원시 값 묶음. plain struct이며 UObject 포인터를 포함하지 않는다. |
| 생성자 | ObjectInitializer를 Super에 전달한다. 별도 로코모션 재생 초기화는 없다. |
| `NativeInitializeAnimation()` | Super → snapshot 기본 초기화 → 파생/이력 Reset → 참조 캐시 → GT 데이터 수집. |
| `NativeUninitializeAnimation()` | 캐시 nullptr → snapshot/파생/이력 Reset → Super. 이전 Pawn의 이동/Stop 이력이 재사용되지 않게 한다. |
| `CacheReferences_GameThread()` | Game Thread임을 check하고 참조를 다시 구한다. Character가 없으면 하위 컴포넌트 캐시도 nullptr이다. |
| `NativeUpdateAnimation()` | Super → 참조 유효성 확인/필요 시 캐시 복구 → GatherGameThreadData. |
| `NativeThreadSafeUpdateAnimation()` | Super → `const Snapshot = GameThreadData` 값 복사 → 유효하지 않으면 Reset/return → UpdateKinematics. |
| `ResetDerivedData_AnyThread()` | 현재 관측/전이/Stop 값과 이전 frame 이력을 기본 상태로 지운다. RunEnterSpeed/RunExitSpeed 같은 튜닝 값은 지우지 않는다. |

Character/MovementComponent는 BlueprintReadOnly로 노출돼 있어도 worker thread에서 임의 멤버 접근이 안전해지는 것은 아니다. AnyThread 계산에서는 snapshot과 애니메이션 전용 API를 사용한다. NativeThreadSafeUpdate가 매번 반드시 worker에서 실행된다고도 단정하지 않는다. 이전 Stop 검사에서 worker 실행을 실제로 관측한 사례는 있다.

이 snapshot 전달은 엔진이 관리하는 AnimInstance update 순서에서 사용한다. struct 값 복사 자체가 mutex나 임의 비동기 작업 간 동기화 장치인 것은 아니다. 별도 async task를 추가하면 안전성을 다시 검토해야 한다.

현재 Reset은 벡터/속도/각도/입력량을 0, 사실·전이·이력 bool을 false, LocomotionGait/StopGait/PreviousLocomotionGait를 Walk, StopEntryFoot를 None, StopEntrySpeed/PreviousGroundSpeed를 0으로 만든다. ResolvedGait는 Run, RotationMode는 VelocityDirection으로 되돌린다. UObject 참조를 지우는 것은 NativeUninitializeAnimation의 별도 처리다. 아직 valid snapshot이 없는 상태의 기본값을 실제 gameplay 요청/관측값으로 해석하지 않는다.

### 4-2. `FKhazanAnimGameThreadData` 전체 필드

`GatherGameThreadData()`는 매번 기본 초기화된 `NewData`를 만든다. 참조가 하나라도 유효하지 않으면 bValid=false인 데이터를 전달하고 반환한다. 모든 필드를 수집한 뒤 bValid=true를 넣고 GameThreadData를 교체한다.

| 필드 | 수집 출처 | 단위/현재 용도 |
| --- | --- | --- |
| `bValid` | Gather의 참조 검사 결과 | 미연결 Preview/해제 상태에서 잘못된 파생 계산 방지. 초기 false. |
| `ActorRotation` | Character::GetActorRotation | 도(deg). 현재는 Yaw만 사용해 Velocity를 Actor 기준으로 변환. |
| `VelocityWorld` | CMC::Velocity | cm/s. 실제 이동 관측. GroundSpeed, VelocityLocal, 이동 여부/방향의 기반. |
| `AccelerationWorld` | CMC::GetCurrentAcceleration | cm/s². 현재 AnimInstance 멤버로 복사한다. 입력 여부/Stop 선택의 판정식에는 사용하지 않는다. |
| `MoveInputWorld` | Intent.MoveInputWorld | 무차원 월드 평면 입력. 현재 Native 파생 함수는 이 필드를 아직 사용하지 않는다. Turn에서 필요한 재료일 수 있으나 Turn 계산이 이미 있다는 뜻은 아니다. |
| `InputAmount` | Intent.InputAmount | 0~1. AnimInstance에서 다시 Clamp한 뒤 유효 입력 여부 계산. |
| `MaxAcceleration` | CMC::GetMaxAcceleration | cm/s². 수집돼 있지만 현재 Native 파생 로직에서 미사용. |
| `MaxBrakingDeceleration` | CMC::GetMaxBrakingDeceleration | cm/s². 수집돼 있지만 현재 Native 파생 로직에서 미사용. |
| `MovementMode` | CMC::MovementMode | Walking/NavWalking/Falling 등을 판별. TEnumAsByte, 초기 MOVE_None. |
| `TargetGait` | Intent.TargetGait | 수집하나 현재 파생 함수에서 미사용. |
| `MaxAllowedGait` | Intent.MaxAllowedGait | 수집하나 현재 파생 함수에서 미사용. |
| `ResolvedGait` | LocomotionComponent::GetResolvedGait | AnimInstance에 복사하고 Sprint 우선 선택에 사용. |
| `RotationMode` | Intent.RotationMode | AnimInstance에 복사. 현재 회전 제어/Turn 선택을 실행하지는 않는다. |
| `bMovementAllowed` | Intent.bMovementAllowed | AnimInstance의 유효 이동 입력 gate. |

snapshot의 세 gait 선언 기본값은 Run이다. 반면 살아 있는 Intent 기본값은 Target=Walk, MaxAllowed=Sprint다. **무효 snapshot의 초기값과 유효 gameplay 값은 다르다.** Gather가 성공하면 실제 값으로 덮이고, 실패하면 bValid=false 경로가 파생 값을 Reset한다.

### 4-3. `UpdateKinematics_AnyThread()`의 순서와 변수

현재 순서는 아래와 같으며, `DeltaSeconds`는 `(void)DeltaSeconds;`로 미사용 처리한다. C++에서 원샷 시간을 적분하지 않는다.

1. snapshot Velocity/Acceleration 복사, InputAmount를 0~1로 Clamp.
2. Actor Yaw로 VelocityLocal 계산.
3. GroundSpeed와 지상/공중/입력/이동 여부 계산.
4. 이동 중일 때 MovementDirectionAngle 계산, 아니면 0.
5. ResolvedGait/RotationMode 복사.
6. `UpdateLocomotionSelection_AnyThread()` 실행.
7. `UpdateTransitionData_AnyThread()` 실행. 이 함수 끝에서 이전 frame 이력을 갱신.

| AnimInstance 변수 | 계산/갱신 | 소비와 의미 |
| --- | --- | --- |
| `VelocityWorld` | snapshot 복사 | 실제 월드 속도. 입력 벡터가 아니다. |
| `VelocityLocal` | `LessLess_VectorRotator(VelocityWorld, ActorYawRotation)` | Actor Yaw 역회전으로 표현한 속도. X 전후, Y 좌우. 메시 상대 Yaw -90을 기준으로 다시 돌리는 값이 아니다. |
| `AccelerationWorld` | snapshot 복사 | CMC 현재 가속도 관측. 현재 Stop 선택/입력 판정은 이 값으로 하지 않는다. |
| `GroundSpeed` | `float(VelocityWorld.Size2D())` | `sqrt(Vx²+Vy²)` cm/s. 수직 낙하 속도는 제외. |
| `MovementDirectionAngle` | 이동 중 `float(DegAtan2(VelocityLocal.Y, VelocityLocal.X))`, 정지 시 0 | Actor 정면에 대한 **실제 이동 방향각**. 앞 0, 오른쪽 +90, 왼쪽 -90, 뒤 ±180도. 새로운 입력의 Turn 요청각이 아니다. |
| `InputAmount` | `Clamp(Snapshot.InputAmount,0,1)` | 처리된 이동 의도의 크기. 물리 스틱 원본/속도와 구분. |
| `bIsGrounded` | Mode가 Walking 또는 NavWalking | Grounded pose/전이 조건의 사실값. |
| `bIsFalling` | Mode가 Falling | 공중 분기용. `!bIsGrounded`와 모든 MovementMode에서 동의어는 아니다. |
| `bHasMovementInput` | `Snapshot.bMovementAllowed && InputAmount > 0.01f` | **허용된 유효 이동 의도**. 장치가 눌려 있다는 원시 사실만 나타내지 않는다. |
| `bIsMoving` | `GroundSpeed > 3.f` | 실제 평면 이동 여부. 입력/허용과는 별도다. |
| `ResolvedGait` | snapshot 복사 | 허용된 요청 gait. 실측/시각 gait가 아니다. |
| `RotationMode` | snapshot 복사 | 전달된 정책 값. 현행 기본은 VelocityDirection. |

위 속도/방향 멤버는 주로 `Transient, BlueprintReadOnly`다. C++이 계산하고 ABP가 읽는다. Transient는 런타임 관측값을 영구 에셋 설정으로 저장하지 않으려는 선언이다. 모든 멤버가 반드시 현재 ABP 핀에 연결돼 있다는 뜻은 아니다.

파일 내부 상수 `MovementInputThreshold=0.01`, `MovingSpeedThreshold=3`은 각각 입력량/속도 잡음 경계다. Player의 dead zone 0.1과 목적 및 계층이 다르므로 하나의 숫자로 합치지 않는다.

### 4-4. 입력, 가속도, 속도를 혼동하지 않는 기준

- 현재 `bHasMovementInput`에 bMovementAllowed가 붙은 이유는 이 변수가 **애니메이션에 허용된 이동 명령**을 뜻하기 때문이다. 입력 원본 여부가 필요하면 별도 의미를 정의해야 한다.
- 허용이 꺼져도 관성/외력으로 Velocity가 남을 수 있으므로 bHasMovementInput=false와 bIsMoving=true는 모순이 아니다.
- CMC `GetCurrentAcceleration()`을 모든 힘을 합한 `dVelocity/dt`로 간주하지 않는다. 제동으로 속도가 줄어도 현재 입력 가속도는 0일 수 있다.
- Acceleration 크기로 입력 유사 조건을 만들 수는 있지만 그것은 지금의 Intent 기반 계약을 바꾸는 일이다. 입력 없음/이동 불허/특수 이동을 동일하게 관측한다고 가정하지 않는다.
- MovementDirectionAngle의 원래 계산 `NormalizedDeltaRotator(VelocityRotation, ActorRotation).Yaw`와 현재 수평 역회전+atan2는 평면 Yaw 기준에서 같은 목적이다. 이름/구현이 바뀌어도 이를 입력 목표각으로 재해석하지 않는다.

## 5. Loop 선택 — `LocomotionGait`

`UpdateLocomotionSelection_AnyThread()`는 먼저 `bHasGroundedMovementInput = bIsGrounded && bHasMovementInput`을 만든다. **이 조건이 true일 때만 LocomotionGait를 갱신한다.**

| 조건 순서 | 결과 |
| --- | --- |
| 유효한 지상 입력 + ResolvedGait가 Sprint | LocomotionGait=Sprint. 저속이어도 요청된 Sprint loop를 선택할 수 있다. Start는 없다. |
| 위 Sprint 조건이 아니고 bIsMoving=false | LocomotionGait=Walk. |
| 기존 LocomotionGait가 Walk가 아님 | GroundSpeed > RunExitSpeed이면 Run, 아니면 Walk. |
| 기존 LocomotionGait가 Walk | GroundSpeed >= RunEnterSpeed이면 Run, 아니면 Walk. |
| 유효한 지상 입력 없음 | 기존 LocomotionGait 유지. Stop 진입 직전/전이 중 loop가 감속 때문에 바뀌는 것을 막는다. |

`RunEnterSpeed=220`, `RunExitSpeed=190` cm/s는 AnimInstance의 `EditDefaultsOnly, BlueprintReadOnly` 튜닝이다. Walk→Run 진입 경계와 Run→Walk 이탈 경계를 나눈 히스테리시스다. 정확히 220은 Run 진입, 정확히 190은 Walk 이탈이다. 190~220 사이에서는 이전 선택의 영향을 받는다.

이 두 숫자는 Player의 170/470이나 스틱 경계 0.6과 다르다. 하나는 **어떤 pose를 보여줄지**, 다른 하나는 **어떤 속도로 움직이려 하는지**를 정한다.

| 파생 bool | 현재 식 | 의미 |
| --- | --- | --- |
| `bShouldWalkRun` | 지상 유효 입력 && LocomotionGait != Sprint | WalkRun 상태를 선택할 조건. Walk/Run 내부 선택은 enum. |
| `bShouldSprint` | 지상 유효 입력 && LocomotionGait == Sprint | Sprint loop 상태를 선택할 조건. 현재 심볼은 bShouldSprint이며 bShouldSprintLoop가 아니다. |
| `bIsStopping` | 지상 && 입력 없음 && 실제 이동 중 | 현재 물리적으로 감속/정지 중인 상황. Stop 상태 재생 중이라는 플래그가 아니다. |
| `bShouldBeIdle` | 지상 && 입력 없음 && 실제 이동 없음 | Idle 후보 조건. Stop 원샷 완료를 의미하지 않는다. |

`TargetGait → ResolvedGait → LocomotionGait → StopGait`는 중복 변수 네 개가 아니라 **요청 → 허용된 요청 → 현재 loop 선택 → 정지 진입 때 보존한 loop 선택**이라는 서로 다른 수명/책임이다.

## 6. Stop 진입 데이터 — 현재 핵심 계약

### 6-1. 변수와 수명

| 변수 | 작성 시점 | 용도 |
| --- | --- | --- |
| `bShouldEnterStop` | 매 유효 update 시작에 false, release 조건에서 그 update만 true | ABP에 Stop 진입 기회를 알리는 펄스. 현재 Stop state가 활성인지 또는 요청이 실제 소비됐는지의 확인값은 아니다. |
| `StopEntrySpeed` | Stop 진입 펄스를 만들 때만 | `Max(PreviousGroundSpeed, GroundSpeed)`. 해제 frame 감속으로 작아진 속도를 보완하는 진입 관측값. 현재 이 값으로 CMC를 제동하거나 클립 시간을 조절하지 않는다. |
| `StopGait` | 같은 시점에 PreviousLocomotionGait 복사 | Walk/Run/Sprint Stop 분기. 이후 감속으로 값이 바뀌지 않는다. |
| `StopEntryFoot` | 같은 시점에 SelectStopEntryFoot 호출 | Walk/Run LF/RF 선택용 후보. Sprint 단일 Stop에는 발 분기가 필요 없다. |
| `bShouldPlayStart` | update/Reset에서 false | 선언은 남아 있으나 Start는 사용하지 않는다. 남아 있는 변수를 Turn 요청으로 재활용하거나 Sprint에서 다시 true로 만들지 않는다. |

StopEntry*는 입력 해제 사건을 관측한 **진입 데이터**다. ABP가 실제 상태에 들어갔음을 역으로 보고한 값은 아니다. 현재 별도의 Stop request ID/소비 확인/Stop state active 멤버는 없다.

### 6-2. 이력 변수

이 값은 AnimInstance 내부 계산에만 필요하므로 private 일반 멤버다. Blueprint용 편집 값이나 플레이어 입력 상태가 아니다.

| 변수 | 이전 frame에서 보존하는 값 | 이유 |
| --- | --- | --- |
| `bHasPreviousKinematicFrame` | 유효한 이전 계산이 있었는가 | 처음 초기화한 update를 가짜 입력 해제로 판정하지 않음. |
| `bWasMoving` | 이전 bIsMoving | 현재 속도가 이미 0이어도 방금까지 움직였는지 확인. |
| `bHadGroundedMovementInput` | 이전 bIsGrounded && bHasMovementInput | 단순 무입력이 아니라 지상 입력을 방금 잃은 사건을 검출. |
| `PreviousGroundSpeed` | 이전 GroundSpeed | release frame의 급격한 감속으로 진입 속도를 잃지 않음. |
| `PreviousLocomotionGait` | 이전 LocomotionGait | 해제 직전 재생 선택과 Stop 선택을 일치시킴. |

### 6-3. `UpdateTransitionData_AnyThread()`의 실제 식

```cpp
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
        StopEntrySpeed = FMath::Max(PreviousGroundSpeed, GroundSpeed);
        StopGait = PreviousLocomotionGait;
        StopEntryFoot = SelectStopEntryFoot_AnyThread();
    }
}

bHasPreviousKinematicFrame = true;
bWasMoving = bIsMoving;
bHadGroundedMovementInput = bIsGrounded && bHasMovementInput;
PreviousGroundSpeed = GroundSpeed;
PreviousLocomotionGait = LocomotionGait;
```

- 맨 앞의 false 대입은 전이 펄스를 이전 update에서 그대로 유지하지 않게 한다. StopGait/Foot/Speed는 매번 지우지 않는다.
- `if (bHasPreviousKinematicFrame)`가 현재 올바른 코드다. 이전에 있었던 부정 조건 `!bHasPreviousKinematicFrame` 오류를 현재 결함으로 반복 보고하지 않는다.
- `bHadGroundedMovementInput && !bHasMovementInput`은 전에는 있었고 지금은 없는 edge다. 계속 무입력인 Idle에서는 반복 발생하지 않는다.
- 지상 gate는 공중 입력 해제를 지상 Stop으로 처리하지 않게 한다.
- `(bWasMoving || bIsMoving)`의 OR 덕분에 Walk 170→0으로 바로 정지한 update도 Stop에 진입할 수 있다. 현재 bIsStopping만 검사하는 방식과 다르다.
- Max는 직전/현재 두 관측 중 큰 속도를 고르는 보완이다. 실제 장치 release 시각의 연속 물리 속도를 완벽하게 복원하거나 과거 최고 속도를 누적하는 식은 아니다.
- 선택 후에 이력을 갱신한다. 이를 앞당기면 현재 값과 이전 값의 구분을 잃는다.

현재 속도가 0인 Walk 해제 frame에는 `bShouldEnterStop=true`, `bShouldBeIdle=true`, `bIsStopping=false`가 **동시에 가능**하다. ABP에서 Stop 진입 우선순위를 보장해야 한다. Stop→Idle은 단순 GroundSpeed==0이 아니라 원샷 종료 규칙을 사용한다. 이번 문서 작업에서 모든 전이 우선순위의 최신 핀을 재검증한 것은 아니다.

### 6-4. `SelectStopEntryFoot_AnyThread()`의 실제 의미

1. `GetSyncGroupPosition("Locomotion")`으로 애니메이션 동기화 그룹의 위치를 읽는다. 그룹은 에셋의 편집용 marker track 이름과 다르다.
2. 이전 마커/다음 마커가 LeftFoot→RightFoot 또는 RightFoot→LeftFoot인지 검사한다.
3. `PositionBetweenMarkers`가 유한한 0~1 값인지 검사한다. 유효한 좌우 쌍이 없거나 범위가 잘못되면 None 반환.
4. Alpha <= 0.5이면 이전 마커, > 0.5이면 다음 마커를 고른다.
5. 선택한 이름이 LeftFoot이면 Left, 아니면 Right를 반환한다.

`LocomotionSyncGroupName`, `LeftFootMarkerName`, `RightFootMarkerName`은 cpp의 파일 내부 FName 상수다. 매번 문자열을 새 의미로 해석하지 않고 같은 그룹/marker 식별자를 사용한다.

이 함수는 **시간상 가까운 접촉 마커를 기준으로 발 후보를 고르는 휴리스틱**이다. 현재 월드에서 실제로 체중을 받치는 발을 판독하거나 IK 접촉을 측정한 결과가 아니다. 그룹 결과는 엔진의 최근 완료된 평가 버퍼에서 온다. 지금 계산 중인 최종 pose를 미리 읽는 것이 아니다.

StopEntryFoot는 진입 때 고정한다. Stop→Move에서 이것을 계속 현재 발이라고 쓰지 않는다. 재입력 시점의 동기화는 진행 중인 애니메이션과 그룹 상태의 문제다.

## 7. ABP 구성과 에셋의 마지막 관측 기준

근거: 2026-09-08 Stop 검사 리포트와 같은 날짜 Animation/Engineering 기록. 이 절은 이번 문서 작업에서 Editor를 다시 열어 확인한 최신 그래프 덤프가 아니다.

### 7-1. 그래프 책임과 마지막 구조

```text
ABP_Player (Parent: UKhazanAnimInstance)
  Locomotion [상위 State Machine]
    Grounded
      GroundedLocomotion [내부 State Machine]
        Idle / WalkRun / Sprint / Stop
      → Inertialization → Grounded Output
    Airborne_TEMP
  → DefaultSlot → Output Pose
```

- Root Motion Mode의 마지막 관측값은 `Root Motion from Montages Only`다.
- WalkRun은 loop Sequence Player 두 개를 LocomotionGait enum으로 선택한다. Sprint도 별도의 loop Sequence Player다.
- 세 loop는 Sync Group `Locomotion`, Can Be Leader, Loop=true로 관측했다. Idle은 일반 반복 pose이며 보행 marker 동기화 대상이 아니다.
- Stop state는 Always Reset on Entry=true, 다섯 Sequence Player는 Loop=false다.
- Stop은 StopGait로 Walk/Run/Sprint를 선택하고 Walk/Run 내부에서 StopEntryFoot로 LF/RF를 선택한다. 마지막 관측에서 Foot 기본 분기는 LF, Right 분기는 RF였다.
- Sprint에는 단일 Default Pose만 있는 Foot enum 노드가 남아 있었지만, 연결 시퀀스는 하나다. 이 불필요할 수 있는 노드가 Sprint LF/RF 두 클립을 뜻하지 않는다. 이번에 삭제하지 않았다.
- Stop Player들은 마지막 검사에서 Locomotion / Always Leader / Leader Joining Position Override=true였다. 이 관측값을 모든 비순환 Stop에 최적이라고 승인한 결과로 읽지 않는다.
- Inertialization 노드가 연결돼 있다는 사실과 모든 전이가 Inertialization 방식이라는 주장은 다르다. 모든 edge의 방식/시간/우선순위는 별도 확인 대상이다.
- enum 노드에 직렬화된 blend time 배열만 보고 실제 핀 override까지 같은 값이라고 단정하지 않는다. 마지막 추가 관측에는 0초 override와 Run Foot 기본 핀 0.1초 차이가 있었다. 이를 발 튐의 확정 원인으로 판정하지 않았다.
- Start/Turn state의 새 구현은 확인되지 않았다. Airborne_TEMP는 완성된 Jump/Fall/Land 시스템이 아니다.

### 7-2. 전이 계약

| 경로 | 사용할 의미 |
| --- | --- |
| Idle/Stop → WalkRun | 유효한 지상 이동 입력, bShouldWalkRun. Stop은 재입력으로 중단 가능. |
| Idle/WalkRun/Stop → Sprint | bShouldSprint. Start 없이 loop로 진입. |
| Sprint → WalkRun | 이동 입력은 유지되고 시각 선택이 Walk/Run으로 바뀜. |
| WalkRun/Sprint → Stop | bShouldEnterStop 펄스. bIsStopping을 단순 대체 조건으로 쓰지 않음. |
| Stop → Idle | 원샷 완료/적절한 블렌드 시점. 재입력 경로와 구분. |
| Grounded → Airborne_TEMP | 현재 공중 임시 분기. 지상 Stop/Turn보다 상위 계층. |

위는 유지할 설계 계약이며, 모든 현재 edge의 핀/우선순위/완주를 이번에 실행 검증했다는 표가 아니다. 특히 Stop 진입과 Idle 후보가 동시에 true인 경우 및 재입력 우선순위는 회귀 검사 항목이다.

### 7-3. 현재 기본 시퀀스의 마지막 검사값

아래 경로는 `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/` 기준이다. marker 수는 2026-09-08 리포트 값이다.

| 상대 경로 | 프레임 구간 수 / 길이 | marker 수 | Enable Root Motion / Force Root Lock |
| --- | --- | --- | --- |
| `Idle/CA_P_Kazan_DualAxeSword_Off_Stand` | 249 / 10.375초 | 0 | false / false |
| `Walk/DAS_Khazan_Walk_Loop` | 33 / 1.375초 | 2 | false / false |
| `Run/DAS_Khazan_Run_Loop` | 119 / 4.958333초 | 12 | false / false |
| `Sprint/DAS_Khazan_Sprint_Loop` | 119 / 4.958333초 | 16 | false / false |
| `Walk/DAS_Khazan_Walk_Stop_LF` | 40 / 1.666667초 | 3 | false / false |
| `Walk/DAS_Khazan_Walk_Stop_RF` | 40 / 1.666667초 | 1 | false / false |
| `Run/DAS_Khazan_Run_Stop_LF` | 89 / 3.708333초 | 1 | false / true |
| `Run/DAS_Khazan_Run_Stop_RF` | 91 / 3.791667초 | 2 | false / true |
| `Sprint/DAS_Khazan_Sprint_Stop` | 114 / 4.75초 | 1 | false / true |

마지막 Root Lock 기준은 위 항목 모두 Ref Pose였다. 프레임레이트는 24 fps이며, 33프레임 구간과 0~33의 34개 키를 구분한다.

현재 Run loop 참조는 `DAS_Khazan_Run_Loop`이며 이전의 `CA_P_Kazan_DualAxeSword_Run_F`가 아니다. 사용자가 긴 Run/Sprint의 유효한 여러 주기를 보존했으므로 과거의 짧은 단일 주기로 임의로 잘라 되돌리지 않는다.

### 7-4. Stop marker 저장값과 한계

| Stop | marker 이름@초 |
| --- | --- |
| Walk LF | LeftFoot@0.002455, RightFoot@0.544413, LeftFoot@1.209577 |
| Walk RF | RightFoot@0.018979 |
| Run LF | LeftFoot@0.087311 |
| Run RF | RightFoot@0.167619, LeftFoot@0.376154 |
| Sprint | LeftFoot@0.167488 |

한쪽 marker 하나만 있는 Stop을 좌우 순환 보행 위상이 완전히 정의된 클립으로 취급하지 않는다. 끝의 양발 정착 구간과 초반의 발 접촉 구간은 재입력 조건이 다르다. marker 수와 ABP 설정을 확인한 것은 접지의 시각적 품질이 완벽하다는 증거가 아니다.

좌우는 캐릭터 자신의 발을 뜻한다. `LF/RF`는 Stop의 진입 variant, Turn 이름의 `L/R`은 회전 방향이므로 같은 분류가 아니다. Sync Marker는 발 고정/IK/자동 클립 선택 기능이 아니다. 실제 양발 동시 착지에 좌우 marker를 같은 시간으로 겹치거나 가짜 1프레임 차이를 만들지 않는다. 별도 접지 event/curve를 채택하면 새 계약으로 다룬다.

### 7-5. Root, 복사 원본, 기존 편집의 보호

- 사용자 방침은 Stop을 인플레이스로 사용하는 것이다. 관측 설정은 Run/Sprint ForceRootLock=true, Walk 두 개는 false였다. 설정 차이만으로 Walk root 이동이나 결함을 단정하지 않는다.
- 현재 본 계층은 `C_P_Kazan(scale 100) → Root → Bip001`이다. `Root`라는 이름의 본이 최상위가 아니다. 최상위 Root Lock만으로 자식 Root의 모든 키가 고정된다고 생각하지 않는다.
- Run/Sprint Stop에서는 이전에 자식 Root의 움직임을 최상위 C_P_Kazan에 합성한 복사본을 만들었다. 자세한 식/검사 범위는 [STOP_ROOT_TRANSFER_2026-09-08.md](STOP_ROOT_TRANSFER_2026-09-08.md)를 참조한다. 이 처리는 Skeleton의 본 삭제가 아니다.
- 원본 시퀀스는 Weapons 쪽에 보관돼 있다. 원본/작업 복사본/현재 ABP 참조를 구분한다. `DAS_*` 접두사만으로 미편집 원본, 복사 이력, ABP 채택 여부를 보장하지 않는다. 원래 `_New` 생성 시 검사와 이후 일반 이름으로 관측한 시퀀스의 모든 편집 이력이 같다고 단정하지 않는다.
- Walk/Run/Sprint loop에는 사용자가 첫 pose를 마지막 sample로 복사한 편집이 있다. 복구 후 전체 본 RAW/압축 pose의 끝점 검사는 3/3 통과했다. 원본과 다르다는 이유로 이 편집을 되돌리지 않는다. 끝점 pose 일치만으로 속도 연속성/발 미끄러짐까지 보장하지 않는다.
- Root Lock은 Foot Lock이 아니다. 캡슐 제동 거리, 원래 보폭, 재생 속도, 전이, 발 접촉은 분리해 평가한다.
- 249프레임이라는 이유로 일괄 단축하지 않는다. Turn에 Stop의 변환/길이를 검사 없이 적용하지 않는다. 작업 범위 밖의 본 트랙이나 무기·상체 동작을 삭제하지 않는다.

## 8. 검증된 범위와 미완료의 구분

### 8-1. 완료/관측의 종류

| 항목 | 근거와 범위 |
| --- | --- |
| 입력/속도/loop/Stop 사용자 구현·시험 | 사용자 보고. 대체로 제어되지만 발이 조금 튄다는 보고가 있다. 어시스턴트의 전체 자동 테스트 합격으로 바꿔 기록하지 않는다. |
| 현재 C++ 데이터 계약 | 이번에 소스를 다시 읽었다. snapshot/AnyThread, gait 선택, Stop 해제 판정과 진입 데이터 고정을 확인했다. |
| 마지막 새 프로세스용 빌드 | 2026-09-08 `KhazanEditor Win64 Development` UBT 성공, DLL 시각 15:53:56. 이번에 새로 빌드한 결과는 아니다. |
| 실제 PIE Stop 진입 데이터 | 같은 날 Enhanced Input action 주입→Controller/Player/CMC/AnimInstance 경로에서 아래 값을 관측했다. |
| 에셋 저장/복구 검사 | 별도 프로세스의 Root 이동 합성 3/3, loop 끝점 3/3 등이다. 각 저장 리포트에 명시한 대상/버전의 검사이며 현재 전체 PIE 동작 보증이 아니다. |

| 해제 gait | 직전 속도 | 현재 속도 | StopEntrySpeed | StopGait | StopEntryFoot | bShouldEnterStop |
| --- | ---: | ---: | ---: | --- | --- | --- |
| Walk | 170 | 0 | 170 | Walk | Right | true |
| Run | 470 | 392.245117 | 470 | Run | Left | true |
| Sprint | 600 | 502.935822 | 600 | Sprint | Right | true |

위 값은 NativeThreadSafeUpdateAnimation→UpdateTransitionData_AnyThread의 Foreground Worker #0/#1 실행에서 관측했다. 모든 좌우 클립, 상태 전이 완료, 발 접촉의 시각적 품질, 실제 게임패드/IMC 전체까지 검증한 표는 아니다.

### 8-2. 미완료/미확정

- Stop의 모든 ABP 전이, 모든 variant 완주, 중간 재입력, 공중 전이, 낮은 FPS의 포괄 검사.
- 32초 추가 PIE 검사 결과 회수. 예약했다는 이유로 합격 처리하지 않는다.
- 가벼운 발 튐의 근본 원인. marker/진입 pose/root/제동/블렌드 중 어느 것으로도 아직 확정하지 않았다.
- 전체 Stop의 top/child root 잔류 변위, 단일 marker와 끝 구간의 group 동작에 대한 추가 시각 검사.
- LookingDirection/LockOn gameplay 회전, Turn 선택/상태/회전 연계, 공중 전용 pose, 무기 레이어 등.

이전 검증에는 어시스턴트의 잘못된 anim-node index 추측으로 Editor가 종료된 사건이 있었고, 이후 다른 실행에서는 캡처/디버거 통신이 중단됐다. 두 번째 중단의 근본 원인은 미확정이며 사용자 Stop 코드의 결함으로 취급하지 않는다. 이번에는 해당 Editor 상태를 재확인하거나 조작하지 않았다.

실행/중단점/callback의 정확한 재개·정리는 [ENGINEERING_WORK_CONTINUITY.md](../Engineering/ENGINEERING_WORK_CONTINUITY.md)의 2026-09-08 절을 읽는다. 확인하지 않은 이전 PID/session이 현재도 유효하다고 가정하지 않는다. **추측한 0/1 상태 머신 index로 GetCurrentStateName을 다시 호출하지 않는다.** 이 문서 작성을 검사 세션 복구 완료로 기록하지 않는다.

## 9. 다음 Turn 작업의 경계 — 아직 구현하지 않음

사용자 최신 요구는 모든 Start를 제외한 상태로 Turn에 진행하는 것이다. 다만 이번 요청은 현재 상태의 문서 정리이므로 새 Turn 코드/그래프 설계를 적용하지 않는다.

다음 설명에서는 아래 기존 사실을 지킨다.

1. `MovementDirectionAngle`을 새 입력의 Turn 요청각으로 재활용하지 않는다. 실제 속도와 새 의도, Actor의 정면은 다른 값이다.
2. 현재 CMC가 자동 회전을 소유한다. RotationMode enum만 추가해 회전 권한 전환이 구현되지는 않는다. AnyThread에서 Actor 회전을 직접 변경하지 않는다.
3. 이동 중 Turn과 명시적인 정면 목표가 필요한 TurnInPlace를 구분한다. 자유 시점에서 카메라만 돌렸는데 캐릭터도 회전하는 사양을 임의로 추가하지 않는다.
4. 현재 구현에 Turn 방향 이력, 요청 소비, 재생 중 선택 고정, 재입력 중단, root 회전 조정이 있다고 가정하지 않는다. 필요성을 설명한 뒤 설계한다.
5. C++에 일반 로코모션 Montage 제어와 독자적인 재생 Phase 시계를 복원하지 않는다. ABP 재생 수명과 gameplay 회전 책임을 나눈다.
6. 에셋 이름/marker 의미를 실제 자료와 대조한다. Run 90도 MovingTurn이 있다는 전제로 구현하지 않는다.

InGame의 마지막 Turn 목록은 2026-09-07 표적 감사가 근거다. 아래 이름은 상대 경로이며 길이/marker/root는 당시 기록이다. 사용 준비 완료를 뜻하지 않는다.

| 용도 후보 | 존재가 기록된 상대 경로 |
| --- | --- |
| Walk StandTurn 180 L/R | `Walk/CA_P_Kazan_DualAxeSword_Walk_StandTurn_L_180` / `..._R_180` |
| Run StandTurn 180 L/R | `Run/CA_P_Kazan_DualAxeSword_Run_StandTurn_L_180` / `..._R_180` |
| Run MovingTurn 180 L/R | `Run/CA_P_Kazan_DualAxeSword_Run_MovingTurn_L_180` / `..._R_180` |
| Sprint MovingTurn 90 L/R | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_90` / `..._R_90` |
| Sprint MovingTurn 180 L/R | `Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_180` / `..._R_180` |

당시 10개 모두 249구간/10.375초, marker 없음, Root Motion/Force Root Lock=false였다. 그 이후 새 trim/marker/root 준비를 완료한 증거는 이번에 얻지 않았다. Walk/Run StandTurn을 무조건 MovingTurn의 대체로 배정하지 않는다.

## 10. 근거 자료와 오독 방지

### 현재 상태를 뒷받침하는 자료

| 자료 | 읽는 목적 |
| --- | --- |
| [KhazanAnimInstance.h](../../Source/Khazan/Animation/KhazanAnimInstance.h) / [.cpp](../../Source/Khazan/Animation/KhazanAnimInstance.cpp) | 실제 선언, 식, 호출 순서, Reset 재확인. |
| [KhazanPlayer.h](../../Source/Khazan/Character/KhazanPlayer.h) / [.cpp](../../Source/Khazan/Character/KhazanPlayer.cpp) | 속도/입력 설정, L3, AddMovementInput 계약. |
| [KhazanLocomotionType.h](../../Source/Khazan/Character/Locomotion/KhazanLocomotionType.h) | enum과 Intent의 현재 이름/초기값. |
| [KhazanLocomotionComponent.cpp](../../Source/Khazan/Character/Component/KhazanLocomotionComponent.cpp) | setter, 입력 지우기, 허용된 gait. |
| [Stop 검증 리포트](../../Saved/ImportReports/Khazan_InGame_Stop_Verification_20260908.json) | 마지막 Stop metadata/그래프와 실제 PIE 데이터, 검사 한계. |
| [InGame 대상 감사](../../Saved/ImportReports/Khazan_InGame_Locomotion_Audit_20260907.json) | Turn 등 처음 확인한 InGame 목록. 과거 loop marker 수/Start 방침은 현재 값이 아니다. |
| [loop 끝점 검사](../../Saved/ImportReports/Khazan_DAS_LoopClosure_verify_20260908.json) | 사용자 loop 마지막 pose 편집을 유지하는 근거. |
| [Stop root 합성 검사](../../Saved/ImportReports/Khazan_DAS_StopRootTransfer_verify_20260908.json) | 당시 세 복사본의 변환/pose 검사. |
| [SKELETON_RECOVERY_2026-09-08.md](SKELETON_RECOVERY_2026-09-08.md) | 본 트랙 복구와 loop 끝점 재적용의 범위. |

### 과거 이름/제안을 현재 구현으로 취급하지 않기

| 과거 자료의 표현 | 현재 처리 |
| --- | --- |
| `MovementDirection`, `MovementAngle` | 현재 실명은 `MovementDirectionAngle`. 의미는 Actor 기준 실제 이동 방향각. |
| `IsWalking`, `bUseRun`, `bUseRunStop`, `RunStopSelectionSpeed` | 이번 Source 검색에서 현행 심볼이 아니다. loop는 LocomotionGait, Stop은 StopGait 사용. |
| `bShouldSprintLoop` | 현재 실명은 `bShouldSprint`. |
| `StopFoot` | 현재 실명은 `StopEntryFoot`. |
| Sprint LF/RF Stop 필수 | 현재는 Sprint 단일 `DAS_Khazan_Sprint_Stop`. |
| SprintStart 구현이 다음 단계 | 사용자 취소. 모든 Start를 사용하지 않는다. |
| C++ 수동 state/phase, LocomotionProfile, RT_DAS_* 동작 확인 | 현재 InGame 구현/합격 증거가 아니다. 복원하지 않는다. |

`build_dual_axe_locomotion_assets.py`, 구형 `audit_khazan_locomotion.py`, 구형 `run_locomotion_pie_trace.py`는 현재 데이터 계약의 재생성/검증 절차로 실행하지 않는다. 기존 단계 가이드의 예제 코드도 현재 소스와 대조하지 않고 일괄 적용하지 않는다.

## 11. 앞으로의 작업 시작·종료 체크

시작할 때:

1. Router → 이 정본 → 요청에 필요한 소스/저장 리포트만 읽는다. 과거 단계 가이드에서 구현 상태를 추측하지 않는다.
2. 사용자 최신 방침, 현재 실제 심볼, 각 값의 작성자/소비자/갱신 시점을 확인한다.
3. 설명, 진단, 구현, 테스트, 문서 변경 중 무엇을 요청받았는지 구분한다. 설명만 요청받고 게임 파일을 변경하지 않는다.
4. BP/에셋의 현재 값이 필요하면 마지막 관측일을 확인하고 필요한 대상만 검사한다. 과거 저장 리포트와 현재 미저장 Editor 상태를 동일시하지 않는다.
5. 기존 데이터로 충분한지 먼저 확인한다. 같은 의미의 bool/enum/직전 frame 이력을 다른 클래스에 중복 추가하지 않는다.

종료할 때 다음 형식으로 이 문서 하단에 추가한다.

```text
## YYYY-MM-DD 변경/확인 제목
- 최신 방침 변경:
- 대상 파일과 실제 변경 주체:
- 추가/변경 변수: 타입, 단위, 의미, 작성자, 소비자, 갱신/고정/Reset 시점
- 추가/변경 함수: 소유 클래스, 역할, 호출 순서, 스레드 경계
- ABP/에셋에 실제 적용한 내용:
- 제안만 하고 아직 적용하지 않은 내용:
- 검증: 실행일, 대상 버전, 방법, 결과, 미검증 범위
- 남은 작업과 다음 정확한 절차:
```

## 2026-09-08 이번 문서 통합 결과

- 현재 C++와 기존 검사 증거를 구분한 정본을 새로 추가했다. 새 Turn 코드, enum, ABP, 시퀀스 편집은 추가하지 않았다.
- 모든 Start 제외를 현재 방침으로 반영했다. 기존 5단계 제안은 취소이며 구현 완료에 포함하지 않는다.
- Router/AGENTS와 기존 Animation·Engineering 문서에 이 정본을 먼저 참조하는 규칙을 추가한다.
- 다음에는 이 문서의 데이터 계약을 기준으로 Turn을 설명한다. 현재 Stop 부분 검증을 전체 테스트 완료로 격상하지 않는다. 미회수 검사 세션을 재개할 경우에만 Engineering continuity의 안전 절차를 확인한다.
- 문서 검증: 기존 7개 문서의 원문을 줄바꿈 형식 정규화 후 비교해 내용 보존을 확인했다. 정본의 로컬 링크 13개가 존재하고, 이번에 보호 대상으로 잡은 관련 소스/에셋 25개의 SHA-256은 변경되지 않았다. 이는 문서/파일 보존 검사이며 게임 빌드나 PIE 검증이 아니다.

## 2026-09-08 Turn 적용 범위 요청과 Sprint 동작 의미 확인 대기

- 새 사용자 요청: Walk에 Turn 두 동작을 넣고 Sprint에는 전용 Turn을 쓰지 않는다. Run은 문장 앞부분의 포함 표현과 뒷부분의 제외 표현이 충돌하므로, 마지막의 "run은 안넣을거야"를 기준으로 제외하는 것으로 잠정 해석한다. 모든 Start 제외 방침은 유지한다.
- Walk 두 동작의 기존 InGame 후보는 좌/우 StandTurn 180이다. 이번에 에셋을 새로 검사하거나 연결하지 않았다.
- Sprint의 "180근처 방향 전환이면 Stop모션을 취소하고 다시 Sprint"는 재생 중 Stop을 즉시 끊고 재가속하는 것인지, Stop으로 제동 동작을 보여준 뒤 반대 방향 Sprint로 이어가는 것인지 확인이 필요하다. 서로 다른 전이 정책을 임의로 확정하지 않는다.
- 소스 재확인: UpdateTransitionData_AnyThread는 지상 유효 입력 상실에만 Stop 요청을 만든다. 유효 입력이 계속 유지되면 방향 180도 변경 자체로 Stop 요청을 만들지 않는다. Player의 HandleInputMoveReleased는 토글 모드에서 bSprintRequested=false로 만든다. 따라서 스틱 중앙 통과가 입력 해제로 처리될 경우 Sprint 재개에는 현재 요청 수명 정책도 고려해야 한다.
- 이번에는 위 범위/미확정 사항만 기록했다. Turn/Sprint 전이의 새 변수·함수·ABP를 제안 확정하거나 구현하지 않았고, 빌드/PIE도 수행하지 않았다. Sprint 의도 확인 후 현행 데이터 계약에 맞춰 상세 절차를 설명한다.

## 2026-09-08 Sprint 급반전 의미 확정 및 애니메이션 시간축 재검사

### 최신 방침과 실제 적용 여부

- 사용자가 Sprint 동작을 확정했다: Sprint 중 180도에 가까운 새 방향 입력에서 **Sprint Stop 시퀀스의 짧은 제동 구간을 Turn처럼 사용하고 반대 방향 Sprint로 이어간다. 일반 Stop 상태에 들어가는 동작이 아니다.** 위 “Sprint 동작 의미 확인 대기”는 해소됐다.
- Walk 좌/우 Turn 두 동작, Run Turn 제외(사용자 마지막 제외 표현 우선), 모든 Start 제외 방침을 유지한다.
- C++/ABP에 새 Turn 변수, 함수, enum, 상태는 아직 구현하지 않았다. 아래 `SprintPivot`은 설명을 위한 제안명이며 현재 심볼이 아니다.

### 기존 데이터와 섞지 않을 설계 계약 — 아직 미구현

- 에셋 재사용과 상태 재사용을 구분한다. 제안 흐름은 `Sprint → SprintPivot → Sprint`이며 Pivot 내부의 별도 Sequence Player가 기존 `DAS_Khazan_Sprint_Stop`을 참조한다. 일반 Stop의 재생 cursor/진입 데이터/완주 규칙을 공유하지 않는다.
- `StopGait`, `StopEntryFoot`, `StopEntrySpeed`, `bShouldEnterStop`, `bIsStopping`은 기존 의미를 유지한다. Pivot 포즈를 재생시키려고 유효 입력을 지우거나 `bMovementAllowed=false`로 만들지 않는다.
- `EKhazanGait::Sprint`는 이동 의도/보행 종류다. 제동 중 실제 GroundSpeed가 감소한다고 Sprint 의도가 반드시 사라지는 것은 아니다. Turn/Pivot의 임시 동작 구분은 Gait 및 일반 Stop 진입 데이터와 별개의 역할이다.
- 급반전 각도는 실제 진행 방향(필요 시 반전 직전 방향 보존)과 새 planar 입력 방향 사이에서 판단한다. 기존 `MovementDirectionAngle`은 Actor 기준 실제 velocity 각도이므로 같은 변수로 재해석하지 않는다. 저속/무입력 처리와 반복 재진입 방지 조건이 필요하다.
- Root Lock 상태의 Stop 포즈는 캡슐을 자동 제동/회전시키지 않는다. 실제 제동·회전·재가속은 Character/Locomotion 측 game-thread 이동 정책, AnimInstance는 snapshot/표현 데이터, ABP는 pose/전이를 담당하는 구조로 설명한다. worker-thread 계산에서 Character/CMC를 변경하지 않는다.
- 제동 동안 raw intent와 실제 CMC에 보내는 이동 명령을 분리한다. 새 방향을 그대로 AddMovementInput하면서 Stop 포즈만 덮으면 이미 반대 방향으로 가속 중인 몸에 제동 포즈를 섞게 될 수 있다.
- 현 Player는 deadzone 진입 시 `HandleInputMoveReleased`로 토글 `bSprintRequested`를 지운다. 스틱 중앙 통과 급반전은 짧은 입력 공백과 진짜 입력 해제를 구별하는 정책/테스트가 필요하다. Sprint 요청을 무조건 영구 유지하거나 L3 없이 새 Sprint를 시작하는 변경은 하지 않는다.
- Pivot 해제/취소 시 입력, 지상 여부, Sprint 허용 상태를 재검사한다. 입력 해제, L3 취소, 공중/피격 등은 무조건 반대 Sprint 재개와 구별한다. Sprint Stop에는 LF/RF 두 variant가 없으므로 가짜 variant를 만들지 않는다.
- Pivot 해제 시점, root 회전 처리, Sync Group 역할, enum의 정확한 소유 클래스/API는 시간축/유효 제동 구간 확인 후 상세 설명에서 정한다. 일반 Stop의 전체 길이/marker 정책을 그대로 복사하지 않는다.

### 이번에 직접 확인한 시간축과 최신 marker 관측

- InGame 11개(Idle, loop 3, Stop 5, Walk Turn 2)는 모두 24/1 fps, RateScale 1.0이다. ABP Sequence Player 10개는 PlayRate/PlayRateBasis=1.0, PlayRate 입력 핀 외부 연결 없음이다. 새 빌드/PIE/실제 시간 배속 측정은 하지 않았다.
- PSA 11개의 N/R와 공개 exporter 계산 규칙에서 복원한 유효 sample 간격은 약 30 fps다. 6개 FBX 키 시간은 1/24초 격자이며, source/InGame 각각 5개 표적 본 회전 변화는 PSA 연속 frame +1과 대응한다.
- 기존 “현재 24 fps”는 정확한 import 관측이다. 이를 원작의 정확한 속도로 해석하지 않는다. 동일 키 구간의 1.25배 재생 비교가 근거 있는 다음 검사이며 **이번에 RateScale/PlayRate/프레임레이트/marker를 변경하지 않았다.**
- 시간축/원작 RateScale 해석의 한계와 clip trim 차이는 [Art 시간축 검사](../Art/DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md)에 분리 기록했다. 상세 데이터는 `Saved/ImportReports/Khazan_Locomotion_Timing_Audit_20260908.json`을 재사용한다.
- 7-4 표 이후 현재 Editor marker 읽기에는 다음 차이가 있다. Walk Stop LF: LeftFoot@0.004655. Walk Stop RF: RightFoot@0.004655, LeftFoot@1.549214. Run Stop RF의 두 번째 LeftFoot: @0.879554. 나머지 Stop marker는 이전 관측값과 같다. 이번 어시스턴트 편집이 아니라 현재 에셋 관측이며 저장 여부/편집 주체/시각 품질은 단정하지 않는다.

### 남은 작업과 다음 순서

1. 시간축 증거에 근거한 1.25배 비교/보정 방법을 사용자에게 설명한다. 실제 일괄 속도 수정은 사용자 요청 없이 수행하지 않는다.
2. 기준 속도를 결정한 뒤 Walk 두 Turn의 유효 구간과 Sprint Stop의 Pivot용 제동/해제 구간을 확인한다. 현재 Walk Turn은 아직 249구간/10.375초 임포트본이다.
3. 확정된 범위에서 변수 소유/수명/Reset, 함수 호출 순서/스레드, CMC 회전과 ABP 전이를 줄별로 설명한다. 사용자가 직접 구현하는 기존 방식으로 진행한다.

## 2026-09-08 Walk 170 / Run 470 / Sprint 600의 출처 구분

- 현재 세 값은 원작 게임 메타데이터에서 추출하거나 애니메이션 보폭과 대조해 확정한 이동 속도가 아니다. 현재 프로젝트의 이동 설정값과 원작 검증값을 구분한다.
- Walk 170 / Run 470의 현 구현 채택 근거는 사용자의 “작은 스틱 입력은 170, 임계값 초과는 470” 요구다. 사용자가 그 수치를 최초에 어디서 얻었는지까지 이번에 확인한 것은 아니며, 원작 gameplay metadata로 대조 검증하지 않았다.
- Sprint 600은 어시스턴트가 구현/테스트 가이드에서 제안한 기본 튜닝값이다. [INGAME_LOCOMOTION_STEP_2.md](INGAME_LOCOMOTION_STEP_2.md) 9행 및 492행에는 애니메이션에서 측정한 속도/최종 튜닝값이 아니라고 명시돼 있다. 600을 원작 Sprint 최대 속도로 설명하지 않는다.
- 현재 선언은 KhazanPlayer.h의 WalkSpeed=170, RunSpeed=470, SprintSpeed=600이며, RefreshLocomotionGait가 CMC MaxWalkSpeed에 대입한다. EditDefaultsOnly이므로 BP override 가능성은 별도다. 이번에는 현재 C++/기존 기록만 확인했으며 BP/PIE를 새로 검사하지 않았다.
- AnimInstance의 GroundSpeed=VelocityWorld.Size2D()는 실제 속도를 관측하는 계산이지 시퀀스에서 적정 이동 속도를 산출하는 계산이 아니다. 이전 170/470/600 실행 관측은 설정 적용 검증이며 원작 속도 일치나 발 미끄러짐 해소 검증이 아니다.
- 앞선 1.25배는 애니메이션 시간축 비교 후보이지 이동 속도 세 값에 자동 적용할 보정 배율이 아니다. 현재 코드/속도/ABP/시퀀스는 변경하지 않았다. 원작 이동값 확인 또는 보폭/접지 기반 속도 적합성 검증은 별도 미수행 작업이다.

## 2026-09-08 이후 수치 안내는 원작 메타데이터 근거 필수

- 사용자 최신 지시로, 앞으로 로코모션의 수치는 원작 메타데이터를 출처로 안내한다. 속도뿐 아니라 가감속, 회전율/각도 임계값, 입력 threshold/deadzone, 재생률, blend/Stop/Pivot 시간과 해제 조건의 거리·비율에도 적용한다. 임의값을 예제 코드에 넣고 나중에 튜닝하는 방식으로 진행하지 않는다.
- 매 수치의 기록 형식: **항목/변수 → 원작 package/파일 경로 → property/field/curve/key → 원시 값과 단위 → 적용 조건 → 필요한 변환식 → 확인 상태**. 원본 직접 확인, 원본 기반 계산, 미확인을 구분한다. 원본 버전과 override/배율이 결과에 영향을 주면 함께 기록한다.
- 원본에서 찾지 못한 값은 미확인으로 남긴다. 이를 적당한 숫자나 엔진 기본값으로 대체하지 않는다. 수치가 필수인 다음 단계는 필요한 원작 자료를 먼저 확인하고, 대체 튜닝이 필요하면 사용자 결정이 선행해야 한다. 구조/책임 설명은 수치 없는 변수/조건으로 진행할 수 있다.
- 기존 Walk 170 / Run 470 / Sprint 600은 위 출처 구분 절의 상태를 유지한다. 현재 적용값이지 원작 메타데이터 검증값이 아니다. 정본의 다른 기존 튜닝값도 원작 출처를 제시하지 못하면 원작 확정값으로 재사용하지 않는다. 이번에 기존 수치를 변경하거나 모든 값의 원작 대조 조사를 수행한 것은 아니다.
- 앞선 1.25배는 PSA/FBX 시간 정보와 추출 규칙에 근거한 비교 계산값이다. 원작 최종 PlayRate에 직접 기록된 값이 아니며 해당 보고서의 가정/미확인 범위를 유지한다. 이를 원작 이동 속도의 보정 배율로 확장하거나 자동 적용하지 않는다.
- 다음 Walk Turn/SprintPivot 상세 절차에서는 진입 각도 임계값, 제동·회전·해제 시점, 재진입 방지 시간, 스틱 중앙 통과 판정 시간 등을 원작 근거 없이 숫자로 확정하지 않는다. 근거가 확보되지 않은 단계는 미확인 항목과 필요한 자료를 먼저 설명한다.
- 모든 Start 제외, Walk 두 Turn/Run Turn 제외/Sprint Stop 시퀀스의 Pivot 재사용, InGame 한정, 사용자가 직접 구현하는 책임 계약은 유지한다. 이번 변경은 AGENTS.md/Engineering 규칙/이 정본에 수치 출처 규칙을 추가한 것이며 C++/ABP/시퀀스 변경과 새 빌드/PIE는 없다.

## 2026-09-08 SprintPivot 준비와 공동 구현 1단계 안내 — Source 미적용

### 최신 요청과 진행 방식

- 요청 동작은 Sprint 중 거의 반대 방향 입력에서 Sprint Stop 시퀀스의 제동 구간을 잠깐 사용한 뒤 반대 방향 Sprint로 이어가는 것이다. 별도 SprintPivot 동작이며 일반 Stop 상태 진입이 아니다. 이번 요청 범위는 SprintPivot이고, Walk 두 Turn은 후속 별도 작업이다. 모든 Start/Run Turn 제외와 InGame 한정 정책을 유지한다.
- 사용자가 직접 구현하도록 변수·함수·코드 각 줄·계산·클래스 책임·에디터 조작·검증을 설명하는 방식을 AGENTS.md에 고정했다. 이번에 게임 소스/ABP/에셋은 직접 수정하지 않았다.
- 새 설명 문서: [INGAME_SPRINT_PIVOT_STEP_1.md](INGAME_SPRINT_PIVOT_STEP_1.md). 제안 코드를 Source에 생성/적용하지 않은 가이드다. 준비 관측은 [Khazan_SprintPivot_Preparation_20260908.json](../../Saved/ImportReports/Khazan_SprintPivot_Preparation_20260908.json)에 기록했다.

### 현재 확인과 수치 제약

- 기존 PSA metadata, locomotion source survey, timing report를 재사용했다. Sprint Stop PSA의 동명 JSON 및 원본 PC/Kazan 경로의 BP/ABP/Locomotion/Sprint/Movement/Turn 관련 JSON 이름을 표적 확인했으나 원작 Pivot 진입 각도, 제동 해제 event/time, 입력 중앙 통과 규칙은 확보하지 못했다. 원작 전체에 해당 자료가 없다는 결론은 아니다.
- 원작 출처 없는 진입 각도, 최소 속도, 제동/회전/전이 시간, 재진입 유예, 입력 유예 시간을 추가하지 않는다. PSA 총길이와 발 Sync Marker를 Pivot 해제 시점의 근거로 대체하지 않는다. 필요한 원작 BP/DA/DT JSON 위치를 사용자에게 요청했다.
- 현재 Editor PID 32936에서 InGame Sprint Loop/Stop의 FrameRate=24/1, RateScale=1.25를 읽었다. 이전 1.0 관측 이후의 현재 값이며 이번 어시스턴트가 변경한 값이 아니다. 저장 여부/편집 주체는 단정하지 않는다. 1.25를 원작 runtime PlayRate의 직접 metadata 값으로 재분류하지 않는다.
- InGame Sprint Stop은 114구간/4.75초, EnableRootMotion=false, ForceRootLock=true였다. 해당 Stop/Loop와 Weapons Sprint Stop import의 AnimNotify/float curve/transform curve/Editor metadata tag는 비어 있었다. 이는 발 Sync Marker의 존재 여부를 판단한 검사가 아니다.

### 이번 가이드의 제안 계약 — 아직 현행 구현 아님

| 대상 | 제안 의미와 책임 |
| --- | --- |
| Character/Locomotion/KhazanLocomotionMath.h/.cpp | 새 일반 C++ 파일. TryCalculateMovementInputAngle이 VelocityWorld와 MoveInputWorld의 평면 signed angle을 계산. UObject/CMC/상태/재생을 건드리지 않는 공통 함수 |
| AnimInstance MovementInputAngle | 실제 진행 방향 대비 새 월드 입력의 각도, 단위 deg. 기존 MovementDirectionAngle(Actor 정면 대비 속도 방향)과 구분 |
| AnimInstance bHasValidMovementInputAngle | 이번 관측 각도의 유효성. Pivot 상태나 진입 요청 bool이 아님 |
| UpdateMovementInputAngle_AnyThread | 기존 snapshot의 VelocityWorld/MoveInputWorld만 읽어 관측 멤버 둘을 매 update 초기화/계산. 지상/입력/이동 사실값 계산 뒤, 기존 selection/Stop 이력 갱신 전 호출 |
| ResetDerivedData_AnyThread | 새 관측값 0/false를 수명주기/invalid snapshot 경로에서도 초기화 |

- Snapshot에는 필요한 두 벡터가 이미 있으므로 중복 필드를 추가하지 않는다. Player/Controller/LocomotionComponent/gait enum/일반 Stop 데이터는 이번 첫 단계에서 바꾸지 않는다.
- 계산은 normalize2D → dot/cross.Z → DegAtan2이다. 0/±90/±180은 기하학 결과이며 원작에서 정해야 하는 Pivot threshold가 아니다. GetSafeNormal2D 기본 수치 안전성은 원작 최소 Sprint 속도/입력 deadzone 근거가 아니다.
- 공통 함수는 이후 game-thread 입력 처리에서도 재사용한다. 최종 Pivot 진입 판정은 새 반대 방향 이동 명령을 CMC에 적용하기 전의 진행 방향과 비교해야 한다. AnimInstance 관측은 물리 처리 후 반전 순간을 놓칠 수 있으므로 최종 gameplay 판정의 권위로 사용하지 않는다.

### 후속 구현 경계

- 전체 흐름은 Sprint → SprintPivot → Sprint. SprintPivot용 별도 Sequence Player가 같은 Sprint Stop asset을 참조할 수 있지만 일반 Stop 상태/StopGait/StopEntryFoot의 입력 해제 계약을 바꾸지 않는다.
- Root Lock된 제동 포즈는 캡슐을 제동/회전시키지 않는다. 실제 제동·회전·재가속과 Pivot 단계는 game thread의 Player/Locomotion 계층, 그 값 전달은 snapshot, 포즈/블렌딩은 ABP 책임으로 설명할 예정이다. 최종 멤버/enum/API는 아직 구현하지 않았다.
- 반대 방향 입력 의도와 L3 Sprint 요청을 보존한다. ClearMoveInput 또는 bMovementAllowed=false로 일반 Stop을 위장하지 않는다. 현행 중앙 통과 시 Sprint 토글 해제 문제는 별도 입력 정책 근거가 필요하다.
- Pivot 중 bShouldSprint가 유지될 수 있으므로 그 bool만으로 즉시 Sprint 복귀시키는 전이를 만들지 않는다. 제동 해제 조건과 취소 조건을 구분해야 한다.

### 검증과 다음 단계

- 엔진 Python의 대응 수학 함수로 정면/좌/우/반대/회전된 기준/Z 제외/영속도/영입력의 8개 참조 사례를 확인했고 모두 기대값과 일치했다.
- 이는 제안 C++의 컴파일/호출 검사나 Pivot 재생·제동·회전 PIE 검증이 아니다. 새 C++ 빌드/PIE, 기존 미회수 Stop 검사/중단점/callback 정리는 수행하지 않았다.
- 사용자는 가이드의 방향 계산/관측 첫 단계만 먼저 적용할 수 있다. 실제 Pivot 단계의 수치 확정이 필요한 부분은 원작 자료 확보 전까지 미확인이다. 이후 Router → 이 정본 최신 절 → 새 가이드 → 사용자가 실제 변경한 소스 → 제공된 원작 자료 순서로 재개한다.

## 2026-09-08 수치 정책 개정과 SprintPivot 설명 재개 가능

- 사용자 최신 지시: 최대한 원작 metadata를 우선하지만, 필요한 경우 어시스턴트가 임의 수치를 선정하고 임시값임을 명시해 사용할 수 있다. 앞선 원작 수치 필수 절과 SprintPivot 준비 절의 “원본 근거가 없으면 수치가 필요한 구현 설명을 보류” 조건을 대체한다.
- 원작 직접 확인 / 원작 기반 계산 / 임시 튜닝값을 구분한다. 임시값은 선정 이유·단위·동작 영향·검증과 조정 기준을 설명하고, 조정 가능한 설정에 모아 이후 교체 비용을 줄인다. 기존 미검증 속도 등은 이번 승인으로 원작 검증값이 되지 않는다.
- SprintPivot 진입 각도, 제동·회전·해제 시점, 전이/재진입 및 입력 중앙 통과 관련 값은 기존 자료를 우선 확인하고, 필요한 근거가 없으면 명시된 임시값으로 다음 설명을 진행할 수 있다. 원작 BP/DA/DT JSON 제공은 더 이상 필수 재개 조건이 아니다.
- 원작 Stop의 길이/발 marker를 곧바로 원작 Pivot 해제 조건이라고 부르지 않는다. Stop을 재사용하는 현재 설계에 맞춰 고른 제동 구간/시간은 확인 근거에 따라 관측·계산·임시 튜닝으로 구분한다.
- Sprint → SprintPivot → Sprint, 일반 Stop과 별도 상태, L3 Sprint 의도 보존, game-thread 이동 제어와 snapshot/ABP 표현 분리, 모든 Start/Run Turn 제외 및 InGame 한정은 유지한다.
- 사용자가 직접 구현하도록 각 줄과 변수/함수/클래스 이유/에디터 작업을 설명하는 방식은 유지한다. 이번 변경은 지침과 관련 문서의 날짜별 추가뿐이며, 새 수치 선정/Source 적용/ABP·에셋 편집/빌드·PIE는 없다.

## 2026-09-08 캐릭터 전체 아키텍처 검토와 Math 선행 추가 제안 철회

- 사용자 최신 요청은 HeinMach/StormPass 전체 모작과 Player/몬스터/보스의 이동·대시·공격·스킬·피격 확장성을 기준으로 한 리팩터링 검토다. SprintPivot 코드를 계속 덧붙이는 요청으로 처리하지 않는다.
- [캐릭터 아키텍처 검토](../Engineering/CHARACTER_ARCHITECTURE_REVIEW_20260908.md)에 실제 문제/보존 대상/권장 책임 구조/단계별 검증을 기록했다. GAS/Linked Layers/캐릭터 정의 등은 설계 제안이며 적용 완료가 아니다.
- 현재 Source에는 KhazanLocomotionMath.h/.cpp와 MovementInputAngle/bHasValidMovementInputAngle가 없다. 앞선 가이드의 이 파일/관측 멤버 선행 추가는 철회한다. Pivot 방향 계산은 실제 이동 제어 소유 함수에서 시작하고 실제 공유 필요가 있을 때만 공통 helper로 추출한다.
- C++와 현재 ABP의 전체 중첩 AnimGraph/EventGraph를 검사했다. ABP의 고유 소비 멤버는 LocomotionGait/StopGait/StopEntryFoot/bIsGrounded/bIsFalling/bShouldBeIdle/bShouldEnterStop/bShouldWalkRun/bShouldSprint의 9종이다.
- MovementDirectionAngle, bShouldPlayStart, StopEntrySpeed, bIsStopping은 현 native/ABP 범위에서 소비가 없어 제거 후보다. Acceleration/미사용 snapshot 필드 및 해당 의존 계산도 검토한다. GroundSpeed 같은 native 선택 기반값은 BP 직접 소비가 없다는 이유로 제거하지 않는다.
- MovementDirectionAngle의 Actor 정면 대비 실제 속도 방향 의미는 여전히 같다. 락온/스트레이프의 방향별 pose 소비가 실제 생길 때 설계할 값이며, SprintPivot 입력각이나 제자리 Turn 목표각으로 바꿔 쓰지 않는다.
- 진입 gait/발 고정, CMC 물리, snapshot/AnyThread 경계, InGame/Start 제외/일반 Stop과 Pivot 분리는 보존할 계약이다. 로코모션 특화 선택/발 이력은 전용 표현 영역으로, 공통 이동 적용은 Player에서 Locomotion 계층으로 이동하는 안을 검토했다.
- 검사 리포트: [Khazan_Character_Architecture_Review_20260908.json](../../Saved/ImportReports/Khazan_Character_Architecture_Review_20260908.json). Editor PID 32936에서 잘리지 않은 원본 export를 내부 검색했고 도구의 잘린 clipboard 출력은 미사용 판정 근거로 쓰지 않았다.
- 실제 삭제/rename/이동 전 C++와 BP의 외부 참조, Config의 MovementAngle → MovementDirectionAngle redirect, 직렬화/부모 클래스 영향을 확인해야 한다. 이번에는 게임 파일을 변경하지 않았고 새 빌드/PIE/성능 검증도 없다.
- 다음 절차는 책임/수명 계약 확정 → Player/AI 공통 이동 적용 → 표현 계층과 최소 공통 액션 검증이다. 사용자와 구조를 정한 뒤 한 줄씩 설명하는 공동 구현 방식으로 진행한다. 원작 우선·명시된 임시 수치 허용 정책은 유지한다.

## 2026-09-08 전체 아키텍처 v1 확립 — 현재 구현과 목표 분리

- 전체 목표 구조는 [CHARACTER_GAMEPLAY_ARCHITECTURE.md](../Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md)로 확립했다. 앞으로 구조/새 기능/리팩터링은 Router → 목표 아키텍처 → 이 현행 정본/필요한 실제 소스 순으로 확인한다. 이 문서는 계속 실제 구현의 변수/이력/검증 정본이다.
- 채택한 목표는 클래스 기반 제어 HFSM, GAS의 액션 실행, 공통 Locomotion/CMC 제약 해결, Main 관측과 Locomotion Linked Layer 표현 분리다. 목표 클래스가 이미 만들어졌다고 해석하지 않는다.
- UpdateLocomotionSelection_AnyThread, UpdateTransitionData_AnyThread, SelectStopEntryFoot_AnyThread 및 LocomotionGait/StopGait/StopEntryFoot 이력은 향후 locomotion 인스턴스로 이관한다. 이관 시 실제 Sync Group 소유와 Reset/relevancy를 검증한다. 현재 위치는 바뀌지 않았다.
- MovementDirectionAngle 등 기존 미소비 경로와 Start 잔재는 계속 참조 확인 후 정리 후보이며 이번에 삭제하지 않았다. 새 LocomotionMath/입력각 멤버부터 추가하던 절차는 재개하지 않는다.
- 후속 순서는 새 정본의 A1 공통 이동·제어 → A2 최소 Player/적 전투 → A3 애니메이션 분리 → A4 회피/장비 → A5 Turn/Pivot이다. Walk/Run/Sprint Start 제외와 InGame/root-locked Stop 결정은 유지한다.
- 이번 변경은 설계/라우팅 문서뿐이다. 게임 코드/BP/에셋/Config 변경, 새 빌드/PIE/성능 측정이 없으며 이전 검증 범위와 실행 정리 대기 항목은 그대로다.

## 2026-09-08 7계층 Tag–Ability 검토 — 현행 AnimInstance 보존

- 사용자 요청은 아키텍처 적용성 판단이며 코드 작성/적용 요청이 아니다. 전체 결과는 [Engineering 설계 정본 하단](../Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md)의 “사용자 7계층 Tag–Ability 아키텍처 적용성 검토”에 기록했다.
- 실제 `KhazanAnimInstance.cpp/.h`를 다시 읽었다. GT 수집→snapshot→AnyThread 관측/선택 경계를 재사용하며, 공격 승인·콤보·데미지·강인도·무적 원본을 Main에 추가하지 않는다.
- `UpdateLocomotionSelection_AnyThread`, `UpdateTransitionData_AnyThread`, `SelectStopEntryFoot_AnyThread`와 loop/Stop gait·발 이력은 기존 locomotion 표현 분리 대상이다. 이번에 이관하지 않았다. `bShouldPlayStart`는 여전히 false로 설정되는 잔재이며 Start를 재도입하지 않는다.
- 공유 gameplay 상태를 태그로 통일하는 것과 표현 내부의 bool/Foot/Gait/엔진 MovementMode를 전면 삭제하는 것은 별개다. 태그 count를 매 worker update에서 ASC에 직접 조회·수정하는 경로를 만들지 않는다.
- Main ABP는 공통 snapshot·Linked Layer·Montage Slot·필요 보정 합성을 담당하는 틀로 본다. 무기/체형별 몽타주와 Skeleton/Socket 호환성은 별도 데이터 계약이며, 보스 Ability 공유만으로 같은 ABP/시퀀스 재사용을 보장하지 않는다.
- 액션 Notify/ANS는 실행 문맥을 식별해 이벤트를 전달하고 Ability/Combat이 최종 창을 소유한다. Notify End만으로 취소 정리를 보장하지 않으며, 저프레임·section jump·평가 생략·pose 갱신 이후 무기 sweep을 후속 검증한다.
- MotionWarping은 별도 액션의 root motion/CMC 계약을 확인한 뒤 도입한다. InGame 한정, 모든 Start 제외, Walk/Run 발별 Stop·Sprint 단일 Stop, 현재 root-locked Stop과 CMC 이동은 이번에 변경하지 않았다.
- [검증 범위] Source/Config/uproject/ABP_Player의 저장 리포트 대상 39개 파일 hash가 현재 디스크 파일과 같았다. ABP의 소비 목록/Linked Anim 노드 부재는 저장 검사 재사용이며, 새 BP 컴파일·PIE·성능/애니메이션 타격 검증은 없다.
- [다음 절차] 태그/GAS와 기존 제어 HFSM의 소유권 차이를 전체 설계에서 구체화한 뒤 공통 이동·최소 Player/적 전투로 진행한다. 이번에는 새 데이터 계약을 런타임에 적용하지 않았고 Math/입력각 관측 추가 또는 Turn 구현을 재개하지 않았다.


## 2026-09-08 전체 아키텍처 v2 확정 — 현재 구현 유지, M단계로 전환

- [아키텍처 v2](../Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2)를 필수 개발 기준으로 확정했다. 별도 제어 HFSM을 필수로 만들던 v1과 앞선 유지/폐기 미확정 상태를 대체한다. 공유 gameplay 상태는 ASC 태그/효과, 액션은 Ability, 이동 제약은 Locomotion/CMC가 소유한다.
- [M0–M10](../Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md)이 기존 A단계 순서를 대체한다. 첫 [M1](../Engineering/CHARACTER_TAG_ABILITY_STEP_1.md)은 공통 Character의 ASC 접속과 ActorInfo 수명이다. Main에 새 태그/공격 bool을 추가하거나 worker에서 ASC를 직접 조회하지 않는다.
- UpdateLocomotionSelection_AnyThread/UpdateTransitionData_AnyThread/SelectStopEntryFoot_AnyThread와 gait·Stop 발 이력은 M4 Locomotion Linked Layer 이관 대상이다. 이번에 이관/삭제/rename하지 않았으며 현재 소스 의미와 마지막 ABP 관측은 그대로다.
- M2에서 Player 입력 의도와 공통 CMC 적용을 분리하고, 태그/원인별 제약을 실제 이동 정책에 연결한다. M3 공통 전투 이후 M4 표현 분리, M8 Turn/Pivot으로 진행한다.
- InGame 한정, 모든 Start 제외, Walk/Run 발별 Stop·Sprint 단일 Stop, Walk 좌/우 Turn·Run Turn 제외·별도 SprintPivot, 현재 root-locked Stop/CMC 경계는 유지한다.
- [검증 범위] 설계/단계 문서만 갱신했다. 저장 리포트 대상 게임 파일 39개는 동일 hash이며 C++/BP/에셋 직접 수정·새 빌드/PIE/성능 검증은 없다. M1 제안은 사용자 적용 전이다.



## 2026-09-09 GAS 선택 재검토 — 표현 경계 유지

- 사용자 질문은 GAS와 Gameplay Tags 기반 자체 액션 시스템 비교다. [Engineering 검토 기록](../Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#gas-versus-custom-action-review-20260909)에 판정/조건부 이관 범위를 추가했다. v2의 채택이나 현재 M단계를 변경하지 않았다.
- 실제 `KhazanAnimInstance.cpp`에서 GT 수집 → snapshot → AnyThread 관측/선택을 재확인했다. 액션 실행 기반과 무관하게 공격 승인·콤보 수명·피해·상태 태그의 원본은 Main 밖에 둔다. worker에서 Actor/ASC/자체 실행기를 직접 조회·수정하지 않는다.
- 관측용 bIsGrounded/bHasMovementInput, 표현용 LocomotionGait/StopEntryFoot를 enum/bool이라는 이유로 제거하지 않는다. 다중 원인이 쓰는 이동 허용 원본의 이관은 기존 M2 대상이며 이번에 변경하지 않았다.
- ANS로 창을 편집하는 장점은 GAS에서도 가능하다. ANS는 실행·창을 식별해 이벤트를 보내며 액션 종료가 자기 창/기여를 정리한다. 몽타주 중단/늦은 End/중첩 무적을 태그 일괄 삭제나 Notify End 하나로 해결하지 않는다.
- [검증 범위] 관련 소스와 로컬 엔진/공식 문서의 표적 정적 검토, 저장 리포트 대상 게임 파일 39개 hash 일치 확인이다. 게임 파일 편집·새 빌드·PIE·BP 미저장 상태/성능 검증은 없다. M1은 여전히 적용 전이며 M4 표현 이관/Start 제외/InGame/root-locked Stop 방침을 유지한다.



## 2026-09-09 GAS 유지와 M1 상세 공동 구현 안내

- 사용자가 자체 Tag-FSM 대안을 철회했다. 전체 기준은 기존 v2/M0–M10이며 [M1 공통 ASC 가이드](../Engineering/CHARACTER_TAG_ABILITY_STEP_1.md#m1-resume-detail-20260909)부터 상세 설명을 재개했다.
- M1은 KhazanCharacter의 컴포넌트·인터페이스·ActorInfo 수명이다. 현재 AnimInstance의 GT 수집/snapshot/AnyThread 관측을 확인했고 이번 단계의 새 ASC 접근을 worker에 넣지 않는다.
- 게임 소스/BP/에셋은 변경하지 않았다. 현재 Locomotion/Stop/발 선택, M4 표현 분리 대상과 InGame/모든 Start 제외/root-locked Stop 정책을 유지한다.
- 저장 표적 게임 파일 39개 hash는 동일하다. 신규 빌드/PIE/애니메이션 회귀 검증을 수행한 것이 아니며 M1은 사용자 적용·검증 대기다.


### 같은 작업 후속 확인

- M1 안내 중 uproject의 GameplayAbilities 활성화가 별도로 반영됐다. 마지막 비교에서 AnimInstance 등 나머지 표적 파일 38개는 같았다. 어시스턴트는 게임 파일을 변경하지 않았으며, 이 플러그인 설정만으로 이동/애니메이션 회귀 검증이 완료된 것은 아니다.



## 2026-09-09 M1 완료 보고와 M2.1 입력/허용 분리 제안

- [현재] 사용자가 M1을 완료했다고 보고했으며 공통 Character의 ASC/Interface/lifecycle 코드 반영을 확인했다. 현재 AnimInstance/LocomotionComponent/Player의 이동 소스는 기존 계약 그대로다.
- [제안/아직 미적용] [M2.1 가이드](../Engineering/CHARACTER_TAG_ABILITY_STEP_2.md)는 Intent.MoveInputWorld/InputAmount를 제한 중에도 보존하고, bMovementAllowed를 ASC tag count의 읽기용 결과로 바꾼다. 공개 SetMovementAllowed(bool)를 제거한다.
- 최종 일반 입력 허용은 LocomotionComponent::IsMovementInputAllowed()에서 ASC 상태와 엔진 입력 무시를 합친다. GatherGameThreadData의 NewData.bMovementAllowed 공급자를 이 함수로 바꾸고, worker의 Snapshot.bMovementAllowed && InputAmount 조건은 유지하는 제안이다.
- Player는 입력을 먼저 기록한 다음 출력 gate를 확인한다. 제한을 실제 Released로 처리하여 토글 Sprint 요청까지 지우던 경로를 분리한다. callback이 과거 입력을 임의 재전송하지는 않는다.
- 차단 시 미소비 Pawn 입력만 비우며 현재 CMC 제동/중력과 이미 계산된 변위는 유지한다. 기존 Stop/marker/발/Start 제외/InGame/root lock/ABP 그래프는 변경하지 않는다.
- M2.2의 CMC 정책/데이터 및 M2.3의 AI 의도·구동/snapshot은 남는다. M2.1의 공통 태그 조회만으로 Monster MoveTo와 animation 입력이 완전히 연결됐다고 판정하지 않는다.
- [검증 범위] 실제 소스/엔진 API 정적 대조와 문서 작성만 수행했다. M2 Source/BP/에셋 편집, 새 빌드/PIE/애니메이션 회귀 검증은 없다.


- 같은 M2.1 제안 보충: Player::UnPossessed에서 원시 입력과 Sprint 요청을 먼저 지운 뒤 공통 부모의 해제/ASC Refresh를 호출한다. 이전 Pawn의 눌림이 snapshot에 잔류하지 않게 하는 계약이며 별도 차단 효과는 보존한다. 실제 적용/검증 전이다.


## 2026-09-09 M2.1 이동 입력 허용 bridge 현재 구현·부분 검증

- [현재 구현] `UKhazanLocomotionComponent`는 BeginPlay의 Game Thread에서 Owner의 ASC를 찾고 `Block.Movement.Input`의 `NewOrRemoved` 이벤트에 직접 구독한다. `Intent.bMovementAllowed`는 최초 Refresh와 태그의 0↔비0 경계 callback이 작성한다. 컴포넌트 tick은 없다.
- [현재 구현] `SetMoveInputWorld()`는 차단 중에도 정규화된 원시 world input과 0~1 InputAmount를 기록한다. Player는 이를 먼저 기록한 뒤 `IsMovementInputAllowed()`를 통과할 때만 `AddMovementInput`을 호출하며, gait CMC 출력도 같은 gate 뒤에 있다. 실제 Released와 UnPossessed는 원시 입력을 정리한다.
- [현재 구현] Main AnimInstance는 Game Thread 수집에서 공통 허용 함수의 결과를 snapshot으로 복사한다. AnyThread 선택은 snapshot만 소비하며 ASC/Actor를 직접 읽거나 쓰지 않는다.
- [실제 검증] 실제 Infinite Test GE 두 개의 적용·개별 제거에서 tag count `0→1→2→1→0`과 캐시된 허용 `true→false→false→false→true`가 일치했다. 차단 효과를 남긴 Stop PIE와 다음 PIE의 깨끗한 시작·종료도 통과해 delegate/Intent cleanup과 이전 `bHasBegunPlay` assert 수정이 확인됐다.
- [아직 미확인] 자동 Enhanced Input 주입이 프로젝트 `IA_Move` binding까지 전달되지 않아, 키보드/패드 입력이 차단 중 CMC로 내려가지 않는 실제 장면은 아직 관찰하지 못했다. 현재 Test BP도 BeginPlay 한 호출 안에서 효과를 모두 제거하므로 네 개의 수동 이벤트로 분리한 체감 시험이 남는다.
- [빌드 범위] 수정 소스의 Live Coding 성공과 PIE 실행은 확인했다. Editor 완전 종료 상태의 전체 Development Editor 빌드는 아직 없다. M2.2 데이터/CMC 정책, M2.3 AI 이동과 M4 Linked Layer 이관도 이번 검증 범위가 아니다.
- 기존 InGame 한정, 모든 Start 제외, Walk/Run 발별 Stop·Sprint 단일 Stop, root-locked Stop/CMC 이동과 Stop 발 이력 계약은 바뀌지 않았다. 어시스턴트는 Source/BP/animation asset을 수정하지 않고 현행 정본에 실제 상태만 추가했다.

### 같은 세션 후속 — 프로젝트 `IA_Move` 실제 경로 검증

- `IA_Move`에 `(0,1)` action 값을 12프레임 주입한 결과, Block count 1에서도 `HandleInputMove()`가 원시 InputAmount 1.0을 기록했다. 캐시 허용은 false였고 캐릭터 변위·속도·가속도는 모두 0이어서 gate 뒤 CMC 출력이 차단됐다.
- 같은 Test GE를 handle로 제거하면 count 0 / 허용 true가 됐고, 같은 action 주입은 387.214 uu 이동, 종료 시 `(0,470,0)` uu/s 속도와 `(0,1800,0)` uu/s² 가속도를 만들었다. 수치는 현재 PIE 관측값이며 원작 metadata나 변경할 튜닝값으로 확정한 것이 아니다.
- action 주입을 끝낸 뒤 InputAmount 0과 MoveInputWorld 영벡터를 확인해 Completed/Released 경로도 통과했다. 마지막 PIE 종료와 임시 callback cleanup도 정상이다.
- 따라서 M2.1의 원시 입력 보존 → ASC 허용 gate → CMC 출력/Anim snapshot 계약은 기능 런타임에서 확인됐다. Editor 종료 상태의 전체 Development Editor 빌드만 남으며, M2.2/AI/Linked Layer와 기존 Stop·Turn 범위는 여전히 별도 단계다.


## 2026-09-09 M2.1 완료와 M2.2·M2.3 표현 경계

- Editor 종료 상태 전체 Development Editor 빌드가 성공해 M2.1을 완료 처리한다. 앞 절의 “전체 빌드만 남음”은 당시 상태다.
- [제안/아직 미적용] M2.2는 `Intent`에서 MaxAllowedGait와 tag 허용 projection을 분리하고, `ResolvedMovementPolicy`에서 MaxAllowed/ResolvedGait/RotationMode/MaxWalkSpeed를 보관한다. Main AnimInstance GT 수집은 raw Target/Input과 resolved policy를 각각 snapshot에 복사한다.
- [제안/아직 미적용] M2.3의 Khazan CMC는 AI RequestPathMove/RequestDirectMove를 동일 raw intent로 기록한다. Path pause 중 InputAmount는 마지막 방향과 함께 보존되지만 snapshot의 허용=false 때문에 worker의 bHasMovementInput은 false다. 도착/실패/abort에서는 AIController가 raw intent를 0으로 정리한다.
- Main AnimInstance는 AIController/PathFollowing/ASC를 AnyThread에서 직접 읽지 않는다. M2 시험용 enemy ABP도 C++ snapshot을 보기 위한 Ref Pose 진단 자산일 뿐 생산 locomotion layer가 아니다.
- 기존 InGame 한정, 모든 Start 제외, Walk/Run 발별 Stop·Sprint 단일 Stop, root-locked Stop/CMC 이동, Stop 발 이력과 아직 미구현 Turn 범위는 바뀌지 않는다. Block으로 입력 허용이 사라질 때 기존 Stop 진입 조건이 실제 감속을 계속 관측해야 한다.
- 상세 적용/검증은 [M2.2·M2.3 가이드](../Engineering/CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)를 따른다. 이번에는 문서와 읽기 전용 CDO report만 갱신했고 게임 C++/BP/animation asset을 수정하지 않았다.


## 2026-09-09 M2.2 자료형 이관 사용자 작업 중

- [현재 부분 구현] 사용자가 `KhazanLocomotionType.h`에서 gait ordinal, `EKhazanLocomotionIntentSource`, `RequestedRotationMode`, movement constraint, resolved policy, locomotion config를 추가했다. LocomotionComponent/Player/AnimInstance 소비자는 아직 M2.1 계약이므로 현재 소스 전체는 의도적인 중간 상태다.
- [현재 정정 필요] `FKhazanLocomotionIntent::bMovementAllowed`는 아직 남아 있으나 M2.2 최종 계약에서는 삭제한다. tag 허용 projection은 resolved policy로 이동한다. `MinAnalogWalkSpeed`의 현재 입력 `170.f`는 WalkSpeed와 혼동한 값이며 현재 Player CDO 이관값 `15.f`로 정정한다.
- [영향 없음] InGame 한정, 모든 Start 제외, Walk/Run 발별 Stop·Sprint 단일 Stop, root-locked Stop/CMC 이동, Stop 발 이력과 미구현 Turn 범위는 이번 자료형 분리로 변경하지 않는다.
- [제안/미적용] 후속 전체 절차는 [M2.2 순서형 실습판](../Engineering/CHARACTER_TAG_ABILITY_M2_2_WALKTHROUGH.md)을 따른다. Config/Intent/Constraint/Policy의 작성자와 수명을 분리하고, LocomotionComponent만 공통 CMC 정책을 쓰며, AnimInstance는 Game Thread snapshot만 갱신한다.
- [검증 범위] 어시스턴트는 현재 소스/diff를 정적으로 확인하고 문서만 추가했다. 진행 중 compile 오류를 실행하지 않았으며, 사용자 C++·BP·asset을 수정하거나 M2.2 빌드/PIE 완료로 판정하지 않았다.


## 2026-09-09 M2.2 20.5까지 사용자 반영 확인

- [현재 부분 구현] locomotion config/intent/constraint/resolved policy와 config helper, Character Definition, Character의 Definition 참조·초기화 호출까지 소스에 들어왔다. 다음 작성 지점은 LocomotionComponent의 intent/constraint handle이다.
- [정적 통과] `MinAnalogWalkSpeed=15.f`, raw intent의 `bMovementAllowed` 제거, config 검증과 gait→속도 매핑, DataAsset const getter/property는 M2.2 계약과 일치한다.
- [수정 필요] Character의 Locomotion getter에 M2 Probe용 `BlueprintPure` 노출이 빠졌다. `PostInitializeComponents()`의 Definition/Locomotion 초기화가 GameWorld guard 바깥에 있어 preview/editor world에서도 실행될 수 있으므로 ASC와 config 초기화 모두 같은 조기 return 뒤에 둔다.
- [예상 미완성] `InitializeMovementConfig`의 Component 선언/정의와 옛 Intent 소비자 이관은 이후 20.7~20.18 범위다. 현재 컴파일 오류 가능성을 기능 회귀로 판정하지 않는다.
- 기존 Stop/발 이력/Start 제외/Turn 미구현 계약과 animation asset은 변경하지 않았다. 실제 소스 수정과 빌드·PIE는 사용자가 후속 단계를 적용한 뒤 검증한다.


## 2026-09-09 M2.2 20.6 handle 선언 반영

- [현재 부분 구현] LocomotionComponent 헤더에 현재 Controller의 raw-intent 쓰기 권한을 나타내는 native intent handle과, 원인별 이동 제약을 Blueprint에서도 보관할 수 있는 transient constraint handle이 추가됐다. 둘은 issuing LocomotionComponent의 weak pointer와 GUID를 가진다.
- [정적 통과] Component forward declaration, private 필드와 friend 발급 권한, constraint handle의 `USTRUCT(BlueprintType)`/`GENERATED_BODY`, native permission multicast delegate 선언을 확인했다. Character의 BlueprintPure getter와 GameWorld 초기화 경계 정정도 반영됐다.
- [아직 미구현] 현재 active intent ID/source, constraint map, 발급·검사·해제 API와 policy rebuild는 20.7 이후 범위다. 선언된 handle만으로 이동 소유권이나 제한이 자동 작동하지 않는다.
- [검증 범위] 읽기 전용 정적 확인만 수행했다. 전체 빌드·PIE와 C++·BP·asset 수정은 수행하지 않았다.
