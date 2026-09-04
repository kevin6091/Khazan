# Art / Resource 작업 연속성

> Art 작업이 중단되거나 완료되지 않았을 때만 하단에 인수인계 섹션을 추가한다.

## 2026-08-31 기준점

- 라이브 완성본: `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`
- 최종 감사: `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`, 26/26 통과
- 현재 알려진 미완전 영역은 원본 데이터가 없는 terrain WLM/weightmap과 fog custom shader뿐이다.
- 기존 결과 회귀가 의심되면 전체 임포트보다 최종 감사와 해당 mismatch report를 먼저 실행한다.
- 다음 Art 작업은 `ART_PROJECT_STATE.md`에서 범위를 확인한 뒤 요청에 필요한 Pipeline 또는 Knowledge 문서만 추가로 읽는다.

## 2026-09-01 완료 기준점

- 라이브 맵: `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`
- 에디터 재시작 후 최종 상태: actor 9,449, categorized 9,449, uncategorized 0, 통합 31/31 통과.
- 정적 구성: root Prop 9,104, child 27, foliage HISM 113/12,495, Landscape proxy 57, terrain preview 2.
- 렌더 표면: live MI 613, packed channel correct 583, effective Masked 496, Opaque 117, Translucent 0.
- source lighting: 89개를 원본 값으로 보존. preview environment 4개와 route inspection fill 3개가 별도 폴더에 있다.
- Fog: 50개와 SHA-256 `3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48` 유지. 이번 pass에서 변경하지 않았다.
- 최우선 재개 리포트: `HeinMach_Final_Reconstruction_Audit.json`, `HeinMach_StaticCoverage_Closure_Audit.json`, `HeinMach_VisualRoute_Audit.json`.
- 세부 회귀 감사: `HeinMach_RestoredLevel_Integrity_Audit.json`, `HeinMach_ChildRender_Integrity_Audit.json`, `HeinMach_LandscapeStatic_Integrity_Audit.json`, `HeinMach_Foliage_Reload_Audit.json`, `HeinMach_MaterialRendering_Audit.json`.
- 최종 visual capture: `Saved/Screenshots/WindowsEditor/RiderMCP/20260831-164249_viewport.png`부터 `20260831-164257_viewport.png`까지 6개이며 tag/path/SHA는 Visual Route Audit에 있다.
- 가역 백업: `Saved/ArtBackups/HeinMach_MaterialRendering_PreFix`, `Saved/ArtBackups/HeinMach_AlphaSurface_PreFix`, map backup `L_HeinMach_Environment_PreMaterialLightingFix`, `L_HeinMach_Environment_PreLandscapeStaticRestore`.
- 남은 원본 데이터 제약은 Landscape WLM/weightmap/layer graph다. 현재 geometry 위치는 exact지만 셰이딩은 recovery material이다.
- 다음에 Fog, decal, dynamic skeletal prop, VFX를 요청하면 정적 환경 closure와 분리된 새 Art pass로 진행한다.
- 재개 시 source snapshot 변경이 없다면 FModel/Content 전수조사를 하지 말고 위 리포트의 mismatch만 표적 조사한다.

## 2026-09-02 완료 기준점

- 라이브 맵: `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`.
- 최신 최종 감사: actor 9,452, categorized 9,452, uncategorized 0, `all_checks_passed=true`(35/35).
- 구성: root Prop 9,104, child 27, foliage HISM 113/12,495, Landscape proxy 57, terrain 2, Fog sheet 50, source light 89, preview environment 4, route fill 5, preview volumetric fog 1.
- Fog sheet transform hash는 `3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48`, source light hash는 `c87a605a9227f5a4f7426d27a8b4f6bbdc6eeed1baa1f138672f9616e1f3c0f7`이다.
- Fog base material version 4와 Landscape recovery material version 2를 사용한다. 두 material 모두 최신 표적 재컴파일에서 새 `LogMaterial` warning이 없다.
- root 좌표 이탈 1개는 원본 위치로 복구했고 최신 root integrity audit는 passed다.
- 재개 우선순위: `HeinMach_Final_Reconstruction_Audit.json` → 실패한 세부 report만 표적 확인 → source snapshot/schema 변경 때만 전수조사.
- 캡처 재개 규칙: HighResScreenshot 및 viewport config 조작 금지. 필요할 때만 health 확인 뒤 Rider 단일 캡처를 사용한다.
- 현재 Fog/Lighting 작업에 남은 blocker는 없다. 원본 WLM/weightmap과 proprietary `xxVolumetricMist` shader 부재는 계속 데이터 제약이다.

## 2026-09-02 최종 기준점 — 사용자 삭제 보존·최적화·튜토리얼·Light·나무

- 라이브 맵은 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`, SHA-256은 `B7EB531B09D504737CA1CC6125B201484519D8FA1D80FA0A00249482FCABFCA7`이다.
- 사용자 삭제 10개는 `HeinMach_UserExclusions.json`, exact duplicate 제거 109개는 `HeinMach_OptimizationExclusions.json`에 tombstone으로 남아 있다. 둘 다 복원 금지다.
- 사용자 편집 직후 백업은 `Saved/ArtBackups/HeinMach_UserEdited_BeforeOptimization_20260902_161357/L_HeinMach_Environment.umap`이며 SHA-256은 `17581BC984432060C3B194A9871D42E884024F7F23402EEE3E70A635768AA799`다.
- 수동 transform 1개는 `HeinMach_ManualOverrides.json`에 보존돼 있다. origin이 원본과 다르다는 이유로 자동 복구하지 않는다.
- DualAxeSword 튜토리얼 Art anchor는 PlayerStart 1개와 enemy marker 2개다. 실제 AI/UI/gate/loadout은 아직 Engineering 범위다.
- source LightColor/관련 property 및 route fill color mismatch는 0개다. source light 89개 transform hash는 `c87a605a9227f5a4f7426d27a8b4f6bbdc6eeed1baa1f138672f9616e1f3c0f7`로 유지됐다.
- 흰색 fallback 가지 slot 27개는 recovered material로 교체됐고 placeholder는 0개다.
- 최종 인벤토리는 actor 9,336, root 8,992, child 27, foliage 113/12,495, Landscape 51, terrain 1, Fog 50, source light 89, preview environment 4, route fill 5, preview volumetric fog 1, tutorial 3이다.
- `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`은 `all_checks_passed=true`, 39/39, uncategorized 0이다.
- 재개 시 `HEINMACH_OPTIMIZATION_TUTORIAL_LIGHT_TREE_2026-09-02.md`와 exclusion/override 3종을 먼저 읽고 실패한 report만 표적 조사한다.

## 2026-09-03 최종 기준점 — HeinMach 보존 및 StormPass 환경 복원

- HeinMach는 사용자 exclusion 18개를 복원하지 않은 actor 9,328개 상태다. `HeinMach_UserExclusions.json`을 먼저 확인하고 사용자가 지운 항목을 재생성하지 않는다.
- HeinMach dry-tree live recovered binding은 86개이며 suspicious/white fallback은 0이다.
- StormPass 라이브 맵은 `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment`다.
- StormPass 최종 actor 14,381: root 13,050, child 551, Landscape 456, foliage 218/21,259, Light 53, Fog 53.
- native WaterBody 두 곳은 actor-level `WaterMaterial`을 slot 0에 복구했고 WorldGrid/Default material은 전체 맵에서 0이다.
- 최신 정본은 `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json`, `status=passed`, failed stage 0이다.
- Water 정본은 `StormPass_NativeWaterMaterials.json` 및 `StormPass_NativeWaterMaterial_ReloadAudit.json`이며 hierarchy check 79, failure 0이다.
- Fog는 모든 환경 요소 이후 마지막으로 다시 적용했고 `StormPass_Fog_ReloadAudit.json` failure 0이다.
- 최종 맵 SHA-256은 `3719E53A6B2CEBED831DA586E04BFF13C1C5B76DAE5D2A5FDEA4C45DB42B03CA`다.
- 최종 복사 백업은 `Saved/ArtBackups/StormPass_Verified_Final_20260903_145740`; 라이브 `.umap`과 hash가 같다.
- 재개 순서: 최종 통합 감사 → 실패 stage의 reload audit → 해당 label/package만 표적 조사. source snapshot/schema가 그대로면 전수조사하지 않는다.
- 현재 요청 범위에 남은 blocker는 없다. Gameplay/C++/캐릭터 이동 로직은 작업하지 않았다.

### 2026-09-03 최종 hash 갱신

- Water master의 source black default texture까지 닫은 뒤 최종 SHA-256은 `F63A6C8D66C3F5D6A677EF00B2AECDB4406A6B229AB7C4DB1E4D42F25CC2C91E`로 갱신됐다.
- 위 `3719...` hash와 `StormPass_Verified_Final_20260903_145740`은 직전 체크포인트로만 보존한다.
- 재개 정본 백업은 `Saved/ArtBackups/StormPass_Verified_Final_20260903_151800`이며 핵심 report/metadata 5개와 동일 hash `.umap`을 포함한다.

## 2026-09-04 StormPass 최종 기준점 — 위치·Light·머테리얼·Fog

- 라이브 맵: `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment`.
- 사용자 요청 범위에 따라 StormPass 환경 콘텐츠만 다뤘다. `KhazanAnimInstance.cpp`를 포함한 source code, 캐릭터 로직, HeinMach 콘텐츠는 변경하지 않았다.
- 최종 인벤토리: actor 14,408 = root 13,050 + child 551 + Landscape 456 + foliage 218 + source Light 53 + environment profile 27 + Fog 53. foliage instance는 21,259개다.
- 최종 배치 감사의 최대 오차는 root location 0 cm/rotation `0.00009155°`, foliage location 0 cm/rotation `0.00000639°`, Light location 0 cm/rotation `0.00000171°`, environment location `3.64e-12` cm, Fog location 0 cm/rotation `0.00000242°`다. 모든 tolerance failure는 0이다.
- environment profile 27개의 class/transform/property failure는 0이다. Directional Light scale `(1,1,1)`과 sky/cloud collision-off 교정이 포함된다.
- 나무 material repair는 MI 9개/733 slot, false-emissive repair는 MI 5개/44 slot, ore repair는 MI 4개/860 slot이며 각각 failure 0이다. 활성 parent는 `M_SP_SourceTreeFoliage_V2`, `M_SP_SourceOre_V2`다.
- Fog 53개는 다른 모든 변경 뒤 마지막으로 다시 적용했으며 Standard 51 + Local 2, failure 0이다.
- 정본 report는 `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json`; `status=passed`, failed stage 0, material slot 17,979, null/default fallback 0이다.
- 정본 `.umap` SHA-256은 `9A4B02BE61CA734265B91490828B6369B69CC3428D7A82726CEA215B770D9191`, 크기는 43,709,400 bytes다.
- 정본 백업은 `Saved/ArtBackups/StormPass_Verified_Final_20260904_111819`이며 맵 hash가 라이브와 일치한다.
- 재개 시 최종 통합 감사의 실패 stage만 표적 확인한다. source snapshot/schema가 바뀌지 않았다면 FModel 전수 추출을 반복하지 않는다.
- 알려진 데이터 제약은 cooked proprietary material graph topology 부재와 irregular BSP Post Process Volume 6개의 transformed-bounds proxy 표현뿐이다. source metadata의 point/plane 정보는 보존돼 있다.

## 2026-09-04 최종 기준점 — StormPass sky/Fog clipping 교정

- 라이브 맵은 `/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment`이며 actor 14,408개 상태다.
- 사용자가 지운 HeinMach 항목과 HeinMach 맵 전체, `KhazanAnimInstance.cpp`를 포함한 source/gameplay/character logic은 작업 범위 밖으로 보존했다.
- 화면 수평 밴드의 주원인은 Fog sheet가 아니라 horizon fade 없이 depth test까지 꺼져 있던 cloud hemisphere였다. sky는 raw wrapped USD V gradient, Fog sheet는 `PixelDepth` fade가 각각 seam/근접 절단 위험을 갖고 있었다.
- 활성 visual parent는 `M_SP_SourceSky_V2`, `M_SP_SourceCloud_V2`, Fog V2 3종이다. Fog V2는 `PixelDepth`가 없고 camera distance + `DepthFade` + facing fade를 사용하며 모두 depth test가 활성화돼 있다.
- environment assignment는 sky V2 1개와 cloud V2 2개가 정확하다. Fog parent binding은 45/6/2, 총 53개이며 reload failure 0이다.
- background mountain actor의 transform은 source metadata와 일치해 수정하지 않았다. 검은 원경은 stale SkyLight capture를 다시 잡아 해결했다.
- 최신 통합 감사 `Saved/ImportReports/StormPass_Final_Reconstruction_Audit.json`은 `status=passed`, failed stage 0이며 `visual_material_integrity.failure_count=0`이다.
- Fog 리로드 감사 `Saved/ImportReports/StormPass_Fog_ReloadAudit.json`은 location/scale 오차 0, rotation 최대 `2.4148365e-6°`, failure 0이다.
- 최종 맵은 43,709,418 bytes, SHA-256 `E1007AFFEAE22AF49599690EB3CE67582B1B43FC25C8D3E6AFBE17B76C03361D`다. dirty StormPass map/content package는 0이다.
- pre-fix 백업은 `Saved/ArtBackups/StormPass_PreSkyFogVisualFix_20260904_121446`이다.
- 재개 시 먼저 최종 통합 감사와 Fog reload audit만 확인한다. `visual_material_integrity`가 실패할 때에만 해당 V2 parent/assignment를 표적 조사하며, source snapshot/schema가 바뀌지 않았다면 FModel 전수 추출을 반복하지 않는다.
- 현재 요청 범위에 남은 blocker는 없다.

## 2026-09-04 최종 기준점 — HeinMach 전역 Fog·FogSheet 무결성 교정

- 라이브 맵은 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`, actor 9,328개 상태다.
- 작업 범위는 HeinMach 전역 Fog, FogSheet, 환경 머티리얼/셰이더와 배치 검증뿐이다. `KhazanAnimInstance.h`를 포함한 Source/Gameplay/캐릭터 콘텐츠는 변경하지 않았다.
- 사용자 exclusion 18개 + exact-duplicate optimization exclusion 109개 = 127개 tombstone은 수정 전후 모두 부재한다. 사용자 삭제 항목을 복원하지 않는다.
- 활성 Fog parent는 `M_HeinMach_FogSheet_Preview_V5`다. 75 expression, `PixelDepth` 0, camera/world distance + `DepthFade` + facing fade, depth test 활성, one-sided다.
- FogSheet 50개는 source placement/material/parameter/sort/component policy와 일치한다. location/scale 최대 오차 0, rotation 최대 `4.9072265539962245e-6°`, mismatch 0이다.
- `HM_PreviewVolumetricFog`는 정확히 1개다. cutoff 0, albedo `(158,177,196)` RGB, volumetric enabled이며 기존 보수적 preview density를 유지한다.
- 나무 live 감사 결과 1,123 actor/1,669 slot/100 material에서 suspicious 0이다. 전체 관리 환경 material은 605종/11,460 slot, channel/opaque-parent repair 필요 0, effective Translucent 0이다.
- V5 재컴파일과 저장 후 level reload를 완료했다. `HeinMach_Final_Reconstruction_Audit.json`은 `all_checks_passed=true`, 43/43이며 uncategorized 0이다.
- 최종 맵 SHA-256은 `B209ACB34FCEFC3D6F11EE47D098107976CA30B6A84CFA16335EA6638C2812E0`이다. pre-fix 백업은 `Saved/ArtBackups/HeinMach_PreFogReview_20260904_143116`, 전후 캡처는 `Saved/ArtValidation/HeinMach_Fog_Review_20260904`에 있다.
- 재개 시 `HeinMach_Final_Reconstruction_Audit.json` → `HeinMach_FogIntegrity_Review.json` → 실패한 항목만 표적 확인한다. source snapshot/schema가 바뀌지 않았다면 전수 추출 또는 비-Fog actor 복원을 반복하지 않는다.
- 알려진 데이터 제약은 cooked proprietary Fog graph와 WEP 구역별 `FOG_Deep`/`FOG_Dark` controller 부재다. 현재 전역 Fog는 안정적인 UE5 preview이며 원본 런타임 지역 전환의 완전 복제는 아니다.
- 현재 요청 범위에 남은 blocker는 없다.
