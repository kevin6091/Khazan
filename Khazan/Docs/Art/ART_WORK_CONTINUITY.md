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

## 2026-09-07 진행 중 — StormPass 실제 플레이 경로·표면 렌더링

- 기존 `passed` 감사가 실제 화면 품질을 보장하지 못함을 원본 시작 카메라에서 확인했다. 상세 근거/재개 문서: `STORMPASS_PRESENTATION_REVIEW_2026-09-07.md`.
- 에디터를 직접 실행해 StormPass 14,408 actor를 열었다. 원본 시작 PlayerStart는 아직 없으며, 기존 Source/HeinMach/사용자 삭제는 건드리지 않는다.
- 초기 USD 표면 검사 542 MI 중 534개의 packed-channel 오류를 발견했다. 54개의 effective Translucent도 원본 full-package JSON과 다시 대조한다.
- 새 수리 도구: `Scripts/StormPass/repair_stormpass_surface_rendering.py`. `audit()`는 현재 상태를 보고하고 초기 plan을 보존한다. `repair_batch(offset, limit)`는 plan의 stable index 범위를 백업 후 수정한다. 실행한 batch는 `Saved/ImportReports/StormPass_SurfaceRendering_Batch_*.json`에 남는다.
- 재개 시 먼저 `StormPass_SurfaceRendering_Plan_20260907.json` / 최신 audit / batch report를 읽는다. 완료 batch를 무조건 재실행하지 말고 audit mismatch 경로만 재확인한다.
- 맵 원본 백업은 `Saved/ArtBackups/StormPass_PreRoutePresentation_20260907`. 조명/PP 실험값은 원래 상태로 되돌렸으며, Boss Phase 2/Clear의 임시 editor 숨김만 비교를 위해 남아 있다. 이 상태는 최종 표시 정책이 아니다.
- 경로 metadata `StormPass_PlayableCameraAnchors.json`에는 정확히 18개 spawn anchor, 26개 streaming volume이 있다. 원본 Landscape 위 덮임은 이 18곳에서 발견되지 않았다.
- 남은 작업: USD 표면 수정 종료, 원본 단계별 표시 복구, 실제 PlayerStart 및 편집용 경로 카메라, 조명·Fog 최종 검증, 에디터 재시작 감사, 오늘 작업 commit/main push. 아직 완료/푸시하지 않았다.

## 2026-09-08 09:47 KST 재개 — Bad Request 신고 후 저장 상태 확인

- 사용자에게 `{"detail":"Bad Request"}`가 표시돼 작업이 중단됐다. 확인된 별도 오류는 49개 MI 일괄 호출의 MCP 180초 응답 timeout이며, 두 오류가 동일 원인이라는 근거는 없다. 실패 요청의 HTTP 상세가 없으므로 원인 확정/재발 방지 보장을 하지 않는다.
- UnrealEditor PID 34500은 정상 응답하며 중단 전 작업도 실제로 저장됐다. 현재 source control adapter 538개 중 108개 완료 / 430개 잔여다. `StormPass_NativeSurfaceBatch_0030.json`까지 완료. 최초 49개 표적 샘플 + index 0–59이며 중복 1개는 생략됐다.
- 기존 USD channel/blend 검사는 542개 중 mismatch 0까지 완료했다. 이후 추가 원본 부모 추출에서 `GlobalMetallic=.4`, `GlobalRoughness=.6`, `GlobalSpecular=.2`, inherited `MetallicAdjust=-.5` 등을 확인했다. 해당 보정은 `restore_stormpass_surface_controls.py`의 별도 native adapter 작업이다. 원본 BBQ custom shading bytecode의 완전 복제는 아니다.
- canonical source chain/수치: `StormPass_InheritedSurfaceControls_20260907.json`. 모든 요청은 full package 경로 기반이며 288개 실사용 재질 + 해당 부모만 추가 추출했다. 에셋 전수 재추출은 하지 않았다.
- 맵은 14,426 actors: 원본 14,408 + source PlayerStart 1 + editor-only review Camera 17. 원본 actor 삭제/이동 0. Phase 1/2/Clear 1,335/1,098/698개는 persistent editor layer + game visibility/collision 상태로 분리했다. 현재 `traversal` 표시 상태다.
- 수레 `WP_BANTU_Cart_Wood_002`의 source LOD0 section index `[0,1,2,3,5,4]`로 3/4/5 슬롯을 교정했다. 원본 중복 material index가 USD에서 deduplicate됐던 문제이며 `StormPass_CartSectionCorrection_20260907.json`에 근거가 있다.
- 재개 체크포인트로 StormPass 맵만 명시적으로 저장했다. 이 조명은 아직 최종 검증 전: SkyLight specified source cube/intensity1.2/lower-hemisphere color 활성, PP shadow gain1/film slope.88/ambient cubemap2.5, Lumen 원래 설정. 기존 전역 Fog/Fogsheet V2는 변경하지 않았다.
- `snapshot_user_work.ps1 -Mode Verify`: 기존 사용자 파일/삭제 258개 전부 동일. Source/Animation/HeinMach 변경 없음. commit/push 미실행.
- 재개 순서: native adapter index60부터 10개 이하 짧은 호출로 진행(이미 완료된 MI는 readback으로 생략) → missing SSS 25개 표적 검토 → 실제 활성 viewport camera + 전체 editor window 캡처로 시각 확인 → 조명/Fog 최종 확인 → fresh-editor 및 Git 검증/commit/main push.
- `take_screenshot(kind=viewport)`는 4-pane 구성에서 비활성 widget의 이전 화면을 반환할 수 있다. 레이아웃 변경 없이 `kind=editor_window`를 사용하고, camera는 `LevelEditorSubsystem.get_active_viewport_config_key()`로 실제 활성 key를 확인한다. HighResScreenshot/viewport layout 변경/forceLive 추정 사용 금지.

## 2026-09-08 10:12 KST 추가 체크포인트 — native surface 완료 / PNG import 경로 교정

- 짧은 batch 0060–0530 완료. `StormPass_NativeSurfaceControls_Audit.json`은 material_count538 / failures0이며 모든 MI가 개별 저장됐다.
- 이후 첫 PNG(`BASE_Black.png`) 자동 임포트에서 에디터가 종료됐다. 이는 앞서 신고된 HTTP Bad Request와 별도 사건이다. 로그의 직접 원인은 `Interchange`가 `TaskGraph.cpp:705 ++Queue(QueueIndex).RecursionGuard == 1` assert를 발생시킨 것이다. Rider의 `RunScript` game-thread callback 안에서 동기 Interchange import가 실행됐다.
- 신규 texture import manifest는 아직 만들어지지 않았고, 25개 Subsurface 단계는 미실행이다. 저장된 맵(14,426 actors), 538 MI 및 기존 사용자 변경은 유지된다.
- 같은 live 자동 임포트는 재시도하지 않는다. `AssetTools.cpp:3566–3569`에서 `SpecifiedFactory == nullptr`일 때만 Interchange를 선택함을 확인했다. `restore_stormpass_subsurface_inputs.py`에 명시적 `TextureFactory()`를 지정했다.
- 안전한 재개: GUI 종료 상태에서 `import_stormpass_surface_textures_commandlet.py`를 unattended `UnrealEditor-Cmd -NullRHI -run=pythonscript`로 실행 → import manifest/로그 확인 → GUI로 StormPass 재시작 → SSS를 5개 이하씩 연결 → 최종 scene 검증. Source/Engine C++ 또는 프로젝트 전역 import 설정은 변경하지 않는다.

## 2026-09-08 Khazan 본 삭제 후 InGame 애니메이션 트랙 복구 진행

- 현재 상태: SK_Khazan/SKM_Khazan은 이미 HEAD와 SHA-256이 일치하며 계층은 C_P_Kazan → Root → Bip001이다. InGame AnimSequence 63개 중 DAS 작업본 8개만 root 트랙 1개로 축소되어 있고 나머지 55개와 해당 Weapons 원본은 226개 트랙을 유지한다.
- 보존: Walk/Run/Sprint loop Sync Marker 2/12/16개가 남아 있다. 현재 길이, 기존 root 키, marker, notify, curve/설정을 보존하며 누락된 225개 트랙만 복구한다. 전체 Git 롤백이나 재임포트는 수행하지 않는다.
- 백업: Saved/ArtBackups/Khazan_SkeletonRecovery_20260908_132146/manifest.json. 현재 InGame, SK/SKM/ABP, 해당 자동 저장본 82개(492,441,030 bytes)를 복사하고 각 SHA-256을 검증했다.
- 마지막 검증: /Game/_Recovery/KhazanSkeleton_20260908 아래 복사본 8개의 225개 트랙 복구 및 모든 프레임 RAW pose 비교가 통과했다. 원본 시퀀스의 길이/마커/설정과 root 키는 그대로다. 리포트는 Saved/ImportReports/Khazan_SkeletonRecovery_prepare_20260908.json이다.
- 실패 원인: 편집된 스켈레톤을 반영하는 과정에서 시퀀스의 본 트랙 자체가 사라졌다. 로컬 UE 5.8 AnimSequencerController의 skeleton update 경로는 새 계층에 없는 트랙을 제거한다. 스켈레톤 복원만으로 삭제된 트랙이 재생성되지는 않는다.
- 남은 작업: 복사본의 compressed pose/메시 동작 확인 → 같은 8개 작업본에 누락 트랙 적용 → 별도 프로세스에서 저장 결과 검증 → 결과 문서 추가. C++/ABP 수정은 필요하지 않다.
- 재개: Scripts/Animation/recover_khazan_missing_bone_tracks.py와 prepare 리포트를 먼저 확인한다. Editor Python에서 runpy.run_path(unreal.Paths.project_dir()+'Scripts/Animation/recover_khazan_missing_bone_tracks.py', init_globals={'RECOVERY_MODE':'apply'}, run_name='__main__')를 사용한다. 스크립트는 backup hash 일치/미저장 수정 없음/복사본 8개 통과를 선행 검사한다. 적용이 일부 진행됐다면 무조건 재실행하지 말고 apply 리포트의 완료 에셋과 현재 트랙 수를 먼저 확인한다.
- 별도 확인: Sprint Stop 작업본은 이번 시작 시점에 249프레임 구간/10.375초다. 직전 문서의 114프레임 구간/4.75초와 달라 사용자에게 길이 선택을 질문했으며 답변 전에는 현재 길이를 보존한다.

### 2026-09-08 같은 작업 완료 및 남은 선택 사항

- 위 진행 기록 이후 복사본 compressed pose 검증, 실제 8개 작업본 적용/저장, fresh-process 재검증을 모두 완료했다. Saved/ImportReports/Khazan_SkeletonRecovery_apply_20260908.json 및 Khazan_SkeletonRecovery_FreshAudit_20260908.json은 passed다. 최종 commandlet 로그는 Khazan_SkeletonRecovery_FreshAudit_Final_20260908.log이고 exit code 0/오류 0이다.
- 원본 시퀀스 8개의 트랙은 모두 226개다. 기존 root 키 전체와 marker/길이/설정을 보존했고 대상 외 Content 파일 61개의 hash가 같다. 실제 작업본에 복구를 다시 적용할 필요가 없다.
- 애니메이션 트랙 손상에 대한 남은 필수 복구는 없다. 선택 사항은 Sprint Stop의 직전 4.75초 길이 복원 여부다. 답변이 오면 Docs/Animation/SKELETON_RECOVERY_2026-09-08.md를 읽고 해당 한 클립의 현재 길이/dirty 상태를 먼저 확인한 뒤 새 백업을 만든다. 이전 문서의 114프레임 구간은 24 fps에서 4.75초/115 sample keys다. 새 사용자 편집을 확인 없이 덮어쓰지 않는다.
- Root 최상위로의 후속 계층 변환은 별도 복사본을 사용한다. 현재 공유 Skeleton에서 최상위 C_P_Kazan(scale 100)을 다시 삭제하지 않는다. 변환 범위와 검증 기준은 위 전용 문서에 기록했다.

## 2026-09-08 DAS loop Control Rig 끝 프레임 편집 복원 진행

- 사용자 보완: DAS_Khazan_Walk_Loop/Run_Loop/Sprint_Loop은 Control Rig에서 첫 프레임을 마지막 프레임에 복사해 Bake한 작업본이다. 앞선 본 트랙 복구는 정상 원본의 포즈를 채운 결과여서 이 사용자 끝 프레임 편집을 재현하지 못했다.
- 현재 적용: 첫 포즈를 Walk 33번, Run/Sprint 119번 마지막 sample에 복사한 결과를 실제 세 시퀀스에 적용/저장했다. 첫 프레임부터 끝 직전까지의 RAW 포즈 보존과 RAW/COMPRESSED 처음·끝 일치 검사를 통과했다. 길이/프레임 수, 모든 Sync Marker 30개와 설정을 보존했다.
- 백업: Saved/ArtBackups/DAS_LoopClosure_20260908_134814. 변경 전 실제 loop 3개와 기존 Driving Level Sequence 3개를 복사하고 SHA-256을 검증했다. loop_pose_before.json에는 세 시퀀스의 모든 본/프레임 및 설정을 저장했다.
- 마지막 검증: Saved/ImportReports/Khazan_DAS_LoopClosure_apply_20260908.json은 passed다. 스크립트는 Scripts/Animation/restore_das_loop_end_pose.py이며 verify가 기본이다. 외부 Control Rig 시퀀스의 작업 이력을 복원한 것이 아니라 사용자가 설명한 Bake 결과를 AnimSequence에 재적용했다.
- 남은 작업/정확한 재개: 별도 UnrealEditor-Cmd의 -run=pythonscript -script=Scripts/Animation/restore_das_loop_end_pose.py로 저장본 재검증. 실행 중 Editor의 MCP 포트 충돌을 피하려면 -ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False를 해당 프로세스에만 전달한다. apply 재실행은 하지 않는다. 최종 결과를 Animation/Art 문서에 추가한다.
- 기존 Khazan_SkeletonRecovery_FreshAudit_20260908.json은 끝 프레임 편집 이전의 원본 포즈 복구 이력이다. 현행 세 loop의 마지막 프레임은 의도적으로 원본과 다르며, 이전 source-equality 검사를 현재 끝 프레임의 정답으로 사용하지 않는다.

### 2026-09-08 loop 끝 프레임 복원 최종 완료

- 위 진행 기록 이후 fresh-process 저장본 검증 3/3을 완료했다. Khazan_DAS_LoopClosure_verify_20260908.json은 passed/commandlet=true이며 RAW/COMPRESSED endpoint error가 세 시퀀스 모두 [0,0,0]이다. 마지막 직전까지 포즈 보존, marker/길이/설정 보존, 다른 Content 66개 SHA-256 보존도 통과했다.
- 최종 로그 Khazan_DAS_LoopClosure_FreshAudit_20260908.log는 exit 0/오류 0이다. 현재 사용자 요청인 세 loop 첫/끝 포즈 복구의 남은 필수 작업은 없다.
- 재검증은 Scripts/Animation/restore_das_loop_end_pose.py의 기본 verify 모드로 한다. 이후 사용자가 추가 편집하면 baseline과 달라질 수 있으므로 차이를 곧바로 손상으로 단정하지 않는다. apply를 다시 실행하거나 이전 skeleton 복구 스크립트로 끝 프레임을 원본 포즈로 되돌리지 않는다.
- 상세 결과와 이전 복구의 한계 보완은 Docs/Animation/SKELETON_RECOVERY_2026-09-08.md 및 ANIMATION_LOCOMOTION.md에 날짜별로 추가했다.

## 2026-09-08 HeinMach 인간형 Enemy 추출·조립 시작

- 요청: DAS 튜토리얼과 초반 HeinMach 인간형 적의 외형 조합, 장비, 머티리얼, 텍스처, 원작 메타데이터 추출 및 Enemy 전용 폴더 임포트. 게임 로직/C++ 변경 작업이 아니다.
- 확인: `HeinMach_Spawn_Main01.json`의 tutorial actor 1066 `SA_EmpireSword_Early3_Item`, 1055 `SA_Empire_SwordShield_2`. 전체 spawn handler 47개를 `Saved/Extracted/HeinMachEnemies/SourceSpawnActors.json`에 저장했다. 도끼 여부는 장비 참조를 추가 확인해야 한다.
- 원본: FModel 기존 AppSettings의 설치 게임/Pak 및 기존 키를 사용한다. 키는 출력/기록하지 않는다. CUE4Parse 1.2.2.202609 기반 표적 도구 `Scripts/Enemies/EnemyExtractor`를 준비했다. .NET 10은 `C:/Users/user/.dotnet/dotnet.exe`를 사용한다.
- 보호: `Saved/Extracted/HeinMachEnemies/ProtectedBaseline.json`에 시작 시 기존 변경 파일과 두 완성 환경 맵의 SHA-256을 보존했다. 기존 Art 문서는 하단 추가만 허용한다.
- 현재 UE Editor 미실행/미연결. 임포트는 UE 5.8 commandlet으로 진행할 수 있다. Python은 `C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe`를 사용한다.
- 재개: InitialMetadataRequests.json의 8개 package부터 metadata를 추출하고 CB/SpawnInfo/외형 데이터 참조를 따라간다. TargetedPackageIndex가 생성되면 재사용하며 전 게임 재추출하지 않는다. 이후 Enemy 전용 신규 경로에 임포트→조립→별도 프로세스 재로드 감사→완료 문서 추가. 아직 UE 에셋 임포트는 미실행이다.

## 2026-09-08 HeinMach Enemy 전신 조합·재로드 완료, 그래픽 검증 진행

- 완료: 개별 source mesh 17, 전신 조합 mesh 44, BP 45, texture 149, source 대응 material 36 + 보조 1, idle 3개를 `/Game/_Art/Enemies/HeinMach`에 저장했다. `HeinMachEnemy_FreshAudit.json`이 passed이며 확인용 새 맵 저장까지 완료했다.
- 마지막 검증: idle 모든 프레임/bone의 RAW·COMPRESSED pose를 정규화된 원본 PSA와 대조했다. 본체 하나가 포즈를 재생하는 최종 조합 BP의 검/방패 socket과 spawn을 45/45 검사했다. 원본 파츠/geometry는 별도 보존한다.
- 해결한 원인: 추출 quaternion의 미세한 비정규화가 Sequencer Euler 변환에서 큰 골반 오차를 만들었고, 입력 정규화로 해결했다. 초기 파츠 BP의 template weak leader 참조는 actor instance로 자동 재연결되지 않아, source 파츠를 전신 mesh로 조합하고 완성 BP에 적용했다. 초기 prototype은 별도 프로세스에서 미참조 확인 후 정리했다.
- 현재 진행: 실제 D3D RHI의 `verify_enemy_render_assets.py`가 shader compile 후 저장 맵을 재로드하고, 미참조 import staging을 정리한다. 로그 `Saved/Logs/HeinMachEnemy_RenderAssetAudit.log`, 결과 `Saved/ImportReports/HeinMachEnemy_RenderAssetAudit.json`. 이 실행 중 다른 UE writer를 띄우지 않는다.
- 중단 시 정확한 재개: 위 RHI 프로세스/로그와 report의 최종 상태를 먼저 확인한다. 실패면 해당 material/참조만 수정하고 같은 RHI 감사만 재실행한다. 통과 후 bundle Python으로 `finalize_enemy_sources.py`를 실행하여 최종 source/derived archive와 보고서를 FModel 루트에 복사하고 hash 대조한다. 마지막 결과를 정본 하단에 추가한다.
- 남은 원작 재현 범위: custom BBQCartoon shader, AvatarColor/체형/얼굴 적용, UE MorphTarget·LOD 체인, cloth/physics 전체 복원. metadata/raw를 확보했지만 현재 원작 완전 재현으로 기록하지 않는다. 전투 AI 구현 결과도 아니다.
- 정정: 앞선 시작 기록의 `ProtectedBaseline.json` 설명과 달리 실제 baseline에 저장된 hash는 기존 HeinMach/StormPass 환경 맵 2개다. 두 맵의 현재 hash 일치는 `HeinMachEnemy_ProtectedMaps.json`으로 확인했다. 기존 변경 파일 전체 hash를 검증한 것으로 확대하지 않는다.
- 정본: `Docs/Art/HEINMACH_ENEMY_EXTRACTION_2026-09-08.md`.

### 2026-09-08 Enemy 그래픽 재로드 검증 완료

- 위 진행 이후 RHI 감사가 passed/exit 0으로 완료됐다. material 37개 compile, 저장 맵의 Blueprint 45개 재로드/소켓/idle 참조 확인, 미참조 staging Skeleton 12개 정리를 마쳤다. 실행 중인 Enemy UE writer는 종료됐다.
- `HeinMachEnemy_ProtectedMaps.json`의 기존 환경 맵 2/2 hash 일치도 통과했다. 문서 정본 하단의 최종 검증 절을 기준으로 한다.
- 후속 사용은 `/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue`에서 시작한다. 에셋을 다시 만들 필요는 없다. 최종 외부 archive 및 hash는 `HeinMachEnemy_SourceExtraction.json`으로 확인한다.
- 원작 완전 재현에 남은 shader/색상·체형/morph·LOD/cloth·physics와 전투 기능 범위는 위 기록대로 미완료다. 작업 중 시도했던 template leader BP나 초기 prototype 삭제 절차로 돌아가지 않는다.

## 2026-09-09 Enemy 병종·의상·장비·애니메이션 확장 시작

- 사용자 요청: 다른 인간형 병종 및 무기 추가, 얼굴은 3개로 제한하고 의상 중심의 조합, metadata와 같은 애니메이션 재생 속도로 임포트. 기존 40종 얼굴 전수 조합 방식은 이번 대표 목록의 기준으로 사용하지 않는다.
- 원본 확인: 보존된 HeinMach spawn 47개에는 Sword/SwordShield/Halberd 외에 `CB_EmpireBow_Early`, `CB_Empire_SwordHArmor_Early`, `CB_EmpireSword_Sick_F`가 있다. 6개 인간형 CB를 V2 metadata로 표적 추출했다. 다른 지역 인간형까지 추가할지는 사용자에게 선택 질문을 보냈으며, 우선 HeinMach 확장은 독립적으로 진행한다.
- 옷 유사성: 이전 tutorial recipe가 상의 2/하의 2개였고 얼굴 5개 조합 비중이 컸다. 기존 master는 AvatarColor preset 적용이 없는 표시용 그래프다. 원작 군복 공통 요소와 미복원 색상/신규 병종 누락을 구분해서 수정한다.
- 현재 Editor PID 11080, 기존 `L_HeinMach_EnemyCatalogue` 열림, dirty content/map 없음. 초기 단일 viewport 캡처 `Saved/Screenshots/WindowsEditor/RiderMCP/20260909-014822_viewport.png`를 확인했다. 별도 commandlet writer와 동시에 에셋을 저장하지 않는다.
- 백업: `Saved/ArtBackups/HeinMachEnemyExpansion_20260909/manifest.json`. 기존 Enemy 파일 669개를 복사/hash 대조했고, 대상 외 사용자 변경 파일 및 기존 환경 맵을 포함한 보호 파일 39개 hash를 남겼다.
- 도구/진행 자료: `Scripts/Enemies/discover_enemy_expansion.py`, `Saved/Extracted/HeinMachEnemiesV2/EditorBaseline.json`, `HumanCBRequests.json`, `HumanSourceInventory.json`. FModel 설정/기존 extractor를 재사용하며 키는 기록하지 않는다.
- 다음 절차: CB→실제 look recipe/장비/AP·AB 참조 확인 → 신규 source 의상·무기/애니메이션만 dependency 추출 → 얼굴 3개를 의상에 순환 배정하는 대표 목록 작성 → 메타데이터 기반 SequenceLength/NumFrames/RateScale 및 clip/montage 배율 구분 → 임포트/현재 catalogue 정리 → 저장/시각/시간축 재검증. 기존 Player/C++는 수정 대상이 아니다.


### 2026-09-09 V2 ?? ?? ? ?? ???? ?? ?? ??

- ?? ??? 2,141 packages, renderable exports 1,005 (708 sequence packages, 256 textures, 41 meshes). ??? ?? dangling SI ?? 1?? SourceClosure.missing? ??.
- ?? identity 001/002/003? ???? ?? ?? 16? ??: ?? 4, ??? 4, ?? 4, ???? 1, ??? 1, ?? ?? ??? 2. ?? ?? ??? ??? 001?003 ? ???? ??? 003.
- Saved/Extracted/HeinMachEnemiesV2/ImportManifest.json, CombinedMeshManifest.json. ?? ?? 14?. ?? 3??? pelvis/shoulder ?? source bind mismatch? ??? skin? ??? ??. ???? carrier cloth bind? ?? ??? ???? bind? ???? ??.
- 708 ?? sequence? NumFrames/SequenceLength? 30fps ??. AnimComposite? AnimPlayRate? DilationCurve.T_Original/T_Dilation?? ??. ??? ??? ?? bake ?? ???? prepare_enemy_animation_timing.py. ApplyDilationCurveType=None? ?? ??.
- live UE PID11080?? ? ???? ?? ? private memory 78,803,853,312 bytes, ??? commit ?? ? 657MB? ??. ?? ??? ?? ??/?? ?? 669? ?? ?? ???? ??? ?? ??? ?? PID11080 ??. ? texture ??? ????? Library report ???. ?? ??/??? ??? ???? ???? ???.
- ??: NullRHI commandlet?? import_enemy_expansion_library.py ??. ??? ?? ???. ????? source/baked? import ? ??/?? audit, ?? BP/catalogue ??, ?? GUI ??? ? ?? ??. ?? staging ?? ?? ??? ???? ???.


### 2026-09-09 V2 ?? ? ????? ?? ??

- NullRHI ?? ??: HeinMachEnemyV2_Library.json status passed. ? ??? 107?, ???? 69?, ??/??? ?? 36?, ?? ?? 14?.
- ?? ?? ??? 3?? ?? ? ?? 711?(?? 30fps), ?? ?? 722?? ??. 143? ??? DilationCurve? ?? ???? ?? ??? ???. 26? ???/VFX timeline, ?? ???? ???? ?? elite shield ?? timeline 1?, ?? ?? 0? ???? 1?? ?????? ??.
- ??/metadata/derived 9,219?? SHA256, cooked 2,144package, ? 1.785GB? Desktop/??/EnemyExtracts/HumanoidExpansion_20260909? ??. SourceArchive report passed.
- AnimationImportManifest.json 1,433??? 75?? ?? commandlet? ??/?? ? ? ??? ???RateScale???/??/??? ?? RAW/COMPRESSED pose? ??. 0?674 ??. 675 batch?? ??? rational frame rate? ?? ??? ?? ??: 30fps ?? ??? ? ??? ?? ? ??? ?? frame rate? ????? importer ??, ?? ?. saved existing version? ???.
- Scripts/Enemies/run_enemy_animation_batches.py? ?? ? ???? batch report? ??. ? ??? ??? ?? ? build_enemy_expansion_assemblies.py, audit_enemy_expansion_catalogue.py? ?? ????. BP ?? ?? ???.
- Preview catalogue ??/legacy ??, ?? RHI shader ??/???, ?? ?? ?? hash ? ?? ???? ?? ??. ??? ?? ???? Saved/Extracted/HeinMachEnemiesV2? Saved/ImportReports/EnemyAnimationBatches.


### 2026-09-09 V2 ?? ??????BP????? ??

- AnimationImportAudit passed: 1,433?(711 source, 722 playback), ?? duration ?? 4.123535148892188e-7?, pose max [0.0001068115cm, quaternion component 0.00070858, scale 1.3113e-6]. ? 75? commandlet? ??/?? ??? ?? exit ??.
- UE 5.8 factory? ?? ??? ?? target rate? ?? ?? ? ?? ????. initialize ? commandlet? AnimationSettings CDO? ?? source-derived rate? ?? ???? NEVER notify? ??/???? ??. Config hash ?? ??. ??? ?? ?? 39?? Saved/ArtBackups/.../FailedCompressionBatch? ??? ? ?????.
- BP 16? ? CatalogueAudit passed. ?? BP45/????44? Archive/FaceVariants_20260908? ??(redirector ??). LegacyAssetMoves.json? ?? ??.
- ?? ?? full package? BASE_Normal ? ?? ?? basename? ?? ?? audit?? ??. PNG hash/?? ??? ??? ?? ?? ???? ????, ?? texture? ?? ?? byte? ????. TextureIdentity report passed.
- ?? ??? ?? ?? Animation/Engineering ?? 6?? baseline ?? ?? ??? ?? ????. ????? ???? ???. Player/C++ ? ?? ?? ?? hash? ????.
- ??? ??: verify_enemy_expansion_render.py? AllowCommandletRendering/RenderOffscreen?? ?? ?. RenderAudit ?? ? ?? ???? ????? ?? ??, ?? ? ?? active viewport ??? ????? ??. Metadata/?? archive ?? manifest ? report ???, Art ?? ?? ??? ?? ?? ?? ??? ???.

### 2026-09-09 V2 최종 저장·검증·전달 완료

- 앞선 진행 섹션 일부의 한글이 인코딩 문제로 `?`로 남아 있다. 기존 기록은 보존하며 이 절과 `HEINMACH_ENEMY_EXPANSION_2026-09-09.md`의 최종 결과를 현재 상태로 사용한다.
- 대표 BP 16개, 원본 시퀀스 711개와 시간 보정 재생 시퀀스 722개의 저장을 완료했다. 실제 RHI에서 머티리얼 69개/텍스처 256개/조립 BP 16개 검증 통과. 명명된 Rotator 축으로 최종 BP 회전 오류를 수정했고, 라이브 화면에서 수직 자세와 장비를 확인했다.
- `HeinMachEnemyV2_FinalAudit.json`, `AnimationImportAudit`, `RenderAudit`, `OrientationAudit`, `PreservationAudit`가 passed다. 애니메이션 길이 최대 오차 4.123535148892188e-7초. 첫/중간/마지막 모든 bone의 RAW/COMPRESSED pose를 검사했으며 전 프레임 원작 화면/전투 PIE 검증은 아니다.
- 기존 Enemy 669개 백업 hash 일치, 기존 579개 무변경, 89개 Archive 이동 및 이전 카탈로그 맵 갱신. 이전 경로 redirector는 디스크에 없으므로 `LegacyAssetMoves.json`으로 과거 경로를 변환한다. 이동된 89개 자산을 현재 에디터에서 로드했다.
- 보호 파일 33개와 Config 4개는 시작 hash와 같고, 외부에서 바뀐 Animation/Engineering 문서 6개는 되돌리지 않았다. Player C++/ABP/DAS/환경 맵은 이 Art 작업에서 바꾸지 않았다.
- 최종 CSV/manifest/report와 파이프라인 스크립트를 프로젝트 Metadata/Expansion_20260909 및 `Desktop/카잔/EnemyExtracts/HumanoidExpansion_20260909`에 동기화했다. `SHA256.json` 및 `DeliverySHA256.json`을 보존한다.
- 현재 GUI Editor PID 2620이 `L_HeinMach_EnemyCatalogue`를 열고 있으며 마지막 확인은 dirty content/map 0개다. 실행 중인 임포트 배치는 없다. 최종 유효 화면은 `Saved/Screenshots/WindowsEditor/RiderMCP/20260909-023700_viewport.png`; 근접 추가 캡처는 Slate 실패로 중단하고 게임 뷰 임시 설정을 복원했다.
- 후속 사용: 카탈로그에서 BP를 선택하고 `AnimationIndex.csv`로 원본 동작과 `A_EN_PLAY_*`를 찾는다. 재생용 클립은 1배로 사용한다. 중갑 파츠들은 같은 클립·위상으로 갱신한다. 생성 완료 자산을 일괄 재임포트할 필요는 없다.
- 남은 원작 재현 경계: cooked cartoon shader topology와 색상/체형 RNG, UE morph/LOD/cloth/physics 전체 복원, 전투 Notify/AI/Actor time dilation. 원본은 보존했지만 실행을 완전히 복원했다고 기록하지 않는다. 후속 요청 시 정본→해당 source JSON/asset→대상 보고서 순으로 필요한 범위만 확인한다.

### 2026-09-09 실사용 Enemy 정리 완료, main 커밋·푸시 진행

- 사용자 요청: 16개 실사용 외형 밖의 원본/과거 조합 정리, BP 설명, 원본 30 fps와 재생용 복사본 차이 설명, main 커밋·push. 애니메이션은 검증 후 선택할 예정이므로 그대로 둔다.
- 완료: 참조 closure 밖 195개(BP45/mesh67/material41/texture42), 343,444,687 bytes 삭제. 195개 UE 파일을 `Desktop/카잔/EnemyExtracts/ProjectCleanup_20260909`에 복사/hash 확인했다. 기존 Saved/raw 외부 source archive는 유지한다.
- 남은 UE 자산 1,771개 전체 hash 동일, 애니메이션 1,436개 무변경, Blueprint 16개 재로드와 socket/material/Idle 검증 passed, 누락 Enemy 참조 0. 최종 `EnemyCleanupFinalAudit_20260909.log`는 정상 종료/오류 0이다.
- API 성공 후 남은 texture `T_EN_T_EV_BlankWhite_01.uasset` 1개는 재실행에서도 남았다. 미참조·프로세스 종료·경로 및 백업 hash를 확인한 뒤 그 단일 파일만 정리했고 최종 fresh audit를 통과했다.
- 비교: 722개 중 271개는 Composite 구간/배속/반복/연결/시간 보정이 필요하고 451개는 원본과 같은 시간축이다. 같은 시간축 440개는 모든 sample/bone도 저장 정밀도 안에서 같고, 11개는 표본 수가 다르다. 정본 `ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md`와 비교 CSV/JSON에 기록했다.
- Git: 현재 main이며 fetch 직후 origin/main과 동일했다. Enemy 폴더/스크립트/관련 문서만 커밋한다. 다른 코드·Player 자산·설정 변경 및 기존 DAS 문서 변경은 작업 트리에서 보존한다. 보호한 44개 파일 hash는 모두 같다.
- 남은 절차: Cleanup metadata/외부 archive 동기화 → 대상 파일만 stage → staged 범위·diff·생성파일 제외 검토 → main commit → origin main push → remote commit hash 확인. 기존 애니메이션 임포트나 시각 폴리싱을 다시 수행할 필요는 없다.

### 2026-09-09 Enemy 정리 main 전달 확인

- 에셋·스크립트·Enemy 문서 변경을 `65119aa65dcf6f7d20b756715695111b946f2ee9` (`art: add curated humanoid enemies and metadata-timed animations`)로 main에 커밋·push했다. Git LFS 39개/110 MB 업로드 완료이며 `git ls-remote origin refs/heads/main`이 해당 commit과 일치했다.
- staged 4,415개 파일은 Enemy Content 4,372개, 스크립트 36개, Art 문서 7개다. 캐시/빌드 산출물과 Player/C++/설정은 제외했다. 공용 Art 문서도 Enemy 섹션만 stage해 기존 DAS 문서 변경을 보존했다.
- 현재 요청의 외형 정리·설명·검증·주요 변경 전달은 완료다. 이 완료 기록은 후속 문서 커밋에 포함한다. 애니메이션 실사용 목록 선정과 삭제는 사용자가 검증 후 요청하는 후속 범위로 남긴다.

### 2026-09-09 원본 애니메이션 조건부 삭제 착수

- 사용자 요청은 인게임에서 필요 없는 것이 확실한 원본만 삭제하고 Git push하는 것이다. 새로 확인한 현재 BP는 원본 5개를 참조하며 원작 AP/BlendSpace/WeaponSlot/Weapon Notify에도 직접 원본 참조가 있다. 따라서 재생용 722개만 남기는 전면 삭제 조건은 충족하지 않는다.
- `HeinMachEnemy_AnimationPruning_Metadata_20260909.json`: 기존 저장 metadata를 분석해 Source 711개 중 현재 참조 없음 + 알려진 원작 소비가 이미 bake된 Composite segment뿐인 549개를 삭제 대상으로 정했다. 원작 직접 참조 또는 재생용 대응이 없는 162개와 기존 Idle 3개는 보존한다. Composite 안의 Weapon Notify 참조는 body bake로 대체되지 않으므로 직접 소비로 분류한다.
- 삭제 전 백업 완료: `C:/Users/user/Desktop/카잔/EnemyExtracts/AnimationPruning_20260909/BackupManifest.json`. 549개 원본 복사와 SHA-256 확인, 남길 1,222개 hash 및 기존 사용자 작업/Config/환경 50개 hash를 기록했다. 현재 변경 대상 Enemy의 unsaved edit는 없다.
- 재개: `Scripts/Enemies/prune_enemy_source_animations.py`의 `delete_sources()`를 UE Python에서 실행 → 별도 commandlet에서 `verify_saved_assets()` → 새 AnimationPruning metadata/Art 문서 발행 → Enemy 변경만 main commit/push. `backup()`은 기존 기준을 덮어쓰지 않으며 반복 실행하지 않는다. 삭제는 plan hash 및 개별 백업/현재 파일 hash/최신 미참조 검증 이후에만 진행한다.
- 현재 단계는 삭제 직전이며, Blueprint/재생용/플레이어/게임 코드 변경은 없다. 기존 metadata와 전체 import builder는 역사 자료로 보존하고 삭제 파일을 재생성하지 않는다.

### 2026-09-09 원본 애니메이션 정리·검증 완료

- 549개 원본 삭제 완료, 290,576,489 bytes 감소. 현재 Source 162 + 기존 Idle 3 + Playback 722 = AnimSequence 887개, Enemy 전체 UE 자산 1,222개다. 남은 에셋 전체 hash가 같고 BP/재생 속도/키를 수정하지 않았다.
- GUI 삭제 중 `FAppTime` handled ensure와 legacy 참조 수집 fallback 경고가 있었으나 API 성공·실제 파일 삭제·보존 hash를 확인했다. GUI에 unsaved Enemy package는 없다.
- 첫 독립 감사는 에셋 검사 passed 후 MCP HTTP 포트 충돌로 process error가 남았다. 프로젝트 설정을 바꾸지 않고 최종 감사 프로세스에만 `-DisablePlugins=ModelContextProtocol`을 적용해 재검사했다. 최종 로그 `EnemyAnimationPruningFinalAudit_20260909.log`: Success, 0 errors, 1 기존 scalability warning, exit 0.
- 현재 rate/sample/길이/RateScale 검사, Playback compressed pose 2,166개, 카탈로그 BP 16개 참조 검증 passed. missing Enemy dependency 0. 기존 Router/Animation/Engineering 문서 8개는 외부 작업 변경으로 관측했으며 되돌리지 않았다.
- 정본 `ENEMY_SOURCE_ANIMATION_PRUNING_2026-09-09.md`; 남은 전달 절차는 새 metadata 발행 → 해당 Enemy/Art 변경만 stage → main commit/push → 원격 hash 확인이다. 현재 애니메이션을 추가로 편집하거나 검증을 처음부터 반복할 필요는 없다.

### 2026-09-09 조건부 원본 삭제 main 전달 완료

- 에셋 삭제·판단 metadata·스크립트·Art 문서를 `ec802c8f37cb45ecdab3ee9460495f7f65595ade` (`art: prune verified unused enemy source animations`)로 main에 커밋하고 origin에 push했다. `git ls-remote origin refs/heads/main`의 동일 hash를 확인했다.
- 커밋은 검증된 원본 삭제 549개와 새 metadata 9개·스크립트 3개·Art 문서 6개의 567개 파일이다. 공용 Art 문서는 Enemy 추가 기록만 stage했으며 기존 사용자 Player/C++/설정/다른 문서 변경은 포함하지 않았다.
- 현재 요청의 안전한 삭제·검증·Git 전달은 완료다. 원본 전체 미사용 조건은 성립하지 않으므로 Source 162개와 기존 Idle 3개는 보존한 상태가 최종 결과다. 이 확인 기록은 후속 문서 커밋으로 전달한다.

### 2026-09-09 Enemy 애니메이션 구조 통합 완료

- 사용자 후속 요청으로 남은 재생 자산의 네이밍/구조를 통일했다. 884개를 `A_EN_PLAY_*` 및 8개 병종별 `Animations/Playback` 폴더로 이동하고, 같은 원본의 초기 Idle 3개는 전 프레임 비교 후 제거했다. 현재 Enemy UE 자산 1,219개, AnimSequence 884개다.
- `CompositeBake` 722개와 `DirectOriginalTimeline` 162개 모두 `EnemyArtRole=PlaybackSequence`다. 유래와 원작 package는 metadata에 보존했고 FPS/길이/sample/RateScale/root 설정은 이동 전 계약과 같다.
- UE AssetTools가 BP 16개 참조를 갱신해 저장했다. old package/redirector/missing dependency 0. 별도 commandlet에서 884개 처음/중간/마지막 RAW+COMPRESSED pose 총 5,298회와 BP/카탈로그를 검사했다. 최종 로그 `EnemyAnimationStructureAudit_20260909.log`는 Success/오류 0/exit 0이다.
- 변경 전 애니메이션 887개와 BP 16개는 `Desktop/카잔/EnemyExtracts/AnimationStructure_20260909`에 hash 백업했다. 보호한 외부 작업의 검사 시점 변경은 0개이며 `KhazanAnimInstance.cpp`/Player/Config를 수정하지 않았다.
- 최신 정본 `ENEMY_ANIMATION_LIBRARY_STRUCTURE_2026-09-09.md`, metadata `AnimationStructure_20260909`. 남은 절차는 Enemy/관련 Art 파일만 stage 검토 → main commit/push → 원격 hash 확인이다.

### 2026-09-09 Enemy 재생 라이브러리 main 전달 완료

- 통합 변경을 `6fd77bcc281e549f82bdb4204593b181faa02d83` (`art: unify enemy playback animation library`)로 main에 커밋하고 origin에 push했다. `git ls-remote origin refs/heads/main` 일치까지 확인했다.
- stage 전 정확한 범위 1,808개 경로를 검사했다: old animation 삭제 887, 새 animation 추가 884, BP 수정 16, metadata/스크립트/문서만 포함했다. 최대 신규 파일은 약 2.86 MiB이며 build/cache 파일은 없다.
- 사용자 Player/DAS/C++/Config/다른 문서 변경은 작업 트리에 그대로 보존했다. 현재 요청의 네이밍·폴더 통합, 중복 Idle 정리, 검증 및 Git 전달은 완료다. 이 전달 확인은 후속 문서 커밋으로 반영한다.
