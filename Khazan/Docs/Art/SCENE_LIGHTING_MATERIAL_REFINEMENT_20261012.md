# DevMap · HeinMach 조명과 표면 표현

## 2026-10-12 — 작업 시작 / 실제 저장본 기준

사용자 요청은 두 레벨의 과한 밝기, 어두운 음영, 어색한 그림자와 표면 표현을 자연스럽고 실사에 가까운 방향으로 조정하는 것이다. Art 작업이며 기존 gameplay/Animation/Audio/VFX 수명은 이번 수정 대상이 아니다.

최신 HeinMach 정본 `HEINMACH_CLEAN_PRESENTATION_20261011.md`의 PP8 제거 결과를 기준으로 한다. 옛 source 룩/지역 toon 볼륨을 다시 생성하지 않는다. 기존 `HeinMach_UserExclusions`, `HeinMach_OptimizationExclusions`, `HeinMach_ManualOverrides` 및 현재 배치/눈 변형을 보존한다. 원작 자료는 `Rendering/Metadata/LookRestoration_20261002/SourceManifest`, `HeinMachReference_20261006`와 기존 표면 channel 감사에서 표적 재사용한다.

별도 작업본 `C:/Users/user/Desktop/GitProject/Khazan_SceneLookWork_20261012/Khazan`을 만들었다. 두 Map만 독립 복사했고 다른 Content/Source/Plugin은 읽기 전용 소비를 위한 junction이다. 새 runtime class/file은 없다. 사용자/외부 editor에 명령을 보내지 않는다. Main 두 map과 Source/Config/module baseline·backup은 `Metadata/SceneLook_20261012/Baseline.json`과 `Before`에 보존한다.

검사는 `Scripts/Art/scene_look_task_20261012.py`의 task-owned 숨김 editor로 수행한다. `scene_look_capture_20261012.py`는 실제 PIE game viewport의 일반 Shot을 사용한다. SceneCapture 및 HighResScreenshot 결과를 실제 게임 화면으로 바꾸어 기록하지 않는다. 전후 QA 품질은 같은 High GI/Reflection/Shadow, Epic AA, native1600×900이며 제품 설정에 저장하지 않는다. 조명·노출 수치를 원작 직접 값/계산/임시 tuning으로 구분한다. 아직 적용이나 시각 검증 완료가 아니다.

현재 절은 시작 상태다. 실제 원인, 최종 값·변경 package·Main 전달·새 프로세스 검사 결과는 아래 날짜 절에 추가한다.

## 2026-10-12 — 검증된 조정본 / Main 파일 잠금 대기

현재 실제 맵은 `/Game/Maps/DevMap`, `/Game/Maps/L_HeinMach_Environment`다. 최초 Main은 Dev24/Hein10008 actor이며 후처리0이다. 예전9861 actor 기록은 후속 사운드 배치 전 이력이다. 이번 조정본은 노출·렌더링 품질만 소유하는 `Art_NaturalLighting_DevMap/HeinMach` 볼륨 각1개를 추가했다. 새 C++/BP runtime class, Toon/outline/custom blendable, Source/Config/module 변경은 없다. 이전 후처리8 제거 요청의 커스텀 룩을 복구한 것이 아니다.

| 소유자/field | 실제 기존 값 | 최종 값 · 출처 | 선택 이유·검증 |
|---|---|---|---|
| Dev DirectionalLight.Intensity | 6 lux | TEMP 6000 lux | 현재 atmospheric sky 조합의 native 조도 범위를 재조정. 원작 광도 아님. DevAfter02 실제 역광/후면 비교 |
| Dev Sun.LightSourceAngle | .735700° | TEMP2.5° | 바닥의 날카로운 그림자 경계 완화 |
| Dev SkyLight.Intensity | 1 | TEMP8 | 역광 피부·의상·장비를 읽을 수 있도록 sky fill 증가. trial4/8 및 hardware/software 비교, HW 해제/정적 캡처는 최종 미채택 |
| Dev Exposure min/max/bias | authored PP 없음 | TEMP7–14 EV100 / +.65 EV | 조도 재조정과 함께 midtone 보존. 속도 up/down1 EV/s도 TEMP이며 PP Details에서 조정 가능 |
| Hein Sun.Intensity / SourceAngle | 5000 lux /5° | TEMP2500 lux /3° | 눈의 과도한 흰 영역과 넓은 뭉친 명암 완화. 원작 lux 변환 확정값 아님 |
| Hein Sun.SpecularScale | .01 | native PBR 보정1 | source OP의 cartoon 계열 specular 억제값은 원본 자료에 보존하고 stock PBR에서 재질 반응을 복구.1을 원작값으로 표현하지 않음 |
| Hein SkyLight.Intensity / LightColor |1.1 / FColor(168,196,213)|TEMP4 / (255,255,255)|이미 색이 있는 captured source sky에 별도 tint를 중복 곱하지 않고 어두운 면의 fill 강화. sky material/texture는 그대로 |
| Hein source/fire local light Intensity | 최초 SavedScene의189개 current 값 | TEMP 최초값×.3 | 상대 색/배치/radius/falloff/flicker 유지, 과한 횃불·지역광 억제. 기존22500 unitless 예는6750이 되는 계산값. 반복 author는 최초 baseline을 사용해 곱을 누적하지 않음 |
| Hein Exposure min/max/bias | authored PP 없음 | TEMP4–13 EV100 /−.6 EV | 눈 highlight 보존하면서 지역 자동 노출 유지. fixed EV로 동굴을 덮지 않음 |
| 공통 FilmToe / AO intensity | engine 기본 | TEMP.45 / .35 | 낮은 밝기의 경계와 중복 가림을 완화. global saturation/contrast/color gain은 추가하지 않음 |
| LocalExposure Highlight / Shadow contrast | 기본중립1/1 | TEMP.9 / Dev.95·Hein.75 | 눈 highlight와 어두운 바위 면의 범위를 좁힘. 별도 toon shader 없음 |
| Lumen scene lighting / final gather / reflection quality | PP override 없음 | native 품질 선택2/2/2 | 기존 Lumen/VSM/ray tracing 설정 재사용. renderer global Config 변경 없음 |

수치는 `scene_look_author_20261012.py:POLICY` 및 DevAuthor02/HeinAuthor03의 policy/pp_fields에 모였으며 원작 검증값 또는 사용자 직접 지정값이 아닌 **어시스턴트 TEMP 미술 조정**이다. 각 기존 Light/새 PP Details에서 조정한다. 기존 actor/component 위치·스케일·방향은 바꾸지 않았다. 두 sky dome의 CastShadow/AffectDistanceFieldLighting/AffectDynamicIndirectLighting/VisibleInRayTracing만 꺼서 sky proxy가 장면 가림·광원 전달에 개입하지 않게 했다. RealTimeCapture는 유지한다.

### 재질의 실제 오류와 최소 수정

현재 환경의 masked USD MI489개가 상속하는 `/USDCore/Materials/UsdPreviewSurface`에는 Opacity 출력만 있고 OpacityMask 출력이 없다. source Masked override를 저장한 사실과 실제 alpha shader 입력이 연결된 사실이 달랐다. 엔진 material/plugin을 고치지 않고 project-local `Rendering/SceneLook/M_HM_PBR_Masked`와 기존 translucent intermediate의 호환 복제1개만 만들었다. 사용 중인489 MI의 parent를 해당 호환 parent로 연결했다. alpha UV·texture component·UseOpacityTexture·Opacity·원래 clip 값을 유지하고 explicit RGBA dot 후 기존 Opacity lerp→OpacityMask를 연결한다. native component가 A인481개와 R인8개를 그대로 소비한다. source texture 재임포트·압축/gamma 변경은 없다.

`MainBeforeParameters01`→`PreparedSaved02`는489개 모든 scalar/vector/texture 값 및 base-property overrides의 일치를 확인했다. 의도한 예외는 `WM_COM_SmallTree_Base_001/002/003_02`의 native UseEmissiveColorTexture1→0뿐이다. 실제 Tex_E가 포화 green/yellow RGB mask인데 기존 adapter가 이를 radiance로 직접 내보냈다. 텍스처 바인딩은 유지했고 native PBR에서 raw glow를 끄는 TEMP 보정이다. 원작 emission HLSL을 확보했다거나 원작 glow가0이라고 주장하지 않는다.

원작 표적 경로는 `Desktop/카잔/Exports/BBQ/Content/Art/World/World_Material/Prop/Material/WM_COM_SmallTree_Base_00{1,2,3}_02.json`이다. exact SHA/field는 FoliageFinish03에 있다. 원작 BasePropertyOverrides.ShadingModel=MSM_TwoSidedFoliage, leaf003의 source Diffuse_Intensity/SSS_Mask_Intensity=.8, Tex_D=WT_COM_ThinTree_Base_001_03_D, Tex_E=WT_COM_ThinTree_Base_001_02_E를 확인했다. native/source PNG alpha0–255와 native CompressionNoAlpha=false도 확인해 알파 유실·재임포트 가설은 채택하지 않았다.

Stock TwoSidedFoliage 및 diffuse 기반 transmission 시험은 HeinAfter02에서 leaf가 과도하게 희어져 **시각 불합격**으로 철회했다. FoliageNormalize01은 기존 base-property overrides를 복원했다. 최종 DefaultLit/기존 two-sided/clip 정책이며 source 전용 shader 이식 완료가 아니다. 실패 enum/setter API 실행과 원래 texture/export/역광 trial을 보존하고 최종 proof로 사용하지 않는다.

### 검증·정확한 재개

최종 준비본은493 package/map(기존 MI489+새 부모2+map2), `PreparedDelivery.json`에 Before/Prepared SHA가 있다. `PreparedSaved02` 성공: actor25/10009, 기존 protected pose24/10008의 변화0, scalar/vector/texture/base overrides의 예상 밖 차이0, PP 각각1/custom blendable0. 조회 중 기존 Audio cue1개가 derived dirty로 표시됐지만 저장0이며 선택 author/saves에 포함되지 않는다.

실제 D3D12 game viewport 전후는 DevBefore01→DevAfter02, HeinBefore01→HeinAfter04다. 같은 QA High GI/Shadow/Reflection·Epic AA/100% TSR을 적용했으며 요청 editor 창1600×900과 **실제 Shot1092×573**은 구분한다. 시작 절의 native1600×900 문구는 이 절로 정정한다. SceneCapture/HighResScreenshot을 쓰지 않았다. snow/cloth/pose는 시간에 따라 달라 pixel-identical 비교가 아니다. [Dev 비교](../../Metadata/SceneLook_20261012/DevMap_BeforeAfter.jpg), [Hein 비교](../../Metadata/SceneLook_20261012/HeinMach_BeforeAfter.jpg)를 참고한다. 표면 굴곡·highlight retention·역광 의상/피부·횃불 색을 직접 검수했다. source WLM/shader/전체pixel parity, Shipping FPS/전 레벨 경로 검증을 완료로 확대하지 않는다.

**Main은 아직 미반영이다.** 현재 Main editor PID16504/DevMap의 dirty map/content0을 read-only로 확인했지만 Win32 error32로 DevMap.umap 교체 접근이 거부됐다. DeliveryBlocked.json의 content_writes=0이며 요청에 따라 사용자 editor를 종료/reload/save하지 않았다. 사용자가 저장 후 종료해 lock이 풀리면 `scene_look_deliver_20261012.py install`을 실행한다. 전체 checksum preflight를 반복하며 Main이 baseline과 달라졌으면 덮어쓰지 않고 새 현재 맵에 조명 field만 이관한다. install 뒤 새 MainSaved01/SavedAudit, MainDevAfter01/MainHeinAfter01 RHI→selected493 SHA→비교 이미지/FinalVerification/ResumeState→Art MD 완료 절 순으로 재개한다. 전수 추출/재임포트/기존 Source·DLL 전달을 하지 않는다.

재사용할 기술 근거: UE5.8 `MaterialEditingLibrary.cpp:SetMaterialInstanceScalarParameterValue`는 내부에서 setter/update를 호출하지만 반환값 bResult를 true로 바꾸지 않는다. setter의 false만으로 미적용으로 판단하지 말고 readback을 확인한다. protected 입력은 public MaterialEditingLibrary 연결 API를 사용하며 source plugin AssetData가 registry에 없으면 loaded object 기반 AssetTools.duplicate_asset을 사용한다.


## 2026-10-12T14:44:13+09:00 — DevMap·HeinMach Main 반영 및 새 화면 검증 완료

앞선 Main 잠금 대기 기록을 이 완료 기록으로 대체한다. 사용자 Main 에디터가 종료된 뒤 선택493개 전부의 baseline SHA와 교체 접근을 먼저 확인했고 Main에 map2/기존 masked MI489/부모2만 전달했다. 사용자 프로세스 강제 종료·저장·reload0, Source/Config/DLL 전달0이다. MainSaved01 새 프로세스의 saved audit Success/Exit0, 기존 actor pose10032 변화0, 보호 material parameter/base overrides 예상 밖 차이0을 확인했다. MainDevAfter01(DevMap3뷰)/MainHeinAfter01(HeinMach4뷰)는 실제 D3D12 game viewport를 촬영하고 Exit0/성공/재질 compile failure0이다. 역광 캐릭터·눈/바위/횃불·음영 화면을 직접 검수했으며 실제 Shot1092×573과 요청 창1600×900은 구분한다. 현재493개 파일 SHA가 준비본과 전부 같다. 비교 이미지는 새 Main 촬영으로 갱신했다. Three small-tree raw emission off는 명시한 TEMP 보정이며 실패한 stock foliage transmission trial은 철회된 상태다. 원작 전용 shader/pixel 전체 일치와 Shipping 성능·전 경로 플레이 검증은 별도이며 완료로 확대하지 않는다. 재개 정본은 Metadata/SceneLook_20261012/FinalVerification.json과 complete ResumeState.json이다. 이미 완료된 전체 저작/추출/재임포트를 반복하지 않는다.

<!-- SceneLook_20261012_MainCompleted -->


## 2026-10-15 — HeinMach 노출·청회색 조명 후속 완료

사용자 요청에 따라 현재 Main의 원작 사진 대조 조명을 재조정했다. 이 문서의 10월12일 광원/LocalExposure 값은 해당 시점 기록이며 최신 HeinMach 값은 HEINMACH_COLOUR_VFX_20261015.md의 TEMP 표다. 현재 맵에서 새로 확인된 Arcane Kuwahara 배경/캐릭터 필터2 연결을 제거했고 노출·직접광·환경광·Fog 자체발광을 조정했다. actor10009의 배치·pose 변화0, 현재 custom blendable0/색보정 override0/LocalExposure 중립1이다. VFX는 안개 색 오염과 누락 역노출 보상을 보완했다.

Main 전달105/저장 readback/실제 native 화면·피격 회귀가 완료됐다. 최종 Main SHA, 원작 사진 출처, 구체 ROI 관측 및 완전한 shader/pixel parity 미확인 경계는 Metadata/HeinMachColourVFX_20261015/FinalVerification.json을 따른다. 완료된 과거493 package 저작/전달은 반복하지 않는다.

<!-- HeinMachColourVFX_20261015_complete -->
