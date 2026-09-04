# StormPass 환경 Level 복원 — 2026-09-03

## 작업 경계

- 대상 맵: `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment`
- 대상은 환경 Level의 정적 오브젝트, Landscape proxy, foliage, 원본 Light, Fog, 시각 머테리얼뿐이다.
- 캐릭터 이동, 전투, AI, 퀘스트, UI, 오디오, Gameplay BP, C++ 소스는 수정하지 않았다.
- WaterBody의 collision/navigation 값은 원본 JSON에서 분석만 했고 프로젝트에서는 변경하지 않았다.
- HeinMach는 별도 사용자 편집본으로 취급했다. `HeinMach_UserExclusions.json`의 `do_not_restore=true` 18개를 복원하지 않았으며 HeinMach 맵에는 이번 StormPass pass가 쓰지 않았다.

## 중단 상태 진단과 복구

- 중단 재개 시 라이브 StormPass 맵이 과거 14,058 actor 체크포인트로 돌아가 있었다.
- 당시 root/child/Landscape는 남아 있었지만 foliage 218개와 source Light 53개가 없었고, 진단용 `SP_Foliage_ComponentApiProbe` 1개가 남아 있었다.
- 사용자가 만든 오브젝트를 추정 삭제하지 않고, 명확히 작업 도구가 만든 probe 1개만 제거했다.
- 검증된 pre-Light 맵과 저장 report를 기준으로 foliage와 Light를 다시 복구한 뒤 각각 저장/재로딩 감사했다.

## 최종 구성

| 영역 | 최종 수량 | 검증 |
| --- | ---: | --- |
| root StaticMesh prop | 13,050 actor / 271 mesh | mesh, transform, mobility, shadow, 7,717 render override 일치 |
| child StaticMesh prop | 551 actor / 44 mesh | transform 일치, material override 123/123 |
| Landscape geometry proxy | 456 actor | Main 440 + Boss 16, component/material failure 0 |
| foliage | 218 HISM / 21,259 instance | 19 mesh, override 50, instance transform failure 0 |
| source Light | 53 | Point 52 + Spot 1, JellyFish IES 42, property/transform failure 0 |
| Fog | 53 | Standard 51 + Local 2, transform/material/parameter failure 0 |
| native custom water | 2 | 원본 actor material binding 및 actor별 색 파라미터 일치 |
| 전체 | 14,381 actor | 예상 밖 actor/중복/누락 0 |

## Light

- `StormPass_Light`와 관련 streamed level의 source JSON에서 53개를 복구했다.
- Point Light 52개, Spot Light 1개이며 원본 JellyFish IES 참조가 있는 42개는 복원 IES profile에 연결했다.
- 최종 최대 오차는 위치 0 cm, 회전 약 `0.00000171°`, scalar property 약 `0.00000362`다.
- 정본 감사: `Saved/ImportReports/StormPass_Light_ReloadAudit.json`과 최종 통합 감사의 `stages.lights`.

## Fog — 최종 쓰기 단계

- FModel source는 `WBP_FogSheet_C` 51개와 `WBP_FogSheet_Local_C` 2개다.
- source parent 분포는 `FMI_FogSheet_02` 45, `FMI_FogSheet_01` 6, `FM_FogSheet_Local` 2다.
- exact source mesh 2종과 `FTW_Smoke_Noise_001` 1024×1024 texture를 사용한다.
- actor 53개의 transform, source parent variant, two-sided 정책, scalar/vector/texture parameter를 개별 MIC로 보존했다.
- 최초 복구 도중 Rotator positional 인자 순서가 UE Python과 달라진 문제를 발견했고, `pitch=`, `yaw=`, `roll=` named argument로 교정했다.
- WaterBody 보완 이후 Fog를 다시 적용해 요청대로 Fog가 마지막 Level 쓰기 단계가 되게 했다.
- 재로딩 감사 최대 오차는 위치 0 cm, 회전 약 `0.00000242°`, scale 0이며 failure 0이다.
- cooked custom Fog parent graph는 FModel 추출물에 없으므로 animated noise, edge/depth/near/far fade를 포함한 UE5 preview parent를 사용한다. 원본 graph 자체의 완전 복제로 표기하지 않는다.

## native WaterBody 흰 체크 재질 복구

다음 두 child actor는 component `OverrideMaterials=[null]`이 정상 source 값이다. 원작의 `xxWaterBodyCustomActor`가 actor의 `WaterMaterial`을 런타임에 slot 0에 넣기 때문에 일반 child 복원만으로는 `WorldGridMaterial`이 남았다.

- `SP_ChildProp_StormPass_Boss_Phase_1_02379_00076`
  - source material: `Water_Material_StormPass_CustomMesh_AK`
  - `EffectColor=(5, 0.15, 0.15, 1)`, `FoamColor=(0.25, 0, 0, 1)`
- `SP_ChildProp_StormPass_Boss_Phase_2_02538_00179`
  - source material: `Water_Material_StormPass_CustomMesh_AK_Inst1`
  - `EffectColor=(5, 0.1, 0.1, 1)`, `FoamColor=(0.4, 0, 0, 1)`

FModel에서 다음 4개 material JSON과 참조 texture 11개의 원본 PNG/JSON을 추가 추출했다.

- `Water_Material_AK`
- `Water_Material_SkoffaCave_CustomMesh_AK`
- `Water_Material_StormPass_CustomMesh_AK`
- `Water_Material_StormPass_CustomMesh_AK_Inst1`

복원 asset은 `/Game/_Art/Kazan/Environment/StormPass/Reconstructed/WaterAssets`에 있다.

- source material instance parent chain 3단을 그대로 구성했다.
- master의 source parameter inventory 138 scalar, 12 vector, 13 texture를 유지했다.
- exact source texture 11개에 원본 sRGB/compression 설정을 적용했다. 여기에는 비표시 foam-info 기본값 두 곳이 공유하는 `BASE_Black_NoneSRGB`도 포함한다.
- actor별 `EffectColor/FoamColor`를 별도 MIC 2개에 보존했다.
- 원본 base override인 TwoSided, Masked, SingleLayerWater, clip 0.3333을 적용했다.
- cooked `Water_Material_AK` graph는 FModel JSON에 shader topology가 없어 UE5 SingleLayerWater preview graph로 재구성했다. texture/parameter/instance 계층은 exact지만 proprietary graph 자체는 근사다.
- 최종 master는 expression 331개, sampler 10개, pixel texture sample 11개다. 최종 강제 재컴파일 이후 새 `LogMaterial` warning/error는 0개다.
- 저장/재로딩 감사에서 material hierarchy/actor binding failure 0, parameter check 79/79다.

정본 metadata/report:

- `Content/_Art/Kazan/Environment/StormPass/Metadata/StormPass_NativeWaterMaterials.json`
- `Saved/ImportReports/StormPass_NativeWaterMaterial_Restoration.json`
- `Saved/ImportReports/StormPass_NativeWaterMaterial_ReloadAudit.json`

## 최종 감사와 정본

- 정본 report: `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json`
- 결과: `status=passed`, failed stage 0.
- 전체 material slot 17,976개 중 null 0, WorldGrid/Default material 0.
- 최종 맵 크기: 43,544,493 bytes.
- 최종 SHA-256: `3719E53A6B2CEBED831DA586E04BFF13C1C5B76DAE5D2A5FDEA4C45DB42B03CA`.
- 시각 확인용 Water MIC preview:
  - `Saved/Screenshots/WindowsEditor/RiderMCP/20260903-060257_preview_MI_SP_Water_Boss_Phase_1_Actor_02379.png`
  - `Saved/Screenshots/WindowsEditor/RiderMCP/20260903-060313_preview_MI_SP_Water_Boss_Phase_2_Actor_02538.png`

## 백업과 재개 순서

- pre-Fog map: `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment_PreFogRestore`
- pre-native-water map: `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment_PreNativeWaterRestore`
- 최종 검증 스냅샷: `Saved/ArtBackups/StormPass_Verified_Final_20260903_145740`
- 스냅샷 `.umap` SHA-256은 라이브 맵과 동일하다.

회귀가 의심되면 다음 순서로만 확인한다.

1. `StormPass_Final_Reconstruction_Audit.json`의 failed stage를 확인한다.
2. 실패한 stage의 reload audit만 표적 실행한다.
3. Water 흰 체크 재질이면 `StormPass_NativeWaterMaterials.json`과 두 label의 slot 0만 확인한다.
4. source snapshot/schema가 바뀐 경우에만 FModel 전수조사를 다시 한다.

## 2026-09-03 source default texture closure

- Water master의 비표시 `SurfaceWaterFoamInfo`와 `WaterFoamInfo`가 공유하는 source `BASE_Black_NoneSRGB` PNG/JSON을 추가 추출했다.
- source water texture는 최종 11개이며 두 parameter default를 exact texture로 연결했다. 미해결 source texture default는 0이다.
- 이 추가 저장 뒤 Fog를 다시 마지막 쓰기 단계로 적용했고 Fog/Water/통합 reload audit를 모두 재실행했다.
- 앞 절의 `3719...` hash와 `StormPass_Verified_Final_20260903_145740`은 이 closure 직전의 검증 체크포인트다.
- 최신 최종 SHA-256은 `F63A6C8D66C3F5D6A677EF00B2AECDB4406A6B229AB7C4DB1E4D42F25CC2C91E`다.
- 최신 최종 스냅샷은 `Saved/ArtBackups/StormPass_Verified_Final_20260903_151800`이며 `.umap` hash가 라이브 맵과 일치한다.

## 2026-09-04 위치·환경·표면 교정 및 최종 closure

### 위치 재검토

- 원본 scope는 streaming level 52개 중 시각 환경 sublevel 38개다. 저장 metadata와 기존 canonical report를 다시 대조했으며 phase/background object를 임의로 숨기거나 이동·삭제하지 않았다.
- root prop 13,050개는 누락·초과 0, 최대 location 오차 0 cm, rotation 오차 `0.00009155°`, scale 오차 0이다.
- child prop 551개는 placement/material mismatch 0이다.
- Landscape proxy 456개(Main 440 + Boss 16)는 component/material failure 0이다.
- foliage HISM 218개/instance 21,259개는 최대 location 오차 0 cm, rotation 오차 `0.00000639°`, scale 오차 `2.32e-7`이며 failure 0이다.

### Environment profile과 Light

- source environment profile 27개를 별도 관리 prefix로 구성했다: Directional Light 1, Exponential Height Fog 1, Post Process Volume 11, Sky Light 1, Sphere Reflection Capture 9, Static Mesh 3, Wind Directional Source 1.
- Directional Light actor scale을 metadata/default와 같은 `(1,1,1)`로 교정했다. sky/cloud mesh는 `set_collision_enabled(NO_COLLISION)`로 검증 가능한 collision-off 상태를 적용했다.
- environment profile 최대 오차는 location `3.64e-12` cm, rotation/scale 0, scalar property `4.77e-8`이며 failure 0이다.
- source Light 53개(Point 52 + Spot 1, JellyFish IES 42)는 location 오차 0 cm, rotation `0.00000171°`, scalar property `0.00000362` 이내이며 failure 0이다.

### 나무·world prop·ore material

- 흰색 fallback처럼 보이던 나무 계열 MI 9개를 source BaseColor/Opacity/Normal/Emissive texture와 packed `_S`의 AO=R, Roughness=G 규칙으로 재구성했다. 사용 slot은 733개다.
- tree parent는 `/Game/_Art/Kazan/Environment/StormPass/Reconstructed/MaterialRepairs/Trees/M_SP_SourceTreeFoliage_V2`다.
- source에서 `EmissiveOn` override가 없던 world prop MI 5개는 잘못 켜진 `UseEmissiveColorTexture`만 해제했다. 영향 범위는 44 slot이다.
- ore 계열 MI 4개는 `WM_BBQProp_Ore -> WM_COM_Ore_White_002 -> variant` 계층과 source `GlowColor`, `BaseEmissiveAmount`, `TexBrightness`, texture를 반영했다. 사용 slot은 860개다.
- ore parent는 `/Game/_Art/Kazan/Environment/StormPass/Reconstructed/MaterialRepairs/Ore/M_SP_SourceOre_V2`다.
- 초기 parent의 Masks sampler 기본 texture 호환 문제는 기존 asset을 삭제하지 않고 V2 parent로 우회했다. V2는 실제 `TC_MASKS` source texture를 기본값으로 사용하며 tree/ore texture expression은 각각 5/6개, sampler failure 0이다.
- V2 작업 이후 `Saved/Logs/Khazan.log` 2,477줄에서 `Failed to compile` 또는 `Sampler type` 오류는 0이다.
- 검증 preview는 `20260904-021403_preview_MI_WM_COM_SmallTree_Base_003_02.png`, `20260904-021409_preview_MI_WM_COM_Ore_White_002.png`다.

### Fog-last와 최종 정본

- 위의 모든 environment/material 변경 뒤 Fog를 마지막 콘텐츠 쓰기 단계로 재실행했다.
- Fog는 Standard 51 + Local 2 = 53개이며 누락·초과 0, 최대 location 오차 0 cm, rotation `0.00000242°`, scale 오차 0, material/parameter failure 0이다.
- 최종 actor는 14,408개이며 recognized 14,408, unrecognized 0, duplicate label 0이다.
- 전체 material slot은 17,979개이며 null 0, WorldGrid/Default material 0이다.
- `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json`은 `status=passed`, failed stage 0이다. 감사 자체는 `map_modified=false`인 읽기 전용 단계다.
- 최종 `.umap` 크기는 43,709,400 bytes, SHA-256은 `9A4B02BE61CA734265B91490828B6369B69CC3428D7A82726CEA215B770D9191`다.
- `Saved/ArtBackups/StormPass_Verified_Final_20260904_111819`에 동일 hash 맵과 핵심 report 9개를 보존했다.
- cooked proprietary tree/ore graph topology는 FModel metadata에 없으므로 source texture/parameter를 사용하는 UE5 native preview graph다. 또한 source의 불규칙 BSP Post Process Volume 6개는 point/plane metadata를 보존하면서 exact transformed bounds로 표현한다.
- Gameplay/C++/캐릭터 로직과 HeinMach는 이 closure에서 수정하지 않았다.

## 2026-09-04 sky/Fog 화면 절단 재현·교정

### 재현과 원인 분리

- main/boss 방향의 viewport에서 화면을 가로지르는 단단한 회색 경계를 재현했다.
- Fog sheet 53개를 진단용으로 일시 숨겼을 때 경계는 유지됐고, cloud mesh 두 개를 일시 숨겼을 때 사라졌다. 모든 임시 visibility는 즉시 복원했으며 최종 temporary-hidden actor는 0이다.
- source `WAS_CloudMesh.usda`는 local Z 0..93,238.984 cm인 상부 hemisphere다. 기존 preview cloud는 source `HorizonVisibilityMin/Max`를 사용하지 않고 `disable_depth_test=True`여서 hemisphere의 바닥 경계가 geometry 위에 화면 밴드처럼 보였다.
- source sky/cloud USD UV의 V 범위는 -1..0이며 wrapping된다. 이를 sky 수직 색 보간에 직접 사용한 기존 graph는 seam/wedge를 만들 수 있었다.
- 기존 Fog parent의 near/far fade는 `PixelDepth` 기반이었다. 큰 plane에 가까워지거나 카메라가 sheet를 교차하면 actor와 무관한 화면 축 경계가 나타날 수 있는 구조였다.

### V2 visual material

- sky parent `/Game/_Art/Kazan/Environment/StormPass/Reconstructed/EnvironmentAssets/Materials/M_SP_SourceSky_V2`는 `WorldPosition - ActorPositionWS`의 normalized Z를 사용한다. source `Horizon Falloff`, `Bottom color`, `Sky Color`, `Overall Color` parameter와 source texture binding을 유지했다.
- cloud parent `/Game/_Art/Kazan/Environment/StormPass/Reconstructed/EnvironmentAssets/Materials/M_SP_SourceCloud_V2`는 source `HorizonVisibilityMin/Max`에 따른 월드 높이 fade를 복구했고 depth test를 활성화했다. layer 1/2의 source color/intensity/amount/UV parameter 및 density/distortion/lookup/normal texture를 유지했다.
- environment actor assignment는 `MI_SP_Sky_GloomyDay_V2`, `MI_SP_Cloud_White_Layer1_V2`, `MI_SP_Cloud_GloomyDawn_Layer2_V2`로 교체했다.
- Fog parent는 `M_SP_FogSheet_FMI_02_OneSided_V2`, `M_SP_FogSheet_FMI_01_TwoSided_V2`, `M_SP_FogSheet_Local_TwoSided_V2`다. 세 graph 모두 `PixelDepth`가 없고 `Distance(WorldPosition, CameraPositionWS)`, source near/far parameter, `DepthFade`, `abs(dot(PixelNormalWS, CameraVectorWS))` 기반 facing fade를 사용한다.
- Fog actor 53개는 source transform, mesh, sort priority, two-sided policy, scalar/vector/texture parameter를 유지했다. parent 분포는 45/6/2다.

### 배치·Light·머테리얼 재검토

- 전체 배치 감사는 root 13,050, child 551, Landscape 456, foliage HISM 218/21,259 instance에서 failure 0이다.
- 화면을 크게 가리던 `SP_Prop_StormPass_Background_32_WLP_COM_Background_Mountain_29`의 transform은 source metadata `(189247.62, 197409.36, 5108.6494)`, rotation `(-5.1284, -74.4881, -2.35469)`, scale `(7.48, 7.48, 3.09)`와 정확히 일치했다. 배치 오류가 아니므로 이동·삭제하지 않았다.
- sky parent 교체 직후 원경 산과 나무가 검게 보인 것은 SkyLight가 이전 invalid/black capture를 보존한 상태였다. `SP_Environment_SkyLight`를 deterministic recapture한 뒤 source placement를 유지한 채 정상 ambient contribution을 복구했다.
- tree parent `M_SP_SourceTreeFoliage_V2`를 현재 상태에서 재컴파일했다. 과거 구형 `M_SP_SourceTreeFoliage` 실패 로그와 분리해 확인했으며 활성 tree/sky/cloud/Fog V2의 신규 compile failure는 0이다.

### 저장·검증

- 작업 전 백업: `Saved/ArtBackups/StormPass_PreSkyFogVisualFix_20260904_121446`, 65 files / 44,771,313 bytes.
- Fog asset preparation report: `Saved/ImportReports/StormPass_Fog_AssetPreparation.json`, `status=prepared`.
- Fog restoration report: `Saved/ImportReports/StormPass_Fog_Restoration.json`, `status=restored`, actor reused 53, created 0, failure 0.
- Fog saved-map reload report: `Saved/ImportReports/StormPass_Fog_ReloadAudit.json`, `status=passed`, actor 14,408, Fog 53, location/scale 오차 0, rotation 최대 `2.4148365394514667e-6°`.
- 통합 report `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json`은 `status=passed`, failed stage 0이다. 새 `visual_material_integrity` stage는 V2 parent 5개, environment assignment, Fog parent 45/6/2, `PixelDepth` 부재, depth-test 활성, temporary-hidden 0을 검증한다.
- 전체 material slot은 17,979개이며 null/WorldGrid/Default material은 0이다. 최종 dirty StormPass map/content package도 0이다.
- 최종 map size는 43,709,418 bytes, SHA-256은 `E1007AFFEAE22AF49599690EB3CE67582B1B43FC25C8D3E6AFBE17B76C03361D`다.
- 비교 화면은 `Saved/Screenshots/StormPassVisualAudit/SkyHigh_V2.png`와 `Saved/Screenshots/WindowsEditor/RiderMCP/20260904-034343_viewport.png`다. hard horizontal cloud cutoff와 sky seam이 재현되지 않는다.
- Fog 복원은 환경 graph 교정 뒤 마지막 Level 콘텐츠 적용 단계로 수행했다. 이후 검사는 맵을 수정하지 않는 reload audit이며, 진단 재컴파일로 dirty가 된 단일 tree V2 parent만 동일 graph 상태로 저장했다.
