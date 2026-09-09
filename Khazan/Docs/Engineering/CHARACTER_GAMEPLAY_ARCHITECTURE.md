# Khazan 캐릭터·게임플레이 아키텍처 정본

## 2026-09-08 — 목표 아키텍처 v1 확립

### 문서의 지위와 범위

사용자 요청에 따라 앞으로 구현할 **목표 구조를 이 문서로 확립한다.** 이전 검토안의 후보 나열을 실행 기준으로 구체화한 설계 결정이다. 구현이 이미 완료됐거나 원작 게임의 내부 코드를 확인했다는 뜻은 아니다.

- 목표: The First Berserker: Khazan의 HeinMach/StormPass에서 플레이어, 일반 적, 보스, 이동·회피·공격·스킬·피격·사망, 전투와 레벨 진행을 함께 수용한다.
- 이번 산출물: 설계 정본과 문서 라우팅. C++/BP/에셋/Config/빌드 설정 변경은 없다.
- v1 설계 전제: 싱글플레이, ACharacter/CharacterMovementComponent(CMC) 기반 캐릭터. 멀티플레이·Pawn 간 실시간 능력 상태 승계가 요구되면 ASC 소유 위치와 예측/복제 경계를 별도 결정한다.
- 설계 정본은 이 문서, **실제 로코모션 구현 정본**은 [LOCOMOTION_CURRENT_IMPLEMENTATION.md](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md)다. 목표를 현행 구현이라고 기록하지 않는다.
- 기존 [구조 검토](CHARACTER_ARCHITECTURE_REVIEW_20260908.md)는 문제와 검사 근거의 이력이다. 이후 기능 배치·새 클래스·이관 순서는 이 문서를 따른다.
- 이 문서는 기능 설계의 기준이지 앞으로 게임 파일을 직접 수정할 포괄적 허가는 아니다. 공동 구현은 사용자가 직접 따라 하는 설명 방식을 유지한다.

### 보존할 사용자 결정

- 런타임 애니메이션 시퀀스는 `/Game/_Art/Kazan/Animation/InGame` 범위만 사용한다.
- Walk/Run/Sprint의 모든 Start는 제외한다.
- Walk는 좌/우 Turn을 사용한다. Run 전용 Turn은 넣지 않는다.
- Sprint의 반대 방향 전환은 단일 Sprint Stop 클립을 짧게 사용하는 **SprintPivot**이다. 입력 해제에 의한 일반 Stop 상태와 구분한다.
- 현재 Stop은 root-locked/in-place이며 CMC가 이동·감속을 담당한다. 이 설계 확립만으로 Root Motion 정책을 변경하지 않는다.
- 원작 metadata/report를 수치의 우선 출처로 삼는다. 필요하면 명시적인 임시 튜닝값을 사용할 수 있으나 출처·선정 이유·단위·영향·검증 기준을 남긴다.
- 현재 이동 속도나 애니메이션 재생률이 원작 검증값이라고 간주하지 않는다. 이번에는 새 gameplay 수치를 선정하지 않았다.

## 1. 채택한 구조와 변경 불변식

**클래스 기반 제어 HFSM + GAS 액션 실행 + 공통 이동 정책 + 분리된 애니메이션 표현 + 데이터 기반 캐릭터 구성**을 채택한다.

HFSM은 계층형 상태 머신이다. 상위 상태의 공통 정책을 하위 상태가 공유하되, 모든 상태 종류를 한 트리에 넣지는 않는다.

| 결정 ID | 채택 내용 | 막으려는 문제 |
| --- | --- | --- |
| ARCH-01 | 게임플레이와 애니메이션의 최종 결정권을 분리한다. | ABP 전이나 몽타주 상태가 체력·이동 허가의 원본이 되는 문제 |
| ARCH-02 | 클래스 기반 HFSM은 생존·행동 제어 모드만 소유한다. | 공격마다, 발마다, 무기마다 State 클래스를 늘리는 조합 폭발 |
| ARCH-03 | 공격·회피·스킬·피격 반응의 실행 수명은 GAS Ability가 소유한다. | AttackState와 AttackAbility의 중복 시작/종료/취소 |
| ARCH-04 | 공통 LocomotionComponent가 이동 의도와 제약을 해결하고 CMC 정책을 적용한다. | Player와 AI의 이동 구현 복제, 여러 클래스의 회전 경쟁 |
| ARCH-05 | 제약은 원인별 handle로 취득·해제한다. | 공격 종료가 피격·사망의 이동 제한까지 풀어 버리는 문제 |
| ARCH-06 | Main AnimInstance는 공통 관측, Locomotion Linked Layer는 이동 포즈와 이력을 소유한다. | Main에 모든 액션의 bool·float·timer가 쌓이는 문제 |
| ARCH-07 | 같은 동작 구조의 차이는 데이터로, 실제 실행 구조의 차이는 클래스/레이어로 표현한다. | 캐릭터별 C++/ABP 전체 복제 또는 거대한 만능 설정 파일 |
| ARCH-08 | Player와 AI는 같은 액션 요청·이동 제약 계약을 사용한다. | 몬스터만 스태미나/피격/사망 규칙을 우회하는 문제 |
| ARCH-09 | 상태·액션·연출의 취소와 종료는 idempotent하며 요청/실행 식별자를 확인한다. | 오래된 callback이 새 행동을 종료하거나 제어를 복구하는 문제 |
| ARCH-10 | 외부 UObject 수집은 Game Thread, worker에는 평가 수명이 보장된 관측값만 전달한다. | 캐시한 포인터를 thread-safe 데이터로 오인하는 문제 |
| ARCH-11 | 레벨 진행·스폰·체크포인트·보스 전투 진행은 AnimInstance에 넣지 않는다. | 맵/보스 이름별 if가 공통 캐릭터에 누적되는 문제 |
| ARCH-12 | 새 기능은 최소 Player + 일반 적 하나로 공통성을 먼저 검증한다. | 플레이어 로코모션 완성 후에야 공유 불가능함을 발견하는 문제 |

이 선택은 이 프로젝트의 설계 결정이다. UE가 강제하는 유일한 표준이나 원작 카잔의 구조라는 주장이 아니다. GAS를 채택하는 이유는 네트워크만이 아니라 액션 수명, 자원, 효과, 취소 및 비동기 실행 기반을 중복 구현하지 않기 위해서다.

## 2. 전체 책임 구조

```text
PlayerController → Player의 장치/카메라 기준 입력 해석 ─┐
AIController → Behavior Tree / PathFollowing ───────────┤
                                                      ↓
                       AKhazanCharacter의 공통 요청 진입점
                         │                          │
                    이동 의도                    액션 요청
                         ↓                          ↓
              LocomotionComponent        KhazanAbilitySystemComponent
              제약 해결 / 이동 구동          승인 / 실행 / 취소
                         │                          │
                         └── CharacterStateMachine ┘
                             공통 제어 정책 조회
                               ↑            ↑
                          체력/상태 효과   연출 제어 요청

          LocomotionComponent → CMC → 캡슐 이동 / 충돌 / 실제 Velocity
          Ability / Task → CombatComponent → 유효 타격 → Effect / Attribute
                                      ↓
                       Game Thread 애니메이션 스냅샷
                                      ↓
                 Main AnimInstance / Main ABP
                  ├─ Locomotion Linked Layer: 이동 포즈 / Stop 발 이력
                  ├─ Montage Slot: 실행 중 액션의 포즈 합성
                  └─ 필요한 보정: IK / additive / aim

Encounter / Checkpoint / Progression → 캐릭터 생성·제어 요청
캐릭터의 검증된 gameplay 이벤트 → AI / Encounter / UI / Camera / Audio
```

그림의 선은 실제 소유자에게 보내는 typed 요청/관측이다. 모든 통신을 거대한 전역 EventBus로 바꾸라는 뜻은 아니다.

### 단일 작성자 원칙

| 사실 또는 결정 | 최종 소유자 | 다른 계층의 접근 |
| --- | --- | --- |
| 스틱 기울기, L3 토글, 카메라 기준 입력 변환 | Player 입력 어댑터 | 공통 이동 의도로 전달 |
| AI 목표 위치·공격 의도 | AIController/BT | 공통 이동·액션 요청으로 전달 |
| HP, 스태미나 및 수치형 효과 | ASC의 AttributeSet/GameplayEffect 처리 | 읽거나 효과 적용 요청; 별도 HP float 금지 |
| 생존/일반 조작/강제 제어 모드 | CharacterStateMachineComponent | 읽기 전용 정책·상태 ID |
| 현재 실행 중인 공격/회피/스킬 | 해당 Ability와 ASC 실행 기록 | 실행 ID로 조회·취소 요청 |
| 이동 허용, gait 제한, 회전/이동 구동 선택 | LocomotionComponent의 해결된 정책 | 원인별 제약 요청; CMC 직접 덮어쓰기 금지 |
| 실제 위치·속도·바닥·MovementMode | CMC/엔진 물리 경로 | 관측만; 커스텀 물리 확장은 별도 계약 |
| 적중 창·타격 대상 중복 방지 | CombatComponent, 액션 실행별 기록 | 해당 실행의 창 열기/닫기 요청 |
| 장착 항목·장비가 부여한 능력/에셋 수명 | EquipmentComponent | 로드 완료 통지와 승인된 장비 변경 요청 |
| loop gait·Stop 클립/발·블렌드 | Locomotion 애니메이션 인스턴스/그래프 | gameplay 결정에 역사용하지 않음 |
| 보스 페이즈 | BossPhaseComponent | BT/ABP/UI에는 읽기용 관측 |
| 체크포인트·영속 진행 | Progression/Save 계층 | 안정된 ID로 읽기/저장 |

소유자란 관련 값을 다 그 클래스 안에 넣는다는 뜻이 아니다. 예를 들어 ASC는 Ability에 실행을 위임하고, FSM은 State 객체에 진입/이탈 정책을 위임한다. 승인·수명·종료의 최종 책임이 명확하다는 뜻이다.

## 3. 클래스 기반 HFSM: 무엇을 상태로 만들 것인가

### 3.1 채택할 제어 상태 트리

```text
Character Control
├─ Alive
│  ├─ Operational
│  ├─ Incapacitated
│  └─ Scripted
└─ Dead
```

- `Alive`: 살아 있는 동안 공통으로 적용되는 부모 상태다.
- `Operational`: 일반 입력/AI 요청을 규칙에 따라 받을 수 있다. Idle이라는 뜻이 아니며 공격 중에도 이 제어 상태일 수 있다.
- `Incapacitated`: 기절처럼 일반 조작을 강제로 막는 상태다. 모든 가벼운 피격 모션을 이 상태로 만들지 않는다.
- `Scripted`: 처형·컷신 등 명시적인 시스템이 일반 조작 대신 제어권을 가진다.
- `Dead`: 현재 Pawn의 종단 상태다. 몽타주가 끝나도 Alive로 돌아가지 않는다. v1의 부활은 새 Pawn 생성과 저장 상태 재적용으로 다룬다.
- 초기화 전에는 별도 Ready gate를 닫는다. 데이터가 없는데 기본 Operational로 시작해 행동을 받지 않는다.

프로젝트 제어 우선순위는 **사망 > 강제 행동 불능 > 유효한 연출 제어 요청 > 일반 조작**이다. 원작에서 추출한 우선순위가 아니라 v1 정책이다. 특정 연출의 피격 면역 여부는 피해/효과 규칙에서 별도로 결정한다.

한 캐릭터에는 활성 leaf 하나와 그 조상 경로만 있다. 부모 Alive의 정책과 자식 Operational의 정책이 함께 적용되는 것이지, Operational/Dead를 각각 독립 bool로 켜는 구조가 아니다.

### 3.2 클래스와 함수의 책임

다음 이름은 앞으로 만들 **목표 타입/계약 이름**이며 현재 Source에 존재한다고 가정하지 않는다.

| 타입/함수 | 책임과 이유 |
| --- | --- |
| `UKhazanCharacterStateMachineComponent` | State 인스턴스 소유, 전이 요청 큐, guard 검사, 공통 제어 정책 발행. Character마다 하나 |
| `UKhazanCharacterState : UObject` | 제어 상태의 공통 인터페이스. 공격 에셋이나 PlayerController 입력을 직접 알지 않음 |
| `UKhazanStateAlive` | 살아 있는 경로에 공통인 진입/이탈 규칙 |
| `UKhazanStateOperational` | 일반 조작의 기본 정책 |
| `UKhazanStateIncapacitated` | 행동 불능 원인이 존재하는 동안의 정책 |
| `UKhazanStateScripted` | 연출 소유자의 유효한 요청/취소 수명 |
| `UKhazanStateDead` | 사망 전이, 일반 액션 차단, 사망 이벤트 1회 발행 및 사망 처리 시작 |
| `Initialize(Context)` | 공통 Character/ASC/Locomotion에 대한 유효한 Game Thread 문맥 연결 |
| `CanEnter(Event) const` | 부작용 없는 진입 가능 검사. 이 함수에서 비용 차감·몽타주 시작 금지 |
| `Enter(Event)` | 자신의 제약 handle·delegate 등 취득 |
| `HandleEvent(Event)` | 관련 사실 변화 처리 및 전이 요청. 자신이 즉시 다른 State를 실행하지 않음 |
| `TickState(DeltaSeconds)` | 해당 상태에 연속 계산이 실제로 필요할 때만 사용 |
| `Exit(Reason)` | 자신이 취득한 것만 정리. 무조건 이동 허용/기본 상태 복구 금지 |

`Context`는 다른 모든 시스템을 호출할 수 있는 만능 서비스 로케이터가 아니다. 해당 상태가 필요한 공통 계약만 제공한다. Player 전용 Cast와 ABP 내부 상태 조회를 넣지 않는다.

### 3.3 전이 처리 규칙

1. Health/상태 효과/연출 요청처럼 권한 있는 소스가 사실 변화를 알린다.
2. FSM은 최신 사실로 목표 제어 상태를 해결한다. 입력 버튼이 직접 `Dead`를 지정하지 않는다.
3. guard를 검사한 뒤 공통 조상 아래의 기존 경로를 leaf부터 Exit한다.
4. 새 경로는 부모부터 Enter한다. 공통 부모는 불필요하게 Exit/Enter하지 않는다.
5. 전이 중 callback에서 들어온 추가 요청은 큐에 넣고 다음 안전한 처리 지점에서 해결한다. 재귀적으로 ChangeState를 호출하지 않는다.
6. 전이 세대 ID를 갱신한다. 이전 상태에서 시작한 비동기 완료는 세대/소유자를 확인한다.
7. 제어 정책 변경을 이동/액션 계층에 알린다. 사망·강제 차단이 대기 중이면 신규 액션 gate도 즉시 이를 반영해야 한다.

State 객체는 Character별로 생성해 UPROPERTY로 보관한다. mutable CDO나 전역 singleton State를 공유하지 않고, 매 프레임 새 State를 생성하지 않는다. 비활성 State 전부를 Tick하지 않는다.

`Status.Stunned` 같은 원인 태그와 `Control.Incapacitated` 같은 FSM 결과 태그는 구분한다. 자신의 결과 태그를 다시 진입 원인으로 삼으면 상태가 영원히 해제되지 않는 순환이 생긴다.

### 3.4 이 트리에 넣지 않는 것

- Walk/Run/Sprint: 이동 축이다.
- Idle/Stop/왼발/오른발: 애니메이션 표현 축이다.
- Attack/Dodge/Skill/Drink: 실행 중인 Ability다.
- Burning/Poisoned/Slow: 함께 존재 가능한 효과/태그다.
- Patrol/Chase/FindAttackPosition: AI의 의사결정이다.
- BossPhase: 보스 전투 진행 축이다.

`Walk_Attack_Poisoned` 같은 조합 State를 만들지 않는다. 여러 독립 축이 동시에 존재하고, 각 소유자가 자신의 규칙을 해결한다.

## 4. 액션 실행 계층: GAS를 채택한다

### 4.1 HFSM과 GAS의 관계

HFSM은 **현재 어떤 종류의 제어를 허용하는가**, Ability는 **승인된 행동 하나를 어떻게 실행하고 끝내는가**를 소유한다.

공격에 `UKhazanAttackState`와 `UGA_KhazanAttack`를 동시에 두고 두 객체가 공격 시작/종료를 관리하는 설계는 채택하지 않는다. Ability 자체가 클래스 기반 실행 단위다. 복잡한 한 액션 내부에만 준비/활성/회복 phase 또는 작은 하위 실행 객체를 둘 수 있다.

Epic의 Gameplay Ability는 조건·비용·비동기 Task·종료/취소를 위한 기반이다. 정상 종료 시 EndAbility를 빠뜨리면 실행 상태가 남는다. 이 기반 위에 프로젝트의 승인/취소 규칙을 추가한다. [공식 Gameplay Ability 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-gameplay-abilities-in-unreal-engine)

### 4.2 소유 클래스

| 타입 | 역할 |
| --- | --- |
| `UKhazanAbilitySystemComponent` | 공통 액션 요청, grant된 Ability 조회, 제어 정책/태그/자원 검사, 실행 채널과 취소 중재 |
| `UKhazanGameplayAbility` | 프로젝트 액션 공통 base. 실행 ID, 종료 이유, 공통 cleanup 계약 |
| `UKhazanGameplayAbility_MeleeAttack` | 근접 공격 실행 방식. 콤보 단계·무기별 클립/계수는 ActionDefinition에서 받음 |
| `UKhazanGameplayAbility_Dodge` | 회피의 비용·유효 구간·이동 구동 요청·종료 |
| `UKhazanGameplayAbility_HitReact` | 피격 반응 실행. 데미지 판정이나 영구 사망 상태의 소유자가 아님 |
| `UKhazanGameplayAbility_Death` | Dead 진입이 내부 경로로 요청하는 사망 액션/연출. 종료해도 Dead를 해제하지 않음 |
| `UKhazanAttributeSet` | 최초 수직 기능 검증에 필요한 체력/스태미나 수치. 추가 속성은 실제 소비 시 추가 |
| Ability Task | 몽타주/이벤트/타깃 수집 등 비동기 실행. 종료 시 delegate와 임시 자원을 정리 |

스킬마다 C++ 클래스를 무조건 만들지 않는다. 실행 방식이 같은 공격은 하나의 Ability 클래스와 여러 ActionDefinition으로 표현한다. 투사체 발사와 잡기처럼 수명/타깃/취소 구조가 다른 행동은 별도 Ability가 타당하다.

v1 ASC는 공통 `AKhazanCharacter`가 소유하며 ActorInfo의 Owner/Avatar도 해당 Character를 기준으로 초기화한다. Player/Monster가 같은 기반을 사용한다. 영속 장비·성장은 별도 Progression 데이터에서 새 Pawn에 적용한다. Lyra의 PlayerState ASC 배치를 그대로 복제하지 않는다.

### 4.3 입력과 AI의 공통 진입 계약

- `AKhazanCharacter::SubmitActionRequest(Request)`: Player/AI가 함께 쓰는 얇은 진입점이다. 자체 거대 switch를 만들지 않고 ASC로 전달한다.
- `FKhazanActionRequest`: Action 식별자, 입력의 시작/해제 등 의미, 타깃/방향 등 해당 행동에 필요한 값, 요청 ID를 담는다. 장치의 FInputActionValue를 몬스터까지 전파하지 않는다.
- ASC는 Action ID → 부여된 Ability Spec/Definition을 명시적으로 찾는다. 현행 `Input.Action.*` 태그만 선언했다고 GAS에 자동 연결되는 것은 아니다.
- 결과는 `Rejected / Buffered / Started` 및 실패 이유/실행 ID로 구분한다. UE의 TryActivateAbility 반환값 하나를 프로젝트의 비용 지불·게임 효과 시작까지 모두 완료했다는 증거로 확대하지 않는다.
- 입력 버퍼는 ASC의 제한된 액션 요청 버퍼가 소유한다. 애니메이션 bool로 보존하지 않는다. 만료/대체 규칙은 데이터로 지정하고, 사망·빙의 해제·Pawn 초기화에서는 비운다.

### 4.4 동시 실행과 취소 규칙

v1은 **주요 신체 액션 채널 하나 + 독립 실행**을 기본으로 한다.

- 근접 공격·회피·전신 피격은 주요 신체 채널에서 서로 중재한다.
- 지속 효과·게임플레이를 방해하지 않는 독립 능력은 공존할 수 있다. 독립 능력은 승인 없이 주요 신체 이동/전신 몽타주를 차지하지 않는다.
- 이동 중 공격 가능 여부는 이동 제약의 문제이며, 공격을 허용하려고 WalkAttack이라는 새 제어 State를 만들지 않는다.
- 추가 상체/하체 액션 채널은 실제 동시 액션 요구가 확인될 때만 확장한다. Montage Slot/Group과 gameplay 실행 채널은 다른 개념이다.
- 취소 창은 현재 실행의 phase/태그와 ActionRelationship 데이터로 판단한다. “새 액션의 숫자 priority가 크면 무조건 취소”만으로 처리하지 않는다.
- 가벼운 피격이 모든 공격을 중단시키지는 않는다. 슈퍼아머는 피격 반응 억제와 관련 있고 무적은 피해 수락과 관련 있다. 같은 bool로 합치지 않는다.
- 일반 취소 창을 닫기 위해 모든 주요 Ability에 `SetCanBeCanceled(false)`를 남발하지 않는다. 일반 취소는 프로젝트 중재 정책에서 막고, 사망 등 시스템 종료 경로로 정리 가능한 실행을 유지한다.
- Dead/Incapacitated에서도 허용되는 사망/강제 피격 반응은 권한 있는 내부 요청으로만 실행한다. 일반 입력이 gate를 우회하는 공개 “강제 실행” 옵션을 갖지 않는다.

Lyra의 Activation Group과 Tag Relationship Mapping은 참고할 공식 샘플 패턴이다. **그 그룹/매핑 정책은 Lyra의 확장이며, GAS 플러그인을 켜면 Khazan에도 자동 생기는 기능이 아니다.** 여기의 신체 채널과 취소 정책은 Khazan에서 구현할 계약이다. [Lyra Ability 구조](https://dev.epicgames.com/documentation/en-us/unreal-engine/abilities-in-lyra-in-unreal-engine)

### 4.5 액션 수명과 실패 처리

```text
요청
 → 준비 검사: Ready / 제어 정책 / Ability 보유 / 태그 / 자원 / 취소 가능
 → 채널 전환 승인
 → 필요한 기존 액션 취소·정리
 → 새 Ability 시작 및 Commit 성공 확인
 → 몽타주·이동 제약·적중 창 등 실제 실행
 → 정상 완료 / 취소 / 실패
 → 동일한 공통 cleanup 경로
```

- 사전 검사에서 실패한 요청은 현재 액션을 취소하지 않는다.
- 사전 검사와 실제 Commit 사이의 상태 변화 가능성은 남는다. GAS가 “기존 행동 취소와 새 비용 적용”을 자동 원자적 트랜잭션으로 처리한다고 가정하지 않는다.
- v1 실패 정책: 전환 중 재검사/Commit 실패 시 새 실행을 종료하고 자신이 얻은 채널/제약을 회수한다. 이미 취소된 이전 공격을 부활시키지 않고 현재 제어 정책 아래의 유효한 기본 동작으로 돌아간다.
- 최초 비용은 실제 공격 판정/회피 이동 같은 되돌리기 어려운 효과보다 먼저 성공해야 한다. 취소 후 환불은 자동이 아니라 해당 ActionDefinition의 명시적 규칙이다.
- 일반 종료/취소/몽타주 실패/장비 제거/EndPlay 모두 적중 창, delegate, timer, 이동 제약, 임시 효과 handle을 정리한다.
- cleanup은 두 번 들어와도 안전해야 한다. `EndAbility` 호출과 외부 callback 재진입의 순서를 구현 시 시험한다.
- 실행마다 `ActionExecutionId`를 부여한다. Ability 객체를 재사용해도 이전 실행의 callback은 새 실행을 종료하지 못한다.
- v1 주요 액션은 캐릭터별 인스턴스 재사용을 기본으로 검토하고 재진입을 중재한다. 실제 동시 실행이 필요한 Ability만 그 요구에 맞는 instancing을 선택한다.
- 몽타주 재생의 성공/실패/완료/중단 수명은 Ability Task가 관리한다. AnimInstance Tick에서 별도 “공격 남은 시간”을 감소시키지 않는다.

## 5. 공통 이동 계층: LocomotionComponent를 실제 제어자로 만든다

### 5.1 Player에서 옮길 것과 남길 것

- Player에 남김: 스틱 dead zone, Walk/Run 입력 경계, L3 토글/홀드, 카메라 Yaw 기준 월드 방향 변환.
- LocomotionComponent로 이관: 요청 gait와 여러 허용 상한 해결, 속도/가감속 설정 적용, 회전 정책, 이동 제약 및 SprintPivot 수명.
- CMC에 유지: 가속·제동 적분, 충돌, 바닥 판정, MovementMode, 루트 모션과 캡슐 이동의 엔진 경로.
- AI: PathFollowing의 목적지/진행 요청을 사용하되 같은 gait/제약 정책을 적용한다. AI 이동을 Player의 스틱 함수나 L3로 흉내 내지 않는다.

정규화된 방향으로 고정 목표 속도를 사용하는 현재 Player 조작은 보존한다. AI PathFollowing이 요청하는 감속/도착 동작까지 Player AddMovementInput 경로로 강제 통일하지 않는다.

### 5.2 의도·제약·해결 결과를 분리한다

| 데이터 계약 | 작성자 | 의미 |
| --- | --- | --- |
| `FKhazanLocomotionIntent` | 현재 유효한 Player/AI 입력 어댑터 | 어느 방향으로 어떤 gait를 원하는가 |
| `FKhazanMovementConstraint` | State/Ability/상태 효과 연결부 | 해당 원인이 요구하는 이동 입력 차단, gait 상한, 회전/이동 구동 조건 |
| `FKhazanMovementConstraintHandle` | LocomotionComponent | 특정 원인의 제약을 나중에 정확히 해제할 식별자 |
| `FKhazanResolvedMovementPolicy` | LocomotionComponent만 | 모든 현재 원인을 반영한 적용 결과 |
| CMC의 Velocity/MovementMode | 엔진 | 의도와 무관하게 실제 일어난 이동 |

위 새 타입은 설계 이름이다. 실제 필요한 필드만 첫 기능에서 만들며 설정 묶음을 먼저 거대하게 만들지 않는다.

예: 공격과 기절이 모두 이동을 제한하는 중 공격이 끝나면 **공격 handle만 제거**한다. 기절 handle이 남으므로 이동은 계속 제한된다. `SetMovementAllowed(true)`를 두 시스템이 공유하는 방식은 이 경우 안전하지 않다.

- 이동 입력 허가는 관련 제약의 논리적 합성으로 정한다. 입력 차단과 기존 속도 제거, 중력 중단은 별개다.
- gait는 요청과 모든 유효 상한 중 가장 제한적인 결과다. 현재 enum 순서에 의존한다면 순서 계약/테스트를 유지한다.
- 제약 변경은 스틱 이벤트 없이도 다시 해결·적용한다. 입력이 없는 동안 공격/기절이 끝났는데 CMC 설정이 오래 남아서는 안 된다.
- 원시 이동 의도와 허용된 이동 명령을 구분한다. 공격 중 스틱을 계속 기울인 경우를 구현할 때, 장치 Released와 정책 차단을 같은 사건으로 덮어쓰지 않는다.
- 방향 구동의 최종 선택은 제어 상태의 강제 정책 > 승인된 액션 이동 > Pivot > 일반 이동 순으로 중재한다. 이것은 v1 소유권 정책이며 원작 수치가 아니다.
- 회전도 같은 소유권 규칙을 따른다. 기본 OrientRotationToMovement, 액션 타깃 회전, Pivot 수동 회전이 같은 프레임에 경쟁하지 않는다.
- 상태 효과 태그의 중첩 수명은 ASC/GameplayEffect handle·count에 맡긴다. 단순 FGameplayTagContainer 하나의 Add/Remove만으로 여러 효과의 소유권을 대신하지 않는다.

### 5.3 SprintPivot의 최종 배치

SprintPivot은 **LocomotionComponent 내부의 이동 하위 동작**이다.

1. 새 의도와 실제 진행 방향의 반전 조건을 이동 계층이 판단한다.
2. Pivot 진입 방향·구동 phase·실행 식별자를 해당 동작의 문맥에 고정한다.
3. LocomotionComponent가 제동/방향 handoff와 CMC 회전 정책을 제어한다.
4. 애니메이션에는 Pivot이 활성인지와 필요한 phase/시간 관측만 전달한다.
5. Locomotion Linked Layer는 일반 Stop이 아닌 Pivot 표현 상태에서 Sprint Stop 클립을 사용한다.
6. Pivot이 끝나면 유효한 현재 의도를 다시 해결해 Sprint 등 허용된 이동으로 이어 간다. 처음 저장한 요청을 무조건 재실행하지 않는다.
7. 피격·사망·회피가 Pivot을 중단하면 자신의 구동만 해제하고 상위 제약은 보존한다.

`MovementDirectionAngle`은 “Actor 정면 대비 실제 속도 방향”, Pivot 반전 검사는 “진행 방향 대비 새 이동 의도”다. 서로 다른 양이다. 후자를 만들기 위해 Main AnimInstance에 새로운 입력각 float부터 추가하지 않는다. 필요한 계산은 이동 동작의 소유 함수에서 지역 계산으로 시작한다.

Pivot phase와 표현 구간이 연결될 때는 하나의 gameplay phase 계약을 소비한다. 서로 독립적인 C++ timer와 ABP 자동 종료가 모두 다음 gameplay 상태를 결정해서는 안 된다. 사용할 구간/시간/재생률은 이후 InGame 원본과 수치 출처를 확인하며 설계한다.

### 5.4 Root Motion과 갱신 순서

- 현재 locomotion/Stop은 in-place + CMC를 유지한다. SprintPivot도 이 기준에서 설계한다.
- 회피/공격은 해당 ActionDefinition에서 in-place 구동 또는 Montage Root Motion 사용 여부를 명시한다. 에셋마다 확인 없이 일괄 활성화하지 않는다.
- Root Motion 액션은 승인된 이동 구동권 안에서 CMC 경로를 사용한다. 같은 시간에 임의 SetActorLocation/Velocity와 경쟁시키지 않는다.
- 우선 CMC의 기존 기능으로 구현한다. 커스텀 물리/회전 통합 지점이 실제로 필요해질 때만 CMC subclass를 추가한다.
- 입력/제약 변경 반영은 CMC가 해당 이동을 소비하기 전에 이뤄져야 한다. 애니메이션은 해당 업데이트에서 확정된 gameplay 관측을 수집한다.
- 이 문장은 엔진의 모든 모드에 절대적인 Tick 순서가 있다는 뜻이 아니다. 실제 component tick prerequisite와 애니메이션 갱신 시점은 통합 단계에서 계측한다. AnimInstance 업데이트에서 gameplay 이동을 변경해 순서를 우회하지 않는다.

## 6. AnimInstance/ABP 분리

### 6.1 채택할 배치

```text
UKhazanAnimInstance : UAnimInstance
└─ 가족별 Main ABP (현재 ABP_Player가 첫 대상)
   ├─ Linked Anim Layer: LocomotionPose
   │  └─ UKhazanLocomotionAnimInstance : UAnimInstance
   │     └─ 가족별 ABP_LocomotionBase
   │        ├─ Grounded: Idle / WalkRun / Sprint / Stop / WalkTurn / SprintPivot
   │        └─ Airborne: 해당 가족이 실제 지원하는 상태
   ├─ Montage Slot / 필요한 전신·부분 신체 합성
   └─ 검증된 IK / additive / 후처리
```

`UKhazanLocomotionAnimInstance`는 Main의 gameplay 수집/계산 lifecycle을 통째로 상속·복제하지 않는다. 두 클래스는 서로 다른 역할의 인스턴스다.

v1은 **Locomotion 상태 머신 전체를 하나의 locomotion linked instance 안에 둔다.** Idle/Move/Stop을 임의의 여러 인스턴스로 먼저 쪼개지 않는다. loop/Stop 이력과 Sync Group 조회의 소유 범위를 일치시키기 위함이다.

### 6.2 Main의 역할

- `UKhazanAnimInstance`의 기존 Game Thread 참조 수집/snapshot 경계를 유지한다.
- CMC의 실제 운동과 gameplay에서 확정된 제어/액션/이동 상태 중 실제 표현에 필요한 것만 수집한다.
- 공통 관측을 한 번 계산해 레이어에 공급한다. 레이어마다 Character/CMC/ASC를 Cast하고 다시 수집하지 않는다.
- 입력 해석, 액션 가능 판정, 스태미나 차감, 공격 hit 검사, CMC 설정 변경을 하지 않는다.
- Main ABP는 LocomotionPose, 액션 Slot, 보정 합성을 연결한다. 공격마다 새로운 전역 bool와 전신 State Machine 노드를 추가하지 않는다.

### 6.3 Locomotion 인스턴스의 역할

- 실제 속도에 따른 loop gait 선택/히스테리시스.
- 현재 사용자 구현의 Stop 진입 gait·발 고정과 관련 이력.
- Walk Turn 좌/우 포즈, SprintPivot용 클립/블렌드와 표현상 전이.
- locomotion 전이용 bool/enum 및 유효성/Reset.
- 해당 움직임 세트가 소비하는 데이터만 소유한다. 공격 콤보, 스태미나, 피격 면역을 넣지 않는다.

`LocomotionGait`는 시각적 loop 선택이고 `ResolvedGait`는 이동 정책 결과다. 이름만 비슷하다고 하나로 합치지 않는다.

`StopGait`/`StopEntryFoot`는 진입 시 고정되는 표현 데이터다. 매 프레임 현재 gait/발로 덮어쓰지 않는다. 레이어 재생성/무기 교체/메시 변경/유효 snapshot 상실 시 이전 이력을 폐기한다.

슬롯에 가려진 동안의 오래된 입력 해제 펄스가 액션 종료 뒤 새 Stop으로 재생되지 않도록 relevancy와 요청 유효성을 정의한다. gameplay 이벤트를 한 animation update짜리 bool에만 맡기지 않는다.

### 6.4 Linked Layer와 애니메이션 데이터

- 목표 인터페이스 `ALI_KhazanCharacterAnimation`의 최초 경계는 `LocomotionPose`다. 미사용 UpperBody/Aim/IK 인터페이스를 미리 모두 만들지 않는다.
- locomotion 관련 인터페이스 layer를 추가할 때 같은 비기본 그룹 `LocomotionLayers`를 사용해 필요한 인스턴스 공유를 명시한다.
- 인터페이스의 Group과 발 marker의 Sync Group `Locomotion`은 서로 다른 설정이다.
- Walk/Run/Sprint/Stop의 marker 조회와 재생은 같은 locomotion 인스턴스에서 검증한다. 링크만 했다고 다른 인스턴스의 marker phase까지 자동 공유된다고 가정하지 않는다.
- 같은 skeleton/구조에서 무기별 clip만 다르면 데이터/child defaults만 바꾼다. Main ABP와 상태 머신을 통째로 복제하지 않는다.
- 구조가 실제로 다르면 해당 가족의 layer 구현을 교체한다.
- 서로 다른 skeleton·체형의 몬스터에게 같은 ABP 에셋을 무조건 사용시키지 않는다. 공통 gameplay/C++ 관측 계약은 공유하고 skeleton/이동 가족별 Main/Locomotion ABP를 둔다.
- 장비 교체 때만 필요한 레이어를 준비하고 링크한다. 매 Tick LinkAnimClassLayers를 호출하지 않는다. unlink만으로 메모리가 반드시 해제되는 것은 아니므로 asset handle 수명도 관리한다.

Linked Anim Layer는 인터페이스와 별도 ABP로 구현을 나누는 엔진 기능이다. 인스턴스 공유 그룹 및 unlink 후 메모리 처리는 명시적으로 구성해야 한다. [공식 Animation Blueprint Linking 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-linking-in-unreal-engine)

### 6.5 스레드와 데이터 전달

- Main Game Thread 수집 → 엔진이 관리하는 animation update → 공통 파생 관측 → linked node 입력/Property Access → 해당 layer의 node update 순으로 사용할 데이터 의존성을 설계한다.
- 현행 `FKhazanAnimGameThreadData`는 raw snapshot 계약이다. 새 `FKhazanAnimFrameData`를 도입한다면 실제 레이어 소비 필드만 묶는 읽기용 표현 계약이지 gameplay의 두 번째 상태 저장소가 아니다.
- worker에서 ASC/Character/LocomotionComponent를 직접 조회·수정하지 않는다. TObjectPtr 캐시나 `BlueprintThreadSafe` 표시만으로 안전해지지 않는다.
- linked node 입력/Property Access의 복사 시점과 Main/Linked 업데이트 순서를 UE 5.8에서 검증한다. 필요한 경우 엔진의 proxy/PreUpdate 경계를 사용하며, 임의 공유 메모리에 복사하는 것으로 동기화를 대신하지 않는다.
- 레이어가 아직 갱신되지 않은 입력을 NativeThreadSafeUpdateAnimation에서 읽지 않도록 실제 node 함수 호출 시점까지 확인한다.
- On Become Relevant는 포즈 선택/초기화에 사용한다. gameplay 액션 시작이 정확히 한 번 발생한다는 보장은 아니므로 액션 시작/데미지 적용 위치로 사용하지 않는다.

Lyra는 Main 데이터 재사용, Linked Layer, Anim Node Functions의 실례다. 여기에서는 그 모듈화 원리를 참고하며 Lyra의 Start, 무기 발사, 회전 수치를 그대로 가져오지 않는다. [Lyra 애니메이션 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine)

### 6.6 몽타주·Notify·적중의 경계

- Ability/Task가 액션 몽타주의 실행 수명을 소유하고 ABP Slot이 포즈를 합성한다.
- 소울라이크 근접 공격을 무조건 상체 레이어로 제한하지 않는다. 전신/부분 신체 정책은 액션과 실제 클립에 맞춘다.
- Sync Marker는 포즈 동기화용이다. 공격 가능 창, 무적 창, 타격 판정을 foot marker에서 추론하지 않는다.
- Notify/NotifyState는 실행 중 액션에 식별 가능한 이벤트를 전달할 수 있다. 최종 gameplay 적용은 살아 있는 해당 실행의 Task/CombatComponent가 검증한다.
- Notify/NotifyState 에셋 객체에 캐릭터별 hit 대상 목록·제약 handle을 저장하지 않는다. mutable 실행 데이터는 Character/Ability/Task 문맥이 소유한다.
- 애니메이션 중단으로 Notify End가 오지 않는 경우에도 Ability 종료에서 적중 창과 제약을 닫는다.
- 골격 pose/notify/root motion이 전투 판정에 필요한 동안에는 그 평가를 보장하는 budget 정책을 둔다. 화면 밖이라는 이유로 평가를 생략하면서 같은 정확도의 무기 socket 타격이 보장된다고 주장하지 않는다.

## 7. enum·bool·태그·State 클래스를 선택하는 기준

| 표현 | 사용할 경우 | Khazan 예 |
| --- | --- | --- |
| enum | 같은 축에서 하나만 선택되는 유한 상태 | Gait, Foot, 제어 상태 ID, 한 액션 내부 phase |
| bool | 독립된 사실/판정 결과 | bIsGrounded, 유효 snapshot 여부 |
| GameplayTag/Effect | 동시에 존재 가능한 분류·효과·요구 조건 | 독, 슈퍼아머, 액션 분류, 입력 식별자 |
| State 클래스 | 독립적인 Enter/Exit와 자원/제어 수명 | Operational, Incapacitated, Scripted, Dead |
| Ability 클래스 | 비용·취소·타깃·비동기 실행 수명 | 공격, 회피, 스킬, 피격 반응 |
| AnimGraph State | 포즈 재생과 블렌딩의 독립 수명 | Idle, Stop, WalkTurn, SprintPivot |
| DataAsset/구조체 | 실행 구조는 같고 설정/콘텐츠만 다름 | 무기별 공격 정의, 몬스터별 이동 세트 |

bool 개수 자체가 설계 품질이나 성능을 결정하지 않는다. `bIsWalking/bIsRunning/bIsSprinting`을 모두 독립적으로 수정하면 모순이 가능하지만, enum에서 필요한 읽기 전용 전이 bool을 파생하는 것은 허용한다.

enum 기반 pose 선택이나 간단한 비교를 금지하지 않는다. Fast Path 여부는 실제 노드와 Property Access/컴파일 결과로 확인한다. 몇 개의 비교를 없애기 위해 동일 상태를 여러 mutable bool로 저장하지 않는다. 최적화 대상은 프로파일 결과로 결정한다. [Epic 애니메이션 최적화 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-optimization-in-unreal-engine)

### 주요 데이터의 수명 계약

| 값/문맥 | 작성자 | 갱신·고정 | 폐기/Reset |
| --- | --- | --- | --- |
| Player의 Sprint 요청 | 입력 어댑터 | L3 정책/장치 입력 변화 | 해제·취소·빙의 해제 등 조작 계약 |
| RequestedGait/이동 의도 | Player 또는 AI 어댑터 | 유효 명령 변화 | 명령 취소·소유 제어기 교체 |
| ResolvedMovementPolicy | LocomotionComponent | 의도/제약/구동권 변화 | 재초기화 때 현재 원인으로 재해결 |
| ControlState ID/Policy | FSM | 검증된 상태 전이 | Pawn 종료. 외부에서 ID를 직접 Set하지 않음 |
| ActionExecutionId/Action 문맥 | ASC + 해당 Ability | 승인된 실행 시작 | 종료 시 무효화, 늦은 callback 거부 |
| 공격 phase/ComboIndex | 실행 중 Attack Ability | 그 공격의 이벤트/단계 변화 | 해당 실행 종료 |
| 적중한 대상 목록 | CombatComponent의 실행/타격 창 문맥 | 해당 창의 검증된 적중 | 창/액션 종료; 에셋 전역에 저장 금지 |
| LocomotionGait | Locomotion AnimInstance | 관측 기반 loop 선택 | 레이어 초기화/유효성 상실 |
| StopGait/StopEntryFoot | Locomotion AnimInstance | 유효 Stop 진입 관측 시 고정 | 새 진입 또는 이력 무효화 |
| Pivot 방향/phase/실행 ID | LocomotionComponent | gameplay Pivot 실행 동안 | 종료/취소/제어권 상실 |
| BossPhase | BossPhaseComponent | 검증된 전투 진행 이벤트 | encounter reset 계약 |
| CharacterDefinition | 공유 읽기 전용 데이터 | 준비된 정의 적용 | 정의 교체/참조 해제; 런타임 상태 수정 금지 |

## 8. 데이터 기반 캐릭터 구성과 초기화

### 8.1 데이터의 계층

- `UKhazanCharacterDefinition : UPrimaryDataAsset`
  - 공통 Character 구성의 진입 데이터.
  - Mesh/skeleton 가족, Main ABP/locomotion 구현, 기본 이동 설정, 기본 AbilitySet, 초기 attribute 데이터, 필요한 AI 정의를 참조한다.
  - “이 캐릭터가 누구이며 어떤 기능 묶음을 사용하는가”를 표현한다. 현재 HP/현재 공격 phase를 저장하지 않는다.
- `UKhazanActionDefinition : UPrimaryDataAsset`
  - 실행 Ability 클래스, Action ID/분류, 비용/쿨다운, 이동/회전 정책, Montage/Section, 타격/취소 구간의 데이터.
  - 액션 구조가 다르면 전용 정의 subtype/설정 구조체를 사용한다. 모든 종류의 스킬을 하나의 거대한 optional 필드 묶음으로 강제하지 않는다.
- `UKhazanAbilitySet : UDataAsset`
  - 부여할 Ability/초기 효과/필요한 속성 묶음. grant 결과 handle을 부여 주체가 추적한다.
- `UKhazanActionRelationshipData : UDataAsset`
  - 액션 분류 간 block/cancel/require 관계. 실행 중 취소 창과 결합해 승인한다.
  - 일반 정책을 여러 Ability에 복사하지 않는다. 개별 능력만의 타깃/지형 조건은 해당 Ability가 검사한다.
- `UKhazanLocomotionAnimSet : UDataAsset`
  - 같은 그래프 구조에서 바뀌는 InGame clip/BlendSpace 참조와 실제 필요한 표현 튜닝.
  - 현재 사용 중인 Sequence/enum 조합을 보존한다. 이 설계 때문에 BlendSpace1D나 Motion Matching으로 교체하지 않는다.
- 장비 정의
  - 장착 Mesh, 부여할 AbilitySet/ActionDefinition, 애니메이션 세트/필요한 layer 구현 참조.
  - 실제 장비 기능 단계에서 타입을 만든다. 무기마다 공통 Character를 상속한 새 C++를 만들지 않는다.

정의 에셋의 수치에는 원작 직접값/원작 기반 계산값/임시 튜닝값을 식별할 수 있는 설명·metadata/report 연결을 남긴다. 모든 float를 복잡한 provenance 런타임 객체로 감쌀 필요는 없지만, 어느 자료에서 어떤 단위/조건으로 가져왔는지 추적 가능해야 한다.

### 8.2 준비·장착·해제 순서

1. 공통 Character가 기본 컴포넌트를 생성한다. 액션/이동 입력 수락은 Ready 전까지 닫는다.
2. 기존 `UKhazanAssetManager`를 통해 선택한 CharacterDefinition의 필요한 에셋을 준비한다. 별도 만능 AssetManager를 만들지 않는다.
3. ASC ActorInfo/속성/기본 능력, 이동 기본 설정, 애니메이션 가족, AI 준비를 의존 순서대로 연결한다.
4. 필수 준비가 끝나면 명시적 Ready 신호로 입력/AI 실행을 연다. 여러 BeginPlay의 우연한 호출 순서에 기대지 않는다.
5. 장비 변경은 해당 변경 요청의 세대 ID를 갖는다. 이전 비동기 로드 완료가 최신 장비를 덮어쓰지 못한다.
6. 실행 중 액션과 충돌하는 장비 교체는 미루거나 정책에 따라 취소한 뒤 교체한다. 이전 Ability/Effect grant handle과 asset handle만 제거한다.
7. 참조 중인 액션/레이어가 남아 있는 동안 필요한 에셋을 해제하지 않는다. 미로드 에셋은 안전한 fallback 또는 명시적 요청 실패로 처리한다.
8. EndPlay/빙의 해제 시 입력 버퍼, 실행, delegate, 로드 callback과 장비 부여 수명을 정리한다.

전체 캐릭터·무기·보스 에셋을 공통 base의 hard reference로 연결하지 않는다. 필요한 가족/장비의 soft reference를 준비 시점에 로드하고 유효한 사용 수명 동안 보존한다. 매 Tick 동기 로드는 금지한다.

## 9. 전투·AI·보스·레벨의 확장 경계

### 9.1 CombatComponent

`UKhazanCombatComponent`는 “공격을 해야 하는가”가 아니라 **실행 중 공격의 타격 검사**를 담당한다.

- Ability가 실행 ID와 공격 정의를 사용해 적중 창을 연다.
- CombatComponent가 무기/타격 형상, 팀/대상 유효성, 같은 창의 중복 적중을 검사한다.
- 유효 타격 결과를 ASC의 피해/효과 경로에 전달한다. Player와 Monster의 별도 HP 차감 코드를 만들지 않는다.
- 피해 수락, 무적, 슈퍼아머, 경직 강도는 구분한다. 피해 처리 결과에 따라 필요한 HitReact/강제 제어 변경을 요청한다.
- 실제 socket pose에 의존하는 추적은 pose 갱신 이후의 Game Thread 검사 시점을 보장한다.
- 액션 종료 시 그 실행의 모든 적중 창을 닫는다. 다른 실행의 창을 실수로 닫지 않는다.

Lock-on/Targeting은 타깃 선택과 유지가 실제 구현되는 시점에 별도 책임으로 추가한다. AnimInstance의 MovementDirectionAngle이 적 선택이나 락온 수명을 소유하지 않는다.

### 9.2 AI와 일반 몬스터

v1 AI 의사결정은 **AIController + Behavior Tree/Blackboard**를 사용한다. 동일 캐릭터를 BT와 StateTree가 동시에 지휘하게 만들지 않는다.

- BT: 순찰, 추적, 위치 선정, 사용할 Action ID 선택.
- PathFollowing: 이동 목적지와 경로 추종. 실제 이동 허용/gait/구동 경쟁은 공통 이동 계약에 종속된다.
- 공통 ASC: 선택한 액션의 가능 여부·실행·종료.
- BT의 액션 Task: 자신이 제출한 실행 ID의 결과를 기다린다. 실패/Abort 때 자신의 요청만 취소하고 다른 시스템의 피격·사망 액션을 종료하지 않는다.
- Blackboard: 판단용 캐시다. 별도 체력/현재 액션의 최종 원본이 아니다.
- 대부분의 적 변형: CharacterDefinition, AbilitySet, ActionDefinition, AI 데이터, 애니메이션 가족 조합으로 구성한다.
- 새로운 locomotion 형태나 전투 실행 구조가 있을 때만 해당 capability/가족 구현을 추가한다.

Behavior Tree/Blackboard는 AI 판단과 그 판단 데이터의 분리를 제공한다. 여기서 BT는 신체 액션 실행 FSM을 대체하지 않는다. [공식 Behavior Tree 개요](https://dev.epicgames.com/documentation/en-us/unreal-engine/behavior-tree-in-unreal-engine---overview)

### 9.3 보스

- `UKhazanBossPhaseComponent`는 체력/부위 파괴/전투 이벤트에 따른 페이즈 전이를 소유한다.
- 페이즈에 따라 사용 가능한 패턴/가중치/능력 구성을 바꾸며 BT는 그 결과를 소비한다.
- 패턴 실행 자체는 공통 Ability/Task/이동/전투 계약을 사용한다.
- 특정 보스만의 다단 패턴은 전용 Ability나 그 패턴의 작은 실행 객체에 둔다. Main AnimInstance에 `BossType == ...` 분기를 추가하지 않는다.
- 페이즈 전환 연출이 필요하면 Scripted 제어 요청과 전용 액션을 사용한다. 그 종료 callback이 HP 기반 페이즈를 되돌리지 않는다.
- 보스 숫자가 늘어난다고 공통 CharacterStateMachine에 보스 이름별 State를 추가하지 않는다.

### 9.4 HeinMach/StormPass와 진행 저장

- `AKhazanEncounterDirector`: 해당 전투 구역의 시작/종료, 웨이브/스폰 요청, 배리어·보상 등 gameplay 진행을 소유하는 목표 Actor.
- `AKhazanCheckpoint`: 상호작용과 체크포인트 선택/리셋 요청의 월드 진입점.
- `UKhazanProgressionSubsystem : UGameInstanceSubsystem` + `UKhazanSaveGame`: 현재 run/영속 진행 중 저장할 데이터의 단일 소유 경로.
- 기존 GameMode: 플레이 세션의 스폰/리스폰 조정. 모든 encounter의 내부 패턴을 직접 구현하지 않는다.
- World subsystem은 월드 전체 검색/등록의 실소비가 필요할 때 추가한다. 처음부터 같은 스폰을 관리하는 Director와 subsystem을 중복 생성하지 않는다.
- 저장은 EncounterId/CheckpointId/CharacterDefinition 같은 안정된 식별자를 사용한다. Actor 포인터, AnimInstance 상태, Ability 실행 객체를 저장하지 않는다.
- 체크포인트 리셋 때 복원할 적·보스·획득물의 범위는 원작 자료와 gameplay 요구에서 결정한다. 이번 설계는 그 수치/세부 규칙이 검증됐다는 뜻이 아니다.
- UI/카메라/오디오/VFX는 gameplay 사건과 attribute를 소비한다. 화면 이펙트 완료가 유일한 데미지 또는 사망 판정 근거가 되지 않는다.

## 10. 목표 파일 배치와 생성 시점

다음은 파일의 책임 위치다. **한 번에 전부 생성하라는 작업 목록이 아니다.** 아래 A 단계의 실제 소비가 생길 때 생성한다. 기존 경로는 불필요하게 이동/rename하지 않는다.

| 위치 | 파일/타입 | 상태와 최초 단계 |
| --- | --- | --- |
| `Character/KhazanCharacter.*` | 공통 조립/초기화/얇은 요청 전달 | 기존 유지·확장, A1/A2 |
| `Character/KhazanPlayer.*` | 장치 입력 의도/카메라 | 기존 유지·공통 이동 적용 이관, A1 |
| `Character/KhazanMonster.*` | 몬스터 공통 진입점 | 기존 유지, A1/A2 |
| `Character/Component/KhazanLocomotionComponent.*` | 공통 이동 정책·제약·Pivot | 기존 확장, A1/A5 |
| `Character/Locomotion/KhazanLocomotionType.*` | 이동 의도/gait/제약 관련 공통 타입 | 기존 확장, A1 |
| `Character/Component/KhazanCharacterStateMachineComponent.*` | 제어 HFSM | 신규, A1 |
| `Character/State/KhazanCharacterState.*` | State base/context 계약 | 신규, A1 |
| `Character/State/KhazanStateAlive.* / KhazanStateOperational.*` | 최초 제어 경로 | 신규, A1 |
| `Character/State/KhazanStateIncapacitated.* / KhazanStateDead.*` | 실제 피격/사망 제어 | 신규, A2 |
| `Character/State/KhazanStateScripted.*` | 실제 연출 제어 수명 | 신규, A6에서 필요한 시점 |
| `AbilitySystem/KhazanAbilitySystemComponent.*` | 공통 액션 중재 | 신규, A2 |
| `AbilitySystem/KhazanGameplayAbility.*` | 액션 실행 공통 base | 신규, A2 |
| `AbilitySystem/KhazanAttributeSet.*` | HP/스태미나 및 최초 효과 기반 | 신규, A2 |
| `AbilitySystem/Abilities/KhazanGameplayAbility_MeleeAttack.*` | 근접 공격 실행 | 신규, A2 |
| `AbilitySystem/Abilities/KhazanGameplayAbility_HitReact.* / KhazanGameplayAbility_Death.*` | 피격/사망 액션 | 신규, A2 |
| `AbilitySystem/Abilities/KhazanGameplayAbility_Dodge.*` | 회피 실행 | 신규, A4 |
| `AbilitySystem/Tasks/` | 내장 Task로 부족한 실제 재사용 동작만 | 필요 시. 빈 wrapper 선행 생성 금지 |
| `Character/Component/KhazanCombatComponent.*` | 타격 창·대상 검증 | 신규, A2 |
| `Character/Component/KhazanEquipmentComponent.*` | 장비/부여 handle/에셋 수명 | 신규, A4 |
| `Character/Component/KhazanBossPhaseComponent.*` | 보스 페이즈 | 신규, A6 |
| `Animation/KhazanAnimInstance.*` | Main 공통 관측 | 기존 축소, A3 |
| `Animation/KhazanLocomotionAnimInstance.*` | locomotion 표현과 이력 | 신규, A3 |
| `Animation/KhazanAnimTypes.h` | 실제 공유할 읽기용 frame 계약 | 필요 필드 확정 후, A3 |
| `Data/KhazanCharacterDefinition.*` | Character 구성 데이터 | 신규 최소형, A1부터 확장 |
| `Data/KhazanActionDefinition.* / KhazanAbilitySet.* / KhazanActionRelationshipData.*` | 액션 설정/부여/관계 | 신규 최소형, A2 |
| `Data/KhazanLocomotionAnimSet.*` | locomotion 세트 설정 | 신규, A3 |
| `AI/KhazanAIController.* / AI/Tasks/` | 판단과 공통 액션 Task | 신규, A1/A2 |
| `World/Encounter/KhazanEncounterDirector.* / World/Checkpoint/KhazanCheckpoint.*` | 전투 구역/체크포인트 gameplay | 신규, A6 |
| `System/KhazanProgressionSubsystem.* / Save/KhazanSaveGame.*` | 진행 상태/저장 | 신규, A6 |
| `System/KhazanAssetManager.*` | 기존 로딩 기반 활용 | 필요 범위에서만 확장 |
| `Khazan.Build.cs / Khazan.uproject` | GAS 및 AI 모듈/플러그인 연결 | A2/A1에 실제 필요 모듈 확인 후 변경 |

경로 표는 `Source/Khazan` 기준이다. 신규 BP/데이터 에셋 이름도 해당 단계에서 실제 경로를 정한다. 현재 프로젝트의 `Bluprints` 철자를 자동 교정하거나 기존 에셋을 이 설계 때문에 한꺼번에 이동하지 않는다.

## 11. 현재 코드에서 이관할 내용

현재 기준선은 [검토 리포트](../../Saved/ImportReports/Khazan_Character_Architecture_Review_20260908.json)와 로코모션 정본이다. 이번 설계 작업에서 Source/Config/uproject/ABP_Player 39개 파일 hash가 앞선 검토 기준과 동일함을 확인하고 주요 소스를 다시 읽었다. ABP를 이번에 새로 실행/컴파일한 것은 아니다.

| 현재 위치/심볼 | 처리 방향 | 보존/주의 |
| --- | --- | --- |
| Player `RefreshLocomotionGait` | 입력의 RequestedGait 선택은 Player, 해결 결과의 CMC 적용은 LocomotionComponent로 분리 | 스틱 크기와 2단 목표 속도 조작을 보존 |
| Player 생성자/BeginPlay의 이동 튜닝 | 공통 CharacterDefinition/Locomotion 적용 경로로 이관 | 카메라/mesh 보정까지 함께 옮기지 않음 |
| Component `SetMovementAllowed` | 원인별 제약 API와 최종 해결 결과로 교체 | 입력 없음과 행동 금지를 구분; 일괄 bool 해제 금지 |
| `SetMaxAllowedGait / SetRotationMode` | 요청 변화가 실제 공통 이동 정책에 반영되게 함 | 단순 저장소에 머물지 않음 |
| Main `GatherGameThreadData` | 공통 snapshot 수집 유지·소비 없는 필드 축소 | UObject 수집은 GT |
| `UpdateKinematics_AnyThread` | 공통 운동 관측과 locomotion 전용 선택을 분리 | 한 함수를 통째로 다른 거대 클래스에 이동하는 것으로 끝내지 않음 |
| `UpdateLocomotionSelection_AnyThread` | Locomotion AnimInstance로 이관 | loop gait 히스테리시스 의미 보존 |
| `UpdateTransitionData_AnyThread` | Locomotion AnimInstance로 이관 | Stop 진입 edge/직전 gait/발 고정의 현재 검증 보존 |
| `SelectStopEntryFoot_AnyThread` | Sync Group을 실제 소유하는 locomotion instance로 이관 | 가장 가까운 marker는 접지 정답의 보장이 아님 |
| `LocomotionGait / StopGait / StopEntryFoot` | locomotion 표현 문맥으로 이동 | BP 연결/초기화/Reset 함께 변경 |
| `MovementDirectionAngle / VelocityLocal` | 현재 소비 없는 경로는 참조 확인 후 제거 후보 | 미래 스트레이프 실소비 때 해당 표현 영역에서 재도입 가능 |
| `bShouldPlayStart` | 제거 후보 | 모든 Start 제외 방침, 항상 false인 현 잔재 |
| `StopEntrySpeed / PreviousGroundSpeed / bIsStopping` | 실제 소비 확인 후 축소 후보 | 변수 이름만으로 ABP Stop 활성 상태라고 해석하지 않음 |
| Snapshot의 미소비 가속/입력/상한 필드 | 실제 읽는 경로별로 정리 | Gameplay Intent의 대응 필드까지 무조건 삭제하지 않음 |
| Controller `Input_Attack` | 공통 ActionRequest 전달 | 현재 비어 있음. AnimInstance에 Attack bool 추가하지 않음 |
| `AKhazanCharacter` | 공통 기능 조립·초기화·전달 | 모든 기능의 실제 로직을 Character Tick에 모으지 않음 |

현재 ABP_Player가 읽는 것으로 확인된 멤버는 LocomotionGait, StopGait, StopEntryFoot, bIsGrounded, bIsFalling, bShouldBeIdle, bShouldEnterStop, bShouldWalkRun, bShouldSprint다. 다른 에셋의 외부 프로퍼티 참조까지 전수 부재를 확인한 것은 아니다.

실제 reflected 심볼을 삭제/이동할 때는 C++/Find in Blueprints 참조, 부모 클래스, 직렬화, Config의 `MovementAngle → MovementDirectionAngle` Redirect를 함께 확인한다. IDE 의미 기반 refactoring이 필요한 변경은 해당 절차로 수행한다. 빈 override 제거와 엔진 ACharacter Tick 비활성화는 다른 작업이다.

## 12. 주요 상황의 제어 흐름과 검증 기준

### 12.1 공격 도중 피격, 이어서 사망

1. 입력/AI가 공통 ASC에 공격 요청을 제출한다.
2. 승인된 Attack Ability가 비용 적용 후 자신의 이동 제약·몽타주·적중 창을 관리한다.
3. 피격은 Combat/Effect 경로가 피해와 반응을 결정한다. 슈퍼아머가 있으면 피해는 받아도 가벼운 반응이 생략될 수 있다.
4. 강제 경직이 유효하면 관련 효과/FSM 정책과 HitReact 액션이 적용된다. Attack 종료는 Attack의 handle만 정리한다.
5. HP가 사망 조건에 도달하면 Dead 전이가 일반 액션 요청을 닫고 기존 실행을 정리한다. Death Ability는 내부 승인으로 실행한다.
6. 늦게 도착한 Attack 몽타주 완료가 실행 ID 검사를 통과하지 못한다. Dead 해제나 이동 허용을 수행하지 못한다.
7. Death 연출 종료는 사망 표현의 종료다. 체력/제어 상태는 계속 Dead다.

검증: 중복 데미지 없음, 취소 뒤 적중 창 없음, 이동 제약 누락 없음, 사망 이벤트 중복 없음, 공격 버튼으로 부활/재공격 불가.

### 12.2 회피 취소와 비용 실패

1. 공격 중 회피 요청이 들어오면 제어 상태·취소 창·스태미나·회피 자산을 검사한다.
2. 사전 검사 실패면 기존 공격을 유지하고 실패 이유를 반환한다.
3. 승인 뒤 기존 공격을 취소했지만 회피 Commit이 실패하면 회피의 임시 권한을 정리하고 현재 제어 정책으로 복귀한다.
4. 회피가 실행됐다면 회피 종료/피격 취소가 자신의 이동/무적 효과 handle만 해제한다.

검증: 비용 부족 시 불필요한 공격 취소 없음, Commit 실패 후 잠긴 채널 없음, 피격 면역/이동 제약의 영구 잔류 없음.

### 12.3 SprintPivot

1. Sprint 이동 중 반대 방향 의도를 이동 계층이 검출한다.
2. Pivot 문맥과 CMC 구동을 시작한다. L3 토글/일반 Stop 이력을 임의로 바꾸지 않는다.
3. 로코모션 layer가 Pivot 표현으로 Sprint Stop 클립을 사용한다.
4. 구동 handoff 후 현재 입력으로 이동을 다시 해결한다.
5. 중간 공격/회피/피격/사망 요청은 정의된 중재 규칙으로 처리하고 종료된 Pivot callback은 무시한다.

검증: 일반 Stop과 구분, 기본 회전과 Pivot 회전 경쟁 없음, 입력 유지에 의한 무한 재진입 없음, 중단 후 이동권 복구 정확, 상위 제약 무시 없음.

### 12.4 AI 공격 및 체크포인트 리셋

- AI는 Player와 같은 Action ID 요청을 사용한다. BT가 몽타주만 직접 재생해 비용/타격/취소 규칙을 우회하지 않는다.
- AI Task Abort는 자신의 실행 ID에만 적용한다.
- 리셋은 기존 Pawn/encounter 수명을 정리하고 Definition/진행 데이터로 새 상태를 구성한다.
- 이전 적이나 Player Pawn의 callback, 적중 목록, Stop 발, 입력 버퍼가 새 Pawn으로 승계되지 않는다.

검증: Player 전용 Cast 없이 일반 적의 이동/공격/피격/사망 가능, 새 Pawn의 ASC/애니메이션 준비 이전 명령 거부, 이전 실행이 새 Pawn을 변경하지 못함.

## 13. 마이그레이션 실행 순서

이 순서는 과거 “AnimInstance에 Pivot 변수부터 추가”하는 단계를 대체한다. 매 단계는 사용자가 이해하고 구현·검증한 뒤 다음으로 넘어간다. 게임 파일을 한꺼번에 재작성하지 않는다.

| 단계 | 실제 구현 범위 | 완료 판정 |
| --- | --- | --- |
| A0 — 기준선 보존 | 현재 코드/BP 참조·동작 목록·검증 상태 고정. 미사용 후보와 실제 소비 목록 분리 | 현행과 목표를 구별할 수 있고, 롤백/비교 대상이 정확함 |
| A1 — 공통 이동 + 제어 HFSM 골격 | 최소 CharacterDefinition, Alive/Operational State, Ready gate, Player 입력과 공통 CMC 적용 분리, 원인별 이동 제약. 일반 적 하나의 AI 이동 연결 | Player 조작 보존, 적에도 같은 gait 제한 적용, 겹친 제약 중 하나를 해제해도 나머지 유지, 입력 이벤트 없이 제약 변경 반영 |
| A2 — 최소 전투 수직 기능 | GAS 연결, 공통 ASC/Ability/Attribute, 하나의 공격, 타격, HitReact/Dead, 일반 적과 Player의 같은 요청 경로 | 둘 다 공격·피해·경직·사망 가능, 정상/취소/실패의 자원 cleanup, 비용 실패/중복 적중/늦은 callback 시험 통과 |
| A3 — AnimInstance/Linked Layer 분리 | Main 관측과 locomotion 표현 분리, 현재 locomotion SM/loop/Stop 이관, 세트 데이터와 인터페이스 연결 | 현재 Walk/Run/Sprint/Stop/발 선택 회귀 없음, 재초기화·재링크 검증, A2 공격 Slot 재생 보존, worker 데이터 전달 순서 확인 |
| A4 — 회피·장비·두 번째 변형 | Dodge, 장비가 부여하는 능력/표현 세트, 다른 무기 또는 다른 적 정의 | 새 데이터 변형을 위해 Main AnimInstance/공통 Character의 액션 분기를 추가하지 않음. 장비 교체 취소·에셋 준비 실패 시험 |
| A5 — Turn/Pivot | Walk 좌/우 Turn, Locomotion 소유 SprintPivot. Run Turn/모든 Start는 제외 | 반전·재입력·피격·회피 중단, Root Lock/CMC 경계, 정상 Stop과의 분리 확인 |
| A6 — 보스·레벨 진행 | 실제 보스 페이즈, 필요한 Scripted 상태, Encounter/Checkpoint/Progression 수직 기능 | 해당 레벨 전투 시작→사망/리셋→보스 진행을 끝까지 검증. 맵별 코드가 AnimInstance에 추가되지 않음 |
| A7 — 확장과 성능 | 실제 적 종류/무기/스킬 확장, 목표 하드웨어·동시 수에서 측정 후 최적화 | correctness 유지 상태에서 CPU/메모리/에셋 로드 예산 충족. 수치는 측정/출처와 함께 결정 |

A2에서 현재 ABP의 기존 Slot을 사용할 수 있지만, 공격 상태/콤보 bool을 Main에 새로 쌓는 임시 구현은 허용하지 않는다. A3 완료 전이라도 액션 수명은 GAS가 소유한다.

A1도 한 번의 큰 코드 전달로 진행하지 않는다. 다음 공동 구현의 첫 소단계는 **현행 Player의 입력 해석과 CMC 적용을 분리할 데이터/함수 계약을 설명하고, 제약 소유권과 Ready/HFSM 경계를 최소형으로 연결하는 것**이다. 그때 파일별 실제 코드와 에디터 변경을 한 줄씩 설명한다.

### 매 단계의 공통 검사

- 단순 빌드 성공, 사용자 테스트 보고, 어시스턴트 정적 검사, 실제 PIE 측정을 구분해서 기록한다.
- Runtime 검사 재개 전에는 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)에 남은 이전 실행/디버거 정리 항목의 현재 상태를 먼저 확인한다. 이번 문서 작업으로 그 항목이 해결된 것은 아니다.
- 상태 전이·액션 승인/거절·취소·제약 취득/해제는 식별자와 이유를 가진 이벤트 로그로 남긴다. 모든 캐릭터의 매 Tick 로그를 기본으로 켜지 않는다.
- frame rate 변화, 애니메이션 update 생략, 몽타주 중단, 데이터 미로드, 메시/레이어 재초기화, EndPlay를 포함한다.
- 타이밍 값은 gameplay 시간/몽타주 재생 시간/구간 비율 중 무엇인지 명시한다. pause/hit stop/play rate와 불일치하는 별도 wall clock timer를 추가하지 않는다.
- 문서와 구현이 다르면 먼저 실제 코드를 확인하고 차이를 기록한다. 설계를 이유로 사용자 코드를 무단 되돌리지 않는다.

## 14. 재발 방지 규칙과 변경 절차

### 새 변수/함수/클래스 제안 전 필수 답변

1. 어떤 gameplay/표현 요구를 해결하는가? 지금 실제 소비자는 누구인가?
2. 최종 작성자와 읽는 계층은 누구인가? 이미 같은 의미를 소유한 값이 있는가?
3. 값은 현재 관측인가, 요청인가, 해결 결과인가, 진입 시 고정한 이력인가?
4. 어느 함수/이벤트에서 갱신되고 언제 Reset/해제되는가?
5. Game Thread/worker 중 어디서 접근하며 데이터 전달 수명은 보장되는가?
6. 정상 완료뿐 아니라 취소·실패·사망·EndPlay·재초기화에서 누가 정리하는가?
7. Player와 일반 적이 같은 계약을 사용할 수 있는가?
8. 수치의 단위와 출처는 무엇이며, 임시값이면 어떻게 검증·교체하는가?
9. 데이터/지역 변수/기존 private 함수로 충분한가? 새 타입의 독립 수명이나 다수 소비 근거는 무엇인가?
10. 무엇을 검사해야 회귀 없이 완료했다고 할 수 있는가?

### 금지할 확장 패턴

- Main AnimInstance의 `bIsAttacking/bCanDodge/ComboIndex/SkillCooldown/HitReactTimer`를 gameplay 원본으로 추가.
- Ability와 별도 AttackState가 같은 행동의 완료/취소를 각각 관리.
- 모든 것을 기존 LocomotionComponent나 새 ActionManager 한 파일로 옮기고 책임 분리라고 부르기.
- “나중에 쓸 것”을 이유로 Math helper, 미사용 snapshot 값, empty State/Component를 먼저 생성.
- 여러 시스템의 `SetMovementAllowed(true)`/`SetActorRotation`/`Montage_Play` 경쟁.
- 캐릭터 이름·무기 이름·레벨 이름에 따라 공통 AnimInstance에서 분기.
- 데이터 차이마다 Main ABP/전체 상태 머신을 복제.
- linked instance마다 외부 gameplay 데이터를 다시 수집하거나 이름만 ThreadSafe로 지정.
- 원작 metadata 미확인 값을 원작 정확한 수치로 표현.
- FSM/Linked Layer/GAS를 쓴다는 이유만으로 성능이 좋아졌다고 단정하거나 측정 없이 “수백 캐릭터 지원”을 약속.

### 구조를 바꿔야 할 때

이 정본을 영구 고정해 개선을 막는 것이 목적은 아니다. 책임 결정을 바꿀 때는 하단에 날짜별 결정 기록을 추가한다.

필수 항목: 변경할 ARCH ID, 새로운 요구/근거, 기존 구조로 부족한 이유, 새 소유자와 수명, 영향받는 코드/BP/데이터, 이관/회귀 검사, 실제 적용 여부.

후속 안내는 먼저 해당 계약과 현행 심볼을 확인하고 파일별 책임 이유를 설명한다. 코드 한 줄·변수 하나·함수 호출 순서·연산 의미·에디터 노드/핀과 검증을 단계별로 안내한다. “같이 구현하자”를 직접 파일 편집 요청으로 해석하지 않는다.

## 15. 근거와 이번 검증 범위

### 프로젝트 근거

- [현재 로코모션 계약](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md)
- [구조 검토와 사용처 근거](CHARACTER_ARCHITECTURE_REVIEW_20260908.md)
- [검토 리포트](../../Saved/ImportReports/Khazan_Character_Architecture_Review_20260908.json)
- [현재 Main AnimInstance](../../Source/Khazan/Animation/KhazanAnimInstance.cpp)
- [현재 LocomotionComponent](../../Source/Khazan/Character/Component/KhazanLocomotionComponent.cpp)
- [현재 Player 이동 적용](../../Source/Khazan/Character/KhazanPlayer.cpp)
- [기존 시스템/Config 구조](SOURCE_BP_CONFIG_ARCHITECTURE.md)

### 공식 기능 근거와 프로젝트 결정의 구분

본문의 Epic 링크는 Ability lifecycle, 애니메이션 모듈화/데이터 접근/최적화, AI 도구의 기능 근거다. 이 문서의 HFSM 트리, ASC Character 소유, 신체 액션 채널, 취소/실패 정책, 클래스 배치, 마이그레이션 순서는 이 프로젝트에 맞춘 설계 결정이다.

원작 카잔의 구현 클래스, 프레임 타이밍, 이동 속도, Root Motion 정책을 공식 Unreal 문서로 증명하지 않는다.

### 완료 범위

- 목표 아키텍처 v1, 책임/수명/동시 제약/취소/스레드/데이터 계약, 파일 배치, 이관 순서, 검증 기준을 문서화했다.
- 주요 현행 소스와 기존 표적 검사 근거를 대조했다. 전체 Content 전수 재조사나 신규 원작 metadata 추출은 하지 않았다.
- 게임 코드/BP/에셋/Config/Build.cs 수정, GAS/Linked Layer 구현, 새 빌드/PIE/성능 검증은 수행하지 않았다.
- 후속 공동 구현은 A1의 작은 소단계부터 시작한다. 이 문서의 목표 타입을 이미 존재하는 파일/심볼처럼 사용하지 않는다.


## 2026-09-08 — 사용자 7계층 Tag–Ability 아키텍처 적용성 검토

### 요청과 판정의 지위

- 사용자 요청은 7계층을 충분히 이해하고 현재 프로젝트에 적용할 수 있는지 판단하는 것이다. 이번에는 구현 예제나 게임 파일 수정을 요청하지 않았다.
- 판정: 태그 기반 공통 gameplay 어휘, GAS 실행/효과, 모듈형 표현, GameplayCue, 타깃/무기 타격, 인터페이스 상호작용이라는 방향은 HeinMach/StormPass의 Player/일반 적/보스에 적용 가능하다.
- 다만 “모든 bool/enum 금지”, “태그만으로 분기/실행 수명 제거”, “노티파이면 프레임 오차 없음”, “보스 Ability를 부여만 하면 모든 체형에서 동일 동작”을 기술적 보장으로 채택하지 않는다. 아래는 적용을 위한 검토 의견이며, 코드 적용이나 기존 v1 제어 HFSM의 교체 확정을 뜻하지 않는다.
- 새 문서의 권고를 과거 사용자 결정이나 원작 내부 구조의 확인으로 표현하지 않는다. 새 gameplay 수치도 선정하지 않았다.

### 현행 대조와 재사용 범위

- 현재 `Khazan.uproject`는 EngineAssociation 5.8이다. 설치 엔진 `C:/Program Files/Epic Games/UE_5.8/Engine/Build/Build.version`의 PatchVersion=2, Changelist=56702186을 확인했다.
- `Khazan.Build.cs`에는 GameplayTags 직접 의존성이 있고, GameplayAbilities/GameplayTasks/MotionWarping 직접 의존성은 없다. 이것을 다른 플러그인을 통한 GAS의 간접 활성화 여부까지 확인한 것으로 확대하지 않는다.
- `KhazanGameplayTags.cpp`의 현행 native 태그는 Input/AssetData/AssetLabel 계열이다. 아래 Ability/State/Condition/Status/Event/Window/GameplayCue 이름은 새 설계 어휘이며 현행 선언이 아니다.
- 공통 `AKhazanCharacter`는 LocomotionComponent를 소유한다. Khazan 전용 ASC/AttributeSet/GameplayAbility는 아직 구현되지 않았고 Controller의 `Input_Attack` 본문과 Monster native 동작은 비어 있다.
- `AKhazanPlayer::RefreshLocomotionGait`가 CMC 속도를 적용하고, LocomotionComponent의 `SetMaxAllowedGait/SetMovementAllowed`는 저장/입력 정리를 담당한다. 태그 기반 행동 차단을 CMC 이동/회전까지 적용할 공통 연결 책임이 필요하다.
- `KhazanAnimInstance.cpp`의 `GatherGameThreadData` 및 `NativeThreadSafeUpdateAnimation` 경계는 재사용한다. `UpdateLocomotionSelection_AnyThread`, `UpdateTransitionData_AnyThread`, `SelectStopEntryFoot_AnyThread`와 Stop gait/발 이력은 기존 A3의 locomotion 표현 분리 대상이다. 전투 판단을 Main에 추가하지 않는다.
- 저장된 [표적 검토 리포트](../../Saved/ImportReports/Khazan_Character_Architecture_Review_20260908.json)의 Source/Config/uproject/ABP_Player 39개 파일 hash와 현재 디스크 파일이 일치했다. ABP Linked Anim 노드 부재 및 소비 목록은 그 리포트의 검사 결과를 재사용했다. 현재 Editor의 미저장 그래프를 새로 검사한 것은 아니다.
- 모든 Start 제외, InGame 시퀀스 한정, Walk/Run 발별 Stop과 Sprint 단일 Stop, 기존 CMC/root-locked Stop은 유지한다. 이 검토로 루트 모션 정책을 일괄 변경하지 않는다.

### 7계층별 적용 계약

| 계층 | 적용 판단과 필요한 보완 |
| --- | --- |
| State Matrix | 공유 gameplay 상태/조건 어휘는 등록된 GameplayTag로 통일한다. 전역인 것은 사전이며 실제 보유 상태/count는 캐릭터별 ASC에 있다. 태그 분류, 현재 보유 상태, 일회성 이벤트, 연출 Cue를 구분한다. snapshot 유효성 bool, Foot/Gait/엔진 MovementMode와 같은 내부 관측·배타 선택까지 태그로 교체할 필요는 없다. |
| Execution | 액션 실행은 Ability/Task가 소유하고 Character는 조립/초기화/요청 전달을 맡는다. 같은 실행 구조의 평타 변형/콤보 단계는 Ability 클래스와 액션 데이터로 표현할 수 있다. 구조가 다른 돌진·잡기·브레스는 독립 실행을 둔다. |
| Math & Consequence | HP/Stamina/Poise는 AttributeSet, 비용/피해/상태 효과는 GameplayEffect와 필요한 계산 경로가 담당한다. 수치 반영 후 반응 정책이 Event를 만들고 ASC가 해당 반응을 승인한다. GAS가 Poise의 의미나 고갈 시 이벤트를 기본 제공하지는 않는다. |
| Presentation / AI | Main ABP는 공통 관측·Linked Layer·Montage Slot·필요 보정의 합성 틀이다. 완전히 빈 그래프를 목표로 하지 않는다. AI는 판단/요청을 소유하며 BT MoveTo/PathFollowing은 유지할 수 있다. 액션 실행과 공통 이동 제약을 우회하지 않는 것이 기준이다. |
| Sensory & Feedback | GameplayCue는 확정된 타격/반응의 시청각 결과만 처리한다. 등록된 Cue 태그와 위치·법선·표면·instigator 등 문맥을 전달한다. 실제 Niagara/Audio 호출은 Cue 구현 안에서 수행한다. Cue가 피해·강인도·이동 허가를 결정하지 않는다. |
| Spatial & Targeting | 타깃 선정, 실제 이동 보정, 무기 적중 검사를 서로 구분한다. Ability의 실행 문맥이 타깃을 보존하고 승인된 CMC 구동 경로에 MotionWarping을 연결한다. 무기 추적과 중복 적중 목록은 Combat/Task의 실행별 문맥에 둔다. |
| Interaction | 프로젝트용 Interactable 인터페이스로 실행 대상을 추상화한다. Interact Ability는 시도/진행/중단과 캐릭터의 임시 제약을 소유하고, 상자/문은 실제 열림·보상·영속 상태를 소유한다. 상호작용 오브젝트 모두에 ASC를 붙일 필요는 없다. |

### CancelAbilitiesWithTag 예제의 방향 정정

로컬 UE 5.8.2에서 직접 확인한 동작:

- `GameplayAbility.h`의 `CancelAbilitiesWithTag`는 **그 Ability가 실행될 때 취소할 다른 Ability의 분류**다.
- `GameplayAbility.cpp`의 `PreActivate`가 `ApplyAbilityBlockAndCancelTags(..., true, CancelAbilitiesWithTag)`를 호출한다.
- `AbilitySystemComponent_Abilities.cpp`의 `CancelAbilities`는 활성 Spec의 `GetAssetTags()`를 비교한다. 소유 캐릭터의 모든 Owned Tag를 검색하는 함수가 아니다.
- `UGameplayAbility::CancelAbility`는 `CanBeCanceled()`도 검사한다. 태그 일치만으로 어떤 실행이든 무조건 중단된다고 보장하지 않는다.

따라서 대검 강공격에 `CancelAbilitiesWithTag = State.Reaction.Hit`를 설정하면, 해당 분류를 가진 **기존 피격 Ability를 강공격 시작 때 취소**하려는 방향이다. “나중에 맞으면 이 강공격이 취소된다”는 뜻이 아니다.

다음은 제안 어휘로 설명한 올바른 책임 예다. 프로젝트에 생성하지 않았다.

| 설정/사건 | 제안 의미 |
| --- | --- |
| 공격 Ability의 Asset Tags: `Ability.Action.Attack` | 이 Ability를 공격으로 분류한다. |
| 공격 Ability의 Activation Owned Tags: `State.Action.Attack` | 해당 공격이 실행되는 동안 캐릭터에게 공격 중 상태를 제공한다. |
| 반응 Event: `Event.Reaction.Hit` | 확정된 피격 반응 문맥을 대상 ASC에 전달한다. 상태 태그를 계속 보유하게 하는 것과 다르다. |
| 피격 Ability의 Cancel Abilities With Tag: `Ability.Action.Attack` | 피격 실행 때 취소 대상으로 승인된 공격 분류를 지정한다. |
| 공격의 Activation Blocked Tags: `Status.Stun` | 이미 기절한 캐릭터의 신규 공격 승인을 막는다. |

- `Status.Stun`이 실행 도중 추가될 때 기존 공격을 중단하는 규칙은 신규 활성화 금지와 별도다. 효과/ASC 관계 처리에서 실제 취소까지 연결해야 한다.
- `HandleGameplayEvent → TriggerAbilityFromGameplayEvent → InternalTryActivateAbility` 경로도 로컬 소스에서 확인했다. 이벤트 태그를 보내기만 하면 미부여 Ability를 생성하거나 활성화 검사를 우회해 실행하는 것이 아니다.
- 임의 DataAsset에 GAS와 같은 이름의 필드를 추가한다고 엔진이 자동으로 소비하지 않는다. 기존 목표 `KhazanActionRelationshipData` 같은 데이터 소비/검증을 공통 ASC 경로에 구현해야 한다. Lyra의 관계 매핑 역시 프로젝트 확장 사례다.
- 기술 근거: [Gameplay Ability의 태그·수명](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-gameplay-abilities-in-unreal-engine), [Lyra 관계 매핑](https://dev.epicgames.com/documentation/en-us/unreal-engine/abilities-in-lyra-in-unreal-engine). 원작 카잔의 수치/내부 구조 근거로 사용하지 않는다.

### 피해·취소·애니메이션 시간의 보완

- Poise 고갈에 따른 반응, SuperArmor가 억제하는 반응 종류, Invincible이 막는 피해 범위는 프로젝트의 효과/반응 규칙으로 명시한다. 이름을 등록하는 것만으로 방어 동작이 생기지 않는다.
- 한 적중의 HP/Poise 결과를 확정한 뒤 사망과 일반 반응의 우선순위를 결정한다. 실행 중 각 attribute callback에서 무조건 피격 이벤트를 보내면 동일 적중에서 중복 반응/사망 뒤 피격이 발생할 수 있다. 반응별 중복 방지 및 재진입 처리를 둔다.
- 피격은 관계상 중단 대상 액션을 취소한다. 모든 passive/독립 Ability까지 무조건 CancelAll하는 것을 기본 정책으로 삼지 않는다.
- 애니메이션 Notify/ANS는 실행 중인 Ability/Combat에 식별 가능한 창 이벤트를 전달한다. Event를 받은 쪽은 실행 ID·몽타주/창 문맥을 검증한 뒤 태그와 타격 창을 변경한다. 공유 Notify 에셋에 캐릭터별 handle·적중 목록을 저장하지 않는다.
- Queued Notify와 Branching Point는 동기/정밀도/비용이 다르다. Notify 사용만으로 낮은 frame rate, section jump, blend, animation update 생략에서 오차 없는 검출을 보장하지 않는다. [공식 Notify 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-notifies-in-unreal-engine)
- 공격 창은 몽타주 시간축을 사용하되, 쿨다운/지속 효과/애니메이션 없는 실행의 시간을 전면 금지하지 않는다. 독립적인 시계가 같은 gameplay 종료를 중복 소유하지 않도록 한다.
- 정상/취소/Commit 실패/몽타주 실패/장비 제거/사망/EndPlay에서 창·임시 Effect·이동 제약·Warp Target·delegate를 실행별로 정리한다. Notify End만 기다리지 않는다.
- 태그 count와 효과/제약 handle을 사용해 각 원인의 기여만 회수한다. 다른 무적 효과가 남았는데 상호작용 종료가 Invincible을 일괄 지우는 방식은 금지한다.
- 효과 기반 근거: [GAS의 Attribute/Effect/Cue 책임](https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-the-unreal-engine-gameplay-ability-system).

### Cue·타깃·타격·상호작용의 보완

- Cue는 전역 무문맥 EventBus가 아니다. GAS의 Cue 실행 경로와 등록된 구현에 태그 및 hit 문맥을 제공한다. Flesh/Stone/Metal의 조합을 무제한 런타임 문자열 생성으로 처리하지 않고, 미리 등록한 태그/표면 데이터 매핑으로 선택한다.
- PhysicalMaterial/SurfaceType → Cue/연출 데이터 선택은 프로젝트가 구성할 규칙이다. 엔진이 태그의 영문 이름을 해석해 혈흔/스파크/사운드를 자동 추론하지 않는다. 피해를 받지 않는 벽도 확정된 접촉 결과로 Cue를 재생할 수 있으므로 모든 표면 반응을 HP 차감 성공에 종속시키지 않는다.
- 보스 Charge의 실행 코드는 Player에도 공유할 수 있으나 사용자가 요구한 “부여만으로 재사용”은 공통 avatar 계약, 필요한 Attribute/Component, 타깃 입력, 호환 Skeleton/Montage/Socket, 이동 방식과 리소스가 갖춰진 경우에 가능하다. 체형별 데이터까지 준비 없이 같은 BP/애니메이션을 실행할 수 있다는 뜻은 아니다.
- MotionWarping은 선택된 구간의 root motion을 목표에 맞추는 기능이다. 플러그인/컴포넌트 외에도 Montage의 구간/타깃 이름, root motion 추출과 CMC 경로를 연결한다. 타깃 유효성·추적 종료·최대 보정 범위·벽/지형·실패 정책은 별도로 설계하며, 목표 도달이나 적중을 보장하지 않는다. [공식 Motion Warping 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-warping-in-unreal-engine)
- 기존 root-locked Stop에 타깃만 전달해 공격 워핑까지 완성됐다고 보지 않는다. 공격/회피의 실제 InGame 에셋을 표적 확인한 뒤 해당 액션만 이동 방식을 정한다.
- 캐릭터 이동 캡슐을 검 타격 판정의 유일한 형상으로 사용하지 않는 방향은 적합하다. 무기에서는 실제 bone/socket 기반 이전→현재 위치 sweep과 칼날 길이 방향 표본, 창별 중복 방지가 필요하다. 큰 각변위 구간은 보간/추가 표본 등 누락 대책을 검증한다. 매 frame 현재 위치에 선 하나를 그리는 것만으로 검 궤적과 수학적으로 동일한 판정이 생기지 않는다.
- 발차기·물기·브레스·폭발·투사체는 각기 맞는 형상/방식을 사용한다. Capsule/Sphere/Overlap 자체를 모든 전투에서 금지하지 않는다. pose 의존 추적은 해당 pose 갱신 이후 검사 시점을 보장하고, 화면 밖 animation budget 정책도 검증한다.
- 상호작용은 유효 대상/거리/시야/대상의 사용 가능 상태를 확인하고, 실제 결과를 확정하는 시점과 취소를 구분한다. 상자는 열린 상태와 보상 지급의 단일 작성자이며 같은 실행의 중복 호출이 보상을 중복 지급하지 않도록 한다. 도중 무적은 해당 액션 데이터가 요구할 때만, 명시한 구간/수명으로 제공한다.

### 기존 ARCH 결정과의 관계 및 권고

- ARCH-01/03/05/06/08/09/10: gameplay·표현 분리, GAS 액션 수명, 원인별 제약, Player/AI 공통성, 실행 ID/cleanup, GT→worker 경계를 보존한다.
- ARCH-07: “액션마다 무조건 새 C++ 클래스”보다 같은 실행 방식+데이터 변형이라는 기존 결정을 유지하는 것이 확장 목표에 적합하다.
- ARCH-02와 7절: 기존 필수 제어 HFSM·내부 bool/enum 선택 정책과 사용자의 문자 그대로의 전면 태그화는 그대로는 같지 않다. 차이를 숨기거나 기존 HFSM이 태그 아키텍처의 필수 엔진 기능이라고 설명하지 않는다.
- 검토 권고: 공유 gameplay 상태/승인 관계는 ASC 태그·효과로 통일하고, 이를 소비하는 공통 제어/Locomotion 정책을 둔다. Alive/Operational 등의 별도 HFSM을 반드시 먼저 생성할지는 실제 Enter/Exit·Scripted 수명 요구로 재검토한다. 태그 정책만으로 충분하면 필수 HFSM을 줄일 수 있고, HFSM이 필요하면 자체 상태 원본과 ASC 태그 원본을 중복 작성하지 않도록 한쪽을 projection으로 둔다.
- 이번에는 HFSM 유지/폐기나 A1 이관 절차 변경을 구현 결정으로 확정하지 않았다. 후속 구현 전에 사용자 7계층 방향을 반영한 ARCH-02/제어 소유권을 구체화해야 하며, 예전 A1의 빈 State 파일부터 자동 생성하지 않는다.
- 신규 책임의 배치 검토: Cue 표현은 기존 전투 이벤트의 하위 소비자, 타깃/워핑/타격은 Ability·공통 이동·Combat의 해당 책임, 상호작용은 Ability와 대상 인터페이스에 둔다. 이 7가지 개념을 7개의 거대한 Manager 클래스나 모든 행동을 통과하는 단일 직렬 파이프라인으로 만들지 않는다.

### 다음 검증과 이번 완료 범위

- 후속 구현은 공통 태그 사전/상태 작성자/제약 수명 계약을 먼저 구체화하고, Player와 일반 적 하나에서 같은 공격→비용→타격→피격/사망→Cue 경로를 검증하는 작은 수직 기능으로 진행한다. 기존 이동 보존과 공통 CMC 제약 적용을 함께 다룬다.
- 이후 Linked Layer 이관, 회피·무적 중첩, 장비/두 번째 동작 변형, 실제 액션의 워핑·표면별 Cue·상호작용, 보스 페이즈/레벨 진행을 확장한다. 모든 클래스를 미리 생성하지 않는다.
- 검증 항목: 신규 활성화 차단과 실행 중 취소의 구분; 자원 부족 시 기존 액션 보존; 겹친 제한 중 하나만 해제; 피격 취소 후 적중 없음; 같은 hit에서 사망/반응 중복 없음; 늦은 callback 무시; 저프레임/화면 밖/몽타주 중단; 다른 체형의 데이터 준비 실패; 상호작용 중단/중복 호출; 레이어·장비 교체/EndPlay 정리.
- 이번 완료는 정적 적용성 검토와 날짜별 문서 기록이다. Source/BP/에셋/Config/Build.cs/uproject 수정, 새 GAS/Linked Layer/워핑/상호작용 구현, 빌드·PIE·성능 측정은 수행하지 않았다.


<a id="character-architecture-v2"></a>

## 2026-09-08 — 아키텍처 v2 확정: Data-Driven Tag–Ability 7계층

### V2-00. 후속 개발의 필수 기준과 이력 우선순위

사용자의 “수정할 구조를 모두 MD에 정리하고 이제부터 철저하게 이 아키텍처에 따라 개발한다”는 지시에 따라 **아래 v2를 채택된 개발 기준으로 확정한다.** 앞선 적용성 검토의 보완 사항도 이 계약에 편입한다. 설계 선택을 다시 “참고 후보”로 취급하지 않는다. 다만 구현 완료와는 구분한다.

- 조회 순서: Router → 이 v2 절 → [마이그레이션](CHARACTER_TAG_ABILITY_MIGRATION.md) → 현재 단계/현행 정본/필요한 소스.
- 이 문서 앞부분 v1의 필수 제어 HFSM, 클래스/폴더 생성표, A0–A7 순서와 앞선 “HFSM 유지/폐기 미확정” 기록은 이력이다. **충돌 항목은 이 v2와 새 M0–M10 순서가 대체한다.**
- 게임플레이 상태의 공통 원본은 캐릭터별 ASC의 태그/효과이며, 액션 수명은 Ability/Task가 소유한다. 별도 CharacterStateMachine 및 Alive/Operational/Incapacitated/Scripted/Dead State 클래스는 이번 목표 구조와 마이그레이션에서 만들지 않는다.
- 상태별 정책은 태그 관계/효과/이동 제약 데이터로 해결한다. 같은 공격·기절·사망을 FSM, Character, AnimInstance가 독립 상태로 중복 소유하지 않는다.
- 내부 bool/enum, 애니메이션 상태 머신, Ability 안의 국소 실행 phase는 의미에 맞게 사용한다. gameplay 공개 상태를 별도의 변경 가능한 bool/enum으로 복제하는 것과 구분한다.
- 기존 기록은 삭제·수정하지 않고, 새 결정과 구현 결과를 날짜별로 추가한다. 기존 설계를 바꿀 때는 관련 ARCH ID, 이유, 새 소유자, 수명, 이관/검증 범위와 적용 상태를 먼저 기록한다.
- 최신 사용자 요청이 작업 범위를 정한다. 이번 권한은 MD 확립·마이그레이션 설계·사용자가 따라 할 첫 단계 설명이다. 게임 C++/BP/에셋을 어시스턴트가 직접 적용하는 포괄적 권한이 아니다.
- 싱글플레이, Character 소유 ASC, 체크포인트 복귀 시 새 Pawn 구성을 유지한다. 멀티플레이 예측/복제 또는 Pawn 간 실행 상태 승계는 현재 완료 조건에 포함하지 않으며 실제 요구 시 소유권 변경을 기록한다.

### V2-01. ARCH 결정 변경표

| ID | v2 채택 결정 | v1에서 달라지는 범위 |
| --- | --- | --- |
| ARCH-01 | gameplay 사실/승인과 애니메이션 포즈를 분리한다. | 유지. ABP/Notify가 최종 피해/행동 허가의 원본이 되지 않는다. |
| ARCH-02 | 공통 상태 원본은 ASC 태그/GameplayEffect이며 별도 제어 HFSM을 도입하지 않는다. | v1 3절 State 트리/클래스, 제어 FSM 그림, A1 필수 HFSM을 대체한다. 실제 현행 FSM 파일은 없으므로 삭제 대상도 없다. |
| ARCH-03 | 액션 실행/비용 Commit/정상·취소·실패 수명은 Ability/Task가 소유한다. | 유지. AttackState를 병행하지 않는다. |
| ARCH-04 | LocomotionComponent가 원시 이동 의도와 태그/제약을 해결해 CMC 정책을 적용한다. | HFSM 정책 입력을 태그/효과·액션의 명시적 제약으로 교체한다. |
| ARCH-05 | 태그는 count, 효과·부여·이동 제약은 각 원인의 handle과 실행 ID로 회수한다. | 단일 허용 bool을 여러 작성자가 덮는 기존 API를 M2에서 이관한다. |
| ARCH-06 | Main은 공통 관측/합성, Locomotion Linked Layer는 이동 포즈/Stop 발 이력을 소유한다. | 유지. Main ABP를 완전히 비우거나 worker에서 ASC를 직접 읽지 않는다. |
| ARCH-07 | 실행 방식이 같으면 클래스+데이터 변형, 구조가 다르면 별도 Ability/Task/Layer다. | 스킬마다 클래스 복제와 만능 설정 파일을 모두 피한다. |
| ARCH-08 | Player/AI는 동일한 승인·비용·취소·이동 제약 계약을 사용한다. | BT의 일반 MoveTo/PathFollowing은 유지하며 직접 액션/몽타주 실행 우회를 제거한다. |
| ARCH-09 | 모든 callback/종료는 Pawn 수명·실행 ID·소유권을 확인하고 중복 호출에도 안전하게 정리한다. | FSM 세대 ID를 선행 생성하지 않고 실제 액션/장비/요청 수명에 식별자를 둔다. |
| ARCH-10 | UObject/ASC/월드 접근과 gameplay 쓰기는 Game Thread, worker에는 평가 수명이 보장된 값만 전달한다. | 유지. 캡처한 포인터 자체는 snapshot이 아니다. |
| ARCH-11 | 보스 페이즈/Encounter/Checkpoint/Progression/상호작용 대상 상태는 해당 gameplay 소유자가 관리한다. | 태그는 외부 관측용이며 Main AnimInstance에 레벨 로직을 넣지 않는다. |
| ARCH-12 | 공통 기능은 Player와 일반 적 하나에서 먼저 검증한다. | 화면 표현이나 입력 장치가 같아야 한다는 뜻은 아니다. |
| ARCH-13 | GameplayCue는 확정된 결과의 VFX/SFX/필요 피드백만 담당한다. | 정식 계층으로 추가. 피해/무적/행동 허가를 Cue에 두지 않는다. |
| ARCH-14 | 타깃 선택, 액션 이동/워핑, 실제 적중 검사를 분리한다. | 공간 계층과 형상별 타격 계약을 추가한다. |
| ARCH-15 | 상호작용은 Ability와 인터페이스의 시작/결과 확정/취소 계약으로 처리한다. | 대상의 영속 상태/보상을 Player가 소유하지 않는다. |
| ARCH-16 | 데이터 정의는 읽기 전용 설정이며 캐릭터/장비 초기화와 소비 경로를 명시한다. | 태그 문자열이나 임의 DataAsset 필드만 추가하고 자동 작동한다고 가정하지 않는다. |
| ARCH-17 | ASC의 ActorInfo 연결, 데이터 준비, 게임플레이 Ready를 서로 다른 단계로 관리한다. | ASC가 생겼다는 이유로 공격 요청을 허용하지 않는다. |
| ARCH-18 | 태그 사전과 Asset Tags/Owned Tags/Event/Cue의 의미·수명을 구분한다. | 전역 상태 컨테이너·런타임 문자열 조합·관측 bool 일괄 제거를 금지한다. |
| ARCH-19 | 거절/Commit 실패/취소/적중/태그·제약 잔류를 이유와 식별자로 추적한다. | 많은 종의 몬스터 확장은 데이터 검증과 실제 회귀/성능 측정을 통과해야 한다. |

앞선 14절의 새 변수/함수/클래스 검토 항목은 계속 적용한다. v1 타입/단계명이 나오는 부분은 이 변경표와 아래 계약으로 치환한다.

### V2-02. 7계층의 책임과 생성 시점

| 계층 | 실제 소유자/역할 | 소비자·생성 시점 |
| --- | --- | --- |
| 1. State Matrix | 등록된 공통 태그 사전 + 캐릭터별 ASC의 Owned Tag/count + GameplayEffect 수명 | ASC 승인, 이동 정책, 반응 정책, UI/애니메이션의 읽기용 관측. 선언은 해당 소비자가 생기는 M2 이후 필요한 범위부터 한다. |
| 2. Execution | GameplayAbility/AbilityTask의 액션 실행. Khazan ASC는 공통 요청·관계·취소 중재 | M1 엔진 ASC 연결. M3 공통 요청 소비가 생길 때 Khazan ASC/Ability base 추가. |
| 3. Math & Consequence | AttributeSet/GameplayEffect/Calculation이 수치를 처리하고, CombatResponse가 확정된 결과의 반응·사망을 처리 | M3 최소 HP/Stamina/Poise와 즉시 적중. 지속 피해 등 다른 적용 경로도 동일한 결과 확정 계약을 거쳐야 한다. |
| 4. Presentation / AI | Main+Linked Layer+Slot은 포즈; Controller/BT는 판단·요청 | M2 공통 AI 이동, M3 공통 액션 요청, M4 현재 Locomotion 이관. AI 판단을 AnimInstance에 넣지 않는다. |
| 5. Sensory & Feedback | 등록된 GameplayCue 구현/연출 데이터 | M3 최초 적중 Cue, M6 표면별 확장. 실제 Spawn/Play API는 이 표현 계층 내부에 둔다. |
| 6. Spatial & Targeting | 타깃 문맥은 실행/실제 LockOn 소유자, 이동은 Locomotion/CMC+MotionWarping, 타격은 CombatComponent | M3 기본 근접 타격, M6 타깃·워핑·형상별 정밀 타격. 필요한 액션이 없는 컴포넌트는 선행 추가하지 않는다. |
| 7. Interaction | Interact Ability의 캐릭터 실행 수명 + Interactable 대상의 상태/결과 | M7에서 실제 상자/문으로 도입. 월드 상호작용 대상 모두가 ASC를 가질 필요는 없다. |

이 계층들은 책임 경계다. 7개 Manager 클래스나 모든 사건을 통과시키는 하나의 직렬 EventBus를 만들라는 뜻이 아니다.

### V2-03. 단일 작성자와 수명

| 사실/자원 | 최종 작성자 | 독자/Reset·해제 |
| --- | --- | --- |
| 장치 입력/카메라 기준 방향/L3 요청 | Player 입력 어댑터 | 공통 이동·액션 요청. 해제/빙의 해제에서 자신의 입력만 정리 |
| AI 목적지/행동 의도 | AIController/BT | 공통 정책/요청. BT Abort는 자신이 요청한 실행 ID만 취소 |
| 공유 gameplay 상태 | ASC의 Ability/Effect별 기여 | 다른 시스템은 태그 조회/관측. 일반 소비자가 Loose Tag count를 일괄 덮지 않음 |
| HP/Stamina/Poise | ASC의 AttributeSet/GameplayEffect 경로 | 결과 확정 후 반응/UI. 다른 Character float로 복제하지 않음 |
| 현재 공격/회피/피격과 콤보 문맥 | 해당 Ability 실행 | 실행 ID·단계·입력 버퍼 소비. End/Cancel/Fail/EndPlay에서 자신의 자원 정리 |
| 피해 결과의 반응/사망 전이 | 목표 타입 `UKhazanCombatResponseComponent` | 확정된 CombatResult 소비, 태그/Effect·반응 Event 출력. M3 첫 HitReact/Death의 실제 소비 시 생성 |
| 이동 허가/gait 상한/회전·구동 선택 | LocomotionComponent | 의도/태그/handle 변화에 재해결하여 CMC에 적용. 외부 bool 원본 금지 |
| 실제 위치/속도/바닥/충돌 | CMC/엔진 물리 | snapshot 관측. root motion도 승인된 CMC 구동 경로 사용 |
| 적중 창/이전 socket pose/중복 대상 | CombatComponent의 실행·창별 문맥 | Ability/Task가 시작·닫기 요청. 종료/섹션 전환/중단에서 수명 검증 |
| 무적/슈퍼아머/기절 | 해당 GameplayEffect 또는 명시한 Ability 기여 | 각각의 effect/execution handle만 회수. 같은 태그의 다른 기여 보존 |
| 사망 | CombatResponse가 확정해 ASC에 적용한 Pawn 수명의 사망 효과 | Death Ability 종료와 무관하게 유지. 체크포인트는 새 Pawn 구성 |
| 연출 강제 제어 | 해당 Scripted/Interaction 실행 또는 Encounter의 유효 요청 | 실행별 태그/제약/Effect handle. 정상·취소·대상 소멸에서 회수 |
| loop/Stop gait·Stop 발 | Locomotion 애니메이션 인스턴스 | 진입 고정/Reset/relink 규칙. gameplay 허가의 원본으로 사용하지 않음 |
| 장비 정의/능력 부여/레이어 로드 | EquipmentComponent | 자신이 부여한 Spec/Effect/asset handle. 교체 세대 ID로 늦은 로드 무시 |
| 보스 페이즈/전투 구역/저장 진행 | BossPhase/Encounter/Progression 계층 | 읽기용 태그/이벤트/데이터 제공. 같은 진행을 태그와 별도 쓰기 값으로 이중 관리하지 않음 |
| 상자 열림/보상 지급 | 해당 상호작용 대상/Progression | 실행 식별자로 결과를 한 번 확정. Player가 구체 클래스별 분기하지 않음 |

CombatResponse는 새로운 전체 액션 관리자가 아니다. 이동·타격 추적·몽타주·AI 판단을 소유하지 않고, 확정된 수치 결과로부터 반응/종단 상태를 만드는 실제 책임만 가진다. 정의 타입/정확한 함수 시그니처는 M3의 첫 소비 경로에서 확정한다.

### V2-04. 태그 어휘와 관계 규칙

다음은 채택된 의미/namespace 계약이다. 표에 있다고 이번에 native 선언이나 에셋을 생성한 것은 아니다. 소비 단계에서 필요한 leaf부터 등록한다.

| 분류 | 채택 어휘 예 | 의미/소유 |
| --- | --- | --- |
| Input | 기존 `Input.Action.Move/Sprint/Turn/Jump/Attack` | 입력 식별자. Actor 상태나 Ability 활성화를 자동 의미하지 않음 |
| Ability Asset Tags | `Ability.Action.Attack`, `Ability.Action.Dodge`, `Ability.Reaction.Hit`, `Ability.Reaction.Death`, `Ability.Interaction` | Ability 자체의 분류. cancel/block 대상 검색에 사용 |
| Owned State | `State.Action.Attack`, `State.Action.Dodge`, `State.Reaction.Hit` | 실행 중에 소유 캐릭터에 부여. 해당 실행 종료 시 회수 |
| Lifecycle | `State.Life.Dead`, `State.Ready.Gameplay`, `State.Control.Scripted` | 사망/완전 준비/유효 연출 수명. 준비 태그는 ActorInfo 연결만으로 부여하지 않음 |
| Condition / Status | `Condition.Invincible`, `Condition.SuperArmor`, `Status.Stun` | 각각 피해 수락/반응 억제/기절 효과 규칙. 과거 제안의 `Status.Stunned`를 별칭으로 동시에 도입하지 않음 |
| Block | `Block.Movement.Input`, `Block.Action.Input` | 효과/상태 정의가 부여하고 공통 이동/일반 액션 요청이 소비. 이동 입력 차단과 모든 물리 정지는 다름 |
| Window | `Window.Combo`, `Window.HitboxActive` | 활성 실행·창과 연결된 상태. 전체 캐릭터 count만으로 어느 공격 창인지 추정하지 않음 |
| Event | `Event.Reaction.Hit`, `Event.Reaction.Death` | 일회성 payload 전달. 공격자/대상/적중 결과/실행 문맥을 전달 |
| Cue | `GameplayCue.Combat.Hit.Flesh/Stone/Metal` | 등록된 연출 선택. 문자열 의미로 물질을 자동 추론하지 않음 |

- Asset Tags와 Owned Tags는 서로를 자동 부여하지 않는다. 피격 Ability의 취소 대상에 공격 Asset Tags를 지정한다. 공격에 피격 태그를 넣어 “나중에 맞으면 자기가 취소된다”고 해석하지 않는다.
- 신규 활성화 금지, 현재 실행 취소, 현재 액션의 일반 취소 창, 내부 HitReact/Death의 강제 반응 경로를 구분한다.
- 일반 입력/AI가 공개 옵션 하나로 Ready·사망·비용 규칙을 우회할 수 없다. 내부 반응도 유효한 결과/요청 출처를 확인한다.
- 임의 DataAsset의 태그 규칙은 공통 ASC가 읽고 적용해야 한다. native GAS 태그 조건과 추가 관계 데이터의 합성 규칙은 M3에서 단일 경로로 구현한다.
- 일반 취소 창을 닫기 위해 모든 주요 액션에 CanBeCanceled=false를 적용하지 않는다. 죽음/종료 때 정리가 필요한 액션은 시스템 취소 경로를 유지한다.
- 관계 조회의 exact/계층 match, source/target 조건, 중첩 count, 실제 실패 이유를 테스트한다.
- 태그나 데이터를 사용해도 수식/조건문/인터페이스 호출은 필요하다. 공통 코드에 무기·몬스터 이름별 예외를 누적시키지 않는 것이 기준이다.

### V2-05. 승인·효과·사망·취소의 실행 계약

1. Player/AI 요청은 요청 ID와 Action 식별자, 입력 의미, 필요한 타깃/방향만 전달한다. 장치 타입을 Ability에 전달하지 않는다.
2. 공통 ASC는 Ready, 능력 부여, 태그/관계, 취소 창, 비용/자원, 타깃/필수 리소스를 검사한다. 사전 실패는 기존 액션을 중단시키지 않는다.
3. 승인된 전환만 기존 액션을 취소하고 새 Ability를 실행한다. Commit 실패는 새 실행의 자원을 회수하며 이미 취소한 공격을 되살리지 않는다. 비용/쿨다운은 실제 gameplay 효과보다 먼저 확정한다.
4. Ability/Task는 자기 실행의 이동 제약·몽타주·창·타깃·delegate/필요 timer를 취득한다. 주요 신체 액션의 상호 배타 정책과 독립 passive 수명을 구분한다.
5. Combat의 유효 타격은 source/target/실행/창/hit ID와 EffectSpec 문맥을 가진다. target의 효과 적용 경계에서 한 적중의 계산 결과를 확정한 뒤 CombatResult를 전달한다.
6. AttributeSet은 수치 제약을 지키고, 각 attribute 수정 callback에서 독립적으로 Hit/Death를 즉시 발행하지 않는다. 같은 hit의 모든 관련 수치 반영 뒤 CombatResponse가 사망 우선/반응 억제/강인도 소진 결과를 결정한다.
7. M3 첫 구현은 즉시 적중을 대상으로 결과 확정 경계를 만든다. 지속/주기 피해를 추가할 때는 외부 Apply 호출뿐 아니라 실제 periodic 실행 경로도 같은 결과 확정/중복 방지 어댑터로 연결한다. 적용 callback 하나로 모든 효과 실행을 관측했다고 가정하지 않는다.
8. 사망 확정은 재진입/중복 hit를 차단하고 Pawn 수명의 Dead 효과를 먼저 적용한다. 일반 액션 요청/이동 정책이 이를 관측한 상태에서 기존 액션을 정리하고 Death Ability를 요청한다. Death 연출 종료는 Dead 해제가 아니다.
9. 일반 피격은 정의된 반응만 실행하고 관계상 대상 액션만 취소한다. 무적, 슈퍼아머, 경직 강도를 별도 규칙으로 처리한다.
10. 종료는 정상/취소/Commit 실패/몽타주 실패/장비 제거/타깃 소멸/사망/EndPlay를 포함한다. 실행 ID를 검증하고 자기 창·effect/constraint handle·Warp Target·delegate·timer만 정리한다. 오래된 callback이 새 실행/사망 상태를 바꾸지 못한다.

영구 사망 효과의 handle과 임시 HitReact의 handle은 수명이 다르다. EndPlay의 ASC 전체 종료는 Actor 수명의 종료이며, 일반 피격 때 쓰는 취소 정책과 구분한다.

### V2-06. 공통 이동·표현·Cue·공간·상호작용 계약

- **이동:** 원시 입력 의도는 정책으로 막힌 동안에도 해제 입력과 구분한다. 이동 태그 count와 액션별 제약/구동 handle의 변화에 정책을 재계산해 CMC에 적용한다. 입력 이벤트가 없어도 기절/제약 변화가 반영돼야 한다. 같은 원인의 같은 제한을 태그와 handle로 중복 등록하지 않도록 각 기여의 계약을 명시한다.
- **구동:** 일반 Player 입력, AI PathFollowing, 승인된 액션 root motion/warping, Pivot과 강제 제어의 충돌을 Locomotion에서 중재한다. CMC의 정상 충돌/바닥/중력 경로를 유지한다. 입력 차단만으로 Velocity/중력이 자동 중단된다고 보지 않는다.
- **표현:** Main GT snapshot → 안전한 animation update 데이터 → Linked Layer/Slot 합성을 사용한다. worker에서 ASC/Character/CMC를 직접 조회·수정하지 않는다. Locomotion의 marker 조회·Stop 이력은 동일 linked instance에 둔다. 레이어 재링크/비활성/몽타주에 가려짐의 Reset도 검증한다.
- **Notify:** 에셋은 실행별 mutable 상태를 보관하지 않는다. Notify/ANS는 활성 실행·창을 식별해 이벤트를 전달하고 Ability/Combat이 검증한다. Queued/Branching Point, section jump, update 생략, frame rate 변화를 고려한다. 모든 timer를 금지하지 않고 시간축과 최종 종료 소유자를 하나로 정한다.
- **Cue:** 등록된 Cue/표면 데이터에 위치·법선·PhysicalMaterial/SurfaceType·instigator 등 문맥을 전달한다. 연출 구현 내부의 Spawn/Play는 허용한다. Cue의 도착이나 재생 성공을 피해/무적/적중의 조건으로 사용하지 않는다. 벽 접촉도 HP 변화 없이 피드백을 낼 수 있다.
- **타깃:** 순간 공격 목표는 실행 문맥이 고정/추적 종료 정책으로 관리한다. 지속 LockOn이 실제 요구될 때만 TargetingComponent가 장기 목표를 소유하고 Ability는 필요한 스냅샷을 받는다.
- **워핑:** MotionWarping은 실제 액션의 Montage 구간/타깃 이름/root motion 추출/CMC 이동 정책과 함께 도입한다. 장애물/대상 소멸/추적 중단/보정 제한을 데이터와 실행 규칙으로 다루며 이동 도달·적중을 보장하지 않는다.
- **타격:** 무기 bone/socket의 이전→현재 sweep과 칼날 길이 표본, 큰 각변위 대응, 실행·창별 중복 방지를 사용한다. pose 갱신 이후 GT 검사와 화면 밖 평가 정책을 검증한다. 브레스/폭발/투사체/물기 등은 적합한 형상/방식을 사용한다. Character 이동 캡슐을 유일한 무기 판정으로 쓰지 않되 Capsule/Overlap API 자체를 금지하지 않는다.
- **상호작용:** Interact Ability는 유효 대상·거리·시야·진행/취소·임시 무적을, 대상은 수락/결과 확정/영속 상태를 소유한다. 결과 확정 전 중단과 확정 후 종료를 구분하며 보상은 실행 ID로 한 번만 지급한다. 대상 삭제와 재시도에서도 handle/완료 callback이 새 요청에 섞이지 않는다.
- **AI/보스/레벨:** BT/Blackboard는 판단·요청, BossPhase는 페이즈, Encounter/Progression은 진행을 담당한다. 장비/페이즈로 바뀌는 정의·능력·레이어는 로드 준비와 교체 세대 ID를 거친다. 체형/스켈레톤/능력 요구 계약이 맞을 때 같은 실행 코드를 공유한다.

### V2-07. 데이터 정의와 준비/종료

- `KhazanCharacterDefinition`: 캐릭터/골격 가족, 이동 기본값, 기본 AbilitySet, 초기 Attribute/효과, 표현 세트, 실제 AI 정의. 읽기 전용 설정이며 현재 상태를 저장하지 않는다.
- `KhazanActionDefinition`: 실행 Ability, Action ID/분류, 필요한 비용/쿨다운/리소스, Montage/Section, 이동/타깃/타격/취소/피드백 참조. 실제 구조가 다른 액션은 적절한 subtype/작은 설정으로 분리한다.
- `KhazanAbilitySet`: 능력/초기 효과 부여 묶음. 부여 주체가 반환 Spec/Effect handle을 보존하고 자기 묶음만 해제한다.
- `KhazanActionRelationshipData`: require/block/cancel과 허용 전환 관계. 등록만 해 두고 소비 코드가 없는 데이터를 완료로 보지 않는다.
- 반응/피해 정의, 무기 타격 profile, LocomotionAnimSet, 표면별 Cue/연출 정의, 상호작용 정의는 실제 소비 단계에서 필요한 필드만 만든다.
- 수치는 원작 metadata/report 우선이다. 원작 직접값/계산값/임시값을 구분하고 파일·field·단위·조건, 계산식/가정 또는 선정 이유/조정 기준을 남긴다. 이번에는 새 gameplay 수치를 선정하지 않았다.
- 기존 AssetManager를 사용하고 soft reference를 준비 시점에 로드한다. Main base에 모든 몬스터·무기 에셋의 hard reference를 모으지 않는다. 미로드 필수 데이터는 Ready 이전 실패로 설명하고 임의 지연 timer로 순서를 맞추지 않는다.
- 초기화 순서: 컴포넌트 구성 → ASC ActorInfo 연결 → 정의 로드/검증 → Attribute/Ability 부여 → 이동/표현/입력·AI 연결 → GameplayReady. 각 단계의 구조적 준비 상태와 외부 gameplay 태그를 구분한다.
- 종료 순서: 신규 요청 차단/세대 무효화 → 활성 실행·창·임시 제약·이벤트 정리 → 부여/로드 수명 정리 → Actor/Component 종료. 살아 있는 동일 Pawn의 재빙의는 ActorInfo 참조 갱신이며 무조건 모든 효과를 지우는 작업이 아니다.
- M1은 `UAbilitySystemComponent`를 그대로 부착해 인터페이스/ActorInfo/종료 계약만 만든다. M3에서 공통 요청의 실제 소비가 생길 때 `UKhazanAbilitySystemComponent`를 도입한다. reflected 멤버의 기본형과 subobject 이름은 보존하고 기본 subobject class 변경 시 BP/CDO를 검증한다. 빈 subclass를 미리 생성하지 않는다.

### V2-08. 현행에서 이관해야 하는 항목 전부

| 현행 위치 | 목표/시점 | 보존·검증 |
| --- | --- | --- |
| Character의 LocomotionComponent 조립 | M1에 ASC와 IAbilitySystemInterface 추가 | Player/Monster 공통 부모, ASC Owner=Avatar=Character |
| Player `RefreshLocomotionGait`와 CMC 설정 | M2 공통 Locomotion 적용, 입력 해석만 Player에 남김 | 현재 입력/L3/2단 gait 조작, CDO override/수치 출처 |
| Component `SetMovementAllowed`, `SetMaxAllowedGait`, `SetRotationMode` | M2 태그/원인별 제약→해결 결과 API | 요청 변화 시 즉시 재해결, 다중 원인 해제/회전 경쟁 |
| Controller `Input_Attack`의 빈 본문 | M3 공통 액션 요청 전달 | 시작/해제/버퍼/실패 이유, AI와 같은 실행 경로 |
| Controller `Input_Jump`의 직접 `Jump()` | M3에 사용 중인 Jump도 공통 요청/Jump Ability로 이관 | 지원 동작 보존, 새 공격만 GAS로 만들고 기존 입력이 gate를 우회하지 않음 |
| `Input_Jump`의 테스트 `PlayDynamicForceFeedback` | M3 피드백 소비/데이터로 이관 또는 테스트 잔재 정리 | 현재 테스트 값은 원작 검증값 아님. 실패한 점프에도 입력만으로 진동하는 경로 제거 |
| Main GT 수집/`NativeThreadSafeUpdateAnimation` | M4 공통 관측 경계 유지·필요 필드만 전달 | 실제 UObject 접근 스레드/수명 |
| Main `UpdateLocomotionSelection_AnyThread` | M4 Locomotion Linked Layer 인스턴스 | loop gait 히스테리시스/기존 포즈 |
| Main `UpdateTransitionData_AnyThread`, `SelectStopEntryFoot_AnyThread` | M4 Locomotion의 Stop 진입/발 이력 | 같은 Sync Group 소유, 진입 고정, 재초기화/재링크 |
| 미사용 방향각/Start/속도·snapshot 후보 | M4 실제 native/BP/직렬화 참조 확인 후 정리 | GroundSpeed 같은 간접 소비값 보존, Redirect/외부 참조 확인 |
| ABP_Player의 현행 이동 그래프 | M4 Main 합성+Locomotion layer | Start 제외/InGame/Walk·Run 발별 Stop/Sprint 단일 Stop 회귀 |
| 회피/장비/능력·레이어 교체 | M5 실제 데이터/실행/로드 수명 도입 | 무적 중첩·장비 제거·같은 클래스의 다른 데이터 |
| 미구현 타깃/워핑/타격 확장 | M6 | 액션별 root motion/호환 skeleton/socket, 정확도/저프레임 검증 |
| 미구현 상호작용 | M7 | 인터페이스·결과 한 번 확정·취소/대상 소멸 |
| 미구현 Walk Turn/SprintPivot | M8 | Walk 좌/우, Run Turn/모든 Start 제외, CMC 정책 아래 Pivot |
| 미구현 보스/레벨 진행/저장 | M9 | 태그·부여/레이어·Encounter reset, 새 Pawn 수명 |
| 다수 캐릭터/무기/패턴 확장 | M10 | 데이터 검증·회귀·실제 측정; 수량만으로 성능 보장하지 않음 |

기존 코드/에셋을 설계에 맞춘다며 자동 삭제/rename/재임포트하지 않는다. reflected 참조 이관은 실제 적용 단계에서 IDE 의미 기반 refactoring과 BP/직렬화/Redirect 검사를 함께 수행한다.

### V2-09. 이번 완료/미적용과 다음 절차

- 완료: v2의 채택 결정, 모든 기존 책임 변경, 7계층 경계, 태그/데이터/실행/취소/스레드/수명/Player·AI 계약, [M0–M10 마이그레이션](CHARACTER_TAG_ABILITY_MIGRATION.md), [M1 공동 구현 가이드](CHARACTER_TAG_ABILITY_STEP_1.md).
- 첫 단계의 게임 수정 대상은 `Khazan.uproject`, `Khazan.Build.cs`, `KhazanCharacter.h/.cpp`다. 이 목록은 사용자가 따라 할 예정 범위다. 이번에 게임 파일에 적용하지 않았다.
- 정적 근거: 현행 Character/Player/Monster/Controller/AnimInstance/모듈을 재확인했다. 기존 리포트 대상 게임 파일 39개는 동일한 hash였다. ABP는 저장 리포트의 범위를 재사용했다.
- 설치 UE 5.8.2 소스에서 ASC OnRegister/InitAbilityActorInfo/RefreshAbilityActorInfo/OnUnregister/DestroyActiveState와 IAbilitySystemInterface의 선언/호출을 확인했다. API 적합성 확인이며 제안 코드의 컴파일/PIE 완료가 아니다.
- M1 사용자 적용/빌드/PIE는 대기다. 이후 단계는 해당 완료 조건을 통과한 뒤 설명한다. 이전 Stop 진단 정리/미검증은 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)에 남긴 상태와 구분한다.



<a id="gas-versus-custom-action-review-20260909"></a>

## 2026-09-09 — GAS 필수 여부와 Gameplay Tags 기반 자체 액션 시스템 검토

### 검토 상태와 적용 범위

- 사용자 요청은 “GAS 플러그인이 꼭 필요한가, 제시한 자체 Tag-FSM 설명을 어떻게 평가하는가”에 대한 구조 검토다. 자체 시스템으로 전환하라는 결정이나 게임 파일 직접 편집 요청으로 해석하지 않는다.
- **7계층의 책임 분리는 GAS 없이도 구현할 수 있다.** 현재 v2가 선택한 엔진 구현은 GAS다. 아키텍처 원칙과 그 원칙을 구현하는 프레임워크를 구분한다.
- 이번 기록은 선택 근거를 보완하며 v2 / M0–M10 / M1의 채택 상태를 변경하지 않는다. 별도 CharacterStateMachine/HFSM 생성도 승인·채택하지 않는다.
- 실제 구현은 여전히 M1 적용 전이다. 현재 `Khazan.Build.cs`에는 `GameplayTags`가 있고 직접 `GameplayAbilities`/`GameplayTasks` 의존성은 없다. `Khazan.uproject`에 GAS의 명시적 활성화 항목이 없으며, `AKhazanCharacter`는 ASC/`IAbilitySystemInterface` 없이 LocomotionComponent를 소유한다. 다른 플러그인의 간접 활성화 여부까지 조사한 결론은 아니다.

### 엔진 사실과 설명의 정정

1. **Gameplay Tags는 GAS 없이 쓸 수 있다.** `FGameplayTag`, `FGameplayTagContainer`, `FGameplayTagQuery`와 태그 사전은 Runtime/GameplayTags 모듈의 기능이다. Epic의 GAS는 엔진에 포함된 GameplayAbilities 플러그인이며 ASC/GameplayAbility/GameplayEffect/AttributeSet/GameplayCue를 사용하려면 그 기반이 필요하다. [Epic Gameplay Tags](https://dev.epicgames.com/documentation/unreal-engine/using-gameplay-tags-in-unreal-engine)
2. GAS는 싱글플레이에도 사용할 수 있다. 공식 범위에는 RPG뿐 아니라 액션 어드벤처도 포함되며 멀티플레이 복제/예측을 지원한다. 우리 싱글플레이 마이그레이션에 멀티플레이 예측·Pawn 간 ASC 승계를 선행 구현할 필요는 없다. 다만 기능을 사용하지 않는다고 프레임워크의 코드/메모리 비용이 사라진다고 주장하지 않는다. “GAS는 무겁다”에서 초기 학습/설정 비용과 실제 CPU/메모리 비용을 분리하고, 후자는 대상 환경에서 측정한다. [Epic GAS 개요](https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-the-unreal-engine-gameplay-ability-system)
3. enum **변수 하나**가 한 번에 한 값을 갖는 것은 맞지만, 독립 enum 여러 개·bit flag·직교 상태로 동시 조건을 표현할 수도 있다. `FGameplayTag` 자체도 태그 하나이며 여러 태그는 Container가 담는다. 태그의 이점은 공통 어휘·계층 조회·데이터 관계를 공유하기 쉽다는 것이다. 태그만으로 배타 전이·우선순위·취소·원인별 소유권이 생성되지는 않는다.
4. “현업에서 싱글 하드코어 액션은 이런 구조를 아주 많이 쓴다”는 빈도나 원작 카잔의 실제 내부 구조는 이번에 입증하지 않았다. 프로젝트 선택의 근거는 요구 기능/팀의 유지 비용/검증이며 출처 없는 업계 일반론이 아니다.
5. `Tags_CannotAct`에 상태를 추가해 여러 액션의 신규 실행을 막는 방식은 가능하다. 모든 Player/AI 요청이 같은 관계 데이터와 공통 승인 경로를 사용하고, 해당 조건이 적용되는 액션군을 명시해야 한다. 그러나 이미 실행 중인 공격의 취소, 이동 제한, 해제 후 복구는 별도의 정책 소비가 필요하다. 일반 액션 차단 규칙으로 내부 피격·사망 처리까지 막지 않는다.
6. ANS로 콤보/무적/타격 창의 타이밍을 편집하는 방식은 GAS와 자체 구현 양쪽에서 가능하다. Notify에는 Queued/Branching Point의 실행 정확도·순서 차이와 필터/평가 조건이 있다. “타이머가 없으니 프레임 오차와 예외 정리가 없다”는 보장은 채택하지 않는다. [Epic Animation Notifies](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-notifies-in-unreal-engine)
7. GAS도 프로젝트 규칙을 자동 완성하지 않는다. Ability의 활성화·Commit·Cancel·End와 태그 조건을 제공하지만 프로젝트는 적절한 종료와 자기 자원 정리, 콤보 관계·반응 우선순위·몽타주 실패를 구현해야 한다. 임의 DataAsset을 생성하는 것만으로 엔진이 관계를 소비하지 않는다. [Epic Gameplay Ability](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-gameplay-abilities-in-unreal-engine)

### 제시된 TryAttack/ANS_AddTag 예제에서 보완할 책임

| 항목 | 현재 예제의 한계 | GAS 사용 여부와 무관한 필수 계약 |
| --- | --- | --- |
| 공통 실행기와 개별 액션 | ActionComponent가 AttackMontage를 직접 재생한다. 같은 패턴으로 TryDodge/TryBreath의 세부 로직까지 누적하면 컴포넌트가 모든 행동을 소유하게 된다. | 입력 래퍼는 허용하되 공통 실행기는 승인·전환을 맡고, 개별 Action/Ability 실행은 독립 수명을 가진다. 같은 실행 방식은 읽기 전용 데이터 변형으로 재사용한다. |
| 태그의 중첩 | 표준 Container의 AddTag는 동일 태그를 중복 추가하지 않는다. 누가 몇 번 부여했는지는 기록하지 않는다. | 원인/실행별 handle과 집계 count를 관리하거나 단일 소유자가 유효 기여로부터 집합을 재계산한다. 모든 소비자의 임의 Add/Remove를 허용하지 않는다. |
| 무적 해제 | 회피와 다른 효과가 동시에 Condition.Invincible을 제공할 때 회피 End의 RemoveTag 하나로 다른 효과의 무적까지 사라질 수 있다. | 회피는 자신의 기여만 회수한다. 단순 count만 두더라도 중복 해제와 이전 callback을 막을 소유권 검사가 필요하다. |
| 공격 태그 일괄 제거 | “공격 관련 태그를 싹 지운다”는 방식은 병행 실행/효과가 제공한 상태를 지울 수 있다. | 취소된 실행이 소유한 태그·창·제약·delegate·타깃만 정리한다. 이전 실행의 늦은 End가 새 실행을 해제하지 못하게 한다. |
| 실행과 재생 성공 | PlayMontage 호출 뒤 Attack 태그만 넣으면 재생 실패에도 공격 상태가 남을 수 있다. 재생/중단 callback은 다른 실행을 재진입시킬 수 있다. | 외부 재생/취소 호출 전 유효 실행 문맥과 callback 식별 계약을 준비한다. 실패·취소·정상 종료를 공통 정리 경로에 연결한다. |
| 회피 전환 | 기존 공격을 먼저 끊고 나서 스태미나/필수 리소스 부족을 발견하면 요청 실패로 진행 중인 공격을 잃는다. | 사전 승인과 자원 확인 뒤 허용된 전환을 수행한다. Commit/재생 실패의 비용 처리와 cleanup을 정의한다. 이미 취소한 공격은 자동으로 복원되지 않는다. |
| ANS의 역할 | ANS End만 기다리는 구조는 액션 취소/장비 제거/사망/EndPlay와 독립된 정리 계약이 없다. | ANS는 실행·몽타주·창을 식별한 열기/닫기 이벤트를 보낸다. 액션 종료가 자기 창을 모두 닫으며, 늦거나 중복된 End에도 안전하다. ANS 에셋 객체에 캐릭터별 실행 상태를 저장하지 않는다. |
| 공통 차단 조건 | 임의 태그를 추가해도 새 실행 차단과 현재 실행 중단이 저절로 연결되지 않는다. | 상태 변화 구독/관계 적용, 신규 승인, 진행 중 취소, 강제 반응을 각각 설계한다. 취소 창은 유효한 해당 실행에 연결한다. |

예를 들어 회피와 별도 상태 효과가 동시에 무적을 제공한다면, 회피 종료 후에도 효과의 기여는 남아야 한다. 이 요구는 싱글플레이에서도 발생하며 네트워크 기능을 없애도 사라지지 않는다.

`State.Action.Attack`은 액션 실행의 시작/끝이 소유하고, `Window.Combo` 같은 시간 구간은 그 실행 아래의 창으로 둔다. 콤보 창이 닫혔다고 공격 실행이 끝난 것은 아니다. 쿨다운/지속 상태 효과처럼 몽타주와 다른 시간축을 가진 책임에 필요한 timer까지 금지하지 않는다.

제시문에 있는 `State.Condition.*`/`State.Window.*`/`State.Debuff.*`는 이번에 새 별칭으로 등록하지 않는다. 현행 채택 어휘인 `Condition.*`/`Window.*`/`Status.*` 및 이벤트/Ability 분류와의 구분을 유지한다.

### 선택에 따른 구현 비용

| 책임 | 현재 v2의 GAS 기반 | 자체 Gameplay Tags 기반을 선택할 경우 |
| --- | --- | --- |
| 상태와 실행 | ASC, Ability/Task, 태그 조건·기여 기반을 사용하고 프로젝트 관계를 연결 | 공통 요청/전환 실행기, 실행 인스턴스, 수명·count/handle·관계 적용을 직접 구현 |
| 수치와 결과 | AttributeSet/GameplayEffect/계산 + 프로젝트 CombatResponse | 단일 수치 소유자·비용/피해/지속 효과·결과 확정·반응 경로를 직접 구현 |
| 피드백 | GAS GameplayCue에 연출 데이터/구현을 연결 | 태그 기반 연출 조회/전달/지속 연출의 생성·종료를 직접 구현. GameplayTags만으로 GAS GameplayCue API를 쓸 수 있다고 설명하지 않음 |
| 애니메이션/AI/공간/상호작용 | 프로젝트의 Linked Layer·ANS·BT·Combat·워핑·인터페이스 구현이 필요 | 같은 책임이 필요. 액션/효과/피드백 접속 부분을 자체 API에 맞춰 구현 |
| 학습/검증 | GAS 개념과 엔진의 실행 계약을 익히고 프로젝트 확장을 검증 | 자신이 작성한 경로는 직접 추적하기 쉽지만 런타임 기반 설계와 회귀 검증까지 팀이 소유 |

자체 구현은 필요한 기능만 작성하고 디버깅 경로를 직접 통제할 수 있다는 장점이 있다. 그 선택 자체를 잘못이라고 보지 않는다. 완전한 GAS 재구현이나 멀티플레이 기능을 의무화할 이유도 없다. 다만 여기서 비교하는 대상은 태그 타입과 enum 타입이 아니라 **현재 게임에 필요한 액션 실행 기반을 엔진에서 가져올지 직접 유지할지**다.

우리 범위에는 Player/일반 적/보스의 공유 액션, 공격·회피·피격·사망, 강인도·비용·무적/슈퍼아머 중첩, 장비 부여와 상호작용이 포함된다. 이 요구를 유지한다면 **현재 권고는 GAS의 필요한 책임을 단계별로 사용하는 것**이다. 이는 원작 내부 구조나 성능 우월성을 확인한 결론이 아니라, 자체 구현 시 필수로 떠안는 실행/효과 수명을 비교한 설계 판단이다. 싱글플레이가 이유라는 것만으로 선택을 뒤집지는 않는다.

향후 사용자가 자체 실행기를 선택하면 ARCH-02/03/05/09/13/16/17/18/19의 GAS 의존 계약과 M1–M3/M5의 접속·부여·효과 부분을 우선 개정하고 나머지 단계의 호출 계약도 점검한다. 첫 단계는 태그 사전·원인별 상태 기여·요청/실행/종료 계약을 최소 실제 액션 소비와 함께 확정하는 단계로 다시 설계한다. 현재 M1 가이드의 ASC/Interface 코드를 자체 컴포넌트 이름으로 단순 치환하지 않는다. 별도 거대 HFSM과 액션 실행 수명을 이중 구현하지 않는 원칙은 유지한다. 이 문단은 조건부 이관 범위이며 실행 지시가 아니다.

### 현재 AnimInstance와 검증 범위

- `KhazanAnimInstance.cpp`의 Game Thread 수집 → 값 snapshot → AnyThread 관측/포즈 선택을 실제 소스로 재확인했다. 어느 실행 기반을 선택해도 이 경계는 보존한다. 공격 승인·태그 원본·피해·콤보 수명을 Main AnimInstance로 옮기지 않는다.
- `bIsGrounded`/`bHasMovementInput`은 현재 snapshot에서 계산하는 관측이며 `LocomotionGait`/`StopEntryFoot`는 표현 선택/이력이다. 공유 gameplay 상태 원본을 태그로 통합한다는 이유만으로 이 bool/enum을 일괄 삭제하지 않는다. `Intent.bMovementAllowed`의 다중 원인 제약 이관은 계속 M2 대상이다.
- 표적 엔진 근거: 로컬 UE 5.8.2의 `Engine/Source/Runtime/GameplayTags/GameplayTags.Build.cs`는 GameplayAbilities 모듈에 의존하지 않는다. `Private/GameplayTagContainer.cpp`의 `FGameplayTagContainer::AddTag`(현재 808행)는 AddUnique, `RemoveTag`(860행)는 RemoveSingle과 parent 재계산이다. 이것이 원인별 중첩 기여 시스템이라는 뜻은 아니다.
- GAS의 `FGameplayTagCountContainer`는 `Engine/Plugins/Runtime/GameplayAbilities/Source/GameplayAbilities/Public/GameplayEffectTypes.h`에 있으며 기본 GameplayTags Container와 다른 타입이다. 자체 구현 가이드에서 GAS 의존성을 숨겨 끌어오지 않는다.
- 저장 표적 리포트 `Saved/ImportReports/Khazan_Character_Architecture_Review_20260908.json`의 게임 파일 39개가 현재 디스크와 동일한 SHA256임을 다시 확인했다. BP 정보는 저장 리포트를 재사용했으며 미저장 에디터 상태를 확인한 것은 아니다.
- 이번 변경은 Engineering 설계/상태 및 Animation 현행 정본의 검토 기록 추가뿐이다. 게임 소스·Build.cs·uproject·Config·BP·에셋 변경과 새 빌드/PIE/성능 측정은 없다.



<a id="gas-retained-m1-resumed-20260909"></a>

## 2026-09-09 — 자체 Tag-FSM 제안 철회, GAS v2 / M1 공동 구현 재개

- 사용자 확정: “이번 제안은 철회하고 기존 마이그레이션을 계속 진행, M1부터 아주 자세히 설명”한다. 앞선 GAS 대안 비교는 검토 이력으로 보존하며 자체 ActionComponent/FSM 전환안은 채택하지 않는다.
- ARCH-02/03/05/09/13/16/17/18/19를 포함한 기존 v2의 GAS 기반 계약과 M0–M10을 그대로 따른다. 별도 제어 HFSM/Tag-FSM이나 GAS 대체 실행기를 생성하지 않는다.
- 첫 범위는 M1의 엔진 UAbilitySystemComponent, IAbilitySystemInterface, Character 소유 Owner/Avatar, PostInitializeComponents의 최초 Init, 빙의 변화의 Refresh, EndPlay의 DestroyActiveState다. 프로젝트 전용 ASC/Ability는 실제 요청 소비가 생기는 M3에서 구현한다.
- “진행해보자 + 아주 자세히 설명”은 기존 공동 구현 방식에 따라 사용자가 직접 적용할 위치/각 줄/수명/에디터/검증 설명으로 처리한다. 이번에 게임 파일을 직접 변경하거나 M1 적용 완료로 기록하지 않는다.
- [M1 가이드 보충](CHARACTER_TAG_ABILITY_STEP_1.md#m1-resume-detail-20260909)에 인터페이스와 컴포넌트의 차이, Owner/Avatar와 Controller 구분, 헤더 조각의 조립 위치, 두 빙의 순서, 임시 조회 검증과 실패 진단을 추가했다.
- 현재 Source/Build.cs/uproject를 다시 확인했으며 M1은 적용 전이다. 저장 표적 리포트 대상 게임 파일 39개가 동일 SHA256이다. UE 5.8.2의 ASC/ActorInfo/Pawn lifecycle과 공식 문서를 정적으로 대조했으며 빌드/PIE를 실행한 결과는 없다.


### 같은 작업 후속 확인 — M1 플러그인 항목 부분 적용

- 위 초기 확인 이후 Khazan.uproject에 GameplayAbilities / Enabled=true 항목이 추가된 것을 디스크에서 확인했다. 어시스턴트가 이 게임 파일을 편집한 것은 아니다. M1은 이제 플러그인 설정만 부분 반영된 상태이며, 마지막 확인의 Build.cs/Character에는 나머지 M1 코드가 없다. 전체 M1 적용/빌드/런타임 완료를 뜻하지 않는다.



<a id="m2-movement-bridge-20260909"></a>

## 2026-09-09 — M1 소스 반영 확인 및 M2 공통 이동의 소단계 확정

- 사용자가 M1 완료를 보고했다. 현재 uproject/Build.cs/KhazanCharacter.h/.cpp에서 GAS 플러그인·모듈·ASC/Interface·Init/Refresh/DestroyActiveState가 반영된 것을 확인했다. M1은 사용자 완료 보고를 받아 다음 단계로 진행하며, 어시스턴트가 빌드 로그/PIE/빙의·종료 사례를 독립 검증한 것으로 확대하지 않는다.
- ARCH-04/05/08/09/10/16/18의 기존 책임을 유지하면서 M2를 [M2.1–M2.4](CHARACTER_TAG_ABILITY_STEP_2.md)로 나눈다. M2.1 태그 입력 제한/원시 입력 보존 → M2.2 CharacterDefinition/CMC 작성자/다중 원인 gait 정책 → M2.3 AI PathFollowing 구동 → M2.4 통합 검증이다.
- M2.1 제안 계약: Block.Movement.Input을 ASC effect 기여/count로 관리한다. LocomotionComponent는 BeginPlay에서 등록/초기 count 조회, 태그 경계 알림에서 재조회, EndPlay에서 자기 delegate handle 해제를 수행한다. 실제 효과 기여는 FActiveGameplayEffectHandle, 구독 수명은 FDelegateHandle로 구분한다.
- Intent.bMovementAllowed는 ASC 결과의 읽기용 투영이며 초기/미연결/종료는 false다. 공개 SetMovementAllowed(bool)를 제거하여 외부 쓰기를 금지한다. 원시 MoveInputWorld/InputAmount는 제한 중에도 보존하고 실제 입력 해제에서 지운다.
- 공통 IsMovementInputAllowed()가 ASC 유효성/태그 투영/Pawn의 기존 IsMoveInputIgnored를 합친다. Player 출력/속도 적용 gate와 AnimInstance GT snapshot이 이를 소비하고 worker는 기존 snapshot만 사용한다. 새 공통 helper는 이 두 실제 소비 경로 때문에 생성한다.
- 차단 알림은 Pawn의 미소비 일반 입력을 비우지만 CMC가 이미 소비한 입력/변위를 소급 취소하거나 Velocity/중력/Root Motion을 일괄 중단하지 않는다.
- 이 소단계에서는 Player의 기존 속도/회전 작성과 MaxAllowedGait 단일 setter가 아직 남는다. M2.2에서 이관한다. AI RequestDirectMove/RequestPathMove/ApplyRequestedMove는 별도 경로이므로 M2.1 태그 관측만으로 AI MoveTo 차단 완료를 선언하지 않는다.
- 현재 요청은 공동 구현 설명이다. M2 제안은 Source/BP/에셋에 직접 적용하지 않았다. 수치 이관은 기존 정본/표적 BP·원본 자료를 대조하는 M2.2 범위이며 이번에 신규 gameplay 튜닝값은 선정하지 않았다.


- 같은 M2.1 수명 보충: 원시 입력 보존에 대응해 Player::UnPossessed에서 자기 MoveInput/Sprint 요청을 먼저 정리한 뒤 M1 부모 UnPossessed/Refresh를 호출하도록 안내한다. 제한 효과는 해제하지 않는다. KhazanPlayer.h의 override 선언이 추가 대상이며 게임 적용은 아직 아니다.


<a id="m2-2-m2-3-contract-20260909"></a>

## 2026-09-09 — ARCH-04/05/08/09/16/17의 M2.2·M2.3 구체 계약

- M2.1은 전체 빌드까지 완료됐다. 후속 상세 구현은 [Step 2의 19–21절](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)을 정본 절차로 사용한다.
- ARCH-04: CharacterDefinition의 읽기 전용 config + 현재 raw intent + 활성 constraint 집합으로 ResolvedMovementPolicy를 매번 재계산한다. LocomotionComponent만 공통 CMC 속도/가감속/회전 정책의 최종 작성자다.
- ARCH-05/09: GameplayEffect, delegate, movement constraint, current intent source, AI path request는 서로 다른 handle/ID다. 해제는 자기 ID만 처리하며 과거 값을 복구하지 않고 남은 기여로 재계산한다.
- intent source는 현재 Controller별 token을 사용한다. 새 Possess가 이전 token을 무효화하고, 이전 callback은 새 Controller의 raw intent를 지우거나 쓰지 못한다.
- gait 상한은 가장 제한적인 기여를 선택한다. 회전은 배타 선택이므로 명시 priority, 같은 priority에서는 최신 발급 순서를 사용한다. Block.Movement.Input은 ASC effect/tag count가 이미 원인을 집계하므로 movement constraint로 중복 표현하지 않는다.
- ARCH-08: 표준 BT Move To는 Controller의 virtual RequestMove를 통과한다. AIController는 path request의 pause/resume/완료 수명을 관리하고, Khazan CMC는 RequestPathMove/RequestDirectMove의 실제 물리 진입을 같은 Locomotion permission으로 gate한다.
- Controller pause와 CMC gate는 서로 다른 원본이 아니다. 전자는 PathFollowing 시간/결과를 중지하고 후자는 물리 우회를 막는다. 구체 request ID와 pause 소유가 맞는 경우만 resume하며 abort/교체된 요청을 되살리지 않는다.
- ARCH-16/17: M2.2 Definition은 이동 config만 가진다. PostInitializeComponents에서 ASC ActorInfo 다음 config를 검증하고, 그 뒤 Possess/BeginPlay에서 입력·AI를 연결한다. Ability/Attribute/AI/animation soft data와 GameplayReady tag는 실제 M3 소비 전 선행 추가하지 않는다.
- 현재 수치 170/470/600, 15, 1800/1800, Yaw 540은 Player CDO/소스의 프로젝트 이관값이다. 수입 적에 같은 값을 쓰는 경우 M2 경로 비교용 임시값이며 원작 metadata로 표현하지 않는다.
- 이번 계약은 기존 ARCH ID를 변경하지 않고 구체화한다. 설명만 작성했고 게임 Source/BP/asset에는 적용하지 않았다. M2.4 이전에는 M2 완료가 아니다.
