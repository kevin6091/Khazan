# Yetuga 원작 방어·그로기·회복 표적 조사 — 2026-10-08

조사 범위는 저장된 원작 JSON/Source ZIP의 읽기와 이 신규 보고서 작성이다. 게임 Source/BP/에셋, 기존 문서, 원본 metadata는 수정하지 않았으며 재추출·에디터 제어도 하지 않았다. 원본 수치의 소비 구현이 없으면 원시 값만 보존한다. 누락된 property를 엔진 기본값·0·false로 채우지 않는다.

원본 ZIP: `Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip`.

- ZIP SHA-256: `e47a8802233b69676eb8b9d0fe26bb372e1e42c7e4fe6c6f5a954eaa78de9a34`.
- 재사용 원본 인덱스: 이 보고서와 같은 폴더의 `YetugaOriginalDefenseRecovery.json`. 표적 40 package, 154 export의 정확 package/export index/exportName/원시 properties 및 애니메이션 Notify 참조를 저장했다. 표적 40개 모두 ZIP JSON SHA-256이 `SourceMetadataIndex.json`과 일치했다.
- 이하 `Y/`는 `BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/`를 뜻한다. 모든 field는 특별한 표시가 없으면 해당 export의 `Properties` 아래다. JSON은 약 267 KB이며 전체 ZIP의 무분별한 field dump가 아니다.

등 약점 부위 파괴, 스태미나 고갈, 직가/패리 반응 그로기, 공격 종료·벽 충돌 회복은 별개 경로다. Brutal Attack의 실제 활성화 판정과 플레이어 실행 연결은 이 Yetuga ZIP에서 확정할 수 없다.

## 1. 등 약점 Group1과 부위 파괴

`Y/Base_Setting/CB_Yetuga`, export 1 `Default__CB_Yetuga_C`의 `StatusProfile.ObjectPath`는 `Y/Base_Setting/CS_Yetuga.0`다.

`CB_Yetuga`의 다음 damage box들은 모두 `DefenseGroup=EGrDefenseGroup::Group1`, `bDeactiveAtDestruction=true`, `bWeakPointDamgeBox=true`를 명시한다. `bWeakPointDamgeBox`는 원본 철자다. `BodyInstance.PhysMaterialOverride`는 `PM_Ice`, 약점 적중 sound는 `efx_pc_enemy_weakness_hit`다.

| export | exportName | SCS 연결 export/AttachToName |
|---|---|---|
| 31 | `xxDamageBox_Back1_GEN_VARIABLE` | 13 `SCS_Node_18` / `Bip001-L-UpperArm` |
| 32 | `xxDamageBox_Back3_GEN_VARIABLE` | 14 `SCS_Node_19` / `Bone-R-UpperArm-Twist` |
| 33 | `xxDamageBox_Back_GEN_VARIABLE` | 22 `SCS_Node_6` / `Bip001-Spine` |

즉 이름이 Back인 세 box가 Group1을 공유한다. Back1/Back3의 실제 socket은 팔 bone이므로 세 box를 모두 척추 bone에 붙은 단일 box라고 설명하면 틀린다. 별도 box 수를 약점 적중 횟수 또는 부위 파괴 횟수로 해석하지 않는다.

`Y/Base_Setting/CS_Yetuga`, export 0 `CS_Yetuga`, `PartDestruction[0]`의 `Key=EGrDefenseGroup::Group1`; `Value`의 정확 설정은 다음과 같다.

| field | 원시 값 | 확인 가능한 의미/제한 |
|---|---|---|
| `bCanDestruction` | `true` | 이 group의 파괴를 설정상 허용 |
| `Durability`, `SecondDurability` | `350`, `350` | 원작 내구도 값. HP/스태미나/필요 타수로 변환하지 않음 |
| `MaxDestructionNum` | `1` | 설정상 최대 파괴 수 |
| `bShowBattleDirecting` | `true` | 부위 파괴 연출 설정 |
| `BattleTIme`, `AfterNormalGroggyTime` | `0`, `0` | 원시 시간 field. 자동 런타임 트리거 의미는 native 미확인 |
| `bCheckHPOver`, `bCheckHPBelow` | `false`, `false` | 이 Group1 설정의 HP 위/아래 조건 사용 안 함 |
| `HPRatioOver`, `HPRatioBelow` | `0`, `0` | 위 조건이 꺼진 상태의 저장 값 |
| `bDoNotAccumDuringNormalGroggy` | `false` | 일반 그로기 중 누적 금지 flag는 꺼짐 |
| `StartAccumValueDecreaseTime`, `AccumValueDecreaseValuePerSecond` | `0`, `0` | 누적값 감소 설정 원시 값 |
| `NormalGroggySkill` | `null` | 일반 부위 그로기 skill 연결 없음 |
| `BigGroggySkill.ObjectPath` | `Y/Skill/00_PartGroggy/SI_Yetuga_PartGroggy.0` | 실제 부위 파괴 그로기 연결 |
| `bNoChangeBigGroggyOnlyAddSpell` | `false` | spell만 추가하는 정책 flag는 꺼짐 |
| `bApplyCompleteDestroyedDamageInfo` | `false` | 아래 custom bonus 적용 flag는 꺼짐 |

`CompleteDestroyedDamageInfo`의 `CustomSkillPowerBonusAdd/Rate`, `CustomSkillStaminaAttackPowerAdd/Rate`는 모두 `0`이다. 이 자료만으로 “등 갑옷 파괴 후 모든 피해가 특정 배율로 증가한다”라고 설명할 근거는 없다. 내구도 누적 계산, 무기별 부위 파괴 damage, 반경별 적중 판정은 native 및 공격자 damage 자료가 필요하다.

## 2. 부위 파괴 그로기와 회복 연결의 확인 범위

`Y/Skill/00_PartGroggy/SI_Yetuga_PartGroggy`, export 0 `SI_Yetuga_PartGroggy`:

- `SkillName.SourceString="부위 파괴 그로기"`.
- `SkillStateSubType=ESkillStateSubType::PartDestructionGroggy`.
- `SkillStatePtr.AssetPathName` → `SB_Yetuga_PartGroggy_C`.
- `StatusChangeInfoList[0].StatusToChangeInfos[0]`: `StatusToChange=EDynamicStatusToChange::HP`, `Operator=EStatusOper::Rate`, `Value=-1000`, `bDieHard=true`; 같은 list entry의 `bChangeImmediate=true`. **원작 Rate 분모/소비 함수는 미확인이므로 -1%, 피해량 1000 등으로 환산하지 않는다.**
- `SpellInfoList[0]` → `SP_Yetuga_PartGroggy_Injuried.2`, `[1]` → `SP_Yetuga_PartGroggy_Stun.1`; 양쪽 `DurationMS=0`. 0을 spell 즉시 제거·무효라고 해석하지 않는다.

`SB_Yetuga_PartGroggy`, export 0 `SB_Yetuga_PartGroggy_C`의 `SuperStruct.ObjectPath`는 `BBQ/Content/_Common/State/Base/SB_Base_PartDestruction_Groggy.10`다. export 1 `Default__SB_Yetuga_PartGroggy_C`:

- `"시작시 스펠 인덱스"=[0,1]`.
- `"시작애니"` → `AC_Yetuga_PartGroggy_Start.0`.
- `"루프애니"` → `AC_Yetuga_PartGroggy_Loop.0`.
- `"종료애니"` → `AC_Yetuga_PartGroggy_End.0`.
- `"루프애니 재생횟수"=2`.

시작/루프/종료 Animation Composite의 `AnimationTrack.AnimSegments[0]`는 각각 원본 `CA_M_Yetuga_PartGroggy_Start/Loop/End`를 가리킨다. Loop 구간 `AnimStartTime=0.0`, `AnimEndTime=2.0`, `AnimPlayRate=1.0`, `LoopingCount=1`; SB에 별도 루프 횟수 2가 있다. **Common parent가 ZIP/index에 없으므로 이 두 값을 곱해 실제 전체 그로기 시간을 확정하지 않는다.** 종료 애니메이션 gameplay 목록에서 다음 회복 SI를 직접 실행하는 Notify는 확인되지 않았다.

`SP_Yetuga_PartGroggy_Injuried`, export 0 `xxSpellFunc_MaterialParam_1`: `ScalarParamName=EMaterialParameterNames::PartsDisolve1`, `BlendInTime=1.5`. 최종 scalar값 field는 누락됐다. export 1 `xxSpellFunc_Particle_0`: `PP_Bleed_Loop`, `AttachSocketName=Bip001-Spine2`, 상대 위치 `(15,0,0)`, 상대 rotation Pitch `-90`. 부위 파괴 후 시각 자료이며 스태미나 고갈 판정과 동일하다는 근거는 아니다.

`SP_Yetuga_PartGroggy_Stun`, export 0 `xxSpellFunc_ReleaseOnEndState_1`의 `EndSkillInfos[0].AssetPathName` → `SI_Yetuga_PartGroggy`. 이 spell은 해당 skill 종료에 연결된 release policy를 가진다. 일반 회복 SI와 부위 파괴 후 회복 SI 양쪽 `SpellConditionToUseSkill.ExcludeSpells[0]`가 이 Stun spell을 가리킨다. 따라서 자료상 부위 파괴 그로기 spell과 회복 실행 배제 조건의 관계는 확인된다.

부위 파괴 후 전용 SI도 존재하지만 자동 호출 자체는 미확인이다. `Y/Skill/21_StaminaRecover/SI_Yetuga_PartGroggy_StaminaRecover`, export 0:

- `SkillName.SourceString="부위 파괴 후 괴력 충전 포효"`.
- `SkillStatePtr`는 일반 회복과 동일한 `SB_Yetuga_StaminaRecover_C`.
- `StatusChangeInfoList[0].StatusToChangeInfos[0]`: Stamina / `Rate` / `100000`; `bChangeImmediate=true`.
- `CancelGroups=[ESkillCancelGroup::ForceCancel]`, `SelfCancelGroups=[]`.
- export 1 `xxStateInputConditionSelfStatus_0`: Stamina / `LessThanOrEqualTo`, `bKeepOpResult=true`. 비교 `Value`, `bUseRatio`, `AfterTime`는 누락됐다.

CB의 `DefaultSkillList` 등록은 확인된다. 그러나 이 전용 SI를 PartGroggy 종료에서 자동 호출하는 실행 함수는 저장된 원본 범위에서 확인되지 않았다. Common parent의 state 종료 처리, 스태미나 변경에 따른 native actor 경로를 추가 확인해야 한다.

## 3. 스태미나 고갈과 일반 회복

`CS_Yetuga` export 0의 정확 경로:

`Properties.StaminaStatus[0].Key=EStateBattleStance::Battle`의 `Value.StaminaExhaustionInfo.StaminaExhaustionTerm=8.0`.

이 원본 JSON package의 SHA-256은 `0a597b5598466b7644b9475be6fec2a9ea528b90c2ffc977ff7ff47740fded72`이며 ZIP raw bytes와 SourceMetadataIndex가 일치했다. 시간 parameter의 원시 값은 8.0이다. 관련 parameter의 단위는 상태 시간 문맥상 초로 읽되 native timer 시작·멈춤·취소·override 방식은 이 자료에서 확인하지 못했다. 확정된 플레이어 Brutal 기회 시간이 8초라는 뜻으로 사용하지 않는다.

같은 `StaminaStatus[0].Value`:

| field | 원시 값 |
|---|---|
| `RecoveryPerSecond` | `0` |
| `DamageStateRecoveryPerSecond` | `[]` |
| `bImmediatelyStaninaRecoveryBeginStaminaExhaution` | `false` |
| `bUseDamageReaction` | `true` |
| `bUseSuperArmourStamina` | `true` |
| `StaminaExhaustionInfo.StaminaExhaustionDamageRate` | `0.0` |
| `StaminaExhaustionInfo.EndStaminaExhaustionRecoveryOperator` | `EStatusOper::Add` |
| `StaminaExhaustionInfo.EndStaminaExhaustionRecoveryStamina` | `0` |
| `StaminaExhaustionInfo.bKeepBurstAttackHoldReleaseAnim` | `false` |
| `GuardStaminaConsumeRate` | `-1.0` |
| `GuardStaminaRecoveryRate` | `1.0` |
| `GuardStaminaRecoveryRateBySubState` | `[]` |

회복 skill 실행과 별개인 상태 종료 회복 field는 `Add/0`이다. 정상 전투 recovery/sec 역시 0이므로 일반 몬스터처럼 자연 회복 값을 새로 채우면 원본과 구별해야 한다. 현재/최대 스태미나 절대량은 이 CS export에 없으며 이 조사에서 새로 확정하지 않았다.

`Y/Base_Setting/AP_Yetuga`, export 0 `AP_Yetuga`, `StaminaExhaustionAnimSetMap[0]`:

- `Key=EStaminaExhaustionAnimationIndex::Index1`.
- `Value.StartAnim` → `Y/Moving/Reaction/AC_Yetuga_GroggyStr_F_Start_New.0`.
- `LoopAnim` → `AC_Yetuga_GroggyStr_F_Loop_New.0`.
- `EndAnim` → `AC_Yetuga_GroggyStr_F_End_New.0`.
- `StartAnimBlendTime/LoopAnimBlendTime/EndAnimBlendTime`는 모두 `0.2`.

이 세 **New** composite의 실제 segment는 `CA_M_Yetuga_GroggyStand_F_Start/Loop/End`다. 동일 접두사라고 `CA_M_Yetuga_GroggyStr_F_*`를 실제 참조 sequence로 바꾸면 안 된다. segment의 원본 구간은 Start `[0.0,0.96666664]`, Loop `[0.0,4.0]`, End `[0.0,1.7]`, 각각 `AnimPlayRate=1.0`, `LoopingCount=1`. 애니메이션 길이의 합을 상태 지속시간 8.0과 동일한 수명으로 계산하지 않는다.

일반 회복 연결은 `CB_Yetuga` export 1 `StaminaRecoverySkill.ObjectPath=Y/Skill/21_StaminaRecover/SI_Yetuga_StaminaRecover.0`다. `SI_Yetuga_StaminaRecover` export 0의 이름은 `"괴력 충전 포효"`, `bEnableParringSkill=false`; export 1 `xxStateInputConditionSelfStatus_0`:

- `CheckDynamicStatus.DynamicStatus=EGrDynamicStatus::Stamina`.
- `CompareOperator=ECompareOperator::LessThanOrEqualTo`.
- `AfterTime=6.4`, `bKeepOpResult=true`.
- **비교 threshold Value/Ratio field는 누락됐다. 따라서 문서에 Stamina≤0을 원본 직접값으로 쓰지 않는다.** 조건 지속 검사/시간 기준의 native 구현은 미확인이다.

`SB_Yetuga_StaminaRecover`, export 1의 Step1→None은 `AC_Yetuga_StaminaRecover`를 `AnimPlayRate=1.0`, `AnimLoopCount=1`, `AnimBlendAlpha=0.1`로 참조한다. Step1 `SkillEventMap[0]` Index1은 export 3 `xxSimpleSkillEventTag_2`(`EventTag=StartSubState`)→export 2 `xxDynamicStatusChangeInstFunc_0`다. 함수의 정확 raw field는 `StatusChangeInfoList[0]`의 `FuncChangeDynamicStatus=Stamina`, `Operator=Rate`, `Value=99999`다. **회복 수치가 기록된 이벤트는 StartSubState이며 포효 애니메이션 끝이나 Notify 시작으로 옮겨 설명하지 않는다.**

`AC_Yetuga_StaminaRecover` export 0의 segment 끝은 `2.5333333`, 원본 playrate 1.0. 별도 `Notifies[4]` `xxSkillEventTag`는 `LinkValue=0.6625519`, `Duration=0.43901312`, export 10 `xxAnimNotifyState_SkillEventTag_0.Index=Index1`이다. 이 Notify 존재만으로 회복 함수의 EventTag=StartSubState를 AnimationNotifyStart로 바꿀 수 없다.

8.0 고갈 term, 입력 condition 6.4, 포효 composite 길이는 서로 다른 출처와 목적이다. “고갈 8초 후에 6.4초를 추가 대기” 또는 “6.4초에 무조건 완전 회복” 같은 합성 시간표는 native 수명 확인 전 미확인이다. `Rate99999/100000`도 원작 분모·clamp·비교 대상 없이 100%로 단정하지 않는다.

## 4. 덤프의 직가/패리 반응과 별도 그로기

원본 enum은 `JustGuardReaction`, `ParryingReaction`이다. 프로젝트/사용자의 BrinkGuard와의 명명 대응은 별도 계약이며 ZIP에는 BrinkGuard라는 이름이 없다.

`Y/Skill/05_DempseyRoll/SB_Yetuga_DempseyRoll`, export 1 `Default__SB_Yetuga_DempseyRoll_C`, `SubStateInfos`에서 `Key=Step2`인 entry의 `Value.SkillEventMap[1]`:

- `Key=ESimpleSkillEventIndex::Index2`.
- `Value.SkillTag.ObjectPath` → 같은 package export 8 `xxSimpeEvnetTagAttackerDamagerSkillReaction_0`.
- 이 tag의 `Results=[EDamagerSkillReactionType::ParryingReaction, EDamagerSkillReactionType::JustGuardReaction]`.
- `SkillTagCondition[0]` → export 15 `xxSimpleSkillTagCondition_NotifyEnable_0`; 이 조건의 Properties는 `{}`. 누락된 Index/enum 기본값을 임의 채우지 않는다.
- `Value.Funcs[0]` → export 7 `xxPlayAnimatiomFunc_0`: `SkillAnimation=AC_Yetuga_JustGuardReaction.0`, `AnimBlendAlpha=0.3`.
- `Value.Funcs[1]` → export 6 `xxConsumeStaminaRegainFunc_2`: `StaminaConsumeRegainInfo.StaminaOperator=Rate`, `StaminaConsumeValue=500`. 함수명은 consume지만 실제 Rate 계산·부호·분모는 native 미확인이다.

`AC_Yetuga_DempseyRoll` export 0 `Notifies[73]`: `LinkValue=5.1676207`, `Duration=0.30028677`, export 80 `xxAnimNotifyState_SkillEventTag_1.Index=Index2`. NotifyEnable 조건의 정확 소비 방식을 확인하지 않았으므로 이 창 밖 모든 직가가 같은 그로기를 일으킨다고 일반화하지 않는다. Notify 수는 타수도 아니다.

`Y/Moving/Reaction/AC_Yetuga_JustGuardReaction` export 0은 `CA_M_Yetuga_DamageParry_F` segment `[0.0,1.26]`, playrate 1.0이다. **export 7 `xxAnimNotifyState_EnableCancelSK_0`**:

- `AnimSkillCancelMode=EAnimSkillCancelMode::ChangeNextSkill`.
- `ComboSkillInfo.ObjectPath=Y/Skill/24_Groggy/SI_Yetuga_Groggy.0`.
- 참조 Notify `Notifies[11]`: `LinkValue=0.51459247`, `Duration=0.102497935`, `NotifyName=xxEnableCancelSK`.

직가/패리 이벤트→반응 animation→다음 그로기 skill을 가리키는 cancel Notify라는 실제 자료 연결은 확인됐다. CancelSK의 자동 활성화 조건/취소 우선순위/상위 state override는 native 미확인이다.

`SI_Yetuga_Groggy` export 0 `SkillName.SourceString="직가 리액션 그로기"`, `SkillStatePtr` → `SB_Yetuga_Groggy_C`. 이 SB는 `xxCommonSimpleSkill`을 상속하며 export 1:

1. Step1→Step2, `AC_Yetuga_Groggy_Loop`, `AnimPlayRate=1.0`, `AnimLoopCount=1`, `AnimBlendAlpha=0.2`.
2. Step2→None, `AC_Yetuga_Groggy`, playrate/loop 동일, blend `0.1`.

두 composite는 `CA_M_Yetuga_GroggyStr_F_Loop` `[0.0,2.1666667]`, `CA_M_Yetuga_GroggyStr_F_End` `[0.0,2.3]`를 참조한다. AP 고갈 **New/GroggyStand** 포즈 및 PartGroggy 포즈와 구별된다. 이 전용 SI에는 부위 파괴 HP-1000/PartsDisolve 또는 회복 Rate99999 연결이 없다. 따라서 “직가 그로기=등 갑옷 파괴=스태미나 고갈”은 이 자료와 맞지 않는다. 직가로 스태미나가 결과적으로 고갈되는 경우의 native state 전이는 별도 확인이 필요하다.

`CS_Yetuga.0.ParringStaminaDamageTableSelect.ParringStaminaDamageTag`: table `BBQ/Content/_Common/Constants/ParringStaminaDamageDataTable.0`, `RowName="06_보스_중_2"`. 이 table은 Yetuga ZIP/index에 없고 SourceClosure external reference에만 있다. 일반 패리/직가의 스태미나 차감량을 Rate500과 동일한 전역 수치라고 할 근거는 없다.

## 5. 공격 종료/벽 충돌 회복 및 Armageddon 고갈 분기

공격 뒤 end/recovery pose는 상태 또는 resource 회복과 구별해야 한다. 확인 예로 `Y/Skill/10_ChargeTackle/SB_Yetuga_ChargeTackle` export 1:

- Step2 `AC_Yetuga_ChargeTackle_Run`와 Step3 `AC_Yetuga_ChargeTackle_Run_Loop`에 `xxSimpeEvnetTagOnCollisionWall` 태그가 있다.
- 해당 tag→`xxChangeNextStepFunc` 참조는 신규 JSON에 원시 값으로 저장했다. 벽 충돌용 Step7 `AC_Yetuga_ChargeTackle_Stun`→Step8 `AC_Yetuga_ChargeTackle_Stun_End`→None이 존재한다.
- 일반 진행 Step4 `AC_Yetuga_ChargeTackle_Run_End`→Step9 `AC_Yetuga_ChargeTackle_End`→None도 별개다.
- Step8/Step9 끝 이벤트의 함수는 `xxSimpleSkillEventFuncSkillCoolTime`다. 각각 export 12 `xxSimpleSkillEventFuncSkillCoolTime_0`, export 13 `xxSimpleSkillEventFuncSkillCoolTime_1`이며 양쪽 모두 `AddValue=20.0`, `bUseSelectSkill=true`, `SelectSkill.AssetPathName`→`SI_Yetuga_IceBreath`다. 스태미나 회복 함수나 PartDestructionGroggy로 동일시하지 않는다. 두 step의 playrate/loop는 1.0/1이다. native 조건 및 후딜 중 피해 배율/취소 가능 범위는 미확인이다.

Armageddon에는 스태미나 고갈을 별도로 유발하는 명시 경로가 있다. `Y/Skill/13_Armageddon/SB_Yetuga_Armageddon` export 1의 Step9 `SkillEventMap[0]` Index1→export 14 `xxSimpleSkillEventTag_2`(`AnimationNotifyStart`)→export 35 `xxSkillEventFunc_SelfStaminaExhaustion_0`(Properties `{}`). Step9 애니메이션 단순 종료 회복과 고갈 호출은 같은 종류가 아니다.

- Step1 EndSubState의 tag export 20→조건 export 27 Stamina/LessThanOrEqualTo→함수 export 8 `NextSubStateStep=Step9`.
- Step2 AnimationNotifyTick tag export 21→조건 export 28 동일→함수 export 9 Step9.
- Step8 EndSubState tag export 19→조건 export 26 동일→함수 export 6 Step9.
- 세 비교 조건의 threshold Value/Ratio는 누락됐다. 임의로 ≤0을 직접 원작값으로 쓰지 않는다.

Group1 보호 spell도 Armageddon에 연결된다. `SI_Yetuga_Armageddon` export 0 `SpellInfoList[0]` → `SP_Yetuga_Armageddon_PartOff.2`, `DurationMS=30000`; `[1]`→ `SP_Yetuga_Armageddon_PartOn.1`, `DurationMS=3000`.

- PartOff export 0 `xxSpellFunc_ActivePartDestruct_0`: `Group=Group1`, `bActive=false`, `bRevertActiveAtRemove=true`.
- PartOff export 1의 `xxSpellFunc_ReleaseOnEndState_0.EndSkillInfos`는 일반 `SI_Yetuga_Armageddon`과 `SI_Yetuga_S09_1_Armageddon`을 가리킨다. 저장 duration만으로 무조건 30초 파괴 면역이라고 설명할 수 없다.
- PartOn export 0은 `Group=Group1`을 명시하나 **bActive field가 누락됐다**. 이름만으로 true를 직접 확인값이라고 기입하지 않는다.
- SB Step1 StartSubState tag export 15→spell func export 34 `SpellInfoIndex=0`, `bUseRandomRate=true`; Step5 StartSubState tag export 17→func export 33 Index1, `bUseRandomRate=true`; Step6 StartSubState tag export 22→func export 32 Index1. RandomRate 수치/해석이 누락된 함수에 대해서 적용 성공을 항상 보장하지 않는다.

Armageddon BT 조건도 원시 값으로 보존한다. `Y/Base_Setting/BT_Yetuga` export 37/40/43의 `StatusConditions`: HealthPoint/LessThanOrEqualTo/Value65, Stamina/GreaterThanOrEqualTo/Value20, 모두 `bCompareRate=false`. SI input condition export 1에는 Stamina/GreaterThanOrEqualTo/Value1/RatioValue0.5가 있지만 bUseRatio field는 없다. 따라서 “HP65% 이하, 스태미나50% 이상”이라는 단정은 하지 않는다.

## 6. Brutal Attack 연결: 확인 자료와 미확인 경계

확인된 것은 Yetuga가 **피격자**로 사용할 Grapple animation mapping이다. `AP_Yetuga` export 0 `SpecialDamageAnimList`:

| Key | Value |
|---|---|
| `ESpecialDamageAniType::Grapple1` | `AC_Yetuga_DamageGrapple_Atk_01.0` |
| `Grapple2` | `AC_Yetuga_DamageGrapple_Atk_02.0` |
| `Grapple_Back1` | `AC_Yetuga_DamageGrapple_Atk_01_B.0` |
| `Grapple_Back2` | `AC_Yetuga_DamageGrapple_Atk_02_B.0` |

정면 두 composite는 원작 Yetuga `CA_M_Yetuga_DamageGrapple_Atk_01/02`를 사용한다. 후방 두 composite는 원작 ApesStoneHandElite의 `CA_M_ApesStoneHandElite_DamageGrapple_Atk_B_01/02`를 실제 참조한다. 종별 이름만으로 모두 Yetuga sequence라고 바꾸지 않는다.

이 mapping은 피격 포즈 선택 근거다. 플레이어 Brutal Attack 실행권, 약점/스태미나 조건, target query, 허용 거리/각도, 앞/뒤 판정, interaction request, 피해 수치, 기회 창의 전체 수명은 이 ZIP으로 확정되지 않는다. “부위 파괴 즉시 Brutal 가능”, “모든 직가 그로기에서 Brutal 가능”, “AP 고갈 blend0.2가 Brutal 입력 창”이라는 설명은 원본 근거 미확인이다. 이를 확정하려면 공격자 player Grapple/Burst 관련 SI/SB, native eligibility/targeting 소비 코드 또는 대응 원본 metadata가 필요하다.

## 7. 발견 전/인트로/전투 개시: 저장 범위

`LevelPresence.json`의 유일한 행은 level HeinMach, package `BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01`, actor `SA_Yetuga`, type `xxSpawnHandler_Character`다. 저장 `properties`의 `ActorBP_Soft` → CB_Yetuga, `SpawnInfo` → SA_Yetuga export 2, `SpawnIDX=82`, `BalanceGroupIndex=5`, `TIDX=283005`, **`bSpawnAtBeginPlay=false`**, `DependentLevelPath=/Game/_Kazan_/Level/HeinMach/HeinMach_Landscape2`.

`Y/Base_Setting/SA_Yetuga` export 2 `SA_Yetuga`: `TIDX=283005`, `Version=20`, DataScript→export 0→wrapper export 1의 TIDX 역시 283005. 원본 spawn identity는 일치한다. 저장 LevelPresence/SourceClosure spawn 행에는 `storedIntro`, `SpawnStart`, `BattleStart`, `InitSkill` field가 없다. CB CDO에도 InitSkill property가 없다. 이 누락은 “인트로가 없다”는 증거가 아니라 저장 범위가 호출 루틴을 담지 않았다는 뜻이다.

실제 존재와 연결은 다음과 같다.

- `SI_Yetuga_Roar.0.SkillName.SourceString="인트로 포효"`; SkillStatePtr → `SB_Yetuga_Roar_C`. SB export 1의 Step1→None은 `AC_Yetuga_Roar`, playrate 1.0, loop1, blend0.5, SkillEventMap `[]`.
- `SI_Yetuga_ChargeTackle_Intro.0.SkillName.SourceString="인트로 돌진 달리기"`; SkillStatePtr → 일반 `SB_Yetuga_ChargeTackle_C`; DamageInfos→L/R 두 자료. 이름만으로 초기 step을 별도 확정하지 않는다.
- CB `DefaultSkillList`에 두 SI가 등록돼 있다. 등록만으로 Roar→IntroTackle의 호출 순서 또는 플레이어 발견 트리거가 확정되지 않는다.
- AI_Yetuga export 1 `CombatTrigger`의 `BehaviorTree`는 `BT_Yetuga.0`다. 원본 전투 AI tree 연결과 level 인트로 sequence 트리거는 별개다. Skill의 `BattleStartCooltime`은 시작 cooldown parameter이며 전투 시작 시 그 skill을 실행한다는 지시가 아니다.

전체 원본 `HeinMach_Spawn_Main01` package는 Source ZIP/index에 없다. 정확한 발견 전 routine을 확인하려면 이 level package와 Yetuga boss intro를 호출하는 LevelSequence/trigger/InitSkill 소비 자료를 표적으로 확보해야 한다. 현재 ZIP의 581 JSON을 다시 전수 재출력할 필요는 없다.

## 8. 후속 조사에서 필요한 자료

1. `BBQ/Content/_Common/State/Base/SB_Base_PartDestruction_Groggy`: Yetuga subclass의 시작/루프/종료 실행, PartGroggy 회복 자동 호출 여부. index/ZIP에는 없고 SourceClosure external reference에 있음.
2. `BBQ/Content/_Common/Constants/ParringStaminaDamageDataTable`, row `06_보스_중_2`: 일반 직가/패리 스태미나 계산 parameter. index/ZIP에는 없고 external reference에 있음.
3. `BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01` 및 관련 Yetuga intro sequence/trigger: stored spawn 행에 없는 발견/인트로/개시 루틴.
4. native BBQ의 StaminaExhaustion timer, state input condition, Rate arithmetic, NotifyEnable/EnableCancelSK 소비 및 player Brutal/Grapple requester metadata: 절대 스태미나 단위, Rate 분모, 고갈/그로기 취소·연결, 실제 Brutal 기회 창.

현재 보고서는 원시 설정을 검증한 분석 결과다. 원작 runtime 재현·게임 자산 변경·PIE 검증을 완료했다는 기록이 아니다.
