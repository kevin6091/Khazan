# Dodge 입력과 해금형 특별 공격 구현 안내

사용자가 직접 C++와 에디터 설정을 적용하는 안내다. 목표는 A 입력으로 방향별 Dodge를 실행하고, 현재 Dodge의 입력창에서 X/Y를 누르면 각각 해금된 특별 공격으로 넘어가는 것이다. 공통 ComboAction 추출, CanActivateAbility 사전 검사, local node CheckCost gate는 현재 사용자 Source에 이미 있다. 그 부분을 다시 추출하지 않는다.

이 폴더의 16개 .h.txt/.cpp.txt는 **전체 파일 제안**이다. 확장자 .txt는 설명용 사본이라는 표시다. 실제 Source에 같은 이름으로 추가/비교 적용하고, Docs의 사본을 build 대상에 넣지 않는다. 기존 Source를 분석한 시점 이후 사용자 변경이 있으면 변경 부분을 비교해서 적용한다. 게임 파일은 어시스턴트가 수정하지 않았다. SOURCE_BASELINE.json에 당시 Source SHA256을 남긴다. build와 PIE는 적용 후 사용자가 수행해야 한다.

이번 범위는 방향 선택, GAS 실행/취소, Montage, Combo 입력 중재, 해금 gate다. 피해 확정·적중 trace·무적 window·GameplayCue·영속 Save producer는 구현 완료 범위에 포함하지 않는다. 원작 모션 대응, 비용, 입력창 시간과 LockOn 선회 중 월드 회피 궤적은 별도 검증 항목이다.

파일별 책임과 적용 위치는 다음과 같다.

| 실제 파일 | 이번 책임 | 작성자와 소비자 |
| --- | --- | --- |
| Source/Khazan/Ability/KZDodgeTypes.h 신규 | 8방 enum | Player가 값 생성, ASC가 Spec 선택, Dodge BP가 defaults 설정 |
| Ability/PlayerAbility/KZDodgeAbility.h/.cpp | 각 BP의 방향 설정과 Dodge AssetTag | 에디터에서 작성, ASC가 CDO getter로 읽음 |
| Character/KZPlayer.h/.cpp | 현재 카메라/actor Yaw로 입력 방향 계산 | Controller가 한 번 호출, 반환 enum만 사용 |
| Player/KZPlayerController.h/.cpp | IA_Dodge Started와 현재 IA_Move 조회, X/Y 라우팅 | Enhanced Input → Player/ASC |
| Ability/KZAbilitySystemComponent.h/.cpp | granted Spec 조회, 소비 bool, 실제 입력 소유권 | Controller/ComboAction이 요청, Spec과 native event가 소비 |
| Ability/Combo/KZComboActionAbility.h/.cpp | 현재 node의 Edge 예약/실행과 handoff | ASC command 및 Montage Notify → 실행 중 Ability |
| Ability/Combo/KZComboDefinitionData.h/.cpp | authored graph의 에디터 오류 검사 | 에디터 Validate Assets |
| KZGameplayTags.h/.cpp | Weak/Strong 해금 tag 선언·등록 | GE가 ASC에 부여, Edge/Ability gate가 읽음 |
| Character/KZCharacter.cpp | 빙의 종료·EndPlay의 실행/입력 정리 | Character 수명 경계 |
| 기존 DA_InputData/IMC/CharacterDefinition | 입력 lookup과 Spec grant | AssetManager/Controller/Character |
| 기존 DA_Player_Combo_Definition | 방향 node, Montage/Section, X/Y Edge | 모든 ComboAction이 같은 asset 읽음 |

표의 첫 줄을 제외한 상대 경로 앞에는 Source/Khazan/을 붙인다. 개별 전체 사본은 같은 이름의 .txt 파일이다. 함수/변수 목록과 에디터 설정도 아래에 있다.

실행 순서는 IA_Dodge Started → 현재 IA_Move → Player.ResolveDodgeDirection → ASC.TryActivateDirectionalDodge → 해당 Dodge BP의 Entry → 공통 ActivateAbility → Montage다. X/Y Started는 ASC.SubmitComboCommand를 먼저 호출하고, 현재 Ability가 소비했는지를 받은 뒤 일반 InputTag press를 전달한다. 해금 조건은 이 command를 평가하는 Edge와 특별 공격 자체의 CanActivate 두 곳에서 읽는다.

Player/Controller/ASC/Ability command/Notify 처리는 Game Thread에서 수행한다. AnimInstance worker가 ASC/Actor를 직접 읽거나 Dodge/해금을 작성하지 않는다. AI의 C++ 소비자는 카메라 입력을 흉내 내지 않고 같은 ASC API에 선택한 enum을 넘길 수 있다. BP에서 AI 요청을 실제로 소비하게 될 때 BlueprintCallable 노출을 검토하며 지금 미사용 노드를 선행 추가하지 않는다.

먼저 graph 오류 검사를 추가한다. 대상은 KZComboDefinitionData.h/.cpp다. Dodge를 늘리기 전에 기존 Weak/Strong graph도 같은 검증을 통과시킨다. header의 public 영역에 WITH_EDITOR 선언을 추가한다.

```cpp
#if WITH_EDITOR
virtual EDataValidationResult IsDataValid(FDataValidationContext& Context) const override;
#endif
```

cpp에는 WITH_EDITOR 안에서 Animation/AnimMontage.h, Misc/DataValidation.h, UObject/Class.h를 include한다. 전체 함수는 다음과 같다.

```cpp
EDataValidationResult UKZComboDefinitionData::IsDataValid(
    FDataValidationContext& Context) const
{
    const EDataValidationResult ParentResult = Super::IsDataValid(Context);
    bool bHasErrors = false;

    const auto ReportError = [&Context, &bHasErrors](const FString& Message)
    {
        Context.AddError(FText::FromString(Message));
        bHasErrors = true;
    };

    TSet<FName> NodeIds;
    for (const FKZComboNode& Node : Nodes)
    {
        if (Node.NodeId.IsNone())
        {
            ReportError(TEXT("Combo NodeId is empty."));
        }
        else if (NodeIds.Contains(Node.NodeId))
        {
            ReportError(FString::Printf(
                TEXT("Duplicate Combo NodeId: %s"), *Node.NodeId.ToString()));
        }
        else
        {
            NodeIds.Add(Node.NodeId);
        }

        if (!IsValid(Node.Montage) || Node.SectionName.IsNone() ||
            Node.Montage->GetSectionIndex(Node.SectionName) == INDEX_NONE)
        {
            ReportError(FString::Printf(
                TEXT("Node %s has an invalid Montage/Section."),
                *Node.NodeId.ToString()));
        }
    }

    // 모든 NodeId를 모은 뒤 검사하므로 배열 뒤쪽 target도 정상으로 인정한다.
    for (const FKZComboNode& Node : Nodes)
    {
        for (int32 EdgeIndex = 0; EdgeIndex < Node.CommandEdges.Num(); ++EdgeIndex)
        {
            const FKZComboCommandEdge& Edge = Node.CommandEdges[EdgeIndex];
            if (!Edge.CommandTag.IsValid() ||
                Edge.CommandPhase == EKZComboCommandPhase::Cancel)
            {
                ReportError(FString::Printf(
                    TEXT("Node %s Edge %d has an invalid command or unsupported Cancel phase."),
                    *Node.NodeId.ToString(), EdgeIndex));
            }

            if (Edge.TargetNodeId.IsNone() || !NodeIds.Contains(Edge.TargetNodeId))
            {
                ReportError(FString::Printf(
                    TEXT("Node %s Edge %d targets missing Node %s."),
                    *Node.NodeId.ToString(), EdgeIndex, *Edge.TargetNodeId.ToString()));
            }

            for (int32 EarlierIndex = 0; EarlierIndex < EdgeIndex; ++EarlierIndex)
            {
                const FKZComboCommandEdge& Earlier = Node.CommandEdges[EarlierIndex];
                FKZComboCommandEdge Conditions = Edge;
                Conditions.TargetNodeId = Earlier.TargetNodeId;

                // target을 제외한 모든 reflected 조건이 완전히 같으면 뒤의 Edge는 가려진다.
                if (FKZComboCommandEdge::StaticStruct()->CompareScriptStruct(
                    &Earlier, &Conditions, 0))
                {
                    ReportError(FString::Printf(
                        TEXT("Node %s Edges %d and %d have identical conditions."),
                        *Node.NodeId.ToString(), EarlierIndex, EdgeIndex));
                    break;
                }
            }
        }
    }

    return bHasErrors || ParentResult == EDataValidationResult::Invalid
        ? EDataValidationResult::Invalid
        : EDataValidationResult::Valid;
}
```

- WITH_EDITOR는 검증 코드를 Editor build에만 포함한다. gameplay runtime에서 매 입력마다 graph를 전수 검사하지 않는다.
- 반환 EDataValidationResult는 Valid/Invalid/NotValidated 상태다. 부모의 Invalid도 보존한다. 이 클래스는 실제 규칙을 검사했으므로 오류가 없으면 Valid를 반환한다.
- Context는 에디터가 만든 오류 모음이며 비const 참조다. AddError로 메시지를 추가하기 때문에 참조가 필요하다. 함수 뒤의 const는 DataAsset 값을 바꾸지 않는다는 뜻이다.
- ParentResult는 부모의 검사 결과, bHasErrors=false는 이번 검사가 시작될 때의 지역 오류 상태다. 영속 gameplay bool이 아니다.
- ReportError는 이 함수 안에서만 쓰는 lambda다. [&Context, &bHasErrors]는 두 지역 값을 참조로 잡고, FText로 에디터 메시지를 남긴 뒤 오류 플래그를 올린다. 외부 공통 helper로 분리할 실제 소비가 없다.
- NodeIds는 TSet<FName>이다. 배열의 순서와 무관하게 ID 존재/중복을 검사한다. None인 이름과 같은 이름의 두 node를 거절한다. FName은 이름 식별자이고 위치/방향 각도 값이 아니다.
- Montage null, SectionName None, GetSectionIndex==INDEX_NONE 중 하나면 재생 불가능하다. || 단축 평가 덕분에 Montage가 null이면 그 뒤의 GetSectionIndex를 호출하지 않는다.
- 두 번째 순회에서 target을 검사한다. 첫 순회가 모든 ID를 모았으므로 뒤쪽에 작성한 target도 정상이다.
- EdgeIndex/EarlierIndex는 배열의 0 기반 번호다. CommandTag가 비었거나 Cancel phase면 오류다. Cancel은 pending cleanup이고 공격 실행 Edge로 사용하지 않는 현 계약이다.
- Conditions는 검사할 Edge의 지역 복사다. TargetNodeId만 앞 Edge와 같게 만든 뒤 reflected struct를 비교한다. 모든 나머지 조건이 동일하면 target이 달라도 앞 규칙이 먼저 매칭되므로 뒤 규칙이 가려진다. CompareScriptStruct의 0은 비교 플래그 없음이다.
- 모든 조건의 의미를 보편적으로 증명하는 검증은 아니다. Any와 특정 Hold/Move가 배열 순서로 일부 겹치는 경우, tag query의 논리적 함의, Montage Notify frame, CharacterDefinition grant와 BP defaults는 아래의 수동 검사로 확인한다. 같은 CommandTag라는 이유만으로 다른 조건의 합법적인 ordered fallback을 거절하지 않는다.

이제 방향 타입을 만든다. Source/Khazan/Ability/KZDodgeTypes.h에 아래 전체 코드를 추가한다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "KZDodgeTypes.generated.h"

// 캐릭터 정면에서 오른쪽으로 도는 순서다. 8방 섹터 계산의 index와 일치해야 한다.
UENUM(BlueprintType)
enum class EKZDodgeDirection : uint8
{
    F  = 0 UMETA(DisplayName = "Forward"),
    RF = 1 UMETA(DisplayName = "Right Forward"),
    R  = 2 UMETA(DisplayName = "Right"),
    RB = 3 UMETA(DisplayName = "Right Back"),
    B  = 4 UMETA(DisplayName = "Back"),
    LB = 5 UMETA(DisplayName = "Left Back"),
    L  = 6 UMETA(DisplayName = "Left"),
    LF = 7 UMETA(DisplayName = "Left Forward")
};
```

- #pragma once는 같은 header의 중복 포함을 막는다. CoreMinimal은 UE 기본 타입과 reflection macro를 제공한다.
- generated.h는 UHT가 이 enum의 reflection 정보를 생성할 header다. 직접 만드는 파일이 아니며 include 목록의 마지막이어야 한다.
- UENUM(BlueprintType)은 BP Class Defaults의 dropdown으로 쓸 수 있게 한다. uint8은 enum의 저장 타입이다.
- F/RF/R/RB/B/LB/L/LF는 기존 사용자 BP/sequence 이름의 방향 순서다. F=0부터 LF=7은 섹터 번호이며 gameplay 튜닝값이 아니다. 계산기에서 나온 정수를 enum으로 변환하므로 선언 순서를 바꾸면 계산도 함께 바꿔야 한다.
- UMETA(DisplayName)은 에디터 표시 이름만 바꾼다. RF라는 C++ 값이나 asset 이름을 바꾸지 않는다. 별도 COUNT를 에디터 선택지에 노출하지 않는다.

KZDodgeAbility.h는 다음과 같다. cpp의 ctor는 기존 Dodge AssetTag 설정을 유지하고 공격이라고 쓰인 주석만 바로잡았다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Ability/KZDodgeTypes.h"
#include "KZDodgeAbility.generated.h"

UCLASS()
class KHAZAN_API UKZDodgeAbility : public UKZComboActionAbility
{
	GENERATED_BODY()
	
public:
	UKZDodgeAbility();

    // granted Spec의 CDO에서 읽는 방향 설정이다. 실행 중에 갱신하지 않는다.
    EKZDodgeDirection GetDodgeDirection() const
    {
        return DodgeDirection;
    }

private:
    UPROPERTY(EditDefaultsOnly, Category = "Dodge")
    EKZDodgeDirection DodgeDirection = EKZDodgeDirection::F;
};
```
```cpp
#include "Ability/PlayerAbility/KZDodgeAbility.h"

#include "KZGameplayTags.h"

UKZDodgeAbility::UKZDodgeAbility()
{
	// GAS가 이 Ability를 Dodge 행동으로 구분할 때 쓰는 Asset Tag다.
	FGameplayTagContainer AssetTags;
	AssetTags.AddTag(KZGameplayTags::Ability_Action_Dodge);
	SetAssetTags(AssetTags);
}
```

- UKZDodgeAbility는 UKZComboActionAbility를 상속한다. 비용/Task/Notify/콤보 수명을 다시 구현하지 않는다. C++ 클래스 8개를 만들지 않고 BP 8개가 defaults만 다르게 쓴다.
- DodgeDirection은 EKZDodgeDirection 타입의 정적 BP 설정이다. 단위는 방향 선택지다. 기본 F는 미설정 상태에서 forward가 되는 초기값이며 8개 BP를 모두 F로 두라는 뜻이 아니다.
- EditDefaultsOnly는 BP Class Defaults에서만 설정한다. 현재 실행 중 방향을 Tick으로 덮어쓰지 않는다. private은 외부 C++의 직접 수정을 막는다. 이번 소비자는 C++ ASC이므로 BlueprintReadWrite를 열지 않는다.
- GetDodgeDirection() const는 설정을 값으로 반환한다. 작은 enum을 복사하고, const로 읽기만 한다. ASC는 실행 instance가 아니라 granted Spec.Ability의 CDO 설정을 조회한다.
- ctor AssetTags는 이 Ability의 분류다. Ability.Action.Dodge를 ASC Owned Tags에 부여한 것이 아니다. Block/CancelAbilitiesWithTag는 Ability Asset Tags를 대상으로 한다. 공통 base의 Block.Movement.Input/Block.StaminaRegen은 실행 동안 ASC가 소유하는 ActivationOwnedTags다.
- InstancedPerActor/LocalOnly/BlockAbilitiesWithTag와 CancelAbilitiesWithTag는 기존 KZActionAbility에서 상속된다. 별도 AbilityState enum/FSM/AnimInstance Dodge bool을 만들지 않는다.

Player header에 #include "Ability/KZDodgeTypes.h"를 generated.h보다 위에 넣고 public에 아래 함수를 선언한다.

```cpp
EKZDodgeDirection ResolveDodgeDirection(
    const FVector2D& MovementInput,
    const FRotator& ControlRotation) const;
```

KZPlayer.cpp는 이미 Kismet/KismetMathLibrary.h를 포함한다. 아래 정의를 추가한다.

```cpp
EKZDodgeDirection AKZPlayer::ResolveDodgeDirection(
    const FVector2D& MovementInput,
    const FRotator& ControlRotation) const
{
    // 비잠금은 모든 입력에서 F다. 무입력도 기존 Player deadzone으로 판정한다.
    if (!IsLockedOn() || MovementInput.Length() <= MoveInputDeadZone)
    {
        return EKZDodgeDirection::F;
    }

    // 기존 HandleInputMove와 동일한 카메라 Yaw 기준 입력이다.
    const FRotator CameraYaw(0.0, ControlRotation.Yaw, 0.0);
    const FVector CameraForward = UKismetMathLibrary::GetForwardVector(CameraYaw);
    const FVector CameraRight = UKismetMathLibrary::GetRightVector(CameraYaw);
    const FVector WorldInput =
        CameraForward * MovementInput.X + CameraRight * MovementInput.Y;

    // 캐릭터 Yaw 기준 정면/오른쪽 성분으로 투영한다. Pitch/Roll은 제외한다.
    const FRotator ActorYaw(0.0, GetActorRotation().Yaw, 0.0);
    const FVector ActorForward = UKismetMathLibrary::GetForwardVector(ActorYaw);
    const FVector ActorRight = UKismetMathLibrary::GetRightVector(ActorYaw);
    const double LocalForward = FVector::DotProduct(WorldInput, ActorForward);
    const double LocalRight = FVector::DotProduct(WorldInput, ActorRight);

    // 정면=0°, 오른쪽=+90°. 음수 왼쪽 각도를 [0, 360)으로 바꾼다.
    double AngleDegrees = UKismetMathLibrary::DegAtan2(LocalRight, LocalForward);
    if (AngleDegrees < 0.0)
    {
        AngleDegrees += 360.0;
    }

    // 360°/8과 반 섹터 폭은 균등 8방을 위한 기하학 상수다.
    // 원작의 조작 임계값을 추출했다고 주장하는 값이 아니다.
    constexpr int32 DirectionCount = 8;
    constexpr double SectorDegrees = 360.0 / DirectionCount;
    const int32 DirectionIndex =
        FMath::FloorToInt((AngleDegrees + SectorDegrees * 0.5) / SectorDegrees)
        % DirectionCount;

    return static_cast<EKZDodgeDirection>(DirectionIndex);
}
```

이 함수는 방향만 계산한다. MovementInput은 이번 Dodge press 순간의 IA_Move 값, ControlRotation은 그 순간 Controller 회전이다. const 참조는 불필요한 복사와 인자 수정을 막는다. 함수의 마지막 const는 Player의 member를 바꾸지 않는다. 값은 지역 변수에서 계산하고 enum만 반환한다. Raw Intent, Sprint 요청, CMC 속도와 캐릭터 회전을 쓰는 함수가 아니다.

| 지역 값 | 타입과 단위 | 생성 의도와 소비 |
| --- | --- | --- |
| MovementInput | FVector2D, 입력의 무차원 세기 | 현행 계약 X=전후 Y=좌우, Controller 전달 |
| ControlRotation | FRotator, degree | 카메라 기준 입력의 Yaw만 사용 |
| CameraYaw/ActorYaw | FRotator, degree | Pitch/Roll=0으로 평면 기저 생성 |
| CameraForward/Right | FVector, 단위 기저 | 장치 입력을 월드 방향으로 변환 |
| WorldInput | FVector, 무차원 입력 벡터 | actor 기저에 투영할 현재 의도 |
| ActorForward/Right | FVector, 단위 기저 | 캐릭터 정면/오른쪽을 판정 |
| LocalForward/Right | double, 입력 성분 | 내적, Atan2 인자 |
| AngleDegrees | double, degree | [-180,180] 결과를 [0,360)으로 정리 |
| DirectionCount | constexpr int32, 개수 | enum에 맞는 균등 8방 |
| SectorDegrees | constexpr double, degree | 360/8=45의 기하학 폭 |
| DirectionIndex | int32, 0..7 | 반 섹터 이동 → floor → wrap, enum 변환 |

!IsLockedOn()이면 방향 입력과 무관하게 F를 반환한다. LockOn이라도 Length()<=기존 MoveInputDeadZone이면 F다. 현재 native 초기값 0.1은 기존 프로젝트 설정이고 원작 확인값이 아니다. BP override가 있다면 그 실제 값이 사용된다. 여기서 새 Dodge 전용 threshold를 만들거나 수치를 변경하지 않는다.

WorldInput=CameraForward*X+CameraRight*Y는 기존 HandleInputMove와 같은 식이다. 일반 UE template에서 흔히 쓰는 X=좌우,Y=전후 식을 섞으면 여기 프로젝트의 방향이 뒤집힌다. 내적은 WorldInput의 actor 정면/오른쪽 성분을 뽑는다. 방향 각도는 세기에 불변이므로 WorldInput normalize가 필요 없다. 무입력은 앞의 deadzone 분기가 처리했다.

DegAtan2(LocalRight,LocalForward)는 오른쪽을 양수로 삼는다. F=(1,0)→0°, R=(0,1)→90°, B=(-1,0)→180°, L=(0,-1)→-90°→270°. 두 Yaw가 같고 입력(1,1)이면 RF,(-1,1)이면 RB다. 카메라 Yaw=90°, actor Yaw=0°이고 입력(1,0)이면 월드 +Y이며 actor-local R다. 이는 기하학 예제이지 gameplay tuning이 아니다.

(angle+22.5)/45를 floor하면 정면 주변 [-22.5,22.5)가 index 0에 들어온다. F의 음수 쪽은 360으로 옮겼기 때문에 %8로 index 8을 0으로 돌린다. 정확한 경계 +22.5°는 RF, -22.5°는 F 쪽에 속하는 이 구현의 반열린 구간 규칙이다. 부동소수점 경계 근처는 실제 입력으로 검사한다. 별도 원작 hysteresis/deadzone 각도 metadata를 확인한 결과는 아니다.


Controller에서 IA_Dodge를 연결한다. KZPlayerController.h의 private 영역에 다음을 선언하고, 기존 두 wrapper의 선언을 바꾼다.

```cpp
void Input_DodgeStarted(const FInputActionValue& InputValue);
bool SubmitComboCommand(
    const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase);
void AbilityInputTagPressed(
    const FGameplayTag& InputTag, bool bAllowNewActivation = true);
```

cpp에 EnhancedPlayerInput.h와 LogChannels.h를 추가한다. InputAction.h, KZInputData, AssetManager, KZPlayer와 project ASC include는 이미 있다. SetupInputComponent의 기존 InputData/EnhancedInputComponent가 있는 if 내부에서 X/Y bind 앞에 이 블록을 넣는다.

```cpp
const UInputAction* DodgeAction =
    InputData->FindInputActionByTag(KZGameplayTags::Input_Action_A);
if (IsValid(DodgeAction))
{
    EnhancedInputComponent->BindAction(
        DodgeAction, ETriggerEvent::Started,
        this, &ThisClass::Input_DodgeStarted);
}
```

Input.Action.A는 현재 존재하는 tag다. Input.Action.Dodge라는 새 tag를 여기서 쓰지 않는다. Started 한 번으로 방향 요청 한 번을 보내며 Triggered 반복 바인딩은 하지 않는다. Dodge는 키를 놓을 때 중단하는 hold가 아니므로 Completed/Canceled를 AbilityInputTagReleased/Canceled로 전달하지 않는다. 이것은 X/Y의 정상 Release/Cancel 정리를 생략하라는 뜻이 아니다.

정의할 Dodge callback은 다음과 같다.

```cpp
void AKZPlayerController::Input_DodgeStarted(const FInputActionValue&)
{
    AKZPlayer* PlayerCharacter = Cast<AKZPlayer>(GetPawn());
    UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent();
    UEnhancedPlayerInput* EnhancedPlayerInput = Cast<UEnhancedPlayerInput>(PlayerInput);
    const UKZInputData* InputData =
        UKZAssetManager::GetAssetByName<UKZInputData>(KZGameplayTags::AssetData_InputData);

    if (!IsValid(PlayerCharacter) || !IsValid(ASC) ||
        !IsValid(EnhancedPlayerInput) || !IsValid(InputData))
    {
        return;
    }

    // 과거 Locomotion Intent가 아니라 현재 IA_Move 값을 읽는다.
    const UInputAction* MoveAction =
        InputData->FindInputActionByTag(KZGameplayTags::Input_Action_Move);
    if (!IsValid(MoveAction) || MoveAction->ValueType != EInputActionValueType::Axis2D)
    {
        UE_LOG(LogAbility, Error, TEXT("Dodge needs a valid Axis2D Move action."));
        return;
    }

    const FVector2D MovementInput =
        EnhancedPlayerInput->GetActionValue(MoveAction).Get<FVector2D>();
    const EKZDodgeDirection Direction =
        PlayerCharacter->ResolveDodgeDirection(MovementInput, GetControlRotation());

    // 최초 Dodge는 Combo command 대신 방향 요청 API를 사용한다.
    ASC->TryActivateDirectionalDodge(Direction);
}
```

- FInputActionValue const 참조는 Enhanced Input delegate가 요구하는 인자다. Dodge button의 값 자체는 방향을 담지 않으므로 cpp 정의에서는 이름을 생략했다.
- PlayerCharacter는 현재 GetPawn을 AKZPlayer로 캐스팅한 지역 포인터다. Controller가 Pawn 교체 이후 옛 Player/ASC를 member에 캐시하지 않는다.
- ASC는 현 Pawn의 IAbilitySystemInterface 경로를 쓰는 기존 GetKZAbilitySystemComponent helper다. Unreal engine ASC와 project ASC의 역할을 섞지 않는다.
- EnhancedPlayerInput은 Controller의 PlayerInput 객체를 UEnhancedPlayerInput으로 좁힌 포인터다. InputComponent는 callback binding, PlayerInput은 현재 action value 조회를 맡으므로 서로 대체하지 않는다.
- InputData는 AssetManager가 AssetData.InputData tag로 찾는 DA_InputData다. 물리 key를 C++ 문자열로 박거나 여기에 IA_Move member를 선행 저장하지 않는다.
- 네 포인터가 유효하지 않으면 요청을 만들지 않는다. Cast 실패/null을 검사하고, 존재하지 않는 입력을 임의의 forward 입력으로 바꾸지 않는다.
- MoveAction은 기존 Input.Action.Move lookup의 결과이며 const UInputAction*다. 실제 설정이 Axis2D인지 검사한 뒤 Get<FVector2D>()를 호출한다. 잘못된 asset이면 로그와 return으로 data 오류를 보여 준다.
- GetActionValue는 **현재 Enhanced Input이 평가한 action 값**이다. 장치 원시 전압/키 상태와 같은 값이 아니다. modifier/deadzone/trigger가 적용되며 action이 Triggered가 아니면 0을 반환할 수 있다. 따라서 IA_Move에 불필요한 Hold/Chord trigger를 넣지 않는다. 같은 frame 이동+회피는 실제 엔진 입력 평가와 PIE에서 검증한다.
- MovementInput/Direction은 callback 지역값이다. Direction은 press 때 한 번만 선택되고 선택된 Ability Entry가 이후 방향을 나타낸다. Controller/Player/AnimInstance CurrentDodgeDirection member를 만들지 않는다.
- ASC.TryActivateDirectionalDodge는 성공 여부 bool을 반환한다. 이번 callback은 실패 시 다른 방향을 다시 시도하거나 자동 반복하지 않는다. 중복/누락 grant는 ASC 로그, cost/tag 차단은 GAS gate와 breakpoint에서 확인한다.
- Command.Player.Dodge.A는 이미 등록됐지만 이번 최초 Dodge에는 broadcast하지 않는다. 현재 A Edge 소비자가 없으며 방향 선택이 먼저 필요한 좁은 request이기 때문이다.

ASC header는 새 방향 enum include를 generated.h 위에 추가하고 아래 선언들을 **한 묶음**으로 바꾼다. Controller/ComboAction의 호출·callback도 같은 build 전에 함께 바꿔야 한다.

```cpp
bool TryActivateDirectionalDodge(EKZDodgeDirection Direction);

bool TryActivateComboEntry(
    const UKZComboDefinitionData* Definition,
    FName EntryNodeId,
    FGameplayAbilitySpecHandle IgnoreHandle,
    const FGameplayTag& CommandTag);

DECLARE_EVENT_TwoParams(
    UKZAbilitySystemComponent, FOnComboCommand,
    const FKZComboCommand&, bool&);

void AbilityInputTagPressed(
    const FGameplayTag& InputTag, bool bAllowNewActivation = true);
bool SubmitComboCommand(
    const FGameplayTag& CommandTag, EKZComboCommandPhase Phase);
```

DECLARE_EVENT_TwoParams는 BP dynamic multicast가 아니라 C++ native event다. UKZAbilitySystemComponent가 Broadcast 권한을 소유하고 외부 Ability는 기존 OnComboCommand() accessor로 구독한다. callback에 bool&를 추가하는 이유는 여러 listener의 반환값을 수집하는 별도 manager 없이 이번 동기 요청의 소비 여부를 되돌리기 위해서다. 지역 bool reference를 Task/member에 저장하거나 다음 frame에 쓰면 안 된다.

ASC cpp에 KZDodgeAbility.h, KZGameplayTags.h, LogChannels.h를 포함한다. 전체 첨부는 ComboDefinition include도 Ability/Combo/KZComboDefinitionData.h의 정규 경로로 표시했다. 방향 선택 함수는 다음과 같다.

```cpp
bool UKZAbilitySystemComponent::TryActivateDirectionalDodge(EKZDodgeDirection Direction)
{
    if (static_cast<uint8>(Direction) > static_cast<uint8>(EKZDodgeDirection::LF))
    {
        return false;
    }

    FScopedAbilityListLock AbilityListLock(*this);
    FGameplayAbilitySpec* TargetSpec = nullptr;
    for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
    {
        const UKZDodgeAbility* DodgeDefaults = Cast<UKZDodgeAbility>(AbilitySpec.Ability);
        if (!IsValid(DodgeDefaults) || DodgeDefaults->GetDodgeDirection() != Direction)
        {
            continue;
        }

        if (TargetSpec != nullptr)
        {
            UE_LOG(LogAbility, Error,
                TEXT("Duplicate granted Dodge direction: %d"), static_cast<int32>(Direction));
            return false;
        }
        TargetSpec = &AbilitySpec;
    }

    if (TargetSpec == nullptr)
    {
        UE_LOG(LogAbility, Warning,
            TEXT("No granted Dodge for direction: %d"), static_cast<int32>(Direction));
        return false;
    }

    const FGameplayAbilitySpecHandle TargetHandle = TargetSpec->Handle;
    if (TargetSpec->IsActive())
    {
        UGameplayAbility* PrimaryInstance = TargetSpec->GetPrimaryInstance();
        const UKZActionAbility* ActionInstance = Cast<UKZActionAbility>(PrimaryInstance);
        if (!IsValid(ActionInstance) || !ActionInstance->HasInputEnded())
        {
            return false;
        }

        // 비용/태그/entry를 먼저 검사한다. public base API로 실제 override를 호출한다.
        if (!AbilityActorInfo.IsValid() ||
            !PrimaryInstance->CanActivateAbility(TargetHandle, AbilityActorInfo.Get()))
        {
            return false;
        }

        CancelAbilityHandle(TargetHandle);
        TargetSpec = FindAbilitySpecFromHandle(TargetHandle);
        if (TargetSpec == nullptr || TargetSpec->IsActive())
        {
            return false;
        }
    }

    // Dodge는 A press/release owner가 아니라 방향 요청으로 시작하는 graph-only Spec이다.
    const bool bPreviousInputPressed = TargetSpec->InputPressed;
    TargetSpec->InputPressed = false;
    if (TryActivateAbility(TargetHandle))
    {
        return true;
    }

    if (FGameplayAbilitySpec* FailedSpec = FindAbilitySpecFromHandle(TargetHandle))
    {
        FailedSpec->InputPressed = bPreviousInputPressed;
    }
    return false;
}
```

| 값/호출 | 의미 |
| --- | --- |
| Direction | 요청자가 선택한 enum. LF보다 큰 저장값은 잘못된 enum이므로 false |
| FScopedAbilityListLock | 이 scope의 grant/remove 구조 변경을 엔진 규칙대로 지연. thread mutex가 아님 |
| TargetSpec=nullptr | 아직 방향에 맞는 실행 가능 Spec을 찾지 못한 지역 상태 |
| AbilitySpec.Ability | 해당 granted Ability의 defaults/CDO. 활성 실행 상태 포인터가 아님 |
| DodgeDefaults | 실제 UKZDodgeAbility 파생인지와 authored 방향을 읽는 const 포인터 |
| continue | Dodge가 아니거나 방향이 다른 후보를 건너뜀 |
| 두 번째 TargetSpec | 동일 방향 중복 grant 오류. grant 순서로 임의 선택하지 않음 |
| TargetHandle | callback 이후에도 같은 Spec을 다시 찾을 식별자 |
| PrimaryInstance | 활성인 InstancedPerActor 실행 객체 |
| ActionInstance | 현재 실행의 HasInputEnded를 읽기 위한 좁은 cast |
| CanActivateAbility | 같은 Spec restart 전에 현재 비용/쿨다운/태그/entry 데이터의 사전 검사 |
| CancelAbilityHandle | 기존 activation을 정리. 다음 line에서 실제 종료됐는지 다시 검사 |
| bPreviousInputPressed | activation 거절 시 복구할 Spec 필드의 이전 지역값 |
| TryActivateAbility | 엔진 gate/PreActivate/Activate 경로. true는 활성화 승인 |

같은 방향의 Spec이 active라면 InputEnd 전에는 false다. InputEnd 뒤에는 base public UGameplayAbility 포인터로 CanActivateAbility override를 호출한 다음 cancel/restart한다. project override가 protected여도 base의 public virtual API를 통해 호출할 수 있다. check 뒤의 cancel callback에서 Spec이 제거되거나 아직 active로 남으면 새 실행을 강행하지 않는다. 다른 방향은 target이 inactive이므로 TryActivateAbility의 현재 Action block이 승인 여부를 결정한다.

Dodge Spec은 InputTag가 없는 방향 request이므로 InputPressed=false다. A를 누른 physical owner를 8 Spec 중 하나에 저장해 release로 회피를 끝내는 구조가 아니다. 비용 부족이나 태그 차단에서는 target activation이 거절된다. 같은 Spec의 사전 gate가 통과한 후 OnEnd GE 적용 등으로 조건이 달라질 수 있으므로 완전한 rollback을 보장하는 함수라고 설명하지 않는다.

이제 X/Y command의 소비 여부를 돌려준다. 기존 SubmitComboCommand를 아래 bool 함수로 교체한다.

```cpp
bool UKZAbilitySystemComponent::SubmitComboCommand(
    const FGameplayTag& CommandTag, EKZComboCommandPhase Phase)
{
    if (!CommandTag.IsValid())
    {
        return false;
    }

    switch (Phase)
    {
    case EKZComboCommandPhase::Begin:
        if (HeldComboCommands.HasTagExact(CommandTag))
        {
            return false;
        }
        HeldComboCommands.AddTag(CommandTag);
        break;

    case EKZComboCommandPhase::Release:
        if (!HeldComboCommands.HasTagExact(CommandTag))
        {
            return false;
        }
        HeldComboCommands.RemoveTag(CommandTag);
        break;

    case EKZComboCommandPhase::Cancel:
        HeldComboCommands.RemoveTag(CommandTag);
        break;

    default:
        // InputEnd/HoldCommit/HoldEnd는 Montage에서 Ability로 직접 전달한다.
        return false;
    }

    const FKZComboCommand Command(CommandTag, Phase);
    bool bConsumed = false;
    ComboCommandEvent.Broadcast(Command, bConsumed);

    // 이 지역 bool 참조는 동기 Broadcast 동안만 유효하다.
    return Phase == EKZComboCommandPhase::Begin && bConsumed;
}
```

CommandTag는 물리 Spec lookup인 InputTag와 다르다. X는 Command.Player.Attack.X, Y는 Command.Player.Attack.Y다. Phase는 사건 종류다. 두 인자 모두 ASC가 다른 객체에 저장해 수정하는 인자가 아니다.

- 유효하지 않은 command는 false로 종료한다.
- Begin에서는 held에 이미 있으면 중복 물리 시작으로 거른다. 새 Begin은 HeldComboCommands에 넣은 뒤 방송한다. 예약/Edge 검사가 지금의 held 상태를 읽을 수 있는 순서다.
- Release는 Begin 없이 온 사건을 실행하지 않는다. 정상 Release에서는 held를 먼저 빼서 Release Edge가 자기 버튼을 계속 held라고 보지 않게 한다.
- Cancel도 held를 지우지만 공격 Release Edge를 만들지 않는다. callback은 pending을 버리는 정리 사건으로 해석한다.
- default는 InputEnd/HoldCommit/HoldEnd를 외부 Controller 사건으로 받지 않는다는 경계다. 이 세 phase는 Montage Notify에서 직접 RunHeld로 처리한다.
- Command는 const FKZComboCommand 지역 객체다. native callback의 const&는 이번 Broadcast 중 복사 없이 읽는 payload다.
- bConsumed=false로 시작하고 Broadcast(Command,bConsumed)를 동기 호출한다. listener가 유효 예약/즉시 실행 승인에서만 true로 올린다.
- 반환은 Begin에만 의미 있다. Release/Cancel callback은 소비 bool을 바꾸지 않고 cleanup을 진행한다. 반환값을 무시하던 ClearComboCommands의 기존 호출은 그대로 사용해도 된다.
- HeldComboCommands는 ASC/Pawn 입력 수명 동안 계속 눌린 command 집합이다. 실행 예약 한 칸인 PendingCommandTag와 목적·수명이 다르다. Ability가 끝났다는 이유만으로 현재 물리 held 상태를 지우지 않는다.

KZComboActionAbility.h의 private callback은 다음 signature로 교체한다.

```cpp
void HandleComboCommand(
    const FKZComboCommand& Command, bool& bConsumed);
```

기존 AddUObject/Remove 연결과 FDelegateHandle을 그대로 사용한다. UFUNCTION을 붙일 native callback이 아니다. cpp 함수는 다음과 같다.

```cpp
void UKZComboActionAbility::HandleComboCommand(
    const FKZComboCommand& Command, bool& bConsumed)
{
    if (!IsActive() || !Command.CommandTag.IsValid())
    {
        return;
    }

    switch (Command.Phase)
    {
    case EKZComboCommandPhase::Begin:
        if (bConsumed ||
            ComboWindowPhase == EKZComboWindowPhase::Closed ||
            PendingCommandTag.IsValid() ||
            FindMatchingCommandEdge(Command) == nullptr)
        {
            return;
        }

        PendingCommandTag = Command.CommandTag;
        if (ComboWindowPhase == EKZComboWindowPhase::OpenToCommit)
        {
            // 유효한 예약으로 이번 press를 소비한다. target은 아직 시작하지 않는다.
            bConsumed = true;
        }
        else
        {
            const bool bExecuted = CommitPendingCommand();
            bConsumed = bConsumed || bExecuted;
        }
        return;

    case EKZComboCommandPhase::Release:
        // 버튼 Release는 일반 Begin buffer를 거치지 않는다.
        RunCommand(Command);
        return;

    case EKZComboCommandPhase::Cancel:
        if (PendingCommandTag == Command.CommandTag)
        {
            ClearPendingCommand();
            return;
        }
        if (PendingCommandTag.IsValid())
        {
            const FKZComboCommand PendingCommand(
                PendingCommandTag, EKZComboCommandPhase::Begin);
            if (FindMatchingCommandEdge(PendingCommand) == nullptr)
            {
                ClearPendingCommand();
            }
        }
        return;

    default:
        return;
    }
}
```

첫 guard는 이미 끝난 실행과 비어 있는 command를 거른다. Begin의 bConsumed는 다른 listener가 이미 선택한 같은 press를 다시 실행하지 않게 한다. Closed면 창 밖이고, PendingCommandTag가 valid면 한 칸 예약이 이미 찼다. FindMatchingCommandEdge==nullptr는 command/phase/held/hold/move/해금/target 재생 가능 조건을 통과한 Edge가 없다는 뜻이다.

PendingCommandTag=Command.CommandTag는 태그 하나를 저장한다. OpenToCommit에서 bConsumed=true는 **예약 승인**이다. InputCommit Notify가 아직 오지 않았으므로 target이 시작됐다는 뜻은 아니다. CommitToEnd라면 CommitPendingCommand()가 지금 재검사/실행한 결과만 OR로 더한다. 이미 true인 결과를 false로 내리지 않는다. bConsumed||CommitPendingCommand()처럼 쓰면 이미 true일 때 함수 호출이 생략되므로 실행 결과를 지역 bool로 먼저 받는다.

Release는 RunCommand로 즉시 처리하며 일반 Begin 입력창과 한 칸 buffer를 거치지 않는다. Cancel은 자기 pending을 지우고, 다른 버튼 취소가 RequiredHeldCommands 조건을 깨면 그 pending도 지운다. Cancel에서 special attack을 실행하지 않는다. 예약된 Begin은 정상 Release만으로 무조건 제거하지 않으며, Cancel과 다른 사건이다.

OpenToCommit에서 소비됐던 Begin이 나중 InputCommit 재검사에서 비용/해금 변화 때문에 실패해도 과거 press를 일반 공격으로 다시 재생하지 않는다. 즉시 실행 실패에서는 false를 반환해 같은 현재 press의 generic fallback을 허용한다. 다만 InputEnd 전에는 현재 Action block이 generic 신규 실행을 거절한다. 이것을 두 번째 공격 자동 예약이라고 설명하지 않는다.

Controller의 RouteAttackInput과 두 wrapper를 교체한다. 기존 Weak/Strong Started/Completed/Canceled는 그대로 이 함수를 호출한다.

```cpp
void AKZPlayerController::RouteAttackInput(
    const FGameplayTag& InputTag,
    const FGameplayTag& CommandTag,
    EKZComboCommandPhase CommandPhase)
{
    switch (CommandPhase)
    {
    case EKZComboCommandPhase::Begin:
    {
        // 먼저 graph에 기회를 주고, 소비 여부로 신규 일반 실행만 중재한다.
        const bool bConsumed = SubmitComboCommand(CommandTag, CommandPhase);
        AbilityInputTagPressed(InputTag, !bConsumed);
        break;
    }

    case EKZComboCommandPhase::Release:
        SubmitComboCommand(CommandTag, CommandPhase);
        AbilityInputTagReleased(InputTag);
        break;

    case EKZComboCommandPhase::Cancel:
        SubmitComboCommand(CommandTag, CommandPhase);
        AbilityInputTagCanceled(InputTag);
        break;

    default:
        return;
    }
}
```
```cpp
bool AKZPlayerController::SubmitComboCommand(
    const FGameplayTag& CommandTag, EKZComboCommandPhase CommandPhase)
{
    if (UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent())
    {
        return ASC->SubmitComboCommand(CommandTag, CommandPhase);
    }
    return false;
}
```
```cpp
void AKZPlayerController::AbilityInputTagPressed(
    const FGameplayTag& InputTag, bool bAllowNewActivation)
{
    if (UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent())
    {
        ASC->AbilityInputTagPressed(InputTag, bAllowNewActivation);
    }
}
```

Begin case의 중괄호는 switch의 지역 bConsumed 수명을 그 case 안으로 제한한다. Command가 먼저 처리되면 현재 Dodge node의 해금 Edge가 먼저 선택된다. !bConsumed는 소비됐을 때 false, 소비되지 않았을 때 true다. 새 일반 공격을 시작할 권한만 바꾼다. Release와 Cancel은 기존 command 선행 순서를 유지한다. 각각 generic Release Task가 Ability를 끝내기 전에 graph 사건을 평가하고, generic cancel 전에 held/pending을 정리한다.

wrapper의 bool return은 ASC가 없으면 false, 있으면 소비 결과 그대로다. Press wrapper는 bAllowNewActivation을 그대로 전달한다. default=true는 다른 기존 C++ caller가 한 인자 press를 쓸 때 원래 진입 동작을 유지하기 위한 API 기본값이다. Controller 라우팅에서는 인자를 명시한다. GetKZAbilitySystemComponent는 기존처럼 현재 Pawn의 ASC를 조회한다.

ASC의 AbilityInputTagPressed도 반드시 같이 교체한다. false를 inactive 후보에만 적용하면 InputEnd 후 active Spec cancel/restart가 여전히 실행돼 같은 press를 두 번 사용할 수 있다.

```cpp
void UKZAbilitySystemComponent::AbilityInputTagPressed(
    const FGameplayTag& InputTag, bool bAllowNewActivation)
{
    if (!InputTag.IsValid())
    {
        return;
    }

    FScopedAbilityListLock AbilityListLock(*this);
    for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
    {
        if (!AbilitySpec.Ability || !AbilitySpec.IsActive() ||
            !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
        {
            continue;
        }

        UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance();
        if (!IsValid(PrimaryInstance))
        {
            UE_LOG(LogAbility, Error,
                TEXT("Input Ability must use InstancedPerActor: %s"),
                *GetNameSafe(AbilitySpec.Ability));
            return;
        }

        const UKZActionAbility* ActionInstance = Cast<UKZActionAbility>(PrimaryInstance);
        if (bAllowNewActivation && IsValid(ActionInstance) && ActionInstance->HasInputEnded())
        {
            const FGameplayAbilitySpecHandle RestartHandle = AbilitySpec.Handle;
            if (!AbilityActorInfo.IsValid() ||
                !PrimaryInstance->CanActivateAbility(RestartHandle, AbilityActorInfo.Get()))
            {
                return;
            }

            CancelAbilityHandle(RestartHandle);
            FGameplayAbilitySpec* RestartSpec = FindAbilitySpecFromHandle(RestartHandle);
            if (RestartSpec == nullptr || RestartSpec->IsActive())
            {
                return;
            }

            RestartSpec->InputPressed = true;
            if (!TryActivateAbility(RestartHandle))
            {
                if (FGameplayAbilitySpec* FailedSpec = FindAbilitySpecFromHandle(RestartHandle))
                {
                    FailedSpec->InputPressed = false;
                }
            }
            return;
        }

        // 콤보가 소비했어도 활성 Spec의 GAS press protocol은 유지한다.
        const FGameplayAbilitySpecHandle ActiveHandle = AbilitySpec.Handle;
        AbilitySpec.InputPressed = true;
        AbilitySpecInputPressed(AbilitySpec);

        FGameplayAbilitySpec* ActiveSpec = FindAbilitySpecFromHandle(ActiveHandle);
        if (ActiveSpec != nullptr && ActiveSpec->IsActive())
        {
            InvokeReplicatedEvent(
                EAbilityGenericReplicatedEvent::InputPressed,
                ActiveHandle,
                PrimaryInstance->GetCurrentActivationInfo().GetActivationPredictionKey());
        }
        return;
    }

    if (!bAllowNewActivation)
    {
        return;
    }

    for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
    {
        if (!AbilitySpec.Ability || AbilitySpec.IsActive() ||
            !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
        {
            continue;
        }

        const FGameplayAbilitySpecHandle CandidateHandle = AbilitySpec.Handle;
        AbilitySpec.InputPressed = true;
        if (TryActivateAbility(CandidateHandle))
        {
            return;
        }
        if (FGameplayAbilitySpec* FailedSpec = FindAbilitySpecFromHandle(CandidateHandle))
        {
            FailedSpec->InputPressed = false;
        }
    }
}
```

- InputTag.IsValid와 HasTagExact는 정확한 physical binding 하나를 고른다. Gameplay parent match로 다른 입력을 함께 실행하지 않는다.
- 첫 loop는 active Spec을 먼저 찾는다. PrimaryInstance는 실행 객체다. 현재 KZAction은 InstancedPerActor이므로 없으면 설정 오류 로그와 return이다.
- ActionInstance는 HasInputEnded만 읽는다. bAllowNewActivation=true **그리고** InputEnd 이후일 때만 restart를 시도한다. false일 때 같은 Spec restart도 못 한다.
- RestartHandle로 비용/태그/entry를 먼저 검사하고 기존 activation을 cancel한 뒤 다시 찾아 실제 inactive인지 확인한다. 성공하면 새 activation은 InputPressed=true로 시작한다. 실패하면 handle로 찾은 새 후보의 눌림 상태를 해제하며 같은 입력의 다른 후보로 넘어가지 않는다.
- 그 밖의 active branch는 Spec.InputPressed=true, AbilitySpecInputPressed, InvokeReplicatedEvent를 전달한다. 콤보가 소비했다는 이유로 활성 GAS input protocol을 끊지 않는다.
- callback에서 종료/제거될 수 있으므로 ActiveHandle로 다시 찾고 active인 경우에만 generic event를 호출한다. ActivationPredictionKey는 현재 GAS 실행을 식별하는 기존 키이며 새 gameplay 방향 ID가 아니다. LocalOnly인 현 프로젝트에서도 기존 GAS 입력 Task protocol을 유지한다.
- active owner가 없고 bAllowNewActivation=false면 return한다. 따라서 graph-only special이 시작된 같은 X/Y press로 ordinary Weak/Strong Spec을 추가로 시작하지 않는다.
- true이면 두 번째 loop가 inactive의 정확한 InputTag 후보를 grant 순서대로 TryActivate한다. 성공한 한 개에서 return한다. 거절한 후보의 InputPressed를 false로 돌린다. 실패한 후보가 버튼 release owner로 남지 않게 한다.
- 이것은 generic priority manager가 아니다. 현재 동일 입력 후보의 기존 grant-order와 active ownership을 보존하는 작은 API 보정이다.


다른 Entry Ability로 넘길 때 입력 소유권도 맞춘다. KZComboActionAbility.ApplyEdge는 현재 target이 다른 granted ComboAction Entry인지 확인한다. 현재 Source의 마지막 인자 bool을 실제 CommandTag로 바꾸며, 함수 전체 맥락은 다음과 같다.

```cpp
bool UKZComboActionAbility::ApplyEdge(const FKZComboCommandEdge& Edge, const FKZComboCommand& Command)
{
	// TargetNodeId가 다른 granted Ability의 Entry인지 먼저 확인한다.
	// Entry가 아니면 현재 Ability 안의 일반 노드 전환으로 처리한다.
	UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo());
	
	if (!IsValid(ASC))
	{
		return false;
	}
	
	const FGameplayAbilitySpecHandle SourceHandle = GetCurrentAbilitySpecHandle();
	
	if (!ASC->HasComboEntry(ComboDefinition, Edge.TargetNodeId, SourceHandle))
	{
		// 다른 entry Ability가 없으면 현재 Ability 내부 Node다.
		return TransitionToNode(Edge.TargetNodeId);
	}
	
	const bool bWasBlocking = IsBlockingOtherAbilities();

	// StrongCharge early Release는 InputEnd 전이므로
	// source block을 잠시 풀어야 StrongAttack을 시작할 수 있다.
	if (bWasBlocking)
	{
		SetShouldBlockOtherAbilities(false);
	}
	
	const bool bActivated = ASC->TryActivateComboEntry(
		ComboDefinition,
		Edge.TargetNodeId,
		SourceHandle,
		Command.CommandTag);
	
	if (!bActivated)
	{
		if (IsActive() && bWasBlocking)
		{
			SetShouldBlockOtherAbilities(true);
		}
		
		return false;
	}
	
	// Target의 CancelAbilitiesWithTag가 source를 취소하는 것이 정상이다.
	// 잘못된 Blueprint 설정으로 source가 남았다면 여기서 정리한다.
	if (IsActive())
	{
		FinishAbility(false);
	}

	return true;
}
```

- Edge와 Command는 const 참조로 읽기만 한다. Edge는 공유 DataAsset의 authored 규칙이고 Command는 현재 사건이다.
- ASC가 없으면 false다. SourceHandle은 현재 실행의 Spec ID다. HasComboEntry는 같은 Definition pointer와 target EntryNodeId를 사용하는 **다른** granted Ability를 찾는다.
- 다른 Entry가 없다면 TransitionToNode를 호출한다. 이것은 같은 Montage의 local section 전환이다. 다른 Montage의 special node는 target grant가 빠지면 이 경로에서 거절되므로 CharacterDefinition 설정이 필수다. grant 누락을 해금 정책으로 사용하지 않는다.
- bWasBlocking은 source가 지금 다른 Action들을 block하는지 저장한 지역 bool이다. handoff 순간만 SetShouldBlockOtherAbilities(false)로 source의 block을 풀어 target을 검사한다. 이동/regen OwnedTags를 일괄 제거하는 코드가 아니다.
- TryActivateComboEntry에 Definition/TargetNodeId/SourceHandle/**Command.CommandTag**를 넘긴다. 기존 bInputPressed 지역 bool 계산은 삭제한다. 어떤 물리 버튼의 소유권인지 ASC가 판단할 정보를 보낸다.
- false이면 아직 살아 있는 source의 기존 block을 복구하고 false를 반환한다. 비용/태그/entry 사전 거절에서 Dodge를 먼저 끝내지 않는 경로다.
- true이면 target의 CancelAbilitiesWithTag가 source를 이미 끝냈을 수 있다. 남아 있는 경우에만 FinishAbility(false)로 정리한다. 후속 Montage Task 시작 실패까지 돌려 주는 transaction으로 해석하지 않는다.
- local 전환의 ApplyCost와 새 target activation의 CommitCost는 서로 다른 경로다. handoff 뒤 source에서 또 ApplyCost를 호출해 target 비용을 중복 청구하지 않는다.

ASC.TryActivateComboEntry의 전체 교체안이다.

```cpp
bool UKZAbilitySystemComponent::TryActivateComboEntry(
    const UKZComboDefinitionData* Definition,
    FName EntryNodeId,
    FGameplayAbilitySpecHandle IgnoreHandle,
    const FGameplayTag& CommandTag)
{
    if (!IsValid(Definition) || EntryNodeId.IsNone())
    {
        return false;
    }

    FScopedAbilityListLock AbilityListLock(*this);
    FGameplayAbilitySpec* TargetSpec = nullptr;

    for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
    {
        if (!AbilitySpec.Ability || AbilitySpec.Handle == IgnoreHandle)
        {
            continue;
        }

        const UKZComboActionAbility* ComboAbility =
            Cast<UKZComboActionAbility>(AbilitySpec.Ability);
        if (!IsValid(ComboAbility) ||
            ComboAbility->GetComboDefinition() != Definition ||
            ComboAbility->GetEntryNodeId() != EntryNodeId)
        {
            continue;
        }

        if (TargetSpec != nullptr)
        {
            UE_LOG(LogAbility, Error,
                TEXT("Duplicate granted Combo Entry: %s"), *EntryNodeId.ToString());
            return false;
        }
        TargetSpec = &AbilitySpec;
    }

    if (TargetSpec == nullptr || TargetSpec->IsActive())
    {
        return false;
    }

    // 실제 소비자가 있는 X/Y만 물리 입력 binding으로 대응시킨다.
    FGameplayTag InputTag;
    if (CommandTag == KZGameplayTags::Command_Player_Attack_X)
    {
        InputTag = KZGameplayTags::Input_Action_X;
    }
    else if (CommandTag == KZGameplayTags::Command_Player_Attack_Y)
    {
        InputTag = KZGameplayTags::Input_Action_Y;
    }

    const bool bTargetOwnsInput =
        InputTag.IsValid() &&
        IsComboCommandHeld(CommandTag) &&
        TargetSpec->GetDynamicSpecSourceTags().HasTagExact(InputTag);

    const FGameplayAbilitySpecHandle TargetHandle = TargetSpec->Handle;
    const bool bPreviousTargetInputPressed = TargetSpec->InputPressed;
    FGameplayAbilitySpec* SourceSpec = FindAbilitySpecFromHandle(IgnoreHandle);
    const bool bTransferSourceInput =
        bTargetOwnsInput &&
        SourceSpec != nullptr &&
        SourceSpec->InputPressed &&
        SourceSpec->GetDynamicSpecSourceTags().HasTagExact(InputTag);

    // 같은 버튼 handoff의 이전 owner를 남기면 Released가 이전 Spec에서 반환한다.
    if (bTransferSourceInput)
    {
        SourceSpec->InputPressed = false;
    }
    TargetSpec->InputPressed = bTargetOwnsInput;

    if (TryActivateAbility(TargetHandle))
    {
        // GAS activation 승인이다. 이후 Commit/Task 성공의 transaction 보장은 아니다.
        return true;
    }

    // callback 뒤에는 이전 포인터를 계속 사용하지 않고 Handle로 다시 찾는다.
    if (FGameplayAbilitySpec* FailedTarget = FindAbilitySpecFromHandle(TargetHandle))
    {
        FailedTarget->InputPressed = bPreviousTargetInputPressed;
    }
    if (bTransferSourceInput)
    {
        if (FGameplayAbilitySpec* PreviousSource = FindAbilitySpecFromHandle(IgnoreHandle))
        {
            PreviousSource->InputPressed = true;
        }
    }
    return false;
}
```

이 함수가 읽는 Definition/EntryNodeId는 target을 정확하게 선택하는 두 조건이다. IgnoreHandle은 현재 source를 후보에서 제외하고 나중 소유권을 옮길 Spec을 찾는 ID다. CommandTag는 이벤트의 의미다. const 포인터/const 참조를 사용해 공유 graph와 command를 수정하지 않는다.

첫 loop는 common ComboAction CDO를 cast하고 동일 Definition+Entry인지 비교한다. 다른 BP가 같은 Entry를 중복 grant하면 로그/false다. TargetSpec이 없거나 이미 active면 새 target으로 넘기지 않는다. TargetHandle은 callback 뒤 재조회용이며 TargetSpec pointer와 수명이 같다고 가정하지 않는다.

| 지역 변수 | 타입 / 초기값 | 작성·읽기·정리 의도 |
| --- | --- | --- |
| TargetSpec | FGameplayAbilitySpec*, nullptr | 일치 후보 하나를 선택, scope 종료 시 지역 포인터 폐기 |
| InputTag | FGameplayTag, invalid | 현재 X/Y command의 실제 입력 tag만 대응 |
| bTargetOwnsInput | bool | tag valid + 해당 command held + target binding exact 일치 |
| TargetHandle | FGameplayAbilitySpecHandle | 활성화/실패 callback 뒤 같은 target 조회 |
| bPreviousTargetInputPressed | bool | target의 이전 눌림 값, activation 거절 시 복구 |
| SourceSpec | FGameplayAbilitySpec* | IgnoreHandle로 찾은 이전 owner |
| bTransferSourceInput | bool | 같은 physical binding의 실제 눌림 owner를 옮길 때만 true |
| FailedTarget/PreviousSource | Spec 포인터, callback 뒤 조회 | 실패 복구 시 오래된 참조를 쓰지 않음 |

X command를 Input.Action.X로, Y를 Input.Action.Y로 대응한다. 지금 실제 소비자가 있는 두 경우만 쓰고 미사용 범용 map DataAsset/helper를 만들지 않는다. 이후 새로운 physical command가 같은 입력 수명 계약을 실제로 소비하면 해당 대응을 늘린다.

graph-only DodgeAttack은 DynamicSpecSourceTags에 Input.Action.X/Y가 없다. 버튼이 held여도 bTargetOwnsInput=false이므로 Spec.InputPressed=false다. special의 node가 hold를 읽어야 하는 경우 기존 ASC held command 집합으로 판단한다. 실제 binding이 있는 StrongCharge 등은 command가 그 binding과 맞고 버튼이 아직 held일 때만 true다.

같은 버튼을 사용하는 source→target에서 source.InputPressed를 false로 해야 한다. 기존 Released는 grant 순서로 InputPressed인 Spec 하나를 찾고, 그 Spec이 inactive여도 정리 후 바로 반환한다. source가 true로 남아 있으면 inactive source에서 함수가 끝나 새 target의 WaitInputRelease를 깨우지 못한다. 반대로 source가 Y를 소유하고 X target으로 이동하면 Y owner는 건드리지 않는다. X/Y 서로의 release/cancel을 혼동하면 안 된다.

Release Edge에서 넘어가는 경우에는 ASC가 held를 먼저 지웠으므로 target은 held owner가 아니다. source의 physical Released 정리는 뒤따르는 generic release에서 실행된다. bTransferSourceInput은 현재 target이 실제 held owner일 때만 source를 지우므로 이 경로의 cleanup도 보존된다.

TryActivate 거절 시 target의 이전 값과 실제 이관했던 source의 true를 handle 재조회로 복구한다. PreActivate/Activate 이후 source가 취소되고 target Task가 바로 실패하는 특수 경우의 원상 복구는 이 함수가 보장하지 않는다. 지금 데이터 검증과 CanActivate를 앞에 두는 이유가 이 실패 범위를 줄이기 위해서다.

공통 ComboAction의 기존 함수와 상태는 다음처럼 연결된다. 전체 KZComboActionAbility.cpp.txt도 첨부돼 있다. 남은 이름 KZComboAttackAbilityPrivate와 ComboAttackMontage는 기존 내부 namespace/Task 이름이며 Ability.Action.Attack tag를 부여하는 코드가 아니다. 이번 절차에서는 symbol rename refactor를 섞지 않는다.

| 함수 | 호출자 / 의도 / 반환 및 수명 |
| --- | --- |
| constructor | common defaults. Block.Movement.Input/Block.StaminaRegen ActivationOwnedTags |
| GetComboDefinition const | ASC가 shared graph pointer를 읽음, asset을 수정하지 않음 |
| GetEntryNodeId const | ASC가 target 진입 ID를 값으로 읽음 |
| CanActivateAbility const | GAS/restart 사전 검사. Super의 cost/cooldown/tags+ASC/Anim/Entry/section 유효성. 상태를 쓰지 않음 |
| ActivateAbility | 엔진 PreActivate 이후. 이전 delegate/state 정리→data 재검사→Commit→command bind→Move task→Notify bind→entry Montage |
| StartEntryMontage | entry Montage/section으로 PlayMontageAndWait. CurrentNodeId/Task/callback을 ReadyForActivation보다 먼저 저장. 시작 실패/종료면 false |
| HandleComboCommand | ASC native event. Begin 예약/즉시 실행, Release 즉시, Cancel cleanup. 소비 bool true만 상승 |
| FindMatchingCommandEdge const | 현재 node의 authored 배열 순서에서 첫 MatchesEdge pointer, 없으면 nullptr |
| MatchesEdge const | command/phase/hold/move/추가 held/OwnerTagRequirements/target 재생 가능을 모두 검사 |
| IsHoldType const | bHoldCommitted로 Before/After, Any는 통과. 시간 측정 함수 아님 |
| IsMoveType const | 현재 Locomotion intent/gait로 Run vs NonRun. actual velocity나 옛 입력을 대입하지 않음 |
| RunCommand | 현재 사건의 첫 Edge를 찾아 ApplyEdge, 없으면 false |
| ApplyEdge | local section 전환 또는 다른 granted Entry activation. 실패 시 source block 복구 |
| CommitPendingCommand | pending을 지역 복사→한 칸 지움→Begin 조건 재검사/RunCommand. 실패를 자동 재시도하지 않음 |
| RunHeld | InputEnd/HoldCommit/HoldEnd phase에서 authored Edge 순서+held를 검사. 첫 matching Edge의 실행 결과를 반환 |
| TransitionToNode | 같은 Montage 유효 target 및 재생 소유권/cost를 먼저 검사. ApplyCost→새 state/reset→inertialization→ID→section jump |
| IsNodePlayable const | NodeId/Montage/Section 및 GetSectionIndex. root motion/원작 타이밍 검증 함수는 아님 |
| HandleMontageNotifyBegin | AnimInstance dynamic callback. 현재 Montage인지 확인한 뒤 ProcessMontageNotify |
| IsNotifyFromCurrentMontage const | Payload.SequenceAsset/현재 node Montage/AnimInstance current Montage 비교. 실행 instance ID 검증까지 확장하지 않음 |
| ProcessMontageNotify | InputOpen/Commit/End와 HoldCommit/HoldEnd를 해당 state/RunHeld로 해석 |
| HandleMoveInput | Move GameplayEvent. InputEnd 뒤에만 관성화/몽타주 종료→Finish. payload의 방향을 쓰지 않음 |
| BindComboCommandDelegate | 현재 ASC의 OnComboCommand에 AddUObject와 Handle 저장. 과거 command를 재방송하지 않음 |
| UnbindComboCommandDelegate | 현재 handle만 Remove하고 Reset. 다른 listener를 지우지 않음 |
| BindMontageNotifyDelegate | 선택한 AnimInstance의 OnPlayMontageNotifyBegin에 AddUniqueDynamic |
| UnbindMontageNotifyDelegate | 같은 AnimInstance의 자기 callback만 RemoveDynamic 후 weak reset |
| ClearPendingCommand | 한 칸 PendingCommandTag를 invalid로 reset |
| ResetRuntimeState | pending/CurrentNodeId/window/hold 초기화. ASC held나 authored asset은 지우지 않음 |
| HandleMontageCompleted | 자연 완료 callback, FinishAbility(false) |
| HandleMontageAborted | cancel/interrupt callback, FinishAbility(true) |
| FinishAbility | 아직 active일 때만 현재 handle/ActorInfo/ActivationInfo로 EndAbility |
| EndAbility | command/notify unbind→runtime reset→Super(owned tags/tasks/action cleanup)→ActiveMontageTask=null |

RunHeld는 첫 matching Edge의 ApplyEdge가 실패해도 다음 낮은 우선순위 Edge를 다시 실행하지 않는 현재 정책이다. tag 조건이 다른 locked fallback과 cost 실패 fallback을 같은 것으로 생각하지 않는다. 해금 tag 두 종류와 RequiredHeldCommands는 정확히 같은 이름을 두 입력에 반복 기재하는 칸이 아니다.

| 공통 멤버 | 타입 / 초기값 / 단위 | 작성자·소비자·Reset |
| --- | --- | --- |
| ComboDefinition | TObjectPtr<DataAsset>, nullptr | BP 작성, CanActivate/graph/ASC 읽음. 실행마다 변경/Reset 안 함 |
| EntryNodeId | FName, None | BP 작성, 시작/ASC 조회. 실행 reset 대상 아님 |
| ComboTransitionInertializationDuration | float=0.08 s | 기존 임시 튜닝값, local section 전환에서 소비. 원작 근거 미확인, 이번에 변경 안 함 |
| LocomotionExitInertializationDuration | float=0.24 s | 기존 임시 튜닝값, Move로 빠질 때 소비. 별도 원작 확인 없음 |
| ActiveMontageTask | UPROPERTY Transient TObjectPtr, nullptr | 시작 시 자기 Task, End 뒤 nullptr. Task 수명은 GAS에 연결 |
| BoundAnimInstance | TWeakObjectPtr | Notify bind 때 저장, unbind 때 reset. Actor/Anim 수명을 연장하지 않음 |
| ComboCommandDelegateHandle | FDelegateHandle, invalid | native bind 결과, remove/reset용. Gameplay 실행 ID 아님 |
| PendingCommandTag | FGameplayTag, invalid | 유효 Begin 한 칸. Commit/Cancel/새 node/End에서 clear |
| CurrentNodeId | FName, None | Ready 전에 entry, Jump 전에 target. End/new reset에서 None |
| ComboWindowPhase | enum Closed | Open→OpenToCommit, Commit→CommitToEnd, End/new reset→Closed |
| bHoldCommitted | bool=false | HoldCommit=true, 새 node/End=false. 원작 charge 시간 자체 아님 |
| KZAction의 bInputEnded | bool=false | InputEnd=true, 새 local node ResetInputEnd/End=false. 버튼 release와 다름 |
| ASC HeldComboCommands | FGameplayTagContainer, empty | Submit Begin 추가/Release·Cancel 제거, 수명 끝 Clear |
| ASC ComboCommandEvent | native event | ASC 동기 broadcast, 각 active Ability가 자기 handle로 bind/unbind |

ProcessMontageNotify의 상태 변화도 명확히 구분해야 한다.

| Notify | 변화 | 이번 Dodge 결과 |
| --- | --- | --- |
| InputOpen | pending clear, OpenToCommit | 이때부터 유효 X/Y를 한 칸 예약 |
| InputCommit | OpenToCommit일 때 CommitToEnd, CommitPendingCommand | 이미 예약한 Begin을 재검사하고 실행 |
| InputEnd | pending clear, Closed, SetInputEnded, RunHeld(InputEnd) | Begin 특별 공격창 종료, 일반 Action 교체 허용 |
| HoldCommit | bHoldCommitted=true, RunHeld | 기존 charge용. 이번 기본 Dodge에 추가 안 함 |
| HoldEnd | RunHeld | 기존 charge용. 기본 Dodge에 추가 안 함 |

InputEnd는 Ability가 즉시 끝나는 Notify가 아니다. Action block은 풀리지만 ActivationOwnedTags는 Ability 종료까지 유지된다. Move가 계속 들어오면 기존 HandleMoveInput이 종료를 요청하고, 새 Action activation이면 CancelAbilitiesWithTag가 종료시키며, 아무 입력이 없으면 Montage 완료에서 자연 종료한다. Normal 이동 차단이 Root Motion을 없애는 것은 아니다.

빙의 종료와 EndPlay를 닫는다. Character cpp에 KZGameplayTags.h를 추가한 뒤 다음 두 함수로 비교 적용한다.

```cpp
void AKZCharacter::UnPossessed()
{
    if (UKZAbilitySystemComponent* ASC =
        Cast<UKZAbilitySystemComponent>(AbilitySystemComponent))
    {
        // ActorInfo가 유효한 동안 Action 수명부터 닫는다.
        FGameplayTagContainer ActionTags;
        ActionTags.AddTag(KZGameplayTags::Ability_Action);
        ASC->CancelAbilities(&ActionTags);
        ASC->ClearComboCommands();
    }

    Super::UnPossessed();
    if (AbilitySystemComponent->GetAvatarActor_Direct() == this)
    {
        AbilitySystemComponent->RefreshAbilityActorInfo();
    }
}
```
```cpp
void AKZCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    AbilitySystemComponent->DestroyActiveState();
    if (UKZAbilitySystemComponent* ASC =
        Cast<UKZAbilitySystemComponent>(AbilitySystemComponent))
    {
        ASC->ClearComboCommands();
    }
    Super::EndPlay(EndPlayReason);
}
```

ActionTags는 이번 scope에서 만든 FGameplayTagContainer다. Ability.Action AssetTag 계열에 CancelAbilities를 먼저 요청하고, 아직 ActorInfo가 유효할 때 Task/Notify/OwnedTags를 정리한다. ClearComboCommands는 held에 Cancel 사건을 보내고 Spec.InputPressed를 비운다. 정상 Release 공격을 만들지 않는다. Super::UnPossessed 후 기존 Avatar가 여전히 자기 Character이면 ActorInfo를 Refresh한다.

Player::UnPossessed의 raw intent/Sprint/LockOn constraint cleanup은 이미 있고 보존한다. 이번에 Player 쪽에 ASC reset을 중복 추가하지 않는다. EndPlay는 기존 DestroyActiveState를 유지하고 command 기록도 비운 다음 Super를 호출한다. 다른 원인의 tag count를 RemoveAll/일괄 RemoveLoose로 삭제하지 않는다. 현재 Action은 cancelable 기본 실행을 사용하며 나중 커스텀 취소 거절을 넣으면 수명 계약도 함께 검증해야 한다.

해금 native tag를 등록한다. 기존 WeakAttack05 태그를 삭제하거나 대신 사용하지 않는다. 아래 두 선언은 namespace KZGameplayTags의 Unlock 영역에 추가한다.

```cpp
UE_DECLARE_GAMEPLAY_TAG_EXTERN(Unlock_Skill_DAS_DodgeAttack_Weak);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(Unlock_Skill_DAS_DodgeAttack_Strong);
```

cpp도 같은 namespace에 추가한다.

```cpp
UE_DEFINE_GAMEPLAY_TAG(
    Unlock_Skill_DAS_DodgeAttack_Weak, "Unlock.Skill.DAS.DodgeAttack.Weak");
UE_DEFINE_GAMEPLAY_TAG(
    Unlock_Skill_DAS_DodgeAttack_Strong, "Unlock.Skill.DAS.DodgeAttack.Strong");
```

선언/등록은 tag 사전을 만드는 작업이다. 캐릭터를 해금시키는 작업이 아니다. ASC가 그 tag를 **소유**해야 OwnerTagRequirements와 ActivationRequiredTags가 통과한다. 두 문자열은 프로젝트 semantic 명칭이며 원작 내부 tag를 추출한 결과가 아니다. AssetTags에 같은 문자열을 붙여도 해금 소유 사실이 되지 않는다.


소스 변경을 모두 적용한 뒤 저장하고, 사용자가 에디터를 정상 종료한 상태에서 Development Editor cold build를 실행한다. 새 UENUM/UPROPERTY/signature는 Live Coding 결과만으로 BP 직렬화 반영까지 확인했다고 보지 않는다.

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" KhazanEditor Win64 Development "-Project=C:\Users\user\Desktop\GitProject\Khazan\Khazan\Khazan.uproject" -WaitMutex -NoHotReloadFromIDE
```

이번 어시스턴트 작업은 이 build를 실행하지 않았다. 기존 기록의 Editor DLL LNK1104는 실행 중 DLL 점유였다. 새 오류가 나오면 첫 C++/UHT 오류를 현재 변경과 비교한다. 이 안내가 Game target의 기존 InterchangeResult.h 문제를 해결했다는 뜻은 아니다.

새 Editor를 켜고 기존 Weak/Strong/Charge BP와 Dodge BP 8개를 Compile/Save한다. 기존 X/Y press, 연타, charge early release, held handoff의 release/cancel을 먼저 확인한다. 새 Dodge 데이터를 추가하기 전 기존 콤보의 입력 경로가 맞는지 구분하는 순서다.

IA_Dodge를 생성한다.

1. Content Browser에서 /Game/Input에 Input Action asset IA_Dodge를 만든다. Value Type=Boolean으로 둔다. 최초 회피 요청은 Started를 사용하므로 추가 Hold/Chord trigger가 필요 없다.
2. 기존 /Game/Input/IMC_Default에 IA_Dodge mapping을 추가한다. Gamepad Face Button Bottom을 A 동작에 연결하고, 키보드 입력은 중복 없는 원하는 키를 선택한다. 이 물리키는 프로젝트 설정이며 원작 키 binding 확인으로 표현하지 않는다.
3. /Game/Data/DA_InputData의 Input Actions 배열에 한 행을 추가한다. InputTag=Input.Action.A, InputAction=/Game/Input/IA_Dodge다. 다른 Move/Sprint/X/Y 행은 기존대로 둔다.
4. 기존 /Game/Input/Locomotion/IA_Move가 Value Type=Axis2D인지 확인한다. 현재 W/S가 X, D/A가 Y가 되는 기존 IMC modifier 규칙을 기준으로 검사한다. 같은 frame Move+Dodge와 no-input Dodge도 시험한다.
5. FindInputActionByTag는 이 DataAsset의 tag→InputAction lookup이다. InitialAbilityGrant.InputTag와는 다른 곳이다. A 행을 InputData에 추가했다고 8 Dodge Spec을 grant한 것이 아니다.

Dodge Montage를 만든다.

1. /Game/_Art/Player/Animation/InGame/DAS/Dodge의 CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1에서 Anim Montage를 생성하고 같은 폴더에 AM_DAS_Dodge로 저장한다.
2. 아래 M1 sequence 8개만 순서대로 DefaultGroup.DefaultSlot track에 놓는다. unmarked Off_Dodge_L/R나 NonCombat/Start 후보를 섞지 않는다. 각 segment는 대응 sequence 한 번을 재생하는 범위로 둔다.
3. 각 segment 시작에 section을 만들고 아래 SectionName으로 지정한다. 첫 Default section도 Dodge_F로 이름을 맞춘다. NodeId와 SectionName은 다른 필드지만 여기서는 같은 문자열로 작성해 실수를 줄인다.
4. Montage Sections의 각 section Next를 None으로 설정한다. 화면의 연결선과 section 목록을 함께 확인한다. section이 자동으로 다음 방향으로 이어지면 한 회피에서 여러 방향을 재생하게 된다.
5. Sequence Skeleton과 BP_Player mesh가 SK_Player를 사용하는지 확인한다. InGame 복제본의 Enable Root Motion/실제 최상위 root track을 Preview로 확인한다. 예전 source 후보 저장감사는 M1 8개가 enable_root_motion=true, force_root_lock=true였지만 현재 InGame asset property는 이번 도구가 읽어내지 못했다. 확인하지 않은 import 상태를 완료로 기록하지 않는다.
6. 기존 ABP_Player의 DefaultGroup.DefaultSlot과 Inertialization 경로를 사용한다. 새로운 Dodge state/AnimInstance enum을 추가하지 않는다. 저장 감사의 Root Motion Mode는 Root Motion from Everything이며 Montages Only로 임의 되돌리지 않는다. Root Motion은 CMC가 capsule에 적용하고 AddMovementInput/SetActorLocation/Launch를 겹쳐 같은 이동을 두 번 만들지 않는다.

| 방향 | sequence 파일 이름 | NodeId / SectionName |
| --- | --- | --- |
| F | CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1 | Dodge_F |
| RF | CA_P_Kazan_DualAxeSword_Off_Dodge_RF_M1 | Dodge_RF |
| R | CA_P_Kazan_DualAxeSword_Off_Dodge_R_M1 | Dodge_R |
| RB | CA_P_Kazan_DualAxeSword_Off_Dodge_RB_M1 | Dodge_RB |
| B | CA_P_Kazan_DualAxeSword_Off_Dodge_B_M1 | Dodge_B |
| LB | CA_P_Kazan_DualAxeSword_Off_Dodge_LB_M1 | Dodge_LB |
| L | CA_P_Kazan_DualAxeSword_Off_Dodge_L_M1 | Dodge_L |
| LF | CA_P_Kazan_DualAxeSword_Off_Dodge_LF_M1 | Dodge_LF |

모든 sequence의 package 폴더는 /Game/_Art/Player/Animation/InGame/DAS/Dodge다. section의 시작 시간은 해당 실제 segment 시작 위치를 사용한다.

Notify를 각 section에 세 개 작성한다. Montage Notify track 우클릭 → Add Notify → Montage Notify를 사용한다. 일반 Skeleton Notify나 Montage Notify Window가 아니라 point Montage Notify다. Details의 Notify Name에 InputOpen/InputCommit/InputEnd를 정확히 넣고 Montage Tick Type을 Branching Point로 지정한다. 기존 코드가 OnPlayMontageNotifyBegin을 구독하므로 Notify 종류와 이름을 모두 맞춰야 한다.

첫 작동 시험용 timing은 다음과 같다. **이 4/8/24 프레임은 어시스턴트가 고른 임시 튜닝값**이다. 원작 Notify metadata를 확인한 값이 아니다. C++ magic number가 아니라 Montage의 authored point 위치에 모아 저장한다.

| Notify | 각 section 로컬 frame | 30 fps 가정 시 로컬 시간 | 임시 선정 의도와 영향 |
| --- | --- | --- | --- |
| InputOpen | 4 | 4/30 ≈ 0.133333 s | 회피 시작 피드백 후 예약 허용. 이 전의 press는 특별 공격으로 소비 안 됨 |
| InputCommit | 8 | 8/30 ≈ 0.266667 s | Open 뒤 짧은 예약 구간을 두고, 이후 입력은 즉시 실행 |
| InputEnd | 24 | 24/30 = 0.8 s | 뒤쪽 회복 구간에서 일반 Action/Move 교체 허용 |

시간 계산 입력의 근거는 Saved/KZStaminaLockOnDodgeInspect.json의 dodge_combat_m1[0].frame_rate={numerator:30, denominator:1}, number_of_frames=32, play_length=1.0666667222976685다. 해당 path는 /Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Combat/Evasion/Dodge/CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1이다. 이는 **현재 UE 후보의 저장 감사/임포트 관측값**이며 원작 gameplay window의 직접 metadata가 아니다. InGame 복제본의 실제 sample rate와 길이를 Editor에서 확인한다. 30 fps가 다르면 frame/FPS 변환을 다시 계산하며 기존 seconds를 그대로 복사하지 않는다.

Montage의 절대 Notify 시간은 section start S에 로컬 시간을 더한다. RF의 시작이 S_RF이면 세 위치는 S_RF+4/FPS, S_RF+8/FPS, S_RF+24/FPS다. montage 전체 시간 0.133333에 모든 section의 InputOpen을 겹쳐 놓지 않는다. section 시작/끝을 확인하고 세 위치가 자기 segment 안에 있는지 확인한다. 최초에는 같은 frame에 여러 상태 Notify를 배치하지 않아 처리 순서 의존을 만들지 않는다.

임시 timing 조정 기준은 늦은 취소/오입력/버퍼 응답이다. 원치 않는 즉시 회피 취소면 Open/Commit을 뒤로, 입력 응답이 너무 늦으면 앞쪽으로 조정하되 Open<Commit<End<실제 section end를 유지한다. End가 너무 앞이면 root-motion 회피가 잘리고, 너무 뒤면 회복 구간 일반 입력이 늦다. 원작 metadata가 확보되면 asset/version/notify field/frame/unit을 기록한 뒤 같은 의미인지 대조해서 교체한다. 이번 안내의 임시 frame을 원작값으로 승격하지 않는다.

기존 8 Dodge BP defaults를 지정한다. 폴더는 /Game/Bluprints/AbilitySystem/Abilities/Player/Dodge다.

| BP | DodgeDirection | ComboDefinition | EntryNodeId |
| --- | --- | --- | --- |
| GA_Player_DodgeAbility_F | F | DA_Player_Combo_Definition | Dodge_F |
| GA_Player_DodgeAbility_RF | RF | 동일 asset | Dodge_RF |
| GA_Player_DodgeAbility_R | R | 동일 asset | Dodge_R |
| GA_Player_DodgeAbility_RB | RB | 동일 asset | Dodge_RB |
| GA_Player_DodgeAbility_B | B | 동일 asset | Dodge_B |
| GA_Player_DodgeAbility_LB | LB | 동일 asset | Dodge_LB |
| GA_Player_DodgeAbility_L | L | 동일 asset | Dodge_L |
| GA_Player_DodgeAbility_LF | LF | 동일 asset | Dodge_LF |

Class Defaults에서 inherited KZ|Combo 항목과 Dodge 항목을 펼친다. 모두 공통 UKZDodgeAbility를 부모로 두며 inherited InstancingPolicy=InstancedPerActor, NetExecutionPolicy=LocalOnly, Block/CancelAbilitiesWithTag=Ability.Action을 확인한다. Action의 취소/OwnedTags 설정을 각각 BP graph에 다시 구현하지 않는다.

공유 asset 경로는 /Game/Data/ComboCommand/DA_Player_Combo_Definition이다. Nodes에 Dodge_F부터 Dodge_LF까지 8개를 추가하고 각각 Montage=AM_DAS_Dodge, SectionName=위 표로 둔다. 기존 Weak/Strong/Charge node를 보존하고 우선 CommandEdges는 빈 상태로 Dodge 단독 실행부터 검사한다.

CharacterDefinition은 /Game/Data/Character/DA_CharacterDefinition_Player다. Initial Ability Grants 배열에 Dodge BP 8개를 추가하고 각 InputTag는 **비운다**. 같은 방향 한 개만 grant한다. 기존 Weak/Strong의 X/Y binding은 현재 설정을 보존한다. 원래 Character grant 코드가 InputTag 없이도 GiveAbility하므로 새로운 grant manager가 필요 없다.

비용/회복 설정을 분리해 authoring한다. 처음 입력/몽타주 검증을 할 때 새 Dodge/특별 공격의 Cost Gameplay Effect는 None으로 둔다. 이것은 **비용 없는 경로 시험 설정**이며 원작 Dodge가 무비용이라는 결론이 아니다. 기존 X/Y Cost GE는 변경하지 않는다. 원작 Dodge/스킬 비용이 미확인인 상황에서 기존 공격 Cost를 원작 회피 비용으로 복사하지 않는다.

실제 cost를 연결할 때는 각 Ability의 CostGameplayEffect에 확인한 GE를 연결한다. GE의 Stamina modifier가 소비량을 소유하고, CanActivate/Commit/local TransitionToNode가 해당 설정을 사용한다. 표적 비용 부족 검증도 GE가 연결된 뒤 수행한다. 검사 전후 Stamina/CurrentNodeId/current Montage/Ability active를 비교한다. 이번 제안은 per-node 비용 정책을 유지하며 새로운 cost literal은 넣지 않았다.

OnEndAbilityGameplayEffect는 기존 /Game/Bluprints/AbilitySystem/Effects/GE_Player_StaminaRegenDelay를 연결해 현재 프로젝트의 종료 후 regen delay 정책을 재사용할 수 있다. 이 GE의 기존 duration을 새 원작 확인값으로 주장하거나 임의 수정하지 않는다. 이 슬롯이 None이면 종료 후 별도 delay가 적용되지 않는다는 실제 차이가 있으므로 Class Defaults를 확인한다. normal→Dodge→special 연속 전환에서 delay 갱신과 Block.StaminaRegen count를 PIE에서 검사한다.

먼저 F에서 X/Y 특별 공격 둘을 완성한다.

1. /Game/Bluprints/AbilitySystem/Abilities/Player/DodgeAttack에 UKZComboAttackAbility를 부모로 GA_Player_DodgeWeakAttack_F와 GA_Player_DodgeStrongAttack_F를 만든다. EventGraph에 별도 Montage Play를 넣지 않는다. inherited common C++가 재생/취소한다.
2. 최초 모션 연결 시험에서는 Weak_F에 Com_DodgeAtk_F_JustMoment, Strong_F에 Com_DodgeAtk_F_RecklessRush를 임시 대응시킨다. 폴더는 /Game/_Art/Player/Animation/InGame/DAS/DodgeAttack이며 전체 prefix는 CA_P_Kazan_DualAxeSword_다. **이 대응은 어시스턴트가 제안한 임시 콘텐츠 연결이며 원작 X/Y·스킬 대응 확인 결과가 아니다.** 원작 대응 확인 뒤 교체한다. Charge variant는 이번 plain Y/Begin 시험에 사용하지 않는다.
3. 각 sequence에서 별도 Montage AM_DAS_DodgeWeakAttack_F / AM_DAS_DodgeStrongAttack_F를 만들고 DefaultGroup.DefaultSlot을 쓴다. 각각 section 이름을 DodgeWeakAttack_F / DodgeStrongAttack_F로 지정하고 Next=None으로 둔다.
4. 첫 target 시험은 한 motion을 자연 완료하는 단일 section/CommandEdges 빈 구성으로 둔다. 특별 공격 취소/추가 콤보 Notify timing은 아직 원작 미확인이다. target에 InputOpen/Commit/End를 억지로 넣지 않고 끝까지 block 후 자연 종료를 확인한다. 이후 특별 공격 cancel window를 authoring할 때 그 설정을 별도 범위로 기록한다.
5. 공유 Definition에 DodgeWeakAttack_F / DodgeStrongAttack_F node를 만들고 해당 Montage/Section을 연결한다.
6. 두 BP ComboDefinition은 같은 공유 asset이고 EntryNodeId는 각 node다. Activation Required Tags는 Weak BP에 Unlock.Skill.DAS.DodgeAttack.Weak, Strong BP에 .Strong을 한 개씩 넣는다. Activation Owned Tags에는 해금 tag를 넣지 않는다.
7. CharacterDefinition에 두 특별 공격 BP를 grant하고 InputTag는 비운다. 잠긴 상태에서도 Spec을 grant한다. 다른 input entry가 직접 시작시키지 않으며 직접 activation/AI request도 RequiredTags를 통과해야 한다.
8. Dodge_F node에 아래 X/Y 두 Edge를 작성한다.

| 필드 | X Edge | Y Edge |
| --- | --- | --- |
| CommandTag | Command.Player.Attack.X | Command.Player.Attack.Y |
| CommandPhase | Begin | Begin |
| Hold | Any | Any |
| Move | Any | Any |
| RequiredHeldCommands | empty | empty |
| OwnerTagRequirements.RequireTags | Unlock.Skill.DAS.DodgeAttack.Weak | Unlock.Skill.DAS.DodgeAttack.Strong |
| OwnerTagRequirements.IgnoreTags | empty | empty |
| OwnerTagRequirements.TagQuery | empty | empty |
| TargetNodeId | DodgeWeakAttack_F | DodgeStrongAttack_F |

CommandTag가 이미 이번 버튼을 가리킨다. RequiredHeldCommands에 X/Y 자기 자신을 무조건 다시 넣으면 눌렀다 놓는 tap buffer의 Commit이 실패할 수 있다. 그 필드는 **추가로 계속 눌려 있어야 하는 command 조건**을 요구할 때만 사용한다. 이번 최소 특별 공격의 Hold/Move를 Any로 두므로 차지와 Run-only 제한을 만들지 않는다.

X/Y event 선택과 Weak/Strong 해금 사실을 별도로 읽는다. Dodge_F node 자체가 회피 중/방향 F를 고정하므로 Edge에 bIsDodging나 또 다른 Direction 값을 추가하지 않는다. Ability.Action.Dodge를 OwnedTags 요구로 넣어도 ctor AssetTag 분류만으로는 소유 tag가 생기지 않는다. 이번 gate는 graph node와 unlock으로 작성한다.

해금 GE를 만든다.

1. /Game/Bluprints/AbilitySystem/Effects/Unlock 폴더에 GameplayEffect BP GE_Dev_Unlock_DodgeAttack_Weak와 GE_Dev_Unlock_DodgeAttack_Strong을 만든다. Dev는 제품 Save producer가 아니라 gate 검증용이라는 표시다.
2. Class Defaults의 Duration Policy=Infinite. Components에 **Target Tags (Granted to Actor)**를 추가한다. UE 5.8 설치 소스의 UTargetTagsGameplayEffectComponent가 사용하는 표시 이름이다.
3. 해당 component의 Add Tags → Added에 자기 Weak/Strong native 해금 tag를 하나씩 추가한다. GE Asset Tags나 Ability AssetTags에 넣는 것으로 대체하지 않는다. 별도 attribute modifier/stacking/time tuning은 필요 없다.
4. 네 상태 시험은 CharacterDefinition Initial Effects에 이 GE들만 없음/Weak/Strong/둘 다를 각각 추가하는 것으로 진행한다. 기존 초기 Stamina/regen GE는 유지하고 개발용 두 row만 바꾼다. 각 변경마다 Stop PIE 후 새 PIE로 시작한다.
5. 이 방식은 현재 Character::PostInitializeComponents가 Authority에서 InitialEffects를 적용하고 Ability를 grant하는 실제 소비 경로를 사용한다. Infinite GE가 살아 있는 동안 ASC가 해금 tag를 소유한다. Instant GE로 영속 tag를 부여하려 하지 않는다.
6. 실행 중 해금/해제 시험이 필요하면 실제 현재 producer/callback에서 MakeEffectContext→MakeOutgoingSpec→ApplyGameplayEffectSpecToSelf의 반환 FActiveGameplayEffectHandle을 그 producer가 보관하고, 자기 handle만 RemoveActiveGameplayEffect로 제거한다. 이 안내 때문에 미래 ProgressionManager와 빈 helper를 새로 만들지 않는다.
7. 제품에서는 Save/스킬 습득 데이터가 영속 원본이다. Pawn 준비/재생성 시 실제 해금 producer가 효과를 재투영한다. Ability::EndAbility나 Dodge input이 해금 tag를 지우지 않는다. 개발용 InitialEffects를 항상 넣으면 시작부터 unlocked이므로 최종 제품의 해금 절차와 구분한다.

| InitialEffects 추가 상태 | 창 안 X | 창 안 Y |
| --- | --- | --- |
| 두 GE 없음 | special Edge 불일치 | special Edge 불일치 |
| Weak GE만 | DodgeWeakAttack_F | special Edge 불일치 |
| Strong GE만 | special Edge 불일치 | DodgeStrongAttack_F |
| 둘 다 | DodgeWeakAttack_F | DodgeStrongAttack_F |

미해금/창 밖 press는 InputEnd 전에는 기존 Action block 때문에 신규 일반 공격도 시작되지 않는다. InputEnd 뒤에는 ordinary X/Y fallback이 가능하다. 해금 전 기본 회피공격의 원작 유무는 미확인이며 여기서는 별도 미해금 DodgeAttack을 만들어 넣지 않는다. 원작에서 기본 회피공격이 확인되면 special RequireTags Edge와 기본 IgnoreTags fallback을 구분해 작성한다.

F의 두 갈래가 맞으면 8방 전체 Edge를 확장한다. 확인된 asset이 F/B/L/R뿐이고 특별 가족의 모든 방향 대응도 미확인이다. 바로 전체 입력 경로를 시험할 수 있도록 아래는 **임시 콘텐츠 대응표**다. 원작 재현 완료 표가 아니다.

| 공격 target 방향 | 임시 Weak sequence | 임시 Strong sequence | 확인/제한 |
| --- | --- | --- | --- |
| F | Com_DodgeAtk_F_JustMoment | Com_DodgeAtk_F_RecklessRush | 두 가족의 X/Y 대응 미확인 |
| B | Com_DodgeAtk_B_JustMoment | Com_DodgeAtk_B_RecklessRush | 동일한 미확인 대응 |
| L | Off_DodgeAtk_L_M1 | Off_DodgeAtk_L_M1 | 실행/gate 시험에서 같은 motion 공유, 강/약 시각 구분 미확정 |
| R | Off_DodgeAtk_R_M1 | Off_DodgeAtk_R_M1 | 동일한 제한 |

위 sequence들은 파일 존재를 확인했다. prefix/폴더는 F 특별 공격과 같다. 실제 root track/Enable Root Motion/Skeleton/재생 범위는 각 target Preview에서 검사한다. property 조회가 빈 결과였으므로 이번에 해당 내용을 확인했다고 기록하지 않는다.

B/L/R에도 Weak/Strong BP와 각각의 Montage/node를 만들면 특별 공격 BP는 총 8개다. EntryNodeId는 DodgeWeakAttack_B/L/R, DodgeStrongAttack_B/L/R다. 모두 같은 Definition, InputTag empty, 각각 자기 Weak/Strong ActivationRequiredTags를 쓴다. L/R이 같은 sequence를 시험에 쓰더라도 두 logical Entry를 구분해 해금 gate와 이후 데이터 교체 위치를 명확히 한다.

| 출발 Dodge node | X TargetNodeId | Y TargetNodeId | 대응 상태 |
| --- | --- | --- | --- |
| Dodge_F | DodgeWeakAttack_F | DodgeStrongAttack_F | F 임시 모션 대응 |
| Dodge_RF | DodgeWeakAttack_F | DodgeStrongAttack_F | 대각선→F 임시 mapping |
| Dodge_R | DodgeWeakAttack_R | DodgeStrongAttack_R | R 임시 강/약 motion 공유 |
| Dodge_RB | DodgeWeakAttack_B | DodgeStrongAttack_B | 대각선→B 임시 mapping |
| Dodge_B | DodgeWeakAttack_B | DodgeStrongAttack_B | B 임시 모션 대응 |
| Dodge_LB | DodgeWeakAttack_B | DodgeStrongAttack_B | 대각선→B 임시 mapping |
| Dodge_L | DodgeWeakAttack_L | DodgeStrongAttack_L | L 임시 강/약 motion 공유 |
| Dodge_LF | DodgeWeakAttack_F | DodgeStrongAttack_F | 대각선→F 임시 mapping |

각 row에 동일한 X/Y 해금 RequireTags/Begin/Any 조건을 붙인다. 대각선 원작 특수 motion이 확보되면 target node/Ability를 추가하고 Edge 데이터만 바꿀 수 있다. 8 Dodge×2 입력이라는 이유로 없는 시퀀스 16개나 native 클래스 16개를 만들 필요는 없다. 원작 대응이 달라지면 임시 mapping을 제품 정답으로 유지하지 않는다.

Content Browser에서 DA_Player_Combo_Definition을 Validate Assets로 검사한다. duplicate ID/target/section/identical Edge 오류가 없어야 한다. 이어서 수동으로 (1) 모든 target Entry BP의 shared Definition pointer (2) unique EntryNodeId (3) CharacterDefinition에 같은 BP 한 번 grant (4) graph-only InputTag empty (5) target RequiredTags를 표와 대조한다. graph 검증만으로 이 BP/grant 계약을 자동 확인한 것이 아니다.


검증은 아래 순서로 수행한다. 이것은 사용자가 Source/에셋을 적용한 뒤의 예상 결과이며 어시스턴트가 PIE에서 관측한 결과가 아니다.

| 시험 | 예상 결과 | 실패 시 먼저 볼 곳 |
| --- | --- | --- |
| 기존 idle X/Y | 원래 entry 하나만 활성화 | RouteAttackInput 순서, grant-order, held 중복 |
| 기존 local 콤보 | 예약/Commit 하나, 같은 press 재시작 없음 | bConsumed/false restart gate, Notify phase |
| 기존 charge early Release | 기존 Release Edge, 정상 target | release 선행 held 제거, Entry grant |
| held 동일 입력 handoff 후 Release | 새 target의 WaitInputRelease 수신 | source.InputPressed=false 이관, target 실제 binding |
| Canceled/입력 해제 | 정상 Release 공격 생성 안 됨 | Command Cancel와 generic cancel, pending clear |
| 비LockOn+임의 방향 | 모두 F Dodge Spec | IsLockedOn 분기, A handler가 현재 Pawn 조회하는지 |
| LockOn+무입력 | F | 현재 Move action value/deadzone |
| LockOn+8방 | F/RF/R/RB/B/LB/L/LF | X=전후/Y=좌우, 두 Yaw, BP 방향 중복 |
| 동일 frame Move+Dodge | 현재 평가된 방향 | GetActionValue, IMC modifiers/Move triggers, callback breakpoint |
| 같은 방향 재입력, InputEnd 전 | restart 차단 | active Spec의 HasInputEnded |
| 같은 방향 재입력, InputEnd 뒤 | 이전 실행 정리 후 새 activation | preflight/cancel/re-find, Cost/entry |
| InputOpen 전 X/Y | special 소비 안 됨 | Montage Notify 종류/이름/시간, 현재 phase |
| Open~Commit X/Y tap | 한 칸 예약, Commit에서 특별 공격 | PendingCommandTag/해금/target grant |
| Commit~End X/Y | 해당 특별 공격 즉시 승인, 일반 공격 추가 시작 없음 | bool 반환, target gate/graph-only InputTag |
| InputEnd 뒤 X/Y | 일반 X/Y 진입 | phase Closed, generic true, target cancellation |
| unlock 네 조합 | 표의 Weak/Strong gate | ASC OwnedTags, GE TargetTags component, target RequiredTags |
| 비용 부족(실제 Cost GE 연결 후) | 사전 activation 거절, InputEnd 전 source 보존 | CanActivate/ApplyEdge 결과 및 source block 복구 |
| 비용 부족 같은 Spec restart | cancel 전에 거절 | preflight의 CheckCost와 현재 Cost GE |
| 없는/중복 방향 grant | 로그/false | CharacterDefinition AbilityClass와 CDO Direction |
| capsule/벽/경사 | root-motion CMC 이동과 collision | 최상위 root track/mesh transform/actual capsule delta |
| target 선회 중 회피 | 방향 선택은 고정, 실제 궤적을 별도 확인 | LockOn rotation policy와 CMC root motion 변환 |
| 자연 종료/interrupt/UnPossess/Stop PIE | Task/delegate/OwnedTags/held/Spec press 잔존 없음 | common EndAbility, Character cleanup, GE handle |

루트모션 거리가 이상하면 현재 native Player mesh scale은 0.01이라는 Source 사실과 BP 최종 scale을 따로 확인한다. 과거 저장감사의 0.009를 현행 정답으로 되돌리지 않는다. 원작/root metadata를 확인하지 않은 상태에서 scale 역수나 SetActorLocation 보정으로 거리를 맞추지 않는다. mesh가 움직이고 capsule이 안 움직이는지, root delta가 없거나 좌표축이 틀렸는지, wall collision이 제한한 실제 displacement인지 나눠 본다.

LockOn을 유지한 actor Yaw가 회피 중 변하면 선택된 RF/R 같은 node는 바뀌지 않지만 root-motion 월드 궤적은 기존 CMC/회전 정책의 영향을 받을 수 있다. 이번 enum 계산만으로 직선 월드 궤적 고정을 보장하지 않는다. 실제 요구/PIE 증거가 생길 때 Locomotion의 원인별 constraint나 실제 root-motion 정책으로 처리하며 Main AnimInstance bool을 임의로 추가하지 않는다.

breakpoint를 통한 사용자의 확인 순서는 Input_DodgeStarted의 MovementInput/Direction → TryActivateDirectionalDodge의 TargetHandle/CDO direction → CanActivate/Activate의 EntryNode → HandleComboCommand의 phase/window/해금 match → ApplyEdge/TryActivateComboEntry의 target/bTargetOwnsInput → EndAbility/unbind다. 같은 입력이 어떤 Spec을 시작했는지와 어떤 Spec이 Released를 받는지 구분해서 본다.

해금 검사에서 막히면 Edge OwnerTagRequirements는 현재 ASC의 OwnedTags를 읽고, target CanActivate의 Super도 ActivationRequiredTags를 읽는지 확인한다. tag 사전에 등록된 문자열이 보이는 것과 Pawn이 tag를 소유하는 것은 다르다. 해금 GE를 적용한 ASC가 다른 Actor의 ASC인지도 확인한다.

새 target을 먼저 검증하고 승인 뒤 source를 닫는 현재 경로는 일반적인 비용/태그/데이터 사전 실패를 줄인다. UE PreActivate는 target Activate/Commit/Task보다 먼저 기존 Action을 cancel할 수 있다. 따라서 TryActivate true인데 target Montage가 바로 실패하면 source가 자동으로 복원된다고 가정하지 않는다. 해당 실패는 target Montage/Slot/Skeleton/section/bind/Task 로그로 진단하고 데이터 오류부터 고친다.

어시스턴트가 확인한 것은 실제 Source/현행 문서, 표적 asset 파일 존재, 설치 UE 5.8의 CanActivate/Delegate/EnhancedInput/Validation API, 저장된 Dodge 후보 감사다. asset property 조회는 빈 결과였고, Rider call hierarchy는 C++ symbol을 해석하지 못해 Source의 실제 호출부를 대조했다. .txt 제안은 컴파일된 바이너리가 아니며 에디터 설정과 게임 동작은 이 표의 적용 후 검증이 필요하다.

구현 안내를 따라 첫 검증이 끝났을 때의 기준은 방향별 Dodge 요청, F의 해금 X/Y handoff, 기존 입력 회귀와 수명 cleanup이다. 8방 특별 공격의 임시 콘텐츠 대응, 원작 비용/타이밍, 특별 공격 취소/무적/적중/피해 및 Save producer는 적용·검증한 범위만 별도로 기록한다.

2026-10-01 에디터 표시 이름 확인: 설치 UE 5.8 GameplayEffectTypes.h의 FGameplayTagRequirements는 RequireTags를 "Must Have Tags", IgnoreTags를 "Must Not Have Tags", TagQuery를 "Query Must Match"로 표시한다. DA_Player_Combo_Definition의 Node → Command Edges → Owner Tag Requirements를 펼치고 Must Have Tags에 해당 Weak/Strong 해금 tag를 넣는다. Must Not Have Tags와 Query Must Match는 이번 최소 Edge에서 비운다. 위 표의 RequireTags/IgnoreTags/TagQuery는 C++ field 이름이고 이 세 이름이 에디터의 대응 label이다.

## 2026-10-01 — 기존 방향각 계산과 Dodge 입력각의 재사용 범위

사용자가 기존 MoveDirection 계열 계산을 지적해 현행 Source를 다시 확인했다. `UKZAnimInstance::MovementDirectionAngle`은 실제로 존재하며 `UpdateKinematics_AnyThread`가 CMC 실제 속도 snapshot을 Actor Yaw로 역회전한 `VelocityLocal`에 `DegAtan2(Y,X)`를 적용한다. 현재 실제 속도가 `MovingSpeedThreshold` 이하이면 0으로 기록한다. 이 임계값은 현 프로젝트 설정이며 원작 확인값이 아니다. `AKZPlayer::HandleInputMove`의 지역 `MoveDirection`은 `Intent.MoveInputWorld.GetSafeNormal2D()`로 만든 월드 방향 벡터이며 각도가 아니다.

기존 계산 방식은 Dodge에도 사용 가능하다. 다만 Dodge 입력에서 읽을 데이터는 누른 순간의 현재 Move action value다. 실제 속도의 관성, 정지 상태, 이동 차단, animation snapshot 갱신 시점 때문에 AnimInstance의 저장된 `MovementDirectionAngle`을 방향 선택의 권위로 읽지 않는다. 예를 들어 Actor/Camera Yaw가 같고 왼쪽으로 이동하다 오른쪽+Dodge를 누르면 실제 속도각은 아직 L일 수 있지만 Dodge 선택은 현재 오른쪽 입력의 R이어야 한다.

앞선 `ResolveDodgeDirection`의 `WorldInput` 계산까지 유지한 뒤, `ActorYaw` 선언부터 `AngleDegrees` 초기 계산까지를 아래 코드로 대체할 수 있다. 이후 음수 각도 보정과 균등 8방 양자화는 유지한다. 기존 내적 구현도 같은 수평 기저 변환이며 오류 수정이나 새 gameplay 정책이 아니다.

```cpp
const FRotator ActorYaw(0.0, GetActorRotation().Yaw, 0.0);
const FVector LocalInput =
    UKismetMathLibrary::LessLess_VectorRotator(WorldInput, ActorYaw);

double AngleDegrees =
    UKismetMathLibrary::DegAtan2(LocalInput.Y, LocalInput.X);
```

- `ActorYaw`: 현재 Actor의 수평 방향. 입력 처리 Game Thread에서 읽는다. Camera Yaw는 앞 단계에서 장치 입력을 월드로 바꾸는 기준이며 이 단계의 캐릭터 기준과 역할이 다르다.
- `LocalInput`: 함수 지역 FVector. 현재 월드 입력을 Actor 좌표계로 역회전한 결과다. X는 정면 성분, Y는 오른쪽 성분이다. 앞선 코드의 `LocalForward`/`LocalRight`와 각각 같은 수학적 의미이며 방향 계산 뒤 보관/Reset하지 않는다.
- `LessLess_VectorRotator`: 기존 AnimInstance가 이미 쓰는 엔진 순수 수학 API다. 설치 UE 5.8 `Engine/Source/Runtime/Engine/Classes/Kismet/KismetMathLibrary.inl:1543`에서 `B.UnrotateVector(A)`를 반환하는 것을 확인했다. 기존 KismetMathLibrary include와 Engine 의존성을 그대로 사용할 수 있다.
- `DegAtan2(Y,X)`: 오른쪽을 양수로 삼는 Actor 기준 signed angle, 단위 degree. 입력 벡터를 사용하므로 별도의 속도 임계값이나 `bIsMoving` 검사를 옮겨오지 않는다. 비LockOn/무입력 처리는 기존 함수의 첫 분기와 Player deadzone 설정이 담당한다.

현재 프로젝트에는 위 변환과 Atan2를 묶은 공통 Khazan 함수가 없다. 이번 설명은 기존 엔진 수학 API를 같은 방식으로 호출하는 제안이며 새로운 math helper, Player의 각도 멤버, AnimInstance의 gameplay 상태를 추가하지 않는다. 360/8과 반구간은 균등 방향 분할의 기하학 상수이고 원작 방향 경계 metadata 추출값이 아니다.

현행 `KZDodgeAbility.h`에는 사용자가 작성한 `EKZDodgeDirection`, `GetDodgeDirection()`, defaults 설정 `DodgeDirection`이 존재한다. 아직 runtime `KZDodgeTypes.h`와 Player `ResolveDodgeDirection`은 없다. 앞선 타입 헤더 분리안은 적용된 상태가 아니며, 타입을 옮길 경우 기존 헤더의 같은 UENUM 정의를 중복으로 남기지 않는다. 이번 확인은 현행 Source와 설치 엔진 구현을 읽은 범위이며 게임 Source/BP/에셋 수정 및 build/PIE를 수행하지 않았다. 이 추가 절은 대체 설명이고 이전 전체 .txt 제안과 zip을 적용 완료로 바꾸지 않는다.

## 2026-10-01 — 전체 첨부보다 작은 Dodge 변경 범위

사용자가 제안의 크기와 현재 구조 재사용을 재검토하도록 요청했다. 현재 Source를 확인한 결과 공통 ComboAction의 실행/입력창/해금 검사/handoff와 CanActivate/Cost gate가 이미 있다. Dodge enum/defaults/getter도 기존 KZDodgeAbility.h에 있다. 이 안내와 zip의 전체 파일 사본을 모두 교체해야 Dodge를 추가할 수 있다는 절차는 최신 권장안이 아니다.

최신 설계는 Architecture 하단의 “ARCH-72 최소 변경 재검토: 기존 입력 경로로 방향별 Dodge 연결”과 Migration 하단 D4를 따른다.

1. 현재 enum 정의를 유지하므로 신규 KZDodgeTypes.h는 필수가 아니다. 필요한 header는 enum 전방 선언, cpp는 기존 Dodge header include로 연결할 수 있다.
2. 기존 F BP에 ComboDefinition/Entry/Montage/Notify/A binding을 설정하고 Started를 기존 ASC press에 연결하면 공통 base의 회피 재생을 확인할 수 있다. 이는 F checkpoint이고 8방 완료가 아니다.
3. 8방의 추가는 현재 IA_Move read와 Player 지역 방향 계산, Controller 지역 Spec 선택이다. ASC의 기존 AbilityInputTagPressed에 optional RequestedHandle만 추가해 active/inactive 두 순회를 해당 Spec으로 제한한다. 기존 InputTag 검사, TryActivateAbility, press/release/cancel/restart 수명은 유지한다.
4. 이 안의 Dodge 8 BP는 모두 Input.Action.A를 binding한다. A Completed/Canceled는 기존 tag release/cancel로 간다. 앞선 8 Dodge graph-only grant 및 TryActivateDirectionalDodge 전용 함수 제안은 이 범위에서 대체한다. 특별 공격 target은 계속 graph-only다.
5. 특별 공격/해금은 기존 shared graph의 X/Y Edge, OwnerTagRequirements, target ActivationRequiredTags와 GE 소유 tag로 구성한다. 새 Combo 실행/Edge 필드/해금 manager/native 특별 공격 class를 추가하지 않는다.
6. X/Y의 command 소비·일반 activation 중재 및 graph-only/binding 입력 기록은 현행 경로의 작은 공통 보완으로 남긴다. 자동 IsDataValid와 무관한 정리를 최초 Dodge 실행의 필수로 묶지 않는다. UnPossessed 취소 누락도 기존 함수 보완으로 따로 설명한다.

새 runtime 파일 없이 구성할 수 있다. 현재 8 BP/Ability 요구는 보존하고, Controller가 ASC의 실행 수명이나 비용을 별도로 구현하지 않는다. 선택 실패 또는 중복일 때 invalid RequestedHandle로 일반 A 후보를 실행해서는 안 된다. 같은 Spec restart의 비용/data 승인은 기존 실행 cancel 전에 확인한다. 이 절은 제안 범위 정정이며 game code/BP/asset 적용 및 build/PIE 결과가 아니다. 이후 코드 안내는 현재 Source에 대한 작은 diff를 기준으로 제공한다.


## 2026-10-01 — 최소 범위 확정 보정: 기존 X/Y 순서도 유지 가능

바로 위 최소 검토의 6번에 적은 X/Y 소비 중재는 현재 InputEnd 정책에서는 필수 변경이 아니다. 현행 Action은 InputEnd 전 일반 Action을 block하고, 현행 InputEnd는 ComboWindow를 Closed로 만든 뒤 block을 푼다. 따라서 InputEnd 전 X/Y는 일반 공격 activation이 거절된 다음 기존 Combo Command가 Dodge의 특별 Edge를 처리한다. InputEnd 뒤에는 기존 일반 공격이 시작되고 Dodge의 Begin Edge는 닫힌 창에서 평가되지 않는다.

이 경계를 유지하는 최종 최소안은 Player/Controller/ASC 기존 h/cpp의 방향 계산/지역 Spec 선택/optional RequestedHandle 필터와 graph-only target 입력 기록·같은 Spec restart 사전 승인 보완이다. 현재 Dodge enum/base, ComboAction command handler/delegate, Definition schema, X/Y RouteAttackInput 순서를 유지한다. 나머지는 기존 BP/Montage/shared graph의 node/edge/해금 GE 데이터다. 자동 validation과 수명 정리는 독립 보완으로 구분한다. InputEnd 뒤에도 특별 Edge를 우선시키는 규칙을 실제 채택할 때 소비 중재를 다시 검토한다.

이 추가 절과 Architecture 마지막 ARCH-72 절이 이전 전체 첨부의 넓은 입력 변경 제안보다 우선한다. game code/BP/asset 수정 및 build/PIE는 수행하지 않았다. 현재 native 정책을 BP가 유지하는지와 실제 montage 입력창/비용/방향/Release/Cancel은 적용 후 확인한다.



## 2026-10-01 — 이후 최소 변경 안내가 우선

이 문서와 같은 폴더의 전체 파일/zip은 앞선 제안 기록으로 보존한다. 최신 사용자 원칙과 실제 현행 Source 기준 적용 절차는 [DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md](../../DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md)와 [작은 변경 patch](../DodgeMinimal_20261001.patch)가 우선한다. 기존 7파일만 보완하고 새 runtime 파일은 만들지 않으며, 현재 ComboAction/enum/Definition과 X/Y 순서를 유지한다. Dodge 8 grant는 같은 Input.Action.A, 특별 target은 InputTag empty다. 여기의 16파일을 일괄 덮어쓰지 않는다.
