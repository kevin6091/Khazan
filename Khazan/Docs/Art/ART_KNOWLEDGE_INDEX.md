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

## 2026-09-29 Enemy LockOn 기준점

- [LOCKON_TARGET_ANCHOR_AUDIT_20260929.md](LOCKON_TARGET_ANCHOR_AUDIT_20260929.md): 원작 `xxLockOnSphereComponent`, 현재 복원 메시 소켓, `LookAt01`과 LockOn 기준의 구분, gameplay `LockOnTargetPoint` 이관 계약의 정본이다.
- 조사한 현재 Enemy 메시에는 공통 `LockOnTarget` 소켓이 없다. `LookAt01`은 머리의 별도 시선 소켓이며 원작 Character BP의 `xxLockOnSphereComponent`를 대체하지 않는다.
- 기계 판독 요약은 `Saved/ImportReports/KZ_LockOnTargetAnchorAudit_20260929.json`이다. 이번 감사에서 C++/Blueprint/SkeletalMesh/Skeleton을 수정하지 않았다.

## 2026-09-29 HeinMach 플레이 가능 경로·충돌

- [HEINMACH_PLAYABILITY_COLLISION_20260929.md](HEINMACH_PLAYABILITY_COLLISION_20260929.md): DualAxeSword 인간형 튜토리얼 시작점, 원작 자동 진행 125 actions/1,485 route points, 지형·prop collision, 2,281 route wall, 242 NavMesh bounds, 26 NavArea_Null modifier, 14 원작 link와 10 복원 보정 link의 출처·적용·PIE 검증 정본이다.
- 기계 판독 자료는 `Saved/ImportReports/HeinMach_OriginalAutomationRoute.json`, `HeinMach_Playability_Restoration.json`, `HeinMach_RouteCollision_SourceMapping.json`, `HeinMach_Playability_RuntimeVerification.json`이다.

## 2026-09-30 Character camera 부착점과 컷씬 camera

- [CHARACTER_CAMERA_MOUNT_AUDIT_20260930.md](CHARACTER_CAMERA_MOUNT_AUDIT_20260930.md): Player `Cine_Cam_Start/End`의 현재 reference-bone 형식, UE attach 가능 여부, 일반 camera 조립, Yetuga/BigBear socket, 원작 컷씬 직접 부착과 조사 한계의 정본이다.
- Player의 확인된 원작 컷씬 부착점은 `Cine_Cam_End`다. `Cine_Cam_Start`는 attach 가능한 후보이나 저장 Level metadata에서는 사용처를 확인하지 못했다.
- Yetuga 본체·IceRock 보조 mesh와 BigBear를 확인했다. Yetuga/Apes의 `LookAt01`과 gameplay `LockOnTargetPoint`는 camera mount가 아니며, 보스용 camera/cine 명칭 socket은 현재 애셋과 조사한 원작 Skeleton metadata에서 확인되지 않았다.
- 기계 판독 자료는 `Saved/ImportReports/KZ_CharacterCameraMountAudit_20260930.json`과 `KZ_OriginalCharacterCameraMountAudit_20260930.json`, 재현 도구는 `Scripts/Character/audit_character_camera_mounts.py`와 `audit_original_character_camera_mounts.py`다.

## 2026-09-30 HeinMach Player 상대 스케일 근거

- 원본 `C_P_Kazan.psk` 정점 경계, 원본 ThornTree USDA cm 단위와 복원 HeinMach 메시의 동일 경계, 현행 `SK_Player` 삽입 최상위 본의 `100`배를 대조한 결과는 [ART_PROJECT_STATE.md](ART_PROJECT_STATE.md)의 같은 날짜 절과 `Saved/ImportReports/HeinMach_PlayerScaleAudit_20260930.json`에 있다.
- 현행 topology의 계산된 Player Mesh Component 상대 스케일은 `0.01`이다. 원작 actor scale `1`의 직접 복사가 아니며, 현재 `0.009`에서 사용자 적용 전이므로 실제 게임플레이 크기와 Root Motion은 미검증이다.

## 2026-10-01 StormPass Blade Phantom arena 정본

- [STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md): 두 source phase의 장소/동일 좌표 변형, spawn dependency와 컷씬 참조, 실제 수정·수치 출처·native 근사 범위·재로드 검증·검수 전환 절차의 정본이다.
- 저장 자료는 `Content/_Art/Player/Environment/StormPass/Metadata/BladePhantom_ArenaPolish_20261001`이다. `OriginalAnchors`, `SurfaceAssignments`, `SkyPresets`, `MissingRenderPlan/Applied`, `CascadeCoreSources`, `FogBridge`, `*Reloaded`, `ReloadVerification`을 먼저 사용한다. 기존 source material plan의 `_Art/Kazan` 문자열은 현행 `_Art/Player`로 정규화해 조회한다.
- Source slot의 순서를 UE ordinal slot으로 단정하지 않는다. 두 water actor의 `WorldGridMaterial`은 원작 런타임 WaterBody 재질 바인딩 placeholder다. 기존 native tree의 옛 selector 값보다 실제 그래프의 roughness=G/AO=R/nonmetallic 계약을 확인한다.
- 검수 전환은 `polish_blade_phantom_arenas.py:view`, 감사는 `finish_blade_phantom_arena_polish.py`를 사용한다. 기존 전체 재복원/PlayerStart route-anchor 재배치를 선행하지 않는다. 원작/계산/임시값은 정책 JSON과 결과 문서에서 구분한다.

## 2026-10-01 StormPass Phase1/2 위치 해석 보완

- [폴리싱 정본의 같은 날짜 추가 확인](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md)과 `Metadata/BladePhantom_ArenaPolish_20261001/PhaseCoordinateClarification.json`을 먼저 본다. 공통 참조 마커/비교 카메라 좌표의 일치와 전투 환경의 일치는 서로 다른 문제다. Phase1 성채와 Phase2 숲의 저장 배치는 같은 보스 좌표 영역을 공유한다.
- 원본 `StormPass_All` streaming export `105/116`에는 `LevelTransform`이 직렬화되지 않았다. 물 actor root 위치와 source hash도 보완 report에 있다. 표적 추출한 BP01/BS master metadata는 `Saved/Extracted/StormPass/BladePhantomPhaseTransition_20261001`이며 Blueprint Function bytecode/원작 native runtime은 이 JSON만으로 확인할 수 없다. 정확한 runtime 전환·teleport를 검증한 자료로 사용하지 않는다.
- 기존 ReviewCamera를 선택해도 변형은 전환되지 않는다. `view('boss_phase_1')` / `view('boss_phase_2')`는 editor 환경 선택이고 gameplay 자동 전환이 아니다.

## 2026-10-01 StormPass Phase1 밝기·흰빛 보정 정본

- [폴리싱 정본의 마지막 Phase1 밝기 재검토 절](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md) 및 `Metadata/BladePhantom_ArenaPolish_20261001/Phase1LightReviewSourceManifest.json`을 먼저 사용한다. 이전 3 EV/candela adapter보다 이번 정책이 우선한다. 새 수치는 원작 광도 단위 확정이 아닌 native 임시 튜닝이며 `PolishPolicy.json:temporary_native_adapter.phase1_light_review`에 모였다.
- 원작 스크린샷 3장, source WEP·local light·child inherited field, 실제 core emitter 색과 source/native 저장 파일 SHA가 manifest에 있다. `CascadeCoreColorSources.json`은 Small export 87 / Medium 102의 실제 core StartColor를 근거로 한다. 별개 root light 색을 원작 불꽃 색의 직접 근거로 재사용하지 않는다.
- `r.VolumetricFog=0`이면 asset에 기록된 원본 발광 안개가 보이지 않는다. UE 5.8 기본 품질 계약은 **Shadows High 이상**이며 Effects 품질과 혼동하지 않는다. `view('boss_phase_1')`는 현재 editor session의 fog CVar도 켠다. project INI 변경이나 runtime 품질 시스템 구현은 아니다.
- texture compression 변경은 sRGB를 재설정할 수 있다. P1 color atlas는 Default compression 이후 sRGB를 설정·저장하고 실제 readback을 확인한다. 재귀 MaterialEditingLibrary 검사에는 null node/child 보호가 필요하다.
- `Phase1LightReviewAfter`, `LightReview_ReloadVerification`, `LightReview_Phase2Regression` 및 `LightReview_*Reloaded`가 최종 감사 자료다. 원본 배치·PlayerStart 유지, Phase2 local light/PP 불변, 저장된 Phase1 조명 정책을 재사용한 전환 검사를 확인했다. gameplay 자동 페이즈 전환은 계속 미구현이다.

## 2026-10-02 StormPass 인접 전장 authoring 정본

- [STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md)의 2026-10-02 추가 절과 `Metadata/BladePhantom_SideBySide_20261002`를 우선 확인한다. 사용자 요청에 따라 현재 `/Game/Maps/L_StormPass_Environment`는 Phase1 유지/Phase2 +X 20,390 cm, 두 전장 동시 표시다. 옛 alias umap은 현행 맵 redirector다. 원본 동일 좌표 fact를 현재 배치 규칙으로 적용하지 않는다.
- 재사용 데이터: `ActorsBefore`, `ForegroundBoundsBefore`, `Layout`, `LayoutAppliedAudit`, `SideBySide_*Reloaded`, `GroundSupportReloaded`, 최종 `ReloadVerificationWithCollision`, `SideBySideSourceManifest`. HISM local mesh bbox만으로 footprint를 판단하지 않고 3,218 instance world transforms를 반영한 저장 bounds를 사용한다. 먼 Background 산은 배치 간격 판단에서 제외하되 보존한다.
- `polish_blade_phantom_arenas.py:side_layout/show_side_by_side/view`와 route `set_variant`가 같은 layout을 소비한다. `separate_arenas` 반복 호출은 offset을 누적하지 않는다. `ArenaMarkers`의 editor-only 마커 두 개로 접근한다. 원본 좌표 기준 전체 재복원/route-anchor 재배치/Save All은 실행하지 않는다.
- 이동 후 fixed world-origin terrain shader는 geometry delta와 RootXY delta를 함께 적용해야 한다. 복제 parent만 변경하고 원본 parent는 유지한다. 양쪽 bounded PP/source local lights/분리 sun을 검사하되 shared sky/fog/GI 및 Pawn lighting channel 불변 범위를 숨기지 않는다.
- 지원 바닥 두 개는 원작 collision 미검증을 보완하는 native authoring 근사다. top Z는 중심 마커 XY를 포함하는 floor tile bbox에서 선택하며 높은 진입/계단 타일과 평균하지 않는다. UE 5.8 Python `HitResult`는 직접 `.impact_point`가 아니라 `to_dict()`의 `blocking_hit/impact_point/impact_normal/hit_actor`를 사용한다. 재로드 지면 trace 8/8을 Character/AI PIE나 전체 길/NavMesh 검증으로 확대하지 않는다.


## 2026-10-02 InGame 추가 DAS의 재생 속도 정본

- 추가 이동한 DAS animation/RateScale/Dilation 작업은 [InGame 보정 결과](INGAME_DAS_PLAYBACK_CORRECTION_2026-10-02.md)를 먼저 확인한다. V4 공간/V5 exact60 계약은 기존 DAS 복원 정본을 계속 사용한다.
- Metadata/InGamePlayback_20261002: PlaybackPlan(140개와 copy 2개의 정확한 원본·선택 구간·mapping), OriginalTimingFields(488 package의 선택 원시 시간 필드/추출 hash), ScopeMapping/SkillStateRates/Consumptions, ApplyReport(44개 write 결과), FreshProcessAudit(142 sequence/5 montage), Expected_* 및 보존 보고서. 큰 OriginalTimingFields는 대상 package만 조회한다.
- SourceTimeline/UnusedReplacement/이미 Dilation-baked를 구분한다. 표시 RateScale=1.0인 clip도 포즈 시간축에 배속이 bake돼 있을 수 있다. prefix/tail/crop/padding 보존, original package와 export object 이름 차이, raw source의 반복 소비, Player mesh 0.01의 공간/시간 구분은 새 결과 정본에 있다. 전수 재추출/전체 DAS importer보다 저장된 mapping과 대상 metadata를 먼저 재사용한다.


## 2026-10-02 두 레벨 source 룩 복원 — 저장·검증 결과

- [LEVEL_LOOK_RESTORATION_2026-10-02.md](LEVEL_LOOK_RESTORATION_2026-10-02.md): source 값/계산/임시값, 실제 셰이더 consumer, StormPass 보스-only pruning·배경 보존, HeinMach 사용자 편집 보존, 재로드·fresh-process 및 시각 검수 한계의 정본.
- 첫 조회 자료: `Rendering/Metadata/LookRestoration_20261002/SourceManifest`, `HeinMachTerrainPlan/Compilation`, `SourceSkyConsumers`, `Phase2GlobalMaterialConsumers`, `FinalShaderCompilation`, `*_FinalReloaded`, `*_FreshProcess`, `FreshProcessSummary`, `DeliveryVerification`.
- `StormPassPrunePlan`은 삭제 원본 pose/slot 및 whitelist를 보존한 계획이다. 삭제 후 재생성/옛 전체 importer 재실행 금지. 기존 `show_side_by_side/view`는 승인된 삭제를 허용하고 양쪽 전장을 유지한 채 시점을 선택한다.
- cooked `MSM_BBQCartoon` / `MSM_BBQHalfCartoon` 이름·parameter cache를 발견한 사실은 원작 실행 HLSL/엔진 fork를 확보한 사실이 아니다. stored parameter 존재와 실제 expression 소비를 구분해 `SourceSkyConsumers`처럼 기록한다.

## 2026-10-06 HeinMach Sky/PP/강설 조회 정본

- [HEINMACH_WEATHER_RESTORATION_2026-10-06.md](HEINMACH_WEATHER_RESTORATION_2026-10-06.md): 실제 저장 범위, source field/단위/계산/native 임시값, shader 적응, actual game 성능과 정확한 재개 절차.
- 저장 metadata 첫 조회: `Rendering/Metadata/HeinMachWeather_20261006/SourceDiscovery`, `SourceParticleContracts`, `OriginalBrushTopology`, `VectorFieldExtraction`/`VectorFieldExtraction8`, `ExposureContractCorrection`, `SnowApplied`/`SnowMaterialUpdate`, `FreshSavedSceneAudit`, `RenderGraphVerification`, `GameViewportVerification`, `PerformanceVerification`, `GeneratedUnusedCleanup`.
- 현행 시스템은 `/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NS_HM_SourceSnow_TwoLayers`, 2 GPU handles다. 원본은 `FP_World_IceBlizzard`, source package 전체 경로/JSON hash와 source 4-emitter 계약은 정본/report에 있다. 삭제된 trial 시스템과 `NativeSnowFinal.t3d`를 현행으로 읽지 않는다. 현행 export는 `NativeSnowTwoLayers.t3d`다.
- original WEP 볼륨 대응: 209 Blizzard1 / 210 Blizzard2 / 211 Boss / 212·213 Cave1 / 214 Escape / 215 OP. original Node vertex pool을 복원한 81 polygons를 재사용하며 이름/끝자리로 region을 추정하지 않는다.
- pre-exposed HDR PP에는 자동 PreExposure scale 중복을 피하는 계약이 필요하다. ComponentMask는 기본 R/G 상태를 확인한다. dispatch/tick CSV count는 ms가 아니다. SceneCapture의 검은 음영/노이즈와 main game 판정을 혼동하지 않는다.
- 저장 source report로 답할 수 있는 항목은 전수 추출하지 않는다. 다음 표적 계약은 source collision/puff, rotating dust field, MaxBlizzard와 지역 snow/WEP runtime 연결, 원작 전용 shader/같은 build controlled frame이다.

## 2026-10-06 HeinMach 실사 중심 후속 룩

- 최신 미술 조정 정본: [HEINMACH_LOOK_REFINEMENT_2026-10-06.md](HEINMACH_LOOK_REFINEMENT_2026-10-06.md). source weather 복원 자료는 앞선 정본을 유지하되 현재 grade/MI 값은 이번 사용자 방향이 우선한다.
- 첫 조회 `Rendering/Metadata/HeinMachLookRefinement_20261006/Applied`, `BeforeApplyActorPoses`, `FreshSavedSceneAudit`, `RenderGraphVerification`, `VisualComparison`, `SavedGameVerification`, `PerformanceVerification`, `RecoveredEditorQuality`, `EditorRecoveryIncident`.
- 엔트리 동일 시점 기존 High/최종 저장본 비교는 `Saved/ImportReports/HeinMachLookRefinement_20261006/LegacyHigh.png`와 `Saved/SavedEntry.png`. `CameraDrift/NestedMIDTrial` 결과는 최종 화면 근거가 아니다. QA MID는 항상 saved MIC에서 파생한다.
- 이전 source PlayerStart 이름으로 현재 사용자가 만든 `PlayerStart`를 되돌리지 않는다. 이번 audit 기준은 적용 직전 snapshot이다. live `DEBUG RESETLOADERS` crash 및 정확한 복구 기록을 후속 작업 전에 확인한다.

## 2026-10-06 — Armed/UnArmed 현재 위치와 재사용 근거

두 사용 Equip 클립은 현재 /Game/_Art/Player/Animation/InGame/DAS/Equip/CA_P_Kazan_DualAxeSword_Armed/_UnArmed이다. 옛 Shared/Equip paths는 참조0 확인 뒤 제거됐다. Metadata/HealWeapon_20261006/EquipPSASource.json·EquipAudit.log·SavedAssetAudit_Final.json·AssetInstallManifest.json을 먼저 사용한다. 새 playback 보정이 아니라 기존 SourceTimelineReplacement1s/rate1 유지/경로 이동이다. PSA header의 AnimRate31을 원작 gameplay equip speed로 단정하지 않는다. 런타임 attachment/Slot/Ability 계약은 Engineering의 HEAL_WEAPON_PRESENTATION_20261006.md다.

## 2026-10-06 HeinMach 사진 기반 수정·표면 차이 조회

- 현행 정본 [HEINMACH_REFERENCE_MATCH_2026-10-06.md](HEINMACH_REFERENCE_MATCH_2026-10-06.md). 이전 실사 중심 설정보다 최신 원작 재현 방향/현재 saved values가 우선한다. 원작 완전 동일 및 전용 BRDF 이식 완료로 읽지 않는다.
- 첫 자료 `Content/_Art/Player/Environment/Rendering/Metadata/HeinMachReference_20261006`: InstallManifest/DeliveryVerification/FreshSavedSceneAudit/AppliedTrial/SourceMaterialAnalysis/PerformanceVerification/MainGameCapture/ParticleReadback/MotionVerification. 현재 source WEP/fog 숫자는 종전 SourceManifest를 재사용,13개 표적 material JSON/hash/parent chain은 새Source. 원작 build번호/두 추출시점의 동일build는 미식별이다.
- 실제 rock base007 opaque394/Collision004 opaque521 등 variant parent까지 확인했다. HalfCartoon DetailMap/VertexPaint, Moss BrightAmbient/PivotPainter와 current USD binding의 차이가 새정본에 있다. MaterialAttributes.Expression=null/캐시 parameter를 실제shader body로 표현하지 않는다. source raw opaque override와 상속값을 구분한다.
- 현재 postpass는 BeforeDOF/TSR 이전, snow/dust BeforeDOF·ResponsiveAA·velocity출력false·A-only, budget`.25`, near150cm. 원작 크기는main SimCache에서flakes`.5–.75cm`/dust`.3cm` 대응 확인. 과거weather문서의 velocitytrue/near50은 이 범위에서 대체된다.
- 캐릭터 stencil254/sky252/정상 signed normal decode 유지. OP priority100이 Blizzard1을 덮던 문제와 sky SceneDepth equality 문제를 교정했다. 새source mask나 fullmap importer로 재구성하지 않는다.
- 전후사진 `Saved/ImportReports/HeinMachReference_20261006/BeforeAfter.jpg`(같은project/camera), 원작5사진 `OriginalReferences.jpg`(다른시점/build), 동체 `MotionComparison.jpg`(controlled QA). Boss이전baseline지면내카메라는전후비교제외. 사진통계를source조명값/순수ghosting점수로바꾸지않는다.

## 2026-10-06 — DAS 전투·접촉·혈흔·표면 입자 조회

- [DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md): 폴더/원본 실행 조건/복원 방법/최종 검사/21 Niagara 및 shader 미복원/재개 절차.
- 첫 metadata는 `Content/_Art/Effects/Metadata/Extraction_20261006`의 AssetManifest/DependencyEdges/AnimationEffectNotifies/EffectRoutingContracts/PhysicalSurfaceContracts/SourceOnlyAssets/Recovery/Cascade다. manifest에 source package/type/JSON SHA/native 목적지가 있다. raw는 `Saved/Extracted/CombatEffects_20261006/OriginalRaw`와 OriginalBindingRaw; 원본 cooked 파일을 UE5 asset로 읽지 않는다.
- source `PP_Damage_Spray.ItemList`의 NewDefense/NewJustGuard/EnhancedJustGuard와 `PA_Attack_Slash.NewExtraData`의 NewParrying을 구분한다. SurfaceType13 DeepSnow/10 Snow/7 Dirt 등은 source PhysicalMaterial의 field를 근거로 읽고 현재 프로젝트 surface에 자동 대응됐다고 해석하지 않는다. notify socket/scale/time/killOnEnd/attack-success/dilation은 binding raw entry를 먼저 확인한다.
- 최신 검사는 DeliveryVerification/FreshSavedAssetAudit/ShaderVerification/RepresentativeEffectRendering. source table을 통한 유도 editor curve는 80,841개이며 원작 editor key 직접 복원이 아니다. 80,874개 table shape/117 native curve key/MI 522개 source override 검사와 실제 원작 shader/전체 수명 동일성을 구분한다. protected GPU EmitterInfo 5필드는 직접 readback 미검증이다.
- Guard readback의 배열 잘림은 SETNOPEC 숫자의 exponent 처리 문제였으며 소수 문자열 변환으로 해결했다. `Import_numeric` 중간 failed는 `Import_numericdata` completed 및 마지막 전체 audit가 후속 해결한다. 이미 끝난 numericdata를 후속 사용자 수정 위에 반복하지 않는다.

## 2026-10-06 — HeinMach 횃불·화로 및 source child 효과 조회

- [HEINMACH_TUTORIAL_FIRES_2026-10-06.md](HEINMACH_TUTORIAL_FIRES_2026-10-06.md) 마지막 절: 메인 배치72곳/FX95/light100/fixture35/decal28, source/계산/native 경계, final fresh main 검증 및 후속 재개.
- 첫 자료 `Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006/{FireActorCandidates,Components,DynamicFixtures,DestructibleFireSpawners,NativeAssetManifest,SourceOnlyAssets,Placement,DeliveryVerification}.json`. Components의 source level/index/component name·lineage/property_origins, DynamicFixtures의 CDO origin/Value/bIsDefaultValue로 원작 수치와 상속을 찾는다. 기존 root가 사용자에 의해 이동했으면 현재 root에 source local child를 합성한 배치를 유지한다.
- raw/교환 payload는 `Saved/Extracted/HeinMachTutorialFires_20261006`; source-only148은 빈 native graph로 구현된 것이 아니다. source native65+native flicker7 = 새 asset72, 재사용70/Engine DefaultParticle1. PS root3은 FP_LVL_WBP_LightObj_001_FIRE_medium / FP_LVL_WBP_LightObj_001_fire_small / FP_FireDust_001이다.
- `CascadeCompatibility`, `Recovery/Cascade`, `FireShaderRecovery`, `SmokeChannelEvidence`, `ShaderVerification`, `MainSavedSceneAudit`, `MainPreview/Playback`, `PerformanceVerification`를 재사용한다. Epic quality에서 비활성인 UE4 DetailModeBitmask7은 engine migration 기준15로 파생해야 한다. Lifetime0는 infinite lifetime이며 임의 loop 변경으로 해결하지 않는다. 불투명 alpha의 smoke atlas는 source R density를 읽는다.
- 설치가 완료된 `heinmach_tutorial_fires_deliver.py install` 및 full importer/전체 HeinMach rebuild는 재실행하지 않는다. 후속 snow/다른 편집은 현재 main snapshot에 actor/tag 단위로 적용한다. shared `/Game/_Art/Effects` texture/curve/MPC/vector field를 이번 화로 작업에서 재저장하지 않았다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

첫 자료는 [HEINMACH_SNOW_DEFORMATION_2026-10-06.md](HEINMACH_SNOW_DEFORMATION_2026-10-06.md) 마지막 절과 `Saved/ImportReports/HeinMachSnow_20261006`: OriginalSnowContracts(package/field/raw/SHA), Topology/Authoring/ShaderStats, Delivery20261007/SnowContactModuleUpdate/MainVerification20261007/FinalVerification20261007. raw는 Saved/Extracted/HeinMachSnow_20261006/Source. final48 asset/mesh46/material2은 Rendering/HeinMachSnow, 플레이 map은 /Game/Maps. SnowQA5PNG/RuntimeGeometry가 실제 main 화면·14.5cm 변위 증거다. stripped source shader를 확보한 것으로 해석하거나 initial full author/deliver를 최신 사용자 맵 위에서 반복하지 않는다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

最新 snow brush 크기는 HEINMACH_SNOW_DEFORMATION_2026-10-06.md의 후속 확대 절을 따른다. BroadBrush20261007/{Baseline,SavedSettings,StagePIEPassed,Delivery,FinalVerification}.json/main_verify.log/MainPreview가 current actor settings/source/module/map/실제 접촉·크레이터/PNG 증거다. 반경40×32/100cm와 contact20/24cm는 assistant 임시 tuning, 원작 source 계약은 기존 OriginalSnowContracts에서 읽는다. 초기 작은 brush map/module hash를 현재값으로 재사용하지 않는다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

HeinMach snow 현재 높이·깊이/연락 범위·shader 정상성은 HEINMACH_SNOW_DEFORMATION_2026-10-06.md 최신 두꺼운 눈 절과 DeepSnow20261007의 SavedSettings/Delivery/FinalVerification 및 MainPreview를 따른다. 이전 broad 높이15cm/weapon reach24cm를 현재 HeinMach 값으로 재사용하지 않는다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

Enemy 현행 animation 경로는 [ENEMY_ANIMATION_ORGANIZATION_20261007.md](ENEMY_ANIMATION_ORGANIZATION_20261007.md)와 CurrentAnimationLibrary.csv를 먼저 읽는다. 옛 Playback/AM/가져온 접두사 경로는 역사적 export이며 현재 이름으로 가정하지 않는다.

실제 Main 반영 완료다. Archer 제외 HeinMach Humanoids4종 및 Yetuga/ApesStoneHandElite의 Art676, 기존 gameplay93을 purpose12폴더와 의미 이름으로 정리했다. 신규 gameplay44를 더해 현재813시퀀스, 기존 montage33과 신규22를 더해55montage다. Idle/Locomotion/Attack/Damage/Death/Guard/Alert/Equip/Interaction/Recovery/Prop/Pose이며 방향·단계·변형은 보존한다. A_EN_PLAY/중복 AC·CA·M·EN·Boss·캐릭터 접두사와 hash tail을 제거했다. 겹치는 direct source/Composite는 Original/Composite로 구분한다. CurrentAnimationLibrary.csv가 current→legacy→original source/frame/FPS/length/RateScale/root/options의 조회표다. 과거 export CSV는 historical 원본이며 수정하지 않았다.

813개 EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame을 저장·fresh Main readback했다. 4NPC의 기존 RootMotionFromMontagesOnly로 공격/End 몽타주 root delta를 CMC가 소비한다. Nav 보행은 기존 CMC/velocity pose/Foot Placement를 유지하며 RootMotionFromEverything 보행 구현이라고 부르지 않는다. Yetuga/Apes는 library/options 정리이지 신규 AI 구현이 아니다. index0/first track audit769의 Root765/Weapon_R1/B_Rock3을 유지했다. raw pose19M/곡선·재생률 비교와 compressed extraction tolerance를 구분한다. source pose/root 트랙·Skeleton topology/scale/Player .01·재생속도/재임포트 수정은 없다.

Rename참조 갱신 후 옛802 packages는 fresh registry/commandlet 및 Main hash 확인으로 실제 제거됐다. source assets의 imported actor/catalogue 참조도 갱신했다. 실패 fixup와 QA 로그를 지우지 않았다. Archer177개 hash는 전달 전후 동일하다. Main stock build·813 saved reload/dirty0를 완료했다. 자산별 분류·이름·원본 출처는 ENEMY_ANIMATION_ORGANIZATION_20261007.md 및 Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv를 따른다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Contact55 ?? ???? Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/RequestedContract/SavedSettings/Delivery/FinalVerification/PendingApplyStatus.json? MainPreview, Art Snow ?? ?? pending ?? ???. ????? Preview Main24660 nativeSuccess/foot34cm/weapon50cm?? canonical PID3528 lock ??(worker2256)?. ?? failure ??/?? metadata ??? ???? Preview ??? ?? canonical ?? ??? ?? ???.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
현재 데이터는 Contact55_20261007의 RequestedContract/SavedSettings/Delivery/FinalVerification/PendingApplyStatus.json와 MainPreview, Art Snow 정본의 이번 pending 절을 재사용한다. 이전 실패/원작 metadata는 보존하며 Preview 성공을 원본 적용 완료로 쓰지 않는다.


<!-- HeinMachGhosting_20261008_applied -->
## 2026-10-08 — HeinMach 이동 캐릭터 선명도·잔상 수정

재사용 근거는 Saved/ImportReports/HeinMachGhosting_20261008이다. MainDelivery/FreshRuntimeVerification와 FreshConfigAudit가 최종 증거이며 actual-input5조건65사진은 Captures/20261007T221643_574561Z에 있다. 상세는 Art reference-match 정본 이번 절과 Engineering Source/BP/Config 정본으로 분리 기록했다.


<!-- ApesYetugaBehaviorResearch_20261008 -->
## 2026-10-08 — Apes·Yetuga 패턴의 재사용 근거

첫 자료는 [APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md](APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md) 최신 절이다. Metadata/EnemyBehaviorResearch_20261008의 ApesOriginalAnalysis/Evidence/ResolvedBranches, YetugaOriginal/AIContractSummary/SkillStepsBranches/SkillAvailability/YetugaOriginalSkillAnalysis, root YetugaOriginalDefenseRecovery, PublicApes/PublicYetuga 및 ResearchVerification를 재사용한다. 원본 package/export-index/field/raw/hash, 현재212개source mapping, 공개clip정확URL/시각/hash를 보존했다.

Yetuga exhaustion GroggyStand/New, 직가 GroggyStr, 등 PartGroggy는 별도포즈다. NormalAtk01의동작4와group5를구분한다. DamageParry의 Moving/Reaction 및 Armageddon 동명이인사본은 Index.local_path로찾는다. 기존SourceMetadataZIP/게임asset은변경하지않았고 추가library재추출/retime/rootrepair는없다. gameplay 해석·native미확인은 Engineering 분석에 분리했다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

원작 소진·브루탈 어택의 첫 조회점은 [MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md](MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md) 최신 절이다. Metadata/EnemyStaminaResearch_20261008의 TargetedFindings/StatusAndHoldingSupplement/TargetedOriginal01–04와 Metadata/MonsterStamina_20261008/AnimationPlan.json을 재사용한다. cooked CS/AP/SI/SB/SD의 package/field/raw/hash와 공식 공개 자료를 구분했다. native 양쪽 완료 후 exact Max sequence를 직접 복원했다고 표현하지 않는다.

기존 보정 clip49를 InGame용으로 복제했고 bone payload/재생률/root옵션은 author audit에서 보존했다. Skeleton2에는 필요한 DefaultSlot만 등록하고 reference bone 이름/parent/pose를 보존했다. Yetuga New Composite의 GroggyStand와 old GroggyStr/PartGroggy, Apes variant01과 skill25 variant02를 섞지 않는다. Main 전달·새 saved readback은 완료이며 runtime 동작은 Engineering 정본을 읽는다. 전체 추출/retime/root repair를 반복하지 않는다.

<!-- PlayerAttackVFX_20261008_MainComplete_1911 -->
## 2026-10-08 19:11 KST — DAS 공격 VFX 최종 재사용 근거

첫 문서는 [PLAYER_ATTACK_VFX_PLAYBACK_20261008.md](PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 최종 Main 완료 절이다. `Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json`, `CombinedPreparedPlaybackPlan.json`/`CombinedPlaybackWindows.csv`, `MainCombinedSavedAssetAudit.json`, `ReviewedAttackAndFloorProof.json` 및 `MainRuntimePIE/{Driver,ActualNativeModule,RootVisualReview}.json`을 재사용한다. 현재401구간(Particle345/Decal56), 몽타주8, Art15와 Main 실제 공격18/Brutal5·176캡처·fallback0의 근거다. 추가 Brutal Snow4 및 기존 Snow65/Water20은 unsupported source 기록이며 native particle 작성 범위로 합산하지 않는다.

원작 package/field/raw 값·시간 변환은 `MetadataAudit`와 준비 plan/CSV, native 해석/texture/channel/child blend는 `ResourceAudit` 및 고유 ShaderRecovery/ContextOpacityFix/AtlasUVFix/AtlasUVFreshVerify/DecalFloorQA를 읽는다. `BaseParticleUnusedMaskRestore.json`은 불필요 후보의 단일 복구, `AtlasUVFailureEvidence`는 실제 체크무늬 실패를 보존한다. frozen ArtCandidateManifest의 이전 pending/Main변경0 상태는 FinalVerification의 supersession이 대체한다. cooked graph·원작 full pixel parity·401개 모두의 화면 가시성·shipping 성능은 미검증이며 완료된 전체 추출/author/delivery를 재실행하지 않는다.

## 2026-10-08 — Combat Reaction·공격 형상·제자리 root 후속 근거

첫 조회점은 [COMBAT_REACTION_ANIMATION_AUDIT_20261008.md](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 최신 절이다. `Metadata/CombatReaction_20261008/AnimationClassification.json`은7몸/원작 AP·현재 경로 분류, `InPlaceReactionRootAudit.json`은 실제 root/index0/first track·sample extraction, `PlayerSourceRootReadback.json`은 Work source24개 옵션 readback, `MonsterAttackCollisionPlan.json`은 인간35patterns/55nodes/원본108windows의 표적 계산이다.

Box100개의 source Bounds 합성 검증과 현재 actor-frame 정렬 검증을 구분한다. 작성 계획은113Box/key1498, 미지원8unique/11occurrences 제외이며 실제 author save/reload/PIE는 아직 확인되지 않았다. Player AirF/B sampled true root·child Root는 제자리이고 Bip001 pose를 root로 옮기지 않는다. 외부 RMS world 이동250/120/150cm는 원작값이 아닌 CharacterDefinition 임시 튜닝이다. source/baked 시간·공간 `.01`·재생률1x를 혼동하거나 전체 library/root repair를 재실행하지 않는다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — CombatReaction 현재 Main 정본과 재사용 증거

이 기능의 이전 “author/save/PIE 미확인” 상태는 [COMBAT_REACTION_ANIMATION_AUDIT_20261008.md](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 완료 절과 `Metadata/CombatReaction_20261008/{Authoring_Final,CollisionAuthoring_Final,NativePIE_Final,IntegratedRegression,WorkSavedReload,MainSavedReload,FinalVerification}.json`이 보충한다. Main146행(16Source/130asset)·원본245/raw 동일 Player24/63montage·16Loop crop·113Monster/60Player collision windows·fresh654,552checks가 실제 근거다. `Screenshots/*.png`7장과 RuntimeChanges.patch/UserGuide를 재사용한다.

AnimationClassification·ReactionAuthoringPlan·MonsterAttackCollisionPlan·Root audit의 원본 field/직접값/계산식과 임시 프로젝트 선택은 유지한다. Heavy Air/giant fallback/미지원11shape를 전체 원본 지원으로 바꾸지 않는다. `.01` 시간 배율 재적용이나 전체 metadata/retime/root repair/author/delivery를 다시 실행하지 않는다.

## 2026-10-11 — Player VFX polish 재개 완료 증거 위치

[완료 Art6/합집합18 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json), [재생 정본](PLAYER_ATTACK_VFX_PLAYBACK_20261008.md), [Root actual Main9장](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Resume_20261010/ArtFollowupPlans/Main02V5Bound_20261010T165705559241Z/RootVisual_Main02_ACTUAL_ROOT_ACCEPTED.json), [독립 Main 검토](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Resume_20261010/IndependentMain02VisualAndRuntimeReview.json)를 우선한다. Actual15 Smash slot5 World03 원인 격리, Sphere RGB/threshold0.5 원본 근거와 재구성 경계, latest Effects461/WPO1 private intake 및 source/native external rebase는 동일 Resume 폴더에 저장했다. Native Main02 18+5/FirstPose13와 Saved401/Art18은 완료; 원작 shader/pixel·전체401 가시성·Shipping 성능은 미확인이다. 전수 재조사·전체 추출·과거 전달 반복은 하지 않는다.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — HeinMach clean presentation 및 공격 VFX 경계 교정 완료

[이번 작업 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)과 [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json)을 우선한다. HeinMach authored PP/툰/외곽선8 제거, 나머지9861 actor/component 및 Sky/Fog/조명198 보존을 fresh canonical-map RHI에서 확인했다. VFX128 emissive root에 역노출 보정을 적용했다. AutoExposure=False trial은 백색 clipping 때문에 철회했으며 기본 장면 metering/HDR/AA/물리 Fog는 남는다.

차지 slot0 smoke의 미연결 마스크와 slot1의 false color-switch 오소비를 교정했고 최종 실제1.1235초 격리 화면에서 두 사각형 제거를 확인했다. OverFury cube는 VAT decode/WPO 누락을 원본 VAT4 데이터+공식 native decoder로 교정했다. 혈액은 이전보다 실제 sprite 분사를1.5배 늘리는 임시 튜닝이며 decal 증가는 없다. 이동 경로 mesh-decal의 source15/s는 임시0/s로 중단했고 마지막 baked cache까지 fresh readback으로 확인했다. source 숫자/임시 숫자·원작 stripped shader 경계는 새 정본을 따른다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->
## 2026-10-11 — Combat UI / 미전달 표현 후속 재사용 경로

- UI 원작 package/widget override/texture16/font-face1/원본 X 표식과 실제 Xbox B glyph/수치 출처는 [COMBAT_UI_SOURCE_AUDIT_20261011](COMBAT_UI_SOURCE_AUDIT_20261011.md). 저장 metadata는 `Metadata/CombatUI_20261011/SourceWidgetAudit.json` 및 SourceWidgets/Resources/Parents/Inputs/Fonts이고 재전수추출하지 않는다.
- `.ufont` streamed data는 기존 EnemyExtractor의 표적 `font-data`로 읽는다. 실제 header OTTO인 OpenType/CFF는 `.otf`로 임포트하며 raw SHA/bytes는 FontDataReport를 따른다. AES key를 report/log에 쓰지 않는다.
- Blood physical sprite/Cascade sibling remap, DAS 표시 튜닝, Snow40/profile2, 조명 Sun5000/Sky1.1 및 최종 Main RHI는 [COMBAT_PRESENTATION_FOLLOWUP_20261011](COMBAT_PRESENTATION_FOLLOWUP_20261011.md). 최종 receipt/backup을 확인하고 증량 author를 반복 실행하지 않는다.

## 2026-10-11 — B 표시 알파 경계 교정 조회

`M_UI_BrutalRing` 최신 A-only/inward feather·Main SHA c4d6ff…·실제 B 화면은 [UI Art 정본](COMBAT_UI_SOURCE_AUDIT_20261011.md)의 B 알파 후속과 `Metadata/CombatUI_20261011/BrutalAlphaFinalVerification.json`을 따른다. 기존 R/G/A opacity 때문에 생긴 붉은 사각형을 제거했고, 원작 radius .49/.38/색과 glyph 픽셀은 유지했다. EdgeSoftnessPixels1.25는 원작 수치가 아닌 명시된 임시 표시 튜닝이다. 기존 UI receipt의 다른36개 제품 hash는 그대로이며 전체 import/reconstruction을 반복하지 않는다.


## 2026-10-12T02:04:36+09:00 — 원작 사운드 재개: 저장 배열 누락 수정본 검증 / Main 잠금 대기

chunk0/chunk1의 실제 audio index 104178파일/23359 uasset를 확인했고 chunk1의 sound package2도 조사했다. 음원은 chunk0 소유다. source bank/event/game-sync/aux와 현재 source notify는 저장 metadata/report를 재사용하며 전체 리소스를 다시 조사하지 않았다. 한국어 KR 분기를 사용했다. Native decoded WAV1644는 원본48kHz/채널·gain·loop·끝음을 보존하는 PCM16이며 normalization/tail trim/추가 lossy encode0이다. 원본 PCM의 clipping4153 samples는 보존했으며 새 믹서 clipping과 구분한다. 현재 Audio/Original 에셋2147은 source cue480/wave1644+timing silence1/ambient wrapper10/native reverb6/기타 settings6이다.

645 sequence의 KZAudio point1958/state205 총2163 event는 saved import contract의 실제 dilation 여부와 원본 T_Original→T_Dilation piecewise linear table로 현재 baked clock에 한 번만 계산했다. 원본 CAkActionPlay TransitionTime(ms)/1000의18 fade는16 Linear와2 Log1/Exp1을 구분한다. 후자의 sqrt(t)/t² shape는 명시된 native 임시 근사다. 숫자/package/field/원시값·hash는 AudioAuthoringPlan01/PlaybackPlan/SourcePlayFadePlan01/NativeCuePlan01/SpatialAudioPlan01/ProjectileAudioPlan01에 보존했다. bank→media recipe는 엔진 최대32 child 기술 제약에 맞춰 그룹화했다. SoundWaveAssetPtr의 영구 참조4663개는 fresh process에서 검증했다.

중단점의 검증 중 이전 Python 배열 iteration으로 바꾼 구조체 사본이 배열에 재기록되지 않아37 ComboDefinition의 ImpactSound/GuardSound/ProjectileSound가 None으로 남은 것을 발견했다. index별 windows/nodes/pattern_objects 재대입으로 수정했고 모든 비오디오 export field를 전후 대조했다. 수정본은 BindingRepair03_Prepared/Prepared/Content에 있다. SavedAudit06_PreparedBindings가 player impact61/monster guard405/object guard4/projectile2 및 기존645 pose·curve GUID/RateScale/root/non-audio notify 보존을 새 프로세스로 확인했다. 새 AudioPIE07_PreparedProjectile은7 family+cancel8, original source loop 정리, 실제 Shoot/Impact의 두 비행음 녹음이 nonzero/clipping0으로 통과했다. 투사체의 source state Rock/Snow와 duration1.6503333/1.536s, source event maximum radius3000/5000cm를 보존했다. original SoundData.ProjectileRTPC80/60·SphereRadius2000의 원작 native 제어 의미와 global RTPC 완전 재현은 미확인이다.

Main HeinMach 환경음은 source actor39+기존 fire FX anchor95=134 ambient와 reverb13을 이미 저장했다. EnvironmentPIE04_RHI의 숲/절벽/동굴/보스룸/배치 fire7 실제 listener·reverb 출력은 passed/새 clipping0이며 기존9861 actor class/label/transform/PP0와 최신Snow40cm/Sky/Fog/UI를 보존했다. native reverb·총량 headroom·repetition·voice budget은 어시스턴트 임시값이다: SC_Original gain0.5(-6.0206dB), SFX64/Ambient24/Fire8, character wet send0.05–0.15, finite ambience12–28s, fire gain0.35/pitch0.99–1.01, cave3.2s/boss2s/outside0.35s/volume0.30·0.08/fade1.5s. 전체 native reverb parameter profile은 EnvironmentAuthor01/Environment.json과 author script에 있으며 원본 Wwise aux/room bounds와 구분한다. source attenuation point97의 normalized distance=distance_cm/max_radius, scaling2 gain=To+1을 사용하되 nonconstant curve의 native linear 보간은 근사다. source random avoidRepeat1의 native bag 및75 one-post/one-item sequence의 bag은 원본 전역 순서와 같다고 주장하지 않는다.

**Main37 수정 바인딩은 아직 미반영이다.** 새 Rider Main PID19752가 파일을 잠그고 있어 Delivery01의37행은 모두 Windows error32로 대기하며 saved hash 충돌0이다. 사용자 에디터 제어·저장·종료0이다. 수정본 검증을 Main 완료로 표현하지 않는다. source music fallback12는 자동 BGM으로 재생하지 않았고 미확인 parent source8/above-surface layer58/비사용 projectile switch3/native DSP·global RTPC·plugin tone output/Shipping 성능은 한계로 남긴다. 완전 SDK/IR/sample parity를 주장하지 않는다. 재개 근거는 PreparedVerification01.json과 ResumeState05.json이다.


## 2026-10-12 — Player Parry 준비본과 alpha 검사 정정

원작 Just_L/R composite의 반대 이름 raw sequence 참조, DilationAnimPositions 31개를 사용한 22/60초 bake, PP_Damage_Spray.NewJustGuard→PP_AtkEx_JustGuard의 13 emitter, 기존 원작 성공 cue를 연결했다. 새 motion2/particle1/master3/MI5=11개와 기존 Guard GA/Montage2개가 준비본이다. 정확한 package/SHA·수치·현재 검증 범위는 [PLAYER_PARRY_SOURCE_20261012.md](PLAYER_PARRY_SOURCE_20261012.md)에 기록했다. 공유 원본·Audio Notify·다른 작업은 저장하지 않았다.

최초 어두운 effect preview의 검은 원판은 shader 결함이라는 가설과 달리 검사 전용 빈 GameModeBase 맵에 생성된 **DefaultPawn_0의 구형 메시**였다. AlphaPreview06의 hidden_fixture_pawns에 origin(0,0,0)을 기록했고 이 Pawn만 숨긴 실제 RHI 캡처에서 원판이 사라졌다. AlphaPreview01–05 및 Isolate03은 그 fixture가 가려 외관 합격 근거로 사용하지 않는다. 보호된 LOD property를 직접 변경하려던 Isolate01/02는 API 실패로 끝났으며 task-owned process만 정리했다.

불필요한 local5 MI의 Additive 통일과 black-emissive gate는 AlphaFinalize02에서 철회했다. 모든 MI의 원본 base-property overrides를 복원했으며 particle의 13 emitter를 모두 유지했다. local3 parent의 continuous opacity와 0.04 UV / 최소1.25px edge feather만 유지한다. untextured DefaultParticle spark는 elliptic alpha와 ParrySparkSoftnessPower=2로 모서리·끝을 부드럽게 했다. 이 세 수치는 원작이 아닌 어시스턴트 임시 표현 값이다. root shader/source pixel parity·Shipping 성능은 미확인이다. 최종 preview/saved readback 결과는 PreparedVerification과 하단 후속 기록을 따른다.

**Main 에셋 반영은 잠금으로 대기한다.** 다른 에디터/채팅은 제어하지 않았다. 재추출/전체 author를 반복하지 않고 DeliveryPreflight/ResumeState의 대상만 SHA 확인 후 복사하고 fresh Main saved/RHI를 검증한다.



## 2026-10-12T08:17:34+09:00 — Player Parry 에셋 Main 전달·fresh 검수 완료

새 motion2/particle1/local master3·MI5와 기존 Guard Montage·GA를 합친13 package를 Main에 전달했고 fresh MainSavedAudit02·MainPIE02에서 확인했다. source composite/dilation/22 frame/source cue와 기존 Guard segment·notify는 유지했다. 실제 Main의 성공 모션/weapon contact flash/꼬리 프레임을 열어 불투명 card/원판 경계가 없고 입자 끝이 연속 fade하는 것을 확인했다. source MI blend overrides는 복원됐으며13 emitter를 유지한다. local parent의 .04 UV/1.25px와 spark ellipse power2는 사용자 요구에 대한 임시 표현 수치다. 기존 공유 재질·texture·audio를 재저장하지 않았다.

Main DLL/source/asset SHA와 실제 RHI/저장 검사 결과는 Metadata/Parry_20261012/FinalVerification.json에 결속됐다. 이전 Main 잠금/준비본 pending은 이 범위에서 해소됐다. DefaultPawn 검은 원판 가설 정정과 이전 실패 proof는 보존한다. 초기 RHI의 메모리 budget/FPS 경고, 원작 stripped shader/pixel/impact writer parity, 실제 스피커 출력(-nosound) 및 Shipping 성능은 범위를 구분한다. 정확한 runtime은 Engineering PARRY_IMPLEMENTATION_20261012.md, 완료 후 재개 기준은 ResumeState.json이다. 전체 추출/저작/과거 DLL 전달을 반복하지 않는다.



## 2026-10-12T10:52:19.737884+09:00 — Fab VFX 공급 폴더 대조·native 반입 재사용 인덱스

정본은 [FAB_VFX_IMPORT_20261012.md](FAB_VFX_IMPORT_20261012.md)다. 원본 C:/Users/user/Desktop/VFX의4개 uproject·Content file 최초 inventory는 Metadata/FabVFX_20261012/LocalInventory.json, full package→원본 file은 SourcePackageIndex.json, 요청 Fab7→현재 root/status/count는 ListingMap.json을 조회한다. 새 질문에 이 공급 폴더 전체를 다시 조사하지 않는다.

현재 검증 완료 root는 /Game/Cursed_Magic(NS58), /Game/NiagaraVFXBundle(NS609), /Game/ARPGVFXPack03(NS15)이다. StageDependencies08/DependencyAudit.json은 native3357/의존성과 원본에도 없는 soft5, Delivery.json은 원본·대상 path/초기 SHA/덮어쓰기0, MainLoad02/AssetLoadAudit.json·Exit.json은 public3247/external110/load0/Exit0, MainShaders01/ShaderAudit.json·Exit.json은 실제 RHI Material375/compile0/stats양수375/Exit0이다. FinalVerification.json은 source/target SHA3357·현재 Source/Config/uproject snapshot·최종 범위, ResumeState.json은 아직 못 반입한4개 항목과 추가 절차다. native final1회 검증 완료 뒤 전수 import/compile/기존 폴더 이름 변경을 반복하지 않는다.


## 2026-10-12T13:26:59.800787+09:00 — Fab VFX 7팩 반입·얕은 폴더 정리 완료

Fab 7팩의 현재 라이브러리 정본은 [FAB_VFX_IMPORT_20261012.md](FAB_VFX_IMPORT_20261012.md)의 최신 완료 절 및 `Metadata/FabVFX_20261012/Completion`이다. 공급 원본 전체를 다시 조사하지 않고 다음 저장 증거를 재사용한다.

- `ListingMap.json`: Fab ID·상품명·로컬 Content root·현재 numbered pack path·NS 수. 네 번째 링크는 사용자 정정의 Roar Spell VFX다.
- `InputManifest.json` / `RenamePlan.json` / `FolderMap.json` / `LayoutSummary.json`: 원본 3,969 file, public 3,859 old→new object path, 얕은 폴더, 이름 충돌 처리.
- `PropertiesBefore.json` / `MainAudit02/OrganizedAudit.json` / `Exit.json`: public 3,859 load, settings 7,943, old refs/hard missing/redirectors/errors 0, NS 786.
- `RendererBasis.json` / `StageShaders.json` / `StageShaders02/Exit.json`: 현재 Main renderer에 맞는 Material 419 실제 RHI compile; 최종 Material SHA 및 renderer 일치.
- `WPBuilder02` / `WPStageAudit05` / `MainAudit02/WPDemoAudit.json` / `WPOriginalWorld.json`: Cursed 데모 103 actors·7 external objects, 실제 actor transform/class/NS 선택 보존, native duplicate builder 보완. 엔진 재생성 descriptor bounds/class 차이는 `WPDescriptorDifferences.json`에 별도 보존.
- `PublishReceipt.json` / `FinalVerification.json` / `ResumeState.json` / `LibraryOverview.md`: Main files 3,969·최종 SHA·7팩 complete/잔여 0·사용 폴더 표.
- `Before`, `Retired/Content`, `WPBeforeMain`, `PublishReceiptBeforeWP.json`: 처음 3팩 및 보완 전 task package의 불변 보존·변경 경계.

현재 root는 `/Game/VFX/01_ARPGEssentials`(52), `02_DynamicImpact`(16), `03_SlashHit`(35), `04_RoarSpell`(1), `05_CursedMagic`(58), `06_NiagaraBundle`(609), `07_ARPG03`(15) 및 `_Shared`다. 이 괄호는 native registry NiagaraSystem 개수이며 원작 수치가 아니다. 첫 작업의 루트 report/경로/미반입 상태는 역사 자료로만 쓴다. 후속은 실제 소비할 효과만 표적 확인하고 전체 재임포트·rename·shader 검사를 반복하지 않는다.


## 2026-10-12T13:28:50.418609+09:00 — Fab7 현재 열린 Main 에디터 표시 확인

RiderLink의 현재 Main PID16504에서 read-only registry 조회로 7팩 root의 NiagaraSystem 52/16/35/1/58/609/15 및 public asset 3859를 확인했다. 강제 rescan/asset save/map save/맵 전환/PIE 제어는 0이다. 현재 열린 에디터에서도 `/Game/VFX` 라이브러리를 바로 조회할 수 있다. 증거는 `Metadata/FabVFX_20261012/Completion/LiveEditorAvailability.json`이다. 7팩 반입·정리는 complete/남은 필수 작업0을 유지한다.


## 2026-10-12T13:40:48+09:00 — DevMap·HeinMach 룩 준비본 / Main 잠금 대기

[SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md](SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md)를 첫 조회한다. DevMap/HeinMach 조정본493(map2/기존 masked MI489/새 parent2), PP 각1·toon/custom blendable0, 기존 actor pose10032 변화0와 scalar/vector/texture/base overrides의 예상 밖 변경0을 확인했다. small-tree3 raw RGB emission off만 TEMP 예외다. source stock foliage transmission 시험은 white leaf로 철회했고 최종 기존 DefaultLit/기존 two-sided/clip을 유지한다. DevAfter02/HeinAfter04 실제 D3D12 game viewport 검수·Exit0와 PreparedSaved02/PreparedDelivery가 준비본 정본이다. Source/Config/DLL 전달0, 원작 전용 shader/pixel·Shipping 검증은 별도다. Main editor PID16504/DevMap의 dirty0을 read-only 확인했지만 Win32 error32 map lock으로 Main content writes0에서 중단했다. 사용자에게 저장 후 editor 종료를 요청했고 editor 종료/reload/save 제어0이다. 잠금 해제 뒤 install→새 MainSaved01→MainDevAfter01/MainHeinAfter01→selected493 SHA/화면→FinalVerification/완료기록 순으로 재개한다. Main이 baseline과 달라졌으면 최신 사용자 변경을 보존해 field만 이관한다. 전체 추출/재임포트/Source·과거 DLL 전달을 반복하지 않는다. exact resume는 Metadata/SceneLook_20261012/ResumeState.json, 비교는 DevMap_BeforeAfter.jpg/HeinMach_BeforeAfter.jpg다.

<!-- SceneLook_20261012_PreparedAwaitingMainUnlock -->


## 2026-10-12T14:44:13+09:00 — DevMap·HeinMach Main 반영 및 새 화면 검증 완료

앞선 Main 잠금 대기 기록을 이 완료 기록으로 대체한다. 사용자 Main 에디터가 종료된 뒤 선택493개 전부의 baseline SHA와 교체 접근을 먼저 확인했고 Main에 map2/기존 masked MI489/부모2만 전달했다. 사용자 프로세스 강제 종료·저장·reload0, Source/Config/DLL 전달0이다. MainSaved01 새 프로세스의 saved audit Success/Exit0, 기존 actor pose10032 변화0, 보호 material parameter/base overrides 예상 밖 차이0을 확인했다. MainDevAfter01(DevMap3뷰)/MainHeinAfter01(HeinMach4뷰)는 실제 D3D12 game viewport를 촬영하고 Exit0/성공/재질 compile failure0이다. 역광 캐릭터·눈/바위/횃불·음영 화면을 직접 검수했으며 실제 Shot1092×573과 요청 창1600×900은 구분한다. 현재493개 파일 SHA가 준비본과 전부 같다. 비교 이미지는 새 Main 촬영으로 갱신했다. Three small-tree raw emission off는 명시한 TEMP 보정이며 실패한 stock foliage transmission trial은 철회된 상태다. 원작 전용 shader/pixel 전체 일치와 Shipping 성능·전 경로 플레이 검증은 별도이며 완료로 확대하지 않는다. 재개 정본은 Metadata/SceneLook_20261012/FinalVerification.json과 complete ResumeState.json이다. 이미 완료된 전체 저작/추출/재임포트를 반복하지 않는다.

<!-- SceneLook_20261012_MainCompleted -->


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 바닥 Niagara·alpha Main 완료

사용자 지정 /Game/VFX/03_SlashHit/KZ_Parring_Distort의 원본6 emitter는 그대로 보존했다. /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort 복제의 M_SW_distort_Sprite_0/M_SW_distort_Sprite001_1/Hit003_6 renderer만 CustomFacingVector 및 실제 User.KZFloorNormal로 저작했다. shader에 카메라 facing을 남기는 잘못된 수동 binding trial은 native author의 host-map binding3개 true로 대체됐다.

원본 parent/MI2쌍을 새 경로에 복제하고 기존 opacity에 UV radial feather(.8–1)를 곱하며 refraction 가장자리를 중립1로 돌려 사각 경계를 제거했다. 이는 어시스턴트 표시 TEMP이고 원작 직접 수치가 아니다. scalar/vector/texture override는 원본과 동일하다. 원본 source Niagara/머티리얼/텍스처를 수정하지 않았다. 실제 RHI PrivatePIE05/Fall_02 화면에서 부드러운 바닥 원형과 사각 경계 제거를 검수했고, fresh Main saved/RHI가 같은6 package를 검증했다. 경로·SHA·runtime 증거는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json. Fab 사용자 지정 효과와 원작 metadata 재현은 구분하며 원작 pixel/shader 동일성은 주장하지 않는다.


## 2026-10-12T19:30:36.993088+09:00 — 전체 정수 FPS·몽타주 표시 증폭 수정 Main 완료

원인: UE5.8 UAnimMontage::UpdateCommonTargetFrameRate가 호환되지 않는 source sampling rates를 만날 때 CommonTargetFrameRate를 무효화하고 UAnimCompositeBase의100000/1fps precision fallback을 사용한다. 원본 전체 inventory2674/158에서 fractional461/fallback36이었다. import의 (frames−1)/exact source or dilation duration으로 생성된 rational FPS가 근거이며 재생 자체가100000배 빨라진 것으로 혼동하지 않는다.

461 sequence를 nominal30/60Hz로 변환하고 frame-index bone keys3854855개를 그대로 보존했다. raw duration=Dnew=N/Fint, alpha=Dnew/Dold, RateScale_new=RateScale_old×alpha로 실제 seconds를 유지한다. notify/marker local seconds·embedded visual scalar/vector curve X와 slope/weighted tangent·montage source trim 좌표를 함께 변환했다. 원본 TimingContract/metadata는 보존하고 IntegerFPSRepair tag를 덧붙였다.45 의존 montage의 표시 sampling은 모두 정수다. montage DataModel 자체를 강제 정수 grid로 바꾸는 trial은 reload 시 실제 length를 반올림하여 철회했고, 원래 precision model clock은 보존했다.

fresh Main의 모든2674 sequence/158 montage에서 fractional sequence0/fallback0; MainSaved01은 실제 montage length 차이0·raw key/notify 일치를 확인했다. concurrent Main Niagara attack VFX88개는 최신 저장본에서 다시 보정하고 원본 pose hash/신규 notify를 보존했다. 현재 Enemy 조회는 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv(813행/270수정)와 전체 Plan/FinalVerification을 사용한다. 예전 CSV는 변환 전 역사값이다. original game metadata numbers와 clock 계산/knockback TEMP 표현은 구분한다. FPS 수정 과정에서 skeleton/root tracks/material/HP·ST/공격 geometry·world clock을 재저작하지 않았다.


## 2026-10-12T19:50:49.391255+09:00 — Dodge 표현 정본 등록

`Metadata/BeastDodge_20261012/Completion/FinalVerification.json`: 8방향 Dodge의 CursedMagic Dash1/Blink1 참조, 새 SW_Player_DodgeSuccess, 실제 Niagara/Audio 검사·RHI 화면과 Main 전달 SHA. `Feedback/AudioSource.json`: 저작 WAV0.18초/48000Hz/peak0.16/clipping0 및 어시스턴트 표시 TEMP 출처. `User.Scale_All` preset기본값×0.12/0.15를 사용하며 source Fab 패키지는 변경하지 않는다. 실제 gameplay 무적·짧은 피격 계약은 Engineering ARCH-94 기록을 따른다.

<!-- BeastDodge_20261012_MainCompleted -->


## 2026-10-13T02:25:35.076330+09:00 — 현재 효과 알파 카드 경계·HeinMach 눈 수 Main 수정 완료

정본은 `Metadata/ParticleAlpha_20261013/FinalVerification.json`이다. 기존 사용 metadata→현재524 animation의 notify/HeinMach96 effect component→331 PS/NS·281 material interface를 확인했다. 전체 Content/원작 추출을 재조사하지 않았다. 직접 renderer 재질203/부모86, 현재 alpha 입력의 실제138 PNG 채널·부모/인스턴스 상속을 확인했다. HDR4 lookup/검정 float는 PNG 강제 변환하지 않았다.

공용 `Shared/Materials/Other/DefaultParticle`은 PC.A만 opacity mask로 사용해 실제 카드가 흰 사각형이었다. 기존 Masked blend를 유지하고 타원 공간 마스크를 연결했다.16 sprite instance는 실제 sampled texture의 A가255 상수인 채 불투명 카드를 그렸다. 해당 instance에만 R density/particle Alpha 선행 clamp/안쪽 feather를 적용한다. 부모 default repair0과 원래 source RGB·particle modules/shape/수명·event/animation·mesh/Additive 정책은 보존한다. 어시스턴트 표시 TEMP는 feather.03UV/최소1.25px/무텍스처 ellipse power2이며 원작 shader 수치가 아니다.

메인 선택30파일=부모13+MI16+기존 NET_HM_WeatherBudget1을 hash/CAS 전달했다. Source/Config/map/PS/NS/texture/바이너리·QA asset 전달0이다. 기존 눈2레이어의 source1250/2500 particles_s는 그대로이고 생성 scale.25→.20(어시스턴트 표시 TEMP)으로 rate312.5/625→250/500, 기존 대비20% 줄었다. 실제3샘플 평균 flakes2119→1862.33/dust532.67→454.67로 감소했다. 이는 random/time-dependent active count이며 매 순간 정확히20%라는 뜻이 아니다. 눈 크기/속도/수명/재질·camera/원본 actor 배치는 바꾸지 않았다.

새 MainShaderVerify01은86 material compile errors0·16 scalar override·snow.20, MainSnow01은 실제 game view/count/저장0으로 통과했다. standalone 동일 camera card17의 검은 사각·solid card 제거 및 texture 양성을 직접 확인했다. actualPS8 중4는 기본 단독 parameter에서 active0이므로 전체8 양성 화면 검증이라고 기록하지 않는다. 실제 PartGroggy blood/짧은 blade·wood 표본과 눈 entry/sky를 검수했으며 모든 전투 frame/camera·Shipping/원작 shader 전체 동일성은 주장하지 않는다.

초기 protected API/강제 HDR PNG/fixture reentrancy/PIE viewport/반환값·부분 저장 실패는 각 run에 보존했다. Windows 접근 제한은 별도 consumer의 정상 종료 후 선택 전달로 해결했으며 foreign editor 종료/저장/reload0이다. task-owned CardsBefore01 hung fixture만 정확 PID/args 확인 후 정리했다. 모든331 source system과 HeinMach map·눈 graph hash가 원본과 일치한다. 후속은 이 보고서/RepairPlan/TextureChannelAnalysis에서 표적 시작하고 prepare/전체 author/과거 CAS를 반복하지 않는다. 필수 잔여0이다.

<!-- ParticleAlpha_20261013_MainCompleted -->

## 2026-10-13T08:42:00+09:00 — 사용자 패링·적중 사진 비교 자료

[COMBAT_PRESENTATION_FOLLOWUP_20261011.md](COMBAT_PRESENTATION_FOLLOWUP_20261011.md)의 2026-10-13 사진 비교 절을 먼저 읽는다. 참조 사진 2장은 `Metadata/CombatVFXReferenceReview_20261013/References`에 보존했다. 현재 Main Guard의 실제 참조는 3-emitter `PP_Combat_HitBurst`이며 과거 JustGuard 13-emitter 캡처를 현행 패링으로 혼동하지 않는다. GA/HitBurst/혈액 PS의 현재 SHA와 완료 보고서 일치, 실제 성공 패링·적중 캡처, 현재 근사 접점 계산, 8개 보완 항목과 주변 광 영향의 추가 확인을 기록했다. 이 작업은 분석·문서만이며 게임 수정/build/새 PIE는 하지 않았다. 첨부 GiantVFXWork의 Main 미전달 개선을 현재 Main 결과에 합산하지 않았다. 효과 발생·입자 수 통과를 사진 재현 품질 통과로 해석하지 않으며 수명/발생 시점/SFX는 사진만으로 미확인이다.

<!-- CombatVFXReferenceReview_20261013_analysis_complete -->


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery5 role / mesh3 / FT_Trail.G / RGBA ShaderLUT? ?? Heal ??? ????. ?? Heal?Action receipt? ??, runtime1/DEV1/asset13 ?? ??, ? runtime class/tag/manager0. Main build/saved/actual Heal?PlayerAttackCollision2 ?? ?11 effect/alpha ?? ?? ??, ?? ?? ??0. ?? cooked graph ???? ?? native ???/TEMP ??? ?? ???? ????. ??: Art PLAYER_HEAL_VFX_SOURCE_20261013.md / Engineering PLAYER_HEAL_VFX_RUNTIME_20261013.md; evidence Metadata/HealVFX_20261013/FinalVerification.json, ??0.

## 2026-10-13T09:47:37+09:00 — 패링/공격 사진 역할 정정 (08:42 비교 대체)

사용자 정정: **백색 중심·붉은 선은 플레이어 공격, 넓은 분홍·보라 광막은 패링**이다. COMBAT_PRESENTATION_FOLLOWUP_20261011.md의 같은 시간 최신 재판정 절을 먼저 읽는다. 08:42의 역할별 부족점/광막 조건 보류/혈액-보라 광막 결합 제안은 후속 기준에서 철회한다. 올바른 역할의 사진 복사본은 Metadata/CombatVFXReferenceReview_20261013/References/{Attack_LinearWhiteRed,Parry_PinkPurpleHalo}.png이며 이전 오명명 파일은 역사 자료로 보존했다. 현재 필요한 것은 패링 광막·분홍 중심/보라 외곽·작은 보조 sparks, 기존 공격 슬래시의 백색 중심/붉은 외곽 위계·명중 강조·백색 미세 sparks, 두 표현의 설정 구분과 근사 접점의 표적 검증이다. 혈액/바닥 혈흔/무기 추적/알파 개선은 이미 존재한다. 분석·문서만이며 게임 수정/build/새 PIE는 하지 않았다.

<!-- CombatVFXReferenceReview_20261013_user_corrected_roles -->


## 2026-10-13T14:14:46+09:00 — 인간형4·Player SFX 재사용 근거

`Metadata/HumanoidSFX_20261013/FinalVerification.json`이 현재 Main 완료 정본이다. `Inventory02/Inventory.json` current936/58/5/84, `PlaybackPlan01.json` source-parent→raw/inverse map 및 현재 prefix/crop, `AudioAuthoringPlan01.json` final1682/527·source event/field/clock/TEMP/stop, `Coverage01.json` current bound275/quiet hold·approved callback 분류, `NativeCuePlan01.json` 추가원작51cue/262recipe/fallback0, `NativeDecodedImport01.json` original SHA/trim/media reuse, `BankNodeFacts.json` 원본 Wwise action/volume/random/attenuation fields를 재사용한다. `Events01–04/Raw01–04`는 표적 원본 추가이며 기존 two-chunk Index03을 재전수하지 않는다. `Stage01/MainDelivery01`은 최신 Main baseline 보호·선택570 전달, `MainSavedFinal01`은 실제 저장 보존이다. `MixerStage02_RHI` actual78/WAV/finite-tail, `MainInteraction01` 첫3 성공, `MainParry03_Balanced`17성공·peak.768127, `MainDodge01`11성공·original JustDodge/foot+body cue 관측을 구분한다. stale sequential-Parry expired와 raced build 실패를 완료 증거로 읽지 않는다. 임시 callback72/voice.85/foot.9/weapon1/stop.08/parry.5·native sends와 원작 field 직접값/계산을 분리한다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

GiantVFX 재사용 인덱스: 최종원인과숫자=GIANT_VFX_REFINEMENT_20261013.md 마지막 절; 초기49PS/46materials/84sequence author=Metadata/GiantVFX_20261013/AssetAuthor02; actual retained projector=DecalHideIsolation01/RendererHideDiagnostic.json 및 SnowDecalProbe01; source shader/texture/roughness=Metadata/MonsterVFX_20261008/HumanOriginal/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Material/Decal/MI/FMI_Decal_Deferred_D_02.json; actual final23/69PNG=MainSnowDecalFinal01; fullcurrent completion/hashes=FinalVerification.json. Source metadata와 target current material/RuntimeActive material을 분리하며 단독case 양성을 연속case 합격으로 대체하지 않는다.

## 2026-10-14 — Player 일반 적중음 재사용 인덱스

`Saved/ImportReports/GameplayAudio_20261011/BindingAuthor02_Persistent/Bindings.json`은 Player Combo 60창에 공통 `SC_efx_pc_dualaxesword_com_impact`를, 일곱 Definition에 `SC_efx_pc_enemy_hit_{skin,metal,leather,rock,yetuga}`를 연결한 당시 기록이다. 해당 source event 근거는 `Saved/ImportReports/GameplayAudio_20261011/AudioAuthoringPlan01.json`의 약공격 스윙/foley와 BrutalAttack grapple clip 행이다. 2026-10-14 사용자 청취 교정으로 60창 공통 cue만 제거한 준비본은 `Saved/ImportReports/GameplayAudio_20261011/PlayerImpactReview_20261013/Prepared/Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset`; `Metadata/PlayerImpactSFX_20261013/VerifyPrepared01/PreparedReadback.json`이 Main 대비 비오디오 동일성을 증명한다. Main asset은 아직 잠겨 미반영이며 현재 runtime에서 exact cue만 억제한다. 뒤 작업은 `Metadata/PlayerImpactSFX_20261013/FinalVerification.json`과 현재 파일 SHA를 먼저 확인한다.


## 2026-10-15 — HeinMach 색감·혈흔·VFX 색 보존 정본

HEINMACH_COLOUR_VFX_20261015.md → Metadata/HeinMachColourVFX_20261015/FinalVerification.json이 최신이다. 현재 원작 사진/TEMP 조명·혈흔값, 제거한 Arcane Kuwahara 연결, Surface root95 fog/역노출 보상, 현재321 system 목록·두 맵 native 비교, 굴절 QA 배경 차이 및 한계를 재사용한다. 현재 catalogue는 CandidateAudit03/Usage.json이며 CurrentCatalogDelta.json에 패링 효과 교체가 기록돼 있다. broad Content 재조사·FModel 재추출 없이 해당 effect/material만 표적 확인한다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 ? GiantRootUsage ?? ?? ??? ?? ?? ??

Yetuga/Apes root ??? `Metadata/GiantRootUsage_20261015/FinalVerification.json` ? AuditAfter/{Usage,RootAudit}.json ? RuntimeAfter/RootPoses.json? ?????. ??170 sequence/30 montage/2 combo definition, ??162 root on/??? Additive8 off, true-root/track0 ????. RootMotion flag? ??? ????? ANIM_FIRST_FRAME? ?? ??? ?? ? ??. PartGroggy Loop/End4?522.148cm ???? REF_POSE? Main ????? ?? native model/notify170 ? ?????166 ??? ????. ???/Source ???? ?? ?? receipt? ??? ??4/??170 manifest?? ????. Art ??? ENEMY_ANIMATION_ORGANIZATION_20261007.md ?? ???.



## 2026-10-15 — HeinMach GateCube 포탈 조회

GateCube 위치/실제 동굴 지면·포탈 정면·전장 내부 도착점은 HEINMACH_YETUGA_PORTAL_20261015.md 및 Metadata/HeinMachPortal_20261015/{FinalVerification,Placement06/Placement,PortalLook03/PortalLook,Readback04/Readback}.json을 우선한다. 실제 전장 source는 기존 HeinMach_Spawn_Main01.json의 Yetuga_TargetPoint(root470)/SA_Yetuga(root450)이며 Boss_Start는 전장 직전 통로다. 전체 환경을 다시 조사하지 않는다. 실제 화면은 RHI06의3 PNG다.

<!-- HeinMachPortal_20261015_complete -->


## 2026-10-15 — BlueB·Spin donor 조합 재사용 근거

HEINMACH_BLUE_SPINNING_20261015.md와 Metadata/HeinMachLookSpin_20261015/{FinalVerification,MainDelivery02/Receipt,MainSaved01/Verification,ColourFinal03/Comparison}.json을 우선한다. Source timing은 기존 CombinedPlaybackWindows.csv를 재사용하고 새 source 전수조사는 없다. OverFury의 FS_Spline_Helix_08 mesh 두 emitter가 회전 합성에서 회색 막을 만들었고, Spin-only PS의 Required.Material2 교체로 해결했다. shared321+donor/DevMap/KZ_Slash 총324 SHA 유지, 원래176 effects 보존이다. Native pause 촬영은 render-settle와 QA screen message 숨김이 필요하며 기존 실패 촬영은 최종 색 근거가 아니다.

<!-- HeinMachLookSpin_20261015_complete -->

## 2026-10-15 — 원작 Yetuga 전투 BGM 조회

정본: YETUGA_BGM_SOURCE_20261015.md. 원본 chunk0 Media446487212, DebugName Music\boss\bgm_boss_yetuga_82_4on4.wav와 HeinMach start/pre_01 battle switch branch를 확인했다. Metadata/YetugaBGM_20261015/SourceMusic.json 및 Raw/AudioFileExtractionReport.json에 fresh 원본 hash·clip/gain·계산된 intro/loop sample 경계가 있다. 기존 음악 fallback12/다른 SFX 전체 author를 재실행하지 않는다. Main 음악4asset는 Import01/Import.json, 실행은 Engineering 포탈 최신 절과 Implementation.json을 따른다. 사용자 정정으로 사망/처치/이탈 종료0이며 원본 loop를 유지한다.


## 2026-10-16 ? HeinMach ?? ?? ??/?? ??

HEINMACH_ROUTE_PRUNING_20261016.md ? Metadata/HeinMachRoutePrune_20261016/FinalVerification.json?Selection.json?MainSaved01/InventoryVerification.json? ?? ???. ?? map SHA1d224b14?? ?? ?? ?? ?? ?? ??? ?? ???. ??1? inventory/552 depth/48? ??? ????? ???????? ???? ???? ???. instance9137 ? foliage8296/?? ??841??. source mesh transform?world AABB? ???? stale NullRHI bounds/?? collision ?? ?? ?? warm full-editor ??? ???. ?? RoutePruneExclusions ??? ?? Player metadata ???. Before umap?37.8MB ???? ?? ?? ??? ??? ???? ??? ????.


## 2026-10-16 — HeinMach 사용 구간 정리 조회 (한글 기록 정정)

앞선 같은 작업의 한글 출력 오류 절은 HEINMACH_ROUTE_PRUNING_20261016.md와 이 절로 정정한다. Metadata/HeinMachRoutePrune_20261016/FinalVerification.json·Selection.json·MainSaved01/InventoryVerification.json을 먼저 읽는다. 현재 map SHA1d224b14이며 전량 복원 보고서로 삭제 배치를 되살리지 않는다. actor4258/instance9137 중 foliage8296/경로 충돌841. Depth552뷰/48시야쌍과 warm RHI 정합성 보고서를 재사용하고 stale NullRHI bounds/즉시 collision snapshot을 canonical로 삼지 않는다. Player metadata의 RoutePruneExclusions와 Before 원본이 복구 근거다.
