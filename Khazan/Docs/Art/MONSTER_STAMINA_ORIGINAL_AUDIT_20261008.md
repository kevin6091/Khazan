# 몬스터 자원 소진과 브루탈 어택 원작 조사

## 2026-10-08 — 표적 metadata와 공개 자료

저장된 도메인 자료를 먼저 확인하고 필요한 원본 package 19개만 표적 확인했다. 전체 Content/원본 전수 재추출, 클립 재임포트·재생률·root track 수정은 하지 않았다. FModel mounted 원본의 전체 게임 build 번호는 미확인이다. 파일 hash와 export index는 저장 snapshot 식별이며 현재 판매 버전과 동일하다는 보증이 아니다.

재사용 evidence:

- `Metadata/EnemyStaminaResearch_20261008/TargetedFindings.json`: 인간형 CS, Player Grapple/FinalBlow SI·SB·SD, 패링 표, holding 함수명, 출처 package/file/export/field/raw/SHA.
- `Metadata/EnemyStaminaResearch_20261008/StatusAndHoldingSupplement.json`: CS6/AP6와 holding/dead 관련 추가 표적 확인.
- `Metadata/MonsterStamina_20261008/AnimationPlan.json`: 현행 이름에 연결한 소진18·front/back 피격24·Player5 클립과 타격 시간 계산. 계획/분석 파일이며 실제 적용 완료 receipt는 아니다.
- `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv`: current→legacy→원본 source 대응. 옛 Playback 명칭을 현행 asset 경로로 그대로 사용하지 않는다.

### 일반 적과 강적의 자원은 원작에서도 구분된다

공식 Basic Battle Guide의 Stamina 설명(약 95초)은 행동 소비와 회복을 보여준다. Fortitude 설명(약 125~140초)은 행동 소비·자연 회복이 없는 자원이다. 155~180초는 자원 소진과 브루탈 어택 기회를 다루며 195~215초의 stagger와도 구별한다. 260초 전후의 Reflection은 일반 Guard 성공과 구분해야 한다. 영상은 간격을 둔 표본과 자막을 확인한 것으로 연속 전 프레임 판독을 수행했다고 주장하지 않는다. [공식 Basic Battle Guide](https://www.youtube.com/watch?v=ISdLCHvHF_c)

저장 CS의 `Properties.StaminaStatus`, Battle entry `Value`는 다음과 같다. RecoveryPerSecond 및 DamageStateRecoveryPerSecond는 원시 자원량/초 필드로 기록하지만 게임 내부 배율·캐릭터 실제 gauge 환산은 미확인이다.

| 대상/CS snapshot | RecoveryPerSecond | 소진 중 DamageStateRecoveryPerSecond | 즉시 소진 회복 시작 flag | StaminaExhaustionTerm |
| --- | ---: | ---: | --- | ---: |
| Swordsman / CS_EmpireSword | 120 | 100 | true | 5.0 |
| SwordShield / CS_Empire_SwordShield | 80 | 100 | true | 5.0 |
| Heavy / CS_Empire_SwordHArmor | 70 | 1000 | true | 5.0 |
| Halberd **Early** / CS_EmpireHalberd_E_Early | 45 | 100 | true | 5.0 |
| Apes / 저장 CS_ApesStoneHand_E snapshot | 0 | 배열 비어 있음 | false | 5.0 |
| Yetuga / 저장 CS_Yetuga snapshot | 0 | 배열 비어 있음 | false | 8.0 |

인간형4 출처는 `TargetedOriginal_01/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/<family>/Base_Setting/CS_*.json`의 export0이다. Apes/Yetuga 저장 파일·정확 package·hash는 Supplement의 `stored_status_profiles`를 따른다. Halberd Early의 값을 모든 Halberd 변형으로 일반화하지 않는다.

정확 기간 field는 `Value.StaminaExhaustionInfo.StaminaExhaustionTerm`이다. 공개 패치도 Yetuga 브루탈 어택 기회 시간을 5초에서 8초로 늘린다. 한국어 게시 날짜와 영어 날짜의 시간대 차이가 있으며, 이것은 native timer 시작 시점을 증명하지 않는다. [공식 6월 업데이트](https://steamcommunity.com/games/2680010/announcements/detail/543361383085900259?l=koreana)

따라서 일반 인간형까지 자동 회복·공격 비용을 없애는 이번 규칙은 사용자 프로젝트 정책으로 구분한다. 원작을 근거로 여섯 종류의 내부 자원이 완전히 동일하다고 결론 내릴 수 없다.

### 패링 감소량과 회복 경계

원작 `BBQ/Content/_Common/Constants/ParringStaminaDamageDataTable`에는 `StaminaRateValue`가 있다. 확인한 일반 row는 1.0, 정예 상 row와 보스 중 row는 0.5다. 절대 자원 5로 변환하는 native 소비식을 확보하지 못했으므로 사용자 지정 5의 원작 출처로 삼지 않는다.

여섯 profile의 소진 종료 설정은 `EndStaminaExhaustionRecoveryOperator=EStatusOper::Add`, `EndStaminaExhaustionRecoveryStamina=0`이다. 이것만으로 종료 시 회복이 없다고 결론 내릴 수 없다. 별도 damage-state 회복과 native holding/skill 경로가 있기 때문이다.

확인한 native 함수 이름에는 `IsStaminaExhaustionTimeEnd`, `GetHoldAttacker`, `IsEndHolding`, `DoForceHoldDead`, `IsPauseStaminaExhaustionBySkill`, `IsPauseStaminaExhaustionByAnimNotify`, `CanStaminaRecoverySkillByOnDamage`, `ChangeConditionDeadState`가 있다. 함수 이름·직렬화 속성은 실행 bytecode나 호출 순서가 아니다. **공격자 모션과 피해자 모션이 모두 끝난 뒤 생존하면 정확히 MaxStamina로 충전하는 보편적 순서는 metadata만으로 확인하지 못했다.** 해당 구현은 Engineering 문서에 사용자 계약으로 기록한다.

공식 패치는 특정 skill 사용 중 소진 시간을 멈추는 조건과 보스 회복 관련 수정도 명시한다. 이는 단순히 한 animation notify로 모든 종료를 판단하는 구조라는 주장과 구별한다. [5월 소진 시간 정지](https://steamcommunity.com/games/2680010/announcements/detail/516336075474470254), [4월 회복 관련 수정](https://steamcommunity.com/games/2680010/announcements/detail/543353773096960512)

### 브루탈 어택의 원작 스킬 경로

Player 원본 package `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Grapple/SI_Kazan_DualSwordAxe_Com_Grapple`의 export0 `SkillName`은 **브루탈 어택**, subtype은 `StaminaExhaustionSkill`, InputType은 `Interaction`이다. 사용자가 임시로 부른 이름과 공식 명칭이 일치한다.

`SB_Kazan_DualSwordAxe_Com_Grapple_02`의 native parent는 `xxSimplePlayerGrappleSkill`이다. front는 Step1 Start→Step2 Atk01→Step3 Atk02, back은 BackGrappleStep4→5 Back01→6 Back02→None이다. 첫 SD는 `HoldAttackAuto_DamagerReaction`, `DieHard`, `TargetFlagStaminaExhaustionSkillTarget` 및 Grapple1/Back1 반응을, 마지막 SD는 `HoldReaction_AnimEndAutoRelease` 및 Grapple2/Back2를 참조한다. 양쪽 모션의 독립적인 수명과 전후 피격 클립을 사용할 근거다. native 동기화·정렬 거리·전체 취소 정책은 미확인이다.

치명적인 공격은 별도 분기가 있다. `GrappleInfo.FinalBlowDamagePreivewInfos`의 index/count와 `SI_Kazan_Com_FinalBlow`의 `브루탈 어택 : 처형`/`Execution`, `SB_Player_FinalBlow_Base`→`SD_FinalBlow`의 Execution1 반응을 확인했다. AP FinalBlowTypes는 Sword/Shield026, Heavy034, Halberd011, Apes019이며 Yetuga는 동일 필드가 없어 default/native 동작을 미확인으로 남긴다. 일반 Grapple front/back과 별도 처형 cinematic을 한 기능으로 합쳐 재현 완료라고 설명하지 않는다.

### 소진·피격 애니메이션 대응

AP의 `StaminaExhaustionAnimSetMap[Index1]` StartAnim/LoopAnim/EndAnim과 `SpecialDamageAnimList` Grapple1/Grapple2/Grapple_Back1/Grapple_Back2를 표적 연결한다. 단순 파일명의 Groggy/Down을 골라 소진 상태라고 추정하지 않는다.

- 인간형: 각 AP의 Groggy Start/Loop/End와 DamageGrapple front/back을 사용한다. SwordShield StartAnimBlendTime은 0.05, 나머지5는 0.2, Loop/End는 0.2다. AP field의 직접값이며 UE montage 자동 section 연결 사이의 별도 blend가 자동 발생한다는 뜻은 아니다.
- Apes: AP Moving/Reaction이 가리키는 Groggy Loop/End Variant01이다. Skill25의 Variant02는 별도이며 혼용하지 않는다.
- Yetuga: current 파일명 `Damage_GroggyStr_F_*_New`에 대응한 **New Composite 내부 source는 GroggyStand_F**이다. 이전 GroggyStr/PartGroggy와 구분한다. 이름만 보고 New 대응을 배제하거나 다른 pose를 가져오지 않는다.
- Player: 현재 시간 보정된 Composite Playback 5개를 InGame/DAS/BrutalAttack에 복제하는 계획이다. 0.01 mesh scale 계약을 유지하며 raw CA를 새로 재생률 보정하거나 root translation에 중복 100배 적용하지 않는다.

Player hit point는 원본 window와 dilation을 기존 Playback 60fps 시간축에 변환한 계산값이다. front 전체 montage 약 1.4672088초/2.2105424초, back 약 1.4708156초/2.2272091초다. 입력값·piecewise dilation·프레임 양자화·source hash는 AnimationPlan에 있다. 실제 원작 접촉 프레임을 직접 관측했다고 부르지 않는다. 몬스터 피격 클립 길이를 Player 클립에 맞춰 임의 배속하는 근거도 아니다.

이 문서는 원작 분석 결과다. 실제 gameplay 설정·code 적용·build·PIE 상태는 [Engineering 구현 기록](../Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md)과 별도 receipt를 따른다.

## 2026-10-08 16:36 KST — Work 클립 연결과 실제 스켈레톤 슬롯 확인

별도 Work에서 선택 클립 47개를 복제하고 20개 몽타주를 작성했다. `Metadata/MonsterStamina_20261008/Authoring.json`의 각 clip_audits는 원본/복제의 raw bone transform MD5, 길이·RateScale·프레임·root motion 옵션·skeleton을 직접 비교해 일치했다. Player 기존 0.01 표시 scale 계약에 추가 배속·root translation 배율을 적용하지 않았다. 시각 접촉과 원작 전체 재현의 검증을 뜻하지 않는다.

첫 preflight 실패는 Apes/Yetuga 스켈레톤에 slot group이 0개이고 DefaultSlot이 없는 것이었다. 원본 트랙을 수정하거나 skeleton을 복제하는 대신 두 기존 Skeleton에 실제 새 montage 소비자의 DefaultSlot만 등록했다. `skeleton_slot_audits`는 전후 모든 reference bone 이름·parent index·reference pose의 완전 일치를 기록한다. Skeleton package의 직렬화는 달라지므로 '모든 원본 Skeleton 파일 무변경'으로 기록하지 않는다. 대상은 `Shared/Elites/ApesStoneHandElite/Skeletons/SKEL_EN_ApesStoneHandElite`, `HeinMach/Bosses/Yetuga/Skeletons/SKEL_EN_Yetuga` 두 개뿐이다. 초기 파일은 `AssetBaseline.json`과 `BeforeAssets`에 보존했다.

실제 게임용 body에 필요한 캡슐은 저장 CB의 export2 CapsuleComponent에서 Apes R99/HalfHeight240, Yetuga R150/HalfHeight265 cm를 확인했다. mesh offset은 Apes export63 (-50,0,-240), Yetuga export57 (0,0.000031,-265), yaw -90도다. CB 파일·hash·field는 `BodiesAuthoring.json`에 있다. 현재 Art body의 표시 scale 1을 재사용하며 Apes 원본 CharacterScale 0.8 및 원본 BoneMod 전체를 재구성한 것으로 표현하지 않는다. 별도 gameplay BP/ABP는 Engineering 작업이고 기존 Art BP는 보존했다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

선택 에셋의 Main 실제 반영과 새 프로세스 저장 재로드를 완료했다. 원본 감사/metadata 출처와 native 구현을 분리한다. Authoring47clip+body idle2의 기존 raw bone data/길이/rate/root flags를 보존했고20montage는 기존 보정 클립을 이어 사용한다. Player Front/Back의 notify 시간은 기존 원작 window→dilation→60fps 계산으로 authoring했으며 현재 Player .01에 추가 100배 보정을 하지 않았다. Skeleton2의 DefaultSlot만 추가하고 reference bone 이름/parent/pose를 그대로 유지했다.

새 Main actual module16924에서49copies/20montages/6monsterDefs+Player/35cost-free attack BP/2body의 saved reference를 확인했고 dirty0였다. 이것은 원작 native stamina recovery 순서 또는 시각 접촉의 정확 재현을 증명하는 것이 아니다. 원작의 positive human recovery와 Fortitude 정책 차이, separate Execution asset 경로, Yetuga GroggyStand/New와 old GroggyStr/PartGroggy 차이는 앞선 분석 그대로 유지한다. 정확 원본과 구현/사용자 수치 구분은 각 표적 report 및 Engineering 정본으로 연결한다.
