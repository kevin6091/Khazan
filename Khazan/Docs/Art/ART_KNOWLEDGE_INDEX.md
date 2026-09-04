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
