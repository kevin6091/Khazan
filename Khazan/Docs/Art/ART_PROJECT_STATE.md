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

## 2026-09-08 Stop C_P_Kazan Root 트랙 _New 생성

- [완료] InGame의 Run_Stop_LF/Run_Stop_RF/Sprint_Stop을 같은 이름_New로 복사하고 Root/C_P_Kazan의 애니메이션 트랙만 수정했다. 상위 scale 100을 반영해 움직임을 C_P_Kazan으로 옮기고 Root 트랙을 비웠다. Skeleton/본 계층은 유지했다.
- [보존] 현재 원본 길이 3.958333/3.791667/4.75초, 24 fps, Sync Marker와 일반 속성/옵션을 보존했다. 나머지 본의 FK Control Rig 채널 2,025개는 키/탄젠트까지 같다. 보호 파일 71개 hash가 동일하다.
- [검증] 별도 Unreal 프로세스에서 _New 3/3 RAW/압축 포즈, Root 고정, 기타 채널 및 속성 보존을 확인했다. 최종 commandlet exit 0/오류 0.
- [범위] Root Motion 활성화/정규화 scale/Root Lock 등 설정은 원본대로 유지했다. 실제 CharacterMovement 이동 거리나 PIE 전이 검증은 하지 않았다.
- [백업/정본] Saved/ArtBackups/DAS_StopRootTransfer_20260908_141845, Docs/Animation/STOP_ROOT_TRANSFER_2026-09-08.md, Saved/ImportReports/Khazan_DAS_StopRootTransfer_verify_20260908.json.

## 2026-09-08 DAS 로코모션 24 fps 시간축 재검사

- [완료/읽기 전용] PSA 11개, Blender FBX 6개, 현재 InGame 시퀀스 11개 및 ABP Sequence Player 10개를 표적 검사했다. PSA/FBX/게임 코드/에셋은 변경하지 않았다.
- [판정] 현재 InGame은 모두 24 fps/RateScale 1.0이다. PSA N/R 및 공개 CUE4Parse exporter 계산 규칙에서 복원한 유효 sample 간격은 11개 모두 약 30 fps다. 과거의 “24 fps로 임포트됨”은 “원작 속도가 정확히 24 fps”라는 뜻이 아니다.
- [근거] FBX 키 시간이 1/24초 격자에 있고, source/현재 InGame 각각 5개 시퀀스의 표적 본 회전 변화는 PSA 연속 frame +1과 대응했다. 같은 동작 구간을 24 fps 시간축에 배치해 늘어난 것으로 판단한다.
- [미적용 제안] 동일 키 구간의 30/24=1.25배 비교 테스트. 원작의 최종 ABP/Montage/RateScale 및 정확한 exporter binary 버전은 미확인이다. 속도/접지의 시각 합격이나 모든 애니메이션의 전수 보정을 완료한 것이 아니다.
- [정본/재사용] [DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md](DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md), Saved/ImportReports/Khazan_Locomotion_Timing_Audit_20260908.json. 기존 marker/loop 끝 pose/Stop root 편집은 보존했다.
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

### 2026-09-09 Enemy 재생 애니메이션 네이밍·폴더 통합 완료

- 남은 AnimSequence를 실제 재생 역할로 통합했다. 중복 초기 Idle 3개를 전 프레임 RAW/COMPRESSED 비교 후 제거하고 최종 884개를 모두 `A_EN_PLAY_*`, 병종별 `Animations/Playback` 폴더로 이동했다.
- 원작 Composite bake 722개와 원본 시간축 직접 재생 162개는 파일명/폴더를 공유한다. 유래는 `PlaybackDerivation`과 `PreviousEnemyArtRole`, `OriginalPackage` metadata로 구분한다. FPS·길이·sample·RateScale·root 설정은 변경하지 않았다.
- BP 16개의 애니메이션 참조를 UE rename으로 새 경로에 저장했다. old package/redirector/missing dependency 0. 별도 commandlet에서 884개 RAW/COMPRESSED 5,298 pose 평가, 카탈로그 16개, 최종 exit 0/오류 0을 확인했다.
- 최신 정본: [ENEMY_ANIMATION_LIBRARY_STRUCTURE_2026-09-09.md](ENEMY_ANIMATION_LIBRARY_STRUCTURE_2026-09-09.md). 현재 목록은 `Metadata/AnimationStructure_20260909/CurrentAssets.json`, 애니메이션 표는 `AnimationLibrary.csv`, 백업은 `Desktop/카잔/EnemyExtracts/AnimationStructure_20260909`다.

## 2026-09-10 HeinMach·StormPass BigBear Enemy 라이브러리 추가

- 두 레벨의 실제 스폰이 같은 `CB_BigBear_E`를 참조하고 HeinMach는 `AI_BigBear_E_NoneBurst`, StormPass는 `AI_BigBear_E_BurstTutorial`을 쓰는 것을 확인했다. 중복 캐릭터 대신 `/Game/_Art/Enemies/Shared/Beasts/BigBear` 공용 라이브러리로 구성하고 레벨별 맥락은 metadata에 보존했다.
- 원작 외형 V1/V2/V3 Blueprint 3개, SkeletalMesh/Skeleton 각 1개, 머티리얼 12개, 텍스처 25개, preview map 1개와 재생용 AnimSequence 102개를 저장했다. 전체 Asset Registry 자산은 145개이고 staging/redirector는 0개다.
- 메시 71-bone PSK에만 맞추지 않고 76개 PSA 공통 79-bone 레이아웃의 helper 8개를 reference pose와 함께 복구했다. 프로젝트는 검증된 LOD0 30,023 vertices를 사용하며 원작 LOD0/1/2는 외부 archive에 보존한다.
- 애니메이션은 30fps 직접 시간축 12개와 Composite bake 90개다. 구간·반복·AnimPlayRate·DilationCurve를 포즈에 적용하고 최종 길이에 맞는 유리수 FPS로 저장해 모두 RateScale 1.0으로 재생한다. root motion 95, force root lock 3, additive 1의 source 설정을 보존했다.
- 별도 UE 프로세스에서 102개 RAW/COMPRESSED 포즈와 길이, 145개 에셋 구조, D3D12/SM6 머티리얼 12개 및 BP 3개 재로드를 통과했다. 정본은 [BIG_BEAR_EXTRACTION_2026-09-10.md](BIG_BEAR_EXTRACTION_2026-09-10.md), 최종 보고서는 `BigBear/Metadata/Extraction_20260910/FinalExtractionReport.json`이다.
- Blueprint는 시각 조립 Actor이며 AI/GAS/공격 collision/ragdoll/원작 Notify 실행은 포함하지 않는다. proprietary cartoon shader graph와 source LOD chain도 완전 복원 범위가 아니다.

## 2026-09-11 HeinMach Yetuga 보스 라이브러리

- `HeinMach_Spawn_Main01.SA_Yetuga`의 `ActorBP_Soft` → `Boss/01_Yetuga/Base_Setting/CB_Yetuga`와 실제 `CharacterMesh0`을 기준으로 `/Game/_Art/Enemies/HeinMach/Bosses/Yetuga`에 보스 라이브러리를 구성했다.
- 본체 453 bone/소형 얼음 20 bone의 mesh·skeleton 각 2개, 2D texture 56개, source parent/leaf MI 14개와 preview shader 3개, 시각 BP 1개, 비교 map 1개, 재생용 AnimSequence 120개로 Asset Registry 총 199개다. 모든 시퀀스는 `Animations/Playback/A_EN_PLAY_*`에 있고 임포트 원본 시퀀스 중복은 없다.
- 원본 PSA 91개 중 다른 몬스터 폴더의 Grapple_B 두 개도 `Skeleton=C_M_Yetuga_Skeleton`을 확인해 포함했다. 직접 시간축 9개와 Composite 111개를 저장했으며 활성 dilation 66개, root motion 99개, force root lock 68개, additive 1개다.
- 본체 원본 198-bone PSKX에 PSA 전용 비가중 reference bone 255개를 추가했다. 소켓 7개를 원본 이름·parent·transform으로 복원했고 원본 LOD0/1/2는 archive에 보관한다. 현재 임포트된 LOD0은 본체 207,390/얼음 8,051 vertices다.
- 정본은 [YETUGA_EXTRACTION_2026-09-11.md](YETUGA_EXTRACTION_2026-09-11.md). 원본 JSON·상속값·시간축·검증 결과는 Yetuga의 `Metadata/Extraction_20260911`을 따른다. 전용 shader graph, AI/전투/physics/cloth/custom notify 실행은 별도의 복원 범위이며 시각 BP에 구현한 것으로 간주하지 않는다.

## 2026-09-15 ApesStoneHandElite Early/Standard 실사용 라이브러리

- `/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite`에 공용 mesh/skeleton 1쌍, texture 31개, MI 13개/master 2개, 재생 시퀀스 92개, Early/Standard 시각 BP 2개 및 비교 맵으로 총 143개 에셋을 저장했다. 새 프로세스의 에셋/참조/포즈 감사는 exit 0/pass이며 임시 package 0개다.
- 원작 CB component override까지 확인한 최종 외형은 Early=기본 재질, Standard=V3다. V2와 Early의 추가 V3 재질 조합은 레시피 CDO 기본값에서 실제 CB에 의해 교체된다. HeinMach 스폰 3개와 StormPass 1개는 Early이며 Standard의 두 레벨 스폰을 확인한 것으로 확대하지 않는다.
- 기본/V3 메시의 material chunk 외 payload가 동일해 중복 메시를 만들지 않았다. 97-bone 원본의 bind/weight 수치를 보존한 채 PSA 453-bone 순서로 재매핑하고 비가중 helper 356개를 추가했다. 소켓 7개, 원본 3 LOD 보관과 UE LOD0 24,862 vertices를 확인했다.
- 직접 source 시간축 10개와 원작 Composite bake 82개 모두 `Animations/Playback/A_EN_PLAY_*`다. 활성 dilation 44개, root motion 70개, force root lock 51개, additive 1개를 원본 property 기준으로 대조했다. 최대 길이 오차 약 `1.94214e-7 s`이며 원본 게임 전체 실행의 hit-stop/AI 속도 실측 검증은 아니다.
- 정본 [APES_STONE_HAND_EXTRACTION_2026-09-15.md](APES_STONE_HAND_EXTRACTION_2026-09-15.md), 선택 근거 `VariantUsage.json`, 보존 확인 `MeshDerivationAudit.json`, 최종 완료 상태는 `ValidationSummary.json`/`RenderValidationSummary.json`/`FinalExtractionReport.json`이다. Ghost/Wraith·시체·V2 분류 JSON과 원작 BoneMod는 보존하며 전용 shader/BoneMod/AI 실행까지 완전히 구현한 것으로 간주하지 않는다.

## 2026-09-15 StormPass WildDog·WildBoar 실사용 라이브러리

- 두 `HeinMach_Spawn_Main01`/`StormPass_Spawn_Main01`을 표적 조사했다. WildDog는 StormPass의 `CB_WhiteDog` spawn 17개, WildBoar는 StormPass의 `CB_WildBoar_New` spawn 2개가 확인됐고 HeinMach에는 두 종의 spawn이 없다.
- `/Game/_Art/Enemies/Shared/Beasts/WildDog`에는 공용 mesh/skeleton, texture 25개, source MI 10개/master 2개, CoatV1~V3 BP와 재생 시퀀스 82개를 포함한 125개 에셋을 저장했다. 일반 PicaroonDog와 Ghost 후보는 선택한 live spawn closure 밖이므로 UE 캐릭터에서 제외했다.
- `/Game/_Art/Enemies/Shared/Beasts/WildBoar`에는 공용 mesh/skeleton, texture 20개, source MI 7개/master 2개, CoatV1~V3 BP와 재생 시퀀스 74개를 포함한 109개 에셋을 저장했다. 캐릭터 geometry는 하나지만 원본 `PartsIndexCache`가 재질 외형 세 결과를 노출하므로 세 BP를 유지했다.
- 각 종의 V1/V2/V3 ActorX는 material chunk 이외 payload가 같아 mesh 한 개로 deduplicate했다. Dog 48 bone/weight 35,029행, Boar 71 bone/weight 12,528행의 원본 대응을 검사했고 source LOD0/1/2는 archive에 보관하며 UE에는 LOD0만 임포트했다.
- WildDog 애니메이션은 direct 17/composite 65의 82개, WildBoar는 direct 11/composite 63의 74개다. 직접 시퀀스는 모두 원본 30/1 FPS이고 Composite 구간·반복·play rate·dilation을 bake했다. 모든 시퀀스는 `Animations/Playback/A_EN_PLAY_*`, `RateScale=1.0`이며 원본 중복 UE 시퀀스는 없다.
- fresh asset/RAW·COMPRESSED pose 감사와 일반 UnrealEditor D3D12/SM6 렌더 검증을 통과했다. WildDog shader 12개와 BP 3개, WildBoar shader 9개와 BP 3개의 compile/reload 및 세 coat 표시를 확인했다. BP는 시각 조립 Actor이며 AI/전투/physics/custom notify 실행은 범위에 포함하지 않는다.
- 정본은 [WILD_DOG_EXTRACTION_2026-09-15.md](WILD_DOG_EXTRACTION_2026-09-15.md)와 [WILD_BOAR_EXTRACTION_2026-09-15.md](WILD_BOAR_EXTRACTION_2026-09-15.md)다. 전용 cooked shader graph와 WildDog BoneMod의 실행 의미는 metadata/raw archive에 보존한 미구현 범위다.

## 2026-09-15 Enemy 에셋 라이브러리 구조 정리 완료

- `/Game/_Art/Enemies`의 UE 에셋 1,940개를 현재 사용 구조로 정리했다. 살아 있는 21개 package는 UE rename API로 이동했고 실제 에셋 삭제는 0개다. 영향 참조 678개는 이동 전 외부 SHA-256 백업을 만들었다.
- `HeinMach/Empire`의 공용 장비·skeleton·pose carrier는 `HeinMach/Shared`, 옛 최상위 `HeinMach/HalberdElite`는 `HeinMach/Humanoids/HalberdElite`, 인간형 공용 애니메이션은 `HeinMach/Shared/Animations/Playback`으로 합쳤다. `MageHard` BP/mesh는 basename을 유지한 채 `OtherRegions/Humanoids/Mage`에 합쳤다.
- 최초 빈 leaf 37개와 이동 후 빈 상위 계층을 하위부터 제거해 총 63개 디렉터리를 정리했다. 최종 empty/Legacy 명칭 디렉터리와 ObjectRedirector는 0개다. 과거 Legacy/Archive JSON은 근거 자료로 보존했다.
- fresh Unreal 감사에서 전체 목록·class, 영향 없는 package 1,262개 hash, 영향 자산 678개 로드, 애니메이션 1,354개·메시 35개·BP 28개 계약, 내부 dependency와 카탈로그 6개를 검사했다. 계약 오차/누락/redirector는 0이며 process exit 0이다.
- 정본은 [ENEMY_ASSET_LIBRARY_STRUCTURE_2026-09-15.md](ENEMY_ASSET_LIBRARY_STRUCTURE_2026-09-15.md), 현재 조회 자료는 `Content/_Art/Enemies/Metadata/Structure_20260915`이다. 캐릭터 C++/Player/Config는 이 작업에서 수정하지 않았다.

## 2026-09-16 DualAxeSword WeakAtk01 원작 시간축 표적 확인

- 원작 `AC_Kazan_DualAxeSword_Com_WeakAtk01`의 segment와 213-point Dilation mapping을 직접 확인했다. source `FastAtk01_M1`의 `0–3.53 s`는 실제로 `3.4326434 s`에 재생되며 table 인접 진행률은 약 `0.911179–1.417051x`다.
- 조사 정본은 [DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md §7](DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md#7-2026-09-16--weakatk01-구간별-재생-속도-표적-확인), 수치 report는 `Saved/ImportReports/Khazan_DAS_WeakAttack_Timing_20260916.json`이다.
- P1.5 적용안은 mapping을 별도 playback AnimSequence에 bake하고 runtime 배율을 `1.0`으로 유지하는 것이다. 이번 확인에서는 Content asset, 게임 C++/BP를 수정하거나 Editor에서 import/build/PIE하지 않았다.

## 2026-09-16 DualAxeSword Weak Attack 콤보·Root Motion 추가 판정

- 원작 Skill Blueprint와 Composite를 대조해 표준 1–4타와 해금 5타 source를 확정했다. 2타는 `FastAtk02_M1`이며 사용자가 처음 고른 `FastAtk02_Loop`는 표준 단계에 참조되지 않는 별도 variant다.
- 1–4타 source metadata의 `bEnableRootMotion=true`, `bForceRootLock=true`를 확인했다. 1–5타 PSA Root track의 계산 변위도 모두 0이 아니며, 사용자의 모든 스킬 Root Motion 방침에 따라 파생 playback Sequence의 Root를 제거하거나 `Enable Root Motion=false`로 바꾸지 않는다.
- 최신 근거는 [DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md §8](DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md#8-2026-09-16--weakatk-콤보-source와-root-motion-추가-확인)이다. P1.5는 Root 포함 1타 playback Sequence와 combo Montage 골격을 사용자 적용하는 단계이며, 실제 Content asset/C++/BP/build/PIE는 아직 변경·검증하지 않았다.
## 2026-09-16 DualAxeSword 원본 시간축 복원 준비 완료·임포트 대기

- 원작 AnimSequence 457개와 DualAxeSword skill AnimComposite 397개를 전수 대조했다. 현재 source 444개는 모두 원본 sample count/길이/sample rate와 다르며, 비로코모션 기존 337개 교체·누락 source 13개 생성·Composite playback 360개 생성의 710개 write manifest를 확정했다.
- 활성 Dilation Composite는 전체 253개, 현재 스켈레톤으로 생성 가능한 범위에서는 250개다. segment trim/rate/loop와 위치별 Dilation을 pose 시간축에 bake하며 캐릭터 Root 움직임은 현재 스켈레톤 최상위 `C_P_Kazan`으로 옮겨 실제 Root Motion 추출이 가능하게 하는 계약이다.
- 현재 ABP가 직접 쓰는 locomotion 9개와 semantic/runtime locomotion AnimSequence를 합친 280개는 검사만 하고 보호한다. 24 fps + RateScale 1.25로 유효 cadence는 30 fps지만 원본과 key 수/유효 길이/root 설정 차이가 있어 후속 별도 결정을 요구한다.
- 실제 UE package write는 아직 시작하지 않았다. 열린 일반 Editor를 저장·종료한 뒤 기존 337개 hash backup, 10개 pilot, 전체 batch, 710개 fresh pose 및 locomotion hash audit 순으로 실행한다. 상세 정본은 `DAS_ANIMATION_RESTORATION_2026-09-16.md`다.

### 2026-09-16 DualAxeSword import preflight 통과

- UE 5.8 읽기 전용 commandlet에서 준비된 710개 전부의 pose hash/shape, skeleton track, root topology 이관, rational frame grid, destination 보호 경계를 검사해 exit 0/pass를 확인했다.
- 이 단계는 Content package를 저장하지 않았다. 실제 임포트는 열린 일반 Unreal Editor를 Save All 후 종료한 다음 기존 337개를 별도 hash 백업하고 시작한다.

## 2026-09-16 DualAxeSword 원본 시간축·미사용 로코모션 임포트 완료

- [범위 정정] 앞 절의 locomotion 280개 전체 보호/710개 manifest는 사용자 정정 전 기록이다. 현재 참조 9개만 보호하고 미사용 locomotion 271개를 복원했다.
- [검사] 현재 참조 9개는 24 fps × `RateScale 1.25`로 유효 30 fps다. 원본과 sample 수·유효 길이 차이는 남으며, AnimNotify event 0개/Sync Marker 37개를 확인했다. 9개 package SHA-256은 작업 전후 동일하다.
- [완료] 원본 source 457개, 미사용 파생 locomotion 164개, 원작 이름 Composite playback 360개, 총 981개를 Unreal Content에 저장했다. 기존 교체 608개, 신규 생성 373개다.
- [이름] 기존 source/InGame/Runtime package 이름을 유지했고 Composite playback basename도 원작 `AC_...` 이름을 그대로 사용했다.
- [Root Motion] 캐릭터 playback은 Root를 포함한 pose를 원작 시간 mapping으로 bake하고 `C_P_Kazan` root로 이관했다. Root Motion 활성 630개, Force Root Lock 600개가 최종 manifest 계약과 일치한다.
- [검증] preflight 981/981, checkpoint import 981/981, fresh-process final audit 981/981 모두 passed다. final audit failure 0, backup file 608개 및 보호 locomotion 9개 hash 검증을 통과했다.
- [백업/정본] `Saved/ArtBackups/DAS_Animation_PreTimingFix_20260916_182555`, [DAS_ANIMATION_RESTORATION_2026-09-16.md](DAS_ANIMATION_RESTORATION_2026-09-16.md), `Saved/ImportReports/Khazan_DAS_AnimationFinalAudit_20260916.json`이 복원·검증 정본이다.
- [경계] Object/Missile 또는 미추출 Design 무기 source를 쓰는 Composite 37개는 캐릭터 animation으로 잘못 만들지 않고 metadata-only로 유지했다. C++/Blueprint/Montage 연결과 PIE 품질 검증은 아직 별도 단계다.

## 2026-09-17 DualAxeSword Root Motion 이동량 V4 교정 완료

- [판정 정정] 2026-09-16 감사는 시간축·pose·package 계약만 확인했고 CharacterMovement 월드 이동을 확인하지 않아 이동 품질 판정으로는 불충분했다.
- [원인] Composite segment/loop 경계의 절대 Root reset과 `SK_Khazan`의 삽입 root `C_P_Kazan` scale `100`을 고려하지 않은 Root Motion 추출 단위가 각각 경계 역이동과 약 100배 이동을 만들었다.
- [수정] Composite 351개의 Root delta를 UE `FTransform` 순서로 누적하고, Root Motion 활성 플레이어 애셋 630개의 이관 root translation만 `0.01`로 정규화했다. Mesh scale `0.009`, runtime Root Motion 배율 `1.0`, rotation/scale/비Root pose는 유지했다.
- [보호] 현재 `ABP_Player` 참조 locomotion 9개는 수정하지 않았고 final audit에서 SHA-256 9개가 모두 일치했다.
- [적용] 메인 Content 981/981 배치 처리 완료. 630개가 V4로 재작성됐고 351개는 이미 현재 계약이라 검증 후 건너뛰었다. 애셋 이름과 package 경로는 유지했다.
- [검증] V4 preflight, 메인 import, 별도 fresh final audit가 모두 passed/failure 0이다. 격리 CharacterMovement PIE에서 `FastAtk01_M1`은 `118.39194 cm`로 원본 기반 기대값 오차 `0.00035 cm`, 합성 공격 경계와 종료는 `135.0 cm`로 오차 `0 cm`였다.
- [보고서] `Saved/ImportReports/Khazan_DAS_RootMotionScaleImport_20260917.json`, `Khazan_DAS_RootMotionScaleFinalAudit_20260917.json`, `Khazan_DAS_RootMotionPIEProbe_20260917.json`. 상세 정본은 [DAS_ANIMATION_RESTORATION_2026-09-16.md](DAS_ANIMATION_RESTORATION_2026-09-16.md)의 2026-09-17 절이다.
- [남은 품질 검증] 실제 WeakAttack Ability/Montage 연결 후 1–5타 화면 검수와 source에 실제로 포함된 장거리 flash 기술의 targeting/Motion Warping 적합성 검토다. 현재 수치 감사만으로 모든 기술의 최종 연출 품질까지 완료했다고 보지 않는다.

### 2026-09-17 Root Motion의 임시 Mesh scale 전제 제거

- 앞 절의 Mesh scale `0.009` 기반 월드 환산은 당시 런타임 관측 기록일 뿐 애니메이션 에셋 계약이 아니다. 현재 `0.009`를 animation preparation/import 입력으로 사용하는 코드와 최신 보고서는 없다.
- V4 보정 `0.01`은 라이브 `SK_Khazan`의 `C_P_Kazan` reference scale `100`의 역수다. preflight/final audit가 실제 Skeleton과 manifest의 역수 관계를 검사하도록 갱신했다.
- asset-space 전수 검사 968개/Root Motion 630개 failure 0, component scale `0.005`·`0.01`·`0.02`의 격리 CharacterMovement PIE 6개 probe가 모두 통과했다. 정본 보고서는 `Khazan_DAS_AssetSpaceMovementAudit_20260917.json`과 `Khazan_DAS_RootMotionScaleIndependencePIE_20260917.json`이다.
- 현재 V4 Content는 Skeleton 계약에 맞으므로 재임포트하지 않았다. 컴포넌트 scale 변경은 에셋 재가공 사유가 아니며, Skeleton의 삽입 root reference scale/topology 변경만 preparation 재실행 사유다.

### 2026-09-17 DualAxeSword Composite playback exact 60 Hz 교정

- [원인 정정] 이전 Composite 생성식이 정수 interval 수와 cooked 실수 길이를 동시에 보존한 뒤 `intervals / duration`을 FPS로 기록해, 360개 중 359개의 sample rate가 `60/1`이 아니었다. Dilation 가감속과 sampling rate를 분리하지 못한 파이프라인 결함이다.
- [적용] `PlaybackDerivation=CompositePlayback` 360개 전체를 exact `60/1`로 재표본화했다. frame 수는 `round(old duration × 60)`, 길이는 `frames / 60`이며 endpoint pose/Root Motion과 기존 property/package/name을 보존했다. source/locomotion cadence는 이번 대상이 아니다.
- [WeakAttack] 1–5타는 각각 206/200/298/269/156 frames이며 모두 Root Motion·Force Root Lock 유지다. 현재 1번만 든 `AM_DAS_WeakAtkCombo`의 segment cache와 Montage 길이도 `3.4333333969 s`로 갱신했다.
- [보호] 수정 전 360개와 Montage는 `Saved/ArtBackups/DAS_Composite_PreExact60_20260917_184000`에 361/361 hash 검증 백업했다. Character Mesh Component scale은 변환 입력으로 사용하지 않았다.
- [검증] import 360/360, fresh-process exact-60 final audit 360/360, backup 361/361이 모두 `passed`다. 최종 보고서는 `Khazan_DAS_CompositeExact60_{Preflight,Backup,Import,FinalAudit}_20260917.json`, 상세 정본은 [DAS_ANIMATION_RESTORATION_2026-09-16.md](DAS_ANIMATION_RESTORATION_2026-09-16.md)의 exact 60 Hz 절이다.

## 2026-09-29 Enemy LockOn anchor read-only 감사

- [확인] Yetuga, ApesStoneHandElite, WildDog, WildBoar의 현재 저장 SkeletalMesh 소켓과 BigBear의 현재 소켓 부재를 UE 5.8에서 읽었다. 공통 `LockOnTarget` 소켓은 없다.
- [원작 근거] 인간형·Yetuga·Apes·Dog·Boar Character metadata에 캐릭터별 `xxLockOnSphereComponent`가 있고 다수 CDO의 `bUseRotToTargetLockOnSphereLocation=true`를 확인했다. BigBear `SourceClosure`도 해당 component export type을 확인한다.
- [판정] `LookAt01`은 머리 시선 소켓이고 별도 LockOn 컴포넌트가 있으므로 LockOn 정본으로 사용하지 않는다. gameplay에서는 Monster별 SceneComponent 기준점을 둔다.
- [정본] 상세는 [LOCKON_TARGET_ANCHOR_AUDIT_20260929.md](LOCKON_TARGET_ANCHOR_AUDIT_20260929.md), 요약 report는 `Saved/ImportReports/KZ_LockOnTargetAnchorAudit_20260929.json`이다.
- [보호] 게임 Source와 Content asset은 수정·저장하지 않았다. UE 검사 script는 완료됐고 commandlet exit 1은 기존 `GameFeatureData` ensure 때문이다.

## 2026-09-29 HeinMach DualAxeSword 시작·진행 경로 플레이 가능화 완료

- 원본 `HeinMach_Spawn_Main01/MISSION01_START`를 `HM_Tutorial_PlayerStart_DualAxeSword`로 확정했다. 두 인간형 tutorial anchor와 맨손 오프닝 제외를 유지했다.
- Landscape 48개와 source 판정 prop 8,987개의 collision을 저장하고, `HeinMach_Chrcollision`의 활성 비degenerate wall 2,281개, Nav bounds 242개, NavArea_Null 26개, 원작 NavLink 14개를 복원했다.
- 원작 `xxAutomationTestActor_1`의 63 MoveTo/1,485점/1,422구간을 전수 검증했고, 복원 Recast gap 10곳은 원본 route 기반 forward link로 연결했다. 전 점·전 구간과 첫 tutorial route가 통과했다.
- PIE에서 DualAxeSword R/L mesh가 부착된 `BP_Player`가 `IA_Move`로 약 `706.74 cm` 이동한 뒤 지면 상태였고 hidden route wall의 Pawn 차단이 확인됐다.
- 상세 수치·출처 구분·임시 보정·후속 gameplay 경계는 [HEINMACH_PLAYABILITY_COLLISION_20260929.md](HEINMACH_PLAYABILITY_COLLISION_20260929.md)와 `Saved/ImportReports/HeinMach_Playability_RuntimeVerification.json`이 정본이다.

## 2026-09-30 Character camera mount read-only 감사

- 현재 Player mesh의 `Cine_Cam_Start`와 `Cine_Cam_End`는 authored socket이 아니라 `Root` 직속 reference bone이다. 두 이름 모두 UE scene attachment API가 유효한 attach 지점으로 판정한다.
- 원작 StormPass Level metadata에서 별도 `CineCameraActor1`이 Player skeletal component의 `Cine_Cam_End`에 붙은 직접 사례를 확인했다. `Cine_Cam_Start`의 실제 사용처는 저장 Level 집합에서 확인되지 않았다.
- Yetuga와 Apes의 `LookAt01`은 머리 시선 socket이며 camera mount로 판정하지 않는다. Yetuga 본체와 IceRock 보조 mesh, BigBear를 함께 확인했으며 Yetuga/BigBear의 현재 Blueprint에는 camera/spring arm component가 없고 원작 Skeleton metadata에도 camera/cine 명칭 socket은 없다.
- 현재 일반 camera는 Player capsule 아래 SpringArm과 Camera로 조립되며 animated mesh에 붙지 않는다. `KZLockOnComponent`는 view/control rotation만 갱신하고 camera를 target에 attach하지 않는다.
- 상세 근거는 [CHARACTER_CAMERA_MOUNT_AUDIT_20260930.md](CHARACTER_CAMERA_MOUNT_AUDIT_20260930.md), report는 `Saved/ImportReports/KZ_CharacterCameraMountAudit_20260930.json`과 `KZ_OriginalCharacterCameraMountAudit_20260930.json`이다. 게임 Source/Content asset은 수정·저장하지 않았다.

## 2026-09-30 HeinMach Player 상대 스케일 원본 대조 (읽기 전용)

- 원본 `BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Model/C_P_Kazan.psk`의 `PNTS0000` 45,751점에서 Z 최소 `1.670107 cm`, 최대 `201.293518 cm`, 경계 높이 `199.623411 cm`를 직접 계산했다. 원본 `HeinMach_Cine_LevelEvent02`의 `C_P_Kazan2_6` actor는 scale `(1,1,1)`이며 skeletal component에 별도 `RelativeScale3D` override가 없다. 이 컷씬 actor는 게임플레이 Player CDO의 직접 대체 근거가 아니다.
- 원본 `BBQ/Content/Art/World/World_Model/Prop/Tree/WP_STA_ThornTree_BIG_003.usda`는 `metersPerUnit=0.01`이고 경계 크기가 `(1095.45545, 667.08045, 509.59073) cm`다. 복원 맵의 동일 메시 경계 크기 `(1095.455444, 667.080444, 509.590729) cm`와 일치하며, actor scale `0.5640706`도 원본 HeinMach 배치 metadata와 일치한다. 따라서 확인한 환경 표본에는 추가 100배 배율이 없다.
- 현재 `/Game/_Art/Player/Character/Meshs/SKM_Player`의 로컬 경계 높이는 `19791.514145 cm`이고 `/Game/_Art/Player/Character/Meshs/SK_Player`의 삽입 최상위 본 `C_P_Kazan` reference scale은 `(100,100,100)`이다. 해당 현행 임포트 topology를 원본 cm 단위에 맞추는 Mesh Component 역배율은 **`(0.01,0.01,0.01)` = `1/100`**이다. 이는 원작에 직렬화된 `RelativeScale3D=0.01` 직접 확인값이 아니라 원본 단위와 현재 임포트 topology에서 계산한 값이다.
- 현행 `0.009`에서는 경계 높이 약 `178.124 cm`, 계산값 `0.01`에서는 약 `197.915 cm`다. 원본 PSK의 `199.623 cm`와 남는 약 `0.86%` 차이는 서로 다른 메시/포즈의 AABB 비교이므로 그 차이를 맞추려 `0.0100863`으로 튜닝하지 않는다.
- 읽기 전용 UE commandlet 보고서는 `Saved/ImportReports/HeinMach_PlayerScaleAudit_20260930.json`이다. 맵 SHA-256 전후 동일(`20FE65479279A9BD12E631FDE55A4237861C14EBF7EA3BE445544FCADA453BCE`); Player/맵/애니메이션 asset 및 Source 변경과 `0.01` PIE 적용 검증은 하지 않았다.

## 2026-09-30 `SK_Player` 최상위 본 `100 → 1` 에디터 편집 가능성 (설명만)

- 현재 본 인덱스 0은 `C_P_Kazan`이며 reference scale은 `(100,100,100)`이다. 원본 PSK의 `Root`는 별개이며 현재 `C_P_Kazan → Root → Bip001` 계층이다. 현행 `SKM_Player` 로컬 경계는 약 `19791.51 cm` 높이라 단순히 Skeleton의 숫자만 1로 바꾸는 것은 약 `200 cm`짜리 임포트 메시/바인드 계약을 동시에 만드는 조작이 아니다.
- UE 5.8 Skeleton Editor의 일반 Bone Manipulation은 애니메이션 미리보기 변경으로, 창을 다시 열면 원래 transform으로 복귀한다. `Skeletal Mesh Editing Tools`의 Skeleton Editing은 영구 본 편집을 지원하지만 현재 공유 Skeleton의 reference pose를 바꾸는 작업이며 메시 geometry·skin bind·애니메이션·소켓·physics를 함께 검증하고 필요한 데이터를 이관해야 한다. 참고: Epic [Skeleton Editor](https://dev.epicgames.com/documentation/unreal-engine/skeleton-editor-in-unreal-engine), [Skeleton Editing](https://dev.epicgames.com/documentation/unreal-engine/skeleton-editing-in-unreal-engine).
- 현재 Root Motion preparation은 삽입 최상위 본 scale `100`의 역수 `0.01`을 실제 Skeleton에서 읽어 적용하고 preflight에서도 검사한다. 본을 1로 바꾸면 기존 계약은 유효하지 않다. 현 목표가 HeinMach에서 원본 크기를 맞추는 것뿐이라면 Mesh Component 상대 스케일 `0.01` 변경이 별도 애니메이션 이관을 요구하지 않는 경로다.
- 이 절은 설명/검토만 기록한다. 게임 Skeleton·SkeletalMesh·AnimSequence·Blueprint·Source는 수정하지 않았고, 최상위 본 1배 이관/PIE 검증도 수행하지 않았다.

## 2026-10-01 StormPass Blade Phantom 두 보스 환경 폴리싱 적용

- 정본: [STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md). Phase1 성채 홀과 Phase2 숲/landscape는 같은 보스 좌표 영역의 원작 sublevel 변형으로 확인했다. 원본 진입·보스 spawn·컷씬 staging을 구분해 editor-only 마커 5개와 검수 카메라 2개를 저장했다.
- 기존 root/child 배치, foliage 3,218 instance 및 landscape 16 component를 보존했다. 렌더 슬롯 3,143개의 source→UE 대응을 검증하고, native surface MI 188개를 페이즈 전용으로 분리해 원작 WEP global 값을 적용했다. DeepGray/DeepNight sky, cloud off, 페이즈 sun/sky/fog 및 BossClear PP enabled 조건을 연결했다.
- 누락된 원본 깃발 14개와 하위 light 28개를 추가하고, 원본 배치/텍스처의 native fire·화염벽 47곳을 보완했다. 기존 Phase2 fog sheet 7개에는 원본 FogSheetColor를 native bridge로 연결했다. 원작 VM/cloth/custom shading 완전 포팅과 구분하며 임시 exposure·광도·FX 크기/시간 값은 metadata policy에 명시했다.
- `L_StormPass_Environment` 저장/실제 World 재로드 후 Phase1/2의 geometry/material/slot/추가 render/표시/environment 검사가 통과했다. 초기 actor 14,426 → 최종 14,522, 원래 arena actor 누락 0. 최종 저장 검수 모드는 Phase1이며 source phase를 동시에 켜지 않는다.
- 플레이어·HeinMach·게임 C++는 수정하지 않았다. 기존 사용자 변경과 작업 중 외부에서 갱신된 Engineering 문서를 보존했다. 자동 gameplay phase transition, 원작 water-spline Niagara DI 9개와 FX/cloth 실행 그래프의 완전 복원은 이번 완료 범위가 아니다.

## 2026-10-01 StormPass 페이즈 좌표 설명 보완 (읽기 전용)

- 원본 streaming entry와 물 actor root를 재확인했다. 두 source phase의 저장 배치 좌표 영역은 겹치며, 성채 홀과 숲/landscape라는 실제 전투 환경은 다르다. 두 streaming entry에는 `LevelTransform`이 직렬화돼 있지 않다. 원작 runtime offset/teleport와 정확한 전환 호출 순서까지 확인한 결론은 아니다.
- 두 ArenaReference 마커는 하나의 원본 공통 `TargetPoint_Boss` 복제 표식이며, ReviewCamera도 같은 비교 시점이다. 카메라 선택만으로 페이즈 환경이 바뀌지 않는다. 기존 `view('boss_phase_1'/'boss_phase_2')`를 사용한다. 자동 gameplay 전환은 미구현이다.
- 상세 보완은 [폴리싱 정본 하단](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md), 데이터는 `BladePhantom_ArenaPolish_20261001/PhaseCoordinateClarification.json`에 추가했다. 이번 확인은 World 읽기와 metadata/문서 기록만 수행했으며 게임 파일은 변경하지 않았다.

## 2026-10-01 StormPass Phase1 과노출·흰빛 재검토 적용

- 원작 Phase1 전투 스크린샷 3장을 직접 비교해 이전 흰 광역 보조광/과노출을 수정했다. [폴리싱 정본의 Phase1 밝기 재검토 절](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md)에 source field와 native 보정값을 구분했다. 기존 3 EV는 임시 2.25 EV로 대체하고 13 root/28 child light의 광도·falloff adapter, sky intensity, PP를 `PolishPolicy.json`에 모았다. 원작 photometric 단위 확정값은 아니다.
- 원작 WEP의 붉은 volumetric fog는 에디터 `r.VolumetricFog=0` 때문에 빠져 있었다. 검수 전환의 Phase1 분기에서 session CVar를 켠다. 실제 `sg.ShadowQuality=1`; UE 5.8의 Shadows High 이상이 해당 기능을 켜는 기본 품질 분기다. project/scalability INI는 바꾸지 않았다.
- 원본 Phase1 core fire atlas RGB × 실제 core emitter StartColor `(0.964706,1,0)`를 연결했다. parent/MI/texture 각 2개만 저장했다. color texture의 sRGB는 source flag 직접 확인값이 아니라 native 색 해석이며 compression 이후 설정·저장·readback으로 확인했다.
- 두 페이즈 전환 후 Phase2 point light 11개/PP 원상 유지, 표시·environment 검사 실패 0. Phase1 맵 저장/실제 World 재로드 후 light 41개와 PP 및 PlayerStart pose 유지, actor 14,522, 임시 capture 없음. 원본 geometry/추가 render/표시 감사 실패 0.
- 최종 화면: `Saved/ArtReviews/BladePhantom_20261001/Phase1_LightReview_Delivery.png`. metadata는 `Phase1LightReviewSourceManifest`, `Phase1LightReviewBefore/After`, `LightReview_ReloadVerification`, `LightReview_*Reloaded.json`을 먼저 확인한다. 현재 전달 맵은 Phase1이다. 게임 C++/캐릭터/HeinMach와 사용자 메시 배치를 수정하지 않았으며 관련 없는 dirty Dodge asset도 저장하지 않았다.

## 2026-10-02 StormPass 두 전장 나란히 배치 완료

- 사용자 요청으로 현행 `/Game/Maps/L_StormPass_Environment`에서 Phase1 성채는 유지하고 Phase2 전체 1,120 actor를 +X 20,390 cm 평행 이동했다. 이전 source 동일 좌표/상호 배타 표시 설명은 source 기록이며, 현재 authoring에서는 두 전장과 bounded PP를 동시에 활성화한다. 20 m 여유는 원작 값이 아닌 명시적 임시 편집 간격이며 실제 bounds로 이동량을 계산했다.
- `StormPass/01_BladePhantom/ArenaMarkers`에 주 마커 두 개: `SP_BP_Phase1_ArenaReference_TargetPoint_Boss` `(162650,51600,695)`, Phase2 동명 마커 `(183040,51600,695) cm`. Outliner `ArenaReference` 검색/선택/F로 접근한다. 마커는 editor-only 참조이며 runtime spawn이 아니다. 기존 `view('boss_phase_1/2')`와 route variant 명령은 이제 양쪽을 표시한 채 시점만 바꾼다.
- Phase2 terrain의 복제 native material RootXY도 +X 20,390 cm 이동해 UV를 유지했다. 별도 channel 1 sun과 Phase2 local lighting channel을 사용하지만 sky/fog/간접 GI는 Phase1 전역 환경을 공유한다. 기존 Phase1 밝기 보정을 보존했다.
- 기존 중심 지면 미검출을 보완해 invisible `BlockAll/QueryAndPhysics` 지원 바닥 2개를 각 blood-water core에 추가했다. 현재 바닥 bbox/물 범위 기반 authoring 근사이며 원작 collision 복원이 아니다. 저장/World 교체 재로드 후 지면 trace 8/8, marker/PP/landscape/PlayerStart 계약 실패 0; actor 14,525. 실제 Character/AI PIE·전 레벨 NavMesh 검증은 수행하지 않았다.
- 정본/수치·검증 한계: [폴리싱 정본의 2026-10-02 절](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md). 자료는 `Metadata/BladePhantom_SideBySide_20261002`, 최종 보고서 `ReloadVerificationWithCollision.json`, 백업은 `Saved/ArtBackups/StormPass_SideBySide_20261002`. 현재 사용자 맵 이동/PlayerStart/삭제 메시와 관련 없는 C++/BP 변경을 보존했다.


## 2026-10-02 InGame DAS 재생 속도 보정 완료

- [실제 적용] 기존 InGame AnimSequence 140개 중 22개에 기본 소비 분기의 segment rate/Dilation을 full-source 범위로 bake(60/1, RateScale 1), 18개는 기존 24 fps 키를 유지하고 원작 cadence 30/24=1.25를 적용했다. 이미 맞는 100개는 패키지 hash 동일.
- [연결 데이터] 강공격 Montage 2개의 segment/section/notify/branching cache 시간을 새 포즈 시각으로 이관했다. 반복/서로 다른 배속을 가진 UltimateSlash Air/Loop는 기존 V5 완성본 2개를 InGame에 복사했다. 최종 시퀀스 142/Montage 5, scope package 152. 새 Ability 연결 변경 없음.
- [검증] 저장 후 새 UnrealEditor-Cmd의 RAW/COMPRESSED·전 본 5개 sample·time/grid/root/property와 Montage event 검사 passed. 기존 byte backup 150/150 검증, 범위 밖 animation 870개 크기/mtime 동일. 현재 Player mesh scale 0.01을 재확인했고 이 작업은 공간 배율/Skeleton/mesh/game C++/BP에 쓰지 않았다. 동시 다른 편집의 Config/BP_Player/DodgeAttack Montage 차이는 보존했다.
- [정본/자료] [INGAME_DAS_PLAYBACK_CORRECTION_2026-10-02.md](INGAME_DAS_PLAYBACK_CORRECTION_2026-10-02.md), Metadata/InGamePlayback_20261002의 PlaybackPlan/OriginalTimingFields/ApplyReport/FreshProcessAudit. 기본 분기 선택·full-source 미소비 구간·60 Hz 양자화·다른 소비 분기·PIE 미검증 범위가 명시돼 있다.


## 2026-10-02 두 레벨 source 룩 복원 — 저장·검증 결과

- 정본은 [LEVEL_LOOK_RESTORATION_2026-10-02.md](LEVEL_LOOK_RESTORATION_2026-10-02.md), 보고서는 `Rendering/Metadata/LookRestoration_20261002`다. 현재 `/Game/Maps`의 두 맵과 native 렌더 에셋 저장 완료. 원작 실행 shader port / 최종 외형 일치 완료라는 판정은 아니다.
- StormPass actor 14,525→2,547: 새 local fog 2개 추가 및 불필요한 관리 actor 11,980개 삭제. 두 전장/source foliage/Phase2 terrain 16개·mountain 및 필요한 Main landscape 4개 보존. Stage marker는 기존 P1 `(162650,51600,695)`, P2 `(183040,51600,695)`. mission route Start는 P1 source entry `(162240,51600,296.66724)`로 이동했다.
- Phase2 source DeepNight sky/sky light/fog, 붉은 covering/glow/pollution consumer, 깊이 기반 푸른 haze 및 native PP 조정 저장. sun의 Pawn channel 0 지원/위치 mask/forward priority 보정. 기존 P1 PP/torch/source prop pose는 보존하지만 전역 sky/GI는 P2 기준 공유여서 이전 P1 전체 외형 불변을 주장하지 않는다.
- HeinMach source weightmap terrain 2개/11·12 layer와 기존 47 terrain actor, source WEP PP 7개/OP sky/light/fog 적용. 사용자의 Start/수동 배치/18+109 tombstone 유지. inherited MI 3개의 roughness/metallic channel 교정.
- native toon/outline을 8 환경 MI에 연결. Player/Enemy visual BP 29개·skeletal template 58개에 custom depth/stencil 254, project `r.CustomDepth=3`. source BBQCartoon/HalfCartoon의 정확한 renderer와 NTP 전체 함수는 확보하지 못했다.
- live 및 fresh-process readback: missing slot 0 / 검사한 packed mismatch 0, ground support 8/8, 보존·삭제 계약 통과. 마지막 fresh audit exit 0; native 주요 shader 9개 컴파일. 최종 viewport 룩 비교와 실제 Character/AI/보스 phase gameplay 검증은 미완료다. native 임시값은 위 정본과 `NATIVE`에 분리했다.

## 2026-10-06 HeinMach 후처리·하늘·강설 저장 및 game 검수

- 정본: [HEINMACH_WEATHER_RESTORATION_2026-10-06.md](HEINMACH_WEATHER_RESTORATION_2026-10-06.md). 사용자 지시대로 모든 Unreal 작업을 별도 숨김 background process에서 수행했다. Rider 실행 사용자 editor는 조작하지 않았다.
- 저장된 HeinMach는 9,610 actors(강설 1개 추가). source BSP PP 7개/81 faces·source sky pose 복원, PP override=false 처리 및 pre-exposure 계약 교정, 지역별 Sky/Cloud/Star/Nebula 연결, native 그림자 보정 적용. 다른 모든 actor pose/PlayerStart·기존 삭제 항목 보존 fresh audit 통과.
- 원본 FT_SnowTickle_03와 16³/8³ 벡터 bulk로 `NS_HM_SourceSnow_TwoLayers`의 두 GPU emitter를 구성했다. camera-centered world-space, source 크기/수명/alpha/속도 scale, Cave1 per-view 숨김 적용. 흰 사각형 원인이던 opacity mask RGB 혼입을 교정했다.
- 별도 actual game viewport에서 8,187 flakes+3,115 dust, 정상 auto activation/이동 camera spawn·동굴 snow 숨김 관측. 최종 PNG는 `Saved/ImportReports/HeinMachWeather_20261006/GameViewport_*`; SceneCapture/진단 PNG를 최종 적용 화면으로 사용하지 않는다.
- 최종 DX12 SM6/RTX3060Ti/1280×720 local CSV: GPU simulation median 0.04635 ms/P95 0.0535 ms, translucency ON/OFF median 차이 +0.0764 ms. 180/185 frames, 사용자 editor 동시 실행·Development 측정이다. shipping/전 route 성능 보장이 아니다.
- 4개 재질 명시적 SM6 recompile errors=0, 최종 saved-scene 계약 통과. 미사용 task trial/QA 9개는 referencer 0/byte backup 후 제거. 새 runtime C++/BP manager 없음. 게임 C++/BP/Config/애니메이션 및 StormPass에 이번 작업의 편집을 적용하지 않았다.
- 완전 원작 동일 판정은 보류: cooked shader body 부재로 native 대체식, ground collision/puff·dust field 회전·MaxBlizzard/전체 지역 snow 강도·wind 전환·Moon/Planet 활성화 및 같은 build 원작 controlled 비교는 미복원/미검증이다. source sky/PP 지역 전환과 snow 전체 지역 전환을 구분한다.

## 2026-10-06 후속 요청 — HeinMach editor 열람

- 사용자 직접 요청으로 미저장 여부를 확인하고 저장된 변경을 interactive editor에서 불러왔다. 요청 당시 실행 editor가 없어 새 PID 9596으로 HeinMach를 열었다. 최초 dirty map/content 0개, autosave 복구 대상 0개.
- map/전용 rendering asset 15개는 DeliveryVerification의 SHA 동일, 맵 actors 9,610과 현행 snow 시스템 연결 확인. 맵·게임 Source/BP/렌더 에셋을 저장하지 않았다. `LiveEditorReloadVerification.json` 참조.
- 현재 viewport PIE `Play` 상태로 사용자가 확인할 수 있도록 남겨 두었다. live PIE 강설 8,817 flakes/3,520 dust, dirty map/content 0개, screenshot 확인. `LiveEditorPIEVerification.json`과 [정본 후속 기록](HEINMACH_WEATHER_RESTORATION_2026-10-06.md) 참조. 이전의 “사용자 editor를 아직 재로드하지 않음”은 이 후속 요청의 확인 범위에서 대체된다.

## 2026-10-06 후속 요청 — 실사 중심·아주 약한 툰 룩 저장

- 최신 사용자의 미술 방향으로 HeinMach 기존 8 PP/6 지역 MI와 sun specular만 조정해 map+MI 7 package 저장. [새 룩 정본](HEINMACH_LOOK_REFINEMENT_2026-10-06.md)과 `Rendering/Metadata/HeinMachLookRefinement_20261006`을 우선한다. 원작 재현 수치와 이번 native 미술 선택을 구분한다.
- 강한 청색 틴트/무채색과 과한 character toon/outline을 줄이고 filmic grade·부드러운 명암·절제된 반사를 적용. current editor는 native 100% TSR, High texture/GI/shadow·Epic AA. console extras는 session override이며 공유 프로젝트 Config에 넣지 않았다.
- fresh serialization audit: 9,610 actor, 추가/삭제/pose 변경 0, 적용 전 사용자가 저장한 `PlayerStart` 보존. 4 shader compile errors0/기존 instruction count, MID 없는 actual saved-game PNG4와 GPU snow simulation median/P95 `.01755/.0226 ms` 확인. 전체 frame 60FPS 보장 또는 원작 shader 동일 판정은 아니다.
- 파일 잠금 해제 중 assistant의 live `DEBUG RESETLOADERS`가 PID9596 crash를 유발했다. 직전 dirty0/저장 데이터 보존, 사과 및 PID25196 최신 map 재열람·editor camera/품질 복구. 사용자가 재시작한 현재 PIE는 유지했다. 이 global loader command를 live editor에서 재사용하지 않는다.

## 2026-10-06 룩 조정 최종 전달 상태

- `HeinMachLookRefinement_20261006/DeliveryVerification` passed: map+6 MI만 변경, 다른 전용 package9개/backup7개 SHA 확인. `FinalLiveEditorVerification`은 PID25196 Idle/dirty0/actor9,610/100%·AA3·High 확인이다. 사용자가 Play를 종료했으며 해당 편집 상태를 유지했다. 앞 절 Play는 중간 관측이다.

## 2026-10-06 마지막 live 미저장 상태 정정

- 마지막 보고서 작성 시에는 map dirty1/content0으로 바뀌었다. `FinalLiveEditorVerification.json` 배열을 우선한다. 새 dirty 원인은 미확정, 추가 reload/Save All/discard 없이 보존했다. 미술 저장본 Delivery는 통과했으며 현재 live 미저장 상태와 구분한다.

## 2026-10-06 — Heal 사용 Equip Sequence의 InGame 이동

Engineering Heal 후속의 resource 결과만 기록한다. 기존 /Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Equip/CA_P_Kazan_DualAxeSword_Armed 및 _UnArmed 두 Sequence를 UE rename으로 /Game/_Art/Player/Animation/InGame/DAS/Equip으로 이동했다. 기존 메인 AssetRegistry referencers는 둘 다0이며 원래 file2개를 백업/hash 확인 후 제거했다. redirector가 남아 있다는 초기 계획과 구분한다. clip 길이1s/30frame31key/RateScale1/rootfalse·topology adapter를 유지했고 .01 Player/.009 weapon을 playback에 섞지 않았다.

Metadata/HealWeapon_20261006/EquipPSASource.json은 원본 FModel PSA ANIMINFO31samples/AnimRate31/hash, EquipAudit.log/SavedAssetAudit_Final.json은 기존·이동 후 TimelineReplacement 관측이다. export header `(31-1)/31`와 현 timeline1s를 혼동해 새 rate를 만들지 않았다. 원작 equip playback rate/Notify timing은 미확인이다. 실제 이관/hash/build 검증은 DeliveryVerification/AssetInstallManifest, runtime 결과는 Docs/Engineering/HEAL_WEAPON_PRESENTATION_20261006.md에 분리 기록했다. 다른 source animation을 이동하거나 재임포트하지 않았다.

## 2026-10-06 HeinMach 원작 사진 비교 — 메인 오류 수정 반영

- 최신 방향은 원작 분위기·색감·그림자·표면 룩 재현이다. [HEINMACH_REFERENCE_MATCH_2026-10-06.md](HEINMACH_REFERENCE_MATCH_2026-10-06.md)가 사진5장 분석/실제 수정/원본·계산·native 수치/검증·미완료의 정본이다. 이전 실사 중심 grade값은 이번 저장 범위에서 대체한다. 원작 전용 셰이더 및 완전 비주얼 동일 판정은 아직 미완료다.
- hidden 격리 작성→메인12package 선택 반영→메인actual game5시점/fresh audit 통과. 9,610 actors/모든 pose차이0, 현재 PlayerStart `(12022.196341630144,13909.267886166936,223.7105706322176)cm` 유지. 메인 원본11package byte backup/hash 확인, QA는 미반영. 사용자 Rider editor PID27916/DevMap/dirty0 read-only 확인; live reload/reset/Save All 없음.
- OP priority100→10으로 Blizzard1 가림 해소, sky stencil252의 가시성 깊이 판정 보완, 기존 PP를 BeforeDOF/TSR 이전으로 이동. motion blur/scene fringe0, snow/dust의 depth/velocity 출력 해제·A-only atlas 재검증. source palette 기반의 지역 haze와 절제된 toon/outline, native sun7000lux/angle5°/source OP specular`.01` 저장.
- 기존2 GPU emitter graph를 유지하고 새 NiagaraEffectType으로 spawn`.25` 적용. 같은 조건 count8600+2298→2382+784, GPU simulation median`.0164→.0138ms`; current snow ON/OFF translucency median차이`.0446ms`. 전체 frame44.4ms 수준/동시editor/Development 결과이므로60FPS 보장 아님.
- 실제 움직이는 run/translation4variants×65frames, native3+QA3shader errors0, main game fallback0 관측. input-driven 전체 대시/공격/급회전의 잔여TSR artifact와 원작 BRDF/rock detail·cover/foliage shading/wind/runtime weather 전체는 미검증·미복원이다.
- 저장자료 `Rendering/Metadata/HeinMachReference_20261006`의 Delivery/Install/FreshSavedSceneAudit/SourceMaterialAnalysis/PerformanceVerification을 우선한다. 기존cached자료와 표적추출13package 사용, 전수조사 없음. 비교 사진은 `Saved/ImportReports/HeinMachReference_20261006/BeforeAfter.jpg`, 메인사진 `final`.

## 2026-10-06 — DualAxeSword 전투·혈흔·눈/먼지 효과 저장 결과

- 사용자 직접 요청의 Art 추출/임포트 결과는 [DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md) 마지막 절이 정본이다. 목적지 `/Game/_Art/Effects`: DAS Core/Flow/Yaksha/Enchant, Combat GuardParry/AttackContact/Blood/HitReaction/Shared, Movement 표면별 Player/Monsters, Shared dependencies, Metadata로 정리했다.
- 원본 시각 2,313 package 및 binding 733 package raw/JSON, 600 package 교환 payload 모두 실패 0. 원본 effect notify 4,146/routing entry 3,426/physical surface 계약 16개를 보존했다. native 2,028 `.uasset`(ParticleSystem 751 포함) 생성·fresh load/reference/MI override 검사·파일 SHA 검증 완료. distribution table 80,874/색상 curve key 117 검사, real RHI 109 master shader errors 0, 대표 9 효과 PIE/45 PNG 통과.
- 원본 추출/지원 native 작성은 완료했으나 **요청 전체의 원작 동일 재생 복원은 미완료**다. Niagara 21/MaterialFunction 264는 stripped editor graph 때문에 source-only. 복원용 material의 원작 distortion/dissolve/VAT/전용 renderer 동일성, runtime socket/owner/buffer writer와 전투/표면 이벤트 연결은 미구현·미검증이다. 게임 C++/BP/Notify/기존 맵이나 사용자 live editor를 이 작업에서 바꾸지 않았다.
- source manifest/catalog와 `Content/_Art/Effects/Metadata/Extraction_20261006/DeliveryVerification.json`부터 재사용한다. 전체 재추출/재임포트를 반복하지 않으며 다른 동시 작업 변경은 이 작업 결과로 합산하지 않는다.

## 2026-10-06 — HeinMach 원작 횃불·화로·조명 메인 배치 완료

- [HEINMACH_TUTORIAL_FIRES_2026-10-06.md](HEINMACH_TUTORIAL_FIRES_2026-10-06.md) 마지막 절과 `HeinMach/Metadata/TutorialFires_20261006/DeliveryVerification`이 정본이다. 원작 플레이 구역 fire fixture 72곳: 기존37곳에 FX/조명 추가, missing spawner35곳에 파괴 전 static 외형/FX/조명 복원. inactive44 lights 및 cinematic3 제외, 파티클 없는 candle5 기존 외형 유지.
- FX95/PointLight100/새 fixture35/ground burn decal28 = 새 actor258, 총9,868. 원작 child transform·parameter·IES·색/거리와 기존 root 사용자 이동을 반영했다. 기존9,610 poses/PlayerStart와89 lights intensity/radius 보존 fresh main audit 통과. 기존 sky/weather/PP/terrain material·game C++/BP/Config 편집 없음.
- 원본 closure284/raw·JSON·payload 실패0, Cascade3/17 emitter/273 유도 distribution. UE4 DetailMode7→UE5 Epic15 호환 및 원작 ParamModes fixed array28개 교정, source DXT1 smoke R density·native exposure/burn 식 복원. stripped 원작 shader graph와 BP light runtime/Chaos 기능은 복원 완료로 판정하지 않는다.
- 72 native asset+map1 선택 설치/SHA73·원본 map backup 검증 passed. 최종 actual-RHI master8 errors0, fresh main audit passed, actual main game6시점/PNG12·live particle 재생/no fallback 통과. DevMap/StormPass SHA 동일. Outliner `HeinMach/Reconstructed/TutorialFires`.
- local ON/OFF/ON 각200 samples에서 GT Effects 추가 `.170975ms` 관측. 사용자 editor와 GPU 공유 및 shadow/base/TSR 편차로 GPU 비용은 미확정이며60FPS 보장이 아니다. 원작 동일 프레임 비교·기존 foliage/일부 기구 시야 가림은 남아 있다.
- 모든 authoring/렌더는 별도 숨김 UE, 마지막 live PID27916/DevMap/dirty0 read-only 확인. 사용자 editor reload/save/PIE/camera/종료 없음. 후속 변경은 최신 맵에 선택 적용하며 이번 installer/옛 stage 전체 맵을 재반영하지 않는다.

## 2026-10-06 — Engineering 몬스터 gameplay 파생 리소스 전달

기존 HeinMach Enemy Art BP/Playback library의 필요한4종 mesh/material/equipment/skeleton만 재사용했다. 원본 clip60개 SHA 보존, gameplay clone60을 /Game/Monsters/<Family>/Animations/InGame에 작성했으며 원본 키/FPS/RateScale 재임포트·retime은 없다. 기존 source skeleton3개는 현재 main 파일 재snapshot 후 montage DefaultSlot만 등록했다. skeleton/원본 데이터의 출처는 Metadata/MonsterAI_20261006/OriginalSkillAudit·Context·AuthoringPlan·Intake·RootPoseAudit·OriginalClipHashes, SlotBaseline/Before hash다.

새 Character BP는 /Game/Bluprints/Monsters, gameplay GA/DA/ABP/BS/Montage는 /Game/Monsters. Human body1.2/Heavy empty carrier1.3+갑옷 leader pose/Halberd전용1.0을 보존한다. 최소137package(새132/기존5)의 main 선택 반영/hash/build/saved load가 완료됐다. 기존 Player .01/.009와 original Art clip/assembly를 일괄 교체하지 않았다. AI·피해 제외·임시 수치·검증은 Engineering [MONSTER_AI_IMPLEMENTATION_20261006.md](../Engineering/MONSTER_AI_IMPLEMENTATION_20261006.md) 최신 완료 절에 분리 기록했다. 외형의 원작 완전 일치/연속 motion 품질은 이번 static/native 기능 검증과 구분한다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

`/Game/Maps/L_HeinMach_Environment`의46 native snow surface/2 material/field Actor를 실제 메인에 반영했다. 발·무기·몸 접촉에 둥근 높이 파임과 압축 재질을 적용, 기존9,868 poses/화로258 보존(총9,869). Main saved reload/native PIE Success04:22:07 UTC 및48 assetSHA passed. 원작 계수의 native cm 해석/임시 contact·rim·재질 값과 original shader/pixel 비교 미완료는 [눈 정본](HEINMACH_SNOW_DEFORMATION_2026-10-06.md) 마지막 절을 따른다. 지면 충돌/경로/성능은 Engineering 정본에 분리했다. 다른 Monster/PlayerParts 작업 완료 여부를 이번 결과로 승격하지 않는다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

최신 user 방향으로 눈 brush를 확대: 발40×32cm/무기100cm 반경, 둥근 눌림과 원형 크레이터다. assistant 임시 조정값이며 원작 값이 아니다. 현재 main map9,869poses/46surface/65micro/258fire 보존, main actual PIE06:28:20 UTC Success. 기존 material/48asset 재사용, 추가 asset0. 현재 결과는 HEINMACH_SNOW_DEFORMATION_2026-10-06.md의 후속 확대 절과 Saved/ImportReports/HeinMachSnow_20261006/BroadBrush20261007/FinalVerification.json. 새 설정은 user editor 작업 저장 후 재시작으로 확인한다. 이전 작은 brush 값을 현행으로 해석하지 않는다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

깊은 눈 후속 main 반영 완료. layer60/36/18cm, 발.7압축, rim12cm 및 normal 중앙차분. 실제 GPU 발40.5cm/무기58.0cm와 native contact PIE passed. 어시스턴트 임시값이며 원작 검증값이 아니다. 변경/범위/재시작/자료는 snow 정본 최신 절.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

실제 Main 반영 완료다. Archer 제외 HeinMach Humanoids4종 및 Yetuga/ApesStoneHandElite의 Art676, 기존 gameplay93을 purpose12폴더와 의미 이름으로 정리했다. 신규 gameplay44를 더해 현재813시퀀스, 기존 montage33과 신규22를 더해55montage다. Idle/Locomotion/Attack/Damage/Death/Guard/Alert/Equip/Interaction/Recovery/Prop/Pose이며 방향·단계·변형은 보존한다. A_EN_PLAY/중복 AC·CA·M·EN·Boss·캐릭터 접두사와 hash tail을 제거했다. 겹치는 direct source/Composite는 Original/Composite로 구분한다. CurrentAnimationLibrary.csv가 current→legacy→original source/frame/FPS/length/RateScale/root/options의 조회표다. 과거 export CSV는 historical 원본이며 수정하지 않았다.

813개 EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame을 저장·fresh Main readback했다. 4NPC의 기존 RootMotionFromMontagesOnly로 공격/End 몽타주 root delta를 CMC가 소비한다. Nav 보행은 기존 CMC/velocity pose/Foot Placement를 유지하며 RootMotionFromEverything 보행 구현이라고 부르지 않는다. Yetuga/Apes는 library/options 정리이지 신규 AI 구현이 아니다. index0/first track audit769의 Root765/Weapon_R1/B_Rock3을 유지했다. raw pose19M/곡선·재생률 비교와 compressed extraction tolerance를 구분한다. source pose/root 트랙·Skeleton topology/scale/Player .01·재생속도/재임포트 수정은 없다.

Rename참조 갱신 후 옛802 packages는 fresh registry/commandlet 및 Main hash 확인으로 실제 제거됐다. source assets의 imported actor/catalogue 참조도 갱신했다. 실패 fixup와 QA 로그를 지우지 않았다. Archer177개 hash는 전달 전후 동일하다. Main stock build·813 saved reload/dirty0를 완료했다. 자산별 분류·이름·원본 출처는 ENEMY_ANIMATION_ORGANIZATION_20261007.md 및 Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv를 따른다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Main Source3/? Contact55 material2/Preview map/UnrealEditor-KhazanSnowContact55QA_20261007.dll? ?? ????. ?? native PIE ?? ?? /Game/Maps/L_HeinMach_Environment_Contact55_20261007, fresh background Main PID24660, 12:08:02 UTC Khazan.Snow.PIE Success?. GPU ?? ?34.000cm/??50.000cm?? ?? canonical /Game/Maps/L_HeinMach_Environment? ?? ???? ???. ??? Main PID3528? HeinMach/dirty0/PIE???? ??? ???? ?? file lock? ????. ??? save/reload/PIE/camera/close? ???? ???. FinalVerification? success=false/preview_verified=true/canonical_map_pending=true? ??? Preview ??? ????.
???55/35/50cm?nominal full foot8?5cm/reach8cm? Preview?? ????. ????? Art Snow ?? ?? pending ?/Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/FinalVerification.json??. worker2256 ?? ??? ?? canonical? ?? ?????.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
사용자55/35/50cm·명목 foot full rim8×5cm/reach8cm의 현재 근거는 Art Snow 정본 이번 pending 절과 Contact55_20261007/FinalVerification.json이다. worker2256 대기 중이며 원본 canonical은 아직 미적용이다.


<!-- HeinMachGhosting_20261008_applied -->
## 2026-10-08 — HeinMach 이동 캐릭터 선명도·잔상 수정

실제 변경·원인·원작 수치와 native 튜닝 구분·RHI 비교·검증 한계는 HEINMACH_REFERENCE_MATCH_2026-10-06.md의 이번 절을 따른다. native100/TSR 이동 누적2와 캐릭터 파츠 mask 복원이 Main 적용/선택 reload·fresh runtime 검증됐다. 기존 PP BeforeDOF/blur0·의상 물리·Snow canonical pending 작업을 보존했다.


<!-- ApesYetugaBehaviorResearch_20261008 -->
## 2026-10-08 — Apes·Yetuga 패턴 원본/공개 자료 분석 완료

APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md 및 Metadata/EnemyBehaviorResearch_20261008을 따른다. 기존원본hash·공개전투표적프레임·공식patch·현행212asset경로를대조했다. original/cache/public/시간검증/report를새research영역에저장하고 도메인문서에분리기록했다. 게임에셋·원본ZIP·Root Motion옵션·재생률·Skeleton/scale은수정하지않았다. 분석완료와새AI구현/원작런타임일치검증을구분한다. 미관련Snow/렌더링/physics작업의완료·대기상태를이번연구로변경하지않는다.


<!-- HeinMachSnow_AttackContact_20261008_complete -->

## 2026-10-08 10:52 KST — Contact55 기본 HeinMach 반영·새 접촉 검증 완료

이전 Preview 성공·canonical 대기를 이번 새 전달로 완료했다. 기본 /Game/Maps/L_HeinMach_Environment는 현재 Contact55 material2와 최대55cm/발35cm/무기50cm·rim 포함 발 반경축8×5cm를 사용한다. material2의 바이너리·D/N/S·source weight/UV·mesh/collision·9868 source poses/fire258/snow46/micro65는 보존했고 맵의 기존 Snow owner에 contact profile2(4.56MiB payload)를 저장했다. 원작 직접 높이로 간주하지 않으며 사용자55/35/50 및 기존 임시36/18/rim12 구분을 유지한다. resource 재추출/새 머테리얼/texture/mesh 작성0.

무기는 기존 실제 Attack Ability 실행 중 지역 눈 표면에 닿을 때만 넓은 crater를 만들며 이동은 작은 발 파임이다. 세부 native 소유/계산/임시 접촉6cm·검증은 Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 이번 절을 따른다. fresh canonical MainPID652 native PIE Success01:45:35 UTC; 새 모듈/저장 profile2/기존 scene/settings 확인과 GPU 발34cm·무기50cm, partial/residual/range/cache/EndPlay 검증을 완료했다. 실제 활성 Player/4NPC Attack pose를 평가 후 고정한 접촉 fixture이며 모든 자연 montage 궤적·원작 pixel parity·GPU/shipping 최악 성능은 미검증이다.

정본 Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/{Delivery,FinalVerification,MainVerification,SurfaceProfiles,SurfaceProfileProof}.json 및 MainVerify.log/StagePIE.log. canonical SHA57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7, 선택 alias UnrealEditor-KhazanSnowWeaponContact20261008.dll. 이전 worker2256을 중지·archive했고 이전 PendingApplyStatus는 SupersededByAttackContact20261008, canonical_pending=false다. 옛 Delivery/Preview FinalVerification/PendingCanonical은 과거 증거로 보존하며 재적용하지 않는다. 사용자 에디터 save/reload/PIE/close는 실행하지 않았다. 마지막 UE 연결/프로세스는 없었고 다음 새 에디터에서 기본 맵을 확인한다.



<!-- HeinMachSnow_AttackContact_20261008_normal_rebuild_verified -->
## 2026-10-08 11:01 KST — 후속 일반 Main DLL 빌드도 새 접촉 검증 완료

전달 뒤01:49:41 UTC Main 프로젝트 native build가 새로 실행돼 normal DLL과 manifest가 갱신됐다. 이 빌드는 본 작업이 시작한 것이 아니며 되돌리지 않았다. 최신 전체 Main Source가 본 작업의 검증된 NativeBuildProof와 byte 일치하고 canonical/Source3/기존 보호 asset·Config도 동일함을 확인했다. 현재 manifest는 `UnrealEditor-Khazan.dll`, SHA `4ca0cc527b9d94c6812246befd974e5ce268ec5ece23207add6394d369cde354`다. 앞 절의 alias 선택·원래 DLL 보존은 당시 전달 사실이며 현재 선택 모듈 정본은 이 절이다. 이전 성공 Delivery/FinalVerification을 수정하지 않았다.

새 hidden MainPID19372에서 실제 normal DLL 경로·저장 canonical profile2/55cm·작은 발 범위/scene9,869를 재검증했고01:58:40 UTC `Khazan.Snow.PIE` Success 및 정상 종료했다. Player Run142/Dodge236 표본 maximum35/55, Player/4NPC active 공격 지면 양성/공중·비공격·취소 음성과 기존 GPU 발34/무기50cm/cache/EndPlay 회귀가 통과했다. 자료는 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/NormalMainRebuild_20261008`의 snapshot Delivery(not_a_delivery), MainColdBuild.log, MainVerification/Exit, MainVerify.log다. 이번 Snow 수정·canonical 반영은 완료이고 old worker/preview pending을 재개하지 않는다. 기존 모듈 변경 및 source 보존 절차·원작/mip/normal/자연 fast sweep/GPU/shipping 미검증 범위는 유지한다.

같은 Development Editor/frozen attack scope의 normal DLL SnowTick은 active929 평균0.507301/P95 1.033800/max4.364200ms, `Profile(20261008_105739).csv`다. 이전 .420499ms와 조건이 다른 별도 관측이며 개선율로 비교하지 않는다. 사용자 에디터를 저장/종료/재시작하거나 예전 alias로 manifest를 되돌리지 않았다. 새 에디터에서 기본 HeinMach를 확인한다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

원작 소진·브루탈 AP/SI/SB/SD/CS 표적 감사와 현재 재사용 클립 authoring을 완료했다. Source/수치 해석은 MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md, 구현은 Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md로 분리한다. 선택 복제49sequence/20montage 및 최소 gameplay 연결이 Main에 반영됐고 fresh Main saved readback이 완료됐다. 두 Skeleton의 DefaultSlot 외 reference bone 변경은 없다. 기존 .01 Player/baked timing/root motion을 추가 배율로 보정하지 않았다.

이번 Art 범위는 저장 원작 포즈/클립 매핑·재사용 보존과 필요한 slot 등록이다. Apes/Yetuga는 기존 Art body·material·scale1을 재사용했고 원작 Apes .8 character scale/native bone modifier/원작 전체 접촉 포즈를 복원한 결과로 설명하지 않는다. autonomous AI나 별도 lethal cinematic Execution 완료가 아니다. 기존 다른 Art/VFX 작업의 진행 상태는 유지한다.

<!-- PlayerAttackVFX_20261008_MainComplete_1911 -->
## 2026-10-08 19:11 KST — Player 현재 공격 VFX Main 반영 완료

현재 DAS 몽타주8의 source 기반401구간(Particle345/Decal56)과 선택 Art15(기존 master9/신규 dependency6)를 Main에 반영했다. 최종34파일/23패키지 전달, 새 Main 실제 RHI의 일반 공격18/Brutal5·176캡처·material compile/fallback0·정상 종료, 새 Main 저장본8,308 field 대조가 완료됐다. WorldSubUV 누락 UV와 blend 출력/density 복구 뒤 실제 OverFury의 opaque 면/네모와 체크무늬 fallback이 사라졌다. 추가 Brutal Snow4와 기존 source Snow65/Water20은 unsupported로 보존했다.

첫 조회점은 [PLAYER_ATTACK_VFX_PLAYBACK_20261008.md](PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 이번 최종 절과 `Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json`이다. 사용자 에디터는 저장/reload/종료하지 않았으며 새 native notify schema는 일반 재시작으로 로드한다. source graph의 native 재구성·원작 full pixel parity 미검증·짧은 효과/피해자 가림에 따른 가시성 한계는 정본을 따른다. 옛 private/pending 보고서를 현재 미적용 상태로 해석하거나 전체 추출·authoring을 반복하지 않는다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — CombatReaction 분류·InGame 파생 에셋 Main 완료

Player/몬스터6의 Short/Knockback/Launch·기상·방패 반응을 저장 pool과 몽타주로 정리해 Main에 반영했다. unique63 montage와 Player InGame24 clip의 원본 raw/재생률/root 계약, source245·Loop crop16·Definition7을 fresh Main에서 검증했다. Source root repair/재임포트/재리타이밍은 없었다. [Art 감사 정본](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 2026-10-10 완료 절, [최종 증거](../../Metadata/CombatReaction_20261008/FinalVerification.json), [사용 설명](../../Metadata/CombatReaction_20261008/UserGuide_20261010.md)을 따른다.

Main 에셋130 합집합·fresh654,552 readback/dirty0 완료다. Heavy Launch/Apes·Yetuga 전용 fallback, QuickStand 미연결, unsupported shape11 및 임시 Loop hold/거리·피해량은 원작 완전 재현과 구분한다. 실제 runtime/입력·회복은 Engineering 정본에 기록했다. 별도 MonsterVFX/PlayerVFX polish의 진행 상태는 해당 문서로 판단한다.

<!-- BrutalInputDevMapComplete_20261010 -->
## 2026-10-10 — Main DevMap 바닥 확장·몬스터6종 배치 완료

사용자 요청으로 /Game/Maps/DevMap의 Floor XY scale8→32를 적용했다. 약80m×80m→320m×320m, 면적16배다. Z scale8/위치(0,0,-0.5cm)/메시/충돌을 보존했다. DevAI_Navigation XY scale1→4로 약312m×312m를 포함하며 load/build lock이 풀린 뒤 실제 bounds update와 nav rebuild를 완료했다. fresh saved reload에서 짐승 두 위치와 월드XY축 ±140m 네 지점의 projection6개 모두 성공했다.

기존 인간10마리(Swordsman7, SwordShield1, HeavySwordsman1, HalberdElite1)의 배치·대기/순찰/Talk01/02를 유지하고 기존 BP_Monster_ApesStoneHandElite와 BP_Monster_Yetuga를 각1마리 추가했다. 총12마리/6종이다. 새 Actor Label은 DevTest_ApesStoneHandElite, DevTest_Yetuga이며 DevMap/Monsters/Beasts 폴더에서 찾는다. 좌표는 각각(5500,-2200,240)cm, (5500,2200,265)cm이고 둘 다 Yaw180°다. XY·Yaw·바닥/nav 확대율은 사용자의 큰 테스트 맵 요청에 따른 어시스턴트 임시 배치값이며 원작 메타데이터 좌표가 아니다. Z는 각 기존 BP의 scaled capsule half-height240/265cm에서 가져왔다.

기존 animation·PlayRate·Player0.01 배율을 편집하지 않았고 기존 gameplay BP/Definition/ASC/피격·소진·브루탈을 재사용했다. Apes/Yetuga의 AIStateTree는 기존 None을 유지하므로 자율 전투 AI 패턴 추가 완료로 해석하지 않는다. 별도 새 Main PIE에서6종/12마리 모두 종별 초기HP/Stamina와 AnimInstance·Definition·ASC를 확인했다. 인간4종 native CombatPolicyPIE도 성공했다. 이번 검사 에디터는 NullRHI로 실행했으며 새 배치의 화면 PNG/원작 배치 일치 검사는 하지 않았다.

[FinalVerification](../../Metadata/BrutalInputDevMap_20261010/FinalVerification.json), [설명·배치표](../../Metadata/BrutalInputDevMap_20261010/README.md), Authoring09.json/FreshSavedVerification02.json/FreshPIEVerification02.json이 현재 증거다. Author09 saved행의 중복은 Slate save 재진입으로 같은5개 package를 세 번 기록한 것이며 새 프로세스의 실제 값·hash/dirty0를 확인했고 helper를 보완했다. 성공한 author를 재실행하지 않는다. 입력 B 변경의 구현 기록은 Engineering 정본을 따른다.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — 몬스터6종 VFX Main 완료

six-family source 지원2855구간을 Sequence487에 연결했다. technical sentinel487 포함 State3342, Death montage6/Definition6 포함 author499, Art457+reused WPO1 및 adapter supplement4를 전달했다. fresh Main 저장·네 실제 RHI·Root 표본 시각 검토는 [FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)로 완료 확인됐다. D00 바닥 원과 Roar02 density/dissolve의 양성을 확인했고 QA11 shader 준비 뒤 이전 black/checker 카드가8 asset bytes 변화 없이 사라졌다. particle/decal·Apes material·Yetuga trail writer·Halberd Rim의 source/adapter·원작 shader/NI/pixel parity 미확인과 unsupported216은 [Art 정본](MONSTER_VFX_PLAYBACK_20261008.md)에 유지했다. 외부 Player follow-up/ARCH-86은 별도다.

초기968/Art457은 보존하고 Main 누락 adapter4를 별도 strict supplement로 추가한 최종972 기준이다. Source/native/material graph와 private proof는 유지했으며 새 Main 최종 검증은 추가 전달 이후 결과다.

## 2026-10-11 — Player 공격 VFX polish Main 완료

[최종 완료 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json) 상태는 `ArtFollowupDeliveredAndFreshMainVerified`다. 중단된 Smash slot5 World03 삼각형 연기 보정을 마쳤고 기존 머테리얼6개만 후속 반영했다. 최종 선택 Art18, 최신 Main Source101/b84의 실제 RHI18+Brutal5·FirstPose13·Saved401/8,308필드·Art18 검사 및 Input13 변경0을 확인했다. 이전 Art17/Private11 HOLD·Main followup pending은 이번 범위에서 대체한다. Root 실제 Main9장/264캡처와 원본 수치·adapter·임시 혈액2배 및 남은 작은 glints/gray bands·원작 shader/pixel/Shipping 미검증은 [Art 재생 정본](PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 같은 날짜 마지막 절을 따른다. Source/native/module 선택 및 사용자/외부 에디터는 수정하지 않았다. 기존 기록·receipt·backup을 보존했다.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — ARCH-86 Apes·Yetuga / InGame Fall 선택 Art Main 확인

Content151(저장 asset150+DevMap)과 실제 Main fresh saved/RHI 확인은 [FinalVerification](../../Metadata/GiantCombatFall_20261011/FinalVerification.json)의 MainDeliveredAndFreshVerified다. player 기존 InGame/DAS/Fall·FallAttack 시퀀스를 재사용하여 AM/DA/GA를 연결했고 기존 Airborne pose의 placeholder만 FallLoop로 바꿨다. enemy 두 family의 original pattern montage/ComboDefinition·GA·BS/ABP·기존 BP/Definition을 설정했다. 원본 sequence 재임포트·일괄 Root/RateScale 변경0이다.

Player .01/enemy1, 기존 VFX·DeathPresentation·Brutal50/B 및 DevMap12마리/대화 짝을 보존했다. 한 테스트 Cube의 top1200 cm·Start(-350,0,1292)는 원작 레벨 수치가 아닌 사용자 낙하 테스트용 임시 배치다. 최신 Main Definition2를 기반으로 own author를 재적용한 뒤 사망 참조를 cold readback으로 확인했다. 제품176/보호 Source84/VFX Content965 해시 불일치0이며 source zip/기존 보고서를 덮어쓰지 않았다.

원작 native 잡기/MoveTo/Spell/camera/전체 BT 및 pixel/frame 동일성은 미확인이고 Apes 누락 projectile 모델은 Engine sphere 대체다. Yetuga pickup의 생략 action Spawn은 추론, 다음 throw의 명시 Use는 원본 직접값이다. 초기 자동 StepStart 생성/준비 중 발사 해석은 철회됐다. 원본/계산/임시 값과 자료·함수·사용자 테스트·남은 경계는 [Engineering 구현 정본 마지막 절](../Engineering/APES_YETUGA_FALL_IMPLEMENTATION_20261011.md)을 따른다. 다른 에디터 제어0, Python gameplay 조작0, 검사 에디터 정상 종료다.


## 2026-10-11 — 사용자 요청으로 HeinMach authored 후처리 전부 제거

PPRemove01/PPColdReadback01의 실제 저장/새 로드에서 PP8→0, actor9869→9861이며 다른 actor/component 설정을 보존했다. Toon/outline/regional grade 연결이 제거됐고 Sky/Fog/조명/fire/snow는 유지한다. 원본 map byte backup과 상세는 ART_WORK_CONTINUITY 최신 HeinMachCleanPresentation 절을 따른다. 차지 굴절 사각형·OverFury VAT 큐브·혈액 분출 보정, 몬스터 root-motion flag와 camera 정책은 아직 진행 중이며 과거 Player VFX 표본 완료로 이번 문제 해결을 주장하지 않는다.
<!-- HeinMachCleanPresentation_20261011_PPRemoved -->

## 2026-10-11 — HeinMach clean presentation 및 공격 VFX 경계 교정 완료

[이번 작업 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)과 [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json)을 우선한다. HeinMach authored PP/툰/외곽선8 제거, 나머지9861 actor/component 및 Sky/Fog/조명198 보존을 fresh canonical-map RHI에서 확인했다. VFX128 emissive root에 역노출 보정을 적용했다. AutoExposure=False trial은 백색 clipping 때문에 철회했으며 기본 장면 metering/HDR/AA/물리 Fog는 남는다.

차지 slot0 smoke의 미연결 마스크와 slot1의 false color-switch 오소비를 교정했고 최종 실제1.1235초 격리 화면에서 두 사각형 제거를 확인했다. OverFury cube는 VAT decode/WPO 누락을 원본 VAT4 데이터+공식 native decoder로 교정했다. 혈액은 이전보다 실제 sprite 분사를1.5배 늘리는 임시 튜닝이며 decal 증가는 없다. 이동 경로 mesh-decal의 source15/s는 임시0/s로 중단했고 마지막 baked cache까지 fresh readback으로 확인했다. source 숫자/임시 숫자·원작 stripped shader 경계는 새 정본을 따른다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->
## 2026-10-11 — Combat UI 원작 자료 적용 / 백그라운드 Art Main 완료

원작 texture16·Medium FontFace1과 UI adapter material2/WBP 및 BP7을 Main에 저장했다. 실제 local Controller HUD, TargetPoint reticle/B, monster head/Boss top 게이지를 final RHI UI 검사/fallback0/Exit0으로 확인했다. 출처/숫자/미복원 경계는 [UI 감사](COMBAT_UI_SOURCE_AUDIT_20261011.md)다.

미전달 후속 blood4/DAS variant1/core6/montage3 및 fall2/snow materials2/HeinMach map1을 포함한 Content19를 Main에 반영했다. native18+Brutal5/392 captures/fallback0, 실제 Snow/동일 카메라3/PP0/9861 actor 및 모든 actor transform 보존을 확인했다. 증량/tint/Sun·Sky는 명시된 어시스턴트 임시값이다. 정확한 숫자·source·backup/receipt는 [Art 후속](COMBAT_PRESENTATION_FOLLOWUP_20261011.md)을 따른다. 필수 잔여는 없으며 shader/pixel/frame 완전 동일성과 Shipping 성능은 미검증이다.

## 2026-10-11 — B 인디케이터 알파 부드러운 경계 Main 완료

기존 `M_UI_BrutalRing`의 R/G/A 혼합 opacity를 A-only로 교정하고, 원작 radius·색을 유지한 inward feather/임시 EdgeSoftnessPixels1.25를 적용했다. 원본 B texture 및 나머지 UI 제품36개는 byte 동일하다. 단일 material Main 전달/fresh saved readback/실제 native UI PIE/shader fallback0/Exit0 및 B 화면 직접 검수가 완료됐다. [UI Art 정본](COMBAT_UI_SOURCE_AUDIT_20261011.md)의 마지막 절과 `Metadata/CombatUI_20261011/BrutalAlphaFinalVerification.json`을 따른다. 필수 잔여는 없다.

## 2026-10-12 — ARCH-88 Monster VFX·피격/사망·Combat UI Main 완료

Main Source10/asset59, 새 runtime 파일0이다. 공격 첫 spawn을 finalized bone pose 뒤로 옮기고 혈흔 floor producer42/mesh receiver16을 제거했다. 실제 accepted hit의 검붉은 피, normal/paired death 완료 뒤 black ash·3초 TEMP dissolve·Destroy, UI_Chest에 매 프레임 붙는 LockOn/B, immediate HP/ST와 감소 잔상, transparent CurBar/별도 gradient dark track, compact Elite124×22를 적용했다. 실제 build·fresh RHI Attack198/1577/death6/actual hit13/UI02/fallback0/Exit0 및 최신 saved audit가 통과했다.

출처·TEMP·표시 검수는 Docs/Art/MONSTER_PRESENTATION_REPAIR_20261011.md, runtime/cleanup/정확한 resume는 Engineering ARCH-88 완료 절, 최종 source/asset SHA·loaded module·동시 audio67 보존은 Metadata/MonsterPresentationRepair_20261011/FinalVerification.json을 따른다. Source/selected visual field는 검증 이후 동일하며 사운드 작업의 후속 GUID 재생성24는 최신 파일로 보존했다. 필수 잔여0이다. 원작 native correction52/stripped shader·pixel/frame 완전 일치 및 Shipping 성능 완료를 뜻하지 않는다.


## 2026-10-12T02:04:36+09:00 — 원작 사운드 Main 에셋·출력 및 수정 바인딩 준비본 검증

Audio/Original2147/source wave1644·cue480/645 sequence2163 event/HeinMach134 ambient·13 reverb는 Main 저장·fresh 검증됐다. 전체 원본 chunk0/chunk1 index를 재사용했다. 마지막37 ComboDefinition 배열 참조 누락을 수정한 준비본은 fresh saved/실제 flight 포함 audio PIE에서 검증됐지만 Rider editor의 Windows error32로 Main 교체 대기다. 완료로 확대하지 않는다. 원본/TEMP·Wwise DSP 한계/검증과 exact resume는 ART_WORK_CONTINUITY 마지막 사운드 절 및 Saved/ImportReports/GameplayAudio_20261011/{PreparedVerification01,ResumeState05}.json을 따른다. 기존PP0/Sky/Fog/Snow40cm/UI/원본 기록을 유지했다.


## 2026-10-12 — Player Parry 준비본과 alpha 검사 정정

원작 Just_L/R composite의 반대 이름 raw sequence 참조, DilationAnimPositions 31개를 사용한 22/60초 bake, PP_Damage_Spray.NewJustGuard→PP_AtkEx_JustGuard의 13 emitter, 기존 원작 성공 cue를 연결했다. 새 motion2/particle1/master3/MI5=11개와 기존 Guard GA/Montage2개가 준비본이다. 정확한 package/SHA·수치·현재 검증 범위는 [PLAYER_PARRY_SOURCE_20261012.md](PLAYER_PARRY_SOURCE_20261012.md)에 기록했다. 공유 원본·Audio Notify·다른 작업은 저장하지 않았다.

최초 어두운 effect preview의 검은 원판은 shader 결함이라는 가설과 달리 검사 전용 빈 GameModeBase 맵에 생성된 **DefaultPawn_0의 구형 메시**였다. AlphaPreview06의 hidden_fixture_pawns에 origin(0,0,0)을 기록했고 이 Pawn만 숨긴 실제 RHI 캡처에서 원판이 사라졌다. AlphaPreview01–05 및 Isolate03은 그 fixture가 가려 외관 합격 근거로 사용하지 않는다. 보호된 LOD property를 직접 변경하려던 Isolate01/02는 API 실패로 끝났으며 task-owned process만 정리했다.

불필요한 local5 MI의 Additive 통일과 black-emissive gate는 AlphaFinalize02에서 철회했다. 모든 MI의 원본 base-property overrides를 복원했으며 particle의 13 emitter를 모두 유지했다. local3 parent의 continuous opacity와 0.04 UV / 최소1.25px edge feather만 유지한다. untextured DefaultParticle spark는 elliptic alpha와 ParrySparkSoftnessPower=2로 모서리·끝을 부드럽게 했다. 이 세 수치는 원작이 아닌 어시스턴트 임시 표현 값이다. root shader/source pixel parity·Shipping 성능은 미확인이다. 최종 preview/saved readback 결과는 PreparedVerification과 하단 후속 기록을 따른다.

**Main 에셋 반영은 잠금으로 대기한다.** 다른 에디터/채팅은 제어하지 않았다. 재추출/전체 author를 반복하지 않고 DeliveryPreflight/ResumeState의 대상만 SHA 확인 후 복사하고 fresh Main saved/RHI를 검증한다.



## 2026-10-12T04:22:44+09:00 — 사진 기준 몬스터 혈액·지면 혈흔 Main 완료

Main runtime2/DEV2/신규 유효 package5·build2026101254·fresh saved/CDO6·실제 눈 RHI6종/24혈액·12소멸/지면 lifetime·actual collision13을 완료했다. 이전 ResumeState/ResumeState02의 pending은 이 절에서 대체한다. 정확한 현재 SHA/loaded module·수치 출처·한계는 Metadata/MonsterBloodReference_20261012/FinalVerification.json, 다음 절차는 ResumeState03.json과 MONSTER_PRESENTATION_REPAIR_20261011.md의 최신 사진 완료 절을 따른다. 첫 shader fallback/몸 안쪽 발생/횃불 과노출을 기존 owner·재질만 보완했다. 사용자 PID19752/foreign editor 제어0이며 새 C++를 사용하려면 사용자 editor의 정상 재시작이 필요하다. 남은 필수 구현0; 원작 native/pixel/frame parity·Shipping stress는 별도다. 기존 사운드/패링 준비본을 덮어쓰거나 완료된 broad author/delivery/archive를 반복하지 않는다.


## 2026-10-12T08:12:54+09:00 — 혈액 작업 메인 에디터 적용 완료

앞선 사진 혈액 Source/package는 그대로 유지됐고 후속 사용자 요청으로 실제 Main editor PID23736/DevMap/현 canonical DLL/몬스터6 CDO를 확인했다. 새 Art authoring/asset save0이며 정상 재시작 필요는 해소됐다. Source·UHT timestamp 보완/합본 build·actual hit13과 정확한 적용 증거는 Engineering continuity의 같은 날짜 절, Metadata/MonsterBloodReference_20261012/MainEditorIntegration/Result.json·ResumeState04.json을 따른다.


## 2026-10-12T08:17:34+09:00 — Player Parry 에셋 Main 전달·fresh 검수 완료

새 motion2/particle1/local master3·MI5와 기존 Guard Montage·GA를 합친13 package를 Main에 전달했고 fresh MainSavedAudit02·MainPIE02에서 확인했다. source composite/dilation/22 frame/source cue와 기존 Guard segment·notify는 유지했다. 실제 Main의 성공 모션/weapon contact flash/꼬리 프레임을 열어 불투명 card/원판 경계가 없고 입자 끝이 연속 fade하는 것을 확인했다. source MI blend overrides는 복원됐으며13 emitter를 유지한다. local parent의 .04 UV/1.25px와 spark ellipse power2는 사용자 요구에 대한 임시 표현 수치다. 기존 공유 재질·texture·audio를 재저장하지 않았다.

Main DLL/source/asset SHA와 실제 RHI/저장 검사 결과는 Metadata/Parry_20261012/FinalVerification.json에 결속됐다. 이전 Main 잠금/준비본 pending은 이 범위에서 해소됐다. DefaultPawn 검은 원판 가설 정정과 이전 실패 proof는 보존한다. 초기 RHI의 메모리 budget/FPS 경고, 원작 stripped shader/pixel/impact writer parity, 실제 스피커 출력(-nosound) 및 Shipping 성능은 범위를 구분한다. 정확한 runtime은 Engineering PARRY_IMPLEMENTATION_20261012.md, 완료 후 재개 기준은 ResumeState.json이다. 전체 추출/저작/과거 DLL 전달을 반복하지 않는다.



## 2026-10-12T10:52:19.737884+09:00 — Fab 외부 VFX 3팩 Main 반입·검증 완료 / 나머지 4항목 원본 확인 대기

Cursed Magic Niagara58/Niagara VFX Bundle609/ARPGVFXPack03 15, 총 NiagaraSystem682를 원본 package root /Game/Cursed_Magic, /Game/NiagaraVFXBundle, /Game/ARPGVFXPack03에 반입했다. 의존성59/외부 actor-object110을 포함해 신규 native3357·5,017,846,876byte이며 기존 덮어쓰기0·Source/Config/uproject 변경0·asset save0이다. MainLoad02 public3247/external110/error0/exit0, 실제 MainShaders01 D3D12·SM6 Material375 compile error0/stats375양수/exit0, 원본·Main SHA3357 검증이 완료됐다. 전체 대응표·데모 preview soft5/legacy input·RigVM 경고·숫자/검증 경계는 [이번 Art 정본](FAB_VFX_IMPORT_20261012.md), 최종 receipt는 Metadata/FabVFX_20261012/FinalVerification.json이다.

7개 전체는 미완료다. Action-RPG Essentials/Dynamic Impact and Collision/Slash and Hit은 공급 폴더의 대응 원본 미확인이고 4번째 de3c9ae3 링크는 조회403/상품명 미확인이다. 추가 로컬 경로/정상 상품 정보를 기다린다. VFX gameplay 연결 및 데모 플레이 가능·전수 화면/Shipping 성능 완료를 뜻하지 않는다. 완료한 3팩을 전체 재반입하지 않는다. staging은 자동 삭제 검토 차단으로 보존했고 exact resume는 Art continuity/Metadata/FabVFX_20261012/ResumeState.json이다.


## 2026-10-12T11:04:18+09:00 — 사용 애니메이션 Root88 / VFX basis·scale Main 완료
현재 사용395개/body392+prop3에 대해 Root 옵션/track을 확인하고 native first/mid/end1176포즈를 검사했다. Animation88의 first-frame 누적 origin을 RefPose lock으로 정렬했다. Root raw channels, 전체 model·notify392 SHA, 모든 timing/Root enable/force/normalized scale 및 original resources는 보존됐다. exact imports 기준 수치는 RootLockPlan.json의 first-root/skeleton reference 필드이며 신규 원작 튜닝값이 아니다. actor 좌표의 root-stripped source collision에 live body scale을 한 번 반영, socket 없는FX는actor orientation+mesh origin/offset·size body scale 적용. VFX198/1577 및 death6는 delivered Source와 동일한 private RHI Success이고 Main current canonical/freshRoot·HP30·Player16·saved 원본 유지가 Success다. active correction-curve rows0 / 원작 native·pixel parity·전체두레벨·network는 완료 검증으로 표현하지 않는다. Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json 및 ResumeState03.json, MainBefore/RootAssetsBefore 백업을 따른다.


## 2026-10-12T13:12:55+09:00 — 사망·브루탈·공격/회피/착지 효과 Main 후속

기존 PP_Player_Parry_Success(원본 JustGuard13 emitter의 로컬 alpha 복원), PP_AtkEx_Grapple_01/02와 original world smash_weak surface variants를 재사용했다. 새 particle/material/texture asset0. 원작 출처는 Metadata/Parry_20261012/OriginalEvidence.json, Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json, Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv 및 기존 Player VFX playback 정본이다. gameplay source field/공격 피해/모션 데이터/오디오는 그대로다.

montage8에 추가된55 window는 공격44(파랑+보라/검붉은 accent), 방향별 회피8, 착지3이다. 기존 trigger/입력 event GUID/field·section/segment 보존을 저작 시 확인하고 SavedAudit02에서55 start/end pair·template·scale·수명을 재조회했다. 루프를 방치하지 않고 notify end에서 deactivate하여 잔여 입자를 drain한다. 기존 Spin 강한 내려찍기2 marker의 dust/snow/grass strong variant는 weak variant로 바꿔 바닥으로 낮게 퍼지게 했고 실제 weapon-tip/walkable normal 기준을 적용했다. 착지 먼지는 벽에 들어간 칼끝의 실패를 피하려고 실제 grounded actor 발밑으로 보정했으며 collider/gameplay 위치는 바꾸지 않았다.

새 수치는 모두 어시스턴트 TEMP 표시값이다: attack blue scale0.35(가벼운 공격)/0.5(강한 공격), accent0.25/0.35, dodge0.25, plunge blue0.5/purple0.4/ground1, Spin ground0.8. Notify Scale3D에서 조정한다. 착지 start는 기존 Land section entry+UE endpoint epsilon0.0001초이고 window0.121175006초는 저장 source damage window 길이를 사용한 표시 adapter이며 새 gameplay duration이 아니다. weapon-tip100cm는 기존 blood source RelativeLocation.Z=100에서 가져온 cm 값이고 원작 floor native writer를 복원했다고 표현하지 않는다. 효과 기호의 파랑/보라/검붉은 인상은 현재 복원 parent·조명에 따른다.

혈흔 TEMP는 Monster Class Defaults: main 기존8/95/150cm half extents, satellite6(technical presentation cap16), radius90–280cm, size factor0.35–0.65, 기존24초 hold+3초 fade 유지다. 전체 방위로 점과 불규칙한 큰 얼룩을 함께 펼친다. shape/RGB 마스크·검붉은 분사·source ash와 dissolve3초는 이전 사진 혈액 구현을 재사용한다. 정상/짝 사망의 source 끝 포즈 수리와 실제6종7장/4방위 검사는 Engineering 최신 절을 따른다.

실제 게임 viewport 캡처와 source/hash/원본 보호는 Metadata/CombatFinishFollowup_20261012/PresentationFinal02·FinalVerification.json, 추가 ground 보정은 PlungeAnchor01/Applied.json에 있다. 대표 실제 화면을 별도 검토하며 editor screenshot/이전 실패를 시각 합격으로 쓰지 않는다. 전체 native shader/pixel parity·Shipping stress를 주장하지 않는다.


## 2026-10-12T13:16:18+09:00 — ARCH-92 메인 에디터 적용 확인 완료

Rider normal Khazan Run으로 Main PID16504/DevMap을 열었다. read-only RiderLink가 실제 canonical DLL SHA a247fac8a6c457a90d336ceb9ed90a5445bca878295d941b1c5081a375977f9b와 FinalBuild05 일치, 6종 CDO scatter6/radius90–280cm, dirty content/map0를 확인했다. asset save0, PIE 미시작이며 에디터를 열어 둔다. FinalVerification.json은 MainDelivered_Built_Validated_EditorReady, ResumeState04.json은 complete/잔여0이다. 사용자 이전 Main은 착수 때 종료돼 있었고 강제 종료/HotReload/기존 session 저장0이다. 모든 실제 테스트·동일 runtime source·Art TEMP와 원작 한계는 앞선 완료 절을 유지한다.


## 2026-10-12T13:26:59.800787+09:00 — Fab VFX 7팩 반입·얕은 폴더 정리 완료

미반입 4팩(Action-RPG Essentials / Dynamic Impact and Collision / Slash and Hit / Roar Spell VFX)을 `VFX/Assets/Content`에서 찾아 기존 3팩과 함께 Main `/Game/VFX`에 반영했다. 7개 numbered pack folder와 `_Shared`를 사용하고 NiagaraSystem은 각 팩 root, 지원 에셋은 한 child folder에 있어 Content 아래 visible 최대 깊이 3이다.

| 상품 | 현재 Unreal 경로 | NiagaraSystem |
| --- | --- | --- |
| Action-RPG Essentials VFX Pack V2.0 | `/Game/VFX/01_ARPGEssentials` | 52 |
| Dynamic Impact and Collision Effects Pack | `/Game/VFX/02_DynamicImpact` | 16 |
| Slash and Hit VFX | `/Game/VFX/03_SlashHit` | 35 |
| Roar Spell VFX | `/Game/VFX/04_RoarSpell` | 1 |
| Cursed Magic Niagara | `/Game/VFX/05_CursedMagic` | 58 |
| Niagara VFX Bundle | `/Game/VFX/06_NiagaraBundle` | 609 |
| ARPGVFXPack03 | `/Game/VFX/07_ARPG03` | 15 |

최종 3,969 files / public 3,859 / Niagara 786 / 외부 WP actor 103 + object 7이다. MainAudit02 native load·참조·7,943 settings 비교·Cursed actor 배치/효과 선택 보존은 passed/Exit 0, 같은 Main renderer의 StageShaders02 Material 419 real-RHI compile도 passed/Exit 0이다. 최종 전달 SHA와 기존 3,357개 retired SHA 확인을 마쳤다. Source/Config/uproject/gameplay hookup 작업 변경 0이며 동시 외부 Source 변경은 보고서에 분리한다. 원본 preview soft path 5개와 demo legacy input 경고, 전체 시각/Shipping 검증 범위는 [Art 정본](FAB_VFX_IMPORT_20261012.md)의 최신 완료 절을 따른다.

이 작업의 현재 상태·재개 정본은 `Metadata/FabVFX_20261012/Completion/FinalVerification.json` 및 `ResumeState.json`(complete/remaining 0)이다. 예전 root와 미반입 4개/검증 중 상태를 현재로 재사용하지 않는다. 기존 최초 반입 report/backup은 역사 증거로 보존했다.


## 2026-10-12T13:28:50.418609+09:00 — Fab7 현재 열린 Main 에디터 표시 확인

RiderLink의 현재 Main PID16504에서 read-only registry 조회로 7팩 root의 NiagaraSystem 52/16/35/1/58/609/15 및 public asset 3859를 확인했다. 강제 rescan/asset save/map save/맵 전환/PIE 제어는 0이다. 현재 열린 에디터에서도 `/Game/VFX` 라이브러리를 바로 조회할 수 있다. 증거는 `Metadata/FabVFX_20261012/Completion/LiveEditorAvailability.json`이다. 7팩 반입·정리는 complete/남은 필수 작업0을 유지한다.


## 2026-10-12T13:40:48+09:00 — DevMap·HeinMach 룩 준비본 / Main 잠금 대기

[SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md](SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md)를 첫 조회한다. DevMap/HeinMach 조정본493(map2/기존 masked MI489/새 parent2), PP 각1·toon/custom blendable0, 기존 actor pose10032 변화0와 scalar/vector/texture/base overrides의 예상 밖 변경0을 확인했다. small-tree3 raw RGB emission off만 TEMP 예외다. source stock foliage transmission 시험은 white leaf로 철회했고 최종 기존 DefaultLit/기존 two-sided/clip을 유지한다. DevAfter02/HeinAfter04 실제 D3D12 game viewport 검수·Exit0와 PreparedSaved02/PreparedDelivery가 준비본 정본이다. Source/Config/DLL 전달0, 원작 전용 shader/pixel·Shipping 검증은 별도다. Main editor PID16504/DevMap의 dirty0을 read-only 확인했지만 Win32 error32 map lock으로 Main content writes0에서 중단했다. 사용자에게 저장 후 editor 종료를 요청했고 editor 종료/reload/save 제어0이다. 잠금 해제 뒤 install→새 MainSaved01→MainDevAfter01/MainHeinAfter01→selected493 SHA/화면→FinalVerification/완료기록 순으로 재개한다. Main이 baseline과 달라졌으면 최신 사용자 변경을 보존해 field만 이관한다. 전체 추출/재임포트/Source·과거 DLL 전달을 반복하지 않는다. exact resume는 Metadata/SceneLook_20261012/ResumeState.json, 비교는 DevMap_BeforeAfter.jpg/HeinMach_BeforeAfter.jpg다.

<!-- SceneLook_20261012_PreparedAwaitingMainUnlock -->


## 2026-10-12T14:44:13+09:00 — DevMap·HeinMach Main 반영 및 새 화면 검증 완료

앞선 Main 잠금 대기 기록을 이 완료 기록으로 대체한다. 사용자 Main 에디터가 종료된 뒤 선택493개 전부의 baseline SHA와 교체 접근을 먼저 확인했고 Main에 map2/기존 masked MI489/부모2만 전달했다. 사용자 프로세스 강제 종료·저장·reload0, Source/Config/DLL 전달0이다. MainSaved01 새 프로세스의 saved audit Success/Exit0, 기존 actor pose10032 변화0, 보호 material parameter/base overrides 예상 밖 차이0을 확인했다. MainDevAfter01(DevMap3뷰)/MainHeinAfter01(HeinMach4뷰)는 실제 D3D12 game viewport를 촬영하고 Exit0/성공/재질 compile failure0이다. 역광 캐릭터·눈/바위/횃불·음영 화면을 직접 검수했으며 실제 Shot1092×573과 요청 창1600×900은 구분한다. 현재493개 파일 SHA가 준비본과 전부 같다. 비교 이미지는 새 Main 촬영으로 갱신했다. Three small-tree raw emission off는 명시한 TEMP 보정이며 실패한 stock foliage transmission trial은 철회된 상태다. 원작 전용 shader/pixel 전체 일치와 Shipping 성능·전 경로 플레이 검증은 별도이며 완료로 확대하지 않는다. 재개 정본은 Metadata/SceneLook_20261012/FinalVerification.json과 complete ResumeState.json이다. 이미 완료된 전체 저작/추출/재임포트를 반복하지 않는다.

<!-- SceneLook_20261012_MainCompleted -->


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 바닥 Niagara·alpha Main 완료

사용자 지정 /Game/VFX/03_SlashHit/KZ_Parring_Distort의 원본6 emitter는 그대로 보존했다. /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort 복제의 M_SW_distort_Sprite_0/M_SW_distort_Sprite001_1/Hit003_6 renderer만 CustomFacingVector 및 실제 User.KZFloorNormal로 저작했다. shader에 카메라 facing을 남기는 잘못된 수동 binding trial은 native author의 host-map binding3개 true로 대체됐다.

원본 parent/MI2쌍을 새 경로에 복제하고 기존 opacity에 UV radial feather(.8–1)를 곱하며 refraction 가장자리를 중립1로 돌려 사각 경계를 제거했다. 이는 어시스턴트 표시 TEMP이고 원작 직접 수치가 아니다. scalar/vector/texture override는 원본과 동일하다. 원본 source Niagara/머티리얼/텍스처를 수정하지 않았다. 실제 RHI PrivatePIE05/Fall_02 화면에서 부드러운 바닥 원형과 사각 경계 제거를 검수했고, fresh Main saved/RHI가 같은6 package를 검증했다. 경로·SHA·runtime 증거는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json. Fab 사용자 지정 효과와 원작 metadata 재현은 구분하며 원작 pixel/shader 동일성은 주장하지 않는다.


## 2026-10-12T19:30:36.993088+09:00 — 전체 정수 FPS·몽타주 표시 증폭 수정 Main 완료

원인: UE5.8 UAnimMontage::UpdateCommonTargetFrameRate가 호환되지 않는 source sampling rates를 만날 때 CommonTargetFrameRate를 무효화하고 UAnimCompositeBase의100000/1fps precision fallback을 사용한다. 원본 전체 inventory2674/158에서 fractional461/fallback36이었다. import의 (frames−1)/exact source or dilation duration으로 생성된 rational FPS가 근거이며 재생 자체가100000배 빨라진 것으로 혼동하지 않는다.

461 sequence를 nominal30/60Hz로 변환하고 frame-index bone keys3854855개를 그대로 보존했다. raw duration=Dnew=N/Fint, alpha=Dnew/Dold, RateScale_new=RateScale_old×alpha로 실제 seconds를 유지한다. notify/marker local seconds·embedded visual scalar/vector curve X와 slope/weighted tangent·montage source trim 좌표를 함께 변환했다. 원본 TimingContract/metadata는 보존하고 IntegerFPSRepair tag를 덧붙였다.45 의존 montage의 표시 sampling은 모두 정수다. montage DataModel 자체를 강제 정수 grid로 바꾸는 trial은 reload 시 실제 length를 반올림하여 철회했고, 원래 precision model clock은 보존했다.

fresh Main의 모든2674 sequence/158 montage에서 fractional sequence0/fallback0; MainSaved01은 실제 montage length 차이0·raw key/notify 일치를 확인했다. concurrent Main Niagara attack VFX88개는 최신 저장본에서 다시 보정하고 원본 pose hash/신규 notify를 보존했다. 현재 Enemy 조회는 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv(813행/270수정)와 전체 Plan/FinalVerification을 사용한다. 예전 CSV는 변환 전 역사값이다. original game metadata numbers와 clock 계산/knockback TEMP 표현은 구분한다. FPS 수정 과정에서 skeleton/root tracks/material/HP·ST/공격 geometry·world clock을 재저작하지 않았다.


## 2026-10-12T19:50:49.391255+09:00 — 플레이어 Dodge·성공 회피 표현 Main 완료

8방향 Dodge BP는 기존 Fab `/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Dash1`(회피 자체)과 `NS_Cursed_Magic_Blink1`(실제 공격 회피 성공)을 참조한다. source NS/머티리얼/텍스처 수정0이다. 새 `/Game/Monsters/Shared/Feedback/SW_Player_DodgeSuccess`는 어시스턴트 저작 WAV0.18초/48000Hz/mono/peak0.16/clipping0/양끝0이며 원작 SFX가 아니다. 원본 WAV와 표시 TEMP는 `Metadata/BeastDodge_20261012/Feedback/AudioSource.json`에 보존한다.

단위 없는0.12/0.15는 어시스턴트 표시 TEMP이고 preset의 노출 FLOAT `User.Scale_All` 기본값에 곱한 뒤 Activate한다. component scale만 바꾸거나 절대 parameter값으로 덮던 trial은 채택하지 않는다. 실제 RHI 화면에서 발 주변의 얇은 trail과 캐릭터 가독성을 확인했다. MainFinalQA04 방어 검사에서 실제 새 Niagara component와 SoundWave 재생·Dodge 종료의 자기 표현 정리를 확인한다. 성공 SFX/VFX는 피해 producer가 Dodge 방어를 승인한 경우 실행당1회만 발생한다. canonical 근거는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이며 gameplay 무적·제어 수명은 Engineering 기록을 따른다. 필수 잔여0, 원작 pixel/audio 전체 일치는 주장하지 않는다.

<!-- BeastDodge_20261012_MainCompleted -->


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

몬스터의 지정 Slash/Sting 참조는0으로 복구했고 기존 player effect100 객체를 보존한 채 KZ_Slash 별도 child100을 추가했다. Shader/색·source 원래 효과를 제거하거나 대신 재생하지 않는다. reference bones FX_L_Axe_01/02 및 FX_R_Sword_01/02의 geometry를 실제 Weapon_L/R grip에 연결한다. WeaponSlashProbe04의 reference measured offsets와 SM_VFX_SlashRing_01 bounds[-100,-100,-20]..[0,100,20]cm, Meshes[0].Rotation.Yaw180deg에서 span200/centre 보정을 계산했다. 이 숫자는 요청 Fab/current imported asset의 좌표계 변환이며 원작 gameplay 튜닝값이 아니다. shared KZ_Slash/KZ_SwordsMan_Sting asset은 수정하지 않았고 component만 독립 회전·크기 곡선을 중립화한다.

기존 원작 spark adapter를 CPU finite120(40×3)방사형 불꽃으로 재사용했다. TEMP는 life.18–.38s/speed1000–1800cm_s/width2–4cm/length16–30cm 및 blue(.04,.28,3)/purple(1.4,.025,2.4)/red(2,.012,.035) linear HDR와 alpha(0,.95),(.55,.7),(1,0)이다. 실제 수치 조정은 소유 PS의 module/curve에서 한다. 기존 혈액3 emitter와32 root blocks 및 nested data를 보존하며 승인 hit·parry·player received hit에서만 이 burst를 소비한다. cancelled PP/M_Monster_HitFlameFlash 두 asset은 Content에서 제거하고 metadata backup을 보존했다. 추가54 unconditional colour windows는 복원하지 않았다. 기존 ground scatter·dissolve/ash·SlamDistort alpha는 보존한다.

실제 BurstVisual05의120입자/얇은 radial streak 및 중간 contact, natural player original+additional/added-only4 frames, actual monster hit/received-hit 화면을 검수했다. 최초 GPU와 fluid material의 가시성 실패, old raw size lookup cache, camera API 오류는 실패로 보존한다. AdditiveSaved02·ExactBeforeAudit01(220×21 차이0)·FinalVerification이 최신 정본이다. 앞선 replacement author/delivery와 resource 전체 추출/Root/FPS author를 반복하지 않는다.


## 2026-10-13T02:25:35.076330+09:00 — 현재 효과 알파 카드 경계·HeinMach 눈 수 Main 수정 완료

정본은 `Metadata/ParticleAlpha_20261013/FinalVerification.json`이다. 기존 사용 metadata→현재524 animation의 notify/HeinMach96 effect component→331 PS/NS·281 material interface를 확인했다. 전체 Content/원작 추출을 재조사하지 않았다. 직접 renderer 재질203/부모86, 현재 alpha 입력의 실제138 PNG 채널·부모/인스턴스 상속을 확인했다. HDR4 lookup/검정 float는 PNG 강제 변환하지 않았다.

공용 `Shared/Materials/Other/DefaultParticle`은 PC.A만 opacity mask로 사용해 실제 카드가 흰 사각형이었다. 기존 Masked blend를 유지하고 타원 공간 마스크를 연결했다.16 sprite instance는 실제 sampled texture의 A가255 상수인 채 불투명 카드를 그렸다. 해당 instance에만 R density/particle Alpha 선행 clamp/안쪽 feather를 적용한다. 부모 default repair0과 원래 source RGB·particle modules/shape/수명·event/animation·mesh/Additive 정책은 보존한다. 어시스턴트 표시 TEMP는 feather.03UV/최소1.25px/무텍스처 ellipse power2이며 원작 shader 수치가 아니다.

메인 선택30파일=부모13+MI16+기존 NET_HM_WeatherBudget1을 hash/CAS 전달했다. Source/Config/map/PS/NS/texture/바이너리·QA asset 전달0이다. 기존 눈2레이어의 source1250/2500 particles_s는 그대로이고 생성 scale.25→.20(어시스턴트 표시 TEMP)으로 rate312.5/625→250/500, 기존 대비20% 줄었다. 실제3샘플 평균 flakes2119→1862.33/dust532.67→454.67로 감소했다. 이는 random/time-dependent active count이며 매 순간 정확히20%라는 뜻이 아니다. 눈 크기/속도/수명/재질·camera/원본 actor 배치는 바꾸지 않았다.

새 MainShaderVerify01은86 material compile errors0·16 scalar override·snow.20, MainSnow01은 실제 game view/count/저장0으로 통과했다. standalone 동일 camera card17의 검은 사각·solid card 제거 및 texture 양성을 직접 확인했다. actualPS8 중4는 기본 단독 parameter에서 active0이므로 전체8 양성 화면 검증이라고 기록하지 않는다. 실제 PartGroggy blood/짧은 blade·wood 표본과 눈 entry/sky를 검수했으며 모든 전투 frame/camera·Shipping/원작 shader 전체 동일성은 주장하지 않는다.

초기 protected API/강제 HDR PNG/fixture reentrancy/PIE viewport/반환값·부분 저장 실패는 각 run에 보존했다. Windows 접근 제한은 별도 consumer의 정상 종료 후 선택 전달로 해결했으며 foreign editor 종료/저장/reload0이다. task-owned CardsBefore01 hung fixture만 정확 PID/args 확인 후 정리했다. 모든331 source system과 HeinMach map·눈 graph hash가 원본과 일치한다. 후속은 이 보고서/RepairPlan/TextureChannelAnalysis에서 표적 시작하고 prepare/전체 author/과거 CAS를 반복하지 않는다. 필수 잔여0이다.

<!-- ParticleAlpha_20261013_MainCompleted -->


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset 형상 Main 전달 완료

SK35/PA35/post-process20/shared CopyPose1/기존 gameplay BP6의97 package를 Main에 전달했다. 원본 vertex/skeleton/animation/texture/material/LOD 재임포트0이다. source metadata anatomy17/17/16 capsule의 package/field/raw/SHA는 OriginalAnatomyShapes.json, 그 외 dominant LOD0 skin bounds와 Yetuga actual skin tip sphere/질량·관성 계산은 final evidence의 source reports다. Feel은 current Player TEMP 재사용과 명시된 virtual-inertia TEMP2/기술적 adaption이며 원작 physics 전체 복원으로 표현하지 않는다. 최종 explicit simulated317이며 초기378/미완료 기록을 대체한다. Runtime 품질/검증/cleanup은 ../Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json을 따른다. 필수 잔여0; full 원본 추출/재임포트/기존 shader·VFX·animation 변경을 반복하지 않는다.
<!-- MonsterSecondaryPhysics_20261013_main_complete -->


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery5 role / mesh3 / FT_Trail.G / RGBA ShaderLUT? ?? Heal ??? ????. ?? Heal?Action receipt? ??, runtime1/DEV1/asset13 ?? ??, ? runtime class/tag/manager0. Main build/saved/actual Heal?PlayerAttackCollision2 ?? ?11 effect/alpha ?? ?? ??, ?? ?? ??0. ?? cooked graph ???? ?? native ???/TEMP ??? ?? ???? ????. ??: Art PLAYER_HEAL_VFX_SOURCE_20261013.md / Engineering PLAYER_HEAL_VFX_RUNTIME_20261013.md; evidence Metadata/HealVFX_20261013/FinalVerification.json, ??0.

## 2026-10-13T09:47:37+09:00 — 패링·공격 VFX 참조 역할 정정과 재분석

사용자 정정에 따라 백색 중심·붉은 선형 VFX는 공격, 분홍·보라 광막은 패링으로 확정해 다시 비교했다. 08:42 분석의 역할별 결론을 후속 기준에서 철회하고 COMBAT_PRESENTATION_FOLLOWUP_20261011.md의 최신 재판정 표를 정본으로 둔다. Main Guard GA/HitBurst/혈액 PS SHA는 기존 완료 증거와 일치한다. 최우선 부족점은 성공 패링의 넓은 광막이며 공격은 이미 있는 붉은 슬래시·밝은 선을 다듬고 실제 명중의 백색·붉은 강조와 작은 sparks를 보완하는 방향이다. 기존 혈액/혈흔·무기 추적·알파 개선을 미구현으로 분류하지 않는다. 분석과 사진 사본/문서 기록만 수행했으며 게임 코드/BP/에셋 수정·build·새 PIE는 없다. 정확한 시간/주변 광의 생성 방식·SFX와 근사 접점의 실제 어긋남은 미확인이다.

<!-- CombatVFXReferenceReview_20261013_user_corrected_roles -->

## 2026-10-13 — Notion Art 현황·주간 구현 화면 기록 완료

김민재 Notion의 일일/주간·레벨/전투 표현 roadmap/task에 Original Player 파츠/Hair·천, Enemy library와 보조 물리, HeinMach/StormPass·눈/fire/weather·조명/재질, 원작 UI·Monster6/Player/Parry/Heal VFX와 알파 작업의 현재 적용·검증 범위를 기록했다. 현재 효과와 10/13 참고사진의 공격/패링 역할 재분석·아직 구현하지 않은 광막을 구분했다. cooked 그래프 재구성·TEMP·원작 픽셀 미검증을 원작 직접 복원으로 표현하지 않았다.

새로 업로드한 실제 Main 화면4종은 ParticleAlpha_20261013/MainSnow01/Entry.png, CombatUI_20261011/BrutalAlphaMainPIE01/04_BrutalAvailable_B.png, Parry_20261012/MainPIE02/01_ActualParryFlash.png, HealVFX_20261013/MainFinalPIE01/KZHeal_10_0.png다. 촬영일/의미를 명시했고 과거 주간에 추가한 누적 화면은 10/13 참고임을 구분했다. 기존 캡처를 보존해 주간6개 모두 이미지가 있다. 새 생성/이미지 편집·FModel 추출·재임포트·map/asset save·editor/PIE 제어0이다.

Notion 템플릿/본문·이미지 결속을 재조회 확인했다. 완료 및 다음 갱신 기준은 Metadata/NotionProgress_20261013/FinalVerification.json/ResumeState.json. 현재 주간: https://app.notion.com/p/3f8ec99d2c54819e92aeffcad36b4b57?pvs=204

<!-- NotionProgress_20261013_report_backfill_complete -->


## 2026-10-13T13:11:51.008812+09:00 — GiantVFX Main 실제 반영·시각 잔여 분리

GiantVFX는 Main 선택 반영 및 눈 노출/Roar helper 제거/부착·혈액 mesh 크기 후속을 완료했다. 실제 Main Armageddon 흰 판은 미해결이다. technical pass와 visual pending을 FinalVerification.json에서 분리 정정했다. 현재 Art 상태와 정확 재개는 GIANT_VFX_REFINEMENT_20261013.md 및 Metadata/GiantVFX_20261013/ResumeState.json을 따른다.


## 2026-10-13T13:18:40.096195+09:00 — Player Slash 정렬 Main 완료

OverFury 추가 KZ_Slash17쌍 제거/기존 효과 유지. 나머지33쌍은 requested shared asset을 유지하고 actual particle yaw90/initial XYscale2와 mesh/renderer·무기 geometry를 반영해 위치·각도·크기를 맞췄다. source effect1359×37/clocks/GUID와 shared asset SHA를 보존했다. 여러 실제 공격 시점·타이밍/공중 Spin 검수 및 GPU/저장/Main 검증은 Metadata/PlayerSlashAlignment_20261013/FinalVerification.json을 따른다. 별도 Parry sampler 진단은 해당 진행 작업의 이슈이며 이번 Slash의 asset 수정에 포함하지 않았다.

<!-- PlayerSlashAlignment_20261013_complete -->

## 2026-10-13 — 패링 사진 후속 구현 반영 / 외관 일치 검증 잔여

Reference 폴더17+Guard GA1 및 기존 runtime2/DEV1에 패링 광막·별도 굴절·finite camera shake/FOV를 반영했다. 최신 Native14(17상황/camera/FOV/만료)/Shader02(parent6/MI9) passed, CurrentVerification.json에 현재 SHA와 보존/한계를 기록했다. 실제 밝은 DevMap에서 broad violet halo의 사진 일치는 아직 미확정이고 HeinMach 비교가 남았다. 원작 stripped shader/임시 CPU·색·alpha adapter를 구분하며 완전 동일/완료로 기록하지 않는다. 자세한 도메인 정본과 continuity의 최신 패링 절을 따른다.


## 2026-10-13T14:14:46+09:00 — Player·인간형4종 SFX 현재 동작·상호작용 Main 완료

현재936 animation/58 ComboDefinition/5 CharacterDefinition/84 grant를 조사해 원작 상위 Composite 음원 누락, 저장되지 않았던 공격 audio array binding, 같은 발/초기 cry·Guard 성공 중복을 보완했다. Main 최종1682 audio/control occurrence·527sequence(소리 제거 callback-only3 포함)·35combo/174attack window·Dodge8 성공음이 저장됐다. 원작 추가51cue/248new wave(262recipe, 동일 원본 재사용14), fallback0이며 원래 chunk0/chunk1 index에서 필요한 metadata/bank/media만 표적 추출했다. Yetuga/Apes·map/ambient 재author0이다. 원작 random choice/gain/media tail/source curve와 현재 Root/FPS/physics/VictimFront·Slash/Parry/피격 VFX 제거를 보존했다.

새 사본의78 actual mesh montage/모든 예상 cue·cancel/loop cleanup·AT actual owner destroy/PCM tail passed, Main 실제 CombatEffect/PlayerAttackCollision/Guard/Parry17/Dodge11 및 현재524+callback3 fresh saved/native pose/curve/root/GUID·non-audio 보존이 passed다. actual master peak.5539245605/RMS.0203483704/clipping0, actor destroy 후 tail peak.0198669434가 관측됐다. Main parry의 near-full-scale.999847을 보고 해당 cue 상단만 TEMP gain.5(−6.02dB)로 낮췄고 실제 재검증 peak.768127/clipping0이다. Dodge 성공은 원본 SC_efx_pc_common_justdodge를 기존 승인 callback에서 실행당 한 번 재생한다. 570asset 선택 전달은 baseline SHA guard/atomic 교체로535새 전달+35동일/lock0/conflict0이며 MainSavedFinal01은1682/527/174/8/238cue success다.

TEMP voice.85/foot.9/weapon1, source stop 최소.08초, native reverb send.05/.15 및 원작 native callback이 직렬화되지 않은72 first-pose adapter를 원작 직접값과 구분한다. 유한 단발음은 action transition/owner destroy 뒤 자연 끝음 유지, loops/source stop만 fade한다. Wwise SDK DSP·모든 장치 주관 청취·Shipping·완전 원작 음향 일치는 미검증이다. 실패도 보존했고 현재 필수 잔여0이다. 정확한 원본/event/field·타임라인/수치·WAV·Main SHA는 Metadata/HumanoidSFX_20261013/FinalVerification.json 및 같은 root의 계획/보고를 따른다. 이전 prepared37이나 전체 extraction/author/old DLL 복원을 반복하지 않는다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

GiantVFX는 Main 선택 반영 및 현재 시각 검수를 완료했다. 처음155case/465PNG와 GAS8+objects3 검증에 더해 최종Saved84 보존, 연속23/69PNG 및 실제 Armageddon GAS 화면/취소 정리를 확인했다. 흰 사각/몸체 투영은 Armageddon_Start의 retained FMI_Decal_Deferred_D_02였다. PS/충격파 숨김에도 지속되고 decal-only 숨김에서 사라지는 증거와 전용 non-emissive spatial alpha 수정으로 해결했다. 원래 noise/얼음/돌 파티클은 제거하지 않았다. 후속 Main 변경은 기존sequence1의 material reference 및 새owned shader2뿐이다. FT_Dirt_Tex_01.R density·radial envelope·KZGiantDecalOpacity .12는 편집 가능한 TEMP 복원이며 roughness .1의 원작 출처 및 숫자 구분은 GIANT_VFX_REFINEMENT_20261013.md 마지막 절에 기록했다. 원작 cooked VAT/distortion/pixel 완전 일치는 미확인이다. exact 완료/실패/backup/current PNG는 Metadata/GiantVFX_20261013/FinalVerification.json, SnowDecalDelivery01, MainSnowDecalFinal01을 따른다. 상태는complete_current_implementation_and_review/잔여0이며 기존 author/Shader clone/전체 전달을 반복하지 않는다.

## 2026-10-13 — WeakAttack01 Slash 후속 Main 완료

첫 약공격 추가 Slash의 추적 손을 실제 내려베는 Weapon_R로 수정하고 원래/추가 첫 타격4 객체에 TEMP 전방35cm·XY1.15배를 적용했다. 실행1/Notify 설명1/기존 DEV1/asset1이며 새 runtime 구조0. Main build/fresh saved/actual18+Brutal4·GPU70/actor yaw90 성공, 다른 효과/clock/GUID/audio/피해/Physics 및 OverFury 상태 보존. 정확 상태·한계·후속은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json과 ResumeState.json, 해당 도메인 표현 정본 마지막 절이다. 이전 mirror 후보/stale private Source/DLL 전달을 반복하지 않는다.
## 2026-10-14 — 두 거인 부위 파괴 SFX/VFX Main 반영

Apes/Yetuga 원본 PartGroggy Start/Loop/End notify의 SFX·VFX를 전용 montage에서 재생한다. 화면을 덮던 원본 VAT 혈액 메시 3개는 두 종 전용 PS 복사본에서 투명 기술 재질로 가리고, 원본 sprite 혈흔·연기·방울과 timing을 유지했다. Main RHI 두 종/8캡처에서 큰 붉은 판이 사라지고 작은 혈흔·먼지가 유지됨을 확인했다. 원작 VAT shader/청감의 완전 일치는 미확인이다. 세부 바인딩·한계는 `GIANT_VFX_REFINEMENT_20261013.md`의 2026-10-14 절과 `Metadata/GiantReaction_20261014/MainPIEFinal`을 따른다.

## 2026-10-14 — 최종 RHI 재검증

설정 변경 후 Main 빌드와 Apes/Yetuga PartGroggy RHI 재검증이 통과했다. 최종 화면은 `Metadata/GiantReaction_20261014/MainPIETuningFinal`, 원본 VAT/청감 미확인 범위와 hash는 `FinalVerificationTuning.json`을 따른다.

## 2026-10-14 — 플레이어 공격음 준비본 Main 적용

기존 에디터 파일 잠금 때문에 남아 있던 `DA_Player_Combo_Definition`의 오디오 필드 수정본을 Main에 선택 반영했다. 적용 직전 Main SHA가 기록된 원본과 같음을 확인하고 백업했다. 새 프로세스의 저장 에셋 readback은 26 node/60 attack window에서 공통 적중음 연결 0, 비오디오 node 전부 동일, 테스트 중 package save 0을 확인했다. 실제 PlayerAttackCollision 녹음에서도 재질별 body hit이 들리고 중복 common cue는 관측되지 않았으며 PCM clipping 0이다. 다른 완료 VFX·물리·UI 준비본은 각각의 Main 최종 영수증과 대조했고 과거 작업 폴더를 일괄 복사하지 않았다. 상세 해시와 증거는 `Metadata/MainIntegration_20261014/FinalVerification.json`이다. 진행 중인 GiantGrabWarning/GiantCamera 작업의 최종 외관·청감은 이 완료 범위에 포함하지 않는다.

## 2026-10-15 — Main 반영 유지 및 이전 진행 중 표현 작업 확인

앞선 10/14 통합 검사에서 제외했던 잡기 경고 VFX/SFX와 카메라는 이후 Main 저장·기존 RHI 검증을 완료했다. 오늘 별도 새 프로세스에서 잡기 경고 7개, 카메라 48 에셋/86 이벤트, 후속 Player Slash 5 몽타주/33쌍과 원래 효과 882개 보존을 재확인했다. 플레이어 Combo의 중복 공통음 연결 0도 유지된다. 준비본 추가 전달은 필요하지 않았고 에셋 저장 0이다. 현재 근거는 `Metadata/MainIntegration_20261015/FinalVerification.json`; 원작 외관·청감의 완전 일치 한계는 기존 도메인 continuity를 유지한다.


## 2026-10-15 — Apes·Yetuga 잡기 경고 Main 저장본 확인

메인 반영 여부 재확인 요청에 따라 새 UE 에디터 프로세스에서 7개 잡기 애니메이션의 원본 경고 ParticleSystem·SoundWave 연결을 읽었다. 7개 파일 SHA가 2026-10-14 최종 저작본과 모두 같고, 원본 경고 PS의 9 emitter와 4.360875초 SoundWave, UI_Chest/카메라 배치/구간 종료 분리 설정이 유지된다. game asset save 0 및 검사 전후 모든 대상 SHA 동일이다. 따라서 미반영·중단된 임포트/Notify 적용분은 없다. 증거는 `Metadata/GiantGrabWarning_20261015/SavedReadback.json`, 원본·시각 검증·shader 한계는 `GIANT_VFX_REFINEMENT_20261013.md`의 2026-10-14 잡기 경고 절이다. 오늘 새 원본 추출·shader 저작·PIE 화면 검사를 수행한 것으로 읽지 않는다.

## 2026-10-15 — Yetuga 작은 눈먼지 격자 표시 Main 수정 완료

9x9 T_Smoke03_SubUV_9x9 atlas 전체가 1x1 card 안에 표시되던 작은 snow layer를 프레임별 R-density sampling/보간으로 교정했다. 전용 기존-parent 복사1 + 기존 A05/A06 instance parent2, Main 총3 package 저장 완료다. PS23/보호39/앞선 사망 데칼 수정8은 SHA 동일, 큰 눈먼지/원래 위치·속도·수명·빈도·alpha 정책은 유지했다. source 이동·행동6/particle7/actual GAS2 총15 fresh D3D12 재생 Success/compile failure0 및 SideMove/TurnBackRun 전후 화면 확인. frame clock은 original shader 미확인의 normalized-age TEMP 복원이고 원작 FPS 직접값이 아니다. 게임 Source/Config/DLL·animation·texture 변경0, 빌드 재실행0. 정본은 GIANT_VFX_REFINEMENT_20261013.md 최신 절과 Metadata/YetugaSnowLayout_20261015/FinalVerification.json이다.


## 2026-10-15 — CombatFeel 사용자 지정 패링 연결 완료

메인 Guard의 요청 KZ_Parring_Distort와 기존 Brutal 접촉 burst3개의 저장·fresh readback·실제 D3D12 패링17 검증을 완료했다. full9 임시 잔상 연결은 Author02 접촉3 연결로 대체했고 original Niagara/PS/material/Brutal montage 자체는 보존했다. 현재 외관과 TEMP 수명·shader 미확인 경계는 PLAYER_PARRY_SOURCE_20261012.md의 최신 절. 저장/검증 근거: `Metadata/CombatFeel_20261015/FinalVerification.json`. 관련 재author 대기나 미전달 에셋 없음.



## 2026-10-15 — HeinMach 색감·빨간 혈흔·VFX 색 보존 완료

Main map2/Definition7/Surface VFX root95/혈흔 Ground1, 총105 package 적용·현재 SHA·fresh saved readback 검증 완료. 원작 사진 기준 TEMP 청회색 조명/노출과 진한 빨간 혈흔을 적용하고 Arcane Kuwahara 연결2를 제거했다. 정확한 기존 Brutal 혈액 PS를 플레이어/몬스터6종 승인 피격에 연결했다. 현재321 system을 두 맵에서 native 촬영했으며275쌍이 .2s에 가시,46은 다른 대상/파라미터/시간대가 필요하다. 왜곡2종은 같은 opaque 배경3회씩 재검사하여 맵 색 오염이 아님을 확인했다. 빌드/실제 피격·가드·6종 혈흔 회귀 성공. 원작 전용 shader/pixel 일치·Shipping 성능 측정은 미확인이다. 수치/검증/재개는 HEINMACH_COLOUR_VFX_20261015.md 및 Metadata/HeinMachColourVFX_20261015/FinalVerification.json, ResumeState03.json을 따른다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 ? Yetuga?Apes PartGroggy ?? ?? ?? ??

Main ?? Damage_PartGroggy_Loop/End ?2?, ?4package? root lock? Reference Pose? ????. ?? ?????/????Notify?Skeleton??? Root ??? ????, ??522.148cm locked root offset?0?? ????. ?? ??170/510 saved poses ? Main D3D12 weak-part Start/Loop/End6?? ??, ???166?? ??, probe??/??backup4 ?? ???. ?? Root '??' ??? flag/??? pose-origin ??? ???? ?? ENEMY_ANIMATION_ORGANIZATION_20261007.md ?? ???. ?? `Metadata/GiantRootUsage_20261015/FinalVerification.json`. ???/?? ?? ??.


## 2026-10-15 — Notion 표현 작업·스크린샷 상세 기록 완료

사용자 요청으로 김민재[언리얼11기] Notion의 기존 기록을 보존하며 Fab7, 공격/패링/회복/피격·사망·거인 VFX, SFX, 보조 물리, UI와 HeinMach 색감·강설의 실제 적용·검증/한계를 상세히 정리했다. 최신 통합 PROTO는 https://app.notion.com/p/3faec99d2c548131b97bd0bbd32b8b9f 이며, 후속 검증 PROTO는 https://app.notion.com/p/3faec99d2c54813ab44bf825823f1c50 이다. 현재 패링 KZ_Parring_Distort+Brutal 접촉3, Player 보라·파랑 피격burst 제거 뒤 빨간 승인혈흔, 사망 흰decal8 제거와 Yetuga9×9 sampler의 서로 다른 원인/수정·원본/TEMP를 구분했다.

Main HeinMach를 별도 소유 D3D12 PIE(PID26284)에서 새로 촬영한 Player/Entry/OpenSky 3장과 기존 기능별 전후/패링/HUD/잡기 화면을 합쳐 고유 PNG12장을 Notion native 파일로 첨부·직접 검수했다. 새 캡처는 Capture.success=true/asset_saves=0/dirty_content=[]/actor10009이며 정상 자체 종료했다. 이 3장의 실제 viewport 해상도는998×426이고, 별도 HUD/패링1600×900 화면과 구분했다. 사진은 카메라 시간 곡선·SFX 청감·성능의 증거로 과장하지 않았다.

신규 PROTO2/일감27(명시 범위 완료19·후속8)/일일보고2를 만들고 기존 프로젝트4·상위일감7·10/13 일일/현재 주간·메인을 보완했다.45페이지 재조회, 모든 Task5개 필수항목·27개 report뷰 self filter·기존본문13개/메인DB6개 보존·이미지12/JSON첨부1 및 로컬레퍼런스42개 존재를 확인했다. 조건 의존 VFX46·원작 custom shader/VAT/Wwise DSP/pixel·연속 플레이/Shipping은 후속으로 유지한다.

이번 문서화의 게임 Source/Content/Config 수정·새 build·전투 suite 재실행0, 외부 editor 제어0이다. 증거/페이지ID/이미지 SHA·크기/전후 Notion본문과 정확한 다음 절차는 Metadata/NotionProgress_20261015/{FinalVerification,ResumeState,EvidenceIndex,ScreenshotManifest,ScreenshotFiles}.json 및 CaptureHeinMain01/Capture.json을 따른다. 문서 작업은complete/잔여0이며 후속 게임 일감8개는 별도 계획이다.

<!-- NotionProgress_20261015_complete -->


## 2026-10-15 — GateCube 포탈과 Yetuga 전장 도착점 Main 완료

Main HeinMach에 Gameplay/YetugaPortal의 portal/arrival2 actor 및 전용 VFX4asset을 추가했다. 배치 단계의 GateCube transform과 기존10010 actor class/transform, 공유 포탈 원본4파일을 보존했다. 이후 동시 저장의 PlayerStart1 수정은 유지했으며 최신10009 actor 동일과 해당 전후 transform을 별도로 기록했다. 상대 yaw90/발광 노출 보상과 전장 내부 지면 배치를 RHI06 실제 walking/3화면 및 fresh Readback04에서 확인했다. 최신 map을 과거 Work map으로 교체하지 않는다. 세부·수치 출처·한계는 HEINMACH_YETUGA_PORTAL_20261015.md 및 Metadata/HeinMachPortal_20261015/FinalVerification.json을 따른다.

<!-- HeinMachPortal_20261015_complete -->

## 2026-10-15 — GateCube 큐브 메시 제거 완료

메인 HeinMach의 GateCube에서 Cube 메시 연결을 제거해 에디터/게임 양쪽에서 큐브 geometry가 보이지 않게 저장했다. 액터 위치와 포탈 이펙트·도착점·진입 충돌·암전 설정은 유지한다. 새 프로세스의 `Metadata/HeinMachPortal_20261015/GateCubeVisibilityReadback02/Result.json`에서 `mesh=null`, map save0, 저장 SHA 동일과 포탈 계약 보존을 확인했다. 최신 map SHA는 `7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728`이며 앞선 포탈 완료 영수증 이후의 승인된 추가 변경이다. 상세는 HEINMACH_YETUGA_PORTAL_20261015.md 최신 절. Source/공유 Cube/VFX 변경·새 build/PIE0, 필수 잔여0.

<!-- HeinMachPortal_20261015_gate_cube_removed -->


## 2026-10-15 — HeinMach BlueB·Spinning 표현 Main 완료

HeinMach 노출 보정을−1.1→−2.15EV로 낮추고 TEMP 청회색 direct/sky/fog를 적용했다. 새 화면 필터 없이 발광 VFX 역노출 보상을 유지한다. Spinning KZ_Slash0, OverFury 사본6/Charge3+2 조합과 Helix 회색 면 제외를 Main3 asset에 반영했다. 동시 포탈/몬스터/PlayerStart를 최신 map 기준으로 보존했다. saved 검사·Main DevMap 두 suite·HeinMach 실제3시야/회전 공격·충돌 검수 완료다. HeinMach broad suite의 별도 rear-Brutal fixture 실패는 통과로 재명명하지 않는다. 원작 shader/pixel/Shipping 및42조건 한계는 유지한다. 정본 HEINMACH_BLUE_SPINNING_20261015.md, Metadata/HeinMachLookSpin_20261015/FinalVerification.json. 필수 잔여0이다.

<!-- HeinMachLookSpin_20261015_complete -->

## 2026-10-15 — Yetuga 원작 전투 음악 Main 임포트

원작 chunk0의 Media446487212 / Music\boss\bgm_boss_yetuga_82_4on4.wav를 fresh 표적 추출하고 HeinMach battle branch의 first/loop·layer/trim/gain을 렌더했다. Main `/Game/Audio/Original/Music/Yetuga/`에 Intro/Loop Wave2+music SoundClass/Cue2를 추가했고 기존 SFX/레벨 저장0이다. SourceMusic.json/Import01/Import.json에 원본·계산 경계·asset hash를 기록했다. 원작 native DSP/sample parity·실기 청취는 미확인이다. 정본은 YETUGA_BGM_SOURCE_20261015.md이며 실행 계약은 Engineering 포탈 문서에 분리했다. 사용자 결정으로 진입 후 사망/처치/이탈 종료 없이 loop한다.


## 2026-10-16 ? HeinMach ??? ?? ?? ?? Main ??

PlayerStart?Yetuga ?? ? Yetuga ??? ?? ??? ???? actor4,258?, instance9,137?(????8,296/??? ?? ??841)? Main?? ????. ?? actor5,764/instance5,639, monster10/PlayerStart1/???BGM ??? ?? look ???. Depth552????48?? ? ?? full-editor ??? fresh Main ?? ??/transform ?? ??, ??40/??13 ? ?? route8 complete+3 partial ???. .umap37,790,567?22,693,731bytes. ?? HEINMACH_ROUTE_PRUNING_20261016.md, Metadata/HeinMachRoutePrune_20261016/FinalVerification.json. ?? ??0, ?? Shipping ????/FPS ??0.


## 2026-10-16 — HeinMach 미사용 배치 삭제 완료 (한글 기록 정정)

바로 앞 같은 작업의 깨진 한글 절은 출력 인코딩 오류이며 이 절과 HEINMACH_ROUTE_PRUNING_20261016.md를 따른다. Main은 PlayerStart→포탈/Yetuga 전장과 사용 시야를 보존한 actor4,258/instance9,137 삭제본이다. instance는 foliage8,296+미사용 경로 충돌841이다. 잔존 actor5,764/instance5,639, 몬스터10/PlayerStart1/포탈·BGM·전역 룩 보존. Depth552뷰/전후48쌍 및 fresh Main의 잔존 설정·transform 비교 통과, 지면40/nav투영13 및 기존 경로8 complete+3 partial 유지다. 맵37,790,567→22,693,731bytes, 필수 잔여0. Source/Config 변경·공유 resource 저장·Shipping 재패키징0. 정본 Metadata/HeinMachRoutePrune_20261016/FinalVerification.json.
