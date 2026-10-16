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


## 2026-09-11 — ARCH-16/17: Character Definition의 기존 AssetManager 편입 결정

- [발견한 불일치] M2.2의 앞선 §20.19 안내는 `UKhazanCharacterDefinition : UPrimaryDataAsset` 인스턴스를 Player BP가 hard reference하도록 제안했다. 그러나 v2 V2-07은 기존 AssetManager를 통한 soft reference 준비를 채택했고, 프로젝트에는 이미 `UKhazanAssetData`/`PDA_AssetData` catalog와 `AssetData.*` key·`AssetLabel.Preload` 로딩 경로가 있다. 아직 Character Definition 에셋은 생성되지 않아 적용 데이터의 이관은 없다.
- [ARCH-16 결정] 현행 custom catalog를 유지하는 동안 Engine Primary Asset으로 직접 scan하는 타입은 `UKhazanAssetData` 하나다. `UKhazanCharacterDefinition`은 `UDataAsset` payload로 두고 `PDA_AssetData`의 `FAssetEntry`가 GameplayTag name에서 soft object path로 연결한다. 각 Definition을 별도 Primary Asset type으로 추가 scan하거나 같은 대상을 hard pointer와 catalog 양쪽에서 중복 소유하지 않는다.
- [선택과 수명] 공통 `AKhazanCharacter` class default는 기존 용어를 따른 `CharacterDefinitionAssetName` GameplayTag만 보관한다. GameInstance가 `AssetLabel.Preload` 집합을 준비한 뒤 Character가 tag로 Definition을 조회해 transient runtime pointer를 보관하고, LocomotionComponent는 검증된 config 값 사본만 Pawn 수명 동안 소유한다. Definition은 mutable gameplay 상태를 소유하지 않는다.
- [확장 방식] Player는 `AssetData.CharacterDefinition.Khazan`, 이후 실제 Monster/보스는 자기 Definition entry/tag를 가진다. 구체 캐릭터 이름을 공통 Character C++에 switch 또는 hardcoded path로 누적하지 않는다. `AssetData.*` tag는 asset catalog key이며 ASC Owned State가 아니다.
- [ARCH-17 준비 경계] Character Definition은 locomotion 초기화 전에 필수다. 따라서 현재 단계에서는 Preload label을 사용하고, 누락 tag/path/type은 명확한 로그와 이동 fail-closed로 끝내야 한다. 임의 timer 또는 Actor 생성 도중 숨은 동기 load 성공을 GameplayReady로 간주하지 않는다.
- [선행 보강] 현재 `GetAssetPathByName()`/`GetAssetSetByLabel()`은 lookup 실패 후 null을 역참조하고 runtime index는 `PreSave()` 재저장에 의존한다. `LoadSyncByLabel()`은 path name과 asset tag 두 key로 같은 객체를 cache해 release가 비대칭이다. Definition 소비를 추가하기 전에 lookup 실패 안전성, `PostLoad()` index rebuild, 단일 cache key/load·release 대칭을 바로잡는다.
- [절차 영향] 이 결정은 M2.2의 data 준비 소단계 내부 수정이다. M2.3 AI나 M3 Ability를 앞당기지 않는다. 앞선 hard-reference §20.19 안내는 적용 전 철회하며, AssetManager 보강 → Definition payload/tag 연결 → Data Asset catalog 등록 → Player/이후 Monster 선택 순서로 대체한다.
- [적용 상태] 이번 결정에서는 게임 C++·Config·BP·uasset을 수정하지 않았다. 정확한 소스 이관, 빌드와 Editor catalog/Player 설정은 사용자 공동 구현 후 검증한다.


## 2026-09-11 — ARCH-16 확장성 기준과 현행 Definition 심볼 확인

- [현행 소스] 사용자가 파일과 타입을 `KhazanCharacterDefinitionData.h/.cpp`, `UKhazanCharacterDefinitionData`로 통일했고 기반 타입은 `UDataAsset`이다. `/Game/Data/Character/DA_Character_Khazan`은 아직 생성되지 않았으며, `AKhazanCharacter`의 `CharacterDefinition`은 아직 `EditDefaultsOnly` 객체 포인터인 과도기 상태다.
- [확장성의 두 의미] Definition에 config·AbilitySet·Attribute·표현/AI 참조 필드를 늘리는 스키마 확장성은 `UDataAsset`과 `UPrimaryDataAsset`이 같다. `UPrimaryDataAsset`의 추가 이점은 `FPrimaryAssetId`, primary type scan, Asset Bundle, load/unload 및 cook/chunk 규칙을 실제 소비할 때 생기는 로딩·배포 확장성이다.
- [현행 결정 유지] 현재 `PDA_AssetData`가 이미 GameplayTag key, soft path, label과 preload 수명을 제공하므로 이 catalog를 정본으로 유지하는 동안 Definition payload는 `UDataAsset`으로 둔다. 같은 Definition을 custom `AssetData.CharacterDefinition.*` key와 별도 `KhazanCharacterDefinitionData:<AssetName>` PrimaryAssetId 양쪽에 중복 등록하지 않는다.
- [향후 전환 조건] 캐릭터별 Definition이 독립적인 bundle/menu/encounter/DLC chunk의 load root가 되어 Engine Primary Asset API로 직접 발견·감사·해제할 실제 소비가 생기면, 해당 도메인의 정본 ID를 `FPrimaryAssetId`로 이관하고 custom catalog entry를 제거한 뒤 `UPrimaryDataAsset`으로 전환한다. 기반 타입만 바꾸고 기존 catalog를 병행하는 것은 전환 완료가 아니다.
- [에셋 생성 경계] `DA_Character_Khazan` 파일 자체는 runtime 연결 전에 먼저 생성해도 안전하지만, manager 보강 전에는 `PDA_AssetData` preload 등록과 Player BP 연결을 완료한 것으로 보지 않는다. 현재 객체 포인터 칸에 DA를 지정하면 AssetManager를 우회하므로 지정하지 않는다.
- [적용 상태] 이번 확인에서는 게임 C++·Config·BP·uasset을 수정하거나 빌드/PIE하지 않았다. 설명과 정본 기록만 보강했다.


## 2026-09-11 — ARCH-16 Character Definition 에셋 네이밍 정렬

- [현재 확인] `/Game/Data/Character/DA_Character_Khazan`이 `UKhazanCharacterDefinitionData` 인스턴스로 생성됐다. 현재 `PDA_AssetData`와 `BP_KhazanPlayer` 바이너리에는 이 경로 참조가 없으므로 runtime 연결 전 이름을 정리할 수 있다.
- [명명 계약] Data Asset 인스턴스는 `<AssetTypePrefix>_<Responsibility>[_Variant]` 순서를 사용한다. Character Definition 인스턴스의 최종 권장명은 `DA_CharacterDefinition_Khazan`이다. `CharacterDefinition`은 전체 읽기 전용 캐릭터 정의, `LocomotionConfig`는 그 안의 이동 설정 한 영역, `Khazan`은 구체 variant다.
- [제외한 이름] `DA_Character_Khazan`은 책임이 빠져 이름만으로 데이터를 식별할 수 없다. `DA_KhazanConfigData`는 `ConfigData`라는 새 포괄 용어를 만들고 향후 AbilitySet·Attribute·표현·AI 참조까지 포함할 전체 Definition을 현재 Locomotion config와 혼동시킨다.
- [계층별 어휘] C++ 타입은 `UKhazanCharacterDefinitionData`, 에셋은 `DA_CharacterDefinition_Khazan`, catalog key는 `AssetData.CharacterDefinition.Khazan`, Character class-default selector는 `CharacterDefinitionAssetName`, runtime pointer는 `CharacterDefinition`, 이동 하위 값은 `LocomotionConfig`를 사용한다.
- [적용 경계] 이번 기록은 명명 검토다. 게임 에셋을 직접 rename하거나 catalog/BP에 연결하지 않았고, 빌드/PIE도 수행하지 않았다.


## 2026-09-11 — ARCH-16/17 AssetManager 과잉 보강 복원 범위

- [사용자 승인] 이번 직접 구현은 과잉 보강의 복원과 필요한 오류 수정에만 한정한다. 다음 Character Definition tag/selector/catalog/BP 연결은 설명만 제공하며 사용자가 적용한다.
- [복원 기준] Git HEAD의 AssetManager 설계로 돌아간다. `GetAssetByName()`의 기존 동기 로드 fallback, public `LoadSyncByPath()`/`ReleaseByPath()`, `ReleaseByName(FName)`, `NameToLoadedAsset`의 FName key를 복원한다. cache-only 조회 강제와 tag-key map 이관은 철회한다. ARCH-16의 기존 catalog 활용 결정은 유지한다.
- [필요한 보강] `PostLoad()`/`PreSave()`에서 기존 index 생성 본문을 공유하고 누락 lookup을 역참조하지 않는다. `GetAssetPathByName()`은 기존 값 반환을 유지하며 누락 시 빈 경로, `GetAssetSetByLabel()`만 nullable pointer를 반환한다. Manager는 이 결과와 catalog 누락을 안전하게 처리한다.
- [cache 대칭] 기존 path load의 `AssetPath.GetAssetFName()`을 공통 보관 key로 유지한다. label load의 개별 선행 load를 제거하고 batch load 뒤 같은 path key로만 보관한다. label release도 `ReleaseByPath()`로 동일 key를 지운다. tag명과 파일명으로 한 번의 label load가 두 cache 항목을 만들던 오류만 바로잡는다. 서로 다른 경로의 같은 leaf name 구분과 원인별 참조계수는 기존 설계의 범위 밖이며 이번에 새 체계를 만들지 않는다.
- [ARCH-17 경계] 기존 입력 소비의 lazy load 복원은 새 Character Definition의 준비 실패를 숨겨도 된다는 뜻이 아니다. 다음 Definition 연결에서 preload 완료/필수 데이터 준비 실패를 실제 소비 경계에서 검증한다. `GetAssetByName()` 호출 성공만으로 preload 성공이나 GameplayReady를 판정하지 않는다.
- [적용/검증] 이 절은 복원 전에 확정한 범위다. 실제 변경 및 빌드/실행 결과는 Engineering 현행/진단 문서에 별도 기록한다. 새로운 gameplay 수치, Character/Locomotion/Anim/GAS/에셋 변경은 이번 직접 구현 범위에 없다.


<a id="player-first-combat-architecture-20260915"></a>
## 2026-09-15 — v2.1 Player 우선 전투 제어 재정립 (ARCH-20–29)

### 결정의 범위와 기존 v2와의 관계

현재 Player는 공통 ASC 연결과 Player 이동 정책까지만 실제 검증됐고, 공격 요청·비용·피해 결과·피격 반응·콤보 수명은 아직 없다. 이 상태에서 AIController와 Behavior Tree부터 만들면 검증되는 것은 목적지 이동뿐이며, AI가 나중에 사용할 공통 액션 승인 계약은 검증할 수 없다. 공격을 임시 함수나 Montage 직접 재생으로 우회하면 Player 액션 기반을 만든 뒤 AI를 다시 이관해야 한다. 따라서 **M2.3 AIController 선행 구현을 보류하고 Player 전투 수직 절편을 먼저 만든다.**

- v2의 ASC 태그/GameplayEffect 상태 원본, Ability/Task 실행 수명, LocomotionComponent 이동 정책, CombatResponse 결과 처리, Main/Linked Layer 표현 분리는 유지한다.
- 이 절은 v2의 구현 순서만 Player 우선으로 고치고, 빠른 액션 전투에 필요한 실행 중재·콤보·방어 결과·SprintPivot 계약을 구체화한다.
- V2-02의 AI 생성 시점, V2-08의 `M2 AI → M3 전투` 순서, 기존 Migration의 M2.3 이후 순서는 충돌 범위에서 이 절과 최신 Player 우선 Migration이 대체한다. 과거 M2.3 설계는 미래 A1 검토 자료로만 보존한다.
- ARCH-12의 Player/일반 적 공통 검증은 최종 공통 계약의 합격 조건이다. 각 공통 타입의 첫 소비를 반드시 AI에서 동시에 구현하라는 뜻으로 사용하지 않는다. Player와 무판단 시험 대상에서 계약을 먼저 고정한 뒤 AI를 두 번째 요청 어댑터로 연결할 수 있다.
- 이번 결정은 설계 문서와 마이그레이션 변경이다. Source, BP, DataAsset, 애니메이션 에셋을 수정하거나 빌드·PIE를 새로 수행한 결과가 아니다.

### ARCH-20–29 결정표

| ID | 채택 결정 | 이유와 적용 범위 |
| --- | --- | --- |
| ARCH-20 | Player 액션·자원·전투 결과를 먼저 수직 검증하고 AIController 구현은 뒤로 이동한다. | 현재 AI가 호출할 공통 액션 계약이 없으므로 이동 전용 AI를 먼저 만들면 전투 AI 이관 비용이 생긴다. 완료된 M1/M2.1/M2.2는 유지한다. |
| ARCH-21 | Player 상태는 하나의 거대 enum/HFSM이 아니라 서로 독립적인 사실의 소유자로 나눈다. | 공격·무적·공중·콤보 창·스태미나 상태는 동시에 존재할 수 있다. ASC, Ability, AttributeSet, CMC, Locomotion, Anim이 자기 사실만 쓴다. |
| ARCH-22 | 공통 ASC가 일반 액션 요청과 하나의 전신 액션 실행 lane을 중재하고, Ability는 자기 실행 ID와 국소 phase를 소유한다. | 공격·회피·패링·피격·사망의 동시 실행과 교체를 한 경로에서 판정하되 passive/독립 Ability까지 직렬화하지 않는다. |
| ARCH-23 | PlayerController와 미래 AIController는 서로 다른 의도 생성자이며 같은 공통 요청/승인 결과를 소비한다. | Player는 장치 입력을 의미 입력으로 바꾸고, AI는 전술적 Action을 선택한다. AI가 Player 입력 태그를 흉내 내거나 양쪽이 Montage를 직접 재생하지 않는다. |
| ARCH-24 | 콤보 실행 문맥과 해금 원본을 분리한다. | 활성 Combo Ability가 현재 node·창·buffer를 소유하고, 영속 Progression/Save가 해금 사실을 소유한다. 읽기 전용 Combo Definition은 가능한 edge와 요구 조건만 정의한다. |
| ARCH-25 | HP/Stamina/Poise는 AttributeSet/GameplayEffect 경로만 쓰고, 행동 불가 여부는 각 Ability 비용/요구 조건과 이동 정책이 판정한다. | `bCanAct`나 Character의 복제 float 하나로 공격·회피·Sprint를 함께 막지 않는다. 비용 실패는 기존 실행을 취소하지 않는다. |
| ARCH-26 | 타격 후보와 방어 판정과 최종 결과를 분리하고, 패링/튕김은 실행 ID가 있는 CombatResult로 양쪽에 전달한다. | 대상이 방어 성공을 확정하기 전에 피해를 적용하거나 Player가 Monster 구체 타입을 직접 경직시키지 않는다. |
| ARCH-27 | SprintPivot은 LocomotionComponent가 소유하는 짧은 이동 maneuver이고 별도 GameplayAbility로 중복 구현하지 않는다. | 입력을 유지한 큰 방향 반전은 일반 입력 해제 Stop과 다르다. 액션 승인 경로는 활성 Pivot을 명시적으로 중단할 수 있고 Linked Locomotion Layer는 포즈만 재생한다. |
| ARCH-28 | 공중 여부는 CMC의 물리 사실, 추락 결과는 gameplay 결과, 사망은 Pawn 수명의 Effect, 부활/리스폰은 외부 수명으로 분리한다. | `bIsFalling`, `bDead`, Death Montage 종료, 새 Pawn 생성이 하나의 상태 전이로 섞이지 않게 한다. |
| ARCH-29 | 미래 AI는 인지·전술 선택·이동 요청만 AI 계층에 두고, 비용·취소·콤보·피격·사망 실행은 Player와 같은 공통 계층을 사용한다. | Behavior Tree/StateTree 선택은 콘텐츠 요구가 생길 때 결정한다. BT Task는 요청/실행 ID를 기다리고 자신이 만든 요청만 Abort한다. |

### Player 상태의 실제 소유자

| 사실 | 작성자 | 소비자와 종료 규칙 |
| --- | --- | --- |
| 장치 입력, 입력 phase, 카메라 기준 방향 | `AKhazanPlayerController`와 Player 입력 어댑터 | Locomotion 또는 공통 ActionRequest로 즉시 전달. Completed/Canceled/UnPossessed에서 자기 입력만 정리 |
| Gameplay 준비, Dead, Stun, Invincible, SuperArmor, 입력 차단 | ASC에 적용된 Ability/GameplayEffect의 태그 기여 | 요청 승인, CombatResponse, Locomotion, UI가 읽는다. 원인별 Effect/실행 수명으로 제거 |
| HP, Stamina, Poise | AttributeSet과 GameplayEffect/Calculation | Ability 비용, 전투 결과, UI가 읽는다. Character float로 복제하지 않음 |
| 현재 전신 액션 | 활성 GameplayAbility + 공통 ASC의 exclusive lane | Spec/실행 ID로 식별. 정상·취소·실패·사망·EndPlay에서 해당 실행 자원만 정리 |
| 공격 한 실행의 현재 combo node, 입력 buffer, hit/window 문맥 | 활성 Combo/Attack Ability | 같은 실행의 Notify/Task/관계 해석이 소비. Ability 종료 때 전부 폐기 |
| 해금된 스킬과 영속 진행 | Progression/Save 계층 | Pawn 준비 시 Ability grant 또는 해금 태그로 투영. 새 Pawn에도 다시 적용하며 Combo Ability가 Save를 직접 읽지 않음 |
| raw 이동 의도, gait/회전 해결, 이동 제약, SprintPivot maneuver | LocomotionComponent | CMC와 Anim snapshot이 소비. source/constraint/maneuver별 handle 또는 세대 ID로 중단·정리 |
| 위치, 속도, 바닥, Falling | CMC/엔진 물리 | gameplay와 animation이 관측. gameplay 소비가 실제 생길 때만 ASC tag로 edge를 투영하며 CMC 원본을 대체하지 않음 |
| loop/Stop/Pivot pose와 Stop 발 이력 | Main snapshot을 받는 Locomotion Linked Layer | pose 선택에만 사용. 공격 허가·피해·사망의 원본이 아님 |
| AI 감지 대상, 거리 판단, 다음 행동 후보 | 미래 AIController/Brain | 공통 이동·ActionRequest를 만들고 결과/실행 ID를 기다린 뒤 폐기 |

`EPlayerState` 하나로 위 행을 합치지 않는다. Ability 내부의 `Startup/Active/Recovery` 같은 국소 phase enum, Locomotion의 `None/SprintPivot` 같은 배타 maneuver enum, CMC MovementMode는 각각 자기 수명 안에서 사용할 수 있다. 이것들은 전체 gameplay 상태를 서로 덮는 두 번째 원본이 아니다.

### 공통 ActionRequest와 전신 액션 lane

1. PlayerController는 `Input.Action.Attack` 같은 의미와 Started/Completed/Canceled phase를 보낸다. 연속 호출이 필요하지 않은 공격을 매 frame `Triggered`로 제출하지 않는다. 미래 AI는 물리 입력을 만들지 않고 `Action.Attack.*`처럼 선택한 gameplay action을 요청한다.
2. 공통 ASC는 요청 ID를 발급하고 Ready, Dead/Stun/Block, Ability grant, 관계, 현재 취소 창, 필수 target/resource, 비용 가능성을 사전 검사한다. 결과는 최소한 실행됨, 실행 중 buffer로 인수됨, 거절됨과 구체 이유, 관련 실행 ID를 구분한다.
3. 전신 액션 lane은 공격·회피·패링·피격·사망처럼 pose와 이동을 함께 점유하는 실행을 한 번에 하나만 승인한다. 재생과 무관한 passive, resource regen, 관측 Ability는 독립 실행할 수 있다. 어떤 Ability가 lane을 점유하는지는 Ability metadata/관계가 정하며 Character enum이 정하지 않는다.
4. 후보가 실패했을 때 기존 액션을 먼저 취소하지 않는다. 전환 중재는 후보의 사전 승인과 lane 예약, 실제 활성화/비용 Commit, 기존 replaceable 실행 취소의 경계를 추적해야 한다. 새 실행이 montage·hit window·이동 제약을 노출하기 전에 실패 cleanup이 가능한 상태여야 한다.
5. HitReact/Death 같은 내부 반응 요청은 일반 입력 차단을 우회할 수 있지만 임의 `force` bool로 모든 검사를 생략하지 않는다. 유효한 CombatResult, 대상 Pawn, 원인 실행 ID를 확인하고 관계표에 정의된 취소만 수행한다.
6. 공통 입력 buffer와 Combo buffer를 섞지 않는다. Combo Ability의 다음 타 입력은 해당 실행이 소유한다. 공격 recovery 중 Dodge처럼 서로 다른 Ability 사이의 queue가 실제 필요해지는 단계에서만 ASC가 만료 시각·우선순위·원 요청 ID가 있는 소수의 pending request를 소유한다.

첫 구현에서 `UKhazanAbilitySystemComponent`, Ability base, Ability grant/input mapping은 실제 Basic Attack 소비와 함께 만든다. 별도 Action Manager, Combo Manager, Player State Machine, 미사용 Relationship/Definition 타입을 한꺼번에 생성하지 않는다. 두 액션 사이의 관계 또는 같은 실행 클래스의 데이터 변형이라는 소비가 생기는 순간에 해당 데이터 타입을 추가한다.

### 콤보와 스킬 해금 계약

- 기본 연속 공격은 한 Combo Ability 실행이 여러 node를 진행하는 구조를 우선한다. 현재 node, 입력 buffer, 유효 window, 이미 소비한 입력, 실행 ID는 그 Ability 인스턴스의 mutable 상태다.
- Combo Definition은 node가 사용할 Action/Montage section과 edge의 입력 의미, 필요 해금, 상태 조건, 다음 node만 보관하는 읽기 전용 그래프다. 런타임 index나 `bComboQueued`를 DataAsset에 저장하지 않는다.
- Progression/Save가 해금 사실의 원본이다. Pawn 초기화는 해금 결과를 Ability grant 또는 `Unlock.*` 태그로 ASC에 투영하고 source grant handle을 기록한다. Combo edge는 이 투영만 읽는다.
- 비용·쿨다운·타깃 방식·실행 구조가 독립적인 Skill/Finisher는 별도 Ability다. Combo edge가 그 Ability를 공통 ASC에 요청하고 승인된 경우에만 현재 Combo 실행에서 전환한다. 그래프가 직접 비용을 차감하거나 Montage를 재생하지 않는다.
- 전신 액션 간 block/cancel은 Action Relationship 계약, 한 Combo 실행 안의 node 연결은 Combo Definition이 맡는다. 하나의 거대 관계 DataAsset에 두 의미를 섞지 않는다.
- 해금되지 않은 edge, 비용 부족, window 종료, target 소멸은 서로 다른 거절 결과다. 실패한 branch 때문에 이미 진행 중인 합법적인 공격을 임의로 취소하지 않는다.

### Stamina와 행동 제한 계약

- Attack/Dodge/Parry/Skill의 비용은 Ability cost/GameplayEffect로 Commit한다. UI 사전 표시는 예상값이며 실제 승인 원본이 아니다.
- Stamina가 부족하면 해당 새 요청만 거절한다. 같은 순간 진행 중인 다른 액션, 다른 원인의 이동 제약, regen Effect를 일괄 제거하지 않는다.
- Sprint 요청 자체는 현재처럼 Locomotion intent다. Sprint 중 drain과 부족 시 Run 이하 제한을 연결할 때 Locomotion은 Stamina 값을 직접 쓰지 않는다. 실제 소비 단계에서 resolved Sprint의 진입/이탈을 관측하는 하나의 source-owned gameplay 실행이 drain Effect와 gait constraint를 취득·해제하고, 해제·빙의 종료·사망에서 자기 handle만 정리한다.
- regen 지연, drain 주기, 각 행동 비용, 최소 잔량은 원작 metadata 직접값·원작 기반 계산값·임시 튜닝값으로 구분해 Character/Action 데이터에 모은다. 현재 문서에서는 gameplay 숫자를 확정하지 않는다.

### 타격, 패링, 튕김, 피격과 사망

1. Attack Ability가 실행 ID와 hit window ID를 가진 창을 열고, Combat 계층이 socket의 이전/현재 pose를 이용해 타격 후보를 만든다.
2. 대상의 방어 해석 경계가 Invincible, Dodge window, Guard/Parry window, 공격 속성, 방향/각도 조건과 중복 HitId를 검사한다.
3. 그 뒤 하나의 `CombatResult`를 확정한다. 결과는 피해, 방어, 패링 성공, 공격 튕김, Poise 반응, 사망 여부와 source/target/request/execution/window/hit 식별자를 구분한다.
4. 피해가 확정된 경우만 EffectSpec을 적용한다. 패링 성공이면 방어자에게 성공 결과를, 공격자에게 Deflected 반응 결과를 보내며, 방어자가 Monster 클래스를 cast해 몽타주나 상태를 직접 바꾸지 않는다.
5. CombatResponse는 결과를 받아 HitReact/Deflected/Death Ability를 요청한다. Death는 다른 반응보다 우선하고 Pawn 수명의 Dead Effect를 먼저 남긴다. Cue와 진동은 확정 결과를 받은 뒤 재생한다.

Parry window와 Invincible window는 활성 Ability 실행에 묶인 별도 기여다. Anim Notify State는 창의 시작/끝 신호를 전달할 수 있지만 최종 소유자는 Ability/Task이며 Notify End가 누락돼도 Cancel/EndPlay cleanup이 가능해야 한다.

### SprintPivot의 gameplay·이동·표현 경계

SprintPivot은 Sprint 입력을 놓아 생기는 일반 Stop이 아니다. **Sprint가 계속 요청되는 동안 현재 평면 이동 방향과 새 raw 입력 방향 사이에 큰 반전이 생겼을 때**, 현재 Sprint를 짧게 제동하고 반대 방향으로 다시 Sprint하는 Locomotion maneuver다.

- 판정 입력은 이전의 유효한 평면 이동/진행 방향과 새 `MoveInputWorld`다. 기존 `MovementDirectionAngle`은 Actor 정면 대비 속도 방향의 애니메이션 관측값이므로 Pivot trigger로 재사용하지 않는다.
- 진입 조건은 grounded, resolved Sprint, 유효한 raw 입력과 평면 속도, 활성 Pivot 없음, 더 높은 우선순위의 전신 액션/이동 차단 없음이다. 정확한 방향각 임계값·최소 속도·제동 시간·회전 속도·재생 구간은 원작 metadata를 우선 확인하고, 없으면 `SprintPivotConfig` 같은 한 설정 영역의 명시적 임시값으로 둔다.
- 진입 시 LocomotionComponent가 maneuver 종류, 세대 ID, 진입 방향, 목표 방향과 자기 이동 제약/구동 handle을 소유한다. 목표 방향은 한 실행 동안 고정하고 raw 입력은 계속 최신값으로 기록한다. 중첩 Pivot을 시작하지 않는다.
- Locomotion Linked Layer는 snapshot의 maneuver를 보고 Sprint Stop 계열 포즈의 필요한 짧은 구간을 재생한다. 현재 root-locked Stop/CMC 이동 경계는 유지하며 ABP가 gameplay maneuver의 완료 원본이나 공격 승인자가 되지 않는다.
- 완료 시 자기 제약만 해제하고 최신 raw 입력과 현재 Stamina/태그 정책을 다시 해결한다. 입력이 여전히 유효하고 Sprint가 허용되면 새 방향 Sprint로 복귀하고, 입력이 해제됐으면 일반 Stop/Idle 규칙으로 간다.
- Attack/Dodge/Parry 승인, HitReact/Death, Falling, UnPossess/EndPlay는 활성 maneuver 세대가 맞을 때 Pivot을 중단하고 자기 handle을 정리한다. 늦은 animation callback은 새 Pivot이나 새 Pawn을 끝내지 못한다.

따라서 Pivot은 공통 액션 승인과 피격 취소 계약이 생긴 뒤 구현한다. 먼저 Pivot bool과 Anim 전이를 추가하면 공격/피격이 들어온 뒤 Locomotion과 Ability 중 누가 회전·제동·종료를 소유하는지 다시 고쳐야 한다.

### 추락, 사망, 부활/리스폰

- CMC MovementMode와 물리 속도가 공중 여부의 원본이다. grounded 전용 Ability가 필요해질 때 movement mode edge를 ASC tag/이벤트로 투영할 수 있지만 매 frame 다른 bool을 독립 작성하지 않는다.
- 추락 높이/낙하 속도/착지 표면으로 결과를 계산하는 소비가 생기면 fall 시작과 impact context를 한 실행이 보관하고, 착지에서 환경 `CombatResult` 또는 전용 consequence를 확정한다. 단순 Falling pose를 위해 피해 Ability를 항상 실행하지 않는다.
- 사망은 CombatResponse가 확정하고 Dead Effect가 Pawn 수명 동안 유지된다. Death Ability는 입력/이동 정리와 연출 수명만 소유한다.
- 체크포인트 리스폰은 Encounter/Checkpoint/Progression이 새 Pawn을 만들고 Definition, Attribute, AbilitySet, 해금을 다시 적용하는 외부 수명이다. 전투 중 제자리 부활이 실제 게임 기능으로 필요하면 Dead를 제거할 권한과 비용을 가진 별도 Resurrection Ability/Effect로 설계하며 Death Montage 종료와 혼동하지 않는다.

### 미래 AI Monster 구조

- AIController/Brain은 감지 결과와 전술 기억을 소유하고 접근, 거리 유지, 공격 후보, 방어 후보를 선택한다. 캐릭터의 HP/Stamina/현재 액션 원본을 복제하지 않는다.
- PathFollowing은 원거리 접근과 일반 이동 intent를 Locomotion에 전달한다. 근접 공격의 최종 정렬, 회전 고정, Motion Warping, hit window는 승인된 Ability 실행이 소유한다.
- AI의 BT/StateTree Task는 ActionRequest 결과와 실행 ID를 기다린다. Abort 시 자기 request/execution만 취소하며 `StopAllMontages`, 전체 태그 제거, 전체 Ability 취소로 정리하지 않는다.
- Player와 AI가 공유하는 것은 ASC 승인, Ability/Effect, CombatResult, Locomotion constraint, Action/Character data다. 입력 mapping, 카메라, perception, 전술 점수, path 목적지는 공유 대상이 아니다.
- AI 프레임워크를 Behavior Tree, StateTree, Utility 조합 중 무엇으로 정할지는 실제 Monster 한 종의 패턴·거리·협동/예약 요구를 정리한 뒤 A1/A2에서 결정한다. 현재는 AIController, custom CMC, Blackboard, BT 시험 에셋을 만들지 않는다.

### 현재 소스의 판정과 수정 시점

| 현재 영역 | 판정 | 다음 변경 시점 |
| --- | --- | --- |
| `AKhazanCharacter`의 엔진 ASC, `IAbilitySystemInterface`, LocomotionComponent, Definition selector | 공통 조립 위치로 유지한다. 거대 Player 상태를 추가하지 않는다. | P1에서 실제 요청 중재 소비와 함께 concrete ASC를 `UKhazanAbilitySystemComponent`로 바꾸고 기존 subobject 이름/기반형 reflected 계약을 보존 |
| `AKhazanPlayerController`의 Enhanced Input binding | 장치 입력 어댑터 책임은 맞다. 현재 Attack은 비어 있고 Jump는 `Character::Jump()` 및 시험 진동을 직접 호출한다. | P1에서 Attack/Jump를 공통 요청으로 이관하고 진동은 확정 Cue/결과 경로로 이동 또는 테스트 잔재 제거 |
| `AKhazanPlayer`의 이동 입력 변환과 Sprint toggle | 현재 책임에 맞으며 M2.2 검증 결과를 보존한다. 공격·콤보·피격 bool을 추가하지 않는다. | Stamina/Pivot 소비가 생길 때 공개된 Locomotion 계약만 확장 |
| `UKhazanLocomotionComponent`의 intent, constraint, resolved policy | 유지한다. 현재 Player 경로의 단일 CMC 정책 작성자는 적절하다. | Sprint resource 소비 시 gait edge, P5에서 maneuver 수명 추가. AI path gate용 custom CMC는 A1까지 보류 |
| `UKhazanCharacterDefinitionData`의 LocomotionConfig | 읽기 전용 정의와 catalog 선택 계약을 유지한다. | P1부터 실제 소비가 생긴 AbilitySet/초기 속성/표현 참조만 단계별 추가. 미래 AI 설정을 지금 빈 필드로 넣지 않음 |
| `AKhazanMonster` 빈 공통 Character shell | 미래 공통 대상 기반으로 보존한다. | P3의 무판단 전투 시험 대상에는 사용할 수 있으나 AIController/BT는 연결하지 않음 |
| Main AnimInstance의 현재 loop/Stop | 현재 동작을 보존하고 gameplay 상태 저장소로 확장하지 않는다. | P4에서 기존 pose/Stop 이력을 Locomotion Linked Layer로 옮긴 뒤 P5 SprintPivot 포즈를 그 영역에 추가 |

빈 `BeginPlay`/`Tick`의 정리는 기능 경계가 안정된 뒤 할 수 있는 소규모 정리이며 Player 전투 기반의 선행 조건이 아니다. 현재 변경 대상 목록을 늘리기 위해 별도 리팩터링 단계로 만들지 않는다.


## 2026-09-15 — ARCH-04/20/27/29: Khazan CMC 생성 조건 확정

- [판정] 이전 M2.3의 `UKhazanCharacterMovementComponent : UCharacterMovementComponent` 방향과 inherited default subobject 교체 방식은 유효하다. 정확한 구조는 CMC를 감싸는 별도 wrapper component가 아니라 엔진 CMC의 project subclass다.
- [엔진 근거] 로컬 UE 5.8.2에서 `UCharacterMovementComponent::RequestPathMove`와 `RequestDirectMove`는 virtual이고 PathFollowing이 acceleration 설정에 따라 둘 중 하나를 호출한다. `ACharacter`는 `CharacterMovementComponentName`으로 기본 CMC를 생성하며 `FObjectInitializer::SetDefaultSubobjectClass`는 base class가 정의한 subobject class를 파생형으로 바꾸는 API다.
- [현재 생성 여부] P1 ActionRequest, P2 Attribute/Stamina, P3 CombatResult에는 custom CMC가 필요하지 않다. P4 표현 분리도 CMC subclass의 소비자가 아니다. 미래 사용 가능성만으로 빈 subclass를 지금 생성하지 않는다.
- [P5 조건] SprintPivot은 우선 LocomotionComponent의 maneuver와 기존 CMC 공개 API로 구현한다. 같은 frame의 자동 회전/가속 요청 경쟁, 별도 movement mode, low-level velocity 적분처럼 base CMC 외부에서 정확히 중재할 수 없는 실제 문제가 확인될 때만 P5에서 생성 시점을 앞당긴다.
- [A1 조건] AI PathFollowing은 Player의 입력 어댑터를 거치지 않고 CMC의 두 navigation request 함수로 들어온다. `Block.Movement.Input` 중에도 raw AI intent를 보존하면서 engine 요청은 마지막 경계에서 차단해야 하고 Controller pause만으로 직접 navigation request 우회를 막을 수 없다면 A1에서 custom CMC가 정당한 실제 소비자를 갖는다. 현재 목표 구조에서는 이 가능성이 높지만 A1 진입 검증 전의 무조건 필수 파일로 취급하지 않는다.
- [책임 제한] custom CMC를 만들면 navigation/물리 엔진 경계의 얇은 adapter로 둔다. LocomotionComponent가 계속 intent·gait·회전·constraint·maneuver 정책의 작성자이고, CMC는 승인된 값을 실행하거나 engine request를 전달/거절한다. CMC에 Ability 상태, Stamina, combo, AI 전술, path request ID를 소유시키지 않는다.
- [교체 방식] `AKhazanCharacter`의 `FObjectInitializer` initializer list에서 `ACharacter::CharacterMovementComponentName`의 class를 교체한다. 같은 이름 또는 다른 이름의 두 번째 movement component를 `CreateDefaultSubobject`로 추가하지 않는다. 기존 `GetCharacterMovement()` base pointer와 Locomotion 호출은 다형성을 통해 계속 동작한다.
- [별도 수명 문제] AI 자동 빙의 전에 Definition/ASC/Locomotion이 준비되는지에 따른 `PostInitializeComponents()` 순서 변경은 CMC subclass 교체와 별도 결정이다. A1의 실제 spawn/possess 호출 순서를 확인한 뒤 필요한 경우에만 적용한다.
- [재검토 대상] 과거 M2.3 코드의 두 override, pending request 정리, navigation intent handle 전달 설계는 A1의 시작점으로 유효하지만 확정 구현은 아니다. P1–P8에서 추가된 Ready/Dead/action/maneuver 계약과 당시 UE 소스를 다시 대조하고 표적 테스트한 뒤 채택한다.
- [적용 상태] 이번 확인에서는 Source/BP/CDO를 변경하거나 빌드·PIE를 수행하지 않았다. 현재 `AKhazanCharacter`는 엔진 기본 `UCharacterMovementComponent`를 계속 사용한다.


<a id="statetree-gas-p1-review-20260915"></a>
## 2026-09-15 — StateTree·GAS·입력 버퍼 대조 검토와 P1 단순화 제안

### 검토 상태

- 이 절은 사용자가 제시한 `StateTree + GAS 태그 관계 + Input Buffer/AnimNotify` 구성을 UE 5.8 공식 문서, 공식 Lyra 사례, 로컬 UE 5.8.2 API, 현재 P1 실습판과 대조한 **아키텍처 검토 결과**다.
- 게임 Source/BP/DataAsset/Animation asset은 변경하지 않았다. 아래 단순화안은 기존 ARCH-22와 P1 계약을 바꾸는 **채택 전 제안**이며, 사용자가 방향을 결정하기 전에는 새 정본으로 간주하지 않는다.
- 기존 P1-A 소스 적용은 이 재검토가 끝날 때까지 보류한다. 현재 P1 소스는 아직 적용되지 않았으므로 이관 비용은 문서 수정뿐이다.

### 공식성에 대한 판정

1. StateTree는 에픽이 제공하는 범용 계층형 상태 머신이며 일반 Actor에 붙일 수 있다. 그러나 확인한 공식 문서는 StateTree를 Player 액션 RPG나 콤보의 최상위 제어기로 권장하거나 `공신력 1위`로 순위를 매기지 않는다. 일반 Actor 지원과 Player 전투의 공식 표준이라는 주장은 구분한다.
2. GAS는 Ability의 활성화 조건·비용·취소·종료, 태그 기반 block/cancel/required 관계, 비동기 AbilityTask, 입력과 몽타주 실행 수명을 직접 지원한다. 공식 Lyra도 Jump·Dash·Melee 같은 Player 액션을 GAS로 실행하고 Input Tag, AbilitySet grant handle, Tag Relationship Mapping, Activation Policy/Group을 추가한다.
3. 애니메이션 타이밍에 맞춘 입력 버퍼는 액션 게임에 유용한 프로젝트 기능이지만, 고정 `0.2~0.3초` 큐 컴포넌트가 에픽의 필수 공식 하위 시스템이라는 근거는 확인하지 못했다. 그 숫자는 원작 metadata 직접값도 아니므로 채택하지 않는다.

### 현재 v2에서 유지할 책임

- ARCH-02/03의 ASC 태그·Effect가 공유 gameplay 상태를, 활성 GameplayAbility/Task가 액션 실행 수명을 소유한다는 경계는 유지 가치가 높다.
- ARCH-04의 LocomotionComponent → CMC 이동 정책, Presentation/AI/CombatResult/GameplayCue의 책임 분리, Main AnimInstance를 gameplay 상태 저장소로 쓰지 않는 계약도 유지한다.
- Player와 AI가 같은 Ability 실행 경로를 공유한다는 ARCH-23/29의 목표는 유지한다. 공유해야 하는 것은 입력 장치 모양이 아니라 Ability 활성화와 결과 계약이다.
- StateTree를 Player 액션의 두 번째 권위자로 추가하지 않는다. `Grounded`, `Attack`, `ComboBranch`, `HitReact`를 트리 상태로 다시 소유하면 CMC·ASC 태그·활성 Ability에 이미 존재하는 사실과 수명이 중복된다.

### 과도한 P1 영역

현재 P1 실습판은 최소 수직 절편 안에 다음을 동시에 도입한다.

- `Input.*`, `Action.*`, `Ability.*`의 세 겹 식별
- `FKhazanActionRequest/Result`와 다수의 별도 C++ 실패 enum
- Request ID와 Execution ID의 이중 번호
- 활성 입력 요청, 활성 실행, pending activation handshake의 여러 원장
- 단일 ActionRequest source 등록과 Player 입력 어댑터에 결합된 `State.Ready.Gameplay`
- 자체 `ExclusiveFullBody` lane

GAS에는 이미 `FGameplayAbilitySpecHandle`, Ability instance/activation info, `TryActivateAbility`, `AbilitySpecInputPressed/Released`, 활성화 실패 태그 callback, Ability 종료 callback과 취소 여부, Ability/Task 종료 수명이 있다. 위 P1 요소 대부분은 아직 존재하지 않는 AI wait/abort, stale hit callback, cross-ability buffer 문제를 미리 해결하면서 엔진 수명을 다시 추적한다. 따라서 **v2 전체가 과설계인 것은 아니지만 현재 P1 구현 계약은 과설계**라는 판정이다.

### 채택 제안: 얇은 GAS 입력 어댑터

1. `UKhazanAbilitySystemComponent`는 만든다. 현재 실소비는 Input Tag pressed/released 처리, AbilitySet grant handle 관리, GAS failure/end 관측이다.
2. AbilitySet entry는 Ability class와 선택적 Input Tag만 가진다. PlayerController는 Enhanced Input을 Input Tag pressed/released로 번역하고 ASC는 해당 spec에 엔진 `AbilitySpecInputPressed/Released`와 `TryActivateAbility`를 적용한다.
3. AI는 A2에서 Action/Ability tag 또는 보관한 spec handle로 같은 ASC의 Ability를 활성화한다. AI가 Player Input Tag를 흉내 내거나 PlayerController source 등록에 의존하지 않는다.
4. `UKhazanGameplayAbility`에는 실제 공통 소비가 생긴 항목만 둔다. P1에서는 활성화 정책이 필요하면 `OnInputTriggered` 정도를 둔다. 전신 동시 실행은 먼저 Ability tag block/cancel 관계로 표현하고, 두 번째 실제 동시성 사례가 생기면 Lyra식 `Independent / ExclusiveReplaceable / ExclusiveBlocking` 그룹을 검토한다.
5. Basic Attack Ability는 Montage AbilityTask와 자기 Locomotion constraint를 소유하고 모든 Ability 종료 경로에서 정리한다. Jump Ability가 Jump/StopJumping을 소유한다.
6. P1에서는 별도 ActionRequest/Result, Request ID, Execution ID, active request/execution map, pending activation handshake, custom full-body lane을 만들지 않는다. 활성화 실패는 GAS의 failure tag container/callback으로, 종료는 Ability end callback과 `bWasCancelled`로 관측한다.
7. `State.Ready.Gameplay`가 필요하다면 ActorInfo·필수 Definition·grant·Locomotion 같은 gameplay 기반 준비만 뜻하게 한다. 로컬 Player 입력 매핑 존재 여부를 Ready count의 필수 항으로 넣지 않는다.
8. P3 hit window에서 늦게 도착한 callback을 구분할 실제 필요가 확인되면 그 공격 Ability의 지역 generation/window token을 추가한다. A2에서 AI Task가 특정 요청의 승인·종료·Abort를 기다려야 할 때만 외부 request ticket을 추가한다.
9. P6 콤보 입력 버퍼는 활성 Combo Ability가 현재 node, 유효 window, buffered input 하나를 소유하는 형태로 시작한다. Attack→Dodge처럼 서로 다른 Ability 사이의 일반 큐가 실제 조작 시험에서 필요할 때만 ASC 또는 입력 router에 작은 cross-action buffer를 추가한다. Notify는 window 이벤트를 보내고 Ability/Task가 권위와 cleanup을 소유한다.

### StateTree를 추가할 수 있는 명확한 조건

- A2의 적 AI가 Patrol/Investigate/Engage/Retreat처럼 디자이너가 편집할 상호 배타적 상위 의사결정 흐름을 필요로 할 때
- 보스 phase 또는 Scripted sequence처럼 Ability보다 긴 orchestration 수명을 시각적 트리로 편집할 실제 소비자가 생길 때

이 경우에도 StateTree Task는 GAS Ability를 요청하고 그 완료를 기다리는 adapter여야 한다. Montage·비용·hit window·cancel window·피해 결과의 권위는 Ability/Task와 Combat 계층에 남긴다. Player의 `Grounded → Combat → LightAttack → ComboBranch`를 지금 StateTree의 단일 상태 축으로 만들지 않는다.


<a id="architecture-v2-2-simplicity-20260915"></a>
## 2026-09-15 — 아키텍처 v2.2 확정: GAS 중심 구조와 단순성 불변식

### 결정의 지위

- 사용자는 GAS 중심의 현재 책임 분리를 유지하고 Player 전투용 StateTree를 추가하지 않으며, 기능에 필요하지 않은 거대 구조·복잡한 관계·불명확한 코드와 이름을 이후 설계에서 배제하기로 확정했다.
- 바로 위 `StateTree·GAS·입력 버퍼 대조 검토와 P1 단순화 제안`을 채택한다. 이 절은 ARCH-22/23/24/26/29와 P1의 충돌 범위를 대체하는 최신 정본이다.
- 유지하는 핵심은 ASC의 공유 gameplay 상태, Ability/Task의 액션 수명, LocomotionComponent→CMC의 이동 정책, Combat 결과와 표현의 분리, Player/AI의 실행 코드 공유다. 과거 `ActionRequest` 구현 형태는 유지 대상이 아니다.
- 싱글플레이 현재 요구를 기준으로 구현한다. GAS의 엔진 제공 수명과 handle을 사용하되, 현재 요구에 없는 멀티플레이 예측 wrapper·범용 메시지 계층·재시도 protocol은 만들지 않는다.

### 변경된 ARCH 계약

| 관련 ID | v2.2 확정 계약 | 대체·보류 범위 |
| --- | --- | --- |
| ARCH-05/09 | 먼저 엔진이 반환하는 Spec/Effect/delegate/task handle과 Ability instance 수명을 사용한다. custom ID는 그것으로 구분할 수 없는 실제 stale/out-of-order callback이 있을 때 해당 소유자 안에만 추가한다. | 모든 자원에 Pawn/요청/실행/창/hit ID를 일률적으로 붙이지 않는다. 기존 Locomotion constraint/intent handle은 실제 중첩·stale source 검증 소비가 있으므로 유지한다. |
| ARCH-16 | 설정은 우선 Ability/CharacterDefinition의 명확한 필드에 둔다. 두 개 이상의 실제 variant가 같은 실행 코드를 공유하거나 디자이너가 독립 편집해야 할 때만 별도 DataAsset으로 추출한다. | `KhazanActionDefinition`과 `KhazanActionRelationshipData`는 필수 기반 타입이 아니다. optional 필드가 많은 만능 Action DataAsset을 만들지 않는다. |
| ARCH-17 | P1은 `State.Ready.Gameplay`를 만들지 않는다. ActorInfo와 필수 Definition이 준비된 뒤 Ability를 grant하며, 미부여 spec은 활성화될 수 없다는 엔진 경계를 사용한다. | 실제 비동기 부분 준비 상태를 여러 외부 소비자가 구분해야 할 때만 하나의 명확한 readiness 계약을 추가한다. 입력 mapping 존재 여부를 gameplay Ready count에 넣지 않는다. |
| ARCH-19 | 활성화 실패는 GAS failure tag/callback과 구체 로그로 관측한다. 소비자가 요구하지 않는 별도 C++ 실패 enum을 복제하지 않는다. | P1의 다수 ActionRequest 실패 enum과 결과 protocol을 폐기한다. UI/AI가 구체 결과를 실제 소비할 때 필요한 failure tag만 추가한다. |
| ARCH-22 | Khazan ASC는 Input Tag를 해당 Ability spec의 pressed/released 및 `TryActivateAbility`로 연결하는 얇은 adapter다. 실행의 권위와 cleanup은 Ability/Task다. | 공통 `ActionRequest/Result`, Request/Execution ID 원장, pending activation handshake, request source 등록, custom full-body lane을 폐기한다. |
| ARCH-23 | Player는 기존 `Input.Action.*` tag로 입력을 전달하고, AI는 A2에서 Ability tag 또는 Spec handle로 같은 Ability를 활성화한다. 공유 대상은 GAS 실행과 결과이지 동일 요청 DTO가 아니다. | AI가 Player 입력 tag를 흉내 내거나 미래 AI 때문에 Player용 broker를 선행 구현하지 않는다. |
| ARCH-24 | 첫 콤보는 활성 Attack/Combo Ability가 현재 단계와 buffered input을 지역 상태로 소유한다. 실제 원작 분기가 확인된 만큼만 데이터화한다. | P6 시작부터 범용 graph runtime, custom graph editor, 전역 FIFO buffer를 만들지 않는다. 선형 combo면 배열/명시적 다음 단계로 시작하고 실제 branching 때 edge를 추가한다. |
| ARCH-26 | 첫 `CombatResult`는 실제 두 소비자가 함께 필요로 하는 결과와 기존 엔진 문맥만 담는다. | source/target/request/execution/window/hit 식별자를 전부 복제한 만능 결과 구조를 선행 생성하지 않는다. hit 중복이나 늦은 callback에 필요한 지역 token은 해당 hit task/window가 소유한다. |
| ARCH-29 | AI Brain은 선택한 Ability를 활성화하고 엔진 Ability 종료를 기다린다. 특정 Task Abort가 자기 실행만 취소해야 하는 실제 문제가 생기면 그 Task에 최소 추적 handle/ticket을 둔다. | 공통 ActionRequest protocol과 전역 execution ledger를 AI 선행 조건으로 삼지 않는다. StateTree는 AI 상위 판단 또는 장기 orchestration의 실제 소비가 있을 때만 검토한다. |

### 구조 생성 기준

새 구조는 아래 질문을 모두 통과할 때만 만든다.

1. 현재 단계에서 실행되는 기능과 구체 소비자가 있는가?
2. 엔진 타입, 기존 owner의 private 함수나 지역 변수로 해결할 수 없는가?
3. 독립적으로 시작·종료·취소되는 수명이 있는가, 또는 실제 두 곳 이상이 공유하는가?
4. 새 구조가 제거하는 중복이 새 API·동기화·cleanup보다 큰가?
5. 실패·취소·EndPlay에서 누가 정리하는지 한 문장으로 말할 수 있는가?
6. 이름만 보고 요청, 현재 사실, 해결 결과, 최종 결과 중 무엇인지 알 수 있는가?

다음 기준도 고정한다.

- 새 tag는 작성자와 현재 소비자가 모두 있을 때만 선언한다.
- 새 enum은 실제로 선택해야 하는 둘 이상의 배타 값이 있을 때만 만든다.
- 새 delegate는 비동기 관측자가 실제로 있을 때만 만든다.
- 새 handle은 중첩 acquire/release 또는 stale callback 방지가 실제 필요할 때만 만든다.
- 새 interface는 서로 다른 구현 둘 이상이나 엔진/모듈 경계의 실제 결합 해소가 있을 때 만든다.
- 새 Component는 Actor와 함께 존재한다는 이유가 아니라 독립 상태와 수명을 소유할 때 만든다.
- 새 DataAsset은 디자이너 편집, 여러 variant 공유, 로드 경계 중 하나가 실제 필요할 때 만든다.
- 한 번 전달하는 값은 구조체 `Context`로 감싸지 않는다. 관련 인자가 반복되고 함께 진화할 때만 작은 문맥 타입으로 묶는다.
- wrapper가 호출을 그대로 전달하기만 하면 만들지 않는다. 검증·변환·수명 소유 중 하나가 있어야 한다.
- 튜토리얼식 한 줄 해설은 공동 구현 MD에 둔다. Production source 주석은 코드에서 드러나지 않는 이유·단위·수명·제약만 설명한다.

### 클래스별 단순화 판정

| 영역 | 판정 | 구현 기준 |
| --- | --- | --- |
| `UKhazanAbilitySystemComponent` | 유지 | P1의 실제 Input Tag→spec 입력/활성화가 첫 소비다. 요청 원장·combo·damage·AI 판단을 넣지 않는다. |
| `UKhazanGameplayAbility` base | 조건부 | P1 두 Ability가 실제로 공유하는 동작이나 ASC가 읽는 설정이 있을 때만 만든다. 이름만 있는 빈 base는 만들지 않고 필요 전에는 엔진 `UGameplayAbility`를 직접 상속할 수 있다. |
| `UKhazanAbilitySet` | 유지 | Character variant의 시작 Ability 묶음이라는 실제 데이터 소비가 있다. P1에는 Ability class와 기존 Input Tag만 두고 Effect/Attribute는 해당 단계에서 확장한다. 반환 Spec handle은 실제 제거·재부여 소비 범위에서만 보관한다. |
| Action Relationship asset | 보류 | Attack/Jump는 GAS 기본 tag 관계로 시작한다. P7에서 여러 Ability에 같은 관계가 반복돼 불일치가 생길 때 Lyra식 중앙 mapping을 도입한다. 범용 규칙 엔진을 만들지 않는다. |
| Activation Group/full-body lane | 보류 | 기본 block/cancel tag로 표현할 수 없는 두 번째 실제 동시성 사례가 생길 때만 세 가지 이하의 명확한 분류를 검토한다. |
| Combo Definition | 조건부 | P6에서 실제 공격 수와 분기만 표현한다. 단순 연속 공격이면 작은 배열로 시작하고, 해금 branching이 실제 확인될 때 edge를 추가한다. |
| Combat hit owner | 미확정 유지 | P3 첫 공격은 AbilityTask 또는 Ability 지역 객체로 수명을 닫는 방식을 먼저 검토한다. 여러 Ability가 같은 지속 추적 서비스를 공유해야 할 때만 `CombatComponent`가 정당화된다. |
| Combat response owner | 미확정 유지 | 결과→HitReact/Death 변환 책임은 유지하지만 별도 `CombatResponseComponent`를 미리 만들지 않는다. ASC/Character의 작은 함수로 부족한 실제 다중 소비가 생길 때 생성한다. |
| Targeting/Equipment/BossPhase/Interaction 타입 | 책임만 유지 | 해당 기능의 첫 수직 절편 전에는 클래스·인터페이스·데이터를 만들지 않는다. 문서의 계층명은 생성 의무가 아니다. |
| custom CMC | 조건부 | 기존 공개 CMC API로 해결하지 못하는 PathFollowing 우회나 low-level 구동 충돌을 A1/P5에서 실제 확인할 때만 subclass를 만든다. |

### 현행 Source 가독성 감사

- `FKhazanMovementConstraintHandle`과 현재 intent token은 중첩 제약 A/B, 개별 해제, 재빙의 stale source 시험을 실제 통과했으므로 현재 복잡도에 근거가 있다. 단지 더 일반화하기 위해 새 ID 계층을 얹지 않는다.
- `EKhazanLocomotionMode`는 현재 Source 소비가 없다. `AKhazanCharacter`, `AKhazanPlayer`, `AKhazanMonster`에는 기능 없는 Tick/BeginPlay override가 있고 Character tick도 켜져 있다. `KhazanLocomotionComponent.cpp`의 `InterchangeResult.h`도 현재 사용되지 않는다. 이들은 다음 관련 Source 정리 시 참조를 다시 확인하고 제거할 후보이며 새 기능의 선행 조건은 아니다.
- PlayerController의 지역 변수 `Action2/Action3/Action4`는 `TurnAction/JumpAction/AttackAction`처럼 의미 이름으로 바꿀 후보이다. 입력 callback도 이후 수정 시 Unreal식 한 가지 명명 규칙으로 통일한다.
- AssetManager의 `GetAssetByName`/`LoadSyncByName`과 Character의 `CharacterDefinitionAssetName`은 실제 타입이 GameplayTag라 이름이 정확하지 않다. BP/직렬화 영향을 조사하지 않은 즉시 rename은 하지 않으며, 관련 API를 다음에 손댈 때 `...ByTag`/`...AssetTag` 이관 가치를 검토한다.
- `AKhazanPawn`은 C++ 검색에서 자기 파일 외 소비가 보이지 않는 starter shell이다. Blueprint/asset 참조를 확인하기 전에는 삭제하지 않지만 공통 Character와 병행하는 새 기능 기반으로 사용하지 않는다.

### 명명 불변식

- `Request`는 아직 승인되지 않은 의도, `Active`는 현재 실행 중인 사실, `Result`는 확정 결과에만 사용한다.
- `Handle`은 소유 자원을 개별 해제·취소하는 opaque 영수증일 때만 사용한다. 단순 번호나 표시용 값을 handle이라 부르지 않는다.
- `State`, `Context`, `Data`, `Info`, `Manager`, `Processor`, `Helper` 같은 넓은 단어는 구체 책임을 대신하지 못한다. 타입 이름에는 `AbilityInput`, `MeleeHit`, `CombatResult`, `MovementConstraint`처럼 실제 대상을 넣는다.
- bool은 `bIs/bHas/bCan/bShould`로 질문을 표현하고 한 owner 내부 관측에 사용한다. 외부 gameplay 권한을 여러 bool로 복제하지 않는다.
- 함수는 `동사 + 대상`으로 작성한다. `Process`, `Handle`, `Update`만으로 의미가 끝나는 이름을 피하고 무엇을 입력받아 무엇을 바꾸는지 드러낸다.
- 같은 개념에 Input/Action/Ability/State tag를 모두 만들지 않는다. 장치 입력에는 기존 `Input.Action.*`, Ability 분류에는 `Ability.*`, 외부가 실제 관측하는 지속 사실에만 `State.*`를 사용한다.

이 단순성 규칙은 확장성을 포기하는 규칙이 아니다. 작은 owner와 엔진 수명을 유지하면 새 Ability는 기존 Ability를 건드리지 않고 추가할 수 있고, 실제 반복이 확인된 뒤 추출한 공통 타입은 요구가 분명하므로 사용과 유지보수가 더 쉽다.


<a id="architecture-v2-3-capability-components-20260915"></a>
## 2026-09-15 — 아키텍처 v2.3 확정: capability component와 단일 CombatComponent 경계

### 결정의 지위

- 사용자는 Component를 붙인 호환 Actor가 그 Component 이름에 맞는 재사용 가능한 능력을 얻어야 한다고 확정했다. 동시에 전투 책임을 여러 작은 Component로 기계적으로 나누지 않는다.
- 이 절은 v2.2의 단순성 불변식을 유지하며, `Combat hit owner 미확정`, `Combat response owner 미확정`과 P1의 pressed/released 선행 구현 범위를 아래 계약으로 구체화한다.
- 여기서 `모든 Actor가 사용 가능`은 아무 종류의 Actor에서도 무조건 동작한다는 뜻이 아니다. `UCharacterMovementComponent`가 `ACharacter` 계약을 요구하듯, 각 Component가 선언한 최소 owner 계약을 만족하는 모든 Actor가 같은 기능을 얻는다는 뜻이다. 필요 없는 범용화를 위해 owner 차이를 숨기는 adapter와 분기 묶음을 만들지 않는다.

### Component 채택 규칙

새 `UActorComponent`는 다음 조건을 만족할 때만 만든다.

1. Component가 제공하는 한 문장의 능력이 있다. 예: `LocomotionComponent는 Character의 이동 의도와 여러 이동 제약을 하나의 CMC 정책으로 해결한다.`
2. 지원하는 owner 계약을 명시할 수 있다. 예: `CombatComponent는 IAbilitySystemInterface를 통해 유효한 ASC를 제공하는 Actor를 지원한다.`
3. 붙인 뒤 외부 호출자는 owner subclass마다 다른 내부 구현을 알 필요 없이 같은 public API를 사용할 수 있다.
4. Component가 검증, 상태, 수명, cleanup 중 하나를 실제로 소유한다. 단순히 다른 객체의 함수를 같은 인자로 전달하는 wrapper는 만들지 않는다.
5. 실행 한 번에만 필요한 값은 Ability/AbilityTask의 지역 수명에 둔다. Actor 수명 동안 여러 실행이 공유해야 하는 값만 Component 멤버가 된다.
6. 하나의 응집된 능력을 다시 `AttackComponent`, `GuardComponent`, `ParryComponent`, `PoiseComponent`, `HitReactComponent`처럼 잘게 분해하지 않는다. 서로 독립적으로 부착·교체·종료해야 하는 실제 요구가 생기기 전에는 한 Component와 GAS 객체의 조합으로 해결한다.

### 채택한 런타임 구성

```text
전투 가능한 Character/Actor
├─ AbilitySystemComponent
│  ├─ 공유 gameplay 상태: tag / attribute / active effect
│  └─ 실행 인스턴스: granted ability / ability task
├─ LocomotionComponent       (ACharacter + CMC가 필요한 이동 능력)
└─ CombatComponent           (P3에서 도입할 공통 전투 교환 능력)

실행 한 번의 세부 수명
└─ GameplayAbility / AbilityTask
   ├─ montage
   ├─ 공격·취소 window
   ├─ 그 실행의 movement constraint handle
   └─ 그 실행의 hit 중복 방지 집합 또는 token
```

`AbilitySystemComponent` 자체가 이미 Actor에 Ability·Tag·Effect 실행 능력을 붙이는 공식 Component다. `UKhazanAbilitySystemComponent`는 이를 대체하는 전투 Manager가 아니라 프로젝트의 기존 `Input.Action.*` tag를 granted spec activation에 연결하는 얇은 확장이다.

### `UKhazanCombatComponent`의 정확한 역할

`UKhazanCombatComponent`는 P3의 첫 실제 공격 판정에서 만든다. Component를 붙이고 필요한 전투 설정을 초기화한 호환 Actor는 Character subclass 전용 공격/피격 코드를 추가하지 않고 같은 전투 교환 경계에 참여할 수 있어야 한다.

최소 owner 계약은 다음과 같다.

- owner는 `IAbilitySystemInterface`를 통해 유효한 `UAbilitySystemComponent`를 제공한다.
- 공격 Ability, Montage, 무기 수치 같은 콘텐츠는 CharacterDefinition/AbilitySet/Ability asset에서 제공한다. Component가 없는 데이터를 임의로 만들어 내지 않는다.
- skeletal mesh나 CMC가 필요한 동작은 그 기능을 요구하는 Ability/Task가 별도로 검사한다. 따라서 ASC를 가진 비Character Actor도 피해 수신처럼 자신이 지원하는 Combat API는 사용할 수 있다.

CombatComponent가 맡을 책임은 다음 범위다.

- owner ASC 연결을 한 번 검증하고 Component 수명 동안 안전하게 참조한다.
- 공격 실행이 만든 **확정된 접촉 후보**를 공통 전투 입력으로 받아 source/target 유효성 및 전투 참여 가능 여부를 검사한다.
- GameplayEffect spec과 GameplayEvent를 통해 피해 계산 및 HitReact/Death 실행으로 넘기는 공통 진입점을 제공한다.
- 여러 Ability 실행이 실제로 공유해야 하는 Actor 단위 전투 기록이나 delegate가 생기면 그 최소 상태와 cleanup을 소유한다.
- owner가 종료되면 자신이 등록한 delegate와 자신이 소유한 runtime 기록만 해제한다.

CombatComponent가 맡지 않을 책임은 다음과 같다.

- Enhanced Input binding과 Player 입력 해석
- Ability 활성화 수명, 비용, cooldown, block/cancel 규칙
- combo 단계, combo buffer, montage 재생 및 notify window
- damage 수치의 권위와 Attribute 변경 계산
- 이동 속도·회전·가감속 및 movement constraint 해결
- AnimGraph/Linked Layer 포즈 선택과 GameplayCue 표현
- AI 의사결정, lock-on/target 선택, 장비·성장 데이터

위 항목은 각각 기존 GAS Ability/Task/Effect/Attribute, LocomotionComponent, Animation/Cue, AI/Targeting/Equipment 경계에 남긴다. 특히 `CombatResponseComponent`를 함께 만들지 않는다. 첫 HitReact와 Death는 GameplayEvent로 반응 Ability를 활성화하는 경로부터 검증한다. 하나의 CombatComponent로도 표현할 수 없는 독립 수명과 실제 교체 요구가 확인될 때만 새 Component를 다시 심사한다.

### 붙이면 무엇을 얻는가

정확한 의미는 `CombatComponent 부착 + 유효한 ASC + 필요한 Definition/AbilitySet 설정`을 만족하면 다음을 얻는다는 것이다.

- Player, 일반 적, 보스가 같은 전투 입력·결과 경계를 사용한다.
- 각 Character subclass에 `TakeMeleeDamage`, `ReceiveParry`, `StartHitReact` 같은 서로 다른 함수를 반복해서 만들지 않는다.
- 공격 실행은 자기 Ability/Task 안에서 닫히고, 다른 Actor와 결과를 교환하는 순간만 CombatComponent를 통과한다.
- 해당 Actor가 지원하지 않는 mesh/weapon 동작 때문에 피해 수신 같은 공통 기능까지 막히지 않는다.

`Component를 Add하는 것만으로 설정 없는 공격 애니메이션까지 생긴다`는 계약은 채택하지 않는다. 그것은 Component가 콘텐츠 선택, 입력, 실행, 표현을 모두 떠안게 해 거대한 전투 Manager가 되기 때문이다.

### 지금 만들지 않는 이유와 생성 시점

현재 P1의 첫 소비는 `입력 tag → granted ability spec → activation`이며 다른 Actor와 교환하는 hit나 damage가 없다. 지금 CombatComponent를 만들면 ASC를 찾아 저장하는 빈 wrapper만 남으므로 Component 채택 규칙 4를 통과하지 못한다.

따라서 다음 순서를 고정한다.

1. P1에서 ASC 입력 활성화, Ability grant, BasicAttack/Jump 실행과 자기 cleanup을 완성한다.
2. P2에서 BasicAttack의 Stamina 비용 한 경로를 GAS Attribute/Effect로 검증한다.
3. P3.1에서 BasicAttack의 실제 접촉 후보와 대상에게 넘길 최소 데이터가 생기는 같은 변경 안에 `UKhazanCombatComponent`를 만든다.
4. 그 시점에 Player와 최소 한 종류의 적이 같은 Component 계약으로 한 번의 hit를 교환하는지를 검증한다.

### P1 입력 어댑터의 더 작은 시작점

P1 첫 절편의 실제 소비자는 한 번 누르는 Attack이다. 따라서 첫 `UKhazanAbilitySystemComponent`에는 `TryActivateAbilitiesByInputTag(const FGameplayTag&)` 하나만 구현한다. 이 함수는 Dynamic Spec Source Tag가 정확히 같은 granted spec을 찾고 엔진 `TryActivateAbility`를 호출한다.

- held 입력 배열, 매-frame input processor, pressed/released replicated event는 첫 절편에 넣지 않는다.
- Jump의 `WaitInputRelease`를 실제 구현하는 P1 후속 절편에서 엔진 `InputReleased` generic replicated event가 필요함을 확인하고 그때 press/release 전달을 추가한다.
- combo 재입력은 P6의 활성 Combo Ability가 실제 소비할 때 추가한다.

이 순서는 기능을 버리는 결정이 아니라 소비자가 생기는 빌드 checkpoint에 기능을 배치하는 결정이다.


<a id="architecture-v2-4-global-component-rule-20260915"></a>
## 2026-09-15 — 아키텍처 v2.4 정정: 모든 Component에 적용하는 capability 원칙

### 사용자 정정과 대체 범위

- 사용자가 든 `CombatComponent`는 capability component를 설명하기 위한 예시였다. 바로 위 v2.3이 그 예시에 지나치게 집중해 미래 P3의 중심 타입처럼 확정한 해석은 철회한다.
- 최신 원칙은 **현재와 미래의 모든 Component**에 동일하게 적용한다. Component는 호환 owner에 부착됐을 때 이름으로 예측 가능한 하나의 완결된 능력을 제공해야 하며, 코드 분류나 작은 책임 분할만을 목적으로 생성하지 않는다.
- v2.2의 GAS 중심 실행, 단순성 불변식, 실제 소비 전 타입 보류 원칙은 그대로 유지한다. v2.3의 일반 owner 계약과 Component 채택 질문도 유지하되 `UKhazanCombatComponent를 P3.1에서 반드시 생성한다`는 일정만 취소한다.

### 전역 Component 판정법

모든 새 Component 후보는 다음 순서로 판정한다.

1. 먼저 Ability/AbilityTask의 실행 지역 상태, 기존 Component의 응집된 함수, Actor의 composition 초기화 함수로 해결할 수 있는지 본다.
2. 그래도 Actor 수명 동안 독립적으로 유지되는 상태와 cleanup이 있고, 호환 owner 여러 종류가 같은 public API를 사용해야 할 때 Component를 선택한다.
3. 지원 owner를 지나치게 넓히지 않는다. `AKhazanCharacter` 계열만 지원하면 그것도 명확한 재사용 계약이다. 현재 소비자가 없는 임의 `AActor` 지원을 위해 adapter와 nullable 분기를 누적하지 않는다.
4. 붙인 Component를 쓰기 위해 owner subclass마다 별도 전달 함수와 상태 복사를 만들어야 한다면 API 경계를 다시 검토한다.
5. 한 기능을 여러 Component가 부분 소유하거나 같은 상태를 ASC tag, Character bool, Component enum으로 중복 작성하지 않는다.
6. Component 수를 줄이기 위해 서로 관계없는 기능을 하나의 Manager Component에 합치지도 않는다. 응집된 기존 owner에 함수로 둘 수 있으면 그 owner에 둔다.

### 현재 및 후보 Component 전수 판정

| 대상 | 현재 판정 | capability 계약과 경계 |
| --- | --- | --- |
| `UAbilitySystemComponent` / `UKhazanAbilitySystemComponent` | 채택 | 붙인 GAS owner가 Ability/Tag/Effect 실행 능력을 얻는다. Khazan subclass는 현재 Input Tag→granted spec activation 한 차이만 더한다. combo, damage, AI 결정을 넣지 않는다. |
| `UKhazanLocomotionComponent` | 채택 | 지원하는 Khazan Character가 입력/AI 이동 의도와 여러 이동 제약을 하나의 CMC 정책으로 해결한다. Config, intent, constraint, resolved policy는 한 이동 능력의 연속된 데이터이므로 현재 분해하지 않는다. |
| `UKhazanCombatComponent` | 조건부 후보 | 여러 전투 owner가 Ability/Effect만으로 닫히지 않는 공통 hit 교환 상태/API를 실제로 필요로 할 때만 만든다. P3 시작 자체가 생성 의무가 아니다. |
| `InputBufferComponent` | 현재 제외 | 첫 combo의 입력은 활성 Ability 지역 수명으로 충분하다. 여러 서로 다른 시스템이 같은 Actor 단위 buffer를 공유하는 실제 요구가 생길 때 다시 판정한다. |
| `CombatResponseComponent`, `GuardComponent`, `ParryComponent`, `PoiseComponent` | 현재 제외 | 우선 GAS Ability/Effect/Tag와 필요 시 하나의 기존 전투 경계로 구현한다. 이름별 파일 분할을 목적으로 만들지 않는다. |
| `TargetingComponent` | 조건부 후보 | lock-on 대상 탐색·선택·유지·해제가 Actor 수명의 독립 능력이고 Player/AI 등 복수 producer가 같은 API를 쓸 때만 만든다. 공격 한 번의 target은 Ability/Task 지역이다. |
| `EquipmentComponent` | 조건부 후보 | 장착 슬롯, 교체, 부여/회수 handle을 Actor 수명 동안 실제 소유할 때 만든다. 단순 무기 포인터 하나 때문에 선행 생성하지 않는다. |
| `InteractionComponent` | 조건부 후보 | 여러 상호작용 source/target이 동일 탐색·선택 수명을 공유할 때만 만든다. 대상 자체의 결과와 보상은 대상 owner에 둔다. |

이 표의 `조건부 후보`는 예약된 클래스명이 아니다. 해당 단계에서 기존 GAS/Actor/Component로 기능을 먼저 수직 검증하고, Component가 제거할 실제 중복과 소유할 수명이 확인될 때 최종 이름과 API를 결정한다.

### Component가 아닌 구조에도 같은 단순성 기준 적용

단편화를 막는 기준은 Component에만 한정하지 않는다.

- 별도 DataAsset은 같은 묶음을 두 곳 이상에서 재사용하거나 독립 로드·편집·교체할 때 추출한다.
- 별도 base class는 자식 둘 이상이 실제 공통 동작이나 계약을 공유할 때 만든다.
- 별도 interface는 서로 다른 구현 둘 이상을 한 소비자가 다뤄야 할 때 만든다.
- 별도 subsystem/manager는 world 또는 game instance 범위의 고유 수명과 복수 owner 조정이 있을 때 만든다.
- 한 owner에서 한 번 호출되는 짧은 초기화는 그 owner의 명확한 함수 또는 lifecycle 지점에 둔다. 전달만 하는 Component를 추가하지 않는다.

### P1 AbilitySet 재판정

현재 초기 Ability의 정적 작성자는 이미 `UKhazanCharacterDefinitionData` 하나이며, runtime grant owner는 자기 ASC를 소유한 `AKhazanCharacter` 하나다. 아직 장비, GameFeature, 직업 교체, 공통 적 패키지처럼 같은 Ability 묶음을 독립적으로 부여·회수하는 두 번째 source가 없다.

따라서 P1에는 별도 `UKhazanAbilitySet` DataAsset을 만들지 않는다.

- CharacterDefinition에 `InitialAbilityGrants` 배열을 직접 둔다.
- 배열 원소는 `AbilityClass`와 선택적 `InputTag`만 가진다.
- Character의 `PostInitializeComponents()`는 ActorInfo와 Definition/Locomotion 초기화 뒤 authority에서 이 배열을 한 번 Spec으로 grant한다.
- ASC가 Character와 함께 파괴되므로 현재는 반환 Spec handle 원장을 저장하지 않는다.

다음 중 하나가 실제로 생길 때 `UKhazanAbilitySet` 추출을 다시 검토한다.

1. 같은 Ability 묶음을 서로 다른 CharacterDefinition 둘 이상이 공유한다.
2. 장비·상태·게임 기능이 그 묶음을 독립적으로 부여하고 나중에 회수해야 한다.
3. 묶음 자체를 별도 asset으로 교체하거나 독립 로드해야 한다.

이때도 부여 source가 반환 Spec handle을 소유하고 자기 묶음만 회수한다. 미래 가능성만으로 지금 DataAsset, granted-handle struct, remove protocol을 만들지 않는다.


## 2026-09-16 — ARCH-17/22 P1.3 확인과 P1.4 적용 경계

- 실제 Source의 `UKhazanAbilitySystemComponent`는 Dynamic Spec Source Tag exact match 뒤 engine Spec handle로 `TryActivateAbility()`를 호출하는 얇은 adapter이며 ARCH-22 경계를 유지한다.
- 실제 Source의 `UKhazanBasicAttackAbility`는 빈 프로젝트 base 없이 `UGameplayAbility`를 직접 상속하고, CharacterDefinition의 초기 grant가 class와 `Input.Action.Attack` mapping을 제공한다. 별도 AbilitySet/readiness 원장을 만들지 않았으므로 ARCH-16/17과 v2.4 계약을 유지한다.
- 2026-09-16 UE 5.8.2 cold build는 성공했다. Definition asset에도 BasicAttack class와 Attack input tag가 저장돼 있다. PIE debug HUD의 Spec 정확히 한 개 여부와 locomotion 회귀는 사용자가 화면에서 확인할 범위다.
- 다음 P1.4는 PlayerController의 Attack `Started` edge를 기존 ASC adapter에 연결하는 제안이다. 새 tag, Component, request/result, held processor, pressed/released 전달을 만들지 않는다. 실제 Source 적용·PIE 완료로 기록하지 않는다.
- 아키텍처 계약 변경은 없다. P1.4 상세 절차는 `CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md`의 2026-09-16 절에 둔다.

## 2026-09-16 — ARCH-06/09/17/22 P1.4 적용 확인과 P1.5 실행 소유권

- 실제 PlayerController Source는 물리 Attack `Started` edge만 기존 ASC의 exact Input Tag adapter에 전달한다. Controller는 Spec handle, Montage task, movement constraint를 보관하지 않는다. 이는 ARCH-17/22의 입력·grant 경계를 유지한다.
- P1.5 제안에서 `UKhazanBasicAttackAbility`의 한 `InstancedPerActor` 실행이 `UAbilityTask_PlayMontageAndWait`, 발급 LocomotionComponent의 weak pointer, `FKhazanMovementConstraintHandle` 한 건을 보관한다. `EndAbility()`가 정상/중단/취소/EndPlay의 공통 cleanup 지점이며 다른 원인의 constraint를 제거하지 않는다. 이는 ARCH-06/09의 실행 수명과 handle cleanup 계약을 구체화한다.
- `LocomotionComponent`는 기존 공개 API로 제약을 합성하고 CMC policy를 다시 계산한다. Ability가 CMC, raw input, AnimInstance 파생 값을 직접 쓰지 않는다. Main ABP는 기존 `DefaultSlot` 합성으로 Montage를 표현한다.
- Ability 설정을 담는 `GA_BasicAttack_Khazan`은 native 구현의 content subclass이며 새 C++ 공통 base나 AbilitySet 계층이 아니다. CharacterDefinition의 기존 한 grant class를 이 Blueprint class로 교체하고 Input Tag는 유지한다.
- 후보 공격 Sequence의 직접 확인 길이는 `10.375 s`, Rate Scale은 `1.0`, root motion은 disabled다. 같은 폴더 8개가 같은 길이이므로 실제 Montage segment 구간은 아직 미확인이다. 임시 gait cap `Run`도 원작값이 아닌 handle 수명 검증값이다.
- 아키텍처 계약 변경은 없다. P1.5는 제안 상태이며 게임 Source/asset 적용·PIE 완료로 기록하지 않는다. 구체 절차는 `CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-4-applied-p1-5-montage-constraint-20260916`에 둔다.

<a id="skill-root-motion-combo-contract-20260916"></a>
## 2026-09-16 — ARCH-01/03/04/06/09/22/24 스킬 Root Motion·콤보 계약 정정

- 사용자 확정 방침에 따라 이 프로젝트의 스킬/공격 재생 자산은 Root Motion을 사용한다. 위 5.4절의 “공격마다 in-place 또는 Root Motion을 선택” 문장은 **스킬/공격 범위에서 대체**하며, locomotion loop/Stop의 현행 in-place 정책까지 일괄 변경한다는 뜻은 아니다.
- `UKhazanAbilitySystemComponent`는 granted Spec, 활성화, owned tag/effect, 그리고 실제 소비자가 생기는 시점의 일반 pressed/released 전달만 담당한다. montage 위치, 구간별 재생률, 콤보 단계, 입력 buffer, 해금 분기를 ASC 멤버로 올리지 않는다. 이는 ARCH-22의 얇은 입력 adapter 계약을 유지한다.
- `UKhazanBasicAttackAbility`의 한 `InstancedPerActor` 활성 실행이 약공격 콤보 전체 수명, 현재 단계, 지역 입력 buffer, `PlayMontageAndWait` task, movement constraint handle과 모든 종료 cleanup을 소유한다. 공격 단계마다 Ability를 끝내고 다시 활성화하는 구조는 사용하지 않는다. 이는 ARCH-03/09/24의 액션 수명 계약이다.
- 원작 Composite Dilation은 파생 playback AnimSequence에 bake한다. 이때 몸 포즈뿐 아니라 `Root` 트랙도 같은 `T_Dilation → T_Original` mapping으로 재표본화한다. 파생 Sequence의 `Enable Root Motion=true`, 원본에서 직접 확인된 1–4타의 `Force Root Lock=true`, Sequence/Montage/task 재생 배율 `1.0`, task root-motion translation scale `1.0`을 사용한다.
- Main AnimInstance는 현재 `Root Motion from Montages Only`를 유지한다. Montage가 포즈와 root delta를 평가하고 CharacterMovementComponent가 그 delta를 충돌 포함 이동으로 소비한다. ASC, Character Tick, AnimNotifyState, AnimInstance worker가 매 frame 위치나 재생률을 쓰지 않는다. 이는 ARCH-01/04/06의 표현·이동 경계다.
- `Force Root Lock`은 추출된 이동을 끄는 옵션이 아니다. 추출 뒤 스켈레탈 포즈의 root 기준을 고정하는 설정이다. 실제 root delta 사용 여부는 `Enable Root Motion`과 AnimInstance Root Motion Mode가 결정한다.
- 첫 통합 checkpoint P1.5는 하나의 콤보 Montage와 `Attack01` section을 만들고, section의 자동 다음 연결을 비워 둔 채 1타의 Root Motion·Dilation·정상/취소 cleanup만 검증한다. P6에서 같은 활성 Ability에 pressed 입력을 전달하고, notify/gameplay event로 열린 창에서만 `Attack01→02→03→04`, 해금 시 `04→05` section 연결을 결정한다. Ability가 GAS의 `CurrentMontageSetNextSectionName`을 호출하고 ASC는 명령 전달·복제를 담당한다.
- 입력 창 Notify는 의미 이벤트만 전달한다. Notify나 Float Curve가 ASC 또는 Montage play rate를 계속 변경하지 않는다. interruption에서 Notify End가 누락되어도 Ability의 `EndAbility()`가 buffer/window/task/constraint를 모두 reset하는 것이 최종 cleanup 계약이다.
- 이 절은 위 2026-09-16 P1.5 기록의 `root motion disabled` 및 `AM_DAS_BasicAttack01` 단발 자산 전제를 대체한다. 실제 Source, Blueprint, AnimSequence, Montage, build, PIE는 아직 사용자 적용 전이다.

<a id="single-player-production-gas-weak-attack-20260916"></a>
## 2026-09-16 — ARCH-30/31/32 싱글 플레이 제품 경계·GAS 근거·WeakAttack 명명

### ARCH-30 — 목표는 테스트 예제가 아니라 완성도 높은 싱글 플레이 모작이다

- 제품 실행 환경은 Standalone 싱글 플레이이며 멀티플레이는 요구사항이 아니다. 원작의 공격 시간축, Root Motion, 충돌, 입력 창, 취소, 자원 소비, 피격 결과와 표현을 하나의 실제 gameplay 경로로 완성한다.
- P1 등의 수직 절편과 debug HUD, probe, console cancel은 그 경로를 단계별로 검증하는 장치다. 임시 즉시 `EndAbility()`, placeholder animation, 시험 전용 Component나 gameplay 상태를 최종 구현으로 남기지 않는다.
- 가상의 client/server 분리를 위해 prediction ledger, RPC bridge, replicated combo state, PlayerState ASC를 선행 추가하지 않는다. 영구 해금과 저장 진행도는 Progression/Save가 소유하고, 새 Character가 만들어질 때 Definition·장비·진행도에서 Ability를 다시 부여한다. 현재 Character 소유 ASC는 Avatar와 함께 끝나는 전투 실행 상태를 맡는다.

### ARCH-31 — GAS 참고 근거와 싱글 플레이 적용 범위

- [tranek/GASDocumentation](https://github.com/tranek/GASDocumentation)의 ASC, grant, Spec, Ability instance, input, AbilityTask, tag/effect 수명 설명을 GAS 구현의 기본 참고 자료로 사용한다. 문서 자체가 밝히듯 UE 5.3 기준의 비공식 자료이므로 UE 5.8.2에서 API·기본값·수명 동작이 다르면 현재 엔진 plugin source를 최종 근거로 삼는다.
- 문서의 핵심 구분을 현재 구조에 유지한다. ASC는 granted `FGameplayAbilitySpec`과 tag/effect를 보관하고, Spec은 class·입력 연결·runtime grant 상태를 가진다. 활성 Ability instance가 공격 한 번 또는 콤보 체인의 실행 상태를 가지며, Montage·입력 대기처럼 시간을 갖는 작업은 AbilityTask가 수행한다.
- `GiveAbility()`를 `HasAuthority()`에서 호출하고 `ServerOnly` Ability를 쓰는 것은 Standalone world에서도 GAS가 요구하는 authority 경계를 지키는 것이다. 이는 멀티플레이 지원 목표를 뜻하지 않는다. 새 gameplay Ability는 별도 근거가 없는 한 `ServerOnly`를 명시하고, local prediction과 direct input replication은 도입하지 않는다.
- active Spec 입력 전달이 P6에서 필요해지면 ASC는 `AbilitySpecInputPressed()`와 GAS generic replicated event가 기대하는 일반 입력 계약까지만 제공한다. 싱글 플레이에서도 기존 AbilityTask 생태계와 맞추기 위한 engine protocol로 사용하며 combo step, buffer, window, montage position은 Ability 지역 상태로 둔다.
- `InstancedPerActor` Ability는 ASC마다 한 instance를 재사용하므로 모든 activation 시작과 `EndAbility()`에서 combo index, buffered input, window, task pointer, constraint handle을 명시적으로 초기화·정리한다. 이는 tranek 문서의 instancing 주의사항과 현재 ARCH-09 cleanup 계약을 함께 만족한다.
- authored skill Root Motion은 AnimSequence/Montage → AnimInstance → CMC 경로를 사용한다. GAS의 RootMotionSource AbilityTask 예시는 별도 이동 생성 기법이며, 원작 애니메이션 root track을 대체하는 근거로 사용하지 않는다.

### ARCH-32 — `WeakAttack`이 도메인 정본 명칭이다

- 원작 Skill Blueprint와 Composite의 `WeakAtk01`–`WeakAtk05`를 실행하는 현재 `BasicAttack`은 약공격과 같은 행동이었다. 범용 기본 공격이라는 별도 gameplay 개념은 확인되지 않았으므로 `BasicAttack` 명칭을 폐기하고 `WeakAttack`을 사용한다.
- native 구현은 `UKhazanWeakAttackAbility`, content subclass는 `GA_WeakAttack_Khazan`, 콤보 Montage는 `AM_DAS_WeakAttackCombo`, task instance name은 `WeakAttackComboMontage`를 사용한다. 과거 문서의 `UKhazanBasicAttackAbility`, `GA_BasicAttack_Khazan`, `AM_DAS_BasicAttack01`, `BasicAttackComboMontage`는 새 구현에 복사하지 않는다.
- 물리 입력 라우팅 태그 `Input.Action.Attack`은 행동 class 이름이 아니므로 유지한다. Weak/Strong 입력을 별도 태그로 분리해야 한다는 원작 근거와 실제 소비자가 생기면 입력 계약 변경으로 따로 검토한다.
- 2026-09-16 실제 Source class/file을 `UKhazanWeakAttackAbility`와 `KhazanWeakAttackAbility.h/.cpp`로 변경하고 `NetExecutionPolicy=ServerOnly`를 명시했다. 기존 Definition asset의 `/Script/Khazan.KhazanBasicAttackAbility` 참조는 class redirect로 새 class에 연결한다. Montage/Blueprint/full combo 구현과 build·PIE 검증은 여전히 P1.5 이후 작업이다.

<a id="p1-5-production-lifetime-correction-20260916"></a>
## 2026-09-16 — ARCH-06/09/31 P1.5 제품 수명 계약 보정

- 앞 P1.5 제안의 `MaxAllowedGait=Run` movement constraint는 원작 공격 정책이 아니라 handle cleanup을 보기 위한 시험값이었다. 실제 소비되는 공격 전용 이동·회전 정책이 확인되지 않은 상태에서 제품 코드에 이 제약을 만들지 않는다. P1.5의 authored 이동은 Dilation이 bake된 Montage Root Motion이 만들고 CMC가 충돌을 포함해 소비한다.
- 이후 원작 근거로 공격 중 회전, 입력 이동, 타깃 보정 정책이 확인되면 `UKhazanWeakAttackAbility`가 해당 실행에 필요한 constraint handle만 발급·소유하고 `EndAbility()`에서 반환한다. P1.5에서 미리 빈 handle, weak component pointer, 임시 gait cap을 넣지 않는다.
- P1.5의 실행 자원은 `UAbilityTask_PlayMontageAndWait` 한 건이다. 정상 완료는 `OnCompleted`, Montage 교체는 `OnInterrupted`, task 시작 실패·외부 task 취소는 `OnCancelled`에서 공통 종료 함수로 들어간다. `OnBlendOut`은 공격 수명 종료 신호로 사용하지 않는다.
- UE 5.8의 `bAllowInterruptAfterBlendOut=false`는 정상 Blend Out 시작 뒤 Montage가 끊기면 `OnInterrupted`도 `OnCompleted`도 오지 않을 수 있다. 실행이 active로 고착되지 않도록 P1.5는 `bAllowInterruptAfterBlendOut=true`를 명시한다. `bStopWhenAbilityEnds=true`, task rate `1.0`, root-motion translation scale `1.0`, 시작 section `Attack01`도 명시한다.
- 원작 `SB_Kazan_DualAxeSword_Com_WeakAtk`의 `Step1`은 `AnimBlendAlpha=0.1`, `AnimPlayRate=1.0`, `AnimLoopCount=1`, `bApplyAttackSpeed=true`다. `AC_...WeakAtk01`의 `StartBlendTime=0.24`와 `EndBlendTime=0.3`은 `xxAnimNotifyState_RigRotToTarget`의 왼손 보정 필드이며 Montage Blend In/Out 근거가 아니다. `AnimBlendAlpha`가 원작 런타임에서 초 단위 Montage blend와 동일하다는 소비 코드까지는 확보하지 못했으므로 P1.5에서 양자를 확정값으로 등치하지 않는다.
- P1.5의 `AM_DAS_WeakAttackCombo/Attack01`은 1타 통합 계약이다. P6에서 2–5타를 붙이기 전 `AnimBlendAlpha`가 단계 전환 cross-fade를 뜻하는지 확인한다. 한 Montage의 section 경계로 같은 전환 품질을 낼 수 없다는 증거가 나오면 한 Ability instance가 콤보 전체 수명을 소유한다는 ARCH-09 계약은 유지하면서 presentation asset/task 분할만 바꿀 수 있다.
- 이 보정은 P1.5의 제품 구현 계약이며 실제 Source, playback Sequence, Montage, Ability Blueprint, cold build, PIE 적용 완료를 뜻하지 않는다.

## 2026-09-17 — ARCH-09/31 P1.5 Montage 추상화 판단

- 현재 `UKhazanWeakAttackAbility`는 `UAbilityTask_PlayMontageAndWait`를 생성하고 완료·중단·취소 delegate를 Ability 종료 경로에 연결한다. 사용자는 좌클릭 PIE에서 `Attack01` Montage 재생을 확인했고 `Saved/Logs/Khazan.log`에도 시작 로그가 반복 기록됐다. 이 증거는 시작 경로 확인이며 강제 cancel, Montage interrupt, Blend Out 직후 interrupt, 다음 PIE cleanup까지 모두 검증됐다는 뜻은 아니다.
- 엔진 AbilityTask가 ASC를 통한 Montage 재생, Ability cancel 연결, Montage delegate 연결·해제, Ability 종료 시 Montage 정리와 root-motion translation scale 복원을 이미 소유한다. 따라서 같은 일을 전달만 하는 `IMontagePlayer`나 정적 `UKhazanMontageUtility`는 v2.2의 새 구조 생성 기준을 충족하지 않는다.
- 현재 한 소비자의 가독성 정리는 `UKhazanWeakAttackAbility`의 private 함수로 Montage task 생성·delegate 연결을 묶고, `OnInterrupted`와 `OnCancelled`를 같은 종료 callback으로 합치는 범위가 적절하다. Ability는 commit 여부와 정상/취소 종료 정책을 계속 소유한다.
- `MontageTask` 멤버는 실행 중 task를 Ability 코드가 다시 조회·취소할 실제 소비가 없다면 필수 생명주기 소유자가 아니다. 활성 task의 보존과 Ability 종료 cleanup은 `UGameplayAbility`의 active task 경로가 수행한다. 다만 P6의 section 전환 구현에서 실제 소비가 생기는지 확인한 뒤 제거 여부를 확정한다.
- 두 개 이상의 Ability에서 Montage 재생과 GameplayEvent 대기 정책이 실제로 반복되는 P3/P6 시점에는 game-specific `UAbilityTask` 추출을 다시 검토한다. 그 task는 엔진 delegate와 event 수집을 소유하고, 콤보 상태·commit·Ability 종료 판단은 실행 Ability에 남긴다.
- 이번 검토에서는 게임 Source, Blueprint, Montage를 수정하지 않았다.

<a id="attack-input-language-combo-hold-20260917"></a>
## 2026-09-17 — ARCH-33/34/35 약·강 입력 조합과 유지 입력 계약

### 확인된 현재 상태와 원작 근거

- 실제 `AKhazanPlayerController`는 `/Game/Input/IA_Attack`의 `Started`만 받아 `Input.Action.Attack`으로 ASC를 호출한다. `/Game/Input/IMC_Default`에는 Left Mouse Button만 연결돼 있고 Right Mouse Button 입력은 없다. `UKhazanAbilitySystemComponent`도 inactive Spec에 `TryActivateAbility()`만 호출하므로 active Ability에 press/release를 전달하지 못한다.
- 실제 `/Game/_Art/Kazan/Animation/InGame/DAS/WeakAtk/AM_DAS_WeakAtkCombo`에는 `Attack01` section과 `DAS_Khazan_WeakAtk01` segment만 있다. 따라서 현재 자산만으로는 두 번째 입력을 받아도 `Attack02`로 진행할 presentation 경로가 없다. 이전 절의 제안명 `AM_DAS_WeakAttackCombo`보다 실제 저장된 원본 유지 이름 `AM_DAS_WeakAtkCombo`를 현행 이름으로 사용한다.
- 원작 `.../Common/WeakAtk/SI_Kazan_DualAxeSword_Com_WeakAtk`은 `AttackType=FastAttack`, `SkillInputType=SkillM01`이고, `SB_...WeakAtk`은 `SkillM01`과 `Pressed`를 사용한다.
- 원작 `.../Common/StrongAtk/SI_Kazan_DualAxeSword_Com_StrongAtk`은 `AttackType=StrongAttack`, `SkillInputType=SkillM02`다. `SB_...StrongAtk`에는 `SkillM01`, `SkillM02`, `SecondInputType=SkillM02`, `Pressed`, `xxSetChargingStepFunc`, `DoChangeCharageStep`가 함께 존재한다. 따라서 약공격과 강공격의 조합 분기는 실제 요구다.
- 원작 `AC_...StrongAtk01_Start`와 `AC_...StrongAtk01_Charge`의 `xxAnimNotifyState_SkillInputProg`은 `Released`를 검사한다. 저장된 `PlaybackEvents.json` 기준 Start의 release 창은 원본 `0.1593871–0.2 s`, playback `0.1992338551–0.24999997 s`다. Charge에는 원본 `0–1.3 s`, `0–0.717957 s`, `0.717919–1.3 s`의 release/charge-step 창이 있고 playback으로 각각 약 `0–1.1780140925 s`, `0.0001–0.6000966776 s`, `0.6000589403–1.1781134007 s`에 대응한다. 이는 단일 임의 hold threshold가 아니라 애니메이션 시간축의 release와 charge step 계약이라는 직접 근거다.
- 원작 `AC_...WeakAtk01`의 두 `xxSkillInputProg` 구간은 원본 `0.31871584–0.6105073 s`, `0.6138552–1.0215641 s`이고 playback으로 약 `0.2929789424–0.5131536622 s`, `0.5165015501–0.9242099718 s`다. 두 NotifyState의 세부 enable/disable 의미는 원작 runtime 소비 코드까지 확인되지 않았으므로 둘을 임의로 하나의 확정 콤보 창이라고 합치지 않는다.
- 같은 `AC_...WeakAtk01`에는 `xxAnimNotifyState_ReserveInput`이 별도로 세 구간 존재한다. 원본 `0.2282529–0.5708918 s`, `0.44233206–0.7362118 s`, `1.1393118–1.2893118 s`가 playback 약 `0.2205535080–0.4756474282 s`, `0.3825092135–0.6388580379 s`, `1.0419576641–1.1919575 s`로 변환된다. `SB_...WeakAtk`의 Step1 `Index8`은 `Pressed` 입력 event를 `Step2` 변경 함수에 연결한다. 반면 late `Index7` input-check는 `NotifyEnable` 조건 뒤 `Step1` same-step 변경으로 연결된다. 따라서 앞 두 reservation 후보와 늦은 reservation 후보를 모두 01→02 buffer로 취급하지 않는다. 입력 예약과 진행 판정이 별개라는 강한 근거지만 proprietary runtime 구현은 없으므로 정확한 begin/end 부작용은 추론으로 구분한다.

### ARCH-33 — 공격 입력은 의미와 phase를 함께 전달한다

- `Input.Action.Attack`을 `Input.Action.WeakAttack`과 `Input.Action.StrongAttack`으로 분리한다. 이는 ARCH-32에서 분리 근거가 생길 때 재검토하기로 한 조건이 충족된 변경이다. 원작 `SkillM01/M02`가 각각 실제 소비자이며 좌·우 입력 조합을 구별해야 한다.
- Enhanced Input의 `Started`는 press, `Completed`는 정상 release, `Canceled`는 입력 평가 취소로 번역한다. 공격을 매 frame `Triggered`로 보내지 않는다. `Canceled`는 Spec의 pressed 상태를 해제하지만 성공적인 차지 release와 같은 결과로 취급하지 않는다.
- PlayerController는 물리 키를 의미 입력과 phase로 번역하는 adapter다. combo node, buffer, hold duration, montage section, unlock 판단을 소유하지 않는다. 미래 AI는 마우스 phase를 흉내 내지 않고 같은 Ability 실행/분기 계약을 의미 action으로 요청한다.
- `IA_WeakAttack`은 Left Mouse Button, `IA_StrongAttack`은 Right Mouse Button을 사용한다. Strong의 press를 즉시 Ability에 전달하고 release를 나중에 전달해야 하므로 Enhanced Input의 `Hold` trigger가 Ability 활성화를 지연시키는 구조는 사용하지 않는다.

### ARCH-34 — ASC는 Spec 입력 protocol만 중계한다

- `UKhazanAbilitySystemComponent`는 exact Dynamic Spec Source Tag로 Spec을 찾고 press/release 상태를 갱신한다. inactive Spec의 press는 활성화를 시도하고, active Spec의 press/release는 `AbilitySpecInputPressed/Released()`와 `InvokeReplicatedEvent(InputPressed/InputReleased, Spec.Handle, current activation prediction key)`를 모두 호출한다.
- UE 5.8 `AbilityLocalInputPressed/Released()`가 위 두 호출을 따로 수행하며, `AbilitySpecInputPressed/Released()`만으로는 `UAbilityTask_WaitInputPress/Release`가 구독하는 generic replicated event가 발생하지 않는다. tag 기반 adapter도 이 engine protocol을 그대로 보존한다.
- 현재 공격 Ability는 `InstancedPerActor`이므로 current instance activation info를 사용한다. 이 입력 protocol은 싱글 플레이에서도 기존 GAS AbilityTask와 맞추기 위한 수명 계약이며 ASC에 combo 상태를 넣는 근거가 아니다.
- generic input event에는 어떤 Input Tag였는지 payload가 없다. 같은 Spec의 재입력처럼 의미가 자명한 단계에는 `WaitInputPress/Release`를 사용하고, active Weak Ability가 Strong press를 구별하는 실제 혼합 분기부터 별도 Gameplay Event tag와 payload를 추가한다. 소비자가 생기기 전에 전역 입력 event 사전을 만들지 않는다.

### ARCH-35 — 콤보와 충전 상태는 활성 Ability의 지역 실행 문맥이다

- `UKhazanWeakAttackAbility`의 한 활성 실행이 Weak chain의 current section/node, 입력 창, buffered semantic input 한 건, montage task와 cleanup을 소유한다. Weak 1타마다 Ability를 끝내고 다시 활성화하지 않는다.
- Strong 입력의 첫 실제 소비 시 `UKhazanStrongAttackAbility`를 별도 실행 Ability로 만든다. Strong은 Start/Charge/Release와 charge step을 소유한다. Weak와 Strong의 상호 입력은 하나의 거대 Ability나 ComboManager를 만들 근거가 아니며, 확인된 branch window에서 의미 입력 event를 받아 같은 Ability의 section을 바꾸거나 다른 Ability 활성화를 요청한다.
- 혼합 분기 단계에서는 현재 공격의 실행 lane/tag가 다른 공격 Ability의 독립 즉시 활성화를 막는다. 예를 들어 Weak 실행 중 Strong press는 Strong Spec의 일반 활성화 시도가 차단되고, 현재 Weak Ability가 typed Strong event를 합법 window에서만 소비해 전환을 요청한다. 대상 Ability 활성화 성공을 확인하기 전에 현재 실행을 먼저 끝내지 않는다. 같은 press를 generic input task와 typed event handler가 동시에 소비하지 않도록 own-input 재입력은 generic event, 다른 공격 키 분기는 typed event로 역할을 나눈다.
- 동일 계열 연속 입력은 `WaitInputPress(false)`로 다음 press를 기다린다. `true`로 만들면 활성화에 사용된 첫 press를 즉시 다시 소비해 2타가 예약될 수 있으므로 사용하지 않는다. task는 한 번 broadcast하고 끝나므로 다음 입력이 필요하면 Ability가 새 task를 arm한다.
- Strong은 활성화 직후 `WaitInputRelease`를 시작할 수 있다. 여기서 반환되는 `TimeHeld`는 task 생성부터 release까지의 관측값이며, 원작 charge step/window를 대체하는 단일 판정값으로 확정하지 않는다. exact step 판정은 Dilation 변환된 원작 Notify 구간과 Strong state 연결을 표적 조사한 뒤 작성한다.
- AnimNotify/NotifyState는 window open/close 또는 의미 Gameplay Event만 보낸다. combo node와 buffered input의 권위는 Ability에 있고, interruption으로 Notify End가 누락돼도 `EndAbility()`가 window, buffer, held/release 상태와 task pointer를 초기화한다.
- Weak 첫 구현도 `ReserveInput`과 `SkillInputProg`를 하나의 `bComboWindowOpen`으로 합치지 않는다. 활성 Ability에는 서로 겹칠 수 있는 `bInputReservationOpen`, `bComboAdvanceOpen` 같은 두 지역 사실과 buffered input 한 건을 둔다. press 시 advance가 열려 있으면 즉시 합법 edge를 소비하고, reservation만 열려 있으면 한 건을 보관하며, advance begin에서 보관 입력을 다시 평가한다. 두 창의 정확한 이벤트 의미가 추가 근거로 달라지면 이 지역 해석만 교체한다.
- 첫 구현은 현재 node마다 buffered input 한 건으로 시작한다. 전역 FIFO `InputBufferComponent`, 범용 graph runtime, custom graph editor는 만들지 않는다. 원작 branch 표가 완성되고 두 개 이상의 무기/Ability가 같은 read-only schema를 실제 소비할 때 node/edge data화를 확장한다.

<a id="enhanced-input-combo-queue-review-20260917"></a>
## 2026-09-17 — ARCH-36/37 Enhanced Input Combo 검토와 연타 큐 계약

### UE 5.8 엔진 확인

- 로컬 UE 5.8의 `InputTriggers.h`에서 `FInputComboStepData`, `FInputCancelAction`, `UInputTriggerCombo`는 모두 `UE_DEPRECATED(5.8, ...)`로 선언돼 있다. Editor data validation도 Combo Trigger가 deprecated이며 미래 버전에서 제거될 것이라는 warning을 추가한다. 따라서 새 전투 기반을 이 타입에 의존시키지 않는다.
- 현재 구현은 순서대로 지정된 InputAction의 설정 event를 관찰하고, 다음 step의 `TimeToPressKey`를 넘기거나 다른 combo action이 순서 밖에서 발생하거나 cancel action이 발생하면 index를 0으로 돌린다. 완성 시 한 frame `Triggered`를 반환하고 즉시 reset한다. 이 기능은 패턴 인식기이며, 공격 실행별 montage section·원작 Notify window·해금·비용·현재 Ability 수명·buffer 소비를 알지 못한다.
- 같은 약공격 세 번을 Combo Trigger로 인식해도 입력 세 번이 현재 공격 section의 합법 창에서 발생했다는 보장이 없다. 패턴이 먼저 완성된 순간 공격 Ability가 block 상태라면 결과는 실행 queue로 남지 않는다. 반대로 긴 `TimeToPressKey`는 원작 animation window 밖의 입력까지 받아들일 수 있다.
- `UInputTriggerChordAction`은 deprecated가 아니지만 한 action이 현재 `Triggered`인 동안 다른 action을 허용하는 비대칭 modifier 계약이다. 기본 설정은 같은 frame에 chord 결과가 발생하면 선행 action delegate를 억제할 수 있으나, 선행 약공이 이전 frame에 이미 시작된 뒤 강공이 들어오는 대칭 동시 입력을 되돌리지는 못한다. 따라서 stance+attack 같은 명시적 modifier에는 사용할 수 있지만 약공+강공 조합 전체의 공통 parser로 사용하지 않는다.
- `FInputActionInstance::GetElapsedTime()`은 action이 Started/Ongoing/Triggered 상태로 평가된 시간을, `GetTriggeredTime()`은 Triggered 상태 시간을 제공한다. 이 값이나 Controller의 별도 WorldTime 누적을 Strong charge의 권위로 삼지 않는다. `WaitInputRelease`는 AbilityTask 생성 시점부터 release까지를 측정하므로 Strong activation 직후 시작해 관측값으로 사용할 수 있고, 실제 charge step과 release 허용은 animation에 고정된 원작 Notify/event window가 결정한다.

### ARCH-36 — Enhanced Input은 전투 문법의 lexer다

- `IA_WeakAttack`과 `IA_StrongAttack`은 별도 Digital InputAction으로 유지하며 공격용 `Hold`, `Combo` trigger를 붙이지 않는다. Controller는 `Started`, `Completed`, `Canceled` edge를 각각 semantic press, 정상 release, 취소 cleanup으로 번역한다. `Ongoing`/매 frame `Triggered`를 공격 명령으로 제출하지 않는다.
- 연속 약공, 약→강, 강→약은 물리 키 패턴만으로 완성되는 명령이 아니다. 현재 attack node, 열려 있는 reservation/progression window, 해금, 비용과 실행 차단을 함께 보아야 하므로 활성 GameplayAbility가 판정한다.
- 실제 원작에서 두 버튼을 동시에 누르는 독립 branch가 확인되기 전에는 `IA_WeakStrongChord`를 만들지 않는다. 확인될 경우에도 Chorded Action의 선행 키 순서 의존성이 원작 허용 오차와 맞는지 먼저 검증한다. 맞지 않으면 press edge와 현재 down 상태로 project-local chord를 한 번만 파생하며, 허용 시간은 원작 근거값 또는 명시한 임시 튜닝값으로 둔다.
- 방향 커맨드처럼 Ability 실행과 무관하게 최근 입력 이력을 여러 소비자가 조회해야 하는 실제 기능이 생기면 deprecated Combo Trigger 대신 작은 project command recognizer를 검토한다. 현재 확인된 Weak/Strong 연속·유지 입력만으로는 그 구조를 만들지 않는다.

### ARCH-37 — 콤보 큐는 활성 공격 실행의 node-local 단일 예약이다

- `CombatInputBufferComponent`가 montage/Notify window와 Combo Tree를 함께 추적하는 구조는 채택하지 않는다. 그렇게 하면 Ability와 Component가 current node, 유효 window, branch 선택, 취소 cleanup을 동시에 소유하게 된다.
- 런타임 상태는 활성 Weak 또는 Strong Ability가 소유한다. 현재 node, reservation window, advance window, 한 건의 buffered semantic input, 현재 node의 다음 edge가 이미 확정됐는지 나타내는 transition-committed 사실, 현재 montage section을 Ability 종료와 함께 reset한다. Notify/NotifyState는 창의 begin/end 신호만 보내며 권위 상태를 저장하지 않는다.
- 읽기 전용 Combo Definition은 충분한 실제 branch가 생기는 P6-D에서 도입할 수 있다. node는 montage section/action 참조를, edge는 요구 input tag와 phase, 필요한 window 종류, unlock/state 조건과 다음 node를 표현한다. runtime index, pressed 상태, buffer, stamina 값은 DataAsset에 저장하지 않는다.
- 첫 P6 구현의 큐 용량은 현재 node당 한 건이다. reservation이 닫혀 있으면 press를 버리고, 열려 있고 slot이 비었으면 저장한다. slot이 이미 찼으면 같은 키 연타와 다른 공격 키를 모두 추가 적재하지 않고 먼저 합법적으로 예약된 입력을 유지한다. 이 `first accepted input wins`는 연타 한 번으로 여러 미래 타가 자동 실행되는 것을 막기 위한 명시적 초기 정책이며, 원작 overwrite 정책은 아직 미확인이다.
- press를 slot에 넣기 전 현재 node에 해당 input의 정적 edge가 있고 현재 unlock/state 조건이 맞는지 확인한다. 존재하지 않거나 해금되지 않은 입력은 slot을 차지하지 않는다. advance window에서 직접 들어온 후보 또는 reservation slot의 입력을 고른 뒤 Ability가 cost/target과 현재 section을 다시 검증한다. 성공한 경우에만 buffer를 소비하고 transition을 committed로 잠근 뒤 `Montage_SetNextSection` 또는 확인된 전환을 수행한다. 동적 검증에 실패하면 후보를 버리고 현재 합법 공격은 먼저 종료하지 않는다.
- transition이 committed된 뒤에는 같은 section의 남은 window에서 들어오는 모든 추가 press를 무시하고 input wait를 재arm하지 않는다. section이 실제로 다음 node에 들어간 뒤 current node를 바꾸고 committed를 해제하며 새 node용 slot을 비운 다음 input wait를 새로 arm한다. 같은 node에서 연타한 여러 press를 Attack02·03·04에 걸쳐 보존하지 않는다. release는 held 상태 또는 charge branch를 갱신하는 edge이며 일반 press FIFO 원소로 추가하지 않는다. `Canceled`, montage interrupt, Ability cancel/end, Pawn 교체에서는 모든 지역 입력 상태를 지운다.
- Attack→Dodge처럼 서로 다른 Ability 사이의 recovery queue, 또는 여러 Ability가 공유해야 하는 방향 command history가 실제로 생기면 별도 입력 buffer/history owner를 다시 심사한다. 그 구조는 semantic input event와 만료/소비만 소유하고 montage section, combo graph, stamina, Ability 활성 여부를 판정하지 않는다.

### 채택된 실행 흐름

```text
Physical key
  -> Enhanced Input: Weak/Strong + Started/Completed/Canceled
  -> PlayerController: 장치 입력을 semantic tag/phase로 번역
  -> Khazan ASC: Spec.InputPressed와 GAS generic input protocol 중계
       -> inactive own Spec: TryActivateAbility
       -> active own Spec: WaitInputPress/Release
       -> active attack의 other-key branch: typed Gameplay Event
  -> Active Attack Ability
       <- montage Notify/event: reservation/advance/charge window
       <- read-only Combo Definition: 현재 node에서 가능한 edge
       -> GAS tag/cost/unlock 재검증
       -> Montage section 전환 또는 대상 Ability handoff
```

이 흐름에서 ASC는 전투 입력 상태 머신이 아니고, Controller는 hold/combo 판정자가 아니며, AnimNotifyState는 buffer owner가 아니다. 활성 Ability 하나가 현재 실행의 최종 소비자이므로 interrupt와 `EndAbility()`에서 입력 상태와 animation 수명을 함께 닫을 수 있다.

## 2026-09-17 — ARCH-38 P6-A 창 중첩과 Montage→Ability 이벤트 경계

- P6-A의 실제 WeakAtk01 `ReserveInput` 후보 둘은 `0.3825092135–0.4756474282 s`에서 서로 겹친다. 따라서 Notify 하나가 끝날 때 다른 Notify가 아직 열려 있을 수 있으며 단일 bool을 Begin=true/End=false로 쓰면 창이 조기에 닫힌다. 활성 WeakAttack Ability는 reservation과 advance 각각의 활성 깊이 `int32`를 지역 상태로 소유하고 `depth > 0`을 열린 상태로 해석한다. 모든 값은 activation 시작과 `EndAbility()`에서 0으로 reset한다.
- Montage의 window NotifyState는 begin/end `Gameplay Event`만 Avatar ASC에 보낸다. event tag는 실행 상태나 Owned Tag가 아니며 NotifyState도 buffer, current node, transition 결정을 저장하지 않는다. 활성 `UKhazanWeakAttackAbility`가 `WaitGameplayEvent`로 이벤트를 받고 depth·buffer·transition을 변경한다.
- P6-A의 입력 대기는 `WaitInputPress(false)` 한 건이다. advance가 열렸으면 즉시 `Attack01→Attack02`를 확정하고, reservation만 열렸으면 최초 입력 한 건만 보관하며, 어느 창도 아니면 그 press를 버리고 새 task를 arm한다. transition 확정 뒤에는 P6-A 실행에서 입력 대기를 다시 arm하지 않는다.
- `Attack01`과 `Attack02`의 authored Next Section은 모두 `None`이다. Ability가 현재 Montage와 현재 section을 재검증한 뒤 `CurrentMontageSetNextSectionName(Attack01, Attack02)`가 실제로 설정된 경우에만 transition-committed를 true로 만든다. Montage 완료·중단·cancel과 Pawn 수명 종료는 Ability task cleanup과 `EndAbility()` reset으로 닫는다.
- 이 한 edge에는 Combo DataAsset, 전역 buffer Component, 범용 graph runtime을 만들지 않는다. 같은 schema를 요구하는 실제 분기가 생기는 P6-D 전까지 section 이름과 한 edge는 WeakAttack Ability의 좁은 계약으로 유지한다.

## 2026-09-17 — ARCH-39 P6-A Montage window 전달 경로 단순화

- ARCH-38의 window 소유권, reservation/advance 분리, depth counter, Ability-local buffer 계약은 유지한다. 다만 P6-A에서 window begin/end를 전달하기 위해 제안했던 전역 Gameplay Event tag 네 개와 custom `KhazanAnimNotifyState_GameplayEventWindow`, `WaitGameplayEvent` task 네 개는 현재 소비자 수에 비해 계층이 많으므로 채택하지 않는다.
- UE 5.8에는 Montage 전용 `UAnimNotify_PlayMontageNotifyWindow`와 `UAnimInstance::OnPlayMontageNotifyBegin/End`가 이미 있다. P6-A Montage에는 내장 `Montage Notify Window`를 사용하고 `NotifyName` 두 개(`InputReservation`, `ComboAdvance`)만 작성한다. Begin/End 구분은 서로 다른 engine delegate가 제공하므로 네 개의 전역 tag가 필요하지 않다.
- 활성 `UKhazanWeakAttackAbility`가 자신이 시작한 `WeakAttackMontage`의 AnimInstance delegate에 activation 동안만 bind한다. callback은 payload의 `SequenceAsset`이 해당 Montage인지 확인한 뒤 reservation/advance depth를 변경한다. `EndAbility()`는 bind했던 AnimInstance에서 두 delegate를 제거하고 depth, buffer, transition state를 reset한다. ASC와 AnimInstance에는 combo mutable state를 추가하지 않는다.
- Gameplay Event 경로 자체를 폐기하는 결정은 아니다. 다른 입력 key의 의미를 활성 Ability에 payload와 함께 전달하거나, 둘 이상의 Ability/시스템이 같은 animation event를 실제로 소비할 때 사용한다. 같은 montage를 시작한 한 Ability만 자기 window를 소비하는 P6-A에는 direct montage notify delegate가 더 작은 계약이다.
- 동일한 montage+notify bind/filter/unbind 코드가 둘 이상의 실제 Ability에 반복되면 그때 game-specific AbilityTask로 추출한다. 첫 소비자만 있는 현재 단계에서는 custom AbilityTask도 만들지 않는다.
- 2026-09-17 Editor/Python read-only 확인에서 `AM_DAS_WeakAtkCombo`는 `Attack01` section 한 개, `DAS_Khazan_WeakAtk01` segment 한 개, notify 0개다. UE 5.8 `UAnimMontage::AddAnimCompositeSection()`은 새 section 추가 시 이전 section의 `NextSectionName`이 `None`이면 새 section으로 자동 연결한다. 따라서 `Attack02` section을 만든 직후 authored `Attack01 -> Attack02` 연결을 다시 `None`으로 지워야 하며, runtime Ability가 합법 입력을 소비한 경우에만 연결한다.

## 2026-09-17 — ARCH-40 카잔 전투의 지속 가능한 최소 구조

- 이후 설계 목표는 현재 checkpoint의 코드량만 줄이는 것이 아니라, 확인된 카잔 전투를 완성할 수 있는 구조 중 가장 작은 계약을 고르는 것이다. 이 프로젝트에서 이미 확정된 범위는 Standalone 싱글 플레이, 공격·스킬의 authored Root Motion, Weak 1–4타와 해금 5타, Strong press/hold/release, 확인된 Weak↔Strong 분기, montage 시간축의 입력 창이다. 가상의 네트워크·범용 전투 프레임워크는 넣지 않지만 이 확정 범위를 P6-A 한 edge 때문에 잃지도 않는다.
- 변하지 않을 책임 경계는 `Enhanced Input/Controller = 물리 입력을 의미와 phase로 번역`, `ASC = granted Spec 활성화와 engine press/release/event 전달`, `활성 Attack Ability = 현재 section·입력 한 건·창·전환·취소 수명`, `Montage = Root Motion·포즈·시간 창`, `Progression = 해금 사실`이다. 마이그레이션 단계가 늘어도 이 상태를 다른 Manager나 Component로 옮기지 않는다.
- P6-A의 한 칸 buffer는 Weak 전용 bool이 아니라 유효하지 않은 값이 empty를 뜻하는 `FGameplayTag BufferedInputTag`로 둔다. own-input `WaitInputPress`는 `Input.Action.WeakAttack`을 저장하고, 이후 확인된 other-key event는 같은 칸에 Strong tag를 저장할 수 있다. FIFO, timestamp와 전역 queue는 추가하지 않는다.
- 전환 함수도 `TryCommitAttack02()`처럼 checkpoint 결과를 이름에 고정하지 않는다. 현재 montage section과 buffered semantic input을 받아 합법한 다음 section을 찾고 연결하는 `TryCommitBufferedTransition()` 같은 Ability 내부 계약으로 둔다. P6-A에는 `Attack01 + Weak → Attack02` 규칙 하나만 존재하고, P6-B/D는 같은 함수의 확인된 규칙만 늘린다. 범용 graph runtime이나 별도 Combo Manager를 만들지 않는다.
- `InputReservationDepth`, `ComboAdvanceDepth`, 한 칸 tag, transition-committed 사실은 실제 겹치는 원작 window와 한 section당 한 입력 정책 때문에 필요한 최소 지역 상태다. AnimInstance 직접 Montage Notify delegate는 엔진 기능을 그대로 쓰는 transport이며 전투 상태를 소유하지 않는다.
- 공통 AbilityTask 추출은 소비자 수만으로 결정하지 않는다. 여러 실제 Ability에서 동일한 montage-notify 필터, bind/unbind, interruption cleanup 정책이 반복되고 그 중복이 오류나 정책 불일치를 만들 때만 추출한다. 추출하더라도 위 책임과 데이터 계약은 바꾸지 않는 지역 구현 정리여야 한다.

## 2026-09-17 — ARCH-41 전체 회복 시퀀스의 조기 콤보 전환과 cross-fade

- `DAS_Khazan_WeakAtk01`과 `DAS_Khazan_WeakAtk02`는 각각 공격 뒤 정자세 회복까지 포함한 전체 시퀀스다. 따라서 Attack01 section 끝에서 Attack02를 authored next로 재생하면 1타 회복을 모두 기다린 뒤 2타가 시작되어 콤보가 끊겨 보인다. 반대로 Attack01 segment 자체를 짧게 잘라 두면 무입력 1타에서도 회복부가 사라진다. 두 경우 모두 채택하지 않는다.
- 로컬 UE 5.8.2의 `FAnimMontageInstance::SetNextSectionName`/section advance와 `FAnimTrack::GetAnimationPose`를 확인했다. section link 또는 jump는 다음 section 위치로 재생 위치를 옮길 뿐, 인접 segment 사이에 별도 pose cross-fade를 만들지 않는다. 그러므로 ARCH-38의 `CurrentMontageSetNextSectionName(Attack01, Attack02)` 전환안은 이 절에서 대체한다.
- 한 `UKhazanWeakAttackAbility` 실행이 콤보 수명을 계속 소유하되, 합법 입력을 소비하는 순간 현재 `PlayMontageAndWait` task만 `EndTask()`로 닫고 같은 `AM_DAS_WeakAtkCombo`를 목표 section(`Attack02`)에서 새 task로 다시 재생한다. UE `UAnimInstance::Montage_PlayInternal`은 같은 group의 기존 montage를 새 montage의 Blend In 설정으로 정지시키고 새 instance를 시작하므로 Attack01의 현재 pose가 blend-out되는 동안 Attack02 시작 pose가 blend-in된다. 입력이 없으면 기존 Attack01 task가 전체 회복부까지 정상 완료한다.
- 현재 Montage의 editor 확인값은 Blend In/Out `0.1 s`, Blend Option `Hermite Cubic`, Rate Scale `1.0`이다. 원작 `SB_Kazan_DualAxeSword_Com_WeakAtk`의 Step1/Step2에는 `AnimBlendAlpha=0.1`, `AnimPlayRate=1.0`, `AnimLoopCount=1`이 직접 기록돼 있다. `AnimBlendAlpha`를 UE Montage 초 단위 Blend In으로 대응시키는 것은 프로젝트 구현 매핑이며 proprietary 소비 코드로 동일 의미가 증명된 것은 아니다. 현재 `0.1 s`를 유지하고 원작 영상·PIE pose/root-motion 품질로 검증한다.
- 새 재생은 root-motion montage instance도 Attack02 instance로 교체한다. `AnimRootMotionTranslationScale=1.0`을 유지하고 Actor 위치를 코드로 보간하거나 mesh 임시 scale을 이동 배율에 사용하지 않는다. 전환 프레임의 capsule 변위·회전·속도 불연속은 PIE에서 별도 품질 gate로 확인한다.
- 같은 Montage asset의 이전 instance가 `0.1 s` 동안 blend-out될 수 있으므로 payload의 `SequenceAsset` 비교만으로는 이전 instance의 늦은 Notify를 배제할 수 없다. Ability는 새 재생 직후 `FAnimMontageInstance::GetInstanceID()`를 저장하고 `FBranchingPointNotifyPayload::MontageInstanceID`까지 일치하는 Begin/End만 소비한다. 이는 재생 방식 때문에 생긴 필수 식별값이며 combo 상태를 AnimInstance로 옮기는 것이 아니다.
- 현재 ASC는 active Spec에 `AbilitySpecInputPressed()`를 호출하며 엔진은 이를 활성 Ability instance의 `InputPressed()` virtual로 전달한다. P6-A의 동일 Weak key 연타는 `UKhazanWeakAttackAbility::InputPressed()`에서 직접 한 칸 buffer로 제출한다. 이를 위해 매 입력마다 `WaitInputPress` task를 재생성하지 않는다. ASC의 generic replicated event 전달은 Strong release 등 다른 AbilityTask 소비자를 위해 그대로 유지한다.
- 새 전환은 즉시 `CurrentSectionName`과 active montage instance를 Attack02로 교체한다. 이전 section의 중복 예약을 막기 위한 별도 `bTransitionCommitted`는 더 이상 필요하지 않다. P6-A의 최소 mutable 상태는 current section, active montage instance ID, reservation/advance depth, `FGameplayTag` 한 칸 buffer, 현재 montage task와 bind한 AnimInstance다.
- custom notify/event tag/AbilityTask, 전역 input-buffer component, section별 recovery duplicate, 별도 montage 다섯 개는 만들지 않는다. 향후 단계마다 서로 다른 blend 설정이 실제로 확인되거나 같은 montage-notify 수명 코드가 여러 Ability에 반복될 때만 asset/task 분리를 재검토한다.
- `UAnimationLibrary::ExtractRootTrackTransform`을 `1/120 s` 중앙 차분으로 표본 확인한 파생값에서 Attack02 시작의 root 이동 속도는 playback asset 좌표 Y축 약 `335.36 asset-unit/s`, Attack01 `0.3825092135 s`는 약 `328.62`, `0.55 s`는 약 `93.76`이었다. 앞서 확인한 bone pose 최접근 구간 `0.54–0.57 s`와 root 속도 최접근 시점이 같지 않으므로 pose 한 기준으로 고정 cut을 선정하지 않는다. 이 값은 mesh scale을 적용한 world 속도나 원작 직접 기록값이 아니며, PIE capsule 연속성의 표적 관측 지점을 고르는 데만 사용한다.

## 2026-09-17 — ARCH-42 WeakAttack 콤보 창 계약 단순화 재검토

- 실제 `UKhazanWeakAttackAbility`는 header 76줄과 cpp 439줄, 합계 515줄이며 현재 실행 가능한 edge는 `Attack01 + Weak → Attack02` 하나다. 코드량 대부분은 콤보 규칙이 아니라 두 종류의 NotifyState Begin/End, 겹침 depth, 이전 Montage instance 식별, task 교체 방어와 cleanup에서 발생했다. 이 상태로 section별 분기를 복사해 5타를 완성하는 방식은 채택하지 않는다.
- 원작 metadata의 `ReserveInput`과 input-progression 후보가 서로 다른 이름과 겹치는 시간 구간을 가진다는 사실만으로 두 런타임 상태창의 정확한 의미가 증명되지는 않는다. 따라서 ARCH-40의 `InputReservationDepth`와 `ComboAdvanceDepth`를 제품 구조의 필수 상태로 본 판정은 철회한다. 원작 시간 후보와 영상은 프로젝트 Montage에서 입력 허용 시작점과 전환 확정점을 고르는 근거로 사용하되, 원작 내부 이벤트를 일대일로 복제하지 않는다.
- Weak 연속타의 최소 authored 계약은 각 공격에 `ComboInputOpen` 점 Notify 하나와 `ComboCommit` 점 Notify 하나다. Open 이후 최초 semantic input 한 건만 `BufferedInputTag`에 저장하고 Commit에서 현재 step, 입력 tag, 해금 조건을 다시 검사한다. Commit 뒤에는 입력을 닫고 buffer를 비운다. NotifyState End, 겹침 depth, 여러 window의 합성은 없다.
- 활성 Ability의 최소 mutable 상태는 `CurrentComboStep`, `BufferedInputTag`, `bAcceptingComboInput`, 현재 Montage task와 delegate 제거를 위한 AnimInstance reference다. Step은 `1..5`의 section 배열을 인덱싱하고 `1→2`, `2→3`, `3→4`는 같은 증가 규칙을 사용한다. `4→5`에서만 Progression이 소유한 해금 tag를 ASC에서 확인한다. 잠긴 경우 4타 회복을 그대로 끝내며 별도 5타 Ability를 만들지 않는다.
- `MontageSetNextSectionName()`은 UE 5.8.2 source상 next-section index를 바꿀 뿐 pose cross-fade를 만들지 않는다. 각 원본 시퀀스가 회복부까지 포함하고 전환 보간이 필요하다는 제품 조건 때문에 ARCH-41의 같은 Montage 재생/목표 section 시작 방식은 유지한다. 다만 전환은 `ComboCommit` 점에서만 일어나므로 전환 전 Open/Commit을 이미 지난 이전 instance의 늦은 NotifyState End를 구별할 필요가 없어지고 active Montage instance ID 상태를 제거할 수 있다.
- `UKhazanWeakAttackAbility`는 한 번의 활성 수명 동안 전체 Weak chain을 계속 소유한다. ASC는 입력 전달만 하고 combo step, window, unlock branch를 소유하지 않는다. Combo DataAsset, 전역 buffer component, custom Notify class, custom AbilityTask는 여전히 만들지 않는다. 동일한 Montage 재생·Notify 수명 코드가 두 번째 실제 Ability에 반복될 때만 공통 task 추출을 다시 심사한다.
- 이 절은 구조 재검토 결과이며 아직 Source·Montage에 적용되지 않았다. 실제 Open/Commit 시간은 저장된 원작 metadata 후보와 원작 영상, PIE pose/root-motion 연속성을 함께 검증해 section별로 확정한다.

## 2026-09-17 — ARCH-43 단일-task 브랜치 컷 확정과 Jump 의미 교정

### 채택 범위

회수 동작까지 들어 있는 각 WeakAttack 시퀀스를 온전히 보존하고, 모든 Montage section의 authored `Next Section`을 `None`으로 두는 브랜치 컷 구조를 P6의 기본 표현 계약으로 채택한다. 입력이 없으면 현재 section이 회수 동작까지 재생된 뒤 Montage와 Ability가 자연 완료된다. 합법적인 입력 한 건이 예약돼 있으면 현재 타수의 authored branch 지점에서 다음 section으로 이동한다.

| 제안 요소 | 판정 | 프로젝트 계약 |
|---|---|---|
| `Attack01`–`Attack05` 전체 시퀀스와 unlinked section | 채택 | 각 section은 자기 공격과 전체 회수를 가진다. 자동 연결은 전부 `None`이다. |
| 한 번의 `PlayMontageAndWait`로 전체 Weak chain 실행 | 채택 | 같은 Montage instance를 유지하고 마지막으로 진입한 unlinked section이 끝날 때 task가 완료된다. |
| `MontageJumpToSection`으로 회수부를 건너뜀 | 채택 | 활성 Ability의 `MontageJumpToSection()`을 통해 ASC의 현재 Montage 명령 경로를 사용한다. |
| 입력 가능 구간 어디서든 입력 즉시 Jump | 기본안에서 제외 | 입력 시점마다 출발 pose와 root 속도가 달라진다. 고정 `ComboCommit` 지점에서만 Jump해 authored cut을 재현한다. |
| `State.Combo.CanAdvance` loose tag | 제외 | 한 Ability 실행 안에서만 소비되는 일시적 창이다. ASC 공유 상태로 올릴 소비자가 없고 중단 cleanup 위험만 늘어난다. |
| `Event.Combo.WindowOpened` Gameplay Event | 제외 | Montage와 이를 실행한 같은 Ability 사이의 지역 신호다. AnimInstance의 내장 Montage Notify delegate로 충분하다. |
| custom `ANS_ComboWindow` | 제외 | UE 내장 `Montage Notify`로 필요한 두 point를 전달할 수 있다. 별도 Notify class는 의미나 수명을 추가하지 않는다. |
| 전역 input-buffer component·Combo Manager·범용 graph runtime | 제외 | 현재 실행 Ability의 한 칸 buffer와 순차 section 규칙으로 충분하다. |

이 판정은 ARCH-41의 “타수마다 같은 Montage를 새 task로 다시 재생”을 기본 경로에서 대체하고, ARCH-42의 `ComboInputOpen`/`ComboCommit` 고정 지점은 유지하면서 전환 명령만 task 재생에서 section jump로 바꾼다. 과거 절은 조사 이력으로 보존하지만 P6 구현은 이 절을 따른다.

### UE 5.8.2에서 Jump가 실제로 하는 일

- `UGameplayAbility::MontageJumpToSection()`은 이 Ability가 ASC의 현재 animating ability일 때 `CurrentMontageJumpToSection()`을 호출한다. Ability가 `UAnimInstance`를 직접 찾아 명령하는 것보다 현재 GAS Montage 소유 관계를 보존한다.
- `FAnimMontageInstance::JumpToSectionName()`은 대상 section 위치를 계산하고 `SetPosition(NewPosition)`을 호출한다. Montage를 다시 재생하거나 Blend In을 다시 적용하지 않는다.
- `FAnimMontageInstance::SetNextSectionName()`은 section 연결 인덱스만 바꾼다. 이것도 pose cross-fade를 만들지 않는다.
- 따라서 “`JumpToSection`이 Montage Blend In Time으로 다음 타수에 보간한다”는 설명은 사실이 아니다. 한 task를 유지할 수 있다는 장점과 자동 보간이 없다는 품질 조건을 함께 받아들여야 한다.

Jump 전환 품질은 코드가 만든 임의 보간이 아니라 `현재 타수의 고정 cut pose/root delta`와 `다음 타수 section 시작 pose/root delta`의 호환성으로 결정한다. 먼저 원작 metadata 후보와 영상을 이용해 고정 branch 지점을 정하고, PIE에서 capsule 위치·yaw·root-motion 속도와 상체/하체 pose 튐을 확인한다. 호환되는 지점을 찾을 수 없다는 실제 증거가 생기면 같은 Montage 재생에 의한 cross-fade, 별도 transition clip 또는 AnimGraph inertialization을 서로 비교해 하나로 교체한다. 여러 전환 방식을 미리 동시에 유지하는 runtime 분기는 만들지 않는다. Inertialization은 pose 완화 수단이며 Root Motion 연속성을 대신 검증해 주지 않는다.

### 타수마다 필요한 authored 신호

`Attack01`–`Attack04`에는 UE 내장 `Montage Notify` 두 개만 둔다.

1. `ComboInputOpen`: 이 타수에서 다음 분기용 입력 한 건을 받기 시작하는 지점이다.
2. `ComboCommit`: 입력을 닫고, 저장된 입력·현재 타수·해금 상태를 다시 검사해 다음 section으로 Jump하는 유일한 지점이다.

`ComboInputOpen` 뒤 첫 semantic input만 `BufferedInputTag`에 들어간다. `ComboCommit`에서 입력이 없거나 edge가 없거나 5타가 잠겨 있으면 buffer를 비우고 현재 section의 회수부를 그대로 재생한다. 전환이 성공하면 현재 step을 먼저 다음 step으로 갱신하고, 입력 허용을 닫고, buffer를 비운 뒤 `MontageJumpToSection(NextSection)`을 호출한다. 다음 section의 `ComboInputOpen`을 만나기 전 입력은 그 다음 타수로 이월하지 않는다. 이 규칙으로 연타가 한꺼번에 3·4·5타까지 예약되는 것을 막는다.

고정 point 두 개를 쓰는 이유는 단순히 NotifyState 코드를 줄이기 위해서가 아니다. 입력을 받을 수 있는 구간과 실제 pose/root-motion을 자르는 순간을 분리하면, 플레이어 입력 반응성과 애니메이션 전환 품질을 각각 authored할 수 있다. 원작 `ReserveInput`과 `SkillInputProg`가 별도 시간 구간으로 기록된 사실과도 모순되지 않는다. 다만 proprietary 소비 의미가 확인되지 않았으므로 기존 구간의 시작·끝 값을 그대로 두 point로 단정하지 않는다. Attack01의 저장된 playback 후보는 `ReserveInput 0.2205535080–0.4756474282 s`, `0.3825092135–0.6388580379 s`, progression `0.2929789424–0.5131536622 s`, `0.5165015501–0.9242099718 s`이며, 최종 Open/Commit 위치는 원작 영상과 cut 품질 검증으로 확정한다.

원작 근거가 이후 “구간 안의 어느 프레임에서도 즉시 cancel”을 요구하고 그 전체 구간의 pose/root-motion 연속성이 확인되면, 두 point 계약을 내장 `Montage Notify Window`와 Ability-local phase로 교체할 수 있다. 그 경우에도 ASC tag나 Gameplay Event는 추가하지 않는다. section jump로 열린 NotifyState를 벗어나면 UE가 이전 state의 `NotifyEnd`를 발생시키므로, `WaitingForWindow / WindowOpen / WindowClosed` 같은 지역 phase에서 `WindowOpen`일 때만 End를 소비해야 한다. 현재는 그러한 가변 즉시 전환 근거가 없으므로 이 예외 구조를 먼저 구현하지 않는다.

UE 5.8.2의 `FAnimMontageInstance::Terminate()`도 Montage 중단 시 활성 State Branching Point 전부에 `NotifyEnd`를 보낸다. 따라서 Window End 자체를 무조건 “콤보 확정”으로 쓰려면 자연 종료와 interrupt/cancel 종료를 다시 구별해야 한다. `ComboCommit` point는 중단 때문에 합성되는 End가 없으므로 이 예외 상태와 필터를 만들지 않는 더 작은 계약이다.

### Ability의 최소 runtime 상태와 책임

활성 `UKhazanWeakAttackAbility`가 가지는 mutable 상태는 다음으로 제한한다.

- `CurrentComboStepIndex`: `Attack01`–`Attack05` 고정 section 배열의 0-based index다. activation에서 0으로 시작하고 종료에서 `INDEX_NONE`으로 reset한다.
- `BufferedInputTag`: 현재 타수에서 받은 최초 semantic input 한 건이다. invalid tag가 빈 상태다.
- `bAcceptingComboInput`: `ComboInputOpen`과 `ComboCommit` 사이에만 `true`다.
- `ActiveMontageTask`: activation에서 한 번 만든 `PlayMontageAndWait` task다.
- `BoundAnimInstance`: 내장 Montage Notify Begin delegate를 `EndAbility()`에서 제거하기 위한 weak reference다.

section 이름 배열은 정적 사실이며 runtime 상태가 아니다. `CurrentSectionName`, Montage instance ID, 두 window depth, Notify End handler, step별 task 재생과 `bTransitionCommitted`는 제거 대상이다. payload는 해당 `WeakAttackMontage`에서 온 Notify인지 stateless하게 확인한다.

`InputPressed()`는 입력 허용 중이고 slot이 비어 있을 때만 `Input.Action.WeakAttack`을 저장한다. `ComboCommit` handler 한 곳이 현재 index와 tag로 다음 section을 결정한다. `1→2`, `2→3`, `3→4`는 같은 순차 규칙이고 `4→5`에서만 Progression/Save가 ASC에 투영한 확정 해금 사실을 읽는다. 아직 그 투영 tag 이름이 Source에 없으므로 임의 문자열을 만들지 않는다. 잠금 실패는 현재 4타를 취소하지 않고 회수까지 완료시킨다.

정상 완료, Montage interrupt, Ability cancel, Pawn 교체와 EndPlay는 모두 기존 `EndAbility()` cleanup으로 모인다. 여기서 Notify delegate를 해제하고 task pointer, step, buffer와 입력 허용 사실을 reset한다. ASC는 Spec 활성화와 active Spec input 전달, 현재 Montage 명령 중계만 맡으며 combo step·재생 속도·window를 저장하지 않는다.

<a id="character-architecture-v3-native-minimal-20260917"></a>
## 2026-09-17 — 아키텍처 v3 확정: UE 네이티브 우선·최소 실행 소유자

### 결정의 지위와 우선순위

이 절은 현재 Source, UE 5.8.2 엔진 Source, 최신 원작 metadata 보고서와 실제 제품 범위를 다시 대조한 전면 재감사 결과다. 기존 v2.2의 GAS 중심 단순성 원칙과 ARCH-43의 단일-task 브랜치 컷을 유지하되, 구현보다 큰 추상화와 UE 네이티브 기능을 중복한 부분을 아래 계약으로 대체한다.

- v1의 제어 HFSM, v2.1의 ActionRequest/Result·Request/Execution 원장·전신 lane, ARCH-38~41의 custom event/window·두 depth·Montage 재시작 경로는 과거 이력이다. 새 구현에 복사하지 않는다.
- v2의 7계층은 책임을 점검하는 분류표로만 남긴다. 7개 Manager/Component/DataAsset을 만드는 구현 청사진으로 사용하지 않는다.
- 최신 실행 구조는 `입력 어댑터 → ASC → 활성 Ability/Task → Montage/AnimGraph/CMC`이며, 실제 두 번째 소비자나 독립 수명이 생긴 기능만 별도 타입으로 추출한다.
- 이 절은 문서 아키텍처를 확정한 것이며 현재 Source, Blueprint, Montage, AnimSequence를 적용 완료로 뜻하지 않는다.

### [적발된 설계 결함]

| 영역 | 확인된 결함 | 판정과 조치 |
|---|---|---|
| WeakAttack 실행 | 현행 `UKhazanWeakAttackAbility`는 01→02 한 edge에 section별 task 재생, instance ID, 두 NotifyState depth, Begin/End handler를 가진다. | 기능보다 큰 상태다. ARCH-43의 한 task·두 point Notify·step index·한 칸 buffer로 교체한다. |
| section 전환 | `JumpToSection` 또는 `SetNextSection`이 Montage Blend In/Out으로 section 사이를 보간한다는 과거 설명이 있었다. | UE 5.8.2에서 Jump는 위치를 `SetPosition`하고 SetNext는 연결 index만 바꾼다. section 내부 cross-fade는 없다. |
| 관성화 Notify | 다음 section 첫 frame에 `PlayRequestInertialization`/`Request Inertialization` Notify를 두면 Jump 순간 항상 실행된다는 안. | 현재 UE 5.8.2 설치본에 그 이름의 내장 AnimNotify가 없다. section 시작과 같은 시각의 Branching Point는 검색에서 `TriggerTime <= StartTrackPos`로 건너뛸 수 있다. custom Notify를 만들지 않고 Commit 코드가 request와 Jump를 연속 수행한다. |
| 관성화 범위 | Inertialization이 root 이동 에너지까지 이어 주어 popping을 완전히 없앤다는 주장. | Inertialization은 평가 pose/curve의 offset을 감쇠한다. Montage root motion은 별도 시간 구간에서 추출되어 CMC로 가므로 capsule의 translation/yaw delta는 보간하지 않는다. authored cut과 root delta 검증은 계속 필수다. |
| AnimGraph 배치 | 현재 정본의 Inertialization은 `GroundedLocomotion` 뒤, `DefaultSlot` 앞에 있다. | Slot이 만든 inertialization request의 downstream에 있지 않아 공격 Montage request를 받을 수 없다. 기존 노드를 최종 Slot 뒤로 이동해 한 노드가 locomotion과 slot request를 함께 받는 것을 기본안으로 한다. |
| Ability base | 현재 `UKhazanGameplayAbility`는 공통 동작과 데이터가 없는 빈 subclass다. | 실제 두 Ability가 공유하는 코드가 생기기 전에는 제거하고 `UKhazanWeakAttackAbility`가 `UGameplayAbility`를 직접 상속한다. |
| ASC 입력 | ASC가 combo 상태까지 가져가야 한다는 과거 후보와 `ActivationInfo` deprecated fallback이 남아 있다. | ASC는 exact input tag→Spec press/release/activation만 중계한다. Combo state는 올리지 않는다. `InstancedPerActor`의 실제 primary instance activation info를 사용하도록 정리한다. |
| 입력 callback | Weak/Strong마다 Started/Completed/Canceled 함수를 복제했고 Completed와 Canceled를 같은 release 의미로 합쳤다. | tag payload를 받는 세 generic callback으로 줄인다. Strong cancel이 실제 소비될 때 정상 release와 별도 의미 event로 보낸다. |
| Enhanced Input Combo | 고정 키 순서를 `UInputTriggerCombo`로 전투 콤보의 권위로 삼는 안. | UE 5.8에서 관련 타입이 deprecated이며 montage node/window, 해금, 비용, cancel 상태를 알지 못한다. 전투 콤보 기반으로 사용하지 않는다. |
| Enhanced Input 전처리 | `AKhazanPlayer`가 장치 dead zone을 다시 계산한다. | 장치 dead zone·축 swizzle·negate는 InputAction/MappingContext modifier가 소유한다. Gait 선택처럼 gameplay 의미가 있는 threshold만 프로젝트 설정에 남긴다. |
| Asset 로딩 | `UKhazanAssetManager`+`UKhazanAssetData`가 GameplayTag→SoftPath registry, preload, 별도 hard-reference map을 중복 구현한다. | 현재 실제 소비는 InputData와 CharacterDefinition 두 개다. cache map은 조회에 쓰이지 않고 release API는 streamable handle을 해제하지 않는다. 직접 asset reference로 단순화하고, 나중에 streaming이 필요할 때 UE Primary Asset/Bundle API를 사용한다. |
| GameInstance | `UKhazanGameInstance`의 유일한 제품 책임이 custom AssetManager 초기화이며 constructor/Shutdown은 비어 있다. | AssetManager 이관 뒤 실제 GameInstance 수명이 생기지 않으면 C++ subclass를 제거한다. |
| Character/Player/Monster | 빈 `BeginPlay`/`Tick`, 활성화된 Actor Tick, 빈 Monster shell과 중복 `AKhazanPawn`이 남아 있다. | 참조 검사를 통과한 빈 override와 Tick을 제거한다. `AKhazanPawn`/빈 Monster 삭제는 Blueprint parent reference를 먼저 확인한다. |
| Player presentation | camera arm/pitch, mesh 위치·회전, 특히 임시 `0.009` scale이 native constructor에 고정돼 있다. | BP/character presentation data로 옮긴다. animation/root motion 데이터를 이 임시 mesh scale에 맞춰 변형하지 않는다. |
| Anim snapshot | `MoveInputWorld`, `MaxAcceleration`, `MaxBrakingDeceleration`, `RequestedGait`, `MaxAllowedGait`를 매 frame 복사하지만 C++ 파생 계산에서 읽지 않는다. | BP 비공개 snapshot의 미사용 필드를 제거한다. BlueprintReadOnly 멤버는 실제 ABP reference audit 뒤 필요한 것만 유지한다. |
| Anim transition | 모든 Start 제외가 확정됐는데 `bShouldPlayStart`를 매 frame false로 쓰며, 속도 임계값 일부는 출처 표시 없이 cpp literal이다. | `bShouldPlayStart`를 제거한다. 실제 필요한 animation threshold는 한 설정 영역에 원작값/계산값/임시값 상태를 표시한다. |
| 수학 API | native C++에서 `UKismetMathLibrary`를 단순 forward/right/unrotate/atan2 연산에 사용한다. | `FRotationMatrix`, `FRotator::UnrotateVector`, `FMath::Atan2/RadiansToDegrees`로 줄인다. 새 utility class는 만들지 않는다. |
| Locomotion intent | 동시에 하나뿐인 possessor 입력 source에 random GUID handle과 진단 enum까지 둔다. | 현재 동작을 당장 깨지 않지만 A1 AI 연결 때 source pointer 검증만으로 충분한지 다시 측정한다. 같은 Controller 재빙의의 stale callback이 실제 없으면 intent GUID/type을 제거한다. |
| Locomotion constraint | 여러 제한 원인이 같은 bool을 덮지 않도록 handle map을 둔 구조. | 이것은 공격·Stamina·상태 효과의 중첩 cleanup에 필요한 구조이므로 유지한다. 현재 소비 없이 priority 종류를 더 늘리지는 않는다. |
| 미래 Combat/Target/Interaction | 이름만 정한 Component, Manager, Result, DataAsset을 단계 계획에 미리 고정한 부분. | 첫 실제 hit/target/interaction을 Ability/Task/Actor owner에서 수직 구현하고 독립 수명 또는 둘 이상의 실제 소비가 확인될 때만 추출한다. |
| StateTree | Player action과 GAS 실행을 StateTree에 다시 표현하거나 BT와 StateTree를 동시에 두는 후보. | Player에는 사용하지 않는다. 첫 Monster AI부터 StateTree를 유일한 상위 AI orchestration 기본안으로 사용하되 Task는 CMC/ASC 요청과 완료 대기만 맡는다. |
| Debug/production 경계 | GameMode가 Cog 창을 항상 등록하고 Cog 모듈을 runtime public dependency로 둔다. | 개발 빌드 전용 경계로 옮긴다. Shipping gameplay 초기화와 debug UI 등록을 섞지 않는다. |
| 현재 build 상태 | `KhazanPlayerController.cpp`가 `ULocalPlayer::GetSubsystem`을 사용하면서 `Engine/LocalPlayer.h`를 직접 include하지 않는다. ASC는 deprecated `FGameplayAbilitySpec::ActivationInfo`를 읽는다. | 아키텍처와 별개인 즉시 정리 항목이다. cold build 전에 include와 activation-info 경로를 고친다. |

### [아키텍처 재설계안]

#### 1. 런타임 소유자는 다섯 경계만 유지한다

```text
Enhanced Input / AI StateTree
    ↓ 의미 입력 또는 행동 선택
PlayerController / AI Task
    ↓ input tag press/release 또는 Ability 활성화
Khazan ASC
    ↓ granted Spec 활성화, GAS tag/effect/cost/cancel
활성 GameplayAbility + 엔진 AbilityTask
    ↓ Montage section, authored Notify, root motion
AnimGraph(DefaultSlot → Inertialization) + CharacterMovementComponent
```

1. **입력/AI 의도:** Enhanced Input은 장치 값을 정규화하고 press/release/cancel을 만든다. Controller는 의미 tag로 번역한다. 미래 AI StateTree는 물리 키를 흉내 내지 않고 Ability를 요청한다.
2. **GAS 공통 상태:** ASC는 granted Spec, Owned Tag/Effect/Attribute와 input protocol을 소유한다. 전역 combo parser나 montage controller가 아니다.
3. **액션 실행:** 활성 Ability가 자기 실행의 current step, 한 칸 buffer, cost, cancel, Montage task와 cleanup을 소유한다.
4. **이동:** CMC가 실제 capsule 이동과 root motion을 처리한다. LocomotionComponent는 공통 gait/rotation/input block과 실제 중첩 제약만 해결한다.
5. **표현:** Montage/AnimBP/Sync Marker/Inertialization/GameplayCue가 pose와 피드백을 표현한다. gameplay 승인과 피해 결과를 작성하지 않는다.

GameplayCue, Motion Warping, Targeting, hit trace, Interaction은 위 다섯 경계에 실제 기능으로 붙는다. 각각을 선행 Manager로 만들지 않는다.

#### 2. Weak 1–5타의 최종 최소 계약

- Montage 하나, `Attack01`–`Attack05` section 다섯 개, 각 section의 authored `Next Section=None`을 사용한다.
- `Attack01`–`Attack04`마다 내장 Montage Notify point `ComboInputOpen`과 `ComboCommit`만 둔다. gameplay 분기이므로 `Branching Point`를 사용한다.
- activation마다 `PlayMontageAndWait` task를 한 번만 `Attack01`에서 시작한다.
- mutable state는 `CurrentComboStepIndex`, `BufferedInputTag`, `bAcceptingComboInput`, `ActiveMontageTask`, delegate 제거용 `BoundAnimInstance`만 둔다.
- Open 뒤 최초 합법 입력 한 건만 저장한다. Commit이 오면 입력을 닫고 edge·section·해금·현재 Montage 소유권을 검증한다.
- `1→2→3→4`는 같은 순차 규칙을 사용한다. `4→5`에서만 Progression이 ASC에 투영한 실제 해금 tag를 확인한다. 그 tag가 확정되기 전에는 문자열을 만들지 않는다.
- 성공 시 Ability private 함수 하나가 관성화 request를 제출하고 `MontageJumpToSection()`을 호출한다. 실패/무입력/잠금이면 현재 section의 recovery를 끝까지 재생한다.
- Weak→Strong 등 다른 입력의 실제 branch가 생기면 같은 one-slot tag와 같은 Commit 경계에 확인된 edge만 추가한다. 범용 Combo Graph/DataAsset은 두 무기 또는 둘 이상의 실제 실행 class가 같은 schema를 공유할 때만 추출한다.

#### 3. Jump와 관성화의 정확한 순서

`ComboCommit`의 Branching Point callback은 Game Thread의 Montage advance 중 실행된다. 전환 검증을 통과한 경우 다음 순서를 한 함수 안에서 수행한다.

```cpp
AnimInstance->RequestMontageInertialization(
    WeakAttackMontage,
    ComboSectionInertializationDuration,
    nullptr);

MontageJumpToSection(NextSectionName);
```

- `RequestMontageInertialization()`은 Montage의 Slot Group에 다음 AnimGraph update용 request를 기록한다. `MontageJumpToSection()`은 GAS가 현재 animating ability인지 확인하는 경로를 유지한다.
- request를 다음 section 첫 frame Notify에 맡기지 않는다. 첫 frame marker의 경계 누락과 한 frame 늦은 요청을 피한다.
- `ComboSectionInertializationDuration`은 Ability content 설정 한 곳에 둔다. 원작 Step의 `AnimBlendAlpha=0.1`을 초 단위 duration으로 대응하는 값은 **원작 필드 기반 프로젝트 매핑 후보**이며 proprietary 의미가 증명된 직접값은 아니다. `0.15 s`는 현재 근거가 없으므로 기본 범위로 확정하지 않는다.
- BlendProfile은 실제 손/무기/발 QA에서 전신 동일 감쇠가 문제라는 증거가 생길 때 추가한다. 미리 per-step 배열이나 profile asset을 만들지 않는다.
- Dead Blending은 UE 5.8에서 experimental이므로 shipping 기본안으로 바꾸지 않는다.

#### 4. AnimGraph의 한 노드 배치

현재 기본안은 기존 Grounded 내부 Inertialization을 복제하지 않고 최종 합성 경계로 이동하는 것이다.

```text
Locomotion State Machine
    → DefaultSlot
    → Inertialization
    → (향후 실제 IK/Control Rig가 있으면 그 앞)
    → Output Pose
```

UE 문서상 request를 만든 노드보다 downstream이면 되고, 한 Inertialization 노드가 여러 request를 처리할 수 있다. 따라서 이 배치가 내부 locomotion transition과 DefaultSlot Montage request를 함께 받는지 ABP Debugger/Animation Insights로 검증한다. 서로 다른 상·하체 공간이 실제 필요할 때만 두 번째 노드를 추가한다.

관성화가 시작되면 outgoing source pose는 더 평가되지 않으므로, Commit 뒤 반드시 실행돼야 할 gameplay Notify를 recovery 쪽에 두지 않는다. hit/cost/branch의 필수 신호는 Commit 이전 또는 다음 section의 정상 진행 구간에 둔다.

#### 5. Root Motion 품질 gate

관성화 합격과 Root Motion 합격을 따로 본다.

- visual pose: 손·무기·골반·양발의 한 frame pop과 관성 감쇠 중 ghosting/overshoot를 확인한다.
- capsule: Commit 직전 frame, 전환 frame, 다음 frame의 world translation/yaw delta를 기록한다.
- collision: 벽, 경사, 적 capsule 접촉에서 CMC가 전환 delta를 소비하는지 확인한다.
- authored data: cut 시각과 다음 section 첫 root delta의 방향·크기가 맞지 않으면 Commit 또는 next clip 시작 범위를 조정한다.
- animation/root data를 임시 mesh scale `0.009`에 맞춰 보정하거나 Actor를 코드로 보간하지 않는다.

관성화가 pose를 개선해도 capsule 속도/yaw가 튀면 완료가 아니다. 이 경우 먼저 authored cut/root track을 고치고, 해결 불가한 실제 edge에만 별도 transition clip 또는 Montage instance cross-fade를 비교한다. production runtime에 두 전환 방식을 동시에 남기지 않는다.

#### 6. UE 네이티브 기능 채택표

| 기능 | 채택 방식 |
|---|---|
| Enhanced Input modifiers | dead zone, axis swizzle, negate와 장치별 scaling에 사용한다. |
| Enhanced Input Chord | 원작에 실제 동시 modifier 입력이 확인된 명령에만 사용한다. Weak/Strong 순차 콤보 parser로 쓰지 않는다. |
| Enhanced Input Combo Trigger | UE 5.8 deprecated이므로 신규 기반에서 제외한다. |
| GAS Ability/Task | 비용·태그·취소·Montage 실행 수명의 기본이다. 현재 `PlayMontageAndWait`를 유지한다. |
| Montage Notify point | Combo Open/Commit처럼 한 시각의 authored 결정에 사용한다. |
| AnimNotifyState/Notify Window | hit trace, 무적, guard처럼 실제 duration이 의미일 때만 사용한다. Ability 종료가 최종 cleanup이다. |
| Inertialization | section jump의 pose pop 완화와 locomotion transition에 한 downstream 노드를 공유한다. |
| Sync Marker/State Machine | 기존 locomotion 발 위상·Stop 선택에 유지한다. |
| Motion Warping | 타깃 보정이 필요한 실제 Root Motion 공격부터 도입한다. combo section 연결 자체를 대신하지 않는다. |
| GameplayCue | 확정된 hit/guard/parry 결과의 VFX/SFX/카메라·진동 피드백에 사용한다. |
| StateTree | 첫 Monster AI의 상위 판단과 보스 패턴 orchestration 기본안이다. Player action/GAS의 두 번째 상태 원본으로 쓰지 않는다. |
| Primary Asset/Asset Bundle | runtime streaming과 독립 unload가 실제 필요해질 때 custom registry 대신 사용한다. |

#### 7. 구현 단순화 순서

1. cold build blocker인 `Engine/LocalPlayer.h` include와 ASC deprecated activation-info 접근을 정리한다.
2. 빈 `UKhazanGameplayAbility`, 빈 Tick/BeginPlay, 미사용 `Input.Action.Jump`와 snapshot 필드를 reference audit 후 제거한다.
3. WeakAttack을 ARCH-43/v3 한 task 구조로 바꾸고 01→02 한 edge만 먼저 검증한다.
4. ABP의 기존 Inertialization 노드를 `DefaultSlot` 뒤로 이동하고 request-before-jump를 연결한다.
5. pose와 root-motion gate를 통과한 뒤 같은 배열 규칙으로 03/04, 실제 해금 tag가 준비되면 05를 연다.
6. input callback을 tag payload 기반 generic 함수로 정리하고 Enhanced Input asset에서 dead zone을 소유한다.
7. Character/InputData를 명시적 asset reference로 이관한 뒤 custom AssetManager/AssetData/GameInstance 초기화 계층을 제거한다. runtime streaming 소비가 생기면 UE Primary Asset으로 다시 연결한다.
8. 첫 실제 hit, Strong charge, dodge/parry, Monster AI 순으로 수직 기능을 추가한다. 각 단계에서 반복이 확인되기 전에는 custom AbilityTask, CombatComponent, Combo DataAsset, TargetingComponent를 만들지 않는다.

### 유지하는 구조

- Character 소유 ASC와 `IAbilitySystemInterface`, CharacterDefinition의 작은 `InitialAbilityGrants` 배열은 유지한다.
- ASC의 exact Dynamic Spec Source Tag 검색은 Ability 수가 적은 현재 프로젝트에서 충분하다. 별도 tag→handle cache를 만들지 않는다.
- 한 타수당 one-slot `first accepted input wins`와 section 진입 전 미래 입력을 쌓지 않는 정책을 유지한다.
- `LocomotionComponent → CMC`, 원인별 movement constraint handle, Montage Root Motion, `Root Motion from Montages Only`를 유지한다.
- Main AnimInstance의 Game Thread snapshot→thread-safe 파생 계산 경계와 locomotion Sync Marker를 유지한다.

### 적용 상태

이번 전면 재감사는 Architecture/Migration/Animation/Source-BP-Config 문서를 갱신한다. Source, Config, Blueprint, Montage, AnimSequence와 DataAsset은 수정하지 않았으며 cold build와 PIE도 새로 실행하지 않았다. 현행 WeakAttack 515줄 구조와 현재 ABP node 위치는 아직 디스크에 남아 있으므로 다음 구현에서 위 순서대로 이관한다.

### v3 보완 — Weak/Strong 조합·홀드 입력의 최소 전달 계약

- 같은 입력의 재입력은 GAS의 active Spec `InputPressed`/`InputReleased` 경로를 그대로 사용한다. Weak 연타를 위해 별도 event나 전역 queue를 중복 발행하지 않는다.
- 활성 Weak가 Strong을, 활성 Strong이 Weak를 구별해야 하는 첫 실제 branch에서만 반대 키의 semantic press/release를 typed Gameplay Event로 전달한다. GAS generic input event에는 원래 Input Tag payload가 없으므로 이 경우에는 event가 실제로 새 의미를 운반한다. Montage window begin/end를 event로 우회하는 과거 구조와 목적이 다르다.
- Controller는 `Started`에서 press 시각을 하나 기록하고, `Completed`/`Canceled`에서 hold duration과 종료 원인을 만든다. node별 hold threshold, charge step, 해금, stamina와 분기 허용 여부는 Enhanced Input Trigger가 아니라 현재 실행 Ability가 판정한다.
- Enhanced Input의 `Hold`는 UI나 전역 입력처럼 실행 문맥과 무관하게 같은 threshold를 쓰는 기능에만 사용한다. 카잔 공격의 node별 hold 분기를 InputAction asset 여러 개로 복제하지 않는다.
- 실제 동시 입력 branch가 확인되면 Enhanced Input `Chorded Action`을 먼저 비교한다. 키 순서와 허용 오차가 원작과 맞지 않을 때만 위 press 시각 두 개로 chord를 파생한다.
- 현재 공격 Ability의 한 칸 `BufferedInputTag`만 다음 edge 후보를 소유한다. typed event는 입력을 전달할 뿐 current node, Montage window, unlock, cost 또는 transition을 소유하지 않는다.
- 다른 공격 Ability로 handoff가 필요하면 대상 Ability 활성화 성공을 확인한 뒤 출발 Ability를 끝낸다. press 시작 시각이나 이미 계산된 hold duration처럼 경계를 넘어야 하는 최소값만 `FGameplayEventData` 또는 명시적 activation payload로 넘기며 전역 combo session을 만들지 않는다.

<a id="arch-44-three-phase-combo-and-recovery-exit-20260918"></a>
## 2026-09-18 — ARCH-44: 3상태 콤보 입력과 회수부 행동 전환

### 기존 두 point 계약의 실제 결함

ARCH-43의 `ComboInputOpen → ComboCommit` 계약은 Commit 전에 들어온 입력을 고정 cut에서 실행하는 데는 충분하지만, Commit을 지난 직후 들어온 합법 입력도 모두 버린다. 원작 재현 목표에서 필요한 것은 다음 세 상태다.

1. `Closed`: 다음 콤보 입력을 받지 않는다.
2. `BufferUntilCommit`: 입력을 한 건 저장하지만 즉시 Jump하지 않는다.
3. `ImmediateCommit`: 입력 창은 계속 열려 있고, 새 입력 한 건이 들어오면 즉시 전환한다.

따라서 ARCH-43의 “타수마다 Open/Commit 두 point”는 다음 계약으로 대체한다.

- `ComboInputOpen`: `Closed → BufferUntilCommit`. 기존 buffer를 비운다.
- `ComboCommit`: 저장된 입력이 있으면 이 고정 지점에서 전환한다. 저장 입력이 없으면 `BufferUntilCommit → ImmediateCommit`으로 바꾸고 입력을 계속 기다린다.
- `ComboInputEnd`: `ImmediateCommit → Closed`. 전환 없이 남은 buffer를 비운다.
- Open–Commit 입력은 Commit까지 기다린다. Commit–End 입력은 들어온 프레임에 즉시 전환한다. End 이후 입력은 현재 타수에 예약하지 않는다.
- 세 개 모두 duration 0의 내장 `Montage Notify` point와 `Branching Point` tick을 사용한다. `ComboInputEnd`도 point 이름일 뿐 `OnPlayMontageNotifyEnd` delegate나 NotifyState가 아니다.
- 한 타수의 첫 합법 입력만 소비하는 one-slot 정책, 한 Montage task, authored `Next=None`, code-side inertialization 후 section Jump는 유지한다.

세 상태를 표현하려면 기존 `bAcceptingComboInput`에 `bComboCommitReached` 한 비트를 추가하거나 하나의 3값 enum으로 교체해야 한다. 현재 작은 Source에서는 bool 한 개 추가가 최소 변경이다. ASC tag, Gameplay Event, custom NotifyState, 전역 buffer나 Combo Manager는 필요하지 않다.

Commit 이후 Jump는 입력 프레임에 따라 출발 pose와 Root Motion delta가 달라진다. Inertialization은 pose만 완화하므로 Commit–End 전체 범위의 capsule translation/yaw가 다음 section 시작과 허용 가능한지 프레임별로 검사한다. 품질이 깨지는 뒤쪽 프레임은 `ComboInputEnd`를 앞당겨 authored 범위에서 제외한다.

### 공격 중 이동이 끝까지 기다리는 현재 원인

현재 저장본은 다음 사실을 가진다.

- `GA_Player_WeakAttack` CDO의 Activation Owned/Required/Blocked, Block/Cancel Ability tag container는 모두 비어 있다. C++도 `Block.Movement.Input`을 부여하지 않는다.
- `AKhazanPlayer::HandleInputMove()`는 `LocomotionComponent::SetMoveInputWorld()`로 raw 이동 의도를 먼저 기록한 뒤 허용 gate를 거쳐 `AddMovementInput()`을 호출한다.
- `ABP_Player`는 `Root Motion from Montages Only`다.
- UE 5.8.2 CMC는 `HasAnimRootMotion()` 동안 일반 `CalcVelocity()`를 건너뛰고 animation root-motion velocity로 `Velocity`를 덮는다.

따라서 현상은 현재 입력 자체가 사라진 것이 아니라, Attack02 Root Motion Montage를 중단하는 경로가 없어 montage가 끝날 때까지 일반 이동 속도가 capsule을 구동하지 못하는 것이다. 이는 엔진 동작으로는 정상이나 카잔 제품 동작의 완료 상태는 아니다.

### 콤보 point와 외부 행동 전환 point를 분리한다

`ComboInputEnd`는 “다음 타수 입력을 더 받지 않는 시각”이다. 이동·회피·다른 스킬로 현재 공격을 끊을 수 있는 시각과 의미가 다르다. 두 시각이 우연히 같더라도 C++ 계약을 합치지 않고 Montage에서 같은 프레임에 서로 다른 이름을 둘 수 있다.

첫 외부 전환 marker는 `RecoveryCancelOpen` point 하나로 둔다.

- point 전: 현재 타수의 공격 실행과 Root Motion을 유지한다.
- point 도달 시 이미 유효한 raw 이동 intent가 있으면 WeakAttack Ability를 조기 종료한다.
- point 이후 새 이동 입력이 시작되면 즉시 WeakAttack을 종료한다.
- 한 번 열린 뒤 section 자연 종료까지 다시 닫히지 않는 계약이면 별도 `RecoveryCancelEnd`를 만들지 않는다. 원작에서 다시 닫히는 구간이 확인될 때만 End가 필요하다.
- Ability 종료는 현재 `PlayMontageAndWait`의 `bStopWhenAbilityEnds=true`를 사용한다. task가 GAS 소유 Montage를 정지하고 Montage Blend Out으로 locomotion graph에 복귀한다. 별도 utility가 같은 Montage를 이중 정지하지 않는다.

이미 눌린 이동은 `LocomotionComponent`의 raw intent가 보존하므로 별도 이동 buffer bool이 필요 없다. point 이후 처음 눌린 이동을 active Ability에 알리는 교차 경계만 필요하다. 이때 polling Tick, Player→WeakAttack cast, 전역 command queue를 만들지 않는다. Enhanced Input의 Move Started를 의미 event 한 건으로 ASC에 전달하고 활성 Ability가 내장 `WaitGameplayEvent`로 받는 방식을 첫 수직 절편으로 사용한다. 이 event는 Montage가 같은 Ability에 보내는 combo window 신호를 우회하는 것이 아니라, 입력 owner와 action owner 사이에 실제 새 의미를 전달하므로 정당하다.

이동은 대상 Ability가 없으므로 출발 Ability를 종료해 locomotion으로 복귀한다. 다른 Montage/Ability로 전환할 때는 대상 Ability 활성화가 성공한 뒤 같은 Slot Group의 새 Montage가 이전 Montage를 interrupt하도록 한다. 대상 활성화 실패 전에 출발 Montage부터 정지해 빈 자세를 만들지 않는다. 피격·사망 같은 강제 경로까지 막으므로 일반 취소 창 구현에 `SetCanBeCanceled(false)`를 전역 gate로 사용하지 않는다.

### 적용 상태

이번 절은 Source/Content를 수정한 결과가 아니다. 현재 저장 Montage에는 `ComboInputOpen`과 `ComboCommit` 두 point만 있으며 둘 다 `Queued`다. `ComboInputEnd`, `RecoveryCancelOpen`, 3상태 입력 및 이동 handoff는 다음 구현 checkpoint다.

<a id="arch-45-edge-triggered-locomotion-exit-20260918"></a>
## 2026-09-18 — ARCH-45: ComboInputEnd 이후 새 이동 입력으로 로코모션 전환

### ARCH-44 이동 전환 계약 정정

ARCH-44의 3단계 콤보 입력 계약(`ComboInputOpen → ComboCommit → ComboInputEnd`)은 유지한다. 다만 이동 전환에 대해 기록한 `RecoveryCancelOpen`과 현재 raw 이동 intent 조회 방식은 이번 결정으로 철회한다.

- 이동 입력은 콤보 입력처럼 예약하거나 버퍼링하지 않는다.
- `ComboInputEnd`가 지난 뒤 새로 발생한 Move Input Action의 `Started` edge만 현재 공격을 끝낸다.
- `ComboInputEnd` 이전에 누르고 계속 유지한 방향은 End 이후 취소 요청으로 재사용하지 않는다. 다시 놓고 눌러 새 `Started`가 발생해야 한다.
- Move Action의 기존 `Triggered`는 매 프레임 locomotion intent와 `AddMovementInput()`을 갱신하는 현재 책임을 그대로 유지한다.
- 이번 단계에서는 `ComboInputEnd` 자체가 콤보 입력 창을 닫는 동시에 이동 취소 허용을 여는 경계다. 같은 프레임에 네 번째 Notify point를 중복 배치하지 않는다. 다른 공격에서 두 시각이 실제로 달라지는 authored 근거가 생길 때만 별도 `MovementCancelOpen` point로 분리한다.

### 최소 런타임 경로

```text
IA_Move Started
  → PlayerController가 Event.Input.MoveStarted를 ASC에 전달
  → 활성 WeakAttack의 WaitGameplayEvent task가 수신
  → bCanCancelToLocomotion 검사
      false: 아무 상태도 저장하지 않고 무시
      true : FinishAbility(true)
  → EndAbility
  → PlayMontageAndWait(bStopWhenAbilityEnds=true)가 현재 Montage를 Blend Out
  → Root Motion Montage에서 locomotion graph로 복귀
```

Controller는 물리 키를 의미 이벤트로 번역할 뿐 공격 Ability를 cast하거나 찾지 않는다. ASC는 `HandleGameplayEvent()`로 사건을 전달할 뿐 콤보 phase나 몽타주를 소유하지 않는다. 활성 Ability가 자기 authored gate와 실행 수명을 판단한다. 싱글 플레이 전용 프로젝트이므로 이 경로에 입력 RPC나 예측 계층을 추가하지 않는다.

`FinishAbility(true)` 시점은 입력을 받은 프레임이다. 다만 시각적인 pose 전환은 Montage asset의 Blend Out 설정을 사용한다. 이는 자연 종료를 기다린다는 뜻이 아니라 그 프레임부터 재생 중단과 locomotion blend가 시작된다는 뜻이다. Blend Out 동안 남은 Root Motion이 체감상 이동 시작을 늦추는지는 별도 runtime gate로 확인하며, 확인 없이 0초 정지나 Root Motion 비활성화를 적용하지 않는다.

### 공통화 결정

현재 구현에는 콤보 Ability가 `UKhazanWeakAttackAbility` 하나뿐이므로 다음 추상화는 만들지 않는다.

- **인터페이스:** UInterface는 `CurrentComboStepIndex`, one-slot buffer, phase, AbilityTask, delegate cleanup 같은 실행 상태와 수명을 소유하지 못한다. 각 Ability에 동일 구현을 다시 두게 되므로 중복 제거 수단이 아니다.
- **Jump 유틸리티:** `UGameplayAbility::MontageJumpToSection()`이 이미 ASC의 현재 animating Ability/Montage 경로를 사용한다. 한 줄을 감싸는 helper는 책임을 줄이지 않는다.
- **Notify 자동 배치 템플릿:** Open/Commit/End 시각은 각 clip의 타격·회수·Root Motion에 맞춘 authored 데이터다. 공통 비율로 자동 배치하면 잘못된 타이밍을 양산한다.
- **커스텀 Combo AbilityTask/Combo Component/DataAsset graph:** 현재 `PlayMontageAndWait`, `WaitGameplayEvent`, 세 Notify point, one-slot buffer로 필요한 수명이 표현된다. 엔진 task를 합친 새 task나 전역 manager를 지금 추가하면 cleanup과 디버깅 경로만 늘어난다.

두 번째 실제 콤보 Ability를 구현하기 직전에 `UKhazanComboGameplayAbility : UKhazanGameplayAbility` 추출을 수행한다. 그때 두 Ability에서 실제로 동일한 것으로 확인된 항목만 옮긴다.

- 공통 후보: 단일 Montage task 수명, Notify delegate bind/unbind, Open/Commit/End phase, one-slot 입력 소비, inertialization request 후 section jump, 이동 Started event 대기, 정상/취소 cleanup.
- 파생 Ability 책임: 입력 tag 조합, hold 판정, 다음 node/section 결정, unlock/cost 조건, 공격별 Montage와 authored section 집합.
- 선형 `CurrentIndex + 1` 규칙을 공통 base의 고정 정책으로 만들지 않는다. Weak/Strong 조합과 hold branch가 실제로 들어오면 파생 클래스의 `ResolveTransition(...)` 계약으로 분리한다.
- 두 번째 Montage부터 이름 누락·point 순서·Branching Point 설정 오류가 반복될 때 Editor-only validator를 추가한다. validator는 타이밍을 생성하지 않고 계약만 검사한다.

이 결정은 이후 모든 콤보 Ability에 코드를 복사하겠다는 뜻이 아니다. 현재 vertical slice를 먼저 완성하고, 두 번째 소비자가 생기는 첫 시점에 동작을 보존한 채 base로 추출한다.

### 적용 상태

이번 기록은 아키텍처 결정과 다음 공동 구현 절차다. Source, Blueprint, Montage asset은 이 기록으로 직접 수정하지 않았으며 `ComboInputEnd`의 실제 asset 배치, cold build, PIE 결과는 사용자의 적용 후 확인 대상이다.

<a id="arch-46-minimal-move-event-payload-20260918"></a>
## 2026-09-18 — ARCH-46: Move Started 이벤트의 최소 GameplayEvent payload

ARCH-45의 Controller → ASC 이벤트 전달에서 `FGameplayEventData::Instigator`, `Target`, `EventTag`를 채우라는 설명은 현재 소비 계약보다 과했다. 이 항목은 다음처럼 정정한다.

- 이벤트의 수신 대상은 `HandleGameplayEvent()`를 호출한 **ASC 인스턴스**로 이미 결정된다. payload의 `Target`은 전달 주소가 아니다.
- `Instigator`와 `Target`은 이벤트 의미상 행위자·대상이 필요할 때 소비자가 읽는 선택 metadata다. 현재 WeakAttack의 Move Started callback은 둘을 읽지 않으므로 채우지 않는다.
- 라우팅 태그는 `HandleGameplayEvent(EventTag, &Payload)`의 첫 번째 인자다. UE의 gameplay-event activation 및 `WaitGameplayEvent` 경로는 callback용 복사본에 일치한 태그를 채우므로 송신 측에서 `Payload.EventTag`를 중복 대입하지 않는다.
- 엔진 경로는 payload 포인터가 null이 아니라고 전제하므로 `nullptr` 대신 **비어 있는 지역 `FGameplayEventData`**를 전달한다.
- 현재 구현은 기존 `Input.Action.Move` 태그를 Move `Started` edge에서만 보내므로 그대로 사용한다. Started/Completed/Ongoing을 서로 다른 의미로 동시에 전달해야 할 실제 소비자가 생길 때만 별도 event tag를 분리한다.

따라서 Controller의 책임은 자신의 현재 Pawn에서 ASC를 얻고, 빈 non-null payload와 함께 해당 태그를 한 번 전달하는 것까지다. 별도 Pawn 지역 변수와 중복 유효성 검사는 필요하지 않다. Character의 ASC 소유 관계와 payload actor metadata는 서로 다른 계약이며, 전자가 후자를 요구하지 않는다.
<a id="arch-47-run-sprint-stop-sequence-root-motion-20260918"></a>
## 2026-09-18 — ARCH-47: Run/Sprint Stop의 Sequence Root Motion 계약

### 결정과 범위

- 기존의 locomotion 전체 root-locked 정책 중 `DAS_Khazan_Run_Stop_LF`, `DAS_Khazan_Run_Stop_RF`, `DAS_Khazan_Sprint_Stop` 세 시퀀스는 예외가 아니라 **의도적으로 capsule을 구동하는 Sequence Root Motion**으로 이관한다.
- 이번 결정은 RunStop 두 발 변형과 SprintStop에만 적용한다. WalkStop 두 시퀀스와 Walk/Run/Sprint 반복 이동은 현재 계약을 유지하며, 별도 근거 없이 함께 바꾸지 않는다.
- 이 프로젝트는 싱글 플레이이고 Stop은 Locomotion State Machine의 Sequence Player가 재생하므로 Main ABP의 Root Motion Mode는 `Root Motion from Everything`을 사용한다. `Montages Only`로 되돌리거나 Stop을 몽타주/GameplayAbility로 감싸지 않는다.
- 동작 경로는 `Stop Sequence -> AnimInstance root-motion extraction -> SkeletalMeshComponent -> CharacterMovementComponent -> capsule`이다. ASC, WeakAttack Ability, PlayerController, AnimInstance worker에서 위치를 직접 더하지 않는다.

### 소유권과 취소

- Stop 진입 여부와 LF/RF/Sprint 선택은 기존 Locomotion 데이터 계약이 소유한다.
- Stop 재생 중 새 이동 입력이 들어오면 기존 State Machine 전이로 WalkRun/Sprint에 복귀한다. 전이가 시작된 프레임부터 outgoing Stop의 root motion 기여도도 pose blend weight와 함께 감소하거나 종료되어야 하며, 별도 이동 버퍼나 Stop Ability를 만들지 않는다.
- Stop 종료는 해당 Sequence Player의 완료를 기준으로 Idle로 전이한다. 속도가 먼저 0이 되었다는 이유만으로 Stop을 자르지 않는다.
- Stop은 단발이며 길이와 marker 구성이 서로 다른 독립 클립이므로 반복 보행용 `Locomotion` Sync Group의 `Always Leader`로 두지 않는다. Stop Sequence Player는 `Do Not Sync`를 기본 계약으로 삼고 LF/RF 선택은 기존 `StopEntryFoot` snapshot으로 고정한다.

### 에셋 공간과 크기 계약

- source의 이동 트랙은 skeleton bone index 0인 `C_P_Kazan`에 있어야 한다. child `Root`에 이동을 남긴 채 `Enable Root Motion`만 켜는 방식은 허용하지 않는다.
- 현 skeleton의 삽입된 `C_P_Kazan` reference scale 100을 보정하는 translation 배율은 `1 / 100 = 0.01`이다. 이는 skeleton topology에서 유도된 에셋 변환값이다.
- 캐릭터 Mesh Component의 현재 임시 scale `0.009`는 에셋 전처리 입력이 아니다. 이를 역수로 보상하는 `AnimRootMotionTranslationScale`, `AddActorWorldOffset`, CMC 속도 보정은 추가하지 않는다.
- 최종 월드 이동량은 component transform과 collision을 거친 결과이므로, 에셋 공간 추출량과 PIE capsule 이동량을 분리해 검증한다.

### 상태

이 절은 이후 구현 계약을 확정한다. 2026-09-18 저장본에는 세 Stop 에셋의 Root Motion 플래그와 ABP의 `Root Motion from Everything`이 이미 있으나, 세 에셋은 기존 보호 목록 때문에 최신 skeleton-scale 보정 import를 거치지 않았다. 표적 재변환·재임포트와 PIE capsule 검증은 다음 Animation 단계에서 수행한다.

<a id="arch-48-input-end-attack-handoff-20260921"></a>
## 2026-09-21 — ARCH-48: ComboInputEnd 기반 공격 Ability handoff와 이동 입력 차단

### 현재 구현에서 즉시 Weak/Strong 전환이 발생하는 이유

- `UKhazanAbilitySystemComponent::AbilityInputTagPressed()`는 입력 태그와 정확히 일치하는 비활성 Spec을 찾으면 즉시 `TryActivateAbility()`를 호출한다.
- 현재 `GA_Player_WeakAttack`과 `GA_Player_StrongAttack`에는 서로를 막는 Ability Asset Tag / Block Abilities With Tag 계약이 없다. 따라서 Weak가 활성 중이어도 Strong의 활성화 검사가 통과하며, 같은 Slot Group의 새 Montage가 기존 Montage를 interrupt할 수 있다.
- `SetCanBeCanceled(false)`로 이 문제를 막지 않는다. 이 설정은 InputEnd 이전의 일반 공격 전환뿐 아니라 피격·사망 같은 강제 취소까지 함께 막기 때문이다.

### 공격 상호 배타와 InputEnd 개방 계약

- native `Ability.Action.Attack`을 Weak/Strong 및 이후 같은 전신 공격 Ability의 **Ability Asset Tag**로 사용한다. 이는 실행 중 캐릭터 상태가 아니라 block/cancel 검색용 Ability 분류다.
- 공통 공격 Ability의 `Block Abilities With Tag`에도 `Ability.Action.Attack`을 둔다. 공격이 시작되면 GAS가 같은 분류의 새 공격 활성화를 막는다.
- 각 section의 `ComboInputEnd` point에 도달하면 현재 Ability가 `SetShouldBlockOtherAbilities(false)`를 호출한다. UE 5.8.2의 이 API는 현재 instance가 적용한 `BlockAbilitiesWithTag` count만 해제하며, 이후 `EndAbility()`에서 같은 count를 중복 제거하지 않는다. 다음 활성화 때 `PreActivate()`가 blocking 상태를 다시 true로 초기화하므로 `InstancedPerActor` 재사용에도 누수가 없다.
- 공통 공격 Ability의 `Cancel Abilities With Tag`에도 `Ability.Action.Attack`을 둔다. InputEnd 이후 대상 공격 활성화가 실제로 성공할 때 대상이 출발 공격을 취소한다. 대상 활성화 성공 전에 출발 Ability나 Montage를 먼저 끝내지 않는다.
- 현재 외부 소비자가 없는 `State.Action.Attack`은 추가하지 않는다. Ability 분류와 이동 차단이라는 실제 두 소비 계약만 둔다.

### 반대 공격 선입력과 한 칸 handoff

- tag 차단만 추가하면 InputEnd 이전의 반대 공격 press는 활성화 실패 후 사라진다. 따라서 현재 활성 공격이 반대 공격의 semantic press를 받아 기존 `BufferedInputTag` 한 칸에 저장해야 한다.
- ASC 입력 라우터는 Spec 활성화를 시도하기 **전에** 입력 태그를 빈 non-null `FGameplayEventData`와 함께 한 번 전달한다. 활성 Combo Ability는 자신의 반복 입력은 기존 `InputPressed()`로 받고, 반대 공격 태그만 `WaitGameplayEvent`로 듣는다. 새 전역 queue나 Controller의 Ability cast를 만들지 않는다.
- `ComboInputOpen` 이전 입력은 저장하지 않는다. Open–End 사이에서 처음 승인된 입력 하나가 branch를 소유한다.
- 자기 입력은 기존 규칙을 유지한다. Open–Commit이면 Commit까지 기다렸다가 같은 Ability의 다음 section으로 Jump하고, Commit–End이면 즉시 Jump한다.
- 반대 공격 입력은 Commit에서 section Jump 대상으로 소비하지 않고 InputEnd까지 유지한다. InputEnd에서 공격 block을 해제한 뒤 ASC가 Dynamic Spec Source Tag로 대상 Spec을 찾아 활성화를 한 번 시도한다.
- 대상 활성화가 성공하면 대상의 `Cancel Abilities With Tag`가 출발 공격을 끝내고 새 Montage가 시작된다. 실패하면 출발 공격은 회수부와 자연 종료를 계속한다. buffer는 한 번 소비하며 실패 전에 출발 Montage를 정지하지 않는다.
- InputEnd 이후 새 반대 공격 press는 이미 attack block이 해제됐으므로 즉시 대상 Ability를 활성화한다. 향후 Strong hold 문법이 실제로 handoff 경계를 넘을 때만 press/release 시각 등 필요한 최소 metadata를 buffer 계약에 추가한다.

### `Block.Movement.Input`의 원래 책임과 현재 누락

- `UKhazanLocomotionComponent`는 이미 ASC의 `Block.Movement.Input` count 변경을 구독하고, count가 0이 아닐 때 `AddMovementInput()`으로 이어지는 이동 입력 출력을 차단한다.
- 현재 Weak/Strong Ability는 이 태그를 부여하지 않는다. 지금 공격 중 일반 이동이 적용되지 않는 주원인은 Root Motion Montage가 CMC의 일반 velocity 계산을 대신하기 때문이며, 태그 기반 차단이 아니다.
- 공통 공격 Ability의 `Activation Owned Tags`에 `Block.Movement.Input`을 둔다. GAS가 Activate에서 count를 더하고 정상 종료·취소·실패 cleanup의 `EndAbility()`에서 회수하므로 수동 `AddLooseGameplayTag/RemoveLooseGameplayTag` 쌍을 만들지 않는다.
- 이 태그는 CMC 자체나 Root Motion을 정지시키지 않는다. 플레이어/AI locomotion 입력이 CMC로 출력되는 것만 막는다. `ComboInputEnd` 이후 Move event가 공격을 끝내면 Activation Owned Tag가 회수되고 다음 이동 갱신부터 CMC 입력이 다시 통과한다.
- 2026-09-21 저장 Source에서는 `Input_MoveStarted()`가 비어 있고 `Input_Move()`의 `Triggered` 경로가 매 frame Move gameplay event를 보낸다. ARCH-45의 “End 이후 새 Started edge만 취소” 계약을 유지하려면 event 송신은 `Input_MoveStarted()`로 옮기고 `Input_Move()`에서는 locomotion intent와 `AddMovementInput()`만 갱신한다.

### 공통화 경계

StrongAttack이 두 번째 실제 콤보 Ability가 되었고 두 클래스가 Montage task, Notify bind/unbind, Open/Commit/End phase, buffer, 이동 취소 및 cleanup을 그대로 복제하고 있으므로 ARCH-45에서 보류했던 공통 base 추출을 지금 수행한다. 이 base는 공격 분류와 이동 차단까지 고정하므로 과거 후보명 `UKhazanComboGameplayAbility`보다 책임이 정확한 `UKhazanComboAttackAbility : UKhazanGameplayAbility`를 사용한다.

- base가 소유할 것: 공격 tag container 기본값, Montage task 수명, Notify delegate, 3상태 입력 phase, 한 칸 buffer, 반대 입력 event 대기, InputEnd handoff, 이동 event 대기, 정상/취소 cleanup, 관성화 요청과 section Jump의 공통 절차.
- 파생 Weak/Strong이 소유할 것: Montage asset, 유효 section 집합, 자기 입력과 허용 handoff 입력, 다음 node/section 해석, 해금·비용·hold 분기.
- UInterface는 실행 상태와 AbilityTask 수명을 소유할 수 없으므로 사용하지 않는다. Combo Manager, 별도 buffer component, StateTree, custom AbilityTask 또는 DataAsset graph도 이번 요구에는 추가하지 않는다.
- base에 `CurrentIndex + 1`을 고정하지 않는다. 현재 Weak/Strong은 선형이어도 이후 약→강, 강→약, hold branch는 파생 `ResolveTransition()`이 결정한다.

### 적용 상태

이번 절은 실제 Source와 로컬 UE 5.8.2 GameplayAbilities plugin 구현을 대조해 확정한 다음 공동 구현 계약이다. 게임 Source, Blueprint, Montage asset은 수정하지 않았고 cold build와 PIE도 실행하지 않았다.

<a id="arch-49-held-move-after-input-end-20260921"></a>
## 2026-09-21 — ARCH-49: 유지 중인 이동 입력의 ComboInputEnd 이후 전환

### ARCH-45/46/48 이동 edge 계약 정정

사용자 확정 동작은 `ComboInputEnd` 이후 새 Move `Started`만 받는 방식이 아니다. 공격 중부터 이동 입력을 계속 유지하고 있어도 현재 section의 `ComboInputEnd`가 지난 직후 로코모션으로 전환해야 한다. 따라서 ARCH-45의 “새 Started edge만 취소”, ARCH-46의 “Move Started에서만 이벤트 송신”, ARCH-48의 `Input_MoveStarted()` 이관 제안은 이동 입력 sampling 범위에서 이 절로 대체한다.

- `AKhazanPlayerController::Input_Move()`는 Enhanced Input의 `Triggered` 동안 현재와 같이 매 frame `Input.Action.Move` Gameplay Event를 ASC에 보낸다.
- 활성 Combo Attack Ability는 `ComboInputEnd` 전에는 이 이벤트를 받더라도 `bCanCancelToLocomotion == false`이므로 아무 상태도 저장하지 않고 무시한다.
- `ComboInputEnd`가 `bCanCancelToLocomotion = true`로 바꾼 뒤, 방향 입력을 계속 유지 중이면 다음 `Triggered` event가 즉시 현재 공격을 종료한다.
- 이는 공격 Ability 내부에 과거 이동 press를 보관하는 buffer가 아니다. Enhanced Input이 현재 유지 중인 물리 입력을 계속 보고하고, Ability는 authored gate가 열린 현재 frame의 신호만 소비한다.
- `Input_MoveStarted()`는 이번 계약에서 gameplay event 송신 위치로 사용하지 않는다. 현재 빈 구현을 `Input_Move()`로 옮기거나 Move event를 Started 전용으로 바꾸지 않는다.

### `Block.Movement.Input`과의 결합

- 공격 Ability가 활성인 동안 `ActivationOwnedTags`의 `Block.Movement.Input`은 `AKhazanPlayer::HandleInputMove()` 안에서 `AddMovementInput()`으로 가는 출력을 막는다. 같은 frame의 Controller gameplay event 송신까지 막지는 않는다.
- InputEnd 이후 유지 입력 event가 Ability를 종료하면 GAS가 `Block.Movement.Input` count를 회수한다. 다음 `Triggered` 갱신부터 같은 유지 입력이 정상적으로 `AddMovementInput()`까지 통과한다.
- 따라서 Root Motion 공격 중 CMC locomotion이 섞이지 않으면서도, 플레이어가 방향키를 떼었다 다시 누를 필요 없이 회수 허용 시점부터 이동으로 복귀한다.
- 공통 base로 이관할 callback 이름은 실제 event 의미에 맞춰 `HandleMoveInputTriggered` 또는 `HandleMoveInput`으로 둔다. 기존 `HandleMoveInputStarted`라는 이름을 새 base에 복사하지 않는다.

### 적용 상태

이번 절은 사용자가 확정한 현재 입력 의도를 문서에 반영한 것이다. `KhazanPlayerController.cpp`의 `Input_Move()` event 송신은 의도된 구현으로 보존하며, 게임 Source와 asset은 이번 기록에서 수정하지 않았다.

<a id="arch-50-minimal-ability-taxonomy-and-interruption-20260921"></a>
## 2026-09-21 — ARCH-50: 최소 Ability 태그 계층과 방향성 handoff·피격 재트리거

### 태그 계층 원칙

태그로 모든 Ability 쌍의 전환 관계를 표현하지 않는다. 태그는 여러 시스템이 실제로 함께 조회하는 **분류와 지속 상태**에만 쓰고, 현재 node에서 어떤 입력 edge를 허용하는지는 실행 중 Ability가 판정한다.

```text
Input.Action.*                 물리/의미 입력 라우팅

Ability.Action                자발적인 전신 행동의 공통 분류
└─ Ability.Action.Attack      Weak/Strong 및 이후 공격
└─ Ability.Action.UseItem     물약 등 아이템 사용

Ability.Reaction              외부 결과에 의해 강제되는 반응 분류
└─ Ability.Reaction.Hit       피격 반응

Event.Reaction.Hit            한 번 발생한 피격 문맥 전달
Block.Movement.Input          ASC가 현재 소유하는 이동 입력 차단 사실
Unlock.*                      영구/준영구 진행 조건
```

- 각 Ability의 Asset Tags에는 가장 구체적인 한 분류만 둔다. `Ability.Action.Attack`은 부모 `Ability.Action` 질의에도 계층 매칭되므로 둘을 중복 기입하지 않는다.
- 아직 실제 Ability나 소비자가 없는 `Dodge`, `Skill`, `Death`, 세부 Hit 방향 태그는 선행 생성하지 않는다. 구현될 때 위 계층 아래 필요한 leaf만 추가한다.
- `Input`, `Ability`, `Event`, `Block`, `Unlock`의 의미를 섞지 않는다. `StrongCanTransitionToWeak` 같은 pairwise 태그나 `State.Action.Attack`의 중복 사본을 만들지 않는다.

### Action 상호 배타와 방향성 handoff

- 전신 Action은 활성 중 `Block Abilities With Tag = Ability.Action`으로 다른 자발 행동의 임의 활성화를 막는다.
- 전환 대상 Action은 `Cancel Abilities With Tag = Ability.Action`으로 둔다. 단, 대상이 먼저 정상 활성화된 경우에만 기존 Action을 취소한다.
- `ComboInputEnd`는 모든 Action block을 무조건 해제하는 point가 아니다. 이 point는 현재 Ability의 `bCanExitAttack` gate만 연다.
- 현재 Ability가 `CanHandoffToInput(InputTag, CurrentNode)`에서 허용한 요청에 대해서만 `SetShouldBlockOtherAbilities(false)` 후 대상 활성화를 시도한다. 활성화가 실패하고 출발 Ability가 여전히 활성이라면 `SetShouldBlockOtherAbilities(true)`로 count를 복구한다.
- Weak→Strong을 허용하고 Strong→Weak을 금지하려면 Weak의 resolver만 Strong input을 승인하고 Strong resolver는 Weak input을 거부한다. 이 방향성은 Ability 실행 규칙이며 새 Gameplay Tag가 아니다.
- InputEnd 전에 들어온 허용 입력은 기존 one-slot buffer에 보관했다가 InputEnd에서 handoff한다. InputEnd 이후 새 입력은 현재 Ability가 즉시 같은 resolver로 판정한다. 금지된 입력은 저장·활성화·차단 해제를 모두 하지 않는다.
- 이 결정은 ARCH-48의 “InputEnd에서 항상 `SetShouldBlockOtherAbilities(false)`”를 대체한다.

### ASC 입력 전달 순서 정정

방향성 gate를 현재 Ability가 소유하므로 공격 입력의 Gameplay Event는 직접 Spec 처리를 마친 뒤 전달한다.

```text
입력 대상 Spec 처리
  비활성·허용: 평소처럼 활성화
  비활성·현재 Action block: 활성화 실패
  활성: 기존 InputPressed 전달
        ↓
HandleGameplayEvent(InputTag)
        ↓
현재 실행 Ability가 buffer/handoff 허용 여부 판정
```

- idle에서 새 Ability가 먼저 활성화돼도 그 Ability는 자기 입력 이벤트를 기다리지 않고 반대 handoff 입력만 기다리므로 중복 소비가 없다.
- active Action 때문에 대상 활성화가 실패한 뒤 event가 현재 Action에 도달하므로, 현재 Action이 방향성과 authored gate를 판정할 수 있다.
- InputEnd 이후 허용 handoff라면 event callback에서 block을 잠시 해제하고 `TryActivateAbilityByInputTag()`를 호출한다. ASC의 원래 Spec 순회가 이미 끝났으므로 새 대상의 최초 press를 `InputPressed()`로 다시 전달하지 않는다.
- `TryActivateAbilityByInputTag()`의 `AbilitySpec.IsActive()` 제외는 유지한다. 이 helper는 비활성 입력 Ability로 handoff하기 위한 API이며 피격 재트리거 경로가 아니다.

### 피격 Ability의 반복 재생

- HitReaction은 `InstancedPerActor`와 UE native `bRetriggerInstancedAbility = true`를 사용한다.
- 피해 확정 경로는 `Event.Reaction.Hit` Gameplay Event를 대상 ASC에 보낸다. 같은 HitReaction Spec이 이미 활성이라도 엔진은 기존 instance의 `EndAbility()` cleanup을 수행한 뒤 같은 Spec을 새 activation으로 시작한다. 겹치는 두 instance를 유지하지 않고 Montage를 처음부터 다시 재생한다.
- HitReaction Asset Tag는 `Ability.Reaction.Hit`이다. `Block Abilities With Tag`와 `Cancel Abilities With Tag`는 현재 수직 절편에서 `Ability.Action`을 사용한다.
- HitReaction이 `Ability.Reaction.Hit` 또는 부모 `Ability.Reaction`을 block하면 `CanActivateAbility()`가 retrigger 분기보다 먼저 실패할 수 있으므로 자기 reaction 분류를 block하지 않는다.
- HitReaction에 `SetCanBeCanceled(false)`를 사용하지 않는다. 사망·더 높은 우선순위 반응과 cleanup 경로를 막지 않아야 한다.

### 물약과 피격의 결합

- Potion Ability는 `Ability.Action.UseItem`으로 분류한다. Action 계층이므로 다른 자발 Action과 상호 배타 정책을 공유하지만 `Ability.Reaction.Hit`을 막지 않는다.
- 피격이 발생하면 체력 피해 계산과 HitReaction 활성화는 별도 계약이다. HitReaction이 정상 활성화되면 `Cancel Abilities With Tag = Ability.Action`이 Potion Ability를 종료하고, Potion의 `PlayMontageAndWait` cleanup이 사용 모션을 중지한 뒤 Hit Montage가 시작된다.
- 물약 회복 적용 시점은 Potion Ability의 별도 commit point가 소유한다. 피격이 그 point 전에 Potion을 취소하면 회복을 적용하지 않고, 이미 commit된 회복을 단순 Montage 취소로 되돌리지 않는다.
- 향후 SuperArmor처럼 HitReaction은 억제하지만 Action 중단은 필요한 판정이 실제로 생기면 확정된 CombatResponse 결과가 Action cancel을 별도로 요청한다. 모든 피해에 무조건 cancel을 넣거나 이번 단계에 예외 태그를 선행 생성하지 않는다.

### 현재 구현 확인과 다음 이관

- `UKhazanAbilitySystemComponent::TryActivateAbilityByInputTag()`가 active Spec을 제외하는 현재 코드는 의도에 맞다.
- 2026-09-21 저장 Source의 `KhazanGameplayTags.cpp`는 `Ability_Action_Attack`에 `UE_DECLARE_GAMEPLAY_TAG_EXTERN`을 한 번 더 사용했다. cpp에서는 `UE_DEFINE_GAMEPLAY_TAG(Ability_Action_Attack, "Ability.Action.Attack")`이어야 하며, 공통 attack base가 이 태그를 참조하기 전에 바로잡는다.
- 다음 공동 구현은 `(1)` 위 tag 정의 수정 및 실제 소비용 부모 `Ability.Action` 추가, `(2)` ASC input event를 Spec 처리 뒤로 이동, `(3)` `UKhazanComboAttackAbility` 추출, `(4)` Weak만 Strong handoff를 승인하고 Strong은 Weak handoff를 거부, `(5)` Action/Movement block count와 실패 복구를 PIE에서 검증하는 순서다.

### 적용 상태

이번 절은 사용자 요구와 로컬 UE 5.8.2 `InternalTryActivateAbility()`·`ApplyAbilityBlockAndCancelTags()` 구현을 근거로 아키텍처를 정정한 것이다. 문서만 추가했으며 게임 Source, Blueprint, Montage는 수정하지 않았다. HitReaction과 Potion Ability는 아직 구현 완료 상태로 기록하지 않는다.

<a id="arch-51-authored-combo-graph-and-semantic-input-phase-20260921"></a>
## 2026-09-21 — ARCH-51: 다분기 콤보의 노드 그래프와 의미 입력 phase 계약

### 기존 handoff안의 적용 한계와 유지할 경계

- `Y 연타`, `Y → 다음 Y 유지 → X`, press/release에 따른 charge 분기처럼 실제 조합이 다양하다는 요구가 확인됐으므로, ARCH-37에서 보류했던 읽기 전용 Combo Definition의 도입 조건이 충족됐다.
- ARCH-50의 `Ability.Action` 상호 배타, 현재 실행 Ability가 전환을 승인한다는 원칙, 피격의 별도 retrigger 경로는 유지한다. 다만 공격 키 press만 `HandleGameplayEvent(InputTag)`로 보내는 계약은 다른 키의 release/cancel 및 hold 상태를 보존하지 못하므로 공격 콤보 입력 전달 범위에서 이 절로 대체한다.
- 입력 문자열 하나나 입력 순서 하나마다 GameplayAbility를 만들지 않는다. 현재 콤보 node가 이미 이전 입력의 결과를 나타내며, active Attack Ability 하나가 해당 실행의 node·입력 상태·window·pending edge·Montage 수명을 함께 소유한다.
- 다른 GameplayAbility로 handoff하는 것은 비용·쿨다운·취소 정책·실행 수명의 소유자가 실제로 달라지는 edge에만 사용한다. 같은 공격 실행 안의 tap/hold/release 및 약·강 혼합 분기는 우선 같은 Ability의 node/section 또는 명시된 Montage 전환으로 처리한다.

### 입력 phase는 태그 계층이 아니라 작은 값 타입으로 전달

- `Input.Action.WeakAttack`과 `Input.Action.StrongAttack`은 의미 입력 tag로 유지한다. `Pressed`, `Released`, `Canceled`를 각 입력 아래 Gameplay Tag로 증식시키지 않는다.
- ASC 경계에 `EKhazanAbilityInputPhase { Pressed, Released, Canceled }`와 `{ InputTag, Phase }` 한 건을 나타내는 값 타입을 둔다. Controller는 Enhanced Input의 `Started/Completed/Canceled`를 이 세 phase로 번역하고, ASC는 기존 Spec `InputPressed` 및 GAS generic replicated input protocol을 수행한 뒤 의미 입력 알림을 방송한다.
- 활성 Combo Attack Ability는 이 ASC 알림을 activation에서 구독하고 `EndAbility()`에서 해제한다. 자기 입력과 다른 공격 입력을 같은 callback에서 받되, 한 물리 edge를 generic input task와 의미 입력 callback 양쪽에서 중복 소비하지 않는다. 콤보 base는 의미 입력 callback을 권위 경로로 사용하고 generic protocol은 GAS 호환을 위해 유지한다.
- `Completed`는 정상 release edge이고 `Canceled`는 입력 평가 취소/Mapping Context 상실 cleanup이다. 둘 다 Spec의 `InputPressed`는 false로 만들지만, `Canceled`를 charge release 공격으로 소비하지 않는다. 현재 Controller가 두 경우를 모두 `AbilityInputTagReleased()`로 보내는 구현은 charge 구현 전에 분리한다.
- Gameplay Event는 `Event.Reaction.Hit`처럼 gameplay 문맥과 payload를 전달하거나 Montage authored event를 AbilityTask가 기다리는 용도로 유지한다. 물리 입력의 모든 phase를 표현하기 위한 중복 tag 사전으로 사용하지 않는다.

### Hold는 임의 시간 임계값이 아니라 입력 수명과 authored charge event의 결합

- press에서 해당 의미 입력을 held 집합에 넣고 정상 release/cancel에서 제거한다. `Ongoing`을 매 frame 콤보 명령으로 제출하거나 Controller timer 하나로 tap/hold를 확정하지 않는다.
- 원작 `StrongAtk01_Start/Charge` metadata에는 `Released` 검사 구간과 `xxSetChargingStepFunc`/`DoChangeCharageStep`가 있으므로, Strong Ability는 Montage의 release 허용 window와 charge-step authored event를 권위 경계로 사용한다.
- charge-step event가 도착했을 때 Strong 입력이 아직 held이면 charge node로 진행하고, 그 전에 정상 release가 합법 window에서 들어오면 release edge를 선택한다. `Canceled`는 공격 edge를 선택하지 않고 현재 pending/held 상태를 정리한다.
- 이후 원작에서 animation event와 독립된 실제 시간 임계값이 직접 확인될 때만 그 값을 Combo Definition의 명시적 설정으로 추가한다. 현재 단계에서는 임의 hold 초를 만들지 않는다.

### 최소 읽기 전용 Combo Definition

- node id는 `FName`을 사용한다. `Strong01`, `Strong01Charge`, `Strong01Release`, `MixedWeakAfterCharge` 같은 node 식별자를 Gameplay Tag로 만들지 않는다.
- node는 재생할 Montage/section 또는 현재 Ability가 해석할 presentation 참조와 outgoing edge 목록을 가진다.
- edge는 최소한 의미 `InputTag`, `InputPhase` 또는 authored event, 필요한 window/held 조건, 요구·차단 owner tag, target node, 실행 방식(`WithinAbility` 또는 실제 수명 변경이 있는 `AbilityHandoff`)을 가진다.
- runtime current node, held input, 한 건 pending edge, window depth, transition committed, stamina/target 결과는 DataAsset에 저장하지 않는다. 모두 active Ability instance의 transient 상태다.
- 현재 node마다 pending 입력은 한 건만 둔다. node가 바뀌면 slot을 비우므로 빠른 연타 전체를 미래 여러 타수에 FIFO로 보존하지 않는다. 정확한 overwrite/priority는 원작 branch 자료가 확인되기 전까지 기존 `first accepted valid edge wins` 계약을 유지한다.
- 범용 graph editor, StateTree, 전역 ComboManager, 모든 Ability가 공유하는 입력 이력 Component는 만들지 않는다. plain DataAsset과 Combo Attack base의 작은 resolver로 시작한다.

### `Y → Y Hold → X` 실행 예

```text
Y Started
  -> StrongAttack Ability 활성화
  -> current node = Strong01
  -> held = { Strong }

Y Completed
  -> 현재 node의 Released edge가 합법하면 tap/release 공격으로 진행

또는 다음 Y Started
  -> current node의 Strong+Pressed edge를 한 건 예약
  -> authored commit에서 Strong01Charge로 전환
  -> held에 Strong 유지

ChargeStep authored event
  -> Strong이 아직 held이면 charge step/node 진행

X Started
  -> 별도 Weak Ability의 임의 활성화는 Ability.Action block으로 실패
  -> active Strong execution이 Weak+Pressed edge를 조회
  -> 정의가 WithinAbility이면 혼합 target node/section으로 전환
  -> 정의가 실제 AbilityHandoff이면 해당 edge가 허용한 시점에만 block을 잠시 풀고 대상 Ability 활성화
```

이 구조에서 과거 입력 배열을 계속 저장할 필요가 없다. `Strong01Charge`라는 current node 자체가 `Y로 시작했고 다음 Y가 charge 경로로 소비됐다`는 축약된 이력이며, X는 그 node의 outgoing edge만 조회한다.

### 2026-09-21 저장 Source의 실제 차이와 다음 순서

- 저장 Source에는 `UKhazanComboAttackAbility`가 아직 없고 Weak/Strong은 각각 `UKhazanGameplayAbility`를 직접 상속한다.
- `AbilityInputTagPressed()`는 여전히 Gameplay Event를 Spec 순회 전에 전송한다. ARCH-50에서 확정한 event-after-spec 순서도 아직 반영되지 않았다.
- Controller의 attack `Completed`와 `Canceled`는 모두 `AbilityInputTagReleased()`로 들어가 phase 의미가 소실된다.
- 따라서 다음 구현은 `(1)` ASC의 `{InputTag, Phase}` 의미 입력 계약과 cancel 경로, `(2)` Combo Definition의 최소 node/edge 타입, `(3)` 실제 공통 상태가 생긴 `UKhazanComboAttackAbility`, `(4)` Strong의 press/release/charge vertical slice, `(5)` 그 위에 첫 혼합 X edge를 추가하는 순서다. HitReaction/Potion retrigger·cancel 규칙은 이 공격 입력 그래프와 합치지 않는다.

### 적용 상태

이번 절은 복합 콤보 요구에 따라 아키텍처 계약을 보완한 기록이다. 게임 Source, Blueprint, Montage, DataAsset은 수정하지 않았고 Combo Definition 및 phase delegate의 빌드·PIE 검증도 아직 수행하지 않았다.

<a id="arch-52-combo-rule-ownership-20260921"></a>
## 2026-09-21 — ARCH-52: 콤보 규칙 원본과 실행 Ability의 책임 분리

### 결론

다수의 키 조합과 모든 전환 규칙을 각 GameplayAbility의 C++ 분기로 직접 작성하지 않는다. 정적 콤보 topology와 edge 조건은 읽기 전용 `UKhazanComboDefinitionData`가 소유하고, 현재 활성 Combo Attack Ability는 그 정의를 해석하여 현재 실행 한 건의 전이 가능 여부를 최종 판정하고 실행한다. Ability는 규칙 데이터베이스가 아니라 GAS 수명·비용·취소·Montage와 runtime state를 결합하는 실행 권위다.

### 책임 경계

- Enhanced Input/Controller: `Started`, `Completed`, `Canceled`를 의미 입력 tag와 phase로 번역한다. 조합 이력이나 콤보 tree를 소유하지 않는다.
- ASC: Spec 입력 protocol과 의미 입력 방송, Ability 활성화·차단을 담당한다. 입력 FIFO나 현재 combo node를 소유하지 않는다.
- Combo Definition DataAsset: node id, node가 재생할 Montage/section, 현재 node에서 가능한 input/authored-event edge, held-input 요구, owner-tag 요구, target node를 저장한다. 현재 node, buffer, held 상태나 Ability/Task 포인터는 저장하지 않는다.
- active Combo Attack Ability: current node, held inputs, 한 건 pending edge, Open/Commit/End gate, Montage task와 delegate handle을 소유한다. Definition의 edge와 현재 ASC 상태를 대조하고 성공한 transition만 commit한다.
- GAS tags/effects: 사망·피격·행동 상호 배타처럼 combo graph 밖의 공유 gameplay 상태와 전역 활성화/취소 정책을 소유한다. unlock처럼 특정 edge가 요구하는 상태는 edge의 owner-tag requirement로 조회하되 태그를 DataAsset이나 Ability가 임의 부여하지 않는다.
- Montage authored points: 입력을 받을 시점과 commit/회수 종료, charge step처럼 애니메이션이 정하는 시간 경계를 소유한다. DataAsset에 frame time을 복제하지 않는다.

### Ability 경계

- 한 connected attack chain은 한 active Ability 실행으로 유지한다. Weak/Strong 입력이 섞여도 같은 비용·취소·실행 수명 안의 분기라면 node 또는 Montage를 전환하고 Ability handoff를 만들지 않는다.
- Weak 시작과 Strong 시작 Ability는 같은 Combo Definition을 참조하고 서로 다른 entry node만 가질 수 있다. 어느 쪽으로 시작했는지는 Ability class 이름보다 runtime current node가 정확히 표현한다.
- 별도 cooldown, 독립 cost commit, 다른 취소 정책이나 별도 실행 결과를 가진 실제 Skill로 넘어갈 때만 다른 Ability로 handoff한다. 단순히 입력 tag가 달라졌다는 이유로 Ability를 교체하지 않는다.

### 최소 데이터 모델

- node: `NodeId`, `Montage`, `MontageSectionName`, `InputEdges`, `AuthoredEventEdges`.
- input edge: `InputTag`, `InputPhase`, `RequiredHeldInputs`, 엔진 `FGameplayTagRequirements`, `TargetNodeId`.
- authored-event edge: `EventName`, `RequiredHeldInputs`, `FGameplayTagRequirements`, `TargetNodeId`.
- 배열 순서를 동일 trigger의 우선순위로 사용하고, node/edge 수가 실제 병목으로 측정되기 전에는 runtime map/cache를 추가하지 않는다.
- 범용 graph editor, StateTree, Enhanced Input Combo Trigger, 전역 ComboManager, 조합 문자열별 Ability class는 채택하지 않는다. `UDataAsset`, Montage authored point, GAS tag requirement와 active Ability의 작은 resolver로 구현한다.

### 적용 상태

이 절은 ARCH-51의 책임을 구체화한 설계 결정이다. 게임 Source와 asset은 수정하지 않았으며 `UKhazanComboDefinitionData`와 공통 Combo Attack Ability는 아직 구현되지 않았다.

<a id="arch-53-source-neutral-combo-command-20260921"></a>
## 2026-09-21 — ARCH-53: Player/AI 공통 source-neutral Combo Command

### ARCH-51/52 정정

Player의 `Pressed/Released/Canceled`를 Combo Definition의 공통 edge 계약으로 직접 사용하면 AI가 물리 키를 흉내 내야 한다. 이는 미래 AI가 Ability를 요청하고 Player/AI가 같은 실행 Ability를 공유한다는 ARCH-36의 경계와 충돌한다. 따라서 ARCH-51의 `InputPhase` edge와 ARCH-52의 `InputEdges`는 공통 Combo Definition 범위에서 이 절로 대체한다.

`EKhazanAbilityInputPhase`를 `AKhazanPlayerController` 내부 타입으로 옮기지 않는다. 그렇게 하면 ASC·Combo Definition·AI가 PlayerController 선언에 의존한다. PlayerController의 세 Enhanced Input callback 자체가 물리 phase를 이미 표현하므로 별도 공유 input-phase enum은 입력 adapter 완료 뒤 필요하지 않다.

### 두 경로의 분리

1. **GAS Player input protocol:** `AbilityInputTagPressed/Released/Canceled`는 Player 입력에 대해 granted Spec의 `InputPressed`, `UGameplayAbility::InputPressed/Released`, generic replicated input task 경로만 처리한다. AI가 이 함수를 호출해 키를 흉내 내지 않는다.
2. **공통 Combo Command:** `FKhazanComboCommand { CommandTag, Phase }`를 ASC의 native event로 방송한다. phase는 source-neutral `Begin`, `Release`, `Cancel`이며 PlayerController와 AI 의도 생산자가 같은 API로 제출한다.

최소 command tag는 `Command.Attack.Weak`과 `Command.Attack.Strong` 두 개다. `Input.Action.*`는 Player 장치/Spec routing, `Command.Attack.*`는 Player·AI 공통 공격 의도, `Ability.Action.Attack`은 실행 Ability 분류라는 서로 다른 의미를 가진다. phase마다 GameplayTag를 늘리지 않는다.

### Player와 AI 흐름

```text
Player Enhanced Input Started
  -> ASC AbilityInputTagPressed(Input.Action.StrongAttack)
  -> ASC SubmitComboCommand(Command.Attack.Strong, Begin)

AI decision
  -> 선택한 Attack Ability Spec 활성화
  -> ASC SubmitComboCommand(Command.Attack.Strong, Begin)

Player Completed 또는 AI의 charge release 결정
  -> ASC SubmitComboCommand(Command.Attack.Strong, Release)
```

PlayerController는 물리 입력을 command로 번역하는 adapter다. AIController/BT/StateTree task는 Enhanced Input이나 PlayerController를 경유하지 않고 같은 ASC command API를 직접 호출한다. AI 판단 계층은 정확한 Montage frame, buffer와 section jump를 관리하지 않으며 원하는 공격 command만 제출한다.

### 공통 Combo Attack Ability

- activation에서 ASC command event를 구독하고 `EndAbility()`에서 delegate handle을 해제한다.
- `Begin`은 command를 held set에 넣고 현재 node의 command edge를 제출한다. `Release`는 held에서 제거하면서 release edge를 제출하고, `Cancel`은 held/pending 상태만 정리하여 공격 edge를 실행하지 않는다.
- current node, one-slot pending edge, Open/Commit/End gate, Montage task와 cleanup은 active Ability instance가 소유한다.
- command가 없어도 Montage authored event edge는 자동 전환할 수 있다. 따라서 AI의 자동 연속 동작과 charge step도 물리 입력 없이 실행 가능하다.
- Weak/Strong의 입력 조합이 같은 공격 실행 수명을 공유하면 동일 Ability 실행 안에서 node/Montage를 전환한다. 별도 Skill 수명으로 넘어갈 때만 Ability handoff를 사용한다.

### Combo Definition 정정

- `InputEdges`를 `CommandEdges`로 바꾼다.
- command edge는 `CommandTag`, `CommandPhase`, `RequiredHeldCommands`, `OwnerTagRequirements`, `TargetNodeId`를 가진다.
- authored-event edge는 그대로 유지한다. Player/AI source, Controller 포인터, input key, Spec handle, runtime held/buffer는 DataAsset에 저장하지 않는다.

### 적용 상태와 다음 순서

현재 Source의 `EKhazanAbilityInputPhase`/`FKhazanAbilityInputEvent`/ASC input event는 P6-D1 Player 경로로 구현됐으나 아직 소비자가 없다. 다음 단계는 이를 공통 Combo Command event로 교체한 뒤 cold build하는 것이다. 그 다음에만 command edge 기반 Combo Definition을 만들고, 실제 소비와 함께 `UKhazanComboAttackAbility`를 추출한다. 게임 Source와 asset은 이 문서 기록에서 수정하지 않았다.

<a id="arch-54-command-consumer-vertical-slice-20260921"></a>
## 2026-09-21 — ARCH-54: Combo Command 적용 감사와 소비자 수직 이관

### 저장 Source에서 확인된 현재 상태

- `EKhazanComboCommandPhase`, `FKhazanComboCommand`, ASC의 `SubmitComboCommand()`/native event, Controller의 `Started`/`Completed`/`Canceled` 변환은 Source에 적용됐다.
- UBT 실행은 성공했으나 target이 `up to date`였으므로 이번 확인은 새 cold compile을 수행한 결과로 기록하지 않는다.
- ASC command event를 구독하는 코드는 아직 없다. Weak/Strong 연타를 실제로 처리하는 경로는 계속 각 클래스의 `InputPressed()`와 `SubmitComboInput()`이다. 새 command 경로가 현재 동작을 만들었다고 해석하지 않는다.
- Weak/Strong은 PlayerAbility 폴더로 이동했지만 Montage task, notify bind/unbind, Open/Commit/End gate, one-slot buffer, 이동 복귀 및 cleanup을 거의 전부 복제한다. 두 번째 실제 소비자가 이미 있으므로 공통 attack base 추출 조건이 충족됐다.
- native 이름과 문자열 `Command_Player_Attack_*` / `Command.Player.Attack.*`는 Player와 AI가 함께 제출한다는 계약과 충돌한다. 실제 graph나 asset이 이 임시 tag를 저장하기 전에 `Command_Attack_Weak/Strong` / `Command.Attack.Weak/Strong`으로 정정한다.
- `KhazanComboTypes.cpp`는 0 byte이고 header 밖 구현이 없으므로 유지할 책임이 없다. 타입을 header-only로 둘 동안 삭제한다.

### 다음 단계는 유휴 schema가 아닌 하나의 수직 기능으로 진행

1. Controller가 같은 ASC를 한 번 얻어 Player Spec input protocol을 먼저 처리하고 이어서 source-neutral command를 제출한다. 세 개의 단순 forwarding helper는 제거한다.
2. plain `UDataAsset`에 `NodeId`, `Montage`, `SectionName`, `CommandEdges`만 둔다. edge는 command tag/phase, required held commands, owner tag requirements, target node만 가진다. runtime state, Controller, Spec handle, Task, buffer를 저장하지 않는다.
3. `UKhazanComboAttackAbility`가 ASC command event를 실제 구독하고 Montage/notify/one-slot pending transition/held commands/이동 복귀/cleanup을 소유한다. `InputPressed()`와 command event를 동시에 콤보 입력으로 소비하지 않는다.
4. Weak와 Strong의 현재 선형 회귀를 같은 base와 Definition으로 먼저 이관한다. `Weak04 -> Weak05` edge의 owner requirement에 `Unlock.Skill.DAS.WeakAttack05`를 둔다.
5. 두 Blueprint가 새 base 경로로 저장되고 PIE 회귀가 끝난 뒤에만 동작 없는 native Weak/Strong wrapper를 제거한다. Blueprint reparent 전에 class 파일부터 삭제하지 않는다.

### 이번 최소형에서 의도적으로 보류하는 것

- authored charge event edge, Begin/Release 교체 우선순위, 서로 다른 Montage 사이의 task handoff, 실제 별도 Skill Ability handoff는 현재 선형 Weak/Strong 회귀 뒤 각각 실제 사례와 함께 추가한다.
- 첫 수직 절편은 같은 Montage 안의 section jump만 commit한다. node에 Montage 참조를 두어 entry는 서로 다른 Montage를 사용할 수 있지만, cross-Montage edge는 해당 task 수명과 blend를 검증하기 전 asset에 만들지 않는다.
- 범용 graph editor, command history FIFO, ComboManager, Controller/AI별 graph, phase gameplay tag는 만들지 않는다.

### 공통/전용 폴더 경계

- `Ability/Command`의 command 계약, `Ability/Combo`의 Definition과 ComboAttackAbility는 Player/AI 공통이다.
- Player 전용 GameplayAbility Blueprint와 그 Definition asset은 Player 콘텐츠 폴더에 둘 수 있다. 폴더가 Player 전용이라는 사실과 C++ 실행 계약이 PlayerController에 의존하는 것은 서로 다른 문제다.

이번 절은 저장 Source 정적 감사와 다음 이관 계약이다. 게임 Source와 asset은 수정하지 않았고, 문서만 추가했다.

<a id="arch-55-family-specific-command-and-standalone-policy-20260921"></a>
## 2026-09-21 — ARCH-55: Player/AI Monster 공격 어휘 분리와 Standalone 실행 정책 정정

### Player/AI 공통성의 정확한 범위

- ARCH-53/54에서 `Command.Player.Attack.*`를 Player와 AI가 함께 제출한다는 이유로 `Command.Attack.*`로 바꾸려 한 제안은 철회한다. 현재 `Command.Player.Attack.Weak/Strong`과 native 심볼 `Command_Player_Attack_Weak/Strong`을 유지한다.
- Player와 AI Monster가 공유하는 것은 `FKhazanComboCommand`, ASC의 `SubmitComboCommand()` API, `UKhazanComboAttackAbility`의 실행 알고리즘이다. 공격 목록, GameplayAbility asset, Combo Definition, node topology와 command tag 어휘까지 같아야 한다는 뜻이 아니다.
- Player Definition은 `Command.Player.*`를 사용한다. AI Monster는 첫 실제 소비자를 구현할 때 별도 `Command.AIMonster.*` 계층과 해당 Monster의 Ability/Combo Definition을 추가한다. AI 종류가 여러 개라는 이유만으로 사용되지 않는 세부 tag를 선행 생성하지 않는다.
- 공통 Combo Ability는 특정 Player command를 C++에 하드코딩하지 않고 현재 Definition의 edge를 해석한다. 따라서 같은 C++ 실행기를 사용하면서 Player와 각 AI Monster가 전혀 다른 공격·스킬·애니메이션을 가질 수 있다.

### 일반 Ability 입력과 Combo Command를 분리한다

- `UKhazanAbilitySystemComponent::AbilityInputTagPressed/Released/Canceled()`는 공격 전용 API가 아니다. 물약, 회피, 상호작용과 이후 추가될 단발성 Ability를 포함하여 Player 입력을 granted Spec에 전달하는 일반 GAS 입력 경로로 유지한다.
- `AKhazanPlayerController::RouteAttackInput()`은 콤보 공격 callback에서만 사용한다. 같은 ASC를 한 번 얻고 일반 Spec 입력 처리를 먼저 수행한 뒤, 공격에 필요한 `SubmitComboCommand()`를 추가 호출한다.
- Combo command가 필요 없는 Ability는 `RouteAttackInput()`을 거치지 않고 `AbilityInputTagPressed/Released/Canceled()`만 호출한다. 모든 Player 행동을 Combo Definition이나 command graph로 밀어 넣지 않는다.
- AI Controller/BT는 Player input protocol을 호출하지 않는다. 자신에게 부여된 AI Ability Spec을 선택·활성화하고, 콤보 실행에 필요한 경우에만 AI 전용 command를 같은 `SubmitComboCommand()` API로 제출한다.

### Standalone NetExecutionPolicy

- 이 프로젝트는 멀티플레이를 지원하지 않는 Standalone 게임이다. 공통 Combo Attack Ability의 `NetExecutionPolicy`는 `LocalOnly`로 명시한다.
- 기존 Weak/Strong의 `ServerOnly`는 Standalone Actor가 Authority이기 때문에 실행됐던 것이며, 전용 서버가 필요하다는 뜻은 아니었다. 다만 제품 의도와 다른 정책명이므로 공통 base로 이관하면서 제거한다.
- 해당 대입을 단순 삭제하면 enum 기본값인 `LocalPredicted`가 남으므로 삭제만 하지 않는다. `InstancedPerActor`와 `LocalOnly`를 생성자에서 각각 명시한다. Standalone에서는 PlayerController와 AIController가 모두 local controller로 판정되므로 Player/AI 공통 base 사용과 충돌하지 않는다.

### ComboInputEnd의 실행 경계

- `ComboInputOpen`부터 `ComboInputEnd` 전까지 들어온 공격 command는 현재 활성 Combo Ability가 Definition edge로 판정한다. 이 구간의 Weak/Strong 조합을 새 Ability의 임의 활성화에 맡기지 않는다.
- `ComboInputEnd`는 해당 section의 콤보 분기 구간이 끝나고 회수부에서 다른 자발 Action으로 나갈 수 있는 지점이다. 이 point에서 pending command를 비우고 이동 종료 gate를 열며 `SetShouldBlockOtherAbilities(false)`로 현재 Ability가 적용한 `Ability.Action` block을 해제한다.
- 이후 새 Action이 실제 활성화되면 그 Ability의 cancel policy 또는 같은 Slot montage interrupt가 기존 공격을 종료한다. 아무 입력도 없으면 기존 공격은 회수 모션을 끝까지 재생하고 자연 종료한다.
- 다음 section으로의 정상 콤보 전이는 `ComboInputEnd` 전에 commit되므로 section jump 직전과 새 section의 `ComboInputOpen`에서는 block 상태를 유지한다.

### 상속과 접근 지정자

- `ActivateAbility()`와 `EndAbility()`는 엔진이 호출하고 파생형이 명시적으로 확장할 가능성이 있는 lifecycle override이므로 `protected`에 둔다.
- montage callback, command resolver, pending commit, node transition, delegate bind/unbind와 runtime reset은 공통 base의 불변식을 구성한다. 빈 Weak/Strong migration shim이 호출하거나 재정의할 지점이 아니므로 `private`에 둔다.
- 상속한다는 이유만으로 기존 구현 전체를 `protected`로 노출하지 않는다. 실제 charge authored event나 cross-Montage 전환에서 파생형 차이가 생길 때, 그 한 책임만 좁은 `protected virtual` hook으로 추가한다.
- `ComboDefinition`과 `EntryNodeId`는 Blueprint CDO의 Defaults에서 설정하는 읽기 전용 구성값이다. 파생 C++ 코드가 실행 중 직접 바꾸지 않도록 private `EditDefaultsOnly`로 유지한다.

이 절은 ARCH-53/54의 command semantic rename과 Player/AI 동일 command 어휘 가정을 대체한다. 게임 Source와 asset은 이 기록에서 수정하지 않았다.

<a id="character-architecture-arch-56"></a>
## 2026-09-22 — ARCH-56: 논리 조작 Command와 trigger·held 조건 분리

### Command 식별자의 의미

- Player Combo Command는 결과 공격명(`Weak`, `Strong`)이나 특정 장치의 물리 키명(`X`, `Y`, `LMB`, `RMB`)이 아니라 Player 전투 조작 슬롯을 나타낸다. 채택 명칭은 `Command.Player.Attack.Primary`, `Command.Player.Attack.Secondary`다.
- Enhanced Input이 Gamepad 버튼·마우스·키보드·사용자 재바인딩을 Input Action에 매핑하고, PlayerController가 그 Action을 위 논리 Command로 번역한다. 화면의 버튼 글리프는 Enhanced Input 매핑에서 조회하며 Gameplay Tag 문자열에서 유추하지 않는다.
- 현재 node와 Definition edge가 같은 Primary/Secondary 조작의 실제 결과를 결정한다. 따라서 같은 Primary가 현재 node에 따라 약공 연계, 차지 뒤 혼합 연계, 다른 무기 연계로 이어질 수 있다. 결과 공격명은 node/Ability/section의 책임이다.
- `Command.Player.*`와 `Command.AIMonster.*`의 family 분리는 ARCH-55대로 유지한다. AI는 물리 키를 흉내 내지 않으며 자기 Definition의 command 어휘를 `SubmitComboCommand()`에 제출한다.
- 현재 `Command.Player.Attack.Weak/Strong`을 Primary/Secondary로 바꾸는 것은 native 심볼, tag 문자열, Controller 전달값과 이미 저장된 Combo Definition 참조를 함께 확인해야 하는 semantic migration이다. 이 기록만으로 Source나 asset을 수정하지 않는다. `Input.Action.WeakAttack/StrongAttack`까지 바꿀지는 별도 판정한다. 해당 Input Tag가 초기 Ability 진입의 의미 이름이면 유지할 수 있고, 장치 독립 조작 슬롯을 뜻한다면 `Input.Action.Attack.Primary/Secondary`로 함께 정렬한다.

### `CommandPhase`와 `RequiredHeldCommands`는 서로 다른 축이다

- `EKhazanComboCommandPhase`는 한 시점에 발생한 trigger event다. `Begin`은 누르기/의도 시작, `Release`는 정상 해제와 release edge 평가, `Cancel`은 입력 문맥 상실·계획 취소·빙의 변경에서 공격 edge 없이 정리한다.
- `RequiredHeldCommands`는 trigger가 발생한 순간에도 계속 유지 중이어야 하는 command 상태 조건이다. 예를 들어 Secondary를 유지한 채 Primary를 새로 누르는 분기는 trigger `{ Primary, Begin }`, condition `{ Secondary held }`로 표현한다.
- `Hold`를 phase로 추가해도 위 분기를 대체할 수 없다. `Secondary Hold`는 Primary가 방금 눌렸다는 사실을 표현하지 못하고, 매 frame 보내면 중복 transition·buffer 오염이 생기며, 임계 도달 때 한 번만 보내면 그 임계값과 시간 소유자가 다시 필요하다.
- 단일 버튼 차지는 `Begin`에서 held에 추가하고, Montage가 정한 charge-step authored point에서 현재 held 여부를 검사하며, `Release` edge가 현재 charge node의 해제 공격을 선택하는 방식으로 확장한다. 이때 단순 release edge의 `RequiredHeldCommands`에는 방금 놓은 자기 command를 넣지 않는다. Release 처리에서 Begin 존재를 검증한 뒤 자기 tag를 held에서 제거하므로 이 컨테이너는 해제 후에도 남아 있어야 하는 다른 command 조건을 뜻한다.
- 정말로 animation timing과 독립된 “홀드 임계 도달” 사건이 필요한 실제 소비자가 생기면 `Hold`라는 연속 phase 대신 의미가 분명한 one-shot authored/runtime event를 별도 edge 종류로 추가한다. 현재 확인된 차지 요구만으로 phase를 늘리지 않는다.

### 최소성 판정

- `RequiredHeldCommands`는 `Y 유지 중 X`와 같은 실제 확정 조합을 표현하므로 제거하지 않는다. 일반 연타와 단일 버튼 release edge에서는 비워 둔다.
- `Begin/Release/Cancel` 세 phase를 유지하고 `Hold` phase는 추가하지 않는다. 활성 Combo Ability의 `HeldCommands`가 activation 지역 상태를 소유하며 ASC는 command를 방송만 한다.
- 데이터 배열 순서가 같은 trigger에 대한 우선순위다. 새 Manager, 전역 입력 이력, frame별 hold tick, 범용 command parser는 추가하지 않는다.

이 절은 ARCH-55의 Player/AI family 분리를 유지하면서 그 절의 `Weak/Strong` command 명칭만 대체한다. 게임 Source와 asset은 이 기록에서 수정하지 않았고 build/PIE도 수행하지 않았다.

<a id="character-architecture-arch-57"></a>
## 2026-09-22 — ARCH-57: `KZ` 프로젝트 타입 접두사와 `Player` 주인공 역할명 확정

### 명명 경계

- C++ 런타임 타입의 프로젝트 접두사는 `Khazan`에서 `KZ`로 변경한다. 클래스·구조체·열거형·델리게이트·프로젝트 네임스페이스와 관련 파일명이 이 규칙을 따른다. 예: `UKhazanAbilitySystemComponent` → `UKZAbilitySystemComponent`, `FKhazanComboCommand` → `FKZComboCommand`, `KhazanGameplayTags` → `KZGameplayTags`.
- 주인공 캐릭터라는 역할을 나타내는 타입·에셋·변수명은 `Khazan` 대신 `Player`를 사용한다. 예: `AKhazanPlayer` → `AKZPlayer`, `BP_KhazanPlayer` → `BP_Player`, `DA_CharacterDefinition_Khazan` → `DA_CharacterDefinition_Player`.
- 프로젝트와 Unreal 모듈의 고유 정체성은 계속 `Khazan`이다. 따라서 `Khazan.uproject`, `Source/Khazan`, `Khazan.Build.cs`, Target 파일, 모듈 진입점 `Khazan.cpp/.h`, `KHAZAN_API`, `/Script/Khazan`은 변경하지 않는다. 이 이름들은 런타임 타입 접두사나 주인공 역할명이 아니다.
- `_Art/Kazan`과 `CA_P_Kazan_*` 같은 원작 추출 경로·식별자는 원본 출처를 보존한다. `_Art/Kazan`에는 주인공뿐 아니라 HeinMach·StormPass 월드와 환경 리소스도 함께 있으므로 `Player` 역할 폴더로 해석하지 않는다.

### 실제 적용 범위

- native reflected type 44개와 대응 소스 파일·include·generated header·호출부를 `KZ` 계약으로 이관했다.
- 주인공 의미를 가진 Blueprint, Character Definition, 파생 애니메이션, 모듈러 메시·스켈레톤·PhysicsAsset·머티리얼 69개를 `Player` 이름으로 이관하고 참조 에셋을 다시 저장했다.
- `DefaultEngine.ini`에 기존 native class/struct/enum/property 경로용 Core Redirect를 두고, Gameplay Tag `AssetData.CharacterDefinition.Khazan`은 `AssetData.CharacterDefinition.Player`로 redirect했다. 새 저장 결과가 안정된 뒤에도 기존 저장 데이터와 외부 참조를 위한 호환 경계로 유지한다.
- 이름 변경 전 사용자가 편집 중이던 주요 에셋 6개는 `Saved/KZNamingBackup/BeforeEditorMigration`에 별도 백업한 뒤 에디터 마이그레이션을 수행했다.
- 현재 실행 가능한 Animation·Enemy 도구에 저장돼 있던 이전 native class 경로와 `SK_Khazan`/`SKM_Khazan`/`DAS_Khazan_*` 참조도 새 `KZ`/`Player` 경로로 맞췄다. 과거 결과 파일명, 원작 metadata, 프로젝트명 기반 로그·metadata key는 이관 당시 증거와 호환 계약이므로 변경하지 않았다.

### 검증 결과

- Unreal asset registry 재검사 결과 이름 또는 패키지 경로에 역할명 `Khazan`이 남은 에셋 0개, `/Game` redirector 0개, 이전 경로 잔존 0개, 새 목적지 누락 0개다.
- native source 재검사 결과 의도적으로 유지한 모듈 정체성과 호환 redirect를 제외한 기존 `Khazan` 접두사 타입·include·파일명은 0개다.
- `KhazanEditor Win64 Development` 빌드는 성공했다. `/Game` Blueprint 38개도 모두 compile됐으며 Blueprint compile failure는 0개다.
- `CompileAllBlueprints` commandlet 프로세스는 Blueprint compile 전에 기존 `GameFeatures.GameFeatureData` 클래스를 찾지 못하는 startup ensure 때문에 종료 코드 1을 반환했다. 이번 명명 이관으로 생긴 Blueprint 오류와는 분리된 기존 프로젝트 설정 문제다.
- 변경한 Python 도구 전체는 UE 5.8 bundled Python의 `compileall`을 통과했다.

이 절은 제안이 아니라 2026-09-22에 실제 Source·Config·Unreal asset에 적용하고 검사한 명명 계약이다. 과거 절의 `UKhazan*`, `FKhazan*`, `EKhazan*` 표기는 당시 기록을 보존하며, 이후 구현은 이 절의 `KZ`/`Player` 경계를 따른다.

<a id="character-architecture-arch-58"></a>
## 2026-09-23 — ARCH-58: StrongCharge의 authored threshold와 release 분기

### 목표 동작과 실행 소유권

- Player의 Y `Begin`은 Strong Attack Ability를 즉시 활성화하고 `StrongChargeStart`에서 Charge 모션을 시작한다. Enhanced Input의 `Hold` trigger나 Controller timer는 사용하지 않는다.
- 정상 `Release`가 `ChargeReady`보다 먼저 오면 `StrongAttack01`, `ChargeReady` 이후에 오면 `StrongChargeAttack`으로 전환한다. Y를 계속 유지하면 `ChargeEnd` authored point가 `StrongChargeAttack`으로 강제 전환한다.
- `Cancel`은 정상 release 공격을 선택하지 않는다. 현재 command의 held/pending만 정리하고, held 조건이 사라진 authored edge도 실행하지 않는다.
- held command, 현재 charge phase node, pending command와 Montage task는 활성 `UKZComboAttackAbility` 인스턴스가 소유한다. Character, Controller, AnimInstance에 charge bool이나 hold timer를 추가하지 않는다.

### 최소 schema 확장

- `FKZComboCommandEdge`에는 기존 Open/Commit/End 창을 따르는 기본값과 현재 node 수명 동안 즉시 실행할 수 있는 값을 구분하는 작은 timing enum을 추가한다. 기존 Weak/Strong 연타 edge의 기본값은 windowed이며, Charge node의 Y `Release` edge만 immediate다.
- `FKZComboNode`에는 `EventName`, `RequiredHeldCommands`, `OwnerTagRequirements`, `TargetNodeId`를 가진 authored-event edge 배열을 추가한다. `ChargeReady`와 `ChargeEnd`는 Montage의 `Play Montage Notify` Branching Point가 이 배열을 구동한다.
- `StrongChargeStart`와 `StrongChargeReady`는 같은 Montage와 같은 `Charge` section을 가리킨다. `ChargeReady` edge는 재생 위치를 되감지 않고 runtime `CurrentNodeId`만 바꾸는 logical transition이다. 서로 다른 section으로 향하는 `StrongAttack01`과 `StrongChargeAttack` edge만 관성화 요청 뒤 section jump를 수행한다.
- 이 확장은 실제 charge 소비가 생긴 ARCH-52의 `AuthoredEventEdges` 도입 조건을 충족한다. Strong 전용 timer, frame별 command, `WaitInputRelease`와 Combo Command의 중복 소비, 전역 ChargeManager는 추가하지 않는다.

### 수치 근거와 현재 asset 차이

- 기존 원작 metadata 기록의 `AC_...StrongAtk01_Charge` playback 변환값은 charge step 경계가 약 `0.6000589403–0.6000966776 s`, release/charge 구간 끝이 약 `1.1780140925–1.1781134007 s`다. 현재 30 fps `DAS_Player_StrongCharge`에서 `ChargeReady`는 이 경계를 `0.600000 s`로 대응한 원작 기반 계산값이고, `ChargeEnd`는 뒤쪽 경계 `1.178113 s`를 사용한다. 이는 임의 gameplay timer가 아니라 Montage의 Charge segment 시작 기준 authored point다.
- 읽기 전용 Unreal 검사에서 `DAS_Player_StrongCharge`는 `1.500000 s`, `DAS_Player_StrongChargeAttack`은 `5.433333 s`이고 둘 다 30 fps, Root Motion enabled, Force Root Lock이다.
- 현재 `AM_DAS_StrongAttackCombo`는 `Attack01/02/03` section과 세 공격 segment만 가지며 총 `14.366667 s`다. Charge 두 segment, `Charge`/`ChargeAttack` section, `ChargeReady`/`ChargeEnd` notify는 아직 없다.
- 현재 `DA_Player_Combo_Definition`에는 `StrongAttack01/02/03`만 있고 `GA_Player_StrongAttack`의 저장 `EntryNodeId`도 `StrongAttack01`이다. 따라서 이 절의 동작은 아직 적용 완료가 아니다.

### 현재 X/Y tag 이관과 선행 조건

- 2026-09-23 작업 트리의 Source는 사용자가 `Input.Action.WeakAttack/StrongAttack`과 `Command.Player.Attack.Weak/Strong`을 `Input.Action.X/Y`, `Command.Player.Attack.X/Y`로 변경했다. 이 사용자 변경은 되돌리지 않는다.
- 저장된 `DA_InputData`, `DA_CharacterDefinition_Player`, `DA_Player_Combo_Definition`은 읽기 검사에서 여전히 이전 Weak/Strong tag를 가진다. 새 Source와 비교가 실패하므로 Charge 구현 전에 세 asset의 tag를 X/Y로 재저장하거나 동일 범위의 Gameplay Tag redirect를 먼저 적용해야 한다.
- 이번 절은 read-only Source/asset 감사와 구현 계약 기록이다. 게임 Source, Config, Blueprint, Montage, DataAsset은 어시스턴트가 수정하지 않았고 build·PIE도 완료로 기록하지 않는다.

<a id="character-architecture-arch-59"></a>
## 2026-09-23 — ARCH-59: Player input binding tag와 Ability 분류 tag의 분리

- `FGameplayAbilitySpec::GetDynamicSpecSourceTags()`의 `Input.Action.*`는 이 프로젝트에서 **해당 granted Spec의 Player 입력 binding metadata**로 사용한다. CharacterDefinition의 `{ AbilityClass, InputTag }`를 grant할 때 Spec에 넣고, `UKZAbilitySystemComponent::AbilityInputTagPressed/Released/Canceled()`가 `HasTagExact(InputTag)`로 같은 Spec을 찾는 현재 경계는 유지한다.
- `UGameplayAbility::GetAssetTags()`/`SetAssetTags()`의 `Ability.Action.*`는 Ability가 어떤 gameplay 행동인지 나타내는 분류다. block/cancel/query에 사용하며 물리 입력 선택 키로 사용하지 않는다. 여러 공격 Ability가 `Ability.Action.Attack`을 공유할 수 있으므로 이 태그로 Y 입력 대상을 고르지 않는다.
- UE 5.8 엔진 계약상 Dynamic Spec Source Tags는 Spec과 함께 복제되고, 그 Ability가 만드는 GameplayEffect Spec의 captured source tags에도 합쳐진다. 따라서 입력 binding tag 사용은 허용하되, 임의의 owner 상태나 실행 중 상태를 이 컨테이너에 누적하지 않는다. 공유 gameplay 상태는 ASC owned tag/GameplayEffect, Ability 실행 상태는 Ability/Task가 소유한다.
- 2026-09-23 후속 raw asset 확인에서 `DA_InputData`와 `DA_CharacterDefinition_Player`는 `Input.Action.X/Y`, `DA_Player_Combo_Definition`은 `Command.Player.Attack.X/Y`를 저장한 상태로 확인됐다. ARCH-58의 “여전히 Weak/Strong tag” 문장은 사용자가 에셋을 다시 저장하기 전 검사 시점 기록이며 현재 선행 불일치는 해소됐다.
- 한 InputTag에 여러 활성화 후보 Spec을 부여할 경우 현재 입력 순회는 후보 전부에 press 상태와 활성화 시도를 전달한다. 그런 사용례가 생기면 명시적 priority/context resolver를 별도 계약으로 추가하며, Ability Asset Tag를 입력 선택자로 대체하지 않는다. 현재 X와 Y에 각각 한 Spec을 부여하는 범위에서는 추가 resolver가 필요 없다.

<a id="character-architecture-arch-60"></a>
## 2026-09-23 — ARCH-60: 같은 InputTag의 여러 Ability는 단일 Spec으로 중재한다

- 사용자는 앞으로 `Input.Action.Y` 하나에 여러 Ability Spec을 부여할 계획임을 확인했다. 현재 `AbilityInputTagPressed()`는 일치하는 모든 Spec에 `InputPressed=true`를 쓰고 비활성 Spec마다 `TryActivateAbility()`를 호출하므로, 모든 후보가 활성화를 시도하고 서로 차단하지 않는 후보는 동시에 실행될 수 있다. 이 동작을 Y Action의 최종 계약으로 사용하지 않는다.
- 하나의 Player action press는 최대 하나의 Spec만 선택한다. 이미 실행 중인 동일 입력 Spec이 그 입력 실행을 소유하고 있으면 그 Spec에 재입력을 전달하고, 그렇지 않으면 context/activation requirement와 명시적 우선순위로 비활성 후보를 판정하여 첫 성공에서 중단한다. 단순 `ActivatableAbilities` 순회 순서나 먼저 적용된 block 결과를 gameplay 우선순위로 취급하지 않는다.
- 활성화 시도 전에는 선택 후보의 `FGameplayAbilitySpec::InputPressed`를 true로 설정해야 activation 시작 시 초기 눌림 상태가 보인다. 시도가 실패하면 즉시 false로 복구한다. 성공한 Spec 하나만 true를 유지한다.
- `Released`와 `Canceled`는 같은 InputTag 전체가 아니라 실제로 `InputPressed`가 true인 선택 Spec만 정리한다. 정상 Release만 active Spec의 `AbilitySpecInputReleased`와 generic replicated release event로 전달하며 Cancel은 release 공격을 만들지 않는다.
- Ability의 `ActivationRequiredTags`/`ActivationBlockedTags`, cost와 cooldown은 후보 적격성 조건이며 단독 우선순위가 아니다. 실제 두 번째 Y 후보를 추가할 때 binding priority의 작성 위치와 수명을 함께 구현한다. 그 전까지 동일 InputTag 중복 grant는 현재 Source에서 안전한 구성으로 간주하지 않는다.
- 공격의 `Command.Player.Attack.Y` 방송은 이 Spec 선택과 별개다. 활성 Combo Ability가 command graph로 연타·차지·handoff를 판정하며, 여러 Y Ability를 전부 직접 활성화해서 콤보를 표현하지 않는다.

<a id="character-architecture-arch-61"></a>
## 2026-09-23 — ARCH-61: StrongCharge 범용 edge 확장 철회와 입력 중재 보정

### 잘못된 선행 판단의 정정

- `HeldCommands`와 `RequiredHeldCommands`는 command가 현재 눌려 있는지와 chord 조건만 표현한다. 누른 경과 시간이나 최소/최대 charge 시간을 측정하지 않는다. 이를 시간 기반 charge까지 이미 완성된 구조로 설명한 것은 잘못이었다.
- ARCH-58에서 제안한 `FKZComboAuthoredEventEdge`, command timing enum, 같은 section의 logical node 전환은 현재 StrongCharge 한 소비자에 비해 범용 Combo schema와 resolver를 불필요하게 키운다. 이 세 제안은 철회하며 Source와 asset에는 적용하지 않는다.
- ARCH-52/P6-D2의 authored-event edge 후보도 현재 StrongCharge 구현 근거로 사용하지 않는다. 두 번째 실제 authored-event graph 소비자가 확인되기 전에는 공통 Definition에 추가하지 않는다.

### StrongCharge의 작은 실제 소유자

- 기존 `UKZStrongAttackAbility`가 더 이상 빈 migration shim이 아니라 StrongCharge의 실제 차이만 소유한다. 공통 `FKZComboNode`와 `FKZComboCommandEdge` schema는 변경하지 않는다.
- activation에서 엔진 `UAbilityTask_WaitInputRelease` 하나를 시작한다. 정상 release가 반환한 `TimeHeld` 자체를 임의 timer로 재해석하지 않고, Charge Montage의 `ChargeReady` authored point 전후를 나타내는 Ability-local phase와 함께 tap/charged target을 선택한다.
- Charge Montage의 `ChargeReady`와 `ChargeEnd` Play Montage Notify가 각각 최소 charge 완료와 최대 유지 종료를 알린다. Strong Ability의 private phase는 `Charging`, `Ready`, `Resolved` 세 값뿐이다. Release가 `Charging`이면 `StrongAttack01`, `Ready`이면 `StrongChargeAttack`, `ChargeEnd`까지 unresolved이면 `StrongChargeAttack`으로 한 번만 전환한다.
- 공통 Combo base에는 기존 notify handler가 인식하지 않은 notify를 파생형에 넘기는 좁은 protected virtual hook과 검증된 node 전환 함수의 protected 접근만 추가한다. Montage delegate/task를 Strong에서 다시 중복 소유하지 않는다.
- `Cancel`은 release가 아니며 공격 분기를 만들지 않는다. 활성 Combo Ability를 canceled 종료하여 `WaitInputRelease`와 Montage task를 함께 정리한다.

### 같은 InputTag의 여러 진입 Ability

- 같은 `Input.Action.Y`를 가진 여러 Spec은 후보군이지 동시 실행 목록이 아니다. idle press에서는 CharacterDefinition의 grant 배열 순서를 명시적 후보 순서로 사용하고 첫 활성화 성공에서 중단한다. 실패 후보의 `InputPressed`는 즉시 false로 복구한다.
- 동일 입력의 활성 Spec이 있으면 그 실행에만 재입력을 전달하고 새 비활성 후보를 함께 시작하지 않는다. 정상 release/cancel은 실제 `InputPressed`가 true인 선택 Spec만 정리한다. 이 규칙으로 한 물리 키가 context에 따라 여러 진입 행동을 가질 수 있지만 한 번의 press가 여러 실행 수명을 동시에 만들지는 않는다.
- `TryActivateAbilityByInputTag()`는 현재 호출자가 없고 위 Press protocol과 입력 소유권을 함께 처리하지 못한다. 입력 중재 구현에서 재사용되지 않으면 제거하며, 미래 handoff를 이유로 미사용 public helper를 유지하지 않는다.
- 한 활성 Combo Ability 안의 `Y hold/release`, `Y 중 X`, node별 결과 차이는 새 Spec 여러 개를 켜서 표현하지 않는다. 기존 Combo Command와 Strong Ability-local charge phase가 현재 실행 안에서 판정한다.

이번 절은 ARCH-58의 StrongCharge 확장안과 ARCH-60의 미확정 priority resolver를 위 범위에서 대체한다. 어시스턴트가 만든 미적용 StrongCharge proposal diff는 폐기하며 게임 Source와 Content에는 이 정정으로 변경을 적용하지 않았다.

<a id="character-architecture-arch-62"></a>
## 2026-09-23 — ARCH-62: StrongCharge와 StrongAttack 실행 수명 분리

- 사용자 의도는 `Y Begin -> StrongCharge Ability`, 최소 charge 전 정상 release -> 현재 Charge 실행 종료 후 기존 `StrongAttackAbility` 활성화, charge 완료 뒤 release 또는 최대 유지 종료 -> Charge 실행 안의 `StrongChargeAttack` 전환이다. ARCH-61에서 charge phase를 기존 `StrongAttackAbility`에 넣은 결정은 이 절로 대체한다.
- `UKZStrongAttackAbility`는 기존 `StrongAttack01 -> 02 -> 03` 실행만 유지한다. 새 `UKZStrongChargeAbility`가 `Charging/Ready/Resolved`, `WaitInputRelease`, `ChargeReady/ChargeEnd` authored point와 실패 handoff를 소유한다. 별도 cooldown/cost/cancel 수명이 확인되지 않은 `StrongChargeAttack`은 우선 같은 Charge 실행의 공격 node로 유지한다.
- 최소 charge 전 release에서는 선택된 Charge Spec의 `InputPressed`를 먼저 해제하고 generic `InputReleased`로 `WaitInputRelease`를 깨운다. Charge Ability는 자신의 실행을 끝내 `Ability.Action` block과 Montage task를 정리한 다음, 에디터에서 지정한 실제 granted `GA_Player_StrongAttack` class를 `TryActivateAbilityByClass()`로 활성화한다. 새 Strong Spec에 과거 press를 재주입하지 않는다.
- `Canceled`는 generic `InputReleased`를 보내지 않는다. 선택 Charge Spec의 `InputPressed`만 지운 뒤 Controller의 `Command.Player.Attack.Y/Cancel`을 받은 활성 Combo Ability가 canceled 종료하며 StrongAttack 또는 ChargeAttack을 시작하지 않는다.
- 공통 `UKZComboAttackAbility`는 charge phase를 소유하지 않는다. 기존 delegate callback은 현재 Montage 검증 뒤 `ProcessMontageNotify(FName)`라는 protected virtual 처리 함수로 전달하고, base 구현이 `ComboInputOpen/ComboCommit/ComboInputEnd`를 처리한다. Charge 파생형은 이를 override해 base를 호출한 뒤 `ChargeReady/ChargeEnd`만 처리한다. 앞서 제안한 `HandleUnhandledMontageNotify` 명칭과 계약은 폐기한다.
- 공통 base에서 파생 Charge가 실제로 필요한 접근은 검증된 `TransitionToNode()`와 안전한 `FinishAbility()`뿐이다. `Cancel` command는 그 command가 현재 held set에 있던 활성 Combo 실행만 canceled 종료한다. `FKZComboAuthoredEventEdge`나 새 command timing enum은 추가하지 않는다.
- `Input.Action.Y` 후보 순서는 CharacterDefinition grant 배열 순서다. `GA_Player_StrongCharge`를 `GA_Player_StrongAttack`보다 앞에 두며 한 press는 첫 활성화 성공 Spec에서 중단한다. 활성 동일 입력 Spec을 처리한 뒤에도 반드시 반환하여 비활성 후보 활성화 루프로 내려가지 않는다.

이번 절은 사용자의 실행 수명 정정에 따른 설계 기록이다. 게임 Source, Blueprint, Montage와 DataAsset은 수정하지 않았고 build/PIE 결과도 아직 없다.

<a id="character-architecture-arch-63"></a>
## 2026-09-23 — ARCH-63: 선택 Spec의 Input Canceled 처리 보정

- `AbilityInputTagCanceled()`는 exact InputTag와 `InputPressed == true`가 함께 맞는 선택 Spec 하나의 눌림을 지운 뒤, 그 Spec이 활성 상태면 엔진 `CancelAbilityHandle()`로 해당 실행을 canceled 종료한다. generic `InputReleased`는 보내지 않으므로 `WaitInputRelease`의 실패/성공 공격 분기가 실행되지 않는다.
- 이 선택 Spec 취소가 Charge 실행의 Task, Montage와 delegate를 정리한다. 이후 Controller가 방송하는 Combo `Cancel`은 다른 활성 subscriber의 held/pending cleanup 의미를 유지하며, 공통 Combo base가 임의의 held command Cancel 하나만으로 모든 공격 실행을 종료하도록 바꾸지 않는다. ARCH-62의 “Combo Cancel을 받은 base가 종료” 설명은 이 절로 대체한다.
- Charge 파생형이 필요한 공통 base 확장점은 검증된 Montage 이름을 처리하는 `ProcessMontageNotify(FName)`, `TransitionToNode()`, `FinishAbility()`다. `HandleComboCommand()`의 기존 Cancel 정리 계약은 유지한다.

이번 보정도 설계 설명만 갱신했으며 게임 Source에는 적용하지 않았다.

<a id="character-architecture-arch-64"></a>
## 2026-09-23 — ARCH-64: 단일 Combo Edge의 hold·release·node-event 전이 계약

- `StrongCharge`의 성공/실패 전이를 `UKZStrongChargeAbility::ActivateAbility()`, `ProcessMontageNotify()`, `StartChargedAttack()`, `ActivateFailedChargeAttack()`에서 직접 선택하는 ARCH-62/63의 Charge 전용 실행안은 폐기한다. Node에서 Node로 가는 모든 전이는 Combo Definition의 같은 Edge 형식으로 작성하고 공통 Combo runtime이 해석한다. 별도 `FKZComboAuthoredEventEdge`를 추가하지 않는다.
- 현재 `FKZComboCommandEdge`는 command 한 번이 도착한 순간에만 평가되고, `HeldCommands`는 활성 Ability 내부에서만 살아 있으며, 입력창이 닫혀 있을 때 받은 Begin은 이후 node 종료 시점에 다시 평가되지 않는다. 또한 `TransitionToNode()`가 다른 Montage를 거부한다. 따라서 현행 `RequiredHeldCommands`는 `WeakAttack01` 도중 Y를 누른 채 유지하다가 WeakAttack01의 authored 종료 시점에 `StrongCharge`로 넘어가는 요구를 충족하지 못한다.
- 물리/AI command의 현재 눌림 집합과 최초 Begin 시각은 Character ASC가 소유한다. 이 ledger는 활성 Ability 교체와 node 전환을 지나서도 유지되고 Release/Cancel/UnPossess/EndPlay에서 해당 command를 정확히 정리한다. Combo Ability는 ASC의 snapshot을 읽으며 같은 상태를 별도 mutable held set으로 중복 소유하지 않는다.
- 기존 Edge 형식은 하나만 유지하되 trigger를 `Command`, `HoldThreshold`, `NodeEvent`로 구분한다. `Command`는 tag와 Begin/Release phase를, `HoldThreshold`는 아직 눌린 command와 경과 기준을, `NodeEvent`는 Montage에 작성된 전이 시점 이름을 사용한다. 모든 trigger는 공통으로 `RequiredHeldCommands`, hold/node 경과시간 범위, owner tag requirements를 조건으로 사용할 수 있다. 배열에서 첫 번째로 완전히 일치한 Edge 하나만 소비하며 겹치는 범위는 asset validation에서 오류로 판정한다.
- 시간 조건은 `CommandBegin` 기준과 `CurrentNodeEnter` 기준을 구분한다. 전자는 다른 공격 중 미리 누른 시간을 포함하고, 후자는 Charge node에 들어온 뒤 실제 charge한 시간만 센다. Release command에는 해제 직전까지의 hold duration snapshot을 실어, ledger에서 tag를 제거한 뒤에도 최소/최대 시간 조건을 판정할 수 있게 한다.
- `RequiredHeldCommands`는 특정 command event에 부속된 장식이 아니다. `Command`, `HoldThreshold`, `NodeEvent` 어느 평가점에서도 현재 ASC ledger와 비교한다. 따라서 `WeakAttack01`의 `ComboInputEnd` 같은 authored node event에 `RequiredHeldCommands={Command.Player.Attack.Y}`와 target `StrongCharge`를 둬서, Y가 계속 눌린 경우에만 전이할 수 있다.
- Edge는 `TargetNodeId`와 선택적인 `TargetAbilityClass`를 가진다. 대상 Ability가 비어 있거나 현재 실행과 같으면 같은 Ability 안에서 node를 바꾸고, 다른 class이면 공통 handoff 경로가 현재 실행을 정리한 뒤 그 granted Ability를 target node로 활성화한다. Charge 실패의 `GA_Player_StrongAttack/StrongAttack01` handoff와 Weak→Charge handoff는 이 데이터로 표현하며 StrongCharge C++에서 클래스를 직접 호출하지 않는다.
- 같은 Ability 안의 target이 다른 Montage여도 공통 node player가 이전 Montage task callback을 해제·종료한 뒤 target Montage/Section을 시작한다. 정상·취소·실패·Ability handoff 모두 timer/task/delegate와 node-local reached event를 정리하며, stale timer는 실행 ID와 current node를 재검증한 뒤 무시한다.
- `StrongCharge` 데이터의 의도는 다음 세 Edge다. Y Release가 최소 charge 전이면 `GA_Player_StrongAttack/StrongAttack01`, Y Release가 최소 charge 이후면 같은 실행의 `StrongChargeAttack`, Y가 계속 held인 채 최대 유지 authored point 또는 hold threshold에 도달하면 `StrongChargeAttack`이다. 임계 시각은 원작 metadata를 우선하고, 현재 Montage authored point를 사용할 때는 그 출처와 경계를 기록한다.
- 이 구조에서 `GA_Player_StrongCharge`는 idle Y의 entry를 `StrongCharge`로 선택하는 역할만 가진다. `UKZStrongChargeAbility`의 `Charging/Ready/Resolved`, `WaitInputRelease`, notify override, 실패 class와 성공 node 직접 호출은 제거 대상이다. `GA_Player_StrongAttack`의 별도 실행 수명은 Edge의 generic Ability handoff로 유지한다.

이번 절은 사용자가 요구한 data-driven Combo graph 계약으로 ARCH-62/63의 Charge 전용 분기 부분을 대체한다. 게임 Source와 Content에는 아직 적용하지 않았다.

<a id="character-architecture-arch-65"></a>
## 2026-09-23 — ARCH-65: InputEnd 공통 경계와 최소 Combo Edge

ARCH-64에서 제안한 `Min/Max duration`, duration origin, 임의 NodeEvent, Edge별 target Ability 같은 선택지는 현재 요구보다 복잡하므로 폐기한다. 다음의 작은 계약으로 ARCH-64를 대체한다.

### 모든 Montage Action의 공통 InputEnd

- `UKZActionAbility`를 `UKZGameplayAbility`와 `UKZComboAttackAbility` 사이의 얇은 공통 기반으로 둔다. 주요 Montage Action만 이 기반을 사용하고 passive/상태 Ability에는 강제하지 않는다. Player와 Monster의 Montage Action이 함께 사용한다.
- Action Ability는 시작할 때 다른 `Ability.Action`을 막고, Montage의 `InputEnd` point가 오면 차단을 푼다. Montage를 쓰지 않는 Action도 같은 protected 동작을 직접 호출할 수 있다. 필요한 runtime 상태는 `bInputEnded` 한 값뿐이며 기존 Combo의 `bCanExitToLocomotion`을 대체하므로 bool 수를 늘리지 않는다.
- `InputEnd` 뒤 새 Action 요청이 오면 기존 Action은 교체 가능하다. 다른 Spec은 기존 `CancelAbilitiesWithTag` 경로로 교체하고, 같은 Input/같은 Spec 재시작은 ASC가 input-ended 실행을 먼저 취소한 뒤 다시 활성화한다. 이 처리가 없으면 활성 Spec 우선 반환 때문에 같은 키의 다음 Ability가 시작되지 않는 현행 결함이 남는다.
- `InputEnd` 전에 들어온 다른 Action을 전역 queue로 자동 보존하지 않는다. 계속 눌린 입력을 node 종료에서 소비해야 하는 경우에만 아래 `InputEnd` Edge로 명시한다. InputEnd 뒤 새로 들어온 입력은 모든 Action Ability가 공통으로 받을 수 있다.
- 기존 `ComboInputOpen`과 `ComboCommit`은 Combo 전용 입력창으로 유지한다. 기존 `ComboInputEnd`는 공통 의미의 `InputEnd`로 바꾼다. 한 marker가 Combo 예약 종료와 다른 Action 허용을 함께 여는 현재 계약을 유지하며, 실제 asset에서 두 시각이 달라질 때만 별도 marker를 추가한다.

### 기존 Edge에 필요한 최소 확장

- Edge 구조는 하나만 유지한다. 기존 `CommandTag`, `CommandPhase`, `RequiredHeldCommands`, `OwnerTagRequirements`, `TargetNodeId`를 유지한다.
- `CommandPhase`에 `Hold`와 `InputEnd`를 추가한다. `Cancel`은 상태 정리 사건이며 Edge를 실행하지 않는다.
- Edge에는 `HoldTime` 하나를 추가한다. 이는 해당 command가 현재 node에서 연속으로 눌린 최소 시간이다. 실제 판정 시간은 `Now - max(CommandBeginTime, NodeEnterTime)`으로 하나만 사용한다. 따라서 이전 node에서 미리 누른 시간으로 새 Charge node를 건너뛰지 않으며 별도 duration-origin 설정이 필요 없다.
- 입력 순간의 이동 문맥을 구분하기 위해 `Move` 한 항목을 추가한다. 값은 `Any/Stand/Walk/Run/Sprint`이며 Begin 순간의 raw 이동 유무와 resolved gait로 한 번 snapshot한다. Release/Hold/InputEnd도 같은 snapshot을 사용하므로 전이 직전에 멈췄는지가 아니라 실제 공격 키를 누른 순간을 판정한다.
- Edge 배열 순서가 우선순위다. 앞에서부터 첫 완전 일치 Edge 하나만 소비한다. 긴 hold, 구체적인 Move, 추가 held/tag 조건을 가진 Edge를 fallback보다 앞에 둔다. asset validation은 앞 Edge가 뒤 Edge를 완전히 가리는 설정, 동일 조건의 중복, 존재하지 않는 target을 오류로 판정한다. 별도 Priority 프로퍼티는 추가하지 않는다.

Edge의 판정 순서는 항상 동일하다.

1. 현재 node와 `CommandTag/CommandPhase`가 일치한다.
2. node-local held time이 `HoldTime` 이상이다.
3. Begin 때 snapshot한 `Move`가 일치한다.
4. ASC에 `RequiredHeldCommands`가 모두 남아 있다.
5. 현재 owner tag가 `OwnerTagRequirements`를 만족한다.
6. `TargetNodeId`가 유효하고 재생 가능하다.

### 입력 상태와 Ability handoff

- Player command 상태는 ASC의 map 하나가 소유한다. key는 CommandTag이고 value는 Begin 시각과 Begin 순간 Move snapshot뿐이다. 별도 held container와 시간 map을 중복 보유하지 않는다. map에 존재하면 held다. Release/Cancel/UnPossess/EndPlay에서 정확히 제거한다.
- 활성 Combo Ability는 node 진입 시각 하나와 다음 `Hold` Edge를 깨울 timer 하나만 가진다. node 진입 또는 Begin 뒤 현재 node의 가장 가까운 HoldTime을 예약하고, callback은 current node와 실행 유효성을 다시 확인한다. Ability-local `HeldCommands`는 제거한다.
- `InputEnd`가 오면 현재 held command 각각에 대해 `InputEnd` phase를 평가한다. 따라서 `WeakAttack01`의 Y/InputEnd Edge에 `RequiredHeldCommands=Y`, target `StrongCharge`를 두면 Y가 계속 눌린 경우에만 전이한다.
- Edge에는 target Ability 프로퍼티를 추가하지 않는다. target node가 다른 granted Combo Ability의 고유 `EntryNodeId`이면 ASC가 그 Spec으로 공통 handoff하고, 아니면 현재 Ability가 node를 전환한다. 같은 Definition 안의 EntryNodeId는 중복될 수 없으며 validation에서 검사한다. 이 규칙으로 `StrongAttack01`은 기존 StrongAttack Ability, `StrongCharge`는 StrongCharge Ability로 넘어간다.
- 다른 Ability로 handoff할 때 target을 먼저 활성화하고 성공한 경우에만 출발 실행을 정리한다. held command로 들어가는 handoff는 target Spec에 현재 pressed 소유권을 넘기고, Release로 들어가는 handoff는 넘기지 않는다. 실패 시 출발 실행과 Montage를 먼저 없애지 않는다.
- 같은 Ability 안의 target node가 다른 Montage이면 공통 node player가 이전 task callback을 해제하고 target Montage/Section을 시작한다. Charge 전용 Montage 전환 코드를 만들지 않는다.

### StrongCharge 데이터 표현

Edge 프로퍼티는 다음처럼 사용한다. 실제 `HoldTime` 수치는 원작 metadata를 우선하고 현재 Montage authored 값을 사용할 때 출처를 구분한다.

| Source | Command/Phase | HoldTime | 추가 조건 | Target |
| --- | --- | --- | --- | --- |
| WeakAttack01 | Y / InputEnd | 0 | RequiredHeld=Y | StrongCharge |
| StrongCharge | Y / Release | ChargeReady | 없음 | StrongChargeAttack |
| StrongCharge | Y / Release | 0 | 없음 | StrongAttack01 |
| StrongCharge | Y / Hold | ChargeEnd | RequiredHeld=Y | StrongChargeAttack |

Release Edge는 위에서부터 검사하므로 charge 완료 Edge가 먼저, 0초 fallback Edge가 뒤에 온다. Run/Stand 분기는 같은 Command/Phase/HoldTime에서 구체적인 `Move` Edge를 `Any` fallback보다 앞에 둔다.

이 데이터가 적용되면 `UKZStrongChargeAbility`의 `Charging/Ready/Resolved`, `WaitInputRelease`, notify override, 실패 class, 성공 node, 직접 `TryActivateAbilityByClass()` 호출은 모두 제거한다. `GA_Player_StrongCharge`는 `EntryNodeId=StrongCharge`인 진입 Ability로만 남는다.

### Monster 경계

- Monster를 위해 별도 Montage/Ability 실행 체계를 만들지 않는다. `InputEnd`, GAS block/cancel, Montage task와 cleanup은 Player/Monster가 같은 `UKZActionAbility` 계약을 사용한다.
- 분리할 것은 입력/판단 계층이다. Player Controller는 물리 키를 Begin/Release/Cancel command와 hold 상태로 번역한다. Monster AI는 키를 흉내 내거나 hold ledger를 만들지 않고 선택한 Ability를 직접 요청하고 완료/InputEnd를 기다린다.
- 실제 Monster가 다단 공격을 AI 결정으로 연결해야 할 때만 같은 Combo Ability에 AI가 명시적인 command를 제출할 수 있다. Monster에 hold 요구가 없으면 Hold/Release Edge를 작성하지 않는다. 현행 `AKZMonster`에는 실제 공격 소비자가 없으므로 `UKZMonsterComboAbility` 같은 빈 전용 기반은 선행 생성하지 않는다.

이번 절은 구조 검토 결과이며 게임 Source와 Content에는 아직 적용하지 않았다.

<a id="character-architecture-arch-66"></a>
## 2026-09-24 — ARCH-66: Move 실시간 판정과 Hold/Release 시간 계약 보정

ARCH-65의 `Move` Begin snapshot과 ASC의 `{BeginTime, Move}` 저장 계약은 잘못됐다. 공격 키를 누른 뒤 이동 입력을 놓았는데도 과거 Run 조건이 남기 때문이다. ARCH-65 중 Move snapshot에 관한 문장만 다음 계약으로 대체한다.

### Move는 저장하지 않고 Edge 검사 시점에 읽는다

- Edge의 `Move(Any/Stand/Walk/Run/Sprint)` 항목은 유지하되 command 상태에 저장하지 않는다. Begin, Release, Hold, InputEnd 어느 phase든 해당 Edge를 검사하는 바로 그 순간의 `LocomotionIntent`를 읽는다.
- `InputAmount == 0`이면 `Stand`다. 0이 아니면 현재 `RequestedGait`로 Walk/Run/Sprint를 구분한다. 현재 캡슐 속도는 관성 때문에 입력을 놓은 뒤에도 남을 수 있고, `ResolvedGait`는 Action의 이동 차단 때문에 낮아질 수 있으므로 이 입력 문맥의 기준으로 쓰지 않는다.
- 현행 `AKZPlayer::HandleInputMoveReleased()`가 `ClearMoveInput()`과 `ResetRequestedGaitToDefault()`를 호출하므로 이동 키를 놓은 뒤 다음 Edge 검사에서는 이전 Run/Sprint가 남지 않는다. 별도 Move 저장값과 취소 처리는 필요 없다.
- Move 변화 자체는 전이 사건이 아니다. 이동을 멈췄다는 이유만으로 즉시 node를 바꾸지는 않으며, 그 뒤 발생한 Release, Hold timer, InputEnd 또는 새 Begin이 현재 Move를 판정한다.

따라서 ASC의 지속 입력 상태는 `CommandTag -> BeginTime` map 하나다. map에 tag가 있으면 현재 held이고, Move snapshot은 없다.

### Hold와 Release는 서로 다른 사건이다

- `Begin`: Enhanced Input의 `Started`에서 command의 BeginTime을 한 번 기록한다. 이미 map에 있으면 중복 Begin은 무시한다.
- `Release`: Enhanced Input의 `Completed`가 버튼을 정상적으로 놓았다는 명시적 사건이다. 이때 `Now - BeginTime`을 계산하고 map에서 command를 제거한 뒤 Release Edge를 검사한다.
- `Cancel`: Enhanced Input의 `Canceled`, UnPossess 또는 입력 문맥 상실이다. map에서 command를 제거하지만 Release Edge는 검사하지 않는다.
- `Hold`: 물리 입력 callback이 아니다. 현재 node의 Hold Edge가 요구한 시각에 timer가 깨우는 내부 사건이다. callback 때 command가 아직 map에 있을 때만 Hold Edge를 검사한다. Release/Cancel이 먼저 command를 제거했다면 아무 일도 하지 않는다.
- `InputEnd`: 버튼을 놓았다는 뜻이 아니다. Montage에 저작한 Action 교체/held handoff 경계다. 이 시점에도 map에 남아 있는 command만 각각 InputEnd Edge로 검사한다.

`HoldTime`은 매 frame 증가시키는 runtime 변수가 아니라 Edge의 최소 시간 값이다. 지속 상태로 저장하는 시간은 BeginTime 하나뿐이다. Release, Hold timer, InputEnd에서 필요한 순간에 다음 식으로 현재 node에서의 유효 hold 시간을 계산한다.

`HeldTime = Now - max(BeginTime, NodeEnterTime)`

Release 전에 command를 map에서 제거하므로 Release 사건에는 계산된 HeldTime을 일회성 command 값으로 전달한다. 이는 계속 갱신되는 멤버가 아니다. Hold/InputEnd도 같은 식의 지역 계산값을 사용한다.

### StrongCharge의 세 결과

StrongCharge node의 Release Edge는 배열 순서대로 다음 두 개를 둔다.

1. `Y / Release / HoldTime=ChargeReady -> StrongChargeAttack`
2. `Y / Release / HoldTime=0 -> StrongAttack01`

그리고 최대 유지 종료는 다음 Edge 하나로 둔다.

3. `Y / Hold / HoldTime=ChargeEnd -> StrongChargeAttack`

- ChargeReady 전에 Y를 놓으면 Release의 HeldTime이 첫 Edge에 부족하므로 두 번째 fallback이 실행된다.
- ChargeReady 이상 누른 뒤 Y를 놓으면 첫 번째 Release Edge가 실행된다.
- Y를 놓지 않고 ChargeEnd에 도달하면 timer가 map의 Y를 확인하고 세 번째 Hold Edge를 실행한다.
- Y를 먼저 놓거나 Cancel하면 Y가 map에서 사라지므로 이후 ChargeEnd timer는 전이하지 않는다.
- 경계값은 `HeldTime >= Edge.HoldTime`으로 포함한다. Release와 ChargeEnd timer가 같은 game-thread frame에 겹치면 먼저 성공한 전이가 실행/node 식별자를 바꾸고 나머지 callback은 무효 실행으로 끝낸다. 두 경로의 target도 모두 StrongChargeAttack이다.

`WeakAttack01`의 `Y / InputEnd -> StrongCharge`는 InputEnd가 왔을 때 Y가 map에 계속 남아 있어야 한다. 그 전에 Y를 놓았다면 InputEnd는 Y Edge를 만들지 않는다. 이 계약으로 Release, held timeout, authored InputEnd를 섞지 않고 각각 하나의 명확한 사건으로 구분한다.

이번 절은 ARCH-65의 Move와 시간 사건 설명을 보정한 구조 결정이며 게임 Source와 Content에는 아직 적용하지 않았다.

<a id="character-architecture-arch-67"></a>
## 2026-09-24 — ARCH-67: Montage Notify 기반 Hold 경계

현재 StrongCharge는 hold 시작이 항상 `StrongCharge` node 진입과 일치하고 그 진입 조건으로 Y held를 요구할 수 있다. 따라서 ARCH-65/66의 `HoldTime`, command BeginTime, NodeEnterTime, hold timer와 일회성 HeldTime은 현재 요구에 불필요하다. 해당 시간 측정 계약을 폐기하고 Montage에 저작한 경계로 대체한다. ARCH-66의 Move 실시간 판정과 InputEnd/Release 구분은 유지한다.

### 다섯 Notify 역할

Notify 이름은 역할을 드러내도록 다음 다섯 가지를 사용한다. 이는 시스템이 인식하는 이름의 종류이며, 여러 Montage section에는 같은 이름의 Notify instance가 반복될 수 있다.

| Notify | 의미 |
| --- | --- |
| `InputOpen` | 현재 node의 한 칸 command buffer를 연다. |
| `InputCommit` | Open 이후 저장된 command를 실행하고, 이후 입력은 즉시 실행하는 구간으로 바꾼다. |
| `InputEnd` | buffer를 닫고 Action 교체를 허용하며, 현재 held command의 InputEnd Edge를 검사한다. |
| `HoldCommit` | 이 node의 최소 hold 성공 경계를 통과했다고 기록하고, 현재 held command의 HoldCommit Edge가 있으면 검사한다. |
| `HoldEnd` | 최대 hold 경계다. 이 순간에도 held인 command의 HoldEnd Edge를 검사한다. |

`Open`, `Commit`, `End`처럼 맥락 없는 이름은 Montage 종료와 hold 종료를 혼동시키므로 사용하지 않는다. Hold 시작은 node 진입 자체이므로 `HoldOpen` Notify는 만들지 않는다.

모든 section이 다섯 개를 전부 가질 필요는 없다.

- 일반 Combo section은 보통 `InputOpen`, `InputCommit`, `InputEnd`를 가진다.
- StrongCharge section은 `HoldCommit`, `HoldEnd`를 가진다. 일반 combo buffer도 필요할 때만 Input 계열을 추가한다.
- ChargeAttack recovery에서 다른 행동으로 빨리 나가게 하려면 ChargeAttack section에 `InputEnd`를 둔다.
- Combo가 아닌 Montage Action은 공통 교체 경계가 필요할 때 `InputEnd`만 사용한다.

Input의 Open→Commit→End와 Hold의 node entry→HoldCommit→HoldEnd는 서로 독립적인 두 시간축이다. 두 종류의 구간이 Montage에서 겹쳐도 한 enum으로 합치지 않는다.

### 최소 runtime 상태

- ASC는 현재 held인 CommandTag set만 소유한다. Begin은 tag를 추가하고, Release/Cancel은 제거한다. 시간은 저장하지 않는다.
- 활성 Combo Ability는 현재 node에 대해 `bHoldCommitted` 하나만 가진다. node 진입 때 false, `HoldCommit`에서 true, node 이탈/종료에서 reset한다. 기존 StrongCharge의 `Charging/Ready/Resolved` enum 전체를 대체한다.
- `InputOpen/InputCommit/InputEnd`에는 기존 한 칸 pending command와 input window phase를 사용한다. Hold 상태와 input buffer 상태는 동시에 존재할 수 있으므로 같은 변수로 합치지 않는다.
- `InputEnd`의 다른 Action 허용 상태는 공통 Action Ability가 소유한다. Hold 전용 Ability, timer와 `WaitInputRelease`는 만들지 않는다.

이 한 bool은 Release가 HoldCommit 전인지 후인지 구분하는 실제 소비자가 있으므로 필요한 상태다. Montage 위치를 매번 검색하거나 GameplayTag로 Ability-local phase를 노출하지 않는다.

### 같은 Edge resolver에서의 표현

Edge의 사건은 `Begin`, `Release`, `InputEnd`, `HoldCommit`, `HoldEnd`로 표현한다. `Cancel`은 held/pending 정리만 하고 Edge를 실행하지 않는다. Hold 판정에는 `Any/BeforeCommit/AfterCommit` 세 값의 짧은 조건 하나를 둔다. `HoldTime` 숫자는 두지 않는다.

StrongCharge node의 Edge는 다음 세 개다.

| Command / Event | Hold 조건 | Target |
| --- | --- | --- |
| Y / Release | BeforeCommit | StrongAttack01 |
| Y / Release | AfterCommit | StrongChargeAttack |
| Y / HoldEnd | AfterCommit | StrongChargeAttack |

- Y Release는 Enhanced Input `Completed`에서 즉시 들어온다. held set에서 Y를 제거한 뒤 현재 `bHoldCommitted`에 맞는 Release Edge 하나를 실행한다.
- `HoldCommit`은 `bHoldCommitted=true`를 먼저 기록한다. 전이 Edge가 작성돼 있으면 같은 resolver로 실행하고, 없으면 현재 charge motion을 계속 재생한다.
- `HoldEnd`는 그 순간 held set에 남은 command만 resolver에 보낸다. Y가 먼저 Release/Cancel됐다면 Y/HoldEnd 사건 자체를 만들지 않는다.
- Hold node의 Release는 일반 combo buffer의 Open/Commit 상태로 지연하지 않는다. Release는 held 수명을 끝내는 사건이므로 즉시 Hold 조건을 판정한다.

WeakAttack01의 held handoff는 `Y / InputEnd / Hold=Any -> StrongCharge`로 표현한다. InputEnd도 현재 held set을 순회해 사건을 만들기 때문에 같은 Y를 `RequiredHeldCommands`에 다시 적지 않는다. `RequiredHeldCommands`는 X+Y 같은 추가 chord를 요구할 때만 사용한다.

### Notify 방식의 적용 범위

이 방식은 hold command가 node 진입부터 이미 눌려 있고 charge 기준이 Montage 재생 위치에 묶이는 현재 공격에 맞다. Montage play rate나 일시정지가 바뀌어도 threshold가 모션과 함께 이동한다.

미래에 이미 재생 중인 하나의 node 중간에서 처음 누른 각 command마다 서로 다른 실제 경과 시간을 재야 한다면 Notify만으로는 그 늦은 Begin 기준을 알 수 없다. 그 요구가 실제로 생길 때 해당 command의 BeginTime을 추가한다. 현재 StrongCharge와 WeakAttack01 held handoff에는 그 기능이 필요하지 않다.

Notify 순서는 section별로 `InputOpen < InputCommit < InputEnd`, `HoldCommit < HoldEnd`를 validation한다. gameplay 경계에는 현재와 같은 Montage Notify/Branching Point 전달 경로를 사용하고, node 전환 뒤 도착한 이전 Montage callback은 현재 Montage와 실행 유효성 검사로 버린다.

이번 절은 Hold 시간 계약 검토 결과이며 게임 Source와 Content에는 아직 적용하지 않았다.

## 2026-09-27 — ARCH-67 적용 감사와 전체 구현 범위 판정

- 저장 Source에는 ARCH-67의 다섯 Notify(`InputOpen`, `InputCommit`, `InputEnd`, `HoldCommit`, `HoldEnd`), ASC held command set, `bHoldCommitted`, 단일 Edge resolver, EntryNode 기반 Ability handoff와 같은 InputTag 재입력이 적용됐다. `UKZStrongChargeAbility`는 전용 charge 상태 없이 빈 진입 타입으로 남아 있다.
- 현재 PIE 로그에서는 WeakAttack01→02→03→04, StrongAttack01→02→03, StrongCharge→StrongChargeAttack 전환과 PIE 종료가 오류 없이 관측됐다. 사용자는 현재 콤보 동작을 완료했다고 확인했다. 이 증거로 **현재 Player 콤보/차지 실행 수직 절편은 동작 상태**로 판정한다.
- `KhazanEditor Win64 Development` UBT 검사는 성공했고 target은 up-to-date였다. `UnrealEditor-Khazan.dll`의 저장 시각은 최신 Combo/ASC Source보다 뒤이므로 현재 실행 모듈에 해당 Source가 반영된 상태다.
- 현재 runtime은 같은 Ability 안의 다른 Montage 전환을 명시적으로 거부한다. 현재 Player graph는 같은 Montage section 전환 또는 다른 granted Entry Ability handoff로 구성되어 이 제한을 밟지 않는다. 실제 Combo에서 같은 Ability·다른 Montage Edge가 생길 때 공통 node player를 확장한다.
- `UKZActionAbility`의 InputEnd 상태·block 해제 계약은 공통으로 구현됐지만 verified Montage Notify를 전달하는 실제 소비자는 아직 Combo Ability뿐이다. 다음 비콤보 Montage Action이 생기면 그 Action의 기존 Montage task/notify 경로에서 `SetInputEnded()`를 호출해 두 번째 소비를 검증하며, 지금 별도 전역 notify router를 만들지 않는다.
- 현재 Move 조건은 `Any/NonRun/Run`이며 Stand와 Walk, Run과 Sprint를 각각 따로 구분하지 않는다. 현재 데이터가 비주행/주행 두 분류만 요구하면 충분하며, 실제 분기가 생기기 전에는 enum을 늘리지 않는다.
- Combo Definition의 중복 NodeId, 존재하지 않는 target, 동일·가려진 Edge, Notify 순서를 편집 시점에 막는 `IsDataValid()` 계약은 아직 없다. 노드와 Edge를 본격 확장하기 전 추가할 첫 안정화 항목이다.
- 이 완료는 v3의 **액션 실행/콤보 한 수직 절편**에 한정된다. Stamina와 Cost, hit window와 접촉 판정, Damage/HP, HitReact/Death, GameplayCue, Monster AI, Dodge/Guard, Targeting, Interaction과 Encounter는 구현되지 않았다. 따라서 문서 아키텍처의 방향은 확립됐지만 전체 게임 아키텍처 구현 완료는 아니다.
- 다음 구현 순서는 새 Combo 추상화를 더 만드는 것이 아니라 P2의 첫 Stamina Cost 한 경로를 연결한 뒤 P3의 `WeakAttack01 한 번의 hit 후보 → Damage 적용 → HitReact → HP 0 Death → Cue` 수직 절편으로 진행한다. Combo Ability handoff가 여러 activation을 만들기 때문에 Strong/Charge 비용은 원작 비용 단위가 확인되기 전 일괄 적용하지 않는다.

## 2026-09-27 — ARCH-68 Stamina → LockOn 8방 → Dodge 우선순위

- 사용자 우선순위에 따라 다음 수직 절편은 `P2 최소 Stamina/Cost → LockOn Walk·Run 8방 → Dodge motion/cost → P3 hit·damage` 순서로 진행한다. 이는 P3를 폐기하는 결정이 아니라 Dodge의 선행 조건인 자원과 방향 표현을 먼저 닫는 순서 변경이다.
- `Stamina/MaxStamina`의 원본은 Character가 등록한 `UKZAttributeSet` 한 곳이다. 초기값과 비용은 GameplayEffect로 적용하고 `KZAbilitySystemComponent`에 수동 차감·별도 stamina float·행동별 if를 추가하지 않는다. 첫 비용 검증은 한 activation으로 전체 section combo를 실행하는 WeakAttack 하나에만 연결한다.
- StrongCharge → StrongAttack처럼 Ability handoff가 새 activation을 만드는 경로는 양쪽 `CommitAbility()`가 각각 실행된다. 원작의 비용 단위가 확인되기 전 양쪽 Cost GE를 복제하지 않는다.
- 첫 LockOn 소비자는 Player Actor에 `현재 target + 그 원인이 취득한 movement constraint handle`만 둔다. target이 유효할 때 constraint가 `ResolvedRotationMode=LockOn`과 최대 gait Run을 기여하고, 해제·target invalid·UnPossess에서 그 handle만 회수한다. 검색·전환·카메라·공격 보정이라는 두 번째 실제 소비가 생기기 전에는 `TargetingComponent/Manager`를 선행 생성하지 않는다.
- LockOn pose 선택은 이미 snapshot에 있는 `RotationMode`와 `MovementDirectionAngle`을 소비한다. gameplay target이나 lock 수명을 AnimInstance/ABP가 소유하지 않는다.
- Dodge는 `UKZActionAbility` 파생 Ability가 cost, montage task, 방향 snapshot, root-motion 실행과 cleanup을 소유한다. `InputEnd`는 Action base가 검증된 현재 Montage의 notify를 받아 block을 해제하고, 각 Action이 필요하면 held move exit를 추가한다. Dodge가 두 번째 실제 소비자이므로 Combo 안의 notify bind/filter를 이 작은 공통 계약으로 올리는 것은 허용한다.
- 이번 Dodge 범위는 방향별 motion, Cost, Action 교체, CMC Root Motion과 종료 cleanup이다. 피해 판정 소비자가 아직 없으므로 `State.Invincible`을 미리 추가하지 않는다. P3 hit 결과가 생기면 authored invulnerability NotifyState와 실행별 Effect handle을 연결한다.
- 이 절은 구현 순서와 책임 결정이다. 게임 Source/Content/Config에는 아직 적용하지 않았다.

<a id="character-architecture-arch-69"></a>
## 2026-09-29 — ARCH-69: 화면 중앙 LockOn 획득·기준점·카메라 계약

사용자가 LockOn 입력 시 카메라에 보이는 적을 검색하고, 화면 중앙에 가장 가까운 적을 선택하며, 카메라와 Player가 그 적을 계속 바라보는 요구를 확정했다. 따라서 ARCH-68의 “검색·카메라라는 실제 소비가 생기기 전에는 TargetingComponent를 만들지 않는다”는 보류 조건은 충족됐다. Player Actor가 target을 직접 보관하는 L1 임시 소유 계약은 아래 `UKZTargetingComponent` 계약으로 대체한다. 7계층의 Spatial·Targeting 책임이며 전역 TargetManager는 만들지 않는다.

### 소유권과 호출 경계

- `AKZPlayerController`는 `Input.Action.LockOn`의 `Started`만 받아 현재 Pawn의 `ToggleLockOn()`을 호출한다. 같은 키의 두 번째 Started는 재검색보다 해제를 우선한다.
- `AKZPlayer`는 Player 조립과 얇은 전달점만 유지하고, `UKZTargetingComponent`가 현재 target weak reference, 자신이 취득한 movement constraint handle, 검색·시작·유지·해제와 camera control rotation 출력을 소유한다.
- `AKZMonster`는 capsule/root에 붙은 `LockOnTargetPoint` SceneComponent 한 점을 소유하고 getter로 world location을 제공한다. 현재 모든 gameplay 적이 이 기반을 사용하므로 아직 별도 Targetable interface는 만들지 않는다.
- `UKZLocomotionComponent`는 기존처럼 LockOn constraint를 해결해 최대 gait Run과 `EKZRotationMode::LockOn`을 CMC에 적용한다. AnimInstance/ABP는 target을 읽지 않고 기존 snapshot의 RotationMode와 MovementDirectionAngle만 소비한다.
- 검색·projection·trace·control rotation write는 locally controlled Player의 game thread에서만 실행한다. AI target 선정과 Ability의 순간 target snapshot은 별도 producer/consumer 계약으로 유지한다.

### 첫 Target 선택

첫 입력에서만 현재 World의 활성 `AKZMonster`를 순회한다. 현 단계에서는 입력 한 번당 한 번의 `TActorIterator`가 요구 범위를 충족하므로, 원작 근거가 없는 탐색 반경·collision registry·전역 subsystem을 먼저 만들지 않는다.

각 후보는 다음 순서로 검사한다.

1. 유효한 다른 World actor이고 숨김 상태가 아니며 `LockOnTargetPoint`가 유효한지 확인한다.
2. `PlayerController::GetPlayerViewPoint()`의 실제 camera 위치·회전을 사용한다. camera forward와 `TargetPoint - CameraLocation`의 dot이 0보다 커야 한다.
3. `ProjectWorldLocationToScreen(..., bPlayerViewportRelative=true)`가 성공하고 투영점이 viewport 사각형 안에 있어야 한다.
4. camera 위치에서 target point까지 `Visibility` trace를 수행한다. blocking hit가 없거나 첫 hit actor/component owner가 해당 Monster일 때만 화면에 보이는 후보로 인정한다.
5. 화면 중심 `(W/2, H/2)`에 대한 정규화 좌표 `dx=(ScreenX-W/2)/(W/2)`, `dy=(ScreenY-H/2)/(H/2)`를 만들고 `Score=dx²+dy²`가 가장 작은 후보를 선택한다. 해상도와 종횡비에 따른 pixel 편향을 피하며 world distance는 중심 점수에 섞지 않는다. 수치가 같은 경우에만 camera 거리 제곱이 작은 후보를 고른다.

후보가 없으면 constraint와 camera를 건드리지 않고 unlocked 상태를 유지한다. 획득 뒤 target이 잠깐 가려지거나 화면 밖으로 나갔다는 이유만으로 자동 해제하지 않는다. 현재 해제 원인은 두 번째 LockOn 입력, target 파괴/무효화, UnPossess와 EndPlay다. 사망/비타기팅 태그는 해당 gameplay 상태가 구현될 때 후보·유지 predicate에 추가한다.

### 높이와 원작 기준점

`PlayerZ`와 `TargetZ`를 같게 만드는 처리는 폐기한다. camera LookAt은 Monster의 full 3D `LockOnTargetPoint`를 사용한다. Player capsule은 기존 CMC 경로가 Controller Yaw만 따라가고 `bUseControllerRotationPitch=false`를 유지하므로 target 높이를 보존해도 capsule이 위아래로 기울지 않는다.

원작 metadata에는 공통 `LockOnTarget` skeleton socket 대신 캐릭터별 `xxLockOnSphereComponent`와 `bUseRotToTargetLockOnSphereLocation=true`가 반복된다. 현재 복원 메시의 `LookAt01`은 머리 시선 socket이며 별도 LockOn component의 대체물이 아니다. 원본 좌표와 현재 소켓 감사의 정본은 `Docs/Art/LOCKON_TARGET_ANCHOR_AUDIT_20260929.md`다. 원본 component의 sphere radius 의미를 확인하지 못했으므로 현 구현은 안정된 한 점만 옮기며 radius를 추정하지 않는다.

### camera와 Player 회전

현재 `BP_Player` SpringArm은 `bUsePawnControlRotation=true`, camera/rotation lag는 꺼져 있다. 따라서 lock 유지 tick에서 실제 camera 위치에서 target point로 향하는 full Pitch/Yaw LookAt을 계산하고, 현재 Controller rotation에서 `FMath::RInterpTo`로 보간한 뒤 `SetControlRotation()`에 쓴다. Roll은 0으로 유지한다. 같은 Controller Yaw를 CMC의 controller-desired rotation이 기존 CharacterDefinition `RotationRate`로 따라가므로 camera는 부드럽고 빠르게 먼저 정렬되고 Player capsule은 locomotion 정책의 속도로 target을 향한다. `SetActorRotation()`을 겹치지 않는다.

원작 Player camera 보간 수치는 현재 metadata에서 찾지 못했다. 첫 적용의 `LockOnViewInterpSpeed=12.0 1/s`는 **임시 튜닝값**이다. 60 fps에서 매 frame 남은 각도 오차의 약 20%를 줄여 큰 첫 회전은 빠르게 시작하고 끝에서 완만해지는 `RInterpTo` 성질을 사용한다. 기존 CMC Yaw `RotationRate=540 deg/s`도 현 프로젝트 이관값이지 원작 직접 확인값은 아니다. 두 값은 한 설정 영역에서 조정하고 magic number로 tick 함수에 흩어 놓지 않는다.

LockOn 중 수동 `Input_TurnCamera`는 camera target 출력과 충돌하므로 현재 범위에서는 소비하지 않는다. target 전환 입력이 실제 요구될 때 같은 component의 별도 명령으로 추가한다. 해제 시 control rotation을 과거 각도로 되돌리지 않고 현재 시점에서 수동 camera 입력을 재개한다.

이번 절은 설계와 표적 asset/metadata 감사 결과다. 게임 C++/Blueprint/Input asset과 Enemy asset에는 아직 적용하지 않았고 build/PIE도 수행하지 않았다.

<a id="character-architecture-arch-70"></a>
## 2026-09-29 — ARCH-70: 월드 진행 collision·navigation과 Character 이동 책임

- 레벨이 walkable surface, 물리 장애물, 진행 경계, NavMesh bounds, NavArea_Null과 off-mesh 연결을 소유한다. Player/Monster 클래스에 HeinMach 좌표나 맵별 route 분기를 넣지 않는다. 이는 ARCH-04/08/11/23/29의 이동·Player/AI·레벨 진행 경계를 구체화한다.
- `AKZLevelRouteCollisionActor`는 source box 2,281개를 직렬화하는 hidden HISM container다. `AKZNavMeshBoundsBox`와 `AKZNavModifierBox`도 source brush의 단순 box transform을 저장하는 level adapter다. 이 타입들이 movement intent, gait, action 또는 encounter state를 소유하지 않는다.
- Player와 미래 AI Character의 capsule 이동/충돌 해결은 CMC가 수행한다. AI의 경로 요청은 같은 Recast와 source/compatibility NavLink를 소비한다. 별도 Player 전용 invisible wall이나 AI 전용 복제 지형을 만들지 않는다.
- 원작 자동 Player route에서 계산한 compatibility link 10개는 복원 geometry의 Recast 단절을 연결하는 맵 데이터다. forward drop/link를 실제로 실행할 animation, Ability/Task, 취소·착지 결과가 필요하면 해당 action 수명 소유자가 구현한다. NavLink가 gameplay 결과를 확정하지 않는다.
- `NavArea_Null` 26개는 원본 `NavModifierVolume`의 단일 ±100 cm convex와 actor transform을 그대로 사용한다. source `NavLinkProxy6`의 적용 snap radius `50 cm`와 compatibility link의 `50 cm`는 복원 전용 임시값이며 원본값으로 승격하지 않는다.
- 적용 상태: map/GameMode/GameDefaultMap, 세 level adapter, NavigationSystem dependency와 restore/audit/runtime verify scripts가 실제 저장됐다. 일반 Editor Recast/PIE와 Development Editor build를 통과했다. `KZPlayer`의 locomotion 의미나 CharacterDefinition 수치는 이번 작업에서 변경하지 않았다.
- 검증 정본은 `Saved/ImportReports/HeinMach_Playability_RuntimeVerification.json`이다. 현재 보장은 63 MoveTo의 1,485점·1,422구간 Recast 연결, DualAxeSword Player 이동과 source wall 충돌이다. Encounter, 인간형 적 spawn/AI, tutorial 학습 UI와 interaction action은 별도 수직 절편이다.

## 2026-09-30 — ARCH-69 개정: LockOn 카메라의 비대칭 Pitch 제한

- 현행 `UKZLockOnComponent::UpdateLockOnFacing()`은 실제 camera 위치 대신 `Player actor location + (0, 0, 250 cm)`를 고정 pivot으로 사용한다. 이 `250 cm` 및 기존 `ToTarget.Z` 범위 `[-50, 250] cm`는 현재 Source 값이며 원작 metadata에서 확인한 값이 아니다. 기존 ARCH-69의 실제 camera 위치 full LookAt 설명은 현재 구현과 다르다.
- 새 요구는 LockOn 중 수평 거리에 관계없이 일정 각도보다 더 아래로 내려다보지 않고, 위쪽 target은 바라볼 수 있게 하는 것이다. 따라서 target anchor의 3D 높이는 유지하되, 거리 벡터의 Z를 제한하던 처리를 제거하고 계산된 Controller Pitch의 음수 하한을 제한한다. UE Pitch는 양수가 올려다보기, 음수가 내려다보기다. 최종 보간 출력에도 같은 하한을 적용해 LockOn 진입 전 시선이 이미 하한 아래였던 경우를 포함한다. 위쪽 Pitch에는 LockOn 전용 제한을 두지 않는다.
- 현재 component가 카메라 출력과 target 수명을 계속 소유한다. Player/Locomotion/AnimInstance나 SpringArm attachment를 이 변경 때문에 바꾸지 않는다. `MaxLookDownAngleDegrees=20°`는 원작 근거가 없는 **임시 튜닝값**이다. component defaults에서 조절하며, `20°` 선택은 급한 탑다운을 피하면서 낮은 target을 조금 내려다볼 수 있게 하는 시작점이다. 현재 SpringArm 길이 `600 cm` 기준 충돌·offset이 없으면 이 각도에서 arm 회전으로 생기는 상승량은 약 `600 sin(20°)=205 cm`이며, 값이 작을수록 카메라 상승 상한도 낮아진다. 실제 높이와 framing은 BP offset·collision과 PIE에서 검증해야 한다.
- 원래 full 3D LookAt의 무제한 Pitch 계약은 이 비대칭 제한 범위에서 대체한다. 카메라 회전 보간, CMC Yaw 회전, target 획득/해제 수명은 ARCH-69의 기존 계약을 유지한다.

## 2026-09-30 — ARCH-71: 방향별 Dodge와 해금형 DodgeAttack의 Combo 계약 제안

사용자는 Dodge를 8방 각각 별도 Ability로 표현하고, LockOn에서 8방을 사용하며 비잠금에서는 Forward만 쓰기로 했다. Dodge 도중 공격은 Dodge 방향에 따라 다른 DodgeAttack Ability로 이어지고 해금 조건을 가진다. 이는 ARCH-68의 비콤보 `UKZActionAbility` 파생 Dodge 설계를 대체하는 새 요구다. 아래는 **설계/적용 순서이며 Source·BP·Montage 적용 완료가 아니다.**

### Edge가 맡는 것과 맡지 않는 것

- `FKZComboNode::NodeId`가 현재 Dodge 여부와 고정된 방향을 이미 나타낸다. `Dodge_F`, `Dodge_FR` 등의 노드에만 DodgeAttack Edge를 작성하면 `bIsDodging`·`DodgeDirection` 공통 Edge 조건이 필요 없다. 같은 Edge schema의 `CommandTag/Phase`, `OwnerTagRequirements`, `TargetNodeId`를 재사용한다. 특정 방향에서만 다른 공격을 허용하는 경우도 그 Dodge 노드의 Edge/target으로 표현한다.
- Edge는 **현재 실행 안에서 허용한 전환**만 기록한다. 첫 Dodge 방향 선택, 8개 granted Spec 중 하나의 활성화, Cost/쿨다운, Root Motion/충돌, 영속 해금 사실과 취소/EndPlay 수명은 각각 입력 adapter·ASC·Ability/Task·Progression의 책임이다. 모든 gameplay 분기를 범용 Edge predicate로 몰아넣지 않는다.
- DodgeAttack 해금은 영속 Progression/Save가 원본이고 Pawn 준비 시 ASC에 `Unlock.Skill.DAS.DodgeAttack` 같은 프로젝트 semantic tag로 투영한다. 실제 태그 이름은 원작 내부 tag 확인 결과가 아니다. Dodge 노드의 공격 Edge는 `OwnerTagRequirements`로 이를 요구한다. 해당 spec은 graph-only grant로 두고 물리 `InputTag`를 배정하지 않는다. Progression producer가 아직 없으므로 초기에는 locked 경로를 확인하고 개발용 tag 부여로 unlocked 경로를 시험한다.

### 최소 실행 구조

- 현행 `UKZComboAttackAbility`는 Notify·Montage task·한 칸 command buffer·node/edge 해석·handoff·cleanup을 모두 갖고 있지만 constructor에서 `Ability.Action.Attack`을 부여한다. 이 실행 부분만 공통 `UKZComboActionAbility : UKZActionAbility`로 올리고, 기존 `UKZComboAttackAbility`는 Attack tag를 설정하는 얇은 파생형으로 유지한다. 저장된 Weak/Strong Blueprint 부모 경로를 바꾸지 않는다. `UKZDodgeAbility`는 공통 base에서 파생해 Dodge tag와 진입 방향 설정만 소유한다. DodgeAttack은 새 빈 native subclass 없이 기존 Attack 파생형의 Blueprint 변형으로 시작한다. ASC의 entry 조회 cast는 공통 base로 바꾼다.
- 8개 Dodge Blueprint Ability는 동일한 native 구현·Combo Definition을 공유하되 각각 고유 방향과 `Dodge_<방향>` EntryNodeId를 가진다. 하나의 물리 `IA_Dodge`가 Started 때 방향을 한 번 고정한다. 비잠금은 입력 방향과 무관하게 F; LockOn은 그 순간의 월드 이동 의도를 actor-local 정면/오른쪽에 투영해 8등분한다. 무입력은 F다. 기존 Player deadzone을 재사용하며 CMC 실제 속도로 방향을 추정하지 않는다. AI는 물리 입력을 흉내 내지 않고 같은 ASC 방향 요청 API에 선택한 방향을 넘길 수 있다.
- ASC의 좁은 `TryActivateDirectionalDodge(Direction)`가 granted Dodge spec 중 설정된 방향과 일치하는 하나를 선택한다. 같은 방향 중복 grant는 오류다. `Input.Action.Dodge.<방향>` 태그 8개나 방향별 C++ 클래스 8개는 만들지 않는다. 같은 Dodge Spec 재입력은 `InputEnd` 이후 기존 Action처럼 이전 실행을 정리하고 새 activation을 시작하며, 그 전에는 차단한다.
- Dodge와 DodgeAttack은 하나의 읽기 전용 Dodge Combo Definition을 공유한다. Dodge 8개 노드는 한 Dodge Montage의 해당 section을 재생하고, 각 노드의 X/Begin Edge가 해금 tag와 authored 입력창을 통과하면 대상 DodgeAttack Entry로 handoff한다. 출발 Dodge를 먼저 끝내지 않고 대상의 activation/Commit이 성공할 때만 이전 실행을 정리한다. 각 activation의 Cost 단위는 별도 확인한다. 기존 Attack Cost GE를 복사하지 않는다.
- 현재 InGame DodgeAttack 시퀀스는 F/B/L/R 네 방향만 파일 존재를 확인했다. 우선 네 개의 DodgeAttack Blueprint Ability와 EntryNode를 사용하고, 대각선 Dodge 노드에서 어느 cardinal 공격으로 잇는지는 Combo Definition Edge 데이터로 작성한다. 첫 임시 연결 후보는 FR/FL→F, BR/BL→B이며 원작 분기 근거는 미확인이다. 원작 규칙 또는 사용자 방향 결정이 나오면 데이터만 바꾼다. 8방 공격 asset이 확보되어 실제 공격별 비용/취소/모션 차이가 생기면 Entry Ability를 8개로 늘려도 runtime schema는 그대로다.
- 현행 X/Y Started의 `AbilityInputTagPressed()` 선행은 Dodge `InputEnd` 뒤 일반 공격을 DodgeAttack Edge보다 먼저 활성화할 수 있다. Started에서 ASC held Combo Command를 먼저 제출하고 활성 node의 Edge를 평가한 뒤 일반 InputTag 진입을 시도하는 순서로 바꿔야 한다. 첫 idle 공격은 새 entry 활성화가 뒤따르며, 기존 Weak/Strong 연타·charge·handoff 회귀를 반드시 검사한다. Release/Cancel은 현재의 command 선행 정리 계약을 유지한다.
- Dodge/Attack Montage의 section Next는 의도하지 않은 다음 section으로 이어지지 않게 `None`으로 작성한다. Dodge의 InputOpen/InputCommit/InputEnd 시점은 authored motion과 실제 조작 검증으로 정하고 임의 시간을 넣지 않는다. Root Motion 이동은 Montage/CMC 한 경로만 사용한다. invulnerability는 피해 판정 소비자가 구현될 때 Dodge window와 실행별 Effect handle로 추가한다.

### 사전 안정화와 제품 검증

- 8 Dodge + 4 DodgeAttack 노드를 넣기 전에 `UKZComboDefinitionData::IsDataValid()`로 중복 NodeId, 없는 target, 잘못된 Montage/section, 동일·가려진 Edge를 검출한다. 현재 `ApplyEdge()`는 target Entry Spec이 없으면 local node로 해석하므로 실제 handoff target의 grant와 Definition 공유도 시작 시 검사한다.
- locked/unlocked, 8방/비잠금 F, 같은 방향 재입력, DodgeAttack 성공·Cost 실패 시 Dodge 보존, X/Y 기존 콤보, InputEnd 전후, UnPossess/EndPlay cleanup, CMC capsule 이동·벽/경사, LockOn 선회 중 월드 회피 궤적을 각각 PIE에서 확인한다. 현재 Character `UnPossessed()`는 held command만 비우고 active Action을 명시적으로 취소하지 않으므로 이 수명 경계도 Dodge 적용 시 함께 닫는다.

### 2026-09-30 입력 중재 보정

위의 “Command를 먼저 제출한 뒤 일반 Spec 진입을 시도”만으로는 즉시 DodgeAttack handoff가 성공한 같은 X press에서 새 일반 WeakAttack도 시도할 수 있다. 또한 Command를 소비했다는 이유로 GAS input protocol을 아예 건너뛰면 현재 X/Y Spec의 `InputPressed`와 Cancel 수명이 깨진다. 이를 다음의 작은 반환 계약으로 구체화한다.

- `SubmitComboCommand(Begin)`은 현재 Combo Ability가 Begin Edge를 예약하거나 성공적으로 실행했는지 `bConsumed`를 반환한다. native event의 callback이 한 `bool& bConsumed`를 true로 올리고, ASC는 기존 held command 갱신을 먼저 수행한다. Release/Cancel은 기존 cleanup 순서를 유지하며 반환값은 입력 entry 중재에 사용하지 않는다.
- Controller는 Begin에서 `bConsumed=SubmitComboCommand(...)` 다음 `AbilityInputTagPressed(InputTag, bAllowNewActivation=!bConsumed)`를 호출한다. ASC는 허용값과 관계없이 같은 InputTag의 **이미 활성인** 선택 Spec에 GAS press를 전달한다. 소비된 Begin은 비활성 일반 공격 Spec의 새 activation만 건너뛴다. 따라서 Dodge가 X를 소비하면 WeakAttack은 시작하지 않고, 기존 Weak/Strong이 자기 X/Y를 소비해도 `InputPressed` 및 후속 Release/Cancel은 유지된다.
- 첫 idle press는 구독 중인 Combo Ability가 없어 `bConsumed=false`이므로 기존처럼 entry Spec이 활성화된다. Dodge Edge가 해금/Cost/Window 때문에 실패하면 false가 되어 그 순간 허용된 일반 Action 진입만 기존 GAS block/InputEnd 계약에 따라 시도한다. 성공 handoff 뒤 같은 press가 두 번째 Action을 시작하지 않는지 회귀한다.
- `DodgeAttack`처럼 `InputTag`가 비어 있는 graph-only target Spec에는 handoff 시 `InputPressed=true`를 넘기지 않는다. 그 Spec은 물리 Release로 찾아 정리할 수 없고, 필요한 held 사실은 ASC의 Combo Command set에 이미 있다. 기존 `TryActivateComboEntry()`의 무조건적인 `bInputPressed` 대입을 target Spec의 입력 binding 유무에 맞게 보정한다.

## 2026-10-01 — ARCH-72: Dodge→Weak/Strong 해금 분리와 현행 적용 감사

### 현재 적용과 새 요구

- 사용자는 현재 진행상황과 다음 공동 구현 절차를 요청했고, Dodge→Weak와 Dodge→Strong이 각각 해금형 특수 스킬로 이어진다는 요구를 명확히 했다. 이번 작업은 Source/저장 Blueprint/로그의 읽기 전용 감사와 문서 설명이다. 게임 C++/BP/Content를 수정하지 않았다.
- 현재 `UKZDodgeAbility : UKZActionAbility`는 constructor에서 `Ability.Action.Dodge`, `Block.Movement.Input`, `Block.StaminaRegen`만 설정한다. 방향 설정, ActivateAbility/몽타주 task, Combo Definition/EntryNodeId, Combo delegate/Notify 처리는 없다. `UKZComboActionAbility` 추출과 방향별 ASC 선택도 아직 없다.
- `/Game/Bluprints/AbilitySystem/Abilities/Player/Dodge/GA_Player_DodgeAbility_{F,RF,R,RB,B,LB,L,LF}` 8개의 파일과 `UKZDodgeAbility` 상속 관계는 Rider asset hierarchy로 확인했다. F/R의 property 조회는 빈 결과였으므로 이를 전체 EventGraph 검사나 실행 검증으로 해석하지 않는다.
- 실제 입력 태그는 사용자가 추가한 `Input.Action.A`이며, Command는 `Command.Player.Dodge.A`다. 앞 절의 `Input.Action.Dodge`는 미적용 제안명이다. 새 절차는 현재 A 태그와 기존 Blueprint 이름을 재사용한다. Controller에는 아직 Dodge binding이 없다.
- 표적 경로에서 `IA_Dodge`, `AM_DAS_Dodge`, Dodge Combo Definition, Dodge Cost/Unlock GE와 DodgeAttack Ability는 확인되지 않았다. Dodge/DodgeAttack InGame Sequence는 존재한다. 2026-10-01 10:29 UBT 로그는 Dodge/Tag C++의 Live Coding `Succeeded`이고 에디터 로그는 8개 Dodge BP 재컴파일을 기록한다. 이것은 새 cold build/회피 PIE 통과가 아니다.

### 이전 제안에서 보완할 계약

1. ARCH-71의 단일 `Unlock.Skill.DAS.DodgeAttack`/X-only 분기를 대신해 두 특수 행동을 별도 요구로 표현한다. 제안 semantic tag는 `Unlock.Skill.DAS.DodgeAttack.Weak`와 `.Strong`이다. 프로젝트 명칭이며 원작 내부 태그 확인값이 아니다. 실제 스킬 트리가 둘을 함께 해금한다면 같은 producer가 두 태그를 부여하면 된다.
2. 각 Dodge node의 X/Begin Edge는 Weak 해금 태그와 `DodgeWeakAttack_<방향>` target을, Y/Begin Edge는 Strong 해금 태그와 `DodgeStrongAttack_<방향>` target을 사용한다. Hold/Move는 Any, 추가 held command는 실제 필요가 없으면 비운다. NodeId가 Dodge와 방향을 이미 고정하므로 범용 Edge에 IsDodging/DodgeDirection을 추가하지 않는다.
3. target 특수 공격 Ability의 `ActivationRequiredTags`도 같은 해금 사실을 읽는다. Edge는 그 전환의 허용 여부, Ability는 직접 Spec/AI 활성화를 포함한 실행 승인 경계를 맡는다. 상태 작성자는 하나이며 별도 해금 bool은 만들지 않는다. 해금 태그를 ActivationOwnedTags에 넣지 않는다.
4. 초기 구성은 기존 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`에 Dodge/특수 공격 node를 추가하는 것으로 단순화한다. 모든 관련 Ability는 같은 Definition을 참조한다. 현 ASC는 Definition pointer와 EntryNodeId의 일치로 handoff를 찾으므로 별도 Dodge Definition은 일반 공격 graph와 연결되지 않는다. ARCH-71의 별도 Dodge Definition은 독립 graph가 실제 필요한 경우의 선택지로 남긴다.
5. 방향별 Dodge 8개와 작성된 특수 공격 Entry Ability는 CharacterDefinition에서 처음부터 graph-only grant하고 InputTag는 비운다. 잠긴 특수 스킬도 grant는 유지하되 Edge/ActivationRequiredTags로 실행을 제한한다. 현재 ApplyEdge는 target Spec이 없으면 local node로 해석하므로 grant 누락을 해금 정책으로 사용하지 않는다. 같은 Definition/EntryNodeId 및 같은 Dodge 방향의 중복 grant는 오류다.
6. 공통 Combo 실행/Notify/task/cleanup과 두 현재 소비자가 공유하는 이동·회복 차단 태그는 `UKZComboActionAbility`로 이관한다. `UKZComboAttackAbility`는 기존 직렬화 class/Blueprint 부모를 유지하고 Attack AssetTag만 설정한다. `UKZDodgeAbility`는 새 공통 base와 방향 defaults를 사용한다. 별도 빈 DodgeAttack native class나 Player/AnimInstance의 Dodge 상태 사본은 만들지 않는다.

### 입력·비용·실패 경계 보정

- `bConsumed`는 OpenToCommit에서 유효 Begin을 예약했을 때 true, CommitToEnd에서는 Edge 실행이 성공했을 때 true다. 실패한 즉시 실행을 소비 성공으로 보고하지 않는다. 이미 true인 reference를 다른 listener가 false로 내리지 않는다.
- `AbilityInputTagPressed(InputTag, bAllowNewActivation=false)`는 비활성 후보뿐 아니라 현재 active Spec의 InputEnd 후 cancel/restart도 금지한다. 기존 활성 Spec의 GAS press 전달은 유지한다. 그렇지 않으면 같은 Ability의 local Edge 성공 직후 소비된 press가 새 activation으로 다시 실행될 수 있다.
- graph-only target에는 `InputPressed=false`를 유지하고 X/Y held 사실은 기존 ASC command set에서 읽는다. 입력 binding이 있는 StrongCharge 등은 실제 command와 binding이 일치할 때만 ownership을 넘긴다.
- 현 `TransitionToNode()`는 CheckCost 실패에도 state를 바꾸고 section jump를 실행한다. 비용 gate를 state reset/CurrentNodeId 변경/관성화/점프 전에 두고 실패 시 false로 반환하는 보완이 필요하다. 현 per-node ApplyCost 정책은 사용자의 기존 변경이며 임의로 activation-only로 되돌리지 않는다. Dodge→특수 공격은 다른 Ability activation의 Commit 비용이며 local node 비용과 중복 청구하지 않는다.
- UE 5.8 `UGameplayAbility::CanActivateAbility()`는 비용/태그를 먼저 검사하지만 `PreActivate()`의 CancelAbilitiesWithTag 처리는 override ActivateAbility의 Commit/몽타주 재생보다 앞선다. `TryActivateAbility()`의 true를 Commit과 재생의 완전한 성공/rollback 보장으로 설명하지 않는다. 일반적인 사전 비용 부족은 source block을 복구하고 Dodge를 보존할 수 있으나 activation 후 task/데이터 실패는 별도 검증 대상이다. 공통 CanActivateAbility에서 필수 entry data를 사전 검증하고 authoring 검증을 우선한다. 범용 transaction/rollback 계층은 이번에 추가하지 않는다.
- 동일 방향 re-Dodge의 cancel/restart에서도 비용·태그·entry data를 가능한 범위에서 먼저 검사한다. 기존 실행을 취소한 뒤 새 비용 부족을 발견하는 경로를 성공적인 회피 보존으로 기록하지 않는다.
- UnPossessed는 현재 ClearComboCommands만 수행한다. Ability.Action 취소를 ActorInfo 유효 시점에 명시해 task/delegate/OwnedTags를 끝내고 입력 기록을 정리한다. EndPlay의 DestroyActiveState와 별개다.

### 원작·데이터 미확인과 이번 검증 범위

- InGame에는 Off_DodgeAtk F/B/L/R와 Com_DodgeAtk F/B의 JustMoment, RecklessRush, RecklessRush_Charge가 있다. 저장 `Khazan_DAS_CompositeExact60_FinalAudit_20260917.json`은 playback composite 복원 결과다. 파일명/재생 시간만으로 Weak=JustMoment, Strong=RecklessRush, 원작 해금 조건·차지 규칙을 확정하지 않는다.
- 8방 Dodge 존재가 8방 Weak 특수 공격과 8방 Strong 특수 공격 존재를 뜻하지 않는다. 각 가족의 실제 모션 대응과 대각선 매핑을 확인한 만큼만 Entry Ability를 작성한다. 이전 FR/FL→F, BR/BL→B 임시 후보는 원작 확인값이 아니며 자동 적용하지 않는다.
- 해금 전 기본 회피공격 유무는 사용자 확인 질문을 남겼다. 답변 전 설명의 임시 동작은 특수 스킬 Edge 불일치, InputEnd 전 기존 Dodge 유지, 이후 일반 공격 진입 허용이다. 이는 원작 확정 규칙이 아니다. 기본 회피공격이 있는 경우 unlocked special Edge와 잠긴 경우의 fallback Edge를 같은 node 데이터로 표현할 수 있다.
- 방향 계산은 press 때 현재 Move action value와 camera Yaw를 읽어 월드 의도→Actor local로 변환한다. 360°/8=45°, 반구간 22.5°는 균등 8방 양자화의 수학값이다. deadzone은 기존 Player 설정을 재사용하며 새 gameplay literal을 넣지 않는다. 게임플레이/Ability 접근은 Game Thread에서 하고 AnimInstance worker가 방향·해금 상태를 작성하지 않는다.
- Dodge/DodgeAttack 비용, Notify frame, 전이/블렌드 시간과 실제 Skeleton/Root Motion/LockOn 중 회피 궤적은 새로 확인하지 않았다. 기존 mesh scale 기록은 과거값이고 현재 native source는 0.01이므로 BP 최종 scale을 다시 확인한다. 이번 문서 감사는 build/PIE 실행이나 source 적용을 포함하지 않는다.

## 2026-10-01 — ARCH-71/72 공통 Combo Action 부분 적용 재확인과 코드 설명 보완

- 사용자가 `KZComboActionAbility.cpp`의 코드 첨부와 상세 설명을 요구했다. 이번 점검에서 실제 Source는 위 초기 감사보다 앞서 있다. `UKZComboActionAbility : UKZActionAbility`에 실행 상태/Definition/Entry getter/Task/Notify/Edge/cleanup이 옮겨졌고, 기존 `UKZComboAttackAbility`는 Attack AssetTag ctor만 남았다. `UKZDodgeAbility`도 새 공통 base를 상속하며 Dodge AssetTag만 설정한다.
- `UKZAbilitySystemComponent::HasComboEntry/TryActivateComboEntry`의 include/cast도 실제로 `UKZComboActionAbility`를 사용한다. 이전 절의 "공통 base 추출과 Dodge parent 연결이 아직 없다"는 기록은 당시 검사 시점에 한정된다. 해당 사용자 변경을 되돌리지 않았다.
- 남은 공통 base 보완은 `CanActivateAbility()`의 entry/ASC/AnimInstance 사전 검사와 `TransitionToNode()`의 비용 부족 시 조기 반환이다. 현재 Source는 CheckCost 실패에도 state reset/CurrentNodeId 변경/section jump를 실행한다. local node마다 ApplyCost를 적용하는 사용자 정책은 그대로 보존하는 설명용 보완안을 만들었다.
- 전체 코드 보완안은 `Examples/ComboAction_20261001/KZComboActionAbility.h.txt`와 `.cpp.txt`다. 기존 함수/API와 한 인자 Combo Command delegate를 유지하고 CanActivate 선언/정의, local Cost gate 및 사실과 다른 주석만 보완했다. 이 파일은 게임 Source 적용이나 build/PIE 통과 결과가 아니다.
- `CanActivateAbility`는 CDO/실행 인스턴스 양쪽에서 호출될 수 있으므로 전달된 ActorInfo와 authored entry 설정을 읽고 실행 상태를 쓰지 않는다. `Super::CanActivateAbility`의 비용/쿨다운/태그 gate를 유지한다. Activate의 재검사와 Commit 실패 cleanup도 유지하며 PreActivate 이후 Task 재생 실패의 rollback을 보장하지 않는다.
- 현 `SubmitComboCommand`는 void/한 인자 event이며 Controller Begin은 generic press 선행이다. ARCH-72의 bConsumed/command 선행/graph-only InputPressed 보정과 graph validation은 아직 미반영이다. Dodge 방향/defaults/입력/몽타주/특수 공격/해금은 이번 설명에서 적용하지 않았다.
- 원작 동일값을 새로 검증하지 않았다. 기존 header의 Combo 관성화 0.08 s와 이동 복귀 0.24 s는 현재 프로젝트 임시 튜닝값으로 표시하고 수치는 보존했다. 같은 frame의 HoldCommit/Release는 Game Thread에서 실제 먼저 처리된 사건이 판정을 결정하며, Notify가 항상 먼저라고 보장하지 않는다.
- 검증은 실제 Source 및 설치 UE 5.8 GameplayAbilities의 CanActivate/PreActivate/EndAbility/Cost/Task API 표적 대조와 제안 파일 diff 확인이다. 게임 C++/BP/Content는 편집하지 않았고 새 build/PIE를 실행하지 않았다.

## 2026-10-01 — ARCH-72 입력 소유권 계약 구체화와 Dodge 공동 구현 안내

- 사용자가 Dodge 입력부터 Ability 실행, X/Y 해금형 특별 공격까지 직접 따라 구현할 수 있는 전체 소스와 함수·변수·에디터 설명을 요청했다. 현행 Source를 다시 확인한 결과 공통 ComboAction의 CanActivateAbility와 TransitionToNode 비용 조기 반환은 이미 사용자 코드에 반영됐다. 앞 절의 미적용 기록은 당시 검사 시점에 한정한다.
- ARCH-03/04/07/09/10/72의 입력 수명 계약을 구체화한다. TryActivateComboEntry의 마지막 인자는 모호한 bool 대신 실제 CommandTag로 제안한다. ASC는 X→Input.Action.X, Y→Input.Action.Y 대응과 target Spec의 실제 binding, 현재 held 사실을 모두 확인해서 InputPressed를 결정한다. InputTag가 없는 graph-only DodgeAttack에는 false를 유지한다.
- 같은 물리 입력을 가진 다른 Entry로 handoff할 때 source Spec의 InputPressed도 target으로 이관한다. source가 true로 남으면 기존 Released의 grant-order 탐색이 비활성 source에서 반환해 target의 WaitInputRelease가 깨질 수 있다. 실행 실패 시 handle로 다시 찾은 두 Spec의 이전 입력값을 복구한다. 다른 버튼의 입력 소유권은 건드리지 않는다. 영속 input owner manager나 Player/AnimInstance 상태 사본은 만들지 않는다.
- Command의 소비 반환은 동기 native delegate의 bool 참조를 통해 전달한다. Begin의 유효 예약 또는 즉시 실행 승인만 true로 올리며 Release/Cancel은 기존 정리 경로다. 일반 GAS press는 유지하되 소비된 Begin으로 비활성 activation 및 InputEnd 후 같은 Spec restart를 시도하지 않는다. restart는 CanActivate 사전 검사 후 기존 실행을 취소한다.
- 에디터 검증은 빈/중복 NodeId, target 누락, Montage/section 오류, 지원하지 않는 Cancel Edge와 완전히 같은 조건의 중복 Edge를 대상으로 한다. 서로 다른 조건이 배열 순서로 가려지는 모든 경우, BP grant 누락, Notify 위치/순서와 원작 모션 대응까지 자동 증명한다고 설명하지 않는다.
- 설명용 산출물은 Examples/DodgeSpecialAttack_20261001 아래의 전체 소스 제안과 단계별 안내다. 게임 Source/BP/Content에 적용하거나 build/PIE 완료로 기록하지 않는다. Weak/Strong의 원작 motion 대응, 대각선 target, 비용, Notify frame, 영속 해금 producer는 확인된 것과 임시 authoring을 구분한다.

## 2026-10-01 — ARCH-72 공동 구현 안내의 임시 authoring과 검증 범위

- 전체 [소스와 구현 안내](Examples/DodgeSpecialAttack_20261001/GUIDE.md)를 작성했다. 16개 전체 h/cpp 제안, Source baseline hash 및 정적 대조 결과를 첨부했다. 설명 작업이며 게임 파일 적용/새 build/PIE는 수행하지 않았다.
- 즉시 따라 할 수 있는 Dodge point Notify 위치로 각 section local InputOpen=4 frame, InputCommit=8 frame, InputEnd=24 frame을 **어시스턴트 선정 임시 튜닝값**으로 제안했다. 원작 입력창 근거는 없다. 초기 회피 피드백, 한 칸 예약 구간, 뒤쪽 회복 교체를 검증하는 시작점이며 Montage authoring에 모아 저장한다. Open<Commit<End<section end를 유지하고 응답/오입력/회피 잘림을 조정 기준으로 삼는다.
- 30 fps 시간 환산 입력은 Saved/KZStaminaLockOnDodgeInspect.json의 dodge_combat_m1[0].frame_rate numerator=30/denominator=1, number_of_frames=32, play_length=1.0666667222976685이다. path는 Weapons/DualAxeSword/Shared/Combat/Evasion/Dodge/CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1이다. 이는 현재 UE 후보의 저장 감사/임포트 관측이며 원작 gameplay window 직접 metadata가 아니다. InGame 복제본의 실제 frame rate/길이는 Editor에서 다시 확인하고 절대 Notify 시간은 section start+local frame/FPS로 계산한다.
- Weak F/B→JustMoment, Strong F/B→RecklessRush와 L/R 양쪽 가족→동일 Off_DodgeAtk_L/R_M1, 대각선 RF/LF→F 및 RB/LB→B는 전체 입력 경로 시험용 **임시 콘텐츠 대응**이다. 원작 스킬/입력/대각선 규칙 확인 결과가 아니다. F 두 갈래부터 검사하며 현재 파일 수를 16 고유 모션이 있는 것으로 표현하지 않는다.
- 새 액션 비용은 None인 입력/몽타주 시험 구성을 명시했으며 원작 무비용으로 확정하지 않았다. 기존 X/Y 비용과 local per-node ApplyCost를 보존한다. 피해/무적/Cue/Save producer는 실제 소비 구현 시 닫는다.

## 2026-10-01 — ARCH-72 최소 변경 재검토: 기존 입력 경로로 방향별 Dodge 연결

사용자가 앞선 Dodge 제안의 변경량과 기존 구조 재사용을 재검토하도록 요청했다. 실제 ASC, Controller, Action/ComboAction, Dodge, Definition/grant Source를 읽었다. 이번 결과는 설계·설명이며 게임 Source/BP/에셋 적용 또는 build/PIE 완료가 아니다.

- 현재 UKZDodgeAbility는 이미 UKZComboActionAbility를 상속하며 EKZDodgeDirection/defaults/getter도 KZDodgeAbility.h에 있다. 공통 실행 추출, CanActivate 사전 검사, local Cost gate를 다시 구현하지 않는다. Montage Task/window/buffer/OwnerTagRequirements/ApplyEdge/TryActivateComboEntry/정상·취소 cleanup은 현행 기능을 재사용한다.
- 앞선 전체 16파일 제안에는 이미 존재하는 코드의 전체 사본, 타입 헤더 분리, editor validation 및 공통 입력·수명 보완이 함께 들어 있었다. 이 전체 교체와 IsDataValid 선행을 Dodge 추가의 최소 필수 단계로 삼은 설명을 대체한다. 독립 Dodge 실행기, 새 Task/Component/Manager/DataAsset/native DodgeAttack class를 만들지 않는다.
- 새 runtime KZDodgeTypes.h는 필수가 아니다. 현재 enum 정의 위치를 유지하고 Player/ASC header에서 필요한 경우 enum class EKZDodgeDirection : uint8; 전방 선언, 사용하는 cpp에서 기존 Dodge header include로 연결한다. 같은 UENUM을 두 곳에 정의하지 않는다.
- 방향별 최초 선택은 Controller 입력 adapter가 현재 Move action value로 Player의 지역 방향 계산을 호출하고, ASC의 granted Spec을 읽어 Dodge defaults 방향이 일치하는 Spec Handle 하나를 찾는 제안으로 축소한다. 선택은 Game Thread에서 목록 lock 안에서 하고 handle만 보관해 이후 기존 입력 경로에 전달한다. 없는/중복 방향이면 실패하며 invalid handle을 일반 A fallback으로 넘기지 않는다.
- 기존 AbilityInputTagPressed(InputTag)에 선택적인 FGameplayAbilitySpecHandle RequestedHandle 인자를 추가하는 안을 권장한다. 기본값은 invalid handle이며 기존 X/Y 호출은 유지된다. 유효 handle이 있으면 기존 active/inactive 두 순회 모두 해당 Spec만 검사하고, 기존 exact InputTag 검사도 유지한다. 기존 Spec 입력 기록/engine TryActivateAbility/GAS press/동일 Spec InputEnd restart 경로를 그대로 쓴다. 별도 TryActivateDirectionalDodge public 함수와 그 안의 restart/activation 복제는 필요하지 않다.
- 이 안은 앞선 8 Dodge graph-only grant 계약을 변경한다. Dodge 8개는 모두 기존 Input.Action.A를 binding하며 RequestedHandle이 한 press의 variant를 선택한다. A Completed/Canceled도 기존 tag release/cancel 경로로 연결한다. 해금형 특별 공격 Entry는 계속 InputTag 없는 graph-only grant다. 방향별 input tag 8개와 영속 input-owner map은 만들지 않는다.
- 같은 방향 재입력은 현행 InputEnd 계약을 유지한다. 다른 방향 target은 source InputEnd 전 GAS Action block으로 거절되고 InputEnd 뒤에는 새 Action의 기존 cancel 정책으로 source를 정리한다. 같은 Spec restart는 cancel 전에 기존 CanActivate/Cost/data 승인을 확인하는 작은 공통 보완을 유지한다. 비용 실패에 source를 먼저 취소하는 현행 순서를 완성 동작으로 삼지 않는다.
- X/Y Begin은 기존 Combo Command를 먼저 평가하고 소비 여부로 신규 activation 및 같은 Spec restart를 중재하는 공통 보완이 여전히 필요하다. 소비돼도 기존 active Spec의 GAS press 수명은 유지한다. 즉시 특별 공격 전환 후 같은 press가 일반 공격을 새로 시작하는 충돌을 제거하며 새 전투 이벤트 계층을 만들지 않는다.
- TryActivateComboEntry는 기존 handoff를 유지한다. graph-only target의 InputPressed=false와 실제 같은 binding을 가진 handoff의 입력 소유권 정리는 공통 입력 계약 보완으로 설명한다. 기존 Weak/Strong/Charge 회귀를 생략하거나 현재 bool 인자가 실제 입력 binding까지 증명한다고 설명하지 않는다.
- 해금은 기존 Edge OwnerTagRequirements와 target ActivationRequiredTags, GE 소유 tag로 표현한다. 새 해금 상태/manager나 Edge schema를 추가하지 않는다. tag 사전 등록은 기존 native tag 영역 또는 프로젝트 tag 설정으로 가능하다. 영속 Save producer는 별도 실제 구현 경계다.
- IsDataValid 자동 검사 및 무관한 정리는 별도 보강 단계로 둔다. entry/section/grant/방향 중복은 실제 BP/DataAsset 설정과 현행 CanActivate에서 확인한다. UnPossessed Action 취소 누락은 기존 Character 수명 함수의 작은 공통 보완으로 따로 제시하며 새 cleanup 시스템을 만들지 않는다.

변경 범위: 새 runtime 파일/타입은 0개인 구성이 가능하다. 주요 Dodge 추가는 Controller 입력 연결/지역 Spec 선택, Player 지역 방향 계산, 기존 ASC press의 handle 필터다. X/Y 소비 및 handoff 입력 기록은 기존 ASC/ComboAction/Controller의 공통 보정이고, montage/node/edge/해금은 기존 에셋 데이터다. 8개 BP 요구를 유지하며 하나의 Ability로 몰래 합치지 않는다. 이후 안내는 전체 파일 교체보다 현재 Source를 기준으로 한 작은 diff로 제공한다.


## 2026-10-01 — ARCH-72 추가 축소: 현행 InputEnd 계약이면 X/Y 중재 변경 불필요

위 최소 변경 검토 뒤 현행 native 제어 흐름과 설치 UE GAS block 조건을 추가 확인했다. 같은 날짜 위 절의 “X/Y 소비 반환/command 선행이 여전히 필수” 결론은 아래 현행 계약 범위에서는 대체한다.

- 현재 UKZActionAbility는 InputEnd 전 Ability.Action을 block하고 일반 Attack은 Ability.Action.Attack AssetTag를 가진다. UE AreAbilityTagsBlocked는 부모 tag를 포함해 이를 거절한다. 현재 RouteAttackInput Begin의 generic press → Combo Command 순서에서, Dodge InputEnd 전 일반 공격 activation은 거절된 뒤 살아 있는 Dodge가 기존 Command/Edge로 특수 공격을 예약·실행할 수 있다.
- 현재 ComboAction ProcessMontageNotify(InputEnd)는 Pending을 비우고 ComboWindowPhase를 Closed로 만든 다음 Action block을 해제한다. 이후 새 X/Y Begin은 일반 공격 진입이고 Dodge Begin Edge는 닫힌 창에서 실행되지 않는다. InputEnd Notify의 RunHeld는 별도 authored InputEnd Edge를 동기적으로 평가하는 기존 경로다.
- 따라서 “InputEnd 전 특별 공격, InputEnd 뒤 일반 공격”이라는 현재 경계에서 bConsumed event/Begin 순서/bAllowNewActivation을 필수 추가하지 않는다. 기존 X/Y 흐름과 ComboAction handler를 유지하고 Dodge node의 Begin Edge/owner tag/target Entry 데이터를 추가하는 것이 더 작은 제안이다. 앞선 입력창 종료 뒤에도 특수 Edge를 우선해야 한다는 가정은 현재 소스에 없었다.
- 향후 일반 Action을 허용하면서 같은 X/Y를 다른 열린 Edge가 우선 소비해야 하는 실제 정책으로 변경할 경우 command 선행/소비 중재를 다시 검토한다. 해당 기능을 현재 Dodge의 필수 기반으로 선행 추가하지 않는다.
- 최소 공통 보정은 graph-only 특수 target에 InputPressed를 기록하지 않는 기존 TryActivateComboEntry 분기와, 같은 Spec restart의 비용/data 사전 승인이다. 현재 DynamicSpecSourceTags의 작성자는 CharacterDefinition grant의 InputTag 하나뿐이라는 계약을 확인했다. 일반 binding/Charge의 입력 소유권 재설계는 Dodge 특수 target 구현과 구분해 회귀/별도 수정하며 전체 CommandTag API 변경을 무조건 요구하지 않는다.
- 핵심 Dodge 수정은 기존 Player/Controller/ASC 세 클래스의 h/cpp에 한정할 수 있다. 기존 Dodge/ComboAction/ComboDefinition/CharacterDefinition native class와 schema는 유지한다. tag 사전 등록은 기존 경로로 하고 UnPossessed 취소는 Character의 별도 작은 수명 보완이다. 새 runtime 파일은 필요 없다.

이 결론은 현행 native Action block/InputEnd 정책이 BP에서도 유지된다는 전제의 정적 제어 흐름 분석이다. BP의 override와 실제 입력창/방향/비용/Release/Cancel은 적용 후 PIE로 확인해야 한다. 이번에 runtime 동작을 실행 관측한 결과는 아니다.



## 2026-10-01 — ARCH-72 최소 Dodge의 구체 코드 안내와 상시 최소 변경 방침

- 사용자 최신 방침을 [AGENTS.md](../../AGENTS.md), [UE5_ENGINEERING_RULES.md](UE5_ENGINEERING_RULES.md), Router 하단에 기록했다. 모든 구현·기능 추가에서 현재 구조/기능을 우선 재사용하고, 새 구조는 기존 경로로 해결되지 않는 실제 책임·수명·소비자와 더 작은 대안이 부족한 이유를 확인한 뒤 제안한다. 최신 MD 상태/스타일 확인과 실제 Source 대조를 매 작업의 기준으로 유지한다.
- [DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md](DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md)와 [변경 부분 patch](Examples/DodgeMinimal_20261001.patch)를 작성했다. 바로 위 추가 축소 계약을 구체화한 사용자 적용 안내다. 기존 Player/Controller/ASC h/cpp 6파일과 Character UnPossessed 1파일만 대상으로 하고 새 runtime 파일/클래스는 0개다. 현 ComboAction/Dodge/Definition native 코드는 교체하지 않는다.
- 현재 입력값 → Player의 지역 inverse-yaw/atan 방향 계산 → Controller의 A-bound Dodge defaults/방향 Spec 선택 → 기존 ASC press의 optional RequestedHandle 순서다. ASC active/inactive 두 순회에 handle 필터를 넣고 exact input tag 조건을 유지한다. 지역 값만 만들며 Main AnimInstance의 velocity 각도를 입력 방향으로 재사용하지 않는다.
- 같은 Spec InputEnd restart는 Cancel 전에 기존 CanActivate/비용/data 승인을 조회하고 Cancel 뒤 Spec이 없어졌거나 active이면 중단한다. graph-only target의 InputPressed=false는 현재 DynamicSpecSourceTags 작성자가 grant InputTag뿐이라는 소스 계약을 이용한 작은 보완이다. 별도 입력 owner manager를 만들지 않으며 기존 binding/Charge의 입력 수명은 회귀 확인 대상으로 둔다.
- X/Y generic press → ComboCommand 순서와 현 ComboAction event/window/buffer/Edge/handoff는 유지한다. InputEnd 전 Action block, InputEnd 때 Closed 후 unblock이라는 native 정책을 BP가 유지하는 조건이다. Dodge 8 grant는 모두 A, 특별 공격 grant는 InputTag empty, 해금은 기존 owner/activation 요구와 GE다. Save/피해/무적은 이번 연결의 구현 완료 범위가 아니다.
- 실제 검증: 설치 UE 5.8 API와 현행 소스/표적 asset 존재를 확인했고 patch 문맥 check가 통과했다. 이번 작업 시작 대비 Source 9개 SHA256이 모두 동일하다. 게임 C++/BP/Config/에셋에 제안을 적용하지 않았고 build/PIE도 수행하지 않았다. 임시 Notify 4/8/24 frame·특별 공격 모션 대응의 출처/영향/조정 조건은 새 안내에 명시했다.

## 2026-10-01 — ARCH-73 제안: LockOn 복귀의 이동 포즈를 기존 입력·gait 정책으로 선택

- [근거] 실제 패드 입력을 읽기 전용으로 수집한 PIE에서 L 입력 약 -91.35도/세기 1/이동 허용 true/컴포넌트 ResolvedGait Run인데 공격 종료 첫 관측의 AnimInstance 방향은 약 0도, LocomotionGait는 Walk였다. 8프레임 뒤 방향 -82.03도와 Run으로 바뀌었다. Raw 자료는 `Saved/ImportReports/WeakAttackLockOnExit_20261001_raw.json`, 요약은 같은 이름의 `_summary.json`이다. 전진 속도가 남아 있었으므로 이 사례는 속도 0 fallback이 아니다.
- [제안 지위] 다음 계약은 사용자 적용용이며 구현 완료/수정 효과 검증을 의미하지 않는다. 현재 actual-velocity 각도·속도 hysteresis 구현 기록은 이번 코드가 적용되기 전까지 현행이다.
- [책임/변경 범위] 기존 `UKZAnimInstance::UpdateKinematics_AnyThread`의 지역 계산과 `UpdateLocomotionSelection_AnyThread` 한 분기만 수정한다. 새 runtime 파일/멤버/태그/상태 수명/공통 helper는 없다. `KZPlayer`의 raw intent, ASC/Ability 입력·취소, CMC 정책은 재사용한다.
- [방향 제안] 지상·유효 이동 허용 입력·LockOn일 때 `MovementDirectionAngle`은 기존 snapshot의 `MoveInputWorld`를 snapshot Actor Yaw로 역회전한 입력 방향각이다. 나머지 조건에서는 현 실제 속도각/fallback을 유지한다. 이 필드는 이 조건에서 순수 속도 관측값이 아니라 이동 포즈 선택값이 된다. `VelocityWorld/Local`, `GroundSpeed`, `AccelerationWorld`, `bIsMoving`은 계속 실제 운동 관측이다.
- [gait 제안] 지상 유효 입력의 LockOn 포즈는 기존 LocomotionComponent가 확정한 `ResolvedGait`를 사용한다. 스틱 세기/요청/상한으로 이미 Walk/Run을 판정하므로 새 임계값을 추가하지 않는다. 비LockOn의 현재 실제 속도 hysteresis와 기존 Sprint 결과는 유지한다. 가속/감속 중에도 의도된 gait를 즉시 표시한다는 표현 정책 변경이며 발 미끄러짐/일반 방향 변경을 후속 QA한다.
- [작성자/소비자/스레드] Player 입력 어댑터→LocomotionComponent가 기존 의도를 쓰고, GameThread가 기존 FKZAnimGameThreadData에 복사한다. AnyThread 함수는 const snapshot만 읽어 현재 프레임의 포즈 각도/gait를 작성한다. 실제 소비자는 현재 LockOn Walk/Run Blend Space 및 ABP gait 선택이다. worker에서 Actor/ASC를 새로 읽지 않는다. 지역 `const FVector InputLocal`은 함수 호출 안에서만 살고 Reset이 없다. 기존 관측 초기화/입력 해제·차단/Stop 이력/취소 수명을 재사용한다. 새로운 Player 전용 데이터나 미래 AI helper를 만들지 않는다.
- [수치/검증] 새 gameplay tuning literal이 없다. 기존 atan2의 기하학 각도와 기존 ResolvedGait만 쓴다. 수정안은 `Examples/LockOnRecoveryPose_20261001.patch`(기존 1파일 +12/-3)다. 실제 Git 루트의 `Khazan/Source/...` 경로로 문맥 검사와 변경 건수 확인이 통과했다. Source 적용/수정안 build/수정 후 PIE는 아직 없다. 방향 hunk→gait hunk 순서로 확인한 뒤 시각적 튐의 잔존 여부를 판정한다.

## 2026-10-02 — ARCH-74 Guard 직접 구현 계약

- 사용자 직접 구현 요청에 따른 착수 계약이다. 기존 `UKZActionAbility`의 InputEnd/block/cancel, ASC exact input Spec, LocomotionComponent constraint, GameThread snapshot, DefaultSlot/Inertialization을 재사용한다. 유지·해제·연속 피격은 Combo edge 수명과 달라 `UKZGuardAbility` 한 실행 소유자만 추가한다. Guard Manager, CombatComponent, 새 Task/입력 parser는 만들지 않는다.
- Guard 활성화/유지 Cost는 없다. GuardState GE의 `State.Guarding`과 Walk 상한 constraint는 held 수명에만 적용하고 Release/Cancel/실패/EndPlay에 해당 handle만 해제한다. release 뒤 Guard_End 회복 중에는 방어하지 않는다. InputEnd부터 다른 Action이나 종료 중 이동에 즉시 양보한다.
- 공유 방어 사실의 작성자는 Ability가 적용한 GE, 소비자는 GT Anim snapshot과 ASC의 `TryGuardHit`다. AnimInstance bool은 읽기 전용 표현 복사이며 worker가 ASC를 읽지 않는다. LockOn Guard 방향은 기존 입력 기반 각도, 비LockOn은 F를 사용한다. 이동 제약은 기존 Walk 설정을 사용한다.
- 미래 공격 판정은 방어 가능 공격/공격 방향 등을 먼저 검증한 뒤 피격자의 `TryGuardHit(StaminaDamage, Attacker)`를 호출한다. true면 해당 HP 피해를 적용하지 않는다. 소모량은 공격 데이터 작성자의 값이며 고정 가드 Cost로 추정하지 않는다. 부족한 스태미너/비활성/해제/잘못된 피해량은 false다. GuardBreak·HP·적 hit trace는 이번 runtime 범위가 아니다.
- 일반 Guard 원작 `SB_Kazan_DualAxeSword_Com_Guard_Normal_New.json`, `GuardSkillInfo.GuardStaminaRecoveryDelayTime=0.5 s`를 성공 지연으로 사용한다. 원작 cancel timing을 기존 PlaybackPlan 역매핑으로 변환한 InputEnd는 프로젝트 계약 대응값이며 원작 엔진 내부 판정과 동일하다고 단정하지 않는다. 새 블렌드는 명시된 임시 표현 튜닝으로 관리한다. 에셋의 현행 재생률·Root·0.01 mesh scale을 유지한다.
- 이 절 작성 시점은 구현 전이다. 실제 변경/빌드/런타임 결과는 완료 절에 별도로 추가한다. 시작 스냅샷은 `Saved/GuardImplementation_20261002/Before/Manifest.json`이다.


## 2026-10-02 — ARCH-74 Guard 적용·검증 완료

- 앞선 착수 계약을 실제 Source/BP에 적용했다. 독립 held·release·반복 성공 수명은 UKZGuardAbility 하나, 공유 방어 상태는 GE State.Guarding, 입력 held 사실은 기존 Spec.InputPressed, 이동 상한은 기존 constraint handle, 표현은 GT snapshot이다. 미래 피해 callback에 제공하는 ASC.TryGuardHit만 추가했으며 공격별 StaminaDamage 작성 책임은 호출자에게 남겼다.
- Start/성공/End는 하나의 Montage/기존 PlayMontageAndWait를 사용하고 매 섹션 Task/instance ID를 갱신한다. Release 즉시 자기 GE/Walk handle을 제거하고 InputEnd에서 End 전환/회복 중단을 처리한다. 전체 17 sequence의 marker와 실제 Montage branching event의 차이는 [Guard 현행 문서](GUARD_IMPLEMENTATION_20261002.md)에 명시했다.
- 실제 검증은 cold build, 새 프로세스 asset/pose audit 및 실제 DevMap PIE의 held/8방향/Cost/연속 성공/release/공격·이동 취소/자연 종료/UnPossess다. Success 결과를 Metadata/GuardImplementation_20261002/RuntimeResult.json에 보존했다. 적 hit/HP/방어 각도/GuardBreak·JustGuard/멀티플레이/화면 QA를 구현 완료로 확장하지 않는다.
- 원작 직접 확인 regen 지연 0.5초, 원작 기반 시간축 변환 InputEnd, 명시된 임시 Montage/ABP 0.1초와 기존 복귀 0.24초를 구분했다. 기존 스케일/재생 보정·Dodge/콤보 코드를 유지한다.


## 2026-10-06 — ARCH-74 검증 범위 정정 및 Guard 표현 에셋 수리

- ARCH-74의 실행/공유 상태/입력/이동/스레드 책임은 유지한다. 10월 2일 “8방향 통과”는 AnimInstance 각도와 SampleData 배치 검사였으며 실제 Blend Space cache/mesh pose 검사 완료를 뜻하지 않는다.
- 실제 PIE에서 Guard BS의 복제된 파생 segment index와 교체한 SampleData 순서 불일치를 확인했다. 0도 실제 cache index2/L/weight1 디버거 증거를 확보한 뒤 해당 Guard BS의 UBlendSpace::ResampleData만 적용했다. 실행 구조·snapshot·source pose·재생률·스케일을 바꾸지 않았다.
- 기존 개발 전용 test 확장/cold build/saved asset reload 뒤 8방향 실제 clip 및 12 checkpoint×227본 mesh pose, 뒤 경계/상대 yaw/nonLock F/Loop와 기존 Guard gameplay 검사가 통과했다. runtime class/공통 helper/미사용 관측 상태를 추가하지 않았다.
- 실제 적용/검증과 물리 입력·연속 화면·적 hit/HP의 미검증 구분은 [Guard 현행 문서의 2026-10-06 절](GUARD_IMPLEMENTATION_20261002.md) 및 Metadata/GuardLocomotion_20261006/RuntimeResult.json이 최신이다.

## 2026-10-06 — ARCH-74 이동 입력 중 Guard Start/End 생략 계약 (적용 전)

- 사용자 직접 수정 요청: 유효한 이동 입력을 유지한 Guard press는 Start 없이 GuardLocomotion, release는 End 없이 기본 로코모션으로 전환한다. 정지 상태에서 시작한 Start/End 중 이동 입력이 들어와도 해당 모션을 빠져나온다. 앞선 InputEnd까지 이동 복귀를 기다리는 정책은 이 Start/End 이동 전환 범위에서 대체한다.
- 이동 여부는 기존 LocomotionComponent의 허용된 InputAmount로 판단한다. 속도, 새 deadzone, 새 held/moving 상태 사본을 추가하지 않는다. Start 중 이동은 montage task만 정리하고 Guard GE/Walk constraint/Ability 수명은 유지한다. release/End 중 이동은 기존 소유 handle과 Ability를 정리한다.
- Guard 성공 반응은 held 상태에서 이동하더라도 계속 재생한다. 이동 중 release에는 방어와 Walk 제한을 즉시 해제하고 End 없이 복귀하며 이미 적용한 성공 비용은 되돌리지 않는다. InputEnd marker/정지 시 Start·End 절차/기존 관성화 설정은 재사용한다.
- 변경 대상은 기존 Guard cpp와 개발 전용 PIE test다. 새로운 runtime 파일·클래스·공통 helper·BP·애니메이션 에셋은 필요하지 않다. 현재는 계약 기록이며 실제 적용/build/PIE 결과는 후속 절에 구분한다. 시작 백업: `Saved/GuardMovementPolicy_20261006/Before/Manifest.json`.


## 2026-10-06 — ARCH-74 이동 Start/End 생략 적용·검증 완료

위 이동 입력 정책을 기존 Guard cpp 3함수에 적용했고 cold build/최종 DevMap PIE Khazan.Guard.PIE Success(01:32:08.870 UTC)를 확인했다. 새 상태 소유자/runtime 파일은 없고 GE/Spec/constraint/Task/snapshot/ABP 책임을 유지한다. Start 생략은 held 수명을 유지하며 release/End 이동은 자기 수명을 정리한다. 정지 절차와 held 성공 반응/비용은 유지한다. 상세 데이터 계약·Task 중단 순서·개발 test 관측 범위 수정·실제 증거·미검증은 [Guard 정본의 이동 Start/End 절](GUARD_IMPLEMENTATION_20261002.md) 및 Metadata/GuardMovementPolicy_20261006/RuntimeResult.json이다.

## 2026-10-06 — ARCH-74 다른 동작 중 held Guard 자동 활성화 계약 (적용 전)

- 사용자 직접 수정 요청: 다른 동작 중부터 가드 입력을 유지하면 기존 Action InputEnd 또는 자연 종료로 활성화가 허용되는 첫 입력 update에서 Guard를 실행한다. 불허 상태를 무시해 이전 동작을 강제로 중단하지 않는다. 입력을 먼저 release/cancel하면 이후 자동 실행하지 않는다.
- 실제 디스크 Source의 Guard binding은 이미 Triggered이며 IA/IMC trigger 목록은 비어 있다. 이를 유지하고 기존 Input_GuardPressed에서 State.Guarding이면 일반 press 전달을 생략한다. 방어 중이 아니면 기존 ASC press를 재시도한다. 일반 press의 InputEnd 동일 Spec restart를 지속 입력의 Guard 유지에 반복 적용하지 않게 한다.
- 별도 held bool/queue/timer/ASC API/Ability 변경은 추가하지 않는다. Enhanced Input 현재 Triggered가 held 의도의 작성자, 기존 ASC activation/block/cancel이 소비·실행 허가, Guard GE가 방어 사실의 소유자다. Controller는 현 Pawn ASC를 매번 조회한다. 기존 Completed/Canceled/UnPossess cleanup을 유지한다.
- 코드 변경 대상은 기존 Controller cpp 콜백 1개와 개발 전용 test다. 현재 실제 키는 LeftShift/Gamepad_LeftShoulder(LB)이고 사용자 표현 RB와 다르므로 키 변경 선호만 비동기로 확인 중이다. 핵심 held 동작 수정은 키와 독립적으로 진행한다. 백업: Saved/GuardHeldInput_20261006/Before/Manifest.json. 현재는 적용 전 계약이며 build/PIE는 후속 기록으로 구분한다.


## 2026-10-06 — ARCH-74 held Guard 자동 실행 적용·검증 완료

위 계약을 Controller Input_GuardPressed 한 콜백에 적용했다. 현재 Triggered binding과 Guard GE의 State.Guarding을 재사용해 불허 중 재시도/방어 중 재시작 방지를 구분한다. 새 입력 상태 사본·queue·timer·ASC API는 없다. 기존 InputEnd 허가/Guard 비용/취소·handle 소유 책임을 유지한다. cold build 후 실제 Controller binding callback을 쓰는 DevMap PIE Khazan.Guard.PIE가 03:02:36.401 UTC Success였다. 상세 함수·키·실제 검증 범위는 [Guard 정본의 held 입력 절](GUARD_IMPLEMENTATION_20261002.md) 및 Metadata/GuardHeldInput_20261006/RuntimeResult.json이다. 실제 키는 기존 LShift/LB이며 키 변경 선택에 별도 응답이 없어 IMC를 보존했다.

## 2026-10-06 — ARCH-75 Heal 직접 구현 착수 계약

사용자 직접 구현 요청이다. HP/MaxHP는 기존 KZAttributeSet에 추가하고 CharacterDefinition.InitialEffects의 instant GE로 MaxHP→HP=200을 초기화한다. 200과 Heal HP +100은 사용자 지정 임시 게임 설정이며 원작 검증 수치가 아니다. Player/Controller/AnimInstance에 체력 사본을 만들지 않는다. 무제한 물약으로 Cost/Cooldown/수량 상태가 없다.

Heal의 유한 실행·Notify 회복·InputEnd·취소는 UKZActionAbility 파생 UKZHealAbility 하나가 소유한다. 기존 GAS block/cancel, PlayMontageAndWait, exact Spec 입력, UnPossess/EndPlay cleanup을 재사용한다. 기존 LocomotionComponent Walk 상한 handle 하나를 실행 중 보유해 이동은 허용하고 종료/실패/취소에 해당 handle만 해제한다. Actor/worker/Ability에서 이동 정책을 중복 작성하지 않는다.

상체 전용 UpperBody Slot과 기존 포즈 cached source/LayeredBoneBlend를 ABP에 연결한다. Main AnimInstance의 새 Heal bool/태그 snapshot/helper는 없다. 기존 DefaultSlot/Guard/Locomotion/Stop/최종 Inertialization은 유지한다. 실제 하체/상체·CMC 이동은 개발 PIE에서 검증한다. 새 runtime 파일은 Heal h/cpp 2개이며 별도 Task/Manager/Component는 없다.

사용자 기존 에디터 PID9596 및 다른 프로젝트 작업 PID13632를 조작하지 않는다. 별도 C:/Users/user/Desktop/GitProject/Khazan_HealWork_20261006/Khazan snapshot에서 cold build/숨김 에디터 authoring/검증을 수행한다. 저장 에셋은 작업 시작 hash와 메인 경로가 여전히 일치할 때만 적용한다. 실행 중 메인 DLL 교체/LiveCoding은 하지 않는다. 현재는 착수 계약이며 적용/build/PIE 완료는 후속 기록으로 구분한다.

## 2026-10-06 — ARCH-75 Heal Source 적용·격리 검증, 메인 반영 대기

실행자는 UKZHealAbility 한 클래스(h/cpp 2파일)이며 기존 Action/ASC/InputTag Spec/Definition/LocomotionComponent/엔진 Montage task를 재사용했다. 공유 HP/MaxHP는 AttributeSet, 초기·회복량은 GE, 회복 1회·instance ID·자기 Walk 제약 수명은 Ability가 소유한다. Main AnimInstance/helper/FSM/수량·HP 사본은 추가하지 않았다. 무제한·무비용 물약은 full HP에서도 모션을 실행하고 HP0에서는 실행하지 않는 현 프로젝트 정책이다.

UpperBody Slot/LayeredBoneBlend/cached action base를 작업 ABP에 연결했다. 기존 DefaultSlot/Guard/Locomotion/Stop/최종 Inertialization은 보존했다. 200/100은 사용자 지정, Notify/Blend는 명시된 임시 authoring 값이다. 메인 Source 적용, 기존 Build.cs의 격리 cold build, Heal PIE Success(05:19:29.000 UTC)/Guard 회귀 Success(05:20:57.182 UTC)/새 saved reload를 확인했다.

메인 Content는 열린 editor의 SK_Player 파일 잠금으로 아직 시작 hash이며 검증 파일 10개를 별도 준비했다. 숨김 helper가 메인 editor exit 후 Source/asset 충돌 재확인→선택 적용→메인 build한다. 최신 실제 단계는 Metadata/HealImplementation_20261006/ApplyStatus.json이며 Complete 전에는 메인 적용 완료가 아니다. 상세 Source·변수·cleanup·에셋·출처·검증은 [Heal 정본](HEAL_IMPLEMENTATION_20261006.md)이다.

## 2026-10-06 — ARCH-75 메인 실제 적용·직접 테스트 준비 완료

사용자 후속 메인 반영 지시로 clean/PIE 없음 상태의 메인 editor를 정상 종료하고 검증된 10개 에셋을 선택 적용했다. 메인 cold build Succeeded/ApplyStatus Complete(05:48:35.668 UTC), 새 PID27568 DevMap에서 native Heal/GA·GE/input·grant/ABP UP_TO_DATE의 저장 reload를 확인했다. Source·원본 clip·기존 책임 계약은 유지했다. 앞선 pending은 역사적 시점이며 현재 메인 적용은 완료다. gameplay 자동 테스트는 계속 격리에서 수행한 범위, 물리 입력·연속 화면은 사용자 직접 QA로 구분한다. 정본·증거는 [Heal 문서](HEAL_IMPLEMENTATION_20261006.md)의 메인 완료 절과 Metadata/HealImplementation_20261006/MainAppliedResult.json이다.
 
## 2026-10-06 — ARCH-76 Heal 무기 수납·발도 착수 계약

사용자 직접 구현 요청. ARCH-75의 Heal Ability/HP GE/Walk constraint/ASC 입력·Action 취소를 재사용한다. 기존 BP Player 무기 컴포넌트와 Skeleton BackPack 부착점을 사용하며 별도 Equipment Component/State/Ability는 생성하지 않는다. Heal 실행이 변경 전 부착 parent/socket/relative transform을 저장하고 정상·취소·실패·UnPossess에 자기 변경만 복구한다. 공유 장비 상태 bool을 선행 추가하지 않는다.

기존 UpperBody Montage에 UnArmed→Heal을 연결하고 Arms Slot Montage Armed를 이어 재생한다. 상체와 양팔의 실제 마스크가 다르므로 발도 Montage 1개·Arms 합성 노드만 추가한다. 한 Heal Ability가 기존 PlayMontageAndWait를 단계별로 사용한다. 발도 시작에 기존 SetInputEnded로 Action 차단을 풀어 Dodge/Attack/Guard에 양보한다. 취소 종료 후 이전 montage instance ID만 즉시 정리해 새 액션을 멈추지 않는다. 미래 피격 실행자는 기존 Action cancel 또는 ASC cancel 경로를 써야 하며 이번에는 미구현 피해 시스템을 만들지 않는다.

클립은 기존 Armed/UnArmed를 InGame/DAS/Equip으로 UE rename한다. source pose·재생률·Player 0.01/무기 0.009는 보존한다. 부착 타이밍은 실제 손·등 궤적 확인 후 Montage notify로 소유하며 원작 직접 timing을 못 찾으면 명시된 임시 표현값으로 기록한다. 작업·PIE는 별도 Khazan_HealWeaponWork_20261006에서 수행한다. 이 절은 구현 전이며 결과는 후속 실제 검증 절로 구분한다.

## 2026-10-06 — ARCH-76 Heal 수납·발도 실제 적용·검증

ARCH-76 착수 계약을 기존 Heal h/cpp에 적용했다. 두 무기 attachment snapshot은 Heal 실행만 소유하고 HP/장비 공유 bool/AnimInstance 상태 사본은 추가하지 않았다. 첫 Montage 완료에 Arms Montage를 같은 Ability/엔진 Task로 시작하고 Walk handle 반환·InputEnd unblock, 취소에 원래 attachment와 이전 montage instance만 정리한다. 새 runtime 파일/클래스0이다. Animation graph는 기존 상체 cache 뒤 Arms cache/Slot/Layer5노드, Armed/UnArmed는 InGame/DAS/Equip으로 실제 이동(기존 참조0/old file2개 제거)했다.

격리 stock cold build/실제 Heal PIE(06:29:18.543 UTC)·Guard 회귀(06:31:27.946 UTC)/saved reload, 메인 선택 package7개+old paths2개 제거/hash/cold build(06:35:05 UTC)를 확인했다. 물약 중 Walk/발도 일반 gait, 하체·몸통·목·머리의 base pose·Armed 양손, X/Y/Dodge/Guard·forced cancel/회복·attachment/UnPossess cleanup을 검사했다. 실제 적 hit는 아직 실행자가 없고 기반 취소 경로만 검증했다. 현행 상세·수치·제한·메인 reload는 [Heal 수납·발도 정본](HEAL_WEAPON_PRESENTATION_20261006.md)과 Metadata/HealWeapon_20261006을 따른다. 기존 Architecture 계층/ASC 입력·태그 계약을 변경하지 않았다.
## 2026-10-06 — ARCH-77 첫 몬스터 StateTree/기존 ComboAction 수직 구현 계약

- 사용자 직접 구현 요청의 범위는 DevMap의 Swordsman/SwordShield/HeavySwordsman/HalberdElite 감지·배회·전투 진입·접근·대치/횡이동·단일/연속 공격 애니메이션이다. 피해/피격/적 Guard 성공/적 HP 소비는 연결하지 않는다. 이번 절은 구현 착수 계약이며 build/PIE 완료 기록이 아니다.
- ARCH-43/v3의 첫 Monster StateTree 기본안을 유지한다. 신규 runtime 파일은 AIController h/cpp와 StateTree task/condition h/cpp 네 개로 시작한다. StateTree가 Idle/Alert/Chase/Standoff/Attack을 선택하며 별도 FSM·Manager·행동 enum 멤버의 두 번째 상태 원본을 만들지 않는다. 노드의 enum은 편집 시 작업 종류 선택이며 현재 gameplay 상태 사본이 아니다.
- AIController는 엔진 Sight perception·focus·navigation과 기존 Locomotion intent token의 작성 권한을 소유한다. 이동 태그 차단은 기존 permission event로 navigation을 즉시 멈추며 허용 시 현재 StateTree 작업이 재요청한다. 원본 move 의도는 active path의 다음 점에서 관측해 기존 Locomotion snapshot으로 전달한다. CMC가 실제 navigation 이동/회전을 담당한다.
- StateTree task instance는 자기 대기 시간·nav 목표·선택한 Ability Spec handle만 보관한다. 기존 Character ASC/grants와 UKZComboActionAbility/PlayMontageAndWait가 공격 수명·Montage·콤보 전이·취소를 소유한다. AI는 기존 ASC SubmitComboCommand로 연속 공격 의도만 제출하고 montage frame/section jump를 직접 제어하지 않는다. 종료/실패/UnPossess/EndPlay에서 자기 nav/command/spec/intent 권한을 정리한다.
- AKZMonster의 기존 class defaults에 네 병종의 실제 소비 설정과 Ability 후보만 추가한다. 새 MonsterDefinition/AttackAbility/AnimInstance/공통 helper는 선행 생성하지 않는다. 기존 CharacterDefinition/AssetData registry를 재사용하고 새 Animation BP는 UKZAnimInstance의 GT snapshot/rotation mode/velocity를 읽는다.
- 원작 조사 결과는 Metadata/MonsterAI_20261006/OriginalSkillAudit.json이다. SubStateInfos.SkillAnimation/AnimPlayRate/AnimBlendAlpha와 SkillEventMap→xxChangeNextStepFunc→AC notify index 및 저장 PlaybackEventTimes의 dilation 변환 시각을 기록한다. 조건부 콤보의 가능한 단계 순서를 사용하되 원작 AI의 선택 확률·피해/상태 조건 전체를 재현했다고 하지 않는다.
- 원작 AIDataAsset의 참조는 CB에서 확인되지만 해당 원본 AI 데이터/실행 코드는 현재 표적 자료에 없다. 감지/기억/공격 거리/대치 주기/배회 반경/행동 비율 및 이동 가감속·회전 설정은 임시 튜닝값으로 owner 설정에 모으고 이유·단위·검증 기준을 후속 정본에 기록한다. Player 0.01 scale을 Enemy에 적용하지 않고 기존 Enemy assembly scale/rig을 보존한다.
- 새 격리 프로젝트 Khazan_MonsterWork_20261006에서 asset authoring/build/PIE를 수행한다. 메인 사용자 에디터에는 자동 gameplay 입력을 주지 않는다. 선택 asset/hash 검증·정상 재시작 후 메인 DevMap 전달을 별도 완료 기록으로 남긴다.

## 2026-10-06 — ARCH-77 첫 4종 몬스터 실제 완료

ARCH-77의 StateTree 선택/AIController perception-focus-nav/공통 Locomotion intent/기존 ComboAction 실행 경계를 실제 적용했다. 새 runtime4파일, 기존 Monster 설정/armor leader pose, definition tags4/registry·데이터를 사용한다. Blueprint 애니메이션은 기존 Main AnimInstance의 GT snapshot을 소비하며 전투 수명 사본/Monster AttackAbility를 생성하지 않았다. task 자기 nav/command/spec·controller delegate/intent/target cleanup을 실제 PIE로 검사했다. 첫 공격 정책은 저장 원작 패턴·event 시간과 명시된 임시 AI 설정을 구분한다.

격리 제품 build/Monster·Heal·Guard PIE 및 메인 선택137package/hash/cold build·PID11000/DevMap saved reload가 완료됐다. 후속 현행 정본은 [MONSTER_AI_IMPLEMENTATION_20261006.md](MONSTER_AI_IMPLEMENTATION_20261006.md) 최신 완료 절과 Metadata/MonsterAI_20261006이다. Damage/CombatResponse/Guard hit producer/death·원작 AI 전체 복원이 완료된 것으로 해석하지 않는다.

## 2026-10-07 — ARCH-78 발견 전 대기 루틴·대화 짝·실제 이동 포즈 보완 착수

사용자 직접 수정 요청이다. ARCH-77의 IdlePatrol에서 정지/배회를 합친 정책을 대체한다. Idle은 정지한 원작 Basic Loop 대기와 발견 시 대응 End의 유한 완료이고 Patrol은 별도 이동 작업이다. Swordsman은 사용자 지정 Guard/Basic03/Search/Sit01 및 Talk01/02 쌍을 정확히 사용한다. 다른 병종은 자기 skeleton의 저장 자료에서 Loop/End가 모두 존재하는 루틴만 구성한다.

신규 runtime 파일/Ability/AnimInstance/Manager 없이 기존 CharacterDefinition에 실제 소비되는 루틴 설정을 작게 추가하고 기존 초기 grant/ComboDefinition/ComboAction/엔진 Montage Task를 사용한다. Loop의 Montage section은 자기 반복, 발견 명령은 기존 combo command Release edge로 같은 Montage의 End에 진입한다. AI가 직접 MontageJump/pose frame을 구동하지 않는다. Idle task는 자기 spec과 End 요청 여부만 보유하며 End 완료 후 Root를 재선택한다. 이미 End로 준비한 경우 기존 공통 Alert를 중복 실행하지 않는다. 정상/취소/대상 상실/UnPossess/EndPlay cleanup은 기존 spec/nav/command 경로를 따른다.

대화는 level의 상호 partner 참조·상반 역할01/02가 모두 유효하고 두 definition에 해당 역할이 있을 때만 선택한다. pair 중 한쪽 발견은 둘의 전투 진입을 알리고 각자 대응 End를 끝낸다. 파트너 상실/UnPossess는 남은 쪽이 End 후 solo로 복귀한다. 별도 그룹 Manager/전역 대화 상태/두 번째 AI FSM은 없다. instance의 Patrol 선택은 배치 설정이고 현재 행동 사본이 아니다.

이동 증상은 native 실제 속도·AnimInstance 갱신·BlendSpace 입력/sample/time/mesh pose를 분리 검증한다. 10월6일 CMC 이동/상태 통과를 걷기 클립·발 고정 검증으로 확대하지 않는다. 원작 clips/루틴 순서/재생률 근거와 FK 발 접지 궤적에서 계산한 속도, 임시 표현 설정을 구분한다. CMC·기존 Locomotion snapshot/worker 경계를 유지하고 Player .01/기존 gameplay·원본 Art clip을 변경하지 않는다. 작업/검사는 기존 별도 MonsterWork에서 하고 메인 PID7220/다른 SnowWork를 조작하지 않는다. SourceBaseline/DebuggerEvidence는 Metadata/MonsterIdle_20261007이며 이 절은 적용 전 계약이다.

## 2026-10-07 — ARCH-78 실제 보행 검증 후 접지 처리 보완 계약

추가 검증에서 cardinal 걷기는 보폭/phase 보정으로 개선됐으나 대각선의 비선형 관절 블렌딩에는 실제 접지 발의 수평 잔차가 남았다. 재생률만으로 발 접지를 보장하지 못하므로 기존 엔진 AnimationWarping의 Foot Placement → Leg IK를 네 몬스터 ABP의 Walk branch에만 적용한다. 새 runtime class/component/task는 생성하지 않는다. 기존 세 Skeleton에는 실제 FK 발을 위한 Virtual Bone target 두 개씩만 추가하며 기존 bone/slot/socket/Art clip은 보존한다. InGame walk의 저장 FK 궤적에서 계산한 접지 구간을 contact curve로 기록한다. 이 구간과 엔진의 plant/trace/spring 설정은 원작 확인값이 아닌 계산/임시 표현 설정이다.

ARCH worker 경계를 지키기 위해 바닥/owner를 읽는 엔진 Foot Placement를 사용한 NPC ABP만 GameThread에서 update/evaluate한다. Main AnimInstance에 전투 상태를 넣지 않고 engine CanRunParallelWork의 실제 소비 설정 bRequiresGameThreadPoseEvaluation 하나만 둔다(초기 false; NPC author가 true, 엔진 스케줄러가 const로 읽음; gameplay reset 수명 없음). Player의 snapshot/parallel 경로는 유지한다. Walk 이후 Run/Stand 선택과 DefaultSlot을 두어 공격의 authored pose에는 접지 보정을 적용하지 않는다. 이 절은 추가 검증을 위한 계약이며 성공/메인 적용을 의미하지 않는다.

## 2026-10-07 — ARCH-78 실제 적용·메인 최종 완료

Idle 정지 Loop/대응 End, 선택적인 상호 Talk01/02, 별도 Patrol 및 combat Stand/실제 이동 포즈를 적용했다. 기존 Definition/grants/ComboAction/StateTree/nav/Locomotion/CMC/snapshot을 재사용하고 새 C++ runtime 파일·Ability subclass·Component·Manager는 없다. 기존 ComboAction을 설정한 data-only GA Blueprint16개/ComboDefinition16/Montage16은 실제 루틴 데이터로 작성했다. 추가 enum/struct는 Definition의 Role·Name·실행 class를 담으며 gameplay 상태 사본이 아니다. task가 자기 실행 handle/End 요청/weak partner, Controller가 target/focus/nav, Ability가 Loop/End 수명을 소유한다. NPC만 Foot Placement의 floor 읽기를 GT로 제한하고 Player scheduling=false를 실제 saved reload에서 확인했다.

PostPlacedNewNode 누락 원인과 최종32방향 asset-player/mesh/contact 및12FPS Halberd8 재검사, 자연 감지/대치/13공격/cleanup, Waiting/SourceAudit/Heal/Guard가 성공했다. scoped129package/원본32 hash 보존/Main cold build5action/Succeeded/Main26644 DevMap saved reload/dirty0/PIE없음, own 정상 종료를 확인했다. 메인 자동 PIE·원작 전체 AI/피해/네트워크 완료를 의미하지 않는다. 접지의 측정 scope와 임시 표현 설정은 [현행 정본](MONSTER_UNAWARE_LOCOMOTION_20261007.md)의 최종 완료 절/RuntimeResult.json을 따른다. 이전 M 전체 완료로 확대하지 않는다.


## 2026-10-07 ? ARCH-78 ??: ?? ????? ?? ????? ?? ?? ??

??? ?? ?? ??. HeavySwordsman? Basic03 Loop?End, HalberdElite? Basic02 Loop?End? ????. ?? CharacterDefinition UnawareRoutines? ? Basic ??? ???? ?? GA/Combo/Montage? ?????. Halberd02? ?? Playback?? InGame ????? ??? segment/End ??? ????. ?? sequence pose/FPS/RateScale? ?? ???Talk ??? ????.

?? Sight ?? ??? Talk partner ???? ??? Controller BattleTarget? ?? Player Actor? ??? ?? ??/leash/?? ??? ??? ???. ?? bEverSeen/?? ?? ??/??? strong ??? ??? ???. ??? ???UnPossess?EndPlay cleanup? ????. TargetMemorySeconds? ?? Sight sensory record? MaxAge? ???? PursuitLeashRadius? ?? ??? ?? ???? ?? ?? ??? ? ?? ???? ???. Home? ??? Patrol ???? ???.

Standoff? ??? ?/??/?? Enter? ?? TimeRemaining? ?? ? Root? ?????. ?? ??? ?? ?? ???? ?? ???? ???. ??? ????? ?? ring ??? ?? ??? ?? ??? local nav ??? ????. Attack? ?? Spec ?? ?? ??? ????. ? chase cooldown?timer??? ???? gameplay ?? ?? ?? ?? ??/Task/Ability/Locomotion ??? ????. ? runtime ??0??.

? ?? ?? ????. ?? ?? Khazan_MonsterWork_20261006?? ?? main Source/config? ??? ???? ?? ????, native ?? StateTree/Sight/End/?? ??/?? ??/?? ??/cleanup ??? ? scoped main ???cold build?? saved reload? ????. ???? Main PIE? ?? ???? ???. ?? ??/?? ??? Metadata/MonsterCombatPolicy_20261007? Engineering Continuity? ?? ???.

## 2026-10-07 — ARCH-78 후속: 고정 대기·전투 타깃 유지·선택 행동 완료 실제 완료

직전 같은 주제의 착수 문단은 저장 인코딩 문제로 한글이 물음표로 기록됐다. 해당 이력은 보존하며 이 절을 읽을 수 있는 계약 및 실제 완료 기록으로 사용한다. 사용자 직접 수정 요청에 따라 HeavySwordsman은 Basic_Loop_03→Basic_End_03, HalberdElite는 Basic_Loop_02→Basic_End_02로 고정했다. 기존 CharacterDefinition.UnawareRoutines를 Basic 한 항목으로 좁히고 기존 GA/ComboDefinition/Montage를 재사용했다. Halberd02 두 시퀀스만 기존 Playback에서 gameplay InGame으로 복제했으며 원본 pose/FPS/RateScale은 재작성하지 않았다. 신규 runtime C++ 파일/Ability/Component/Manager는 0이다.

BattleTarget의 작성자는 기존 Controller Sight 성공 콜백과 활성 Talk 파트너 공유이고 소비자는 기존 StateTree 조건/Task·Focus·Locomotion이다. weak Player Actor가 유효한 동안 시야 상실·기억 시간·거리에 의해 전투 타깃을 해제하지 않는다. 별도 bEverSeen/전투 bool/strong 참조/두 번째 FSM은 없다. SightLostAt과 거리·시간 기반 타깃 해제 분기만 제거했다. TargetMemorySeconds는 Sight sensory record의 MaxAge로만 남고 PursuitLeashRadius는 직렬화 설정을 보존하되 타깃 포기에 사용하지 않는다. Actor 무효화/UnPossess/EndPlay의 기존 자기 handle·task·intent·focus cleanup을 유지하고 실제 PIE에서 검사했다.

Standoff Task는 Enter에서 선택한 기존 TimeRemaining/StrafeSign 및 local MoveGoal의 수명을 소유한다. 첫 Tick(0)으로 목표를 확정하고, 플레이어가 EngageDistance 밖으로 나가면 마지막 local goal을 유지하며 선택한 구간을 완료한다. 거리 증가/공격 가능에 따른 즉시 Succeeded를 제거했다. 완료 후 기존 OnStateCompleted→Root가 Chase/Attack 등을 재선택한다. Attack은 기존 Spec 활성 수명(선택된 콤보 포함)이 끝나야 완료한다. 새 Chase 지연 타이머나 조정값은 추가하지 않았다. 여기서 한 행동은 locomotion clip 한 바퀴가 아니라 선택된 Standoff 구간 또는 Ability 실행 수명이다.

격리 stock CombatPolicyPIE 4종 및 기존 WaitingPIE 회귀, 메인 선택 9파일(hash 일치)·cold build·새 DevMap saved reload를 완료했다. 미관련 Source/Config/uproject/DevMap/Player BP·ABP 등 89파일은 전달 직전 대비 보존됐다. 검증 당시 Main PID29556/PIE 없음/dirty0이다. 상세 계약·수치 출처·실패 이력은 [Monster 현행 정본](MONSTER_UNAWARE_LOCOMOTION_20261007.md)의 같은 날짜 후속 완료 절과 Metadata/MonsterCombatPolicy_20261007/MainAppliedResult.json을 따른다. 원작 AIData 완전 복원·피해/피격·전체 M단계 완료로 확대하지 않는다.

## 2026-10-07 — ARCH-79 Enemy 전체 애니메이션 정리·Root Motion·공격 다양성/재추격 반응 착수

사용자 직접 수정 요청이다. Art 범위는 HeinMach Humanoids의 Archer 제외4병종, Yetuga, ApesStoneHandElite의 현재 재생 시퀀스676개이다. Engineering은 현재4종 gameplay 복사본93개 및 기존 StateTree/Controller/Definition/ComboAction을 재사용한다. 용도 폴더/의미 이름 변경은 UE asset rename 및 참조 수정으로 수행하고 old→new/source provenance를 보존한다. Archer/원본 archive/스켈레톤 topology/Player scale는 대상이 아니다.

Root Motion 활성화는 실제 skeleton index0/track/extraction audit 후 수행한다. 걷기까지 Root Motion으로 바꿀지 사용자 선택을 비동기로 요청했다. 답변 전에는 기존 Nav/CMC 보행과 RootMotionFromMontagesOnly를 유지하고 모든 대상 Sequence의 Root Motion을 활성화해 공격 Montage 이동에 소비하는 기준으로 진행한다. 단순 static-root/움직이는 pelvis를 wrapper 실패로 간주해 전이하지 않는다. 공용 Skeleton을 변형하거나 scale로 이동량을 보정하지 않는다. 확인된 native Root track은 보존한다.

공격 패턴은 저장 SB step/event timing과 현재 clip library에서 원작 순서의 가능한 유한 animation 경로를 기존 GA/Combo/Montage 데이터로 추가한다. 히트·특수 상황 producer가 없는 조건부 경로는 animation-only 선택이라는 출처를 명시하며 피해 처리는 추가하지 않는다. 별도 Attack Ability/Manager/FSM은 없다. 사용자 약10% 상향은 기존 ContinueComboChance .75→.85와 현재 임시 AttackIntervalSeconds를1.1로 나눈 값으로 분리 기록한다. 실제 전체 공격 빈도는 공격 길이/거리/대치에 영향을 받으므로 정확한10% runtime 증가를 보장하지 않는다.

사용자는 기존 행동 완료 대기만으로 재추격이 여전히 빠르다고 보고했다. 기존 Standoff/Attack 완료 정책을 유지하고 기존 Task instance TimeRemaining에 Chase 진입의 짧은 반응 대기만 추가한다. owner AISettings.ChaseReactionSeconds .4초는 어시스턴트 임시 튜닝값이며 기존 goal refresh .35초와 유사한 짧은 반응 구간이다. 첫 Chase 진입에도 동일하게 적용한다. Timer delegate/추가 gameplay 상태 사본은 없고 Task Enter에서 설정/Tick에서 소비/Exit와 재진입에서 재설정한다. 원인별 취소/Target 무효화/UnPossess cleanup은 유지한다. 변경 전 baseline은 Metadata/EnemyAnimationOrganization_20261007이며 실제 build/PIE/Main 전달은 후속 완료 기록과 구분한다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

ARCH-79 Main 완료.

ARCH-79 실제 완료다. 기존 StateTree/AISettings/CharacterDefinition grants/ComboAction/ComboDefinition/Montage를 재사용했다. runtime 새 파일·class·component·manager는0, 실제 gameplay Source는 KZMonster.h와 KZMonsterStateTreeNodes.cpp 두 파일이며 기존 development KZMonsterAIPIETest.cpp를 보완했다. Player/ASC/ComboAction 실행 코드를 재작성하지 않았다.

공격은13→35(Swordsman5, SwordShield3, Heavy7, Halberd20)이며 해당4종 Attack68클립을 모두 연결했다. finite 준비/loop/타격/회복은 같은 Action 안에서 필수 순서를 유지하고 실제 combo만 기존 held X/InputEnd로 잇는다. 신규 combo6개의 끝 경계 InputEnd 실패는 montage data에서 마지막 sample 이전으로 보완했다. 정확한 시간식과 원작 SB/file/field는 MONSTER_ATTACK_ROOT_MOTION_20261007.md 및 AttackExpansionPlan.json/AllSavedSkillAudit.json을 따른다. 원작 hit/guard 조건 producer나 피해/피격을 새로 구현한 것은 아니다.

현재 공격 선택에는 독립 RNG probability가 없고 거리/각도/cooldown gate를 쓴다. 기존 임시 interval2..4초를1.1로 나눠1.8181818..3.6363636초로, combo continuation .75→.85(+10percentage points)로 설정했다. 전체 공격 빈도의 정확한10%를 보장하는 통계 수치가 아니다. ChaseReactionSeconds .4초는 assistant 임시 tuning이며4BP AISettings에 저장했다. 선택 Standoff/Attack을 끝낸 뒤 Chase에 진입하고 기존 task TimeRemaining을 Enter에서 설정/Tick에서 감소시켜 nav 요청을 잠시 보류한다. 첫 Chase에도 적용한다. 타깃 유지/기존 cleanup을 보존한다.

stock SourceAnimationAudit813/18,958,755 raw transforms·곡선/선택 metadata 동일 Success; compressed root QA .01cm/normalized angular1e-4rad는 기술 허용 오차다. raw tolerance1e-6와 구분하며 실제 최대 압축 positional 차이.0060654cm였다. AttackPatternsPIE 최종35개/모든 section/actual root travel/HP 불변·취소 cleanup·네 종 실제 rechase Success. CombatPolicyPIE 네 종 선택 행동 완료/시야 밖 target 유지/.4초 nav hold/후속 물리 추격 Success, Waiting/Heal/Guard PIE Success. 최초 full Monster.PIE의32 방향보행/contact sample min11·median0cm/s는 통과했으며 montage notify만 보완한 뒤 중복 walk 검사는 반복하지 않았다. retreat fixture는 Root lunge로700cm를 따라잡는 문제와 nav 밖5000cm 배치 문제를 각각 보존하고, 최종8후보 projection+complete path 및 Chase 진입 이후 physical advance로 검사했다.

Main 선택 전달은 파일981개(기존69/신규경로912), 이름 변경 옛 파일802개를 정확한 path/hash guard 뒤 제거했다. backup Before와 실패 로그를 보존한다. 미관련 Source/Config86 및 Archer177개 hash를 보존했다. Main stock cold build Succeeded, fresh Main PID3528 /DevMap/4BP·ABP UP_TO_DATE/813 options·35 grants·68 clips/저장값 재확인/PIE없음/dirty0이다. 자동 Main PIE는 실행하지 않았다. Main에 사용자 직접 Play용 DevMap이 열려 있다. 최종 manifest와 증거는 Metadata/EnemyAnimationOrganization_20261007/FinalVerification.json, DeliveredManifest.json, MainReadyAudit.json을 따른다.

Main 최초 read-only 검사에서 DevAI_ label 접두사에 Navigation volume까지 포함해 actor수5로 실패했다. 4 BP/ABP·813 options 검사는 이미 통과한 상태였고, exact4family actor label로 QA 식을 고친 뒤 같은 fresh editor에서 전체 read-only 검사를 다시 통과했다. 실패 JSON/MainReload log를 보존했고 이 과정에서 게임 코드·map·asset save/PIE는 수행하지 않았다. raw tolerance의 정확한 값은1e-6이며 이전 Art 본문의 최초 .001cm 언급은 엄격한 compressed probe와 혼동한 설명이다. 최종 compressed .01cm와 raw 검사를 구분한다.

## 2026-10-08 — ARCH-80: NPC4 이동 보간과 공격 추적 회전 (구현 계약)

- 사용자 직접 수정 요청: 기존 NPC4 이동 모션 보간, 대치 중 타깃 상실처럼 보이는 동작, 공격 중 완만한 LookAt 및 다음 콤보 공격 전 재정렬을 개선한다. 새 runtime 파일/class/component/상태 사본을 만들지 않는다.
- 기존 BattleTarget/Gameplay Focus와 StateTree 행동 완료 정책은 유지한다. 타깃의 실재 상실과 Root Motion 동안 몸 회전 중단을 구분한다. Rider LLDB 별도 Work PIE의 DevAI_Swordsman/Attack_Kick에서 타깃 BP_Player0 유지, CMC bUseControllerDesiredRotation=1, bAllowPhysicsRotationDuringAnimRootMotion=0, 실제 RootMotionMontageInstance를 확인했다. 증거: Metadata/MonsterMotion_20261008/DebuggerBaseline.json.
- AIController는 기존 GetDesiredRotation 엔진 계약으로 최신 타깃의 평면 방향을 제공한다. 공격 실행 여부는 ASC의 현재 AnimatingAbility/IsActive 및 기존 AttackAbilities 목록에서 파생한다. CMC가 실제 capsule 회전을 수행하며 원본 montage root yaw/translation은 그대로 합성한다. Player 및 일반 이동 policy/RotationRate를 직접 덮어쓰지 않는다.
- ComboActionAbility에는 기존 node/held edge/몽타주 InputEnd notify로 다음 전환이 임박했는지 읽는 const 조회만 추가한다. 타이머/회전 상태/다음 node 사본을 저장하지 않는다. InputEnd 직전과 다음 section 준비 구간의 조준 속도를 높인다. 실패 edge/비활성/종료/취소/다른 액션에서는 파생 조회가 false가 되어 공격 회전 제한이 자동 소멸한다. 모두 Game Thread 조회다.
- 몬스터 기존 AISettings에 AttackTrackingYawRate=60 deg/s, ComboReaimYawRate=180 deg/s, AttackPreparationSeconds=0.15 s를 모아둔다. 원작 AI 회전 수치는 미확인이며 어시스턴트 임시 튜닝값이다. 느린 일반 공격 추적, 더 빠른 다음 공격 준비, 짧은 선행 재정렬을 위해 선정했다. 플레이어가 옆으로 움직이는 PIE에서 연속 yaw/오차 감소와 원본 Turn root yaw 보존을 확인해 조정한다. 순간 SetActorRotation 보정은 사용하지 않는다.
- 대치 Combat BlendSpace 4개의 TargetWeightInterpolationSpeedPerSec는 원작 BS_*_LockOnMove의 직접값(6/10/10/5)을 사용한다. 원작 normalized XY+Stand와 현행 angle/speed 표본 배치는 다르므로 원작 게임과 동일 시각 결과라는 주장은 하지 않는다. 정확한 원본 package/export/field/SHA 및 에셋 변경 전후는 표적 script report에 기록한다. 기존 ABP 관성화 노드/발 처리/GT 평가를 재사용한다.
- 별도 MonsterWork에서 구현/build/PIE 후 이번 소유 변경만 Main으로 전달한다. 현재 사용자 Main editor 및 Snow 작업을 덮어쓰거나 조작하지 않는다. 검증 완료 상태는 아래 후속 기록과 해당 작업 문서에서 구분한다.

## 2026-10-08 — ARCH-80 최종 검증 보충 / Main 미반영

ARCH-80의 구현은 현재 MonsterWork에만 적용됐다. CMC가 회전/원본 root 합성을 소유하고 Controller는 현재 BattleTarget으로 desired yaw만 반환한다. Ability const 조회는 실제 montage InputEnd와 현재 held edge/조건의 준비 가능성만 읽는다. 미래 비용 변경/commit 성공을 예측하거나 실패 전환을 강제하지 않는다. 첫 ARCH-80의 실패 edge false 표현은 현재 조건 불일치/비활성/montage mismatch 범위로 한정한다.

새 runtime 상태 사본/Manager/파일 없이 기존6개 runtimeSource를 보완했으며 공격 종료·취소·타깃 무효·UnPossess는 기존 수명/조회 원본으로 처리한다. 원작 sample 보간과 임시 공격 회전값의 출처를 구분했다. 정확 구현/검증은 MONSTER_FACING_SMOOTHING_20261008.md 마지막 절이다. Source8 중2개는 개발용test이며 Player 제품 기능 확장이 아니다. Main13700 파일 잠금으로 실제 Main 전달·fresh native 검증은 남아 있다.


## 2026-10-08 — ARCH-81 플레이어 Combo 공격 판정·수치 피해 직접 구현 착수

사용자 직접 요청으로 기존 FKZComboNode/UKZComboActionAbility에 공격별 duration window, 원작 baked/현재 pose 파생 geometry key, group별 recipient hit set, 초록 debug draw를 연결한다. 새 gameplay class/component/manager/task/tag는 만들지 않는다. Data 작성자는 기존 DA_Player_Combo_Definition, 실행·timer·dedup·cleanup 소유자는 활성 ComboAction, query/피해 승인 작성자는 authority GT이며, 공통 instant GE와 기존 몬스터 ASC/AttributeSet이 HP·Stamina 결과를 소유한다. Actor/AnimInstance/AI의 전투 상태 사본은 추가하지 않는다.

원작 출처는 Metadata/PlayerAttackCollision_20261008/Original/SourceAttackWindows.json 및 BoxSemantics.json이다. 원작 duration/1회 공격/group 기록에서 recipient당 window/shared group 1회 정책을 추론한다. separate window는 별도 타격이다. Box half extent는 원작 Bounds와116창의 모서리 계산으로 확인했다. 원작 trace channel/팀/장애물/최종 damage formula/native cylinder 소비는 확인되지 않았으며 프로젝트 정책·파생/임시값을 구분한다. 절대 HP10/Stamina5는 각 window의 편집 가능한 어시스턴트 임시값이며 원작 raw multiplier의 환산으로 표현하지 않는다.

다음 틱의 UE timer가 CMC 갱신 후 montage clock의 모든 통과 key를 소비하고, 정상 combo 전환/완료에는 현재 구간을 flush한다. 외부 cancel/실패/UnPossess/EndPlay는 판정·timer·자기 hit set을 즉시 정리한다. 자동 NextSection chain의 clock은 첫 section 길이로 자르지 않는다. 신규 target reaction/death/GuardBreak/무적을 이번 numerical damage 완료와 혼동하지 않는다. 현재는 격리 ComboWork의3개 product 파일 적용·첫 cold build만 완료했고 Main 반영·실제 PIE 검증은 아직 전이다.


## 2026-10-08 15:52 KST — MonsterStamina 작업 중 및 이전 stats 기록 가독성 보충


이번 ARCH-82는 기존 ASC/AttributeSet/CharacterDefinition·Instant 피해 GE·MontageTask·Locomotion constraint·StateTree를 재사용한다. AKZMonster가 attribute 결과를 coalesce해 death/exhaustion을 선택한다. 공유 상태는 ASC State.Exhausted/State.Dead이며 내부 montage phase는 Ability 실행 상태로 한정한다. 다른 Actor/AI/AnimInstance에 독립 exhaustion bool을 중복 저장하지 않는다.

추가 runtime 클래스2는 몬스터 Exhaustion(피격·timer·회복)과 Player BrutalAttack(입력·타깃·notify)의 서로 다른 실행 수명 때문에 필요하다. 새 manager/component/FSM/shared helper는 없다. 피격량은 ARCH-81의 기존 window·damage GE가 소유하고 이번 구현은 수치 결과를 소비한다. 두 작업의 ComboAction Source/data 소유권을 섞지 않는다. 패링은 성공 결과 생산자의 ReportAttackParried hook이며 정상 Guard 성공을 패링으로 대체하지 않는다.

각 Ability가 자기 task/timer/notify/constraint handle을 정상·실패·취소·UnPossessed·EndPlay에서 정리한다. 양쪽 정상 완료와 생존 검사가 있어야 현재 MaxStamina 충전하며 OnEndEffect/NotifyEnd 하나에 회복을 맡기지 않는다. 정책 숫자/타이밍/입력 제안과 원작 직접 확인은 MONSTER_STAMINA_EXHAUSTION_20261008.md로 구분한다. 현재 Work 구현 진행 중이며 Main·PIE 완료를 뜻하지 않는다.


## 2026-10-08 — ARCH-81 실제 적용·검증 결과

- 공격 collision의 window/pose key/shape/extent/HitGroup/HP·Stamina damage는 기존 ComboDefinition node가, timer/query/대상별 중복 적중/전환·취소·종료 cleanup은 기존 ComboActionAbility가 소유하도록 실제 적용했다. 기존 ASC/AttributeSet와 instant SetByCaller GE를 재사용하며 새 runtime manager/component/state/tag/task는 추가하지 않았다.
- 원작 duration·baked geometry를 사용하되 recipient dedup/channel/Guard/절대 피해 환산은 원작 native 검증과 구분한다. 확인되지 않은 해석/임시값을 editor Source와 현행 구현 문서에 표시한다.
- Main 선택 전달, 최신 Source compile/link, 충돌13case와 실제 입력·Guard·Heal 검사, 별도 새 Main의 저장 schema readback이 완료됐다. 실행 중 Main 강제 reload/restart는 하지 않았다. 구 editor는 정상 재시작 후 해당 DA를 저장한다. 계약·검증·수치 정본은 `PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md`와 task receipt를 따른다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

ARCH-82를 실제 Main에 적용했다. 기존 ASC/AttributeSet/CharacterDefinition/Instant damage GE/몽타주 Task/Locomotion handle/StateTree를 재사용하고, 별도 수명인 Exhaustion과 BrutalAttack Ability 두 클래스(새 runtime4파일)만 추가했다. State.Exhausted/State.Dead의 공유 상태는 ASC가 소유하며 Ability의 내부 phase/completion은 자기 실행 순서다. HP/Stamina 결과는 다음 tick에 묶어 death 우선으로 소비한다. 플레이어·피해자 양쪽 실제 Task 완료가 모인 뒤 생존자의 End 완료에서 현재 MaxStamina를 한 번 설정한다.

AI의 bPausedForCombatReaction은 게임 상태 사본이 아니라 이 반응이 StateTree Pause를 취득했는지 나타내는 cleanup 소유권이다. 다른 이유로 멈춘 Tree를 임의 Resume하지 않으며 target 기억을 유지한다. pending ARCH-80의 추가 회전은 실제 active Monster Attack과 일치할 때만 CMC에 적용하고 소진 제약 중 제외한다. 기존 ComboAction의 충돌/사용자 Jump·Down/입력 계약을 보존했다. 개발용 최초 Sight 격리·Heal observer 보완의 과거 Work 변경은 이번에 전체 파일로 덮어쓰지 않았다.

Main 선택 전달 runtime15/dev1/assets89, stock Build.cs 유지·임시 editor cpp3 제외, Work native453/0실패 및 Facing/CombatPolicy/Guard/Heal/PlayerAttackCollision 회귀5종 Success, 새 Main 실제 DLL·저장 참조·BS4/CDO·dirty0 검증이 완료됐다. 정확 근거는 Metadata/MonsterStamina_20261008/FinalVerification.json이며 물리적 패링 생산자·별도 cinematic Execution·Apes/Yetuga 자율 AI는 후속 범위다.

## 2026-10-08 18:32 KST — ARCH-83 공격 VFX 실행 소유권·브루탈 추가 범위

사용자의 현재 모든 공격 이펙트 직접 구현 요청을 따른다. 최초 ComboDefinition18node 분석 뒤 ARCH-82의 Front/Back BrutalAttack이 Main에 전달돼 실제 두 번째 소비자가 생겼다. 기존 ComboAction의 Start/Stop/ClearCombatEffect와 weak resource record를 기존 부모 UKZActionAbility의 protected 구현으로 옮겨 공유한다. 새 manager/component/공유 helper class/전역 timer는 만들지 않는다. 새 runtime 파일은 data-only UKZAnimNotify_CombatEffect h/cpp 두 개뿐이다.

기존 Ability 실행이 자원·원본 종료 정책·component-bound timer를 소유한다. Combo의 현재 node/실제 HP hit/몽타주 instance·execution/dedup 계약은 Combo에 남기고, Brutal의 타깃·paired reaction·피해·입력·movement constraint는 기존 BrutalAbility에 남긴다. 이펙트는 피해를 다시 적용하거나 gameplay 상태를 결정하지 않는다. 원본 bOnAttackSuccessed는 확정된 현재 실행의 적중 결과로만 허용하며, 현재 BrutalHPDamage0 설정은 이 작업에서 임의 변경하지 않는다. 원작 native BattleEffectIndex·opacity shader topology는 미복원 상태의 adapter와 구분한다.

현재 private에 최신 Main Source93개와 새 Brutal DAS7개를 guarded intake했고 Combo2는 exact three-way 병합했다. Main Source/Content에는 아직 VFX 후보를 전달하지 않았다. 원본5개 Grapple composite의 새54Particle/Decal occurrence와 기존347개를 분리 분석·작성하고, 실제 취소/정상 완료/캐릭터 격리 및 저장 재로드를 검사한 뒤 선택 전달한다. 적용·build·PIE 완료는 후속 실제 증거로만 기록한다.

<!-- PlayerAttackVFXMainComplete_20261008_1911 -->
## 2026-10-08 19:11 KST — ARCH-83 실제 Main 완료

ARCH-83의 기존 ActionAbility protected Start/Stop/ClearCombatEffect 공유를 Main에 적용했다. Combo의 실제 hit/node/execution/delegate 관측과 Brutal의 paired target/피해/입력/제약 수명은 기존 실행 소유자에 남는다. Notify는 data-only이며 Pawn/실행 상태를 저장하지 않는다. 신규 runtime class1/파일2는 기존 branching-point Notify의 데이터 확장뿐이고 새 manager/component/전역 Tick은 없다. 확정된 피해 결과만 표현에 사용하며 VFX가 gameplay 피해를 생산하지 않는다. 동기 GE 후와 재생 entry마다 현재 소유권을 검증하고 source 종료 flag·정상/취소·잔여 decal 수명을 구분한다.

최신 Main 독립 변경을 병합·보존한 전체 build Success,11Source(runtime10/dev1)+8몽타주+15Art 선택 전달, fresh Main 실제 alias의18 Combo+Brutal5case RHI Success 및8몽타주401paired ID/8,308field saved readback을 확인했다. 현재 BrutalHPDamage0에서는 조건부 blood0이 올바른 정책이며 양성6.25피해는 transient 개발 fixture만 사용했다. 원작 native BattleEffectIndex/첫 적중·CDO default·shader topology·픽셀 일치와 멀티플레이는 확인되지 않았다. 원작 원시값과 adapter를 혼동하지 않는다.

현재 실행 정본과 검증 한계는 [PLAYER_ATTACK_VFX_RUNTIME_20261008.md](PLAYER_ATTACK_VFX_RUNTIME_20261008.md)의19:11 완료 절, 증거는 [FinalVerification](../../Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json)이다. 사용자16572의 구 모듈은 조작/reload하지 않았으므로 정상 재시작 후 새 schema를 사용한다. 전체 M단계나 원작 완전 일치 완료를 의미하지 않는다.


## 2026-10-08 — ARCH-84 피격·SystemGuard·브루탈 접근 계약 (구현 중)

사용자의 직접 구현 요청이다. 기존 Combo 충돌→공통 피해 GE→확정된 결과의 표현 순서를 유지한다. 공격 window의 반응 종류(None/Short/Knockback/Launch)는 공격자 데이터가 지정하고 CharacterDefinition의 종류별 몽타주 pool에서 방향 변형을 랜덤 선택한다. 입사 방향으로 일반 피격 모션을 선택하지 않는다. 공유 ASC 이벤트와 단일 UKZHitReactionAbility만 추가하며 새 combat manager/component/FSM은 만들지 않는다. HP0/몬스터 Stamina0/Dead/Exhausted와 기존 paired Brutal 반응은 일반 피격보다 우선한다. Ability가 취소/완료/실패의 몽타주·제약·공중 movement mode를 정리한다.

SwordShield는 원본 Battle LockOnMove의 SystemGuard180과 attack DamageType notify 구간을 구분한다. 기존 노드에 방어 시간 구간을 추가하며 현재 몽타주 시간으로 소비한다. Passive shield block에는 Active Guard FrontAngle60/GuardStaminaConsumeRate1.8을 임의 혼용하지 않는다. 180을 full cone으로 해석하는 것은 native 소비자 미확인 프로젝트 adapter다. 방패 반응 Hit→End의 재차 피격도 방어하도록 기존 피격 Ability가 자기 shield 실행 여부를 제공한다. 실제 방어는 HP 피해를 막고 공격 window의 사용자 조정 StaminaDamage를 소모하며 소진이면 기존 Exhaustion이 우선한다.

이미 있는 UKZBrutalAttackAbility/UKZExhaustionAbility와 전후 paired montage를 재사용한다. 즉시 TeleportPhysics 정렬을 원본 Grapple Start MoveTo의 .03356 trigger/.433283초 CubicInOut을 참고한 swept 접근으로 바꾼다. 최종 spacing은 기존 live capsule 정책이며 원본350을 최종 간격으로 단정하지 않는다. .01 mesh scale은 actor 정렬에 재적용하지 않는다. 기존 사용자 BrutalHPDamage50 및 lethal Hit2 이후 양쪽 반응 완료를 보존한다. 원본 조사/분류는 Art 별도 문서, 런타임 검증/임시값은 Engineering에 기록한다. 아직 Main 전달/빌드/PIE 완료가 아니다.

## 2026-10-08 20:20 KST — ARCH-84 몬스터6 행동·공격 VFX 직접 구현 계약

사용자 직접 요청으로 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga의 기존 애니메이션·행동·공격·소진에 원작 시각 이벤트를 연결한다. ARCH-83의 Ability 실행·적중·취소 수명은 보존한다. 일반 ABP sequence와 비Action Exhaustion은 montage branching delegate만으로 표현할 수 없으므로, 구체적인 data-only MonsterVisual NotifyState 한 클래스/두 runtime 파일을 추가한다. 엔진 NoMergeOnConcurrentPlay 및 NotifyInstanceID가 서로 다른 asset-player/montage 재생을 구분하며, 공유 Notify asset에 Pawn별 상태를 저장하지 않는다.

기존 CombatEffect data class에 현재 particle/decal 생성·위치·바닥·parameter 계산의 stateless factory만 공유한다. 기존 ActionAbility는 승인·실제적중·record/timer/cleanup을 그대로 소유한다. 기존 Monster는 자기 mesh의 NotifyInstanceID별 실제 component/material snapshot만 보유하며 Begin/Tick/End·취소·death freeze·EndPlay에서 자기 자원을 정리한다. gameplay 상태/AI/Ability 상속은 다시 만들지 않는다. 추가 Material bone/vector·curve와 Yetuga trail mesh는 실제 원본 notify를 소비하는 이 수명에 한정한다. worker에서 Actor/ASC/material을 갱신하지 않는다.

원본 notify/시간/attach/조건은 저장 canonical clip metadata와 표적 resource closure를 재사용한다. Niagara/cooked shader/native 조건이 복원 불가하면 원본 확인값과 명시된 렌더 adapter/임시값을 구분하고 필요한 시각 재생을 작성한다. 조건부 적중을 animation만으로 성공 처리하거나 별도 몬스터 공격 피해/자율 boss AI를 이 VFX 작업으로 생성하지 않는다. 별도 MonsterVFXWork에서 구현·저장·실제RHI/cleanup/기존Player 회귀 후 소유 변경만 Main에 전달하며 기존 사용자 브루탈 HP50을 보존한다. 이 절은 계약이며 아직 구현·빌드·PIE·Main 반영 완료가 아니다.

## 2026-10-08 20:36 KST — ARCH-84 사망 표현과 원본 Decal 곡선 계약 보완

현재 사망 경계는 `AKZMonster::FinishDeathPresentation`의 즉시 pose freeze이므로 원본 Death 시퀀스 Notify의 실제 소비자가 없다. 이번 이펙트 직접 구현 범위에서 기존 `FKZMonsterStaminaSettings`에 선택적인 `DeathPresentationMontage`만 추가한다. ASC Dead 상태·이동 제한·Ability 취소·Brutal 피해/쌍 수명은 기존 ARCH-82가 계속 소유한다. 기존 Monster가 사망 표현 전용 montage/AnimInstance의 weak receipt와 end delegate를 소유하고 종료·중단·EndPlay 때 자신의 visual 자원과 delegate를 정리한 뒤 freeze한다. 새 Death Ability, AI, FSM, 공통 manager는 만들지 않는다. 완주한 lethal Brutal2는 마지막 paired reaction 자세를 보존하며 Death montage를 다시 재생하지 않는다. 원본 Death 방향 선택 producer가 없으므로 기본 앞 사망 클립 선택은 프로젝트 표현 adapter로 명시하고, 클립의 포즈·시간·이펙트 수치는 원본 정본을 사용한다.

Apes/Yetuga의 원본 Decal 곡선은 Player의 네 곡선 인덱스와 혼동하지 않는다. 새 복원 Decal 재질은 출처가 식별된 곡선 키/보간·lifespan의 GPU age 계약을 사용하고, Notify가 끝난 후에도 원본 lifespan까지 올바르게 감쇠한다. 기존 Player native 효과·재질을 일괄 재작성하지 않는다. 위 항목은 계약/적용 예정 기록이며 build·saved reload·RHI 검증 완료를 뜻하지 않는다.


## 2026-10-08 — In-place 피격의 실제 이동 경로 추가

별도 Work commandlet에서 Player Air F/B의 true skeleton root C_P_Kazan/index0/track0과 child Root 모두 이동0을 확인했다. 순서/누락/다른 Root의 이동 전사 문제가 아니다. Swordsman Up의 Bip001 이동은 포즈이며 world root로 임의 전사하지 않는다. 근거는 Metadata/CombatReaction_20261008/PlayerSourceRootReadback.json 및 InPlaceReactionRootAudit.json이다. `unreal-root-motion-repair`는 읽기 진단에만 적용했고 root/골격을 재구성하지 않았다.

이런 클립은 플레이 중 실제 날림을 별도로 구동해야 한다. 새 물리 component/helper 대신 HitReaction 실행에 엔진 UAbilityTask_ApplyRootMotionJumpForce의 RootMotionSource를 소유한다. Short/방패/미지원 Giant Short fallback은 이 이동을 만들지 않는다. 지원하는 Knockback은 수평, Launch는 수평+수직 곡선이다. duration은 실제 몽타주의 반응→Land/Getup 시각에서 가져오고 새 gameplay timer 수치를 만들지 않는다. CMC는 anim root motion을 RootMotionSource보다 먼저 적용하므로 자기 force 중에는 AnimInstance IgnoreRootMotion을 소유하고 완료/취소에 이전 mode를 복구한다. 원본 클립 옵션/track/rate는 보존하고 InGame 복제의 root 옵션만 실제 기존 template 정책으로 켠다.

CharacterDefinition HitReactions의 KnockbackDistance250cm, LaunchDistance120cm, LaunchHeight150cm는 어시스턴트가 선택한 임시 튜닝값이다. 원작 absolute 거리/높이로 확인한 수치가 아니다. 캐릭터 종마다 조절할 수 있고 실제 capsule 이동·벽 sweep·착지/기상 완료·과도한 이동 여부로 검증한다. 숫자를 여러 함수에 흩어 넣지 않는다. 일반 Monster Attack Window HP10/Stamina5도 원작 절대 피해량 환산이 미확인인 임시 설정으로 기존 window 데이터에 모아 조절한다. Player 기존 피해값은 임의 변경하지 않으며 승인된 접촉의 애니메이션 반응은 피해0에서도 가능하다. 원작 raw knockback curve/힘·거리 필드와 프로젝트3종 분류는 구분한다. 아직 이 force의 build/PIE 완료가 아니다.

## 2026-10-08 20:47 KST — ARCH-84 시퀀스 종료 자원과 Rim 표현 소비자

원본 부분 Notify 구간이 자연 종료된 후에도 `bDestroyOnAnimEnd` 자원이 남는 경우, 부분 Notify의 End만으로 receipt를 버리면 이후 취소/사망 정리가 누락된다. 같은 MonsterVisual NotifyState에 data-only `bAnimationContextBoundary`를 두고 VFX가 있는 source clip별 full-span sentinel 하나를 저작한다. 별도 class/게임 상태/폴링 timer를 추가하지 않으며, source sequence와 엔진 montage/asset-player context identity에 속한 presentation receipt만 clip 종료·교체·취소 때 정리한다. sentinel은 프로젝트 수명 adapter이고 원본 발생 횟수와 분리 집계한다.

Halberd `Damage_Disease`의 원본 Rim point notify는 source payload `Duration=1.2`, `BlendIn=0`, `BlendOut=1.2`, `CustomColor=(2,0,0,0)`를 별도 interval로 소비한다. source SequenceLength=2.4와 오래된 Notifies.SegmentLength=1.2를 dilation으로 오인하지 않는다. 원본 shader graph/지수는 미확인이다. 기존 MonsterVisual State의 선택적인 material overlay와 scalar curve 소비자를 재사용해 전용 additive Fresnel 재질을 잠시 적용하고, baseline overlay를 자기 receipt 범위에서 복원한다. RGB·타이밍은 원본 확인값, Fresnel 표현과 engine 기본 지수5 사용은 명시된 임시 렌더링 adapter다. 원본 그래프를 복원했다는 주장은 하지 않는다. Apes scalar/vector도 실제 shader consumer 유무를 확인하고, 값 write만으로 화면 검증을 대체하지 않는다.


## 2026-10-08 — 동시 작업 ARCH 번호 식별 보충

동시에 진행된 두 별도 작업이 ARCH-84를 기록했다. 기존 기록을 보존하고 이후 CombatReaction(일반 피격/SystemGuard/Brutal 접근) 계약은 ARCH-85로 식별한다. Monster VFX/사망 표현 계약은 다른 작업의 ARCH-84로 유지한다. 이 번호 보충은 게임 코드 변경이나 두 작업의 병합 완료를 의미하지 않는다. 공유 KZMonster/CharacterDefinition/ComboAction과 Definition 저장 에셋은 최신 Main을 CAS 확인하고 각 변경을 보존해 통합해야 한다.


## 2026-10-08 21:58 KST ? ARCH-84 ?? ?????? corpse? ?? ??? ??

?? Apes Execution ??? Death 1?800, FinalBlow ?0?999.9998, ExecutionO ?0?2000?? normalized0..1? ???. ?? shader topology/??? ?????? raw curve? ??? ???? ?? ??? radius ???10cm ?? ?? ??? adapter/assistant ????? ????. ?? source field/?/SHA? ? master ??? Resources/ExecutionRadiusRevision.json? ???? ?? normalized adapter ??? ????. animation curve?Gameplay ?????? MI source values? ??? ???.

?? ??? BrutalHPDamage50? nonlethal Apes??? FinalBlow? ????? source execution material? ??? ???? ?? ?? ??? ???? ?? ????. ?? ?? Exhaustion? paired owner? actual HP? ??? ? ?? execution replacement material? ????. ?? animation preview? ?? ???? ?? ???? ???? ???? ???? ???. ?? ???? ?? adapter?? ?? native ?? ??? ???? ???.

??HP0? ??? ??Death/pairedBrutal2 ??? ??? MID?source parameter? frozen corpse?? ???? ??. ?? Monster? material receipts? pending/terminal presentation ownership? ?? weak Ability owner? ????, ?? paired completion??? FinishAbility cleanup ?? ?? receipt? Actor ?? ????? ????. ? gameplay State/??/manager/DeathAbility/actor hide? ??????? ??? ??. ??????context replacement?UnPossess?EndPlay??? ?? baseline ??? ????. exact Mesh/Anim/NotifyID/Source/MontageInstance ??? ???? ?? ???/?? paired ?? DEV ??? ????. runtime schema/???2855source event fields? ??? ???. build/PIE/Main ??? ?? ?? ??? ????.


## 2026-10-08 22:16 KST ? ARCH-84 NoMerge ?? ????? ?? ?? ??? ??

? actualRHI?? ?? DevMap Swordsman Walk_Peace_F_Composite? ?? ???? frame?? ? NotifyID? Begin?? ??? ????. Engine AnimInstance.cpp1898?1919? NoMergeOnConcurrentPlay? ? Montage/AssetPlayer context? ??? ?? ??? ?? match?? ???. ?? BlendSpace? SingleNode? ? context? ???? ???? ??? NoMerge constructor ??? ????. ?? ????source event fields???? ????.

?? Monster? singleAction/default slot? engine default matching? ???? Actor/Mesh/Anim/NotifyID? receipt? ???? source context? ?? ????. ?? avatar/?? ?? ??? ??? ????. ?? AnimInstance?? ?? asset? ?? notify? ??? ? ? ???? ?? engine default? merge? ? ??? ? ?? lifecycle?? ?? ??? ???? ???. ?? concrete consumer? ?? ? ??? ?? ?? instanceID??? frame-delay ??/manager? ??? ???. ?? ?? ? context? ???? graph/engine ?? ???? ????.

? RHI test-start failure? Automation StartTestSession? ?? PIE? ???? ?????. DEV test? ?? Player test?? ?? pawn? ???? latent entry? ???? QA driver? TestStarted ?? ??? PIE? ????. ??? editor? ???? ???. ?? ??/?? ?? ??? ?? ?? ?? ?? ????. fresh saved flags? nativeRHI/???cleanup ???? ?? ??.

## 2026-10-10 19:48 KST — ARCH-84 중단 재개와 Apes 현재 재질 연결 적용

10월8일 PrivateMonster RHI2는 consumer6 assertion 및 light usage fallback으로 실패했고 Main 전달 전에서 중단됐다. 10월10일 정확 재개 때 Main/private Source·Config·uproject가 Build10의 입력 SHA와 동일하고 실행 중 editor가 없음을 확인했다. 기존 작업을 다시 추출/전체 저작하지 않는다.

Apes의 원작 Notify는 V3 MI5를 지목하지만 현재 BP/SK 슬롯은 NON-V3 MI5다. 기존 MaterialOverrides 타입을 그대로 사용해 원작5행을 유지하고 현재 MI5에 대응하는 명시적 프로젝트 alias5행을 추가했다. 두 private Sequence의 State5만 수정하고 원본 pose/curve/time, 나머지497 author 파일, original Main-before journal 및 native schema를 보존했다. 기존 Monster AcquireBinding에서 새 slot replacement MID에 earliest baseline의 효과적인 uniform 값을 복사해 현재 Tex_D/색/비율을 유지한 뒤 원작 Execution/O·bone parameter를 갱신한다. overlay에는 이 복사를 적용하지 않는다. 원본 재질 버전의 동등성을 주장하거나 BP/mesh/원본 MI를 바꾸지 않는다.

따뜻한 DevMap에서 입김2가 나오지 않은 것은 bWinterOnly 조건의 정상 결과였다. DEV fixture는 실제 recipe가 winter owner 없이 억제되는 것을 검사한 다음 기존 AKZSnowDeformation을 transient로 생성해 실제 sequence의 winter-positive 재생을 검사한다. FieldResolution128은 QA 메모리 예산이며 제품 snow 설정/원작 수치가 아니다. fixture는 clip 완료·실패·cleanup에서 자기 actor만 제거한다. 제품 환경 조건은 유지했다.

Apes probe2와 표적 apply는 성공했고 Build11은37.578s/exit0, private/Main 입력 불변이다. 이후 fresh saved/RHI·Player 회귀·Main 전달과 검증은 아직 대기다. 근거는 Saved/ImportReports/MonsterVFX_20261008/Authoring/ApesCurrentMaterialBindingRevision/{Probe,Applied}.json, Build/Attempt11/Exit.json이며 Art alias 출처는 Resources/ApesCurrentMaterialBindingEvidence.json이다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — ARCH-85 피격·SystemGuard·브루탈 최소 확장 Main 완료

ARCH-85 계약을 Main에 실제 적용했다. 신규 runtime class는 공통 UKZHitReactionAbility1개/h·cpp2개이며 기존14개 파일의 작은 확장으로 총16개다. ASC 태그/event와 기존 AbilityTask/GE/Locomotion 제약을 공유하고, 피해 확정은 Combo collision/Effect가, 실행·취소는 HitReaction/Brutal/Exhaustion이 소유한다. 별도 상태 사본·Manager·FSM을 만들지 않았다. 짝 capsule ignore는 기존 Exhaustion full-pair 수명에서 자기 추가분만 소유하고 복구한다. world wall 충돌·50 1회·양쪽 완료를 보존한다.

Main146행 전달·stock build·RHI32/15/3·stock 회귀4개·fresh Work/Main 각각654,552 saved checks가 성공했다. 현행·수치 출처·지원 fallback·검증 한계는 [피격 runtime 정본](COMBAT_REACTION_RUNTIME_20261008.md)의 2026-10-10 완료 절과 [최종 증거](../../Metadata/CombatReaction_20261008/FinalVerification.json)를 따른다. 기존 ARCH-84 MonsterVFX는 별도 작업이고 그 완료를 이번 결과로 주장하지 않는다. 후속 shared Source/Definition 변경은 새 Main alias/source/asset SHA를 받아 병합·검증해야 하며, 이전 Work baseline이나 old pending delivery를 다시 적용하지 않는다.


<!-- MonsterVFX_ApesGrapple_Rim_PrivateCheckpoint_20261010 -->
## 2026-10-10 20:11 KST — ARCH-84 실제 Grapple source·Rim owner와 private 검증 범위 정정

앞선21:58 paired execution 계약 및 Runtime22:26의 retention 설명은 source material notify가 실제로 존재하는 경우의 소유 정책이다. 현행 Apes paired Grapple 앞/뒤01/02와 InGame 사본은 각각 원본 Particle4/material0이며, FinalBlow3+Die_F2만 execution material State를 가진다. 현재 Grapple에 FinalBlow dissolve를 붙여 재현하거나 기존 paired 경로에서 그 terminal material 유지가 검증됐다고 설명하지 않는다. producer가 없는 현행 경로의 paired Execution retention은 미검증으로 남긴다.

NONV3 현재 슬롯 alias는 기존 MaterialOverrides 타입의5행 추가로 두 Sequence/State5만 수정했다. 원작 V3행·source/effect fields·schema58d4696c…6cf 및 original Main-before journal499를 보존했다. Runtime Source9+DEV2, 저장 Sequence487/State3342/Death6와 Art 후보457이 현재 범위다. 새 gameplay producer/AI/manager는 없다.

RHI3의 native failure20은 paired terminal replacement/value를 기대한 QA뿐이었다. ordinary Death의 Execution800/consumer5 관측과 fresh SavedReadback4 통과를 전체 RHI 성공으로 확대하지 않는다. Build13은16.422s/exit0이고 실제 paired clip에 맞는 QA만 보완했으며 추가 게임 코드 수정은 없다. PrivateMonsterRHI4는 실행 중이다.

Rim의 실제 source skeleton은 Halberd WeaponV2다. PrivateRimQA Attempt2는 실제 BP의 compatible EnemyWeapon_R에서 overlay/weight fade/baseline 복원·save0/fallback0을 확인했다. 역광 PNG로 시각 강도는 미확정이어서 추가 QA 중이다. 기존20:47의 Rim 구현 계약을 full visual pass로 읽지 않는다. 자세한 source/field·실제 DLL·시간 표본·재개 순서는 [Monster runtime 정본](MONSTER_VFX_RUNTIME_20261008.md)의 이번 절을 따른다.

MonsterVFX는 Main 미전달이다. 별도 ARCH-85 CombatReaction의 Main 완료를 이번 기능의 완료로 재사용하지 않고, 이후 shared Source/Definition은 최신 Main 변경을 보존하여 CAS/병합·재검증한다.

## 2026-10-11 — ARCH-86 계획: Apes·Yetuga StateTree / 플레이어 낙하

- 직접 구현 요청 범위: 저장 원본 패턴 자료를 바탕으로 두 짐승의 전투를 기존 StateTree·ComboAction·Definition에 연결, 점프 없이 CMC 낙하/착지와 공중 X 낙하 공격, DevMap 높은 발판 및 발판 위 PlayerStart. 작업/테스트 에디터는 새 `Khazan_GiantFallWork_20261011/Khazan`에서만 실행한다.
- 원본 근거: `Metadata/EnemyBehaviorResearch_20261008`의 Apes resolved branches, Yetuga package/export-index 해석 및 저장된 재생 타임라인. Apes Early를 HeinMach 기본으로, Yetuga는 거리/각도별 우선순위 선택을 보존한다. 원본 raw HP 65/60/50은 비율로 임의 변환하지 않는다.
- 책임: StateTree는 행동 선택/기존 AIController의 재사용 시간, Ability는 조건부 단계/몬타주/취소 실행 수명, CMC는 실제 낙하/착지, AnimInstance는 기존 Falling 관측을 유지한다. 새 공용 FSM/Manager/컴포넌트 및 gameplay 상태 사본을 만들지 않는다.
- 이 기록은 착수/설계 계획이며 아직 게임 구현·빌드·PIE 완료 기록이 아니다. 원본 native 이벤트/확률 해석이 누락된 항목은 프로젝트 어댑터 또는 미검증으로 기록한다.


<!-- MonsterVFX_ARCH84_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — ARCH-84 몬스터 VFX 실제 Main 완료

기존 ActionAbility 순수 factory·engine Notify를 재사용해 신규 data-only MonsterVisual NotifyState1개/h·cpp2와 기존 Monster receipt 경로를 적용했다. mesh/Anim/NotifyID/source-context 소유 자원이 부분 tail·clip 경계/loop/cancel·material overlap·death freeze/UnPossess/EndPlay에서 정리된다. optional Death montage는 기존 Definition/Exhaustion을 사용하며 새 gameplay State/Manager/DeathAbility/AI는 없다. runtime9(기존7+신규2파일)+DEV2=Source11이다.

[FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)의 실제 `MainDeliveredAndFreshVerified`는 최종 선택972·Sequence487/State3342/Death6·fresh Main saved/네 실제 RHI·Root 표본 검토를 결속한다. ordinary Death material 유지와 실제 Grapple material recipe0, 사용자 피해50/B 입력·ARCH-85를 보존했다. 원작 미직렬화 victim Decal43 정책·shader/NI adapter·unsupported216 및 새 ARCH-86의 독립 범위는 실행/Art 정본을 따른다.

초기968/Art457은 보존하고 Main 누락 adapter4를 별도 strict supplement로 추가한 최종972 기준이다. Source/native/material graph와 private proof는 유지했으며 새 Main 최종 검증은 추가 전달 이후 결과다.

## 2026-10-11 — ARCH-86 실제 Main 구현·검증 및 재현 경계

ARCH-86은 현재 실제 Main Source/asset으로 반영됐다. StateTree/AI는 타깃·후보와 기존 행동 수명, MonsterPatternAbility는 조건부 단계·몽타주·자기 실행 자원, SkillObject는 발사 이후 독립 수명, FallAbility/CMC는 실제 낙하·착지의 실행을 소유한다. 기존13 runtime 파일 + 새 runtime6, DEV1, editor Json rule1이다. FSM/Manager/컴포넌트와 Main AnimInstance의 gameplay 상태 사본0이다.

MainBuild02·fresh Main saved150+DevMap·실제 Main RHI 낙하/전투8사례 성공, 제품176/보호Source84/VFX Content965 해시 보존은 [최종 증거](../../Metadata/GiantCombatFall_20261011/FinalVerification.json)를 따른다. 초기 설계/Work/실패 로그를 완료 근거로 대체하지 않는다. current manifest는 UnrealEditor-Khazan-20261011.dll이다. 기존 모듈/데이터는 byte backup으로 보관했고 외부 에디터 제어0이다.

실행 설명/소스 diff/원본 및 임시 값/후속은 [구현 정본 마지막 절](APES_YETUGA_FALL_IMPLEMENTATION_20261011.md)에 있다. source129노드가 데이터에 존재하는 것과 모든 native BT fallback·MoveTo/grab/Spell/camera·원작 pixel/frame 동작이 동일한 것은 별개다. 평탄화한 Yetuga 후보와 공통 Chase, missing Apes projectile sphere, Yetuga pickup Spawn 추론은 explicit 재현 경계로 유지한다.


## 2026-10-11 ? ARCH-87 Combat UI ?? ??

???? Main? ?? ?? ??? ?? UI ??? ?? ????. ? runtime ??? UKZCombatHUDWidget? h/cpp2???, ?? local PlayerController? ??/viewport/EndPlay? ????. Widget? ASC? HP/MaxHP/Stamina/MaxStamina? GT?? ?? ???? ????. Actor/ASC/Ability? gameplay ?? ??, ?? ??, ?? Manager? ???? ???. ?? LockOnComponent?? ?? ?? current-target getter? ????. ??? ??? ?? B ??? ??? ????? ?? ?? FindBrutalTarget?? ?? ?? ?? ??? ??? ?? ?? ??? ????, ? ??? ?? ??? ?? ??? ????.

Monster? ?? ??? ?? UI ??(??/??? ??, ??, ?? bone/socket)? ?? Monster? ??. Yetuga BP? ?? ??? ?? ?? ?? ?? ??? viewport? ????. ?? actor ??/?? WidgetTree ?? UI? ???? ??/??/UnPossess/EndPlay?? ??? ????. B ??? ?? granted BrutalAbility? CanActivateAbility/FindBrutalTarget ??? ???? ?? ?? ?? ??? ????? ???.

?? widget/image/layout/color? ??? Metadata/CombatUI_20261011? ?? Art ??? ????. ?? xxAnimatedProgressBar.InterpolationTimeMultiply=.35? ???/?? ?????? ???? ?? ?? .35?? ????? ????. ?? ?? ??, DPI, ??? ??, ?? ?? ?? ??, ???0, ?? ??, ??/B, normal/Yetuga ??? ?? Main process?? ????. ? ?? ?? ???? ?? build/PIE ??? ???.
# 2026-10-11 — ARCH-86 후속 병합 계약 / ARCH-87 보존

백그라운드 CombatPresentationFix의 미전달 변경을 이번 Main 통합 요청으로 이어서 처리한다. 기존 Brutal/Exhaustion Ability가 paired montage 동안 root travel의 임시 IgnoreRootMotion과 이전 mode 복구를 소유하고, 기존 UpdateAlignment가 실제 victim capsule 위치에서 목적지를 갱신한다. 정상·취소·실패 cleanup은 기존 EndAbility/ReleaseBrutalMovementIgnore를 사용한다. 새 runtime class·manager·상태 사본은 없다. 원본 paired pose/sequence, GAS 실행 수명과 피해 정책을 유지한다.

ARCH-87의 적격 locked target 우선 선택, LockOn getter, Controller 소유 HUD, Monster 표시 설정과 UMG/Slate 의존성을 병합 때 보존한다. Private author wrapper 및 대량 editor 의존성은 Main runtime module에 전달하지 않는다. 낙하 montage/공격 창은 저장된 FallPlan의 기존 baked 시간축 변환을 한 번만 적용하며 원본 sequence를 재임포트하지 않는다. 설원은 기존 level-owned 표시 field의 작은 설정/접촉 확장이다. 실제 빌드·PIE·Main 전달 결과는 후속 날짜별 검증 절에 추가한다.
## 2026-10-11 — ARCH-87 UTF-8 계약 보충 / 실제 Main UI

앞선 ARCH-87 중간 추가 절의 인코딩 손상은 이 절과 `COMBAT_UI_RUNTIME_20261011.md`로 보충한다. 원래 기록은 삭제하지 않는다. 새 runtime 파일은 `UI/KZCombatHUDWidget.h/.cpp` 두 개이며 기존 local PlayerController가 생성·viewport 추가·EndPlay 제거를 소유한다. GT Widget tick이 현재 possessed Pawn 및 각 대상 ASC의 HP/MaxHP·Stamina/MaxStamina를 표시용으로 읽는다. 확정 gameplay 값·Ability 실행 수명·회복/피해 정책은 ASC/기존 Ability가 계속 소유한다. UI에 gameplay timer/공유 bool/새 manager를 만들지 않는다.

기존 LockOnComponent의 read-only GetCurrentTarget과 각 Monster의 실제 TargetPoint를 소비한다. B 인디케이터는 granted Brutal spec의 CanActivateAbility와 FindBrutalTarget 결과를 사용하고 실행 중에는 해제한다. 실제 행동과 표식을 일치시키기 위해 모든 기존 적격 조건을 통과한 locked target을 우선하며, 없으면 최근접 적격 target을 선택한다. 대상 소멸·HP0 표시 감소 완료·UnPossess·EndPlay에서 표시를 정리한다. Monster의 boss/elite/name/head-bone 표시 설정은 Monster가 소유하고, Yetuga는 상단 HUD, 일반 적은 실제 Bip001-Head 위치에서 표시한다.

원작 이미지16·UI material2·FontFace1과 layout/color/폰트 수치는 Art 원본 감사에 결속한다. 양방향 게이지 보간 `.35초`는 원작 raw `.35`의 native 단위/공식이 미확인이므로 어시스턴트 임시 표시 튜닝이며 WBP Class Defaults에서 조정한다. gameplay 값은 즉시 변화한다. source ring/fade 및 boss 선택·visibility는 명시된 프로젝트 adapter다. Main Build06/PIEEditor03 전체 통과 후 ARCH-86 후속 27파일을 병합했으며 새 Main 빌드/저장 readback은 통과했다. 후속 실제 PIE 회귀 결과는 완료 절에 추가한다.
## 2026-10-11 — ARCH-86 후속 / ARCH-87 Main 적용·검증 종료

직전 후속 계약과 UTF-8 UI 보충 절은 실제 Main Source/Content로 적용됐다. 새 gameplay runtime 파일0, UI Widget h/cpp2, 기존 Controller/LockOn/Monster/Brutal 최소 확장이다. Source8/Content19 후속 선택 전달과 UI Source10/Content27의 실제 저장·빌드·RHI를 각 최종 receipt로 확인했다. Main paired12/Snow/CombatEffect18+Brutal5/UI05/Shader fallback0, 새 readback 및 actor9861/PP0/동일 카메라3가 완료됐다. current module은 canonical UnrealEditor-Khazan.dll SHA `c908da8696b7844df39c7d476aa3ea8c10b96d206137b359c9252940d13c98bf`다. 기존 Tag–Ability 책임/locked target 우선/GAS 수치를 보존했고 문서상의 완료는 위 검증 범위로 한정한다.

## 2026-10-11 — ARCH-88 사용자 직접 수정 요청: Monster VFX·피격/사망·Combat UI

최신 요청으로 몬스터6종의 공격 이펙트 위치/방향을 전부 재검사하고, 바닥 혈흔 데칼 생성은 제거한다. 실제 승인된 피격에는 다량의 검붉은 분사, 사망 애니메이션/짝 실행 완료 후에는 검은 재와 dissolve 소멸을 적용한다. LockOn/B 표식은 실제 가슴 소켓에 부착해 매 프레임 투영하며, 게이지는 즉시 foreground 반응과 원작 alpha/layout을 적용한다. 원작 확인값·계산값·사용자 요청의 새 표현/임시 튜닝을 구분한다.

ARCH-84/85/87의 기존 Monster/Notify/factory/Hit 결과/HUD 수명을 재사용한다. gameplay 피해·GAS 실행/취소·paired 수명은 유지한다. 새 Manager/FSM/component/공유 gameplay 상태 사본을 만들지 않는다. Corpse의 material/particle 정리는 기존 Monster presentation owner가 담당하며 UnPossess/EndPlay cleanup을 유지한다. Main에는 선택된 runtime 작은 diff와 표적 asset만 전달한다. 기존 GiantFallWork를 최신 Main에서 snapshot하고 거기서 검사/저작한다. 기존 다른 task editor는 제어하지 않고, Main 전달 직전 동시 변경의 SHA와 책임을 대조한다. 이 절은 착수 계약이며 실제 수정/빌드/PIE 완료가 아니다.

## 2026-10-11 — ARCH-89 원작 사운드 재생 계약 (적용 전)

현재 사운드 직접 구현 요청은 기존 GAS/Ability/Task/CMC/피해 승인 경계를 유지하는 Presentation 확장이다. 새 runtime 파일은 stateless Audio Notify/NotifyState h·cpp4개다. 데이터는 SoundCue·SoundWave·엔진 attenuation/concurrency가 소유한다. 일반 유한음은 실제 Actor의 엔진 AudioComponent가 원본 끝음까지 재생·자동 정리하며, 반복/명시적 stop 구간은 실제 Mesh와 engine notify occurrence ID의 component tag로 자기 컴포넌트만 찾아 종료한다. Notify UObject에 공유 재생 상태나 원장, 전역 manager/FSM/MainAnimInstance 상태·Tick을 추가하지 않는다. Actor 파괴는 엔진 StopWhenOwnerDestroyed, 애니메이션 교체/취소는 NotifyState End로 정리한다.

원본 xxAkEvent/Footstep/PostAudioEvent/UntilAnimEnd의 시작·종료는 원본 AnimationTrack의 trim/rate/loop 및 SourceDilationCurve를 현행 baked sequence에 한 번만 변환한다. Montage와 그 child sequence에 같은 사운드를 중복 저작하지 않는다. 발소리의 실제 지면 선택은 CMC 범위 trace/PhysicalMaterial·기존 Snow owner이며 원본 physical_material switch를 native SoundCue 정수 파라미터로 선택한다. 피해/막기 소리는 기존 FKZAttackCollisionWindow의 선택적인 SoundBase2개와 실제 승인 결과만 소비한다. 공격 실패/단순 이동은 적중 소리를 만들지 않는다.

Wwise bank mix의 gain/delay/layer·한국어 kz 분기와 랜덤 변형은 오프라인 복원 후 UE cue로 재생한다. 수학적 unity1 및 cm/s 단위 변환을 튜닝으로 혼동하지 않는다. 원본 수치가 없는 취소 anti-click fade·native 공간/리버브/voice budget은 조정 가능한 명시적 임시 표현 설정으로 기록하고 원작 SDK·플러그인 DSP 동일성으로 표현하지 않는다. 후처리/조명·눈/RootMotion/UI/gameplay 수치는 이번 사운드 작업으로 되돌리지 않는다. 이 절은 적용 전 계약이며 import/build/PIE 완료가 아니다.


## 2026-10-12 ? ARCH-89 ?? ??? ??? ?? ?? ??

?? Player_Hit? skin/metal/leather/rock/yetuga ???? ??? ?? ????. ?? FKZHitReactionSettings? ???? ImpactSound1?? ?? ?? ??? HP ??? Combo/SkillObject/Brutal ? ???? ?? Definition?? ?? ???? ????. Clip? ?? VO/weapon common impact? ?? ???? ???? miss/guard/stamina-only?? body hit? ??? ???. ?? runtime class/file0, ?? gameplay ??/manager/tick0??. ??? ??? ?? ???? ?? ??? ??7 Definition? ???? ??? native adapter?? ?? native caller? ???? ???? ???. Source waveform gain/??? ???? ???mapping? ?? ??? Art? ????.


## 2026-10-12T00:17:33+09:00 — ARCH-89 최소 body hit 계약 UTF-8 보충 / checkpoint

직전 Architecture의 body hit 추가 절은 PowerShell stdin 인코딩으로 일부 문자가 물음표가 되었으므로 이 UTF-8 절로 보충한다. FKZHitReactionSettings의 선택적인 ImpactSound1개는 실제 승인된 HP 피해의 Combo/SkillObject/Brutal 세 소비자가 대상 Definition에서 읽는다. miss/guard/stamina-only는 body hit을 만들지 않는다. 신규 gameplay class/file0·manager/state 사본/tick0이며 source material-name의 현행 family mapping은 native adapter다. 원본 native caller의 동일성은 미확인이다. projectile audio는 기존 SkillObject의 실제 launch/impact/Actor component 수명으로 재생·종료한다.

Build13은 exit0이다. 기존 순수 Audio Notify/NotifyState 두 class/h·cpp4와 현재 owner의 작은 확장, editor-only finalizer 및 DEV PIE test를 적용했다. NativeImport05의 영구 wave 참조 수정은 위 Art checkpoint를 따른다. AudioPIE01 논리 관측 Success와 실제 녹음 peak0을 구분한다. 다음은 BindingAuthor02_Persistent 종료/새 mixer 출력·취소·실제 hit/guard 회귀와 saved 보존 검사다. exact 재개는 ResumeState03.json이며 사용자/다른 task editor 제어0이다.

## 2026-10-12 — ARCH-88 Main 구현 계약

직접 요청의 runtime 수정은 기존 Monster h/cpp, HUD h/cpp, Combo/Brutal accepted-hit 호출6파일이다. 새 runtime class/component/manager/FSM0이다. Source10 전달 중 나머지는 실제 PIE QA3개와 editor-only UnrealEd/Json 의존성이다. Main worker AnimInstance에 ASC/Actor 접근이나 gameplay 상태 사본을 추가하지 않았다.

Monster는 notify occurrence/mesh/AnimInstance receipt를 먼저 설치하고 한 번의 bone-finalize callback으로 첫 particle spawn을 수행한다. end/cancel/EndPlay에서 자기 delegate를 해제한다. 실행 중 callback unregister가 functor를 해제할 수 있으므로 capture를 local로 복사하며, particle factory의 reentry 뒤 receipt를 ID/mesh로 다시 찾는다. 공격 resource/socket/typed offset/rotation과 기존 자료의 권한을 보존한다.

Player Combo는 기존 guard 분기·hit-group/window dedup·GE 성공 뒤 monster에1회의 PlayHitBlood를 호출한다. HP0 대상/빗나감/취소 뒤에는 발생하지 않는다. Product에 HP damage literal0인 유효 공격이 있으므로 성공한 unguarded collision 자체를 blood 조건으로 쓰고 gameplay 값을 새로 채우지 않는다. Brutal은 기존 accepted positive HP producer에서만 같은 owner 함수를 호출한다. 기존 BodyImpactSound·guard/impact audio 코드와 sound notify를 보존했다. broadphase center가 몸 바깥에 있을 수 있으므로 mesh closest physics point, 실패 시 실제 chest socket을 사용한다. finite world PSC가 drain을 소유하고 decal을 만들지 않는다.

Monster death는 ASC HP0을 계속 정본으로 사용한다. normal death montage/paired completion의 기존 FreezeDeathPresentation 뒤 universal dissolve로 transfer하며 완료된 source material receipt/binding을 정리한다. 실제 body/weapon mesh에 MID를 만들고 GT Tick에서 normalized progress를 갱신해3초 TEMP 종료 시 Destroy한다. 재는 actual body bones7곳에서 발생하는 finite world particle이다. 사망 수명과 표시 수명을 GAS/AI/새 enum에 이중 구현하지 않았다. EndPlay가 자기 delegates·MIDs/receipts를 정리하고 engine world PSC는 finite tail을 마친다.

HUD는 player/controller의 기존 GT NativeTick에서 ASC 현재 값을 즉시 foreground에 반영하고 감소 잔상만 .35초 TEMP로 보간한다. 표시 HP/ST는 gameplay 작성자가 아니다. LockOn/B reticle의 공통 position은 actual UI_Chest(Bip001-Spine2)로 매 프레임 projection하고 기존 CanActivate/eligible lock priority/camera targeting 위치는 유지한다. Elite frame 축소 및 원작 alpha의 별도 empty track는 HUD 책임이다. ownership/UnPossess/EndPlay cleanup은 기존 경로를 사용한다. 숫자 원본/TEMP 및 resource/package 출처는 Art 정본 마지막 절에 분리 기록했다.

실제 Main build/saved/Attack198·1577/death6·actual hit13cases와 UI regression은 성공한 report만 근거로 하며 최종 전수 screenshot 식별/pose framing을 보완한 MainRuntime02가 진행 중이다. original Halberd CorrectionInfos52의 native bone 계약, original shader/VM/pixel/frame parity 및 Shipping performance는 확인 범위 밖이다. 이를 현재 엔진 pose/socket 변환 검증으로 대체해 확인했다고 주장하지 않는다.

## 2026-10-12 — ARCH-88 Main 구현 검증 종료

직전 구현 계약은 Main에 적용됐으며 FinalVerification.json이 MainDeliveredAndFreshVerified다. Source10/asset59/새 runtime0, actual finalized pose Attack198/1577, normal/paired death6, accepted hit13 case 및 HalberdElite UI02, latest saved audit가 통과했다. 각 실제 loaded DLL/Source·asset hash와 동시 audio GUID 후속 갱신의 구분은 Engineering continuity 완료 절을 따른다. 새 Manager/FSM/AnimInstance gameplay 사본 없이 기존 Tag–Ability/GAS owner·Monster presentation/HUD·cleanup 경계를 유지했다. 필수 구현·Main 검증 잔여0이며 원작 native correction52/stripped shader/pixel/frame parity와 Shipping 성능은 별도 미확인이다.


## 2026-10-12 — ARCH-88 사진 기준 혈액/지면 혈흔 후속 계약

사용자의 첨부 Reference.png 직접 수정 요청으로 기존 floor blood 전면 억제를 이번 피격 표현에 한해 대체한다. 기존 accepted-hit producer와 AKZMonster::PlayHitBlood, 엔진 Cascade/SpawnDecalAtLocation을 재사용한다. 실제 피해 승인·dedup·취소·GAS/사망/UI/사운드는 그대로이며 새 runtime 파일/class/manager0이다. GT에서 현재 피격 지점→월드 지면 trace로 표면과 normal을 확인하고 해당 지면에만 불규칙한 원본 texture의 혈흔을 유한 수명으로 생성한다. 피 분사는 큰 sheet/덩어리와 미세 방울의 복수 층을 기존 HitBloodEffect asset에 저작한다. 설정은 현행 Monster Class Defaults/particle/material parameters에 모으고 원작 직접 값과 사진 비교 TEMP를 구분한다. Work에 최신 Main C++를 stage하되 private author/build 의존성은 Main에 전달하지 않는다. Main 사용자 editor PID19752는 제어하지 않으며 fresh own editor에서 검증한다. 이 절은 착수 계약으로 아직 적용/build/PIE 완료가 아니다. 근거·exact baseline은 Metadata/MonsterBloodReference_20261012/Baseline.json이다.


## 2026-10-12 ? ARCH-90 ??? ?? ?? ?? ?? (?? ?)

?? Guard Ability ??? ?? ?? ?? ?? JustGuard ?? ????. ? runtime class/component/manager/tag? ??? ???. ?? activation? world game time?? ??? release/End?? ???. ?? ??? Start ??? ????? ?? ???? Success/held ??? ?? ?? ?? ???. ?? hit-group/window dedup, unblockable ??? ??? GE/?? ?? cleanup? ????.

Guard_Start ?? Notifies[3]? BeginJustGuard 0/Duration .292? ?? InGame Player_Guard_Start inverse_map? ? ? ?? .146?? ????. ?? Normal_Start? baked source mapping? ????? ???? adapter?? ?? Guard_Start ?? Dilation? ?? native ?? ?? ???? ???. JustGuardReduseStaminaPowerRate .5? ??? ?? ??? ???? ??? ??? ?? Definition.ParryStaminaDamage ? ReportAttackParried/Parried pattern ???? ????. ?? ??14? ???? ?? ???5? ???? ???.

Guard/ASC? ?? boolean ?? ??? ???? ?? ? hit producer?? out-parried? ??? ?? GuardSound ??? ???. ?? ??? ??? Guard ???? ?? melee/skill object? ?? ????. ?? Blueprint-callable ? ?? API? ??? ????. ?/? ?? ??? ?? AC_Guard_Suc_Just_L/R ? ??? ??? Def_JustGuard_R/L? ???? source DilationAnimPositions? ? ? bake??. ?? Guard montage? section/notify? ???? ?? audio/guard notifies? ????.

?? PP_Damage_Spray NewJustGuard ? PP_AtkEx_JustGuard? ?? ??? ????. finite world-space weapon flash? UV edge feather? ??? presentation adapter/TEMP?? shared ??? ?? ???? ???. ?? ???? ?? ??? ???? ???. Main editor? ???? ?? ?? Khazan_ParryWork_20261012? ?? writable copy?? author/build/PIE ? ?? Main CAS ????. ?? Source/??? ?? ???PIE ??? ?? ?? ??? ????.


## 2026-10-12T02:04:36+09:00 — ARCH-89 사운드 runtime build·준비본 검증 / Main37 잠금

Build29/current alias2026101303는 성공했고 제품 runtime 및 자체 audio editor/QA는 그 build input과 동일하다. 이후 다른 작업의 DEV2 변경은 보존하고 전체 현재 Source 일치와 구분한다. Notify2 class/새 runtime4 및 기존 owner6파일의 작은 확장으로 타이밍·확정 피해/guard·비행음·cancel/EndPlay를 연결했다. 실제 family/cancel/loop/flight 및 기존 gameplay 회귀 출력은 검증됐다. Python 배열 사본 재기록 누락의37 asset 수정본은 prepared 검증 완료·Main 잠금 대기이며 complete=false다. 상세 계약·현재/원작 미확인 범위와 exact resume는 Engineering continuity 마지막 ARCH-89 및 ResumeState05/PreparedVerification01을 따른다. 사용자/foreign editor 제어0, 무관한 Source/feature rollback0이다.


## 2026-10-12 — ARCH-90 패링 준비본: 실제 검증 / Main 잠금

기존 Guard/ASC/Combo/MonsterSkillObject 6 runtime 파일의 작은 확장으로 시작 후 0.146초 전방 blockable 적중을 패링한다. 원작 raw 0.292초를 현재 GuardStart inverse_map으로 계산했으며 비용 배율 0.5와 effect detach 0.06초는 직접 source 값이다. 기존 몬스터 Definition의 사용자 결정 ParryStaminaDamage와 Pattern Parried/고갈 정책을 재사용한다. 새 runtime class/file/태그/GE/Manager는 0개이며 새 DEV test 1개다. Source·책임·cleanup·값 구분·에디터 설정·검증은 [PARRY_IMPLEMENTATION_20261012.md](PARRY_IMPLEMENTATION_20261012.md)에 기록했다.

task-owned ParryWork의 실제 melee/field 15개 상황과 6종 몬스터, 고갈/좌측 response/비용/동일 HitGroup/독립 연타/Release/Cancel/UnPossess를 확인했다. 기존 Guard와 PlayerAttackCollision도 성공했다. 기존 5개 재생 segment·notify는 fresh reload로 동일하며 Montage refresh의 Suc_R 파생 cache 차이는 따로 기록했다. 원작 normal Guard의 JustGuard 설정을 그대로 복원한 것이 아니라 사용자 요청에 따른 시작 창 adapter다.

**Main 구현 반영은 미완료다.** GA_Player_Guard와 AM_DAS_Player_Guard가 기존 Main editor PID19752의 Windows 공유 잠금(error32)으로 대기한다. 대상 SHA 충돌0이며 Source·package를 부분 복사하지 않았다. 사용자/foreign editor 종료·제어0, private DLL/과거 manifest 복원0이다. 현재 잠금과 candidate SHA는 Metadata/Parry_20261012/DeliveryPreflight.json, 준비본 검증과 정확한 재개는 PreparedVerification.json/ResumeState.json을 따른다.



## 2026-10-12T04:22:44+09:00 — ARCH-88 사진 기준 혈액·바닥 혈흔 Main 완료

첨부 사진 후속의 runtime2(KZMonster h/cpp)/기존 DEV2/신규 유효 package5를 Main에 적용하고 검증했다. 새 runtime file/class/component/manager0이다. 이전 floor blood 제거 정책은 최신 사진 지시에 따라 accepted hit의 불규칙한 새 지면 혈흔에 한해 대체한다. 원작 notify42/mesh decal16의 제거는 유지하므로 그때 잘못 배치되던 데칼을 복구하지 않는다. 기존 accepted/dedup producer와 GAS 피해·guard·취소·사망/UI/사운드 실행 수명은 변경하지 않았다.

혈액은 현행 피해 receiver capsule의 실제 scaled radius/half-height/월드 축과 Contact 높이의 최근접 축점을 사용한다. 6종 Mesh PhysicsAsset=None을 MainSnowVisual07 실제 값으로 확인해 몸 안쪽 chest pivot 대신 capsule 표면에서 공격자 쪽으로 분사한다. raw skeletal skin 표면을 복원한 것으로 표현하지 않는다. 새 위치/방향 수치를 임의로 넣지 않고 현행 capsule geometry를 계산에 사용했다. floor는 this/attacker를 제외한 static/dynamic complex trace와 CMC walkable normal로 확정한다. 분사 축을 지면 접선으로 투영하고 projector X를 -normal에 맞춘다. 기존 KZSnowDeformation.GetSnowSurfaceHeight/SurfaceContactSamples의 layer/rim을 읽어 렌더된 눈과 바닥 양쪽을 포함하며 Snow40cm·변형·맵/조명 정책을 바꾸지 않았다.

GT BeginPlay는 기존 혈액 재질의 EnsureIsComplete만 호출한다. editor ODSC의 ready=1/shaderMap=1이어도 complete=0인 상태에서 첫 피격이 fallback 사각형을 그리던 문제를 실제 값과 첫 프레임 비교로 확인했다. background만 제출한 MainSnowVisual05의 첫 흐린 색도 보존했고, 완비는 hit 전에 수행한다. cooked shader 준비를 엔진 cache가 소유하며 Actor별 새로운 timer/상태/handle을 추가하지 않았다. Blood PSC와 월드 Decal은 유한 engine 수명으로 drain/fade하며 피해자 사망·EndPlay에 묶이지 않는다.

MainBuild15/current module2026101254 input 동일·exit0, MainSaved11 save0/CDO6/재질·gamma, MainSnowVisual11 실제 RHI6종/24혈액·12소멸/기울어진 바닥·뜬 피격 무데칼·피해자 제거 뒤 유지·fade destroy, MainActualHits04 실제 collision13의 burst/decal/dedup/miss/cancel/HP0/lower-clamp/Spin7/OverFury19가 통과했다. 마지막 두 RHI의 loaded module/Source는 build와 같으며 QA COLD_FIRST=1로 검사 전 재질 완비 강제를 하지 않았다. 사용자 Main PID19752는 종료/reload/reset하지 않았으므로 정상 재시작으로 새 C++를 로딩해야 한다. 원작 native/pixel/frame parity, Shipping stress, multiplayer는 주장하지 않는다. 정확한 SHA·사진·수치/한계·재개는 Metadata/MonsterBloodReference_20261012/FinalVerification.json, ResumeState03.json과 Art 정본 최신 절을 따른다.


최종 지면 마스크는 rendered-depth AbsoluteWorldPosition의 ddx/ddy 외적으로 receiver pixel normal을 계산해 abs(normal.Z)>=실제 CMC WalkableFloorZ인 면에만 적용한다. producer가 기존 CMC 값을 MID의 BloodWalkableFloorZ에 쓰며 material의 default0은 초기화 값이다. 전역 Snow 변형을 수정하지 않고 수직 옆면의 붉은 늘어짐을 제외했다.

MainActualHits03의 oversized QA capsule은 Spin5/7·Fury16/19 ground를 생성했다. 기존 맵의 경사·빈 곳으로 capsule 표면이 이동한 fixture 문제여서 runtime 지면 reject를 약화시키지 않았다. DEV fixture만 실제 GeometryBound+oversized radius margin/target offset으로 범위를 계산한 전용 평면과 QA 높이10000cm/두께20cm 위에서 검사하도록 수정했다. cleanup은 평면 제거·원래 Pawn/Ability/attributes/transform 복구를 유지한다. 최종 MainActualHits04의13개 검사는 이 평면에서 actual montage/collision/HP/burst/ground를 검증하고 실제 눈 맵의 slope/void reject는 MainSnowVisual11에서 따로 검증했다.


## 2026-10-12T08:17:34+09:00 — ARCH-90 패링 Main 적용·fresh 검증 완료

이전 준비본/Main 잠금 대기는 패링 범위에서 해소됐다. Main Source7(runtime6/DEV1)/package13(기존2/신규11)을 SHA 확인·백업 후 전달했다. 현재 전체 Main Source/Config로 MainBuild02가 성공한 뒤 일반 stock build가 현재 모듈 UnrealEditor-Khazan.dll을 선택했다. 이를 과거 suffix로 되돌리지 않고 현재 모듈에서도 다시 검증했으며 actual loaded DLL과 동일한 Source/13 asset SHA가 FinalVerification.json에 결속됐다. MainBuild01은 copy2의 과거 mtime 때문에 구 UHT PROLOG13/BODY16을 재사용하여 실패했다. 두 전달 헤더의 시각만 갱신해 PROLOG15/BODY18을 생성했고 제품 코드 내용은 바꾸지 않았다. 후속 전달 도구는 현재 write time을 사용한다.

새 MainPIE02의 Parry15개 상황/6종 Definition 소비·고갈·비용·연타·이동 Guard·좌측 response·release/cancel/UnPossess, 기존 Guard와 PlayerAttackCollision 회귀가 모두 성공했다. MainSavedAudit02는 저장0으로 설정/원본 5 playback segment·notify/7 section/source tag를 reload 검사했다. 실제 .13/.24초 화면에서 모션/weapon contact flash/연속 alpha를 직접 검수했다. 정상 가드 후 성공으로 창을 다시 열지 않으며 전방 blockable 공격만 패링한다. 기본 .146초는 기존 source→current inverse_map 계산, 비용 .5와 detach .06초는 source 값, 몬스터 ST 피해는 기존 Definition 사용자 결정이다.

이후 혈액 작업의 KZMonster runtime2/기존 DEV2와 모든 다른 Source/Config를 보존했다. 사용자/foreign editor 제어0·private DLL 복원0·Audio Notify 수정0이다. 초기 RHI에 GPU memory budget/낮은 FPS 표시가 관측됐으며 이번 fixed-step 기능 검사로 성능을 검증했다고 주장하지 않는다. 실제 스피커 출력(-nosound), 원작 shader/pixel/impact-point 완전 일치와 Shipping/network는 미확인이다. 필수 잔여0이며 최신 결과는 Metadata/Parry_20261012/FinalVerification.json과 ResumeState.json을 따른다. 과거 전체 author/추출/옛 alias를 다시 적용하지 않는다.



## 2026-10-12T09:50:12+09:00 — ARCH-91 몬스터 Root/공격 판정/이펙트 후속 검사 중

사용자의 직접 수정 요청이다. 최신 Main의 6종 실제 소비자를 재조회했다: 시퀀스395/Definition57/Node220/window405/montage126. MainUsageAudit02/RootAudit는 asset save0/dirty0이며 모두 EnableRootMotion/ForceRootLock=true, true skeleton root index0/track0 정상이다. pelvis 등의 child 움직임184개를 root 이관 근거로 사용하지 않는다. 아직 런타임의 모든 root 이동이 정상이라고 주장하지 않는다.

기존 ComboAction·엔진 timer/shape·GAS dedup/피해·Monster/Notify의 표시 수명을 재사용한다. private에서 닫힌 끝 경계의 재검사와 마지막 window 이후 callback 예약을 차단하고, 기존 actor 축/locked-root baked collision 좌표에 현행 mesh relative scale을 한 번 반영했다. Source339 pose 비교는 actor 축의 root-stripped anchor가 원본 baked anchor와 맞으며 mesh yaw/root travel을 다시 더하면 오차가 커짐을 확인했다. 새 gameplay 수치를 넣지 않고 실제 body transform을 사용한다. VFX는 Monster의 socket 없는 actor 기준/실제 몸 크기와 source-correction의 같은 프레임 final bone을 사용하도록 기존 owner를 보완했다. 새 runtime file/class/manager0이다. LatestSourceTime은 GT notify clock→GT bone-finalize의 실제 지연 소비값이며 End/취소/EndPlay의 기존 delegate cleanup을 사용한다. Player/audio/UI/혈액·사망 값은 보존한다.

현재 Main Source/asset 수정0이다. Main을 idle GiantFallWork에 한 번 snapshot했고 baseline native late hit fixture를 보존했다. BaselineLateHit01의 paused-boundary HP7과 world-clock 기반 normal/OverFury 실패를 구분한다. QA를 실제 montage clock 기준으로 보완한 FixBuild01은 성공·input동일이고 FixedLateHit01이 실행 중이다. giant PatternMoves54의800/2000cm vertical curves와 Walking 소비의 실제 확인, six-family runtime/FX/저장 보존/CAS Main 전달·fresh build/실제 테스트가 남는다. 현재 상태/실패/정확한 다음 절차는 Metadata/MonsterRootCollisionRepair_20261012/ResumeState01.json을 따른다. 완료된 old stage/author/delivery를 반복하거나 private DLL을 Main에 전달하지 않는다.


## 2026-10-12T10:45:24+09:00 — ARCH-91 실제 원인 확정·private 검증 / Main 미반영
9:50의 Root 옵션·track 정상 판정은 루트 잠금 포즈 정렬의 완료 판정이 아니었다. 실제 사용395개(몸체392/별도 prop3)를 메시에서 시작·중간·끝1176포즈로 검사했다. AnimFirstFrame 잠금이 누적 시작 root 좌표를 유지했고, Yetuga ChargeTackle_End 7157.4663cm / Apes Run_Loop_Stone 5157.4663cm가 실제 몸체에서 재현됐다. 현재 imported RAW Root 첫 transform과 skeleton reference transform의 차이를 RootLockPlan.json에 고정하고, 88개 RootMotionRootLock만 RefPose로 변경했다. EnableRootMotion/ForceRootLock/normalized scale, raw channels, timing, montage/definition/window/damage/group/audio는 유지한다. 원작 신규 튜닝값이 아니라 UE FRootMotionReset의 기준 포즈 adapter이며 raw source key를 transfer/재작성하지 않았다.
RootAssetsBefore exact SHA backup / disposable duplicate probe / fresh native RootPreservationAfter02 Success 완료다. 몸체392개 전체 DataModel(모든 track/key/curve/attribute) 및 notify event·notify object 직렬화 SHA가 변경 전과 전부 동일하다. raw 판정 .01cm/.001deg와 기존 compressed 기술 허용 .01cm/1e-4rad를 구분한다. RoundAttack의 기존 .0020149deg 압축 오차만 raw tolerance를 잘못 적용한 첫 QA 실패였으며 해당 에셋을 추가 변경하지 않았다. collider는 source actor axes/root-stripped geometry에 live mesh relative scale을 한 번 곱한다. 마지막 window End 동등 경계와 이후 timer를 닫아 paused-end late query를 차단한다. monster socket 없는 VFX는 actor rotation + mesh origin, local offset/size는 live body scale, source correction은 current finalized bone pose를 소비한다. LatestSourceTime은 기존 receipt 내부 GT notify→GT bone-finalize 전달 값이다. 새 runtime file/class/manager0이다.
VerticalPattern.PIE는 기존 Walking/RMS 경로에서 원본800cm 곡선을 소비하며 실제 capsule +659.906cm/관측1.51555s를 확인했다. 최대 곡선 값의 정확 재현이나 전체 궤적 일치 판정이 아니며, Flying mode 전환을 제안/적용하지 않는다. 기존 이동 소스를 보존한다. common PlayerAttackCollision 실제16경로(종료·pause·cancel·Spin7/Fury19) Success다. SixFamilyContacts02는30경로중 Shield case4에 별도 Step1 HP10이 섞였다. source log로 기존 controller의 deferred StartMonsterLogic 재시작을 확인하고 검사 소유 controller tick을 끈 fixture03을 실행중이다. 게임 AI는 변경하지 않았다.
현재 Main Source/asset 반영0. private FinalPrivateBuild04 Success/input unchanged; six contacts03 및 all198 attack assets/current-pose correction/사망 검사는 실행중이다. 재개는 Metadata/MonsterRootCollisionRepair_20261012/ResumeState02.json을 따른다. 저장된 baseline/failed 로그를 삭제하거나 stage/author를 무조건 재실행하지 않는다. Main에는 현재 전체 Source로 canonical build하며 오래된 private DLL/Config/다른 작업을 전달하지 않는다.


## 2026-10-12T11:04:18+09:00 — ARCH-91 Root·공격 콜라이더·VFX Main 완료
Main에 Source7(runtime4/DEV3) 및 RootMotionRootLock 옵션만 바꾼 Animation88 package를 exact SHA/CAS로 반영했다. 새 runtime file/class/manager0, 다른 baseline610파일 보존, private DLL/Config 전달0. MainBuild01은 source 오류 없이 PCH virtual-memory C3859/C1076로 실패했고, 병렬1/noXGE MainBuild02는 Succeeded/input unchanged다. 현재 canonical UnrealEditor-Khazan.dll SHA `e14ca4b34c8a8a8042c2087fca2e646196b51e617d906c1884bee4e6c29cf511`를 사용한다.
실제 사용395 Root enabled/force lock/true-root·track0 및 Body392의1176포즈를 확인했다. 첫 프레임 누적 origin88개만 RefPose lock으로 정렬했으며 근거는 RootLockPlan의 imported RAW root first transform와 skeleton reference pose/UE FRootMotionReset이다. RootAssetBefore 및 MainBefore 백업을 보존한다. 전체 DataModel 모든 key/curve/attribute와 notify event/object SHA392개가 변경 전=private 후=Main fresh로 동일하다. source montage126/definition57/node220/window405의 geometry key·time·HP/Stamina·group·audio와 rate/나머지옵션이 fresh saved audit에서 동일하다. Props3는 다른 skeleton으로 body1176포즈에서 분리하고395 옵션/track audit에 포함했다.
Main actual RootPoses/MonsterHits30/PlayerAttackCollision16 Success. monster30은6종별 한 window 안1회 / 종료 후접근0 / exact-end pause후접근0 / 취소후접근0 / live mesh scale와actor yaw 반영을 실제 HP GE로 확인한다. player16의 기존 Spin7/Fury19와blood13 기반행동도 보존한다. source scale/last-End 경계·timer 종료만 기존 ComboAction에 보완했다. VFX198 assets/1577 source occurrences 및Death6는 동일 delivered Source의 private 실제RHI Success, finite world transforms / deterministic uncorrected source geometry max position3.46e-13cm·angle4.83e-6deg / template identity / body size를 확인했다. 이 보고서의 active correction-curve row는0이므로 해당 branch의 per-pose 실행을 실제 데이터 검증했다고 표현하지 않는다. source 없는 VFX actor axes/mesh origin 및 body scale은 적용했으며 curve branch는 기존 receipt의 latest GT clock→finalized-bone callback으로 구조 보완했다. 원작 native shader/pixel parity·전체두레벨연속전투·network는 검증 완료 범위가 아니다.
Main 파일·canonical build·fresh saved/actual runtime 완료. FinalVerification.json / ResumeState03.json 및 exact Delivered95를 재개 정본으로 읽는다. stage/old alias/full author/retime/reimport를 반복하지 않는다. Main editor 정상 재시작 후 직접 Play에서 green debug volume이 실제 공격 window에서만 나타나고 칼의 크기·방향/몸체 alignment를 확인할 수 있다.
<!-- CombatFinishFollowup_20261012_contract -->
## 2026-10-12 — ARCH-92 사망 종료 포즈·브루탈 접촉·액션 VFX 후속 계약

사용자의 직접 수정 요청이다. 기존 Monster의 사망 표시 소유권, Brutal/Exhaustion의 짝 실행, Action의 효과 receipt와 Notify 데이터를 재사용한다. 새 runtime class/manager/공유 gameplay 상태는 만들지 않는다. HP/Dead·피해·공격 창·원본 이동/애니메이션 채널은 유지한다. 사망 interruption을 정상 완료로 취급해 현재 포즈를 즉시 멈추는 경로를 수정하고 실제 terminal pose를 검사한다. 브루탈 접촉 효과는 실제 두 Pawn의 접촉 공간에 배치한다. 내려찍기와 다른 액션의 효과는 기존 타이밍·수명 소비자에 연결한다. 혈흔의 방사형 확산은 Monster Class Defaults의 표시 설정에 모으며 새 숫자는 어시스턴트 임시 표현값으로 명시한다.

착수 시 Main editor는 종료돼 있었고 baseline Source121과 표적 package bytes를 보존했다. Rider debugger는 KZMonster.cpp254/302에 대해 실행 코드 연결 실패, startup native frame 미해결을 반환해 사용하지 못했다. owned actual native PIE에서 ordinary death6 정상 terminal pose 오차0, 중단6은 약0.27초의 서 있는 pose를 freeze하고 모델 cm 오차167–441을 재현했다. 이는 중단 경로의 근거이며 전체 사용자 전투에서 중단 발생 빈도를 계측한 것은 아니다. 검증·정확한 재개는 Metadata/CombatFinishFollowup_20261012와 도메인 continuity에 추가한다.


## 2026-10-12T13:16:18+09:00 — ARCH-92 메인 에디터 적용 확인 완료

Rider normal Khazan Run으로 Main PID16504/DevMap을 열었다. read-only RiderLink가 실제 canonical DLL SHA a247fac8a6c457a90d336ceb9ed90a5445bca878295d941b1c5081a375977f9b와 FinalBuild05 일치, 6종 CDO scatter6/radius90–280cm, dirty content/map0를 확인했다. asset save0, PIE 미시작이며 에디터를 열어 둔다. FinalVerification.json은 MainDelivered_Built_Validated_EditorReady, ResumeState04.json은 complete/잔여0이다. 사용자 이전 Main은 착수 때 종료돼 있었고 강제 종료/HotReload/기존 session 저장0이다. 모든 실제 테스트·동일 runtime source·Art TEMP와 원작 한계는 앞선 완료 절을 유지한다.

## 2026-10-12 — ARCH-93 몬스터 확정 피격 섬광으로 범위 교정 (착수 계약)

최신 사용자는 ARCH-92의 모든 공격/회피/착지 색상 확장을 철회하고 실제 몬스터 타격에서만 짧은 플레임 섬광을 요구했다. 기존 Combo/Brutal/SkillObject의 확정 적중 → Monster.PlayHitBlood → world finite Cascade 경로를 재사용한다. 새로운 runtime 파일·class·manager·태그·관측 상태·피해 판정을 추가하지 않는다. 기존 피격 particle의 혈액3 emitter를 보존하고 자체 소유 섬광3 emitter를 추가하므로 공격 유형·중복 방지·취소·miss는 기존 producer 계약을 따른다. 기존 몬스터 혈액/사망/브루탈 위치/자연스러운 바닥 먼지와 source 원본 효과는 유지한다. 최근 추가 KZExtra 색상54 window의 child만 삭제하고 기존 입력/GUID/시각/section/segment를 보존한다. 광원·불꽃 궤적·streak 대신 stationary circular flash/유한 alpha를 사용하며 새로운 표시 숫자는 Art 자산 TEMP다. 정확한 baseline/진행 증거는 Metadata/HitFlashCorrection_20261012에 남긴다. 이는 아직 적용·실제 화면 검증 완료 기록이 아니다.


## 2026-10-12T14:40:04.303632+09:00 — ARCH-94 Apes·Yetuga 원본 분기 구체화 / 짧은 피격·Dodge 무적 계약

사용자의 직접 구현·정밀 테스트 요청이다. 기존 StateTree Task/Condition, AIController, MonsterPattern/Combo Ability, ASC, HitReaction, Dodge와 CharacterDefinition을 재사용한다. gameplay 상태의 원본은 ASC이며 새 FSM/Manager/Component를 만들지 않는다. Yetuga 원본 BT의 조건 true/false, selector/sequence 순서, MoveTo→UseSkill, 선택 substep 및 LockOnMove를 현재 평탄화 후보 대신 StateTree 실행 경로로 구체화한다. Apes는 HeinMach Early 원본 AI·이동/후속과 실제 피격 대응 자료를 우선한다. 원본 custom BT native 기본값/RNG/Spell·부위 상태 소비와 Level 시작 trigger의 미확인 항목을 임의로 원작 확정값이라고 부르지 않는다. 구조 일치·저장값 일치·실제 branch 실행·원작 전체 동일성을 분리한다.

플레이어 피격 제어 제한은 Definition의 조정 가능한 0.1초 TEMP로 시작한다(원작값 아님). HitReaction의 자기 몽타주/RootMotionSource/이동mode/제약을 짧은 deadline에서 정리하며 몬스터와 Shield 수명은 유지한다. Dodge 0.1초는 사용자 직접 지정값이며 Dodge Ability의 자기 ASC tag 기여·시작 시각·timer가 소유하고 정상/취소/실패/재활성화/UnPossess에서 자기 기여만 회수한다. 실제 melee/projectile/field/직접 피해 producer는 Guard/HP 적용 전에 공통 ASC 승인 경로에서 이를 소비한다. 한 공격 group의 무적 접촉은 1회 소비하며 HP/ST/HitReaction/확정 적중 이벤트를 만들지 않는다. 실제 Dodge 방어 결과만 성공 SFX/VFX를 생성하고 Dodge 자체 표현은 실행 수명에 결속한다. 새 표현 숫자는 Art TEMP와 사용자/원본 값으로 분리한다.

작업은 C:\Users\user\Desktop\GitProject\Khazan_BeastDodgeWork_20261012\Khazan의 Source/Config 및 소유 Content(Monsters/Data/Bluprints) 복사본에서 시작한다. 나머지 Content junction은 읽기 전용으로 다루고 저장하지 않는다. 현재 Main baseline SHA/현행 canonical을 Before/Baseline에 보존했다. 현재 사용자 에디터 PID16504를 저장·종료·PIE·LiveCoding하지 않는다. 준비·빌드·정밀 native 실행·회귀·RHI 이후 정확한 변경만 Main CAS 전달하며 동시 외부 변경과 과거 private DLL을 덮지 않는다. 아직 적용/빌드/PIE 완료가 아니다.

## 2026-10-12 — ARCH-95 섬광 철회·전투 표현/판정 후속 착수

최신 직접 수정 요청으로 ARCH-93의 stationary flash를 철회한다. 이전 추가54 무조건 색상 창 제거는 유지한다. 기존 확정 피해/Guard/Monster presentation/CombatEffect receipt·Combo window·CMC를 재사용한다. 새 runtime class/component/manager/tag0이다. 원작 불꽃/불똥을 승인된 적중·패링·플레이어 피격에만 연결하고, 인간형 Slash·찌르기와 Player Slash는 사용자 지정 Niagara 두 경로를 사용한다. 기존 native Niagara 확장 준비본의 작은 diff를 현 Main에 합치며 원본 이벤트/피해/공격 창/오디오/Root를 보존한다.

패링 성공은 기존 L/R source clip·Guard task의 수명으로 표시하고 입력 Release가 이미 승인된 성공 포즈를 즉시 잘라 버리지 않도록 한다. Spin의 behind/lateral baked center를 actor front로 교정하며 Fury의 앞쪽 확장은 원본 gameplay 검증값이 아닌 조정 가능한 asset TEMP다. 몬스터 primitive는 stepping/walkable floor와 movement base를 허용하지 않는다. 내려찍기 피격은 기존 Knockback 응답을 재사용한다. 표시 숫자와 원본/계산값은 Art author receipt로, 충돌 TEMP와 계산식은 Engineering collision 정본으로 분리한다. 기존 Main Source/에셋·다른 작업 변경을 baseline/CAS로 보존한다. 정확한 상태는 Metadata/CombatImpactUpgrade_20261012/ResumeState.json이며 이 절은 완료 기록이 아니다.


## 2026-10-12T18:08:30.145524+09:00 — ARCH-96 몬스터 넉백·애니메이션 시계 정규화 착수

사용자의 직접 수정 요청이다. 기존 HitReaction Ability/JumpForce Task/CharacterDefinition과 원인별 root-mode·이동 제약·취소 정리를 재사용한다. 새 runtime class/file/manager/tag0이며 기존 runtime2파일에 선택적인 KnockbackTimeMappingCurve만 추가한다. 해당 정규화 곡선은 몬스터4종의 기존 수평 거리·HitLand 종료 시간 안에서 속도를 줄이는 표현 TEMP이고, Player/Launch/Giant 대체 반응은 기존 경로를 유지한다. 원작 UseCurve 및 CV_common_groundKnock_strong 참조는 확보됐지만 곡선 key/native 스케일의 직접 근거는 없다. 미확인 원작 숫자로 표현하지 않는다.

시퀀스 시계 변경은 Art/Animation 작업이며 Frame-index bone keys를 재샘플링하지 않는다. 새/기존 duration 비율로 RateScale과 local notify/marker 시각, montage source trim을 같이 변환해 실제 playback 시간과 montage world event/section/공격 판정 시각을 보존한다. 데이터 모델·플랫폼 sampling rate와 실제 엔진 공통 몽타주 rate를 별도로 검사한다. 계획·백업·진행 상태는 Metadata/AnimationTimingKnockback_20261012이며 Main 반영 완료가 아니다.


## 2026-10-12T19:30:36.993088+09:00 — ARCH-96 몬스터 넉백·전체 FPS Main 완료

Main516행=기존 runtime2(KZHitReactionAbility.cpp/CharacterDefinition h)+DEV2/Build editor dependency1+asset511을 선택 적용하고 새 Main build/reload/실제 RHI를 확인했다. 기존 ASC·HitReaction/JumpForce Task·Definition과 취소/root-mode·회복 수명을 재사용했다. 새 runtime class/file/manager/tag0, private DLL·Config 전달0이다. 다른 작업의 Player0.1초 제어 제한/ground-hit 분류/원작 StateTree 추가와 최신 공격 VFX88개를 보존했다.

MainBuild01 exit0, MainSaved01의461 sequence3854855 bone key/notify GUID·시각·158 montage의 actual sampling 및 재생 시간 차이0, MainKnockback01의6종11case(인간 F/B8/Giant2/벽1)·회복/재피격/cancel/root-mode 복구, 기존 실제 monster collision 회귀가 성공했다. MainInventory01의 전체2674 sequence/158 montage에서 소수 sequence/model·sampling0,100000fps fallback0이다. native loaded module/516SHA/각 evidence는 Metadata/AnimationTimingKnockback_20261012/FinalVerification.json에 결속했다.

인간4종은 기존250cm와 실제 HitLand 시간을 유지하며 Definition.KnockbackTimeMappingCurve에서 normalized2u-u² TEMP 감속을 조정한다. baseline 착지 직전 약278–375cm/s의 일정속도 → 최종 약8–28cm/s로 줄어든다. RootSource 제거는 엔진의 MarkedForRemoval/다음 이동 tick 삭제를 구분해 검증했다. Apes/Yetuga는 NoAir/NoBlow 대체 clip의 짝 grapple root 이동을 해당 실행 instance만 PushDisableRootMotion으로 억제하여 baseline−278.01/−222.11cm →0cm다. source clip/raw/root 옵션 및 Short fallback·정상 Launch Task는 보존했다.

필수 잔여0이다. 현재 editor는 정상 재시작으로 새 C++/asset cache를 로딩한다. 사용자/foreign editor 제어0이며 이전 pending·failed trial 기록은 이 완료로 대체한다. 원작 curve keys/전체 pose·native/network/shipping parity는 미확인이고 TEMP를 원작 수치라고 부르지 않는다. 과거 author/추출/원본 retime/root repair/옛 DLL 전달을 다시 실행하지 않는다.


## 2026-10-12T19:50:49.391255+09:00 — ARCH-94 실제 소유 계약·Main 검증

기존 ASC/Ability/Task/AIController/StateTree를 확장해 실제 Main에 반영했다. 새 runtime 파일·class·manager0, 개발 QA3다. Yetuga source121노드→compiled173상태, Apes9상태이며 Definition.OriginalPatternStateTree가 기존 배치 override보다 우선한다. 실행 task는 실제 PatternRun의 정상/취소 결과를 성공/실패로 반환하고 선택 실패를 원본 후속에 연결한다. passive는 AIController가 실제 accepted HP 피해 이력·pending을 소유하며 죽음/EndPlay/대상 변경 정리를 수행한다.

착수 계약의 Definition 피격 시간 제안은 실제 `KZHitReactionAbility.PlayerControlLockSeconds` EditDefaultsOnly 소유로 정정한다. Player non-shield의 마지막 실행부터0.1초는 어시스턴트 TEMP이며 자기 montage/RMS/제약/root mode를 끝내 다음 입력을 허용한다. Dodge0.1초는 사용자 지정값이고 Dodge Ability의 실제 world-time deadline/자기 ASC 기여·timer가 소유한다. 모든 실제 피해 producer는 ASC의 승인 경로를 통해 Guard/피해 전에 이를 소비하고 성공 표현은 실행당1회다. 취소/실패/재피격·타 원인 기여 보존을 검증했다. 동시 ARCH-96 curve/자기 montage root 억제는 보존한다.

MainBuild04 Exit0/runtime hash 일치, 최신 native 감사·passive·방어11·복구6·47개 기술·PlayerAttackCollision 및 Guard/Parry/GiantFall 성공의 정확 증거는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. 원작 native RNG/abort/defaults와 Group1 producer·selected float·물리 전체 동일성은 미확인/명시적 잔여다. 구조/원시 field/현재 UE 실행 성공을 원작 전체 무오차로 기록하지 않는다.

<!-- BeastDodge_20261012_MainCompleted -->

## 2026-10-12 — ARCH-95 최신 사용자 교정: 몬스터 원복·플레이어 추가 Slash

사용자 최신 지시는 앞선 인간형 Slash/Sting 교체 및 플레이어 Slash 교체를 철회한다. 몬스터120개 occurrence의 기존 효과 설정을 복구하고 지정 Niagara 두 리소스를 몬스터에 연결하지 않는다. Player 기존50 start/stop쌍의 resource·위치·회전·소켓·수명 정책을 복구하고 별도 child의 추가 Slash만 기존 Action receipt로 재생한다. 기존 notify GUID/clock와 ARCH-96 정수 FPS·넉백, 확정 타격 불꽃·패링 포즈·Spin/Fury·plunge 복구는 유지한다. 전체 패키지의 과거 bytes를 덮어쓰지 않고 변경한 표현 field만 복구한다.

추가 Slash의 위치와 각도는 actor-front 고정 offset을 사용하지 않는다. 실제 장착 무기의 현재 finalized pose와 휘두름 궤적을 확인하고 엔진 attachment/현행 receipt를 우선 사용한다. 필요할 때만 해당 receipt의 pose history와 GT finalized-bone 갱신을 작은 확장으로 추가하며 새 runtime class/component/manager/tag0을 유지한다. 정상 끝·취소·사망·EndPlay에서 기존 receipt의 delegate/FX cleanup을 사용한다. 원작/현재 무기 geometry에서 계산한 값과 표현 TEMP를 분리한다. 최신 진행·정확 재개는 Metadata/CombatImpactUpgrade_20261012의 additive amendment 기록이며 앞선 Monster Niagara33회·replace106 검증은 철회 전 상태의 기록이다.


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

사용자 최신 지시로 몬스터의 지정 Niagara 교체를 철회하고 원본120개 효과 occurrence를 복구했다. Player 원본50 start/stop쌍을 복구하고 별도 KZWeaponSlash child50쌍만 추가했다. immutable before package와220개 객체×21개 수정 field를 비교해 차이0이다. 원래 notify GUID/clock, ARCH-96 FPS·넉백, ARCH-94 방어/AI, SlamDistort·혈액/사망/UI/오디오를 보존했다. 과거 패키지 bytes 전체 또는 private DLL을 Main으로 덮어쓰지 않았다.

추가 Slash는 기존 Action effect receipt와 finalized-bone delegate로 소유한다. 실제 Weapon_L/R 뼈에 reference cutting-edge geometry를 연결하고 successive actor-space tip pose에서 이동을 뺀 swing tangent를 계산한다. FX marker의 별도 animation track은 실제 장착 무기의 대체 pose로 사용하지 않는다. X는 실제 접선, Y는 절삭면이며 requested mesh의200cm reference span/renderer yaw180·centre를 보정한다. Niagara component의 CurveRotation0/CurveScale1·Rotation0만 neutralise하고 shared Niagara asset은 보존한다. 정상/취소/node 교체·사망/UnPossess/EndPlay cleanup은 기존 receipt가 처리한다. 새 runtime class/component/manager/tag0, 새 개발 plunge QA1이다.

Native Player18+Brutal5/실제 승인 hit blood, collision16/Parry17·received-hit feedback/monster-overlap plunge ground·cancel, human33 actual attacks 및 original4-family FX·requested Niagara0이 통과했다. saved100 package에서 original monster120/player100+added player100을 확인했다. 실제 코드·에셋·loaded module 및 모든 검증은 Metadata/CombatImpactUpgrade_20261012/FinalVerification.json이다. 최신 normal Main editor를 열고 loaded module·dirty0 및 설정을 확인했다. Runtime Source가 같은 전체 suite와 DEV-only isolated4 preview를 구분한다. 이전 replace33 검증·실패 camera API·tail assertion은 최신 완료 계약의 근거로 쓰지 않는다.

## 2026-10-13 — ARCH-97 StrongCombo의 인간형 정면 피격 선택 착수

사용자 직접 수정 요청으로 StrongCombo 1·2·3타의 6개 AttackWindows만 VictimFront로 지정한다. ARCH-85의 기존 확정 피해→Character event→HitReaction Ability/Task 계약을 재사용한다. 기존 HitReactionType enum 끝에 VictimFront를 추가해 저장 ordinal을 보존하고, CharacterDefinition.HitReactions.VictimFront에 인간형4종의 기존 AM_BrutalVictimFront를 연결한다. 유효한 설정은 Short event의 OptionalObject로 전달하여 해당 montage를 고정 선택한다. 설정 없는 대상은 현재 StrongCombo의 Knockback으로 fallback한다. 새 runtime 파일/class/tag/manager와 변경 gameplay 수치는 없다.

앞/뒤 랜덤 Knockback/Down→Loop→Getup 및 JumpForce를 이 요청의 인간형 StrongCombo에서 선택하지 않는다. 짝 브루탈 실행은 활성화하지 않으며, 일반 피격 Ability의 자기 montage instance만 root extraction을 억제해 피해자 클립의 paired 이동을 재사용하지 않는다. 기존 피해 승인/dedup/HP·ST/guard/소진·사망 우선/회복·취소 cleanup 및 다른 공격은 유지한다. 실제 Main probe는 StrongAttack01–03 모두 각2 window Knockback이며 기존 정면 피해자 montage의 Damage1·Damage2/원본 segment를 확인했다(Probe02/Probe.json). 현재는 착수 계약이며 적용/build/PIE 완료가 아니다. 변경 전8파일은 Metadata/StrongComboVictimFront_20261013/Baseline.json과 Before에 보존했다.


## 2026-10-13T01:40:50.930443+09:00 — ARCH-97 StrongCombo 인간형 VictimFront Main 완료

사용자 요청을 Main에 적용했다. StrongAttack01–03 각2개, 총6개 AttackWindow만 VictimFront로 변경하고 인간형4종(Swordsman/SwordShield/HeavySwordsman/HalberdElite)의 HitReactions.VictimFront에 기존 AM_BrutalVictimFront를 연결했다. 정면 피해자 모션 Damage1→Damage2를 기존 일반 HitReaction Ability/Task로 고정 재생하며 짝 브루탈을 시작하지 않는다. 해당 자기 montage instance의 paired root travel만 억제하고 Knockback/Launch RMS를 만들지 않는다. 설정 없는 Apes/Yetuga는 이전 Knockback pool을 유지한다. 사망·소진·guard 및 피해 승인/dedup/HP·ST/기존 효과는 기존 계약을 따른다.

runtime3파일/기존 DEV1/저장5package 수정이며 새 runtime file/class/태그/manager 및 새 gameplay 수치0이다. enum을 끝에 추가하여 None/Short/Knockback/Launch의 기존 ordinal을 보존했다. Character의 Short event.OptionalObject가 명시한 montage를 Ability가 선택하며, 정상·재피격·취소의 기존 제약/tag/montage cleanup을 재사용했다. 다른 Player window/몬스터 공격·브루탈/Definition의 원래 모든 피격·이동·AI·grant·소진 설정은 fresh Saved01 readback으로 보존 확인했다. 정면 클립에 execution material notify0도 확인해 추가 사망/재질 adapter를 만들지 않았다.

Build02 exit0/input동일, actual RHI ActualStrong02의4종×3타=12case/24승인 적중·어느 target facing에서도 고정 pose·자기 root-disable·RMS 없음·자연 완료/재피격/취소·다른 Short/Knockback pool·거대형 fallback과 기존 PlayerAttackCollision16 회귀가 성공했다. 실제 loaded module SHA는 `b8f1d59008558802324c3b8e7a1cdaba9a526f02efd36f852788a9fd25bbc4b5`이며 전체 Source/선택5asset·저장/실행 evidence는 Metadata/StrongComboVictimFront_20261013/FinalVerification.json과 Changes.patch다. Actor 크기/높은 평면은 격리 QA fixture이며 원작 pixel/전체 pose 일치 검증으로 표현하지 않는다.

필수 잔여0이다. Probe01의 Python 미노출 property/ActualStrong01의 DEV None-group·blend-out 기대값 실패는 역사로 보존하고02의 성공으로 대체한다. CollisionRegression01은 등록명을 잘못 입력해 matched test0이며 Launch PID/CommandLine을 확인한 task-owned process만 종료했다. 정확한 등록명으로 실행한02의 성공을 근거로 한다. 제품 runtime은 첫 실제 검사 이후 추가 변경0이며 Build02는 DEV 보완이다. 기존 editor process0에서 시작했고 외부/사용자 editor 제어0이다. 이후 조정은 최신 Main Definition의 VictimFront와 Player StrongCombo의6window만 표적 확인한다. 완료한 author/과거 VFX·Root·retime/private DLL 전달을 재실행하지 않는다.


## 2026-10-13 — 몬스터 보조 물리 착수 계약 (ARCH-06/07/10/16 유지)

기존 SkeletalMeshComponent/engine RigidBody/PostProcess가 천·Hair의 포즈·시뮬레이션 수명/EndPlay cleanup을 소유한다. ASC/Ability/Task/CMC/공격·root motion 소유자는 유지한다. 본체는 animated kinematic, 모듈 파츠는 기존 CopyPose와 부모 tick prerequisite/cloth collision source를 사용한다. Gameplay bool/state/새 runtime class·component·manager·tag는 추가하지 않는다. 현재 격리 준비/품질 조사이며 Main 구현 완료가 아니다. 최신 계약과 검증은 MONSTER_SECONDARY_PHYSICS_20261013.md 및 해당 continuity를 따른다.
<!-- MonsterSecondaryPhysics_20261013_intake -->

## 2026-10-13 — ARCH-98 Yetuga/Apes VFX 표시 소유자·단위 보완 착수

사용자는 두 종의 모든 VFX 부착/발걸음 눈/손 내려찍기/브레스/투석/파편·알파 품질을 직접 수정하도록 요청했다. 현행 Main을 Khazan_GiantVFXWork_20261013에 새로 snapshot하고 두 종 Content 및 ApesYetuga Effects만 쓰기 소유했다. Source baseline/237asset SHA는 Metadata/GiantVFX_20261013/Baseline.json, current consumer probe는 Probe02(137sequence/49ParticleSystem/129node)다. 별도 ParticleAlpha/보조 물리 Work와 최신 StrongCombo ARCH97를 보존한다.

확인한 실행 누락: KZAnimNotifyState_MonsterVisual은 AKZMonster만 소비하므로 AKZMonsterSkillObject의 실제 Prop 시퀀스 VFX가 제외된다. IceBreath carrier/field는 현재 Mesh/StaticMesh/Animations가 모두 없고 보이는 표현도 없다. 기존 SkillObject에 source-notify receipt와 선택적 Spawn/Flight/Impact effect를 붙여 실제 객체/애니메이션/발사/충돌 수명에서만 재생한다. 최종 bone pose 후 spawn, 정상/clip 변경/충돌/취소/EndPlay에서 자기 delegate/attached loop만 정리하며 finite world impact tail은 engine이 소유한다. GAS/AI/피해/판정/속도·기간·geometry는 수정하지 않는다. 새 runtime class/file/manager/gameplay tag0이다.

원본 Cascade module의 world-cm size/velocity와 현재 .01 body scale의 혼합도 조사한다. effect data에 particle world-unit 선택값을 작게 추가해 두 종의 검증된 particle만 world-cm로 소비하고, bone/model offset 및 decal/writer geometry는 별도 기존 변환을 유지한다. 기존 Monster finalize correction에서도 같은 particle-scale 계약을 사용한다. 기존 원본 notify GUID/시간·FPS/root tracks/오디오·캡슐/상태·다른 종/Player 기능을 보존한다. 원작 직접 metadata, 단위 adapter 계산, 참조 사진 기반 TEMP 저작을 보고서/Art 정본에 구분한다. 현재는 착수이며 제품 수정·build/actual RHI/Main 완료가 아니다. Art 수치/리소스·원작 그림은 새 GIANT_VFX_REFINEMENT_20261013.md, 실행 결과는 Engineering 문서에 각각 기록한다.


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 보조 물리 Main 완료 (ARCH-06/07/10/16 유지)

기존 engine SkeletalMesh/RigidBody/CopyPose가 보조 포즈·수명·EndPlay를 소유한다. ASC/Ability/Task/CMC/AI 소유자는 그대로다. 새 runtime class/component/manager/tag0이다. 중검의 기존 BeginPlay만 follower 독립 평가·parent tick prerequisite·full parent cloth collision source로 보완했다. 실제99SHA/Main build/saved/RHI/gameplay 완료 정본은 MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json이다. 기존 착수/미반영/검증 대기 기록을 이 완료가 대체한다.
<!-- MonsterSecondaryPhysics_20261013_main_complete -->


## 2026-10-13 ? Heal ?? VFX: ?? Action ?? ?? ???

ARCH-06/07/10/16 ? Action feedback receipt ??? ????. ?? UKZHealAbility.HandleMontageNotify? CombatEffect data/batched child? start/stop ??? ????. ?? active Montage/instance? ????, spawn/dedup/finalized bone?End/??/??/UnPossess cleanup? UKZActionAbility? ?? receipt? ????. ??? runtime class/file/component/manager/tag0??. HP/???/InputEnd/?? ??/??/CMC/?????/root/FPS/audio? ???? ???. ?? Heal DEV ??? ??11 effect/bone??? values?capture/cleanup ??? ????.

?? ??? SB_Kazan_Recovery.UpperAnim=AC_Kazan_Recovery, source particle windows5/mesh3/FT_Trail.G/ShaderLUT??. cooked Niagara VM/editor/material graph ???? ?? native Cascade? ??? ?????? ?? source world/pixel parity? ???? ???. ?? raw Heal ?? ??? ???? source LinkValue? Stow offset? ???. source DilationCurve1.3497161s? ??????? ?? Heal1.4666667s? ????? ???. Source ?? ??/?? clock ??/?? TEMP? ?? Art ??? ????. ?? ?? ??? Main ?? ??? Metadata/HealVFX_20261013/FinalVerification.json ? ResumeState.json?? ????.

## 2026-10-13 — ARCH-95 플레이어 피격 불꽃 제거 착수 (사용자 직접 요청)

플레이어가 맞을 때 추가된 보라/파랑 공통 불꽃을 제거한다. 기존 CharacterDefinition.HitReactions.ImpactEffect의 선택적 수신자 표현을 사용해 Player Definition에서 PP_Combat_HitBurst 참조만 None으로 변경한다. ASC 피해 승인/Guard/Dodge/HP/ST·HitReaction Ability/짧은 제어 제한은 그대로이며 새 runtime 구조/태그/수치0이다. 공격 적중 혈액 PS와 패링 GA가 공유하는 PS 자체는 삭제/변경하지 않는다. 기존 Parry 개발 회귀의 수신자 feedback 기대값은 optional 설정에 맞춰 관측한 실제 컴포넌트 수를 검사한다. 첫 Apply01은 text exporter의 None 필드 생략 처리 때문에 저장 전에 실패했고 Main asset SHA는 그대로다. Apply02 이후 저장 재로드·실제 피격/방어 회귀를 검증하며 현재는 완료 기록이 아니다. 증거는 Metadata/PlayerReceivedHitVFXRemoval_20261013에 분리한다.
## 2026-10-13 — ARCH-95 플레이어 피격 불꽃 제거 Main 완료

앞선 착수의 Player Definition.HitReactions.ImpactEffect→None을 실제 저장·새 프로세스에서 검증했다. 기존 선택적 수신자 표현 계약을 활용해 gameplay runtime Source0/새 구조0/asset1/기존 DEV test1줄이다. ASC 승인·피격 실행/제어 제한·패링·몬스터 적중 공유 에셋은 보존했다. Main Build01 성공, fresh Native02의17사례/실제피격5 효과0/HP·ST·패링 유지가 Success/Exit0이다. 정확한 변경·실패 기록·loaded module SHA는 COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 절과 Metadata/PlayerReceivedHitVFXRemoval_20261013/FinalVerification.json을 따른다. 프로젝트 적용과 현재 열린 사용자 editor의 cached object 갱신을 구분하며 이전 세션에 구효과가 남으면 Player Definition만 Reload한다.

<!-- PlayerReceivedHitVFXRemoval_20261013_complete -->

## 2026-10-13 — ARCH-95 패링 사진 기반 원작 VFX·굴절·카메라 후속 착수

사용자 직접 구현 요청이다. 기존 Guard의 승인 bParried 분기와 ParryImpactEffect를 재사용하며 원작 PS/texture/curve를 표적 확인해 패링 전용 에셋으로 복원한다. 직전 Player Definition의 피격 ImpactEffect=None과 공격 적중 공유 PS는 유지한다. 기존 Guard h/cpp에 선택적 TSubclassOf<UCameraShakeBase>와 local PlayerController의 ClientStartCameraShake 호출만 추가할 계획이다. 새 runtime class/component/manager/tag0이며 finite camera shake 수명은 엔진이 소유한다. 성공 parry마다 발생하고 일반 Guard/실패/피격에서는 시작하지 않는다. 승인된 finite feedback는 input release가 바로 자르지 않는다.

원작 AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L의 xxCameraMod_Shake_0에서 LocOscillation.Y amplitude−100/frequency25/offset zero, FOV amplitude3/frequency25/offset zero, FinalScale.1, FadeIn/Out.17953826s와 Notify.Duration.35907653s를 확인했다. 이것은 원작 field 직접값이고 실제 camera native 시간축/양쪽 모션의 모든 내부 parity를 확정한 것은 아니다. Engine LegacyCameraShake의 대응 field로 finite feedback를 구현하고 raw FinalScale을 amplitude에 한 번 적용한 계산값을 명시한다. Source VFX graph가 cooked에서 stripped되어 shader 재구성과 경계 feather는 원작 직접값이 아닌 표시 TEMP로 분리한다. 사진의 붉은/보라 광막, 굴절 중립 외곽과 Alpha/Depth 교차, 실제 camera 변화·종료/연속패링·Guard/피격 회귀를 모두 확인한 뒤 완료 기록한다. 근거/진행은 Metadata/ParryPhoto_20261013에 남기며 현재 완료가 아니다.

## 2026-10-13 — ARCH-95 OverFury 추가 Slash 철회·나머지 무기 궤적 정렬 착수

사용자 직접 수정 요청이다. OverFury의 KZWeaponSlash17 start/end쌍만 제거하고 원작 notify/효과·입력/피해/시간축은 보존한다. 나머지 추가 Slash는 공유 KZ_Slash asset을 유지하며 기존 Action receipt의 GT finalized pose/cleanup에서 실제 장착 grip/칼끝·무기 reach를 사용해 링 끝점/크기/스윙면을 검증한다. 새로운 runtime class/file/manager/tag0이다. actor-space pose가 빼던 몸통 회전과 bounding-centre 앵커의 차이를 실제 여러 프레임/시점에서 먼저 관측한다. 새 gameplay 튜닝값이 아니라 현재 Fab mesh radius100/diameter200cm·renderer yaw180 및 실제 무기 geometry의 변환/계산이다.

Main source/asset 수정0, fresh 별도 Khazan_PlayerSlashWork_20261013의 source/config/binary 사본·Content hardlink 중 6target montage는 링크를 끊어 안전하게 분리했다. Probe01 saved/export은 passed. 현재 baseline DEV 계측 build와 그 뒤 before RHI 진행 단계다. 정확 재개는 Metadata/PlayerSlashAlignment_20261013/ResumeState.json. 기존 source VFX/피해/오디오/Physics/FPS/Parry·다른 작업은 보존하며 full reauthor/reimport나 외부 editor 제어를 하지 않는다.


## 2026-10-13T12:06:39+09:00 — ARCH-89 SFX coverage·natural tail 작은 확장

현재 직접 요청은 Player와 인간형4종의 모든 현행 action/interaction을 대상으로 한다. 기존 ASC/Ability/Task/피해·Guard/Dodge 승인·Animation ownership를 유지한다. 새로운 runtime class/file/component/manager/tick0이다. 기존 PlayAudio Notify의 optional VolumeMultiplier(default1)와 PreserveFiniteTailOnOwnerDestroyed(defaultfalse)를 추가했다. per-source bank gain 위에 asset-authored TEMP trim을 곱하고, 적용한 finite one-shot만 actor destroy 후 자연 drain한다. loops/명시 stop은 이전 cleanup을 유지한다. EndSound도 같은 정책/볼륨을 소비한다. defaults는 scope 밖 giant 기존 data를 보존한다. 엔진 AudioComponent::OnUnregister는 owner destruction의 one-shot에 bStopWhenOwnerDestroyed=false를 지원하고 BeginDestroy는 loop만 stop한다는 source 근거를 확인했다.

임시 voice0.85/footstep0.90/weapon1은 숫자 출처를 PlaybackPlan01 profile에 모았으며 원작 gain과 구분한다. 아직 실제 믹서 조정/완료 검증이 아니다. 이후 현재5 family data에만 적용하고 peak/tails/combination/cancel/loop/death output으로 조정한다. 이전 미전달37 DataAsset bytes를 복사하지 않고 최신 Main에서 audio field만 수정하여 StrongVictimFront/Root/FPS/physics/VFX·Parry 후속을 보존한다. source3 수정·build 진행/새 asset0이며 exact resume는 Metadata/HumanoidSFX_20261013/ResumeState01.json과 Art 같은 날짜 절이다. 사용자·foreign editor 제어0이다.


## 2026-10-13T13:16:42.496440+09:00 — ARCH-95 Slash 무기 정렬 후속 완료

ARCH-95의 원래 효과 보존·기존 Action receipt 소유권은 유지한다. 이전 actor-space history/mesh bounding-centre·raw span200 정렬은 다음으로 대체한다. 실제 Weapon_L/R에 reference cutting-edge offsets를 강체 연결하며 world tip 차이에서 avatar translation만 빼 body/root yaw를 포함한다. 실제 칼끝과 grip을 절삭선에 투영한 radius로 위치·크기를 정한다. PreviousActorLocation은 이 receipt의 presentation history이며 activation별 초기화/기존 cancel·end cleanup을 따른다. ASC·GAS 판정·타깃·피해·태그/새 State 또는 Manager를 추가하지 않았다.

수치 근거는 요청 Fab/current imported asset이며 원작 gameplay 직접값과 구분한다. KZ_Slash의 SM_VFX_SlashRing_01 raw radius100/diameter200cm, renderer Meshes[0].Rotation.Yaw180deg; emitter RapidIteration Constants.Slash_Additive/Slash_Translucent.InitialMeshOrientation.Rotation=(0,0,.25)turns→90deg 및 InitializeParticle의 initial XY mesh scale2가 근거다. 그래서 effective span=200×2=400cm, correction yaw=360−90−180=90deg이며 실제 effective leading endpoint는 local(+200,0,0)cm다. System.ExposedParameters.User.ScaleLerp=.15000000596, graph lerp(1−u,1+u,CurveScale1) 때문에 종전 실제 particle XYscale는2.3이었다. component User.ScaleLerp0은 modulation의 수학적 identity이며 asset의 initial2는 보존한다. User.Rotation0/CurveRotation0도 component에만 적용한다. raw asset/좌표·GPU/수식은 Metadata/PlayerSlashAlignment_20261013/NiagaraGeometryEvidence.json, 무기 reference_edges_cm은 CombatImpactUpgrade_20261012/WeaponSlashProbe04/WeaponProbe.json이다. 임의 gameplay 튜닝값을 새로 넣은 변경이 아니다.

OverFury addon17 start/end쌍만 제거했고 다른5 montage의 addon33쌍은 유지했다. original1359 effects×37 properties와 모든6 montage notify clocks/GUID를 fresh Main에서 보존 확인했다. runtime3파일의 작은 수정과 기존 DEV 검수 확장/asset6만 이번 소유 범위다. 원래 effect/audio/physics/FPS·HP/ST/Ability 수명은 유지하며 병행 작업의 Source를 보존했다. 실제 Main build·18+Brutal5·GPU70 samples/17 attacks·공중 회전 재생과 native collision16(Spin7/Fury19)은 FinalVerification.json을 따른다. component-only 정렬 검증을 실제 GPU/시각 합격으로 대체하지 않는다.

<!-- PlayerSlashAlignment_20261013_complete -->


## 2026-10-13T14:14:46+09:00 — ARCH-89 current humanoid·Player SFX Main 완료

실행 상태/승인은 기존 ASC/Ability/Task·attack hit group/Guard/Dodge가 소유하고 표현은 기존 PlayAudio Notify를 재사용한다. runtime Source3에 optional VolumeMultiplier(default1), finite owner-tail(defaultfalse)와 EndSound 동일 정책만 확장했다. 해당5family authored Notify만 finite tail을 보존하며 scope 밖 default/giant data는 이전 계약을 유지한다. Body impact는 수신자 Definition, 무기 impact/Guard는 현재 attack window, 회피 성공은 기존 TryAvoidHit once-per-execution이 소유한다. 같은 성공 SFX를 Suc pose에서 또 재생하지 않는다. 새 runtime class/file/component/manager/tick0이다.

기존 DEV Audio Editor에 protected Python array 대신 audio class2-only clear/no-save command, Audio PIE에 sample-plan/actual cue coverage/owner destroy tail, Dodge QA에 실제 authored SuccessSound reflection만 추가했다. build01–04 성공, 현재 Main final saved1682/527/174/8/238cue, full fresh pose/root/curve/FPS/nonaudio notify/GUID 보존 및 실제78 mixer·메인 melee/Guard/Parry17/Dodge11이 passed다. Source/자산/검증 hash·실패/버전은 Metadata/HumanoidSFX_20261013/FinalVerification.json 정본이다. 실제 핵심 root/FPS/physics/VictimFront·Parry/Slash/피격 VFX 제거 변경을 유지했고 기존37prepared bytes를 덮어쓰지 않았다.

유한음은 owner destroy/몬타주 취소 후 자연 drain, loops/명시 source stop만 fade하며 새 shared mutable notify state나 MainAnimInstance member/timer를 만들지 않는다. source 수치/계산과 명시 TEMP .85/.9/1/.08s 및 측정 기반 parry cue.5·미직렬화72callback first-pose adapter를 구분한다. 원작 DSP/sample/frame 전체 동일·Shipping·전 장치 청취는 별도 검증 범위다. 필수 잔여0이며 사용자 editor·foreign process 제어0, 현재 완료를 이전 pending37/locked/prepared 기록보다 우선한다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

ARCH-98 완료 기록: 기존 Tag–Ability 7계층의 실행/확정피해/자원·취소 계약은 유지하고 presentation receipt/SkillObject와 asset reference만 사용했다. 신규 runtime class/file/manager/tag0, 이번 재개 Source추가0이다. 초기selected7runtime+DEV1/198target과 현재Main 검증은 MONSTER_VFX_RUNTIME_20261008.md 및 Metadata/GiantVFX_20261013/FinalVerification.json을 따른다. PlayerSlash ARCH-95 current source는 승인된 후속으로 함께 보존했다. GameCue 전면 마이그레이션이나 전체 원작 구조 확인으로 표현하지 않는다.

## 2026-10-13 — WeakAttack01 사용자 사진 후속 방향·전방 확대 착수

사용자 사진에서 첫 약공격의 두 효과 방향이 어긋나고 하나가 몸에 붙는 문제가 확인됐다. 앞선 SlashAlignment의 축/GPU 끝점 합격만으로 이 장면의 실제 밝은 궤적 방향을 합격 처리한 판단은 부족했으며 이번 시각 수정의 완료 근거로 사용하지 않는다. 기존 기록은 보존한다.

현재 소유 범위는 WeakAttack01의 KZFX_bab7be8e310a56b59c0b9461 원래 PlaneSlash와 KZWeaponSlash 추가 효과의 start/end4 객체, 기존 Action receipt/Notify 설명 및 기존 DEV 검수다. 새 runtime class/file/component/manager/tag0이다. 공유 Niagara/mesh/material은 읽기만 한다. Metadata/WeakAttack01Slash_20261013/Before 및 Baseline.json에 실제 이전 파일을 보존하고 Khazan_WeakSlashWork_20261013에서 별도 editor로 작업한다. RuntimeMainApplied.json의 기존 Source3(실행1/설명1/DEV1) 작은 변경만 Main에 적용했고 asset0, 빌드 진행 중이다. 양수 scale·zero offset의 다른 공격 동작은 그대로다. 음향/패링/거대 VFX 작업과 외부 editor를 제어하지 않는다.

후보는 음수 X scale로 radial UV/head를 반사하며 대응 끝점을 선택하고 기존 RelativeLocation을 avatar-local cm로 소비하는 방식이다. 첫 타격 전방35cm/평면 크기1.15배는 사용자 요청에 따른 TEMP 시각 튜닝이며 원작 직접 수치가 아니다. 이 후보는 아직 실제 시각 검증/최종 asset 반영 완료가 아니다. MeshProbe01의 두 Mesh OBJ/UV와 source PlaneSlash를 표적 조회했다. BeforeComposed01은 실제 baseline 성공이나 사진의 문제를 해소했다는 증거가 아니다. 원래 효과 단독 진단01은 생성 문자열 문법 오류,02는 TextureExporterTGA의 unsupported texture assertion으로 실패했고 제품 asset 저장0이다. 해당 own process만 종료/자연 crash 종료했으며 texture exporter는 진단에서 제거했다.

정확 재개: MainBuild01 결과→새 Main module을 별도 작업본에 가져옴→original-only 재생으로 두 효과 식별→author_weak_attack01_slash_20261013.py 후보를 task-private montage에 적용→세 시점/초기·중기·후기 실제 장면과 signed GPU endpoint·forward offset 확인→최신 Main asset의 audio 등 병행 변경을 보존한 선택 반영→fresh saved/Main 실제 RHI→완료 기록. 개인 에디터를 재사용하거나 과거 montage6/full author/private DLL을 Main에 복사하지 않는다.

## 2026-10-13T15:06:26.891782+09:00 — ARCH-95 Sequencer 기반 공격 Niagara 편집 계약 착수

사용자 직접 구현 지시다. 코드의 수치/방향 보정을 계속 덧붙이는 대신 LevelSequence를 편집 원본으로 사용하고, editor 적용 명령이 Niagara별 Transform 곡선과 Life Cycle 창을 기존 CombatEffect notify에 저장한다. runtime은 기존 Action receipt/GT finalized pose·MontageInstance 검증/정상·취소·사망·EndPlay cleanup을 재사용한다. 사용자가 편집해 적용한 효과는 weapon-sweep 자동 계산을 우회하며 avatar-local cm / Euler degrees / dimensionless scale / montage seconds 계약을 사용한다. 원래 source 효과/오디오/피해/판정/애니메이션 포즈·Root·FPS는 보존한다. 새 runtime class/component/manager/tag는 만들지 않는다. 기존 notify에 optional editor-authored transform channels와 editor-only apply API만 추가할 계획이며, Python editor menu/LevelSequence 엔진 도구로 시각 편집을 제공한다. 불필요한 매게임 LevelSequence player/character animation override는 사용하지 않는다.

WeakAttack02 수동 offset 작업은 이 편집 workflow 요청으로 대체됐다. 이전 Before02은 기존 배치의 실제 관측만 passed이며 위치 수정/후보 적용0이다. 메뉴·Sequence·데이터 apply·fresh native 비교 완료 전에는 구현 완료로 기록하지 않는다. 정확 재개/실패/프로세스는 Metadata/CombatVFXSequencer_20261013/ResumeState.json을 따른다. 새 수치가 필요한 경우 원작/현재 asset geometry/TEMP를 구분한다.

## 2026-10-13 — ARCH-95 WeakAttack01 방향·전방 표현 Main 완료

사용자 사진의 반대 방향 Slash를 수정했다. 월드 좌표로 재생하는 원래 PlaneSlash의 CorrectionBoneName=Weapon_L을 추가 Slash의 공격 손으로 해석한 이전 author 휴리스틱이 원인이다. 실제 첫 약공격의 0.35→0.40초 포즈에서 Weapon_L 쪽 FX tip은 위로 회수되고 Weapon_R 쪽은 우측 위에서 좌측 아래로 이동한다. 이는 현재 실제 포즈 관측이며 원작 실행 코드의 확인으로 표현하지 않는다. 정확한 데이터·근거는 Metadata/WeakAttack01Slash_20261013/CuttingHandEvidence.json과 EquippedGeometryObservation.json이다. addon SourceField의 기존 L 문구는 초기 생성 이력이며 현행 Near/Tip 설정과 이번 override를 우선한다.

AM_DAS_WeakAttackCombo의 첫 KZFX_bab7be8e310a56b59c0b9461 및 KZWeaponSlash start/end4 객체만 변경했다. 추가 효과 Near/Tip을 FX_R_Sword_02/01로 바꾸어 실제 내려베는 Weapon_R을 따른다. 기존 RelativeLocation을 Action finalized-pose receipt에서 avatar-local cm로 더하는 작은 계산만 추가했다. 양수 scale/zero offset의 나머지 공격과 기존 수명/취소 cleanup은 유지한다. 새 runtime 파일/class/component/manager/tag0이며 실행 Source1/Notify 설명1/기존 DEV1/asset1이다. 중간 음수 scale 반전 후보는 시각 실패로 철회했고 관련 product 코드도 제거했다.

전방35cm·평면 크기1.15배는 요청한 전방 확대를 위한 TEMP이며 원작 직접값이 아니다. 에디터에서 첫 notify child의 RelativeLocation/Scale3D로 조정한다. 최신 Main montage 사본에 선택 저작하고 전체 직렬화 diff를 검사한 뒤 SHA CAS/atomic replace로 반영했다. Main SavedMain01은 FinalAuthor01 전체 export와 완전히 동일하다. notify clock/GUID·다른 효과와 오디오/HP/ST/피해/콜라이더/Physics 및 다른 montage5는 보존한다.

MainBuild04 성공, 실제 MainRHI01의18 natural node·Brutal4/실제 승인 HP110→100·두 avatar/조건부 효과·정상 종료/취소 및 실제 GPU70개·17공격은 성공했다. 세 actor-relative 시점·초기/중기/후기 장면289개를 검수했고, MainYaw90RHI01에서 actor를90도 회전시킨 첫 약공격도 성공했다. 각 프로세스의 실제 DLL df9764361d10eec695f0855e34b0dacfb98da06138303a1c8db17cbd7a1f0ed3를 결속했다. GPU 최대0.000031cm는 reference marker+명시된35cm offset에 대한 검수 오차이며 실제 메시 vertex와 완전 일치라는 뜻이 아니다. 현재 Imperial_R tip과 가상 marker의 가장 가까운 vertex 차13.147cm 및 원작 shader/pixel parity 미확인 경계를 보고서에 명시했다.

정본은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json, 재개는 ResumeState.json이다. 필수 잔여0, own editor0, 외부 editor 제어0이다. 실패한 TGA/NullRHI FBX export·문자열 진단·mirror 후보 및 중단한 private 전체 build는 보존한다. 이후 현재 Main Source/first4 객체에서 시작하고 stale private Source/DLL·전체6 montage author·mirror 후보를 전달하지 않는다. 앞선 SlashAlignment의 축/GPU 합격이 사용자 사진의 반대 방향을 해소했다는 판단은 이번 actual hand/시각 검증으로 대체한다.

<!-- WeakAttack01Slash_20261013_complete -->
## 2026-10-13 — ARCH-85 대형 몬스터 비중단 피격 계약 (구현 착수)

사용자 직접 수정 요청에 따라 Apes/Yetuga의 일반 피격만 현재 공격·이동·AI를 유지하는 가산 표현으로 분리한다. 확정 피해/스태미너는 기존 GE/ASC, 스태미너 소진·사망은 기존 Exhaustion/Dead가 계속 소유한다. 기존 Definition의 선택적 additive montage pool과 AKZCharacter의 표현 receipt, 두 ABP의 독립 Slot Group을 사용한다. ASC montage/HitReaction Ability를 경유하면 PreActivate의 Action 취소·태그가 먼저 발생하므로 이 표현에는 직접 UAnimInstance montage를 사용한다. 공유 상태 태그·Ability·Manager를 새로 만들지 않는다. 실행 montage를 읽는 AI는 presentation의 최신 montage 대신 실제 Attack Ability montage를 참조한다. 완료·재진입은 엔진 montage 수명, 소진/사망/UnPossessed/EndPlay는 exact-instance receipt 정리를 사용한다. 아직 적용/build/PIE 완료가 아니다. 근거/원본 수치와 additive author adapter는 Metadata/GiantHitOverlay_20261013에 분리 기록한다.

## 2026-10-13 — 거인 일반 피격 표현 계약 Main 적용 확인

앞 절의 미적용 상태는 이 완료 기록으로 갱신한다. Main Source 6개, 에셋 22개와 동일 Main-object DLL을 반영했고, fresh Main PIE 25/25 조건 및 원본 full-pose 16개 hash 보존을 확인했다. 일반 피격은 표현 전용 Slot으로 Action을 유지하고, ST0/HP0은 기존 Exhaustion/Death 경로가 우선한다. 새 gameplay 상태 소유자·태그·Ability는 없다. 세부 구현·원작 특수 경직/그로기 근거·미구현 부위 내구도 조건은 `GIANT_NONINTERRUPTING_HIT_20261013.md`와 `Metadata/GiantHitOverlay_20261013/FinalVerification.json`을 따른다.

## 2026-10-14 — ARCH-89/92 일반 적중음·브루탈 처치 표시 계약 교정

ARCH-89의 승인된 HP 피해/수신자 재질별 body hit 계약은 유지한다. 이전 author가 Player 일반 Combo 60창에 동일 `SC_efx_pc_dualaxesword_com_impact`를 더해, 저장된 스윙 음향과 body hit 위에 공통의 무거운 충돌음을 매번 겹쳤다. 사용자 청취 교정에 따라 이 특정 중복 음원만 Player Combo의 기존 승인 적중 소비자에서 억제한다. 다른 ImpactSound, Monster 공격, Guard/Parry, 브루탈의 별도 grapple montage 음향은 유지한다. 저장된 Combo DataAsset을 잠근 외부 에디터 때문에 데이터 필드 삭제는 검증된 준비본까지만 완료했고 Main 파일은 변경하지 못했다. 파일 잠금이 풀리면 60창의 해당 필드만 제거한 준비본을 SHA 대조 후 반영하고 임시 exact-cue runtime 억제를 제거한다. 새 음량·시간 수치나 runtime 타입은 없다.

ARCH-92의 완료된 치명 브루탈을 피해자 Damage2 마지막 포즈에서 바로 정지시키던 정책은 사용자 요청으로 대체한다. 짝 실행 두 주체가 완료되면 기존 Exhaustion Ability가 자기 몽타주/제약을 정리한 뒤 기존 Monster `FinishDeathPresentation()`의 저장된 DeathPresentationMontage를 시작한다. HP/Dead, 짝 수명과 비치명 회복, 중단 사망 경로는 기존 소유자에 둔다. 6종 정면/후면12의 실제 사망 몽타주 재생·terminal pose/캡처, 별도 일반 사망 정상/중단12가 새 모듈에서 통과했다. 정확한 실행·잠금·미반영 범위는 `Metadata/PlayerImpactSFX_20261013/FinalVerification.json`을 따른다.


## 2026-10-14 — ARCH-99 대형 몬스터·패링 카메라 표현 계약

기존 Tag–Ability 7계층의 피해/입력/상태는 변경하지 않았다. Yetuga·Apes의 원작 xxAnimNotifyState_CameraMod 데이터는 기존 UKZAnimNotifyState_MonsterVisual의 카메라 전용 분기에 보관하고, 실제 소비자는 로컬 PlayerCameraManager의 UKZCombatCameraModifier다. 86개 독립 이벤트의 원본 축/주파수/시간·거리·fade를 기존 단일 CameraShake BP로 표현할 수 없어 UCameraModifier 하위 클래스 하나만 추가했다. 새 gameplay state, ASC tag, manager, delegate는 없다. 전투·이동·피해 Ability는 카메라 피드백을 소유하지 않는다.

작성은 애니메이션 notify의 게임 스레드, 소비는 로컬 카메라 갱신의 게임 스레드다. mesh와 notify instance ID로 이벤트를 구분하고 weak mesh 수명, NotifyEnd 또는 명시적 active-end에 따른 quadratic release로 정리한다. 원본 source scale 0은 재생하지 않는다. 패링은 Guard 승인 분기에서 같은 modifier에 유한 이벤트를 넣고, 기존 별도 BP CameraShake 호출은 제거했다. 로컬 플레이어별로만 적용하며 AI/원격 플레이어의 gameplay 상태를 복제하지 않는다. 파생 출력 clamp와 랜덤 축은 원작값이 아닌 조정 가능한 TEMP 표시값이다.

원본88/현행 바인딩86의 출처·계산·미확인 조건은 MONSTER_VFX_RUNTIME_20261008.md 최신 절과 Metadata/GiantCamera_20261014/OriginalCameraEvents.json을 따른다. Build07은 최신 Main target up to date/Succeeded, 현재 DLL SHA와 48 asset/86 notify fresh readback, 4 monster 실제 PIE 및 parry17 실제 PIE 성공은 Metadata/GiantCamera_20261014/FinalVerification.json에 결속했다. 원작 전용 xxCameraMod 실행 코드와 source package 2개의 현행 AnimSequence가 없어 원작 프레임 완전 일치는 주장하지 않는다.


## 2026-10-14 — ARCH-95 플레이어 KZ_Slash 바깥 배치 계약 보완

기존 추가 Slash의 실행 소유자와 정상/취소 cleanup은 Action Ability effect receipt 그대로다. finalized pose에서 선택한 실제 무기의 스윙 접선(X)·절삭면(Y)으로 회전을 만들고 매 프레임 실제 tip에서 캐릭터 바깥쪽으로 `WeaponSlashOutwardOffsetCm`를 적용한다. 이 값은 Notify별 TEMP 시각 데이터이며 기본 0이다. 첫 프레임 추정 선택이 틀리던 공격은 저장 Notify의 좌·우 무기 이름으로 확정했다. 기존 원래 VFX·WeakAttack02의 Sequencer 소유권, ASC 상태·피해 경로는 유지하며 새 실행 상태나 manager는 추가하지 않는다. Main 저장·빌드·실제 PIE 근거는 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`이다.

## 2026-10-15 — ARCH-88/95 HeinMach 색감·피격 VFX 후속 착수

사용자 직접 수정 요청으로 이전 Player ImpactEffect=None 정책을 대체하고, 현재 브루탈에서 재생하는 PP_Dmg_Blood_Trail_Sub를 플레이어/6종 몬스터의 기존 승인 피격 표현에 연결한다. 원래 PS는 복제·증량하지 않는다. 공유 PlayHitReaction의 기존 spawn 위치만 현재 캡슐 표면으로 보완하며 ASC/피해/가드·회피 승인/Ability 수명은 변경하지 않는다. 새 runtime 클래스·파일·manager·상태는 없다. HeinMach의 장면 색은 조명과 노출 설정에서 조정하고 VFX용 역노출 보정 누락·맵별 LocalExposure 차이를 제거한다. 혈흔 빨강·거리/노출 조정은 원작 확인값이 아닌 명시된 TEMP 시각 후보다. 현재 BaselineAudit02의321 system/206 material/97 root와 저장 원작 사진을 기준으로 격리본을 준비했고 아직 candidate의 저장·시각 검증·Main 전달은 완료되지 않았다. 근거/재개는 Metadata/HeinMachColourVFX_20261015이다.
## 2026-10-15 — ARCH-99/85/92/94 후속: 선형 카메라 힘과 거인 전투 연결

사용자의 직접 구현 요청으로 기존 CameraModifier의 사인파/이차 envelope를 방향·변위 힘의 선형 상승과 선형 원점 복원으로 변경한다. 반복 힘은 독립 이벤트/반대 방향의 연속 pulse로 표현하며 Notify End/취소는 그 시점 변위를 보존해 복원한다. 원작 camera notify 원시 값과 identity는 보존하고, 최소 상승 0.08s/최소 복원 0.16s/최대 반복 4Hz는 사용자가 자연스러운 값을 선정하도록 허용한 어시스턴트 TEMP 설정이다. 새 runtime class/manager/shared gameplay state는 추가하지 않는다.

Guard의 승인된 패링 경로만 KZ_Parring_Distort 및 기존 Brutal CombatEffect 데이터 사본을 소비한다. 예전 패링 PSC/바닥용 Niagara/화면 PP 생성 경로는 제거한다. 두 캐릭터 사이 흉부 높이에 contact를 배치하고 원본 camera-facing renderer를 유지한다. particle 수명은 원본 window와 엔진 auto-destroy/drain이며 Guard 종료 이후에도 해당 component의 finite timer가 소유한다.

Yetuga의 원거리 Armageddon은 기존 SourceGate/SourceSkill 실행을 활용하고 에디터 AISettings의 optional skill/range/chance/cooldown으로 사용자 정책을 적용한다. chance는 실행 진입에서 한 번 평가하며 true/false gate에서 각각 RNG를 돌리지 않는다. 기존 상태 트리 노드/원작 status 데이터는 보존한다. 거인 추격의 실패한 nav query는 engine abstract direct path로 계속 시도하며 CMC collision은 유지한다. capture-bearing 이동만 기존 TargetMax보다 멀리 있는 선택 target까지 확장하고 miss/recovery/다른 공격은 보존한다.

약점 파괴 root track은 read-only audit와 Rider의 실제 PartGroggy 실행에서 검증한다. 이미 올바른 true root/track order/추출을 재베이크하지 않는다. Exhaustion은 기존 montage Start→Loop→Loop를 runtime link해 locomotion 포즈로 빠지는 재시작 구간을 없애고 원래 timer/Brutal 소유권을 유지한다. source zero-blend section은 기존 ABP inertializer로 최소 0.12s TEMP 전이를 적용한다. paired victim→death는 기존 Monster death owner에 0.24s TEMP 최소 inertialization만 적용한다. 적용/빌드/PIE/화면 검수 범위는 완료 기록에서 분리한다. 재개 및 근거 디렉터리는 Metadata/CombatFeel_20261015이다.


## 2026-10-15 — ARCH-99/85/92/94 CombatFeel 실행 계약 확정

앞선 같은 날짜 계획의 'chance는 실행 진입' 및 'abstract direct path 추격' 설명은 현재 구현으로 대체한다. Armageddon chance는 source true/inverted-false gate가 같은 selection frame에 공유하는 한 RNG 결과이고 task Enter 재평가는 없다. off-nav abstract path의 실제 입력0이 관측돼 선택된 기존 이동 task의 DirectMoveGoal을 AIController가 기존 intent→Pawn/CMC 입력으로 소비한다. 정상 nav 복귀/Exit/금지/Unpossess cleanup은 StopRequestedMove 한 경로로 정리한다. 목표는 navigation resource이며 ASC gameplay 상태의 사본이 아니다. 공격/피해/자원/죽음 수명과 worker 경계는 유지한다.

Runtime 신설0, 기존 camera/Guard/Pattern/Exhaustion/AI/Monster 소유자와 기존 data field만 보완했다. .12s combo floor는 source0뿐 아니라 더 짧은 source blend에도 적용하며 긴 blend는 보존한다. 실제 적용, 빌드, 각 DLL별 PIE/화면 검수 및 미확인 경계는 `Metadata/CombatFeel_20261015/FinalVerification.json`와 도메인 현행 문서에 기록했다. 앞선 실패나 계획 기록은 삭제하지 않는다.



## 2026-10-15 — ARCH-88/95 HeinMach 피격 VFX 후속 완료

앞선 착수 기록의 Main 미반영 상태를 완료로 대체한다. 기존 승인 피격 표현 소유자 AKZCharacter::PlayHitReaction과 CharacterDefinition.HitReactions.ImpactEffect만 재사용했다. 현재 Brutal 혈액 PS를 Player/몬스터6종에 연결하고 발생 위치만 기존 캡슐 표면으로 계산한다. 승인 피해/가드·회피/ASC 상태/Ability·몽타주 수명 계약은 동일하며 새 gameplay class·상태·태그·manager가 없다. 추가한 console capture는 기존 editor/dev automation QA 파일 안에만 있다.

Main105 package SHA/readback, 표준 build와 실제 피격·가드/몬스터6종·공격 collision3 suite 및 native VFX 비교 완료는 Metadata/HeinMachColourVFX_20261015/FinalVerification.json을 따른다. source task-before diff와 모듈별 검사 범위를 보존했다. 조명/혈흔 TEMP 수치 및 원작 shader/pixel 미확인 한계는 Art 정본 HEINMACH_COLOUR_VFX_20261015.md의 책임이다. 기존 v2 7계층의 실행·상태 소유권은 바꾸지 않는다.

<!-- HeinMachColourVFX_20261015_complete -->

## 2026-10-15 — ARCH-05/09/11/15: HeinMach 자동 진입 포탈

GateCube → Yetuga 전장 이동의 실제 독립 수명은 새 배치 Actor `AKZBossPortal` 한 개가 소유한다. 기존 포탈 소유자가 없어 GameMode/Controller에 맵 검색·좌표·timer를 더하는 대안보다 책임이 작다. runtime h/cpp2, Level의 기존 Niagara/Engine TargetPoint와 overlap·TeleportTo·PlayerCameraManager만 재사용하며 새 Manager/Subsystem/Interaction 탐색·인터페이스/Ability/태그 사본은 추가하지 않는다. 자동 통과이며 별도 입력·보상·공유 상호작용 실행을 요구하지 않는 이 범위에 한정한다.

원인별 Controller ignore count·ASC action block count·무적 tag contribution은 진입 한 건에 한 번 취득하고 정상/실패/소멸/빙의 변경 시 각 한 번 회수한다. 캐릭터 실행은 기존 ASC CancelAllAbilities가 자기 cleanup으로 종료하고, 포탈은 LockOn/Player raw intent 해제 API를 사용한다. 목적지와 크기·VFX·fade 시간은 Level Details에서 편집한다. Main AnimInstance/Locomotion/MonsterPatternAbility에는 포탈 상태나 좌표를 넣지 않는다. 이 절은 구현 경계의 채택이며 실제 저장·빌드·PIE 범위는 `HEINMACH_YETUGA_PORTAL_20261015.md`의 최신 결과를 따른다.


## 2026-10-15 — ARCH-83/95 SpinningAttack 표현 교체 착수

사용자가 SpinningAttack의 KZ_Slash를 다른 효과로 교체하고 OverFury/ChargeAttack 효과를 차용하도록 직접 요청했다. 기존 montage CombatEffect의 batch/실행 receipt/정상·취소 cleanup을 재사용하고 Spinning에 한해 이전 추가 Niagara 연결을 기존 Cascade 효과로 바꾸는 Art 데이터 수정부터 진행한다. donor 공유 particle와 다른 공격은 보존하며 gameplay damage/section/Ability 수명·입력·GAS 상태를 변경하지 않는다. 현재 새 runtime class/component/manager/file 계획0이다. 실제 효과 방위·발생 위치와 조합은 원작 타격 시각을 보존한 native 재생에서 검수한다. 추가 수치/다른 공격에서 가져온 효과의 배치는 원작 Spinning 직접값이 아닌 TEMP 표현임을 Art 정본에 기록한다. 현재 Main 미반영이며 근거/재개는 Metadata/HeinMachLookSpin_20261015다.

<!-- HeinMachLookSpin_20261015_intake -->


## 2026-10-15 — ARCH-05/09/11/15 포탈 실행 검증 완료

앞선 자동 진입 portal 계약을 Main runtime2/DEV1/배치2 actor로 구현했다. 독립 수명은 기존 engine Actor가 소유하고 ASC action block/tag count 및 Controller ignore count의 자기 기여만 회수한다. 실제 Player intent/CMC walking, black-before-teleport, 전장 floor/yaw와 중복/소멸 cleanup이 RHI06에서 통과했다. 새 범용 Interaction manager/Ability/태그 사본은 없다. 최신 좌표/전용 Niagara·TEMP·정확 검증은 HEINMACH_YETUGA_PORTAL_20261015.md 및 FinalVerification.json을 따른다. 이는 포탈 한 수직 절편이며 전체 Interaction/Encounter 마이그레이션 완료를 뜻하지 않는다.

<!-- HeinMachPortal_20261015_complete -->

## 2026-10-15 — ARCH-89/99 컨트롤러 진동 표현 계약 (사용자 직접 요청, 검증 생략)

원작 진동 metadata는 미확인이다. 사용자 지시의 약공격=약하고 짧게/강공격·Spinning·OverFury·패링=강하고 짧게, Yetuga/Apes/Elite의 행동 강도 구분을 기존 표현 경로에 구현한다. 기존 AKZPlayerController가 UE PlayDynamicForceFeedback의 로컬 장치 출력과 조정값을 소유한다. 새 runtime class/file/component/manager/tag/에셋은 만들지 않는다. Source/ASC/Ability의 피해·입력·태그·StateTree 판단은 변경하지 않는다.

실제 작성자는 기존 ComboAction 공격창/몬스터 노드 시작, Guard 승인 패링, MonsterVisual 원본 camera notify와 기존 monster footstep audio notify다. MonsterPatternAbility는 기존 ComboAction 상속을 통해 같은 경로를 사용한다. 공격창의 중복 억제는 해당 Combo 실행의 hit-group 집합만 사용하며 기존 ResetAttackCollision에서 함께 초기화한다. GT에서 로컬 PlayerController만 소비하고 몬스터의 출력은 현재 Pawn 거리로 감쇠한다. 진동은 유한 양수 duration의 엔진 dynamic effect이며 엔진이 종료/Controller 수명을 관리한다. Ability 종료로 다른 진동을 일괄 정지시키거나 공유 Notify에 runtime 상태를 저장하지 않는다.

어시스턴트 TEMP 설정은 PlayerController의 KZ|Feedback|Temporary에 모은다. intensity(무차원0~1)/duration(s): Weak(.22,.06), Strong·Spinning·OverFury·Parry(.90,.10), Monster약(.14,.045), Monster강(.65,.12). 몬스터 full-strength400cm/max3000cm 사이는 선형 감쇠한다. 선택 이유는 짧은 타격 구분과 먼 적의 지속 진동 방지이며 원작 직접값이나 실기 검증값이 아니다. 이후 장치별 체감에 따라 이 설정만 조정한다.

사용자의 “검증은 거치지 마”를 따른다. 이번 범위에서는 빌드/PIE/테스트/장치 출력 검증을 실행하지 않는다. 소스 반영과 현재 실행 중인 바이너리 반영을 구분하며 후속 결과도 임의 성공으로 기록하지 않는다.


## 2026-10-15 — ARCH-83/95 Spinning 표현 교체 완료

기존 montage data-only CombatEffect와 Action 실행/수명·적중·취소 계약으로 해결했으며 새 gameplay owner/State/태그/manager/runtime 파일을 추가하지 않았다. 원래176 효과·clock/GUID·피해/입력/오디오와 공유 donor는 유지한다. Main3 presentation asset 선택 전달, 실제 HeinMach Spinning/cleanup·충돌과 Main DevMap 두 회귀 suite 검사가 완료됐다. HeinMach broad suite의 별도 rear-Brutal fixture 실패는 통과로 확대하지 않는다. 이 요청의 Source/Config/DLL/build 변경0이다. 계약 변경 없이 Art의 TEMP donor 조합만 달라졌고 원작의 내부 구조/수치로 표현하지 않는다. Metadata/HeinMachLookSpin_20261015/FinalVerification.json과 Art HEINMACH_BLUE_SPINNING_20261015.md가 최종 근거다.

<!-- HeinMachLookSpin_20261015_complete -->

## 2026-10-15 — ARCH-05/89 Yetuga 전장 BGM 단방향 시작 계약

사용자의 직접 구현 요청과 후속 정정에 따라 기존 AKZBossPortal의 성공한 전장 이동만 원작 Yetuga BGM의 시작 신호로 사용한다. 새 runtime 파일/class/manager/Ability/tag/tick/delegate를 추가하지 않는다. 기존 포탈에 편집 가능한 soft sound와 재생 component receipt만 보관하며 engine SpawnSound2D에 World를 전달한다. 캐릭터·보스 수명이나 거리·HP·Dead 태그를 BGM 종료 조건으로 만들지 않는다. 플레이어 사망/Yetuga 처치/전장 이탈/포탈 FinishTravel 후에도 원본 반복 구간을 계속 재생한다. 같은 포탈의 재진입은 살아 있는 재생 component를 확인해 중복/처음부터 재시작을 억제한다. 월드/PIE의 종료는 engine audio 정리 대상이다. 이 절은 앞선 진행 안내의 사망·처치·이탈 종료 계획을 명시적으로 철회한다.

포탈 이동·입력/ASC counted lock·암전 cleanup은 그대로다. 원작 음악의 내용·구간·gain 출처는 Art의 YETUGA_BGM_SOURCE_20261015.md로 분리 기록한다. 음악 재현을 원작 Wwise 전역 DSP/RTPC나 native scheduler의 sample parity로 확대하지 않는다. 실제 적용/빌드/재생 범위는 아래 완료 기록과 Metadata/YetugaBGM_20261015를 따른다.

### 2026-10-15 — 동일 계약 Main 적용 결과

runtime2 소스와 원작 음악4asset 저장 및 Main stock DLL 빌드가 완료됐다. 새 runtime class/file·map 저장0이며 실제 PIE/청취 검증은 실행하지 않았다. module SHA8014a3c141b2951dcac0a8c5b38402639dbaa6a565d71b915df7f5cfc776c849, 기존 map SHA7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728 유지다. 정확한 범위/재개는 Metadata/YetugaBGM_20261015/Implementation.json과 Engineering 포탈 최신 절을 따른다. 앞선 계약 이외의 게임 상태 소유/AI/능력 구조 변경0이다.

## 2026-10-15 — ARCH-09/14/89/99 진동 2배·사망/Yetuga 잡기 LockOn 계약

사용자 직접 수정 및 HeinMach 재패키징 요청이다. 진동은 기존 APlayerController.ForceFeedbackScale을 2로 설정한다(사용자 지정 무차원 배율). UE 5.8 PlayerController.cpp의 최종 ForceFeedbackScale 곱셈/0..1 clamp를 재사용하므로 기존 duration·거리 감쇠는 유지하고 최대 장치 출력은1이다. 원작 진동 metadata 확인값이 아니다.

LockOnComponent가 선택 대상 ASC의 기존 HP 변경 delegate를 구독해 HP<=0에서 동기 해제하고 자기 delegate/이동 constraint만 회수한다. 시작/검색/유지 시 살아 있는 ASC 대상만 허용한다. HP·Dead의 작성자는 변경하지 않는다. Yetuga의 성공한 CaptureEffect/attachment 수명은 기존 MonsterPatternAbility가 계속 소유하며, 잡힌 local Player의 잠금을 해제한다. 잡기 종료/취소 cleanup 후 같은 PlayerController/Pawn이며 양쪽 생존·유효할 때 잡았던 Yetuga를 직접 재잠금한다. 잡기 실패에는 변경이 없고, 잡힌 동안 monster attachment가 있는 Player의 신규 잠금은 차단한다. 기존 CharacterDefinitionAssetName의 읽기 getter로 Yetuga를 식별하며 이름 부분검색/새 상태 태그/manager는 추가하지 않는다.

새 runtime 파일/class0. 기존 Controller cpp, Character header, LockOn h/cpp, MonsterPattern h/cpp의 작은 변경과 기존 DEV test 보완으로 진행한다. 현재는 착수 계약이며 적용/build/PIE/package 완료가 아니다. 근거·백업: Metadata/LockOnRumble_20261015. 기존 Epic Shipping/HeinMach 단일 map 설정을 재사용해 변경 후 새 build/cook를 수행한다.


## 2026-10-15 — ARCH-09/14/89/99 LockOn/진동 계약 실제 완료

앞선 착수 계약을 runtime5/Config1/DEV2로 적용했다. 진동은 config property의 Engine 기본1을 프로젝트 DefaultGame ForceFeedbackScale2로 override하며 PlayerController.cpp는 원래 SHA를 보존한다. 기존 Engine clamp와 finite pulse 수명을 재사용한다. LockOn은 직접 HP delegate/자기 constraint를, PatternAbility는 성공한 capture의 controller receipt와 기존 cleanup을 소유한다. CharacterDefinitionAssetName getter는 기존 ID의 읽기 전용 노출이다. 새 공개 gameplay 상태/manager/tag/runtime class는 없다.

Editor build·두 native RHI suite·HeinMach 단일 Epic Shipping build/cook·최종 container와 config·90초 offscreen 시작을 실제 완료했다. 초기 DEV 사망 assertion 보정/각 DLL과 실물 패드·Shipping 전체 combat 미확인 범위는 Metadata/LockOnRumble_20261015/FinalVerification.json을 따른다. 앞선 계획/진행 중 기록은 이 범위에서 완료로 대체한다.

<!-- LockOnRumble_20261015_complete -->
