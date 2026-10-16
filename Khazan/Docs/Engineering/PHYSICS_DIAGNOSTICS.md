# Physics 진단 기록

> 런타임 movement physics, collision, physical animation, ragdoll, constraint 문제만 기록한다.
> 메시 임포트 단계의 collision/physics asset 생성은 Art 작업으로 분류한다.

## 2026-08-31 기준

- 아직 별도 physics 진단 기록이 없다.
- 새 진단 시 증상, 재현 Level/BP, collision preset과 channel, simulation 주체, authority/network 조건, 관련 body/constraint, 로그 또는 디버거 증거, 수정과 검증 결과를 날짜별로 추가한다.

## 2026-09-29 HeinMach CharacterMovement collision 복원

- 재현 Level은 `/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment`, Pawn은 `BP_Player`, capsule은 radius `34 cm`/half-height `88 cm`다.
- 원인은 복원된 Landscape/prop mesh의 gameplay collision·navigation data와 원작 `HeinMach_Chrcollision` route wall이 플레이용 맵에 완결되게 연결되지 않은 상태였다.
- Landscape 48개와 source 판정 prop에 collision을 적용하고, 활성 비degenerate `xxWallComponent` 2,281개를 `WorldStatic/QueryOnly` hidden HISM으로 저장했다. source에서 명시적으로 disabled인 wall 1개와 degenerate 924개는 제외했다.
- PIE에서 `IA_Move` 2초 입력으로 평면 `706.740701 cm`, 수직 `56.102992 cm` 이동하고 입력 해제 뒤 `is_moving_on_ground=true`를 확인했다. source wall instance `2229`를 향한 Pawn profile trace가 `BoundaryCollision`에 blocking hit를 반환했다.
- 최종 물리·경로 report는 `Saved/ImportReports/HeinMach_Playability_RuntimeVerification.json`, instance provenance는 `HeinMach_RouteCollision_SourceMapping.json`이다.

## 2026-10-07 — Original Player 모듈 파츠 RigidBody / import wrapper와 joint 초기화 공간

- 증상/재현: 별도 PlayerPartsWork DevMap standalone PIE, main .01 component와 imported root100. Original 5파츠 CopyPose 연결 후 WorldSpace RigidBody에서 Torso bounds2.50e11cm로 변형. baseline anchor 복사는 정상이라 단순 attachment/LeaderPose 문제로 분류하지 않았다.
- 원인·수정: UE5.8 ref-pose FBodyInstance/ConstraintInstance 생성의 scale100 joint frame과 실제 unit world pose 차이. ImmediatePhysicsAdapters가 geometry는 unit actor scale로 다시 생성하는 것을 actual actor AABB로 확인해 **joint Pos1/Pos2만** .01 변환한 derived Original PA3개를 ABP Override로 사용. 기존 Original geometry/material/limits/damping/mass와 main query PA는 보존한다. source metadata physics parity는 미확인이다.
- 주체/채널: Character Mesh와 파츠는 CharacterMesh/QueryOnly/world ragdoll=false. 독립 엔진 UAnimInstance의 CopyPose/RigidBody가 cape/hair/cloth 보조 포즈를 소유한다. Player Capsule/CMC/GAS/Montage에 동일 gameplay 상태를 추가하지 않았다. network replica/dedicated server는 미검증이다.
- 검증: 최종 PlayerParts.PIE/Original shape AABB·unit world bone scale·source anchor·bounds/화면, rendered Guard Success. rendered Heal 고정 checkpoint 실패2로그 보존, stock main DLL/NullRHI 동일 Heal 전체 Success 및 stock actual PIE configuration readback Success. 정본/정확한 로그는 PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md, Metadata/PlayerParts_20261007이다.
- 적용: 신규/잠금 없는10패키지 전달. main PID7220가 BP_Player+Torso/Leg/Hair PA를 잠가4패키지는 전달 대기. main BP_Player의 실제 부착은 아직 미적용이며 소스/DLL/Config/Map/Imperial 변경 없음. 사용자 작업 저장·main 종료 후 guarded delivery script로 남은4개만 적용한다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

증상은 HeinMach의 작은 바닥 돌 위에서 capsule/CMC가 표면 요철을 따라 높이가 변하는 현상이다. nav 해상도만의 문제로 확정하지 않았다. actual Pawn block과 그 아래 walkable substrate를 검사해65 supported micro dressing만 Pawn Ignore/Nav 영향false로 저장, 큰 돌/절벽/기존2,281route wall/poses는 보존했다. 81component의8노출 표준 channel을 원본과 비교 저장/reload하여 Pawn65개 외 응답을 보존했다. 재검증 Recast63MoveTo/1,485points/1,422complete segments 통과.

WaterfallUp StaticMeshActor_6987(노출bump11.807cm) 전후 actual CMC 약685/682cm 이동을 10cm 재표본화한 높이2차차분RMS1.81303582→1.50061163cm(17.2321% 감소). 원인·결과의 범위는 이 표적 fixture이며 모든 map animation 떨림 제거로 확대하지 않는다. CMC/nav 전역 MaxStep/slope/voxel과 character physics source는 이 눈 작업에서 수정하지 않았다. snow visual 변위는 기존 substrate collision 위로 쌓이고 접촉 시 substrate까지 압축한다. Actual RHI 압축깊이14.5cm/render-physics<1cm/main Khazan.Snow.PIE Success04:22:07 UTC. 근거는 Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/{FloorCMCBeforeAfter,CollisionChannelsPreserved,NavigationFinal}.json와 FinalVerification20261007.json, 상세는 HEINMACH_SNOW_IMPLEMENTATION_20261006.md 마지막 절이다.

## 2026-10-07 — Original 파츠 보조 물리 Main 전달 완료

앞선 file lock4개는 정상 메인 종료 이후 해소돼 14/14 prepared SHA 전달 완료다. 새 메인 PID8292/DevMap의 read-only saved readback에서 Original5 메시/PA/ABP, CharacterMesh0 아래 SCS 계층, relative identity와 기존 본체 .01 배율을 확인했다. Torso/Leg/Hair의 검증된 joint-only 단위 보정·geometry 보존 계약을 그대로 사용하며 새 physics 튜닝·재임포트·본체 ragdoll 변경은 없다. FinalMainHashVerification 보호95파일 unchanged, MainReadyAudit dirty0/PIE없음. 기존 격리 physics/shape/Guard/stock Heal 성공과 이번 메인 load/hash 검증을 구분한다. 상세와 연속 화면·원작 physics 일치의 미확인 범위는 PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md 최신 Main 완료 절이다.

## 2026-10-07 — Original Player 파츠 물리 메인 적용 완료

후속 사용자 Main 반영 요청으로 main26644의 identity/DevMap/PIE Idle/dirty0를 재확인해 정상 종료했다. 남은 BP_Player와 Original Torso/Leg/Hair PA4개 전달 성공, 전체14 SHA 검증 완료다. main8292 저장본에서 Original5/SCS parent/PA/ABP/relative1/QueryOnly/no world simulation, 본체 Player_PhysicsAsset과 6 BP UP_TO_DATE를 확인했다. 최신 Source/Config/Map/본체 ABP·PA/모듈95파일은 보존했다. 기존 lock 대기는 해소됐으며 joint unit 보정과 기존 격리 physics PIE 근거는 유지한다. 이번 main에서 gameplay PIE를 새로 실행한 것으로 표현하지 않는다. 근거 MainIntegrationResult.json/MainReadyAudit.json과 PlayerParts 정본 최신 절, 남은 범위는 사용자 연속 화면/원작 physics 파라미터 일치 QA다.

## 2026-10-07 — Player secondary body collision 완료

정본: PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md의 몸 충돌 최종 완료 절. 모든 내부 pairs disabled였고 파츠 skeleton에는 일부 본체 bones가 없어 actual parent Mesh/Player_PhysicsAsset의 engine AddClothCollisionSource와 RigidBody external cloth collision을 적용했다. 세 part 각18 kinematic body가 현재 부모 pose/원래 cm geometry를 정확히 따르고 실제 contact/impulse가 모두 발생한다. Runtime C++0, 기존 asset7 수정/Main 전달 완료/155보호SHA 동일.

UE5.8 ImmediatePhysicsActorHandle CreateParticleHandle가 shape collision flags를 전부 다시 켜므로 NoCollision mass-only broad capsule + thin proxy 안은 실패했다. 최종 single thin capsule radius cloth1cm/hair.75cm, imported mass/CoM/body-axis inertia diagonal 계산 복원, damping linear.05/angular.35(s^-1)다. damping/radius는 원작 확인값이 아닌 assistant 임시값. source Original/main PA/joint limits 유지. SingleThin/Guard/Heal/native52 및 최신stock reload 성공, 실제 뒤쪽 화면 확인. 자료·전체 tensor/정점·모든동작 일치 미확인은 정본/BodyCollisionTuning provenance 참조.

도구 실패 이력은 startup26160/23800/29600 logs(심볼 부족으로 원인 확정 불가), duplicate pin compile failure, USkeletalMesh 대신 component API 사용 보완, stock 비교0bone/None physics override 검사 오류를 보존했다. 실제 제품 runtime 오류와 분리한다. 최신main19684/DevMap read-only 검사는 관련7 BP UP_TO_DATE, Original5 SCS hierarchy/외부collision3 flags, dirty0/PIE 없음이다. main에 자동PIE/force quit/SaveAll을 하지 않았다.


## 2026-10-07 ? Hair ?????? ?? ?? ??

??? PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md? Hair ?? ?? ?? Metadata/PlayerParts_20261007/HairRefinement?. ??18 dynamic bone?? ?? weighted ponytail65 bone/14?? ????? Head/root3 kin, ?? ?4?? ?? CopyPose?. ??? derived Hair PA1?/runtime C++0, original/main PA?BP/ABP?????? ?? ???. ?? external18 anatomical collider? current pose/shape ? ?? contact/impulse? ????.

SLERP acceleration support/near-critical damping??? angular limits? thin virtual inertia conditioning? ?? ???? ?? assistant ?? ????. `UPhysicsConstraintTemplate` current instance ?????? PIE default profile/save? ??? ???. SetDefaultProfile ?? ?? ?? ??? ???? ?? saved65 profile readback??. Head ?? ???? ?? ?? ??4 bone? ?? capsule? ???? ???. ?? capsule natural axial inertia? ?? flip ?? ?? ????, ?? mass/contact shape? ???? ?? principal moment? ?? ??? ?? ?? ???? actual stability? ????. ?? tensor ???? ???? ???.

?? native ? saved process08:22:49 UTC Success: tip RMS8.810660?7.200052cm/peak25.207770?16.502579cm, actual responding18?65, local peak27.974185deg<35 QA. Hair11773/body contact positive, finite/scale/bounds/shape/anchors ??. same control rotation/input?? close camera arm? QA? ?? ??/????. ?? alias stock Guard/Heal/readback ??, Main21248 read-only saved7BP/Original5/dirty0/PIE??/candidate1 ? ??161SHA ??. ???/?? ???pose?LOD???? QA? ???. ?? INI Read void ???/DefaultProfile/face lock/low inertia/enum formatting ??? ????? ????? ?? runtime ??? ????.


## 2026-10-07 23:36 KST — Torso·Leg 천 조정 Main 반영

`PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md`의 이번 완료 절과 `Metadata/PlayerParts_20261007/ClothRefinement/Verification.json`을 따른다. 기존 PA2에 Hair 기준 복원·감쇠, 실측 Leg full-strip contact, uniform principal-inertia floor(Torso1/Leg4), Leg Depth0 swing32deg와 solver24/4/4를 적용했다. 원작 physics 직접값은 미확인이며 임시값/계산값을 구분했다. Hair·본체·BP/ABP·Main Source/DLL은 보존했다.

fixed30 및 fresh 일반 시간 간격 native PASS, 메인 실제 모듈의 Stock Guard/Heal와 Original5 runtime readback PASS. Main3528에서 PA2만 CAS/선택 reload 및 ready audit를 완료했고 HeinMach world·선택·dirty0/noPIE·보호161파일을 유지했다. Torso867정점은 세 표본 inside0, Leg dominant3835정점은111/390/350이 body proxy 내부다. 관통 완전 제거/모든 전투 pose 검증을 완료했다고 표현하지 않는다. 숫자·shape·inertia·Python readback 한계와 정확한 SHA/증거는 정본 및 보고서에 기록했다.


<!-- LeftShoulderCloth_20261008_complete -->
## 2026-10-08 10:38 KST — 어깨 spring-only 변경 검증 및 기존 Hair 일반 시간 간격 관측

어깨 조정은 fixed30 전후/새 프로세스 saved native PIE 및 실제 Main module stock readback을 통과했다. active spring8 field 외 profile diff0, saved-default 일치, fixed30 Torso peak11.999827deg(45deg QA 미만), 세 자세 surface867/dominant735 inside0. Main selective reload 완료, protected162/Original5/BP7/기존 solver 유지. `Metadata/PlayerParts_20261008/LeftShoulderCloth` 참조.

일반 시간 간격 NullRHI(고정 timestep 없음, cap60) 후보2회에서 Hair peak60.079030/59.592638deg, 원래 Torso 복원 대조에서71.877890deg로 Hair35deg QA만 실패했다. Torso peaks23.880193/15.335114/20.995945deg와 Leg는 각45deg QA 미만이었다. Hair PA는 동일 SHA, fixed30 Hair/Leg 전후 metrics는 정확히 동일하다. 원래 Torso 대조에서도 관측됐으므로 이번 spring 변경의 회귀로 단정하지 않는다. 실제 timing/solver 초기화/부하 중 어느 원인인지는 **미확정**이며 별도 분석 대상이다. 테스트 임계값과 Hair 설정은 수정하지 않았다. 실패 원문·선택 buffered block·SHA는 `NormalDeltaObservation.json`과 세 원문 log에 보존했다.

Main 첫 전달 WinError5는 읽기 전용 Restart Manager로 SnowWork PID13888의 공유 파일 잠금을 확인했다. 다른 작업을 종료/조작하지 않고 정상 종료 후 전달을 재개했다. 실패 기록은 MainSelectiveHistory, 성공 기록은 MainSelectiveHandoff/MainFinalState/FinalCompletion에 분리했다.

## 2026-10-08 12:12 KST — 플레이어 허리 Iron2 지속 떨림: 충돌 원인 분리·수정 완료

`Metadata/PlayerParts_20261008/WaistJitter/CauseProof.json`은 Iron2 외부 anatomy 접촉만 진단용으로 끈 대조에서 fixed30 parent-relative 회전 step RMS78.84~82.56→0.74~1.17도/프레임, 다른 cloth30 동일성을 확인했다. final은 collision/simulation을 켠 채 Leg PA의 capsule Center2만 보정했다. 독립 Leg/Body ref를 섞지 않고 공통 pelvis로 정렬해 actual dominant support536 정점과 anatomy18에서 Center를 계산했다. 원작 physics 값은 미확인이며 계산/임시 정책으로 구분했다.

`CenterApplied.json`은 다른 body/constraint/solver 필드 보존과 Save1을 기록한다. Candidate/SavedReload fixed30 및 NormalDelta native 모두 Success, final Iron fixed30 step RMS0.168~0.207도/프레임·일반 시간 간격 speed RMS4.65~6.04도/s·실제 접촉/actor collision1을 확인했다. stock Main base DLL 별도 실행과 Main13700 선택 전달·재로딩/ReadyAudit도 성공했다. 완료 SHA/owned editor 종료/private binary 복원/보존163은 `FinalReceipt.json`을 따른다. Hair·최신 왼쪽 어깨 설정은 유지했다.

주의: 과거 baseline/control PhysicsOff label 구간은 제외하며, 최신 probe는 EnableSimulation과 positive-delta를 사용한다. Frame2 1/100은 UE 변환과 일치해 변경하지 않았다. cached contact gap/ref clearance는 skin penetration이 아니며 모든 동작 관통0이나 원작 일치 검증은 아니다. baseline/control과 후보의 BP/Source/probe 차이, Main live patch와 stock base DLL 차이를 보존한다. 이전 shoulder Hair normal-delta 실패 기록은 유지하며 이번 조건의 통과만 추가한다. 상세 수치/계산/재개 기준은 `PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md` 최신 절과 해당 report README다.

<!-- ShoulderSoftening_20261008_complete -->
## 2026-10-08 — 어깨 가까운 천 추가 유연화 검증·카메라 notify 실패 분리

현재 Torso 왼쪽 Cape8 관절만 active SLERP spring/damping을 낮추고 proximal2의 swing1/2를 넓혔다. 배율은 proximal .60/sqrt(.60)/1.5, middle .75/sqrt(.75)/1, distal .85/sqrt(.85)/1의 **어시스턴트 임시값**이며 원작 physics field는 미확인이다. proximal 저장값은 spring615.537→369.322, damping50.909→39.434, swing8.8→13.2deg다. SetDefaultProfile 후 full expected constraint/default 및 body·joint·PA snapshot 검사로 anchors·twist·geometry·mass·관성·충돌·solver/Hair/Leg/Iron 보존을 확인했다. Main runtime Source 변경0이며 기존 editor-only Scripts만 확장했다. 상세 기준값·property·배율은 `PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md` 이번 완료 절과 `Metadata/PlayerParts_20261008/ShoulderSoftening/TemporaryTuning.ini`에 있다.

baseline/candidate와 fresh saved native PIE Success. 짧은 패널 speed RMS+29.82%, 긴 천 첫 simulated 관절+2.72%이나 전환 kick을 포함해 지속 flutter 증가를 보증하지 않는다. Torso peak13.201777deg/8개, Hair31.588156deg/65개, Leg32.207188deg/30개가 기존 QA를 통과했고 Hair·Leg metrics/허리64 late bone-window CSV 비교는 전후 동일했다. Torso LOD0 positive-direct-sim867/dominant735 정점은 세 자세에서 external anatomy18에 대해 inside0/finite다. 표본 body-proxy 검사를 모든 pose/피부 관통0으로 확대하지 않는다. `NativeComparison.json`/`SavedReloadComparison.json`/`Verification.json`이 실제 증거다.

첫 `IntakeInputMismatchNative.log`는 Input.Action.RB 매핑 불일치이며 최신 입력 자료 동기화 뒤 성공한 재시험으로 대체했다. `CloseFramingNotifyFailureNative.log`의 전 파츠 motion0 실패도 보존한다. Python 기본 notify는 CoreUObject PropertyAccessUtil의 PreEditChange/PostEditChangeChainProperty를 발행하고, ActorComponent의 등록 해제/재등록 및 owner RerunConstructionScripts가 BP-created component를 재생성할 수 있다. fixture는 파츠 weak pointer를 초기 캐시하므로 이 경로가 샘플을 무효화할 수 있다. 해당 실패 run에서 재구성 호출을 계측한 것은 아니므로 원인 확정/PA 회귀로 표현하지 않는다. transient camera에 notify NEVER를 사용한 최신 saved 재시험은 Success이며 PA SHA는 동일했다. 이전 Hair 일반 시간 간격 실패는 삭제하지 않는다.

stock 검증은 실제 mapped Main base DLL C251AC…를 사용했으며 선언된 SnowPlayerCapsule 모듈/live patches와의 실행 동일성은 미검증이다. private binary 복원 후 Main24552 DevMap에서 TorsoPA1 전달·reload Success, protected166 동일/dirty content·map0/noPIE/선택 보존을 확인했다. 최초 WinError5 실패는 MainSelectiveHistory에 보존하고 재시도 성공을 `MainSelectiveHandoff.json`/`MainReadyAudit.json`에 기록했다. 최종 Torso SHA EC471B6F…C400D22. 상세 원시값·화면·보존 SHA와 후속 기준은 PlayerParts 정본 최신 절이다. 전체 ClothAuthor/HairAuthor나 이번 배율 Apply를 반복하지 않는다.


## 2026-10-08 — Player Combo 공격 query 충돌 정본

- 공격은 물리 simulate component 추가 없이 Ability의 활성 구간 query로 검사한다. Box/Sphere overlap+sweep 및 Cylinder broadphase+finite-cylinder/capsule narrowphase를 사용한다. 엔진 frame 사이에 지나간 authored key도 검사하며 green debug shape를 그린다.
- 원작 Box halfextent/offset은 stored Bounds116/116 재구성으로 확인했다. actor-facing groundcm baked center에 현행 mesh Z=-88cm만 적용하며 yaw/.01을 중복 적용하지 않는다. Cylinder height 의미는 미확인이므로 임시 halfheight=Size.Z/2로 표시한다.
- controlled 정상 capsule 적중/범위 밖 제외와 중복·취소·하한 등 native13case 통과. Spinning7/OverFury19 총횟수 검증은 큰 target capsule이며 정상 target의 모든 공격 시각 정합 검증과 구분한다. 구체 데이터/출처/보고서는 `Docs/Engineering/PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md`를 사용한다. Player parts physics/BP/ABP는 이번 전달에서 보존했다.


## 2026-10-13 — 몬스터 보조 물리 준비·실행 품질 조사 중

사용자 직접 요청으로 player의 현재 물리 설정을 재사용한다. Router/Architecture/Migration/Physics/PlayerParts 정본과 저장 metadata에서 시작했다. 기존 gameplay6종 PhysicsAsset None을 확인했고, imported35 SK 전체에 PA35/secondary post-process20/Elite CopyPose1 및 기존 BP6 설정을 작업본에 생성했다. 신규 runtime class/component/manager/tag0이며 기존 KZMonster.BeginPlay의 modular follower 초기화만 작은 보완을 준비했다. 현재 Main 게임 에셋·Source 반영은0이다.

정확한 상태는 `Metadata/MonsterSecondaryPhysics_20261013`과 `Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md`다. NativeAudit01/Author01/HeavyCollision01 Success, PrivateBuild01/03/05 Success. 컴파일 도구 타입 오류 Build02/04는 실패 로그로 보존했다. 첫 PhysicsPIE01은6종 모두 finite/실제 simulation·반응/접촉을 관측했지만 Heavy Hair49.34°, Halberd142.77°, Apes90.63°, Yetuga177.71°가 기존 cloth45° QA를 넘어 **Fail**이다. 조작한 QA를 성공으로 기록하지 않는다. 새 candidate97 packages는 아직 전달하지 않는다.

별도 owned29816/LLDB에서 GameThread `FPhysicsRun::Sample` line110과 PA24/4/4·fixed1/60, active acceleration SLERP·hard angular limits·projection 값과 Halberd idle47.04°를 직접 관측했다. Engine/PDB 하위 stack은 미해결이며 root cause 확정 전이다. `DebuggerEvidence.json`을 보존하고 agent breakpoint 제거/session detach, 기존 user exception8 상태를 유지했다. Debug01은 중단시간 영향을 받는 진단 run이며 생산 성능/정상 타이밍 검증이 아니다.

재개: PrivateBuild06 확인 → 최신 owned process 목록/실제 project 확인 → `KZ_MONSTER_PHYSICS_NO_CONTACT=1` 진단 전용 PhysicsPIE 대조 → 같은 saved candidate의 접촉 활성 대조/worst bone·stage 비교 → geometry/관절 충돌을 근거에 따라 최소 수정 → flag 없는 fresh saved/native/RHI 및 실제 PlayerAttackCollision 회귀 → 최신 Main SHA/CAS·필드 병합과 별도 Main module build/검증 → 완료 기록. 기존 full Author는 existing-result guard가 있으며 반복 실행하지 않는다. 사용 중인 다른 ParticleAlpha/Main 작업 editor를 종료/저장/제어하지 않는다. 원작 anatomy17/17/16 capsule 형상은 `OriginalAnatomyShapes.json`의 field/raw 값, feel은 현재 player의 명시된 TEMP 재사용이다. 전체 원작 물리/skin 관통0 검증은 미완료다.

<!-- MonsterSecondaryPhysics_20261013_intake -->


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset / 천·Hair Main 완료

사용자 요청을 Main에 적용했다. imported SK35 전부 PA35를 연결했고, explicit cloth/hair가 있는20 메시에는 engine RigidBody post-process, 중검병3 모듈에는 shared CopyPose1을 연결했다. 기존 gameplay BP6와 SK35 수정, 신규 PA35/ABP21의97 package + 기존 KZMonster.BeginPlay 파츠 block1 + DEV 검증1의99행을 exact SHA/CAS로 전달했다. 신규 runtime class/file/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. protected Player/Config/기타 Source SHA 차이0이다. 기존 GAS/AI/Ability/피해·몽타주·root motion·VFX 소유자는 유지한다.

MainBuild01 Exit0, MainSaved02 저장0·35 링크/게임플레이 파츠 연결, MainFinalQA01 실제6 family 이동→방향 전환→authored attack section 모션→피격→회복·finite/물리 반응/몸 접촉/중검 CopyPose 및 PlayerAttackCollision 회귀2검사 Success다. 실제 loaded canonical Main module SHA와99 target SHA는 `Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json`이다. 최종 실제 peak: Swordsman:29.93° / SwordShield:29.18° / HeavySwordsman:30.80°,25.62° / HalberdElite:30.26° / ApesStoneHandElite:39.39° / Yetuga:37.86°. 정상 캐릭터 전체 world ragdoll은 off이고 engine post-process가 보조 뼈317개의 수명/취소/EndPlay를 소유한다. 테스트 floor/camera/fixture와 검사 settings는 별도 owned process에서만 사용했고 map/asset 저장0, user/foreign editor 제어0이다.

수치/형상 출처: Human Adult17/Elite17/Halberd16 원작 anatomy capsule은 OriginalAnatomyShapes.json의 package/export field/raw Center·Rotation·Radius·Length/SHA다. 해당 reference bone에만 사용하고 source NoCollision policy는 몸 접촉 목적의 활성 collision으로 변경했다. 그 외 anatomy는 실제 LOD0 dominant skin AABB에서 계산했다. feel은 현재 Player_Original_Hair/Torso_RigidBody_PhysicsAsset의 player TEMP spring/damping/각도/몸 damping·반경·mass-per-length와24/4/4·1/60을 재사용한 것이다. source original physics 전체 동일값으로 기록하지 않는다.

일반19 post-process는 unit enemy ComponentSpace, Yetuga1은 WorldSpace다. Yetuga37 짧은 털의 source784/56·8/8/3도·0.1/1.5·0.5cm는 유지하고 hard angular bounds/exact solver/실제 dominant skin tip sphere를 사용했다. skin uniform-box + pivot parallel-axis virtual inertia와 어시스턴트 TEMP 배율2로 과한 뒤집힘을 줄였고 큰 cloth4는 기존 virtual inertia TEMP2를 적용했다. 근거/수식/원시 support와 각 저장 값은 위 final report의 sources 및 saved native report다. 원래 고정점에서 겹치는 anatomy proxy pairs는 분리하고 그 외 몸 접촉을 유지한다. PA editor의 DefaultInstance.InertiaTensorScale, constraints의 spring/damping/limits/collision을 조정 위치로 사용한다. 새 gameplay tuning literal/runtime settings owner는 추가하지 않았다.

PrivateFinalQA01 Yetuga cloth49.67° 실패는 geometry/숫자를 바꾸지 않고 QA를 느슨하게 통과시킨 것이 아니다. cloth 관성만 보완한 PrivateFinalQA02의 fresh saved/RHI/gameplay3검사와 Main 최종 검증으로 대체한다. 이전 broad nonlinear/alpha1/geometry/soft limit 및 도구 compile/link 실패는 보존했다. ParticleConstraints count0은 immediate-mode의 등록 경로 차이이므로 관절 미생성으로 확정하지 않는다. debugger session/agent breakpoint는 정리하고 user exception 상태는 유지했다.

필수 잔여0이다. 현재 gameplay6 family runtime 검증과 그 외 저장 library variants 설정을 구분한다. 전체 source-game physics parity/모든 skin 삼각형 관통0/network/shipping은 검증하지 않았다. 후속은 이 완료 → final evidence → 대상 PA의 설정만 표적 확인한다. full author/메타데이터 전수 추출/원본 재임포트/Player 전체 author/FPS/root/VFX 재실행·옛 DLL 전달은 하지 않는다. 앞선 Main 미반영/검증 대기 절은 이 완료로 대체한다.

<!-- MonsterSecondaryPhysics_20261013_main_complete -->
