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

