# 2026-10-06 — DevMap 첫 4종 몬스터 AI

## 범위와 적용 상태

사용자 직접 구현 요청: Swordsman, SwordShield, HeavySwordsman, HalberdElite의 Idle/배회, 플레이어 감지, 전투 준비, 접근, 플레이어를 보면서 거리 유지·좌우 걷기·대기, 원작 단일/연속 공격, 플레이어 후퇴 시 재추적. **피해 판정·피격·적 HP 소비·Guard 성공은 연결하지 않는다.** 원작 공격 재생과 가능한 단계 순서를 사용하며 원작 AI 전체 복제라고 표현하지 않는다.

ARCH-77을 따른다. 새 runtime 파일은 `AI/KZMonsterAIController.h/.cpp`, `AI/KZMonsterStateTreeNodes.h/.cpp` 네 개다. 기존 `KZMonster`, `KZCharacter`, `KZAbilitySystemComponent`, `KZComboActionAbility`, `KZComboDefinitionData`, `KZCharacterDefinition`, `KZLocomotionComponent`, `KZAnimInstance`, AssetData registry를 사용한다. 별도 Monster AttackAbility/AnimInstance/Manager/FSM/피해 시스템은 없다.

이 문서의 최초 절은 **Source 적용·격리 에셋/테스트 진행 중** 기록이다. 메인 에셋 전달·최종 build/PIE 결과는 하단 완료 절에서만 확정한다.

## 행동 선택과 실행 책임

공통 `/Game/Monsters/AI/ST_Monster`는 엔진 `StateTreeAIComponentSchema`를 사용한다. ContextActor는 `AKZMonster`, AIController는 `AKZMonsterAIController`다. 각 노드의 AIController instance-data 핀은 해당 context에 바인딩한다. 루트 아래 선택 우선순위는 다음과 같다.

| 상태 | 진입 조건 | 실제 실행 | 완료 후 |
| --- | --- | --- | --- |
| Alert | 감지 대상이 있고 아직 그 대상의 전투 준비를 하지 않음 | 기존 ComboAction으로 Vigilant/FreakOut/Armed 재생, 이동 중지 | Root 재선택 |
| Chase | 대상이 있고 준비 완료, EngageDistance 밖 | 엔진 MoveTo 대상 Actor, Run/LockOn | 근접하면 Root |
| Attack | 대상이 있고 cooldown 완료, AttackDistance 안, 정면 각도 안 | 후보 중 직전과 다른 Ability 선택, ASC 활성화, 확률에 따라 기존 연속 입력 의도 제출 | Ability 종료 후 Root |
| Standoff | 대상이 있으나 위 상태를 선택하지 않음 | Walk/LockOn, 왼쪽·정지·오른쪽 선택, 선호 거리로 보정 | 거리 이탈/공격 가능/대치 시간 종료 시 Root |
| IdlePatrol | 감지 대상 없음 | Idle 또는 Home 주변 reachable point로 Walk, 멀리 나왔다면 Home 복귀 | 대상 감지/대기 시간 종료 시 Root |

StateTree의 활성 상태가 행동 수명 원본이다. `EKZMonsterTask`/`EKZMonsterCondition`은 에셋 편집용 종류 선택이며 캐릭터가 별도로 변경하는 FSM 상태 사본이 아니다.

`AKZMonsterAIController`는 Sight perception, weak target, focus, navigation과 기존 Locomotion 작성 토큰을 소유한다. Sight 성공 대상 중 실제 player-controlled `AKZPlayer`만 받는다. 대상이 사라지거나 시야 상실 기억 시간이 끝나거나 Home leash 밖으로 나가면 대상/focus를 해제한다. 다른 몬스터의 감지 이벤트를 전투 대상으로 채택하지 않는다.

`SetFocus(Player)`와 기존 `RotationMode::LockOn`/CMC controller-desired rotation이 플레이어를 보게 한다. 엔진 PathFollowing이 실제 CMC 이동을 구동한다. active path의 다음 목표를 향하는 방향만 기존 `SetMoveInputWorld`로 전달하여 공통 snapshot/AnimInstance의 방향 관측이 유지된다. AIController가 `AddMovementInput`으로 같은 이동을 두 번 구동하지 않는다.

`Block.Movement.Input` 허용 변화는 기존 Locomotion delegate를 받는다. 불허가 되면 navigation/자기 입력을 즉시 중지한다. 다시 허용되면 현재 StateTree 이동 작업이 재요청한다. Monster PostInitializeComponents의 `Super`에서 AutoPossess가 먼저 일어날 수 있으므로 CharacterDefinition 준비 전에는 AI 시작을 보류하고 Controller Tick에서 재시도한다.

## 변수·함수의 소유와 수명

| 소유자/항목 | 용도·단위 | 작성·소비·종료 |
| --- | --- | --- |
| Monster.AISettings | 감지/거리/주기/확률 편집 설정 | BP defaults 작성, Controller/Task 읽기. 실행 중 상태가 아님 |
| Monster.AIStateTree | 공유 행동 선택 에셋 | BP 작성, Controller 시작 시 사용 |
| Monster.AlertAbility / AttackAbilities | 준비 동작과 공격 후보 class | BP 작성, Task는 ASC에서 이미 부여된 spec을 찾음. 실제 grants는 기존 CharacterDefinition |
| Controller.BattleTarget | 감지한 실제 Player weak 참조 | Sight/Tick 작성, 조건/작업 소비, 상실·UnPossess·EndPlay Reset |
| Controller.AlertedTarget | 해당 대상의 준비 동작을 수행했는지 기억 | Alert Enter 작성, NeedsAlert 소비, 대상 해제 시 Reset |
| Controller.HomeLocation | 해당 possess의 출발 위치, world cm | OnPossess 작성, 배회/복귀/leash 소비 |
| Controller.SightLostAt | 시야 상실 시작 world seconds, -1은 상실 없음 | Sight callback/Tick 작성, 기억 만료 계산 |
| Controller.NextAttackAt | 다음 공격 선택 가능 world seconds | Attack Exit 또는 활성화 실패 작성, CanChooseAttack 소비 |
| Controller.LastAttackClass | 직전 후보 weak class | Attack 성공 작성, 다음 선택에서 즉시 반복 제외 |
| Controller.IntentHandle/BoundLocomotion/delegate handle | 기존 AI 입력 작성 권한과 permission 구독 | 준비된 Pawn에 발급/구독, release에서 자기 권한·구독만 반환 |
| Task.TimeRemaining / RetryAt | 자기 대기 잔여 s / nav 재요청 world s | Enter/Tick 작성, 해당 Task 종료 시 수명 끝 |
| Task.MoveGoal / StrafeSign | world cm 목표 / -1·0·+1 선택 | Idle/Standoff Enter/Tick 작성, MoveTo 소비 |
| Task.AbilityHandle / bContinueCombo | 실행 중 spec 식별 / 이번 실행의 연속 의도 여부 | Enter 작성, Tick 대기/Exit 자기 spec·command 정리 |

`EnterState`는 자기 이동을 멈추고 정책을 설정한 뒤 대기/목표/Ability를 준비한다. `Tick`은 대상·거리·시간·spec 활성 상태를 검사하고 필요할 때 MoveTo를 요청한다. `ExitState`는 자기 nav와 held combo 의도를 정리하고 자기 spec만 취소한다. 공격 자연 종료도 기존 GAS 태그/Task cleanup을 거친다.

Controller UnPossess/EndPlay는 Tree 중지 → 자기 nav 중지 → delegate 해제 → intent token 반환 → target/focus/기억 정리 순서다. 기존 Character UnPossessed의 Action 취소/ComboCommands clear도 유지한다. notify 종료만 기다리는 cleanup은 아니다. 모두 엔진의 gameplay game thread 경로이며 AnimInstance worker는 기존 GT snapshot만 읽는다.

## 원작 공격과 입력 연결

| 병종 | 설정된 후보 | 최대 authored 단계 |
| --- | --- | --- |
| Swordsman | Early Slash / Early Smash / Pierce | 2 / 1 / 2 |
| SwordShield | SwordCombo / Pierce / ShieldCrash | 2 / 1 / 1 |
| HeavySwordsman | SwordSwing01 / SwordSwing02 / SwordSwing03 / SwordSwing02 첫 단계 회복 | 4 / 2 / 3 / 1 |
| HalberdElite | Early Swing / Early Pierce / Early Push | 3 / 2 / 1 |

각 후보는 기존 `UKZComboActionAbility` 파생 **데이터 BP**다. `DA_Combo_*`의 각 node는 한 Montage section을 가리킨다. section NextSection은 None이고, 원작 change-step event를 저장된 playback 시간으로 변환한 지점에 Montage `InputEnd` branching-point notify를 둔다. 해당 node의 InputEnd command edge가 다음 node로 연결된다.

AI는 연속을 선택한 실행에만 `SubmitComboCommand(Command.Player.Attack.X, Begin)`을 제출한다. 이 기존 태그는 재사용하는 공통 combo 의도 키이며 실제 게임패드 버튼을 누르는 것이 아니다. InputEnd에서 기존 ASC/ComboAction이 held 의도를 받아 section 전환한다. 연속을 선택하지 않으면 첫 단계의 원래 회복까지 재생한다. Exit에서 Cancel로 자기 held 의도를 반환한다.

원작 `FindTarget`/거리 조건의 모든 실행 의미·StartEnd/Tick 평가 주기는 재현하지 않았다. 저장된 event window의 첫 시각을 project InputEnd 지점으로 매핑하고 StateTree의 대상/거리와 연속 선택으로 조건을 단순화했다. **Halberd Push의 AttackSuccess 의존 후속 단계는 hit producer가 없으므로 제외**했다. 누락된 Heavy SwordSting/Halberd RoundAttack 원본 Skill JSON을 추측해 새 패턴을 만들지 않았다.

## 에셋과 포즈 경로

- 캐릭터: `/Game/Bluprints/Monsters/BP_Monster_{Swordsman,SwordShield,HeavySwordsman,HalberdElite}`.
- 데이터·Ability·Montage·ABP·BlendSpace: `/Game/Monsters/<Family>/{Data,Abilities,Animations}`.
- 실제 gameplay 시퀀스만 `/Game/Monsters/<Family>/Animations/InGame`에 기존 Art Playback에서 복제한다. 원본 Art 시퀀스의 키/FPS/RateScale을 재임포트·재타이밍하지 않는다.
- 기존 AssetData에 `MonsterDefinitions` 그룹으로 네 CharacterDefinition을 preload 등록한다. Player registry를 보존한다.

새 ABP 부모는 기존 `UKZAnimInstance`. Peace/Combat BlendSpace의 X=MovementDirectionAngle(deg), Y=GroundSpeed(cm/s), RotationMode enum으로 선택 → DefaultSlot → Inertialization → Root다. Idle/일반 Walk/Run과 전투 Stand/LockOnWalk F/R/B/L을 사용한다. 방향 대각선은 BlendSpace 보간이며 8개의 서로 다른 원본 클립을 확보했다고 표현하지 않는다. chase에는 Run_F를 사용한다. Player ABP/UpperBody/Arms 경로는 변경하지 않는다.

gameplay clone은 `EnableRootMotion=false`, `ForceRootLock=true`, `RootMotionRootLock=RefPose`다. 실제 이동은 CMC/nav, 공격은 이번 범위의 animation-only 표현이다. 원본 루트 궤적을 gameplay capsule에 추가 구동하는 설계는 아니다. root track/스켈레톤 경로 확인 결과는 `Metadata/MonsterAI_20261006/RootPoseAudit.json`에 저장한다.

기존 Art assembly의 mesh/material/socket/equipment를 새 Character BP에 복사한다. Human 두 종은 기존 Human skeleton과 body scale1.2, Heavy는 Elite skeleton의 empty pose carrier와 body scale1.3/갑옷3개/weapon, Halberd는 전용 skeleton/body scale1.0이다. Heavy armor에만 `MonsterBodyPart` 태그를 두고 Monster BeginPlay에서 기존 leader-pose API로 본체 mesh를 따라가게 한다. Player body0.01/weapon0.009를 Enemy에 적용하지 않는다.

## 수치 출처와 임시 조정 기준

원본·계산·임시를 섞지 않는다.

1. **원작 직접 자료**: `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/…/SB_*.json`의 CDO `SubStateInfos.Value.SkillAnimation`, `AnimPlayRate=1`, `AnimLoopCount=1`, `AnimBlendAlpha`, `SkillEventMap`의 `xxChangeNextStepFunc.NextSubStateStep`, 대응 AC notify Index. 정확한 파일/field/원시 event는 `OriginalSkillAudit.json`과 `AuthoringPlan.json`에 보관한다.
2. **원작 기반 계산**: `PlaybackEventTimes.json`의 source event time와 원본 time-dilation curve로 만든 `playback_start_seconds`를 InputEnd에 사용한다. 몽타주 위치=`앞 section들의 segment 길이 합 + playback_seconds / AnimPlayRate`. 저장 Playback의 실제 길이/FPS/RateScale은 `AnimationLibrary.csv` 출처이며 추출/임포트 결과와 원본 field를 구분한다.
3. **원작 원시 값의 project 해석**: 첫 단계 `AnimBlendAlpha` 값(.1/.2/.25/.3 등)을 montage BlendIn seconds에 대응시켰다. 원작 field의 실행 코드/단위가 확인된 것은 아니며 동일 시간 의미라는 project 가정이다. 나머지 combo inertia=.1s, exit/BlendOut/로코모션 모드 전이=.2s는 임시 표현 튜닝값이다. 각 GA/Montage/ABP 소유 설정에서 조정한다.
4. **원작 기반 크기 계산**: 원본 CB capsule HalfHeight·Radius에 CDO Scale을 곱한다. Human HH85cm×1.2=102cm/Radius32×1.2=38.4cm, Heavy HH95×1.3=123.5cm, Halberd HH140×1=140cm. body offset Z=-scaled HH. CB 경로/원시 값은 `OriginalSkillAudit.json`/plan이다. LockOnTargetPoint Z=HH×.5는 임시 표시 위치다.
5. **기술적 표현**: 360도 방향 주기/정규화/접선의 직교 연산, 부호 -1·0·+1, 상태 0 초기화, section/grid 반올림은 기하학·엔진 표현이며 원작 gameplay 튜닝값으로 분류하지 않는다.

`OriginalSkillContext.json`에는 별도 SI.EndCooltime(예: Early Slash raw5.0)와 SB 내부 TargetCondition의 Min/MaxDistance·FrontBaseAngle을 보관한다. 이 자료가 존재함을 숨기지 않는다. 다만 combo-local 조건을 초기 AI 선택 거리로, skill-local cooldown을 전역 행동 간격으로 동일시하지 않았으며 이번 StateTree interval에 직접 적용하지 않았다. CB의 AIDataAsset 참조는 있지만 해당 AI_ 원본 JSON/실행 코드는 현재 표적 저장 자료에 없다.

현재 필요한 AI 값은 **원작 근거 미확인의 임시 튜닝값**이며 `FKZMonsterAISettings`/Monster BP defaults 한 소유 설정에 모았다.

| 설정 | 현재값·단위 | 선정 의도 / 조정 기준 |
| --- | --- | --- |
| Sight / LoseSight / half-angle | 1400 / 1800cm / 90deg | DevMap에서 근접 전 감지, 거리 hysteresis. 너무 일찍/늦게 붙으면 범위 조정 |
| memory / home leash | 4s / 3000cm | 잠깐 시야 상실 추적, 테스트 구역 이탈 제한. 장애물 테스트로 확인 |
| Engage / preferred / attack | Sword350/240/310, Shield340/230/300, Heavy410/285/365, Halberd540/385/490cm | 무기 길이에 따른 표시 간격. capsule center 간 2D 거리이며 hit reach 검증값 아님 |
| tolerance / facing half-angle | 45cm / 45deg | 잦은 거리 보정/등 돌린 공격 방지. 진동·허공 공격 관찰 후 조정 |
| 공격 간격 / 대치 | 2–4s / 1–2.5s | 여러 패턴과 횡이동을 관찰할 수 있게 선택. 원작 SI cooldown과 별개 |
| strafe goal / refresh | 160cm / .35s | 원형 대치 목표를 적당한 간격으로 갱신. 걷기 방향과 경로 떨림 확인 |
| combo / left-pause-right | .75 / 같은 확률 | 단일 회복과 연속을 모두 관찰. 원작 확률 미확인 |
| patrol / idle / patrol chance | 300cm / 2–5s / .5 | 출발점 주변 Idle/배회 혼합. 원작 AI값 아님 |
| nav acceptance / retry | 35cm / .5s | 도달/실패 재요청 관리. 경로 실패·정지 떨림 확인 |
| Walk / Run | Human·Heavy180, Halberd200 / 모두420cm/s | 기존 playback을 테스트할 임시 속도. 원작 stride 일치 미검증 |

CharacterDefinition의 가속/제동1800cm/s²·회전540deg/s·최저 analogue speed15cm/s는 기존 공통 설정의 기본값을 유지한 것이며 원작 검증값이 아니다. sprint는 사용하지 않고 max gait=Run이다. 장애물 경로와 CMC RVO avoidance를 사용한다. 실제 hit가 없으므로 collision attack reach/경직/죽음 수치를 이 표에서 확정하지 않는다.

## DevMap 직접 확인 방법

Outliner `DevMap/Monster AI` 폴더에 네 `DevAI_<Family>` actor가 있다. PlayerStart 주변 기존 지형을 유지하며 초기 배치는 Swordsman(1900,-1300), SwordShield(1900,1300), Heavy(-1900,1300), Halberd(-1900,-1300)cm다. 테스트 배치 수치는 원작 level 배치 재현값이 아니다. Capsule HalfHeight에 맞춘 Z로 바닥에 선다. 기존 Definition 없는 `TEST_Monster` 네 fixture를 대체한다.

1. DevMap PIE에서 한 몬스터의 시야 정면으로 접근한다. 처음에는 Idle/배회, 감지 후 준비 동작, 이어 달려 접근해야 한다.
2. 가까이 머문다. Player를 보면서 단일/연속 공격, 걷기 대치, 좌우/정지 선택이 반복돼야 한다. 바로 직전 공격 class는 연속 재선택에서 제외한다.
3. 뒤로 물러난다. 공격 실행 회복이 끝나면 다시 추적해 공격/대치 범위로 접근해야 한다.
4. 시야/출발점 구역에서 크게 벗어나면 기억/leash 정책에 따라 전투를 해제하고 배회/복귀한다.
5. 네 종류의 mesh/무기/갑옷과 방향 전환을 확인한다. 이번에는 공격이 플레이어 HP를 줄이지 않아야 한다.

자동 검사는 `Khazan.Monster.PIE`다. 실제 Sight/Nav/CMC/ASC를 사용하고 native fixture가 Player를 테스트 위치로 옮긴다. 키보드나 Python 이동 입력을 주입한 검사가 아니다. 콤보 모든 section/종료/UnPossess cleanup, HP 불변을 검사한다. `Khazan.Heal.PIE`, `Khazan.Guard.PIE`로 기존 기능 회귀를 확인한다. 물리 장치·연속 화면 보간 품질·원작 AI 선택 확률의 동일성은 별도 검증이다.

## 재현 도구와 결과 위치

- `Scripts/Engineering/prepare_monster_animation_manifest.py`: 저장 자료를 표적 읽어 `OriginalSkillAudit/Context`, `AuthoringPlan` 생성. 읽기 전용 원작 분석.
- `Scripts/Engineering/MonsterAuthorEditor.cpp`: 격리 work 프로젝트에만 일시 포함하는 public editor API authoring 도구. 제품 Build.cs에 editor-only 의존성을 넣지 않는다.
- `Scripts/Engineering/monster_isolated_editor.py`: 엄격한 별도 프로젝트 identity의 에디터 mailbox/PIE lifecycle. 입력 주입 없음.
- `Metadata/MonsterAI_20261006`: 원작 근거, Intake, build/PIE 실패와 최종 결과, 저장 reload, 전달 manifest.
- 격리 work: `C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan`.

nav volume 생성은 단순 SpawnActor/Builder.Build만으로는 실제 brush model이 생기지 않았다. 공개 `UActorFactory::CreateBrushForVolumeActor`로 brush model을 만든 뒤 nav bounds(±3900cm, Z±300cm)/build 완료/실제 nav projection을 검증한다. 첫 실패 기록을 남기고 통과로 해석하지 않는다. authoring 재실행은 work의 자기 `DevAI_` actors/새 assets만 대상으로 하며 사용자 Art library/Player graph를 일괄 덮어쓰지 않는다.

## 2026-10-06 — 구현·제품 검증·메인 반영 완료

앞의 진행 중 상태를 이 절의 실제 결과로 대체한다. Source/runtime4파일과 기존 연결을 적용했고 공통 StateTree1, character BP4, ABP4/BS8, attack GA13+Alert GA4, ComboData17/Montage17/CharacterDefinition4, gameplay InGame sequence60을 작성했다. 필요한 StateTree/GameplayStateTree plugin과 AIModule/StateTreeModule/GameplayStateTreeModule만 제품에 추가했다. editor-only author cpp와 의존성은 work에서 제거했다.

제품 stock build Succeeded(ColdBuild_Stock3/ColdBuild_VisualCapture). 실제 격리 PIE: Guard10:59:29.428 UTC/Heal10:59:57.988/Monster11:02:54.097 Success. 캡처만 보완한 최종 Monster11:16:15.957 Success도 확인했다. 네 종류의 Alert/Chase/Attack/Standoff/재추적·actual nav 이동/Player focus/lateral 대치, 공격13개 모든 authored section, capsule animation-only 고정/HP 불변, 자연 end 이동 태그 해제, UnPossess/repossess·held cleanup을 검사했다. 카메라를 상대 방향으로 돌리고 deferred screenshot 완료 후 teleport하여 검증 이미지의 fixture 잔상을 제거했다. 일반 게임 motion blur/연속 화면 보간과 원작 AI 정책 동일성을 전수 검증한 것은 아니다.

원본 clip60개 main/work SHA 동일. 현재 main skeleton3개를 재snapshot해 DefaultSlot만 추가한 뒤 기존5package를 hash 백업하고 선택137package(새132/기존5, 약42.5MB)만 설치했다. 기존5는 DevMap/PDA_AssetData/skeleton3이다. 기존 main dirty0/PIE 없음/PID27916 normal quit→선택 copy/모든SHA 일치→ColdBuild_Main Succeeded→새 main PID11000/DevMap read-only reload를 확인했다. BP4/ABP4 UP_TO_DATE, sequence60/root policy 정상, DevAI_ actors4+nav1, legacy fixture0, dirty map/content0, game world 없음. 기존 Player BP/ABP/Controller/Heal source4개와 source clip60개 SHA 보존. Main 자동 gameplay 테스트는 실행하지 않았다.

결과: Metadata/MonsterAI_20261006/RuntimeResult.json, PIE_Stock_Final.log, MonsterPIE_Visual_Final.log, SavedAssetAudit_Stock_Final.json, MainReadyAudit.json, FinalHashVerification.json, AssetInstallManifest.json, SourceDeliveryManifest.json, DeliveryVerification.json. 기존5 byte backup은 Saved/MonsterAI_20261006/Before/Manifest.json, 준비본은 ReadyContent다. Work editor는 원래 background throttle true를 복원하고 정상 종료했다. 반영/helper/authoring 대기 작업이 없다.

해결 기록: empty nav brush/public actor factory, editor API 맞춤, 시야 fixture의 actor-forward 배치, PIE 중 asset API 호출 제거, listener ctor 설정, stock 복원의 cached build-rule timestamp/NoUBTMakefiles, MSVC1455 paging/PCH 부족의 NoXGE·MaxParallelActions=1 재빌드. 최종 build 성공과 최초 실패 로그를 구분해 보존했다. 전역 paging/compiler/background 설정은 변경하지 않았다.

다음은 사용자의 DevMap 직접 Play·정면 접근·가까이 대치/후퇴 화면 QA다. 수치는 AISettings 또는 해당 GA/Montage/ABP owner에서 조정하며 원작/계산/임시 출처 구분을 유지한다. 실제 피해/피격/Guard producer/death·원작 AIData/skill cooldown 선택 복원은 별도 요청 범위다. 완료된 authoring/retime/전체 복사를 반복하지 않는다. 저장 메타데이터/이번 정본과 현재 Source에서 새 증상을 좁힌다.

## 2026-10-07 — 재개 요청 후 실제 반영 상태 확인

현재 main의 Source13파일/선택 에셋137package가 최종 전달 manifest의 SHA256과 전부 일치하며 누락/차이0이다. 기존 메인 build Succeeded와 Monster·Heal·Guard PIE Success도 로그에서 확인했다. `Metadata/MonsterAI_20261006/ResumeAudit_20261007.json`에 이번 확인을 저장했다. 이어서 적용해야 할 구현·전달 단계는 없다.

이번 확인 당시 UnrealEditor 프로세스/Rider UE 연결은 없었다. 새 build/PIE/에디터 reload나 gameplay 수정은 수행하지 않았다. 앞 절의 검증과 미검증 구분을 유지하며 다음 직접 확인은 메인 `/Game/Maps/DevMap`의 `DevMap/Monster AI` 네 actor를 대상으로 한다.

## 2026-10-07 — Idle/Patrol·실제 보행 설명의 현행 대체

이 문서 초기 IdlePatrol과 보행 설명은 [MONSTER_UNAWARE_LOCOMOTION_20261007.md](MONSTER_UNAWARE_LOCOMOTION_20261007.md)의 최종 완료 절이 해당 범위에서 대체한다. Idle은 정지 Loop/대응 End, 선택적 mutual Talk pair, Patrol은 별도 이동, combat Stand는 미발견 Basic Loop와 분리됐다. BS 입력 binding 누락을 실제 actor-speed/player/mesh 관측으로 확인·수정했고4종32방향 및 별도12FPS Halberd8/Waiting/SourceAudit/Heal/Guard가 성공했다. 메인129 scoped package/원본32 hash/cold build/saved reload 완료, Main26644 DevMap/PIE없음/dirty0다. 이전60 original hash 중 BasicLoop01의 사전 main 변경과 이번32 raw pose/FPS/RateScale 대조를 구분한다. 상세 수치/임시 설정/한계·실패 기록은 새 정본/Metadata를 읽으며 기존 완료 author·retime·전체 복사를 반복하지 않는다.


## 2026-10-08 15:00 KST ? ??? 6? HP?Stamina ?? ?? Main ??

?? ??? ??? ?? ???? **???**??. ?? `UKZAttributeSet`? HP/MaxHP/Stamina/MaxStamina? `UKZCharacterDefinitionData.InitialEffects`? ??? ????. ? C++ ??????????runtime ??? ??? ????????????? ??/???UI?AI ??? ???? ???. ?? ??? 2026-10-08 ??? ?? ????? ?? ????? ???? ???. ???? ???? ?? ??? ????.

| ??? ?? / ?? family | HP = MaxHP | Stamina = MaxStamina | ?? ?? |
|---|---:|---:|---|
| Swordsman | 100 | 50 | ?? ?? CharacterDefinition |
| ShieldMan / SwordShield | 100 | 50 | ?? ?? CharacterDefinition |
| HeavySwordsman | 200 | 50 | ?? ?? CharacterDefinition |
| HalberdElite | 200 | 50 | ?? ?? CharacterDefinition |
| Apes / ApesStoneHandElite | 400 | 100 | Definition + ??? GE ??? ?? |
| Yetuga | 1000 | 150 | Definition + ??? GE ??? ?? |

?? ??? `/Game/Monsters/<family>/Effects/GE_Init_<family>`? `/Game/Monsters/<family>/Data/DA_Character_<family>`?. ? GE? ?? Player Health/Stamina ??? GE? ?? GameplayAttribute ??? ??? data-only UGameplayEffect Blueprint?? Instant/Override?. modifier ??? **MaxHP ? HP ? MaxStamina ? Stamina**?. ?? AttributeSet? ???? ????? clamp??? ???? ?? ?????. ?? `AKZCharacter::PostInitializeComponents`? GameWorld/authority ??? ??? ?? ??4? Definition? InitialEffects? ????. ? ?? ??? ?? ???? ???? ?? ???? PIE ?? ??? ???? ???.

??4?? ?? InitialEffects? ?? ??? ??? ? ?? GE1?? ????. LocomotionConfig/UnawareRoutines/InitialAbilityGrants? ?? ?? export ??? ????. Apes/Yetuga? ?? BP? Art? Actor assembly??? ??? GAS character? reparent??? ???AssetData registry?AI?DevMap? ???? ???. ?? Definition ??? ?? DA2?? InitialEffects? ?????, ?? locomotion ??? ?? ?? ???? ?? AI ???? ???? ???. ?? ?? gameplay monster? ??? ? ? DA? ?? character ??/?? ??? ????.

?? ??? GE6 ??, ?? DA4 ??, Apes/Yetuga DA2 ??? **12 uasset**??. Player GE2? ?? ?? template?? ???? ?? Main/Work SHA ?? ??? ????. ?? Source/Config/?? ???manifest95??? ?? ?? ? fresh Main ?? ? SHA ????. ??? ??? `Scripts/Engineering/configure_monster_initial_stats_20261008.py`(Work ??, ?? ??? ??)? `verify_monster_initial_stats_20261008.py`(?? ??)?? ?? Source? ???.

??: ?? Work ?? PID15348?? ??, ? Work commandlet PID28116 ? ? hidden Main commandlet PID27884?? 6?24modifier? ?? `/Script/Khazan.KZAttributeSet:<field>` ??????Override?????Instant?UP_TO_DATE?Definition ??? ???. ? saved reload ?? ??, dirty content/map0?? own editor?? ?? ????. Main PID24552 ?? ??? ?? ?? ???? ???, ?? Unreal editor process0? ??? ? ??4? backup/CAS? ??12?? ????. ??? editor? ????? ???? ???. ? native build/PIE/????? ?? ??? ???? ???.

?? ? ? nested magnitude setter? EditDefaultsOnly instance ??? ????. ? Swordsman ???? Work ????? ??? ?? backup copy? ???? ???. ?? Player GE? Main? ???? ????, ?? ??? ???? ??? ? ?? StructBase.copy/export_text/import_text? scalar? ?? ?????. ?? binary backup ??? ???? ???.

?? ??? `Metadata/MonsterStats_20261008/FinalVerification.json`??. `Configured.json`? ??/?? Definition ??, `WorkSavedReload.json`? `MainSavedReload.json`? ?? ?? ???, `PreparedManifest.json`? `Delivery.json`? ??12? ??, `Baseline.json`? `Before/`? ??4?/Player template ??, `MainProtectedBefore.json`? ??95? ???. Delivery.json? main_saved_reload_verified=false? **?? ??** ???? ?? ??? FinalVerification.json?? ????.

?? ??? ?? ??/?????/?? ????. ??? ????? ??? ? GE_Init_<family>? Modifiers? ?? ???/??? ? ? ?? ??? ?? ????. ?? ?????? ?? authoring?? ?? ??? author/retime/delivery? ???? ???.


## 2026-10-08 15:52 KST — MonsterStamina 작업 중 및 이전 stats 기록 가독성 보충


기존 15:00 KST 몬스터 초기 수치 기록의 일부 한국어가 작성 과정에서 물음표로 손실되어 이 절에 가독성 있는 사실을 추가한다. 이전 기록은 삭제하지 않는다. 몬스터6의 GE_Init/CharacterDefinition 12개는 이미 Main 적용과 fresh saved readback을 완료했다. 값은 Swordsman/SwordShield HP100·Stamina50, HeavySwordsman/HalberdElite HP200·Stamina50, Apes HP400·Stamina100, Yetuga HP1000·Stamina150이고 모두 current=max이다. 근거는 Metadata/MonsterStats_20261008/FinalVerification.json complete=true 및 WorkSavedReload/MainSavedReload.json이다. 그 작업은 설정만 한 것으로 소진/회복/피격 기능 완료와 구분한다. Player 초기 GE2와 당시 Source/Config를 보존했다. Apes/Yetuga 당시에는 Definition/GE만 있고 gameplay BP/registry 연결은 없었다.

새 사용자 요청은 여섯 몬스터 공통 무자동회복·무공격Cost, 편집 가능한 피격/패링 감소량, 스태미너0 소진, 브루탈 어택의 양쪽 정상 완료 후 생존 MaxStamina 회복이다. 상세 계약과 수치 출처/미확인은 Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md를 따른다. 현재 native 구현은 별도 Khazan_MonsterWork_20261006/Khazan에만 있으며 Main 게임 Source/에셋 미전달이다. 첫 빌드는 다른 editor의 전역 LiveCoding mutex로 거부되어 독립 Work 출력에 NoHotReloadFromIDE로 재시도 중이다. 실제 성공 전 build/PIE 완료로 쓰지 않는다.


## 2026-10-12T14:44:13+09:00 — 검병 발차기·돌진 제외 Main 완료 / 방패병 동작 식별 대기

사용자 요청으로 검병 GA_Kick와 GA_Rush를 기존 BP_Monster_Swordsman.AttackAbilities 및 DA_Character_Swordsman.InitialAbilityGrants에서 제외했다. 공격 후보5→3, 초기 grant14→12다. 남은 GA_EmpireSword_Early_Slash/Early_Smash/Pierce 및 Alert/Idle/Exhaustion/HitReaction은 유지한다. 기존 ARCH-77 StateTree 선택→ASC Spec 활성화→ComboAction 실행을 재사용하며 runtime C++/Tag/Config/DLL 변경0이다. 게임 리소스 삭제·montage/animation/collider/VFX/피해 설정 수정0, 새 runtime file/class0이다. 별도 Khazan_AttackFilterWork_20261012에서 두 asset만 저장했고 Main에 exact SHA/CAS로 전달했다. Prepared02 및 새 MainSaved01 Success/Exit0, AttackAbilities/InitialAbilityGrants와 보호된 AI/Locomotion/HitReactions/MonsterStamina/Unaware/InitialEffects의 원본 보존을 확인했다. DevMap 배치 검병7개 모두 후보3, 방패병1개 후보3을 fresh load로 확인했다. HeinMach에서 해당 두 BP의 배치 actor는0이다. 이는 saved policy 검증이며 새 PIE 실행·제자리 달리기 체감 검증으로 기록하지 않는다. 방패병은 수정 전후 모두 SwordCombo/Pierce/ShieldCrash 후보3, 초기 grant8이며 Kick 클래스가 없다. 두 방패병 asset의 byte SHA는 원본과 동일하다. 사용 중4개 sequence의 raw 발/골반 포즈41시점은 Probe02에 보관했지만, 수치만으로 사용자가 말한 발차기 동작을 확정하지 않는다. 방패치기인지 검 연속공격인지 사용자에게 동작 식별을 질문한 상태다. 임의로 sword swing이나 ShieldCrash를 제거하지 않았으며 방패 동작 제외는 미완료/식별 대기다. 정본은 Metadata/MonsterAttackFilter_20261012/FinalVerification.json 및 ResumeState.json. 확인 후 current Main의 해당 후보/grant 또는 실제 kick node만 작은 data 변경으로 제외하고 새 saved/배치 actor 검증을 수행한다.

<!-- MonsterAttackFilter_20261012_SwordsmanMainVerified -->
