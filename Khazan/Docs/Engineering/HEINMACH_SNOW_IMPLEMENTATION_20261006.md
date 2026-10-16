# 2026-10-06 HeinMach snow runtime contract

## 구현 착수와 책임

직접 수정 요청이다. 최신 ARCH-43/v3 및 최소 변경/현재 AI 계약을 유지한다. CMC·Locomotion·ASC·Ability·AnimInstance·AI의 gameplay 책임을 바꾸지 않는다. 새 runtime 타입은 `AKZSnowDeformation` 한 Actor(h/cpp 2개)이다. level 수명에 걸쳐 여러 Player/AI의 contact를 한 지면 field로 누적하고 material 소비자에게 공급해야 하므로 Character private state로 둘 수 없다. 발마다 새 Component, GameplayTag, Cue, manager/subsystem, 이벤트 원장을 추가하지 않는다. 독립적인 level field의 실제 수명이 새 Actor의 근거다.

작업 Source는 아직 격리 프로젝트에 있다. 메인 `KZCharacter.cpp`는 맥락으로 읽었고 수정하지 않았다. Tick은 game-thread `TG_PostUpdateWork`에서 엔진의 finalized skeletal/component transform을 읽는다. worker AnimInstance에서 Actor/ASC를 접근하지 않는다. 기존 engine texture region update만 사용하며 Build.cs private `RHI` 한 의존을 추가한다.

## 데이터 계약

- writer: 실제 ACharacter의 authored foot/paw bone 및 부착 StaticMesh 무기 경로. consumer: 명시적으로 `HeinMachSnowSurface` component tag를 부여한 native snow material. 엔진 component tag이며 새로운 gameplay 태그 사전 상태가 아니다.
- field: world XY 2cm grid, transient linear RGBA16F texture. R compression[0,1], G rim[0,1], B substrate world Z(cm), A valid. cached cell은 CPU world tile에 보존하며 Player window를 이동해도 같은 world cell을 다시 공급한다.
- max accumulation으로 반복 contact가 substrate를 관통하지 않는다. quintic shoulder는 양 끝의 기울기/곡률을 완만하게 연결한다. stored source scalar의 원작 shader 단위 미확인과 native cm 해석/임시 tuning은 [Art 정본](../Art/HEINMACH_SNOW_DEFORMATION_2026-10-06.md)에 분리했다.
- ground state는 CMC의 현재 `IsMovingOnGround`를 읽는다. 새로운 gait·Dodge·Attack/HP boolean 사본을 만들지 않는다. 무기접촉은 실제 component 경로·substrate distance를 검사하며 입력 수명/피해 판정을 소유하지 않는다.
- actor EndPlay에 자기 MID가 여전히 적용된 slot만 원래 material로 복구하고 weak contact/history·cache·자기 texture/material 참조를 반환한다. 새 owner가 바꾼 material을 덮어쓰지 않는다. level/PIE마다 field를 새로 만들며 전역 texture/package에 runtime pixel을 저장하지 않는다.
- cached field는 수량 예산으로 먼 오래된 tile만 반환한다. 원작 refill 시간 미확인으로 시간에 따른 복구는 아직 넣지 않는다. 2D field의 중첩 층/altitude·slope/contact tolerance는 독립적인 native 제한이며 검증/상세 수정 결과를 하단에 기록한다.

## 검증 및 반영 상태

현재는 격리 private cold build 진행 상태이며 메인 적용·PIE·원작 동일성 완료 기록이 아니다. 재개 source/project는 `C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan`; scripts는 `Scripts/Art/heinmach_snow_stage.py` 및 author/probe/source, 증거는 `Saved/ImportReports/HeinMachSnow_20261006`이다. 공유 Plugins junction의 첫 build lock은 private copy로 정정했다. 메인 DLL을 강제 해제하지 않았다.

반영은 다른 Monster editor 작업 완료 뒤 최신 Source/config/map hash 및 live dirty·PIE 없음을 확인하고 선택적으로 수행한다. staged 오래된 Source/BP/Maps 전체 복사는 하지 않는다. final native compile/실제 game QA/기존 actor pose·collision·material/새 saved reload·메인 결과는 후속 날짜별 절로 구분한다.

## 2026-10-06 — cold build와 실제 contact 검증 진행

Native Actor와 dev-only `KZSnowDeformationPIETest.cpp` 격리 cold build가 통과했다. editor bridge는 실제 `UMaterialEditorOnlyData::Displacement` 입력만 연결하며 다른 gameplay class를 추가하지 않는다. profiling은 CSV `HeinMachSnow/SnowTick`로 실제 field Tick 비용을 측정한다. 정식 runtime 파일은 h/cpp2개, test는 별도 development-only이며 Character/ASC/CMC/AI source는 이 작업에서 변경하지 않았다.

최초 native QA 좌표가 눈 weightmap 위의 실제 바위 collider를 맞춘 것은 test fixture 문제다. `SnowGround` log의 actor/component/impact/normal/tag와 `BlockingSurface.json`이 값의 근거다. gameplay ground contact 판정을 편의상 완화하지 않았다. source bone/contact 경로 검증은 다음 PIE 결과가 있어야 완료다. LLDB attach는 staged 심볼 해석 불가로 중단했고 own breakpoint/session을 정리했다. 실제 runtime 증거는 fallback native integration log이며 breakpoint hit 증거로 표시하지 않는다.

메인 current Source에 추가되는 다른 chat의 Monster/Heal 변화는 보존한다. 현재 main HeinMach SHA9da24fa9...58ea251, 별도 화로 작업의 9,868actor 후보도 진행 중이다. 이 작업의 오래된 9,611actor 맵으로 화로 설치본을 덮어쓰지 않는다. final 단계에서는 최신 main map에 snow component 교체/tag와 field Actor만 다시 적용해야 한다. 사용자 live map은 StormPass로 바뀌었으므로 DevMap으로 임의 복구하지 않는다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

실제 메인 Source에 level presentation owner `AKZSnowDeformation` h/cpp 2개와 development-only `KZSnowDeformationPIETest.cpp`를 반영했다. 기존 ASC/Ability/CMC/Locomotion/AnimInstance/AI 상태·입력·취소 수명은 변경하지 않는다. finalized pose를 game-thread TG_PostUpdateWork에서 읽고 발/Toe0, pelvis/spine/head/팔·다리를 관측한다. 몸 접촉은 MOVE_None에서도 가능하다. 발 중앙이 작은 돌을 맞추면 실제 발끝을 같은 reach12cm로 재검사한다. 접촉 height를 늘려 공중을 땅으로 취급한 변경은 없다.

장비는 기존 부착 component의 actual bounds 경로, 합쳐진 장비는 실제 imported LOD0 지배 weapon bone vertex를 editor에서 bone-local center/극점으로 굽는다. 11 actual component mesh 입력에서 원작 장비 4 profile을 저장했다(`Resume20261007/MergedWeaponProfiles.json`). runtime에 전체 vertex CPU skinning이나 gameplay 무기 상태 사본을 추가하지 않는다. 약한 component/bone contact history와 자기 MID만 소유하며 EndPlay에 자신이 계속 소유한 material slot만 복구한다.

40.96m 이동 창/2cm texel/2048² RGBA16F, tile128/cache256, CPU field 약48MiB/GPU32MiB는 기술 예산이다. toroidal GPU addressing으로 겹친 tile을 보존하고 새 strip/dirty tile만 region update, zero tile batch로 clear한다. 오래된 먼 CPU tile은 예산 초과 시 퇴거한다. window 바깥 모든 actor의 무제한 영구 이력/중첩 층 분리 field/원작 refill 시간을 보장하지 않는다. 수치 provenance와 material은 Art 정본에 분리했다.

지형 떨림은 nav 간격만으로 단정하지 않았다. 작은 돌의 실제 Pawn blocking과 아래 walkable substrate를 9점 검사해 노출 bump≤12cm/bounds height≤60cm/XY≤800cm의 65 component만 Pawn Ignore·CanEverAffectNavigation=false·HeinMachMicroDressing으로 저장했다. 임시 선별 기준이며 원작 데이터가 아니다. 큰 돌·낭떠러지·route wall2,281/NavBounds242/Null26/Links24/기존 actor pose를 보존했다. 이전 private 작업의 표적 외16개는 unchanged main baseline 응답/nav/tag로 복구했고 81개×노출 표준 collision 8채널 저장/reload를 검사했다(`CollisionChannelsPreserved.json`). 65개 이외의 채널 응답은 baseline과 같다. 실제 새 메인 saved audit65개를 재확인했다.

Recast build 완료를 대기하고 map을 저장한 후 기존 원작 MoveTo63/1,485 point/1,422 complete segment 모두 통과, collapsed17/실패0(`Resume20261007/NavigationFinal.json`). 표적 WaterfallUp StaticMeshActor_6987 bump11.807cm 위에서 actual CMC가 약685/682cm 이동한 전후 비교: 10cm 재표본화 높이 2차 차분 RMS1.81303582→1.50061163cm, 비율.82767898/17.2321% 감소(`FloorCMCBeforeAfter.json`). 전 맵/모든 animation jitter 완전 제거의 증거로 확대하지 않는다. 전역 CMC MaxStep/slope/nav voxel이나 별도 smooth-path manager는 추가하지 않았다.

격리 ColdBuild_LatestMainFinal/ColdBuild_ToeEdgeContact/ColdBuild_DodgeContactSamples 모두 Succeeded. 최신 main runtime Source를 수령해 빌드했으며 독립 Monster 작업의 development-only KZMonsterAIPIETest.cpp 변화만 module snapshot guard에서 제외/보존했다. 앞선 main Dodge QA 두 번의 압축0 실패 로그는 남겼다. 실제 착지 종료 대기/발끝 fallback/접촉 diagnostics 보완 후 final main PIE Success 04:22:07 UTC: GPU파임14.5cm, render/physics<1cm, 실제 Player 이동/회피 및 4 Monster 발·누운 torso·merged weapon, airborne suppression/반복50회/6000cm 창 이동 이력/EndPlay 복구. 격리 몸/장비 fixture를 gameplay knockdown·attack hit QA로 승격하지 않는다.

성능은 메인 `Saved/Profiling/CSV/Profile(20261007_132110).csv`, SnowTick active1,094 samples 평균.9883947ms/P95 3.0408ms/max19.9835ms. 최초 asset/cache 작업과 다른 editor 경쟁을 포함한 Development Editor 게임 스레드 값이다. 이전 warm .5019ms와 cold1.7657ms는 다른 범위이며 개선율로 계산하지 않는다(12:59 기록의 `.1.7657`은 `1.7657`의 표기 오류). shipping FPS/GPU cost/network 검증은 미완료다.

전달 결과:48 native assets+현재 map+Snow Source3+private RHI 의존+Nanite tessellation SystemSettings. 다른 AI 의존/Config 변경은 기존 사용자 작업으로 보존했다. DLL은 manifest-selected `UnrealEditor-KhazanSnow20261007.dll`, BuildId55116800, SHA c76703374ec0573caba7948d4cbcef1e8058d3e749711de2e2f859ac6af0e3ce. 일반 UnrealEditor-Khazan.dll은 독립 작업의 최신 hash17b0a230...49 상태를 그대로 보존했으며 덮어쓰지 않았다. mapSHA4560f07aa655421056cb6846b2df4646778b01636f752c4e3d2e2cfda8256129. 백업은 DeliveryBackup20261007 및 ModuleBeforeContact 파일이다. MainVerification20261007/FinalVerification20261007이 latest source/asset/module/scene/PIE 증거다.

사용자 editor를 save/reload/PIE/camera/close하지 않았다. 작업 전용 main PID27452는 검증 후 정상 종료. 독립적으로 새로 열린 main PID17552를 ~04:26 UTC read-only 확인: DevMap/PIE없음/dirty0/native KZSnowDeformation class 존재, 실제 log의 alias module 로드도 확인. 에디터를 다시 종료·재시작할 필요 없이 사용자가 `/Game/Maps/L_HeinMach_Environment`를 열어 Play할 수 있다. initial deliver.py는 재실행하지 않는다. 후속 Source 변경은 current main을 stage에 수령/빌드하고 guarded update_module.py를 사용하며, 다른 build가 일반 DLL을 재작성해도 그 DLL을 이전 snapshot으로 복구하지 않는다. 현재 소스가 전부 정상 빌드되면 일반 DLL 경로도 동일한 native class를 포함한다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

기존 AKZSnowDeformation h/cpp와 development-only Snow PIE test만 보완했다. 새 runtime 파일/class/component0. FootRadiusCm40×32/FootContactHeightCm20/WeaponRadiusCm100cm, 새 WeaponContactHeightCm24cm다. 기존 WeaponRadiusCm가 brush radius와 trace reach를 동시에 소유하던 결합을 분리했다. 발과 무기의 눈 접촉 높이도 확대하면서 weapon brush100cm를 vertical trace reach100cm로 오해해 공중을 파는 문제를 방지한다. 모든 값은 이번 사용자 룩 요청에 따른 어시스턴트 임시값이며 원작 값이 아니다. 실제 캐릭터 capsule/무기 gameplay hit/damage collision에는 손대지 않았다.

큰 brush의 셀 수 증가에 대응해 기존 StampSnow를 tile 단위 loop로 보완: tile lookup/할당은 한 번, 내용이 달라진 tile만 dirty/upload. max 압축/quintic 경계/rim/고도 gate와 기존 cache 소유·EndPlay 계약을 유지한다. 접촉 경로 sample spacing=max(texel size, brush의 작은 반경×.25), weapon은 원형 반경×.25다. 따라서 현재 발8cm/무기25cm이며 C2 brush 중심의 겹침을 유지하는 기술 간격이다. .25는 원작 숫자가 아니다. Previous를 마지막 sampled contact 기준으로 누적해 느린 이동이 간격 미달로 계속 누락되지 않도록 했다. 원래 teleport256cm guard/공중 억제는 유지한다. 게임 스레드 finalized pose 관측과 기존 ASC/Ability/CMC/Animation 책임·cleanup도 그대로다.

ColdBuild_BroadBrush20261007/ColdBuild_BroadBrushQA20261007 모두 Succeeded. width 검사 추가 후 실제 다시 빌드했다. private contact PIE Success06:15:07 UTC, fresh main alias 모듈 실제 PIE Success06:28:20 UTC/PID28460. 기존 depth14.5cm/render-vs-collision<1cm/반복·cache·EndPlay, actual Player run/Dodge/Imperial_R ground-vs-air와4 Monster feet/body/merged equipment 및 새 blade 밖(60,50)cm 압축>0.1이 통과했다. 기존 map poses/collision/nav/material 보존,4serialized settings main readback 통과. global Nav/CMC/PlayerParts source를 바꾸지 않아 기존 경로 전수 검사를 근거 없이 반복하지 않았다.

CPU는 main Profile(20261007_152647).csv SnowTick active376samples 평균1.3528705/P95 3.5578/max14.1171ms. 큰 범위와 cold cache/동시 editor의 Development Editor 결과이며 이전 .9884ms와 조건이 달라 개선율/전체FPS로 읽지 않는다. private CSV151407은 SnowTick column이 없어 별도 비용 증거로 쓰지 않았다. cache/texture 예산48/32MiB는 유지한다. GPU·shippingFPS/연속 gameplay knockdown/원작 pixel parity 미검증도 유지한다.

Source3+map만 선택 전달, 기존 texture/mesh/material 신규0. 새 manifest-selected UnrealEditor-KhazanSnowBroad20261007.dll SHA3163ae8558af254eeb1d1b60035020c825a9861aab6791ed27bc7db30bd54817을 발행해 loaded normal DLL SHA516be188...57acab52를 보존했다. mapSHAb9802151...d1b76b00, 실제 Source SHA와 backup은 BroadBrush20261007/Delivery.json 및 Backup. user editor8292 DevMap/PIE없음/미저장 /Game/Data/ComboCommand/DA_Player_Combo_Definition 1개/map0를 read-only 확인했고 save/reload/close/PIE를 하지 않았다. 새 UPROPERTY layout은 실행 중인 모듈에 자동 반영되지 않으므로 user 저장·재시작이 필요하다. private24332와 background main28460는 정상 종료했다.

현재 최신 결과는 BroadBrush20261007/FinalVerification.json과 같은 폴더의 main_verify.log다. 이전 initial Delivery/FinalVerification map/moduleSHA는 당시 증거로 보존하며 현재 값을 대표하지 않는다. 초기 deliver/finalize/update_module helper를 그대로 반복하지 않는다. 후속 작업은 current main Source/map와 새 manifest 모듈에서 시작하고 current hash를 기준으로 선택 반영한다. 일반 DLL을 옛 SnowWork snapshot으로 교체하지 않으며, user dirty ComboDefinition/동시 PlayerParts 작업을 덮어쓰지 않는다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

기존 presentation owner AKZSnowDeformation h/cpp만 작은 수정: 조정 가능한 FootCompression.7을 추가하고 foot stamp에만 공급했다. body/weapon1, finalized pose GT/PostUpdateWork, contact/cache/tile upload/EndPlay 수명과 기존 ASC/Ability/CMC/AI 책임을 유지한다. 새 runtime 파일/class/manager0, KZComboActionAbility.cpp 수정0. 머테리얼·높이 provenance/normal smoothing은 Art 정본의 같은 후속 절에 분리했다.

ColdBuild_DeepSnow20261007(81.49s)/DeepSnowQA20261007(16.54s) Succeeded. development-only QA에 partial foot GPU readback과 authored fraction 검사를 추가했다. 테스트 좌표가 pure layer라고 가정해 실패한2검사 로그를 보존하고 mixed layer의 실제 full depth×FootCompression과 비교했다. scalar maximum bound·full crater>partial foot·compressed render agreement/반복·scroll 이력과 기존 actual Player/Monster/equipment/airborne/EndPlay 회귀를 검사했다. private 및 fresh main PID15340 실제 PIE Success.

메인 CPU CSV Profile(20261007_170957).csv: active582 평균1.286296/P95 3.720700/max15.676300ms. cold asset/cache와 다른 editor 경쟁을 포함한 Development Editor SnowTick 측정이다. 이전 조건과 달라 개선율로 계산하지 않는다. CPU cache48MiB/GPU field32MiB/2cm·2048² 예산 유지. 추가 normal 샘플은 pixel shader에만 있으며 실제 GPU 전체 비용/shippingFPS는 미검증이다.

현재 Source3/map/material2/module hash는 DeepSnow20261007/Delivery.json/FinalVerification.json과 Backup을 따른다. current unrelated Source를 compiled stage와 byte 비교한 후에만 선택 전달했고 normal DLL을 보존했다. 기존 사용자/독립 Monster·PlayerParts 작업을 old snapshot으로 되돌리지 않는다. 기존 running editor 새 layout에는 사용자 저장·재시작 필요. initial/broad helper의 strict old SHA를 현재값으로 재사용하지 않는다. 후속 수정은 최신 main Source intake(own3 수정은 별도 보존), native cold build, private actual RHI, guarded selected delivery, fresh main PIE 순이다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Main Source3/? Contact55 material2/Preview map/UnrealEditor-KhazanSnowContact55QA_20261007.dll? ?? ????. ?? native PIE ?? ?? /Game/Maps/L_HeinMach_Environment_Contact55_20261007, fresh background Main PID24660, 12:08:02 UTC Khazan.Snow.PIE Success?. GPU ?? ?34.000cm/??50.000cm?? ?? canonical /Game/Maps/L_HeinMach_Environment? ?? ???? ???. ??? Main PID3528? HeinMach/dirty0/PIE???? ??? ???? ?? file lock? ????. ??? save/reload/PIE/camera/close? ???? ???. FinalVerification? success=false/preview_verified=true/canonical_map_pending=true? ??? Preview ??? ????.

?? presentation owner h/cpp2?? devtest? ????? ? runtime ??0, ComboActionAbility/product AI/CMC ??0??. FootCompression35/55?WeaponCompression50/55?body1, reference55cm/minSnowHeight clip, ? full rim envelope8?5cm(brush8/1.4?5/1.4)/reach8cm??. ?? RGBA16F?tile/cache/field 2cm?2048??GT PostUpdateWork ? EndPlay ownership? ????. Source3/? material2/Preview? QA alias? ?? hashes? Delivery.json? ???. ?? provenance?shader ??? Art Snow ??? ?? Preview pending ?? ???.

native fixture? LOD0 barycentric smooth-normal ?? SceneDepth?128?128 baseline ?? isolated-foot2Dpeak? tiny depression? ????. partial depth/residual?? ??0???weapon fraction ??/cache scroll??? fullclear substrate agreement, Player run/Dodge/4Monster gait/body/merged gear/??weapon/EndPlay? ????. ? Preview2492? Halberd torso ?? ??? animation? ?? ??? pelvis? ??? fixture timing???. private test case15? bPauseAnims=true? pose placement ?? ??? ?? case17 ???? ????. ?? body contact ??? ????. ? QA alias? ???? ?? alias? ???? ??? test ?? runtime h/cpp ? ?? ?? Source byte ??, ?? Deep material??? DLL?canonical map hash? ????. ?? foot8cm ?? ? isolated airborne negative? ?????.

?? Main CSV Profile(20261007_210703).csv: active1752samples ??0.702610/P95 1.859600/max7.112500ms. Development Editor? SnowTick CPU?? cold cache/?? editor ??? ????. ?? ??? ?? ?????? FPS? ?? ???. GPU????/shipping ????? gameplay montage??? pixel ???? ?????.

canonical authored blob? baseline SHA? Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/Delivery.json/PendingCanonical, ?? Preview ??? FinalVerification.json, handoff? PendingApplyStatus.json? ????. hidden worker2256(12:08:54 UTC)? helper wait_apply? ???3528? ?? ?? ?? ??? ?? ???. ?? ? canonical SHA CAS?atomic copy? ???? ??? ??? map? ????. applied receipt ?? finalize/?? appender ???. ?? canonical? fresh Main PIE ??? Preview ??? ???? ???. ?? canonical ?? ??? ???.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
기존 Snow presentation owner h/cpp와 devtest만 보완하며 새 runtime 타입0, ComboActionAbility/product AI/CMC 변경0이다. FootCompression35/55·WeaponCompression50/55·body1, reference55/minSnow clip과 명목 foot full rim envelope8×5cm(brush8/1.4×5/1.4)/reach8cm다. 기존 RGBA16F·2cm/2048²·tile/cache/GT PostUpdateWork·EndPlay ownership은 유지한다. 원작 출처와 material은 Art Snow 정본의 이번 pending 절에 분리했다.

LOD0 barycentric smooth-normal SceneDepth와128×128 고립 foot의 baseline 차이 최대값으로 작은 파임을 측정했다. partial depth/residual·범위밖0·동일weapon fraction 반복/cache/fullclear·Player run/Dodge/4Monster gait/body/merged gear/airweapon/EndPlay가 통과했다. first Preview2492의 Halberd torso 실패는 pose 배치 후 animation이 계속 재생되는 fixture timing이었다. case15에서 배치 전에 bPauseAnims=true로 고정해 기존case17 방식을 재사용했다. 제품 body contact 코드는 변경하지 않았다. QA alias는 새 이름으로 발행했고 이전 alias/일반 DLL/Deep material/다른 Source·canonical map은 보호했다. actual foot8cm 바로 위의 isolated airborne negative는 미수행이다.

실제 Main SnowTick CPU는 active1752samples 평균0.702610/P95 1.859600/max7.112500ms다. Development Editor이며 cold cache/동시 editor 영향을 포함하고 이전 측정과 개선율을 계산하지 않는다. GPU 전체 비용/shipping FPS·모든 gameplay montage·원작 동일성은 미검증이다.

현재 hashes/Preview 실제 결과/원본 대기는 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007의 Delivery.json/FinalVerification.json/PendingApplyStatus.json과 MainPIE.log를 따른다. 원본 baseline SHA700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba는 유지하며 authored pending SHA c2796c4a0ec5540c22bcdb367ad7e7b8da7bff4a5aacb9a5c29bfdc19de4808c는 PendingCanonical/L_HeinMach_Environment.umap에 보존한다. hidden worker2256(12:08:54 UTC)은 사용자3528 종료까지 원본에 쓰지 않고 이후 baseline SHA CAS/atomic 적용만 한다. map 변경 시 보존·BlockedCanonicalChanged, 다른 lock은 WaitingForCanonicalUnlock이다. 적용 뒤 finalize와 완료 appender를 확인하며 Preview PIE를 원본 canonical fresh Main PIE로 확대하지 않는다. 원본 적용 완료는 아직 아니다.


## 2026-10-08 무기 공격과 실제 눈층 접촉 분리

기존 `AKZSnowDeformation`의 무기 관측 경로는 공격 Ability의 실행 여부를 검사하지 않았다. 부착 무기의 최초 지면 근접 또는 보행 중 무기 이동만으로도 기존 큰 무기 brush가 적용될 수 있었다. Contact55의 `WeaponContactHeightCm=79cm`도 substrate를 찾는 범위였으나, 기존 구현에서는 지역별 눈 높이를 구분하지 않아 얕은 눈 위의 공중 무기를 접촉으로 판정할 수 있었다. 또한 이전 Contact55 canonical 전달은 사용자 editor의 map 잠금으로 대기 상태였으므로, 당시 canonical 맵의 큰 발 brush40×32cm와 새 Source 기본값/Preview의 작은 발 설정을 같은 현행 값으로 읽으면 안 된다. 이번 Main 최종 반영 여부는 아래 최종 결과와 새 delivery receipt로 확정한다.

변경은 기존 presentation owner의 h/cpp, development-only Snow test, 그 owner가 배치된 HeinMach map 데이터다. 새 runtime class/component/manager, ASC/Ability/AI/CMC/AnimInstance 수정은 없다. `FKZSnowSurfaceSamples`는 두 현재 지형 머테리얼의 접촉 계산 데이터를 기존 Snow Actor가 소유하도록 추가한 작은 직렬화 struct이며 별도 상태 소유자나 subsystem이 아니다. 실제 틱은 계속 game-thread의 finalized pose 관측 경로를 사용한다.

발·몸 접촉을 처리한 뒤, 캐릭터의 기존 `IAbilitySystemInterface`→ASC 연결을 통해 활성 Spec을 한 번 검사한다. `Spec.IsActive()`와 Ability asset tag `Ability.Action.Attack`이 함께 참일 때만 무기 관측을 실행한다. 이 태그를 ASC owned state tag로 오해하거나 새 공격 bool을 ASC/Character에 복제하지 않는다. 공격이 아니면 해당 component의 contact map에서 `bWeapon` 이력만 제거한다. 합쳐진 장비는 본체 mesh와 map을 공유하므로 발·몸 이력은 보존한다. 다음 공격은 이전 비공격 이동 경로를 이어 파지 않는다. 정상 종료·취소 후의 공격 비활성 관측과 기존 EndPlay material/contact cleanup을 재사용한다.

무기 판정은 두 단계다. 넓은 ray는 아래 substrate를 찾는 용도이며 blade 충돌 체적이 아니다. displacement가 경사면 normal 방향이므로 수직 ray의 substrate 탐색 여유는 `WeaponContactHeightCm/max(MinSurfaceNormalZ,UE_SMALL_NUMBER)`로 계산한다. 현재 serialized79cm/기존 normal.Z 제한.5에서158cm다. **158cm는 substrate-ray 탐색 budget이며 실제 무기 접촉 범위가 아니다.** 실제 hit material(MID이면 Parent)을 authored profile과 일치시킨 뒤 hit XY의 지역 눈 높이를 계산한다. 눈 weight가 없거나 profile이 없는 표면은 무기 crater를 생성하지 않는다. 기존 field의 압축·rim과 높이 gate도 반영하고, `(WeaponPoint−ImpactPoint)·ImpactNormal`의 거리로 경사면 접촉을 판정한다. 허용 거리는 substrate 아래 `−6cm`부터 현재 눈 표면 위 `+6cm`까지로 유지한다. `WeaponSurfaceContactToleranceCm=6cm`는 원작 근거 미확인인 어시스턴트 임시 접촉 여유값이다. source weight mip/filter 및 collision face normal과 GPU interpolated displacement normal의 차이를 흡수하려고 선정했으며, 실제 GPU·공중 음성 검사와 사용자가 보는 공격 접촉으로 검증·조정한다. 새로운 무기 gameplay hit/damage collision을 의미하지 않는다.

기존 무기 crater 반경100cm는 접촉 후 시각 파임 크기로만 유지한다. 공격 이동 경로 sample 간격은 `max(TexelSizeCm, WeaponSurfaceContactToleranceCm)`이므로 현재2cm field/6cm tolerance에서는6cm다. 이전 반경 기반25cm 간격보다 blade의 접촉 경로를 촘촘하게 관측하지만 이미 `WeaponCompression` 이상 눌린 중심은 다시 큰 brush를 쓰지 않는다. max 압축·바닥 clipping·C2 brush/rim·bounded tile cache와 upload 책임은 유지한다. 이 간격과100cm 반경은 원작 검증값이 아니라 기존 기술/임시 튜닝값이다.

사용자 결정인 눈 최대55cm·발35cm·무기50cm와 rim 포함 발 반경축8×5cm를 보존했다. raw FootRadius는 기존1.4배 rim support를 나눈8/1.4×5/1.4cm, 발 reach8cm, foot/weapon 압축 fraction은35/55·50/55다. 얕은 눈에서는 기존 shader가 실제 weighted 높이까지만 파서 substrate 아래로 내려가지 않는다. DeepSnow2 36cm·기타 눈18cm·rim12cm는 앞선 어시스턴트 임시 튜닝값이며 원작 직접 높이로 승격하지 않는다.

### 작성 데이터와 수치 출처

작성 스크립트는 `Scripts/Engineering/heinmach_snow_contact_surface.py`다. 기존 자료만 표적 재사용했으며 원작 리소스 전체 조사·재추출·머테리얼 변경은 없다.

- 지형 변환/레이어 출처: `Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002/HeinMachTerrainPlan.json`의 `root_location`, `root_scale`, `min_section`, `dimensions`, `weight_layers`, `layers[].textures.diffuse.object_name`.
- native Weight texture 연결 출처: 같은 폴더 `HeinMachTerrainTextures.json`의 `weights`.
- source R weight: `Saved/Extracted/LookRestoration_20261002/HeinLandscape/HeinMach_Landscape{1,2}/WLI_*.png`. 원본8-bit grayscale를 R/255로 읽고 sRGB 변환하지 않는다. Puddle은 total에서 제외하며 snow 분류는 현재 작성 shader와 같은 diffuse source 이름의 Snow 여부다.
- 높이·압축 reference/rim 출처: `Contact55_20261007/SavedSettings.json`의 해당 Contact55 material `SnowHeightCm_<layer>`, `HM_DepthReferenceCm_User=55`, `SnowRimHeightCm_Temporary=12`. 작성 때 실제 Stage material scalar와 원본 Weight texture 연결·non-sRGB·X/Y Clamp를 다시 읽어 저장 자료와 일치하는지 검사했다. scalar provenance는 사용자55 및 기존 임시36/18/12를 구분한다.

각 source texel에 `(N,T,S)` 세 float를 굽는다. `N=Σ(non-puddle snow layer weight×layer height_cm)`, `T=Σ(all non-puddle layer weight)`, `S=Σ(snow layer weight)`다. runtime은 세 채널을 각각 bilinear 보간한 뒤 `H=N/max(T,0.00001)`, `SnowMask=S/max(T,0.00001)`을 계산한다. 먼저 H로 나눈 결과를 보간하면 현재 proof에서13.35/16.47cm 차이가 나므로 나눗셈 순서를 보존했다. 분모 guard0.00001은 기존 material의 기술적 값이며 gameplay 원작 수치가 아니다.

world weight UV는 source shader와 같이 `UVOrigin=root+(min_section−0.5)×scale`, `UVScale=dimensions×scale`, `UV=(WorldXY−UVOrigin)/UVScale`다. GPU texel 중심 규칙에 따라 sample 좌표는 `UV×Resolution−0.5`이며 Clamp한다. profile은 `Material, UVOriginCm, UVScaleCm, Resolution, Samples, DepthReferenceCm, RimHeightCm`를 저장한다.

압축 field는 초기 nearest-cell 계산을 폐기하고 현재 GPU `FIELD_CODE`와 같은 mip0 네 cell bilinear 계산을 사용한다. 각 cell의 `Compression/Rim/GroundZ/Alpha`를 `UploadTiles`와 동일하게 `FFloat16Color`로 양자화한 뒤 보간한다. Alpha는 compression 또는 rim이 있으면1, 없으면0이다. moving window의 가장자리까지 거리를 texel 단위로 구해 `I=saturate(Edge/16)`, inside shoulder는 `I²(3−2I)`로 계산한다. 고도 유효도는 `1−smoothstep(.75×LayerHeightToleranceCm,LayerHeightToleranceCm,abs(HitZ−Field.B))`이며 현재 tolerance32cm라24→32cm 구간이다. 최종 `V=Field.A×InsideShoulder×Altitude`다. 지역 눈 표면은 `H−min(H,55×saturate(Field.R))×V+12×saturate(Field.G)×V×SnowMask`로 구한다. 16texel shoulder/.75 고도 shoulder/half storage는 새 gameplay tuning이 아니라 현재 shader·texture upload의 기술 계약을 옮긴 것이다. source weight texture mip/압축과 collision face normal 대 Nanite smooth displacement normal의 차이는 여전히 별도 RHI 확인 범위다.

Landscape1은253×316, Landscape2는505×631, 총398,603 texel이다. 세 float32 채널은 **4,783,236 bytes / 4.56MiB**이며 매 프레임 texture readback이나 vertex CPU skinning을 추가하지 않는다. 이 숫자는 source dimensions에서 계산한 profile array payload이며 UObject·TArray·map 전체 overhead를 포함한 메모리 측정값이 아니다. 작성 시간6.933s는 이번 machine의 외부 Python bake 관측값이며 runtime tick 비용이 아니다.


<!-- HeinMachSnow_AttackContact_20261008_complete -->
## 2026-10-08 10:52 KST — 공격과 실제 눈 표면 접촉에 따른 무기 파임 완료

메인 `/Game/Maps/L_HeinMach_Environment`에 기존 Contact55 대기 설정과 새 접촉 데이터를 반영했다. 이전 canonical은 발 brush40×32cm/깊은 눈60cm 상태였으며, Source 기본값과 Preview의 작은 발 설정만으로 canonical 적용 완료라고 판단하지 않았다. 현재 기본 맵은 사용자 지정 최대55cm·발35cm·무기50cm, 명목 rim 포함 발 반경축8×5cm(brush8/1.4×5/1.4cm), foot reach8cm다. 얕은 눈 파임은 물리 바닥에서 제한된다. 이 값과 DeepSnow2 36/기타 눈18/rim12cm의 사용자·임시 튜닝 구분은 앞선 출처 계약을 유지한다.

제품 변경은 기존 `KZSnowDeformation.h/.cpp`와 맵의 Snow owner 데이터다. 개발 전용 `KZSnowDeformationPIETest.cpp`를 보완했다. 새 runtime 파일/class/component/manager, Character/ASC/Ability/AI/CMC/AnimInstance gameplay 변경은 없다. `FKZSnowSurfaceSamples`는 기존 presentation owner의 직렬화 데이터 struct다. active GAS Spec의 Ability asset tag를 읽으므로 `Ability.Action.Attack`을 ASC owned state로 복제하지 않는다. 비공격일 때 weapon 이력만 제거해 다음 공격으로 이동 경로가 이어지지 않는다. 공격 중에도 지역 눈 표면에 접촉한 probe만 기존 넓은 crater brush를 쓴다. 무기 반경100cm는 표현 크기이며 충돌 체적이 아니다. 원작 수치 미확인인 임시 접촉 여유6cm는 owner 설정 `WeaponSurfaceContactToleranceCm`로 관리한다.

원본 weight PNG/기존 source UV 변환과 현재 Contact55 scalar에서 두 CPU 표면 profile을 작성했다. 세 채널 `(높이 분자, non-puddle 전체 weight, snow weight)`를 각각 보간한 다음 나눠 기존 shader 계산 순서를 보존한다. 압축 field도 UploadTiles의 half-float RGBA, mip0 네 셀 bilinear, alpha·16texel window shoulder·고도 smoothstep을 동일하게 반영한다. 경사 substrate 탐색은79/.5=158cm지만 최종 실제 접촉은 normal 거리와 지역 표면 높이로 좁힌다. source 데이터/정확한 계산/검증은 `SurfaceProfiles.json`, `SurfaceProfileProof.json`, author/audit 보고서와 위 구현 계약을 따른다. 배열 payload4,783,236bytes(4.56MiB); GPU readback·CPU vertex skinning 추가0. 머테리얼/texture/mesh 작성0이며 기존46 surfaces의 Contact55 참조를 canonical에 완료했다.

ColdBuild_SurfaceContact_QA/Slope/Filter/FieldGridQA/LateralQA는 Succeeded. 최초 build의 QA shadow 변수 실패는 원래 로그에 보존했다. 첫 RHI PID13888 및 두 번째14176은 새 Player/4NPC 공격·공중·취소 검사와 GPU 발34/무기50cm가 통과했으나 기존 Run/Dodge reader가0으로 실패했다. 보완한2cm grid만으로는 해결되지 않았다. 실제 원인은 Player 입력(0,1)이 월드Y 이동인데 reader가 같은Y축으로 폭 표본을 만들어 발자국 양옆X를 누락한 것이다. 이전100cm passive weapon stamp가 중앙까지 덮어 이 오류를 가렸다. reader를 이동 방향에 수직인 폭 방향·2cm 셀 중심·제품과 같은 MicroDressing 제외로 수정했고, 발 양성/압축 상한 assertion을 유지했다. 제품 발 범위나 기대값을 늘려 실패를 숨기지 않았다. 두 실패 로그는 `StagePIE_SparseFootGrid_Fail.log`, `StagePIE_AlongPathGrid_Fail.log`다.

최종 private RHI PID27636은01:43:35 UTC `Khazan.Snow.PIE` Success. 새 메인 background PID652는01:45:35 UTC 동일 시험 Success, saved reload/정상 종료/선택 DLL 확인까지 완료했다. Player 실제 Run/Dodge, NPC4종 실제 보행, 발/몸/merged gear, 반복/scroll/EndPlay, 비공격 장비 이동 및 지면 접촉 음성, 실제 활성 공격 Spec/node/montage의 지면 양성·눈 위 공중 음성·고공 음성·취소 후 음성, 이전 비공격 이력 차단이 통과했다. 메인 Run200·Dodge288 압축 표본과 최대35/55=.636364가 기록돼 이동에서 weapon50/55 crater가 없음을 확인했다. 공격 접촉 검사에서는 실제 부여된 Ability를 활성화하고 평가된 포즈를 고정하거나 무기를 배치했다. 모든 자연스러운 공격 montage의 전체 칼날 궤적이나 원작 픽셀 일치 검증은 아니다. 실제 GPU 고립 발34cm(요청35cm 대비1cm 범위), 무기50cm, weighted 층53cm와 잔여3cm·범위 밖0·바닥 agreement를 검증했다. CPU mip0 식은 source-layer 직접 계산 대비 최대0.00000237cm 오차지만 source weight mip/filter·face normal 대 Nanite smooth normal 차이와 detached 장비 중심선 probe 근사는 남는다.

메인 CPU `Profile(20261008_104433).csv`, SnowTick active1,530 표본 평균0.420499/P95 0.817000/max6.013800ms. background Development Editor, cold/cache·동시 에디터와 보행/고정 공격 fixture를 포함한다. 빠른 자연 공격 sweep 최악 비용·GPU/shipping FPS나 이전 표본 대비 개선율로 해석하지 않는다. 비공격 무기는 geometry probe/trace를 건너뛰며 공격 probe 간격6cm와 이미50/55로 눌린 중심의 큰 brush 재작성 생략을 적용했다. 기존 bounded cache/texture budget·cleanup을 유지했다.

현재 정본은 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/{Delivery,FinalVerification,MainVerification,NativeBuildProof}.json`, `StagePIE.log`, `MainVerify.log`, `Backup`이다. canonical SHA `57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7`; 선택 모듈 `UnrealEditor-KhazanSnowWeaponContact20261008.dll` SHA `f6b86d4a25530168c93aa00092aa417cadb94ea0acd1e018116bad2f3258c2a2`. Source3의 SHA도 receipt에 있다. 모든 비소유 Source를 compiled Stage와 byte 비교하고 최신 Main Source/기본 맵/manifest/보호 파일 CAS를 확인한 뒤 Source3·map·새 alias/manifest만 선택 전달했다. 원래 DLL a95c2156…bb2, 이전 alias/Preview·material2·BP Original5·ghosting Config를 보존했다. 메인 scene9,869 actor/원본9,868 poses/눈46/micro65/fire258/weapon profile4를 새 프로세스에서 확인했다.

기존 Contact55 worker2256은01:17 UTC 이전 status를 보존하고 중지해 새 전달과 충돌하지 않도록 했다. 이전 PendingCanonical/Delivery/Preview FinalVerification은 과거 증거로 보존한다. `Contact55_20261007/PendingApplyStatus.json`은 새 성공 receipt를 가리키는 `SupersededByAttackContact20261008`, canonical pending=false다. 이전 Preview 성공을 canonical QA 성공으로 바꾼 것이 아니라 이번 fresh canonical Main QA가 적용 완료 근거다. 초기 설치·old wait_apply/finalize를 재실행하지 않는다.

사용자 PID3528은 전달 전 DevMap·PIE/dirty 없음에서 read-only 확인했다. 사용자 save/reload/PIE/camera/selection/close/전역 RESETLOADERS를 실행하지 않았고, 새 C++ 모듈은 실행 중인 이전 모듈을 강제로 교체하지 않았다.01:50:20 UTC 마지막 health는 disconnected이고 Windows process 목록에도 UnrealEditor가 없었다. 사용자 세션 종료를 어시스턴트가 실행한 것으로 기록하지 않는다. 다음에 새 에디터에서 기본 HeinMach를 열면 선택된 새 native 접촉을 확인할 수 있다. 마지막 상태는 `MainBeforeDelivery.json` 및 `MainAfterDelivery.json`을 따른다. 이는 전달 대기나 구현 미완료와 구분하는 사용자 실행 세션 전환 사항이다.

후속 수치 수정은 현재 Source/맵/receipt에서 시작한다. Weight/UV/height/rim 머테리얼을 바꾸면 profile도 다시 굽고 private Stage `launch author`→fresh `launch audit`→native RHI→guarded selected delivery→fresh Main QA 순으로 진행한다. 이미 완료한 원작 전수 추출/초기 설치/예전 pending blob 재적용을 반복하지 않는다. Source intake 전에 본 Snow Source3을 별도 보존해 최신 사용자·독립 작업을 받아들인 후 복원/재빌드한다. 자연 공격의 대표 빠른 montage와 정확한 경사/mip 오차 조정은 별도 검증 범위다.



<!-- HeinMachSnow_AttackContact_20261008_normal_rebuild_verified -->
## 2026-10-08 11:01 KST — 후속 일반 Main DLL 빌드도 새 접촉 검증 완료

전달 뒤01:49:41 UTC Main 프로젝트 native build가 새로 실행돼 normal DLL과 manifest가 갱신됐다. 이 빌드는 본 작업이 시작한 것이 아니며 되돌리지 않았다. 최신 전체 Main Source가 본 작업의 검증된 NativeBuildProof와 byte 일치하고 canonical/Source3/기존 보호 asset·Config도 동일함을 확인했다. 현재 manifest는 `UnrealEditor-Khazan.dll`, SHA `4ca0cc527b9d94c6812246befd974e5ce268ec5ece23207add6394d369cde354`다. 앞 절의 alias 선택·원래 DLL 보존은 당시 전달 사실이며 현재 선택 모듈 정본은 이 절이다. 이전 성공 Delivery/FinalVerification을 수정하지 않았다.

새 hidden MainPID19372에서 실제 normal DLL 경로·저장 canonical profile2/55cm·작은 발 범위/scene9,869를 재검증했고01:58:40 UTC `Khazan.Snow.PIE` Success 및 정상 종료했다. Player Run142/Dodge236 표본 maximum35/55, Player/4NPC active 공격 지면 양성/공중·비공격·취소 음성과 기존 GPU 발34/무기50cm/cache/EndPlay 회귀가 통과했다. 자료는 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/NormalMainRebuild_20261008`의 snapshot Delivery(not_a_delivery), MainColdBuild.log, MainVerification/Exit, MainVerify.log다. 이번 Snow 수정·canonical 반영은 완료이고 old worker/preview pending을 재개하지 않는다. 기존 모듈 변경 및 source 보존 절차·원작/mip/normal/자연 fast sweep/GPU/shipping 미검증 범위는 유지한다.

같은 Development Editor/frozen attack scope의 normal DLL SnowTick은 active929 평균0.507301/P95 1.033800/max4.364200ms, `Profile(20261008_105739).csv`다. 이전 .420499ms와 조건이 다른 별도 관측이며 개선율로 비교하지 않는다. 사용자 에디터를 저장/종료/재시작하거나 예전 alias로 manifest를 되돌리지 않았다. 새 에디터에서 기본 HeinMach를 확인한다.

<!-- HeinMachSnow_PlayerCapsule_20261008_complete -->
## 2026-10-08 14:26 KST — 플레이어 캡슐 기준 눈 파임 Main 완료

사용자의 최신 요청에 따라 플레이어의 작은 발별 stamp를 실제 이동 capsule 기준으로 대체했다. 제품 수정은 기존 KZSnowDeformation.h/.cpp 두 파일, 개발 검증은 기존 KZSnowDeformationPIETest.cpp다. Controller/ASC/Ability/CMC/AI/AnimInstance gameplay 변경, 새 runtime file/class/component/manager/UPROPERTY, map/material/texture 수정은 모두0이다. 기존 layer 최대55cm·이동35cm·무기50cm, tile/cache/field budget 및 shader/EndPlay 계약을 유지한다. FootRadiusCm는 이제 몬스터의 기존 발별 footprint에 사용되며 플레이어 capsule 반경을 별도 임시값으로 덮어쓰지 않는다.

GT/PostUpdateWork의 기존 ObserveCharacter가 PlayerControlled ACharacter의 GetScaledCapsuleRadius/HalfHeight와 실제 component center를 읽는다. 바닥 B=center−(0,0,halfHeight), 지역 눈 높이 H는 기존 weapon과 공유하는 private GetSnowSurfaceHeight가 authored profile·bilinear weight·half-float field·compression/rim/altitude/window 식으로 계산한다. 높이 h=(H−dot(B−ImpactPoint,Normal))/Normal.Z가 양수일 때만 접촉한다. 하단 반구의 footprint 반경은 sqrt(c*(2R−c)), c=min(h,R)이며 항상 현재 scaled capsule R 이하다. 기존1.4배 rim envelope를 나눠 raw brush radius를 정하므로 rim 포함 범위를 임의로 키우지 않는다. 수평 바닥의 capsule 단면 계산을 지역 경사 평면에 적용한 원형 근사이며 모든 경사/높이 변화의 정확한 체적 교차라고 주장하지 않는다. R=34cm는 실제 검증 pawn의 관측값이며 원작 capsule 확인값 또는 새 gameplay tuning이 아니다.

기존 FContact/StampSnow와 이동 간격 max(texel,rawRadius*.25), teleport gate, C2 shoulder 및 max compression을 재사용한다. 플레이어 foot/paw row만 skip/reset하고 몬스터 foot/paw와 모든 body contact는 유지한다. capsule NoCollision 또는 지역 눈 위로 벗어나면 접촉하지 않는다. player 제어 해제 시 해당 capsule contact map만 제거하여 재빙의의 stale sweep를 막는다. 무기 활성 Attack Spec 판정과 실제 지역 표면 접촉/tolerance6cm·50/55는 이전 구현 그대로이며 shared height 추출 외 의미 변경이 없다. 새 공격/이동 상태 사본, GPU readback 및 CPU skinning은 없다.

Private 최신88Source intake 및 cold build170.91s Succeeded. Stage PID27416과 새 hidden Main PID19372의 전체 Khazan.Snow.PIE가 각각 Success/exit0이다. mesh를500cm 올려 발/몸 bone 접촉을 제거한 fixture에서 capsule R34cm 중심=.636364, 20.286cm 거리=.067291, 38cm 바깥=0이다. stationary bound 및 airborne negative도 통과했다. fresh Main 실제 Run435.81cm/Dodge396.25cm 이동 모두 maximum35/55, Dodge36 grounded capsule frame이다. 기존 NPC4 발/몸·active 공격과 지면/공중·비공격/취소·이력·cache/scroll/EndPlay 및 GPU isolated foot34cm/weapon50cm 회귀도 통과했다. GPU foot 값은 공용 field writer의 고립 표현 fixture이며 capsule 전체 화면의 픽셀 일치 검사로 확대하지 않는다. 고정/배치 공격 fixture는 모든 자연스러운 montage sweep의 증거가 아니다.

Source3는 Main에 적용했고 module만 새 alias UnrealEditor-KhazanSnowPlayerCapsule20261008.dll로 선택 전달했다. SHA a237a02fe7d3e78f1e036d215ca773e223efb35e8b9a184046e3ce8379fa7b58. canonical SHA57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7, actor9869/profile2 및 map/Config/BP/Leg PA/기존 normal DLL·비소유Source85의 hash를 보존했다. Main fresh verifier는 실제 loaded alias path/hash를 확인했으며 asset save/material recompile0이다. 사용자24552/DevMap/noPIE/dirty0는 read-only 확인했고 save/reload/PIE/camera/close/LiveCoding을 실행하지 않았다. 현재 실행 중인 사용자 editor의 DLL은 강제 교체하지 않았으므로 새 코드는 해당 editor 재시작 후 적용된다.

Main SnowTick GameThread CPU는 full GPU/player/NPC fixture의 nonzero558 samples 평균.746997ms/P95 1.5736/max7.9532ms이다. Stage452 samples 평균.721ms/P95 1.632ms는 별도 관측이다. Development Editor의 full native workload이며 shipping FPS/GPU 성능 및 이전 다른 fixture 대비 개선율을 의미하지 않는다. 기존 bounded cache/texture 예산과 incremental dirty upload는 유지했다. 원작 수치·pixel parity·모든 경사의 밀착까지 검증한 것은 아니다.

재개/검증 정본은 Saved/ImportReports/HeinMachSnow_20261006/PlayerCapsule_20261008의 CompletionValidation.json, Delivery.json, NativeBuildProof.json, QASummary.json, Stage/MainVerification 및 Exit, Stage/MainPIE.log, MainSnowTick.csv, Before/Backup이다. 진행 중 continuity 절의 남은 Snow build/native 전달은 이 완료 절로 대체된다. 후속은 현재 Main Source/manifest/동일 canonical에서 시작하며 이전 AttackContact/Contact55 delivery 또는 이번 이미 완료한 publish를 다시 실행하지 않는다. 별도 Charge/Spinning 문제의 검증/에셋 수정은 Snow 완료와 구분하여 기록한다.
## 2026-10-11 — 사용자40cm / capsule padding 후속 Main 완료

기존 shader/profile contact를 유지하며 DeepSnow40cm/발35cm=.875/weapon substrate cap1 및 문서화된 extra padding15cm를 적용했다. 기존55cm reference는 current40cm로 바꾸고 profile2를 다시 적용했다. 이는 사용자 수치/명시된 해석이며 원작 확인값이 아니다. MainSnowResume03의 GPU40/발 관측34(표본 허용오차 내), capsule 바깥0/이동·회피·공격·공중·몬스터4종을 검증했다. exact 계산·DEV fixture 보완·saved map/backup은 [후속 정본](COMBAT_PRESENTATION_FOLLOWUP_20261011.md) 및 FinalVerification을 따른다.

## 2026-10-16 — 현행 구현 상세 설명을 위한 소스·저장 증거 대조

사용자 요청은 현재 눈 변형의 상세 설명이며 게임 파일 직접 수정 요청이 아니다. Router → 관련 Architecture/Migration 표현 책임 → 이 정본/10월11일 후속 → 현재 Source 순으로 확인했다. C++/BP/asset/Config 수정, 새 build/PIE, 에디터 저장·실행 제어는 하지 않았다. 이번 실제 변경은 Art/Engineering 정본 하단 설명 기록뿐이다.

`KZSnowDeformation.h/.cpp` 및 `KZSnowDeformationPIETest.cpp`는 `Metadata/CombatPresentationFix_20261011/MainResume/FinalVerification.json`의 최종 SHA와 현재 파일이 각각 동일하다. 해당 receipt의 material2도 동일하다. 현재 맵 SHA는 `1d224b14ae0ec39b90229e2a122b174b672ca64d976f3c0ef0032236c47f7c00`으로 10월16일 RoutePrune 최종 receipt와 동일하다. RiderLink는 disconnected였으므로 live actor override/현재 실행 포즈를 새로 검사한 것으로 표현하지 않는다. 맵 배치·재질 개수는 Art 정본의 같은 날짜 절을 따른다.

현행 호출 경로는 `BeginPlay`의 transient RGBA16F texture 생성/대상 component MID 바인딩 → `TG_PostUpdateWork`의 `Tick` → `FollowPlayer` → 월드의 각 ACharacter에 `ObserveCharacter` → `StampSnow` → 오래된 창 밖 cache 퇴거 → `UploadTiles`다. R=압축, G=rim, B=substrate world Z(cm), A=유효 여부이다. CPU 셀은 float3이며 upload 시 half-float RGBA로 변환한다. 기본 2048²/2cm/128² tile/256 cache는 기술 예산으로 texture32MiB, 전체 tile 셀 payload48MiB이며 container/전송/profile 비용은 별도다. time refill/savegame 저장은 없다.

현재 PlayerControlled 캐릭터의 이동 흔적은 발별 brush가 아니라 scaled capsule 하단과 `GetSnowSurfaceHeight`의 교차로 계산한다. immersion>0인 경우 `sqrt(c*(2R-c))+max(0,PlayerCapsulePaddingCm)`를 바깥 반경으로 쓰며 `c=min(immersion,R)`다. padding15cm와 FootCompression35/40은 10월11일 계약이다. rim envelope1.4를 나누어 실제 Stamp 반경을 얻는다. 몬스터는 foot/paw와 sole toe0, 양쪽은 pelvis/spine/head/팔다리의 기존 bone contact를 사용한다. 최초 문서의 IsMovingOnGround 설명을 현행 필수 gate로 읽지 않는다. 현재 함수는 실제 trace/pose/capsule 교차를 검사하고 body는 MOVE_None에서도 관측한다.

첨부된 `KZMonsterPatternAbility.cpp:25`는 Ability asset tag `Ability.Action.Attack`을 설정한다. Snow owner는 `ObserveCharacter`에서 active Spec의 AssetTags를 읽어 무기 접촉 관측을 허용한다. Ability가 직접 StampSnow를 호출하거나 피해 승인/공격 collision window를 Snow가 기다리는 구조는 아니다. 공격 수명이 끝나면 bWeapon 이력만 지워 다음 공격까지 sweep를 이어 붙이지 않는다. merged weapon은 editor에서 구운 bone-local center/극점, 별도 장비는 실제 bounds 장축5점을 사용하고 프레임 사이를 접촉 tolerance 기반으로 표본화한다. probe/큰 brush는 실제 칼날 collider와 구분한다.

`GroundContact`는 Visibility complex 수직 trace, MicroDressing 제외, SurfaceTag/normal.Z gate다. 무기는 넓은 substrate 탐색 뒤 `dot(probe-hit,normal)`이 `[-tolerance, currentSnowHeight+tolerance]`인지 다시 검사한다. `GetSnowSurfaceHeight`는 profile의 높이분자/전체weight/눈weight를 각각 bilinear한 뒤 나누며 CPU field도 GPU와 같은 half-float/mip0 bilinear/window shoulder/altitude gate로 계산한다. profile 미작성 지면은 무기·capsule 접촉을 허용하지 않는다. `WeaponContactHeightCm`의 C++ 기본24와 과거 HeinMach 저장79 override를 혼동하지 않는다. 10월11일 author는 압축/padding/profile만 갱신하며 이번 턴의 live override 재조회는 없었다.

`StampSnow`는 타원 좌표의 quintic depth, rim, max compression 누적과 고도 불일치 셀 reset을 사용한다. 압축R은 현행 reference40cm에 대한 요청 깊이 비율이며 얇은 layer에서는 substrate에 clip된다. `GetCompressionAtLocation`은 단일 CPU cell의 R 조회이고, 실제 렌더 높이와 동일한 의미가 아니다. 창은 world tile의 modulo GPU 주소로 겹친 영역을 보존하고 새 strip/dirty tile만 올린다. 같은 XY 여러 지면을 독립 보존하는 다층 field가 아니며 퇴거한 이력/레벨 재시작 뒤 흔적도 영구 보존하지 않는다. 현재 Tick은 창 밖 캐릭터까지 순회하므로 캐릭터 관측 전체가 거리로 cull된다고 설명하지 않는다.

다음 확인은 이 날짜 절 → 실제 두 Source → MainResume receipt/Snow40 readback → 최신 맵 증거 순이다. shader 높이·weight·UV·rim을 수정할 경우 두 SurfaceContactSamples도 동일 계약으로 다시 bake해야 한다. 원작 shader/native 일치, 자연스러운 모든 빠른 무기 sweep·경사·Shipping 성능은 기존 미검증 범위를 유지한다. 설명 요청 완료이며 기존 author/delivery/추출을 재실행할 잔여 작업은 없다.
