# 2026-10-02 HeinMach / StormPass 원작 룩 복원

## 적용 범위와 현재 판정

사용자가 두 레벨의 누락된 전역 셰이더·머테리얼 및 Phase2 외부 전장의 룩 수정을 요청했다. StormPass는 두 보스 전장만 사용하도록 정리했다. Art 변경이며 게임 액션 C++/애니메이션/스케일 수정 작업이 아니다.

- 현행 맵: `/Game/Maps/L_HeinMach_Environment`, `/Game/Maps/L_StormPass_Environment`. 과거 `_Art/.../Maps` 경로는 redirector다.
- 두 맵과 아래 렌더링 에셋은 실제 저장했다. 라이브 재로드 및 별도 프로세스의 직렬화 검증을 수행했다.
- **원작과 완전히 동일한 렌더러를 복원한 결과는 아니다.** 원작 커스텀 셰이딩 모델의 실행 코드와 일부 runtime 기능은 현재 cooked JSON에 없다. 구현한 UE native 대체식과 원작 직접 값의 구분은 아래와 보고서에 남긴다.
- 초기/중간 Phase2 화면 비교는 수행했지만, 최종 색상·마스크·스카이 보정 후의 viewport 시각 검수와 HeinMach 최종 화면 검수는 미완료다. 이후 레벨 viewport 캡처가 갱신되지 않거나 `FSlateApplication::TakeScreenshot failed for viewport`로 실패했다. 최종 수치 readback/컴파일 성공을 최종 외형 일치로 표현하지 않는다.

정본 도구는 `Scripts/Art/restore_level_look.py`, 기계 판독 보고서는 `Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002`다. 원본 데이터는 기존 FModel export와 `Saved/Extracted/LookRestoration_20261002`의 필요한 package만 조회·추출했다. FModel UI를 직접 조작했다고 기록하지 않는다.

## 실제 발견한 누락과 수정

| 항목 | 발견한 문제 | 저장한 처리 | 구현 한계 |
|---|---|---|---|
| 캐릭터 / 환경 툰 | `MSM_BBQCartoon`, `MSM_BBQHalfCartoon`을 stock PBR로 대체한 상태 | native PP 명암 밴드·깊이/노멀 윤곽선, 8개 환경 MI | 원작 custom shading model의 라이팅 공식은 미복원 |
| 캐릭터 판별 | body/weapon custom depth 미설정 | Player 포함 29 BP, 58 skeletal component의 custom depth/stencil 254, `r.CustomDepth=3` | 렌더링 마스크 예약값이며 원작 gameplay ID가 아님 |
| HeinMach terrain | 실제 weightmap layer를 쓰지 않는 preview terrain | 원본 2 weight grid, 11/12 layer, 33 surface texture와 25 weight texture로 native material 2개 구축; 기존 terrain actor 47개에 적용 | normalized linear blend. 원작 height blend/RVT/displacement 미복원 |
| HeinMach 지역 환경 | WEP 지역 PP 누락 | 원본 7 brush bounds/priority/transform로 bounded PP 7개와 OP startup sky/light/fog | 비정형 cooked brush는 bounding box 근사. 이동에 따른 light/fog/GI runtime 전환 미구현 |
| Phase2 전역 covering | 지형 외 바위/나무에 붉은 EMP covering/glow consumer 없음 | Phase2 전용 world/tree parent, 고유 world MI 및 복제 tree MI에 색상·glow 연결 | 눈/오염 mask와 HDR 배율은 native 근사 |
| Phase2 수면 | EMP pollution 색상 미소비; native 물이 갈색으로 보임 | 원래 water 파라미터를 유지한 전용 MI/parent에 pollution 색상·native absorption 처리 추가 | 원작 water function/fluidsim/전체 wave math 미복원 |
| Phase2 분위기 | Phase1 sky/fog 공유, auto exposure로 흰 낮처럼 보임 | DeepNight sky, source Phase2 sky light/fog, local fog 및 깊이 기반 푸른 haze, native exposure/bloom/saturation 조정 | 하늘·skylight/GI/height fog의 완전한 공간 분리 아님 |
| 스카이의 저장 전용 파라미터 | 태양 배경, 별 blink/color/horizon, 성운 desaturation/noise 이름만 존재 | 원본 FTW texture를 재사용해 실제 expression 입력 연결. `SourceSkyConsumers.json`에서 그래프 도달성 검사 | procedural 식은 native 재구현. 원작 RefractionDepthBias=0의 굴절 경로 미복원 |
| HeinMach packed surface | inherited child MI 3개의 Roughness=B / Metallic=G 뒤바뀜 | Roughness=G, Metallic=B, AO=R로 수정; SRGB=false 확인 | RGB packing 계약만 교정 |
| 두 전장 태양 | lighting channel 0 Pawn에는 Phase2 sun 미적용, 두 sun forward priority 경고 | 두 sun이 channel 0/1을 사용하고 위치 기반 light function mask. forward priority P1=0/P2=1 | volumetric/translucent의 우선 sun과 GI는 전역 공유 |

packed 교정 대상은 `MI_WM_MCN_Object_Short_001`, `MI_WM_MCN_Statue_Stone_001_03_a`, `MI_WM_COM_Bonfire_Base_001`이며 `HeinMachPackedChannelRepairs.json`에 전체 경로와 전후 selector를 기록했다. 나무의 native 직접 G/R 그래프는 사용하지 않는 USD selector를 오류로 판정하지 않았다.

## 원작 데이터와 native 식의 구분

원본 목록/해시/상속·template 해석은 `SourceManifest.json`, terrain 계약은 `HeinMachTerrainPlan/Compilation.json`에 있다. 다음은 대표 근거이며 master default를 leaf 캐릭터 override 검증값으로 취급하지 않는다.

| 원본 package / 파일 | 정확한 field와 원시 값 | 단위·조건 / native 사용 |
|---|---|---|
| `BBQ/Content/_Kazan_/BaseMaterials/Character/M_AKCartoonCharacter` | `Properties.ShadingModel=MSM_BBQCartoon`, `ShadingModels.ShadingModelField=8192` | 원작 custom enum. stock 엔진 모델로 동일 실행 불가 |
| 같은 master | `CachedExpressionData.Parameters`: `Shading Width=.7`, `Shading Intensity=.7`, `ShadingSmoothness=.001`, `NTPThreshold=0` | 무차원 master default. 명암 밴드에 세 값 사용; 실제 leaf NTP override는 미검증 |
| `AR_Data/EnvRenderParams/ERP_Base` 및 WEP template | `CartoonOutlineWidth=.75`, `CartoonOutlineDistance=10000` | 원본 width 단위 미확정. native에서 pixel width / cm depth 거리로 해석한 근사 |
| `StormPass_EnvironmentProfile.json:boss_phase_2.components.environment_material` | `VectorValues.CoveringColor=(.421875,0,0,0)`, `CoveringGlowColor=(300,0,0,0)`; `ScalarValues.EnvCoverWeight=1.5` | source linear RGB / source weight. A=0을 색의 미사용으로 해석하지 않음. mask·HDR 변환은 아래 native 식 |
| 같은 EMP | `SurfacePollutionColorHeight=(.315,0,0,75)` | source RGB + height payload. native water는 RGB 소비; 75의 원작 runtime 높이 적용식은 미복원 |
| 같은 profile의 fog | `FogDensity=1.5`, `FogHeightFalloff=1`, `VolumetricFogDistance=5000`, `FogMaxOpacity=.9`, `CameraFollowOffset.Z=-2000` | source density/falloff의 native 단위 변환은 미검증. 거리/offset cm. global fog는 fixed ground proxy이며 camera follow 실행 아님 |
| 같은 fog | `VolumetricFogEmissive=(.120568,.167239,.234375,0)`, `VolumetricFogAlbedo=FColor(97,71,38,255)` | linear emissive와 byte FColor를 구분. LocalFog albedo만 sRGB→linear 변환 |
| 같은 PP `default_properties.Settings` | `AutoExposureBias=1.5`, `BloomIntensity=7.5`, `ColorSaturation=(.25,.25,.25,1)`, `ColorSaturationShadows=(.25,.25,.25,1)` | 원작 기록은 보존. native exposure/bloom/saturation 적용은 아래 임시값으로 구분 |
| `AR_Data/SkyMaterial/SkyColor_DeepNight` | `StarBrightness=1`, `StarBlinkWeight=.5`, `StarBlinkSpeed=2`, `StarBlinkUVScale=10`, `StarColorWeight=.75`, horizon min/max `0/50000`, `SunlightBackgroundIntensity=1.533792`, radius `.5` | raw parameter를 native procedural 식 입력으로 사용. 동일 원작 식 복원 아님 |
| `WEP_HeinMach_OP`의 해결된 WDL/WSL template | sun `FColor(199,206,212,255)`, rotation Pitch `-90`; sky `FColor(168,196,213,255)`, intensity `1` | byte 색/degree/source intensity. sun lux `20000`은 이전 native 값 유지, 원작 값으로 주장하지 않음 |
| 해결된 HeinMach OP fog | `FogDensity=.5`, `FogHeightFalloff=1.25`, `VolumetricFogEmissive=(.145833,.056945,0,0)`, max opacity `.6` | startup OP field. native 변환은 .005 density / .125 falloff |
| `WLM_HeinMach`, `WLM_HeinMach2`와 상속 `WLM_Base_Terrain5_Inst` | 정확한 layer texture / layer tiling / source root / section / grid | `HeinMachTerrainPlan.json`에 각 layer 값·단위 저장. tiling m→cm ×100; fixed world UV 계산 공개 |

source `ColorGainShadows` / `ColorGainHighlights`의 RGB가 전부 0인 경우 stock tonemapper에 그대로 쓰면 HDR가 지워졌다. 해당 값은 원본 보고서에 보존하고 native gain은 중립 1로 처리한 부분을 `native_pp_settings` 결과에 명시했다. 원작 gain 공식 확인으로 표현하지 않는다.

원작 sky texture는 `FTW_Sky_Nebula`, `FTW_Sky_Star_Mask_001`, `FTW_Sky_Cloud_Distortion`, `FTW_Smoke_Noise_002`의 기존 정확한 export/import를 사용했다. 마지막 두 sampler는 각각 Masks / Linear Grayscale이다. texture 이름 존재와 그래프 실제 소비를 구분해 검사했다.

## 어시스턴트가 선정한 임시 native 수치

`restore_level_look.py:NATIVE`와 `SourceManifest.native_authoring_controls`가 최종 조정값의 정본이다. 원작이 직접 지정한 값이 아니다.

| 그룹 | 최종 임시 값 | 이유·영향·후속 조정 기준 |
|---|---|---|
| toon / outline | world toon `.16`, character `1`; outline world `.16`, character `.8`; depth edge `.004`, normal edge `.3`, stencil depth tolerance `2 cm` | PBR detail 유지하면서 캐릭터 명암/윤곽을 강조. 실제 Character의 배경 겹침·원경 aliasing을 화면으로 확인해 조정 |
| Phase2 native PP | fixed min=max `EV100 2.5`, bloom `.5`, global/shadow saturation `.85/.85`; source exposure bias `1.5` 유지 | source PP를 UE5 stock pipeline에 직접 넣었을 때 과노출 또는 과한 탈색. 원작 화면의 어두운 숲/붉은 물/푸른 원경을 기준으로 선택. 최종 viewport 검수 남음 |
| covering | tint weight `.85`, world base mask `.30`, foliage base mask `0`; luminance `.03→.20`, neutral tolerance `.50`, up-normal weight `.35`, glow scale `.002` | 원작 mask 코드가 없어 texture 밝기/중립도/위 방향의 native mask. source glow `300`에 `.002` 적용. 눈 전체가 하얗게 남거나 바위/목재가 균일하게 빛나는지 확인 필요 |
| water pollution | weight `.85`, absorption density `.02 /cm` | 원래 water albedo/absorption을 원본 파라미터로 유지하고 native pollution branch에서 blend. source RGB의 보색을 absorption으로 쓰는 공식은 원작 확인값이 아님. 혈수 색·반사·바닥 가시성으로 조정 |
| fog 변환 | global density `×.01`, falloff `×.1`; local density P1 `×.15`, P2 `×.60`; local radius `7500/6000 cm` | source 색을 native fog로 재현하기 위한 근사. 원작 부피/radius 아님. LocalFog base radius `500 cm`는 설치 UE5.8 header의 기술적 값이며 원작 수치 근거가 아님 |
| Phase2 depth haze | start `1000 cm`, luminance scale `8`; source density `1.5`, view distance `5000 cm`, max opacity `.9` 입력 | opacity=`min(.9,1-exp(-max(depth-1000,0)*1.5/5000))`; source emissive RGB×8×`View.PreExposure`. native 깊이 기반 복원식. 근경 혈수는 붉게, 원경은 푸르게 남는지 실제 화면 재검수 |
| sky | sun-background scale `.25`, nebula noise strength `.02 UV`; 기존 preview sky luminance `2`, nebula influence `.05` 유지 | 원본 색·blink·noise texture를 native 처리. direction은 source WDL degree→radian→반대 forward 계산. 실제 낮/밤 sky의 밝기·seam 확인 필요 |

공간 분리 light-function 경계 X `170790 cm`는 기존 두 PP 사이 gap의 중점 계산값이다. source 값이 아니다. background retention `50000 cm`는 source `WorldPropDistanceMax`를 이번 보존 반경으로 재사용한 authoring 선택이며 원작 terrain culling contract가 아니다.

## StormPass 두 전장만 남긴 배치

두 전장의 기존 분리 배치를 유지하고 불필요한 원본 관리 actor 11,980개를 삭제했다. 원본 조사만으로 임의 전부 재생성하지 않았고 Content 에셋은 삭제하지 않았다.

- 최종 actor 2,547개. 두 전장의 source actor·foliage, Phase2 terrain 16 component와 먼 mountain mesh를 보존했다.
- Main landscape 중 필요한 background 4개를 기존 Phase2 translation `(+20390,0,0) cm`으로 함께 배치했다. fixed weight root와 surface tile UV를 보정했다. 이동으로 원작의 내부 상대 UV 위상이 바뀌지 않게 한다.
- `StormPassPrunePlan.json`은 삭제한 각 actor의 기존 위치/회전/scale/slot과 보존 목록을 담는다. **삭제 후 이 계획을 다시 생성하면 원래 11,980개 계획을 잃으므로 재생성하지 않는다.**
- 삭제한 mission route의 StormPass PlayerStart는 source P1 entry marker `(162240,51600,296.66724)`, yaw `-10.00003`으로 이동했다. `StormPassApplied.PlayerStart_before`는 수정 전 immutable snapshot의 pose다. HeinMach PlayerStart에는 적용하지 않았다.

| 전장 | 주 마커 | 위치 cm |
|---|---|---|
| Phase1 성채 | `SP_BP_Phase1_ArenaReference_TargetPoint_Boss` | `(162650,51600,695)` |
| Phase2 외부 숲/혈수 | `SP_BP_Phase2_ArenaReference_TargetPoint_Boss` | `(183040,51600,695)` |

Outliner의 `ArenaReference`로 접근한다. `Scripts/StormPass/polish_blade_phantom_arenas.py:show_side_by_side/view`는 이번 삭제 계획에 포함된 없는 route actor를 허용하도록 수정했다. 두 전장을 유지한 채 editor 시점만 바꾸며 자동 gameplay phase 전환 구현은 아니다. 기존 P1 PP/torch/local-light 정책과 source 전장 prop pose는 보존했다. 전역 sky/skylight/fog는 P2 기준으로 바뀌어 P1의 간접 조명까지 이전과 동일하다고 보장하지 않는다.

## HeinMach 사용자 변경 보존

- 현재 Start `HM_Tutorial_PlayerStart_DualAxeSword`의 위치 `(12083.049,12216.91,202.70361)`, yaw `-114.986206`은 수정 전 snapshot과 동일하다.
- `HeinMach_UserExclusions` 18개, `HeinMach_OptimizationExclusions` 109개 모두 재생성하지 않았다. `HeinMach_ManualOverrides`도 변경하지 않았다.
- 기존 actor pose 변경은 source OP 방향으로 맞춘 `HM_PreviewSun`뿐이다. source PP 7개와 source sky 1개 추가로 actor 9,601→9,609.
- 기존 terrain component를 다시 만들거나 오래된 root aggregate를 임의로 숨기지 않았다. 저장된 실제 사용자 삭제를 기본 full importer로 되돌리지 않는다.

## 검증·중단 이력

- Live World 재로드: StormPass actor 2,547 / 사용 material 211; HeinMach actor 9,609 / 사용 material 662. missing mesh slot 0, 검사한 packed input mismatch 0. SP 삭제 대상 잔존 0/보존 대상 누락 0, HM tombstone 복원 0/수동 변경 0/Start 변경 0.
- P1/P2 주 마커·P1 entry·Start에서 simple/complex Visibility ground trace **8/8**. 기존 지원 바닥 top Z `89.00001 cm`. native authoring floor이며 원작 collision/NavMesh/AI/Character gameplay 완주 증명이 아니다.
- 새 process에서 두 map 및 Player의 body/두 weapon custom depth template를 읽어 같은 계약을 검사했다. `FreshProcessSummary`, 각 `*_FreshProcess.json`, `Saved/Logs/LookFreshAudit_Final_20261002.log` 참조. `NullRHI` 검사이므로 외형·shader 실행 검증으로 취급하지 않는다.
- 첫 fresh commandlet은 프로젝트 AssetManager가 `/Script/GameFeatures.GameFeatureData`를 찾지 못해 ensure/exit 1이 났다. **검사 프로세스에만** `-EnablePlugins=GameFeatures`를 주어 재실행했고 exit 0으로 검증했다. 프로젝트 gameplay config는 이 문제를 우회하도록 수정하지 않았다.
- native 주요 material 9개 SM6 editor statistics가 양수다. `FinalShaderCompilation.json`: toon 110, sky 197, sun mask 각각 96, covering world/tree 423/263, water 1168, terrain 471/494 pixel instructions. 비용과 원작 shader 동등성을 의미하지 않는다.
- sky 추가 중 잘못된 LinearColor noise sampler가 compile 실패를 일으켰으나 source TC_Grayscale에 맞게 LinearGrayscale로 고친 뒤 197 instructions로 컴파일됐다. 실패 기록과 최종 수정 결과를 구분한다.
- Rider game-thread에서 TextureFactory 없이 synchronous Interchange import를 실행해 TaskGraph recursion assert가 두 번 발생했다. 원인: `TaskGraph.cpp:705`, `++Queue(QueueIndex).RecursionGuard == 1`. live Editor를 재개한 후 모든 terrain texture import를 명시적 `unreal.TextureFactory()`로 바꿔 58개 texture import 성공. 이 원인으로 다른 gameplay 파일을 수정하지 않았다.

시각 비교 자료는 `Saved/Extracted/LookRestoration_20261002/VisualReferences/GameplayReferenceManifest.json`이다. [Noobfeed의 실제 보스 플레이 이미지](https://www.noobfeed.com/articles/the-first-berserker-khazan-guide-how-to-beat-blade-phantom-second-boss)의 4/5번에서 혈수·붉은 바위·푸른 원경을 확인했다. 설치 원본 build와 영상 build 일치는 미검증이다. 2024 intro 이미지도 저장했으나 Phase2 플레이의 직접 대조 기준으로 사용하지 않았다.

`Saved/Screenshots/WindowsEditor/RiderMCP/20261002-084227_viewport.png`는 과노출 사전 화면, `085113`은 EV5 시험, `090131`은 EV3.5 시험, `093630`은 중간 haze의 화면이다. 이후 최종 EV2.5/색상/mask/sky 상태의 화면으로 재사용하지 않는다. native UI pipe도 unavailable여서 UI를 본 것으로 가장하거나 HighResScreenshot 우회를 하지 않았다.

## 아직 확보하지 못한 원작 구현

`M_AKCartoonCharacter` cooked metadata는 `MaterialAttributes.Expression=null`이고 함수 이름만 있으며 MaterialExpression export와 실행 가능한 원작 shader source가 없다. 따라서 확인된 default 값을 native 입력으로 사용하는 것과 원작 renderer를 port하는 일은 다르다.

- 원작 BBQCartoon/HalfCartoon의 light/shadow/sub-light/capsule-shading 공식, 일부 ERP 거리/brightness 응답.
- 원작 NTP/hatching/rim 전체 함수와 leaf override의 실행 일치. imported diffuse에 포함된 선화와 별도 procedural hatching을 혼동하지 않는다.
- FFX CACAO 및 원작 `PPM_FilmicSharpen_Default`, `PPM_FilmPass_Default`, `PPM_DepthOfField_Default`의 전체 custom pass. 대응 가능한 native color-grade/film/DOF field와 신규 toon/haze는 적용했지만 동일 코드가 아니다.
- WEP의 runtime light/sky/fog/GI 혼합, camera-follow fog와 비정형 volume의 정확한 blend.
- terrain height/RVT/displacement, 완전한 water fluidsim/caustic/wave 함수, animated covering/pollution notify와 source height 조건.

완전한 원작 일치를 확정하려면 관련 original engine/shader implementation 또는 같은 build의 controlled gameplay captures가 더 필요하다. 현재 결과를 "원작 전역 셰이더 전부 복제 완료"로 보고하지 않는다.

## 재개 절차 / 백업

1. Router → 이 문서 및 마지막 `ART_WORK_CONTINUITY` → `SourceManifest`, `FinalShaderCompilation`, `*_FinalReloaded`, `FreshProcessSummary`만 먼저 읽는다.
2. Rider health/PIE/현재 World/dirty 상태를 확인한다. 다른 사용자의 dirty map/content를 Save All 하지 않는다.
3. 레벨 viewport가 실제 갱신 가능한 상태에서 Source P2 camera와 같은 위치를 확인하고 단일 viewport 캡처로 최종 붉은 근경/푸른 원경/자연스러운 노출을 검수한다. 이어 HeinMach Start와 Phase1 interior를 검수한다. 잠깐 만든 actor/selection/gameview/realtime/performance override는 저장하지 않고 복원한다.
4. 수치 조정은 `NATIVE` 및 MI 파라미터에 모아 native 임시값으로 기록한다. source JSON/원작 값 표를 수정해 임시값을 원작으로 만들지 않는다.
5. 필요하면 관련 에셋만 저장한 뒤 해당 맵 재로드/새 process audit를 다시 실행한다. `storm_prune_plan`/전체 scene importer/actor source reset은 재실행하지 않는다.

immutable byte backup: `Saved/ArtBackups/LevelLook_PreRestore_20261002/BackupManifest.json`, 추가 에셋은 `AdditionalAssets.json`. source package JSON hashes와 Shader/Texture/Applied/Prune/Background 보고서를 같은 날짜 폴더에 보존한다. 후속 사용자 편집이 있으면 옛 BP/map 전체 backup을 덮어 복원하지 말고 필요한 rendering 변경만 이관한다.
