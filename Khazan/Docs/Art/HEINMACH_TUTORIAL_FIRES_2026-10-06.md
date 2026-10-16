# HeinMach 튜토리얼 횃불·화로·조명 복원

## 2026-10-06 — 요청 범위와 원본

사용자 직접 요청으로 원작의 횃불·화톳불 조명과 파티클을 추출해 기존 HeinMach 맵에 배치한다. 튜토리얼 범위 확인 질문에는 답변이 없어, 사전에 설명한 **HeinMach 전체 플레이 구역**을 기준으로 진행했다. 컷신 전용 효과는 제외한다. 게임 C++/BP와 Chaos 파괴·사운드 연결은 이번 미술 배치 작업에서 수정하지 않는다.

첫 조회 자료:

- `Content/_Art/Player/Environment/HeinMach/Metadata/HeinMach_EnvironmentPlacements.json`
- `Saved/Extracted/HeinMachTutorialFires_20261006/{FireActorCandidates,Components,DestructibleFireSpawners,DynamicFixtures,AssetManifest}.json`
- 원작 level JSON: `C:/Users/user/Desktop/카잔/Exports/BBQ/Content/_Kazan_/Level/HeinMach`.
- 원본 raw·JSON·교환 payload: `Saved/Extracted/HeinMachTutorialFires_20261006`.
- 지속 metadata: `Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006`.

FModel 설정을 사용하는 기존 EnemyExtractor로 필요한 패키지만 추출했다. 이 추출본은 cooked UE4.27 자료이며 원작의 정확한 build 번호는 미식별이다. 시각 참조 closure **284개**, raw/metadata/payload 추출 실패 **0**이다. 동일 source package의 기존 texture·vector field·MPC만 재사용하고, 화로 재질과 파티클은 이번 작업 소유 폴더에 분리했다.

## 2026-10-06 — 배치 계약

원작 후보 80개 중 컷신 3개를 제외했다. 플레이 구역의 불꽃 기구는 **72곳**이고, 별도의 촛대 5개에는 원본 파티클 컴포넌트가 없어 기존 정적 외형을 유지했다.

| 대상 | 원본 수 | 이번 처리 |
|---|---:|---|
| 일반 횃불·등불·화로 | 37 | 기존 외형 유지, 원본 자식 FX/조명 추가. 금속 등불 24곳 포함 |
| 파괴 가능 화로 spawner | 35 | 원본 `StaticMeshArray[0]`의 파괴 전 외형과 자식 FX/조명 복원 |
| 중심 불꽃 | 72 | 원작 Cascade template와 instance parameter 사용 |
| 별도 FireDust | 23 | 원본 등불 자식 효과 추가 |
| 켜진 자식 PointLight | 100 | 원본 위치·색·반경·IES·거리 설정 사용 |
| 꺼진 자식 조명 | 44 | `Intensity=0` 또는 `bAffectsWorld=false`라 켜지 않음 |
| ground burn decal | 28 | 원본 크기와 자식 transform 사용 |

기존 9,610 actors와 89개 독립 source lights를 보존하고 **258 actors**를 추가한다: FX 95 + PointLight 100 + 화로 외형 35 + decal 28. 총 **9,868 actors**다. 기존 actor pose 차이는 `1e-6` 이하, 기존 조명 intensity/radius 차이 0이다. 사용자가 옮긴 PlayerStart `(12022.196341630144,13909.267886166936,223.7105706322176)cm`를 유지한다.

일반 BP의 local → attachment parent chain → 현재 native root actor transform 순서로 합성한다. 기존 root가 사용자에 의해 이동한 경우 현재 root를 따른다. spawner는 원작 actor transform과 상속된 component override를 사용한다. 각 actor tag에 정확한 source level/index/component key를 남겼다. 메인 맵은 `/Game/Maps/L_HeinMach_Environment`, Outliner 폴더는 `HeinMach/Reconstructed/TutorialFires/{Particles,Lights,Fixtures,GroundBurn}`이다.

## 2026-10-06 — 리소스와 원본/계산/native 구분

복원한 3종은 다음 원본 package다.

- `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Level/FP_LVL_WBP_LightObj_001_FIRE_medium`
- `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Level/FP_LVL_WBP_LightObj_001_fire_small`
- `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Level/BBQ_Level/FP_FireDust_001`

원본 emitter 17개/LOD 및 cooked distribution을 유지한다. 원본에서 null인 distribution에는 기존 검증된 importer를 재사용해 editor distribution **273개**를 유도했다. 이 값은 원작 editor key 직접 복원이 아니라 원본 table의 operation/stride/time bias/time scale/lock 조건으로부터 계산한 값이다. core의 `Lifetime.Table.Values=[0]`, `EmitterDuration=.1s`, `EmitterLoops=1`, burst count 1/time 0도 유지한다. UE5 Lifetime.cpp 경로에서 수명 0은 무한 수명이므로 편의상 무한 반복 burst로 바꾸지 않았다.

이번 소유 native package **72개**: Texture2D 28, TextureLightProfile 5, source 기반 master material 7, source MI 17, StaticMesh 4, Cascade 3, native flicker master 1/MI 7이다. 기존 exact-source 리소스 70개와 Engine 기본 리소스를 참조한다. MaterialFunction 등 stripped graph는 원본만 보존하며 빈 native 그래프를 만들어 복원 완료로 세지 않는다. 최종 지원 여부는 `NativeAssetManifest`/`SourceOnlyAssets`를 기준으로 한다.

| 값 | 출처 상태와 적용 조건 |
|---|---|
| 컴포넌트 위치·회전·scale, 색, 반경, 원본 instance parameter | `Components`의 `property_origins`/`lineage`, `DynamicFixtures`의 `cdo_origins`/개별 `Value`와 `bIsDefaultValue`가 직접 근거 |
| spawner parameter mapping | 원본 CDO/override를 source distribution parameter에 대응한 native adapter. stripped BP runtime 함수의 실행을 확인한 것은 아님 |
| IES 5개 | 원본 inline `PF_FloatRGBA`의 R half bits, 원본 brightness/multiplier 사용. UE IESLoader의 `V=x*180/256`, `H=y*360/256`에 맞춰 LM-63 계산. 원본 LM-63 파일 직접 추출은 아님 |
| light intensity ×750, Unitless/noninverse | 기존 HeinMach native 조명 adapter 재사용. 원작 xxPointLight의 단위/constructor 기본값은 미확인. 원작 lumens라고 주장하지 않음 |
| 미직렬화 조명의 그림자 false | 새 native 조명의 비용을 제한하기 위한 명시된 native 선택. 원작 class default 직접 확인값이 아님. 기존 독립 89 lights는 그대로 유지 |
| flicker amplitude `.08` | 임시 native 값. source AnimationSpeed 사용, 원작 animation intensity 함수는 미복원. `NativeFlickerAmplitude`로 조절 가능 |
| FireRadianceGain/NativeFireReferenceGain 각 `256` | 기존 outdoor HDR adapter를 기준으로 선택한 native 값. 원작 emissive radiance 미확인. 두 값으로 정규화한 뒤 EyeAdaptationInverse를 사용해 EV4 동굴에서 과노출을 줄임 |
| smoke opacity R | source DXT1 payload의 A가 전부 255임을 실제 PNG readback으로 확인. grayscale R density를 사용한 native 복원. 원작 stripped shader 식을 직접 읽은 것은 아님 |
| burn footprint | source RGB packed mask/Color/채널 strength/FadePower/Fadeout를 사용한 native 식. 원작 panner/dissolve 본문은 미복원 |

Packed world surface는 기존 Art 계약인 AO R/Roughness G/Metal B와 source normal/base textures를 사용한다. 새 flame/ember 재질은 BeforeDOF, ResponsiveAA=true, translucent velocity=false로 기존 HeinMach의 시간축 처리와 맞춘다. 기존 눈·sky·후처리·terrain material을 수정하지 않는다.

## 2026-10-06 — 실제 재생에서 찾은 이관 문제

처음 저장·참조·compile 검사는 통과했지만 actual game에서 모든 새 Cascade 컴포넌트가 비활성/particle count 0이었다. source `ParticleSpriteEmitter.Properties.DetailModeBitmask=7`은 UE4의 Low/Medium/High를 포함하며, 현재 UE5 `r.DetailMode=3` Epic bit는 포함하지 않는다. UE5.8 `ParticleSystemComponent.cpp::InitParticles`는 이 bit로 instance 생성을 차단한다. 숨겨진 probe에서 DetailMode 2로만 바꾸자 같은 template가 21 particles/active=true가 되어 원인을 확인했다.

`ParticleEmitter.cpp::Serialize`의 기존 `AddEpicDetailMode` migration과 같은 High→Epic 변환을 이번 17개 emitter에 적용했다: native bitmask **15**. 새 UE5 패키지로 생성했으므로 자동 legacy migration을 기대할 수 없었다. 프로젝트 전체 품질을 내리지 않았다. fresh Epic probe에서 **95/95 active**, core system이 180 frames 동안 재생되는 것을 확인했다.

또한 SETNOPEC가 원작 `ParamModes[1]`/`[2]`를 적용하지 않던 문제를 complete fixed array setter로 교정했다. core readback은 `[DPM_Abs,DPM_Abs,DPM_Direct]`로 일치한다. 원본 값 교정이며 새 튜닝값이 아니다.

source smoke 두 atlas는 A min/max `255/255`다. A-only opacity가 회색 사각형을 만들었으므로 R density로 변경했다. actual CaveFire/EscapeFire 재검수에서 사각형이 사라졌다. 화염에는 native 노출 대응을 추가해 동굴의 날아가는 흰색 중심을 줄였다. 근접/광각 QA camera 설정은 원작 카메라 수치가 아니며 맵에 저장하지 않는다.

## 2026-10-06 — 격리 작업과 검증 단계

`Saved/ArtStaging/HeinMachTutorialFires_20261006`에서 hidden UE만 사용한다. mutable Maps/new fire asset/metadata branch는 실제 복사이고 다른 Content는 읽기 전용 junction이다. runtime 새 파일/class/component/manager는 **0**이다. `Scripts/Art/heinmach_tutorial_fires_*`는 offline 추출·authoring·검수용이다.

- `StageSetup`/`BaselineScene`: main map 초기 SHA와 9,610 pose/89 light 보존 기준.
- `NativeImport`/`Recovery/Cascade`/`CascadeCompatibility`: 실제 이관과 editor distribution 계산/호환 변환.
- `Placement`/`StageSavedSceneAudit`: 9,868 actors, 기존 pose/PlayerStart/light·새 source transform/parameters 검사.
- `ShaderVerification`: 실제 DX12 shader errors와 pixel/vertex instruction 수. null-RHI 검사와 구분한다.
- `Preview/Playback`/`Probe/Runtime`: 실제 game viewport 6시점/두 프레임씩, live 활성/particle count. occluded 중간 카메라 결과를 최종 시각 근거로 쓰지 않는다.
- `PerformanceCapture`/`PerformanceVerification`: ON/OFF/ON warmup 200 frames + 200 samples. Development 1280×720 TSR, 사용자 editor 동시 실행. 전체 60FPS 보장과 원작 동일 판정을 하지 않는다.

메인 적용 여부와 마지막 검증은 아래 후속 완료 절 및 `DeliveryVerification`이 정본이다. 처음의 inactive probe/채널 오류/중간 API 실패는 성공 근거로 사용하지 않는다. 특히 원본 shader body, BP runtime light 함수, Chaos 파괴/사운드 및 원작의 같은 build·camera·weather 비교는 아직 완전 복원이 아니다.

정확한 재개: Router → Art 최신 상태/이 문서/continuity → 현재 SHA/새 backup → 해당 원본/metadata만 표적 확인 → 기존 task owner의 작은 수정 → background real RHI/fresh saved load/game 화면 검수. full extractor/importer나 옛 HeinMach 전체 rebuild를 반복하지 않는다. live `DEBUG RESETLOADERS`/SaveAll/discard/종료는 사용하지 않는다.

## 2026-10-06 — 메인 배치 반영 및 최종 검증 완료

원작 자료에 있는 플레이 구역의 불꽃 기구 72곳을 `/Game/Maps/L_HeinMach_Environment`에 반영했다. 불꽃·연기·불씨 PSC 95개, 켜진 자식 PointLight 100개, 파괴 전 화로 외형 35개, ground burn decal 28개를 추가했다. 기존 일반 기구 37개를 중복 생성하지 않았으며 꺼진 자식 조명 44개, 파티클 없는 촛불 5개, cinematic 전용 3개는 앞 절의 분류를 유지했다. 새 actor 258개/총 actor 9,868개다.

최종 파일 기준 **72개 native asset + map 1개**를 선택 설치했다. 앞 절의 임시 집계 중 Texture2D 28개와 flicker MI 7개/Engine 2개는 다음 실제 집계로 정정한다. 새 native는 Texture2D **29**, TextureLightProfile 5, source 기반 Material 7, source MI 17, StaticMesh 4, Cascade 3, native flicker Material 1/MI **6**이다. source closure 284개는 task native **65**, exact-source 기존 asset **70**, Engine DefaultParticle **1**, source-only **148**(MaterialFunction 141/RT 5/atlas 1/curve 1)로 구분했다. Engine 경로라는 이유만으로 stripped 함수 55개를 복원된 Engine asset으로 잘못 분류하던 준비 manifest도 수정했다. `NativeAssetManifest`와 `SourceOnlyAssets`가 최종 지원 범위 정본이다.

- `prepare`/`install`/`verify` 모두 성공. 반영 직전 map SHA `9da24fa9daffe01aa5a5ed581d3b4ac6466592a92e1638b0c0f8b530d58ea251`를 확인했고 원본 byte backup은 `Saved/ArtBackups/HeinMachTutorialFires_20261006/Content/Maps/L_HeinMach_Environment.umap`에 보존했다. 설치 후 73개 SHA와 원본 backup SHA 검증 passed. 이 작업 저장본의 map SHA는 `f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442`다.
- 새 메인 process `audit --main` exit0/marker/`MainSavedSceneAudit.passed=true`. 기존 9,610 actor pose·PlayerStart 보존, 기존 89 source lights의 intensity/radius 차이 0. 새로운 source transform/instance parameter/IES/material slot/template·17 emitter/Epic bit 검사 통과. DevMap/StormPass map SHA도 반영 전과 동일했다.
- 최종 source/native master 8개 actual DX12 SM6 recompile errors0 및 양수 shader instruction을 확인했다. 이후 메인 actual game `capture --main` exit0/marker/no default-material fallback. `MainPreview/Playback.passed=true`, 6시점 × 60/90 frame의 PNG 12장과 각 지점 live active/particle>0 확인. 최종 CaveFire/EscapeFire의 연기 사각형이 해소됐고 불꽃·불씨가 재생된다. StoneBrazier 근접 QA에는 기존 foliage/기구가 일부 시야를 가리는 문제가 남아 있으며 기존 geometry를 임의 이동하지 않았다.
- 최종 ON/OFF/ON 성능 CSV는 각 200 warmup/200 samples, Development/DX12/SM6, RTX3060Ti/Ryzen5600X, 1280×720 TSR, 사용자 editor 동시 실행이다. probe 안에서만 다른 Pawn/AI tick을 고정했다. GameThread Effects median `.3123/.13155/.29275ms`, 두 ON 평균 minus OFF **+.170975ms**; CascadeWorldManager 같은 계산 **+.126325ms**는 이 조건에서의 관측값이다. GPU shadow/base/TSR와 전체 frame 편차가 커 **GPU 추가 비용을 확정할 수 없다**. `PerformanceVerification.gpu_cost_conclusive=false`; 음수 GPU 차이를 개선으로 해석하지 않으며 전체 60FPS 보장을 하지 않는다. 소스 draw/fade 거리 및 새 조명의 native shadow 제한을 사용했다.
- 최종 interactive read-only 확인은 PID27916, `/Game/Maps/DevMap.DevMap`, dirty map/content0. 중간 StormPass 관측 뒤 실제 world가 DevMap으로 바뀐 것을 확인했으며 assistant가 맵을 전환한 것은 아니다. 저장·재로드·camera·PIE·종료 제어 없이 유지했다. 작업 전용 hidden process들은 정상 종료했다.

지속 metadata는 `Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006`, 검수 PNG/log/CSV 요약은 `Saved/ImportReports/HeinMachTutorialFires_20261006`이다. Outliner `HeinMach/Reconstructed/TutorialFires`에서 기구/입자/조명/decal을 찾는다. 메인 배치와 재생 검증은 완료했고 원작 전용 shader body·BP light animation 함수·Chaos 파괴/소화 상호작용 및 동일 build/camera의 픽셀 단위 원작 일치는 미복원/미검증이다.

후속 작업은 최신 메인에서 새 snapshot/backup을 만들고 source component key/tag로 해당 actor만 수정한다. 이번 `prepare→install`은 완료한 반영이므로 재실행하지 않는다. 이후 snow/다른 작업이 메인 맵을 저장하면 이 작업의 map SHA는 당시 snapshot이며 최신 전체 맵의 정본으로 사용하지 않는다. 이전 stage의 전체 맵을 다시 복사하면 후속 사용자/다른 작업 변경이 손실되므로 현재 맵에 작은 diff를 적용한다.
