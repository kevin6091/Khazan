# Khazan Tag–Ability 아키텍처 마이그레이션

## 2026-09-08 — M0–M10 실행 기준 확정

- 목표 구조는 [아키텍처 v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2)다. 이 문서가 v1 A0–A7과 필수 제어 HFSM 선행 생성 순서를 대체한다.
- 사용자와 한 단계씩 구현한다. 설명/설계 승인과 실제 Source/BP 적용/빌드/PIE 완료를 구분한다.
- 현재 상태: M0 정적 기준선 확인 및 계획 수립. M1 [첫 단계 가이드](CHARACTER_TAG_ABILITY_STEP_1.md) 작성, **게임 적용 전**.
- 범위는 HeinMach/StormPass의 Player/일반 적/보스, 이동·공격·회피·스킬·피격·사망·장비·상호작용·레벨 진행이다. 로코모션 분리만으로 완료 처리하지 않는다.
- 실제 구현 단계에서는 Router → v2 → 이 문서의 현재 단계 → 현행 정본/해당 소스 순으로 읽는다. 모든 과거 가이드와 Content를 다시 전수 조사하지 않는다.

## 1. 단계별 범위와 완료 조건

| 단계 | 구현 범위 | 완료 판정 |
| --- | --- | --- |
| M0 — 현재 기준선 보존 | 현재 게임 파일/리포트/ABP 소비/남은 진단을 기록하고 v2와 현행 차이를 분리 | 기존 결과를 새 통과로 확대하지 않고 비교 대상을 특정. 이번에는 정적 기준선 확인 완료 |
| M1 — 공통 ASC 연결 | GAS 플러그인/모듈, Character의 엔진 ASC·IAbilitySystemInterface, ActorInfo 최초 연결/빙의 갱신/EndPlay 정리 | Player와 Monster에 각각 ASC 하나, 인터페이스 조회 일치, Owner/Avatar 일치, 기존 이동 회귀 없음. 사용자 적용/검증 대기 |
| M2 — 태그와 공통 이동 정책 | 소비할 최소 상태/Block 태그, 원인별 제약, CharacterDefinition 최소 이동 데이터, Player 입력과 CMC 적용 분리, AI 일반 이동 | 입력 없이 제약 변화 반영, 중첩 제한 하나만 해제, Player/AI 동일 gait 제한, raw intent/허용 명령 구분 |
| M3 — 최소 공통 전투와 Cue | Khazan ASC/Ability base, 요청·부여·Ready·관계 데이터, Attack/Jump/HitReact/Death, Attribute/Effect/CombatResponse, 기본 무기 판정·적중 Cue | Player/적 모두 같은 경로로 공격·비용·피해·반응·사망. 정상/거절/실패/취소 cleanup와 기존 Jump 우회 제거 |
| M4 — Main/Locomotion 표현 분리 | Main 공통 관측, Locomotion Linked Layer/세트, 기존 loop/Stop/발 이관, 미사용 경로 정리 | 현재 Walk/Run/Sprint/Stop 회귀 없음, Sync Group/Reset/relink 검증, M3 액션 Slot 유지, worker snapshot 검증 |
| M5 — 회피·장비·데이터 변형 | Dodge/무적 구간, 장비 AbilitySet·표현 세트·로드 수명, 두 번째 무기/적 데이터 | 겹친 무적/제약 정리, 교체·로드 실패 처리, 같은 실행 클래스가 다른 데이터로 동작 |
| M6 — 공간/타깃/워핑/타격 확장 | 실제 LockOn/액션 타깃, 필요한 MotionWarping, 표면 Cue, 형상별 타격·고속 sweep 검증 | 장애물/타깃 소멸/추적 종료/큰 각변위/화면 밖 평가, 워핑 실패와 적중을 구분 |
| M7 — 인터페이스 상호작용 | Interact Ability, Interactable 계약, 실제 상자/문, 결과 확정·취소·선택적 무적 | 중복 보상 없음, 확정 전 취소/확정 후 종료 구분, 대상 소멸·거리 이탈 정리 |
| M8 — Walk Turn / SprintPivot | 공통 이동 정책 아래 Walk 좌/우 Turn, 별도 SprintPivot과 Locomotion 표현 | Run Turn/모든 Start 제외, 일반 Stop과 분리, 공격/회피/피격 중단 후 구동 경쟁·재진입 없음 |
| M9 — 보스·Encounter·진행 저장 | 실제 페이즈/패턴, 필요한 Scripted 실행, 스폰·전투구역·체크포인트·Progression | 대상 레벨 전투→사망/리셋→진행까지 연결, 이전 Pawn callback/부여/레이어 수명 잔류 없음 |
| M10 — 콘텐츠 확장과 측정 | 종별 데이터/구조가 다른 Ability·형상, 지속 피해/추가 규칙, 회귀와 측정 | 데이터 검사·정확성 유지, 목표 환경에서 CPU/메모리/로드 검증. 측정 없는 수량/성능 약속 금지 |

단계 순서는 의존성과 회귀 범위를 줄이기 위한 프로젝트 결정이며 원작 게임 내부 개발 순서가 아니다. 각 단계도 다음 소단계처럼 나눈다.

## 2. M1 — 오늘 설명할 범위

M1은 상태와 Ability가 부착될 **공통 소유자와 엔진 접속 계약**만 만든다.

- 사용자 수정 예정 파일: `Khazan.uproject`, `Source/Khazan/Khazan.Build.cs`, `Source/Khazan/Character/KhazanCharacter.h/.cpp`.
- 첫 단계에서 사용하는 타입은 엔진 `UAbilitySystemComponent`다. 공통 요청 중재가 생기는 M3에서 `UKhazanAbilitySystemComponent`를 실제 구현한다. 지금 빈 subclass/Ability/State/DataAsset을 만들지 않는다.
- ASC Owner와 Avatar는 현재 Character다. PlayerState 영속 ASC나 복제 설정을 선행 도입하지 않는다.
- ActorInfo는 등록된 컴포넌트가 있는 gameplay world의 PostInitializeComponents에서 연결하고, 이후 빙의 변화는 RefreshAbilityActorInfo로 갱신한다. Pawn 초기화 중 빙의가 더 먼저 발생하는 경로도 처리한다.
- EndPlay에서 엔진의 DestroyActiveState를 호출한 뒤 부모 종료를 수행한다. ActorInfo를 먼저 비워 능력 종료 문맥을 없애지 않는다.
- M1에서 능력/속성/상태 태그를 아직 부여하지 않는다. ASC 발견 가능과 GameplayReady를 구분한다. 기존 이동 경로와 AnimInstance의 동작을 유지한다.
- 상세 위치·변수/함수·각 줄·에디터/빌드/런타임 검사는 [M1 가이드](CHARACTER_TAG_ABILITY_STEP_1.md)를 따른다.

## 3. M2 — 공통 이동과 태그 상태의 첫 실제 소비

1. 현재 Player의 입력 해석/속도 적용, Component의 허용 setter, CMC 회전 설정과 BP CDO override를 표적 대조한다.
2. 기존 이동 값을 단위/현재 적용값/원작 확인 상태로 기록하고 CharacterDefinition의 최소 이동 설정으로 이관한다. 기존 값이라는 이유로 원작 수치로 승격하지 않는다.
3. 원시 Player/AI 의도와 허용된 명령, 최종 이동 정책을 분리한다. L3 개인 요청은 입력 어댑터에 남긴다.
4. `Block.Movement.Input` 등 실제 소비할 태그와 원인별 이동 제약 handle을 연결한다. ASC count 변화 delegate와 초기 count를 읽고 소유 component의 종료 때 delegate를 해제한다.
5. Character/Ability/효과가 CMC를 제각각 덮지 않도록 Locomotion에 최종 적용 경로를 만든다. 같은 제한 기여를 태그와 handle 양쪽에 중복 기록하지 않는다.
6. 일반 적 하나의 AIController/PathFollowing에 같은 속도·회전·제약 정책을 적용한다. 기본 MoveTo가 회전/CMC 입력을 우회하는지 검증한다.

검사: 두 원인이 동시에 이동을 막는 동안 하나만 해제해도 계속 차단; 입력을 갱신하지 않아도 제약이 반영; 차단을 입력 Released로 덮지 않음; Walk/Run/Sprint/Stop과 재입력 보존. 큰 클래스/enum 전체 교체로 시작하지 않는다.

## 4. M3 — 전투 기능의 소단계

### M3.1 준비·부여·공통 요청

- 실제 Action 요청 소비가 생기므로 Khazan ASC와 Ability base를 만든다. M1 reflected 포인터는 엔진 base형, subobject 이름은 `AbilitySystemComponent`를 유지한다. 생성하는 concrete class 변경 시 기존 BP/CDO에 중복/유실이 없는지 확인한다.
- 최소 CharacterDefinition/AbilitySet/ActionDefinition/RelationshipData를 연결하고 source grant handle·load generation을 기록한다.
- Ability·Attribute·이동·표현·입력/AI의 필요한 준비가 끝난 후에만 `State.Ready.Gameplay`를 제공한다.
- Controller/BT는 공통 Action 요청을 사용한다. 요청 결과는 거절/버퍼/실행과 이유/실행 ID로 구분한다. 입력 태그 선언만으로 GAS 자동 연결을 주장하지 않는다.
- 같은 시기에 현재 `Input_Jump → Character.Jump` 우회를 Jump Ability 요청으로 이관한다. 카메라 입력/스틱 해석까지 Ability Tick으로 옮기지 않는다.

### M3.2 실행·몽타주·기본 무기 타격

- 기본 Attack Ability 하나와 실제 InGame Montage/Slot/ANS를 연결한다. 원작 데이터 우선, 필수 임시값은 출처·단위·이유를 표시한다.
- 실행 ID/몽타주·창 문맥을 검증해 Combat의 hit window를 열고 닫는다. 이전→현재 무기 위치 추적과 창별 중복 방지를 구현한다.
- 액션 이동 제약은 M2 계약을 사용한다. 종료가 다른 실행/상태 효과의 제한을 풀지 않는다.
- M4 이전에는 기존 ABP Slot을 사용할 수 있다. 전투 원본 bool/timer를 Main에 임시 추가하지 않는다.

### M3.3 Attribute/Effect와 반응

- 최소 HP/Stamina/Poise, 비용/피해 Effect와 필요한 계산을 만든다. 숫자의 근거를 따라 데이터화한다.
- target의 효과 적용/결과 확정 경계를 만들고 확정된 CombatResult를 CombatResponse에 전달한다. 각 attribute callback에서 Hit/Death를 따로 발행하지 않는다.
- CombatResponse는 사망 우선·무적/슈퍼아머/강인도 반응 규칙을 적용하고 태그/효과와 Event를 출력한다.
- HitReact와 Death Ability를 연결한다. Dead 효과는 Pawn 수명, Death Ability는 연출 수명이다. 일반 액션 취소와 EndPlay 전체 종료를 구분한다.
- 첫 범위는 즉시 적중이다. 향후 periodic damage를 추가할 때는 실제 주기 실행도 같은 결과 확정 경계에 연결한다.

### M3.4 공통 Cue와 수직 검증

- 최초 적중 Cue를 연결하고 hit 문맥이 올바른 연출에 도달하는지 확인한다.
- Controller의 테스트 진동은 승인/실행 결과 기반 피드백 경로로 이관하거나 테스트 잔재로 정리한다. 입력만 눌러도 진동하는 원본 동작을 새 원작 계약으로 간주하지 않는다.
- Player와 일반 적이 각각 공격자/피격자가 되는 같은 경로를 확인한다.
- 자원 부족, 준비 미완료, stun 중 요청, 공격 중 피격, 피격과 사망 동시, 늦은 callback, 몽타주 중단, EndPlay를 검사한다.
- 모든 substep 설명만 끝났다고 M3를 완료 처리하지 않는다. 실제 결과와 실패 이유를 남긴다.

## 5. M4 이후의 이관 주의점

- M4: 기존 ABP의 실제 native/BP/직렬화 참조를 검사하고 선택/이력을 함께 옮긴다. GetSyncGroupPosition의 소유 instance와 Reset을 확인한다. 미사용 후보는 참조 확인 후 정리하며 기존 CoreRedirect를 임의 삭제하지 않는다.
- M5: 같은 구조의 데이터 변형으로 재사용을 증명한다. Ability/무기/스켈레톤 요구가 다른데 grant만으로 재생 가능하다고 가정하지 않는다.
- M6: MotionWarping은 액션별 설정이다. locomotion/Stop root lock을 일괄 변경하지 않는다. 타깃 도달과 실제 적중을 따로 검사한다.
- M7: 상호작용 대상의 보상/진행 상태는 인터페이스 구현 소유다. 무적을 제공하면 실행별 Effect handle로 회수한다.
- M8: 기존 SprintPivot은 Locomotion 소유의 이동 동작이라는 결정을 유지한다. Ability와 별도로 같은 Pivot 실행 수명을 만들지 않는다.
- M9: 보스 페이즈와 Scripted 제어를 별도 거대 FSM으로 회귀시키지 않는다. 실제 주체가 요청/태그/부여/연출 수명을 소유한다.
- M10: 지속 피해처럼 새로운 효과 경로와 독립 실행의 공존은 검사 목록에 추가한다. 최적화 때문에 pose/Notify를 생략하면 타격 정확도 계약도 함께 검증한다.

## 6. 단계 완료 기록과 실패 시 재개

각 적용 기록은 날짜, 단계/소단계, 실제 수정 파일·BP 경로, 변경한 계약, 수치 출처, 빌드·런타임 결과, 미검증, 남은 작업을 포함한다. 문서 예제를 제시한 것은 적용 결과가 아니다.

- 빌드 실패: 마지막 성공한 substep과 현재 파일 diff/오류를 보존한다. 기존 사용자 변경/에셋을 전체 복원하지 않는다.
- 런타임 실패: 정상 경로와 실패 경로를 분리해 로그/필요한 runtime evidence를 수집한다. 추정한 AnimNode index와 과거 session/PID로 호출하지 않는다.
- 입력/몽타주/창 잔류: 해당 요청·Pawn·실행·effect/constraint handle을 확인한다. 모든 태그/제약을 일괄 지워 증상을 숨기지 않는다.
- 이관 중 일시 호환 경로가 필요하면 작성자는 하나이고 나머지는 읽기용 projection임을 명시한다. 같은 상태의 두 변경 가능한 원본을 만들지 않는다.
- 직접 구현/빌드/PIE 재개 전 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)의 이전 실행 상태를 현재 환경과 대조한다. 이번 설계 작업으로 과거 디버거/검증 callback 정리가 끝난 것은 아니다.

## 7. 이번 검증과 보존

- 기존 표적 리포트의 Source/Config/uproject/ABP_Player 39개 파일이 현재 디스크 파일과 같음을 확인했다.
- 실제 Input_Jump의 Jump/테스트 진동 직접 호출을 추가 이관 대상으로 기록했다.
- 로컬 UE 5.8.2의 ASC/Interface/ActorInfo lifecycle과 모듈 선언을 표적 확인했다. M1 제안 코드의 엔진 API 적합성을 확인한 범위다.
- 게임 코드/BP/Config/Build.cs/uproject/에셋은 이번에 변경하지 않았다. 신규 빌드·PIE·성능 시험은 수행하지 않았다.



## 2026-09-09 — GAS 유지 확정과 M1 설명 재개

- 사용자가 Gameplay Tags 기반 자체 FSM/액션 시스템 제안을 철회했다. [기존 v2 유지 결정](CHARACTER_GAMEPLAY_ARCHITECTURE.md#gas-retained-m1-resumed-20260909)에 따라 이 문서의 M0–M10 순서를 유지한다.
- 현재 단계: M1 공통 ASC 연결을 사용자가 직접 따라 구현하도록 상세 설명. [M1 본문과 재개 보충](CHARACTER_TAG_ABILITY_STEP_1.md#m1-resume-detail-20260909)을 함께 사용한다.
- 실제 디스크의 Character/Build.cs/uproject는 M1 적용 전임을 재확인했다. 생성자 default subobject/인터페이스/ActorInfo 연결을 설명했으며 C++/BP 직접 적용, 빌드/PIE 완료와 구분한다.
- 적용 순서: 기존 작업 보존/Editor 종료 → uproject → Build.cs → Character 헤더 → 생성/조회 → 최초 Init → 빙의 Refresh → EndPlay → 전체 빌드/새 Editor → Player·Monster별 ASC/ActorInfo/기존 이동 확인.
- M1의 인스턴스·인터페이스·Owner/Avatar·빙의 갱신·종료·이동 회귀 확인이 끝난 뒤 M2의 태그/원인별 공통 이동 정책으로 넘어간다. 단순 컴파일 성공이나 가이드 설명 완료만으로 M1을 완료 처리하지 않는다.


### 같은 작업 후속 확인 — M1 시작 상태 갱신

- Khazan.uproject의 GameplayAbilities 활성화가 별도로 반영됐다. 마지막 확인에서 Build.cs/Character는 기존 상태다. 플러그인 항목을 중복 추가하지 말고 현재 소스를 확인한 뒤 M1의 모듈/Character 연결부터 이어간다. 파일 설정 확인이며 플러그인의 실제 Editor 로드/빌드/PIE 검증은 아니다.



## 2026-09-09 — M1 사용자 완료, M2.1 안내 시작

- M1: 사용자 완료 보고를 받았고 실제 네 파일의 핵심 연결 코드를 확인했다. 이전 “플러그인만 반영/나머지 적용 대기”는 과거 시점이다. 개별 빌드/PIE 사례의 독립 재검증은 이번에 하지 않았다.
- 현재 공동 구현 단계는 [M2.1 태그 기반 입력 제한](CHARACTER_TAG_ABILITY_STEP_2.md)이다. 안내 코드는 미적용이며 설명을 M2 완료로 처리하지 않는다.
- M2.1: Block.Movement.Input, ASC 이벤트 등록/초기 조회/해제, 읽기용 허용 결과, 원시 입력과 출력 gate 분리, Effect handle A/B 중첩 검사.
- M2.2: CharacterDefinition의 최소 이동 데이터, 실제 BP/CDO·수치 출처 확인, Player의 CMC 적용 이관, 다중 원인 gait/회전·입력 소유 수명.
- M2.3: AIController/PathFollowing의 실제 구동과 같은 정책 연결, 우회/중단/재개/도착/실패 검사.
- M2.4: 기존 이동/Stop과 모든 제약·Player/AI 경로 통합 확인 후 M3 진입.
- 원래 M2의 데이터/공통 CMC/AI 완료 조건은 유지한다. 태그 선언 또는 Player만 멈추는 결과로 M2 전체를 완료하지 않는다.


- M2.1의 Player 입력 수명에는 UnPossessed 시 자기 이동/Sprint 요청 정리도 포함한다. Step 2의 16절을 적용하며, 태그/효과 전체 해제 또는 AI/CMC 이관 완료와 혼동하지 않는다.


## 2026-09-09 — M2.1 완료와 M2.2·M2.3 실행 순서 확정

- M2.1은 실제 effect A/B count/handle, IA_Move raw intent/CMC gate/Released, 반복 PIE 종료, Editor 종료 상태 전체 Development Editor 빌드까지 통과했다.
- 현재 사용자 적용 단계는 [M2.2·M2.3 연속 가이드](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)다. 두 단계를 한 번에 안내했지만 M2.2 전체 빌드/Player 검증을 중간 checkpoint로 둔다.
- M2.2의 확정 제안: 최소 CharacterDefinition 이동 config, raw intent와 resolved policy 분리, 현재 Controller별 intent token, gait/회전 constraint handle, Locomotion의 CMC 정책 단일 작성, Player의 입력 어댑터화, Anim GT snapshot 관측.
- M2.3의 확정 제안: 공통 Khazan CMC의 RequestPathMove/RequestDirectMove 최종 gate, AIController의 concrete request ID·pause 소유권, same-request resume, 완료/실패/abort/빙의 cleanup, 표준 BT Move To/PathFollowing 시험.
- 수입 Swordsman/Archer BP 두 종은 AActor 부모이므로 M2.3에서 강제 reparent하지 않는다. `AKhazanMonster` 기반 최소 시험 셸로 Player/일반 적 공통 수직 경로를 먼저 검증한다.
- 이 기록은 설계/설명이며 적용 완료가 아니다. M2.2/2.3 사용자 적용·빌드·PIE와 M2.4 통합 확인 뒤에만 M2를 닫고 M3로 진행한다.


<a id="player-first-migration-20260915"></a>
## 2026-09-15 — Player 우선 순서 개정: M2.3 AI 보류, P1 시작

### 현재 단계와 대체 범위

- M1 공통 ASC 연결, M2.1 태그 기반 Player 입력 차단, M2.2 Player Definition/Locomotion 정책과 runtime 행렬은 완료 기록을 유지한다.
- M2.3-A의 custom CharacterMovementComponent, AIController, Monster 자동 빙의, Blackboard/Behavior Tree는 아직 Source/Content에 적용되지 않았다. 이 구현은 중단이 아니라 **A1로 보류**한다.
- 위쪽 M0–M10 표와 M2.3 상세 순서는 과거 계획으로 보존한다. 충돌하는 미래 순서는 [아키텍처 v2.1 ARCH-20–29](CHARACTER_GAMEPLAY_ARCHITECTURE.md#player-first-combat-architecture-20260915)와 아래 P1–P8 → A1–A2 순서가 대체한다.
- 현재 공동 구현의 다음 단계는 **P1 — Player 공통 ActionRequest와 Basic Attack 실행 수직 절편**이다. 이 설계 갱신만으로 P1 소스가 적용되거나 빌드된 것은 아니다.

### 개정된 실행 순서

| 단계 | 실제 구현 범위 | 완료 조건 |
| --- | --- | --- |
| P0 — 검증된 기반 보존 | 기존 M1, M2.1, M2.2 결과와 `/Game/Test/BP_M2MovementProbe` 근거를 기준선으로 고정 | Player Walk/Run/Sprint/Stop, raw/resolved 분리, 중첩 tag/constraint, UnPossess/재PIE 결과를 새 단계의 완료로 중복 주장하지 않음. 현재 완료 |
| P1 — Player 액션 진입과 한 실행 | 실제 Basic Attack 소비와 함께 Khazan ASC/Ability base, ActionRequest/Result, 요청·실행 ID, 전신 액션 lane, 최소 grant/Ready를 연결. Attack/Jump 입력 우회 제거 | Attack 입력 한 번이 공통 요청→승인→Ability→Montage/이동 제약→정상·취소 cleanup을 통과. 연타/차단/실패 이유와 실행 ID 확인. Jump도 직접 호출 우회를 남기지 않음 |
| P2 — Attribute와 Stamina | 최소 HP/Stamina/Poise 초기화, 공격 비용, regen, resolved Sprint와 drain/Run 제한의 원인별 수명 | 비용 성공/부족 거절, regen 차단·재개, Sprint drain 시작/종료, 부족 시 Sprint만 제한, 사망/UnPossess/EndPlay handle 정리. 임의 수치는 출처 분류 |
| P3 — 기본 전투 결과 수직 절편 | Basic Attack hit window, Combat 판정, 무판단 공통 target, EffectSpec/CombatResult, HitReact/Death, 최초 Cue | Player가 target을 맞히는 경로와 test result로 Player가 맞는 경로가 같은 계약을 사용. 중복 hit, 피격과 사망 동시, montage 중단, 늦은 callback 검증. AI 판단 없음 |
| P4 — 표현 책임 분리 | Main 공통 snapshot/Slot과 Locomotion Linked Layer로 기존 loop/Walk·Run 발별 Stop/Sprint 단일 Stop 이관 | 현재 이동·Stop 회귀 없음, 진입 gait/발 고정, sync/reset/relink, 공격 Montage Slot과 worker snapshot 검증 |
| P5 — SprintPivot | Locomotion maneuver 수명, 큰 Sprint 방향 반전 판정, 짧은 Sprint Stop pose, 제동·방향 재설정, action/피격/사망/공중 중단 | 일반 Stop과 구분, 한 maneuver만 활성, 최신 raw 입력 보존, attack/hit/death/fall/입력 해제/태그 차단/재진입/늦은 callback에서 자기 handle만 정리 |
| P6 — Combo와 해금 분기 | Combo Ability runtime node/buffer/window, 읽기 전용 Combo Definition, Progression 해금 투영, 별도 Skill Ability 전환 | 같은 입력에서 해금 전후 가능한 edge가 정확히 달라지고, 잘못된 edge/비용 실패가 현재 합법 실행을 깨지 않음. Pivot→Attack 및 interruption 회귀 |
| P7 — Dodge/Guard/Parry/Deflect | 회피 비용·무적 창, 방어/패링 창, CombatResult 방어 해석, 공격자 Deflected 반응, Poise 규칙 | 피해/회피/방어/패링/튕김 결과가 단일 hit에서 하나로 확정. 양쪽 실행 ID와 창 소유권, Stamina 실패, Pivot 중 Dodge/Parry 중단 회귀 |
| P8 — 공중·추락·사망·리스폰 | CMC movement mode projection, fall consequence, Dead Effect/Death Ability, 체크포인트 새 Pawn 재구성 | grounded action 차단, fall/landing 결과, 중복 사망 방지, old Pawn callback 무효화, Definition/Attribute/Ability/해금 재적용. 제자리 Resurrection은 실제 요구가 있을 때 별도 |
| A1 — AI 이동 어댑터 | 보류한 common CMC gate, AIController intent token, PathFollowing request ID/pause/resume/abort, 최소 Monster Definition | Player 기준선 회귀 없이 일반 적 한 종의 접근 이동과 block 중첩, 동일 request만 재개, UnPossess/재PIE 정리 |
| A2 — AI 전투 판단 어댑터 | perception/target memory, 전술 선택, ActionRequest BT/StateTree task, spacing/공격/방어 요청 | AI가 Montage/비용/피해를 직접 실행하지 않고 P1–P8 공통 계약으로 공격·피격·패링·사망. Task Abort가 자기 request/execution만 취소 |
| C1 이후 — 콘텐츠 확장 | 장비 변형, targeting/warping, 형상별 타격, 상호작용, 보스/Encounter/Progression, 측정 | 기존 M5–M10의 데이터 변형·공간·상호작용·보스·성능 조건을 기능별 수직 절편에 적용 |

이 순서는 원작 내부 개발 순서가 아니라 현재 프로젝트의 재작업을 줄이기 위한 결정이다. P1–P8 동안 공개 API와 데이터는 미래 AI도 사용할 공통 Character/ASC/Locomotion 계층에 둔다. Player를 먼저 구현한다는 이유로 `AKhazanPlayer` 전용 Ability, Monster cast, Player 입력을 요구하는 공통 전투 함수를 만들지 않는다.

### P1의 정확한 구현 경계

P1은 상태 이름을 대량 선언하는 단계가 아니다. **한 번의 Attack 입력이 실제 소비하는 최소 공통 경로**를 완성하면서 필요한 타입만 만든다.

1. `KhazanGameplayTags`에는 P1에서 즉시 소비하는 Ability/Owned/Ready/Block leaf만 추가한다. Combo, Parry, Deflect, Death, AI 태그는 해당 단계 전에는 미리 선언하지 않는다.
2. `UKhazanAbilitySystemComponent`를 만들고 현재 `AKhazanCharacter`의 default subobject concrete class만 교체한다. reflected 포인터의 엔진 base형과 `AbilitySystemComponent` subobject 이름은 유지해 기존 BP/CDO 중복 생성 위험을 줄인다.
3. `UKhazanGameplayAbility` base에는 공통 요청이 읽을 전신 lane/독립 실행 분류와 실행 식별 계약만 둔다. 콤보 index, 공격별 montage, Monster 판단을 base 멤버로 올리지 않는다.
4. Character Definition에는 실제 Basic Attack을 부여할 최소 AbilitySet 참조만 연결한다. AbilitySet entry는 grant class와 요청 식별에 필요한 최소 mapping을 제공하고, ASC는 source grant handle을 보관해 Pawn 종료/재초기화에서 자기 grant만 회수한다.
5. ActorInfo, 필수 Definition, P1 AbilitySet grant, 입력 어댑터 준비가 모두 성공한 뒤에만 `State.Ready.Gameplay`를 부여한다. Definition 누락이나 grant 실패를 lazy fallback 성공처럼 숨기지 않는다.
6. Basic Attack Ability 하나가 공통 요청의 첫 실제 소비자가 된다. 승인 후 자기 실행 ID, 전신 lane, Montage/Task, Locomotion constraint, delegate를 취득하고 정상 종료·입력 취소·몽타주 실패·Ability 취소·EndPlay에서 자기 것만 정리한다. P1에서는 타격/피해를 아직 성공했다고 기록하지 않는다.
7. `AKhazanPlayerController::Input_Attack`은 장치 입력을 의미 요청으로 전달한다. 단발 Attack은 `Triggered` 매 frame 호출과 분리해 Started/Completed 의미를 명시한다. `Input_Jump`의 `Character::Jump()` 직접 호출도 공통 요청을 거치는 최소 Jump Ability로 옮기되, 카메라 회전과 Move/Sprint raw intent는 Ability로 옮기지 않는다.
8. Jump에 붙은 시험용 `PlayDynamicForceFeedback`는 제거하거나 P3의 확정 결과 Cue/피드백 경로로 이동한다. 입력을 누른 사실만으로 성공 피드백을 재생하지 않는다.

P1에서 별도 CharacterStateMachine, `EPlayerState`, CombatResponse, Combo Manager/Definition, AIController, custom CMC, Blackboard/BT를 만들지 않는다. CombatResponse는 P3, Combo Definition은 P6, AI 전용 타입은 A1/A2에서 실제 소비와 함께 만든다.

### P1 검증 순서

1. Editor 종료 상태에서 UHT/Development Editor 전체 빌드를 수행하고 기존 Player BP의 ASC subobject가 하나인지, class-default Definition selector가 보존됐는지 확인한다.
2. 새 Editor/PIE에서 ActorInfo Owner/Avatar, Definition, Ability grant source, Ready tag count를 확인한다. 준비 실패 Pawn은 Attack 요청을 명확한 이유로 거절해야 한다.
3. Attack Started 한 번이 요청 ID 하나와 실행 ID 하나를 만들고 Montage가 한 번만 시작하는지 본다. 키를 유지해도 의도하지 않은 매-frame 재요청이 없어야 한다.
4. 공격 중 같은 입력, Jump 요청, Block.Action.Input, 준비 태그 제거를 각각 시험해 실행됨/버퍼됨/거절됨과 이유를 구분한다. P1에 일반 pending buffer를 아직 구현하지 않았다면 `버퍼 없음`이 명시적 결과여야 한다.
5. Montage 정상 종료, 강제 중단, Pawn UnPossess, PIE 종료에서 전신 lane, Owned tag, Locomotion constraint, delegate/Task가 남지 않는지 확인한다. 실패한 후보 요청은 기존 실행을 먼저 취소하지 않아야 한다.
6. 기존 M2.2의 Walk/Run/Sprint/Stop, raw input 보존, gait/rotation constraint A/B와 Block GE A/B, 재PIE 초기값을 표적 회귀한다. 전체 M2.2 행렬은 관련 코드가 바뀐 범위만 다시 확인한다.

P1 수치가 필요한 경우 원작 metadata 직접값, 원작 기반 계산값, 임시 튜닝값을 구분한다. Basic Attack의 재생률·취소 window·이동 제한을 편의상 magic number로 넣지 않는다. 원본 확인 전에도 구조 구현은 가능하지만 필수 임시값은 Ability/Action 데이터 한곳에 두고 출처와 조정 기준을 기록한다.

### 보류한 M2.3을 다시 여는 조건

A1을 시작할 때는 기존 Step 2의 21절 코드를 그대로 적용하지 않는다. P1–P8에서 확정된 ActionRequest, Ready, Stamina, Dead, Locomotion maneuver 중단 계약을 먼저 대조한 뒤 다음만 재사용한다.

- PathFollowing의 raw intent와 Player raw intent가 같은 Locomotion policy를 통과한다는 원칙
- concrete `FAIRequestID`, 자기 pause 소유권, same-request resume, 완료/실패/Abort/UnPossess cleanup
- 일반 접근 이동은 PathFollowing, 전투 위치 정렬/warping은 Ability 실행이 소유한다는 경계

AI 시험 Pawn은 Player 공격의 무판단 target으로 먼저 사용할 수 있지만, 이것은 AIController/BT 구현 완료가 아니다. A1/A2 전까지 수입 Swordsman/Archer를 강제 reparent하거나 미래 Monster 데이터 필드를 Character Definition에 미리 채우지 않는다.


### 2026-09-15 — A1의 custom CMC 생성 판정 checkpoint

- A1 표의 `common CMC gate`는 지금 빈 `UKhazanCharacterMovementComponent`를 미리 만들라는 뜻이 아니다. P1–P4는 엔진 기본 CMC를 유지하고, P5도 공개 API와 Locomotion maneuver로 먼저 구현한다.
- A1 시작 시 Player `AddMovementInput` 경로와 AI PathFollowing의 `RequestPathMove`/`RequestDirectMove` 경로를 각각 추적한다. Controller pause만으로 모든 AI movement request가 멈추고 raw intent/재개 계약도 만족하면 subclass를 생략할 수 있다.
- PathFollowing 또는 다른 navigation producer가 Controller gate를 우회하거나, block 중 raw intent 보존과 pending engine request 제거를 동시에 만족시키지 못하면 그 시점에 `UKhazanCharacterMovementComponent`를 만든다. 이는 실제 두 virtual 함수의 소비가 생긴 경우다.
- 생성할 때는 `AKhazanCharacter`의 inherited `CharacterMovementComponentName`을 `FObjectInitializer::SetDefaultSubobjectClass`로 교체한다. 두 번째 movement component를 만들지 않으며 Player BP CDO의 inherited class, Definition selector, M2.2 이동 회귀를 cold build/새 Editor에서 확인한다.
- CMC는 navigation/physics adapter만 맡는다. AIController가 concrete path request ID와 pause/resume 수명을, LocomotionComponent가 intent/policy/constraint를 계속 소유한다. CMC 교체만을 이유로 `PostInitializeComponents()` 호출 순서를 함께 바꾸지 않는다.


<a id="p1-simplification-review-20260915"></a>
## 2026-09-15 — P1 ActionRequest 재검토와 구현 보류

- [판정] v2의 GAS 중심 상태·Ability 실행·Locomotion·표현·AI 책임 분리는 유지할 가치가 있다. 그러나 현재 P1 표와 실습판의 ActionRequest/Result, Request ID + Execution ID, 세 종류의 runtime 원장, pending activation handshake, Player request source와 결합한 Ready, custom full-body lane을 첫 공격 전에 모두 만드는 범위는 과하다.
- [공식 API 대조] UE 5.8 GAS가 이미 spec handle, input pressed/released 전달, 활성화 시도, failure tag callback, end callback/취소 여부, Ability/Task 수명을 제공한다. 공식 Lyra도 Input Tag → Ability activation, AbilitySet grant handles, tag relationships, activation policy/group를 GAS 확장으로 구현한다. StateTree는 범용 HFSM이지만 Player 액션 전투의 공식 필수 상위 제어기라는 근거는 확인하지 못했다.
- [즉시 상태] 기존 P1-A 절차는 적용하지 않는다. P1 Source가 아직 없으므로 삭제/롤백할 게임 코드도 없다. [P1 실습판](CHARACTER_TAG_ABILITY_P1_WALKTHROUGH.md)의 기존 코드는 과거 제안으로 보존하며, 하단 보류 절보다 우선하지 않는다.
- [교체 후보] P1은 custom ASC, Ability base, AbilitySet의 `Ability class + optional InputTag`, Controller의 InputTag pressed/released 전달, BasicAttack/Jump Ability, Montage Task, Locomotion constraint, GAS failure/end 관측만으로 다시 자른다.
- [제외 후보] P1에서 custom ActionRequest/Result와 실패 enum, Request/Execution ID, active request/execution maps, pending handshake, source registration, custom exclusive lane을 제외한다. 태그 block/cancel로 첫 동시성 규칙을 표현하고 두 번째 실제 사례가 생길 때 Lyra식 Activation Group을 검토한다.
- [후속 추가 조건] P3의 stale hit callback에는 공격 지역 token, A2의 BT/StateTree wait/abort에는 외부 request ticket, P6의 같은 콤보 연타에는 활성 Combo Ability 지역 buffer를 실제 필요가 확인되는 단계에서 각각 추가한다. 서로 다른 액션 사이 queue는 조작 시험이 요구할 때만 별도 확장한다.
- [StateTree 위치] Player combat에는 지금 추가하지 않는다. A2 AI의 상위 의사결정이나 보스/Scripted orchestration에 실제 소비자가 생기면 StateTree Task가 GAS Ability를 요청하고 완료를 기다리는 adapter로 검토한다.
- [수치] 제안에 포함된 `0.2~0.3초` buffer 수명은 원작 metadata 근거도 공식 필수 기본값 근거도 확인되지 않았으므로 채택하지 않는다. P6에서 원작 직접값/계산값/명시적 임시 튜닝값으로 다시 판정한다.
- [결정 경계] 이 절은 단순화 권고와 P1 보류 기록이다. 기존 ARCH-22와 P1 정본을 실제로 교체하는 최종 계약/상세 실습판은 사용자의 방향 결정 뒤 별도 날짜 절에 작성한다.


<a id="p1-v2-2-minimal-contract-20260915"></a>
## 2026-09-15 — v2.2 채택과 최소 P1 계약 확정

### 대체 범위

- 사용자가 GAS 중심 구조 유지와 오버엔지니어링 금지를 확정했다. Architecture의 `v2.2 GAS 중심 구조와 단순성 불변식`이 최신 정본이다.
- 위쪽 P1 표와 182–206행의 ActionRequest/Result, Request/Execution ID, 전신 lane, input source 기반 Ready 및 그 검증 절차는 과거 계획이다. 아래 최소 P1이 충돌 범위를 대체한다.
- 기존 P1 실습판의 코드는 구현하지 않는다. 새 P1 공동 구현 설명은 최소 계약을 기준으로 처음부터 다시 작성한다.

### 최소 P1의 기능 목표

Attack 입력 한 번이 기존 `Input.Action.Attack` tag를 통해 하나의 granted Ability spec을 찾아 정확히 한 번 활성화하고, 그 Ability가 한 공격 Montage와 필요한 Locomotion constraint를 소유한 뒤 정상·중단·취소·EndPlay에서 정리되는 경로를 만든다. Jump도 기존 직접 `Character::Jump()` 우회를 Ability 실행으로 옮긴다.

### P1에서 만드는 것

1. 기존 `Input.Action.Attack/Jump`를 AbilitySet entry의 입력 식별로 재사용한다. `Action.Attack` 같은 중간 namespace를 추가하지 않는다.
2. `UKhazanAbilitySystemComponent`는 입력 tag와 일치하는 spec에 `AbilitySpecInputPressed/Released`를 전달하고 필요한 시점에 `TryActivateAbility`를 호출하는 기능만 가진다.
3. 최소 `UKhazanAbilitySet`은 Ability class와 선택적 Input Tag를 가진다. 실제 제거·재부여가 필요한 grant owner만 엔진 Spec handle을 보관한다.
4. `UKhazanGameplayAbility` base는 두 Ability의 실제 공통 동작이나 ASC가 읽을 설정이 생길 때만 만든다. 그렇지 않으면 P1 Ability는 `UGameplayAbility`를 직접 상속한다.
5. BasicAttack Ability는 Montage AbilityTask와 자기 Locomotion constraint를 소유한다. Jump Ability는 Jump/StopJumping과 press/release 수명을 소유한다.
6. 실패는 GAS failure tag/callback과 구체 로그로 관측하고, 종료는 Ability end/cancel 정보를 사용한다.

### P1에서 만들지 않는 것

- `FKhazanActionRequest`, `FKhazanActionRequestResult`, 별도 실패 enum
- Request ID, Execution ID, active request/execution map, pending activation handshake
- request source 등록, custom full-body lane, Activation Group
- `State.Ready.Gameplay`와 readiness contribution ledger
- 공통 입력 buffer, Combo Definition, Relationship DataAsset
- CombatComponent, CombatResponseComponent, TargetingComponent, custom CMC, AI 타입
- P1 소비가 없는 Owned/Window/Combo/Parry/Death tag

### 최소 검증

1. Input Started 한 번에 Attack Ability가 한 번만 활성화된다.
2. 입력 유지가 의도치 않은 매-frame 재활성화를 만들지 않는다.
3. Ability가 활성 중일 때 같은 spec 재활성화 결과가 설정한 GAS 정책과 일치한다.
4. Montage 정상 종료·강제 중단·Ability 취소·UnPossess/EndPlay에서 task와 Locomotion constraint가 남지 않는다.
5. Jump press/release가 Ability를 통과하며 Controller가 직접 Jump/StopJumping하지 않는다.
6. 실패한 활성화가 기존 실행이나 다른 이동 제약을 정리하지 않는다.
7. M2.2 Walk/Run/Sprint/Stop과 중첩 movement constraint 회귀가 없다.

### 뒤 단계의 단순화 경계

- P3은 첫 근접 hit의 수명을 AbilityTask/Ability 지역 소유로 먼저 닫고, 실제 공유 서비스가 확인될 때만 CombatComponent를 만든다. CombatResult에는 첫 소비에 필요한 필드만 둔다.
- P6은 실제 원작 콤보가 선형이면 작은 순서 데이터와 활성 Ability의 buffered input 하나로 시작한다. 확인되지 않은 branching graph나 전역 queue를 미리 만들지 않는다.
- P7은 GAS 기본 block/cancel/required tag로 시작하고, 여러 Ability에 동일 관계가 반복될 때만 중앙 Tag Relationship Mapping을 만든다.
- A2 AI는 Ability tag 또는 Spec handle로 같은 GAS Ability를 활성화한다. 특정 BT/StateTree Task의 wait/abort에 구분이 필요할 때만 그 Task 수명의 ticket을 추가한다.
- 각 단계 시작 전에 새 class/tag/DataAsset/delegate/handle의 현재 작성자와 소비자를 확인하며, 없으면 그 단계에서 제외한다.

### 큰 단계는 다음처럼 다시 자른다

- P2는 먼저 Stamina Attribute와 BasicAttack 비용 한 경로만 만든다. Sprint drain/regen은 그다음 소단계이며, HP는 실제 피해가 시작되는 P3, Poise는 실제 경직 규칙이 시작되는 P7까지 만들지 않을 수 있다.
- P3은 `한 번의 hit 후보 생성` → `한 번의 damage 적용` → `HitReact` → `HP 0의 Death` → `Cue` 순으로 각각 빌드/런타임 확인 가능한 소단계로 나눈다. 첫 소단계부터 모든 반응 Component와 결과 필드를 만들지 않는다.
- P4는 현재 이동 포즈 보존 → Linked Layer 이관 → Slot 합성 순으로 나눠 기존 Locomotion 회귀 지점을 좁힌다.
- P6은 단일 다음 공격 입력 → 선형 연속 공격 → 실제 분기 → 해금 반영 → 별도 Skill 전환 순으로 늘린다. 앞 단계 소비가 없는 graph 기능을 다음 단계 때문에 만들지 않는다.
- P7은 Dodge → Invincible window → Guard → Parry/Deflect → Poise 순으로 독립 수직 절편을 만든다. 한 번에 방어 체계 전체를 구현하지 않는다.
- P8과 A1/A2도 한 gameplay 결과 또는 한 AI 행동이 처음부터 끝까지 동작하는 크기로 나눈다. 표의 단계명은 목표 묶음이며 한 번에 생성할 파일 묶음이 아니다.


<a id="p1-v2-3-capability-component-migration-20260915"></a>
## 2026-09-15 — v2.3 capability component 반영과 P1 실행 순서 재편

### 최신 기준

- Architecture의 [v2.3 capability component와 단일 CombatComponent 경계](CHARACTER_GAMEPLAY_ARCHITECTURE.md#architecture-v2-3-capability-components-20260915)가 Component 책임과 P1 입력 범위의 최신 계약이다.
- v2.2에서 확정한 GAS 중심 구조와 오버엔지니어링 금지는 유지한다. 이 절은 `P1 시작부터 pressed/released 전체 지원`, `P3에서 CombatComponent가 계속 미확정`인 부분만 대체한다.
- 실제 공동 구현은 [P1 최소 실습판 v2.3](CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md)을 사용한다. 과거 `CHARACTER_TAG_ABILITY_P1_WALKTHROUGH.md`의 ActionRequest 코드는 사용하지 않는다.

### P1 — 입력에서 자기 정리까지 한 Ability 실행

| 순서 | 한 번에 구현할 것 | 이 checkpoint가 증명하는 것 | 아직 넣지 않는 것 |
| --- | --- | --- | --- |
| P1.1 | 얇은 `UKhazanAbilitySystemComponent`와 Character의 concrete subobject 교체 | 기존 ASC lifecycle을 보존하면서 `InputTag → granted spec activation` 책임을 둘 실제 위치가 생긴다. | AbilitySet, Ability, Controller 연결, buffer, pressed/released |
| P1.2 | Ability class + Input Tag 한 쌍만 가진 최소 `UKhazanAbilitySet`, CharacterDefinition의 grant | Character variant가 가진 시작 Ability가 엔진 Spec으로 정확히 한 번 부여된다. | Effect/Attribute 묶음, 재부여 원장, 레벨 scaling |
| P1.3 | 직접 `UGameplayAbility`를 상속한 `UKhazanBasicAttackAbility`와 활성화 관측 | 빈 공통 Ability base 없이 Attack spec 하나가 실행되고 종료된다. | montage, hit, damage, combo |
| P1.4 | PlayerController의 Attack을 `Started`에서 ASC 입력 tag API로 연결 | 물리 입력 한 번이 Ability 한 번으로 이어지고 hold가 frame 반복을 만들지 않는다. | Player 전용 ActionRequest DTO, 전역 input queue |
| P1.5 | BasicAttack montage task + 해당 실행의 Locomotion constraint | montage 정상 종료·중단·취소에서 Ability가 자기 task/constraint만 정리한다. | hit window, stamina, damage, full-body lane Manager |
| P1.6 | Jump Ability와 필요한 pressed/released 전달 | Controller의 직접 Jump/StopJumping 우회가 사라지고 release 수명이 GAS task까지 도달한다. | 모든 입력의 held processor, combo buffer |
| P1.7 | P1 전체 및 M2.2 회귀 검증 | Attack/Jump와 기존 Walk/Run/Sprint/Stop, 중첩 제약, UnPossess/EndPlay가 함께 안전하다. | P2 이후 기능 |

각 행은 독립 cold build 가능한 크기다. 앞 행이 빌드되고 그 행의 관측 결과가 확인되기 전에는 다음 행의 새 타입을 만들지 않는다.

### P2 — 첫 실제 비용

1. Stamina AttributeSet에 실제 필요한 current/max 값만 추가한다.
2. BasicAttack 한 개의 Cost GameplayEffect를 연결한다.
3. 비용 부족 시 GAS activation failure와 기존 실행 불변을 확인한다.
4. Sprint drain/regen은 별도 checkpoint에서 추가한다.

### P3 — 단일 CombatComponent를 실제 hit와 함께 도입

1. P3.1: BasicAttack 실행이 한 번의 접촉 후보를 만들 때 `UKhazanCombatComponent`를 생성하고 공통 owner 계약을 검증한다.
2. P3.2: Player와 한 적이 같은 Component API로 확정 접촉 한 건을 교환한다. 공격 window의 중복 대상 집합은 그 Ability/Task가 소유한다.
3. P3.3: Component의 공통 진입점이 Damage GameplayEffect spec을 target ASC에 적용한다.
4. P3.4: GameplayEvent로 HitReact Ability를 활성화하고 HP 0에서 Death를 검증한다.
5. P3.5: 확정 결과 뒤 GameplayCue 표현을 연결한다.

P3 시작 때 `CombatResponseComponent`, `HitComponent`, `GuardComponent`, `ParryComponent`, `PoiseComponent`를 함께 만들지 않는다. 각 기능은 먼저 Ability/Task/Effect/Tag와 하나의 CombatComponent로 구현하고, 독립 부착·교체·수명 요구가 실제로 생길 때만 새 Component 후보를 심사한다.

### 이후 단계

- P4: 현재 locomotion pose 보존 → Linked Layer 이관 → combat Slot 합성.
- P5: Ability가 LocomotionComponent의 공개 maneuver/constraint API를 실제 소비. 공개 API로 CMC 구동이 부족하다는 증거가 있을 때만 custom CMC.
- P6: 단일 후속 입력 → 선형 combo → 확인된 분기 순. 활성 Ability 지역 buffer로 시작.
- P7: Dodge → Invincible → Guard → Parry/Deflect → Poise. GAS 기본 tag 관계를 먼저 사용.
- P8: 스킬 한 개의 targeting → cost → effect → cue 수직 절편.
- A1/A2: 공통 Character/CombatComponent/Ability를 적에게 재사용하고, AI 의사결정 계층은 실제 필요 시 BT 또는 StateTree adapter로 연결.

### Component 수 검토 checkpoint

새 Component 제안마다 다음을 기록한다.

1. 이 Component를 붙일 서로 다른 실제 owner가 둘 이상인가?
2. 붙였을 때 얻는 한 문장의 능력은 무엇인가?
3. 요구하는 owner interface/component는 무엇인가?
4. Ability 한 번의 지역 상태로 끝낼 수 없는 이유는 무엇인가?
5. 기존 ASC, CombatComponent, LocomotionComponent에 넣으면 응집도가 깨지는가?
6. Begin/EndPlay와 취소 시 자신이 정리할 자원은 무엇인가?

답이 없으면 새 Component를 만들지 않고 현재 owner의 작은 함수 또는 Ability/Task 지역 구현으로 시작한다.

### P1.2–P1.4 검증 시점 명확화

- 위 표의 P1.3 `활성화 관측`은 P1.4 입력 연결까지 합쳐졌을 때 수행하는 검증을 뜻한다. 독립 checkpoint의 정확한 경계는 P1.2에서 AbilitySet grant 계약, P1.3에서 BasicAttack class와 granted spec 존재, P1.4에서 `Attack Started → Input Tag → TryActivateAbility → 실행/종료`다. 검증만을 위해 P1.3에 임시 자동 활성화 코드나 test Tick을 넣지 않는다.


<a id="p1-v2-4-direct-definition-grants-20260915"></a>
## 2026-09-15 — v2.4 전역 Component 기준 반영과 P1.2 수정

### 정정

- 사용자의 Component 예시는 특정 CombatComponent 확정 요청이 아니었다. Architecture v2.4의 capability 원칙을 모든 현재/미래 Component와 다른 구조 추출에 적용한다.
- `UKhazanCombatComponent`는 P3 필수 타입이 아니라 실제 공통 hit 상태/API가 GAS Ability/Task/Effect만으로 닫히지 않을 때의 후보로 되돌린다.
- P1.2의 별도 `UKhazanAbilitySet`도 현재 grant source 하나에는 불필요한 asset 계층이다. 기존 `UKhazanCharacterDefinitionData`에 최소 초기 grant 배열을 직접 두는 아래 절차가 앞선 P1.2 AbilitySet 행을 대체한다.

### P1.1 실제 확인 결과

- 사용자가 `Source/Khazan/Ability/KhazanAbilitySystemComponent.h/.cpp`를 작성했고 제안한 `TryActivateAbilitiesByInputTag` 구현과 일치한다.
- `AKhazanCharacter`는 기존 이름의 ASC default subobject 하나를 `UKhazanAbilitySystemComponent` concrete class로 생성한다. 기존 base pointer와 ActorInfo/possess/end lifecycle은 유지됐다.
- 2026-09-15 19:08 UBT 기록에서 UE 5.8.2 UHT가 3개 generated file을 작성했고 새 ASC cpp와 Character cpp compile, module/DLL link, metadata가 모두 성공했다. `Result: Succeeded`다.
- 최신 `Khazan.log`는 이 빌드 전 기록이므로 새 Editor/PIE에서 component runtime class와 M2.2 회귀를 확인한 증거는 아직 없다. P1.2 작성은 진행하되 P1 전체 완료 전 반드시 확인한다.

### 수정된 P1 순서

| 순서 | 범위 | 완료 기준 |
| --- | --- | --- |
| P1.1 | Khazan ASC + Character concrete subobject | Source 대조와 cold build 성공. 새 PIE 회귀 확인은 누적 검증 대기. |
| P1.2 | CharacterDefinition의 `InitialAbilityGrants` + Character의 authority one-shot grant | 새 schema/build 성공, 기존 Definition locomotion 값 보존, 빈 배열 PIE 무효과. |
| P1.3 | `UKhazanBasicAttackAbility` 최소 실행/종료 + Definition에 한 entry | ASC에 BasicAttack spec 한 개가 존재. |
| P1.4 | Attack `Started`를 Input Tag activation으로 연결 | 입력 한 번에 Ability 한 번 실행·종료. |
| P1.5 | Montage Task + 실행별 Locomotion constraint | 정상/중단/취소/EndPlay cleanup. |
| P1.6 | Jump Ability + 실제 press/release generic event | 직접 Character Jump 우회 제거와 release 종료. |
| P1.7 | 누적 회귀 | ASC class, Definition, Attack/Jump, M2.2 이동/constraint 모두 통과. |

### P1.2에서 만드는 것

1. `KhazanCharacterDefinitionData.h` 안의 `FKhazanInitialAbilityGrant`.
2. 같은 Definition의 `InitialAbilityGrants`와 const-reference getter.
3. `AKhazanCharacter::PostInitializeComponents()`의 authority 전용 one-shot grant loop.

### P1.2에서 만들지 않는 것

- 새 Component
- `UKhazanAbilitySet` DataAsset과 asset 인스턴스
- granted handle 배열과 remove/regrant API
- `UKhazanGameplayAbility` base
- BasicAttack Ability class 또는 Blueprint
- Ability level/scaling field
- duplicate lookup map, readiness tag, init state machine
- Input pressed/released, Controller binding, combo buffer

P1.2의 배열은 비어 있어도 유효하다. P1.3에서 실제 BasicAttack class가 생긴 뒤 첫 entry를 작성한다. 검증만을 위해 null entry나 임시 Ability를 만들지 않는다.


<a id="p1-3-basic-attack-spec-20260915"></a>
## 2026-09-15 — P1.2 Source/build 대조와 P1.3 진입

- 사용자가 P1.2 Definition schema와 authority one-shot grant loop를 적용했다. 실제 Source는 v2.4 계약과 일치한다.
- 2026-09-15 19:36 UE 5.8.2 UBT에서 UHT, Definition/Character compile, module/DLL link, metadata와 `Result: Succeeded`를 확인했다. 새 PIE/runtime 기록은 아직 없어 asset property와 이동 회귀는 누적 검증 대기다.
- 현재 `KhazanCharacter.cpp`의 미사용 `ParticleHelper.h` include는 P1.3 전 제거한다. 다른 P1.2 코드는 되돌리지 않는다.
- P1.3은 직접 `UGameplayAbility`를 상속한 `UKhazanBasicAttackAbility` 두 Source 파일, `InstancedPerActor`, 표준 Commit/End와 관측 log만 만든다. 공통 Ability base, Component, AbilitySet, tag, montage, 비용, hit, buffer는 만들지 않는다.
- cold build 뒤 기존 CharacterDefinition의 첫 entry에 native BasicAttack class와 `Input.Action.Attack`을 지정한다. 이 단계의 완료 기준은 ASC에 inactive BasicAttack `FGameplayAbilitySpec` 한 개가 존재하는 것이다. activation은 P1.4에서 검증한다.
- 상세 구현과 Spec/grant/instance/activation/revoke 용어 계약은 [P1 최소 실습판 P1.3](CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-2-applied-p1-3-basic-attack-spec-20260915)을 따른다.
