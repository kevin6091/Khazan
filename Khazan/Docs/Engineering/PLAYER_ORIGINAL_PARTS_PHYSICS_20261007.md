# 2026-10-07 — BP_Player Original 파츠와 보조 물리

## 요청과 현재 적용 경계

사용자가 Torso/Shoes/Leg/Hair/Arm의 Original 버전과 해당 PhysicsAsset을 BP_Player에 직접 부착하고 머리카락·망토의 실제 움직임을 구현하도록 요청했다. 기존 에디터를 작업에 사용하지 않고 별도 프로세스로 검증한다. 신규 gameplay runtime class/manager/상태 사본은 추가하지 않는다.

작업 프로젝트: `C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan`. Source/Config/Plugins/Binaries는 독립 복사다. Content의 Player/Character 61파일도 독립 복사이며 나머지 21,118파일의 hardlink는 읽기 전용으로 취급하고 저장하지 않는다. 메인 Source/Config/Maps와 Imperial 메시/에셋은 전달 대상으로 삼지 않는다.

현재 정식 본체 경로는 `/Game/_Art/Player/Character/Meshs/SKM_Player`, Skeleton은 `SK_Player`다. Original 메시와 PhysicsAsset은 `Meshs/{Part}/Player_Original_{Part}` 및 `_PhysicsAsset`, 본체는 `Meshs/Player_PhysicsAsset`이다. 첫 snapshot과 메인 BP_Player/ABP_Player/6 PhysicsAsset의 SHA는 일치했다. 백업은 `Metadata/PlayerParts_20261007/Before`, 출처는 BeforeManifest.json이다.

## 엔진 책임과 검증 계획

파츠의 애니메이션 복사와 보조 물리는 엔진 CopyPoseFromMesh/RigidBody의 AnimGraph·각 SkeletalMeshComponent가 소유한다. LeaderPose follower는 독립 물리 평가를 하지 않으므로 그 방법으로 머리/망토 시뮬레이션 완료를 기록하지 않는다. Parent tick/scale/동일 본 매핑, animation-driven anchor와 secondary simulated body, PhysicsAsset shape/constraint·실제 최종 bone pose를 검증한다. Player의 Capsule/CMC/GAS·Montage/RootMotion 수명은 유지한다.

Original 이름의 기존 PhysicsAsset 사용과 원작 게임 물리 파라미터의 직접 확인은 별개다. 현행 geometry·ref pose·scale을 먼저 audit하며, 원작 수치가 없는 추가 튜닝은 임시 설정임을 명시한다. 전체 캐릭터 ragdoll을 기본 이동/전투에 켠 상태로 완료하지 않는다.

## 2026-10-07 — 착수와 격리 audit 준비

실제 적용은 아직 없다. 편집기 전용 helper/asset audit/mailbox와 독립 프로젝트만 준비했다. helper는 작업 Source에만 컴파일하고 제품 Build.cs에 editor 의존성을 넣지 않는다. ColdBuild_Author는 MaxParallelActions1로 실행 중이다.

첫 Python audit 요청은 PowerShell 문자열 wrapper 직렬화 때문에 실패했고 순수 .NET ReadAllText로 교정했다. `-ExecutePythonScript` 실행은 시작 스크립트 종료 뒤 자동 QUIT_EDITOR하므로 장기 mailbox 실행은 `-ExecCmds=py ...`로 교체해야 한다. 최초 PID15412는 정상 종료했다. 미처리 quit 요청003은 Archived로 이관해 재실행 직후 종료를 방지했다. 재실행 후 native audit→정확한 body/bone 선택→author→PIE/화면→저장 재로드/hash→메인 선택 전달 순서로 진행한다. 현재 사용자 메인 PID7220 및 Snow 작업 프로세스는 조작하지 않았다.

## 2026-10-07 — Original 5파츠 author 성공, 물리 품질 검사에서 스케일 문제 발견

별도 PID20820에서 `Khazan.PlayerParts.Author`가 11:47:49 KST에 성공했다. Torso 15바디 중 망토 6, Leg 32 중 옷자락/가죽/철장식 28, Hair 21 중 18을 Simulated로 구분하고 나머지는 Kinematic으로 지정했다. Shoes 5와 Arm 4는 animation-driven 바디다. Component는 Original PA, QueryOnly, main mesh 직접 자식, relative identity, 독립 CopyPose ABP를 사용한다. 본체 Player_PhysicsAsset 연결과 기존 Capsule/CMC/GAS/무기/ABP는 유지했다. 이때 메인에는 전달하지 않았다.

첫 WorldSpace PIE의 native test는 기존 assertion을 통과했지만 실제 화면과 bounds가 실패했다. Torso extent가 약 2.50e11cm까지 늘었고 Hair/Leg도 과도한 치수를 보여, `PIE_WorldSpace_FailedQuality.log` / `WorldSpace_FailedQuality.png`로 보존하고 **품질 실패**로 판정했다. 움직임이 있다는 assertion만으로 정상 물리로 기록하지 않는다. 후속 검사는 unit world bone scale, parent bounds에서 계산한 QA envelope, 실제 immediate actor geometry 크기를 포함한다.

Rider LLDB로 **작업 PID20820에만** attach했다. `PlayerPartsPIEEditor.cpp:97`, GameThread, `KZPlayerPartsPIE::FRun::Snapshot(false)`에서 Torso component scale `0.0099999997764825821`, component의 첫 query body scale 약 `0.99999986/0.99999998/0.99999986`을 직접 관측했다. 엔진 AnimGraphRuntime PDB가 없어 RigidBody.cpp:1206 breakpoint는 실행 코드 없음으로 미결합됐고 해당 엔진 frame/내부 값을 debugger로 확정하지 못했다. 그래서 로컬 UE 5.8 소스와 후속 native actor shape 관측으로 보완한다. 이 한계를 엔진 내부 debugger 확인으로 표현하지 않는다. agent breakpoint 2개를 제거하고 attach session을 STOP(detach)한 뒤 own mailbox012로 editor를 정상 종료, foreground throttle 원복했다. 기존 user exception breakpoint 8개는 보존했다(동일 opaque ID로 선택 변경 불가). 메인/다른 에디터는 제어하지 않았다.

엔진 `SkeletalMeshComponentPhysics.cpp:962–995,1094–1175` / `AnimNode_RigidBody.cpp:1159–1168`의 ref-pose 생성은 body getter에 mesh reference pose를 그대로 사용하며, WorldSpace component scale 인자는 constraint 생성에 적용된다. 따라서 imported wrapper100에 의해 RBAN shape가 커지는 조건과 실제 world pose(component.01 * wrapper100)의 크기 불일치를 수정한다. Original component PA의 geometry/constraints는 보존하고 Torso/Leg/Hair에 한해 `_RigidBody_PhysicsAsset` 사본에서 capsule center/radius/length와 joint Pos1/Pos2를 **1 / observed imported wrapper scale (=.01)**로 변환해 RBAN Override에 사용한다. 이 숫자는 원작 튜닝값이 아니라 현재 임포트·엔진 경로의 단위 변환이며, 재임포트/스켈레톤/메시 변경은 없다. 결과 검증 전 메인 전달은 계속 보류한다.

현재 helper 2파일의 보정/QA 강화본을 별도 프로젝트에서 ColdBuild_Author7로 빌드 중이다. 다음 절차: 성공 로그 확인 → own ExecCmds mailbox editor → Author 재실행 → 강화된 PlayerParts.PIE와 화면 → Guard/Heal → 저장 새 프로세스 재로드 → target hash 확인 → 승인된 에셋만 메인 전달. Scripts의 helper를 메인 Source/Build.cs에 넣거나 작업 DLL을 메인으로 복사하지 않는다.

## 2026-10-07 — 관절 보정만 유지하는 것으로 수정 / 앞선 형상 변환 폐기

ColdBuild_Author7는 QA helper의 deprecated `Chaos::ParticleHandle::Geometry()` 호출 경고를 포함했고 실제 own PID8480에서 `ParticleHandle.h:632`의 check(false)로 종료됐다. stack은 `PlayerPartsPIEEditor.cpp:139`였다. **검사 코드 오류**로 분리하고 `GetGeometry()`로 수정했다. 제품 Source/에셋 코드에 이 호출을 추가한 적은 없다. ColdBuild_Author8은 경고 없이 성공했다.

PID7976에서 저장 에셋 재로드 후 강화된 PlayerParts.PIE가 12:04:11 KST에 Success였고 캐릭터 bounds/복사 anchor/world bone unit scale/머리·망토·옷자락 pose 차이는 정상 범위였다. 그러나 직접 읽은 immediate actor geometry는 Torso Spine1이 `0.359/0.389/0.507cm`, Leg Pelvis가 `0.578/0.835/0.612cm`로 작았다. 앞선 **형상까지 .01 변환하는 가설은 폐기**한다. 이 결과는 `PIE_FrameAndShapeConversion_Rejected.log`에 보존했다.

정확한 경로는 `Engine/Private/PhysicsEngine/ImmediatePhysics/ImmediatePhysicsAdapters.cpp:CreateGeometry/MakeActorSetup/MakeJointSetup`이다. geometry는 BodySetup AggGeom과 unit actor transform에서 다시 생성하고 joint connector는 `GetRefFrame()`에 `GetLastKnownScale()`을 적용한다. 후속 derived PA는 **Original capsule/sphere/box·mass/damping·angular limits·collision table 모두 그대로 복제하고 DefaultInstance.Pos1/Pos2만 1 / imported wrapper100으로 변환**한다. 이는 컴포넌트에 사용할 원본 PA와 RBAN ref-pose joint 초기화의 공간 차이를 분리한 것이다. 숫자 단위 보정은 임포트/엔진 근거이며 원작 physics 튜닝값 확인이 아니다.

ColdBuild_Author9로 helper를 재빌드한다. QA는 각 actor geometry BoundingBox의 full extents와 동일 bone의 Original `AggGeom.CalcAABB(Identity).GetSize()`를 0.1cm QA 허용오차로 비교해 작아진 충돌체도 검출한다. Parent envelope 비율2, bone scale 허용오차 .001, angular difference .1deg 등은 검증 판정 기준이며 게임플레이/physics 튜닝으로 저장하지 않는다. 다음은 Author 재실행→최종 PIE·화면→Guard/Heal→stock main DLL 별도 프로세스 saved/runtime readback→hash 선택 전달이다. 메인은 아직 미수정이다.

## 2026-10-07 — 최종 구현·검증 완료 / 메인 파일 잠금으로 4패키지 전달 대기

**최종 구현**: BP_Player native CharacterMesh0 아래 Torso/Shoes/Leg/Hair/Arm, Original 메시·PA, relative identity, 독립 UAnimInstance ABP 5개다. Torso/Leg/Hair는 CopyPose→RigidBody(WorldSpace)→Output, Shoes/Arm은 CopyPose→Output이다. source Original 형상/관절 각도/감쇠/질량 설정은 보존했다. Torso 망토6, Leg 옷자락·장식28, Hair18의 총52 simulated body, 기타 anchor와 Arm/Shoes는 animated kinematic이다. 엔진의 파츠별 AnimInstance/ImmediatePhysics가 표현 수명과 EndPlay cleanup을 소유하고 ASC/Ability/Tag/CMC/Montage ownership은 바꾸지 않았다. 메시·Skeleton·본체 ABP·본체 PA·Imperial·Source/Config/Maps는 전달 대상이 아니다. 기존 무기 두 SCS, socket/scale, Heal 수납/발도 경로는 보존했다.

**관절 단위 계약**: `_RigidBody_PhysicsAsset` 3개는 현재 Original PA의 동일 형상/유형/설정을 복제하며 `ConstraintSetup[*].DefaultInstance.Pos1/Pos2`만 ref root scale100의 역수(.01)로 변환한다. Engine ImmediatePhysicsAdapters geometry는 unit actor scale에서 생성하므로 geometry를 .01로 줄이는 앞선 안은 폐기됐다. 최종 native actor Spine1의 full dimensions `35.872/38.922/50.725cm`과 전체 actor의 shape AABB가 source Original과 QA 0.1cm 내 일치했다. 현재 import/root100와 component.01 조건에 대한 엔진 공간 보정이며 원작 physics 수치 직접 확인이나 새 임시 tuning이 아니다.

**실제 검증**: ColdBuild_Author9 성공(67.29s). 작업 PID13368의 Author 12:10:50 / PlayerParts.PIE 12:11:35 / Guard.PIE 12:13:18 KST Success. 최종 bone finite, unit world scale, source pose anchor 0.1cm 내, 부모 bounds 기반 envelope, Original collider dimensions 비교, idle/이동/방향 전환/정지에서 보조 pose 차이를 검사했다. idle bypass 대비 첫 physics sample은 Torso64.819641°/Leg44.421165°/Hair35.016949°였고 Torso bounds extent41.392/52.919/87.863cm로 정상 범위였다. 이 각도는 QA 관측값으로 gameplay limit가 아니다. 실제 Original_Idle/Moving PNG를 확인했고 초기 거대 변형이 없어졌다. 제품 C++ 파일은 새로 추가하거나 수정하지 않았다.

**Heal 범위**: rendered 검사2회에서는 FPS 지연과 고정 checkpoint 조건에서 각각 Armed 현재 montage/instance, 자연 종료 checkpoint가 실패했다. 두 로그를 삭제하지 않았다. 재시도에서는 Arms 양손 포즈 및 하체·몸통 Walk 원본 pose 오차0이 관측됐으나 종료 항목1개가 실패했다. 제품 timing/Ability/테스트 assertion은 바꾸지 않았다. 작업 DLL을 제거하고 현재 main DLL과 동일 SHA의 stock DLL로 별도 PID17564/NullRHI에서 동일 Heal 전체 검사가 12:22:18 KST Success였다. saved/runtime readback은 12:24:58 KST Success로 main body+Original5 mesh/PA/ABP/parent/scale/worldSimulationFalse를 실제 PIE에서 확인했다. stock binary SHA는 StockBinary.json, 기록은 Heal_Stock_NullRHI_Success.log / Stock_RuntimeReadback.json이다. rendered 연속/hardware QA와 원작 physics 일치 검증은 완료로 표현하지 않는다.

**전달 상태**: 검증 결과/각 SHA는 Verification.json / DeliveryManifest.json에 있다. 14개 중 신규 ABP5+derived PA3+Shoes/Arm Original PA2의 **10개만 메인에 전달·SHA 검증 완료**. BP_Player와 Torso/Leg/Hair Original PA 3개는 Windows file lock 때문에 아직 before SHA다. 따라서 **현재 main BP_Player에는 아직 5파츠가 적용됐다고 말하지 않는다**. 각 pending .uasset.playerparts_pending 파일은 검증된 prepared SHA와 일치한다. 마지막 BP_Player를 dependencies 뒤에 전달하는 방식이다.

**정확한 차단 증거·재개**: Windows Restart Manager read-only inquiry로 해당 lock owner는 사용자 main UnrealEditor PID7220, `/Khazan/Khazan/Khazan.uproject -skipcompile`임을 확인(FileLocks.json). ReadWrite open과 atomic replace 모두 실패했고 ACL/ReadOnly는 정상이다. 메인 프로세스나 다른 작업 에디터를 종료·제어하지 않았다. own PID17564는 mailbox031로 정상 종료/throttle restore 완료했다. 사용자에게 저장 후 main 종료를 요청한 상태다. main 종료 후 아래 명령 한 번으로 journal의 이미 전달된 SHA를 보존하고 남은4개만 전달한다. 어느 main hash든 before/prepared와 다르면 concurrent 변경으로 중단하므로 사용자 저장 내역을 덮어쓰지 않는다. 그 경우 최신 BP를 work에 독립 복사하고 기존 Graph/설정을 유지해 SCS 파츠만 다시 추가해 검증/새 baseline을 만든다.

`& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' 'Scripts/Engineering/deliver_player_original_parts.py'`

반환 complete=true, 14/14 delivered digest 확인 후 현재 문서/ENGINEERING_PROJECT_STATE/PHYSICS_DIAGNOSTICS/CONTINUITY에 **실제 전달 완료**를 추가한다. 현재 Source/Config/Maps나 helper DLL을 복사하지 않는다. 작업 프로젝트는 재현/인수인계를 위해 보존했다.

## 2026-10-07 — Main 통합 완료와 새 메인 에디터 로드 확인

사용자의 Main 반영 요청에 따라 전달 대기를 해소했다. `DeliveryManifest.json`은 05:25:55 UTC에 complete=true이며, 최종 확인에서 **14/14 메인 파일이 검증된 작업본 SHA와 일치**했다. 앞선 10/14·잠금4개 기록은 당시 상태다. `MainIntegrationPreflight.json`의 메인 PID26644는 DevMap/PIE 없음/dirty0이었고, 기존 메인 로그의 정상 종료 후 새 메인 PID8292가 DevMap을 열었다.

메인 read-only 확인은 `MainReadyAudit.json`이다. BP_Player와 본체/파츠 ABP 6개가 모두 BS_UP_TO_DATE이며 Original Torso/Shoes/Leg/Hair/Arm 메시·PhysicsAsset·ABP 연결을 확인했다. 각 파츠의 SCS 부모는 CharacterMesh0, 상대 scale은 identity다. 본체 SKM_Player/ABP_Player/Player_PhysicsAsset와 기존 .01 배율은 유지됐다. SCS template의 GetAttachParent가 null인 것은 실제 인스턴스 attachment 관측이 아니므로 SubobjectData의 parent handle로 저장 계층을 검증했다.

`FinalMainHashVerification.json`: 14 prepared SHA 일치, 통합 전 보호한 95파일(Source84/Config5/uproject1/DevMap·본체ABP·본체PA3/Binaries2) 전부 unchanged. 새 제품 C++ 수정·DLL 교체·재빌드는 없다. 첨부 PlayerPartsPIEEditor.cpp는 격리 검증용이며 표현 기능은 전달된 BP/ABP/PA가 소유한다. 기존 몬스터·눈 기능의 Source/프로젝트 설정을 유지했다.

이번 검증은 메인 저장 에셋의 새 프로세스 로드·구성·compile status·SHA다. 앞선 격리 native physics/Guard/stock Heal/stock runtime readback Success를 재사용하며 이번에 새 PIE를 수행했다고 기록하지 않는다. 마지막 메인은 PIE 없음/dirty content·map0으로 사용자 직접 Play 가능하다. 다음은 DevMap Play에서 이동·회피·가드·Heal에 따른 머리/망토/옷자락의 연속 화면 확인이다. 원작 물리 수치 일치 및 hardware 연속 QA는 기존 미확인 범위를 유지한다.

## 2026-10-07 — 사용자 후속 요청으로 메인 반영 완료

- 사용자 최신 요청 “작업한 내용을 Main에디터에 반영해줘”에 따라 최종 통합을 진행했다. 기존 lock PID7220는 이미 종료됐고 현재 main PID26644였다. DevMap/PIE Idle/dirty0를 read-only로 확인하고 QUIT_EDITOR 직전에 다시 identity·dirty·game world를 확인한 뒤 정상 종료했다. 강제 종료/SaveAll/사용자 dirty 폐기는 없었다.
- Before/prepared SHA와 현재 메인 14개 파일이 모두 일치했다. guarded delivery 재개로 남은 BP_Player·Torso/Leg/Hair Original PhysicsAsset 4개를 실제 반영했다. DeliveryManifest.complete=true, 14/14 target SHA=prepared를 확인했다. 이전 “10개 반영/4개 잠금 대기”는 이번 실제 완료로 해소됐다.
- 최신 main Source/Config/uproject/DevMap/본체 ABP·PhysicsAsset/현재 modules 및 module DLL을 포함한 95파일은 통합 전후와 재로드 후 SHA를 비교해 보존했다. 격리 helper C++/Build.cs/DLL을 메인에 전달하지 않았다. Snow/Monster의 최신 변경과 현재 alias DLL을 사용해 그대로 재시작했다.
- 새 사용자용 main PID8292는 DevMap으로 정상 로드됐다. MainReadyAudit.json은 Original Torso/Shoes/Leg/Hair/Arm의 실제 저장 SCS template, CharacterMesh0 parent, Original mesh/PA/ABP, relative scale1, QueryOnly/no world simulation, 본체 Player_PhysicsAsset 및 기존 무기2개를 확인했다. BP_Player+파츠 ABP5가 모두 BS_UP_TO_DATE, dirty0, game world 없음이다. main에서 자동 PIE/actor spawn/compile/save는 하지 않았다.
- 검증 구분: 보조 physics/실제 bone·collider·bounds/이동·Guard·Heal은 앞선 별도 프로세스 실제 PIE 증거다. 이번 턴은 메인 파일 전달·새 프로세스 저장본 재로드 확인이며 새 main gameplay PIE 성공으로 기록하지 않는다. 사용자에게 열린 DevMap Play로 바로 확인 가능한 상태다. 원작 physics 수치 동일성·장시간 hardware QA는 기존 미검증 상태다.
- 근거: Metadata/PlayerParts_20261007/{MainIntegrationPreflight,MainIntegrationProtectedBefore,MainIntegrationResult,MainReadyAudit,DeliveryManifest}.json, Saved/Logs/PlayerPartsMainReadyEditor.log, Saved/Screenshots/WindowsEditor/RiderMCP/20261007-052906_editor_window.png. shared log의 05:27:09 Python inspection AssertionError ('Torso', [])는 발생 스크립트 출처를 확정하지 않고 보존했다. 최종 guarded MainReadyAudit은 모든 파츠/6 BP 검사를 통과했으며 Blueprint/Linker/Class/AnimBlueprint load 오류·ensure/fatal/unknown property는 없었다. 자동 통합/전달 pending은 없다.

## 2026-10-07 — 몸 충돌과 소폭 감쇠 조정 최종 완료

사용자가 실제 보조 물리는 정상임을 확인한 뒤 몸 관통 및 물처럼 흐물거리는 느낌을 줄이도록 직접 요청했다. 이번 변경은 **BP_Player ConstructionScript + 기존 Torso/Leg/Hair ABP3 + derived RigidBody PA3, 총7패키지**다. 제품 C++/새 runtime class/component/manager/메시·Skeleton/본체PA/Original source PA/Imperial/Locomotion·GAS·Ability·Event·Tag는 수정하지 않았다. 표현·수명·cleanup은 기존 SkeletalMeshComponent/CopyPose/RigidBody/ImmediatePhysics가 소유한다.

### 원인과 최종 데이터 계약

- CollisionAudit은 Torso15/Leg32/Hair21의 모든 내부 collision pairs105/496/210이 disabled임을 확인했다. 파츠 ref skeleton에는 본체의 일부 해부학적 뼈가 없어 local PA에 모든 몸 충돌체를 추가하는 방식은 부적합하다. BP_Player 생성 시 actual Mesh와 Player_PhysicsAsset을 각 Torso/Leg/Hair의 **AddClothCollisionSource**에 등록하고 해당 ABP RigidBody의 bUseExternalClothCollision=true/WorldSpace를 사용한다. 기존 ConstructionScript 실행 링크를 유지했다. 엔진의 weak source·delegate·tick prerequisite·cache/EndPlay 정리와 중복 등록 방지를 재사용한다.
- native 실제 PIE에서 **각 part18개, 총54 external kinematic colliders**가 부모의 현재18몸뼈를 정확히 따라가는 것을 확인했다(pose error0cm, source shape cm 크기 일치). 모든 internal pairs는 그대로 disabled이며 실제 몸은 외부 colliders와 충돌한다. 원래 main/Original PA와 파츠 component QueryOnly/no ragdoll 설정을 유지한다.
- 자동 맞춤 옷 캡슐은 radius10~27cm라 단순 collision 활성화는 옷을 부풀게 한다. 처음 시도한 original mass-only/NoCollision 형상 + 얇은 nonmass 형상은 **폐기**했다. UE5.8 ImmediatePhysicsActorHandle_Chaos.cpp의 CreateParticleHandle가 ActorSetup.Shapes를 버리고 모든 새 shape의 bSimCollision=1을 켜므로 mass-only 형상도 다시 충돌한다. 숫자 테스트의 Success와 초기 화면 품질 실패를 구분해 로그·PNG를 보존했다.
- 최종은 simulated52바디 각각 **얇은 capsule1개**다. center/rotation/length와 기존 joint/각도 제한/drive를 보존하고 radius만 cloth1cm/hair0.75cm로 설정했다. 원래 unit actor mass/CoM/body-axis inertia diagonal을 engine MakeDynamicActorSetup으로 계산해 derived DefaultInstance의 mass override/InertiaTensorScale로 복원했다. 52개 모두 mass 상대오차0.0001, inertia diagonal 상대오차0.001, CoM0.001cm QA 기준을 통과했다. 기존 geometry mass를 활용한 **현행 임포트/engine 계산값**이며 원작 게임 metadata 직접 확인값이 아니다. 전체 off-diagonal tensor/고유축 동일성은 검증하지 않았다.
- InertiaTensorScale은 inertia의 단순 배수가 아니다(ScaleInertia(true), uniform S의 효과 S^5). body축 I에서 q_i=(trace(I_old)/2-I_old,i)/(trace(I_thin)/2-I_thin,i), detS=(qX*qY*qZ)^(1/5), S_i=sqrt(q_i/detS)로 주대각을 복원했다. 단위: mass kg, inertia kg·cm², CoM cm, scale 무차원. bone별 계산값·출처·판정은 BodyCollisionTuning/CalculatedMassInertia.json에 있다. ref wrapper100/component.01의 기존 joint Pos1/Pos2 변환은 재적용하지 않았다.

### 수치 출처와 느낌 조정

Engineering 정본/저장 metadata 및 Desktop 카잔의 Player 모델·Exports를 표적 확인했으나 **원작 Player PhysicsAsset/감쇠·cloth 설정 export는 찾지 못했다**. 확인한 저장 자료 범위의 결과이며 원작 게임에 해당 수치가 없다는 뜻이 아니다. Original 이름의 imported PA나 engine 기본값을 원작 검증값으로 표시하지 않는다.

**어시스턴트가 선택한 임시 튜닝값**: derived SkeletalBodySetups[simulated bone].DefaultInstance.LinearDamping0.01→0.05, AngularDamping0→0.35(s^-1); AggGeom.SphylElems[0].Radius cloth1cm/hair0.75cm. 목적은 약간의 속도 감쇠와 과하게 두꺼운 접촉 방지다. 무게·각도 제한·gravity/spring drive를 새 튜닝으로 강화하지 않는다. 차후 느낌 조정은 먼저 derived PA의 damping만 작은 범위에서 비교하며, 새로운 원작 export가 확보되면 같은 bone/property/버전/단위/조건을 대조한다. helper const와 TuningProvenance.json에 임시 출처를 명시했다.

### 실제 검증과 메인 적용

- Baseline06:24:19 UTC는 Hair/Torso/Leg contact0/impulse0을 기록했다. 기존 부풀음 안은 접촉 성공이어도 화면 실패로 보존했다. SingleThin author06:42:47, PlayerParts.PIE06:44:13, Guard06:48:44, Heal06:51:41 UTC 모두 Success. 최종 실제 contact manifold points는 Hair4537/Torso613/Leg3320, impulses는 모두 양수다. representative mass는 이전과 동일한 Hair1.645364/Torso12.054688/Leg5.860874kg이며 runtime damping.05/.35를 확인했다. shape1/finite pose/bounds/anchor/18body geometry와 현재 pose, idle/방향 이동/정지/Guard/Heal을 검사했다. contact 수치는 해당 검사 프레임 누적이며 모든 경우의 정점 관통0을 뜻하지 않는다.
- Thin_Idle/Moving과 Stock_Back PNG를 직접 확인했다. 최신 main module SHA2F27C046480AEB7C328B79CD3268DC6C8FC07659ED4B4FB4D8773D296183773E를 **work에만** 복사한 stock own29184의 saved/runtime readback07:05:24 UTC Success: candidate7 SHA, Original5 실제 components, no world ragdoll, Torso12/Leg59/Hair72 전용 뼈의 finite actual pose 확인. 첫 parent 비교는 본체에 없는 part 전용 뼈를 비교한 검사 오류여서050실패를 보존하고 실제 part pose 검사로 교정했다. 모든 own editor는 normal quit/throttle true 원복했다.
- 다른 작업이 main module/프로세스를 갱신했으므로 최신 PID/동일DLL을 다시 확인했다. main28172의 root/DevMap/PIE 없음/dirty0/7before SHA를 QUIT 직전에 검증하고 **정상 종료**했다. 7/7 guarded atomic delivery complete=true 뒤 main19684를 사용자용 DevMap으로 다시 열었다. force quit/SaveAll/workDLL·Source 전달/main 자동PIE는 수행하지 않았다.
- MainReadyAudit: BP_Player/본체ABP/partABP5 총7 BP UP_TO_DATE; Original5 mesh/원래PA/ABP/SCS parent CharacterMesh0 확인, main read-only RigidBody3 export는 WorldSpace/derived PA/bUseExternalClothCollision=True. 모든 target7 SHA=prepared, **보호155(Source/Config/uproject/DevMap/본체ABP·PA/비대상 Player content/current module) unchanged**다. 마지막 main read-only 상태는 game world 없음/dirty0이며 최종 main gameplay PIE를 새로 성공했다고 주장하지 않는다. 일시적인 공유 로그의 검사 None override 오류는 mesh default PA fallback/GetAssociatedObject로 교정했고 저장 변경은 없었다.

최종 근거는 Metadata/PlayerParts_20261007/BodyCollisionTuning/{DeliveryManifest,Verification,MainReadyAudit,FinalMainHashVerification,TuningProvenance,CalculatedMassInertia}.json 및 실제 native/stock logs·PNG다. 이전 PlayerParts 전체14 전달 journal은 당시 이력이며 이7 수정의 최신 정본은 BodyCollisionTuning이다. **미검증**: 원작 물리 수치 동일성, 모든 mesh 정점/모든 전투 pose/모든 LOD/장시간 hardware 연속 QA. 현재 요청 범위의 몸 collider 접촉·소폭 damping·메인 적용은 완료했다.


## 2026-10-07 ? Hair? ???? ?? ????? ??? ?? ??

??? ?? ??? ?? ? ????? ???? ??? ?? ??? ?? ???? ????? ????. **?? ?? ??? ?? Hair derived RigidBody PhysicsAsset ? ???**?: `/Game/_Art/Player/Character/Meshs/Hair/Player_Original_Hair_RigidBody_PhysicsAsset`. ???Skeleton????Original source PA?BP/ABP??? ???GAS/Ability/Event/Tag/Locomotion??? C++? ???? ???. ?? runtime ??0?? ?? ABP RigidBody/ImmediatePhysics/CopyPose? ??? cleanup? ?? ????. ??? ????/??? ?? ?? ???? ???? ???.

### ?? ??? ??

- native imported LOD0 skin-weight audit?? Hair_69? ?? ?? ?? ??? ??? ????. ??18 simulated body? ? ?? ? ??? ?? ?? ???? **????14?/65 weighted bone ?? simulated body**? ????. Head/Hair_BoneRoot/Hair_BoneRoot_002 ? anchor? Kinematic: derived ?68??/65????.
- ?? ? `Hair_LL4_001/002`, `Hair_RR4_001/002`? ???? ??? CopyPose? ???. ?4?? ?? ??? ?? ???? ?? lock??? ? capsule? ??? ??????? ?? ?? ? ?? ?? ? ????. ?? stock readback?? ??4?? ?? current pose? ??/?? ??? QA0.1cm/0.1deg ??? ????.
- ? simulated body? bone??? child pivot ??? ?? capsule ???. ??=segment/2, ?? ??=?? ???2radius. terminal? end marker? ??? ?? ?? ?? ??? ???? ??? ??? ????. internal pairs? ?? disabled, ?? actual parent Mesh/Player_PhysicsAsset? external18 ? collider? ????. Body collision source/BP/ABP ??? ??.
- ? ??? ref-pose parent/child pivot? ???? ????. ? connector translation? unit reference translation/wrapper100?? ????. ?? .01 ??? ?? ????? ???. `UPhysicsConstraintTemplate::SetDefaultProfile`? ??? PIE? ??? ?? ?? default profile? drive/limit? ????.

### ?? ??? ?? ??

?? ?? ?? ?? BodyCollisionTuning? ?? ?? ?? ???? ????? ? ?? export? ???? ???. ?? Original? imported PA? ?? physics ?? ????? ???? ???. ??? **????? ?? ??**?? ?? derived PA? body DefaultInstance/constraint DefaultProfile? ????. ?? author? ? ?? ??? `Metadata/PlayerParts_20261007/HairRefinement/TemporaryTuning.ini`, ?? body ??? `AppliedPerBone_InertiaConditioned.txt`, ??? `TuningProvenance.json`??.

| ?? ??/?? | ?? ???/?? | ????? |
| --- | --- | --- |
| AggGeom.SphylElems[0].Radius | 0.5cm | ?? ?? proxy, ?? ??? ?? |
| DefaultInstance mass override | 0.002kg/cm ? imported segment length; total1.820300kg | ?? ?? fit? ? ??? ?? ?? ??? ?? ?? |
| LinearDamping | 0.1s^-1 | ?? ?? ?? |
| AngularDamping | root1.5?tip0.8s^-1 | ?? ??/?? ?? ?? ?? |
| Swing1/2 limited angle | root8?tip18deg | ? ?? ??? ?? |
| Twist limited angle | root3?tip6deg | ? ??? ?? |
| SLERP orientation/velocity acceleration drive | omega root28?tip10s^-1; k=omega?=784?100, c=2omega=56?20 | ?? ?? ??? ?? ?? ??; ?? assistant ?? ?? |
| InertiaTensorScale | thin capsule? ?? principal inertia? body ?? ??? ??? ?? | ?? ??? ?? axial inertia? ?? ?? spin/flip ??; kg?cm?/scale ??? |

depth ?? t=(depth?1)/(chain body count?1)??. virtual inertia ??? assistant ?? ?? ???? ?? ??? ?? ?? shape/mass ?? ????. q_i=(targetI/2)/(trace(I_thin)/2?I_thin,i), detS=(qXqYqZ)^(1/5), S_i=sqrt(q_i/detS)? ????. ?? ?? ??/??? ????. ?? off-diagonal tensor/??? isotropy ?? assertion? ???? ????, ?? ??? ?? ?????? ??? ????. ?? source PA/?? PA mass/cloth ??? ??? ???.

### ?? ??? ?? ??

- ?? PA baseline PIE07:45:46 UTC Success: independently responding joints18, tip RMS8.810660cm/peak25.207770cm, local bend RMS20.046051deg/peak55.571588deg.
- ?69 body ?? contact?finite ??? ????? ? local rotation? ?? **?? ??**??. ??? ? constraint DefaultProfile ????? PIE? save? ?? limit/drive? ???? ?? author ??? ?? ?? ???? ??? ????. ?? ?? ?4??? Head overlap ? thin inertia ???? ?? ??? flip? ?? ???? ?? ?? CopyPose ??/virtual inertia conditioning?? ????. ?? ???PNG?candidate history? ???? ???.
- **?? ? ???? ??? native PIE08:22:49 UTC Success**: same control rotation/?? ????? ???release/stop; responding joints65, tip RMS7.200052cm/peak16.502579cm(?18.3%/34.5% ??), local bend RMS8.601447deg/peak27.974185deg. finite/unit world scale/character envelope/shape one/18 external collider current pose?geometry ? anchor QA ??. ?? local flip35deg? QA ???? ?? ????? ???. ?? contact points Hair11773/Torso652/Leg3298 ? ?? impulses? ????. contact ??? ?? ??? ???? ?? ?? ??0? ??? ???.
- `SavedProfileAudit.log`: ?? ???65??? limits8?18/3?6, orientation?velocity drive enabled, spring/damping? ?? readback??. close view? camera arm? ?? ??/cleanup, ?? control rotation/??? ????. Final_Idle/Moving PNG? ?? ????. ?? camera probe? control rotation?? ?? ??? ?? ??? ?? ???.
- ?? ??? ? module alias? ?????? ?? main stock `UnrealEditor-KhazanSnowDeep20261007.dll`, SHA5AE3FEA4667F3AE8B652100BD85909DD97EF2680B95545CD914FF724DAE84E77? **work??** ????. own1516 Guard08:27:11/Heal08:29:12 UTC Success; stock readback08:30:09 UTC? Original5 actual components/no ragdoll/Hair72 finite poses/face lock4 copied pose/candidate1 SHA? ????. own normal quit/foreground throttle true ?? ??. helper binary? work Saved/PlayerHairHelperBinary?? ????.

### ?? ??? ?? ??

?? Main19684? Rider ?? ??? disconnected?? PID/project? target before SHA? ??? ? OS? **?? ? ?? ??**? ????. ?? ??/SaveAll/Save?Discard ?? ??? ???. Main? ?? Exiting/log closed08:31:48 UTC ? process ??? ??? ? 1PA guarded atomic delivery complete=true? ????. pre-exit PIE/dirty0? ?? ????? ???? ???. target before/prepared CAS? user dirty? ??? ???? ?? ?? ??? ????.

? Main21248? ?? alias DLL/DevMap?? ?? ????. ? read-only audit? ??? endswith ??? `<BlueprintStatus.BS_UP_TO_DATE:3>` ?? ??? ?????? ?? report? ???? enum ?? ??? ????(??/compile ?? ??). ???? Rider? guarded read-only audit? **??7 BP UP_TO_DATE/Original5 stored part connection/parent CharacterMesh0/candidate SHA/PIE ??/dirty0**? ????. main ?? PIE/compile/save? ??. ?? module/Source/Config/DevMap/??? Player content161??? integration ?? ?? ?? unchanged. ?? ? ?? ???4??? ?? ConcurrentChangesBeforeIntegration.json? ????. work helper DLL/Source/Build.cs? Main? ???? ???.

??: HairRefinement/{Verification,DeliveryManifest,MainReadyAudit,FinalMainHashVerification,TuningProvenance}.json ? ? ?? native/stock log/PNG. ?? ???????? ?? ???? pending0??. ?? physics ??/?? ??????LOD???? hardware ??? ?????. ?? ?? ??? ? **Hair PA?** ????? ?? Root support/Tip freedom/drive damping? ?? ???? ????. full author/?? body tuning/?? Original parts ??? ???? ???.


## 2026-10-07 23:36 KST — Hair 기준 Torso·Leg 천 반응 조정 및 Main 반영 완료

Original Torso/Leg의 기존 derived RigidBody PhysicsAsset 두 개를 조정했다. Hair·Shoes·Arm·본체 `Player_PhysicsAsset`·BP/ABP·Main runtime Source/DLL은 보존했다. Shoes/Arm에는 별도 secondary cloth 체인이 없다. 기존 CopyPose/RigidBody와 본체의 외부 충돌체 18개를 계속 사용하며 새 runtime 클래스는 없다.

### 적용 계약과 수치 근거

원작 physics export의 해당 값은 미확인이다. `Metadata/PlayerParts_20261007/ClothRefinement/TemporaryTuning.ini`는 어시스턴트 임시값의 정본이며 `TuningProvenance.json`, `AppliedPerBone.txt`에 property·단위·계산·검증을 기록했다. Original이라는 에셋 이름은 원작 물리값 확인을 뜻하지 않는다.

- 기본 `Swing1/2Limit` root→tip 8.8→19.8deg, twist3.3→6.6deg, SLERP 복원 omega25.454545→9.090909s^-1, angular damping1.35→.72s^-1, linear damping.1s^-1. Hair의 현재 설정 대비 기본 각도×1.1, omega÷1.1, 감쇠×.9다. 세계공간 변위10%를 보장하는 관계는 아니다. **Leg의 새 simulated Depth0 관절만 swing32deg**를 사용해 몸 접촉 회피 여유를 확보했다. 하위 보간·twist·복원 강도는 그대로이며32deg도 어시스턴트 임시값이다.
- `DefaultInstance` 질량은 실측 contact segment LengthCm×.003kg/cm, 최소 반경/박스 두께 기준은1cm/2cm다. Leg contact box는 실제 imported LOD0 dominant skin-weight 정점의 bone-local 전체 범위를 덮는다. segment X 및 transverse weighted covariance의 주축Y, Z=X×Y에서 X/Z=max(2Radius, Max−Min), Y=Max−Min, center는 각 축 min/max 중점이다. 충분한 폭/소유 정점이 없으면 capsule fallback을 사용한다. 이 geometry는 원작 직접값이 아닌 현재 imported mesh의 계산 결과다.
- imported `RefSkeleton` wrapper100을 unit-cm 형상과 connector에 중복 적용하지 않는다. 새 parent connector의 저장 translation만 unit offset/100이며 현행 런타임 배율을 유지했다. source ref-body Phi≤contact radius 또는 unweighted/coincident root 보호는 animation-driven anchor로 둔다. 추가 이름 기반 Leg pin은 비어 있다. Torso21body(8 cloth sim), Leg63body(30 cloth sim+기존 Iron2)이며 보호 anchor를 유지한다.
- SLERP acceleration drive의 저장 spring=omega², damping=2omega, orientation identity/velocity zero, hard cone/twist, `SetDefaultProfile` 동기화다. 엔진 drive 배율의 영향과 원작값은 구분한다.
- 관성은 선택된 contact geometry와 질량에서 실제 `FActorSetup.Inertia` principal moments I를 계산한다. target=max(I)×m, m=Torso1/Leg4; uniform scale s=(target/min(I))^(1/5)를 `DefaultInstance.InertiaTensorScale=(s,s,s)`에 저장했다. UE5.8 `ImmediatePhysicsAdapters.cpp`의 `bInertaScaleIncludeMass=true` 및 `BodyUtils.cpp`/Chaos `Utilities.h::ScaleInertia`에 따라 **전체 tensor가s^5배**, eigenvalue 비율은 보존된다. isotropic tensor가 아니다. 저장 후 fresh actor로 최소 principal moment·질량·CoM을 검증했다. 기존 body-axis diagonal만 같게 하는 정책은 작은 principal moment를 막지 못해 사용하지 않았다.
- PA `SolverSettings`: fixed step1/60s, position24/velocity4/projection4, Torso linear/Leg nonlinear, `ParentDominates=false`, angular projection alpha.8. Leg solver는 보존된 Iron2에도 적용되므로 입력 보존을 동작 불변 보장으로 확대하지 않는다. 원작 solver값이 아닌 임시 안정화 값이다.

### 실제 검증

아래 각도는 실제 saved Bone1/Bone2 connector의 world 상대 quaternion 각도이며 kinematic CopyPose/Iron은 제외한다. 기준과 최종의 sim 집합은 Torso6→8/Leg26→30으로 달라 같은 정점·관절 집합의 통제 실험으로 과장하지 않는다.

| 조건 | Torso RMS/peak deg | Leg RMS/peak deg | Hair RMS/peak deg |
| --- | --- | --- | --- |
| 변경 전 fixed30 | 39.288148 /82.928390 | 46.299694 /129.865832 | 8.687415 /31.588255 |
| 최종 fixed30 PASS | 3.764723 /11.961719 | 15.330120 /32.207126 | 8.687415 /31.588255 |
| 저장 후 fresh process, 일반 시간 간격 PASS | 3.490849 /8.542873 | 15.214920 /32.211325 | 8.720381 /27.288118 |

`PIE_Before_Fixed30.log`, `PIE_FinalSaved_Success.log`의14:17:53 UTC Root32 block, `PIE_FinalSaved_NormalDelta_Success.log`를 사용했다. 일반 시간 간격은 PID15472/NullRHI/cap60/UseFixedTimeStep 없음이다. Hair65 관절의 fixed30 측정과 에셋 SHA는 정확히 동일하다. Root24 등 이전 block과 최종 block을 구분한다. `Final_Front_Idle.png`/`Final_Front_Moving.png`는 별도 에디터의 실제 화면이다.

메인 실제 loaded Normal DLL(A95C215679067B88F14A7BFCB8B9A7864B0C765926E917F0AB16F4D4D75F5BB2)을 Work PID13600에 사용했다. Stock Guard(14:24:49 UTC)·Heal(14:27:35 UTC) PASS. 별도 일반 PIE의 `Stock_RuntimeReadback.json`에서 Original5/부착 부모/ABP/비래그돌/단위 scale, secondary bone Torso12·Leg59·Hair72의 finite pose, PA2 SHA 및 Hair 불변을 확인했다.

Main PID3528에서 PA2만 fully_load_packages→CAS 교체→ASSUME_NEGATIVE reload(True, empty error)했다. `MainSelectiveHandoff.json`/`MainReadyAudit.json`에 HeinMach world·actor 집합·선택·dirty0·noPIE·보호161파일·기존 loaded DLL 및 최신 Snow disk alias 보존을 기록했다. BP7 up-to-date/Original5와 실제 loaded PA solver24/4/4를 읽었다. `skeletal_body_setups`는 설치된 Python API에 노출되지 않아 Main body-array 직접 검사는 하지 못했다. 해당 body/형상 검증은 별도 native 테스트와 Main 전달 SHA 일치 근거로 구분한다. Main 종료·PIE·SaveAll·C++ 재빌드는 수행하지 않았다. `Verification.json`의 final MainIntegrated가 이전 pending trial 기록을 대체한다.

### 남은 관통 범위와 후속 확인

본체 implicit collision proxy 대 LOD0 linear-skinned 정점을 세 pose에서 측정했다. Torso867 정점은 inside0, Leg dominant3835 정점은 inside111/390/350, minPhi−7.724334/−9.641862/−8.041948cm다. Leg에는 **잔여 proxy overlap이 남아 있다**. 일부 worst 정점은 대부분 kinematic attachment가 소유하며 직접 sim 가중치가 작다. ref pose의 dominant inside4/all-positive56도 함께 기록해 원래 형상과 동적 overlap을 구분했다. 피부 triangle 자체와 proxy는 다르며 전체 정점/triangle 내부/morph/WPO/다른 LOD/공격·회피·장시간 및 continuous sweep의 관통0을 증명하지 않았다. raw baseline/final 정점 집합도 다르다. cached manifold `InitialPhi=0`/현재 plane gap/접촉0을 실제 skin 관통0으로 해석하지 않는다.

후속 조정은 이 저장본과 `Verification.json`·`AppliedPerBone.txt`에서 시작한다. 사용자가 관측한 실제 pose/위치를 좁힌 뒤 attachment skin weight·원본 애니메이션·몸 proxy의 영향과 물리 joint를 구분한다. Hair나 본체를 일괄 변경하지 않으며, 에셋 변경 시 별도 에디터에서 saved/일반 시간 간격 검증과 manifest binding을 갱신한다.


<!-- HeinMachGhosting_20261008_applied -->
## 2026-10-08 — HeinMach 이동 캐릭터 선명도·잔상 수정

HeinMach 잔상 수정에서 BP_Player의 Original5/weapon2 render mask만 기존 body의 True/254에 맞췄다. Independent CopyPose/RigidBody·PA2·tick·scale·skeletal velocity는 바꾸지 않았다. mesh·ABP·PhysicsAsset override·transform 비교와 fresh saved audit는 Saved/ImportReports/HeinMachGhosting_20261008/Parts에 있다. physics tuning 결과를 shader ghosting 완전 해결의 근거로 사용하지 않는다. Main 선택 전달·Config·fresh actual-input 검증은 SOURCE_BP_CONFIG_ARCHITECTURE.md 이번 절을 따른다.


<!-- LeftShoulderCloth_20261008_complete -->
## 2026-10-08 10:38 KST — 왼쪽 어깨 천 미세 조정, Main 반영 완료

사용자가 이동 중 왼쪽 어깨 천이 약간 뻣뻣하게 서는 느낌을 줄여 아주 조금만 더 펄럭이도록 직접 요청했다. 기존 최종 ClothRefinement를 유지하면서 `/Game/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset`의 왼쪽 Cape simulated 관절8개에서 `DefaultInstance.ProfileInstance.AngularDrive.SlerpDrive.Stiffness`만 기준값×0.95로 변경했다. `SetDefaultProfile`로 저장 default도 일치시켰다. 다른 profile field, damping/각도 제한/connector/관성/geometry/body/anchor/충돌/solver는 변경하지 않았다. Hair·Leg·본체 PA/BP/ABP와 Main runtime Source/DLL은 보존했다.

0.95는 어시스턴트가 선정한 **임시 튜닝값**(무단위 배율)이며 원작 직접값/사용자 지정 숫자가 아니다. 원작의 해당 물리 field 값은 저장 자료에서 미확인이다. 기준 저장본은 `BeforeManifest.json` 및 `Before/`(Torso SHA BC422363…), 과거 계수 출처는 `Metadata/PlayerParts_20261007/ClothRefinement/AppliedPerBone.txt`·`TuningProvenance.json`이다. 아래는 현재 프로젝트 acceleration SLERP drive의 실제 저장 계수다. `CandidateProfileAudit.json`의 joints.before_stiffness/after_stiffness/damping과 full profile에 원시 float 값이 있다. 배율의 float32 저장값은0.949999988079071이다. 동일 관성의 spring 관계를 적용한 계산상 natural-frequency 비율은 sqrt(.95)=.9746794345, damping 고정 시 상대 damping 비율은1/sqrt(.95)=1.0259783521이다. engine drive scaling 가정의 계산이며 원작 값이나 세계공간 펄럭임 증가율을 뜻하지 않는다.

| Bone | Before Stiffness | Saved Stiffness | Unchanged Damping |
| --- | ---: | ---: | ---: |
| `B_Cape_02_02_L_Armor001` | 647.933837891 | 615.537109375 | 50.909088135 |
| `B_Cape_01_02_L_Armor001` | 647.933837891 | 615.537109375 | 50.909088135 |
| `B_Cape_01_03_L_Armor001` | 456.404937744 | 433.584686279 | 42.727272034 |
| `B_Cape_01_04_L_Armor001` | 211.570205688 | 200.991699219 | 29.090906143 |
| `B_Cape_01_05_L_Armor001` | 82.644607544 | 78.512374878 | 18.181816101 |
| `B_Cape_01_03_01_01_L_Armor001` | 298.347076416 | 283.429718018 | 34.545452118 |
| `B_Cape_01_03_01_02_L_Armor001` | 173.760299683 | 165.072280884 | 26.363634109 |
| `B_Cape_01_03_01_03_L_Armor001` | 82.644607544 | 78.512374878 | 18.181816101 |


검증은 `Metadata/PlayerParts_20261008/LeftShoulderCloth`의 `NativeComparison.json`/`Verification.json`/`FinalCompletion.json`에 분리했다.

- 같은 fixed30 이동 비교에서 짧은 어깨 패널 속도 RMS55.325880→55.611735deg/s(+0.516675%), 긴 천7은27.525438→27.441731deg/s(−0.304108%), 전체8은 거의 동일했다. Torso joint 굽힘 RMS3.764723→3.840786deg(+2.020414%), 최대11.961719→11.999827deg, tip RMS10.191403→10.529690cm(+3.319337%), 최대26.927262→26.945201cm이다. 전체 flutter가5% 늘었다고 해석하지 않는다.
- baseline/candidate native PIE Success. 8개 full profile에서 active SLERP stiffness만 변경했고 saved default diff0이다. Hair·Leg logged numeric metrics는 정확히 동일했다. Torso의 current-pose LOD0 positive-direct-sim867/dominant735 정점과 external anatomy18에 대한 세 자세 표본은 모두 inside0이었다. 이는 표본 검사이며 모든 동작/LOD/피부 관통 없음의 증명은 아니다. 전후 PNG를 보존하고 화면을 확인했다.
- fresh process의 saved profile8 일치 및 fixed30 native PIE Success. Torso peak11.999827deg, Hair peak31.588255deg/65 joints, Leg peak32.207126deg이다. Main 실제 loaded DLL A95C…를 사용한 stock PIE readback은 Original5 및 finite Torso12/Leg59/Hair72를 확인했다. Guard/Heal은 gameplay/runtime 변경이 없어 반복하지 않았고 기존 회귀 기록을 유지했다.
- 일반 시간 간격 NullRHI 후보2회는 수정하지 않은 Hair의35deg QA만 실패했다(peak60.079030/59.592638deg). 원래 Torso 복원 대조에서도 동일 실패71.877890deg가 재현됐다. Torso는 세 시험 모두45deg 미만이다. `NormalDeltaObservation.json`에 실패를 보존했고 Hair 수정/시간 간격 원인 확정/모든 조건 통과로 기록하지 않았다.
- 첫 Main replace는 다른 SnowWork 에디터의 파일 잠금으로 WinError5, Main 원본 SHA 유지 상태에서 중단됐다. 그 에디터의 정상 종료를 기다린 뒤 새 snapshot으로 PA1만 atomic 전달·selective reload했다. Main PID3528 DevMap/actor·선택 보존, PIE/dirty0, Original5/BP7 up-to-date, solver1/60·24/4/4·linear=true를 확인했다. 전달 snapshot protected162는 모두 동일하다. 최초 snapshot 이후 별도 작업의 DefaultEditor.ini 변경은 최신값을 보존했다. explicit save/compile/PIE/종료 명령은 Main에서 실행하지 않았으며 엔진 reload의 referencer 내부 처리와 구분한다.

최종 Torso SHA `7560A4A740D8AD99370F7D210CC7A444A828EC0F14C4939141A8CD50A23CFCDE`. 별도 PlayerParts 에디터들은 종료했고 Work helper DLL/PDB/modules는 복원했다. 편집 도우미는 기존 `PlayerPartsAuthorEditor.cpp`의 `Khazan.PlayerParts.LeftShoulderSpring`과 기존 PIE helper의 optional shoulder probe만 확장했다. 첫 Json link 실패와 Work 전용 editor dependency 보완 후 성공을 build log에 남겼다. Main runtime 새 파일0이다.

후속 작업은 현재 저장 profile에서 시작한다. `Apply=true`는8개 정확한 baseline을 검사해 중복곱을 막으며 현재 adjusted 에셋에 다시 실행하지 않는다. 전체 ClothAuthor 재실행은 이번 spring override를 덮어쓴다. Hair 일반 시간 간격 문제와 기존 Leg 잔여 body-proxy overlap은 별도 문제로 유지한다.

## 2026-10-08 12:12 KST — 허리 Iron2 충돌 떨림 수정·Main 완료

사용자가 관측한 허리의 지속적인 떨림을 Leg의 `B_Iron_01_01_R_Pelvis` / `B_Iron_01_01_L_Pelvis`로 분리했다. `Metadata/PlayerParts_20261008/WaistJitter`가 상세 증거 폴더이며 `FinalReceipt.json`이 최종 상태다. `CauseProof.json`의 fixed30 접촉 대조는 baseline78.8445~82.5556도/positive-delta frame RMS가 **진단용 Iron 접촉 비활성**에서0.7356~1.1733도로 감소함을 보여 준다. 다른 cloth30 값은 그 대조에서 동일했다. 최종 수정에서는 접촉을 비활성화하거나 장식을 고정하지 않았다.

실제 저장/전달은 `Content/_Art/Player/Character/Meshs/Leg/Player_Original_Leg_RigidBody_PhysicsAsset.uasset`의 **capsule Center2만**이다. SparseSpheres는 적용하지 않았다. `CenterApplied.json`의 exact body/constraint/default profile/asset snapshot 검사로 반경·길이·회전·mass override·InertiaTensorScale·damping·관절/drive·solver 및 다른 body 필드가 보존됐음을 확인했다. CoM은 Center 이동에 따라 바뀌며 principal moments는 기술적 상대 허용오차0.0001 내에서 동일하다(관측 최대 상대 오차 약2.135e-7). runtime Source/Config 수정0, 새 runtime 파일0이다.

| Bone | 이전 Center(X,Y,Z cm) | 새 Center(X,Y,Z cm) | 참조 anatomy 최소 여유(cm) |
| --- | --- | --- | --- |
| `B_Iron_01_01_R_Pelvis` | (7.7883222634,-2.3182778064,0.3073638396) | (15.7454605103,-1.2322616577,-12.0231981277) | 0.4317379011 |
| `B_Iron_01_01_L_Pelvis` | (7.7882966068,-2.3188193980,-0.3072770668) | (16.2953720093,3.0121307373,1.9773033857) | 0.6722866262 |

수치 출처는 **원작 physics 직접 확인값 아님 / 어시스턴트 geometry 계산 및 임시 정책**이다. native audit의 `ImportedLOD0InverseRefBoneLocalCm`에서 bone별 largest-weight dominant536 정점을 추출해 후보 Center를 정했다. 기존 capsule 반경1cm·길이 약21.74236cm·회전은 현행 PA에서 재사용했다. 공통 골반 기준으로 `IronUnit.GetRelativeTransform(LegPelvisUnit) * BodyPelvisUnit`을 사용했다. 독립 Body/Leg ref pelvis는 위치4.18411cm·회전5.0438도 차이가 있으므로 독립 ref를 직접 혼합하지 않는다. anatomy18 capsule과 두 segment/radius 거리를 계산해 겹치지 않는 실제 정점 후보(R5/L9) 중 dominant coverage 최대, 그다음 기존 Center에서 이동 최소를 골랐다. 전체 공간 최적해나 전체 armor 표면 coverage를 보증하지 않는다. 알고리즘/원시 값·좌표·fresh mass/principal/CoM은 `CenterAlignedDryRun.json`·`CenterApplied.json`·`CandidateIronPhysicsAudit.json`에 보존했다. 질량은 각각 약6.276336/6.276208kg 유지다.

- `CandidateMotionVerification.json`: rendered fixed30 native PIE Success, Iron IdleLate RMS R0.167726/L0.205137도, AfterReleaseLate R0.207162/L0.197763도/positive-delta frame. actual collision/enabled 모두1이며 contact samples343/360/161/240이 존재한다.
- `SavedReloadMotionVerification.json`: 새 process로 저장 PA를 재로딩한 fixed30 native 전체 검사 통과. `NormalDeltaMotionVerification.json`: 고정 timestep 없는 새 process도 전체 PIE Success, 실제 관측 mean dt 약0.06124/0.06399s, Iron speed RMS4.65415~6.03696도/s. Hair65·Torso8·Leg30 기존 각도 검사를 그대로 통과했다. 이전 shoulder 기록의 Hair 일반 시간 간격 실패는 삭제하거나 원인 해결로 표시하지 않는다. 이번 초기 bypass/실행 조건이 달라 이번 통과 관측만 추가한다.
- `StockObservation.json`·`StockSavedReadback.json`: Main selected base DLL SHA `9314DF5646B92EDBB61D3E0F3BEABCF99277FA1FEA286DA265C20BBABC8B30EF`를 Work에 연결한 별도 실행에서 Original5·finite Torso12/Leg59/Hair72·candidate SHA/Hair 보존을 확인했다. Iron idle150 positive samples/5s step RMS R0.173401/L0.214368도였다. Main Live Coding patches는 복사하지 않았으므로 live-patched Main과 실행 동일성을 주장하지 않는다. private DLL/PDB/modules는 `StockBinding.status=Restored`와 hash로 복구했다.
- `MainSelectiveHandoff.json`·`MainReadyAudit.json`: Main13700 DevMap에서 Leg1개 CAS 전달·선택 재로딩 Success, BP7/Original5 up-to-date, protected163 동일·dirty content/map0·actor identity/선택 보존. Main PIE/종료/전체 저장/명시적 compile은 수행하지 않았다. 최종 Leg SHA256 `6D3B02FDB05C1D11A4DC3B2A0C5E2799313434EB6E898CC4475E565BCDAFDEF0`. Hair 및 최신 Torso 왼쪽 어깨 PA hash는 각각 `46F21D…6857A` / `7560A4…FCDE`로 유지했다. owned Work editor는 모두 종료했다.

baseline/NoIronContact의 `PhysicsOff` label은 초기화용 `p.RigidBodyNode`가 이미 초기화된 node를 멈추지 못했으므로 결론에서 제외한다. 최신 optional probe는 `p.RigidBodyNode.EnableSimulation`을 사용하고 동일 game time의 중복 샘플을 제외한다. baseline/control과 후보 사이 최신 BP/Source intake 및 probe bypass 차이가 있어 위 개선율을 PA 단독 동일조건 효과로 단정하지 않는다. 기존 constraint Frame2의1/100은 UE BodyScale/component scale 보정과 일치하므로 수정하지 않았다. cached contact gap·참조 shape 여유는 runtime skin 관통 깊이가 아니다. 검증은 제한된 idle/moving/release fixture이며 모든 pose/triangle의 관통0 검증은 아니다. 후속은 현재 final PA에서 시작하며 전체 ClothAuthor/HairAuthor/CollisionAuthor/shoulder author를 반복하지 않는다.

<!-- ShoulderSoftening_20261008_complete -->
## 2026-10-08 — 왼쪽 어깨 가까운 천 추가 유연화·Main 반영 완료

사용자의 추가 펄럭임 요청으로 현재 Torso derived PA의 왼쪽 Cape simulated 관절8개만 조정했다. 대상은 `/Game/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset`이며, 이전 spring×.95가 반영된 저장본 SHA `7560A4…FCDE`를 기준으로 한다. `Metadata/PlayerParts_20261008/ShoulderSoftening/TemporaryTuning.ini`와 `CandidateProfileAudit.json`에 정확한 기준 float·배율·저장 profile을 기록했다. **원작 해당 physics 값은 미확인이며 아래 배율은 어시스턴트 임시 튜닝값**이다.

- 가까운 `B_Cape_01_02_L_Armor001` / `B_Cape_02_02_L_Armor001`: active SLERP spring×.60, damping×sqrt(.60), swing1/2×1.5. 실제 저장 spring615.537109375→369.322265625, damping50.909088135→39.434009552, swing8.800000191→13.200000763deg다.
- 중간 `B_Cape_01_03_L_Armor001` / `B_Cape_01_03_01_01_L_Armor001`: spring×.75, damping×sqrt(.75). 나머지4개는 spring×.85, damping×sqrt(.85). 이6개의 swing 제한은 유지했다. sqrt 배율은 같은 관성에서 spring 감소에 따른 상대적인 nominal damping ratio를 유지하는 계산이며 실제 flutter 증가율이나 원작값을 뜻하지 않는다.
- `DefaultInstance.ProfileInstance.AngularDrive.SlerpDrive.{Stiffness,Damping}`와 가까운2개의 `ConeLimit.Swing1LimitDegrees/Swing2LimitDegrees`만 바꾸고 `SetDefaultProfile`로 동기화했다. 전체 expected constraint/default profile 및 reflected body·joint·PA snapshot을 검사했다. 고정 부착 뼈2·twist·inactive Swing/Twist drive·connector·geometry·mass·관성·몸 충돌·solver를 보존했다. Hair·Leg/Iron·본체·BP/ABP·Main runtime Source는 수정하지 않았다. 기존 Scripts의 editor-only author/optional probe만 확장했고 새 Main runtime 파일0이다.

실제 검증은 `NativeComparison.json`·`SavedReloadComparison.json`·`Verification.json`을 따른다. baseline/candidate fixed30 native PIE와 fresh saved profile readback/PIE 모두 Success다. 짧은 패널 속도 RMS55.561434→72.131229deg/s(+29.82%), 긴 천 첫 simulated 관절 RMS41.996690→43.139979deg/s(+2.72%)다. 긴 천7개 전체 RMS는27.383058→26.118029deg/s(−4.62%)이며 전환 순간의 kick도 포함하므로 모든 구간의 지속 flutter가 증가했다고 보증하지 않는다. Torso saved joint bend peak13.201777deg, 실제 반응8개, Hair peak31.588156deg/65개와 Leg peak32.207188deg/30개는 기존 검사를 통과했다. Hair·Leg logged metrics와 허리 CSV의64개 late bone-window 비교값은 전후 동일하다. Torso 세 자세 표본의 positive-direct-sim867/dominant735 정점은 anatomy18에 대해 inside0/finite였으며, 이는 LOD0 linear skin의 세 표본 결과이고 모든 동작·LOD·triangle의 관통0 검증은 아니다. `SavedReload_Close_Idle.png`/`SavedReload_Close_Moving.png` 및 stock 화면을 보존했다.

도구 실패는 삭제하지 않았다. `IntakeInputMismatchNative.log`의 첫 `Input.Action.RB` 매핑 불일치는 최신 입력 자료 동기화 후 성공한 baseline/candidate와 구분한다. 카메라 `set_editor_property` 기본 notify를 사용한 `CloseFramingNotifyFailureNative.log`는 전 파츠 motion0으로 실패했다. 엔진 Pre/PostEditChange→component reregister→owner ConstructionScript 재실행 경로가 fixture의 cached weak component를 무효화할 수 있어 PA 실패로 단정하지 않는다. transient 카메라에 `notify_mode=NEVER`를 사용한 최신 saved 시험은 Success이며 저장 PA는 바뀌지 않았다. 이전 Hair 일반 시간 간격 실패와 Leg 잔여 proxy overlap 기록도 유지한다.

stock 별도 실행은 Main PID24552에 실제 매핑된 `UnrealEditor-Khazan.dll` SHA `C251AC0684153C792852CCA77365F2F58C6CB8391B262D30AD2109A1BD8EC660`을 사용했다. 선언된 `UnrealEditor-KhazanSnowPlayerCapsule20261008.dll` 및 Live Coding patches와 다르므로 미래 Snow 모듈/현재 live-patched Main의 실행 동일성은 주장하지 않는다. `StockBinding.status=Restored`로 private binary를 복원했다. `MainSelectiveHandoff.json`은 DevMap에서 Torso PA1의 CAS 전달·selective reload Success, protected166 동일, actor/선택 보존·dirty content/map0·noPIE를 기록한다. 첫 transient WinError5는 MainSelectiveHistory에 남긴 뒤 재시도가 성공했다. `MainReadyAudit.json`에서 Original5/BP7 UP_TO_DATE를 확인했고 `FinalReceipt.json`은 complete=true/owned editor0/private binary 복원을 기록한다. Main 자동PIE·전체 저장·명시적 compile·종료는 하지 않았다. 최종 Torso SHA는 `EC471B6F631C9FB4247B942254739101694FB490F733D1ACCF7CA2F89C400D22`이며 Hair `46F21D…6857A`와 Leg `6D3B02…FDEF0`를 보존했다. 후속은 이 저장본부터 시작하며 전체 ClothAuthor 또는 같은 Apply=true 배율을 다시 실행하지 않는다.
