# 전수조사 지식 베이스

> 목적: 이미 조사한 대상을 다시 전수 스캔하지 않도록 조사 범위, 확정 결과, 상세 메타데이터 위치, 신뢰도와 재조사 조건을 한곳에 기록한다.
> 모든 작업은 프로젝트 문서 1–6을 먼저 읽고, 이 문서의 질문별 조회표와 기존 JSON 보고서를 확인한 뒤 필요한 최소 범위만 조사한다.
> 대용량 row-level 데이터는 중복해서 Markdown에 복사하지 않는다. 이 문서에는 전체 의미, 수량, 스키마, 신뢰도와 정확한 JSON 경로를 남기며 개별 record는 지정된 JSON을 조회한다.

## 조회 우선순위

1. 1_PROJECT_STATE.md부터 6_SURVEY_KNOWLEDGE_BASE.md까지 확인한다.
2. 이 문서의 질문별 우선 조회표에서 이미 조사된 결과를 찾는다.
3. Content의 영속 Metadata JSON을 조회한다.
4. Saved/ImportReports의 해당 범위 보고서를 조회한다.
5. 기존 보고서를 만든 audit/analyze 스크립트로 필요한 범위만 재검증한다.
6. 위 자료가 없거나 source snapshot이 달라졌을 때만 전수조사를 수행한다.

파일명 유사도나 기억에 의존해 전수조사하지 않는다. 기존 보고서의 mismatch 목록이 있으면 그 목록만 대상으로 좁힌다.

## 완성본 Level

사용해야 할 완성본은 다음 하나다.

- 패키지: /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment
- 파일: Content/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment.umap
- 역할: HeinMach 환경 재구성 live/final map
- 마지막 확정 감사: Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json
- 감사 결과: audited, all_checks_passed=true, 26개 check 전부 통과
- 최종 구성: actor 2,938, prop 2,665, foliage batch 113, HISM instance 12,495, child render 15, fog 50, terrain 2, source light 89, preview environment 4
- 재시작 검증: Unreal Editor 정상 종료 후 다시 열어 placement, foliage, environment, final audit를 재실행해 통과

맵 파일 수정 시각이나 파일 크기가 더 최신이라는 이유로 다른 맵을 완성본으로 판단하지 않는다. 완성 여부는 위 패키지 경로와 Final Reconstruction Audit 결과로 판단한다.

## Maps 폴더 Level 용도

| Level | 용도 | 완성본 여부 |
| --- | --- | --- |
| L_HeinMach_Environment | 현재 live 재구성 맵. 모든 후속 수정과 검증 대상 | 예 |
| L_HeinMach_Environment_BeforeReconstruction | corrected 재구성 전 롤백 지점 | 아니오 |
| L_HeinMach_Environment_PreSurfaceFix | source-isolated mesh 및 surface 수정 전 롤백 지점 | 아니오 |
| L_HeinMach_Environment_BeforeLegacyCleanup | 잘못 생성된 generic actor 777개 정리 전 | 아니오 |
| L_HeinMach_Environment_BeforeFoliageRestore | HISM foliage 113배치 이전 전 | 아니오 |
| L_HeinMach_Environment_BeforeChildRenderRestore | 비루트 child render mesh 15개 복원 전 | 아니오 |
| L_HeinMach_Environment_BeforeFogSheetRestore | fog sheet 50개 복원 전 | 아니오 |
| L_HeinMach_Environment_BeforeTerrainPreviewMaterial | terrain preview material 적용 전 | 아니오 |
| L_HeinMach_Environment_LightingOnly | 조명만 확인하기 위한 staging/reference 맵 | 아니오 |
| L_HeinMach_FoliageImportSandbox | PointInstancer/HISM 임포트와 이전 검증용 sandbox | 아니오 |

2026-08-31 확인 당시 main map 파일은 10,325,423 bytes, 최종 저장 시각은 18:16:38이었다. 이 값은 무결성 판단 기준이 아니라 당시 snapshot이다.

## 조사 Snapshot

### FModel 전체 추출물

- root: C:/Users/user/Desktop/카잔
- snapshot 날짜: 2026-08-31
- PNG 4,347
- JSON 1,988
- FBX 544
- PSA 528
- USDA 210
- HDR 66
- UEXP 50
- UMAP 34
- PSK 21
- UASSET 16
- 이 수량은 새 추출물이 추가되면 달라질 수 있다. 단일 파일을 찾는 작업에 전체 root를 다시 세지 말고 4_FMODEL_ASSET_RULES.md의 경로와 naming 규칙부터 사용한다.

### HeinMach source 분석

- 분석 생성 시각: 2026-08-31T12:23:55.340023+09:00
- source world JSON: 35
- parsed world JSON: 35
- parse error: 0
- level summary: 35
- streaming level record: 29
- 전체 actor placement metadata: 11,065
- actor type: 592종
- template package: 410
- renderable StaticMesh placement candidate: 2,782
- live map에서 검증된 일반 root prop placement: 2,665
- 2,782는 분석 후보 수이며 live map의 기대 prop 수로 사용하지 않는다. 현재 live 기대값은 2,665다.

### Source reference graph

- material reference: 177
- other reference: 132
- skeletal mesh reference: 27
- static mesh reference: 212
- template reference: 402
- texture reference: 97
- USD file: 561
- USD reference: 1,252
- unique USD reference: 751
- missing USD reference: 0

### 원본 dump에서 확인된 비지오메트리 메타데이터

- player respawn point: 10
- monster spawn: 47
- other spawn handler: 161
- light metadata: 97
- reflection capture: 5
- environment controller: 17
- 이 수치는 원본 전체 메타데이터다. 현재 환경-only live map은 gameplay spawn과 cinematic을 제외하며 source light actor 89개를 사용한다.

### 원본 export gap

- JSON parse error: 0
- USD missing reference: 0
- properties JSON이 없는 template package: 33
- exported file이 없는 package: material 79, other 131, skeletal mesh 26, static mesh 0, template 42, texture 97
- 위 항목은 FModel dump의 보조 export 부재를 뜻하며 live map에서 같은 수의 에셋이 누락되었다는 뜻은 아니다.

## 영속 Metadata 카탈로그

모든 경로의 기준 root는 Content/_Art/Kazan/Environment/HeinMach/Metadata다.

| 파일 | 포함 정보 | 현재 수량/상태 | 우선 사용처 |
| --- | --- | --- | --- |
| HeinMach_AssetManifest.json | 35개 level 요약, actor type, template package, asset reference, USD graph | placement 11,065, USD missing 0 | source 종류, package/reference 존재 여부 |
| HeinMach_EnvironmentPlacements.json | 모든 source actor의 Unreal 좌표 transform 및 actor/component 정보 | placement 11,065 | 특정 source actor, transform, component 조회 |
| HeinMach_LevelData.json | 좌표계, streaming level, spawn, light, reflection, environment controller | JSON 유효, parse error 0 | 레벨 구조와 비지오메트리 메타데이터 |
| HeinMach_MissingAssets.json | parse/reference/export gap | parse 0, USD missing 0, template JSON gap 33 | source dump 부재 여부 판정 |
| HeinMach_RenderableStaticMeshPlacements.json | renderable StaticMesh 후보와 source reference/transform | candidate 2,782 | 일반 prop 후보 조회. live 기대값은 import/audit의 2,665 사용 |

좌표 규칙:

- JSON transform은 Unreal Engine centimeters, Z-up의 원본 좌표다.
- FModel USDA는 USD 좌표 표현을 위해 Unreal Y를 반전한다.
- JSON transform을 사용하면서 Y를 다시 반전하면 좌표가 틀어진다.

## 현재 포함/제외 범위

환경 재구성에서 조사·사용한 level 계열:

- HeinMach_Chrcollision
- HeinMach_Landscape1
- HeinMach_Landscape2
- HeinMach_SubLV01_OP
- HeinMach_SubLV02_Blizzard
- HeinMach_SubLV02_Blizzard_1
- HeinMach_SubLV02_Blizzard_2
- HeinMach_SubLV02_CaveEntry
- HeinMach_SubLV03_Cave
- HeinMach_SubLV03_Cave_1
- HeinMach_SubLV03_Cave_2
- HeinMach_SubLV04_Waterfall
- HeinMach_SubLV04_WaterfallUp
- HeinMach_SubLV04_WaterfallUp_1
- HeinMach_SubLV05_Escape
- HeinMach_SubLV05_Escape_1
- HeinMach_SubLV06_Boss
- HeinMach_SubLV07_BG

제외:

- 모든 HeinMach_Cine_*
- 주인공 맨손 비틀거림·기본 이동 전용 장면
- Spawn_Main01
- Sound
- BGM
- POS
- MoveCustomSpline
- Precache와 캐릭터/게임플레이 전용 레이어

## 완료된 전수·정밀 조사 결과

### Corrected Static Mesh와 배치

- source USDA 183개를 독립 source로 취급했다.
- 결과: Static Mesh 183, Material Instance 334, Texture 955.
- USD asset sharing과 material-slot merging을 끈 corrected library가 canonical이다.
- 일반 prop 2,665개는 source manifest와 비교해 missing 0, unexpected 0, mesh mismatch 0, transform mismatch 0이다.
- 첫 StaticMesh_Reconstruction 결과는 공유/병합 문제가 있었으므로 Corrected 보고서로 대체되었다.

### Material과 surface

- unique material requirement 332.
- material assignment 332.
- Masked 기대 assignment 331, mismatch 0.
- TwoSided 기대 assignment 112, mismatch 0.
- source override target 294, 최종 override mismatch 0.
- source TwoSided slot observation 713, mismatch 0.
- placement audit의 mesh_slot_mismatch_count 108 및 slot-count mismatch 3은 source material basename과 재구성 MI 이름을 단순 비교한 진단값이다.
- 위 이름 진단값만으로 재임포트하지 않는다. canonical 판정은 override validation 0, Masked/TwoSided mismatch 0, 실제 binding과 WorldGrid 여부다.

### Foliage

- source level 15개에서 PointInstancer batch 113개를 확인했다.
- prototype 19개.
- instance 12,495개.
- HISM batch 113개로 복원했다.
- baseline과 reload audit에서 mesh/count/instance world transform/actor transform/material mismatch가 모두 0이다.
- foliage를 개별 actor로 전개하거나 source 전체를 다시 검색하지 말고 Transform Baseline과 Reload Audit를 먼저 사용한다.

### 비루트 render component

- visible non-root StaticMeshComponent: 128.
- foliage PointInstancer 관련: 113.
- 실제 child render mesh: 15.
- child 구성: table 9, carriage break 5, bridge 1.
- child용 source mesh: 3.
- 최종 child transform, mesh, override material mismatch 0.

### Fog

- 비시네마틱 WBP_FogSheet_C: 50.
- 분포: SubLV01_OP 14, SubLV03_Cave 4, SubLV03_Cave_1 1, SubLV04_Waterfall 1, SubLV04_WaterfallUp 2, SubLV04_WaterfallUp_1 1, SubLV05_Escape 1, SubLV06_Boss 6, SubLV07_BG 20.
- actor transform, sort priority, mesh, material instance parent mismatch 0.
- 원본 custom fog parent shader graph는 추출되지 않았다.
- 현재 one-sided translucent preview material v3는 컴파일되고 WorldGrid fallback이 없다.

### Terrain

- Landscape1 component 18.
- Landscape2 component 39.
- 합계 57.
- geometry, normals, tangents, UV0/UV1은 존재한다.
- 원본 WLM, weightmap, layer blend graph는 없다.
- live terrain actor는 HM_Terrain_Landscape1과 HM_Terrain_Landscape2 두 개다.
- snow diffuse 기반 preview material v1 적용, material mismatch 0, WorldGrid 0.
- 원본 지형 shader 복원 여부를 판단하기 위해 57개 component를 다시 전수조사하지 않는다. 새 WLM/weightmap이 확보되었는지만 확인한다.

### Winding과 culling

- 원본 mesh audit: 190.
- positive triangle 1,986,738.
- negative triangle 6,597.
- near-zero 2.
- parser error 0.
- 전체 winding이 뒤집힌 mesh는 없다.
- negative determinant live actor 341.
- reverse_culling component 0.
- vegetation의 mixed winding은 authored TwoSided 구조가 포함된다.
- negative scale만 보고 mesh를 뒤집거나 reverse culling을 일괄 적용하지 않는다.

### 최종 live map

- actor total 2,938.
- categorized 2,938.
- uncategorized 0.
- duplicate label 0.
- populated StaticMesh component 2,845.
- unique used StaticMesh 302.
- HISM 113 / instance 12,495.
- environment audit의 light actor class 수 91.
- inventory 분류의 source light 89와 preview environment 4는 역할 기준 분류이며, preview 4개 중 일부만 Light class이므로 두 수치를 단순 합산해 light class 수로 사용하지 않는다.
- 최종 integrated check 26/26 통과.

## Saved 보고서 카탈로그

Saved/ImportReports는 생성 가능한 상세 감사 결과다. 파일이 존재하면 source 전체보다 먼저 읽는다.

| 보고서 | 지위 | 핵심 내용 |
| --- | --- | --- |
| HeinMach_Final_Reconstruction_Audit.json | 최우선 canonical | live map 경로, 2,938 inventory, child/fog/terrain/HISM/culling 26 checks |
| HeinMach_Environment_Audit.json | canonical | actor/component/unique mesh/HISM/light class 요약 |
| HeinMach_Placement_Surface_Audit.json | canonical | prop 2,665 transform/mesh, surface, override, culling |
| HeinMach_StaticMesh_Reconstruction_Corrected.json | canonical | source 183, placement 2,665, SM 183/MI 334/Texture 955 |
| HeinMach_Material_Surface_Repair.json | canonical | Masked/TwoSided 요구와 repair 결과 |
| HeinMach_Override_Material_Reconstruction.json | canonical | override target 294, unresolved 0 |
| HeinMach_Foliage_Reload_Audit.json | canonical | 재시작 후 HISM와 instance transform 검증 |
| HeinMach_Foliage_Transform_Baseline.json | canonical baseline | batch 113, instance 12,495 world transform digest |
| HeinMach_Foliage_Batch_Restore.json | canonical transfer record | sandbox에서 main map으로 이전한 상세 |
| HeinMach_Render_Gap_Analysis.json | canonical | non-root 128, child 15, fog 50, gap mesh orientation |
| HeinMach_Child_Render_Restore.json | canonical | child 15 복원과 material assignment |
| HeinMach_FogSheet_Restore.json | canonical preview record | fog 50, preview version 3 |
| HeinMach_Terrain_Preview_Material.json | canonical preview record | terrain 2, 57 component source 한계, preview version 1 |
| HeinMach_FModel_MeshOrientation_Audit.json | canonical | source mesh 190 winding 전체 결과 |
| HeinMach_Legacy_Actor_Cleanup.json | 단계 기록 | generic actor 777 제거, 당시 actor 2,760 |
| HeinMach_Foliage_Batch_Import.json | 단계 기록 | sandbox batch 113/instance 12,495 import |
| HeinMach_Foliage_Instance_Probe.json | 진단 기록 | foliage component 113/instance 12,495 probe |
| HeinMach_UE_Material_Metadata_Probe.json | 진단 기록 | UE material property 접근 가능성 조사 |
| HeinMach_UE_MeshOrientation_Probe.json | 진단 기록 | UE mesh orientation API 조사 |
| HeinMach_Environment_Reconstruction.json | 중간 상태 | 당시 2,873 actor. child/fog 추가 전이므로 현재 기대값으로 사용 금지 |
| HeinMach_Environment_Import.json | superseded | 초기 22 mesh 중심 import. corrected reconstruction 이전 |
| HeinMach_StaticMesh_Reconstruction.json | superseded | asset sharing/slot merging 문제가 있던 첫 reconstruction |

## 질문별 우선 조회표

| 필요한 정보 | 가장 먼저 볼 파일 | 다음 단계 |
| --- | --- | --- |
| 어떤 Level이 완성본인가 | 이 문서의 완성본 Level 섹션 | Final Reconstruction Audit의 map_path 확인 |
| 특정 source actor나 transform | HeinMach_EnvironmentPlacements.json | source level/actor/component key로 부분 검색 |
| live 일반 prop 위치/메시 | Placement Surface Audit | mismatch가 있을 때만 Renderable Placements의 해당 label 확인 |
| 메시·머티리얼·텍스처 source 수 | StaticMesh Reconstruction Corrected | 해당 source package만 조회 |
| 머티리얼 TwoSided/Masked | Material Surface Repair | Override Material Reconstruction |
| foliage 위치 | Foliage Transform Baseline | Reload Audit의 mismatch batch만 조회 |
| 누락된 자식 메시 | Render Gap Analysis | Child Render Restore |
| fog 수와 위치 | Render Gap Analysis의 fog_sheet_actors | FogSheet Restore |
| terrain 구조 | Terrain Preview Material report | 새 WLM/weightmap 존재 여부만 확인 |
| winding/뒤집힘 | FModel MeshOrientation Audit | 의심 mesh 하나만 targeted probe |
| 원본 package/reference 존재 여부 | HeinMach_AssetManifest.json | MissingAssets.json |
| spawn/light/streaming 구조 | HeinMach_LevelData.json | 필요한 record만 package/object path로 검색 |
| 에셋 naming/path 규칙 | 4_FMODEL_ASSET_RULES.md | AssetManifest에서 특정 package 확인 |
| 중단된 작업 상태 | 5_WORK_CONTINUITY.md | 해당 canonical report 확인 |

## 전수조사 재실행 조건

다음 중 하나일 때만 전수조사를 허용한다.

- FModel root에 새 추출물이 추가되거나 기존 source가 교체되었다.
- Metadata schema/version이 바뀌어 기존 결과를 신뢰할 수 없다.
- canonical JSON이 없거나 파손되었고 좁은 범위 재생성으로 복구할 수 없다.
- targeted audit가 실제 mismatch 목록을 만들었고 공통 원인을 특정할 수 없다.
- 사용자가 명시적으로 새 전체 snapshot을 요구했다.

다음은 전수조사 조건이 아니다.

- viewport에서 어둡거나 다른 camera angle로 보인다.
- backup 또는 sandbox 파일의 수정 시각이 더 최신이다.
- negative scale actor가 있다.
- source material명과 reconstructed MI명이 다르다.
- 이미 canonical audit가 0 mismatch를 기록한 범위가 단순히 기억나지 않는다.

## 불가피한 전수조사 기록 형식

전수조사를 수행했다면 작업을 종료하기 전에 이 문서 하단에 다음을 모두 추가한다.

- 조사 날짜와 목적
- source root와 포함/제외 범위
- source snapshot 수량 또는 변경 fingerprint
- 사용한 script와 정확한 command/entry point
- 생성한 영속 Metadata JSON 경로
- 생성한 상세 report 경로
- 총 수량, 분류별 수량, 오류와 미확정 항목
- 기존 조사 중 무엇을 대체하는지
- 다시 조사해야 하는 명시적 조건
- 후속 작업자가 먼저 사용할 key, label, package path

대규모 record는 Content Metadata 또는 Saved report에 JSON으로 보존하고, 이 문서에는 그 파일의 스키마·수량·결론·신뢰도·재조사 조건을 반드시 남긴다.

## 기존 Character/ActorX 조사 인덱스

- ActorX importer: 프로젝트 로컬 Plugins/UnrealPSKPSA
- 자동 import entry point: Scripts/import_fmodel_psk.py
- FModel source: C:/Users/user/Desktop/카잔/BBQ/Content/_Kazan_/Art/Character/CHA_Model
- UE destination: /Game/_Art/Kazan/FModel/PSK
- PSK source/import 수: 21
- import 실패: 0
- 21개 모두 Skeletal Mesh와 Skeleton이 유효함을 재검증했다.
- 카잔 base source mesh는 C_P_Kazan.psk이며 UE 조립 base는 /Game/_Art/Kazan/Character/Meshs/SKM_Khazan이다.
- 외형은 Arm, Face, Hair, Leg, Shoes, Torso의 독립 파츠와 의상/상태 variant로 나뉜다.
- PSA total: 528.
- PSA 경로 분포: DualAxeSword 직속 417, Normal 70, Style/Flow 29, Animation root 10, Style/Yaksha 2.
- PSA prefix 분포: CA_P_Kazan 512, CA_PC_Kazan 9, CA_I_Axe 4, CA_Kazan_DualAxeSword 2, Pose_Kazan_NonCombat 1.
- naming, 파츠 분할, material/texture channel의 상세 규칙은 4_FMODEL_ASSET_RULES.md가 canonical summary다.
- source PSK/PSA 파일 집합이 바뀌지 않았다면 같은 수량과 이름 분포를 다시 전수 집계하지 않는다.
