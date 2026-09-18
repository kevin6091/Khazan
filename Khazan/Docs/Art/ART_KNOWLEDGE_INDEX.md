# Art / Resource 지식 인덱스

> 상세 레코드는 기존 metadata와 Saved report를 재사용한다. 이 문서는 질문별 첫 조회 위치만 유지한다.

| 필요한 정보 | 첫 조회 위치 | 다음 조회 |
| --- | --- | --- |
| FModel naming, path, 캐릭터 메시 분할 | `4_FMODEL_ASSET_RULES.md` | 해당 source package만 표적 확인 |
| HeinMach 완성 Level과 전체 수량 | `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json` | `6_SURVEY_KNOWLEDGE_BASE.md` |
| 일반 prop transform·mesh·surface | `Saved/ImportReports/HeinMach_Placement_Surface_Audit.json` | `HeinMach_EnvironmentPlacements.json`의 해당 label |
| source mesh/material/texture 대응 | `Saved/ImportReports/HeinMach_StaticMesh_Reconstruction_Corrected.json` | 해당 package만 확인 |
| foliage instance transform | `Saved/ImportReports/HeinMach_Foliage_Transform_Baseline.json` | Reload Audit의 mismatch batch |
| child render·fog 누락 | `Saved/ImportReports/HeinMach_Render_Gap_Analysis.json` | Child/Fog restore report |
| terrain preview와 원본 제약 | `Saved/ImportReports/HeinMach_Terrain_Preview_Material.json` | source WLM/weightmap 존재 여부만 확인 |
| winding·뒤집힘 | `Saved/ImportReports/HeinMach_FModel_MeshOrientation_Audit.json` | 문제 mesh 하나만 targeted probe |
| FModel package/reference 존재 | `Content/_Art/Kazan/Environment/HeinMach/Metadata/HeinMach_AssetManifest.json` | MissingAssets JSON |

## 전수조사 허용 조건

- FModel source snapshot이 추가·교체되었다.
- metadata schema가 바뀌어 기존 report를 신뢰할 수 없다.
- canonical report가 없거나 손상되었고 표적 재생성이 불가능하다.
- targeted audit가 실제 mismatch 목록을 만들었지만 공통 원인을 특정할 수 없다.

불가피한 전수조사 후에는 source snapshot, 포함/제외 범위, script, 결과 수량, 오류, 상세 JSON 경로, 기존 조사 대체 관계와 재조사 조건을 이 문서 하단에 추가한다.

## 2026-09-01 우선 조회표

| 필요한 정보 | 첫 조회 위치 | 판정 기준 |
| --- | --- | --- |
| 최신 완성본과 전체 수량 | `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json` | actor 9,449, uncategorized 0, 31/31 |
| 비-Fog 정적 메시 누락 여부 | `Saved/ImportReports/HeinMach_StaticCoverage_Closure_Audit.json` | unresolved non-Fog root StaticMesh 0 |
| root Prop 원본 좌표·mesh·material | `Saved/ImportReports/HeinMach_RestoredLevel_Integrity_Audit.json` | managed 9,104, failures `{}` |
| child StaticMesh direct/inherited | `Saved/ImportReports/HeinMach_ChildRender_Integrity_Audit.json` | 15+12=27, failures `{}` |
| Landscape exact geometry proxy | `Saved/ImportReports/HeinMach_LandscapeStatic_Integrity_Audit.json` | 18+39=57, bounds/placement failure 0 |
| foliage | `Saved/ImportReports/HeinMach_Foliage_Reload_Audit.json` | 113 batch, 12,495 instance, mismatch 0 |
| packed channel·blend·TwoSided | `Saved/ImportReports/HeinMach_MaterialRendering_Audit.json` | 613 MI, packed correct 583, effective Translucent 0 |
| alpha surface 수정 provenance | `Saved/ImportReports/HeinMach_AlphaSurfacePolicy_Repair.json` | source JSON 17종, target 29, unresolved/failure 0 |
| PlayerStart 카메라 좌표 | `Saved/ImportReports/HeinMach_PlayableCameraAnchors.json` | source-facing route camera 6개 |
| 실제 viewport 검수 증거 | `Saved/ImportReports/HeinMach_VisualRoute_Audit.json` | 대표 6지점 screenshot 및 SHA-256 |
| preview lighting | `Saved/ImportReports/HeinMach_PreviewLighting_Calibration.json` | source light 89 보존, route fill 3 |

## 조사 메타데이터 해석

- `HeinMach_RootTemplateCoverage_Audit.json`의 unresolved root 694개는 정적 Prop 누락 694개가 아니다.
- unresolved root component 분류는 Brush 272, Billboard 142, Scene 103, SplineVolume 90, StaticMesh 50, Capsule 16, Skeletal 11, RuntimeVirtualTexture 4, Decal 3, VirtualHeightfield 2, Box 1이다.
- StaticMesh 50개는 모두 Fog이며 이번 작업 경계 밖이다. 비-Fog root StaticMesh unresolved는 0개다.
- child template audit는 local non-root component 5,649개 중 실제 visible/non-foliage/non-fog StaticMesh 27개를 해석했으며 unresolved 0개다.
- source snapshot이나 schema가 바뀌지 않는 한 위 closure report가 root/child 정적 메시 전수조사를 대체한다.
- dynamic skeletal prop, decal, gameplay spawner/volume, VFX는 정적 메시 좌표 누락과 분리해 별도 요청에서 다룬다.

## 2026-09-02 Fog / Lighting 우선 조회표

| 필요한 정보 | 첫 조회 위치 | 판정 기준 |
| --- | --- | --- |
| 최신 전체 Level 상태 | `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json` | actor 9,452, uncategorized 0, 35/35 |
| Fog v4와 source parameter | `Saved/ImportReports/HeinMach_FogLighting_Polish.json` | MI 50, transform hash 동일, material version 4 |
| source light와 route fill | `HeinMach_FogLighting_Polish.json` | source 89/hash 동일, route fill 5 |
| Volumetric Fog | `HeinMach_FogLighting_Polish.json`의 `volumetric_fog` | preview 1, volumetric enabled |
| 노출과 Lumen | 같은 report의 `post_process` | EV100 0–14, bias -0.25, Lumen 설정값 일치 |
| root Prop 좌표 회귀 | `HeinMach_RestoredLevel_Integrity_Audit.json` | managed 9,104, failures `{}` |
| Landscape 좌표/경계 | `HeinMach_LandscapeStatic_Integrity_Audit.json` | 18+39=57, failure 0 |
| 안전한 시각 참고 | `Saved/Screenshots/WindowsEditor/RiderMCP/20260902-053101_editor_window.png` | 동굴 노출 참고용; 정본은 report/log |

- `HeinMach_Final_Reconstruction_Audit.json`의 `all_checks_passed=true`가 최신 완료 판정이다.
- map load 직후 일시적으로 9,447개가 조회된 사례는 actor 등록 완료 후 9,452개로 정상화됐다. 이 수량만으로 FModel 전수조사를 시작하지 않는다.
- 좌표 이탈 1개는 표적 감사로 발견·복구했으며 이후 `HeinMach_RestoredLevel_Integrity_Audit.json`이 `status=passed`, failures `{}`다.

## 2026-09-02 최적화·튜토리얼·Light·나무 우선 조회표

| 필요한 정보 | 첫 조회 위치 | 판정 기준 |
| --- | --- | --- |
| 사용자 삭제 보호 | `Content/_Art/Kazan/Environment/HeinMach/Metadata/HeinMach_UserExclusions.json` | 10개 모두 `do_not_restore=true` |
| 보수적 최적화 삭제 | `HeinMach_OptimizationExclusions.json` | 109개 tombstone, label hash 일치 |
| 기존 수동 좌표 | `HeinMach_ManualOverrides.json` | 1개 `preserved_transform`, `do_not_reset=true` |
| 중복 판정 상세 | `Saved/ImportReports/HeinMach_ConservativeOptimization.json` | exact group 107, removed 109, failure 0 |
| DualAxeSword 튜토리얼 공간 | `Saved/ImportReports/HeinMach_DualAxeTutorial_Restoration.json` | PlayerStart 1, enemy anchor 2 |
| source LightColor | `Saved/ImportReports/HeinMach_LightColor_Metadata_Audit.json` | source/route-fill mismatch 0, source transform hash 유지 |
| 흰색 나무 판정과 복구 | `Saved/ImportReports/HeinMach_WhiteTreeMaterial_Repair.json` | 문제 slot 27개 수정, placeholder 0 |
| 최신 전체 Level 상태 | `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json` | actor 9,336, uncategorized 0, 39/39 |
| 이번 작업 전체 설명 | `Docs/Art/HEINMACH_OPTIMIZATION_TUTORIAL_LIGHT_TREE_2026-09-02.md` | 근거·정본·재개 순서 |

- 이전 9,452개 기준은 사용자 삭제 및 최적화 이전 기준점이다. 최신 완료 판정에는 9,336개 기준만 사용한다.
- 복원 누락처럼 보이면 FModel을 재탐색하기 전에 exclusion 2종과 manual override를 먼저 대조한다.
- 흰색 나무는 원작 의도라는 근거가 없으며 null/inherited LOD export fallback으로 판정됐다. 동일 증상은 source JSON의 `IsNull`, texture 수, 동일 family sibling부터 확인한다.

## 2026-09-03 StormPass 우선 조회표

| 필요한 정보 | 첫 조회 위치 | 판정 기준 |
| --- | --- | --- |
| 최신 전체 StormPass 상태 | `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json` | actor 14,381, failed stage 0 |
| root/child 위치와 material | 같은 report의 `stages.root_props`, `stages.child_props` | 13,050 + 551, mismatch 0 |
| Landscape | 같은 report의 `stages.landscape` | Main 440 + Boss 16, failure 0 |
| foliage | 같은 report의 `stages.foliage` | HISM 218 / instance 21,259 / override 50 |
| source Light | 같은 report의 `stages.lights` | Point 52 + Spot 1, IES 42, failure 0 |
| Fog | `Saved/ImportReports/StormPass_Fog_ReloadAudit.json` | 53, transform/material/parameter failure 0 |
| native WaterBody source 근거 | `Content/_Art/Kazan/Environment/StormPass/Metadata/StormPass_NativeWaterMaterials.json` | actor 2, texture 11, source hierarchy/parameter inventory |
| native WaterBody 저장 검증 | `Saved/ImportReports/StormPass_NativeWaterMaterial_ReloadAudit.json` | hierarchy check 79, binding failure 0 |
| 흰 체크/기본 재질 | 최종 report의 `stages.material_surface` | 17,976 slot, null 0, WorldGrid/Default 0 |
| 전체 작업 설명 | `Docs/Art/STORMPASS_RECONSTRUCTION_2026-09-03.md` | 중단 복구, 한계, 백업, 재개 순서 |

- StormPass Water 두 곳의 source `OverrideMaterials=[null]`은 누락이 아니다. `xxWaterBodyCustomActor.WaterMaterial`의 런타임 slot binding을 별도로 해석해야 한다.
- Fog/Water cooked custom master graph는 FModel JSON에 topology가 없으므로 UE5 preview graph다. source texture/parameter/parent chain exact와 proprietary graph exact를 혼동하지 않는다.
- 최신 HeinMach exclusion 기준은 18개이며, 이전 문서의 10개 기준은 사용자 추가 삭제 전 이력이다.

### 2026-09-03 StormPass 최신 정본 보정

- Water source texture 정본 수량은 11개, unresolved source texture default는 0이다.
- 최신 StormPass map SHA-256은 `F63A6C8D66C3F5D6A677EF00B2AECDB4406A6B229AB7C4DB1E4D42F25CC2C91E`다.
- 이전 `3719...` hash는 `BASE_Black_NoneSRGB` default closure 직전 체크포인트다.

## 2026-09-08 DAS 애니메이션 속도 / PSA·FBX 시간축

| 필요한 정보 | 첫 조회 위치 | 판정 기준 |
| --- | --- | --- |
| 24 fps가 원작 속도인지 | [DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md](DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md) | 11개 PSA의 유효 간격 약 30 fps, 현 InGame 24 fps; 원작 최종 runtime 배속은 별도 |
| 실제 FPS/키 개수/marker/ABP PlayRate | `Saved/ImportReports/Khazan_Locomotion_Timing_Audit_20260908.json` | Editor 직접 읽기 11개/Sequence Player 10개 |
| 임포트 속도 저하의 근거 | 같은 JSON의 FBX 및 angular-step 검사 | 6개 FBX의 1/24초 시간 격자; source/InGame 각각 5개 표적 본에서 PSA offset +1 대응 |
| Run 30.25, Walk 30.882353, Turn 32의 의미 | 시간축 문서 2절 | N/R 유효 길이와 (N-1) 구간을 구분; AnimRate를 그대로 nominal fps에 적용하지 않음 |

- 기존 PSA metadata의 `duration_seconds=(N-1)/AnimRate`는 원작 SequenceLength의 독립 실측값이 아니다. 시간 해석은 이번 보완을 우선하며 이전 report는 보존한다.
- 새로운 source snapshot/에셋 수정이 없으면 위 결과를 재사용한다. 이번 검사는 표적 조사이며 모든 DAS 애니메이션의 전수 합격이 아니다.

## 2026-09-08 HeinMach 인간형 Enemy 재사용 자료

- 정본: [HEINMACH_ENEMY_EXTRACTION_2026-09-08.md](HEINMACH_ENEMY_EXTRACTION_2026-09-08.md). 후속 Enemy 외형 작업은 이 문서와 저장 manifest부터 확인한다.
- UE: `/Game/_Art/Enemies/HeinMach`; 검병 40, 검·방패병 4, 별도 HalberdElite 1. 확인용 맵 `Preview/L_HeinMach_EnemyCatalogue`.
- `Content/_Art/Enemies/HeinMach/Metadata/EnemyImportManifest.json`: 원작 package → 개별 mesh/texture/material 대응, source slot 및 Skeleton/LOD/Morph 출처.
- 같은 폴더 `CombinedMeshManifest.json`: 전신 조합 44개의 파츠 목록, point/wedge/material offset, bone mapping 검사. `EnemyAssemblyCatalog.json`: 완성 BP 45개.
- `VisualRecipes.json`의 `PartsList`가 geometry 조합의 근거다. `ColorOverrideRandomPreset`은 Empire001/002/003 color, `BoneModRandomPreset`은 검병 Base/Fat/Sick, 방패병 Base/Fat/Muscle이며 적용 완료 자료가 아니다. runtime 선택 조건 확인 없이 랜덤 preset 번호를 고정 외형으로 단정하지 않는다.
- `SourceSpawnActors.json`: HeinMach 원본 spawn handler 47개. 튜토리얼은 actor 1066 검병/1055 방패병으로 표적 확인됐다. 다른 이름의 CB를 튜토리얼 적으로 대체하지 않는다.
- 외부 원본 보존: `C:/Users/user/Desktop/카잔/EnemyExtracts/HeinMach_20260908`. package full path, raw cooked archive, 모든 source LOD PSK, morph record 및 SHA-256을 보존한다.
- 감사: `Saved/ImportReports/HeinMachEnemy_{SourceExtraction,LibraryBuild,CombinedBodies,AssemblyBuild,FreshAudit,RenderAssetAudit,ProtectedMaps}.json`. 반복 전수 추출 없이 미통과 항목만 표적 확인한다.

## 2026-09-09 Enemy V2 우선 조회

- 최신 의상/장비/애니메이션 정본은 [HEINMACH_ENEMY_EXPANSION_2026-09-09.md](HEINMACH_ENEMY_EXPANSION_2026-09-09.md)이다. 앞선 얼굴 중심 45종은 보관용이며 현재 대표 카탈로그는 16종이다.
- 원본 선택과 경로: `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/{ImportManifest,AssemblyCatalog,SourceClosure}.json`, 간편 조회 `EnemyCatalogue.csv`.
- 속도: 같은 폴더 `AnimationImportManifest.json`, `AnimationTimingAudit.json`, `AnimationIndex.csv`. 원본 711개는 `(NumFrames-1)/SequenceLength=30 fps`, 재생용 722개는 source segment/활성 DilationCurve를 반영한 1배 재생 자산이다. ActorX AnimRate와 nominal sample rate를 혼동하지 않는다.
- 이벤트 원본/변환 시간: `PlaybackEventTimes.json`, 4,863개 notify 시간 대응. 실행 로직은 source JSON에만 보존되며 gameplay Notify 구현과 구분한다.
- 최종 감사: `Saved/ImportReports/HeinMachEnemyV2_FinalAudit.json`에서 animation/render/orientation/preservation 보고서를 연결한다. 소스 raw archive는 `C:/Users/user/Desktop/카잔/EnemyExtracts/HumanoidExpansion_20260909`, 원본 package 2,144개다.
- UI 카탈로그: `/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue`; 마법사 BP는 `/Game/_Art/Enemies/OtherRegions/Humanoids`이다. 옛 경로는 `LegacyAssetMoves.json`으로 조회한다.

### 2026-09-09 Cleanup 이후의 최신 조회 기준

- [ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md](ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md)에 삭제 결과, 실제 BP Components, 30 fps 원본과 Composite bake의 차이를 정리했다.
- 현재 남은 파일은 `Metadata/Cleanup_20260909/RetainedAssets.json`, 삭제한 195개는 `RemovedAssets.json`이다. 이전 Archive 89개도 삭제됐으므로 옛 import manifest만 보고 다시 생성하지 않는다.
- `PlaybackComparison.csv`: 시간축 변경 271개 / 동일 451개. 원본과 같은 451개가 모두 byte 중복은 아니며 11개는 표본 수가 다르다. 애니메이션은 모두 보존했다.
- `BlueprintComponents.json`: BP 16개의 실제 부모 Actor, 메시·Idle·배속·collision·transform. gameplay AI/Ability/AnimGraph를 구현한 자료가 아니다.
- 최신 감사 `HeinMachEnemy_CleanupAudit_20260909.json`은 남은 1,771개 UE 자산 hash, 카탈로그 16개, 의존성 누락 0을 확인한다. 백업은 `Desktop/카잔/EnemyExtracts/ProjectCleanup_20260909`다.

### 2026-09-09 원본 애니메이션 정리 이후 최신 기준

- [ENEMY_SOURCE_ANIMATION_PRUNING_2026-09-09.md](ENEMY_SOURCE_ANIMATION_PRUNING_2026-09-09.md): 원본 전체 삭제가 안전하지 않은 실제 AP/BlendSpace/무기 참조, 조건부 삭제 549개, 남긴 Source 162/Idle 3개의 이유와 검증.
- `Metadata/AnimationPruning_20260909/RetainedAssets.json`이 현재 Enemy 1,222개 기준이다. 애니메이션은 887개이며 재생용 722개는 그대로다. 이전 `Cleanup_20260909`의 1,771개 목록은 정리 전 이력이다.
- 같은 폴더의 `AnimationRetention.csv`, `RetainedSourceDecisions.json`, `HeinMachEnemy_AnimationPruning_Metadata_20260909.json`은 전체 package/field 기준 재사용 가능한 원본 소비 분석이다. Composite 안의 Weapon Notify 참조도 직접 소비로 별도 보존한다.
- `RemovedSources.json`과 외부 `AnimationPruning_20260909/BackupManifest.json`으로 삭제 파일을 복구할 수 있다. 별도 프로세스 감사 `HeinMachEnemy_AnimationPruning_Audit_20260909.json` 및 최종 commandlet exit 0/오류 0을 확인했다.

### 2026-09-09 Enemy 애니메이션 현재 경로

- [ENEMY_ANIMATION_LIBRARY_STRUCTURE_2026-09-09.md](ENEMY_ANIMATION_LIBRARY_STRUCTURE_2026-09-09.md)가 최신 네이밍·폴더 정본이다. AnimSequence 884개는 모두 `A_EN_PLAY_*`이며 각 병종의 `Animations/Playback`에 있다.
- `Metadata/AnimationStructure_20260909/CurrentAssets.json`: 현재 Enemy UE 자산 1,219개의 경로/hash. `AnimationLibrary.csv`: 884개 병종·유래·원작 package·FPS·sample·길이·RateScale.
- `RenameMap.json`: old→current 884개 경로. `LegacyIdleDuplicates.json`: 중복 Idle 3개 전 프레임 비교와 삭제 근거. `BlueprintComponents.json`: 새 경로를 쓰는 BP 16개의 컴포넌트 계약.
- `PlaybackDerivation=CompositeBake` 722개, `DirectOriginalTimeline` 162개다. 둘 다 프로젝트 재생용이며 원작 유래는 metadata로만 구분한다. 이전 manifest의 destination은 역사 경로로 취급한다.
- 최종 `HeinMachEnemy_AnimationStructureAudit_20260909.json`: redirector/missing dependency 0, 길이 변화 0, RAW/COMPRESSED pose 평가 5,298회, 카탈로그 16개, commandlet 오류 0.

### 2026-09-10 HeinMach·StormPass BigBear Enemy

- [BIG_BEAR_EXTRACTION_2026-09-10.md](BIG_BEAR_EXTRACTION_2026-09-10.md): 두 레벨의 공통 `CB_BigBear_E` 판정, 외형 V1~V3, 79-bone 스켈레톤 복구, 원작 시간축을 반영한 재생 애니메이션 102개와 Blueprint 사용 경계의 정본.
- 프로젝트 정본 루트: `/Game/_Art/Enemies/Shared/Beasts/BigBear`. 현재 AnimSequence는 모두 `Animations/Playback/A_EN_PLAY_*`, 시각 조립은 `Blueprints/BP_EN_BigBear_V01~V03`, 비교 맵은 `Preview/L_EN_BigBear_Catalogue`다.
- `Metadata/Extraction_20260910/FinalExtractionReport.json`: 최종 범위와 제한. `ValidationSummary.json`: 145개 asset/skeleton/texture/material/animation 감사. `RenderValidationSummary.json`: 실제 D3D12/SM6 compile·BP 재로드 결과.
- `AnimationLibrary.csv`, `AnimationImportManifest.json`, `AnimationTimingAudit.json`, `PlaybackEventTimes.json`: source package, direct/composite 유래, FPS·길이·root/additive 계약 및 1,164개 원작 event 시간을 조회한다.
- `LevelPresence.json`: HeinMach `SA_BigBear_E_2`/`AI_BigBear_E_NoneBurst`와 StormPass `SA_BigBear_E`/`AI_BigBear_E_BurstTutorial`의 source property 근거. 외부 원본 archive는 `Desktop/카잔/EnemyExtracts/BigBear_20260910`, hash 목록은 `ArchiveSHA256.json`이다.

### 2026-09-11 HeinMach Yetuga Boss

- [YETUGA_EXTRACTION_2026-09-11.md](YETUGA_EXTRACTION_2026-09-11.md): 실제 보스 식별, 본체 453/얼음 20 bone, 재질 상속/default 복원, 시퀀스 120개, 소켓·BP와 셰이더의 구현 경계.
- 루트 `/Game/_Art/Enemies/HeinMach/Bosses/Yetuga`; 배치 BP `Blueprints/BP_EN_Boss_Yetuga`; 비교 맵 `Preview/L_EN_Yetuga_Catalogue`; 애니메이션 `Animations/Playback/A_EN_PLAY_*`.
- `Metadata/Extraction_20260911/ImportManifest.json`: source package, slot 순서, 원본 master 기본값, 부모/자식 override 및 값별 `parameter_origins`. `metadata_only_texture_parameters`는 native 2D binding이 아닌 원본 참조 목록이다.
- 같은 metadata 폴더의 `AnimationLibrary.csv`, `AnimationImportManifest.json`, `AnimationTimingAudit.json`, `PlaybackEventTimes.json`: FPS 분수·sample·길이·배속·root/additive·2,324 event의 출처와 변환을 조회한다.
- `SourceMetadata.zip`/`SourceMetadataIndex.json`: 원본 581 package JSON과 hash. `SourceClosure.json`/`LevelPresence.json`: 표적 탐색과 실제 스폰 근거. 전체 맵 재탐색보다 이 자료를 우선한다.
- `ValidationSummary.json`, `RenderValidationSummary.json`, `FinalExtractionReport.json`, `ArchiveSummary.json`: 저장 후 Unreal 감사, 실제 RHI 검사 및 원본 archive 확인. 외부 archive는 `Desktop/카잔/EnemyExtracts/Yetuga_20260911`이다.

### 2026-09-15 ApesStoneHandElite 실사용 버전

- [APES_STONE_HAND_EXTRACTION_2026-09-15.md](APES_STONE_HAND_EXTRACTION_2026-09-15.md): Early/Standard CB의 최종 SCS override, V2/V3/Ghost/Wraith/EmptyMesh/시체의 사용 범위와 제외 근거.
- 루트 `/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite`; BP `Blueprints/BP_EN_ApesStoneHandElite_Early`, `BP_EN_ApesStoneHandElite_Standard`; 비교 맵 `Preview/L_EN_ApesStoneHandElite_Catalogue`.
- `Metadata/Extraction_20260915/VariantUsage.json`에는 레시피 CDO 원본·CB override·effective recipe, `LevelPresence.json`에는 HeinMach Early 스폰 3개와 StormPass Early 스폰 1개의 자료가 있다. recipe CDO의 V2를 Standard 실사용으로 오인하지 않는다.
- 기본/V3의 geometry/bind/weights/UV/colors는 같고 material chunk만 다르다. `MeshDerivationAudit.json`은 source bind 97개, 모든 skin weight 45,190행의 vertex/bone 대응 보존과 PSA 453-bone 재매핑을 확인한다. skeleton package는 실제로 Yetuga와 공유한다.
- `AnimationLibrary.csv`, `AnimationImportManifest.json`, `PlaybackEventTimes.json`: 직접 시퀀스 10개와 Composite bake 82개, FPS/길이/root 계약과 notify/event 1,000행. 원본 중복 UE 시퀀스는 없다.
- 외부 원본은 `Desktop/카잔/EnemyExtracts/ApesStoneHandElite_20260915`; 단계 도구 `Scripts/Enemies/*apes_stone_hand*.py`. `run_apes_stone_hand_editor_stage.py`는 phase별 process exit와 임시 plugin 옵션을 기록한다. 게임 Config/uproject를 수정하지 않는다.

### 2026-09-15 WildDog·WildBoar 실사용 버전

- [WILD_DOG_EXTRACTION_2026-09-15.md](WILD_DOG_EXTRACTION_2026-09-15.md): StormPass `CB_WhiteDog`의 SCS override, V3/V2/V1 배열과 source material index 0/1/2의 역방향 대응, 일반 PicaroonDog/Ghost 제외 근거, 애니메이션 82개와 BP 역할의 정본.
- [WILD_BOAR_EXTRACTION_2026-09-15.md](WILD_BOAR_EXTRACTION_2026-09-15.md): StormPass `CB_WildBoar_New`와 `CD_RD_M_WildBoar_001`의 세 live material outcome, helper mesh 제외, 애니메이션 74개와 표시용 scale fallback의 정본.
- 프로젝트 루트는 `/Game/_Art/Enemies/Shared/Beasts/WildDog`와 `/Game/_Art/Enemies/Shared/Beasts/WildBoar`다. 각 `Metadata/Extraction_20260915/VariantUsage.json`은 CDO·component override·effective recipe와 제외 결정을, `LevelPresence.json`은 HeinMach 0 및 StormPass Dog 17/Boar 2 spawn 근거를 보존한다.
- V1/V2/V3 geometry는 `MATT0000` 이외 ActorX chunk가 같다. 각 `MeshDerivationAudit.json`에서 Dog 48 bone/35,029 weight, Boar 71 bone/12,528 weight와 alias를 확인한다. 원본 LOD0/1/2는 외부 archive에 있고 프로젝트는 LOD0 하나다.
- `AnimationLibrary.csv`, `AnimationImportManifest.json`, `AnimationTimingAudit.json`, `PlaybackEventTimes.json`은 Dog direct 17/composite 65/event 429, Boar direct 11/composite 63/event 460의 FPS·길이·root 설정·시간 변환 근거다. UE에는 재생 결과만 `Animations/Playback/A_EN_PLAY_*`로 남긴다.
- `ValidationSummary.json`, `RenderValidationSummary.json`, `FinalExtractionReport.json`, `ArchiveSummary.json`은 fresh UE 감사, 실제 RHI compile/render와 archive 완료 판정이다. 외부 원본은 `Desktop/카잔/EnemyExtracts/WildDog_20260915`, `WildBoar_20260915`; 단계 도구는 `Scripts/Enemies/*wild_dog*.py`, `*wild_boar*.py`다.

### 2026-09-15 Enemy 에셋 현재 구조

- [ENEMY_ASSET_LIBRARY_STRUCTURE_2026-09-15.md](ENEMY_ASSET_LIBRARY_STRUCTURE_2026-09-15.md): 전체 Enemy 폴더 원칙, 21개 이동 대응, 빈/Legacy 폴더 정리와 fresh 감사 결과의 정본.
- 현재 package 목록은 `Content/_Art/Enemies/Metadata/Structure_20260915/CurrentAssets.json`, 표 형식은 `AssetLibrary.csv`, 옛 경로 대응은 `RenameMap.json`을 사용한다.
- `HeinMach/Humanoids`는 실제 병종, `HeinMach/Shared`는 공용 장비·rig·pose carrier·애니메이션, `Shared/Beasts`와 `Shared/Elites`는 레벨 공용 비인간형/엘리트 라이브러리다. `OtherRegions/Humanoids/Mage`에는 normal/hard 변형을 함께 둔다.
- `EmptyDirectoryCleanup.json`은 제거된 63개 디렉터리, `ValidationSummary.json`은 1,940개 에셋과 애니메이션/메시/BP 계약 검증, `WorkspacePreservation.json`은 범위 밖 사용자 작업 보존 기록이다.
- 이동 전 영향 자산 외부 백업은 `Desktop/카잔/EnemyExtracts/EnemyAssetStructureCleanup_20260915`; 재현 도구는 `Scripts/Enemies/*enemy_asset_structure*.py`다.

## 2026-09-16 DualAxeSword Weak Attack Dilation

- 원작 `AC_Kazan_DualAxeSword_Com_WeakAtk01`은 `FastAtk01_M1`의 `0–3.53 s`를 segment rate `1.0`으로 쓰면서 213-point `T_Original → T_Dilation` table로 실제 길이를 `3.4326434 s`로 바꾼다. 구간별 변화는 AnimSequence `RateScale` override가 아니다.
- raw curve key, mapping 예시, 인접 table rate, WeakAtk01–05 비교와 207-sample bake 계약은 [DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md §7](DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md#7-2026-09-16--weakatk01-구간별-재생-속도-표적-확인)을 먼저 본다.
- 전체 213 mapping point와 계산 provenance는 `Saved/ImportReports/Khazan_DAS_WeakAttack_Timing_20260916.json`에 있다. source snapshot이 바뀌지 않으면 package를 다시 전수 추출하지 않는다.
- P1.5에서는 Dilation을 재생용 pose 시간축에 한 번만 bake하고 Sequence/Montage/Ability task의 배율을 모두 `1.0`으로 둔다. notify 45개와 원작 root-motion 실행은 아직 구현 범위가 아니다.

### 2026-09-16 Weak Attack 콤보·Root Motion 보정

- 위 마지막 문장의 `root-motion 실행은 아직 구현 범위가 아니다`는 P1.5 적용 범위를 사용자 확정 방침이 대체한다. 공격 playback Sequence는 Root track도 Dilation 시간축에 bake하고 `Enable Root Motion=true`로 사용한다.
- 표준 1–5타 source는 `FastAtk01_M1`, `FastAtk02_M1`, `FastAtk03_M1`, `FastAtk04_M1`, `Com_WeakAtk05`다. `FastAtk02_Loop`는 표준 Skill Blueprint 단계에서 참조되지 않는 별도 Composite source다.
- 원작 상태 단계, 해금 시 `WeakAtk04 → WeakAtk05` 연결, source root 변위와 flag 근거는 [DAS 시간축 검사 §8](DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md#8-2026-09-16--weakatk-콤보-source와-root-motion-추가-확인)을 우선 조회한다.
- 원본 snapshot은 `Saved/OriginalAttackTiming/Metadata`, 계산 report는 `Saved/ImportReports/Khazan_DAS_WeakAttack_Timing_20260916.json`과 `Saved/ImportReports/Khazan_DAS_PSA_SourceMetadata.json`이다. source가 바뀌지 않으면 재전수 추출하지 않는다.
## 2026-09-16 DualAxeSword 애니메이션 복원 자료

- [DAS_ANIMATION_RESTORATION_2026-09-16.md](DAS_ANIMATION_RESTORATION_2026-09-16.md): 원작 AnimSequence/Composite 전수 범위, source timing과 Dilation bake 계약, `C_P_Kazan` Root Motion topology 보정, 비로코모션 write manifest, locomotion audit-only 보호 목록, 백업·배치·fresh audit 재개 절차.
- 기계 판독 정본은 `Saved/ImportReports/Khazan_DAS_OriginalMetadataAudit_20260916.json`, `Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json`, `Saved/Extracted/DualAxeSword_20260916/AnimationImportManifest.json`이다.
- 실제 UE API를 통한 저장 전 전수 검사는 `Saved/ImportReports/Khazan_DAS_AnimationImportPreflight_20260916.json`이며 710/710개 pass, Content write 0이다.

### 2026-09-16 최종 적용 정정

- 위 710개/locomotion 280개 전체 보호 기록은 사용자 범위 정정 전 준비 이력이다. 최종 보호 범위는 현재 ABP 참조 9개이며, 미사용 locomotion 271개를 복원 대상에 포함했다.
- 최종 manifest는 source 457개 + 미사용 파생 locomotion 164개 + Composite playback 360개 = 981개다. 기존 608개를 같은 package로 교체하고 373개를 생성했다.
- current locomotion 9개 판정은 `Saved/ImportReports/Khazan_DAS_OriginalMetadataAudit_20260916.json`의 `current_locomotion_audit`를 사용한다. 유효 cadence는 30 fps지만 9개 모두 exact-source rebuild review가 필요하며, Sync Marker 37개 때문에 marker-aware migration이 필요하다.
- 저장 후 집계는 `Saved/ImportReports/Khazan_DAS_AnimationImportAudit_20260916.json`, 독립 재로드 정본은 `Saved/ImportReports/Khazan_DAS_AnimationFinalAudit_20260916.json`이다. 둘 다 981/981 `passed`이며 보호 9개 hash도 동일하다.
- 작업 전 기존 608개 backup은 `Saved/ArtBackups/DAS_Animation_PreTimingFix_20260916_182555`다.

### 2026-09-17 DualAxeSword Composite exact 60 Hz

- 최신 재생 시간축 정본은 [DAS_ANIMATION_RESTORATION_2026-09-16.md의 exact 60 Hz 절](DAS_ANIMATION_RESTORATION_2026-09-16.md#2026-09-17-composite-재생본의-정확한-60-hz-교정)이다. 이전 Composite playback의 `60.***`/`59.***` 분수 FPS는 폐기된 V4 생성 계약이다.
- 현재 `PlaybackDerivation=CompositePlayback` 360개는 모두 data-model 및 platform target `60/1`이다. 시간 가감속은 pose의 source-time mapping에 bake되어 있고 Sequence/Montage 추가 rate는 `1.0`이다.
- 전수 근거는 `Saved/ImportReports/Khazan_DAS_CompositeExact60_Preflight_20260917.json`, `Khazan_DAS_CompositeExact60_Import_20260917.json`, `Khazan_DAS_CompositeExact60_FinalAudit_20260917.json`이다. 수정 전 361 package backup은 `Saved/ArtBackups/DAS_Composite_PreExact60_20260917_184000`이다.
- 재현 도구는 `Scripts/Animation/fix_das_composite_playback_60fps.py`, 독립 감사는 `audit_das_composite_playback_60fps.py`다. generator 자체도 `prepare_das_animation_timing.py`의 exact 60 Hz 계약으로 고쳤다.
