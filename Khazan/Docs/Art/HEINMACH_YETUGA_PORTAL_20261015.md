# HeinMach GateCube 포탈 배치

## 2026-10-15 — 착수 / 표적 조사

사용자가 배치한 `GateCube`는 현재 `/Game/Maps/L_HeinMach_Environment`의 `StaticMeshActor_3219`이며 좌표 (19550,4270,-130)cm, yaw20°의 Engine Cube다. 기존 환경·광원·재질을 복원하거나 교체하지 않고, 이 위치에 기존 Niagara 포탈을 배치한다. locator의 transform은 보존하고 게임 중 표시와 solid collision만 끈다. 실사용 포탈 1개와 도착 TargetPoint 1개가 추가된다.

원작 전장 입구는 기존 `Saved/ImportReports/HeinMach_PlayableCameraAnchors.json`의 `Mission01_Boss_Start`를 재사용한다. source actor `xxPlayerStart_1` attachment chain으로 계산된 world position과 yaw를 출처로 삼고 현행 지면 collision에 맞춘 Z는 적용 실측으로 구분한다. 포탈의 실제 크기/회전·alpha·Niagara 외관과 바닥 배치는 후속 실제 RHI 확인 결과를 아래 추가한다. 전환 동작·입력·실패 cleanup은 `Docs/Engineering/HEINMACH_YETUGA_PORTAL_20261015.md`의 책임이다.

첫 read-only 표적 감사는 `Metadata/HeinMachPortal_20261015/Audit01/Audit.json`(10010 actors/dirty0/save0)이다. Content/FModel 전수조사나 기존 VFX 원본 재임포트는 하지 않았다. 동시에 진행 중인 HeinMachLookSpin의 조명·맵 변경은 최신 디스크를 기준으로 보존해야 한다.


## 2026-10-15 — 최종 배치·외관 Main 완료

GateCube의 원래 transform은 보존하고 게임 표시·solid collision만 껐다. `HM_Yetuga_EntrancePortal` 중심은 (19550,4270,-6.752918548882)cm, entry half extent는 TEMP (80,140,160)cm다. portal/arrival 두 객체는 Gameplay/YetugaPortal 폴더에서 편집한다. 최신 도착점은 전장 내부 (-3761.6345,-11455,-4572.605507799506)cm, yaw156.25044846566882°이며 원작 Yetuga_TargetPoint의 XY와 현행 맵의 지면을 사용했다. 초기 Boss_Start는 전장 직전 통로여서 최종 목적지로 폐기했다. source RootComponent export470의 원시 위치와 SA_Yetuga export450까지의 방향 계산·TEMP 목적지 선택을 구분하며 정확한 원본·SHA는 Readback04와 Placement06에 있다.

현재 `/Game/VFX/Portal/YetugaEntrance/NS_YetugaEntrance`는 기존 N_Portal4Boss의 전용 사본이다. 실제6 renderer의 재질을 전용 master sprite/MI/core material 3개로 연결했으며 공유 원본4파일은 SHA 동일하다. 포탈 plane은 XZ이므로 컴포넌트 상대 yaw90으로 gate의 통과 방향을 향하게 했다. 재질 발광에 엔진 EyeAdaptationInverse Alpha1을 사용해 물리 노출에서 꺼지던 core를 보완했다. 색·alpha·blend·MI parameters와 입자 simulation/분산은 원본을 유지한다. 재질 compile error0이며 원본 graph를 추출 불가한 Khazan 원작 shader라고 주장하지 않는다. 기존 Fab portal의 현행 맵 적용이다.

Main D3D12 RHI06의 실제 game viewport에서 청록색 안개 gate, 진입 암전, 전장 내부 도착을 검수했다. Entry/Black/Arrival3장과 실제 PNG 해상도/해시는 FinalVerification.json에 있다. 이전 VisualTrials02의 회전만 한 어두운 후보와 RHI02/03/04 QA 실패는 최종 완료본으로 오인하지 않는다. 원본 alpha/blend/MI parameters와 공유 원본4파일 보존을 fresh saved Readback04에서 확인했다. 포탈 배치 시 기존10010 actor transform/class를 보존했고, 그 뒤 Main 동시 저장에서 이동한 PlayerStart1개는 되돌리지 않았다. 최신10009 actor 동일 및 PlayerStart의 전후 transform을 별도로 기록한다. Source/전환 수명 검증은 Engineering 동명 문서에 분리했다.

동시 HeinMachLookSpin 작업은 이 최신 Main map을 보존해야 한다. 오래된 Work map 전체를 복사하면 portal/arrival actor가 사라진다. Main 최신 Source로 빌드된 DLL을 사용해 필요한 look 필드만 반영하며, KZBossPortal class가 없는 과거 private DLL로 최신 map을 열어 저장하지 않는다. 완료 영수증의 map SHA/두 actor/전용 Niagara 참조를 반영 후 다시 표적 확인한다.

<!-- HeinMachPortal_20261015_complete -->


## 2026-10-15 — Readback05 최종 스냅샷 보충

동시 Main 저장 뒤 fresh Readback05(save0)가 포탈/arrival2 actor의 참조·transform·범위·암전 시간과 전용4asset/공유 원본 보존을 다시 통과했다. 최종 확인 map SHA는 `62e48f3c26be58069ddfc9d3458787048d51bc7e8714eda9e5ca640e74c5938a`, 영수증 시각은 `2026-10-15T04:28:08.040073+00:00`다. 기존10009 actor 동일과 별도 PlayerStart1 수정, 이 작업 밖의 추가 actor 10개를 구분해 보존했다. 앞선 Readback04 기록은 해당 시점의 기록으로 유지하며 최신 근거는 FinalVerification.json의 Readback05/RHI06이다. 실제 walking·암전·전장 이동·복구 Success 이후 게임 Source/자산을 추가 수정하거나 사용 중인 editor를 reload/save하지 않았다. 현재 요청의 필수 잔여0이다.

<!-- HeinMachPortal_20261015_readback05 -->

## 2026-10-15 — GateCube 큐브 메시 연결 제거 Main 완료

사용자 후속 요청에 따라 GateCube의 StaticMeshComponent에서 `/Engine/BasicShapes/Cube.Cube` 연결을 비워 `StaticMesh=None`으로 저장했다. 이전의 게임 중 숨김뿐 아니라 에디터에서도 큐브 geometry가 표시되지 않는다. GateCube 액터·컴포넌트·transform은 유지하며, 포탈/도착점의 위치·Niagara·진입 범위·충돌·암전 시간은 변경하지 않았다. 최신 동시 작업이 반영된 Main map SHA `ff7c68d9fd99474aabbb6289eb38ee0cbe6962bd3baee9e5e88d34dede6fee91`에서 시작했으며 과거 포탈 완료 시점의 맵으로 되돌리지 않았다.

적용 근거는 `Metadata/HeinMachPortal_20261015/GateCubeVisibility01/Result.json`(map save1), 별도 새 프로세스의 `GateCubeVisibilityReadback02/Result.json`(save0)이다. 저장본 mesh 없음/게임 숨김/큐브 충돌 비활성 및 포탈 계약 보존을 확인했고 actor 수10022도 유지된다. 최신 map SHA는 `7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728`이다. Readback01은 검사 코드의 tuple/list 비교 오류로 실패했고 게임 저장0이며, JSON 자료형을 정규화한02가 통과했다. 관련 없는 임시 dirty audio package는 저장하지 않았다. 게임 C++/공유 Cube 에셋/포탈 VFX 수정·새 빌드·PIE 재실행0이다. 기존 전환 PIE 검증은 앞선 완료 기록을 따르며 이번 검증은 저장 상태 확인이다.

필수 잔여0. 후속 작업은 이 최신 저장본을 유지한다. GateCube의 bounds로 초기 배치를 계산하던 이전 author script를 다시 실행하지 않는다.

<!-- HeinMachPortal_20261015_gate_cube_removed -->
