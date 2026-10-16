# 2026-10-06 HeinMach 후처리·SkyBox·강설 복원

## 실제 저장한 범위

사용자의 직접 구현 요청으로 `/Game/Maps/L_HeinMach_Environment`와 HeinMach 전용 렌더링 에셋을 수정했다. 모든 Unreal 작업은 RiderLink/ModelContextProtocol을 끈 별도 숨김 프로세스에서 수행했다. 사용자가 Rider로 실행한 에디터에 연결하거나 명령·저장·재로드·종료를 보내지 않았다. 게임 C++/게임플레이 BP/Config/애니메이션과 StormPass 맵은 이번 작업의 편집 대상이 아니다.

- 후처리의 원작 `bOverride=false`를 활성화하던 복사 오류를 교정했다. 비활성 필드가 native override로 살아나지 않게 한다. 원작 override가 없는 필드는 원본 확인값이라고 부르지 않는다.
- 기존 크기가 0인 후처리 볼륨을 원작 BSP 면과 transform으로 복원했다. `Node.iVertPool → Vert.pVertex → Point`와 원작 Surfs의 normal/UV를 사용한 7개 볼륨, 81개 면이다. Source Points/Bounds 일치 검사 후 import했다. 단순 AABB로 원래 경계를 대체하지 않았다.
- OP/Blizzard1/Blizzard2/Boss/Cave1/Escape별 원작 하늘 색·별·성운·구름 프리셋과 두 구름 레이어를 전용 재질에 연결했다. 지역 혼합은 엔진 PostProcessVolume/동일 parent MI의 파라미터 혼합을 사용한다.
- source SkyMesh 위치·scale, 전용 sky MI, sky 식별용 stencil 252를 저장했다. 원래 character stencil 254는 유지한다. 먼 geometry를 거리만으로 하늘로 판단하던 분기는 sky stencil과 scene/custom depth 일치 검사로 바꿨다.
- 원본 강설 텍스처와 두 벡터 필드를 추출·임포트해 GPU Niagara 두 레이어를 구현했다. 기존 소유자와 Niagara 기능을 사용하며 새 runtime C++/BP weather manager는 만들지 않았다.

현재 저장 맵은 9,610 actors다. 사전 9,609개 중 삭제된 actor가 없고 강설 NiagaraActor 하나만 추가했다. pose 변경은 원래 PP 7개와 sky mesh뿐이다. PlayerStart와 다른 모든 actor pose, 이전에 삭제한 18+109개 항목의 부재를 유지했다. 검사 정본은 `FreshSavedSceneAudit.json`이다.

전용 에셋 폴더는 `/Game/_Art/Player/Environment/Rendering/HeinMachWeather`다. 현재 사용 중인 시스템은 **`NS_HM_SourceSnow_TwoLayers`**이며 `HM_Environment_SourceSnow`가 참조한다. emitter는 `Source_Flakes_Fast_Large`, `Source_Dust` 각 하나다. 중간에 생성한 불완전/검사용 시스템 4개와 QA 재질/MI 5개는 전체 referencer가 0임을 확인하고 SHA-256 byte backup 후 제거했다. `GeneratedUnusedCleanup.json` 참조. 기존 사용자 에셋을 정리 대상으로 삼지 않았다.

## 원작 자료와 수치 출처

원작 설치 리소스에 기존 EnemyExtractor/FModel의 CUE4Parse provider를 사용했다. 기존 cached JSON/report에서 시작해 필요한 package, texture, vector bulk, Model.Verts만 표적 추출했다. AES 값은 문서/출력에 남기지 않는다. 설치 게임의 표시 build 번호와 다른 영상 build의 일치 여부는 확인하지 않았다. 아래 수치의 식별 근거는 저장된 original package/JSON/hash다.

자료 폴더:

- `Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002/SourceManifest.json`
- `Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006/`
- `Saved/Extracted/HeinMachWeather_20261006/Source/BBQ/Content/`
- 원본 sky/level cached JSON: `C:/Users/user/Desktop/카잔/Exports/BBQ/Content/`

주 강설 package는 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Level/BBQ_Level/Enviroment/FP_World_IceBlizzard`다. 추출 JSON SHA-256은 `a65e587fa456e574f8f9e935cab970802d928934fcb16f9bedbdb65e6b3d32ef`다. 전체 모듈/ResourceData/참조는 `SourceParticleContracts.json`에 보존했다.

| 원본 field / 조건 | 원작 직접 확인값 | 현재 적용 |
| --- | --- | --- |
| WEP_HeinMach_OP의 WAS_IceBlizzard `Spawn`, GPU ParticleModuleSpawn `RateScale` | 500, uniform 2.5–5 | 계산값 `500 × [2.5,5] = 1,250–2,500 particles/s`, 두 GPU 레이어 |
| primary `ParticleModuleLifetime`, compiled GPU size | 5–6 s, 0.5–0.75 cm | 동일 범위, SpriteSize/Position write switches 명시 활성화 |
| primary StartLocation distribution | X −1,500–0, Y −250–250, Z 0–500 cm | OP source yaw 120°로 회전한 camera 중심 spawn box |
| primary StartVelocity distribution | X 750–1,250, Y −50–50, Z −500–−250 cm/s | 같은 uniform 범위·source OP 회전 |
| primary ParticleModuleVectorFieldLocal | scale 50, intensity 10,000, tightness 0.025, XYZ tiled | source 16³ bulk, Niagara sample/apply module |
| dust ParticleModuleLifetime | 1–2 s | 동일 |
| dust `ParticleModuleTypeDataGpu_1.ResourceData.MiscBias` XY / MiscScale XY | 0.3, 0.3 cm / scale 없음 | compiled GPU 기준 0.3² cm. 다른 editable StartSize table을 GPU 정본으로 사용하지 않음 |
| dust ParticleModuleLocationPrimitiveSphere | radius 50 cm | camera 중심 구형 spawn |
| dust initial velocity / constant acceleration / drag | (0,−2,1)–(5,2,5) cm/s / (1,0,1) cm/s² / 0–1 | source owner rotation과 native force/drag modules |
| dust vector field | 8³, scale 250, intensity 5,000, tightness 0.05, XYZ tiled | original 512 vectors |
| GPU CameraFade | 50 cm | world vertex–camera 거리의 선형 fade |
| primary/dust GPU color sample A | primary 16 samples, dust 8 samples | `Abyte/255 × ColorScale.W + ColorBias.W`, normalized lifetime 선형 보간 |
| dust missing WEP FlakeColor / distribution fallback / ColorBias | constant (1,1,1), compiled bias RGB (1,1.5,2) | GPU bias 사용. WEP SnowColor를 dust FlakeColor라고 오인하지 않음 |
| primary/dust SizeBySpeed | min scale 1, max Y 2 / 4 | velocity axis의 vertex offset으로 동일 clamp scale 적용 |
| FM_World_Snow_Particle texture / Rows / Columns | FT_SnowTickle_03, 4 / 4 | original 1,024² G8 atlas, random subimage, LinearGrayscale, sRGB=false |
| original material flags | responsive AA, two-sided, no vertex fog, output translucent velocity, separate translucency=false | Before DOF, velocity output, responsive AA, unlit/translucent |

두 source 벡터 필드는 FFloat16Color bulk의 XYZ를 FGA로 변환했다. 16³는 4,096, 8³는 512개의 원본 벡터를 사용한다. 생성된 random noise로 바꾸지 않았다. `VectorFieldExtraction.json`, `VectorFieldExtraction8.json`이 원본 bulk 위치·변환·차원·bounds/hash를 기록한다.

Niagara ApplyVectorField는 target velocity를 tightness와 다른 순서로 더한다. source force intensity는 유지하고 velocity input은 `source intensity × source tightness`로 연결했다. primary는 250, dust도 250이다. 이 변환은 **원작 기반 계산/native 적응**이며 Cascade와 모든 timestep에서 동일한 적분기라고 주장하지 않는다. camera-follow source local-space 대신 기존 눈송이가 camera 이동에 끌려오지 않는 world-space를 사용한다. camera query는 CPU EmitterUpdate 한 번씩에서 실행하고 GPU spawn에 위치를 업로드한다.

Sky mesh source는 `HeinMach_Light`의 xxSkyMeshComponent다. source relative location `(7917.611, −10604.79, −13768.473) cm`, scale `(50,50,50)`을 적용했다. 현재 mesh는 두 레벨이 공유하는 원본 `SM_WAS_SkyMesh`의 기존 import를 읽기 전용으로 재사용한다. stencil 252/254는 native renderer 식별 예약이며 원작 숫자가 아니다. source sun의 `SpecularScale=0.01`을 복원했다. 유지한 native sun 20,000 lux / SkyLight intensity 1은 원작 단위 변환의 직접 검증값이 아니다.

| source WEP profile | SkyColor preset | Cloud layer 1 / 2 | source rotation speed 1 / 2 |
| --- | --- | --- | --- |
| OP, Cave1 | SCM_SkyColor_GloomySunset | CCM_BaseZeroCloud_Layer1 / Layer2 | 0.001 / 0.00125 |
| Blizzard1 | SCM_SkyColor_Midnight | CCM_DramaticCloud_Layer1 / CCM_DeathCloud_Layer2 | 0.001 / 0.00125 |
| Blizzard2, Boss | SCM_SkyColor_Dawn | CCM_GloomyDawnCloud_Layer1 / Layer2 | 0.00025 / 0.00125 |
| Escape | SCM_SkyColor_Dawn | CCM_GloomyDawnCloud_Layer1 / Layer2 | 0.001 / 0.002 |

위 speed는 원작 WEP field의 원시 값이다. native UV/time 이동에 같은 값을 사용했지만 원작 구름 회전 함수의 전체 공식/각도 단위는 cooked material body 부재로 미확인이다. sky palette/Star/Nebula/Cloud scalar·vector의 상세 값과 원본 package는 `SourceDiscovery.json` 및 source JSON에 있다. 원작 BSP actor 209=Blizzard1, 210=Blizzard2, 211=Boss, 212·213=Cave1, 214=Escape, 215=OP다. 검수에서 끝자리로 profile을 추정하지 말고 이 대응을 사용한다.

## UE5 임시 보정과 실제 해결한 오류

`ExposureContractCorrection.json`이 최종 수치 정본이다. 이전 `LookApplied.json`의 shadow scale 2는 중간값으로 보존하며 현재 값으로 사용하지 않는다.

| native 임시값 | 선정 이유·영향·검증 기준 |
| --- | --- |
| Outdoor EV100 8, Cave EV100 4 | 눈의 명부와 covered view 노출을 분리. 같은 game view에서 흰 눈/어두운 바위/동굴 검수. original EV로 표시하지 않음 |
| Bloom 0.35, flare 0, dirt 0 | 원작 custom renderer의 큰 field 값을 native pass에 직접 넣었을 때의 과도한 번짐 제거. source serialized 값은 보존 |
| WorldToonWeight / WorldOutlineOpacity 각각 0.08 | 먼 바위/terrain의 과한 banding·검은 테두리 완화. character stencil의 별도 model 유지 |
| HM_NativeShadowFillScale 8 | actual game에서 2/4/8 A/B. source grade를 유지하면서 바위 texture 디테일을 복원. 원작값이 아닌 native 밝기 변환 보정 |
| sky/snow radiance 256 = 2^8 | native 고정 EV에서 source linear palette를 표현하기 위한 조정 |
| shadow radiance outdoor 256 / cave 16 = 2^EV | cave의 낮은 EV에서 shadow floor가 과도하게 밝아지는 문제를 방지. sky 물리 밝기와 shadow 보정 입력 분리 |

shadow floor는 `BaseColor × source BBQCartoonShadingBrightness × source BBQCartoonShadowAmbientIntensity × native scale × native shadow radiance × View.PreExposure`다. source brightness는 OP 0.45/Boss 0.5, source ambient는 0.5이며 해당 WEP directional/sky light component의 정확한 field에서 가져왔다. character stencil을 제외하고 기존 scene color와 max를 취하는 native 대체식이다. source BBQCartoon 전체 모델/동일 AO·GI 공식이 아니다.

재질은 pre-exposed HDR를 입출력하는데 UE5 PostProcessMaterial shader의 기본 경로가 input 역변환/output PreExposure 곱을 수행한다. `M_HM_RegionalLook.disable_pre_exposure_scale=true`로 계약을 맞췄다. 로컬 엔진 근거는 UE5.8 `PostProcessMaterialShaders.usf` 387–389, `MaterialTemplate.ush` SceneTextureLookup 및 `PostProcessMaterial.cpp` shader defines다. 노출 계약 수정만으로 원작 색보정/native brightness 차이까지 해결되는 것은 아니었으며 위 A/B 보정을 함께 적용했다.

눈의 불투명 흰 사각형은 ComponentMask 기본 R/G가 켜진 상태에서 A만 추가한 오류였다. emissive red가 Opacity로 들어갔다. 현재 Opacity mask는 정확히 `[R=false,G=false,B=false,A=true]`다. original atlas·lifetime alpha·camera fade가 실제로 적용됨을 game viewport에서 확인했다.

원작 material의 `DepthFade=10` scalar도 확인했지만 cooked node body/실제 사용 여부는 미확인이다. native DepthFade를 추가하면 UE5의 translucent velocity/depth 쓰기와 충돌해 컴파일이 거부됐다. 해당 시도는 저장하지 않았고 현재는 source velocity output과 camera fade를 유지한다. SceneDepth 접근을 숨기는 custom HLSL 우회는 사용하지 않았다.

Niagara sample module을 dynamic Vec3 input으로 취급하던 오류, InitializeParticle write switches가 꺼진 오류, GPU Camera DI가 offscreen PrimaryView를 읽어 stale 위치에 spawn하던 오류, 중복 emitter 생성도 수정했다. 현재 GPU vector input은 `Output.SampleVectorField.SampledVector`이고 saved system handle는 정확히 2개다.

## 검증 결과

- `FreshSavedSceneAudit.json`: 저장 map의 모든 기존 actor 존재/pose, PlayerStart, 8 PP, Cave flags, sky stencil/material, Niagara asset/autoactivate/no shadow/fixed bounds, 두 opacity mask 및 최종 native MI parameter 계약 통과. map 저장 이후 검수/cleanup은 map에 쓰지 않았다.
- `RenderGraphVerification.json`: 별도 real-RHI에서 4개 재질의 명시적 재컴파일 errors가 모두 빈 배열. pixel instructions regional 110 / sky 198 / flakes 107 / dust 107. 컴파일 통과 수치를 성능이나 원작 일치율로 바꾸지 않는다.
- `NativeSnowTwoLayers.t3d`, `NiagaraSupplement.json`: 두 실제 emitter/compiled graph export. 이전 `NativeSnow*` 파일은 각 시도의 이력이며 현재 시스템으로 오인하지 않는다.
- `GameViewportVerification.json`: 실제 `-game -RenderOffscreen` viewport에서 8,187 flakes + 3,115 dust를 관측했다. 두 레이어의 auto activation, 이동한 camera 주변 spawn, alpha 적용을 확인했다. 현재 저장된 PlayerStart game view, 눈 OFF, 위쪽 sky, 높은 sky 시점, original cave brush center probe를 캡처했다. 마지막 두 시점은 QA 위치이며 원작 gameplay camera라고 부르지 않는다.
- 최종 화면은 `Saved/ImportReports/HeinMachWeather_20261006/GameViewport_Source.png`, `GameViewport_SnowOff.png`, `GameViewport_Sky.png`, `GameViewport_OpenSky.png`, `GameViewport_CaveProbe.png`다. cave probe에서 눈이 보이지 않는 것을 실제 game view로 확인했다. Cave1 두 PP의 source weather에 falling snow가 없어서 native per-view UserFlags bit 0으로 alpha를 숨긴다.
- SceneCapture2D는 Lumen opt-in 및 SeparateTranslucency를 명시했지만 이번 Substrate/custom PP 경로에서 실제 game과 다른 검은 음영·노이즈가 관측됐다. `FinalVisual.json`/SceneCapture 이미지를 최종 game 외형 판정으로 쓰지 않는다. `ActualGame_Diagnose_*`, `GameViewport_DiagnosticCube`도 해당 진단 조건의 이력이며 최종 적용 이미지가 아니다.

성능은 Ryzen 5 5600X / RTX 3060 Ti, DX12 SM6, Development 실제 offscreen game, 1,280×720, t.MaxFPS=30에서 눈 ON 180 / OFF 185 numeric frames의 CSV를 비교했다. 사용자 Rider 에디터가 동시에 실행 중이었다. 연속 두 구간의 local 측정이며 shipping/전 구간 성능 보장이 아니다.

| 측정 항목 | 중앙값 | P95 |
| --- | --- | --- |
| GPU/NiagaraGPUSimulation, 눈 ON | 0.04635 ms | 0.05350 ms |
| GPU/Translucency, 눈 ON | 0.12230 ms | 0.12910 ms |
| GPU/Translucency, 눈 OFF | 0.04590 ms | 0.04990 ms |

translucency 중앙값 차이는 +0.07640 ms다. 다른 pass·background variance를 포함하지 않은 부분 측정이다. dispatch count=2를 2 ms로, tick count를 시간으로 해석하지 않는다. parser는 CSV 끝의 최신 header와 중간 추가 columns를 사용한다. 자료는 `PerformanceVerification.json`, `Saved/Profiling/CSV/HM_Snow_On_20261006.csv`, `HM_Snow_Off_20261006.csv`다. GPU 양자화/renderer·해상도·camera가 달라지면 다시 측정한다.

검사용 bare transient Material을 `-game`에서 만들다 EditorOnlyData 초기화 경로 때문에 백그라운드 process가 한 번 access violation으로 종료됐다. MaterialFactoryNew로 미리 만든 QA asset을 읽는 방식으로 바꿔 A/B 완료/exit 0을 확인했고 QA 5개를 이후 제거했다. 사용자 에디터의 crash가 아니다. source/shader authoring 시 중간 미연결 노드 compile warnings와 최종 `recompile_material()` errors를 구분한다. runner는 known stage success marker까지 확인하며 process exit 0만으로 authoring 통과를 보고하지 않는다. 오래된 `SnowFailure.json`/`LookFailure.json`은 실패 시도 이력이고 위 최종 성공 검사와 구분한다.

## 미복원·미검증 계약과 정확한 재개

이 결과는 원작 리소스 기반 native 복원과 실제 검수다. **원작과 차이가 없다는 판정은 아직 할 수 없다.** 원작 cooked export에서 material node body와 BBQ 전용 shading/PP shader source가 제거돼 있어 palette/parameter 재현과 원작 shader 실행 일치는 다르다. spherical UV/gradient, cloud mix, star blink, nebula mix 및 shadow floor는 명시한 native 대체식이다.

현재 snow는 OP standard 두 GPU emitter의 native 이관이다. 원본은 CPU collision/event emitter와 지면 puff emitter도 가진다. 다음은 현재 구현 완료로 표시하지 않는다.

- 원작 CPU collision → ground smoke/puff event 연계 및 별도 WindDust closure.
- dust vector field RotationRate `(0.1,0,0.1)`의 original 공간/단위·적분과 native 이관.
- Blizzard1의 `WAS_IceBlizzard_Max`/MaxBlizzard template 교체, 전 지역 Spawn/색/Blow/yaw의 runtime 전환과 원작 blend/lifetime. 현재 sky/grade 지역 전환은 저장됐지만 snow 전체의 지역별 강도 전환은 아니다.
- OP 500/yaw120; Blizzard1 Max Spawn3/PlakeSpawn1000/yaw85; Blizzard2 Spawn500/Blow5/yaw70.700005; Boss Spawn1000/Blow7.5/yaw30; Escape Spawn750/Blow5/yaw70.700005의 원시 WEP 데이터는 저장돼 있다. `Blow`를 확인 없이 vector field force multiplier라고 가정하지 않는다.
- MoonCrack/Planet 등의 source 참조는 조사했으나 해당 HeinMach 실행 상태의 활성화 조건이 확인되지 않아 임의 spawn하지 않았다.
- 같은 build 원작과 같은 camera/time에서 controlled side-by-side 및 전체 route·보스·camera clipping 검증.

재개 순서는 Router → 이 정본/Art 최신 continuity → SourceDiscovery/SourceParticleContracts/최종 audit/PerformanceVerification이다. 원본 전수 재조사·map 전체 rebuild·다른 맵/PlayerStart reset을 반복하지 않는다. 필요한 source emitter/function만 표적 조사해 현재 Niagara 소유자/재질/기존 volume을 우선 확장한다.

기존 사용자 Rider editor는 건드리지 않는다. 저장된 변경을 그 editor에서 보려면 사용자가 본인의 미저장 변경 여부를 확인하고 HeinMach map/변경 asset을 재로드해야 한다. assistant가 stale live map을 Save All 하거나 전체 backup으로 덮어 복구하지 않는다.

재검수는 standalone Python `C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe`로 `Scripts/Art/run_heinmach_weather_background.py audit`, `render_probe --render`, `game_capture --render --game`를 순서대로 실행한다. 그 다음 `analyze_heinmach_weather_performance.py`를 실행한다. sky/shadow 미세 보정은 `heinmach_weather_look.py NATIVE`와 전용 MI, snow 재질 보완은 `heinmach_weather_snow.py`에서 수행한다. 이미 built인 system에는 emitter를 다시 append하지 않는다. `probe`는 immutable Before.json을 덮어쓰므로 재실행하지 않는다. QA A/B를 다시 하려면 `qa_materials --render`를 먼저 실행하고 필요 후 명시한 task QA만 cleanup한다.

사전 map/대상 shader 백업은 `Saved/ArtBackups/HeinMachWeather_20261006/Content`, 삭제한 task 시험 asset 백업은 `GeneratedUnused`다. backup은 당시 상태이며 이후 사용자 변경을 일괄 덮어 복원하는 용도가 아니다. 정확한 작업 범위·검증·실패·남은 계약을 보존하고 후속 결과는 아래 날짜별 절에 추가한다.

## 2026-10-06 최종 디스크 결과 검증

`DeliveryVerification.json`을 추가했다. 정리 이후 별도 NullRHI 프로세스에서 맵을 다시 읽은 audit가 exit 0/성공 marker로 통과했다. map SHA-256은 `f229d15245e511fa3c347c96ccdd0dc1bf35ce158332e63d064aad4d8cf6f7a2`이며 actors 9,610, 전용 사용 asset 15개, 실제 game PNG 5개(각 1,280×720)의 존재·해시와 4개 재질 compile errors=0을 확인했다. 이 검증은 원작 렌더링 동일성 판정이 아니다.

명시한 시험 Niagara 4개는 commandlet의 `delete_asset=true` 이후에도 byte-identical 파일이 남아 있었다. 삭제 전 referencer 0과 backup SHA 일치를 확인한 해당 작업 생성 파일 4개만 정확한 경로로 제거했다. QA 5개를 포함한 9개 모두 최종 디스크 부재와 backup SHA가 확인된다. 정리 재실행에서 이미 없는 package의 `get_referencers`는 `None`을 반환하므로 최종 보고서는 `referencer_query_state=package_missing`으로 기록한다. 이를 새로운 referencer 0 측정이라고 해석하지 않는다. 남은 실제 asset/맵 참조는 이후 fresh audit가 검사했다. 이 단계는 map을 저장하지 않았다.

별도 작업 프로세스는 모두 종료됐으며 사용자 Rider editor에 명령이나 재로드를 보내지 않았다. 최종 primary game 이미지의 바위 음영·투명 눈송이, OpenSky의 하늘, CaveProbe의 강설 숨김을 확인했다. 위 미복원 계약은 그대로 남아 있다.

## 2026-10-06 후속 사용자 요청 — 에디터에서 변경 확인

사용자가 미저장 작업 확인 후 변경 에셋을 다시 불러오도록 직접 요청했다. 이 확인 작업에는 이전 background-only 제한 대신 최신 열람 요청을 적용했다. 요청 시 실행 중인 UnrealEditor 프로세스와 RiderLink 연결이 없었으며, 마지막 세션의 정상 종료와 autosave 복구 목록 0개(`RestoreEnabled=false`)를 확인했다. 새 interactive editor(PID 9596)에 HeinMach를 열고 RiderLink로 확인했다. 최초 dirty map/content는 모두 0개였다.

`LiveEditorReloadVerification.json`: 저장된 맵과 전용 에셋 15개의 SHA-256이 `DeliveryVerification.json`과 같음을 확인하고 파일을 다시 읽었다. actors 9,610, `NS_HM_SourceSnow_TwoLayers` 연결 확인. 게임 C++/BP/렌더 에셋/맵을 저장하거나 수정하지 않았다. 편집 뷰포트는 입구의 검수 카메라로 맞췄다.

편집 화면의 입자 검사에서 World를 outer로 만든 NiagaraSimCache가 `Modify()`를 통해 맵을 dirty로 표시했다. 원래 미저장 항목이 0개였던 세션이며, 작업이 만든 임시 캐시는 맵을 저장하지 않고 다시 읽어 제거했다. 이후 검사는 `unreal.new_object(unreal.NiagaraSimCache)`의 `/Engine/Transient` outer를 사용한다. live editor에서 `create_niagara_sim_cache(editor_world)`를 반복하지 않는다. `editor_set_viewport_realtime(true)`는 엔진 구현상 기존 override 제거이며 기본 Realtime을 켜는 API가 아니다. 없는 override를 제거하면 handled ensure가 발생하므로 반복 호출하지 않았다. Computer Use는 native pipe가 없어서 규정된 retry/reset 후 사용할 수 없었으며, 에디터 API와 Rider screenshot으로 확인했다.

`LiveEditorPIEVerification.json`: viewport PIE/PlayerStart에서 강설 활성, flakes 8,817/dust 3,520 관측. dirty map/content는 모두 0개다. 사진은 `Saved/Screenshots/WindowsEditor/RiderMCP/20261006-041831_editor_window.png`이며 화면에서 눈과 기존 레벨을 확인했다. 사용자 열람을 위해 PIE `Play` 상태로 editor를 열어 두었다. 편집으로 돌아갈 때는 Stop/Esc를 사용한다. 새 preview editor를 종료하거나 사용자 소스의 빌드·수정으로 확대하지 않았다. 시작 로그의 GameFeatureData class 관련 handled ensure는 기록돼 있으나 이 세션의 map 로드/PIE 확인은 통과했다. 원작 일치/미복원 범위는 위 기록 그대로다.

## 2026-10-06 후속 원작 사진 비교 — 강설·합성 현행 계약

[HEINMACH_REFERENCE_MATCH_2026-10-06.md](HEINMACH_REFERENCE_MATCH_2026-10-06.md)와 `Rendering/Metadata/HeinMachReference_20261006`이 현재 저장값/검증의 우선 자료다. 기존2GPU graph와 원본 atlas/VF/크기·수명을 유지하며 EffectType spawn`.25` 적용, near fade150cm, snow/dust depth/velocity 출력false, BeforeDOF/ResponsiveAA/A-only 유지. PP master는 TSR 이전 BeforeDOF, sky 가시성 판정과 OP priority 교정. 동일 조건 particles8600+2298→2382+784, sim median`.0164→.0138ms`; 전체FPS 보장 아님. main saved-game/fresh audit/12package SHA 검증 통과. 본서의 velocity true/near50/과거 grade·Start는 현재 지시 범위에서 대체되며 미복원 weather/BRDF/원작 controlled 동일성 계약은 새 정본에 계속 남긴다.


## 2026-10-13T02:25:35.076330+09:00 — 현재 효과 알파 카드 경계·HeinMach 눈 수 Main 수정 완료

정본은 `Metadata/ParticleAlpha_20261013/FinalVerification.json`이다. 기존 사용 metadata→현재524 animation의 notify/HeinMach96 effect component→331 PS/NS·281 material interface를 확인했다. 전체 Content/원작 추출을 재조사하지 않았다. 직접 renderer 재질203/부모86, 현재 alpha 입력의 실제138 PNG 채널·부모/인스턴스 상속을 확인했다. HDR4 lookup/검정 float는 PNG 강제 변환하지 않았다.

공용 `Shared/Materials/Other/DefaultParticle`은 PC.A만 opacity mask로 사용해 실제 카드가 흰 사각형이었다. 기존 Masked blend를 유지하고 타원 공간 마스크를 연결했다.16 sprite instance는 실제 sampled texture의 A가255 상수인 채 불투명 카드를 그렸다. 해당 instance에만 R density/particle Alpha 선행 clamp/안쪽 feather를 적용한다. 부모 default repair0과 원래 source RGB·particle modules/shape/수명·event/animation·mesh/Additive 정책은 보존한다. 어시스턴트 표시 TEMP는 feather.03UV/최소1.25px/무텍스처 ellipse power2이며 원작 shader 수치가 아니다.

메인 선택30파일=부모13+MI16+기존 NET_HM_WeatherBudget1을 hash/CAS 전달했다. Source/Config/map/PS/NS/texture/바이너리·QA asset 전달0이다. 기존 눈2레이어의 source1250/2500 particles_s는 그대로이고 생성 scale.25→.20(어시스턴트 표시 TEMP)으로 rate312.5/625→250/500, 기존 대비20% 줄었다. 실제3샘플 평균 flakes2119→1862.33/dust532.67→454.67로 감소했다. 이는 random/time-dependent active count이며 매 순간 정확히20%라는 뜻이 아니다. 눈 크기/속도/수명/재질·camera/원본 actor 배치는 바꾸지 않았다.

새 MainShaderVerify01은86 material compile errors0·16 scalar override·snow.20, MainSnow01은 실제 game view/count/저장0으로 통과했다. standalone 동일 camera card17의 검은 사각·solid card 제거 및 texture 양성을 직접 확인했다. actualPS8 중4는 기본 단독 parameter에서 active0이므로 전체8 양성 화면 검증이라고 기록하지 않는다. 실제 PartGroggy blood/짧은 blade·wood 표본과 눈 entry/sky를 검수했으며 모든 전투 frame/camera·Shipping/원작 shader 전체 동일성은 주장하지 않는다.

초기 protected API/강제 HDR PNG/fixture reentrancy/PIE viewport/반환값·부분 저장 실패는 각 run에 보존했다. Windows 접근 제한은 별도 consumer의 정상 종료 후 선택 전달로 해결했으며 foreign editor 종료/저장/reload0이다. task-owned CardsBefore01 hung fixture만 정확 PID/args 확인 후 정리했다. 모든331 source system과 HeinMach map·눈 graph hash가 원본과 일치한다. 후속은 이 보고서/RepairPlan/TextureChannelAnalysis에서 표적 시작하고 prepare/전체 author/과거 CAS를 반복하지 않는다. 필수 잔여0이다.

<!-- ParticleAlpha_20261013_MainCompleted -->
