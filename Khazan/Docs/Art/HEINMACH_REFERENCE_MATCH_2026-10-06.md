# 2026-10-06 HeinMach 원작 사진 비교·렌더링 오류 수정

## 현재 판정과 실제 반영

사용자의 최신 목표는 이전의 실사 중심 제안보다 **원작 HeinMach의 룩 재현**이 우선이다. 사진 5장과 현재 저장본, 원작 WEP·머테리얼 metadata를 비교했다. 발견한 지역 선택·하늘 깊이 판정·후처리 순서·눈 depth/velocity 문제를 수정하고 메인 프로젝트에 12개 package를 반영했다. **원작 전용 셰이더 이식 및 비주얼 완전 동일 판정은 완료하지 않았다.** 남은 표면 재현과 검증 조건을 아래에 구분한다.

이번 작업은 Router → Art 상태/규칙/지식/continuity → 기존 Look/Weather 정본과 저장 report에서 시작했다. 캐릭터 C++/게임플레이 BP/Animation/공유 Config/StormPass를 편집하지 않았다. 새 runtime class, component, tick, manager는 없다. 새 게임 에셋은 기존 두 Niagara emitter의 spawn budget을 설정하는 `NET_HM_WeatherBudget` 하나다. QA 에셋은 격리 프로젝트에만 남긴다.

- 맵: `/Game/Maps/L_HeinMach_Environment`.
- 변경: map 1, `M_HM_RegionalLook` 1, 지역 MIC 6, snow/dust material 2, 기존 Niagara system 1, 새 EffectType 1.
- 모든 9,610 actor의 추가·삭제·pose 변경 0. fresh **메인** audit의 최대 pose 차이도 0이다.
- 현재 사용자의 `PlayerStart`: location `(12022.196341630144,13909.267886166936,223.7105706322176) cm`, rotation `(0,0,0)°`, scale `(1,1,1)` 유지. 과거 정본의 Start로 되돌리지 않았다.
- 모든 UE 작성·실행 검수는 숨김 background process에서 했다. Rider editor PID27916은 read-only health/현재 world·dirty 조회만 했다. 관측 world는 `DevMap`, dirty map/content는 모두 0이었다. `DEBUG RESETLOADERS`, Save All, live map reload/PIE 제어를 하지 않았다.
- 원본 11 package를 `Saved/ArtBackups/HeinMachReference_20261006/Content`에 byte backup. 메인 파일이 격리 시작 SHA와 같은지 확인한 뒤 선택 파일만 교체했다. 다른 복사 package 316개는 격리 baseline과 동일하다. 다른 동시 작업의 파일을 정리하거나 되돌리지 않았다.

## 사진별 분석

| 사용자 자료 | 실제로 보이는 특징 | 재현 시 적용한 판단과 한계 |
| --- | --- | --- |
| `HeinMach 원작.jpg` 720×405 | 절벽·먼 계곡. 근경 눈은 비교적 중립적이며 원경은 청회색으로 약해진다. 부드러운 확산광, 작은 붉은 전투 광원. 바위 전체가 검은 실루엣으로 붙지 않는다 | 원경 haze와 지역 tint를 함께 사용하고, 강한 직사광/날카로운 나뭇가지 그림자를 줄임. 전투 붉은 효과는 이 환경 작업에서 새로 구현하지 않음 |
| `HeinMach원작.jpg` 720×405 | Yetuga 근처의 따뜻한 회갈색 바위와 차가운 회백색 눈. 표면이 젖은 플라스틱처럼 반짝이지 않음. 명암 경계는 존재하지만 모든 면을 굵은 선으로 자르지 않음 | sun specular를 source OP 값으로 복귀, world toon/outline은 작게 유지. 보스의 haze 색을 순수 청색으로 통일하지 않음 |
| `HeinMach 원작 (2).jpg` 720×405 | 높은 카메라의 묘지/횃불 장면. 차가운 푸른 바탕 속 따뜻한 불빛과 작은 분홍색 빛. 눈의 넓은 하이라이트는 무광에 가까움 | 전역 채도를 올려 따뜻한 풀/이끼를 강조하던 이전 룩을 철회. source 지역 palette를 구분하며 bloom은 작게 사용. 해당 묘지의 동일 카메라·광원 상태 비교는 아직 안 함 |
| `HeinMach 원작.png` 1317×716 | 영상 7:01/21:59의 좁은 길·오른쪽 텐트. 상당히 어두운 청색/청록색 환경, 어두운 캐릭터가 은은한 경계로 분리됨 | 이 사진 한 장의 어둠을 전체 레벨의 동일 노출로 가정하지 않음. 눈보라 구간의 청회색과 외곽선의 작은 기여를 맞춤. native `ReferenceStart` 카메라는 근처 검수 시점이며 영상 카메라와 정확히 정렬된 상태가 아님 |
| `HeinMach 원작 보스 전장.jpg` 720×405 | 넓은 전장. 청회색 눈, 회갈색·따뜻한 원경 바위, 대기의 soft contrast, 강한 붉은 피드백. 시야 전체에 큰 눈송이가 빽빽하지 않음 | Boss haze를 따뜻한 원작 inscattering 쪽으로 돌리고 눈 생성량을 줄임. native Boss 시점은 ground trace 후 지면 위에서 찍었으며 원작과 같은 전투 phase/카메라로 평가하지 않음 |
| `HeinMach 현재 프로젝트 상황.png` 1300×622 | 이전 프로젝트 사진의 밝은 흰 눈·검은 바위 양극화, 노란 식물/녹색 이끼 강조, 큰 눈송이, 단단한 나뭇가지 그림자 | 문제 파악 자료. 이번 작업 직전 상태는 별도 실제 game `baseline`이며 이 오래된 사진을 이번 변경 전 카메라와 같다고 표시하지 않음 |

전체 공통점은 차가운 공기, 무광 눈/바위, 지역에 따라 달라지는 회색·청색·회갈색, 절제된 반사, 캐릭터 중심의 약한 경계다. 따뜻한 횃불·전투 효과가 색의 국소 대비를 만든다. 단순한 전역 desaturation이나 세계 전체의 강한 툰 경계로 바꾸면 사진의 룩과 다르다.

`ReferencePhotoAnalysis.json`은 중앙 ROI(가로 15–86%, 세로 10–78%)의 표시 RGB/luma 통계다. HUD/자막을 가능한 제외했지만 영상 압축·다른 카메라/시간/빌드/노출이 있으므로 원작 linear 조명 값이나 동일성 점수로 사용하지 않았다. `OriginalReferences.jpg`는 원본 5장의 비교용 축소 보기다.

추가 자료로 공식 First 15 Minutes 영상 `https://www.youtube.com/watch?v=eu9rhfCqZTM`의 공개 다운로드를 시도했지만 HTTP403으로 완료하지 못했다. 부분 파일은 레퍼런스로 사용하지 않았다. 수집 실패는 `References/Collection.json`에 있다. 인증/쿠키 우회는 하지 않았다.

## 실제 발견한 렌더링 문제와 조치

### 1. OP가 눈보라 볼륨을 덮고 있었다

기존 bounded OP priority `100`은 Blizzard1 `12`보다 높았다. 입구의 넓은 겹침에서 원작의 차가운 지역 하늘/안개가 선택되지 않는 문제다. 기존 source BSP 7개/81 faces와 pose는 유지하고 OP만 native priority `10`으로 낮췄다. Blizzard1/2 `12/13`, Escape `30`, Boss `40`, Cave1 `50`, 전역 preview `-100`은 유지했다. 이 priority는 **native routing 선택**이며 원작 weather controller의 priority를 복원한 값이 아니다.

### 2. 지역 하늘의 SceneDepth 판정이 지나치게 엄격했다

기존 `Stencil252 && abs(SceneDepth-CustomDepth)<2cm`는 하늘 픽셀의 far clear depth/큰 거리 정밀도 차이에서 실패할 수 있었다. 실제 시야의 하늘 branch가 빠져 기본 OP proxy만 보이는 문제가 있었다.

현재는 stencil252와 `SceneDepth >= CustomDepth - max(2cm,CustomDepth*0.00002)`로 전경 occlusion을 검사한다. `0.00002`는 native 상대 깊이 정밀도 허용치다. foreground SceneDepth가 sky CustomDepth보다 앞이면 하늘을 덮지 않는다. 변경 후 actual game OpenSky에서 지역 cloud가 보이는 것을 확인했다. source Sky/Cloud/Star/Nebula 데이터와 전용 sky mesh의 pose/stencil은 그대로다. 원작의 절차적 sky 함수 자체와 같다는 판정은 아니다.

### 3. 캐릭터 경계 계산이 TSR 뒤에 있었다

기존 `BL_SCENE_COLOR_BEFORE_BLOOM`의 scene color는 이미 TSR로 재구성된 화면이었다. 반면 normal/depth/custom stencil을 읽어 캐릭터/외곽선을 정하는 식은 현재 프레임의 입력을 사용했다. 서로 다른 시간/샘플의 경계를 곱하면 움직이는 팔·다리의 mask와 음영이 흔들릴 수 있다.

UE5.8 `Renderer/Private/PostProcess/PostProcessing.cpp`에서 TSR → MotionBlur → BeforeBloom 순서를 확인했다. 기존 master를 **BeforeDOF, TSR 이전**으로 옮겨 같은 입력 시점에서 경계·툰 계산을 하게 했다. custom depth temporal jitter는 유지한다. signed world normal의 `normalize(Normal.xyz)`는 올바른 기존 decode이며 수정 대상이 아니었다.

전체 8 PP의 motion blur amount와 scene fringe intensity도 `0`으로 설정했다. 사진 기반의 native 선택이며 원작 motion blur `.15`를 그대로 복사한 결과가 아니다. TSR는 유지하며 FXAA는 비교에만 사용했다.

### 4. 눈/먼지가 캐릭터의 depth/velocity에 개입했다

snow/dust material의 `output_translucent_velocity=true`가 활성화돼 있었다. 투명 눈이 캐릭터 앞을 통과할 때 underlying opaque depth/velocity 대신 눈의 입력이 history 판단에 쓰일 수 있다. 두 material에서 이를 껐다. 원작 `bEnableSeparateTranslucency=false`에 대응하는 **BeforeDOF** 합성은 유지하고 ResponsiveAA도 유지한다.

Atlas/lifetime **A-only opacity**를 보존한다. Custom color node의 Mask texture R, ParticleRGBA, World/Camera/Age/CameraFade/Radiance 입력을 명시적으로 재연결하고 real DX12에서 compile/save했다. 별도 game process의 DefaultMaterial fallback 유무도 검사한다.

중간 시도에서 회색 사각형이 나타났다. 처음에는 AfterDOF/DepthFade 합성을 의심했지만, game log에서 Custom Mask 입력 누락과 DefaultMaterial fallback을 확인했다. 해당 시도는 최종본으로 사용하지 않았다. DepthFade10 실험은 제거했고 원작 cooked active graph를 모르는 상태에서 10을 필수 식으로 넣지 않았다. 두 단계의 원인 설명을 혼동하지 않는다.

이 조치들은 경계/시간 입력의 결함을 제거한 것이다. controlled motion의 정지 후 차이는 Lumen/그림자 noise와 AA도 포함한다. 이를 순수 ghosting 점수로 해석하거나 **모든 gameplay motion에서 할로가 완전히 0**이라고 주장하지 않는다. 실제 사용자 입력의 대시·공격·회전 전체는 이번 background QA가 대신하지 않는다.

### 5. 눈 생성량

기존 두 GPU emitter graph/원본 atlas·vector field·수명/크기는 보존했다. 기존 NiagaraSystem에 EffectType을 연결하여 두 emitter의 spawn count를 `0.25`배로 줄였다. 모든 엔진 quality level에 적용하는 mask31은 품질 bit mask이며 게임 수치가 아니다. camera near fade는 `50 → 150cm`로 늘려 매우 가까운 입자를 부드럽게 억제했다.

원작 OP spawn500 × GPU rate scale2.5–5 = emitter당 1,250–2,500/s. 현재 native 0.25배는 312.5–625/s다. **source rate의 원시 입력과 native 감소 선택을 구분한다.** 순간 개체 수는 수명/난수/측정 시점에 따라 달라지므로 정확히 75% 감소한 순간 count라고 표현하지 않는다.

## 머테리얼 분석과 원작 셰이더의 차이

cached scene report의 실제 환경 material은 661개다. USD opaque parent392, translucent parent213, display color3, weighted terrain2, fogsheet preview50, sky1이다. 이는 **parent 분류**이며 instance blend override를 무시한 실제 translucent 213개라는 뜻이 아니다.

확인한 정상 부분: USD root normal sampler는 Normal, `*_S`의 주요 packed 연결은 AO=R/Roughness=G/Metallic=B다. 대표 rock/moss의 D/N/S binding은 원작 참조와 대응한다. 원작 metadata를 확인하지 않은 global normal flip/채널 교체/재임포트를 하지 않았다.

새 조사는 원본 provider에서 이름3개만 index해11개 후보를 얻었다. base material3개와 parent2개를 추출한 뒤 실제 scene에서 많이 쓰이는 `_opaque`/Portal4개와 필요한 parent closure를 표적 추출했다(총13 package). 전수 조사는 안 했다. 원시 JSON은 `Saved/Extracted/HeinMachReference_20261006/Source/BBQ/Content/...`와 저장 metadata의 `Source`에 있다. 원작 build 번호는 이번 원본 loader에서 식별하지 못했으며 파일 SHA로 추출본을 식별한다. 이전 cached WEP와 이번 package가 같은 게임 build임을 확정하지 않는다.

| 원본 package/export | 확인한 원시 field/value | 현재와의 실제 차이 |
| --- | --- | --- |
| `Art/World/World_Material/Prop/Material/WM_CTR_Rock_Base_007` | `BasePropertyOverrides.ShadingModel=MSM_BBQHalfCartoon`, Masked, clip`.3333`; `DetailTexIntensity=.5`, `DetailUVScale=6` | USD D/N/S 소비만으로 원작 detail/lighting 식이 복원되지 않음. source `_opaque`의 parent가 이 base임을 확인했으며 scalar override는 없음. base field를 `_opaque`에 직접 직렬화된 값으로 부르지 않음 |
| `.../WM_CTR_Rock_Collision_004` | `UseVertexPaint=true`, `Tex_D/S/N_Red=WT_WOD_Stoneset_Tile_001`, `_Green=WT_WOD_Soil_Tile_001`; UV red3/green6; detail intensity`.75`, UV5 | 기존 native base texture 연결만으로 vertex red/green blend와 source detail/covering 전체가 복원되지 않음 |
| `.../Base/WM_BBQProp_DetailMap_Rock` | parent `WM_BBQProp_Base`, `UseDetailMap=true`, `PixelNormalWeight=.25`, `Tex_Detail_D1=WT_COM_DetailMap_Rock_006_D`, `Tex_Detail_N1=WT_COM_Rock_Tile_001_N` | field/texture 존재를 확인했으나 cooked 식의 normal/detail 혼합 의미는 확보하지 못함. `.25`를 임의로 normal 강도로 바꿔 넣지 않음 |
| `.../WM_CTR_Moss_Green_001` | `MSM_BBQBrightAmbient`, TwoSided/Masked/clip`.3333`, source D/N/E, PivotPainter P1/P2, `UseBBQGrassMovement=true` | USD DefaultLit가 source bright ambient·cover·wind/PivotPainter를 그대로 구현하지 않음. 현재 D/N은 올바른 moss texture이며 soil 오바인딩이라는 추측은 배제 |
| `.../Base/WM_BBQGrass` | parent `Base_BBQFoliage`; `Roughness=10`, `SpecularAmount=0`, `DiffuseColorMultiplier=(.75,.75,.75,1)`, `UseCovering/FakeAO/DynamicOpacity/Wind=true` | 원시 이름과 값은 확인했으나 native PBR의 roughness pin에 10을 직접 복사하는 것은 검증된 원작 식이 아님 |
| `_Kazan_/BaseMaterials/Character/M_AKCartoonCharacter` | `MSM_BBQCartoon`, ShadingModelField8192, cooked MaterialAttributes.Expression=null | 현행 player generated parent는 stock DefaultLit/Masked다. cache/parameter를 읽은 사실과 원작 실행 BRDF를 확보한 사실을 구분 |

scene usage는 RockBase007 opaque394, Collision004 opaque521/base9/Portal2/va2 opaque45다. opaque/Portal source의 parent는 각각 base007/base004로 확인했고 va2 opaque는 va2를 상속한다. `WM_BBQProp_Base → M_WorldProp`의 root는 HalfCartoon, `Base_BBQFoliage`는 BrightAmbient이며 둘 다 cooked `MaterialAttributes.Expression=null`/Expressions 미포함이다. `ExpressionName`은 각각 `MaterialExpressionMaterialFunctionCall_2`/`MaterialExpressionQualitySwitch_10`로 남아 있지만 실행 graph를 제공하지 않는다.

current character parent에는 dithered LOD transition이 있으나 이것만으로 애니메이션 픽셀 흔들림의 원인이라고 확정하지 않았다. DitherTemporalAA function이 실제 skin alpha 경로에 있다는 근거도 찾지 못했다. Skin material의 HasPixelAnimation/LOD/dither를 근거 없이 일괄 변경하지 않았다.

Stock UE5.8에는 원작 전용 BBQ shading model이 없다. FModel은 texture/parameter/reference/원시 package를 얻는 데 유용하지만 이름을 stock enum으로 바꾼다고 전용 BRDF가 구현되지 않는다. **원작 shader binary가 게임 전체에 없다고 조사한 것이 아니다.** cooked shader library 전체의 실행 body/decompilation은 이번에 수행하지 않았다. 현재 PP는 이미 조명된 SceneColor를 normal band와 base-color floor로 조정하는 native 근사이며 source BRDF의 대체 증명이 아니다.

따라서 현재 개선은 지역/합성 결함과 조명·색감의 큰 차이를 줄인 결과다. 바위 detail/vertex blend/covering, foliage ambient·wind, 피부의 원작 BRDF까지 완전히 같다고 쓰지 않는다.

## 수치 출처와 현행 native 설정

source 숫자는 `Rendering/Metadata/LookRestoration_20261002/SourceManifest.json.HeinMach.<profile>.components`와 원본 `BBQ/Content/Art/ArtRendering/AR_PostProcess/WEP/WEP_HeinMach_<profile>`의 resolved component properties에서 재사용했다. 원본 상속/override가 들어간 결과이며 이름이 비슷한 다른 WEP 값으로 대체하지 않았다.

| profile | source FogDensity / VolumetricFogDistance(cm) / FogMaxOpacity | source FogInscatteringColor linear RGB | source VolumetricFogEmissive linear RGB | native emissive mix |
| --- | --- | --- | --- | --- |
| OP | `.5 / 7500 / .6` | `(.108159,.137044,.15625)` | `(.145833,.056945,0)` | `.2` |
| Blizzard1 | `2 / 5000 / .75` | `(.00855,.009311,.010417)` | `(.143918,.21301,.307292)` | `.8` |
| Blizzard2 | `.5 / 5000 / .75` | `(.244792,.166981,.116889)` | `(.199185,.208333,.198631)` | `.25` |
| Boss | `4 / 5000 / 미기록` | `(.234375,.170152,.179513)` | `(.152297,.316134,.359375)` | `.2` |
| Cave1 | `.5 / 7500 / .8` | `(0,0,0)` | `(.037371,.04974,.067708)` | `.8` |
| Escape | `1 / 5000 / .9` | `(.213542,.162577,.106725)` | `(.102895,.173347,.223958)` | `.8` |

Boss FogMaxOpacity는 resolved metadata에 없어 native fallback`.6`을 사용한다. 원작 직접 값으로 부르지 않는다. HazeColor는 `(1-mix)*sourceInscatter + mix*sourceEmissive`로 계산하지만 mix 자체는 사진으로 선정한 native 값이다. 표의 source FogDensity도 원시 field 계수이며 physical extinction을 직접 복원한 값이 아니다.

native haze 식은 `min(maxOpacity,1-exp(-max(depth-start,0)*density/viewDistance))*weight`다. source volumetric fog shader 식이 아니다. start1000cm는 기존 native 선택을 유지하며 weight`.75`를 사용한다. luminance는 기존 native EV100 outdoor8/cave4에서 `2^EV=256/16`을 계산한다. pre-exposed HDR의 `View.PreExposure`는 1회만 적용하며 master `disable_pre_exposure_scale=true`를 유지한다.

| 현행 조정과 출처 구분 | 값·단위 | 선정·확인 기준 |
| --- | --- | --- |
| sun intensity / light source angle | native `7000 lux / 5°` | 이전 native20000lux의 과도한 명암차와 날카로운 그림자 억제. 가지 그림자와 눈 detail을 actual game에서 확인 |
| sun specular scale | 원작 직접 OP`.01`, 무차원 | `WEP_HeinMach_OP.directional_light.SpecularScale=.01` 복귀. 이전 native`.15` 대체. 모든 지역의 source sun 값이 runtime에 전환되는 구현은 아님 |
| world/character toon weight | native `.08 / .45`, 선형 혼합 계수 | world 면의 큰 단계화 억제, 캐릭터 쪽 toon 기여. 원작 BRDF 계수와 같은 의미가 아님 |
| world/character outline opacity | native `.04 / .22`, 계수 | 사진의 절제된 경계. width는 기존 native1pixel 유지 |
| shade smoothness / shadow fill | native `.06 / 2`, 계수 | 기존 native band 경계 폭과 base-color floor 보정. source shadow brightness/ambient는 이전 자료 재사용 |
| global·shadow saturation / contrast / bloom | native `.55 / .55 / .96 / .12`, 계수 | 이전 실사 중심`.95`와 황록색 강조 대체. mid/high sat1, 기존 filmic grade 유지 |
| OP/Blizzard1/Blizzard2 scene tint | native `(.65,.78,1)/(.48,.70,1)/(.75,.82,1)`, linear RGB multiplier | 사진의 한색 정도와 지역 구분. source tint 직접 복사가 아님 |
| Boss/Cave1/Escape scene tint | native `(.88,.92,1)/(.92,.84,.80)/(.88,.86,.84)` | 보스의 따뜻한 회색, 동굴·탈출의 색 분리. linear RGB multiplier |
| snow spawn scale / near fade | native `.25 / 150cm` | 시야 가림·큰 near flakes·밀도 억제. 기존 GPU graph 유지 |
| motion blur / scene fringe | native `0 / 0` | 동체 blur/색 어긋남 제거와 경계 검사 |

선정값은 `Scripts/Art/heinmach_reference_author.py`의 `FIT/TINT/HAZE_EMISSION_MIX/PRIORITY`에 모았다. 이번 saved assets의 재현 owner는 이 제한된 author다. 과거 `weather_look.py NATIVE`만 실행하면 이전 값으로 돌아간다. 전체 importer를 재실행하지 않는다.

## 실제 검증과 성능

- **Main** hidden actual standalone game: `main_captureProcess.json` exit0/marker pass. 저장 MIC 사용, MID 대체 없음. Player/Entry/ReferenceStart/Boss/OpenSky의 일반 `Shot` PNG5개, 1280×720, TSR 이력 유지. HighResShot/SceneCapture를 동체 증거로 쓰지 않았다. game log의 `Default Material will be used in game` 0개.
- **Main** fresh NullRHI: `main_auditProcess.json` exit0/pass. `FreshSavedSceneAudit.json`의 9,610 actors/pose delta0/PlayerStart/8PP/6MIC/BeforeDOF/preExposure/A-only/no snow depth-velocity/EffectType`.25`/source sun spec`.01` 계약 통과.
- real DX12/SM6 compile: native PP110, snow/dust 각107 pixel instructions, errors0. QA3재질도 errors0. instruction 수는 엔진 통계이며 총GPU 시간이 아니다. final game에서 fallback도 재확인.
- controlled motion: source `InGame/DAS/Locomotion/Run/CA_P_Kazan_DualAxeSword_Run_F`의 single-node animation과 deterministic lateral actor translation, 4 variants×65 frames. 동일 parameter의 old/new PP, TSR snow 유무와 FXAA 비교. translation/phase는 QA sample이며 저장된 게임 수치가 아니다. input-driven PIE/전체 전투 검증 완료가 아니다.
- `MotionImageAnalysis.json`의 정지2→24frame crop 차이는 약1–1.8 표시RGB 값이며 Lumen/AA/그림자 noise를 포함한다. 신구 차이로 개선율을 계산하지 않는다. `MotionComparison.jpg`를 눈으로 확인할 자료로 저장.
- main Player capture의 flake/dust count는 `final/Capture.json`을 우선한다. 생성량의 같은 조건 비교는 아래 별도 측정에서 확인한다.

추가 main 단일 시점 SimCache 검사에서 flakes SpriteSize XY `.5000117–.7499385cm`, dust`.30000001cm`를 실제 읽었다. 원작 init size와 대응하며, 이미지가 크다는 이유만으로 Niagara size 단위가 틀렸다고 판단하지 않았다. material SizeBySpeed WPO 적용 전 속성이다. 해당 추가 capture가 당시 동일 `main_capture.log/main_captureProcess.json` 이름을 사용해 로그를 덮었다. 이전5시점의 실제 결과는 `final/Capture.json`과5PNG/해시 및 성공 tool 결과이며, 덮인 로그를5시점 로그로 부르지 않는다. 이후 runner는 particle readback을 다른 prefix로 기록한다.

성능 조건은 RTX3060Ti, Ryzen5600X, UE5.8.2, DX12/SM6, 1280×720·native100%/High·Epic AA, TSR, Development offscreen, 고정 Entry camera, Rider editor 동시 실행이다. 각 variant warmup 후200 GPU samples를 연속 비교했으며 순서/다른 editor 부하를 완전히 분리하지 못한다. `t.MaxFPS30`이어도 실제 frame은 아래와 같으며 레벨 전체의60FPS 보장이 아니다.

| variant | warmup 직후 flakes/dust | GPU Niagara simulation median / P95(ms) | GPU translucency median / P95(ms) | 전체 GPU median(ms) |
| --- | --- | --- | --- | --- |
| LegacySnow(이전 budget 없음·velocity 있음) | `8600 / 2298` | `.0164 / .022815` | `.11115 / 5.22723` | `34.65965` |
| SparseSnow(현행`.25`·velocity 없음) | `2382 / 784` | `.0138 / .01921` | `.1019 / .356835` | `33.8942` |
| NoSnow | system 없음 | stat 미출력(0 측정이라고 쓰지 않음) | `.0573 / .072355` | `33.22925` |

현재 눈 ON/OFF translucency median 차이는`.0446ms`다. 전체 GPU 차이 또는 큰 Legacy P95 이상치를 눈만의 인과적 개선으로 단정하지 않는다. FrameTime median은 이전44.9995/현행44.4356/눈 없음44.4283ms다. 눈은 가볍지만 이것으로 전체 level의 성능 문제가 해결된 것은 아니다.

## 저장 자료와 재개

영속 metadata: `Content/_Art/Player/Environment/Rendering/Metadata/HeinMachReference_20261006`. 실제 사진/CSV/log는 `Saved/ImportReports/HeinMachReference_20261006`와 `Saved/ArtStaging/HeinMachReference_20261006/Saved`.

첫 조회 자료는 `InstallManifest/DeliveryVerification/FreshSavedSceneAudit/SourceMaterialAnalysis/PerformanceVerification`이다. 사진 비교 `BeforeAfter.jpg/OriginalReferences.jpg`, 동체 비교 `MotionComparison.jpg`, 메인 actual game5개는 `final`. 비교 사진은 축소만 했으며 장면을 고치지 않았다. 이전 Boss baseline 카메라는 지면 안에 있어 동일 장면 전후 비교에서 제외했다.

미완료 계약:

1. 같은 원작 build·위치·카메라·날씨·시간·표시 설정의 controlled 비교. 현재5사진은 다른 장면이며 pixel identical 평가의 근거가 아니다.
2. BBQCartoon/HalfCartoon/BrightAmbient의 실제 BRDF, rock detail/vertex blend/cover, foliage ambient/PivotPainter/wind 및 원작 runtime sun 전환. metadata로 원작 식을 추측한 것을 직접 복원이라고 기록하지 않는다.
3. 이전 weather 미완료 항목: MaxBlizzard/전체 지역 snow rate·풍향·color/Blow의 runtime 계약, 회전 dust field, ground collision/event puff, Moon/Planet. 이번 priority/sky 수정을 전체 snow 지역 controller 완성으로 확대하지 않는다.
4. 실제 입력의 이동/큰 회전/큰 대시/공격, 배경 contrast별 잔류 TSR artifact 확인. 이번 motion QA와 순수 ghosting 검증을 구분한다.

다음 작업은 Router→최신 Art 상태→본서→저장 report 순서다. 주요 rock `_opaque`/variant의 **대상 metadata와 parent closure**를 추가로 읽고 기존 native material의 부족한 consumer를 작게 보완한다. 원래 shader 실물의 유무/실행 의미 조사와 사진에 맞춘 native 식의 선택을 구분한다. 현재 올바른 D/N/S channel과 pose를 이유 없이 되돌리지 않는다.

변경을 이어가면 **현재 메인의 새 snapshot/hash를 먼저 만든다**. 이번 installer는 이전 baseline 일치를 전제로 하는 최초 반영용이며 재apply하지 않는다. 작성은 같은 hidden 격리 환경의 제한된 owner, 검증은 audit→compile→일반 game shot→필요한 motion/performance 순서다. 이전 source actor importer/전체 weather builder/옛 Start 복원/global loader reset은 재실행하지 않는다. live에 새 dirty가 있으면 내용을 먼저 확인해 저장본과 혼동하지 않는다.

기술 참고: [Epic TSR](https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-in-unreal-engine?lang=en-US), [Post Process Materials](https://dev.epicgames.com/documentation/unreal-engine/post-process-materials-in-unreal-engine), [Cooked Content](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-cooked-content-in-the-unreal-engine), [FModel](https://github.com/4sval/FModel). 실제 render 순서/API는 설치된 UE5.8 소스를 우선했다.

## 2026-10-06 최종 파일·사용자 세션 확인

마지막 메인12package SHA가 설치 manifest와 모두 같으며 map SHA는 `9da24fa9daffe01aa5a5ed581d3b4ac6466592a92e1638b0c0f8b530d58ea251`이다. before/after의4비교 카메라 수치는 Player/Entry/ReferenceStart 차이0, OpenSky 회전 readback차이`2e-12`로 대응한다. 같은 카메라 비교이지 같은 원작 build의 동일 시점 비교는 아니다.

`FinalLiveReadonly.json`: PID27916/DevMap/Idle, dirty map/content0,100%/TSR4/AA quality3. 사용자 editor에 saved HeinMach를 자동 reload하지 않았다. 이번 작업의 background UE는 모두 종료했으며 다른 CombatEffects 작업의 commandlet은 유지했다. 이전 로그/미확인사항과 새 저장본의 검증 범위를 위 정본대로 구분한다.


<!-- HeinMachGhosting_20261008_applied -->
## 2026-10-08 — HeinMach 이동 캐릭터 선명도·잔상 수정

현재 Main3528은 내부 해상도87%, sg.AntiAliasingQuality2, TSR history100%, velocity weight-clamp sample4였다. AA2는 UE의 High 그룹이며, 이전 세션의 Epic3/100%가 계속 유지된 상태는 아니었다. 8개 PP volume은 이미 motion-blur override0이고, regional look은 BL_SCENE_COLOR_BEFORE_DOF였다. 이번에 다시 blur/DOF를 원인으로 단정하거나 기존 pass 수정을 반복하지 않았다.

실제 입력으로 실행한 BP_Player는 본체만 CustomDepth=True/Stencil254였고 Original Torso/Shoes/Leg/Hair/Arm 및 양쪽 무기는 False/0이었다. 따라서 현재 PP가 visible 의상·무기 표면과 본체를 서로 다른 character/world shading 및 outline 분기로 분류하는 구체적인 불일치가 있었다. 이 계약은 원작 stencil 값의 복원이 아니라 기존 native 룩의 캐릭터 예약값이다. 기존 template7에 True/254만 복원했다. 에셋·Config 변경의 세부 책임은 Engineering의 SOURCE_BP_CONFIG_ARCHITECTURE 이번 절을 따른다.

원작 shader 수치가 아닌 명시적 native 튜닝: r.TSR.Velocity.WeightClampingSampleCount4→2. 설치 UE5.8 Renderer/Private/PostProcess/TemporalSuperResolution.cpp의 해당 CVar 설명은 값이 클수록 움직임이 흐려지며 선명도에2를 제시한다. native100 viewport/PIE를 프로젝트 DefaultEditor에 저장했다. AA2/history100은 유지했고 Epic history200을 전달하지 않았다. history200은 각 축2배라 history 픽셀 수4배이며, 이번 해결에 필요하다고 검증되지 않았다. count2 설정은 프로젝트의 TSR 전체에 적용된다. 해상도87→100은 내부 픽셀 수가 1/(0.87²), 약1.321배가 되는 비용이 있다. 이를 FPS 향상으로 표현하지 않는다.

검증은 hidden private real-RHI game의 EnhancedInput action 주입→기존 PlayerController/CMC/GAS→실제 ABP/weak attack montage 경로다. single-node pose/SceneCapture/HighResShot 비교가 아니다. baseline87/AA2/count4, native100/AA2/count4, native100/AA2/count2, native100/AA3/count2, native100/AA2/count2/parts254의5조건을 각각200프레임/13사진으로 관측했다. 모든 조건에서 실제 이동과 공격 montage를 확인했고 TSR history100은 동일하게 유지했다. 정성적으로 native100/짧은 history/통일된 mask 쪽의 의상·무기 경계가 선명해졌다. 물리의 시간 누적·눈 파임·노출 차이가 있어 이미지 차이를 정량적 ghosting 점수나 완전한 동시 pose 비교로 사용하지 않는다. sample tick 평균은37.68/37.67/37.85/38.12/38.72ms였으며 dual-editor·30FPS 제한·Shot 계측이 포함돼 제품 성능 벤치마크가 아니다.

추가 실제 velocity/reprojection viewport와 regional PP on/off를 확인했다. 캐릭터 전체의 공통 velocity 누락을 근거로 per-bone velocity/CopyPose/의상 physics를 비활성화하지 않았다. r.MotionVectorSimulation0은 camera-cut simulation 기본값이며 이를 general skeletal velocity-off로 오인하지 않는다. UE5.8의 미등록 r.PostProcessAAQuality 조회0도 AA-off 근거로 사용하지 않는다. per_bone_motion_blur=True/URO=False/AlwaysTickPoseAndRefreshBones 및 독립 CopyPose/RigidBody를 보존했다. 빠른 masked hair·모든 전투 pose에서 잔상0/원작과 동일함까지 검증한 것은 아니다.

증거: Saved/ImportReports/HeinMachGhosting_20261008의 RuntimeProbe/MaterialProbe/MainReadOnly, Parts authorReport/auditReport 및 FreshConfigAudit, Captures/20261007T221643_574561Z/CaptureMetadata, VelocityCapture, MainDelivery, FreshRuntimeVerification.json. 실패한 delegate-handle JSON 기록은 계측 cleanup을 수정했고, BG game의 Main BP 파일 잠금은 해당 소유 game만 정상 종료해 해제한 뒤 선택 전달했다. 실패 기록 MainDelivery_BackgroundGameLock.json을 보존했다. 사용자 editor3528의 dirty content/map0를 확인한 후 BP_Player package만 fully_load/reload했으며 map save/reload·PIE·close는 하지 않았다.

Main canonical/Contact55 preview map 및 Snow source·module manifest SHA를 유지했다. 기존 Contact55 worker2256의 canonical 대기 작업을 이번 ghosting 수정의 미완료로 합치지 않는다. 작업 결과는 Main 적용/선택 reload 및 별도 fresh runtime 검증 완료다. 재검사는 별도 background 게임에서 heinmach_ghosting_game.py의 새로운 pid/session mailbox를 사용하고 actual-input 캡처를 실행한다. 기존 user editor를 capture 대상으로 사용하지 않는다.


<!-- HeinMachGhosting_20261008_viewport_readback -->
## 2026-10-08 — 현재 에디터의 별도 해상도 driver 확인

최종 현재 뷰포트 readback 보완: 에디터 전용 real-time mode1/display-resolution 및 non-real-time mode2/DPI도 현재 세션에서 Manual0으로 바꿨다. r.ScreenPercentage100만으로 에디터의 별도 resolution driver가 Manual이 됐다고 가정하지 않았다. r.Editor.Viewport.ScreenPercentageMode.RealTime0/NonRealTime0/ScreenPercentage100 및 TSR count2를 Main3528에서 확인했다. AppData 전역 사용자 config를 저장하지 않았고 dirty0/noPIE·현재 world를 유지했다. MainViewportReadback.json이 증거다. 재시작은 프로젝트 DefaultEditor로 동일하게 검증됐다.
