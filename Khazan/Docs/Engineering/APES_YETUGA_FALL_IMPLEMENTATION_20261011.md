# Apes·Yetuga StateTree / 플레이어 낙하 구현

## 2026-10-11 — 분리 작업 구현과 검증 계약 (Main 전달 전)

사용자 직접 구현 요청에 따른 ARCH-86 작업이다. 작업 사본은 `C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan`이다. 기존 Main 에디터를 제어하거나 해당 프로세스에 Live Coding을 적용하지 않는다. 아래 구현과 Main 전달·검증 완료는 별개다. 마지막 상태는 본 문서 하단 및 Engineering continuity를 확인한다.

### 책임과 변경 범위

기존 `ST_Monster`의 Idle → Alert → Chase / Standoff / Attack 선택, `KZMonsterAIController`, 캐릭터별 ASC, CharacterDefinition, ComboDefinition, ComboAction을 재사용한다. 별도 FSM·Manager·전투 상태 복사본을 만들지 않는다. 새 runtime 파일은 세 타입의 h/cpp 6개다.

| 소유자 | 실제 역할 |
|---|---|
| Monster AI / StateTree | 현재 타깃, 후보의 거리·방향·HP·스태미나·쿨다운 조건, 후보 선택, 실행 중 Ability가 끝날 때까지 대기 |
| `KZMonsterPatternAbility` | 기존 ComboAction을 확장하여 원본 SB의 자동 단계, 조건부 다음 단계, 패링/확정 적중/잡기/충돌 이벤트와 실행 자원을 소유 |
| `KZMonsterSkillObject` | 발사 후 몬스터 몽타주와 독립적인 돌·얼음·장판의 이동/적중/수명. 별도 AI를 갖지 않음 |
| `KZFallAbility` | 기존 ComboAction의 Start/Loop/Land 노드, 실제 CMC 착지 이벤트, 일반 낙하와 낙하 공격의 실행 수명 |
| Player / ASC | CMC 낙하 진입에서 일반 Fall 활성화, 공중 X를 FallAttack으로 먼저 라우팅. 지상 X와 브루탈 B는 기존 경로 |
| AnimInstance / ABP | 기존 관측·Slot·관성화·로코모션. 콤보/피해/타이머의 소유자로 변경하지 않음 |

### 몬스터 데이터와 함수

`FKZMonsterSkillChoice`는 실제 AI 후보다. `Skill`은 원본 스킬 이름, `Ability`는 부여된 GA class, `Condition`은 후보 조건, `Weight`는 Apes 선택 가중치다. `EndCooldown`/`BattleStartCooldown`은 초 단위다. Yetuga는 `bOrderedCombatPatterns=true`로 처음 통과한 후보를 선택한다. 동일 스킬이 서로 다른 거리 밴드에 여러 번 등장할 수 있다. 강제 후속 스킬의 쿨다운 조회 행은 Weight=0으로 일반 선택에서 제외한다.

`FKZCombatPatternCondition::Matches()`는 게임 스레드에서 Actor/ASC를 읽는다. XY 거리는 cm, 상대 Yaw는 deg, 높이는 타깃 Actor 중심 minus 시전자 중심의 cm다. HP는 `bHPIsRatio`가 명시된 경우에만 MaxHP로 나눈다. MaxHP 조건의 -1은 비활성 sentinel이다. 타깃 조건의 반전과 자기 HP/스태미나 조건을 구분한다. 벽 검사는 시전자와 타깃을 제외한 Visibility trace를 사용한다.

`SelectCombatPattern()`은 실제 조건·쿨다운이 맞는 후보를 고른다. `IsPatternReady()`는 전투 최초 감지 시간과 스킬별 ready 시간을 확인한다. `RecordPatternFinished()`는 스킬 종료 시 EndCooldown을 기록한다. 원본의 다른 스킬에 대한 추가 쿨다운은 `AddPatternCooldown()`으로 현재 ready 시간과 now 중 큰 값에 AddValue 초를 더한다. 이 ready-time 소비 방식은 UE 어댑터이며 원본 native 함수를 확인한 것이 아니다.

Combo 노드의 `PatternSkill`, `AutomaticNextNode`, `PatternBranches`, `PatternActions`, `PatternMoves`는 하나의 GAS 실행 안에서 사용된다. 별도의 Monster 현재 공격 enum을 만들지 않는다. 원본 SB → 현재 animation library 대응과 playback 시간 변환은 `Metadata/GiantCombatFall_20261011/AuthoringPlan.json`에 저장한다.

`ResolveEvent()`는 AND 조건과 이벤트의 활성 시간 구간을 확인한다. `bDeferUntilStepEnd`이면 다음 노드만 예약하고 현재 애니메이션 끝의 `PatternNext_<현재노드>`에서 소비한다. 즉시 변경이면 `EnterPatternNode()`가 기존 `TransitionToNode()`를 호출한다. 노드가 달라진 뒤 넘어오는 이전 노드의 Notify는 이름 prefix로 무시한다. EndSubState가 예약한 분기도 해당 마커에서 실제로 소비한다. 마지막 노드는 Ability를 정상 종료한다.

`RecordAcceptedAttackHit()`는 기존 collision/GE 결과 검증 뒤 호출된다. Source object·montage instance·execution 검증을 통과한 실제 HP 적용만 기록한다. collision query 중 재진입하여 노드를 바꾸지 않고 다음 게임 스레드 tick에서 처리한다. 패링은 기존 `ReportAttackParried()`가 사용자 결정 스태미나 5 감소를 적용한 뒤 활성 PatternAbility에 전달한다.

`PatternMoves`는 실제 원본 MoveTo의 시작/끝, 대상 제한·offset, 커브를 저장한다. CMC의 `FRootMotionSource_MoveToDynamicForce` handle을 이 실행이 소유한다. 해당 구간만 애니메이션 root translation을 Ignore하여 이중 이동을 피하고, 구간·노드·실행 종료에 자기 handle과 이전 RootMotionMode를 복구한다. Priority=1000은 엔진 AbilityTask의 기술적 우선순위이며 원작 튜닝값이 아니다. 목적지·커브 X를 시간 진행률, Y/Z를 경로 offset으로 소비하는 방식은 명시된 UE 어댑터다.

`BeginCapture()`는 확정 적중 대상만 붙잡는다. 현재 피격/행동 태그 정책의 자기 GE handle, 이전 이동 mode와 parent/socket, 자신이 추가한 move-ignore를 보관한다. 원본 HoldAttachInfo의 손/피해자 socket과 RagdollBone/PhysicsBlendWeight를 소비한다. 현재 임포트 physics asset + Engine PhysicsHandle로 연결하며 원본 FallDown physics asset/native hold operator 자체의 재현은 아니다. 취소/종료에서 자기 handle/component/attachment/physics/이동 제한을 정리한다.

투사체 `Age`, `FlightAge`는 이 Actor가 실제로 소비하는 초 단위 수명이다. 비행 커브는 원본 정규화 시간축과 CustomCurveScale을 사용한다. 일반 종료 후 발사된 오브젝트는 원본 LifeTime까지 유지하며 취소에서는 해당 실행의 오브젝트만 제거한다. `PatternRun`은 재활성화 후 과거 투사체가 새 실행의 소유 목록에 들어가지 않도록 하는 자원 ID다. 얼음 직선 오브젝트의 후속 장판은 같은 source run에 등록한다. 소유 몬스터가 사라지면 잔존 Actor도 종료한다.

### 원본으로 확인한 데이터와 어댑터

원본 zip·full package·field·시간 매핑은 기존 [패턴 분석](APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md), [Art source audit](../Art/APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md)와 계획 JSON을 따른다. 같은 basename의 SD를 다른 package에서 가져오지 않는다.

| 항목 | 원본 입력 및 현재 적용 |
|---|---|
| Apes 후보 | `.../ApesStoneHand_E/Base_Setting/AI_ApesStoneHand_E_Early`의 10개 SkillGroups. Range/Angle/Height/Rate 보존. 일반 몬스터 임시 AttackChance로 대체하지 않음 |
| Yetuga 후보 | `BT_Yetuga` near 0..800, middle 799..2500 체인과 후방 선택 순서. HP 65/60/50, `bCompareRate=false` → **절대 HP**, %로 변환하지 않음 |
| NormalAtk02 후속 | 양쪽 SB의 FindTarget/TargetCondition MaxDistance=800에서 Step2 예약 |
| Dempsey 패링 | 마지막 지정 NotifyEnable 구간에서 Reaction. Yetuga 현재 clip 시간 5.328740734..5.684516269 s, Apes 0.5696434..0.8628588 s. 이전 타격 횟수 조건을 임의 추가하지 않음 |
| Yetuga 대치 | `BT_Yetuga` export 62–65 `MoveSetting` 좌/우/뒤 Rate=2/2/1, MoveTime=1.67 s, bUseMoveByTime=true. 기존 StateTree 태스크에서 선택한 방향을 해당 시간 유지 |
| Apes FastBall | COI LifeTime=10 s, Scale=.8, CapsuleHalfHeight=70. radius는 원본 누락으로 **70 cm 임시 가정**. CV_Apes… Scale=(15000,100,100), duration=2 s |
| Yetuga FastBall | COI LifeTime=10 s, CapsuleRadius=24, CV_Yetuga_FastBall_OBJ_02 Scale=(5000,2500,1500), duration=3 s |
| IceBreath | 직선 COI LifeTime=3.5 s, radius=10, ForceVec.X=3000. cm/s 해석은 어댑터. 후속 TimerLoop Time=.2 s/MaxCount=10; 부모 SB Time=.4 s는 실제 Notify 활성 구간에서 소비 |
| Ice Field | COI LifeTime=10 s, Idle 공격 Box=(281.25,250,100), destruction 공격 sphere radius=250. Step8 요청/수명 끝에서 파괴 전환 |
| 공통 MoveCurve | 추가 표적 추출 `OriginalCommonCurves/BBQ/Content/_Common/MoveCurve/CV_Common_Jump_Normal.json`, `CV_common_accel_deaccel_normal.json`. archived closure에 빠져 있던 참조만 추출 |

Apes FastMove의 SB tick 분기는 존재하지만 해당 clip의 SkillEventTag 마커는 원본 export에 없다. 현재는 원본 MoveTo 구간에 한정하여 조건을 검사하는 어댑터다. 원본 RNG 정규화, MoveTo 목표/회전 소비 단위, AnimBlendAlpha의 시간 해석, native grab/physics, spell/camera 함수는 동일성 미확인이다. 이동·전이 기본 보간은 기존 프로젝트 설정을 재사용하며 그 값을 원작 직접 확인값으로 부르지 않는다.

### 플레이어 낙하 절차

Player `OnMovementModeChanged()`가 실제 `IsFalling()` 진입에서 부여된 일반 Fall GA를 찾는다. 일반 Fall은 전투·이동 제한을 소유하지 않는 포즈 실행이다. 기존 행동이 몽타주를 소유 중이면 일반 Fall은 활성화하지 않고 ABP의 실제 FallLoop 포즈를 기반 포즈로 사용한다. `CanJumpInternal_Implementation()`은 false, 기존 IA_Jump mapping을 해제한다.

ASC가 공중 X를 받으면 `bPlungeAttack=true`인 부여된 Fall GA를 먼저 활성화한다. 공중에서 이를 활성화할 수 없으면 지상 공격으로 흘리지 않는다. 원래 가드/피격/사망 등의 GAS 차단 정책은 그대로 적용된다. X를 놓아도 낙하 공격을 취소하지 않는다. B는 기존 Brutal 입력이다.

`LandedDelegate`가 실제 충돌 착지를 알린 시점에 Land 노드로 전환한다. 이는 CMC가 아직 Falling에서 Walking을 선택하는 중의 엔진 이벤트다. 타이머나 높이 추정으로 착지를 결정하지 않는다. 다른 비지상 이동 mode로 전환될 때 활성 낙하 실행을 취소하며, 실제 착지의 Land 노드는 유지한다. 정상/취소/실패 종료에서 자기 delegate/task/제약을 정리한다.

모든 플레이어 시퀀스는 기존 `InGame/DAS/Fall` 및 `FallAttack`을 사용한다. Player mesh .01은 유지한다. FallAttack 원본 AC_Start는 0..0.273 구간 rate=.5, 0.273..0.29 구간 rate=.005, AC_End는 .29..2.7333333 구간 rate=1이다. 착지 노드 InputEnd=.42649162 s, 공격 구간 0...121175006 s는 원본 `.../Kazan/Skill/DualAxeSword/Common/FallAtk` metadata다. constant AbsoluteOffset=(-110.00064,-15,0), BoxSize=(160,100,100)를 현재 ground-X collision calibration으로 연결한다. 공격 피해량은 기존 ground-X 값 재사용이며 원작 수치가 아니다. 원본 stamina 199의 배율이 미확인이라 현재 FallAttack cost=0 임시값(기존 GA 비용 설정에서 조정 가능)이다.

### DevMap과 검증

`DevTest_FallPlatform`은 Engine Cube 한 개다. scale=(12,8,12), location=(0,0,600), 윗면=1200 cm, PlayerStart=(-350,0,1292). **사용자 요청 테스트용 임시 치수**이며 원작 레벨 수치가 아니다. 기존 Floor/Nav/12종 배치와 대화 짝을 유지한다. 배치된 두 giant의 레거시 빈 pattern override는 현재 BP의 패턴/AI 설정으로 갱신한다.

native `Khazan.GiantFall.PIE`는 실제 CMC로 플랫폼에서 걸어 나가고, 실제 PlayerController gamepad X 입력으로 낙하 공격을 시작한다. Python은 분리 에디터 시작/PIE 수명/로그 관측만 수행하며 Actor를 이동하거나 키를 주입하지 않는다. 기존 카메라 설정은 수정하지 않고 검증 전용 CameraActor로 PNG를 얻는다. 원래 카메라와 fixture Actor는 끝에 복구/제거한다.

현재 1차 PIE(PrivatePIE02)는 일반 낙하/착지, X 낙하 공격/착지, X release 지속, 지상 X, Brutal B, 새로 생성한 두 giant의 Sight→Roar→StateTree Attack을 관측했다. 배치 인스턴스 pattern count=0으로 실패했으며, 이 문제를 수정한 뒤 재검증이 필요하다. 이후 조건·패링·이동·오브젝트·잡기 테스트 및 Main 전달은 아래 날짜별 추가 기록에서 실제 결과를 확인한다.

## 2026-10-11 — Main 반영·fresh 빌드/저장/RHI 검증 결과

현재 선택 모듈은 `UnrealEditor-Khazan-20261011.dll`이다. [FinalVerification](../../Metadata/GiantCombatFall_20261011/FinalVerification.json)의 `MainDeliveredAndFreshVerified`는 이번에 실제 반영한 구현과 검사 범위를 뜻하며, 원작 내부 함수까지 완전 동일하다는 뜻은 아니다. MainBuild02 성공, MainSavedAudit01(새 모듈 실제 로드) 성공, MainPIE(실제 RHI) `Khazan.GiantFall.PIE` 전체 성공이다. 검사 에디터는 정상 종료했다. 기존 에디터 제어/Live Coding0, Python gameplay 이동/입력0이다.

### 실제 반영 범위와 보존

- runtime 기존13파일의 작은 확장과 새 타입3개 h/cpp6개, native 테스트1개, editor-target `Json` 의존성만 추가한 Build.cs1개: Source21개다. 별도 FSM/Manager/컴포넌트 및 Main AnimInstance의 gameplay 상태는 추가하지 않았다. Work의 author wrapper와 대규모 editor 모듈 의존성은 Main에 복사하지 않았다.
- Content151(저장 asset150+DevMap)을 반영했다. 원본 animation sequence 재임포트·일괄 RateScale/root 옵션 변경은 하지 않았다. Apes48노드/19 GA/일반 후보10+쿨다운 전용9행, Yetuga81노드/24 GA/일반 후보28+쿨다운 전용6행이다. 129개 노드/후속 참조가 저장된 데이터를 읽어 검증됐다. 모든 GA가 일반 랜덤 후보라는 뜻은 아니다. 강제/level/회복 스킬은 원작 용도와 사용자 스태미나 정책 때문에 자동 후보에서 제외한다.
- 최신 Main Definition 두 개를 기반으로 재적용하여 기존 `DeathPresentationMontage`, 초기 Effect·기존 부여·Brutal50을 유지했다. source13의 변경 주변에서 기존 Player/Monster VFX·death 코드를 보존했다. 전달 제품176파일, 이 작업 밖의 Source84개, VFX Content965개가 최신 저장 receipt/해시와 일치한다.
- 백업: `Saved/GiantFallBackup_20261011/20261011_030609`. 이전 module manifest/DLL/PDB도 NativeBeforeBuild에 보관했다. 기존 Source/asset을 포함한 전달 기록은 [DeliveryReceipt](../../Metadata/GiantCombatFall_20261011/DeliveryReceipt.json), 작은 변경과 새 소스의 정확한 내용은 [OwnedSourceDiff](../../Metadata/GiantCombatFall_20261011/OwnedSourceDiff.patch)다.

### 실제 PIE 검사

플랫폼에서 native CMC로 걸어 나가 일반 Start→Loop→실제 Landed→Land를 확인했다. 다른 회차는 실제 PlayerController `Gamepad_FaceButton_Left`(X) 입력으로 낙하 공격을 활성화했고 X release 이후에도 착지 공격이 지속됐다. 지상 X·브루탈 B 부여/경로와 두 giant의 실제 Sight→Roar→자율 StateTree Attack도 확인했다.

개별8사례는 Apes NormalAtk02의 근거리 Step2 연결/원거리 생략, Yetuga Dempsey Step2 이른 패링에서 단계 유지/마지막 창의 reaction(실제 stamina5 감소), Apes FastMove의 실제 위치 변화·후속 단계, Apes 및 Yetuga held rock 발사와 위치 변화, Yetuga Ice field의 floor 위 배치, CloseGrab 실제 적중/붙잡기와 취소 후 attachment·GE·RootMotionSource 해제다. RootMotionSource는 엔진이 다음 CMC tick에서 제거하므로 그 시점에 검증한다. 패링 API 전달을 검증한 것이며 새 플레이어 perfect-guard 입력 판정까지 구현했다고 확대하지 않는다. 모든 129노드를 실제 플레이에서 개별 완주하거나 원작 영상과 pixel/frame 비교한 검사는 아니다.

### 검사 중 수정과 데이터 계약

몽타주 전체 position에서 section start를 빼는 float 연산이 Notify의 local 시작 경계보다 미세하게 작아져 Apes Spawn을 거부했다. 일치하는 Animation Notify는 자체 시점으로 소비하고, Tick/Parry 등의 활성 창 검사는 유지한다. 같은 시각의 source event index 여러 개는 UE branching marker 하나를 공유하며 각 조건/행동은 유지한다.

Yetuga FastBall Step1의 pickup marker(.663037050 s)는 생략된 BeginSkillAction을 Spawn으로 **추론**했고, Step2의 명시 `ESkillAction::Use`(.680444771 s)에서 동일한 돌을 발사한다. native class CDO 기본값은 미확보다. 초기 StepStart마다 생성/첫 marker에서 발사하던 연결은 철회한다. `bUseSkillObjectSpawn`은 여기서 Notify가 소비하는 설정으로 다룬다. floor 생성은 손 pose가 바닥 아래일 수 있어 capsule 위에서 trace한다. 모든 판정은 실제 게임 스레드 실행이며 source/temporary 상태를 섞지 않는다.

### 원작 동일성의 남은 경계

source로 확인한 거리·각도·HP/stamina 조건, cooldown, 단계/이벤트/curve/재생 시간과 현재 프로젝트 어댑터를 구분한다. native RNG 정규화, AnimBlendAlpha의 native 단위, MoveTo 세부 소비/종료 결과, 원본 grab/physics operator, camera/Spell 함수, Apes scripted level binding은 완전 동일성 미확인이다. 원본 Yetuga BT의 일부 전용 MoveTo→NoCool 후속/선택 substep·fallback 시퀀스는 현재 공통 Chase와 평탄화된 후보 선택으로 대체되며 **BT 전체 구조 그대로의 구현은 아니다**. Apes projectile source 모델이 없어 Engine sphere를 사용한다. 이 범위를 원작과 완전히 같다고 표현하지 않는다.

후속 동일성 작업은 기존 `YetugaOriginal/BehaviorTreeResolved.txt`의 MoveTo/UseSkill sequence·SelectedSkillSubStateSteps를 현재 AI 후보/StateTree task와 대조하는 작은 확장부터 시작한다. 전체 재추출/재임포트나 새 만능 Manager를 생성하지 않는다. Spell/camera 및 source native enum/MoveTo 기본값은 exact package의 추가 metadata 또는 원작 영상/실측을 확보하여 현재 추론을 검증한다. 비용0/피해 재사용·벽 거리 fallback·누락된 physics blend1 같은 임시 어댑터는 원작 직접값으로 바꾸어 부르지 않는다.

### 직접 테스트

Main 프로젝트를 새로 열고 DevMap에서 PIE를 시작한다. 플레이어는 플랫폼 위에서 시작한다. 이동키로 가장자리를 벗어나면 일반 낙하/착지를 볼 수 있고, 떨어지는 동안 패드 X(또는 기존 약공격 X 입력)를 누르면 낙하 공격 뒤 실제 착지 타격으로 이어진다. 점프 입력은 비활성화됐고 `CanJumpInternal`도 false다. 바닥에는 기존12마리와 Apes/Yetuga 두 종류가 있으므로 가까이 이동해 전투 패턴을 볼 수 있다. 임시 발판은 테스트용 한 개이며 기존 바닥/Nav/대화 배치를 대체하지 않는다.
## 2026-10-11 — 미전달 landed/paired 후속 Main 검증 보충

기존 ARCH-86 Main 결과를 유지하고, landed의 기존 baked timeline을 한 번 변환해 끝 pose까지 보존하며 paired Brutal/Exhaustion의 이전 root mode 소유·복구/live victim 정렬을 보완했다. MainNativeResume01의 실제 landed 및6종 front/back12사례, UI의 적격 locked target 우선, VFX18+Brutal5/fallback0을 통과했다. raw sequence 변경0/Player .01·피해·비용·blend 유지다. exact 원본 시간/계산/변경·backup·receipt는 [후속 정본](COMBAT_PRESENTATION_FOLLOWUP_20261011.md)을 따른다. 원작 BT/native/pixel 전체 재현을 완료했다고 확장하지 않는다.


## 2026-10-12T19:50:49.391255+09:00 — 원본 경로의 StateTree 구체화 Main 완료

ARCH-94로 Yetuga 원본121노드의 source property/49gate/46skill/10MoveTo/5LockOnMove·성공/실패 후속을 `ST_Yetuga_Original`173상태로 옮겼다. Apes는 `ST_Apes_Original`9상태와 기존 Early 후보, actual damage passive3행을 사용한다. original24+alias4/Apes19의 실제47기술, actual Sight→Roar→combat, deterministic7피격 SideMove 및 compiled 원시 field/정확 class·entry/후속은 최신 MainFinalQA04에서 성공했다. 과거 공통 Chase/평탄화 후보만으로 대체되던 Yetuga 전용 순서·NoCool·selected substep의 구조 제한은 이 구체화 범위에서 대체된다.

정확한 전달 SHA/빌드/module/검사와 수치 출처는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. native RNG·abort·생략 CDO·Group1 producer·selected float/이동 물리 전체 동일성은 미확인이다. Apes 임계 >=/history reset/독립 chance draw는 원작 직접 검증값이 아닌 프로젝트 어댑터다. 모든 실제 UE 기술 실행 성공과 원작 native 전체 동등성을 구분한다. 후속은 저장 plan/report 및 exact package에서 부족한 근거만 확보한다.

<!-- BeastDodge_20261012_MainCompleted -->

## 2026-10-13 — Apes·Yetuga 잡기 완결·Tackle 비활성·Armageddon 착지 Main 검증

구현과 검증의 최신 정본은 `Metadata/GiantGrabs_20261013/FinalVerificationVisualRepair.json`이다. 기존 8개 targeted asset과 13개 targeted Source의 Main↔독립 Work SHA 일치, Main/Work 저장 에셋 각각 42항목, 별도 백그라운드 Main DevMap NullRHI 및 RHI `Khazan.GiantFall.PIE` 13/13 성공, 실제 로드된 `UnrealEditor-Khazan.dll` 경로를 기록한다. 초기 전달 후 렌더링 검수에서 수정한 Main 파일은 `KZMonsterPatternAbility.cpp/.h`, Yetuga `GA_Original_CloseGrab`/`GA_Original_RushGrab` 네 개뿐이며 직전본은 `Metadata/GiantGrabs_20261013/BeforeVisualRepair`에 보존했다. 기존 다른 작업 파일이나 Rider 실행 에디터 프로세스는 수정·종료하지 않았다. UHT가 복사된 헤더의 이전 generated code를 잠시 재사용해 첫 Main 빌드가 실패했으나, UE 공식 `-ForceHeaderGeneration -NoUBTMakefiles`로 생성 코드를 갱신한 다음 최종 빌드는 성공했다.

`FastBall`은 원본 `SI_ApesStoneHand_E_FastBall.SkillName.SourceString`상 실제 돌 던지기다. 이를 삭제하지 않고 원본 계열 바위 mesh `FS_Rock_Big_009`로 프로젝트의 잘못된 Yetuga 바위 참조를 교체했다. 정확한 투사체 mesh 대응은 임시 매핑이다. Apes `Dodge_A`와 `Level_DashAtk_New`, Yetuga `CloseGrab`과 `RushGrab`의 기존 콤보 정의·Ability·StateTree 경로를 사용해 적중→잡힘 상태 효과→몬스터 성공/후속 노드→플레이어 `CA_P_Kazan_Hold_Demon`→정상/취소 해제까지 이었다. `RushGrab_Step2` 입장 직후 해제하던 경로는 제거했다. Accepted attack window의 동일성을 GE SetByCaller `KZAttackBeginsCapture`로 넘겨 collision 시작시각 0.6841691809초와 재계산 montage 위치 0.684166초의 float 경계 차이 때문에 `PendingCapture`가 소실되던 실제 버그를 수정했다. 기존 `GE_MonsterCapture`가 플레이어의 액션/이동 제약을 소유하며 Ability 종료·취소 시 own effect handle, 부착, 충돌 무시 설정과 이동 모드를 복원한다. 새 상태 관리자·컴포넌트는 만들지 않았다.

원본 `HoldAttachInfo.AttachSocketName=Weapon_L`과 target Apes `Bip001-Spine`/Yetuga `Hold_Spine`을 기존 grab Ability의 조정 가능한 `VictimCaptureTargetSocket`으로 연결했다. 최초 스냅 직후와 붙잡은 동안 손·목표 소켓 위치를 정렬한다. 이 프로젝트의 현재 PhysicsAsset으로 source `FallDown` ragdoll blend를 흉내 내던 physics-handle 분기는 RHI에서 플레이어 몸이 바닥으로 떨어지는 오류를 만들어 제거했다. 원본 전용 FallDown 물리 자산 및 native HoldAttachComponent가 확인되면 물리 보조 동작은 그때 별도 재현해야 한다. 추출 player hold clip은 root motion disabled여서 `IgnoreRootMotion` 설정 시도는 효과가 없었고 최종 코드에서 철회했다. frame39/30=1.3초 hold는 임포트 시퀀스 프레임 수에서 계산한 값이다. 일부 원본 몬스터 잡기는 이 시각 바로 전 마지막 1프레임 안에서 해제되므로 PIE는 최종 포즈 정지 또는 frame38/30 도달을 수용한다. 현재 `VictimCaptureBlendSeconds=0.12초`는 원본 근거가 없는 프로젝트 임시 표현값이다.

잡기 창은 `bBeginsCapture=true`, `bBlockable=false`로 저장했다. ASC는 잡기에서 활성 Dodge Ability의 `TryAvoidHit` 성공만 허용하고 별도 무적 태그는 회피 수단으로 보지 않는다. `KZDodgeAbility.InvulnerabilitySeconds=0.1초`는 현재 프로젝트 설정이며 원작 무적 길이의 직접 검증값이 아니다. 일반 guard/parry로 잡기를 막지 않는다. Yetuga `ChargeTackle`은 사용자 지시대로 후보 가중치0, `DisabledPatternSkills`, StateTree 선택·후속 gate에서 실행 차단했고 원본 archive는 보존했다. `CloseGrab`/`RushGrab` 둘은 유지했다. Armageddon 착지창은 원본 `AC_Yetuga_Armageddon_Jump_End` Notify[14]/`_Close` Notify[17]의 0.652310151~0.702310119초, radius2000cm·Z size500cm와 `bDontJustGuard` 근거로 Step3/4에 복구했다. 현재 HP10/ST5, offset 합산과 Z half-height 해석은 임시 어댑터/계산이며 원본 피해 최종값이 아니다. 실제 PIE는 착지 피해와 원본 `RushGrab_Step5` 후속을 관측했다.

렌더링 전후 검수에서 네 grab의 손↔목표 소켓 오차 0.000cm를 기록했다. 테스트 fixture가 잡힌 플레이어를 재배치하던 오류도 고쳐 실제 부착 화면을 검사했다. 대상 애니메이션 10개 root track은 순서·motion extraction 감사에서 통과했지만, 모든 Apes/Yetuga 행동 129노드의 화면 전이를 원작 영상과 일대일 검수한 것은 아니다. Apes `Dodge_A`의 현재 근접 선택 weight1/0~400cm는 원본 passive trigger가 아직 매핑되지 않아 임시값이다. 이 임시값, 물리 자산, FastBall 정확 mesh 및 native RNG/카메라·모션 전체 일치가 남아 있으며 Main 기능 검증 성공을 원작과 한 프레임 차이도 없다는 주장으로 확대하지 않는다.

## 2026-10-13 패턴 이동 source 전환 공백 보완 및 전체 애니메이션 감사

`UKZMonsterPatternAbility::EnterPatternNode`는 기존 `ClearPatternMovement()`로 이전 RootMotionSource를 제거한 뒤 `TransitionToNode()`를 호출하지만 새 node의 `UpdatePatternMovement()`는 보통 다음 `TickPattern` 끝에서만 실행했다. montage notify가 그 tick 이후 일어나고 다음 node의 MoveTo window가 시작 시각 0 근처라면 CMC가 한 번 이동 source 없이 갱신할 수 있는 경로다. 새 node/전환에 성공하고 pending action 상태를 초기화한 직후 기존 `UpdatePatternMovement()`를 한 번 호출한다. 같은 tick에 기존 Tick이 뒤따르면 `MovementWindow`/`MovementLoop` guard가 중복 등록을 막는다. 새 class/component/data/튜닝 수치는 추가하지 않았다. 직접 검사한 원본 시작 window 사례는 Apes DempseyRoll Step2, Level_DashAtk_New Step8, Dodge_A Step8, Dodge_B Step2, Yetuga RushGrab Step7, DashAtk Step2, FastMove Step2다. 비활성화된 Yetuga ChargeTackle Step3도 원본에는 window가 있지만 runtime 선택은 계속 차단한다.

읽기 전용 Main 검사: 두 DA 129 node/118 unique sequence, EnableRootMotion disabled 0, 참 root track missing/not-first 0, dirty 0. engine-extracted actor motion 0인 시퀀스 8개 중 5개 Bip001 중간 pose 이동은 start/end net translation 0인 정지 동작이며 근거 없이 true root로 bake하지 않았다. `AuthoringPlan.json`의 129개 source `AnimBlendAlpha` 대응 `blend`와 현재 설정의 차이는 0; source 0 blend 10개 유지. 격리 Work와 Main의 UE5.8 KhazanEditor 빌드가 성공했고 분리 숨김 NullRHI DevMap `Khazan.GiantFall.PIE` 각 13 fixture가 Success로 완료했다. 최종 단일 Source SHA, 기존 20 파일 동일성, 실제 Main DLL 경로와 로그는 `Metadata/GiantGrabs_20261013/ImmediateMoveVerification.json`에 있다. 이 테스트는 코드상 한 프레임 공백 가능성과 기존 패턴 회귀를 다루며, 전 장면의 화면 끊김·원작 영상 동일성을 측정한 것은 아니다.

2026-10-13 보충: 8개 시퀀스의 root 추출 0은 해당 clip 자체의 결과다. FastMove 같은 단계의 actor 이동은 기존 PatternMoves/RootMotionSource가 담당할 수 있으므로 '정지 동작'을 런타임 이동 없음으로 읽지 않는다.

2026-10-13 최종 검증 추가: 위 수정이 반영된 Main DLL을 별도 숨김 D3D12/RHI DevMap 에디터에서 직접 로드했다. `ImmediateMoveMainRHI.log`의 `Khazan.GiantFall.PIE` 13 fixture도 Success이며 editor exit 0이다. `ImmediateMoveVerification.json`의 `main_rhi_pie`에 실제 모듈과 완료 행을 추가했다. 이는 해당 13사례의 렌더러 동반 회귀 검증이지 전체 node/frame 원작 일치 판정은 아니다.

2026-10-13 원본 PA 선택 경계 보충: source player mesh의 기본 `C_P_Kazan_PhysicsAsset`(body17/constraint0)와 별도 `C_P_Kazan_Ragdoll_HoldSpine2`(body20/constraint19)를 두 pak에서 표적 추출했다. `ECommonPhysicsAsset::FallDown`의 native 선택 경로를 확인하지 못했으므로 HoldSpine2를 `BeginCapture`에 임의로 적용하지 않았다. 이전 임포트 PA simulation의 바닥 처짐을 다시 만들지 않도록 현재 붙잡기 경로는 유지했다. 패키지/SHA/원본 metadata는 `Metadata/GiantGrabs_20261013/SourceAssetTrace.json`을 따른다.


## 잡기 방어 불가와 원본 경고 연결 (2026-10-14)

Main의 Apes `Dodge_A_Step8/12`, `Level_DashAtk_New_Step8/12`, Yetuga `CloseGrab_Step1`, `RushGrab_Step3/5` 저장 판정창은 모두 `bBeginsCapture=true`, `bBlockable=false`다(`Metadata/GiantGrabs_20261013/FreshReadback.json`). `KZComboActionAbility.cpp` 적중 경로는 먼저 `TryDodgeHit(..., Window.bBeginsCapture)`를 호출하며, 그 다음 `Window.bBlockable && ... TryGuardHit(...)`에서만 일반 방어·Perfect Guard/Parry를 실행한다. `KZAbilitySystemComponent.cpp::TryDodgeHit`는 capture의 `bDodgeOnly`가 true일 때 활성 회피 Ability의 `TryAvoidHit` 성공만 허용한다. 따라서 현재 데이터와 실행 분기상 두 종 잡기는 가드·패링할 수 없고 성공한 회피만 무효화한다. 기존 태그/Ability 수명은 변경하지 않았다.

원본 `xxHoldingAttackWarning`에 대응한 전용 Cascade·SoundWave를 기존 `KZAnimNotifyState_MonsterVisual` + `KZAnimNotify_CombatEffect`, `KZAnimNotifyState_PlayAudio` 경로로 7개 AnimSequence에 추가했다. `KZAnimNotify_CombatEffect`에는 기본 false인 `bFaceCameraOutsideMeshBounds` 한 설정만 추가했다. 켜진 이 UI effect는 기존 `UI_Chest` 소켓을 쓰되 카메라 방향의 mesh world AABB 앞면으로 원점을 옮기고 화면을 향하게 한다. 위치는 현재 mesh bounds의 투영으로 계산하며 수치 튜닝 상수를 새로 두지 않았다. 일반 전투 effect는 이 경로를 사용하지 않는다. 경고 state가 끝나면 기존 `OnNotifyEndDeattach`를 사용해 유한 Cascade tail을 소켓에서 분리한다. 추가 manager/component/상태 복제는 없다.

Main `Build02.log`의 UE5.8 KhazanEditor 빌드 성공, `CameraFacingAuthorReport.json`의 7개 저장·비소유 Notify 보존, `SavedReadback.json`의 새 프로세스 7개 재확인을 마쳤다. 중간에 병행된 GiantCamera 작업은 같은 Yetuga clip 4개에 camera state를 추가했고 `Metadata/GiantCamera_20261014/OverlapMergeFinal.json`의 병합 성공을 확인한 뒤 본 경고 설정을 다시 저장했다. 마지막 `Metadata/GiantGrabWarning_20261014/PIE/RuntimeReport.json`은 Main D3D12 `Khazan.GiantFall.PIE` 성공, 실제 Apes/Yetuga GrabWarning 발생 각 양성, 원본 음향 5회 및 active particle 양성이다. 경고 UI는 최종 PNG에서 눈으로 확인했다. 이 fixture는 기존 실제 잡기·취소·착지 경로를 검증하지만, 두 종의 잡기를 실제 Guard 입력을 계속 누른 채 맞는 별도 통합 사례나 원작 픽셀 동일성까지 주장하지 않는다. 방어 불가 결론의 직접 근거는 저장된 공격창과 위 short-circuit 실행 분기다.


## 2026-10-15 — 거리 복귀·Armageddon·장거리 잡기·groggy/콤보 연결 Main 완료

멀어져 Idle에 남는 두 실행 원인을 기존 소유자 안에서 수정했다. disabled ChargeTackle SourceGate의 true와 inverted false가 모두 false였던 것을 `bInvert` 반환으로 보완해 source false continuation으로 진행한다. 원작 StateTree와 disabled skill 정책은 유지한다. 또한 baked navmesh 밖에서 accepted abstract path가 Moving만 표시하고 Pawn 입력은 0인 Yetuga 실행을 PursuitProbe03에서 확인했다(Walking/속도470cm/s/MaxAcceleration1800cm/s², IgnoreMoveInput=false, active montage/root 없음). AIController의 task-owned `DirectMoveGoal`을 기존 Locomotion intent→Pawn AddMovementInput→CMC로 소비한다. 유효 nav 투영 성공 시 원래 MoveTo로 복귀하며 권한 상실/task Exit/Unpossess는 기존 StopRequestedMove가 목표/입력을 함께 정리한다. 새로운 gameplay state나 manager는 없다.

Yetuga AISettings의 `RangedPatternSkill=Armageddon`, range800–5000cm, chance.3, cooldown20s를 저장했다. range 입력은 원작 BT058 거리 분기800 및 BT export37 Armageddon maxDistance5000을 활용한다. 원본 상위 HP raw<=65/MinStamina raw>=20/EndCooltime240은 BEHAVIOR_ANALYSIS 및 AuditBefore02에 기록되어 있다. 사용자 요청대로 설정된 원거리 선택에서 HP ceiling만 해제하고 source stamina/angle/장애물/Ability/기존 cooldown owner를 유지한다. **30%/20s는 원작 직접값이 아닌 TEMP 정책**이다. 같은 selection frame의 true/false gate가 하나의 RNG 결과를 공유하며 task Enter에서 다시 뽑지 않는다. Apes에는 존재하지 않는 Armageddon을 추가하지 않았다.

capture-bearing node의 정방향 trace-target 이동만 선택 target의 현재 거리−원본 TargetOffset까지 TargetMax 상한을 확장한다. 원본 이동 시간/curve/미스/회복/다른 공격 이동은 유지하며 임의 고정 장거리 literal을 넣지 않았다. 실제 2000cm 고정 표적에서 Apes Level_DashAtk_New_Step8 1846.74cm, Yetuga RushGrab_Step5 1815.15cm 이동 및 양쪽 held=1을 확인했다. 이동 중인 플레이어의 회피는 원래 공격의 행동이며 자동 포획 보장을 넣지 않았다.

약점 파괴와 groggy에 쓰는16 sequence의 before/after read-only root audit rows가 완전히 동일하다. PartGroggy_Start 두 clip은 enable_root_motion=true, true root `Root` index0 및 정상 track 순서다. 추출523.544cm에 대해 실제 약점 파괴 캡슐 이동 Apes526.802cm/Yetuga526.790cm을 확인했다. Rider에서는 실제 Apes PartGroggy의 MontagesOnly/DisableRootMotionCount0/mesh scale1/root translation scale1/Walking을 확인했다. 올바른 원본 track을 재베이크하거나 과대 배율로 바꾸지 않았다.

두 몬스터의 기존 AM_Exhaustion은 Start→Loop 및 Loop→Loop를 각 runtime montage instance에 연결하고 기존 timer/Brutal/End cleanup을 유지한다. Physics03에서 Start/Loop를 연속 관측(Apes277/Yetuga437 samples), End 후 State.Exhausted 해제를 통과했다. 콤보 Commit/Open section jump에는 기존 ABP Slot inertializer를 사용해 `MinimumTransitionBlendSeconds=.12s` TEMP floor를 적용한다. source0/짧은.1s 전이는 보완하고 더 긴 원본 blend와 clip/Notify 시간은 보존한다.

Build11 standard/Build12 suffix 성공. PursuitFinal 및 최신 표준 Main FinalMain01은 실제 source StateTree의 4500cm 추적/다음 공격, full-HP Armageddon entry, 두 capture 및 BeastDodge.SourceAudit, GiantFall13 회귀 전부 Success, 저장0이다. 원거리 30%는 저장 policy이며 QA에서는 0/1 경계로 선택 경로를 확인한 것이지 통계 실측30%가 아니다. 최신 실행 모듈/모든 원시 실패 기록/수치 출처/현재 SHA는 `Metadata/CombatFeel_20261015/FinalVerification.json`. 사망 연결은 COMBAT_PRESENTATION_FOLLOWUP_20261011.md의 최신 절.

