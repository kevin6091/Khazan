# HeinMach 색감·혈흔·전투 VFX 색 보존

## 2026-10-15 — 메인 적용, 최종 RHI 검증 진행

사용자 요청은 원작 사진에 가까운 낮은 노출·청회색 장면, 더 빨간 혈흔, 현재 브루탈 혈액 파티클의 플레이어/몬스터 피격 재사용, DevMap과 HeinMach의 VFX 색 유지다. Router 이후 기존 SceneLook/clean presentation/혈액 정본과 저장 metadata에서 시작했다. 원작 사진은 Docs/Art의 HeinMach 원작 사진5장 및 Saved/ImportReports/HeinMachReference_20261006/OriginalReferences.jpg를 재사용했다. 원작 조명·셰이더의 직접 일치값으로 튜닝값을 표현하지 않는다.

실제 시작 맵은 2026-10-12 문서의 custom blendable0과 달랐다. Art_NaturalLighting_HeinMach에 /Game/_RND_ArcanePP/MI_PP_Arcane_BG_V6(Weight .4), MI_PP_Arcane_CH_V3(Weight1)이 추가돼 있었다. 2026-10-15 metadata의 NativeLookRetune06/T3D는 Kuwahara 이웃 평균화/variance 선택과 stencil2 캐릭터 분기를 보여준다. 연결 두 개만 제외했고 실험용 재질 에셋은 보존했다. 컬러 LUT/전체·명암대별 saturation/gain/contrast/gamma/offset override는 없으며 두 맵 LocalExposure Highlight/ShadowContrastScale은 엔진 중립1이다. 공통 film tone mapping, AA, 물리 광원은 남는다.

### 실제 적용한 값과 출처

| 소유자·필드 | 최종 값 | 출처·목적 |
| --- | --- | --- |
| HeinMach HM_PreviewSun Intensity | 1800 lux | TEMP. 시작2500 lux의 강한 직접광을 낮춤 |
| HM_PreviewSun LightColor | sRGB8 R205/G225/B255 | TEMP. 약한 차가운 직접광. Python FColor는 이름 인자로 채널을 지정 |
| HM_PreviewSkyLight Intensity | 8 | TEMP. 환경광 배율. 바위·캐릭터의 그늘을 읽게 함 |
| HM_PreviewSkyLight LightColor | sRGB8 R195/G218/B255 | TEMP. 청회색 환경광 |
| Art_NaturalLighting_HeinMach AutoExposureBias | -1.1 EV | TEMP. 시작-.6 EV보다 낮은 노출. 기존 histogram/range 유지 |
| HM_PreviewVolumetricFog VolumetricFogEmissive | linear RGB .025/.04/.06 | TEMP. 시작 .145833/.056945/0의 주황 자체발광을 약한 차가운 값으로 교정. density/falloff/start/기하 유지 |
| M_Monster_HitBloodGround BloodColor | linear RGB .08/.0016/.003 | TEMP. 시작 .012/.00025/.00075의 거의 검정색을 진한 빨강으로 교정 |
| 같은 재질 BloodRoughness/Metallic | .38/0 | TEMP. 검게 꺼지는 금속 반응을 없애고 젖은 비금속 표면 사용 |
| BloodShadowReadabilityEmission | .04 | TEMP. BloodColor에 곱한 작은 역노출 발광. 첫 .3 후보는 눈밭에서 너무 밝아 제외 |
| 현재 참조 Surface VFX root95 bUseTranslucencyVertexFog | false | 엔진 기술 설정. 씬 안개로 이펙트 색이 물들지 않도록 함. depth test/alpha/blend/굴절/기존 파라미터 보존 |
| 발광 출력 EyeAdaptationInverse Alpha | 1 | 엔진 전노출 보상. 원작 gameplay 값 아님. 누락된 기존 출력만 감싸며 색 계산은 보존 |

현재 브루탈 success-only 창에서 실제 사용하는 /Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub를 기존 HitReactions.ImpactEffect에 그대로 연결했다. Player1/Monster6 Definition의 나머지 HitReaction 설정은 동일하다. PS를 복제하거나 count/lifetime/curve/notify clock을 바꾸지 않았다. 기존 몬스터 물리 혈액·바닥 얼룩을 유지한다. 수신자 캡슐 표면 발생 위치와 승인 피격/가드 경계의 runtime 기록은 Engineering continuity 및 COMBAT_PRESENTATION_FOLLOWUP_20261011.md에 분리한다.

MainDelivery01/Receipt.json은 105 package의 시작 Main SHA 비교·백업·동일 SHA 전달을 기록한다. 구성은 map2/Definition7/현재 Surface VFX root95/혈흔 Ground1이다. 병행 작업의 몬스터 BP/Guard BP를 전달 대상으로 삼지 않았다. 새 SnowFlipbook9x9 root에는 그 작업의 기존 graph/MI 연결을 보존하고 안개 옵션만 바꿨다. 새 runtime class/component/manager/texture/particle asset은 없다.

### 검증과 한계

MainSaved01/SavedVerification.json: 현재 map PP custom blendable0, 색보정 override0, Definition7 정확한 PS 연결 및 다른 설정 보존, Surface root95 안개 차단·깊이/파라미터 보존, PS321 SHA 유지가 통과했다. 동일 이름 Param 노드가 여러 개이므로 파라미터를 이름 dict가 아니라 class/name/value 전체 multiset으로 비교한다. 기술적 hidden/굴절의 검정 출력은 발광 보상과 구분한다.

NativeHein05/Capture.json은 실제 game Shot 네 시야이며 998×426이다. 요청 해상도1600×900으로 오인하지 않는다. 시작과 비교해 배치10009 actor/pose 변화0, 정적 ReferenceStart 영역의 RGB 평균은 171.06/174.42/174.58→154.71/164.84/174.40, RGB 모두244 초과 픽셀은5.35%→2.88%다. 이는 특정 ROI 관측이며 전체 장면/원작 일치 수치가 아니다. Player 기본 시야에는 큰 식생 가림이 있어 그 사진을 얼굴/전투 검증 근거로 쓰지 않는다.

AllVFXDev03/AllVFXHein03은 현재 참조321 system을 각각 .2s game age로 재생한 PNG다. ColourComparisonFinal은275개 양쪽 가시 신호, 7개의 에너지 차이 검토 항목을 기록한다. 6개는 무작위 크기·회전·분포 변화이며 hue 차이는 작다. PP_BlackBlood_Die_Loop의 한 쌍은 editor viewport가 촬영돼 색 검증으로 인정하지 않고 FinalPolish 재촬영 대상으로 기록했다. 파라미터/스켈레탈 대상·지연 burst·완료된 효과는 이 격리 한 프레임으로 외관이 검증됐다고 주장하지 않는다. 굴절/물리 돌·얼음 파편의 장면 응답도 원래 기능이다. VFX에 HeinMach 전용 필터/색보정을 제거했다는 의미이며 모든 native HDR 변환·조명 응답을 우회한다는 뜻이 아니다.

실제 눈밭의 6종 혈액/데칼 및 수명·접지 검사는 ActualHitsHein02에서 성공했고 첫 밝은 후보를 낮춘 결과를 직접 확인했다. 실제 메인 RHI·피격·가드·콜리전 및 마지막 두 왜곡 발광 root의 재촬영은 현재 진행 중이다. 최종 결과는 본 문서 하단과 Metadata/HeinMachColourVFX_20261015/FinalVerification.json에 추가한다. 원작 사진의 카메라/광원 조건 및 원작 custom shader가 달라 완전한 원작 pixel parity는 미확인이다.


## 2026-10-15 — Main 반영·최종 검증 완료

앞선 같은 날짜의 RHI 진행 중/FinalPolish 대기 기록은 이 절로 대체한다. Main 105 package의 SHA를 전달 영수증과 다시 대조해 모두 동일함을 확인했다. MainSaved01의 map2/Definition7/Surface VFX root95/혈흔 Ground1 검사는 성공이다. 원래 PS321의 SHA, 재질 parameter multiset·blend/depth, 다른 HitReaction 설정을 보존한다. 장면 TEMP 값은 위 표 그대로이며 실험용 Kuwahara 에셋을 삭제하지 않고 HeinMach의 연결 두 개만 제외했다.

최종 색 검사의 정본은 NativeAllDev01/NativeAllHein01이다. 새 DEV 전용 KZ.QA.ColourShot이 실제 PIE game viewport를 직접 ReadPixels하여 잘못된 editor viewport가 찍히던 초기 Shot 결과를 대체했다. 두 맵 각각 현재 참조321 system/321 PNG, 실제998×426, shader compile/default fallback 실패0/저장0/Exit0을 확인했다. 전체321쌍 중 .2s에서 양쪽 신호가 보인 것은275이며 나머지46은 대상·파라미터·다른 시간대가 필요하다. 321개 전체의 최종 외관/원작 동일 프레임 일치를 한 장으로 검증했다고 확대하지 않는다.

NativeColourComparison의 검토 플래그7개 중5개는 무작위 크기·입자 분포에 따른 에너지 차이이며 색 방향 차이는 작다. 나머지 KZ_Parring_Distort/NS_Player_Plunge_ParringDistort는 발광 색보정 문제가 아니라 굴절 입력 차이다. 최초 QA panel이 투명 재질이라 서로 다른 맵의 opaque SceneColor를 샘플링했다. QA panel만 불투명으로 바꾼 RefractionOpaqueDev01/Hein01의 각3회, 총6쌍은 모두 가시/검토 플래그0, RGB signature 각도 최대2.600034°다. 이는 QA 비교값이며 게임 튜닝값이나 원작 일치 오차가 아니다. 원래 normal/refraction graph를 유지했다. [왜곡 비교](../../Metadata/HeinMachColourVFX_20261015/RefractionOpaqueComparison/All_00.jpg).

실제 HeinMach 눈밭에서 빨간 피격 혈액과 6종 기존 바닥 혈흔을 확인했다. MainHitsHein01의 승인 피격·가드/패링·몬스터6종 혈흔·사망/경사면/접지 없음/독립 수명·실제 공격 콜리전3 suite는 성공이다. MainCaptureBuild02의 표준 DLL 빌드는 성공했고 이후 native 색 검사는 새 모듈로 완료했다. 제거한 두 화면 필터 외 새 화면 pass는 없지만 Shipping FPS 측정은 하지 않았다. 원작 사진과 카메라·셰이더가 달라 완전한 원작 pixel parity는 미확인이다. 공통 native film tonemapping/AA와 물리 파편의 조명·굴절 반응은 유지되며 VFX가 모든 HDR 연산을 우회한다는 뜻이 아니다.

최종 영수증은 Metadata/HeinMachColourVFX_20261015/FinalVerification.json, 재개 기준은 ResumeState03.json이다. 중단된 전달/저장/필수 검증은 없고 작업 소유 editor는 모두 종료했다. Rider/타 세션 editor는 종료·저장·reload하지 않았다. 현재 Main에서 시작하고 완료 author/delivery나 이전 DLL/작업폴더의 일괄 복원을 반복하지 않는다. 과거 넓은 CombatEffect suite의 fixture/AI 간섭/시간초과는 실패 기록으로 남기며 이번 성공 suite로 소급하지 않는다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 — 후속 어두운 BlueB 룩 반영

사용자 후속 요청으로 이전 exposure bias−1.1/태양1800lux 등 장면 TEMP 값은 HEINMACH_BLUE_SPINNING_20261015.md의 BlueB 표(−2.15EV/1000lux/푸른 direct·sky 및 fog emissive)로 대체됐다. 기존 혈흔/피격/95 VFX root와 화면 필터 제거 결과는 보존한다. 새 전역 색보정은 없고 후속 Final03 native 색 비교의280 가시/42 조건 필요, 물리 조명·굴절 응답 한계를 따른다. 이전105개 전달을 반복하지 않았다. 최신 맵의 포탈/몬스터·PlayerStart를 유지한3개 선택 전달과 실제 Main 검수의 정본은 Metadata/HeinMachLookSpin_20261015/FinalVerification.json이다.

<!-- HeinMachLookSpin_20261015_complete -->
