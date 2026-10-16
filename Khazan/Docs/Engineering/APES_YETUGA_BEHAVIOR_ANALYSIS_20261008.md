# Apes 엘리트·Yetuga 보스 행동/공격 패턴 분석

## 2026-10-08 — 분석 결과와 범위

사용자는 구현에 앞서 원작/공개 자료를 통한 정확한 패턴 분석을 요청했다. 이번 결과는 **분석**이며 게임 Source/BP/asset/맵/AI 설정은 적용하지 않았다. 원작 cooked AI·스킬 설정, 실제 공개 전투의 표적 프레임, 공략 작성자 설명, 공식 patch를 대조했다. 원작 native 실행 코드를 확보하거나 직접 원작 runtime을 실험한 것은 아니다.

현재 4 Humanoid의 StateTree/ComboAction 구현과 Yetuga/Apes 애니메이션 라이브러리를 혼동하지 않는다. 두 대상의 신규 AI는 아직 구현하지 않았다. 기존 ARCH-79 구현·사용자 Source 변경·Main 에디터 상태는 유지했다. Art 원본/경로/시간축/공개 자료 보존은 [Art 감사](../Art/APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md)를 따른다.

핵심 차이는 **Apes의 조건별 가중 선택·피격 대응 passive**와 **Yetuga의 별도 custom 트리·거리/후방 분기·조건부 기술 연계**다. 두 몬스터를 동일한 랜덤 Attack 리스트와 Idle 복귀로 축약하면 원작의 공격 문법을 잃는다.

### 증거를 읽는 기준

- **원본 확인:** 정확한 package/export index/field/raw value가 있다. 설정 존재·참조·직렬화 연결을 확인했다는 뜻이며 native 소비 알고리즘까지 재현했다는 뜻은 아니다.
- **화면 관측:** 공개 전투 표적 프레임에서 해당 움직임을 확인했다. 피해 판정 횟수·항상 발생하는 조건·최종 시간은 별도다.
- **작성자 설명:** 영상/공략의 주장이다. 화면·원본으로 독립 확인된 부분과 나눈다.
- **해석/미확인:** 이름/구조로 예상되는 의미와 확보하지 못한 native default·수치 배율·이벤트 소비를 구분한다.

이하 `D_A`는 `BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E`, `D_Y`는 `BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga`다. 거리 값은 **원작 custom field의 raw 값**이다. cm·m/캡슐 기준·actor scale 적용을 검증하지 않은 채 단위를 바꾸지 않는다. 각도 field의 degree는 그대로 기록한다. 임의 gameplay tuning값은 이번 분석에 추가하지 않았다.

## Apes — 바위 원인 정예 / Granite Jocko

### 변형과 등장 맥락

`CB_ApesStoneHand_E`는 Standard AI, `CB_ApesStoneHand_E_Early`는 Early AI를 연결한다. 둘은 같은 `AP_ApesStoneHand_E`를 쓰지만 일반 선택군·passive가 다르다. 저장 LevelPresence의 HeinMach Early1/2/3 및 StormPass Early는 모두 **Early CB**다. 이 두 레벨에 Standard가 배치됐다는 증거는 이번 저장 자료에서 확인되지 않았다.

공개 영상의 실제 도감은 Granite Jocko다. 동일 이름의 도감 항목이 두 개 있으며 영상만으로 Early/Standard를 정확히 식별하지 못했다. 영상 제목의 Yeti를 보스 Yetuga와 같은 대상으로 해석하지 않는다. [게임 도감 02:28](https://www.youtube.com/watch?v=XkAaFFcRdBY&t=148s)

### 일반 선택군 — 정확한 원작 설정

출처: `D_A/Base_Setting/AI_ApesStoneHand_E` 또는 `..._Early`, 같은 이름 `xxAIData` export의 `Properties.CombatPreset.SkillGroup[i].Skill`. 표의 모든 행 `bUse=true`. Rate는 원시 선택 가중치며 고정 백분율이 아니다. 사용 가능 거리·각도·높이·쿨타임·상황에 따라 후보 집합이 달라지고 native 정규화는 미확인이다.

| 기술/원문 용도 | Standard Rate | Early Rate | Range Min–Max | Angle Base / Left / Right |
|---|---:|---:|---|---|
| NormalAtk01 / 후려치기 | 2 | 2 | 0–400 | 0 / 120 / 120 |
| NormalAtk02 / 내려 찍기 | 5 | 5 | 0–400 | 0 / 60 / 60 |
| TurnAtk / 휘두르기 | 1 | 1 | 0–400 | 180 / 60 / 60 |
| CounterAtk / (버스트) 양손 모아 찍기 | 10 | 일반군 없음 | 0–500 | 0 / 90 / 90 |
| DempseyRoll / 전진 주먹 연속 휘두르기 | 0 | 1 | 0–400 | 0 / 60 / 60 |
| DashAtk / 도약 주먹 찍기 | 3 | 3 | 500–2000 | 0 / 45 / 45 |
| FastBall / 강하게 돌 던지기 | 2 | 2 | 1000–3000 | 0 / 60 / 60 |
| BackMoving / 뒷걸음질 | 6 | 5 | 0–500 | 0 / 90 / 90 |
| FastMove / 빠른 추격 | 10 | 10 | 1500–4000 | 0 / 45 / 45 |
| SideMove / (장)옆걸음치기 | 3 | 3 | 0–1500 | 0 / 90 / 90 |
| TurnBackRun_Short / 짧은 선회 이동 | 2 | 1 | 0–500 | 180 / 60 / 60 |

Standard DempseyRoll의 Rate0은 **일반 추첨 가중치**다. Dodge_B·BackMoving·SideMove·FastMove의 다음 기술로 도달하는 연결도 있어 사용 불가/미사용이라고 단정하면 잘못이다. CounterAtk는 Standard 일반군의 Rate10 기술이다. 이름만으로 플레이어 공격 직후 자동 반격한다고 설명할 근거는 없다.

### 공격 패턴 — 준비/실행/후속/회복

| 기술 | 원작 실행/관측 동작 | 정확한 후속·주의점 |
|---|---|---|
| NormalAtk01 | `SB...NormalAtk01.SubStateInfos`: Step1 `_01`→Step2 `_02`→Step3 `_03`→종료. 근접 연속 휘두르기/회전 | 3 step에 attack volume 2+4+4, group `1 / 2·3 / 4·5`. 자료상 **5 attack group**이다. 같은 손·전완 group을 따로 세지 않는다. 실제 적중은 충돌·group 중복 제거에 달린다. |
| NormalAtk02 | 머리 위에서 전방 바닥 내려찍기. Step1 기본 Next=None | 조건 notify에서 instant FindTarget 원형 `Yaw360/RangeMax800`·높이 조건을 통과하면 Step2 `_02`로 바꾼다. 가까이 남았을 때 후속이 붙을 수 있으며 고정 2연타로 만들지 않는다. |
| TurnAtk | 뒤쪽 상대를 향한 휘두르기 | 일반 AI가 BaseDegree180·Range0–400으로 후보를 제한한다. 정면 기술과 동일하게 고르지 않는다. |
| CounterAtk | 양손 모아 내려찍는 버스트 | Standard 일반군 기술, SI `bEnableParringSkill=false`. 자동 counter trigger는 미확인이다. 손·전완 group1과 별도 DonutSlice volume을 단순 5타로 세지 않는다. |
| DempseyRoll | 뒤로 준비/전진 연속 공격. 선택 Composite source `0–2.6s`→`4.5–6.75s` | source 7s 전체를 재생하지 않는다. 선택 group은 `1·2 / 5`. Step2의 명시 ParryingReaction/JustGuardReaction 이벤트는 반응 애니메이션·raw stamina500 소비를 연결한다. |
| DashAtk | 도약→주먹 내려찍기→팔 매몰→회수 | 실제 영상에서 팔 매몰 중 플레이어가 공격한다. 원본 5 volume은 group1·2다. 후방 instant target max500/OffsetYaw180 조건은 TurnBackRun_Short 후속으로 간다. |
| FastBall | Start→Shoot→End, 손에서 실제 바위 투사체 생성·발사 | SI 원문/쿨타임 field20, 전투 시작 쿨타임20, parry skill false. `COI...FastBall_OBJ`가 Idle/Move/Explosion/WorldExplosion/Destruction/ParryingReaction을 가진다. 몸 몽타주만으로 투석이 완성되지 않는다. |
| Level_DashAtk_New / Dodge_A | 거리별 접근·근접 잡기·잡기 성공/실패 | Level skill과 회피 후 잡기 자료다. 기본 일반군과 같은 무작위 공격이라고 취급하지 않는다. Level 버전의 일부 event/notify 연결은 도달 trigger 미확인이다. |

공개 영상의 [00:10–00:39](https://www.youtube.com/watch?v=fjZsbwldgTw&t=10s)에서 돌진/팔 훑기, 투석, 도약·팔 매몰·회수, 단독 내려찍기, 연속 회전을 각각 확인했다. 제작자는 돌진 잡기·근접 후속·5타를 설명하지만 성공한 잡기 전체와 각 피해 판정 횟수는 이 프레임만으로 확정하지 않았다. 원본 5 group이 연속공격의 별도 근거다.

Level_DashAtk_New의 실제 배열은 Step1,3,4,5,7,8,9,10,11,12다. Step5 notify에서 raw max400→Step12 Start2_Stone, min400/max700→Step8 CloseGrab_Start, min700/max3400→Step7 Run_Loop. 잡기 접촉/성공은 target attach·ragdoll·별도 성공 단계와 직접 피해 timer를 연결한다. 그러나 Step1/3의 Idle에는 matching skill notify가 없고 Step4 tag field도 생략돼, runtime/native 없이 항상 도달하는 선택 순서로 확정하지 않는다.

### 이동 중 다음 행동을 정하는 분기

- **BackMoving:** 첫 단계 instant target max700이면 DempseyRoll. 다른 단계 min700/max1500이면 DashAtk. 뒤쪽 벽 검사도 별도 step을 고른다.
- **FastMove:** notify tick에서 가까운 target max400을 검사하고 DempseyRoll/SideMove 원시 RandomRate `.5/1.0`의 후속 선택을 가진다. native 확인 전 1/3·2/3 고정 확률로 환산하지 않는다.
- **SideMove:** 시작 시 상대 각도를 검사해 좌/우 step을 고른다. max600이면 DempseyRoll 연결. 벽 검사로 추가 이동 단계가 있다. 오른쪽 step의 WallCheck 원문도 `Directions.Left=Fail`이므로 이름만 보고 임의로 수정하지 않는다.
- **TurnBackRun_Short:** 뒤쪽 벽 검사로 step 변경, 이후 max1500 target 검사 실패에서 Social 연결이 있다.

따라서 이동은 공격 선택 사이의 단순 Idle filler가 아니다. 뒤로 물러나며 다음 공격 거리를 확보하고, 횡이동·빠른 접근 끝에서 공격으로 넘어가는 실행 경로가 있다.

### 피격 대응 — Early와 Standard의 중요한 차이

Standard `SB_ApesStoneHand_E_DodgeSkill_E`는 SelfStatus `HP/LessThan/bUseRatio=true/RatioValue=.9`, 피해 기록 `CheckTimeTerm6/TotalDamageRateMax.13`, battle-state 제외·상대 공격/무기별 range 조건을 가진다. 대응 UseSkill은 **Dodge_B**이며 이 실행의 EndSubState에서 **DempseyRoll**로 연결한다. `.13`의 집계/비교 소비는 native 미확인이라 “6초간13% 피해를 받으면 무조건”으로 바꾸지 않는다.

Early `SB...DodgeSkill_Early`는 세 passive 모두 **SideMove**를 호출한다. raw Count/Random 조건은 `(4초,5)/.5`, `(4초,6)/.7`, `(5초,7)/1.0`다. hit count 경계 비교·집계·독립 추첨 여부는 미확인이다. 최소한 **연속 공격을 받았을 때 횡이동을 사용하는 대응 자료**는 실제로 존재한다. 모든 입력을 읽어 회피한다고 설명하지 않는다.

### 대기/발견/고갈/등 파괴

AP의 Idle은 실제로 공용 Yetuga Stand_F를 연결하며 현행 이름은 `Locomotion_Stand_F_Original_Variant02`다. 미발견 대기, Level 특별 개시 기술, 발견 후 포효, 일반 전투 선택은 구분한다.

| 배치/자료 | 원본에서 확인한 연결 | 미확인 |
|---|---|---|
| AI 공통 CombatPreset | StartSkillInfo→Roar, WaitTime1, 이동 선택군의 Run/Walk/LockOn 별도 설정 | 시야/이벤트 감지→전투 진입의 native 전체 알고리즘 |
| HeinMach Early1 | SpawnStartSkillInfo→DashAtk_LevelSkill | Level skill의 일부 이벤트 trigger |
| HeinMach Early3 | BattleStartSkillInfo→DashAtk_StartSkill; Basic_Loop_01→Basic_End_01 | 저장 값 외 최종 runtime override |
| StormPass Early | BattleStartSkillInfo→DashAtk_StartSkill; Basic_Loop_02→Basic_End_02 | 최종 runtime override |
| HeinMach Early2 | PeaceTasks Patrol/Skill/Patrol/Skill 참조 | nested level export498–501의 세부 모션/시간 |

피로 AP는 GroggyStr Start/Loop/End, 회복 기술 SI 원문은 `괴력 충전 포효`다. StartSubState의 Stamina RateSet10000, notify의 ConsumePerSecond-580, CustomSkillStaminaAttackPowerRate-10000은 **원시 값**이며 native 스케일 확인 전 100%/5.8%로 번역하지 않는다. 위키의 Non-Replenishing 표기는 자연 회복이 없다는 주장이지 명시 회복 기술도 없다는 증거가 아니다.

PartGroggy는 별도 PartDestructionGroggy와 HP raw Rate-1000/injury spell을 연결한다. 공개 training 영상에서 강한 타격 뒤 상체 반응·훈련 완료를 확인했지만 곧바로 처치돼 살아 있는 full 기상 루틴은 미관측이다. 등을 대고 넘어지는 처치 조건·등 파괴 설명은 [도감 공략](https://steamcommunity.com/sharedfiles/filedetails/?id=3452706584)과 영상 작성자 서술도 별도 보존했다. Yetuga의 뒤로 눕는 **공격**을 Apes의 등 파괴 **반응**과 혼동하지 않는다.

## Yetuga — 예투가 보스

### 행동 선택 구조

`D_Y/Base_Setting/AI_Yetuga.Properties.SetupType=Custom`, CombatTrigger→`BT_Yetuga`. 원본은 **native custom `xxNBehaviorTree`**이며 stock UE `UBehaviorTree`로 구현됐다고 표현하지 않는다. asset export를 제외한 노드121개, CanUseSkill condition40개를 해석했다.

root Selector export2의 Children은 `[37,56]`다. 37에서 Armageddon 가능 조건을 검사하고 false 경로는 근거리/중거리/그 밖 및 후방 각도로 분기한다. 56은 별도 fallback 경로다. serialized Children/TrueChild/FalseChild의 연결과 순서는 확인했다. Selector 이름에서 예상되는 우선 선택 구조와 native의 재평가·실행 중 abort·success/failure 반환 방식은 구분한다.

| 분기 | 정확한 원본 위치 | 조건 |
|---|---|---|
| Armageddon 상위 검사 | BT export37 | range max5000, HP raw<=65, stamina raw>=20, 둘 다 bCompareRate=false |
| 첫 거리 분기 | export58 | Min0/Max800 |
| 다음 거리 분기 | export55 | Min799/Max2500; 799/800 겹침은 원문 유지 |
| 후방 검사 | export13/12 | BaseDegree180, Left70, Right70 |
| rear JumpBackPress | export81 | range max600, rear180±45, Group1 destruction step<=ParticalDestruction |
| rear TurnAtk | export121 | range max400, rear180±120 |

정면 가까운 false-chain의 주요 기술 순서는 **Armageddon→IceBreath→CounterAtk→NormalAtk01→DashAtk→DempseyRoll→RushGrab→NormalAtk02→TurnAtk→이동/회피**다. 실제 후보가 되는지는 각 조건·기력·SI input·쿨타임에 달린다. 중거리 정면에서는 **Armageddon→IceBreath→RushGrab→ChargeTackle→DashAtk→FastBall→DempseyRoll→Social/이동**의 구조가 나온다. 랜덤 Selector도 존재하지만 모든 공격을 동일 확률로 고르는 단일 random 목록은 아니다.

fallback에는 target max700 조건에서 `MoveToTarget(AcceptanceRadius400,MoveLimitTime3)`→`NormalAtk02_NoCoolTime` sequence가 있다. 접근 완료 후 공격 실행을 묶는 자료다. LockOnMove의 좌/우/뒤 원시 Rate는2/2/1, MoveTime1.67이 반복된다. 이동 제한시간이 추격 지연시간이나 액션 종료 시간과 동일하다고 해석하지 않는다.

AI RecognitionValue의 SightRange6500/SightYaw360, time 기반 target-update `TImeSeconds6`, Random target select, BattleRange20000도 원본 field다. 보스 LevelPresence는 spawnAtBeginPlay=false인 SA/CB 참조만 확인돼 **아레나/시네마틱의 정확한 최초 호출 순서는 미확인**이다. Roar의 `인트로 포효`, ChargeTackle_Intro의 `인트로 돌진 달리기`는 존재하지만 이름만으로 둘의 실행 순서를 확정하지 않는다.

### 공격 종류와 후속

| 기술 | 동작 문법 | 원본에서 확인한 분기/주의점 |
|---|---|---|
| NormalAtk02 | 내려찍기→올려치기 | Step1 기본 종료. target max800 조건을 통과하면 Step2 후속. 항상 두 동작을 끝내는 규칙이 아니다. |
| NormalAtk01 | 손바닥 연속 휘두르기→회전 마무리→회복 | SI 원문 `1_손바닥4연타`, 3 step, **5 명시 attack group**. 4동작과5group을 구분한다. 마지막 Composite에 group4/5가 별도로 있다. |
| TurnAtk | 짧은 휘두르기 | 후방/각도·거리 선택 경로와 정면 경로가 모두 있다. 공개 단발 횡타 전부가 이 기술이라고 화면만으로 확정하지 않는다. |
| CounterAtk | 양손 높이 올려 지면 내려찍기 | SI 원문 `양손 모아 찍기`, 근접 candidate. 이름만으로 자동 counter가 아니다. |
| DempseyRoll | 뒤로/옆으로 준비→전진 연속 주먹 | 본공격 group1–5. 준비 횡이동에도 별도 group이 있어 전 step의 group수를 무조건 합치지 않는다. 명시 직전가드/패리 반응 경로가 있다. |
| DashAtk | 뒤로 준비→도약→주먹 매몰→팔 회수/후속 | 공략과 프레임에서 팔을 뺄 때 피격도 관측. 매몰 중 틈과 회수 타격을 구분한다. |
| JumpBackPress | 등으로 뒤쪽 내려앉기→기상 | 등뒤 상대에 대한 전용 선택이며 Group1 부위 상태 조건도 있다. 기상 정면 타격을 공개 클립에서 확인했다. |
| ChargeTackle | Start→Run→RunLoop→RunEnd→End | Stun→StunEnd 대체 단계가 있다. 벽 충돌 경직은 여러 공략 서술이며 이번 clip에서 직접 독립 관측한 것은 아니다. |
| FastBall | 준비→투척→End | 손/돌 projectile의 실행이 분리된다. SI EndCooltime20/BattleStartCooltime30. |
| IceBreath | 뒤로 이동→뒤로 도약→Breath01→Breath02→End | 전방 훑기·얼음 형성·지면 타격/파쇄를 영상에서 확인. 조건부 **ChargeTackle Step6** 연계; Grab 고정 후속이 아니다. |
| Armageddon | 얼음 준비→도약 시작→일반/근접 착지→End | 거리/각도/AttackSuccess 이벤트로 대체 step을 고른다. Step6에서 **RushGrab Step5**로 이어지는 경로가 있다. |
| RushGrab | 뒤로 준비→접근→양팔 펼쳐 몸 던지기 | 접촉 성공/빗나감/End 단계가 별도다. miss 시 느린 실패·구르기 이탈을 공개 clip에서 확인했다. |
| CloseGrab | 근접 왼팔 발광→붙잡기→성공 이동/내던짐 또는 실패 | RushGrab과 다른 기술이다. 성공01/회전성공01/성공02/Fail 분기가 있다. |

[Inven 데모 시기 자료](https://www.inven.co.kr/board/party/6187/21)와 [DCinside 발매 후 원본 클립](https://gall.dcinside.com/mgallery/board/view/?id=berserkerkhazan&no=19069)을 대조했다. 공개 분류의 기본4동작은 오른손 시작, 강화5동작은 왼손 시작이다. NoobFeed의 강화 오른손 시작 설명은 이 자료와 충돌한다. 팔 방향은 몬스터 자신의 좌/우 기준이다.

### 후속을 고정하면 틀리는 지점

**Armageddon→잡기:** 대형 얼음 공격 후 RushGrab을 수행하는 clip을 확인했다. 원본 Step6→RushGrab Step5 연결도 있다. 그러나 Step6 진입은 `AttackSuccess`·정면 조건을 사용하는 경로다. 이것을 “패링을 실패하면 무조건 잡기”, “얼음 공격 뒤 항상 잡기”, “CloseGrab”으로 바꾸지 않는다. native AttackSuccess가 어떤 성공 결과를 집계하는지는 미확인이다.

**IceBreath→돌진:** 거리1000–5000·FrontBaseAngle70 조건의 ChargeTackle Step6 연계가 있다. 공략에서 자주 연속으로 보이는 기술과 원본에서 직접 연결된 후속을 나눠야 한다.

**DempseyRoll→직가 반응:** Step2의 `Results=[ParryingReaction,JustGuardReaction]` 이벤트→`AC_Yetuga_JustGuardReaction`+stamina raw500 소비가 연결된다. 이 reaction Composite의 EnableCancelSK에는 `AnimSkillCancelMode=ChangeNextSkill`, `ComboSkillInfo=SI_Yetuga_Groggy`가 있다. 마지막 방어 뒤 움찔하는 공개 모습과 별도 원본 반응 경로가 있으나, 모든 이전 타격 직가가 필수인지·event 허용 window·자동 취소 우선순위는 native 확인이 필요하다.

Grab SI의 `bEnableParringSkill=false`는 원본 확인이다. 일반 guard/회피/무적 전체 결과는 해당 skill flag 하나만으로 확정하지 않는다. 각 SD/attack volume의 방어 소비를 함께 확인해야 한다.

### 페이즈 설명을 단정하지 않는 이유

원본 BT의 special 사용 조건은 다음과 같다. bCompareRate가 false로 명시돼 있는 raw Value를 퍼센트로 표현하지 않는다.

| 기술 | BT status 조건 | 거리 조건 | SI cooldown |
|---|---|---|---|
| Armageddon | HP raw<=65, Stamina raw>=20 | max5000 | EndCooltime240 |
| IceBreath | HP raw<=60, Stamina raw>=30 | max3000 | EndCooltime90 |
| DempseyRoll | HP raw<=50 | 분기별600–1500 또는max600, 정면±65 | EndCooltime25/BattleStartCooltime10 |

출처: `BT_Yetuga`의 해당 CanUseSkill exports와 개별 `SI`. Armageddon SI에는 별도 stamina input `RatioValue=.5/Value1`이 있으나 bUseRatio는 생략돼 default 소비를 확정하지 않는다. RushGrab/CloseGrab에는 HP ratio input이 있으나 RatioValue 자체가 생략돼 원본 cutoff를 숫자로 채울 수 없다.

[Prima의 2025-01-21 데모 공략](https://primagames.com/tips/the-first-berserker-khazan-how-to-beat-yetuga-boss)은 HP40–50%, Inven은 약50%, [NoobFeed의 2025-03-30 공략](https://www.noobfeed.com/articles/the-first-berserker-khazan-guide-how-to-beat-yetuga-first-boss)은 첫 Brutal 이후 관측을 설명한다. 이들은 **동일 트리거의 원본 증명**이 아니다. 원본 구조는 기술별 개방 조건을 가지므로 단일 Phase2 bool로 모든 강화 공격을 한 번에 여는 재현은 아직 정당화되지 않는다.

대형 얼음 공격을 “회피 불가, 패링만”으로 쓰는 공략도 있으나 [Escapist](https://www.escapistmagazine.com/the-first-berserker-khazan-how-to-beat-the-yetuga/)·Inven·Prima의 회피 설명과 충돌한다. 브레스/얼음 생성/마지막 파쇄의 방어 flag도 각 구간별 확인 없이 동일하게 묶지 않는다.

### 네 종류의 틈/경직을 구분

| 구분 | 원본/화면 근거 | 의미 |
|---|---|---|
| 공격 회수/회복 | NormalAtk01 종료 자세, Dash 팔 매몰·회수, Grab 실패 | 해당 실행의 빈틈. 기력 고갈8초를 여기 넣지 않는다. |
| 직가/패리 reaction Groggy | Dempsey reaction→SI_Groggy | 방어 결과에 따른 별도 반응 경로. |
| 등 부위 파괴 | CS Group1→SI_PartGroggy, CB Back/Back1/Back3 weakpoint box | 뒤쪽 파괴 그룹과 반응. 일반 exhaustion과 구분한다. |
| 스태미나 고갈 | AP Index1 Start/Loop/End, CS exhaustion term8, 공식 patch | 자원 고갈 상태의 별도 수명이다. |

공식 [2025-06-26 패치](https://steamcommunity.com/games/2680010/announcements/detail/543361383085900259)는 Yetuga exhaustion을 **5초→8초**로 바꿨다(Steam518753/PS5 01.013.021/Xbox1.1.13.21). 이번 저장 원본 CS도 고갈 term8을 가진다. archive의 공개 patch/build 식별이 끝난 것은 아니지만 두 독립 자료의8초는 일치한다.

일반 StaminaRecover SI의 AfterTime6.4는 입력 조건의 시간 field다. 이것을 고갈 전체 길이로 바꾸거나 8−6.4를 최종 회복 animation 길이로 임의 계산하지 않는다. 부위 파괴 전용 PartGroggy_StaminaRecover는 AfterTime 없이 별도 즉시 status 변화/포효를 가진다. 일반 고갈 종료·부위 파괴 종료·Brutal 피해자 반응이 동일 회복 알고리즘이라는 증거는 없다.

## 자료 보존·검증·정확한 다음 절차

재사용 자료 root는 `Metadata/EnemyBehaviorResearch_20261008`다. ApesOriginalAnalysis/Evidence/ResolvedBranches와 YetugaOriginal의 raw SHA 인덱스·AIContractSummary·SkillStepsBranches·SkillAvailability·표적 Skill/Defense 보고서, PublicApes/PublicYetuga의 원본·프레임·manifest·출처표를 먼저 읽는다. current library212행은 `CurrentApesYetugaLibrary.csv`로 연결한다.

이번 실제 검증은 원본 package SHA·export 참조·저장 source/현재 mapping·공개 evidence file/hash·보고서 JSON/링크의 정적 검증이다. C++ build/PIE·원작 통제 실험·모든 난이도/최신 patch 일치 검증은 이번 분석에 포함하지 않았다.

남은 표적은 다음이다.

1. custom AI의 reevaluation/interrupt·CanUseSkill 실패/cooldown 소비·Rate 정규화·거리 기준/단위를 native 계약이나 통제 실험으로 확인한다.
2. HP raw65/60/50·SI ratio default·fixed-point stamina 연산을 확정한다. 자료 없이 공개 공략의50%를 대신 넣지 않는다.
3. 각 attack group의 reset/dedup 수명, AttackSuccess의 정확한 결과, Grab 성공/실패와 일반 guard/BrinkGuard/Parry flag를 확인한다.
4. HeinMach Early2 nested PeaceTasks level exports498–501과 Yetuga 아레나 최초 개시 trigger만 표적 조회한다. 이미 저장된 animation/library 전체 조사를 반복하지 않는다.
5. 추가 전투는 버전·난이도·HP/기력·거리·뒤/앞·방어 결과를 고정한다. 추격/콤보 연계/자원 고갈/등 파괴/Brutal을 각각 검사한다.
6. 직접 구현 요청이 들어오면 기존 StateTree/Definition/ComboAction/몽타주 구조에서 표현할 수 있는 범위를 먼저 검토한다. 이번 연구를 근거 없이 새 범용 manager나 중복 상태 구조를 만드는 허가로 해석하지 않는다.

## 2026-10-08 — 스킬 연계·방어 구간 표적 확인 보완

앞선 개요의 추가 표적 분석을 완료했다. 정확한 참조/원시 시간/생략값은 `YetugaOriginal/YetugaOriginalSkillAnalysis.md` 및 JSON에 보존한다. SB8개와 연결 원본75개의 SHA 및 export index/ObjectName 일치를 검사했다.

1. **NormalAtk01 종료 뒤에도 다음 동작을 고른다.** Step3 Index1은 rear/벽/Random 조건의 TurnBackRun_Short, Index2/3은 좌/우 벽 및 target 조건의 SideMove Step5/6이다. Index4는 `SelfStatus export13.CheckDynamicStatus={HealthPoint,LessThanOrEqualTo,bUseRatio=true,RatioValue=.7}` 및 `TargetCondition export15={LockOnTarget,bCheckDistance=true,MaxDistance300}`를 연결해 RushGrab을 예약한다. 여기의 `.7`은 비율 사용이 명시된 조건으로 BT의 bCompareRate=false/raw65와 다르다. 여러 조건의 native 결합/후속 중단·우선순위는 별도 미확인이다.
2. **DempseyRoll→CloseGrab 후속도 있다.** Step2 Index1의 AnimationNotifyStart→LockOnTarget 거리 max500/정면 조건→CloseGrab(쿨타임 무시/force cancel). 별도 Index2는 마지막 공격 구간의 ParryingReaction/JustGuardReaction→reaction 애니메이션·raw500 소비다. 명시적인 “패링 실패” 조건은 없으므로 반응 뒤 후속 event 생존 여부를 검증해야 한다.
3. Dempsey 마지막 반응창은 AC export80 `LinkValue5.1676207/Duration.30028677`이며 group5 대표 손 창 `5.1746855`와 겹친다. CloseGrab 예약창은 export81 `6.51835/.23164988`다. 둘은 **원본 AC 시간축**이지 live 재생 시간은 아니다. 이 자료로 마지막 구간 gating을 확인했지만 “앞선 네 타 모두 직가 필수”를 증명하지 않았다.
4. **Armageddon의 원거리/근접 착지 분기는 서로 다르다.** Step3 AttackSuccess+정면 조건→Step6, Step4 OnAttack→Step6. Step6 target max1500/정면 조건→RushGrab Step5. 일반 default는 Step5 End다. 근접 착지를 선택하는 target 검색 max2000도 존재한다. AttackSuccess/OnAttack 결과 정의를 확보하지 않아 hit/guard/BrinkGuard/Parry를 임의 매핑하지 않는다.
5. **대형 착지 폭발의 직전가드 금지 field가 있다.** `D_Y/Skill/13_Armageddon/SD_Yetuga_Proto_Armageddon_02` export0 `Properties.AttackInfo.GuardDamageInfo.bDontJustGuard=true`. SI DamageInfos[1] 및 착지 Notify DamageInfoIndex1을 따라 확인했다. Start의 별도 StaminaBreak SD와 구분한다. 일반 guard/Parry 및 회피 결과까지 이 bool 하나로 확정하지 않는다. 공개 공략의 “패링”을 원작 `JustGuardReaction`과 같은 의미로 번역하면 오류가 생길 수 있다.
6. **잡기 성공과 실패/방향이 분리된다.** RushGrab 일반/Slow HoldingSuccess→성공 단계; 성공 EndSubState→Social 후속. CloseGrab 기본 Start→Fail, OnAttack 성공→Success01, 벽+holding 조건→Success01_Turn, 두 성공형 모두 Success02로 이어진다. 두 잡기는 상대 기술의 cooltime AddValue15를 가진다. 이는 즉시 상대 잡기를 실행하는 연계가 아니다.
7. RushGrab Hold 및 CloseGrab Grab SD는 `AttackType=HoldAttackAuto/GuardDamageInfo.bDontGuard=true`다. 초기 capture Notify DamageInfoIndex 생략의 default 소비는 미확인이다. 성공 중 `.5/MaxCount5` timer는 반복 상한이며 실제 고정5회 피해가 아니다.
8. NormalAtk01의 SD 이름과 hitbox BoneName이 항상 일치하지 않는다(AC02 group3 SD_R_02지만 L-Hand/L-Forearm). SD 이름만으로 팔 순서를 고정하지 않는다. Dempsey의 본공격 손 volume은 L/R/L/R/L로 직접 확인했다. BoneName은 공격 volume 부착 bone이며 시각 모션 판정과도 구분한다.

위 보완으로 기본 연속공격 종료→이동/잡기, 강화 연타 종료→직가 reaction 또는 근접 잡기, 얼음 공격→조건부 돌진 잡기, 브레스→조건부 돌진 달리기를 서로 다른 경로로 구분했다. 실제 재현 구현/원작 통제 실험은 이번에 수행하지 않았다.

## 2026-10-08 — 방어/회복 최종 확인과 증거 검증

`Metadata/EnemyBehaviorResearch_20261008/YetugaOriginalDefenseRecovery.md/.json`에 표적40package/154export·원본 SHA를 보존했다. 고갈8의 정확 출처는 `D_Y/Base_Setting/CS_Yetuga`, export0 `CS_Yetuga`, `Properties.StaminaStatus[0].Key=Battle`의 `Value.StaminaExhaustionInfo.StaminaExhaustionTerm=8.0`이다. JSON SHA는 `0a597b5598466b7644b9475be6fec2a9ea528b90c2ffc977ff7ff47740fded72`. 같은 설정의 종료 회복은 Operator=Add/RecoveryStamina0이다. **고갈 상태 시간 field와 실제 Brutal 입력/처형 기회 창을 동일하다고 단정하지 않는다.** native timer 시작·멈춤·override는 미확인이다.

AP의 stamina 고갈 Index1은 New Composite를 통해 **GroggyStand_F** Start/Loop/End를 쓴다. 직가 전용 Groggy는 **GroggyStr_F**다. 두 포즈와 등 PartGroggy를 한 그로기 animation으로 통합하지 않는다. PartGroggy 후 전용 StaminaRecover SI는 등록돼 있지만, 그로기 종료에서 이 SI를 자동 호출하는 경로는 저장 범위에서 미확인이다. 일반 회복의 SB 시작 연산은 Stamina Rate/99999, 전용 SI 즉시 연산은 Rate/100000이며 분모·회복 시점은 native 미확인이다.

최종 cache 검증에서 `AC_Yetuga_DamageParry_F`가 Moving/Reaction과 Skill/13_Armageddon에 **서로 다른 SHA로 존재**함을 발견했다. 이름만으로 flat cache를 조회하던 위험을 고쳐 두 원본을 `YetugaOriginal/PackageCopies/<package suffix>.json`으로 분리하고 Index.local_path로 연결했다. 기존 flat 사본과 실패 기록은 보존한다. raw 원본 ZIP 및 게임 asset은 변경하지 않았다. Skill 조사 resolve도 full package→local_path를 사용해 재검증했고75개SHA/참조가 일치했다.

`ResearchVerification.json`은 Yetuga237개 정확사본SHA, Apes선택59개hash, Yetuga공개27clip, Apes공개20manifest항목, 현행212개asset존재·source mapping, JSON parsing 및 도메인문서 연결을 검사한다. 최초 filename 충돌 실패는 `ResearchVerificationFailure_NameCollision.json`에 남겼다. 추가 재현 작업은 먼저 이 보고서와 표적MD를 읽고 부족한 native/Level 조건만 확보한다. 게임 Source/BP/assets 변경, build, PIE는 이번 패턴 연구에서0회다.


## 2026-10-12T19:50:49.391255+09:00 — 원본 경로의 StateTree 구체화 Main 완료

ARCH-94로 Yetuga 원본121노드의 source property/49gate/46skill/10MoveTo/5LockOnMove·성공/실패 후속을 `ST_Yetuga_Original`173상태로 옮겼다. Apes는 `ST_Apes_Original`9상태와 기존 Early 후보, actual damage passive3행을 사용한다. original24+alias4/Apes19의 실제47기술, actual Sight→Roar→combat, deterministic7피격 SideMove 및 compiled 원시 field/정확 class·entry/후속은 최신 MainFinalQA04에서 성공했다. 과거 공통 Chase/평탄화 후보만으로 대체되던 Yetuga 전용 순서·NoCool·selected substep의 구조 제한은 이 구체화 범위에서 대체된다.

정확한 전달 SHA/빌드/module/검사와 수치 출처는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. native RNG·abort·생략 CDO·Group1 producer·selected float/이동 물리 전체 동일성은 미확인이다. Apes 임계 >=/history reset/독립 chance draw는 원작 직접 검증값이 아닌 프로젝트 어댑터다. 모든 실제 UE 기술 실행 성공과 원작 native 전체 동등성을 구분한다. 후속은 저장 plan/report 및 exact package에서 부족한 근거만 확보한다.

<!-- BeastDodge_20261012_MainCompleted -->
