# 피격·방패 방어·브루탈 어택 실행 정본

## 2026-10-08 — 구현 중 계약

Main 전달과 이번 작업 PIE 검증은 아직 완료되지 않았다. 실제 완료/실패 결과는 날짜별 후속 절과 `Metadata/CombatReaction_20261008` receipt로 판단한다. 원본 에셋 분류는 [Art 감사](../Art/COMBAT_REACTION_ANIMATION_AUDIT_20261008.md), 방패 원본 근거는 [SwordShield 연구](SWORDSHIELD_GUARD_RESEARCH_20261008.md)를 따른다.

### 책임과 데이터

`FKZAttackCollisionWindow::HitReaction`은 공격 데이터의 종류(None/Short/Knockback/Launch)다. 작성자는 에디터, 소비자는 기존 ComboAction이다. HP/Stamina 절대 피해와 별개다. 0 피해량의 승인된 접촉도 피격 애니메이션을 재생할 수 있으며 조건부 혈흔 VFX는 기존 실제 음수 HP 피해 계약을 유지한다. 공격 원소에 종류가 표시된다. 공격자 방향은 일반 피격 선택에 쓰지 않는다.

`FKZHitReactionSettings`는 CharacterDefinition의 정적 몽타주 pool이다. ShortHits/Knockbacks/Launches/ShieldBlocks에서 null을 제외하고 균등 무작위 선택한다. 일반 종류가 비었으면 Short fallback이다. 방향별 이름은 후보를 식별하는 용도다. pool을 조회하고 포즈 실행을 소유하는 단일 `UKZHitReactionAbility`를 Player/Enemy가 같이 부여받는다. 별도 피격 manager/상태 컴포넌트를 만들지 않는다.

기존 `UKZComboActionAbility::QueryAttackCollision`이 현재 두 faction(Player→Monster, Monster→Player)에만 같은 형상·sweep·window/group별 적중 dedup·피해 GE를 적용한다. 승인된 피해 적용 뒤 `AKZCharacter::PlayHitReaction`이 ASC event를 보낸다. 인자는 반응 종류와 공격자다. 공격자는 event의 출처이며 방향 판정용 입력이 아니다. None/Dead/Exhausted/HP0/몬스터 Stamina0은 일반 반응을 시작하지 않는다. HP0·Stamina0의 실제 처리와 브루탈 짝 완료는 기존 Monster/Exhaustion 실행에 남는다.

### 실행 수명

HitReaction Ability는 캐릭터별 인스턴스이며 정확한 네 event로만 시작한다. `State.HitReacting`, 입력/스태미나 재생 제한을 실행 중 소유하고 기존 Action을 취소·차단한다. 재피격은 자기 실행을 취소 후 새 몽타주로 시작한다. 랜덤 선택은 게임 스레드에서 이 시점에 한 번 한다. 몽타주 section chain의 실제 Task 완료에서 복귀하며 blend-out 시작을 완료로 오인하지 않는다.

회전 제약은 LocomotionComponent의 기존 원인별 handle을 취득·반납한다. 캐릭터 상태 bool을 따로 복제하지 않는다. 공중 mode를 바꾸면 자기 소유권과 이전 mode를 기록하고 실제 착지/완료/취소/실패에서 정리한다. montage instance/sequence/mesh/avatar/ASC 검증을 통과한 `HitLand`만 착지 신호로 받는다. 다른 원인이 바꾼 movement mode를 되돌리지 않는다. 종료/실패/UnPossess/EndPlay에서 Task·delegate·몽타주·제약을 정리한다. 같은 Ability가 동기 callback으로 다시 시작한 실행의 자원을 오래된 callback이 정리하지 않게 실행 ID/instance를 검증한다.

Monster의 `State.HitReacting`을 기존 combat incapacitation 조회에 포함해 StateTree Pause/Resume 경로가 target을 유지한 채 대기한다. HP0/소진 처리가 먼저 기존 일반 피격을 취소한다. Player stamina0은 Monster 소진 정책을 적용하지 않는다. 플레이어의 별도 사망 시스템 전체를 이번 피격 구조로 새로 만들지 않는다.

### ShieldMan

현재 프로젝트 family 명은 `SwordShield`다. CharacterDefinition에서 `bSystemGuardOnLockOn`을 켠 종만 passive 방어를 한다. 원본 Battle LockOn Move의 SystemGuardFrontAngle180을 full cone으로 소비하는 것은 native 해석 미확인 adapter다. 전방 각 안의 blockable 공격만 HP를 막고 기존 window의 조정 가능한 StaminaDamage를 소모한다. GuardStaminaConsumeRate1.8과 ActiveGuard FrontAngle60을 같은 값으로 섞지 않는다.

`FKZComboNode::SystemGuardWindows`는 node-local 재생 초의 X=start/Y=end 구간이다. 현재 node/몽타주/section을 검증한 뒤 section 시작을 뺀 실제 시간을 조회한다. 별도 timer/state 사본을 만들지 않는다. 현재 active Action이 있으면 이 authored 방어 구간만 허용한다. 일반 발견 전 움직임은 방어하지 않는다. 방패 반응 Hit→End 중에는 현재 `IsShieldReaction()` 실행이 재차 방어를 허용한다. 피격 재차 무작위 반응과 HP0/소진 우선순위를 유지한다. incoming attack의 bBlockable=false는 우회한다.

Player Guard success의 Suc_F/Suc_L/Suc_R 균등 랜덤은 기존 `UKZGuardAbility::TryGuardHit`에 이미 구현되어 있어 중복 코드를 추가하지 않는다.

### 브루탈 어택

이미 있는 `UKZBrutalAttackAbility`와 `UKZExhaustionAbility`를 재사용한다. Player X의 기존 대상 선택→victim claim→Start/Attack1/Attack2와 대응 Damage1/Damage2→양쪽 실제 완료→생존한 victim End 완료에서 MaxStamina 회복 순서다. HP 피해50은 사용자 지정 임시값으로 CharacterDefinition6개의 `BrutalHPDamage`에 설정되어 있으며 Hit2에서 한 번 적용한다. 방향별 victim montage는 이 짝 실행을 유지하기 위한 앞/뒤 구분이다. 일반 피격 무작위 방향 정책으로 브루탈 짝을 섞지 않는다.

즉시 위치 teleport 대신 원본 Grapple Start MoveTo의 trigger .03356초, Duration .433283초, CubicInOut를 참고한 capsule sweep 접근을 사용한다. `BrutalAlignmentSeconds`는 조정 가능한 Definition 설정이며 단위 초다. native 목적지350/near75를 최종 spacing이라고 확정하지 않는다. 목적지는 기존 양쪽 live capsule 반경 합과 설정 간격을 따른다. 메시 .01 배율은 actor 좌표에 다시 적용하지 않는다. 벽에 막히면 기존 짝 취소 경로로 안전하게 정리한다. 접근 timer는 이 Ability 실행만 소유하며 완료/취소에서 제거한다. Hit2로 HP0이 된 짝을 접근 구간 이후 임의 중단하지 않는다.

### 검증과 조정

일반 반응은 pool membership·실제 chain 완료·Action 취소·재피격·원인별 제약 복구를 확인해야 한다. 공중 반응은 root/물리 이동 여부와 착지 뒤 capsule/CMC mode까지 확인한다. Guard는 전후 각·active attack 방어 구간·반복 방패 피격·스태미나0과 unblockable을 검사한다. 브루탈은 앞/뒤 접근·막힘·취소·50 1회·양쪽 완료·생존 회복·치사 반응 유지를 검사한다. 단순 에셋 옵션이나 animation preview 확인만 PIE 성공으로 기록하지 않는다.


## 2026-10-08 — In-place 피격의 실제 이동 경로 추가

별도 Work commandlet에서 Player Air F/B의 true skeleton root C_P_Kazan/index0/track0과 child Root 모두 이동0을 확인했다. 순서/누락/다른 Root의 이동 전사 문제가 아니다. Swordsman Up의 Bip001 이동은 포즈이며 world root로 임의 전사하지 않는다. 근거는 Metadata/CombatReaction_20261008/PlayerSourceRootReadback.json 및 InPlaceReactionRootAudit.json이다. `unreal-root-motion-repair`는 읽기 진단에만 적용했고 root/골격을 재구성하지 않았다.

이런 클립은 플레이 중 실제 날림을 별도로 구동해야 한다. 새 물리 component/helper 대신 HitReaction 실행에 엔진 UAbilityTask_ApplyRootMotionJumpForce의 RootMotionSource를 소유한다. Short/방패/미지원 Giant Short fallback은 이 이동을 만들지 않는다. 지원하는 Knockback은 수평, Launch는 수평+수직 곡선이다. duration은 실제 몽타주의 반응→Land/Getup 시각에서 가져오고 새 gameplay timer 수치를 만들지 않는다. CMC는 anim root motion을 RootMotionSource보다 먼저 적용하므로 자기 force 중에는 AnimInstance IgnoreRootMotion을 소유하고 완료/취소에 이전 mode를 복구한다. 원본 클립 옵션/track/rate는 보존하고 InGame 복제의 root 옵션만 실제 기존 template 정책으로 켠다.

CharacterDefinition HitReactions의 KnockbackDistance250cm, LaunchDistance120cm, LaunchHeight150cm는 어시스턴트가 선택한 임시 튜닝값이다. 원작 absolute 거리/높이로 확인한 수치가 아니다. 캐릭터 종마다 조절할 수 있고 실제 capsule 이동·벽 sweep·착지/기상 완료·과도한 이동 여부로 검증한다. 숫자를 여러 함수에 흩어 넣지 않는다. 일반 Monster Attack Window HP10/Stamina5도 원작 절대 피해량 환산이 미확인인 임시 설정으로 기존 window 데이터에 모아 조절한다. Player 기존 피해값은 임의 변경하지 않으며 승인된 접촉의 애니메이션 반응은 피해0에서도 가능하다. 원작 raw knockback curve/힘·거리 필드와 프로젝트3종 분류는 구분한다. 아직 이 force의 build/PIE 완료가 아니다.

## 2026-10-08 22:20 KST — SwordShield 뒤 브루탈 접근 충돌 진단·수정 검증 전

이번 CombatReaction 계약은 동시 MonsterVFX의 ARCH-84와 구분하여 ARCH-85다. Root가 소유한 Work PID29476의 LLDB에서 `KZBrutalAttackAbility.cpp:163`, GameThread의 next-tick delegate → `UpdateAlignment`를 정지해 확인했다. sweep 결과 `Hit.Distance=0.0760849342cm`, `Hit.Time=0`(초가 아닌 sweep 비율)이고, `Hit.HitObjectHandle.ReferenceObject=0x000001f61f320000`은 `BP_Monster_SwordShield1`로 해석됐다. `AlignmentTarget`도 정확히 같은 포인터였다. 최적화 때문에 `Hit.GetActor()` 호출은 불가능했으며 직접 handle 값으로 짝 피해자가 충돌 대상임을 확인했다. 별도 `Hit.Component`/초기 침투 flag 관측까지 주장하지 않는다. 정확한 값·관측 한계·정리는 [DebuggerShieldBack.json](../../Metadata/CombatReaction_20261008/DebuggerShieldBack.json)에 기록했다.

현재 코드의 valid blocking hit는 기존 montage abort/짝 취소로 이어진다. 수정 계획은 기존 `UKZExhaustionAbility`의 짝 수명 안에서 양쪽 live capsule에 상대 Actor만 `IgnoreActorWhenMoving`으로 등록하는 것이다. claim 전 `GetMoveIgnoreActors` membership을 확인해 없던 방향만 추가하고, 약한 원래 소유자 참조와 자기 추가 여부만 보존한다. 정상·취소·사망·End cleanup에서 자기 entry만 제거하며 외부 Abort/Super 호출 전에 receipt를 비워 새 실행을 오래된 cleanup이 건드리지 않게 한다. 벽·world 충돌, 접근 거리/시간, 피해50과 양쪽 실제 완료 후 생존 회복은 유지한다. 이 보완은 기존 Exhaustion h/cpp2개의 수정이며 새 class/파일이 아니다. 전체 전달 runtime 범위는 신규 HitReaction2+기존14=16파일로 늘어난다. **이 진단 기록에서는 수정 적용·빌드·PIE·Main 전달 성공을 아직 확정하지 않는다.**

별도 fresh Work PID23920의 저장 readback은 654,552검사/실패0/미지원0으로 통과했다(`WorkSavedReadback_PrePIE02.json`). pool/grant7, montage63/계획65, Loop 잘림16, 실제 raw 동일 Player 복제24, source245, Guard3/9, 충돌36 Definition/113구간/1498key와 Monster 종류109Short·2Knockback·2Launch를 확인한 범위다. 이 저장 검사를 새 짝 충돌 수정의 runtime 검증으로 재사용하지 않는다. 다음은 reciprocal ignore의 actual membership·기존 one-way entry 보존·자연 완료/취소 cleanup과 SwordShield back pair3 재검사, 전체 PIE·회귀, stock/fresh Work/Main 검증이다. 원본 giant NoAir/NoBlow의 fallback 참조는 면역 근거가 아니다.

## 2026-10-08 — Player 저장 피해량 정정: 기존 HP10/Stamina5 보존

Player의 실제 저장 에셋 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`은 `Nodes[].AttackWindows[].HPDamage=10`, `StaminaDamage=5`다. 기존 fresh Main PID2512의 [MainFreshSavedReadback.json](../../Metadata/PlayerAttackCollision_20261008/MainFreshSavedReadback.json)은 UTC `2026-10-08T06:55:14.270737+00:00`, 성공/에셋 저장 없음으로 18개 공격 노드·60개 window·553개 key와 모든 window의 실제 10/5를 확인했다. 구조체 선언의 기본값0을 이미 할당된 에셋 값과 혼동한 초기 “Player 피해0 보존” 설명은 이 기록으로 정정한다.

[AuthorReport.json](../../Metadata/PlayerAttackCollision_20261008/AuthorReport.json)의 `after_sha256`, [BeforeAuthor.json](../../Metadata/CombatReaction_20261008/BeforeAuthor.json)의 Main/Work 전달 전 SHA, 이번 확인 시점의 Main 해당 uasset SHA는 모두 `0ea30c0dda465ff6594036cff1c48151e44c721f0ceffda08c6956c4c429188b`다. 따라서 10/5는 CombatReaction 작성 전에 이미 저장되어 있던 값이다. Collision author는 기존 window를 복사한 뒤 `HitReaction`과 출처 설명만 변경하여 이 피해량을 보존한다. [CollisionAuthoring_Final.json](../../Metadata/CombatReaction_20261008/CollisionAuthoring_Final.json)과 fresh Work [WorkSavedReadback_PrePIE02.json](../../Metadata/CombatReaction_20261008/WorkSavedReadback_PrePIE02.json)도 Player60개 window 모두 10/5를 확인했다. 이번 작업에서 Player 피해량을 새로 10/5로 설정했다는 뜻이 아니다.

HP10/Stamina5의 원래 사용자 선택 여부 및 원작 절대 피해량 근거는 미확인이다. “승인된 피해0 접촉도 반응할 수 있다”는 Ability의 유효한 정책 설명은 유지하지만, 현재 Player 에셋이 피해0이라는 관측으로 해석하지 않는다. 이 정정은 문서만 변경하며 게임 소스·충돌 geometry/timing·애니메이션·저장 에셋을 변경하지 않았다.

## 2026-10-10 — ARCH-85 현재 적용 범위·미완료 검증 정정

Work에는 피격/SystemGuard/브루탈 접근 구현과 짝 capsule ignore cleanup 보완까지 실제 적용돼 있다. 기존 Exhaustion의 짝 수명에서 양쪽 상대 Actor만 이동 ignore에 등록하며 기존 entry는 보존하고 자기 추가분만 정상·취소·실패 정리한다. 10-08 22:20의 “수정 계획/검증 전”은 당시 기록으로 유지하고, 현재 [NativePIE_Final.json](../../Metadata/CombatReaction_20261008/NativePIE_Final.json)의 실제 RHI 피격32·브루탈15·충돌3case 성공으로 해당 Work runtime 검증 상태를 보충한다. 피해50·양쪽 완료 후 생존 MaxStamina 회복·벽에 의한 취소를 검사한 범위이며 원작 pose/contact 완전 일치나 멀티플레이 검증은 아니다.

현재 Main에는 이 작업의 runtime16개·asset130개를 아직 전달하지 않았다. 기존 Guard/Heal/PlayerAttackCollision 회귀 성공 이후 Monster.CombatPolicyPIE의 Heavy stage4/5 timeout을 조사하다 중단됐다. 이를 해결하고 전체 회귀 성공→임시 helper3개 제거/stock Build.cs 복원→stock build→fresh Work 저장 재로드→최신 Main CAS 선택146파일 전달→fresh Main actual module/readback이 남아 있다. [재개 감사](../../Metadata/CombatReaction_20261008/ResumeDriftAudit_20261010.json)는 현재 Main drift0와 Work Source106/DLL snapshot 동일만 확인했고 런타임 검증을 새로 실행하지 않았다. 중단 editor의 뒤늦은 GPU device removed는 행동 정책 timeout의 확인된 원인이 아니다. 정확한 process/증거/재개 절차는 [Engineering continuity의 2026-10-10 절](ENGINEERING_WORK_CONTINUITY.md)을 따른다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — ARCH-85 Main 반영·최종 검증 완료

이 작업의 이전 Work-only/회귀 조사/stock build·Main 전달 대기 상태를 아래 실제 완료 결과로 보충한다. runtime16개(공통 HitReaction 신규 h/cpp2개와 기존14개), 에셋130개를 Main에 선택 전달했다. 별도 피격 Manager/Component/FSM은 추가하지 않았다. 기존 Combo collision/GE/ASC event/AbilityTask/Locomotion constraint/CharacterDefinition 및 Exhaustion·Brutal 실행을 재사용한다. 최종 증거는 [FinalVerification.json](../../Metadata/CombatReaction_20261008/FinalVerification.json), 실제 변경은 [RuntimeChanges.patch](../../Metadata/CombatReaction_20261008/RuntimeChanges.patch), 사용·조정 설명은 [UserGuide](../../Metadata/CombatReaction_20261008/UserGuide_20261010.md)의 최신 완료 절이다.

일반 피격은 공격 window의 Short/Knockback/Launch를 받아 해당 종의 비어 있지 않은 후보에서 랜덤 재생한다. 방향은 입력 공격각으로 고르지 않으며 물리 이동 방향은 공격자에서 멀어지는 방향이다. 지원되는 날림은 반응→착지→Down Loop→Getup을 같은 몽타주 수명으로 완료한다. In-place 원본의 이동은 engine RootMotionSource가 소유하며 종료·취소·재피격·사망·소진·UnPossess에서 자기 이동/루트모션/회전 제약을 정리한다. Main7 Definition에 공통 피격 grant/pool과 조정 가능한 world cm 설정이 실제 저장됐다.

SwordShield는 발견 후 전방 passive guard와 authored active-node guard window를 구분한다. 방어 성공은 HP 피해를 막고 해당 공격 window의 StaminaDamage를 소비하며 0이면 소진이 우선한다. 원본 FrontAngle180의 full-cone 해석은 native 확인이 안 된 프로젝트 adapter다. Player Guard의 기존 Suc_F/L/R 랜덤을 그대로 사용했다. Player 일반 공격의 저장 HP10/Stamina5는 변경 전 에셋의 실제 값을 보존했다. Monster35 공격의 HP10/Stamina5·blockable=true, Knockback250cm/Launch120cm·높이150cm, Down Loop0.3초 및 Monster 종류109Short/2Knockback/2Launch의 네 날림 window 선택은 어시스턴트 임시 설정이며 원작 절대값으로 주장하지 않는다. 기존 Definition/window에서 조절한다.

브루탈은 게임패드 X/기존 약공격 입력의 기존 우선 요청 경로를 사용한다. 소진 대상 claim→점진 capsule sweep 정렬→앞/뒤 짝 공격과 피해 반응→Hit2의 HP50 1회→양쪽 실제 완료→생존 대상 End 완료에서 MaxStamina 회복 순서다. 50은 사용자 임시 결정이다. 원본 MoveTo trigger0.03356초/Duration0.433283초와 CubicInOut을 참고하며 목적 간격은 live capsule와 기존 설정을 사용한다. .01 메시 배율을 actor 이동/시간에 다시 적용하지 않았다. 대상 capsule에 막히던 문제는 Exhaustion의 full-pair 수명에서 필요한 reciprocal move-ignore만 추가해 해결했다. 사전 entry는 보존하고 자기 추가분만 복구한다. 벽은 계속 sweep을 막고 짝 취소/cleanup이 실행된다.

실제 RHI native 검사는 피격32·브루탈15·Monster→Player 충돌3case, 1,066 assertion, 변형26종 및 캡처7장을 통과했다. 앞/뒤6종·접근 취소·벽·치사·50 1회·양쪽 완료·회복·사전 one-way ignore 보존·일반 반응 재진입·실제 이동/CMC 복구·Shield/Guard 경계를 검사했다. 새 PID23912의 Guard/Heal/PlayerAttackCollision/CombatPolicy stock 회귀4개도 실제 engine Success이며 인간4종 완료를 확인했다. 과거 Heavy 정책 timeout은 fresh debug run과 undebugged run에서 재현되지 않았고 원래 원인은 미확인이다. 그 실패를 이유로 제품 AI를 임의 수정하지 않았다. 뒤늦은 GPU device-removed와 timeout의 인과도 확인하지 않았다. 실패와 디버거 로그는 보존했다.

임시 author2/test1은 SHA 확인 후 archive하고 Work Source에서 정확3개만 제거했다. Build.cs는 Main의 정확 bytes로 복원했다. stock build Succeeded(5.19초), Source/Config103개는 전용 PIE 당시와 임시3 제거/Build.cs 복원만 다르며 production16개는 동일하다. 최종 stock DLL SHA는 `74a069363f9100a4784ac03a4941214f0a98f732b4dc296d3f7198c7e62d2983`이다. 전체 RHI 결과는 동일 production source의 helper 포함 이전 DLL에서 수행했고, 최종 stock DLL에서는 fresh saved 검증을 수행한 범위로 구분한다.

fresh Work PID29152와 fresh Main PID16544에서 각각 654,552검사/실패0/필수 미지원0/dirty0를 확인했고 정상 종료했다. Main 실제 loaded module은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`, BuildId55116800이며 Main canonical DLL은 보존했다. 선택146행과 Main/Work bytes, Source/Config103개, 보호 baseline652개·dependency268개를 확인했다. 사용자/다른 task 에디터를 저장·PIE·종료·reload하지 않았다.

지원 한계는 유지한다. Heavy에는 대응 source Air chain이 없어 Launch가 Short로 fallback한다. Apes/Yetuga의 NoAirDamage/NoBlowDamage는 면역 bool이 아닌 전용 Damage_Grapple_Atk_02 애니메이션 fallback 참조로 사용한다. QuickStand4개는 정리했지만 현재 chain에 연결하지 않았다. 원본 미지원 shape11 occurrence는 임의 Box를 만들지 않고 제외했다. 원작 전체 pose/contact·pixel 완전 일치, 멀티플레이, Player 별도 사망 시스템·실제 패링 생산자는 이 완료 범위가 아니다. 조정은 기존 Definition/ComboDefinition에서 수행하고 과거 author/import/retime/delivery를 반복하지 않는다.

<!-- BrutalInputDevMapComplete_20261010 -->
## 2026-10-10 — 브루탈 입력 B 변경 Main 완료

사용자 요청으로 패드 B(Gamepad_FaceButton_Right)를 브루탈 입력으로 분리했다. 기존 KZGameplayTags에 Input.Action.B만 추가하고 KZPlayerController의 Started/Completed/Canceled 세 binding을 기존 AbilityInputTagPressed/Released/Canceled로 전달한다. Source4개 수정, 새 runtime 파일·class0개다. IA_BrutalAttack Boolean1개를 만들고 기존 IMC_Default·DA_InputData에 추가했으며 Player Definition의 기존 KZBrutalAttackAbility grant만 Input.Action.X→B로 바꿨다. X 약공격·Y 강공격·A 회피와 나머지 기존 입력/부여 행은 fresh readback에서 보존 확인했다.

ASC는 이미 각 Brutal Spec의 configured dynamic input tag를 비교하므로 ASC/Brutal Ability/Task/짝 수명 구현을 추가하거나 고치지 않았다. B는 기존 소진된 유효 대상·거리·현재 액션 조건을 충족할 때 실행하고, Hit2 사용자 피해50·접근·피해자 모션·양쪽 완료 후 생존 회복 계약을 유지한다. 앞선 X 설명은 당시 기록이며 현행 브루탈 키는 B다. 새 상태 태그·GameplayEffect·매니저·상태 사본은 없다.

Main KhazanEditor Development build 성공이며 fresh 실제 로드 모듈은 UnrealEditor-Khazan-20261010.dll, SHA b6e6cae57236e8c44fd750a747ac461d8eafb0884cb5f3ede04065acbd35c1d3다. 사용자 실행 중 canonical DLL 잠금은 고유 suffix 출력으로 해결했고 사용자 에디터 종료/Live Coding을 하지 않았다. 별도 새 Main 에디터의 saved28검사/dirty0와 PIE12마리 live ASC·Definition·AnimInstance·HP/Stamina 초기화, 기존 C++ Khazan.Monster.CombatPolicyPIE의 인간4종 발견/End·대치·타깃 유지·행동 완료/재추적·공격 완료가 통과했다. 테스트 에디터는 정상 종료했고 저장 byte 불변이다. Python 플레이어 입력·이동 주입과 실제 패드 B 버튼 누름 검사는 하지 않았다.

증거와 정확한 재개 기준은 [작업 설명](../../Metadata/BrutalInputDevMap_20261010/README.md), [FinalVerification](../../Metadata/BrutalInputDevMap_20261010/FinalVerification.json), FreshSavedVerification02.json·FreshPIEVerification02.json·Verify02.log다. DevMap 배치/크기 및 임시 수치 출처는 Art state의 같은 날짜 절을 따른다. 이전 CombatReaction 전체 author/delivery/retime를 재실행하지 않는다.


## 2026-10-12T19:30:36.993088+09:00 — ARCH-96 몬스터 넉백·전체 FPS Main 완료

Main516행=기존 runtime2(KZHitReactionAbility.cpp/CharacterDefinition h)+DEV2/Build editor dependency1+asset511을 선택 적용하고 새 Main build/reload/실제 RHI를 확인했다. 기존 ASC·HitReaction/JumpForce Task·Definition과 취소/root-mode·회복 수명을 재사용했다. 새 runtime class/file/manager/tag0, private DLL·Config 전달0이다. 다른 작업의 Player0.1초 제어 제한/ground-hit 분류/원작 StateTree 추가와 최신 공격 VFX88개를 보존했다.

MainBuild01 exit0, MainSaved01의461 sequence3854855 bone key/notify GUID·시각·158 montage의 actual sampling 및 재생 시간 차이0, MainKnockback01의6종11case(인간 F/B8/Giant2/벽1)·회복/재피격/cancel/root-mode 복구, 기존 실제 monster collision 회귀가 성공했다. MainInventory01의 전체2674 sequence/158 montage에서 소수 sequence/model·sampling0,100000fps fallback0이다. native loaded module/516SHA/각 evidence는 Metadata/AnimationTimingKnockback_20261012/FinalVerification.json에 결속했다.

인간4종은 기존250cm와 실제 HitLand 시간을 유지하며 Definition.KnockbackTimeMappingCurve에서 normalized2u-u² TEMP 감속을 조정한다. baseline 착지 직전 약278–375cm/s의 일정속도 → 최종 약8–28cm/s로 줄어든다. RootSource 제거는 엔진의 MarkedForRemoval/다음 이동 tick 삭제를 구분해 검증했다. Apes/Yetuga는 NoAir/NoBlow 대체 clip의 짝 grapple root 이동을 해당 실행 instance만 PushDisableRootMotion으로 억제하여 baseline−278.01/−222.11cm →0cm다. source clip/raw/root 옵션 및 Short fallback·정상 Launch Task는 보존했다.

필수 잔여0이다. 현재 editor는 정상 재시작으로 새 C++/asset cache를 로딩한다. 사용자/foreign editor 제어0이며 이전 pending·failed trial 기록은 이 완료로 대체한다. 원작 curve keys/전체 pose·native/network/shipping parity는 미확인이고 TEMP를 원작 수치라고 부르지 않는다. 과거 author/추출/원본 retime/root repair/옛 DLL 전달을 다시 실행하지 않는다.


## 2026-10-12T19:50:49.391255+09:00 — 플레이어 짧은 피격 복구 / Dodge 승인 Main 완료

ARCH-94의 실제 반영·빌드·native 검증은 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. Player non-shield HitReaction의 마지막 실행부터0.1초 TEMP(`PlayerControlLockSeconds`, Ability EditDefaultsOnly)에서 자기 실행을 끝내고 montage blend-out의 자기 root motion만 억제해 CMC 이동을 즉시 복구한다. 반복 피격은 execution serial과 timer 교체로 이전 종료가 새 실행을 풀지 않는다. Short/Knock/Launch 및 재피격 총6사례에서 조기 잠금·정상/재피격 deadline·다음 Dodge·실제 CMC 이동을 MainFinalQA04로 확인했다. Launch의 정상 Falling은 제어 실패로 오판하지 않는다.

Dodge 무적0.1초는 사용자 지정값이며 actual world-time deadline과 자기 `State.Invulnerable` contribution이 소유한다. melee/field/projectile/captured 피해의 공통 ASC 승인·같은 group dedup·타 기여 보존·8방향 취소·비용 실패를 확인했다. 방어11사례는 실제 GE 경로이고 성공 feedback은 실제 방어1회만 생성한다. 몬스터/Shield 수명과 동시 ARCH-96의 optional KnockbackTimeMappingCurve/자기 대체 clip root disable은 보존했다.

<!-- BeastDodge_20261012_MainCompleted -->


## 2026-10-13T01:40:50.930443+09:00 — ARCH-97 StrongCombo 인간형 VictimFront Main 완료

사용자 요청을 Main에 적용했다. StrongAttack01–03 각2개, 총6개 AttackWindow만 VictimFront로 변경하고 인간형4종(Swordsman/SwordShield/HeavySwordsman/HalberdElite)의 HitReactions.VictimFront에 기존 AM_BrutalVictimFront를 연결했다. 정면 피해자 모션 Damage1→Damage2를 기존 일반 HitReaction Ability/Task로 고정 재생하며 짝 브루탈을 시작하지 않는다. 해당 자기 montage instance의 paired root travel만 억제하고 Knockback/Launch RMS를 만들지 않는다. 설정 없는 Apes/Yetuga는 이전 Knockback pool을 유지한다. 사망·소진·guard 및 피해 승인/dedup/HP·ST/기존 효과는 기존 계약을 따른다.

runtime3파일/기존 DEV1/저장5package 수정이며 새 runtime file/class/태그/manager 및 새 gameplay 수치0이다. enum을 끝에 추가하여 None/Short/Knockback/Launch의 기존 ordinal을 보존했다. Character의 Short event.OptionalObject가 명시한 montage를 Ability가 선택하며, 정상·재피격·취소의 기존 제약/tag/montage cleanup을 재사용했다. 다른 Player window/몬스터 공격·브루탈/Definition의 원래 모든 피격·이동·AI·grant·소진 설정은 fresh Saved01 readback으로 보존 확인했다. 정면 클립에 execution material notify0도 확인해 추가 사망/재질 adapter를 만들지 않았다.

Build02 exit0/input동일, actual RHI ActualStrong02의4종×3타=12case/24승인 적중·어느 target facing에서도 고정 pose·자기 root-disable·RMS 없음·자연 완료/재피격/취소·다른 Short/Knockback pool·거대형 fallback과 기존 PlayerAttackCollision16 회귀가 성공했다. 실제 loaded module SHA는 `b8f1d59008558802324c3b8e7a1cdaba9a526f02efd36f852788a9fd25bbc4b5`이며 전체 Source/선택5asset·저장/실행 evidence는 Metadata/StrongComboVictimFront_20261013/FinalVerification.json과 Changes.patch다. Actor 크기/높은 평면은 격리 QA fixture이며 원작 pixel/전체 pose 일치 검증으로 표현하지 않는다.

필수 잔여0이다. Probe01의 Python 미노출 property/ActualStrong01의 DEV None-group·blend-out 기대값 실패는 역사로 보존하고02의 성공으로 대체한다. CollisionRegression01은 등록명을 잘못 입력해 matched test0이며 Launch PID/CommandLine을 확인한 task-owned process만 종료했다. 정확한 등록명으로 실행한02의 성공을 근거로 한다. 제품 runtime은 첫 실제 검사 이후 추가 변경0이며 Build02는 DEV 보완이다. 기존 editor process0에서 시작했고 외부/사용자 editor 제어0이다. 이후 조정은 최신 Main Definition의 VictimFront와 Player StrongCombo의6window만 표적 확인한다. 완료한 author/과거 VFX·Root·retime/private DLL 전달을 재실행하지 않는다.
