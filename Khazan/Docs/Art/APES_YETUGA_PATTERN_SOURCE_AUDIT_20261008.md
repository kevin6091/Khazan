# Apes·Yetuga 패턴 원본/공개 자료 감사

## 2026-10-08 — 조사 범위와 실제 상태

사용자 요청은 공격·행동 패턴 분석이다. 게임 C++/BP/애니메이션/맵/옵션은 이번에 수정하지 않았다. 에디터 조작·build·PIE·원작 실행도 수행하지 않았다. 저장된 원작 cooked JSON, 공개 전투 프레임, 작성자 설명, 공식 패치를 분리해 분석했다. 동작·조건 해석은 [Engineering 분석](../Engineering/APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md)을 따른다.

2026-10-07 정리된 현행 라이브러리는 Yetuga 120, ApesStoneHandElite 92 시퀀스다. 이는 AI 구현 완료를 뜻하지 않는다. 현재 이름은 `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv`에서 조회하며 옛 `Playback/A_EN_PLAY_*` 경로를 그대로 사용하지 않는다. Root Motion 옵션은 기존 정리 결과를 유지했다. 이번 분석으로 재임포트·재생률 보정·root repair를 실행하지 않는다.

### 정확한 대상

| 대상 | 원작 식별자 | 근거·한계 |
|---|---|---|
| Yetuga | `Design/Monster/Boss/01_Yetuga`, `SA_Yetuga`, TIDX 283005 | Boss Yetuga다. `SA.Version`은 직렬화 field이며 공개 패치 버전으로 해석하지 않는다. |
| Apes Standard | `Design/Monster/Apes/ApesStoneHand_E`, `SA_ApesStoneHand_E.ActorName=바위 원인_정예`, TIDX 282004 | `CB_ApesStoneHand_E→AI_ApesStoneHand_E`의 실제 연결을 확인했다. |
| Apes Early | `SA_ApesStoneHand_E_Early.ActorName=원인_바위_정예_Early`, TIDX 282009 | `CB_ApesStoneHand_E_Early→AI_ApesStoneHand_E_Early`. 저장 LevelPresence는 HeinMach 3곳·StormPass 1곳에서 이 변형을 확인한다. |
| 공개 영상 Apes | 게임 도감의 `Granite Jocko` | 실제 도감 프레임으로 확인했다. 이름만으로 Early/Standard 중 어느 변형인지 확정하지 않는다. 일반 Wild Jocko·Yetuga·Netherworld Jocko와 구분한다. |

### 원본 보존 자료와 조회 순서

| 범위 | 원본 자료 | 이번 재사용 인덱스 |
|---|---|---|
| Yetuga | `Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/{SourceMetadata.zip,SourceMetadataIndex.json,SourceClosure.json,LevelPresence.json,AnimationLibrary.csv,PlaybackEventTimes.json}` | `Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/Index.json`, `BehaviorTreeResolved.txt`, `AIContractSummary.json`, `SkillStepsBranches.json`, `SkillAvailability.json` |
| Apes | `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/`의 같은 원본 묶음 | `ApesOriginalAnalysis.md`, `ApesOriginalEvidence.json`, `ApesOriginalResolvedBranches.json` |
| 현행 이름 | `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv` | `Metadata/EnemyBehaviorResearch_20261008/CurrentApesYetugaLibrary.csv` |

원작 package 접두사는 `BBQ/Content/_Kazan_/`다. `ObjectPath` 마지막 숫자는 해당 package JSON export 배열의 인덱스다. 같은 subobject 이름이 여러 개 있으므로 이름만으로 참조를 연결하지 않는다. Yetuga design package 237개를 원본 index SHA-256과 대조해 분석 사본으로 보존했다. Apes의 선택 design 59개와 추가 표적 animation/projectile 자료 역시 원본 hash를 확인했다. 원본 ZIP은 변경하지 않았다.

### 공격을 식별할 때의 규칙

- `SI`의 `SkillName/SkillStatePtr/InputConditions/cooldown`은 기술의 식별·사용 조건이다. `SB`의 `SubStateInfos/NextSubStateStep/SkillEventMap`은 실제 단계·조건부 후속이다. Composite와 Sequence 이름만 보고 순서를 고정하지 않는다.
- `AP.SpecialDamageAnimList.Grapple*→DamageGrapple_Atk*`는 붙잡힌 **피해자 반응**이다. 이름에 `Atk`가 있어도 공격 후보로 일괄 추가하지 않는다. Prop의 돌/얼음 애니메이션도 몬스터 몸의 공격 포즈와 구분한다.
- 애니메이션 동작 수, SB step 수, attack notify volume 수, attack group 수, 실제 유효 적중수는 각각 다르다. Apes NormalAtk01은 3 step, volume `2+4+4`, group `1 / 2·3 / 4·5`다. 같은 group에 손·전완 volume이 함께 붙어 있어 10타라고 설명하면 잘못이다.
- `CounterAtk`라는 이름만으로 자동 반격을 단정하지 않는다. Apes SI 원문은 `(버스트) 양손 모아 찍기`이며 Standard 일반 선택군에도 있다. 자동 반격 trigger는 별도 증거가 필요하다.
- class/asset 존재, CB 기본 보유, AI 일반 선택, passive/연계 선택, Level 스크립트 연결, 실제 영상 관측을 구분한다. 예컨대 Standard DempseyRoll의 일반 Rate는 0이지만 다른 동작의 다음 기술로 도달할 수 있다.

### 시간축·재생속도

원작 source notify `LinkValue`, Composite segment의 원본 구간, 저장된 `DilationSequenceLength`, 현재 baked 시퀀스 시간은 같은 값이 아닐 수 있다. 기존 `PlaybackEventTimes.json` 및 이번 resolved report의 source/playback 병기 결과를 먼저 사용한다. SB `AnimPlayRate=1`만 보고 source 실시간과 같다고 단정하지 않는다. live attack-speed·actor dilation·hit stop의 최종 시간은 이번 자료로 검증하지 않았다.

표적 예: Apes NormalAtk01_03 source 6.733333s→saved dilation 5.847048s; NormalAtk02 후속 조건 raw LinkValue 2.416413s→saved playback 2.2181253015s. DempseyRoll은 source 7s 전체가 아니라 선택 Composite의 `0–2.6s` 및 `4.5–6.75s` 구간을 잇는다. 위 값은 원작 저장 field/기존 bake 계산이며 임의 튜닝값이나 최종 live 측정값이 아니다. step play rate와 이미 baked dilation을 중복 적용하지 않는다.

### 공개 자료와 실제 관측

| 자료 | 날짜/조건 | 실제 확인 범위 |
|---|---|---|
| [Nirr Inven Yetuga](https://www.inven.co.kr/board/party/6187/21) | 2025-01-17, 데모 시기 | 작성자 전투 WebP 11개 표적 프레임 및 원문 |
| [DCinside Yetuga 패턴 정리](https://gall.dcinside.com/mgallery/board/view/?id=berserkerkhazan&no=19069) | 2025-04-14, 정식 발매 후; 난이도/build 미표기 | 원본 WebP 16개 표적 프레임 및 원문 |
| [TurboAchiever Granite Jocko 전투](https://www.youtube.com/watch?v=fjZsbwldgTw) | 2025-03-28 | 원본 110초 영상 확보, 전체 2초 간격/주요 구간 0.5초 간격 프레임 검사; 설명과 관측 분리 |
| [Granite Jocko Training Challenge](https://www.youtube.com/watch?v=XkAaFFcRdBY) | 2025-04-04 | 원본 시각 검증, 02:12–02:14 반응·02:14.4 훈련 완료·02:28 도감 |
| [공식 June 26 패치](https://steamcommunity.com/games/2680010/announcements/detail/543361383085900259) | 2025-06-26; Steam 518753/PS5 01.013.021/Xbox 1.1.13.21 | Steam 공개 News API 원문: Yetuga exhaustion 5→8초 |

원본 WebP 27개·접촉시트·출처/시간/hash manifest와 공식 API 원문은 `Metadata/EnemyBehaviorResearch_20261008/PublicYetuga`에 저장했다. Apes 영상·검증된 프레임·manifest는 같은 root의 `PublicApes`다. 클립 상대 시각은 원작 공격 시작 기준 timer가 아니다. 전체 전투를 연속 재생하거나 모든 프레임의 실제 피해 판정을 분석했다고 기록하지 않는다.

공개 공략의 페이즈 HP 약 절반/40–50%/첫 Brutal 이후 설명은 서로 일치하는 trigger를 증명하지 않는다. Yetuga BT의 HP raw 65/60/50에는 `bCompareRate=false`가 저장돼 있어 곧바로 65%/60%/50%로 바꾸지 않는다. source game patch 식별·custom 소비 코드·입력 조건의 생략된 default가 확보되기 전에는 미확인으로 보존한다.

### 남은 표적 확인과 재개 절차

1. Engineering 분석과 위 저장 report를 먼저 읽는다. 기존 원본 ZIP 전체 추출/애니메이션 재작성을 반복하지 않는다.
2. 부족한 사항은 package→export index→field로 표적 조회한다. Apes HeinMach Early2 PeaceTasks는 level exports 498–501의 nested property가 필요하다.
3. native의 Rate 정규화·고유 status 배율·attack group reset·trace/각도/거리 소비·중단 우선순위·종료 trigger는 raw property와 별도로 확인한다.
4. 추가 영상은 게임 버전·난이도·HP/기력·상대 위치·직전가드 결과를 고정해 검사한다. 이번 클립의 한 사례를 무조건 연계나 고정 회복 시간으로 일반화하지 않는다.
5. 별도 구현 요청이 있기 전에는 Source/BP/asset 수정·Main 적용을 수행하지 않는다. 분석 완료와 원작 runtime 일치 검증 완료는 구분한다.

## 2026-10-08 — Yetuga 원본 스킬/공격 그룹 추가 교차검증

`YetugaOriginal/YetugaOriginalSkillAnalysis.md/.json`은 SB8개와 관련원본75개를 export index/이름/SHA로 연결한다. NormalAtk01은 SI의4연타 이름과 달리 attack group5, Dempsey 본공격도5 group이다. source notify의 실제 BoneName을 SD 이름으로 대체하지 않는다. NormalAtk01 AC02 group3은 SD_R_02 이름을 쓰지만 L-Hand/L-Forearm volume이 저장돼 있다.

Armageddon 착지 Notify의 DamageInfoIndex1→SI DamageInfos[1]→`SD_Yetuga_Proto_Armageddon_02.AttackInfo.GuardDamageInfo.bDontJustGuard=true`를 직접 추적했다. 시작 StaminaBreak와 착지 폭발, 일반 guard/JustGuard/Parry를 구분한다. 두 잡기 SD는 HoldAttackAuto/bDontGuard=true며 초기 capture index default는 생략돼 native 미확인이다. 이러한 원본 설정을 이번 프로젝트 notify/피격 기능으로 적용한 것은 아니다.

Engineering 분석의 마지막 보완 절은 NormalAtk01 회수 후 HP ratio.7/근접 RushGrab, Dempsey 마지막 reaction과 별도의 CloseGrab 예약, Armageddon 조건부 RushGrab, IceBreath 조건부 ChargeTackle를 구분한다. 브레스/얼음 객체·바위 투사체·잡힌 target 반응을 몸 애니메이션 목록과 따로 조회한다. 원본 event 시간은 그대로 저장했으며 재생률을 새로 수정하지 않았다.

## 2026-10-08 — 방어 포즈·동명이인 원본·최종 근거 확인

`YetugaOriginalDefenseRecovery.md/.json`은 같은 research root에 있는 표적40package/154export 보고서다. Yetuga exhaustion AP는 New Composite→GroggyStand_F, 직가 reaction 전용 Groggy는 GroggyStr_F다. 부위 파괴 PartGroggy Start/Loop/End와 구분한다. CS Battle.StaminaExhaustionInfo.StaminaExhaustionTerm8.0 및 공식5→8초 patch는 일치하지만 actual Brutal 허용 창·native timer 전체 수명까지 검증한 것은 아니다.

최종 사본 감사에서 Moving/Reaction과 Skill/13_Armageddon의 `AC_Yetuga_DamageParry_F`가 서로 다른 package/SHA임을 확인했다. 두 원본을 YetugaOriginal/PackageCopies의 **full package suffix**로 보존하고 Index.local_path가 정확 사본을 지목한다. 기존 flat 사본은 역사적 호환용이며 이름만으로 원본을 식별하지 않는다. SourceMetadata.zip은 변경하지 않았다. 처음 실패는 ResearchVerificationFailure_NameCollision.json, 최종 확인은 ResearchVerification.json이다.

게임 asset212개 존재·현재 source/legacy 이름 매핑, Yetuga237개 원본사본SHA, Apes59개기초hash 및 별도표적보고서, 공개원본/시간검증/manifest를 확인했다. 원본의 gameplay Notify를 새 native/GAS로 임포트하거나 animation 옵션·속도·scale을 수정한 것은 아니다. 후속은 위 저장 자료에서 표적확인으로 이어가며 전체 retime/rename/재임포트를 재실행하지 않는다.

## 2026-10-11 — 실제 Pattern/Fall author·원본 field 해석 보완

Source zip 및212 library는 보존했다. 추가 표적 curve2는 `Metadata/GiantCombatFall_20261011/OriginalCommonCurves/BBQ/Content/_Common/MoveCurve/CV_Common_Jump_Normal.json`와 `CV_common_accel_deaccel_normal.json`; `FloatCurves`/`FloatCurves[1]/[2]`의 Keys(Time/Value/Tangents)를 보존한다. source/archive closure에 빠진 해당 curve만 추출했고 기존 대규모 extraction/retime은 반복하지 않았다. 적용곡선의 X 시간 진행률 정규화/YZ offset 및 native MoveTo 소비는 current CMC 어댑터이며 원작 실행함수 확인과 구분한다.

Yetuga FastBall source Step1 `xxAnimNotifyState_SkillAction` pickup time=.663037050 s의 `bNotifyBegin=true`, BeginSkillAction 미직렬화다. Step2 marker time=.680444771 s에는 `BeginSkillAction=ESkillAction::Use`가 직접 있다. current adapter는 첫 marker Spawn을 추론하고 명시 Use에서 돌을 발사한다. native class default Spawn 자체의 직접 확인은 아니다. 기존 StepStart 자동 생성/첫 marker Use 해석은 철회한다. Apes FastBall source SkillEvent Index1 Spawn→다음 Step2 Use 연결은 별도 경로다.

현재 main body/animation/source 명세48/81노드·입력/필드 provenance·미지원19 및 관측 범위는 `AuthoringPlan.json`/FinalVerification와 [구현 정본 마지막 절](../Engineering/APES_YETUGA_FALL_IMPLEMENTATION_20261011.md)에 재사용 가능하게 남겼다. 원본 metadata 동작, 현재 어댑터, 실제 build/PIE 검증을 구분한다. AP missing model sphere 및 native physics/카메라/Spell/전체 BT/pixel/frame 동일성 경계는 계속 유지한다.

## 2026-10-13 — Apes·Yetuga 잡기와 Armageddon 원본 자료·화면 검수

원본 보관 명세 `Metadata/GiantCombatFall_20261011/AuthoringPlan.json`의 `xxHoldingStartFunc.raw.HoldAttachInfo`에는 공통 `AttachSocketName=Weapon_L`가 있고, ApesStoneHandElite는 `TargetSocketName=Bip001-Spine`, Yetuga는 `TargetSocketName=Hold_Spine`이다. Apes 행의 `RagdollInfo.PhyAssetType=ECommonPhysicsAsset::FallDown`, `RagdollBoneName=Bip001`, `PhysicsBlendWeight=0.5`는 원본 직접값이다. 현재 임포트된 Player PhysicsAsset은 원본 FallDown 자산으로 확인되지 않았다. 기존 UE physics-handle/상반신 시뮬레이션을 렌더링 PIE에서 켰을 때 잡힌 몸이 손에서 바닥으로 처지는 현상을 확인했으므로, 이 미확인 물리 결합은 제거하고 원본 손·몸통 소켓을 잡기 동안 정렬했다. 이 정렬은 원본 `HoldAttachComponent`의 현재 프로젝트 어댑터이지 원작 native 물리 구현을 직접 복원했다는 뜻이 아니다.

Apes의 `SI_ApesStoneHand_E_FastBall.SkillName.SourceString=강하게 돌 던지기`와 별개의 `Dodge_A`/`Level_DashAtk_New` 잡기 성공 분기를 구분했다. FastBall 돌 던지기는 원본 패턴이므로 유지한다. 현재 `FS_Rock_Big_009`는 같은 계열의 임시 외형 매핑이며 정확한 COI mesh 대응은 미확인이다. Yetuga의 잡기는 `CloseGrab`, `RushGrab` 두 계열이다. `RushGrab_Step2`는 성공 후 붙잡은 포즈다. `ChargeTackle` 원본 자료는 보존했으나 레벨 선택·후속에서는 사용자 지시에 따라 제외했다. Armageddon 착지 타격의 원본 근거는 `AC_Yetuga_Armageddon_Jump_End` Notify[14] 및 `_Close` Notify[17]의 재생 시각 0.652310151~0.702310119초, cylinder EndRadius 2000cm·Size.Z 500cm와 `SD_Yetuga_Proto_Armageddon_02.AttackInfo.GuardDamageInfo.bDontJustGuard=true`다. 원본 자체의 모든 손상·카메라·파티클 결과까지 확인한 것은 아니다.

플레이어에게 연결한 추출 시퀀스 `/Game/_Art/Player/Animation/Weapons/DualAxeSword/Recovered/CA_P_Kazan_Hold_Demon`은 현재 저장 에셋 기준 40 evaluated frames/1.333333초·139 tracks·`EnableRootMotion=false`다. `Metadata/GiantGrabs_20261013/PlayerHoldPoseAudit.json`에서 frame10 뒤에도 65개 몸 트랙이 변하므로 10프레임에서 고정하던 시도는 철회하고 최종 frame39=1.3초에서만 유지한다. 이 시퀀스의 원본 게임 내 모든 캐릭터별 상호작용 재생 조건까지 직접 입증한 것은 아니다.

분리된 백그라운드 RHI DevMap 검수의 `Metadata/GiantGrabs_20261013/VisualEvidence`는 Apes 두 잡기와 Yetuga 두 잡기의 성공·유지 화면을 보존한다. 검수 당시 손 소켓↔목표 몸통 소켓 거리는 네 사례 모두 0.000cm였고 `FinalVerificationVisualRepair.json` 및 Work `VisualPIE7.log`에 남겼다. Main 최종 RHI 패턴 검사는 13/13 성공했다. 이는 부착 안정성의 현재 화면 검증이며 원작 촬영 프레임과의 실측 비교나 Apes/Yetuga 전체 129노드의 모든 전이 화면 검수를 대체하지 않는다. 대상 잡기·Armageddon 애니메이션 10개 root track/추출 감사는 `RootMotionAudit.json`에 별도로 보존했다. 해당 10개의 참 root track이 첫 순서이고 UE root extraction에 동작이 있음을 확인했으며, 모든 동작의 주관적 끊김이 사라졌다는 증거로 확대하지 않는다.

## 2026-10-13 — 화면 정렬 probe의 판정 범위 보충

`Metadata/GiantGrabs_20261013/VisualEvidence/AlignmentProbe.log`는 네 grab의 소켓 거리 0.000cm와 화면 7장을 남긴 격리 검수다. 이 probe의 전체 테스트 종료 표시는 실패였는데, 당시 검사가 몬스터가 해제한 마지막 1/30초 안에도 Player montage의 정확한 최종 frame39 정지를 요구했기 때문이다. 해당 조건을 원본 클립의 마지막 표본 frame38/30 도달 또는 frame39 유지로 고친 최종 Main RHI `MainPIE.log`는 13/13 성공했다. probe 로그의 거리 측정과 최종 전체 검사를 구분해 사용한다.

## 2026-10-13 Apes·Yetuga 전체 패턴 시퀀스 루트/전환 추가 감사

별도 숨김 Main 에디터에서 현재 두 Pattern DA의 129 node가 직접 참조하는 AnimSequence 118개를 읽기 전용으로 조사했다. 원본별 결과는 `Metadata/GiantGrabs_20261013/AllPatternClipInventory.json`, 엔진 root 추출과 참 skeleton root/index/track 정보는 `AllPatternRootAudit.json`이다. 118개 모두 EnableRootMotion=true, 참 skeleton root track 존재 및 첫 순서, dirty package 0이었다. 8개는 엔진 추출 actor root 이동이 0이고 그중 5개는 Bip001에 중간 pose 이동이 있으나 처음과 마지막 위치 차는 0이다. 특히 Armageddon_End·두 StaminaRecover·Apes DashAtk_IDLE·Apes FastMove를 루트 트랙 오류로 단정해 일괄 재작성하지 않았다. root motion on 설정만으로 모든 화면 전이의 연속성을 증명할 수 없다.

`Metadata/GiantCombatFall_20261011/AuthoringPlan.json`의 각 node `step_properties.AnimBlendAlpha`/계산된 `blend`와 Main `PatternBlendSeconds` 129개를 대조해 불일치 0을 확인했다. 0초 전환 10개도 원본에 0으로 명시된 단계다. 따라서 이 값들을 임의 보간값으로 변경하지 않았다. 전환 시 이전 MoveTo source 제거와 다음 tick 등록 사이의 코드상 공백은 Engineering의 `EnterPatternNode`에서 새 window 즉시 등록으로 보완했다. Work/Main NullRHI DevMap `Khazan.GiantFall.PIE` 각 13사례 성공과 Main 컴파일을 `ImmediateMoveVerification.json`에 기록했다. 원작 영상과 전체 129 node 전이의 나란히 프레임 비교는 아직 수행되지 않았으며 '모든 끊김 제거' 또는 원작 완전 동일성으로 확대하지 않는다.

2026-10-13 보충: 위의 '고정/제자리'는 해당 AnimSequence의 참 root 추출량과 첫·끝 Bip001 위치 차가 0이라는 뜻이다. Apes FastMove 등은 별도 원본 MoveTo window가 actor를 이동시키므로 실제 캐릭터가 제자리라는 뜻은 아니다.

## 2026-10-13 원본 두 pak의 잡기 물리/Apes 투사체 표적 추적

기존 FModel 설정의 GameDirectory/AES를 출력하지 않고 저장된 CUE4Parse EnemyExtractor로 pakchunk0·pakchunk1을 함께 mount하여 해당 이름만 index/metadata/raw 표적 조회했다. `Metadata/GiantGrabs_20261013/SourceAssetTrace.json`과 `TargetedPlayerPhysicsMetadata`, `TargetedPlayerPhysicsRaw`, `TargetedApesProjectileAnimationMetadata`가 재사용 근거다. 원본 플레이어 메시 `C_P_Kazan.Properties.PhysicsAsset`는 `C_P_Kazan_PhysicsAsset`를 직접 참조하며 이 자산은 body17/constraint0이다. 별도 `C_P_Kazan_Ragdoll_HoldSpine2`는 body20/constraint19이고 원본 raw `.uasset/.uexp`를 스테이징했다. 그러나 `ECommonPhysicsAsset::FallDown` enum에서 그 별도 package로 가는 실제 native 매핑은 아직 확인되지 않았다. 이름만으로 현재 잡기 physics를 다시 켜지 않았다. UE5 에셋 변경0.

Apes `COI_ApesStoneHand_E_FastBall_OBJ`에는 명시 mesh property가 없고 source projectile Idle/Move composite은 공통 `Missile_Skeleton`을 참조한다. pak에는 같은 VFX 계열 `FS_Rock_Big_009`가 존재하고 프로젝트도 해당 asset을 쓰지만, COI visual class와 그 mesh의 직접 참조는 찾지 못했다. 따라서 임시 외형 매핑임을 유지한다. FastBall 자체가 원본 돌 던지기라는 기존 판정은 바뀌지 않는다. 다음 표적은 원본 ECommonPhysicsAsset 선택자와 projectile visual class binding이며, 근거 전 전체 PA/투사체를 교체하지 않는다.
