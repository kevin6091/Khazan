# Dodge 최소 변경 공동 구현 안내 — 2026-10-01

이 문서는 사용자가 직접 적용할 구현 절차다. 어시스턴트는 게임 C++/BP/에셋을 변경하지 않았다. 아래 코드는 현재 Source를 기준으로 한 제안이다. 이전 DodgeSpecialAttack 전체 16파일 첨부보다 이 최소 안내와 Architecture 마지막 ARCH-72 절이 우선한다.

## 이번 목표와 적용 상태

목표는 A Started → 현재 Move 입력 기준 방향 선택 → 기존 ASC press → 이미 존재하는 Dodge ComboAction 실행, 그리고 Dodge 입력창 안의 X/Y → 해금된 특별 공격 Entry다. 비LockOn과 LockOn 무입력은 F, LockOn 유효 입력은 F/RF/R/RB/B/LB/L/LF 중 하나다.

현재 실제 Source에는 공통 ComboAction, Montage Task/Notify/window/buffer/Edge/비용 gate/CanActivate, Dodge 상속/enum/defaults/getter, A/Dodge 태그, X/Y 라우팅과 CharacterDefinition grant가 있다. 아직 Player 방향 함수, Controller Dodge binding, ASC RequestedHandle 필터는 없다. 현재 표적 폴더에 IA_Dodge/AM_DAS_Dodge/특별 공격 BP는 없다. 8개의 Dodge BP 및 InGame 시퀀스 파일은 있다. 라이브 에디터 미저장 상태와 BP defaults/slot/root/timing을 이번 작업에서 읽거나 저장하지 않았다.

핵심은 기존 Player/Controller/ASC의 h/cpp 6파일 수정이다. Character UnPossessed의 기존 수명 누락 보완 1파일을 별도로 포함한다. 새 runtime 파일/class/state/component/manager/task/math helper는 없다. KZDodgeAbility와 ComboAction/ComboDefinition/CharacterDefinition native schema는 변경하지 않는다.

| 소유자 | 이번 책임 | 재사용하는 기능 |
| --- | --- | --- |
| Player | 현재 입력 → Actor 기준 방향, 함수 지역 계산 | IsLockedOn/MoveInputDeadZone/기존 수학 API |
| Controller | A 입력과 현재 Move action 조회, 방향별 Spec Handle 선택 | Enhanced Input/InputData/GetKZASC |
| ASC | 요청한 handle만 기존 press 루프에 통과 | Spec press/release/cancel/activation/restart |
| 활성 ComboAction Ability | 몽타주·입력창·예약·전환·비용·종료 | 현재 구현 전체 |
| BP/공유 graph/GE | 방향/Entry/Montage/해금/Edge 데이터 | 기존 타입과 GAS OwnedTags |
| Locomotion/CMC/ABP | 차단 합성·캡슐 root motion·포즈 | 기존 이동/DefaultSlot 경로 |

단계별로 아래 코드를 적용한다. [변경 부분만 담은 패치](Examples/DodgeMinimal_20261001.patch)는 동일 코드를 모은 참조다. 프로젝트 루트에서 `git apply --check --ignore-space-change Docs/Engineering/Examples/DodgeMinimal_20261001.patch`는 현재 working tree 문맥과 일치하는지만 확인한다. 변경을 쓰지 않으며 컴파일 검사도 아니다. 사용자 Source가 바뀌었으면 현재 파일과 대조해 해당 부분만 적용한다.

## 1. ASC에 선택한 Spec Handle 필터 추가

파일은 Source/Khazan/Ability/KZAbilitySystemComponent.h/.cpp다. ASC에 Dodge enum/방향 계산/전용 실행기를 넣지 않는다. Controller가 고른 엔진 Spec Handle로 기존 입력 경로만 좁힌다.

### 1-1. 헤더의 기존 선언 교체

```cpp
void AbilityInputTagPressed(
    const FGameplayTag& InputTag,
    FGameplayAbilitySpecHandle RequestedHandle = FGameplayAbilitySpecHandle());
```

- InputTag는 현재와 같은 const FGameplayTag&다. 입력 tag 객체를 참조하고 수정하지 않는다.
- RequestedHandle은 엔진의 작은 Spec 식별자를 값으로 받는다. Ability/Spec 전체를 복사하거나 소유하는 것이 아니다.
- 기본 생성자는 invalid handle을 만든다. “특정 Spec을 요청하지 않음”이라는 의미다. 기존 X/Y의 한 인자 호출이 유지된다.
- void 반환은 기존 계약이다. 새 실패 enum/result wrapper를 만들지 않는다. GAS 실행 승인과 실행 수명은 기존 경로가 소유한다.
- 기본 인자는 .h에만 적는다. .cpp 정의에서 반복하지 않는다.

### 1-2. cpp 정의의 인자 목록 교체

```cpp
void UKZAbilitySystemComponent::AbilityInputTagPressed(
    const FGameplayTag& InputTag,
    FGameplayAbilitySpecHandle RequestedHandle)
```

함수 몸체는 보존한다. GetActivatableAbilities를 순회하는 두 for문, 즉 이미 active인 Spec 루프와 inactive 후보 루프의 각각 첫 부분에 아래를 넣는다.

```cpp
if (RequestedHandle.IsValid() && AbilitySpec.Handle != RequestedHandle)
{
    continue;
}
```

RequestedHandle이 유효하고 이번 Spec의 Handle이 다르면 continue한다. invalid이면 이 조건이 false이므로 기존 InputTag 탐색을 수행한다. 두 루프 모두 넣어야 현재 F 회피 중 R 요청이 active F 루프에서 먼저 처리되는 것을 막는다. 기존 Ability 유효성/active 여부/HasTagExact(InputTag) 검사는 그대로 남긴다. Handle과 tag 조건을 둘 다 통과해야 한다.

| 사례 | 선택 결과 |
| --- | --- |
| 기존 X/Y 호출, handle 생략 | 기존 exact InputTag 탐색 |
| A + 유효 R Spec handle | A binding이 있는 R Spec만 처리 |
| 유효 handle이지만 tag 불일치/Spec 제거됨 | activation 없음 |
| Controller가 방향을 못 찾음 | ASC 호출 전 거절, invalid로 A 후보를 실행하지 않음 |

### 1-3. 같은 Spec 재입력 비용 사전 검사

현재 AbilityInputTagPressed는 active Action의 HasInputEnded가 true이면 기존 실행을 먼저 Cancel한다. 비용이 부족하면 새 activation은 실패하지만 기존 회피 회복도 이미 취소된다. 기존 RestartHandle 선언과 CancelAbilityHandle 사이에 아래 CanActivate 검사를 추가한다.

```cpp
const FGameplayAbilitySpecHandle RestartHandle = AbilitySpec.Handle;

if (!AbilityActorInfo.IsValid() ||
    !PrimaryInstance->CanActivateAbility(RestartHandle, AbilityActorInfo.Get()))
{
    return;
}

CancelAbilityHandle(RestartHandle);
```

이 블록은 기존 if (IsValid(ActionAbility) && ActionAbility->HasInputEnded()) 안에 있다. PrimaryInstance는 바로 위에서 기존 코드가 얻고 검사한 UGameplayAbility*다.

- RestartHandle: 현재 실제 Spec 식별자를 지역 값으로 보존한다.
- AbilityActorInfo.IsValid(): ASC의 ActorInfo가 존재하는지 검사한다. 없으면 이후 포인터 사용을 하지 않는다.
- PrimaryInstance->CanActivateAbility: public engine base API를 통해 실제 override를 호출한다. 기존 비용/쿨다운/태그와 ComboAction entry/AnimInstance/data gate를 읽으며, 비용을 소비하지 않는다.
- 실패 return은 기존 실행 Cancel보다 앞이다. 현재 회피가 유지된다.
- 승인 후 기존 Cancel→handle 재조회→InputPressed=true→TryActivateAbility 경로를 유지한다. 사전 승인은 이후 callback/Commit/Task 실패의 rollback 보장은 아니다.

Cancel 뒤 기존 null 검사도 아래로 보완한다.

```cpp
if (RestartSpec == nullptr || RestartSpec->IsActive())
{
    return;
}
```

Spec이 제거됐거나 취소되지 않고 아직 active이면 새 activation으로 진행하지 않는다. CanActivate 성공을 강제 Cancel 성공으로 해석하지 않는다.

### 1-4. graph-only 특별 공격에는 InputPressed를 남기지 않기

같은 cpp의 TryActivateComboEntry에서 기존 bPreviousInputPressed 선언과 다음 대입을 아래로 교체한다.

```cpp
const bool bPreviousInputPressed = TargetSpec->InputPressed;
const bool bHasInputBinding = !TargetSpec->GetDynamicSpecSourceTags().IsEmpty();
TargetSpec->InputPressed = bInputPressed && bHasInputBinding;
```

현재 Spec DynamicSpecSourceTags의 작성자는 CharacterDefinition grant의 InputTag 하나다. 따라서 현재 프로젝트에서 비어 있지 않음은 InputTag binding이 있음을 뜻한다. 이 전제는 현행 Source 계약이지 엔진 일반 보장이 아니다. 나중에 다른 종류의 dynamic tag를 부여하는 작성자를 추가하면 이 검사를 input tag 검사로 바꿔야 한다.

bPreviousInputPressed는 기존 activation 실패 복구용 지역 값이다. bHasInputBinding도 지역 bool이며 멤버 상태를 추가하지 않는다. binding 없는 특별 공격은 X/Y가 held여도 false다. held 사실은 기존 HeldComboCommands에서 읽는다. 기존 binding이 있는 target은 기존 bool 동작을 유지한다. 실패 시 기존 복원 코드는 그대로다.

HasComboEntry, TryActivateComboEntry의 인자 형식, SubmitComboCommand, OneParam event, Released/Canceled, X/Y 호출 순서는 유지한다. 일반 Charge의 binding 사이 입력 소유권 문제는 기존 회귀/별도 보완 대상이며 이 안내 때문에 범용 input owner manager를 만들지 않는다.

## 2. Player에 지역 방향 계산 추가

Source/Khazan/Character/KZPlayer.h의 generated include 뒤, class 전방 선언들과 같은 위치에 넣는다.

```cpp
enum class EKZDodgeDirection : uint8;
```

EKZDodgeDirection의 실제 정의는 이미 Ability/PlayerAbility/KZDodgeAbility.h에 있다. 여기에 같은 UENUM을 복제하지 않는다. Player header의 일반 C++ 선언은 enum 이름과 uint8 기반 타입만 알면 된다. 새 reflected UFUNCTION/UPROPERTY를 추가하는 작업이 아니다.

public 영역에 선언한다.

```cpp
EKZDodgeDirection ResolveDodgeDirection(
    const FVector2D& MovementInput,
    const FRotator& ControlRotation) const;
```

KZPlayer.cpp에 아래 include를 추가한다. KismetMathLibrary include는 현재 이미 있다.

```cpp
#include "Ability/PlayerAbility/KZDodgeAbility.h"
```

cpp에 전체 함수를 추가한다.

```cpp
EKZDodgeDirection AKZPlayer::ResolveDodgeDirection(
    const FVector2D& MovementInput,
    const FRotator& ControlRotation) const
{
    if (!IsLockedOn() || MovementInput.Length() <= MoveInputDeadZone)
    {
        return EKZDodgeDirection::F;
    }

    const FRotator CameraYaw(0.0, ControlRotation.Yaw, 0.0);
    const FVector CameraForward = UKismetMathLibrary::GetForwardVector(CameraYaw);
    const FVector CameraRight = UKismetMathLibrary::GetRightVector(CameraYaw);
    const FVector WorldInput =
        CameraForward * MovementInput.X + CameraRight * MovementInput.Y;

    const FRotator ActorYaw(0.0, GetActorRotation().Yaw, 0.0);
    const FVector LocalInput =
        UKismetMathLibrary::LessLess_VectorRotator(WorldInput, ActorYaw);
    double AngleDegrees =
        UKismetMathLibrary::DegAtan2(LocalInput.Y, LocalInput.X);

    if (AngleDegrees < 0.0)
    {
        AngleDegrees += 360.0;
    }

    constexpr int32 DirectionCount = 8;
    constexpr double SectorDegrees = 360.0 / DirectionCount;
    const int32 DirectionIndex =
        FMath::FloorToInt((AngleDegrees + SectorDegrees * 0.5) / SectorDegrees)
        % DirectionCount;

    return static_cast<EKZDodgeDirection>(DirectionIndex);
}
```

### 방향 함수의 인자·지역 값·연산

MovementInput은 현재 평가된 Move action의 2D 값이다. 현재 프로젝트 계약은 X=전후, Y=좌우다. ControlRotation은 같은 입력 처리 순간 Controller의 회전이며 각 성분 단위는 degree다. 두 인자의 const&는 입력을 수정하지 않으며 큰 값 객체 복사를 피한다. 함수 끝 const는 Player의 멤버를 변경하지 않는 관측 함수임을 뜻한다. Controller A Started에서 Game Thread로 호출한다.

첫 분기 !IsLockedOn() || Length<=MoveInputDeadZone은 정책이다. 비LockOn 또는 유효 입력 없음이면 F를 반환한다. 기존 MoveInputDeadZone native 값 0.1은 Source/Khazan/Character/KZPlayer.h의 현재 프로젝트 설정이며 원작 확인값이 아니다. BP override가 실제 설정이다. 새로운 임계값/속도 threshold를 추가하지 않는다.

CameraYaw는 Pitch/Roll을 0으로 두고 camera/control Yaw만 쓴다. CameraForward/Right는 각각 월드 수평 기준의 정면/오른쪽 단위 벡터다. WorldInput은 두 방향에 장치 입력 성분을 곱해 합성한 월드 의도다. 실제 velocity/cm/s가 아니다.

ActorYaw는 현재 캐릭터 정면의 수평 방향이다. LessLess_VectorRotator는 WorldInput에 ActorYaw의 역회전을 적용한다. 설치 UE 5.8 엔진 구현은 B.UnrotateVector(A)다. LocalInput.X는 캐릭터 정면 성분, Y는 오른쪽 성분이다. 기존 AnimInstance가 VelocityWorld→VelocityLocal에 사용하는 계산 방식을 재사용하되 현재 입력을 넣는다. 저장된 MovementDirectionAngle은 실제 속도의 snapshot 각도이므로 읽지 않는다.

DegAtan2(Y,X)는 [-180,180] degree를 구한다. 오른쪽이 양수다. 음수에는 360을 더해 왼쪽 -90을 270으로 표현한다. 입력 세기를 양수배해도 각도가 같고 무입력은 이미 첫 분기가 처리하므로 별도 normalize가 필요 없다.

DirectionCount=8, SectorDegrees=360/8, 반구간=SectorDegrees*0.5는 균등 8방의 기하학 정의다. Floor는 반구간을 더한 각도가 들어가는 sector를 고르고 %8은 F 경계에서 8을 0으로 감싼다. 정확한 sector 경계는 더 큰 index 쪽으로 배정된다. 부동소수점 경계 근처 결과는 실제 입력/각도로 확인한다. 이 경계들은 원작 방향 판정 metadata 확인값이 아니다.

static_cast는 index를 이미 존재하는 enum으로 바꾼다. enum 순서가 F=0, RF=1, R=2, RB=3, B=4, LB=5, L=6, LF=7이어야 한다.

| Actor-local 각도 | enum |
| --- | --- |
| 0° | F |
| 45° | RF |
| 90° | R |
| 135° | RB |
| 180° | B |
| 225° / -135° | LB |
| 270° / -90° | L |
| 315° / -45° | LF |

카메라/Actor Yaw가 같으면 (1,0)→F, (0,1)→R, (-1,0)→B, (0,-1)→L, (1,1)→RF다. camera Yaw=90°, Actor Yaw=0°, input=(1,0)이면 월드 +Y이므로 R이다. 이는 손으로 확인할 기하학 사례이며 gameplay 튜닝값이 아니다.

모든 지역 값은 함수 호출 동안만 존재한다. 현재 Direction 멤버나 Reset 함수를 추가하지 않는다. 속도/CMC/Actor 회전/Sprint 요청을 변경하지 않는다. 방향은 이후 선택된 BP의 Entry node로 고정되고 현재 LockOn 회전 정책이 실제 root-motion 궤적에 미치는 영향은 별도 PIE 확인이다.

## 3. Controller에 A 입력과 Spec 선택 연결

파일은 Source/Khazan/Player/KZPlayerController.h/.cpp다. Player 전용 장치 입력의 해석과 variant 선택은 입력 adapter의 책임이며 ASC에는 Dodge class 의존성을 추가하지 않는다. 실제 비용/태그 승인·취소·실행은 기존 ASC/GAS/Ability가 한다. 미래 AI는 물리 A 입력을 흉내 내지 않고 선택한 Ability/Spec을 기존 GAS 경로로 실행할 수 있다. AI adapter를 지금 생성하지 않는다.

### 3-1. 헤더 선언과 cpp include

private 영역에 아래 세 콜백을 선언한다. FInputActionValue 전방 선언은 현재 이미 있다.

```cpp
void Input_DodgeStarted(const FInputActionValue&);
void Input_DodgeCompleted(const FInputActionValue&);
void Input_DodgeCanceled(const FInputActionValue&);
```

cpp에는 다음 세 include를 추가한다. Build.cs의 EnhancedInput/GameplayAbilities 의존성은 이미 있으므로 새 모듈을 추가하지 않는다.

```cpp
#include "EnhancedPlayerInput.h"
#include "GameplayAbilitySpec.h"
#include "Ability/PlayerAbility/KZDodgeAbility.h"
```

### 3-2. SetupInputComponent의 기존 InputData 블록 끝에 binding 추가

기존 StrongAttack Canceled binding 다음, InputData if 블록 안에 넣는다.

```cpp
const UInputAction* DodgeAction =
    InputData->FindInputActionByTag(KZGameplayTags::Input_Action_A);

if (IsValid(DodgeAction))
{
    EnhancedInputComponent->BindAction(
        DodgeAction, ETriggerEvent::Started, this, &ThisClass::Input_DodgeStarted);
    EnhancedInputComponent->BindAction(
        DodgeAction, ETriggerEvent::Completed, this, &ThisClass::Input_DodgeCompleted);
    EnhancedInputComponent->BindAction(
        DodgeAction, ETriggerEvent::Canceled, this, &ThisClass::Input_DodgeCanceled);
}
```

InputData는 현재 DA_InputData lookup이다. Input.Action.A는 이미 native tag 사전에 있다. DodgeAction은 지역 const UInputAction*이며 asset을 새로 생성하거나 소유하지 않는다.

IsValid 분기는 아직 IA_Dodge를 만들지 않은 상태에서 null action binding을 하지 않게 한다. 기존 InputData lookup은 행이 없으면 Error log 후 nullptr을 반환한다. A binding만 생략하고 기존 Move/X/Y binding은 유지된다. 첫 PIE 전에 에디터 데이터 단계를 마쳐 이 로그가 없어야 한다.

Started는 최초 회피 요청 한 번, Completed는 정상 버튼 해제, Canceled는 입력 시스템의 취소다. Triggered 매 프레임 회피 요청을 사용하지 않는다. this는 현재 Controller 인스턴스, ThisClass::...는 이 인스턴스가 실행할 멤버 함수 포인터다. 새 tick/timer/delegate를 만들지 않는다.

### 3-3. Started 함수 추가

```cpp
void AKZPlayerController::Input_DodgeStarted(const FInputActionValue&)
{
    AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn());
    UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent();
    const UEnhancedPlayerInput* EnhancedPlayerInput =
        Cast<UEnhancedPlayerInput>(PlayerInput);
    const UKZInputData* InputData =
        UKZAssetManager::GetAssetByName<UKZInputData>(
            KZGameplayTags::AssetData_InputData);

    if (!IsValid(PlayerCharacter) || !IsValid(ASC) ||
        !IsValid(EnhancedPlayerInput) || !IsValid(InputData))
    {
        return;
    }

    const UInputAction* MoveAction =
        InputData->FindInputActionByTag(KZGameplayTags::Input_Action_Move);
    if (!IsValid(MoveAction))
    {
        return;
    }

    const FVector2D MovementInput =
        EnhancedPlayerInput->GetActionValue(MoveAction).Get<FVector2D>();
    const EKZDodgeDirection Direction =
        PlayerCharacter->ResolveDodgeDirection(MovementInput, GetControlRotation());

    FGameplayAbilitySpecHandle SelectedDodgeHandle;
    {
        FScopedAbilityListLock AbilityListLock(*ASC);
        for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
        {
            if (!Spec.Ability ||
                !Spec.GetDynamicSpecSourceTags().HasTagExact(KZGameplayTags::Input_Action_A))
            {
                continue;
            }

            const UKZDodgeAbility* DodgeDefaults = Cast<UKZDodgeAbility>(Spec.Ability);
            if (!IsValid(DodgeDefaults) || DodgeDefaults->GetDodgeDirection() != Direction)
            {
                continue;
            }

            if (!ensureMsgf(!SelectedDodgeHandle.IsValid(),
                TEXT("Duplicate granted Dodge direction: %d"), static_cast<int32>(Direction)))
            {
                return;
            }
            SelectedDodgeHandle = Spec.Handle;
        }
    }

    if (!ensureMsgf(SelectedDodgeHandle.IsValid(),
        TEXT("No A-bound Dodge for direction: %d"), static_cast<int32>(Direction)))
    {
        return;
    }

    ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_A, SelectedDodgeHandle);
}
```

1. GetPawn→Cast는 지금 조종 중인 Player를 읽는다. 오래된 Pawn pointer를 멤버에 저장하지 않는다.
2. GetKZAbilitySystemComponent는 현재 Pawn의 기존 ASC를 얻는다.
3. PlayerInput→UEnhancedPlayerInput은 현재 장치 입력의 평가 결과를 읽을 엔진 객체다. const pointer이므로 새 입력을 주입하거나 상태를 변경하지 않는다.
4. 기존 AssetManager로 InputData를 얻고 네 필수 객체가 유효하지 않으면 return한다. 실패했다고 임의 F Ability를 활성화하지 않는다.
5. InputData의 Input.Action.Move로 기존 MoveAction을 찾는다. missing이면 lookup log 뒤 return이다.
6. GetActionValue(MoveAction).Get<FVector2D>()는 현재 평가된 Move 값의 복사다. UE의 GetActionValue는 triggering 아닌 action에 zero value를 반환한다. IA_Move는 Axis2D여야 하며 현재 HandleInputMove의 계약과 동일하다.
7. ControlRotation과 함께 Player 방향 함수에 넘긴다. 이전 Move callback이 작성한 Locomotion intent/Anim snapshot의 순서에 의존하지 않는다. 같은 frame Move+A는 실제 mapping/trigger 평가와 함께 PIE로 확인한다.
8. SelectedDodgeHandle은 기본 invalid인 지역 엔진 handle이다. 새 입력 owner 원장/방향 멤버가 아니다.
9. FScopedAbilityListLock은 엔진이 제공하는 목록 변경 보류 범위다. 중괄호 안에서 읽고 범위 종료 시 자동 해제한다. Game Thread 수명 보조이지 worker에서 ASC를 안전하게 읽는 mutex 계약이 아니다.
10. const Spec&는 실제 granted Spec을 복사하지 않고 읽는다. Ability가 없거나 A exact binding이 없으면 continue한다. 다른 input/특별 공격은 후보가 아니다.
11. Spec.Ability의 Dodge CDO/defaults를 읽는다. 실행 인스턴스를 만들어 보거나 활성 방향을 변경하지 않는다. GetDodgeDirection과 현재 Direction이 같은 것만 후보다.
12. 이미 valid handle이 있으면 같은 방향 중복 grant 오류다. 첫 후보를 조용히 고르거나 둘을 실행하지 않고 return한다. return 시 list lock도 해제된다.
13. 후보의 Handle만 지역 값으로 기록한다. list 범위 밖에 Spec pointer/참조를 보관하지 않는다.
14. 찾은 handle이 없으면 return한다. invalid를 전달하면 ASC는 “일반 A 탐색”으로 해석하므로 반드시 여기서 막는다.
15. 기존 ASC press에 A+선택 Handle을 보낸다. Controller가 Commit/Cancel/몽타주/비용을 직접 실행하지 않는다.

같은 방향의 active Spec은 기존 HasInputEnded/restart 정책을 사용한다. InputEnd 전 같은 방향 A는 기존 GAS press만 전달되고 몽타주를 재시작하지 않는다. 다른 방향 inactive Spec은 InputEnd 전 Action block 때문에 거절된다. InputEnd 뒤 다른 방향은 새 Action 활성화와 기존 CancelAbilitiesWithTag로 이전 실행을 끝낸다. 비용 사전 거절은 새 Action의 PreActivate 취소보다 먼저다.

### 3-4. Completed/Canceled 추가

```cpp
void AKZPlayerController::Input_DodgeCompleted(const FInputActionValue&)
{
    AbilityInputTagReleased(KZGameplayTags::Input_Action_A);
}

void AKZPlayerController::Input_DodgeCanceled(const FInputActionValue&)
{
    AbilityInputTagCanceled(KZGameplayTags::Input_Action_A);
}
```

두 콜백은 새 로직 없이 기존 Controller wrapper를 사용한다. InputValue가 필요 없어서 인자 이름을 생략했다. Completed는 A 입력 owner의 InputPressed를 지우고 GAS release를 전달한다. Dodge base에는 버튼 Release로 몽타주를 끝내는 Task를 새로 붙이지 않았으므로 일반 A tap 뒤 회피는 계속 재생된다. Canceled는 정상 Release 공격을 만들지 않고 실제 A owner의 active Ability를 취소한다.

A는 이번 설계에서 현재 Dodge 진입 입력이다. Command.Player.Dodge.A를 새 held 명령으로 제출하거나 모든 Dodge node에 A Edge를 만들 필요가 없다. Attack 도중 A buffer/cancel 같은 추가 규칙을 실제 구현할 때 그 Command의 소비 계약을 추가한다. 현재 X/Y RouteAttackInput와 Combo event는 유지한다.

## 4. 기존 에셋 연결 — 먼저 F, 다음 8방

아래는 Editor에서 사용자가 수행할 작업이다. 현재 InGame 파일 존재만 확인했고 실제 asset property/미저장 BP는 확인하지 않았다. 기본 참조를 F에서 검증한 뒤 같은 최종 구조의 나머지 방향 데이터를 확장한다. 임시 probe class/API를 생성하지 않는다.

### 4-1. IA_Dodge와 기존 InputData/IMC

1. /Game/Input에서 Input Action IA_Dodge를 생성한다. Value Type=Boolean. 최초 단계에는 추가 Hold/Chord trigger를 넣지 않는다. Started를 한 번 요청하는 입력이다.
2. /Game/Input/IMC_Default의 Mappings에 IA_Dodge를 추가하고 Gamepad Face Button Bottom(A)을 연결한다. 기존 같은 키 mapping 충돌을 확인한다. 키보드 키는 현재 프로젝트의 중복 없는 키를 선택한다. 이 물리키는 프로젝트 binding이고 원작 입력 metadata 확인값이 아니다.
3. /Game/Data/DA_InputData → Input Actions 배열에 InputTag=Input.Action.A, InputAction=/Game/Input/IA_Dodge를 추가한다.
4. 기존 Move 행은 /Game/Input/Locomotion/IA_Move 및 Axis2D/X전후·Y좌우 계약을 유지한다. IA_Move modifier/trigger를 이 설명 때문에 변경하지 않는다.
5. Save한다. SetupInputComponent의 A lookup이 valid여야 세 callback이 연결된다. A tag 사전 등록만으로 엔진이 action을 자동 bind하지 않는다.

### 4-2. 기존 root-motion 회피 모션으로 Montage

폴더 /Game/_Art/Player/Animation/InGame/DAS/Dodge에서 아래 _M1 8개를 사용한다. 같은 폴더의 _M1 없는 L/R 대안을 섞지 않는다.

| 방향 | 실제 파일 이름 | NodeId / SectionName |
| --- | --- | --- |
| F | CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1 | Dodge_F |
| RF | CA_P_Kazan_DualAxeSword_Off_Dodge_RF_M1 | Dodge_RF |
| R | CA_P_Kazan_DualAxeSword_Off_Dodge_R_M1 | Dodge_R |
| RB | CA_P_Kazan_DualAxeSword_Off_Dodge_RB_M1 | Dodge_RB |
| B | CA_P_Kazan_DualAxeSword_Off_Dodge_B_M1 | Dodge_B |
| LB | CA_P_Kazan_DualAxeSword_Off_Dodge_LB_M1 | Dodge_LB |
| L | CA_P_Kazan_DualAxeSword_Off_Dodge_L_M1 | Dodge_L |
| LF | CA_P_Kazan_DualAxeSword_Off_Dodge_LF_M1 | Dodge_LF |

F sequence 우클릭 → Create → Create AnimMontage로 AM_DAS_Dodge를 같은 폴더에 만든다. 우선 F 하나로 시작해도 된다. 이후 위 순서로 같은 Slot track에 나머지 segment를 놓고 각 실제 segment 시작에 같은 이름의 section을 만든다. Default section은 Dodge_F로 맞춘다. 모든 section의 Next를 None으로 해 자동으로 다음 방향까지 재생하지 않게 한다.

기존 Attack이 사용하는 DefaultGroup.DefaultSlot/ABP_Player Slot 뒤 Inertialization 경로를 재사용한다. Sequence와 Player mesh의 Skeleton이 맞는지, InGame asset에 Enable Root Motion/실제 최상위 root 이동이 있는지 확인한다. 저장 원본 후보의 enable_root_motion=true/force_root_lock=true는 현재 InGame 복제본 property 직접 확인을 뜻하지 않는다. 현재 ABP root-motion mode를 이 안내 때문에 Montages Only로 변경하지 않는다. root motion의 capsule 이동은 기존 CMC가 수행하고 AddMovementInput/SetActorLocation/Launch를 중복 적용하지 않는다.

### 4-3. 기존 point Montage Notify 세 개

Montage Notify track 우클릭 → Add Notify → Montage Notify로 point를 만들고 Details의 Notify Name을 InputOpen/InputCommit/InputEnd로 지정한다. Montage Tick Type은 Branching Point다. Skeleton 일반 Notify나 Notify Window는 이 콜백 계약과 다르므로 종류도 확인한다. 이름이 ComboInputOpen인 과거 기록을 현행 이름으로 복사하지 않는다.

앞선 안내에서 정한 임시 authoring을 그대로 재사용할 수 있다.

| 이름 | section 로컬 frame | FPS=30일 때 로컬 시간 | 임시 선정 의도 |
| --- | --- | --- | --- |
| InputOpen | 4 | 4/30≈0.133333 s | 시작 피드백 뒤 특별 공격 예약 허용 |
| InputCommit | 8 | 8/30≈0.266667 s | 예약 실행, 이후 Begin은 즉시 전환 |
| InputEnd | 24 | 24/30=0.8 s | 특별 공격 창 종료, 일반 Action/Move 복귀 허용 |

4/8/24는 어시스턴트가 이전에 선정한 **임시 튜닝값**이며 원작 Notify 타이밍 근거는 없다. 새 C++ literal을 넣지 않고 Montage point 위치에 모아 관리한다. 숫자가 기존 문서에 있다고 원작 확인값이 되는 것은 아니다.

환산 입력의 저장 출처는 Saved/KZStaminaLockOnDodgeInspect.json의 dodge_combat_m1[0]이다. 정확한 path는 /Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Combat/Evasion/Dodge/CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1이며 frame_rate 원시 struct는 numerator=30/denominator=1, number_of_frames=32, play_length=1.0666667222976685 s다. 이것은 현재 UE 후보의 임포트/저장 감사 관측으로 원작 gameplay window metadata가 아니다.

InGame 각 clip의 실제 sample rate/길이를 Editor에서 확인한다. Notify 절대시간=section start S+local frame/FPS다. 세 point는 자신의 section 안에, Open<Commit<End<section end 순서로 둔다. section 시작 첫 frame의 Notify 검색 경계에 의존하지 않는다. FPS가 다르면 local frame/FPS를 재계산한다.

Open/Commit이 너무 빠르면 회피가 원치 않게 공격으로 잘리고, 너무 늦으면 입력 응답이 늦다. End가 너무 빠르면 root-motion 회피가 덜 끝난 상태에서 일반 입력이 허용되고, 너무 늦으면 회복 입력이 답답하다. 실제 조작/모션을 보고 point를 조정하고 원작 근거가 확보되면 동일 의미/조건을 대조해 교체한다.

### 4-4. 공유 Definition·기존 Dodge BP·grant

/Game/Data/ComboCommand/DA_Player_Combo_Definition → Nodes에 Dodge_F를 추가하고 NodeId=Dodge_F, Montage=AM_DAS_Dodge, SectionName=Dodge_F로 둔다. 처음 CommandEdges는 비운다. 8방 확장 때 위 표의 나머지 node를 같은 형식으로 추가한다. 기존 Weak/Strong/Charge node는 보존한다.

기존 /Game/Bluprints/AbilitySystem/Abilities/Player/Dodge/GA_Player_DodgeAbility_F를 열고 Class Defaults에서 아래를 설정한다.

| 항목 | F 설정 | 나머지 방향 |
| --- | --- | --- |
| Parent | 현재 UKZDodgeAbility | 동일 |
| Dodge Direction | F | 각자의 RF/R/RB/B/LB/L/LF |
| Combo Definition | DA_Player_Combo_Definition | 같은 asset 객체 |
| Entry Node Id | Dodge_F | 해당 Dodge_<방향> |
| Instancing Policy / Net Execution | 현재 InstancedPerActor / LocalOnly | 부모 설정 유지 |
| Block/Cancel Abilities With Tag | Ability.Action | 부모 설정 유지 |
| Activation Owned Tags | 기존 Block.Movement.Input/Block.StaminaRegen | 부모 설정 유지 |

Combo Definition은 static TObjectPtr 설정이며 BP 작성자가 저장하고 Activate/Edge가 읽는다. Entry Node Id는 static FName이며 native 초기 NAME_None은 미설정이다. Dodge Direction은 기존 EditDefaultsOnly enum이며 native 초기 F는 각 BP를 authoring하기 전 기본값이다. 런타임 방향을 이 멤버에 쓰거나 Reset하지 않는다. 지금 enum/getter/ctor를 다시 작성하지 않는다.

현재 Dodge Cost GE가 없다면 첫 입력/모션 연결 checkpoint에서는 Costs의 Cost Gameplay Effect Class=None으로 경로를 확인할 수 있다. 이는 원작 무비용 판정이 아니다. 확인된 Dodge Cost GE가 있으면 그 기존 설정을 연결하며 기존 Attack cost를 임의 복사하지 않는다. 새 stamina 숫자를 C++에 넣지 않는다. 실제 비용 부족 검증은 Cost GE를 연결한 뒤 수행한다.

On End Ability Gameplay Effect에는 기존 /Game/Bluprints/AbilitySystem/Effects/GE_Player_StaminaRegenDelay를 재사용할 수 있다. 현재 종료 후 지연 정책을 이어 쓰는 설정이며 duration을 원작 확인값으로 새로 주장하거나 변경하지 않는다.

/Game/Data/Character/DA_CharacterDefinition_Player → Initial Ability Grants에 F BP를 한 번 추가하고 InputTag=Input.Action.A로 지정한다. 8방 확장 때 기존 Dodge BP 8개 각각 한 번, 모두 같은 A tag로 추가한다. 앞선 전체 안내의 Dodge grant InputTag 비움 지시는 이 최소안에서 대체된다. 특별 공격 grant는 다음 절처럼 비운다. CharacterDefinition의 native grant 함수는 변경하지 않는다.

먼저 비LockOn F의 A tap→한 번 회피→자연 종료/회복 Move를 확인한다. 이후 나머지 7 BP/section/node/A grant를 확장하고 LockOn 8방을 확인한다. 같은 방향 중복 BP defaults/grant는 Controller ensure에 걸려야 한다.

## 5. Dodge → X/Y 해금형 특별 공격은 기존 graph로

이 단계는 C++ 새 실행 코드를 만들지 않고 기존 Attack BP, shared graph, tag/GE를 연결한다. 우선 F 두 갈래를 닫고 실제 모션/분기가 확인된 방향 데이터를 확장한다. 8방×2버튼이라는 이유로 고유 모션/Ability 16개를 무조건 만들지 않는다.

### 5-1. 해금 tag 사전 등록

해금 태그 문자열은 프로젝트 semantic 이름이며 원작 내부 tag를 확인한 값이 아니다.

- Unlock.Skill.DAS.DodgeAttack.Weak
- Unlock.Skill.DAS.DodgeAttack.Strong

이 둘은 Edge/Ability/GE의 에디터 데이터가 소비하므로 native h/cpp 상수를 새로 만들 필요가 없다. Project Settings → Gameplay Tags에서 Import Tags From Config를 확인하고 Manage Gameplay Tags에서 DefaultGameplayTags.ini source에 두 tag를 추가할 수 있다. ini를 직접 작성한다면 기존 Config/DefaultGameplayTags.ini의 이미 있는 section 아래에 다음 행만 추가하고 기존 redirect를 보존한다.

```ini
ImportTagsFromConfig=True
+GameplayTagList=(Tag="Unlock.Skill.DAS.DodgeAttack.Weak",DevComment="Dodge weak special unlock")
+GameplayTagList=(Tag="Unlock.Skill.DAS.DodgeAttack.Strong",DevComment="Dodge strong special unlock")
```

tag dictionary에 등록되는 것과 ASC가 tag를 소유하는 것은 다르다. 소유 사실은 다음 Infinite GE가 작성한다. native 상수를 선호해 기존 KZGameplayTags 영역에 등록하는 방법도 가능하지만 이 최소 절차에서 둘 다 중복 정의하지 않는다.

### 5-2. F 특별 공격 BP/Entry

기존 UKZComboAttackAbility를 부모로 하는 두 BP를 /Game/Bluprints/AbilitySystem/Abilities/Player/DodgeAttack에 작성한다. 명칭은 GA_Player_DodgeWeakAttack_F와 GA_Player_DodgeStrongAttack_F다. 새 native DodgeAttack class는 없다.

현재 InGame DodgeAttack 폴더에는 Com_DodgeAtk_F_JustMoment 및 Com_DodgeAtk_F_RecklessRush 등이 있다. F Weak=JustMoment, F Strong=RecklessRush는 앞선 **임시 콘텐츠 대응**을 재사용하는 첫 연결 후보다. 파일 존재는 확인했지만 원작 X/Y·스킬 대응은 미확인이다. prefix는 CA_P_Kazan_DualAxeSword_다. Charge variant를 plain Y에 임의 연결하지 않는다.

확인한 모션으로 /Game/_Art/Player/Animation/InGame/DAS/DodgeAttack/AM_DAS_DodgeWeakAttack_F 및 AM_DAS_DodgeStrongAttack_F를 작성한다. 각각 같은 이름의 entry section DodgeWeakAttack_F/DodgeStrongAttack_F, Next=None, 기존 DefaultSlot을 사용한다. 특별 공격의 비용/입력창/피해/취소를 모션 이름만으로 확정하지 않는다. 최초 연결에서는 자연 종료를 확인하고 InputEnd authoring은 actual clip의 회복 시점을 확인한 뒤 한다.

shared Definition에 두 node를 추가하고 각 Montage/SectionName을 연결한다. 두 BP의 ComboDefinition은 같은 DA_Player_Combo_Definition 객체, EntryNodeId는 각 node다. source/target Definition pointer가 다르면 현재 ASC의 Entry 검색이 연결되지 않는다.

target BP의 Activation Required Tags에 각각 Weak 또는 Strong 해금 tag를 넣는다. Activation Owned Tags에 unlock을 넣지 않는다. 요구 태그는 실행 승인 시 읽는 조건이고 소유 태그는 실행이 쓰는 상태이므로 역할이 다르다.

CharacterDefinition Initial Ability Grants에 두 BP를 추가하고 InputTag는 None/비움으로 둔다. 잠겨 있어도 grant는 유지한다. 현재 ApplyEdge는 target Entry Spec이 없으면 local node 전환으로 해석하므로 grant를 해금 on/off 수단으로 쓰지 않는다. 다른 Montage의 local jump는 현재 코드에서 거절된다.

### 5-3. Dodge_F의 두 Edge

| 필드 | X | Y |
| --- | --- | --- |
| Command Tag | Command.Player.Attack.X | Command.Player.Attack.Y |
| Command Phase | Begin | Begin |
| Hold / Move | Any / Any | Any / Any |
| Required Held Commands | empty | empty |
| Owner Tag Requirements → Must Have Tags | Unlock.Skill.DAS.DodgeAttack.Weak | Unlock.Skill.DAS.DodgeAttack.Strong |
| Must Not Have Tags / Query Must Match | empty | empty |
| Target Node Id | DodgeWeakAttack_F | DodgeStrongAttack_F |

Must Have Tags는 C++ RequireTags, Must Not Have Tags는 IgnoreTags, Query Must Match는 TagQuery의 UE 5.8 에디터 표시 이름이다. Node → Command Edges → Owner Tag Requirements를 펼쳐 작성한다.

CommandTag는 이번 버튼 사건이다. RequiredHeldCommands는 추가 hold 조건이므로 자기 X/Y를 다시 넣지 않는다. tap이 Release된 뒤 Commit에서 예약 Begin을 실행하는 기존 계약을 유지한다. 현재 Dodge node가 회피 종류/방향을 이미 표현하므로 IsDodging/Direction Edge 필드나 Main AnimInstance의 전투 bool이 필요 없다.

기존 MatchesEdge가 OwnerTagRequirements.RequirementsMet(ASC OwnedTags)를 검사하고 기존 ApplyEdge/TryActivateComboEntry가 target을 실행한다. target 자체의 ActivationRequiredTags는 직접 Spec 활성화에도 같은 해금 경계를 적용한다. 읽는 곳은 둘이고 상태 작성자는 GE 하나다.

### 5-4. 현재 X/Y 순서를 유지하는 이유와 기대 결과

현재 RouteAttackInput Begin은 generic press → SubmitComboCommand다. InputEnd 전에는 Action의 Ability.Action block으로 일반 Attack 진입이 거절되고 살아 있는 Dodge가 command를 처리한다. InputEnd는 ComboWindow Closed→Action block 해제 순서이므로 이후 새 Begin은 일반 공격이고 특별 Begin Edge는 실행되지 않는다. 따라서 현재 정책에서 bConsumed/TwoParam event/bAllowNewActivation을 추가하지 않는다.

| 시점/상태 | 기대 결과 |
| --- | --- |
| InputOpen 전 X/Y | 특별 Edge 예약 없음, 일반 공격은 block |
| Open~Commit, 해금된 X/Y | 한 칸 예약 후 Commit에서 해당 특별 Entry |
| Commit~End, 해금된 X/Y | 기존 즉시 전환 |
| InputEnd 전, 미해금 | Edge 조건 불일치, Dodge 유지 |
| InputEnd 뒤 새 X/Y | 기존 일반 공격 진입 |
| target 사전 Cost/tag/data 거절 | existing ApplyEdge가 살아 있는 source block 복구 |
| target activation 후 Task/Commit 실패 | 기존 실행 복원을 보장하지 않음, 데이터/Task 실패를 별도 확인 |

이 표는 현행 native 정책을 BP가 유지하는 경우의 Source 분석이다. 실제 montage Notify/BP override/프레임 순서는 PIE로 확인한다. 이후 InputEnd 뒤에도 열린 특별 Edge를 우선시키는 새 규칙을 채택하면 입력 중재를 그때 검토한다.

### 5-5. 기존 InitialEffects로 해금 네 조합 확인

/Game/Bluprints/AbilitySystem/Effects/Unlock에 개발용 GE_Dev_Unlock_DodgeAttack_Weak 및 GE_Dev_Unlock_DodgeAttack_Strong을 만든다. Class Defaults의 Duration Policy=Infinite, Components에 Target Tags (Granted to Actor), Add Tags→Added에 각 unlock tag를 넣는다. attribute modifier나 새 timer가 필요 없다. Instant/GE AssetTags는 같은 소유 계약이 아니다.

CharacterDefinition의 기존 Initial Effects 배열에서 기존 Stamina/regen GE는 유지하고 개발용 두 GE만 없음/Weak만/Strong만/둘 다로 바꾼다. 매번 Stop PIE→새 PIE로 확인한다. 현재 Character 초기화가 initial GE를 적용하므로 새 C++ producer는 없다. 이는 개발 검증용 시작 해금 상태이며 제품 Save/스킬 습득 구현 완료가 아니다. 실제 producer가 생기면 그 producer가 자기 Effect handle로 부여/해제하고 Pawn 준비 시 영속 원본을 반영한다.

다른 Dodge node에는 실제로 확인한 가족/방향의 target Edge를 작성한다. 대각선 RF/LF→F, RB/LB→B는 이전 안내의 원작 미확인 임시 후보이며 자동 확정하지 않는다. L/R 두 가족에 같은 Off_DodgeAtk_L/R_M1을 공유하는 것도 최초 경로 시험용 임시 대응이다. 모션/해금 규칙이 확인된 만큼 데이터를 확장한다.

## 6. 기존 Character 수명 보완

Source/Khazan/Character/KZCharacter.cpp에 #include "KZGameplayTags.h"를 추가한다. UnPossessed의 기존 ASC if 안에서 ClearComboCommands 바로 앞에 Action cancel을 넣는다.

```cpp
FGameplayTagContainer ActionTags;
ActionTags.AddTag(KZGameplayTags::Ability_Action);
ASC->CancelAbilities(&ActionTags);
ASC->ClearComboCommands();
```

ActionTags는 지역 FGameplayTagContainer이며 Ability.Action이라는 AssetTag 분류에 맞는 실행들을 취소하는 filter다. ASC owned tag를 일괄 제거하는 코드가 아니다. ActorInfo가 유효한 Super::UnPossessed/현재 ActorInfo clear 이전 위치에서 호출한다.

CancelAbilities가 기존 EndAbility/Task/delegate/ActivationOwnedTags cleanup을 실행한다. 그 뒤 ClearComboCommands가 pending cancel 사건과 Spec 입력 기록을 정리하므로 정상 Release 공격을 만들지 않는다. Player의 raw intent/Sprint/LockOn cleanup, Character의 이후 ActorInfo clear, EndPlay DestroyActiveState는 보존한다. 새 cleanup manager/빈 State를 추가하지 않는다.

## 7. 적용 순서와 검증

1. 위의 핵심 6파일 수정과 Character 수명 보완을 사용자가 저장한다. 현재 base/enum/CanActivate/Cost gate는 반복 작성하지 않는다.
2. Unreal Editor 작업을 저장하고 정상 종료한다. 프로젝트 루트 PowerShell에서 아래 Development Editor cold build를 실행한다. 헤더/새 callback/엔진 native API를 새 바이너리로 확인한다.
3. 새 Editor에서 변경 영향 BP를 Compile/Save하고 IA_Dodge/IMC/InputData와 F의 Montage/node/BP/A grant를 연결한다. F checkpoint를 먼저 닫는다.
4. 나머지 7 방향의 데이터/A grant를 확장해 8방/동일 frame 입력/restart를 확인한다.
5. 해금 tag 사전, F 두 특별 Entry와 GE 네 조합을 연결해 기존 X/Y·Charge 회귀를 확인한다. 이후 확인된 방향 데이터로 확장한다.
6. Cost GE가 실제 연결된 뒤 사전 비용 실패 유지, capsule/벽/경사/LockOn yaw, 정상·취소·UnPossess/Stop PIE 정리를 확인한다.

```powershell
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat' KhazanEditor Win64 Development '-Project=C:\Users\user\Desktop\GitProject\Khazan\Khazan\Khazan.uproject' -WaitMutex -NoHotReloadFromIDE
```

### 실제 적용 후 기대 결과와 실패 시 표적 확인

| 검사 | 기대 결과 | 실패 시 확인 |
| --- | --- | --- |
| 비LockOn A, 이동 입력 방향 무관 | F 한 번 | IsLockedOn/SelectedHandle/F defaults |
| LockOn 무입력 | F | 현재 IA_Move 값/기존 deadzone |
| LockOn 8방 | 대응 BP Entry | X전후·Y좌우/camera·Actor Yaw/방향 defaults |
| 같은 frame Move+A | 현재 평가된 Move 방향 | Move trigger/IMC/action value/callback breakpoint |
| 같은 방향 InputEnd 전 | 재시작 없음 | HasInputEnded/기존 active press 경로 |
| 다른 방향 InputEnd 전 | 새 Dodge 거절 | native Action block/BP override |
| InputEnd 뒤 재입력 | 요청한 방향 시작 | 두 루프 handle 필터/InputEnd point/ASC cancel |
| 같은 방향 Cost 부족 | 이전 회피 회복 유지 | CanActivate가 Cancel보다 먼저인지 |
| A tap Release | InputPressed 정리, 회피 재생 계속 | Completed vs Canceled/binding/새 release Task 여부 |
| A Canceled | 실제 입력 owner 실행 canceled | Spec InputPressed/A binding |
| 해금 네 조합 X/Y | 해당 가족만 특별 Entry | OwnedTags/Edge RequireTags/target RequiredTags |
| buffer tap/즉시 전환 | 한 번 입력에 한 전환 | Notify 종류·이름·순서/pending/target grant |
| InputEnd 뒤 X/Y | 기존 일반 공격 | Closed/SetInputEnded/일반 binding |
| 자연 종료/interrupt/UnPossess | Task/delegate/block 잔존 없음 | 기존 EndAbility/ActorInfo 유효 시점 |
| root-motion 캡슐/벽 | 기존 CMC 경로로 이동·collision | 최상위 root/slot/Skeleton/BP scale/실제 capsule delta |
| 기존 Weak/Strong/Charge | 기존 흐름 유지 | RequestedHandle 기본 invalid/graph-only 기록 보완 |

사용자가 breakpoint를 확인할 위치는 Controller Started의 MovementInput/Direction/SelectedHandle → ASC의 두 루프/HasInputEnded → CanActivate/Activate의 EntryNode → Combo command의 window/edge/owner tags → TryActivateComboEntry target → EndAbility다. 이 안내는 실제 debugger 실행 기록이 아니다.

원작 수치와 대응이 미확인인 항목은 비용·입력창·특별 가족/대각선 모션·무적·적중/피해·Save producer다. 이번 범위는 방향별 실행과 해금 Edge의 연결이며 이들을 완료로 기록하지 않는다. 비용 literal, capsule displacement 보정, Main AnimInstance의 전투 timer를 추가하지 않는다.

## 8. 어시스턴트의 실제 확인 범위

- 현재 Source 9개 baseline hash를 읽고 필요한 기존 7파일의 diff만 작성했다. 새 runtime 파일은 0개다.
- 설치 UE 5.8의 FScopedAbilityListLock, Spec const accessor, EnhancedPlayerInput::GetActionValue, GAS 부모 tag block/PreActivate blocking 초기화, 비용/ActivationRequiredTags, tag ini/GE component field를 확인했다.
- 표적 InGame Dodge/DodgeAttack/8 BP/InputData/IMC/shared Definition 파일의 존재와 저장 후보 감사의 timing 입력을 확인했다. BP property/미저장 Editor/실제 root-motion playback 검증은 하지 않았다.
- git apply --check --ignore-space-change가 현재 working tree에서 통과했다. patch 문맥 검사이며 C++ compile/PIE 성공을 의미하지 않는다.
- 게임 Source/BP/Config/에셋에 제안을 적용하지 않았고 build/PIE는 수행하지 않았다. 실제 수정은 정책·안내 MD와 참조 patch뿐이다.
