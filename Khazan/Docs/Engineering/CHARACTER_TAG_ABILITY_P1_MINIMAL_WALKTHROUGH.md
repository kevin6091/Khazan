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
