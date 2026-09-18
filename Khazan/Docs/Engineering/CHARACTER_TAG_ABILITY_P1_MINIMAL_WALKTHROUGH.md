# Character Tag–Ability P1 최소 공동 구현 실습판

<a id="p1-minimal-walkthrough-v2-3-20260915"></a>
## 2026-09-15 — v2.3 기준과 현재 상태

이 문서는 사용자가 게임 Source와 Editor asset을 직접 적용하고, 어시스턴트가 각 책임·타입·줄·수명·검증을 설명하는 공동 구현용 문서다. 과거 `CHARACTER_TAG_ABILITY_P1_WALKTHROUGH.md`의 ActionRequest/Execution ID/full-body lane 코드는 사용하지 않는다.

현재 확인된 기반은 다음과 같다.

- `Khazan.uproject`는 UE 5.8을 사용하며 `GameplayAbilities` plugin이 이미 `Enabled: true`다.
- `Khazan.Build.cs`에는 `GameplayTags`, `GameplayAbilities`, `GameplayTasks`가 이미 public dependency로 들어 있다.
- `AKhazanCharacter`는 `IAbilitySystemInterface`를 구현하고 엔진 기본 `UAbilitySystemComponent`를 default subobject로 가진다.
- `PostInitializeComponents()`의 `InitAbilityActorInfo(this, this)`, Possess/UnPossess refresh, EndPlay의 `DestroyActiveState()`가 이미 있다.
- 기존 `Input.Action.Attack`과 `Input.Action.Jump` native tag가 있다.
- PlayerController의 Attack callback은 비어 있고 Jump callback은 현재 `ACharacter::Jump()`를 직접 호출한다.
- P1 Source는 아직 적용되지 않았다.

최신 책임 계약은 다음 문서를 따른다.

1. `CHARACTER_GAMEPLAY_ARCHITECTURE.md#architecture-v2-3-capability-components-20260915`
2. `CHARACTER_TAG_ABILITY_MIGRATION.md#p1-v2-3-capability-component-migration-20260915`
3. 이 문서의 현재 checkpoint

## P1 전체 목표

P1이 끝나면 다음 한 경로가 실제로 동작해야 한다.

```text
Enhanced Input의 Attack Started
    ↓ 기존 Input.Action.Attack
Khazan ASC가 같은 Input Tag로 grant된 Ability Spec을 찾음
    ↓ 엔진 TryActivateAbility
BasicAttack Ability가 활성화됨
    ↓ Ability가 자기 실행 자원을 소유
Montage + 필요한 Locomotion constraint
    ↓ 모든 종료 경로
AbilityTask 종료 + 자기 constraint만 release + EndAbility
```

Jump도 같은 기반으로 옮기되, 첫 checkpoint에는 넣지 않는다. 공격 적중, 피해, Stamina, combo, 회피, guard, parry, AI, StateTree, CombatComponent도 아직 넣지 않는다.

## P1.1에서 실제로 할 일

첫 checkpoint의 목표는 다음 한 문장이다.

> 기존 ASC lifecycle은 그대로 둔 채, `Input.Action.*` tag와 일치하는 granted Ability Spec을 찾아 엔진 활성화를 요청할 수 있는 최소 프로젝트 ASC를 실제 Character에 설치한다.

이 단계는 화면에 공격을 재생하지 않는다. 아직 Ability가 grant되지 않았고 PlayerController도 호출하지 않기 때문이다. 대신 다음을 독립적으로 검증한다.

- 새 UCLASS가 UHT와 C++ compile을 통과한다.
- 기존 `AKhazanCharacter`의 ASC default subobject 실제 클래스가 `UKhazanAbilitySystemComponent`로 바뀐다.
- `IAbilitySystemInterface` 반환형과 기존 LocomotionComponent의 ASC 관측은 그대로 동작한다.
- M2.2 locomotion에 회귀가 없다.

CombatComponent를 먼저 만들지 않는 이유도 명확하다. 지금은 다른 Actor와 교환할 hit/damage 입력이 없으므로 CombatComponent를 만들면 ASC 포인터를 저장하는 빈 wrapper가 된다. 첫 실제 공통 hit가 생기는 P3.1에서 한 개의 CombatComponent를 도입한다.

## 수정 파일과 책임

### 새로 만드는 파일

```text
Source/Khazan/Ability/KhazanAbilitySystemComponent.h
Source/Khazan/Ability/KhazanAbilitySystemComponent.cpp
```

`Ability` 폴더는 ASC, GameplayAbility, AbilitySet처럼 GAS 실행과 직접 관련된 프로젝트 타입을 모은다. `Character/Component`에 두지 않는 이유는 이 ASC가 Player Character 하나의 부품이 아니라 향후 일반 적과 보스도 사용할 공통 GAS 확장이기 때문이다.

### 수정하는 파일

```text
Source/Khazan/Character/KhazanCharacter.cpp
```

Character는 Component들의 composition root다. 그래서 `AbilitySystemComponent`라는 기존 subobject의 **구체 생성 클래스**만 프로젝트 ASC로 바꾼다. ActorInfo 초기화, Definition 로드, Locomotion 초기화 순서는 바꾸지 않는다.

### 이 checkpoint에서 수정하지 않는 파일

```text
Khazan.uproject
Source/Khazan/Khazan.Build.cs
Source/Khazan/Character/KhazanCharacter.h
Source/Khazan/Player/KhazanPlayerController.*
Source/Khazan/KhazanGameplayTags.*
Content의 Blueprint/DataAsset/Montage
```

plugin과 module dependency는 이미 준비돼 있다. 기존 Character header의 멤버 타입을 `TObjectPtr<UAbilitySystemComponent>`로 유지하면 엔진 interface와 기존 소비자는 프로젝트 subclass를 몰라도 된다. typed accessor는 실제 호출자가 생기는 후속 checkpoint에서 필요 여부를 판단한다.

## 1. 폴더 만들기

Rider의 Project 창에서 `Source/Khazan`을 우클릭하고 `New | Directory`로 `Ability` 폴더를 만든다. Windows Explorer에서 만들어도 된다.

Unreal Editor의 `Tools | New C++ Class`를 사용할 필요는 없다. 이 단계는 두 파일을 정확한 모듈 경로에 직접 만들며, UBT/UHT가 다음 cold build에서 새 UCLASS를 찾는다.

## 2. `KhazanAbilitySystemComponent.h` 작성

파일 경로:

```text
Source/Khazan/Ability/KhazanAbilitySystemComponent.h
```

전체 내용:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "AbilitySystemComponent.h"
#include "GameplayTagContainer.h"
#include "KhazanAbilitySystemComponent.generated.h"

UCLASS()
class KHAZAN_API UKhazanAbilitySystemComponent : public UAbilitySystemComponent
{
	GENERATED_BODY()

public:
	bool TryActivateAbilitiesByInputTag(const FGameplayTag& InputTag);
};
```

### Header 각 줄의 의미

`#pragma once`

- 이 header가 한 translation unit 안에서 중복 포함되는 것을 막는다.

`#include "CoreMinimal.h"`

- 프로젝트의 기본 Unreal 타입과 macro 환경을 가져온다.

`#include "AbilitySystemComponent.h"`

- 상속 대상 `UAbilitySystemComponent`의 완전한 정의가 필요하다. 포인터만 선언하는 경우와 달리 상속에는 forward declaration만 사용할 수 없다.

`#include "GameplayTagContainer.h"`

- public 함수 인자에 쓰는 `FGameplayTag` 계약을 이 header 자체가 명시한다. 다른 header의 우연한 간접 include에 기대지 않는다.

`#include "KhazanAbilitySystemComponent.generated.h"`

- UHT가 만드는 reflection 코드를 연결한다. Unreal 규칙상 이 파일은 일반 include 중 마지막이어야 한다.

`UCLASS()`

- 엔진 reflection과 default subobject 생성을 지원하는 UObject class로 등록한다. Blueprint에서 직접 생성하거나 설정할 현재 소비가 없으므로 `BlueprintType`, `Blueprintable` 같은 지정자는 추가하지 않는다.

`class KHAZAN_API UKhazanAbilitySystemComponent : public UAbilitySystemComponent`

- `U`는 UObject class prefix다.
- `KhazanAbilitySystemComponent`는 프로젝트 확장이라는 의미를 분명히 한다.
- `KHAZAN_API`는 Khazan module 밖에서 이 class symbol을 사용할 때 필요한 export/import macro다.
- 엔진 ASC를 포함(composition)하는 wrapper가 아니라 직접 상속하므로 기존 GAS API, ActorInfo, spec/effect 수명을 그대로 사용한다.

`GENERATED_BODY()`

- UHT가 constructor/helper/reflection 선언을 삽입할 자리다.

`public:`

- 후속 PlayerController 또는 공통 입력 adapter가 이 기능을 호출해야 하므로 public이다.

`bool TryActivateAbilitiesByInputTag(const FGameplayTag& InputTag);`

- `Try`: 활성화가 보장되지 않음을 나타낸다. GAS는 required/block tag, cost, 이미 활성 상태 같은 조건으로 요청을 거절할 수 있다.
- `ActivateAbilities`: 이 함수는 입력을 저장하거나 전투 상태를 직접 바꾸지 않고 엔진 Ability 활성화를 요청한다.
- `ByInputTag`: Ability Asset Tag가 아니라 grant된 Spec에 붙인 입력 식별자를 검색한다.
- 반환 `bool`: 일치하는 spec 중 적어도 하나에 대해 엔진 `TryActivateAbility`가 성공을 보고했으면 `true`다. Epic API 설명대로 최종 비동기 성공 전체를 보증하는 값은 아니며, 상세 실패는 GAS failure 관측으로 확인한다.
- `const FGameplayTag&`: tag를 복사하지 않고 읽기 전용 참조로 받는다. 함수 호출 뒤 이 참조를 저장하지 않으므로 caller의 tag 수명에 의존하지 않는다.
- `UFUNCTION`이 없는 이유: 현재 호출자는 C++이고 Blueprint 노출 소비가 없다. 필요할 때만 reflection 표면을 늘린다.

constructor, Tick, 배열, map, delegate, request ID를 선언하지 않는다. 현재 함수에 필요한 지속 상태가 하나도 없기 때문이다.

## 3. `KhazanAbilitySystemComponent.cpp` 작성

파일 경로:

```text
Source/Khazan/Ability/KhazanAbilitySystemComponent.cpp
```

전체 내용:

```cpp
#include "Ability/KhazanAbilitySystemComponent.h"

#include "GameplayAbilitySpec.h"

bool UKhazanAbilitySystemComponent::TryActivateAbilitiesByInputTag(const FGameplayTag& InputTag)
{
	if (!InputTag.IsValid())
	{
		return false;
	}

	FScopedAbilityListLock AbilityListLock(*this);
	bool bActivatedAnyAbility = false;

	for (const FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
	{
		if (!AbilitySpec.Ability ||
			!AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
		{
			continue;
		}

		if (TryActivateAbility(AbilitySpec.Handle))
		{
			bActivatedAnyAbility = true;
		}
	}

	return bActivatedAnyAbility;
}
```

### Source 각 줄과 분기의 의미

`#include "Ability/KhazanAbilitySystemComponent.h"`

- 구현 파일은 자기 header를 가장 먼저 포함해 header가 독립적으로 compile 가능한지 확인한다.
- `Khazan.Build.cs`의 기존 `PublicIncludePaths`에 `Khazan`이 있으므로 module root 아래 `Ability/...` 경로로 포함할 수 있다.

`#include "GameplayAbilitySpec.h"`

- `FGameplayAbilitySpec`, `FGameplayAbilitySpecHandle`, `FScopedAbilityListLock`의 완전한 정의를 사용한다.
- 특히 `FScopedAbilityListLock`을 명시적으로 쓰므로 간접 include에 맡기지 않는다.

함수 signature는 header 선언과 정확히 같아야 한다. class scope를 붙인 `UKhazanAbilitySystemComponent::`가 이 구현의 owner를 지정한다.

`if (!InputTag.IsValid())`

- 비어 있는 `FGameplayTag`는 어떤 입력도 의미하지 않는다.
- 잘못된 입력을 전체 ability 목록 검색으로 넘기지 않고 즉시 실패한다.
- 여기서 log를 남기지 않는 이유는 입력이 없는 호출이 반드시 crash 수준의 오류는 아니고, 반복 입력 경로에서 불필요한 log spam을 만들 수 있기 때문이다. 실제 설정 검증은 AbilitySet 단계에 둔다.

`FScopedAbilityListLock AbilityListLock(*this);`

- `GetActivatableAbilities()`가 반환하는 목록을 순회하는 동안 ability 제거로 배열 원소가 무효화되지 않도록 ASC의 공식 scope lock을 잡는다.
- `*this`는 현재 `UKhazanAbilitySystemComponent` 객체이며 base `UAbilitySystemComponent&`로 전달된다.
- 지역 객체이므로 함수 scope를 벗어나면 destructor가 자동으로 lock을 해제한다. 별도 handle map이나 수동 cleanup이 없다.
- 이 lock은 thread 동기화 mutex가 아니다. GAS ability list의 순회 중 변경을 지연시키는 수명 guard다. 이 함수는 Player 입력이 들어오는 Game Thread에서 호출한다.

`bool bActivatedAnyAbility = false;`

- 반환할 지역 관측값이다.
- UObject member가 아니며 호출이 끝나면 사라진다.
- `false` 초기값은 아직 어떤 spec도 활성화 성공을 보고하지 않았다는 뜻이다.

`for (const FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())`

- ASC에 grant되어 활성화 가능한 spec들을 한 번 순회한다.
- `const &`이므로 배열 원소를 복사하지 않고 읽으며 이 함수가 spec 설정을 직접 수정하지 않음을 표현한다.
- 별도 `TMap<InputTag, Handle>`를 유지하지 않는다. P1의 작은 ability 수에서는 선형 검색이 충분하고, map을 추가하면 grant/remove와 동기화해야 할 상태가 하나 더 생긴다. 실제 profiling에서 필요할 때만 index를 검토한다.

`if (!AbilitySpec.Ability || ... )`

- 첫 조건은 유효한 Ability class/CDO가 없는 spec을 제외한다.
- `||`는 왼쪽이 참이면 오른쪽을 평가하지 않는 short-circuit 연산이다. 따라서 Ability가 없을 때 뒤 조건을 불필요하게 검사하지 않는다.

`AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag)`

- 후속 AbilitySet이 **grant된 spec**에 기록할 입력 tag container를 읽는다.
- `HasTagExact`는 부모/자식 tag의 계층 매칭을 허용하지 않는다. 예를 들어 `Input.Action`이 `Input.Action.Attack`을 대신 매칭하지 않는다.
- 입력 binding은 정확한 버튼 계약이므로 exact match가 의도에 맞는다.
- 같은 Ability class를 서로 다른 CharacterDefinition에서 다른 입력 tag로 grant할 수 있고, Ability 자체의 분류 tag와 입력 배치를 섞지 않는다.

`continue;`

- 현재 spec은 대상이 아니므로 아래 활성화 호출을 건너뛰고 다음 spec을 검사한다.

`if (TryActivateAbility(AbilitySpec.Handle))`

- 새 실행 ID나 request 객체를 만들지 않고 엔진이 grant 시 만든 `FGameplayAbilitySpecHandle`을 그대로 사용한다.
- 엔진 ASC가 Ability의 활성 여부, tag requirement/block, cost, authority/prediction 설정 등을 검사한다.
- 기본 두 번째 인자 `bAllowRemoteActivation`은 엔진 기본값 `true`를 사용한다. 현재 프로젝트는 싱글플레이지만 불필요하게 공식 동작을 제한하지 않는다.

`bActivatedAnyAbility = true;`

- 여러 spec이 같은 입력 tag를 가진 경우 앞의 성공 뒤에도 나머지를 계속 검사한다. `||` short-circuit로 뒤의 활성화 요청을 생략하지 않기 위해 명시적 분기를 쓴다.
- P1 AbilitySet은 Attack tag에 정확히 한 spec만 grant한다. 따라서 P1 검증에서는 한 번만 활성화되어야 한다.
- 미래에 같은 입력의 문맥별 Ability가 실제 필요하면 GAS tag requirement가 어느 spec을 허용할지 결정할 수 있다. 지금 이를 위한 별도 우선순위 Manager는 만들지 않는다.

`return bActivatedAnyAbility;`

- 일치 spec 없음 또는 모든 활성화 거절이면 `false`, 하나 이상 요청 성공이면 `true`다.
- 이 함수는 montage 완료나 공격 적중 같은 최종 결과를 반환하지 않는다. 그것들은 Ability의 비동기 수명 뒤에 발생한다.

## 4. `KhazanCharacter.cpp`의 include 교체

현재 상단에는 다음 include가 있다.

```cpp
#include "AbilitySystemComponent.h"
```

이 한 줄을 다음으로 교체한다.

```cpp
#include "Ability/KhazanAbilitySystemComponent.h"
```

이제 이 `.cpp`는 생성할 concrete class의 완전한 정의를 안다. 새 header가 base header도 포함하므로 기존 `AbilitySystemComponent.h`를 별도로 중복 include할 필요가 없다.

`KhazanCharacter.h`는 계속 `class UAbilitySystemComponent;`만 forward declare하고 base pointer를 보관한다. 이 단계에서 header 의존성과 public API를 넓히지 않는다.

## 5. Character constructor의 concrete class 한 줄 교체

현재 줄:

```cpp
AbilitySystemComponent = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("AbilitySystemComponent"));
```

교체할 줄:

```cpp
AbilitySystemComponent = CreateDefaultSubobject<UKhazanAbilitySystemComponent>(TEXT("AbilitySystemComponent"));
```

### 이 한 줄에서 바뀌는 것

- `CreateDefaultSubobject`의 template 인자만 엔진 base class에서 프로젝트 subclass로 바뀐다.
- subobject 이름 문자열 `AbilitySystemComponent`는 그대로 유지한다. 기존 native/Blueprint component 정체성을 불필요하게 바꾸지 않는다.
- 왼쪽 멤버 타입은 base pointer이므로 derived object를 안전하게 보관한다. 이것이 일반적인 다형성이다.
- `GetAbilitySystemComponent()`는 계속 `UAbilitySystemComponent*`를 반환해 `IAbilitySystemInterface` 계약을 지킨다.
- 기존 `InitAbilityActorInfo`, `RefreshAbilityActorInfo`, `DestroyActiveState` 호출은 상속된 엔진 함수를 그대로 실행한다.
- ASC를 두 개 만들지 않는다. 기존 한 개의 concrete class만 교체한다.

### 이 한 줄에서 바뀌지 않는 것

- OwnerActor와 AvatarActor는 계속 현재 Character 자신이다.
- ASC가 PlayerController나 PlayerState로 이동하지 않는다.
- replication/prediction 설정을 새로 켜지 않는다.
- Ability를 grant하지 않는다.
- Attack이나 Jump 입력을 아직 연결하지 않는다.
- locomotion tag delegate와 movement constraint 수명을 바꾸지 않는다.

## 6. 저장 전 직접 대조

다음 여섯 항목을 눈으로 확인한다.

1. 새 파일명이 class명과 정확히 대응한다: `KhazanAbilitySystemComponent.h/.cpp`.
2. `generated.h` include가 header의 마지막 include다.
3. class에는 `KHAZAN_API`와 `GENERATED_BODY()`가 있다.
4. header와 cpp의 함수명, 반환형, `const FGameplayTag&`가 한 글자도 다르지 않다.
5. Character constructor에는 `AbilitySystemComponent` subobject 생성이 여전히 정확히 한 줄만 있다.
6. `KhazanCharacter.cpp`에 old/new ASC header를 둘 다 중복 include하지 않았다.

## 7. cold build

이 변경은 새 UCLASS를 추가하고 기존 default subobject의 concrete class를 바꾼다. Unreal Editor와 Live Coding Console을 완전히 닫고 빌드한다. Live Coding patch로 넘기지 않는다.

Rider에서는 solution configuration을 `Development Editor | Win64`, target을 `KhazanEditor`로 두고 Build한다.

PowerShell에서 직접 빌드하려면 프로젝트 root에서 다음 명령을 사용할 수 있다.

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
  KhazanEditor Win64 Development `
  "C:\Users\user\Desktop\GitProject\Khazan\Khazan\Khazan.uproject" `
  -WaitMutex -NoHotReloadFromIDE
```

기대 결과:

- UHT가 `KhazanAbilitySystemComponent.generated.h`를 생성한다.
- `KhazanAbilitySystemComponent.cpp`와 `KhazanCharacter.cpp`가 compile된다.
- 마지막에 `Result: Succeeded` 또는 Rider의 build success가 나온다.

이 단계에는 gameplay 튜닝 숫자가 없다. 따라서 원작값/계산값/임시 튜닝값 분류 대상도 없다.

## 8. Editor와 PIE 검증

cold build 성공 뒤 Editor를 다시 연다.

1. `BP_KhazanPlayer`를 연다.
2. inherited `AbilitySystemComponent`가 사라지거나 중복 생성되지 않았는지 Components panel에서 확인한다.
3. Details 또는 debugger에서 실제 component class가 `KhazanAbilitySystemComponent`인지 확인한다.
4. DevMap PIE를 시작한다.
5. 기존 Walk/Run/Sprint/Stop과 이동 입력 차단 probe가 이전 M2.2 결과와 같은지 확인한다.
6. Output Log에 duplicate default subobject, invalid ASC, locomotion ASC requirement 오류가 없는지 확인한다.

Attack은 여전히 아무 동작도 하지 않는 것이 정상이다. 새 입력 함수도 아직 호출되지 않는다. 화면 동작이 없다는 사실을 P1 완료로 오해하지 않는다.

더 직접 확인하려면 PIE에서 Character가 생성된 뒤 debugger로 `AKhazanCharacter::GetAbilitySystemComponent()` 반환 객체의 runtime class를 본다. 기대 class는 `UKhazanAbilitySystemComponent`다. 이 검증을 위해 임시 Tick, bool, log를 production source에 추가하지 않는다.

## 9. 자주 생기는 실패와 원인

### `Cannot open include file: KhazanAbilitySystemComponent.generated.h`

- header 파일명과 `generated.h` 이름이 다른지 확인한다.
- `generated.h` 뒤에 다른 include가 있는지 확인한다.
- Editor가 열린 채 Live Coding으로만 compile하지 않았는지 확인하고 cold build한다.

### `use of undefined type FScopedAbilityListLock` 또는 spec 관련 incomplete type 오류

- cpp에 `#include "GameplayAbilitySpec.h"`가 있는지 확인한다.

### `UKhazanAbilitySystemComponent`를 찾지 못함

- `KhazanCharacter.cpp`가 `#include "Ability/KhazanAbilitySystemComponent.h"`를 포함하는지 확인한다.
- 파일이 `Source/Khazan/Ability` 아래에 있는지 확인한다.
- class spelling과 `KHAZAN_API`를 확인한다.

### Editor에서 기존 Blueprint component가 이상하거나 class가 갱신되지 않음

- Editor와 Live Coding Console을 닫았는지 확인한다.
- cold build 성공 후 Editor를 새로 실행했는지 먼저 확인한다.
- subobject 문자열을 기존 `AbilitySystemComponent`와 다르게 바꾸지 않았는지 확인한다.
- Blueprint를 임의로 재생성하거나 asset을 삭제하기 전에 build log와 component class를 먼저 대조한다.

### build는 성공했지만 Attack이 재생되지 않음

- 이 checkpoint의 정상 결과다. AbilitySet grant와 PlayerController 연결은 아직 없다.

## 10. 이 checkpoint 완료 보고에 필요한 증거

다음 세 가지면 충분하다.

1. 새 header/cpp와 Character constructor 교체 내용
2. cold build 마지막 성공 또는 첫 compile error 전문
3. Editor 재실행 후 PIE에서 기존 M2.2 이동 회귀 여부

어시스턴트는 그 실제 내용을 대조한 뒤에만 P1.1을 적용·빌드 완료로 기록한다.

## 다음 checkpoint 예고 — 아직 구현하지 않음

P1.2에서는 다음 최소 데이터 계약만 만든다.

- Ability class
- 기존 `Input.Action.*` 중 선택적 Input Tag
- 이 두 값을 Character variant에 따라 한 번 grant하는 `UKhazanAbilitySet`

Effect, AttributeSet, input buffer, combo graph, grant/remove 원장 전체는 넣지 않는다. P1.2 설명은 P1.1의 실제 build와 기존 Blueprint subobject 보존을 확인한 다음 현재 Source 기준으로 작성한다.


<a id="p1-1-applied-p1-2-direct-grants-20260915"></a>
## 2026-09-15 — P1.1 적용 확인과 P1.2 직접 초기 Ability grant

### P1.1 실제 대조 결과

- 사용자가 작성한 `KhazanAbilitySystemComponent.h/.cpp`는 위 P1.1 코드와 일치한다.
- `AKhazanCharacter`는 기존 `AbilitySystemComponent` 이름의 subobject 한 개를 `UKhazanAbilitySystemComponent`로 생성한다.
- 멤버 타입, `GetAbilitySystemComponent()`, ActorInfo 초기화, Possess/UnPossess refresh, EndPlay cleanup은 기존 base ASC 계약을 유지한다.
- 최신 UBT log는 UE 5.8.2 UHT가 새 class를 처리하고 `KhazanAbilitySystemComponent.cpp`, `KhazanCharacter.cpp`, module, DLL, metadata를 모두 성공시켰다. 최종 결과는 `Result: Succeeded`다.
- 최신 gameplay log는 이 cold build 이전 시각이므로 새 Editor에서 runtime component class와 M2.2 PIE 회귀를 확인한 기록은 아직 없다. P1.7 전에는 반드시 누적 확인한다.

### 사용자 정정의 전역 반영

`CombatComponent`는 예시였으며 특정 Component를 중심으로 구조를 다시 짜라는 뜻이 아니었다. 모든 Component와 새 타입에 같은 질문을 적용한다.

> 붙였을 때 호환 owner가 얻는 완결된 능력이 있는가? 그 능력에 필요한 독립 상태와 cleanup을 실제로 소유하는가?

P1.2에는 새 Component가 필요하지 않다. 또한 현재 초기 Ability 묶음의 작성자는 CharacterDefinition 하나, grant owner는 Character 하나이므로 별도 `UKhazanAbilitySet`도 아직 추출하지 않는다. Ability 목록을 기존 CharacterDefinition에 직접 두고, 같은 묶음의 두 번째 부여 source나 독립 회수가 생길 때 AbilitySet으로 추출한다.

## P1.2 목표

이번 checkpoint의 목표는 다음 한 문장이다.

> CharacterDefinition이 `AbilityClass + 선택적 InputTag`로 구성된 초기 Ability 목록을 읽기 전용으로 제공하고, Character가 ASC ActorInfo와 필수 이동 설정을 준비한 뒤 authority에서 그 목록을 정확히 한 번 grant한다.

이번 단계는 실제 BasicAttack class를 만들지 않는다. 기존 Definition asset의 새 배열은 빈 상태로 둔다. 따라서 화면 동작이 바뀌지 않는 것이 정상이다.

## 파일 범위

수정하는 파일은 세 개뿐이다.

```text
Source/Khazan/Data/KhazanCharacterDefinitionData.h
Source/Khazan/Data/KhazanCharacterDefinitionData.cpp
Source/Khazan/Character/KhazanCharacter.cpp
```

새 C++ 파일, 새 Component, 새 DataAsset 인스턴스, 새 GameplayTag는 만들지 않는다. `KhazanCharacter.h`, `Khazan.Build.cs`, `Khazan.uproject`, PlayerController도 수정하지 않는다.

## 1. CharacterDefinition header 전체 작성 결과

대상:

```text
Source/Khazan/Data/KhazanCharacterDefinitionData.h
```

현재 내용을 다음 최종 형태로 만든다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Character/Locomotion/KhazanLocomotionType.h"
#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "KhazanCharacterDefinitionData.generated.h"

class UGameplayAbility;

/** CharacterDefinition이 초기화 때 한 번 부여할 Ability 한 건이다. */
USTRUCT(BlueprintType)
struct KHAZAN_API FKhazanInitialAbilityGrant
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ability")
	TSubclassOf<UGameplayAbility> AbilityClass = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ability",
		meta = (Categories = "Input.Action"))
	FGameplayTag InputTag = FGameplayTag::EmptyTag;
};

UCLASS(BlueprintType)
class KHAZAN_API UKhazanCharacterDefinitionData : public UDataAsset
{
	GENERATED_BODY()

public:
	const FKhazanLocomotionConfig& GetLocomotionConfig() const;
	const TArray<FKhazanInitialAbilityGrant>& GetInitialAbilityGrants() const;

private:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Locomotion",
		meta = (AllowPrivateAccess = "true"))
	FKhazanLocomotionConfig LocomotionConfig;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Character|Abilities",
		meta = (AllowPrivateAccess = "true"))
	TArray<FKhazanInitialAbilityGrant> InitialAbilityGrants;
};
```

### include 설명

`CoreMinimal.h`

- `TArray`, `TSubclassOf`, UObject macro와 기본 타입을 제공한다.

`KhazanLocomotionType.h`

- 기존 `FKhazanLocomotionConfig`의 실제 정의를 제공한다. 기존 계약 그대로다.

`GameplayTagContainer.h`

- 새 struct가 값 멤버로 보관하는 `FGameplayTag`의 완전한 정의를 제공한다.
- 값 멤버는 포인터와 달라서 forward declaration만으로 둘 수 없다.

`Engine/DataAsset.h`

- 기존 `UDataAsset` base를 제공한다.

`KhazanCharacterDefinitionData.generated.h`

- 새 USTRUCT와 기존 UCLASS의 reflection 코드를 연결한다.
- 항상 일반 include 중 마지막에 둔다.

### `class UGameplayAbility;`

- `AbilityClass`는 Ability 객체를 값으로 포함하지 않고 `TSubclassOf`로 class reference만 보관한다.
- header에서 Ability의 함수나 크기를 사용하지 않으므로 forward declaration으로 충분하다.
- 무거운 `GameplayAbility.h`를 Definition header의 모든 소비자에게 전파하지 않는다.

### `FKhazanInitialAbilityGrant`

이 struct는 runtime 상태가 아니라 CharacterDefinition에 저장되는 **초기 부여 지시 한 건**이다.

`USTRUCT(BlueprintType)`

- DataAsset Details에서 배열 원소를 구조화해 편집하고 필요할 경우 Blueprint가 읽을 수 있게 한다.
- 별도 UObject나 Component 수명은 만들지 않는다.

`KHAZAN_API`

- 이 reflected struct가 module 경계에서도 올바르게 export되게 한다.

`TSubclassOf<UGameplayAbility> AbilityClass`

- 인스턴스가 아니라 어떤 GameplayAbility class를 grant할지 가리킨다.
- `TSubclassOf`가 선택 가능한 class를 `UGameplayAbility` 계열로 제한한다.
- 초기값 `nullptr`은 아직 지정되지 않았음을 뜻한다.
- 이름을 단순히 `Ability`라고 하지 않고 `AbilityClass`라고 해 asset instance나 실행 instance와 구분한다.

`FGameplayTag InputTag`

- 해당 Ability를 입력으로 활성화할 때 spec에 붙일 선택적 식별자다.
- `FGameplayTag::EmptyTag`면 Ability는 grant되지만 입력 검색 대상은 아니다. 이후 이벤트 기반 HitReact나 passive Ability도 같은 최소 형식을 사용할 수 있다.
- `meta = (Categories = "Input.Action")`는 Editor picker를 기존 입력 namespace로 제한한다. 새 tag namespace를 만들지 않는다.
- 이 tag는 Ability가 실행 중 소유하는 `State.*` tag나 Ability 분류 tag가 아니다.

두 필드는 함께 부여 시점에 한 번 소비되므로 작은 struct 하나로 묶는 것이 타당하다. 별도 `InputBinding`, `AbilityDefinition`, `GrantOptions` 구조로 더 나누지 않는다.

### `GetInitialAbilityGrants()`

```cpp
const TArray<FKhazanInitialAbilityGrant>& GetInitialAbilityGrants() const;
```

- 첫 `const`: 호출자가 반환 배열과 원소를 수정할 수 없다.
- `TArray<...>&`: 전체 배열을 복사하지 않고 Definition의 기존 저장소를 읽는다.
- 함수 뒤 `const`: getter가 Definition 객체를 변경하지 않는다.
- Character는 초기화 중 이 참조를 즉시 순회하고 저장하지 않는다. Definition이 AssetManager preload 수명 동안 살아 있다는 기존 계약을 따른다.

### `InitialAbilityGrants`

- 작성자: `DA_CharacterDefinition_*` asset의 디자이너 설정.
- 소비자: authority `AKhazanCharacter::PostInitializeComponents()` 한 곳.
- 갱신 시점: Editor에서 정적 asset을 편집할 때.
- runtime reset: 하지 않는다. Character의 ASC에는 grant된 Spec이 별도로 저장된다.
- worker thread: 읽지 않는다. Game Thread 초기화에서만 소비한다.

## 2. CharacterDefinition cpp getter 추가

대상:

```text
Source/Khazan/Data/KhazanCharacterDefinitionData.cpp
```

기존 getter 아래에 다음 함수를 추가한다.

```cpp
const TArray<FKhazanInitialAbilityGrant>&
UKhazanCharacterDefinitionData::GetInitialAbilityGrants() const
{
	return InitialAbilityGrants;
}
```

반환형을 두 줄로 나눈 것은 긴 signature 가독성을 위한 서식일 뿐 동작 차이는 없다. 기존 locomotion getter는 변경하지 않는다.

함수가 반환한 참조는 Definition의 배열을 가리킨다. Character가 그 참조를 멤버로 보관하지 않고 즉시 순회하므로 별도 lifetime wrapper가 필요하지 않다.

## 3. Character cpp에 Spec 정의 include 추가

대상:

```text
Source/Khazan/Character/KhazanCharacter.cpp
```

상단의 프로젝트 ASC include 근처에 다음을 추가한다.

```cpp
#include "GameplayAbilitySpec.h"
```

`FGameplayAbilitySpec` 지역 객체를 실제로 생성하고 `GetDynamicSpecSourceTags()`를 호출하므로 완전한 정의가 필요하다. `KhazanAbilitySystemComponent.h`의 간접 include에 기대지 않는다.

## 4. Locomotion 초기화 실패를 fail closed로 마무리

현재 코드는 다음과 같다.

```cpp
if (!LocomotionComponent->InitializeMovementConfig(CharacterDefinition->GetLocomotionConfig()))
{
	UE_LOG(LogDefault, Error, TEXT("%s failed to initialize locomotion from %s."),
		*GetNameSafe(this), *GetNameSafe(CharacterDefinition));
}
```

log 뒤에 `return;`을 추가한다.

```cpp
if (!LocomotionComponent->InitializeMovementConfig(CharacterDefinition->GetLocomotionConfig()))
{
	UE_LOG(LogDefault, Error, TEXT("%s failed to initialize locomotion from %s."),
		*GetNameSafe(this), *GetNameSafe(CharacterDefinition));
	return;
}
```

지금까지는 이 블록 뒤에 코드가 없어 `return` 유무가 관측 동작을 바꾸지 않았다. 이제 뒤에 Ability grant가 생기므로 의미가 생긴다. 필수 Character Definition의 이동 설정이 유효하지 않은 Character에게 공격 Ability만 부분 부여하지 않고 초기화를 중단한다.

별도 `State.Ready.Gameplay` tag나 초기화 상태 머신을 만들지 않는다. 성공한 lifecycle 순서 자체가 준비 계약이다.

## 5. 같은 `PostInitializeComponents()` 끝에 grant loop 추가

방금 수정한 locomotion 초기화 `if` 블록 바로 뒤에 다음 코드를 추가한다.

```cpp
	if (HasAuthority())
	{
		for (const FKhazanInitialAbilityGrant& InitialAbilityGrant :
			CharacterDefinition->GetInitialAbilityGrants())
		{
			if (!InitialAbilityGrant.AbilityClass)
			{
				UE_LOG(LogDefault, Error,
					TEXT("%s has an InitialAbilityGrant with no AbilityClass in %s (InputTag: %s)."),
					*GetNameSafe(this),
					*GetNameSafe(CharacterDefinition),
					*InitialAbilityGrant.InputTag.ToString());
				continue;
			}

			FGameplayAbilitySpec AbilitySpec(InitialAbilityGrant.AbilityClass);

			if (InitialAbilityGrant.InputTag.IsValid())
			{
				AbilitySpec.GetDynamicSpecSourceTags().AddTag(
					InitialAbilityGrant.InputTag);
			}

			AbilitySystemComponent->GiveAbility(AbilitySpec);
		}
	}
```

### grant loop 각 줄의 의미

`if (HasAuthority())`

- GAS `GiveAbility`는 authority에서만 유효하다.
- Standalone PIE의 Character는 authority이므로 이번 환경에서는 실행된다.
- client가 같은 Definition을 읽었다고 각각 Spec을 만들게 하지 않는다.
- 현재 싱글플레이 범위를 넘어선 prediction/replication 초기화 계층은 추가하지 않는다.

`for (const FKhazanInitialAbilityGrant& InitialAbilityGrant : ...)`

- Definition의 초기 grant 배열을 순서대로 읽는다.
- `const &`로 복사를 피하고 정적 Definition 데이터를 수정하지 않는다.
- 이 참조는 loop iteration 동안만 존재한다.

`if (!InitialAbilityGrant.AbilityClass)`

- Editor에서 배열 원소를 만들고 class를 비워 둔 설정 오류를 검사한다.
- null class로 `FGameplayAbilitySpec`을 만들지 않는다.

`UE_LOG(...)`

- actor, Definition asset, InputTag를 함께 기록해 어느 설정이 비었는지 찾을 수 있게 한다.
- 새 failure enum, delegate, 결과 struct를 만들지 않는다.

`continue`

- 잘못된 원소 하나만 건너뛰고 나머지 유효한 초기 Ability는 grant한다.
- 기존 Ability를 취소하거나 다른 Component 상태를 정리하지 않는다.

`FGameplayAbilitySpec AbilitySpec(InitialAbilityGrant.AbilityClass);`

- stack에 잠시 존재하는 엔진 Spec 지시 객체를 만든다.
- UE 5.8 이 constructor의 기본 Ability Level은 `1`, InputID는 `INDEX_NONE`, SourceObject는 `nullptr`이다.
- Level 1은 원작 전투 수치라고 주장하는 값이 아니라 엔진 constructor의 기술적 기본값이다. P1에는 level scaling 소비가 없으므로 별도 데이터 필드를 만들지 않는다.
- 실제 level 차이가 gameplay에 쓰이는 단계에서 원작값/계산값/명시적 임시값을 구분해 `AbilityLevel` 필드 추가를 다시 심사한다.

`if (InitialAbilityGrant.InputTag.IsValid())`

- 입력 tag는 선택적이다. 비어 있으면 그대로 grant하고 입력 검색 tag만 추가하지 않는다.

`GetDynamicSpecSourceTags().AddTag(...)`

- Ability class asset 자체가 아니라 이번 grant로 생기는 Spec에 입력 tag를 기록한다.
- 같은 Ability class라도 서로 다른 Definition에서 다른 입력을 배정할 여지가 있다.
- P1.1의 `TryActivateAbilitiesByInputTag()`가 바로 이 container를 검색한다.

`AbilitySystemComponent->GiveAbility(AbilitySpec);`

- ASC가 Spec을 자기 `ActivatableAbilities` container에 복사·등록한다.
- 반환 `FGameplayAbilitySpecHandle`은 의도적으로 저장하지 않는다.
- 현재 부여 source는 Character 생성 한 번뿐이고 Ability는 ASC와 Character가 끝날 때 함께 사라진다. 실행 중 Definition 교체나 부분 회수 기능이 없다.
- 장비나 다른 source가 Ability 묶음을 부여하고 자기 것만 회수해야 할 때 그 source가 반환 handle을 보관한다.

### 별도 함수나 Component로 추출하지 않는 이유

현재 grant loop는 `PostInitializeComponents()`에서 정확히 한 번 실행되고 다른 caller가 없다. Character는 ASC와 Definition을 조립하는 composition root이므로 이 초기화는 해당 lifecycle 함수의 응집된 책임이다.

지금 `AbilityGrantComponent`, `AbilityManager`, `GrantInitialAbilities()` wrapper를 만들면 호출 한 번을 다른 이름으로 전달하는 계층만 늘어난다. loop가 다른 lifecycle에서도 재사용되거나 독립 해제 수명을 얻을 때 함수를 추출한다.

## 6. 완성된 초기화 순서

P1.2 적용 후 Game Thread 순서는 다음과 같다.

```text
AKhazanCharacter::PostInitializeComponents
  1. Super 호출
  2. GameWorld 검사
  3. ASC InitAbilityActorInfo(this, this)
  4. CharacterDefinition을 기존 catalog tag로 조회
  5. Definition 유효성 검사
  6. LocomotionConfig 검증·복사·CMC 적용
  7. authority 검사
  8. InitialAbilityGrants를 Spec으로 변환
  9. 유효한 InputTag를 Dynamic Spec Source Tag에 추가
 10. ASC GiveAbility
```

PossessedBy는 ActorInfo 참조만 refresh한다. Ability를 다시 grant하지 않는다. UnPossess도 Spec을 지우지 않는다. EndPlay은 기존 `DestroyActiveState()`로 실행 중 Ability를 끝내고 ASC subobject가 Actor와 함께 파괴되면서 Spec container도 끝난다.

## 7. 저장 전 대조

1. `generated.h`는 Definition header의 마지막 include다.
2. `UGameplayAbility` forward declaration은 USTRUCT보다 위에 있다.
3. `AbilityClass`는 `TSubclassOf<UGameplayAbility>`이며 Ability instance pointer가 아니다.
4. `InputTag` metadata namespace는 정확히 `Input.Action`이다.
5. getter 선언과 정의의 `const TArray<FKhazanInitialAbilityGrant>&`가 일치한다.
6. Character cpp에는 `GameplayAbilitySpec.h`가 있다.
7. grant loop는 ActorInfo, Definition, Locomotion 성공 뒤에 있다.
8. `GiveAbility`는 `HasAuthority()` 안에 있다.
9. Spec handle 배열, 초기화 bool, 새 Component를 추가하지 않았다.
10. 기존 ASC subobject를 다시 만들거나 교체하지 않았다.

## 8. cold build

새 reflected USTRUCT와 UPROPERTY가 추가되므로 Editor와 Live Coding Console을 닫고 전체 build한다.

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
  KhazanEditor Win64 Development `
  '-Project=C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' `
  -WaitMutex -NoHotReloadFromIDE
```

기대 결과:

- UHT가 `FKhazanInitialAbilityGrant`와 `InitialAbilityGrants` property를 처리한다.
- Definition cpp와 Character cpp가 compile된다.
- module/DLL link와 metadata가 성공한다.
- 최종 `Result: Succeeded`다.

## 9. Editor 검증

build 성공 후 Editor를 새로 연다.

1. `/Game/Data/Character/DA_CharacterDefinition_Khazan`을 연다.
2. 기존 `Character | Locomotion` 값이 P1.2 전과 그대로인지 확인한다.
3. `Character | Abilities`에 `Initial Ability Grants` 배열이 보이는지 확인한다.
4. 이번 checkpoint에서는 배열 크기를 `0`으로 유지한다. null 원소나 임시 Ability asset을 만들지 않는다.
5. asset을 열었다는 이유로 기존 locomotion 값을 다시 입력하거나 바꾸지 않는다.
6. `BP_KhazanPlayer`의 `CharacterDefinitionAssetName`이 기존 `AssetData.CharacterDefinition.Khazan`인지 확인한다.

## 10. PIE 검증

1. DevMap PIE를 시작한다.
2. Player의 CharacterDefinition load/Locomotion 초기화 오류가 없는지 본다.
3. `Initial Ability Grants`가 비어 있으므로 Ability grant 관련 오류가 없어야 한다.
4. Walk/Run/Sprint/Stop이 이전과 동일해야 한다.
5. Attack은 계속 아무 동작이 없어야 한다.
6. PIE 종료 시 crash나 ASC cleanup 오류가 없어야 한다.

이 checkpoint에서 화면 효과가 없는 것은 미구현이 아니라 의도한 데이터·수명 기반 검증이다.

## 11. 실패 진단

### UHT가 `UGameplayAbility`를 인식하지 못함

- `class UGameplayAbility;`가 USTRUCT 위에 있는지 확인한다.
- `AbilityClass` spelling과 `TSubclassOf<UGameplayAbility>`를 대조한다.
- Editor를 닫고 cold build했는지 확인한다.

### `FGameplayAbilitySpec` incomplete type 오류

- `KhazanCharacter.cpp`에 `#include "GameplayAbilitySpec.h"`를 추가했는지 확인한다.

### `GetInitialAbilityGrants`를 찾지 못함

- Definition header 선언과 cpp class scope 이름을 대조한다.
- 반환형의 struct 이름이 `FKhazanInitialAbilityGrant`인지 확인한다.

### Definition asset에서 새 배열이 보이지 않음

- 새 DLL로 Editor를 재시작했는지 확인한다.
- UPROPERTY가 `InitialAbilityGrants` 위에 있는지 확인한다.
- DataAsset의 native class가 여전히 `UKhazanCharacterDefinitionData`인지 확인한다.

### 기존 locomotion 값이 사라져 보임

- asset을 저장하지 말고 닫는다.
- build/UHT 성공 여부와 Definition class가 바뀌지 않았는지 먼저 확인한다.
- 새 DataAsset을 다시 만들지 않는다. 기존 asset과 catalog 경로를 보존한다.

### null AbilityClass 오류 log가 출력됨

- `Initial Ability Grants`에 빈 원소가 들어 있다. 이번 단계에서는 배열 크기를 0으로 되돌린다.
- BasicAttack class는 P1.3에서 만든 뒤 유효한 원소로 추가한다.

## 12. P1.2 완료 증거

다음 내용을 대조하면 된다.

1. 수정한 Definition header/cpp
2. Character cpp의 include, locomotion 실패 `return`, authority grant loop
3. cold build 마지막 성공 또는 최초 error 전문
4. Definition asset에 빈 `Initial Ability Grants`가 보이고 기존 locomotion 값이 유지되는지
5. 새 PIE의 Definition/Locomotion/ASC 오류 및 이동 회귀 여부

실제 결과를 확인한 뒤에만 P1.2를 완료로 기록한다.

## 다음 checkpoint — 아직 구현하지 않음

P1.3에서는 빈 공통 Ability base를 만들지 않고 `UGameplayAbility`를 직접 상속하는 `UKhazanBasicAttackAbility` 하나를 만든다. 첫 버전은 활성화 횟수와 정상 `EndAbility` 수명만 관측하며 Montage, Locomotion constraint, hit, damage, Stamina는 넣지 않는다. 그 class가 생긴 뒤 Definition의 첫 원소에 `AbilityClass`와 기존 `Input.Action.Attack`을 지정한다.


<a id="p1-2-applied-p1-3-basic-attack-spec-20260915"></a>
# 2026-09-15 — P1.2 적용 대조 뒤 P1.3 BasicAttack class와 첫 granted Spec

## P1.2 실제 대조 결과

- `FKhazanInitialAbilityGrant`는 `AbilityClass + 선택적 InputTag`만 가진 정적 grant 지시로 구현됐다.
- `UKhazanCharacterDefinitionData`는 배열을 const reference로 제공한다.
- Character는 ActorInfo, Definition, Locomotion 초기화가 성공한 뒤 authority에서 `FGameplayAbilitySpec`을 만들고 `GiveAbility()`를 호출한다.
- 2026-09-15 19:36 UBT 기록에서 UE 5.8.2 UHT, Definition/Character compile, module/DLL link, metadata가 성공했고 `Result: Succeeded`다.
- 새 PIE log는 아직 없어 실제 asset property 노출, 빈 배열 무효과, M2.2 이동 회귀는 누적 runtime 검증 항목으로 남는다.
- `KhazanCharacter.cpp`의 `#include "ParticleHelper.h"`는 현재 파일에서 소비되지 않고 P1.2와 무관하다. P1.3 파일을 추가하기 전에 이 include 한 줄만 제거한다.

`TSubclassOf<class UGameplayAbility>`처럼 elaborated type specifier를 직접 쓴 현재 선언은 유효하며 build도 통과했다. 별도 forward declaration 형태로 바꾸는 것은 필수 수정이 아니다. `InitialAbilityGrants`의 `meta` 들여쓰기도 동작과 무관한 서식이므로 이번 기능 변경의 조건으로 삼지 않는다.

## P1.3의 정확한 목표

이번 checkpoint의 목표는 다음 한 문장이다.

> 실제 `UKhazanBasicAttackAbility` class 하나를 만들고, 기존 CharacterDefinition의 첫 grant 지시가 authority Character ASC 안의 BasicAttack `FGameplayAbilitySpec` 한 개로 등록되는 것을 확인한다.

이번 단계에서 Controller의 Attack 입력은 계속 비어 있다. 따라서 Ability의 `ActivateAbility()`가 아직 호출되지 않는 것이 정상이다. 검증을 위해 Tick, BeginPlay 자동 실행, 임시 키 binding, `GiveAbilityAndActivateOnce()`를 추가하지 않는다.

## 용어와 객체 수명

### `UGameplayAbility` class

- 공격이 실행될 때 무엇을 할지를 정의하는 타입이다.
- `UKhazanBasicAttackAbility::StaticClass()` 또는 `TSubclassOf<UGameplayAbility>`가 class reference다.
- class 자체는 특정 Character가 공격을 배웠다는 runtime 상태가 아니다.

### Ability CDO

- Unreal이 class마다 보관하는 Class Default Object다.
- `FGameplayAbilitySpec(TSubclassOf<UGameplayAbility>)` 생성자는 전달받은 class의 CDO를 `Spec.Ability`에 넣는다.
- CDO는 class 기본 설정을 대표한다. 실행별 변경 상태를 CDO에 쓰면 안 된다.

### `FKhazanInitialAbilityGrant`

- CharacterDefinition asset에 저장된 프로젝트의 **정적 부여 지시 한 건**이다.
- 어떤 class를 어떤 입력 tag로 grant할지를 말한다.
- 아직 ASC에 등록된 Ability도 아니고, 실행 중인 Ability도 아니며, engine `FGameplayAbilitySpec`도 아니다.

### `FGameplayAbilitySpec`

- 특정 ASC가 사용할 수 있도록 등록한 Ability 한 건의 engine runtime record다.
- class/CDO, level, input ID, source object, 고유 `FGameplayAbilitySpecHandle`, Dynamic Spec Source Tags, 활성 횟수와 instance 목록 등을 묶는다.
- ASC의 `ActivatableAbilities` container가 Spec을 소유한다.
- 같은 Ability class도 서로 다른 grant라면 서로 다른 Spec과 Handle을 가질 수 있다.

### grant와 `GiveAbility()`

- **grant**는 “그 ASC가 그 Ability를 사용할 권한/등록 항목을 갖게 한다”는 동작을 뜻한다.
- `GiveAbility(const FGameplayAbilitySpec&)`가 grant를 수행하는 engine API다.
- authority만 grant할 수 있다.
- 함수는 전달된 Spec을 ASC의 container에 등록하고 그 Spec의 Handle을 반환한다.
- “granted Ability”라고 말할 때 정확한 runtime 실체는 대개 ASC에 들어 있는 granted `FGameplayAbilitySpec`이다. 이미 공격이 실행 중이라는 뜻은 아니다.

### activation과 Ability instance

- `TryActivateAbility(Spec.Handle)`는 이미 granted된 Spec을 찾아 조건과 비용을 검사하고 실행을 시도한다.
- 인스턴싱 정책에 따라 실제 `UGameplayAbility` 실행 instance가 생성되거나 기존 instance가 재사용된다.
- 이번 BasicAttack은 `InstancedPerActor`이므로 Character의 해당 Spec에 primary instance 하나가 연결되고 실행마다 재사용된다.

### `EndAbility()`와 `ClearAbility()`

- `EndAbility()`는 현재 실행을 끝낸다. Spec 자체는 ASC에 남으므로 다음 입력에 다시 활성화할 수 있다.
- `ClearAbility(SpecHandle)`는 grant 자체를 회수해 Spec을 ASC에서 제거한다.
- P1의 초기 Ability는 Character와 ASC가 함께 끝나므로 별도 partial revoke handle을 저장하지 않는다.

```text
CharacterDefinition asset
  FKhazanInitialAbilityGrant { AbilityClass, InputTag }
                  |
                  | Character initialization reads it
                  v
temporary FGameplayAbilitySpec
                  |
                  | ASC::GiveAbility copies/registers it
                  v
ASC ActivatableAbilities: granted Spec + SpecHandle
                  |
                  | later InputTag search + TryActivateAbility(Handle)
                  v
UKhazanBasicAttackAbility runtime instance executes
                  |
                  | EndAbility: execution ends, Spec remains
                  v
ASC can activate the same granted Spec again

ClearAbility(Handle): Spec/grant itself is removed
```

## 왜 `InstancedPerActor`인가

설치된 UE 5.8.2의 `UGameplayAbility` constructor 기본값은 `InstancedPerExecution`이다. 이번 class에서는 기본값에 기대지 않고 다음 이유로 `InstancedPerActor`를 명시한다.

1. BasicAttack은 자주 실행된다. 실행마다 Ability UObject를 새로 만드는 비용이 필요하지 않다.
2. P1.5에서 montage task와 Locomotion constraint handle을 한 공격 실행 동안 Ability member로 소유해야 한다.
3. 같은 Spec의 공격 두 개가 동시에 실행되는 것은 현재 계약이 아니다. `InstancedPerActor`의 단일 active instance가 이 경계를 직접 표현한다.
4. P1.6 이후 press/release 같은 활성 instance 입력 처리는 UE 5.8 source에서도 `InstancedPerExecution`보다 `InstancedPerActor`가 명확하다.

대가는 instance member 값이 다음 activation에도 남을 수 있다는 점이다. 현재는 member가 없고, P1.5에서 handle/delegate가 생기면 `EndAbility()`의 모든 종료 경로에서 reset한다.

`NonInstanced`는 UE 5.8에서 deprecated 경로이며 실행 상태나 delegate/task를 안전하게 소유할 수 없으므로 사용하지 않는다. Net Execution/Replication Policy는 이번 standalone 수직 검증에 새 계약을 만들 근거가 없어 UE 5.8 기본값을 유지하고 multiplayer 완료로 간주하지 않는다.

## 이번 파일 범위

새로 만드는 파일은 두 개다.

```text
Source/Khazan/Ability/KhazanBasicAttackAbility.h
Source/Khazan/Ability/KhazanBasicAttackAbility.cpp
```

기존 파일에서는 다음 한 줄만 정리한다.

```text
Source/Khazan/Character/KhazanCharacter.cpp
  - 사용되지 않는 #include "ParticleHelper.h" 제거
```

build 뒤 기존 asset 하나를 편집한다.

```text
기존 DA_CharacterDefinition_Khazan
  Initial Ability Grants[0]
```

새 Component, Ability base, AbilitySet, GameplayTag, Blueprint Ability asset, montage, Attribute, GameplayEffect, input buffer를 만들지 않는다.

## 1. `KhazanBasicAttackAbility.h`

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "KhazanBasicAttackAbility.generated.h"

UCLASS()
class KHAZAN_API UKhazanBasicAttackAbility : public UGameplayAbility
{
	GENERATED_BODY()

public:
	UKhazanBasicAttackAbility();

protected:
	virtual void ActivateAbility(
		const FGameplayAbilitySpecHandle Handle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		const FGameplayEventData* TriggerEventData) override;
};
```

### 각 선언의 의미

`#include "Abilities/GameplayAbility.h"`

- base class의 완전한 정의와 정확한 override signature를 제공한다.
- `FGameplayAbilitySpecHandle`, `FGameplayAbilityActorInfo`, `FGameplayAbilityActivationInfo`, `FGameplayEventData`도 이 public contract를 통해 제공된다.

`UCLASS()`

- native class를 reflection/class picker에 등록한다.
- 이번에는 이 class 자체를 Definition의 `AbilityClass`로 선택하므로 Blueprint child가 필요 없다.

`UKhazanBasicAttackAbility : public UGameplayAbility`

- 빈 프로젝트 공통 Ability base를 만들지 않고 engine 실행 단위를 직접 사용한다.
- 두 번째 Ability에서 실제 공통 코드나 공통 불변식이 생기기 전에는 base를 추출하지 않는다.

constructor

- class 기본 실행 정책인 `InstancedPerActor`를 설정한다.
- actor나 ASC를 조회하지 않는다. constructor/CDO 구성 시점에는 runtime ActorInfo가 없다.

`ActivateAbility(...)`

- ASC가 activation 전처리와 조건 검사를 마친 뒤 호출하는 native 실행 진입점이다.
- 직접 호출하지 않는다. P1.4에서 `TryActivateAbility()`가 이 경로를 연다.

인자별 의미:

- `Handle`: 실행을 시작한 granted Spec의 `FGameplayAbilitySpecHandle` 값 복사본이다. UObject pointer나 실행 ID가 아니다.
- `ActorInfo`: ASC가 보관하는 owner/avatar/component 문맥을 가리키는 읽기용 pointer다. Ability가 소유하지 않는다.
- `ActivationInfo`: 이번 activation의 authority/prediction 문맥 값이다. `EndAbility()`에 같은 문맥을 돌려준다.
- `TriggerEventData`: Gameplay Event로 시작했을 때의 선택적 payload다. P1.3/P1.4는 handle activation이므로 사용하지 않는다.

함수는 Game Thread에서 GAS activation call stack 안에서 실행된다. Character Tick이나 animation worker thread에서 호출되지 않는다.

## 2. `KhazanBasicAttackAbility.cpp`

```cpp
#include "Ability/KhazanBasicAttackAbility.h"

#include "LogChannels.h"

UKhazanBasicAttackAbility::UKhazanBasicAttackAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
}

void UKhazanBasicAttackAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	if (!CommitAbility(Handle, ActorInfo, ActivationInfo))
	{
		EndAbility(
			Handle,
			ActorInfo,
			ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	UE_LOG(LogDefault, Log, TEXT("%s activated ability %s."),
		*GetNameSafe(ActorInfo ? ActorInfo->AvatarActor.Get() : nullptr),
		*GetNameSafe(GetClass()));

	EndAbility(
		Handle,
		ActorInfo,
		ActivationInfo,
		/* bReplicateEndAbility */ true,
		/* bWasCancelled */ false);
}
```

### 각 실행 줄의 의미

`InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;`

- 이 설정은 class/CDO 기본값에 기록된다.
- `GiveAbility()`는 UE 5.8.2에서 이 정책을 보고 Spec에 primary instance를 만든다.
- 한 Character/한 Spec에 하나인 instance를 activation마다 재사용한다.

`CommitAbility(Handle, ActorInfo, ActivationInfo)`

- activation 직전의 마지막 조건/비용/쿨다운 검사를 하고 성공하면 비용/쿨다운을 적용하는 engine 표준 경계다.
- P1.3에는 Cost/Cooldown GameplayEffect가 없어 gameplay 수치를 소비하지 않지만 lifecycle을 지금 닫아 두면 P2에서 Cost를 연결할 때 실행 함수를 다시 우회하지 않는다.
- 실패하면 공격 본문을 실행하면 안 된다.

commit 실패의 `EndAbility(..., true, true)`

- GAS 전처리로 시작된 active execution을 닫는다.
- 첫 `true`는 종료를 필요한 상대 실행 문맥에도 알리라는 engine parameter다. standalone에서도 같은 명시를 유지한다.
- 두 번째 `true`는 정상 완료가 아니라 commit 실패로 중단됐음을 뜻한다.
- `return`으로 success log와 정상 종료 경로에 진입하지 않는다.

`UE_LOG(...)`

- P1.4에서 한 번의 Attack Started가 실행 본문에 몇 번 도달했는지 관측하는 최소 증거다.
- 별도 activation counter member를 만들지 않는다. 같은 문구의 log 발생 횟수가 관측값이다.
- `ActorInfo ? ... : nullptr`은 진단 표현 자체가 null dereference를 만들지 않게 한다.
- P1.3에서는 입력이 아직 연결되지 않았으므로 이 log가 출력되지 않는 것이 정상이다.

정상 `EndAbility(..., true, false)`

- 현재는 montage/task가 없으므로 관측 직후 같은 call stack에서 정상 종료한다.
- 두 번째 bool이 `false`이므로 정상 완료로 기록된다.
- Spec은 제거되지 않으며 다음 activation을 받을 수 있다.

### `Super::ActivateAbility()`를 호출하지 않는 이유

설치된 UE 5.8.2의 base `UGameplayAbility::ActivateAbility()`는 native 구현 본문을 제공하는 함수가 아니라 Blueprint `K2_ActivateAbility`/event 경로를 dispatch하거나 아무 동작도 하지 않는 기본 구현이다. engine source도 native child가 이 함수를 override하고 `CommitAbility()`를 호출하라고 명시한다.

이번 native class가 실행 전체를 소유하므로 `Super::ActivateAbility()`를 호출하지 않는다. 나중에 data 전용 Blueprint child를 만들더라도 Event Activate Ability graph를 이 native path와 병행해 두 실행 권위로 만들지 않는다.

## 3. 기존 Character include 정리

`Source/Khazan/Character/KhazanCharacter.cpp`에서 다음 한 줄을 삭제한다.

```cpp
#include "ParticleHelper.h"
```

현재 파일 어디에서도 해당 header의 심볼을 쓰지 않는다. P1.3에 필요한 include를 그 자리에 추가하지 않는다. 새 Ability cpp가 자기 log dependency를 직접 include한다.

## 4. Editor를 열기 전 cold build

새 reflected UCLASS를 추가하므로 Unreal Editor와 Live Coding Console을 닫고 전체 build한다.

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
  KhazanEditor Win64 Development `
  '-Project=C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' `
  -WaitMutex -NoHotReloadFromIDE
```

기대 결과:

1. UHT가 `UKhazanBasicAttackAbility` generated code를 만든다.
2. 새 cpp와 Character cpp가 compile된다.
3. `UnrealEditor-Khazan.dll` link와 metadata 작성이 성공한다.
4. 마지막이 `Result: Succeeded`다.

새 UCLASS가 build되지 않은 상태에서 Editor를 먼저 열면 Definition class picker에 새 class가 나타나지 않을 수 있다.

## 5. 기존 CharacterDefinition asset에 첫 entry 작성

build 성공 후 Editor를 새로 연다.

1. 기존 Khazan CharacterDefinition asset을 연다. 새 Definition asset을 복제하지 않는다.
2. `Character | Locomotion` 값이 기존과 같은지 먼저 확인한다.
3. `Character | Abilities > Initial Ability Grants`의 배열 크기를 `1`로 만든다.
4. `[0] > Ability Class`에서 native `KhazanBasicAttackAbility`를 선택한다.
5. `[0] > Input Tag`에서 정확히 `Input.Action.Attack`을 선택한다.
6. asset을 저장한다.

이 entry의 두 필드는 다음처럼 소비된다.

```text
AbilityClass = KhazanBasicAttackAbility
  -> FGameplayAbilitySpec constructor가 class CDO와 새 SpecHandle을 준비

InputTag = Input.Action.Attack
  -> Spec.GetDynamicSpecSourceTags()에 기록
  -> P1.1 ASC helper가 HasTagExact로 찾을 값
```

Ability Asset Tags에 `Input.Action.Attack`을 넣지 않는다. Dynamic Spec Source Tag는 **이번 grant의 입력 mapping**, Ability Asset Tag는 **Ability 종류 분류와 cancel/block 관계**다. P1.3에는 후자의 실제 소비가 없으므로 `Ability.Action.Attack`이나 `State.Action.Attack`을 아직 추가하지 않는다.

## 6. P1.3 PIE 검증

1. DevMap에서 PIE를 시작한다.
2. 콘솔에 `ShowDebug AbilitySystem`을 입력한다.
3. 이어 `AbilitySystem.Debug.SetCategory Ability`를 입력한다.
4. local player ASC의 Ability 목록에 `KhazanBasicAttackAbility`가 정확히 한 줄 존재하는지 확인한다.
5. 상태가 `Active`로 고정되어 있지 않은지 확인한다.
6. Output Log에서 Definition load, locomotion 초기화, invalid AbilityClass 오류가 없는지 확인한다.
7. Attack 입력은 아직 아무 실행도 만들지 않아야 하며 `activated ability` log도 없어야 한다.
8. Walk/Run/Sprint/Stop이 이전과 같고 PIE 종료 crash가 없는지 확인한다.

`ShowDebug AbilitySystem`은 class/활성 상태를 확인할 수 있지만 P1.1의 exact input tag mapping 자체를 화면에 모두 표시하지는 않는다. 이번에는 asset의 `[0].InputTag` 값과 granted class 존재를 각각 확인하고, 실제 mapping은 P1.4의 입력 activation으로 종단 검증한다.

HUD가 보이지 않으면 Output Log에서 engine `GiveAbility` log를 검색한다. temporary auto activation 코드는 넣지 않는다.

## 7. P1.3 합격 기준

다음이 모두 성립하면 P1.3을 통과한 것이다.

1. 새 header/cpp가 위 책임과 signature로 존재한다.
2. `InstancedPerActor`만 명시했고 실행 member나 공통 base를 추가하지 않았다.
3. `CommitAbility` 실패는 canceled 종료, 성공은 한 log 뒤 normal 종료로 닫힌다.
4. cold build가 성공한다.
5. Definition 기존 이동 값이 보존되고 초기 grant entry가 정확히 한 개다.
6. PIE의 ASC Ability 목록에 BasicAttack Spec이 정확히 한 개다.
7. 아직 input 미연결이므로 activation log가 0회다.
8. 기존 이동과 종료 수명에 회귀가 없다.

## 8. 실패 진단

### class picker에 BasicAttack이 없음

- Editor를 새 DLL 이전부터 열어 둔 상태인지 확인한다.
- cold build의 UHT와 link 성공을 확인한다.
- header에 `UCLASS()`, `GENERATED_BODY()`, 마지막 일반 include 뒤 `generated.h`가 있는지 확인한다.

### `ActivateAbility` override 불일치

- `Handle`, `ActorInfo`, `ActivationInfo`, `TriggerEventData` 순서를 대조한다.
- `ActivationInfo`는 engine signature와 같이 값 전달이다.
- 함수 끝에 `const`를 붙이지 않는다.

### `LogDefault`를 찾지 못함

- 새 Ability cpp에 `#include "LogChannels.h"`가 있는지 확인한다.
- header에 이 include를 옮기지 않는다.

### Definition에서 null AbilityClass 오류

- 배열을 먼저 1로 만들고 class를 선택하지 않은 채 PIE한 경우다.
- `[0].AbilityClass`가 native `KhazanBasicAttackAbility`인지 확인한다.

### Ability 목록에 두 줄 이상 존재

- `Initial Ability Grants`에 중복 entry가 있는지 먼저 본다.
- grant loop를 `PossessedBy`, `BeginPlay`, Controller에도 복사했는지 확인한다.
- P1.2 계약상 grant caller는 authority `PostInitializeComponents()` 한 곳뿐이다.

### Ability가 P1.3에서 실행됨

- 임시 auto activation, Blueprint BeginPlay activation, 기존 Controller Attack 호출을 추가했는지 찾는다.
- 이번 checkpoint에서는 granted와 active를 구분하기 위해 실행되지 않아야 한다.

## 다음 checkpoint — 아직 구현하지 않음

P1.4에서만 `AKhazanPlayerController::Input_Attack`의 실제 Enhanced Input trigger phase를 `Started`로 확정하고, controlled Pawn의 Khazan ASC에 `Input.Action.Attack`을 전달한다. 그때 `InputTag -> granted Spec -> TryActivateAbility -> Commit -> log -> EndAbility` 전체 경로를 처음 실행한다. P1.4 전에는 montage, 공격 상태 tag, combo buffer를 추가하지 않는다.


<a id="p1-4-attack-input-activation-20260916"></a>
# 2026-09-16 — P1.3 적용 대조 뒤 P1.4 Attack 입력 활성화

## P1.3 실제 대조 결과

- `UKhazanBasicAttackAbility`는 `UGameplayAbility`를 직접 상속하고 `InstancedPerActor`를 명시한다.
- `ActivateAbility()`는 `CommitAbility()` 실패를 canceled 종료로 닫고, 성공하면 `LogAbility` 한 줄을 남긴 뒤 normal 종료한다. Montage, 비용, hit, combo 상태는 아직 없다.
- `LogAbility`는 `LogChannels.h/.cpp`에 실제 선언·정의돼 있으므로 현재 Source의 로그 category 사용은 유효하다.
- `DA_CharacterDefinition_Khazan.uasset`의 직렬화 데이터에는 `InitialAbilityGrants`, `KhazanBasicAttackAbility`, `Input.Action.Attack`이 존재한다. 에셋 편집이 저장된 상태다.
- 2026-09-16 UE 5.8.2 UBT cold build 명령은 `Generated code is up to date`, `Target is up to date`, `Result: Succeeded`로 끝났다.
- 2026-09-15 최신 PIE 기록에는 `ShowDebug AbilitySystem`과 `AbilitySystem.Debug.SetCategory Ability` 실행, 정상 PIE 종료가 남아 있다. 디버그 HUD에 표시된 Spec 행 자체는 파일 로그에 저장되지 않으므로 **BasicAttack Spec 정확히 한 개**라는 시각 확인은 사용자 확인 항목으로 남긴다.

## P1.4의 정확한 목표

이번 checkpoint의 목표는 다음 한 문장이다.

> 물리 Attack 입력의 시작 경계 한 번이 `Input.Action.Attack`과 정확히 일치하는 granted Spec을 찾아 `UKhazanBasicAttackAbility`를 한 번 실행하고, 그 실행이 같은 call stack에서 정상 종료되는 것을 확인한다.

이번 단계는 공격 애니메이션을 재생하는 단계가 아니다. 성공했을 때 보이는 gameplay 동작은 없으며 `LogAbility`의 activation log가 주 증거다. 화면에서 공격 모션이 나오지 않는 것이 정상이다.

## 작성자·소비자·수명 계약

| 항목 | 작성자 | 소비자 | 갱신/종료 시점 |
| --- | --- | --- | --- |
| 물리 Attack 입력 edge | Enhanced Input | `AKhazanPlayerController::Input_Attack()` | 키/버튼이 비활성에서 평가 시작 상태로 바뀐 한 프레임 |
| `Input.Action.Attack` native tag | `KhazanGameplayTags` | PlayerController와 ASC의 exact tag 검색 | 정적 등록 값이며 runtime에 변경하지 않음 |
| Dynamic Spec Source Tag | Character의 초기 grant loop | `UKhazanAbilitySystemComponent` | authority 초기화 때 Spec에 기록되고 ASC와 함께 종료 |
| BasicAttack 실행 | GAS `TryActivateAbility()` | `UKhazanBasicAttackAbility::ActivateAbility()` | `EndAbility()`에서 즉시 종료, granted Spec은 유지 |

호출은 Game Thread에서 일어난다. AnimInstance worker thread나 Character Tick은 이 경로에 참여하지 않는다.

## 이번 파일 범위

직접 수정할 파일은 하나다.

```text
Source/Khazan/Player/KhazanPlayerController.cpp
```

`KhazanPlayerController.h`의 기존 `Input_Attack(const FInputActionValue&)` 선언은 그대로 사용할 수 있다. 다음 파일은 이번 checkpoint에서 수정하지 않는다.

- `KhazanAbilitySystemComponent.h/.cpp`
- `KhazanBasicAttackAbility.h/.cpp`
- `KhazanCharacter.h/.cpp`
- `KhazanCharacterDefinitionData.h/.cpp`
- `DA_CharacterDefinition_Khazan`
- `IA_Attack`, `DA_InputData`, `IMC_Default`

## 1. concrete ASC header include 추가

`KhazanPlayerController.cpp`의 project include 구역에 다음 한 줄을 추가한다.

```cpp
#include "Ability/KhazanAbilitySystemComponent.h"
```

이 include가 필요한 이유는 `AKhazanCharacter::GetAbilitySystemComponent()`의 반환형이 engine base인 `UAbilitySystemComponent*`인 반면, 호출할 함수 `TryActivateAbilitiesByInputTag()`는 `UKhazanAbilitySystemComponent`에만 선언돼 있기 때문이다. Header에는 concrete ASC를 멤버나 인자로 노출하지 않으므로 이 include를 `KhazanPlayerController.h`에 넣지 않는다.

## 2. Attack binding을 `Started`로 변경

`SetupInputComponent()`의 Turn/Jump/Attack 지역 변수는 기능 이름으로 정리하고 Attack의 trigger event만 `Started`로 바꾼다.

```cpp
const UInputAction* TurnAction =
	InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Turn);
EnhancedInputComponent->BindAction(
	TurnAction,
	ETriggerEvent::Triggered,
	this,
	&ThisClass::Input_Turn);

const UInputAction* JumpAction =
	InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Jump);
EnhancedInputComponent->BindAction(
	JumpAction,
	ETriggerEvent::Triggered,
	this,
	&ThisClass::Input_Jump);

const UInputAction* AttackAction =
	InputData->FindInputActionByTag(KhazanGameplayTags::Input_Action_Attack);
EnhancedInputComponent->BindAction(
	AttackAction,
	ETriggerEvent::Started,
	this,
	&ThisClass::Input_Attack);
```

`Action2/Action3/Action4`를 `TurnAction/JumpAction/AttackAction`으로 바꾸는 것은 runtime 변경이 아니다. 무엇을 가리키는 포인터인지 이름에서 확인하기 위한 기존 가독성 감사 항목의 정리다.

UE 5.8.2의 `ETriggerEvent` 계약에서 `Started`는 `None -> Ongoing` 또는 `None -> Triggered` 전이에 한 번 발생한다. `Triggered`에는 `Triggered -> Triggered`가 포함되므로 디지털 Attack 버튼을 누르고 있는 동안 매 입력 처리 tick마다 callback이 반복될 수 있다. 현재 BasicAttack은 즉시 `EndAbility()`되므로 `Triggered`를 유지하면 한 번 누르고 있는 동안 재활성화 로그가 반복된다. `Started`가 이번의 “한 press edge = 한 activation attempt” 계약을 만든다.

Jump는 아직 P1.6 전이므로 기존 `Triggered`와 직접 `Character::Jump()` 경로를 이번 변경에서 건드리지 않는다.

## 3. 빈 `Input_Attack()` 구현

기존 빈 함수 본문을 다음처럼 작성한다.

```cpp
void AKhazanPlayerController::Input_Attack(const FInputActionValue& InputValue)
{
	if (AKhazanCharacter* KhazanCharacter = Cast<AKhazanCharacter>(GetPawn()))
	{
		if (UKhazanAbilitySystemComponent* KhazanAbilitySystemComponent =
			Cast<UKhazanAbilitySystemComponent>(
				KhazanCharacter->GetAbilitySystemComponent()))
		{
			KhazanAbilitySystemComponent->TryActivateAbilitiesByInputTag(
				KhazanGameplayTags::Input_Action_Attack);
		}
	}
}
```

`InputValue`는 callback signature를 기존 Enhanced Input value delegate와 맞추기 위해 남겨 둔다. 이번 동작은 값의 크기나 축을 쓰지 않고 `Started` edge 자체만 소비하므로 함수 본문에서 읽지 않는다.

### 각 줄과 분기의 의미

`GetPawn()`

- 현재 이 PlayerController가 소유한 Pawn을 그 입력 순간에 조회한다.
- Controller가 Pawn pointer를 별도 멤버로 복제해 보관하지 않는다. possession 변경 시 stale pointer가 생기지 않는다.

`Cast<AKhazanCharacter>(GetPawn())`

- 현재 Pawn이 프로젝트의 공통 Character 계약을 만족하는지 확인한다.
- 실패하면 입력을 처리하지 않고 함수가 끝난다. 공격 입력 때문에 null 또는 다른 Pawn을 역참조하지 않는다.
- `AKhazanPlayer` 전용 실행 코드를 만드는 대신 Player가 이미 상속하는 공통 Character의 ASC 계약을 사용한다.

`KhazanCharacter->GetAbilitySystemComponent()`

- `IAbilitySystemInterface` override를 통해 Character가 소유한 ASC base pointer를 받는다.
- ASC를 Controller가 생성하거나 소유하지 않는다. ASC 수명은 Character가 계속 소유한다.

`Cast<UKhazanAbilitySystemComponent>(...)`

- base pointer의 실제 runtime class가 P1.1에서 교체한 Khazan subclass인지 확인한다.
- 실패하면 프로젝트 전용 입력 API를 호출하지 않는다. `CastChecked`를 쓰지 않으므로 설정 오류가 입력 순간 crash로 바뀌지 않는다.

`TryActivateAbilitiesByInputTag(KhazanGameplayTags::Input_Action_Attack)`

- 문자열을 새로 만들지 않고 native tag singleton을 const reference로 전달한다.
- ASC는 유효한 tag인지 확인하고 Ability list를 잠근 뒤 모든 granted Spec을 돈다.
- `DynamicSpecSourceTags.HasTagExact()`이 정확히 같은 입력 tag를 가진 Spec만 선택한다.
- 일치하는 Spec의 engine `FGameplayAbilitySpecHandle`로 `TryActivateAbility()`를 호출한다.
- 반환 bool은 현재 UI나 AI 소비자가 없으므로 Controller가 저장하지 않는다. 별도 성공 bool, delegate, request ID를 만들지 않는다.

## 4. 전체 호출 순서

```text
Attack 키/버튼을 누름
  -> IA_Attack 평가가 시작됨
  -> ETriggerEvent::Started 한 번
  -> AKhazanPlayerController::Input_Attack
  -> 현재 Pawn을 AKhazanCharacter로 확인
  -> Character가 소유한 UKhazanAbilitySystemComponent 확인
  -> TryActivateAbilitiesByInputTag(Input.Action.Attack)
  -> granted Spec의 Dynamic Spec Source Tag exact match
  -> TryActivateAbility(Spec.Handle)
  -> UKhazanBasicAttackAbility::ActivateAbility
  -> CommitAbility
  -> LogAbility 한 줄
  -> EndAbility(normal)
  -> 같은 Spec은 ASC에 남아 다음 press를 기다림
```

현재 helper 이름이 복수형인 이유는 서로 다른 granted Spec이 같은 입력 tag를 가질 수 있는 engine 자료구조를 순회하기 때문이다. P1.3의 데이터 계약은 Attack tag에 BasicAttack Spec 정확히 하나이므로 실제 결과는 한 번이어야 한다. 한 press에 로그가 두 줄이면 helper를 첫 match에서 강제로 끊기 전에 중복 grant를 먼저 고친다.

## 5. 이번 단계에서 추가하지 않는 것

- `AbilitySpecInputPressed()` / `AbilitySpecInputReleased()` 전달
- held input 배열과 매-frame input processor
- Montage와 `UAbilityTask_PlayMontageAndWait`
- Locomotion constraint
- 공격 중 상태 tag, cooldown, Stamina cost
- hit window, damage, combo buffer
- Controller의 activation 성공 bool, counter, delegate, 요청 구조체
- Attack용 새 GameplayTag

`AbilitySpecInputPressed/Released`는 P1.6 Jump의 release 소비자가 실제 생길 때 추가한다. P1.4의 BasicAttack은 activation edge만 필요하다.

## 6. 저장 전 직접 대조

1. `KhazanPlayerController.cpp`에 concrete ASC include가 정확히 한 번 있다.
2. Attack action 검색은 기존 `KhazanGameplayTags::Input_Action_Attack`을 사용한다.
3. Attack binding만 `ETriggerEvent::Started`다.
4. `Input_Attack()`은 `GetPawn()`에서 시작하고 Controller에 Pawn/ASC 멤버를 새로 만들지 않았다.
5. `TryActivateAbilitiesByInputTag()`를 직접 호출하며 `TryActivateAbility()`를 Controller에서 다시 구현하지 않았다.
6. Jump의 직접 호출과 force-feedback 시험 코드는 P1.6 전까지 보존했다.

## 7. build

새 reflected type은 없지만 checkpoint를 분리하기 위해 PIE, Unreal Editor, Live Coding Console을 닫고 다음 cold build를 실행한다.

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
  KhazanEditor Win64 Development `
  '-Project=C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' `
  -WaitMutex -NoHotReloadFromIDE
```

기대 결과는 `KhazanPlayerController.cpp` compile, Khazan module/DLL link, 마지막 `Result: Succeeded`다. 변경 저장을 잊었다면 `Target is up to date`만 나오므로 파일 저장 상태를 먼저 확인한다.

## 8. P1.4 PIE 검증

### 사전 확인

1. Editor를 새 build 뒤 연다.
2. `DA_CharacterDefinition_Khazan`의 `Initial Ability Grants`가 정확히 한 원소인지 확인한다.
3. `[0].Ability Class = KhazanBasicAttackAbility`인지 확인한다.
4. `[0].Input Tag = Input.Action.Attack`인지 확인한다.
5. DevMap에서 PIE를 시작한다.
6. 콘솔에 `ShowDebug AbilitySystem`을 입력한다.
7. 콘솔에 `AbilitySystem.Debug.SetCategory Ability`를 입력한다.
8. BasicAttack Spec이 한 줄 있고 현재 계속 Active 상태가 아닌지 확인한다.

### 입력 횟수 검증

1. Output Log에서 `LogAbility`를 필터링하거나 `activated ability`를 검색한다.
2. Attack 버튼을 짧게 한 번 누르고 놓는다.
3. 다음 형식의 로그가 정확히 한 줄 늘어나는지 확인한다.

```text
LogAbility: <현재 Avatar 이름> activated ability KhazanBasicAttackAbility.
```

4. Attack 버튼을 계속 누르고 있어도 같은 press에서 로그가 더 늘지 않는지 확인한다.
5. 버튼을 놓고 다시 한 번 누르면 로그가 정확히 한 줄 더 생기는지 확인한다.
6. 빠르게 여러 번 눌렀을 때 discrete press 수와 log 수가 같은지 확인한다.

Ability는 로그 직후 즉시 끝나므로 debug HUD에서 `Active`를 눈으로 포착하지 못할 수 있다. 이번 checkpoint에서는 activation log가 실행 본문 도달 증거이고, HUD의 Spec이 계속 남아 있는 것이 `EndAbility()`가 grant를 지우지 않았다는 증거다.

### 회귀 검증

1. Walk/Run/Sprint 이동이 이전과 같다.
2. 발별 Walk/Run Stop과 Sprint 단일 Stop이 이전과 같다.
3. Attack 입력 뒤 이동 입력과 Sprint가 막힌 채 남지 않는다.
4. PIE를 끝낼 때 crash/assert가 없다.
5. Output Log에 invalid AbilityClass, missing Definition, ActorInfo 관련 오류가 없다.

## 9. P1.4 합격 기준

다음이 모두 성립하면 P1.4를 통과한 것이다.

1. build가 `Result: Succeeded`다.
2. ASC에 BasicAttack Spec이 정확히 한 개다.
3. 한 번의 press가 activation log 한 줄을 만든다.
4. 같은 hold가 추가 activation을 만들지 않는다.
5. release 뒤 다음 press는 다시 정확히 한 번 활성화된다.
6. Spec은 실행 후에도 남고 Active 상태는 남지 않는다.
7. 기존 locomotion과 PIE 종료에 회귀가 없다.

## 10. 실패 진단 순서

### 눌러도 callback이 실행되지 않음

1. `DA_InputData`에 `Input.Action.Attack -> IA_Attack` entry가 있는지 확인한다.
2. `IMC_Default`에 `IA_Attack`의 실제 키/버튼 mapping이 있는지 확인한다.
3. Attack binding이 `Started`와 `Input_Attack`을 가리키는지 확인한다.
4. `SetupInputComponent()`가 실행됐고 `InputData`가 null이 아닌지 debugger로 확인한다.

### callback은 실행되지만 activation log가 없음

1. `GetPawn()` 결과가 현재 Player Character인지 확인한다.
2. 두 Cast가 성공하는지 확인한다.
3. `TryActivateAbilitiesByInputTag()` 진입 시 `InputTag`가 `Input.Action.Attack`인지 확인한다.
4. `GetActivatableAbilities()`에 BasicAttack Spec이 한 개 있는지 확인한다.
5. 그 Spec의 `DynamicSpecSourceTags`에 `Input.Action.Attack`이 exact tag로 있는지 확인한다.
6. `TryActivateAbility(AbilitySpec.Handle)` 반환값을 debugger에서 확인한다.
7. 반환이 false면 ActorInfo의 Owner/Avatar 유효성과 activation failure log를 확인한다.

### 한 번 누르고 있는 동안 로그가 계속 늘어남

- Attack binding이 여전히 `Triggered`인지 먼저 확인한다.
- 같은 Attack action을 Blueprint나 다른 C++ 위치에서도 binding했는지 찾는다.
- 임시 Tick activation이나 BeginPlay activation을 남겨 두지 않았는지 확인한다.

### 한 번 짧게 눌렀는데 로그가 두 줄 이상 생김

- Definition에 같은 Attack entry가 중복인지 확인한다.
- `ShowDebug AbilitySystem`에서 BasicAttack Spec이 여러 개인지 확인한다.
- grant loop가 `PostInitializeComponents()` 외 lifecycle에 복사되지 않았는지 확인한다.
- `SetupInputComponent()`에서 같은 action/callback binding이 중복인지 확인한다.

### `TryActivateAbility()`는 성공처럼 보이지만 log가 없음

engine API의 bool은 remote activation이나 이후 실패 때문에 최종 실행 완료의 절대 증거가 아니다. 현재 standalone P1.4에서는 `UKhazanBasicAttackAbility::ActivateAbility()` breakpoint와 `LogAbility`가 실제 본문 도달 증거다. `CommitAbility()`가 false면 canceled 종료 뒤 success log 전에 return하므로 해당 분기도 확인한다.

## 다음 checkpoint — P1.4 통과 뒤에만 진행

P1.5는 실제 공격 Montage를 `UAbilityTask_PlayMontageAndWait`로 재생하고 그 한 실행이 Locomotion constraint handle을 소유·해제하는 단계다. P1.4의 press 횟수와 activation 횟수가 먼저 일치해야 Montage 중복, 입력 중복, task cleanup 문제를 서로 구분할 수 있다. P1.4를 통과하기 전에는 Montage, hit notify, damage, combo를 추가하지 않는다.

<a id="p1-4-applied-p1-5-montage-constraint-20260916"></a>

# 2026-09-16 — P1.4 적용 확인과 P1.5 Montage·실행별 이동 제약

## 이번 checkpoint의 위치

사용자가 `KhazanPlayerController.cpp`에 P1.4를 적용했다. 실제 Source는 다음 경계를 만족한다.

- Attack action은 `ETriggerEvent::Started`에서 한 press edge만 전달한다.
- Controller는 현재 Pawn의 `UKhazanAbilitySystemComponent`를 구해 `Input.Action.Attack`을 전달한다.
- ASC가 granted Spec의 Dynamic Spec Source Tag를 exact match하고 `TryActivateAbility()`를 호출한다.
- 사용자가 함께 바꾼 Jump binding의 `Started`는 보존한다. Jump는 아직 직접 `Character::Jump()`를 호출하며 P1.6에서 GAS press/release 경로로 옮긴다.

2026-09-16 UE 5.8.2 cold build는 `Target is up to date`, `Result: Succeeded`였다. 사용자는 이번 구현 완료를 보고했다. 이 기록 작성자가 새 PIE 화면과 한 press당 로그 개수를 다시 캡처한 것은 아니므로, P1.4 runtime 횟수와 이동 회귀의 최종 증거는 사용자 확인 범위다.

P1.5의 목표는 즉시 끝나던 BasicAttack을 다음 수명으로 바꾸는 것이다.

```text
Attack Started
  -> granted Spec 활성화
  -> BasicAttack Ability instance 활성
  -> 이 실행의 Movement Constraint 한 건 획득
  -> CommitAbility
  -> PlayMontageAndWait task 활성
  -> 정상 완료 / Montage 중단 / Ability 취소 / EndPlay
  -> 이 실행이 얻은 Constraint handle 한 건만 해제
  -> EndAbility
  -> task 종료, Spec은 ASC에 계속 남음
```

이번 범위에는 hit notify, 무기 충돌, 피해, stamina, cooldown, combo buffer, motion warping, 새 상태 tag가 없다. Montage는 아직 공격 표현과 Ability 수명의 기준일 뿐이다.

## 실제 에셋 표적 확인 결과

2026-09-16 UE Editor의 read-only Python 조회 결과는 다음과 같다.

| 항목 | 확인값 | 의미 |
| --- | --- | --- |
| 후보 Sequence | `/Game/_Art/Kazan/Animation/Weapons/DualAxeSword/Shared/Combat/Attacks/FastAttack/CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1` | 경로와 이름으로 고른 P1 구조 시험 후보이며 원작의 확정 1타라고 판정하지 않음 |
| Asset class | `AnimSequence` | Montage가 아니므로 runtime용 Montage를 별도로 생성해야 함 |
| Skeleton | `/Game/_Art/Kazan/Character/Meshs/SK_Khazan` | Player mesh와 `ABP_Player` target skeleton이 같은 `SK_Khazan`이므로 골격 계약은 맞음 |
| Play length | `10.375 s` | asset 직접 조회값. 단일 타격의 확정 지속시간으로 사용하지 않음 |
| Rate Scale | `1.0` | source sequence의 직접값 |
| Root Motion | `Enable Root Motion=false`, `Force Root Lock=false` | 이 후보는 현재 root motion 이동을 제공하지 않음 |
| Main ABP 마지막 구조 | `Locomotion -> DefaultSlot -> Output Pose` | `DefaultGroup.DefaultSlot` Montage를 최종 pose에 합성할 위치가 있음 |

같은 `FastAttack` 폴더의 8개 Sequence가 모두 `10.375 s`로 조회됐다. 이 공통 길이는 각 공격의 실제 gameplay recovery 시간을 증명하지 않는다. 따라서 생성 직후 전체 구간을 그대로 P1.5 합격본으로 사용하지 않는다. Editor에서 원하는 타격 동작이 들어 있는 실제 frame 구간을 눈으로 확인하고 Montage segment의 시작·끝을 그 구간으로 제한한다. 시작/끝 frame을 아직 확인하지 않았다면 `미확인`으로 두며 임의 초 값을 문서나 코드에 넣지 않는다.

## P1.5-A — Montage asset 만들기

### 1. 원본 Sequence 구간 확인

1. 위 `CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1`을 연다.
2. Preview 반복 재생을 끄고 timeline 표시를 frame 기준으로 본다.
3. 준비 자세에서 실제 공격이 시작되는 첫 frame과 회복이 끝나는 마지막 frame을 찾는다.
4. 두 frame과 Editor가 표시하는 대응 시간을 별도로 적는다. 이 값은 원작 gameplay metadata의 직접 timing이 아니라 **현재 import animation에서 선택한 P1 표현 구간**으로 기록한다.
5. 10.375초 전체에 서로 다른 동작이나 긴 정지 구간이 섞였다면 원본 Sequence 자체를 파괴적으로 crop하지 않는다. Montage의 Anim Segment 범위만 제한한다.

이 단계에서 정확한 타격 판정 시작/끝을 정하지 않는다. 눈으로 고른 구간은 pose 재생 범위이고, 실제 hit window는 P3에서 원작 notify/metadata를 다시 확인해 별도 계약으로 만든다.

### 2. Montage 생성

1. Content Browser에서 후보 Sequence를 우클릭한다.
2. `Create` 또는 `Create Advanced Asset` 메뉴의 `Create AnimMontage`를 선택한다.
3. 새 폴더 `/Game/_Art/Kazan/Animation/Combat/Runtime/DualAxeSword`를 만든다. 현재 이 폴더는 Source에 없으므로 직접 생성해야 한다.
4. 생성한 asset을 그 폴더로 옮기고 `AM_DAS_BasicAttack01`로 이름을 바꾼다.
5. Montage를 열고 Montage Track의 Anim Segment를 선택한다.
6. `Anim Start Time`과 `Anim End Time`을 앞에서 확인한 실제 표현 구간에 맞춘다. 숫자는 timeline에서 읽은 값을 그대로 사용한다.
7. `Anim Play Rate=1.0`, `Loop Count=1`로 둔다. `1.0`은 source 속도를 바꾸지 않는 항등 배율이고, 한 번 재생은 이번 단일 공격 실행의 구조 조건이다.
8. Slot이 `DefaultGroup.DefaultSlot`인지 확인한다. `ABP_Player`의 마지막 관측 Slot과 정확히 같아야 한다.
9. 자동 blend out은 켠 상태로 둔다. Blend In/Out 수치는 원작값을 확인하지 못했으므로 생성된 Editor 기본값을 이번 구조 시험의 임시값으로 유지하고 원작값이라고 기록하지 않는다.
10. 저장한다.

source Sequence의 root motion이 꺼져 있으므로 이 Montage는 공격 전진을 만들지 않는다. P1.5에서 캐릭터가 제자리 CMC 이동을 유지하는 것이 현재 자료와 맞는다. lunge, motion warping, target correction은 이 단계에서 추가하지 않는다.

## P1.5-B — BasicAttack의 실행 수명 구현

수정 파일은 두 개다.

```text
Source/Khazan/Ability/KhazanBasicAttackAbility.h
Source/Khazan/Ability/KhazanBasicAttackAbility.cpp
```

`KhazanCharacter`, PlayerController, ASC, CharacterDefinition schema, LocomotionComponent 구현은 이번에 바꾸지 않는다. Ability가 이미 공개된 `AcquireMovementConstraint()`와 `ReleaseMovementConstraint()`를 소비한다.

### 1. `KhazanBasicAttackAbility.h`

현재 헤더를 다음 형태로 확장한다.

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "Character/Component/KhazanLocomotionComponent.h"
#include "KhazanBasicAttackAbility.generated.h"

class UAbilityTask_PlayMontageAndWait;
class UAnimMontage;

UCLASS(Blueprintable)
class KHAZAN_API UKhazanBasicAttackAbility : public UGameplayAbility
{
	GENERATED_BODY()

public:
	UKhazanBasicAttackAbility();

protected:
	virtual void ActivateAbility(
		const FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		const FGameplayEventData* TriggerEventData) override;

	virtual void EndAbility(
		const FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		bool bReplicateEndAbility,
		bool bWasCancelled) override;

private:
	UFUNCTION()
	void HandleMontageCompleted();

	UFUNCTION()
	void HandleMontageInterrupted();

	UFUNCTION()
	void HandleMontageCancelled();

	void FinishAbility(bool bWasCancelled);

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Khazan|Attack|Animation",
		meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UAnimMontage> AttackMontage = nullptr;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Khazan|Attack|Animation",
		meta = (AllowPrivateAccess = "true"))
	float MontagePlayRate = 1.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Khazan|Attack|Locomotion",
		meta = (AllowPrivateAccess = "true"))
	FKhazanMovementConstraint MovementConstraint;

	UPROPERTY(Transient)
	TObjectPtr<UAbilityTask_PlayMontageAndWait> MontageTask = nullptr;

	UPROPERTY(Transient)
	TWeakObjectPtr<UKhazanLocomotionComponent> MovementConstraintOwner;

	UPROPERTY(Transient)
	FKhazanMovementConstraintHandle MovementConstraintHandle;
};
```

#### 선언별 책임

- `KhazanLocomotionComponent.h` include가 필요한 이유는 `FKhazanMovementConstraintHandle`을 값 멤버로 보관하기 때문이다. 포인터 class만 전방 선언하는 경우와 달리 값 타입은 헤더에서 완전한 정의가 필요하다.
- `UCLASS(Blueprintable)`은 native 실행 로직을 유지하면서 캐릭터 variant별 Montage와 제약 설정을 Blueprint CDO에 저장하게 한다. 빈 C++ Ability base를 추가하는 것이 아니다.
- `EndAbility()` override는 정상 완료, task 중단, 외부 취소, `DestroyActiveState()`가 모두 통과하는 공통 cleanup 지점이다.
- 세 `UFUNCTION()`은 `FMontageWaitSimpleDelegate`의 dynamic multicast에 연결되므로 reflection 선언이 필요하고 인자가 없다.
- `AttackMontage`는 정적 설정이다. 작성자는 `GA_BasicAttack_Khazan` Class Defaults, 소비자는 `ActivateAbility()`, 갱신 시점은 asset 편집 때뿐이다.
- `MontagePlayRate`도 정적 설정이다. `1.0`은 현재 source의 `Rate Scale=1.0`과 같은 항등 배율이다. 원작 gameplay 배속을 새로 추정한 값이 아니다.
- `MovementConstraint`는 한 activation이 LocomotionComponent에 기여할 값이다. Blueprint CDO가 작성하고 Ability activation이 사본을 넘긴다.
- `MontageTask`는 현재 실행의 비동기 재생 대기 객체다. `Transient`이므로 asset 설정으로 저장하지 않는다.
- `MovementConstraintOwner`는 handle을 발급한 정확한 Component의 weak pointer다. Ability가 Component 수명을 연장하지 않으면서 종료 때 같은 발급자에게 영수증을 돌려준다.
- `MovementConstraintHandle`은 이 실행이 획득한 한 제약의 영수증이다. 다른 공격, 피격, scripted 제약을 일괄 해제하지 않는다.

`InstancedPerActor`이므로 이 세 runtime 멤버는 Character의 BasicAttack Ability instance 한 개에 존재한다. 같은 Spec은 활성 중 기본적으로 다시 활성화되지 않으므로 현재 단계에서는 한 instance에 두 공격 실행의 handle이 겹치지 않는다. Combo/retrigger 정책은 P6에서 별도로 정한다.

### 2. `KhazanBasicAttackAbility.cpp`

현재 즉시 `EndAbility()`하는 구현을 다음으로 교체한다.

```cpp
#include "Ability/KhazanBasicAttackAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Animation/AnimMontage.h"
#include "Character/KhazanCharacter.h"
#include "LogChannels.h"

UKhazanBasicAttackAbility::UKhazanBasicAttackAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
}

void UKhazanBasicAttackAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	AKhazanCharacter* Character =
		ActorInfo ? Cast<AKhazanCharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
	UKhazanLocomotionComponent* Locomotion =
		Character ? Character->GetLocomotionComponent() : nullptr;

	const bool bHasValidMontageConfig =
		IsValid(AttackMontage) &&
		FMath::IsFinite(MontagePlayRate) &&
		MontagePlayRate > 0.f;

	if (!Locomotion || !bHasValidMontageConfig)
	{
		UE_LOG(LogAbility, Error,
			TEXT("%s could not start %s. Locomotion=%s, Montage=%s, PlayRate=%g."),
			*GetNameSafe(Character),
			*GetNameSafe(GetClass()),
			*GetNameSafe(Locomotion),
			*GetNameSafe(AttackMontage),
			MontagePlayRate);

		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	MovementConstraintOwner = Locomotion;
	MovementConstraintHandle =
		Locomotion->AcquireMovementConstraint(this, MovementConstraint);

	if (!MovementConstraintHandle.IsValid())
	{
		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	if (!CommitAbility(SpecHandle, ActorInfo, ActivationInfo))
	{
		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
		this,
		FName(TEXT("BasicAttackMontage")),
		AttackMontage,
		MontagePlayRate,
		NAME_None,
		/* bStopWhenAbilityEnds */ true,
		/* AnimRootMotionTranslationScale */ 1.f,
		/* StartTimeSeconds */ 0.f,
		/* bAllowInterruptAfterBlendOut */ false);

	if (!MontageTask)
	{
		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	MontageTask->OnCompleted.AddDynamic(
		this, &ThisClass::HandleMontageCompleted);
	MontageTask->OnInterrupted.AddDynamic(
		this, &ThisClass::HandleMontageInterrupted);
	MontageTask->OnCancelled.AddDynamic(
		this, &ThisClass::HandleMontageCancelled);

	MontageTask->ReadyForActivation();

	if (!IsActive())
	{
		return;
	}

	UE_LOG(LogAbility, Log, TEXT("%s activated ability %s."),
		*GetNameSafe(Character),
		*GetNameSafe(GetClass()));
}

void UKhazanBasicAttackAbility::EndAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const bool bReplicateEndAbility,
	const bool bWasCancelled)
{
	if (!IsEndAbilityValid(SpecHandle, ActorInfo))
	{
		return;
	}

	if (UKhazanLocomotionComponent* Locomotion = MovementConstraintOwner.Get())
	{
		if (MovementConstraintHandle.IsValid())
		{
			Locomotion->ReleaseMovementConstraint(MovementConstraintHandle);
		}
	}

	MovementConstraintHandle.Reset();
	MovementConstraintOwner.Reset();
	MontageTask = nullptr;

	Super::EndAbility(
		SpecHandle,
		ActorInfo,
		ActivationInfo,
		bReplicateEndAbility,
		bWasCancelled);
}

void UKhazanBasicAttackAbility::HandleMontageCompleted()
{
	FinishAbility(false);
}

void UKhazanBasicAttackAbility::HandleMontageInterrupted()
{
	FinishAbility(true);
}

void UKhazanBasicAttackAbility::HandleMontageCancelled()
{
	FinishAbility(true);
}

void UKhazanBasicAttackAbility::FinishAbility(const bool bWasCancelled)
{
	const FGameplayAbilitySpecHandle SpecHandle =
		GetCurrentAbilitySpecHandle();
	const FGameplayAbilityActorInfo* ActorInfo = GetCurrentActorInfo();

	if (!ActorInfo || !IsEndAbilityValid(SpecHandle, ActorInfo))
	{
		return;
	}

	EndAbility(
		SpecHandle,
		ActorInfo,
		GetCurrentActivationInfo(),
		/* bReplicateEndAbility */ true,
		bWasCancelled);
}
```

`TriggerEventData`는 override signature의 일부이며 현재 activation이 event payload를 소비하지 않으므로 읽지 않는다. 별도 복사본이나 멤버로 보관하지 않는다.

#### `ActivateAbility()` 실행 순서

1. `ActorInfo->AvatarActor`를 현재 `AKhazanCharacter`로 확인한다. Spec이나 Ability CDO가 Character를 소유하는 것이 아니라 ASC의 현재 ActorInfo가 실행 대상을 제공한다.
2. Character가 공개한 LocomotionComponent를 얻는다. Ability가 CMC 값을 직접 덮어쓰지 않는다.
3. Montage pointer와 유한한 양수 PlayRate를 검사한다. 설정 실패는 canceled end로 닫혀 Spec 자체는 남는다.
4. `MovementConstraintOwner`에 발급자를 weak pointer로 기록하고, `Source=this`로 제약 한 건을 획득한다. Component 장부에는 Ability instance의 weak identity와 새 GUID가 기록된다.
5. handle이 유효하지 않으면 이후 일을 하지 않고 종료한다. `EndAbility()`가 owner pointer까지 초기화한다.
6. `CommitAbility()`를 호출한다. 현재 비용/쿨다운은 없지만 P2에서 이 경계가 실제 비용 확정 지점이 된다. 실패하면 이미 얻은 제약은 공통 cleanup에서 즉시 해제된다.
7. task의 `TaskInstanceName`은 디버그 식별자이고 GameplayTag가 아니다.
8. `StartSection=NAME_None`은 기본 section 시작, translation scale `1.0`은 항등 배율, start time `0.0`은 Montage 처음, `bStopWhenAbilityEnds=true`는 외부 취소 때 재생도 함께 정리한다.
9. 정상 완료는 `OnCompleted`, 다른 Montage가 덮거나 Ability가 취소되면 `OnInterrupted`, task가 시작 자체에 실패하거나 외부 task cancel을 받으면 `OnCancelled`로 들어온다.
10. delegate를 모두 연결한 뒤 `ReadyForActivation()`을 마지막에 호출한다. 이 호출 도중 Montage 시작 실패가 `OnCancelled`를 동기 발생시켜 Ability를 끝낼 수 있으므로, 다음 줄에서 `IsActive()`를 다시 확인한다.
11. 성공 로그는 task activation 뒤 Ability가 아직 active일 때만 남긴다. P1.4의 한 press당 로그 검증을 계속 사용할 수 있다.

`OnBlendOut`에는 종료 callback을 연결하지 않는다. UE 5.8.2 task 계약에서 정상 blend out 뒤 `OnCompleted`가 별도로 온다. Blend가 시작하자마자 constraint를 풀면 아직 전신 공격 pose가 남은 동안 다음 이동 정책이나 공격이 먼저 시작할 수 있다.

#### `EndAbility()` cleanup 순서

1. `IsEndAbilityValid()`가 중복 callback이나 이미 끝난 실행의 두 번째 종료를 거절한다.
2. `MovementConstraintOwner`가 아직 살아 있고 handle이 유효하면 정확히 그 Component에 정확히 그 GUID 한 건을 반납한다.
3. handle과 weak owner를 무조건 reset한다. `InstancedPerActor`의 다음 activation이 이전 실행 상태를 상속하지 않는다.
4. 지역 `MontageTask` pointer를 비운다.
5. `Super::EndAbility()`가 GAS active count, owned state, replication과 `ActiveTasks`를 정리한다. `PlayMontageAndWait`는 `bStopWhenAbilityEnds=true`이므로 취소 종료에서는 자신이 재생하던 Montage도 중지한다.

`EndAbility()`는 granted Spec을 삭제하지 않는다. 이번 변경 뒤에도 Spec은 ASC의 `ActivatableAbilities`에 남고, 실행 중에만 Spec active count와 Ability instance의 active 상태가 올라간다.

## P1.5-C — cold build와 Ability Blueprint 설정

### 1. C++ cold build

Editor와 Live Coding을 닫은 뒤 실행한다.

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
  KhazanEditor Win64 Development `
  '-Project=C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' `
  -WaitMutex -NoHotReloadFromIDE
```

UHT가 `EndAbility` override와 세 callback, 새 reflected property를 처리하고 `KhazanBasicAttackAbility.cpp`가 compile된 뒤 `Result: Succeeded`여야 한다.

### 2. 실제 설정을 가진 Ability Blueprint

native class는 실행 코드를 소유하고, 캐릭터별 콘텐츠 값은 Blueprint CDO에 둔다.

1. `/Game/Data/Ability/Khazan` 폴더를 만든다.
2. `Blueprint Class`에서 부모 `KhazanBasicAttackAbility`를 선택한다.
3. 이름을 `GA_BasicAttack_Khazan`으로 한다.
4. Event Graph에 `ActivateAbility`나 `EndAbility`를 새로 구현하지 않는다. native override를 그대로 사용한다.
5. Class Defaults → `Khazan|Attack|Animation`의 `Attack Montage`에 `AM_DAS_BasicAttack01`을 지정한다.
6. `Montage Play Rate=1.0`으로 둔다.
7. `Khazan|Attack|Locomotion`의 `Movement Constraint`를 펼친다.
8. `Max Allowed Gait=Run`, `Override Rotation Mode=false`, `Debug Name=P1.BasicAttack`으로 둔다.
9. Compile, Save한다.

`Max Allowed Gait=Run`은 원작 metadata 직접값이 아니다. Sprint를 요청한 상태에서 공격 실행 동안 resolved gait만 Run으로 제한되고, 종료 뒤 살아 있는 Sprint 요청이 다시 적용되는지 확인하기 위한 **P1 임시 튜닝값**이다. 이 값은 Ability CDO 한곳에 모여 있어 이후 원작 근거가 확보되면 교체할 수 있다. 회전 override는 근거가 없으므로 켜지 않는다.

### 3. CharacterDefinition의 grant class 교체

1. `/Game/Data/Character/DA_CharacterDefinition_Khazan`을 연다.
2. `Initial Ability Grants[0]`의 기존 native `KhazanBasicAttackAbility`를 `GA_BasicAttack_Khazan`으로 **교체**한다. 새 배열 원소를 추가하지 않는다.
3. 같은 원소의 `Input Tag=Input.Action.Attack`은 그대로 둔다.
4. 기존 LocomotionConfig 값은 건드리지 않는다.
5. 저장하고 PIE를 완전히 다시 시작한다.

grant된 `FGameplayAbilitySpec::Ability`는 이제 Blueprint generated class의 CDO를 가리키므로 `AttackMontage`와 `MovementConstraint` 설정을 읽을 수 있다. 이미 실행 중인 PIE의 기존 Spec class는 asset을 바꿔도 자동 교체되지 않으므로 새 PIE가 필요하다.

## P1.5-D — PIE 검증 순서

### 1. 기본 수명

1. `ShowDebug AbilitySystem`을 켜고 Ability category를 본다.
2. BasicAttack Spec이 정확히 하나이며 처음에는 inactive인지 확인한다.
3. Attack을 한 번 누른다.
4. `AM_DAS_BasicAttack01`이 `DefaultSlot`을 통해 한 번 재생되고 Ability가 그동안 active인지 본다.
5. 재생 중 Attack을 다시 눌러도 Montage가 처음부터 재시작되거나 task가 둘 생기지 않아야 한다.
6. 완료 뒤 Spec은 남고 active 표시는 내려가야 한다.
7. 다시 누르면 같은 Spec으로 새 실행 한 번이 시작돼야 한다.

Montage가 10.375초 내내 active라면 C++ 문제가 아니라 Montage segment를 전체 source 범위로 둔 것이다. P1.5-A로 돌아가 실제 표현 구간을 확인한다.

### 2. 이동 제약과 복구

1. 이동 입력과 Sprint 요청을 유지해 `ResolvedGait=Sprint` 상태를 만든다.
2. Attack을 누른다.
3. Ability active 동안 `ResolvedGait=Run`으로 제한되고 Sprint loop 대신 Run 선택이 보이는지 확인한다.
4. Montage 정상 완료 뒤 같은 Sprint 요청을 계속 유지했다면 `ResolvedGait=Sprint`로 돌아와야 한다.
5. Attack 중 이동 입력을 놓았다면 종료 뒤 남은 실제 intent에 따라 Idle/Stop으로 가야 하며 Ability가 Sprint를 강제로 복구하면 안 된다.
6. 회전 모드는 이번 제약으로 바뀌지 않아야 한다.

이 검증은 “공격 중 Run이 원작값”을 증명하지 않는다. 한 원인의 handle만 추가·제거돼 다른 원인과 raw intent가 보존되는지를 증명한다.

### 3. 외부 취소 cleanup

Attack Montage가 재생 중일 때 콘솔에서 실행한다.

```text
AbilitySystem.Ability.Cancel BasicAttack
```

UE 5.8.2의 이 command는 local player ASC에서 부분 이름이 맞는 현재 Ability를 취소한다. 매칭되지 않으면 먼저 다음 명령으로 실제 granted 이름을 확인하고 `GA_BasicAttack_Khazan` 또는 표시된 class 부분 문자열을 사용한다.

```text
AbilitySystem.Ability.ListGranted
```

취소 직후 다음이 모두 성립해야 한다.

- Montage가 중지된다.
- Ability가 inactive가 된다.
- `MovementConstraintHandle`이 reset된다.
- Sprint 요청을 유지했다면 resolved gait가 다시 Sprint로 계산된다.
- 다음 Attack press가 정상적으로 새 실행을 만든다.

이 경로에서 Ability 취소 delegate를 받은 `PlayMontageAndWait`는 `OnInterrupted`를 발생시키고, callback이 `FinishAbility(true)`로 들어간다. `DestroyActiveState()`도 active Ability를 취소하므로 같은 cleanup 계약을 사용한다.

### 4. 설정 실패와 EndPlay

1. 저장하지 않은 시험으로 `GA_BasicAttack_Khazan`의 `Attack Montage`를 잠시 비우고 PIE에서 Attack을 누른다.
2. `LogAbility`에 `could not start` 오류가 한 번 나오고 Ability가 active로 남지 않는지 확인한다.
3. PIE를 끝내고 값을 원상복구하며 저장하지 않은 시험 변경을 버린다.
4. 정상 Montage를 다시 지정한 PIE에서 공격 도중 PIE를 종료한다.
5. crash/assert가 없고 다음 PIE에서 처음부터 Sprint/Attack이 정상인지 확인한다.

Montage가 다른 Montage에 의해 실제로 덮이는 `OnInterrupted` runtime 시험은 두 번째 전신 action이 생겼을 때 다시 수행한다. 현재 P1.5에서는 외부 Ability cancel이 동일한 interrupted cleanup 경로를 검증하며, `OnCancelled`의 task-start 실패 binding은 Source/API 대조 범위다.

## P1.5 합격 기준

1. C++ cold build가 `Result: Succeeded`다.
2. Definition에 `GA_BasicAttack_Khazan + Input.Action.Attack` 한 entry만 있다.
3. ASC에 BasicAttack Spec이 한 개만 존재한다.
4. 한 press가 한 Montage task를 만들고 hold/active 중 추가 press가 재시작을 만들지 않는다.
5. 정상 완료 뒤 Ability active 상태와 실행별 constraint가 모두 사라진다.
6. console cancel 뒤에도 Montage, Ability, constraint가 모두 정리되고 재활성화할 수 있다.
7. Sprint raw 요청은 공격 중 보존되고 임시 Run cap만 적용됐다가 종료 뒤 복구된다.
8. PIE 종료에서 crash/assert 또는 다음 PIE로 이어지는 stale 상태가 없다.
9. 기존 Walk/Run/Sprint, 발별 Walk/Run Stop, 단일 Sprint Stop에 새 회귀가 없다.

이 기준을 통과하면 다음은 P1.6이다. 이미 `Started`로 바뀐 Jump 입력을 `UKhazanJumpAbility`의 grant/activation으로 옮기고, `Completed`와 `Canceled`를 GAS의 pressed/released 수명에 연결한 뒤 Controller의 직접 `Jump()` 우회를 제거한다.

## 2026-09-16 — P1.5 원본 길이 확인에 따른 절차 보정

- 이 절은 앞의 P1.5-A에서 현재 uasset의 공통 `10.375 s` timeline을 눈으로 찾아 Montage segment만 제한하라고 한 절차를 보정한다. 서로 다른 원본 PSA 길이와 모두 같은 uasset 길이가 불일치하므로 `10.375 s`가 원작 동작 길이가 아니라는 점은 확인됐다. 공통 FBX timeline 또는 import 범위가 포함됐다는 것은 현재 근거의 원인 판단이며, 정확한 원인은 FBX take/frame range를 열어 추가 확인한다.
- 추출 원본 PSA 기준 `FastAtk01_M1`은 107 samples, 30fps에서 `106 / 30 = 3.5333 s`다. `FastAtk02`는 69 samples/`2.2667 s`, `FastAtk02_Loop`는 61 samples/`2.0 s`, `FastAtk02_M1`은 102 samples/`3.3667 s`로 서로 다른 원본이다. 전체 대조표와 이름 판정은 [Animation 현행 정본의 2026-09-16 절](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md#2026-09-16--dualaxesword-공격-애니메이션-이름과-원본-psa-확인)을 따른다.
- 따라서 P1.5-A에서는 먼저 같은 이름의 FBX take/frame range를 원본 PSA의 sample 범위와 맞춰 AnimSequence를 정상 길이로 임포트한 뒤 pose를 확인한다. 현재 잘못 늘어난 timeline에서 임의 구간을 골라 확정본으로 삼지 않는다. hit window는 여전히 P3의 별도 계약이다.
- `Loop` 접미사는 반복 재생 명령이 아니다. P1의 단발 공격 Montage는 검증된 Sequence를 segment `Loop Count=1`로 재생한다. 이름만으로 `FastAtk02_Loop`를 2타에 선택하거나 Montage loop/section self-link를 만들지 않는다.
- `M1`의 정확한 사내 뜻은 미확인이고 root-motion 표식이라는 근거도 없다. P1의 후보 `FastAtk01_M1`은 현재 확인된 유일한 FastAtk01 원본이므로 이름이 아니라 정상 import 뒤 실제 pose와 공격 단계 적합성을 보고 채택한다.
- 이번 보정은 설명과 문서 기록이며 C++, Blueprint, Montage, Animation Sequence를 직접 수정하거나 build/PIE하지 않았다.

<a id="p1-5-dilation-integrated-20260916"></a>
## 2026-09-16 — P1.5 원작 Dilation을 포함한 최신 적용 절차

이 절이 앞의 P1.5-A asset 생성 절차를 대체한다. P1.5-B 이후의 `PlayMontageAndWait + 실행별 movement constraint + EndAbility cleanup` 구조는 유지한다.

### 왜 고정 RateScale로 해결하지 않는가

원작 `AC_Kazan_DualAxeSword_Com_WeakAtk01`은 `FastAtk01_M1`의 `0–3.53 s`를 segment rate `1.0`, loop 1회로 사용한다. 별도 RateScale override는 없고, 213-point `T_Original → T_Dilation` table이 실제 길이를 `3.4326434 s`로 바꾼다. 인접 table의 source 진행률은 약 `0.911179–1.417051x`이고 전체 평균은 약 `1.02836199x`다. 평균을 Montage Play Rate에 넣으면 총 길이는 맞아도 초반 감속과 중간 가속은 사라진다.

UE 5.8의 Montage Time Stretch Curve는 non-default global play rate를 curve weight로 분배하는 별도 기능이다. 음수 값을 포함한 원작 raw Dilation curve를 그대로 복사하는 호환 필드가 아니므로 이번 수직 절편에서는 사용하지 않는다. Ability가 Tick하며 `Montage_SetPlayRate()`를 바꾸는 구현도 새 시간 상태와 cancel/network 경계를 만들기 때문에 사용하지 않는다.

### P1.5-0 — 원작 시간축이 bake된 playback Sequence

생성할 최종 runtime asset을 다음처럼 분리한다.

```text
/Game/_Art/Kazan/Animation/Combat/Runtime/DualAxeSword/
    A_DAS_WeakAtk01_Playback
    AM_DAS_BasicAttack01
```

`A_DAS_WeakAtk01_Playback`은 잘못 늘어난 현재 10.375초 FBX import를 crop한 자산이 아니다. 원본 `FastAtk01_M1` pose와 `WeakAtk01` Composite metadata로 새로 만든 파생 재생 자산이다.

1. `T_Dilation=0–3.4326434 s`를 균일하게 표본화한다.
2. 213-point table의 역함수를 구간 선형 보간해 각 표본의 `T_Original`을 구한다.
3. source segment `0–3.53 s`의 pose를 해당 위치에서 평가한다. translation/scale은 선형, quaternion은 같은 회전 반구의 normalized linear interpolation을 사용한다.
4. 목표 60 Hz에서 interval은 `round(3.4326434 × 60)=206`, sample은 207개다. 정확한 길이를 유지할 data-model frame rate는 `5110687/85161 ≈ 60.01205951 fps`다.
5. 출력 Sequence의 `Rate Scale=1.0`, `Enable Root Motion=false`, `Force Root Lock=true`로 둔다. 앞의 두 값 중 root 설정은 원작값을 그대로 복사한 것이 아니라 P1.5의 CMC 구동/무 root-motion 정책이다. 원작 source의 직접값은 `Enable Root Motion=true`, `Force Root Lock=true`다.
6. 출력 asset metadata에는 최소한 원작 Composite package, source Sequence package, `PlaybackDerivation=CompositeDilationBake`, source/composite/dilation 길이, 207 sample과 frame-rate 분수를 기록한다.

현재 저장된 계산 근거는 `Saved/ImportReports/Khazan_DAS_WeakAttack_Timing_20260916.json`이다. 기존 Enemy pipeline의 `Scripts/Enemies/prepare_big_bear_animation_timing.py`가 같은 table 역변환/pose interpolation을, `Scripts/Enemies/import_big_bear_animations.py`가 UE `IAnimationDataController`를 통한 sequence 작성을 이미 사용한다. Player용 도구를 작성할 때 이 두 계약을 좁게 재사용하고 BigBear 경로나 manifest 자체를 수정하지 않는다.

playback Sequence를 연 뒤 다음을 먼저 검사한다.

- data model: 207 keys, 206 frames, `5110687/85161` frame rate
- Play Length: 허용 오차 `1e-5 s` 이내에서 `3.4326434 s`
- Rate Scale: `1.0`
- 첫/마지막 pose: source `0.0/3.53 s`와 일치
- 재생 위치 약 `0.4 s`: source pose 약 `0.467117 s`와 일치
- root motion 이동이 capsule/mesh를 밀지 않음

이 검사를 통과하기 전 Montage나 Ability에 임시 평균 배율을 넣지 않는다.

### P1.5-1 — Montage

1. `A_DAS_WeakAtk01_Playback`에서 AnimMontage를 만들어 `AM_DAS_BasicAttack01`로 저장한다.
2. Slot은 Main ABP가 합성하는 `DefaultGroup.DefaultSlot`을 사용한다.
3. segment `Anim Start Time=0`, `Anim End Time=3.4326434`, `Anim Play Rate=1.0`, `Loop Count=1`로 둔다.
4. section self-link나 loop를 추가하지 않는다.
5. Blend In/Out은 원작 확정값을 아직 확보하지 못했으므로 Editor 기본값을 **임시 엔진값**으로 기록한다. P1.5에서는 Blend Out 시작이 아니라 `OnCompleted`에서 Ability를 정상 종료한다.
6. 원작 Composite notify 45개는 이 Montage에 일괄 복사하지 않는다. P1.5의 montage는 포즈와 Ability 수명만 검증한다.

### P1.5-2 — Ability Source

`KhazanBasicAttackAbility.h/.cpp`에는 앞 P1.5-B의 코드를 적용한다. 최신 timing 계약에서 달라지는 설정은 다음뿐이다.

- `AttackMontage = AM_DAS_BasicAttack01`
- `MontagePlayRate = 1.0`
- `CreatePlayMontageAndWaitProxy(... Rate=MontagePlayRate ...)`는 실행 중 바뀌지 않는다.
- Character, ASC, Controller, AnimInstance에 Dilation curve, track position, Tick 함수를 추가하지 않는다.

실행 순서는 `입력 → 기존 granted Spec 활성화 → constraint 발급 → CommitAbility → PlayMontageAndWait → completed/interrupted/cancelled → EndAbility → 정확한 constraint handle 반환`이다. `EndAbility()`는 실행을 끝내지만 Spec을 ASC에서 제거하지 않는다.

`MovementConstraint`의 `MaxAllowedGait=Run`, rotation override off는 원작 전투 수치가 아니라 기존 P1.5 handle cleanup을 눈으로 확인하기 위한 임시 구조 시험값이다. Dilation bake와 별개로 관리한다.

### P1.5-3 — 적용·검증 순서

1. playback Sequence만 만든 뒤 Editor preview에서 길이, key 수, 세 표본 pose를 검사한다.
2. Montage를 만들고 `DefaultSlot`, 1회 재생, 세 배율이 모두 `1.0`인지 확인한다.
3. 앞 P1.5-B의 C++를 적용하고 Editor를 닫은 상태에서 cold build한다.
4. `GA_BasicAttack_Khazan` CDO에 Montage와 movement constraint를 설정하고 Definition의 기존 native grant entry를 그 Blueprint class로 교체한다. entry를 추가해 Spec을 중복 grant하지 않는다.
5. 새 PIE에서 Attack 한 번이 약 `3.4326434 s + Montage blend 완료 구간` 동안 active인지 본다. pose source가 끝에 도달하는 시각과 task `OnCompleted` 시각은 blend 설정 때문에 구분한다.
6. active 중 추가 press가 두 번째 task/constraint를 만들지 않는지 확인한다.
7. 정상 완료, 외부 Ability cancel, PIE 종료에서 Montage와 정확한 constraint handle이 정리되고 Spec 한 개는 ASC에 inactive로 남는지 확인한다.
8. Sprint raw intent가 공격 중 보존되고 임시 Run cap만 적용됐다가 종료 후 복구되는지 확인한다.
9. 기존 Walk/Run/Sprint/Stop과 다음 PIE에 stale 상태가 없는지 확인한다.

### 현재 적용 경계

2026-09-16 현재 실제 `KhazanBasicAttackAbility.cpp`는 `CommitAbility()` 뒤 즉시 `EndAbility()`하는 P1.3 구현이다. playback Sequence, Montage, P1.5 Ability Source, Ability Blueprint는 아직 적용·빌드·PIE되지 않았다. 이번 절은 원작 metadata 조사로 이전 asset 절차를 교정한 사용자 적용 안내다.

<a id="p1-5-root-motion-combo-correction-20260916"></a>
## 2026-09-16 — P1.5 Root Motion 필수·콤보 전제 최종 보정

이 절이 앞의 P1.5 자산 이름, `Enable Root Motion=false`, 단발 공격 전제를 대체한다. 앞 P1.5-B의 `PlayMontageAndWait + movement constraint handle + EndAbility cleanup` 코드는 아래에서 명시한 section과 Root Motion 설정만 반영해 계속 사용한다.

### 1. 먼저 책임을 고정한다

| 책임 | 소유자 | 이번에 두지 않는 상태 |
| --- | --- | --- |
| Input Tag와 granted Spec exact match, inactive Spec 활성화 | `UKhazanAbilitySystemComponent` | 재생률, Montage position, combo index |
| 한 콤보 실행의 task/constraint/정상·취소 수명 | `UKhazanBasicAttackAbility` | 영속 해금 원본, 전역 입력 queue |
| 원작 Dilation이 반영된 포즈와 root delta | 파생 playback `UAnimSequence` | gameplay 승인/비용 |
| 1–5타 시간 배치와 section | 하나의 `UAnimMontage` | 공격 가능 여부의 최종 판단 |
| 미래의 입력창/타격창 시각 알림 | AnimNotify 또는 Gameplay Event | 재생률 Tick, ASC 상태 직접 변경 |
| 추출된 root delta와 collision을 사용한 실제 이동 | `UCharacterMovementComponent` | combo 선택 |
| raw intent와 여러 원인의 gait/rotation 제약 합성 | `UKhazanLocomotionComponent` | 공격 root delta 생성 |

`PlayMontageAndWait`가 내부에서 ASC의 Montage API를 쓰는 것은 GAS가 활성 Montage와 cancel/replication을 추적하기 위해서다. 이 호출 경로 때문에 ASC가 애니메이션 속도나 Root Motion을 계산하는 것은 아니다.

Float Curve를 읽는 `AnimNotifyState::NotifyTick()`에서 `Montage_SetPlayRate()`를 반복 호출하지 않는다. NotifyState 자신이 진행하는 시간축을 다시 바꾸는 순환 의존이 생기고, 큰 frame delta·section 전이·interrupt에서 표본이나 End가 빠질 수 있으며, networking/cancel 상태도 하나 더 생긴다. 이번 원작에는 이미 `T_Original → T_Dilation` table이 있으므로 재생 전에 파생 Sequence로 bake하는 편이 더 단순하고 결정적이다. NotifyState는 이후 combo window나 hit window처럼 **구간의 의미**만 알린다.

원작 Skill Blueprint의 `Step1`–`Step6`은 `AnimPlayRate=1.0`, `AnimLoopCount=1`, `bApplyAttackSpeed=true`다. 따라서 두 종류의 속도를 구분한다. Composite Dilation은 클립 내부 위치별 기본 timing이므로 playback Sequence에 bake한다. 미래 Attack Speed attribute/effect는 그 결과 전체에 곱할 수 있는 gameplay 배율이며, 실제 AttributeSet이 생기는 단계에서 Ability가 시작 시점 값을 읽어 task rate에 전달한다. P1.5에는 해당 attribute가 없으므로 task rate는 `1.0`이다. 공격 도중 값이 변할 때 즉시 재배속할지는 원작 근거를 확인하기 전까지 구현하지 않는다.

### 2. 1–5타 선정 결과

원작 `SB_Kazan_DualAxeSword_Com_WeakAtk`와 각 Composite의 segment를 함께 대조한 결과다.

| 공격 | 원작 Composite | 사용할 source | 판정 |
| --- | --- | --- | --- |
| 1타 | `WeakAtk01` | `CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1` | 선정 그대로 맞음 |
| 2타 | `WeakAtk02` | `CA_P_Kazan_DualAxeSword_Off_FastAtk02_M1` | 기존 선정의 `_Loop`를 `_M1`로 교체 |
| 3타 | `WeakAtk03` | `CA_P_Kazan_DualAxeSword_Off_FastAtk03_M1` | 선정 그대로 맞음 |
| 4타 | `WeakAtk04` | `CA_P_Kazan_DualAxeSword_Off_FastAtk04_M1` | 선정 그대로 맞음 |
| 해금 5타 | `WeakAtk05` | `CA_P_Kazan_DualAxeSword_Com_WeakAtk05` | 선정 그대로 맞음 |

`FastAtk02_Loop`는 `WeakAtk02_Loop` Composite에만 연결된다. 이 Composite는 `2.0 s`, 고정 `1.0x`, 별도 `Absorb` 입력 notify를 가지며 표준 WeakAtk Skill Blueprint의 `SubStateInfos`에는 참조되지 않는다. 정확한 별도 진입 조건은 아직 확정하지 않았으므로 삭제하지 말고 미래 특수 분기 후보로 보존한다.

원작 단계 번호는 공격 번호와 완전히 같지 않다. `Step1/2/3/4`가 기본 1–4타이고, `Step4`는 `SP_Kazan_DualAxeSword_Flow_HyperMaster` 활성 시 `SpecialSubStateTag=Step5`를 사용한다. `Step5`도 4타 `WeakAtk04`를 재생하지만 press를 `Step6`으로 보내며, `Step6`이 실제 5타 `WeakAtk05`다. 프로젝트에서는 영속 Progression이 해금 사실을 소유하고, Ability가 그 읽기 결과로 4→5 전이를 허용한다. 해금 원본 시스템이 아직 없으므로 P1.5에서 임의 bool/tag를 먼저 만들지 않는다.

### 3. Root Motion과 Dilation을 함께 bake한다

1타의 기존 `T_Dilation → T_Original` 역변환, 207 samples, `5110687/85161 fps`, `3.4326434 s` 계약은 유지한다. 달라지는 핵심은 **Root 트랙도 다른 모든 bone과 같은 시각으로 재표본화**한다는 점이다.

```text
output time t
  -> saved Dilation table을 역보간하여 source time s를 구함
  -> source의 모든 bone pose를 s에서 평가
  -> Root translation/rotation도 같은 s에서 평가
  -> output AnimSequence의 같은 frame에 기록
```

이 방식이면 준비 동작의 감속·타격 구간의 가속과 root 이동 속도가 같은 시간축을 사용한다. 몸만 retime하고 Root를 원래 균일 속도로 두거나, Root를 제거한 뒤 별도 CMC impulse를 넣지 않는다.

파생 Sequence `A_DAS_WeakAtk01_Playback` 설정은 다음과 같다.

- `Rate Scale=1.0`
- `Enable Root Motion=true`
- `Force Root Lock=true`
- `Root Motion Root Lock=Ref Pose`: 원작 metadata에는 해당 enum이 직렬화되지 않았다. 이는 UE 5.8의 engine 기본값을 쓰는 **임시 엔진값**이며 첫 frame/원점 튐과 추출 delta를 검사한 뒤 유지 여부를 판정한다.
- root track을 삭제하거나 첫 frame 값으로 평탄화하지 않음

원작 1–4타 source package는 `bEnableRootMotion=true`, `bForceRootLock=true`를 직접 직렬화한다. 5타 package flag는 현재 표적 metadata에 없지만 PSA의 `Root` 트랙은 시작→끝 약 `208.66098 cm` 변위를 가진다. 사용자 확정 정책에 따라 5타 파생 자산도 `Enable Root Motion=true`로 만든다.

`Force Root Lock=true`는 이동을 끄지 않는다. 엔진은 Root Motion을 추출한 뒤 스켈레탈 포즈의 root 기준을 고정하고, 추출한 delta는 CharacterMovementComponent가 capsule 이동에 사용한다. 이동을 0으로 만드는 값은 task의 `AnimRootMotionTranslationScale=0`인데, 이 프로젝트에서는 `1.0`을 유지한다.

### 4. 콤보 Montage 골격을 처음부터 만든다

단발 이름 `AM_DAS_BasicAttack01` 대신 다음 자산을 만든다.

```text
/Game/_Art/Kazan/Animation/Combat/Runtime/DualAxeSword/
    A_DAS_WeakAtk01_Playback
    AM_DAS_WeakAttackCombo
```

P1.5에서는 Montage에 1타 sequence만 넣어도 된다. 중요한 것은 미래 콤보와 같은 Montage/section 계약을 지금 사용하는 것이다.

1. `A_DAS_WeakAtk01_Playback`에서 AnimMontage를 만들고 `AM_DAS_WeakAttackCombo`로 저장한다.
2. Slot은 Main ABP가 이미 합성하는 `DefaultGroup.DefaultSlot`이다.
3. 첫 section 이름을 `Attack01`로 바꾸고 section 시작을 montage `0.0 s`에 둔다.
4. `Attack01`의 `Next Section` 연결은 `None`으로 둔다. 입력 없이 2타로 자동 진행하면 안 된다.
5. segment는 playback Sequence 전체, `Anim Play Rate=1.0`, `Loop Count=1`이다.
6. Montage 자체의 Rate Scale도 `1.0`이다.
7. Blend In/Out은 원작 확정값이 아직 없으므로 생성된 Editor 기본값을 **임시 엔진값**으로 기록한다.
8. Main Animation Blueprint Class Defaults의 Root Motion Mode가 `Root Motion from Montages Only`인지 확인한다. 스킬은 Montage로만 재생하므로 이 모드가 root delta를 CMC에 전달하면서 locomotion graph의 root를 섞지 않는 현재 계약이다.
9. 원작 notify를 일괄 복사하지 않는다. P1.5는 포즈 시간축, root 이동, Ability 수명만 검증한다.

P6에서는 같은 Montage 뒤에 `A_DAS_WeakAtk02_Playback`부터 `05`까지 순서대로 배치하고 section을 `Attack02`–`Attack05`로 만든다. section의 기본 Next는 모두 `None`으로 유지하고, 활성 Ability가 유효 입력을 소비했을 때 GAS의 replication-aware `ASC->CurrentMontageSetNextSectionName(Current, Next)`를 호출한다. 다음 section을 **결정**하는 주체는 Ability이고 ASC는 현재 Montage 명령의 전달·복제를 수행한다. 이렇게 하면 버튼을 누르지 않았을 때 현재 타격 끝에서 Montage와 Ability가 정상 종료된다.

### 5. P1.5 Ability 코드 보정

앞 P1.5-B 헤더의 편집 가능한 `MontagePlayRate` property는 제거한다. Dilation이 bake된 자산의 기본 배율은 항상 항등값이며, CDO에서 다시 튜닝하면 원작 시간축을 이중 변경할 수 있기 때문이다. `ActivateAbility()`의 유효성 검사는 `IsValid(AttackMontage)`만 확인하고 오류 로그에서도 PlayRate 항목을 제거한다. 미래 Attack Speed attribute가 실제 생기면 Ability가 activation 시점의 gameplay 배율을 지역값으로 계산해 task에 넘긴다.

```cpp
if (!Locomotion || !IsValid(AttackMontage))
{
	UE_LOG(LogAbility, Error,
		TEXT("%s could not start %s. Locomotion=%s, Montage=%s."),
		*GetNameSafe(Character),
		*GetNameSafe(GetClass()),
		*GetNameSafe(Locomotion),
		*GetNameSafe(AttackMontage));

	EndAbility(SpecHandle, ActorInfo, ActivationInfo,
		/* bReplicateEndAbility */ true,
		/* bWasCancelled */ true);
	return;
}
```

`AttackMontage`에는 `AM_DAS_WeakAttackCombo`를 지정하고, task의 `StartSection`을 명시적으로 `Attack01`로 바꾼다.

```cpp
MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
	this,
	FName(TEXT("BasicAttackComboMontage")),
	AttackMontage,
	/* Rate */ 1.f,
	FName(TEXT("Attack01")),
	/* bStopWhenAbilityEnds */ true,
	/* AnimRootMotionTranslationScale */ 1.f,
	/* StartTimeSeconds */ 0.f,
	/* bAllowInterruptAfterBlendOut */ false);
```

- task `Rate=1.0`: Dilation은 이미 Sequence에 bake됐으므로 다시 배속하지 않는다.
- `StartSection=Attack01`: 나중에 section이 다섯 개가 되어도 첫 활성화 위치가 바뀌지 않는다.
- `AnimRootMotionTranslationScale=1.0`: authored root delta를 항등 배율로 사용한다.
- `bStopWhenAbilityEnds=true`: 외부 취소 때 Montage와 root-motion 발생도 함께 끝낸다.

현재 `MovementConstraint`는 root 이동의 대체물이 아니다. LocomotionComponent가 gait/rotation 정책과 raw intent를 보존하고, Montage가 재생되는 동안 CMC가 animation root motion을 우선 소비한다. 공격 종료 뒤에는 남아 있던 raw intent와 남은 제약들로 locomotion policy를 다시 계산한다.

P1.5에서는 ASC 코드를 바꾸지 않는다. 활성 중의 두 번째 Attack press는 현재 adapter에서 재활성화되지 않으며 무시되는 것이 이번 checkpoint의 정상 결과다. 이 덕분에 Root Motion·task·cleanup 문제와 combo input 문제를 섞지 않고 검증한다.

### 6. P6에서 추가할 입력 흐름 — 지금 선행 구현하지 않음

```text
Attack press
  -> ASC가 Input.Action.Attack Spec을 찾음
  -> Spec inactive: TryActivateAbility
  -> Spec active: AbilitySpecInputPressed + GAS generic InputPressed event
  -> 활성 BasicAttack Ability의 지역 buffer가 press를 기록
  -> 현재 section의 combo window가 열리면 다음 section 예약
  -> 4타에서는 Progression의 해금 사실을 읽어 Attack05 허용 여부 결정
```

ASC 확장은 모든 Ability가 쓸 수 있는 pressed/released 전달까지만 한다. `CurrentComboStep`, `bInputBuffered`, `bComboWindowOpen`, `Attack05` 해금 여부를 ASC에 넣지 않는다. `UAbilityTask_WaitInputPress`는 한 번의 press 뒤 끝나므로 Ability가 다음 입력을 기다릴 때 새 task를 만들고, `EndAbility()`에서 지역 buffer/window/task pointer를 reset한다.

Combo window는 미래 `AnimNotifyState` 또는 두 개의 의미 notify가 Gameplay Event를 보내는 방식으로 연결할 수 있다. Notify Begin/End가 gameplay 상태의 최종 cleanup은 아니다. interrupt, cancel, death, EndPlay에서는 Ability의 `EndAbility()`가 창이 닫힌 상태로 reset해야 한다.

### 7. P1.5 적용·검증 순서

1. `A_DAS_WeakAtk01_Playback`만 먼저 생성한다. 207 samples, `3.4326434 s`, 모든 track과 Root 포함, 세 root 설정을 확인한다.
2. Animation Editor에서 root-motion 처리 표시를 켜고 capsule/preview root의 진행 방향, 첫 frame 튐, 끝 위치를 본다. source PSA의 root delta 계산값 약 `131.546982 cm`와 방향·규모가 맞는지 비교하되, skeleton/import 좌표 변환 전후 축 표기는 구분한다.
3. `AM_DAS_WeakAttackCombo`를 만들고 `Attack01`, Next=None, Slot, 세 재생 배율 `1.0`을 확인한다.
4. 앞 P1.5-B Ability 코드를 적용하되 Montage와 StartSection을 위 값으로 사용한다.
5. Editor를 닫고 UE 5.8.2 cold build를 실행한다.
6. `GA_BasicAttack_Khazan`의 `AttackMontage`에 새 Montage를 지정하고 CharacterDefinition의 기존 한 grant entry를 이 Blueprint class로 **교체**한다. entry를 추가하지 않는다.
7. 새 PIE에서 한 press가 한 Ability/task를 만들고 capsule이 root track을 따라 전진하는지 확인한다. Mesh만 앞으로 빠졌다가 되돌아오면 Root Motion Mode, Sequence Enable Root Motion, Montage Slot을 다시 본다.
8. 공격 중 이동 입력을 유지해도 CMC locomotion 속도가 root delta에 중복 가산되지 않는지 본다. 종료 뒤에는 보존된 raw intent에 따라 정상 locomotion이 재개돼야 한다.
9. 벽을 향해 공격해 capsule이 CMC collision에서 멈추는지 확인한다. Mesh가 벽을 통과한 뒤 capsule로 복귀하는 결과는 실패다.
10. 정상 완료와 console cancel 각각에서 Montage, animation root motion, Ability active count, 정확한 movement constraint handle이 모두 정리되는지 확인한다. granted Spec 한 개는 inactive로 ASC에 남아야 한다.
11. Attack을 빠르게 두 번 눌러 P1.5에서는 두 번째 task/section 전이가 생기지 않는지 확인한다. 이 결과를 통과한 뒤 P6의 active-Spec pressed 전달을 추가한다.
12. 기존 Walk/Run/Sprint/Stop과 다음 PIE에 stale 이동·Montage·constraint가 없는지 확인한다.

### 8. 현재 적용 경계

이번 정정은 원작 metadata/PSA와 현재 Source 대조 및 사용자 적용 절차다. 실제 `KhazanBasicAttackAbility.cpp`는 여전히 `CommitAbility()` 직후 `EndAbility()`하는 P1.3 구현이며, playback Sequence, combo Montage, Ability Blueprint, Root Motion runtime, cold build, PIE는 아직 적용·검증되지 않았다.

<a id="p1-weak-attack-naming-correction-20260916"></a>
# 2026-09-16 — 최신 명칭 정정: BasicAttack이 아니라 WeakAttack

앞 절들의 `BasicAttack`은 원작 `WeakAtk01`–`WeakAtk05`를 가리킨 임시 이름이었다. 아래 표가 이후 모든 소스·에셋 절차를 대체한다.

| 과거 표기 | 이후 사용할 표기 |
| --- | --- |
| `UKhazanBasicAttackAbility` | `UKhazanWeakAttackAbility` |
| `KhazanBasicAttackAbility.h/.cpp` | `KhazanWeakAttackAbility.h/.cpp` |
| `GA_BasicAttack_Khazan` | `GA_WeakAttack_Khazan` |
| `AM_DAS_BasicAttack01` | 사용하지 않음 |
| `AM_DAS_WeakAttackCombo` | 유지 |
| `BasicAttackComboMontage` task instance name | `WeakAttackComboMontage` |
| “BasicAttack Spec/instance” | “WeakAttack Spec/instance” |

`Input.Action.Attack`은 Controller가 공격 버튼 의도를 전달하는 입력 태그이므로 유지한다. 이 태그와 행동 class 이름은 다른 계층의 이름이다. 현재 별도 StrongAttack 입력 계약이 없으므로 사용되지 않는 `Input.Action.WeakAttack` 태그를 선행 생성하지 않는다.

실제 Source에는 다음 변경이 적용됐다.

```text
Source/Khazan/Ability/KhazanWeakAttackAbility.h
Source/Khazan/Ability/KhazanWeakAttackAbility.cpp
    UKhazanWeakAttackAbility
    InstancingPolicy = InstancedPerActor
    NetExecutionPolicy = ServerOnly
    현재 실행 본문 = CommitAbility 후 즉시 EndAbility하는 P1.3 상태
```

Definition asset에는 옛 `/Script/Khazan.KhazanBasicAttackAbility` 문자열이 저장돼 있었으므로 `DefaultEngine.ini`에 class redirect를 추가했다. binary `.uasset` 문자열을 직접 편집하지 않는다. 새 C++ module을 빌드한 뒤 Editor에서 `DA_CharacterDefinition_Khazan`을 열어 `Initial Ability Grants[0].Ability Class`가 `KhazanWeakAttackAbility`로 해석되는지 확인하고 저장한다. 기존 원소를 유지하며 중복 grant 원소를 추가하지 않는다.

P1.5 AbilityTask 코드를 적용할 때는 task instance name도 다음처럼 쓴다.

```cpp
MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
	this,
	FName(TEXT("WeakAttackComboMontage")),
	AttackMontage,
	/* Rate */ 1.f,
	FName(TEXT("Attack01")),
	/* bStopWhenAbilityEnds */ true,
	/* AnimRootMotionTranslationScale */ 1.f,
	/* StartTimeSeconds */ 0.f,
	/* bAllowInterruptAfterBlendOut */ false);
```

현재 직접 적용된 범위는 native rename, file rename, class redirect, `ServerOnly` 명시까지다. 아직 `GA_WeakAttack_Khazan`, playback Sequence, combo Montage, montage task 수명, build와 PIE는 적용 또는 검증되지 않았다. 다음 구현은 P1.5-0의 Dilation·Root track bake부터 시작한다.

<a id="p1-5-production-revision-20260916"></a>
# 2026-09-16 — P1.5 최신 제품 구현 절차

이 절이 앞 P1.5 코드의 임시 movement constraint, `bAllowInterruptAfterBlendOut=false`, 과거 `BasicAttack` 표기를 대체한다. 소스와 에셋을 실제 적용한 완료 기록이 아니라 사용자가 순서대로 적용할 최신 절차다.

## 1. 이번 checkpoint의 정확한 결과

한 번의 `Input.Action.Attack`으로 ASC에 이미 grant된 WeakAttack Spec이 활성화되고, 하나의 `UKhazanWeakAttackAbility` instance가 `AM_DAS_WeakAttackCombo`의 `Attack01`만 재생한다. 재생 pose와 root delta에는 원작 Composite Dilation이 미리 bake돼 있다. 정상 끝, Montage interrupt, task cancel·시작 실패는 모두 Ability 종료로 모이며 Spec은 제거되지 않고 ASC에 inactive 상태로 남는다.

이번 checkpoint에는 2–5타 section, active-Spec 두 번째 입력 전달, combo buffer/window, hit/damage/stamina, 해금 상태, 공격 전용 locomotion constraint를 넣지 않는다. 두 번째 입력이 무시되는 것은 P1.5의 의도된 경계이고 P6에서 같은 활성 Ability로 전달한다.

P6에서 실제 2–5타를 추가하기 전에는 원작 `AnimBlendAlpha`의 소비 의미를 확인한다. section 경계가 원작의 단계별 cross-fade를 재현하지 못하면 한 Ability가 콤보 전체 실행을 소유하는 계약은 유지하되, 각 타의 Montage/task를 계획된 handoff로 잇는 표현 구조도 비교한다. P1.5는 1타만 재생하므로 이 미확인 항목이 현재 Root Motion·수명 통합을 막지는 않는다.

## 2. 먼저 native rename을 안정화한다

1. Editor와 Live Coding을 완전히 종료한다.
2. `KhazanEditor Win64 Development`를 `-NoHotReloadFromIDE`로 cold build한다.
3. Editor에서 `/Game/Data/Character/DA_CharacterDefinition_Khazan`을 열고 기존 `Initial Ability Grants[0]`의 class가 `KhazanWeakAttackAbility`로 해석되는지 확인해 저장한다. `Input.Action.Attack`은 유지하고 새 grant 원소를 추가하지 않는다.
4. 이 시점 PIE의 한 번 입력은 아직 `CommitAbility()` 직후 끝난다. WeakAttack 활성 로그 한 번과 inactive Spec 한 개가 보이면 rename checkpoint의 정상 결과다.

class가 `None`이면 P1.5로 넘어가지 않는다. module build 결과, `DefaultEngine.ini`의 class redirect, Editor load log를 확인하고 기존 원소의 class만 복구한다.

## 3. P1.5-0 playback Sequence를 만든다

- source PSA: `CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1.psa`
- source package: `BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1`
- Composite: `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/WeakAtk/AC_Kazan_DualAxeSword_Com_WeakAtk01`
- source 직접값: `SequenceLength=3.5333333 s`, `NumFrames=107`, `bEnableRootMotion=true`, `bForceRootLock=true`
- Composite 직접값: source segment `0–3.53 s`, rate `1.0`, loop `1`, Dilation table `213` points, `DilationSequenceLength=3.4326434 s`, `TimePerFrame=0.016666668 s`
- 출력 계산값: `206` intervals, `207` samples, frame rate `5110687/85161 ≈ 60.01205951 fps`

각 출력 index `i=0..206`에 대해 `t_out=i*3.4326434/206`을 만들고, 저장 table의 `(T_Dilation,T_Original)`을 piecewise-linear 역보간해 `t_src`를 구한다. source pose의 translation/scale은 선형 보간하고 quaternion은 두 key의 내적이 음수면 뒤 quaternion 부호를 뒤집은 뒤 normalized linear interpolation한다. `Root`도 다른 모든 bone과 같은 `t_src`로 표본화한다.

출력 asset은 `/Game/_Art/Kazan/Animation/Combat/Runtime/DualAxeSword/A_DAS_WeakAtk01_Playback`이며 target Skeleton은 `/Game/_Art/Kazan/Character/Meshs/SK_Khazan`, preview mesh는 `/Game/_Art/Kazan/Character/Meshs/SKM_Khazan`이다. `Rate Scale=1.0`, `Enable Root Motion=true`, `Force Root Lock=true`, `Root Motion Root Lock=Ref Pose`로 저장한다. 마지막 enum은 원작 직렬화값이 아니라 UE 5.8 constructor 기본값이므로 첫 frame 튐과 root delta 검사 후 유지한다.

PSA의 프로젝트 좌표 변환 뒤 Root 시작은 약 `(0, 0.0000085, 0) cm`, 끝은 약 `(0, 131.546997, 0) cm`, delta는 약 `(0, 131.546982, 0) cm`, path distance는 약 `181.456085 cm`다. 이 값들은 에셋 생성 후 방향·규모 회귀검사에 쓰며 Montage blend와 collision을 거친 최종 capsule 순변위와 무조건 같다고 보지 않는다.

기존 `Scripts/Enemies/prepare_big_bear_animation_timing.py`의 ActorX parse·좌표 변환·보간과 `Scripts/Enemies/import_big_bear_animations.py`의 UE 5.8 `AnimSequenceFactory`·controller 기록 계약만 좁게 재사용한다. BigBear manifest/path를 고치지 않고 Player 전용 `Scripts/Animation/prepare_das_weak_attack_playback.py`, `Scripts/Animation/import_das_weak_attack_playback.py`로 분리한다.

## 4. P1.5-1 Montage를 만든다

1. playback Sequence로 `AM_DAS_WeakAttackCombo`를 만든다.
2. Slot은 Main ABP가 소비하는 `DefaultGroup.DefaultSlot`이다.
3. 첫 section은 `Attack01`, 시작은 `0.0 s`, `Next Section=None`이다.
4. segment는 playback Sequence 전체, segment play rate `1.0`, loop count `1`, Montage Rate Scale `1.0`이다.
5. 원작 `Step1`의 `AnimBlendAlpha=0.1`, `AnimPlayRate=1.0`, `AnimLoopCount=1`, `bApplyAttackSpeed=true`는 직접 확인됐다. 다만 `AnimBlendAlpha`의 원작 소비 코드가 없으므로 이를 Montage Blend In/Out 초 값과 확정적으로 같다고 기록하지 않는다. `RigRotToTarget.StartBlendTime=0.24`, `EndBlendTime=0.3`은 왼손 타깃 보정 값이라 Montage에 복사하지 않는다.
   - P1.5의 실제 비교를 시작하기 위한 임시 원작-field 매핑값으로 Montage Blend In/Out Time을 각각 `0.10 s`로 둘 수 있다. 이는 `AnimBlendAlpha=0.1`을 초 단위 양쪽 blend로 해석한 가정이며 원작 직접 확인값이 아니다. 시작·종료 pose와 capsule root displacement를 원작 영상과 비교해 유지 여부를 판정한다.
6. Main ABP Root Motion Mode는 현재 계약인 `Root Motion from Montages Only`를 유지한다.
7. 원작 notify 45개는 아직 복사하지 않는다. P1.5는 pose 시간축, root 이동, task 수명만 연결한다.

## 5. P1.5-2 Ability Source 계약

`UKhazanWeakAttackAbility`는 `WeakAttackMontage` asset reference와 활성 `MontageTask`만 가진다. 임시 gait cap, LocomotionComponent weak pointer, constraint handle, 편집 가능한 play-rate property를 만들지 않는다.

task 호출의 고정 인자는 다음과 같다.

```cpp
MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
	this,
	FName(TEXT("WeakAttackComboMontage")),
	WeakAttackMontage,
	/* Rate */ 1.f,
	FName(TEXT("Attack01")),
	/* bStopWhenAbilityEnds */ true,
	/* AnimRootMotionTranslationScale */ 1.f,
	/* StartTimeSeconds */ 0.f,
	/* bAllowInterruptAfterBlendOut */ true);
```

UE 5.8 header가 설명하듯 마지막 값이 `false`이면 정상 Blend Out 시작 뒤 interrupt에서 `OnInterrupted`도 `OnCompleted`도 받지 못할 수 있다. 따라서 `true`를 명시한다. `OnCompleted`는 정상 종료, `OnInterrupted`와 `OnCancelled`는 취소 종료로 연결하고 `OnBlendOut`에는 Ability 종료를 연결하지 않는다.

`EndAbility()`가 실행되면 base 구현이 등록된 모든 AbilityTask를 종료한다. `bStopWhenAbilityEnds=true`이므로 외부 취소나 사망 정책이 Ability를 끝낼 때 해당 Montage와 그 root-motion 발생도 같이 멈춘다. `EndAbility()`는 Spec 제거가 아니라 이번 활성 실행만 끝낸다.

### 사용자가 적용할 전체 header

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "KhazanWeakAttackAbility.generated.h"

class UAbilityTask_PlayMontageAndWait;
class UAnimMontage;

UCLASS(Blueprintable)
class KHAZAN_API UKhazanWeakAttackAbility : public UGameplayAbility
{
	GENERATED_BODY()

public:
	UKhazanWeakAttackAbility();

protected:
	virtual void ActivateAbility(
		const FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		const FGameplayEventData* TriggerEventData) override;

	virtual void EndAbility(
		const FGameplayAbilitySpecHandle SpecHandle,
		const FGameplayAbilityActorInfo* ActorInfo,
		const FGameplayAbilityActivationInfo ActivationInfo,
		bool bReplicateEndAbility,
		bool bWasCancelled) override;

private:
	UFUNCTION()
	void HandleMontageCompleted();

	UFUNCTION()
	void HandleMontageInterrupted();

	UFUNCTION()
	void HandleMontageCancelled();

	void FinishAbility(bool bWasCancelled);

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Khazan|WeakAttack|Animation",
		meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UAnimMontage> WeakAttackMontage = nullptr;

	UPROPERTY(Transient)
	TObjectPtr<UAbilityTask_PlayMontageAndWait> MontageTask = nullptr;
};
```

### 사용자가 적용할 전체 cpp

```cpp
#include "Ability/KhazanWeakAttackAbility.h"

#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "GameFramework/Character.h"
#include "LogChannels.h"

namespace KhazanWeakAttackAbilityPrivate
{
	const FName MontageTaskName(TEXT("WeakAttackComboMontage"));
	const FName FirstSectionName(TEXT("Attack01"));
}

UKhazanWeakAttackAbility::UKhazanWeakAttackAbility()
{
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
	NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
}

void UKhazanWeakAttackAbility::ActivateAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	const FGameplayEventData* TriggerEventData)
{
	MontageTask = nullptr;

	ACharacter* Character = ActorInfo
		? Cast<ACharacter>(ActorInfo->AvatarActor.Get())
		: nullptr;
	UAnimInstance* AnimInstance = ActorInfo ? ActorInfo->GetAnimInstance() : nullptr;
	const bool bHasFirstSection = IsValid(WeakAttackMontage)
		&& WeakAttackMontage->GetSectionIndex(KhazanWeakAttackAbilityPrivate::FirstSectionName) != INDEX_NONE;

	if (!IsValid(Character) || !IsValid(AnimInstance) || !bHasFirstSection)
	{
		UE_LOG(LogAbility, Error,
			TEXT("%s could not start %s. Character=%s, AnimInstance=%s, Montage=%s, Attack01=%s."),
			*GetNameSafe(ActorInfo ? ActorInfo->AvatarActor.Get() : nullptr),
			*GetNameSafe(GetClass()),
			*GetNameSafe(Character),
			*GetNameSafe(AnimInstance),
			*GetNameSafe(WeakAttackMontage),
			bHasFirstSection ? TEXT("valid") : TEXT("missing"));

		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	if (!CommitAbility(SpecHandle, ActorInfo, ActivationInfo))
	{
		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	MontageTask = UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
		this,
		KhazanWeakAttackAbilityPrivate::MontageTaskName,
		WeakAttackMontage,
		/* Rate */ 1.f,
		KhazanWeakAttackAbilityPrivate::FirstSectionName,
		/* bStopWhenAbilityEnds */ true,
		/* AnimRootMotionTranslationScale */ 1.f,
		/* StartTimeSeconds */ 0.f,
		/* bAllowInterruptAfterBlendOut */ true);

	if (!IsValid(MontageTask))
	{
		UE_LOG(LogAbility, Error, TEXT("%s failed to create the WeakAttack montage task."),
			*GetNameSafe(Character));

		EndAbility(SpecHandle, ActorInfo, ActivationInfo,
			/* bReplicateEndAbility */ true,
			/* bWasCancelled */ true);
		return;
	}

	MontageTask->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
	MontageTask->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageInterrupted);
	MontageTask->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageCancelled);
	MontageTask->ReadyForActivation();

	if (IsActive())
	{
		UE_LOG(LogAbility, Log, TEXT("%s started %s at section %s."),
			*GetNameSafe(Character),
			*GetNameSafe(GetClass()),
			*KhazanWeakAttackAbilityPrivate::FirstSectionName.ToString());
	}
}

void UKhazanWeakAttackAbility::EndAbility(
	const FGameplayAbilitySpecHandle SpecHandle,
	const FGameplayAbilityActorInfo* ActorInfo,
	const FGameplayAbilityActivationInfo ActivationInfo,
	bool bReplicateEndAbility,
	bool bWasCancelled)
{
	Super::EndAbility(
		SpecHandle,
		ActorInfo,
		ActivationInfo,
		bReplicateEndAbility,
		bWasCancelled);

	if (!IsActive())
	{
		MontageTask = nullptr;
	}
}

void UKhazanWeakAttackAbility::HandleMontageCompleted()
{
	FinishAbility(/* bWasCancelled */ false);
}

void UKhazanWeakAttackAbility::HandleMontageInterrupted()
{
	FinishAbility(/* bWasCancelled */ true);
}

void UKhazanWeakAttackAbility::HandleMontageCancelled()
{
	FinishAbility(/* bWasCancelled */ true);
}

void UKhazanWeakAttackAbility::FinishAbility(const bool bWasCancelled)
{
	if (!IsActive())
	{
		return;
	}

	EndAbility(
		GetCurrentAbilitySpecHandle(),
		GetCurrentActorInfo(),
		GetCurrentActivationInfo(),
		/* bReplicateEndAbility */ true,
		bWasCancelled);
}
```

`MontageTask=nullptr` 초기화는 `InstancedPerActor` instance 재사용 때 이전 실행의 관측 포인터를 버린다. Avatar·AnimInstance·Montage·`Attack01`을 `CommitAbility()` 전에 검사하므로 설정 오류에서 미래 cost/cooldown을 먼저 소비하지 않는다. factory는 task를 만들 뿐이고 delegate를 모두 연결한 뒤 `ReadyForActivation()`이 실제 재생을 시작한다. 재생 시작 실패는 그 호출 안에서 `OnCancelled`를 동기 발생시킬 수 있으므로 성공 로그는 `IsActive()`를 다시 확인한 뒤 남긴다.

`EndAbility()`는 먼저 engine base cleanup을 실행한다. base가 scope lock 때문에 종료를 지연했다면 Ability가 아직 active이므로 pointer를 유지하고, 실제 종료돼 inactive가 된 뒤에만 pointer를 비운다. base는 active task를 끝내며 `bStopWhenAbilityEnds=true`인 task가 자신이 재생 중인 Montage를 중지한다. 세 callback이 거의 동시에 겹쳐도 `FinishAbility()`의 `IsActive()` guard와 engine의 중복 종료 guard가 두 번째 종료를 무시한다.

`GA_WeakAttack_Khazan`은 이 native 함수를 덮어쓰지 않는 data-only Blueprint로 사용한다. Blueprint Event Activate Ability를 새로 구현하면 native 실행 경로가 달라질 수 있으므로 P1.5에서는 Class Defaults의 Montage reference만 작성한다.

## 6. P1.5-3 Blueprint·Definition

native class를 부모로 하는 `GA_WeakAttack_Khazan`을 만들고 Class Defaults의 `Weak Attack Montage`에 `AM_DAS_WeakAttackCombo`를 지정한다. CharacterDefinition의 기존 한 grant entry class를 이 Blueprint generated class로 교체하며 `Input.Action.Attack`은 유지한다. native class entry를 남긴 채 Blueprint entry를 추가하면 같은 입력 태그의 Spec이 둘이 되어 두 활성화를 시도할 수 있으므로 금지한다.

## 7. P1.5-4 합격 기준

1. 한 press에 Ability·task·Montage가 각각 한 번만 시작한다.
2. `Attack01`만 재생되고 입력 없이 다음 section으로 가지 않는다.
3. capsule이 root-motion 방향으로 이동하고 Mesh만 빠졌다가 capsule로 돌아오지 않는다.
4. 벽에서는 CMC collision이 capsule을 막는다.
5. 이동 입력을 유지해도 locomotion 속도와 root delta가 이중 가산되지 않고, 공격이 끝난 뒤 기존 raw intent로 locomotion이 재개된다.
6. 정상 완료 뒤 Ability는 inactive, Montage/task는 종료, granted Spec은 ASC에 한 개 남는다.
7. 강제 cancel과 다른 Montage interrupt 뒤에도 같은 정리 결과가 나온다.
8. Blend Out이 시작된 직후 interrupt해도 Ability가 active로 고착되지 않는다.
9. 빠른 두 번째 Attack 입력은 P1.5에서는 새 task나 `Attack02`를 만들지 않는다.
10. 다음 PIE에서 stale Montage, root-motion scale, Ability active 상태가 남지 않는다.

## 8. 현재 실제 상태

2026-09-16 현재 실제 Source는 native rename과 `ServerOnly`까지 적용됐고 `ActivateAbility()`는 `CommitAbility()` 직후 `EndAbility()`한다. 위 playback Sequence, Montage, AbilityTask 코드, Ability Blueprint, rename 뒤 cold build·Definition resave·PIE는 아직 적용 또는 검증되지 않았다.

## 2026-09-17 — 사용자 적용 뒤 상태

- 실제 Source에 P1.5의 `UAbilityTask_PlayMontageAndWait` 경로가 적용됐다. 사용자는 좌클릭 시 Montage가 재생되는 것을 PIE에서 확인했다.
- 로그에는 `GA_Player_WeakAttack_C`가 `Attack01` section에서 시작됐다는 기록이 반복돼 있다. 따라서 앞의 “AbilityTask 코드와 PIE가 미적용”이라는 2026-09-16 상태는 현재 상태가 아니다.
- 아직 증거가 없는 항목은 이 문서 7절의 강제 cancel, 다른 Montage interrupt, Blend Out 직후 interrupt, 다음 PIE cleanup 검증이다. 시작 재생 확인만으로 이 항목들을 완료 처리하지 않는다.
- 현재 코드는 엔진 task를 올바른 책임 위치에서 사용한다. 가독성 때문에 별도 interface/static utility를 추가하지 않고, 필요하면 Ability 내부 private 함수 및 공통 abort callback으로 정리한다.

<a id="p1-6-a-attack-input-contract-20260917"></a>
## 2026-09-17 — 다음 공동 구현 P1.6-A: 약·강 공격 입력 수명

이번에 사용자가 실제로 구현할 범위는 combo section 전환이 아니라 그 전제인 입력 contract다. 게임 파일은 이 설명 작업에서 직접 수정하지 않았다. 순서는 native tag 등록 → Editor asset 이관 → ASC/Controller 코드 교체 → cold build/PIE다.

### 1. 왜 먼저 이 단계를 하는가

현재 `TryActivateAbilitiesByInputTag()`는 비활성 Spec을 활성화할 수만 있다. Ability가 이미 `Attack01`을 실행 중일 때 같은 좌클릭을 누르면 `TryActivateAbility()`가 다시 실패하거나 무시될 뿐, 실행 중 Ability의 `WaitInputPress`에는 입력이 도착하지 않는다. 우클릭과 release도 아예 존재하지 않는다. 콤보 node와 buffer를 추가하기 전에 이 입력 수명을 먼저 연결해야 한다.

### 2. native tag를 먼저 추가한다

첫 cold build에서는 기존 `Input_Action_Attack`을 지우지 말고 아래 두 tag를 나란히 추가한다. Editor asset이 아직 옛 tag를 직렬화하고 있으므로 이관 전에 제거하면 asset picker와 기존 grant가 끊긴다.

```cpp
UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_WeakAttack);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(Input_Action_StrongAttack);
```

```cpp
UE_DEFINE_GAMEPLAY_TAG(Input_Action_WeakAttack, "Input.Action.WeakAttack");
UE_DEFINE_GAMEPLAY_TAG(Input_Action_StrongAttack, "Input.Action.StrongAttack");
```

`WeakAttack`은 원작 `SkillM01/FastAttack`, `StrongAttack`은 `SkillM02/StrongAttack`의 프로젝트 의미 이름이다. 물리 Left/Right Mouse Button 이름을 tag에 넣지 않아 키 리바인딩과 AI 요청에서 장치 이름이 새지 않게 한다.

### 3. Editor에서 Input asset을 이관한다

1. Content Browser에서 `/Game/Input/IA_Attack`을 **Rename**으로 `IA_WeakAttack`으로 바꾼다. Explorer에서 `.uasset` 파일 이름을 바꾸지 않는다.
2. 같은 Bool/Digital 값 형식의 `/Game/Input/IA_StrongAttack`을 만든다. 두 InputAction에 Hold trigger나 Combo trigger를 넣지 않는다.
3. `/Game/Input/IMC_Default`에서 Left Mouse Button은 `IA_WeakAttack`, Right Mouse Button은 `IA_StrongAttack`으로 매핑한다.
4. `/Game/Data/DA_InputData`의 기존 `Input.Action.Attack → IA_Attack` entry를 `Input.Action.WeakAttack → IA_WeakAttack`으로 바꾸고 `Input.Action.StrongAttack → IA_StrongAttack` entry를 추가한다.
5. `/Game/Data/Character/DA_CharacterDefinition_Khazan`의 기존 Weak Ability grant Input Tag를 `Input.Action.WeakAttack`으로 바꾼다. 아직 `UKhazanStrongAttackAbility`가 없으므로 Strong grant를 가짜 class에 연결하지 않는다.
6. Save All 뒤 `/Game/Input` 폴더에서 Fix Up Redirectors를 실행한다. Reference Viewer에서 `IA_Attack` redirector만 남거나 옛 `Input.Action.Attack`을 소비하는 asset이 없는지 확인한다.

두 번째 source 변경과 cold build에서 모든 asset 이관을 확인한 뒤 `Input_Action_Attack` 선언/정의를 제거한다. Weak Spec에 옛 tag와 새 tag를 동시에 장기간 달아 두지 않는다.

### 4. ASC API를 press/release로 교체한다

`KhazanAbilitySystemComponent.h`의 공개 API는 아래 두 함수가 된다.

```cpp
void AbilityInputTagPressed(const FGameplayTag& InputTag);
void AbilityInputTagReleased(const FGameplayTag& InputTag);
```

기존 `TryActivateAbilitiesByInputTag()`는 Controller 이관이 끝난 같은 변경에서 제거한다. 구현의 핵심 순서는 아래와 같다.

`KhazanAbilitySystemComponent.cpp`에는 `GameplayAbilitySpec.h`와 함께 `Abilities/GameplayAbility.h`를 include한다. `GetPrimaryInstance()`가 반환한 실제 Ability instance에서 current activation info를 읽으려면 완전한 `UGameplayAbility` 타입이 필요하다.

```cpp
void UKhazanAbilitySystemComponent::AbilityInputTagPressed(const FGameplayTag& InputTag)
{
    if (!InputTag.IsValid())
    {
        return;
    }

    FScopedAbilityListLock AbilityListLock(*this);

    for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
    {
        if (!AbilitySpec.Ability ||
            !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
        {
            continue;
        }

        AbilitySpec.InputPressed = true;

        if (!AbilitySpec.IsActive())
        {
            TryActivateAbility(AbilitySpec.Handle);
            continue;
        }

        AbilitySpecInputPressed(AbilitySpec);

        FGameplayAbilityActivationInfo ActivationInfo = AbilitySpec.ActivationInfo;
        if (UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance())
        {
            ActivationInfo = PrimaryInstance->GetCurrentActivationInfo();
        }

        InvokeReplicatedEvent(
            EAbilityGenericReplicatedEvent::InputPressed,
            AbilitySpec.Handle,
            ActivationInfo.GetActivationPredictionKey());
    }
}
```

`AbilitySpec.InputPressed=true`를 활성화 시도보다 먼저 기록해야 활성화 직후 만들어지는 `WaitInputRelease`가 “현재 눌린 상태”를 볼 수 있다. active이면 `AbilitySpecInputPressed()`가 Ability instance의 일반 input callback을 수행하고, 이어지는 `InvokeReplicatedEvent()`가 `WaitInputPress` task delegate를 깨운다. 둘 중 하나만 호출하면 UE 5.8의 표준 입력 contract를 온전히 재현하지 못한다.

release도 대칭이다.

```cpp
void UKhazanAbilitySystemComponent::AbilityInputTagReleased(const FGameplayTag& InputTag)
{
    if (!InputTag.IsValid())
    {
        return;
    }

    FScopedAbilityListLock AbilityListLock(*this);

    for (FGameplayAbilitySpec& AbilitySpec : GetActivatableAbilities())
    {
        if (!AbilitySpec.Ability ||
            !AbilitySpec.GetDynamicSpecSourceTags().HasTagExact(InputTag))
        {
            continue;
        }

        AbilitySpec.InputPressed = false;

        if (!AbilitySpec.IsActive())
        {
            continue;
        }

        AbilitySpecInputReleased(AbilitySpec);

        FGameplayAbilityActivationInfo ActivationInfo = AbilitySpec.ActivationInfo;
        if (UGameplayAbility* PrimaryInstance = AbilitySpec.GetPrimaryInstance())
        {
            ActivationInfo = PrimaryInstance->GetCurrentActivationInfo();
        }

        InvokeReplicatedEvent(
            EAbilityGenericReplicatedEvent::InputReleased,
            AbilitySpec.Handle,
            ActivationInfo.GetActivationPredictionKey());
    }
}
```

현재 프로젝트 공격 Ability는 `InstancedPerActor`이므로 `GetPrimaryInstance()`의 current activation prediction key가 현재 실행을 가리킨다. ASC에는 combo index, hold seconds, input window, Montage 위치를 추가하지 않는다.

### 5. PlayerController는 phase만 번역한다

`SetupInputComponent()`에서 Weak와 Strong 각각 `Started`, `Completed`, `Canceled`를 바인딩한다. `Triggered`는 누르고 있는 매 frame 발생할 수 있으므로 공격 제출에 사용하지 않는다.

```cpp
EnhancedInputComponent->BindAction(
    WeakAttackAction, ETriggerEvent::Started,
    this, &ThisClass::Input_WeakAttackStarted);
EnhancedInputComponent->BindAction(
    WeakAttackAction, ETriggerEvent::Completed,
    this, &ThisClass::Input_WeakAttackCompleted);
EnhancedInputComponent->BindAction(
    WeakAttackAction, ETriggerEvent::Canceled,
    this, &ThisClass::Input_WeakAttackCanceled);
```

Strong에도 같은 세 bind를 작성한다. 여섯 callback에서 Pawn과 ASC를 반복해서 cast하지 않도록 Controller private helper 한 개로 `UKhazanAbilitySystemComponent*`를 얻는다. Started는 해당 tag의 `AbilityInputTagPressed()`, Completed는 `AbilityInputTagReleased()`를 호출한다. Canceled도 우선 pressed 상태 정리를 위해 Released를 호출하되, P6-C에서 Strong의 성공 release와 구별되는 typed cancel event를 추가한다. Canceled를 지금부터 별도 함수로 둬야 나중에 의미를 잃지 않는다.

### 6. P1.6-A 검증

1. Editor를 닫고 UE 5.8 cold build를 통과한다.
2. Editor에서 `DA_InputData`, `IMC_Default`, CharacterDefinition을 다시 열어 Weak/Strong tag와 InputAction 참조가 유효한지 본다.
3. PIE 첫 Left press에서 inactive Weak Spec이 한 번만 활성화되고 `Attack01`이 시작되는지 확인한다.
4. Montage 실행 중 Left를 다시 누르면 새 Montage/새 Ability activation이 생기지 않고 ASC의 active branch에서 `InvokeReplicatedEvent(InputPressed)`까지 한 번 지나가는지 breakpoint로 확인한다. 아직 `WaitInputPress` consumer가 없으므로 2타가 나오지 않는 것이 정상이다.
5. Left release와 입력 focus 손실로 발생한 Canceled 뒤 `FGameplayAbilitySpec::InputPressed`가 false인지 확인한다.
6. Right press/release가 Controller와 ASC까지 오되 아직 matching Strong Spec이 없어 Ability가 실행되지 않는지 확인한다. 임시 Weak 실행으로 연결하지 않는다.
7. 정상 완료, Montage interrupt, 다음 PIE에서 Weak Ability가 stale active로 남지 않고 granted Spec은 ASC에 한 개 남는지 확인한다.

### 7. 다음 P6-A에서 추가할 것

P1.6-A가 통과하면 `DAS_Khazan_WeakAtk02`를 실제 `AM_DAS_WeakAtkCombo`에 추가하고 `Attack02` section을 만든다. 그때 처음 `UAbilityTask_WaitInputPress::WaitInputPress(this, false)`와 Ability-local buffered input 한 건을 추가한다. `false`는 활성화에 사용된 첫 press를 2타 입력으로 재소비하지 않게 한다.

WeakAtk01 metadata에는 `ReserveInput`과 `SkillInputProg`가 별도로 있다. playback 변환 시간은 다음과 같다.

| 의미 | playback 구간 |
|---|---|
| `ReserveInput` 후보 1 | `0.2205535080–0.4756474282 s` |
| `ReserveInput` 후보 2 | `0.3825092135–0.6388580379 s` |
| `SkillInputProg` 후보 1 | `0.2929789424–0.5131536622 s` |
| `SkillInputProg` 후보 2 | `0.5165015501–0.9242099718 s` |
| 늦은 `ReserveInput` 후보 | `1.0419576641–1.1919575 s` — 01→02에서 제외 |

`SB_...WeakAtk`의 Step1은 `Index8`에서 `Pressed` input event를 `Step2`로 바꾸는 함수에 연결한다. late `Index7` input-check는 `NotifyEnable` 조건 뒤 `Step1` same-step 변경으로 연결되므로 마지막 ReserveInput을 01→02용으로 섞지 않는다. P6-A에서는 앞 두 reservation 후보와 두 progression 후보만 사용하고, 늦은 후보의 restart/repeat 의미는 별도 checkpoint로 남긴다.

P6-A에서 하나의 `bComboWindowOpen`으로 다 합치지 않는다. Ability 지역에 서로 겹칠 수 있는 reservation window와 advance window를 구분한다. advance가 열린 press는 즉시 edge를 소비하고, reservation만 열린 press는 한 건을 보관하며, advance begin에서 보관 입력을 다시 검사한다. 이 해석은 class 이름과 graph 연결을 합친 원작 기반 추론이므로 첫 PIE에서 원작 영상과 조작 반응을 비교하고, proprietary runtime 의미가 다르면 두 window의 역할만 보정한다. 임의 buffer 초는 추가하지 않는다.

Strong은 그 다음 P6-C에서 별도 `UKhazanStrongAttackAbility`로 구현한다. Right Started가 Start/Charge를 즉시 시작하고 `WaitInputRelease`가 release를 기다린다. `TimeHeld`는 관측값이며 원작 charge-step Notify의 대체 임계값이 아니다. Weak↔Strong 조합은 P6-D에서 input tag가 담긴 Gameplay Event를 실제 소비할 때 추가한다.

## 2026-09-17 — P1.6-A 적용 전 추가 확인: Combo Trigger와 연타는 넣지 않는다

현재 프로젝트 엔진 UE 5.8에서 `UInputTriggerCombo`, `FInputComboStepData`, `FInputCancelAction`은 deprecated다. 이 trigger는 입력 순서와 step 간 제한시간을 인식할 뿐 현재 montage section과 원작 reservation/progression window를 알지 못한다. 따라서 `IA_WeakAttack`과 `IA_StrongAttack`의 Triggers 배열에는 P1.6-A에서 `Combo`, `Hold`, `Chorded Action`을 추가하지 않는다.

P1.6-A의 목적은 다음 세 edge가 손실 없이 GAS에 도달하게 하는 것뿐이다.

| Enhanced Input | 프로젝트 의미 | 이번 단계의 ASC 처리 |
| --- | --- | --- |
| `Started` | press | `Spec.InputPressed=true`, inactive면 activate, active면 generic pressed event |
| `Completed` | 정상 release | `Spec.InputPressed=false`, active면 generic released event |
| `Canceled` | 입력 평가 취소 | pressed cleanup을 위해 released protocol 실행. P6-C에서 정상 release와 별도 typed cancel 의미 추가 |

연타 처리의 첫 실제 구현은 P6-A의 활성 Weak Ability 안에 둔다.

1. `Attack01` 진입 시 현재 node용 buffered input을 비우고 `WaitInputPress(false)`를 arm한다.
2. press가 왔을 때 advance window가 열려 있으면 01→02 edge를 즉시 검증한다.
3. advance는 닫혔고 reservation만 열려 있으면 최초 Weak press 한 건을 저장한다.
4. 둘 다 닫혀 있으면 해당 press를 버린다.
5. slot이 찬 뒤 들어온 추가 Weak/Strong press는 queue 뒤에 붙이거나 기존 선택을 덮지 않는다.
6. advance begin 시 저장 입력을 unlock/tag/cost와 현재 section에 대해 다시 검증한다.
7. 성공한 경우에만 `Attack01 -> Attack02` next section을 설정하고 slot을 소비한 뒤 현재 node의 transition을 committed로 잠근다.
8. committed 뒤에는 Attack01의 남은 window에서 추가 press를 무시하고 input wait를 다시 만들지 않는다.
9. `Attack02`가 실제 시작된 뒤 current node를 바꾸고 committed를 해제하며 새 node용 slot을 비운 다음 input wait를 새로 arm한다.
10. montage interrupt, cancel, 정상 end에서는 window, slot, committed 상태를 모두 reset한다.

이 규칙으로 좌클릭을 빠르게 여러 번 눌러도 Attack01 중 받아들인 한 번만 Attack02를 예약한다. Attack03은 Attack02가 시작된 뒤 들어온 새 입력이 있어야 예약된다. 원작의 buffer overwrite 정책은 아직 직접 확인되지 않았으므로 `first accepted input wins`는 난타가 전체 콤보를 자동 재생하지 않게 하는 초기 제품 정책으로 기록하고 조작 비교에서 보정한다.

`CombatInputBufferComponent`는 P6-A에서 만들지 않는다. 같은 공격 실행의 node/window/buffer는 Ability 수명과 함께 끝나므로 Ability가 가장 작은 올바른 owner다. 이후 Attack→Dodge 같은 서로 다른 Ability 사이의 recovery queue 또는 방향 command history를 둘 이상의 실제 소비자가 공유하게 될 때만 별도 component를 검토하며, 그 경우에도 montage와 Combo Definition 판정은 component에 넣지 않는다.

## 2026-09-17 — P1.6-A 착수 직전 실제 프로젝트 재확인

- 현재 실제 Ability Blueprint는 `/Game/Bluprints/Abilities/Player/GA_Player_WeakAttack`이고 실제 Montage는 `/Game/_Art/Kazan/Animation/InGame/DAS/WeakAtk/AM_DAS_WeakAtkCombo`다. 앞 절의 `GA_WeakAttack_Khazan`, `AM_DAS_WeakAttackCombo`는 과거 절차명이며 이번 적용에서는 실제 asset 이름을 바꾸지 않는다.
- 현재 `UKhazanWeakAttackAbility::StartWeakAtkMontage()`는 `UAbilityTask_PlayMontageAndWait* Task` 지역 변수를 사용한다. 헤더에 `MontageTask` 멤버가 없고 cpp에도 `MontageTask = nullptr` 대입이 없으므로 P1.6-A에서 Ability task 보관 방식을 바꾸지 않는다.
- P1.5 잔여 보정으로 `Task->OnCancelled`를 기존 `HandleMontageAborted()`에 연결해야 한다. UE 5.8 task는 Montage 재생 시작 실패와 `ExternalCancel()`에서 이 delegate를 broadcast하므로, 연결하지 않으면 실패 경로에서 Ability가 active로 남을 수 있다. 이는 P1.6-A 입력 구조 변경이 아니라 첫 cold build 전에 함께 적용할 한 줄짜리 수명 보정이다.
- 현재 native input tag는 `Input.Action.Attack` 하나이고, `AKhazanPlayerController`는 `IA_Attack`의 `Started`만 받아 `TryActivateAbilitiesByInputTag()`를 호출한다. ASC는 inactive/active를 구분하지 않고 매번 `TryActivateAbility()`만 시도한다.
- 실제 마이그레이션 대상은 `/Game/Input/IA_Attack`, `/Game/Input/IMC_Default`, `/Game/Data/DA_InputData`, `/Game/Data/Character/DA_CharacterDefinition_Khazan`과 GameplayTags·ASC·PlayerController source다. WeakAttack Ability와 Montage는 이번 단계의 수정 대상이 아니다.
- 이 기록은 적용 전 재확인이다. 게임 Source, InputAction, MappingContext, DataAsset, Blueprint, Montage, build와 PIE는 이 설명 작업에서 수정하거나 실행하지 않았다.

## 2026-09-17 — P1.6-A 적용 뒤 다음 공동 구현 P6-A

- 적용 감사에서 Weak/Strong 입력과 ASC protocol, asset 이관, build와 Attack01 PIE 시작은 확인됐다. 먼저 `Input_WeakAttackCanceled()`의 잘못된 press 호출을 release로 바꾸고 `DA_InputData`의 누락된 Jump row를 복구한다.
- `AM_DAS_WeakAtkCombo`에는 `DAS_Khazan_WeakAtk02`를 Attack01 뒤에 추가하고 `Attack02` section을 segment 시작에 둔다. Attack01과 Attack02 authored Next Section은 둘 다 `None`이다.
- Montage의 gameplay window 신호는 begin/end tag를 보내는 작은 generic AnimNotifyState 한 타입으로 연결한다. WeakAttack Ability는 네 `WaitGameplayEvent` listener와 `WaitInputPress(false)`를 소유한다.
- reservation 구간 둘이 겹치므로 `InputReservationDepth`, advance에도 대칭적인 `ComboAdvanceDepth`를 사용한다. buffer는 bool 한 건, transition 확정도 bool 한 건이며 activation 시작과 `EndAbility()`에서 모두 reset한다.
- window는 `PlaybackEvents.json`과 WeakAttack timing report의 Dilation 변환값을 사용한다. reservation은 `0.2205535080–0.4756474282`, `0.3825092135–0.6388580379 s`, advance는 `0.2929789424–0.5131536622`, `0.5165015501–0.9242099718 s`다. 늦은 reservation 후보는 P6-A에서 제외한다.
- 합격 기준은 무입력 `Attack01` 종료, reservation 입력 한 건의 지연 소비, advance 입력의 즉시 확정, 창 밖 입력 폐기와 재대기, 난타 시 Attack02까지만 진행, 모든 종료에서 stale depth/buffer/commit 부재, Root Motion capsule 이동 연속성이다.

## 2026-09-17 — P6-A 설명 보정: 내장 Montage Notify Window 사용

- 바로 위 절의 generic GameplayEvent window NotifyState와 event tag 네 개는 P6-A 적용안에서 제외한다. 내장 `Montage Notify Window`를 사용하고 Notify Name은 `InputReservation`, `ComboAdvance` 두 개만 둔다. Begin delegate가 depth를 올리고 End delegate가 내리므로 이름마다 Begin/End tag를 따로 만들지 않는다.
- `UKhazanWeakAttackAbility`는 activation 동안 `UAnimInstance::OnPlayMontageNotifyBegin/End`에 bind하고 자기 `WeakAttackMontage` payload만 받는다. `EndAbility()`에서 두 delegate를 반드시 unbind한 뒤 모든 지역 상태를 reset한다. Notify End는 정상 시간축 갱신에 쓰되 interruption cleanup의 최종 보장은 계속 `EndAbility()`다.
- Montage editor read-only 확인값은 Attack01 segment `0.0–3.4326434135 s`, Montage cached length `3.4326500893 s`, Attack02 source length `3.3280539513 s`, 양쪽 Sequence Rate Scale `1.0`, Enable Root Motion `true`, Force Root Lock `true`다. Attack02는 실제 editor segment 끝에 snap해서 붙이며 보고서 소수값을 손으로 절대 위치에 입력하지 않는다.
- 새 Attack02 section을 만들면 엔진이 Attack01의 Next Section을 Attack02로 자동 지정한다. Montage Sections의 `Clear` 또는 개별 연결 해제로 Attack01/Attack02 authored next를 둘 다 `None`으로 만든다. 무입력 1타 종료를 성립시키는 필수 단계다.
- notify track 이름은 편집 가독성만 위한 분류이며 runtime 식별자가 아니다. runtime은 각 `Montage Notify Window` 안의 Notify Name을 비교한다. 두 reservation window와 두 advance window를 Attack01 section의 playback 시간에 각각 배치하고 하나의 긴 window로 합치지 않는다.

## 2026-09-17 — P6-A 구현 형태 보정: 시험용 2타 코드로 고정하지 않는다

- 앞 절의 `bool` 한 건 buffer는 최종 Source에서 `FGameplayTag BufferedInputTag` 한 칸으로 구현한다. invalid tag가 empty이며 P6-A의 `WaitInputPress(false)` callback은 `Input.Action.WeakAttack`을 넣는다. 이는 이미 확인된 Weak↔Strong 입력 의미를 잃지 않으면서 FIFO나 별도 객체를 만들지 않는 최소 표현이다.
- 최종 함수 이름을 `TryCommitAttack02()`로 두지 않는다. `TryCommitBufferedTransition()` 한 함수가 현재 Montage/section, buffer tag, 창과 committed 상태를 검증하고 P6-A에서는 `Attack01 + Weak → Attack02` 규칙 하나만 선택·연결한다. 한 번만 쓰는 별도 resolver 함수는 아직 만들지 않는다.
- P6-B에서 02→03→04와 해금 05를, P6-D에서 확인된 혼합 edge를 같은 함수의 규칙으로 추가한다. current node·buffer·cleanup owner와 호출 흐름은 바꾸지 않는다. 분기 수와 편집 요구가 실제로 커질 때만 조회 함수 분리나 read-only DataAsset 이관을 다시 판단한다.
- 나머지 최소 상태는 겹치는 원작 창 때문에 필요한 `InputReservationDepth`, `ComboAdvanceDepth`와 section당 중복 확정을 막는 `bTransitionCommitted`다. ASC, AnimInstance, 별도 Component에는 이 상태를 복사하지 않는다.

## 2026-09-17 — P6-A 최종 적용 절차 보정: section 끝 연결이 아니라 중간 재생 교체

- 바로 위 절까지의 `CurrentMontageSetNextSectionName()`과 `bTransitionCommitted`, `WaitInputPress(false)` 적용안은 이 절에서 대체한다. UE 5.8.2 engine source 확인상 section 이동은 segment cross-fade를 만들지 않으며, full-length Attack01 끝 연결은 회복 동작 뒤에 Attack02를 시작한다.
- Montage에는 Attack01과 Attack02 full sequence를 그대로 보존하고 두 authored Next Section을 모두 `None`으로 둔다. 물리적으로 Attack02 segment가 Attack01 뒤에 있어도 runtime은 그 끝을 기다리지 않는다. 합법 입력 시 기존 montage task를 `EndTask()`한 뒤 같은 Montage를 `StartSection=Attack02`로 다시 재생하여 Montage Blend In `0.1 s`로 두 instance를 교차시킨다. 무입력 시에는 Attack01 전체 회복을 재생한다.
- 기존 task를 먼저 `EndTask()`하는 이유는 새 montage가 기존 montage를 interrupt할 때 이전 task의 `OnInterrupted`가 전체 Ability를 끝내지 못하게 하기 위해서다. `EndTask()` 자체는 Ability가 끝난 경우가 아니므로 `bStopWhenAbilityEnds=true`여도 기존 montage를 즉시 정지하지 않으며, 뒤이은 새 `Montage_Play`가 blend 설정으로 기존 instance를 정지시킨다.
- `ActiveMontageTask`는 이제 지역 변수가 아니라 Ability의 transient member다. 이 변경은 재사용 helper를 만들기 위한 것이 아니라 section 교체 직전에 이전 task의 delegate 수명을 닫기 위해 실제로 필요하다. 새 재생 뒤 `GetActiveInstanceForMontage()`의 instance ID를 저장하고 Montage Notify callback에서 asset과 ID를 모두 검사한다.
- 현재 ASC가 이미 active Spec의 `InputPressed()` virtual을 호출하므로 Weak 재입력은 Ability override에서 `Input.Action.WeakAttack`을 제출한다. 별도 `WaitInputPress` task와 재arm 함수는 만들지 않는다. future Weak→Strong edge는 typed event가 같은 `SubmitComboInput(StrongTag)` 경로를 호출하므로 한 칸 tag buffer 계약은 유지된다.
- 즉시 재생 교체 후 current section이 Attack02로 바뀌므로 `bTransitionCommitted`는 제거한다. 유지할 상태는 `CurrentSectionName`, `ActiveMontageInstanceID`, `InputReservationDepth`, `ComboAdvanceDepth`, `BufferedInputTag`, `ActiveMontageTask`, bind된 AnimInstance다.
- Attack01 Montage Notify Window는 원작 변환값을 사용한다. `InputReservation`은 `0.2205535080–0.4756474282 s`, `0.3825092135–0.6388580379 s`; `ComboAdvance`는 `0.2929789424–0.5131536622 s`, `0.5165015501–0.9242099718 s`다. Montage Tick Type은 gameplay 분기에 쓰이므로 `Branching Point`로 둔다. 정확한 proprietary notify 소비 의미는 미확인이므로 early/mid/late 입력을 각각 원작 영상과 비교한다.
- 19개 주요 bone의 local pose를 read-only 표본 비교했을 때 Attack02 시작 pose와 Attack01 약 `0.54–0.57 s` 부근이 가장 가까웠다. 이는 고정 cut 원작값이 아니라 품질 검사용 파생 관측이다. `0.55 s` magic marker를 코드나 asset에 추가하지 않고, 해당 구간을 포함해 early/mid/late 전환의 blend와 root-motion 연속성을 관찰한다.
- raw root track을 `1/120 s` 중앙 차분한 별도 파생 관측에서는 Attack02 시작 Y 속도 약 `335.36 asset-unit/s`에 Attack01 `0.3825092135 s`의 약 `328.62`가 가깝고, pose가 가까운 `0.55 s`에서는 약 `93.76`이었다. pose와 root 속도 양쪽의 최접근 시점이 다르므로 하나의 자동 산출 cut을 원작값처럼 고정하지 않는다. `0.3825 s`와 `0.54–0.57 s`를 모두 slow-motion 품질 관측 지점으로 사용한다.
- 검증은 무입력 1타 full recovery, reservation의 지연 소비, advance의 즉시 전환, 창 밖 입력 폐기, 난타해도 P6-A에서 2타까지만 진행, 이전 instance Notify 무시, cancel/interruption cleanup, capsule root-motion 연속성을 별도 항목으로 수행한다.
