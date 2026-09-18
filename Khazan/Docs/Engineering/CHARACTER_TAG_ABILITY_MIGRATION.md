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


## 2026-09-16 — P1.3 Source/build 확인과 P1.4 진입

- 사용자가 `UKhazanBasicAttackAbility` Source와 기존 CharacterDefinition의 첫 grant entry를 적용했다. Ability는 `InstancedPerActor`, 표준 Commit, 성공 log, 즉시 normal End라는 P1.3 계약과 일치한다.
- Definition asset의 직렬화 데이터에서 `InitialAbilityGrants`, native `KhazanBasicAttackAbility`, `Input.Action.Attack`을 확인했다. 2026-09-16 UE 5.8.2 cold build는 `Target is up to date`, `Result: Succeeded`다.
- 최신 PIE log에는 AbilitySystem debug 명령과 정상 종료가 있으나 HUD의 Spec 행 자체는 저장되지 않는다. BasicAttack Spec 정확히 한 개와 이동 회귀는 사용자의 화면 확인이 남아 있다.
- 다음 공동 구현은 P1.4다. `KhazanPlayerController.cpp`의 Attack binding을 `ETriggerEvent::Started`로 바꾸고 빈 `Input_Attack()`이 현재 `AKhazanCharacter`의 `UKhazanAbilitySystemComponent`에 `Input.Action.Attack`을 전달한다.
- P1.4 Source는 아직 제안 상태이며 직접 적용하지 않았다. Montage, Locomotion constraint, pressed/released, cost, hit, combo는 P1.4 범위가 아니다.
- 상세한 파일별 코드, 각 줄의 책임, build/PIE 합격 기준과 실패 진단은 [P1 최소 실습판 P1.4](CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-4-attack-input-activation-20260916)를 따른다.

## 2026-09-16 — P1.4 Source 확인과 P1.5 진입

- 사용자가 `KhazanPlayerController.cpp`에 Attack `Started -> UKhazanAbilitySystemComponent::TryActivateAbilitiesByInputTag(Input.Action.Attack)` 연결을 적용했다. 같은 편집에서 Jump도 `Started`로 바뀌었으며 P1.6 전까지 직접 `Character::Jump()` 경로는 보존한다.
- 2026-09-16 UE 5.8.2 cold build는 `Target is up to date`, `Result: Succeeded`다. 사용자는 구현 완료를 보고했지만 이 기록 작성자가 새 PIE의 press/log 횟수와 locomotion 회귀 화면을 다시 캡처하지는 않았다.
- 다음 checkpoint는 P1.5다. native BasicAttack이 `PlayMontageAndWait` task, 발급 Component weak pointer, 실행별 `FKhazanMovementConstraintHandle`을 소유하고 모든 정상/중단/취소 종료를 `EndAbility()` cleanup으로 모은다.
- P1 후보 Sequence와 Player/ABP는 같은 `SK_Khazan` skeleton이다. 다만 후보와 같은 폴더의 8개 Sequence가 모두 `10.375 s`라서 전체 길이를 원작 단일 공격 지속시간으로 사용하지 않는다. 사용자가 Montage segment의 실제 표현 구간을 시각 확인해야 한다.
- P1 구조 시험 제약은 `MaxAllowedGait=Run`, rotation override off다. Run은 원작 확인값이 아니라 Sprint intent 보존과 handle 해제를 관찰하기 위한 임시 튜닝값이다.
- P1.5는 hit, damage, stamina, cooldown, combo, root-motion 이동을 만들지 않는다. 상세 Source, asset 설정, console cancel과 합격 기준은 [P1 최소 실습판 P1.5](CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-4-applied-p1-5-montage-constraint-20260916)를 따른다.

## 2026-09-16 — P1.5 원작 Dilation 통합 보정

- 원작 `WeakAtk01`은 source AnimSequence의 `RateScale`을 구간별로 바꾸지 않는다. `FastAtk01_M1` segment `0–3.53 s`, `AnimPlayRate=1.0`, `LoopingCount=1` 위에 213-point Dilation table을 적용해 실제 재생 길이를 `3.4326434 s`로 만든다.
- 앞 절의 현재 10.375초 uasset에서 눈으로 segment를 자르는 절차는 최종안이 아니다. P1.5 앞에 **P1.5-0 원작 시간축 playback Sequence bake**를 둔다. 저장 table의 역함수로 source pose를 재표본화하고 Sequence/Montage/task를 모두 `1.0x`로 실행한다.
- UE Montage Time Stretch Curve에 원작 raw Dilation key를 그대로 복사하거나 Ability Tick에서 `Montage_SetPlayRate()`를 갱신하지 않는다. 두 방식은 원작 저장 table과 다른 계약 또는 새 runtime 상태를 만들기 때문이다.
- P1.5 Ability 책임은 그대로다. `PlayMontageAndWait`가 실행 수명을 소유하고 BasicAttack instance가 정확한 movement constraint handle 하나를 정상/중단/취소/EndPlay 공통 `EndAbility()`에서 반환한다. `KhazanCharacter`, ASC, Controller, Main AnimInstance에는 곡선 재생 상태를 추가하지 않는다.
- source metadata의 root motion/force root lock은 확인됐지만 P1.5는 CMC 구동 범위이므로 root-motion 이동을 활성화하지 않는다. notify 45개의 의미와 시간 변환은 hit/cancel/combo 소비가 생기는 P3/P6로 넘긴다.
- Art 근거와 전 수치 표는 [DAS 애니메이션 시간축 검사 §7](../Art/DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md#7-2026-09-16--weakatk01-구간별-재생-속도-표적-확인), 실제 사용자 적용 순서는 [P1 최소 실습판의 최신 P1.5 보정](CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-5-dilation-integrated-20260916)을 따른다.

<a id="p1-5-root-motion-combo-aware-20260916"></a>
## 2026-09-16 — P1.5 Root Motion 필수 및 콤보 선행 계약 정정

- 사용자 확정 방침에 따라 위 절의 `P1.5는 root-motion 이동을 활성화하지 않는다`는 범위를 폐기한다. P1.5 playback Sequence는 Dilation 재표본화에 `Root` 트랙을 포함하고 `Enable Root Motion=true`로 만든다. Main ABP의 `Root Motion from Montages Only`, Montage/task play rate `1.0`, task `AnimRootMotionTranslationScale=1.0`을 함께 검증한다.
- 원작 `SB_Kazan_DualAxeSword_Com_WeakAtk`의 표준 단계는 `WeakAtk01 → WeakAtk02 → WeakAtk03 → WeakAtk04`다. `Step4`는 `SP_Kazan_DualAxeSword_Flow_HyperMaster`가 활성일 때 같은 `WeakAtk04`를 쓰는 특수 `Step5`로 치환되고, 그 단계의 press가 `Step6=WeakAtk05`로 연결된다.
- 따라서 원작 표준 1–5타 source는 `FastAtk01_M1`, `FastAtk02_M1`, `FastAtk03_M1`, `FastAtk04_M1`, `Com_WeakAtk05`다. `FastAtk02_Loop`는 별도 `WeakAtk02_Loop` Composite의 source이고 표준 Skill Blueprint 단계에서 참조되지 않으므로 2타 정본으로 사용하지 않는다.
- 자산 구조는 단발 `AM_DAS_BasicAttack01` 대신 하나의 `AM_DAS_WeakAttackCombo`와 `Attack01`–`Attack05` section을 목표로 한다. P1.5에서는 `Attack01`만 넣거나 활성화해 Root Motion/수명 수직 절편을 먼저 통과시키며, 자동 다음 section link는 `None`이다. P6가 입력 전달, 지역 buffer/window, section 예약과 5타 해금 판정을 추가한다.
- ASC에는 Dilation curve, Montage position, combo index, unlock bool을 넣지 않는다. ASC는 P6에서 active Spec에도 engine pressed event를 전달하는 일반 adapter만 확장하고, 활성 BasicAttack Ability가 combo 상태와 cleanup을 소유한다.
- 상세 사용자 적용 순서는 [P1 최소 실습판의 최신 Root Motion·콤보 보정](CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-5-root-motion-combo-correction-20260916)을 따른다. 이번 기록은 설계·원본 대조이며 게임 Source/asset 적용, build, PIE 완료가 아니다.
- 이번 보정은 문서와 저장 report 작성만 완료했다. playback Sequence/Montage/Ability Source의 적용, cold build, PIE 검증은 아직 완료하지 않았다.

<a id="p1-weak-attack-rename-20260916"></a>
## 2026-09-16 — P1 용어 이관: BasicAttack → WeakAttack

- 원작 `WeakAtk01`–`WeakAtk05` 콤보와 현재 P1의 `BasicAttack`이 같은 행동임을 확인했으므로 최신 용어를 `WeakAttack`으로 확정했다. 과거 단계 기록은 보존하지만 이후 구현에서는 `BasicAttack` 이름을 새로 만들지 않는다.
- 실제 C++ class와 파일을 `UKhazanWeakAttackAbility`, `KhazanWeakAttackAbility.h`, `KhazanWeakAttackAbility.cpp`로 변경했다. 현재 P1.3 동작인 `CommitAbility()` 후 즉시 `EndAbility()`는 명칭 변경 범위에서 유지했다.
- Standalone 싱글 플레이 계약을 분명히 하기 위해 class constructor에 `NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly`를 명시했다. Character의 authority-only `GiveAbility()`와 `Input.Action.Attack` → Spec activation 경로는 유지한다.
- `Config/DefaultEngine.ini`에 `/Script/Khazan.KhazanBasicAttackAbility` → `/Script/Khazan.KhazanWeakAttackAbility` class redirect를 추가했다. 현재 `DA_CharacterDefinition_Khazan`에 저장된 옛 native class path는 다음 Editor load에서 redirect되어야 하며, 새 class로 표시되는지 확인한 뒤 asset을 저장한다.
- 아직 실제 `GA_BasicAttack_Khazan` asset은 없으므로 binary asset rename은 수행하지 않았다. P1.5에서 처음 만들 이름은 `GA_WeakAttack_Khazan`이고 Montage는 이미 확정한 `AM_DAS_WeakAttackCombo`다.
- 다음 순서는 새 이름으로 cold build → Definition asset load/save와 grant class 확인 → P1.5-0 `A_DAS_WeakAtk01_Playback` 생성 → P1.5 Montage/Ability 수명 구현이다. 이번 변경에는 build, Editor asset resave, PIE 검증을 포함하지 않았다.

## 2026-09-16 — P1.5 최신 진입 계약: Root Motion·Montage task만 연결

- P1.5는 `A_DAS_WeakAtk01_Playback` 생성, `AM_DAS_WeakAttackCombo`의 `Attack01` section 생성, `UKhazanWeakAttackAbility`의 `PlayMontageAndWait` 수명 연결, `GA_WeakAttack_Khazan`과 기존 Definition grant 교체, cold build·PIE 검증 순서로 진행한다.
- 앞 절의 임시 `MaxAllowedGait=Run` movement constraint는 제거한다. 원작 공격 제약이 확인되지 않은 상태에서 handle cleanup만을 위한 runtime 상태를 제품 구현에 넣지 않는다. 공격 이동은 root track→Montage→AnimInstance→CMC 경로를 사용한다.
- UE 5.8 task 호출은 `bStopWhenAbilityEnds=true`, `AnimRootMotionTranslationScale=1.0`, `bAllowInterruptAfterBlendOut=true`다. 정상 Blend Out에는 Ability를 끝내지 않고 `OnCompleted`, `OnInterrupted`, `OnCancelled`만 종료 경로에 연결한다.
- 원작 `Step1.AnimBlendAlpha=0.1`은 직접 확인됐지만 UE Montage Blend In/Out과 동일한 단위·소비 의미인지는 미확인이다. 원작 Composite의 `RigRotToTarget.StartBlendTime/EndBlendTime`은 손 타깃 보정 값이므로 Montage 값으로 사용하지 않는다.
- 현재 native rename 뒤 cold build와 Definition resave도 아직 확인되지 않았다. 따라서 P1.5 에셋 생성 전에 rename 안정화 checkpoint를 먼저 통과한다.

## 2026-09-17 — P1.5 시작 경로 적용 확인과 코드 정리 경계

- 실제 Source의 `UKhazanWeakAttackAbility`에는 `PlayMontageAndWait` 생성, `Attack01` 시작, 완료·중단·취소 종료, `bStopWhenAbilityEnds=true`, `bAllowInterruptAfterBlendOut=true`가 적용돼 있다.
- 사용자는 좌클릭 PIE에서 Montage 재생을 확인했다. `Saved/Logs/Khazan.log`의 반복된 `started ... at section Attack01` 기록도 시작 경로를 뒷받침한다. P1.5 전체 checkpoint 중 cancel·interrupt·cleanup 행렬은 아직 별도 확인이 필요하다.
- 별도 Montage interface/static utility는 만들지 않는다. 엔진 AbilityTask가 이미 Ability 수명과 결합된 재생 추상화이며, 현재 프로젝트에서 별도 구현체나 공유 정책 소비자가 확인되지 않았다.
- 가독성 개선은 먼저 Ability 내부 private 함수 추출과 중복 callback 통합으로 제한한다. P3/P6에서 Montage+GameplayEvent 정책이 여러 공격 Ability에 반복될 때 game-specific AbilityTask의 실제 소비자와 계약을 확인한 뒤 공통화한다.
- 이 기록은 설계 판단과 실제 상태 갱신이며 이번 설명 작업에서 Source/BP/asset은 수정하지 않았다.

## 2026-09-17 — P1.5 종료 gate와 P6 콤보 선행 계약 보정

### 순서 보정

기존 P6의 “단일 후속 입력 → 선형 combo → 확인된 branching” 방향은 유지한다. 다만 원작에서 `SkillM01`, `SkillM02`, `Pressed`, `Released`, charge step과 혼합 입력이 직접 확인됐으므로 단일 `Input.Action.Attack/Started`를 P6까지 유지하는 전제는 폐기한다. 다음 구현 순서는 아래와 같다.

| Checkpoint | 실제 범위 | 완료 조건 |
|---|---|---|
| P1.5-E | 현재 Montage Ability의 정상 완료·강제 cancel·다른 Montage interrupt·Blend Out 뒤 interrupt·PIE 재진입 cleanup | 모든 경로에서 Ability inactive, task/Montage 종료, 다음 실행 정상, granted Spec 한 개 유지 |
| P1.6-A | `WeakAttack/StrongAttack` 의미 입력과 `Started/Completed/Canceled`, ASC의 active Spec generic press/release protocol | inactive press는 정확히 한 Spec 활성화, active re-press/release는 GAS input task에 정확히 한 번 전달, cancel 뒤 `InputPressed=false` |
| P6-A | Weak `Attack01→Attack02` 한 edge, 원작 시간축 window, Ability-local buffer 한 건 | 창 전 입력은 한 건만 보관되고 합법 창에서만 2타 연결, 무입력 시 1타 종료, interrupt cleanup |
| P6-B | Weak `02→03→04`, 확인된 unlock 뒤 `04→05` | 해금 전후 edge가 정확히 달라지고 Root Motion/section 종료가 안정적 |
| P6-C | 별도 Strong Ability의 press→Start/Charge→release/step | Right press 즉시 시작, Completed release와 Canceled가 구분되고 원작 charge window가 playback 시간축에서 재현됨 |
| P6-D | `Weak→Strong`, `Strong→Weak`의 metadata로 확인된 branch만 추가 | 입력 tag가 payload로 보존되고 현재 Ability만 window/buffer를 소유하며 전역 queue와 generic/typed 이중 소비가 없음. 대상 활성화 성공 전 현재 실행을 먼저 종료하지 않음 |
| P6-E | 여러 공격에서 반복된 montage+event 수집 계약 평가 | 반복이 확인될 때만 game-specific `PlayMontageAndWaitForEvent` AbilityTask 추출 |

기존 P1.6 Jump 전환은 삭제하지 않고 `P1.6-J`로 식별해 P1.6-A 뒤에 둔다. 공격 입력 contract를 먼저 바로잡아야 이후 Jump와 다른 입력도 같은 pressed/released engine protocol을 재사용할 수 있다.

### 수치와 자산 gate

- 실제 `AM_DAS_WeakAtkCombo`는 현재 `Attack01`만 가진다. P6-A에서 `DAS_Khazan_WeakAtk02`를 Montage 뒤에 추가하고 `Attack02` section을 생성하기 전에는 combo runtime 코드를 완료로 보지 않는다. section의 자동 `Next Section`은 둘 다 `None`으로 두고 Ability가 합법 입력일 때만 `CurrentMontageSetNextSectionName(Attack01, Attack02)`를 호출한다.
- WeakAtk01의 metadata-mapped input-progression 후보는 playback `0.2929789424–0.5131536622 s`와 `0.5165015501–0.9242099718 s`다. 별도 `ReserveInput`은 playback `0.2205535080–0.4756474282 s`, `0.3825092135–0.6388580379 s`, `1.0419576641–1.1919575 s`다. P6-A의 01→02 edge에는 progression과 겹치는 앞 두 reservation 후보만 우선 연결한다. 늦은 후보는 `Index7` input-check→`Step1` same-step 경로와 연관되므로 별도 restart/repeat 의미가 확인될 때까지 01→02 buffer에서 제외한다. reservation/capture와 progression/consume은 서로 겹칠 수 있는 두 지역 window로 모델링하고 하나의 임의 combo bool이나 합쳐진 시간 구간으로 축약하지 않는다. proprietary begin/end 부작용은 아직 추론임을 유지한다.

## 2026-09-17 — P1.6/P6 입력 parser와 연타 큐 보정

- UE 5.8에서 `UInputTriggerCombo`와 관련 step/cancel struct가 deprecated임을 로컬 엔진 source와 validation code로 확인했다. P1.6-A와 P6의 기반으로 사용하지 않는다.
- P1.6-A는 `IA_WeakAttack`/`IA_StrongAttack`의 평범한 Digital 입력과 Started/Completed/Canceled 전달만 구현한다. Hold 시간 누적, Chorded Action, Combo Trigger, 전역 queue를 이 단계에 추가하지 않는다.
- P6-A의 Weak 01→02는 활성 `UKhazanWeakAttackAbility` 안의 node-local 한 slot으로 검증한다. reservation이 열린 동안 최초 합법 press 하나만 보관하고, advance에서 재검증해 성공한 경우에만 소비한다. 추가 연타는 미래 node용 FIFO로 누적하지 않는다.
- P6-B는 실제 section 진입 뒤 slot과 input wait를 재arm하는 방식으로 02→03→04와 해금 05를 확장한다. 한 번의 난타가 남은 모든 section을 자동 예약하지 않는지 확인한다.
- P6-C의 Strong hold는 activation 직후 `WaitInputRelease`를 시작한다. 반환 `TimeHeld`는 관측값이며 charge step은 원작 Notify/event window가 결정한다. Canceled는 pressed cleanup과 공격 취소를 수행하며 정상 Completed release와 구별한다.
- P6-D에서 Weak↔Strong의 실제 branch가 두 개 이상 확인되면 read-only Combo Definition을 추출한다. matching과 runtime buffer는 active Ability에 남기고 DataAsset에는 node/edge 정적 사실만 둔다.
- 대칭적인 약+강 동시 입력이 원작 branch로 확인되지 않은 현재에는 Chorded Action asset을 만들지 않는다. 미래에 확인되면 선행 action의 기존 activation을 억제할 수 있는지와 입력 순서 허용 범위를 먼저 검증한다.
- Strong Start release는 playback `0.1992338551–0.24999997 s`, Charge release/step 후보는 playback `0–1.1780140925 s`, `0.0001–0.6000966776 s`, `0.6000589403–1.1781134007 s`다. 이 값들은 `PlaybackEvents.json`의 원작 Dilation 변환값이며 새 튜닝값이 아니다. 실제 Strong montage를 만들 때 사용 segment와 branch 연결을 다시 대조한다.
- 공격 입력 buffer에 임의 `0.2 s` 같은 만료 timer를 넣지 않는다. 현재 node의 원작 window와 Ability 종료/section 전환이 buffer 수명을 결정한다.

### 검증 행렬

- Weak: `L`, `LL`, `LLL`, 창 직전/안/직후 press, mash, 입력 없이 종료.
- Strong: `R tap`, `R hold`, 정상 release, input mapping 취소, montage interrupt 중 release.
- 혼합: `L→R`, `LL→R`, `R→L`, 확인되지 않은 조합 거절, unlock 전후 edge.
- 공통: Root Motion capsule 이동과 충돌, Montage 교체, cancel, 사망/EndPlay, 다음 PIE, stale held/window/buffer 부재, ASC에 granted Spec은 남고 active instance만 종료되는지 확인.

이번 보정은 Architecture/Migration 절차 갱신이다. 게임 Source, InputAction, MappingContext, Blueprint, Montage는 수정하지 않았고 build·PIE도 실행하지 않았다.

## 2026-09-17 — P1.6-A 적용 감사와 P6-A 실제 진입점

- 실제 Source에는 `Input.Action.WeakAttack/StrongAttack`, ASC `AbilityInputTagPressed/Released`, Controller의 양 입력 `Started/Completed/Canceled`가 반영됐다. `IA_WeakAttack`, `IA_StrongAttack`, `IMC_Default`, `DA_InputData`, CharacterDefinition도 새 공격 태그와 에셋을 직렬화한다. 최신 UBT는 `Result: Succeeded`이며 PIE 로그에는 `GA_Player_WeakAttack_C`의 `Attack01` 시작이 반복 기록됐다.
- P1.6-A 종료 전에 두 회귀를 보정한다. `Input_WeakAttackCanceled()`가 현재 `AbilityInputTagPressed()`를 호출하므로 `Released()`로 고친다. `DA_InputData`에는 `Input.Action.Jump → /Game/Input/Locomotion/IA_Jump` 항목이 빠져 최신 PIE에 lookup error가 있으므로 기존 Jump 항목을 복구한다.
- ASC press 쪽도 release와 대칭으로 null `AbilitySpec.Ability`를 거르고 `Abilities/GameplayAbility.h`를 직접 include한다. 새 Weak/Strong InputAction lookup은 null을 확인한 뒤 bind해 DataAsset 오류가 null binding으로 이어지지 않게 한다.
- 현재 Montage binary에는 `Attack01`과 `DAS_Khazan_WeakAtk01`만 있고 `DAS_Khazan_WeakAtk02` asset은 별도로 존재한다. P6-A presentation 단계에서 같은 Slot 뒤에 2타를 추가하고 `Attack02` section을 정확히 segment 시작에 둔다. 두 section의 authored Next는 `None`이다.
- native window event tag 네 개와 begin/end event만 전달하는 `UKhazanAnimNotifyState_GameplayEventWindow`를 먼저 build한다. Montage에는 원작 Dilation 변환값으로 reservation 둘과 advance 둘을 Branching Point 상태로 배치한다. 겹치는 reservation은 Ability의 depth counter로 처리한다.
- 그 뒤 `UKhazanWeakAttackAbility`가 네 window event를 계속 대기하고 `WaitInputPress(false)`를 node-local 한 번씩 arm한다. reservation 입력은 한 건만 보관하고 advance begin 또는 advance 안 press에서 현재 Montage/section을 재검증해 `Attack01→Attack02`를 확정한다. 무입력은 Attack01에서 정상 종료하고, 확정 뒤 추가 난타는 Attack03용으로 보존하지 않는다.
- 이 기록은 사용자 적용 상태의 정적/로그 감사와 다음 공동 구현 절차다. 이번 설명 작업에서 게임 Source/BP/Input/Montage를 직접 변경하거나 새 build/PIE를 실행하지 않았다.

## 2026-09-17 — P6-A window 전달 방식 재검토와 Jump 정정

- 사용자가 `Input.Action.Jump` row는 시험용이어서 의도적으로 삭제했다고 확인했다. 앞 절의 `DA_InputData` Jump row 복구 요구는 취소한다. native Jump tag까지 제거할지는 별도 dead-code 정리 범위이며 P6-A의 선행 조건이 아니다.
- P6-A의 전역 window Gameplay Event tag 네 개, custom `KhazanAnimNotifyState_GameplayEventWindow`, `WaitGameplayEvent` listener 네 개 제안은 현재 범위에서 철회한다. UE 5.8 내장 `Montage Notify Window` 두 이름과 활성 WeakAttack Ability의 `OnPlayMontageNotifyBegin/End` bind가 동일한 정보를 더 적은 타입과 전역 식별자로 전달한다.
- reservation/advance 의미와 원작 playback 시간, 겹침을 위한 depth counter, 한 건 buffer, `WaitInputPress(false)`, Ability의 section 확정 책임은 바뀌지 않는다. 단순화한 것은 Montage에서 Ability로 window edge를 운반하는 방법뿐이다.
- Gameplay Event는 이후 Weak 실행 중 Strong 입력처럼 ASC 경계를 통해 의미 tag/payload를 전달할 실제 소비자가 생길 때 사용한다. montage notify 수집 패턴이 여러 Ability에 반복될 때만 custom AbilityTask 공통화를 다시 판정한다.
- 현재 `AM_DAS_WeakAtkCombo`는 Attack01 section/segment 한 개와 notify 0개임을 read-only 확인했다. Attack02 section을 추가하면 UE가 이전 section을 자동 연결하므로 Montage Sections에서 그 authored link를 반드시 지운 뒤 저장한다.

## 2026-09-17 — P6-A 제품 구조 보정: 한 edge 구현과 전체 콤보 계약을 분리

- P6-A는 asset과 검증 범위만 `Attack01→Attack02` 한 edge다. runtime API까지 `Attack02` 전용으로 만들지 않는다. 활성 WeakAttack Ability는 현재 montage section, reservation/advance depth, `FGameplayTag BufferedInputTag` 한 칸, transition-committed 사실만 소유한다.
- own Weak 재입력은 buffer에 `Input.Action.WeakAttack`을 기록한다. invalid tag가 빈 slot이다. 이후 Weak↔Strong branch를 연결할 때도 같은 slot에 의미 tag를 넣으므로 bool buffer를 tag로 교체하는 마이그레이션을 다시 하지 않는다.
- Ability 내부의 `TryCommitBufferedTransition()` 한 함수가 현재 section과 입력 tag에서 합법한 다음 section을 고르고 현재 montage instance에 연결한다. 첫 구현의 합법 규칙은 `Attack01 + Weak → Attack02` 하나이며, P6-B/D에서 metadata로 확인된 규칙만 같은 함수에 추가한다. 규칙 조회를 다른 실제 소비자가 공유하기 전에는 별도 resolver나 table로 분리하지 않는다.
- 내장 Montage Notify Window와 AnimInstance delegate 사용, Ability-local cleanup, 얇은 ASC 계약은 유지한다. Combo DataAsset, generic graph runtime, input buffer component, custom notify class와 custom AbilityTask는 이 단계에 추가하지 않는다.

## 2026-09-17 — P6-A 재감사: 빌드 오류 분리와 콤보 구현 축소안

- Rider/UBT 전체 빌드는 활성 Live Coding mutex 때문에 C++ compile 전에 `Unable to build while Live Coding is active`로 중단됐다. 에디터를 닫지 않고 UBT `-SingleFile` Live Coding pass-through로 다시 검사한 결과 `KhazanWeakAttackAbility.cpp`는 `Result: Succeeded`였다.
- 같은 방식으로 변경 번역 단위를 검사했을 때 `KhazanPlayerController.cpp:30`에서 `ULocalPlayer` 불완전 형식 오류가 재현됐다. `Engine/LocalPlayer.h` 직접 include가 빠진 것이 실제 compile 실패 원인이다. `KhazanAbilitySystemComponent.cpp`는 compile됐지만 `FGameplayAbilitySpec::ActivationInfo` 두 사용이 UE 5.8 deprecation warning이다.
- 현행 WeakAttack은 header 76줄, cpp 439줄이며 한 edge를 위해 두 NotifyState의 Begin/End, 두 depth counter, Montage instance ID와 section별 하드코딩 분기를 가진다. 이 형태를 5타로 복사 확장하지 않는다.
- 다음 사용자 적용 순서는 `(1)` PlayerController cpp에 `Engine/LocalPlayer.h`를 직접 include해 build blocker 제거, `(2)` WeakAttack의 두 NotifyState 계약을 `ComboInputOpen`/`ComboCommit` 점 Notify로 교체, `(3)` mutable state를 current step·한 칸 tag buffer·input-open 사실로 축소, `(4)` section 이름 배열과 한 개의 `TryAdvanceCombo()`로 1–5타 일반화, `(5)` 4→5에서만 확정된 progression tag 확인, `(6)` cold build와 PIE 검증이다.
- 실제 pose cross-fade는 `MontageSetNextSectionName()`이 제공하지 않는다. 따라서 조기 Commit에서 현재 task를 닫고 같은 Montage를 다음 section부터 다시 재생하는 ARCH-41 방식은 유지하되, 점 Notify 계약으로 이전 instance의 늦은 window End가 없어지므로 instance ID 필터와 depth 상태는 제거한다.
- 이 감사에서는 Source와 Montage를 수정하지 않았다. Single-file compile만 수행했으며 full link, cold build, PIE는 아직 검증되지 않았다.

## 2026-09-17 — P6 브랜치 컷 최종 재검토: 단일 Montage task와 고정 Commit Jump

이 절은 Architecture `ARCH-43`의 실행 순서다. 앞 절의 “다음 타수마다 task를 닫고 같은 Montage를 다시 재생한다”는 기본안을 대체한다. 회수부를 가진 전체 시퀀스, unlinked section, 한 Ability가 전체 Weak chain을 소유하는 계약은 유지한다.

### 1. 먼저 현재 빌드 실패를 콤보 구조와 분리한다

`KhazanPlayerController.cpp`에 `#include "Engine/LocalPlayer.h"`가 빠진 compile 오류를 먼저 고친다. Live Coding을 종료한 cold build가 이 수정으로 통과하는지 확인한 뒤 WeakAttack을 변경한다. 현행 `KhazanWeakAttackAbility.cpp` 자체는 single-file compile을 통과했으므로 콤보 설계를 빌드 오류의 원인으로 오인하지 않는다.

### 2. Montage를 최종 1–5타 형태로 구성한다

1. 같은 Slot track에 `DAS_Khazan_WeakAtk01`–`DAS_Khazan_WeakAtk05` 전체 시퀀스를 순서대로 둔다. 각 segment에서 회수부를 자르지 않는다.
2. 각 segment 시작에 `Attack01`–`Attack05` section을 둔다. 새 section 추가 때 UE가 이전 section을 자동 연결할 수 있으므로 Montage Sections 패널에서 다섯 section의 `Next Section`을 모두 `None`으로 다시 확인한다.
3. `Attack01`–`Attack04`에는 내장 `Montage Notify` point `ComboInputOpen`과 `ComboCommit`을 한 쌍씩 둔다. `Attack05` 뒤에 확인된 Weak 후속 분기가 없으므로 이 두 Notify를 관성적으로 추가하지 않는다.
4. Open은 플레이어의 다음 입력을 보관하기 시작할 수 있는 지점, Commit은 실제 pose/root-motion을 자를 단 하나의 지점이다. Attack01의 원작 playback 구간들은 배치 후보 근거일 뿐 확정 point가 아니다. 원작 영상과 PIE를 프레임 단위로 비교해 각 타수의 cut을 정한다.
5. 두 Notify의 Montage Tick Type은 gameplay 분기에 사용하는 정밀 이벤트이므로 `Branching Point`로 둔다. custom `ANS_ComboWindow`, `State.Combo.CanAdvance`, window Gameplay Event tag는 만들지 않는다.

내장 `Montage Notify Window` 하나의 Begin을 Open, End를 Commit으로 쓰는 안도 최종 기본안에서는 제외한다. UE는 정상적으로 window 끝을 통과할 때뿐 아니라 Montage가 중단돼 active state를 정리할 때에도 `NotifyEnd`를 호출한다. 그러면 cancel 도중의 End와 authored Commit을 구분하는 분기가 다시 필요하다. 두 point는 같은 타임라인 범위를 표현하면서 그 종료 예외를 만들지 않는다.

### 3. `UKhazanWeakAttackAbility`를 한 task 구조로 축소한다

header에는 Montage asset, 현재 task, delegate cleanup용 AnimInstance weak reference, `CurrentComboStepIndex`, `BufferedInputTag`, `bAcceptingComboInput`만 runtime 상태로 남긴다. section 이름 다섯 개는 cpp의 고정 배열로 둔다.

다음 항목은 제거 대상이다.

- `CurrentSectionName`
- `ActiveMontageInstanceID`
- `InputReservationDepth`
- `ComboAdvanceDepth`
- `HandleMontageNotifyEnd()`
- `IsNotifyFromActiveMontage()`가 보관한 instance-ID 상태
- section 전환마다 `ActiveMontageTask->EndTask()` 후 새 task를 만드는 코드
- `Attack01 + Weak → Attack02`만 적은 하드코딩 분기

남길 함수 계약은 작게 유지한다.

| 함수 | 책임 |
|---|---|
| `StartWeakAttackMontage()` | `Attack01`에서 `PlayMontageAndWait`를 정확히 한 번 시작하고 완료·중단 callback을 연결한다. |
| `SubmitComboInput(InputTag)` | 입력 허용 중이고 slot이 비었을 때 현재 타수용 입력 한 건만 저장한다. |
| `HandleMontageNotifyBegin(Name, Payload)` | 이 Montage의 `ComboInputOpen`이면 입력을 열고, `ComboCommit`이면 입력을 닫은 뒤 `TryAdvanceCombo()`를 한 번 호출한다. |
| `TryAdvanceCombo()` | current step·input tag·target section·5타 해금을 검사하고 성공 시 step 상태를 reset한 뒤 `MontageJumpToSection()`을 호출한다. |
| `ResetComboState()` | activation/종료 경계에서 index, buffer, 입력 허용 사실을 초기화한다. |
| `FinishAbility(bCancelled)` | task 완료·중단을 기존 `EndAbility()` cleanup 한 곳으로 모은다. |

`MontageJumpToSection()`은 `UGameplayAbility`가 제공하는 함수를 사용한다. 이 함수는 현재 Ability가 ASC의 animating ability인지 확인한 뒤 ASC의 Montage 명령으로 전달한다. `AnimInstance->Montage_JumpToSection()`을 직접 호출할 필요가 없다.

### 4. 입력과 전환 순서를 고정한다

1. activation 성공 시 `CurrentComboStepIndex=0`, 빈 buffer, 입력 닫힘으로 시작하고 task를 `Attack01`에서 한 번 재생한다.
2. 현재 section의 `ComboInputOpen`이 오면 `bAcceptingComboInput=true`로 바꾼다.
3. 그 뒤 들어온 첫 Weak press만 `BufferedInputTag`에 저장한다. 같은 타수의 추가 mash는 버린다.
4. `ComboCommit`이 오면 먼저 입력을 닫고 buffer를 지역 값으로 옮긴 뒤 member slot을 비운다. 입력이 없거나 현재 node에 그 tag의 edge가 없으면 Jump하지 않는다.
5. 합법 edge이면 다음 section이 실제로 존재하는지 확인한다. `Attack04→Attack05`에서는 확정된 progression 투영을 검사한다. 잠겨 있으면 Jump하지 않는다.
6. 성공할 때만 index를 다음 값으로 갱신하고 `MontageJumpToSection(NextSectionName)`을 호출한다. 다음 타수의 `ComboInputOpen` 전까지 입력은 닫힌 상태다.
7. 입력이 없거나 검증이 실패하면 현재 section의 회수부를 끝까지 재생한다. authored Next가 `None`이므로 task `OnCompleted`가 발생하고 Ability가 정상 종료된다.

이 방식은 연타 전체를 FIFO에 쌓지 않는다. 한 타수에 입력 한 건만 소비하고 Jump 뒤 slot을 비우므로, `LLLLL`을 매우 빠르게 눌렀다고 미래 네 타수가 미리 예약되지 않는다. 다음 타수의 Open 이후에 다시 누른 입력만 그 타수의 후보가 된다. 이후 Weak→Strong 분기가 확인되면 같은 slot에 Strong input tag를 넣고 `TryAdvanceCombo()`의 확인된 edge만 추가한다. 그때도 별도 Combo Manager나 DataAsset을 자동으로 만들지 않는다.

### 5. Jump 품질 gate를 코드 완료 조건에 포함한다

UE 5.8.2의 `JumpToSectionName()`은 재생 위치만 바꾸며 Montage Blend In을 재적용하지 않는다. 따라서 아래 검증이 통과해야 단일-task 브랜치 컷을 확정 적용한 것으로 본다.

- Attack01→02, 02→03, 03→04, 해금 후 04→05를 각각 같은 authored Commit에서 여러 번 전환해 출발 pose가 매번 같은지 확인한다.
- 전환 직전/직후 capsule 위치·yaw·frame root delta를 기록해 timeline 위치 차이를 Actor 이동으로 잘못 누적하지 않는지 확인한다.
- 상체 손·무기, 골반, 양발 pose가 한 프레임 튀는지 원작 영상과 나란히 비교한다.
- 입력 없음에서는 각 타수의 회수와 정자세 복귀가 끝까지 보이고 다음 section이 자동 재생되지 않는지 확인한다.
- Open 직전 입력, Open–Commit 사이 첫 입력, 같은 구간 mash, Commit 직후 입력, Montage interrupt, Ability cancel을 각각 시험한다.
- 5타 잠금 중에는 4타 회수가 정상 완료되고, 해금 투영 후에만 같은 입력으로 5타에 진입하는지 확인한다.

Jump에서 pose/root-motion 불연속이 실제로 남으면 cut 위치와 다음 segment 시작 pose를 먼저 재조정한다. 호환되는 authored cut을 찾을 수 없을 때에만 task 재생 cross-fade나 별도 transition 표현을 다시 비교한다. 실패 대비용 두 번째 전환 경로를 production 코드에 동시에 남기지 않는다.

### 적용 상태

이번 절은 구조 재검토와 문서 갱신이다. 현재 `KhazanWeakAttackAbility.h/.cpp`의 두 window depth, Montage instance ID, task 재생 코드는 아직 그대로이며 Source·Montage·Blueprint를 수정하거나 cold build·PIE를 실행하지 않았다.

<a id="p6-native-inertialization-v3-20260917"></a>
## 2026-09-17 — P6 v3: 단일-task Jump + 코드 요청 관성화

이 절은 바로 위 P6 브랜치 컷 절에 관성화 검증 결과와 전체 아키텍처 v3의 적용 순서를 합친 최신 실행 기준이다. Architecture의 [v3 절](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v3-native-minimal-20260917)이 책임 정본이며, 이 절은 사용자가 실제로 이관할 순서다.

### 검수 결론

- `MontageJumpToSection()`은 같은 Montage instance의 재생 위치를 바꾸며 Montage Blend In/Out을 다시 시작하지 않는다.
- Inertialization은 이 hard position change에서 생기는 skeletal pose offset을 완화하는 유효한 UE 기능이다.
- 다만 UE 5.8.2 설치본에는 `PlayRequestInertialization` 또는 `Request Inertialization`이라는 내장 AnimNotify가 확인되지 않았다.
- section 첫 frame Branching Point는 Jump가 이미 그 위치에 놓인 뒤 다음 검색에서 시작 위치와 같아 건너뛸 수 있다. 따라서 첫 frame Notify는 전환 request의 안정적인 owner가 아니다.
- `ComboCommit`을 소비한 Ability가 `RequestMontageInertialization()`을 호출하고 바로 `MontageJumpToSection()`을 호출한다.
- 관성화는 Montage root-motion extraction 또는 CMC capsule delta를 교차 보간하지 않는다. Root Motion 품질 검증은 별도 gate다.

### P6-0 — 빌드와 dead abstraction 정리

1. `KhazanPlayerController.cpp`에 `Engine/LocalPlayer.h`를 직접 include하고 cold build로 현재 blocker를 제거한다.
2. ASC 입력 함수는 active `InstancedPerActor` primary instance의 current activation info를 사용한다. deprecated `FGameplayAbilitySpec::ActivationInfo` fallback을 제품 경로에서 제거한다.
3. 공통 동작이 없는 `UKhazanGameplayAbility`를 제거하고 WeakAttack이 `UGameplayAbility`를 직접 상속한다. Blueprint parent와 redirect가 있으면 먼저 reference를 확인한다.
4. 이 단계에서는 combo 기능을 바꾸지 않는다. build 오류와 architecture 변경을 한 commit/checkpoint에 섞지 않는다.

### P6-1 — Montage authored contract

1. 한 Slot track에 `DAS_Khazan_WeakAtk01`–`05` 전체 recovery 포함 시퀀스를 둔다.
2. segment 시작에 `Attack01`–`Attack05` section을 두고 모든 `Next Section`을 `None`으로 둔다.
3. `Attack01`–`Attack04` 각각에 `ComboInputOpen`, `ComboCommit` 내장 Montage Notify point를 둔다. 두 point 모두 Montage Tick Type은 `Branching Point`다.
4. `Attack05` 뒤 확인된 Weak branch가 없으면 관성적으로 Open/Commit을 추가하지 않는다.
5. 다음 section 첫 frame에는 관성화용 Notify를 추가하지 않는다.
6. Open/Commit 실제 시각은 저장된 metadata 후보, 원작 영상, pose/root delta 비교로 타수별 확정한다. 과거 후보 숫자를 그대로 복사해 완료로 판단하지 않는다.

### P6-2 — AnimGraph 한 노드 이동

현재 정본은 `GroundedLocomotion → Inertialization → Grounded Output`, 상위 출력 뒤 `DefaultSlot → Output`이다. 공격 Slot request를 받기 위해 아래로 바꾼다.

```text
Locomotion State Machine
  → DefaultSlot
  → Inertialization
  → Output Pose
```

- 기존 노드를 이동하고 같은 공간의 두 번째 노드는 만들지 않는다.
- 향후 IK/Control Rig가 있으면 Inertialization은 그 앞에 둔다.
- 변경 뒤 locomotion state transition도 이 최종 노드가 request를 받는지 ABP Debugger와 Animation Insights로 회귀 검사한다.
- Message Log에 missing inertialization requester 오류가 없어야 한다.

### P6-3 — WeakAttack 상태 축소

남길 runtime state는 다섯 개다.

```text
CurrentComboStepIndex
BufferedInputTag
bAcceptingComboInput
ActiveMontageTask
BoundAnimInstance
```

제거 대상은 `CurrentSectionName`, `ActiveMontageInstanceID`, `InputReservationDepth`, `ComboAdvanceDepth`, Notify End handler, instance-ID filter, section별 task replay다. section 이름은 cpp의 정적 배열이며 runtime mutable state가 아니다.

`ActivateAbility()`는 모든 필수 owner와 `Attack01`을 검증하고 Commit 뒤 `PlayMontageAndWait`를 정확히 한 번 시작한다. 한 타수에서 다음 타수로 갈 때 task를 닫거나 다시 만들지 않는다.

### P6-4 — Commit에서 request와 Jump를 한 함수로 묶는다

전환 함수는 다음 조건을 순서대로 검사한다.

1. Ability가 active인가.
2. Commit을 보낸 payload의 `SequenceAsset`이 `WeakAttackMontage`인가.
3. `CurrentComboStepIndex`가 다음 section을 가질 수 있는가.
4. buffer에 현재 node의 합법 semantic input이 있는가.
5. ASC의 current Montage가 이 Montage이고 animating ability가 현재 Ability인가.
6. target section이 실제 Montage에 존재하는가.
7. 4→5라면 실제 progression 투영 tag가 존재하는가.

성공 직전에 먼저 `bAcceptingComboInput=false`, buffer clear, step index 갱신을 수행한다. 그 다음 같은 Game Thread 호출 안에서 다음 두 명령을 실행한다.

```cpp
AnimInstance->RequestMontageInertialization(
    WeakAttackMontage,
    ComboSectionInertializationDuration,
    nullptr);

MontageJumpToSection(NextSectionName);
```

`ComboSectionInertializationDuration`은 `EditDefaultsOnly`인 하나의 presentation tuning으로 둔다. 최초 후보 `0.1 s`는 원작 Step `AnimBlendAlpha=0.1`을 UE duration으로 대응한 프로젝트 매핑 후보라고 주석과 문서에 표시한다. 원작 직접 초 값으로 표현하지 않는다. `0.15 s`나 타수별 배열, BlendProfile은 관측 근거 없이 추가하지 않는다.

### P6-5 — 입력 정책

- `ComboInputOpen` 전 입력은 버리지 않고 보관하는 정책으로 오해하지 않는다. 현재 정책은 Open 뒤 첫 입력만 받는다.
- 같은 node에서 여러 번 누르면 첫 합법 입력 한 건만 유지한다.
- Commit 뒤 다음 section의 Open 전 입력은 미래 node로 이월하지 않는다.
- 입력 없음, edge 없음, 잠금, 현재 Montage 불일치는 Jump하지 않고 현재 recovery를 끝까지 재생한다.
- Strong branch의 실제 소비가 생기기 전에는 추가 event tag/listener를 만들지 않는다. 생기면 current Weak Ability로 Strong semantic event 한 건을 전달하되 buffer와 Commit owner는 그대로 유지한다.

### P6-6 — 품질 검증 행렬

| 분류 | 확인 항목 |
|---|---|
| task 수명 | activation당 Montage task 한 개, section jump 뒤 같은 task 유지, 마지막 unlinked section 완료에서 Ability 정상 종료 |
| 입력 | 무입력, Open 직전, Open~Commit 첫 press, mash, Commit 직후, 각 타수 재입력, 4→5 잠금/해금 |
| pose | 손·무기·골반·양발의 pop, blend 중 overshoot, 짧은 blend의 원작 실루엣 유지 |
| root motion | Commit 전/전환/다음 frame capsule translation·yaw delta, 벽·경사·적 충돌, CMC movement mode |
| cleanup | Montage interrupt, Ability cancel, 사망, Pawn EndPlay, PIE 재진입 뒤 buffer/delegate/task 잔류 없음 |
| locomotion | Idle/WalkRun/Sprint/Stop 전환이 이동한 최종 Inertialization node에서도 정상, Sync Marker/Stop foot 회귀 없음 |
| 진단 | Animation Insights의 Montage section/Notify/pose track, Message Log inertialization error 없음 |

pose가 개선돼도 capsule root delta가 튀면 실패다. 먼저 Commit과 다음 sequence 시작 범위를 조정한다. 그 방법으로 해결되지 않는 edge가 실제로 확인될 때만 transition clip 또는 별도 montage-instance cross-fade를 그 edge의 단일 대안으로 채택한다.

### P6 이후 아키텍처 정리 순서

1. PlayerController 공격 callback을 tag payload 기반 Started/Completed/Canceled 세 함수로 축소한다.
2. 장치 dead zone은 Enhanced Input modifier로 옮기고 Player의 수동 dead zone 필드를 제거한다.
3. Anim snapshot 미사용 필드와 `bShouldPlayStart`, 빈 Tick/BeginPlay를 reference audit 뒤 제거한다.
4. Character/InputData의 직접 asset reference 이관을 별도 checkpoint로 진행하고 custom AssetManager/AssetData/GameInstance 초기화를 제거한다.
5. 첫 실제 hit에서 Ability/Task 지역 trace로 수직 검증한다. 둘 이상의 실제 공격이 공유할 상태와 API가 확인될 때만 Combat capability를 추출한다.
6. 첫 Monster AI에서 StateTree plugin/module을 추가하고 StateTree Task가 PathFollowing 또는 ASC Ability를 요청·대기하도록 한다. Player action state를 StateTree에 복제하지 않는다.

### 적용 상태

이번 절은 문서 정본 개정이다. Source, Config, Blueprint, Montage, AnimSequence, DataAsset을 수정하지 않았고 cold build/PIE도 수행하지 않았다. 사용자가 현재 구현을 이관할 때는 P6-0부터 checkpoint별로 적용하고, 각 단계가 통과하기 전 다음 구조를 선행 생성하지 않는다.

<a id="p6-v3-1-current-checkpoint-20260918"></a>
## 2026-09-18 — P6-v3.1 실제 현재 상태와 01→02 적용 체크포인트

### 실제 확인값

- 저장된 `/Game/_Art/Kazan/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAtkCombo`는 `DefaultSlot`, `RateScale=1.0`, section `Attack01` 하나, `DAS_Khazan_WeakAtk01` segment 하나, Notify 0개다. Blend In/Out은 각각 `0.1 s`, `Hermite Cubic`이다.
- 저장된 `DAS_Khazan_WeakAtk01`과 `02`는 각각 `3.4333333969 s`, `3.3333332539 s`이며 둘 다 `RateScale=1.0`, `EnableRootMotion=true`, `ForceRootLock=true`, Root Lock `RefPose`다.
- `GA_Player_WeakAttack` CDO는 위 Montage를 참조하며 `InstancedPerActor`, `ServerOnly`다.
- 현행 Source는 `Attack02` section과 `InputReservation`/`ComboAdvance` window가 존재한다고 가정하므로 Content와 불일치한다. 현재 상태에서 PIE 콤보 검증을 시작하지 않는다.
- 일반 증분 Development Editor build는 2026-09-18 성공했지만 Controller object를 재컴파일하지 않았다. `KhazanPlayerController.cpp` 강제 single-file compile은 `ULocalPlayer` 불완전 타입으로 C2027/C2059/C2143 실패했다. `KhazanAbilitySystemComponent.cpp` single-file compile은 성공했지만 deprecated `AbilitySpec.ActivationInfo` 경고 두 건이 재현됐다.
- `/Game/Bluprints/Abilities/GA_GamePlayAbility`가 `UKhazanGameplayAbility`를 직접 부모로 참조한다. package referencer는 확인되지 않았지만 이 asset을 정리하기 전 native base를 삭제하지 않는다. 빈 base 제거는 이번 combo checkpoint와 분리한다.

### 이번 체크포인트 범위

1. Controller에 `Engine/LocalPlayer.h`를 직접 include하고 ASC가 active `InstancedPerActor` primary instance의 current activation info만 사용하게 고친 뒤 full build를 통과한다.
2. WeakAttack의 기존 Montage 재시작, instance ID, 두 window depth와 Notify End 경로를 제거한다. 한 `PlayMontageAndWait`, `CurrentComboStepIndex`, 한 칸 `BufferedInputTag`, `bAcceptingComboInput`, Begin delegate만 남긴다.
3. Montage에 `DAS_Khazan_WeakAtk02`와 `Attack02`를 추가하고 두 section의 authored Next를 `None`으로 둔다. Attack01에는 `ComboInputOpen`, `ComboCommit` Montage Notify point 두 개만 둔다.
4. Main ABP의 기존 Inertialization node를 `DefaultSlot` downstream으로 이동한다. Root Motion mode와 각 Sequence의 Root Motion 설정은 유지한다.
5. `ComboCommit`에서 `RequestMontageInertialization()`을 요청한 직후 Ability의 `MontageJumpToSection()`을 호출한다. task를 종료하거나 새로 만들지 않는다.
6. 첫 완료 gate는 01→02만 대상으로 한다. 03–05, Weak↔Strong event, hit trace, Controller generic callback, AssetManager 정리는 이 gate에 섞지 않는다.

### 수치 지위

- 최초 `ComboInputOpen` 관측 후보 `0.2205535080 s`는 저장된 원작 `ReserveInput` 시작값이다.
- 최초 `ComboCommit` 관측 후보 `0.3825092135 s`는 원작 구간 경계이면서 프로젝트 root-track 파생 비교에서 Attack01 root 속도 약 `328.62 asset-unit/s`가 Attack02 시작 약 `335.36 asset-unit/s`와 가까웠던 시각이다. 원작의 직접 branch 명령 시각으로 확인된 값은 아니다.
- 관성화 duration `0.1 s`는 원작 `AnimBlendAlpha=0.1`을 UE duration으로 대응한 프로젝트 매핑 후보다. 세 값 모두 기능 배선 완료값과 제품 품질 확정값을 구분하고 원작 영상·PIE pose/capsule 검증으로 조정한다.

### 완료 gate

- 한 번 누르면 Attack01 recovery까지 재생하고 종료한다.
- Open–Commit 사이 두 번째 Weak 입력 한 건만 저장되고 Commit에서 Attack02로 이동한다.
- 난타가 미래 타수를 예약하지 않으며 Jump 뒤 같은 AbilityTask가 유지된다.
- `DefaultSlot` 관성화 request 누락 오류가 없고 pose pop과 capsule translation/yaw를 별도로 검사한다.
- Idle/Walk/Run/Sprint/Stop과 Sync Marker에 회귀가 없다.

이번 절은 read-only asset inspection, single-file compile 진단과 구현 설명 정리다. Source와 Content asset은 수정하지 않았으며 PIE는 수행하지 않았다.

<a id="p6-v3-1-attack02-blocker-20260918"></a>
## 2026-09-18 — P6-v3.1 01→02 전환 차단 원인과 최소 보정

### 재현된 원인

- 사용자 적용 후 `Attack01`은 재생되지만 반복 Weak 입력에도 `Attack02`로 이동하지 않는 증상이 보고됐다.
- 현행 `ResetRuntimeState()`와 헤더 기본값은 `CurrentComboStepIndex=INDEX_NONE(-1)`으로 만든다. 반면 `Attack01` 재생 성공 시 이를 `Attack01Index(0)`으로 설정하는 문장이 없다. 저장소 전체 검색에서도 해당 멤버 대입은 transition 성공 시의 `CurrentComboStepIndex = NextComboStepIndex`와 reset의 `INDEX_NONE`뿐이었다.
- 따라서 `ComboInputOpen` 뒤 두 번째 Weak press가 들어오면 `SubmitComboInput()`은 `NextComboStepIndex = -1 + 1 = 0`을 계산하고 Weak tag를 buffer에 저장할 수 있다. 그러나 `ComboCommit`에서 `TryCommitBufferedTransition()`은 현재 index `-1`에 대해 `IsValidComboStepIndex(CurrentComboStepIndex)`가 false가 되어 반드시 반환한다. `MontageJumpToSection()`에는 도달하지 않는다.
- 이 결함은 Commit 시각과 무관하다. `ComboCommit` point를 뒤로 옮겨도 현재 index가 계속 `-1`이므로 결과는 변하지 않는다.

### 최소 보정 계약

- 첫 Montage task의 delegate를 연결한 뒤 `ReadyForActivation()`을 호출하기 전에 `CurrentComboStepIndex = Attack01Index`를 한 번 설정한다. 그러면 첫 Open 구간의 입력은 `NextComboStepIndex=1`, 즉 `Attack02`를 예약하고 Commit에서 0→1 전환을 수행한다.
- task가 즉시 실패하거나 Ability가 종료되면 기존 `FinishAbility()`/`EndAbility()`/`ResetRuntimeState()`가 index를 다시 `INDEX_NONE`으로 정리하므로 별도 bool이나 Manager는 추가하지 않는다.
- index는 "현재 실행 중인 combo node"의 소유 상태다. 활성화 전·종료 후에는 `INDEX_NONE`, 첫 타 재생을 시작할 때 `0`, 실제 Jump를 확정할 때만 다음 값으로 바뀐다.

```cpp
ActiveMontageTask = Task;

Task->OnCompleted.AddDynamic(this, &ThisClass::HandleMontageCompleted);
Task->OnInterrupted.AddDynamic(this, &ThisClass::HandleMontageAborted);
Task->OnCancelled.AddDynamic(this, &ThisClass::HandleMontageAborted);

CurrentComboStepIndex = KhazanWeakAttackAbilityPrivate::Attack01Index;
Task->ReadyForActivation();
```

### 저장 asset read-only 대조

- `AM_DAS_WeakAtkCombo`는 길이 `6.766666889 s`, section `Attack01`/`Attack02`, `DefaultSlot` segment 두 개를 가진다. 두 번째 segment는 `3.433333397 s`에서 시작한다.
- `ComboInputOpen`은 `0.220553502 s`, `ComboCommit`은 `1.237220883 s`에 있으며 둘 다 duration `0`인 `AnimNotify_PlayMontageNotify` point다. 이름은 Source 계약과 정확히 일치한다.
- 두 point의 저장된 Montage Tick Type은 현재 `Queued`다. 이는 이번 `INDEX_NONE` 차단 원인은 아니지만 P6 authored contract의 `Branching Point`와 불일치하므로 최소 코드 보정 뒤 둘 다 `Branching Point`로 바꾸고 같은 프레임에서 다시 검증한다.

### 검증 상태와 다음 gate

- 결론은 정적 제어 흐름과 저장 asset read-only inspection으로 확정했다. 원인이 코드에서 결정적으로 드러나므로 debugger attach는 수행하지 않았다.
- 이번 점검에서 게임 Source와 Content asset은 수정하지 않았고 build/PIE도 수행하지 않았다. 사용자가 위 한 줄과 Tick Type을 적용한 뒤 cold build하고 `L`, `LL`, Open 전 입력, Open–Commit 입력, Commit 뒤 입력을 구분해 PIE로 검증한다.

<a id="p6-v3-2-three-phase-input-recovery-exit-20260918"></a>
## 2026-09-18 — P6-v3.2 3상태 입력과 회수부 이동 전환

### 현재 확인값

- 사용자 보정 후 01→02 section Jump는 PIE에서 동작한다.
- 디스크 저장 Montage의 현재 point는 `ComboInputOpen=0.220553502 s`, `ComboCommit=0.529886901 s`이며 둘 다 duration 0의 `AnimNotify_PlayMontageNotify`, Tick Type `Queued`다. `ComboInputEnd`는 아직 없다.
- WeakAttack Ability/Blueprint에는 `Block.Movement.Input`이나 다른 활성/차단/cancel tag가 없다. `ABP_Player`는 `Root Motion from Montages Only`다.
- CMC는 Anim Root Motion이 있는 동안 일반 속도 계산을 건너뛰고 Anim Root Motion velocity를 적용한다. Attack02 후 이동이 montage 종료까지 보이지 않는 현상은 현재 Root Motion을 조기 종료할 recovery handoff가 없기 때문이다.

### P6-v3.2-A — 콤보 창을 세 point로 교체

1. `Attack01`에 `ComboInputEnd` Montage Notify point를 추가해 `Open < Commit < End < section end` 순서를 만든다.
2. 세 point의 Montage Tick Type을 모두 `Branching Point`로 바꾼다.
3. Source에 `ComboInputEndNotifyName`과 `bComboCommitReached` 한 개만 추가한다.
4. Open에서 buffer clear, accepting=true, commitReached=false로 만든다.
5. Commit에서 accepting을 닫지 않는다. buffer가 있으면 즉시 기존 transition 함수를 호출하고, 없으면 commitReached=true로 바꾼다.
6. Commit 뒤 입력은 buffer에 기록한 직후 기존 transition 함수를 호출한다.
7. End에서 accepting=false, commitReached=false, buffer clear를 수행한다.
8. transition 시작과 `ResetRuntimeState()`에서도 두 bool과 buffer를 닫는다.

`ComboInputEnd`의 최종 시각은 임의 숫자로 확정하지 않는다. 원작 progression/reservation metadata와 영상, Commit–End 각 출발 frame의 pose 및 capsule root delta를 대조해 마지막 합법 frame을 정한다.

### P6-v3.2-B — Attack02 recovery에서 locomotion으로 조기 복귀

1. Attack01/Attack02의 실제 회수부에 `RecoveryCancelOpen` point를 둔다. 이 point는 combo End와 별도 계약이다.
2. point에 도달했을 때 `LocomotionComponent`의 현재 raw `MoveInputWorld`가 유효하면 WeakAttack을 조기 종료한다.
3. point 뒤 새 이동 시작도 잡기 위해 Move `Started`를 semantic gameplay event 한 건으로 전달하고 활성 WeakAttack이 엔진 `WaitGameplayEvent` task로 기다린다.
4. recovery가 열리기 전의 event는 별도 bool queue로 저장하지 않는다. 계속 누르고 있으면 Locomotion raw intent가 point에서 잡고, 이미 놓았다면 취소 요청도 사라진 것으로 본다.
5. 조기 종료 시 Montage를 직접 두 번 정지하지 않는다. `EndAbility()`가 task를 끝내고 `PlayMontageAndWait`의 `bStopWhenAbilityEnds=true`가 GAS current montage를 Blend Out한다.
6. 먼저 현재 Montage Blend Out만 사용해 pose/root/movement 반응을 검사한다. Blend Out과 Inertialization을 동시에 기본 적용하지 않는다. 실제 pop 또는 입력 복귀 지연이 확인되면 그 증거로 하나의 전환 방식을 다시 선택한다.

### 외부 Ability 전환 경계

- 이동 복귀와 달리 Dodge/Strong/Skill은 대상 Ability가 있다. 입력을 받은 출발 Ability가 recovery cancel 시점에 대상 활성화를 시도하고 성공한 뒤에만 자신을 끝낸다.
- 같은 Slot Group에서 새 Montage가 시작되면 UE가 이전 Montage를 interrupt하고 각 Montage Blend 설정을 사용한다. 출발 Montage를 먼저 Stop한 다음 대상 활성화를 시도하는 순서는 사용하지 않는다.
- 실제 Strong/Dodge Ability가 생기기 전에는 범용 ActionTransitionManager, cancel graph, 공통 base helper를 만들지 않는다. 두 번째 실소비자에서 반복되는 최소 코드를 확인한 뒤 현재 빈 `UKhazanGameplayAbility` base 활용 여부를 결정한다.

### 완료 gate

- Open–Commit 입력은 Commit에서 Jump한다.
- Commit–End 입력은 입력 프레임에 즉시 Jump한다.
- End 이후 입력은 다음 타수를 예약하지 않는다.
- mash는 타수마다 한 건만 소비하며 다음 section Open 전 입력을 이월하지 않는다.
- Attack02 recovery 중 이동을 계속 누른 경우 `RecoveryCancelOpen`에서 Montage가 조기 종료되고 locomotion으로 전환한다.
- point 뒤 새로 누른 이동도 즉시 조기 종료한다.
- 이동 입력 없이 두면 full recovery와 정상 `OnCompleted`가 유지된다.
- 조기 Blend Out 동안 capsule 위치/yaw, 벽 충돌, 발 미끄러짐과 locomotion pose pop을 검사한다.

이번 절은 구조 검토와 read-only 확인 결과다. Source, Blueprint, Montage를 직접 수정하거나 build/PIE하지 않았다.

<a id="p6-v33-edge-move-exit-20260918"></a>
## 2026-09-18 — P6 v3.3: ComboInputEnd 이후 Move Started로 공격 종료

### 이번 체크포인트의 정확한 동작

`ComboInputEnd` 전의 이동 입력은 저장하지 않는다. End가 열린 다음에 새로 발생한 `IA_Move Started`만 활성 WeakAttack을 취소한다. End 전에 방향키나 스틱을 누르고 계속 유지해도 자동 취소하지 않으며, End 이후 새 Started를 만들기 위해 입력을 놓고 다시 눌러야 한다.

### 구현 순서

1. `KhazanGameplayTags.h/.cpp`에 native event tag `Event.Input.MoveStarted`를 선언·정의한다.
2. `KhazanPlayerController::SetupInputComponent()`에서 기존 Move `Triggered`, `Completed`, `Canceled` binding을 유지하고 `Started` binding 하나를 추가한다.
3. 새 `Input_MoveStarted` callback은 현재 Pawn의 Khazan ASC에 `FGameplayEventData`를 채워 `HandleGameplayEvent(Event.Input.MoveStarted, ...)`를 호출한다. 공격 Ability를 cast하거나 montage를 직접 정지하지 않는다.
4. `UKhazanWeakAttackAbility::ActivateAbility()`가 commit에 성공한 뒤 `UAbilityTask_WaitGameplayEvent`를 한 번 만들고, exact tag·반복 수신으로 활성화한다. 별도 task 멤버는 만들지 않으며 Ability 종료 시 task의 `OnDestroy()` cleanup을 사용한다.
5. WeakAttack에 runtime bool `bCanCancelToLocomotion` 하나와 event callback 하나를 추가한다. 초기화·activation·section jump에서는 false, `ComboInputEnd` 처리에서는 true다.
6. event callback은 Ability 활성 여부와 bool만 검사한다. false면 기록 없이 return하고, true면 기존 `FinishAbility(true)` 경로를 사용한다.
7. `PlayMontageAndWait`의 `bStopWhenAbilityEnds=true`를 유지한다. 직접 `Montage_Stop()`을 중복 호출하지 않는다. 종료 시 엔진 task가 ASC가 소유한 현재 Montage인지 확인하고 asset Blend Out으로 정지한다.
8. 별도 `RecoveryCancelOpen`, movement buffer, Tick polling, current raw-intent 조회, Controller의 WeakAttack cast는 추가하지 않는다.

### 검증 행렬

- End 전 Move Started: 공격 지속, 나중에 자동 종료되지 않음.
- End 전 이동 입력을 계속 유지: End 통과만으로 종료되지 않음.
- End 뒤 새 Move Started: 같은 프레임에 Ability 종료와 Montage Blend Out 시작.
- End 뒤 Move Started가 없을 때: section recovery를 끝까지 재생하고 `OnCompleted`로 정상 종료.
- Open~Commit Weak 입력: Commit에서 다음 section으로 jump.
- Commit~End Weak 입력: 입력 프레임에 다음 section으로 jump.
- ComboInputEnd 뒤 Weak 입력: 현재 section에 예약되지 않음.
- Attack01→02 jump 직후: 이동 취소 gate가 false로 재설정되어 다음 section의 End 이전에는 이동으로 끊기지 않음.
- 이동 취소 뒤: Montage Root Motion이 종료되고 locomotion 입력이 다시 capsule을 구동함. asset Blend Out 동안 지연이 보이면 먼저 Blend Out과 root-motion trace를 측정한다.

### 공통화 gate

이번 단계에서는 WeakAttack 내부에 최소 상태를 둔다. 두 번째 실제 combo Ability를 시작할 때 코드 복사보다 먼저 dedicated `UKhazanComboGameplayAbility`를 추출한다. Interface, Jump-only utility, notify 자동 생성기, custom combo task는 현재 checkpoint에서 만들지 않는다. 추출 시에는 선형 Weak 전용 규칙을 base에 고정하지 않고 입력 tag/hold/unlock/branch 해석을 파생 Ability의 transition resolver로 남긴다.

### 적용 상태

사용자가 `ComboInputEnd`를 처리했다고 보고했으며, 이번 기록에서는 그 asset을 직접 재검증하거나 Source를 수정하지 않았다. 위 tag·Controller event·WaitGameplayEvent·gate 코드는 다음 공동 구현 대상이고, 적용 후 cold build와 PIE 검증 결과를 이 문서에 추가한다.

### IA_Move read-only 확인

저장 `IA_Move`는 Axis2D이며 asset 자체의 Modifier/Trigger 배열은 비어 있다. `IMC_Default`의 현재 Move mapping에는 `InputModifierSwizzleAxis`만 있고 별도 Trigger나 Dead Zone은 없다. 현재 디지털 키 테스트에는 이 구성이 blocker가 아니지만, 이후 analog stick을 연결하면 작은 축 노이즈가 Move `Started` 의미가 되지 않도록 Enhanced Input mapping의 Dead Zone에서 먼저 정규화한다. Controller나 Ability에 별도 임계 숫자를 중복 하드코딩하지 않는다.

확인은 UE 5.8 Python commandlet의 read-only asset 조회로 수행했다. 조회 스크립트는 완료됐지만 commandlet 종료 시 프로젝트의 기존 `GameFeatureData` class load ensure가 함께 보고되어 전체 commandlet 성공으로 기록하지 않는다. 임시 조회 파일은 삭제했다.

### 2026-09-18 — P6 v3.3 payload 정정

위 구현 순서 1·3의 별도 `Event.Input.MoveStarted` 추가 및 actor metadata 채움은 현재 구현에 필요하지 않다. 현행 `Input.Action.Move`를 Move `Started` binding에서 전달하고, 송신 코드는 빈 non-null `FGameplayEventData`만 만든다. `Instigator`, `Target`, `Payload.EventTag`는 현재 수신 callback이 소비하지 않으므로 설정하지 않는다. 수신 ASC는 `HandleGameplayEvent()`를 호출한 인스턴스로 이미 정해지며, null payload는 엔진의 gameplay-event task/activation 경로가 허용하지 않으므로 사용하지 않는다.

### 2026-09-18 — P6 v3.4 현재 WeakAttack → Locomotion 보간 경로 확인

저장 에셋과 Source를 read-only로 확인한 결과, 현재 `AM_DAS_WeakAtkCombo`에서 locomotion으로 돌아가는 보간은 Montage의 **Standard Blend Out**이 담당한다.

- Montage: Blend Out `0.1 s`, `Hermite Cubic`, Blend Mode Out `Standard`, Blend Profile Out `None`, Blend Out Trigger Time `-1.0`, Enable Auto Blend Out `true`.
- `ABP_Player`: Root Motion Mode는 `Root Motion from Montages Only`. Main AnimGraph에는 Locomotion State Machine, `DefaultSlot`, `Inertialization`, Output이 순서대로 배치되어 있고 Slot의 `Always Update Source Pose`는 false다.
- 자연 종료: 다음 section link가 없는 section의 남은 시간이 기본 Blend Out 시간 안으로 들어오면 엔진이 0.1초 Standard Blend Out을 시작한다. Slot의 Montage weight가 내려가며 source인 locomotion pose 비중이 올라가고, 완전 종료 뒤 `OnCompleted`가 Ability를 끝낸다.
- Move Started 조기 종료: `HandleMoveInputStarted()` → `FinishAbility(true)` → `EndAbility()` 뒤 `PlayMontageAndWait(bStopWhenAbilityEnds=true)`의 task cleanup이 `ASC::CurrentMontageStop()`을 호출한다. override 시간이 없으므로 같은 asset Blend Out `0.1 s`를 사용한다.
- 현재 locomotion 복귀에는 `RequestMontageInertialization()`을 호출하지 않으며 Montage의 Blend Mode Out도 `Standard`다. AnimGraph의 Inertialization 노드는 요청이 없으면 이 종료 보간을 대신 수행하지 않는다. `ComboSectionInertializationDuration=0.08 s` 요청은 타수 간 section jump에만 사용된다.
- Root Motion은 Montage blend-out weight와 함께 감쇠되므로 조기 종료 프레임에 즉시 완전히 사라지는 계약이 아니다. 0.1초 동안의 capsule 이동·입력 체감은 pose Blend Out과 별도로 PIE trace로 확인해야 한다.

UE 5.8.2 Python 조회 스크립트 자체는 완료됐으나 commandlet 종료 코드는 프로젝트의 기존 `GameFeatureData` class-load ensure 때문에 1이었다. 조회용 임시 파일은 삭제했으며 게임 Source와 Content asset은 수정하지 않았다.

<a id="p6-v35-five-step-contract-audit-20260918"></a>
## 2026-09-18 — P6 v3.5: Attack05 추가 뒤 5단 콤보 계약 점검

### 저장 상태 read-only 확인

- `AM_DAS_WeakAtkCombo`의 `DefaultSlot`에는 `DAS_Khazan_WeakAtk01`부터 `DAS_Khazan_WeakAtk05`까지 다섯 segment가 순서대로 저장돼 있다. 모든 segment의 Play Rate는 `1.0`이며, 다섯 Animation Sequence 모두 Enable Root Motion과 Force Root Lock이 켜져 있다.
- 그러나 저장된 Montage Section은 `Attack01`부터 `Attack04`까지 네 개뿐이다. 다섯 번째 sequence가 track에 있어도 `Attack05` section이 없으면 `GetSectionIndex("Attack05")`가 실패하므로 4→5 전이는 불가능하다.
- Attack01~04에는 각각 `ComboInputOpen`, `ComboCommit`, `ComboInputEnd` point가 있고 Attack05에는 `ComboInputEnd`만 있다. 다음 Weak node가 없는 Attack05에 Open/Commit을 두지 않는 현재 구성은 맞다.
- 확인된 13개 point의 Montage Tick Type은 모두 `Queued`다. section cut과 입력 소비 경계를 frame-exact gameplay 계약으로 쓸 point이므로 `Branching Point`로 맞추는 것이 현재 설계와 일치한다.
- Montage의 현재 저장 Blend Out은 `0.25 s`, Hermite Cubic, Standard, Blend Profile 없음, Trigger Time `-1.0`, Auto Blend Out 활성이다. 이 값은 원작 검증값이 아닌 현재 프로젝트 asset 값이며, 앞선 v3.4의 `0.1 s` 기록보다 최신 저장 상태가 우선한다.

### Source에서 발견한 두 불일치

1. `UKhazanWeakAttackAbility::ActivateAbility()`의 section 유효성 조건은 `HasComboSection(1)`을 두 번 호출하고 index `2`, 즉 `Attack03`을 검사하지 않는다. 0~4를 순회하며 최초 누락 section을 찾는 짧은 검증으로 교체한다.
2. `AKhazanPlayerController::SetupInputComponent()`는 `Input_MoveStarted`를 `ETriggerEvent::Triggered`에 연결한다. 합의한 계약이 “End 뒤 새로 발생한 Move Started만 취소하며, End 전에 누르고 유지한 입력은 자동 취소하지 않음”이므로 해당 binding은 `Started`로 고쳐야 한다. 연속 이동 적용을 담당하는 `Input_Move`만 `Triggered`를 유지한다.

### Attack05 해금 경계

- Source에는 이미 `Attack05UnlockTag` 설정과 4→5 직전 `HasMatchingGameplayTag()` 검사가 있다.
- 현재 native tag 사전에는 해당 unlock tag가 없고 `GA_Player_WeakAttack`의 저장 설정도 비어 있다. 따라서 section을 추가해도 05는 의도대로 잠긴 채 남는다.
- 원작 metadata에서 해금 근거는 `SP_Kazan_DualAxeSword_Flow_HyperMaster`다. 프로젝트 semantic tag는 이 원인을 나타내는 `Unlock.Skill.DualAxeSword.HyperMaster`로 정의할 수 있으나, 이는 원작 내부 GameplayTag를 발견한 것이 아니라 원작 skill 사실을 프로젝트 상태 계약으로 투영한 이름이다.
- Ability나 PlayerController가 Save/SkillTree를 직접 읽거나 자기 자신에게 loose tag를 임의 부여하지 않는다. 영속 Progression이 해금 사실을 소유하고 Pawn/ASC 초기화 경계에서 tag 또는 GameplayEffect로 투영한다. 실제 progression producer가 아직 없으므로 우선 locked 1~4 경로를 완료하고, unlocked 5타 검증은 그 producer를 연결하는 별도 checkpoint에서 수행한다.

### 다음 적용 순서

1. Montage에 `Attack05` section을 다섯 번째 segment의 정확한 첫 frame에 snap해 추가하고 모든 section의 default Next를 `None`으로 확인한다.
2. 13개 named point를 `Branching Point`로 바꾸고 Attack01~04의 `Open < Commit < End`, Attack05의 End-only 계약을 확인한다.
3. Ability activation의 필수 section 검사를 0~4 loop로 정리하고, 누락된 section 이름 하나를 명확히 로그한다.
4. Move Started binding을 `Started`로 보정한다.
5. cold build 뒤 unlock tag가 없는 상태에서 `1`, `1→2`, `1→2→3`, `1→2→3→4`, 4타 창의 추가 press를 각각 검증한다. 마지막 입력은 소비되지 않고 Attack04 recovery로 끝나야 한다.
6. 위 base chain과 cleanup이 통과한 뒤 progression projection을 연결하고 4→5 해금 경로를 검증한다.

이번 점검은 Source와 저장 asset의 read-only 대조다. 게임 Source와 Content asset은 직접 수정하지 않았고 build/PIE도 수행하지 않았다. 조회 스크립트는 값을 출력했으나 종료 시 기존 `/Script/GameFeatures.GameFeatureData` class-load ensure가 발생해 commandlet 전체 성공으로 기록하지 않는다. 임시 조회 파일은 삭제했다.
<a id="p6-v36-attack05-gate-audit-20260918"></a>
## 2026-09-18 — P6 v3.6: Attack05 해금 gate 저장본 감사와 다음 단계

### `Attack05UnlockTag = ...`의 정확한 의미

`UKhazanWeakAttackAbility` 생성자의 대입은 Ability CDO/인스턴스가 검사할 **태그 키 값**을 정한다. `UE_DEFINE_GAMEPLAY_TAG`도 태그 문자열을 사전에 등록할 뿐이다. 어느 코드도 이 두 문장만으로 ASC의 owned tag count를 올리지 않는다.

현재 Source의 4→5 경로는 `CanEnterComboStep(4)`에서 다음 세 조건을 모두 요구한다.

1. `Attack05` section이 Montage에 존재한다.
2. `Attack05UnlockTag`가 유효하다.
3. 현재 ActorInfo의 ASC가 `HasMatchingGameplayTag(Attack05UnlockTag)`를 만족한다.

`AKhazanCharacter::PostInitializeComponents()`의 `GiveAbility()`는 WeakAttack Spec을 만들고 `Input.Action.WeakAttack`을 Dynamic Spec Source Tag로 넣을 뿐 `Unlock.Skill.DAS.WeakAttack05`를 부여하지 않는다. 저장된 CharacterDefinition과 프로젝트 Source에서도 이 unlock tag를 부여하는 GameplayEffect/loose-tag 경로는 발견되지 않았다.

### 저장된 Montage와 관측이 충돌할 때의 판별

- 저장된 `AM_DAS_WeakAtkCombo`의 Attack01~05 section은 모두 `NextSectionName=None`이다. 저장본 기준으로 Attack04가 자동으로 Attack05에 이어지지 않는다.
- 출력 로그에 `transitioned WeakAttack Attack04 -> Attack05`가 있다면 Ability의 gate가 실제로 통과한 것이다. 같은 프레임의 `ASC->GetTagCount(Attack05UnlockTag)`를 Cog Gameplay Tags 또는 debugger에서 확인한다. locked 기대값은 0, unlocked는 1 이상이다.
- 위 전환 로그가 없다면 05 진입으로 단정하지 않는다. 직전 Ability가 끝나 새 WeakAttack이 Attack01에서 다시 활성화됐는지 시작 로그를 확인하고, 열린 Montage Editor의 미저장 section link가 있는지 확인한 뒤 저장·Editor 재시작으로 메모리 상태를 제거한다.
- Cog에서 추가한 loose tag, 무한 GameplayEffect, Blueprint construction/runtime 부여가 있었다면 PIE 종료만으로 남는 Editor 디버그 상태와 새 PIE ASC를 구분한다. 불가능해 보이는 결과는 Editor를 완전히 닫고 cold build 뒤 다시 확인한다.

### 해금의 최종 소유자

해금 사실은 향후 Progression/Save가 소유하고 Pawn 초기화 경계에서 현재 캐릭터 ASC로 투영한다. 개발 확인에는 Cog로 loose tag를 추가·제거할 수 있지만, CharacterDefinition의 초기 owned tag로 영구 등록하면 새 캐릭터가 항상 해금되므로 사용하지 않는다. Progression 연결 전에는 locked 1~4 경로를 기준 동작으로 유지한다.

현재 WeakAttack 전용 클래스에서 unlock tag는 변하지 않는 native 계약이므로 `Attack05UnlockTag`를 Blueprint 설정용 `UPROPERTY`로 유지할 실소비자가 없다. 혼동을 줄이려면 해당 멤버와 생성자 대입을 제거하고 `CanEnterComboStep()`에서 `KhazanGameplayTags::Unlock_Skill_DAS_WeakAttack05`를 직접 조회한다. 이는 해금을 부여하거나 gate 결과를 바꾸는 수정이 아니라, 고정된 query key를 불필요하게 데이터화한 한 단계를 제거하는 정리다. 두 번째 실제 combo Ability에서 서로 다른 unlock 규칙이 반복되기 전에는 공통 node/DataAsset으로 추출하지 않는다.

### 다음 구현 순서

1. 위 로그와 tag count로 Attack05 gate를 locked/unlocked 각각 한 번씩 확정한다.
2. Architecture ARCH-47에 따라 RunStop LF/RF와 SprintStop 세 에셋만 Sequence Root Motion으로 표적 이관한다.
3. Stop 루트 모션의 capsule·collision·재입력 취소를 통과한 뒤 WeakAttack의 다음 수직 기능은 Attack01의 실제 hit window와 피해 결과로 진행한다. 두 번째 combo Ability가 생기기 전에는 공통 Combo base/task/manager를 추가하지 않는다.

이번 기록은 Source나 asset을 변경했다는 뜻이 아니다. 저장본 정적 감사 결과와 다음 공동 구현 절차만 확정했다.
