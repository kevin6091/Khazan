# HeinMach 동굴 입구 → Yetuga 전장 포탈

## 2026-10-15 — 직접 구현 착수 / 소유권

사용자 요청은 GateCube 위치의 자동 진입 포탈과 암전 후 같은 HeinMach 월드의 Yetuga 전장 이동이다. 기존 Source에는 포탈·이동 전환 소유자가 없으며 GameMode/PlayerController에 특정 맵 좌표를 넣지 않는다. 새 runtime 파일은 `Environment/KZBossPortal.h/.cpp` 두 개다. 하나의 배치 액터가 실제 진입 box, Niagara 표현, 목적지 참조 및 전환 동안의 자원을 소유한다. 기존 Engine overlap/TeleportTo/PlayerCameraManager fade와 ASC Ability 차단/count, Player 입력·LockOn cleanup을 재사용한다. 새 Manager/Subsystem/ASC/Ability/GameplayTag/AnimInstance 상태는 없다.

ARCH-05/09/11/15의 상호작용 대상 소유권을 적용한다. 별도 상호작용 입력·진행·보상이나 공유 탐색 수명이 없는 자동 통과이므로 선행 Interact Ability/인터페이스를 추가하지 않는다. 포탈 전환 내부 phase는 공개 gameplay 상태의 사본이 아니다. GT의 실제 player capsule overlap만 진입하며 중복 overlap/몬스터/사망 플레이어는 거부한다. ASC action 차단·무적 기여와 Controller move/look ignore 기여는 각 한 번 추가·회수한다. 정상/실패/빙의 변경/대상 소멸/EndPlay에서 자기 기여만 정리하며 외부 기여를 Reset하지 않는다. 전환 동안만 tick한다.

좌표는 런타임 C++ literal로 두지 않고 Level의 `ExitPoint` 참조와 TargetPoint transform을 사용한다. 원작 `Mission01_Boss_Start` 출처는 `Saved/ImportReports/HeinMach_PlayableCameraAnchors.json` → `source_json`의 `HeinMach_Spawn_Main01.json`, `xxPlayerStart_1`, attachment-chain world position `(-128.38306,-9446.851,-4053.18) cm`, yaw `-109.99981689453126°`다. 지면은 현행 맵 collision trace로 확인한 적용 좌표이며 원작 직접 수치와 구분한다. capsule 반높이 및 엔진 `MIN_FLOOR_DIST`만 더해 capsule center를 얻고 TeleportTo의 encroachment 검사를 유지한다.

암전 0.45s/검정 유지 0.15s/복원 0.6s, entry half extent (80,140,160)cm 및 지면 위 중심160cm는 원작 근거가 없는 어시스턴트 TEMP다. 서 있는 플레이어가 통과하기 충분한 범위와 짧은 전환을 목적으로 선정했으며 Level Details에서 직접 조정한다. 실제 화면·ground/overlap/복구 테스트 결과에 따라 조정하고, 적용/빌드/PIE 완료는 아래 후속 기록에만 남긴다. Art 표현/배치 상세는 해당 Art 문서에 분리한다.

## 2026-10-15 — 첫 저장·실제 이동 검증 / 표현 조정 진행

Main Build01(runtime)/Build02(DEV QA 추가)가 stock `KhazanEditor Win64 Development`에서 성공했다. `Placement04`의 첫 저장에서 높은 trace가 동굴 지붕 윗면을 선택한 것을 검토해, `Placement05`에서 GateCube 상단에서 아래로 쏘는 Pawn trace로 수정했다. 최종 입구 바닥은 (19550,4270,-166.752918548882)cm, 포탈 중심은 이 바닥+160cm다. Python Rotator의 위치 인자 순서도 keyword(pitch/yaw/roll)로 고쳐 도착 yaw를 실제 원작 방향으로 저장했다. 두 수정 모두 배치 절차 문제이며 runtime C++ 좌표나 원본 VFX를 바꾸지 않았다. 모든 이전 영수증·실패 로그·맵 백업은 보존한다.

원본 JSON을 표적 확인한 결과 SHA256 `f6039905e189edc3f4d432262038ba56a1476fc9b6ea6336118126df1da29277`의 export195 `CollisionCapsule.Properties.RelativeLocation`에 (-128.38306,-9446.851,-4053.18)cm가 직접 기록돼 있고 `Properties.RelativeRotation.Yaw` 원시 값은 **250.00018°**다. export1008 `xxPlayerStart_1.Properties.PlayerStartTag=Mission01_Boss_Start`이며 같은 component를 RootComponent로 참조한다. 저장 report의 -109.99981689453126°는 정규화·float 변환 결과이며 원시 음수 yaw라고 표현하지 않는다. 도착 marker Z=-4188.589563779831cm는 현행 맵 Pawn collision 측정값이다. 캐릭터 center에는 실제 capsule 반높이와 엔진 MIN_FLOOR_DIST를 더한다.

Main `RHI01`은 실제 저장 맵/실제 player capsule overlap으로 `Khazan.Portal.PIE` Success였다. 중복 진입의 추가 count0, black=1에서 약24km가 아닌 **약240m**의 맵 내 이동, 도착 XY/yaw/보행 가능 바닥, 정상 fade/입력·action/무적 기여 회수, idle tick 종료, 목적지 없음, 외부 기여를 유지한 portal EndPlay, 진입 뒤 목적지 소멸의 유한 복귀를 통과했다. 실제 이동의 정확 거리는 Runtime.csv 좌표에서 계산하며 이 문장의 약240m는 설명용 반올림이다. 모듈 SHA는 `b3ff7b30b01e07ff70a1f47b951c6fccc060205fdcbd894ab8c0a9d78168c57d`이고 저장 package0이다.

첫 화면은 Niagara 정면 가시성이 부족해 완료로 판정하지 않는다. 동시 RHI 프로세스의 VRAM budget 경고도 첫 캡처에 포함돼 있어 성능 통과 근거로 사용하지 않는다. `VisualTrials*`에서 컴포넌트 회전만 격리 검토하며, 마지막 Main 저장/새 readback 및 필요한 재실행 결과가 최종 정본이다.


## 2026-10-15 — 최종 Main 완료: 실제 걸어서 진입 → 전장 내부

앞선 Boss_Start 채택을 현재 목적지로 사용하지 않는다. 실제 도착 화면이 전장 직전 통로였으므로 원본 같은 JSON의 export482 `Yetuga_TargetPoint` → root470 `Properties.RelativeLocation=(-3761.6345,-11455,-4455.1245) cm`를 전장 내부의 기준으로 선택했다. 원본의 grab marker를 포탈 도착 기준으로 사용하는 선택은 TEMP이며 원작 포탈 동작의 복원이라고 표현하지 않는다. `SA_Yetuga` export1081/root450의 원시 위치 `(-5471.6367,-10702.597,-4276.216) cm`까지의 XY 벡터에 atan2(dY,dX)를 적용한 yaw는 156.25044846566882°다. 현재 맵 Pawn trace의 바닥 Z는 -4572.605507799506cm, normal.Z=.998964이며 배치 영수증은 Placement06이다. 현재 Encounter/보스 생성 방식은 변경하지 않았다.

최종 Main suffix Build07 성공 후 새 Main D3D12 RHI06의 `Khazan.Portal.PIE`가 Success다. 실제 Player intent → CMC → 동굴 충돌을 따라 걸어서 entry overlap을 발생시킨다. 실제 전장 이동은 1회이며 black=1에서만 TeleportTo를 실행했고, camera cut/지연 이력 초기화/도착 yaw·보행 가능 바닥/암전 복원/자기 입력·action block·무적 기여 회수가 통과했다. 중복 overlap, 목적지 없음, 외부 count를 유지한 portal EndPlay, 진입 후 목적지 소멸의 유한 복귀도 통과했다. 원본에 없던 영구 State/Manager/Subsystem/Ability나 기존 combat Source 변경은 없다. runtime 파일2, DEV test1, Main map1 및 전용 VFX 사본4개다.

검증 오류 이력도 보존한다. RHI02는 QA가 프로젝트의 X=전방 입력을 (0,1)로 호출한 오류였으며 게임 이동은 수정하지 않았다. RHI03은 실제 진입/전장 이동이 성공했으나 엔진 encroachment 및 지면 안착의 작은 위치 보정을 1cm 이내로 제한한 QA가 실패했다. 최종 검사는 실제 capsule radius 이내 도착·보행 가능 floor와 출발점 유지로 의미를 바로잡았다. runtime TeleportTo의 충돌 안전 보정을 제거하지 않았다. 각 실행의 실제 DLL SHA는 해당 Driver.json에 보존하며 최신 Source/표준 DLL/Map/4asset SHA 및 화면은 `Metadata/HeinMachPortal_20261015/FinalVerification.json`에 결속한다.

Fresh Readback04(save0/dirtyMap0)는 기존10009 actor transform·class 동일 및 포탈 배치 후 동시 저장의 PlayerStart1 수정을 구분해 기록했다. 우리 Placement06까지의 기존10010 actor transform/class 보존 이후에 생긴 별도 수정을 되돌리지 않았다. 추가2 actor, GateCube hidden/collision 설정, 목적지 참조/회전, trigger 크기, 전용 Niagara/상대 yaw90, 재질 alpha·blend·MI parameters 및 공유 원본4파일 SHA 보존이 통과했다. 마지막 Entry/Black/Arrival 실제 game viewport 3장은 해상도를 PNG header로 기록하며 요청 창 크기와 혼동하지 않는다. Editor QA texture quality2/pool800MB는 저장하지 않았다. Shipping/성능 인증, 별도의 강제 UnPossess/막힌 목적지 사례는 이번 완료 범위가 아니다.

조절은 World Outliner의 `Gameplay/YetugaPortal/HM_Yetuga_EntrancePortal`을 선택해 Portal Fade 설정과 `EntryVolume` box extent, `PortalEffect`의 Niagara·상대 위치/회전/크기를 편집한다. `HM_Yetuga_ArenaArrival`은 capsule 발 기준이며 위치와 yaw를 수정한다. runtime C++에 Level 좌표는 없다. 재검사만 필요하면 새 출력 폴더의 KZ_PORTAL_OUT/KZ_PORTAL_CAPTURE=1과 `heinmach_portal_validation_driver_20261015.py` 또는 readback script를 사용한다. 완료된 authoring을 반복 실행하거나 과거 map/DLL을 복사하지 않는다.

RHI04는 실제 이동·도착과 복구가 실행됐으나 반복 +1000cm 배치한 마지막 실패 시험체가 전장 절벽에 닿아 physics settling이 227.348cm였다. 최종 QA는 정상 도착으로 검증한 동일한 walkable floor를 실패 시험체에도 재사용한다. 게임 코드·목적지·암전 수치는 이 QA 수정 과정에서 바꾸지 않았다. fresh Readback04의 dirty map/content 목록은 최종 receipt에 보존하며 조회에서 dirty로 표시된 자원은 저장하지 않았다. 모든 content package가 dirty0이었다고 표현하지 않는다.

마지막 QA 빌드 중 메인 에디터가 실행돼 stock Build06이 LNK1104 공유 잠금으로 실패했다. 사용자 에디터를 종료하거나 reload/save하지 않고 Main Source의 suffix2026101517 모듈을 Build07로 빌드해 RHI06에서 검증했다. runtime portal 코드는 최초 stock 빌드 이후 바꾸지 않았고 후속 Source 수정은 DEV QA뿐이다. 열려 있던 Main HeinMach의 native portal 및 arrival 배치를 read-only로 관측했다. 이후 Main map 바이트가 재저장돼도 최신 디스크의 포탈 계약을 Readback04에서 다시 확인하며 과거 map으로 되돌리지 않는다.

최종 RHI 캡처에는 동시 에디터 실행 중 실제 VRAM budget 경고가 표시됐다. 전환 기능 Success와 단일 실행 프레임 성능 검증을 구분한다. 최신3장은 진입/완전 암전/전장 도착의 실제 화면이며 부분 fade-out 샘플은 이 실행에서 별도 PNG로 잡히지 않았다. 이전 RHI04/FadeOut.png는 이전 모듈/실행의 보조 화면으로만 남긴다. concurrent 추가 actor도 최종 영수증에 별도로 기록하고 이 작업의 추가 actor2개로 합산하지 않는다.

<!-- HeinMachPortal_20261015_complete -->


## 2026-10-15 — Readback05 최종 스냅샷 보충

동시 Main 저장 뒤 fresh Readback05(save0)가 포탈/arrival2 actor의 참조·transform·범위·암전 시간과 전용4asset/공유 원본 보존을 다시 통과했다. 최종 확인 map SHA는 `62e48f3c26be58069ddfc9d3458787048d51bc7e8714eda9e5ca640e74c5938a`, 영수증 시각은 `2026-10-15T04:28:08.040073+00:00`다. 기존10009 actor 동일과 별도 PlayerStart1 수정, 이 작업 밖의 추가 actor 10개를 구분해 보존했다. 앞선 Readback04 기록은 해당 시점의 기록으로 유지하며 최신 근거는 FinalVerification.json의 Readback05/RHI06이다. 실제 walking·암전·전장 이동·복구 Success 이후 게임 Source/자산을 추가 수정하거나 사용 중인 editor를 reload/save하지 않았다. 현재 요청의 필수 잔여0이다.

<!-- HeinMachPortal_20261015_readback05 -->

## 2026-10-15 — Yetuga 원작 BGM 시작 추가 / 사용자 정정 반영

기존 portal의 성공한 TeleportTo 직후에 ArenaMusic을 LoadSynchronous하고 engine SpawnSound2D(GetWorld(), Music)로 시작하도록 runtime2파일만 수정했다. 편집 가능한 soft path 기본값은 `/Game/Audio/Original/Music/Yetuga/SC_YetugaBattle.SC_YetugaBattle`다. 원작 자료/임포트는 Art의 `YETUGA_BGM_SOURCE_20261015.md`에 분리 기록한다. 몬스터 Ability나 피해/StateTree 경로를 변경하지 않았다.

사용자 최신 정정에 따라 **플레이어 사망·Yetuga 처치·전장 이탈 시 종료하지 않는다.** HP/Dead/보스/거리 관측, 종료 delegate/timer, 별도 music tick/manager/class를 추가하지 않았다. 현재 ArenaMusicComponent.IsPlaying이면 포탈 재진입 시 새로 생성하거나 곡을 처음부터 다시 시작하지 않는다. FinishTravel/EndPlay에 음악 Stop/FadeOut도 넣지 않았다. World를 context로 사용하는 2D 재생은 traveller Pawn 수명과 무관하며 원본 loop를 계속 재생한다. 월드/PIE 자체가 종료되면 엔진이 정리한다. 이것은 최초 진행 안내의 자동 종료 계획을 대체하는 사용자 결정이다.

포탈 목적지/입력 counted lock/암전/카메라/이동 실패 처리와 map 배치는 보존했다. 포탈 이동에 실패하면 음악을 시작하지 않는다. unity gain/pitch/zero start는 engine API 기본 표현이며 새 임시 gameplay tuning은 없다. 기존 camera fade의 전역 audio fade는 그대로 유지하므로 전환 암전 중에도 재생 위치는 계속 진행한다.

Main KhazanEditor Win64 Development의 stock DLL 빌드가 `Metadata/YetugaBGM_20261015/Build01.log`에서 Succeeded(34.93s)다. 임포트는 종료된 task-owned hidden commandlet만 사용했고 사용자 editor의 저장/reload/종료0이다. 이번 요청에서 PIE/전투/실기 청취 검증은 실행하지 않았다. 이전 포탈/진동의 검증 이력을 이번 음악 동작 검증으로 합산하지 않는다. 정확한 source/asset/module hash 및 적용 상태는 `Metadata/YetugaBGM_20261015/Implementation.json`을 따른다.
