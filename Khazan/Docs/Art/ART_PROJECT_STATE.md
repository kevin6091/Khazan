# Art / Resource 프로젝트 상태

> FModel 추출, UE 임포트, 캐릭터·환경 에셋, 머티리얼, Level 복원 상태만 기록한다.
> C++·Gameplay BP·Config·컴파일·런타임 Crash 정보는 이 문서에 기록하지 않는다.

## 2026-08-31 기준

- [완료] 카잔 파츠를 `SKM_Khazan` 베이스에 Leader Pose Component로 동기화했다.
- [완료] Ghost 무기의 투명·발광 머티리얼 구조를 분석했다.
- [완료] 프로젝트 로컬 `Plugins/UnrealPSKPSA`를 UE 5.8용으로 구성하고 FModel PSK 21개를 `/Game/_Art/Kazan/FModel/PSK`에 임포트했다.
- [완료] HeinMach corrected source library에 Static Mesh 183개, Material Instance 334개, Texture 955개를 분리 임포트했다.
- [완료] 일반 prop 2,665개, foliage HISM 113배치/12,495 instance, child render mesh 15개, fog sheet 50개, terrain 2개, source light 89개를 복원했다.
- [완료] 완성 Level은 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment` 하나다.
- [검증] 최종 Level은 액터 2,938개이며 통합 감사 26/26을 통과했다.
- [제약] terrain의 원본 WLM/weightmap/layer graph와 fog의 원본 custom parent shader graph는 추출물에 없어 현재 표현은 가역적인 preview 근사치다.
- [범위 제외] 모든 `HeinMach_Cine_*`와 주인공이 맨손으로 비틀거리며 기본 이동만 하는 장면은 Art 복원 대상에서 제외한다.

## 레거시 상세 기록

- FModel 네이밍·파츠·경로 상세: `4_FMODEL_ASSET_RULES.md`
- 기존 전수조사 수량과 canonical report: `6_SURVEY_KNOWLEDGE_BASE.md`
- 위 파일은 필요한 질문이 있을 때만 Art 작업에서 선택적으로 읽고 새 결과를 추가하지 않는다.

## 2026-09-01 HeinMach 정밀 복원 완료 기준

- [완료] 라이브 완성본은 계속 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment` 하나다.
- [완료] 원본 root/template 계층을 재사용해 일반 Prop을 2,665개에서 9,104개로 확장했다. 중복·예상 밖 액터·mesh/transform mismatch는 모두 0이다.
- [완료] child StaticMesh는 direct 15개와 inherited 12개, 총 27개이며 누락·좌표·머티리얼 mismatch는 0이다.
- [완료] foliage는 HISM 113배치, 12,495 instance를 유지하며 mesh·수량·actor/instance transform·material mismatch는 0이다.
- [완료] 원본 LandscapeComponent USDA 57개를 exact geometry proxy로 복원했다. Landscape1 18개, Landscape2 39개이며 bounds·placement mismatch는 0이다.
- [완료] 실제 렌더링되는 Material Instance 613개를 감사했다. packed map 583개는 AO=R, Roughness=G, Metallic=B로 통일했고, 잘못 남은 Translucent 29개를 원본 JSON에 따라 Masked/TwoSided/clip 0.3333으로 복구했다. 최종 effective Translucent는 0개다.
- [완료] 원본 source light 89개를 보존하고 preview environment 4개와 동굴 검수용 route fill 3개를 사용한다.
- [검증] 최종 액터는 9,449개, categorized 9,449개, uncategorized 0개이며 `HeinMach_Final_Reconstruction_Audit.json` 31/31을 통과했다.
- [검증] PlayerStart 기반 6개 지점에서 재시작 후 카메라 검수를 수행했다. 대표 경로에서 부유·유격·inside-out으로 판정할 정적 메시 문제는 발견되지 않았다.
- [검증] 비-Fog root StaticMesh 미해결은 0개다. root audit의 미해결 694개 중 StaticMeshComponent 50개는 모두 범위 제외 Fog이며 나머지는 Nav/Brush/Spline/Decal/동적 Skeletal·Gameplay 타입이다.
- [경계] Fog 50개는 수정하지 않았다. 위치 해시는 계속 `3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48`이다.
- [제약] 원본 Landscape WLM/weightmap/layer graph는 추출물에 없어 57개 geometry proxy에 slope-based recovery material을 사용한다. 이를 원본 Landscape 셰이딩의 완전 복원으로 기록하지 않는다.

## 2026-09-02 HeinMach Fog / Lighting 최종 폴리싱

- [완료] 라이브 완성본은 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`다.
- [완료] Fog sheet 50개의 원본 transform, sort priority, one-sided 정책을 유지한 채 preview base material을 v4로 재구성했다.
- [완료] Fog v4는 2-octave panning noise, source Rotator/PanningSpeed, bounded density, edge fade, DepthFade, near/far fade와 약한 emissive를 사용한다.
- [완료] 누락된 원본 `xxVolumetricMist` 구현을 대체하는 가역적 preview `HM_PreviewVolumetricFog` 1개를 별도 폴더에 추가했다. 원본 shader 완전 복원으로 간주하지 않는다.
- [완료] source light 89개를 FModel 캐시 값으로 재설정하고 transform SHA-256 `c87a605a9227f5a4f7426d27a8b4f6bbdc6eeed1baa1f138672f9616e1f3c0f7`을 보존했다.
- [완료] 어두운 동굴/협로에 movable, shadowless route fill 5개를 별도 폴더로 추가했다.
- [완료] Post Process는 Histogram EV100 0–14, bias -0.25, speed up/down 3.0/1.5이며 Lumen quality 2, detail 1.5, view/trace 40,000 cm, gather 2, indirect 1.2다.
- [수정] 좌표 감사에서 Z가 2,320 cm 이탈한 `HM_Prop_HeinMach_SubLV01_OP_643_WP_VFS_Rock_Big_016_Inst_5` 한 개를 원본 `(16972.729, -9096.09, 3502.5315)`로 복구했다.
- [수정] `M_HeinMach_Landscape_Recovery`의 끊긴 ComponentMask graph를 v2 월드 노멀 내적 방식으로 교체했고 새 compile warning은 0건이다.
- [검증] 최종 액터 9,452개, categorized 9,452개, uncategorized 0개, 통합 감사 35/35 통과다.
- [검증] root Prop 9,104, child 27, foliage 113/12,495, Landscape component 57, terrain 2, Fog 50, source light 89, preview environment 4, route fill 5, preview volumetric fog 1이다.

가역 백업은 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment_PreFogLightingPolish`와 `Saved/ArtBackups/HeinMach_FogLighting_PrePolish_20260901`에 있다.

## 2026-09-02 HeinMach 보수적 최적화 및 최종 교정

- [보호] 사용자가 직접 삭제한 root Prop 3개, Landscape proxy 6개, terrain 1개를 `HeinMach_UserExclusions.json` tombstone으로 고정했다. 이후 복원 대상이 아니다.
- [백업] 사용자 편집 직후 맵은 `Saved/ArtBackups/HeinMach_UserEdited_BeforeOptimization_20260902_161357/L_HeinMach_Environment.umap`에 보존했다. SHA-256은 `17581BC984432060C3B194A9871D42E884024F7F23402EEE3E70A635768AA799`다.
- [완료] 완전히 동일한 mesh/material/transform/render/collision 상태가 증명된 중복 Prop 109개만 제거했다. 삭제 정본은 `HeinMach_OptimizationExclusions.json`이며 향후 복원하지 않는다.
- [보호] 기존 수동 이동 1개는 `HeinMach_ManualOverrides.json`의 `preserved_transform`으로 고정했다.
- [완료] `HeinMach_Spawn_Main01` metadata에서 DualAxeSword 공격 튜토리얼용 PlayerStart 1개와 적 위치 앵커 2개를 복원했다. 맨손 opening cine는 계속 제외한다.
- [경계] 적 AI spawn, 공격 안내 UI, 완료 gate, DualAxeSword 강제 장착은 Engineering 통합 작업으로 남는다.
- [수정] source LightColor 이중 sRGB 변환을 제거하고 89개 source light와 route fill 5개를 재검증했다. 최종 light property/color mismatch는 0개이며 source transform hash는 유지됐다.
- [수정] 흰색 나무 27개는 source snow 표현이 아니라 null/inherited LOD의 WhiteSquare fallback이었다. 동일 material family의 textured sibling으로 가지 slot만 복원했고 placeholder는 0개다.
- [검증] 최종 액터 9,336개, categorized 9,336개, uncategorized 0개이며 통합 감사 39/39가 모두 통과했다.
- [정본] 상세 근거와 재개 절차는 `Docs/Art/HEINMACH_OPTIMIZATION_TUTORIAL_LIGHT_TREE_2026-09-02.md`에 있다.

## 2026-09-03 HeinMach 사용자 추가 삭제 보존 및 StormPass 완료

- [보호] HeinMach에서 사용자가 추가로 삭제한 항목을 포함해 `HeinMach_UserExclusions.json`의 exclusion은 18개다. 전부 `do_not_restore=true`이며 이후 복원 금지다.
- [검증] HeinMach 최종 actor는 9,328개, uncategorized 0이며 사용자 exclusion 18개는 모두 부재한다. 맵 SHA-256은 `3D52A935E217467F009D7DAF165C0E49AC42508060B0AF10B0E261AAFC12ABEE`다.
- [수정] HeinMach dry-tree recovered material의 live binding 86개를 확인했고 흰 fallback/suspicious slot은 0이다.
- [완료] StormPass 라이브 맵은 `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment`다.
- [완료] StormPass 구성은 root 13,050, child 551, Landscape proxy 456, foliage HISM 218/21,259 instance, source Light 53, Fog 53이며 전체 actor는 14,381개다.
- [완료] source Light는 Point 52 + Spot 1, JellyFish IES binding 42개다.
- [완료] native WaterBody 두 곳의 WorldGrid fallback을 FModel material hierarchy와 texture 11개 기반 SingleLayerWater preview로 교체했다. hierarchy/parameter/binding reload failure는 0이다.
- [검증] 전체 material slot 17,976개에서 null 및 WorldGrid/Default material은 0개다.
- [검증] `StormPass_Final_Reconstruction_Audit.json`은 `status=passed`, failed stage 0이며 최종 맵 SHA-256은 `3719E53A6B2CEBED831DA586E04BFF13C1C5B76DAE5D2A5FDEA4C45DB42B03CA`다.
- [경계] cooked proprietary Fog/Water master graph는 추출물에 없어 UE5 preview graph를 사용한다. source mesh/transform/texture/parameter/instance 계층은 검증했지만 원본 graph 자체의 완전 복제로 기록하지 않는다.
- [정본] 상세 근거와 재개 절차는 `Docs/Art/STORMPASS_RECONSTRUCTION_2026-09-03.md`에 있다.

### 2026-09-03 StormPass Water source default closure

- [완료] `BASE_Black_NoneSRGB`를 추가해 Water source texture 11개와 master texture-parameter default의 미해결을 0으로 만들었다.
- [검증] 추가 저장 후 Fog를 마지막으로 다시 적용했고 Fog/Water/통합 reload audit는 모두 failure 0이다.
- [정본 갱신] 위 `3719...` 값은 closure 직전 체크포인트다. 최신 최종 맵 SHA-256은 `F63A6C8D66C3F5D6A677EF00B2AECDB4406A6B229AB7C4DB1E4D42F25CC2C91E`다.
- [백업] 최신 스냅샷은 `Saved/ArtBackups/StormPass_Verified_Final_20260903_151800`이며 라이브 `.umap`과 hash가 같다.

## 2026-09-03 DAS 로코모션 런타임 소스 정리

- [완료] Dual Axe Sword의 `Locomotion` package 범위에서 AnimSequence 107개를 확인했다. 구성은 Base 45, LockOn 25, Guard 16, Flow 21이다.
- [완료] 원본은 수정하지 않고 `/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword` 아래에 `RT_DAS_*` 런타임 복사본 107개를 준비했다.
- [완료] 원본 PSA frame metadata를 기준으로 공통 249-frame import 뒤에 남은 padding을 제거했다. 반복 take인 Run/Run_Hard는 첫 20-frame 주기, Sprint는 첫 60-frame 전신 주기를 사용한다.
- [완료] 45개 순환 loop에 `LeftFoot`/`RightFoot` Sync Marker 96개를 넣고 24 fps frame에 정렬했다.
- [완료] runtime 107개는 Root Motion 비활성, Force Root Lock 활성, Ref Pose lock 정책으로 통일했다.
- [검증] fresh-process 감사 결과 runtime 107/107, source 107/107, 오류 0, 경고 2다. 경고는 Base Idle 두 개의 원본 PSA 구간이 현재 FBX export보다 각각 14 frame 긴 source 제한이다.
- [경계] 이름에 이동 단어가 있어도 `Locomotion` package 밖의 공격·스킬·장착 문맥 17개는 범위에 포함하지 않았다.
- [정본] 구조와 Anim Blueprint 사용 기준은 `Docs/Animation/ANIMATION_LOCOMOTION.md`, 상세 mapping은 `Saved/ImportReports/Khazan_DAS_Locomotion_RuntimeBuild.json`에 있다.
- [백업] 작업 전 런타임 바이너리는 `Saved/ArtBackups/DAS_Locomotion_Runtime_Before_2026-09-03`에 보존했다.

## 2026-09-04 StormPass 배치·환경·머테리얼 최종 교정

- [범위] StormPass 환경 Level만 수정했다. Gameplay/C++/캐릭터 이동 로직과 HeinMach는 열거나 변경하지 않았다.
- [배치] FModel JSON/저장 metadata 기준으로 root 13,050, child 551, Landscape proxy 456, foliage HISM 218/21,259 instance의 위치를 다시 감사했다. 누락·초과·중복·배치 mismatch는 모두 0이다.
- [환경] source profile 27개를 복구·검증했다: Directional Light 1, Exponential Height Fog 1, Post Process Volume 11, Sky Light 1, Sphere Reflection Capture 9, environment Static Mesh 3, Wind Directional Source 1. Directional Light actor scale은 source 값 `(1,1,1)`로 교정했고 sky/cloud mesh collision은 비활성화했다.
- [Light] source Light 53개(Point 52 + Spot 1, JellyFish IES 42)의 transform/property mismatch는 0이다.
- [머테리얼] 흰색으로 보이던 나무 계열 MI 9개/사용 slot 733개를 source texture와 packed `_S` 채널(AO=R, Roughness=G) 기반 `M_SP_SourceTreeFoliage_V2`로 교정했다.
- [머테리얼] 잘못 발광하던 world prop MI 5개/44 slot의 비원본 emissive texture 사용을 해제했고, ore MI 4개/860 slot은 source texture·색·발광 계층 기반 `M_SP_SourceOre_V2`로 복원했다.
- [컴파일] V2 parent는 실제 `TC_MASKS` texture를 기본값으로 사용한다. V2 생성 이후 로그 2,477줄에서 `Failed to compile`/`Sampler type` 오류는 0이며 최종 감사의 sampler failure도 0이다.
- [Fog-last] 모든 교정 이후 Fog 53개(Standard 51 + Local 2)를 마지막 쓰기 단계로 재적용했다. Fog 누락·초과·transform/material/parameter failure는 0이다.
- [검증] 최종 actor 14,408개, material slot 17,979개, null/WorldGrid/Default material 0개다. `StormPass_Final_Reconstruction_Audit.json`은 `status=passed`, failed stage 0이다.
- [정본] 최종 맵 크기는 43,709,400 bytes, SHA-256은 `9A4B02BE61CA734265B91490828B6369B69CC3428D7A82726CEA215B770D9191`다.
- [백업] `Saved/ArtBackups/StormPass_Verified_Final_20260904_111819`에 맵과 핵심 report 9개를 복사했고 라이브/백업 `.umap` hash 일치를 확인했다.
- [제약] cooked proprietary material graph는 추출 metadata에 topology가 없어 source texture/parameter를 사용하는 UE5 native preview graph로 재구성했다. 불규칙 BSP Post Process Volume 6개는 source point/plane metadata를 보존한 exact transformed-bounds proxy다.

## 2026-09-04 StormPass 하늘·Fog 화면 절단 교정

- [범위] StormPass 환경 Level의 하늘, 구름, Fog, SkyLight와 기존 배치/머테리얼 검증만 수행했다. Gameplay/C++/캐릭터 로직과 HeinMach는 변경하지 않았다.
- [원인] 화면을 수평으로 덮던 주된 밴드는 Fog actor가 아니라 source cloud hemisphere였다. 기존 preview cloud는 source `HorizonVisibilityMin/Max` fade가 빠지고 depth test가 비활성화되어 돔 하단이 화면 공간 경계처럼 렌더링됐다. 기존 Fog preview의 `PixelDepth` near/far fade도 카메라가 큰 sheet에 접근하거나 교차할 때 별도 절단선을 만들 수 있었다.
- [하늘] `M_SP_SourceSky_V2`는 wrapped USD V 좌표 대신 `WorldPosition - ActorPositionWS` 높이를 사용해 source Bottom/Sky/Overall color를 보간한다. `MI_SP_Sky_GloomyDay_V2`와 cloud V2 두 layer를 sky/cloud actor 3개에 연결했다.
- [구름] `M_SP_SourceCloud_V2`에 source horizon visibility 범위 기반 월드 높이 fade를 복구하고 depth test를 활성화했다. cloud density/distortion/lookup/normal texture와 source scalar/vector parameter는 유지했다.
- [Fog] 3종 Fog parent를 V2로 교체했다. `PixelDepth`를 제거하고 `Distance(WorldPosition, CameraPositionWS)`, `DepthFade`, 면 방향 fade를 사용한다. source 배치와 MIC parameter는 그대로이며 parent 분포는 FMI_02 45, FMI_01 6, Local 2다.
- [Light/배치] source 좌표와 정확히 일치하던 background mountain은 이동·숨김·삭제하지 않았다. sky material 교체 뒤 남아 있던 검은 SkyLight capture만 deterministic recapture했다. 보호 대상 14,381개 actor transform signature는 변경 전후 동일하다.
- [머테리얼] 활성 tree parent `M_SP_SourceTreeFoliage_V2`를 현재 상태에서 다시 컴파일했으며 tree/sky/cloud/Fog V2의 신규 `Failed to compile` 로그는 0건이다.
- [검증] 저장 맵 리로드 뒤 actor 14,408, Fog 53, environment 27, material slot 17,979, null/WorldGrid/Default 0이다. Fog 최대 오차는 location/scale 0, rotation `0.00000242°`이고 `PixelDepth` 재도입, depth-test 비활성화, 잘못된 V2 assignment는 모두 0이다.
- [정본] `StormPass_Final_Reconstruction_Audit.json`은 `status=passed`, failed stage 0이다. 최종 `.umap`은 43,709,418 bytes, SHA-256 `E1007AFFEAE22AF49599690EB3CE67582B1B43FC25C8D3E6AFBE17B76C03361D`다.
- [백업] 작업 전 관련 맵/환경/Fog asset과 스크립트 65개, 44,771,313 bytes를 `Saved/ArtBackups/StormPass_PreSkyFogVisualFix_20260904_121446`에 보존했다.

## 2026-09-04 HeinMach 전역 Fog·FogSheet·머티리얼 무결성 교정

- [범위] HeinMach 환경 Level의 전역 Fog, FogSheet, 환경 머티리얼/셰이더, 오브젝트 배치만 검토·수정했다. `KhazanAnimInstance.h`를 포함한 Source/Gameplay/캐릭터 콘텐츠는 변경하지 않았다.
- [보호] 사용자 exclusion 18개와 보수적 최적화 exclusion 109개, 총 127개 tombstone은 수정 전후 모두 부재한다. 사용자 삭제 오브젝트는 하나도 복원하지 않았다.
- [원인] 기존 FogSheet preview parent는 구형 그래프와 최신 그래프가 한 asset에 함께 남아 105 expression/`PixelDepth` 2개 상태였다. 화면 공간 깊이 fade는 카메라가 큰 sheet에 접근하거나 교차할 때 절단선이 생길 위험이 있었다. 전역 Fog는 cutoff 70,000 cm의 하드 경계와 R/B가 뒤집힌 albedo도 갖고 있었다.
- [FogSheet] 새 `M_HeinMach_FogSheet_Preview_V5`를 75 expression의 단일 그래프로 구성했다. `Distance(WorldPosition, CameraPositionWS)`, `DepthFade`, facing fade를 사용하며 `PixelDepth`는 0개, depth test는 활성, one-sided다. 50개 MI의 source opacity/fade/pan/noise/tint parameter와 sort priority를 보존해 V5로 연결했다.
- [컴포넌트] FogSheet 50개는 source `WBP_FogSheet` 정책에 맞춰 collision/navigation/overlap/decal/occluder/indirect-light/shadow 영향을 모두 비활성화했다. 저장 후 재로드에서도 정책과 V5 assignment가 유지된다.
- [전역 Fog] `HM_PreviewVolumetricFog`는 맵 전체에 정확히 1개다. cutoff를 0으로 바꿔 하드 경계를 제거하고 albedo를 `(158,177,196)`의 올바른 RGB 순서로 교정했다. 기존 보수적 preview density/falloff/volumetric distance는 유지했다.
- [배치] actor 9,328개와 모든 actor label/transform signature를 보존했다. FogSheet 50개는 source metadata 대비 location/scale 오차 0, rotation 최대 `4.9072266e-6°`이며 누락·초과·mesh/material/sort mismatch는 0이다.
- [머티리얼] 현재 맵 기준 나무 1,123 actor/1,669 slot/100 material을 재감사해 missing/default/placeholder 후보 0개를 확인했다. 관리 환경 material 605종/11,460 slot은 channel repair 필요 0, 잘못된 opaque-parent 0, effective Translucent 0이며 null/WorldGrid/Default fallback도 0이다.
- [컴파일·검증] V5를 표적 재컴파일했고 `Failed to compile`/`LogMaterial`/shader compiler error는 0이다. `HeinMach_Final_Reconstruction_Audit.json`은 `all_checks_passed=true`, 43/43 통과다.
- [정본] 최종 맵 SHA-256은 `B209ACB34FCEFC3D6F11EE47D098107976CA30B6A84CFA16335EA6638C2812E0`이다. 작업 전 안전 백업은 `Saved/ArtBackups/HeinMach_PreFogReview_20260904_143116`, 비교 캡처는 `Saved/ArtValidation/HeinMach_Fog_Review_20260904`에 있다.
- [제약] source WEP가 구역별로 전환하는 cooked `FOG_Deep`/`FOG_Dark` controller와 proprietary master graph topology는 추출물에 없다. 따라서 단일 전역 Fog는 source 색/특성을 참고한 안정적인 UE5 preview이며 원본 런타임 지역 전환 로직의 완전 복제로 기록하지 않는다.

## 2026-09-08 Khazan 스켈레톤 편집 후 애니메이션 트랙 복구

- [완료] InGame DAS 작업본 8개의 삭제된 본 트랙을 1개(root) → 226개로 복구했다. 현재 길이와 Sync Marker 30개를 보존하고 기존 root 키를 변경하지 않았다.
- [검증] 별도 Unreal 프로세스에서 8/8 RAW 전체 본/프레임, 압축 포즈의 발 동작, root/marker/설정 보존을 확인했다. 대상 외 Content 파일 61개는 백업과 SHA-256이 동일하다. 최종 commandlet exit 0/오류 0.
- [보존] SK_Khazan/SKM_Khazan은 시작 시점부터 Git HEAD와 같았으며 수정하지 않았다. 현재 계층은 C_P_Kazan → Root → Bip001이다.
- [백업] Saved/ArtBackups/Khazan_SkeletonRecovery_20260908_132146에 현재/자동 저장 82개 파일과 검증 hash를 보존했다.
- [경계] Sprint Stop은 이번 시작 시점의 10.375초 길이를 보존했다. 직전 기록의 4.75초로 다시 자를지는 사용자 답변 대기다. Root 최상위 계층 변경과 PIE 발 접지 검증은 수행하지 않았다.
- [정본] Docs/Animation/SKELETON_RECOVERY_2026-09-08.md 및 Saved/ImportReports/Khazan_SkeletonRecovery_FreshAudit_20260908.json.

## 2026-09-08 DAS loop 사용자 끝 프레임 포즈 재적용 완료

- [보완] 이전 본 트랙 복구가 사용자 Control Rig의 첫 프레임→마지막 프레임 복사 편집까지 재현하지 못했음을 확인했다.
- [완료] InGame Walk/Run/Sprint loop의 기존 마지막 33/119/119번 sample을 0번 포즈와 같게 복원해 저장했다. 길이/설정, Sync Marker 총 30개와 중간 프레임 포즈를 보존했다.
- [검증] 별도 프로세스에서 3/3 RAW 및 compressed 처음·끝 포즈 차이 0. 보호 대상 Content 66개 SHA-256 동일, commandlet exit 0/오류 0.
- [백업] Saved/ArtBackups/DAS_LoopClosure_20260908_134814에 현재 파일 6개와 전체 loop RAW 포즈/설정 스냅샷을 보존했다.
- [정본] Docs/Animation/SKELETON_RECOVERY_2026-09-08.md의 추가 복구 섹션 및 Saved/ImportReports/Khazan_DAS_LoopClosure_verify_20260908.json. 이전 source-equality 감사는 이 끝 프레임 수정 이전의 이력이다.

## 2026-09-08 HeinMach Enemy 외형 라이브러리 추가

- [완료] `/Game/_Art/Enemies/HeinMach`에 튜토리얼 검병 40종, 검·방패병 4종, 별도 할버드 정예 1종의 외형 Blueprint를 저장했다. 개별 source 메시 17개와 조합 전신 메시 44개, texture 149개, source 대응 material 36개 및 보조 material 1개, idle animation 3개를 포함한다.
- [검증] `HeinMachEnemy_FreshAudit.json` 통과. 별도 UE 프로세스에서 source 참조와 모든 idle sample/bone RAW·COMPRESSED pose, Blueprint 45개의 spawn/무기 socket을 확인했다. `Preview/L_HeinMach_EnemyCatalogue`를 신규 저장했다.
- [출처] 튜토리얼 actor는 `SA_EmpireSword_Early3_Item`, `SA_Empire_SwordShield_2`. Halberd를 튜토리얼 검병의 도끼 variant로 단정하지 않는다. source closure 327/missing 0, raw archive 347 package를 보존했다.
- [경계] 원작 전용 shader는 표시용 대체 그래프다. 랜덤 색상·체형 적용, UE MorphTarget/LOD 체인·cloth/physics 전체 복원과 전투 AI는 미완료다. 원본 metadata와 ActorX/raw는 보존했다. geometry 조합 40/4를 색상·체형까지 완전 복원한 수로 해석하지 않는다.
- [보호] 기존 HeinMach/StormPass 환경 맵 2개 SHA-256이 시작 시점과 같다. 기존 Player/C++는 직접 편집하지 않았다.
- [정본] `Docs/Art/HEINMACH_ENEMY_EXTRACTION_2026-09-08.md`. 실제 그래픽 RHI compile 결과는 해당 문서 하단 및 `HeinMachEnemy_RenderAssetAudit.json`의 최종 상태를 확인한다.

### 2026-09-08 Enemy 그래픽 감사 완료

- `HeinMachEnemy_RenderAssetAudit.json` passed. 실제 D3D SM6 material 37개 compile 및 저장된 확인용 맵의 조립 45개 재로드를 통과했다. 미참조 staging Skeleton 12개를 정리했다. 최종 Enemy 폴더는 uasset 300개 + 새 catalogue map 1개다.
- 원작 완전 재현의 미완료 항목은 위 경계와 Enemy 정본에 유지한다. 전투 PIE나 원작 화면 일치 검증 완료를 의미하지 않는다.

## 2026-09-09 Enemy 의상·병종·애니메이션 확장 완료

- 대표 외형을 검병 4, 방패병 4, 궁병 4, 중갑 대검병 1, 할버드 정예 1, 별도 지역 마법사 2의 총 16개로 구성했다. 얼굴은 001/002/003을 순환 사용한다. 검/방패의 군복 공유는 원본 recipe와 일치하며 궁병·중갑·로브와 활·대검·지팡이를 추가했다.
- `/Game/_Art/Enemies/HeinMach/Humanoids` 및 `/Game/_Art/Enemies/OtherRegions/Humanoids`에 BP를 저장했다. 기존 얼굴 중심 45개 BP와 44개 메시를 `HeinMach/Archive/FaceVariants_20260908`로 옮겼다. 이전 경로 대응은 `LegacyAssetMoves.json`이며 디스크 redirector는 없다.
- 원본 711개 시퀀스를 metadata의 30 fps 시간축으로 임포트하고, 원본 구간 배속·DilationCurve를 반영한 재생용 722개를 추가했다. 1,433개 모두 저장 길이·RateScale·첫/중간/마지막 모든 bone의 RAW/COMPRESSED pose 검증을 통과했다. 최대 길이 오차는 약 4.124e-7초다.
- 텍스처 256, 머티리얼 69, 원본/재사용 메시 36 및 통합 몸체 14를 관리한다. 실제 RHI와 BP 16개 검증을 통과했고, 최종 뷰포트에서 발견한 회전 축 오류도 수정해 수직 배치를 확인했다.
- 정본: [HEINMACH_ENEMY_EXPANSION_2026-09-09.md](HEINMACH_ENEMY_EXPANSION_2026-09-09.md). 통합 보고서: `Saved/ImportReports/HeinMachEnemyV2_FinalAudit.json`. 카탈로그: `/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue`.
- 기존 Player C++/ABP/DAS와 두 환경 맵은 무변경이다. 원작 cartoon shader topology, 색상·체형 RNG, UE morph/LOD/cloth/physics 전체 복원과 전투 runtime 배속은 완료 범위에 포함하지 않는다. 관련 원본·메타데이터는 보존했다.

### 2026-09-09 사용자 요청에 따른 Enemy 실사용 외형 정리

- 미사용 BP 45, 메시 67, 머티리얼 41, 텍스처 42의 총 195개(약 327.53 MiB)를 Content에서 삭제했다. 현재 BP 16, 메시 29, Skeleton 10, 머티리얼 65, 텍스처 214다. 기존 Archive의 얼굴 중심 조합도 삭제 대상에 포함된다.
- 애니메이션은 후속 검증·선정 전까지 모두 유지한다. 기존 Idle 3+Source 711+Playback 722=1,436개이며, 남긴 UE 자산 1,771개 전체 hash는 정리 전과 같다.
- 재생용 722개를 비교해 시간축이 달라지는 271개와 원본과 시간축이 같은 451개로 분류했다. 451개 중 440개는 sample 수와 포즈도 저장 정밀도 안에서 같고, 11개는 표본 수가 다르다. 실제 삭제는 아직 하지 않았다.
- 최신 정본: [ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md](ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md). 현재 inventory와 비교표는 `Content/_Art/Enemies/HeinMach/Metadata/Cleanup_20260909`에 있다. 이전 import manifest는 추출 당시 자료다.
- `HeinMachEnemy_CleanupAudit_20260909.json` passed. 별도 프로세스에서 BP 16개와 카탈로그를 로드했으며 missing Enemy dependency 0, 오류 0이다. 기존 코드/플레이어/환경 및 작업 시작 시 보호 파일 44개는 동일하다.

### 2026-09-09 Enemy 원본 애니메이션 조건부 정리 완료

- 원본 549개(290,576,489 bytes, 약 277.12 MiB)를 삭제했다. 현재 AnimSequence는 Playback 722 + Source 162 + 기존 Idle 3 = 887개다. 직접 사용 또는 대체 미확인 원본이 있어 재생용만 남기는 전면 삭제는 하지 않았다.
- 남은 Enemy UE 자산 1,222개 전체 hash가 작업 전과 같다. BP 16개와 재생용 FPS/길이/RateScale/포즈를 편집하지 않았다. 원작 AP/BlendSpace/Weapon Notify의 직접 참조와 현재 BP 원본 참조 5개를 보존했다.
- 별도 commandlet에서 저장 rate/sample/길이·compressed pose 2,166개·BP 참조 검증 passed, 누락 dependency 0, 최종 exit 0/오류 0. 외부 문서 작업 8개 변경은 별도 관측·보존했다.
- 최신 정본: [ENEMY_SOURCE_ANIMATION_PRUNING_2026-09-09.md](ENEMY_SOURCE_ANIMATION_PRUNING_2026-09-09.md). 현재 목록은 `Metadata/AnimationPruning_20260909/RetainedAssets.json`, 복구 백업은 `Desktop/카잔/EnemyExtracts/AnimationPruning_20260909`다.
