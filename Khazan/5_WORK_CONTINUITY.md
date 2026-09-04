# 작업 연속성 및 인수인계

> 모든 새 작업은 1_PROJECT_STATE.md, 2_UE5_RULES.md, 3_ARCHITECTURE.md, 4_FMODEL_ASSET_RULES.md, 5_WORK_CONTINUITY.md를 먼저 읽고 시작한다.
> 기존 기록은 덮어쓰거나 삭제하지 않는다. 새 진행 내용은 각 문서 하단에 날짜별로 추가한다.
> 크레딧, 에디터 상태, 외부 도구 또는 환경 문제로 작업을 끝내기 어려우면 중단 전에 이 문서에 현재 상태, 마지막 성공 검증, 실패 원인, 남은 작업, 정확한 재개 명령을 남긴다.

## 2026-08-31 HeinMach 재구성 인수인계

### 현재 확정 상태

- 프로젝트: C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject
- FModel root: C:/Users/user/Desktop/카잔
- 라이브 맵: /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment
- 현재 UE: 5.8, UnrealPSKPSA 프로젝트 플러그인 활성화
- 최종 액터: 2,938개
- 일반 prop: 2,665개
- foliage: HISM 113배치, prototype 19개, instance 12,495개
- child render mesh: 15개
- fog sheet: 50개
- terrain: 2개
- source light: 89개
- preview environment: 4개
- 모든 HeinMach_Cine_*와 주인공 맨손 비틀거림·기본 이동 전용 장면은 제외 상태다.

### 완료된 복원

- CorrectedSourceAssets에 Static Mesh 183개, Material Instance 334개, Texture 955개를 source-isolated 방식으로 임포트했다.
- 일반 prop 2,665개를 source placement manifest와 정확히 일치하게 배치했다.
- placeholder 및 손상된 surface 설정을 source material reference 기준으로 복구했다.
- legacy generic actor 777개를 제거하고 terrain actor 2개를 보존했다.
- foliage 113배치를 HISM으로 이전하고 모든 instance transform baseline digest를 저장했다.
- root-only extraction에서 누락된 실제 child render component 15개를 복원했다.
- 비시네마틱 fog actor 50개를 exact transform과 sort priority로 복원했다.
- terrain 2개에 추출된 snow diffuse 기반의 reversible preview material을 적용했다.
- 단계별 backup map을 Content/_Art/Kazan/Environment/HeinMach/Maps에 보존했다.

### 마지막 검증

- 2026-08-31 18:08경 terrain 포함 통합 감사 통과.
- Unreal Editor를 정상 종료하고 새 프로세스로 재실행했다.
- 재시작 후 일반 prop 감사: placements 2,665, missing 0, transform mismatch 0, mesh mismatch 0, TwoSided mismatch 0.
- 재시작 후 foliage 감사: batches 113, instances 12,495, actor count 2,938, mesh/count/instance transform/actor transform/material mismatch 모두 0.
- 재시작 후 환경 감사: actors 2,938, populated mesh components 2,845, unique meshes 302, HISM 113/12,495, light actors 91, count match true.
- 최종 통합 감사: all_checks_passed true, categorized 2,938, uncategorized 0, duplicate labels 0, WorldGrid fog/terrain 0.
- child 최대 오차: location 0 cm, rotation 약 0.0000044도, scale 0.
- fog 최대 오차: location 0 cm, rotation 약 0.0000049도, scale 0.
- 원본 mesh orientation 감사: 190 mesh, positive 1,986,738, negative 6,597, near-zero 2, error 0.
- negative determinant actor 341개는 source mirror placement이며 reverse culling component는 0개다.

### 알려진 원본 데이터 한계

- FModel 추출물에는 57 LandscapeComponent geometry와 UV는 있지만 원본 WLM, weightmap, layer blend material graph가 없다.
- 현재 terrain snow material v1은 가역적인 시각 확인용 근사치다. 원본 terrain shader 복원이 아니다.
- fog actor parameter와 texture reference는 남아 있지만 원본 custom parent shader graph가 없다.
- 현재 fog material v3은 컴파일 검증된 one-sided translucent preview다. 원본 shader fidelity는 보장하지 않는다.
- 위 두 한계는 좌표 또는 winding 결함이 아니다. 더 정확한 복원은 원본 weightmap/WLM 또는 custom shader graph가 새로 확보될 때만 진행한다.

### 중요한 저장 및 world 규칙

- source world와 target world를 같은 Python 실행에서 넘나들며 actor/component reference를 유지하지 않는다.
- 다른 world의 결과를 main map으로 옮길 때 target map을 먼저 저장하고 에디터를 재시작한 뒤 main map을 열어 감사한다.
- dirty non-current world를 같은 실행에서 다시 load하면 저장되지 않은 actor 또는 component reference가 무효화될 수 있다.
- negative scale을 발견해도 reverse culling을 일괄 적용하지 않는다. source winding audit와 실제 material TwoSided를 먼저 확인한다.
- generated material은 compile log, WorldGrid fallback, blend mode, TwoSided, viewport를 확인한 뒤 완료 처리한다.

### 핵심 실행 스크립트

- Scripts/HeinMach/audit_heinmach_final_reconstruction.py
- Scripts/HeinMach/audit_heinmach_environment.py
- Scripts/HeinMach/audit_heinmach_placements_and_surfaces.py
- Scripts/HeinMach/audit_restored_heinmach_foliage.py
- Scripts/HeinMach/analyze_heinmach_render_gaps.py
- Scripts/HeinMach/restore_heinmach_child_render_meshes.py
- Scripts/HeinMach/restore_heinmach_fog_sheets.py
- Scripts/HeinMach/apply_heinmach_terrain_preview_material.py

### 핵심 보고서

- Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json
- Saved/ImportReports/HeinMach_Environment_Audit.json
- Saved/ImportReports/HeinMach_Placement_Surface_Audit.json
- Saved/ImportReports/HeinMach_Foliage_Reload_Audit.json
- Saved/ImportReports/HeinMach_Foliage_Transform_Baseline.json
- Saved/ImportReports/HeinMach_FModel_MeshOrientation_Audit.json
- Saved/ImportReports/HeinMach_Render_Gap_Analysis.json
- Saved/ImportReports/HeinMach_Child_Render_Restore.json
- Saved/ImportReports/HeinMach_FogSheet_Restore.json
- Saved/ImportReports/HeinMach_Terrain_Preview_Material.json

### 다음 재개 절차

1. 핵심 문서 1–5를 읽는다.
2. 라이브 맵 L_HeinMach_Environment를 연다.
3. audit_heinmach_final_reconstruction.py를 먼저 실행한다.
4. 좌표나 surface 회귀가 의심되면 placement audit와 foliage reload audit를 추가 실행한다.
5. all_checks_passed가 false이면 report의 mismatch 목록만 조사하고 정상 asset을 다시 일괄 임포트하지 않는다.
6. 원본 WLM/weightmap 또는 fog parent shader graph가 새로 확보되지 않았다면 terrain/fog preview를 원본 복원으로 과장하지 않는다.

## 2026-08-31 완성 Level과 조사 재사용 갱신

- 완성본은 /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment다.
- Before*, L_HeinMach_Environment_LightingOnly, L_HeinMach_FoliageImportSandbox는 완성본으로 사용하지 않는다.
- 기존 전수조사 및 metadata/report 인덱스는 6_SURVEY_KNOWLEDGE_BASE.md에 있다.
- 이후 재개 절차의 첫 단계는 프로젝트 문서 1–6 확인이다.
- 필요한 정보는 6번 문서의 질문별 조회표와 canonical JSON에서 먼저 찾고, source 변경 또는 실제 mismatch가 있을 때만 좁은 재조사 또는 전수조사를 수행한다.
- 불가피한 전수조사가 끝나기 전 6번 문서에 조사 범위, 결과, 상세 데이터 경로와 재조사 조건을 반드시 추가한다.

## 2026-08-31 DevMap PIE 크래시 인수인계

- 진단 결과와 정확한 시그니처는 `7_RUNTIME_CRASH_DIAGNOSTICS.md`가 canonical 기록이다.
- 현재 직접 실패 값은 `UKhazanAssetManager::LoadedAssetData == nullptr`이며 호출 위치는 `KhazanAssetManager.h:57`, 진입 위치는 `KhazanPlayerController.cpp:36`이다.
- 원인은 `DefaultEngine.ini`에 `GameInstanceClass`가 없어 `UKhazanGameInstance::Init()`이 실행되지 않는 것이다.
- 이번 조사에서는 C++과 Config를 수정하지 않았다.
- 재개 시 먼저 `GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C`를 적용하고 Editor를 완전 재시작해 DevMap PIE와 Standalone을 검증한다.
- 즉시 복구 뒤에는 AssetManager의 `StartInitialLoading()` 기반 초기화와 AssetData/Input/Pawn null 방어를 별도 변경으로 진행한다.
- 앞으로 모든 작업의 선행 문서 확인 범위는 1–7이다.
