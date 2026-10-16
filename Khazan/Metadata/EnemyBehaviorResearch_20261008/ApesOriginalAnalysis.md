# ApesStoneHandElite 원작 행동·공격 패턴 분석 — 2026-10-08

이 문서는 기존 cooked JSON을 읽은 Art 분석이다. Source/BP/게임 에셋/원본 ZIP은 수정하지 않았으며 재추출·에디터 제어·build·PIE를 수행하지 않았다. 시각적 동작과 실행 의미를 원작 게임에서 실측한 보고서가 아니다.

## 출처와 재개 인덱스

- 원본: `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip` 및 `SourceMetadataIndex.json`. ZIP 내 package 경로 뒤 `.json`을 붙이면 원본 export 배열을 읽을 수 있다.
- 패턴 원시 property와 CB/AP/AI/SI/SB: `ApesOriginalEvidence.json`의 `raw_design_exports`, `ai_skill_groups`, `skill_steps`. source ZIP SHA-256과 package hash 대조를 포함한다.
- 정확한 이벤트 참조·조건·함수·notify 시간·attack volume·투사체: `ApesOriginalResolvedBranches.json`. `ObjectPath`의 package 및 export index를 보존한다. 같은 Name의 subobject가 여러 개이므로 이름만으로 참조를 연결하지 않는다.
- 현행 에셋 이름: `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv`; 92 Apes 행을 위 Evidence에 보존했다. 옛 Playback 경로와 현재 경로를 혼동하지 않는다.

이하 `D/`는 정확히 `BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/`다. 예: `D/Skill/01_NormalAtk01/SB_ApesStoneHand_E_NormalAtk01`은 그 full package이며 CDO는 `Default__SB_ApesStoneHand_E_NormalAtk01_C`다. 개별 field의 원시 값은 두 JSON의 package/export_name/export_index/field로 다시 찾는다.

## 변형별 실제 연결과 일반 후보

`D/Base_Setting/CB_ApesStoneHand_E`, `Default__CB_ApesStoneHand_E_C`, `Properties.AIDataAsset`는 `AI_ApesStoneHand_E`; Early CDO의 같은 field는 `AI_ApesStoneHand_E_Early`다. `DodgeStateClass`는 각각 `SB_ApesStoneHand_E_DodgeSkill_E_C`와 `SB_ApesStoneHand_E_DodgeSkill_Early_C`다. 둘의 `AnimationProfiles[Battle]`은 같은 `AP_ApesStoneHand_E`다.

원본에 `enabled_skill`이라는 field가 있는 것으로 표현하지 않는다. 아래는 각 선택 AI의 `Properties.CombatPreset.SkillGroup[i].Skill.bUse`/`Rate`를 실제 읽은 결과다. 모든 저장 행의 bUse는 true다. Standard 저장11행 중 DempseyRoll Rate0이고 나머지10행은 양수; Early10행은 모두 양수다. Rate는 원시 선택 가중치이며 조건·cooldown에 따라 실제 후보 집합이 변한다. 이를 고정 퍼센트로 환산하지 않았다.

| SI suffix / 원본 SkillName.SourceString | Standard index / Rate | Early index / Rate | Range Min..Max | Angle Base / Left / Right |
|---|---|---|---|---|
| `NormalAtk01` / 후려치기 | 0 / 2 | 0 / 2 | 0.0..400.0 | 0.0 / 120.0 / 120.0 |
| `NormalAtk02` / 내려 찍기 | 1 / 5 | 1 / 5 | 0.0..400.0 | 0.0 / 60.0 / 60.0 |
| `TurnAtk` / 휘두르기 | 2 / 1 | 2 / 1 | 0.0..400.0 | 180.0 / 60.0 / 60.0 |
| `CounterAtk` / (버스트) 양손 모아 찍기 | 3 / 10 | 미포함 | 0.0..500.0 | 0.0 / 90.0 / 90.0 |
| `DempseyRoll` / 전진 주먹 연속 휘두르기 | 4 / 0 | 3 / 1 | 0.0..400.0 | 0.0 / 60.0 / 60.0 |
| `DashAtk` / 도약 주먹 찍기 | 5 / 3 | 4 / 3 | 500.0..2000.0 | 0.0 / 45.0 / 45.0 |
| `FastBall` / 강하게 돌 던지기 | 6 / 2 | 5 / 2 | 1000.0..3000.0 | 0.0 / 60.0 / 60.0 |
| `BackMoving` / 뒷걸음질 | 7 / 6 | 6 / 5 | 0.0..500.0 | 0.0 / 90.0 / 90.0 |
| `FastMove` / 빠른 추격 | 8 / 10 | 7 / 10 | 1500.0..4000.0 | 0.0 / 45.0 / 45.0 |
| `SideMove` / (닷지)옆걸음치기 | 9 / 3 | 8 / 3 | 0.0..1500.0 | 0.0 / 90.0 / 90.0 |
| `TurnBackRun_Short` / 짧은 선회 이동 | 10 / 2 | 9 / 1 | 0.0..500.0 | 180.0 / 60.0 / 60.0 |

출처는 `D/Base_Setting/AI_ApesStoneHand_E` 또는 `..._Early`, 같은 이름의 xxAIData export, `Properties.CombatPreset.SkillGroup[i]`다. Range/HeightRange는 거리 raw field이고 소비 코드의 단위·capsule/actor-scale 반영은 이번 자료만으로 확정하지 않았다. UE cm로 사용하기 전 native 계약 확인이 필요하다. Angle은 field 이름이 degree인 원시 각도다.

각 후보 `StatusConditions=[]`, `SelectedSkillSubStateSteps=[]`, `PartDestructionConditions=[]`, `bForceChange=false`, `bUseOnlyAtGuard=false`, `bIgnoreStamina=false`, `bPreventUseTwice=false`가 기록된다. 일반 후보에 HP phase 필터를 새로 추정하지 않는다. 높이는 일반 근접/뒤/옆 후보 Min=-300 Max=300, Dash/FastBall/FastMove Min=-500 Max=500이며 `bHeightCheck=true`다.

두 AI의 `Properties.CombatPreset.StartSkillInfo.SkillInfo`는 `SI_ApesStoneHand_E_Roar`; `WaitTime=1.0`, `bLockOnMoveInsteadRotateTo=true`다. NormalMoveSetting는 Normal_Run Rate3 Time2.0, Normal_Walk Rate1 Time1.8, LockOnMove_LeftRight Rate1 Time1.8; NearMoveSetting는 LockOnMove_Back Rate1 Time1.8, LeftRight Rate2 Time1.8이다. 이 time/Rate를 실측 프레임/확률로 취급하지 않는다. 별도 `AI_ApesStoneHand_E_Battle_Range` 자료도 ZIP에 있으나 위 두 CB의 선택 AI와 섞지 않았다.

## 공격 실행은 SkillBundle이 아닌 SubStateInfos

선택 공격 SB의 BlueprintGeneratedClass.SuperStruct는 native `Class'xxCommonSimpleSkill'`다. 실제 CDO 배열은 `Properties.SubStateInfos`다. 48 step과 51 SkillEventMap event를 확인했으며 등록 배열 순서와 NextSubStateStep/조건분기를 분리한다. step 개수는 타수가 아니다. 모든 확인 step의 AnimPlayRate=1.0, bApplyAttackSpeed=true이며 이는 Composite의 dilation bake와 별도로 live attack-speed 배율을 소비할 수 있음을 뜻한다. 최종 런타임 속도는 미확인이다. Level_Dash/Dodge_A Run step의 AnimLoopCount=2이며 나머지 확인 step=1이다.

| 원본 SB package | step 기본 연결 / 조건 변화 |
|---|---|
| `D/Skill/01_NormalAtk01/SB_ApesStoneHand_E_NormalAtk01` | Step1 NormalAtk01_01 → Step2 _02 → Step3 _03 → None. blend raw .2/.1/.1, playrate1.0. |
| `D/Skill/02_NormalAtk02/SB_ApesStoneHand_E_NormalAtk02` | Step1 _01의 기본 next None. Index1 AnimationNotifyStart, FindTarget instant circle Yaw360/RangeMax800/height[-300,300]/bIDLE=false일 때 xxChangeNextStepFunc_1(분리 export2)의 NextSubStateStep=Step2. Step2 _02→None. |
| `D/Skill/03_TurnAtk/SB_ApesStoneHand_E_TurnAtk` | Step1 TurnAtk_1→None. 일반 AI의 뒤쪽 BaseDegree180 조건에서 고르는 스윙이다. |
| `D/Skill/04_CounterAtk/SB_ApesStoneHand_E_CounterAtk` | Step1 CounterAtk→None. SI 원문 `(버스트) 양손 모아 찍기`, bEnableParringSkill=false. Standard 일반군 Rate10. 이름만으로 자동 반격 트리거를 주장하지 않는다. |
| `D/Skill/05_DempseyRoll/SB_ApesStoneHand_E_DempseyRoll` | Step1 _Step1→Step2 _Step2→None. Step2 Index2의 xxSimpeEvnetTagAttackerDamagerSkillReaction_0(export4) Results=[ParryingReaction,JustGuardReaction], NotifyEnable 조건이 xxPlayAnimatiomFunc_0(export3)의 JustGuardReaction+blend .3 및 xxConsumeStaminaRegainFunc_2(export2)의 EStatusOper::Rate/500을 소비하도록 연결. |
| `D/Skill/08_DashAtk/SB_ApesStoneHand_E_DashAtk` | Step1 DashAtk→None. Index1 AnimationNotifyStart, FindTarget OffsetRotatorYaw180/circle RangeMax500/height[-300,300]→xxSimpleSkillEventFunc_NextSkillEnable_0(export2), NowNextSkill=TurnBackRun_Short, bUseCoolTime=false/bUseForceCancel=true. |
| `D/Skill/11_FastBall/SB_ApesStoneHand_E_FastBall` | Step1 FastBall_Start→Step2 Shoot→Step3 End→None. 실제 투사체 COI와 HoldShoot subobject를 연결하며 단순 body 근접 몽타주만으로 재현할 수 없다. |

NormalAtk01의 Attack notify는2+4+4 volume이며 group1 / group2·3 / group4·5다. 같은 손·전완 volume들은 같은 `Group`과 `AttackIntervalDesc=그룹N+컴포넌트, 1회 공격`을 공유한다. 자료상 다섯 공격 group이지만 actual 유효 적중 횟수는 collision/group-dedup 소비 코드 및 타깃에 달렸다. NormalAtk02 step별 두 volume도 같은 group이어서4notify=4타가 아니다. CounterAtk는 네 손·전완 volume 같은 Group1 및 별도 DonutSlice DamageInfoIndex1(그룹 field 생략), DashAtk는 다섯 volume의 Group1·2다. 정확한 창은 Resolved의 attack_notify_volumes에 있다.

DempseyRoll의 source `BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/ApesStoneHandElite/Animation/CA_M_ApesStoneHandElite_DempseyRoll` SequenceLength=7.0, source notify0개다. 선택 Composite `.../AC_ApesStoneHand_E_DempseyRoll_Step1.Properties.AnimationTrack.AnimSegments[0]`은 AnimStartTime0/AnimEndTime2.6; Step2는4.5/6.75다. SB 기본 연결은2.6–4.5 구간을 건너뛴다. 선택 Composite attack group은1·2 및5, notify6개를6타로 설명하면 오류다.

## 바위 투척의 실제 원본 계약

`D/Skill/11_FastBall/SI_ApesStoneHand_E_FastBall`, 동일 이름 export의 `Properties.SkillName.SourceString=강하게 돌 던지기`, `bEnableParringSkill=false`, `EndCooltime=20`, `BattleStartCooltime=20`다. SB Step1 Index1은 xxFuncSkillObjectSpawn_1(export3) `SkillActionType=ESkillAction::Spawn`, Step2 Index1은 xxFuncSkillObjectSpawn_0(export2)로 가며 두 함수는 `SkillObejctInfo=COI_ApesStoneHand_E_FastBall_OBJ`다. Shoot 함수에서 SkillActionType field는 생략됐으므로 native 기본 enum을 임의로 채우지 않는다.

SpawnTypeHoldShoot export6/7은 `SpawnAndHoldInfo.bUseSocket=true`, SocketName=Projectile-L-Hand, SnapToTarget 위치·회전, BoneOffsetLocation=(50,0,-20), bUseAimShootInfo=true다. DetachShootInfo TargetBoneName은 shoot 함수 쪽 export6 `Bip001-Spine1`, spawn 함수 쪽 export7 `Bip001-Spine`이며 bUseBoneTargeting=true다. 원시 offset 거리·소비단위는 별도다.

`D/Skill/11_FastBall/FastBall_OBJ/COI_ApesStoneHand_E_FastBall_OBJ`, `xxProjectileSkillSetupInfoV2_0` export1 `Properties.ProjectileInfo`는 Idle/Move/Explosion/WorldExplosion/Destruction/ParryingReaction step을 실제 참조한다. Idle AutoChangeMoveState=true; option IsDirectAttack=true, MoveLifeTime10; bUseLifeTime=true/LifeTime10; bUseCapsuleSize=true/CapsuleHalfHeight70; bUseScale=true/Scale0.8. Move Composite backing은 공용 Missile_Idle이며 body skeleton의 공격 pose가 아니다.

같은 폴더 `AC_ApesStoneHand_E_FastBall_OBJ_Move`, xxAnimNotifyState_MoveTo_1(export2)의 `Properties.PositionInfo.UseCurveData.CurveVector=CV_ApesStoneHand_E_FastBall_OBJ`, CustomCurveScale=(15000,100,100)다. 이를 곧바로15000cm/s로 해석하지 않는다. target trace limit=(5000,2500,750), distance ratio=(2,1.5,2), bUseKeepSpeed=true 등이 저장돼 있으며 정확한 소비·시간정규화는 원작 native 미확인이다. Curve 원시 keys와 전체 projectile19 export를 Resolved에 보존했다.

## 뒤·옆 이동과 연계 반응

- BackMoving SB Step1 Index1: WallCheck(export10) DirectionCheckDistance600/Back=Fail → ChangeNextStepFunc(export2) Step2. Step1 Index2: instant target circle max700→NextSkill DempseyRoll(export3). Step2 Index1: circle min700/max1500→NextSkill DashAtk(export4). 세 event의 tag는 AnimationNotifyStart이고 next skill 함수는 NowNextSkill 및 bUseForceCancel=true다.
- FastMove Step1 Index1: AnimationNotifyTick tag(export3), FindTarget(export4) circle max400/height[-300,300] → NextSkillRandom(export2), ChagneNextSkillSelectType=Random, DempseyRoll RandomRate.5/SideMove1.0, 양쪽 bUseCoolTime=false/bUseForceCancel=true. 두 값의 native Random 소비를 확인하기 전1/3·2/3 확률로 확정하지 않는다.
- SideMove Step1의 기본 L_Step1. StartSubState Index1의 FindTarget(export14) OffsetRotatorYaw270/circle max3000/height[-1000,1000] → Step2 R_Step1. L/R의 Index2는 circle max600→DempseyRoll(쿨타임 무시/force cancel). Index3의 WallCheck(export15/16)는 두 방향 모두 raw Directions.Left=Fail/거리600으로 저장돼 각각 Step3 L_Step2 또는 Step4 R_Step2다. R이라고 이름만 보고 Directions.Right로 고치지 않는다.
- TurnBackRun_Short: Step1 Index1 WallCheck Back=Fail/거리600→Step2. Step2 Index1은 FindTarget circle max1500/height[-300,300], CheckType=Fail이면 NextSkill Social/bUseForceCancel=true. Social SI는 `전투 소셜 모션`, EndCooltime60/BattleStartCooltime60이다.

위의 min/max 경계 포함 여부·default CheckType·트레이스 모양의 숨은 기본각은 native 구현을 확인하지 않았으므로 임의 확정하지 않는다. 단순 무작위 이동 목록보다 이벤트가 있는 실제 연계 구조다.

## Early와 Standard 피격 반응의 차이

Standard `D/Base_Setting/SB_ApesStoneHand_E_DodgeSkill_E` CDO PassiveDatas[0] → xxMonsterPassiveDamage_0(export2), xxMonsterPassiveFunc_UseSkill_2(export3). Event의 DamageEventCondition(export4)은 CheckTimeTerm6/TotalDamageRateMax.13/bResetAllDamageEvent=true; SelfStatus(export5)는 HealthPoint/LessThan/bUseRatio=true/RatioValue.9. battle-state 조건(export6)은 bUseDont=true/Except=[StaminaExhaustionOrRemainTime]. TargetCheckData에는 SkillAttack/SpiritSkill만, angle ±90, attack-box remain check -0.15, 무기별 RangeMaxKazanWeaopnTypeOffest DAS400/GSword500/Spear450, PendingLimitTime.01이 있다. 각 raw field의 합산·비교 방향은 consumer 미확인이고 .13을 무조건13%피해 임계로 구현하지 않는다.

UseSkill 함수는 Dodge_B, bUseCoolTime=true, StartSkillStep1, bUseForce=true, bOnlyDamageStateCancel=true, bOnlyGroundDamageStateCancel=true, CancelBlackList=[Dodge_A]다. Dodge_B SB는 Dodge Step1→Run_Loop Step2→None; Step2 EndSubState→DempseyRoll 강제 연계가 확인된다. Step1에 추가 NextSkillEnable이 있으나 그 tag export4는 Properties/EventTag가 생략돼 trigger 의미는 미확인이다.

Early `D/Base_Setting/SB_ApesStoneHand_E_DodgeSkill_Early`에는 PassiveDatas3행 모두 SideMove를 호출한다. 배열 실제 순서는 Damage_0→UseSkill_2, Damage_2→UseSkill_3, Damage_1→UseSkill_0이다. Damage_0은 Count export8(CheckTimeTerm4,TotalHitCountMax5)+Random export11(.5); Damage_2는 Count export10(4,6)+Random export13(.7); Damage_1은 Count export9(5,7)+Random export12(1.0)이다. 모두 PendingLimitTime.1, bUseDont=true인 battle-state 조건을 가진다. Count5/6/7 경계의 >=인지 >인지 native 미확인이므로 `4초5hit 기준` 원시 구성으로만 설명한다. UseSkill_0에는 bUseCoolTime field가 없으며 true/false를 채우지 않는다.

Dodge_A는 둘의 CB DefaultSkillList에 있는 `회피 후 잡기` 실행 자료지만 위 현행 선택 passive는 Early SideMove/Standard Dodge_B다. 기본 공격 일반군에도 없다. 따라서 자료 존재와 현행 자동 선택 경로를 분리한다.

## 도약 뒤 잡기·넘어짐을 혼동하지 않는 해석

`SI_ApesStoneHand_E_DashAtk_LevelSkill`은 `SB_ApesStoneHand_E_Level_DashAtk_New`를 연결한다. SubStateInfos 실제 array key순서는1,3,4,5,7,8,9,10,11,12다. 기본1↔3은 DashAtk_IDLE,4Roar→5DashAtk_Level_H_Short,7Run_Loop(loop2)→8CloseGrab_Start→9Fail,10Success_01_Turn→11Success_02다. Step5 notify 조건은 max400→12Start2_Stone, min400/max700→8, min700/max3400→7. Step8/12의 OnAttack type event→DoChangeStepAtAnimationEnd/Step10, HoldingSuccess type event→Weapon_L attach target Bip001-Spine/FallDown ragdoll/Bip001/weight.5 + camera func를 연결한다. Step10 timer Time.5/MaxCount5/NotifyEnable→HoldingAttachTarget DamageInfoIndex3, Index1→DamageInfoIndex1이다. 타이머 횟수와 실제 target 피해 적용 횟수는 구분한다.

Dodge_A도 유사한 grab 성공/실패 구조지만 Stone clips와 Step1 거리max200→12/min200max400→8/min400max3400→7을 쓴다. Level version과 같은 asset으로 축약하거나 Step 번호를 연속1..10으로 바꾸지 않는다.

Level_Dash Step1·3의 AC_DashAtk_IDLE에는 해당 SkillEvent notify가 없고, Step4 Roar에도 없다. SB의1·3은 AnimationNotifyTick,4의 EventTag field는 생략이다. 기본분기·직접 property는 확인했지만 원작 실행 코드 없이 각 event trigger/도달/우선순위를 확정하지 않는다.

`AP_ApesStoneHand_E.SpecialDamageAnimList`의 Grapple1/2/Back1/Back2→DamageGrapple_Atk*는 피해자 반응 분류다. 이름에 Atk가 있다는 이유로 Apes의 근접 공격 후보로 넣지 않는다. `FallingAnimList` start/loop/end는 모두 AC_M_ApesStoneHand_E_Falling이며 CB FallingStateClass=Common_Falling_C다. 낙하/피격 reaction 연결은 확인됐지만 자발적으로 넘어지는 공격 전략은 미확인이다.

## 피로·회복·발견·대기

`AP_ApesStoneHand_E.Properties.StaminaExhaustionAnimSetMap[0]` key Index1은 GroggyStr_F_Start/Loop/End와 세 blend raw.2를 연결한다. 이는 exhaustion 표현과 소비 연결 근거이며 스태미나 고갈 임계·실제 유지시간까지 확인한 것은 아니다. CB StaminaRecoverySkill은 StaminaRecover; SI 원문은 `괴력 충전 포효`, bEnableParringSkill=false. SB Step1 StartSubState에 DynamicStatusChangeInstFunc(export3) Stamina/RateSet/Value10000, notify 연계 ConsumeStaminaTimeFunc(export2) RateSet/ConsumePerSecond-580, step-start/end func(export4) CustomSkillStaminaAttackPowerRate-10000을 연결한다. 고유 fixed-point 스케일 확인 전100%/5.8% 등으로 환산하지 않는다.

`SI_Groggy` 원문 `직가 리액션 그로기`, SB GroggyStr_F_Loop Step1→End Step2→None. PartGroggy SI는 SkillStateSubType=PartDestructionGroggy, StatusChangeInfoList의 HP/Rate/Value-1000/bDieHardtrue/즉시=true 및 SpellInfoList=SP_ApesStoneHand_E_PartGroggy_Injuried/DurationMS0를 기록한다. SB에는 시작/루프/종료애니와 시작시 스펠 인덱스[0]가 있으나 한글 property의 소비 로직/종료 trigger는 미확인이다.

`AP.Idle`은 Apes 자체 이름의 asset이 아니라 원본 Yetuga/CA_M_Yetuga_Stand_F. 현행 mapped path는 Locomotion/Locomotion_Stand_F_Original_Variant02다. Battle start roar와 미발견 Peace idle를 같은 Idle로 묶지 않는다. LevelPresence는 HeinMach3/StormPass1 모두 CB Early를 기록하며 Standard spawn을 입증하지 않는다. HeinMach 첫 Early SpawnStartSkillInfo=DashAtk_LevelSkill; Early3 BattleStartSkillInfo=DashAtk_StartSkill/Basic_Loop_01+Basic_End_01; StormPass Early BattleStartSkillInfo=DashAtk_StartSkill/Basic_Loop_02+Basic_End_02다. Early2 PeaceTasks는 Patrol/Skill/Patrol/Skill refs며 해당 nested task 원시 properties는 이번 ZIP에 없으므로 재생 asset/시간은 추가 표적 조회가 필요하다.

## 시간축과 현행 이름

같은 SB AnimPlayRate1.0이어도 Composite bake 길이는 원본 SequenceLength와 다를 수 있다. 예: NormalAtk01_03 raw6.733333 → DilationSequenceLength5.847048/현행5.8470478058s; NormalAtk02_01 raw3.16→2.930057s; DashAtk raw6.25→6.5683713s. NormalAtk02 조건 notify raw LinkValue2.416413→saved playback2.2181253015s; Dash followup raw5.527082→5.865259s; FastBall spawn raw.7008107→.6635746505s, shoot raw.741729→.741729s. 이것들은 기존 saved source dilation mapping이며 live attack-speed/hitstop 최종시간이 아니다. source AnimPlayRate, step playrate, baked dilation, actor dilation을 중복 적용하지 않는다.

현재 경로·step·notify의 원본/재생 시간은 Resolved.step_animation_timelines / matching_animation_notify_records, Evidence.current_animation_library에 모두 연결한다. 실제 새 engine notify/GAS/AI 실행 로직이 기존 Art92개 안에 임포트됐다고 주장하지 않는다.

## 다음 표적 확인과 미확인

원작 AI/xxCommonSimpleSkill/xxAnimNotifyState_Attack/NextSkillRandom/RateSet 등 native 소비코드 또는 그 의미를 보증하는 기존 추출 문서가 없으므로 확률 정규화·group reset 수명·수치 배율·취소 우선순위·피로 종료·일부 EventTag 기본값은 미확인이다. Source ZIP에 없는 HeinMach Early2 nested PeaceTasks는 해당 저장 level JSON의 export498–501을 표적 조회한다. 코드/게임 에셋 변경은 별도 사용자 요청 이후에만 진행한다.

재개: (1) 위 두 JSON을 먼저 읽고 package/export-index로 정확한 표적만 연다. (2) 필요한 native 계약이나 nested level props만 추가 확보한다. (3) 원시 확인/계산/이름 추론/실측을 분리해서 날짜별 추가한다. 기존 Art library 재추출·retime·asset-authoring을 다시 실행하지 않는다.
