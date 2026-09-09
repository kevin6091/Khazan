# M1 — 모든 캐릭터의 공통 ASC 연결

## 2026-09-08 공동 구현 가이드 — 사용자 적용 전

- 목표 구조: [아키텍처 v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2).
- 전체 순서: [M0–M10 마이그레이션](CHARACTER_TAG_ABILITY_MIGRATION.md).
- 이 문서의 코드는 **사용자가 직접 따라 적용할 제안 코드**다. 어시스턴트가 Source/BP/Config/uproject에 적용하거나 빌드/PIE를 통과한 결과가 아니다.
- 첫 범위는 GAS 접속·소유·ActorInfo 수명이다. 새 액션/피해/태그 상태/CMC 제약/Linked Layer를 한꺼번에 만들지 않는다.
- 이번 단계에는 gameplay 튜닝 수치가 없다. JSON의 true, nullptr, 엔진 enum/검사 결과는 설정·기술적 표현이다.

## 1. 이번에 만들 동작과 완료 기준

Player와 Monster는 모두 기존 `AKhazanCharacter`를 상속한다. 이 공통 부모가 ASC를 생성하고 엔진의 IAbilitySystemInterface로 반환하게 만든다.

```text
AKhazanCharacter
 ├─ 기존 LocomotionComponent
 └─ UAbilitySystemComponent
       OwnerActor  = 그 Character
       AvatarActor = 그 Character
       조회 계약   = IAbilitySystemInterface
         ├─ AKhazanPlayer가 그대로 상속
         └─ AKhazanMonster가 그대로 상속
```

그림은 캐릭터 하나의 구성을 뜻한다. Player와 Monster가 ASC 인스턴스 하나를 공유하는 것이 아니다.

M1 완료 조건은 두 종류의 캐릭터에서 ASC가 각각 하나이고 인터페이스가 그 인스턴스를 반환하며, ActorInfo가 그 캐릭터를 가리키고 기존 이동이 유지되는 것이다. Ability·Attribute·GameplayReady는 아직 없다. “기절하면 이동이 막힌다”는 M2, “공격/피격이 실행된다”는 M3에서 검증한다.

M1은 엔진 `UAbilitySystemComponent`를 사용한다. 중재 로직이 없는 빈 `UKhazanAbilitySystemComponent` subclass를 미리 만들지 않는다. M3에 실제 공통 Action 요청/관계 데이터 소비가 생기면 그때 subclass를 구현한다. M1부터 reflected 멤버는 엔진 base형, subobject 이름은 고정하여 후속 공개 계약을 보존한다.

## 2. 파일별 수정 위치와 책임

| 사용자 수정 예정 파일 | 변경 이유 |
| --- | --- |
| `Khazan.uproject` | 프로젝트가 Gameplay Abilities 플러그인을 명시적으로 사용하도록 한다. |
| `Source/Khazan/Khazan.Build.cs` | 공개 헤더의 GAS 인터페이스/ASC와 기반 Tasks 모듈을 컴파일·링크할 의존성을 선언한다. |
| `Source/Khazan/Character/KhazanCharacter.h` | 공통 Character의 인터페이스, ASC 참조, 초기화/빙의/종료 lifecycle을 선언한다. |
| `Source/Khazan/Character/KhazanCharacter.cpp` | 기존 생성자에 subobject를 추가하고 엔진 lifecycle에 연결한다. |

이번 단계에서 Player/Monster에 ASC를 각각 추가하면 안 된다. 부모가 이미 소유하기 때문이다. 현재 LocomotionComponent·Player 입력·AnimInstance·ABP의 동작은 첫 단계의 회귀 기준이며 이 단계에서 이관하지 않는다.

`KhazanAnimInstance.cpp`의 `GatherGameThreadData/NativeThreadSafeUpdateAnimation`은 계속 현행 경로를 사용한다. 새 ASC를 worker에서 조회하거나 공격/기절 bool을 여기에 추가하지 않는다.

## 3. 먼저 GAS 플러그인과 모듈을 연결한다

### 3.1 편집 전

- 현재 작업을 보존하고 PIE를 정상 종료한다. 이전 [continuity](ENGINEERING_WORK_CONTINUITY.md)에 디버거/검증 callback 정리 대기 기록이 있으므로 실제 현재 상태를 확인한다. 과거 PID로 강제 종료하지 않는다.
- 이번에는 native 상속/UPROPERTY/default subobject를 바꾸므로 에디터를 닫고 전체 빌드한 뒤 다시 연다. Live Coding의 성공만으로 새 reflected 구조의 검증을 대신하지 않는다.

### 3.2 Khazan.uproject

기존 `Plugins` 배열에 다음 객체를 추가한다. 전체 파일을 이 블록으로 교체하지 않는다. 앞 객체와의 쉼표를 맞추고 이미 같은 Name이 있으면 중복 추가하지 않는다.

```json
{
    "Name": "GameplayAbilities",
    "Enabled": true
}
```

- `Name`의 GameplayAbilities는 플러그인의 내부 식별자다.
- `Enabled: true`는 이 프로젝트에서 플러그인을 사용한다는 설정이다. 캐릭터에 ASC를 부착하거나 Ability를 부여하는 명령은 아니다.
- 에디터 UI로는 Edit → Plugins → “Gameplay Abilities”에 해당한다. 위 JSON을 편집했다면 UI에서 별도로 중복 작업하지 않고 다음 에디터 실행 때 활성화 여부를 확인한다.
- 현재 프로젝트에 이미 있는 PoseSearch 등 다른 플러그인 설정은 보존한다.

### 3.3 Khazan.Build.cs

현재 생성자의 기존 PublicDependencyModuleNames.AddRange 아래에 다음을 추가한다. 기존 목록에는 GameplayTags가 있으므로 중복 추가하지 않는다.

```csharp
PublicDependencyModuleNames.AddRange(new string[]
{
    "GameplayAbilities",
    "GameplayTasks"
});
```

- `PublicDependencyModuleNames`: 이 모듈의 공개 타입을 사용하는 쪽에도 필요한 모듈 의존성이다. Character 헤더에서 GAS 인터페이스를 상속하므로 Public에 둔다.
- `AddRange`: 기존 의존성을 유지하면서 두 항목을 더한다.
- `new string[]`: 모듈 이름의 목록이다.
- `GameplayAbilities`: ASC, Ability, Effect, AttributeSet 등의 GAS 타입을 제공한다.
- `GameplayTasks`: ASC가 상속하는 GameplayTasksComponent 및 비동기 작업 기반 모듈이다.
- 닫는 `});`는 목록과 호출의 끝이다. 현재 Core/Engine/EnhancedInput/GameplayTags/Cog 관련 항목을 없애지 않는다.

이 단계에서 MotionWarping/AIModule 등을 전부 선행 추가하지 않는다. 각각 실제 소비 단계에서 연결한다.

## 4. Character 헤더의 공통 계약을 추가한다

아래는 **기존 파일에 넣을 조각**이다. 현재 GetLocomotionComponent/BeginPlay/Tick/LocomotionComponent를 삭제하거나 같은 클래스를 두 번 선언하지 않는다.

### 4.1 Include와 전방 선언

`KhazanCharacter.generated.h`보다 위에 다음 include를 추가한다.

```cpp
#include "AbilitySystemInterface.h"
```

이 include는 상속할 인터페이스의 완전한 선언이 필요하기 때문이다. `KhazanCharacter.generated.h`는 계속 이 헤더의 마지막 include로 둔다.

기존 `class UKhazanLocomotionComponent;` 옆에 다음을 추가한다.

```cpp
class UAbilitySystemComponent;
```

여기서는 ASC의 포인터만 선언하므로 전방 선언으로 충분하다. ASC 함수를 호출하는 cpp에는 실제 헤더를 include한다.

### 4.2 클래스 선언

현재 클래스 선언 한 줄을 다음으로 바꾼다.

```cpp
class KHAZAN_API AKhazanCharacter : public ACharacter, public IAbilitySystemInterface
```

- `KHAZAN_API`: 모듈 밖에서 사용할 클래스의 export/import 지정이다.
- `public ACharacter`: 기존 캐릭터 상속을 유지한다.
- `public IAbilitySystemInterface`: GAS가 Player/Monster 구체 타입을 몰라도 ASC를 조회할 수 있게 한다.
- 이 인터페이스를 상속하는 것만으로 컴포넌트가 생성되지는 않는다. getter와 생성자를 아래에서 연결한다.
- 기존 UCLASS/GENERATED_BODY와 클래스 본문은 보존한다.

### 4.3 public 선언

기존 public 영역에 다음 세 선언을 추가한다.

```cpp
virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
virtual void PossessedBy(AController* NewController) override;
virtual void UnPossessed() override;
```

- 첫 함수는 인터페이스의 순수 가상 함수를 구현한다. 반환값은 현재 Character의 ASC를 가리키는 포인터다.
- `const`는 getter가 Character의 멤버를 바꾸지 않는다는 뜻이다. 반환한 ASC까지 불변이 되거나 worker 접근이 안전해지는 뜻은 아니다.
- `override`는 엔진/인터페이스와 정확히 같은 시그니처인지 컴파일러가 확인하게 한다.
- `PossessedBy`는 Controller가 Pawn을 소유할 때 엔진이 호출한다. `NewController`는 엔진이 넘긴 기존 객체의 포인터이며 여기서 생성하거나 해제하지 않는다.
- `UnPossessed`는 소유가 해제될 때 호출된다. 캐릭터 Actor 자체가 파괴되는 것과는 다르다.
- 이 단계는 싱글플레이다. 네트워크 클라이언트의 possession/OnRep 연결까지 구현한 것으로 해석하지 않는다.

### 4.4 protected 선언

기존 protected 영역에 다음을 추가한다. 기존 BeginPlay 선언은 그대로 둔다.

```cpp
virtual void PostInitializeComponents() override;
virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
```

- `PostInitializeComponents`: 컴포넌트 구성/초기화 뒤 호출된다. ASC 등록으로 ActorInfo 저장소가 준비된 뒤 Owner/Avatar를 연결할 지점이다.
- `EndPlay`: Actor가 플레이 수명에서 나갈 때 호출된다. `EndPlayReason`은 종료 이유를 나타내는 엔진 enum이다.
- 작은 enum은 값으로 전달하고 `const`로 함수 안의 재대입을 막는다. 객체 소유권을 가진 참조 인자가 아니다.
- 선언 순서가 실제 실행 순서를 정하지 않는다. 호출은 엔진 lifecycle이 수행한다.

### 4.5 private 멤버

기존 LocomotionComponent 멤버 옆에 추가한다.

```cpp
UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character|AbilitySystem", meta = (AllowPrivateAccess = "true"))
TObjectPtr<UAbilitySystemComponent> AbilitySystemComponent = nullptr;
```

- `UPROPERTY`: 엔진 reflection/객체 참조 추적과 에디터 노출에 참여한다.
- `VisibleAnywhere`: ASC 참조를 확인할 수 있도록 하며 디테일에서 임의 다른 참조로 교체하는 설정으로 만들지 않는다.
- `BlueprintReadOnly`: BP에서 읽는 접근을 제공한다. 참조 대상의 모든 함수 실행을 금지한다는 뜻은 아니다.
- `Category`: 에디터 표시 분류다. gameplay 상태 태그가 아니다.
- `AllowPrivateAccess`: C++ private 멤버에 대한 위 BP 읽기 노출을 허용한다.
- `TObjectPtr<UAbilitySystemComponent>`: Character가 보유할 UObject 컴포넌트 참조다. 수치 단위는 없다.
- `nullptr`: 멤버 초기화 시 아직 참조가 없음을 나타낸다. 생성자에서 default subobject를 만들어 즉시 연결한다.

## 5. cpp에 생성과 조회를 연결한다

기존 include에 다음 두 개를 추가한다. 관련 없는 기존 include 정리는 별도 작업으로 남긴다.

```cpp
#include "AbilitySystemComponent.h"
#include "Engine/World.h"
```

첫 헤더는 ASC 함수 호출/생성의 완전한 타입에, 두 번째는 UWorld::IsGameWorld 호출에 필요하다.

### 5.1 기존 생성자에 한 줄 추가

현재 LocomotionComponent 생성 줄 뒤에 추가한다.

```cpp
AbilitySystemComponent = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("AbilitySystemComponent"));
```

- `CreateDefaultSubobject<...>`: Actor 생성자에서 엔진이 관리하는 기본 subobject를 구성한다. BeginPlay마다 NewObject로 새 ASC를 만드는 코드가 아니다.
- `UAbilitySystemComponent`: 이 첫 단계에서 사용할 엔진 타입이다.
- `TEXT(...)`: 엔진 문자열 표현이다.
- `"AbilitySystemComponent"`: subobject의 안정적인 이름이다. BP 기본 객체/인스턴스와 연결되므로 후속 단계에서도 무심코 바꾸지 않는다.
- 대입은 생성된 컴포넌트를 멤버에 보관한다. 클래스 기본 객체에는 template가, 각 캐릭터 인스턴스에는 그 캐릭터의 subobject가 구성된다.
- 기존 PrimaryActorTick 설정과 LocomotionComponent 생성을 유지한다. 수십 캐릭터 최적화를 이유로 여기서 ACharacter의 Tick을 일괄 끄지 않는다.
- 생성자에서는 ActorInfo를 초기화하지 않는다. runtime world/Controller/등록 문맥이 아직 준비되지 않았다.

### 5.2 getter 구현

```cpp
UAbilitySystemComponent* AKhazanCharacter::GetAbilitySystemComponent() const
{
    return AbilitySystemComponent.Get();
}
```

반환형은 인터페이스의 UAbilitySystemComponent 포인터와 같고, `AKhazanCharacter::`는 어느 클래스의 구현인지 지정한다. `.Get()`은 TObjectPtr가 가리키는 객체 포인터를 반환한다. 복사된 ASC를 생성하지 않고 현재 인스턴스를 돌려준다. 이 함수 자체는 초기화/능력 부여/GameplayReady 판단을 하지 않는다.

## 6. ActorInfo 최초 연결

```cpp
void AKhazanCharacter::PostInitializeComponents()
{
    Super::PostInitializeComponents();

    const UWorld* World = GetWorld();
    if (World && World->IsGameWorld())
    {
        AbilitySystemComponent->InitAbilityActorInfo(this, this);
    }
}
```

- `void`: 반환값 없이 lifecycle 처리를 수행한다.
- `Super::PostInitializeComponents()`: ACharacter/APawn의 기존 초기화가 먼저 수행되게 한다.
- `const UWorld* World`: 이번 호출에서만 쓰는 지역 참조다. 멤버로 추가하지 않는다. 포인터를 통해 World를 변경하지 않는다.
- `GetWorld()`: 이 Actor가 속한 World를 얻는다.
- `World && ...`: World가 없으면 뒤의 호출을 하지 않는 단락 평가다.
- `IsGameWorld()`: 실제 게임/PIE world에서만 GAS ActorInfo를 연결한다. 에디터 preview에서 이 코드를 gameplay 초기화로 취급하지 않는다.
- `InitAbilityActorInfo(this, this)`: 첫 this는 능력의 논리 소유자, 두 번째 this는 실제 행동하는 Avatar다. v2에서는 둘 다 현재 Character다.
- 여기의 OwnerActor는 GAS ActorInfo의 의미다. AActor::GetOwner()가 Controller 등 무엇을 반환하는지와 같은 개념으로 혼동하지 않는다.
- ASC는 생성자에서 반드시 생성하는 native default subobject다. 데이터 미로드를 이유로 이 멤버가 없어도 정상 진행하도록 설계하지 않는다. 누락/중복은 아래 인스턴스 검사에서 원인을 확인한다.

로컬 UE 5.8.2의 ASC OnRegister가 ActorInfo 저장소를 할당하고, InitAbilityActorInfo가 그 저장소의 유효성을 검사한다. 이 때문에 생성자가 아닌 컴포넌트 초기화 뒤에 호출한다.

**이 호출은 액션 준비 완료가 아니다.** 초기 Attribute, AbilitySet, 표현/이동/입력·AI 연결 후의 GameplayReady는 M3에서 제공한다.

## 7. 빙의 변화는 참조만 갱신한다

```cpp
void AKhazanCharacter::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);

    if (AbilitySystemComponent->GetAvatarActor_Direct() == this)
    {
        AbilitySystemComponent->RefreshAbilityActorInfo();
    }
}
```

- `NewController`를 부모 함수에 전달해 실제 Pawn 소유 처리부터 완료한다.
- `GetAvatarActor_Direct()`는 ASC에 연결된 Avatar 포인터를 읽는다.
- `== this`는 값 복사나 새 설정이 아니라 같은 Actor를 가리키는지 비교한다.
- Avatar가 이미 이 Character이면 초기 연결이 끝난 것이므로 RefreshAbilityActorInfo로 현재 Controller/관련 컴포넌트 참조를 다시 수집한다.
- 아직 초기 연결 전이면 이 분기는 건너뛴다. APawn의 초기화 내부에서 먼저 빙의될 수 있는데, 그 경우 부모 초기화가 돌아온 뒤 6절의 InitAbilityActorInfo가 최신 Controller를 포함해 연결한다.
- 어느 순서든 Init을 매번 재호출하지 않는다. UE 5.8.2의 InitAbilityActorInfo에는 몽타주 추적 구조를 초기화하는 코드가 있다. 같은 Avatar의 단순 참조 갱신에는 Refresh를 사용한다.

```cpp
void AKhazanCharacter::UnPossessed()
{
    Super::UnPossessed();

    if (AbilitySystemComponent->GetAvatarActor_Direct() == this)
    {
        AbilitySystemComponent->RefreshAbilityActorInfo();
    }
}
```

- 부모가 Controller 연결을 해제한 뒤 참조를 갱신한다.
- 같은 Avatar 검사로 초기화된 ASC만 갱신한다.
- Actor가 계속 존재하므로 ASC/HP/상태 효과 전체를 지우지 않는다.
- PlayerController 참조는 해제 후 비어 있을 수 있다. AIController가 소유한 Monster도 ActorInfo의 PlayerController가 null인 것이 정상일 수 있다.
- 아직 액션이 없는 M1에서는 참조 갱신만 구현한다. M3에 입력 버퍼/진행 중 액션이 생길 때 빙의 해제의 요청 차단·자기 실행 취소 정책을 실제 소비 경로에 연결한다.

메시/관련 컴포넌트가 바뀌는 후속 장비/표현 작업에서도 유효한 ActorInfo 갱신 시점을 정한다. Tick에서 매번 Init/Refresh하지 않는다.

## 8. Actor 종료 시 실행 정리

```cpp
void AKhazanCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    AbilitySystemComponent->DestroyActiveState();

    Super::EndPlay(EndPlayReason);
}
```

- `DestroyActiveState()`: Actor 수명이 끝나는 시점의 GAS 실행/능력 인스턴스 정리를 요청한다. 일반 피격 취소에 사용하는 함수가 아니다.
- 로컬 UE 5.8.2에서는 재진입 방지 상태를 설정하고 실행을 취소하며, 권한 있는 소유자에서는 취소 불가능한 능력까지 종료 정리할 ClearAllAbilities 경로를 호출한다.
- `Super::EndPlay(EndPlayReason)`: 같은 종료 이유로 부모의 Actor/Component 종료를 계속 수행한다.
- ASC의 OnUnregister도 DestroyActiveState를 호출한다. 엔진 함수의 재진입 방지 덕분에 이 호출을 중복 능력 종료로 구현하지 않는다.
- ActorInfo를 먼저 ClearActorInfo로 비우지 않는다. 종료 callback/Ability가 아직 소유자와 실행 문맥을 사용할 수 있어야 한다.
- DestroyActiveState를 “모든 GameplayEffect/태그/프로젝트 handle을 삭제하는 만능 함수”로 설명하지 않는다. M3 이후 자기 효과·제약·delegate·로드 handle은 프로젝트 실행/부여 소유자가 먼저 정리한다.
- M1에는 새 액션/효과가 없으므로 이번 검사는 종료 경로가 정상 호출되는 범위다. 실제 활성 액션 취소 cleanup은 M3에서 따로 검증한다.
- v2 체크포인트는 새 Pawn 구성이다. 동일 Pawn 풀링/재등록의 능력 재부여를 이번 코드가 완성했다고 보지 않는다.

## 9. 변수·함수 전체 계약

| 항목 | 작성자/소비자 | 초기화·갱신·해제 | 스레드/공유 |
| --- | --- | --- | --- |
| AbilitySystemComponent | Character 생성자 작성, IAbilitySystemInterface/GAS 조회 소비 | nullptr 초기 표현→default subobject; Actor와 함께 종료. 매 요청 생성 금지 | native lifecycle GT, Player/Monster 모두 같은 부모 구현 |
| World 지역값 | PostInitializeComponents 작성/소비 | 호출 동안만 존재 | GT, shared 멤버 없음 |
| NewController 인자 | 엔진이 전달, 부모 PossessedBy 소비 | callback 동안 사용; 저장/해제하지 않음 | GT, Player/AI Controller 공통 |
| EndPlayReason 인자 | 엔진 전달, 부모 EndPlay 소비 | 작은 enum 값, 이 함수에서 수정하지 않음 | GT |
| ASC ActorInfo | Init/Refresh가 엔진 내부 값 작성, Ability/Task가 소비 | PostInitialize 최초 연결, 이후 빙의/실제 참조 변경에 Refresh | GT. worker snapshot과 다름 |
| GetAbilitySystemComponent | 인터페이스 조회, 포인터 반환 | 상태 변경/초기화 없음 | const는 thread-safe 선언이 아님 |

호출 관계는 다음과 같다.

```text
생성자: ASC default subobject 구성
 → ASC OnRegister: 엔진 ActorInfo 저장소 준비
 → Character PostInitializeComponents:
      Super 실행 중 빙의가 먼저 올 수 있음
      gameplay world에서 Owner/Avatar 초기 연결
 → BeginPlay: 현재 부모 호출 유지
 → 이후 PossessedBy/UnPossessed: 연결되어 있으면 참조 Refresh
 → EndPlay: DestroyActiveState 후 Super
 → ASC OnUnregister: 엔진 종료 경로
```

같은 단계의 모든 Actor/Component Tick에 절대적인 전역 순서가 있다는 뜻이 아니다. 위는 이 코드가 의존하는 lifecycle 관계다.

## 10. 에디터·빌드·런타임 확인

### 10.1 빌드

1. 에디터를 정상 종료하고 변경한 Source/uproject/Build.cs를 저장한다.
2. Rider에서 프로젝트 변경을 반영한다. 필요한 경우 uproject의 Generate Visual Studio project files로 프로젝트 정보를 재생성한다.
3. `KhazanEditor / Win64 / Development` 대상을 전체 빌드한다. 기존 엔진 설치는 `C:/Program Files/Epic Games/UE_5.8`다.
4. 빌드 성공 후 프로젝트를 새 에디터 프로세스로 연다. 플러그인 활성화 오류와 native class/UPROPERTY 로딩 오류가 없는지 확인한다.
5. 기존 Player BP와 ABP_Player를 열어 Compile 결과를 확인한다. ABP가 정상 재생되는지 확인하되 이번 단계 때문에 그래프를 재작성하지 않는다.

수동 빌드 명령이 필요하면 저장소 루트 PowerShell에서 다음 명령을 사용한다. 어시스턴트가 실행한 결과가 아니다.

```powershell
& 'C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat' KhazanEditor Win64 Development '-Project=C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' -WaitMutex
```

`&`는 공백이 포함된 실행 파일을 호출한다. KhazanEditor/Win64/Development는 빌드 대상·플랫폼·구성이며 gameplay 수치가 아니다. Project 인자는 현재 프로젝트 경로, WaitMutex는 동시 빌드 충돌을 조정하는 UBT 옵션이다.

### 10.2 인스턴스와 인터페이스

- 현재 GameMode가 생성하는 Player BP에서 inherited AbilitySystemComponent가 하나인지 확인한다. 저장 구조 문서의 Player 경로는 `/Game/Bluprints/BP_KhazanCharacter`이며, 현재 맵에서 실제 생성되는 클래스를 우선한다.
- BP에 수동으로 추가한 ASC가 이미 있었다면 native 추가로 둘이 되는지 먼저 확인한다. 기존 사용자 컴포넌트를 자동 삭제하지 않고 어느 경로가 사용되는지 확인한 뒤 이관한다.
- Monster는 부모 `AKhazanCharacter`를 통해 같은 컴포넌트를 상속한다. 기존 테스트 Monster가 없으면 Content Browser의 C++ Classes/Khazan/Character에서 KhazanMonster를 임시 배치해 상속 구성을 확인할 수 있다. 이 단계의 ASC 검사에는 새 몬스터 아트 임포트가 필요하지 않다.
- GAS Blueprint Library의 Get Ability System Component 노드는 이 Actor의 인터페이스를 통해 같은 ASC를 얻어야 한다. 컴포넌트 존재와 인터페이스 반환값이 같은지 확인한다. 검사용 임시 노드를 만들었다면 제품 로직으로 남기지 않는다.

### 10.3 PIE와 lifecycle

1. PIE에서 PostInitializeComponents의 InitAbilityActorInfo 호출 뒤 상태를 확인한다.
2. Player와 임시/기존 Monster에서 각각 ASC의 OwnerActor와 AvatarActor가 해당 Pawn인지 확인한다. 서로의 ASC를 참조하면 실패다.
3. PlayerController 참조는 실제 빙의 상태에 맞아야 한다. Monster의 PlayerController=null만으로 실패라고 판단하지 않는다.
4. 초기화보다 먼저/나중에 빙의되는 두 경로를 확인한다. 이후 소유 해제·재빙의에서는 같은 ASC의 Owner/Avatar를 유지하면서 Controller 참조가 갱신되는지 확인한다.
5. Walk/Run/L3 Sprint/입력 해제 Stop/재입력을 기존 관측과 비교한다. 현재 Stop의 미검증 항목을 이번 ASC 검사만으로 통과 처리하지 않는다.
6. PIE 종료/Actor 종료에서 EndPlay와 GAS 정리 경로가 오류 없이 끝나는지 확인하고, 새 PIE의 새 Pawn에는 새 ASC가 만들어지는지 확인한다.

디버거/값 검사가 필요하면 현재 세션과 현재 소스를 기준으로 위치를 정한다. 과거 Stop 작업의 breakpoint line/PID를 그대로 사용하지 않는다. 어시스턴트가 실제 runtime을 조사할 때는 해당 debugger 절차를 별도로 따른다.

### 10.4 실패 증상과 확인 위치

| 증상 | 먼저 확인할 항목 |
| --- | --- |
| AbilitySystemInterface.h를 찾지 못함/링크 오류 | 플러그인 Name/Enabled, GameplayAbilities 모듈, 프로젝트 갱신/전체 빌드 |
| override 오류 | GetAbilitySystemComponent의 반환형·const, IAbilitySystemInterface 상속, 콜백 시그니처 |
| generated header/UHT 오류 | generated.h가 마지막 include인지, 클래스 중복/UPROPERTY 배치 |
| ASC가 둘임 | 부모 native subobject와 BP 수동 컴포넌트/자식 생성의 중복 |
| 인터페이스 조회가 null | 실제 Pawn 부모/로드된 DLL, getter 반환, 새 native 상속 반영 여부 |
| Owner/Avatar가 null | gameplay world guard, PostInitializeComponents 실행 여부, 부모 호출, 오래된 DLL |
| Controller 참조가 오래됨 | PossessedBy/UnPossessed에서 Super 뒤 Refresh 여부, 초기화 전 guard |
| 이동/Stop이 달라짐 | 이 단계 밖의 Source/CMC/BP 변경이 섞였는지 현재 diff 확인 |
| 종료에서 오류 | ActorInfo를 먼저 비웠는지, 프로젝트/엔진 중복 cleanup 구현 여부, 현재 실행/종료 순서 |

## 11. 실제 검사한 범위와 다음 단계

- 어시스턴트 확인: 현재 Character/Player/Monster 상속과 생성자, 기존 모듈/태그/입력/AnimInstance 경계, UE 5.8.2 엔진 함수 선언·구현. 저장된 표적 리포트 대상 게임 파일 39개의 동일 hash.
- 어시스턴트 미수행: 이 제안 코드의 Source 적용/UHT·컴파일/에디터 재시작/BP Compile/PIE/빙의·종료 시험. 본문은 실행 결과가 아니다.
- 사용자 적용 후 기록할 것: 실제 변경 파일, 빌드 결과, 각 캐릭터의 ASC/Owner/Avatar 확인, 기존 이동 결과, 실패/미검증 항목.
- M1 완료 뒤 M2에서 최소 태그의 실제 소비와 원인별 이동 제약을 붙인다. M1 다음에 빈 HFSM/AttackState/LocomotionMath부터 생성하지 않는다.

## 12. 엔진 근거

- 설치 소스: `C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/Runtime/GameplayAbilities/Source/GameplayAbilities`.
- Public/AbilitySystemInterface.h: GetAbilitySystemComponent() const 선언.
- Private/AbilitySystemComponent.cpp: OnRegister의 ActorInfo 할당, OnUnregister의 DestroyActiveState.
- Private/AbilitySystemComponent_Abilities.cpp: InitAbilityActorInfo, RefreshAbilityActorInfo, DestroyActiveState의 실제 동작.
- Private/GameplayAbilityTypes.cpp: Owner/Avatar/Controller/컴포넌트 참조 수집.
- Public/AbilitySystemComponent.h: public API와 UGameplayTasksComponent 상속.
- [공식 GAS 구성](https://dev.epicgames.com/documentation/ko-kr/unreal-engine/gameplay-ability-system-for-unreal-engine)
- [InitAbilityActorInfo](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/GameplayAbilities/UAbilitySystemComponent/InitAbilityActorInfo)
- [RefreshAbilityActorInfo](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/GameplayAbilities/UAbilitySystemComponent/RefreshAbilityActorInfo)

이 자료는 엔진 API/수명 근거다. 원작 카잔의 상태 구조·프레임 타이밍·스태미나·피해 수치를 확인한 자료가 아니다.



<a id="m1-resume-detail-20260909"></a>

## 2026-09-09 — M1 공동 구현 재개: 개념·조립 위치·검증 보충

사용자가 자체 Tag-FSM 대안을 철회하고 GAS 기반 기존 마이그레이션을 계속하기로 확정했다. 위 본문의 M1 구현 계약은 유지한다. 이번 요청은 사용자가 직접 따라 할 상세 설명이며 아래 코드를 실제 게임 파일에 적용/빌드/PIE 완료한 것은 아니다.

### 이번 단계의 정확한 결과

현재 Player와 Monster는 각각 AKhazanCharacter의 자식이다. 공통 부모의 생성 코드가 각 Pawn마다 별개의 ASC를 구성한다. 다른 캐릭터의 ASC와 전역 인스턴스를 공유하는 구조가 아니다.

| 준비 수준 | M1 종료 시 기대 | 뒤 단계 |
| --- | --- | --- |
| ASC UObject가 존재 | 각 Character에 기본 subobject 하나 | M3에서 실제 중재 로직이 필요할 때 구체 타입 확장 |
| 엔진이 ASC를 조회 | IAbilitySystemInterface가 같은 인스턴스를 반환 | Player/AI의 공통 액션 요청이 소비 |
| ActorInfo가 연결 | Owner와 Avatar가 그 Character, Controller 참조가 현재 상태와 일치 | 장비/표현 등 실제 참조 변화 때 갱신 |
| 초기 수치·능력·태그 정책·게임플레이 준비 | M1에는 아직 부여하지 않음 | M2 최소 이동 정책, M3 능력/속성/Ready |
| 기존 이동·Stop·ABP | 기존 동작 유지가 회귀 기준 | M4에서 Locomotion 표현 분리 |

컴포넌트 생성은 UObject 구성, Init은 능력이 사용할 실행 대상 연결, Refresh는 같은 소유자/Avatar의 관련 참조 재수집이다. BeginPlay가 왔다거나 ASC 포인터가 유효하다는 사실만으로 AbilitySet/데이터 준비 완료를 선언하지 않는다.

### ASC·인터페이스·ActorInfo를 구분한다

- ASC는 캐릭터에 실제로 붙는 UObject 컴포넌트다. 이후 능력 목록/효과/공유 태그와 실행 중재가 이 기반을 사용한다.
- IAbilitySystemInterface는 “이 Actor의 ASC를 돌려준다”는 C++ 계약이다. 인터페이스 자체는 ASC를 생성하지 않는다. 엔진의 UAbilitySystemInterface는 reflection용, IAbilitySystemInterface는 우리가 C++로 구현할 쪽이다. U 인터페이스 클래스를 ACharacter와 다중 상속하지 않는다.
- UAbilitySystemBlueprintLibrary의 GetAbilitySystemComponent처럼 엔진의 Actor→ASC 조회 경로가 이 getter를 소비한다. 액션이 Player/Monster 타입별 캐스팅을 반복하는 구조를 피한다.
- ActorInfo는 GAS 내부의 FGameplayAbilityActorInfo 문맥이다. 프로젝트에서 같은 Owner/Avatar/Controller 변수를 별도로 만들지 않는다.
- GAS OwnerActor는 능력의 논리 소유자, AvatarActor는 실제 행동하는 월드 Actor다. M1에서는 둘 다 this다. 플레이어의 Owner가 PlayerController, 몬스터의 Owner가 AIController라는 뜻이 아니다.
- Pawn 자체의 AActor::GetOwner()는 빙의 과정에서 Controller가 될 수 있다. 이것과 GAS ActorInfo의 OwnerActor를 혼동하지 않는다.
- ActorInfo의 PlayerController는 APlayerController 참조다. AIController가 붙은 Monster에서 null일 수 있으며 그 자체로 초기화 실패가 아니다.
- Character 생성자가 ASC 참조를 작성하고 엔진/GAS 조회가 소비한다. native default subobject와 UPROPERTY/TObjectPtr 참조로 수명을 관리하며 delete나 매 Tick 재생성을 하지 않는다.

### 헤더 조각을 넣은 뒤의 배치 확인

아래는 본문 4절을 현재 헤더에 조립한 형태다. 선언 위치 확인용이며 기존 사용자 변경이 있으면 그 변경을 보존해 병합한다. cpp 구현을 이 헤더에 추가로 복제하지 않는다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AbilitySystemInterface.h"
#include "KhazanCharacter.generated.h"

class UKhazanLocomotionComponent;
class UAbilitySystemComponent;

UCLASS()
class KHAZAN_API AKhazanCharacter : public ACharacter, public IAbilitySystemInterface
{
    GENERATED_BODY()

public:
    AKhazanCharacter();

    UKhazanLocomotionComponent* GetLocomotionComponent() const
    {
        return LocomotionComponent;
    }

    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
    virtual void PossessedBy(AController* NewController) override;
    virtual void UnPossessed() override;

protected:
    virtual void PostInitializeComponents() override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

public:
    virtual void Tick(float DeltaTime) override;

private:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character|Locomotion", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UKhazanLocomotionComponent> LocomotionComponent;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character|AbilitySystem", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UAbilitySystemComponent> AbilitySystemComponent = nullptr;
};
```

추가되는 include/전방 선언/상속/함수/프로퍼티 각각의 의미는 본문 4절을 따른다. 기존 Locomotion getter, BeginPlay, Tick 선언은 의미가 바뀌지 않았다.

- generated.h는 마지막 include이며 전방 선언은 그 다음이다. 상속할 IAbilitySystemInterface에는 실제 헤더, 포인터로만 표현할 ASC에는 전방 선언을 사용한다.
- public/protected/private는 C++ 접근 범위다. protected에 둔 엔진 callback도 virtual 호출로 실행된다. 헤더에서 선언한 순서대로 실행되는 것이 아니다.
- getter의 const는 Character 멤버를 변경하지 않는 접근이다. 반환 타입은 UAbilitySystemComponent*이므로 반환 대상의 모든 동작을 금지하지 않으며 worker-safe 선언도 아니다.
- TObjectPtr의 초기 nullptr는 생성 전 표현이다. 생성자에서 필수 default subobject를 연결하므로 runtime에 이 참조가 없는 것은 정상적인 “데이터 로드 대기”가 아니다.
- UPROPERTY의 VisibleAnywhere/BlueprintReadOnly는 참조 노출 방식이다. 참조 대상 컴포넌트의 내부 설정과 모든 메서드까지 불변이라는 뜻은 아니다.
- 선언한 함수는 cpp에 각각 한 번 구현한다. 기존 생성자/BeginPlay/Tick 함수 본문을 또 만들지 않는다.

### 생성과 초기화를 나누는 이유

CreateDefaultSubobject는 클래스 기본 객체/파생 BP의 기본 구성과 실제 인스턴스 생성에도 관여한다. 생성자 시점에는 gameplay world, Controller, 컴포넌트 등록 문맥이 완성되지 않았다. 따라서 ASC만 만들고 InitAbilityActorInfo는 여기서 호출하지 않는다.

로컬 UE 5.8.2의 ASC OnRegister에서 AbilityActorInfo 저장소가 만들어진다. Character의 PostInitializeComponents에서 Super를 호출한 뒤 gameplay world임을 확인하면 등록/초기화 이후 Owner/Avatar를 연결할 수 있다. 이번 프로젝트는 BeginPlay 전에 이 연결을 끝내는 계약을 사용한다.

본문의 World 변수는 const UWorld*인 지역 포인터다. const는 이 포인터를 통해 World를 변경하지 않는다는 뜻이며 포인터 변수의 재대입을 막는 const pointer 선언과는 다르다. World가 null이면 &&의 단락 평가로 IsGameWorld를 호출하지 않는다. 실제 PIE/game world에서만 Init을 수행하며 에디터 일반 world/preview의 컴포넌트 존재를 gameplay 준비 완료로 읽지 않는다.

### 빙의가 먼저 발생하는 경우와 나중에 발생하는 경우

**부모 초기화 중 AI 빙의가 먼저 발생하는 경우**

1. native 생성자에서 ASC 구성 → 엔진 등록으로 ActorInfo 저장소 준비.
2. AKhazanCharacter::PostInitializeComponents의 Super 호출 안에서 APawn의 자동 AIController 생성/빙의가 발생할 수 있다.
3. PossessedBy에서 먼저 Super가 Controller를 연결한다. 아직 프로젝트 Init 전이므로 ASC Avatar가 this가 아니어서 Refresh는 생략한다.
4. 부모 초기화가 끝나면 Character의 InitAbilityActorInfo(this, this)가 현재 Controller를 포함해 최초 연결한다.

**초기 연결이 끝난 후 플레이어 등의 빙의가 발생하는 경우**

1. InitAbilityActorInfo로 Owner/Avatar를 연결한다. 이 시점에 PlayerController가 없을 수도 있다.
2. 이후 PossessedBy의 Super가 새 Controller를 연결한다.
3. Avatar가 this이므로 RefreshAbilityActorInfo가 현재 Controller/컴포넌트를 다시 수집한다.

이는 대표 순서이며 Player는 반드시 늦고 AI는 반드시 빠르다는 보장은 아니다. 두 경로를 같은 코드로 처리한다. 별도 bASCInitialized를 추가해 같은 준비 사실을 중복 소유하지 않는다.

UnPossessed도 Super가 Controller를 해제한 뒤 Refresh한다. Pawn이 남아 있는 빙의 해제와 Pawn 수명의 종료는 다르다. M1에서는 ASC Owner/Avatar를 유지하며, 입력/액션 취소 정책은 실제 액션이 생기는 M3에서 연결한다.

### 종료와 스레드 경계

- EndPlay의 DestroyActiveState는 해당 Actor 플레이 수명 종료에 사용한다. 일반 피격, 무기 교체, 잠깐 입력 금지에서 호출하지 않는다.
- Super::EndPlay보다 먼저 호출하여 Ability 종료가 Owner/Avatar/컴포넌트 문맥을 이용할 수 있게 한다. 앞에 ClearActorInfo를 넣어 종료 문맥부터 지우지 않는다.
- ASC OnUnregister에서도 엔진이 같은 종료 함수를 호출하며 재진입 방지 상태로 반복 정리를 통제한다. M1에서 이를 복제하는 별도 정리 bool/helper를 만들지 않는다.
- EndPlayReason은 엔진의 종료 사유 enum이며 게임플레이 상태 enum을 새로 만드는 일이 아니다. const 값 인자는 함수 내부 재대입을 막고 그대로 부모에 전달한다.
- runtime의 Init/Refresh/EndPlay와 프로젝트 GAS 접근은 Game Thread에서 처리한다. UObject 생성자도 worker에서 호출해도 되는 업무 함수라고 해석하지 않는다.
- 현재 NativeThreadSafeUpdateAnimation은 snapshot을 소비한다. ASC를 여기에 직접 읽거나 쓰지 않으며, M1은 AnimInstance/ABP를 편집하는 단계가 아니다.

### 에디터에서 직접 확인할 구체적인 절차

본문 10절의 전체 빌드/새 Editor 절차를 먼저 따른다. 플러그인 JSON 편집과 UI 활성화는 같은 설정에 대한 두 접근이며 중복 등록하지 않는다.

1. 저장 구조 기준 Player BP는 /Game/Bluprints/BP_KhazanCharacter다. 열어서 Class Settings의 Parent Class와 Components의 inherited AbilitySystemComponent를 확인한다. 맵/월드 설정에서 실제 사용하는 Pawn이 이 BP인지도 확인한다. BP의 Add Component로 ASC를 또 붙이지 않는다.
2. ABP는 /Game/_Art/Kazan/Character/Bluprints/ABP_Player다. 기존 Compile/부모 로드 상태를 확인하며 그래프나 native parent를 새로 바꾸지 않는다.
3. 기존 테스트 Monster가 없으면 C++ Classes → Khazan → Character의 KhazanMonster를 테스트 맵에 임시 배치할 수 있다. SkeletalMesh가 없더라도 Pawn/ASC 수명 검사는 가능하다. 이 검사를 위해 AI/공격/새 몬스터 아트를 먼저 만들 필요는 없다.
4. BP 조회 검사가 필요하면 Get Ability System Component(AbilitySystemBlueprintLibrary) 노드의 Actor에 검사할 Pawn을 연결한다. Player BP에서는 Self, 임시 Level BP 검사에서는 Outliner에서 참조한 Monster다.
5. 위 Return Value를 순수 Is Valid(Object)의 Object에 연결하고 bool을 문자열로 변환해 Print String의 In String에 연결한다. 임시 실행선은 기존 BeginPlay의 연결을 보존한 Sequence의 별도 Then 출력에 둔다. 이 노드는 조회 평가를 실제 발생시키기 위한 임시 검사다.
6. C++ GetAbilitySystemComponent의 return 줄에 사용자 검사용 breakpoint를 두면 해당 조회가 인터페이스 getter에 들어왔는지 볼 수 있다. Player/Monster별 this와 AbilitySystemComponent를 확인한다. 엔진의 컴포넌트 fallback 검색만 성공한 상태와 인터페이스 경유를 구분한다.
7. InitAbilityActorInfo 호출 줄에 멈췄다면 실행 전 값으로 판정하지 말고 Step Over 후 ASC의 AbilityActorInfo를 펼친다. OwnerActor/AvatarActor는 해당 this, AbilitySystemComponent는 소유 ASC여야 한다. PlayerController는 실제 빙의 상태에 맞춰 판정한다.
8. 소유 해제/재빙의 검사가 필요하면 임시 테스트 이벤트에서 원래 Controller와 Pawn 참조를 먼저 보존하고 UnPossess(Target=Controller) → Possess(Target=같은 Controller, In Pawn=보존 Pawn)를 실행한다. 각 Super 뒤 Refresh에서 같은 ASC/Owner/Avatar를 유지하며 Controller 참조가 비워지고 다시 연결되는지 확인한다. UnPossess 후 Get Pawn을 다시 읽어 원래 Pawn을 찾으려 하면 이미 null일 수 있다.
9. PIE 종료와 새 PIE에서 EndPlay 정리, 새 Pawn의 새 ASC를 확인한다. 이전 세션 포인터와 실행을 재사용하지 않는다. M1에는 활성 Ability가 없으므로 실제 공격 중단 검증은 아직 할 수 없다.
10. 새로 만든 임시 검사 노드/참조/변수/배치/사용자 검사용 breakpoint는 검사 후 자기 작업분만 정리한다. 기존 게임 흐름이나 기존 사용자의 디버거 설정을 일괄 삭제하지 않는다.

위 절차는 사용자 적용 후 수행할 검사다. 이번 설명에서 Editor 조작, BP 노드 생성, breakpoint 설치, 빌드/PIE를 실행하지 않았다. 앞선 Stop 검증의 과거 PID/예약 callback 상태도 이번에 해소된 것으로 기록하지 않는다.

### 이번 실제 확인과 다음 진행

- 현재 KhazanCharacter.h/.cpp, Player/Monster 상속, Build.cs/uproject, AnimInstance snapshot 경계를 재확인했다. M1 코드/플러그인 직접 연결은 아직 적용 전이다.
- UE 5.8.2의 AbilitySystemInterface, ASC OnRegister/OnUnregister, Init/Refresh/DestroyActiveState, ActorInfo InitFromActor, APawn 초기화/빙의 순서와 공식 API를 정적으로 대조했다. 기존 M1 제안 코드를 변경할 필요는 확인되지 않았다.
- 저장 표적 리포트 대상 게임 파일 39개가 동일 SHA256이다. 문서 보충만 수행했으며 새 gameplay 수치도 도입하지 않았다.
- 사용자 적용 후 M1의 빌드·Player/Monster ASC/인터페이스·ActorInfo·빙의 갱신·종료·기존 이동 결과를 기록한다. 실패는 원인과 실제 상태를 남긴다. M1 완료가 확인되면 M2의 최소 태그/원인별 공통 이동으로 진행한다.


### 같은 작업 후속 확인 — 플러그인 활성화는 이미 반영됨

- 상세 안내 준비 중 Khazan.uproject가 변경되어 Plugins에 GameplayAbilities / Enabled=true가 추가된 것을 확인했다. 본문 3.2의 JSON 항목은 이제 추가 대상이 아니라 확인 대상이다. 같은 Name을 다시 넣지 않는다.
- 마지막 파일 비교에서는 나머지 표적 게임 파일 38개가 기준과 같고, Build.cs의 GameplayAbilities/GameplayTasks 및 Character의 ASC/Interface/lifecycle은 아직 없다. 본문 3.3 이후를 현재 소스에 맞춰 적용한다. 사용자가 계속 편집할 수 있으므로 다음 단계마다 이미 반영한 조각은 중복 작성하지 않는다.
- 앞선 ‘39개 동일’은 변경 전 검사 시점의 결과다. 최종 확인에서는 uproject만 위 이유로 달랐다. 어시스턴트는 게임 파일을 수정하지 않았고 새 빌드/Editor 로드/PIE 결과도 확인하지 않았다.



## 2026-09-09 — 사용자 M1 완료 보고와 소스 확인

- 사용자가 M1을 마쳤다고 보고했다. 실제 Khazan.uproject/Build.cs/KhazanCharacter.h/.cpp에서 플러그인·모듈·기본 ASC·인터페이스·ActorInfo 최초 연결/빙의 갱신·EndPlay 종료가 반영된 것을 확인했다.
- 현재 사용자 코드의 주석/배치와 관련 없는 include 정리는 보존했다. M1 예제의 포맷으로 되돌리는 작업은 하지 않았다.
- 이번 확인은 Source 반영과 구조 대조다. 사용자의 “완료” 보고를 개별 빌드/PIE/모든 빙의 경우의 어시스턴트 검증으로 바꾸지 않는다.
- 다음 공동 구현은 [M2.1](CHARACTER_TAG_ABILITY_STEP_2.md)이다. M1 코드를 중복 추가하지 않는다.

