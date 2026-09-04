# 프로젝트 아키텍처

> 모든 작업 시작 전에 프로젝트 핵심 문서 3개를 확인한다. 구조 변경은 기존 내용을 덮어쓰지 않고 이 문서 하단에 추가한다.

## 2026-08-31 기준

### 환경과 소스

- UE 프로젝트: `C:\Users\user\Desktop\GitProject\Khazan\Khazan\Khazan.uproject`
- Unreal Engine 연결 버전: UE 5.8
- FModel 추출 루트: `C:\Users\user\Desktop\카잔`
- HeinMach 속성 JSON: `C:\Users\user\Desktop\카잔\Exports\BBQ\Content\_Kazan_\Level\HeinMach`
- HeinMach 분석 스크립트: `Scripts/HeinMach/analyze_heinmach.py`
- HeinMach 메타데이터: `/Game/_Art/Kazan/Environment/HeinMach/Metadata`

### 런타임 클래스와 Blueprint

- 플레이어 컨트롤러 C++: `AKhazanPlayerController`
- 플레이어 컨트롤러 Blueprint: `/Game/Bluprints/BP_KhazanPlayerController`
- 캐릭터 C++: `AKhazanCharacter`
- 캐릭터 Blueprint: `/Game/Bluprints/BP_KhazanCharacter`
- 게임 모드 C++: `AKhazanGameMode`
- 게임 모드 Blueprint: `/Game/Bluprints/BP_GameMode`
- 에셋 데이터: `UKhazanAssetData`, `/Game/Data/PDA_AssetData`

### 카잔 캐릭터 에셋 구조

- 베이스 Skeletal Mesh: `/Game/_Art/Kazan/Character/Meshs/SKM_Khazan`
- 베이스 Skeleton: `/Game/_Art/Kazan/Character/Meshs/SK_Khazan`
- 모듈 파츠: `Torso`, `Shoes`, `Hair`, `Arm`, `Leg`, `Face`
- 동기화 방식: 각 파츠의 Skeletal Mesh Component가 `SKM_Khazan` 컴포넌트를 Leader Pose Component로 사용한다.

### HeinMach 파이프라인

- 입력: FModel의 레벨 JSON, 메시, 머티리얼 JSON, 텍스처 파일
- 분석 산출물: `Content/_Art/Kazan/Environment/HeinMach/Metadata/*.json`
- 예정 출력: `/Game/_Art/Kazan/Environment/HeinMach` 아래의 임포트 에셋과 재구성 레벨
- 제외 범위: 주인공 맨손 비틀거림·기본 이동 전용 장면

## 2026-08-31 임포트 구조 추가

### ActorX PSK/PSA

- 프로젝트 플러그인: `Plugins/UnrealPSKPSA`
- 업스트림 고정 정보: `Plugins/UnrealPSKPSA/UPSTREAM.md`
- PSK 자동 임포트: `Scripts/import_fmodel_psk.py`
- FModel PSK 입력: `C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Art\Character\CHA_Model`
- UE 출력: `/Game/_Art/Kazan/FModel/PSK`
- 현재 결과: PSK 21개, 실패 0개

### HeinMach 환경 재구성

- USD 입력: `C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Level\HeinMach`
- 환경 임포트: `Scripts/HeinMach/import_heinmach_environment.py`
- 임포트 에셋: `/Game/_Art/Kazan/Environment/HeinMach/Imported/HeinMach_EnvironmentOnly`
- 재구성 맵: `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`
- 구성: 환경 USD 19개, Actor 818개, Static Mesh 22개, Material Instance 22개, Texture 45개
- 머티리얼 연결: 22개 Static Mesh 전체에 유효한 머티리얼 슬롯이 연결되어 있다.
- 제외 입력: 모든 `HeinMach_Cine_*`, 캐릭터, 스폰, 사운드, BGM, POS, MoveCustomSpline, Precache 레이어

## 2026-08-31 FModel 에셋 규칙 문서

- 네이밍·경로·정리·메시 분할 기준: `4_FMODEL_ASSET_RULES.md`
- FModel 에셋의 정식 source key는 basename이 아니라 원본 마운트, 상대 package path, object명을 함께 사용한다.
- 런타임 조회는 `UKhazanAssetManager`와 `UKhazanAssetData`의 Gameplay Tag 기반 `AssetName`을 사용하고, 원본 이름과 경로는 provenance/metadata로 별도 보존한다.

## 2026-08-31 HeinMach 최종 재구성 구조

### 라이브 맵과 에셋 루트

- 라이브 맵: /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment
- corrected source library: /Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets
- override material library: /Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials
- foliage library: /Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FoliageBatches
- foliage import sandbox: /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_FoliageImportSandbox
- child render library: /Game/_Art/Kazan/Environment/HeinMach/Reconstructed/ChildRenderAssets
- fog library: /Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FogSheets
- terrain preview library: /Game/_Art/Kazan/Environment/HeinMach/Reconstructed/TerrainPreview
- placement metadata: Content/_Art/Kazan/Environment/HeinMach/Metadata/HeinMach_RenderableStaticMeshPlacements.json

### 라이브 맵 액터 구조

- HeinMach/Reconstructed/Props: HM_Prop_ prefix 2,665개
- HeinMach/Reconstructed/FoliageBatches: HM_FoliageBatch_ prefix HISM actor 113개, instance 12,495개
- HeinMach/Reconstructed/ChildRender: 비루트 child actor 15개
- HeinMach/Reconstructed/FogSheets: fog actor 50개
- terrain: HM_Terrain_Landscape1, HM_Terrain_Landscape2
- source light actor 89개
- preview environment actor 4개
- 최종 합계: 2,938개, 분류 누락 0개

### 복구 지점

- L_HeinMach_Environment_BeforeReconstruction
- L_HeinMach_Environment_PreSurfaceFix
- L_HeinMach_Environment_BeforeLegacyCleanup
- L_HeinMach_Environment_BeforeFoliageRestore
- L_HeinMach_Environment_BeforeChildRenderRestore
- L_HeinMach_Environment_BeforeFogSheetRestore
- L_HeinMach_Environment_BeforeTerrainPreviewMaterial
- L_HeinMach_Environment_LightingOnly
- L_HeinMach_FoliageImportSandbox

### 주요 자동화와 감사

- source 분석: Scripts/HeinMach/analyze_heinmach.py
- corrected mesh/placement: Scripts/HeinMach/import_heinmach_static_meshes.py
- surface material: Scripts/HeinMach/repair_heinmach_materials.py
- foliage import/restore/audit: import_heinmach_foliage_batches.py, restore_heinmach_foliage_batches.py, audit_restored_heinmach_foliage.py
- 누락 렌더 분석/복원: analyze_heinmach_render_gaps.py, restore_heinmach_child_render_meshes.py, restore_heinmach_fog_sheets.py
- 지형 preview: apply_heinmach_terrain_preview_material.py
- 최종 통합 감사: audit_heinmach_final_reconstruction.py
- 환경 요약 감사: audit_heinmach_environment.py
- 일반 prop transform/surface 감사: audit_heinmach_placements_and_surfaces.py

### 최종 보고서

- Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json
- Saved/ImportReports/HeinMach_Environment_Audit.json
- Saved/ImportReports/HeinMach_Placement_Surface_Audit.json
- Saved/ImportReports/HeinMach_Foliage_Reload_Audit.json
- Saved/ImportReports/HeinMach_Render_Gap_Analysis.json
- Saved/ImportReports/HeinMach_Child_Render_Restore.json
- Saved/ImportReports/HeinMach_FogSheet_Restore.json
- Saved/ImportReports/HeinMach_Terrain_Preview_Material.json
- Saved/ImportReports/HeinMach_FModel_MeshOrientation_Audit.json

## 2026-08-31 조사 정보 계층

- 조사 지식 인덱스: 6_SURVEY_KNOWLEDGE_BASE.md
- 완성 Level: /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment
- 영속 source metadata: Content/_Art/Kazan/Environment/HeinMach/Metadata
- 생성 가능한 상세 audit: Saved/ImportReports
- source 분석 entry point: Scripts/HeinMach/analyze_heinmach.py
- live map 최종 검증 entry point: Scripts/HeinMach/audit_heinmach_final_reconstruction.py
- Before* map은 단계별 rollback, LightingOnly는 조명 staging, FoliageImportSandbox는 HISM import staging이다.
- 대규모 row-level 데이터는 JSON을 canonical detail로 유지하고 Markdown은 발견 내용, 수량, 경로, 신뢰도와 재조사 조건을 제공한다.
