# Khazan 캐릭터 아키텍처 검토 — HeinMach / StormPass

## 2026-09-08 검토 범위와 결론

사용자 목표는 The First Berserker: Khazan의 HeinMach와 StormPass 두 레벨의 플레이 경험을 충실히 재현하는 것이다. 로코모션 단독 완성이 아니라 플레이어의 대시·공격·스킬·피격·사망과 여러 몬스터·보스, 전투/레벨 진행을 함께 수용할 기반을 검토한다. 맵/리소스의 복원 상태를 이번에 조사하거나 검증한 것은 아니다.

이번 요청은 검토다. C++/ABP/에셋/Config를 변경하지 않았다. 아래 새 타입·에셋 이름은 책임을 설명하기 위한 **설계 후보**이며 현행 구현이 아니다. GAS와 Linked Anim Layers 도입도 아직 구현/사용자 승인 완료가 아니다. 원작 카잔이 내부적으로 GAS/Lyra 구조를 사용한다는 주장도 아니다.

결론: 현재의 공통 Character, CMC, 입력 의도, GT snapshot/AnyThread 경계는 유지할 수 있다. 그러나 Player에 공통 이동 적용이 남아 있고, 공통 AnimInstance에 소비되지 않는 관측/취소된 기능과 로코모션 특화 이력이 누적돼 있다. 이 상태에서 액션별 bool/분기를 계속 추가하는 확장은 채택하지 않는다.

**앞선 KhazanLocomotionMath 생성 및 MovementInputAngle/유효성 멤버를 AnimInstance에 먼저 추가하라는 제안은 철회한다.** 현재 두 Math 파일과 새 관측 멤버는 Source에 없다. Pivot 계산은 이후 이동 제어의 실제 소유 함수 안에서 필요한 지역 계산으로 시작한다. 공통 helper는 실제 독립 소비처와 동일한 계산 계약이 확인될 때만 추출한다.

검사 리포트: [Khazan_Character_Architecture_Review_20260908.json](../../Saved/ImportReports/Khazan_Character_Architecture_Review_20260908.json).
로코모션 현행 계약: [LOCOMOTION_CURRENT_IMPLEMENTATION.md](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md).

## 1. 직접 확인한 근거

### 사용처 검사

- 현재 native Source/Config, Player/Character/Monster/LocomotionComponent/AnimInstance/Controller/공통 타입과 모듈 의존성을 확인했다.
- Rider의 KhazanAnimInstance BP 상속 인덱스는 ABP_Player 하나를 반환했다.
- Editor PID 32936에서 AnimGraph 전체 중첩 export 337971문자와 EventGraph 4661문자를 엔진 내부에서 잘림 없이 검사했다. 일반 export 도구 반환은 약 10000문자에서 잘렸으므로 그 부분 출력의 검색 결과로 미사용을 단정하지 않았다.
- 현재 ABP의 변수 참조는 16개이고 고유 멤버는 9개다: LocomotionGait, StopGait, StopEntryFoot, bIsGrounded, bIsFalling, bShouldBeIdle, bShouldEnterStop, bShouldWalkRun, bShouldSprint.
- AnimGraphNode_Base 계열은 StateMachine 2, SequencePlayer 10, BlendListByEnum 5, TransitionResult 14 등을 포함한다. Linked Anim 노드/Property Access 참조는 현 export에서 확인되지 않았다.
- 위 범위에서 MovementDirectionAngle, bShouldPlayStart, StopEntrySpeed, bIsStopping의 ABP 소비는 없었다. GroundSpeed 등 BP 직접 소비가 없는 값 중에도 native 판단에 필요한 값이 있으므로 일괄 제거하지 않는다.
- 다른 모든 Content 에셋에서 외부 AnimInstance 프로퍼티를 읽는지 전수 조사한 것은 아니다. 실제 reflected 멤버 삭제/이동 전에는 IDE/Find in Blueprints 참조와 직렬화/Redirect를 추가 검증한다.

### 우선순위별 구조 문제

| 우선순위 | 근거 | 확장 시 문제 | 제안 |
| --- | --- | --- | --- |
| 높음 | Player RefreshLocomotionGait가 CMC MaxWalkSpeed 적용을 소유 | AI가 같은 이동 정책을 쓰려면 복제/우회 필요 | 장치 해석은 Player, 요청 해결/물리 설정 적용은 공통 Locomotion 계층 |
| 높음 | Component의 SetMaxAllowedGait/SetRotationMode는 저장만 함 | 제한과 실제 CMC 설정이 다른 시점에 반영될 수 있음 | 요청/제약 변화에 공통 정책 재평가와 적용 계약 |
| 높음 | SetMovementAllowed는 단일 bool과 입력 Clear | 공격 종료와 피격/사망 등 여러 제약의 수명이 겹치면 잘못 해제 가능 | 원인별 제약을 합성하고 해제 시 자신이 소유한 원인만 제거 |
| 높음 | 액션 수명/취소/자원/피격 처리 계층 미구현 | 향후 AnimInstance 또는 Player의 거대 상태 분기로 성장 가능 | GAS 중심의 공통 액션 계층 권장 |
| 중간 | 공통 AnimInstance에 전용 loop/Stop 선택과 발 이력 | 다른 골격/이동 세트까지 같은 데이터와 분기 상속 | 공통 관측과 로코모션 표현 상태를 분리하고 Linked Layer 경계 설정 |
| 중간 | 소비 없는 관측값/Start 잔재 | 추가 기능의 근거 없는 선행 필드와 Reset 부담 | 실제 소비 연결을 기준으로 축소 |
| 중간 | bShouldEnterStop은 한 animation update 펄스 | 새 액션/비활성 레이어/업데이트 생략에서 요청 소비 계약 주의 | gameplay 지속 상태/요청과 animation 진입 관측을 구분 |
| 낮음 | 빈 template override/불필요 include | 가독성 부담 | 의미 없는 override 정리는 가능하나 엔진 ACharacter Tick을 임의 비활성화하지 않음 |

이는 구조 검토다. 아직 추가되지 않은 공격·피격 버그가 현재 재현됐다고 보고하지 않는다. 실제 성능 병목은 이번에 측정하지 않았다.

## 2. MovementDirectionAngle의 용도와 처리

현재 값은 Actor 정면에 대한 실제 평면 Velocity 방향이다. 락온/스트레이프에서 캐릭터가 적을 보면서 옆/뒤로 움직일 때 방향별 Blend Space나 포즈 선택의 입력이 될 수 있다. 실제 그 기능을 구현하고 소비시킬 때 필요한 값이다.

반면 SprintPivot 진입은 실제 진행 방향과 새로운 이동 의도의 차이다. 두 각도는 기준이 다르다. 이름이 모두 방향각이라고 같은 변수로 합치지 않는다. 현재 값은 이동하지 않을 때 0으로 초기화되므로 제자리 Turn의 목표 회전각으로도 그대로 사용할 수 없다.

현재 전방 loop/Stop은 이 각도를 쓰지 않으므로 제거 후보로 분류한다. 미래 스트레이프 때문에 매 frame 계산/노출을 계속 유지하는 것을 필수로 취급하지 않는다.

| 항목 | 검토 처분 |
| --- | --- |
| MovementDirectionAngle | 현 native/ABP 소비 없음. 참조 정리 후 제거 후보 |
| VelocityLocal 및 ActorYawRotation 계산 | 현재 위 각도만 위한 의존 경로. 각도 제거 시 함께 검토 |
| bShouldPlayStart | 모든 Start 제외 정책, 항상 false, 현재 ABP 소비 없음. 제거 후보 |
| StopEntrySpeed / PreviousGroundSpeed | 현재 클립/물리 제어 소비 없음. 거리 매칭 등을 실제 채택할 때만 다시 설계 |
| bIsStopping | 계산/Reset 외 현 소비 없음. ABP Stop 활성값으로 오인하지 말고 제거 검토 |
| AccelerationWorld와 snapshot MaxAcceleration/MaxBrakingDeceleration | 현재 파생/ABP 소비 없음. 필요한 기능 없이 선행 수집하지 않음 |
| snapshot MoveInputWorld/TargetGait/MaxAllowedGait/RotationMode | 현 Anim 소비 체인의 필요성 재검토. Gameplay Intent의 대응 필드까지 무조건 삭제한다는 뜻은 아님 |
| GroundSpeed/InputAmount/bIsMoving/bHasMovementInput/ResolvedGait | native 선택 로직이 소비하므로 BP 직접 참조가 없다고 제거하지 않음 |
| LocomotionGait/StopGait/StopEntryFoot | 실제 선택 데이터. 의미·진입 고정 수명 보존 후 전용 표현 영역으로 이동 검토 |

Config/DefaultEngine.ini에는 MovementAngle → MovementDirectionAngle PropertyRedirect가 있다. 삭제/이동 때 기존 BP 직렬화/Redirect 영향과 에디터 재빌드를 함께 확인한다. 이번에는 삭제하지 않았다.

## 3. 권장 책임 구조

다음은 현 프로젝트 요구에 대한 설계 제안이다. 엔진이 강제하는 유일한 표준은 아니다.

```text
Player 입력 해석                   AIController + 의사결정
       └──────────── 공통 요청 ─────────────┘
                           ↓
                  AKhazanCharacter
                   ├─ LocomotionComponent
                   │    의도 + 제약 → 이동/회전 정책 → CMC
                   ├─ AbilitySystemComponent + Abilities
                   │    액션 실행/취소, 자원, 효과
                   └─ Combat / Equipment (필요 기능의 소유 영역)
                        타격 판정 / 장착·세트 교체
                           ↓ 관측값
                Main AnimInstance snapshot
                           ↓
        골격/운동 방식 계열의 공통 Main ABP
                   ├─ 공통 상태 흐름
                   ├─ Linked Layers: 상태별 pose 선택
                   ├─ 액션 Montage/Slot 합성
                   └─ 필요한 IK / additive
```

### Player와 AI: 요청 생성자

Player는 스틱 deadzone, 카메라 기준 입력 변환, L3 토글 같은 사람 입력 해석을 맡는다. 몬스터에게 L3/스틱 임계값이 필요하지 않다.

AI는 추적/거리/전투 패턴을 판단해 gait·이동 목표·액션을 요청한다. 기존 AIController/PathFollowing/CMC 경로를 존중해야 하며 AI MoveTo가 Player::HandleInputMove를 자동 호출한다고 가정하지 않는다. AI 경로 이동의 의도/중단을 공통 이동 계층에 연결하는 어댑터는 별도 구현·검증 항목이다. Velocity만으로 AI의 '원하는 이동'을 역추정하지 않는다.

Behavior Tree 또는 StateTree는 의사결정 계층으로 사용할 수 있다. 이번 제안에서는 첫 일반 적은 Behavior Tree + Blackboard로 시작하는 구성을 권장하되, 두 시스템을 동시에 도입하는 것을 요구하지 않는다. 보스 패턴은 데이터/태스크/필요한 전용 행동으로 확장한다. [Epic Behavior Tree](https://dev.epicgames.com/documentation/en-us/unreal-engine/behavior-tree-in-unreal-engine---overview)

### LocomotionComponent: 이동 정책의 소유자

현재 컴포넌트를 삭제하고 새 저장 컴포넌트를 만드는 것이 아니라 책임을 완성한다.

- 공통 이동 설정, 요청 gait, 허용 제약의 해결과 CMC 설정 적용.
- 자유 이동/락온/Pivot/액션 구동 중 어느 쪽이 이동·회전을 제어하는지 결정.
- 원래 입력 의도와 CMC에 실제 적용할 명령 구분.
- Pivot의 진입 방향/목표 방향 등 여러 update에 걸쳐 필요한 gameplay 상태 보존.
- 제약 추가/해제 시 적용을 갱신. Player 입력 이벤트가 다시 오기를 기다리지 않는 계약.
- 실제 속도 적분/충돌은 CMC에 맡김. 일반 루프의 애니메이션 클립과 발 marker는 여기로 옮기지 않음.

공격 A가 이동을 막고 피격 B도 막고 있다면 A 종료 시 A의 제한만 제거해야 한다. single bool을 true로 덮는 방식은 이 수명을 표현하지 못한다. GAS의 효과/태그 수명 또는 소유 핸들이 있는 요청을 사용해 원인을 합성한다. 단순 GameplayTagContainer 하나를 여러 곳에서 Add/Remove하는 것도 자동으로 소유권/참조 계수를 제공하지 않는다.

각 액션이 MaxWalkSpeed/ActorRotation/입력 허용을 독립적으로 덮지 않게 한다. Root Motion/Root Motion Source를 쓸 액션도 CMC 및 이동 권한 전환과 협력해야 하며, Pivot 회전과 기본 CMC 자동 회전이 동시에 경쟁하지 않게 한다. CMC 서브클래스는 기본 확장 지점으로 해결되지 않는 물리/회전 통합이 실제 필요할 때만 도입한다.

### 액션: GAS 권장, 거대 Action enum 또는 제2의 거대 Component는 비권장

이 프로젝트의 공격·대시·스킬·자원·피격·상태 효과·취소 조합에는 GAS 도입을 권장한다. 비용과 학습 부담은 있지만 공통 실행/취소/효과 수명을 직접 반복 구현하는 부담을 줄일 수 있다. GAS가 근접 콤보·판정·보스 AI·Root Motion 조정을 자동 완성해 주는 것은 아니다. [Epic GAS 개요](https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-the-unreal-engine-gameplay-ability-system)

- ASC: 캐릭터의 능력 실행과 효과/태그/속성 관리.
- Ability: 공격/대시/스킬/피격 반응의 실제 수명.
- AttributeSet: 체력·스태미나 등 계산/이벤트가 필요한 자원.
- GameplayEffect: 피해/소모/버프·디버프 등 변화.
- GameplayCue: VFX/SFX 같은 표현, 피해 판정의 유일한 실행 경로로 사용하지 않음.
- Combat 영역: 필요한 공격 구간의 trace/중복 타격 방지/팀·대상 필터 및 hit 결과 생성. 최종 수치 적용은 효과/피해 규칙과 연결.
- Equipment 영역: 장착 중인 세트/능력/애니메이션 레이어 변경. 무기명별 if를 Main AnimInstance에 추가하지 않음.

싱글플레이 재현의 현 기반에서는 Player/Monster가 공유하는 Character 소유 ASC를 우선 검토한다. Lyra의 PlayerState 소유 방식을 무조건 복제하지 않는다. 플레이어 Pawn 교체/사망·재생성 간 능력·자원 지속 요구가 확정되면 Owner/Avatar 수명 정책을 먼저 결정한다.

Input.Action.Attack 같은 기존 입력 태그와 실행할 Ability의 연결은 명시적인 매핑/요청 API가 필요하다. GameplayTags 모듈이 있다는 사실만으로 GAS가 구현돼 있지는 않다.

액션별 Montage 요청은 Ability/Task 쪽에서 시작한다. Main ABP Slot은 결과 pose를 합성한다. 공격마다 Main AnimInstance에 bIsAttack01/bIsSkill02를 추가하지 않는다. 이동과 병행 가능한 액션만 상체 레이어를 사용하며 카잔의 모든 근접 공격이 상체 전용이라고 가정하지 않는다.

정상 완료뿐 아니라 피격·대시 취소·사망·Pawn 제거 시에도 hit window, 소유 이동 제한, 임시 효과, 이벤트 구독을 정리하는 경로가 필요하다. 종료 Notify 하나에만 영구 제한 해제를 맡기지 않는다.

### 애니메이션: 공통 관측 / 공통 흐름 / 세트별 pose를 분리

공통 UKhazanAnimInstance에는 실제 소비하는 snapshot/관측 데이터와 생명주기 경계를 둔다. struct로 묶는 것은 책임/수명을 드러내는 수단이지 연산을 자동으로 줄이는 기술이 아니다. gameplay 진실값을 별도의 mutable bool로 재결정하지 않는다.

동일 골격/운동 방식 계열의 Main ABP에는 공통 상태 흐름과 최종 합성을 둔다. 상태에서 호출할 pose 구현을 Animation Layer Interface로 분리하고 무기/운동 세트의 Linked Layers가 구현하게 한다. Stop 발 선택·진입 고정·클립 선택 등 로코모션 표현 전용 상태는 그 전용 레이어 영역에 귀속시킨다. C++ 유지가 필요한 부분은 전용 native AnimInstance 기반으로 모을 수 있지만 스냅샷 수집을 레이어마다 반복하지 않는다.

상태 진입/관련성 전용 작업은 Anim Node Functions 같은 실제 재생 수명 지점과 연결할 수 있다. On Become Relevant는 gameplay 입력이 일어난 순간이나 '게임플레이 상태 진입 단 한 번'과 동의어가 아니므로 재관련성/재연결 때 초기화 정책을 검증해야 한다. 기존 Stop의 진입 선택 고정과 sync buffer 의미는 보존한다. [Epic Lyra Animation](https://dev.epicgames.com/documentation/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine)

Linked Layer는 pose 교체 계약이고 DataAsset은 설정/에셋 선택이다. 둘은 대체재가 아니다. 같은 동작 구조에서 클립만 다른 경우 데이터/자식 기본값으로 재사용하고, 독립적인 흐름이 필요할 때만 구현 그래프를 나눈다. Layer linking이 매 프레임 필요하지는 않으며 장착/세트 변경 때 수행한다. 해제만으로 메모리가 자동 반환되는 것은 아니고 참조와 로딩 수명을 관리해야 한다. [Epic Animation Blueprint Linking](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-linking-in-unreal-engine)

서로 다른 골격의 이족/사족/특수 보스에게 하나의 Skeleton 전용 ABP를 그대로 강제하지 않는다. 공유할 수 있는 것은 gameplay 규칙/자료 계약이고, pose 그래프·IK·본 이름은 계열에 맞춰야 한다. 템플릿/retarget 사용 여부는 별도 호환성 검증 사항이다.

### 상태 표현 규칙

- 배타적인 소수 상태: enum. Gait/CMC MovementMode/이동 제어 상태는 서로 다른 축이다.
- 동시에 존재하는 gameplay 상태·제약: 소유 수명이 있는 GAS 태그/효과 또는 적절한 요청.
- 독립 관측 사실: 필요한 bool은 유지. bool 자체를 금지하지 않는다.
- frame 관측/진입 고정 이력/설정: 별도 struct 또는 전용 영역으로 수명을 구분.
- 한 액션/스킬/몬스터마다 메인 멤버나 전이를 추가하는 설계는 피한다.
- gameplay 액션과 ABP 재생 상태를 하나의 거대 enum으로 합치지 않는다.

## 4. 확장과 프로젝트 전체의 연결

새 캐릭터 정의 데이터에는 필요한 외형/골격 계열, 공통 이동 설정, 능력 세트, 애니메이션 세트 및 AI 설정 참조를 조합하는 방향을 권장한다. 이름 후보는 UKhazanCharacterDefinition이며 아직 만들지 않았다. 모든 정보를 거대한 단일 struct에 넣거나 모든 에셋을 hard reference로 묶으라는 뜻은 아니다.

이름/수치/클립만 다른 일반 적은 공통 C++와 데이터/태스크를 재사용한다. 특수 이동이나 전투 규칙이 실제로 다른 보스에는 전용 구현이 필요할 수 있다. '모든 몬스터를 데이터만으로 완성'을 약속하지 않는다.

HeinMach/StormPass의 Encounter/Spawn/Checkpoint/진행 저장은 캐릭터의 외부 소비자다. 레벨이 캐릭터 정의를 선택해 스폰하고 사망/전투 종료 이벤트를 구독하는 구조로 연결하며, AnimInstance가 현재 맵 이름·보스 페이즈·퀘스트를 판별하게 만들지 않는다. 레벨 콘텐츠 제작/복원과 게임플레이 아키텍처 검증은 구분한다.

종류 수와 동시 활성 개체 수는 별개다. 종류 확장은 공통 로직/데이터·자산 참조 분리, 동시 개체 성능은 animation/AI/physics/메모리 프로파일링 문제다. 현재 코드 길이나 bool 개수만으로 FPS 손실을 수치화하지 않았다.

AnimGraph의 직접 멤버/일부 nested struct 읽기는 Fast Path 대상이 될 수 있으므로 flat bool만이 유일한 최적화 방식은 아니다. 실제 연결의 Fast Path/스레드 안전성/레이어 데이터 수집 횟수를 검사한다. 다수 캐릭터는 Animation Budget Allocator 또는 URO 등의 선택을 프로파일링하고, 활성 전투의 판정·종료·Root Motion 계약을 깨지 않도록 해야 한다. [Epic Animation Optimization](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-optimization-in-unreal-engine)

## 5. 리팩터링 순서와 완료 조건 — 적용 전 제안

| 순서 | 작업 | 완료 조건 |
| --- | --- | --- |
| 기준선 | 실제 멤버 소비/기존 loop·Stop/입력 계약 고정 | 사용자 변경 보존, 빌드/회귀 검사 계획과 참조 목록 |
| 공통 이동 | Player의 장치 해석과 공통 이동 적용 분리 | Player와 AI 경로가 같은 제약/속도 정책 사용, 입력 재발생 없이 제한 반영 |
| 공통 표현 | 미사용 값 정리 및 Main/Locomotion Layer 경계 | 기존 loop/Stop 유지, 재연결/발 sync/Root Lock 검증, 타입별 별도 GT 수집 없음 |
| 공통 액션 최소 기능 | GAS 기반 기본 공격·피격·취소, 필요 Combat 판정 | Player와 일반 적이 같은 실행/취소/피해 경로 사용, 이동 제한 해제 충돌 없음 |
| 기능 횡단 검증 | 대시 및 SprintPivot를 확정 책임에 추가 | 액션과 이동 권한 충돌 없음, 일반 Stop/공중/입력/L3/사망 회귀 |
| 콘텐츠 확장 | 다른 무기·일반 적·보스 패턴·Encounter 연결 | 같은 방식의 콘텐츠 추가가 Main AnimInstance 수정 없이 가능 |

즉, 로코모션을 끝없이 먼저 완성한 뒤에만 전투를 시험하지 않는다. Player + 일반 적의 작은 전투 단위로 이동·공격·피격·취소의 결합이 맞는지 조기에 검증한다.

reflected 멤버를 실제 옮기거나 삭제할 때는 C++ 참조뿐 아니라 BP 연결/부모 클래스/redirect/직렬화까지 포함한다. 포맷만 바꾸거나 여러 파일로 동일한 if 분기를 복사하는 작업을 리팩터링 완료로 취급하지 않는다.

## 6. 다음 설명에서의 기준

새 함수/멤버/파일을 제안하기 전에 작성자, 실제 소비자, 수명, 스레드, 취소·해제 경로, Player/AI 공유 범위, 테스트를 먼저 설명한다. 하나의 함수 내부에서만 필요한 값은 지역 변수로 시작한다. 여러 프레임에 걸쳐 보존할 이유와 소비처가 있어야 멤버로 승격한다.

이번 단계에서는 설계 검토와 문서만 완료했다. 신규 코드·GAS·Linked Layer를 적용/컴파일/PIE 검증하지 않았다. 사용자와 책임 구조를 확정한 뒤 기존의 한 줄씩 설명하는 공동 구현 방식으로 진행한다.

## 2026-09-08 후속 결정 — 목표 아키텍처 v1 정본 확립

사용자가 전체 구조 확립과 Markdown 정리를 요청해 [CHARACTER_GAMEPLAY_ARCHITECTURE.md](CHARACTER_GAMEPLAY_ARCHITECTURE.md)를 작성했다. 이 검토의 사용처/문제 근거는 유지하되, 후속 책임 배치와 이관 순서는 새 정본을 따른다.

새 정본은 클래스 기반 제어 HFSM과 GAS 액션 실행의 중복 소유를 금지하고, 공통 이동·Locomotion Linked Layer·Player/AI·보스/레벨 진행까지 수명 계약과 단계별 검증으로 구체화했다. 이번에는 설계 문서만 작성했으며 해당 구조를 런타임에 적용하지 않았다.

