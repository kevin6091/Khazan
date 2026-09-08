# 2026-09-07 StormPass 실제 경로·표면 렌더링 재검토

## 작업 경계

- 대상은 `L_StormPass_Environment`와 이 맵의 환경 에셋뿐이다. Source, Animation, Gameplay, HeinMach는 수정하지 않는다.
- 사용자 요청에 따라 기존 오늘 작업도 최종 Git 커밋·main push 대상에 포함하되, 내용을 변경하거나 롤백하지 않는다.
- 시작 전 맵 백업: `Saved/ArtBackups/StormPass_PreRoutePresentation_20260907/L_StormPass_Environment.umap`, SHA-256 `E1007AFFEAE22AF49599690EB3CE67582B1B43FC25C8D3E6AFBE17B76C03361D`.
- 기존 사용자 변경 258개 파일/삭제는 `StormPass_UserWork_Baseline_20260907.json`과 `Scripts/StormPass/snapshot_user_work.ps1`로 해시·부재 상태를 검증한다.

## 확인된 기존 감사의 공백

- 기존 14,408 actor / 17,979 material slot 검사는 원본 좌표 및 바인딩 존재를 확인했지만, 플레이 시작 시 실제 화면 품질을 보장하지 않았다.
- 원본 `Mission02_Start`는 `(30357.803, 60165.047, 2183.912)`, yaw `-21.012077°`이다. 현재 맵에는 PlayerStart가 없었다.
- 시작 위치 Lit 캡처에서 대부분의 지형/목재가 검게 보인다. 조명 없는 비교 화면에서는 diffuse 텍스처와 경로가 나타나므로 텍스처가 전부 없는 문제가 아니다.
- 실사용 환경 MI 557개 중 542개가 USD 부모였다. 초기 정밀 감사에서 534개의 packed-channel 연결 오류, effective Translucent 54개를 확인했다. bespoke tree/ore/water graph 15개는 USD 수리 대상에서 제외한다.
- USD 변환은 `Roughness=B, Metallic=G`를 사용했으나 프로젝트에서 검증한 원본 환경 packed layout은 `AO=R, Roughness=G, Metallic=B`다. 목재·석재가 매끈한 금속처럼 렌더링되는 원인이다.
- 부모 이름만으로 BlendMode를 판정하면 안 된다. 자체 Masked override가 이미 있는 MI도 많다. 실제 상속 결과와 원본 full-package JSON을 함께 검사한다.
- 일부 `_opaque` 원본은 `bOverride_BlendMode=true`이지만 enum 값이 JSON에서 생략돼 있다. 이것은 기본 enum 값 `BLEND_Opaque=0`이며, 부모의 Masked를 상속하라는 의미가 아니다.

## 배치·경로 근거

- `StormPass_PlayableCameraAnchors.json`에 원본 PlayerStart 18개와 attachment chain을 합성한 world transform, 스트리밍 구역 26개, 레이어 52개를 기록했다.
- 원본 `StormPass_All`의 Boss Phase 1 / Phase 2 / Clear는 각각 독립 streaming level이다. `bInitiallyLoaded=true`는 동시에 보이게 하라는 뜻이 아니다. 원본 시작 구역 `LSV_01_StartPoint`의 표시 목록에도 보스 페이즈들은 없다.
- 한 맵에 이들을 모두 평탄화하면서 다른 페이즈의 수 km 규모 배경 산들이 일반 경로까지 감싸고 차폐할 수 있는 상태였다. source transform을 이동하거나 지형을 삭제하는 방식으로 처리하지 않는다.
- FModel 원본 Landscape 삼각형을 시작/체크포인트 18곳에서 표적 샘플링했다. 해당 위치 위를 덮는 Landscape는 없었다. 시작점은 Landscape 표면보다 105.63 cm 위다. 동굴·다리 구역의 실제 바닥은 별도 static mesh이므로 Landscape 높이만으로 바닥/충돌을 판정하지 않는다.
- 기하 감사: `Scripts/StormPass/audit_stormpass_route_geometry.py`, `Saved/ImportReports/StormPass_RouteLandscapeGeometry_20260907.json`.

## 진행 체크포인트

- `repair_stormpass_surface_rendering.py`가 사용 중인 MI만 검사하고, 기존 slot provenance report와 source USD reference로 원본 JSON을 정확히 대응한다. basename 추측은 사용하지 않는다.
- 수정 전 각 `.uasset`을 백업하며 원본 alpha/Masked/TwoSided/clip을 유지한다. Source 배열과 Fog/물/bespoke graph를 일괄 재생성하지 않는다.
- 조명·색보정·가시성 비교는 임시 상태이며, 최종 저장·재시작 검증 전에는 완료 판정하지 않는다. 기존 최종 감사의 `passed`만으로 이 요청을 완료 처리하지 않는다.
- 남은 순서: 표면 수정 완료 → 실제 경로 캡처 → 페이즈 표시/시작점 복구 → 조명 검증 → Fog 최종 검증 → fresh-editor 감사 → 사용자 변경 보존 검증 → commit 및 non-force main push.
