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

## 2026-09-08 Stop Root 움직임을 C_P_Kazan으로 전달한 _New 생성 진행

- 사용자 범위: Run_Stop_LF/Run_Stop_RF/Sprint_Stop 세 원본에서 같은 위치의 이름_New 시퀀스를 생성한다. Root와 C_P_Kazan 애니메이션 키 외 Sync Marker/길이/옵션/나머지 본/원본은 수정하지 않는다.
- 현재 적용: DAS_Khazan_Run_Stop_LF_New, DAS_Khazan_Run_Stop_RF_New, DAS_Khazan_Sprint_Stop_New를 원본 복사로 생성하고 저장했다. 원본의 현재 길이는 95/91/114프레임 구간(3.958333/3.791667/4.75초)이다.
- 방법: AnimationSequencerDataModel의 FK Control Rig 트랙에서 C_P_Kazan의 scale 100을 반영해 Parent_new(t)=Root_ref^-1*Root_old(t)*Parent_old(t)를 Bake하고, Root의 애니메이션 트랙만 제거했다. 실제 스켈레톤의 본/계층은 변경하지 않았다. C_P_Kazan 아래에 Root 외의 sibling이 없음을 확인했다.
- 마지막 검증: Saved/ImportReports/Khazan_DAS_StopRootTransfer_build_20260908.json은 passed, 3개 저장 완료다. 원본과 복사본의 기타 설정 35개 및 Notify/Marker/길이 정보가 같고, 나머지 225개 본의 Control Rig 채널 2,025개는 키 시간/값/tangent/default까지 정확히 같다. 매 프레임 RAW/압축 컴포넌트 포즈와 Root 고정 상태도 검사했다.
- 백업: Saved/ArtBackups/DAS_StopRootTransfer_20260908_141845. 원본 3개 6,077,827 bytes를 복사해 SHA-256 확인했고 baseline.json/manifest.json에 설정, 기타 채널 해시와 보호 파일 71개의 해시를 저장했다. 원본/다른 InGame/스켈레톤/메시/ABP/AnimInstance 파일은 변경하지 않았다.
- 남은 작업/재개: 별도 UnrealEditor-Cmd -run=pythonscript -script=Scripts/Animation/bake_das_stop_root_to_dummy.py의 기본 verify 모드로 저장본 검증 후 문서에 최종 결과를 추가한다. 실행 중 Editor와 MCP 포트가 충돌하지 않도록 -ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False를 commandlet 프로세스에만 전달한다. build 재실행은 하지 않는다.
- 보존한 옵션: Enable Root Motion=false, Force Root Lock=false, Use Normalized Root Motion Scale=true. 사용자 요청에 따라 본 키 이외의 설정을 변경하지 않았다. 이 기록은 게임 내 Root Motion 활성화나 CharacterMovement 이동 거리 검증을 뜻하지 않는다.

### 2026-09-08 Stop _New Root 이관 최종 완료

- 위 진행 기록 이후 fresh-process 저장본 검증 3/3을 완료했다. Khazan_DAS_StopRootTransfer_verify_20260908.json은 passed/commandlet=true다. 최종 로그 Khazan_DAS_StopRootTransfer_FreshAudit_20260908.log는 exit 0/오류 0.
- Root/C_P_Kazan 외 채널 2,025개와 일반 속성/시퀀스 정보 35개 항목 보존, RAW/압축 전신 컴포넌트 포즈, Root reference pose 고정 및 보호 파일 71개 해시 일치가 통과했다. 사용자 요청인 세 _New 생성의 남은 필수 작업은 없다.
- 현재 결과의 정본은 Docs/Animation/STOP_ROOT_TRANSFER_2026-09-08.md다. 기본 verify 모드로 재검증하고 build를 다시 실행하지 않는다. 후속 사용자 수정으로 baseline이 달라지면 차이를 먼저 확인한다.
- Enable Root Motion=false 등 기존 옵션은 사용자 요청대로 유지했다. Root Motion 활성화나 정규화 scale 정책 변경은 이 작업에 포함하지 않았다. 본 키 이외의 설정을 자동으로 변경하지 않는다.

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

## 2026-09-10 HeinMach·StormPass BigBear 추출·검증 완료

- 두 레벨의 실제 spawn metadata가 공통 `CB_BigBear_E`를 가리키는 것을 확인하고 `/Game/_Art/Enemies/Shared/Beasts/BigBear`에 원작 material variation BP 3개와 애니메이션 102개를 포함한 공용 에셋 145개를 저장했다.
- source closure 309 package, metadata failure 0, raw cooked package 309개를 외부 archive에 보존했다. 원본 PSK의 71개 bone에 PSA 공통 helper 8개를 추가한 79-bone skeleton을 사용하며 76개 PSA 레이아웃과 reference prefix를 검증했다.
- direct source timeline 12개와 Composite bake 90개 모두 `A_EN_PLAY_*`다. source segment/play rate/repeat/DilationCurve, root motion 95, force root lock 3, additive 1을 asset별로 반영했다. Notify/event 1,164행은 metadata이며 실행 코드는 범위 밖이다.
- `ValidationSummary.json`과 `RenderValidationSummary.json` passed. 애니메이션 102개 첫/중간/마지막의 모든 bone을 RAW/COMPRESSED로 평가했고 최대 길이 오차는 약 `1.1981e-7`초다. D3D12/SM6에서 material 12개와 BP 3개의 mesh/material/animation 재로드도 통과했다.
- 기존 사용자 변경 6개 파일과 Player/Locomotion C++는 수정하지 않았다. README와 외부 archive 1,226개 파일의 hash 동기화, 보호 파일 hash 재확인, BigBear/Art 190개 경로의 선택 stage까지 완료했다. 정본은 `BIG_BEAR_EXTRACTION_2026-09-10.md`; 남은 절차는 main commit·push와 원격 hash 확인이다.

### 2026-09-10 BigBear main 전달 완료

- BigBear 에셋·metadata·재현 스크립트·Art 문서 190개 경로를 `e4878e2eb6a4ded141ef7600765d95fb0f2575d8` (`art: add HeinMach and StormPass BigBear enemy`)로 main에 커밋하고 origin에 push했다. Git LFS 2개/6.8 MB 업로드를 완료했고 원격 main hash가 일치했다.
- 커밋 범위는 BigBear Content 173개, 스크립트 12개, Art 문서 5개다. 기존 사용자 변경 6개 파일은 stage/commit에서 제외했으며 최종 보호 hash mismatch는 0개다.
- 추출·임포트·애니메이션 시간축 복원·에셋/렌더 검증·원본 archive·첫 Git 전달은 완료됐다. 이 전달 확인 절은 후속 문서 전용 커밋으로 반영한다.

## 2026-09-11 HeinMach Yetuga 보스 추출 진행

- 요청: Yetuga 본체·재질·텍스처·애니메이션을 원작 JSON 기준으로 추출/복원하여 Unreal에 임포트한 뒤 main commit/push까지 완료한다.
- HeinMach_Spawn_Main01의 SA_Yetuga → Boss/01_Yetuga/Base_Setting/CB_Yetuga → C_M_Yetuga를 확인했다. 본체 PSA 453 bone과 PSKX 198 bone의 공통 reference pose/parent를 대조했고, 누락된 비가중 뼈를 추가하는 파생 PSKX를 생성했다. 얼음 투척물은 별도 20-bone skeleton이다.
- 작업 루트 `Saved/Extracted/Yetuga_20260911`, 목적지 `/Game/_Art/Enemies/HeinMach/Bosses/Yetuga`, 외부 원본 archive `C:/Users/user/Desktop/카잔/EnemyExtracts/Yetuga_20260911`. 재현 스크립트는 `Scripts/Enemies/*yetuga*.py`다.
- 원작 재질의 부모와 cooked master 기본값까지 확인했다. 초기 텍스처 56개 임포트 후 UE 5.8 sampler enum 이름 차이로 master 생성이 중단됐다. 아직 최종 검증/완료가 아니며 해당 API 수정 후 재개한다.
- 다른 몬스터 이름의 폴더에 있는 Grapple_B 두 시퀀스도 실제 Skeleton 필드가 C_M_Yetuga_Skeleton이므로 추가 추출한다. 경로명만으로 배제하지 않는다. 공통 Missile_Skeleton의 투명 gameplay carrier Composite 6개는 캐릭터 시퀀스와 구분해 원본 metadata를 보존한다.
- 정확한 재개: prepare_yetuga_sources.py export → build_yetuga_import_manifest.py → prepare_yetuga_animation_timing.py → Unreal Python commandlet import_yetuga_library.py → run_yetuga_animation_batches.py → assembly/fresh process/실제 RHI 검증 → archive/Art 문서 → Yetuga 경로만 main commit/push 및 원격 hash 확인.
- 작업 전 사용자 변경과 stage 상태는 `WorkspaceBaseline.json`, C++/Config는 `Saved/ImportReports/Yetuga_ProtectedBaseline_20260911.json`에 보존했다. 기존 사용자 C++/Engineering 문서 및 staged rename을 이 Art 작업에서 변경하거나 함께 커밋하지 않는다.

### 2026-09-11 Yetuga 저장 검증과 렌더 검사 진행

- 본체/얼음 mesh·skeleton, 56 texture, MI 14개/master 3개, BP 1개/map 1개와 animation 120개를 저장했다. 전체 199개 에셋의 fresh-process 검사, 원작 소켓 7개, 모든 animation RAW/COMPRESSED 포즈/시간축 검사를 통과했다. 최종 master 버전과 추가 base-property 감사의 재검증은 아직 진행 중이다.
- 실제 D3D12/SM6에서 17 material의 shader instruction 존재를 확인했다. TC_Grayscale의 Linear Grayscale sampler를 수정했다. 원본 VisibleCylinderPos=-999999 sentinel 같은 보존 값의 합산은 bounded graph로 변경했으나 이를 렌더 문제의 확정 원인으로 기록하지 않는다.
- commandlet SceneCapture에서는 본체가 표시되지 않고 눈/얼음만 보이는 문제가 남아 있다. 임시 opaque/unlit diagnostic material에서는 본체 실루엣이 올바르게 표시되어 mesh geometry가 없는 문제는 배제했다. 원본 PNG diffuse alpha는 본체/얼굴/털 모두 거의 255로 확인했다. NoTextureStreaming만으로는 개선되지 않았다.
- 마지막 절차는 숨김/offscreen 일반 UnrealEditor에서 실제 frame을 진행한 뒤 캡처하는 `capture_yetuga_editor_preview.py`다. 현재 실행 PID는 실행 로그에서 확인하며 `Saved/Logs/YetugaEditorPreview_20260911.log`와 `Yetuga_RenderAudit_20260911.json`, preview PNG를 확인한다. 아직 화면 검증 및 원본 archive 최종화/commit/push를 완료로 기록하지 않는다.
- 진행 중 외부 작업이 기존 사용자 변경과 당시 Yetuga 중간 파일을 `d5cfbc77` (`0911`)으로 main에 commit/push했다. 이 작업에서 reset/amend하지 않는다. 처음 22개 사용자 변경과 Source/Config hash는 이후 대조에서도 모두 동일했다. 후속 Yetuga 수정/추가를 새 main commit으로 전달해야 한다.

### 2026-09-11 Yetuga 에셋·최종 검증 완료

- 원본 581 package, 본체/얼음 mesh와 453/20-bone skeleton, texture 56개, MI 14개/master 3개, BP/map 각 1개, 재생용 animation 120개의 복원·임포트를 완료했다. 전체 199개 에셋이며 staging/임시 package 0개다.
- V4 master의 sampler/보존 graph와 source base-property를 포함한 최종 fresh audit가 exit 0/pass다. scalar 2,381/vector 482/texture binding 329, source socket 7개, 전 시퀀스 RAW/COMPRESSED pose/시간축을 대조했다. source skeleton별 PSA reference record hash도 모두 동일하다.
- 일반 UnrealEditor에서 `-ExecCmds="py .../capture_yetuga_editor_preview.py"`로 실제 frame/resource warmup 후 캡처해 본체/털/얼굴/눈/돌기/얼음 투척물의 표시를 확인했다. shader 17개 D3D12/SM6 compile/reload 검증도 pass다. frame 0 commandlet 즉시 capture의 미표시와 실제 저장 에셋 표시를 구분한다.
- 정본은 `YETUGA_EXTRACTION_2026-09-11.md`, 최신 artifact는 `Metadata/Extraction_20260911/ValidationSummary.json`, `RenderValidationSummary.json`, `Preview/*.png`다. 원본 JSON 전체는 SourceMetadata.zip/Index로 Git에 포함하고 원본 cooked/변환 파일은 외부 archive에 보존한다. proprietary shader/gameplay/physics/cloth/notify 및 LOD chain의 구현 제한은 정본을 따른다.

### 2026-09-11 Yetuga main 전달 완료

- 최종 Yetuga 에셋·metadata·재현 스크립트·Art 문서 197개 경로를 `4dfc08a32d6ed30670f3bd098153a6a04b4d3921` (`art: restore HeinMach Yetuga boss and playback animations`)로 main에 커밋하고 origin에 push했다. Git LFS 4개/47 MB 업로드가 완료됐으며 `git ls-remote origin refs/heads/main`과 로컬 HEAD의 동일 hash를 확인했다. 확인 시 작업 트리는 깨끗했다.
- stage 범위는 Yetuga Content, Yetuga 전용 Python 스크립트와 Art 문서 5개로 검사했다. 외부 작업의 `d5cfbc77` 커밋을 보존했으며 작업 시작 시 사용자 변경 22개와 Source/Config의 보호 hash는 최종 검사에서도 동일했다.
- 외부 archive는 `C:/Users/user/Desktop/카잔/EnemyExtracts/Yetuga_20260911`의 2,159개 파일을 SHA-256으로 검증했다. 원본 cooked package 581개와 JSON 581개의 보관을 확인했으며, JSON 전체·검증 보고서·최종 렌더 이미지는 프로젝트 metadata와 Git에도 포함했다.
- 현재 요청의 추출·임포트·시간축 복원·에셋/화면 검증·원본 보관·main 전달을 완료했다. 원작 전용 셰이더와 gameplay/physics/cloth 등의 구현 제한은 정본에 명시한 그대로이며 완전한 원작 실행 로직 복원으로 확대하지 않는다. 이 전달 확인은 후속 문서 전용 커밋으로 반영한다.

## 2026-09-15 ApesStoneHandElite 실사용 버전 추출 진행

- 요청은 버전별 사용 용도 확인 후 실사용 모델·재질·텍스처·애니메이션의 복원/UE 임포트다. Router → Art pipeline/state/knowledge → Yetuga 정본을 읽었다. 기존 사용자 Source/Engineering/Animation 변경 9개와 Source/Config hash는 `Saved/Extracted/ApesStoneHandElite_20260915/WorkspaceBaseline.json`으로 보호한다. task helper 자체의 최초 untracked 기록은 보호한 사용자 변경 수에 포함하지 않는다.
- CB의 SCS component template override까지 읽어 Early=기본 외형, Standard=V3로 확정했다. 레시피 CDO의 V2 및 Early 추가 재질은 실제 CB override에서 교체된다. HeinMach 스폰 3개와 StormPass 1개는 Early다. Ghost/Wraith는 선택한 live closure의 소비 근거가 없고 Dead_002/003은 정적 환경 시체다. 전역 미사용 판정과 혼동하지 않는다.
- 기본/V3 ActorX는 MATT0000 이외의 chunk가 동일해 메시 1개와 재질 BP 2개를 사용한다. 원본 mesh bone 97개가 PSA 453개의 prefix가 아니므로 이름/parent 기준으로 index를 재매핑하고 원래 mesh bind/skin weight 수치를 보존했다. 추가 helper 356개이며 weapon bind의 원본 reference 차이를 덮어쓰지 않았다.
- 선택 closure 387 package/metadata failure 0, PSA 입력 79개 → 직접 재생 10 + Composite bake 82 = 92개다. library script는 mesh/skeleton 1쌍, texture 31, MI 13/master 2개 저장을 완료했다. 최초 commandlet은 GameFeatures 기본 클래스가 로드되지 않아 시작 시 ensure/exit 1이 있었다. engine PluginManager의 command-line 옵션을 확인해 해당 임포트 프로세스에만 `-EnablePlugins=GameFeatures`를 추가했고 Config/uproject를 수정하지 않는다.
- 애니메이션 배치는 `run_apes_stone_hand_animation_batches.py`이며 checkpoint 재사용 조건에 실제 process exit 0을 추가했다. 재개 시 `Saved/ImportReports/ApesStoneHandEliteAnimationBatches/*.json`과 각 batch log를 확인한다. 이후 library 정상 exit 재확인 → assemblies → fresh audit → 일반 UnrealEditor warmup/render → archive → 최종 Art 문서/보호 hash 확인 순서다. 아직 화면 검증/최종 archive 완료로 기록하지 않는다.
- 새 정본 `APES_STONE_HAND_EXTRACTION_2026-09-15.md`; 도구 `Scripts/Enemies/*apes_stone_hand*.py`; 작업 루트 `Saved/Extracted/ApesStoneHandElite_20260915`; 목적지 `/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite`. 원작 BoneMod의 축/zero 의미 및 전용 shader 실행 코드는 미확인 범위로 분리했다.

### 2026-09-15 ApesStoneHandElite 임포트·최종 검증·원본 보관 완료

- library/assemblies/fresh audit/render 및 애니메이션 모든 batch가 process exit 0으로 끝났다. 최종 UE 자산 143개, BP 2종, 재생용 시퀀스 92개이며 material scalar 1,791/vector 504/texture binding 209개와 source socket 7개 검증을 통과했다. staging/임시 package는 0개다.
- 일반 에디터에서 프레임을 진행한 뒤 D3D12/SM6 shader 15개와 두 외형을 검증했다. 최종 PNG는 `RTF_RGBA8_SRGB` target을 사용하며 lit/base-color 이미지를 직접 열어 geometry·피부/털·바위·눈 및 색 차이를 확인했다. 원본 material/texture 수치를 밝게 수정하지 않았다. `ApesStoneHandElite_VisualReview_20260915.json`에 이미지 SHA-256과 검수 범위를 기록했다.
- 외부 archive는 `Desktop/카잔/EnemyExtracts/ApesStoneHandElite_20260915`다. 선택한 cooked package 387개, 선택/제외 분류의 원본 JSON 총 423개, PSK/PSA/PNG/파생 pose/재현 스크립트/보고서를 보관했다. 최종 1,526개 파일의 hash 검증을 통과했다. 원본 JSON 전체는 프로젝트 `SourceMetadata.zip`/Index로 함께 전달한다.
- 독립 source 감사에서 원래 bind 97개와 skin weight 45,190행의 vertex/수치/bone 이름 대응이 유지됐고, 사용자 초기 변경 9개 및 Source/Config 41개 hash가 같았다. 남은 절차는 이번 Apes Content/13개 전용 스크립트/Art 문서 5개의 선택 stage → main commit/push → 원격 hash 확인이다. 이미 통과한 임포트/애니메이션/렌더 검증을 다시 시작할 필요는 없다.

### 2026-09-15 ApesStoneHandElite main 전달 완료

- 이번 Apes Content·전용 스크립트·Art 문서 204개 경로를 `da37752472259d84cd20d49302c6e73fdd0f2ad3` (`art: restore source-selected ApesStoneHandElite variants and animations`)로 main에 커밋하고 origin에 push했다. Git LFS 2개/6.3 MB 업로드 완료 및 원격 main의 동일 hash를 확인했다.
- staged scope/whitespace 검사를 통과했으며 기존 사용자 변경 9개는 stage/commit에서 제외해 작업 트리에 그대로 보존했다. 최종 script EOF 정리 후 외부 archive를 다시 동기화해 최종 hash 검증 수는 1,527개다. 원본 JSON ZIP의 423개 entry도 각각 bytes/SHA-256을 대조했다.
- 요청한 사용처 분류·선별 추출·UE 임포트·에셋/시간축/화면 검증·원본 보관·Git 전달은 완료다. 정본에 명시한 전용 shader/BoneMod/AI 등의 구현 제한은 유지한다. 이 전달 확인은 별도 문서 커밋으로 반영한다.

## 2026-09-15 WildDog·WildBoar 선별 추출·검증·보관 완료

- HeinMach/StormPass spawn metadata를 확인해 WildDog는 StormPass `CB_WhiteDog` 17개, WildBoar는 StormPass `CB_WildBoar_New` 2개를 live 기준으로 선택했다. HeinMach에는 두 종 spawn이 없었다. 일반 PicaroonDog/Ghost와 표시용이 아닌 Boar helper는 UE 라이브러리에서 제외하고 JSON 분류 근거를 보존했다.
- 원작 RandomLook cache에 따라 두 종 모두 CoatV1~V3 세 외형을 구성했다. 각 V1/V2/V3 ActorX의 material chunk 외 payload가 같아 종별 공용 mesh 하나만 임포트했다. 최종 WildDog 125개, WildBoar 109개 UE 에셋이며 staging/임시 package는 0개다.
- 재생용 시퀀스는 WildDog 82개(direct 17/composite 65), WildBoar 74개(direct 11/composite 63)다. 직접 시간축은 모두 원본 30/1 FPS이며 source segment/repeat/play rate/dilation을 bake하고 저장 길이·전 bone RAW/COMPRESSED pose·root 설정을 검증했다.
- library/animation/assembly/fresh audit의 process exit 0과 실제 UnrealEditor warmup 후 D3D12/SM6 렌더를 확인했다. Dog material 12개/BP 3개와 Boar material 9개/BP 3개가 compile·reload됐고 최종 lit/base-color 이미지에서 각 coat 세 가지를 직접 확인했다.
- 외부 archive `Desktop/카잔/EnemyExtracts/WildDog_20260915` 1,244개 파일과 `WildBoar_20260915` 1,121개 파일을 SHA-256으로 검증했다. raw cooked package는 각각 311개/283개, metadata failure는 0이며 원본 JSON 전체를 프로젝트 `SourceMetadata.zip`/Index에도 포함했다.
- source 감사 시 작업 시작 후 사용자가 변경한 기존 문서 4개를 감지해 그대로 보존했다. 기존 14개 사용자 작업 파일을 stage하지 않으며 Source/Config 보호 파일 41개의 hash mismatch는 0개다. 남은 절차는 두 Content 루트, 전용 스크립트 26개와 Art 문서만 선택 stage해 main commit/push하고 원격 hash를 확인하는 것이다.

### 2026-09-15 WildDog·WildBoar main 전달 완료

- WildDog/WildBoar Content 314개 경로, 전용 스크립트 26개와 Art 문서 5개의 총 345개 경로를 `d791f0fc` (`art: restore live WildDog and WildBoar variants`)로 main에 커밋하고 origin에 push했다. Git LFS 객체 4개/6.5 MB 업로드를 완료했다.
- stage 범위 검사와 `git diff --cached --check`를 통과했다. 기존 사용자 변경 14개는 커밋에서 제외해 작업 트리에 유지했으며 Player/맵/C++/Engineering/Animation 파일을 이번 Art 커밋에 포함하지 않았다.
- 사용처 판정, 실사용 외형 선별, 모델·재질·텍스처·애니메이션 임포트, source/fresh/RHI 검증, 원본 archive와 첫 Git 전달은 완료됐다. 원격 main hash 최종 확인과 이 전달 기록 자체의 문서 커밋만 수행하면 된다.

## 2026-09-15 Enemy 에셋 구조 정리 완료

- 현재 Enemy 1,940개 중 살아 있는 package 21개를 공용/병종/변형 구조로 이동했다. 직접 참조가 갱신된 전체 영향 범위는 678개이며 이동 전 468,397,155바이트를 `Desktop/카잔/EnemyExtracts/EnemyAssetStructureCleanup_20260915`에 SHA-256 백업했다.
- UE 적용은 완료됐다. `HeinMach/Empire`, 옛 `HeinMach/HalberdElite`, `HeinMach/Humanoids/Shared`, `OtherRegions/Humanoids/MageHard`를 현재 폴더에 합쳤고, 최초 빈 leaf 및 연쇄 빈 상위 폴더 총 63개를 제거했다. 최종 empty/Legacy directory와 redirector는 0개다.
- fresh audit는 exit 0/pass다. 총 1,940개/class 수, 미영향 1,262개 SHA-256, 영향 678개 로드, AnimSequence 1,354·SkeletalMesh 35·Blueprint 28 계약, 누락 dependency 0, 카탈로그 6개 로드를 확인했다. 수치 계약 최대 오차는 0이다.
- 작업 중 사용자가 `Source/Khazan/Character/Component/KhazanLocomotionComponent.h`를 추가 수정한 사실을 hash로 감지했다. 해당 변경과 기존 Player/맵/C++/Engineering/Animation 작업은 건드리지 않았고 이 Art commit에서 제외한다.
- 정본 `ENEMY_ASSET_LIBRARY_STRUCTURE_2026-09-15.md`, 현재 metadata `Content/_Art/Enemies/Metadata/Structure_20260915`, 재현 도구 `Scripts/Enemies/*enemy_asset_structure*.py`. 남은 절차는 metadata 발행 → 범위 선택 stage → main commit/push → 원격 hash 확인이다.

### 2026-09-15 Enemy 에셋 구조 main 전달 완료

- Enemy Content·현재 구조 metadata·재현 스크립트·Art 문서의 719개 path를 `cc36d53152c167cead1056589be49a38598c1824` (`art: organize enemy asset library`)로 main에 커밋하고 origin에 push했다. Git LFS 객체 24개/100MB 업로드가 완료됐고 당시 원격 main hash와 일치했다.
- stage 전 A 37/M 661/D 21의 정확한 범위를 확인했으며 범위 밖 stage 0, 남은 Enemy/Art task 변경 0, `git diff --cached --check` 및 `git lfs fsck --pointers`를 통과했다.
- 기존 사용자 변경 15개는 작업 트리에 그대로 남겼다. 이 중 `KhazanLocomotionComponent.h`는 Enemy 정리 도중 추가 편집된 hash까지 보존했으며 Player/맵/C++/Engineering/Animation 변경을 Enemy 커밋에 포함하지 않았다.
- 구조 정리·백업·fresh Unreal 계약 감사·metadata 발행·첫 Git 전달은 완료됐다. 이 전달 확인 절만 후속 문서 커밋으로 main에 반영한다.
## 2026-09-16 DualAxeSword 원본 시간축 복원 — Editor 종료 대기

- 상세 정본: [DAS_ANIMATION_RESTORATION_2026-09-16.md](DAS_ANIMATION_RESTORATION_2026-09-16.md)
- 준비 완료: 원본 AnimSequence 457개, skill AnimComposite 397개 전수 비교. write manifest는 비로코모션 source 350개와 playback 360개, 합계 710개다. 보호 locomotion destination과 교집합은 0이다.
- 마지막 검증: UE 읽기 전용 inventory exit 0, offline analyzer/preparation passed, 7개 Python script syntax passed. 현재 ABP 직접 locomotion 9개 및 보호 AnimSequence 280개를 확정했다.
- 중단 원인: 일반 Unreal Editor PID 13372가 열린 상태다. Computer Use surface에는 Windows 앱이 노출되지 않아 Save All/정상 종료를 자동화할 수 없다. 라이브 에디터가 저장 후 commandlet 결과를 되덮는 것을 막기 위해 package mutation을 시작하지 않았다.
- 재개: 사용자가 Editor에서 Save All 후 종료 → inventory/analyzer/preparation 재실행 → `backup_das_animation_timing.py` → `run_das_animation_batches.py 10` pilot → 전체 `run_das_animation_batches.py` → `audit_das_animation_timing_import.py` fresh audit 순서다.

### 2026-09-16 DualAxeSword import preflight 갱신

- 읽기 전용 UE commandlet preflight가 710/710개를 통과했다. 기존 교체 337개, 새 생성 373개, Composite playback 360개, Dilation bake 250개, Root Motion 활성 대상 591개이며 보호 locomotion destination 교집합은 0이다.
- root topology 이관의 component pose 보존 최대 오차는 위치 `1.02280922446851e-16 cm`, quaternion 성분 `3.33066907387547e-16`, scale `1.4210854715202e-14`다. report는 `Saved/ImportReports/Khazan_DAS_AnimationImportPreflight_20260916.json`이다.
- preflight는 Content package를 저장하지 않았다. 현재 일반 Unreal Editor가 계속 열려 있어 실제 변경 시작 조건은 동일하다. 에디터 Save All/완전 종료 후 disk inventory를 다시 고정하고 backup → 10개 pilot → 전체 batch → fresh audit 순서로 재개한다.

## 2026-09-16 DualAxeSword 원본 시간축 복원 — 범위 정정 및 완료

- 사용자의 정정에 따라 locomotion 보호 범위를 전체 280개에서 현재 `ABP_Player`가 참조하는 9개로 좁혔다. 미사용 locomotion 271개는 복원 대상이다.
- 271개 구성은 source locomotion 107개, 미사용 InGame 57개, `RT_DAS_*` 107개다. source 107개는 전체 source 복원에, 나머지 164개는 파생 locomotion 교체에 포함했다.
- 현재 참조 9개도 검사했다. 24 fps × `RateScale 1.25`로 유효 cadence는 30 fps지만 원본과 sample 수/유효 길이가 다르다. AnimNotify event는 0개이고 8개에 Sync Marker 37개가 있어 이번에는 hash 보호했다. 정확한 원본 timeline 전환은 marker-aware 후속 migration 대상이다.
- 최종 manifest는 981개다: source 457개, 미사용 파생 locomotion 164개, Composite playback 360개. 기존 교체 608개, 신규 생성 373개이며 Composite basename은 원작 이름을 유지했다.
- 작업 전 백업은 `Saved/ArtBackups/DAS_Animation_PreTimingFix_20260916_182555`다. 기존 608개와 보호 9개를 hash로 고정했다.
- UE 5.8 preflight 981/981, checkpoint import 981/981, 별도 fresh-process final audit 981/981가 모두 `passed`다. final audit는 backup 608개와 보호 locomotion 9개 hash, 현재 dependency 9개, playback inventory, timing/property/metadata, RAW/COMPRESSED pose를 확인했다.
- 최종 보고서는 `Saved/ImportReports/Khazan_DAS_AnimationImportAudit_20260916.json`과 `Saved/ImportReports/Khazan_DAS_AnimationFinalAudit_20260916.json`이다. 재개할 미완료 import 작업은 없다.
- 후속 범위는 현재 참조 locomotion 9개의 marker-aware exact-source migration 여부 결정, 생성된 공격 playback의 Montage/Ability 연결, PIE에서 콤보·Root Motion·타격/VFX event 품질 검증이다.

## 2026-09-17 DualAxeSword Root Motion 이동량 결함 교정 완료

- 이전 2026-09-16 완료 판정은 CharacterMovement 월드 이동을 검사하지 않은 한계가 있었다. 사용자가 에디터에서 과도한 이동을 확인한 뒤 실제 PIE로 재현했고, 삽입 root scale에 따른 약 100배 이동과 Composite 경계 reset을 확인했다.
- `prepare_das_animation_timing.py`와 importer를 `20260917_DAS_RootMotionScaleAndContinuityV4` 계약으로 갱신했다. 플레이어 Root Motion 630개는 `C_P_Kazan` translation만 `0.01` 정규화하고, Composite 351개는 segment/trim/reverse/loop/dilation delta를 누적한다.
- 메인 Content 재임포트 981/981와 fresh final audit 981/981가 완료됐다. 실패 0, 보호 locomotion 9개 hash 일치, backup 608개 검증 완료다. 정확한 보고서는 `Khazan_DAS_RootMotionScaleImport_20260917.json`과 `Khazan_DAS_RootMotionScaleFinalAudit_20260917.json`이다.
- 격리 CharacterMovement PIE도 통과했다. `FastAtk01_M1` 종료 오차 `0.00035 cm`, `Flow_StrongAtk03_01` 경계·종료 오차 `0 cm`다. 보고서는 `Khazan_DAS_RootMotionPIEProbe_20260917.json`이다.
- 이번 import 복구 작업에 재개할 중단 지점은 없다. 후속 작업은 실제 WeakAttack Ability/Montage에서 콤보 1–5타, 카메라·충돌·타격 정지·Motion Warping을 함께 보는 플레이 품질 검증이다. 그 단계 전까지 전체 기술 연출 완료로 확대하지 않는다.

### 2026-09-17 Mesh Component scale 독립 계약으로 정정 완료

- animation preparation/import에서 임시 Player Mesh scale `0.009` 전제를 제거했다. `0.009` 기반 기존 이동표와 단일-scale 보고서는 당시 런타임 관측 이력이며 최신 에셋 계약이 아니다.
- 현행 `0.01` 보정은 라이브 `SK_Khazan`의 `C_P_Kazan` reference scale `100`의 역수임을 UE 검사로 고정했다. component scale은 에셋 입력이 아니며 `0.005`, `0.01`, `0.02` 세 임의 값에서 실제 CharacterMovement 결과를 정규화해 동일한 source 변위가 나오는 것을 확인했다.
- 최신 보고서는 `Saved/ImportReports/Khazan_DAS_AssetSpaceMovementAudit_20260917.json`과 `Saved/ImportReports/Khazan_DAS_RootMotionScaleIndependencePIE_20260917.json`이며 모두 `passed`다. 전자는 968개/failure 0, 후자는 6개 runtime probe/failure 0이다.
- Content 재임포트는 필요하지 않아 수행하지 않았다. 메인 Unreal Editor와 사용자 C++의 임시 `0.009` 설정은 변경하지 않았다. 이 정정 작업에 재개할 미완료 지점은 없다.

## 2026-09-23 `_Art/Kazan` → `_Art/Player` 폴더 이동 복구 대기

- 현재 상태: 크래시 뒤 `Content/_Art/Kazan`과 `Content/_Art/Player`가 함께 남았다. Asset Registry 표적 감사에서 이전 루트는 271개 package, 새 루트는 9,458개 package였고 이전 package 271개는 모두 새 루트에 대응 항목이 있다. 새 루트 package에서 이전 루트로 향하는 dependency edge와 외부 referencer는 각각 0개였다. 감사 결과는 `Saved/KZArtFolderRepairAudit.json`이다.
- 완료한 보존 조치: `Saved/ArtBackups/KazanToPlayer_PreCleanup_20260923_1110/Kazan`에 이전 폴더 304개 파일, 378,181,586 bytes를 복사했다. 원본과 backup의 SHA-256 전수 비교는 mismatch 0이다. 이전 폴더에만 있던 JSON metadata 33개는 충돌 없이 `Content/_Art/Player`의 같은 상대 경로로 복사했고 hash mismatch 0을 확인했다.
- 마지막 검증: `Content/_Art/Kazan`은 현재도 304개 파일, 378,181,586 bytes이며 backup 대비 누락·크기 차이·hash mismatch가 모두 0이다. quarantine 이동 시도는 파일 잠금 때문에 시작되지 않았고 이동된 파일은 0개다. 따라서 이전 폴더 내용은 손실 없이 그대로 남아 있다.
- 중단 원인: 실행 중인 Unreal Editor가 `Content/_Art/Kazan/Character/Meshs/Player_PhysicsAsset.uasset`를 열고 있어 폴더 이동이 거부된다. 에디터에는 저장되지 않은 사용자 작업이 있을 수 있으므로 프로세스를 강제 종료하지 않았다.
- 정확한 재개 절차: 사용자가 작업을 저장하고 Unreal Editor를 정상 종료한 뒤 `UnrealEditor` 프로세스가 없는지 확인한다. 그 다음 `Content/_Art/Kazan` 전체를 `Saved/ArtBackups/KazanToPlayer_PreCleanup_20260923_1110` 아래 quarantine으로 이동하고, Content에 이전 루트가 없고 새 루트 파일 수가 유지되는지 검증한다. 이후 commandlet Asset Registry 감사를 다시 실행해 이전 package·이전 dependency·외부 referencer가 0인지 확인하고 대표 map/asset load를 검증한 뒤 완료 기록을 추가한다.
- Git 반영 상태: 2026-09-23 main push 준비 index에는 `Content/_Art/Kazan` 파일이 0개이고 `Content/_Art/Player` 파일이 9,491개다. 따라서 커밋과 새 checkout에서는 Player만 남는다. 현재 로컬의 이전 폴더 실파일은 Unreal Editor 잠금과 검증 backup 때문에 index 밖에 보존돼 있으며, 에디터 정상 종료 뒤 위 절차로 제거한다.

## 2026-09-23 `_Art/Kazan` → `_Art/Player` 복구 및 정리 완료

- Unreal Editor 정상 종료 뒤 `Content/_Art/Kazan`을 `Saved/ArtBackups/KazanToPlayer_PreCleanup_20260923_1110/Kazan_RemovedFromContent_20260923_Final`로 격리 이동했다. Content의 이전 root는 없어졌고 격리본은 304개 파일, 378,181,586 bytes다. 선행 backup과 격리본의 SHA-256 전수 비교는 mismatch 0이다.
- 최종 UE 5.8.2 Asset Registry 감사 결과는 이전 root asset 0, Player root asset 9,458, Player에서 이전 root로 향하는 dependency edge 0이다. `SKM_Player`, StrongAttack Montage, HeinMach World, StormPass World 대표 4종은 모두 새 경로에서 실제 load됐다.
- `/Game/_Art/Kazan/.../AM_DAS_StrongAttackCombo` 이전 경로 load는 Core Redirect를 거쳐 `/Game/_Art/Player/.../AM_DAS_StrongAttackCombo`로 정확히 해석됐다. 결과는 `Saved/KZArtFolderFinalVerify.json`, 로그는 `Saved/Logs/KZArtFolderFinalVerify.log`다.
- commandlet 자체 exit code 1은 이 작업과 무관한 기존 `GameFeatureData` class load ensure 때문이다. Python 검증 스크립트는 성공했고 `old=0`, `new=9458`, `old_dependency_edges=0`, `representative_failures=0`, `redirect_failures=0`을 기록했다.

## 2026-09-30 HeinMach 사용자 시작점 기반 Respawn Target — Editor 종료 대기

- 사용자 보존 조건은 현재 저장된 `L_HeinMach_Environment.umap`을 기준으로 고정했다. 사용자가 옮긴 `HM_Tutorial_PlayerStart_DualAxeSword`는 위치 `(12083.049, 12216.91, 202.70361) cm`, 회전 `(Pitch 0, Yaw -114.98620605468753, Roll 0) deg`이며, 사용자가 삭제한 메시를 복원하거나 대체하지 않는다. 사전 검사 시 map SHA-256은 `14AAAD6401BD8BCA83AC71B89C221D3F57651B7A1934E2158FC9BE35D0A85303`, 전체 actor `9,608`, StaticMeshActor `9,098`이다.
- 읽기 전용 사전 검사는 원작 자동 진행 `xxAutomationAction_MoveTo_9`의 source action `626`, point `18`, `(12251.97555, 12132.0716, 254.924115) cm`을 현재 PlayerStart에서 `196.114 cm` 떨어진 가장 가까운 원작 진행점으로 선택했다. 이 위치에는 `HM_PlayerRespawn_WeaponTutorial` TargetPoint를 둘 예정이다. commandlet에서는 Pawn collision trace와 Recast projection을 사용할 수 없어 실제 발 디딤 surface는 아직 PIE 검증 전이다.
- `HeinMach_LevelData.json`의 원작 Monster spawn `47/47`을 TargetPoint 명세로 매핑했다. 기존 `HM_TutorialSpawn_01_EmpireSword`, `HM_TutorialSpawn_02_EmpireSwordShield` 두 개는 위치를 바꾸지 않고 재사용하며, 나머지 45개와 Player respawn 1개만 새로 만든다. 이 표식은 spawn anchor이며 실제 사망·재생성 수명과 Encounter 완료 처리는 아직 연결하지 않는다.
- 현재 맵의 임시 복제본에 실제 적용 스크립트를 실행하고 재로드했다. 새 actor `46`, 최종 TargetPoint `48`, Monster coverage `47/47`, 기존 actor 누락 `0`, 기존 actor transform 변경 `0`, StaticMeshActor `9,098 → 9,098`을 확인했다. 시험 복제본과 시험 backup/report는 검증 뒤 제거했다.
- 중단 원인은 일반 Unreal Editor PID `27180`에 같은 프로젝트가 열린 상태이며 Computer Use에 제어 가능한 Windows surface가 노출되지 않는 점이다. 라이브 에디터의 미저장 상태 또는 후속 저장이 commandlet 결과를 덮어쓰는 것을 막기 위해 실제 맵에는 아직 TargetPoint를 저장하지 않았다.
- 정확한 재개 절차: 사용자가 Unreal Editor에서 `Save All` 후 정상 종료 → `Scripts/HeinMach/audit_heinmach_respawn_targeting.py` 재실행 → PlayerStart transform과 map hash 재고정 → `Scripts/HeinMach/target_heinmach_respawns.py` 실행. 적용 스크립트는 현재 맵을 `Saved/ArtBackups/HeinMach_RespawnTargets_PreApply_20260930`에 먼저 복사하고, 기존 actor/StaticMeshActor/PlayerStart 보존 검사와 Monster `47/47` coverage가 통과할 때만 저장한다. 이후 fresh read-only audit와 PIE surface 확인을 수행한다.
- 현재 사전 검사 보고서는 `Saved/ImportReports/HeinMach_RespawnTarget_Preflight_20260930.json`이다. commandlet process exit `1`은 기존 `/Script/GameFeatures.GameFeatureData` ensure 때문이며 Python 표식 `KZ_HEINMACH_RESPAWN_PREFLIGHT_PASSED_WITH_RUNTIME_SURFACE_UNVERIFIED`와 report status를 실제 판정으로 사용한다.

## 2026-10-01 StormPass Blade Phantom arena polish — 작업 중 체크포인트

- 범위는 `L_StormPass_Environment`의 두 보스 환경과 Art 문서/검수 도구다. 작업 전 map 및 phase metadata를 `Saved/ArtBackups/StormPass_BladePhantom_PrePolish_20261001`에 보존했다. 기존 C++/Engineering 변경, HeinMach map, PlayerStart를 수정하지 않는다.
- 원작 phase 1은 성채 홀, phase 2는 숲/landscape 환경이며 동일 좌표 영역의 서로 배타적인 source sublevel이다. `SA_BladePhantom.DependentLevelPath`는 phase 2를 지목한다. source spawn/TargetPoint와 컷씬 staging 좌표를 구분해 editor-only 마커 5개와 검수 카메라 2개를 추가했다.
- 검증 완료: root prop 1,862, child prop 515, 기존 source light 24, fog sheet 7, foliage component 7/instance 3,218, landscape component 16의 원본 transform/존재 비교 failure 0. 페이즈 전용 native surface MI 188개에 source WEP global material 값을 적용했다. DeepGray/DeepNight sky와 zero-cloud preset을 반영하고 phase별 sun/sky/fog profile 전환을 연결했다.
- 추가 복원: source PSK 깃발 14개(원본 bounds 일치), 하위 light 28개, fire/화염벽 native billboard 47개. 조명 단위, cloth wave와 FX 실행은 native adapter이며 원작 실행 그래프/광도 단위의 완전 재현을 주장하지 않는다. `MissingRenderPolicy.json`에 임시값과 근거를 기록했다.
- 체크포인트 map은 phase 1과 추가 actor 89개까지 저장했다. 이후 phase 2 렌더 검수 상태는 RAM에 있으며 최종 저장/재로드 감사 전이다. 보고서: `Content/_Art/Player/Environment/StormPass/Metadata/BladePhantom_ArenaPolish_20261001`; 이미지: `Saved/ArtReviews/BladePhantom_20261001`.
- 남은 작업: phase 2 fog-sheet MPC 색 native 연결, source material-slot/override 대응 감사, FX shader/표시 검수, 두 phase 최종 이미지, 사용자 파일 hash 보존 검사, 최종 map 저장/재로드 및 Art 결과 문서 추가.
- 정확한 재개: 라이브 StormPass에서 `runpy.run_path('Scripts/StormPass/polish_blade_phantom_arenas.py')`의 `view('boss_phase_1'/'boss_phase_2')`로 검수한다. 추가 render 적용은 `restore_blade_phantom_missing_render.py`의 `prepare_flag/prepare_fire_materials/place_missing/register_variants`를 재사용한다(기존 label 재사용). `preflight_backup()`를 재실행해 새 상태로 기존 backup을 덮어쓰거나, 오래된 전체 map rebuild/route-anchor 복원을 실행하지 않는다. 검사 통과 후 `save_polish()`로 이 map만 저장하고 재로드 검사한다.

### 2026-10-01 StormPass Blade Phantom arena 폴리싱 — 저장·재로드 완료

- 위 체크포인트의 남은 Art 수정/검수를 완료했다. Phase2 fog sheet 색 native bridge를 마지막 재질 단계로 저장했고, source 슬롯 3,143개·재질 203개·source geometry 및 추가 render 89개를 검사했다. 물 runtime binding 2개와 나무 legacy selector의 오탐은 원작 metadata/실제 shader graph로 판정했다.
- Phase1과 Phase2를 각각 저장하고 실제 World가 교체되는 재로드를 수행했다. geometry/material/slot/추가 render/variant/environment 감사 실패 0, 기존 arena actor 누락 0, 최종 actor 14,522다. native flag bounds 오차 최대 `0.000004296875 cm`, editor-only marker/camera 7개가 유지된다. UE가 재생성하는 editor-only icon sprite의 임시 visibility는 gameplay contract에서 제외하며 native MaterialBillboard FX는 검사했다.
- 최종 전달 map은 Phase1 검수 모드다. 재개할 미완료 map 적용 단계는 없다. 정확한 재검수는 결과 정본의 Output Log Python 명령으로 `view('boss_phase_1'/'boss_phase_2')`를 선택하고 마커·ReviewCamera를 확인한 뒤 본체와 finish helper의 read-only 감사기를 사용한다. 바깥 경로는 `view('traversal')`다.
- 결과 정본: [STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md). Source/정책/재로드 자료는 `Metadata/BladePhantom_ArenaPolish_20261001`, 렌더는 `Saved/ArtReviews/BladePhantom_20261001`이다. 원본 backup은 보존했다.
- Source/HeinMach 보호 파일은 hash 동일하며 기존 사용자 작업을 되돌리지 않았다. 작업 중 Engineering 문서 4개에서 외부 변경을 감지했으나 Art 도구의 작성 대상이 아니며 그대로 보존했다. 도구 import가 만든 기존 `.pyc` 변경은 복구했다. Git commit/push는 요청하지 않아 수행하지 않았다.
- 후속 범위는 원작 Niagara/Cascade/cloth 실행과 water-spline DI 9개의 상세 포팅 또는 gameplay 자동 페이즈 전환이다. 원작 renderer 단위/실행 그래프가 확인되지 않은 설정은 임시값/근사로 계속 표시한다. 현재 요청의 저장된 환경 폴리싱 및 두 장소 마킹과 이 후속 개발을 구분한다.

### 2026-10-01 Phase1 밝기/흰빛 재검토 — 진행 체크포인트

- 사용자 피드백으로 원작 스크린샷 3장을 `Saved/ArtReviews/BladePhantom_LightingReview_20261001`에 확보했다. 낮은 적갈색 명도, 작은 따뜻한 불빛, 남아 있는 성채 음영을 비교한다. 이번 조명 수정 수치는 native adapter/임시 튜닝이며 원작 photometric 단위 확정값이 아니다.
- 수정 전 map·정책·스크립트와 Phase1 fire parent/MI/texture 6개는 `Saved/ArtBackups/StormPass_Phase1_LightReview_20261001`에 보존했다. 검수 중 에디터 저장본은 그 안의 `EditorSavedDuringReview`에 추가 보존했다. 저장된 검수 중 map에는 임시 SceneCapture actor가 포함될 수 있으므로 완료 전 `save_polish()`로 제거한다. 사용자 배치나 PlayerStart를 백업으로 일괄 되돌리지 않는다.
- `Phase1LightReviewBefore.json`에는 41개 local light, PP, sun/sky, PlayerStart의 실제 사전 값이 있다. 기존 root light 13개는 source Intensity 2.5/3 × 750을 candela로 쓰며, 하위 light 28개는 별도의 이전 adapter를 사용했다. PP는 3 EV이다. 노출만 1 EV로 낮추는 비교는 성채 전체를 검게 만들었으므로 최종 수정으로 채택하지 않는다.
- Phase1 core fire 원본 RGB texture를 밝기 mask로 바꾼 뒤 다른 root light의 파란색으로 칠한 기존 근사를 수정 중이다. 실제 `core_fire`의 StartColor는 Small export 87 / Medium export 102에서 `(0.964706,1,0)`이며, source/LOD/sha 근거는 `CascadeCoreColorSources.json`이다. `restore_blade_phantom_missing_render.py`의 재현 경로는 원본 atlas RGB × core StartColor로 수정했다. map/최종 조명 적용 및 렌더 검수 완료 전이다.
- 07:56:54 UTC 에디터 충돌은 MaterialEditor→Python 경로의 null pointer다. UE 5.8 `MaterialEditingLibrary.cpp:GetInputsForMaterialExpression`은 연결되지 않은 pin에 `None`을 반환하고 MaterialExpression null을 검사하지 않는다. 재귀 그래프 검사에서 `None`을 다시 전달한 호출을 원인으로 좁혔다. 재개 시 `if not node: return` 및 non-null child만 재귀하는 보호를 반드시 적용한다. 해당 호출을 그대로 반복하지 않는다. 이 충돌 전에 Phase1 fire asset 6개는 새 상태로 저장되지 않았다(parent hash 사전 값과 동일).
- 정확한 재개: 라이브 UE/Rider health와 현재 dirty map부터 확인한다. 관련 없는 dirty `AM_DAS_Player_Dodge`는 저장/변경하지 않는다. StormPass를 열고 null-safe graph 연결 수정으로 Phase1 fire asset 6개만 저장한다. 13 root/28 child light와 Phase1 PP를 원작 화면에 맞춰 native adapter로 비교한다. 정책을 기존 `PolishPolicy.json`에 모으고 `apply_phase_environment`의 Phase1 분기에서 재사용한다. Phase2/바깥 광원은 변경하지 않는다. 안정된 비교 렌더 뒤 `save_polish()`→map 재로드→정책/표시/PlayerStart/원본 geometry 검증을 완료하고 아래에 결과를 추가한다.

### 2026-10-01 Phase1 밝기·흰빛 재검토 — 저장·재로드 완료

- 위 체크포인트의 적용·저장·검증을 완료했다. 원본 core fire RGB/StartColor를 연결한 6개 asset을 저장했다. compression이 sRGB를 재설정하는 추가 문제는 적용 순서를 바꾼 후 저장/readback 검사로 해결했다. null node를 다시 native graph API에 넘기지 않는 직접 연결 검사로 확인했다.
- 이전 3 EV와 candela 변환을 이번 native adapter로 대체했다. 정책은 `PolishPolicy.json`의 Phase1 전용 설정, 재현은 `polish_blade_phantom_arenas.py:apply_phase_environment`다. 원작 field/계산/임시값·선정 이유·검증 기준을 [Art 정본의 마지막 절](STORMPASS_BLADE_PHANTOM_POLISH_2026-10-01.md)에 추가했다.
- 빠진 붉은 안개의 원인은 실제 session `r.VolumetricFog=0`이었다. 현재 CVar는 1이고 `sg.ShadowQuality=1`은 유지했다. UE 5.8 기본 Shadows High 이상이 fog를 활성화한다. Phase1 검수 전환은 session CVar를 켜며 프로젝트/scalability INI는 변경하지 않는다. 다른 변형에도 해당 session 렌더 기능은 적용될 수 있으나 Phase2 asset 설정은 바꾸지 않았다.
- 두 페이즈 전환 및 Phase1 저장 후 실제 World 교체 재로드를 완료했다. local light 41개와 PP 노출/bloom/FilmSlope 저장값, PlayerStart pose 유지. actor 14,522, 임시 capture 없음, dirty map 없음. Phase2 point light 11개 및 PP 설정 불변. geometry·추가 render 89개·visibility 3,220개·environment 감사 실패 0. 최종 unrelated dirty content는 사용자가 작업 중인 `GA_Player_DodgeAbility_B`였으며 저장하지 않았다.
- 마지막 검증은 `LightReview_ReloadVerification.json`, `LightReview_*Reloaded.json`, `LightReview_Phase2Regression.json`이다. source/저장 hash와 비교 원작 이미지는 `Phase1LightReviewSourceManifest.json`, 최종 렌더는 `Saved/ArtReviews/BladePhantom_20261001/Phase1_LightReview_Delivery.png`다. 백업 `Saved/ArtBackups/StormPass_Phase1_LightReview_20261001`과 검수 중 에디터 저장본은 보존했다.
- 미완료 저장 단계는 없다. 정확한 재검수: 연결/현재 map/dirty 상태 확인 → 정본의 Output Log Python 명령으로 `view('boss_phase_1'/'boss_phase_2')` → 환경/variant 감사 → 필요 시 이 맵만 `save_polish()`로 저장. 새 조사 전에 위 manifest/정책/보고서를 읽는다. 전체 map rebuild, route-anchor 복원, save-all로 사용자의 PlayerStart·삭제 메시·Dodge 작업을 되돌리거나 저장하지 않는다. 원작 custom renderer/full FX 포팅과 gameplay 자동 phase 전환은 별도 후속 범위다.

### 2026-10-02 두 전장 인접 배치 — 충돌 바닥 검사 전 체크포인트

- 사용자가 옮긴 현행 `/Game/Maps/L_StormPass_Environment`에서 Phase1은 유지하고 Phase2 전체 1,120 actor를 X +20,390 cm 평행 이동했다. 양쪽 표시·충돌 baseline과 bounded PP를 동시에 활성화하고 `ArenaMarkers` 폴더의 주 마커 두 개를 분리했다. 새 Phase2 landscape material의 world origin도 같은 양만큼 이동하여 UV 정합을 유지했다. 별도 sun 1개 추가, actor 14,523. 맵 저장 및 World 교체 재로드 검증 실패 0.
- 자료/백업: `Metadata/BladePhantom_SideBySide_20261002`, `Saved/ArtBackups/StormPass_SideBySide_20261002`. 원래 겹친 source 좌표와 백업은 보존한다. 사용자 PlayerStart, 삭제 메시, 게임 C++/BP는 수정하지 않았다.
- 마지막 검사에서 기존 중심 바닥은 Visibility 지면 trace 4개 모두 미검출이었다. 각 전장 혈수 영역에 보이지 않는 BlockAll 충돌 상자 1개씩 보완하는 단계가 남았다. 이것은 원작 collision metadata 복원이 아닌 편집용 근사다.
- 첫 floor preflight는 다섯 바닥 타일의 높이가 모두 같다는 잘못된 가정으로 중단됐으며, 해당 호출은 scene을 변경하지 않았다. 중심 마커 XY를 포함하는 `HISM_WP_Base_Floor_001_500X500_a5` 타일의 실제 bbox maxZ 89.00001 cm / 두께 20 cm를 선택하도록 수정했다. 진입·계단의 높은 타일은 배제한다.
- 재개: UE health → 현재 World·dirty map 확인 → 다른 clean map이면 현행 StormPass를 로드 → 기존 `polish_blade_phantom_arenas.py`의 `add_arena_collision_floors()` 실행 → 단순/복합 지면 trace → 이 맵만 저장 → World 교체 재로드 후 지원 바닥·2마커·UV·PlayerStart 확인 → Art 결과/manifest 추가. 다른 dirty map을 버리거나 Save All, 원본 좌표로 route 재복원, 전체 맵 재생성을 하지 않는다. 캐릭터/AI PIE 및 전 레벨 NavMesh 검증은 아직 수행하지 않았다.

### 2026-10-02 두 전장 인접 배치 — 지원 바닥 포함 저장·재로드 완료

- 위 체크포인트의 지원 바닥 적용/검증을 완료했다. 중심을 포함하는 floor tile a5의 bbox에서 topZ 89.00001 cm/두께 20 cm를 선택하여 두 blood-water core에 보이지 않는 BlockAll floor를 추가했다. source 타일 높이 전체가 같다는 가정은 사용하지 않는다. 최초 preflight는 변경 전 중단되었고, 이후 HitResult 직접 속성 조회 실패는 `to_dict()`로 해결했다. source collision 변경 없음.
- 최종 현행 map actor 14,525. map 저장 후 실제 World 교체 재로드, 중심/진입/보스 표식 단순·복합 trace 8/8, 두 마커/PP/geometry 표시, landscape material 16개 및 사용자 PlayerStart pose 유지, dirty map/content 없음. 미완료 적용 단계 없음. viewport screenshot API는 실패하여 새 이미지 검증을 주장하지 않는다.
- 최종 자료: `Metadata/BladePhantom_SideBySide_20261002/ReloadVerificationWithCollision.json`, `GroundSupportReloaded.json`, `Layout.json`, `SideBySideSourceManifest.json`; 기존 분리-only `ReloadVerification.json`은 이 단계보다 먼저 생성된 기록으로 보존한다. 전체 결과는 Art 폴리싱 정본 하단 2026-10-02 절이다.
- 재개는 UE health/현재 World/dirty 상태 확인 → 현행 `/Game/Maps/L_StormPass_Environment` → Outliner `ArenaReference` 또는 기존 helper `view('boss_phase_1/2')`로 시점 선택이다. 양쪽은 계속 표시된다. `separate_arenas`를 다시 이동 도구로 사용하지 말고, 변경 필요 시 저장 `Layout/ActorsBefore/ForegroundBoundsBefore`를 기준으로 표적 작업한다. `add_arena_collision_floors`는 기존 layout 기록이 있으면 사용자 삭제 floor를 자동 재생성하지 않는다. 백업 덮어쓰기/전체 map rebuild/Save All을 하지 않는다.
- 후속 별도 범위는 실제 Character/AI PIE의 지지·이동 및 필요한 NavMesh/벽 조사, runtime boss 전환/teleport/respawn 연결, 완전히 분리된 sky/fog/GI renderer다. 이번 사용자 요청의 인접 전장과 각 1개 주 마커는 저장까지 완료했다. 게임 C++/BP 및 HeinMach를 이 작업에서 편집하지 않았다.

### 2026-10-02 InGame 애니메이션 재생 속도 보정 — 사전 분석 체크포인트

- 사용자 직접 수정 요청 범위는 `/Game/_Art/Player/Animation/InGame` 아래 애니메이션이다. 현재 AnimSequence 140개, Montage 5개, BlendSpace 2개, LevelSequence 3개를 읽었다. 아직 게임 애니메이션 쓰기/저장은 하지 않았다.
- Router → Art 규칙/지식 인덱스 → `DAS_ANIMATION_RESTORATION_2026-09-16.md`의 V4 공간 계약 및 V5 exact 60 Hz 계약을 확인했다. 원본 시간축을 가진 CA와 Dilation-baked playback을 구분하며 기존 WeakAttack 5개의 사용자 crop과 9개 현행 locomotion의 24 fps × 1.25 보정을 유지한다.
- 예전 `Saved/Extracted/DualAxeSword_20260916` 원본 자료는 현재 없었다. 현행 metadata tag의 정확한 OriginalPackage와 남은 exact60 report에서 필요한 원본만 `Saved/Extracted/InGame_Playback_20261002/Metadata`에 표적 재추출했다. 원작 package basename과 export Object Name이 다른 강공격/가드 이동이 있어 full package 참조를 키로 사용해야 한다.
- 실제 Player Mesh relative scale은 약 0.01, SK_Player의 C_P_Kazan reference scale은 100이었다. component scale은 시간 보정 입력이 아니며 기존 root translation 정규화를 재적용하지 않는다. gameplay C++/BP/Skeleton/mesh는 수정하지 않는다.
- 현재 계획은 기본 분기의 segment rate/Dilation을 기존 source pose 순서에 bake하고 현재 full-source 범위를 보존하는 것이다. 원작 Composite가 소비하지 않은 prefix/tail은 기존 source cadence로 유지하며 이를 원작 Composite 전체의 직접 복제로 표현하지 않는다. 출력은 exact 60/1, RateScale 1.0이다. 원작 raw source가 여러 다른 위치에서 반복 사용되는 UltimateSlash Air/Loop는 한 source RateScale로 표현할 수 없어 완성된 기존 Composite playback을 InGame 안에 준비하는 계약을 검토했다.
- 자료: `Saved/ImportReports/InGame_Playback_SequenceSnapshot_20261002.json`, `InGame_Playback_MontageSnapshot_20261002.json`, `InGame_MontageExports_20261002`, `Saved/Extracted/InGame_Playback_20261002/ScopeMapping.json`, `SkillStateConsumptions.json`, `PlaybackPlan.json`. 계획은 강공격 package/object 이름 차이와 Walk 3개 원본 추가 조회를 반영해 최종 고정 전이다.
- 정확한 재개: UE health/PIE stopped/dirty 상태 확인 → 최종 full-package 계획 검증 → InGame package byte backup 및 범위 밖 보존 manifest → temporary duplicate에서 재표본화/endpoint/root track/몽타주 section·notify 리타이밍 증명 → 대상만 적용/저장 → 새 process RAW/COMPRESSED/time/root/property 감사 → Art 결과와 이 절 아래 완료 기록. 전체 DAS importer/Force Delete 반복/Save All/원본 또는 사용자의 crop 복원을 실행하지 않는다.

### 2026-10-02 두 레벨 shader/look 재복원 — 조사·백업 체크포인트

- 사용자 새 요청: HeinMach/StormPass의 누락 전역 shader·material·toon을 최대한 복원하고 StormPass는 보스 2개 전장만 사용한다. Phase2 distant background 및 주변 landscape는 보존/검토하며 다른 source route actor는 명세/백업 후 정리한다. HeinMach 사용자 PlayerStart·삭제·transform override 보존 조건 유지.
- 먼저 Art Router/상태/지식/규칙/StormPass 정본을 확인했다. 기존 canonical HeinMach material/fog report 상당수는 현재 Saved/ImportReports에 없으므로 문서의 완료 기록만으로 현재 적용 상태를 단정하지 않는다. 원본 Source와 현행 맵에서 표적 재감사를 진행한다.
- FModel의 현재 provider를 사용하는 기존 EnemyExtractor로 ERP_Base, WEP base/HeinMach_OP/Phase2, M_AKCartoonCharacter 등 9 package와 WorldMPC/WorldProp master/CTP_Snow를 표적 재추출했다. shader model MSM_BBQCartoon 및 ShadingSmoothness/CellShadingThreshold/Shading Width/Shading Intensity, outline settings는 보존됐지만 MaterialExpression/function 본문은 cooked export에서 제거됐다. 원본 전용 엔진 shader의 완전 복사 가능성을 주장하지 않는다.
- 현재 StormPass 양쪽 PP의 WeightedBlendables는 비어 있다. Phase2 sky/height fog/GI가 Phase1 환경을 공유하고 source covering color 등은 native graph에 연결되지 않았다. 새로운 native shader adapter, 지역 direct light/fog, Phase2 sky/background 및 HeinMach source PP/표면 누락을 실제 적용할 예정이다. 게임 C++/전투·애니메이션은 대상이 아니다.
- 라이브 UE PID 27896/PIE Idle, 두 현재 `/Game/Maps` 맵이 존재하며 마지막 dirty maps/content는 없다. immutable 백업 `Saved/ArtBackups/LevelLook_PreRestore_20261002`에 두 맵/Player BP/Config/현재 phase helper 3개를 보존했다. 원본 재추출/요청은 `Saved/Extracted/LookRestoration_20261002`에 있다.
- computer-use 스킬을 읽고 @oai/sky 초기화를 시도했으나 native pipe unavailable (os error 2)로 실패했다. UI를 실제 확인한 것으로 기록하지 않는다. 지원 API로 UE shader/RHI 및 재로드를 검사하고 Rider viewport 캡처를 필요한 범위에서 시도한다. custom UI helper를 띄우거나 키/설정 내용을 출력하지 않는다.
- 정확한 재개: UE health/dirty 상태 → 표적 native scene snapshots/HeinMach exclusions 확인 → backup manifest 유지 → source look manifest와 기존 기능을 사용하는 Art builder 작성 → 새 shader compile/scene 적용 → 이 작업 asset 및 대상 맵만 저장 → 각 맵 World 교체 재로드/geometry·material·PP·character stencil·background·source 값 검사 → 화면 검수 가능 여부와 근사/미복원 목록을 명시 → Art MD에 날짜별 실제 결과 추가. 이전 전체 map rebuild/Source reset/Save All을 하지 않는다.


### 2026-10-02 InGame DAS 속도 보정 — 적용·새 프로세스 검증 완료

- 위 사전 분석 체크포인트 이후 frozen plan/150개 byte backup을 고정하고, 임시 복사본으로 sequence/몽타주 이관을 증명했다. 실제 retime 22, cadence RateScale 18, 강공격 Montage 2, V5 standalone copy 2를 저장했다. ApplyReport 44개 모두 passed, 시퀀스 100개 기존 package hash 동일. probe 2개 삭제, 최종 scope package 152, 대상 dirty content 없음.
- 새 프로세스 audit: 142 sequence/5 montage, 모든 retime/copy의 RAW/COMPRESSED 전 본 5개 시점 및 root/grid/길이/본 순서/옵션 검사 passed. 강공격 Montage의 3/2 section, 7/3 notify 및 같은 개수 branching cache를 재로드해 검사했다. 최초 segment 문자열 검사는 엔진의 약 1 μs 시작 시각 정리로 실패했고, 기존 1e-5 s 수치 검사로 보완한 최종 결과 passed. 게임 에셋의 추가 타이밍 수정으로 숨긴 실패가 아니다.
- 공간 배율은 수정하지 않았다. Player mesh 세 축 0.009999999776482582 재확인, game Source/Skeleton/mesh와 범위 밖 animation 870개 보존. 동시 다른 작업/사용자 저장으로 Config/DefaultEngine.ini·BP_Player·DodgeAttack Montage baseline hash가 달라져 해당 변경을 유지했다. 이 작업은 그 파일을 저장하지 않았다.
- 정본: [INGAME_DAS_PLAYBACK_CORRECTION_2026-10-02.md](INGAME_DAS_PLAYBACK_CORRECTION_2026-10-02.md). 지속 metadata/report는 Metadata/InGamePlayback_20261002, 원래 byte backup은 Saved/ArtBackups/InGame_Playback_PreFix_20261002(150/150 SHA 검증). 이전 사전 계획 표기와 초기 failed 검사는 당시 상태다. 최종 미완료 에셋 적용 단계 없음.
- 이후 재개: Router → Art 결과 정본/V4·V5 필요한 절 → 대상 TimingContract/DASTimingVersion 및 저장 PlaybackPlan/ScopeMapping → 새로 들어온 에셋의 원본/소비 분기만 조회 → 새 snapshot/backup/계획 → 필요한 대상만 수정 → fresh-process 확인. 이미 retime한 22개에 Dilation을 다시 bake하지 않는다. 현재 helper는 원본 backup/hash/grid guard로 중복 적용을 거부한다. 기본 분기 외 강화율·standalone gameplay 연결·실제 PIE 화면 비교는 별도 소비 문맥에서 확인한다.


## 2026-10-02 두 레벨 source 룩 복원 — 저장·검증 결과

- 위 조사-only 체크포인트 이후 두 실제 맵 및 native rendering assets를 저장했다. 상세 실제 결과/수치 계약은 [LEVEL_LOOK_RESTORATION_2026-10-02.md](LEVEL_LOOK_RESTORATION_2026-10-02.md)를 따른다. 이전 “map 적용/삭제 아직 하지 않음” 상태를 현행으로 사용하지 않는다.
- 마지막 검증: StormPass 2,547 actors / live used MI·material 211 (fresh NullRHI 210), HeinMach 9,609 / 662. missing slot/검사한 packed mismatch 0. SP keep 누락/삭제 잔존 0, ground 8/8. HM Start/수동 override/18+109 tombstone 모두 보존. fresh-process map·Player body/두 weapon stencil readback exit 0. native 주요 shader 9개 SM6 statistics 양수.
- immutable backup main 7개/추가 asset 102개 SHA-256 일치. 현재 backup은 `Saved/ArtBackups/LevelLook_PreRestore_20261002`, 최종 보고서는 `DeliveryVerification.json`, 새 process log는 `Saved/Logs/LookFreshAudit_Final_20261002.log`다.
- 장애/복구: Rider game-thread의 implicit Interchange texture import가 `TaskGraph.cpp:705` recursion assert를 두 번 유발했다. 명시적 `TextureFactory`로 변경해 58개 texture import 성공. source sky noise sampler LinearColor 오류도 LinearGrayscale/Masks로 수정했고 최종 sky PS 197로 컴파일됐다. 원인 확인된 Art importer 문제로 gameplay C++/config를 수정하지 않았다.
- 첫 별도 commandlet은 `/Script/GameFeatures.GameFeatureData` load ensure/exit 1이었다. 테스트 process만 `-EnablePlugins=GameFeatures`로 재검증해 exit 0. 프로젝트 설정 변경 아님. headless 검사를 최종 visual/PIE 동등성으로 보고하지 않는다.
- 미완료: 최종 Phase2 EV2.5/색상·mask·haze·sky 화면 비교, HeinMach tutorial/지역 및 P1 interior 최종 화면 회귀, 실제 Character/AI 이동·boss 자동 전환. 원작 custom renderer·NTP·FFX/custom PP·RVT/water 전체 함수와 runtime WEP 혼합은 source 코드 미확보 상태다.
- 마지막 화면 접근은 stale/캡처 실패였다. 이후 editor가 PID 12024에서 30964의 다른 세션으로 바뀌었고 Rider `get_editor_world()`는 None, PIE state Idle이었다. 해당 새 세션의 맵/자동화 작업을 재설정하지 않았다. 이전 세션의 capture-only camera/gameview/realtime/Slate throttle override를 저장한 적은 없고 그 세션은 종료됐다.
- 정확한 재개: Router→위 정본/최종 reports→UE health/PIE/authoring World/dirty 확인. 다른 작업을 중단하거나 Save All 하지 않는다. 레벨 viewport를 사용할 수 있을 때 `/Game/Maps/L_StormPass_Environment`의 P2 review 시점 및 P1 interior, HeinMach 사용자 Start를 실제 프레임이 갱신된 단일 viewport로 검수한다. capture-only state는 저장하지 않고 원복한다.
- 조정은 `restore_level_look.py:NATIVE`/해당 MI의 native adapter 값만 표적 변경하고 source 값은 보존한다. 새 변경이 없으면 full importer/texture 재추출/terrain 재생성/`storm_prune_plan` 재생성/`separate_arenas` 반복 이동을 하지 않는다. 변경 후 관련 asset만 저장→map 재로드→필요 시 `audit_level_look_fresh_process.py`로 fresh readback. 원작 renderer 동일성은 추가 자료 없이 완료로 바꾸지 않는다.

## 2026-10-06 HeinMach 후처리·원작 하늘·강설 재검토 — 조사 체크포인트

- 사용자 요청: HeinMach 후처리의 어색함 수정, 원작 SkyBox와 자연스럽고 효율적인 강설 복원. 추가 지시로 Rider가 실행한 사용자 Editor PID 22696은 조작하지 않고 별도 숨김 background process에서만 작업한다.
- Router → Art 상태/규칙/지식/continuity → LEVEL_LOOK_RESTORATION_2026-10-02.md와 저장 SourceManifest를 확인했다. 게임 Source/BP·WeakAttack 및 StormPass 변경은 이번 범위가 아니다.
- 마지막 검사: isolated NullRHI commandlet `heinmach_weather_probe.py` exit 0. 현재 저장 HeinMach snapshot은 Rendering/Metadata/HeinMachWeather_20261006/Before.json이다. 게임 맵·에셋은 아직 변경하지 않았다. read-only authoring/API probe 및 background runner만 생성했다.
- 발견: 기존 native_pp_settings는 원작 bOverride=false인 직렬화 field까지 true로 적용한다. 현재 bounded PP에는 bloom 7.5, flare 50, dirt 25/1000, motion blur target 17이 있어 native renderer 화면을 별도 검수해야 한다. Sky는 OP preset 단일 적용이며 source WEP에는 WAS_IceBlizzard 등의 실제 atmospheric component가 있다.
- 표적 추출 진행: 기존 EnemyExtractor/FModel provider의 키 비출력 경로로 WAS_IceBlizzard/WindDust/Moon/Planet/PPW 및 실제 Sky/Cloud preset metadata만 조사한다. Cine opening/UI snow를 InGame 강설 근거로 사용하지 않는다.
- 정확한 재개: background process/log부터 확인 → CoreRequests/SourceDiscovery/EditorAPI → 원작 WAS_IceBlizzard가 참조하는 particle/material/texture closure 표적 추출 → 변경 package와 현재 맵 byte backup/hash → isolated builder 적용 → 별도 RHI background frame/capture 및 fresh serialization audit → Art 정본에 실제/근사/미확인과 source·임시 수치 계약 기록. 사용자 Editor에 Rider ue_* mutation이나 Save All을 호출하지 않는다.

## 2026-10-06 HeinMach weather — 저장·검수 완료 단계와 남은 원작 계약

- 위 조사-only checkpoint 이후 실제 맵/전용 rendering assets를 저장했다. 최신 정본은 [HEINMACH_WEATHER_RESTORATION_2026-10-06.md](HEINMACH_WEATHER_RESTORATION_2026-10-06.md)다. 이전 PID는 당시 사용자 세션 기록이며 그 PID나 새 Rider editor를 assistant 작업 대상으로 사용하지 않는다. 모든 authoring/검수는 hidden isolated process, RiderLink/ModelContextProtocol 비활성이다.
- 현행 map `/Game/Maps/L_HeinMach_Environment`, actors 9,610. source BSP 7 PP/81 faces, 전용 sky/region MI, 원본 2 GPU snow/dust emitter 연결 완료. `NS_HM_SourceSnow_TwoLayers`만 현행이다. 다른 기존 actor pose/PlayerStart/삭제 부재 계약은 `FreshSavedSceneAudit.json` 통과. 게임 C++/게임플레이 BP/Config/animation 및 StormPass를 이 작업에서 수정하지 않았다.
- 마지막 실제 검증: fresh saved-scene exit 0/marker passed, real-RHI `RenderGraphVerification` 4개 compile errors=0, actual standalone game exit 0/`GameViewportVerification` error 없음. game 사진 5개, primary 8,187/dust 3,115 particles, moving QA camera·Cave1 숨김 관측. GPU simulation median/P95 0.04635/0.0535 ms, translucency ON/OFF median 0.1223/0.0459 ms; hardware/조건은 정본과 PerformanceVerification 참조.
- 최종 native shadow scale 8, shadow radiance outdoor256/cave16, `disable_pre_exposure_scale=true`. `ExposureContractCorrection`이 최신값이다. `LookApplied`의 scale2는 과거 중간값. Opacity는 A-only, snow pass BeforeDOF/velocity output. NativeSnowTwoLayers.t3d와 두 real emitter 이름으로 compiled graph를 재사용한다.
- 실패 이력: 잘못된 module output/꺼진 Init write switches/GPU stale camera/중복 emitter/opacity RGB 혼입 수정. DepthFade10+translucent velocity는 UE5 compile 거부되어 해당 시도를 저장하지 않았다. bare transient material 생성으로 background game process crash 1회→MaterialFactoryNew QA asset 방식으로 재검수 성공. 마지막 성공 marker/report가 이전 SnowFailure/LookFailure보다 우선한다. 원인을 숨기거나 사용자 editor crash라고 기록하지 않는다.
- 미사용 task trial NS 4개/QA material·MI 5개는 전체 referencer0/backup SHA 동일 확인 후 제거했다. `GeneratedUnusedCleanup`/`Saved/ArtBackups/HeinMachWeather_20261006/GeneratedUnused` 참조. 사용자가 만든 asset/actor 정리가 아니다. map을 Save All 하지 않았다.
- 미복원: proprietary BBQ/custom PP shader body, ground collision/event puff·WindDust, dust VF rotation, MaxBlizzard replacement/지역 snow Spawn·color·Blow·yaw의 완전한 runtime 전환, Moon/Planet 활성화, 같은 build 원작 controlled camera 비교. 원본값만 있고 실행 의미가 불명확한 Blow를 force 배율로 가정하지 않는다. 현재 sky/PP 지역 혼합 완료를 snow 지역 제어 완료로 바꾸지 않는다.
- 정확한 재개: Router→정본/최신 continuity→SourceDiscovery/SourceParticleContracts/최종 audit/PerformanceVerification. pending contract만 표적 추출·조사하고 기존 Niagara/전용 MI/volume을 먼저 보완한다. Before.json을 쓰는 `probe`를 다시 실행하지 않는다. source component/geometry/map 전체 reset·legacy 전수 importer는 재실행하지 않는다.
- authoring 재개는 현재 map/수정 asset의 새 byte backup 후 `heinmach_weather_look.py NATIVE`·전용 MI 또는 `heinmach_weather_snow.py`의 필요한 부분만 변경한다. verified built system에 emitter를 append하지 않는다. 검수는 runner `audit`→`render_probe --render`→`game_capture --render --game`, 이어 performance analyzer. QA A/B는 `qa_materials --render`를 먼저 실행하고 task QA만 정리한다. SceneCapture/diagnostic PNG를 final game PNG로 사용하지 않는다.
- 사용자 Rider editor는 최신 disk assets/map을 assistant가 재로드하지 않았다. 사용자 미저장 작업 확인 후 본인이 map/assets를 재로드하는 단계가 필요하다. 옛 전체 map backup으로 이후 사용자 편집을 덮거나 stale live map을 저장하지 않는다. 백업 `Saved/ArtBackups/HeinMachWeather_20261006/Content`는 이전 상태의 자료다.

## 2026-10-06 HeinMach weather — 최종 디스크 검증 추가

- `DeliveryVerification.json` passed. 실제 사용 asset 15개, game PNG 5개, 4개 재질 compile errors=0, task 시험/QA 9개 backup SHA 및 디스크 부재 확인. map SHA `f229d15245e511fa3c347c96ccdd0dc1bf35ce158332e63d064aad4d8cf6f7a2`.
- Niagara 시험 4개는 UE 삭제 API 성공 후에도 원래 byte 파일이 남아, referencer0/backup SHA 확인된 정확한 작업 생성 파일만 제거했다. absent package의 registry query는 `None`이므로 cleanup 재검증에 `package_missing`을 명시한다. `NoneType` 반복 검증 오류를 처리하고 마지막 cleanup exit0/marker 통과. 사용 중인 asset·map은 이 정리에서 저장하지 않았다.
- 물리 정리 이후 fresh background audit를 다시 실행해 exit0/marker 통과, 9,610 actors와 기존 pose/PlayerStart 보존 확인. 별도 작업 Unreal 프로세스는 모두 종료, 사용자 Rider editor 조작 없음. 위 미복원 항목과 정확한 재개 절차는 유지한다.

## 2026-10-06 후속 요청 — live editor 재로드/PIE 열람 상태

- 사용자 최신 직접 요청으로 미저장 확인과 변경 에셋 열람을 수행했다. 요청 시 editor는 이미 정상 종료 상태이고 복구 목록 0개였다. 새 interactive PID 9596/RiderLink 연결, HeinMach map/전용 에셋 15개를 Delivery SHA 그대로 로드, 최초 및 최종 dirty map/content 모두 0개. Source/BP/맵/렌더 asset 저장 없음.
- `LiveEditorReloadVerification.json`, `LiveEditorPIEVerification.json`이 최신 확인이다. viewport PIE `Play`로 열어 두었으며 8,817 flakes+3,520 dust와 화면을 확인했다. 편집 복귀는 Stop/Esc. 재개 시 health/state를 먼저 확인하고 이 editor를 임의 종료하거나 기존 Play를 새로 시작하지 않는다.
- 편집 월드 outer의 NiagaraSimCache 검사만 맵 dirty를 만들었다. 작업 전 dirty0이고 임시 cache만 생성한 상황에서 저장 없이 맵을 다시 읽어 제거했다. 후속 cache는 `/Engine/Transient` outer로 생성해 dirty0을 확인했다. 해당 방식과 UE realtime override API의 handled ensure, Computer Use native pipe unavailable/retry/reset 기록은 정본에 있다. 화면은 Rider take_screenshot으로 확인했다.
- 사용자의 editor 확인 요청은 이번 live 열람/PIE 제어를 허용한다. 이전 background-only 에셋 작성 제한을 앞으로 모든 변경의 포괄적 live 편집 허가로 해석하지 않는다. 미복원 계약과 표적 조사 재개 절차는 계속 위 정본을 따른다.

## 2026-10-06 후속 요청 — 실사·약한 툰 룩 적용 및 editor 복구

- 최신 정본 [HEINMACH_LOOK_REFINEMENT_2026-10-06.md](HEINMACH_LOOK_REFINEMENT_2026-10-06.md). 사용자 방향에 맞춘 native tint/saturation/filmic grade, WorldToon `.03`/Character `.16`, outline `.02/.08`, ShadeSmoothness `.12`, native fill2, sun specular `.15`를 map+6 MI에 실제 저장했다. source RGB/sky/brush/현재 snow system과 pose는 보존했다.
- 마지막 저장본 검증: `FreshSavedSceneAudit` passed(9,610, 모든 적용 직전 pose/PlayerStart 보존), `RenderGraphVerification` 4 compile errors0/graph 비용 동일, MID 없는 `SavedGameVerification` error없음/PNG4/8,718 flakes+2,472 dust. current High preset의 snow GPU simulation median/P95 `.01755/.0226 ms`, 100 frames. 전체 frame 성능·원작 동일성 한계는 정본 참조.
- 최초 save lock Error32에서 7 package backup hash 동일. live `DEBUG RESETLOADERS` 호출이 interactive PID9596 access violation crash를 유발했으며 assistant가 사용자에게 알리고 사과했다. 직전 dirty map/content0, 저장 데이터 보존. 이후 background save/audit/RHI/game 검수 exit0·marker 통과. 이 전역 명령은 재사용하지 않는다.
- 검수 후 interactive PID25196으로 최신 map을 열고 이전 editor camera pose·100%/High/Epic AA local 품질을 복구했다. 사용자가 시작한 PIE `Play`를 유지, 최종 dirty0. `RecoveredEditorQuality/EditorRecoveryIncident`와 live screenshot 참조. console extras의 restart persistence나 PIE runtime 진행의 동일 복구는 주장하지 않는다.
- 정확한 재개: Router → 최신 Art 상태/정본 → 이번 Applied/audit/recovery → health/PIE/dirty/현재 사용자 저장 변화 확인. 필요 시 기존 `NATIVE/REALISM_GRADE`와 실제 owner만 작은 수정. 전체 weather builder·원본 actor 재생성·legacy import를 반복하지 않는다. backup은 `Saved/ArtBackups/HeinMachLookRefinement_20261006/Content`; 이후 사용자 편집을 이 backup으로 덮어쓰지 않는다.

## 2026-10-06 룩 조정 최종 점검 추가

- 이번 `DeliveryVerification` passed. 다른 전용 package9개 byte 동일, backup7개 SHA 검증, map SHA audit 동일. 마지막 `FinalLiveEditorVerification` PID25196 Idle/dirty0/최신 map9,610/100%·High·AA3. 사용자가 PIE를 종료했으므로 Play를 재시작하지 않았다. 이전 Play 기록은 중간 확인으로만 읽는다. 이번 미술 조정은 완료이며 weather 원작 일치 미검증 계약은 계속 남는다.

## 2026-10-06 마지막 live dirty 변화 — 후속 작업에서 우선

- 바로 다음 live 검사에서 HeinMach map dirty1/content0이었다. 최종 report 실제 dirty 배열이 위 dirty0 요약을 대체한다. 원인은 확정하지 않았고 추가 reload/Save All/discard를 하지 않았다. Native 저장본 Delivery/audit 완료와 live의 새 미저장 상태를 구분한다. 재개 시 dirty 내용을 먼저 확인하고 사용자 변경을 보존한다.


## 2026-10-06 DualAxeSword 전투·눈/먼지 효과 추출/임포트 — 진행 체크포인트

- 사용자 직접 요청에 따라 FModel 원본에서 휘두름/명중/가드/직전 가드/패링/피격/혈흔과 Player·Monster 달리기/대시/무기 접촉의 눈·먼지를 추출하여 `/Game/_Art/Effects`에 작성 중이다. 작업 범위는 Art assets/scripts/metadata이며 게임 Source/BP/기존 맵과 라이브 editor는 수정하지 않는다. 다른 동시 작업 변경을 보존한다.
- 재개 기준: `Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json`, Source, Bindings/Source, DependencyEdges 및 `Saved/Extracted/CombatEffects_20261006/RootRequests.json`. 현재 Cascade 751/Niagara 21, 별도 decal material/curve 42 roots다. 최종 native 수량/재생 검증은 후속 audit로 확정한다.
- 원본 JSON/payload 추출 실패 0. Vector fields 17개는 source RGB/bounds/dimensions를 검증했다. FloatRGBA textures 13개는 원본 inline bulk의 alpha 포함 half bits를 EXR로 보존하고 RGBA 재조립 SHA256 일치를 확인했다. PrecisionTextureExtraction 참조.
- native textures/vector fields/curves/MPC가 저장됐다. Material v2와 mesh/particle stage를 진행한다. CurveLinearColor fixed arrays는 hidden process의 unsaved T3D scratch actor에서 원본 tangent/key를 가져와 curve만 duplicate했다. scratch map/actor는 저장하지 않았다. native material graph는 원본 그래프의 완전 복원이 아니다.
- 실패/해결: ActorX None material-token crash는 작업용 PSKX token만 바꾸어 회피했다(geometry 동일). destination의 double slash를 정규화했다. HDR 자동 cube 오분류는 process-only TextureImporter INI override 및 exact EXR로 교정했다. 다른 작업 Build.bat lock은 child process의 UE_SKIP_UBT_SDK_SETUP=1로 우회했으며 다른 build/editor를 중지하지 않았다.
- 남은 절차: runner import materials → meshes → particles → fresh saved-asset audit → RHI shader/대표 효과 재생 검수. Niagara 21개는 cooked editor graph/GPU HLSL source가 없으므로 native 재생 복원을 완료로 기록하지 않는다. SourceOnlyAssets의 원본 raw/JSON은 모두 보존한다.
- 정확한 재개: Router → Art 최신 상태/이 절 → importer/manifest/report. Python은 UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe. runner는 hidden subprocess/nullrhi, 검수만 --render. 사용자 editor/PIE를 임의 reload/종료하거나 DEBUG RESETLOADERS를 호출하지 않는다.

## 2026-10-06 HeinMach 원작 사진 비교 — 반영 상태·남은 동일성 작업

- 사용자 요청: 원작사진으로 분위기/색/그림자/toon/outline/빛/머테리얼/PP 비교·재현, 눈 과밀 감소, 캐릭터 움직임의 픽셀/할로 원인 분석·수정. [새정본](HEINMACH_REFERENCE_MATCH_2026-10-06.md)과 최신Art상태/Rendering metadata부터 재개한다. 이전 실사 중심 룩 수치는 이번 저장본 범위에서 대체됐다.
- 현재 **메인12package 적용과 native 오류 수정 검수는 완료**, **원작 완전 동일 목표는 미완료**. 새 runtime 코드/BP/Config/애니메이션/StormPass 변경 없음. 변경 asset는 map/PP master/지역 MI6/snow·dust material2/기존 NS/새 EffectType1. UserStart/9,610 actor poses 차이0, main backup11 SHA 통과. QA는 stage 밖에 복사하지 않았다.
- 마지막 검증: hidden **메인** actual standalone saved-game5PNG/error 없음/fallback 없음, fresh saved-scene audit exit0/actor9610/pose delta0/계약 통과. isolated6material realDX12 errors0, controlled run+translation260frames. ParticleReadback flakesXY`.5000117–.7499385cm`/dust`.30000001cm`. DeliveryVerification passed/12package 현재SHA=설치SHA/11backup 확인.
- 같은 camera의 성능3variants/warmup+200GPU samples: LegacySnow8600+2298→Sparse2382+784, sim median`.0164→.0138ms`, sparse ON/OFF translucency 차이`.0446ms`. 동시에 Rider editor 실행/Development1280×720 High/TSR. 전체 frame 약44.4ms라 전체60FPS를 완료 판정하지 않는다.
- 사용자 editor PID27916/world DevMap/dirty map·content0을 읽기만 했다. health/source editor 재시작 PID 변화는 사용자 세션 관측이며 background failure로 혼동하지 않는다. 이번 live 저장/reload/종료/PIE/camera 변경 없음. 이전 DEBUG RESETLOADERS crash 우회법은 계속 금지한다.
- 재현 owner는 `Scripts/Art/heinmach_reference_author.py`의 FIT/TINT/HAZE_EMISSION_MIX/PRIORITY. 기존 weather_look 전체 builder 실행은 새 값을 되돌릴 수 있다. stage `Saved/ArtStaging/HeinMachReference_20261006`: mutable branches 복사, 나머지 SourceAssets/CorrectedSourceAssets 등 main junction이므로 **shared junction asset을 저장하지 않는다**. 현재 main DLL을 fresh game에서 검증했고 stage Binaries는 초기 복사일 수 있다.
- 실패와 수정: API HitResult tuple 가정→to_dict, protected NiagaraEmitterHandles→지원 EffectType scaling, Custom Mask 입력 손실→실제 game DefaultMaterial fallback 확인/reconnect/recompile/save, 잘못된 SceneDepth sky 등식→occlusion 판정, audit pose 자료 list/dict 표현 차이→동일9수치 비교(최종 delta0). 실패 trial을 성공 근거로 사용하지 않는다. 추가1시점 size probe가 당시 main_capture 로그 이름을 덮었으므로5시점은 final/Capture+PNG/성공 tool 결과로 확인하며 새 runner는 별도 prefix다.
- 정확한 다음 절차: Router→새 정본/Delivery/SourceMaterialAnalysis→현재 main/live 상태·새 byte backup/snapshot→주요 rock variant/detail·vertex/cover/foliage의 미복원 consumer 표적 분석→기존 native owner의 작은 보완→hidden fresh audit/realRHI/game 동일 camera 검수→실입력 TSR 남은 현상 검수. original BRDF body/cooked shader library 조사는 아직 안 했으며 원작 shader가 없다고 단정하지 않는다. 원작 동일 build/camera/weather controlled reference도 필요하다.
- 이번 installer의 baseline은 반영 전 상태이며 **재apply하지 않는다**. 다음 수정은 current main에 맞게 stage를 rebase/새 snapshot하고 user changes를 보존한다. source OriginalImporter/brush 재생성/전체 weather 시스템 재생성/옛 Start 복원/legacy 전수조사를 반복하지 않는다. snapshot/사진/render 구조 확인과 원작 완전 동일 판정을 분리한다.

## 2026-10-06 HeinMach 사진 수정 — 마지막 확인

12개 메인 SHA=InstallManifest, map SHA`9da24fa9daffe01aa5a5ed581d3b4ac6466592a92e1638b0c0f8b530d58ea251`. FinalLiveReadonly는 PID27916/DevMap/Idle/dirty map·content0/100%·TSR4·AA quality3이며 live reload 없이 보존했다. 이번 task의 hidden UE는 모두 종료, 다른 CombatEffects commandlet은 유지. BeforeAfter4카메라 차이0(단 OpenSky float readback2e-12). native 수정 반영 완료와 원작 전체 비주얼 동일성의 미완료 상태는 위 절을 따른다.

## 2026-10-06 — DualAxeSword 효과 최종 상태와 재개 계약

- 이전 이 작업의 진행 체크포인트를 대체하는 최신 결과는 [DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md) 마지막 절이다. 원본 시각 2,313/binding 733 raw·JSON/payload 600 추출 실패 0. native 2,028(Cascade 751) 저장·검사 완료, 기타 예상 외 native 0. 분류 루트 `/Game/_Art/Effects`, 원본은 `Saved/Extracted/CombatEffects_20261006`, 지속 metadata는 `Content/_Art/Effects/Metadata/Extraction_20261006`.
- 마지막 검증: DeliveryVerification passed/2,028 native·2,313 source SHA, FreshSavedAssetAudit passed/emitter 4,518/LOD 5,608/MI 522 source override/table 80,874/curve key 117, ShaderVerification passed/109 master errors 0, RepresentativeEffectRendering passed/9 effect/45 PNG. 실제 이미지에서 근접 Guard/JustGuard/Parry와 혈흔·DAS 궤적·눈 입자를 확인했다. 모든 751 전체 수명/게임 전투/원작 동일 검증은 아니다. GPU EmitterInfo 5 protected 필드는 getter readback 미검증.
- 실패/수정: original null Distribution의 native GPU compile crash는 source table 기반 editor distribution으로 해결. text exponent 때문에 Guard 배열 96→93/128→127로 잘린 runtime assertion은 같은 값을 일반 소수 문자열로 재전달해 해결했다. Import_numeric의 curve overwrite 실패는 Import_numericdata completed로 해결했고 source curve/atlas fresh 검사 통과. task-owned byte backup은 BeforeDecimalRepair/기존 49 particle backup에 보존했다. 초기 texture stale MI 참조 3경로는 source 목적지로 재연결 후 referencer0/backup 검증하고 삭제했다.
- **남은 목표**: source-only Niagara 21와 함수 264의 실제 editor shader/graph 복원, 원작 전용 renderer/custom module/VAT/distortion/dissolve, owner/socket parameter/runtime buffer writer, 실제 전투/표면 routing 및 원작 controlled frame 일치. 원본 source가 stripped라 이번 지원 native 이관 단계의 직접 blocker다. 추출 자체를 미완료로 되돌리거나 native 재생 전부 완료로 기록하지 않는다.
- 정확한 재개: Router → Art 최신 상태/이 정본 마지막 절 → Delivery/AssetManifest/SourceOnlyAssets/해당 binding catalog → 사용할 effect 원본만 표적 확인. 완료한 full extractor/importer/numericdata를 재실행하지 않는다. native 사용은 manifest destination, notify/guard/surface 의미는 source entry로 찾는다. 21 source-only의 원본 editor graph/HLSL 확보 또는 metadata·원작 화면 기반의 좁은 재제작/검증이 다음 복원 절차다. gameplay 연결 요청은 실제 current Source/BP·소켓·시간축/취소 계약의 별도 작업이다.
- 후속 수정 전 현재 user 변화/파일 SHA와 새 byte backup을 확인한다. 검수 runner는 UE python + `Scripts/Art/run_combat_effects_background.py audit`, `compile --render`, `preview --render`; marker/report가 통과해야 한다. 이번 task-owned Unreal process 및 native dump session은 종료했고 사용자 editor/PIE/미저장 작업은 조작하지 않았다. live reload/DEBUG RESETLOADERS/Save All을 사용하지 않는다.

## 2026-10-06 — HeinMach 튜토리얼 화로 복원 진행 체크포인트

- 새 요청은 원작 횃불·화톳불·연결 조명/이펙트의 실제 배치다. 전체 HeinMach 플레이 구간을 기본 범위로 진행 중이며 시작 첫 전투 범위 질문은 선택 확인용이다. 원작 cinematic fire 3개와 소화 event-only 파티클은 상시 배치에서 제외한다.
- Source candidate 일반 fire fixture 37/파괴 가능 화로 spawner 35/정적 candle 5. FModel 저장 Level JSON 및 BP/template 상속을 확인했다. dynamic fixture는 source StaticMeshArray의 파괴 전 외형을 사용하며 Chaos/gameplay는 작업 범위 밖이다.
- 추출 root Saved/Extracted/HeinMachTutorialFires_20261006: 시각 closure 284, raw/metadata/payload 추출 실패 0. Cascade 3종/원작 emitter 17개와 editor distribution 273개를 기존 combat importer로 복원했다. native 셰이더는 원작 atlas/parameter 기반 복원이며 cooked 원작 graph의 완전 이관이 아니다. IES 5개는 inline RGBA half의 R 및 원본 256×1/256×256 sample을 LM-63로 계산했다.
- 별도 hidden stage Saved/ArtStaging/HeinMachTutorialFires_20261006. mutable Maps/new TutorialFires asset/metadata만 실제 복사이며 다른 Content는 읽기 전용 junction이다. 기존 main map/9610 actor SHA 및 pose는 Saved/ImportReports/HeinMachTutorialFires_20261006/{StageSetup,BaselineScene}.json. live PID27916 DevMap/dirty0 확인만 했으며 author/save/reload/PIE 제어는 하지 않았다.
- Native import 최종 process exit0/marker, shaders null-RHI exit0/marker 통과. 첫 import는 PSKX 임시 material lookup error exit1이었으나 slot을 source material로 재연결한 저장본을 재로드한 후 exit0. IES 2D 및 payload 뒤 mip dimensions를 고려하지 않은 중간 가정은 수정했다. 최초 place Transform ctor에 Quat를 전달한 오류는 Rotator로 수정했고 현재 place 재실행 중이다.
- 재개: Router → Art 상태 → 이 체크포인트 → Scripts/Art/heinmach_tutorial_fires_{stage,import,shaders,place,compile}.py 및 새 report. UE bundled python으로 stage.py place 결과를 확인하고 compile(real RHI), 새 saved-scene audit, game capture를 구현/실행한다. full extraction/import를 다시 시작하지 않는다. 기존 map pose/PlayerStart/source 89 lights 및 weather/material을 보존해야 한다.
- 아직 main에 적용하지 않았다. 렌더/보존 검증 후 새 byte backup 및 current main hash guard로 map/new asset만 선택 설치하고 main fresh audit/capture한다. 전역 DEBUG RESETLOADERS, live Save All/종료, old reference install script는 사용하지 않는다. 완료 문서와 이 연속성 문서에 최종 상태를 추가한다.

## 2026-10-06 — HeinMach 화로 실제 재생 교정 체크포인트

- 상세 정본은 [HEINMACH_TUTORIAL_FIRES_2026-10-06.md](HEINMACH_TUTORIAL_FIRES_2026-10-06.md). 격리 저장본 9,868 actors(기존9,610 + FX95/light100/fixture35/decal28), 새 native72 packages. source 위치/parameter와 기존 pose/89 lights/PlayerStart 보존 audit 통과, main은 아직 초기 SHA `9da24fa9...58ea251`이다.
- actual game의 inactive95/particle0 원인은 source UE4 emitter DetailModeBitmask7이 UE5 Epic3을 제외한 것이다. UE5 ParticleEmitter::Serialize의 High→Epic migration과 같은7→15를17 emitter에 적용했다. Epic fresh probe95/95 active/180frames 지속 재생 확인. source core Lifetime0·loops1·burst1은 유지한다. ParamModes 고정 배열의 [1]/[2] 누락도 원본대로 교정했다.
- smoke DXT1 두 atlas의 A255/255 때문에 생긴 sprite 사각형은 R density로 교정했고 CaveFire/EscapeFire 실제 사진에서 해소됐다. source burn RGB footprint도 별도 native 식으로 복원했다. EyeAdaptationInverse +기존native gain256 정규화로 EV4 불꽃 과노출을 줄였다. stripped 원작 shader의 직접 복원이 아니다. 현재 마지막 real-RHI compile exit0/errors0이고 변경 후 performance/capture 최종 재검수를 진행한다.
- 최초성능ON/OFF/ON은 background/움직이는AI 차이로 shadow/frame 편차가 커 GPU 절감 수치로 보고하지 않는다. final 성능은 hidden unsaved process의 다른 Pawns/AI만 고정해200warmup+200samples 반복. Character.get_character_movement 미노출 API 오류는 get_component_by_class로 수정했다. failed report를 완료로 해석하지 않는다.
- latest live readonly PID27916/world **StormPass**/dirty maps·content0. 사용자가 맵을 바꿨으므로 DevMap으로 임의 복구하지 않는다. interactive save/reload/PIE/camera/종료 없음. final install은 `heinmach_tutorial_fires_deliver.py prepare→install`의 현재mapSHAguard/검증backup/new72+map만 선택 복사, 이후 stage.py audit --main /capture --main /deliver.py verify. 다른map/native기존asset을 덮어쓰지 않는다. fresh compile/capture/audit가 최신 authoring 뒤 통과했는지 먼저 확인한다.

## 2026-10-06 — HeinMach 눈 파임 격리 개발 진행

현재 정본 HEINMACH_SNOW_DEFORMATION_2026-10-06.md / Engineering HEINMACH_SNOW_IMPLEMENTATION_20261006.md. main map/Source/config는 아직 snow 변경을 적용하지 않았다. work C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan의 Actor2파일+RHI 의존+Nanite CVars, 새 material2/mesh46/field Actor1만 authoring했다. 기존 actor pose 차이0 및 real DX12 shader errors0/PS524,549를 확인했다. 접촉/깊이/이동/대시/weapon/cleanup QA는 아직 진행 중이다.

마지막 검증은 ColdBuild_ExposedSurfaceQA.log Succeeded. own heinmach_snow_stage.py verify mailbox에서 Khazan.Snow.PIE를 실행한다. Ready.json의 최신 PID/UTC를 먼저 확인하고 새 request 이름을 사용한다. mailbox reentry guard 적용본을 사용한다. 첫 QA source DeepSnow255 지점은 바위가 덮고 있어 검증 좌표를 바꾸었으며 바위/CMC/route collision을 deform 대상으로 바꾸지 않았다. 실제 hit 증거 BlockingSurface.json. user editor와 다른 worker는 조작하지 않는다.

재개: Router→두 snow 정본 마지막 절→Saved/ImportReports/HeinMachSnow_20261006의 최신 marker/log→own Ready 확인→native test와 실제 PNG 검수. 테스트 성공 이전에 완료로 표시하지 않는다. 다른 Monster/HeinMachTutorialFires 작업이 끝난 뒤 최신 main map에 눈 component/tag/Actor만 선택 적용하여 이전 snow stage map으로 새 화로를 덮어쓰지 않는다. 현재 user live StormPass 상태를 보존한다. 마지막에는 원작/계산/임시값 구분, collision 한계, 검증 범위와 Notion 기존 template 전체 필드를 기록한다.

## 2026-10-06 — HeinMachTutorialFires 메인 완료 및 후속 맵 보존 계약

- 앞의 이 화로 작업 진행/재생 체크포인트를 대체한다. [화로 정본](HEINMACH_TUTORIAL_FIRES_2026-10-06.md) 마지막 절, `TutorialFires_20261006/DeliveryVerification.passed=true`: task native72+map1 설치/SHA73/원본backup 확인, fresh main audit 및 actual main capture6시점/PNG12 통과, hidden 작업 process 정상 종료.
- 메인 `/Game/Maps/L_HeinMach_Environment`는 작업 저장 시9,868 actors: 기존9,610 보존+FX95/light100/static fixture35/burn decal28. 원작 불꽃 기구72곳, 기존89 lights/PlayerStart 유지. 현재 화로 저장본 SHA `f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442`; 원본mapbackup SHA`9da24fa9...58ea251`. 다른 맵2개 hash 동일.
- source closure284 = native65/reuse70/Engine1/source-only148. 추가 flicker7을 포함한 native72의 Texture2D29/flickerMI6가 실제 파일 집계이며 초기 숫자를 대체한다. 17 emitter의7→15 Epic 호환, source ParamModes28 arrays, smoke A255→R density, normalized EyeAdaptationInverse/burn 식 교정 후 master8 real RHI errors0. 원작 graph/body/Chaos 기능·동일 프레임 룩은 미복원/미검증.
- 최종 local GT Effects ON/OFF/ON median `.3123/.13155/.29275ms`, 추가 관측`.170975ms`. 각200 samples/Development/720p/TSR/동시 user editor. GPU pass 편차로 GPU cost 미확정, 음수 차이를 개선으로 해석하지 않는다. 후속 성능은 현재 main 및 GPU 조건에서 검증한다.
- 최종 read-only live는 **PID27916/DevMap/dirty maps·content0**. 중간 StormPass 관측을 이 마지막 확인이 대체한다. assistant의 live 전환/save/reload/PIE/camera/종료는 없었다. 이후 실제 사용자 world/dirty 상태를 다시 확인하며 문서에 맞춰 강제 전환하지 않는다.
- **snow 등 후속 맵 작업은 이 완료본을 포함한 최신 main으로 rebase하고 자기 actor/component/tag만 선택 적용한다. 이전 snow/reference/fire stage 전체 map을 복사하지 않는다.** 이 installer의 baseline9da와 prepare→install은 완료한 이력이며 재apply하지 않는다. 새 snapshot/byte backup→대상 source key 확인→작은 diff→hidden saved audit/actual game 검사 순서를 따른다. 이후 다른 맵 저장의 SHA 변경은 이 작업 원상복구 근거가 아니다.

## 2026-10-07 — HeinMach 눈 변형 / 낮은 돌 보완 재개 중간 체크포인트

사용자 직접 구현 요청으로 SnowWork 격리 프로젝트를 최신 메인 HeinMach로 갱신했다. 시작 메인 map SHA는 `f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442`, 기존 9,868 actors / fire 258 / PlayerStart 보존이 기준이다. Main Source에는 동시 진행된 Monster 변경이 있어 최신 Source를 재수신했다. 새 눈 Actor/에셋/맵은 **아직 메인 전달 전**이다. 메인의 Monster.cpp만 컴파일을 위한 GameplayAbility include 및 로컬 Role→RoutineRole 보완이 적용됐다(기능 변경 없음). 사용자 PID7220/DevMap은 read-only dirty 0 확인 외 조작하지 않았다.

- `Khazan_SnowWork_20261006/Khazan`: runtime Actor h/cpp 2, dev test 1. 발/무기 + pelvis/spine/limb 실제 pose contact. MOVE_None에서도 몸 접촉 관측, gameplay 상태 사본 없음.
- 46 own terrain clones/2 materials. Nanite source precision 12, full fallback, MaxEdgeLengthFactor 2.0(원작이 아닌 기술 설정)+own collision/nav recook로 기존 Nanite/충돌 높이 약 8 cm 차이를 교정했다. `verify_023155.log`보다 앞선 02:26:18 UTC `Khazan.Snow.PIE` 실제 Success: dent 14.5 cm, compressed depth 799.5 at capture+800, 실제 Player run/dodge/weapon air-negative/ground-positive, 실제 Swordsman 이동/누운 torso, cache/repeat/EndPlay 통과. 원작 shader graph/물리 cm 단위 원본은 미복구, 15/7.5 cm 해석 등 기존 임시 값 상태 유지.
- supported shallow stone dressing 17 component의 Pawn Ignore/nav false/tag HeinMachMicroDressing. 60 cm bounds height/800 cm XY/12 cm exposed bump 임시 선별 기준, 9-point underlying walkable support 검사. 큰 돌/절벽/경로벽/배치 보존. `Resume20261007/MicroDressing.json`. Nav 저장 후 재검증 아직 필요.
- 이전 CPU 측정 `Profile(20261007_111630).csv`: SnowTick 평균 .5019/P95 .8648/max16.2732 ms, 1,059 active samples. 전체 clear/recenter 비용을 줄이는 toroidal GPU tile 갱신을 새로 적용/빌드 성공했다. **최적화 후 PIE/CSV 미완료**, 이 값을 최종 성능으로 표시하지 않는다.
- editor author를 import할 때 unconditional main/quit가 실행된 문제를 `__main__` guard로 수정했다. Authoring report는 0 bindings로 덮인 상태여서 `heinmach_snow_scene_audit.py`가 retained Topology→SHA clone name→saved scene를 검증해 46 bindings를 복구하도록 준비했다. geometry/원래 poses는 변경하지 않았다.
- old pending quit 재생으로 own editor가 즉시 종료됐던 원인을 PID+session UUID 검증/boot 시 이전 pending 요청 무효화로 수정. 현재 own verifier PID8592, Ready.session 존재. 요청은 반드시 `heinmach_snow_request.py`로 fresh Ready 이후 발행한다.

정확한 다음 순서: pending native `Khazan.Snow.PIE`/CSV 결과 확인 → 필요 시 4 Monster family/weapon rig 보강 → SceneFinalAudit/정상 Nav rebuild 대기 및 map 저장 → latest main Source SHA conflict 검사/intake+fresh build → live editor를 건드리지 않는 scoped main 전달/새 background main 검증 → Art/Engineering 정본과 상태에 최종 검증 추가. MainActor class는 현재 Rider editor에 없으므로 기존 live DLL 자동 hot reload/ResetLoaders/종료를 하지 않는다. 원작 동일 프레임 일치는 미검증이다.

## 2026-10-07 — Snow 최종 전달 직전 체크포인트 12:59 KST

- 저장본 SceneFinalAudit 통과: 9,869 actors, 기존 9,868 pose 동일, snow46/material2, micro dressing65, fire258, route wall2,281, NavBounds242/Null26/Links24. Main baseline SHA f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442 그대로다.
- Recast 원작 MoveTo63/points1,485/segments1,422 모두 통과. 표적65개의 Pawn만 제외한다. private 이전 작업의 미기록16개는 main 원본의 응답/nav/tag로 복구했고, 81 component의 8개 노출 표준 collision channel을 원본 대비 저장/reload 검사했다. 프로젝트 custom channel 설정 없음. CollisionChannelsPreserved.json 참조.
- native Khazan.Snow.PIE 최종 Success 2026-10-07 03:57:20 UTC: Player run/dodge, 실제4종 Monster 발/누운 torso/원본 장비 weapon bone vertex, air negative, GPU 깊이14.5cm, Nanite/fallback substrate<1cm, 반복/창 이동 이력/EndPlay material restore. Torso와 장비의 독립 pose fixture이며 실제 gameplay knockdown montage 검증은 아니다. Foot reach12cm 유지; 측정 minToePivotGap=-7.954cm. 회피 fixture는 눈 위 재배치 및 실제 Ability 종료/착지 대기. writer 접촉 판정 자체를 임의 완화하지 않았다.
- Native CPU CSV: baseline warm mean .5019ms/p95 .8648ms; toroidal 최초 cold run .1.7657ms/p95 4.2218/max51.2731, 3개 editor/페이지·skinned asset compile 영향. shipping FPS/GPU 비용 확정으로 쓰지 않는다. 변경 없는 겹친 GPU tile 유지, 새 strip만 upload, full-clear는 공유 zero tile region batch, CPU/GPU48/32MiB budget.
- 별도 Player Original parts/Monster 변경 보존. Main PID7220 DevMap, PIE없음/dirty0를03:58:49 UTC read-only 확인. own PID26584 정상 종료. Main KZAnimInstance.h와 Monster dev test의 최신 변경을 수령해 ColdBuild_LatestMainFinal 진행 중. Main Snow source/assets/map 아직 전달 전이다.
- 재개: 위 cold build Success 확인 → Source snapshot/map hash 변경 없음 확인 → Scripts/Art/heinmach_snow_deliver.py(48native+map+Source3+RHI/Nanite+manifest-selected DLL) → heinmach_snow_launch_main_verify.py로 main 별도 백그라운드 reload/PIE. user 기존 DLL/에디터는 유지하며 새 class 확인은 재시작 필요. 동일 prefix의 HotReload suffix DLL을 추가하지 않는다. MainVerification success 이후 정본/State/continuity에 완료 추가. delivery 도중 lock이면 정확한 pending/backup/hash를 기록하고 user 편집을 덮어쓰지 않는다.
- source shader/HLSL 및 원작 같은 프레임 snow 변형 비교는 미확보. radius/접촉/rim/압축색/roughness/cache는 명시된 native 임시값,15/7.5는 원작 계수의 native cm 해석이다. 원작 cm 실행 직접 검증 또는 픽셀 동일 완료로 기록하지 않는다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

메인 Art 반영/48asset+맵 SHA/기존9,868poses·화로258 및 actual saved reload 통과. 현재 총9,869, Snow46+material2+HM_SnowDeformation. final actual main PIE04:22:07 UTC Success/PNG5 및 NativeGeometry14.5cm. 앞선 전달 전·Dodge 실패 checkpoint는 latest 성공이 대체한다. 정본 HEINMACH_SNOW_DEFORMATION_2026-10-06.md 마지막 절 및 Saved/ImportReports/HeinMachSnow_20261006/FinalVerification20261007.json이 재개 시작점이다.

이 구현 전달에 pending 파일은 없다. 후속 룩 조정은 current /Game/Maps 맵의 snow46/2material/Actor만 대상으로 하며 initial author/deliver/full-map 복사를 반복하지 않는다. 원작 same-camera snow 연속 프레임/shader 실행 식/원본 coefficient 단위가 확보되면 radius/rim/PBR/native15·7.5cm를 재검토한다. 지금 값은 원작 직접 검증·pixel 동일이 아니다. 기존 사용자 editor 변경은 보존했다. runtime/충돌/nav 및 모듈 재개는 Engineering continuity에 분리한다.

## 2026-10-07 — 눈 파임 확대 작업 진행
사용자 후속 지시로 발의 선명한 작은 자국을 넓은 둥근 눌림으로, 무기는 운석 구멍처럼 넓은 파임으로 조정 중이다. private SnowWork에서 foot radius40×32cm/contact20cm, weapon radius100cm/contact24cm를 적용·저장·재로드했고 poses9,869/snow46/micro65/fire258 보존을 검사했다. assistant 선정 native tuning이며 원작 수치가 아니다. 메인 맵/Source는 아직 이전 값이다. Saved/ImportReports/HeinMachSnow_20261006/BroadBrush20261007/{Baseline,SavedSettings}.json이 출처이며 초기 delivery/full author를 재실행하지 않는다. 다음은 private actual contact PIE/PNG/CPU 측정→current main hash/dirty preflight→Source3/map/별도 aliasDLL 선택 전달→background main QA이다. 사용자 editor8292의 dirty content1을 관측했으며 저장/재로드/종료하지 않았다. runtime 수정/정확한 PID 재개는 Engineering continuity를 따른다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

확대 brush main 반영과 saved readback/actual PIE가 완료됐다. 발40×32cm/무기100cm 반경은 assistant 임시값, contact reach는20/24cm. mapSHAb9802151...d1b76b00, 새asset0/poses보존/PP·weather·fire·micro 충돌 변경 없음. latest Art 정본 후속 확대 절과 BroadBrush20261007/FinalVerification.json에서 재개. 초기작은 brush 기록은 이 후속 룩 지시가 대체한다. main 유저 dirty ComboDefinition1 보존, save/reload/quit 없음. 사용자 저장·재시작 후 /Game/Maps/L_HeinMach_Environment Play로 새 property/module을 확인한다. Source/module 절차는 Engineering continuity를 따른다.

## 2026-10-07 — Enemy 용도별 애니메이션 이름·폴더·Root Motion 옵션 정리 착수

HeinMach Humanoids4종(Archer 제외)/Yetuga/ApesStoneHandElite의 저장 AnimationLibrary CSV로676재생 Sequence를 선정했다. 현재 gameplay93과 합친 old→new/provenance/해시는 Metadata/EnemyAnimationOrganization_20261007의 Inventory/RenamePlan/BeforeManifest에 있다. archive 재추출/재임포트는 없다. Art676 분류는 Idle85/Damage233/Attack128/Death18/Guard17/Locomotion159/Alert20/Pose1/Interaction5/Equip5/Prop3/Recovery2다. 목적 prefix와 방향/단계/변형은 남기고 A_EN_PLAY/AC/CA/M/캐릭터명/hash 접두·꼬리를 제거한다. 동일 이름의 원본/Composite는 명시적 유래 suffix로 구분한다.

아직 rename/options mutation 전이다. 별도 MonsterWork27240/Entry에서18대표 root skill audit 완료, 전체 preflight/probe/reference backup/UE rename/fixup/save/reload가 다음이다. Main19684는 HeinMach PIE 중이므로 그대로다. 자동 Input/movement Python이 아니다. Engine AI·공격 튜닝·재추격은 Engineering ARCH-79/continuity에 기록한다. 재개는 해당 metadata부터 시작하며 기존 library 전체 재임포트/다른 region/Archer는 대상이 아니다.


## 2026-10-07 16:42 KST — 두꺼운 눈·깊은 크레이터 진행 checkpoint

사용자가 얕은 눈을 더 높고 깊게 수정하도록 직접 요청했다. 메인 파일은 아직 변경하지 않았다. 최신 main Source/Config 수령 후 private SnowWork에서 DeepSnow60/DeepSnow2 36/기타Snow18/rim12cm, displacement bound75cm(magnitude .75, terrain scale100), FootCompression .7, HeinMach WeaponContactHeight84cm를 저장/reload했다. 모두 어시스턴트 임시 튜닝값이며 원작 단위 확인값이 아니다. 자료는 Saved/ImportReports/HeinMachSnow_20261006/DeepSnow20261007/Baseline.json, SavedSettings.json, Backup. 최대 layer60cm+기존 reach24cm로84cm를 계산한 보수적 접촉 범위이며 실제 GPU snow top collision이 아니다.

첫 GPU 실제값은 foot40.5cm/weapon58cm. QA가 pure DeepSnow60cm라고 가정한 테스트 두 항목만 실패했다(InitialMixedWeightQAFailure.log). 위치에 기존 weight layer가 섞이므로 실제 층 깊이의 .7 압축 비율을 비교하도록 dev test를 정정했다. 압축 바닥의 render-vs-collision<1cm와 actual player/4 monster/장비/공중 억제는 통과했다. 확대 화면에서 bilinear 높이 derivative가 보이는 문제를 normal-only 2texel 중앙차분으로 보완했다. 실제 RHI shaders 600/624 pixel instructions, compile errors0. 원본 D/N/S와 mesh46은 유지.

private18624 정상 종료, 수정된 QA cold build 진행(다른 작업 build mutex 대기). 재개: 그 build Succeeded 확인 → heinmach_snow_stage.py verify로 fresh PID/Ready 확인 → 새 native PIE/PNG 검사 → deep.py stage_passed <PID> → own quit → guarded publish → 별도 background main_verify actual PIE/CPU 검증 → final 기록. user19684 DevMap 및 독립 Monster27240는 건드리지 않는다. old initial/broad delivery helper는 재실행하지 않는다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

이번 checkpoint의 미반영/QA pending은 해소됐다. latest 자료와 source 계약은 해당 snow 정본의 “두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료” 절 및 DeepSnow20261007/FinalVerification.json을 따른다. own 검증 에디터는 정상 종료한다. 사용자 live save/reload/PIE/close는 실행하지 않는다. 실행 중인 editor에서 새 FootCompression 사용에는 사용자 저장·재시작이 필요하다. 후속 크기·높이 변경은 해당 material scalars/level Actor 설정에서 시작하고 original pixel parity/shippingGPU 완료로 확대하지 않는다.


## 2026-10-07 17:13 KST — 깊은 눈 최종 종료 확인

Fresh main15340은 PIE Success 뒤 exit0으로 정상 종료했다. private18624/26860/16088도 exit0, 실패 초기 verifier17840은 위 완료 절의 사유로 own process만 정리했다. 최종 process 목록에 snow editor가 남지 않았고 사용자19684/독립 PlayerParts13904는 보존했다. Rider health disconnected이므로 user live dirty/PIE를 직접 조회했다고 주장하지 않는다. live save/reload/PIE/camera/close 실행0. FinalVerification/ProcessCleanup.json이 최종 완료 증거다. 새 설정 확인에는 사용자가 미저장 작업만 저장하고 editor를 재시작한 뒤 /Game/Maps/L_HeinMach_Environment를 연다.


## 2026-10-07 17:52 KST — Enemy 정리 적용 및 stock 검증 checkpoint

별도 workspace에서 original769(Art676+gameplay93) 시퀀스와 기존 montage33 rename/options 저장, 신규 gameplay44+montage22가 생성돼 최종813시퀀스/55montage다. 12category로 분류했으며 Archer는 제외한다. CurrentAnimationLibrary.csv가 현재 경로, 과거 경로, original package, timeline derivation, frame/FPS/length/RateScale/root/options를 연결한다. 원본 export CSV의 역사적 경로를 현재 경로로 오해하지 않는다.

root bone0/첫 트랙 일치 전부 검증, Root765/Weapon_R1/B_Rock3은 source676+game93 기준이다. root/pose 재작성·Skeleton/Actor scale 변경·retime/reimport 없음. EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame 저장 readback813 passed. 4 NPC ABP는 기존 RootMotionFromMontagesOnly를 유지해 몽타주의 이동을 소비하고 Nav 보행은 기존 CMC/foot placement로 구동한다. 전체 sequence 옵션 활성화와 root-driven Nav 보행 구현을 구분한다.

AssetTools fixup는801옛 경로를 이미 제거한 뒤 catalogue 로딩에서 완료를 못했고 owns16212만 종료했다. debugger는 engine PDB가 없어 GameThread top unknown/지역값 없음으로 원인 미확정; agent breakpoint 모두 제거, 사용자 breakpoint 변경0. 첫 commandlet의 없는 옛 패키지801 에러는 보존했다. 마지막 남은 YetugaRockSmall redirector는 fresh registry refs0 확인 후 정확한2package commandlet로 정상 삭제(0error)했다. 재시작 saved audit의 remaining old packages=[]다. Main 미전달, runtime 검증/선택 전달 후 정본 ENEMY_ANIMATION_ORGANIZATION_20261007.md에 최종 결과를 기록한다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

실제 Main 반영 완료다. Archer 제외 HeinMach Humanoids4종 및 Yetuga/ApesStoneHandElite의 Art676, 기존 gameplay93을 purpose12폴더와 의미 이름으로 정리했다. 신규 gameplay44를 더해 현재813시퀀스, 기존 montage33과 신규22를 더해55montage다. Idle/Locomotion/Attack/Damage/Death/Guard/Alert/Equip/Interaction/Recovery/Prop/Pose이며 방향·단계·변형은 보존한다. A_EN_PLAY/중복 AC·CA·M·EN·Boss·캐릭터 접두사와 hash tail을 제거했다. 겹치는 direct source/Composite는 Original/Composite로 구분한다. CurrentAnimationLibrary.csv가 current→legacy→original source/frame/FPS/length/RateScale/root/options의 조회표다. 과거 export CSV는 historical 원본이며 수정하지 않았다.

813개 EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame을 저장·fresh Main readback했다. 4NPC의 기존 RootMotionFromMontagesOnly로 공격/End 몽타주 root delta를 CMC가 소비한다. Nav 보행은 기존 CMC/velocity pose/Foot Placement를 유지하며 RootMotionFromEverything 보행 구현이라고 부르지 않는다. Yetuga/Apes는 library/options 정리이지 신규 AI 구현이 아니다. index0/first track audit769의 Root765/Weapon_R1/B_Rock3을 유지했다. raw pose19M/곡선·재생률 비교와 compressed extraction tolerance를 구분한다. source pose/root 트랙·Skeleton topology/scale/Player .01·재생속도/재임포트 수정은 없다.

Rename참조 갱신 후 옛802 packages는 fresh registry/commandlet 및 Main hash 확인으로 실제 제거됐다. source assets의 imported actor/catalogue 참조도 갱신했다. 실패 fixup와 QA 로그를 지우지 않았다. Archer177개 hash는 전달 전후 동일하다. Main stock build·813 saved reload/dirty0를 완료했다. 자산별 분류·이름·원본 출처는 ENEMY_ANIMATION_ORGANIZATION_20261007.md 및 Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv를 따른다.

완료이며 pending helper/추가 에셋 전달이 없다. 최종 Main PID3528은 DevMap/PIE없음/dirty0/4BP·ABP UP_TO_DATE다. owned MonsterWork editor는 preview ScreenPercentage87/MotionBlur3와 원래 foreground throttle을 복구하고 정상 종료했다. 초기 실패 로그는 보존한다. 후속은 Router→Architecture ARCH-79 완료→Migration→MONSTER_ATTACK_ROOT_MOTION_20261007.md/Art ENEMY_ANIMATION_ORGANIZATION_20261007.md→CurrentAnimationLibrary.csv 및 실제 Source 순서다. rename/authoring/fixup/copy setup을 재실행하지 않는다. 직접 확인은 열린 Main DevMap에서 Play하고 감지→End→approach/좌우 대치→다양한 공격→거리 이탈 때 기존 행동 완료+.4초 후 재추격을 본다. 원작 AI 확률/모든 지형·연속 포즈/물리 pad/적 피격·네트워크는 미검증 후속이다.

## 2026-10-07 — Contact55 격리 QA 실패·미반영 재개 체크포인트

사용자 지정 눈 최대55cm/발35cm/무기50cm·발 주변5~8cm 조정은 아직 Main에 전달하지 않았다. 작업 프로젝트는 C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan, own editor PID19200/session f217e1163ec84df48c1cfc2805b44502다. 실제 요청/저장본은 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/{RequestedContract,Baseline,SavedSettings}.json과 Scripts/Art/heinmach_snow_contact55.py를 따른다. private material2 Contact55_20261007과 현재 private map만 authoring됐다. 기존 Main Deep material/맵/일반 DLL·사용자 editor는 보존한다.

11:18:25 UTC 실제 Khazan.Snow.PIE는 Fail이다. tiny foot 중앙 CPU 압축fraction 검사는 통과했으나 GPU foot dent0cm, weapon51cm(요청50), observed weighted layer53.5cm였다. foot35cm GPU 표현은 미완료다. substrate normal(.154,-.085,.984)에서 Nanite displacement가 원본 vertex normal 방향으로 움직여 약8.2/−4.5cm XY 차이가 생길 수 있어 tiny brush의 실제 화면 위치/곡면을 점검한다. 이는 실패 원인의 가설이며 확정하지 않았다. Nanite 세분화/카메라 phase 문제와 구분해 real-RHI에서 확인한다. user 요구를 충족했다고 기록하지 않는다.

실패 자료 Saved/ImportReports/HeinMachSnow_20261006/verify.log 및 private Saved/SnowQA/{RuntimeGeometry.json,Snow_FootCompressed.png,Snow_Compressed.png}를 보존한다. 후속은 실패자료 별도 백업→현재 private Contact55 shader/실제 foot 영역 readback→native QA 재빌드·새 PID/session 확인→actual PIE 통과→current Main target/protected SHA와 dirty read-only 검사→선택 전달→fresh main saved readback/PIE다. Main 전달 전 full authoring/prepare/intake를 반복해 현재 own source나 private shader를 덮어쓰지 않는다. source fixture 보완과 실제 실패 수치는 Engineering continuity의 같은 절을 따른다. 최종 성공 전 heinmach_snow_contact55_docs.py는 실행하지 않는다.

## 2026-10-07 — Contact55 Preview 전달·canonical 잠금 대기와 fixture 재검증

11:48:58 UTC publish_unlocked가 성공해 Main Source3/새 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007 및 첫 alias UnrealEditor-KhazanSnowContact55_20261007.dll을 선택 전달했다. 원본 /Game/Maps/L_HeinMach_Environment는 사용자 Main PID3528이 현재 HeinMach/dirty0/PIE없음 상태로 로드해 Windows 잠금이 남아 있다. 사용자 editor의 save/reload/PIE/camera/close는 수행하지 않았다. 원본 canonical map은 baseline 그대로이며 Content 밖 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/PendingCanonical/L_HeinMach_Environment.umap에 검증 후보를 보존했다. Delivery.json의 canonical_map_pending=true다. 아직 canonical 적용 또는 wait_apply worker를 시작하지 않았다.

첫 새 Main Preview PID2492는 정상 종료0이며 native Khazan.Snow.PIE 전체 결과는 Fail이다. foot34cm/weapon50cm와4 Monster gait는 통과했지만 Halberd 누운 torso fixture 한 항목이 실패했다. Source/재질의 눈 파임을 완료된 Main PIE로 기록하지 않는다. fixture는 walking pose pelvis를 배치한 뒤 animation을 계속 재생해 위치가 움직였고, 실제 product body contact 변경 대신 private test case15에 bPauseAnims=true를 추가했다. 기존 merged weapon case17에서도 같은 pause를 사용한다. 격리 후속 cold build는 Succeeded17.98s이며 새 private PID8672에서 현재 재검증 중이다.

최신 근거는 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/{Delivery,PreviewMapSaved,SavedSettings}.json 및 MainPIE 실패 백업/메인 main_verify.log, private verify.log다. 재개는 private8672 결과 확인→새 StagePIEPassed.json 기록/own 정상 종료→Scripts/Art/heinmach_snow_contact55.py update_fixture_module로 test와 새 QA alias만 선택 전달→fresh Main Preview native PIE→finalize의 preview_verified=true/canonical pending 상태 확인이다. 전체 map/material authoring이나 publish_unlocked를 반복하지 않는다. final success=false인 pending 동안 완료 appender는 실행하지 않는다. canonical은 사용자3528 종료 후 apply_pending/wait_apply가 baseline SHA를 다시 검사해 정확한 PendingCanonical blob만 atomic 적용하며 사용자 map SHA가 달라지면 보존·BlockedCanonicalChanged로 중단해야 한다. 실제 canonical Main 새 PIE와 Preview PIE는 분리 기록한다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Main Source3/? Contact55 material2/Preview map/UnrealEditor-KhazanSnowContact55QA_20261007.dll? ?? ????. ?? native PIE ?? ?? /Game/Maps/L_HeinMach_Environment_Contact55_20261007, fresh background Main PID24660, 12:08:02 UTC Khazan.Snow.PIE Success?. GPU ?? ?34.000cm/??50.000cm?? ?? canonical /Game/Maps/L_HeinMach_Environment? ?? ???? ???. ??? Main PID3528? HeinMach/dirty0/PIE???? ??? ???? ?? file lock? ????. ??? save/reload/PIE/camera/close? ???? ???. FinalVerification? success=false/preview_verified=true/canonical_map_pending=true? ??? Preview ??? ????.

?? ?? ??? Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/FinalVerification.json/Delivery.json/PendingApplyStatus.json ? MainPIE.log/MainPreview?. hidden worker2256?12:08:54 UTC wait_apply? ???? ???3528 ??? ????. source/?? ????PIE ????user editor ?? close? ?? ???. ?? PendingApplyStatus.state? ?? WaitingForUserEditorExit?? ??? ?? ?????? ????, WaitingForCanonicalUnlock?? ?? lock? ?? ??? ????. BlockedCanonicalChanged? ??? map? ???? ? baseline/??? ??? ??? ?? ????. known pending canonical? ?? ?? PendingCanonical/L_HeinMach_Environment.umap?? baseline SHA 700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba? ?? ?? atomic ????.

worker? ???? Delivery.canonical_map_pending=false/??SHA, finalize? ?? appender? ????. AppliedVerificationPending?? canonical ??? ?? ?????? ?? copy?? ?? ?? module/normalDLL/Source hash? ??? verification blocker? ????. ?? canonical ? Main PIE? Preview native ??? ?? ????. ?? prepare/publish_unlocked/old alias overwrite? ???? ???. ??? Preview ?? ????? ?? ???? ?? ??? ???. GPU/shipping?actual foot8cm airborne negative? ??? ????.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
최신 정본은 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007의 FinalVerification.json/Delivery.json/PendingApplyStatus.json 및 MainPIE.log/MainPreview다. worker2256은 사용자3528 종료를 기다린다. 현재 WaitingForUserEditorExit이며 기존 Source/asset 재전달·PIE 반복·사용자 강제 close를 하지 않는다. 잠금 반환 뒤 canonical baseline SHA700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba가 같을 때만 known PendingCanonical/L_HeinMach_Environment.umap을 atomic 적용한다. 변경된 사용자 map은 보존·BlockedCanonicalChanged다.

worker 적용 뒤 Delivery.canonical_map_pending=false/적용SHA와 finalize/완료 appender를 확인한다. AppliedVerificationPending이면 파일은 이미 적용됐으므로 다시 copy하지 말고 current module/normalDLL/Source hash·verification blocker를 확인한다. Preview native 성공과 원본 canonical SHA handoff를 분리하며 원본 새 Main PIE는 수행되지 않았다. 초기 prepare/publish_unlocked/기존 alias overwrite를 반복하지 않는다. GPU/shipping·actual foot8cm airborne negative는 미검증 후속이다. 현재는 Preview 검증 성공·원본 적용 대기이며 canonical 완료 기록이 아니다.


<!-- ApesYetugaBehaviorResearch_20261008 -->
## 2026-10-08 — Apes·Yetuga 연구 완료·후속 재개 절차

본 패턴자료분석은완료다. Art정본 APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md→Engineering분석→Metadata/EnemyBehaviorResearch_20261008/{ResearchVerification,CurrentApesYetugaLibrary,ApesOriginalResolvedBranches,YetugaOriginalDefenseRecovery} 및 YetugaOriginal/표적SkillAnalysis·Public manifest를읽는다. 원본237사본/59Apes기초hash·공개27Yetuga/20Apesmanifest·현재212asset의정적검증을완료했다. flat DamageParry충돌은PackageCopies/Index.local_path로해결했고실패기록은보존했다.

추가필요자료는Apes HeinMachEarly2 level498–501, YetugaIntro호출, native단위/default/event/group/취소소비다. 해당원본만표적조회한다. 이미완료한추출/전체library/retime/rename/rootmotion설정을반복하지않는다. 사용자요청은분석이므로이번연구에서게임Source/BP/assets/에디터/PIE를수정하지않았다. 이절은기존Snow대기등다른작업의재개기록을대체하지않는다.


<!-- HeinMachSnow_AttackContact_20261008_complete -->

## 2026-10-08 10:52 KST — Contact55 기본 HeinMach 반영·새 접촉 검증 완료

이전 Preview 성공·canonical 대기를 이번 새 전달로 완료했다. 기본 /Game/Maps/L_HeinMach_Environment는 현재 Contact55 material2와 최대55cm/발35cm/무기50cm·rim 포함 발 반경축8×5cm를 사용한다. material2의 바이너리·D/N/S·source weight/UV·mesh/collision·9868 source poses/fire258/snow46/micro65는 보존했고 맵의 기존 Snow owner에 contact profile2(4.56MiB payload)를 저장했다. 원작 직접 높이로 간주하지 않으며 사용자55/35/50 및 기존 임시36/18/rim12 구분을 유지한다. resource 재추출/새 머테리얼/texture/mesh 작성0.

무기는 기존 실제 Attack Ability 실행 중 지역 눈 표면에 닿을 때만 넓은 crater를 만들며 이동은 작은 발 파임이다. 세부 native 소유/계산/임시 접촉6cm·검증은 Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 이번 절을 따른다. fresh canonical MainPID652 native PIE Success01:45:35 UTC; 새 모듈/저장 profile2/기존 scene/settings 확인과 GPU 발34cm·무기50cm, partial/residual/range/cache/EndPlay 검증을 완료했다. 실제 활성 Player/4NPC Attack pose를 평가 후 고정한 접촉 fixture이며 모든 자연 montage 궤적·원작 pixel parity·GPU/shipping 최악 성능은 미검증이다.

정본 Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/{Delivery,FinalVerification,MainVerification,SurfaceProfiles,SurfaceProfileProof}.json 및 MainVerify.log/StagePIE.log. canonical SHA57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7, 선택 alias UnrealEditor-KhazanSnowWeaponContact20261008.dll. 이전 worker2256을 중지·archive했고 이전 PendingApplyStatus는 SupersededByAttackContact20261008, canonical_pending=false다. 옛 Delivery/Preview FinalVerification/PendingCanonical은 과거 증거로 보존하며 재적용하지 않는다. 사용자 에디터 save/reload/PIE/close는 실행하지 않았다. 마지막 UE 연결/프로세스는 없었고 다음 새 에디터에서 기본 맵을 확인한다.

재개 대기 없음. 다음 Snow 수정은 위 최신 canonical/source/receipt를 기준으로 한다. 이미 반영된55cm·foot contract·기존 pending blob을 다시 적용하지 않는다. 지형 weight/UV/높이/rim 변경 시만 CPU profile을 함께 재작성하고 private fresh audit/native RHI·새 Main QA를 수행한다. 최초 author/원작 전수 추출·기존 locked material/alias 교체를 반복하지 않는다. 접촉/실행 관측은 Engineering, 실제 표면/재질 수치는 Art에 분리 기록한다.



<!-- HeinMachSnow_AttackContact_20261008_normal_rebuild_verified -->
## 2026-10-08 11:01 KST — 후속 일반 Main DLL 빌드도 새 접촉 검증 완료

전달 뒤01:49:41 UTC Main 프로젝트 native build가 새로 실행돼 normal DLL과 manifest가 갱신됐다. 이 빌드는 본 작업이 시작한 것이 아니며 되돌리지 않았다. 최신 전체 Main Source가 본 작업의 검증된 NativeBuildProof와 byte 일치하고 canonical/Source3/기존 보호 asset·Config도 동일함을 확인했다. 현재 manifest는 `UnrealEditor-Khazan.dll`, SHA `4ca0cc527b9d94c6812246befd974e5ce268ec5ece23207add6394d369cde354`다. 앞 절의 alias 선택·원래 DLL 보존은 당시 전달 사실이며 현재 선택 모듈 정본은 이 절이다. 이전 성공 Delivery/FinalVerification을 수정하지 않았다.

새 hidden MainPID19372에서 실제 normal DLL 경로·저장 canonical profile2/55cm·작은 발 범위/scene9,869를 재검증했고01:58:40 UTC `Khazan.Snow.PIE` Success 및 정상 종료했다. Player Run142/Dodge236 표본 maximum35/55, Player/4NPC active 공격 지면 양성/공중·비공격·취소 음성과 기존 GPU 발34/무기50cm/cache/EndPlay 회귀가 통과했다. 자료는 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/NormalMainRebuild_20261008`의 snapshot Delivery(not_a_delivery), MainColdBuild.log, MainVerification/Exit, MainVerify.log다. 이번 Snow 수정·canonical 반영은 완료이고 old worker/preview pending을 재개하지 않는다. 기존 모듈 변경 및 source 보존 절차·원작/mip/normal/자연 fast sweep/GPU/shipping 미검증 범위는 유지한다.

같은 Development Editor/frozen attack scope의 normal DLL SnowTick은 active929 평균0.507301/P95 1.033800/max4.364200ms, `Profile(20261008_105739).csv`다. 이전 .420499ms와 조건이 다른 별도 관측이며 개선율로 비교하지 않는다. 사용자 에디터를 저장/종료/재시작하거나 예전 alias로 manifest를 되돌리지 않았다. 새 에디터에서 기본 HeinMach를 확인한다.


<!-- PlayerAttackVFX_20261008_private_shader_decal_checkpoint -->
## 2026-10-08 — 공격 VFX private shader·Decal 검증 재개 위치

실제 적용 위치는 `C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan`의 private Effects다. Main product Effects·Source·사용자 에디터는 수정하지 않았다. Root의 native notify/실제 combo 작업과 별도인 Art 후보12개(기존 master변경6/신규 dependency6)는 `Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/ArtCandidateManifest.json`에 before/after SHA로 고정했다. 기존 Main native Effects2,028개 hash변경0이다. shader5 compile/save, fresh After30PNG, Decal2 master compile/save 및 source6 dependency author까지 완료했다. 상세 원작 직접값/재구성 경계와 실패 이력은 `DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md`의 마지막 체크포인트와 각각 ShaderRecovery/DecalRecovery의 고유 token 폴더를 읽는다.

최초 After 재진입 crash는 QA Slate helper의 재귀 호출이었다. IN_TICK guard 추가 후 별도 After-only 프로세스는 정상 종료했다. BloodTrail은 조명 없는 PNG로는 보이지 않아 active count만으로 완료 처리하지 않는다. 실제 Decal 바닥의 네모/투명도/curve·mirror 및 밝은 scene의 BloodTrail은 아직 검사 전이다. 소유 process PID16480/17636은 모두 정상 종료했으며 build link를 막고 있지 않다.

재개 순서: Root가 두 번째 private native build 성공을 알린 뒤, Work의 `Scripts/Art/run_player_attack_vfx_decals.py --qa`를 EnginePython으로 실행한다. task token/PID를 Root에 보고하고 끝날 때 정상 exit와 DecalFloorPreview.json을 함께 확인한다. 실제 바닥18PNG와 lit blood3PNG를 눈으로 검사하고 asset save0/12 private hashes/Main0을 확인한다. 그 뒤에만 Root가 실제 Player ability/weapon/HeinMach runtime QA를 수행한다. Main asset CAS 전달은 Root 소유이므로 이 Art helper가 직접 publish/reload하지 않는다. Source expression topology/VAT/원작 scene parity는 검증되지 않은 채 남아 있으며 숫자 근거를 임의로 원작 확인값으로 승격하지 않는다.

## 2026-10-08 추가 — 저장·실제 공격 완료, OverFury alpha 결함 수정 전 미전달

이전 조명 진단은 source 확인으로 대체한다. 원본 FM_blood_trail은 Unlit/Masked이며 FMI_blood_trail_red가 Translucent로 override한다. 회전 QA helper는 Python native MakeRotator 인자 순서 오류로 floor를 보지 못했으며 keyword pitch/yaw/roll로 수정했다. 검은 Floor 이미지의 status=passed는 script completion일 뿐 visual pass가 아니다. 그 실패 이미지·receipt를 보존했다.

private 혈흔 master의 기존 density expression을 OpacityMask와 Opacity 양쪽에 연결한 최소 수정 후 실제 floor QA에서 검은 사각 면이 사라졌다. `DecalFloorQA_50e7f5e33f71411eb3785da5645f3c47`의21decal/3blood 이미지와 실제 color/curve/mirror를 제한적으로 검사했다. source Blood red(.5,0,0), Crack MI black(0,0,0,.5)을 보존했다. density/원본 shader topology·native curve time 해석·원작 화면 강도 일치는 미검증이다.

347window/694child의 저장 재로드와 기존 native input trigger precision이 `SavedAssetAudit.json`으로 통과했다. 실제18공격 및 적중 혈흔 native PIE도 Success다. 그러나 최신 `RuntimePIE/121_AM_DAS_Player_OverFury_OverFury.png`에서 다른 slash/dust master의 검은 면이 발견되어 전체 visual pass/제품 전달은 보류하고 바로 수정 중이다. Root가 `MainDelivery` 후보를 `MainDelivery_BeforeOverFuryAlphaFix`에 보존했으며 Main Source/Content에는 아직 적용하지 않았다.

재개는 해당 frame의 실제 source particle/material dependency를 표적 확인하고 parent Masked/child Translucent의 alpha 연결을 필요한 master에만 보완하는 순서다. 실제 공격 화면의 검은 면이 제거된 새 proof를 얻은 뒤 후보 SHA/제한적 review를 갱신하고 Root가 선택 CAS 전달·fresh Main 검증을 한다. 이전 Floor proof만으로 전체 공격 룩 완료를 기록하지 않는다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

소진·브루탈 표적 분석/클립 선택 작업은 Main 적용·fresh saved reload까지 완료다. 다른 VFX task의 미완료 checkpoint와 별개다. 원본 분석 재개가 필요하면 MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md → 저장 TargetedFindings/StatusAndHoldingSupplement → AnimationPlan의 정확 package/field/hash 순으로 확인한다. 원작 natural recovery의 인간형 positive value와 강적 Fortitude 차이를 전체 동일 native 규칙으로 합치지 않는다.

재사용 author 증거는 Metadata/MonsterStamina_20261008/Authoring.json의47clip raw bone/rate/root/keys 비교와 skeleton2reference preservation, BodiesAuthoring.json idle2/기존 body audit, MainSavedReload.json 저장49clip/20montage다. 클립 retime/root repair/전체 재추출을 반복하지 않는다. 실제 접촉 pose·원작 scale modifier·cinematic Execution가 후속 Art 범위이며 조정 전 기존 payload와 metadata 근거를 보존한다.


<!-- PlayerAttackVFX_20261008_context_opacity_private_checkpoint -->
## 2026-10-08 — 실제 OverFury 불투명 면·먼지 네모 후속 private 수정

초기 standalone 검사는 원작 일치나 실제 공격 화면의 최종 통과가 아니었다. Root의 실제 native 공격18 node 검사가 실행·적중 조건을 통과한 뒤, `RuntimePIE/121_AM_DAS_Player_OverFury_OverFury.png`의 몽타주 약1.01초 화면에서 큰 검은 곡면과 불투명 먼지 네모를 발견했다. 따라서 이전 Art 후보12의 `passed_private_art_QA`는 제한된 floor/standalone 범위의 과거 기록이며 최종 전달 근거로 사용하지 않는다.

Source masked child와 translucent parent의 서로 다른 출력 계약을 native graph에서 확인했다. `FM_meshoffset_A`, `FM_fluid_A`, `FM_World_Fluid_A`에는 이미 존재하는 opacity density를 `OpacityMask`에도 연결했다. 앞의 두 master의 masked 경로는 scene depth를 읽는 translucent 전용 `DepthFade` 앞의 동일 density를 사용하며, 원래 translucent fade는 유지했다. Parent/child blend와 clip, source numeric parameter는 변경하지 않았다. 첫 Cmd PID29888은 세 파일을 저장한 뒤 WorldSubUV atlas 개수 guard에서 exit1이었으며, 저장된 세 파일과 실패 이력을 보존했다.

`FM_World_SubUV_color_A`, `FM_SubUV_color_A`의 native opacity dependency에는 `Tex_Opa`만 있었고 실제 grayscale 연기 모양인 `Tex_SubUV`는 빠져 있었다. Source texture payload의 alpha는255로 일정하고 RGB는 변한다. 기존 opacity/particle alpha/source strength를 유지한 채 atlas R density를 곱하고, 실제 `Tex_SubUV`에 연결된 기존 atlas Custom의 Age 입력을 원작 Cascade DynamicParameter0 `SubUV_frame`로 바꿨다. Source master grid default6×6과 현재 child override9×9/8×8은 변경하지 않았다. 정확한 cooked graph와 프레임 간 보간 topology는 미확보이며, 이 연결은 원작 직접 graph 복원값이 아닌 native 재구성이다. WorldSubUV에는 atlas Custom이 두 개 있어 단일 node 개수 가정은 틀렸고 실제 texture 연결로 대상을 찾았다. 두 번째 guard 실패 PID14780은 저장0이며, 수정한 author PID22508/token76b73dd839a642c68364b3f87a54aa00은 exit0으로 세 target 저장을 완료했다.

같은 run에서 `Base_Particle`의 실제 native opacity texture 출력은 이미 R임을 확인했다. importer 코드에서 A를 예상한 것은 실제 native 상태와 달랐다. 따라서 이 parent의 alpha 교체를 새 실제 bug 원인이라고 주장하지 않는다. 추가 저장은 alternate Mask pin뿐이고 현재 `FM_Particle_Zero` source child는 Translucent다. 이 불필요 후보의 guarded restore와 최종15/16 범위는 Root와 조정 중이다.

`ResourceAudit/ContextShaderAuthorSummary.json`에 저장된6 target의 before/after SHA, source package/JSON SHA, native graph 관측, author process와 log를 보존한다. 각 target recompile/save에서 오류는 없었고 log의 material/shader compile 실패0이지만, 그 사실만으로 실제 child render가 통과했다고 판단하지 않는다. `ArtCandidateManifest.json`은 현재 후보16(기존10/신규6)의 hash 일치와 Main Effects2,028개 변경0을 확인한 `waiting_actual_overfury_visual_QA` 상태다. 모든 own editor는 종료했으며 Main Source/Effects/사용자 editor에는 수정·저장·reload를 하지 않았다. 다음 단계는 Root의 fresh native 실제 공격 RHI에서 OverFury 약1.01초와 먼지 field의 투명 외곽을 직접 확인한 뒤 guarded 최종 후보를 확정하는 것이다.


<!-- PlayerAttackVFX_20261008_context_scope15 -->
## 2026-10-08 — 불필요 Base_Particle 변경 제외·최종 Art 후보15 대기

Root 결정에 따라 private `Base_Particle` 한 파일만 guarded restore했다. 현재 after SHA `3a361b8a7bcfed84f0785a38a1e898cae7196f87e89983476d22f5cf83431b98`, 보존 backup SHA 및 Main 원본 SHA `1f96ac08825d7eea1342a4a44b8e74789808724e7497984e24b132bd2d7cdf9f`를 확인하고 backup의 정확한 bytes를 복구했다. 실제 native opacity는 이미 R였고, 현재 Translucent consumer에 쓰이지 않는 추가 Mask 출력만 제거한 것이다. 다른 private asset이나 Main 파일은 복구·수정하지 않았다.

`ResourceAudit/BaseParticleUnusedMaskRestore.json`에 단일 복구 증거, `ArtCandidateManifest_Context16BeforeBaseRestore.json`에 직전16 후보를 보존했다. 현재 `ArtCandidateManifest.json`은 실제 필요한15개(기존9/신규6)이며 private expected SHA 모두 일치, Main Effects2,028개 변경0이다. 과거 targeted6 save proof는 보존하고 실제 retained target5와 복구 사실을 구분한다. 상태는 `waiting_actual_overfury_visual_QA`로 유지하며 다음 단계는 Root가 fresh native RHI 실제 OverFury 약1.01초와 smoke field 투명 외곽을 확인하는 것이다. 이 checkpoint는 Main 전달·최종 원작 시각 일치 완료를 뜻하지 않는다.


<!-- PlayerAttackVFX_20261008_atlas_uv_child_RHI -->
## 2026-10-08 — WorldSubUV 체크무늬 fallback 원인·저장 자식9 SM6 재검증

새 실제 OverFury 화면의 큰 회색 체크무늬는 성공한 parent compile/save의 증거와 양립하지 않는 실제 Art 실패다. `RuntimePIE/PrivatePIE.log`의 master `FM_World_SubUV_color_A` 및 Masked child `FMI_World_SubUV_color_A_01`은 PCD3D_SM6에서 Custom input1(UV) 누락으로 컴파일에 실패해 Default Material을 사용했다. 다른 distinct material compile/fallback 실패는 해당 로그에 없었다. 실패 log/Driver/121·123 PNG를 `ResourceAudit/AtlasUVFailureEvidence`에 SHA와 함께 별도 보존했다.

실제 native readback에서 현재 `Tex_SubUV`에 연결된 Custom_0의 UV만 null이었고 Age는 현재 source DP0, Columns/Rows는 기존 scalar nodes에 연결돼 있었다. 동일 master의 다른 atlas Custom_1은 모든 입력이 유효했다. 기존 TextureCoordinate_1의 출력을 Custom_0.UV에 연결하는 한 입력만 복구했다. 파라미터/texture/MI override/geometry/scale/DP curves/atlas 수식·숫자는 변경하지 않았다. 새 private SHA는 `93814b114851baa1cd508b76ebdbade1589e12be23ccd62ab1435e8eb3b6c1d2`다. Context15 범위와 원본 Base_Particle 복구 상태는 유지한다.

첫 UV 검사 PID15592는 RHI 통계를 엄격히 요구했지만 commandlet이 `-AllowCommandletRendering` 없이 실행되어 statistics가 모두0이었다. guard가 저장 전에 중단했으므로 save0이며 이를 컴파일 성공으로 기록하지 않는다. 과거 commandlet의 `recompile_material` errors0만으로 실제 child permutation이 정상이라고 한정하지 않는 이유다. Engine `MaterialEditingLibrary.cpp`의 RecompileMaterial은 현재 resource가 없으면 빈 errors를 반환하고, GetStatistics는 실제 resource에 대해 SubmitCompileJobs/FinishCompilation을 수행한다.

명시적 `-AllowCommandletRendering`을 추가한 private Cmd PID31884/tokenb10d2a6752c24fd19c6af3b41978641c은 28.468초/exit0으로 한 master만 저장했다. 실제 SM6 master PS178/VS344, Masked child01 PS108/VS153, 나머지 referenced child8개 PS178/VS344 instruction을 강제 컴파일 후 확인했다. Source child01은 FT_leaf_01(그리드5×1, alpha255/RGB변화), Masked/TwoSided/Unlit·clip.05이며 Grass source particle13개에서 FS_Leaf_01 TypeDataMesh와 bOverrideMaterial=true로 Required MI를 사용한다. Source smoke child07/03의 grid9×9와 다른 source override는 보존했다. Author log의 수정 전 load 실패는 그대로 남겨 실패 이력을 숨기지 않았다.

새 저장 상태를 별도 read-only RHI PID27776/token38bc8af4d646420cb7d7a7f3581ae514에서 다시 로드했다. 9.797초/exit0, package save0, master와 referenced child9의 positive PS/VS instruction, Failed-to-compile/Default-Material/ShaderCompiler-error log line0을 확인했다. Main `AtlasUVFix_b10...` 및 `AtlasUVFreshVerify_38bc...`에 전체 receipt/log/tools를 보존했다. Child9 바이너리와 Main Effects2,028개 SHA는 모두 불변이다. 후보15(기존9/신규6) manifest는 새 WorldSubUV SHA를 반영했고 `waiting_actual_overfury_visual_QA`를 유지한다. 모든 own editor는 정상 종료했으며 Root의 다음 native build를 막지 않는다. 최종 다음 절차는 Root의 새 Source/Brutal montage author 뒤 실제 공격8 montage RHI에서 fallback log0 및 OverFury 약1.01초 화면을 직접 확인하는 것이다. 이 isolated compile 검사를 실제 공격 시각 통과나 원작 pixel parity로 승격하지 않는다.

<!-- PlayerAttackVFX_20261008_MainComplete_1911 -->
## 2026-10-08 19:11 KST — 공격 VFX Main 완료·새 native schema 로드 절차

직전 private15/UV/실제 OverFury 대기 상태는 완료된 Main 전달과 fresh Main 검증으로 대체됐다. 현재 정본은 [PLAYER_ATTACK_VFX_PLAYBACK_20261008.md](PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 같은 날짜 최종 절과 `Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json`의 `MainDeliveredAndFreshVerified`다. 선택34파일/23패키지, 몽타주8·401구간(Particle345/Decal56), Art15(기존9/신규6)가 반영됐고 새 Main RHI의 공격18/Brutal5·176캡처·material fallback0·저장0/exit0 및 별도 Main 저장본8,308 field 대조를 완료했다. 추가 Brutal Snow4와 기존 Snow65/Water20은 unsupported source 구간으로 보존했다.

현재 선택 모듈은 `UnrealEditor-KhazanPlayerAttackVFX20261008.dll`, SHA `ece6db2ebaaaa98fbbd0235553bba1691d5e520a12a563410aad2ee082032a99`다. 모든 task 검사 editor는 정상 종료했고 사용자 PID16572는 DevMap/PIE없음/dirty0으로 남겼다. 사용자 저장·reload·종료는 하지 않았다. 사용자가 새 native notify schema를 이용할 때는 현재 작업을 보존한 뒤 일반 에디터 재시작으로 현재 프로젝트의 선택 모듈을 로드한다. Live Coding/native schema reload, 옛 alias 재선택, 과거 author/delivery/전체 추출 재실행을 하지 않는다. 다음 새 요청은 Router→Art state→위 playback 최종 절→FinalVerification→필요한 source package/현재 asset 순으로 시작한다.

고정 ArtCandidateManifest의 초기 pending/Main변경0 필드는 과거 snapshot이다. 이를 수정하거나 검증 helper를 다시 실행해 현재 전달 상태를 덮지 말고 FinalVerification의 `frozen_manifest_supersession`을 읽는다. RootVisualReview의 제한된 실제 strand/투명 smoke·fallback 부재가 최종 시각 근거이며 원작 전체 pixel parity와401개 모두의 화면 가시성, cooked shader topology/VAT, 전체 HeinMach/StormPass 및 shipping GPU 성능은 미검증으로 남는다. 실패 log/PNG/guard/backup은 보존돼 있다.

## 2026-10-08 20:20 KST — Monster6 VFX 원본·리소스·시각 작업 착수

요청은 여섯 몬스터의 모든 행동/공격 이펙트 정리·부착·타이밍·품질 보완이다. 원본 clip metadata는 기존 currentlibrary/SourceMetadata.zip에 존재하므로 재추출하지 않는다. 추가 particle/material/texture/mesh/vectorfield 의존성만 표적 추출하고 Metadata/MonsterVFX_20261008에 정확한 package/export/field/raw값/SHA 및 Source→Current 시간식을 저장한다. runtime 계약은 Engineering ARCH-84를 참조하며 Art 문서에 중복하지 않는다.

별도 MonsterVFXWork의 Effects·6family Art/GamePlay 폴더만 writable이다. Main baseline/선택 전달 증거는 Saved/ImportReports/MonsterVFX_20261008에 남긴다. 원본 cooked Niagara/MaterialFunction/shader graph가 없으면 적법한 source 기반 렌더 adapter와 원작 직접 확인을 구분한다. 원본이 없는 픽셀 일치·boss 자율AI 완료로 표현하지 않는다. 다음은 delta native import→소켓/조건/재생시간 author→실제6family RHI 시각/정리 검사→fresh saved audit→Main CAS 선택 전달이며 아직 적용/검증 완료가 아니다.
<!-- PlayerAttackVFXPolish_20261008_Checkpoint_2104 -->
## 2026-10-08 21:04 KST — 공격 VFX 사각형·방향·내려찍기·혈흔 재검토 진행

사용자가 이전 VFX의 사각형 노출, 공격과 다른 슬래시 방향, 부자연스러운 바닥 효과와 혈흔 증량을 직접 수정 요청했다. 기존 19:11 완료 기록은 당시 제한된 캡처 검증이며 전체 비주얼 일치를 의미하지 않는다. Router→Art/Engineering 관련 정본·continuity→저장 metadata 및 현재 Source를 읽었고, 기존 `Khazan_AttackVFXWork_20261008/Khazan`의 writable Effects만 사용한다. 새 증거는 `Saved/ImportReports/PlayerAttackVFXPolish_20261008`에 분리한다. 이전 `PlayerAttackVFX_20261008` author/delivery/8 montage·401 window/보고서를 덮어쓰지 않는다. Main 제품 변경은 아직 없다.

Private 혈흔4는 FM_MeshDecal의 instance/particle 공간 투영과 테두리 마스크, Base_DefaltParticle_Masked의 grayscale 밀도 및 원본 direct ParticleColor emissive 연결을 보완했다. Source cooked graph 부재에 따른 복원 adapter이며 원작 셰이더 완전 일치가 아니다. DP InObjectUnitSize34–36의 단위를 cm로 직접 확인했다는 이전 해석은 철회한다. FT_Bsse_Particle 원본 PNG alpha가 항상1이라는 이전 해석도 철회한다. 최종 원본 PNG/graph 경계는 `Blood/BloodVisualReview_Final.json`, 정확4개 SHA/backup은 `Blood/BloodCandidateManifest_Final.json`을 따른다. Trail UnitScalar80→40cm 및 Sub burst22→44는 사용자의 증량 요청에 따른 어시스턴트 임시 튜닝으로 밀도/수량2배이며 원작 값이 아니다. 최종 Blood After3 실제 RHI12장에서는 검정 상자·사각 바닥 자국 제거를 직접 확인했다. 실제 공격 중 혈흔의 최종 가시성·GPU 비용은 아직 별도 확인이 필요하다.

WorldSubUV master의 색/밀도 프레임 불일치와 원본 child05/06/Breath/Breath1의 명시적 Opa_SubUV_Switch override 누락을 복원했다. 회전 원본/native24개 비교는 단위 일치이며 임의 전역 yaw/각도 변경 근거가 없다. DefaultParticle 기본 그래프가 사각형의 직접 원인이라는 초기 판단은 해당 실제 emitter가 ERM_LightsOnly인 것을 확인해 철회했고 이 에셋은 수정하지 않는다. GroundIsolation의 smoke_1(04/07)에서 검은 polygon cloud를 여전히 재현했다. 누락된 DP2 소멸·DepthFade/밀도 경로와 녹색 바닥 면의 실제 producer를 좁혀 보완 중이다. 이5개 manifest는 시각 완료 전 후보 상태다.

정확 재개: 새 report의 Before01/After01 Driver 및 TransformObservations, GroundIsolation/WorldAtlasCandidateManifest, Blood 최종 manifest/review를 먼저 읽는다. Ground 담당 agent의 수정·새 isolation QA를 확인하고 원본 correction 첫 snapshot과 실제 무기 자세의 방향 계약을 조사한다. 후보 고정 후 새 실제 RHI 전후 full SHA, fresh saved Art 및 unchanged8 montage/401구간 감사→Root visual review→FrozenCandidateManifest→새 polish delivery helper로 선택 전달→fresh Main 확인 순서다. 사용자 에디터를 종료/저장/재시작하지 않는다. Main19:48 BrutalHPDamage50과 진행 중 별도 Monster VFX 작업을 보존하며 새로운 Main 변경은 CAS 충돌로 중단하고 합친다.


## 2026-10-08 21:43 KST ? Monster6 VFX ?? ????? ?? ??

private Resources? ImportReport/FinalResourceAudit? ???passed?? ??457??, ??2028??? byte ??, import failure/missing0??. NativeAdapterMap47 ? GPU Decal richcurve7? ???? ?? JSON2805/payload1440 SHA? ????. ?? ??? Metadata/MonsterVFX_20261008/{HumanOriginal,ApesYetugaOriginal}; asset ?????? ???? ???. ??? ??? ??/??/adapter ??? MONSTER_VFX_PLAYBACK_20261008.md? Engineering ??? ??.

?? private stockBuild6 exit0/40.812s?? author ??? ??? notify ???montage section getter? ??? ? probe/author? ????. ? author? ??? ?? ?? ???? journal? disk_changed=false?. Main Source/Content/native ?? ? ?? RHI ?? ??? ?? ??. ?? ??? Effects polish/CombatReaction ??? CAS? ????.

??? AuthorApiProbe/PrivateAuthoring journal?? saved readback?6?? actualRHI? ???? ???PNG ?? ??/VisualQA?NativeCandidateIntegrity?guarded MainDelivery ??/???fresh Main saved/RHI??????? ???. ?? ?? cooked shader/NI graph, ??10+1 source fallback, correction bone ??52, camera/snow/status context, Prop3 ? boss autonomousAI ??? ????. ?? editor? ???? ??? ???? ?? ?? process? ????.

## 2026-10-08 22:31 KST — Monster6 실제 화면 검증 보완 중

private resources457/재사용2028 보존, author487/visual2855/sentinel487과 fresh saved 검사는 통과했다. 첫 실제 RHI Attempt2는 native material consumer6건 및 M_MonsterLightOnly ParticleSprites usage 누락으로 실패했다. root가 인간 공격 PNG에서 source dust/weapon arc를 직접 확인했지만 아직 최종 품질 완료로 기록하지 않는다. Apes/Yetuga/처형/사망 화면까지 확보하도록 QA capture 상한900→2400으로만 변경했다(gameplay 수치 아님).

M_MonsterLightOnly task-owned master1의 usage를 표적 수정해 새 LightUsageRevision을 기존 ExecutionRadiusRevision→현재457 manifest/audit와 연결한다. adapter identity47/source payload/기존 reused Effects는 변경하지 않는다. Apes material 실제 consumer 문제는 Engineering에서 원인을 조사 중이다. 다음 재개는 LightUsageRevision passed 및 수정 build → fresh private RHI와 player regression → root PNG 실제 검토 → guarded Main 전달 → fresh Main 저장/RHI 검사 순서다. Main 제품은 아직 미반영이며 기존 Attempt2 실패 report를 보존한다.


<!-- PlayerAttackVFXPolish_Resume_20261010_SpearOpacityCandidate -->
## 2026-10-10 ? ?? ?? ???Spear ?? ??? ?? ?? ?? ??

??? ?? VFX ???? ?? Main ?? ??? ???. ?? ?? ?? ??? `Saved/ImportReports/PlayerAttackVFXPolish_20261008/Resume_20261010/ArtCandidateIntake.json`??. ?? World6/Blood4/Recovery2? private ?? SHA 12?? ?? JSON SHA? ?? ?? ?? manifest? ??, Main ??12 ? Spear1? ?? bytes? ????. ??8???/401??? ?? author/retime/???? ???. Engineering? ???Notify ????? ??? ?? runtime ??? continuity? ???.

??? ??? Spear shader author?. `SpearAuthor/9977a3fb...` PID632? DP ?? ??, `ac7fcbfab...` PID25692? Saturate ?? ???? ???? ? ? ??0/exit1???. `3ea5d959...` PID22256? Process.json? running?? ?? ?? SpearAuthor.json/exit receipt? ???? ???? ??0?? ???? ???. ?? ??/??? receipt? ????. Root? ? `976250df...` PID28068? parent1 ???parent/child2 ?? SM6 PS166/VS344/sampler6?58.968?/exit0? ???? ? private SHA4a163853...? ??. ? ??? compile ???? ?????? ??? ???.

`SpearCurveChannelAudit.json`? ?? FC01?04? ?? RGBA keys?Normal/_06? ?? override?PS DynamicParams/Lifetime/??Engine ? native Atlas T3D? ?? ????. FA01?04? ?? serialized Source?4096?1/TSF_RGBA16F?? ??? GradientCurves ?? ??? ???. Normal? HighLight_Pow? parent50 ?? ??1, Main03/Highlight04?? _06? Main01/Highlight02? parent50? ????. ?? curve alpha?? ?? ?? ??. UV ??Offset ??? Highlight alpha? opacity ?? cooked ?? wiring ??? ?? adapter?. ?? isolated capture? .03/.15?? ??? ??age.4/.6647??? source lifetime.5?? ???? ???. ??/PNG hash ??? Root ? ?? ??? ??? ? ???? ????.

Root ???? ?? Spear parent? opacity ? ? ??? MainA?boundedParticleAlpha? ???? HighlightAlpha? radiance?? ???. ? ??? ??/??/MI?PS?life?size????? ?? ??? ??. `Resume_20261010/SpearOpacityAuthor/b72e2808...` PID16544? ??1?private ??? Effects2033 ???Main Spear baselinecbbfb22... ???SM6 parent/child2 ??,50.515?/exit0??. ?? private parent SHA?75833c9bff85c9233255cde90de62a73b013ef5d8a0b99b7d88b53dab95785b2?. ? ? ??? ?? ?? ?? ?? QA ???.

?? ?? `RecoveryFluidProjectionAudit.json`? Fluid222 native package? ????. Main/private ??219, ??? ?? Recovery2? World? FM_meshoffset_A1??? ??? child216? ?? SHA? ????. Recovery Custom?? SceneDepth/SceneColor/WorldPosition ??? ?? ?? ellipse/PixelDepth?? opacity? ???. ?? ?? Tex_Emi RGB? particle tint ?? ? ?? producer? ???? ?? Front2?? ???? ??? ?? ?? ?? ? ????? debug collision ?? ?? material? ???? ???. Root? producer ??? ?? ???.

?? ??: ? ? opacity author SHA/exit? ?? `Resume_20261010/SpearOpacityPreview/6b9195f39df74ee0bccfa43951f86598`? hidden PID29176 ??? ????. warm source PSC? ?? ? ???? ? ?? unchanged source PSC? ?? ?? age?? ???? ??0??. ??? ??/?? ?? ?? ??? ???? ?? ??? ?? retained final SHA? ?? revision manifest? ????. ?? `SpearCandidateManifest_Final.json` ? `FrozenAdditionalRows_Proposal.json`? ??4a163 ??? ???? ???? ??75833 ??? ?? ???? ???. Root? ??13 ?? ???? positive SM6 saved13/unchanged8?401 ????? ??18/Brutal5?green producer/Root ?? ???CAS ?? ???? Main runtime?saved?visual ?? ??? ????. ??? ???? ??/???/??? Main ?? ????? ?? ???.


## 2026-10-10 ? Spear early preview ???Root ?? ?? ??

?? ? PID29176 ?? checkpoint? ?? ?? ??? ????. actualRHI38.047?/exit0?package save0/current75833 hash ??, ??age.03333? ? crescent slash? ??? ?? ? ?? ??? band? ?? ? ????? ??? ???. late .40681?? ?? geometry ? ??? ? floor tail ?? ??? `Resume_20261010/SpearOpacityVisualReview.json`? ???. ?? ??? UE? ??. `SpearCandidateManifest_OpacityRevision_20261010.json` ? `FrozenAdditionalRows_OpacityRevision_Proposal.json`? Root? ???? ??4a163 manifest/??? ????. ??? Root? current75833 ??18+Brutal5??? ? producer ??/???saved13/8?401?CAS Main/fresh Main ???? ?? Main ??? ???.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — CombatReaction Main 완료 후 Art 재개 기준

기존 중단 작업을 완료했다. 이미 저장된 plan/report만 사용해 runtime 검증·stock build·Main130 asset 선택 전달·새 Main saved readback을 수행했고 원본 재추출/재임포트/retime/root repair를 하지 않았다. [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)은 MainDeliveredAndFreshVerified이며 새 Work29152/Main16544 각각654,552검사/실패0/필수 미지원0/dirty0·정상 종료가 기록돼 있다. 사용자/별도 작업 editor를 제어하지 않았다.

다음 조회는 Router→Art state→[피격 Art 감사](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 완료 절→저장 분류/plan/readback→필요한 정확 source asset 순이다. author/helper/prepare/publish를 반복하지 않는다. 원본245/raw24/재생률/root 보존, Loop crop16 임시0.3초, Heavy Short fallback/giant dedicated fallback, QuickStand4 미연결 및 unsupported11 occurrence를 현재 계약으로 읽는다. 추가 수정은 새 현재 Main baseline을 확인한 뒤 표적 자산만 다루며 runtime 계약은 Engineering ARCH-85를 따른다. 별도 MonsterVFX 진행은 그 continuity 절의 상태를 유지한다.


<!-- MonsterVFX_ApesGrapple_Rim_PrivateCheckpoint_20261010 -->
## 2026-10-10 20:11 KST — MonsterVFX source-correct paired QA와 Rim 추가 시각 검사 중

private Source9runtime+DEV2, Sequence487/State3342/Death6 및 Art 후보457을 유지한다. Apes MaterialOverrides의 원작 V3행을 보존하고 현재 NONV3 alias5행을 State5/Sequence2에만 추가했다. Applied passed, 나머지497 author 파일·original Main-before journal499·schema58d4696c…6cf 불변, fresh SavedReadback4 passed다. 기존487 author/추출/import를 다시 실행하지 않는다.

PrivateMonsterRHI3는 editor exit0이지만 native/Driver failed였다. assertion20은 paired replacement/value 기대뿐이며, 실제 Apes Grapple 앞/뒤01/02와 InGame 사본에는 각각 Particle4/material0이다. FinalBlow3+Die_F2의 material State를 현재 paired Grapple의 producer로 오인하지 않는다. ordinary Death Execution800/consumer5는 별도 실제 관측이고, producer가 없는 paired terminal execution retention은 미검증이다. 그 기대에 맞추기 위한 새 dissolve/게임 코드 추가는 없다.

PrivateRimQA/Attempt2는 실제 BP EnemyWeapon_R와 source WeaponV2 compatible skeleton에서 overlay 생성·weight fade·baseline 복원 통과, package save0/asset mutation0/fallback0/20captures를 기록했다. 역광 PNG에서 root가 시각 강도를 아직 확정하지 못해 추가 QA 중이다. actual data/cleanup pass를 visual pass로 승격하지 않는다. 자료는 `Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt2`다.

현재 Build13 passed16.422s/DLL29bd3daf…a9b, 보완은 실제 source paired QA만이며 PrivateMonsterRuntimePIE/Attempt4(PID25160)가 실행 중이다. 정확 재개: 현재 Attempt4 native/Driver/Exit 확인 → 필요 실패만 보완/검증 → 별도 Player 회귀 → Rim 및 전체 PNG root 검토 → 현재 plan/author499/Art457/최신 source/build/actual DLL을 묶은 integrity → 최신 Main 동시 작업 CAS/병합·재빌드·재검증 → guarded 선택 전달 → 새 Main saved/RHI. Attempt2/3 실패와 원본 report/backup은 보존한다. MonsterVFX Main은 아직 미전달이다. Engineering continuity는 Root의20:09 절을 따르고 이번 기록에서 수정하지 않았다.

## 2026-10-10 20:20 KST — MonsterVFX 화면 검증 보완 및 최종 native 재검사

Private RHI4 기능 assertion은 오류0이었으나 기존 PlayerDefinition 빈 AbilityGrant의 시작 오류 로그1회로 Driver/native는 failed다. DEV만 saved 빈 행수를 확인해 정확한 문장·정확한 횟수를 예상 로그로 등록했고 게임 동작/에셋은 변경하지 않았다. Private Build14 exit0/16.953s 및 Main/private 입력 불변을 확인했다. 이전 실패 보고서는 보존한다.

Rim3 runtime은 actualRGB(2,0,0,0)·weight 감쇠·baseline복구/save0/fallback0 통과지만 QA fill5000cd가 weapon을 하얗게 포화시켜 visual 통과로 사용하지 않는다. 후속 QA는 fill0cd, 실제Weapon closeup3방향이다. Yetuga 일부 PNG는 PSC 큰bounds 때문에 map 전체가작게보였으므로 QA카메라만 bodymesh bounds로 변경했다. 독립 targeted QA에서 원작 RootTrail이 있는 공격2개와 실제 NI event가 있는 Recovery1을 원본 그대로 재생해 가까운 화면을 확인한다. 원작 포즈/scale/FX/재질 수치는 바꾸지 않는다.

Main 전달은 아직 하지 않았다. 최종DLL의 Monster/Player native 성공·Rim/Yetuga 실제 PNG 육안 통과·SHA결속 후 guarded delivery 및 새 Main 재검증을 이어간다. 487전체author·457전체import·원본추출/retime/Apes aliasapply는 반복하지 않는다.


## 2026-10-10 20:37 KST — Player 공격 VFX 13개 후보의 실제 검증·잔존 면 재검토

이전 한국어 유실 기록을 삭제하지 않고 이 UTF-8 보충을 사용한다. World6/Blood4/Recovery2/Spear1의 private 후보13을 보존했다. Spear 최종 opacity 후보 SHA는 `75833c9bff85c9233255cde90de62a73b013ef5d8a0b99b7d88b53dab95785b2`이며 Main에는 아직 전달하지 않았다. source 값과 복원 adapter, 혈흔 2배 밀도의 어시스턴트 임시 튜닝을 구분한다. 원작 cooked shader 전체 그래프·pixel parity·shipping GPU 비용을 확인했다고 기록하지 않는다.

ResumeSavedPrivate03의 새 RHI 저장 감사는 Art13의 정확 byte/양성 SM6 자원과 원래 8개 몽타주·401구간·8,308field 보존을 통과했다. ResumePrivateFinal03 native18+Brutal5도 Success이고 현재 Root 실제 Front147/Back156 PNG에서 이전 녹색 기본 데칼이 사라졌다. PD chain3은 그대로 보존했고 실제 런타임 shader readiness 원인과 Editor 보완은 Engineering continuity 및 GreenDecalRuntimeDebugger.json을 따른다.

Root가 Front146(2.513초)의 상단 하늘 뒤에 큰 반투명 각진 면을 관측하여 시각 통과/전달을 보류했다. FS_Kazan_DualAxeSword_Grapple_Atk_02와 FP_Kazan_recovery_stamina_01 등 해당 시점의 실제 producer만 격리 재생한다. producer를 확인한 경우 기존 Spear parent1의 경계 감쇠만 표적 보완할 수 있다. child/atlas/particle/source 시각·수명·크기를 임의 변경하지 않는다. 다음 절차는 producer 확정·필요 parent1 수정/새 early preview → 새 최종13 SHA → Root의 전체 actual RHI와 저장 감사·PNG review → guarded Main 선택 전달 → fresh Main 검증이다. 실패/이전 후보·증거는 모두 보존한다.


<!-- MonsterVFX_GuardedRebase_Checkpoint_20261010_2045 -->
## 2026-10-10 20:45 KST — MonsterVFX Reaction 동시 변경 보존·Rim/Yetuga 시각 원인 확인 중

현재 저장 범위는 Sequence487/State3342/Death6와 Art 후보457이다. 원작 V3 source와 NONV3 현재 슬롯 alias, 원래 timing/pose/curve 및 source schema를 유지한다. 다른 작업 ARCH-85의 Main146 완료 뒤 guarded source 병합으로 Main Source98/private101을 만들었고 Build15가119.359초/exit0·입력 불변으로 통과했다. 최종 private DLL SHA는 `5c6b3e40a2226e1aa044bb3eaf96fc0bb7fc08082f22a0ec19f7a79075dfabe2`이며 MonsterVFX Main 미전달 상태다.

Reaction130개 중 private 물리86개만 intake하고 Main 연결44개는 최신 SHA만 검증했다. 여섯 CharacterDefinition은 최신 Reaction field를 모두 유지하고 이미 만든 DeathPresentationMontage 포인터 하나씩만 복원했다. [ContentRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/ContentRebaseRevision.json)은 probe5680/apply30712 통과·6 saves/6 mutations/Main0·전체 T3D의 다른 field 보존·untouched493 SHA 보존을 기록한다. original author499/Main-before journal·plan·Apes Applied와 Art457은 바꾸지 않았다. 후속 전달은 별도 six-definition override 증거를 사용하고 이전 전체 author를 재실행하지 않는다.

Private native Attempt5의1552 images/fallback0/523.187초 성공은 Build14 이전 후보의 결과이며 최신 Build15 성공을 대신하지 않는다. 새 SavedAudit6 결과와 merged Definition6 검증을 확인해야 한다. [Rim6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt6/Driver.json)의 실제 compatible EnemyWeapon_R에서 source RGB(2,0,0,0)·weight 감쇠·자연 종료 baseline 및 transient 비교 상태 복구/package0/fallback0은 통과했다. Root의 실제 화면에서는 Rim 가시성을 아직 확정하지 못했고, 흰색 Yetuga와 snow writer 표시 관련 시각 RCA도 진행 중이다. 현재 data/runtime 통과를 full visual pass로 읽지 않는다.

재개는 최신 saved/actual-DLL·ContentRebaseRevision 확인 → Rim6 PNG 및 Yetuga snow writer/실제 visual producer를 분리해 원인 확인·필요한 최소 수정만 검증 → 최종 Monster/Player 및 Rim/Yetuga actual RHI·Root PNG review → 원래 metadata·plan/author/Art457와 최신 source·six-definition override의 SHA 결속 → 최신 Main 동시 변경 CAS와 guarded delivery → 새 Main 저장/런타임/화면 검증 순서다. 원본 재추출·전체 import/author/retime를 반복하지 않고 실패 보고서·이전 후보를 보존한다. Apes Grapple의 Particle4/material0은 그대로이며 FinalBlow3+Die_F2의 material State를 현재 paired producer로 가정하지 않는다.

## 2026-10-10 20:58 KST — Spear 실제 early 통과, 붉은 ribbon 모서리 추가 표적 복구

현재 후보는 World6/Blood4/Recovery2/Spear1의 Art13이며 Main 반영0이다. Spear FM_Kazan_Spear_A SHA `ea59a3424706da730a04ba9fd20470e12cfff3c7198fdd895f1eadae2acae014`는 원본 UV0의 V=0/1 외곽에서 opacity가 사라지게 수정했다. `4q(1-q)`는 양끝0/중앙1의 계산 adapter이며 원작 shader code 직접값이 아니다. parent scalar KZFXSpearRawUVFeatherWidth=.10(normalized UV)는 어시스턴트 임시 튜닝값이다. 원본 PS lifetime .5초, curve/atlas/child overrides/색상은 보존했다. PS175/VS344/sampler6, 이전 PS166 대비 9 instruction 증가는 Shipping GPU 시간 실측이 아니다.

SpearBellFixedPreview/da7d85b7365349e09ba30e87e49b5b25 PID28144 exit0/86.984초, actual early .033333/.066667/.1/.15/.25/.4초 등 PNG18장, module97aa, saves0, ea59 bytes 유지. 테스트 fixture만 t.OverrideFPS60으로 시간축을 고정했고 원본 gameplay rate/PS life를 변경하지 않았다. Root는 .0333/.25/.4 실제 PNG에서 밝은 곡선 궤적 유지와 큰 회색 각진 면 소실을 확인했다. 정확한 출처 및 미확인 경계는 Resume_20261010/SpearBellSourceContract.md, source PSKX/UV0 proof는 SpearEdgeReadOnly/SourceMeshUV0.json에 있다.

전체 Final04 실제 PNG104 Front2.531553초에서는 큰 붉은 대각 ribbon의 모서리가 새로 드러나 최종 visual pass를 보류했다. PNG111 Back2.666523초는 붉은 droplet/얇은 trail 및 초록색 decal 오류 소실을 확인했다. 원본 blood ribbon producer가 유력하며 추가 parent FM_blood_trail 한 개를 표적 진단/최소 Private 복구한다. 이를 원작 의도된 붉은 slab라고 단정하지 않는다. 기존 혈액량 80→40cm 및 burst22→44는 사용자 증량 요청에 따른 어시스턴트 2배 임시 튜닝이며 원작 확인값은 아니다.

다음 절차: ribbon 원본 texture/gradient/DP dissolve/UV 자료 → guard된 Private parent 최소 복구 및 isolated PNG → 새14 후보 provenance/manifest → 변경 뒤 Final05 actual/saved 및 Root visual → Engineering continuity의 Main delivery gate. 기존8montage401 타이밍을 재작성하거나 전체 이펙트를 재추출하지 않는다. source graph/DP unit/pixel parity/Shipping 성능은 여전히 미확인 범위다. 본 기록으로 Main 적용 완료를 주장하지 않는다.


<!-- MonsterVFX_VictimRimBuild18_Checkpoint_20261010 -->
## 2026-10-10 21:17 KST — MonsterVFX 피해자 Decal 창 정책·실제 붉은 Rim 확인·Yetuga cleanup 보류

이 절은 앞선 MonsterVFX 기록의 Blood 이름 기반 conditional guard와 Rim 원인 미확정을 보충한다. 원본43개 Decal export에는 `bOnAttackSuccessed`가 생략돼 있었고 원작 CDO 조건은 여전히 미확인이다. 이전 true guard는 원작 검증값이 아닌 프로젝트의 보수적 추론이었다. 새 명시적 표현 정책은 피해자 Damage/Death sequence가 원래 Decal 시각 창을 소유하도록 그 추론을 대체한다. 새 적중/피해 producer나 가짜 성공 상태를 만들지 않았다.

[VictimDecalPolicyRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VictimDecalPolicyRevision.json), SHA `9b3609b797c23f64cf66169515f1d456d9783b4ad522c39fab7e2231fe7516ec`는 probe29200/apply30084 passed다. Sequence26개의 Effect43개 `bOnAttackSuccessed=true→false`만 저장했고 Main0이다. 원본 재질/표면/크기/lifespan·시간/GUID·다른 State fields·raw pose/curve는 동일하다. 나머지473 author asset 및 original author499/Main-before journal·plan·Apes Applied·ContentRebaseRevision은 보존했다. 별도 override 이후 [fresh SavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)은487 Sequence/3342 State/Death6와 revision43/26 marker를 passed/저장0/byte 불변으로 확인했다. 이 정책을 원작 native CDO의 완전 복원이라고 표현하지 않는다.

[Rim8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/Driver.json)은 actual DLL16/capture63/package0/asset mutation0/material compile failures[]다. Root가 [StatisticsSynced PNG24](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/024_Halberd_Rim_Diagnostic_StatisticsSynced_SourceOverlay_WeaponFrontOblique.png), [원래 exposure PNG27](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/027_Halberd_Rim_Diagnostic_Recompiled_OriginalExposure_SourceOverlay_WeaponFrontOblique.png), [같은 MID base 비교 PNG39](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/039_Halberd_Rim_Diagnostic_Recompiled_ManualEV0_SameMIDBase_WeaponFrontOblique.png)를 실제 보아 붉은 Rim/붉은 재질 신호를 확인했다. PNG24는 GetStatistics가 compile 완료를 기다린 뒤이며 explicit recompile 전이다. source RGB(2,0,0)·weight·Duration/BlendOut1.2초를 유지했고 저장 shader/master/MI byte는 변하지 않았다. editor shader 준비 지연의 추론을 지지하는 결과이며 exposure/색/강도를 새 제품 tuning으로 바꾸지 않았다. transient diagnostic 상태는 복원했고 저장하지 않았다.

Root의 최소 Source 보완은 기존 첫 MID 생성 전 WITH_EDITOR EnsureIsComplete 호출이다. Build17은 다른 saved 프로세스의 DLL 잠금으로 LNK1104/exit6였고, 그 프로세스 종료 뒤 [Build18](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt18/Exit.json)이5.234초/exit0·입력 불변으로 통과했다. 현재 DLL SHA `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`의 regular Rim9가 실행 중이다. 진단의 GetStatistics/RecompileMaterial 없이 첫 재생에 붉은 윤곽이 나오는지는 아직 판정하지 않았다.

[Yetuga2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/Driver.json)는38 captures/failed/save0이다. actual snow writer의 main/depth/shadow=false와 Root [PNG10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/0010_Yetuga_Attack_NormalAtk01_03_Playing_011_FrontOblique.png)에서 dome 소실은 확인했지만, cleanup 표본의 Breath2/BodyDust1 active 때문에 full pass가 아니다. 원본 finite lifetime과 QA 1초 관측 여유의 충돌을 표적 조사 중이며 lifetime/sentinel 근거 이후 QA만 보완한다. 원본 FX pose·scale·재질·수명 수치를 새 값으로 바꾸지 않는다.

Main 전달은 아직0이고 사용자 Main PID9460은 Root 관측상 열려 있다. 재개는 current DLL/saved marker → regular Rim 최초 가시성 → Yetuga lifetime 기반 새 cleanup/근접 PNG → Root visual·full Monster/Player 회귀 → original Art457/author499와 두 별도 revision을 결속한 integrity → closed Main CAS/guarded 전달 → fresh Main saved/actual RHI/PNG/finalize다. 전체 source 추출·457 import·487 author/retime·Apes alias apply를 반복하지 않는다. 별도 PlayerVFX 기록과 기존 실패 보고서는 그대로 보존한다.


<!-- MonsterVFX_RegularRim9_Positive_20261010 -->
## 2026-10-10 21:18 KST — Build18 일반 Rim 최초 표시 실제 통과·전체 검증 진행 중

앞선 checkpoint 직후 [PrivateRimQA Attempt9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Driver.json)가 passed로 종료했다. actual loaded DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`, diagnostic_mode=false, PNG30/package saves0/asset mutations0/material compile failures[]이며 [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Exit.json)는62.594초/exit0이다. Driver SHA는 `cd5af174d284ec6e6696a31c313f4b8f5e673eaf43c816e13e7e344169365a0f`다. Root는 [Active03 Front PNG006](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/006_Halberd_Rim_Active_03_WeaponFrontOblique.png)와 [Active06 Front PNG009](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/009_Halberd_Rim_Active_06_WeaponFrontOblique.png)를 직접 보고 첫 표시의 강한 붉은 Rim을 확인했다. 별도 GetStatistics/RecompileMaterial/노출 변경 없이 기존 editor shader 준비 보완이 실제 첫 화면에서 작동했다. 원작 RGB/weight/시간·저장 shader asset을 변경한 결과가 아니다.

이 결과로 regular Rim의 최초 표시·fade/복원 검증은 통과했지만 MonsterVFX 전체/Main 전달 완료는 아니다. Root가 같은 Build18의 PrivateMonster full RHI6을 시작했고 Player 회귀 및 원본 lifetime에 맞춘 Yetuga cleanup/시각 재검증이 뒤따른다. 최종 candidate SHA 결속·closed Main CAS/guarded 전달·fresh Main saved/실제 RHI/Root visual/finalizer까지 앞 절의 재개 순서를 유지한다. Source/Art 후보는 Build18 이후 동일하고 이번 보충은 문서만 추가했다.


<!-- MonsterVFX_CurrentQAExternalB_Checkpoint_20261010 -->
## 2026-10-10 21:39 KST — Yetuga 실제 tail 관측·표현 후보 보존·최종 전달 대기

[Yetuga3 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt3/Driver.json)는82.578초/104PNG/actual loaded DLL1506/package saves0·asset mutations0으로 passed다. Root는 세 PNG를 직접 보았다. 원본 snow writer의 main/depth/shadow 비표시 adapter, 세 saved clip의 actual owned FX와 재질 복구·cleanup을 확인한 표적 범위이며 원작 shader pixel parity나 전체 몬스터 화면 검토 완료를 뜻하지 않는다.

[TailLifetimeEvidence](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/TailLifetimeEvidence.json)의31개 event/13개 resource 표적 근거를 재사용했다. NormalAtk01_03/RushGrab_Slow/StaminaRecover의 모든 serialized LOD0 lifetime 최대는6/7/6초이고 QA+1초 여유로7/8/7초를 관측했다. 활성 또는 미확인 emitter의 최대는6/6/6초다. 비활성 Falldown7초 등을 새로 활성화하지 않았고 원본 particle 수명·pose·scale·시간은 바꾸지 않았다. 추가1초는 어시스턴트 QA scheduling margin이며 원작 수치가 아니다.

[DeliveryReadiness](../../Saved/ImportReports/MonsterVFX_20261008/DeliveryReadiness.json)의 저장 Art457 current SHA와 Main-before CAS에는 차이가 없다. 저장 baseline의 기존 Effects2034개도 Main/Work에서 불변으로 확인했으며 이는 FinalResourceAudit의 exact2028 identity 목록을 새로 조사한 결과가 아닌 더 넓은 기존 baseline 검증이다. 원작 graph/NI 복원 adapter와 source metadata의 한계는 유지한다. Main 전달은0이며 별도 작업의 저장된 Input B/DevMap baseline은 보존한다.

다음 Art 절차는 fresh Native7/Player의 actual current asset 재생과 Root 전체 PNG 검토 → 현재 Art/plan/original author 및 Victim26·ContentRebase6의 분리 증거를 결속한 VisualQA/candidate → guarded 전달 후 fresh Main PNG 검토다. native6의 Input B Error 중단은 성공 자료로 쓰지 않는다. 추가 재질/효과 품질 RCA는 원인·owner를 확인한 표적 개선 후보로만 남기며 현재 화면을 임의로 원작 완전 복원이라고 기록하지 않는다.


<!-- PlayerAttackVFXPolish_Final07_BFixture_20261010 -->
## 2026-10-10 21:43 KST — 공격 VFX Art14 후보 확정·Main 전달 전 최종 검수

최종 private Art14는 World6·혈흔5·Recovery2·Spear1이다. 혈흔 부모 `FM_blood_trail` SHA `f64a56f85c2ba9d1d6b609866e09e46213f93f953f275c22d19187a9789c6ee5`는 원본 R 밀도와 발광 gain을 분리하고, 현재 DP dissolve·gradient·ParticleColor alpha를 opacity에 적용했다. 지나치게 사라지던 a2 중간 후보는 폐기 기록으로 보존한다. Spear 부모 SHA `ea59a3424706da730a04ba9fd20470e12cfff3c7198fdd895f1eadae2acae014`는 실제 원본 mesh UV0..1의 경계와4q(1−q) 완화를 적용해 초기 회색 사각 면을 제거했다. 원본 shader 그래프를 직접 확보한 값으로 표현하지 않는 복원 adapter다.

피 증량은 사용자의 더 많은 피 요청에 따른 어시스턴트 임시 튜닝이다. 원본 UnitScalar80cm→40cm, 원본 burst22→44이며 원본 burst 시각·수명·cap·색은 보존했다. Spear raw UV feather0.10도 normalized UV 단위의 조절 가능한 임시 값이다. 새 texture/particle/게임 수치나 원본 창 시각을 일괄 바꾸지 않았다. [Final05 근접 검수](../Resume_20261010/Final05VisualProductAssessment.md)에서 Root가 큰 빨간 면·회색 면·초록 데칼의 소실, 혈흔 리본/방울과 지면 먼지·공중 슬래시의 유지를 확인했다. 이는 전체 원작 pixel parity/401개 창의 시각 검증 완료를 의미하지 않는다.

[Saved06](../../Processes/ResumeSavedPrivate06/SavedArtAudit.json)은 Art14와 unchanged PD3의 새 SM6 resource/byte/compile 검사를 통과했다. Final06 native는 현재 B 입력에 대해 과거 X 테스트가 남아서 실패했고 제품 Art14/Action2는 바꾸지 않았다. DEV 테스트만 실제 B 경로에 맞춰 새 Build04로 실행하는 Final07의 결과와 Root 화면 검수는 아직 대기다. Main Art 전달은0이며 나머지 Effects·Maps·Monsters·DAS 및 다른 owner 변경을 보존한다. 재개는 Final07 검수/SHA 결속 → closed Main 선택 전달 → fresh Main 실제 RHI·saved·Root PNG → Art playback/state/continuity 완료 append 순서다.

<!-- BrutalInputDevMapComplete_20261010 -->
## 2026-10-10 — DevMap 확장·6종 실제 배치 완료

Main DevMap 저장·fresh reload·nav6지점·PIE12마리 초기화·native 인간4종 CombatPolicyPIE가 완료됐다. 바닥320m×320m와 nav312m×312m, 기존 인간10마리 유지+Apes/Yetuga 각1마리의 정확한 좌표·임시 수치 출처는 ART_PROJECT_STATE.md의 같은 날짜 절과 [배치 설명](../../Metadata/BrutalInputDevMap_20261010/README.md)에 있다. FinalVerification.json success=true, 작업용 author/verifier 종료·dirty0·byte 불변이 최종 기준이다.

재개는 Router→이 최신 Art state/continuity→Metadata/BrutalInputDevMap_20261010/{FinalVerification,Authoring09,FreshSavedVerification02,FreshPIEVerification02}.json→현재 Main DevMap의 Floor/DevAI_Navigation/DevTest_ApesStoneHandElite/DevTest_Yetuga 확인이다. 성공한 authoring·전체 몬스터 import/retime/분류를 반복하지 않는다. 애니메이션/0.01 메시 배율 변경은 없다. 이번 NullRHI 관측은 화면 PNG나 원작 배치 일치 검증이 아니며 Apes/Yetuga 자율 AI는 None이다. B 입력 정본은 Engineering에 분리했다.


<!-- MonsterVFX_SharedPolishIntake_Native7QA_20261010 -->
## 2026-10-10 22:00 KST — 공유 Effects14 반입·반입 전 shader 추론 정정·동일 pose QA 대기

[외부 Delivered17](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json) SHA `a75fa980…7ed7fa9`는 UTC12:47:50에 Source3+기존 Art14를 Main에 선택 전달한 사실이며 fresh Main 검증 대기 상태다. own Art457과 overlap0, Main Effects 새/삭제 uasset0이었다. [SharedEffectsRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1…bb422`로 receipt.before=old private·original baseline/receipt.after=actual Main을 검증해 saved bytes14만 private에 복사했다. Main/Work reuse2034는 승인14+불변2020이며 own457 SHA와 Main-before CAS는 불변이다. import/resave/new native resource0·Main 제품 수정0, ImmutableBeforePrivate14 백업과 원본 ResourceAudit/ArtManifest/AdapterMap/Light/Radius·이전 DeliveryReadiness는 보존했다.

[Diagnostic1 실제 shared graph](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt1/SharedDustShaderReadback.json)은 반입 전 master SHA `93814b11…6c1d2`의 관측이다. MI02의 inherited Tex_Opa white만으로 full-card alpha가 발생한다는 초기 추론은 철회한다. 실제 opacity에는 Tex_SubUV.R의 DynamicParameter.SubUV_frame 기반 atlas mask가 이미 연결되어 있고 white는 곱셈 중립이다. MI06의 fullUV Tex_Opa×single-frame mask도 관측됐으나 카드/먼지 경계 pixel 원인으로 아직 확정하지 않는다. 반입 후 master SHA `f5511be6…06954`는 외부 변경이므로 새 readback/동일 pose 비교를 해야 한다. 기존 source-derived Yetuga MI를 수량 유지를 위해 다른 source MI 대신 repurpose하지 않는다.

[Diagnostic1 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt1/Driver.json)은 failed: pause_anims editor setter가 animation position을0초로 reset해 same_pose=false였고 game time/camera는 불변이었다. shader copy/SHA·Source/asset writes0이나 비교 불변식 실패로 품질 판정은 사용할 수 없다. 기존 SingleNodeInstance.set_playing(False)와 원래 재생 상태 복원으로 QA만 보완한 준비본이 있으며 실제 재실행 통과는 아직 없다. 카드 owner·pixel attribution·원작 cooked graph stripped 한계를 유지한다.

다음은 새 shared14 저장본/graph 검증과 동일 pose·시간·camera의 선택적 숨김 비교 → 새 Build19/current semantic Source의 full Native·Player 및 Root PNG → VisualQA/candidate 결속 → guarded Main 선택 전달 → fresh Main saved/실제 PNG다. Native7은 obsolete X QA 대 current B grant로 failed였으며1390 captures·exit0을 Art 전체 통과로 읽지 않는다. **본 MonsterVFX Main 전달0**이고 외부 feature의 final complete도 주장하지 않는다.

<!-- PlayerAttackVFXPolish_MainVisualHold_20261010_2209 -->
## 2026-10-10 22:09 KST — 공격 VFX 선택 전달 완료·새 Main 화면의 잔여 결함 복구 중

앞선21:43 기록 이후 Art14·Source3의 선택17파일을 Main에 전달했다. [Delivered](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json)의 SHA는 `a75fa9803d7a40c1d0682b27dc1a085724477c38d2b2c73f632991ddb7ed7fa9`이고 상태는 `SelectedPolishDeliveredFreshMainValidationPending`이다. 이 전달 사실을 최종 품질 완료로 읽지 않는다. Build04 exit0과 현재 native DLL `d1957a4bd437fa5f717f99ad41122c8336707ecdc4a45819df2bd0a3c9d09361`, Source3를 사용했다. 다른 Input B/DevMap·몬스터·나머지 Effects 변경은 보존했다.

[새 Main 실제 재생](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Processes/ResumeMainFinal01/Driver.json)은 PID29700/exit0·283PNG·native18+Brutal5·저장0·compile failure0으로 통과했다. [새 Main 저장 검증](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Processes/ResumeSavedMain01/CombinedSavedAudit.json)은 PID5876/exit0·8montage/401창/8308field·Art14/PD3·저장0/byte 불변으로 통과했다. 그러나 Root가 직접 본 Main123/124의 SpinningAttack 바닥 흰 원판과 Main221의 BrutalFront 검은 사각 면 때문에 **전체 visual pass·Completion·finalize는 보류**한다. 데이터·runtime 통과가 이 결함을 부정하지 않는다.

흰 원판은 원본 smash_strong의 `refrac` emitter가 사용하는 `FMI_MashRefractionShock_01_DepthFade_03`의 굴절용 부모를 importer가 ParticleColor 흰 발광/opacity로 변환한 경로가 유력하다. 원본 Ref_str 곡선·900cm size·size-over-life·child ring/depth-fade를 표적 확보했다. 검은 면은 PP_Grapple/Spear/Ghostarm 입자군을 분리한 실제RHI 진단을 실행 중이며 아직 producer를 확정하지 않는다. 기존 효과를 통째로 삭제하거나 원본 시간·색·크기를 임의 변경하지 않는다.

정확 재개는 Saved `Resume_20261010/ResidualProducerIsolation/557a719fe4c047b7a6a26e9a1bdc7db4`의 owned PID26416 결과/PNG/T3D 확인 → producer 확정 후 기존 부모만 작은 Private shader 복구/전후SHA·SM6·isolated PNG → 새 후보 Art 증거(원본/계산/adapter/임시값 분리) → fresh Private 실제/saved/Root 화면 → 기존 Delivered를 보존한 별도 Art-only guarded follow-up 전달 → fresh Main 실제/saved/Root 화면·Input B13 불변 → 새 완료 receipt·Art/Engineering 정본 append 순서다. Source3/native가 바뀌지 않는 Art-only 복구로 새 runtime class/file를 만들지 않는다. 사용자의 Rider 에디터는 제어하지 않고 Root가 시작한 숨김 background만 사용한다. 이전 snapshot·실패·후보·Delivered는 덮어쓰지 않는다.


<!-- MonsterVFX_Build19_Saved7_Diagnostic2_Native8_20261010 -->
## 2026-10-10 22:16 KST — shared14 fresh readback·Yetuga 동일 pose 진단 통과와 전체 화면 검토 대기

[SharedEffectsRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1012742b376300dee3398a9755889027d1d80e8057ff0a38bcabbb422`의 exact saved14를 소비한 fresh [Saved7](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)이 passed다. shared2034=명시적 갱신14+보존2020, own Art457와 Main-before CAS를 유지했다. original source/ArtManifest/ResourceAudit/AdapterMap·Light/Radius·plan/author499 보고서와 별도 Definition6/Victim26 revision을 다시 쓰지 않았고 이번 문서 갱신의 import/resave/product mutation은0이다. Source `4a44ccc6…77c08e4`와 Build19/current DLL의 실행 결속은 Engineering 정본을 따른다.

[Yetuga Diagnostic2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/Driver.json)는 current Build19 actual DLL `b84df875…e311a`에서62.625초/102PNG·RushGrab_Slow/Recovery_StaminaRecover의 두 pose/time/camera 불변식과 원래 재생/filter 상태 복원을 passed로 확인했다. Root가 실제로 본 front PNG는0018/0020/0068/0070이며 clean plate 관측이다. Diagnostic1의 editor pause setter 포즈0 reset 실패를 이 성공과 섞지 않고, 반입 전부터 atlas mask가 연결돼 있었다는 정정도 유지한다. 이 두 clip 표적 진단을 regular 세 clip proof나 전체 원작 shader 품질로 확대하지 않는다.

fresh [Native8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Driver.json)은 current loaded DLL·passed/1568PNG/package0/material compile failures[]이고 [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Exit.json)는492.813초/exit0이다. 캡처 생성·runtime 성공은 전체1568장의 육안 품질 승인과 다르다. 원본 raw 시간/attachment/수명·임시 native renderer/shader adapter 출처, Apes Grapple의 material0과 FinalBlow/Die의5 source material state 계약은 그대로다. 새 gameplay AI나 source에 없는 paired Execution producer를 추가한 결과로 읽지 않는다.

다음은 Root의 current Player 실제 회귀(wrapper session45759, 실행 중/pass 미확정)와 전체 representative PNG 검토 → frozen VisualQA/candidate → 최신 Main shared shader/Source/native/Content 변경 및 CAS 재확인 → guarded 전달 → fresh Main saved/RHI/Root PNG다. 외부 Player polish22:09의 흰 원판/검은 면 후속 owner 조사·개별 보고서는 보존하며 외부 최종 품질 완료를 대신 주장하지 않는다. [DeliveryReadiness_Build19](../../Saved/ImportReports/MonsterVFX_20261008/DeliveryReadiness_Build19.json)의 당시 Native8 pending은 위 후속 결과로 보충한다. **본 MonsterVFX Main 전달0·최종 완료/전체 visual pass 미확정**이다.


<!-- MonsterVFX_CurrentQA_RecoveryDeathVisualHold_20261010 -->
## 2026-10-10 22:22 KST — Native8 후반 Recovery 검은 카드·Death 흰 사각 면의 실제 visual hold

Build19·Saved7·Native8의 current DLL 통과를 보존한다. 뒤이어 [Player actual regression](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt1/Driver.json)은389PNG/162.5초/native Success/package0/compile0, [regular Rim10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt10/Driver.json)은24PNG/48.921초/diagnostic=false/saves0/mutations0으로 passed다. 모두 current actual DLL `b84df875…e311a`이며 package bytes나 source값을 변경한 결과가 아니다. Root 전체 시각 검토는 여전히 미통과다.

Root는 Native8 [1262_MonsterVFX_Yetuga_Recovery_StaminaRecover_Sequence](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/1262_MonsterVFX_Yetuga_Recovery_StaminaRecover_Sequence.png)/[1264](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/1264_MonsterVFX_Yetuga_Recovery_StaminaRecover_Sequence.png)의 Recovery 후반 불투명 검은 spiral card, [Death1348](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/1348_MonsterVFX_ApesStoneHandElite_Death_Die_F_Sequence.png)의 큰 흰 hard rectangle을 실제로 확인했다. 앞 Diagnostic2의 early Recovery clean plate는 이 후반 phase를 검사하지 않았으므로 반증이나 전체품질 통과로 쓰지 않는다. 해당 시점 own Roar_01 PSC/event inventory가 존재하지만 카드가 그 emitter/재질에서 나오는지는 template-only/exclude PNG로 확정한다. Death rectangle의 producer/material chain은 delivery_review가 별도로 표적 조사한다.

기존 두 QA script의 [LateRecovery revision](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/LateRecoveryScriptRevision.json)이 준비됐으며 Root만 UE를 실행한다. --diagnostic-late는 Recovery만 natural playback→actual source pose>=2.2초 freeze→NormalScene/OwnFocus/OnlyOwnRoar01/WithoutOwnRoar01 동일 pose·game time·camera를 캡처한다. 2.2초는 Root 요청2.0–2.35 범위의 임시 QA 선택이고 Native8 world time을 source초로 오인한 계산이 아니다. exact own tagged Roar01 inventory·filter/재생 restore·save0/shader0 계약, 원래 regular3/early2-case 동작 및원작 수명/시간/색/scale는 보존한다. py_compile/오프라인 mode 검사는 통과했으나 새 late actual 결과·visual pass는 아직 없다.

**MonsterVFX RootVisualQA 미통과/Prepared 미생성/Main 전달0**이다. 재개는 두 실제 결함의 선택적 owner·pixel 진단 → source 근거/stripped graph 한계와 필요한 최소 private adapter 수정 분리 → current saved/runtime/전후 PNG → Root 전체 VisualQA/candidate → 외부 Player polish 후속 shared 변경을 다시 확인한 guarded Main 전달 → fresh Main 실제 검증이다. 원본487 author/457 import·임의 texture/color 교체를 반복하지 않으며 외부22:09 hold와 original report/각 revision은 그대로 남긴다.

## 2026-10-10 22:49 KST — 공격 VFX 재개, 잔여 면 경계 검증 중

- 이번 재개 대상은 Player 공격 VFX 보정이다. MonsterWork의 첨부 파일은 별도 Monster 구현으로 전환하는 지시로 해석하지 않았다. 기존 Source3 + Art14의 Main 전달은 `MainDelivery/Delivered.json`에 보존된 provisional 상태이며, 최종 Completion은 아직 없다.
- Private08(PID27052, exit0, 134.928307초)은 native18 + Brutal5 기술 검증과 first-pose13/13 검사를 통과했다. SavedPrivate08의 정확한 파일명은 `CombinedSavedAssetAudit.json`이며, Montage8 / 이벤트401 / 원본8308 검사와 Saved Art16 검사에 통과했다. 앞선 기록의 `CombinedSavedAudit.json` 표기는 이 정확한 파일명으로 읽는다.
- Root가 실제 PNG를 확인했다. Spinning123/124의 불투명 흰 원판과 Front221의 큰 검은 하늘 면은 사라졌지만 Front223/224에 옅은 직선 다각형 경계가 남아 Private08의 시각 승인은 보류했다. 성공 로그만으로 완료 처리하지 않았다.
- Shock 부모는 Private에서 순수 굴절로 보정된 SHA `3d2269e5a1efad4b53c6ca04cab5be1b8a8603be0853fc61f4760d6e571c6e32`이다. 원본 곡선/자식 값은 보존했고, PixelNormalOffset/CoverageIgnored와 radial normal은 원작 그래프 미확인에 따른 엔진 복원 adapter다. 실제 굴절파의 가시성은 아직 미확인이다. early paired captures `ResidualProducerIsolation/108b6dce35ea4e5da34b406f74197179` 및 dense15프레임 `6429022674b84f4eab00444d947d9b40`은 원판 제거만으로 굴절파 복원 통과를 주장하지 않는다.
- SubUV 부모는 PC.A를 먼저 saturate한 Private08 값에서, 원본 Ghostarm `ParticleModuleParameterDynamic_7.DynamicParams[2].Opa_dissolve`를 마지막 atlas opacity에 연결했다. 원본 table `[0,.21508475,.31788456,.34419835]`/TimeScale3은 보존했다. `saturate(atlas.R - DP.Opa_dissolve)` 연결은 제거된 원작 노드 그래프에 대한 명시적 복원 adapter다. 현재 Private SHA `e9cfc1b53d34ff0f8eed7e183282659e72c49a307b4ba1918563654f5dffd1b8`, author PID25072/exit0/36.469초/부모1개만 저장/다른 Effects2033개 불변. Main의 추가 부모2개는 아직 수정하지 않았다.
- Active Frozen16 SHA `4df6f3f20adbfdd42607d0de39f873c2ee5788ee5d91899b68daedee76d7079e`; 이전 Frozen/author/실패/보류 증거는 Saved History와 각 프로세스 폴더에 보존했다. Source3/BuildResumeFinal04/native DLL `d1957a4b…`는 그대로다. Root가 숨긴 `ResumePrivateFinal09` 전체 공격 실행을 시작했다. 사용자 에디터는 조작하지 않았다.
- 정확한 재개: Private09 종료/RuntimeIntegrity/PNG223–225와 Spin123–124를 Root가 확인 → 필요하면 Shock pure-refraction 무저장 기술 진단으로 가시성 원인 확인 → 현재 해시로 fresh Saved 감사 → root visual16 + 실제11 proof를 `Resume_20261010/Tools/art_followup_exact.py`에 연결 → 닫힌 Main의 전체 CAS/원본 receipt 불변 확인 후 Art 부모2개만 follow-up prepare/apply → fresh Main actual/saved/first-pose/Input13 불변 검사 → 새 follow-up Completion과 도메인 문서에 실제 결과 추가. 기존 Main17 receipt를 다시 쓰거나 Private08 보류를 현재 통과 증거로 사용하지 않는다.


<!-- MonsterVFX_PrivateMaterialRepair_LateDiagnostic_D00Tail_20261010 -->
## 2026-10-10 22:52 KST — Roar02·D00 실제 소유 확인 후 재질3 후보 고정·전체 품질 검증 대기

현재 원본487 Sequence/3342 State/Death6·original author499·Art457 보고서와 각 revision은 보존돼 있다. Root의 실제 private 수정은 [FM_WPO_Trail_A1](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Roar02/Attempt1/Repair.json), [Decal 부모2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply1/Repair.json)뿐이다. WPO는 기존 reused master의 추가 선택1, Decal2는 기존 own457 내 override다. JointVisualMaterialRepairRevision SHA `138dc65c…e107a`는 총968(Source11+499+457+reused1)을 별도 결속한다. PS/MI/texture·원본 animation/particle/데칼 시간과 수명·나머지455 own Art 및 Main-before bytes는 보존했다.

잘못된 Roar01 추정을 철회한다. [실제 late3 review](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt3/DiagnosticVisualHoldReview.json)의 template-only/exclude 결과는 Roar02 own PSC만 검은 spiral card를 재현한다. 수정 뒤 [late4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt4/Driver.json)은49.469초/50PNG·동일 pose/time/camera/복구·save0로 passed이고 Root0022 Normal/0034 OnlyRoar02는 후반 검은 면이 없다. source pose2.2320659초의 제한 관측이며 앞 early Diagnostic2나 새 late4를 전체 timeline·regular3-case proof로 사용하지 않는다. source graph stripped 한계와 maxRGB opacity/polar-mask 복원 adapter 출처는 [Art 정본](MONSTER_VFX_PLAYBACK_20261008.md)에 분리했다.

D00 QA1의0000 Normal 흰 면·0004 WithoutD00 없음·0006 OnlyD00 흰 면으로 Apes Death D00 producer는 실제 확정됐지만 Driver는 whole-tail 실패다. clipend+10초 남은 것은 원본30초 혈흔이고 D00 원본9초는 소멸했다. [수정 전 스크립트/실패 보존 및 QA-only revision](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/TailObservationRevision/TailObservationRevision.json) 후 Root가13:46UTC 시작한 [D00 QA2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt2/Driver.json)는 문서 작성 중90.187초/8PNG·passed로 저장됐다. D00+10.0014초 잔존0·전체+31.0109초 잔존0, 동일 pose/time/camera/가시성·재생 복구·bytes 불변·save/asset/shader0이다. 이 자동 제한결과의 overall_visual_pass는false이며 전체 시각 승인과 다르다.

정확 재개: current 재질3/Joint revision SHA·immutable originals/499·Art457/공유2034/Main-before CAS 재확인 → fresh Saved와 full Monster·Player·regular Rim·regular Yetuga 네 회귀/실제 representative PNG → Root VisualQA·candidate launch freshness/예외1 reused WPO의 명시적 provenance → 최신 외부 owner 변경 보존/CAS·guarded Main 전달 → fresh Main saved/RHI/실제 PNG/finalizer다. 현재 **MonsterVFX Main 전달0·최종 visual pass/전체 완료 미확정**이고 Main author/import나 새 gameplay/AI 구현을 시작하지 않는다. 원본 opaque 판의 단순 삭제·수명 축소·PS 이벤트 통째로 제거로 실패를 숨기지 않는다.


### 2026-10-10 22:53 KST — current report 경로·시각 승인 미완료

실제 결속 파일은 [Authoring/VisualMaterialRepairRevision.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json), SHA `138dc65c…e107a`다(앞 JointVisual filename 표기 정정). Root는 D00QA2 종료를 확인했으며 fresh 네 회귀/Saved를 진행할 단계다. Roar02 positive visibility는 여전히 pending이고 late clean plate를 전체 효과 품질로 해석하지 않는다. RootVisual/candidate/Main 전달·fresh Main 완료 기록은 아직 작성하지 않는다.

## 2026-10-10 23:24 KST — Spear 지수 연결 저장·Private10 후반 흰 카드 HOLD

중단 대상은 Player 공격 VFX 품질 보정이다. 기존 Main Source3+Art14 전달 receipt는 그대로 provisional이며 최종 Completion은 없다. Shock와 SubUV의 Private 부모 변경은 Main에 아직 전달하지 않았다.

Spear 첫 author는 Power의 API 입력 이름 `Exponent`로 연결하다 save 전에 실패했다. 엔진 `MaterialEditingLibrary.cpp`와 `MaterialGraphNode.cpp`에서 입력명이 `Exp`로 축약되는 것을 확인해 v2를 실행했다. `SpearHighlightPowerAuthor/3aac9c7726d242eaae21ea8f82a390b4`는 PID6896/exit0/31.891초, 부모1개만 저장/나머지2033 Effects 불변/Main Effects 불변이다. SHA `34e9b033dafae483d037575e9624e56dc6a6aee95e6514cf9ba35c17096fe50a`, PS177/VS344/sampler6. 원본 CachedExpressionData.Parameters의 HighLight_Pow50와 Normal override1은 바꾸지 않고 선형 밝기 gain 대신 `HighlightRGB*pow(sat(HighlightA),HighLight_Pow)`로 연결했다. 원작 cooked 그래프가 제거되어 이 연결은 명시적 복원 adapter이며 원작 shader 직접 복원으로 표현하지 않는다.

Private10(PID12264/exit0/136.062294초)은 실제 native18+Brutal5와 byte 불변 검사를 통과했다. Root가 시간2.095/2.234/2.383초의216–218 PNG에서 큰 흰 대각 면이 없고 붉은 팔 ring이 유지되는 것을 확인했다. 그러나221(2.819887초)의 흰 텍스처 사각 카드 때문에 Root visual은 HOLD다. 캡처 번호는 실행마다 달라 실제 Driver의 position_seconds로 비교한다. SavedPrivate10(PID27468/exit0/94.155499초)의 정확한 감사는 `CombinedSavedAssetAudit.json`과 `SavedArtAudit.json`이다.

Shock는 inactive0 프레임에서 동일 픽셀/active1에서 변화하는 paired captures와 실제 DP·PC.A·ring texture 양성 진단으로 순수 굴절이 렌더링됨을 확인했다. 원작과 같은 가시성·pixel parity·shipping 성능까지 검증한 것은 아니다. 원본 크기/수명/128개 DP curve를 유지한다.

Active Frozen16 SHA `f3045e378e8d836bcb17771b5c6d05178158652473428b9fd9893f023f158b71`. 정확 재개는 `Processes/BlackProducerActual06`의 Root 숨김 same-frame template-exclusion 결과/PNG/복구를 확인하여 후반 흰 카드 producer를 확정 → 해당 기존 부모의 최소 복구 → fresh Private actual/saved/Root PNG → v2 Art-only helper(13/13 guard)의 현재 3부모 또는 실제 필요한 최소 행 선택 전달 → fresh Main actual/saved/first-pose/Input13 → 새 follow-up Completion과 Art 정본 append다. 현재06은 window2.65..3.1의 첫 버전 실행이며, 준비된06_v2 window2.78..3.15는 아직 실행하지 않았다. Root visual 미통과를 candidate approval로 바꾸지 않는다. 사용자/다른 owner 에디터 제어0.


<!-- MonsterVFX_138_FourFreshRHI_D00Hold_202610102348 -->
## 2026-10-10 23:48 KST — 재질 revision 이후 네 실제 회귀 통과·D00 바닥 양성 검증 보류

[VisualMaterialRepairRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json) SHA `138dc65cb89362a72d1374edbe6c17943e33c74cc967296b53be387bc92e107a`의 private 부모3 후보와 원본 Art457/author499/Shared14 기록을 보존했다. [Saved8 readback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)는 이 revision의 실제 graph/pin readback3과 선택 bytes 불변·저장0을 passed로 확인했다. 새 [Native9 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt9/Driver.json)(1549PNG/581.219초), [Player2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt2/Driver.json)(388PNG/144초), [regular Rim11](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt11/Driver.json)(27PNG/40.109초), [regular Yetuga5](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt5/Driver.json)(106PNG/80.438초)이 모두 current Build19 DLL에서 passed/exit0/package saves0/material compile failures[]다. Source/native 결속의 자세한 계약은 [Engineering 정본](../Engineering/MONSTER_VFX_RUNTIME_20261008.md)의 이번 checkpoint를 따른다.

Root가 [Native9 Roar02 실제 화면1216](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt9/1216_MonsterVFX_Yetuga_Recovery_StaminaRecover_Sequence.png)에서 수정 뒤 Roar02 helix의 실제 양성 효과를 확인했다. 앞 late4의 검은 면 없음만으로 양성 효과를 주장하던 범위를 이 실제 화면으로 보충한다. 그러나 [D00 QA6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt6/Driver.json)의 same-pose/time/camera·수명/복구·저장0 passed(87.156초/14PNG)는 **D00 바닥 효과의 정상 양성 확인이 아니다**. OnlyD00NoParticles0008과 NoDecalsNoParticles0012의 순수 바닥 비교도 Root 양성 승인이 없으며 기존 흰 hard quad 제거로 품질 통과를 대신하지 않는다. QA5 WithoutD00 비교에는 다른 혈흔이 남아 있었으므로 완전한 무데칼 기준으로 사용하지 않는다.

[D00 QA4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt4/Driver.json)는 노출되지 않은 Python `DecalComponent.get_component_location` 호출로 failed/78.422초/0PNG였다. 모든 기존 visibility/재생/capture/postprocess 상태의 finally 복구와 saved bytes 불변은 true이며 실패를 보존하고 노출 API로 보완한 QA5/6을 별도로 사용했다. 이전 읽기 분석의 “P5=.2/미연결 FadeOut”은 잘못된 node index 대조였으므로 철회한다. actual saved pin은 M_New P5=ScalarParameter_10, FM P5=ScalarParameter_8이며 두 노드 모두 source FadeOut=1이다. P0는 RGBA(1,1,1,1) 상수로 Particle alpha0 가설도 적용되지 않는다. 원작 topology가 stripped된 polar/mask 복원 adapter의 pixel parity는 여전히 미확인이다.

마지막 readonly preflight는 Source11+author499+Art457+reused WPO1=968의 Main-before/private-after CAS, 원본/Shared/재질 revision 결속과 frozen helper4를 통과했다. 외부 Player의 Shock/SubUV 추가 Main2 follow-up receipt는 아직 없고 두 Main bytes는 이전 값이다. 다른 task의 절대경로 PlayerPrivate editor PID30020은 제어하지 않았으며 delivery census가 이 다른 프로젝트를 blocker로 분류한다는 앞 설명은 철회한다. 23:43:09 KST 실제 census는 empty이고 closed-Main gate가 passed였다.

정확 재개는 Root가 실행하는 owned MID-only 진단으로 curve/색/mask 소비를 분리하고 원본 material/상태를 복구한 실제 바닥 양성 화면을 확인하는 것이다. 게임 수명·색·크기·공용 shader를 임의 조정하지 않는다. 필요시 최소 private 표현 수정의 출처/별도 revision을 먼저 기록하고 fresh Saved/네 회귀를 다시 결속한다. 그 뒤 Root VisualQA → candidate integrity → 최신 외부 Main2/Source/native/Content 및 process CAS → guarded968 전달 → fresh Main saved/실제 네 회귀/Root PNG/finalize 순서다. **VisualQA/candidate/Prepared/Delivered 미생성·이번 MonsterVFX Main 전달0·전체 완료 아님**이다.



<!-- MonsterVFX_DecalReauthorStaging2_202610102357 -->
## 2026-10-10 23:57 KST — QA8 알파 분리·staging 보존과 새 Decal2 적용, 전체 검증 대기

[D00 QA8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt8/Driver.json)(PID30456/74.672초/24PNG/exit0)의 기술 불변식·MID 복원·원래 데칼9초/혈흔30초 자연 수명·저장0은 passed다. Root 실제 D0020(source RGB alpha1)와 E0022(white RGB alpha0)로 Param alpha 가설은 제외했지만 정상 설정 positive 가시성을 우회값으로 대신하지 않는다. 원작 근거 미확인인 Param-as-color 연결을 철회하고 기존 ImageRGB×PC fallback을 쓰는 최소 adapter를 준비·적용한다. source 수치/PS/MI/curve/GUID/time/life는 보존한다.

[ReauthorStaging2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/ReauthorStaging2/Staging.json), SHA `5dbc6a39…1af1e0`는23:51:21 KST private 부모2 원본 복원과 원본/이전2 backup·기존138 보존의 immutable 기록이다. append 전에 Root Probe2(PID12592/save0) 및 [Apply2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply2/Repair.json)(PID17048/save2)가 실제 passed로 끝났다. current after2는 `52d746d6…474dc0a`/`c4eb1ca6…5d33798`, Main/Source/native·나머지455 Art/499 author 불변이다. 따라서 staging original2 상태는 과거 중간상태로 보존하며 현재 상태라고 반복하지 않는다. 이전 revision138 승인도 현재2에는 유효하지 않다.

재개는 새 helper 동결/Root probe2·apply2(완료) → staging에 보존된138 archive 및 mirror 새 current assembler 결속 → fresh Saved/Monster·Player·regular Rim·regular Yetuga → 정상 D00 positive·Root 실제 PNG → 최신 Main/외부 owner/process CAS → guarded968 → fresh Main saved/네 회귀/Root/finalizer다. rollback은 Staging.json PreviousRevision2Assets exact previous_sha256 두 파일만 private 경로에 CAS 복원한다. 원본 metadata/499 journal/487 sequence/457 전체 import를 다시 쓰지 않는다. **현재 새2 적용 뒤 fresh 검증 대기·이번 MonsterVFX Main 전달0·전체 완료 아님**이다.


### 2026-10-10 23:58 KST — current revision6309 실제 결속 추가 확인

위 pending assembler 단계는 Root의 [current revision6309](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json)(SHA `6309ef7d…21be60e`) 실제 결속으로 완료됐고 [이전138 archive](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairHistory/Revision1_138dc65c/Archive.json)의 두 mirror 원본 SHA를 확인했다. Root QA9 owned session19559 실행 결과/정상 D00 positive를 다음 입력으로 확인한다. 이후 current6309 fresh Saved/Monster·Player·regular Rim·regular Yetuga·Root VisualQA/candidate/Main CAS·guarded968·fresh Main이 남는다. Main 전달0·최종 시각 통과 미완료 경계는 유지한다.
 
## 2026-10-10 23:59 KST — Player 회복 리본의 흰 카드 정확 원인 확인

Root owned `Processes/BlackProducerActual10`은 PID22700/exit0/118.035394초이며, BrutalFront Attack2 실제 2.7893528938293457초의 같은 pose/time/camera에서 재질6개를 각각 제외했다. Root가 00/03/04/05/06/07/08 PNG를 직접 보았고 **slot1 `FMI_ribbon_2dist_A_38` 제외06에서 큰 흰 띠·사각 무늬가 사라짐**을 확인했다. Fluid243은 그 무늬의 원인이 아니며 GPU82는 작은 점광만 제거한다. 원본 Recovery PS SHA95e6 및 child MI 수치·입자 시뮬레이션·저장 에셋은 변경하지 않았다.

07은 미노출 속성 이름, 09는 보호된 `EmitterMaterials` 접근 때문에 변경 전에 실패한 진단으로 보존한다. 성공10은 공개 GetMaterial/SetMaterial로 원래 MI 포인터·경로·디스크 해시를 복원했다. 보호된 배열의 원래 형태 복원이나 이미지 pixel identity를 주장하지 않는다. baseline/restored의 소수 픽셀 차이는 별도 `RecoveryMaterialReadOnly/Actual10DecodedMaterialSlotPixelPairs.json`에 남겼다. 저장0·제품 byte 불변·same-state 통과이고 native 전체 완료 자료와 구분한다.

정확 수정 대상은 기존 `/Game/_Art/Effects/Shared/Materials/Ribbon/FM_ribbon_2dist_A` 부모이며 Main/Private 현재 SHA `8d3a5bf3747d216a9aa2cd8434984d9958e1791caf28c53deed09e2ce72c7542`다. 저장된 동일 해시 T3D와 source parent SHA `6bb8d84edb6c75bd98d8acdafca0b19c5c6618e9a2fc8488a861c39862110b06`을 재사용한다. 원본 Emi_pow4/Opa_Pow1을 지수로 연결하고 PC.A를 opacity mask 전에 제한하는 작은 private 복원 후보를 준비 중이다. 원작 노드 topology는 stripped이며 UV1 streaming 기록만으로 원작 연결을 확정하지 않는다. UE5.8 BeamTrail VF는 모든 UV channel을 input.xy로 초기화하므로 단순 UV index 변경이나 엔진 수정은 하지 않는다.

현재 Private10 화면 HOLD와 Main17 provisional은 유지한다. 다음은 Root의 부모1 private author/SM6/bytes 검증 → Frozen Art17(기존16+Ribbon1) → fresh Private11/saved/대표 화면/first-pose → 새 v3 exact 부모4 follow-up(Shock/SubUV/Spear/Ribbon) → fresh Main02/saved/Input13/화면 → 별도 Completion이다. Fluid 부모 추가 수정·Spear TotalU_Pow 실험은 적용하지 않았다. 사용자 에디터 제어0.


<!-- MonsterVFX_6309_Saved9_QA10_PSCBlocker_202610110018 -->
## 2026-10-11 00:18 KST — D00 통과·QA10 세 PSC 양성 뒤 품질 원인 확인 대기

마지막 저장 검증은 current6309의 [Saved9](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)(PID31520/99.75초/exit0·graph3/save0 passed)다. [QA9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/Driver.json)(PID23764/84.985초/24PNG/exit0)는 복원을 통과했고 [RootD00Review](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/RootD00Review.json) SHA `6e68bf2d…fab27e0`로 정상0008 soft circle vs0012 pure floor의 D00 양성을 확인했다. Normal0000 black PSC cards는 HOLD다. [QA10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt10/Driver.json)은 방금 PID17540/89.328초/30PNG/exit0·복구/save0 passed로 종료됐고 Root가 FP_DeathEffect1+world fall2 모두의 검은 카드 양성을 확인했다. 단일 FP burst12 원인으로 좁히지 않는다.

Root Native10 current6309/PID10736은 실행 중이다. 앞 regular Native9/Player2/Rim11/Yetuga5는138 결과이므로6309 승인으로 재사용하지 않는다. 정확 재개는 QA10 actual template/material slot3/6/6 및 current native graph 표적 readback → 원인·최소 수정 필요 여부 결정/필요시 별도 revision → 해당 current의 fresh Saved·Native10/Player3/Rim12/Yetuga6와 Root 전체 시각 확인 → 최신 Main/외부 receipt·process CAS → guarded968·fresh Main saved/네 회귀/finalizer다. Native10의 완료 결과는 아직 없다.

[QA7 sidecar](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/QA7PixelAnalysis/ReferenceResolution.json)가 archived138을 연결하며 `fc5fb913…dd00e0a` 분석은 불변이다. [SourceEvidence](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/QA9BlackCardSourceAudit/SourceEvidence.json)의 source alpha·복원 코드 약점을 actual GPU 원인으로 확정하지 않는다. 제품/Source/helper 수정·agent UE 실행0, MonsterVFX Main 전달0·전체 완료 아님이다. [Art 정본](MONSTER_VFX_PLAYBACK_20261008.md)과 [Engineering continuity](../Engineering/ENGINEERING_WORK_CONTINUITY.md)의 같은 날짜 절을 함께 따른다.

<!-- PlayerAttackVFXPolish_Ribbon17_FairSpin14_202610110039 -->
## 2026-10-11 00:39 KST — Player VFX Art17 저장·Private11 기술 통과, Spin 화면 검증 재개

중단된 Player 공격 VFX 품질 작업을 이어 진행한다. MonsterWork의 Brutal 파일 첨부만으로 별도 gameplay 변경을 시작하지 않았다. 원래 Main Source3+Art14 전달은 `MainDelivery/Delivered.json` SHA `a75fa9803d7a40c1d0682b27dc1a085724477c38d2b2c73f632991ddb7ed7fa9`의 provisional 상태다. 추가 Main 부모4 전달과 최종 Completion은 아직 없다.

Actual10의 동일 프레임 재질 제외로 큰 흰 회복 카드의 정확 producer는 Recovery slot1 `FMI_ribbon_2dist_A_38`임을 확인했다. 원본 Emi_pow4/Opa_Pow1을 기존 부모의 Power에 연결하고 PC.A를 mask 전에 제한했다. 원본 PS/MI/곡선/시간/크기는 보존했으며 원작 cooked graph가 stripped된 명시된 복원 adapter다. 부모1 private 저장 SHA는 `7a18ef7301d3c542a7b062496c955374a231123ebbaa6e43b90be0cefaa58c20`, active Frozen Art17 SHA는 `9b413d2305f8c7a1474253a71698132447cb03f7f4cfd016d58311aac77dffed`다. source parent/child와 author race의 경계는 RecoveryRibbonPowerAuthor 보고서 및 별도 D08 supplement에 보존했다.

새 `ResumePrivateFinal11`(PID13388/133.058819초)과 `ResumeSavedPrivate11`(PID12732/97.966333초)은 exit0·native18+Brutal5·8몽타주/401구간/8,308field·Art17/SM6·저장0·파일 불변을 통과했다. Root는 실제 slash/회복/양수 blood와 이전 큰 white beam/card 제거를 확인했다. 다만 Spin124의2.009536266초 왼쪽 위 faint triangle 때문에 화면 HOLD다. Source3와 Build04 native d195/PDB95e4는 변경하지 않았다. Engineering 상세는 별도 정본을 따른다.

Actual11은 캡처 이력이 달라 Full11에 없는 black-border 카드를 만들었으므로 정확 triangle producer 근거로 사용하지 않는다. Actual13(PID21732/146.843821초/exit0)은 전체 native Success를 관측했지만1.98–2.10초 검사 창을1.949780345→2.124849081초로 건너뛰어 분리 비교를 생성하지 못했다. 기존 status 문자열을 분리 진단 성공으로 해석하지 않는다. Root는 Actual13 PNG095의2.124849081초에서도 triangle 재현을 확인했다.

현재 Root-owned Actual14(session62280)는 앞선 FullPolish 선택12 캡처 이력을 유지하고 측정 검사 창2.00–2.35초 첫 프레임에서 native-history baseline→reset-history baseline→template 제외를 수행한다. 이 창은 관측 프레임에 따른 QA 설정이며 gameplay 수치가 아니다. same numeric pose/time/camera/PSC와 다른 temporal mode를 구분하고 target miss는 failed로 기록한다. 진단 wrapper의5875→4b 정리는 assembled payload 동일성을 runtime DriverSource로 별도 대조할 예정이다. 실행 결과·producer 확정·시각 승인을 아직 주장하지 않는다. 사용자/다른 작업 에디터 제어0이다.

정확 재개는 Actual14 Exit/Driver/ActualFrameParticleExclusion/실제 PNG 확인이다. 특정 template를 제외할 때 사라져도 해당 재질 슬롯을 확인한 뒤 최소 부모 수정 여부를 결정한다. 후보 byte가 바뀌면 Frozen/전체 private RHI/Saved/Root 화면 근거를 새로 묶는다. 현재 네 부모(Shock3d/SubUV e9/Spear34e9/Ribbon7a18)가 그대로이고 화면을 통과하면 별도 accepted Root candidate/visual→v3 exact 부모4 prepare/apply→fresh Main02/Saved02/first-pose/Input13/Root 화면→새 receipt에 결속한 finalize 순서다. 기존 pending/원본 receipt를 덮어쓰지 않는다. 원작 pixel/shader 완전 일치·shipping 성능은 미검증이다.


<!-- MonsterVFX_MainDelivered_MainSavedFailed_20261011010443 -->
## 2026-10-11 01:04 KST — MonsterVFX Main 전달 완료·fresh Main 의존성 확인 대기

current6309의 private Saved9/Native10/Player3/Rim12/Yetuga6 및 [RootVisualQA](../../Saved/ImportReports/MonsterVFX_20261008/VisualQA.json)는 passed다. 이전 QA10 카드 HOLD는 [QA11 shader 준비](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt11/RootShaderReadinessReview.json)의 unchanged8 assets로 해소됐고 제품 alpha-mask 수정은 없다. [Delivered968](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/Delivered.json), SHA `12f3af9d…c86603a`가 실제 Main 전달을 기록한다. 새 alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`이다.

최신 fresh MainSaved는 PID31324/Exit1·effect data_fields 실패, 저장0이다. Halberd FinalBlow event `KZMVFX_f3af66febacc3ab35102cf8b`의 FP_BloodSplit_01 Main 누락을 확인 중이며 다른 재사용 의존성/정확 필드 readback 감사를 별도 진행한다. 실패 원인을 확정하거나 초기968 전달 자체가 실패했다고 바꾸지 않는다. Native Main은 계속 검증 중이다.

정확 다음은 해당 필드·재사용 의존성/closure 확인 → 필요시 original968을 보존한 최소 추가 전달 revision → fresh Main saved·Monster/Player/Rim/Yetuga 네 RHI → Root Main PNG·MainVisualQA/finalizer다. actual `MainDeliveredAndFreshVerified` 후에만 9문서 완료 절을 추가한다. 원작 shader/pixel parity·unsupported216 및 외부 Player Art17/부모4 HOLD·새 ARCH-86는 별도다. whole author/delivery를 반복하지 않는다. 자세한 현재 증거는 [Art 정본](MONSTER_VFX_PLAYBACK_20261008.md)/[Engineering continuity](../Engineering/ENGINEERING_WORK_CONTINUITY.md)를 따른다.

<!-- PlayerAttackVFXPolish_Actual15Slot5_CutoutCandidate_202610110117 -->
## 2026-10-11 01:17 KST — Spin 경계 producer 확정·원본 구형 마스크 후보 준비

Actual14(PID26548/exit0/128.889611초)의 native capture history와 같은 pose/time/camera template 제외 비교에서 smash_strong 제외만 faint triangle을 제거했다. Actual15(PID18508/exit0/174.257668초)는 해당 template의 공개 GetMaterial/SetMaterial 슬롯10을 각각 비교했고, **source/native slot5 `FMI_World_SubUV_color_A_03` 제외07에서 triangle이 사라짐**을 확인했다. Shock slot0과 World07 slot1은 원인이 아니다. Root가 원본 PNG와 비리샘플 ROI를 직접 확인한 RCA는 `Resume_20261010/RootActual15SmashSlot5RCA_20261011_0059.json`, SHA `7c4e1f124c3fbf8ee97d06562273d62f8b9990151844955f31013c9dbd73346e`다. 이 파일의 visual_review_passed는 원인 확인이며 candidate_quality_approved는false다.

같은 숫자 pose/time/camera·원래 MI 포인터/경로·디스크 해시 복원을 통과했고 제품 저장0/Source/native 변경0이다. 보호된 raw override array의 원래 모양, GPU simulation buffer 및 native 전체 테스트 완료는 이 진단으로 주장하지 않는다. 앞 whole-frame Impact/World07 가설은 정확 ROI 비교 전에 제시한 오판으로 철회하며 제품 수정에는 쓰지 않았다. 원본 wrapper race는 실제 실행한 DriverSource payload의 동일성 supplement로 기록했다.

기존 World 부모는 이미 SubUV.R density×Tex_Opa.R×bounded ParticleAlpha를 연결한다. source03에 StaticParameters가 없고 parent inherited switch default는 미확인이라 switch-only 변경은 철회했다. 원작 Required7은 `CutoutTexture=FT_Sphere_CutOutTex`, `OpacitySourceMode=OSM_ColorBrightness`, `AlphaThreshold=.5`, `PSA_Rectangle`다. native cached T3D에서도 동일 설정을 확인했다. 원본 BoundingGeometry8의 UV 범위가 약.21–.79이므로 rawUV.1 envelope 초안은 무효 가능성이 커 실행하지 않았다. Shock edge 초안도 잘못된 대상이므로 실행하지 않는다.

Root는 기존 World 부모와 source03 child 두 에셋만 보완하는 후보를 선택했다. parent default-off adapter, child03의 기존 Tex_Opa를 원본 구형 마스크로 override, RGB 평균 brightness와 원본 threshold.5로 `sat((brightness-.5)/(1-.5))`를 계산해 기존 density opacity에 곱한다. .5는 원작 직접값, remap 수식/연결은 원작 graph가 stripped된 계산 복원 adapter다. 다른 child default 출력/기존 scalar·switch·blend·시간·입자 수·크기는 보존한다. 현재 초안 준비 단계이며 **새2 저장·Frozen18·Private12·Main 추가 전달은 아직0**이다. Source FT_Sphere는 alpha255 상수라 alpha mask를 사용하지 않는다. source geometry와 native live derived geometry가 같다고 단정하지 않는다.

최신 Main에는 다른 작업의 MonsterVFX Delivered968/alias `UnrealEditor-KhazanMonsterVFX20261008.dll`이 실제 반영됐다. 이를 되돌리지 않으며 현재 Main Source/native/Content와 기존 Player Source3의 정확 보존을 읽기 감사한 뒤 후속 CAS/증거를 재결속한다. 이전 d195/Private11 기술 통과와 Art17/Frozen9b는 과거 후보 증거로 보존한다. 사용자/다른 작업 에디터 제어0이다.

정확 재개: Root 새 구형 mask author 전체 검토·동결→owned hidden editor에서 기존 부모+child만 저장/SM6/기타 bytes 보존→Frozen17 raw archive 및 새18→fresh Private12/Saved12(기존 broad sourceTrue 검사를 source4child로 한정하는 Saved-only adapter)→Root 실제 Spin·Slash·ground·blood·recovery PNG/first-pose 및 양성 효과 보존→최신 external Main CAS/native 선택 보존에 맞춘 Art-only 후속6 전달→fresh Main/Saved/Root/Input13→새 follow-up Completion. v4 helper469/Private12 binder461/Main02 v4 binderfb355 초안은 아직 실행하지 않았다. 원작 shader/pixel parity·shipping 성능 미검증은 유지한다.


<!-- MonsterVFX_AdapterSupplement972_FreshMainPending_20261011012157 -->
## 2026-10-11 01:21 KST — MonsterVFX 혈흔 adapter4 supplement 완료·Main 최종 품질 대기

[Main1/Private1 진단](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Private1/Readback.json)은 Halberd f3af66fe event의 ParticleTemplate만 null인 첫 실패와 consumer316/closure22=동일18+누락4를 결속했다. original Union rerun에서 reused_native=true이나 existing_native_sha256=null인 새 NI→Cascade adapter가 Art457에서 제외된 원인이다. [SupplementalDelivered](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json), SHA `d7487b50…1ed44`로 FP_BloodSplit_01/02·FP_Dmg_Blood_Base·FP_Dmg_Blood_Base_BK exact4를 추가했고 total972=original968+별도4다. 원래968/Art457/6309 영수증은 그대로이며 Source/native/material graph/private package 변경0, 이번 asset copy4·save0이다. 기존 private Saved9/Native10/Player3/Rim12/Yetuga6/RootVisualQA는 private bytes가 불변인 범위에서 유지하고 새 Main 검증을 대체하지 않는다.

[첫 실패 archive](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/FailureHistory/Archive.json), SHA `cc4c51ad…66323`의 MainSaved failed 및 pre-supplement MainMonster Success1560/517.265초는 역사 증거이며 최종 Main 성공으로 쓰지 않는다. fresh MainSaved2는 Exit0/PID30360로 종료됐고 최종 검증은 대기다, MainMonster2는 진행 중이며 아직 Exit이 관측되지 않았다. FinalVerification은 아직 없다. canonical MainSaved가 첫 failed 값이면 archive로 보존한 역사 값이며 새 시도 완료로 읽지 않는다. 기존 QA11 카드 해소/6309 private RootVisualQA 승인 범위를 유지하지만 supplement 후 새 Main 시각 승인과 원작 shader/NI VM·픽셀 일치를 확대하지 않는다.

재개는 실행 중 MainSaved2/Monster2 완료→fresh Main Player/Rim/Yetuga→Root가 실제 PNG의 six-family/ordinary death·D00·Rim·Yetuga 양성을 검토하고 MainVisualQA 작성→finalizer 성공 확인 순서다. [Engineering continuity](../Engineering/ENGINEERING_WORK_CONTINUITY.md)의 exact wrapper 명령을 사용하고 이미 완료된 author/import/initial968/supplement apply를 반복하지 않는다. 최신 ARCH86/GiantFall·외부 Player 구형 마스크 후보와 다른 채팅 prefix는 보존했다. `MainDeliveredAndFreshVerified` 전 최종 완료9문서 쓰기0이다.

## 2026-10-11 — Player VFX Art18의 fresh Private 검증용 의존성 동기화

원래 Player Source3+Art14 Main 전달은 provisional이고, 후속 Art6 전달·최종 완료는 아직 pending이다. 최신 외부 Monster Main 전달 이후 실제 Effects 전체를 비교했으며 Main은 6,335파일/2,495uasset, Private는 5,874파일/2,034uasset였다. 누락은 이전 예상457이 아닌 **461uasset**이고 private-only 파일은0이었다. Config·DAS·uproject는 byte 동일했다. 기존 차이7개 중 선택된 Frozen18의6개 variant는 보존하고, 별도 Monster 전달에 명시된 재사용 WPO 부모1개만608a0ded…→57c664d6…로 동기화했다.

Root가 검토·실행한 [intake receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Resume_20261010/EffectsDependencyIntake_20261011/0fa5250607c04193b03b94e6696ff435/AppliedReceipt.json) SHA `b2498029740ca761eb0133cd6fdb0e330cef7976ba4291d97232e86135d9c194`는461개 추가와 WPO1 exact CAS/원래 Private608 백업을 기록한다. Monster Prepared1e08/Delivered12f3의 같은 ReusedMaterialDependency row·source621·author077을 결속했다. WPO의 density/RGB/DP 연결은 기존 외부 복원 adapter이며 원작 cooked graph를 복원했다고 표현하지 않는다. Shader를 새로 authoring하거나 Source/native/Config/DAS/uproject/Main 제품을 수정하지 않았다. Main 실행 중인 읽기 전용 검사 프로세스를 제어하지 않았고, Private closed guard와 전체 Main Source/Config/Content/Binaries/project CAS가 적용 전후 동일함을 확인했다.

[독립 읽기 검증](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Resume_20261010/EffectsDependencyIntake_20261011/0fa5250607c04193b03b94e6696ff435/IndependentReadOnlyAssessment/b1f10f5e0bd247feb5b0d739d9893f35/Assessment.json)은 실제 Private 전체6,335파일이 Main Effects inventory에 선택6개 Frozen hash만 덮어쓴 정확한 합집합임을 확인했다. 기존 파일 변경은 승인된 WPO1만이고,6개 variant·Source/native 및 기타 보호 파일은 보존됐다. 에셋 수는 파일 인벤토리 결과이며 gameplay 튜닝값이 아니다. 외부 Main Source101/Monster native와 Private 기존 compiled source/native가 서로 다르다는 경계를 유지한다.

다음은 이 정확한 dependency epoch의 fresh Private12/Saved12·Root 실제 화면/first-pose 확인 → V5에 현재 external Main CAS/native와 intake receipt 결속 → Art-only 후속6 전달 → fresh Main saved/runtime/Input13/Root 화면 및 별도 완료 기록이다. 이 intake는 시각 승인이나 원작 shader/pixel 일치·Shipping 성능 검증·최종 완료가 아니다.

## 2026-10-11 01:41 KST — 중단 지점 확정·World03 Sphere private 저장·fresh12 검증 진행

중단된 품질 검사의 정확한 대상은 SpinningAttack02의 강한 내려찍기 `FP_P_World_Pc_Default_smash_strong` source/native slot5→`FMI_World_SubUV_color_A_03`의 삼각형 연기였다. 같은 pose/time/camera/history의 actual15 슬롯 제외 비교와 Root PNG 검사를 `Resume_20261010/RootActual15SmashSlot5RCA_20261011_0059.json`(SHA7c4e1f12…)에 보존했다. 이전 Shock/World07 추정은 철회했고 해당 잘못된 author draft는 실행하지 않았다.

원본 Required7의 `CutoutTexture=FT_Sphere_CutOutTex`, `OpacitySourceMode=OSM_ColorBrightness`, `AlphaThreshold=0.5`를 표적 확인했다. 기존 World 부모의 density Custom에 원래 8입력을 보존하면서 RGB cutout과 threshold 두 입력을 추가했다. 새 부모 scalar 기본0은 기술적 비활성값이고 child03만 원본0.5와 Sphere texture를 opt-in한다. RGB 평균과 `saturate((brightness-threshold)/(1-threshold))`는 공개한 reconstruction 계산이며 원작 stripped shader topology의 직접 복원이 아니다. 기존 Mask.R에도 같은 Tex_Opa override가 전달되는 선택이다. 원본 source CPU 정수 평균과 shader 실수 평균의 경계 차이, live native cutout DDC geometry 미관측, 원본 inherited static default 미확인은 유지한다. child03 native false/overridefalse와 다른 source scalar·particle geometry/수명/크기/수량/시간은 보존했다.

Root가 소유한 숨김 private Cmd PID17284는 60.828초/exit0으로 기존 부모·child03 두 package만 저장했다. 부모 after SHA2b492194…/child03 after92e677ba…이며 SM6 PS204/VS344/sampler6 양수다. 실제 author receipt는 `Resume_20261010/SphereCutoutAuthor/b613935412e348ef9646d4d07898b3a2/SphereCutoutAuthor.json` SHA3b9d1f21…이다. Main 제품·Source·native 쓰기는0이다. Frozen18 SHA660863c6…를 별도로 확립하고 Frozen17과 기존 PrivateReady·원래 전달 receipt를 보존했다.

Fresh SavedPrivate12 PID3600은 116.693587초/exit0, Art18/401구간 검사 passed·asset save0·bytes unchanged다. 실제 shader 컴파일 검사는 통과했지만 화면 품질 승인과 동작 검증은 별개다. 지금 Root의 숨김 `ResumePrivateFinal12` actual RHI18+5 검사가 진행 중이다. 최신 외부 Main Source101/Build19 b84 module 및 원래 Player alias 보존을 `ExternalNativeRebase_RootAccepted_20261011.json` SHAe0e4eb60…에 결속했다. private98/d195는 Art 회귀 예비 증거이고 최종 runtime 정본은 fresh Main 검증이다.

남은 순서: Private12 종료/first-pose/실제 PNG 품질 확인 → 현재 Main closed/CAS의 V5 Art6 선택 전달 → fresh Main02/Saved02, Source101/b84·401/18·first-pose·Input13·화면 검사 → 새 최종 receipt 및 도메인 정본 추가. 실패하면 새 실패 증거를 보존하고 승인 없이 품질 통과로 바꾸지 않는다. 사용자/다른 작업의 에디터를 제어하지 않았다.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — MonsterVFX 전달 대기 해소·최종 인수점

[FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)의 실제 `MainDeliveredAndFreshVerified`로 current6309·최종 선택972/Sequence487/State3342/Death6의 Main 전달·저장/네 RHI·Root 표본 검토를 완료했다. D00/Roar02 양성 및 QA11 shader 준비 후 exact8 bytes 불변의 카드 해소를 확인했다. 신규 alpha-mask 제품 수정은 없다.

후속은 [Art 최종 절](MONSTER_VFX_PLAYBACK_20261008.md) → FinalVerification/Delivered → 현재 Main manifest/alias `UnrealEditor-KhazanMonsterVFX20261008.dll`·selected SHA를 읽는다. 원본499 journal·Art457·Apes/Definition6/Victim43/Shared14·QA7 archived reference를 보존하고 old138/구 alias/전체 author/delivery를 반복하지 않는다. 원작 shader/NI/unsupported216/full pixel parity는 별도 미확인이며 외부 Player follow-up/새 ARCH-86는 최신 CAS로 독립 병합한다. runtime 근거는 [Engineering 최종 절](../Engineering/MONSTER_VFX_RUNTIME_20261008.md)을 따른다.

원본968/Art457의 missing-root-adapter 오류와 첫 MainSaved 실패는 덮어쓰지 않았다. FP_BloodSplit_01/02·FP_Dmg_Blood_Base·FP_Dmg_Blood_Base_BK만 [supplement4](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json)로 추가해 최종972에 결속했다. consumer316/closure22의 나머지18 bytes와 private proof는 보존했고 pre-supplement MainMonster Success는 최종 검증으로 재사용하지 않는다.

확정 근거는 2026-10-11 01:41:38 KST의 FinalVerification SHA `e4b2390f…5b994`, supplement `d7487b50…1ed44`, fresh Root MainVisualQA `1586f77a…e44cd2`(PNG11+targeted6 표본)다. 표본 밖 화면/원작 재구성 한계는 Art 최종 절과 해당 evidence limits에 유지한다.

## 2026-10-11 — Player 공격 VFX polish Main 완료

[최종 완료 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json) 상태는 `ArtFollowupDeliveredAndFreshMainVerified`다. 중단된 Smash slot5 World03 삼각형 연기 보정을 마쳤고 기존 머테리얼6개만 후속 반영했다. 최종 선택 Art18, 최신 Main Source101/b84의 실제 RHI18+Brutal5·FirstPose13·Saved401/8,308필드·Art18 검사 및 Input13 변경0을 확인했다. 이전 Art17/Private11 HOLD·Main followup pending은 이번 범위에서 대체한다. Root 실제 Main9장/264캡처와 원본 수치·adapter·임시 혈액2배 및 남은 작은 glints/gray bands·원작 shader/pixel/Shipping 미검증은 [Art 재생 정본](PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 같은 날짜 마지막 절을 따른다. Source/native/module 선택 및 사용자/외부 에디터는 수정하지 않았다. 기존 기록·receipt·backup을 보존했다.

재개 절차: 완료 receipt→새 Root Main visual/FirstPoseMain02/Input13/actual Main02 Saved·RHI 증거→현재 Main manifest/Source CAS를 먼저 확인한다. 과거 frozen pending 필드나 old14 helper를 현재 상태로 재실행하지 않는다. 후속 원작 룩 비교는 현재18 hash 및 대응 원작 공격 프레임의 특정 MI만 표적 조사한다.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — ARCH-86 Apes·Yetuga / InGame Fall 에셋 분리 author

- 작업 사본은 `C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan`. Main Art/Content 전달은 아직 없다. 기존 MonsterVFX/Player VFX latest 자료와 DeathPresentationMontage 설정을 보존한다. Engineering 계약은 [새 구현 문서](../Engineering/APES_YETUGA_FALL_IMPLEMENTATION_20261011.md)를 따른다.
- 원본 source zip/library/playback event table를 재사용하여 Apes48/Yetuga81 nodes, GA entry19/24, 기존 CharacterDefinition/StateTree/BlendSpace/ABP를 분리 author했다. 원본 시퀀스 재임포트/일괄 PlayRate 교체는 하지 않았다. 플레이어는 InGame/DAS/Fall 및 FallAttack 기존 클립만 사용하고 mesh .01을 유지한다.
- 새 표적 자료: Work `Metadata/GiantCombatFall_20261011/OriginalCommonCurves`의 원본 common movement curve 2개. 기존 closure에 없는 참조에 한정하여 EnemyExtractor metadata로 추출했으며 키/설정 파일은 보고서에 복사하지 않았다.
- Author01–04 실제 저장 성공, Main 전달/원작 완전 동일 검증과 별개다. 첫 PIE의 낙하 상태 PNG는 원래 테스트 카메라가 너무 가까워 포즈 전체 평가에 불충분하다. 이후 native fixture는 saved camera 설정을 바꾸지 않는 review CameraActor로 캡처한다. CloseGrab 물리 표현은 현재 physics asset/Engine PhysicsHandle 어댑터이며 원본 FallDown asset/native 함수가 아니다. Apes projectile mesh는 source 누락으로 Engine sphere 시각 대체다.
- 다음: WorkBuild12 → Author05 → native PIE03/screenshot/조건·취소 확인 → author package list와 latest Main CAS를 대조하여 이 작업의 에셋만 전달 → Main cold readback. 실제 Art 변경 목록·원본/계산/임시 수치·검증 경계는 최종 기록에 추가한다. 타 작업 에디터/완료 receipt를 덮어쓰거나 재실행하지 않는다.

## 2026-10-11 03:08 KST — ARCH-86 선택 Art Main 전달, fresh 검증 대기

- Content151(에셋150+DevMap)을 strict CAS/byte backup으로 Main 반영했다. `Metadata/GiantCombatFall_20261011/DeliveryReceipt.json`, 백업 `Saved/GiantFallBackup_20261011/20261011_030609`를 따른다. 아직 최종 Main saved/RHI 완료 전이다.
- Work PrivatePIE08 및 cold SavedAudit04 성공. 원본 sequence 재임포트/일괄 root/RateScale 수정0. Player .01, enemy1, B Brutal50, 기존 VFX 및 사망 montage 참조, DevMap12마리/대화 짝을 보존했다. Work Definition 두 개의 최신 DeathPresentation 누락은 Main 두 최신 asset을 복사한 뒤 own author08로 보정했고 cold readback에서 실제 참조를 확인했다.
- platform은 사용자 낙하 시험용 Engine Cube1, top1200 cm/Start(-350,0,1292) 임시 배치다. Apes FastBall 모델 원본 누락의 sphere 대체와 original-native MoveTo/잡기/카메라/Spell/shader 동일성 미확인은 계속 남는다. Yetuga pickup marker의 생략 action은 Spawn 추론이며 명시 Use인 다음 throw marker까지 돌을 유지한다. 최초 StepStart 자동 생성/첫 marker Use 해석은 철회한다.
- 재개는 Engineering의 같은 시각 continuity 절을 따른다. 새 hidden Main 읽기 전용 saved 검사와 native RHI PIE를 마친 뒤 실제 확인 경계를 분리 기록한다. 타 작업 전체 author/임포트/에디터는 재실행하지 않는다.

## 2026-10-11 — ARCH-86 선택 Art 전달·Main saved/RHI 확인 종료

직전 pending은 이번 저장/실행 범위에서 완료됐다. `Metadata/GiantCombatFall_20261011/FinalVerification.json`/DeliveryReceipt가 MainDeliveredAndFreshVerified이며 MainBuild02/MainSavedAudit01/MainPIE 전체8사례를 결속한다. Content151·원본 sequence 변경0·기존 VFX/Death/Brutal50/B/12배치 보존을 확인했다. backup은 `Saved/GiantFallBackup_20261011/20261011_030609`. 검사 에디터는 종료됐고 기존 에디터 제어0이다.

원작 전체 재현은 별도 미확인/미구현 경계다. exact 후속은 Engineering continuity/구현 마지막 절의 Yetuga 전용 BT sequence·native MoveTo/잡기·Spell/camera·생략 Spawn CDO 기본값 및 Apes projectile 모델/level binding에서 재개한다. source zip/원본 sequence와 다른 VFX author·임포트를 반복 실행하지 않는다. 재개 전 current manifest/새 사용자 변경과 날짜별 최신 지시를 먼저 확인한다.


## 2026-10-11 — HeinMach 후처리 제거 및 공격 이펙트 재검토 착수

최신 사용자 요청은 기존 룩을 유지하는 보정이 아니라 HeinMach의 모든 authored 후처리·툰/외곽선 제거를 먼저 진행하는 것이다. 이전 Player VFX 완료의 표본은 차지 시작의 굴절 사각 경계 및 OverFury 종료의 VAT 큐브를 충분히 포함하지 않았다. 새 actual RHI에서 두 문제를 재현했고 과거 품질 통과를 이 구간에 확대하지 않는다. 혈액 증량은 데칼 추가가 아닌 분출/비산 파티클을 뜻한다.

`Saved/ImportReports/HeinMachCleanPresentation_20261011`가 새 작업 증거 루트다. PPAudit01: 저장 world `/Game/Maps/L_HeinMach_Environment`, actor9869, active PP8, PostProcessComponent0, 초기 dirty0. PPRemove01은 PP8 및 연결된 지역 룩/툰/외곽선만 삭제하여 actor9861을 저장했고 비PP 전체 actor pose/class 및 mesh/material/light/fog/weather component 설정을 동일하게 확인했다. map SHA `57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7` → `0c887cad2110c867724e1b90b9c0404d4229d18ecadd7c32235b2358b644220d`; 원본은 PPRemove01/Before_L_HeinMach_Environment.umap에 있다. PPColdReadback01은 새 프로세스에서 PP0/component0/actor9861을 확인했다. Sky/Fog/fire/snow/terrain 설정은 유지했다. 엔진 화면 출력 변환·AA와 authored 룩을 구분하며 모든 렌더 연산을 중지했다고 주장하지 않는다.

VFXBaseline01은 현재 Main native의 실제 Ability/Notify18+Brutal5 Success, material fallback0, 354 PNG를 남겼다. 011 Charge에서 큰 반투명 사각 평면, 222/224 OverFury에서 우측 혈액 VAT 삼각형 큐브를 확인했다. `P_kazan_charge_start` slot3의 FM_RefractionShock_01은 현재 ParticleColor RGB/A만 출력하고 Refraction consumer가 누락됐다. Fatalblood slash의 MI_BloodVAT4_1 → M_BloodVAT에는 original MF_VAT_DynamicRemeshing consumer/WPO가 없었다. 원본 VAT tex/mesh/DP Param1 1→90 및 MI manual playback·legacy bounds는 저장된 CombatEffects_20261006 metadata/Precision에서 재사용한다. SideFX 공식 VAT3 decoder 자료는 Saved-only로 받아 git blob/hash를 결속했고 원작 stripped graph 자체와 구분한다. 새 함수가 필요하면 실제 VAT 소비자만 /Game에 복제하고 런타임 플러그인을 추가하지 않는다.

현재 효과 수정은 author/검증 진행 중이다. ChargeVATRepair01은 plugin source duplicate lookup 실패로 save0 종료했고 현재 저장 에셋 수정 증거가 아니다. ChargeVATRepair02는 직접 로드된 function duplicate 방식으로 재시도한다. 후속은 해당 Applied/Exit와 실제 saved hashes 확인 → 차지/OverFury/혈액 mask 보정 및 fresh RHI 화면 → 몬스터 실제 사용 animation의 root-motion flag 감사/수정 → 몬스터 Camera 응답 Ignore → 빌드·cold readback/HeinMach·DevMap 실제 검증이다. 다른 작업 Source/native/DevMap/몬스터 구현을 구버전으로 되돌리지 않는다. Root-motion track repair와 단순 enable flag는 구분한다. 사용자/Rider/타 작업 editor 제어0, 새 hidden task editor만 사용한다.

<!-- HeinMachCleanPresentation_20261011_PPRemoved -->


## 2026-10-11 04:35 KST — HeinMach clean presentation 진행: 최종 RHI 확인만 남음

HeinMach PP8 제거·nonPP9861 보존과 cold map readback은 완료이며 map SHA256은 `0c887cad2110c867724e1b90b9c0404d4229d18ecadd7c32235b2358b644220d`다. OverFury Fatalblood slot2의 M_BloodVAT에는 기존 원본 VAT4 데이터/수동 Param1 1..90을 공식 VAT3 decoder에 연결했다. 최종 그래프 자체는 cooked 원본 복원이 아닌 native rendering reconstruction이다. 원본 MI 숫자/texture 데이터·90프레임 clock은 유지한다. VAT tex point/no mip/no streaming 및 mesh full-precision UV를 적용했고 VFXRepairReadback01의 마지막 실제 flow를 확인했다. 공식 SideFX license는 Docs/Art/ThirdParty/SideFX_Labs_LICENSE.md에 보존했다.

차지 경계는 첫 굴절 수정만으로 해결되지 않았다. FinalVFXPIE02 image015의 실제1.143s에서 경계를 재확인했고, ChargeIsolation02의 actual1.051s slot0만 사각형이었다. FM_Smoke의 미연결 Main_tex/Sub_tex/Dist_tex를 원본 FT_S_StepSmoke_01/FT_S_smokeTile_02/FT_PerlinNoise_RG와 원본 scalar에 연결했다. ChargeSmokeRepair01 컴파일206 pixel instructions/save는 성공, 새 RHI 화면은 아직 확인 중이다. 최초0.773s에서 효과가 보이지 않은 ChargeIsolation01은 경계 제거 증거로 사용하지 않는다.

혈액은 PP_Dmg_Blood_Trail UnitScalar 원본80cm에서 임시 density3인26.6667cm, Sub sprite burst 원본[5,10,5,2]에서 임시[15,30,15,6]으로 조정했다. 기존 density2 대비1.5배이며 원본 시각 확인값이 아니다. source mesh-decal continuous Rate15/s는 임시0으로 만들고 death-event count1와 native 타격 decal notify/timing은 유지했다. FM_MeshDecal의 source box local halfsize2.5 안에서 임시 corner fraction.25/edge feather.08로 각진 투영 경계를 완화했다. BloodPresentation02 최초 Custom pin 오류는 BloodPinReadback01의 reconnect/save/309 pixel instructions로 해결했다.

HeinMachRHI01은 실제world가 DevMap이어서 HeinMach 증거가 아니다. HeinMachRHI02는 명시적 load_map 후9861/PP0/component0/SkyFogLight198/initialdirty0을 검증했으나 AutoExposure=False 때문에 물리 조명 지형이 백색 clipping되었다. 이 trial 설정은 철회했다. config는 Bloom/MotionBlur/LensFlare off 및 LocalExposure contrast1만 유지하고 기본 장면 metering을 복구했다. VFXExposure01은 실제 Particle/Niagara 참조와 기존 Effects root151 중128 Surface emissive에 native EyeAdaptationInverse(alpha default1)을 적용했고128모두 SM6 resource compile/save 양성,23은 기존 보정/zero emissive/non-scene/writer 등으로 제외했다. 색보정/툰 volume은0이며 HDR display conversion/AA와 물리 fog는 남는다. 임의의 미래 color-grade에도 자동 면역인 별도 compositor를 구현했다고 주장하지 않는다.

정확한 재개: Saved/ImportReports/HeinMachCleanPresentation_20261011/FinalVFXPIE03/{Driver,Exit}.json 확인 → Charge1.0s 이후 전체 구간과 OverFury 끝/ground blood 실제 PNG 검토 → `run_editor.py HeinMachRHI03 capture_heinmach_clean.py --pie`로 복구된 metering+inverse 상태의 실제9861 맵 검토 → 역노출128 cold readback·blood rate/burst 및 source montage401 유지 검증 → Art/Engineering 완료 기록. 과거 전체 author/delivery/retime/root repair를 반복하지 않는다. 사용자의 Rider/editor 제어0, task-owned hidden editor만 사용한다.

<!-- HeinMachCleanPresentation_20261011_Exposure128PendingFinal -->

## 2026-10-11 — HeinMach clean presentation 및 공격 VFX 경계 교정 완료

[이번 작업 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)과 [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json)을 우선한다. HeinMach authored PP/툰/외곽선8 제거, 나머지9861 actor/component 및 Sky/Fog/조명198 보존을 fresh canonical-map RHI에서 확인했다. VFX128 emissive root에 역노출 보정을 적용했다. AutoExposure=False trial은 백색 clipping 때문에 철회했으며 기본 장면 metering/HDR/AA/물리 Fog는 남는다.

차지 slot0 smoke의 미연결 마스크와 slot1의 false color-switch 오소비를 교정했고 최종 실제1.1235초 격리 화면에서 두 사각형 제거를 확인했다. OverFury cube는 VAT decode/WPO 누락을 원본 VAT4 데이터+공식 native decoder로 교정했다. 혈액은 이전보다 실제 sprite 분사를1.5배 늘리는 임시 튜닝이며 decal 증가는 없다. 이동 경로 mesh-decal의 source15/s는 임시0/s로 중단했고 마지막 baked cache까지 fresh readback으로 확인했다. source 숫자/임시 숫자·원작 stripped shader 경계는 새 정본을 따른다.


최종 검증: MainBuild02 exit0, FinalVFXPIE03 native18+Brutal5 Success/fallback0/save0, ChargeFinalIsolated03 실제1.1235459초, HeinMachRHI03 canonical9861/PP0/component0, BloodBakedRate01 및 FinalAssetReadback02 cache0/역노출128 fresh 읽기 완료다. 전체 회귀 이후 마지막 두 교정은 focused RHI/cold 검사로 확인했다. 앞선 04:35의 pending 상태를 이 완료 근거로 보충한다. 필수 잔여 작업 없음, 원작 shader/pixel/Shipping 검증은 미확인 경계다.

재개가 필요하면 새 정본과 Completion의 현재 asset hash를 먼저 대조한다. 현재 Main Source/module을 유지하고 새 고유 run 이름으로 run_editor.py <run> capture_heinmach_clean.py --pie 또는 capture_final_vfx.py --pie를 실행한다. 마지막 정적 데이터는 final_asset_readback.py를 사용한다. 기존 author/retime/delivery/root repair를 반복하지 않는다. 사용자/외부 에디터 제어0, 작업 background editor는 모두 종료했다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->

## 2026-10-11 — CombatPresentationFix Art 진행 중

최신 Main의 PP0/9861 actor/기존 exposure inverse128, charge mask/VAT 수정을 보존한 별도 Work 에디터에서 진행한다. 증거 루트는 `Metadata/CombatPresentationFix_20261011`이다. Main 에셋은 아직 이번 요청으로 변경하지 않았다. 원작 효과의 source 창/transform/lifetime/velocity/color는 기존 CombinedPreparedPlaybackPlan 및 CombatEffects metadata를 우선 재사용한다. 증량/검붉은 tint/혈흔 경계/조명 숫자는 사용자 스타일 요구에 따른 어시스턴트 임시 튜닝으로 구분한다.

현재 공유 혈흔 sprite는 66개 burst, Trail UnitScalar 80/3cm, continuous mesh-decal rate editable/baked 0, death event Frequency3이다. alias4의 size cache min/max0만으로 투명하다고 결론 내리면 안 된다: 실제 child constant size는 유효하다. 바닥 projection은 이미 authored/random XY를 보존하므로 runtime XY 수정은 하지 않았다. Work의 private AuthorVFX에는 기존 physical sprite를 alias4에 추가, DAS 전용 slash variant 1개와 sprite 증량/8 montage 해당 template 교체를 작성했으나 아직 빌드/실행 전이다. 반복 실행하면 증량 중복이므로 먼저 VFXAuthored/실패 로그와 저장 파일을 확인한다.

눈은 사용자 지정 layer40cm로 DeepSnow만 바꾼 `SnowBake/Settings40.json`에서 기존 정확한 contact baker를 재사용해 profile2/4,783,236 bytes를 생성했다. 다른 36/18cm layer는 보존한다. Work Source는 foot35/40, weapon1 및 PlayerCapsulePaddingCm15를 추가했다. 15cm는 현재 capsule contact 경계 밖에 더하는 해석(선택 질문 대기 후 알린 가정)이며 전체 반경15cm로 사용자 확정되면 변경한다. 아직 material2/actor contact profiles/map 저장과 Snow.PIE는 수행 전이다.

HeinMach 기존 조명은 Sun7000/Sky1이다. PP volume을 다시 추가하지 않고 기존 Sun/Sky를 조정한다. `HeinMachBefore01`이 canonical map의 동일 카메라 RHI 전 화면을 촬영 중이다. 완료/Exit 확인 후 material/snow/map/light author → 후 화면 비교와 VFX 실제 frame 확인 → 기존 Main SHA 비교/선택 전달/새 프로세스 cold readback 순서다. 조명·증량은 원작 직접 확인값으로 기록하지 않는다. 작업 완료 기록은 이 중간 절을 삭제하지 않고 하단에 추가한다.


## 2026-10-11 ? Combat UI ?? ??/??? ??

Metadata/CombatUI_20261011? targeted index ? widget13 ? referenced resources41 ? parent7/input4/fontface1? ????. ?? texture24? PNG ? ?? UI ??15?? Content/UI/Combat/Textures? ?????. Import01.json? ImportEditor01 exit0, TextureContactSheet/ExecutionIconInspection? ???. ?? ??? SourceWidgetAudit.json ? ?? JSON??. ?? LockOn ???? T_Fx_TargetLock, legacy execution? ? X, Xbox B? T_Icon_XB_B?. ?? preset A Interaction(Gamepad_FaceButton_Right), ???? ?? B binding? ???? X ???? B ????? ???? ???.

Cooked UI shader graph/?? native interpolation ??? ? FontFace bulk? ?????. UI material2? ?? ?? texture? radius/color? ??? explicit adapter?? ?? shader ?? ??? ???. ??? Engineering fresh Main PIE ?? ??/??? ????? ?? ?? ????. ?? Art/VFX/Animation/Level asset? ?????? ???. UI source/???? ?? ?? ??? ????.
## 2026-10-11 — UI 저장/실제 실행 통과 및 미전달 후속 Main 반영

원작 UI texture16·material2·원작 Medium FontFace1·WBP_CombatHUD와 monster BP6/controller BP1은 Main에 저장했다. `CombatUI_20261011/PIEEditor03` 실제 RHI 전체 UI 검사와 Exit0이 완료됐다. 상세 출처는 `COMBAT_UI_SOURCE_AUDIT_20261011.md`다. 일부 이전 중간 절의 문자 인코딩 손상은 이 UTF-8 추가 기록으로 보충한다.

미전달 CombatPresentationFix를 재개해 원본 physical blood sprite를 실제 material/type으로 선택하고 Cascade sibling module 참조를 engine whole-system duplicate로 함께 복제했다. VFXAuthorResume03에서 blood4/DAS variant1/core6/montage3 저장, 기존 이벤트36개 재연결이 통과했다. 기존 source timing/lifetime/pose를 보존하며 sprite 증량2배 및 tint(1,.12,.08)은 어시스턴트 임시 표시 튜닝이다. 다른 기존 monster VFX/최종 death-decal Frequency3/charge mask/VAT repair를 구버전으로 덮어쓰지 않았다.

SnowAuthorResume01은 material2/map만 저장해 눈 최대40cm/발35cm/weapon cap, 기존 해석 padding15cm/profile2를 적용하고 PP0·actor9861·전 actor pose를 보존했다. Sun7000→5000/Sky1→1.1은 하이라이트와 암부 가독성을 위한 어시스턴트 임시값이다. 선택 Content19/Source8은 backup+SHA/CAS로 Main에 전달했다. receipt는 `Metadata/CombatPresentationFix_20261011/MainResume/DeliveryReceipt.json`이며 UI 보호 파일36개는 byte 동일하다. Main build/새 read-only 저장 검사까지 통과했고 실제 Main 전투·설원·같은 카메라 화면 및 UI 회귀 확인을 진행 중이다.
## 2026-10-11 — UI·미전달 Art Main 최종 종료

필수 잔여는 없다. UI final PIE05/fallback0 및 MainVFXResume02 native18+Brutal5/392 captures/fallback0/Exit0, Snow actual/동일 카메라3/actor9861/PP0/save0을 완료했다. current asset/native SHA와 backup은 UI FinalVerification 및 CombatPresentationFix MainResume FinalVerification이다. 기존 source timing/geometry/material 및 최종 VAT/charge/혈흔 수정을 유지했다. 재개는 Router→해당 Art 정본/knowledge/source report에서 시작하며 전체 재추출/중복 증량 author/과거 private 전달을 반복하지 않는다. 두 [UI](COMBAT_UI_SOURCE_AUDIT_20261011.md)/[후속](COMBAT_PRESENTATION_FOLLOWUP_20261011.md) 정본의 원본·계산·임시 수치 및 검증 경계를 유지한다. owned editor는 모두 종료됐다.

## 2026-10-11 — B 인디케이터 알파 경계 후속 진행

사용자 요청은 B 표시 테두리의 부드러운 알파 처리다. `BrutalAlphaInspect01/AlphaInspection.json`에서 `M_UI_BrutalRing`의 opacity ComponentMask가 R/G/A를 함께 선택한 사실을 확인했다. 원작 B PNG는 RGBA64×64이며 네 모서리 alpha0, 기존 임포트도 compression_no_alpha=false다. B 픽셀을 다시 추출/가공하지 않는다.

다음 절차는 `Scripts/Art/soften_combat_ui_brutal_alpha_20261011.py`를 own Main commandlet에서 author mode로 실행해 A-only와 inward feather를 저장하고 새 own RHI UI PIE를 확인하는 것이다. 기존 editor PID13416을 제어/저장/종료하지 않는다. source radius .49/.38·색은 보존하며 EdgeSoftnessPixels1.25는 사용자 스타일 요청에 따른 어시스턴트 임시 표시 튜닝이다. 정확한 결과와 backup은 `Metadata/CombatUI_20261011/BrutalAlpha*`에 남긴다. 실행 UI/게임플레이 Source 변경은 없다.

## 2026-10-11 — Player/Monster/HeinMach 원작 사운드 작업 시작·중단 재개점

사용자는 FModel chunk0/chunk1 모두에서 필요한 음원과 metadata를 추출·임포트하고 현행 Player/Monster6 행동·상호작용 및 HeinMach 환경음을 실제 타이밍에 연결하도록 직접 요청했다. 최신 Main의 Sky/Fog와 후처리 제거·공격 VFX 보정, root flags·카메라 변경을 보존한다. 원작 숫자를 우선하고 미확인 audio 튜닝은 TEMP로 분리한다.

현재 FModel GAME_UE4_27/DesktopMobile provider와 active GameDirectory/AES를 로컬 설정에서 재사용한다. AES는 출력/문서에 쓰지 않는다. 설치 paks는 pakchunk0-WindowsNoEditor.pak(29,171,917,980 bytes), pakchunk1-WindowsNoEditor.pak(21,454,569,878 bytes), tiny optional chunk0다. 기존 sound 지식/구현/UE Sound assets는 발견하지 못했다. 기존 EnemyExtractor index에서 sound 관련23536 package를 얻었고 원작 xxAnimNotify_AkEvent를 cached BindingSource에서 확인했다. 초기 중단은 이 read-only discovery 단계였고 음원 추출/임포트/runtime 수정0이었다.

현재 추출 도구에 audio-api/audio-index inspection을 추가하고 build·실제 archive owner/음원 데이터·Event→media→timeline을 확인하는 중이다. 증거는 Saved/Extracted/GameplayAudio_20261011/Index01, Saved/ImportReports/GameplayAudio_20261011/ResumeState.json 및 Before에 보존한다. 아직 완성/원작 음향 일치를 기록하지 않는다. 재개: tool build/API dump→archive별 audio index→현행 행동 source notify와 HeinMach sound actor metadata→필요 event closure만 extract/decode→품질/끝음/볼륨/reverb 계획→import→기존 실행 owner에 연결→별도 background editor build/saved/native audio 검증. 기존 전체 mesh/VFX authoring이나 과거 private Source 전달을 반복하지 않는다.

<!-- GameplayAudio_20261011_DiscoveryCheckpoint -->

## 2026-10-11 — B 알파 수정 Main 반영 / 마지막 실제 UI 검사 진행

Main 에디터의 파일 잠금이 외부에서 풀려 `BrutalAlphaMainDelivery/DeliveryReceipt.json`의 단일 패키지를 hash CAS/atomic replacement로 전달했다. 현재 `M_UI_BrutalRing` SHA는 `c4d6ff781af4bdf9955722e698aae2b382e359949b771df91ff54c30e4039100`이다. 원작 B texture/기존 radius·색·gameplay Source와 Main DLL SHA c908da8696b7844df39c7d476aa3ea8c10b96d206137b359c9252940d13c98bf는 유지했다. 사용자의 Main PID13416/25612를 저장·종료·제어하지 않았다.

마지막 완료 검증은 StageRHI01의 실제 저장본 A-only/EdgeSoftnessPixels1.25/compile0/fallback0/save0/Exit0이다. own Main RHI PID15588은 `BrutalAlphaMainPIE01`에서 실제 저장본으로 기존 Khazan.CombatUI.PIE를 실행 중이다. 재개 시 이 폴더 Launch/PIEDriver/Exit를 먼저 확인하고, 아직 own 프로세스가 살아 있으면 중복 launch/author를 하지 않는다. native Success 및 shader fallback0/Exit0 뒤 final receipt와 Art 상태/이 문서 하단에 완료를 추가한다. 실패하면 해당 Editor.log의 정확한 오류만 표적 확인한다. 전체 UI import/이전 background delivery/캐릭터 C++ build를 다시 실행하지 않는다.

## 2026-10-11 — B 알파 부드러운 경계 후속 종료

필수 잔여는 없다. `BrutalAlphaFinalVerification.json` status는 MainDeliveredAndFreshVerified다. Main 단일 material SHA c4d6ff…와 A-only/feather1.25를 fresh saved inspection/실제 Khazan.CombatUI.PIE Success/fallback0/Exit0/직접 B 화면 검수로 확인했고 다른 UI 제품36개/current DLL은 기존 hash와 동일하다. own editor PID15588은 정상 종료됐다. 사용자 editor 제어·저장·종료는 하지 않았다.

정확한 재개 조회는 Router→UI Art 정본 마지막 B 알파 완료 절→위 final receipt→실제 Main material이다. 완료된 author/preview/전체 import/이전 Main delivery를 다시 실행하지 않는다. 더 부드럽게 조정하는 새 요청이 오면 기존 material의 EdgeSoftnessPixels만 표적 검토한다. 원작 glyph/radius/색과 임시 화면 미분 feather를 계속 구분한다. 이번 완료는 원작 stripped shader의 완전 복원을 뜻하지 않는다.


## 2026-10-11T23:25:56+09:00 — 사운드 재개 checkpoint: 음원·native cue 변환

최신 사운드 요청을 계속 처리 중이다. chunk0·chunk1 실제 archive index와 기존 source metadata를 재사용했고 NativeCuePlan01은 cue473/decoded media1600이다. 한국어 언어ID3721600213/kz 분기, source gain·delay·random playlist weight·layer와 source physical surfaces17종을 확인했다. 발소리 layer의 duplicate230 속도 key를 보존했다. source Wwise step-sequence는 한 post에 한 항목이므로 source75 전체를 concatenator로 이어 재생하지 않는다; native one-item shuffle bag은 원본의 순차 순서와 다른 명시적 adapter다. 원본 gain/끝음을 normalize/trim하지 않고 PCM16으로 보존했다.

NativeImport02는 파형1600/cue473 저장 뒤 voice concatenate75>UE max32가 검출되어 exit1이다. 전체 완료가 아니다. 수정 뒤 NativeImport03이 진행 중이다. 현재 Animation/HeinMach map author는 아직 전이며 기존 PP0/최근 Snow40cm·UI/낙하/Brutal을 되돌리지 않는다. exact 재개는 Saved/ImportReports/GameplayAudio_20261011/ResumeState02.json 및 NativeImport03/Exit.json·Import.json/FinalizedCues473 → author plan645sequence/2146notify → 환경39source·현재fire·native reverb → fresh saved/실제 audio PIE다. 기존 전체 추출을 반복하지 않는다.

## 2026-10-11 — 몬스터 표현·UI 후속 작업 진행 checkpoint

이번 직접 요청의 정본은 MONSTER_PRESENTATION_REPAIR_20261011.md, runtime·실패·exact resume는 Engineering continuity의 ARCH-88 마지막 절이다. Source 원본 Attack198/1577를 재검사 중이며 floor blood decal42/16 receiver만 제거하고 slash/chunks를 보존했다. Private QuickVisual01에서 blood actual particles0이 발견되어 완료 전 수정 중이다. Noise grayscale sampler/기존 RGB와 A output 보존은 해결했고 late dissolve PNG에 몸/무기가 점진 소멸함을 확인했다. Main 적용은 아직0이다.

동시 사운드 Animation24 변경을 보존하여 Work에 다시 staging했다. 이 파일에 혈흔 Effect None만 재적용하고 saved audio Notify를 함께 검증해야 한다. 새 blood192개·lifetime1.2s·size1.4–3.5cm, ash world velocity와 size 등은 어시스턴트의 임시 표현이며 원작 직접 확인값이 아니다. 원작 UI gradient Mid0.8/alpha0.35·0.2·0.1과 project frame124x22 임시 크기를 구분한다. 마지막 완료/메인 적용은 fresh RHI와 실제 입자/화면 검수 뒤에만 기록한다.


## 2026-10-12T00:17:33+09:00 — 사운드 영구 wave 참조 수정 / 실제 출력 검증 대기

NativeImport05_PersistentWaves는 원본 gain/끝음 보존 PCM1644·native cue480을 저장하고 exit0이다. SoundNodeWavePlayer.SoundWave는 transient 캐시라는 엔진 원인을 확인해 editor finalizer에서 SetSoundWave를 호출하여 SoundWaveAssetPtr도 영구 저장한다. AudioPIE01은 실제 notify dispatch·취소·loop cleanup은 통과했지만 녹음 peak0이므로 청음/실제 출력 완료로 주장하지 않는다. 원인은 새 프로세스의 LoadAsset에서 비어 있는 soft pointer로 transient 캐시가 사라지는 것이다. 현재 원본 480 cue 재저장 완료, 환경 wrapper는 새 source cue에서 재구축 중이다.

NotifyAuthor01의645 sequence/2146 event와 기존 non-audio notify 보존은 실제 저장 완료다. HeinMach EnvironmentAuthor01은 원본39 actor·현재 불 FX 기준 fire·native reverb13을 저장했고 기존9861 actor transform/class를 그대로 보존했다. PP0/Snow40cm/Sky/Fog/UI와 다른 task editor는 변경·조작하지 않는다. exact 상태는 Saved/ImportReports/GameplayAudio_20261011/ResumeState03.json이다. 다음은 BindingAuthor02_Persistent 종료→새 source reference/실제 nonzero mixer·환경·fresh saved 보존 검사→최종 문서다.

## 2026-10-12 00:18 KST — 검붉은 피 실입자 확인·디졸브 입도 보완

private QuickVisual04에서6종 모두 검붉은 피 실입자115–192개와 black ash630개를 확인했고 Blood_HalberdElite/late death PNG를 직접 검사했다. 이전 blood0 실패는 원본 LOD disabled를 저장 캐시가 되살리던 엔진 동작이 원인이며 SetupSoloing을 통해 실제 저장을 수정했다. floor receiver16/42 Notify producer 제거와 slash/chunks 보존은 유지한다. Main 적용은 현재0이다.

원작 FT_Noise_Dissolve를 corpse opacity에 쓰되 화면의 큰 덩어리를 줄이는 KZDeathNoiseTiling=6 임시 UV 배율을9 master에 저장했다(DissolveGrain02 passed). shader Linear Grayscale을 유지한다. 원작 native 숫자라고 표현하지 않는다. QuickVisual05와 fresh Main 전체 검증이 남아 있다. 자세한 실패·병합·정확한 재개는 Engineering ARCH-88 마지막 절과 Metadata/MonsterPresentationRepair_20261011에 있다. 동시 audio24 animation의 GUID/timing/property는 MainBefore/Work02 census가 완전히 동일하다.

## 2026-10-12 01:01 KST — Main 표시 수정·검증 종료

FinalVerification.json status는 MainDeliveredAndFreshVerified다. 실제 Main Source10/asset59와 최종 해시·백업·각 실제 loaded DLL을 결속했다. MainRuntime02의198/1577 및6종 normal/paired death/live blood/live ash/MID progress/Destroy, actual accepted-hit13 case, HalberdElite actual UI2가 Success/fallback0/Exit0이다. attack PNG192개/contact sheet8장, blood/ash/late death18장, UI02 damage/normal ring/B 화면을 직접 검사했다.6 component 없는 clip도 native/saved 검사에 포함했다. 원본/런타임 동명 파일 덮어쓰기와 raw root-travel QA 카메라는 검사 코드에서만 보완했다.

최신 MainSavedAudit02 save0은 혈흔 producer42의 Effect None, source geometry198/1577, chest6/skeleton5, corpse master9/P0/tiling6/Linear Grayscale/UI gradient를 확인했다. 동시 사운드24 animation의67 audio Notify는 후속 작업으로 GUID가 재생성됐지만 MainAfter02의 나머지 event field·timing·playback·sound/stop 값은 동일하다. 최신 파일을 보존했고 우리의 바닥 혈흔 제거/사망·UI 계약도 유지했다. 모든 관련 TEMP 숫자는 바로 위 표의 출처 상태를 유지한다.

이번 요청의 구현·Main 검증 필수 잔여는 없다. 재개 근거는 이 정본 마지막 절/Engineering ARCH-88 완료 절/FinalVerification.json이며 완료된 전체 author/import/private copy/alias 복원을 반복하지 않는다. source shader/native correction52의 완전 복원 및 원작 pixel/frame parity·Shipping 성능은 미확인으로 구분한다.


## 2026-10-12T01:30:45+09:00 — 사운드 실제 출력·원본 시간축·HeinMach 검증 checkpoint

사운드 에셋은 Native PCM1644/원본 cue480/ambient wrapper10이다. 최종 SavedAudit05_Final에서490 cue/4663 영구 wave 참조,645 pose·curve GUID/RateScale/root/non-audio notify와2163 authored timing 및7 body Definition을 새 프로세스로 확인했다. 처음 계획의 DilationCurve.SourceDilationCurve만 읽던 누락을 원본 Properties.DilationCurve.DilationAnimPositions와 저장 import의 실제 적용 여부로 고쳤다. 원본 raw1.4973173→current1.9651953, raw end1.8423244→2.329393927592745는 T_Original→T_Dilation의 구간 선형 계산 예다.994 clock 수정/17 유효 occurrence 추가이며 pose 재임포트·리타임0이다. BeforeDilationFix plan과 최초645 byte backup은 보존했다.

SourceFadeAuthor03은 원본 CAkActionPlay.idExt·target media closure와 TransitionTime ms/1000으로18 source fades/13 cue 및 dependent wrapper1을 저장했다.16 Linear는 직접 선형 변환, Log1/Exp1 두 shape는 임시 sqrt(t)/t² native adapter며 duration만 원본이다. SoundNodeWavePlayer의 transient 캐시와 영구 SoundWaveAssetPtr를 구분해 setter로 저장했다.

AudioPIE06_FinalTimings의 Player+monster6/cancel8 녹음은 모두 nonzero/새 clipping0이다. EnvironmentPIE04_RHI의 실제 listener7 구역·출력·reverb는 passed다.134 ambient=source39+placed fire95, reverb13, 기존9861 actor transform/class/label과PP0를 유지했다. nullRHI에서는 listener가0에 머물러 유효 공간·mixer 검사가 아니었으므로 RHI 결과로 대체한다. 원본 auxiliary identity·bounds와 새 native DSP/voice budget/반복 delay/총량 headroom 임시값을 구분하며 SDK/pixel/sample 완전 동일성은 주장하지 않는다. 현재 실제 gameplay 회귀만 진행 중이며 exact resume는 ResumeState04.json이다.


## 2026-10-12 ? Player JustGuard ?? Art checkpoint

??? ?? ?? ?? ?? ?? ??, ?? ??????? ?? ?? ???. ?? DAS extraction/index?? JustGuard? ??? SB/AC/PP_Damage_Spray ??? ???? Flow stance Parry? ????. Metadata/Parry_20261012/OriginalEvidence.json, Probe01? source/current saved readback??. ?? task-private Guard/GuardParry writable copy? ????.

?? ?? source/?? ?? ?? ??, ?? authoring?Main ???RHI ??? ????. ??? source DilationAnimPositions? Just_L/R ??? InGame .3666667? grid? ?? bake??, ?? Guard montage/GA? append??. ?? JustGuard particle? ???? ?? referenced local MI/master? UV edge alpha? ????. ?? tint/texture/distribution ? ?? master? ????. edge ??? TEMP? ???? ?? ?? frame/??/?????? ???? ????. ?? Combat UI/Monster/?? Audio ??? ?? ???.


## 2026-10-12T02:04:36+09:00 — 원작 사운드 재개: 저장 배열 누락 수정본 검증 / Main 잠금 대기

chunk0/chunk1의 실제 audio index 104178파일/23359 uasset를 확인했고 chunk1의 sound package2도 조사했다. 음원은 chunk0 소유다. source bank/event/game-sync/aux와 현재 source notify는 저장 metadata/report를 재사용하며 전체 리소스를 다시 조사하지 않았다. 한국어 KR 분기를 사용했다. Native decoded WAV1644는 원본48kHz/채널·gain·loop·끝음을 보존하는 PCM16이며 normalization/tail trim/추가 lossy encode0이다. 원본 PCM의 clipping4153 samples는 보존했으며 새 믹서 clipping과 구분한다. 현재 Audio/Original 에셋2147은 source cue480/wave1644+timing silence1/ambient wrapper10/native reverb6/기타 settings6이다.

645 sequence의 KZAudio point1958/state205 총2163 event는 saved import contract의 실제 dilation 여부와 원본 T_Original→T_Dilation piecewise linear table로 현재 baked clock에 한 번만 계산했다. 원본 CAkActionPlay TransitionTime(ms)/1000의18 fade는16 Linear와2 Log1/Exp1을 구분한다. 후자의 sqrt(t)/t² shape는 명시된 native 임시 근사다. 숫자/package/field/원시값·hash는 AudioAuthoringPlan01/PlaybackPlan/SourcePlayFadePlan01/NativeCuePlan01/SpatialAudioPlan01/ProjectileAudioPlan01에 보존했다. bank→media recipe는 엔진 최대32 child 기술 제약에 맞춰 그룹화했다. SoundWaveAssetPtr의 영구 참조4663개는 fresh process에서 검증했다.

중단점의 검증 중 이전 Python 배열 iteration으로 바꾼 구조체 사본이 배열에 재기록되지 않아37 ComboDefinition의 ImpactSound/GuardSound/ProjectileSound가 None으로 남은 것을 발견했다. index별 windows/nodes/pattern_objects 재대입으로 수정했고 모든 비오디오 export field를 전후 대조했다. 수정본은 BindingRepair03_Prepared/Prepared/Content에 있다. SavedAudit06_PreparedBindings가 player impact61/monster guard405/object guard4/projectile2 및 기존645 pose·curve GUID/RateScale/root/non-audio notify 보존을 새 프로세스로 확인했다. 새 AudioPIE07_PreparedProjectile은7 family+cancel8, original source loop 정리, 실제 Shoot/Impact의 두 비행음 녹음이 nonzero/clipping0으로 통과했다. 투사체의 source state Rock/Snow와 duration1.6503333/1.536s, source event maximum radius3000/5000cm를 보존했다. original SoundData.ProjectileRTPC80/60·SphereRadius2000의 원작 native 제어 의미와 global RTPC 완전 재현은 미확인이다.

Main HeinMach 환경음은 source actor39+기존 fire FX anchor95=134 ambient와 reverb13을 이미 저장했다. EnvironmentPIE04_RHI의 숲/절벽/동굴/보스룸/배치 fire7 실제 listener·reverb 출력은 passed/새 clipping0이며 기존9861 actor class/label/transform/PP0와 최신Snow40cm/Sky/Fog/UI를 보존했다. native reverb·총량 headroom·repetition·voice budget은 어시스턴트 임시값이다: SC_Original gain0.5(-6.0206dB), SFX64/Ambient24/Fire8, character wet send0.05–0.15, finite ambience12–28s, fire gain0.35/pitch0.99–1.01, cave3.2s/boss2s/outside0.35s/volume0.30·0.08/fade1.5s. 전체 native reverb parameter profile은 EnvironmentAuthor01/Environment.json과 author script에 있으며 원본 Wwise aux/room bounds와 구분한다. source attenuation point97의 normalized distance=distance_cm/max_radius, scaling2 gain=To+1을 사용하되 nonconstant curve의 native linear 보간은 근사다. source random avoidRepeat1의 native bag 및75 one-post/one-item sequence의 bag은 원본 전역 순서와 같다고 주장하지 않는다.

**Main37 수정 바인딩은 아직 미반영이다.** 새 Rider Main PID19752가 파일을 잠그고 있어 Delivery01의37행은 모두 Windows error32로 대기하며 saved hash 충돌0이다. 사용자 에디터 제어·저장·종료0이다. 수정본 검증을 Main 완료로 표현하지 않는다. source music fallback12는 자동 BGM으로 재생하지 않았고 미확인 parent source8/above-surface layer58/비사용 projectile switch3/native DSP·global RTPC·plugin tone output/Shipping 성능은 한계로 남긴다. 완전 SDK/IR/sample parity를 주장하지 않는다. 재개 근거는 PreparedVerification01.json과 ResumeState05.json이다.


## 2026-10-12 — 사진 기준 Monster 혈액/지면 혈흔 후속 진행 checkpoint

사진/원본 packed RGB texture 표적 검토와 Work 혈액3층/새 재질2 저작이 끝났고 Main 전송 전이다. 최신 floor blood 제거 지시는 이번 사진 요청 범위에서 대체한다. 사망/UI/사운드/낙하 설정은 되돌리지 않는다. WorkBuild04가 외부 ParryWork의 UBT mutex를 기다린다. 외부 editor/build를 종료하지 않는다. 지금 Main에는 DEV 검사2파일만 수정했고 제품 runtime2는 Work에만 있다. 마지막 검증·실패/대기 원인·정확 재개 명령/다음 범위는 Metadata/MonsterBloodReference_20261012/ResumeState.json을 따른다. ParticleAuthor02는 fade 수정 전 DLL의 성공이므로 최종곡선 저작 완료로 읽지 않는다. Baseline/Before bytes와 이전 작업 FinalVerification은 보존한다.


## 2026-10-12 — Player Parry 준비본과 alpha 검사 정정

원작 Just_L/R composite의 반대 이름 raw sequence 참조, DilationAnimPositions 31개를 사용한 22/60초 bake, PP_Damage_Spray.NewJustGuard→PP_AtkEx_JustGuard의 13 emitter, 기존 원작 성공 cue를 연결했다. 새 motion2/particle1/master3/MI5=11개와 기존 Guard GA/Montage2개가 준비본이다. 정확한 package/SHA·수치·현재 검증 범위는 [PLAYER_PARRY_SOURCE_20261012.md](PLAYER_PARRY_SOURCE_20261012.md)에 기록했다. 공유 원본·Audio Notify·다른 작업은 저장하지 않았다.

최초 어두운 effect preview의 검은 원판은 shader 결함이라는 가설과 달리 검사 전용 빈 GameModeBase 맵에 생성된 **DefaultPawn_0의 구형 메시**였다. AlphaPreview06의 hidden_fixture_pawns에 origin(0,0,0)을 기록했고 이 Pawn만 숨긴 실제 RHI 캡처에서 원판이 사라졌다. AlphaPreview01–05 및 Isolate03은 그 fixture가 가려 외관 합격 근거로 사용하지 않는다. 보호된 LOD property를 직접 변경하려던 Isolate01/02는 API 실패로 끝났으며 task-owned process만 정리했다.

불필요한 local5 MI의 Additive 통일과 black-emissive gate는 AlphaFinalize02에서 철회했다. 모든 MI의 원본 base-property overrides를 복원했으며 particle의 13 emitter를 모두 유지했다. local3 parent의 continuous opacity와 0.04 UV / 최소1.25px edge feather만 유지한다. untextured DefaultParticle spark는 elliptic alpha와 ParrySparkSoftnessPower=2로 모서리·끝을 부드럽게 했다. 이 세 수치는 원작이 아닌 어시스턴트 임시 표현 값이다. root shader/source pixel parity·Shipping 성능은 미확인이다. 최종 preview/saved readback 결과는 PreparedVerification과 하단 후속 기록을 따른다.

**Main 에셋 반영은 잠금으로 대기한다.** 다른 에디터/채팅은 제어하지 않았다. 재추출/전체 author를 반복하지 않고 DeliveryPreflight/ResumeState의 대상만 SHA 확인 후 복사하고 fresh Main saved/RHI를 검증한다.



## 2026-10-12 — 패링 최종 준비본 검증 확정 / Main 2개 잠금 유지

최종 Build08/PIE03(15 case 및 6종 Definition)/SavedAudit03/AlphaPreview07는 Exit0·passed다. native 실제 loaded module SHA는 PreparedVerification.json에 있고 현재 준비 Source7은 Build08 input과 동일하다. Gameplay 제품 Source6은 앞서 성공한 GuardRegression01/CollisionRegression01과 같은 코드다. source MI base-property overrides가 복원된 saved reload, DefaultParticle ellipse power2와 .04 UV/1.25px edge 연결을 확인했다. 실제 game viewport의 .13/.24초 효과 및 dark RHI burst를 직접 열어 원판·불투명 card 경계가 없음을 확인했다. Source shader/pixel 완전 일치와 실제 스피커 출력/Shipping/network 검증을 완료한 것은 아니다.

**Main product Source/package 변경0, 적용 완료가 아니다.** 마지막 preflight는 대상 SHA 충돌0·GA_Player_Guard/AM_DAS_Player_Guard의 Windows error32 2개다. 기존 Main editor PID19752가 계속 실행 중이다. 사용자에게 작업 저장 후 종료 상태만 요청했고 에디터를 임의로 종료하거나 잠금 handle을 강제로 닫지 않았다. exact resume는 Metadata/Parry_20261012/ResumeState.json, review diff는 PreparedSource.patch다. 잠금 해제 이후 해당 Source7/asset13만 반영하고 fresh Main build/PIE/audit를 추가한다. 전체 저작/추출과 과거 DLL 복원은 반복하지 않는다.


## 2026-10-12 — 사진 혈액 후속 Main 적용 / 첫 피격 shader 검증 중

초기 ResumeState.json의 Main 미반영 기록은 이 절에서 대체한다. runtime2/DEV2와 유효 신규 혈액 package5는 Main 반영됐고 사용 안 하는 초기 package2는 원본/무참조 SHA 확인 뒤 task backup으로 옮겼다. MainBuild10(2026101249)은 성공·input 동일이다. MainSnowVisual04는6종/지면 수명 정책을 통과했지만 QA가 셰이더 완비를 강제한 검사이며 최종 색 이전이다. 첫 검은 사각형은 ODSC 부분 shader map의 fallback이었다. 기존 Monster BeginPlay의 background cache 보완 뒤 강제 warm 없는 MainSnowVisual05와 fresh MainSaved05가 진행 중이다. 마지막 검증·실패 원인·현재 정확한 own PID/남은 검사/재개는 Metadata/MonsterBloodReference_20261012/ResumeState02.json에 있다. 사용자 PID19752/foreign editor 제어0, 사운드/패링 준비본을 덮어쓰지 않았다. 이전 전체 author/delivery 및 archive 스크립트를 다시 실행하지 않는다.


## 2026-10-12T04:22:44+09:00 — 사진 기준 몬스터 혈액·지면 혈흔 Main 완료

Main runtime2/DEV2/신규 유효 package5·build2026101254·fresh saved/CDO6·실제 눈 RHI6종/24혈액·12소멸/지면 lifetime·actual collision13을 완료했다. 이전 ResumeState/ResumeState02의 pending은 이 절에서 대체한다. 정확한 현재 SHA/loaded module·수치 출처·한계는 Metadata/MonsterBloodReference_20261012/FinalVerification.json, 다음 절차는 ResumeState03.json과 MONSTER_PRESENTATION_REPAIR_20261011.md의 최신 사진 완료 절을 따른다. 첫 shader fallback/몸 안쪽 발생/횃불 과노출을 기존 owner·재질만 보완했다. 사용자 PID19752/foreign editor 제어0이며 새 C++를 사용하려면 사용자 editor의 정상 재시작이 필요하다. 남은 필수 구현0; 원작 native/pixel/frame parity·Shipping stress는 별도다. 기존 사운드/패링 준비본을 덮어쓰거나 완료된 broad author/delivery/archive를 반복하지 않는다.


## 2026-10-12T08:12:54+09:00 — 혈액 작업 메인 에디터 적용 완료

앞선 사진 혈액 Source/package는 그대로 유지됐고 후속 사용자 요청으로 실제 Main editor PID23736/DevMap/현 canonical DLL/몬스터6 CDO를 확인했다. 새 Art authoring/asset save0이며 정상 재시작 필요는 해소됐다. Source·UHT timestamp 보완/합본 build·actual hit13과 정확한 적용 증거는 Engineering continuity의 같은 날짜 절, Metadata/MonsterBloodReference_20261012/MainEditorIntegration/Result.json·ResumeState04.json을 따른다.


## 2026-10-12T08:17:34+09:00 — Player Parry 에셋 Main 전달·fresh 검수 완료

새 motion2/particle1/local master3·MI5와 기존 Guard Montage·GA를 합친13 package를 Main에 전달했고 fresh MainSavedAudit02·MainPIE02에서 확인했다. source composite/dilation/22 frame/source cue와 기존 Guard segment·notify는 유지했다. 실제 Main의 성공 모션/weapon contact flash/꼬리 프레임을 열어 불투명 card/원판 경계가 없고 입자 끝이 연속 fade하는 것을 확인했다. source MI blend overrides는 복원됐으며13 emitter를 유지한다. local parent의 .04 UV/1.25px와 spark ellipse power2는 사용자 요구에 대한 임시 표현 수치다. 기존 공유 재질·texture·audio를 재저장하지 않았다.

Main DLL/source/asset SHA와 실제 RHI/저장 검사 결과는 Metadata/Parry_20261012/FinalVerification.json에 결속됐다. 이전 Main 잠금/준비본 pending은 이 범위에서 해소됐다. DefaultPawn 검은 원판 가설 정정과 이전 실패 proof는 보존한다. 초기 RHI의 메모리 budget/FPS 경고, 원작 stripped shader/pixel/impact writer parity, 실제 스피커 출력(-nosound) 및 Shipping 성능은 범위를 구분한다. 정확한 runtime은 Engineering PARRY_IMPLEMENTATION_20261012.md, 완료 후 재개 기준은 ResumeState.json이다. 전체 추출/저작/과거 DLL 전달을 반복하지 않는다.



## 2026-10-12T09:50:12+09:00 — 몬스터 실제 사용 Root/좌표 후속 검사 중

현재 실제 소비자 시퀀스395는 Root 옵션과 true-root/첫 track 모두 정상, save0/dirty0이다. 기존 CurrentAnimationLibrary와 cached collision/VFX plan을 재사용해 Source339 bone samples와 baked attachment origin을 비교했다. 원본 좌표는 actor 축/root-stripped이며 실제 render mesh1.2/1.3 크기가 기존 collision mapping에서 누락됐다. socket 없는 VFX의 actor 기준과 current final pose 보정은 runtime에 한해 private에서 진행 중이다. Root/골격/키/notify/원본 texture·particle 값과 package를 재저작하지 않았다. 현재 Main 적용 완료가 아니며 숫자/원본 출처는 Metadata/MonsterRootCollisionRepair_20261012/MainBasis03/Basis.json 및 MainUsageAudit02/RootAudit.json, 진행/재개는 Engineering continuity와 ResumeState01.json을 따른다.


## 2026-10-12T10:42:05.435790+09:00 — Fab VFX 3팩 반입·native 확인 / shader 검사와 누락 원본 재개

이번 작업은 Art / Resource다. 정본은 Docs/Art/FAB_VFX_IMPORT_20261012.md이며 공급 폴더 C:/Users/user/Desktop/VFX와 요청 Fab7을 대조했다. Cursed Magic Niagara(/Game/Cursed_Magic), Niagara VFX Bundle(/Game/NiagaraVFXBundle), ARPGVFXPack03(/Game/ARPGVFXPack03)의 3팩/시스템682를 Main에 복사했다. 실제 파일3357/5,017,846,876byte이며 기존 파일 덮어쓰기0·Source/Config/uproject 쓰기0·에셋 save0이다. 공용 의존성59와 외부 actor/object110을 포함한다. StageDependencies08 등록3357, MainLoad02 public3247/external110/load error0/exit0이 마지막 완료 검증이다.

원본에도 없는 데모 preview soft path5, 데모 legacy input/RigVM private-memory 경고는 정본에 보존했다. GameFeatures 시작 ensure의 MainLoad01 실패는 검사 프로세스 플래그로만 교정했고 MainLoad02 성공으로 대체됐다. Stage 첫 Python API 실패도 원본 report로 남겼다. 게임 기능에 팩을 연결한 것은 아니다.

현재 own shader 프로세스는 Metadata/FabVFX_20261012/MainShaders01/Launch.json의 PID30652, launcher session70066이다. 이 작업이 시작한 숨김 실제 RHI commandlet이며 Material375 compile/no saves를 수행한다. 타 작업/사용자 editor를 제어하지 않았다. 중단 후에는 PID 숫자만 믿지 말고 Launch.json의 args·project·script와 현재 process를 대조한다. 먼저 MainShaders01/{ShaderAudit,Exit}.json 및 MainShaders.json의 processed/errors/status와 Editor.log를 읽는다. 아직 실행 중이면 중복 launch하지 말고 완료를 기다린다. 종료했고 미완료이면 성공 index 뒤만 대상으로 별도 report label을 사용해 shader 검사를 재개한다. 완료 뒤 Scripts/Art/verify_fab_vfx_import_20261012.py로 source/target SHA와 현재 receipt를 검증하고 정본/Art state/knowledge/continuity 하단에 실제 결과를 추가한다. FinalVerification.json·ResumeState.json은 이 검증 완료 뒤 생성된다.

요청7 전체는 완료가 아니다. Action-RPG Essentials VFX Pack V2.0/Dynamic Impact and Collision Effects Pack/Slash and Hit VFX의 대응 원본을 공급 폴더 및 로컬 Fab cache에서 찾지 못해 async로 별도 경로를 요청했다. 4번째 de3c9ae3-ebfb-4702-8cc2-1c7c2608c0f4는 공개 조회403·연결 가능한 browser 없음으로 상품명 미확인이다. FlaresEffect 등으로 추측하지 않는다. 필요한 원본 경로/정상 상품 정보를 받은 뒤 LocalInventory.json/SourcePackageIndex.json을 재사용해 추가 폴더만 대조하고 신규 package만 stage→dependency closure→target conflict preflight→copy→fresh Main load/RHI 검증한다. 완료한 3팩 전체 반입/이름 변경/기존 파일 덮어쓰기를 반복하지 않는다.


## 2026-10-12T10:45:24+09:00 — 사용 Root 시작 오프셋88 / private 실제 검증
사용395개 중 body392/prop3을 분리했고 first-frame lock의 누적 시작 offset88을 native1176포즈로 확인했다. private RootMotionRootLock만 RefPose로 변경, original imported DataModel·notify SHA392개 전부 동일, raw/root 옵션·timing·audio/particle/material 채널은 보존했다. 수치는 RootLockPlan의 imported RAW first-root / skeleton reference property 근거이며 신규 원작 튜닝값이 아니다. .01cm/1e-4rad는 기존 compressed QA 기술 허용이다. Main 미반영 상태이며 source basis/body scale/최종 뼈 pose VFX는 all198 공격 에셋으로 검증중이다. 정확한 원작 native shader/pixel parity를 완료로 표시하지 않는다. 현재 재개는 Metadata/MonsterRootCollisionRepair_20261012/ResumeState02.json 및 Engineering continuity를 따른다.


## 2026-10-12T10:52:19.737884+09:00 — Fab VFX native/RHI/SHA 완료 확정 / 누락 원본만 재개

앞 절의 shader 진행 상태는 완료됐다. own MainShaders01 PID30652와 launcher는 Exit0으로 종료했고 Material375 compile0/stats양수375가 확인됐다. MainLoad02 및 최종 source/target SHA3357도 passed/Exit0이다. 최종 상태는 Metadata/FabVFX_20261012/FinalVerification.json, exact remaining/resume는 ResumeState.json, 설명·대응표는 Docs/Art/FAB_VFX_IMPORT_20261012.md다. Source/Config/uproject 보호 snapshot 동시 변경0·본 작업 write0·기존 asset overwrite0/save0이다. matched local3팩은 완료지만 all_seven_complete=false를 유지한다.

남은 것은 Action-RPG Essentials VFX Pack V2.0/Dynamic Impact and Collision Effects Pack/Slash and Hit VFX의 정확한 별도 로컬 원본과 4번째 de3c9ae3 상품명/정상 URL 확인이다. 받은 새 source 폴더만 인덱스에 추가하고 full package·version·hard/soft dependency를 확인한 뒤 신규 target conflict 검사→새 package만 반입→fresh Main native/RHI/원본대상 SHA→Art MD 하단 추가 순으로 진행한다. 완료한3팩의 stage/import/compile 전체를 재실행하거나 FlaresEffect/다른 상품을 4번째로 추측하지 않는다.

임시 staging 제거는 자동 tool review가 recursive delete를 blocked by policy로 거부해 실행되지 않았다. Saved/ArtStaging/FabVFX_20261012 약5GB와 검증 evidence를 그대로 보존한다. 이를 원본 또는 전달 실패로 해석하지 않는다. foreign/user editor 제어0이며 필수 추가 native 검증은 없다. 데모 legacy input/RigVM·source preview soft5, 실제 VFX 화면·gameplay hookup/Shipping 성능은 이번 검증 완료와 구분한다.


## 2026-10-12T11:04:18+09:00 — 사용 애니메이션 Root88 / VFX basis·scale Main 완료
현재 사용395개/body392+prop3에 대해 Root 옵션/track을 확인하고 native first/mid/end1176포즈를 검사했다. Animation88의 first-frame 누적 origin을 RefPose lock으로 정렬했다. Root raw channels, 전체 model·notify392 SHA, 모든 timing/Root enable/force/normalized scale 및 original resources는 보존됐다. exact imports 기준 수치는 RootLockPlan.json의 first-root/skeleton reference 필드이며 신규 원작 튜닝값이 아니다. actor 좌표의 root-stripped source collision에 live body scale을 한 번 반영, socket 없는FX는actor orientation+mesh origin/offset·size body scale 적용. VFX198/1577 및 death6는 delivered Source와 동일한 private RHI Success이고 Main current canonical/freshRoot·HP30·Player16·saved 원본 유지가 Success다. active correction-curve rows0 / 원작 native·pixel parity·전체두레벨·network는 완료 검증으로 표현하지 않는다. Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json 및 ResumeState03.json, MainBefore/RootAssetsBefore 백업을 따른다.


## 2026-10-12T11:13:19+09:00 — Main editor ready
Rider Run opened Main PID32684; read-only RiderLink confirms /Game/Maps/DevMap, current canonical DLL matches MainBuild02 SHA, all88 RefPose settings loaded, dirty content0, asset saves0, PIE not started. MainEditorReady.json / FinalVerification.json / ResumeState03.json contain the exact result.


## 2026-10-12T12:09:54.562710+09:00 — Fab7 후속: Assets 프로젝트의 4팩 확인·얕은 폴더 정리 준비

최신 사용자 요청은 4번째 상품을 Roar Spell VFX로 확정하고 VFX/Assets의 나머지4팩 반입 및 전체7팩의 얕은 폴더 정리를 직접 승인했다. 앞선 원본경로 유지/7개 미확인 기록 중 미래 작업 방침을 이 요청으로 대체한다. 현재 Source C:/Users/user/Desktop/VFX/Assets/Content에서 ARPGEssentials299/DynamicCollisionVFX136/SlashFX163/Roar_Spell_VFX14, 새 package612를 확인했다. Niagara는52/16/35/1=104, 기존682와 합계786이다. 공급 프로젝트 EngineAssociation5.4, 대상5.8.2이며 게임 Source/Config/asset gameplay hookup 변경 권한으로 확대하지 않는다.

정리 계획은 /Game/VFX/01_ARPGEssentials,02_DynamicImpact,03_SlashHit,04_RoarSpell,05_CursedMagic,06_NiagaraBundle,07_ARPG03과 실제 공용 의존성 _Shared다. NiagaraSystem은 각 pack root에 바로 두고 지원 에셋은 Materials/Textures/Meshes/Blueprints/Modules/Curves/Demo 한 단계에 모은다. visible folder depth는 Content 아래 최대3이다. duplicate basename552개에만 원래 효과군 또는 full-source-key hash 접미사를 붙여 이름 충돌을 막는다. World Partition 외부 패키지는 엔진이 관리한다.

기존 Main3357 bytes/SHA는 불변 Before 백업, 신규4팩과 기존3팩을 합친 InputManifest3969개/6,435,516,913byte가 임시 project Saved/ArtStaging/FabVFX_Complete_20261012에 있다. MainOwnership02는 outside referencers0/dirty0/Exit0이다. Main editor가 당시 PIE Play였지만 제어·종료하지 않았고 이후 사용자 editor 종료/connection 없음은 inventory로 확인됐다. 현재 Main Content 구조는 아직 바꾸지 않았다.

PilotRename의7개 대표(WorldPartition map 포함) 이동과 기본 value 비교는 passed였으나 기존 Cursed demo RigVM private import LoadErrors로 Exit1이었다. staging demo-only ControlRig9를 recompile_vm/compile_blueprint/save하여 graph model/node counts를 유지했고 RigRefresh01은 passed/Exit0이다. 전체 StageRename01 own PID28520/launcher session79726이 진행 중이다. 이후 일부 demo ABP AnimGraph 중복/material function editor-only 경고를 새 프로세스에서 확인할 필요가 있다. VFX 상태·로직·원본 수치를 새 튜닝으로 변경하지 않았다.

정확 재개: 먼저 Completion/StageRename01/{Launch,Exit}.json과 StageRename.json 및 Editor.log를 읽고 현재PID/args를 대조한다. 실행 중이면 중복 rename하지 않는다. 종료 후 성공 대상은 RenamePlan/새 object existence로 재실행을 건너뛴다. StageRename은 모든 public3859개를 이동해야 한다. 그 뒤 Scripts/Art/run_fab_vfx_fixup_20261012.py로 staging-only redirector fixup, audit_fab_vfx_organized_20261012.py로 fresh class/기본 value/old refs/missing hard refs 검사, 필요한 demo cache 보완과 실제RHI material 검증을 수행한다. 문제를 해결한 준비본만 Main에 전달하며 GameSource/Config/기존 map은 저장하지 않는다. Main publish·old path retire·fresh Main 검사·현재 metadata/docs는 아직 남아 있다.

재사용 evidence는 Metadata/FabVFX_20261012/Completion의 InputManifest/ListingMap/FolderMap/RenamePlan/LayoutSummary/PropertiesBefore/InputRegistry/MainOwnership/PilotRename/RigRefresh01 및 각 process receipt다. Input01 neutral GameFeatures rule 오류와 MainOwnership01의 없는 is_asset_loaded API 실패는 보존하고 Input02/Ownership02 성공이 대체한다. 원본4팩 재조사/기존3팩 broad reimport/옛 native DLL/다른 Source 전달을 반복하지 않는다.


## 2026-10-12 — ARCH-92 Main Source/표시 에셋 적용·검증 중

일반 사망 중단6의 잘못된 freeze뿐 아니라 실제 Front/Back12 브루탈의 종료 블렌드 후 terminal pose 오차8–113cm도 재현했다. 해당 lethal instance만 auto blend-out을 막고 기존 Monster GT tick이 마지막 포즈를 확인하여 Exhaustion의 기존 완료 경로를 호출한다. 비치명타 recovery/공유 montage asset는 유지한다. 새 runtime 파일0. Main Source6 runtime/DEV4 및 표시 montage8에 55개 추가 window(공격44/회피8/낙하3)를 적용했다. 기존 event GUID/trigger/필드와 playback 원본은 보존했고, ground strong source2 marker는 weak variants·weapon tip·walkable projection으로 변경했다. TEMP scale/count/distance는 Notify/Monster 기본 설정이며 원작 값이라고 표현하지 않는다. Author01은 저장 전 보존 검사로 종료, Author02의4개 저장 이후 중단점에서 SHA 확인으로 재개하여 Author03 Exit0/8 완료다. authored checkpoint를 재저작하지 않는다. exact resume는 ResumeState02.json이며 actual RHI와 saved/화면 검증은 진행 중이다.


## 2026-10-12T12:49:08.300308+09:00 — Fab7 얕은 구조 native 검증 통과 / 같은 renderer RHI 검사 중

대형 AssetTools batch의3859개 새 destination은 모두 저장됐으나 final call 이후 isolated PID28520 committed memory가68GB까지 늘어났고 source/Main 변경 없이 own process만 종료했다. 원본 및 Before는 유지했다. neutral staging과 Before의 작업용 복사본에 NTFS compression을 적용해 logical bytes를 보존했고 OS가 paging을 회수한 뒤 디스크 공간도 회복됐다. 새 native audit는25개마다 GC해 memory를 제한했다. StageAudit01 public3859/value7943/error0/hard missing0은 데모맵의 old GameMode reference1 때문에 failed였고, same class/new path를 맵에 다시 저장한 MapRef01 후 StageAudit02는 passed/Exit0/oldrefs0/redirectors0이다. 초기 batch에 나온 demo AnimGraph/material function LoadErrors는 이 fresh load에서는0이었다. 원본 preview soft path5의53 referencer는 별도 유지한다.

현재 current Main RendererSettings/Windows RHI section만 staging Config에 복사한 뒤 StageShaders02 own PID7932/launcher11114가 Material419 real D3D12/SM6 no-save compile을 진행한다. neutral renderer로 시작한 StageShaders01은 작업별 renderer 일치를 위해 own process만 종료했고 초기 receipt를 보존했다. Main Config/Source/기존 map은 변경0, native 검사로 준비본 class/field 보존을 확인했으며 Main publish는 아직 전이다.

정확 재개는 Completion/ResumeState.json이다. 먼저 StageShaders02/Launch·Exit와 StageShaders.json을 읽고 running이면 중복 launch하지 않는다. passed/Exit0 뒤 publish_fab_vfx_organized_20261012.py로 verified stage files를 동일 volume의 Main 새VFX namespace에 move하고 기존3팩3357 파일을 Retired archive로 move한다. source/target 절대경계 및 SHA가 각각 preflight되며 source/Main conflict가 있으면 반영하지 않는다. 이후 fresh MainAudit01/audit_fab_vfx_organized_20261012.py→verify_fab_vfx_completion_20261012.py→Art 정본/state/knowledge/continuity 최종 추가 순이다. 이미 이동한3859 asset의 일괄 rename/전체 original import를 반복하지 않는다.


## 2026-10-12T13:12:55+09:00 — 사망·브루탈·공격/회피/착지 효과 Main 후속

기존 PP_Player_Parry_Success(원본 JustGuard13 emitter의 로컬 alpha 복원), PP_AtkEx_Grapple_01/02와 original world smash_weak surface variants를 재사용했다. 새 particle/material/texture asset0. 원작 출처는 Metadata/Parry_20261012/OriginalEvidence.json, Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json, Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv 및 기존 Player VFX playback 정본이다. gameplay source field/공격 피해/모션 데이터/오디오는 그대로다.

montage8에 추가된55 window는 공격44(파랑+보라/검붉은 accent), 방향별 회피8, 착지3이다. 기존 trigger/입력 event GUID/field·section/segment 보존을 저작 시 확인하고 SavedAudit02에서55 start/end pair·template·scale·수명을 재조회했다. 루프를 방치하지 않고 notify end에서 deactivate하여 잔여 입자를 drain한다. 기존 Spin 강한 내려찍기2 marker의 dust/snow/grass strong variant는 weak variant로 바꿔 바닥으로 낮게 퍼지게 했고 실제 weapon-tip/walkable normal 기준을 적용했다. 착지 먼지는 벽에 들어간 칼끝의 실패를 피하려고 실제 grounded actor 발밑으로 보정했으며 collider/gameplay 위치는 바꾸지 않았다.

새 수치는 모두 어시스턴트 TEMP 표시값이다: attack blue scale0.35(가벼운 공격)/0.5(강한 공격), accent0.25/0.35, dodge0.25, plunge blue0.5/purple0.4/ground1, Spin ground0.8. Notify Scale3D에서 조정한다. 착지 start는 기존 Land section entry+UE endpoint epsilon0.0001초이고 window0.121175006초는 저장 source damage window 길이를 사용한 표시 adapter이며 새 gameplay duration이 아니다. weapon-tip100cm는 기존 blood source RelativeLocation.Z=100에서 가져온 cm 값이고 원작 floor native writer를 복원했다고 표현하지 않는다. 효과 기호의 파랑/보라/검붉은 인상은 현재 복원 parent·조명에 따른다.

혈흔 TEMP는 Monster Class Defaults: main 기존8/95/150cm half extents, satellite6(technical presentation cap16), radius90–280cm, size factor0.35–0.65, 기존24초 hold+3초 fade 유지다. 전체 방위로 점과 불규칙한 큰 얼룩을 함께 펼친다. shape/RGB 마스크·검붉은 분사·source ash와 dissolve3초는 이전 사진 혈액 구현을 재사용한다. 정상/짝 사망의 source 끝 포즈 수리와 실제6종7장/4방위 검사는 Engineering 최신 절을 따른다.

실제 게임 viewport 캡처와 source/hash/원본 보호는 Metadata/CombatFinishFollowup_20261012/PresentationFinal02·FinalVerification.json, 추가 ground 보정은 PlungeAnchor01/Applied.json에 있다. 대표 실제 화면을 별도 검토하며 editor screenshot/이전 실패를 시각 합격으로 쓰지 않는다. 전체 native shader/pixel parity·Shipping stress를 주장하지 않는다.


## 2026-10-12T13:16:18+09:00 — ARCH-92 메인 에디터 적용 확인 완료

Rider normal Khazan Run으로 Main PID16504/DevMap을 열었다. read-only RiderLink가 실제 canonical DLL SHA a247fac8a6c457a90d336ceb9ed90a5445bca878295d941b1c5081a375977f9b와 FinalBuild05 일치, 6종 CDO scatter6/radius90–280cm, dirty content/map0를 확인했다. asset save0, PIE 미시작이며 에디터를 열어 둔다. FinalVerification.json은 MainDelivered_Built_Validated_EditorReady, ResumeState04.json은 complete/잔여0이다. 사용자 이전 Main은 착수 때 종료돼 있었고 강제 종료/HotReload/기존 session 저장0이다. 모든 실제 테스트·동일 runtime source·Art TEMP와 원작 한계는 앞선 완료 절을 유지한다.


## 2026-10-12T13:26:59.800787+09:00 — Fab VFX 7팩 반입·얕은 폴더 정리 완료

요청된 미반입 4팩 재탐색·반입 및 전체 7팩의 얕은 정리는 완료했다. 최신 Main은 `/Game/VFX`의 7 numbered folders + `_Shared`, NiagaraSystem 786 / public asset 3,859 / files 3,969다. 반입 및 폴더 정리에 필요한 남은 작업은 **0**이다. `Completion/ResumeState.json`은 complete다. 이전 shader/publish/누락 4팩 대기와 큰 rename process 진행 상태는 이 완료 절로 대체한다.

마지막 검증: MainAudit02 Exit 0(public load/class/settings 7,943·old refs/missing hard/redirectors/load errors 0), Cursed WP 103 actual actors·7 objects 및 원본 배치/NS 선택 같음, StageShaders02 Exit 0(Material 419 real D3D12/SM6). `verify_fab_vfx_completion_20261012.py` Exit 0은 현재 renderer 일치, Material bytes 보존, 전달 3,969 SHA와 retired 3,357 SHA, WPBeforeMain 보존을 확인했다. 최종 범위·동시 외부 Source 변경 10개·원본에도 없는 preview soft path 5개와 legacy input 경고는 FinalVerification 및 Art 정본에 있다. 이 작업은 Source/Config/기존 gameplay 파일을 저장하지 않았다. 새 효과의 게임 연결·전체 화면/Shipping 검증 완료로 확대하지 않는다.

정확한 후속 절차: `Metadata/FabVFX_20261012/Completion/ResumeState.json` → `FinalVerification.json` → `LibraryOverview.md`/`ListingMap.json`을 읽고 `/Game/VFX/<pack>`에서 필요한 NS를 선택한다. 이름 이력은 `RenamePlan.json`을 조회한다. 이미 완료한 original-root import, 전체 rename, public load/RHI compile을 반복하거나 retired root를 Main에 복원하지 않는다. 새로운 소비/연출 요청이 있을 때만 현행 Architecture/Cue/Notify 계약을 별도 Engineering 도메인으로 확인한다.

실패·복구 증거: 기존 bulk rename memory 문제는 task PID만 종료 후 저장된 목적지에서 재개했으며, unloaded WP actors 누락은 staging native WorldPartitionRenameDuplicateBuilder duplicate mode(WPBuilder02 Exit 0)로 복구했다. WPStageAudit01의 SoftObjectPath API, 02–03의 transient WorldDataLayers 중복 관측, 04의 재생성 descriptor 차이 판별 실패는 보존하고 05 passed 및 MainAudit02가 대체한다. 원본/이동 맵 actual values는 같고 editor-derived bounds/class 변화는 분리 기록한다. 원본 VFX와 Before/Retired/WPBeforeMain은 보존했다. 원래 staging 삭제의 자동 검토 거부를 우회하지 않았으며 task staging은 NTFS 압축된 보존본이다.


## 2026-10-12T13:28:50.418609+09:00 — Fab7 현재 열린 Main 에디터 표시 확인

RiderLink의 현재 Main PID16504에서 read-only registry 조회로 7팩 root의 NiagaraSystem 52/16/35/1/58/609/15 및 public asset 3859를 확인했다. 강제 rescan/asset save/map save/맵 전환/PIE 제어는 0이다. 현재 열린 에디터에서도 `/Game/VFX` 라이브러리를 바로 조회할 수 있다. 증거는 `Metadata/FabVFX_20261012/Completion/LiveEditorAvailability.json`이다. 7팩 반입·정리는 complete/남은 필수 작업0을 유지한다.


## 2026-10-12T13:40:48+09:00 — DevMap·HeinMach 룩 준비본 / Main 잠금 대기

[SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md](SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md)를 첫 조회한다. DevMap/HeinMach 조정본493(map2/기존 masked MI489/새 parent2), PP 각1·toon/custom blendable0, 기존 actor pose10032 변화0와 scalar/vector/texture/base overrides의 예상 밖 변경0을 확인했다. small-tree3 raw RGB emission off만 TEMP 예외다. source stock foliage transmission 시험은 white leaf로 철회했고 최종 기존 DefaultLit/기존 two-sided/clip을 유지한다. DevAfter02/HeinAfter04 실제 D3D12 game viewport 검수·Exit0와 PreparedSaved02/PreparedDelivery가 준비본 정본이다. Source/Config/DLL 전달0, 원작 전용 shader/pixel·Shipping 검증은 별도다. Main editor PID16504/DevMap의 dirty0을 read-only 확인했지만 Win32 error32 map lock으로 Main content writes0에서 중단했다. 사용자에게 저장 후 editor 종료를 요청했고 editor 종료/reload/save 제어0이다. 잠금 해제 뒤 install→새 MainSaved01→MainDevAfter01/MainHeinAfter01→selected493 SHA/화면→FinalVerification/완료기록 순으로 재개한다. Main이 baseline과 달라졌으면 최신 사용자 변경을 보존해 field만 이관한다. 전체 추출/재임포트/Source·과거 DLL 전달을 반복하지 않는다. exact resume는 Metadata/SceneLook_20261012/ResumeState.json, 비교는 DevMap_BeforeAfter.jpg/HeinMach_BeforeAfter.jpg다.

<!-- SceneLook_20261012_PreparedAwaitingMainUnlock -->


## 2026-10-12T14:44:13+09:00 — DevMap·HeinMach Main 반영 및 새 화면 검증 완료

앞선 Main 잠금 대기 기록을 이 완료 기록으로 대체한다. 사용자 Main 에디터가 종료된 뒤 선택493개 전부의 baseline SHA와 교체 접근을 먼저 확인했고 Main에 map2/기존 masked MI489/부모2만 전달했다. 사용자 프로세스 강제 종료·저장·reload0, Source/Config/DLL 전달0이다. MainSaved01 새 프로세스의 saved audit Success/Exit0, 기존 actor pose10032 변화0, 보호 material parameter/base overrides 예상 밖 차이0을 확인했다. MainDevAfter01(DevMap3뷰)/MainHeinAfter01(HeinMach4뷰)는 실제 D3D12 game viewport를 촬영하고 Exit0/성공/재질 compile failure0이다. 역광 캐릭터·눈/바위/횃불·음영 화면을 직접 검수했으며 실제 Shot1092×573과 요청 창1600×900은 구분한다. 현재493개 파일 SHA가 준비본과 전부 같다. 비교 이미지는 새 Main 촬영으로 갱신했다. Three small-tree raw emission off는 명시한 TEMP 보정이며 실패한 stock foliage transmission trial은 철회된 상태다. 원작 전용 shader/pixel 전체 일치와 Shipping 성능·전 경로 플레이 검증은 별도이며 완료로 확대하지 않는다. 재개 정본은 Metadata/SceneLook_20261012/FinalVerification.json과 complete ResumeState.json이다. 이미 완료된 전체 저작/추출/재임포트를 반복하지 않는다.

<!-- SceneLook_20261012_MainCompleted -->


## 2026-10-12T15:41:28+09:00 — 요청 Niagara 내려찍기 바닥용 재사용 착수

/Game/VFX/03_SlashHit/KZ_Parring_Distort는 사용자 지정 Fab Niagara6-emitter asset이며 원작 메타데이터 복원값으로 부르지 않는다. 원본 file/재질/graph는 보존하고 별도 Work의 /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort에 바닥용 variant를 준비한다. 원본 local GPU sprite3의 FaceCamera를 CustomFacingVector로 조정하고 engine default SpriteFacing +X를 Notify 기하학적 pitch90도로 floor normal에 맞출 예정이다. scale1은 기존 system 단위 scale이고 새 gameplay tuning이 아니다. 실제 화면·alpha·부착/종료 검수는 아직 미완료다. Metadata/PlayerSlamDistort_20261012/{Probe01,Probe02,ResumeState.json}를 재개 근거로 사용하고 runtime 상세는 Engineering continuity를 따른다.

<!-- PlayerSlamDistort_20261012_PrivateStarted -->

## 2026-10-12 — 기존 불꽃 재사용 및 지정 Niagara 전투 연결 착수

최신 사용자가 최근 stationary flame flash를 전면 철회했다. 자체 PP/M_Monster_HitFlameFlash와 혈액 PS 안의 KZHitFlash3를 제거하고 기존 Parry/Grapple의 spark sphere 분포·원본 재질을 강한 적중 burst에 재사용한다. 새로운 섬광 재질은 만들지 않는다. 인간4종 Slash/Sting 및 Player Slash는 /Game/VFX/01_ARPGEssentials/KZ_Slash, KZ_SwordsMan_Sting을 정확히 참조한다. 원본 metadata/현재 authored notify 보고서에서 필요한 attack entries만 표적 조회하고 위치·회전/finite lifetime·soft alpha를 실제 RHI로 확인한다. 이전 blood/ash/ground·SceneLook·음향·SlamDistort 별도 준비 변경을 보존한다. Metadata/CombatImpactUpgrade_20261012의 현재 baseline/author/검증/ResumeState를 사용하며 이번 절은 적용 완료가 아니다.


## 2026-10-12T18:08:30.145524+09:00 — 전체 애니메이션 정수 FPS 수정 착수

사용자 전수 확인 요청에 따라 저장된 Enemy index를 먼저 읽고 새 read-only registry 감사로2674 sequences/158 montages를 조회했다. 소수 모델 clock461/호환 실패로 추론한100000fps montage36이다. platform sampling clock과 실제 native rate는 별도 확인 중이며 추론을 실제 관측으로 혼동하지 않는다. 선정 계획461/의존 montage45와 immutable 원본632행 백업은 Metadata/AnimationTimingKnockback_20261012/Plan.json/Baseline.json/Before에 있다. 이 시점은 author/Main 완료가 아니다.

키를 재구성/재샘플하지 않고 clock 단위를30/60Hz로 바꾸며 effective RateScale·sequence local event/marker·montage source trim을 계산 변환한다. 원본 TimingContract는 보존하고 새 계산 출처 tag를 별도 추가한다. Engineering의 Knockback 실행 변경은 Engineering continuity로 구분한다. exact resume는 위 ResumeState.json; legacy export/원본 RootMotion 작업을 다시 실행하지 않는다.


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 바닥 Niagara·alpha Main 완료

사용자 지정 /Game/VFX/03_SlashHit/KZ_Parring_Distort의 원본6 emitter는 그대로 보존했다. /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort 복제의 M_SW_distort_Sprite_0/M_SW_distort_Sprite001_1/Hit003_6 renderer만 CustomFacingVector 및 실제 User.KZFloorNormal로 저작했다. shader에 카메라 facing을 남기는 잘못된 수동 binding trial은 native author의 host-map binding3개 true로 대체됐다.

원본 parent/MI2쌍을 새 경로에 복제하고 기존 opacity에 UV radial feather(.8–1)를 곱하며 refraction 가장자리를 중립1로 돌려 사각 경계를 제거했다. 이는 어시스턴트 표시 TEMP이고 원작 직접 수치가 아니다. scalar/vector/texture override는 원본과 동일하다. 원본 source Niagara/머티리얼/텍스처를 수정하지 않았다. 실제 RHI PrivatePIE05/Fall_02 화면에서 부드러운 바닥 원형과 사각 경계 제거를 검수했고, fresh Main saved/RHI가 같은6 package를 검증했다. 경로·SHA·runtime 증거는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json. Fab 사용자 지정 효과와 원작 metadata 재현은 구분하며 원작 pixel/shader 동일성은 주장하지 않는다.


## 2026-10-12T19:20:23.056916+09:00 — 정수 FPS461/몽타주45 Main 반영 / 새 Main 검증 대기

Art author Final·PrivateSaved03은3854855 raw keys 동일,158 displayed montage FPS integer·실제 시간 차이0을 검증했다. MovieScene frame-index keys는 바꾸지 않고30/60Hz clock+계산 RateScale, local notify/marker 및 inline scalar/vector correction-curve time/tangent·source trim을 함께 변환했다. 기존 몽타주 precision-model clock을 강제로 정수화한 trial은 reload 시간 반올림을 일으켜 철회했다. 표시는 sequence sampling으로 정수화되고 montage 실제 clock은 보존된다. Meta old source contract를 남기고 IntegerFPSRepair tag를 추가했다.

Main 동시 공격 VFX88개 변경을 보존한 최신 merge도 raw 동일/notify 재검증했다. asset511 선택 전달 완료, NativeBuild와 fresh Main 확인은 대기. 현행 Enemy 조회는 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv(813행/270변환)를 사용하고 과거 CurrentAnimationLibrary.csv는 이 변환 전 역사적 값으로 보존한다. exact evidence/resume는 같은 폴더 ResumeState.json/AuthorFinal/NativeAuthor.json/Delivery.json.


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

## 2026-10-13 — Yetuga/Apes VFX 후속 private 작업

정본은 GIANT_VFX_REFINEMENT_20261013.md다. Metadata/GiantVFX_20261013/{Baseline,AnimationOwnership,Probe02/Probe,ParticleExports01/Export,ParticleObjectCatalog}.json이 현재 표적 목록이며 native WorkBuild02 후 실제 viewport before/after 검토를 진행한다. 현재 Main 게임 asset write0, 사전 private UI/source owner·단위 보완과49PS export까지다. 기존 전체 source extraction/rename/Root/FPS author 및 공용 ParticleAlpha/보조 물리를 덮어쓰지 않는다. 정확 재개는 Engineering continuity의 ARCH-98, 리소스/TEMP·원작 그림은 위 Art 정본을 따른다.


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset 형상 Main 전달 완료

SK35/PA35/post-process20/shared CopyPose1/기존 gameplay BP6의97 package를 Main에 전달했다. 원본 vertex/skeleton/animation/texture/material/LOD 재임포트0이다. source metadata anatomy17/17/16 capsule의 package/field/raw/SHA는 OriginalAnatomyShapes.json, 그 외 dominant LOD0 skin bounds와 Yetuga actual skin tip sphere/질량·관성 계산은 final evidence의 source reports다. Feel은 current Player TEMP 재사용과 명시된 virtual-inertia TEMP2/기술적 adaption이며 원작 physics 전체 복원으로 표현하지 않는다. 최종 explicit simulated317이며 초기378/미완료 기록을 대체한다. Runtime 품질/검증/cleanup은 ../Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json을 따른다. 필수 잔여0; full 원본 추출/재임포트/기존 shader·VFX·animation 변경을 반복하지 않는다.
<!-- MonsterSecondaryPhysics_20261013_main_complete -->

## 2026-10-13 — GiantVFX 재개 / 검정 눈먼지 검수 실패 유지

Main 미반영이다. WorkQuality01 114case와 WorkFocus01 16case의 기술 통과는 원작 시각 일치 판정이 아니다. DustPalette01에서 black 출력이 남았고 RendererIsolationRHI01은 개별 emitter1에서도 재현했다. LOD2 구재질 추정은 철회(DustDiagnosisCorrection.json)했고 SnowSubstrateControl03/SnowSubstrateRHI01의 같은 입자·다른 shader 비교를 진행한다. 기술 axis의 enabled 상태는 UParticleSystem.PreSave가 transient SoloTracking으로 복원하므로 저장 뒤 실제 상태 확인이 필요하다.

다음은 위 shader 비교 PNG 확인 → 원인 수정 및 actual attack/foot/breath/rock/field 화면 확인 → fresh saved audit → Main 선택 전달/빌드/RHI다. 완료한 Author02/원본49 PS 및 field2 import/Root/FPS author를 반복하지 않는다. 최신 정확 작업 포인터는 Metadata/GiantVFX_20261013/ResumeState.json이다.


## 2026-10-13 ? ???? ?? VFX ?? ?? / ?? ?

Router ? Architecture/Migration ? Heal ?? ??? ???? ?? ?? ??? ????. ? runtime class/component/manager/tag0, ?? Heal? notify callback?? Action feedback receipt? ????. ?? SB_Kazan_Recovery.UpperAnim=AC_Kazan_Recovery? ??5?? native11 bone adapter? ????? current Heal/Stow/HP/weapon/input/audio ??? ??? ????. cooked Niagara ??/VM shader graph ???? ??? ?? source mesh3/texture FT_Trail/G density/ShaderLUT? source effect ???? native Cascade? ?????. ?? TEMP/skin sampling ??? ?? ????.

Main ?? Source/asset ??0??. ??? ??/??/?? ??? Metadata/HealVFX_20261013/ResumeState.json, ???? Khazan_HealVFXWork_20261013??. WorkBuild01 ??, Author03 ??? ?? ??, fresh Saved/?? RHI/??/??/?? Main ??? ???. ?? editor/???? ???? ???. ?? ????? ??????? VFX/physics/FPS/root author? ???? ???.


## 2026-10-13 ? ?? VFX Main ??/??/?? ??, ?? Main ?? ?

15 target(runtime1/?? DEV1/asset13)? exact SHA/CAS? byte backup?? Main? ????. protected Source/Config/?? Heal?Draw ??0, private DLL/Config ??0??. MainBuild01 exit0/22.04s, MainSaved01 ??0??? notify/GUID/clock ?11bone/22 paired child? ????. ?? MainFinalPIE01? ?? owned editor?? ?? ??? ?? Main ?? ?? ??? ???. ?? source5 role/mesh3/FT_Trail.G/ShaderLUT? ???soft alpha TEMP? ??? ?? ??? PrivatePolished01??. ?? ??? ??? Metadata/HealVFX_20261013/ResumeState.json: MainFinalPIE01 Driver/Exit???PNG ?? ?15SHA/loaded DLL/???? ??? ??. ??? author/??/physics/root/FPS/?? VFX/old DLL? ???? ???.


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery?5 effect role/core?burst???????light flash? ?? Heal/Stow ??? ????. source raw LinkValue+?? Stow offset/rate? ???? ?? HP/InputEnd/weapon/??/?? ??/FPS/root/audio? ????. runtime1/?? DEV1/asset13(??12+?? Heal Montage1)?15 ??? exact SHA/CAS? ????. ? runtime file/class/component/manager/tag0, private DLL/Config/Build ??0, ?? 133 ?? SHA ??0??. ? Source? Main?? canonical build??.

MainBuild01 exit0/22.04s, MainSaved01 save0??? notify/GUID/?? ?11bone/22pair, MainFinalPIE01 ?? Khazan.Heal.PIE/Khazan.Combat.PlayerAttackCollision.PIE Success?. ??11 child emit?parent bone?finite values/HP????????? ?????/???UnPossess cleanup? ???? actual loaded canonical DLL SHA? 39ab3b029cc36dd7c78213f55fc2e22446110268952cbd932571a6a96488a46d?. shader errors0/pixel instructions179?189?207, Main ?? Core1.3667s/hand burst1.9667s ??? energy/continuous edge? ????. missing ParticleSprites/MeshParticles usage ?? default fallback warning0??. ?? editor/???/??/??? owned process fixture, package/map ??0, ???/foreign editor ??0??.

Source mesh3/FT_Trail.G/ShaderLUT?source numeric? clock ??/TEMP? PLAYER_HEAL_VFX_SOURCE_20261013.md? ????. cooked Niagara/VM/material/WPO graph ???? ?? native Cascade? ??? ????? original skin sampling/light/full shader/pixel ????? camera/Shipping/network/??? ???? ???. ExposureCompensation1/EmissiveGain8/feather0.04???1.25px/DepthFade8cm ?? ????? TEMP?. Source Dilation1.3497161s? ?? raw Heal1.4666667s? ???? ??? retime?? ???. ?? ??/???? ???? ?? ?? ? Main ???? ????.

?? ??0. ?? evidence? Metadata/HealVFX_20261013/FinalVerification.json, ResumeState.json, Changes.patch?. ??? ?? ???current /Game/HealVFX/Materials?Particles ? Heal marker? ?? ????. ?? full author/?? ??/?? ????/?? VFX?physics/root/FPS ?? private DLL ??? ???? ???. ?? ??/???/?? ??? ? ??? ????.

## 2026-10-13 — Notion 주간 실제 구현 화면 첨부 완료

새 Main 검증 캡처4종(HeinMach, HUD/B, Parry, Heal)을 직접 Notion에 업로드하고 주간6개의 이미지 결속을 확인했다. 기존 사진/보고는 보존하고 실제 촬영일과 과거 주간의 후속 누적 참고를 명시했다. 새 editor/capture/asset author·이미지 생성/편집은 수행하지 않았다.

NotionProgress_20261013 complete/remaining0. 후속은 FinalVerification.json의 Notion 페이지ID/캡처 출처→현재 Art 완료/evidence→Notion fetch→기존 날짜 append/readback이다. 오래된 캡처를 새 촬영으로 표현하거나 재구성을 원작 픽셀 일치로 주장하지 않는다. 현재 주간: https://app.notion.com/p/3f8ec99d2c54819e92aeffcad36b4b57?pvs=204

<!-- NotionProgress_20261013_report_backfill_complete -->


## 2026-10-13 — ARCH-95 OverFury 추가 Slash 철회·나머지 무기 궤적 정렬 착수

사용자 직접 수정 요청이다. OverFury의 KZWeaponSlash17 start/end쌍만 제거하고 원작 notify/효과·입력/피해/시간축은 보존한다. 나머지 추가 Slash는 공유 KZ_Slash asset을 유지하며 기존 Action receipt의 GT finalized pose/cleanup에서 실제 장착 grip/칼끝·무기 reach를 사용해 링 끝점/크기/스윙면을 검증한다. 새로운 runtime class/file/manager/tag0이다. actor-space pose가 빼던 몸통 회전과 bounding-centre 앵커의 차이를 실제 여러 프레임/시점에서 먼저 관측한다. 새 gameplay 튜닝값이 아니라 현재 Fab mesh radius100/diameter200cm·renderer yaw180 및 실제 무기 geometry의 변환/계산이다.

Main source/asset 수정0, fresh 별도 Khazan_PlayerSlashWork_20261013의 source/config/binary 사본·Content hardlink 중 6target montage는 링크를 끊어 안전하게 분리했다. Probe01 saved/export은 passed. 현재 baseline DEV 계측 build와 그 뒤 before RHI 진행 단계다. 정확 재개는 Metadata/PlayerSlashAlignment_20261013/ResumeState.json. 기존 source VFX/피해/오디오/Physics/FPS/Parry·다른 작업은 보존하며 full reauthor/reimport나 외부 editor 제어를 하지 않는다.


## 2026-10-13T12:06:39+09:00 — Player·인간형4종 SFX 누락/끝음 Mixed 요청 착수

현재936 animation/58 ComboDefinition/5 CharacterDefinition/84 grant를 새 background read-only process에서 읽었다. 이전1462 audio event 누락0이지만, later integer-FPS359 clock 변경은 현재 정본으로 보존한다. raw 시퀀스만 조사하던 이전 사운드 계획이 상위 원작 Composite의 Strong/Charge/Guard/Heal 등 이벤트를 놓친 것을 확인했다. 기존 InGame inverse_map 함수를 재사용해 raw parent→matching raw leaf→현재 baked clock으로 계산했다. 신규 원작34 event 표적 추출/196 bank·media+12 reuse→31 audible cue/149 leaf recipe이며 기존 chunk0/chunk1 index와 FModel settings를 재사용한다. 재전수추출0이다. 기존 ordinary reaction composite에 audio notify가 없는45 clip에는 같은 family의 원본 short cry를 첫 피격 pose에 두는 명시적 TEMP adapter를 준비했다. 동작 없는 silent loop에 임의 소리를 계속 붙이는 방식은 쓰지 않는다. 원본 시각·raw/group/gain/loop/끝음은 보존하고 native mix는 별도 TEMP로 기록한다. current PlaybackPlan01/Inventory02/ResourcePlan01/NativeCuePlan01/ResumeState01이 재개 근거이며 Main 새 asset 저장은 아직0이다. Yetuga/Apes asset·HeinMach map은 이번 scope에서 제외한다.


## 2026-10-13T12:35:17.064758+09:00 ? OverFury ?? ?? ?????? Slash ?? Main ??

OverFury ?? KZWeaponSlash17?? ???? ?? ??? ????. ???5 montage? ??33?? requested KZ_Slash? ???? effective particle mesh diameter400cm(? mesh200?initial XYscale2), yaw90(90 particle+180 renderer+90 correction=360), ?? bounding-centre offset ??? ????. ?? Niagara/mesh/material/texture? ????? ? VFX asset? ??? ???. ?? source/??/?? GPU? Metadata/PlayerSlashAlignment_20261013/NiagaraGeometryEvidence.json ? NativeGPUBefore01/FinalRHI02? ??.

SavedWork04?? montage6? ??1359 effect objects?37 fields? notify clock/GUID? ?????. ?? ?? ?? ??216? ? ?/?/??/??/??? OverFury? ?? ??????? ????. Source FX? ??? QA?? Cascade? ??? ?? mesh trail/decal? ????. source material?shader/pixel ?? ??? ?? Shipping ?? ??? ???? ???.

Main asset6 ?? ??, Main build/fresh saved/RHI? ?? ?? ???. ENGINEERING_WORK_CONTINUITY? ?? ?? ResumeState.json?? ??? MainRHI? ???? ?? ??? ???. AuthorAlign01/02? Rotator positional trial?SavedWork02/03 ??? ???? ????? ???. ?? author? keyword yaw=90? AuthorAlign03??.

## 2026-10-13 — 패링 사진 광막·굴절·카메라 후속 진행 중

이번 작업의 증거 루트는 `Metadata/ParryPhoto_20261013`이다. 사용자가 정정한 패링 사진은 `Metadata/CombatVFXReferenceReview_20261013/References/Parry_PinkPurpleHalo.png`이며 가는 백색/붉은 선 사진은 공격 사진이다. Main의 전용 `PlayerParry/Reference` 후보에 원작 PP_AtkEx_Parry를 복제하고 로컬 parent/MI만 수정했다. Source PP_AtkEx_Parry는 NewParrying 계열이며 기존 NewJustGuard의 PP_AtkEx_JustGuard와 동일 라우팅이라고 주장하지 않는다. cooked shader 원본은 제거되어 색·원형 alpha·굴절 복원은 임시 표현 값이다.

현재 Guard GA는 PP_Player_Parry_Reference와 BP_Parry_SourceCameraShake를 참조한다. Build01/Native05의 실제 모듈은 UnrealEditor-Khazan-731302.dll(SHA ea04f8fb53e38febb566692fb76baa910ef188818b2ad6a7f3145be8a2b9805f)이며 패링17상황/카메라 승인·FOV 변화·만료/기존 피격 VFX 없음 검사는 통과했다. **외관은 아직 합격이 아니다.** Native04는 분홍 사각 광과 검은 streak를 보였고 Halo01의 원형 alpha 및 Additive 복원 후 Native05의 세 프레임은 광막이 보이지 않았다. 효과 component 생성은 렌더링 성공 증거가 아니다. 실패 proof를 보존한다.

마지막 적용은 `Scripts/Art/refine_parry_photo_halo_20261013.py`의 Halo01이며 Native06에서 실제 MI shader permutation을 먼저 준비하여 원인 분리 중이다. 후보 에셋에 외부 참조 module이 없는 것은 확인했다. 이전 received-hit 제거(Player Definition ImpactEffect=None)와 공유 공격/혈액 asset은 보존한다. 재개는 Native06/Driver.json 및 실제 캡처 확인 → 필요 시 최신 로컬 material/CPU circle만 표적 보정 → 실제 광막·굴절·연속 alpha 확인 → 최신 native/저장 검증 → 두 도메인 정본/상태에 실제 결과 추가 순서다. 원작 픽셀 일치와 Shipping 성능은 미확인이다. 전체 추출/전체 author/과거 DLL 복원 또는 다른 에디터 제어를 반복하지 않는다.


## 2026-10-13T12:57:55.018345+09:00 ? GiantVFX ?? ?? ?? ?? ????? ??

GiantVFX ? ???Roar ???? opacity ? Grab ?? ??? Main? ????. ??? MainRefractionFixed01? Armageddon 013/014 ?? PNG? ? ? ?? ???. ?? MI3 ????? private ?? ????? Main ??? ??? ? ??. ?? ??? ??? Metadata/GiantVFX_20261013/ResumeState.json??. ?? active renderer ?? ?? object/terrain writer? ?? ??? ? ??? ???? ????. ?? cooked VAT/refraction shader ??? ????? ?? ??? ?? ??? ????.


## 2026-10-13T12:58:40.411493+09:00 — GiantVFX 재개 기록 인코딩 보완·시각 미완료

앞의 12:57:55 추가 절은 PowerShell 표준입력 인코딩 때문에 문자가 손상됐다. 원문 기록은 보존한다. GiantVFX Main 눈 노출·Roar 축·구형 opacity·Grab 단위 후속을 완료했다. MainRefractionFixed01의 Armageddon 013/014에는 흰 판이 남았다. MI3 재부모화가 Main 문제를 해결했다고 표현하지 않는다. 시각 미완료 정본은 Metadata/GiantVFX_20261013/ResumeState.json이다. 실제 renderer/부착 object/terrain writer의 소유자를 증명한 뒤 해당 대상만 수정한다. 원작 cooked shader와 픽셀 일치는 미확인이고 기술 통과와 시각 합격은 구분한다.


## 2026-10-13T13:13:52.789080+09:00 — PlayerSlashAlignment 정확 재개 검증 완료

PlayerSlashAlignment Main 재개 검증 완료. 약/강/차지/회피/공중Spin 및 OverFury를 실제 여러 시점으로 검사했고 MainRHI02에216게임화면을 확보했다. 추가KZ_Slash는33start/end쌍, OverFury추가0이고 원래1359effect의37properties/clock/GUID는 저장 재검사에서 보존됐다. 실제 GPU70표본·17공격의 endpoint max0.000031cm 및 rendered radial-axis assertion이 통과했다. 원작 cooked shader/pixel parity는 주장하지 않는다. 정확 자료는 Metadata/PlayerSlashAlignment_20261013/ResumeVerification.json 및 MainRHI02/ResumeAllSheet0·1.jpg, 원시PNG다. 별도 Armageddon 흰 판 시각 검수는 진행 중이다.


## 2026-10-13T13:18:40.096195+09:00 — PlayerSlashAlignment 완료·12:35 인코딩 보완

12:35:17의 손상된 한글 기록은 보존하고 이 절/FinalVerification.json에서 이어간다. OverFury addon0, 다른5 montage addon33쌍 유지; raw radius100×initial radial size2/particle yaw90·renderer180을 고려한 span400cm/correction yaw90/location0을 적용했다. component 내부 1±User.ScaleLerp growth만0으로 neutralise했다. shared KZ_Slash/mesh와 원래 효과/시간축을 보존한 현재 Main이 정본이다.

SavedMain01의 원본1359×37/clocks/GUID, 실제 full Main GPU/여러 시점·타이밍 및 grip-centred 공중 Spin와 최신 병행 suffix build의 재생을 확인했다. 완료/스크린샷/숫자 출처는 Metadata/PlayerSlashAlignment_20261013/FinalVerification.json 및 PLAYER_ATTACK_VFX_PLAYBACK의 최신 절이다. old actor-space/bbox author, positional Rotator trial, 실패 Python GPU probe 또는 old private DLL을 재사용하지 않는다. 이번 요청 잔여0이다.

별도 Parry 후보 M_Parry_Distortion/MI_FMI_fluid_A_162는 현재 Noise/FT_PerlinNoise_RG의 sampler Linear Color→Color 불일치로 shader fallback 진단이 있다(MainCollisionRHI01). 해당 Parry 진행 작업의 현재 candidate·원본 texture 색공간 계약을 확인해 표적 보정할 사항이며, 이번에는 공유 texture/다른 VFX를 고치지 않았다.

<!-- PlayerSlashAlignment_20261013_complete -->

## 2026-10-13 — PlayerSlashAlignment 최종 결속 보충

기존 완료 기록과 실패 진단은 보존한다. 병행 재개 검증의 Metadata/PlayerSlashAlignment_20261013/ResumeVerification.json에서 새 Main SavedMain02, 실제 MainRHI02의 GPU70·17공격·216화면 및 ResumeCollision01의 충돌16(Spin7/Fury19)이 모두 passed이며 후속 collision material compile failures는0이다. 과거 MainCollisionRHI01의 Parry sampler 실패를 삭제하거나 합격으로 바꾸지 않는다. 최신 suffix2026101353의 대표 약공격4/실제 GPU도 MainRHI04ComposedPreview에서 passed다. 이전 composed 전체 반복의300초 fixture timeout은 별도 실패로 보존했다.

현재 전달된 runtime3/DEV1/몽타주6 SHA는 두 완료 receipt와 일치한다. 병행 SFX/Parry/Giant Source·에셋·build를 보존했다. 정확한 최종 근거는 CompletionEvidenceIndex.json → FinalVerification.json 및 ResumeVerification.json이며 요청의 필수 잔여0이다. 과거 author/전체 재전달/private DLL 복사를 반복하지 않는다.

## 2026-10-13T13:36:48+09:00 — 인간형·Player SFX 후속: 원본 추가 임포트, 현재 사본 검증 중

원작 상위 Composite를 포함한 현재 계획은1682 sound/control occurrence·524 audio sequence다. 승인된 Guard 성공은 기존 attack window의 GuardSound가 한 번 재생하며 Suc pose의 중복3은 제거한다. 원작 sound event 추가51cue/262 leaf recipe를 표적 bank/media 추출로 임포트했고 fallback recipe0이다. 신규 Source raw 총196+6+82+45 파일, 기존 정확 hash/trim media를 재사용한다. Doom/Charge 후반·회전 마무리·회피8방·무기 입출납·약한 피격/착지까지 포함하며 Yetuga/Apes/map은 재저장 대상이 아니다. 원작 기본 idle/공중 hold에 임의 반복음을 넣지 않는다. 원작 callback 시각 미직렬화72 adapter는 원본 media를 쓰되 TEMP first-pose dispatch로 표시했다. Voice .85/foot .9/weapon1, source stop 최소.08초, native reverb send 및 Wwise DSP 차이는 TEMP이며 완전 원작 음향 일치로 기록하지 않는다.

Main Author01의500seq/35combo와51새 cue·추가 media·거리 설정은 저장했다. 최종 계획의 현재 사본은 신규 Khazan_HumanoidSFXWork_20261013/Khazan이며 현재 Main을 새로 읽어570수정 대상만 독립 파일로 복사했다. Old37 prepared payload는 재사용하지 않았다. Main의 독립 background RHI들이 Win32 error32 잠금을 보유해 두 저장 실패는 보존하고 사본 검증으로 계속한다. SavedStage01/02는 이전 같은 발의 중복 audio notify가 KZAudio 밖에 남아 있는 문제를 실제로 검출했다. protected Python Notifies setter는 실패했으며 native DEV editor의 클래스2만 제거하는 작은 authoring command로 수정한다. 아직 Main 최종 완료/믹서 검증 완료가 아니다. 정확한 재개는 ResumeState02.json이며78개 actual-mixer fixture/끝음 actor destroy/loop/cancel과 실제 hit/Guard/Parry/Dodge를 수행한 뒤 baseline hash 보호로 선택 전달한다.


## 2026-10-13T13:50:50.382128+09:00 — GiantVFX 흰 투영의 비파티클 원인 분리

GiantVFX 흰 판 원인 재분리. 단독 Armageddon3 양성만으로 완료를 주장하지 않는다. MainAffectedResume01의 연속23/69PNG에서 재현했고 shock3 material hidden 및 allPSC hidden에도 흰 바닥 strip과 몸체 투영이 남았다. particle/LOD shader 추정은 철회하며 이전 source refraction MI3 재부모화가 이 문제를 해결하지 않는다. 실제 남은 projector/primitive를 확인 중이다. 현재 DecalHideIsolation01은 unsaved owned world의 데칼만 숨기며 경로/material/world location/size를 저장한다. Main 새 art asset 수정0이고 원작 cooked shader/pixel parity 미확인은 유지한다.

## 2026-10-13 — 패링 사진 후속 최신 재개 지점

현재 구현·검증 영수증은 Metadata/ParryPhoto_20261013/CurrentVerification.json이다. 최신 native14/Shader02는 passed이며 정확한 원작 외관은 unverified다. 저장된 후보는 Reference 폴더17+GuardGA1, 명시적 CPU halo slot/life .2s/source growth22/extent125cm/halo intensity4, 별도 PNO distortion/IOR .06/relative-age fade다. Player received-hit None와 공유 공격/혈액 SHA는 보존됐다. SourceCameraShake는 성공 분기에 연결돼17상황/FOV/만료를 통과했다. 전체 original source/실제/임시 수치와 실패 증거는 Art PLAYER_PARRY_SOURCE/Engineering PARRY_IMPLEMENTATION 최신 절에 분리 기록했다.

마지막 asset 저장은 CPUHalo03이며 Extent01의 원본 X250 복원은 error32로 적용0이다. Native13/14와 Isolate02에서 경계 없는 glow/arc를 보았으나 broad violet halo의 실제 DevMap 가독성은 사진보다 약하고 HeinMach 비교는 아직 없다. 다음은 (1) 현재 module manifest가 가리키는 DLL 존재와 다른 editor 잠금/현재 asset SHA 확인, (2) 실제 HeinMach 전투 camera에서 현재 Guard 성공을 캡처하고 광막 mask·밝기·footprint·occlusion을 비교, (3) 필요 시 현재 로컬 M_Parry_Halo/CPU size만 표적 보정. source X250을 그대로 CPU equal axes에 쓰려면 잠금 해제 후 set_parry_photo_source_extent_20261013.py를 새 immutable label로 실행하고 반드시 fresh native/RHI로 검증. 현재125cm를 원작 확인값으로 표현하지 않는다. (4) 굴절만 켠 checker/background 비교는 최신 preview emitter-name 필터(ParryPhotoHalo 포함)를 사용. Isolate02 refraction-only는 오염돼 proof 불가, (5) 최신 camera/17 native/saved shader 검증과 실제 결과를 문서에 추가한다. 원작 shader 자료가 없으면 pixel 동일성은 계속 미확인이다.

다른 Main 작업이 source/manifest를 계속 바꾸므로 오래된 DLL/Blueprint/공유 material 또는 전체 author를 덮어쓰지 않는다. 다른 user/foreign editor를 임의 종료하지 않는다. 정확한 원작 외관이 확인되지 않은 상태를 완료로 기록하지 않는다.


## 2026-10-13T14:14:46+09:00 — Player·인간형4종 SFX 현재 동작·상호작용 Main 완료

현재936 animation/58 ComboDefinition/5 CharacterDefinition/84 grant를 조사해 원작 상위 Composite 음원 누락, 저장되지 않았던 공격 audio array binding, 같은 발/초기 cry·Guard 성공 중복을 보완했다. Main 최종1682 audio/control occurrence·527sequence(소리 제거 callback-only3 포함)·35combo/174attack window·Dodge8 성공음이 저장됐다. 원작 추가51cue/248new wave(262recipe, 동일 원본 재사용14), fallback0이며 원래 chunk0/chunk1 index에서 필요한 metadata/bank/media만 표적 추출했다. Yetuga/Apes·map/ambient 재author0이다. 원작 random choice/gain/media tail/source curve와 현재 Root/FPS/physics/VictimFront·Slash/Parry/피격 VFX 제거를 보존했다.

새 사본의78 actual mesh montage/모든 예상 cue·cancel/loop cleanup·AT actual owner destroy/PCM tail passed, Main 실제 CombatEffect/PlayerAttackCollision/Guard/Parry17/Dodge11 및 현재524+callback3 fresh saved/native pose/curve/root/GUID·non-audio 보존이 passed다. actual master peak.5539245605/RMS.0203483704/clipping0, actor destroy 후 tail peak.0198669434가 관측됐다. Main parry의 near-full-scale.999847을 보고 해당 cue 상단만 TEMP gain.5(−6.02dB)로 낮췄고 실제 재검증 peak.768127/clipping0이다. Dodge 성공은 원본 SC_efx_pc_common_justdodge를 기존 승인 callback에서 실행당 한 번 재생한다. 570asset 선택 전달은 baseline SHA guard/atomic 교체로535새 전달+35동일/lock0/conflict0이며 MainSavedFinal01은1682/527/174/8/238cue success다.

TEMP voice.85/foot.9/weapon1, source stop 최소.08초, native reverb send.05/.15 및 원작 native callback이 직렬화되지 않은72 first-pose adapter를 원작 직접값과 구분한다. 유한 단발음은 action transition/owner destroy 뒤 자연 끝음 유지, loops/source stop만 fade한다. Wwise SDK DSP·모든 장치 주관 청취·Shipping·완전 원작 음향 일치는 미검증이다. 실패도 보존했고 현재 필수 잔여0이다. 정확한 원본/event/field·타임라인/수치·WAV·Main SHA는 Metadata/HumanoidSFX_20261013/FinalVerification.json 및 같은 root의 계획/보고를 따른다. 이전 prepared37이나 전체 extraction/author/old DLL 복원을 반복하지 않는다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

GiantVFX는 Main 선택 반영 및 현재 시각 검수를 완료했다. 처음155case/465PNG와 GAS8+objects3 검증에 더해 최종Saved84 보존, 연속23/69PNG 및 실제 Armageddon GAS 화면/취소 정리를 확인했다. 흰 사각/몸체 투영은 Armageddon_Start의 retained FMI_Decal_Deferred_D_02였다. PS/충격파 숨김에도 지속되고 decal-only 숨김에서 사라지는 증거와 전용 non-emissive spatial alpha 수정으로 해결했다. 원래 noise/얼음/돌 파티클은 제거하지 않았다. 후속 Main 변경은 기존sequence1의 material reference 및 새owned shader2뿐이다. FT_Dirt_Tex_01.R density·radial envelope·KZGiantDecalOpacity .12는 편집 가능한 TEMP 복원이며 roughness .1의 원작 출처 및 숫자 구분은 GIANT_VFX_REFINEMENT_20261013.md 마지막 절에 기록했다. 원작 cooked VAT/distortion/pixel 완전 일치는 미확인이다. exact 완료/실패/backup/current PNG는 Metadata/GiantVFX_20261013/FinalVerification.json, SnowDecalDelivery01, MainSnowDecalFinal01을 따른다. 상태는complete_current_implementation_and_review/잔여0이며 기존 author/Shader clone/전체 전달을 반복하지 않는다.

## 2026-10-13 — WeakAttack01 사용자 사진 후속 방향·전방 확대 착수

사용자 사진에서 첫 약공격의 두 효과 방향이 어긋나고 하나가 몸에 붙는 문제가 확인됐다. 앞선 SlashAlignment의 축/GPU 끝점 합격만으로 이 장면의 실제 밝은 궤적 방향을 합격 처리한 판단은 부족했으며 이번 시각 수정의 완료 근거로 사용하지 않는다. 기존 기록은 보존한다.

현재 소유 범위는 WeakAttack01의 KZFX_bab7be8e310a56b59c0b9461 원래 PlaneSlash와 KZWeaponSlash 추가 효과의 start/end4 객체, 기존 Action receipt/Notify 설명 및 기존 DEV 검수다. 새 runtime class/file/component/manager/tag0이다. 공유 Niagara/mesh/material은 읽기만 한다. Metadata/WeakAttack01Slash_20261013/Before 및 Baseline.json에 실제 이전 파일을 보존하고 Khazan_WeakSlashWork_20261013에서 별도 editor로 작업한다. RuntimeMainApplied.json의 기존 Source3(실행1/설명1/DEV1) 작은 변경만 Main에 적용했고 asset0, 빌드 진행 중이다. 양수 scale·zero offset의 다른 공격 동작은 그대로다. 음향/패링/거대 VFX 작업과 외부 editor를 제어하지 않는다.

후보는 음수 X scale로 radial UV/head를 반사하며 대응 끝점을 선택하고 기존 RelativeLocation을 avatar-local cm로 소비하는 방식이다. 첫 타격 전방35cm/평면 크기1.15배는 사용자 요청에 따른 TEMP 시각 튜닝이며 원작 직접 수치가 아니다. 이 후보는 아직 실제 시각 검증/최종 asset 반영 완료가 아니다. MeshProbe01의 두 Mesh OBJ/UV와 source PlaneSlash를 표적 조회했다. BeforeComposed01은 실제 baseline 성공이나 사진의 문제를 해소했다는 증거가 아니다. 원래 효과 단독 진단01은 생성 문자열 문법 오류,02는 TextureExporterTGA의 unsupported texture assertion으로 실패했고 제품 asset 저장0이다. 해당 own process만 종료/자연 crash 종료했으며 texture exporter는 진단에서 제거했다.

정확 재개: MainBuild01 결과→새 Main module을 별도 작업본에 가져옴→original-only 재생으로 두 효과 식별→author_weak_attack01_slash_20261013.py 후보를 task-private montage에 적용→세 시점/초기·중기·후기 실제 장면과 signed GPU endpoint·forward offset 확인→최신 Main asset의 audio 등 병행 변경을 보존한 선택 반영→fresh saved/Main 실제 RHI→완료 기록. 개인 에디터를 재사용하거나 과거 montage6/full author/private DLL을 Main에 복사하지 않는다.
## 2026-10-13 — WeakAttack01 실제 내려베기 방향·전방 확대 Main 완료

사용자 사진에서 지적한 첫 약공격을 원래 효과와 KZ_Slash로 분리 재생했다. KZ_Slash는 회수 중인 Weapon_L을 따르던 첫 start/end2 객체만 Weapon_R의 FX_R_Sword_02/01로 바꿨다. 현재 실제 장착 Imperial_R는 내려베는 쪽이며 current CPU-skinned LOD0 geometry/포즈는 Metadata/WeakAttack01Slash_20261013/EquippedGeometryObservation.json과 CuttingHandEvidence.json에 남겼다. 이름만으로 원작 내부 실행 손을 확인했다고 설명하지 않는다. UV 반전 후보는 철회했고 최종 scale은 모두 양수다.

요청한 더 앞쪽·더 큰 표현은 첫 타격에만 TEMP 전방35cm/XY1.15배다. 원래 PlaneSlash start/end의 RelativeLocation.X 15.265580→50.265580cm, XY scale1→1.15 및 원래 Z.95 유지. 추가 KZ_Slash start/end는 avatar-local RelativeLocation(35,0,0)cm와 Scale3D(1.15,1.15,1)이다. yaw90/effective span400cm·emitter initial90/XY2·renderer180과 기존 source clock0.334464–0.599631초/CustomTimeDilation1.25는 보존했다. 새 숫자는 원작 검증값이 아닌 사용자 요청에 따른 시각 TEMP이며 소유 notify 설정으로 관리한다.

공유 KZ_Slash/두 ring mesh/원래 FP_DAS_PlaneSlash_Enhanced와 OverFury는 SHA 동일하다. mesh/texture/material/alpha 변경0이며 다른 공격·원래 오디오/clock/GUID/HP·ST·Physics를 보존했다. Main fresh saved는 private FinalAuthor01 전체 serialized export와 동일하며 차이는 첫4 객체의 location/scale/near/tip뿐이다. SourceField의 L 표기는 초기 author 이력이며 현행 Near/Tip의 R override가 정본이다.

실제 MainRHI01의 세 시점289장/초중후·18공격·Brutal4·GPU70 및 MainYaw90RHI01의 회전된 actor 재생을 확인했다. 대표 사진은 MainRHI01/Slash_00_Frame004_View1.png, Slash_00_Frame005_View2.png 및 MainYaw90RHI01 동명 사진이다. GPU0.000031cm는 reference tip+35cm 설정의 검수 오차이며 물리 메시 vertex/원작 pixel 완전 일치가 아니다. 현재 가상 marker와 Imperial_R vertex의13.147cm 차이는 측정 경계로 분리한다. shader compile failure0, 필수 잔여0이다. 전체 증거/실패·철회/백업은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json과 ResumeState.json이며 stale private Source/DLL·실패한 exporter/mirror·전체 author를 재사용하지 않는다.

<!-- WeakAttack01Slash_20261013_complete -->
### 2026-10-13 — WeakAttack01 최종 영수증의 병행 Source 경계

최종 영수증 생성 시 별도 WeakAttack02 Sequencer 작업이 공유 CombatEffect Notify header와 기존 DEV 검수를 추가 수정한 것을 확인했다. 해당 변경을 덮어쓰거나 그 editor(PID19948/WeakAttack02Slash Before03)를 제어하지 않았다. 본 작업의 Action.cpp/Weak montage SHA는 실제 검증 snapshot과 동일하고 avatar-local offset 설명/expected-offset 검사도 보존됐다. FinalVerification.json은 실제 MainBuild04 및 MainRHI01/MainYaw90RHI01의 loaded DLL df9764361d10eec695f0855e34b0dacfb98da06138303a1c8db17cbd7a1f0ed3에 결속하며, 이후 별도 Sequencer 기능까지 본 작업에서 build/검증했다고 표현하지 않는다. CurrentVerification의 pending-yaw 상태는 FinalVerification/ResumeState의 완료로 대체됐으며 WeakAttack01 필수 잔여0이다.

<!-- CombatVFXSequencer_20261013_Continuity -->
## 2026-10-13 18:10 KST — WeakAttack02 시퀀서 VFX 미리보기 확인

편집용 LevelSequence와 메뉴, Main 몽타주 반영 및 fresh 실제 공격은 적용·검증됐다. 사용 절차는 Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md 최신 섹션에 있다. 아직 대화형 에디터에서 Slash 입자 형상이 보이는지 확인되지 않았다. 자동 캡처에서는 Niagara Actor 기즈모, 컴포넌트 Active와 DesiredAge만 확인됐다. 정확한 다음 단계는 해당 LevelSequence를 에디터에서 열어 Niagara 컴파일 뒤 Life Cycle 안의 플레이어 휘두름을 재생·스크럽하고 형상과 칼 궤도를 육안 비교하는 것이다. 재현 시 Engineering continuity의 emitter/renderer 표적 진단으로 이어간다. 전체 몽타주 재작성이나 공유 KZ_Slash 교체는 필요하지 않다.


<!-- CombatVFXSequencer_20261013_VisualResolved -->
## 2026-10-13 18:31 KST — WeakAttack02 Slash 시퀀서 화면 검증 완료

앞 절의 미리보기 형상 미확인 상태는 최신 에디터 전용 갱신으로 해결됐다. 실제 재생과 정지 프레임의 붉은 Slash 화면 및 위치 이동은 Metadata/CombatVFXSequencer_20261013/EditorAutoVisual18/PlayingPreview.png, EditorScrubVisual19/Before.png, After.png를 참조한다. 일시적인 50cm QA 이동은 저장하지 않았다. 현재 WeakAttack02 편집 도구의 필수 후속 작업은 없다. 다른 공격/여러 효과의 시각적 품질은 해당 애니메이션을 선택해 별도 확인한다.

## 2026-10-13 패링 화면 가시성 후속 재개 지점
Main 저장본 GA_Player_Guard, PP_Player_Parry_Reference, BP_Parry_SourceCameraShake, M_Parry_Distortion, M_Parry_ScreenRadialBlur는 VisibilityFollowupVerification.json의 SHA와 같다. HeinCameraRHI03는 실제 Main DLL로 패링 17건 통과, 화면 캡처 3장 저장, shader 오류 0을 확인했다. 기존 PS 크기 250cm 실험은 철회하고 125cm 저장본으로 복원했다. 화면 흐림·분홍 접촉광은 보이나 사진의 넓은 보라 광막은 미완료다. 다시 시작할 때 원작 NewJustGuard와 CPP_PC_JustGuard 자료를 표적 확인하고, 기존 패링 전용 PS/재질만 수정한 뒤 동일 HeinMach 카메라와 실제 플레이어 카메라에서 사진과 비교한다. 일반 피격 파티클 제거·공유 공격 VFX·기존 패링 성공 판정은 유지한다. 이전의 전체 자산 재작성이나 외부 editor 종료/과거 DLL 복구는 재개 절차가 아니다.

## 2026-10-13 — Apes·Yetuga 잡기 화면 검수와 원본 외형 후속 기준

현재 Main의 완성·저장 범위는 `Metadata/GiantGrabs_20261013/FinalVerificationVisualRepair.json`, 네 잡기 RHI 부착 증거는 `Metadata/GiantGrabs_20261013/VisualEvidence`와 원본 Work `VisualPIE7.log`를 따른다. 첫 화면 검사에서 임포트 Player PhysicsAsset 시뮬레이션 때문에 몸이 손에서 바닥으로 처졌고, 최신 손↔목표 소켓 정렬 검수에서는 네 성공 구간 모두 0.000cm였다. 최종 Main RHI PIE 13/13 성공. 원본 `HoldAttachInfo`의 `FallDown` 물리 자산·native secondary blend, Apes FastBall 정확 원본 mesh 및 원작 영상 프레임별 색/포즈 대조는 아직 미확인이다. 대상 10개 root-motion 감사와 네 grab 정렬을 전체 129노드의 시각적 완전 일치로 해석하지 않는다.

재개 시 Router→이 문서의 최신 절→`Metadata/GiantCombatFall_20261011/AuthoringPlan.json`의 해당 HoldAttachInfo/COI 경로→최종 receipt와 7개 화면 순으로 확인한다. 필요한 FallDown PhysicsAsset과 FastBall COI mesh만 FModel 두 chunk에서 표적 추출해 별도 Work에 연결하고, 사용자가 제공한 원작 장면의 같은 카메라·프레임에서 손/몸 각도와 빛·물리 흔들림을 비교한다. 기존 임포트 시퀀스 전체를 일괄 재임포트하거나 현행 Main 손 정렬을 원본 확인 없이 제거하지 않는다. 사용자의 Rider 실행 에디터와 별개인 숨김 백그라운드 에디터로 저장·검증한다.

## 2026-10-13 Apes·Yetuga 모션 연속성 감사 후 재개 기준

현재 Main 완료 근거는 `Metadata/GiantGrabs_20261013/FinalVerificationVisualRepair.json`과 후속 `ImmediateMoveVerification.json`이다. 129 pattern node/118 clip 전체 root 설정·track 순서 읽기 전용 audit는 오류0, source blend129개 불일치0이었다. 5개의 child pose 이동 경고는 참 root가 고정되고 처음/끝 child 위치가 같은 시퀀스이므로 자동 root repair 대상이라고 판정하지 않았다. 애니메이션 에셋 저장/재임포트0. 원작과 나란히 보는 전체 화면 전이 검사는 미실시이므로 사용자가 느끼는 모든 끊김이 사라졌다고 선언하지 않는다.

재개 시 두 보고서에서 특정 clip/전이만 표적 선정하고, 실제 플레이 capture의 해당 프레임·socket/actor 궤적을 원작 동일 카메라 프레임과 비교한다. source `AnimBlendAlpha=0` 10곳은 원작 명시값이라 임의로 늘리지 않는다. 참 root 추출 0인 동작도 의도된 제자리 동작인지 우선 확인한다. Main 게임 에셋은 직전 완료 상태를 유지하고 Rider 사용자의 editor를 종료하거나 재로드하지 않는다.

2026-10-13 최종 RHI 추가: Main 숨김 D3D12 DevMap의 13 패턴 fixture가 Success였다. 실제 화면 129전이와 원작 동일 프레임 비교는 여전히 미완료다.

2026-10-13 원본 pak 추적 추가: 두 pak 표적 index에서 기본 Player PA body17/constraint0와 별도 `C_P_Kazan_Ragdoll_HoldSpine2` body20/constraint19의 metadata/raw를 보존했다(`Metadata/GiantGrabs_20261013/SourceAssetTrace.json`). `FallDown` enum과 별도 PA의 native mapping이 불명이라 physics simulation을 활성화하지 않았다. Apes COI에 mesh field가 없고 projectile composite은 공통 Missile_Skeleton 사용; `FS_Rock_Big_009` 직접 바인딩은 불명이다. game asset/source 추가 변경0. 재개 때 native mapping을 먼저 밝히고 격리 Work에서만 physics/visual probe 후 Main RHI 잡기13 회귀를 반복한다.

## 2026-10-13T23:23+09:00 — Apes·Yetuga 전투·행동 SFX Main 연결 및 실제 믹서 검증

이번 요청의 기존 SFX 정본은 `Metadata/HumanoidSFX_20261013/FinalVerification.json`(Player·인간형 4종)과 `Saved/ImportReports/GameplayAudio_20261011/AudioAuthoringPlan01.json`(7 family 원본 추출)이다. 두 거인은 전자 완료 범위에서 제외되어 있었다. 원본 계획과 현재 Main 에셋만 표적 비교했고 재추출/전수 임포트는 하지 않았다. 현재 Apes 87 clip/253 event, Yetuga 125 clip/448 event 총 701개가 저장된 Audio Notify에 모두 있으며 cue 누락·오연결·추가0, 7개 Sound None은 원본 stop-only 동작이다. 이전 애니메이션 FPS 보정의 150개 타임 차이는 각 1/60초 미만이고 더 큰 차0이라 임의 복원하지 않았다.

최신 Main의 두 `DA_OriginalPatterns_*`에 빠졌던 공격창 GuardSound 42+252=294, pattern object GuardSound 1+3=4, FastBall 비행음 2를 원본 cue에 다시 연결했다. 기존 수신자 Definition의 Apes rock/Yetuga impact2는 유지했다. 저작 전 uasset은 `Metadata/GiantSFX_20261013/MainGiantAudioRepair01/Before`에 보존했고, 공격/오브젝트의 비오디오 구조체 field는 전후 동일하다. 새 음원·gain·타이밍 숫자·runtime class는 추가하지 않았다. `MainGiantSavedAuditFinal/GiantSFXAudit.json`은 별도 새 프로세스에서 701/701, 공격 Guard 294/294, object Guard 4/4, projectile 2/2, 수신자 impact 2/2와 save0을 확인했다.

실제 Main D3D12 AudioMixer의 `FinalMainAudioRHI01/Driver.json`은 저장된 원래 pattern montage/section으로 포효·일반공격·FastBall·잡기·Apes 회피/턴/가드반응·Yetuga Dempsey/IceBreath/RushGrab/Armageddon을 실행했고, 별도 피격/죽음/이동/Player Heal·Dodge·Guard·Brutal 및 취소 루프까지 총26 sample, 두 FastBall Shoot/Impact 비행음이 Success였다. 출력 26+2 모두 peak>0, clipping0, 최종 mix peak0.5286이다. 발리스타 Swordsman `Interaction_Ballista_HandBattle`의 원본 `SC_efx_empiresword_equip`도 `BallistaInteractionRHI01`에서 단독 실제 재생/PCM peak0.10968/clipping0으로 통과했다. 이것은 애니메이션 수동 재생 근거이며 월드 발리스타 오브젝트 사용 경로의 증거가 아니다.

Apes idle `Locomotion_Stand_F_Original_Variant02`에서 Yetuga foley/voice가 들리는 것은 원작 source_package `.../Yetuga/Ani/CA_M_Yetuga_Stand_F`를 공유하는 기존 설계와 일치하여 교체하지 않았다. 시퀀스 단독 dynamic montage fixture는 시작 첫 업데이트(.007~.128초) 안의 일부 cue를 건너뛰었으나, 실제 저장 giant montage의 동일 Dodge/Turn/JustGuard/Roar와 12개 공격 패턴 검사는 통과했다. 이 실패를 실제 패턴 결함으로 표시하지 않는다. 현재 모든 701 event의 실제 모든 전이/카메라·원작 Wwise DSP/RTPC·동시 음성 총량까지 검수했다고 주장하지 않는다. 현행 Source에는 월드 Ballista/상자/문 상호작용의 호출 소유자가 발견되지 않아 해당 객체 사용 중 SFX는 별도 gameplay 구현 때 연결·검증해야 한다. 재개는 Router→Art 최신 절→`Metadata/GiantSFX_20261013/FinalVerification.json`→해당 asset/로그 표적 확인 순서다.

## 2026-10-14 — 플레이어 일반 공격 적중음 에셋 교정 준비본

현재 `DA_Player_Combo_Definition`의 26node/60 attack window 전부에 동일 `SC_efx_pc_dualaxesword_com_impact`가 설정되어 있었다. 원본 Player 약공격에는 각 스윙/foley/voice cue가 별도로 있고, 수신자 Definition에는 원본 Player_Hit 계열의 재질별 body hit이 있다. 일반 타격에서 이 공통 cue가 매번 중첩되는 현행 믹스를 사용자 청취 판단에 맞춰 교정한다. 브루탈 전용 원본 `...grapple_atk_02/03` cue와 무거운 낙하 공격은 그대로 둔다. 이 선택은 원작 native hit caller 동일성의 직접 확인이 아닌 현재 프로젝트 믹스 수정이다.

메인 uasset은 외부 에디터의 Windows 파일 잠금(Error32)으로 직접 저장·교체되지 않았다. `Author02`가 원본 SHA와 backup을 보존하고 해당 Audio 필드만 None으로 만든 준비본을 저장했다. 새 프로세스 `VerifyPrepared01`은 Main common60/준비본0, 비오디오 node 전부 동일, package save0으로 통과했다. Main 파일은 기존 SHA 그대로이며 준비본이 적용된 것으로 기록하지 않는다. 실제 PlayerAttackCollision 오디오 회귀는 새 runtime module에서 material body hit 관측, 공통 cue 미관측, PCM peak0.24237/clipping0을 확인했다. 정확한 경로와 재개 기준은 `Metadata/PlayerImpactSFX_20261013/FinalVerification.json`, Engineering continuity의 같은 날짜 절을 따른다. Main 파일 잠금이 풀리면 최신 SHA 대조 후 준비본을 반영하거나 변경된 부분만 병합한다.

## 2026-10-14 — 플레이어 JustGuard 광막 Main 적용 후 원본 외관 대조 남음

현재 Main Guard GA는 PP_Player_JustGuard_Halo를 저장 참조한다. 원본 PP_AtkEx_JustGuard의 13 emitter를 유지하면서 flare_circle2/refrac/light를 켜고 사용자가 제거 요청한 이동 스파크 3종을 껐다. 원본 line glow 2종은 복원 재질에서 큰 원판·직선으로 보여 비활성화했다. 원본 FT_Flare_004_LSY/T_GradientGlow/ParticleColor와 임시 발광 배율 ParryVisibilityGain=16, UV 경계 feather=.04를 사용한다. 임시값은 원본 직접값이 아니며 사유는 PLAYER_PARRY_SOURCE 최신 절과 Metadata/ParryVFXRebuild_20261013/FinalVerification.json에 있다.

마지막 검증: 저장된 Main 에셋을 별도 새 프로세스에서 읽은 JustGuardMainRHI01에서 D3D12 HeinMach 실제 패링 17/17 통과, 저장0. 02_ActualParryMotion.png에는 보라·붉은 광막과 화면 왜곡이 보이고 표본 프레임에 카드 경계·이동 스파크는 보이지 않는다. 원본 CPP_PC_JustGuard와 파티클 source metadata는 추출됐지만 cooked 재질 shader topology가 없어 원작 사진의 중심 백색·적색 발광 및 프레임별 픽셀 일치까지는 미완료다. center glow 단순 활성화 실험 JustGuardCenterRHI01은 부자연스러운 원판을 만들어 기각했고 저장 package는 이전 hash로 복원했다.

재개 절차: Router→PLAYER_PARRY_SOURCE 최신 절→FinalVerification.json의 파일 hash/원본 route 확인→JustGuardMainRHI01/02_ActualParryMotion.png와 Metadata/CombatVFXReferenceReview_20261013/References/Parry_PinkPurpleHalo.png를 같은 카메라·프레임 기준으로 표적 비교한다. 원본 재질 graph/텍스처 추가 근거가 확보되면 PlayerParry의 전용 material만 격리 작업에서 수정하고, 원본 line glow를 무작정 켜지 않는다. 저장된 Main GA 및 PS를 fresh readback한 뒤 HeinMach D3D12 실전 캡처와 Khazan.Parry.PIE 17건을 다시 검사한다. Shipping/network/performance와 원작 게임의 동일 프레임 비교는 아직 검증되지 않았다.

## 2026-10-14 03:28 KST — PlayerImpact 준비본 Main 적용 완료

앞선 `DA_Player_Combo_Definition` 파일 잠금 대기는 해소됐다. 원본 SHA `0dbdfd3f…` 확인 후 준비본 SHA `6835a167…`를 Main에 반영하고 원본은 `Metadata/PlayerImpactSFX_20261013/MainApply_20261014/Before`에 보관했다. fresh 저장 readback은 공통 cue 60→0 및 비오디오 node 동일을 확인했다. 실제 PlayerAttackCollision audio PIE는 성공, body hit 관측/common cue 미관측/PCM peak 0.26410/clipping 0이다. 이전 continuity의 해당 자산 미적용 설명은 당시 기록이며 현재 상태는 `Metadata/MainIntegration_20261014/FinalVerification.json`을 따른다. GiantGrabWarning/GiantCamera는 별도 진행 중 작업으로 이 전달의 완료 판정 대상이 아니다.


## 2026-10-14 — 패링 공중 내려찍기 굴절 적용 / 원작 시각 일치 잔여

Main Guard에 NS_Player_Plunge_ParringDistort가 저장 연결돼 승인된 패링에서만 카메라 방향으로 재생된다. HeinMach 실제 캡처 Metadata/GiantCamera_20261014/ParryHeinRHI02의 3장에는 붉은·보라 광막과 중심 왜곡이 보이고 사각 카드 경계는 관측되지 않았다. 초기 Deactivate 후 잔류하던 오류는 DeactivateImmediate+DestroyComponent로 해결했고 Main 최신 DLL의 RHI 패링17개가 수명/정상 방어 분리를 통과했다. 근거는 Metadata/GiantCamera_20261014/FinalVerification.json 및 PLAYER_PARRY_SOURCE 최신 절이다.

원작 cooked shader graph와 같은 시점의 참조 영상이 없어 왜곡 세기·광막 형태의 픽셀 완전 일치는 미확인이다. camera pull80 cm/scale .4/tail .25 s는 assistant TEMP다. 재개할 때 Router→PLAYER_PARRY_SOURCE 최신 절→ParryHeinRHI02의 01/02/03 이미지와 Metadata/CombatVFXReferenceReview_20261013/References/Parry_PinkPurpleHalo.png를 같은 카메라·프레임에서 표적 비교한다. 필요할 경우 기존 Niagara 전용 표시 설정만 조정하고 alpha 경계·무잔류를 재검사한다. 저장 Guard fresh readback과 HeinMach RHI 패링17개/정상 방어·종료를 다시 확인한다.


## 잡기 경고 원본 비교 잔여 (2026-10-14)

Main의 Apes·Yetuga 잡기 경고 PS/SFX와 7개 Notify 적용, 빌드, 새 프로세스 저장 재검사, Main D3D12 PIE는 통과했다. 마지막 근거는 `Metadata/GiantGrabWarning_20261014/{AssetImportReport.json,WarningPlan.json,CameraFacingAuthorReport.json,SavedReadback.json,PIE/RuntimeReport.json}`과 `PIE` PNG다. FModel cooked shader graph와 `xxHoldingAttackWarning` 독점 실행 구현은 확보되지 않아 원작 화면의 픽셀·시간별 알파·Wwise 믹스 일치는 미확인이다. 특히 Apes가 몸을 낮추는 긴 경고 창에서는 `UI_Chest`를 따라가는 파티클이 낮게 보이는 프레임이 있다. 원작 같은 프레임의 영상이 있으면 이 잔여를 비교해야 한다.

재개 순서: `0_DOCUMENT_ROUTER.md` → `Docs/Art/GIANT_VFX_REFINEMENT_20261013.md`의 이번 절 → `WarningPlan.json`/원본 `TelegraphMetadata`·`VisualMetadata` → 최종 `PIE/RuntimeReport.json`과 PNG를 읽는다. 원작 grab UI 영상의 동일 공격·카메라 시점과 직접 대조해 위치/알파/수명 차이만 기록하고, 필요한 경우 기존 Material 어댑터 또는 7개 Notify 설정만 표적 수정한다. 수정 뒤 `verify_giant_grab_warning_saved_20261014.py`와 `giant_grab_warning_pie_20261014.py`를 재실행해 7개 저장 및 양 종 화면·음향을 확인하고 Art 문서 하단에 실제 결과를 추가한다. 원본 9-emitter 그래프를 무근거로 일괄 재임포트하지 않는다.


## 2026-10-14 — Player KZ_Slash 전 공격 바깥 배치 완료 및 원작 시각 비교 잔여

메인 몽타주 5개/33쌍 중 32쌍의 추가 Slash 배치를 수정했고 WeakAttack02의 편집 가능한 Sequencer 한 쌍은 프레임 검토 후 보존했다. 격리본 단독·합성 각 99장과 Main 288장, 원래 효과 882개/시간·GUID 보존의 마지막 근거는 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`이다. 원작 게임의 동일 시점/카메라 영상과 직접 픽셀 비교는 하지 않았고 25–100cm/1.12–1.25배는 TEMP 값이다. 재개 시 Router→PLAYER_ATTACK_VFX_PLAYBACK 최신 절→FinalVerification의 공격별 tuning/PairSheet와 현재 Main 다섯 SHA를 읽고, 원작 동일 프레임이 있으면 효과 외곽·색감·밀도만 표적 비교한다. 필요한 Notify 값만 바꾼 뒤 기존 효과882/33쌍 저장 재검사와 D3D12 실제 재생을 반복한다.

## 2026-10-15 — Main 통합 재개 확인 완료

10/14 통합 당시 진행 중으로 분리한 GiantGrabWarning/GiantCamera는 현재 Main 적용 상태다. 오늘 새 프로세스 저장 readback에서 경고 7개·카메라 48/86·Slash 5/33·원래 효과 882 및 중복음 제거가 통과했다. 이전 보고를 덮어쓰지 않고 `Metadata/MainIntegration_20261015`에 별도 결과를 저장했다. 검토한 전달 대상에는 남은 미반영 준비본이 없으며 원작 외관 비교 등 위 절의 추가 검증은 유지한다. 다시 통합을 확인할 때는 Router→현재 도메인 상태→이 FinalVerification/57개 SHA부터 시작하고 과거 author/full delivery를 반복하지 않는다.

## 2026-10-15 — Player KZ_Slash Main 전달 상태 재확인

사용자의 반영 여부 확인 요청에 따라 Main 몽타주 5개의 현재 SHA를 `MainApply/Receipt.json`의 최종 SHA와 다시 비교해 5/5 동일을 확인했다. 이전 단독/합성 시각 검수와 저장 readback의 대상 그대로이며, 미반영 에셋이나 중단된 전달 단계는 없다. 이번에는 에셋을 재저작하거나 재생 검사를 반복하지 않았다. 오늘의 근거는 `Metadata/PlayerSlashOuter_20261014/ResumeVerification_20261015.json`, 시각 배치 정본은 `PLAYER_ATTACK_VFX_PLAYBACK_20261008.md`의 2026-10-14 절이다.


## 2026-10-15 — 잡기 경고 적용 중단분 없음 재확인

2026-10-14 잡기 경고 적용은 Main에 완료돼 있으며 2026-10-15 새 프로세스의 7개 saved binding/9 emitter/음향 로드·최종 SHA 검사도 통과했다. `Metadata/GiantGrabWarning_20261015/SavedReadback.json`이 최신 저장 여부 근거다. 원작 shader·동일 프레임 비교 한계는 위 2026-10-14 continuity 그대로이며 미반영된 에셋이나 중단된 저장 작업을 뜻하지 않는다. 전체 author/import/옛 DLL 전달을 다시 실행할 필요가 없다. 이후 실제 외관 수정 요청이 오면 위 원본 비교 절차에서 이어간다.

## 2026-10-15 — 사망 흰 원판 오류 원인 확정 / Main 8개 연결 제거

Metadata/MonsterDeathWhiteDisc_20261015/IsolationRHI01의 Yetuga·Apes·Heavy 및 검병 변형 전후 이미지는 같은 정지 프레임에서 문제 데칼 하나만 숨긴 비교다. MonsterHuman/FMI_Decal_Deferred_D_02 및 MI_Decal_Deferred_D_00의 복원 parent가 흰 RGB mask를 Unlit Emissive에 출력해 흰 원판이 된다. 원작 shader 동일성이 검증된 연출이 아니다. 두 공유 재질을 전역 수정하지 않고 사망 시퀀스 8개의 해당 DecalMaterial 연결만 None으로 저장했다. 정상 dirt mark·accepted-hit 바닥 혈흔·검은 ash·dissolve는 보존한다. 새 시각 튜닝값 없음.

현재 Authoring.json passed/save8/source0, Notify와 다른 데이터 보존 확인. 수정 직전 Backup/Content와 Before/After T3D를 보관했다. AfterRHI01의 fresh main 재생 18개와 6종 기존 혈흔/사망 회귀는 진행 중이고 실패 원인 없음. 중단 시 Engineering continuity의 같은 날짜 절에 있는 재개 절차를 사용하며 적용된 에셋을 재author하지 않는다. 최종 검증이 끝나면 MONSTER_PRESENTATION_REPAIR_20261011.md와 본 문서에 추가 기록한다.

## 2026-10-15 — 사망 흰 원판 Main 적용 및 회귀 완료

앞의 같은 날짜 진행 중 기록을 대체하는 최종 상태: Main 사망 시퀀스 8개 저장 완료, fresh readback/전체 Notify·나머지 데이터 보존, 실제 D3D12 사망 변형18 Success/문제 흰 데칼0/정상 dirt1 유지, 기존 quick HP=0 혈흔·ash·dissolve 6종 및 경사면/접지 없음/독립 혈흔 수명 회귀 Success. shader compile/fallback 실패0. 작업 소유 editor는 종료했고 미완료/실패/전달 대기 없음. runtime C++ 및 공유 shader 변경이 없어 이번 빌드는 재실행하지 않았다. 실제 로드 Main DLL SHA는 기존 성공 빌드와 같으며 FinalVerification.json에 기록했다.

재개 근거: Metadata/MonsterDeathWhiteDisc_20261015/FinalVerification.json → 해당 도메인 지식 문서의 같은 날짜 최종 절 → 관련 EventId/패키지/Before·After T3D. 완료된 authoring을 반복 실행하거나 Backup 파일을 Main에 일괄 덮어쓰지 않는다. 후속 시각 변경이 실제 필요하면 대상 바인딩을 먼저 확인한 후 필요한 재생 검증만 반복한다.

## 2026-10-15 — 현재 패링 교체 진행

Engineering continuity의 CombatFeel_20261015를 재개 기준으로 한다. Guard의 이전 PP_Player_JustGuard_Halo/바닥용 Niagara/화면 PP runtime 경로를 제거했고, 메인 Guard BP에 사용자 지정 원본 /Game/VFX/03_SlashHit/KZ_Parring_Distort(원본 camera-facing renderer 보존) 및 현재 BrutalFront의 particle 9개 data 복사본을 저장했다. 원본 particle asset/material/Brutal montage와 floor dust/decals는 수정하지 않았다. scale1은 요청 asset native scale, emission tail .5s는 TEMP이며 기존 particle drain/alpha를 유지한다. 아직 실제 RHI 프레임 및 모든 gameplay 회귀 검수는 진행 중이다. Author01 백업3package 및 SourceBaseline, read-only AuditBefore02, root skill audit를 보존한다. 원작 숫자/메타데이터와 사용자 허용 TEMP를 구분한다.

## 2026-10-15 — Yetuga 작은 눈먼지 격자 표시 원인 확인 / 보정 준비

요청은 눈먼지의 시각 배치 품질 수정이므로 Art다. 기존 GiantVFX manifest와 저장된 ParticleObjectCatalog에서 시작해 현재 dust/footstep 23 PS의 all-LOD renderer 및 관련 재질12/texture4만 표적 확인했다. SavedAudit.json passed/save0, 검증 전후 보호 SHA 동일이다. 작은 레이어의 9x9 T_Smoke03_SubUV_9x9가 1x1 SubUV 설정/복원 sampler로 통째로 표시되는 것이 오와열로 보이는 원인이다. Atlas texture를 실제 PNG로 확인했다. Source particle 위치 분산 문제로 단정하거나 임의 random spawn을 추가하지 않는다.

수정 계획: M_KZGiant_SoftSnowMist를 전용 M_KZGiant_SnowFlipbook9x9로 복사해 R-density sampler만 cell별로 선택/보간하고, A05/A06 1x1 instance2의 parent만 변경한다. 기존 soft-alpha/sphere/depth/exposure/tint와 texture·scalar override·PS module·spawn/속도/수명·Notify/행동을 보존한다. grid9x9/81은 현재 원본 imported texture layout, normalized particle-age에 따른 프레임 재생은 source shader 미확인 TEMP 복원이다. 아직 authoring/Main 적용 전이다.

현재 BeforeRHI02(작업 소유 editor PID27728)의 기존 native 리뷰15case=particle7/source 이동·행동6/GAS pattern2가 진행 중이다. Audit01은 FXConverter plugin 미활성화로 실패, Audit02는 명시 enable 후 성공했다. BeforeRHI01은 catalog basename matcher 오류로 gameplay 시작 전 실패했고 해당 작업 소유 PID24268만 identity 확인 후 종료했다. foreign editor는 제어하지 않았다. BeforeRHI02 종료 보고 후 Scripts/Art/repair_yetuga_snow_flipbook_20261015.py를 한 번 실행하고, 새 AfterRHI 프로세스에서 동일15 재생·shader compile·보호 SHA를 확인한다. 적용 후 재개는 Authoring.json부터 확인하여 완료 author를 반복하지 않는다. 미완료 원인은 현재 검증 진행이며 원본 자료나 사용자 답변 대기 아니다.

## 2026-10-15 — HeinMach 색감·빨간 혈흔·VFX 맵 간 색 보존 작업 중

격리본 Khazan_HeinColourVFXWork_20261015에서 작업 중이며 Main 맵/재질/Definition 전달은 아직 0이다. 현재 참조321 system/206 material/97 root는 Metadata/HeinMachColourVFX_20261015/BaselineAudit02/Usage.json에 저장했다. CandidateAuthor01은 VFX 역노출 누락 보정·두 맵 LocalExposure 중립·혈흔 Ground 빨강/작은 역노출 발광·기존 브루탈 Trail_Sub의 Definition7 연결 후보를 저장했다. 첫 광원 FColor RGB 순서 오류는 격리본에서 명시적 채널 지정으로 교정했고 시각 실패 후보는 보존한다. 최신 장면 후보는 CandidateRetune04(청회색 광원/낮춘 노출/주황 Fog 자체발광 교정)다. 수치는 원작 직접값 아닌 TEMP이며 최종 시각 승인 전이다. 정확한 재개는 같은 root의 ResumeState.json이다. ProbeSmokeDev01은 Python 비공개 editor 설정 클래스 접근 실패로 화면 검증 전 중단했고 해당 own PID9060만 종료했다. 수정한 probe의 소량 검사→두 맵321 system 비교→실제 피격/데칼 화면→최신 Main SHA 비교·선택 적용→fresh readback/Main RHI 순으로 남아 있다.
## 2026-10-15 — Yetuga 작은 눈먼지 Main 수정 및 검증 완료

앞선 준비/진행 중 기록을 완료 상태로 대체한다. Authoring.json passed/Main3(새 전용 material1+MI parent2), fresh AfterRHI01 saved readback/동일15 case 실제 재생 Success/shader failure0. SideMove_L_Long/TurnBackRun 전후에서 격자 작은 구름 소실과 한 덩어리 먼지 외관을 확인했다. PS23·보호39·이전 사망 데칼8 SHA 유지, Source/Config/DLL 변경·새 runtime 구조0이다. 원작 shader clock 없는 normalized-age 보간은 TEMP로 기록했다. 작업 소유 BeforeRHI02/AfterRHI01 editor는 종료했고 전달/적용/검증 미완료 없음.

재개 근거: Metadata/YetugaSnowLayout_20261015/FinalVerification.json → GIANT_VFX_REFINEMENT_20261013.md의 같은 날짜 최종 절 → SavedAudit/Authoring 및 해당 MI parent·RepairedExports. 완료 authoring 스크립트는 재실행하지 않는다. shader/외관을 실제 추가 조정할 때만 Scripts/Art/review_yetuga_snow_layout_20261015.py를 KZ_SNOW_LAYOUT_OUT=<새 QA폴더>, KZ_SNOW_LAYOUT_AFTER=1로 실행해 저장 binding/기존15case를 검증한다. 초기 실패 Audit01/BeforeRHI01은 기록대로 보존하고 최종 성공으로 소급하지 않는다. 독립 native build의 현재 모듈을 그대로 사용하며 오래된 DLL/작업폴더를 일괄 복원하지 않는다.


## 2026-10-15 — CombatFeel 패링 시각 진단 갱신

Author01의 full9 임시 연결은 팔/무기 잔상의 큰 회색 geometry와 검은 면이 보여 Author02의 실제 Brutal 접촉 버스트3개로 대체했다. KZ_Parring_Distort 원본/모든 shared Brutal asset은 보존. 개별 layer 진단은 저장0, 기능 검사 통과와 구분한다. Geometry 문제와 최종 RHI는 Metadata/CombatFeel_20261015를 따르며 ENGINEERING_WORK_CONTINUITY의 최신 정확한 재개 절차가 정본이다. FinalRHI01 실제 Parry/6종 lethal pair 전이는 진행 중이다.


## 2026-10-15 ? HeinMach ????? Main ??, ??? ?? ??

Main105 ??? ? ?? readback ??. ?? ?/??? Kuwahara ??2 ??/95 VFX fog ??/?? ??? HEINMACH_COLOUR_VFX_20261015.md ????. ??? ???? Main RHI ?? ??? ??? ??? Metadata/HeinMachColourVFX_20261015/ResumeState02.json. ?? Main author/??? ???? ???.


## 2026-10-15 — CombatFeel 패링 Main 저장·화면 검수 완료

앞선 Author01 full9/FinalRHI 진행 중 기록은 최종 Author02 burst3 및 exact KZ_Parring_Distort 연결로 대체한다. fresh AuditFinal의 Guard CDO/원래 montage 잔여 effect0, 현재 package SHA=Author02, 실제 Parry17/3캡처를 완료했다. source root16 rows도 동일하며 올바른 animation을 재베이크하지 않았다. original/shared VFX asset과 unrelated 세션 변경은 보존한다. 최종 상태와 evidence는 `Metadata/CombatFeel_20261015/FinalVerification.json`, Art 외관 정본은 PLAYER_PARRY_SOURCE 최신 절이다. 필수 미전달/검증 대기 없음. 재개는 현재 저장 binding/receipt부터 시작하고 이미 완료된 full author/import를 재실행하지 않는다.



## 2026-10-15 — HeinMach 색감·혈흔·VFX Main 최종 완료

앞선 같은 날짜 작업 중/최종 RHI 대기 기록을 완료 상태로 대체한다. complete_main_verified/remaining=[]는 Metadata/HeinMachColourVFX_20261015/FinalVerification.json이며 정확한 재개 기준은 ResumeState03.json이다. Main105 SHA 동일/저장 readback 성공, 현재321 system×2맵 native ReadPixels642장 및 왜곡2종 반복12장 검증, build/실제 Main 피격·가드/몬스터6종 혈흔·수명/공격 콜리전3 suite 성공이다. native shader compile/fallback 실패0, QA 저장0, own editor0, Rider/foreign editor 제어0이다.

275쌍의 .2s 가시 신호/46개 대상·다른 시간 필요, 무작위 분포 및 굴절 배경 응답, 원작 shader/pixel parity·Shipping FPS 미확인은 feature 정본에 분리했다. broad CombatEffect의 fixture/AI 간섭/시간초과는 통과로 재명명하지 않는다. 필수 미반영/중단 작업은 없다. 다음 관련 요청은 Router→현재 Art 상태/HEINMACH_COLOUR_VFX_20261015.md 최종 절→FinalVerification/해당 saved metadata 순으로 시작하고, 완료 author/delivery·전체 리소스 추출·이전 DLL/Source/작업폴더 복원을 반복하지 않는다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 ? GiantRootUsage ??4? ???????? ??

????? ?? pose ???? ??? ? giant PartGroggy Loop/End first-frame origin522.148cm? skeleton reference lock?? ??? Main4package? ????. ?? raw first/reference ? ? ?? ??? RepairPlan/Applied/AuditAfter, ?? ?? key/notify/?? ???170 native SHA?4 exhaustive RAW frame?bone SHA? ????. Native170/510??? ?? ?????? D3D12 Start/Loop/End6?/?? Loop?End0cm ?? ???. source Skeleton/curve/texture/material/???/Actor?MeshScale ??0??.

`Metadata/GiantRootUsage_20261015/FinalVerification.json` ? ENEMY_ANIMATION_ORGANIZATION ?? ?? ????. ?? probe? ProbeCleanup?? ???? ?? byte backup4?? Before? ????. ?? ???/?? ??0, ?? author/reimport/??Root??? ???? ???. ?? ??? ??170 ?? manifest ?4?? SHA?? ????.



## 2026-10-15 — HeinMach 더 어둡고 푸른 룩·SpinningAttack 교체 착수

사용자 후속 지시로 이전 HeinMach TEMP 룩을 더 낮은 노출·푸른 분위기로 재검수하고 SpinningAttack의 KZ_Slash를 제외해 OverFury/ChargeAttack 효과를 차용한다. 원작 사진5장과 이전321 system/재질 saved metadata에서 시작했다. 원작의 어두운 푸른 동선 사진과 비교하면 현재 눈의 밝은 면/직접광 대비가 강하고 푸른 그늘이 약하다. 전용 격리본 Khazan_HeinLookSpinWork_20261015를 만들었고 현재 author 허용 대상은 map1/Spinning montage1뿐이다. Main 쓰기0, donor montage/현재 particle321/KZ_Slash/DevMap 총324 package 보호 SHA를 저장했다.

근거/정확한 재개: Metadata/HeinMachLookSpin_20261015/Preparation.json → BaselineAudit02/Audit.json → LookTrials01/Launch.json·Capture.json. BaselineAudit01은 감사 스크립트의 존재하지 않는 FloatParameters 접근으로 save0 실패했고 해당 조회만 제거해02 성공했다. LookTrials01은 own hidden editor의 PIE 메모리에서 Before/BlueA/B/C를 같은 camera/settling으로 비교 중이다. 아직 후보 저장/전달/최종 실제 Spinning 재생은 미완료다. 새 수치는 원작 직접값이 아닌 TEMP look development이며 기존 Source·피해·입력·애니메이션 clock·audio/다른 공격은 보존한다. foreign/Rider editor를 제어하지 않는다.

<!-- HeinMachLookSpin_20261015_intake -->


## 2026-10-15 — HeinMach 포탈 완료 / Main map 보존

현재 필수 잔여0이다. Metadata/HeinMachPortal_20261015/FinalVerification.json, Placement06/PortalLook03/Readback04/RHI06가 최종 근거다. Boss_Start 통로 위치/회전만 한 어두운 shared N_Portal4Boss 후보는 현재 설정이 아니다. 현재는 전장 내부의 HM_Yetuga_ArenaArrival과 전용 NS_YetugaEntrance다.

후속 look/Level 작업은 새 Main의 portal/arrival actor2, ExitPoint 참조, Niagara 상대 yaw90과 전용4asset을 보존한다. 과거 private Work map을 통째로 복사하지 않으며 KZBossPortal class가 포함된 최신 Main DLL로 편집한다. Router → Art 현행 동명 문서 → FinalVerification → 필요한 해당 actor/material만 확인한다. 단순 재감사는 readback script(save0)로 충분하고 author/원본 추출/Content 전수조사는 반복하지 않는다. 전환 gameplay 검증은 Engineering 동명 문서를 따른다.

<!-- HeinMachPortal_20261015_complete -->


## 2026-10-15 — Readback05 최종 스냅샷 보충

동시 Main 저장 뒤 fresh Readback05(save0)가 포탈/arrival2 actor의 참조·transform·범위·암전 시간과 전용4asset/공유 원본 보존을 다시 통과했다. 최종 확인 map SHA는 `62e48f3c26be58069ddfc9d3458787048d51bc7e8714eda9e5ca640e74c5938a`, 영수증 시각은 `2026-10-15T04:28:08.040073+00:00`다. 기존10009 actor 동일과 별도 PlayerStart1 수정, 이 작업 밖의 추가 actor 10개를 구분해 보존했다. 앞선 Readback04 기록은 해당 시점의 기록으로 유지하며 최신 근거는 FinalVerification.json의 Readback05/RHI06이다. 실제 walking·암전·전장 이동·복구 Success 이후 게임 Source/자산을 추가 수정하거나 사용 중인 editor를 reload/save하지 않았다. 현재 요청의 필수 잔여0이다.

<!-- HeinMachPortal_20261015_readback05 -->


## 2026-10-15 — HeinMach Blue/Spinning 검수 갱신·Main 전달 전

최신 feature는 HEINMACH_BLUE_SPINNING_20261015.md다. 격리 map BlueB/Spinning montage/Spin-only OverFury PS3개 저작·saved 검사가 완료됐고 Main 쓰기0이다. 후보 PS는 두 헬릭스 Required.Material만 기존 zero-output 재질로 교체했다. 기존 original176/clock/GUID·donor montage2·원래 PS321 및 보호324 SHA 유지, SpinRefinedRHI05의 실제 Spinning 선택+공통 수명/취소·적중/브루탈 및 PlayerAttackCollision 성공이다. 원래 Spin/ChargeStreak/Vortex 단독 제외로 회색 면은 남았고 Spin 사본의 헬릭스2를 가린 뒤 소실했다.

색 비교의 앞선 VFXDev02/Hein02·FlagRepeat 결과는 최종 합격 근거로 사용하지 않는다. 작은 효과의 측정에 화면의 빨간 VRAM 경고가 섞였으며, pause 직후 ReadPixels가 이전 렌더 버퍼를 읽어 다른 효과/프레임이 찍히기도 했다. 이제 DisableAllScreenMessages는 QA에만 적용하고, .2s에서 simulation을 pause한 뒤 실제 렌더를 기다려 읽는다. VFXDevFinal03은 .12s 대기322 완료, VFXHeinFinal03은 GetFrameCount 기반2frame 대기322 실행 중이다. shader/fog/게임 동작을 이 촬영 오류에 맞춰 임의 변경하지 않았다. 표적 FlaggedAudit01에서 Yetuga Grab/Roar의 원래 blue–cyan random StartColor 범위와 IceDebris의 DefaultLit을 확인했다. 물리 얼음의 조명 반응과 무작위 분포·대상 필요 효과를 원작 픽셀 일치로 확대하지 않는다.

정확한 재개는 Metadata/HeinMachLookSpin_20261015/ResumeState02.json이다. current own editor는 VFXHeinFinal03/Launch.json의 PID20888, 로그/Progress/Exit를 확인한다. 완료되면 두 Final03을 비교·실제 support 영역과 사진으로 flag를 분류 → ColourComparison01/Review.json에 canonical report와 검토 경계를 기록 → deliver_heinmach_look_spin_20261015.py MainDelivery01로3개 CAS → fresh MainSaved01 및 실제 Main scene/Spinning 검수 → FinalVerification/완료 MD 순이다. CandidateAuthor/SpinHelixRefine03을 반복하거나 과거 전체 Source/DLL/work 복사본을 Main에 복원하지 않는다. 원래 실패와 중단은 보존했고 사용자/Rider/foreign editor 제어0이다.

<!-- HeinMachLookSpin_20261015_renderer_corrected_pending -->


## 2026-10-15 — HeinMach Blue/Spinning 최종 완료·재개 기준

앞선 renderer corrected pending 및 Main 쓰기0 기록은 완료로 대체한다. MainDelivery01은 최신 map 충돌을 쓰기 전에 거절했고, 현재 schema/새 포탈 의존4개를 Work에만 보완해 MapRebaseAuthor03→RebasedSaved02→MainDelivery02의3개 선택 전달을 완료했다. MainSaved01의 portal/arrival·새 몬스터·PlayerStart 보존, MainScene01 실제3시야, MainHeinSpin02의 실제 HeinMach 공격 초·중·후기/cleanup·충돌과 MainDevSpin01의2 suite 및 Final03 두 맵322씩을 검수했다. HeinMach broad suite의 별도 rear-Brutal fixture 실패는 그대로 보존한다. 외부 editor 제어0, Source/Config/DLL 전달0이다.

정확한 현재 상태는 Metadata/HeinMachLookSpin_20261015/FinalVerification.json 및 ResumeState03.json. 필수 잔여=[]이며 원작 pixel/shader·Shipping FPS·42개 다른 조건의 외관은 별도 한계다. 물리 조명/굴절 반응까지 VFX 완전 우회를 주장하지 않는다. 다음 요청은 현재 Main과 final receipt부터 시작한다. MainDelivery01/완료 author/refine/전체 추출이나 과거 private map/Source/DLL 복원을 재실행하지 않는다. 이전 실패·중단·촬영 오류는 보존하며 원래 Rider/foreign 에디터에는 손대지 않았다.


추가 동시 저장본은 MainLatest01에서 poses/montage/light/fog/PP 동일, MainLatestSaved02에서 현재 저장·포탈 계약을 확인해 보존했다. 최종 현재 map SHA는7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728이며 이전 전달 SHA와 구분한다. 최신 파일을 옛 전달 바이트로 복구하지 않는다.

<!-- HeinMachLookSpin_20261015_complete -->

## 2026-10-15 — Yetuga BGM 임포트 완료·재개 지점

Main 음악4asset 저장이 Import01(exit0)에서 완료됐다. 실패/누락 잔여0이며 map와 기존 sound asset은 저장하지 않았다. fresh 원본4event/3bank/1WEM·SourceMusic.json·decoder recipe·Import01/Import.json을 보존했다. 실제 전투/스피커 청취와 원작 전체 Wwise DSP/sample parity는 미검증이다. 상세 정본 YETUGA_BGM_SOURCE_20261015.md 및 Metadata/YetugaBGM_20261015/Implementation.json을 먼저 읽는다. 전체 음악/SFX 추출·성공한 importer를 반복하지 않는다. 후속 변경이 필요하면 기록된 정확한4 경로와 source hash만 확인하고 별도 run 폴더에서 필요한 자산만 갱신한다. 기존 importer는 이미 있는 asset에서 의도적으로 중단하므로 완료 후 그대로 재실행하면 안 된다.

## 2026-10-16 — HeinMach 사용 구간 밖 오브젝트 정리 착수

사용자가 PlayerStart부터 Yetuga 입구 포탈까지의 이동·전투 구간과 Yetuga 전장만 사용하며, 그 외 사용 시야에 영향 없는 메시·포인트 라이트 등 level object를 삭제하도록 명시했다. Art 범위이며 기존 몬스터/PlayerStart/포탈·도착점·플레이 지면과 사용 구간에서 보이는 배경/조명 영향을 보존한다. 공유 Content 에셋 파일 삭제나 게임 C++ 변경은 하지 않는다. 이전 원본 배치 전량 보존 원칙은 이번 명시된 불필요 배치 삭제 범위에 한해 대체된다.

Main 최신 map을 Metadata/HeinMachRoutePrune_20261016/Before에 백업하고 Khazan_HeinMachPrune_20261016/Khazan의 같은 package 경로로 독립 map 사본을 준비했다. 공유 Content/Plugins/Source는 읽기용 junction이며 author는 독립 Content/Maps의 맵만 저장한다. Main map baseline SHA 및 Source/Config SHA는 Baseline.json이다. 현재 Inventory01에서 최신 actor/component world bounds·HISM instance transform·지역 light 영향 반경을 읽는다. 기존 MainLatestSaved02 poses만으로는 실제 삭제 가시성을 판정할 수 없어 현재 단일 레벨의 표적 inventory를 만든다. 전체 FModel/Content 재조사0이다.

진행: 현재 실제 사용 구간과 전장을 경계/지형/시야로 판정 → 사용 구간 밖 후보를 가시성 및 조명·그림자 영향으로 보수적으로 분류 → 격리 맵의 전후 화면·보존 actor/지면/포탈 readback 확인 → Main baseline hash가 같을 때 선택 전달 → fresh Main 검증. 삭제 내역과 재생성 방지 목록·복구 경로를 남긴다. 현재 Main 변경0, 완료/성능 향상/전체 시야 동일을 아직 주장하지 않는다. 소유 프로세스와 정확한 실행은 Inventory01/Launch.json·Editor.log·Exit.json, runner는 Scripts/Art/run_heinmach_route_prune_20261016.py다. 외부 에디터 종료·저장·reload0.

## 2026-10-16 — 게임 발표자료 아트·화면 초안 / Google Slides 연결 대기

카잔 아트 콘셉트와 보라/빨강의 15장 발표 초안이다. 배경 #130C20, 보라 #B49AFF, 빨강 #F14B63은 발표 디자인 선택이며 게임/원작 수치가 아니다. 표지는 SEGA 공식 배포 Khazan key art를 사용하고 출처·권리를 deck.json notes에 기록했다. 본문은 기존 HeinMach 환경/브루탈 UI/포탈/눈 접촉 전후/혈흔 실제 화면7종을 재사용했다. 게임 아트/맵/재질/VFX/Source 수정과 새 게임 capture/build/PIE는0이다.

눈은 collision contact의 압축 field와 Nanite 변위/normal/PBR이라는 현재 계약으로 설명한다. physics collision/NavMesh의 동적 재조각 또는 원작 VHM shader 완전 복원을 주장하지 않는다. 혈흔은 KZMonster::PlayHitBlood의 GetSnowSurfaceHeight·법선 정렬·투영 깊이 보완·자체 fade가 근거다. 과거55cm를 현행 값으로 소개하지 않았다.

Metadata/GamePresentation_20261016의 deck.json/AssetManifest.json/ResumeState.json, assets와 preview/index.html·PNG15장이 재개 근거다. portal은 A=0, blood도 framebuffer alpha 문제가 있어 원본을 보존하고 RGB 포맷 변환본을 만들었다. read-only RGB pixel 비교는 두 장 모두 차이0이다. 포탈은 슬라이드에서 플레이어/포탈 영역을 크롭했다. HTML15장 개별 검수 완료, native Slides/PPTX 생성·Google 변환/검수0이다. Google Drive 연결/사용자 대안 답변과 authoring runtime 제공이 대기 조건이다. 기존 초안으로 Slides 생성·검수·URL 전달을 이어가며, 병행 HeinMach route prune의 에셋/문서 상태를 보존한다.

<!-- GamePresentation_20261016_art_prepared_waiting_connection -->

## 2026-10-16 — 게임 발표자료 연결 확인 후 재개 상태

Google Drive 설치는 installed=true로 확인됐으며 사용자도 계정 연결 완료를 보고했다. 현재 기존 대화에는 Drive/Slides 작성 도구와 PPTX 제작 runtime이 로드되지 않아 native 생성0이다. 앞선 설치/연결 대기와 구분한다. 기존 보라/빨강15장, 실제 게임 화면·공식 key art, RGB 파생2장 및 개별 검수된 HTML은 변경 없이 보존했다. 현재 exact 재개 기준은 Metadata/GamePresentation_20261016/ResumeState.json 및 ConnectionCheck02.json이다. ChatGPT 데스크톱의 같은 프로젝트 새 채팅에서 새로 설치된 도구를 불러와 기존 원고·이미지로 native Slides 제작/검수/URL 전달을 계속한다. 새 아트·맵·게임 Source 변경과 새 게임 촬영0이다.

<!-- GamePresentation_20261016_art_drive_installed_session_tools_missing -->


## 2026-10-16 ? HeinMach ?? ?? ?? ?? ?? ????? ?

Inventory01 10,022 actors/14,776 HISM instances. Depth03? 92 camera anchors ?6=552 ?? SceneDepth ?? ?? ??/? ?? ???/?? ??? ??? ?? ?? actor4,216 + instance9,137? Selection.json? ????. Compare02? ?? PIE?? ?? ??48?(??749?381)? ??? ???? Sheet_00?05? ?? ????. ?? ??/?? ??? ???? ???? ???? ??? ?? temporal ?? ??? ?? pixel identity? ???? ???. ??? ?? ?? ?? ??1.82e-12cm. ??? HISM batch42?? ????? ?? ?? actor??4,258??. VisualReview.json? ??/??? ????.

Main map? ?? baseline SHA7b072b9b ????. ??? Author01(author mode)?? ?? ? ??40??????? ??13? nav projection/11 route? ?? ?? ??, navigation ?? ? ? ??? ?? ? Work fresh verify_scene ? actor/instance ??? ? Main hash CAS ?? ? fresh Main ????. ?? runner? Scripts/Art/run_heinmach_route_prune_20261016.py, ?? author? work identity+baseline SHA+VisualReview ?? receipt? ??? ????. ?? ?? ??/QA ?? ????? ?? tuning? ???.

?? ?? ??: Depth01? HiddenActors Python property ?? ??, Compare01? get_character_movement API ????. HiddenActors? hide_actor_components?, CMC? get_component_by_class? ???? ?? run?? ????. Depth02? ?? ?? ray? ?? ?? ??? ?? ??? authored Z+50 ????? Depth03?? ????. ?? ?? report? ??? ?? ???? ???? ???.


## 2026-10-16 ? HeinMach ??? ?? ?? ????? ??

?? ??/?? ? ??? Main ??? ????. Author01 ???MainBaselineScene01 ?? warm RHI?WorkSaved02 ?? ?? ???MainDelivery01 CAS ???MainSaved01 fresh RHI/?? ?? ???instance transform ??? ????. main SHA1d224b14ae0ec39b90229e2a122b174b672ca64d976f3c0ef0032236c47f7c00. actor4258/instance9137 ??, Source/Config diff0, ?? resource asset ??0. instance ??? foliage8296+??? ?? ??841?? ?? ????9137 ??? ????.

?? NullRHI/commandlet? warm editor collision ??? WorkNull01?02/?? InventoryVerification ??? ????. ??? ???? ?? warm RHI? ???? WorkSaved02/MainSaved01? collision/visibility?? ???? ????. ???? ? ??? ???? ???. final ??? FinalVerification.json ? HEINMACH_ROUTE_PRUNING_20261016.md, ??? Before umap? RoutePruneExclusions ????. ?? ??=[], ?? ??3 partial??? ?? ????? Shipping ???? ??? ????.

?? ? ?? Main? final receipt?? ????. ?? author/delivery? whole-map/foliage ??? ???? ???. ??? ? ??? ??? ?? Main ??? ? run ???? ????, ?? ??? ?? Main ??? ???? ??? actor/component/transform? ????. ?? editor? ?? ?? ???? ?? editor/Rider ??0??.


## 2026-10-16 — HeinMach 구간 정리 최종 완료 (한글 기록 정정)

앞선 이 작업의 일부 진행/완료 절은 PowerShell→Python stdin 인코딩 때문에 한글이 깨졌다. 게임 맵·JSON 검증에는 영향0이며 신규 feature 문서는 UTF-8로 바로잡고 오류본을 Metadata/HeinMachRoutePrune_20261016/DocumentationEncodingBackup에 보존했다. 기존 문서의 과거 절은 보존하며 이 절로 정정한다.

Author01 저장→MainBaselineScene01 원본 warm RHI→WorkSaved02 같은 조건 비교→MainDelivery01 CAS 전달→MainSaved01 fresh RHI 및 retained 전체 설정/transform 검사를 완료했다. Main SHA1d224b14ae0ec39b90229e2a122b174b672ca64d976f3c0ef0032236c47f7c00. actor4258/instance9137 제거이며 instance는 foliage8296+미사용 경로 충돌841이다. 앞선 풀·나무9137 표현도 이 세부 분류로 정정한다. 몬스터10/PlayerStart1/포탈·BGM·룩 보존, Source/Config diff0, 공유 resource 저장0, 필수 잔여=[].

Depth01/Compare01 API 오류 및 Depth02 지면 높이 오류는 각각 Depth03/Compare02에서 보정했다. 즉시 NullRHI collision snapshot 차이로 실패한 WorkNull01·02 등은 그대로 보존했다. 같은 warm RHI의 원본/변경본 비교는 collision/visibility까지 동일하고 성공이며 차이 항목을 무시하지 않았다. 전후48시야·depth552·지면40/투영13, 기존 경로8 complete+3 partial 유지다. 자세한 근거/한계는 HEINMACH_ROUTE_PRUNING_20261016.md와 FinalVerification.json이다. 기존 Shipping 미갱신/FPS 미측정은 별도 한계다.

재개는 현재 Main과 final receipt부터 확인한다. 완료 author/delivery/whole-foliage 복원을 반복하지 않는다. 새 변경은 현재 Main 독립 사본과 새 run 폴더에서 시작한다. 삭제 복구는 Before 원본과 Player metadata RoutePruneExclusions를 대조하고 이후 사용자 변경을 보호해 정확한 actor/component/transform을 선택 이관한다. 소유 에디터는 정상 종료했고 외부 editor/Rider 제어0이다.

## 2026-10-16 — 게임 발표자료 native Slides 화면 검수 완료

기존 보라/빨강15장과 공식 key art·프로젝트 화면8개 배치를 native Slides로 완성했다. 이미지8개는 눈 비교2개를 포함하며, 원본 이미지7종과 공식 key art를 사용했다. 포탈 source939x510의 crop174/146/592/352를 적용해 과확대를 수정했다. 텍스트·표는 rasterize하지 않았다. Google 변환 PDF15장 전체 개별 검수에서 글자/이미지 누락·겹침·잘림이 없었다. 출처/권리와 눈 표현·원작 일치 검증 한계는 notes에 보존했다. 원본 asset·게임 화면 새 촬영·맵/재질/VFX 수정0이며 병행 HeinMach 정리 작업은 건드리지 않았다. Metadata/GamePresentation_20261016/FinalVerification.json과 build/google-render가 완료 근거다. 최종 URL과 후속 편집 절차는 Engineering continuity의 같은 날짜 완료 절을 참조한다. 이전 연결/도구 대기를 완료로 대체한다.
