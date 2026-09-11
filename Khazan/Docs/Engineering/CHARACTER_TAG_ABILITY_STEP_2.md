# M2 — 태그와 공통 이동 정책

## 2026-09-09 — M1 사용자 완료 보고, M2.1 공동 구현 안내

- 목표 기준은 [아키텍처 v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2), 전체 순서는 [M0–M10](CHARACTER_TAG_ABILITY_MIGRATION.md)다.
- 사용자가 M1 완료를 보고했다. 실제 Khazan.uproject/Build.cs/Character.h/.cpp에서 플러그인·모듈·ASC 생성·인터페이스·ActorInfo 최초 연결/빙의 갱신/EndPlay가 반영된 것을 확인했다. 어시스턴트가 이번에 M1의 빌드 로그/PIE/빙의 시험을 독립 검증한 것은 아니다.
- 이 문서는 **사용자가 직접 적용할 M2.1 설명**이다. Source/BP/에셋에 적용하거나 컴파일/PIE를 통과한 결과가 아니다.
- M2 전체를 한 번에 변경하지 않는다. 실제 소비가 생기는 작은 단위로 진행하고 각 단계의 설명/적용/검증을 구분한다.

## 1. M2의 소단계와 이번 범위

| 소단계 | 할 일 | 완료 기준 |
| --- | --- | --- |
| M2.1 — 태그 기반 입력 제한 | Block.Movement.Input, ASC count 구독/초기 조회/해제, 읽기용 허용 결과, 원시 입력 보존, Player/Anim 공통 조회, 효과 handle 중첩 검사 | 효과가 겹쳐도 자기 원인만 해제, 입력 이벤트 없이 허용 상태 갱신, 제한을 실제 입력 Released로 오인하지 않음 |
| M2.2 — 이동 데이터와 CMC 작성자 | 실제 BP/CDO 수치 대조 후 CharacterDefinition의 최소 이동 데이터, Player의 속도/회전 적용을 Locomotion으로 이관, gait 상한/원인별 정책, 준비·부여 수명 | 공통 CMC 정책 적용, 입력이 없어도 제한 변화 반영, Player가 CMC 속도·회전을 직접 쓰지 않음 |
| M2.3 — AI 구동 연결 | 실제 일반 적의 PathFollowing/RequestPathMove/RequestDirectMove와 공통 정책, 중단/재개·도착·실패, AI 의도 snapshot | Player와 AI의 실제 이동에 같은 제한이 적용되고 우회 없음 |
| M2.4 — M2 통합 확인 | 겹친 제한·입력 보존·gait·회전·빙의·종료·기존 locomotion 회귀 | M2 전체 완료 후 M3로 진행 |

이 분할은 M2의 완료 조건을 축소하지 않는다. **M2.1만으로 AI MoveTo 차단이나 CMC 공통화가 끝났다고 기록하지 않는다.** 다음 안내는 M2.2이며 M2.1 직후 M3로 건너뛰지 않는다.

기존 M2에서 나열한 데이터/제약/AI 작업의 책임은 그대로다. 이번에는 기존 setter의 입력 소실 문제와 M1 ASC의 첫 실제 소비를 먼저 확인한다. 숫자/기존 BP override를 이관하는 작업은 M2.2에서 별도로 대조한다.

## 2. 현재 문제와 새 데이터 계약

현재 소스에는 다음 경로가 있다.

- LocomotionComponent::SetMovementAllowed(false)는 Intent를 지운다.
- SetMoveInputWorld도 허용되지 않으면 ClearMoveInput 후 반환한다.
- Player::HandleInputMove는 제한 또는 IsMoveInputIgnored를 실제 HandleInputMoveReleased로 처리한다.
- HandleInputMoveReleased는 입력을 지우고 토글 모드의 Sprint 요청도 해제한다.
- MaxWalkSpeed의 초기/입력 시 적용은 여전히 Player에 있다.
- AnimInstance는 GT에서 Intent 값을 복사하고 worker에서 Snapshot.bMovementAllowed와 InputAmount를 함께 판정한다.

새 계약은 다음과 같다.

| 데이터 | 작성자 | 소비자 | 갱신/Reset |
| --- | --- | --- | --- |
| Block.Movement.Input 기여와 count | ASC의 각 효과/능력 | Locomotion의 이벤트/조회 | 효과별 수명. 다른 기여를 일괄 제거하지 않음 |
| Intent.MoveInputWorld/InputAmount | 실제 입력 어댑터 → SetMoveInputWorld | 요청 gait 및 허용된 이동/표현 | 제한 중에도 새 입력 저장, 실제 Released/dead zone/소유 입력 정리에서 Clear |
| Intent.bMovementAllowed | Locomotion이 ASC count로 계산 | 공통 허용 함수 | ASC 미연결/종료=false, 연결 후 count가 없으면 true |
| IsMovementInputAllowed() 결과 | Locomotion GT 조회 | Player 입력 출력/속도 적용 gate, Anim GT snapshot | ASC 유효성 + 위 태그 결과 + Pawn의 엔진 입력 무시 상태를 현재 조회 |
| ObservedAbilitySystemComponent | Component BeginPlay | 조회/구독 해제 | weak 참조, Component EndPlay에서 Reset |
| MovementBlockChangedHandle | 이벤트 등록 반환값 | 자기 구독 해제 | Component EndPlay에서 Unregister 후 Reset |
| 효과 handle A/B | 임시 검사/향후 해당 실행 | 자기 효과 제거 | 해당 효과 제거 후 보관 해제. delegate handle과 다른 종류 |

bMovementAllowed는 독립적인 gameplay 상태 원본이 아니라 **ASC 결과의 읽기용 투영**이다. 따라서 공개 SetMovementAllowed(bool)를 없앤다. FKhazanLocomotionIntent의 다른 필드와 이 결과가 함께 있는 것은 현재 snapshot 호환을 위한 M2.1 이관 상태이며, 외부 작성자를 다시 허용하지 않는다.

IsMoveInputIgnored는 기존 엔진 입력 gate로 존중한다. 새로운 상태 이상은 Controller의 Ignore 플래그를 임의로 덮어 구현하지 않고 태그/효과 경로를 사용한다.

## 3. 수정 위치

| 파일 | 수정 |
| --- | --- |
| Source/Khazan/KhazanGameplayTags.h/.cpp | 실제 소비할 native tag 한 개 |
| Source/Khazan/Character/Locomotion/KhazanLocomotionType.h | bMovementAllowed의 초기/읽기용 의미 |
| Source/Khazan/Character/Component/KhazanLocomotionComponent.h/.cpp | ASC 구독/해제, 허용 조회, 원시 입력 저장 |
| Source/Khazan/Character/KhazanPlayer.cpp | 입력 보존 후 허용된 출력, 요청 gait와 적용 gate 분리 |
| Source/Khazan/Animation/KhazanAnimInstance.cpp | GT snapshot의 허용 값 공급자만 변경 |

새 C++ 클래스는 없다. 실제 파일은 **Character/Component** 아래다. 다른 cpp의 상대 include에 Component/KhazanLocomotionComponent.h가 등장한다고 Source/Khazan/Component 경로라고 해석하지 않는다.

M1 Character 수명 코드는 유지한다. Player 헤더/이동 수치/CMC 설정/ABP 그래프는 이 소단계에서 이관하지 않는다. 아래 코드 조각은 기존 해당 함수와 교체하거나 명시한 위치에 추가하고, 같은 함수를 중복 정의하지 않는다.

## 4. native tag 등록

KhazanGameplayTags.h의 기존 namespace 안에 추가한다.

```cpp
UE_DECLARE_GAMEPLAY_TAG_EXTERN(Block_Movement_Input);
```

KhazanGameplayTags.cpp의 같은 namespace 안에 추가한다.

```cpp
UE_DEFINE_GAMEPLAY_TAG(
    Block_Movement_Input,
    "Block.Movement.Input"
);
```

- DECLARE는 다른 소스가 참조할 심볼을 선언하고 DEFINE는 실제 native tag를 정의한다.
- Block_Movement_Input은 C++ 이름, Block.Movement.Input은 에디터/규칙에서 사용하는 계층 태그 이름이다.
- 등록은 상태 부여가 아니다. 실행 중 어느 Actor에게 존재할지는 ASC의 효과/능력 기여가 결정한다.
- 이 태그는 일반 이동 입력 차단이다. Velocity 강제 영점, 중력 정지, Root Motion 차단, 피격 Ability 실행을 자동 의미하지 않는다.
- 아직 소비하지 않는 Status.Stun/State.Action.Attack 등은 이 단계에서 함께 선언하지 않는다.

KhazanLocomotionType.h에서는 기존 멤버를 다음 의미로 바꾼다. UPROPERTY는 보존한다.

```cpp
// ASC의 이동 차단 태그로 계산하는 읽기용 결과.
// 초기에는 ASC 연결이 확인되지 않았으므로 허용하지 않는다.
bool bMovementAllowed = false;
```

false는 설정 미준비 상태를 표현하는 초기값이며 원작 게임 튜닝값이 아니다.

## 5. LocomotionComponent 헤더

generated.h 위에 필요한 include를 추가한다.

```cpp
#include "GameplayTagContainer.h"
#include "Delegates/Delegate.h"
```

generated.h 아래 전방 선언에 추가한다.

```cpp
class UAbilitySystemComponent;
```

GameplayTagContainer.h는 콜백의 FGameplayTag 타입, Delegate.h는 FDelegateHandle에 사용한다. ASC는 헤더에서 weak 포인터로만 참조하므로 전방 선언하고 실제 함수 호출용 헤더는 cpp에 둔다.

기존 public의 다음 선언을 제거한다.

```cpp
void SetMovementAllowed(bool bAllowed);
```

이 함수의 cpp 정의도 아래에서 제거한다. 현재 Source 검색에서는 외부 호출이 없고 UFUNCTION이 아니다. 실제 적용 시 현재 참조를 다시 확인하여 사용자 추가 호출이 있으면 그 원인의 효과/handle 경로로 이관한다.

public에는 실제 소비할 조회 함수를 추가한다.

```cpp
bool IsMovementInputAllowed() const;
```

protected에는 엔진 수명 함수를 추가한다.

```cpp
virtual void BeginPlay() override;
virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
```

private에는 다음을 추가한다. 기존 Intent 멤버는 유지한다.

```cpp
void HandleMovementBlockChanged(const FGameplayTag Tag, int32 NewCount);
void RefreshMovementPermission();

UPROPERTY(Transient)
TWeakObjectPtr<UAbilitySystemComponent> ObservedAbilitySystemComponent;

FDelegateHandle MovementBlockChangedHandle;
```

- IsMovementInputAllowed의 const는 조회가 이 컴포넌트를 변경하지 않는다는 뜻이다. Actor/ASC를 읽으므로 GT 전용이며 worker-safe 선언이 아니다.
- HandleMovementBlockChanged의 인자 모양은 엔진 delegate와 맞춘다. Tag는 변경 알림의 태그 값, NewCount는 알림 당시의 정수 count다. 참조 인자가 아닌 값 인자다.
- RefreshMovementPermission은 초기 연결과 태그 알림이라는 실제 두 호출자가 공유하는 계산이다.
- weak 참조는 ASC 수명을 연장하지 않는다. 실제 ASC 소유자는 M1의 Character다. Transient는 영구 저장할 설정이 아님을 나타낸다.
- FDelegateHandle은 내가 등록한 함수 하나를 해제하기 위한 식별자다. 상태 효과 handle이 아니다.
- 별도 count 멤버/태그 container/기절 bool을 만들지 않는다.

## 6. cpp: 등록과 초기 조회

기존 cpp include에 다음을 추가한다.

```cpp
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/Pawn.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"
```

- BlueprintLibrary는 Actor→ASC 공통 조회를 C++에서도 사용하기 위한 헤더다.
- ASC 헤더는 tag count/이벤트 API, Pawn 헤더는 입력 대기 벡터/엔진 입력 무시 조회에 필요하다.
- KhazanGameplayTags는 방금 선언한 native tag, LogChannels는 기존 LogDefault 로그 분류를 제공한다.

다음 함수를 추가한다.

```cpp
void UKhazanLocomotionComponent::BeginPlay()
{
    Super::BeginPlay();

    Intent.bMovementAllowed = false;

    UAbilitySystemComponent* ASC =
        UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetOwner());

    if (!IsValid(ASC))
    {
        UE_LOG(
            LogDefault,
            Error,
            TEXT("%s requires an AbilitySystemComponent for locomotion."),
            *GetNameSafe(GetOwner())
        );
        return;
    }

    ObservedAbilitySystemComponent = ASC;

    MovementBlockChangedHandle =
        ASC->RegisterGameplayTagEvent(
            KhazanGameplayTags::Block_Movement_Input,
            EGameplayTagEventType::NewOrRemoved
        ).AddUObject(
            this,
            &UKhazanLocomotionComponent::HandleMovementBlockChanged
        );

    RefreshMovementPermission();
}
```

실행 순서/줄의 의미:

1. Super가 컴포넌트의 기존 BeginPlay를 수행한다.
2. 초기 허용 값은 false로 둔다. 의존성 실패를 이동 허용으로 감추지 않는다.
3. GetOwner는 이 컴포넌트가 붙은 Actor다. 엔진 라이브러리가 M1 인터페이스를 통해 ASC를 얻으므로 Player 전용 캐스팅이 없다.
4. ASC가 없으면 기존 LogDefault에 owner 이름과 원인을 남기고 반환한다. %s는 문자열 자리, GetNameSafe는 owner가 없을 때도 이름 출력을 처리하며 *는 FString의 문자열 포인터를 넘긴다. 이 로그는 M1 연결/부모 구성을 확인하기 위한 것이다.
5. 성공 시 weak 참조를 보관한다.
6. RegisterGameplayTagEvent는 해당 태그의 이벤트 delegate를 얻는다. 여기서 태그가 부여되는 것은 아니다.
7. NewOrRemoved는 count가 없던 상태에서 생기거나 완전히 없어지는 경계에서 알린다. 양수 count 사이의 변화는 허용 여부를 바꾸지 않으므로 불필요한 재계산을 줄인다.
8. AddUObject는 이 컴포넌트와 멤버 함수 주소를 구독자로 연결하고 FDelegateHandle을 반환한다.
9. 등록 후 Refresh를 한 번 호출한다. 구독 전에 이미 효과가 존재했다면 이후 변경 알림만 기다려서는 현재 상태를 알 수 없기 때문이다.

M1의 Character PostInitializeComponents에서 ASC ActorInfo가 연결된 뒤 컴포넌트 BeginPlay가 오는 runtime 경계를 사용한다. 이 BeginPlay에서 InitAbilityActorInfo를 다시 호출하지 않는다. ASC 연결과 이동 태그 관측자의 시작은 서로 다른 책임이다.

## 7. cpp: 태그 결과와 최종 입력 허용

```cpp
void UKhazanLocomotionComponent::HandleMovementBlockChanged(
    const FGameplayTag Tag,
    int32 NewCount
)
{
    (void)Tag;
    (void)NewCount;

    RefreshMovementPermission();
}
```

두 인자는 엔진 delegate 시그니처를 맞추기 위해 받는다. (void) 표현은 인자를 의도적으로 사용하지 않음을 표시한다. 알림이 중첩되거나 다른 구독자가 상태를 바꾼 경우에도 현재 ASC 값을 기준으로 결정하도록 Refresh에서 다시 조회한다.

```cpp
void UKhazanLocomotionComponent::RefreshMovementPermission()
{
    check(IsInGameThread());

    const UAbilitySystemComponent* ASC =
        ObservedAbilitySystemComponent.Get();

    Intent.bMovementAllowed =
        ASC &&
        ASC->GetTagCount(KhazanGameplayTags::Block_Movement_Input) == 0;

    if (!Intent.bMovementAllowed)
    {
        if (APawn* Pawn = Cast<APawn>(GetOwner()))
        {
            Pawn->ConsumeMovementInputVector();
        }
    }
}
```

- check는 GT에서 gameplay 읽기/쓰기를 수행한다는 프로그래머 불변식 검사다.
- weak.Get()은 유효한 대상이 없으면 null이다.
- ASC가 있고 차단 tag count가 0일 때만 태그 정책상 허용한다. &&는 ASC가 없을 때 함수 호출을 건너뛴다.
- 0은 차단 원인이 없다는 개수이며 gameplay 튜닝값이 아니다.
- 차단되면 Pawn이 아직 소비하지 않은 일반 입력 대기 벡터를 비운다. 같은 프레임에 먼저 들어온 AddMovementInput이 남는 경우를 다룬다.
- ConsumeMovementInputVector는 엔진 대기 입력을 소비할 뿐이다. Intent.MoveInputWorld를 지우거나 Velocity를 강제로 멈추지 않는다.
- 이미 CMC가 이번 이동 계산에 소비한 입력/발생한 변위를 소급 취소하지는 않는다. 정확한 이동 결과는 Tick 순서/물리 경계와 함께 검사한다.
- CMC 제동/중력/외력은 계속 기존 규칙을 사용한다. StopMovementImmediately/DisableMovement를 이 태그의 의미로 넣지 않는다.

```cpp
bool UKhazanLocomotionComponent::IsMovementInputAllowed() const
{
    check(IsInGameThread());

    const APawn* Pawn = Cast<APawn>(GetOwner());

    return ObservedAbilitySystemComponent.IsValid()
        && Intent.bMovementAllowed
        && Pawn
        && !Pawn->IsMoveInputIgnored();
}
```

이 함수는 태그 정책, ASC 유효성, Pawn 존재, 엔진의 기존 입력 무시를 한곳에서 합친다. ASC가 없어졌는데 이전 true 투영만 남은 경우도 허용하지 않는다. 단락 평가로 Pawn이 없으면 마지막 함수는 호출하지 않는다.

Player와 Anim GT가 같은 결과를 소비한다. AnimInstance가 별도의 판단 원본/태그 구독자가 되는 것이 아니다. AI PathFollowing은 아직 이 함수를 사용하도록 연결하지 않았으므로 실제 AI 이동 차단 완료가 아니다.

## 8. cpp: 종료 시 자기 구독 정리

```cpp
void UKhazanLocomotionComponent::EndPlay(
    const EEndPlayReason::Type EndPlayReason
)
{
    if (UAbilitySystemComponent* ASC = ObservedAbilitySystemComponent.Get())
    {
        if (MovementBlockChangedHandle.IsValid())
        {
            ASC->UnregisterGameplayTagEvent(
                MovementBlockChangedHandle,
                KhazanGameplayTags::Block_Movement_Input,
                EGameplayTagEventType::NewOrRemoved
            );
        }
    }

    MovementBlockChangedHandle.Reset();
    ObservedAbilitySystemComponent.Reset();

    Intent.bMovementAllowed = false;
    ClearMoveInput();

    Super::EndPlay(EndPlayReason);
}
```

- ASC가 살아 있고 handle이 유효할 때만 자기 구독을 해제한다. 등록한 tag/event type과 같은 조합을 넘긴다.
- Reset은 handle과 weak 참조를 비운다. Reset만 하는 것은 엔진 delegate에서 구독을 제거하는 것과 다르므로 Unregister가 먼저다.
- 종료 시 읽기용 결과를 false로 두고 자기 입력을 지운다.
- 부모 EndPlay에 같은 종료 이유를 전달한다.
- 이 함수는 자신의 구독을 정리하며 ASC의 모든 태그/효과를 제거하지 않는다. Character의 M1 DestroyActiveState와 책임이 다르다.
- 대상 ASC가 이미 무효여도 자신의 참조/handle/input 정리는 수행한다. 새 Pawn은 새 컴포넌트와 새 구독을 갖는다.
- 이 소단계는 M1의 고정 Character 소유 ASC와 정상 BeginPlay/EndPlay 수명이다. Pawn 풀링/ASC 런타임 교체/별도 재등록 프로토콜이 완성된 것으로 확대하지 않는다.

## 9. 원시 입력은 제한 중에도 보존

기존 SetMovementAllowed(bool)의 cpp 정의를 제거한다. 외부 호출이 발견되면 그 제한 원인을 효과/handle로 이관한다.

SetMoveInputWorld에서 기존 허용 검사/Clear/return 블록을 제거하고 다음 형태로 만든다.

```cpp
void UKhazanLocomotionComponent::SetMoveInputWorld(const FVector& Input)
{
    const FVector Input2D(Input.X, Input.Y, 0.f);

    Intent.MoveInputWorld = Input2D.GetClampedToMaxSize(1.f);
    Intent.InputAmount = Intent.MoveInputWorld.Size2D();
}
```

- Input은 const 참조로 전달해 입력 벡터를 불필요하게 복사하거나 수정하지 않는다.
- 월드 평면 입력이므로 Z는 0이다.
- 벡터 길이는 최대 1로 제한하며 작은 입력을 모두 길이 1로 바꾸는 정규화가 아니다.
- InputAmount는 저장한 벡터의 평면 길이다. 무차원 입력량이며 cm/s 속도가 아니다.
- 여기서는 입력 사실을 기록하므로 허용 여부를 검사하지 않는다.
- ClearMoveInput은 기존대로 실제 Released/dead zone/종료 때 방향과 크기를 지운다. 태그 종료 알림이 임의로 과거 입력을 복원하지 않는다.

## 10. Player: 입력 기록 후 출력 gate

HandleInputMove를 다음 형태로 만든다. 기존 계산/임계값을 보존하면서 허용 검사의 위치를 옮긴 것이다.

```cpp
void AKhazanPlayer::HandleInputMove(
    const FVector2D& MovementInput,
    const FRotator& ControlRotation
)
{
    UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();

    if (!Locomotion)
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
    const FVector Forward = UKismetMathLibrary::GetForwardVector(YawRotation);
    const FVector Right = UKismetMathLibrary::GetRightVector(YawRotation);

    const FVector WorldInput =
        Forward * MovementInput.X + Right * MovementInput.Y;

    Locomotion->SetMoveInputWorld(WorldInput);

    RefreshLocomotionGait();

    if (!Locomotion->IsMovementInputAllowed())
    {
        return;
    }

    const FVector MoveDirection =
        Locomotion->GetIntent().MoveInputWorld.GetSafeNormal2D();

    AddMovementInput(MoveDirection, 1.f);
}
```

의미 있는 각 줄/분기:

1. 기존 공통 컴포넌트를 얻고 없으면 출력 없이 반환한다.
2. 입력 벡터 길이를 float로 읽고 실제 dead zone이면 기존 Released 처리를 한다. MoveInputDeadZone 값 자체는 변경하지 않는다.
3. Controller의 Yaw만 사용하여 수평 Forward/Right를 만든다. Pitch 때문에 평면 입력이 위/아래로 향하지 않게 한다.
4. 현재 프로젝트는 MovementInput.X가 전후, Y가 좌우다. 두 월드 축의 가중합으로 WorldInput을 만든다.
5. SetMoveInputWorld는 제한 상태에서도 원시 입력을 기록한다.
6. RefreshLocomotionGait는 요청 gait를 계산한다. 아래 수정으로 요청 계산과 CMC 적용을 나눈다.
7. 최종 허용 결과가 false이면 실제 이동 입력 전송만 생략한다. 여기서 HandleInputMoveReleased를 호출하지 않으므로 물리적으로 계속 누른 입력/토글 Sprint 요청을 해제로 바꾸지 않는다.
8. 허용되면 저장된 월드 입력의 평면 단위 방향을 만든다. GetSafeNormal2D는 영벡터도 처리한다.
9. AddMovementInput의 1은 기존 고정 gait 입력 스케일이다. 실제 속도는 기존 CMC 정책의 MaxWalkSpeed/가속/제동으로 결정된다.

기하 예: Controller Yaw=0, 입력 (X=1,Y=0)이면 Forward=(1,0,0)이므로 월드 입력도 (1,0,0)이다. 차단 tag가 있더라도 이 입력 사실은 보존되지만 AddMovementInput은 호출하지 않는다. 이 0/1은 축/정규화 예제이며 원작 튜닝 수치가 아니다.

RefreshLocomotionGait에는 다음 두 부분만 먼저 바꾼다.

기존 Intent를 읽은 뒤의 허용/입력량 검사:

```cpp
if (Intent.InputAmount <= 0.f)
{
    return;
}
```

기존 StickGait/RequestedGait 계산과 SetTargetGait는 유지한다. 그 직후, 기존 switch 앞에 추가한다.

```cpp
if (!Locomotion->IsMovementInputAllowed())
{
    return;
}
```

따라서 이 함수는 다음 순서가 된다.

```text
컴포넌트/CMC 참조 확인
→ 입력량 확인
→ 스틱/L3로 요청 gait 계산
→ SetTargetGait
→ 최종 입력 허용 확인
→ 기존 switch로 MaxWalkSpeed 적용
```

RunInputThreshold, WalkSpeed/RunSpeed/SprintSpeed와 switch는 이번에 바꾸지 않는다. 이 속도 적용은 M2.2 이관 전 임시로 남는 기존 경로이며 새 기능을 여기에 누적하지 않는다.

실제 Released/Canceled 처리는 계속 자기 입력을 정리한다. 제한 중 버튼을 놓으면 InputAmount는 0이 되고, 제한이 풀려도 새 입력이 없으면 움직이지 않아야 한다. M1 UnPossessed는 엔진 입력을 정리하지만 프로젝트 Intent/토글 입력 소유자 정리는 M2 후속 입력 수명 정리 항목이며, 이 소단계로 모든 빙의 전환의 입력 상태를 완료했다고 주장하지 않는다.

## 11. AnimInstance: GT snapshot 한 줄 연결

GatherGameThreadData의 기존 한 줄:

```cpp
NewData.bMovementAllowed = Intent.bMovementAllowed;
```

을 다음으로 바꾼다.

```cpp
NewData.bMovementAllowed = LocomotionComponent->IsMovementInputAllowed();
```

이 함수는 기존 check(IsInGameThread()) 아래에서 실행된다. ASC/Actor 접근이 필요한 공통 조회는 여기까지다. NativeThreadSafeUpdateAnimation에는 새 ASC/Actor 접근을 추가하지 않는다.

worker의 기존 계산은 유지된다.

```cpp
bHasMovementInput =
    Snapshot.bMovementAllowed && InputAmount > MovementInputThreshold;
```

InputAmount가 원시 입력으로 남아 있어도 허용이 false이면 표현에 사용하는 유효 이동 입력은 false다. 이 때문에 기존 입력 해제 기반 Stop 선택과 연결된다. 제한 중 실제 Velocity가 남는 것은 CMC 제동 결과일 수 있으며 태그 실패로 단정하지 않는다.

loop/Stop gait, Stop 발 이력, marker, Start 제외, InGame/root-locked Stop 정책과 ABP 그래프는 이번 범위에서 바꾸지 않는다.

## 12. UE 5.8 검사 효과 만들기

Source 적용 후 에디터를 닫은 전체 KhazanEditor Win64 Development 빌드와 새 Editor 실행을 먼저 완료한다. native tag가 에디터 picker에 보이는지 확인한다.

검사용 제안 경로는 /Game/Tests/Gameplay/GE_Test_BlockMovement다. 기존 경로가 있으면 새로 덮어쓰지 않는다. 이것은 원작 효과/최종 Stun 데이터가 아니라 연결을 검사할 임시 자산이다.

1. Content Browser에서 해당 Tests/Gameplay 폴더를 만들거나 연다.
2. Blueprint Class → All Classes → GameplayEffect를 부모로 선택하고 GE_Test_BlockMovement를 만든다.
3. Class Defaults에서 Duration Policy를 Infinite로 둔다. 명시적 handle 제거까지 유지하는 검사 목적이다. Instant 효과로 지속 소유 태그를 검사하지 않는다.
4. Stacking Type은 None으로 둔다. 동일 정의를 두 번 적용하면 별도 active effect 인스턴스/handle로 검사하기 위해서다.
5. Components에서 Grant Tags to Target Actor를 추가한다. 로컬 UE 5.8.2의 표시명은 Target Tags (Granted to Actor)이며 타입은 UTargetTagsGameplayEffectComponent다.
6. 그 컴포넌트의 Add Tags 아래 추가 태그 목록에 Block.Movement.Input을 넣는다. Combined/Inherited 항목은 상속 결과이며 추가 목록에 작성한다.
7. Attribute modifier/Execution/Cue/추가 적용 조건은 이번 검사 효과에 넣지 않는다. Compile/Save 후 실제 적용 태그를 확인한다.

효과 자체를 분류하는 Asset Tags와 대상 ASC에 부여하는 Target Tags는 다르다. Asset Tags에만 넣고 캐릭터 상태가 바뀌기를 기대하지 않는다.

## 13. 두 원인의 handle 검증

임시 검사는 플레이어 BP 또는 별도 테스트 그래프에서 수행한다. 기존 제품 흐름은 보존하며 키 이벤트는 테스트용으로 선택한다. 하나의 적용을 반복해 handle을 덮어쓰지 않도록 각 A/B 적용 경로 앞에 Do Once를 둘 수 있다. 이 경우 각 새 시나리오는 새 PIE로 시작한다.

검사용 변수:

| 변수 | BP 타입/수명 | 역할 |
| --- | --- | --- |
| TestASC | AbilitySystemComponent Object Reference | 적용/제거할 같은 대상. 한 PIE의 검사 문맥 |
| BlockHandleA | Active Gameplay Effect Handle | 첫 적용이 반환한 handle |
| BlockHandleB | Active Gameplay Effect Handle | 두 번째 적용이 반환한 별도 handle |

적용 경로 A:

1. Get Ability System Component의 Actor에 검사할 Pawn을 넣고 Return Value를 TestASC에 보관한다. Is Valid로 존재를 검사한다.
2. TestASC를 Target으로 Make Effect Context를 호출한다. 반환 Context는 이 대상 자신이 테스트 효과를 만든다는 문맥이다.
3. Make Outgoing Spec의 Target=TestASC, Gameplay Effect Class=GE_Test_BlockMovement, Context=위 반환값으로 연결한다.
4. Level은 1로 둔다. 이 효과에는 레벨로 계산하는 수치가 없으므로 검사 Spec을 생성하기 위한 기술적 입력이며 원작 스킬 레벨/피해값을 재현하는 수치가 아니다.
5. Make Outgoing Spec의 Return Value를 Apply Gameplay Effect Spec To Self의 Spec Handle에 연결하고 Target=TestASC로 둔다. BlueprintCallable 노드들의 실행 핀도 Context 생성→Spec 생성→적용 순서로 연결한다.
6. Apply의 Return Value를 BlockHandleA에 저장한다. 각 반환 타입의 유효성을 확인하고 실패는 차단 성공으로 판정하지 않는다.

B도 같은 절차로 적용하되 반환값은 BlockHandleB에 저장한다. GE 정의 자산은 같아도 적용 결과 handle은 별개다.

제거 경로 A는 Remove Active Gameplay Effect(Target=TestASC, Handle=BlockHandleA)다. Stacks to Remove는 엔진 기본 -1을 사용해 **그 handle에 해당하는 효과**를 제거한다. B는 B handle로만 제거한다. 모든 Granted Tags가 같은 효과를 일괄 제거하는 노드를 사용하지 않는다.

검사 행렬:

| 순서 | 태그 count | bMovementAllowed | 일반 입력 허용 결과 |
| --- | --- | --- | --- |
| 효과 없음 | 0 | true | 엔진 입력 gate도 허용하면 true |
| A 적용 | 1 | false | false |
| B 추가 | 2 | false | false |
| A만 제거 | 1 | false | false |
| B도 제거 | 0 | true | 엔진 입력 gate도 허용하면 true |

이 count는 Stacking Type=None의 독립 효과 두 개와 추가 제한 원인이 없는 검사 조건이다. 실제 스택 수와 태그 count가 모든 설정에서 같다고 일반화하지 않는다.

NewOrRemoved에서는 1→2, 2→1에 이 callback이 호출되지 않아도 정상이다. 결과가 계속 false이기 때문이다. 마지막 1→0에서 허용이 갱신된다. 필요하면 ASC의 GameplayTagCountContainer 또는 GetTagCount 반환으로 값을 확인한다.

FDelegateHandle은 이 표의 A/B가 아니다. 그것은 Locomotion이 상태 변경 알림을 받는 구독을 해제하는 용도이고, A/B는 각각 FActiveGameplayEffectHandle이다.

## 14. 실제 동작·실패 검사와 범위

- 정지 상태에서 A/B를 적용/해제하고 입력 이벤트 없이 bMovementAllowed가 바뀌는지 확인한다.
- 이동 입력을 계속 누른 상태에서 A 적용: Intent 방향/크기는 남고 IsMovementInputAllowed=false, 허용된 새 AddMovementInput은 없으며 CMC가 기존 물리 규칙으로 제동해야 한다.
- A가 유지되는 동안 다른 방향으로 입력: 원시 방향은 바뀌지만 이동 출력은 없다.
- A/B 중 하나만 제거: 계속 차단. 마지막 효과 제거 후 입력을 계속 누르고 있으면 기존 Enhanced Input의 다음 유효 이동 입력에서 허용된 이동이 재개된다. 콜백이 임의로 과거 입력을 재전송하지 않는다.
- 차단 중 실제 입력 Released: Intent=0. 마지막 효과가 없어져도 새 입력이 없으면 정지 유지.
- Controller의 엔진 입력 무시가 남아 있다면 tag count=0이어도 IsMovementInputAllowed=false여야 한다.
- 초기 효과가 구독 전에 존재하는 경로에서는 첫 Refresh가 현재 count를 읽어 차단해야 한다. 현재 최소 그래프의 BeginPlay 이후 적용 검사와 이 초기화 순서 검사를 구분한다.
- delegate callback/Refresh/GT Gather에 중단점을 둘 경우 GT에서 실행하는지, worker에는 값 snapshot만 들어가는지 확인한다.
- PIE 종료/새 PIE에서 이전 구독/입력 문맥이 잔류하지 않아야 한다. 임시 effect handle/노드/키/배치/검사용 중단점은 자기 작업분만 정리한다.
- Monster에서도 ASC→Locomotion의 태그 투영은 같은 부모 컴포넌트 경로다. **기본 AI MoveTo의 구동 차단/재개는 M2.3 미구현**이며, Monster 태그 조회 성공을 실제 AI 제어 성공으로 기록하지 않는다.
- CMC 속도/회전·최대 gait 정책을 입력 이벤트와 분리해 적용하는 책임은 M2.2에 남는다. 이번 bridge가 CMC의 모든 이동 경로를 중재한 것은 아니다.
- 기존 Walk/Run/Sprint/Stop 입력과 재입력을 확인한다. 피격 몽타주/공격 승인/무적/강인도는 M3 이후 검사다.

| 증상 | 먼저 볼 곳 |
| --- | --- |
| 태그 picker에 없음 | native DECLARE/DEFINE 위치, 전체 빌드와 새 Editor |
| 효과 적용 후 count=0 | Duration Policy, Target Tags와 Asset Tags 구분, 적용 대상 ASC, 유효 Spec/handle |
| A 제거 시 바로 풀림 | 두 handle이 별개인지, None stacking인지, 전체 효과 제거를 사용했는지 |
| 시작부터 계속 차단 | ASC 조회 로그/부모, Component BeginPlay, 초기 Refresh, 엔진 입력 무시 |
| 입력을 누르는데 Intent가 0 | SetMoveInputWorld의 옛 허용 gate 또는 Player의 옛 Released 분기 잔류 |
| 제한 중 애니메이션만 계속 이동 | GT snapshot이 공통 IsMovementInputAllowed를 사용하는지 |
| 같은 프레임에 조금 움직임 | 이미 CMC가 소비한 입력/제동·외력과 미소비 입력을 구분, Tick 순서 검사 |
| 종료 후 알림 문제 | 자기 delegate handle의 Unregister, EndPlay/ASC 유효성, 새 PIE에서 이전 객체 참조 사용 여부 |

## 15. 수치·엔진 근거·적용 상태

- 새로운 게임플레이 속도·회전·임계값·타이머를 선정하지 않았다. 기존 MoveInputDeadZone/RunInputThreshold/WalkSpeed/RunSpeed/SprintSpeed를 그대로 참조하며 이 값들의 원작 검증 상태를 승격하지 않는다.
- 0/1은 초기값, count 부재, 평면/단위 입력의 기존 수학적 표현이다. 테스트 Spec Level=1, Remove의 -1은 사용한 엔진 API/검사 설정으로 목적을 위에서 밝혔다.
- 로컬 UE 5.8.2의 AbilitySystemComponent.h/.cpp: Register/UnregisterGameplayTagEvent, GetTagCount, MakeEffectContext/MakeOutgoingSpec/BP_ApplyGameplayEffectSpecToSelf/RemoveActiveGameplayEffect.
- GameplayEffectTypes.h: FOnGameplayEffectTagCountChanged의 인자, NewOrRemoved/AnyCountChange.
- GameplayEffectComponents/TargetTagsGameplayEffectComponent.h/.cpp: UCLASS 표시명/EditorFriendlyName/지속 Owned Tag와 Instant 검증.
- Engine/Private/Pawn.cpp의 ConsumeMovementInputVector/Internal_ConsumeMovementInputVector: 입력 소비와 ControlInputVector 초기화. CMC의 RequestDirectMove/RequestPathMove/ApplyRequestedMove는 별도 경로이므로 후속 M2.3 검증이 필요하다.
- [Epic 태그 이벤트 종류](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/GameplayAbilities/EGameplayTagEventType__Type)
- [Epic 대상 태그 부여 컴포넌트](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/GameplayAbilities/UTargetTagsGameplayEffectCompone-)
- [Epic Gameplay Effects](https://dev.epicgames.com/documentation/unreal-engine/gameplay-effects-for-the-gameplay-ability-system-in-unreal-engine?lang=en-US)

M1은 사용자 완료 보고와 현재 Source 반영을 확인했다. M2.1은 이 문서로 제시한 설계/코드/검사 절차이며, 어시스턴트가 실제 Source/BP/에셋 적용·빌드·PIE를 수행한 결과가 아니다. 후속 기록에는 실제 적용 파일, 빌드 결과, 위 조건별 관측과 남은 항목을 적는다.



## 16. M2.1 수명 보충 — 빙의 해제에서 원시 입력 정리

M2.1에서 원시 입력을 보존하므로, 입력 소유자가 없어지는 UnPossessed도 이번 소단계에 포함한다. 위 10절의 “빙의 입력 정리는 후속 항목” 중 Player의 원시 이동/Sprint 요청 정리는 아래 계약으로 구체화하며, 3절의 수정 범위에 KhazanPlayer.h가 추가된다. 이동 수치/CMC 작성자 이관과 AI 입력 수명은 계속 후속 범위다.

KhazanPlayer.h의 public 영역에 추가한다.

```cpp
virtual void UnPossessed() override;
```

KhazanPlayer.cpp에 추가한다.

```cpp
void AKhazanPlayer::UnPossessed()
{
    HandleInputMoveReleased();
    bSprintRequested = false;

    Super::UnPossessed();
}
```

- 먼저 기존 Released 함수를 통해 자신의 원시 이동 입력을 비운다. 토글 모드도 기존 해제 처리를 거친다.
- 홀드 모드 역시 빙의 해제 후 실제 키 Released를 받지 못할 수 있으므로 bSprintRequested를 명시적으로 false로 둔다. 이는 개인 입력 요청 정리이며 ASC의 제한 태그를 해제하는 동작이 아니다.
- 그 뒤 Super를 호출하면 M1 AKhazanCharacter::UnPossessed의 엔진 소유 해제와 ActorInfo Refresh가 계속 실행된다. 부모의 해제 이벤트가 원시 입력을 읽을 때도 이전 눌림이 남지 않도록 먼저 정리한다.
- 새로운 helper/입력 상태 원본은 만들지 않는다. 기존 실제 입력 소유자인 Player에서 정리한다.
- 검사: 이동/Sprint를 누른 상태에서 UnPossess 후 이전 Pawn의 MoveInputWorld/InputAmount는 0, Sprint 요청은 false다. ASC에 별도의 차단 효과가 있었다면 그 기여는 유지돼야 한다. 재빙의 후 새 입력으로 이동하며 옛 입력을 자동 재생하지 않는다.
- 이 보충도 사용자 적용용 코드다. 실제 게임 파일 편집/빙의 시험을 수행한 결과는 아니다.


## 17. 2026-09-09 사용자 적용본 PIE 종료 crash 진단과 M2.1 재검증

### 확정된 종료 crash 원인

사용자 적용본의 `UKhazanLocomotionComponent::EndPlay()`에는 `Super::EndPlay(EndPlayReason)`가 함수 시작과 끝에 각각 한 번씩, 합계 두 번 있다. UE 5.8.2의 `UActorComponent::EndPlay()`는 진입 시 `check(bHasBegunPlay)`를 검사하고 정상 종료 끝에서 `bHasBegunPlay=false`로 바꾼다. 따라서 첫 번째 Super 호출은 정상이나 두 번째 호출은 반드시 같은 컴포넌트에서 `Assertion failed: bHasBegunPlay`, `ActorComponent.cpp:1668`을 발생시킨다.

2026-09-09 14:45:01과 14:45:41의 두 최신 crash report가 같은 assert를 기록했고, 로그 순서도 `BeginTearingDown` 직후 assert다. GE 적용이나 AnimInstance worker 접근이 이 crash의 직접 원인이 아니다.

정리 코드는 구독 해제와 로컬 상태 Reset을 먼저 수행하고 **Super를 마지막에 단 한 번만** 호출한다. 사용자 적용본에서는 함수 첫 줄 쪽의 Super 호출만 제거하고, 기존 마지막 호출은 유지한다. 8절의 원래 제시 코드가 이 순서다.

### 태그 이벤트 구독 적용 오류

사용자 적용본은 `RegisterGameplayTagEvent()`의 반환값을 다음처럼 지역 delegate에 값 복사한 뒤 그 복사본에 구독했다.

```cpp
FOnGameplayEffectTagCountChanged Event =
    ASC->RegisterGameplayTagEvent(
        KhazanGameplayTags::Block_Movement_Input,
        EGameplayTagEventType::NewOrRemoved
    );

MovementBlockChangedHandle = Event.AddUObject(
    this,
    &UKhazanLocomotionComponent::HandleMovementBlockChanged
);
```

UE 5.8.2의 `RegisterGameplayTagEvent()` 반환형은 `FOnGameplayEffectTagCountChanged&`다. 위 코드는 ASC가 소유한 delegate가 아니라 지역 복사본에 callback을 추가하며, BeginPlay가 끝나면 그 복사본도 사라진다. 저장된 handle 역시 ASC delegate의 구독을 가리키지 않으므로 실제 태그의 0→1/1→0 변화가 `HandleMovementBlockChanged()`를 호출하지 않는다.

8절의 원래 제시 방식처럼 반환된 ASC delegate에 직접 추가한다.

```cpp
MovementBlockChangedHandle =
    ASC->RegisterGameplayTagEvent(
        KhazanGameplayTags::Block_Movement_Input,
        EGameplayTagEventType::NewOrRemoved
    ).AddUObject(
        this,
        &UKhazanLocomotionComponent::HandleMovementBlockChanged
    );
```

지역 이름이 필요하다면 값이 아니라 `FOnGameplayEffectTagCountChanged& Event` 참조여야 하지만, 이 단계에서는 직접 체인이 구독 소유자를 가장 명확히 보여 준다.

### 현재 테스트 판정

- PIE world와 `BP_KhazanPlayer_C_0`는 정상 시작했고, Locomotion의 ASC 누락 오류 로그는 없었다. M1의 인터페이스 조회가 BeginPlay에서 ASC를 찾은 경로까지는 통과한 것으로 판정한다.
- 현재 `GE_Test_BlockMovement`에는 `DurationPolicy=Infinite`, `Block.Movement.Input`, `TargetTagsGameplayEffectComponent`, `Stacking=None` 데이터가 존재한다. 05:25의 Instant 설정 오류는 05:26 재저장·검증에서 사라졌다.
- 현재 Player BP에는 TestASC, BlockHandleA/B, MakeEffectContext, MakeOutgoingSpec, Apply/Remove 노드가 존재한다. 그러나 최신 실행 로그에는 handle 유효성, tag count, 허용 결과가 남아 있지 않다.
- 무엇보다 현재 C++ callback이 ASC delegate에 연결되지 않았으므로 A/B 동적 적용·해제 검사는 통과로 인정할 수 없다. 시작 전에 이미 태그가 있었다면 최초 Refresh만 값을 읽을 수 있지만, BeginPlay 뒤의 변화 검증을 대신하지 않는다.

### 수정 후 합격 순서

1. 전체 `KhazanEditor Win64 Development` 빌드 후 새 Editor를 실행한다.
2. 효과를 적용하지 않은 PIE에서 이동 가능과 정상 PIE 종료를 먼저 확인한다. 이 단계에서 같은 assert가 다시 나오면 실행 DLL의 시각과 빌드 산출물을 대조한다.
3. `HandleMovementBlockChanged()`와 `RefreshMovementPermission()`의 tag count 대입 줄에 중단점을 둔다.
4. 효과 없음: count 0, `bMovementAllowed=true`, 이동 가능.
5. A 적용: A handle 유효, count 1, 0→1 callback 1회, `bMovementAllowed=false`, 원시 Intent는 입력 중 보존되지만 `AddMovementInput`은 호출되지 않음.
6. B 적용: B handle은 A와 다른 유효 handle, count 2, `NewOrRemoved` callback 추가 호출 없음, 계속 차단.
7. A만 제거: count 1, callback 추가 호출 없음, 계속 차단.
8. B 제거: count 0, 1→0 callback 1회, `bMovementAllowed=true`, 다음 유효 입력 event부터 이동 재개.
9. 차단 중 실제 Move Released도 별도로 시험해 Intent가 0이 되는지 확인한다.
10. PIE를 종료하고 새 PIE를 한 번 더 시작·종료한다. 종료 assert와 이전 PIE 구독 재호출이 모두 없어야 M2.1 종료 수명이 통과다.

이 기록은 crash dump, 로그, 현재 소스와 asset 정적 확인 결과다. 사용자가 두 C++ 지점을 수정한 뒤의 새 빌드·PIE 결과는 아직 없다.


## 18. 2026-09-09 수정본 C++·BP 실제 검증

### 판정

- **공통 ASC → 이동 허용 캐시 → Player/Anim 소비로 이어지는 M2.1 핵심 bridge는 통과했다.** 수정된 callback 구독, 태그 중첩 카운트, 효과별 handle 해제, PIE 종료 cleanup을 실제 실행에서 확인했다.
- **현재 Player BP도 컴파일되고 실제로 실행된다.** 다만 BeginPlay 한 실행 흐름에서 A 적용 → B 적용 → A 제거 → B 제거를 모두 즉시 끝내므로, 첫 프레임 뒤에는 이미 count 0 / 이동 허용 상태다. 플레이어가 키를 눌러 차단을 체감할 시간이 없는 테스트 구성이다.
- 따라서 M2.1의 구조·효과·종료 수명은 합격이며, 실제 키보드/패드 `IA_Move`가 차단 중 `AddMovementInput`까지 내려가지 않는 장면을 보는 **수동 입력 시험 1건**만 남긴다. 이 시험 전에는 M2.1 전체 완료나 M2.2 시작으로 기록하지 않는다.

### 정적 확인 결과

- `BeginPlay()`는 `RegisterGameplayTagEvent()` 반환값을 `FOnGameplayEffectTagCountChanged&`로 받아 ASC가 소유한 delegate에 `AddUObject()`한다. 이전 지역 delegate 값 복사 오류가 없다.
- `EndPlay()`는 handle 구독 해제, weak pointer와 Intent 정리 뒤 마지막에 `Super::EndPlay()`를 한 번만 호출한다.
- Player는 원시 이동 입력과 gait 요청을 먼저 기록하고 `IsMovementInputAllowed()` 뒤에서만 `AddMovementInput`과 CMC 속도 출력을 허용한다. `UnPossessed()`는 원시 입력과 Sprint 요청을 정리한다.
- AnimInstance의 Game Thread 수집은 `IsMovementInputAllowed()` 결과만 snapshot에 복사한다. worker에서 ASC를 읽거나 수정하는 경로는 추가되지 않았다.
- `/Game/Test/GE_Test_BlockMovement`는 Infinite, `Block.Movement.Input` 부여, `TargetTagsGameplayEffectComponent`, Stacking None으로 확인했다.
- `/Game/_Art/Kazan/Character/Bluprints/BP_KhazanPlayer`는 `BS_UP_TO_DATE`, compile error 0, warning 0, EventGraph 21 nodes다. PIE 인스턴스의 `TestASC`는 자기 `AbilitySystemComponent`를 가리켰고 BP가 만든 A/B handle은 각각 14/15이며 둘 다 실행 성공이고 서로 달랐다.

### 실제 PIE 카운트·허용값

현재 Player ASC에 실제 `GE_Test_BlockMovement` class를 적용하고, 서로 다른 handle A/B를 하나씩 제거했다. 아래 `이동 허용`은 Locomotion Intent에 캐시된 `movement_allowed` 값이다.

| 순서 | Block tag count | 활성 Test GE 수 | 이동 허용 |
|---|---:|---:|---|
| BP 즉시 시험 뒤 기준 상태 | 0 | 0 | true |
| A 적용 | 1 | 1 | false |
| B 적용 | 2 | 2 | false |
| A만 제거 | 1 | 1 | false |
| B 제거 | 0 | 0 | true |

- 런타임 probe의 A/B handle은 11/12였고 둘 다 적용 성공, 서로 다른 handle, 개별 제거 반환값 true였다.
- 이 컴포넌트는 tick으로 허용 캐시를 갱신하지 않는다. BeginPlay 뒤 실제 효과 변화에 맞춰 캐시가 바뀐 결과는 ASC의 `NewOrRemoved` callback이 현재 delegate에 연결됐음을 보여 준다.
- 별도 handle 13의 효과를 활성 상태(count 1, 허용 false)로 남긴 채 PIE를 종료했다. `BeginTearingDown` 뒤 `CleanupWorld for DevMap`까지 진행됐고 Editor process는 유지됐다.
- 두 번째 PIE는 같은 Player 1개, count 0, 활성 Test GE 0, 허용 true로 시작했고 다시 정상 종료됐다. 이전 PIE의 효과나 구독이 다음 PIE에 남지 않았다.
- `Saved/Crashes`의 최신 폴더는 수정 전 14:45:41의 기존 assert이며 이후 새 crash 폴더가 없다. 현재 Editor PID 23328은 연결·응답 상태이고 PIE는 Idle이다.

### 왜 현재 BP만 보고는 동작을 알기 어려운가

현재 Event BeginPlay의 Sequence 두 출력은 같은 BeginPlay 호출 안에서 순서대로 실행된다. A/B 적용 직후 A/B 제거까지 모두 동기 실행되므로 화면이 그려지고 사용자가 입력할 때는 이미 차단이 해제돼 있다. A/B handle과 효과 파이프라인 검사용으로는 유효하지만 이동 차단 체감 시험에는 맞지 않는다.

수동 시험 동안만 BeginPlay에는 `TestASC` 저장과 `IsValid` 확인을 남기고, 아래 네 동작을 각각 별도 Custom Event 또는 임시 테스트 입력에 연결한다.

1. `Test_ApplyA`: Test GE를 적용하고 반환 handle을 `BlockHandleA`에 저장한다.
2. `Test_ApplyB`: 같은 GE를 적용하고 반환 handle을 `BlockHandleB`에 저장한다.
3. `Test_RemoveA`: `BlockHandleA`만 제거한다.
4. `Test_RemoveB`: `BlockHandleB`만 제거한다.

기대 동작은 기준 상태에서 이동 가능, A 적용 후 차단, B 적용 뒤에도 차단, A만 제거해도 차단, B까지 제거한 다음 새 입력 event부터 이동 재개다. 차단 중 실제 Move Released를 한 번 발생시켜 `MoveInputWorld`와 `InputAmount`가 0으로 정리되는지도 본다. 고정 Delay 수치는 필요하지 않으며 각 단계 사이에 직접 이동 입력을 시험하면 된다.

Enhanced Input의 automation 연속 주입도 시도했지만 이 실행에서는 `IA_Move`의 프로젝트 binding까지 전달되지 않았다. 허용 상태에서도 변위 0, InputAmount 0, 가속도/속도 0이어서 차단 로직의 실패 증거로 사용할 수 없다. 실제 키보드/패드 입력 시험은 위 분리된 BP 이벤트로 수행한다.

이번 C++은 15:00:23 Live Coding patch에 반영됐고 `Live coding succeeded`와 이후 PIE 실행을 확인했다. Editor 완전 종료 뒤 전체 `KhazanEditor Win64 Development` 빌드는 아직 수행하지 않았으므로 M2.1 최종 마감 때 별도로 확인한다. 어시스턴트가 Source/BP/asset을 수정하지 않았고, 이 절의 문서만 추가했다.

### 같은 세션 후속 — 실제 `IA_Move` gate 합격

앞선 automation 연속 주입 대신 `EnhancedInputLocalPlayerSubsystem::InjectInputVectorForAction()`으로 실제 `/Game/Input/Locomotion/IA_Move`에 `(X=0, Y=1)` 벡터를 12프레임 전달해 프로젝트 binding을 다시 검사했다.

| 조건 | Block count | 캐시 허용 | 원시 InputAmount | 시험 구간 변위 | 종료 시 속도 | 종료 시 가속도 |
|---|---:|---:|---:|---:|---|---|
| Test GE 활성 | 1 | false | 1.0 | 0.0 uu | (0, 0, 0) | (0, 0, 0) |
| 같은 GE 제거 후 | 0 | true | 1.0 | 387.214 uu | (0, 470, 0) uu/s | (0, 1800, 0) uu/s² |

- 차단 중 `InputAmount=1.0`은 Enhanced Input → Controller binding → `AKhazanPlayer::HandleInputMove()` → `SetMoveInputWorld()`까지 실제로 도달했음을 뜻한다. 동시에 변위·속도·가속도가 모두 0이므로 허용 gate 뒤의 `AddMovementInput()`은 실행되지 않았다.
- 효과 제거 반환값은 true였고 callback 뒤 count 0 / 허용 true가 됐다. 같은 action 주입에서 이동·속도·가속도가 생겨 차단 해제 경로도 확인됐다.
- 주입을 중단한 다음 `InputAmount=0.0`, `MoveInputWorld=(0,0,0)`이 되어 Completed/Released 정리도 통과했다.
- 위 470, 1800, 387.214는 현재 프로젝트의 이 PIE 실행에서 읽은 **관측값**이며 원작 metadata 값이나 새 튜닝 제안이 아니다.
- 마지막 PIE도 `BeginTearingDown` → `CleanupWorld for DevMap`으로 정상 종료했고 임시 callback과 Python 참조를 모두 제거했다. Editor는 Idle이다.

이 추가 결과로 M2.1의 기능 런타임 합격 조건은 충족됐다. 현재 BP의 한 프레임 적용·해제는 사람이 화면으로 보기 어렵다는 사용성 문제만 남으며 기능 실패가 아니다. 네 Custom Event 분리는 시각적으로 다시 보고 싶을 때 사용할 임시 테스트 개선안이다. 마일스톤을 완전히 닫기 전 남은 검증은 Editor 완전 종료 뒤 전체 Development Editor 빌드 한 번이다.


<a id="m2-2-m2-3-detailed-guide-20260909"></a>

## 19. 2026-09-09 — M2.1 최종 완료와 M2.2·M2.3 연속 공동 구현 가이드

### 19.1 M2.1 최종 판정

에디터를 완전히 종료한 상태에서 다음 전체 빌드를 추가로 수행했다.

```text
Build.bat KhazanEditor Win64 Development Khazan.uproject -WaitMutex -FromMsBuild
Result: Succeeded
Target is up to date
ExitCode: 0
```

앞 절에서 확인한 실제 `IA_Move` 차단/해제, 효과 A/B의 독립 handle과 tag count, 두 번의 정상 PIE 종료에 이 전체 빌드 성공이 더해졌다. 따라서 **M2.1은 완료**다. 현재 Player BP의 BeginPlay 시험 노드가 한 호출 안에서 효과를 모두 적용·제거해 사람이 화면으로 보기 어렵다는 점은 테스트 조작 방식의 문제이며 M2.1 기능 미완료 사유가 아니다.

이번부터 현재 단계는 M2.2와 M2.3이다. 아래 내용은 사용자가 직접 구현할 설명이며, 아직 Source/BP/에셋에 적용되거나 빌드·PIE를 통과한 결과가 아니다. 두 단계를 한 문서에서 연속으로 다루지만 다음 순서를 지킨다.

1. M2.2 C++를 적용한다.
2. 전체 빌드 후 Character Definition 에셋을 만들고 Player만 검증한다.
3. M2.2가 통과한 상태에서 M2.3 C++를 적용한다.
4. 다시 전체 빌드한 뒤 일반 적 시험 셸, NavMesh, Blackboard, Behavior Tree를 연결한다.
5. Player 회귀와 AI의 중단·재개·도착·실패를 함께 검증한다.

중간 빌드는 작업량을 줄이기 위한 생략이 아니다. M2.2의 데이터/정책 오류와 M2.3의 내비게이션 수명 오류가 같은 PIE에서 함께 나타나는 것을 막는 진단 경계다.

### 19.2 표적 조사에서 확인한 현재 사실

읽기 전용 Python commandlet로 현재 Blueprint CDO와 asset registry를 조사했고 결과를 `Saved/ImportReports/M2_2_3_CurrentCDO_20260909.json`에 저장했다. CDO는 **Class Default Object**의 약자다. 클래스 또는 Blueprint 인스턴스가 생성될 때 복사해 쓰는 기본값 객체이며, 소스 생성자의 값과 Blueprint가 직렬화해 덮어쓴 값이 합쳐진 결과를 보여 준다.

| 대상 | 실제 확인값 | 의미 |
| --- | --- | --- |
| `BP_KhazanPlayer` 부모 | `/Script/Khazan.KhazanPlayer` | 현재 Player 게임플레이 셸이 맞다. |
| Player Walk / Run / Sprint | 170 / 470 / 600 cm/s | 현재 Player CDO의 사용자 설정값이다. 원작 metadata 직접 확인값은 아니다. |
| Player 입력 Run 임계값 / Dead Zone | 약 0.6 / 0.1 | Player 입력 어댑터 설정이다. 부동소수점 출력의 미세한 꼬리는 저장 표현이며 다른 튜닝값이 아니다. |
| Player CDO `MaxWalkSpeed` | 300 cm/s | 소스 생성자의 600과 다르다. Blueprint가 직렬화한 값이 존재한다. |
| 실제 BeginPlay 직후 속도 | 기존 코드가 170으로 다시 작성 | 현재는 생성자 600 → Blueprint CDO 300 → BeginPlay 170 → 입력 때 gait별 값이라는 다중 작성 경로다. |
| Min Analog / Max Acceleration / Walking Braking | 15 cm/s / 1800 cm/s² / 1800 cm/s² | 현재 CDO 확인값이다. 원작 검증값이 아니다. |
| Rotation Rate | Yaw 540 deg/s | 현재 CDO 확인값이다. |
| 회전 플래그 | Orient Rotation to Movement=true, Use Controller Desired Rotation=false | 현재 Velocity Direction 동작이다. |
| 현재 MovementComponent 클래스 | `/Script/Engine.CharacterMovementComponent` | M2.3 전에는 프로젝트 전용 CMC가 없다. |
| 수입 Swordsman/Archer BP 부모 | `/Script/Engine.Actor` | 두 에셋 모두 Character도 `AKhazanMonster`도 아니다. 바로 AIController/CMC를 붙일 수 없다. |

따라서 170/470/600/15/1800/1800/540은 **현재 프로젝트 이관값**으로 사용한다. 원작에서 직접 추출한 수치라고 표현하지 않는다. M2.3 시험 Monster가 같은 수치를 쓰는 경우에도 원작 적의 수치가 아니라 Player와 AI 경로 차이만 비교하기 위한 **임시 시험값**이다. 나중에 원작 적 metadata를 찾으면 의미·단위·조건을 대조한 다음 Monster Definition에서 교체한다.

### 19.3 먼저 이해해야 할 용어와 관계

#### Character Definition

`Character Definition`은 캐릭터 한 종류의 읽기 전용 설정을 모은 `UPrimaryDataAsset`이다. `DataAsset`은 월드에 Spawn되는 Actor가 아니라 Content Browser에 저장되는 데이터 객체다. `PrimaryDataAsset`은 추후 Asset Manager가 식별·로딩할 수 있는 기본 식별 규약까지 제공한다.

이번 M2.2에서는 이동 수치와 기본 gait/회전 모드만 넣는다. 공격 Ability, Attribute, AI Behavior Tree, 애니메이션 레이어까지 미리 넣지 않는다. 아직 소비자가 없고 로딩/준비 수명도 확정되지 않은 데이터를 한 자산에 선행 추가하면 데이터 주도 구조가 아니라 큰 설정 보관함이 된다.

Character는 Definition을 선택하고, LocomotionComponent는 그 안의 이동 설정을 복사해 런타임 정책을 계산한다. DataAsset 자체는 실행 중 수정하지 않는다.

```text
BP_KhazanPlayer CDO
    └─ CharacterDefinition 참조
         └─ FKhazanLocomotionConfig (읽기 전용 원본)
              └─ LocomotionComponent가 런타임 값으로 복사·검증
                   └─ Resolved Policy 계산
                        └─ CMC에 적용
```

#### CMC

CMC는 `Character Movement Component`, 즉 `UCharacterMovementComponent`의 줄임말이다. 실제 위치, 속도, 가속도, 바닥 판정, 낙하, 충돌 이동을 수행한다. LocomotionComponent는 “현재 허용된 최고 gait와 회전 방식”이라는 정책을 계산하지만 Actor 위치를 직접 적분하지 않는다. CMC는 그 정책을 받아 실제 물리를 수행한다.

`단일 작성자(single writer)`는 CMC를 오직 한 객체만 호출한다는 뜻이 아니다. 점프나 중력처럼 CMC 고유 API는 계속 다른 시스템이 쓸 수 있다. 여기서 단일 작성자는 `MaxWalkSpeed`, 이동 회전 플래그, 공통 가감속처럼 **캐릭터 이동 정책을 표현하는 값**의 최종 작성자가 LocomotionComponent 한 곳이라는 뜻이다. Player 입력 함수와 AIController가 각자 이 값을 덮어쓰지 않는다.

#### Intent와 Resolved Policy

`Intent`는 아직 허용 여부가 적용되지 않은 원시 요청이다. Player가 스틱을 어느 방향으로 얼마나 기울였는지, AI가 어느 방향으로 경로 이동하려는지, 요청 gait가 무엇인지가 들어간다.

`Resolved Policy`는 Definition의 기본값, 현재 Intent, 여러 제약을 합친 최종 정책이다.

```text
Raw Intent                 Constraints                    Definition
TargetGait=Sprint          Cap A=Run, Cap B=Walk          gait별 속도
RequestedRotation=Velocity Rotation override=LockOn       기본 회전/가감속
          \                    |                              /
           +---------------- Locomotion ---------------------+
                                  |
                     MaxAllowedGait=Walk
                     ResolvedGait=Walk
                     ResolvedRotation=LockOn
                     MaxWalkSpeed=WalkSpeed
                                  |
                                 CMC
```

원시 요청을 차단 시 지우지 않는 이유는 “사용자가 아직 이동하려 하지만 현재 gameplay 규칙이 출력을 막고 있다”는 사실과 “사용자가 버튼을 놓았다”는 사실이 다르기 때문이다. AnimInstance는 `InputAmount`와 허용 결과를 함께 보므로 둘을 구분할 수 있다.

#### gait와 속도

`gait`는 Walk, Run, Sprint 같은 이동 방식의 선택이다. gait는 cm/s가 아니며, Definition이 각 gait를 실제 최대 속도에 대응시킨다.

- `TargetGait`: 입력/AI가 원하는 gait다.
- `MaxAllowedGait`: 장비, 상태, 구간 같은 현재 제약들이 허용하는 최고 gait다.
- `ResolvedGait`: 두 값을 합쳐 실제로 선택된 gait다.
- `MaxWalkSpeed`: ResolvedGait를 Definition의 숫자로 변환해 CMC에 쓴 값이다.

Walk/Run/Sprint가 느림→빠름 순이라는 사실을 enum 선언 순서에만 암묵적으로 의존하지 않는다. 비교 helper의 `switch`에서 각 gait의 제한 순위를 명시한다. 향후 enum 항목이 추가돼도 비교 규칙을 함께 수정하지 않으면 검증에서 실패하도록 만든다.

#### 제약과 handle

제약은 런타임 동안 gait 상한 또는 회전 override를 제공하는 한 원인의 기여다. `handle`은 그 기여 하나를 식별하는 영수증이다.

```text
무거운 장비 제약 handle A  ── MaxAllowed=Run
늪 지형 제약 handle B      ── MaxAllowed=Walk

A 제거 후에도 B는 남음     ── 최종 Walk
B까지 제거                 ── Definition 기본 상한으로 복구
```

`FActiveGameplayEffectHandle`, `FDelegateHandle`, `FKhazanMovementConstraintHandle`, `FKhazanLocomotionIntentHandle`은 모두 이름에 handle이 있지만 서로 바꿔 쓸 수 없다.

| handle | 가리키는 대상 | 누가 해제하는가 |
| --- | --- | --- |
| `FActiveGameplayEffectHandle` | ASC에 적용된 효과 한 건 | 그 효과를 적용한 실행/소유자 |
| `FDelegateHandle` | delegate에 등록한 callback 한 건 | callback을 등록한 객체 |
| `FKhazanMovementConstraintHandle` | gait/회전 제약 한 건 | 제약을 획득한 실행/시스템 |
| `FKhazanLocomotionIntentHandle` | 현재 Pawn의 입력 의도 작성 권한 | 현재 Controller/입력 어댑터 |

`Block.Movement.Input`은 이미 GameplayEffect/tag count가 원인별 기여를 관리한다. 같은 차단 원인을 MovementConstraint에도 중복 등록하지 않는다. 이번 MovementConstraint는 gait 상한과 회전 override를 담당한다.

#### intent 권한 handle이 필요한 이유

Pawn A를 Controller 1이 조종하다가 UnPossess되고 Controller 2가 조종하기 시작할 수 있다. Controller 1의 늦은 callback이 단순 `ClearMoveInput()`을 호출하면 Controller 2의 새 입력을 지울 수 있다. LocomotionComponent는 새 Controller에 새 token을 발급하고, 모든 쓰기에서 token이 현재 것인지 확인한다.

```text
Controller 1 token = X
UnPossess / 새 BeginIntentSource
Controller 2 token = Y

Controller 1의 늦은 Clear(X) -> 거절
Controller 2의 Update(Y)     -> 허용
```

이 token은 네트워크 인증 토큰이 아니다. 같은 프로세스 안에서 이전 수명의 callback을 구분하는 capability다.

#### 회전 override의 우선순위

gait는 “더 느린 상한”을 고르면 되므로 여러 원인을 자연스럽게 합칠 수 있다. 회전 모드는 VelocityDirection, LookingDirection, LockOn 중 어느 것이 더 작다고 말할 수 없는 배타 선택이다. 그래서 회전 override에는 명시적 priority가 필요하다.

- priority가 큰 override가 이긴다.
- priority가 같으면 나중에 발급된 constraint가 이긴다.
- 이 tie-break는 결과를 결정적으로 만들기 위한 기술 규칙이다. 원작 수치나 gameplay 밸런스가 아니다.
- 해당 constraint가 해제되면 남아 있는 다음 우선순위로 다시 계산한다.
- override가 하나도 없으면 현재 Intent의 요청 회전 모드로 돌아간다.

#### AI PathFollowing

Behavior Tree의 `Move To`는 매 프레임 Actor를 직접 이동시키지 않는다. 목표로 가는 경로 요청을 만들고, `AAIController`, `UPathFollowingComponent`, `UCharacterMovementComponent`를 순서대로 사용한다.

```text
BT Move To
  -> UAITask_MoveTo
    -> AAIController::MoveTo
      -> AAIController::RequestMove
        -> UPathFollowingComponent
          -> RequestPathMove      (가속 기반 경로 모드)
             또는 RequestDirectMove (속도 직접 요청 모드)
            -> Khazan CMC gate
              -> 실제 CMC 이동
```

M2.1의 Player `AddMovementInput` gate만으로는 아래쪽 AI 경로를 막을 수 없다. M2.3에서 Controller는 경로 요청의 수명을 pause/resume하고, 프로젝트 CMC는 마지막 물리 진입점에서 다시 허용을 검사한다. 두 검사는 중복 상태 원본이 아니다. Controller 검사는 경로 작업의 진행/도착/실패 시간을 멈추고, CMC 검사는 실제 이동 우회를 막는다.

#### Pause, Resume, Abort

- `Pause`: 현재 요청 ID와 경로를 유지한 채 잠시 진행을 멈춘다. 제한 해제 시 같은 요청을 재개할 수 있다.
- `Resume`: 자신이 pause한 같은 요청 ID만 다시 진행한다.
- `Abort`: 요청을 끝내고 완료 결과를 발생시킨다. 제한 해제만으로 되살리지 않는다.
- `Request ID`: 한 번의 경로 이동 요청을 식별하는 값이다. 이전 요청의 완료 callback이 새 요청의 intent를 지우거나 재개하지 못하게 비교한다.

`Block.Movement.Input`은 이번 단계에서 가역적인 이동 제한이므로 pause를 사용한다. 이후 피격 Ability가 AI 판단 자체를 취소해야 하는 경우에는 해당 Ability/BT 정책이 abort 또는 재계획을 선택한다. 모든 차단을 무조건 abort로 바꾸지 않는다.

## 20. M2.2 — Character Definition, 이동 정책, 단일 CMC 작성자

### 20.1 이번 단계에서 실제로 만드는 것

| 파일 | 작업 | 책임 |
| --- | --- | --- |
| `Source/Khazan/Character/Locomotion/KhazanLocomotionType.h/.cpp` | config, raw intent, resolved policy, constraint 자료형 | 값의 의미와 순수 계산 helper |
| `Source/Khazan/Data/KhazanCharacterDefinition.h/.cpp` | 최소 PrimaryDataAsset 클래스 | 캐릭터 종류별 읽기 전용 이동 데이터 |
| `Source/Khazan/Character/KhazanCharacter.h/.cpp` | Definition 선택과 초기화 전달 | ASC 초기화 뒤 Definition을 Locomotion에 공급 |
| `Source/Khazan/Character/Component/KhazanLocomotionComponent.h/.cpp` | intent 권한, constraint handle, 정책 재계산, CMC 적용 | 이동 정책의 단일 작성자 |
| `Source/Khazan/Character/KhazanPlayer.h/.cpp` | 입력만 raw intent로 변환 | 장치 입력 어댑터. CMC 수치 작성 제거 |
| `Source/Khazan/Animation/KhazanAnimInstance.cpp` | resolved policy를 GT snapshot에 복사 | 관측만 수행 |

아직 `UKhazanAbilitySystemComponent`, GameplayAbility base, 공격/회피, AI 타깃 선택, Linked Anim Layer를 만들지 않는다. M2.2의 실제 소비자는 Player 이동, CMC, AnimInstance이며 이 세 경로에 필요한 것만 만든다.

### 20.2 `KhazanLocomotionType.h`의 자료형 재정리

기존 enum은 유지하되 값의 제한 순서를 명확히 하기 위해 gait 값을 명시한다. 기존 에셋에 저장된 ordinal과 같은 0/1/2이므로 의미를 바꾸는 작업은 아니다.

```cpp
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
```

- `UENUM(BlueprintType)`은 enum을 Blueprint 핀과 Details에 노출한다.
- `: uint8`은 저장 크기와 직렬화 기반형을 정한다.
- `EKhazanLocomotionIntentSource`는 디버그/수명 구분용이다. gameplay 상태 태그가 아니다.
- `VelocityDirection`은 실제 이동 방향을 향하는 모드다.
- `LookingDirection`은 Controller가 제공하는 바라보는 방향을 향하는 모드다.
- `LockOn`은 Controller/타기팅 계층이 잠금 대상을 향하도록 방향을 공급한다는 선택이다. enum을 선택하는 것만으로 타깃 탐색이 생기지는 않는다.

같은 헤더에 다음 config를 추가한다.

```cpp
USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanLocomotionConfig
{
    GENERATED_BODY()

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
```

단위는 다음과 같다.

| 필드 | 단위 | 뜻 |
| --- | --- | --- |
| Walk/Run/SprintSpeed | cm/s | 해당 gait에서 CMC가 허용할 평면 최대 속도 |
| MinAnalogWalkSpeed | cm/s | 아날로그 입력이 작아도 CMC가 사용하는 최소 보행 속도 |
| MaxAcceleration | cm/s² | 속도가 증가할 수 있는 최대 가속도 |
| BrakingDecelerationWalking | cm/s² | 걷기 모드에서 입력/요청이 없을 때 감속에 쓰는 값 |
| RotationRate | deg/s | CMC가 방향을 바꿀 때 축별 최대 회전 속도. 현재는 Yaw만 사용 |

`ClampMin`은 에디터 입력 실수를 줄이는 UI 제약이다. 저장 파일 변조나 C++ 대입까지 보장하지 않으므로 런타임 `IsValid`가 별도로 필요하다.

현재 숫자는 원작 검증값이 아니라 앞 절에서 읽은 프로젝트 이관값이다. 이 사실을 DataAsset 설명이나 주석에 남긴다. 여기서 0은 음수 방지와 초기화에 필요한 경계값이며 새 gameplay 튜닝값이 아니다.

기존 `FKhazanLocomotionIntent`에서는 `MaxAllowedGait`와 `bMovementAllowed`를 제거하고 회전 요청 이름을 명확히 바꾼다.

```cpp
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
```

`MaxAllowedGait`는 외부의 단일 setter 값이 아니라 모든 활성 constraint를 접은 결과이므로 raw intent에 있으면 안 된다. `bMovementAllowed`도 ASC tag의 투영 결과이므로 raw intent에서 분리한다.

최종 정책과 제약 요청은 다음과 같다.

```cpp
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
```

- `bMovementAllowedByTags`는 공개 gameplay 상태의 두 번째 원본이 아니다. ASC count를 빠르게 읽기 위해 Locomotion이 보관하는 read-only projection이다. 외부 setter를 만들지 않는다.
- `MaxWalkSpeed`는 관측/디버그용 계산 결과이며 CMC의 같은 필드에 적용된다.
- `bOverrideRotationMode`는 “이 제약이 회전 선택에 참여하는가”라는 자료 유효성 bool이다. 공유 상태를 대체하는 bool이 아니므로 사용해도 된다.
- `DebugName`은 로그에서 원인을 찾기 위한 이름이다. 해제 권한은 이름이 아니라 반환 handle에 있다.

### 20.3 `KhazanLocomotionType.cpp`의 순수 helper

다음 helper는 UObject를 읽거나 CMC를 수정하지 않는다. 입력 config의 유효성과 gait→속도 매핑만 담당한다.

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

float FKhazanLocomotionConfig::GetSpeedForGait(const EKhazanGait Gait) const
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

`NaN`은 Not a Number, `infinity`는 무한대다. 둘은 비교와 물리 계산을 전파해 위치를 망가뜨릴 수 있으므로 단순 음수 검사보다 먼저 막는다. `checkNoEntry()`는 정상 enum이라면 도달해서는 안 되는 분기를 개발 빌드에서 드러낸다. 뒤의 Walk 반환은 Shipping 등에서 실행을 계속해야 할 때의 안전한 fallback이다.

### 20.4 최소 Character Definition 클래스

새 폴더 `Source/Khazan/Data`에 다음 두 파일을 만든다.

`KhazanCharacterDefinition.h`:

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
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Locomotion",
        meta = (AllowPrivateAccess = "true"))
    FKhazanLocomotionConfig LocomotionConfig;
};
```

`KhazanCharacterDefinition.cpp`:

```cpp
#include "Data/KhazanCharacterDefinition.h"

const FKhazanLocomotionConfig& UKhazanCharacterDefinition::GetLocomotionConfig() const
{
    return LocomotionConfig;
}
```

- `#pragma once`는 같은 translation unit에서 헤더 중복 포함을 막는다.
- `.generated.h`는 항상 이 헤더의 마지막 include다. UHT가 UCLASS/UPROPERTY용 코드를 생성한다.
- `EditAnywhere`는 DataAsset 에셋 편집기에서 이 값을 실제로 입력할 수 있게 한다. 실행 중 수정 API는 제공하지 않고 Character/Locomotion은 const getter와 런타임 사본만 사용한다.
- `BlueprintReadOnly`는 Blueprint가 읽을 수 있으나 쓰기 setter를 자동 제공하지 않는다.
- `const FKhazanLocomotionConfig&`는 구조체를 복사하지 않는 읽기 전용 참조다. Character가 이를 Locomotion에 전달할 때 Locomotion이 자기 런타임 사본으로 한 번 복사한다.

### 20.5 Character가 Definition을 선택하고 초기화하는 위치

`KhazanCharacter.h`에 전방 선언과 property/getter를 추가한다.

```cpp
class UKhazanCharacterDefinition;

public:
    UFUNCTION(BlueprintPure, Category = "Character|Locomotion")
    UKhazanLocomotionComponent* GetLocomotionComponent() const
    {
        return LocomotionComponent;
    }

    const UKhazanCharacterDefinition* GetCharacterDefinition() const
    {
        return CharacterDefinition;
    }

private:
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Character|Definition",
        meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UKhazanCharacterDefinition> CharacterDefinition = nullptr;
```

기존 `GetLocomotionComponent()` 본문에는 `UFUNCTION(BlueprintPure)`만 추가하고 같은 getter를 두 번 만들지 않는다. 이것은 Probe BP와 향후 Ability가 상태를 변경하지 않고 공통 컴포넌트를 찾는 실제 소비를 위한 노출이다. 전방 선언은 헤더에서 포인터 타입만 알면 될 때 전체 헤더 의존을 줄인다. `TObjectPtr`는 UObject 참조를 Unreal의 GC/직렬화 시스템에 알리는 포인터 wrapper다. 이 단계는 작은 Definition을 Blueprint CDO가 직접 참조하므로 동기적으로 준비된다. 향후 큰 animation/ability soft reference의 비동기 로딩과 `State.Ready.Gameplay`는 M3 이후 실제 소비가 생길 때 설계한다.

`KhazanCharacter.cpp`에는 Definition 헤더를 include하고 `PostInitializeComponents()`의 GameWorld 블록에서 ASC ActorInfo 초기화 다음에 Locomotion 초기화를 둔다.

```cpp
#include "Data/KhazanCharacterDefinition.h"

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

순서는 다음 이유로 고정한다.

1. `Super::PostInitializeComponents()`가 엔진 컴포넌트 초기화를 끝낸다.
2. Preview/asset editor world에서는 gameplay ActorInfo와 이동 정책을 실행하지 않는다.
3. ASC의 Owner/Avatar를 먼저 연결한다.
4. Definition을 검증하고 Locomotion 런타임 config를 만든다.
5. 실제 입력/AI는 이 뒤의 Possess/BeginPlay에서 token을 얻는다.

Definition이 없을 때 CMC의 우연한 Blueprint 기본값으로 이동시키지 않고 fail closed 한다. 이때 `bHasValidMovementConfig` 같은 bool은 “데이터 준비가 성공했는가”라는 내부 유효성이지 `State.Stun` 같은 gameplay 상태의 중복 원본이 아니다.

### 20.6 LocomotionComponent의 두 handle

`KhazanLocomotionComponent.h`에서 `UKhazanLocomotionComponent` 전방 선언 다음에 두 handle과 native delegate를 둔다.

```cpp
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
```

- `FGuid`는 새 발급마다 사실상 고유한 식별값을 만든다. 0부터 증가시키는 숫자의 wrap/collision 처리를 이 초기 구현에서 별도로 만들 필요가 없다.
- `TWeakObjectPtr`는 handle이 Component의 수명을 연장하지 않는다. Actor가 파괴되면 handle의 `Owner.IsValid()`가 false가 된다.
- `friend class`는 handle 내부 ID를 LocomotionComponent만 발급/검사하게 한다. 외부 호출자는 반환받은 handle을 보관하고 돌려줄 뿐이다.
- intent handle은 Player/AI C++ 경계에서만 사용하므로 reflection이 필요 없다.
- constraint handle은 M2 시험 BP와 향후 Blueprint Ability에서도 값으로 보관할 수 있게 `USTRUCT(BlueprintType)`으로 만든다. 내부 필드는 핀으로 직접 편집하지 않는다.
- `DECLARE_MULTICAST_DELEGATE`는 여러 native C++ listener가 등록할 수 있는 알림이다. 상태 원본이 아니며 M2.3 AIController가 tag 경계 변화를 즉시 받는 데 쓴다.

### 20.7 LocomotionComponent 헤더의 공개 계약

기존 인자 없는 setter를 다음 계약으로 교체한다. 이 조각은 클래스의 `public` 영역이다.

```cpp
public:
    bool InitializeMovementConfig(const FKhazanLocomotionConfig& InConfig);

    FKhazanLocomotionIntentHandle BeginMoveIntentSource(
        UObject* Source,
        EKhazanLocomotionIntentSource SourceType);

    void EndMoveIntentSource(FKhazanLocomotionIntentHandle& Handle);
    bool IsMoveIntentHandleActive(const FKhazanLocomotionIntentHandle& Handle) const;

    bool SetMoveInputWorld(
        const FKhazanLocomotionIntentHandle& Handle,
        const FVector& Input);

    bool ClearMoveInput(const FKhazanLocomotionIntentHandle& Handle);

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

    FKhazanMovementInputPermissionChanged& OnMovementInputPermissionChanged()
    {
        return MovementInputPermissionChanged;
    }
```

모든 mutation 함수가 `bool`을 반환하는 이유는 stale handle을 조용히 현재 상태에 적용하지 않기 위해서다. `false`는 요청이 현재 token의 소유가 아니거나 config/source가 유효하지 않다는 뜻이다. 입력처럼 매 프레임 호출될 수 있는 곳에서 매번 Error 로그를 찍으면 로그 폭주가 생기므로, acquisition/초기화 실패는 로그를 남기고 개별 stale write는 반환값으로 거절한다. 두 BlueprintPure snapshot getter는 Probe가 값을 읽기 위한 복사본을 반환하며 쓰기 권한을 제공하지 않는다. C++ AnimInstance는 불필요한 복사를 피하려고 기존 const-reference getter를 사용한다.

기존 `SetMaxAllowedGait(EKhazanGait)`는 삭제한다. 단일 값 setter로는 두 원인의 상한을 독립적으로 해제할 수 없기 때문이다.

### 20.8 LocomotionComponent의 private 상태와 helper

헤더의 private 영역에 다음을 둔다.

```cpp
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
```

`MovementConfig`은 DataAsset의 런타임 snapshot이다. DataAsset을 계속 수정 가능한 전역 객체처럼 쓰지 않으면서 매 계산마다 asset을 역참조하지 않는다. `ActiveConstraints`의 key는 handle ID이며 value는 원인, 규칙, 적용 순서를 함께 보존한다.

`ActiveIntentSourceType`은 Probe/Details에서 현재 작성자가 Player인지 AI인지 확인하는 실제 진단 소비가 있으므로 reflected read-only 값으로 둔다. 허용 여부를 결정하는 gameplay 상태로 사용하지 않는다. `ApplyOrder`는 시간 초가 아니다. 같은 priority일 때 어느 요청이 나중에 들어왔는지를 결정하는 단조 증가 순번이다. 타이머도 gameplay 튜닝값도 아니다.

### 20.9 config 초기화와 intent 수명 구현

`KhazanLocomotionComponent.cpp`에 필요한 include를 정리한다.

```cpp
#include "Character/Component/KhazanLocomotionComponent.h"

#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "Character/KhazanCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"
```

config 초기화는 다음과 같다.

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

첫 줄의 `check(IsInGameThread())`는 UObject/Character/CMC 상태를 쓰는 함수가 Game Thread에서만 실행된다는 계약을 즉시 검사한다. config 교체 중 이미 Controller token이나 runtime constraint가 있다면 그 소유자가 어떤 기본값을 기준으로 했는지 불명확해지므로 거절한다. 향후 장비로 수치가 바뀌는 것은 Definition 자체 교체가 아니라 명시적 runtime modifier/constraint로 구현한다.

intent source 발급과 회수는 다음과 같다.

```cpp
FKhazanLocomotionIntentHandle UKhazanLocomotionComponent::BeginMoveIntentSource(
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

새 source를 발급하면 이전 `ActiveIntentId`가 교체되므로 이전 handle 복사본은 즉시 stale이 된다. `End`는 올바른 handle일 때만 현재 intent를 reset한다. 잘못된 handle이 들어오면 전달된 지역 handle만 reset하고 현재 source에는 손대지 않는다.

### 20.10 handle을 요구하는 raw intent setter

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

    if (!IsKnownIntentHandle(Handle) || !IsKnownRotationMode(Mode))
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

`SetMoveInputWorld`는 방향 Z를 0으로 만들어 평면 이동 의도로 저장하고 길이를 1 이하로 clamp한다. 예를 들어 카메라 기준 Forward와 Right를 더한 대각선 벡터의 길이가 1보다 커져도 더 빠르게 이동하지 않는다. `InputAmount`는 clamp된 벡터의 2D 길이이므로 0~1이다.

방향/세기만 바뀌면 CMC 속도 정책은 달라지지 않으므로 매 프레임 rebuild하지 않는다. TargetGait, 회전 모드, constraint는 최종 정책을 바꾸므로 값이 실제로 달라질 때 rebuild한다. 모든 public mutation 함수는 같은 Game Thread 계약을 검사한다.

### 20.11 gait 비교와 enum 방어 helper

`KhazanLocomotionComponent.cpp`의 include 직후, constructor와 모든 member function 정의보다 앞선 unnamed namespace에 다음을 둔다. setter가 이 helper를 먼저 볼 수 있어야 한다. 이 함수들은 이 cpp 밖으로 공개할 API가 아니다.

```cpp
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

앞 절의 setter에도 enum 방어를 포함한 최종 조건을 사용한다.

```cpp
if (!IsKnownIntentHandle(Handle) ||
    GetGaitRestrictionRank(Gait) == INDEX_NONE)
{
    return false;
}
```

회전 setter는 다음 조건을 사용한다.

```cpp
if (!IsKnownIntentHandle(Handle) || !IsKnownRotationMode(Mode))
{
    return false;
}
```

`ResetTargetGaitToDefault()`의 완전한 시작 부분은 다음과 같아야 한다.

```cpp
bool UKhazanLocomotionComponent::ResetTargetGaitToDefault(
    const FKhazanLocomotionIntentHandle& Handle)
{
    check(IsInGameThread());

    if (!IsKnownIntentHandle(Handle))
    {
        return false;
    }

    Intent.TargetGait = MovementConfig.DefaultTargetGait;
    RebuildAndApplyMovementPolicy();
    return true;
}
```

이 검사는 정상 Blueprint enum 선택을 의심해서 넣는 것이 아니다. 오래된 직렬화 데이터, 강제 cast, 향후 enum 변경이 잘못된 값을 전달했을 때 CMC까지 전파하지 않기 위한 경계다.

### 20.12 constraint 획득과 개별 해제

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

`MoveTemp`는 지역 구조체의 내용을 map으로 이동시켜 불필요한 복사를 피한다. source는 약한 참조이므로 handle/map 때문에 Ability나 Actor가 살아남지 않는다. `RemovedCount == 1`만 성공인 이유는 map key 하나가 정확히 한 원인을 가리키기 때문이다. 이미 해제한 handle의 두 번째 해제는 false이며 다른 제약에는 영향을 주지 않는다.

`MAX_uint64` 검사는 순번이 0으로 wrap되는 형식적 예외를 막는다. 실제 한 Pawn 수명에서 그 수의 제약을 획득하는 일은 없지만, 조용히 tie-break 순서가 뒤집히는 것보다 신규 획득을 거절하는 편이 안전하다.

### 20.13 모든 원인으로부터 정책을 다시 계산

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

    for (const TPair<FGuid, FActiveMovementConstraint>& Pair : ActiveConstraints)
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

매 변경 때 현재 원인 전체로부터 재계산하므로 “A가 값을 저장했다가 해제하면서 과거 값을 복구했는데 그 사이 B가 바꾼 값” 같은 복구 경쟁이 없다. 해제는 과거 snapshot을 되돌리는 동작이 아니라 현재 남은 기여를 다시 접는 동작이다.

source UObject가 비정상적으로 먼저 사라진 orphan constraint는 다음 rebuild에서 제거된다. 이것은 정상 cleanup을 대체하지 않는다. 정상 Ability/상태는 성공·취소·실패·사망에서 자기 handle을 명시적으로 해제해야 한다. orphan 제거는 버그가 영구 제한으로 남는 것을 막는 마지막 방어다.

### 20.14 정책을 CMC에 적용하는 단일 함수

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

`MaxWalkSpeed=0`으로 차단을 표현하지 않는다. 차단은 출력 gate이고 gait 속도는 이동 정책이다. 둘을 같은 숫자로 합치면 차단 해제 때 어떤 gait 속도로 돌아갈지 다시 추측해야 한다. M2.1의 Player gate와 M2.3의 AI gate가 이동 요청을 막고 CMC는 현재 gait 정책을 그대로 보존한다.

LookingDirection과 LockOn은 이 단계에서 CMC 플래그가 같지만 상위 방향 공급자가 다르다. Player의 camera/control rotation 또는 AI focus가 Looking 방향을 공급하고, Spatial/Targeting 계층이 LockOn 목표를 공급한다. 두 enum을 지금 합치면 이후 애니메이션 레이어와 타기팅 규칙이 구분할 정보를 잃는다.

### 20.15 M2.1 태그 projection과 새 policy 연결

기존 `BeginPlay()`의 ASC 구독 방식은 유지한다. callback은 ASC가 소유한 delegate **참조**에 등록해야 한다.

```cpp
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
        ASC->GetTagCount(KhazanGameplayTags::Block_Movement_Input) == 0;

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

callback 인자만 믿지 않고 현재 ASC count를 다시 읽는다. `NewOrRemoved`는 일반적으로 0↔1 경계만 알려 주며 A/B가 1↔2로 변할 때 callback이 없을 수 있다. 최종 허용은 항상 `count == 0`으로 계산한다.

delegate의 bool은 알림 순간의 공통 조회 결과다. 프로젝트의 gameplay 제한은 tag/effect 경로를 사용한다. 엔진 `SetIgnoreMoveInput`을 AI의 지속 gameplay 상태로 따로 사용하면 해제 알림이 없으므로 M2.3 pause/resume 수명과 어긋난다. 엔진 gate는 외부 안전장치로 존중하되 새 기절·연출 제한은 tag로 표현한다.

### 20.16 EndPlay 정리

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

M2.1 crash의 원인이었던 것처럼 `Super::EndPlay()`는 마지막에 한 번만 호출한다. teardown 중 delegate를 broadcast하지 않는다. AIController는 정상 UnPossess에서 먼저 자기 구독을 해제하지만, Component도 마지막에 multicast listener 목록을 비워 늦은 callback 경로를 닫는다.

### 20.17 Player는 입력 의도만 작성하도록 이관

`KhazanPlayer.h`에서는 다음을 수행한다.

1. `Character/Component/KhazanLocomotionComponent.h`를 include해 intent handle의 완전한 타입을 안다.
2. `BeginPlay()` override를 삭제한다. 기존 역할이던 `MaxWalkSpeed` 쓰기가 사라지기 때문이다.
3. `PossessedBy(AController*)` override를 추가한다.
4. `RefreshLocomotionGait()`를 `RefreshRequestedGait()`로 바꾼다.
5. Walk/Run/SprintSpeed property를 삭제한다.
6. private에 Player intent handle을 보관한다.

핵심 선언은 다음과 같다.

```cpp
#include "Character/Component/KhazanLocomotionComponent.h"

public:
    virtual void PossessedBy(AController* NewController) override;
    virtual void UnPossessed() override;

    void HandleInputMove(
        const FVector2D& MovementInput,
        const FRotator& ControlRotation);
    void HandleInputMoveReleased();

    void HandleInputSprint();
    void HandleInputSprintReleased();
    void HandleInputSprintCanceled();

private:
    void RefreshRequestedGait();

    FKhazanLocomotionIntentHandle PlayerIntentHandle;
    bool bSprintRequested = false;
```

다음 입력 설정은 Player에 남긴다.

```cpp
UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input",
    meta = (ClampMin = "0.0", ClampMax = "1.0"))
float RunInputThreshold = 0.6f;

UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input",
    meta = (ClampMin = "0.0", ClampMax = "1.0"))
float MoveInputDeadZone = 0.1f;

UPROPERTY(EditDefaultsOnly, Category = "Locomotion|Input")
bool bToggleSprint = true;
```

이 값들은 Character의 물리 능력이 아니라 Player 장치 입력을 해석하는 규칙이다. AI는 스틱 dead zone이나 toggle sprint가 없으므로 Character Definition의 공통 물리 config에 섞지 않는다. `bSprintRequested`도 공개 gameplay 상태가 아니라 현재 입력 어댑터의 요청 기억이다. 실제 허용 gait는 Locomotion policy가 결정한다.

`KhazanPlayer.cpp` 생성자에서는 다음 CMC 작성 코드를 모두 제거한다.

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

`BeginPlay()`에서 170을 쓰던 블록과 함수 정의도 삭제한다. Camera/SpringArm/Mesh transform 코드는 그대로 둔다. 이 값들은 이동 정책이 아니라 Player 표현/카메라 조립이다. CMC를 더 이상 직접 참조하지 않으므로 `GameFramework/CharacterMovementComponent.h` include도 Player cpp에서 제거한다.

빙의 때 token을 발급한다.

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

부모 `PossessedBy`를 먼저 호출해 M1 ASC ActorInfo를 현재 빙의에 맞게 갱신한다. Definition/config는 PostInitializeComponents에서 준비돼 있어야 한다. UnPossess에서는 반대로 자기 입력을 먼저 정리하고 token을 끝낸 다음 부모가 ASC 빙의 정보를 갱신하게 한다.

이동 입력 함수의 최종 형태는 다음과 같다.

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

좌표 관계는 다음과 같다.

- Enhanced Input의 2D X/Y는 장치 공간의 축이다.
- ControlRotation에서는 Pitch/Roll을 버리고 Yaw만 사용한다. 카메라가 위를 봐도 지면 이동 벡터가 위로 솟지 않는다.
- `Forward * X + Right * Y`로 월드 평면 방향을 만든다.
- Locomotion이 그 값을 clamp해 raw intent로 먼저 기록한다.
- gait 요청도 차단 여부보다 먼저 갱신한다.
- 마지막 gate를 통과한 경우에만 `AddMovementInput`으로 CMC 입력을 출력한다.

스케일 1을 유지하는 것은 현재 구현 보존이다. 아날로그 크기는 Walk/Run 선택에 쓰고 속도는 gait별 MaxWalkSpeed가 정한다. 아날로그 크기로 속도까지 연속 조절하는 설계로 바꾸려면 별도 동작 결정과 검증이 필요하다.

Released와 Sprint 함수는 다음 형태다.

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

기존 `switch (ResolvedGait)`와 `Movement->MaxWalkSpeed=...`는 완전히 사라진다. `RefreshRequestedGait()`는 이름 그대로 요청만 작성한다. 허용/제약/속도 적용은 LocomotionComponent의 rebuild가 담당한다.

### 20.18 AnimInstance는 raw intent와 resolved policy를 각각 관측

`KhazanAnimInstance.cpp::GatherGameThreadData()`에서 다음 부분을 바꾼다.

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

나머지 ActorRotation, Velocity, Acceleration, MovementMode 수집은 그대로다. `NativeThreadSafeUpdateAnimation()`과 AnyThread 계산에서는 ASC, Actor, LocomotionComponent를 새로 읽지 않는다. Game Thread snapshot 경계를 지키므로 M2.2 때문에 worker thread 안전성이 바뀌지 않는다.

`TargetGait`는 표현에서 “원래 무엇을 요청했는가”를 볼 수 있고, `ResolvedGait`는 실제 허용된 gait를 나타낸다. 현재 worker 선택은 ResolvedGait를 쓰므로 제약 중 Sprint 애니메이션이 계속 나오지 않는다.

### 20.19 에디터에서 Character Definition 생성

C++ 전체 빌드가 성공하고 새 Editor를 연 다음 수행한다. Definition을 지정하기 전 PIE를 누르면 fail-closed 로그가 나고 이동하지 않는 것이 정상이다.

1. Content Browser에서 `/Game/Data/Character` 폴더를 만든다.
2. 우클릭 → `Miscellaneous` → `Data Asset`을 선택한다.
3. 클래스 선택 창에서 `KhazanCharacterDefinition`을 선택한다.
4. 이름을 `PDA_Character_Khazan`으로 정한다.
5. Locomotion Config를 펼치고 아래 값을 넣는다.

| 필드 | 값 | 출처 분류 |
| --- | ---: | --- |
| Walk Speed | 170 cm/s | 현재 Player CDO/소스 이관값 |
| Run Speed | 470 cm/s | 현재 Player CDO/소스 이관값 |
| Sprint Speed | 600 cm/s | 현재 Player CDO/소스 이관값 |
| Min Analog Walk Speed | 15 cm/s | 현재 Player CDO 확인값 |
| Max Acceleration | 1800 cm/s² | 현재 Player CDO 확인값 |
| Braking Deceleration Walking | 1800 cm/s² | 현재 Player CDO 확인값 |
| Rotation Rate | Pitch 0, Yaw 540, Roll 0 deg/s | 현재 Player CDO 확인값 |
| Default Target Gait | Walk | 기존 raw intent 기본값 |
| Default Max Allowed Gait | Sprint | 기존 상한 기본값 |
| Default Rotation Mode | Velocity Direction | 현재 Player CDO 회전 동작 |

6. `/Game/_Art/Kazan/Character/Bluprints/BP_KhazanPlayer`를 연다.
7. `Class Defaults` → `Character|Definition` → `Character Definition`에 `PDA_Character_Khazan`을 지정한다.
8. Compile하고 error/warning을 확인한 뒤 Save한다.

기존 BP에 직렬화돼 있던 `MaxWalkSpeed=300`은 에셋 파일 안의 과거 override로 남아 보일 수 있다. 런타임 PostInitializeComponents에서 Locomotion이 Definition 정책을 최종 적용하므로 실제 기준은 Definition이다. 에디터가 오래된 native property layout을 보여 주면 Editor를 재시작하고 BP를 Compile한다. BP asset을 삭제하거나 inherited CharacterMovement component를 재생성하지 않는다.

Player의 삭제된 Walk/Run/Sprint native property는 새 DataAsset의 중첩 필드로 의미가 이동하므로 단순 `CoreRedirect` 대상이 아니다. `WalkSpeed -> LocomotionConfig.WalkSpeed` 같은 nested redirect를 임의로 만들지 않는다. 삭제 전에 CDO report로 값을 보존했고 위 표대로 Definition에 명시적으로 이관한 뒤 BP를 저장한다. 저장 후 과거 property tag가 없어지는 것은 의도한 단일 원본 이관이다.

### 20.20 M2.2 전용 시험 BP와 원인별 검사

기존 Player 생산 그래프에 테스트 로직을 계속 누적하지 않기 위해 `/Game/Test/M2/BP_M2MovementProbe`라는 빈 Actor BP를 만든다. 이 BP는 시험 맵에서만 사용한다.

변수는 다음과 같다.

| 변수 | 타입 | 용도 |
| --- | --- | --- |
| TargetCharacter | `AKhazanCharacter` Object Reference, Instance Editable | 시험할 Player 또는 Monster |
| GaitHandleA/B | `KhazanMovementConstraintHandle` | 두 gait 원인의 독립 해제 |
| RotationHandleA/B | 같은 handle 타입 | 두 회전 원인의 우선순위 검사 |
| BlockHandleA/B | `ActiveGameplayEffectHandle` | 기존 M2.1 효과 중첩 회귀 |
| BlockEffectClass | GameplayEffect Class, 기본 `GE_Test_BlockMovement` | 시험 효과 |

BeginPlay에서 `Get Player Controller(0)`을 `Enable Input`의 Player Controller 핀에 연결한다. 숫자 키는 게임 입력 설계가 아니라 시험 호출 수단이며 shipping input mapping에 넣지 않는다.

gait 시험 이벤트는 다음 순서다.

1. Player에서 Sprint 요청을 만들어 `TargetGait=Sprint`, 기본 `MaxAllowed=Sprint`, `Resolved=Sprint`를 확인한다.
2. `Acquire Movement Constraint`를 TargetCharacter의 LocomotionComponent에서 호출한다. Source는 Probe의 `Self`, request A는 `MaxAllowedGait=Run`, rotation override=false, DebugName=`Test.Gait.A`다. 반환을 GaitHandleA에 저장한다.
3. 결과는 `MaxAllowed=Run`, `Resolved=Run`, CMC MaxWalkSpeed=470이어야 한다.
4. request B를 `MaxAllowedGait=Walk`, DebugName=`Test.Gait.B`로 획득해 GaitHandleB에 저장한다.
5. 결과는 `MaxAllowed=Walk`, `Resolved=Walk`, MaxWalkSpeed=170이어야 한다.
6. A만 Release한다. B가 남으므로 여전히 Walk다.
7. B를 Release한다. 기본 상한 Sprint로 돌아가고 요청이 여전히 Sprint라면 Resolved도 Sprint다.
8. A를 두 번 Release했을 때 두 번째 반환은 false이고 B 또는 다른 제약은 변하지 않아야 한다.

회전 시험은 다음 순서다. 시험 priority 1과 2는 높고 낮음을 구분하기 위한 기술 시험값이며 원작 gameplay 수치가 아니다.

1. 요청 회전은 VelocityDirection으로 둔다.
2. A: override=true, LookingDirection, priority 1을 획득한다. 최종 LookingDirection이다.
3. B: override=true, LockOn, priority 2를 획득한다. 최종 LockOn이다.
4. B를 해제하면 A의 LookingDirection으로 돌아간다.
5. A를 해제하면 raw intent의 VelocityDirection으로 돌아간다.
6. 같은 priority로 A 다음 B를 발급하면 B가 이기고, B 해제 후 A로 돌아오는지도 확인한다.

회전 모드가 바뀔 때 CMC 플래그도 함께 본다.

| 최종 모드 | Orient Rotation to Movement | Use Controller Desired Rotation |
| --- | --- | --- |
| VelocityDirection | true | false |
| LookingDirection | false | true |
| LockOn | false | true |

LockOn 시험에서 실제 타깃을 바라보지 않아도 이 단계에서는 실패가 아니다. 이번 검사는 정책 선택과 CMC 플래그까지이며, 타깃 위치/ControlRotation 공급은 Spatial/Targeting 단계다.

#### Probe Blueprint의 정확한 노드 경로

`Event BeginPlay`의 exec를 `Enable Input`에 연결하고, `Player Controller` 핀에는 `Get Player Controller`의 Player Index 0 반환을 연결한다. 이 Actor가 키 이벤트를 받을 수 있게 하는 시험용 연결이다.

각 constraint 적용 Custom Event는 다음 공통 순서를 쓴다.

```text
Custom Event
 -> Is Valid(TargetCharacter)
 -> TargetCharacter.GetLocomotionComponent
 -> Make KhazanMovementConstraint
 -> Acquire Movement Constraint
      Target = 위 LocomotionComponent
      Source = Self(BP_M2MovementProbe)
      Constraint = Make Struct 반환값
 -> 반환 handle을 해당 Handle 변수에 Set
```

Gait A의 Make Struct 핀은 MaxAllowedGait=Run, bOverrideRotationMode=false, DebugName=`Test.Gait.A`다. Gait B는 Walk/false/`Test.Gait.B`다. 회전 A/B는 MaxAllowedGait=Sprint로 gait를 제한하지 않게 두고 bOverrideRotationMode=true, 각각의 RotationMode/RotationPriority/DebugName을 채운다.

Release Custom Event는 다음이다.

```text
Custom Event
 -> Is Valid(TargetCharacter)
 -> TargetCharacter.GetLocomotionComponent
 -> Release Movement Constraint
      Target = 위 LocomotionComponent
      Handle = 해당 Handle 변수(Get, by-reference pin)
 -> Return Value를 Print String 또는 breakpoint로 확인
```

`Handle` 핀은 값 복사 literal이 아니라 변수 reference를 연결해야 함수가 성공 뒤 변수도 reset할 수 있다. 함수 Target과 constraint Source는 다르다. Target은 정책을 소유한 LocomotionComponent이고 Source는 이 기여를 만든 Probe Actor다.

Block A/B 적용은 같은 TargetCharacter에서 `Ability System Blueprint Library -> Get Ability System Component`를 호출해 `TargetASC` 지역/변수로 사용한다.

```text
TargetASC.Make Effect Context
 -> TargetASC.Make Outgoing Spec
      Gameplay Effect Class = BlockEffectClass
      Level = 1
      Effect Context = 위 Context
 -> Is Valid Gameplay Effect Spec Handle
 -> TargetASC.Apply Gameplay Effect Spec To Self
 -> 반환 FActiveGameplayEffectHandle을 BlockHandleA 또는 B에 저장
```

Level 1은 현재 modifier 수치가 없는 구조 시험 GE에 유효한 spec level을 주기 위한 시험값이다. 원작 레벨/밸런스가 아니다. A와 B는 같은 GE class여도 `Stacking=None`이므로 서로 다른 active handle이어야 한다.

제거 이벤트는 같은 TargetASC에서 `Remove Active Gameplay Effect`를 호출한다. Handle은 A 또는 B 변수, Stacks To Remove는 -1로 해당 active effect handle의 남은 stack 전체를 제거한다. 다른 handle을 제거하지 않는다. 반환 bool과 Block tag count를 함께 확인한다.

키 입력을 쓰고 싶다면 각 Custom Event를 서로 다른 임시 키 이벤트에 연결하되, 어떤 키인지는 기능 계약이 아니다. 키 충돌이 있으면 BP 디버거에서 해당 Custom Event를 호출하거나 Probe 전용 Enhanced Input context를 사용할 수 있다. 시험이 끝난 뒤 생산 Input Mapping Context에는 이 명령을 남기지 않는다.

### 20.21 M2.2 빌드·PIE 합격표

에디터를 닫고 `KhazanEditor Win64 Development` 전체 빌드를 수행한다. Hot Reload만으로 native USTRUCT/property layout 변경을 검증하지 않는다. 새 Editor에서 Player BP와 Probe BP를 Compile/Save한 뒤 다음을 확인한다.

| 항목 | 기대 결과 |
| --- | --- |
| Definition 미지정 복제 BP | 명확한 Error 로그, 입력 token 미발급, 이동 fail closed |
| 정상 Player 시작 | runtime CMC MaxWalkSpeed=170, config의 가감속/회전률 적용 |
| 작은 입력 | Target/Resolved Walk, 속도 정책 170 |
| 임계값보다 큰 입력 | Target/Resolved Run, 속도 정책 470 |
| Sprint | Target/Resolved Sprint, 속도 정책 600 |
| Block GE 활성 | raw InputAmount는 입력 중 보존, `IsMovementInputAllowed=false`, 위치 출력 차단 |
| Block 해제 | 새 입력 event부터 같은 정책으로 이동 재개 |
| gait A/B | 한 handle 해제가 다른 상한을 풀지 않음 |
| rotation A/B | priority와 발급 순서대로 결정, 개별 해제 시 남은 값으로 재계산 |
| UnPossess | raw input 0, token 종료, 이전 callback의 setter=false |
| Repossess | 새 token으로만 쓰기 가능, 이전 token이 새 intent를 지우지 못함 |
| Anim snapshot | Target은 raw intent, MaxAllowed/Resolved/Rotation은 policy와 일치 |
| PIE 종료·재시작 | 새 crash 없음, constraint/delegate/token이 다음 PIE에 남지 않음 |

정적 검색도 함께 한다.

```text
Source/Khazan 안의 MaxWalkSpeed 쓰기
Source/Khazan 안의 bOrientRotationToMovement 쓰기
Source/Khazan 안의 bUseControllerDesiredRotation 쓰기
Source/Khazan 안의 MaxAcceleration/BrakingDecelerationWalking 쓰기
```

최종 정책 작성은 `KhazanLocomotionComponent.cpp::ApplyMovementPolicyToCharacter()` 한 곳이어야 한다. 읽기와 디버그 표시는 다른 파일에 있어도 된다. M2.2가 이 표를 통과하기 전에는 M2.3 문제를 함께 고치지 않고 먼저 이 경계를 마감한다.

## 21. M2.3 — AIController, PathFollowing, 공통 CMC gate

### 21.1 이번 단계의 책임 분리

M2.3은 세 객체를 추가/변경한다.

| 객체 | 맡는 일 | 맡지 않는 일 |
| --- | --- | --- |
| `AKhazanAIController` | 경로 request ID 추적, tag 제한 때 자기 요청 pause, 같은 요청 resume, 완료/빙의 cleanup | MaxWalkSpeed 작성, Actor 위치 직접 이동, 공격/스킬 실행 |
| `UPathFollowingComponent` | NavMesh 경로의 진행, segment 선택, 도착/실패 결과 | gameplay tag 해석 |
| `UKhazanCharacterMovementComponent` | RequestPathMove/RequestDirectMove를 raw AI intent로 기록하고 마지막 허용 gate 적용 | BT 목표 선택, pause request ID 소유 |

LocomotionComponent는 M2.2처럼 공통 policy 원본이다. AIController와 CMC는 그 결과를 서로 다른 층에서 소비한다.

```text
Block.Movement.Input count
          |
     LocomotionComponent
       /              \
permission event       current permission query
     /                       \
AIController               Khazan CMC
pause/resume request       physical request gate
```

한쪽만 구현하면 충분하지 않다.

- Controller pause만 있으면 프로젝트 코드가 직접 CMC 요청을 보낸 경우 물리 우회를 막지 못한다.
- CMC gate만 있으면 PathFollowing은 계속 시간이 흐르고 blocked/failed 판정을 내리거나 목표를 진행 중이라고 오해할 수 있다.
- 둘 다 같은 Locomotion 결과를 읽으므로 상태 원본을 이중 소유하는 것은 아니다.

### 21.2 모듈 의존성

`Khazan.Build.cs`의 `PublicDependencyModuleNames`에 다음 두 모듈을 추가한다.

```csharp
"AIModule",
"NavigationSystem"
```

최종 배열에는 기존 Core/Engine/Input/GAS/Cog 항목과 함께 들어간다.

- `AIModule`은 `AAIController`, `FAIRequestID`, `UPathFollowingComponent`, Behavior Tree/AI Task 타입의 모듈이다.
- `NavigationSystem`은 NavMesh, pathfinding query와 navigation 경로 타입을 제공한다.
- 새 exported public header가 `AAIController`를 상속하므로 이 의존성을 Private에 숨기지 않는다. 그 헤더를 include하는 다른 translation unit도 타입 정의를 알아야 한다.
- `GameplayTasks`는 이미 존재하며 BT MoveTo 내부의 `UAITask_MoveTo` 경로에 쓰인다.

모듈 목록의 쉼표를 확인한다. Build.cs는 C#이므로 C++ include 문법이나 세미콜론 목록을 쓰지 않는다.

### 21.3 프로젝트 전용 CharacterMovementComponent 생성

새 폴더 `Source/Khazan/Character/Movement`에 두 파일을 만든다.

`KhazanCharacterMovementComponent.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Character/Component/KhazanLocomotionComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KhazanCharacterMovementComponent.generated.h"

UCLASS()
class KHAZAN_API UKhazanCharacterMovementComponent
    : public UCharacterMovementComponent
{
    GENERATED_BODY()

public:
    UKhazanCharacterMovementComponent(
        const FObjectInitializer& ObjectInitializer =
            FObjectInitializer::Get());

    void SetNavigationIntentHandle(
        const FKhazanLocomotionIntentHandle& InHandle);

    void ClearNavigationIntentHandle();
    void ClearPendingNavigationMove();

    virtual void RequestPathMove(const FVector& MoveInput) override;
    virtual void RequestDirectMove(
        const FVector& MoveVelocity,
        bool bForceMaxSpeed) override;

private:
    UKhazanLocomotionComponent* GetKhazanLocomotionComponent() const;
    void RecordNavigationIntent(const FVector& NavigationVector);
    bool CanSubmitNavigationMove() const;

    FKhazanLocomotionIntentHandle NavigationIntentHandle;
};
```

`override`는 base와 정확히 같은 virtual signature인지 컴파일러가 확인하게 한다. 함수 이름이 비슷하지만 인자가 틀려 새 함수를 만들어 버리는 실수를 막는다. `NavigationIntentHandle`은 AIController가 발급받아 이 CMC에 전달하는 capability 사본이다. CMC가 독자적으로 intent source가 되지 않는다.

`KhazanCharacterMovementComponent.cpp`:

```cpp
#include "Character/Movement/KhazanCharacterMovementComponent.h"

#include "Character/KhazanCharacter.h"

UKhazanCharacterMovementComponent::UKhazanCharacterMovementComponent(
    const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    if (FNavMovementProperties* NavProperties =
        GetNavMovementProperties())
    {
        NavProperties->bUseAccelerationForPaths = true;
    }
}

void UKhazanCharacterMovementComponent::SetNavigationIntentHandle(
    const FKhazanLocomotionIntentHandle& InHandle)
{
    check(IsInGameThread());
    NavigationIntentHandle = InHandle;
}

void UKhazanCharacterMovementComponent::ClearNavigationIntentHandle()
{
    check(IsInGameThread());
    NavigationIntentHandle.Reset();
}

UKhazanLocomotionComponent*
UKhazanCharacterMovementComponent::GetKhazanLocomotionComponent() const
{
    const AKhazanCharacter* KhazanCharacter =
        Cast<AKhazanCharacter>(CharacterOwner);

    return KhazanCharacter
        ? KhazanCharacter->GetLocomotionComponent()
        : nullptr;
}

void UKhazanCharacterMovementComponent::RecordNavigationIntent(
    const FVector& NavigationVector)
{
    UKhazanLocomotionComponent* Locomotion =
        GetKhazanLocomotionComponent();

    if (!Locomotion ||
        !Locomotion->IsMoveIntentHandleActive(NavigationIntentHandle))
    {
        return;
    }

    const FVector Direction =
        NavigationVector.GetSafeNormal2D();

    if (Direction.IsNearlyZero())
    {
        Locomotion->ClearMoveInput(NavigationIntentHandle);
        return;
    }

    Locomotion->SetMoveInputWorld(
        NavigationIntentHandle,
        Direction);
}

bool UKhazanCharacterMovementComponent::CanSubmitNavigationMove() const
{
    const UKhazanLocomotionComponent* Locomotion =
        GetKhazanLocomotionComponent();

    return Locomotion &&
        Locomotion->IsMoveIntentHandleActive(NavigationIntentHandle) &&
        Locomotion->IsMovementInputAllowed();
}

void UKhazanCharacterMovementComponent::ClearPendingNavigationMove()
{
    check(IsInGameThread());

    bHasRequestedVelocity = false;
    bRequestedMoveWithMaxSpeed = false;
    RequestedVelocity = FVector::ZeroVector;

    if (CharacterOwner)
    {
        CharacterOwner->ConsumeMovementInputVector();
    }
}

void UKhazanCharacterMovementComponent::RequestPathMove(
    const FVector& MoveInput)
{
    check(IsInGameThread());

    RecordNavigationIntent(MoveInput);

    if (!CanSubmitNavigationMove())
    {
        ClearPendingNavigationMove();
        return;
    }

    Super::RequestPathMove(MoveInput);
}

void UKhazanCharacterMovementComponent::RequestDirectMove(
    const FVector& MoveVelocity,
    const bool bForceMaxSpeed)
{
    check(IsInGameThread());

    RecordNavigationIntent(MoveVelocity);

    if (!CanSubmitNavigationMove())
    {
        ClearPendingNavigationMove();
        return;
    }

    Super::RequestDirectMove(MoveVelocity, bForceMaxSpeed);
}
```

#### 왜 두 Request 함수를 모두 override하는가

UE 5.8.2의 PathFollowing은 `FNavMovementProperties::bUseAccelerationForPaths`가 true면 `RequestPathMove(CurrentMoveInput)`을 호출하고, false면 `RequestDirectMove(MoveVelocity, ...)`를 호출한다. 프로젝트 기본은 true로 두어 CMC의 MaxAcceleration과 제동을 사용하지만, 다른 Pawn/BP 설정이나 특수 이동이 direct 경로를 선택할 수 있으므로 둘 다 마지막 gate를 둔다.

5.5 이후 예전 `bUseAccelerationForPaths` 단독 property는 deprecated됐고 `GetNavMovementProperties()->bUseAccelerationForPaths`가 현재 위치다. 오래된 이름에 값을 써서 경고를 숨기지 않는다.

#### AI raw intent가 방향 크기 1인 이유

`RequestDirectMove`의 입력은 속도 벡터라 길이가 수백 cm/s일 수 있고, `RequestPathMove`의 입력은 방향/가속 입력이다. 둘을 그대로 `InputAmount`로 저장하면 Player의 0~1 계약과 달라진다. AI는 “현재 경로 이동 의도가 존재한다”를 1, 방향은 normalize된 월드 벡터로 기록한다. 실제 속도 제한은 ResolvedGait/MaxWalkSpeed가 담당한다. 원래 벡터는 normalize하지 않고 그대로 `Super`에 넘겨 엔진 pathfollowing 계산을 보존한다.

`GetSafeNormal2D()`와 `IsNearlyZero()`의 tolerance는 0 벡터 정규화 오류를 막는 엔진 수학 경계이며 gameplay 입력 임계값이 아니다.

#### ClearPendingNavigationMove가 지우는 것과 남기는 것

- `bHasRequestedVelocity`: 이번 physics update에 direct requested velocity가 존재한다는 flag.
- `bRequestedMoveWithMaxSpeed`: direct request가 max speed를 강제하는지 나타내는 flag.
- `RequestedVelocity`: 아직 소비되지 않은 경로 속도 요청.
- `ConsumeMovementInputVector`: RequestPathMove/AddInputVector 계열에 남은 입력을 비운다.

실제 `Velocity`, `LastUpdateRequestedVelocity`, Actor transform을 직접 0으로 만들지 않는다. 현재 속도는 CMC의 BrakingDecelerationWalking으로 감속한다. PathFollowing의 pause에서 `Keep`을 선택하는 이유도 순간 정지 대신 이 공통 제동을 사용하기 위해서다. 피격 Ability가 knockback이나 즉시 정지를 요구하면 그 실행이 별도 물리 정책을 명시한다.

### 21.4 모든 Character가 새 CMC를 사용하게 하는 생성자 변경

`KhazanCharacter.h`의 생성자를 다음으로 바꾼다.

```cpp
AKhazanCharacter(
    const FObjectInitializer& ObjectInitializer =
        FObjectInitializer::Get());
```

`KhazanCharacter.cpp`에서 새 헤더를 include하고 생성자 initializer list를 바꾼다.

```cpp
#include "Character/Movement/KhazanCharacterMovementComponent.h"

AKhazanCharacter::AKhazanCharacter(
    const FObjectInitializer& ObjectInitializer)
    : Super(
        ObjectInitializer.SetDefaultSubobjectClass<
            UKhazanCharacterMovementComponent>(
                ACharacter::CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;

    LocomotionComponent =
        CreateDefaultSubobject<UKhazanLocomotionComponent>(
            TEXT("LocomotionComponent"));

    AbilitySystemComponent =
        CreateDefaultSubobject<UAbilitySystemComponent>(
            TEXT("AbilitySystemComponent"));
}
```

`SetDefaultSubobjectClass`는 ACharacter가 원래 `CharacterMovementComponent`라는 이름으로 만드는 inherited default subobject의 클래스를 우리 subclass로 교체한다. 같은 이름의 두 번째 movement component를 `CreateDefaultSubobject`로 추가하면 안 된다. Character는 업데이트할 MovementComponent가 하나여야 한다.

기존 `AKhazanPlayer()`와 `AKhazanMonster()` 생성자는 인자 없는 형태를 유지해도 default argument를 통해 새 부모 생성자를 호출한다. 기존 Blueprint의 inherited component는 Editor 재실행/Compile 후 새 native subclass로 재구성된다.

### 21.5 공통 AIController 생성

새 폴더 `Source/Khazan/AI`에 두 파일을 만든다.

`KhazanAIController.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Character/Component/KhazanLocomotionComponent.h"
#include "KhazanAIController.generated.h"

class UKhazanCharacterMovementComponent;

UCLASS()
class KHAZAN_API AKhazanAIController : public AAIController
{
    GENERATED_BODY()

public:
    virtual FAIRequestID RequestMove(
        const FAIMoveRequest& MoveRequest,
        FNavPathSharedPtr Path) override;

    virtual void OnMoveCompleted(
        FAIRequestID RequestID,
        const FPathFollowingResult& Result) override;

protected:
    virtual void OnPossess(APawn* InPawn) override;
    virtual void OnUnPossess() override;

private:
    void HandleMovementInputPermissionChanged(bool bMovementAllowed);
    void SynchronizeMovementPermission();
    void PauseActiveMoveForMovementBlock(FAIRequestID RequestID);
    void ResumeMovePausedByMovementBlock();
    void ReleaseLocomotionBinding();

    TWeakObjectPtr<UKhazanLocomotionComponent> LocomotionComponent;
    TWeakObjectPtr<UKhazanCharacterMovementComponent> CharacterMovementComponent;

    FKhazanLocomotionIntentHandle AIIntentHandle;
    FDelegateHandle MovementPermissionChangedHandle;

    FAIRequestID ActiveMoveRequestId = FAIRequestID::InvalidRequest;
    FAIRequestID PausedMoveRequestId = FAIRequestID::InvalidRequest;
    bool bOwnsMovementBlockPause = false;
};
```

두 request ID는 역할이 다르다.

- `ActiveMoveRequestId`: 현재 이 Controller 경로가 진행 중이라고 추적하는 구체적 요청.
- `PausedMoveRequestId`: `Block.Movement.Input` 0→1 경계에서 이 Controller가 실제로 pause하는 데 성공한 요청.
- `bOwnsMovementBlockPause`: 요청이 이미 다른 시스템에 의해 Paused였는데 우리 것이라고 착각해 resume하지 않게 하는 소유 표식.

### 21.6 Possess에서 연결하고 UnPossess에서 역순 해제

`KhazanAIController.cpp`의 include:

```cpp
#include "AI/KhazanAIController.h"

#include "Character/KhazanCharacter.h"
#include "Character/Movement/KhazanCharacterMovementComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "LogChannels.h"
```

Possess 구현:

```cpp
void AKhazanAIController::OnPossess(APawn* InPawn)
{
    ReleaseLocomotionBinding();
    Super::OnPossess(InPawn);

    AKhazanCharacter* Character = Cast<AKhazanCharacter>(InPawn);
    UKhazanLocomotionComponent* Locomotion =
        Character ? Character->GetLocomotionComponent() : nullptr;
    UKhazanCharacterMovementComponent* Movement =
        Character
            ? Cast<UKhazanCharacterMovementComponent>(
                Character->GetCharacterMovement())
            : nullptr;

    if (!Character || !Locomotion || !Movement)
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s requires AKhazanCharacter with Khazan locomotion and movement components."),
            *GetNameSafe(this));
        return;
    }

    FKhazanLocomotionIntentHandle NewIntentHandle =
        Locomotion->BeginMoveIntentSource(
            this,
            EKhazanLocomotionIntentSource::AIController);

    if (!NewIntentHandle.IsValid())
    {
        UE_LOG(LogDefault, Error,
            TEXT("%s failed to acquire AI locomotion intent for %s."),
            *GetNameSafe(this),
            *GetNameSafe(Character));
        return;
    }

    LocomotionComponent = Locomotion;
    CharacterMovementComponent = Movement;
    AIIntentHandle = NewIntentHandle;

    Movement->SetNavigationIntentHandle(AIIntentHandle);

    MovementPermissionChangedHandle =
        Locomotion->OnMovementInputPermissionChanged().AddUObject(
            this,
            &AKhazanAIController::HandleMovementInputPermissionChanged);

    SynchronizeMovementPermission();
}
```

첫 `ReleaseLocomotionBinding()`은 정상 수명에서는 이미 비어 있어 아무 일도 하지 않지만, 비정상 재빙의에서 이전 weak/token/delegate가 남은 채 새 Pawn에 연결되는 것을 막는다. 그 다음 `Super::OnPossess`가 PathFollowing과 새 Pawn 연결을 준비한다. Component와 token을 모두 확인한 뒤에만 weak reference와 delegate를 보관한다. delegate 등록 뒤 이벤트가 언젠가 오기를 기다리지 않고 현재 허용값으로 즉시 동기화한다. 이미 block tag가 붙은 Pawn을 AI가 빙의하는 사례를 놓치지 않기 위해서다.

Definition의 `DefaultTargetGait`가 AI가 처음 요청할 gait다. 시험 Monster Definition에서는 Run을 선택한다. AIController 코드에 Monster별 속도 숫자나 `SetTargetGait(Run)`을 하드코딩하지 않는다. 이후 BT/Ability가 걷기/달리기를 선택할 때 같은 intent handle setter를 사용한다.

해제 helper와 UnPossess는 다음과 같다.

```cpp
void AKhazanAIController::ReleaseLocomotionBinding()
{
    UKhazanLocomotionComponent* Locomotion =
        LocomotionComponent.Get();
    UKhazanCharacterMovementComponent* Movement =
        CharacterMovementComponent.Get();

    if (Locomotion && MovementPermissionChangedHandle.IsValid())
    {
        Locomotion->OnMovementInputPermissionChanged().Remove(
            MovementPermissionChangedHandle);
    }

    MovementPermissionChangedHandle.Reset();

    if (Movement)
    {
        Movement->ClearPendingNavigationMove();
        Movement->ClearNavigationIntentHandle();
    }

    if (Locomotion)
    {
        Locomotion->ClearMoveInput(AIIntentHandle);
        Locomotion->EndMoveIntentSource(AIIntentHandle);
    }

    AIIntentHandle.Reset();
    ActiveMoveRequestId = FAIRequestID::InvalidRequest;
    PausedMoveRequestId = FAIRequestID::InvalidRequest;
    bOwnsMovementBlockPause = false;

    CharacterMovementComponent.Reset();
    LocomotionComponent.Reset();
}

void AKhazanAIController::OnUnPossess()
{
    ReleaseLocomotionBinding();
    Super::OnUnPossess();
}
```

delegate를 먼저 제거하므로 cleanup 도중 tag 변화가 다시 AI 이동 함수를 부르지 않는다. CMC의 pending request와 token 사본을 지우고, Locomotion raw intent를 지운 뒤 source token을 종료한다. 마지막에 부모가 PathFollowing/Pawn 빙의를 정리한다. 부모 cleanup 안에서 완료 callback이 발생해도 프로젝트 weak/token 상태는 이미 안전한 값이다.

### 21.7 Controller의 중앙 `RequestMove`에서 request ID 획득

```cpp
FAIRequestID AKhazanAIController::RequestMove(
    const FAIMoveRequest& MoveRequest,
    FNavPathSharedPtr Path)
{
    const FAIRequestID NewRequestId =
        Super::RequestMove(MoveRequest, Path);

    if (!NewRequestId.IsValid())
    {
        return NewRequestId;
    }

    ActiveMoveRequestId = NewRequestId;

    const UKhazanLocomotionComponent* Locomotion =
        LocomotionComponent.Get();

    if (!Locomotion || !Locomotion->IsMovementInputAllowed())
    {
        PauseActiveMoveForMovementBlock(NewRequestId);
    }

    return NewRequestId;
}
```

표준 `AAIController::MoveTo`는 path를 만든 다음 virtual `RequestMove`를 호출한다. Blueprint `Move To Location/Actor`, `UAITask_MoveTo`, 표준 BT `Move To`가 이 경로에 들어온다. 차단 중 새 MoveTo가 시작돼도 새 ID를 받은 직후 pause한다.

`MoveTo` 자체를 override해 실패 때 무조건 Active ID를 지우지 않는다. 엔진의 invalid MoveTo는 기존 이동을 반드시 abort하지 않으며, AI Task stacking을 위해 현재 요청이 계속될 수 있다. 실제로 PathFollowing에 들어간 유효 요청을 반환하는 `RequestMove`와 실제 종료 callback인 `OnMoveCompleted`를 수명 경계로 사용한다.

프로젝트 코드는 `GetPathFollowingComponent()->RequestMove()`를 직접 호출하지 않고 Controller API를 사용한다. 직접 호출은 request 수명 추적을 우회한다. 그래도 CMC의 마지막 gate가 차단 중 물리 이동을 막지만, 안전한 pause/resume 소유권이 없으므로 그런 호출은 아키텍처 위반으로 다룬다.

### 21.8 이동 차단 때 정확한 요청만 pause

```cpp
void AKhazanAIController::HandleMovementInputPermissionChanged(
    const bool bMovementAllowed)
{
    (void)bMovementAllowed;
    SynchronizeMovementPermission();
}

void AKhazanAIController::SynchronizeMovementPermission()
{
    const UKhazanLocomotionComponent* Locomotion =
        LocomotionComponent.Get();

    if (Locomotion && Locomotion->IsMovementInputAllowed())
    {
        ResumeMovePausedByMovementBlock();
        return;
    }

    PauseActiveMoveForMovementBlock(ActiveMoveRequestId);
}

void AKhazanAIController::PauseActiveMoveForMovementBlock(
    const FAIRequestID RequestID)
{
    if (UKhazanCharacterMovementComponent* Movement =
        CharacterMovementComponent.Get())
    {
        Movement->ClearPendingNavigationMove();
    }

    UPathFollowingComponent* PathFollowing =
        GetPathFollowingComponent();

    if (!PathFollowing || !RequestID.IsValid())
    {
        return;
    }

    if (bOwnsMovementBlockPause)
    {
        if (PausedMoveRequestId.IsEquivalent(RequestID))
        {
            return;
        }

        bOwnsMovementBlockPause = false;
        PausedMoveRequestId = FAIRequestID::InvalidRequest;
    }

    if (!RequestID.IsEquivalent(
        PathFollowing->GetCurrentRequestId()))
    {
        return;
    }

    const EPathFollowingStatus::Type Status =
        PathFollowing->GetStatus();

    if (Status == EPathFollowingStatus::Paused)
    {
        return;
    }

    if (Status != EPathFollowingStatus::Moving &&
        Status != EPathFollowingStatus::Waiting)
    {
        return;
    }

    PathFollowing->PauseMove(
        RequestID,
        EPathFollowingVelocityMode::Keep);

    if (PathFollowing->GetStatus() == EPathFollowingStatus::Paused &&
        RequestID.IsEquivalent(
            PathFollowing->GetCurrentRequestId()))
    {
        PausedMoveRequestId = RequestID;
        bOwnsMovementBlockPause = true;
    }
}
```

callback 인자 대신 현재 `IsMovementInputAllowed()`를 다시 조회하는 이유는 config/source/Pawn engine gate까지 포함한 현재 사실을 사용하기 위해서다. false 전환 때 CMC pending request를 먼저 비우고, PathFollowing의 current ID가 우리가 추적한 구체 ID와 같은 경우에만 pause한다.

이미 `Paused`라면 우리 소유로 표시하지 않는다. 예를 들어 다른 AI resource lock이 먼저 pause했다면 block 해제 시 우리가 그 요청을 resume하면 안 된다.

`EPathFollowingVelocityMode::Keep`은 PathFollowing이 현재 `Velocity`를 즉시 0으로 reset하지 않게 한다. 동시에 우리 CMC가 pending path/direct 요청을 지우므로 다음 movement update에서는 공통 braking 정책이 작동한다. `Keep`이 “계속 목표 방향으로 달려도 된다”는 뜻은 아니다.

### 21.9 자신이 pause한 같은 요청만 resume

```cpp
void AKhazanAIController::ResumeMovePausedByMovementBlock()
{
    if (!bOwnsMovementBlockPause ||
        !PausedMoveRequestId.IsValid())
    {
        return;
    }

    UPathFollowingComponent* PathFollowing =
        GetPathFollowingComponent();

    if (!PathFollowing)
    {
        bOwnsMovementBlockPause = false;
        PausedMoveRequestId = FAIRequestID::InvalidRequest;
        return;
    }

    const FAIRequestID RequestToResume = PausedMoveRequestId;

    if (!RequestToResume.IsEquivalent(
            PathFollowing->GetCurrentRequestId()) ||
        PathFollowing->GetStatus() != EPathFollowingStatus::Paused)
    {
        bOwnsMovementBlockPause = false;
        PausedMoveRequestId = FAIRequestID::InvalidRequest;
        return;
    }

    if (PathFollowing->IsResourceLocked())
    {
        bOwnsMovementBlockPause = false;
        PausedMoveRequestId = FAIRequestID::InvalidRequest;
        return;
    }

    bOwnsMovementBlockPause = false;
    PausedMoveRequestId = FAIRequestID::InvalidRequest;

    PathFollowing->ResumeMove(RequestToResume);
}
```

resume 호출 전에 소유 표식을 먼저 지운다. `ResumeMove`가 즉시 도착/실패 callback을 발생시켜 재진입하더라도 오래된 pause 상태가 남지 않는다.

AI resource가 여전히 lock돼 있으면 우리 소유만 내려놓고 resume하지 않는다. resource lock이 해제될 때 그 시스템이 자기 pause를 재개한다. 프로젝트의 독립 pause 원인은 PathFollowing의 resource lock 또는 공통 gameplay tag 수명으로 표현한다. 아무 소유 정보 없이 직접 `PauseMove`를 중첩 호출하는 방식을 새로 추가하지 않는다.

### 21.10 완료·실패·Abort의 request ID cleanup

```cpp
void AKhazanAIController::OnMoveCompleted(
    const FAIRequestID RequestID,
    const FPathFollowingResult& Result)
{
    const bool bFinishedActiveRequest =
        ActiveMoveRequestId.IsValid() &&
        RequestID.IsEquivalent(ActiveMoveRequestId);

    const bool bFinishedPausedRequest =
        PausedMoveRequestId.IsValid() &&
        RequestID.IsEquivalent(PausedMoveRequestId);

    if (bFinishedPausedRequest)
    {
        PausedMoveRequestId = FAIRequestID::InvalidRequest;
        bOwnsMovementBlockPause = false;
    }

    if (bFinishedActiveRequest)
    {
        ActiveMoveRequestId = FAIRequestID::InvalidRequest;

        if (UKhazanLocomotionComponent* Locomotion =
            LocomotionComponent.Get())
        {
            Locomotion->ClearMoveInput(AIIntentHandle);
        }

        if (UKhazanCharacterMovementComponent* Movement =
            CharacterMovementComponent.Get())
        {
            Movement->ClearPendingNavigationMove();
        }
    }

    Super::OnMoveCompleted(RequestID, Result);
}
```

Success, Blocked, OffPath, Aborted, Invalid 등 종료 이유와 관계없이 **현재 active ID가 실제로 끝났을 때** raw intent를 지운다. 이전 request의 늦은 callback ID가 새 Active ID와 다르면 새 intent를 지우지 않는다. 부모 broadcast 전에 프로젝트 상태를 정리하므로 BT/Blueprint 완료 listener가 새 판단을 시작할 때 이전 이동 intent가 남아 있지 않는다.

현재 프로젝트 분기는 `Result`의 세부 code로 갈라지지 않지만 마지막 `Super::OnMoveCompleted(RequestID, Result)`에 원본을 그대로 전달하므로 인자는 실제로 사용된다. 이후 전투 AI가 실패 이유별 재계획을 할 때 이 결과를 추가로 소비할 수 있다. M2.3에서 목표 선택 정책을 미리 넣지 않는다.

### 21.11 Monster의 기본 AIController 연결

`KhazanMonster.cpp`에 AIController 헤더를 include하고 생성자를 다음처럼 만든다.

```cpp
#include "Character/KhazanMonster.h"

#include "AI/KhazanAIController.h"

AKhazanMonster::AKhazanMonster()
{
    AIControllerClass = AKhazanAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
}
```

- `AIControllerClass`는 이 Pawn을 자동 생성·빙의할 Controller 클래스다.
- `PlacedInWorldOrSpawned`는 레벨에 미리 둔 Monster와 런타임 Spawn Monster 모두 기본 AIController를 얻는 선택이다.
- 이 설정은 Behavior Tree를 선택하거나 실행하지 않는다. 공통 이동 접속만 제공한다.
- Monster 종류별 BT, 타깃, 패턴 선택은 AI 데이터/상위 판단 책임이다.

현재 확인한 수입 Swordsman와 Archer BP는 `AActor` 부모다. 이 에셋을 M2.3에서 `AKhazanMonster`로 강제 Reparent하지 않는다. 기존 component hierarchy, construction script, transform, collision이 Character 계약과 다를 수 있기 때문이다. 먼저 작은 gameplay shell로 이동 수직 경로를 검증한 다음, 후속 단계에서 원본 시각 component를 조립하거나 안전한 Character 파생 에셋으로 이관한다.

### 21.12 M2.3 C++ 적용 뒤 첫 전체 빌드와 CDO 확인

1. Editor를 완전히 닫는다.
2. `KhazanEditor Win64 Development` 전체 빌드를 수행한다.
3. UHT error가 있으면 첫 번째 error부터 해결한다. 뒤의 generated header 오류를 별개 문제로 쫓지 않는다.
4. 새 Editor를 연다.
5. `BP_KhazanPlayer`를 열어 Compile한다.
6. inherited `CharacterMovement`의 클래스가 `KhazanCharacterMovementComponent`인지 Details/디버거에서 확인한다.
7. Player Definition이 여전히 지정돼 있는지 확인한다.
8. Player만 둔 PIE에서 Walk/Run/Sprint, Block GE, Stop 전이가 M2.2와 같은지 먼저 본다.

native default subobject class 변경은 Live Coding만으로 기존 Blueprint CDO에 안정적으로 반영됐다고 가정하지 않는다. 컴파일 뒤 inherited component가 여전히 base `CharacterMovementComponent`라면 Editor를 닫고 전체 빌드/재실행부터 다시 확인한다. Blueprint에서 inherited component를 삭제하거나 같은 이름의 component를 추가하지 않는다.

### 21.13 시험용 Monster Definition과 gameplay shell

`/Game/Data/Character/PDA_Character_M2TestMonster`를 `KhazanCharacterDefinition`으로 만든다. M2.2 Player 값과 같은 이동 수치를 넣고 다음 기본 선택만 다르게 한다.

| 필드 | 시험값 | 이유 |
| --- | --- | --- |
| Default Target Gait | Run | AI path가 입력 event 없이 Definition 기본 요청 gait를 사용하는지 확인 |
| Default Max Allowed Gait | Sprint | constraint가 없을 때 Run 요청을 막지 않음 |
| Default Rotation Mode | VelocityDirection | path 방향 회전의 최소 공통 경로 확인 |

이 Monster 수치는 원작 Swordsman 검증값이 아니다. Player/AI가 같은 CMC policy를 통과하는지만 비교하기 위한 임시 시험 데이터다.

다음으로 `/Game/Test/M2/BP_KhazanMonster_M2Test`를 `AKhazanMonster` 부모로 만든다.

1. Class Defaults의 Character Definition에 `PDA_Character_M2TestMonster`를 지정한다.
2. Auto Possess AI는 `Placed in World or Spawned`인지 확인한다.
3. AI Controller Class는 우선 native `KhazanAIController`인지 확인한다. 아래 시험 BP를 만든 뒤 그 클래스로 바꾼다.
4. capsule만으로 path test가 가능하다. 시각 확인이 필요하면 기존 `SK_EN_Swordsman_U01_L01` 같은 Skeletal Mesh를 inherited Mesh에 지정하되 transform은 수입 Actor BP의 실제 component 값을 복사하거나 별도 Art 이관에서 맞춘다. 임의 capsule/mesh 정렬 숫자를 gameplay 근거처럼 추가하지 않는다.

### 21.14 Blackboard와 Behavior Tree 시험 자산

M2.3은 타깃 탐색 AI를 구현하는 단계가 아니므로 시험 자산을 `/Game/Test/M2`에 격리한다.

#### Blackboard

`BB_M2_MovementTest`를 만들고 key 하나를 추가한다.

| Key Name | Key Type | Base Class |
| --- | --- | --- |
| `TargetActor` | Object | Actor |

Blackboard는 Behavior Tree가 읽고 쓰는 작은 공유 메모리다. `TargetActor`는 gameplay tag가 아니며 “어디로 갈 것인가”라는 AI 판단 데이터다.

#### Behavior Tree

`BT_M2_MovementTest`를 만들고 Blackboard Asset에 위 자산을 지정한다.

```text
Root
  -> Sequence
       -> Move To (Blackboard Key = TargetActor)
```

- Root 바로 아래에는 Composite인 Sequence를 둔다.
- Move To의 `Observe Blackboard Value`를 켜면 목표가 바뀔 때 새 요청으로 갱신되는 경로를 시험할 수 있다.
- 움직이는 Player를 대상으로 하면 `Track Moving Goal`을 사용한다.
- Acceptance Radius와 pathfinding 옵션은 첫 구조 시험에서 엔진 기본값을 사용한다. 그 값은 원작 수치가 아니며 최종 전투 거리로 채택하지 않는다.
- 공격/회피 Task나 `Simple Move To`를 추가하지 않는다.

#### 시험 AIController BP

`BP_KhazanAIController_M2Test`를 `AKhazanAIController` 부모로 만든다. Blueprint에 표시되는 `Event On Possess`/`Receive Possess`에서 다음 순서로 연결한다.

```text
Event On Possess
  -> Use Blackboard(BB_M2_MovementTest)
  -> 반환 BlackboardComponent의 Set Value as Object
       Key Name = TargetActor
       Object Value = Get Player Character(0)
  -> Run Behavior Tree(BT_M2_MovementTest)
```

`Use Blackboard` 성공 exec 뒤에 Set/Run을 둔다. `Get Player Character(0)`이 null이면 Run하지 않고 시험 로그를 남기게 branch를 둘 수 있다. 이 Player 획득은 시험 harness의 편의이며 생산 타깃 선정 로직이 아니다.

`BP_KhazanMonster_M2Test`의 AI Controller Class를 이 시험 Controller BP로 바꾼다.

### 21.15 NavMesh 시험 맵

`/Game/Test/M2/L_M2_Movement` 맵을 만들거나 기존 DevMap의 격리된 평면에서 시험한다.

1. 충돌 가능한 바닥을 둔다.
2. `NavMeshBoundsVolume`을 바닥과 이동 목표 영역이 들어오도록 배치한다.
3. Editor의 `P` 키로 초록색 navigable 영역을 확인한다.
4. PlayerStart와 `BP_KhazanMonster_M2Test`를 초록 영역 안에 서로 떨어뜨려 둔다.
5. `BP_M2MovementProbe`를 두고 TargetCharacter를 Monster로 지정한다.
6. Build 메뉴에서 Navigation을 갱신한다.

NavMesh는 월드의 어느 위치를 AI가 걸을 수 있는지 표현하는 탐색 데이터다. 초록 영역 밖 목표는 경로가 없거나 partial path가 된다. M2.3에서 NavMesh 크기나 Acceptance Radius를 원작 전투 수치로 확정하지 않는다.

### 21.16 AI AnimInstance snapshot 진단 자산

AI raw intent가 Main AnimInstance의 기존 GT snapshot 계약으로 들어오는지도 확인한다. Swordsman skeleton을 사용하는 최소 `ABP_M2_SwordsmanProbe`를 `/Game/Test/M2`에 만든다.

1. Animation Blueprint 생성에서 Swordsman mesh의 Skeleton을 선택한다.
2. Parent Class를 `KhazanAnimInstance`로 선택한다.
3. AnimGraph는 `Ref Pose -> Output Pose`만 연결한다.
4. Monster 시험 BP의 Mesh Animation Class에 이를 지정한다.

이 ABP는 걷기 포즈를 만드는 생산 레이어가 아니다. C++ 부모의 `InputAmount`, `bHasMovementInput`, `ResolvedGait`, `RotationMode`를 runtime debug filter에서 보기 위한 진단 자산이다. M4 전에는 수입 적의 locomotion graph를 여기로 복사하지 않는다.

기대 snapshot은 다음과 같다.

| 상황 | Raw InputAmount | bMovementAllowed | bHasMovementInput | ResolvedGait |
| --- | ---: | --- | --- | --- |
| path 이동 중 | 1 | true | true | Definition/constraint 결과, 기본 Run |
| 같은 request가 tag로 pause | 마지막 방향과 1 보존 | false | false | gait policy는 보존 |
| 도착/실패/abort | 0 | 허용 상태에 따름 | false | 기본/현재 policy |

Anim worker가 AIController나 ASC를 직접 cast/조회하는 노드는 만들지 않는다.

### 21.17 정상 이동의 정확한 호출 순서

Rider breakpoint를 다음 위치에 둔다.

1. `AKhazanAIController::RequestMove`
2. `UKhazanCharacterMovementComponent::RequestPathMove`
3. `UKhazanLocomotionComponent::SetMoveInputWorld`
4. `UKhazanLocomotionComponent::ApplyMovementPolicyToCharacter`
5. `AKhazanAIController::OnMoveCompleted`

일반 시험의 기대 순서는 다음과 같다.

```text
BT Move To 시작
-> RequestMove에서 유효한 concrete FAIRequestID 획득
-> PathFollowing status Moving 또는 Waiting
-> bUseAccelerationForPaths=true이므로 RequestPathMove
-> CMC가 방향을 AI raw intent로 기록
-> permission true이므로 Super::RequestPathMove
-> CMC가 Definition의 Run MaxWalkSpeed/가속/제동으로 실제 이동
-> 목표 도착
-> OnMoveCompleted(Success, 같은 request ID)
-> raw input 0, active ID invalid
-> BT Move To 성공
```

`RequestPathMove`는 path segment를 따라 여러 frame 반복 호출될 수 있다. `RequestMove`는 한 이동 요청이 시작될 때 ID를 얻는 경계다. 두 함수 호출 횟수가 같아야 한다고 검사하지 않는다.

### 21.18 A/B Block 효과의 pause/resume 시험

기존 `/Game/Test/GE_Test_BlockMovement`를 Monster ASC에 적용한다. Probe BP에서 Player M2.1과 같은 MakeEffectContext → MakeOutgoingSpec → ApplyGameplayEffectSpecToSelf 경로를 TargetCharacter의 ASC에 사용하고 반환 handle A/B를 따로 저장한다.

반드시 Monster가 실제로 이동 중일 때 다음 순서로 시험한다.

| 순서 | Tag count | Path 상태 | raw AI intent | 실제 결과 |
| --- | ---: | --- | --- | --- |
| 기준 | 0 | Moving | 방향, Amount 1 | 이동 |
| A 적용 | 1 | Paused | 보존 | pending request 제거 후 CMC 제동 |
| B 적용 | 2 | Paused | 보존 | 그대로 정지 |
| A만 제거 | 1 | Paused | 보존 | 재개하지 않음 |
| B 제거 | 0 | Moving으로 재개 | 다음 path update에서 갱신 | 같은 request ID로 이동 재개 |

확인할 세부 사항:

1. A의 0→1에서 Locomotion callback이 한 번 발생한다.
2. AIController가 현재 concrete ID를 `PauseMove(..., Keep)`에 전달한다.
3. `bOwnsMovementBlockPause=true`, PausedMoveRequestId가 current ID와 같다.
4. CMC `RequestedVelocity`와 pending input은 지워지지만 실제 Velocity를 코드로 0으로 쓰지 않는다.
5. B의 1→2와 A 제거의 2→1에서는 `NewOrRemoved` callback이 없어도 count가 0이 아니므로 계속 pause다.
6. B 제거의 1→0에서만 resume한다.
7. resume 뒤 ActiveMoveRequestId와 PathFollowing current ID가 원래 요청과 같다.
8. Pause 자체는 OnMoveCompleted가 아니므로 raw intent가 지워지지 않는다.
9. 실제 Velocity가 줄어드는 시간은 현재 속도, frame step, 바닥/마찰에 좌우된다. 임의 고정 시간을 합격 조건으로 두지 않는다.

Probe에서 AI를 조작할 때는 `TargetCharacter -> Get Controller -> Cast to KhazanAIController` 순서로 현재 빙의 Controller를 구한다. cast 결과를 시작 전에 변수 `TargetAIController`로 저장해도 되지만 매 PIE의 Controller를 새로 얻어야 하며 이전 PIE reference를 재사용하지 않는다.

- 목표 교체: `TargetAIController -> Get Blackboard Component -> Set Value as Object`, Key Name=`TargetActor`, Object Value=다른 유효 Actor. BT Move To의 Observe Blackboard Value가 새 request를 만든다.
- Abort: `TargetAIController -> Stop Movement`. 이는 현재 path request를 abort하고 OnMoveCompleted를 발생시키는 시험이다.
- 상태 관측: `TargetAIController -> Get Move Status` 또는 Gameplay Debugger/중단점에서 Moving/Paused/Idle과 current request ID를 본다. 화면상 위치만으로 pause 소유권을 판정하지 않는다.
- 효과 적용/제거: 앞 절의 TargetASC 경로를 그대로 사용하되 TargetCharacter가 Monster다. Player ASC에 효과를 잘못 적용한 뒤 AI가 안 멈춘다고 판정하지 않는다.

### 21.19 차단 중 새 MoveTo

tag count 1인 상태에서 Blackboard의 TargetActor를 다른 Actor로 바꾸거나 새 `Move To Location`을 요청한다.

1. 기존 요청이 끝나면 그 ID의 OnMoveCompleted가 기존 상태만 정리한다.
2. 새 `RequestMove`가 새 ID를 반환한다.
3. 현재 permission이 false이므로 새 ID도 즉시 pause한다.
4. 이전 PausedMoveRequestId를 새 ID에 잘못 재사용하지 않는다.
5. tag count가 0이 되면 새 ID만 resume한다.

이 시험은 “태그 이벤트가 이미 과거에 발생했으므로 새 요청이 몰래 움직이는” 누락을 잡는다. 그래서 Controller는 tag callback뿐 아니라 `RequestMove` 직후 현재 permission도 조회한다.

새 요청이 이미 차단된 상태에서 첫 PathFollowing update 전에 pause되면 CMC가 아직 방향 벡터를 받지 않았으므로 raw `InputAmount`가 0일 수 있다. 목표가 있다는 이유로 존재하지 않는 이동 방향을 만들어 1로 쓰지 않는다. 제한 해제 후 첫 RequestPathMove/RequestDirectMove에서 실제 방향과 Amount 1이 기록된다. 반대로 이동 중 차단된 요청은 마지막으로 받은 방향/Amount 1을 보존한다.

### 21.20 Abort, 실패, AlreadyAtGoal

#### Block 중 Abort

이동을 tag로 pause한 상태에서 Behavior Tree를 중단하거나 AIController의 `Stop Movement`로 현재 요청을 abort한다.

- OnMoveCompleted의 Result는 Aborted 계열이 된다.
- Active/Paused request ID와 pause 소유 표식이 모두 정리된다.
- raw InputAmount가 0이 된다.
- 그 뒤 Block 효과를 제거해도 종료된 요청을 resume하지 않는다.

#### 도달 불가능한 목표

시험에서 `Allow Partial Path`를 끄고 NavMesh 밖의 도달 불가능한 목표를 준다. 엔진의 실제 결과가 Failed/Invalid/Blocked 중 어떤 세부 code인지 기록한다. 결과 이름을 미리 강제하지 않고 다음 공통 조건을 본다.

- OnMoveCompleted 또는 요청 실패 경계 뒤 current active ID가 남지 않는다.
- raw input이 0이다.
- 다음 정상 MoveTo가 새 ID로 시작한다.
- 실패한 요청을 tag 해제 callback이 재개하지 않는다.

#### AlreadyAtGoal

AI의 현재 위치를 목표로 `Move To Location`을 요청한다. `AAIController::MoveTo`는 `AlreadyAtGoal`을 반환할 수 있고 지속 path 이동을 만들지 않는다.

- 새 raw movement intent가 1로 고정되지 않는다.
- 진행 중인 다른 유효 요청을 단순 invalid 요청 하나 때문에 임의로 잊지 않는다.
- BT task가 즉시 성공하는 경우에도 다음 판단에서 stale pause ID가 없다.

### 21.21 다른 pause 원인과 request 소유권

세 가지 경우를 구분한다.

1. **다른 시스템이 먼저 Paused**: Block tag가 추가돼도 `Status==Paused`이므로 `bOwnsMovementBlockPause`를 얻지 않는다. Block 해제 때 resume하지 않는다.
2. **Block이 먼저 pause한 뒤 AI resource lock 추가**: Block 해제 때 `IsResourceLocked()`가 true이므로 resume하지 않고 자기 소유만 내려놓는다. resource unlock이 재개한다.
3. **Block이 pause한 요청이 abort/교체됨**: 완료 ID 비교로 pause 소유를 지운다. 새 요청 ID에 이전 resume를 보내지 않는다.

독립 시스템이 원인 정보 없이 `PathFollowingComponent->PauseMove()`를 직접 여러 번 중첩하는 방식은 count/handle이 없으므로 안전하게 합칠 수 없다. 새 프로젝트 코드는 gameplay 이동 제한은 ASC tag count, AI task resource 경쟁은 AI resource lock으로 표현한다.

### 21.22 RequestPathMove와 RequestDirectMove 두 경로 검증

첫 시험에서는 새 CMC 생성자가 `Movement Capabilities / Use Acceleration for Paths=true`로 두므로 `RequestPathMove` breakpoint가 와야 한다.

두 번째 시험에서는 **시험 Monster BP에서만** inherited CharacterMovement의 `Nav Movement -> Nav Movement Properties -> Use Acceleration for Paths`를 false로 override하고 Compile한다. 같은 BT Move To를 다시 실행하면 `RequestDirectMove` breakpoint가 와야 한다.

두 모드 모두 다음이 같아야 한다.

- 정상일 때 raw 방향/Amount 1과 실제 이동이 생긴다.
- Block tag가 있으면 raw 의도는 기록되지만 Super request는 호출되지 않는다.
- pending direct velocity 또는 path input이 남지 않는다.
- 효과 A/B 제거 순서와 request ID resume 규칙이 같다.

시험이 끝나면 override를 제거해 Definition/새 CMC의 기본 true로 되돌린다. true/false는 엔진 구동 방식 선택이며 원작 gameplay 수치가 아니다.

### 21.23 빙의 교체와 PIE 종료

이동 중, 그리고 Block으로 pause된 상태에서 각각 다음을 시험한다.

1. AIController가 Monster를 UnPossess한다.
2. 기존 Controller의 delegate handle, pending request, AI intent token, Active/Paused ID가 정리되는지 본다.
3. 같은 Pawn을 다시 AIController가 Possess한다.
4. 새 intent token이 발급된다.
5. 이전 token 사본으로 `ClearMoveInput`/`SetMoveInputWorld`를 호출하면 false이고 새 intent는 변하지 않아야 한다.
6. 새 MoveTo는 새 request ID로 동작한다.
7. Block 효과가 남아 있었다면 새 Controller의 `SynchronizeMovementPermission()`이 즉시 false를 읽고 새 요청을 pause한다.
8. PIE를 종료하고 다시 시작한다. 이전 delegate/request/constraint가 새 world에 호출되지 않고 crash가 없어야 한다.

### 21.24 M2.3 전체 합격표

| 범주 | 합격 조건 |
| --- | --- |
| 클래스 | Player와 Monster runtime CMC가 `UKhazanCharacterMovementComponent` |
| 공통 데이터 | Player/Monster 모두 Definition → Locomotion → CMC 경로 사용 |
| BT 연결 | 표준 BT Move To가 Controller `RequestMove`를 지나 concrete ID 획득 |
| Path mode | 가속 mode는 RequestPathMove, direct mode는 RequestDirectMove를 실제 통과 |
| 정상 이동 | AI raw Amount 1, ResolvedGait 기본 Run, config 속도/가감속 적용 |
| Block A/B | 0→1 pause, count가 남으면 정지, 1→0에서 같은 ID만 resume |
| 물리 | pending 요청은 제거, Velocity를 직접 0으로 덮지 않고 CMC 제동 |
| 새 요청 | 차단 중 생성한 새 ID도 즉시 pause, 이전 ID callback이 새 intent에 영향 없음 |
| Abort | 종료 뒤 tag 해제로 되살아나지 않음 |
| 실패/도착 | raw intent와 active/pause ID 정리, 다음 요청 가능 |
| 다른 pause | 먼저 pause한 요청을 자기 것으로 claim/resume하지 않음 |
| 빙의 | old token/delegate/request가 새 Pawn/새 Controller 상태를 변경하지 않음 |
| Anim | GT snapshot에서 raw intent와 허용/Resolved policy가 예상대로 보임 |
| Player 회귀 | 기존 IA_Move, Walk/Run/Sprint, Block, Stop, PIE 종료 정상 |

### 21.25 이번 두 단계가 끝난 뒤에도 남는 범위

M2.2와 M2.3을 위 절차로 적용·빌드·PIE 검증하면 두 소단계는 완료할 수 있다. 그러나 **M2 전체 완료는 아직 아니다.** M2.4에서 Player/AI를 함께 둔 장시간 통합, 겹친 effect/constraint, 회전/Stop, 저프레임, possess/destroy, 반복 PIE를 한 묶음으로 회귀 확인한 뒤 M3 공통 Ability 요청 계층으로 이동한다.

이번 설계는 다음 ARCH 계약을 구체화하며 바꾸지 않는다.

- ARCH-04: Locomotion이 intent/제약을 policy로 계산하고 CMC에 적용한다.
- ARCH-05: effect, delegate, constraint, intent의 handle을 원인별로 구분한다.
- ARCH-08: Player와 AI는 같은 Locomotion/CMC 정책을 쓰며 BT는 명령만 낸다.
- ARCH-09: Pawn/request/token ID와 정상·취소·실패·EndPlay cleanup을 구분한다.
- ARCH-10: UObject/ASC/CMC 쓰기는 Game Thread에서만 한다.
- ARCH-16/17: Definition은 읽기 전용이며 config 준비 뒤 입력/AI를 연결한다.

새 공격 Ability나 Status.Stun 태그를 이번 코드에 미리 넣지 않는다. M3에서는 이 이동 계약을 소비하는 최소 Ability 수직 기능을 만들고, Ability/Effect가 자기 movement constraint/effect handle을 성공·취소·실패에서 회수하는 것을 실제로 검증한다.

### 21.26 흔한 실패와 이번 단계의 경계

| 증상 | 먼저 확인할 것 | 이유 |
| --- | --- | --- |
| `*.generated.h` 또는 UHT 연쇄 오류 | 첫 UHT 오류, generated include가 마지막인지, USTRUCT/UCLASS macro 위치 | 뒤 오류는 첫 reflection 문법 오류의 결과인 경우가 많음 |
| `AAIController`/PathFollowing link 오류 | Build.cs의 AIModule/NavigationSystem, public header include | 헤더 인식과 linker module 의존은 별도 |
| Player Definition 로그 후 이동 불가 | Player BP Class Defaults의 CharacterDefinition | fail closed가 작동한 것 |
| runtime CMC가 base class | Editor 완전 종료 전체 빌드, ObjectInitializer의 정확한 subobject name, BP Compile | Live Coding만으로 default subobject class가 교체되지 않을 수 있음 |
| BT Move To 즉시 실패 | AI possession, Blackboard TargetActor, NavMesh 초록 영역, 목표 유효성 | policy 이전에 경로가 생성되지 않은 상태 |
| tag 중에도 AI가 한 frame 밀림 | tag callback에서 CMC pending direct/path input을 모두 비웠는지 | Controller pause만으로 이전 physics 요청이 남을 수 있음 |
| tag 해제 뒤 영구 pause | bOwns flag, Paused ID/current ID, resource lock 상태 | 다른 pause를 자기 것으로 해제하면 안 되며 ID 불일치도 resume 금지 |
| abort 뒤 다시 움직임 | OnMoveCompleted에서 Active/Paused ID를 같은 request 기준으로 정리했는지 | 해제 callback이 종료된 ID를 되살린 증상 |
| Anim `InputAmount=1`인데 bHasMovementInput=false | Block 상태라면 정상 | raw 의도와 허용된 출력이 분리된 것 |
| MaxWalkSpeed가 300/600으로 되돌아감 | 프로젝트 전체 CMC 쓰기 검색, BP construction script | 단일 작성자 밖의 과거 writer가 남은 것 |

이번 Block 계약은 일반 path/input 이동을 막는다. 중력, 낙하, 외부 impulse, knockback, montage root motion, Motion Warping을 자동 중단하지 않는다. 이 출력들은 서로 다른 공간/Ability 수명이며 M3/M6의 명시적 정책으로 연결한다.

현재 목표는 standalone 싱글플레이 수직 검증이다. 네트워크에서 client predicted input token을 사용하려면 `PossessedBy`만으로는 client 수명이 충분하지 않으며 `PawnClientRestart`/Controller replication/ASC prediction 계약을 별도로 설계해야 한다. 이번에 사용하지 않는 멀티플레이 경로를 완료했다고 기록하지 않는다.

Custom Nav Link를 통과하는 중 pause, CrowdFollowing, root-motion 기반 AI 이동은 일반 PathFollowing 시험 뒤 각 기능을 실제 도입할 때 별도 회귀가 필요하다. 현재 두 Request override와 request ID 계약을 건너뛰어 우회 구현하지 않는다.


<a id="m2-2-current-source-walkthrough-20260909"></a>

## 22. 2026-09-09 — M2.2 현재 소스 기준 순서형 실습판 추가

- 사용자가 20절을 따라 `KhazanLocomotionType.h`를 수정하던 중 문서의 가시성과 개념 설명이 부족하다고 보고했다. 설계 계약은 유지하고, 실제 현재 소스에서 그대로 이어갈 전용 실습판을 [CHARACTER_TAG_ABILITY_M2_2_WALKTHROUGH.md](CHARACTER_TAG_ABILITY_M2_2_WALKTHROUGH.md)로 분리했다.
- 실습판은 config/raw intent/constraint/resolved policy를 나누는 이유, 모든 삭제·추가 변수의 작성자·소비자·갱신·Reset, handle/token/projection/snapshot/fail-closed 용어, A~K 구현 순서, 예상 중간 컴파일 오류, 에디터 설정과 합격표를 포함한다.
- 현재 헤더 대조에서 `FKhazanLocomotionIntent::bMovementAllowed`가 아직 남아 있고 `FKhazanLocomotionConfig::MinAnalogWalkSpeed`가 `170.f`로 입력된 것을 확인했다. 전자는 policy로 이관하며 삭제하고, 후자는 현재 Player CDO 이관값 `15.f`로 정정한다. `15.f` 역시 원작 metadata 직접 확인값은 아니다.
- 기존 20.11의 `ResetTargetGaitToDefault()` 예시 사이 표현 차이는 실습판에서 “이미 기본값이면 true를 반환하고 rebuild 생략”으로 통일했다. `KhazanCharacter.cpp`의 새 `LogDefault` 로그에 필요한 `LogChannels.h` include도 명시했다.
- 이 추가는 문서 정리와 읽기 전용 소스 대조다. 사용자가 수정 중인 C++·BP·asset은 건드리지 않았고, 중간 빌드 오류는 M2.2 실패로 판정하지 않았다. 실습판 K절의 실제 빌드·PIE 검증 전에는 M2.2 완료가 아니다.


## 23. 2026-09-11 — §20.19 정정: 기존 AssetManager 기반 Character Definition 준비

- 앞선 20.19의 `PDA_Character_Khazan` hard-reference 절차는 적용 전 철회한다. 프로젝트의 `UKhazanAssetData`/`PDA_AssetData`가 이미 GameplayTag name → soft object path와 preload label을 소유하며, v2 ARCH-16/17도 기존 AssetManager 준비 경로를 요구한다.
- `UKhazanAssetData`만 Engine Primary Asset type으로 scan한다. `UKhazanCharacterDefinition`은 현재 직접 PrimaryAssetId/bundle 조회 소비가 없으므로 `UDataAsset` payload로 바꾸고 에셋 이름도 `DA_Character_Khazan`으로 사용한다. 이를 `PDA_AssetData`의 entry로 등록한다.
- Player/Monster 공통 선택자는 `CharacterDefinitionAssetName` GameplayTag다. Player entry/key는 `AssetData.CharacterDefinition.Khazan`, path는 `/Game/Data/Character/DA_Character_Khazan`, label은 `AssetLabel.Preload`로 한다. `AssetData.*` key는 asset lookup용이며 ASC state tag가 아니다.
- Character에는 class-default key와 transient loaded Definition pointer를 구분한다. GameInstance preload 후 `PostInitializeComponents()`가 manager에서 타입 검증된 Definition을 얻고 Locomotion config를 초기화한다. LocomotionComponent에는 값 사본만 전달한다.
- 현재 manager에는 lookup 실패 null 역참조, `PreSave()`에만 의존하는 runtime index, label load의 중복 cache key와 release 비대칭이 남아 있다. 새 필수 Definition을 연결하기 전에 이 경계를 보강한다. 새 순서는 AssetManager 안전성/대칭 → Definition의 UDataAsset·tag selector 연결 → 전체 C++ 빌드 → DA 생성/PDA catalog entry → Player BP tag 지정 → Probe/PIE다.
- 이 정정은 M2.2 data 준비 내부 순서를 보완하며 M2.3/M3 기능을 섞지 않는다. 이번 기록에서 게임 Source/Config/BP/uasset은 수정하지 않았다.


## 24. 2026-09-11 — §20.19 에셋 생성 실습 경계와 현재 심볼

- 실제 타입명은 `UKhazanCharacterDefinitionData : UDataAsset`, 파일명은 `KhazanCharacterDefinitionData.h/.cpp`, 에셋명은 `DA_Character_Khazan`으로 통일한다. 이전 절의 `UKhazanCharacterDefinition` 표기는 과거 심볼이다.
- Editor를 닫은 cold build 뒤 `/Game/Data/Character`에서 `Miscellaneous > Data Asset > Khazan Character Definition Data`를 선택해 `DA_Character_Khazan`을 만든다. locomotion 값은 170/470/600 cm/s, 15 cm/s, 1800/1800 cm/s², RotationRate (0, 540, 0) deg/s, Walk/Sprint/VelocityDirection이며 모두 현재 프로젝트 이관값이지 원작 metadata 직접 확인값이 아니다.
- 에셋 파일 생성은 inert data 작성이므로 manager 연결 전에 수행해도 된다. 다만 현재 `AKhazanCharacter::CharacterDefinition` 객체 포인터에는 할당하지 않는다. 최종 연결은 manager lookup 보강, `AssetData.CharacterDefinition.Khazan` native tag, `CharacterDefinitionAssetName` selector와 transient runtime pointer 이관, C++ 빌드 뒤에 한다.
- 이후 `PDA_AssetData`의 기존 `Data` group에 name=`AssetData.CharacterDefinition.Khazan`, path=`/Game/Data/Character/DA_Character_Khazan`, label=`AssetLabel.Preload` entry를 추가하고 Player BP에는 객체가 아니라 selector tag를 지정한다. 이 등록·지정은 앞선 C++ 연결이 준비된 뒤 수행한다.
- 이번 기록에서는 게임 Source/Config/BP/uasset을 수정하거나 빌드/PIE하지 않았다.


## 25. 2026-09-11 — §20.19 생성 에셋 이름 정정

- 사용자가 `/Game/Data/Character/DA_Character_Khazan`을 생성했다. 실제 파일과 native class `UKhazanCharacterDefinitionData`를 확인했으며, 아직 `PDA_AssetData` entry와 `BP_KhazanPlayer` 참조는 없다.
- `DA_InputData`와 같은 책임 중심 패턴을 유지하되 여러 캐릭터 variant를 구분하기 위해 이름을 `DA_CharacterDefinition_Khazan`으로 정리한다. 형식은 `DA_<Responsibility>_<Variant>`다.
- Editor Content Browser에서 해당 에셋을 rename한 뒤 Character 폴더의 redirector를 정리한다. 파일 시스템에서 `.uasset` 이름을 직접 바꾸지 않는다.
- 후속 catalog path는 `/Game/Data/Character/DA_CharacterDefinition_Khazan`, key는 `AssetData.CharacterDefinition.Khazan`이다. 기존 `DA_Character_Khazan` 경로로 entry를 먼저 만들지 않는다.
- `DA_KhazanConfigData`는 사용하지 않는다. Definition 전체와 내부 `LocomotionConfig`의 용어 경계를 유지하고, class/file/tag/property 이름은 이번 rename 때문에 변경하지 않는다.
- 이번 기록에서는 게임 Source/BP/Config/uasset을 직접 수정하거나 빌드/PIE하지 않았다.


## 26. 2026-09-11 — §20.19 Definition 에셋 완료 후 AssetManager 보강 소단계

- [실제 에셋] `/Game/Data/Character/DA_CharacterDefinition_Khazan`이 존재하고 이전 `DA_Character_Khazan` 파일은 없다. 아직 catalog/BP 참조는 연결하지 않은 상태다.
- [이번 사용자 적용 범위] `UKhazanAssetData`가 `PostLoad()`와 `PreSave()`에서 하나의 `RebuildRuntimeLookupMaps()`를 호출하게 하고, 파생 lookup map은 `Transient`로 둔다. lookup은 `FindAssetPathByName()`/`FindAssetSetByLabel()` nullable pointer 계약으로 바꿔 누락 key를 역참조하지 않는다.
- [Manager 대칭] `UKhazanAssetManager`의 cache 정본 key는 `FAssetEntry::AssetName` GameplayTag 하나다. 경로 이름과 tag 이름으로 같은 객체를 중복 cache하던 public path load/release 경로를 제거하고, `AssetNameToLoadedAsset`에서 load/release한다.
- [조회와 IO 명명] catalog의 `Find...`와 manager의 `FindLoadedAssetByName()`은 메모리 조회만 수행한다. 실제 IO는 `LoadSyncByName()`/`LoadSyncByLabel()`만 수행한다. 기존 `GetAssetByName()`이 preload 실패를 숨겨 동기 로드하던 동작은 제거하고 PlayerController의 두 사용처를 cache-only 조회로 이관한다.
- [검증 경계] 이 보강을 Editor 종료 cold build와 기존 `DA_InputData` 이동/회전 입력 PIE 회귀로 먼저 확인한다. Definition native tag, catalog entry, Character selector는 이 checkpoint 뒤 다음 소단계다.
- [적용 상태] 이번 기록은 사용자 구현용 설명이며 게임 Source/BP/Config/uasset을 직접 수정하거나 빌드/PIE하지 않았다.


<a id="asset-manager-rollback-next-20260911"></a>

## 27. 2026-09-11 — 과잉 보강 복원 완료와 다음 Definition 연결 절차

### 이번에 실제 끝낸 범위

- 사용자 승인으로 AssetManager/AssetData 및 Controller getter의 과잉 보강을 직접 복원했다. 앞선 26절의 `FindLoadedAssetByName`과 tag cache 전환은 철회한다. 현재는 기존 `GetAssetByName`, path/name/label load·release, FName cache다.
- 남긴 필수 보강은 PostLoad index rebuild, 누락 lookup의 안전한 반환, label의 중복 load 제거와 path key의 load·release 대칭이다. `_C` 변환은 원래의 로컬 `AssetEntry` 처리로 돌아가 name/label에 같은 변환 결과를 넣는다.
- 최종 빌드 및 DevMap 새 프로세스 시작/종료는 통과했다. Player/Monster Definition 누락으로 실제 이동 회귀는 아직 불가능하며 다음 연결 뒤 검증한다. Python의 protected 내부 map 비교는 수행하지 못했다. 상세는 [진단 기록](BUILD_RUNTIME_DIAGNOSTICS.md)의 마지막 절을 따른다.
- 다음 내용은 사용자가 직접 적용할 절차/제안이다. 아래 tag, 매개변수, Character selector, catalog/BP 변경은 이번에 적용하지 않았다. M2.2 완료나 M2.3 시작을 뜻하지 않는다.

### 다음 목표와 책임

`PDA_AssetData`가 이미 생성된 `/Game/Data/Character/DA_CharacterDefinition_Khazan`을 preload하고, 공통 Character가 자신의 선택 tag로 이 Definition을 얻어 기존 Locomotion 초기화에 전달하게 한다. Player/Monster는 각 BP에서 tag만 선택한다. Character가 Definition을 선택·검증하고 LocomotionComponent가 config 사본/CMC 정책을 소유하는 경계를 유지한다.

### 1. 실제 소비할 Definition tag 선언

`Source/Khazan/KhazanGameplayTags.h`의 기존 AssetData Tags 아래에 선언한다.

```cpp
UE_DECLARE_GAMEPLAY_TAG_EXTERN(AssetData_CharacterDefinition_Khazan);
```

같은 namespace의 `KhazanGameplayTags.cpp` AssetData Tags 아래에 정의한다.

```cpp
UE_DEFINE_GAMEPLAY_TAG(AssetData_CharacterDefinition_Khazan, "AssetData.CharacterDefinition.Khazan");
```

헤더는 다른 C++ 파일의 참조를 선언하고 cpp가 실제 tag를 등록한다. 이 값은 asset catalog 조회용이며 ASC 상태 태그가 아니다. 이번 Player entry의 실제 소비가 있으므로 선언하며 미사용 몬스터 태그를 먼저 늘리지 않는다.

### 2. 기존 getter에 필요한 최소 조회 선택만 추가

복원된 `GetAssetByName()`은 로드되지 않은 객체를 `TryLoad()`하는 기존 동작을 가진다. 따라서 이 함수를 그대로 호출한 성공만으로 Definition의 선행 준비 성공을 판정하지 않는다. Definition 소비를 추가하는 이번 다음 단계에서만, 아래 최소 확장을 함께 적용한다.

`KhazanAssetManager.h`의 기존 template 선언에 `bool bLoadIfMissing = true`, 아래 template 정의에 기본값 없는 `bool bLoadIfMissing`를 추가한다. 본문의 현재 `if (LoadedAsset == nullptr)`는 `if (LoadedAsset == nullptr && bLoadIfMissing)`로 바꾼다. 다른 본문, 기존 InputData 호출은 그대로다.

- 타입/의미: bool, 호출별 IO 허용 선택이며 보존되는 상태가 아니다. 기본 true는 기존 InputData의 동작을 보존한다.
- 작성자/소비자: Character 초기화 호출이 false를 전달하고 getter의 fallback 분기만 소비한다. 다른 API·cache·상태/스레드는 추가하지 않는다.
- false에서는 경로에 대한 `ResolveObject()` 결과만 사용한다. 없거나 타입이 다르면 nullptr이며 Character가 준비 실패를 처리한다. 이때도 실제 Preload label 등록 여부는 catalog 설정과 시작 로그로 별도 확인한다.
- 이 매개변수는 아직 제안이며 현재 파일에는 없다. 새 `FindLoaded...` 함수나 캐시를 다시 만들지 않는다.

### 3. Character의 선택자와 런타임 참조 분리

`Source/Khazan/Character/KhazanCharacter.h`에 `GameplayTagContainer.h` include를 추가하고 기존 Definition 멤버 위치에서 다음 두 책임을 구분한다.

- `FGameplayTag CharacterDefinitionAssetName`: `EditDefaultsOnly` 선택자다. 기본값은 빈 tag이며 BP Class Defaults에서 Player/Monster별 값을 지정한다. 단위 없는 key이고 Actor 수명 중 반복 갱신하거나 빙의마다 Reset하지 않는다. 공통 C++ 생성자에 Player 전용 tag를 박아 넣지 않는다.
- 기존 `TObjectPtr<UKhazanCharacterDefinitionData> CharacterDefinition`: `EditDefaultsOnly`를 제거하고 `Transient` 런타임 참조로 둔다. nullptr로 시작하며 초기화 때만 작성하고 현재 `GetCharacterDefinition()`과 config 전달이 소비한다. 기존 getter는 const 읽기 용도를 유지한다.
- 두 멤버를 BP에 읽기용으로 보일 경우 현재 `BlueprintReadOnly`, Category, `AllowPrivateAccess` 패턴을 유지한다. 에디터에서 직접 입력할 것은 tag 하나이며 런타임 pointer 칸에 DA를 지정하지 않는다.

### 4. 기존 초기화 본문에 조회 한 곳 연결

`KhazanCharacter.cpp`에 `System/KhazanAssetManager.h`를 include한다. `PostInitializeComponents()`의 현재 GameWorld 검사와 `InitAbilityActorInfo(this, this)`를 유지한다. 그 다음, 기존 `if (!IsValid(CharacterDefinition))` 바로 전에 다음 대입을 둔다.

```cpp
CharacterDefinition = UKhazanAssetManager::GetAssetByName<UKhazanCharacterDefinitionData>(
    CharacterDefinitionAssetName, false);
```

- 이 호출은 2단계의 인자를 적용한 뒤에만 컴파일된다. 태그를 const 참조로 전달하고 typed pointer를 반환받으며, false는 동기 로드를 허용하지 않는 선택이다.
- 현재의 Definition 유효성 검사/오류 return과 `InitializeMovementConfig(CharacterDefinition->GetLocomotionConfig())` 호출은 이어서 사용한다. 실패 로그에는 캐릭터 이름과 선택 tag를 함께 넣어 BP 설정 누락을 식별한다.
- 호출은 초기화 Game Thread에서 한 번 한다. worker AnimInstance에서 AssetManager를 조회하지 않는다. ASC ActorInfo 연결 성공과 config 준비 성공을 동일하게 취급하지 않는다.
- config를 받지 못하면 Component의 기존 초기화 실패 정책이 이동 요청을 거절한다. 타이머로 재시도하거나 AnimInstance에서 설정을 대신 주입하지 않는다.
- 빙의 변화에서는 기존 ASC 참조 갱신/intent handle 처리를 유지한다. 한 Pawn이 끝났다는 이유로 공유 preload 자산을 `ReleaseAll()`하지 않는다.

### 5. 빌드 후 기존 catalog와 Player BP 설정

Editor를 닫고 전체 `KhazanEditor Win64 Development` 빌드를 통과시킨 뒤 새 Editor를 연다.

1. `/Game/Data/PDA_AssetData`를 열고 기존 `Asset Group Name To Set`의 `Data` 그룹 → `Asset Entries`에 항목을 추가한다. 이미 있다면 중복 추가하지 않는다.
2. `Asset Name` = `AssetData.CharacterDefinition.Khazan`, `Asset Path` = `/Game/Data/Character/DA_CharacterDefinition_Khazan.DA_CharacterDefinition_Khazan`, `Asset Labels` = `AssetLabel.Preload`로 지정하고 저장한다. DA 인스턴스이므로 `_C`를 붙이지 않는다.
3. `/Game/_Art/Kazan/Character/Bluprints/BP_KhazanPlayer`의 Class Defaults → `Character | Definition` → `Character Definition Asset Name`에서 같은 tag를 선택하고 Compile/Save한다. 기존 직접 object pointer에 할당하는 과거 절차는 사용하지 않는다.
4. 이번에는 기존 Definition의 `LocomotionConfig` 값을 그대로 연결한다. 숫자를 새로 선정하지 않는다. 실제 Monster Definition은 해당 소비가 이어질 때 따로 등록하며 Player tag를 공통 Character 기본값으로 강제하지 않는다.

### 6. 적용 후 검증과 다음 경계

- 새 PIE에서 Player의 `has no CharacterDefinition`와 `could not acquire a locomotion intent source`가 사라지고 Definition의 config가 공통 Locomotion 초기화에 전달되는지 확인한다. 연결하지 않은 시험 Monster의 경고와 Player 결과를 구분한다.
- Definition을 위한 늦은 sync load 경고가 없어야 한다. 이름/타입/선택자 누락은 로그와 이동 거절로 끝나고 크래시나 임의 fallback config가 없어야 한다.
- 현재 Walk/Run/Sprint/Stop, 태그 중첩 제한, UnPossess/EndPlay/재 PIE와 config/CMC 일치를 확인한다. 위 세부 체크포인트를 통과한 뒤 M2.2를 닫고 M2.3의 일반 적/AI 공통 이동으로 진행한다.
- `ResolveObject()`의 메모리 조회와 `TryLoad()`의 실제 로드 구분은 [Epic FSoftObjectPath API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/CoreUObject/FSoftObjectPath?lang=en-US)를 따른다. 엔진 API의 동작 근거이며 원작 gameplay 수치의 출처가 아니다.

## 28. 2026-09-11 — 현재 AssetManager/AssetData 호출 계약과 Definition 실습 설명 보완

- 사용자 요청은 수정 이력 요약이 아니라 현재 인터페이스의 실제 사용법과 다음 소단계의 상세 설명이다. 이번에는 소스/BP/Config/uasset을 수정하지 않았으며, 27절 이후의 Definition 연결 코드는 계속 사용자 적용 전 제안이다.
- 현재 `GetAssetByName<T>(const FGameplayTag&)`에는 인자가 하나다. `bLoadIfMissing`는 아직 없으며, 27절의 선언/정의/조건 변경을 적용한 뒤에만 두 인자로 호출할 수 있다.

### 현재 호출자가 지켜야 하는 계약

| 인터페이스 | 입력/반환 및 사용 의미 |
| --- | --- |
| `Initialize()` | 기존 GameInstance `Init()`에서 호출한다. Primary catalog를 얻고 Preload label을 동기 준비한다. 반환형은 void다. |
| `GetAssetByName<T>(FGameplayTag)` | catalog 경로를 `ResolveObject`/`Cast`하고 실패하면 `TryLoad`한다. 성공은 T 포인터, 실패는 nullptr다. 이 함수 자체는 manager 보관 map에 객체를 추가하지 않는다. |
| `LoadSyncByName(FGameplayTag)` | catalog의 정확히 같은 name tag로 경로를 얻어 load/manager 보관한다. |
| `LoadSyncByPath(FSoftObjectPath)` | 지정 경로를 load/manager 보관한다. 경로 유효성만으로 실제 파일 존재/타입이 보장되지는 않는다. |
| `LoadSyncByLabel(FGameplayTag)` | 정확히 같은 label의 entry들을 동기 load하고 각 경로의 asset FName으로 보관한다. 그룹 FName을 받는 함수가 아니다. |
| `ReleaseByName(FName)` | `DA_InputData` 같은 경로 끝의 object 이름으로 manager 참조를 제거한다. `AssetData.InputData` tag 문자열을 넘기는 계약이 아니다. |
| `ReleaseByPath` / `ReleaseByLabel` / `ReleaseAll` | 해당 manager 참조를 제거한다. 다른 UObject 참조의 해제, 즉시 GC, catalog 해제 또는 label별 참조 횟수 관리를 보장하지 않는다. |
| `GetAssetPathByName(FGameplayTag)` | `FSoftObjectPath` 값 사본을 반환한다. 누락 시 빈 경로이므로 `IsValid()`로 검사한다. |
| `GetAssetSetByLabel(FGameplayTag)` | 내부 map 값에 대한 `const FAssetSet*`를 반환한다. 누락 시 nullptr이므로 검사 후 `->AssetEntries`를 사용한다. 반환 포인터를 delete하거나 index rebuild 이후까지 보관하지 않는다. |

- name tag/label tag는 TMap의 정확한 key 조회다. 부모 tag를 전달한다고 하위 entry를 함께 찾지 않는다. `Data` group은 편집용 분류다. custom `AssetLabel.Preload`는 이 프로젝트의 grouping tag이며 Engine `UPrimaryAssetLabel` 에셋과 같은 개념으로 취급하지 않는다.
- AssetData의 편집 원본은 `AssetGroupNameToSet`이다. name/label lookup map은 `PostLoad`/`PreSave`에서 재구성하므로 직접 편집하지 않는다. 경로 정규화는 entry의 로컬 사본에 적용되며 BP_/B_/GE_/GA_ 이름에는 `_C`가 추가된다. DA 인스턴스 경로에는 `_C`를 붙이지 않는다.
- manager 보관 key는 경로의 leaf FName이므로 서로 다른 폴더의 같은 object 이름을 독립적으로 보관하지 못한다. label이 겹쳐도 label별 참조 횟수는 없다. 공유 Preload의 release를 개별 Character EndPlay에 넣지 않는다.
- `ReleaseAll()`은 `LoadedAssetData`를 비우지 않는다. 이후 `Initialize()`만 다시 호출하면 catalog 존재 검사에서 반환하므로 보관 map의 재구성이 필요할 때는 해당 load API를 사용해야 한다.
- API는 현재 native C++ 함수이며 UFUNCTION이 아니다. BP에서 Manager 함수 노드를 새로 찾거나 Anim worker에서 호출하는 절차를 안내하지 않는다.

### 다음 실습의 구체적 상태/검증 계약

- tag 등록은 기존 `KhazanGameplayTags` namespace의 AssetData 구역에 선언/정의를 각각 추가한다. Character 공통 생성자에 Player tag를 지정하지 않는다.
- Character header에는 `GameplayTagContainer.h`를 generated header 앞에 추가한다. 선택자는 `EditDefaultsOnly` GameplayTag, runtime Definition은 `Transient` TObjectPtr이며 기존 const getter를 유지한다. runtime 참조 확인을 위해 `VisibleInstanceOnly`를 함께 붙이는 것은 이번 설명의 제안이며 현재 소스에는 적용하지 않았다.
- Character cpp는 기존 GameWorld 검사/ASC ActorInfo 연결 뒤에 `GetAssetByName<UKhazanCharacterDefinitionData>(CharacterDefinitionAssetName, false)` 대입을 두고 기존 유효성 검사와 config 초기화를 이어간다. 실패 로그는 actor/선택 tag를 포함한다. Locomotion의 config는 getter가 반환한 const 참조를 초기화 함수가 값으로 복사하며, 실행 중 DA 편집을 자동 추적하는 구조가 아니다.
- header/reflection/tag 수정 후 Editor를 종료한 전체 빌드를 한다. 그 뒤 기존 `/Game/Data/PDA_AssetData`의 Data group에 정확한 Definition name/path/Preload label을 등록하고 `/Game/_Art/Kazan/Character/Bluprints/BP_KhazanPlayer` Class Defaults의 선택 tag를 지정한다. 기존 Definition asset/수치는 그대로 사용한다.
- Preload 검증은 catalog/BP 저장 후 새 프로세스에서 한다. 에디터에서 DA를 먼저 열면 이미 메모리에 있는 객체를 false 조회가 찾을 수 있어 label 누락을 가릴 수 있다. false 조회의 성공 자체가 Preload membership을 증명하지는 않는다.
- Player runtime Definition 참조, 초기화 실패 로그, CMC의 gait별 MaxWalkSpeed 및 config 적용, Walk/Run/Sprint/Stop, 입력 해제/반복 PIE를 확인한다. 미연결 Monster 오류는 Player의 합격 여부와 구분한다. 이 연결만으로 M2.2 전체 검증이 완료된 것은 아니다.
- 초기화 순서를 모든 Pawn에 일반화하지 않는다. 설치된 UE 5.8 `Engine/Source/Runtime/Engine/Private/Pawn.cpp`에서 Player auto possession은 `PreInitializeComponents`, AI auto possession은 `PostInitializeComponents` 내부에서 발생할 수 있음을 소스로 확인했다. Definition/config 성공 후에도 intent 획득 실패가 남으면 실제 spawn/auto-possession 경로와 호출 순서를 확인한다. 이번에는 관련 게임 코드를 수정하거나 runtime 호출 순서를 검증하지 않았다.
- 이번 검증은 현재 소스/설정/기존 기록 및 해당 엔진 소스의 읽기 전용 대조다. 직전 복원본의 빌드/시작 성공을 위 미적용 제안의 빌드/PIE 성공으로 기록하지 않는다.

