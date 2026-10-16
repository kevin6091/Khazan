# 몬스터 발견 전 대기와 보행 — 2026-10-07 (ARCH-78)

이 문서는 ARCH-77 몬스터 구현의 후속 변경이다. 게임 Source 적용과 격리 에셋 작성/검사가 진행 중이며, 메인 에셋 전달·최종 제품 검증 완료는 하단의 실제 결과 기록으로 판단한다. 기존 2026-10-06 성공 기록을 이번 방향별 포즈/발밀림 검증으로 대체해서 읽지 않는다.

## 실제 원인

격리 LLDB의 Swordsman `UpdateKinematics_AnyThread`에서 유효 snapshot과 GroundSpeed=90cm/s를 확인했다. native PIE active-player 기록에서는 물리 속도 53.347~180cm/s인 네 종류 모두 `BS_Peace_*` X=0/Y=0, Basic Loop weight=1이었다. 즉 CMC 이동이 있었지만 최종 asset-player 입력 바인딩이 갱신되지 않았다.

`Scripts/Engineering/MonsterAuthorEditor.cpp`의 Node 생성에 `PostPlacedNewNode()`가 빠졌다. UE5.8 `Engine/Source/Editor/AnimGraph/Private/AnimGraphNode_Base.cpp`의 해당 함수는 `EnsureBindingsArePresent()`와 `UAnimBlueprintExtension::RequestExtensionsForNode(this)`를 호출한다. 현재 author helper는 이 엔진 초기화를 수행한 뒤 pin을 만들고 연결한다. BP UP_TO_DATE 및 native speed만으로 최종 재생이 정상이라고 판단하지 않는다. 증거는 `Metadata/MonsterIdle_20261007/DebuggerEvidence.json`, `LocomotionProbe_Before.log`이다. AnimGraphRuntime PDB 부재로 engine BlendSpace breakpoint는 매핑되지 않았고 직접 player 기록으로 확인했다.

## 현재 책임과 작은 확장

새 runtime 파일/class/component/manager는 없다. 기존 CharacterDefinition에 `FKZUnawareRoutine` 목록을 추가하고, 기존 ComboAction·ASC 명령·StateTree task·Controller focus/nav·Locomotion/CMC·KZAnimInstance snapshot·몬스터 ABP를 이용한다.

- Definition: Name/Role/AbilityClass 데이터와 기존 InitialAbilityGrants. Role은 Solo/Talk01/Talk02의 배타 데이터 선택이며 공유 gameplay 상태의 사본이 아니다.
- Monster instance: `UnawareRoutineName`(None이면 Solo 중 선택), `bPatrolWhenUnaware`, 서로를 참조하는 `TalkPartner`, 서로 다른 `bSecondTalkRole`. 배치 설정이며 현재 AI state를 별도로 저장하지 않는다.
- ComboAction: 기존 실행 수명과 Loop/End node·Montage section. `GetCurrentNodeId()`는 기존 실행 node를 읽기만 한다.
- Idle task: 실행한 자기 spec handle, End 요청 여부, 실제 대화 상대 weak reference를 task 수명에 보관한다. 종료 시 자기 handle/자기 command만 정리한다. Patrol은 별도 task 선택으로 이전의 랜덤 nav 이동/대기 로직을 이용한다.
- Controller: 실제 Sight 결과·타깃/기억·focus/nav를 소유한다. 두 배우가 실제 Talk Loop일 때만 상대에게 발견을 전파한다. 전달된 기억은 실제 sight라고 표시하지 않는다.
- AnimInstance: 기존 GT snapshot→worker 파생 데이터만 이용한다. Main에 AI state/태그 사본/새 관측 멤버를 추가하지 않았다.

## 대기 → 발견 End → 접근

Swordsman의 Solo는 Guard Loop01→Guard End01, Basic Loop03→Basic End03, Search Loop01→Search End01, Sit Loop01→Sit End01이다. 요청한 `A_EN_PLAY_AC_EmpireSword_*`를 정확히 사용한다. Solo끼리 랜덤 선택은 진입 시 한 번만 하며 Sit 도중 임의로 다른 Loop로 바꾸지 않는다.

각 루틴은 기존 ComboAction BP/ComboDefinition/Montage로 작성한다. Loop section의 Next는 Loop, End의 Next는 None이다. Loop node의 `Command.AI.Alert` Release edge가 End node로 이어진다. 감지 시 task는 Begin→Release pulse를 기존 ASC에 보낸다. 기존 ComboAction의 Release 처리는 Closed window에서도 즉시 edge를 수행한다. End에는 조기 이동 InputEnd를 넣지 않으며 Montage/Ability의 정상 종료 후 접근을 허용한다. 해당 End를 완료하면 AlertedTarget을 기록해 동일 발견에 generic Alert를 또 재생하지 않는다. 대기 데이터가 없는 캐릭터와 Patrol 발견은 기존 generic Alert 경로를 사용할 수 있다.

대화는 서로 유효한 partner/반대 Role/해당 Ability grant/controller가 있어야 한다. 첫 task는 같은 GT turn에서 양쪽의 이미 부여된 Ability를 함께 활성화하며, 다른 task는 실행 중인 자기 spec을 채택한다. 한쪽이 Solo/End/전투/미Possess라면 시작하지 않는다. 한쪽 활성화 실패는 새로 시작한 자기 실행을 취소하고 Solo로 복귀한다. 상대 이탈/취소/UnPossess는 남은 Talk의 End→Solo로 연결한다. 감지하면 양쪽이 각각 Talk01/Talk02의 End를 재생한다. 두 명이 가까이 있다고 자동 대화를 강제하지 않는다.

다른 종류에는 실제 보유한 쌍만 등록했다. SwordShield Basic03/Sit01, Heavy Basic03/Search01/Sit01, Halberd Basic01/Guard01/Search01/Talk01/Talk02이다. Talk02가 없는 종류에 임의로 Talk01 역할을 복제하지 않았다. 원본 패키지와 AnimationTrack.AnimSegments/원시 duration·rate는 `Metadata/MonsterIdle_20261007/IdleAuthoringPlan.json`의 16routine/32step에 있다. 원본 Art clip은 수정하지 않으며 gameplay 복사본은 `/Game/Monsters/<Family>/Animations/InGame`이다.

## 정지·평상시 걷기·대치 걷기

몬스터 ABP는 움직임이 없을 때 평상시 Basic Loop / LockOn Stand를 RotationMode로 선택한다. 기다림의 Guard/Search/Sit/Talk는 Ability의 DefaultSlot이 덮어쓴다. 움직일 때 Walk는 Peace walk / Combat 방향별 Walk, Run은 기존 Run_F Sequence다. 모든 합성은 기존 최종 Inertialization→Output 경로를 사용한다.

Walk BlendSpace의 X는 기존 `VelocityLocal`의 XY 방향 Yaw이며 입력 의도가 아닌 실제 이동 방향이다. Y는 작성 시의 기준 Walk row에 고정한다. 별도 정지 경로를 사용하므로 긴 Idle cycle을 Walk와 시간 혼합해 보폭을 느리게 하지 않는다. Node PlayRate는 실제 GroundSpeed / 기준 속도다. 각 Walk sample RateScale은 기준 속도 / 해당 클립의 계산된 발 접지 속도이며 Sequence의 원본 RateScale/키를 바꾸지 않는다.

Combat 대각선은 90° sector 내 weight `w=(abs(Yaw)%90)/90`에서 `m=sqrt((1-w)^2+w^2)`로 직교 stride vector의 길이 감소를 보정해 NodeRate를 `GroundSpeed/(기준 속도*m)`로 계산한다. 90/1은 기하학 상수다. 이는 일정한 접지 속도·직교 cycle을 가정한 계산 보정이며 지형/발별 순간 속도/회전 접지까지 완전한 foot lock으로 주장하지 않는다. 최종 월드 발 이동 기록으로 그 한계를 검사한다.

## 수치 출처

원작 AIData의 이동 속도 직접값은 미확보다. 기준 속도는 저장 InGame Sequence DataModel의 bone transform keys, frame interval, 기존 mesh relative transform/scale(두 Human1.2, Heavy1.3, Halberd1.0), 기존 Sequence RateScale을 입력으로 계산한 값이다. root-locked 조건의 FK 발 위치를 프레임 중앙 차분하고 이동 반대 접지 성분의 median을 사용했다. 낮은 발 높이15%/최소0.5cm의 접지 선택은 명시적 분석 휴리스틱이며 원작 AI 설정이 아니다. clip/path/frame/bone/선택된 raw 속도·변환·계산 결과는 `StrideAnalysis.json`에 저장한다.

첫 분석 Walk/Run 기준(cm/s)은 Swordsman135.326/445.017, Shield207.943/414.982, Heavy259.945/677.963, Halberd173.779/414.402이다. 실제 author 결과의 원시 float를 우선한다. 정의의 초기 CMC Walk/Run/Sprint에 반영하고 BP 기준 row/rate와 함께 저장한다. 이 값은 원작 직접 확인값이 아니다. 이후 CMC pace만 Definition에서 바꾸어도 BP는 실제 GroundSpeed로 기존 클립 기준 재생률을 계산한다.

기존 sight/range/cooldown/가감속/rotation·0.1s section jump/0.2s presentation은 기존의 원작 미확인 임시 설정을 유지했다. 이번 지시는 관련 값을 원작 확정값으로 승격하지 않는다. Player의 .01 scale/로코모션/Heal/Guard를 변경하지 않는다.

## 배치와 검증 절차

기존 `DevAI_*`4개를 보존한다. `DevAI_Swordsman`은 Guard 지정, 추가 `DevIdle_Basic/Search/Sit/Talk01/Talk02/Patrol`6개는 Outliner `DevMap/Monster AI/Waiting`에 배치한다. Talk 두 배우는 서로 마주보며 mutual partner/반대 role이다. 위치는 테스트 배치값이며 원작 encounter 위치가 아니다.

`Khazan.Monster.WaitingPIE`는 네 Solo의 실제 Loop→정지된 End→종료, 양쪽 Talk Loop/마주보기, 한쪽 UnPossess→상대 End/Solo, 준비된 pair 재시작·양쪽 발견 End를 검사한다. `Khazan.Monster.PIE`는 기존 자연 감지/nav/대치/13공격 section·HP 불변/cleanup에 더해 네 종류의8방 실제 nav Walk, 활성 Combat samples/rate/time, 최종 bone pose 일치를 검사한다. 테스트 fixture는 기존 public nav와 원인별 이동 constraint를 이용하며 게임의 private AI 함수나 테스트 API를 추가하지 않았다. Python으로 이동/입력을 주입하지 않는다.

첫 수정 PIE는 binding·32최종 pose 비교가 통과했으나 두 종류의 explicit focus가 target 기억 만료로 풀려8nav 목적지 중 일부가 실제 F를 평가했다. 이는8방 전체 검증 완료 근거가 아니다. 현재 test는 focus 유지와 예상 actor-local 방향 검사, 실제 월드 발 속도/접지 분석을 보강했다. 최종 saved reload/stock build/제품 회귀와 main 선택 전달 결과는 하단에 별도로 기록한다.

## 2026-10-07 — 발 위상 보완과 측정 조건

저장된 접지 frame 목록에서 Heavy R/B와 Halberd B의 좌·우 발 stance가 F에 비해 약 반 cycle 뒤집힌 것을 확인했다. 단순한 normalized time 혼합/속도 보정만으로 맞지 않는 부분이다. 기존 InGame 보행/Run 복사본24개에 `KZLeftPlant`/`KZRightPlant` SyncMarker를 계산해 저장했다. 각 발의 낮은 높이·이동 반대 속도 mask에서 가장 긴 원형 stance 구간의 시작 frame×DataModel frame interval을 사용했다. 원본 Notify 시간 직접값이 아니다. 원본 Art pose/키/RateScale과 Skeleton은 수정하지 않는다. `StrideAnalysis_WithSync.json`에 이름/frame/seconds/stance frame 수를 추가했다.

기존 BlendSpace marker synchronization을 이용한다. UE5.8 BlendSpaceUtilities의 pattern 비교는 cycle 시작 순서가 다른 동일 좌·우 pattern을 허용한다. 사용 중인 Combat player의 unique marker names 두 개, 실제 sample 시간 전진 및 최종 pose 비교는 격리 sync PIE에서 검사했다. 예전 markers가 없는 normalized-clock 결과는 이번 marker 적용 결과와 구분한다.

첫 world-foot 측정은 Automation latent polling의 짧은 구간에서 contact sample1~7개밖에 확보하지 못했다. 이를 전체 foot lock/발밀림 정도의 확정 증거로 사용하지 않는다. 최종 개발 테스트는 WorldPostActorTick에서 매 프레임 현재 메쉬를 읽고, nav Walk 구간만 world dilation0.25로 분석 해상도를 높이며 원래 값을 정상/실패/취소 시 복구한다. 이 수치는 테스트 측정 조건이며 게임 설정이 아니다. 골 길이/시선 fixture와 검사 후 원래 enemy 위치도 복구한다. 발 joint 속도는 heel/toe rolling과 몸 회전도 포함하므로 실제 sole 접지점의 완전한 고정과 구분한다.

제품 설정: work-only editor author cpp는 `Saved/ExcludedAuthorSources`로 보존 이동했고 게임 Source에는 없다. Stock Build.cs는 main과 내용이 동일하다. 복원 파일 timestamp로 이전 editor 의존 rules DLL이 재사용된 문제를 발견해 timestamp를 갱신했고 `ColdBuild_ProductRulesRefreshed.log`의 실제44action/Succeeded를 얻었다. 앞선 Product/Product2는 header 실패/캐시 설정 상태를 보존하며 최종 stock 근거가 아니다. 현재 fresh product PID26160에서 Waiting→Monster→Heal/Guard를 재검증하는 단계이며 main 에셋 전달은 아직 완료가 아니다.

## 2026-10-07 — 대각선 접지 보완의 적용 범위와 수치 출처

stock 제품 PIE 네 테스트가 통과했지만 `FootBeforePlacement`의 실제 world-foot 기록에서 대각선 발 joint 잔차가 남았다. 순수 PlayRate 식은 stride-vector의 선형 길이 가정이고 실제 FK 관절 회전 블렌드는 비선형이므로 이것만으로 완전 접지를 보장하지 않는다. Walk branch에만 기존 UE `CopyBone(FK→Virtual target)` 두 개 → `Foot Placement` → `Leg IK`를 둔다. 이후 기존 Gait Run 선택/Moving Stand 선택/DefaultSlot으로 합성한다. 새 캐릭터 컴포넌트나 Ability/IK 실행 클래스는 없다.

세 Skeleton에 root→좌·우 발 `VB KZFoot_L/R`만 추가한다. 원본 bone, socket, slot을 삭제/재명명하지 않는다. 원본 Art Sequence 키/RateScale/FPS를 변경하지 않는다. `KZFootContactState_L/R` FloatCurve는 InGame24복사본의 기존 FK 높이/역방향 속도 분석 mask를 기록한 계산 데이터다. 값0=접지, 2=비접지와 threshold1은 상태 mask 표현이며 cm/s의 원작 발 속도가 아니다. 엔진 Manual SpeedCurve 입력에 이 mask를 주고 Unalignment threshold2로 두 상태를 나눈다. constant interpolation으로 sample 사이 상태를 유지하며 BlendSpace에서는 가중치로 혼합된다.

plant LockType은 PivotAroundAnkle로 골 발 joint를 기준으로 잡는다. Trace는 DevMap stable simple collision을 사용한다(bDisableComplexTrace=true). 기타 plant/trace/spring/pelvis 수치는 UE5.8 `AnimationWarping/Source/Runtime/Public/BoneControllers/AnimNode_FootPlacement.h`의 엔진 기본 표현 설정을 초기 임시값으로 사용한다. 원작 필드가 아니다. 예: UnplantRadius35cm(component units), ground distance10cm, trace Start-75/End100cm/Radius5cm, plant unplant angle45deg, pelvis MaxOffset50cm 등이다. 이 값의 소비·효과는 발이 authored pose에서 너무 멀어지면 lock 해제, 바닥검사 범위, pelvis 보정 한계다. clip/mesh 단위와 실제 slip·관절 안정성으로 조정하며 원작 근거가 확보되면 조건/단위를 맞춰 대체한다. Leg IK ReachPrecision0.01cm/MaxIterations12도 엔진 기술 설정이며 원작 gameplay 값이 아니다.

Foot Placement의 엔진 evaluator가 owner/CharacterMovement floor를 직접 읽으므로 NPC ABP만 parallel update와 evaluate를 끈다. 기존 AnimInstance의 `bRequiresGameThreadPoseEvaluation`은 EditDefaultsOnly 초기 false인 스케줄 설정이고 엔진 CanRunParallelWork만 const로 소비한다. NPC author=true, Player=false; 실행마다 바뀌는 gameplay 상태나 snapshot 사본이 아니다. Foot node가 자기 plant state를 수명/재진입에 맞게 관리한다. 최종 mesh test는 엔진이 의도적으로 수정하는 pelvis/다리/Virtual target을 제외한 나머지 local bones의 원본 walk pose를 비교하고 접지 구간의 실제 월드 발 이동은 별도로 측정한다.

첫 FootAuthor는 skeletal-control 출력 pin을 ComponentPose로 연결한 실수로 Fail했다(실제 출력은 Pose). 기록 `FootAuthor_PinFailure.log`는 보존했고 source pin을 수정해 재빌드했다. 이 실패 상태는 main에 반영하지 않는다. 적용/최종 runtime 결과는 이후 절을 따른다.

## 2026-10-07 — DevMap에서 직접 확인·배치하는 방법

World Outliner의 `DevMap/Monster AI/Waiting`을 펼친다. `DevAI_Swordsman`은 Guard, `DevIdle_Basic/Search/Sit`은 해당 Solo 루틴이다. `DevIdle_Talk01/Talk02`는 상호 TalkPartner와 상반 bSecondTalkRole로 마주보는 대화 짝이고 `DevIdle_Patrol`만 bPatrolWhenUnaware=true다. 플레이어가 아직 시야/거리 밖이면 stationary Solo 또는 두 Talk Loop를 유지한다. 발견하면 각각 짝이 맞는 End를 완료한 뒤 Chase/Attack/Standoff로 이동한다. Standoff의 정지는 전투 Stand, 좌·우는 LockOnWalk이며 미발견 Basic Loop와 분리되어 있다.

각 actor Details의 배치 설정: `UnawareRoutineName=None`은 Solo 진입 때 후보 중 한 번 선택, 명시 이름은 Guard/Basic/Search/Sit 같은 definition Name을 선택한다. 두 actor가 가까이 있다고 자동으로 대화하지 않는다. 대화를 선택하려면 양쪽 TalkPartner를 서로 지정하고 bSecondTalkRole을 한쪽 false(01), 다른 쪽 true(02)로 둔다. 둘의 definition에 해당 Talk 역할과 ability가 있어야 한다. 서로 참조하지 않거나 역할이 같거나 한쪽 미Possess/전투/다른 Solo이면 Talk 대신 Solo를 사용한다. 원래 짝으로 시작한 대화의 상대가 없어지면 남은 쪽은 자기 End 후 Solo다. partner를 지정하지 않은 두 actor는 서로 가까이 있어도 각자 Solo를 할 수 있다.

종류별 설정은 `/Game/Monsters/<Family>/Data/DA_Character_<Family>`의 `UnawareRoutines`다. 접힌 원소도 Name/Role 표시를 사용한다. Name·Role·기존 generic ComboAction AbilityClass만 저장하며 실제 Loop/End는 해당 GA의 ComboDefinition/Montage가 소유한다. Swordsman6/SwordShield2/Heavy3/Halberd5의 유효 쌍16을 준비했다. 없는 다른 병종 Talk02를 빌리거나 skeleton을 섞지 않는다. runtime 새파일/class/component/Manager0이며 Foot Placement의 engine scheduling 설정 한 개만 기존 AnimInstance에 추가했다.

보행은 실제 CMC velocity의 actor-local 방향을 기존 snapshot으로 읽어 선택한다. 발별 SyncMarker/시퀀스 보폭 기반 rate가 기본 속도/phase를 맞추고 engine Foot Placement/Leg IK가 Walk의 접지 발을 유지한다. 공격/발견 End 몽타주는 DefaultSlot에서 이후 합성하므로 그대로 authored pose를 수행한다. Foot engine state는 Initialize/relevance 복귀/teleport에서 ResetRuntimeData를 호출한다(UE5.8 FootPlacement.cpp1146–1195). 임의 캐릭터 Reset helper를 추가하지 않았다.

`AnimationWarping` plugin이 enabled여야 Foot node를 로드할 수 있다. 이 node를 사용한 네 NPC ABP는 native `bRequiresGameThreadPoseEvaluation=true`, ABP multi-thread update=false를 유지한다. Player의 설정은 false이며 기존 parallel snapshot 경로다. 이 bool은 engine scheduler용이고 전투 상태나 AI 행동 사본이 아니다. Engine node의 GT floor 읽기를 다시 worker로 넘기지 않는다.

검사 scope: 현재32방 nav fixture는 실제 AI MoveTo/CMC 이동이며 Python 이동/입력 주입이 아니다. 접지 판정은 계산 mask와 낮은 발 높이에 근거하고 속도 유한차분의 양쪽 frame이 모두 plant인 interval을 센다. median<1cm/s·sample>=3은 기술적 QA 기준이지 원작 gameplay 값이 아니다. 대각선4 화면은 별도 development CameraActor를 사용하고 view target/actor/dilation/delegate를 정상/실패/종료 시 돌려놓는다. 실제 발바닥 모든 vertex·모든 경사/눈/연속 전투가 영구적으로 완전 고정된다고 확대하지 않는다. 수납/발도 Heal·Guard 기존 모션과 Player .01·원본 Art pose/rate는 후속 회귀·원본 audit 결과 절로 확인한다.

## 2026-10-07 — 최신 원본 raw pose 대조·제품 대기 재검증 성공

최종 제품 코드에서는 editor author source/dependencies가 제거된 stock rules를 사용한다. `ColdBuild_FootPlacementProduct.log`의44action/Succeeded 이후 development test만 보완해 `ColdBuild_ProductFinal.log` Succeeded. fresh PID8248의 `SourceAnimationAudit` 04:04:42 UTC Success: 현재 main32시퀀스879799 raw transforms, bone key count/FPS/RateScale를 InGame 루틴과 직접 대조했다. 위치/scale 오차0과 normalized quaternion 허용오차 내 동일함을 확인했다. 원본 main root motion=true 등 사용자의 flags를 되돌리지 않는다. InGame nav-driven 복사본은 의도한 enableRootMotion=false/forceRootLock RefPose 정책을 유지한다. 10/6 baseline와 다른 BasicLoop01은 이번 변형으로 단정하지 않으며 기존 main 수정 timestamp와 bytes를 기록했다.

증거 `SourceAnimationAudit_Success.log`, `OriginalWaitingDiskDifferences.json`, `OriginalWaitingClipCurrentBaseline.json`(전달 전 최신 main hash)이다. 출처를 변경 전 전수 baseline이 있었다고 표시하지 않는다. raw source 읽기의 임시 mount는 검사 종료에 해제했고 alias package는 transient/clean으로 처리했다. Main 원본의 save/replace는 없다.

fresh 제품 WaitingPIE 04:06:15 UTC Success에서 4 Solo의 Loop/End 완료 후 접근, pair 초기 동시 Talk·마주보기·partner UnPossess→남은 End/Solo·두 역할 재시작·공동 발견 End를 다시 확인했다. 네 종류 8방향 actual pose/contact camera와 기존 공격/cleanup은 이어지는 최종 Monster.PIE 결과를 따른다. Main 전달은 아직 준비 상태다.

## 2026-10-07 — 메인 반영과 마지막 접지·테스트 보완의 구분

04:16:32 UTC 메인에 준비129패키지(79신규/50기존)를 baseline 충돌0/SHA 일치로 반영했다. 메인 Source cold build는21action/120.91초/Succeeded. 사용자 직접 확인용 메인 PID17552의 MainReadyAudit는 DevMap의10몬스터/4 Solo/서로 마주 보는01·02 pair/Patrol1, NPC GT evaluation=true와 PIE없음/dirty0를 확인했다. MainHashVerification은129 준비본 일치와32원본 파일 보존을 확인했다. 메인 자동 PIE를 실행한 것은 아니다.

최종 관측 중 editor-world API를 PIE에서 호출한 실수로 첫 Monster 시험은 실패했다. 해당 관측 호출을 제거한 다음 시험에서는 Halberd case1의 contact14개/ankle drift median2.117039803cm/s가 기술적 QA<1을 넘어 실패했다. 같은 제품의 read-only 발목·발끝·Virtual target 관측 실행은04:33:35 Success,32방향 median 최대0/min sample4였다. 어느 실패 기록도 삭제하지 않는다. 관측값은 발목과 최종 IK 목표가 함께 움직였음을 보이며, AnimationWarpingRuntime PDB 부재로 엔진 내부 plant/replant/extension 분기를 직접 디버깅했다고 주장하지 않는다.

표적 원본 대조 HalberdInputPlantPlane.json은 F/R204 raw samples를 AnimPose Raw 평가로 읽고 `Root`에 대한 Foot/Toe0의 component 높이 최솟값을 계산했다. 계산 contact에서 최대3.023136611cm, 기존 DistanceToGround10 초과0이다. 이는 원작 gameplay threshold가 아니며 모든 runtime blend frame의 높이 증거와 구분한다. 불필요하게 ground threshold를 늘리지 않는다.

Halberd ABP의 기존 `AnimGraphNode_FootPlacement_1.Node.PlantSettings.MaxExtensionRatio`만0.5→1.0으로 시험한다. 엔진 `GetMaxLimbExtension`은 입력 pose 길이가 chain 길이 이하일 때 `DesiredExtension + (LimbLength - DesiredExtension) * Ratio`를 사용한다. 1은 남은 chain 길이 전부를 허용하는 임시 표현 설정이다. 원작 직접값·사용자 지정값으로 표시하지 않는다. 새로 뼈 길이를 확대하거나 4종 전체 설정을 바꾸지 않는다. 입력 pose가 이미 chain보다 길면 엔진은 기존 DesiredExtension을 유지하므로 이 설정을 모든 상황의 절대 도달 보장으로 설명하지 않는다. ABP 설정에 모아 두며 author helper에도 한 줄로 기록한다.

첫 Python node property 변경과 즉시 compile은 BlueprintCompilationManager의 queued request/CDO ensure로 own editor가 종료됐고 에셋은 저장되지 않았다. 메인은 그대로다. fresh20960에서 property notify NEVER 설정과 다음 request의 compile/save를 분리해04:41:57 정상 저장했다. normal quit/own render3/background throttle true 복구 후 stock cold build4action/10.86초 성공, fresh26976의04:46:48 saved reload에서 Ratio1을 확인했다. 그 값의 최종 runtime 시험과 메인 보완 반영은 이후 완료 절을 따른다.

Heal 회귀의2.7초 고정 관측은 coarse editor frame에서 실제 Heal→Draw handoff보다 먼저 도착했다. 게임 Heal 구현은 그대로이며 개발 test가 Stage9/11/13/15에서 실제 `HasInputEnded`를 기다린다. Monster test는 같은 fixture를 재사용하는 `Khazan.Monster.HalberdPIE` 별칭으로 해당 병종만8방향/nav/공격/cleanup을 재검사할 수 있다. 추가 gameplay API·runtime class는 없다. development camera는 Actor 중심을 보며 화면 범위만 보완했고 actor/control/input의 gameplay 설정을 바꾸지 않는다.

## 2026-10-07 — 최종 구현·메인 반영 완료

현재 이 절이 위 준비/진행 중 기록을 대체하는 실제 결과다. 기존 CharacterDefinition·초기 grant·ComboAction·StateTree·Controller perception/focus/nav·Locomotion/CMC·공통 snapshot을 재사용했다. 새 runtime C++파일/Ability/Component/Manager0, 실제 소비되는 데이터 enum/struct와 기존 함수 보완만 있다. Idle은 Guard/Basic03/Search/Sit01의 정지 Loop와 해당 End, Talk는 서로 마주 보는 상호01/02 pair, Patrol은 별도 이동이다. 발견 시 각 End를 끝낸 뒤 접근한다. 미발견 Basic Loop와 전투 정지 Stand, Peace/Combat walk, Run은 실제 포즈 선택에서 분리됐다.

원인 확인: 기존 author helper의 `PostPlacedNewNode()` 누락으로 애니메이션 노드의 exposed 입력 binding/extension이 초기화되지 않았다. 물리 이동과 native snapshot은 정상인데 BS X/Y=0·Basic Loop weight1이었던 관측을 수정 후 실제 asset-player/sample time/mesh pose로 다시 검증했다. 이전 CMC·AI 상태 성공 기록만으로 보행 성공을 주장한 범위는 이번 실제 포즈 증거로 보완한다.

fresh stock PID26976 최종 결과는 Monster.PIE04:53:47 Success(4종×8방향/자연 감지·End→접근/대치/13공격/재추적/HP 불변/cleanup), HalberdPIE04:58:01 Success(별도12FPS·8방향 재검사), Heal04:59:37/Guard05:00:48 Success다. Waiting04:06:15와 SourceAnimationAudit04:04:42의32시퀀스/879799 raw transforms 결과도 유지된다. 이후 waiting/gameplay source와 원본 파일은 변경되지 않았고 Halberd Foot Placement 한 항목만 보완했다. Source author/dependencies가 없는 stock rules의 테스트다. Python으로 플레이어 입력/이동을 주입하지 않았다.

FootFinal/32CSV의 접지 interval ankle 수평 drift 중앙값 최대0.0cm/s, 최소 유효 sample11; FootHalberdRepeat의8CSV는 중앙값 최대0.0/min sample12다. QA<1cm/s를 두 실행 모두 통과했다. 두 endpoint의 계산 contact/낮은 높이 band/이동 반대 방향 투영을 사용한 관측이다. 모든 발바닥 vertex·접지 시작/끝·모든 경사/극단 frame hitch·원작 연속 포즈가 영구 고정된다는 뜻은 아니다. 이전2.117cm/s 실패와 관측 오류/compile queue 로그도 보존한다. FinalCaptures의4 native 화면은 발까지 포함해 육안 확인했다.

메인에 scoped129패키지(79신규/50기존)를 반영한 뒤 추가 Halberd ABP1만 baseline/hash 검사로 보완했다. 최종129준비 SHA 일치/원본32 파일 hash 보존, Main stock build5action/27.82초/Succeeded다. 첫 상대 project 경로 호출 실패는 로그로 남겼고 절대 경로 재시도가 위 성공이다. Main PID26644를 사용자 직접 테스트용으로 정상 표시 재실행했다. FinalMainReadyAudit05:05:41은 정확한 DevMap10몬스터/4 Solo/상호 pair/Patrol1, NPC GT=true/Player=false, Halberd Ratio1, PIE없음/dirty0를 확인했다. 메인 자동 PIE는 없다. own26976은 render3/maxFPS0/background throttle true를 복구하고05:03:45 정상 종료했다. 대기 중 author/helper/전달 작업이 없다.

증거는 `Metadata/MonsterIdle_20261007/RuntimeResult.json`, `MainAppliedResult.json`, `MonsterPIE_FinalProduct.log`, `HalberdPIE_LowFPS_Success.log`, `HealPIE_FinalProduct.log`, `GuardPIE_FinalProduct.log`, `FinalSavedAudit.json`, `FinalMainReadyAudit.json`, `FinalMainHashVerification.json`, `FinalPreparedAssetManifest.json`, `FootFinalSummary.json`이다. 준비본/백업은 Saved/MonsterIdle_20261007에 있다. Snow/PlayerParts와 Player .01/기존 locomotion 정책·원본 clip/rate를 이 작업이 되돌리지 않았다.

다음 사용자 확인: 열린 DevMap에서 Play → Outliner의 DevAI_Swordsman(Guard), DevIdle_Basic/Search/Sit 및 DevIdle_Talk01/02 쪽으로 접근 → 대응 End 후 접근·플레이어를 보는 좌우 Walk·전투 Stand·공격을 확인한다. DevIdle_Patrol은 별도 배회 예다. 새 배치에서 Name=None이면 Solo 중 한 루틴, Talk를 원하면 양쪽 TalkPartner/반대 bSecondTalkRole/서로 보는 회전/해당 definition 역할을 지정한다. 파트너 없는 actor 둘은 가까워도 Solo이며 파트너 상실은 남은 End→Solo다. 피해/피격·원작 AIData 전체/네트워크/연속 물리 패드 및 전체 지형 QA는 이번 완료 범위에 없다. 이미 완료한 전수 author/retime/전체 복사를 반복하지 않는다.

2026-10-07 완료 용어 보충: 위 새 Ability0은 C++ Ability subclass 추가0이라는 뜻이다. 기존 UKZComboActionAbility를 설정한 data-only GA Blueprint16개와 ComboDefinition16개/Montage16개는 실제 대기 루틴 데이터로 생성했다. 이를 신규 Blueprint 실행 class가 전혀 없다고 해석하지 않는다.

## 2026-10-07 — 고정 대기·발견 후 전투 유지·선택 행동 완료 후 Chase: 실제 메인 완료

사용자 직접 구현 요청의 후속 결과다. 앞선 무인지 루틴 무작위 선택/시야 기억 만료·leash 타깃 포기/거리 증가 즉시 대치 중단 정책은 아래 범위에서 대체한다. 메인까지 실제 반영했다. 신규 runtime C++ 파일·Ability subclass·Component·Manager는 0이며 기존 4파일(Controller h/cpp, StateTreeNodes cpp, development PIE test cpp)과 gameplay package 5개만 전달했다. 다른 작업의 Snow/PlayerParts, DevMap, Config, Player BP/ABP 및 기존 몬스터 ABP·보행·접지 데이터는 이번 전달에 포함하지 않았다.

### 1. 두 병종의 대기 루틴 고정

- HeavySwordsman: DA_Character_HeavySwordsman.UnawareRoutines는 Solo/Basic 하나다. 기존 AM_Idle_Basic의 A_EN_PLAY_AC_EmpireSwordHArmor_Basic_Loop_03→A_EN_PLAY_AC_EmpireSwordHArmor_Basic_End_03 두 segment를 그대로 재사용했다. Heavy Montage 파일은 바꾸지 않았다.
- HalberdElite: DA_Character_HalberdElite.UnawareRoutines도 Solo/Basic 하나다. 기존 GA_Idle_Basic/DA_Combo_Idle_Basic/AM_Idle_Basic을 재사용하고 Montage 두 segment만 A_EN_PLAY_AC_EmpireHalberd_Basic_Loop_02→A_EN_PLAY_AC_EmpireHalberd_Basic_End_02로 교체했다. End section 시간·전체 length는 해당 클립 길이에 맞췄다.
- 위 두 병종의 임의 Solo/Talk 후보 선택은 없어진다. 추가 Idle grants/옛 루틴 에셋은 호환성을 위해 남겨두며 일괄 삭제하지 않았다. Swordsman의 6루틴과 SwordShield의 Basic/Sit 2루틴은 유지한다. 배회 허용과 정지 대기 애니메이션의 선택은 기존처럼 별개의 정책이다.

Halberd 원본은 /Game/_Art/Enemies/HeinMach/Humanoids/HalberdElite/Animations/Playback/A_EN_PLAY_AC_EmpireHalberd_Basic_{Loop,End}_02이다. 각각 /Game/Monsters/HalberdElite/Animations/InGame 아래로 복제했다. GetPlayLength 저장 readback은 Loop 4.866666793823242초, End 2.633333444595337초이며 RateScale은 둘 다 1.0이다. 이는 현재 임포트 에셋 직접 관측값이고 원작 AI 전이 설정을 추출한 수치가 아니다. source/gameplay 길이·RateScale 일치와 기존 nav-driven EnableRootMotion=false/ForceRootLock=true/RefPose lock을 새 stock saved reload에서 확인했다. 원본 키/FPS/pose를 재임포트하거나 재생률을 바꾸지 않았다.

### 2. 플레이어 발견의 실제 호출 흐름과 값의 출처

1. AKZMonsterAIController 생성자가 기존 UAIPerceptionComponent/UAISenseConfig_Sight를 생성하고 OnTargetPerceptionUpdated→HandleTargetPerception을 연결한다. StartMonsterLogic은 실제 Monster의 AISettings로 SightRadius/LoseSightRadius/PeripheralVisionHalfAngle/MaxAge를 설정하고 StateTree를 시작한다.
2. 엔진 Sight가 거리·주변 시야각·가림/가시성 조건을 검사해 FAIStimulus를 전달한다. affiliation enemy/friendly/neutral은 모두 허용하지만 게임 콜백은 Cast<AKZPlayer>, IsPlayerControlled, 유효 Monster 조건을 모두 만족한 Actor만 채택한다. 단순 거리 하나만으로 발견하는 자체 함수가 아니다.
3. Stimulus.WasSuccessfullySensed()이고 기존 타깃이 없거나 같은 Actor이면 BattleTarget weak 참조를 저장하고 Gameplay Focus를 준다. 유효한 기존 다른 타깃을 임의 교체하지 않는다. 양쪽이 실제 Talk Loop 중인 상호 파트너라면 발견한 쪽이 같은 Player를 상대 Controller에도 전달한다.
4. Idle Task는 발견 후 기존 Command.AI.Alert Begin/Release로 자기 ComboAction의 대응 End를 요청한다. Spec이 inactive가 될 때까지 기다린 뒤 AlertedTarget을 표시하고 Root로 돌아간다. 따라서 준비 End를 끝낸 병종은 공통 Alert를 중복 실행하지 않는다. Patrol 도중 발견한 경우는 기존 Alert Task 경로를 사용한다.
5. 기존 Root 선택 우선순위는 Alert→Chase→Attack→Standoff→Patrol→Idle이다. Target 유효/준비 여부/거리/공격 방향·cooldown 조건에 따라 선택하고, 실행 중 Task 완료 시 다시 Root를 선택한다.

MainReadyAudit.json의 네 BP CDO actual settings는 SightRadius=1400cm(14m), LoseSightRadius=1800cm(18m), PeripheralVisionHalfAngle=90도(전체 180도), TargetMemorySeconds=4초다. LoseSightRadius는 엔진의 이미 보던 대상 시야 유지 반경이며 새 타깃 획득 거리와 구분한다. 이 값들은 기존 프로젝트의 임시 AI 튜닝값으로 원작 AIData field는 미확인이다. 이번에 신규 숫자를 선정하지 않았다. FK 보폭 기반 이동속도/원작 SB 공격 메타데이터와 이 Sight 설정을 혼동하지 않는다.

### 3. 한번 발견한 Player는 거리·시야 상실로 잊지 않는다

기존 Controller의 SightLostAt, bMemoryExpired, bOutsideLeash 및 해당 타깃 해제 경로를 제거했다. 실패 Sight stimulus는 sensory observation만 끝내고 BattleTarget을 바꾸지 않는다. Tick은 BattleTarget.IsValid()인 동안 Focus를 유지하고 실제 Player 위치를 기존 조건/Task에서 계속 읽는다. 시야 밖·장애물 뒤·기존 leash 3000cm 밖·4초 경과도 Idle 복귀 사유가 아니다.

TargetMemorySeconds는 UAISenseConfig_Sight.SetMaxAge의 sensory record 설정으로만 남고 BattleTarget의 수명을 결정하지 않는다. PursuitLeashRadius는 기존 직렬화 필드를 보존했지만 타깃 해제에서는 소비하지 않는다. HomeLocation은 미발견 Patrol 원점으로 계속 쓴다. Player Actor가 파괴되어 weak 참조가 무효가 되거나 Controller UnPossess/EndPlay가 발생하면 기존 cleanup에서 target/alert/focus/nav/intent/task를 정리한다. 별도 death 처리 시스템은 추가하지 않았다.

### 4. 선택한 대치/공격을 마친 뒤 재추격

Standoff Enter에서 기존 StandoffSeconds 범위의 TimeRemaining과 -1/0/+1 StrafeSign을 한번 선택한다. MoveGoal을 자기 위치로 초기화하고 Tick(Context, 0.f)을 호출해 해당 선택의 첫 local nav 목표를 즉시 확정한다. 기존 설정 StandoffSeconds=(1.0,2.5)초는 원작 미확인 임시 튜닝값 그대로이고 -1/0/+1은 좌/정지/우 배타 선택 표현이다.

이전 Standoff Tick의 거리 증가 또는 CanChooseAttack 즉시 Succeeded를 제거했다. 현재 TimeRemaining에서 DeltaSeconds를 빼고 만료될 때만 정상 완료한다. EngageDistance 안에서는 기존 ring goal 갱신으로 선택 방향·거리를 유지한다. 밖으로 나가면 기존 마지막 local MoveGoal을 마치며 남은 구간을 유지하고, 플레이어 이동에 따라 ring을 계속 옮겨 조기에 추격하지 않는다. 기존 nav 실패/idle retry는 동일 local goal을 대상으로 수행한다. 끝나면 OnStateCompleted→Root가 현재 조건을 다시 평가해 멀면 Chase를 선택한다.

Attack Task는 원래부터 자기 FGameplayAbilitySpec.IsActive()가 true인 동안 Running을 유지한다. 이를 유지해 단일/선택된 authored combo 실행이 종료된 뒤에만 다시 Chase를 판단한다. 신규 Chase cooldown/timer는 없다. 여기서 한 행동의 완료는 선택된 Standoff 구간 또는 Ability 수명 완료이며 locomotion clip 한 바퀴 완료로 정의하지 않는다. 유효 타깃 자체가 없어지거나 Controller 수명이 끝나는 cleanup은 기다리지 않고 수행한다.

### 5. 실제 검증과 메인 적용

- stock CombatPolicyPIE: 2026-10-07 06:32:02.734 UTC Success. 4종의 자연 Sight→대응 End, Heavy03/Halberd02 실제 montage segment, 선택한 대치 최소 구간 완료 후 Chase, sight/leash/memory 밖에서도 동일 Player/focus 유지 및 실제 재추격, retreat 중 Attack Spec 완료 대기, UnPossess cleanup을 검사했다.
- stock WaitingPIE: 06:43:56.397 UTC Success. 기존 Guard/Basic/Search/Sit Loop→End, mutual Talk 역할·마주보기, 파트너 상실 End→Solo, 한쪽 발견의 양쪽 전달/대응 End를 회귀 검사했다.
- 검사에는 기존 C++ development fixture를 사용했다. Python으로 이동/키입력을 주입하지 않았고 메인에서 자동 PIE를 실행하지 않았다.
- Main DeliveryManifest: 기존 Source 4개+package 5개=9개만 전달, prepared/delivered SHA256 일치. 신규 runtime 파일 0. FinalMainHashVerification: 미관련 89파일 전달 직전 대비 동일, protected_changed=[].
- Main stock cold build: 10actions/68.30초/Result: Succeeded. work DLL을 복사하지 않고 최신 Main Source를 직접 build했다.
- fresh MainReadyAudit: 06:51:21.279651 UTC, PID29556, /Game/Maps/DevMap.DevMap, 네 Monster BP BS_UP_TO_DATE, Heavy/Halberd Basic 단일 routine 및 03/02 실제 segment readback, PIE 없음, dirty content/maps 0. 사용자가 열린 DevMap에서 직접 Play할 수 있다.
- own final MonsterWork PID26036은 background throttle의 기존 true 값을 복구하고 06:46:57.243906 UTC 정상 종료했다. main 이전 PID8292도 clean/no PIE audit 후 정상 재시작했다. 다른 PlayerParts/Snow editor는 조작하지 않았다.

실패 이력을 보존한다. 초기 author mailbox가 asset save 중 Slate callback 재진입으로 같은 안전 저장을 반복한 것은 도구의 processing guard로 해결했다(AssetPreparation_Initial.json). 임시 author cpp 제거 직후 UBT cached source list의 C1083은 work-only project timestamp로 makefile을 재생성해 StockRefreshed build에서 해결했다. Waiting 첫 실패는 다른 테스트가 이미 발견한 Talk pair를 4초 뒤 잊을 것으로 가정하던 개발 fixture의 기존 정책 의존이다(WaitingPIE_LegacyFixtureFailure.log). 게임 정책을 되돌리지 않고 fixture의 Sight 범위/Actor-controller 수명을 개별 격리하고 원래 assertions를 유지했다. 성공/실패 모두 저장했다. 이를 production AI가 다시 타깃을 잊는 문제로 보고하지 않는다.

현재 증거: Metadata/MonsterCombatPolicy_20261007/{MainAppliedResult,DeliveryManifest,FinalMainHashVerification,MainReadyAudit,FinalSavedAudit}.json, CombatPolicyPIE_Success.log, WaitingPIE_Success.log, ColdBuild_Main.log. Scoped Before/Prepared manifests와 실패 로그도 같은 경로에 있다. 새 몬스터 피해/피격·원작 AIData 전체·전체 지형/연속 화면/네트워크 일치 검증은 이번 완료 범위에 없다.

### 6. 다음 확인/재개

열린 메인 DevMap에서 Play 후 DevAI_HalberdElite와 DevAI_HeavySwordsman의 고정 Loop→대응 End를 확인한다. 한 번 발견시킨 뒤 멀리 이탈해도 combat 유지/재접근을 확인한다. 좌·정지·우가 시작된 직후 멀어지면 해당 선택 구간 후 Chase, 공격 중 멀어지면 해당 Ability/선택 콤보 종료 후 Chase가 예상 동작이다. 새 증상이 있을 때 이 결과와 현행 Controller/StateTree Task를 기준으로 좁게 조사한다. 이미 완료한 authoring/full copy/retime/자산 전수조사 및 테스트 전체를 선행 반복하지 않는다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

아래 후속은 몬스터의 이전 RM=false/RefPose 계약과 imported animation 경로를 충돌 범위에서 대체한다.

ARCH-79 실제 완료다. 기존 StateTree/AISettings/CharacterDefinition grants/ComboAction/ComboDefinition/Montage를 재사용했다. runtime 새 파일·class·component·manager는0, 실제 gameplay Source는 KZMonster.h와 KZMonsterStateTreeNodes.cpp 두 파일이며 기존 development KZMonsterAIPIETest.cpp를 보완했다. Player/ASC/ComboAction 실행 코드를 재작성하지 않았다.

공격은13→35(Swordsman5, SwordShield3, Heavy7, Halberd20)이며 해당4종 Attack68클립을 모두 연결했다. finite 준비/loop/타격/회복은 같은 Action 안에서 필수 순서를 유지하고 실제 combo만 기존 held X/InputEnd로 잇는다. 신규 combo6개의 끝 경계 InputEnd 실패는 montage data에서 마지막 sample 이전으로 보완했다. 정확한 시간식과 원작 SB/file/field는 MONSTER_ATTACK_ROOT_MOTION_20261007.md 및 AttackExpansionPlan.json/AllSavedSkillAudit.json을 따른다. 원작 hit/guard 조건 producer나 피해/피격을 새로 구현한 것은 아니다.

현재 공격 선택에는 독립 RNG probability가 없고 거리/각도/cooldown gate를 쓴다. 기존 임시 interval2..4초를1.1로 나눠1.8181818..3.6363636초로, combo continuation .75→.85(+10percentage points)로 설정했다. 전체 공격 빈도의 정확한10%를 보장하는 통계 수치가 아니다. ChaseReactionSeconds .4초는 assistant 임시 tuning이며4BP AISettings에 저장했다. 선택 Standoff/Attack을 끝낸 뒤 Chase에 진입하고 기존 task TimeRemaining을 Enter에서 설정/Tick에서 감소시켜 nav 요청을 잠시 보류한다. 첫 Chase에도 적용한다. 타깃 유지/기존 cleanup을 보존한다.

stock SourceAnimationAudit813/18,958,755 raw transforms·곡선/선택 metadata 동일 Success; compressed root QA .01cm/normalized angular1e-4rad는 기술 허용 오차다. raw tolerance1e-6와 구분하며 실제 최대 압축 positional 차이.0060654cm였다. AttackPatternsPIE 최종35개/모든 section/actual root travel/HP 불변·취소 cleanup·네 종 실제 rechase Success. CombatPolicyPIE 네 종 선택 행동 완료/시야 밖 target 유지/.4초 nav hold/후속 물리 추격 Success, Waiting/Heal/Guard PIE Success. 최초 full Monster.PIE의32 방향보행/contact sample min11·median0cm/s는 통과했으며 montage notify만 보완한 뒤 중복 walk 검사는 반복하지 않았다. retreat fixture는 Root lunge로700cm를 따라잡는 문제와 nav 밖5000cm 배치 문제를 각각 보존하고, 최종8후보 projection+complete path 및 Chase 진입 이후 physical advance로 검사했다.

Main 선택 전달은 파일981개(기존69/신규경로912), 이름 변경 옛 파일802개를 정확한 path/hash guard 뒤 제거했다. backup Before와 실패 로그를 보존한다. 미관련 Source/Config86 및 Archer177개 hash를 보존했다. Main stock cold build Succeeded, fresh Main PID3528 /DevMap/4BP·ABP UP_TO_DATE/813 options·35 grants·68 clips/저장값 재확인/PIE없음/dirty0이다. 자동 Main PIE는 실행하지 않았다. Main에 사용자 직접 Play용 DevMap이 열려 있다. 최종 manifest와 증거는 Metadata/EnemyAnimationOrganization_20261007/FinalVerification.json, DeliveredManifest.json, MainReadyAudit.json을 따른다.

Main 최초 read-only 검사에서 DevAI_ label 접두사에 Navigation volume까지 포함해 actor수5로 실패했다. 4 BP/ABP·813 options 검사는 이미 통과한 상태였고, exact4family actor label로 QA 식을 고친 뒤 같은 fresh editor에서 전체 read-only 검사를 다시 통과했다. 실패 JSON/MainReload log를 보존했고 이 과정에서 게임 코드·map·asset save/PIE는 수행하지 않았다. raw tolerance의 정확한 값은1e-6이며 이전 Art 본문의 최초 .001cm 언급은 엄격한 compressed probe와 혼동한 설명이다. 최종 compressed .01cm와 raw 검사를 구분한다.
