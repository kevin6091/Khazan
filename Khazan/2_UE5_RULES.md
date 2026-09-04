# UE5 작업 규칙

> 모든 작업 시작 전에 프로젝트 핵심 문서 3개를 확인한다. 새 규칙과 변경 이력은 기존 내용을 덮어쓰지 않고 이 문서 하단에 추가한다.

## 2026-08-31 기준

- 회전, 방향 벡터 등 수학 연산은 `UKismetMathLibrary`를 사용하며, 데이터 표현은 `FVector`를 우선한다.
- `FVector`가 Ambiguous 오류를 일으키면 전역 네임스페이스를 명시한 `::FVector`를 사용한다.
- 자동 완성으로 `Aossoa.isph` 등 Unreal 내부 ISPC/SIMD 헤더가 Include되지 않도록 확인한다.
- HeinMach 레벨 재구성에서 주인공의 맨손 비틀거림 및 기본 이동 전용 장면은 임포트·배치·시퀀스 구성 범위에서 제외한다.

## 2026-08-31 임포트 규칙 추가

- FModel ActorX 에셋은 프로젝트 로컬 `UnrealPSKPSA` 플러그인을 통해 임포트하고, 기존 유효 에셋을 덮어쓰지 않는다.
- HeinMach 환경 자동 임포트는 지형·서브레벨·조명·충돌 USD만 허용하며 `HeinMach_Cine_*`, 캐릭터, 스폰, 사운드, BGM, 위치·스플라인 레이어는 포함하지 않는다.
- 자동 임포트 스크립트는 재실행 가능하게 유지하고, 저장된 맵·에셋 클래스·머티리얼 슬롯을 검증한 뒤 완료로 판정한다.

## 2026-08-31 FModel 에셋 규칙 추가

- FModel 추출물의 이름, 경로, 메시 분할, 머티리얼/텍스처 연결을 다루기 전에 `4_FMODEL_ASSET_RULES.md`를 확인한다.
- 원본 package path와 이름을 식별 근거로 보존하며 오탈자, 좌우, variant, LOD suffix를 임의로 정규화하지 않는다.
- basename 추정 대신 USDA/JSON의 명시적 asset reference와 material binding을 우선한다.

## 2026-08-31 HeinMach 재구성 및 검증 규칙

- 모든 작업 전에 1_PROJECT_STATE.md, 2_UE5_RULES.md, 3_ARCHITECTURE.md, 4_FMODEL_ASSET_RULES.md, 5_WORK_CONTINUITY.md를 순서대로 확인한다. 기존 기록은 수정하거나 삭제하지 않고 새 사실을 각 문서 하단에 추가한다.
- USD 임포트에서 서로 다른 source mesh나 material slot이 합쳐지면 안 되는 작업은 asset sharing과 material-slot merging을 모두 비활성화한다.
- USDA PointInstancer는 개별 StaticMeshActor로 임의 전개하지 않는다. prototype reference와 각 instance transform을 보존한 HISM batch로 복원하고 baseline digest로 재검증한다.
- mesh material slot은 basename 또는 slot index만으로 매핑하지 않는다. source USDA binding, source material package, texture fingerprint를 함께 사용한다.
- TwoSided, BlendMode, opacity mask clip과 source override material은 source JSON/USDA를 기준으로 보존한다.
- negative scale 또는 negative determinant는 곧바로 뒤집힌 winding을 뜻하지 않는다. UE가 mirrored transform의 face orientation을 처리하므로 triangle winding audit 없이 reverse_culling을 일괄 활성화하지 않는다.
- 다른 world의 액터나 component를 현재 world로 복제할 때 source/target world가 dirty인 상태에서 같은 Python 실행으로 target을 다시 로드하지 않는다. target world를 먼저 저장하고 에디터를 재시작한 뒤 target을 열어 검증한다.
- FModel이 만든 dynamic material USD의 UsdPreviewSurface가 opaque stub이면 원본 shader graph로 간주하지 않는다. UObject JSON의 parent, scalar/vector parameter, texture reference를 근거로 별도의 preview material을 구성한다.
- UE Python MaterialEditingLibrary에서 단일 입력인 Abs, OneMinus, ComponentMask 노드는 input name으로 None을 사용한다. ComponentMask의 R/G/B/A boolean과 scalar로 사용할 채널을 명시한다.
- Python으로 생성한 material은 저장만으로 완료 처리하지 않는다. compile error, WorldGrid fallback, blend mode, TwoSided, 실제 viewport 표현을 모두 검사한다.
- 재구성 스크립트는 idempotent해야 하며 생성/재사용 수, source count, transform mismatch, mesh/material mismatch를 JSON report로 남긴다.
- 크레딧, 에디터 상태, 외부 도구 문제로 완료하지 못할 가능성이 있으면 중단 전에 5_WORK_CONTINUITY.md를 갱신한다.
- 모든 HeinMach_Cine_* 및 주인공 맨손 비틀거림·기본 이동 전용 장면은 계속 제외한다.

## 2026-08-31 조사 최소화 규칙

- 모든 작업 전에 프로젝트 문서 1–6을 먼저 읽으며, 정보 탐색은 6_SURVEY_KNOWLEDGE_BASE.md의 질문별 우선 조회표에서 시작한다.
- 정보가 기억나지 않는다는 이유만으로 FModel root, Content 전체 또는 모든 Level을 전수 스캔하지 않는다.
- 먼저 영속 Content Metadata를 조회하고, 다음으로 Saved/ImportReports를 조회하며, 그래도 근거가 없을 때만 대상 package, label, mismatch 범위로 좁혀 조사한다.
- canonical audit가 0 mismatch를 기록한 범위는 source snapshot 변화나 새 mismatch 증거 없이 반복 전수조사하지 않는다.
- backup/sandbox의 최신 수정 시각, negative scale, reconstructed material의 이름 차이만으로 전수조사나 일괄 재임포트를 시작하지 않는다.
- 전수조사가 불가피하면 machine-readable 상세 결과는 Metadata/Report JSON으로 보존하고 전체 의미, 수량, 신뢰도, 상세 경로와 재실행 조건을 6_SURVEY_KNOWLEDGE_BASE.md에 추가한다.
