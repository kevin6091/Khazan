# Yetuga 원본 스킬 연결 표적 분석 — 2026-10-08

## 검증 범위와 용어

`SB_Yetuga_NormalAtk01/02`, `DempseyRoll`, `DashAtk`, `Armageddon`, `IceBreath`, `RushGrab`, `CloseGrab`의 저장 원본 JSON을 확인했다. 관련 SB 8개에서 CDO → SubStateInfos → SkillEventMap → tag/condition/function export를 따라갔고, 연결된 AC와 SI/SD를 확인했다. 총 75개 저장 원본의 SHA256이 `Index.json`의 원본 SHA256과 일치했다. 각 `ObjectPath` 끝 `.N`을 JSON 배열의 0-based export index로 해석해 ObjectName의 최종 이름과 실제 export.Name 일치를 검증했다. 전체 237개를 다시 조사하지 않았다.

연구 스크립트는 `Scripts/Research/AnalyzeYetugaOriginalSkills_20261008.py`, 상세 근거는 `YetugaOriginalSkillAnalysis.json`이다. 기존 Docs/game Source/BP/asset을 수정하지 않았다. 원작 `/Script/BBQ` native 함수 본문, 클래스 기본값, 실제 게임 실행은 검증하지 않았다.

- **직접 확인:** 저장 필드 값, enum, export 참조, 애니메이션 Notify의 인덱스/원래 시간축 값.
- **원본 기반 계산:** 명시된 `EAttackNotifyGroup` 값의 서로 다른 개수 및 동일 그룹의 Notify 묶음.
- **미확인:** 생략 필드의 native 기본값, 조건 배열의 AND/OR 결합, 이벤트 우선순위, 강제 취소/분기 전환의 실제 실행 순서, 그룹 적중 이력의 보존·Reset, 동일 대상 실제 피해 횟수.

`AttackBoxComponentGroup`(충돌 컴포넌트 그룹)과 `Group`=`EAttackNotifyGroup`(공격 Notify 그룹)을 구분한다. 한 동작에 손/팔/몸 여러 hitbox Notify가 같은 Group으로 겹쳐 저장돼 있다. Notify 수나 step 수를 타수로 세지 않는다. `AttackIntervalDesc`의 “1회 공격”은 원작 authoring 설명으로 보존하지만 native 중복 적중 방지 로직까지 확인한 것은 아니다. AC 그룹 계산은 연결된 Composite의 명시적 Notify에 한정하며, native 또는 연결 AnimSequence의 추가 동작을 검사했다고 주장하지 않는다.

아래 `.N`은 해당 JSON의 export index이다. 모든 패키지의 공통 접두사는 `BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Skill/`이며 각 파일의 전체 Package는 JSON에 보존했다. 거리·각도는 저장 원시 값으로 적는다. UE 좌표/각도라는 해석과 native 거리 계산·FrontBaseAngle의 반각/전체각 의미는 미확인이다. 초 단위 시간축은 AC의 원래 `LinkValue`/`Duration`이며 TimeDilation/공격속도/재생률을 적용한 최종 플레이 시간으로 변환하지 않는다.

## 공격 그룹 요약

| SB | 실제 연결 AC의 명시적 Group | 원본 기반 계산 | 피해 횟수로 확정하지 않는 이유 |
|---|---|---|---|
| NormalAtk01 | `_01`: Group1; `_02`: Group2/3; `_03`: Group4/5 | 세 AC에 합계 **5개 고유 그룹**, Attack Notify는 3+6+6 | SI 이름은 “1_손바닥4연타”. 시각적 4동작과 5개 피해 그룹은 별도 계약 |
| NormalAtk02 | `_01`: Group1; `_02`: Group1 | 각 단계 AC에 **1개씩**, Attack Notify 각각 3 | 같은 Group1의 단계 간 Reset 소비를 미확인. 조건에 따라 두 번째 AC 생략 가능 |
| DempseyRoll | 본공격: Group1–5; SideL/SideR: 각각 Group1; Back/BackMoving: 없음 | 본공격 **5개**, Attack Notify 15. 각 준비 측이동에 별도 1개 그룹 | 측이동은 선택 분기다. 모든 AC를 합쳐 고정 6타로 만들지 않음 |
| DashAtk | Fast/일반: 각각 Group1/2; Back/Dash: 없음 | 선택된 공격 AC에 **2개**, Attack Notify 각각 4 | Fast와 일반을 함께 재생하지 않는 대체 경로. 착지와 후반 주먹 회수의 별도 그룹 |

## 1. NormalAtk01: 4동작 이름, 5개 그룹, 회수 후 위치 분기

출처: [SB_Yetuga_NormalAtk01.json](SB_Yetuga_NormalAtk01.json), [SI_Yetuga_NormalAtk01.json](SI_Yetuga_NormalAtk01.json), [AC_Yetuga_NormalAtk01_01.json](AC_Yetuga_NormalAtk01_01.json), [AC_Yetuga_NormalAtk01_02.json](AC_Yetuga_NormalAtk01_02.json), [AC_Yetuga_NormalAtk01_03.json](AC_Yetuga_NormalAtk01_03.json).

CDO `.1.Properties.SubStateInfos`의 기본 연결은 `Step1(_01) → Step2(_02) → Step3(_03) → None`이다. 저장 기본 연결에서 가까운/먼 거리로 첫 세 공격 AC 자체를 끊는 조건은 없다.

| AC | 공격 export | Group / DamageInfoIndex | 원래 LinkValue |
|---|---|---|---|
| `_01` | .5/.6/.7 | Group1 / index 생략 | 1.0524035 / 1.0524035 / 1.0754114 |
| `_02` | .13/.10/.11 | Group2 / 1 | 0.7015753 / 0.7015753 / 0.71976125 |
| `_02` | .8/.9/.12 | Group3 / 2 | 1.9143326 / 1.914733 / 1.9505678 |
| `_03` | .5/.7/.9 | Group4 / 3 | 0.49955666 / 0.499557 / 0.499557 |
| `_03` | .8/.10/.6 | Group5 / 4 | 0.667212 / 0.667212 / 0.66721225 |

SI `.0.Properties.DamageInfos`는 R, L, R_02, L_02, Strong 순서다. 첫 그룹의 DamageInfoIndex는 직렬화에서 생략됐으므로 임의로 0을 채우지 않았다. 마지막 `_03`에는 **Group4와 Group5가 서로 다른 시간에 저장**돼 있다. 공개 공략의 “4동작 마지막에 2타”를 뒷받침하는 구조지만 실제 두 번 피해를 반드시 받는다는 런타임 증거는 아니다.

`_02` Group3의 DamageInfoIndex2는 SI의 `SD_Yetuga_NormalAtk01_R_02`를 가리키지만 attack export `.8/.9`의 BoneName은 각각 `Bip001-L-Hand`/`Bip001-L-Forearm`이다. damage asset 이름만으로 실제 사용 손을 확정하지 않는다. 이 차이의 의도·시각 동작은 원본 애니메이션 재생과 native 적중 소비를 따로 확인해야 한다.

Step3의 후속은 모두 `SkillEventMap`이다.

| Step3 event | tag → condition export | function export와 저장 후속 |
|---|---|---|
| Index1 | `.6` AnimationNotifyStart → `.14` MaxDistance600, FrontBaseAngle90, Back; `.12` RandomRate0.5; `.16` 앞 벽 검사 DirectionCheckDistance1500, Front:Fail | `.2` → TurnBackRun_Short, NowNextSkill, bUseCoolTime=false, bUseForceCancel=true |
| Index2 | `.9` AnimationNotifyStartEnd → `.18` Left wall800:Fail; `.11` AITarget circle RangeMax800 | `.5` → SideMove Step5, LockOnTarget, RandomRate0.5, no cooltime, force cancel |
| Index3 | `.7` AnimationNotifyStartEnd → `.17` Right wall800:Fail; `.10` AITarget circle RangeMax800 | `.4` → SideMove Step6, LockOnTarget, RandomRate0.5, no cooltime, force cancel |
| Index4 | `.8` AnimationNotifyStart → `.13` HP LessEqual, bUseRatio=true, RatioValue0.7; `.15` LockOnTarget MaxDistance300 | `.3` → RushGrab, NowNextSkill, force cancel |

`_03`의 Index1–4 Notify가 각각 SB 후속과 연결돼 있다. Index5와 `_02` Index1의 Variation1 Notify도 있으나 현재 CDO의 해당 step에 같은 event index가 저장되지 않았다. 이를 일반 공격 추가타·미사용 데이터·특정 phase 전환으로 단정하지 않는다. 상속/native 소비를 확인하지 못했다.

## 2. NormalAtk02: 거리 조건부 두 번째 공격

출처: [SB_Yetuga_NormalAtk02.json](SB_Yetuga_NormalAtk02.json), [AC_Yetuga_NormalAtk02_01.json](AC_Yetuga_NormalAtk02_01.json), [AC_Yetuga_NormalAtk02_02.json](AC_Yetuga_NormalAtk02_02.json).

- Step1 기본 Next=None, AC `_01`은 왼손/왼팔/지면 hitbox가 모두 Group1이다.
- Step1.Index1 → tag `.3` EventTag=AnimationNotifyStart → condition `.4`: LockOnTarget, bCheckDistance=true, MaxDistance=800 → function `.2`: NextSubStateStep=Step2.
- 해당 AC event Notify `.30`은 Index1, LinkValue=2.1503704, Duration=0.26464796이다.
- Step2 기본 Next=None, AC `_02`는 오른손/오른팔/몸 hitbox가 모두 Group1, DamageInfoIndex=1이다.

따라서 **첫 공격 후 event 시점의 거리 조건으로 두 번째 AC를 연결하는 데이터 경로**가 직접 확인된다. 범위 밖이면 기본 종료라는 해석은 구조와 일치하지만 실제 조건 경계·목표 선택·전환 적용 시점은 native 소비 미확인이다. “항상 2타”라고 구현하면 이 저장 조건을 잃는다. `_01`의 Variation1 Index2 Notify는 같은 SB step의 event map에 없다.

## 3. DempseyRoll: 준비 방향, 5개 그룹, 마지막 방어 반응, CloseGrab

출처: [SB_Yetuga_DempseyRoll.json](SB_Yetuga_DempseyRoll.json), [AC_Yetuga_DempseyRoll.json](AC_Yetuga_DempseyRoll.json), SideL/SideR/BackMoving AC, [SI_Yetuga_DempseyRoll.json](SI_Yetuga_DempseyRoll.json).

기본 step 연결은 `Step1 Back → Step3 BackMoving → Step2 본공격 → None`이며 Step4 SideL/Step5 SideR도 기본 다음은 Step2다.

- Step1.Index1 → tag `.10` StartSubState → condition `.16` FrontBaseAngle90, Front, UseSkillTarget/LockOnTarget → function `.2` NextStep3.
- Step3.Index1 → tag `.12` StartSubState → function `.4`: `StepAction=DoChangeAllRandomStep`, AllRandomSubSteps=[Step4,Step5]. 확률 분포·시드·재선택은 미확인이다.
- Step4.Index1 `.13`/condition `.18`, Step5.Index1 `.14`/condition `.19`: bCheckDistance=true, MaxDistance300, FrontBaseAngle90, Front, CheckType=Fail → function `.5`/`.3` NextStep2. TargetSelectionTypes가 생략됐다.

본공격 Group1–5는 각각 세 개 hitbox Notify가 같은 Group으로 묶인다. 대표 손 Notify는 다음과 같다.

| Group | AC export / BoneName | LinkValue | DamageInfoIndex |
|---|---|---|---|
| 1 | .20 / Bip001-L-Hand | 1.1931529 | 생략 |
| 2 | .13 / Bip001-R-Hand | 2.1802614 | 1 |
| 3 | .22 / Bip001-L-Hand | 3.1922083 | 생략 |
| 4 | .23 / Bip001-R-Hand | 4.1928735 | 1 |
| 5 | .26 / Bip001-L-Hand | 5.1746855 | 2 |

이는 **왼→오른→왼→오른→왼의 5개 본공격 그룹**을 직접 뒷받침한다. SideL/SideR 준비 AC는 각 Group1의 4개 hand/forearm Notify를 갖는다. 같은 그룹의 두 팔을 무조건 2타로 세지 않는다.

**마지막 방어 반응:** SB Step2.Index2 → reaction tag `.8`의 Results=[ParryingReaction,JustGuardReaction] 및 NotifyEnable condition `.15` → function `.7` AC_Yetuga_JustGuardReaction, AnimBlendAlpha0.3 + function `.6` StaminaOperator=Rate, StaminaConsumeValue=500. AC 본공격 `.80` Index2 Notify는 LinkValue5.1676207, Duration0.30028677로 Group5 구간과 겹친다. 따라서 마지막 구간의 방어 반응에 authored gating이 존재한다. **raw500을 500 stamina, 500%, 5% 등으로 변환할 native 근거는 확보하지 않았다.** 재생 교체·현재 skill 종료·고갈 유발 순서 역시 미확인이다.

**CloseGrab 후속:** SB Step2.Index1 → tag `.11` AnimationNotifyStart → condition `.17`: LockOnTarget, bCheckDistance=true, MaxDistance500, FrontBaseAngle90, Front → function `.9`: SI_Yetuga_CloseGrab, NowNextSkill, bUseCoolTime=false, bUseForceCancel=true. AC `.81` Index1 Notify는 LinkValue6.51835, Duration0.23164988이다.

여기에 “직전가드 실패” 또는 “Parry 실패”라는 bool/Fail 조건은 저장돼 있지 않다. 마지막 방어 반응이 발생하면 이후 CloseGrab event까지 도달하지 않는지 여부는 native 실행·런타임 검증이 필요하다. 공개 위키의 “5타 방어 실패 시 근접 잡기”는 그때까지 **관측 기반 설명**으로 유지해야 한다.

## 4. DashAtk: 접근 후 Fast/일반 대체, 착지와 회수의 두 그룹

출처: [SB_Yetuga_DashAtk.json](SB_Yetuga_DashAtk.json), [AC_Yetuga_DashAtk_Fast.json](AC_Yetuga_DashAtk_Fast.json), [AC_Yetuga_DashAtk.json](AC_Yetuga_DashAtk.json), Back/Dash AC.

기본 연결 `Step1 Back → Step2 Dash → Step3 Fast → None`; Step4 일반은 별도 종료형 대체 AC다.

- Step1.Index1 `.4` StartSubState → condition `.6`: LockOnTarget, bCheckDistance=true, MaxDistance500, FrontBaseAngle35, Front, CheckType=Fail → function `.2` NextStep2. **bCheckBaseDirection은 생략**돼 있으므로 각도 조건 활성화를 추정하지 않는다.
- Step2.Index1 `.5` StartSubState → condition `.7`: LockOnTarget, bCheckDistance=true, MaxDistance1500 → function `.3` NextStep4. 기본은 Step3이므로 거리 조건에서 일반 AC로 바꾸는 구조다.
- Fast에는 Group1(.8/.7)과 Group2(.9/.10), 일반에는 Group1(.7/.10)과 Group2(.8/.9)가 저장돼 있다. 각 그룹은 오른손 box와 지면 cylinder를 묶는다.
- 대표 손 LinkValue는 Fast Group1=0.7466415 / Group2=4.76274; 일반 Group1=0.93314517 / Group2=4.9571233이다. Group2를 회수 동작 때의 위험 구간으로 식별하는 것은 공개 클립과 대응하지만 원래 AC를 시각 재생한 검증은 아니다.

Fast/일반에는 Index10 Variation1과 Index1/2 Notify가 있으나 현재 CDO Step3/4 SkillEventMap은 비어 있다. 이를 추가 NextSkill로 읽지 않았다.

## 5. Armageddon: AttackSuccess→RushGrab, 스태미너 분기→반응/고갈

출처: [SB_Yetuga_Armageddon.json](SB_Yetuga_Armageddon.json), [SI_Yetuga_Armageddon.json](SI_Yetuga_Armageddon.json), Armageddon AC들, [SD_Yetuga_Proto_Armageddon_02.json](SD_Yetuga_Proto_Armageddon_02.json).

기본 연결은 `Step1 Start → Step2 JumpStart → Step3 JumpEnd → Step5 End → None`; Step4 JumpEnd_Close와 Step6 End, Step7 Back, Step8 Start, Step9 DamageParry_F가 대체 경로다.

| 조건 경로 | 저장 참조와 결과 |
|---|---|
| 시작 시 방향 실패 | Step1.Index1 → tag `.18` AnimationNotifyStart → condition `.31` FrontBaseAngle80, Front, CheckType=Fail → function `.7` Step7; Step7→Step8→Step2 |
| 가까운 목표 검색 | Step2.Index5 → tag `.12` EndSubState → condition `.25` AITarget circle RangeMax2000/Yaw360, HeightMin−1000/Max1000 → function `.5` Step4 |
| 원거리 착지 후 공격 성공 | Step3.Index1 → tag `.13` AnimationNotifyStart → conditions `.24` AttackSuccess(필드 없음) 및 `.29` FrontBaseAngle70, Front → function `.3` Step6 |
| 가까운 착지 OnAttack | Step4.Index2 → tag `.10` OnAttack(필드 없음) → function `.4` Step6 |
| 가까운 이동 종료 | Step4.Index1 → tag `.23` StopReasons=[MoveOnFloor] → function `.2` Step5 |
| Step6 후속 | Step6.Index1 → tag `.16` AnimationNotifyStart → condition `.30` UseSkillTarget/LockOnTarget, bCheckDistance=true, MaxDistance1500, FrontBaseAngle70, Front → function `.11` **RushGrab Step5**, no cooltime, force cancel |
| 스태미너 조건 | Step1.Index2 / Step8.Index2 / Step2.Index2 → tag `.20` / `.19` / `.21` → condition `.27` / `.26` / `.28`: Stamina LessEqual, 비교 값·ratio 필드 생략 → function `.8` / `.6` / `.9` Step9 |
| 반응 후 고갈 | Step9.Index1 → tag `.14` AnimationNotifyStart → function `.35` xxSkillEventFunc_SelfStaminaExhaustion(필드 없음) |

**Armageddon SB에는 Results=JustGuardReaction/ParryingReaction을 직접 판정해 RushGrab으로 보내는 tag가 없다.** 저장 직접 조건은 AttackSuccess/OnAttack과 방향/거리다. `xxSimpleSkillTagCondition_AttackSuccess`가 가드·직전가드·패링·무피해를 어떻게 처리하는지, `OnAttack`이 정확히 어느 결과에 발화하는지 native 본문 미확인이다. 스태미너 LessEqual 비교 값도 생략됐으므로 임의로 `<=0`을 채우지 않았다. Step9의 이름/애니메이션은 Parry 반응을 시사하지만 이를 곧바로 BrinkGuard 판정 자체와 같다고 하지 않는다.

착지 AC JumpEnd `.3`, JumpEnd_Close `.4`의 공격 Notify에는 DamageInfoIndex=1이 저장돼 있다. SI DamageInfos[1]→SD_Proto_Armageddon_02 `.0.Properties.AttackInfo.GuardDamageInfo.bDontJustGuard=true`. 이로써 **거대 착지 폭발의 직전가드 금지 데이터**가 확인된다. Parry/일반 Guard와 이 필드의 상호작용은 별도 소비 검증이 필요하다. Start의 SD_01 StaminaBreak 공격과 착지 SD_02를 같은 방어 계약으로 묶지 않는다.

Step6.Index2 `.22`→function `.32` SpellInfoIndex1, Step5.Index2 `.17`→`.33` SpellInfoIndex1 및 bUseRandomRate=true, Step1.Index3 `.15`→`.34` SpellInfoIndex0 및 bUseRandomRate=true가 저장돼 있다. SI SpellInfoList[0]=PartOff DurationMS30000, [1]=PartOn DurationMS3000. 이것은 부위 spell의 저장 수명이며 phase HP 조건이나 Exhausted 시간으로 대체하지 않는다.

## 6. IceBreath: 후퇴 변형, 생성·파쇄, ChargeTackle 후속

출처: [SB_Yetuga_IceBreath.json](SB_Yetuga_IceBreath.json), IceBreath AC들과 SI/SD.

기본 연결 `Step1 Back → Step5 BackJump → Step2 Breath01 → Step3 Breath02 → Step4 End → None`.

- Step1.Index1 `.12` StartSubState→condition `.18`: FrontBaseAngle90/Front, MaxDistance800이 있으나 **bCheckDistance 생략**→function `.4` Step5.
- Step1.Index2 `.11` StartSubState→condition `.20`: Back wall DirectionCheckDistance500, Success→function `.3` Step2. 후방 벽 확인으로 BackJump를 건너뛰는 저장 경로다.
- Step5.Index1 `.13` StartSubState→condition `.19`: bCheckDistance=true, MaxDistance700, CheckType=Fail→function `.2` Step2.
- Step2.Index1 `.7` TimerLoop: Time0.4, MaxCount10, NotifyEnable `.16`→function `.6` COI_Yetuga_IceBreath_OBJ spawn, SpawnType `.24`. **TimerLoop 최대 수를 브레스 적중 횟수로 세지 않는다.**
- Step2.Index2 `.14` AnimationNotifyStart→function `.5` COI_Yetuga_IceBreath_Field_OBJ spawn, SpawnType `.23`.
- Step3.Index1 `.9` AnimationNotifyStart→function `.15` ChangeTargetSkill, finder `.21`는 이 skill이 생성한 Field_OBJ, TargetNum0, ChangeStepType=Step8. 객체의 Step8을 호출하는 것이며 Yetuga 자신의 숨겨진 8타라는 뜻이 아니다.
- Step4.Index1 `.10` AnimationNotifyStartEnd→condition `.17`: UseSkillTarget/LockOnTarget, bCheckDistance=true, MinDistance1000, MaxDistance5000, FrontBaseAngle70, Front→function `.8`: **SI_Yetuga_ChargeTackle, CustomSubStateStep=Step6**, LockOnTarget, no cooltime, force cancel.

**IceBreath SB의 NextSkill은 RushGrab/CloseGrab이 아니다.** 이 저장 경로에는 BrinkGuard/Parry 결과 조건도 없다. ChargeTackle Step6 이후 별도의 native/상위 AI 선택까지 검사한 것은 아니다.

## 7. RushGrab: 두 공격 진입, 성공·실패, Social 후속

출처: [SB_Yetuga_RushGrab.json](SB_Yetuga_RushGrab.json), 관련 RushGrab AC들, [SD_Yetuga_RushGrab_Hold.json](SD_Yetuga_RushGrab_Hold.json).

기본 연결은 `Step1 Back → Step6 Back → Step7 Dash → Step5 RushGrab → None`이다. Step3 Slow는 별도 공격 진입이고 기본 종료형이다.

| 단계 | 성공/조건 연결 | 실패/기본 연결 |
|---|---|---|
| Step1 | Index1 tag `.15` StartSubState→condition `.22` LockOnTarget, bCheckDistance=true, MaxDistance1000, Fail→func `.6` Step6 | 기본 Step6 |
| Step6 | Index1 tag `.14` StartSubState→condition `.21` FrontBaseAngle40/Front, MaxDistance300, **bCheckDistance 생략**→func `.5` Step7 | 기본 Step7 |
| Step7 | Index1 tag `.12` StartSubState→condition `.20` LockOnTarget, bCheckDistance=true, MaxDistance1800→func `.4` Step3 Slow | 기본 Step5 일반 |
| Step3 Slow | Index1 HoldingSucess `.18`→func `.2` Step2 Success; Index2 HoldingSucess `.16`→HoldingStart `.7` | 기본 None: 현재 Slow AC 종료 |
| Step5 일반 | Index1 HoldingSucess `.19`→func `.3` Step2 Success; Index2 HoldingSucess `.17`→HoldingStart `.8` | 기본 None: 현재 일반 AC 종료 |
| Step2 Success | EndSubState tag `.13`→NextSkill `.9` Social, no cooltime, force cancel | 기본 Step4 End→None |

HoldingStart는 Yetuga Weapon_L에 Target Hold_Spine 부착과 FallDown 물리 설정을 저장한다. 정확한 hold 소유·해제·동시 이벤트 순서는 native 미확인이다. 일반/Slow 공격 AC는 각각 Group1 하나이며 성공 AC에는 DamageInfoIndex1/2를 가진 별도 공격 Notify가 있다. 초기 포획과 성공 후 피해를 동일한 “잡기 한 타”로 처리하지 않는다.

Step5 StartSubState tag `.11`→function `.10`은 **CloseGrab의 skill cooltime AddValue15**를 저장한다. 이것은 CloseGrab 즉시 실행 연결이 아니다. 재사용 단위·누적 방식·cooltime 적용 시점은 native 미확인이다.

SI DamageInfos[0]의 Hold SD는 `.0.Properties.AttackInfo.AttackType=HoldAttackAuto`, GuardDamageInfo.bDontGuard=true다. 첫 공격 Notify의 DamageInfoIndex는 생략돼 있으므로 index0 기본값 소비를 직접 검증하지 않은 상태를 유지한다.

## 8. CloseGrab: 기본 실패, 성공형과 벽 앞 성공형, 지속 피해

출처: [SB_Yetuga_CloseGrab.json](SB_Yetuga_CloseGrab.json), 관련 CloseGrab AC들, [SD_Yetuga_CloseGrab_Grab.json](SD_Yetuga_CloseGrab_Grab.json).

기본 연결 `Step1 Start → Step2 Fail → None`. 포획용 Start AC는 왼손/왼팔 Notify 두 개가 같은 Group1이다.

| 경로 | 정확한 export 연결 |
|---|---|
| 일반 성공 | Step1.Index1→OnAttack tag `.7`→func `.2`, StepAction=DoChangeStepAtAnimationEnd, NextStep3 |
| 포획 부착 | Step1.Index2→HoldingSucess tag `.17`→HoldingStart `.4` 및 CameraRelease `.5` |
| 벽 방향 성공형 | Step1.Index4→AnimationNotifyTick tag `.14`→WallCheck `.21`(Front:Success,bUseMainTargetLoc=false) 및 HoldingSuccess `.18`→func `.3`, DoChangeStepAtAnimationEnd, NextStep5 + CameraRelease `.6` |
| 일반 성공 마무리 | Step3 Success01→기본 Step4 Success02→None |
| 방향 변경 성공 마무리 | Step5 Success01_Turn→기본 Step4 Success02→None |

Step3/5와 Step4에는 단순 Attack Notify 대신 `xxTargetDirectAttack` 이벤트가 저장돼 있다.

- Step3.Index1 AnimationNotifyStart `.15`→function `.25`: HoldingAttachTarget, DamageInfoIndex1.
- Step3.Index3 TimerLoop `.9`: Time0.5, MaxCount5, NotifyEnable `.20`→function `.27`: HoldingAttachTarget, DamageInfoIndex3.
- Step5.Index1 `.11`→function `.23`: HoldingAttachTarget, DamageInfoIndex1. Index2 TimerLoop `.8`: Time0.5, MaxCount5, NotifyEnable `.19`→function `.26`: HoldingAttachTarget, DamageInfoIndex3.
- Step4.Index1 `.13`→function `.24`: LastSelfAttackTarget, DamageInfoIndex2.
- Step5.Index3 StartSubState `.16`→function `.22`: TargetPointTag="grab", bUseSetTargetPoint=true.

MaxCount5는 event loop 상한이며 실제 포획 지속 피해가 항상 5회라는 증거가 아니다. NotifyEnable 수명·첫 tick 시점·포획 해제·중도 취소로 실제 횟수가 달라질 수 있다.

Step1.Index3 StartSubState `.12`→function `.10`은 **RushGrab cooltime AddValue15**다. RushGrab 즉시 실행과 구분한다. 포획 SD `.0.Properties.AttackInfo.AttackType=HoldAttackAuto`, GuardDamageInfo.bDontGuard=true를 확인했다. 첫 Start Notify의 DamageInfoIndex는 생략돼 있어 기본 index 소비를 미확인으로 둔다.

## 최종 확정과 후속 검사

**원본 데이터 확정:** NormalAtk01의 5개 명시 그룹, NormalAtk02 조건부 두 번째 AC, DempseyRoll 본공격 5개 그룹과 마지막 반응창, DashAtk 대체 AC 각각 2개 그룹, Armageddon의 RushGrab Step5 연결, IceBreath의 ChargeTackle Step6 연결, 두 잡기의 성공/실패·벽 방향 분기와 상호 cooltime 추가가 저장돼 있다.

**아직 확정하지 않은 것:** 그룹당 실제 적중 이력·Reset, 생략 index 기본값, 모든 guard/parry 가능 조합, AttackSuccess/OnAttack 정의, event 배열 우선순위, StaminaOperator::Rate의 스케일, 거리 좌표 변환·FrontBaseAngle 의미, 강제 취소와 애니메이션 반응 뒤 후속 event 생존, phase 트리거·난이도·현재 패치 일치.

다음 검사는 원작 native 소비 코드 또는 버전/난이도를 고정한 전투 캡처에서 해당 event를 계측하는 것이다. 특히 NormalAtk01 마지막 두 그룹의 두 피해, Dempsey 마지막 JustGuard 뒤 CloseGrab 억제, Armageddon Start 방어와 착지 폭발 방어의 차이를 별도로 검증해야 한다. 이 보고서는 새 구현을 적용하거나 런타임 테스트를 완료한 기록이 아니다.
