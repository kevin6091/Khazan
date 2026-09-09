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
