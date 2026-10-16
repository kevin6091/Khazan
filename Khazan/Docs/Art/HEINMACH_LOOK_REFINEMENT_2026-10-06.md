# 2026-10-06 HeinMach 실사 중심·약한 툰 룩 조정

## 요청과 실제 적용 범위

- 최신 사용자 요청은 낮은 화질·과도한 무채색·저렴한 카툰 인상을 줄이고, 조금 실사에 가까우면서 아주 약한 툰 재질을 남기는 것이다. 앞선 원작 복원 수치와 이번 미술 조정값을 구분한다. 이번 숫자는 어시스턴트가 비교 화면을 보고 선정한 **native 임시 미술 조정값**이며 원작 shader 검증값이 아니다.
- Router → Art 상태/규칙/지식/continuity → 기존 weather 정본과 저장 metadata를 재사용했다. 새로운 FModel 추출은 필요하지 않았다.
- 숨김 background Unreal에서 기존 `/Game/Maps/L_HeinMach_Environment`와 `HeinMachWeather/MI_HM_RegionalLook_{OP,Blizzard1,Blizzard2,Boss,Cave1,Escape}`만 저장했다. 게임 패키지 변경은 7개다. 새 runtime 파일·actor·component·manager·PP pass·material graph를 추가하지 않았다.
- 기존 원작 텍스처/노멀/roughness 연결, 하늘·지역 palette/brush/노출·강설 시스템을 활용했다. C++/게임플레이 BP/프로젝트 공유 Config/StormPass/애니메이션을 이 작업에서 수정하지 않았다.
- actor 9,610개, 추가/삭제/변경 pose 0개. 적용 직전 사용자가 저장한 `PlayerStart` `(14337.811642561826,6098.6888163236235,-675.9926831942538) cm`를 보존했다. 이전 weather 기록의 `HM_Tutorial_PlayerStart_DualAxeSword`를 다시 생성하지 않는다.

## 확인한 원인과 수치 계약

표의 이전 수치는 현재 에셋/설정에서 직접 읽은 값이다. 원작 소스 전체는 `LookRestoration_20261002/SourceManifest.json`의 HeinMach profile, weather 정본에 연결된 source package/field를 사용한다. 각 field의 이전 override 상태는 이번 `LiveBefore.json`을 참고한다.

| 소유자·field | 이전 확인값 | 이번 native 선택값·단위 | 선정 이유·검증 기준 |
| --- | --- | --- | --- |
| OP PP `scene_color_tint` | `(0.488729,0.477538,0.796875,1)` | 모든 기존 PP `(0.98,0.99,1,1)`, linear RGB multiplier | 빨강·초록 감쇠와 강한 청색 편향을 줄여 눈·바위·나무 원본 색을 보이게 함. 아주 약한 겨울 냉색만 남김 |
| PP `color_saturation` | OP `.2`, 지역 `.275/.325/.3` | `.95`, RGB/W=`(.95,.95,.95,1)` | 무채색 완화; 녹색 이끼와 갈색 나무, 흰 눈을 실제 game frame에서 비교 |
| PP shadow/midtone/highlight saturation | 기존 serialized `.25/1.25/2.5` | `.92/1.04/.96` | 어두운 표면의 색 복원, 중간톤 미세 강조, 밝은 눈 과채도 억제 |
| PP contrast | OP global `1.25` 등 | global `1.02`, shadow/mid/high `1` | 윤곽이 뭉개지는 과도한 grade 대비 제거, 질감의 국소 대비 보존 |
| PP gamma/gain/offset | 지역별 원본·기존 적용값 | gamma/gain 모두 `1`, offset `0` | 중복 채널 보정 제거. 실제 각 override를 true로 명시하여 이번 계약으로 통일 |
| Film slope/toe/shoulder/black clip/white clip | source grade | `.88/.55/.26/0/.04` | UE5.8 `Scene.cpp`의 ACES 기본값을 이번 native 룩에 선택. 엔진 기본값을 원작 근거로 설명하지 않음 |
| PP film grain, motion blur amount/max, bloom | 기존 설정 | `0`, `.08/1`, `.15` | 입자 노이즈·잔상·과한 glow를 줄여 표면 무늬 보존. native 시각 선택값 |
| 지역 MI `WorldToonWeight / CharacterToonWeight` | `.08 / 1` | `.03 / .16`, 선형 혼합 계수 | DefaultLit 음영을 주로 사용하며 작은 toon 기여만 남김 |
| 지역 MI `WorldOutlineOpacity / CharacterOutlineOpacity` | `.08 / .8` | `.02 / .08` | 두꺼운 검은 외곽선 억제 |
| 지역 MI `ShadeSmoothness` | `.001` | `.12`, Lambert band의 smoothstep 폭 | 단단한 명암 경계를 부드럽게 함 |
| 지역 MI `HM_NativeShadowFillScale` | native 보정 `8` | `2`, 무차원 | 기존 큰 BaseColor floor가 평평하게 만들던 음영 완화. 시험값 `3`보다 대비가 자연스러운 `2` 선택 |
| `HM_PreviewSun` directional component `specular_scale` | source/기존 `.01` | `.15`, 무차원 | 자연스러운 재질 반사를 일부 회복. 시험값 `.6`의 젖은 듯한 과도한 광택은 제외 |

- outdoor EV100 `8`, Cave EV100 `4`, shadow radiance `256/16`, source shadow brightness/ambient·sky/cloud/star/nebula 값·7 BSP priority/blend/geometry 및 Cave1 user flag는 유지했다. exposure·radiance는 앞선 native 계산 계약이며 원작 EV 복원값이 아니다.
- 함수: `Scripts/Art/heinmach_weather_look.py`의 `NATIVE`, `REALISM_GRADE`, `realism_settings`, `refine_saved_look`. 사용자가 재조정할 위치를 이 기존 owner에 모았다.

## 화질 설정과 적용 조건

- 기존 live editor는 Medium, 내부 화면 비율 `71`, texture mip bias `1`, texture pool `600 MB`, TSR method `4`/AA quality `1`이었다. 낮은 내부 해상도와 낮은 texture 품질도 흐린 인상의 원인이다.
- 현재 local preview: 내부 해상도 `100%`, AA `3`/TSR history `200%`, texture/PP/shadow/GI/reflection/effects/view distance/foliage/shading `2`, temporal quality `2`, anisotropy `8`, mip bias `0`, pool `1600 MB`, sharpen `.25`. GPU와 출력 조건을 고려한 native 품질 선택이며 원작 게임 설정값이 아니다.
- `Scalability 2`와 `GameUserSettings.save_settings`로 local editor scalability 저장을 요청하고 추가 console 값을 적용했다. console-only extras는 **현재 세션 override**다. 재시작 후 모든 extras의 유지가 검증됐다고 기록하지 않는다. 프로젝트 `Config/DefaultEngine.ini`에 강제로 넣지 않았다.
- 재적용: Editor Python에서 `runpy.run_path('Scripts/Art/heinmach_weather_look.py'의 절대 경로)`로 config를 읽은 뒤 `QUALITY_PREVIEW`의 각 command를 실행한다. `sg.ResolutionQuality`와 `r.ScreenPercentage` 모두 `100`으로 맞춘다. PIE 화면 비율의 editor override는 `r.Editor.Viewport.OverridePIEScreenPercentage 0`이다.
- 정정: UE5.8에는 `r.PostProcessAAQuality`가 없다. 미지원 query가 반환한 `0`은 AA 꺼짐의 증거가 아니다. 실제 이전 상태는 TSR/Medium이었다. `QualityCVarCorrection.json`이 정정 근거다. 또한 GI quality 1도 UE5.8에서 Lumen IrradianceVolume 경로를 사용한다; GI 꺼짐으로 설명하지 않는다.

## 검증과 자료

- metadata: `Content/_Art/Player/Environment/Rendering/Metadata/HeinMachLookRefinement_20261006`.
- `Applied.json`: 7 package byte backup, 실제 native 값, 8 PP/6 MI, sun 값, 적용 직전 모든 actor pose 유지 assertion. `BeforeApplyActorPoses.json`은 이번 사용자 저장 상태 기준이며 이전 전체 importer snapshot으로 되돌리지 않는다.
- `FreshSavedSceneAudit.json`: 새 NullRHI 프로세스에서 9,610→9,610, pose 변경/추가/삭제 0, 현재 PlayerStart, 8 PP grade override, 6 MI, pre-exposure, sky stencil252, snow 2 GPU handle/alpha/DOF/bounds 계약 통과.
- `RenderGraphVerification.json`: real DX12/SM6 process에서 주요 재질 4개 compile errors 0. pixel instructions는 PP `110`, sky `198`, snow/dust 각 `107`로 기존 graph와 같다. shader 노드/샘플 증가 없이 parameter/grade를 조정했다.
- `VisualComparison.json`: 고정 카메라에서 기존 High 룩과 Neutral/Fill3 trial 비교. camera의 hardware 입력을 차단하고 모든 trial을 saved MIC에서 파생했다.
- `SavedGameVerification.json`: **MID 대체 없는 저장본 actual standalone game**. 현재 사용자 PlayerStart/기존 entry 고정 시점/하늘/동굴 PNG 4개, flakes `8,718`+dust `2,472` 관측, error 없음. final PNG는 `Saved/ImportReports/HeinMachLookRefinement_20261006/Saved/`다.
- 초기 hardware mouse drift와 MID를 다음 MID의 parent로 사용한 실패 trial은 `CameraDrift`, `TintedTrial`, `NestedMIDTrial`에 보존했으며 최종 화면 근거로 쓰지 않는다. UE5.8 `MaterialInstance.cpp`는 MID parent를 거부한다.
- `PerformanceVerification.json`: RTX3060Ti, DX12/SM6, 1280×720, current High/Epic AA preset, saved look, fixed entry 100 frames, Development offscreen, `t.MaxFPS=30`, 이 sample 동안 interactive editor 종료. GPU Niagara simulation median/P95 `.01755/.0226 ms`, translucency `.1179/.1357 ms`. 전체 frame time median/P95 `44.4977/46.4947 ms`이므로 전 레벨 60 FPS/전체 게임 성능 개선을 주장하지 않는다. 이번 작업은 snow system 자체를 수정하지 않았으며 이전 Medium/동시 editor sample과 최적화 전후로 비교하지 않는다.
- 원작 proprietary BBQ shader 완전 이식이나 원작과의 controlled 외형 동일 판정은 아니다. 이전 weather 정본의 미복원 계약은 그대로 남는다.

## 저장 잠금·editor 충돌·복구 기록

- 최초 background save는 Windows Error32로 OP MI 저장 실패, stage marker 실패. 7 파일이 byte backup과 동일함을 확인했다.
- 파일 잠금 해제를 위해 assistant가 live editor에서 `DEBUG RESETLOADERS`를 호출한 직후 PID9596이 access violation `0x28`로 종료됐다. `Saved/Logs/HeinMach_EditorPreview_20261006.log`의 command/critical error와 `Saved/Crashes/UECC-Windows-9556BEC84DB2BCFB5D0D3582E367AD3F_0003`가 근거다. 사용자 종료나 background process 실패로 바꿔 기록하지 않는다. 사용자에게 원인과 사과를 알렸다.
- 명령 직전 dirty map/content 0개였다. 저장 데이터는 보존됐지만 실행 중 PIE 세션은 종료됐으며 runtime 진행 상태의 동일 복구를 주장하지 않는다. **live editor에서 전역 DEBUG RESETLOADERS를 다시 사용하지 않는다.**
- 종료 후 background authoring 재시도 exit0/marker, fresh audit·real-RHI compile·saved-game capture 통과. 기존 map/6 MI backup은 `Saved/ArtBackups/HeinMachLookRefinement_20261006/Content`다.
- 검증 후 interactive PID25196으로 최신 HeinMach를 다시 열고 이전 editor viewport pose `(10494.534774043635,-6517.085901376141,-5174.297077025872) cm`, rot `(-.26692055910825935,177.08372508734465,0)°`를 복구했다. 사용자가 PIE를 다시 시작했으며 해당 Play를 중단하지 않았다.
- `RecoveredEditorQuality.json`의 현재 supported CVar·dirty0 확인. live screenshot `Saved/Screenshots/WindowsEditor/RiderMCP/20261006-052314_viewport.png`에서 실제 이동 중 동굴 재질·조명을 확인했다.

## 후속 재개

1. Router → Art 최신 상태/continuity → 이 정본과 `Applied/FreshSavedSceneAudit/SavedGameVerification/RecoveredEditorQuality`부터 확인한다.
2. user dirty/PIE와 현재 디스크 변경을 먼저 확인한다. 기존 byte backup으로 현재 사용자 편집을 덮어쓰지 않는다. 파일 잠금이 있으면 live 전역 loader reset을 우회책으로 사용하지 않는다.
3. 이번 룩의 작은 추가 조정은 기존 `NATIVE/REALISM_GRADE`, 6 MI, 해당 8 PP/sun만 수정한다. 전체 weather importer/brush 재생성/geometry 재임포트를 반복하지 않는다.
4. authoring: 숨김 runner `look --refine`; 검증 `audit` → `render_probe --render` → `refine_capture --render --game --saved`. 기존 사용자 editor가 해당 package를 잡고 있다면 먼저 정상적인 clean-package 해제/재열람 절차를 준비한다.
5. 현행 map SHA는 이번 fresh audit 기준 `db16f4674ef5f32f898c164446e2c3e15e8be1e2f183d9c3a67694c65f2d172d`. 이후 사용자가 저장한 결과가 바뀌면 이 hash를 복구 지시로 사용하지 않는다.

## 2026-10-06 최종 전달 점검

- `DeliveryVerification.json` passed: 현재 map SHA 동일, 기존 MI 6개만 변경, 전용 asset 15개 중 나머지 9개는 이전 Delivery SHA 동일, 백업 7개 SHA 확인. parent graph/sky/snow/VF/texture package를 이 조정에서 저장하지 않았다.
- 마지막 `FinalLiveEditorVerification.json`은 PID25196 **Idle**, 최신 HeinMach/actor9,610/dirty map·content0, resolution100/AA3/texture·GI·shadow2 확인이다. 사용자가 복구된 PIE를 종료했으며 추가 Play를 시작하거나 camera를 다시 움직이지 않았다. 앞 절의 Play는 그 시점의 관측 기록이다.
- motion blur amount `.08`은 무차원이며 `motion_blur_max=1`은 화면 폭의 `1%`다. grade RGB/contrast/gain/film 및 sharpen 수치는 무차원 native control이다. `1600` texture pool은 MB, mip bias는 mip level, resolution/history는 percentage다.

## 2026-10-06 마지막 live dirty 관측 정정

- 직전 점검은 Idle/dirty0이었지만 마지막 `FinalLiveEditorVerification.json` 작성 시에는 HeinMach map dirty1/content0으로 바뀌었다. 이 보고서의 실제 배열이 앞 절의 dirty0 요약보다 우선한다. 새 dirty 원인은 확정하지 않았으며 추가 map reload/Save All/discard를 하지 않았다. 9,610 actors와 품질 설정은 유지됐다.
- 이번 저장된 미술 결과의 Delivery/audit는 통과한 상태다. 새 live 미저장 변경은 그대로 보존했으며 이 상태를 저장된 디스크 결과와 동일하다고 주장하지 않는다. 다음 작업은 현재 dirty 내용부터 확인한다.

## 2026-10-06 후속 원작 사진 비교 — 현행값 대체 범위

최신 사용자 방향은 [HEINMACH_REFERENCE_MATCH_2026-10-06.md](HEINMACH_REFERENCE_MATCH_2026-10-06.md)의 원작 사진 기반 재현이다. 메인12package에 지역 tint/saturation/toon/outline/sun·haze/priority 및 PP 순서/snow budget·depth-velocity를 실제 반영했다. 본서의 실사 중심 `.95` saturation/`.16` character toon/`.08` outline/`.15` sun spec/`.08` motion blur는 새 저장 범위에서 대체된다. actor9,610/현재 사용자Start와 pose 차이0. 이번12package/메인 game/fresh audit/성능과 미완료 원작 계약은 새 정본과 `Rendering/Metadata/HeinMachReference_20261006`을 먼저 확인한다. 본서의 이전 backup으로 현재 맵을 되돌리지 않는다.

## 2026-10-06 사용자 품질 재검토 — 외형 판정과 원작 셰이더 재현 한계

- 이번 요청은 현재 외형 평가와 셰이더 재현 한계 설명이다. 게임 C++/BP/맵/재질·품질 설정을 수정하거나 저장·재로드하지 않았다. PID25196/Idle, HeinMach dirty map1/content0을 읽기 전용으로 확인했다. 현재 지원 CVar는 screen percentage100/TSR method4/AA quality3/texture quality2다.
- 실제 현재 editor screenshot `Saved/Screenshots/WindowsEditor/RiderMCP/20261006-053750_viewport.png`와 MID 없는 저장본 `Saved/ImportReports/HeinMachLookRefinement_20261006/Saved/SavedEntry.png`, `OpenSky.png`를 다시 봤다. 색·선명도 개선과 별개로 바위의 강한 밝은 반사/어두운 면 대비, 눈송이의 납작한 인상이 남는다. 이는 화면에 대한 미술 평가이며 roughness/normal 오류를 새로 입증한 결과가 아니다. 같은 build·같은 카메라의 원작 비교가 없으므로 원작 외형 일치/정량 일치율을 판정하지 않는다.
- 원작 직접 근거: `Saved/Extracted/LookRestoration_20261002/Source/BBQ/Content/_Kazan_/BaseMaterials/Character/M_AKCartoonCharacter.json`, `Properties.ShadingModel=MSM_BBQCartoon`, `ShadingModels.ShadingModelField=8192`, `MaterialAttributes.Expression=null`; parameter 출처는 `CachedExpressionData.Parameters`와 기존 `SourceManifest.json:toon_master`다. 이 field/null은 확보한 export의 상태이며 게임 전체 shader binary/source가 절대 존재하지 않는다는 증거로 확대하지 않는다.
- 로컬 엔진 근거: UE5.8 `Engine/Source/Runtime/Engine/Classes/Engine/EngineTypes.h:EMaterialShadingModel`에는 BBQ 전용 모델이 없다. `Engine/Source/Runtime/Engine/Public/Materials/Material.h:UMaterialEditorOnlyData.ExpressionCollection` 및 editor-only `MaterialGraph`는 편집용 그래프와 runtime 자료가 다름을 보여 준다. 파라미터 이름/값 확보는 원작 BRDF·shadow·GI 계산 구현 확보와 다르다.
- 현행 대체식 확인: `Scripts/Art/restore_level_look.py:TOON_CODE`는 이미 조명된 SceneColor에 normal/light direction 기반 명암 비율과 윤곽선을 적용한다. `Scripts/Art/heinmach_weather_look.py:region_sky_material`은 BaseColor 기반 floor와 기존 SceneColor의 max를 취한다. 원작 direct/indirect light 분리나 BBQ renderer를 이식한 식이 아니며, shaded surface를 평평하게 만드는 가능성은 남는다. 현재 화면의 모든 문제를 source 부재만으로 설명하지 않는다.
- FModel은 cooked package 탐색·자료 추출 도구다([공식 저장소](https://github.com/4sval/FModel)); cooked Material은 편집용 그래프를 열 수 있는 원본 프로젝트와 다르다([Epic cooked content 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-cooked-content-in-the-unreal-engine)). postprocess의 SceneColor/GBuffer 계약은 [Epic 문서](https://dev.epicgames.com/documentation/unreal-engine/post-process-materials-in-unreal-engine?lang=en-US)를 확인했다. 이번에 원작 compiled shader library를 추출·역분석하거나 전용 엔진 renderer를 확보하지 않았다. 따라서 '원작 셰이더 재현 불가능'이 아니라 '현재 자료와 구현으로 동일 계산을 이식했다고 말할 근거가 부족'이 정확하다.
- 다음 검토 우선순위는 원작 동일 시점·지역·날씨·노출의 화면 비교, 현행 바위/눈 표면의 반사·normal·쌓임 blend와 조명/그림자 보정 분리 검수, 필요한 master/function/shader 자료의 표적 조사다. 현재 실사 중심 grade는 앞선 사용자 미술 요청에 대한 native 선택이며 원작 값 그대로의 복원과 구분한다. 이 순서는 설명/제안이고 새 에셋 적용 완료 기록이 아니다.
