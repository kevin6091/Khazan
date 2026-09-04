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
