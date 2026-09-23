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
