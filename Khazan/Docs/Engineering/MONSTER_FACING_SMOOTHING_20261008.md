# NPC4 이동 보간·타깃 유지·공격 추적 회전

## 2026-10-08 — 요구와 구현 범위

사용자 직접 구현 요청이다. 현재 실제 AI가 연결된 Swordsman, SwordShield, HeavySwordsman, HalberdElite를 대상으로 한다. Yetuga/Apes의 library만 있는 상태를 신규 AI 구현으로 취급하지 않는다.

기존 StateTree → AIController의 타깃/이동 의도 → LocomotionComponent → CMC, ASC/ComboActionAbility → 몽타주, NPC ABP → BlendSpace/Foot Placement/Slot/Inertialization을 재사용한다. 새 runtime 파일/class/component/delegate/행동 상태 사본은 없다. 원본 시퀀스/Root track/재생률/Player의 .01 mesh를 재작성하지 않는다.

## 2026-10-08 — 실제 원인과 관측

별도 MonsterWork의 stock baseline build/CombatPolicyPIE4종은 통과했다. 실제 LLDB의 MirrorNavigationIntent:167에서 DevAI_Swordsman의 GA_Kick/Attack_Kick 실행을 정지해 다음을 확인했다.

- BattleTarget과 AlertedTarget은 같은 BP_Player0이다. 대치/공격 중 타깃을 시야 상실로 지우는 경로는 없다.
- CMC bUseControllerDesiredRotation=1이지만 bAllowPhysicsRotationDuringAnimRootMotion=0이다.
- 실제 RootMotionMontageInstance=Attack_Kick, RootMotionMode=RootMotionFromMontagesOnly다.
- Engine CharacterMovementComponent.cpp:3044–3057은 root montage가 있으면 위 허용 flag가 false일 때 PhysicsRotation을 생략하고 원본 root 회전만 적용한다. 따라서 타깃을 기억하면서도 몸은 플레이어를 따라 돌지 않을 수 있다.

증거는 Metadata/MonsterMotion_20261008/DebuggerBaseline.json 및 BaselinePIE.log다. baseline 정지 프레임 자체에서는 ControlYaw94.5868/BodyYaw94.5663으로 거의 정렬됐으며, 이 단일 값으로 회전 오차 증가를 실측했다고 주장하지 않는다. 실행 branch와 flag, 움직이는 타깃 후속 테스트를 구분한다. agent line breakpoint를 제거하고 사용자 exception8개의 상태를 보존했다. own baseline worker3672는 정상 종료했다.

대치 중에는 기존 유효 BattleTarget을 매 tick Gameplay focus로 유지한다. 이번 GetDesiredRotation은 CMC가 사용하는 시점의 현재 target location으로 yaw를 직접 계산하여 오래된 ControlYaw나 navigation Move focus를 공격/대치 조준의 원본으로 쓰지 않는다. 플레이어가 멀어졌을 때 선택한 행동을 마친 뒤 Chase로 전환하는 정책은 계속 유지한다.

## 2026-10-08 — 변경 책임과 함수

KZMonster 생성자는 CMC의 root montage 중 PhysicsRotation 허용을 켠다. 실제 capsule 회전은 기존 CMC가 수행하고, 원본 root translation/yaw는 엔진이 이후 합성한다. 공격의 추적 yaw만 제한하므로 원본 Turn 공격을 삭제하거나 root를 zero 처리하지 않는다. 비공격 root montage는 Controller의 desired yaw를 현재 body yaw로 반환해 기존 대기/발견 End의 원본 회전을 보존한다.

KZMonsterAIController::GetDesiredRotation() const는 엔진 virtual 계약을 보완한다. 파라미터는 없고 CMC가 사용할 FRotator를 반환한다. GT에서 현재 Pawn/weak BattleTarget/Locomotion policy/ASC의 AnimatingAbility를 읽으며 공유 상태를 쓰지 않는다. LockOn 이외에는 엔진 기본 경로를 반환한다. 유효 target이 정확히 같은 평면 위치이면 현재 몸 방향을 반환한다.

공격 판별은 ASC가 실제 재생하는 active ComboActionAbility의 class가 기존 Monster AttackAbilities에 포함되는지로 한다. 별도 bAttacking/node 사본/회전 타이머를 만들지 않는다. 일반 공격은 작은 yaw 속도로 추적하고, 첫 section의 준비 구간과 다음 콤보 InputEnd 직전에는 높은 속도로 재정렬한다. UKismetMathLibrary::FixedTurn은 현재 yaw와 target yaw의 짧은 각도 차이를 사용해 매 frame Rate × DeltaSeconds 이내의 desired yaw를 만든다. CMC의 원래 RotationRate도 상한으로 계속 작용한다. 공격 종료/취소/다른 montage/UnPossess에서는 조회 원본이 사라져 제한이 자동 해제된다.

KZComboActionAbility::IsApproachingComboTransition(float LeadSeconds) const는 실행을 변경하지 않는 파생 조회다. 인자는 실제 초 단위의 선행 준비 범위, 반환은 bool이다. 현재 node의 InputEnd edge가 현재 held command/기존 MatchesEdge 조건을 만족하고, 현재 montage/section에서 실제 InputEnd notify가 LeadSeconds 안에 도달하면 true다. Montage_GetEffectivePlayRate를 사용해 instance play rate와 Montage.RateScale을 함께 시간 변환한다. node jump/비용/취소/InputEnd 처리는 기존 함수를 그대로 사용한다.

이 조회는 앞으로 전환될 가능성을 읽는 것으로, 미래 비용 변경이나 commit 실패까지 미리 확정하는 함수가 아니다. ARCH-80의 첫 기록 중 “실패 edge에서 false”는 조건 불일치/비활성/montage mismatch 범위로 한정해 읽는다. 준비 중 조준이 더 빨라져도 실패한 전환을 강제로 실행하지 않는다.

## 2026-10-08 — 수치 출처

새 공격 회전값은 원작 AI field를 찾지 못했으므로 어시스턴트 임시 튜닝값이다. 기존 FKZMonsterAISettings의 Combat|Facing 한 곳에 모아 BP defaults에서 조정할 수 있다.

| 변수 | 값·단위 | 의도 |
|---|---:|---|
| AttackTrackingYawRate | 60 deg/s | 공격 중 움직이는 상대를 완만하게 따라감 |
| ComboReaimYawRate | 180 deg/s | 다음 공격 준비 중 더 빠른 조준 |
| AttackPreparationSeconds | .15 s | 실제 InputEnd 이전과 새 section 시작의 짧은 준비 범위 |

Rate × DeltaSeconds는 계산값이며 authored root yaw를 포함한 전체 body yaw 상한을 의미하지 않는다. 조정 기준은 실제 CMC root yaw를 분리한 연속 steering, 타깃 각도 오차, Turn/대시 공격의 원본 움직임 보존이다. 회전을 순간 snap하거나 기존 이동 RotationRate를 덮어쓰지 않는다.

이동은 4 Combat BlendSpace의 TargetWeightInterpolationSpeedPerSec만 기존0에서 원작 직접값으로 바꾼다. 각 원본은 Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/ 아래 해당 family/Moving/Move JSON이다.

| 현행 Combat BS | 원본 family/export | 직접 field·원시 값 |
|---|---|---|
| BS_Combat_Swordsman | EmpireSword/BS_EmpireSword_LockOnMove | Properties.TargetWeightInterpolationSpeedPerSec=6 |
| BS_Combat_SwordShield | Empire_SwordShield/BS_Empire_SwordShield_LockOnMove | 같은 field=10 |
| BS_Combat_HeavySwordsman | Empire_SwordHArmor/BS_Empire_SwordHArmor_LockOnMove | 같은 field=10 |
| BS_Combat_HalberdElite | EmpireHalberd_E/BS_EmpireHalberd_E_LockOnMove | 같은 field=5 |

단위는 sample weight/second이며 블렌드 시간이나 degree/second가 아니다. 원작 normalized XY+Stand 표본과 현행 Direction/Speed 표본 배치가 달라 원작과 동일 포즈를 보장하지 않는다. exact package/export/path/SHA/변경 전후는 CombatBlendSpace_workapply.json에 기록한다. 원본에서 누락된 InterpolationTime/ease를0/false로 추정하지 않았다.

현재 NPC ABP는 actual VelocityLocal XY의 yaw와 기준 Walk row/보행 PlayRate를 소비한다. 같은 Combat BS 안 방향 변경의 sample 보간을 추가하며 기존 상태 전환 관성화/Foot Placement/GT 평가를 재사용한다. 새 direction smoothing 멤버나 Main AnimInstance 계산은 추가하지 않는다. 저장 ABP의 function_graphs는 UE Python reflection에 노출되지 않아 readback_complete=false이며 ABP graph 검증 완료로 표현하지 않는다. 이번 ABP 저장은0회다.

## 2026-10-08 — 격리 검증 진행 상태

Work 경로: C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan. 현재 Main의 unrelated Snow Source3/Config2만 Work로 먼저 intake했다. 이번 owned Source7/BS4의 Main before SHA를 보존했다. 기존 10/7 전체 delivery script를 다시 실행하지 않는다.

FinalBuild.log는 Success다. 첫 compile 실패는 native test local AI shadow(C4458)였고 수정했다. native test의 Montage DataModel null 가능성은 GetSamplingFrameRate API로 고쳤다. 이후 UKismetMathLibrary 래퍼 적용/관측 phase 보완은 다음 최종 cold build에 포함해야 한다.

FacingPIE는 실제 Sight로 타깃 획득 후 StateTree만 중지한 QA fixture에서35개 기존 공격과 held 콤보를 실행한다. 초기 배치 이후 target인 player만 native C++로 이동시키며, 테스트가 몬스터 yaw/Focus/ControlYaw를 매 tick 설정하지 않는다. CMC의 기존 ProcessRootMotionPostConvertToWorld delegate를 변경 없는 관측 wrapper로 일시 연결하고 실제 소비 root quaternion을 body 결과에서 역합성해 추가 steering을 구분한다. 원래 delegate/actor transform/perception/controller 수명은 cleanup한다. CSV는 Saved/MonsterAI/FacingPIE.csv다.

pre tick의 montage position과 CMC의 TickCharacterPose 후 PhysicsRotation 시점은 다르다. 준비 구간 경계의 slow/fast 판정은 실제 root conversion 관측 시점에서 분류하여 test 오류와 runtime 오류를 구분한다. 완료/실패 로그와 CSV는 최종 절에 별도 기록하며, Main 반영·사용자 editor 새 코드 로드는 아직 완료로 기록하지 않는다.

## 2026-10-08 — 최종 회전 검증과 회귀 fixture 보완

최종 FacingPIE는 01:54:58 UTC Success다. 4종35공격/55node, CSV5,542행(active5,497), 실제 post-pose phase 유효5,240행을 관측했다. root를 제거한 추가 steering에 대해 slow60×dt+.25deg 및 max180×dt+.25deg 기술 QA 허용 범위의 위반은0이다. phase 미관측257행은 원래 정책대로 max만 평가했다. fast362행 중331행에서 slow bound보다 빠른 steering을 관측했다. pre-tick 기준만 썼다면 오판할19행은 실제 PhysicsRotation phase에서는 fast였으며 첫 실패 run의17경계 프레임과 별도 기록이다. .25deg는 원작 튜닝값이 아니라 frame/quaternion 역합성 관측의 기술 허용 오차다.

Halberd 원본 Turn 포함 패턴7/18/19에서는 소비 absolute root yaw540.002/180/180deg가 관측됐다. root 이동/회전을 삭제해 조준만 남긴 결과가 아니다. 원본 로컬 root quaternion을 mesh world basis로 변환해 원본의 pitch/roll 축이 월드 yaw로 나타나는 경우도 판정했다. 이 검사는 runtime 원본 root 소비를 확인하며 원작 package/raw-key 전수 동일성 재감사가 아니다. exact 통과 Source6/해당 test 전체/module/log/CSV는 FacingPassedProof.json과 FacingSummary.json에 보존했다.

첫 Monster.PIE는32방향 포즈/contact·35공격 section/root travel·cleanup 검사가 통과했지만 마지막 Swordsman의 최초 무인지/Alert 관측 두 assertion으로 Fail이었다. 이 actor는 자기 검사 전 이미 Loop→End와 combo를 실행했다. 원인은 가족별 시험의 비격리이며, 정확 최초 Sight 이벤트/좌표가 없어 특정 retreat 좌표를 단정하지 않는다. development-only FMonsterPIECommand에 원래 Sight enable 상태 저장/해당 가족만 enable/완료 뒤 disable/cleanup·destructor 복구를 추가했다. assertion을 완화하거나 gameplay 타깃 기억을 지우지 않았다.

격리 수정 후 IntegratedFinalBuild.log는 Succeeded(23.45s)이며 별도 own16676에서 전체 Monster.PIE를 다시 진행한다. Facing class부터 파일 끝30,434bytes 및 runtimeSource6는 통과 당시와 동일해 이전 성공을 같은 구현의 근거로 재사용한다. 이전 DLL에서 수행한 Facing 결과를 이 fixture-only 재빌드 DLL에서 재실행했다고 주장하지 않는다. 새 Main의 loaded alias/CDO/저장값/native 통합 검증과 전달 결과는 다음 완료 절에서 구분한다. 실패 원본은 Monster_First.log이며 Main 전달은 아직 전이다.
## 2026-10-08 — 최종 작업본 검증 완료, Main 반영은 파일 잠금 대기

실제 적용 위치는 Khazan_MonsterWork_20261006/Khazan이다. 게임 런타임은 기존 Source6 파일만 보완했고 새 runtime 파일/class/component/상태 사본은 없다. 기존 development test2개가 변경되어 전달 소유 Source는8개다. Combat BlendSpace4와 기존 mailbox1을 포함한 최종 전달 대상은 DLL/PDB/manifest까지16개다. Main 게임 Source/BlendSpace/DLL/manifest 반영은 아직0이며 Delivery.json도 없다.

사용자가 동시에 저장한 SpinningAttack h/cpp 및 ComboAction의 DoJump800/DoDown-500 코드는 현재 저장본 그대로 보존했다. Main→Work 공통 ComboAction의 우리 차이는 const IsApproachingComboTransition 조회 추가뿐이다. 원작 수치 또는 어시스턴트가 정한 값으로 사용자 LaunchCharacter 숫자를 재분류하지 않는다. 관련 없는 Snow Source/Config와 PlayerParts의 Main Leg 변경도 되돌리지 않았다.

최신 사용자 코드와 병합한 c2a575f25fb9d107825b67ce00a14ec3c35a5e53cc7d417915e6c3839d2ac3f5 DLL에서 FacingPIE는02:57:16.698 UTC Success, CombatPolicyPIE는03:00:44.909 UTC Success, Guard.PIE는03:10:18.987 UTC Success다. FacingSummary_Merged.json은1,167행/active1,128,35공격/55node, post-pose 유효1,058행, slow/max 추가 steering 제한 위반0을 기록한다. phase 미관측70행은 max만 검사했다. fast66행 중60행에서 slow bound를 넘는 준비 회전을 확인했고4종 wrap/slow/fast/normal 복귀가 모두 통과했다. 원본 Halberd Turn root yaw540.002/180/180deg도 보존됐다.

32방향 보행/35공격/자연 Sight·대치·재추격 검사는 앞선 c060 DLL의02:24:03.446 UTC Success이며 MonsterSummary.json/Monster_Final.log에 별도 보존했다. 실제 contact sample 최소5, 보고된 median slip 최대0.000cm/s다. 이는 정상 보행의 계산된 ankle contact 검사이며 전환 전체·모든 발바닥 정점·임의 지형의 육안 품질 보장을 뜻하지 않는다.

Heal 추가 회귀는 기존 고정 observer 시각에서 Armed instance 또는 이전 실행 active assertion이 간헐 실패했다. 실패3개 log와 Heal_DebugFixture.json/log를 보존했다. 디버거 재현에서는 case8 bIsActive=false/BoundAnimInstance=null/실행ID=-1로03:18:19.908 UTC Success였으므로 과거 실패 당시의 정확 상태/원인을 직접 재현했다고 주장하지 않는다. Player 제품 코드는 수정하지 않았다. 기존 개발용 Heal 검사만 Stage4의 기존 실제 Draw position>.6 capture와 같은 frame에 포즈를 검사하고, Stage5/8은 실제 자연 종료를 기다리도록 보완했다. 기존 모든 assertion과60초 deadline은 유지했다. .6/60은 이미 있는 QA 조건이며 새 gameplay 튜닝값이 아니다.

이 test-only 수정 후 cold build19.78s Succeeded, 최종 DLL은 a6bed111a0f59ae2ce46cb8978a6e1582e17dd3730c13bfdfbfb5ee8aadd49d7이다. 이 DLL을 실제 로드한 별도 editor25368의 Heal.PIE는03:25:43.152 UTC Success다. 런타임 Source6과 전체 Monster test는 직전 c2a 통과본과 byte-identical이며 기존 Facing/Policy/Guard를 이 새 DLL에서 다시 실행했다고 표시하지 않는다. 정확 모듈별 결과는 VerifiedDeliveryProof.json에 분리 기록했다. Snapshot91 파일, 비소유 Source78/Config5의 동일성 및16개 대상 preflight가 통과했다.

별도 editor17772/25368은 모두 정상 quit했고 메모리 throttle을 복원했다. debugger session 및 agent breakpoint도 제거했다. 사용자 Main13700은 조작/종료하지 않았다. MainAssetLock_Final.json의 read-only Windows Restart Manager 조회가 BS_Combat_Swordsman.uasset의 잠금 소유자13700을 확인한다. 이전 WinError5 전달은 첫 asset에서 중단돼 rollback/새 alias 모두 비어 있다.

남은 절차: 사용자 Main 작업 저장·종료 → 현재 Source/Config/BS/before hash를 다시 확인(사용자 새 변경이 있으면 보존/재병합·build) → deliver_monster_facing_20261008.py preflight/deliver → 실제 Delivery.json16hash 및 alias 확인 → 별도 새 Main editor에서 verify_monster_facing_main_20261008.py로 loaded DLL/CDO/저장 BS4/dirty0 및 Facing·CombatPolicy·Heal·Guard4 native 검사 → own quit → Main 반영·검증 결과를 별도 append. 이전 전체 몬스터 authoring이나 과거 전체 delivery를 반복하지 않는다.



<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

앞선 파일 잠금 대기 전달은 이번 MonsterStamina 통합으로 완료됐다. 과거 전체 후보 파일/Heal test를 덮어쓰지 않고 최신 Main의 NPC4/ComboAction에 필요한 추적 회전/const query와 Facing dev class만 추가했다. BS4도 최신 Main을 먼저 읽어 원작 TargetWeightInterpolationSpeedPerSec6/10/10/5 한 필드만 수정했다. MotionMerge.json과 LatestCombatBlendSpaceAuthoring.json이 병합·수치 근거다.

실제 attack 동안 FixedTurn 추가 steering60deg/s, 다음 combo 준비180deg/s와 .15s는 어시스턴트 임시 튜닝이며 원작 확인값이 아니다. root 회전을 삭제하지 않고 CMC bAllowPhysicsRotationDuringAnimRootMotion=true로 bounded 추가 steering을 함께 처리한다. 소진 중에는 공격 steering을 제외하고 AI는 자기 reaction Pause 소유권만 Resume한다.

최신 통합 tested Source에서 FacingPIE35공격/55node와 CombatPolicy/Guard/Heal/Collision이 모두 Success다. 원본 Halberd root yaw540.002/180/180도 유지됐다. stock에서 temporary author/test3를 제외한 DLL을 Main 선택 manifest로 반영했고 별도 fresh Main16924가 BS4저장값·BP/ABP up-to-date·실제 CDO 설정·loaded module SHA·dirty0를 확인했다. 근거 Metadata/MonsterStamina_20261008/{IntegratedRegression,DeliveryReceipt,MainSavedReload,FinalVerification}.json이다.

과거 full Monster.PIE의32방향/contact 결과는 당시 Work proof이며 이 latest 통합에서 같은 full test를 다시 실행했다고 주장하지 않는다. 이번 전달의 test 파일은 기존 Main body를 유지하고 Facing class만 추가했으므로 이전 Sight 격리·Heal observer 보완 파일을 재전달하지 않는다. 최종 scope와 추적 회전 조건은 현재 Source를 기준으로 한다.


<!-- MonsterStaminaConcurrentMainBuildVerified_20261008 -->
## 2026-10-08 17:39 KST — 후속 Main 기본 DLL 빌드 보존·재검증

전달 완료 뒤 본 작업이 시작하지 않은 Main native build가 새 canonical DLL과 manifest를 만들었다. 해당 build는 Succeeded이고 선택 모듈은 현재 `UnrealEditor-Khazan.dll`, SHA `3a2b4942da22fdf94cc7cf6581da3b5fb04f63475315c675d66ef6c4782e758d`다. 이전 unique alias 전달·canonical 보존은 당시 사실이며 현재 모듈 선택을 과거 alias로 되돌리지 않았다. 전달105행과 전체 Source/Config가 검증한 현재 구현과 동일한 것을 확인했다.

별도 fresh Main commandlet에서 현재 canonical DLL을 실제 로드해 저장 Definition6+Player1/montage20/sequence49/attackBP35/body2 및 NPC4 BS·CMC/AI CDO·dirty0를 다시 확인했고 exit0으로 종료했다. 증거는 Metadata/MonsterStamina_20261008/{ConcurrentMainRebuild,FinalVerification_CurrentMain,MainSavedReload_ConcurrentBuild}.json과 ConcurrentMainBuild.log다. 이 새 DLL에서 native453/회귀5종을 다시 실행한 것은 아니며 동일한 제품 Source의 이전 Work runtime 결과와 새 Main saved readback을 구분한다. 사용자 Main19576은 읽기 inventory로만 확인했으며 제어·PIE·저장·종료하지 않았다. 이제 현재 Main 기본 DLL을 사용하고 과거 전달/authoring helper를 재실행하지 않는다.
