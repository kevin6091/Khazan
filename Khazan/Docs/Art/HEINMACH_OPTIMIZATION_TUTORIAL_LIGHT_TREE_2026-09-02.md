# HeinMach 최적화·튜토리얼·조명·나무 복원 기록

## 완료 기준

- 라이브 맵: `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`
- 최종 맵 SHA-256: `B7EB531B09D504737CA1CC6125B201484519D8FA1D80FA0A00249482FCABFCA7`
- 사용자 편집 직후 원본 백업: `Saved/ArtBackups/HeinMach_UserEdited_BeforeOptimization_20260902_161357/L_HeinMach_Environment.umap`
- 백업 SHA-256: `17581BC984432060C3B194A9871D42E884024F7F23402EEE3E70A635768AA799`
- 최종 감사: `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`, `all_checks_passed=true`, 39/39 통과
- 이번 검수는 metadata/report와 UE Python 표적 감사를 사용했으며 스크린샷 API는 사용하지 않았다.

## 사용자 삭제 오브젝트 보호

사용자가 단면 노출 또는 어색한 배치 때문에 직접 삭제한 10개 액터는 복원 대상이 아니다. 정본 tombstone은 `Content/_Art/Kazan/Environment/HeinMach/Metadata/HeinMach_UserExclusions.json`이다.

- root Prop 3개
  - `HM_Prop_HeinMach_SubLV01_OP_389_WP_CTR_Rock_Big_005_Inst64`
  - `HM_Prop_HeinMach_SubLV01_OP_643_WP_VFS_Rock_Big_016_Inst_5`
  - `HM_Prop_HeinMach_SubLV01_OP_650_WP_VFS_Slope_Soil_002_a_Inst36`
- Landscape proxy 6개
  - `HM_Landscape_Landscape1_LandscapeComponent_36`
  - `HM_Landscape_Landscape1_LandscapeComponent_37`
  - `HM_Landscape_Landscape1_LandscapeComponent_38`
  - `HM_Landscape_Landscape1_LandscapeComponent_44`
  - `HM_Landscape_Landscape1_LandscapeComponent_45`
  - `HM_Landscape_Landscape1_LandscapeComponent_46`
- legacy terrain 1개
  - `HM_Terrain_Landscape1`

모든 HeinMach 배치·복원·감사 스크립트는 위 파일의 `do_not_restore=true`를 먼저 읽어야 한다. 원본 metadata에 존재한다는 이유로 재생성하면 안 된다.

## 보수적 최적화

- 실행 스크립트: `Scripts/HeinMach/optimize_heinmach_conservative.py`
- 결과: exact duplicate group 107개에서 중복 액터 109개 제거
- 액터 수: 사용자 편집 상태 9,442개에서 9,333개로 감소한 뒤 튜토리얼 앵커 3개를 추가해 최종 9,336개
- 삭제 목록 정본: `Content/_Art/Kazan/Environment/HeinMach/Metadata/HeinMach_OptimizationExclusions.json`
- 상세 리포트: `Saved/ImportReports/HeinMach_ConservativeOptimization.json`
- 삭제 label SHA-256: `92cab25e854d30e2276b309a18d91db1ea43209ccbbe2ca6aba85f608f59963d`

삭제 허용 조건은 단일 StaticMeshComponent를 가진 `HM_Prop_`끼리 mesh, resolved material, transform, visibility, render flag, shadow, reverse culling, mobility, collision state, tag가 모두 동일한 경우뿐이다. 이름에 `Collision`이 포함됐다는 이유, 플레이 경로와의 거리, occlusion 추정, source layer만으로는 삭제하지 않는다. 제거된 109개도 이후 복원에서 재생성하지 않는다.

## 수동 좌표 보호

`HM_Prop_HeinMach_SubLV01_OP_412_WP_CTR_Rock_Big_005_Inst87`은 사용자 편집 맵에서 이미 원본과 다른 위치였다. 원본 Z `-1012.6782` 대신 편집된 Z `-6962.6782`를 유지한다. 메시 world extent가 약 `10951 x 9026 x 11916 cm`이므로 actor origin만 보고 비가시 dummy로 판단할 수 없다.

정본은 `Content/_Art/Kazan/Environment/HeinMach/Metadata/HeinMach_ManualOverrides.json`이며, 복원 스크립트는 `do_not_reset=true`인 `preserved_transform`을 사용한다.

## DualAxeSword 공격 튜토리얼 공간

- source layer: `HeinMach_Spawn_Main01`
- PlayerStart: `HM_Tutorial_PlayerStart_DualAxeSword`, `(12073.493, 24725.363, 303.5308)`, yaw `245.0138`
- 적 앵커 1: `HM_TutorialSpawn_01_EmpireSword`, `(14443.049, 11226.91, 202.70361)`
- 적 앵커 2: `HM_TutorialSpawn_02_EmpireSwordShield`, `(18664.227, 3837.669, 35.0254)`
- Outliner 폴더: `HeinMach/Reconstructed/Tutorial_DualAxeSword`
- 복원 스크립트: `Scripts/HeinMach/restore_heinmach_dualaxe_tutorial.py`
- 리포트: `Saved/ImportReports/HeinMach_DualAxeTutorial_Restoration.json`

원본 환경, PlayerStart, 적 위치 앵커까지가 Art 복원 범위다. 실제 적 Blueprint/AI spawn, 공격 안내 UI, 완료 gate, DualAxeSword 강제 장착은 Engineering 통합 범위다. `HeinMach_Cine_Opening*` 및 맨손 비틀거림/기본 이동 장면은 계속 제외한다.

## Light 색상 최종 감사

FModel의 `LightColor`는 이미 sRGB byte 값이다. 이를 0–1로 정규화한 뒤 `SetLightColor(..., True)`로 넘기면 이중 sRGB 변환이 발생한다. 예를 들어 원본 `(216,161,111)`이 `(237,208,176)`으로 변형됐다.

- source light 89개는 raw `unreal.Color(R,G,B,A)`를 `light_color`에 직접 기록한다.
- `bUseInverseSquaredFalloff`, `LightFalloffExponent`, `MaxDrawDistance`, `MaxDistanceFadeRange`, `IndirectLightingIntensity`도 source metadata와 일치시켰다.
- route fill 5개처럼 코드에 linear color로 선언한 값만 `SetLightColor(..., True)`로 변환한다.
- 수정 전 property mismatch 155개, 최종 source mismatch 0개, route-fill mismatch 0개다.
- source light transform SHA-256은 `c87a605a9227f5a4f7426d27a8b4f6bbdc6eeed1baa1f138672f9616e1f3c0f7`로 유지됐다.
- 감사 스크립트: `Scripts/HeinMach/audit_fix_heinmach_light_color.py`
- 리포트: `Saved/ImportReports/HeinMach_LightColor_Metadata_Audit.json`

## 흰색 나무 머티리얼

흰색 가지는 원작의 눈 표현이 아니라 FModel/USD가 inherited/null LOD material을 내보낼 때 생긴 fallback이었다.

- 범위: `SM_WP_VFS_Tree_Dry_004`, `005`, `006`의 가지 slot
- 문제 material: `MI_WM_VFS_Tree_Branch_001_LOD`, `_LOD_0`, `_LOD2`
- 문제 상태: `/Engine/.../WhiteSquareTexture`, `UseBaseColorTexture=0`, flat normal
- source 증거: `WM_VFS_Tree_Branch_001_LOD2.json`은 `IsNull=true`, texture 0개지만 Masked/TwoSided/clip `0.3333`을 상속한다.
- 복구 근거: 동일 family의 `WM_VFS_Tree_Branch_001_02.json`은 정확한 Diffuse/Normal/Specular/Emissive texture를 가진다.
- 복구 material: `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/RecoveredMaterials/Trees/MI_WM_VFS_Tree_Branch_001_LOD2_Recovered`
- 수정 결과: 27개 actor의 문제 slot만 교체, placeholder slot 0개, transform 변경 0개
- 스크립트: `Scripts/HeinMach/repair_heinmach_white_trees.py`
- 리포트: `Saved/ImportReports/HeinMach_WhiteTreeMaterial_Repair.json`

## 최종 인벤토리와 재개 순서

최종 액터는 9,336개이며 categorized 9,336, uncategorized 0이다. 구성은 root Prop 8,992, child Prop 27, foliage batch 113/HISM instance 12,495, Landscape proxy 51, terrain 1, Fog sheet 50, source light 89, preview environment 4, route fill 5, preview volumetric fog 1, tutorial anchor 3이다.

재개 시 다음 순서만 사용한다.

1. `HeinMach_UserExclusions.json`, `HeinMach_OptimizationExclusions.json`, `HeinMach_ManualOverrides.json`을 먼저 읽는다.
2. `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`을 확인한다.
3. 실패한 세부 리포트만 표적 재검사한다.
4. source snapshot 또는 metadata schema가 바뀐 경우에만 FModel 전수조사를 다시 수행한다.

## 2026-09-02 요청 범위 재확인 및 라이브 재감사

- 캐릭터 이동, AnimInstance, 입력, 전투, Enemy AI와 그 밖의 C++/Gameplay BP는 이번 HeinMach Art 작업 범위가 아니다. 현재 소스 롤백은 사용자가 의도한 상태이므로 Level 복구의 미완료 신호로 해석하거나 수정하지 않는다.
- 허용 범위는 라이브 맵의 source Light, 흰 나무 material slot, DualAxeSword 튜토리얼용 Level 오브젝트 구성뿐이다. 튜토리얼 구성은 source PlayerStart 1개와 enemy 위치 TargetPoint 2개까지이며, 캐릭터·무기·애니메이션·UI·AI 콘텐츠는 만들거나 연결하지 않는다.
- 라이브 맵 SHA-256은 `B7EB531B09D504737CA1CC6125B201484519D8FA1D80FA0A00249482FCABFCA7`로 기존 최종 기준과 동일하다.
- 에디터 read-only 재감사에서 source Light 89개와 route fill 5개는 property/color mismatch 0개였고, source transform hash는 `c87a605a9227f5a4f7426d27a8b4f6bbdc6eeed1baa1f138672f9616e1f3c0f7`로 유지됐다.
- 대상 나무 actor 27개는 recovered branch material을 정확히 27 slot에 사용한다. suspicious white placeholder slot은 0개다.
- `HM_Tutorial_PlayerStart_DualAxeSword`, `HM_TutorialSpawn_01_EmpireSword`, `HM_TutorialSpawn_02_EmpireSwordShield`는 source transform 오차 0, 필수 tag/folder 일치 상태다. `HeinMach_Cine_Opening*` 및 맨손 오프닝 오브젝트는 0개다.
- `HeinMach_Final_Reconstruction_Audit.json` 재실행 결과는 actor 9,336, uncategorized 0, 39/39 통과다. mismatch가 없어 맵·Material·Level actor는 다시 저장하거나 변경하지 않았다.

## 2026-09-04 전역 Fog·FogSheet·배치·머티리얼 재검토

### 범위와 보호 기준

- 라이브 맵은 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`다.
- 이번 변경은 전역 Fog, FogSheet, 환경 머티리얼/셰이더 검증으로 제한했다. `Source/Khazan/Animation/KhazanAnimInstance.h`와 그 밖의 Source/Gameplay/캐릭터 콘텐츠는 열어 수정하지 않았다.
- `HeinMach_UserExclusions.json` 18개와 `HeinMach_OptimizationExclusions.json` 109개를 합친 127개 tombstone은 변경 전후 모두 맵에 없었다. 복구 스크립트는 비-Fog actor를 생성하거나 복원하지 않도록 제한했다.
- 최초 저장 전에 라이브 맵이 안전 백업과 같은 SHA-256 `8C8BA2E50A840301FF12035FC536249763D415CD1603DB633FA5A1097F693221`인지 검사했다. 백업은 `Saved/ArtBackups/HeinMach_PreFogReview_20260904_143116`이며 203 files, 81,976,761 bytes다.

### source 근거와 발견한 결함

- FModel export `WBP_FogSheet.json`의 source component 정책은 collision, shadow, decal, occluder, dynamic indirect lighting, distance-field lighting, navigation 영향이 모두 꺼진 상태다.
- source FogSheet는 50개이며 `FMI_FogSheet_02` 49개, `FMI_FogSheet_01` 1개다. 전부 one-sided이고 `FTW_Smoke_Noise_001`을 사용한다.
- 기존 preview parent는 41-node 구형 graph와 64-node 후속 graph가 한 asset에 같이 남아 expression 105개, `MaterialExpressionPixelDepth` 2개 상태였다. 이 화면 공간 fade는 근접/교차 시 sheet 절단 위험이 있다.
- 기존 전역 Fog는 `fog_cutoff_distance=70000`이라 월드 공간 하드 경계가 있었고, positional `Color` 생성 때문에 intended `(158,177,196)`이 실제 `(196,177,158)` 순서로 저장돼 있었다.
- source WEP metadata는 outdoor/boss/blizzard/escape/OP 구역에서 `FOG_Deep`, cave에서 `FOG_Dark`를 전환한다. 이 controller 구현은 현재 추출물에 없다.

### 적용한 교정

- 기존 V4 asset을 덮어쓰지 않고 새 parent `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FogSheets/Materials/M_HeinMach_FogSheet_Preview_V5`를 만들었다.
- V5는 source 2-octave noise/pan/opacity/edge/depth 특성을 유지하면서 near/far 계산을 `Distance(WorldPosition, CameraPositionWS)`로 교체했다. `DepthFade`와 `abs(dot(PixelNormalWS, CameraVectorWS))` 기반 facing fade를 함께 사용한다.
- 최종 graph는 expression 75개, `PixelDepth` 0개, Translucent/Unlit, depth test 활성, two-sided 비활성이다. metadata version은 5, distance model은 `EuclideanWorldSpace`다.
- FogSheet MI 50개를 V5에 연결하고 각 source MaxOpacity, NearFade, FadingStart/Reduction, pan rotation/speed, noise texture, tint와 actor sort priority를 유지했다.
- 50개 component는 source `WBP_FogSheet` 정책대로 shadow/decal/occluder/lighting/navigation/overlap/collision 영향을 끄고 visible/not-hidden 상태를 유지했다.
- 전역 `HM_PreviewVolumetricFog`는 1개만 유지했다. cutoff는 0, albedo는 normalized `(0.619607843, 0.694117647, 0.768627451)`로 교정했다. density `0.0045`, falloff `0.12`, max opacity `0.55`, volumetric distance `30000` 등 기존 보수적 preview 값은 유지했다.

### 재로드 검증 결과

- 최종 actor 9,328개가 전부 분류됐다: prop 8,987, child 27, foliage batch 113/HISM instance 12,495, Landscape static 48, terrain 1, FogSheet 50, source light 89, preview environment 4, route fill 5, global fog 1, tutorial 3.
- 수정 전후 actor count, label set, 전체 transform signature가 같다. 127개 tombstone도 계속 부재한다.
- FogSheet source record 50개 대비 missing/unexpected/mesh/material/parent/sort/transform/component-policy mismatch가 모두 0이다. location/scale 최대 오차는 0, rotation 최대 오차는 `4.9072265539962245e-6°`다.
- 나무 전수 감사: 1,123 actor, 1,123 component, 1,669 material slot, 100 unique material, suspicious group/slot 0.
- 환경 렌더 머티리얼 감사: 605 unique material, 11,460 managed slot, packed channel correct 584/584, channel repair 필요 0, opaque parent repair 필요 0, effective Translucent 0.
- V5 표적 recompile은 예외 없이 완료됐다. 로그의 shader compile error, `Failed to compile`, `LogMaterial: Error`는 0이다.
- 최종 정본은 `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`의 `all_checks_passed=true`, 43/43다. Fog 전용 근거는 `HeinMach_FogIntegrity_Review.json`, 나무는 `HeinMach_TreeMaterial_FullAudit.json`, 전체 표면은 `HeinMach_MaterialRendering_Audit.json`이다.
- 6개 source PlayerStart route anchor의 전후 viewport는 `Saved/ArtValidation/HeinMach_Fog_Review_20260904`에 있으며, 재로드 후 화면 경계형 Fog 절단이나 새 geometry bleed는 관찰되지 않았다.
- 최종 `.umap` SHA-256은 `B209ACB34FCEFC3D6F11EE47D098107976CA30B6A84CFA16335EA6638C2812E0`이다.

### 재개 기준

1. `HeinMach_UserExclusions.json`, `HeinMach_OptimizationExclusions.json`, `HeinMach_ManualOverrides.json`을 먼저 확인한다.
2. `HeinMach_Final_Reconstruction_Audit.json`과 `HeinMach_FogIntegrity_Review.json`을 확인한다.
3. Fog 문제가 재현될 때만 V5 parent, 50개 MI binding, 해당 route capture를 표적 확인한다.
4. source snapshot/schema가 바뀌지 않았다면 FModel 전수 추출이나 비-Fog actor 복원을 반복하지 않는다.

cooked proprietary Fog master graph와 구역별 `FOG_Deep`/`FOG_Dark` 전환 controller가 없는 한 단일 preview를 원작 런타임의 완전 복제로 표현하지 않는다. 현재 상태는 추출 가능한 source placement/parameter/component policy를 보존하면서 화면 절단 위험을 제거한 안전한 UE5 복구본이다.
