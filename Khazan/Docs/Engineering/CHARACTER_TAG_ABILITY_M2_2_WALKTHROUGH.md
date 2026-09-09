# M2.2 공동 구현 실습판 — 현재 `KhazanLocomotionType.h`부터 완료까지

> 작성일: 2026-09-09
>
> 상태: **사용자 구현 진행 중 / 설계와 코드 예시는 제안 / 아직 M2.2 완료 아님**
>
> 선행 완료: M1, M2.1
>
> 이번 문서의 끝: Player·LocomotionComponent·CMC·AnimInstance가 하나의 이동 정책을 사용하고 M2.2 시험표를 통과하는 지점
>
> 다음 단계: M2.3 AIController·PathFollowing·공통 CMC gate

이 문서는 기존 `CHARACTER_TAG_ABILITY_STEP_2.md` 20절을 읽다가 흐름을 놓치지 않도록 만든 **순서형 실습판**이다. 설계 계약은 바꾸지 않는다. 두 문서가 표현상 충돌하면 현재 소스 대조를 반영한 이 문서의 순서와 정정 사항을 우선한다.

게임 C++·Blueprint·에셋을 어시스턴트가 직접 수정했다는 기록이 아니다. 사용자가 아래 순서대로 적용하고, 실제 빌드와 PIE 결과가 확인돼야 M2.2가 완료된다.

---

## 0. 지금 위치와 먼저 고칠 두 항목

현재 `KhazanLocomotionType.h`에는 다음 작업이 반영돼 있다.

| 항목 | 현재 상태 | 판정 |
| --- | --- | --- |
| `EKhazanGait`의 `Walk=0`, `Run=1`, `Sprint=2` | 반영됨 | 유지 |
| `EKhazanLocomotionIntentSource` | 반영됨 | 유지 |
| `RequestedRotationMode` | 반영됨 | 유지 |
| `FKhazanMovementConstraint` | 반영됨 | 유지 |
| `FKhazanResolvedMovementPolicy` | 반영됨 | 유지 |
| `FKhazanLocomotionConfig` | 반영됨 | 아래 수치 한 곳 정정 |
| `Intent.bMovementAllowed` | 아직 남아 있음 | 삭제 |
| `MinAnalogWalkSpeed = 170.f` | Walk 속도와 혼동됨 | `15.f`로 정정 |

`MinAnalogWalkSpeed`와 `WalkSpeed`는 이름이 비슷하지만 역할이 다르다.

- `WalkSpeed=170 cm/s`: Walk gait가 선택됐을 때 CMC에 적용할 **최대 속도**다.
- `MinAnalogWalkSpeed=15 cm/s`: 0이 아닌 작은 아날로그 입력을 CMC가 처리할 때 사용할 수 있는 **최소 아날로그 보행 속도**다.
- 현재 Player는 `AddMovementInput(..., 1.f)`로 최종 출력하기 때문에 아날로그 세기가 실제 이동 스케일로 직접 전달되지는 않는다. 그래도 M2.2는 기존 Player CDO의 `15`를 보존한다. 이후 입력 스케일 또는 AI 이동이 달라졌을 때 두 값의 차이가 실제 동작에 영향을 줄 수 있기 때문이다.
- `170 / 470 / 600 / 15 / 1800 / 1800 / Yaw 540`은 현재 프로젝트에서 읽은 **이관값**이다. 원작 메타데이터 직접 확인값이 아니다.

지금 빌드가 깨질 수 있는 이유도 명확하다.

1. `Intent.MaxAllowedGait`를 헤더에서 없앴지만 기존 `LocomotionComponent.cpp`와 `KhazanAnimInstance.cpp`가 아직 읽는다.
2. `Intent.RotationMode`를 `RequestedRotationMode`로 바꿨지만 같은 두 파일이 옛 이름을 읽는다.
3. `Intent.bMovementAllowed`를 삭제하면 M2.1 코드가 잠시 그 필드를 계속 읽고 쓴다.
4. `FKhazanLocomotionConfig::IsValid()`와 `GetSpeedForGait()`를 선언한 뒤 cpp 정의를 넣기 전에는 사용 시 linker 오류가 날 수 있다.

이 오류를 없애려고 삭제한 필드를 다시 추가하지 않는다. 아래 의존 순서를 끝까지 이관하면 사라지는 **예상된 중간 오류**다.

---

## 1. 먼저 이해할 네 종류의 값

M2.2의 핵심은 구조체 수를 늘리는 데 있지 않다. **서로 다른 작성자와 수명을 한 그릇에 넣지 않는 것**이 핵심이다.

```text
Character Definition / Config
    캐릭터가 원래 가진 이동 능력과 기본값
                    │
                    ▼
Raw Intent ─────── Resolve ────── Resolved Policy ────── CMC
Controller가 원함       ▲          실제 적용할 결과          물리 실행
                        │
              Active Constraints
              Ability/Effect 등이 건 제한

ASC의 Block.Movement.Input count
                    └──────────────► Policy의 태그 허용 projection
```

### 1.1 `FKhazanLocomotionConfig`: 정적 정의

질문은 “이 캐릭터가 원래 어느 정도로 움직일 수 있는가?”다.

- 작성자: Character Definition DataAsset을 편집하는 제작자
- 최초 소비자: `AKhazanCharacter::PostInitializeComponents()`
- 런타임 소유자: `UKhazanLocomotionComponent`가 값 복사본을 보관
- 갱신 시점: 캐릭터 gameplay 초기화 시 한 번
- Reset: `EndPlay()`
- 포함하는 값: gait별 속도, 가속도, 제동, 회전률, 기본 gait·상한·회전 방식
- 포함하지 않는 값: 현재 입력 방향, 현재 스턴, 현재 공격이 건 제약

DataAsset 자체를 매 프레임 읽지 않고 component에 한 번 복사하는 이유는 런타임 정책 계산이 편집 가능한 전역 UObject에 계속 의존하지 않게 하기 위해서다.

### 1.2 `FKhazanLocomotionIntent`: 원시 의도

질문은 “현재 Controller가 무엇을 요청하는가?”다.

- 작성자: 현재 유효한 intent handle을 가진 PlayerController 또는 AIController 경로
- 소비자: 정책 계산과 AnimInstance의 관측
- 갱신 시점: 입력 이벤트 또는 AI path 요청
- Reset: 입력 Released, UnPossess, 새 작성자 발급, EndPlay
- 포함하는 값: 월드 이동 방향, 입력 세기, 요청 gait, 요청 회전 방식
- 포함하지 않는 값: 허용 여부, 최대 허용 gait, 최종 속도

“원한다”와 “허용됐다”는 다르다. Sprint 버튼을 누른 상태에서도 공격 제약이 Run까지만 허용할 수 있다. 따라서 `TargetGait=Sprint`는 보존하고 최종 결과만 Run으로 제한한다.

### 1.3 `FKhazanMovementConstraint`: 원인 하나의 제한 요청

질문은 “이 Ability/Effect/연출 한 개가 어떤 제한을 기여하는가?”다.

- 작성자: 이후 Ability, Effect bridge, 상호작용 또는 시험 Probe
- 런타임 소유자: LocomotionComponent의 `ActiveConstraints` map에 복사
- 갱신 시점: acquire/release
- Reset: 그 원인이 받은 handle을 release할 때
- 포함하는 값: 최대 허용 gait, 선택적 회전 override, priority, 진단 이름
- 포함하지 않는 값: 다른 원인의 제한, 최종 정책

제약 A가 Run 상한이고 제약 B가 Walk 상한이라면 결과는 Walk다. A만 끝났다고 B까지 제거하면 안 된다. 그래서 setter 한 번이 아니라 **원인별 handle**이 필요하다.

### 1.4 `FKhazanResolvedMovementPolicy`: 파생된 최종 결과

질문은 “현재 모든 입력과 제한을 합쳤을 때 CMC에 무엇을 적용해야 하는가?”다.

- 유일한 작성자: LocomotionComponent의 rebuild 함수
- 소비자: CMC 적용 함수, AnimInstance Game Thread snapshot, 시험 Probe
- 갱신 시점: config 준비, intent source 교체, 요청 gait·회전 변경, constraint acquire/release, 이동 차단 태그 경계 변화
- Reset: config 실패 또는 EndPlay
- 포함하는 값: 태그 허용 projection, 종합 상한, resolved gait, 최종 회전 방식, 최종 MaxWalkSpeed

이 구조체는 새로운 gameplay 원본이 아니다. 원본을 다시 계산한 **읽기 전용 cache**다. 외부 setter를 만들지 않는다.

### 1.5 네 구조체를 하나로 합치면 생기는 문제

한 구조체에 모두 넣으면 다음 작성자가 같은 값을 덮어쓴다.

```text
Player: TargetGait = Sprint
Attack: MaxAllowedGait = Run
Hit:    MaxAllowedGait = Walk
Attack 종료: MaxAllowedGait = Sprint로 복구
결과: 아직 Hit 중인데 Sprint가 풀림
```

분리 후에는 다음처럼 계산한다.

```text
Target                 = Sprint
Definition 기본 상한  = Sprint
Attack 제약            = Run
Hit 제약               = Walk
Resolved               = min(Sprint, Sprint, Run, Walk) = Walk

Attack 제약만 해제
Resolved               = min(Sprint, Sprint, Walk) = Walk

Hit 제약도 해제
Resolved               = min(Sprint, Sprint) = Sprint
```

“이전 값을 저장했다가 복원”하지 않고 **지금 남아 있는 원인 전체를 다시 계산**하기 때문에 종료 순서가 바뀌어도 안전하다.

---

## 2. 용어 사전

| 용어 | 이 단계에서의 정확한 뜻 |
| --- | --- |
| `struct` | 관련 값을 하나의 값 형식으로 묶은 C++ 자료형이다. 그 자체가 Actor나 Component처럼 월드에 존재하지 않는다. |
| `USTRUCT` | Unreal Header Tool이 구조체를 인식해 Blueprint·직렬화·Details에 연결할 수 있게 한 구조체다. |
| `UPROPERTY` | Unreal의 reflection, 직렬화, GC, Details 노출에 참여하는 필드 표시다. 접근 제어와는 별개다. |
| CDO | Class Default Object. C++/Blueprint 클래스의 기본값 원본이다. 인스턴스는 여기서 초기값을 받는다. |
| DataAsset | 코드를 다시 컴파일하지 않고 제작자가 설정을 저장하는 UObject 에셋이다. |
| CMC | `UCharacterMovementComponent`. 가속·제동·최대 속도·회전과 실제 Character 이동을 실행하는 엔진 컴포넌트다. |
| Intent | 실행 명령이 아니라 “원하는 방향/세기/보행 단계”다. 제한을 통과하지 못해도 원시 요청은 남을 수 있다. |
| Constraint | 한 원인이 기여한 제한이다. 여러 개가 동시에 존재할 수 있다. |
| Policy | 현재 원본들을 종합해 실제 적용하기로 결정한 결과다. |
| Handle | 특정 acquire 결과를 다시 찾는 식별자다. 이 단계에서는 `Owner + FGuid`로 구성한다. |
| Token | 여기서는 intent handle의 역할을 설명하는 말이다. 현재 Controller만 raw intent를 쓸 수 있게 하는 권한 증표다. |
| stale handle | 과거에는 유효했지만 새 source 발급·release·EndPlay로 더 이상 현재 ID와 일치하지 않는 handle이다. |
| projection | 다른 시스템의 원본을 읽기 편한 형태로 투영한 값이다. `bMovementAllowedByTags`는 ASC tag count의 projection이다. |
| snapshot | 특정 시점의 값을 복사해 둔 것이다. Anim worker는 UObject를 직접 읽지 않고 Game Thread snapshot을 읽는다. |
| fail closed | 데이터나 권한이 준비되지 않았을 때 우연히 이동을 허용하지 않고 명시적으로 거절하는 정책이다. |
| idempotent cleanup | 같은 종료가 두 번 호출돼도 다른 원인을 지우거나 새 상태를 망가뜨리지 않는 정리 방식이다. |
| Game Thread | Actor·Component·ASC·CMC 같은 gameplay UObject를 안전하게 읽고 쓰는 주 실행 스레드다. |
| AnyThread | 애니메이션 평가처럼 worker thread에서 실행될 수 있는 경로다. gameplay UObject에 직접 접근하지 않는다. |

`bool`, `enum`, 태그는 서로 대체재가 아니다.

- `bool`: config가 준비됐는지, 이 제약이 회전 override에 참여하는지 같은 내부 유효성에 적합하다.
- `enum`: Walk/Run/Sprint처럼 동시에 하나만 선택되는 배타적 선택에 적합하다.
- Gameplay Tag: Stun, Silence, Movement Block처럼 여러 원인이 count로 겹치고 여러 시스템이 공유하는 gameplay 사실에 적합하다.

---

## 3. 구현 순서 전체 지도

아래 순서를 바꾸지 않는다. 특히 Player부터 고치면 새 handle API가 아직 없어 이해하기 어려운 오류가 늘어난다.

| 순서 | 파일 | 이 순서인 이유 | 이 지점의 빌드 |
| ---: | --- | --- | --- |
| A | `KhazanLocomotionType.h` | 모든 후속 API가 사용할 어휘를 먼저 확정 | 깨져도 정상 |
| B | `KhazanLocomotionType.cpp` | config 검증과 gait→속도 계산 정의 | 다른 옛 참조 때문에 아직 깨질 수 있음 |
| C | `KhazanCharacterDefinition.h/.cpp` | Character가 공급할 데이터 타입 준비 | 다른 옛 참조 때문에 아직 깨질 수 있음 |
| D | `KhazanLocomotionComponent.h` | handle·policy API와 런타임 소유권 선언 | cpp가 옛 API라 아직 깨짐 |
| E | `KhazanLocomotionComponent.cpp` | 새 계약의 실제 계산과 CMC 적용 구현 | Player/Anim 옛 호출 때문에 아직 깨짐 |
| F | `KhazanCharacter.h/.cpp` | Definition을 component에 전달 | BP에 asset 지정 전 PIE는 fail closed |
| G | `KhazanPlayer.h/.cpp` | Player를 입력 어댑터로 이관 | Anim 옛 필드 참조가 남을 수 있음 |
| H | `KhazanAnimInstance.cpp` | raw intent와 policy를 구분해 snapshot | 여기까지 마친 뒤 첫 전체 빌드 |
| I | 전체 cold build | UHT와 native layout 재생성 | 반드시 성공해야 에디터 작업 진행 |
| J | DataAsset/BP | 실제 Character Definition 선택 | Compile·Save |
| K | PIE/Probe | 단일 작성자와 중첩 해제 검증 | 표 전체 통과 시 M2.2 완료 후보 |

---

## 4. A — `KhazanLocomotionType.h` 마무리

현재 파일에서 `Intent.bMovementAllowed`를 삭제하고 `MinAnalogWalkSpeed`를 `15.f`로 고친다. 최종 의미를 비교하기 쉽도록 전체 형태를 아래에 둔다. 기존 `EKhazanLocomotionMode`, `EKhazanFoot`도 그대로 유지한다.

아래 예시는 읽는 순서를 `Config → Intent → Constraint → Policy`로 정리했다. 현재 파일처럼 Intent가 먼저 선언돼 있어도 이 네 구조체가 서로의 완전한 타입을 필드로 요구하지 않으므로 컴파일 의미는 같다. 이번 작업 때문에 선언 순서까지 반드시 옮길 필요는 없다. 중요한 것은 각 필드가 올바른 구조체에 속하는지다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "KhazanLocomotionType.generated.h"

UENUM(BlueprintType)
enum class EKhazanGait : uint8
{
    Walk = 0,
    Run = 1,
    Sprint = 2
};

UENUM(BlueprintType)
enum class EKhazanRotationMode : uint8
{
    VelocityDirection,
    LookingDirection,
    LockOn
};

UENUM(BlueprintType)
enum class EKhazanLocomotionIntentSource : uint8
{
    None,
    PlayerController,
    AIController
};

enum class EKhazanLocomotionMode : uint8
{
    Grounded,
    InAir
};

UENUM(BlueprintType)
enum class EKhazanFoot : uint8
{
    None,
    Left,
    Right
};

USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanLocomotionConfig
{
    GENERATED_BODY()

    // 현재 프로젝트 이관값. 원작 metadata 직접 확인값이 아님.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0.0"))
    float WalkSpeed = 170.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0.0"))
    float RunSpeed = 470.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0.0"))
    float SprintSpeed = 600.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.0"))
    float MinAnalogWalkSpeed = 15.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.0"))
    float MaxAcceleration = 1800.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.0"))
    float BrakingDecelerationWalking = 1800.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rotation")
    FRotator RotationRate = FRotator(0.f, 540.f, 0.f);

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
    EKhazanGait DefaultTargetGait = EKhazanGait::Walk;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
    EKhazanGait DefaultMaxAllowedGait = EKhazanGait::Sprint;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Defaults")
    EKhazanRotationMode DefaultRotationMode = EKhazanRotationMode::VelocityDirection;

    bool IsValid(FString& OutError) const;
    float GetSpeedForGait(EKhazanGait Gait) const;
};

USTRUCT(BlueprintType)
struct FKhazanLocomotionIntent
{
    GENERATED_BODY()

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    FVector MoveInputWorld = FVector::ZeroVector;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    float InputAmount = 0.f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    EKhazanGait TargetGait = EKhazanGait::Walk;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    EKhazanRotationMode RequestedRotationMode = EKhazanRotationMode::VelocityDirection;
};

USTRUCT(BlueprintType)
struct FKhazanMovementConstraint
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion")
    EKhazanGait MaxAllowedGait = EKhazanGait::Sprint;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion")
    bool bOverrideRotationMode = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion",
        meta = (EditCondition = "bOverrideRotationMode"))
    EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion",
        meta = (EditCondition = "bOverrideRotationMode"))
    int32 RotationPriority = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Locomotion")
    FName DebugName = NAME_None;
};

USTRUCT(BlueprintType)
struct FKhazanResolvedMovementPolicy
{
    GENERATED_BODY()

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    bool bMovementAllowedByTags = false;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    EKhazanGait MaxAllowedGait = EKhazanGait::Sprint;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    EKhazanGait ResolvedGait = EKhazanGait::Walk;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    EKhazanRotationMode RotationMode = EKhazanRotationMode::VelocityDirection;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Locomotion")
    float MaxWalkSpeed = 0.f;
};
```

### 4.1 선언 관련 세부 설명

- `.generated.h`는 이 헤더의 **마지막 include**여야 한다. 그 아래에 enum과 struct를 선언하는 것은 정상이다.
- `BlueprintType`은 이 형식을 Blueprint 변수·핀에서 선택할 수 있게 한다.
- `EditAnywhere`는 DataAsset이나 Make Struct에서 제작자가 값을 채울 수 있게 한다.
- `BlueprintReadOnly`는 Blueprint가 읽을 수 있다는 뜻이다. C++ 필드 자체가 `const`가 되는 것은 아니다.
- `VisibleAnywhere`는 runtime 관측값을 Details에 보여 주되 일반 편집 대상으로 삼지 않는 의도다.
- `ClampMin`은 Details UI의 입력 제한이다. C++ 대입, 손상된 직렬화, NaN까지 막지 않으므로 cpp 검증이 따로 필요하다.
- `KHAZAN_API`는 out-of-line member function인 `IsValid`, `GetSpeedForGait`를 모듈 경계에 내보낸다.
- enum 숫자를 명시한 것은 저장된 ordinal 안정성을 보이기 위한 것이다. 정책 비교는 `static_cast<uint8>`에 의존하지 않고 다음 cpp의 명시적 helper를 사용한다.

### 4.2 삭제한 필드의 정확한 이관처

| 삭제/변경 전 | 문제가 된 이유 | 새 위치 |
| --- | --- | --- |
| `Intent.MaxAllowedGait` | Controller의 의도가 아니라 여러 제한의 종합 결과다. | `Constraint.MaxAllowedGait` 각각 → `Policy.MaxAllowedGait` 종합 |
| `Intent.RotationMode` | 요청인지 최종 선택인지 이름만으로 구분되지 않는다. | `Intent.RequestedRotationMode`와 `Policy.RotationMode` |
| `Intent.bMovementAllowed` | ASC가 소유한 태그 결과를 입력 작성자가 가진 것처럼 보인다. | `Policy.bMovementAllowedByTags`; 최종 허용은 함수로 계산 |

`Policy.bMovementAllowedByTags`와 `IsMovementInputAllowed()`도 서로 다르다.

```text
Policy.bMovementAllowedByTags
    = ASC가 유효하고 Block.Movement.Input count가 0인가?

IsMovementInputAllowed()
    = config가 준비됐는가
   && ASC가 유효한가
   && 위 태그 projection이 true인가
   && 현재 intent source/token이 유효한가
   && Owner가 Pawn인가
   && 엔진 IsMoveInputIgnored가 false인가
```

따라서 Policy의 bool 하나를 외부에서 true로 설정해 이동을 강제로 복구하는 API는 만들지 않는다.

---

## 5. B — `KhazanLocomotionType.cpp` 구현

현재 이 cpp는 헤더 include만 있다. 아래 두 member function과 이 cpp 내부에서만 쓰는 검증 helper를 추가한다.

```cpp
#include "Character/Locomotion/KhazanLocomotionType.h"

namespace
{
    bool IsKnownGait(const EKhazanGait Gait)
    {
        switch (Gait)
        {
        case EKhazanGait::Walk:
        case EKhazanGait::Run:
        case EKhazanGait::Sprint:
            return true;
        default:
            return false;
        }
    }

    bool IsKnownRotationMode(const EKhazanRotationMode Mode)
    {
        switch (Mode)
        {
        case EKhazanRotationMode::VelocityDirection:
        case EKhazanRotationMode::LookingDirection:
        case EKhazanRotationMode::LockOn:
            return true;
        default:
            return false;
        }
    }
}

bool FKhazanLocomotionConfig::IsValid(FString& OutError) const
{
    const bool bFiniteNumbers =
        FMath::IsFinite(WalkSpeed) &&
        FMath::IsFinite(RunSpeed) &&
        FMath::IsFinite(SprintSpeed) &&
        FMath::IsFinite(MinAnalogWalkSpeed) &&
        FMath::IsFinite(MaxAcceleration) &&
        FMath::IsFinite(BrakingDecelerationWalking) &&
        !RotationRate.ContainsNaN();

    if (!bFiniteNumbers)
    {
        OutError = TEXT("Locomotion config contains NaN or infinity.");
        return false;
    }

    if (WalkSpeed < 0.f || RunSpeed < 0.f || SprintSpeed < 0.f ||
        MinAnalogWalkSpeed < 0.f || MaxAcceleration < 0.f ||
        BrakingDecelerationWalking < 0.f ||
        RotationRate.Pitch < 0.f || RotationRate.Yaw < 0.f ||
        RotationRate.Roll < 0.f)
    {
        OutError = TEXT("Locomotion config contains a negative movement value.");
        return false;
    }

    if (WalkSpeed > RunSpeed || RunSpeed > SprintSpeed)
    {
        OutError = TEXT("Expected WalkSpeed <= RunSpeed <= SprintSpeed.");
        return false;
    }

    if (MinAnalogWalkSpeed > WalkSpeed)
    {
        OutError = TEXT("MinAnalogWalkSpeed must not exceed WalkSpeed.");
        return false;
    }

    if (!IsKnownGait(DefaultTargetGait) ||
        !IsKnownGait(DefaultMaxAllowedGait) ||
        !IsKnownRotationMode(DefaultRotationMode))
    {
        OutError = TEXT("Locomotion config contains an unknown enum value.");
        return false;
    }

    OutError.Reset();
    return true;
}

float FKhazanLocomotionConfig::GetSpeedForGait(
    const EKhazanGait Gait) const
{
    switch (Gait)
    {
    case EKhazanGait::Walk:
        return WalkSpeed;
    case EKhazanGait::Run:
        return RunSpeed;
    case EKhazanGait::Sprint:
        return SprintSpeed;
    default:
        checkNoEntry();
        return WalkSpeed;
    }
}
```

### 5.1 왜 별도 cpp인가

- 구조체는 값 묶음이지만 검증과 매핑이라는 작은 행위도 가진다.
- 이 두 함수는 CMC·Actor·ASC를 전혀 읽지 않는 **순수 계산 경계**다.
- 헤더에 긴 구현을 넣지 않으므로 이 헤더를 include하는 모든 cpp의 재컴파일 부담과 노출을 줄인다.
- unnamed namespace의 helper는 이 translation unit 밖에서 이름이 보이지 않는다. 다른 시스템이 우연히 이 검증 함수를 공용 gameplay API로 사용하지 못하게 한다.

### 5.2 검증을 하나씩 하는 이유

- `NaN`: `0/0` 같은 잘못된 계산 결과다. 모든 일반 비교가 예상과 다르게 동작할 수 있다.
- infinity: 무한대다. 물리 계산에 들어가면 속도·위치를 망가뜨릴 수 있다.
- 음수: 이 config에서는 속도·가속도·회전률의 의미가 없다.
- `Walk <= Run <= Sprint`: gait 제한의 순서와 속도 의미가 일치하게 한다.
- `MinAnalogWalkSpeed <= WalkSpeed`: 최소값이 Walk의 최대값을 넘는 모순을 막는다.
- enum 검증: Blueprint의 정상 dropdown을 의심하는 것이 아니라 오래된 직렬화, 강제 cast, 이후 enum 변경을 방어한다.
- `OutError`: 호출자가 실패 이유를 로그로 남길 수 있게 한다. bool만 반환하면 어떤 필드가 문제인지 알 수 없다.
- `checkNoEntry()`: 정상 enum이면 절대 들어오면 안 되는 경로를 Development 빌드에서 드러낸다. 뒤의 Walk 반환은 실행을 계속해야 하는 구성의 fallback이다.

---

## 6. C — Character Definition 파일 생성

`Source/Khazan/Data`에 `KhazanCharacterDefinition.h`와 `.cpp`를 만든다. 기존 `KhazanInputData`, `KhazanAssetData`와 같은 Data 폴더를 사용하되 책임은 섞지 않는다.

### 6.1 `KhazanCharacterDefinition.h`

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Engine/DataAsset.h"
#include "KhazanCharacterDefinition.generated.h"

UCLASS(BlueprintType)
class KHAZAN_API UKhazanCharacterDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()

public:
    const FKhazanLocomotionConfig& GetLocomotionConfig() const;

private:
    UPROPERTY(EditAnywhere, BlueprintReadOnly,
        Category = "Character|Locomotion",
        meta = (AllowPrivateAccess = "true"))
    FKhazanLocomotionConfig LocomotionConfig;
};
```

### 6.2 `KhazanCharacterDefinition.cpp`

```cpp
#include "Data/KhazanCharacterDefinition.h"

const FKhazanLocomotionConfig&
UKhazanCharacterDefinition::GetLocomotionConfig() const
{
    return LocomotionConfig;
}
```

### 6.3 각 선택의 이유

- `UPrimaryDataAsset`: 일반 DataAsset 기능에 Primary Asset ID를 제공한다. 현재 단계는 Character가 직접 참조하므로 비동기 로딩이 자동으로 생기지는 않는다. 향후 AssetManager 소비가 실제 생길 때 확장할 수 있다.
- `EditAnywhere`: DataAsset 에디터에서 구조체 값을 실제로 편집해야 한다.
- `private`: 런타임 C++ 코드가 필드를 직접 덮는 습관을 막는다.
- `BlueprintReadOnly`: Blueprint 진단은 허용하지만 쓰기 API는 만들지 않는다.
- `AllowPrivateAccess`: private UPROPERTY를 reflection에 노출하되 C++ 캡슐화는 유지한다.
- `const FKhazanLocomotionConfig&`: 복사하지 않는 읽기 전용 참조다. Character가 이 값을 component로 넘기고, component가 자기 런타임 사본으로 한 번 복사한다.

Definition에는 아직 Ability 목록, Attribute, AI 패턴, Anim Layer soft reference를 넣지 않는다. 실제 소비자가 없는 필드를 미리 모으면 Character Definition이 거대한 만능 설정 파일이 된다.

---

## 7. D — `KhazanLocomotionComponent.h`를 새 계약으로 교체

이 단계에서 가장 중요한 변화는 **모든 쓰기 함수가 현재 작성자 handle을 요구한다는 것**과 **제약을 acquire/release한다는 것**이다.

### 7.1 삭제할 공개 API

```cpp
void SetMoveInputWorld(const FVector& Input);
void ClearMoveInput();
void SetTargetGait(EKhazanGait Gait);
void SetMaxAllowedGait(EKhazanGait Gait);
void SetRotationMode(EKhazanRotationMode Mode);
```

특히 `SetMaxAllowedGait`는 새 형태로 overload하지 않고 완전히 삭제한다. 이 함수는 마지막 호출자가 앞선 원인의 제한을 덮어쓰는 구조이기 때문이다.

### 7.2 추가할 handle의 차이

```text
Intent handle
    현재 Controller 한 명의 쓰기 권한
    동시에 하나만 active
    C++ Player/AI 경계에서만 사용

Constraint handle
    원인 하나가 등록한 제한의 해제 권한
    동시에 여러 개 active
    M2 Probe와 향후 Blueprint Ability에서도 보관
```

둘 다 handle이지만 cardinality와 수명이 다르므로 같은 타입으로 합치지 않는다.

### 7.3 최종 헤더 형태

아래는 M2.2 기준 전체 계약이다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "Components/ActorComponent.h"
#include "Delegates/Delegate.h"
#include "GameplayTagContainer.h"
#include "KhazanLocomotionComponent.generated.h"

class UAbilitySystemComponent;
class UKhazanLocomotionComponent;

struct KHAZAN_API FKhazanLocomotionIntentHandle
{
public:
    bool IsValid() const
    {
        return Owner.IsValid() && Id.IsValid();
    }

    void Reset()
    {
        Owner.Reset();
        Id.Invalidate();
    }

private:
    friend class UKhazanLocomotionComponent;

    TWeakObjectPtr<UKhazanLocomotionComponent> Owner;
    FGuid Id;
};

USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanMovementConstraintHandle
{
    GENERATED_BODY()

public:
    bool IsValid() const
    {
        return Owner.IsValid() && Id.IsValid();
    }

    void Reset()
    {
        Owner.Reset();
        Id.Invalidate();
    }

private:
    friend class UKhazanLocomotionComponent;

    UPROPERTY(Transient)
    TWeakObjectPtr<UKhazanLocomotionComponent> Owner;

    UPROPERTY(Transient)
    FGuid Id;
};

DECLARE_MULTICAST_DELEGATE_OneParam(
    FKhazanMovementInputPermissionChanged,
    bool /* bMovementAllowed */);

UCLASS(ClassGroup = (Khazan), meta = (BlueprintSpawnableComponent))
class KHAZAN_API UKhazanLocomotionComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UKhazanLocomotionComponent();

    bool InitializeMovementConfig(
        const FKhazanLocomotionConfig& InConfig);

    FKhazanLocomotionIntentHandle BeginMoveIntentSource(
        UObject* Source,
        EKhazanLocomotionIntentSource SourceType);

    void EndMoveIntentSource(FKhazanLocomotionIntentHandle& Handle);

    bool IsMoveIntentHandleActive(
        const FKhazanLocomotionIntentHandle& Handle) const;

    bool SetMoveInputWorld(
        const FKhazanLocomotionIntentHandle& Handle,
        const FVector& Input);

    bool ClearMoveInput(
        const FKhazanLocomotionIntentHandle& Handle);

    bool SetTargetGait(
        const FKhazanLocomotionIntentHandle& Handle,
        EKhazanGait Gait);

    bool ResetTargetGaitToDefault(
        const FKhazanLocomotionIntentHandle& Handle);

    bool SetRotationMode(
        const FKhazanLocomotionIntentHandle& Handle,
        EKhazanRotationMode Mode);

    UFUNCTION(BlueprintCallable, Category = "Khazan|Locomotion")
    FKhazanMovementConstraintHandle AcquireMovementConstraint(
        UObject* Source,
        const FKhazanMovementConstraint& Constraint);

    UFUNCTION(BlueprintCallable, Category = "Khazan|Locomotion")
    bool ReleaseMovementConstraint(
        UPARAM(ref) FKhazanMovementConstraintHandle& Handle);

    bool IsMovementInputAllowed() const;

    const FKhazanLocomotionIntent& GetIntent() const
    {
        return Intent;
    }

    const FKhazanResolvedMovementPolicy& GetResolvedPolicy() const
    {
        return ResolvedPolicy;
    }

    UFUNCTION(BlueprintPure, Category = "Khazan|Locomotion")
    FKhazanLocomotionIntent GetLocomotionIntentSnapshot() const
    {
        return Intent;
    }

    UFUNCTION(BlueprintPure, Category = "Khazan|Locomotion")
    FKhazanResolvedMovementPolicy GetResolvedMovementPolicy() const
    {
        return ResolvedPolicy;
    }

    EKhazanGait GetResolvedGait() const
    {
        return ResolvedPolicy.ResolvedGait;
    }

    FKhazanMovementInputPermissionChanged&
    OnMovementInputPermissionChanged()
    {
        return MovementInputPermissionChanged;
    }

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(
        const EEndPlayReason::Type EndPlayReason) override;

private:
    struct FActiveMovementConstraint
    {
        TWeakObjectPtr<UObject> Source;
        FKhazanMovementConstraint Constraint;
        uint64 ApplyOrder = 0;
    };

    bool IsKnownIntentHandle(
        const FKhazanLocomotionIntentHandle& Handle) const;

    void ResetIntentToConfigDefaults();
    void RebuildAndApplyMovementPolicy();
    void ApplyMovementPolicyToCharacter();
    void RefreshMovementPermission();
    void HandleMovementBlockChanged(FGameplayTag Tag, int32 NewCount);

    UPROPERTY(Transient)
    TWeakObjectPtr<UAbilitySystemComponent> ObservedAbilitySystemComponent;

    FDelegateHandle MovementBlockChangedHandle;
    FKhazanMovementInputPermissionChanged MovementInputPermissionChanged;

    FKhazanLocomotionConfig MovementConfig;
    bool bHasValidMovementConfig = false;

    UPROPERTY(Transient, BlueprintReadOnly, Category = "Locomotion",
        meta = (AllowPrivateAccess = "true"))
    FKhazanLocomotionIntent Intent;

    UPROPERTY(Transient, BlueprintReadOnly, Category = "Locomotion",
        meta = (AllowPrivateAccess = "true"))
    FKhazanResolvedMovementPolicy ResolvedPolicy;

    TWeakObjectPtr<UObject> ActiveIntentSource;
    FGuid ActiveIntentId;

    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly,
        Category = "Locomotion",
        meta = (AllowPrivateAccess = "true"))
    EKhazanLocomotionIntentSource ActiveIntentSourceType =
        EKhazanLocomotionIntentSource::None;

    TMap<FGuid, FActiveMovementConstraint> ActiveConstraints;
    uint64 NextConstraintApplyOrder = 0;
};
```

### 7.4 추가된 내부 변수의 소유권 표

| 변수 | 작성자 | 소비자 | 갱신 | Reset 이유 |
| --- | --- | --- | --- | --- |
| `MovementConfig` | `InitializeMovementConfig` | rebuild/CMC 적용 | 초기화 1회 | DataAsset runtime snapshot 제거 |
| `bHasValidMovementConfig` | 초기화/EndPlay | 모든 write gate | 초기화 성공·실패 | 데이터 없는 우연한 이동 차단 |
| `Intent` | 유효한 token setter | rebuild/Anim | 입력·요청 | source 종료 시 과거 입력 제거 |
| `ResolvedPolicy` | rebuild/태그 refresh | CMC/Anim/Probe | 원본 변화 | 파생 cache 잔류 방지 |
| `ActiveIntentSource` | begin/end | 최종 허용/handle 검사 | Possess 수명 | 파괴된 Controller의 쓰기 차단 |
| `ActiveIntentId` | begin/end | handle 검사 | source 교체 | 과거 callback 차단 |
| `ActiveIntentSourceType` | begin/end | Details 진단 | source 교체 | Player/AI 표시 정리 |
| `ActiveConstraints` | acquire/release/rebuild orphan 정리 | rebuild | 원인 수명 | 다른 원인과 독립 정리 |
| `NextConstraintApplyOrder` | acquire | 회전 tie-break | acquire마다 증가 | Pawn 수명 종료 시 초기화 |
| `ObservedAbilitySystemComponent` | BeginPlay/EndPlay | 태그 조회 | component 수명 | 파괴된 ASC 접근 방지 |
| `MovementBlockChangedHandle` | BeginPlay/EndPlay | delegate 해제 | 구독 수명 | PIE 종료 callback 방지 |
| `MovementInputPermissionChanged` | tag 경계 broadcast | M2.3 AIController | 허용 경계 | teardown listener 제거 |

### 7.5 `TWeakObjectPtr`와 `TObjectPtr`의 차이

- Character가 소유하는 Component·ASC·Definition은 살아 있어야 하므로 `UPROPERTY TObjectPtr`를 사용한다.
- handle과 constraint source는 대상의 수명을 연장하면 안 된다. Controller나 Ability가 끝났는데 handle 때문에 계속 살아 있으면 cleanup이 왜곡된다. 그래서 `TWeakObjectPtr`를 사용한다.
- weak pointer가 invalid가 되는 것은 cleanup을 대신하지 않는다. 정상 종료에서는 반드시 자기 handle을 release한다. orphan 제거는 마지막 방어다.

---

## 8. E — `KhazanLocomotionComponent.cpp` 구현 순서

한 번에 붙여 넣더라도 아래 책임 묶음 순서로 읽는다.

```text
1. 지역 enum helper
2. 생성자와 BeginPlay의 ASC 관측
3. config 초기화
4. intent token 발급·검사·회수
5. raw intent setter
6. constraint acquire·release
7. 모든 원인에서 policy rebuild
8. CMC에 policy 적용
9. tag projection 갱신과 최종 허용 조회
10. EndPlay 역순 정리
```

전체 구현은 기존 Step 2 문서의 20.9~20.16 코드와 같으며, 다음 세 정정을 적용한다.

1. `ResetTargetGaitToDefault()`는 이미 기본 gait면 즉시 `true`를 반환해 불필요한 rebuild를 피한다.
2. `KhazanCharacter.cpp`가 아니라 이 component cpp의 `LogDefault` 사용에는 기존처럼 `LogChannels.h`가 필요하다.
3. `Intent.bMovementAllowed`를 읽거나 쓰는 코드는 하나도 남기지 않고 `ResolvedPolicy.bMovementAllowedByTags`를 사용한다.

### 8.1 include와 cpp 전용 helper

```cpp
#include "Character/Component/KhazanLocomotionComponent.h"

#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "Character/KhazanCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"

namespace
{
    int32 GetGaitRestrictionRank(const EKhazanGait Gait)
    {
        switch (Gait)
        {
        case EKhazanGait::Walk:
            return 0;
        case EKhazanGait::Run:
            return 1;
        case EKhazanGait::Sprint:
            return 2;
        default:
            return INDEX_NONE;
        }
    }

    bool IsKnownRotationMode(const EKhazanRotationMode Mode)
    {
        switch (Mode)
        {
        case EKhazanRotationMode::VelocityDirection:
        case EKhazanRotationMode::LookingDirection:
        case EKhazanRotationMode::LockOn:
            return true;
        default:
            return false;
        }
    }

    EKhazanGait GetMoreRestrictiveGait(
        const EKhazanGait A,
        const EKhazanGait B)
    {
        const int32 RankA = GetGaitRestrictionRank(A);
        const int32 RankB = GetGaitRestrictionRank(B);
        check(RankA != INDEX_NONE && RankB != INDEX_NONE);
        return RankA <= RankB ? A : B;
    }
}
```

명시적 rank helper를 쓰는 이유는 enum의 저장 숫자와 gameplay 비교 규칙을 결합하지 않기 위해서다. 나중에 enum 표시 순서를 바꾸거나 다른 gait를 추가할 때 이 함수와 검증을 의식적으로 수정하게 된다.

### 8.2 초기화와 ASC 구독

```cpp
UKhazanLocomotionComponent::UKhazanLocomotionComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UKhazanLocomotionComponent::BeginPlay()
{
    Super::BeginPlay();

    ResolvedPolicy.bMovementAllowedByTags = false;

    UAbilitySystemComponent* ASC =
        UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetOwner());

    if (!IsValid(ASC))
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s requires an AbilitySystemComponent for locomotion."),
            *GetNameSafe(GetOwner()));
        return;
    }

    ObservedAbilitySystemComponent = ASC;

    FOnGameplayEffectTagCountChanged& Event =
        ASC->RegisterGameplayTagEvent(
            KhazanGameplayTags::Block_Movement_Input,
            EGameplayTagEventType::NewOrRemoved);

    MovementBlockChangedHandle = Event.AddUObject(
        this,
        &UKhazanLocomotionComponent::HandleMovementBlockChanged);

    RefreshMovementPermission();
}
```

- Tick을 켜지 않는다. config·input·constraint·tag가 바뀌는 사건에만 계산한다.
- delegate를 값으로 복사하지 않고 `&` 참조로 받는다. 실제 ASC가 소유한 delegate에 listener를 등록해야 하기 때문이다.
- `NewOrRemoved`는 주로 count의 `0 ↔ 비0` 경계를 알린다. `1 ↔ 2`를 모두 callback으로 받는다고 가정하지 않는다.
- 등록 직후 `RefreshMovementPermission()`을 호출해 BeginPlay 전에 이미 붙어 있던 effect까지 읽는다.

### 8.3 config 초기화

```cpp
bool UKhazanLocomotionComponent::InitializeMovementConfig(
    const FKhazanLocomotionConfig& InConfig)
{
    check(IsInGameThread());

    if (ActiveIntentId.IsValid() || !ActiveConstraints.IsEmpty())
    {
        UE_LOG(LogDefault, Error,
            TEXT("Cannot replace locomotion config while %s has active runtime owners."),
            *GetNameSafe(GetOwner()));
        return false;
    }

    FString Error;
    if (!InConfig.IsValid(Error))
    {
        bHasValidMovementConfig = false;
        MovementConfig = FKhazanLocomotionConfig{};
        Intent = FKhazanLocomotionIntent{};
        ResolvedPolicy = FKhazanResolvedMovementPolicy{};

        UE_LOG(LogDefault, Error,
            TEXT("Invalid locomotion config for %s: %s"),
            *GetNameSafe(GetOwner()),
            *Error);
        return false;
    }

    MovementConfig = InConfig;
    bHasValidMovementConfig = true;
    ResetIntentToConfigDefaults();
    RebuildAndApplyMovementPolicy();
    return true;
}

void UKhazanLocomotionComponent::ResetIntentToConfigDefaults()
{
    Intent = FKhazanLocomotionIntent{};

    if (bHasValidMovementConfig)
    {
        Intent.TargetGait = MovementConfig.DefaultTargetGait;
        Intent.RequestedRotationMode = MovementConfig.DefaultRotationMode;
    }
}
```

active token이나 constraint가 있는 동안 config 교체를 거절하는 이유는 기존 handle이 어느 정의를 기준으로 발급됐는지 바뀌기 때문이다. 향후 장비·버프의 runtime 변화는 DataAsset 자체 교체가 아니라 modifier/constraint라는 명시적 원인으로 표현한다.

### 8.4 intent source token

```cpp
FKhazanLocomotionIntentHandle
UKhazanLocomotionComponent::BeginMoveIntentSource(
    UObject* Source,
    const EKhazanLocomotionIntentSource SourceType)
{
    check(IsInGameThread());

    FKhazanLocomotionIntentHandle Handle;
    if (!bHasValidMovementConfig ||
        !IsValid(Source) ||
        SourceType == EKhazanLocomotionIntentSource::None)
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s could not acquire a locomotion intent source."),
            *GetNameSafe(GetOwner()));
        return Handle;
    }

    ActiveIntentSource = Source;
    ActiveIntentId = FGuid::NewGuid();
    ActiveIntentSourceType = SourceType;

    ResetIntentToConfigDefaults();
    RebuildAndApplyMovementPolicy();

    Handle.Owner = this;
    Handle.Id = ActiveIntentId;
    return Handle;
}

void UKhazanLocomotionComponent::EndMoveIntentSource(
    FKhazanLocomotionIntentHandle& Handle)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle))
    {
        Handle.Reset();
        return;
    }

    ActiveIntentSource.Reset();
    ActiveIntentId.Invalidate();
    ActiveIntentSourceType = EKhazanLocomotionIntentSource::None;

    ResetIntentToConfigDefaults();
    RebuildAndApplyMovementPolicy();
    Handle.Reset();
}

bool UKhazanLocomotionComponent::IsKnownIntentHandle(
    const FKhazanLocomotionIntentHandle& Handle) const
{
    return Handle.Owner.Get() == this &&
        Handle.Id.IsValid() &&
        Handle.Id == ActiveIntentId &&
        ActiveIntentSource.IsValid();
}

bool UKhazanLocomotionComponent::IsMoveIntentHandleActive(
    const FKhazanLocomotionIntentHandle& Handle) const
{
    check(IsInGameThread());
    return IsKnownIntentHandle(Handle);
}
```

새 source를 begin하면 새 GUID가 발급된다. 예전 handle은 메모리에 남아 있어도 현재 GUID와 다르므로 setter가 false를 반환한다. 오래된 Controller callback이 새 Controller의 입력을 지우는 일을 막는 장치다.

잘못된 handle로 `End`를 호출하면 전달된 handle 복사본만 reset한다. 현재 active source를 건드리지 않는다. 이것이 idempotent cleanup의 핵심이다.

### 8.5 raw intent setter

```cpp
bool UKhazanLocomotionComponent::SetMoveInputWorld(
    const FKhazanLocomotionIntentHandle& Handle,
    const FVector& Input)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle))
    {
        return false;
    }

    const FVector Input2D(Input.X, Input.Y, 0.f);
    Intent.MoveInputWorld = Input2D.GetClampedToMaxSize(1.f);
    Intent.InputAmount = Intent.MoveInputWorld.Size2D();
    return true;
}

bool UKhazanLocomotionComponent::ClearMoveInput(
    const FKhazanLocomotionIntentHandle& Handle)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle))
    {
        return false;
    }

    Intent.MoveInputWorld = FVector::ZeroVector;
    Intent.InputAmount = 0.f;
    return true;
}

bool UKhazanLocomotionComponent::SetTargetGait(
    const FKhazanLocomotionIntentHandle& Handle,
    const EKhazanGait Gait)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle) ||
        GetGaitRestrictionRank(Gait) == INDEX_NONE)
    {
        return false;
    }

    if (Intent.TargetGait == Gait)
    {
        return true;
    }

    Intent.TargetGait = Gait;
    RebuildAndApplyMovementPolicy();
    return true;
}

bool UKhazanLocomotionComponent::ResetTargetGaitToDefault(
    const FKhazanLocomotionIntentHandle& Handle)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle))
    {
        return false;
    }

    if (Intent.TargetGait == MovementConfig.DefaultTargetGait)
    {
        return true;
    }

    Intent.TargetGait = MovementConfig.DefaultTargetGait;
    RebuildAndApplyMovementPolicy();
    return true;
}

bool UKhazanLocomotionComponent::SetRotationMode(
    const FKhazanLocomotionIntentHandle& Handle,
    const EKhazanRotationMode Mode)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle) ||
        !IsKnownRotationMode(Mode))
    {
        return false;
    }

    if (Intent.RequestedRotationMode == Mode)
    {
        return true;
    }

    Intent.RequestedRotationMode = Mode;
    RebuildAndApplyMovementPolicy();
    return true;
}
```

- 이동 방향은 Z를 0으로 만들어 지면 의도로 저장한다.
- 대각선 길이가 1을 넘더라도 clamp해 대각선 입력이 더 빠르지 않게 한다.
- `InputAmount`는 clamp한 월드 벡터의 2D 길이이므로 0~1이다.
- 방향과 세기만 바뀌면 gait/회전/CMC 설정은 바뀌지 않으므로 매 입력마다 rebuild하지 않는다.
- gait와 회전 모드는 policy 결과를 바꾸므로 값이 달라질 때 rebuild한다.
- setter의 bool은 stale token 거절을 호출자가 알 수 있게 한다. 매 프레임 실패 로그를 찍어 로그를 폭주시킬 필요는 없다.

### 8.6 constraint acquire/release

```cpp
FKhazanMovementConstraintHandle
UKhazanLocomotionComponent::AcquireMovementConstraint(
    UObject* Source,
    const FKhazanMovementConstraint& Constraint)
{
    check(IsInGameThread());

    FKhazanMovementConstraintHandle Handle;

    const bool bValidGait =
        GetGaitRestrictionRank(Constraint.MaxAllowedGait) != INDEX_NONE;
    const bool bValidRotation =
        !Constraint.bOverrideRotationMode ||
        IsKnownRotationMode(Constraint.RotationMode);

    if (!bHasValidMovementConfig ||
        !IsValid(Source) ||
        !bValidGait ||
        !bValidRotation)
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s rejected an invalid movement constraint from %s."),
            *GetNameSafe(GetOwner()),
            *GetNameSafe(Source));
        return Handle;
    }

    if (NextConstraintApplyOrder == MAX_uint64)
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s exhausted movement constraint apply order."),
            *GetNameSafe(GetOwner()));
        return Handle;
    }

    FGuid NewId;
    do
    {
        NewId = FGuid::NewGuid();
    }
    while (!NewId.IsValid() || ActiveConstraints.Contains(NewId));

    FActiveMovementConstraint ActiveConstraint;
    ActiveConstraint.Source = Source;
    ActiveConstraint.Constraint = Constraint;
    ActiveConstraint.ApplyOrder = ++NextConstraintApplyOrder;

    ActiveConstraints.Add(NewId, MoveTemp(ActiveConstraint));

    Handle.Owner = this;
    Handle.Id = NewId;

    RebuildAndApplyMovementPolicy();
    return Handle;
}

bool UKhazanLocomotionComponent::ReleaseMovementConstraint(
    FKhazanMovementConstraintHandle& Handle)
{
    check(IsInGameThread());

    if (Handle.Owner.Get() != this || !Handle.Id.IsValid())
    {
        return false;
    }

    const int32 RemovedCount = ActiveConstraints.Remove(Handle.Id);
    if (RemovedCount != 1)
    {
        Handle.Reset();
        return false;
    }

    Handle.Reset();
    RebuildAndApplyMovementPolicy();
    return true;
}
```

- `Source`는 진단과 orphan 확인용이다. 해제 키는 이름이나 Source 포인터가 아니라 GUID다.
- 같은 Ability 객체가 두 constraint를 발급할 수도 있으므로 Source만으로 제거하면 안 된다.
- `ApplyOrder`는 초나 프레임이 아니다. 같은 rotation priority일 때 나중 요청을 고르는 단조 증가 순번이다.
- `MAX_uint64` 검사는 순번 wrap으로 tie-break가 뒤집히는 형식적 예외를 막는다.
- 두 번째 release는 false이고 다른 원인을 제거하지 않는다.
- Blueprint의 `Release` handle 핀에는 변수의 by-reference 핀을 연결해야 함수 안의 `Reset()`이 BP 변수에도 반영된다.

### 8.7 policy rebuild

```cpp
void UKhazanLocomotionComponent::RebuildAndApplyMovementPolicy()
{
    check(IsInGameThread());

    for (auto It = ActiveConstraints.CreateIterator(); It; ++It)
    {
        if (!It.Value().Source.IsValid())
        {
            UE_LOG(LogDefault, Warning,
                TEXT("Removing orphaned movement constraint %s from %s."),
                *It.Value().Constraint.DebugName.ToString(),
                *GetNameSafe(GetOwner()));
            It.RemoveCurrent();
        }
    }

    FKhazanResolvedMovementPolicy NewPolicy;
    NewPolicy.bMovementAllowedByTags =
        ResolvedPolicy.bMovementAllowedByTags;

    if (!bHasValidMovementConfig)
    {
        ResolvedPolicy = NewPolicy;
        return;
    }

    EKhazanGait MaxAllowedGait =
        MovementConfig.DefaultMaxAllowedGait;

    EKhazanRotationMode RotationMode =
        Intent.RequestedRotationMode;

    bool bHasRotationOverride = false;
    int32 WinningRotationPriority = MIN_int32;
    uint64 WinningRotationOrder = 0;

    for (const TPair<FGuid, FActiveMovementConstraint>& Pair :
        ActiveConstraints)
    {
        const FActiveMovementConstraint& ActiveConstraint = Pair.Value;
        const FKhazanMovementConstraint& Constraint =
            ActiveConstraint.Constraint;

        MaxAllowedGait = GetMoreRestrictiveGait(
            MaxAllowedGait,
            Constraint.MaxAllowedGait);

        if (!Constraint.bOverrideRotationMode)
        {
            continue;
        }

        const bool bHigherPriority =
            !bHasRotationOverride ||
            Constraint.RotationPriority > WinningRotationPriority;

        const bool bSamePriorityButNewer =
            bHasRotationOverride &&
            Constraint.RotationPriority == WinningRotationPriority &&
            ActiveConstraint.ApplyOrder > WinningRotationOrder;

        if (bHigherPriority || bSamePriorityButNewer)
        {
            bHasRotationOverride = true;
            WinningRotationPriority = Constraint.RotationPriority;
            WinningRotationOrder = ActiveConstraint.ApplyOrder;
            RotationMode = Constraint.RotationMode;
        }
    }

    NewPolicy.MaxAllowedGait = MaxAllowedGait;
    NewPolicy.ResolvedGait = GetMoreRestrictiveGait(
        Intent.TargetGait,
        MaxAllowedGait);
    NewPolicy.RotationMode = RotationMode;
    NewPolicy.MaxWalkSpeed = MovementConfig.GetSpeedForGait(
        NewPolicy.ResolvedGait);

    ResolvedPolicy = NewPolicy;
    ApplyMovementPolicyToCharacter();
}
```

첫 줄의 orphan 정리는 정상 release를 대체하지 않는다. 정상 Ability는 성공·취소·실패·사망 경로에서 자기 handle을 해제해야 한다. weak Source가 먼저 사라진 버그가 영구 제한으로 남지 않게 하는 마지막 방어다.

gait와 회전의 결합 규칙이 다른 이유는 자료의 성질이 다르기 때문이다.

- gait 상한: 여러 제한을 동시에 만족해야 하므로 가장 제한적인 값이 이긴다.
- 회전 방식: 동시에 두 방식을 실행할 수 없는 배타 선택이므로 priority가 높은 하나를 고른다.
- 같은 rotation priority: 나중에 적용한 요청이 이긴다.
- 승자가 해제되면 과거 값을 저장해 복원하지 않고 남은 map을 다시 순회한다.

### 8.8 CMC의 단일 작성 함수

```cpp
void UKhazanLocomotionComponent::ApplyMovementPolicyToCharacter()
{
    check(IsInGameThread());

    AKhazanCharacter* Character = Cast<AKhazanCharacter>(GetOwner());
    UCharacterMovementComponent* Movement =
        Character ? Character->GetCharacterMovement() : nullptr;

    if (!Character || !Movement || !bHasValidMovementConfig)
    {
        return;
    }

    Movement->MinAnalogWalkSpeed = MovementConfig.MinAnalogWalkSpeed;
    Movement->MaxAcceleration = MovementConfig.MaxAcceleration;
    Movement->BrakingDecelerationWalking =
        MovementConfig.BrakingDecelerationWalking;
    Movement->RotationRate = MovementConfig.RotationRate;
    Movement->MaxWalkSpeed = ResolvedPolicy.MaxWalkSpeed;

    Character->bUseControllerRotationPitch = false;
    Character->bUseControllerRotationYaw = false;
    Character->bUseControllerRotationRoll = false;

    switch (ResolvedPolicy.RotationMode)
    {
    case EKhazanRotationMode::VelocityDirection:
        Movement->bOrientRotationToMovement = true;
        Movement->bUseControllerDesiredRotation = false;
        break;

    case EKhazanRotationMode::LookingDirection:
    case EKhazanRotationMode::LockOn:
        Movement->bOrientRotationToMovement = false;
        Movement->bUseControllerDesiredRotation = true;
        break;

    default:
        checkNoEntry();
        Movement->bOrientRotationToMovement = true;
        Movement->bUseControllerDesiredRotation = false;
        break;
    }
}
```

이 함수가 단일 작성자라는 뜻은 CMC 자체를 없앤다는 뜻이 아니다. **정책을 결정하는 곳은 LocomotionComponent 하나이고, 물리를 실행하는 곳은 CMC**다.

`MaxWalkSpeed=0`으로 Block을 표현하지 않는다. 이동 허용과 gait 속도를 합치면 Block 해제 때 어떤 속도로 돌아갈지 추측해야 한다. Block 중에도 `ResolvedGait=Run`, `MaxWalkSpeed=470`일 수 있지만 `IsMovementInputAllowed=false`라서 Player가 `AddMovementInput`을 출력하지 않는다.

`LookingDirection`과 `LockOn`은 지금 CMC flag가 같아도 의미가 다르다. 전자는 Controller 시선, 후자는 Targeting 계층의 잠금 목표를 사용한다. 이번 단계는 flag 선택까지만 구현하고 실제 LockOn target 공급은 만들지 않는다.

### 8.9 ASC tag projection과 최종 허용

```cpp
void UKhazanLocomotionComponent::HandleMovementBlockChanged(
    const FGameplayTag Tag,
    const int32 NewCount)
{
    (void)Tag;
    (void)NewCount;
    RefreshMovementPermission();
}

void UKhazanLocomotionComponent::RefreshMovementPermission()
{
    check(IsInGameThread());

    const UAbilitySystemComponent* ASC =
        ObservedAbilitySystemComponent.Get();

    const bool bWasAllowed =
        ResolvedPolicy.bMovementAllowedByTags;

    const bool bIsAllowed =
        ASC &&
        ASC->GetTagCount(
            KhazanGameplayTags::Block_Movement_Input) == 0;

    ResolvedPolicy.bMovementAllowedByTags = bIsAllowed;

    if (!bIsAllowed)
    {
        if (APawn* Pawn = Cast<APawn>(GetOwner()))
        {
            Pawn->ConsumeMovementInputVector();
        }
    }

    RebuildAndApplyMovementPolicy();

    if (bWasAllowed != bIsAllowed)
    {
        MovementInputPermissionChanged.Broadcast(
            IsMovementInputAllowed());
    }
}

bool UKhazanLocomotionComponent::IsMovementInputAllowed() const
{
    check(IsInGameThread());

    const APawn* Pawn = Cast<APawn>(GetOwner());
    return bHasValidMovementConfig &&
        ObservedAbilitySystemComponent.IsValid() &&
        ResolvedPolicy.bMovementAllowedByTags &&
        ActiveIntentSource.IsValid() &&
        ActiveIntentId.IsValid() &&
        Pawn &&
        !Pawn->IsMoveInputIgnored();
}
```

callback의 `NewCount`를 cache하지 않고 현재 ASC count를 다시 읽는다. A/B 효과가 겹친 경우 “마지막으로 받은 숫자”를 별도 원본으로 만들지 않는다.

`ConsumeMovementInputVector()`는 Pawn에 아직 소비되지 않은 입력 누적을 비운다. 현재 Velocity, 중력, Root Motion, 이미 계산된 프레임 변위를 0으로 만들지는 않는다. M2.2의 Block 의미는 새 이동 입력 출력 차단이다.

### 8.10 EndPlay

```cpp
void UKhazanLocomotionComponent::EndPlay(
    const EEndPlayReason::Type EndPlayReason)
{
    if (UAbilitySystemComponent* ASC =
        ObservedAbilitySystemComponent.Get())
    {
        if (MovementBlockChangedHandle.IsValid())
        {
            ASC->UnregisterGameplayTagEvent(
                MovementBlockChangedHandle,
                KhazanGameplayTags::Block_Movement_Input,
                EGameplayTagEventType::NewOrRemoved);
        }
    }

    MovementBlockChangedHandle.Reset();
    MovementInputPermissionChanged.Clear();
    ObservedAbilitySystemComponent.Reset();

    ActiveIntentSource.Reset();
    ActiveIntentId.Invalidate();
    ActiveIntentSourceType = EKhazanLocomotionIntentSource::None;
    ActiveConstraints.Empty();
    NextConstraintApplyOrder = 0;

    bHasValidMovementConfig = false;
    MovementConfig = FKhazanLocomotionConfig{};
    Intent = FKhazanLocomotionIntent{};
    ResolvedPolicy = FKhazanResolvedMovementPolicy{};

    Super::EndPlay(EndPlayReason);
}
```

정리 순서는 등록의 역방향이다. 외부 delegate 연결을 먼저 끊고 runtime 소유권과 cache를 비운 뒤 `Super::EndPlay()`를 마지막에 한 번 호출한다. teardown 중 permission delegate를 broadcast하지 않는다.

---

## 9. F — Character가 Definition을 선택하고 공급

### 9.1 `KhazanCharacter.h`

전방 선언을 추가한다.

```cpp
class UKhazanCharacterDefinition;
```

기존 getter에는 Blueprint 진단 소비를 위해 `UFUNCTION`만 붙인다. 같은 이름의 getter를 새로 하나 더 만들지 않는다.

```cpp
UFUNCTION(BlueprintPure, Category = "Character|Locomotion")
UKhazanLocomotionComponent* GetLocomotionComponent() const
{
    return LocomotionComponent;
}

const UKhazanCharacterDefinition* GetCharacterDefinition() const
{
    return CharacterDefinition;
}
```

private에 Definition 참조를 추가한다.

```cpp
UPROPERTY(EditDefaultsOnly, BlueprintReadOnly,
    Category = "Character|Definition",
    meta = (AllowPrivateAccess = "true"))
TObjectPtr<UKhazanCharacterDefinition> CharacterDefinition = nullptr;
```

`EditDefaultsOnly`인 이유는 캐릭터 종류의 정의를 BP Class Defaults에서 고정하기 위해서다. Level에 배치한 인스턴스마다 물리 정의가 우연히 달라지는 것을 막는다.

### 9.2 `KhazanCharacter.cpp`

include에 다음 두 줄을 추가한다.

```cpp
#include "Data/KhazanCharacterDefinition.h"
#include "LogChannels.h"
```

`LogChannels.h`를 빼면 새 `UE_LOG(LogDefault, ...)`의 category 선언을 찾지 못할 수 있다.

`PostInitializeComponents()`를 다음 책임 순서로 바꾼다.

```cpp
void AKhazanCharacter::PostInitializeComponents()
{
    Super::PostInitializeComponents();

    const UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld())
    {
        return;
    }

    AbilitySystemComponent->InitAbilityActorInfo(this, this);

    if (!IsValid(CharacterDefinition))
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s has no CharacterDefinition. Locomotion remains unavailable."),
            *GetNameSafe(this));
        return;
    }

    if (!LocomotionComponent->InitializeMovementConfig(
        CharacterDefinition->GetLocomotionConfig()))
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s failed to initialize locomotion from %s."),
            *GetNameSafe(this),
            *GetNameSafe(CharacterDefinition));
    }
}
```

순서의 의미는 다음과 같다.

1. `Super`가 엔진 component 초기화를 끝낸다.
2. Preview/asset editor world에서는 gameplay 초기화를 건너뛴다.
3. M1의 ASC Owner/Avatar를 먼저 연결한다.
4. Character Definition 존재를 확인한다.
5. config를 LocomotionComponent의 runtime snapshot으로 복사하고 검증한다.
6. 이후 Possess가 발생하면 Controller가 intent token을 받을 수 있다.

Definition이 없으면 CMC의 우연한 BP 기본값으로 계속 움직이지 않는다. 명확한 로그를 남기고 token 발급이 실패하는 fail-closed 동작이다.

---

## 10. G — Player에서 물리 정책을 제거하고 입력만 남김

Player가 “얇은 입력 어댑터”가 된다는 것은 Player 코드가 사라진다는 뜻이 아니다. 장치 입력을 월드 intent로 해석하는 책임은 여전히 Player에 있다. 캐릭터 물리 수치와 제약 해결만 LocomotionComponent로 이동한다.

### 10.1 `KhazanPlayer.h`에서 삭제

```cpp
virtual void BeginPlay() override;

float WalkSpeed = 170.f;
float RunSpeed = 470.f;
float SprintSpeed = 600.f;

void RefreshLocomotionGait();
```

- `BeginPlay`의 유일한 역할이 `MaxWalkSpeed` 쓰기였으므로 함수 자체가 필요 없어졌다.
- 세 speed는 Character Definition으로 이관됐다.
- 함수 이름은 실제 속도까지 적용한다는 인상을 주므로 요청만 기록하는 이름으로 바꾼다.

### 10.2 `KhazanPlayer.h`에서 유지

```cpp
float RunInputThreshold = 0.6f;
float MoveInputDeadZone = 0.1f;
bool bToggleSprint = true;
bool bSprintRequested = false;
```

이 값들은 캐릭터 물리 능력이 아니라 **Player 장치 입력 해석 규칙**이다.

- AI에는 스틱 dead zone이 없다.
- AI에는 toggle sprint 버튼도 없다.
- `bSprintRequested`는 현재 버튼 모드의 기억이지 공유 gameplay 상태가 아니다.
- 따라서 Character Definition이나 ASC tag로 옮기지 않는다.

현재 값 `0.6 / 0.1 / true`도 현행 Player 설정 이관값이며 원작 metadata 직접 확인값은 아니다.

### 10.3 `KhazanPlayer.h`에서 추가

handle을 값 멤버로 보관하므로 component 헤더의 완전한 타입이 필요하다.

```cpp
#include "Character/Component/KhazanLocomotionComponent.h"
```

선언은 다음과 같다.

```cpp
public:
    virtual void PossessedBy(AController* NewController) override;
    virtual void UnPossessed() override;

private:
    void RefreshRequestedGait();

    FKhazanLocomotionIntentHandle PlayerIntentHandle;
    bool bSprintRequested = false;
```

### 10.4 `KhazanPlayer.cpp` 생성자에서 삭제

다음 CMC/회전 작성은 모두 삭제한다.

```cpp
bUseControllerRotationPitch = false;
bUseControllerRotationYaw = false;
bUseControllerRotationRoll = false;

UCharacterMovementComponent* PlayerMovement = GetCharacterMovement();
PlayerMovement->bOrientRotationToMovement = true;
PlayerMovement->RotationRate = FRotator(0.f, 540.f, 0.f);
PlayerMovement->MaxWalkSpeed = 600.f;
PlayerMovement->MinAnalogWalkSpeed = 15.f;
PlayerMovement->MaxAcceleration = 1800.f;
PlayerMovement->BrakingDecelerationWalking = 1800.f;
```

`BeginPlay()`의 `MaxWalkSpeed=WalkSpeed` 블록과 함수 정의도 삭제한다. Player cpp에서 CMC 타입을 더 이상 직접 쓰지 않으므로 다음 include도 제거한다.

```cpp
#include "GameFramework/CharacterMovementComponent.h"
```

Camera, SpringArm, Mesh transform은 이동 정책이 아니라 Player 조립/표현이므로 그대로 유지한다.

### 10.5 Possess와 UnPossess

```cpp
void AKhazanPlayer::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);

    PlayerIntentHandle.Reset();
    bSprintRequested = false;

    if (UKhazanLocomotionComponent* Locomotion =
        GetLocomotionComponent())
    {
        PlayerIntentHandle = Locomotion->BeginMoveIntentSource(
            NewController,
            EKhazanLocomotionIntentSource::PlayerController);
    }
}

void AKhazanPlayer::UnPossessed()
{
    HandleInputMoveReleased();
    bSprintRequested = false;

    if (UKhazanLocomotionComponent* Locomotion =
        GetLocomotionComponent())
    {
        Locomotion->EndMoveIntentSource(PlayerIntentHandle);
    }

    PlayerIntentHandle.Reset();
    Super::UnPossessed();
}
```

- Possess에서는 부모를 먼저 호출해 M1 ASC ActorInfo를 현재 Controller 관계에 맞게 갱신한다.
- 그 뒤 Player token을 발급한다.
- UnPossess에서는 자기 raw input을 먼저 지우고 token을 끝낸 뒤 부모 수명 정리를 호출한다.
- `EndMoveIntentSource`가 handle을 reset하지만 Player에서도 다시 reset한다. 두 번째 reset은 안전하며 지역 멤버가 명시적으로 비워졌음을 보여 준다.

### 10.6 이동 입력

기존 좌표 변환은 유지하되 모든 setter에 handle을 전달한다.

```cpp
void AKhazanPlayer::HandleInputMove(
    const FVector2D& MovementInput,
    const FRotator& ControlRotation)
{
    UKhazanLocomotionComponent* Locomotion =
        GetLocomotionComponent();

    if (!Locomotion ||
        !Locomotion->IsMoveIntentHandleActive(PlayerIntentHandle))
    {
        return;
    }

    const float RawInputAmount =
        static_cast<float>(MovementInput.Length());

    if (RawInputAmount <= MoveInputDeadZone)
    {
        HandleInputMoveReleased();
        return;
    }

    const FRotator YawRotation(0.f, ControlRotation.Yaw, 0.f);
    const FVector Forward =
        UKismetMathLibrary::GetForwardVector(YawRotation);
    const FVector Right =
        UKismetMathLibrary::GetRightVector(YawRotation);

    const FVector WorldInput =
        Forward * MovementInput.X + Right * MovementInput.Y;

    if (!Locomotion->SetMoveInputWorld(
        PlayerIntentHandle,
        WorldInput))
    {
        return;
    }

    RefreshRequestedGait();

    if (!Locomotion->IsMovementInputAllowed())
    {
        return;
    }

    const FVector MoveDirection =
        Locomotion->GetIntent().MoveInputWorld.GetSafeNormal2D();

    AddMovementInput(MoveDirection, 1.f);
}
```

데이터 흐름은 다음 순서다.

```text
Enhanced Input 2D 값
  → dead zone 판정
  → Control Yaw 기준 Forward/Right로 월드 벡터 생성
  → raw intent에 먼저 저장
  → 입력 세기로 TargetGait 요청
  → 최종 허용 검사
  → 허용될 때만 AddMovementInput
```

차단 여부보다 raw intent를 먼저 저장하는 이유는 “사용자가 어느 방향을 누르고 있었는가”와 “이번 프레임에 물리 입력을 출력했는가”를 구분하기 위해서다. Block 중 `InputAmount=1`이면서 `bMovementAllowed=false`인 것은 모순이 아니다.

### 10.7 Released와 gait 요청

```cpp
void AKhazanPlayer::HandleInputMoveReleased()
{
    if (bToggleSprint)
    {
        bSprintRequested = false;
    }

    if (UKhazanLocomotionComponent* Locomotion =
        GetLocomotionComponent())
    {
        Locomotion->ClearMoveInput(PlayerIntentHandle);
        Locomotion->ResetTargetGaitToDefault(PlayerIntentHandle);
    }
}

void AKhazanPlayer::HandleInputSprint()
{
    bSprintRequested = bToggleSprint
        ? !bSprintRequested
        : true;

    RefreshRequestedGait();
}

void AKhazanPlayer::HandleInputSprintReleased()
{
    if (!bToggleSprint)
    {
        bSprintRequested = false;
    }

    RefreshRequestedGait();
}

void AKhazanPlayer::HandleInputSprintCanceled()
{
    bSprintRequested = false;
    RefreshRequestedGait();
}

void AKhazanPlayer::RefreshRequestedGait()
{
    UKhazanLocomotionComponent* Locomotion =
        GetLocomotionComponent();

    if (!Locomotion ||
        !Locomotion->IsMoveIntentHandleActive(PlayerIntentHandle))
    {
        return;
    }

    const FKhazanLocomotionIntent& Intent =
        Locomotion->GetIntent();

    if (Intent.InputAmount <= 0.f)
    {
        return;
    }

    const EKhazanGait StickGait =
        Intent.InputAmount > RunInputThreshold
            ? EKhazanGait::Run
            : EKhazanGait::Walk;

    const EKhazanGait RequestedGait =
        bSprintRequested
            ? EKhazanGait::Sprint
            : StickGait;

    Locomotion->SetTargetGait(
        PlayerIntentHandle,
        RequestedGait);
}
```

기존 `switch (GetResolvedGait())`와 `Movement->MaxWalkSpeed=...`는 완전히 삭제한다. 새 함수는 요청만 쓴다. 실제 gait 제한, 속도 선택, CMC 적용은 component rebuild가 담당한다.

---

## 11. H — AnimInstance는 관측만 이관

`KhazanAnimInstance.h`의 snapshot 구조는 이미 raw와 resolved 필드를 따로 가지고 있으므로 이번 단계에서 새 gameplay 멤버를 추가하지 않는다.

`GatherGameThreadData()`에서 intent와 policy를 각각 읽는다.

```cpp
const FKhazanLocomotionIntent& Intent =
    LocomotionComponent->GetIntent();

const FKhazanResolvedMovementPolicy& Policy =
    LocomotionComponent->GetResolvedPolicy();

NewData.MoveInputWorld = Intent.MoveInputWorld;
NewData.InputAmount = Intent.InputAmount;
NewData.TargetGait = Intent.TargetGait;

NewData.MaxAllowedGait = Policy.MaxAllowedGait;
NewData.ResolvedGait = Policy.ResolvedGait;
NewData.RotationMode = Policy.RotationMode;

NewData.bMovementAllowed =
    LocomotionComponent->IsMovementInputAllowed();
```

다음 옛 참조는 남기지 않는다.

```cpp
Intent.MaxAllowedGait
Intent.RotationMode
Intent.bMovementAllowed
```

Game Thread가 Actor·CMC·LocomotionComponent를 읽고 `FKhazanAnimGameThreadData`에 값으로 복사한다. `NativeThreadSafeUpdateAnimation()`과 `_AnyThread` 함수는 기존 snapshot만 읽는다. worker에서 ASC나 component를 직접 조회하는 코드를 추가하지 않는다.

`TargetGait`와 `ResolvedGait`를 둘 다 관측하는 이유는 다음과 같다.

- Target: Controller가 Sprint를 요청했는지 진단할 수 있다.
- Resolved: 공격/피격 제약으로 Run 또는 Walk까지 제한된 실제 표현을 선택한다.
- 애니메이션의 gait 선택은 Resolved를 사용해야 제한 중 Sprint 포즈가 계속 나오지 않는다.

---

## 12. I — 첫 전체 빌드 전에 정적 검색

Editor를 닫기 전에 Rider 또는 `rg`로 다음 옛 계약이 남았는지 확인한다.

```text
Intent.MaxAllowedGait
Intent.RotationMode
Intent.bMovementAllowed
SetMaxAllowedGait
RefreshLocomotionGait
Player의 WalkSpeed / RunSpeed / SprintSpeed
Player의 MaxWalkSpeed 대입
Player의 bOrientRotationToMovement 대입
```

새 계약에서는 CMC 정책 대입 검색 결과가 다음과 같아야 한다.

| 검색 | 허용되는 최종 작성 위치 |
| --- | --- |
| `MaxWalkSpeed =` | `ApplyMovementPolicyToCharacter()` |
| `MinAnalogWalkSpeed =` | 같은 함수 |
| `MaxAcceleration =` | 같은 함수 |
| `BrakingDecelerationWalking =` | 같은 함수 |
| `RotationRate =` | 같은 함수 |
| `bOrientRotationToMovement =` | 같은 함수의 switch |
| `bUseControllerDesiredRotation =` | 같은 함수의 switch |

읽기, 로그, snapshot, 비교는 다른 파일에 있어도 된다. 여기서 찾는 것은 **대입 작성자**다.

USTRUCT와 UPROPERTY layout을 바꿨으므로 Editor를 완전히 종료하고 `KhazanEditor / Win64 / Development Editor` 전체 빌드를 실행한다. Live Coding만으로 reflection layout 변경을 판정하지 않는다.

### 12.1 오류별 해석

| 오류 형태 | 가장 먼저 볼 곳 |
| --- | --- |
| `no member named MaxAllowedGait/RotationMode/bMovementAllowed` | 옛 Intent 참조 검색 |
| `unresolved external FKhazanLocomotionConfig::IsValid/GetSpeedForGait` | `KhazanLocomotionType.cpp` 정의와 빌드 포함 여부 |
| UHT가 `generated.h` 순서를 지적 | 각 헤더에서 generated include가 마지막 include인지 확인 |
| `LogDefault` 식별 불가 | 해당 cpp의 `LogChannels.h` include 확인 |
| Blueprint callable에서 handle type 오류 | constraint handle의 `USTRUCT(BlueprintType)`, `GENERATED_BODY`, `KHAZAN_API` 확인 |
| `InitializeMovementConfig` 선언/정의 불일치 | `const FKhazanLocomotionConfig&`와 함수 이름 대조 |
| Player setter 인자 수 오류 | 모든 raw setter에 `PlayerIntentHandle` 전달 여부 |

---

## 13. J — Editor에서 실제 Definition 생성

전체 native 빌드가 성공한 뒤 새 Editor를 연다.

1. `/Game/Data/Character` 폴더를 만든다.
2. Content Browser 우클릭 → `Miscellaneous` → `Data Asset`.
3. `KhazanCharacterDefinition` 클래스를 선택한다.
4. 이름을 `PDA_Character_Khazan`으로 정한다.
5. 다음 값을 넣는다.

| 필드 | 값 | 분류 |
| --- | ---: | --- |
| Walk Speed | 170 cm/s | 현재 프로젝트 이관값 |
| Run Speed | 470 cm/s | 현재 프로젝트 이관값 |
| Sprint Speed | 600 cm/s | 현재 프로젝트 이관값 |
| Min Analog Walk Speed | 15 cm/s | 현재 Player CDO 이관값 |
| Max Acceleration | 1800 cm/s² | 현재 Player CDO 이관값 |
| Braking Deceleration Walking | 1800 cm/s² | 현재 Player CDO 이관값 |
| Rotation Rate | Pitch 0, Yaw 540, Roll 0 deg/s | 현재 Player CDO 이관값 |
| Default Target Gait | Walk | 현행 intent 기본값 |
| Default Max Allowed Gait | Sprint | 현행 기본 상한 |
| Default Rotation Mode | Velocity Direction | 현행 Player 회전 동작 |

6. `/Game/_Art/Kazan/Character/Bluprints/BP_KhazanPlayer`를 연다.
7. `Class Defaults` → `Character|Definition`의 `Character Definition`에 `PDA_Character_Khazan`을 지정한다.
8. BP를 Compile하고 Save한다.

Definition 지정 전에 PIE하면 다음이 정상이다.

```text
<Character> has no CharacterDefinition. Locomotion remains unavailable.
```

이는 crash가 아니라 fail-closed 시험이다. Definition이 없는데 과거 BP CMC 기본값으로 이동해 버리면 단일 데이터 원본 계약이 깨진다.

과거 BP에 직렬화된 `MaxWalkSpeed=300`이 asset 안에 남아 있을 수 있다. runtime `PostInitializeComponents()`에서 Locomotion policy가 최종 적용하므로 실제 값은 Definition을 따른다. BP를 삭제하거나 CharacterMovement component를 새로 만들지 말고 Editor 재시작 후 Compile·Save한다.

---

## 14. K — M2.2 검증 순서

### 14.1 기본 이동

| 조작/상태 | Intent | Policy | CMC 기대값 |
| --- | --- | --- | --- |
| 시작·무입력 | Target Walk, Amount 0 | Resolved Walk | MaxWalkSpeed 170 |
| 작은 입력 | Target Walk | Resolved Walk | 170 |
| threshold 초과 입력 | Target Run | Resolved Run | 470 |
| Sprint 요청 | Target Sprint | Resolved Sprint | 600 |

관측할 값은 `GetLocomotionIntentSnapshot`, `GetResolvedMovementPolicy`, CharacterMovement의 runtime Details다.

### 14.2 Block 태그 회귀

M2.1 시험 GE를 사용한다.

```text
입력 유지 + Block count 0
    raw InputAmount > 0
    Policy.bMovementAllowedByTags = true
    IsMovementInputAllowed = true

Block A 적용
    raw InputAmount는 유지
    tag projection false
    최종 허용 false
    새 AddMovementInput 출력 없음

Block B 추가 후 A만 제거
    count 1
    계속 false

B 제거
    count 0
    tag projection true
    다음 입력 event부터 이동 재개
```

Block 중 CMC `MaxWalkSpeed`가 0이 아니어도 정상이다. 허용 gate가 출력만 막는다.

### 14.3 gait constraint A/B

Player가 Sprint를 요청한 상태에서 시험한다.

| 순서 | 활성 제약 | Target | MaxAllowed | Resolved | 속도 |
| ---: | --- | --- | --- | --- | ---: |
| 0 | 없음 | Sprint | Sprint | Sprint | 600 |
| 1 | A=Run | Sprint | Run | Run | 470 |
| 2 | A=Run, B=Walk | Sprint | Walk | Walk | 170 |
| 3 | A만 해제, B 유지 | Sprint | Walk | Walk | 170 |
| 4 | B 해제 | Sprint | Sprint | Sprint | 600 |

A를 두 번 release하면 두 번째는 false여야 하며 B나 다른 handle에 영향이 없어야 한다.

### 14.4 rotation constraint A/B

priority `1`, `2`는 구조 시험값이며 원작 gameplay 수치가 아니다.

```text
raw request = VelocityDirection
A = LookingDirection, priority 1
B = LockOn, priority 2

A 적용       → LookingDirection
B 적용       → LockOn
B 해제       → LookingDirection
A 해제       → VelocityDirection
```

같은 priority로 A 다음 B를 적용하면 ApplyOrder가 큰 B가 이긴다. B를 해제하면 남아 있는 A가 다시 이긴다.

### 14.5 Possess 수명

1. 첫 Possess에서 Player token이 valid이고 source type이 PlayerController인지 확인한다.
2. UnPossess에서 raw input 0, source None, 이전 token setter false를 확인한다.
3. Repossess에서 새 GUID token만 유효한지 확인한다.
4. 과거 handle로 Clear/Set을 호출해도 새 intent가 바뀌지 않아야 한다.

### 14.6 Anim snapshot

- Target은 Intent와 같아야 한다.
- MaxAllowed, Resolved, Rotation은 Policy와 같아야 한다.
- Block 중 raw InputAmount가 있어도 snapshot `bMovementAllowed=false`이므로 AnyThread의 `bHasMovementInput=false`여야 한다.
- Stop 진입은 실제 감속과 이전 프레임 기록을 계속 관측해야 한다.

### 14.7 종료 안정성

- constraint가 남은 상태에서 PIE 종료
- Block GE가 남은 상태에서 PIE 종료
- UnPossess 후 종료
- PIE 재시작 반복

이때 delegate, token, constraint가 다음 PIE에 남거나 EndPlay crash가 발생하면 안 된다.

---

## 15. M2.2 완료 판정

다음이 모두 참일 때만 M2.2 완료 후보로 기록한다.

- [ ] `KhazanLocomotionType.h/.cpp`가 새 네 자료 영역을 사용한다.
- [ ] `Intent`에는 허용 bool과 MaxAllowed가 없다.
- [ ] Character Definition이 생성되고 Player BP에 지정됐다.
- [ ] LocomotionComponent만 공통 CMC 정책을 쓴다.
- [ ] Player에는 speed property와 CMC speed switch가 없다.
- [ ] 현재 Controller token 없이는 raw intent를 쓸 수 없다.
- [ ] gait/rotation constraint A/B가 개별 handle로 해제된다.
- [ ] M2.1 Block A/B가 새 policy에서도 회귀 없이 동작한다.
- [ ] AnimInstance가 Game Thread에서 Intent와 Policy를 각각 snapshot한다.
- [ ] Editor 종료 상태 Development Editor 전체 빌드가 성공한다.
- [ ] BP Compile·Save와 기본 이동/constraint/Possess/PIE 종료 시험이 통과한다.

M2.2 완료 뒤에도 M2 전체는 완료가 아니다. M2.3에서 AI PathFollowing을 같은 permission과 intent 계약에 연결하고, M2.4에서 Player/AI/Stop/제약을 통합 검증한다.
