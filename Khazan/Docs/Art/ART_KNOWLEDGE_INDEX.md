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
