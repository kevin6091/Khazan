# SwordShield 방패막기 원작 조사

## 2026-10-08 — 저장 원본 표적 조사와 최소 구현 권고

분석/권고만 수행했다. 게임 Source·BP·에셋·에디터·빌드를 변경하거나 실행하지 않았다. 대상은 일반 `Empire_SwordShield`이며 정예 `Empire_SwordShield_E`/SpearShield의 GuardCounter 자료를 섞지 않았다. 정확한 source file/package/export/field/원시 값·SHA는 [SwordShieldMechanism.json](../../Metadata/CombatReaction_20261008/SwordShieldMechanism.json)에 저장했다. 기존 원본25개, 선택 export23개, SystemGuard notify 구간11개와 현행 Guard clip11개를 표적 대조했으며 전체 리소스 조사를 하지 않았다.

설계 기준은 Architecture ARCH-82/83와 현재 Migration이다. 공유 자원·상태는 ASC/AttributeSet, 반응 실행은 Ability/Task, 제약은 기존 Locomotion handle을 사용한다. 아래 원작 데이터와 새 프로젝트 구현 정책/미확인 native 소비를 구분한다.

### 원본 파일 조회점

다음 표의 상대 파일명에 붙일 정확한 공통 prefix는 `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/Empire_SwordShield/`다. package는 그 아래 `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/Empire_SwordShield/`로 시작한다. 모든 원본 JSON의 SHA는 보고서 `source_manifest`에 있다.

| ID/원본 파일 | 확인할 내용 |
| --- | --- |
| `Base_Setting/CB_Empire_SwordShield.json` | CDO export1의 IdleStateClass, DamageStateClass, DeadStateClass, DefaultSkillList. |
| `Moving/Move/SB_Empire_SwordShield_Move.json` | CDO export1의 Normal/LockOn 이동별 damage mode와 SystemGuard angle. |
| `Base_Setting/SB_Empire_SwordShield_PassiveDodge.json` | export1 PassiveDatas, export2–9의 Guard 진입·성공 count·Broken 분기와 조건. |
| `Skill/Guard/SB_Empire_SwordShield_Guard.json` | export3 `xxGuardSkillInfo`, export2 무기별 성공 횟수와 능동 GuardBroken 전환. |
| `Skill/Guard/SI_Empire_SwordShield_Guard.json` | export0의 subtype/cooldown/자원 raw, export1 입력 자원 조건. |
| `Skill/GuardReaction/SB_Empire_SwordShield_GuardReaction.json` | export1 Hit→End, export2–7의 새 SystemGuard 적중 시 Hit 재진입. |
| `Skill/GuardReaction/SB_Empire_SwordShield_GuardReaction_Broken.json` | export1의 별도 Broken 반응. |
| `Base_Setting/AP_Empire_SwordShield.json` | export0의 일반 피격·소진·ParringBlock clip 연결. Guard success 전용 AP map은 직렬화돼 있지 않다. |

CS는 별도 새 표적 저장본 `Metadata/EnemyStaminaResearch_20261008/TargetedOriginal_01/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/Empire_SwordShield/Base_Setting/CS_Empire_SwordShield.json` export0이다. SHA `d0de0174dde64eecb98bd3f038e56333215b8299c53b966c02cd8628840d172f`. 기존 [원작 자원 감사](../Art/MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md)와 `StatusAndHoldingSupplement.json`도 재사용했다.

### 능동 Guard와 대치 중 SystemGuard는 별도다

CB CDO export1의 `Properties.IdleStateClass`는 `SB_Empire_SwordShield_Move.0`을 가리킨다. 그 Move CDO export1의 Battle map은 다음처럼 구분돼 있다.

| 정확한 field | 원시 값 | 판단 |
| --- | --- | --- |
| `NormalMoveInfoMap[Key=EAnimationState::Battle].Value.MoveDamageType` | `ECharacterDamageType::Normal` | 일반 이동은 이 map에서 SystemGuard를 설정하지 않는다. |
| `LockOnMoveInfoMap[Key=EAnimationState::Battle].Value.MoveDamageType` | `ECharacterDamageType::SystemGuard` | LockOn 대치/이동의 수신 반응 mode가 SystemGuard라는 직접 근거다. |
| 같은 LockOn entry의 `SystemGuardFrontAngle` | `180.0` | 각도 raw. native가 full cone/half-angle 중 무엇으로 소비하는지 미확인이다. |
| 능동 Guard SB export3 `Properties.FrontAngle` | `60.0` | SystemGuard180과 다른 설정이다. 대치 방패 조건에 이60을 대신 넣지 않는다. |
| 능동 Guard export3 `DefenseDir` | `[EGuardDirection::Front]` | 정면 방어 방향 설정은 직접 확인했다. |
| 능동 Guard `bGuardStartWithNotify`, `bEnableJustGuardAtStart` | 둘 다 `false` | 시작 방식의 flag다. 물리 패링/JustGuard를 구현했다는 뜻이 아니다. |

이 자료는 대치 중 방패를 올린 상태의 방어를 **SystemGuard 경로**로 구현할 근거다. 모든 Idle/Chase/Attack 상태에서 항상 방어한다는 universal predicate는 복구하지 못했다. 현행 ComboAction의 frontal `dot>=0`을 그대로 쓰는 것은 작은 프로젝트 정면 반공간 정책이며, raw180을 전체 cone180°로 해석한 것과 일관되지만 native 소비를 직접 확인한 사실은 아니다.

### 공격 중 예외와 반복 방패 적중

`xxAnimNotifyState_DamageType.Properties.CustomDamageType=SystemGuard`가 일부 공격과 GuardReaction에 실제로 있다. 아래 시간은 AC export0 `Properties.Notifies[].LinkValue/EndLink.LinkValue`의 원시 seconds다. 현재 retimed montage 시간이나 실제 승인 구간을 측정한 값이 아니며 적용하려면 기존 dilation/재생 시간 변환이 필요하다.

| AC 파일 (`Skill/` 아래) | notify export | 원시 시작→끝(s) |
| --- | ---: | --- |
| `Pierce/AC_Empire_SwordShield_Pierce` | 8 / 9 / 7 | `0→0.073623665` / `0.45407096→0.4874043` / `1.2101209→1.8333334` |
| `ShieldCrash/AC_Empire_SwordShield_ShieldCrash` | 7 / 8 | `-5.9604645e-08→0.23643371` / `0.7701271→2.0` |
| `SwordCombo/AC_Empire_SwordShield_SwordCombo_01` | 7 / 8 / 6 | `0→0.148839` / `0→0.4778877` / `1.5171657→2.2333333` |
| `SwordCombo/AC_Empire_SwordShield_SwordCombo_02` | 7 | `0.41852355→1.3333333` |
| `GuardReaction/AC_Empire_SwordShield_GuardReaction_Hit` | 3 | `0→0.6666667` |
| `GuardReaction/AC_Empire_SwordShield_GuardReaction_End` | 2 | `0→0.43333334` |

Pierce7/ShieldCrash8/SwordCombo01-6/02-7와 GuardReaction Hit3/End2는 `bResetCustomDamageTypeAtNotifyEnd=false`가 직접 기록돼 있다. 나머지 누락된 reset field의 native default는 확인하지 않았다. GuardReaction 둘은 `bDontAdditiveAnimation=true`도 가진다. 이 notify가 실제 방어 승인을 보장하는지, 겹친 notify의 우선순위·원복 순서는 native 미확인이다.

따라서 첫 구현에서 모든 공격/일반 피격 중 방패를 제외할 수는 있으나 **원작 전체 공격 중 방어 불가를 확인했다고 설명하면 안 된다**. 반대로 자기 guard-success Hit/End는 다음 SystemGuard 적중을 계속 받도록 별도 취급하는 원본 근거가 있다. GuardReaction SB export1 Step1(Hit)→Step2(End), export4/5의 damage-before event가 export6/7 `CharacterDamageType=SystemGuard`를 검사하고 export2/3의 `NextSubStateStep=Step1`으로 다시 보낸다. Hit 재진입에는 export2 `bEnableSameStep=true`가 있다.

### 성공 반응·회수부·Broken 모션

SystemGuard 성공 모션은 AP의 임의 DamageParry clip이 아니라 **GuardReaction SB가 직접 지정한** `AC_Empire_SwordShield_GuardReaction_Hit`와 `..._End`다. Step1의 `AnimBlendAlpha=0.05`, Step2의 `0.1`은 raw scalar이며 native에서 초 단위 blend duration인지 미확인이다. 두 step의 `AnimPlayRate=1.0`, `bApplyAttackSpeed=true`도 직접 기록했다. 최종 원작 속도를1배라고 단정하지 않는다.

현행 파일은 [Enemy Art 정본](../Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md)과 `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv`에서 다음처럼 찾는다. 초/FPS는 저장된 임포트·playback metadata로 원작 native reaction lockout을 뜻하지 않는다.

| 용도 | 현재 에셋 경로 | 저장 길이(s) |
| --- | --- | ---: |
| SystemGuard 성공 Hit | `/Game/_Art/Enemies/HeinMach/Humanoids/SwordShield/Animations/Guard/Guard_GuardReaction_Hit` | `0.6666666865348816` |
| SystemGuard End | `/Game/_Art/Enemies/HeinMach/Humanoids/SwordShield/Animations/Guard/Guard_GuardReaction_End` | `0.4333333373069763` |
| SystemGuard Broken | `/Game/_Art/Enemies/HeinMach/Humanoids/SwordShield/Animations/Guard/Guard_GuardReaction_Broken` | `2.2171151638031006` |
| 능동 Guard Start / Loop | 같은 Guard 폴더의 `Guard_Start` / `Guard_Loop` | `0.20000000298023224` / `2.0` |
| 능동 Guard Hit / End | 같은 Guard 폴더의 `Guard_Hit` / `Guard_End` | `0.6666666865348816` / `0.4333333373069763` |
| 능동 GuardBroken skill | 같은 Guard 폴더의 `Guard_Broken_Full_New` | `2.2157504558563232` |

`AP_Empire_SwordShield.Properties.ParringBlockDamageAnimations[TypeA]`는 별도 `AC_M_Empire_SwordShield_DamageParry_F`를 가리킨다. 이름이 Parry/Block이라는 이유만으로 이를 SystemGuard 성공 clip으로 대체하지 않는다. 소진은 같은 AP의 `StaminaExhaustionAnimSetMap`이 소유하는 기존 Groggy Start/Loop/End이며 GuardBroken clip과 같지 않다.

### 자원 소비와 guard break는 Stamina0 하나로 설명할 수 없다

CS export0 `Properties.StaminaStatus[Key=Battle].Value`의 원시 기록은 다음과 같다.

| field | raw | 단위/해석 범위 |
| --- | ---: | --- |
| `GuardStaminaConsumeRate` | `1.8` | raw rate. 현재 절대 `AttackWindows.StaminaDamage`에 그대로 곱하는 native 공식은 미확인. |
| `GuardStaminaRecoveryRate` | `0.0` | raw rate. 회복 없음 전체 정책을 이 하나로 단정하지 않는다. |
| `GuardStaminaRecoveryRateBySubState[GuardStanding/GuardSuccess]` | `1.0` / `0.4` | 상태별 raw rate. 적용 우선순위와 기준량 미확인. |
| `RecoveryPerSecond` | `80` | 원작 raw 자원/초. 프로젝트 gauge 환산 미확인. |
| `DamageStateRecoveryPerSecond[StaminaExhaustion]` | `100.0` | 원작 소진 중 별도 회복 경로. |
| `StaminaExhaustionInfo.StaminaExhaustionTerm` | `5.0` | 앞선 소진 구현이 초로 채택한 원본값. |

능동 Guard SI export0 `EndCooltime=10.0`, `StaminaConsumeRegainInfo={StaminaOperator=Rate,StaminaConsumeValue=1000}`, `StatusChangeInfoList[].StatusToChangeInfos={Stamina,Rate,-6500}`가 있다. `bUseRecoveryStamina=true`, `bNotChangeWhenShort=true`, `bCheckCanChange=true`도 기록돼 있다. Rate1000/-6500을1000 HP·10%·65% 같은 값으로 환산하지 않는다. SI export1 입력 조건은 `Stamina >=`, `bUseRatio=true`, `RatioValue=0.1`, `Value=50`이며 이와 능동 Guard raw cost를 passive SystemGuard 성공 비용으로 혼용하지 않는다.

능동 Guard SB export2의 성공 count component는 DualAxeSword/Spear `NeedWeaponSuccessCount=2`, GSword `1`, 기본 `NeedSuccessCount=3`이며 `NowNextSkill→SI_Empire_SwordShield_GuardBroken`, `bUseForceCancel=true`를 연결한다. GuardSkillInfo의 `EndCheckRemainStemina=0`도 raw로 있으나 정확한 소비·종료 비교는 native 미확인이다.

passive SystemGuard의 다른 분기는 `SB_Empire_SwordShield_PassiveDodge` export1 PassiveDatas가 export5→func3(GuardReaction), export6→func4(GuardReaction_Broken)로 연결한다. export5는 DualAxeSword/GSword/Spear 성공1회·`ResetTimeSeconds=0`·`PendingLimitTime=0.2`; export6은 None 및 세 무기 성공1회·`bCheckAttackerReactionValue=true`, `ConditionAttackerReactionValue=30`, reset/pending 각각2초다. **ReactionValue30의 실제 비교가 >=인지, 두 event의 실행 우선순위가 무엇인지, counter의 정확한 갱신은 복구하지 못했다.** Stamina0과 별개인 Broken 조건이 저장돼 있다는 점만 확정한다.

능동 Guard 승격의 별도 target-check export7은 circle `Yaw=90`, `RangeMax=500`, attack-box remain time `-0.2`와 active check를 가진다. export8은 Stamina ratio `>=0.2`, export9는 `bUseDont=true`, StaminaExhaustion과 Except StaminaExhaustionOrRemainTime을 기록한다. func2는 `bOnlyGroundDamageStateCancel=true`, `bExceptGetupStateCancel=true`, GuardReaction/Broken cancel blacklist다. 이 raw 예외의 native 조합을 passive 방패 승인 조건처럼 그대로 구현하지 않는다.

### unblockable·죽음·소진 우선순위의 확인 한계

현재 표적 CB의 `xxHitComponent` export44에는 override Properties가 없다. 저장 자료에서 원작의 전체 unblockable incoming damage-type/flag allowlist, chip HP 공식, guard 승인 native body를 찾지 못했다. `ECharacterDamageType::SystemGuard`는 여기서 피격자의 mode/반응이고 들어오는 공격 종류의 전체 enum 표가 아니다. 강한 공격은 무조건 unblockable이라는 주장은 ReactionValue30 Broken 설정만으로 증명되지 않는다.

Common_Damage_Guts의 기존 저장 metadata에는 `IsStaminaExhaustionTimeEnd`, `GetHoldAttacker`, `IsEndHolding`, `DoForceHoldDead`, `ConditionalSetDeadState` 관련 함수명/ChildProperties가 있다. bytecode를 복구하지 않았으므로 원작의 SystemGuard/죽음/소진 정확한 우선순위를 증명하지 못한다. 프로젝트 현행 `AKZMonster::RefreshCombatState`의 HP0 우선, Stamina0→Exhaustion, paired lethal presentation 완료 후 freeze는 이미 구현·검증된 별도 계약으로 유지해야 한다.

### 현재 코드에서 막히지 않는 이유와 가장 작은 연결

현행 `KZComboActionAbility.cpp`는 Monster만 대상으로 `Window.bBlockable && frontal dot>=0 && TargetASC->TryGuardHit(Window.StaminaDamage,Avatar)`를 호출한다. true면 일반 HP/Stamina 피해 GE를 추가 적용하지 않는다. 그러나 현재 ASC `TryGuardHit`는 이미 활성화된 `UKZGuardAbility`만 순회한다. SwordShield의 저장 grant에는 세 공격·Alert/Idle·Exhaustion이 있고 이 held-input Player Guard는 없다.

Player `UKZGuardAbility::TryGuardHit`는 `IsGuardInputHeld`, 자기 `GuardStateHandle`, `State.Guarding`, Player용 montage sections를 요구한다. 그 클래스를 단순히 SwordShield에 grant하거나 항상 켜면 해결되는 구조가 아니다. 다음은 권고이며 실제 적용이 아니다.

1. 기존 CharacterDefinition에 편집 가능한 shield 승인/비용/성공 반응 설정만 추가하고 SwordShield에만 켠다. HP>0·Stamina>0·Dead/Exhausted 없음과 실제 combat target/LockOn 정책을 현재 ASC/Locomotion/Controller에서 파생한다. 별도의 변경 가능한 AI phase/Guard bool을 복제하지 않는다.
2. 기존 ASC `TryGuardHit`의 Player active Guard 처리는 유지하고, 해당 Monster의 작은 synchronous shield 승인 경로를 fallback으로 연결한다. 기존 `Window.bBlockable=false`는 프로젝트 unblockable bypass로 유지한다. 원작의 완전한 damage-type matrix로 설명하지 않는다.
3. 처음 범위는 대치/idle과 자기 shield-success 반응이다. 공격·일반 wound reaction·air/down·Brutal/Exhaustion/death는 거부한다. 모든 공격 제외는 이번 작은 범위 결정이며 원작의 부분 SystemGuard notify는 후속 대상으로 남긴다.
4. 승인된 방패 적중은 기존 instant GE에 HP0·편집된 Stamina 비용을 한 번 적용하고 true를 반환한다. 이후 반응 montage가 실패/취소돼도 일반 피해를 중복 적용하지 않는다. 비용을 전혀 확정하지 못한 거부는 false로 일반 hit를 보존한다. 비용 scale로 raw1.8을 채택한다면 **현재 절대 피해에 대한 임시 프로젝트 multiplier**임을 표시해야 한다.
5. 이번에 실제 피격 반응을 위해 구현할 유한 Monster reaction Ability가 GuardReaction Hit→End Task를 함께 소유하도록 작은 반응 선택/API를 추가한다. 자기 guard-success 중 새 shield hit는 Hit을 다시 시작한다. 일반 wound 반응과 구분하고, death/exhaustion은 이 유한 반응을 취소하며 자기 Task/delegate/constraint만 반환한다. Player Guard의 held 수명/ABP를 변경하지 않는다.
6. Stamina0은 기존 attribute delegate→Exhaustion 경로에 맡기고 no-auto-regen/no-attack-cost를 유지한다. 원작의 weapon count/ReactionValue 기반 Broken, 능동 Guard Start/Loop/cooldown/cost, 공격 중 부분 방어 구간은 별도 후속이다.

검증할 경계는 front/back·blockable false·combat/일반 이동·공격/일반 반응/guard-success 재적중·Stamina 부족/0·동일 GE의 HP0 우선·Task 실패 뒤 중복 HP 피해 없음·취소/UnPossess/EndPlay·기존 Player Guard 회귀다. 현재 보고서는 그 테스트나 구현을 완료한 결과가 아니다. Art 원본/current clip은 기존 index를 참조하면 되므로 별도 재추출·retime·Art asset 수정은 필요하지 않다.

### 2026-10-08 — 현재 ComboNode의 몽타주 좌표로 변환한 SystemGuard 구간

아래는 원작 직접 기록값이 아니라 **저장된 원작 dilation 자료와 현재 author 계약으로 계산한 값**이다. 원시 AC 초에 이미 구워진 DilationCurve를 다시 무시하거나, 현재 길이 비례로 압축하지 않는다. `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/PlaybackEventTimes.json`의 exact package/notify export 매칭으로 원시 시간→baked local 초를 얻었다. `Metadata/MonsterAI_20261006/AuthoringPlan.json`과 `Scripts/Engineering/MonsterAuthorEditor.cpp::Ability`는 각 클립 전체 구간, `AnimPlayRate=1`, loop1, 앞 segment 길이 누적 `StartPos`를 사용한다. 현재 이름은 `Metadata/EnemyAnimationOrganization_20261007/MontageRenameApplied.json`으로 연결했다. 네 InGame 공격 클립의 현재 `RateScale=1`과 길이는 `CurrentAnimationLibrary.csv`에도 일치한다. 새로운 editor readback을 실행한 결과로 표현하지 않는다.

현재 ComboDefinition의 공통 위치는 `/Game/Monsters/SwordShield/Data/DA_Combo_Empire_SwordShield_<이름>`, 몽타주는 `/Game/Monsters/SwordShield/Animations/Attack/Montages/Attack_<이름>`이다. 표의 초는 **actual montage instance의 asset position**과 비교할 절대 몽타주 좌표이며, Ability 활성화 이후 wall-clock 초가 아니다.

| 이름 / NodeId | 원본 notify export | baked local 시작–끝(초) | 현재 몽타주 시작–끝(초) |
|---|---:|---:|---:|
| SwordCombo / Step1 | 7 | 0–0.14848883200935281 | 0–0.14848883200935281 |
| SwordCombo / Step1 | 8 | 0–0.4480854862701863 | 0–0.4480854862701863 |
| SwordCombo / Step1 | 6 | 1.47313692996412–2.190962553024292 | 1.47313692996412–2.190962553024292 |
| SwordCombo / Step2 | 7 | 0.42210744238491554–1.3854866500009 | 2.6130699954092074–3.576449203025192 |
| Pierce / Step1 | 8 | 0–0.077884288322960932 | 0–0.077884288322960932 |
| Pierce / Step1 | 9 | 0.61315957522622389–0.641930904995338 | 0.61315957522622389–0.641930904995338 |
| Pierce / Step1 | 7 | 1.5850607181109635–2.22951976000024 | 1.5850607181109635–2.22951976000024 |
| ShieldCrash / Step1 | 7 | 0–0.23643368411579119 | 0–0.23643368411579119 |
| ShieldCrash / Step1 | 8 | 0.75249452560555019–1.7900286912918091 | 0.75249452560555019–1.7900286912918091 |

계산식은 `montage_time = StartPos + baked_local_time / segment_AnimPlayRate`다. SwordCombo Step2의 `StartPos=2.190962553024292`는 현재 Step1 클립 전체 길이다. Step1→Step2 명령 전이 notify 시각 `0.7774296450818909`를 Step2 segment 시작 위치로 착각하지 않는다. 실제 전이를 선택하면 Step1의 후반 SystemGuard 구간까지 재생되지 않을 수 있다. 활성 Node와 실제 playing montage/instance를 확인한 뒤 asset position을 조회해야 한다.

SwordCombo Step1의 export7/8은 중첩되므로 finite interval 승인에서는 `[0,0.4480854862701863]`으로 합집합해도 같다. 출처 JSON에는 두 원본 구간을 각각 보존했다. source event table의 일부 end는 `LinkValue+Duration`으로 계산돼 serialized `EndLink.LinkValue`와 float 정밀도만큼 다르다. raw 양쪽 값·table 값·현재 clip-bound clamp를 JSON에 모두 남겼다. 표의 SwordCombo Step1 마지막 끝과 ShieldCrash 마지막 끝은 table 끝이 현행 `GetPlayLength`를 미세하게 넘어 clip 길이로 clamp한 값이다. 트리거 offset을 추가한 실제 native 승인 시각은 확인하지 않았다.

`FKZComboNode::SystemGuardWindows`에 이 값을 사용할 경우 이번 계약은 **원본에 기록된 finite notify 구간 재현**이다. 명시된 `bResetCustomDamageTypeAtNotifyEnd=false` 또는 생략 default가 native에서 모드를 끝 이후까지 유지하는지 미확인이므로, 완전한 native 상태 수명을 증명한 표로 사용하지 않는다. 앞 절의 모든 공격 제외 권고는 이제 이 exact window가 있는 공격에 한해 선택적으로 확장할 수 있다. 다른 공격·일반 반응·Dead/Exhausted 승인 우선순위는 기존 정책대로 유지하며 root가 구현한다. 이번 추가 기록도 게임 Source/에셋 변경이나 PIE 검증 완료를 의미하지 않는다.

### 2026-10-08 — 격리 작성 도구의 현재 좌표 계약 확인

root가 별도로 구현 중인 Work의 실제 `FKZComboNode::SystemGuardWindows`는 **Node-local playback seconds**다. `UKZComboActionAbility::IsInSystemGuardWindow()`가 실제 montage position에서 현재 section 시작을 뺀다. 따라서 author에는 위 표의 **baked local 열**을 저장하고, 절대 몽타주 열은 대응 검증/관측용으로 보존한다. 특히 SwordCombo Step2에 절대 시작 `2.6130699954092074`를 직접 저장하지 않고 local `0.42210744238491554`를 저장한다. 현재 실행 노드·몽타주·section 동일성 검사를 함께 유지한다.

해당 exact interval은 `Metadata/CombatReaction_20261008/ReactionAuthoringPlan.json`의 `system_guard_windows`에도 출처별 9개로 옮겼다. Work-only 임시 `Source/Khazan/Tests/CombatReactionAuthorEditor.cpp`의 `Khazan.Combat.ReactionAuthor`가 현재 몽타주의 section offset을 출처와 비교한 뒤 Combo 3개에 local 구간을 작성하도록 준비했다. 이 도구는 exact isolated Work/no-PIE 조건을 요구하며 이번 작성 담당자는 빌드/에디터/에셋 작성을 실행하지 않았다. 원작 native reset·unblockable matrix·완전한 SystemGuard 수명 미확인 상태는 바뀌지 않는다.
