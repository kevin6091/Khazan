# 2026-10-07 몬스터 공격 확장·Root Motion·재추격

## 적용 범위

ARCH-79 후속 구현이다. 기존 StateTree/Controller, Monster AISettings, CharacterDefinition의 Ability grants, UKZComboActionAbility와 ComboDefinition/Montage를 재사용한다. 새 runtime C++ 파일/class/component/manager는 0이다. 변경 소스는 `KZMonster.h`, `KZMonsterStateTreeNodes.cpp` 및 development 검사 `KZMonsterAIPIETest.cpp`다. KZComboActionAbility.cpp와 공통 Player/ASC/Locomotion 구현은 수정하지 않았다. 이번 절은 별도 workspace의 실제 적용이며 메인 반영·최종 검사 결과는 하단에 추가한다.

## 공격 데이터

| 종류 | 기존 | 신규 | 합계 | 사용 Attack 시퀀스 |
|---|---:|---:|---:|---:|
| Swordsman | 3 | 2 | 5 | 12 |
| SwordShield | 3 | 0 | 3 | 4 |
| HeavySwordsman | 4 | 3 | 7 | 14 |
| HalberdElite | 3 | 17 | 20 | 38 |
| 전체 | 13 | 22 | 35 | 68 |

Swordsman은 Rush/Kick, Heavy는 SwordSting/좌우 Turn을 추가한다. Halberd는 normal Swing/Pierce/Push와 EarlyPush 후속, Round/DownUpperSlash, normal/Early SprintSwing, BackDashCounter, GuardCounter 3분기, Charge 2변형, Smash 및 Turn 2변형을 추가한다. 기존 SwordShield 3패턴이 이미 4 Attack 클립을 모두 사용하므로 중복 패턴을 만들지 않았다. 연속 같은 공격은 기존 LastAttackClass 제외 정책을 그대로 사용한다.

준비→한 번의 finite Loop→타격→회수처럼 반드시 이어져야 할 경로는 한 `Action` node와 여러 montage segment로 묶는다. 준비만 재생하고 combo RNG가 종료시키지 않는다. 단일 Loop 횟수 1은 원작 조건 producer가 없는 현재 animation-only finite 경로 선택이며 원작의 무한 유지/적중 조건 재현을 뜻하지 않는다. 여러 공격 단계의 조건부 콤보는 기존 X held/InputEnd edge로 다음 section에 들어간다.

원본 saved SB의 `SubStateInfos`/`AnimPlayRate`/`SkillEventMap` 및 `PlaybackEventTimes.json`을 표적 읽었다. 정확한 source file/field/event와 없던 자료는 `AllSavedSkillAudit.json`/`AttackExpansionPlan.json`에 남겼다. 원본 next-step notify가 확인되면 그 playback time를 사용한다. 확보하지 못한 경우 현재 imported sequence 길이로 finite 전이를 구성한다. 닫힌 section 끝 시각과 동일한 InputEnd는 엔진 종료 경계에 걸리므로 최종 fallback은 `min(확인한 전이 시간, GetPlayLength - 1 / 실제 GetFrameRate)`다. 이 마지막 샘플 이전의 안전 전이는 현재 구현 정책/원본 기반 frame 계산이며 원작 직접 notify 값이라고 표현하지 않는다. 원본의 더 이른 notify는 유지한다.

Guard/hit/target 조건의 원작 producer, 피해/피격은 추가하지 않았다. GuardCounter의 여러 분기는 현재 각기 선택 가능한 animation 경로다. 발리스타는 장치 의존 Interaction, FootSword는 Equip, DamageGrapple은 피해자 반응이므로 melee Attack 후보 68개의 분류에서 제외한다. Yetuga/Apes의 새 AI/Ability 실행은 이 작업 범위가 아니다.

## 공격 빈도와 값의 출처

현재 CanChooseAttack은 거리·정면 각도·NextAttackAt의 gate이며 독립적인 공격 선택 확률은 없다. gate를 만족하면 Root의 Attack이 Standoff보다 우선한다. 신규 확률 상태를 만들지 않고 기존 AttackIntervalSeconds와 ContinueComboChance를 조정했다.

| 설정 | 변경 전 | 변경 후 | 출처·의도 |
|---|---|---|---|
| AttackIntervalSeconds | 2..4초 | 2/1.1..4/1.1초 ≈1.818..3.636초 | 기존 임시 cooldown의 역수 빈도를 약 10% 증가 |
| ContinueComboChance | .75 | .85 | 임시 조정: 콤보 지속 +10 percentage points |
| ChaseReactionSeconds | 없음 | .4초 | 어시스턴트 선정 임시 반응 시간 |

4 BP의 변경 전 값은 stock 원본 module/byte-identical package에서 읽어 `AITuningPlan.json`에 고정했다. 재시도에서 interval을 반복 나누지 않는다. 정확한 전체 전투 빈도 +10%를 보증하는 수치가 아니다. Attack 길이·거리·방향 및 기존 StandoffSeconds도 실제 빈도에 영향을 준다. 위 값은 원작 AIData 확인값이 아니며 Monster BP의 AISettings/원래 설정 owner에서 조정 가능하다. .4초를 사용자가 지정한 값이라고 기록하지 않는다.

## 재추격의 실제 수명

기존 Standoff Task의 TimeRemaining은 한 번 선택한 좌/정지/우 구간을 마칠 때까지 유지한다. 플레이어가 EngageDistance 밖으로 나가면 마지막 local MoveGoal을 마치며 ring을 계속 옮기지 않는다. Attack Task도 자기 Spec이 active인 동안 Running이다. 이 기존 완료 계약과 persistent BattleTarget을 유지한다.

Chase Enter는 기존 StopRequestedMove 이후 `Data.TimeRemaining = Settings.ChaseReactionSeconds`로 초기화한다. Chase Tick은 타깃이 가까워졌으면 즉시 정상 완료하고, 여전히 멀면 game-thread DeltaSeconds로 남은 시간을 감소시킨다. 시간이 남아 있으면 Running을 반환해 아래 MoveTo 호출까지 내려가지 않는다. 만료 후 기존 Navigation 요청을 수행한다. 초기 발견 후 Chase에도 같은 반응 시간이 적용된다. 별도 timer/enum/bool/컴포넌트나 target 상태 사본은 추가하지 않았다.

이 변수의 작성자는 Chase Enter/Tick, 소비자는 같은 Tick의 navigation gate다. 타입 float, 단위 world game seconds, instance data 수명이며 매 Enter에서 초기화된다. 타깃 무효/UnPossess/EndPlay는 기존 task/controller cleanup을 따른다. 액션의 실행·입력 수명과 취소는 기존 Ability/ASC 소유다. worker AnimInstance가 ASC/Controller를 변경하지 않는다.

## Root Motion 소비

모든 대상 시퀀스의 활성화/잠금 옵션과 원본 보존은 [Art 정본](../Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md)을 따른다. 현재 4 NPC의 기존 RootMotionFromMontagesOnly에서 공격 몽타주의 실제 root delta가 CharacterMovementComponent를 이동시킨다. 기존 Block.Movement.Input은 navigation/input을 제한하며 root delta를 지우는 코드를 새로 추가하지 않았다. Actor/mesh scale은 기존 값이다.

Nav 보행은 기존 실제 velocity→방향별 pose/Foot Placement를 유지한다. RootMotionFromEverything 보행을 구현했다고 기록하지 않는다. 기존 Player .01 scale 및 Heal/Guard 구조는 이 변경의 대상이 아니다.

## 검증 상태와 실패 보존

최초 stock 4종 native PIE는 32 방향별 보행/foot pace, 기존 공격과 신규 finite Action의 root 이동 및 cleanup/HP 불변을 관측했다. 신규 조건부 combo 6개의 InputEnd가 닫힌 section 끝에 있어 후속 단계가 누락됐다. 해당 montage data의 마지막 sample 기준으로 경계를 보완했다. SwordSting의 windup-only/root 이동 0도 같은 실패였다. 게임 ComboAction 코드를 재작성하지 않았다.

최초 일반 retreat fixture의 700cm 이동은 committed root-motion 공격이 플레이어를 따라잡아 Chase가 필요 없어진 사례였다. QA 배치는 기존 LoseSightRadius+PursuitLeashRadius만큼 멀리 두고 실제 action 완료/Chase를 기다리도록 수정했다. 이를 AI가 target을 잃었다고 판단하지 않는다. Focused CombatPolicyPIE는 기존 구간 완료/target 유지/추가 .4초 동안 nav 요청 없음/후속 물리 추격을 4종에서 Success로 확인했다. WaitingPIE의 Solo/Talk/대응 End도 Success다.

최종 source/attack 검사와 메인 build/saved readback은 완료 절에 실제 결과로 추가한다. `PreparedDeliveryManifest.json`은 전달 후보이며 전달 완료 증거가 아니다. 임시 author cpp/dependency는 실제 stock 검사 전에 제거한다. Python으로 Player 이동/키입력을 주입하지 않고 기존 C++ PIE fixture/엔진 API를 사용한다. Main 전달은 최신 unrelated Source/Config와 개별 package hash를 검사하고 이 작업 파일만 반영한다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

ARCH-79 실제 완료다. 기존 StateTree/AISettings/CharacterDefinition grants/ComboAction/ComboDefinition/Montage를 재사용했다. runtime 새 파일·class·component·manager는0, 실제 gameplay Source는 KZMonster.h와 KZMonsterStateTreeNodes.cpp 두 파일이며 기존 development KZMonsterAIPIETest.cpp를 보완했다. Player/ASC/ComboAction 실행 코드를 재작성하지 않았다.

공격은13→35(Swordsman5, SwordShield3, Heavy7, Halberd20)이며 해당4종 Attack68클립을 모두 연결했다. finite 준비/loop/타격/회복은 같은 Action 안에서 필수 순서를 유지하고 실제 combo만 기존 held X/InputEnd로 잇는다. 신규 combo6개의 끝 경계 InputEnd 실패는 montage data에서 마지막 sample 이전으로 보완했다. 정확한 시간식과 원작 SB/file/field는 MONSTER_ATTACK_ROOT_MOTION_20261007.md 및 AttackExpansionPlan.json/AllSavedSkillAudit.json을 따른다. 원작 hit/guard 조건 producer나 피해/피격을 새로 구현한 것은 아니다.

현재 공격 선택에는 독립 RNG probability가 없고 거리/각도/cooldown gate를 쓴다. 기존 임시 interval2..4초를1.1로 나눠1.8181818..3.6363636초로, combo continuation .75→.85(+10percentage points)로 설정했다. 전체 공격 빈도의 정확한10%를 보장하는 통계 수치가 아니다. ChaseReactionSeconds .4초는 assistant 임시 tuning이며4BP AISettings에 저장했다. 선택 Standoff/Attack을 끝낸 뒤 Chase에 진입하고 기존 task TimeRemaining을 Enter에서 설정/Tick에서 감소시켜 nav 요청을 잠시 보류한다. 첫 Chase에도 적용한다. 타깃 유지/기존 cleanup을 보존한다.

stock SourceAnimationAudit813/18,958,755 raw transforms·곡선/선택 metadata 동일 Success; compressed root QA .01cm/normalized angular1e-4rad는 기술 허용 오차다. raw tolerance1e-6와 구분하며 실제 최대 압축 positional 차이.0060654cm였다. AttackPatternsPIE 최종35개/모든 section/actual root travel/HP 불변·취소 cleanup·네 종 실제 rechase Success. CombatPolicyPIE 네 종 선택 행동 완료/시야 밖 target 유지/.4초 nav hold/후속 물리 추격 Success, Waiting/Heal/Guard PIE Success. 최초 full Monster.PIE의32 방향보행/contact sample min11·median0cm/s는 통과했으며 montage notify만 보완한 뒤 중복 walk 검사는 반복하지 않았다. retreat fixture는 Root lunge로700cm를 따라잡는 문제와 nav 밖5000cm 배치 문제를 각각 보존하고, 최종8후보 projection+complete path 및 Chase 진입 이후 physical advance로 검사했다.

Main 선택 전달은 파일981개(기존69/신규경로912), 이름 변경 옛 파일802개를 정확한 path/hash guard 뒤 제거했다. backup Before와 실패 로그를 보존한다. 미관련 Source/Config86 및 Archer177개 hash를 보존했다. Main stock cold build Succeeded, fresh Main PID3528 /DevMap/4BP·ABP UP_TO_DATE/813 options·35 grants·68 clips/저장값 재확인/PIE없음/dirty0이다. 자동 Main PIE는 실행하지 않았다. Main에 사용자 직접 Play용 DevMap이 열려 있다. 최종 manifest와 증거는 Metadata/EnemyAnimationOrganization_20261007/FinalVerification.json, DeliveredManifest.json, MainReadyAudit.json을 따른다.

Main 최초 read-only 검사에서 DevAI_ label 접두사에 Navigation volume까지 포함해 actor수5로 실패했다. 4 BP/ABP·813 options 검사는 이미 통과한 상태였고, exact4family actor label로 QA 식을 고친 뒤 같은 fresh editor에서 전체 read-only 검사를 다시 통과했다. 실패 JSON/MainReload log를 보존했고 이 과정에서 게임 코드·map·asset save/PIE는 수행하지 않았다. raw tolerance의 정확한 값은1e-6이며 이전 Art 본문의 최초 .001cm 언급은 엄격한 compressed probe와 혼동한 설명이다. 최종 compressed .01cm와 raw 검사를 구분한다.

완료이며 pending helper/추가 에셋 전달이 없다. 최종 Main PID3528은 DevMap/PIE없음/dirty0/4BP·ABP UP_TO_DATE다. owned MonsterWork editor는 preview ScreenPercentage87/MotionBlur3와 원래 foreground throttle을 복구하고 정상 종료했다. 초기 실패 로그는 보존한다. 후속은 Router→Architecture ARCH-79 완료→Migration→MONSTER_ATTACK_ROOT_MOTION_20261007.md/Art ENEMY_ANIMATION_ORGANIZATION_20261007.md→CurrentAnimationLibrary.csv 및 실제 Source 순서다. rename/authoring/fixup/copy setup을 재실행하지 않는다. 직접 확인은 열린 Main DevMap에서 Play하고 감지→End→approach/좌우 대치→다양한 공격→거리 이탈 때 기존 행동 완료+.4초 후 재추격을 본다. 원작 AI 확률/모든 지형·연속 포즈/물리 pad/적 피격·네트워크는 미검증 후속이다.


## 2026-10-12T11:04:18+09:00 — ARCH-91 Root·공격 콜라이더·VFX Main 완료
Main에 Source7(runtime4/DEV3) 및 RootMotionRootLock 옵션만 바꾼 Animation88 package를 exact SHA/CAS로 반영했다. 새 runtime file/class/manager0, 다른 baseline610파일 보존, private DLL/Config 전달0. MainBuild01은 source 오류 없이 PCH virtual-memory C3859/C1076로 실패했고, 병렬1/noXGE MainBuild02는 Succeeded/input unchanged다. 현재 canonical UnrealEditor-Khazan.dll SHA `e14ca4b34c8a8a8042c2087fca2e646196b51e617d906c1884bee4e6c29cf511`를 사용한다.
실제 사용395 Root enabled/force lock/true-root·track0 및 Body392의1176포즈를 확인했다. 첫 프레임 누적 origin88개만 RefPose lock으로 정렬했으며 근거는 RootLockPlan의 imported RAW root first transform와 skeleton reference pose/UE FRootMotionReset이다. RootAssetBefore 및 MainBefore 백업을 보존한다. 전체 DataModel 모든 key/curve/attribute와 notify event/object SHA392개가 변경 전=private 후=Main fresh로 동일하다. source montage126/definition57/node220/window405의 geometry key·time·HP/Stamina·group·audio와 rate/나머지옵션이 fresh saved audit에서 동일하다. Props3는 다른 skeleton으로 body1176포즈에서 분리하고395 옵션/track audit에 포함했다.
Main actual RootPoses/MonsterHits30/PlayerAttackCollision16 Success. monster30은6종별 한 window 안1회 / 종료 후접근0 / exact-end pause후접근0 / 취소후접근0 / live mesh scale와actor yaw 반영을 실제 HP GE로 확인한다. player16의 기존 Spin7/Fury19와blood13 기반행동도 보존한다. source scale/last-End 경계·timer 종료만 기존 ComboAction에 보완했다. VFX198 assets/1577 source occurrences 및Death6는 동일 delivered Source의 private 실제RHI Success, finite world transforms / deterministic uncorrected source geometry max position3.46e-13cm·angle4.83e-6deg / template identity / body size를 확인했다. 이 보고서의 active correction-curve row는0이므로 해당 branch의 per-pose 실행을 실제 데이터 검증했다고 표현하지 않는다. source 없는 VFX actor axes/mesh origin 및 body scale은 적용했으며 curve branch는 기존 receipt의 latest GT clock→finalized-bone callback으로 구조 보완했다. 원작 native shader/pixel parity·전체두레벨연속전투·network는 검증 완료 범위가 아니다.
Main 파일·canonical build·fresh saved/actual runtime 완료. FinalVerification.json / ResumeState03.json 및 exact Delivered95를 재개 정본으로 읽는다. stage/old alias/full author/retime/reimport를 반복하지 않는다. Main editor 정상 재시작 후 직접 Play에서 green debug volume이 실제 공격 window에서만 나타나고 칼의 크기·방향/몸체 alignment를 확인할 수 있다.


## 2026-10-15 ? Yetuga?Apes ??170? ?? ?? / PartGroggy ?? ??4? ?? ??

??? ?? ?? ??? ?? ??118 pattern clip ? CombatFeel16 ??? ???? ?, ?? CDO CombatPatterns?Definition grant/reaction(Additive/VictimFront ??)?Stamina?ABP/BlendSpace graph dependency? ??170 sequence/30 montage/2 combo definition? ???. body skeleton ???0, root bone index0/track0 ??0, ForceRootLock off0, AnimBP ? ? MontagesOnly?. ??/??162?? EnableRootMotion=true?? off8?? ?? root? ?? HitAdditive D/L/R/U?. ?? PlayHitReaction? !HasRootMotion ??? ?? KZHitReactionGroup? ??? overlay? ??? root montage? ??? ??? ??.

?? BodyRootPoses.PIE 170/510 ???? ? ?? Damage_PartGroggy_Loop ? Damage_PartGroggy_End ? clip? ?? ???522.148062616cm? ????. EnableRootMotion/ForceRootLock? ?? true??? RootMotionRootLock=ANIM_FIRST_FRAME? imported RAW frame0(-2.670138359,-522.141235352,0)? pose root? ???. target skeleton bone0 Root? reference translation?(0,0,0)??. ? ??? ?? ??? ???? ?? pose ???? ?? ? ???? ???. offset? ? translation ?? Euclidean length(cm)? ???? .01cm? ?? native QA? ??? ?? ???.

??4package hash/?? backup ? ?? Yetuga Loop duplicate? ?? RAW frame?bone/???notify ?? ?? ? ? native probe offset0 ? Main4? RootMotionRootLock? REF_POSE ?? ? ? ???? readback/native/RHI ??? ????. Skeleton/track/??curve?attribute/???FPS?Notifies/???actor?mesh scale ? runtime C++/BP ??0??. Start? ?? root delta/CMC ??? ??? ?? Loop/End? skeleton ???? ???? ??. DataModel ?? SHA1 ? notify object/event SHA1?170? ?? ?? ??, ??166 sequence package SHA256? ????.

?? Native RootPoses170/510 Success(??4 offset522.148?0cm, ?? ??.001036cm), ?? GiantReaction2 ? GiantFall13 Success?. ?? Main D3D12 GiantReaction2? Success?? Start/Loop/End6?? ?? ?? ??? ???. Loop/End4?? ?? ???? ??0?? Apes Loop/Yetuga End? ?? ?? ????. ?? PartGroggy root ??523.544cm? ?? ?? ?526.8cm? ????. ??47 ?? source GAS entry? ?? Success?? ?? RootPoses4 ??? ?? ???? ??? ???.

?? CombatFeel? 'root ??'? flag/??/Start actor ?? ??????, Loop/End? locked pose origin? ???? ?? ???. ? ?? ??? ? ? clip? ?? ???? ?? ??? ????. RootMotionEnabled ? ?? delta??? ?? ?? ??? ???? ?? ?? ?? pose root? skeleton reference? ????. ?? code/DLL? ????? ???? ? native run? ?? Main DLL SHA73fed225...? ???? ??. ??: `Metadata/GiantRootUsage_20261015/FinalVerification.json` ? RepairPlan/Applied/AuditBefore?After/RuntimeBefore02?After/ActualPartRHI. Probe? ???? ??4 backup? ????.

