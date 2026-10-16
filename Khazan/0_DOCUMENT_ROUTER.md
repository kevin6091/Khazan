# 작업 문서 라우터

> 모든 새 작업에서 가장 먼저 읽는 유일한 공통 문서다. 이 문서로 도메인을 판정한 뒤 관련 문서만 연다.
> 이 규칙은 기존 문서의 “1–7 전체 선행 확인” 규칙을 대체한다.

## 도메인 판정

| 도메인 | 요청의 결과 목적 | 대표 요청 |
| --- | --- | --- |
| Art / Resource | 원본 게임 리소스를 추출·분석·임포트하거나 시각 에셋과 Level을 복원 | FModel, PSK/PSA, Static/Skeletal Mesh, Texture, Material, VFX/Fog, Terrain, Foliage, 배치 좌표, 노멀·와인딩, Level 재구성 |
| Engineering | 게임 프로젝트의 실행 구조와 동작을 구현·진단 | C++, GameplayTag, AssetManager, GameInstance, PlayerController, 게임플레이 BP, Project Settings, Config, 컴파일·링크 오류, Assert·Crash, 입력, 런타임 피직스·충돌·래그돌 |

- 분류 기준은 수정할 파일의 확장자가 아니라 요청의 최종 목적이다.
- 임포트/Level 복원을 위한 Python·플러그인 수정은 Art다.
- 게임 모듈의 AssetManager가 Data Asset을 못 읽어 Crash 나는 문제는 Engineering이다.
- 메시 임포트 시 collision 생성은 Art, 캐릭터 런타임 collision·physics 동작은 Engineering이다.
- 머티리얼·Level BP는 Art, 게임플레이 로직·GameMode·Controller BP는 Engineering이다.
- 하나의 요청이 두 목적을 명시적으로 포함할 때만 Mixed로 처리한다.

## Art 문서 선택

| 상황 | 읽고 갱신할 문서 |
| --- | --- |
| 모든 Art 작업의 현재 상태 확인 | `Docs/Art/ART_PROJECT_STATE.md` |
| FModel 추출, PSK/PSA, 임포트, 머티리얼·Level 복원 | `Docs/Art/ART_PIPELINE_RULES.md` |
| 기존 조사 수량, metadata/report, 특정 에셋·배치 정보 조회 | `Docs/Art/ART_KNOWLEDGE_INDEX.md` |
| 중단 작업 재개 또는 인수인계 | `Docs/Art/ART_WORK_CONTINUITY.md` |

Art 작업에서는 `Docs/Engineering`을 읽거나 갱신하지 않는다.

## Engineering 문서 선택

| 상황 | 읽고 갱신할 문서 |
| --- | --- |
| 모든 Engineering 작업의 현재 상태 확인 | `Docs/Engineering/ENGINEERING_PROJECT_STATE.md`, `Docs/Engineering/UE5_ENGINEERING_RULES.md` |
| C++ 클래스, Gameplay BP, Config, AssetManager/GameInstance 구조 | `Docs/Engineering/SOURCE_BP_CONFIG_ARCHITECTURE.md` |
| 컴파일·링크 오류, Assert, Crash, 런타임 버그 | `Docs/Engineering/BUILD_RUNTIME_DIAGNOSTICS.md` |
| 피직스, collision, ragdoll, movement physics | `Docs/Engineering/PHYSICS_DIAGNOSTICS.md` |
| 중단 작업 재개 또는 인수인계 | `Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md` |

Engineering 작업에서는 `Docs/Art`를 읽거나 갱신하지 않는다. 런타임 코드가 참조하는 특정 에셋의 존재 여부만 필요하면 Content 전체를 조사하지 말고 Engineering 아키텍처 문서에 기록된 정확한 경로만 표적 확인한다.

## Mixed 요청

1. Art와 Engineering의 결과물을 먼저 나눈다.
2. 각 결과에 필요한 최소 문서만 읽는다.
3. Art 정보는 Art 문서에, 코드/BP/Config/런타임 정보는 Engineering 문서에 각각 기록한다.
4. 한쪽 도메인의 진행 기록에 다른 도메인의 상세 조사 내용을 복사하지 않고 상대 문서 경로만 남긴다.

## 레거시 문서 분류

| 레거시 파일 | 분류 | 사용 규칙 |
| --- | --- | --- |
| `1_PROJECT_STATE.md` | Mixed | 과거 상태 확인이 꼭 필요할 때만 읽고 갱신하지 않음 |
| `2_UE5_RULES.md` | Mixed | 새 Art/Engineering 규칙 문서로 이관됨 |
| `3_ARCHITECTURE.md` | Mixed | 새 도메인 아키텍처/파이프라인 문서로 이관됨 |
| `4_FMODEL_ASSET_RULES.md` | Art | 상세 FModel 네이밍·분할 규칙이 필요할 때만 Art 작업에서 읽음 |
| `5_WORK_CONTINUITY.md` | Mixed | 새 도메인 continuity 문서로 이관됨 |
| `6_SURVEY_KNOWLEDGE_BASE.md` | Art | 상세 HeinMach/Character 조사 인덱스가 필요할 때만 Art 작업에서 읽음 |
| `7_RUNTIME_CRASH_DIAGNOSTICS.md` | Engineering | 초기 DevMap 진단의 과거 기록이며 새 진단 문서가 대체함 |

레거시 문서는 기록 보존용이다. 새 작업 결과는 반드시 새 도메인 문서에만 추가한다.

## 2026-09-02 Animation 라우팅 추가

- Locomotion, AnimInstance, ABP AnimGraph, State Machine, LF/RF 발 위상, Motion Matching, Linked Anim Graph 요청은 먼저 `Docs/Animation/ANIMATION_LOCOMOTION.md`를 읽는다.
- 애니메이션 C++/ABP 동작 수정이면 추가로 `Docs/Engineering/UE5_ENGINEERING_RULES.md`와 `ENGINEERING_PROJECT_STATE.md`만 읽는다.
- FModel에서 애니메이션을 새로 추출·임포트해야 할 때만 `Docs/Art/ART_PIPELINE_RULES.md`를 추가로 읽는다.
- 애니메이션 요청이라는 이유로 HeinMach 환경 조사 문서나 무관한 Art report를 읽거나 갱신하지 않는다.

## 2026-09-08 로코모션 선행 문서 변경

- Locomotion/AnimInstance/ABP 이동 상태, 입력·gait, Stop/Turn/발 동기화 작업은 이 라우터 다음에 **`Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md`**를 먼저 읽는다. 위 2026-09-02의 로코모션 선행 문서 지정은 이 규칙으로 대체한다.
- 새 정본은 현재 구현의 변수/함수 계약, 실제 코드와 마지막 ABP/에셋 관측값, 검증 상태, 모든 Start 제외 정책을 한곳에 정리한다. 그 뒤 요청에 필요한 현재 소스/저장 리포트만 확인한다.
- `ANIMATION_LOCOMOTION.md`, `INGAME_LOCOMOTION_MIGRATION.md`, 단계별 가이드는 과거 기록과 상세 설명이다. 현재 구현 여부는 새 정본 및 실제 파일로 판단하며, 미적용 제안을 구현 완료로 읽지 않는다.
- C++/ABP 작업의 Engineering 규칙/상태 문서와 기존 Art/Engineering 도메인 경계는 유지한다. 로코모션과 무관한 요청에 이 정본 전체 읽기를 요구하지 않는다.
- 로코모션 변경 결과는 새 정본 하단에 날짜별 데이터 계약/적용 여부/검증 범위를 추가한다. 중단된 실행 검사를 재개할 때만 해당 도메인 continuity의 정확한 정리 절차를 추가로 읽는다.

## 2026-09-08 캐릭터 전체 목표 아키텍처 정본과 조회 순서

- 캐릭터/로코모션/액션/피격/AI의 구조 설계, 새 기능 및 리팩터링은 이 라우터 다음에 `Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md`를 읽는다. 목표 구조와 책임 결정은 이 문서가 정본이다.
- 이 절은 앞선 “로코모션 정본을 첫 도메인 문서로 읽기”의 순서를 해당 요청에서 대체한다. 로코모션의 실제 구현/변수/검증 상태는 이어서 `Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md`와 필요한 실제 소스를 확인한다. 목표와 현행은 서로 대체하지 않는다.
- 좁은 버그/함수 작업은 새 설계 정본의 불변식·관련 책임 계약과 현재 구현의 해당 항목을 읽는다. 무관한 모든 단계별 가이드/Art 문서를 추가로 읽지 않는다.
- 기존 `CHARACTER_ARCHITECTURE_REVIEW_20260908.md`는 검사 근거와 설계 검토 이력이다. 새 구조의 채택 범위, 클래스 기반 HFSM/GAS/Linked Layer 경계와 A0–A7 구현 순서는 새 정본을 따른다.
- 실제 구현 결과는 해당 도메인의 현행 문서에, 책임/수명 계약 변경은 설계 정본 하단의 날짜별 결정에 기록한다. 새 설계 타입을 현재 구현된 심볼로 설명하지 않는다.

## 2026-09-08 Tag–Ability 아키텍처 v2 확정과 새 마이그레이션

- 캐릭터/이동/전투/AI/상호작용 개발은 먼저 [CHARACTER_GAMEPLAY_ARCHITECTURE.md의 v2 확정 절](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2)을 따른다. 같은 문서 앞부분의 v1 필수 제어 HFSM과 앞선 검토의 미확정 상태는 충돌 범위에서 v2가 대체한다.
- 다음으로 [CHARACTER_TAG_ABILITY_MIGRATION.md](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md)의 M0–M10과 해당 소단계를 읽는다. 옛 A1의 State 클래스 생성이나 Pivot 관측 멤버 추가부터 재개하지 않는다.
- 첫 공동 구현은 [CHARACTER_TAG_ABILITY_STEP_1.md](Docs/Engineering/CHARACTER_TAG_ABILITY_STEP_1.md)의 M1 공통 ASC 연결이다. 사용자가 직접 적용하는 설명이며 현재 게임 구현으로 취급하지 않는다.
- 현재 로코모션 변수/ABP 관측·검증은 계속 [LOCOMOTION_CURRENT_IMPLEMENTATION.md](Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md)와 필요한 실제 소스로 확인한다. 목표 v2, 단계 안내, 실제 구현을 구분한다.
- v2 변경/검증 결과는 Engineering 정본·상태·필요 continuity에 날짜별로 추가한다. 실제 locomotion 변경/계약은 Animation 현행 정본에 기록한다. Art 및 레거시 루트 문서를 이 작업 때문에 읽거나 갱신하지 않는다.



## 2026-09-09 M1 완료 보고 이후 M2 안내

- 사용자 M1 완료 보고와 실제 공통 ASC/lifecycle 소스 반영을 확인했다. 현재 공동 구현은 [CHARACTER_TAG_ABILITY_STEP_2.md](Docs/Engineering/CHARACTER_TAG_ABILITY_STEP_2.md)의 M2.1이다.
- 조회 순서는 계속 v2 → [Migration의 현재 소단계](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md) → Step 2 → 현행 소스/로코모션 정본이다. Step 1을 매번 처음부터 적용하지 않는다.
- M2.1 태그 입력 제한, M2.2 데이터/CMC 정책, M2.3 AI 구동, M2.4 통합 검증으로 나눠 진행한다. 가이드와 실제 적용/검증 상태를 구분한다.


## 2026-09-15 Player 우선 전투 아키텍처 개정 이후 조회 순서

- M1, M2.1, M2.2 Player 이동 기반은 완료 기록을 유지한다. 위 2026-09-09 절의 `M2.3 AI 구동이 다음`이라는 미래 순서는 사용자 재검토 결정으로 대체됐다.
- 캐릭터/전투/AI 후속 작업은 이 라우터 다음에 [CHARACTER_GAMEPLAY_ARCHITECTURE.md의 최신 v2.1 ARCH-20–29](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#player-first-combat-architecture-20260915), 이어 [CHARACTER_TAG_ABILITY_MIGRATION.md의 Player 우선 개정](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#player-first-migration-20260915)을 읽는다.
- 현재 공동 구현 단계는 P1 Player 공통 ActionRequest와 Basic Attack 실행 수직 절편이다. `CHARACTER_TAG_ABILITY_STEP_2.md` 21절/M2.3-A의 AIController 코드는 현재 적용 절차가 아니며 미래 A1의 검토 자료다.
- SprintPivot의 실제 변수·포즈·Stop 계약까지 다루면 위 두 Engineering 문서 다음에 [LOCOMOTION_CURRENT_IMPLEMENTATION.md의 최신 절](Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md)을 읽고 관련 소스/에셋만 표적 확인한다.
- Player 우선은 Player 전용 gameplay API를 만든다는 뜻이 아니다. 공통 ASC/Ability/CombatResult/Locomotion 계약을 Player에서 먼저 검증하고 AIController/BT는 A1/A2에서 두 번째 의도 생성자로 연결한다.


## 2026-09-15 GAS v2.2 단순성 정본과 P1 교체

- 캐릭터/전투 후속 작업은 이 라우터 다음에 [Architecture v2.2 단순성 불변식](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#architecture-v2-2-simplicity-20260915), 이어 [Migration v2.2 최소 P1](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#p1-v2-2-minimal-contract-20260915)을 읽는다. 위 v2.1 ActionRequest/전신 lane 절은 충돌 범위에서 과거 이력이다.
- Player 전투에는 StateTree를 추가하지 않는다. ASC/Ability/Task/Tag/Effect가 전투 실행과 공유 gameplay 상태를 맡고 CMC, Locomotion, Animation, Combat 결과의 고유 책임을 유지한다. StateTree는 미래 AI 상위 판단이나 장기 orchestration의 실제 소비가 생길 때만 검토한다.
- 현재 P1은 기존 `Input.Action.*` tag → 최소 Khazan ASC → granted Ability spec → BasicAttack/Jump Ability의 직접 경로다. ActionRequest/Result, Request/Execution ID 원장, pending handshake, request source Ready, custom full-body lane을 구현하지 않는다.
- 새 class/tag/DataAsset/delegate/handle은 현재 작성자와 소비자, 독립 수명, 엔진 기존 기능으로 부족한 이유가 확인될 때만 추가한다. 상세 줄별 설명은 MD에 두고 production code에는 불명확한 이유·단위·수명·제약만 주석으로 남긴다.


## 2026-09-15 Component capability 원칙과 P1.1 최신 진입점

- 캐릭터/전투 후속 작업은 이 라우터 다음에 [Architecture v2.3 capability component 계약](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#architecture-v2-3-capability-components-20260915), 이어 [Migration v2.3 실행 순서](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#p1-v2-3-capability-component-migration-20260915)을 읽는다. v2.2의 GAS 중심·단순성 원칙은 유지되고 Component/CombatComponent/P1 입력 세부만 v2.3이 구체화한다.
- Component는 선언한 owner 계약을 만족하는 모든 Actor에 붙여 같은 능력을 제공해야 한다. 하나의 전투 능력을 작은 Component 다수로 기계적으로 분할하지 않는다.
- `UKhazanCombatComponent`는 유효한 ASC를 가진 Actor의 공통 전투 교환 경계로 P3 첫 실제 hit와 함께 만든다. P1에는 hit/damage 소비가 없으므로 빈 wrapper를 선행 생성하지 않는다.
- 현재 공동 구현 진입점은 [P1 최소 실습판 v2.3의 P1.1](Docs/Engineering/CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-minimal-walkthrough-v2-3-20260915)이다. 새 Khazan ASC의 Input Tag→Spec activation 한 기능과 기존 Character default subobject 교체만 적용한 뒤 cold build한다.
- 위 실습은 사용자가 Source를 직접 적용하는 설명 절차다. 문서 작성 자체를 게임 Source/BP/asset 적용·빌드·PIE 완료로 기록하지 않는다.


## 2026-09-15 전역 capability component 기준과 P1.2

- 최신 Component 해석은 [Architecture v2.4 전역 Component 원칙](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#architecture-v2-4-global-component-rule-20260915)이다. `CombatComponent`는 예시이며 P3 필수 타입이 아니다. 모든 Component는 호환 owner에 부착했을 때 완결된 능력과 실제 상태/cleanup을 제공해야 하고, 작은 책임 분류만을 위해 새 Component를 만들지 않는다.
- 후속 구현 순서는 [Migration v2.4 P1.2 수정](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#p1-v2-4-direct-definition-grants-20260915)을 사용한다. 현재 grant source가 CharacterDefinition 하나이므로 별도 AbilitySet asset을 선행 생성하지 않는다.
- P1.1 Source와 UE 5.8.2 cold build는 실제 확인됐다. 새 PIE 회귀는 누적 검증 대기다.
- 현재 공동 구현은 [P1 최소 실습판의 P1.2 직접 초기 Ability grant](Docs/Engineering/CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-1-applied-p1-2-direct-grants-20260915)다. 사용자가 Definition의 최소 배열과 Character authority one-shot grant를 적용한다.


## 2026-09-15 P1.2 확인 뒤 P1.3 조회 순서

- P1.2 Source와 UE 5.8.2 build는 확인됐다. 새 PIE/runtime 검증은 누적 대기다.
- 현재 공동 구현은 [P1 최소 실습판의 P1.3 BasicAttack class와 첫 granted Spec](Docs/Engineering/CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md#p1-2-applied-p1-3-basic-attack-spec-20260915)이다.
- 용어는 `FKhazanInitialAbilityGrant` 정적 지시 → 임시 `FGameplayAbilitySpec` → authority `GiveAbility()` → ASC 소유 granted Spec/Handle → 이후 `TryActivateAbility()`와 Ability instance 실행 순으로 구분한다. `EndAbility()`는 실행만 끝내며 `ClearAbility()`가 grant 자체를 회수한다.

<a id="single-player-weak-attack-contract-20260916"></a>
## 2026-09-16 싱글 플레이 모작·WeakAttack 최신 계약

- 이 프로젝트의 제품 목표는 **The First Berserker: Khazan의 실제 플레이 감각과 액션 완성도를 재현하는 Standalone 싱글 플레이 모작**이다. 단계별 probe, 로그, 최소 수직 절편은 제작 결과가 아니라 품질 검증 수단이다. 테스트만 통과하는 임시 동작을 최종 기능으로 남기지 않는다.
- 캐릭터·전투 후속 작업은 최신 Architecture의 `ARCH-30`–`ARCH-32`를 먼저 읽는다. 가상의 멀티플레이 확장성을 위해 client prediction, RPC, PlayerState ASC, 복제용 상태 사본을 선행 구현하지 않는다. 다만 Standalone도 authority를 가지므로 `GiveAbility()`의 authority 조건과 같은 GAS 엔진 계약은 유지한다.
- 원작 데이터의 `WeakAtk01`–`WeakAtk05`를 실행하는 기존 `BasicAttack`은 같은 행동을 가리킨 임시 명칭이었다. 현재·미래 정본 명칭은 `WeakAttack`이며, 과거 절의 `BasicAttack` 표기는 이력으로만 읽는다.
- 실제 native class/file은 `UKhazanWeakAttackAbility`와 `KhazanWeakAttackAbility.h/.cpp`로 변경됐다. 기존 직렬화 class 경로는 `DefaultEngine.ini`의 `CoreRedirects`가 새 class로 이관한다. 이후 Blueprint/Montage 이름은 `GA_WeakAttack_Khazan`, `AM_DAS_WeakAttackCombo`를 사용한다.
- `Input.Action.Attack`은 물리 공격 입력을 Ability Spec에 전달하는 라우팅 태그이므로 이번 class 명칭 변경 대상이 아니다. 약공격 행동의 정체성, 콤보 상태와 수명은 `UKhazanWeakAttackAbility`가 소유한다.
- GAS 설계 근거로 [tranek/GASDocumentation](https://github.com/tranek/GASDocumentation)을 적극 참고하되, 해당 문서는 UE 5.3 기준의 비공식·멀티플레이 sample 설명이다. 이 프로젝트의 UE 5.8.2 plugin source와 싱글 플레이 제품 계약이 API·네트워크 부분의 최종 기준이다.

<a id="character-architecture-v3-entry-20260917"></a>
## 2026-09-17 캐릭터 아키텍처 v3 최신 조회점

- 캐릭터·전투 후속 작업은 이 라우터 다음에 [Architecture v3 네이티브 최소 구조](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v3-native-minimal-20260917), 이어 [P6 v3 단일-task Jump와 관성화 이관](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#p6-native-inertialization-v3-20260917)을 읽는다. 이전 P6의 Montage 재시작·instance ID·두 window depth 설계는 조사 이력이다.
- WeakAttack section 전환은 한 `PlayMontageAndWait`, authored `Next Section=None`, `ComboInputOpen`/`ComboCommit` point, Ability-local 한 칸 buffer, `RequestMontageInertialization()` 직후 `MontageJumpToSection()`을 최신 계약으로 사용한다.
- Inertialization은 pose 전환을 완화하지만 Montage Root Motion의 capsule translation/yaw 연속성을 만들어 주지 않는다. visual pose와 root-motion delta를 별도 gate로 검증한다.
- 현재 문서만 재설계됐으며 Source·Blueprint·Montage·AnimSequence·Input asset에는 아직 v3가 적용되지 않았다.

## 2026-09-18 P6-v3.1 실제 구현 진입점

- 다음 공동 구현은 [P6-v3.1 실제 현재 상태와 01→02 적용 체크포인트](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-1-current-checkpoint-20260918)부터 시작한다.
- Controller/ASC build 기준점을 먼저 닫고, 한 task WeakAttack Source와 Attack02 Montage/최종 Inertialization graph를 같은 기능 checkpoint에서 적용한다. 03–05, Strong 혼합 입력과 다른 아키텍처 정리는 01→02 pose·Root Motion gate 뒤에 진행한다.

## 2026-09-18 P6-v3.2 콤보 후반 입력·회수부 이동 전환

- 01→02 Jump 동작 확인 이후 최신 계약은 Architecture [ARCH-44](Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md#arch-44-three-phase-combo-and-recovery-exit-20260918)와 Migration [P6-v3.2](Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-2-three-phase-input-recovery-exit-20260918)이다.
- 콤보 입력은 `ComboInputOpen → ComboCommit → ComboInputEnd`의 3상태를 사용한다. 외부 행동 전환은 별도 `RecoveryCancelOpen`으로 다루며 combo End와 같은 상태로 합치지 않는다.
- 현재 구현 작업은 먼저 3상태 콤보만 적용·검증하고, 그 다음 Attack02 locomotion early exit를 수직 검증한다. Source/asset 실제 적용 여부는 문서가 아니라 현재 파일과 PIE 결과로 판단한다.


## 2026-10-01 — 최소 변경·문서 인지 상시 기준

- 모든 구현·기능 추가는 기존 구조/엔진 기능/현재 데이터의 재사용과 작은 수정이 우선이다. 불가피한 근거 없이 방대한 구조·소스코드를 추가하지 않는다. 상세 규칙은 AGENTS.md와 Docs/Engineering/UE5_ENGINEERING_RULES.md의 같은 날짜 “모든 구현의 최소 변경과 MD 기반 작업 인지”를 따른다.
- 작업 도메인을 판정한 뒤 해당 최신 상태/규칙/Architecture/Migration 및 필요한 continuity·현행 구현 기록을 활용해 현황, 게임 목표, 사용자 지향점과 공동 구현 스타일을 확인한다. 과거 설계나 미적용 첨부를 현재 구현으로 취급하지 않는다.
- 캐릭터/Dodge의 최신 설계는 Architecture/Migration 하단의 2026-10-01 최소 변경 절이다. 기존 ComboAction/Dodge enum을 유지하고 기존 ASC 입력 경로를 Spec Handle로 좁혀 연결한다. InputEnd 전 Action block/InputEnd 때 ComboWindow Closed를 유지하는 범위에서 X/Y 순서·command event는 그대로 쓴다.



## 2026-10-02 Guard 현행 구현 자료

- Guard 입력·유지/해제·성공/스태미너·InputEnd·ABP 요청은 Engineering/Animation이다. 기존 Architecture/Migration 최신 절 다음에 [GUARD_IMPLEMENTATION_20261002.md](Docs/Engineering/GUARD_IMPLEMENTATION_20261002.md)의 실제 Source·asset·변수/함수 계약과 저장 보고서부터 확인한다.
- 구현/검사 완료와 물리 입력·화면/적 타격 후속 검증을 구분한다. 기존 전체 리소스 재조사나 authoring setup 재실행은 선행 절차가 아니다.

## 2026-10-06 Heal 현행 Source·검증·반영 상태 조회

- HP/MaxHP/물약 입력·Ability/상체 보행 합성은 Engineering와 Animation이다. Architecture/Migration 최신 ARCH-75 다음에 [HEAL_IMPLEMENTATION_20261006.md](Docs/Engineering/HEAL_IMPLEMENTATION_20261006.md)를 읽는다. Art Sequence 전수 재조사 대신 저장 출처/PlaybackPlan을 재사용한다.
- 현행 Source 적용/격리 build·PIE·saved reload는 통과했다. 메인 에셋은 기존 editor 파일 잠금으로 prepared 상태이며 exit 후 선택 반영 helper가 실행 중이다. 최신 단계는 Metadata/HealImplementation_20261006/ApplyStatus.json, 재개는 Engineering Continuity의 같은 날짜 Heal 절이다. 격리 검증과 메인 적용을 구분하고 전체 author setup을 반복하지 않는다.

## 2026-10-06 Heal 메인 적용 완료 조회점

후속 사용자 요청으로 메인 10개 에셋/hash/cold build를 실제 적용했고 ApplyStatus=Complete다. 새 메인 DevMap에 native Heal/input·grant/GE/ABP가 로드돼 직접 Play/DPad 아래 테스트할 수 있다. 앞선 prepared/pending 기록 대신 [Heal 정본의 메인 완료 절](Docs/Engineering/HEAL_IMPLEMENTATION_20261006.md), Metadata/HealImplementation_20261006/MainAppliedResult.json을 현재 적용 근거로 읽는다. 전체 authoring setup/복사/helper를 반복하지 않는다.

## 2026-10-06 Heal 수납·발도 후속 조회점

ARCH-76 → [HEAL_WEAPON_PRESENTATION_20261006.md](Docs/Engineering/HEAL_WEAPON_PRESENTATION_20261006.md)의 최신 완료 절 → 현 KZHealAbility h/cpp를 읽는다. 이전 Heal75% InputEnd/Walk를 마지막까지 유지하는 계약은 발도 시작 InputEnd·Walk 제한 반환으로 대체됐다. Armed/UnArmed는 InGame/DAS/Equip, 두 old paths는 참조0/백업 후 실제 제거됐으며 redirector가 아니다. 기존 UpperBody와 새 Arms Layer/동일 Heal Ability를 재사용했고 격리 stock build/Heal·Guard PIE/메인 선택 반영·build 완료 자료는 Metadata/HealWeapon_20261006이다. 원작 Notify/물리 패드/적 hit는 별도 후속 범위다.
## 2026-10-06 — DevMap 몬스터4종 현행 조회점

몬스터 감지/배회·추적/LockOn 대치·단일/콤보 animation은 Engineering+Animation이다. Architecture 최신 ARCH-77 → Migration → [MONSTER_AI_IMPLEMENTATION_20261006.md](Docs/Engineering/MONSTER_AI_IMPLEMENTATION_20261006.md) 최신 완료 절 → AIController/StateTree nodes/Monster/기존 ComboAction Source 순서로 읽는다. source metadata/원작 조건과 임시 AI값은 Metadata/MonsterAI_20261006을 재사용한다. 제품 실제4종 PIE·기존 Heal/Guard 회귀·main137package/hash/cold build/saved load 완료, 새 main PID11000 DevMap/dirty0/PIE없음, pending helper 없음. 피해/피격은 제외했다. Art resource 파생 위치·원본 보존만 Art state 하단에 기록했으며 전체 library/retime/author setup을 다시 실행하지 않는다.

## 2026-10-07 — 몬스터 대기 루틴/대화 쌍/실제 보행 포즈 후속

ARCH-78 → Migration → [MONSTER_UNAWARE_LOCOMOTION_20261007.md](Docs/Engineering/MONSTER_UNAWARE_LOCOMOTION_20261007.md) 최신 실제 결과 → 현행 AI/Monster/Definition/ComboAction·몬스터 ABP를 읽는다. 현재 작업은 Engineering+Animation이며 Art 원본 추출·전체 재조사 없이 저장 AnimationLibrary/선택32step을 이용한다. 대기와 Patrol 분리, Loop→matching End, mutual Talk01/02, asset-player binding 및 방향/속도 기반 보행이 대상이다. 10/6의 상태 전이 성공만으로 최종 walk pose가 검증됐다고 읽지 않는다. 완료/진행 중 구분은 새 정본 하단과 Engineering continuity, Metadata/MonsterIdle_20261007의 실제 결과를 따른다.

## 2026-10-07 — 몬스터 고정 대기·발견 후 영구 전투·선택 행동 완료 후 재추격 조회

ARCH-78 후속 완료 절 → Migration → [MONSTER_UNAWARE_LOCOMOTION_20261007.md](Docs/Engineering/MONSTER_UNAWARE_LOCOMOTION_20261007.md)의 고정 대기 후속 실제 메인 완료 절 → 현행 Controller/StateTree Task를 확인한다. Heavy Basic03/Halberd Basic02 고정, 유효 Player target 유지, 선택 Standoff/Attack 완료 후 Chase가 현재 구현이다. Metadata/MonsterCombatPolicy_20261007/MainAppliedResult.json의 stock 4종/Waiting PIE·Main9/hash/build/saved reload가 실제 근거다. 과거 sight memory/leash에 의한 Idle 복귀와 거리 증가 즉시 Standoff 중단을 현행으로 설명하지 않는다. 전체 authoring/retime/원본 재조사를 반복하지 않는다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

Art 애니메이션 정리 요청은 [Enemy Art 정본](Docs/Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md)→CurrentAnimationLibrary.csv, 몬스터 동작은 Architecture ARCH-79 완료→Migration→[공격·Root Motion·재추격 정본](Docs/Engineering/MONSTER_ATTACK_ROOT_MOTION_20261007.md)을 읽는다. Archer 제외6종/813시퀀스·12분류/35공격은 Main 반영·stock build·PIE와 saved reload 완료다. Nav 보행은 CMC, 몽타주는 root 소비다. 기존 imported path/RootMotion=false 기록을 현재 정책으로 재사용하거나 author setup을 반복하지 않는다.


<!-- ApesYetugaBehaviorResearch_20261008 -->
## 2026-10-08 — Apes 엘리트·Yetuga 보스 원작 패턴 분석 조회점

패턴/공격/회복 요청은 Art+Engineering이다. [원본·공개자료 감사](Docs/Art/APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md)와 [행동 분석](Docs/Engineering/APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md) 최신 보완 절→Metadata/EnemyBehaviorResearch_20261008의 표적 report→필요한 package/export 순으로 읽는다. 원작 cooked AI/SI/SB/CS/AP·공개 전투 표적프레임·공식5→8초 exhaustion을 대조했다. 분석 완료이며 신규 몬스터AI/게임코드/asset 적용·build·PIE 완료가 아니다. ARCH-79의4NPC와 Yetuga/Apes library 상태는 유지한다.

Apes Early/Standard 일반군·피격passive가 다르고 Yetuga는 custom BT다. step/시각동작/notify/attack group/실제적중을 구분한다. BT HP raw65/60/50(bCompareRate=false)을퍼센트로바꾸지않는다. 현재asset212개이름은 CurrentApesYetugaLibrary.csv를조회하고 oldPlayback경로를재사용하지않는다. 동명이름 DamageParry는 Index.local_path/full package로구분한다. 전체추출/retime/rename을반복하지않는다.

## 2026-10-08 — NPC4 이동 보간·대치 조준·공격 추적 회전 후속

Engineering/Animation 요청이다. Architecture ARCH-80 → 현재 Migration → [NPC4 현행 보간·회전 문서](Docs/Engineering/MONSTER_FACING_SMOOTHING_20261008.md) 최신 절 → 관련 Monster/AIController/ComboAction Source 순으로 읽는다. Source6의 작은 확장과 기존 Combat BS4를 사용하며 새 runtime 파일은 없다. 격리 구현/검증과 Main 실제 반영을 구분한다. 현재 최종 병합 DLL의 Facing35는 통과했으나 Main13700의 BS 파일 잠금으로 전달은 아직 전이다. 정확 재개/사용자 코드 동시 변경 보호는 Engineering Continuity 최신 NPC4 절과 Metadata/MonsterMotion_20261008을 따른다. 기존 전체 authoring/retime/delivery를 반복하지 않는다.

## 2026-10-08 ? ??? HP?Stamina ?? ?? ???

Engineering ????. Architecture? ?? AttributeSet/CharacterDefinition ??? ???Migration ?? ???[??? ?? ??? HP?Stamina ?? ?? ?](Docs/Engineering/MONSTER_AI_IMPLEMENTATION_20261006.md)?Metadata/MonsterStats_20261008/FinalVerification.json ? ??? GE/DA? ???. ??? ?????6? ???12?? Main ???fresh saved reload ???? ? ?? Source0??. ShieldMan? ?? family? SwordShield, Apes? ApesStoneHandElite?. Apes/Yetuga? Definition+GE? ???? gameplay actor/registry? ?? ???? ???. ?????????? ??/?? ?? ??? ???? ???. ?? NPC4 ??? Main ??? ? ?? Source8??+OverFury2??? Engineering Continuity ?? ?? ???.


## 2026-10-08 15:52 KST — MonsterStamina 작업 중 및 이전 stats 기록 가독성 보충


기존 15:00 KST 몬스터 초기 수치 기록의 일부 한국어가 작성 과정에서 물음표로 손실되어 이 절에 가독성 있는 사실을 추가한다. 이전 기록은 삭제하지 않는다. 몬스터6의 GE_Init/CharacterDefinition 12개는 이미 Main 적용과 fresh saved readback을 완료했다. 값은 Swordsman/SwordShield HP100·Stamina50, HeavySwordsman/HalberdElite HP200·Stamina50, Apes HP400·Stamina100, Yetuga HP1000·Stamina150이고 모두 current=max이다. 근거는 Metadata/MonsterStats_20261008/FinalVerification.json complete=true 및 WorkSavedReload/MainSavedReload.json이다. 그 작업은 설정만 한 것으로 소진/회복/피격 기능 완료와 구분한다. Player 초기 GE2와 당시 Source/Config를 보존했다. Apes/Yetuga 당시에는 Definition/GE만 있고 gameplay BP/registry 연결은 없었다.

이번 요청은 Engineering 구현과 원작 metadata 분석이 결합된 Mixed다. Router→Architecture 최신 ARCH-82 계약→Migration→MONSTER_STAMINA_EXHAUSTION_20261008.md/표적 evidence→현재 Source 순서다. Art 원작 숫자·클립 매핑은 해당 Art 감사와 Metadata/EnemyStaminaResearch_20261008을 사용한다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

이번 기능은 Mixed 완료다. 현재 구현은 Architecture ARCH-82의 최신 완료 절 → Migration → [소진·브루탈 정본](Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md)을 읽는다. 원작 값·Fortitude/Stamina 차이·클립 매핑은 [Art 감사](Docs/Art/MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md)와 기존 표적 metadata를 재사용한다. Main 전달105파일/stock build/453 native checks/회귀5종/새 Main saved readback이 완료됐고, 이전 Work-only·파일 잠금 대기 상태를 현행으로 사용하지 않는다. NPC4 추적 회전·Combat BS4의 대기 변경도 최신 Source와 함께 Main에 반영됐다. 상세 검증 범위와 미구현 실제 패링 생산자는 정본을 따른다. 전체 재추출·retime·authoring·과거 alias 재전달은 하지 않는다.


<!-- MonsterStaminaConcurrentMainBuildVerified_20261008 -->
## 2026-10-08 17:39 KST — 후속 Main 기본 DLL 빌드 보존·재검증

전달 완료 뒤 본 작업이 시작하지 않은 Main native build가 새 canonical DLL과 manifest를 만들었다. 해당 build는 Succeeded이고 선택 모듈은 현재 `UnrealEditor-Khazan.dll`, SHA `3a2b4942da22fdf94cc7cf6581da3b5fb04f63475315c675d66ef6c4782e758d`다. 이전 unique alias 전달·canonical 보존은 당시 사실이며 현재 모듈 선택을 과거 alias로 되돌리지 않았다. 전달105행과 전체 Source/Config가 검증한 현재 구현과 동일한 것을 확인했다.

별도 fresh Main commandlet에서 현재 canonical DLL을 실제 로드해 저장 Definition6+Player1/montage20/sequence49/attackBP35/body2 및 NPC4 BS·CMC/AI CDO·dirty0를 다시 확인했고 exit0으로 종료했다. 증거는 Metadata/MonsterStamina_20261008/{ConcurrentMainRebuild,FinalVerification_CurrentMain,MainSavedReload_ConcurrentBuild}.json과 ConcurrentMainBuild.log다. 이 새 DLL에서 native453/회귀5종을 다시 실행한 것은 아니며 동일한 제품 Source의 이전 Work runtime 결과와 새 Main saved readback을 구분한다. 사용자 Main19576은 읽기 inventory로만 확인했으며 제어·PIE·저장·종료하지 않았다. 이제 현재 Main 기본 DLL을 사용하고 과거 전달/authoring helper를 재실행하지 않는다.

## 2026-10-08 19:13 KST — 현재 Player 공격 VFX Main 전달·새 프로세스 검증 완료

공격 이펙트는 Mixed다. Architecture ARCH-83 완료 → Migration → [런타임 정본](Docs/Engineering/PLAYER_ATTACK_VFX_RUNTIME_20261008.md)과 [원본·시각 정본](Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 최신 완료 절 → `Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json` 및 `CombinedPlaybackWindows.csv`를 따른다. 기존18공격 진입/자동 후속·앞뒤 브루탈의8몽타주, Particle345/Decal56 총401구간을 Main에 전달했고 별도 새 Main의 실제 RHI18+5검사와 저장8,308field 검사가 통과했다. 사용자 에디터는 저장·PIE·종료·새 native schema reload하지 않았다.

현재 모듈 선택은 기존 canonical을 보존한 `UnrealEditor-KhazanPlayerAttackVFX20261008.dll`이다. 위17:39의 canonical 선택은 당시 기록이며 과거 alias로 되돌리지 않는다. 기존 사용자 에디터는 정상 재시작 후 새 native Notify schema를 사용한다. 이전 pending 기록과 frozen ArtManifest의 초기 pending 필드는 최종 receipt의 supersession으로 읽는다. 전체 재추출·리타이밍·authoring·delivery를 반복하지 않는다. 원작 cooked shader/native 조건 일부와 화면 완전 일치, 별도 Snow/Water 원본 이벤트 및 shipping 성능은 검증 완료 범위가 아니다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — 공통 피격·Shield 방어·브루탈 접근 Main 완료 조회점

이 요청은 Mixed다. Architecture 최신 ARCH-85 완료→Migration→[CombatReaction runtime 정본](Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md)의 완료 절→[사용·조정 설명](Metadata/CombatReaction_20261008/UserGuide_20261010.md)→실제 Main Source/Definition을 읽는다. 원본 분류·클립/raw/root·공격 형상은 [Art 감사](Docs/Art/COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)와 기존 표적 plan을 재사용한다.

Main146행(16runtime/130asset)·stock build·RHI32피격/15브루탈/3충돌·회귀4종·fresh Work/Main654,552checks는 [FinalVerification](Metadata/CombatReaction_20261008/FinalVerification.json)으로 완료 확인됐다. 이전 Work-only/정책 timeout 조사/전달 pending을 현재 상태로 설명하지 않는다. 현재 모듈은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`이며 canonical은 보존했다. Heavy Launch/Apes·Yetuga fallback·unsupported shape11 및 임시 수치의 출처는 각 정본을 따른다. 별도 MonsterVFX의 ARCH-84와 구분하고, 다른 후속 Main delivery가 있으면 새 current manifest/Source를 먼저 확인한다. 완료된 전체 author/metadata 추출/retime/delivery를 반복하지 않는다.

<!-- BrutalInputDevMapComplete_20261010 -->
## 2026-10-10 — 브루탈 B 입력·DevMap 확장/6종 배치 조회

입력 변경은 Engineering, 테스트 맵의 바닥·배치는 Art이며 이번 요청은 Mixed 완료다. Router→Architecture/Migration→[CombatReaction 정본의 B 입력 최신 절](Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md)을 읽고, 맵은 [Art state의 DevMap 최신 절](Docs/Art/ART_PROJECT_STATE.md)과 Art continuity를 읽는다. [설명·배치표](Metadata/BrutalInputDevMap_20261010/README.md), [최종 증거](Metadata/BrutalInputDevMap_20261010/FinalVerification.json), fresh saved/PIE02가 Main Source4·고유에셋5·build·12마리6종 초기화·인간4종 AI 검증 완료 근거다. 새 runtime 파일/class0개다.

현행 브루탈 키는 B이며 과거 X 기록은 당시 상태다. 바닥은 약320m×320m, 기존 인간10마리+Apes/Yetuga 각1마리다. 맵 크기·XY 배치는 원작 근거 없는 테스트용 임시값이고 짐승 자율 AI는 기존 None이다. 실제 물리 B 누름·새 배치 화면/원작 일치는 별도 확인 범위다. 현재 선택 DLL은 이번 검증 시점 UnrealEditor-Khazan-20261010.dll이며 후속은 current manifest/Source를 확인한다. 이미 완료된 author/retime/delivery를 재실행하지 않는다.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — 몬스터6종 VFX Main 완료 조회점

Mixed 요청이다. Architecture 최신 ARCH-84 완료 → Migration → [실행 정본](Docs/Engineering/MONSTER_VFX_RUNTIME_20261008.md)/[Art 정본](Docs/Art/MONSTER_VFX_PLAYBACK_20261008.md) → [최종 증거](Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)를 읽는다. 최종 선택972(Source11/author499/Art457/reused WPO1/추가 adapter4), Sequence487·source2855+sentinel487=State3342·Death6의 Main 전달/fresh saved/네 실제 RHI·Root 표본 검토가 완료됐다. 현재 alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`다. 원작 shader/native/전체 pixel parity·unsupported216/짐승 AI는 별도다. 과거 pending·구 alias·전체 author/delivery를 다시 적용하지 않는다.

초기968/Art457은 보존하고 Main 누락 adapter4를 별도 strict supplement로 추가한 최종972 기준이다. Source/native/material graph와 private proof는 유지했으며 새 Main 최종 검증은 추가 전달 이후 결과다.
## 2026-10-11 — Combat UI와 Main 후속 통합 라우팅

- 록온/B·HP/Stamina·head/boss HUD runtime: Engineering의 `COMBAT_UI_RUNTIME_20261011.md`. 캐릭터 공통 순서는 Architecture→Migration→해당 정본/현재 Source를 유지한다.
- 원작 UI texture/font/widget override/수치·shader adapter: Art의 `COMBAT_UI_SOURCE_AUDIT_20261011.md` 및 저장 `Metadata/CombatUI_20261011`. UI 작업은 두 도메인의 이 최소 자료만 읽는다.
- 낙하 landed/paired Brutal root-mode·capsule 정렬 및 Snow contact: Engineering의 `COMBAT_PRESENTATION_FOLLOWUP_20261011.md`; blood/DAS·Snow layer/조명/RHI는 Art의 동명 정본이다. 최신 Main 전달 완료 evidence는 `Metadata/CombatPresentationFix_20261011/MainResume/FinalVerification.json`과 UI FinalVerification이다. 과거 private 전체/옛 alias를 다시 전달하지 않는다.


## 2026-10-12T02:04:36+09:00 — Player/monster6/HeinMach 사운드 정확 재개 조회

사운드 추출·임포트와 행동별 재생은 Mixed다. Architecture 최신ARCH-89→Migration→Engineering/Art continuity의 최신 사운드 절→Saved/ImportReports/GameplayAudio_20261011/ResumeState05.json 및 PreparedVerification01.json을 읽는다. chunk0/chunk1/원본 metadata·bank/media/timing의 재사용 경로는 Art knowledge index에 있다. Main cue/wave/2163 notify·HeinMach 환경음은 저장됐고 새37 audio-array binding 수정본은 fresh/실제 PIE 검증 완료지만 Rider Main 파일 잠금으로 반영 대기다. 준비본을 Main 완료로 읽거나 전체 re-extract/import/retime/옛 DLL 전달을 반복하지 않는다.


## 2026-10-12T04:22:44+09:00 — 사진 기준 혈액·바닥 혈흔 후속 조회

Mixed다. Architecture 최신 ARCH-88 사진 완료 → Migration → Art MONSTER_PRESENTATION_REPAIR_20261011.md 최신 절/도메인 continuity → Metadata/MonsterBloodReference_20261012/FinalVerification.json 및 ResumeState03.json을 따른다. Main runtime2/DEV2/유효 package5, native build2026101254/fresh saved/실제 눈6종·collision13은 완료다. 이전 바닥 제거는 accepted-hit의 새 불규칙 혈흔에 한해 최신 사진 지시로 대체됐다. 사용자 editor는 제어하지 않았고 정상 재시작이 필요하다. 이전 pending·private 전체 author/delivery/alias 복원을 반복하지 않는다.


## 2026-10-12T08:17:34+09:00 — 가드 시작 패링 Main 완료 조회

패링은 Mixed다. Architecture 최신 ARCH-90 → Migration → Docs/Engineering/PARRY_IMPLEMENTATION_20261012.md와 Docs/Art/PLAYER_PARRY_SOURCE_20261012.md의 Main 완료 절 → Metadata/Parry_20261012/FinalVerification.json을 따른다. Main Source7/asset13·build/fresh Parry15/6종·Guard/PlayerAttackCollision·saved audit가 성공했다. 현재 모듈은 UnrealEditor-Khazan.dll이며 동시 stock build 뒤 현 Source와 함께 검증했다. 이전 Main 잠금/Work-only를 현재 상태로 읽지 않으며 전체 author/추출/옛 DLL 복원은 반복하지 않는다. 기본 창 .146초는 source clock 계산이며 alpha 표현 TEMP와 원작 완전 일치 미확인 범위를 구분한다.



## 2026-10-12T11:04:18+09:00 — 몬스터 Root·충돌·이펙트 Main 완료 조회
Mixed 요청은 Architecture ARCH-91 완료→Migration→Engineering MONSTER_ATTACK_ROOT_MOTION_20261007 / MONSTER_VFX_RUNTIME_20261008, Art ENEMY_ANIMATION_ORGANIZATION_20261007 / MONSTER_PRESENTATION_REPAIR_20261011의 최신 추가 절 및 Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json·ResumeState03.json을 따른다. Source7/RootLock88·current canonical build·fresh MainRoot1176/monster30/player16/saved 동일, 동일 Source privateFX198/1577/death6 완료. 다른 Source/자산·오래된alias/fullauthor/reimport를 반복 전달하지 않는다.


## 2026-10-12T13:12:55+09:00 — 사망 포즈·브루탈 위치·액션 효과/혈흔 후속

Engineering: Architecture ARCH-92 → COMBAT_PRESENTATION_FOLLOWUP_20261011.md/MONSTER_VFX_RUNTIME_20261008.md 최신 절. Art: MONSTER_PRESENTATION_REPAIR_20261011.md/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md 최신 절. 상태·exact proof는 Metadata/CombatFinishFollowup_20261012/FinalVerification.json/ResumeState04.json. 완료된 이전 전체 author/추출/Root·Parry 전달을 반복하지 않는다.


## 2026-10-12T13:40:48+09:00 — DevMap·HeinMach 조명/재질 조정본 준비

Art: Docs/Art/SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md → Metadata/SceneLook_20261012/{PreparedVerification,ResumeState,PreparedDelivery,DeliveryBlocked}.json. 준비본493 검증 완료, Main Win32error32/DevMap.umap lock으로 쓰기0. 잠금 해제 후 선택 전달과 새 Main saved/RHI 검증만 재개한다. 전체 author/추출/과거 Source·DLL 전달은 반복하지 않는다.

<!-- SceneLook_20261012_PreparedAwaitingMainUnlock -->


## 2026-10-12T14:44:13+09:00 — SceneLook Main 완료

Art: Docs/Art/SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md → Metadata/SceneLook_20261012/FinalVerification.json. 앞선 잠금 대기를 대체한다. 선택493개 Main SHA 및 새 saved/RHI 화면 검증 완료. Source/Config/DLL 전달0. 전체 author·추출·재임포트를 반복하지 않는다.

<!-- SceneLook_20261012_MainCompleted -->


## 2026-10-12T18:08:30.145524+09:00 — 몬스터 넉백·몽타주 정수 FPS 진행 조회

Mixed 요청이다. Architecture ARCH-96 → Migration → COMBAT_REACTION_RUNTIME_20261008.md 최신 계약과 해당 도메인 continuity → Metadata/AnimationTimingKnockback_20261012/ResumeState.json·Plan.json·InventoryBefore.json 순서로 읽는다. 시퀀스 키/시계 변환은 Art/Animation, 기존 HitReaction 실행 수명과 실제 이동 검증은 Engineering에 기록한다. 준비/추론/actual sampling·build/PIE/Main 완료를 구분한다.


## 2026-10-12T19:30:36.993088+09:00 — ARCH-96 넉백·몽타주 FPS Main 완료 조회

Mixed. Architecture 최신 ARCH-96 완료 → COMBAT_REACTION_RUNTIME_20261008.md와 Art ENEMY_ANIMATION_ORGANIZATION_20261007.md 최신 절 → Metadata/AnimationTimingKnockback_20261012/FinalVerification.json/CurrentAnimationLibrary_IntegerFPS.csv. Main516/build/fresh raw3854855·montage158/실제6종11case/전체FPS가 완료됐다. 기존 precision montage model과 정수 displayed sampling 구분·TEMP·원작 미확인 범위를 유지하며 과거 전체 author/retime/Root repair/옛 alias 전달은 반복하지 않는다.


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

Mixed 완료. Architecture ARCH95 latest additive amendment → Engineering COMBAT_PRESENTATION_FOLLOWUP_20261011 / Art PLAYER_ATTACK_VFX_PLAYBACK_20261008 최신 절 → Metadata/CombatImpactUpgrade_20261012/FinalVerification.json. Monster requested Niagara0·original220×21 차이0·Player additional50쌍/actual weapon geometry·build/native/saved/Main editor ready. 이전 교체 author/flash·전체 Root/FPS/old DLL 전달을 반복하지 않는다.

## 2026-10-13 — StrongCombo 인간형 VictimFront 피격 후속 조회

Engineering. Architecture 최신 ARCH-97 → Migration → Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md 마지막 절 → Metadata/StrongComboVictimFront_20261013/FinalVerification.json·Changes.patch 순서다. Main StrongAttack01–03의6window/인간형4종 선택값, 기존 HitReaction의 fixed montage와 자기 root 억제, build/fresh saved/actual12case·24hit/기존 collision16 회귀 완료다. 거대형 및 다른 공격 반응은 보존한다. 완료한 author/과거 Root·FPS·VFX 재전달을 반복하지 않는다.


## 2026-10-13 — 몬스터 PhysicsAsset·천/Hair 현재 작업

Engineering 물리: `Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md` → `PHYSICS_DIAGNOSTICS.md` 최신 절 → `Metadata/MonsterSecondaryPhysics_20261013`. Art shape 생성: `Docs/Art/MONSTER_PHYSICS_ASSET_RESTORATION_20261013.md`. 현재 격리 후보/품질 실패 조사 중이며 Main 미반영이다. 과거 Player full author/FPS/root/VFX author를 재실행하지 않는다.
<!-- MonsterSecondaryPhysics_20261013_intake -->


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 보조 물리 Main 완료 (ARCH-06/07/10/16 유지)

기존 engine SkeletalMesh/RigidBody/CopyPose가 보조 포즈·수명·EndPlay를 소유한다. ASC/Ability/Task/CMC/AI 소유자는 그대로다. 새 runtime class/component/manager/tag0이다. 중검의 기존 BeginPlay만 follower 독립 평가·parent tick prerequisite·full parent cloth collision source로 보완했다. 실제99SHA/Main build/saved/RHI/gameplay 완료 정본은 MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json이다. 기존 착수/미반영/검증 대기 기록을 이 완료가 대체한다.
<!-- MonsterSecondaryPhysics_20261013_main_complete -->


## 2026-10-13 ? ???? ?? ?? VFX ??

Mixed ??? Architecture/Migration ? Docs/Engineering/PLAYER_HEAL_VFX_RUNTIME_20261013.md ? Docs/Art/PLAYER_HEAL_VFX_SOURCE_20261013.md? ?? Main ?? ?? ???. Source SB_Kazan_Recovery.UpperAnim/AC_Kazan_Recovery5 particle window?mesh3/FT_Trail.G/ShaderLUT ? ??/?? TEMP? Metadata/HealVFX_20261013/Original/SourceEvents.json/Author03/VisibilityPolish02?? ?? ????. ?? ??? FinalVerification.json, MainSaved01/MainFinalPIE01??15 target/?runtime??0/??HP?weapon?pose???/physics ????. ???/full author/?? retime/?? DLL ??? ???? ???.

### 2026-10-13 — 회복 VFX 조회 경로 정확화

위 metadata 조회는 각각 독립 경로다: Metadata/HealVFX_20261013/Original/ (원본 JSON), Metadata/HealVFX_20261013/SourceEvents.json, Metadata/HealVFX_20261013/Author03/Author.json, Metadata/HealVFX_20261013/VisibilityPolish02/Polish.json. 완료/재개는 같은 root의 FinalVerification.json / ResumeState.json이다.


## 2026-10-13T14:14:46+09:00 — Player·인간형 SFX 누락/끝음 Main 완료 조회

Mixed. Architecture ARCH-89 최신 완료→Migration/Engineering·Art continuity→Metadata/HumanoidSFX_20261013/FinalVerification.json / ResumeState04.json 순서다. 현재 원작 추가51cue/248wave·final1682 sound/control·527seq/35combo/174window/8Dodge 성공과 actual78 mixer/메인 hit·Guard·Parry·Dodge/fresh saved 보존이 완료됐다. Yetuga/Apes·map/ambient 재author는 제외했다. 원본/계산/TEMP와 Wwise DSP 미일치를 구분하며 과거 pending37/full extraction/full author/old DLL 복원을 반복하지 않는다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

GiantVFX Yetuga/Apes와 첨부PlayerSlash 재개는 현재Main 반영·검증 완료다. GiantVFX는 Docs/Art/GIANT_VFX_REFINEMENT_20261013.md 및 Docs/Engineering/MONSTER_VFX_RUNTIME_20261008.md 최신 절과 Metadata/GiantVFX_20261013/FinalVerification.json/ResumeState.json을 먼저 확인한다. PlayerSlash는 Metadata/PlayerSlashAlignment_20261013/ResumeVerification.json 및 FinalVerification.json을 따른다. exact partial/error 재개는 각 domain continuity에 보존했다. 과거 author/full delivery/old DLL을 다시 실행하지 않는다.

## 2026-10-13 — WeakAttack01 반대 방향 Slash·전방 확대 조회

Mixed. Architecture ARCH-95 최신 WeakAttack01 완료 절 → Engineering COMBAT_PRESENTATION_FOLLOWUP_20261011 / Art PLAYER_ATTACK_VFX_PLAYBACK_20261008 최신 절 → Metadata/WeakAttack01Slash_20261013/FinalVerification.json·ResumeState.json. 회수 손 대신 실제 내려베는 Weapon_R의 첫2 addon을 선택하고 첫4 효과 객체의 TEMP 전방35cm/XY1.15배를 Main에 적용했다. build/saved/actual18+Brutal4·GPU70/yaw90 완료. 앞선 전체 Slash 정렬의 시각 판단을 이 first-attack 근거로 보완하며 stale mirror/private DLL/전체 author는 반복하지 않는다.

## 2026-10-15 — HeinMach 색감·혈흔·VFX 후속 조회

원작 사진 대조 색감/빨간 혈흔/맵 간 VFX 색 보존은 Art의 HEINMACH_COLOUR_VFX_20261015.md 최신 완료 절과 Metadata/HeinMachColourVFX_20261015/FinalVerification.json을 우선한다. 승인 피격 발생점·Definition 연결/실제 PIE·build는 Engineering의 COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 절을 읽는다. Main 적용105 및 검증은 완료이며 재개는 ResumeState03.json이다. 이전 진행 중 기록을 이유로 완료 author/전체 리소스 조사를 반복하지 않는다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 ? Yetuga?Apes ??170? ??/?? ?? ?? ??

Mixed. Architecture/Migration?Engineering MONSTER_ATTACK_ROOT_MOTION_20261007.md ? Art ENEMY_ANIMATION_ORGANIZATION_20261007.md ?? ??Metadata/GiantRootUsage_20261015/FinalVerification.json ???. ?? ??170/30montage, PartGroggy Loop/End4? first-frame root522.148cm? reference lock?? Main ??, fresh170/510???weak-part/???RHI6??/??model?notify170/???166 ??? ????. ??? HitAdditive8 off? ?? ?? ???. ?? author/full import/? ????/? DLL ??? ???? ???.



## 2026-10-15 — HeinMach GateCube 포탈 후속 조회

같은 월드의 Yetuga 전장 포탈 동작은 Docs/Engineering/HEINMACH_YETUGA_PORTAL_20261015.md, 배치·전용 Niagara는 Docs/Art/HEINMACH_YETUGA_PORTAL_20261015.md를 따른다. 최신 증거는 Metadata/HeinMachPortal_20261015/FinalVerification.json이다. 현재 Main의 portal/arrival2 actor와 전용4asset을 기존 look/Level 작업에서 보존한다. 과거 Work map/DLL 전달이나 완료된 authoring을 반복하지 않는다.

<!-- HeinMachPortal_20261015_complete -->


## 2026-10-15 — HeinMach BlueB와 Spinning donor 표현 후속

노출 추가 감소·푸른 조명/안개와 Spinning의 KZ_Slash 교체는 Art의 HEINMACH_BLUE_SPINNING_20261015.md → Metadata/HeinMachLookSpin_20261015/FinalVerification.json을 우선한다. 기존 CombatEffect 수명/판정 검증은 Engineering COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 완료 절을 따른다. 기존 HEINMACH_COLOUR_VFX의 장면 TEMP 값만 BlueB로 대체하며 혈흔·VFX 재질 보상은 유지한다. 최신 Main의 포탈/몬스터·PlayerStart를 보존한3 asset 선택 전달과 실제 Main 검사가 완료됐다. 이전 Work map/Source/DLL 일괄 복원·완료 author 재실행은 하지 않는다.

<!-- HeinMachLookSpin_20261015_complete -->


## 2026-10-16 ? HeinMach ??? ?? ?? ??

Art. Docs/Art/HEINMACH_ROUTE_PRUNING_20261016.md ? Metadata/HeinMachRoutePrune_20261016/FinalVerification.json? ????. Main? PlayerStart???/Yetuga ??? ?? ??? ??? actor4258/instance9137 ?????. ?? ?? ?? ???? ???? ??? ?? Player metadata? RoutePruneExclusions? ?? Before map? ?? ??? ??. Source/Config/runtime ?? ??0, Main fresh ?? ??, ?? ??0??.


## 2026-10-16 — HeinMach 미사용 구간 정리 조회 (한글 기록 정정)

앞선 같은 작업의 깨진 한글 절은 이 절로 정정한다. Art → Docs/Art/HEINMACH_ROUTE_PRUNING_20261016.md → Metadata/HeinMachRoutePrune_20261016/FinalVerification.json. Main은 PlayerStart→포탈/Yetuga 전장과 사용 시야를 보존한 actor4258/instance9137 삭제본이다. 현재 Player metadata RoutePruneExclusions와 Before 원본을 복구 근거로 삼으며 과거 전량 배치 보고서로 되살리지 않는다. Main fresh 검증 완료, Source/Config/runtime 신규 변경0, 필수 잔여0이다.
