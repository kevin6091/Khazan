# Apes / Yetuga 비중단 피격과 특수 경직 근거

## 2026-10-13 — 설계·원작 근거 (구현 검증 진행)

사용자 요청은 일반 피격으로 실행 중인 공격/이동/AI를 끊지 않고 현재 포즈에 움찔하는 변화를 더하는 것이다. 이 표현에는 **Local Space Additive Animation + 독립 Montage Slot Group**을 사용한다. 원작의 커스텀 노드를 그대로 복원했다고 주장하지 않는다.

### 확인한 원작 데이터

원본은 Apes `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip`, Yetuga `Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip`이다. 원본 entry/export/field/원시 값/hash와 별도 저장 report 연결은 `Metadata/GiantHitOverlay_20261013/OriginalConditions.json`에 있다.

|항목|ApesStoneHandElite|Yetuga|의미/확인 범위|
|---|---|---|---|
|CS `.StaminaStatus[Battle].bUseSuperArmourStamina`|true|true|원작 직접 확인. 이 flag만으로 모든 native 조건/공식을 확인한 것은 아니다.|
|같은 `.bUseDamageReaction`|false|true|원작 직접 확인. Yetuga의 true를 일반 피격마다 Action을 취소한다는 근거로 해석하지 않는다.|
|AB CDO `.xxAnimGraphNode_AdditiveBlend`|있음|있음|`BlendTime=[0.1,0.1]`, `BlendType=Linear`, `ResetAnimSequence=false`. 원작 커스텀 node의 실행 알고리즘/동적 입력은 미확인.|
|CS `.StaminaExhaustionInfo.StaminaExhaustionTerm`|5.0 s|8.0 s|원작 직접 확인. 현재 프로젝트의 `ExhaustionSeconds` 근거. Start 포함 timer이며 End 포즈까지 합친 전체 제어 잠금 시간과 구분한다.|
|CS `.PartDestruction[Group1].bCanDestruction`|true|true|부위 파괴용 별도 반응 데이터가 있다. 현재 일반 HP/Stamina 피해량과 동일한 단위라고 주장하지 않는다.|
|같은 `.Durability / SecondDurability / MaxDestructionNum`|1 / 200 / 1|350 / 350 / 1|원시 값. 단위/첫·두 번째 내구도 의미/피해 환산 및 구체적인 피격 부위 매핑은 미확인.|
|같은 `.NormalGroggySkill / BigGroggySkill`|null / SI_ApesStoneHand_E_PartGroggy|null / SI_Yetuga_PartGroggy|부위 파괴 → 별도 PartGroggy 참조. 단순 HP 감소나 보스 HP 절반 도달 조건으로 대체하지 않는다. HPOver/HPBelow 검사 flag는 둘 다 false.|

### 상황별 동작과 현재 구현 범위

- **일반 승인된 피격, 스태미너가 남아 있음:** HP/ST 피해는 기존 GE가 처리한다. 두 Definition의 AdditiveHits 설정만 사용해 현재 공격/AI/이동을 유지한다. Short/Knockback/Launch/VictimFront와 blocking reaction을 사용하지 않는 None에도 동일한 작은 피격 표현을 준다. 인간/Player의 None 정책은 유지한다.
- **스태미너가 0 이하, HP가 남아 있음:** 기존 `AKZMonster::RefreshCombatState` → `UKZExhaustionAbility`가 Action을 취소하고 State.Exhausted 및 이동 제한을 소유한다. Start→Loop→End, Brutal Attack 가능 상태는 그대로다. 패링의 스태미너 피해도 같은 소진 조건에 기여한다. 현행 `ReportAttackParried` 기본 5는 이전 사용자 정책이며 원작 패링 Table 값으로 표시하지 않는다.
- **HP가 0 이하:** 기존 사망 경로가 소진보다 우선한다. 진행 중인 Brutal 짝 반응의 마무리 정책도 유지한다.
- **Apes의 특정 패링/Just Guard 반응:** 원작 `SB_ApesStoneHand_E_DempseyRoll` Step2의 `ParryingReaction/JustGuardReaction` + `NotifyEnable` 조건이 `AC_ApesStoneHand_E_JustGuardReaction` 재생(`AnimBlendAlpha=0.3`)과 Rate 방식 StaminaConsumeValue=500을 참조한다. 모든 공격의 패링에 무조건 같은 경직이 생긴다는 뜻이 아니다. 500의 환산과 notify gate의 native 활성 판정은 별도 확인 범위다. 기존 Pattern/Parried 이벤트 경로는 이번에 바꾸지 않았다.
- **Yetuga 돌진의 벽 충돌:** 원작 `SB_Yetuga_ChargeTackle` Step2/3/6의 `OnCollisionWall` 이벤트가 Step7로 바꾸고, Step7은 `AC_Yetuga_ChargeTackle_Stun`, Step8은 Stun_End를 재생한다. 이 반응은 일반 피격/스태미너 소진과 별개다. 기존 Pattern의 Collision 이벤트 매핑은 유지한다. 프로젝트의 일반 blocking world collider 판정과 원작 native wall 판정이 완전히 같다고 주장하지 않는다.
- **부위 파괴:** 두 CS 모두 Group1 BigGroggySkill이 연결돼 있다. 현재 프로젝트는 PartGroggy skill/애니메이션 실행 데이터가 있어도 일반 공격의 부위 내구도 누적·방어 그룹 판정과 자동 trigger가 완성된 것으로 확인되지 않았다. 이번 요청의 일반 가산 피격에 그 시스템을 선행 추가하지 않는다.

### 구현 계약

새 runtime class/component/manager/state tag는 0개다. 기존 `FKZHitReactionSettings.AdditiveHits`가 비중단 표현을 선택한다. `AKZCharacter::PlayHitReaction`은 승인된 피해 이후 living/ST/Dead/Exhausted gate를 확인하고 직접 `UAnimInstance::Montage_Play`를 사용한다. ASC PlayMontage/HitReaction Ability를 사용하면 PreActivate에서 이미 Action 취소와 제한이 발생하므로 이 표현에는 쓰지 않는다. `KZHitReactionGroup / KZHitReaction`은 이 Character의 순수 피격 표현 전용이며 root motion이 없다. UE 5.8의 Play true 옵션은 새 montage와 같은 group의 이전 montage만 교체하므로 Action DefaultGroup은 유지된다. 반복 피격은 해당 group 안에서 crossfade한다.

Character는 weak AnimInstance/Montage 및 instance ID receipt만 보존한다. Stop은 receipt를 확인한 뒤 전용 group의 outgoing crossfade까지 정리한다. 소진/사망은 Monster의 기존 자원 결과 처리, UnPossessed/EndPlay는 Character의 기존 lifecycle에서 정리한다. 제어/피해 상태 사본은 없다. 기존 Combo의 준비/가드 구간 조회와 AI 회전의 시간 조회는 가장 최근의 presentation montage 대신 실제 실행 Ability의 `GetCurrentMontage()`를 읽는다.

두 ABP는 기존 포즈 연결을 보존하고 Output 직전에 항상 Source Pose를 갱신하는 독립 Slot 1개를 추가했다. 원작 Normal L/R/D/U full-pose clip은 보존하고 game-facing copy8를 자신의 첫 프레임 기준 local additive로 만들었다. 첫 프레임 기준 delta/무 root motion/notify 제거는 프로젝트 표현 adapter다. blend enter/exit 0.1 s Linear는 원작 AB node 값을 engine montage에 매핑한 값이며 원작 Montage의 직접 확인값은 아니다. 원본 source/frame count/FPS/길이/rate를 보존한 authoring readback은 `Author01/Authoring.json`에 있다.

Epic의 Slot Group 동작 설명: https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-slots-in-unreal-engine

완료/적용/build/검증 결과는 아래 날짜별 완료 절에만 추가한다.

## 2026-10-13 — Main 반영 및 최종 검증 완료

사용자가 Main editor를 종료한 뒤 `DeliveryPlan.json`의 기존 6개 에셋 baseline hash와 새 16개 에셋의 부재를 확인했다. 별도 Work에서 저장·검증한 22개 에셋(새 additive sequence/montage 16개, 기존 Definition/ABP/Skeleton 6개)을 Main에 원자적으로 반영했다. 최종 Main Source 6개도 `SourceChangesFinal.json`의 빌드·검증된 hash와 일치한다. 원본 full-pose sequence/montage 16개는 변경되지 않았다.

Main Source object로 link한 검증 모듈을 별도 DLL 이름으로 반영했고, fresh Main 전용 editor가 실제 로드한 DLL SHA-256은 `bd16ea80453fa880e46cff39b0ca42962ad24d58e26074de2f8b657b7995aad6`이다. 숨김·저우선순위 Main NullRHI PIE `Khazan.GiantHit.PIE`는 종료 코드 0, **25/25** 조건을 통과했다. 두 거인 각각 네 방향의 피격 포즈 합성, 일반 피격 중 공격 Ability/ASC montage·AI 진행 유지, 반복 피격, 피해 GE, ST0 Exhaustion·HP0 Death, UnPossessed/EndPlay 정리와 일반 검병의 기존 blocking reaction을 확인했다. 별도 RHI 화면 증거는 `PIE01/Family0_Case0_Flinch.png`, `PIE01/Family1_Case2_Flinch.png`에 있다. 정확한 Main 로드·케이스·hash는 `Metadata/GiantHitOverlay_20261013/FinalVerification.json`, `MainCPU02/Driver.json`, `MainCPU02/Native.json`을 따른다.

원작 custom additive node의 내부 포즈 계산과 부위 내구도 자동 누적·피해 환산은 원본 근거가 아직 없어 이번 완료 범위에 포함하지 않는다. 일반 피격의 비중단 표현, 기존 스태미너 소진·사망·특수 Pattern 우선순위는 구현 및 Main PIE 검증 완료다.

## 2026-10-14 — Apes/Yetuga 특수 반응과 Group1 부위 파괴 Main 반영

일반 피격은 앞선 비중단 Local Additive 반응을 유지한다. 공격 충돌의 기존 GE가 HP·스태미너 피해를 적용해도, HP와 스태미너가 남아 있으면 진행 중인 공격/AI를 취소하지 않는다. 스태미너가 0이 되면 기존 `UKZExhaustionAbility`가 행동을 중단하며 Apes 5초, Yetuga 8초는 원작 CS의 `StaminaExhaustionInfo.StaminaExhaustionTerm` 직접 확인값이다. HP 0 사망은 그보다 우선한다. 2026-10-14 Main `Khazan.GiantHit.PIE`에서 기존 25/25 조건이 다시 통과했다.

특수 패턴은 일반 피격과 독립적으로 유지했다. Apes `DempseyRoll_Step2`의 기존 `Parried` 분기는 원작 `SB_ApesStoneHand_E_DempseyRoll`의 notify gate 0.569643–0.862859초에서 `DempseyRoll_Reaction`으로 전환하며 `Damage_JustGuardReaction`의 SFX/VFX를 재생한다. Yetuga `ChargeTackle_Step2/3/6`의 기존 `Collision` 분기는 원작 Step7 `Attack_ChargeTackle_Stun`, Step8 `_Stun_End`로 간다. 이번에는 `UKZMonsterPatternAbility::HandleWorldCollision`에서 Pawn·트리거·걸어 다닐 수 있는 바닥 접촉을 제외하고 실제 비보행성 blocking 월드 충돌만 이벤트로 넘기도록 보완했다. 분기와 원본 clip/notify 바인딩은 `Metadata/GiantReaction_20261014/AuditMain02/Audit.json`에 저장했다. 두 특수 분기의 실제 Just Guard 입력·벽 충돌 장면 재현은 이번 PIE의 검증 범위 밖이며, 데이터 연결과 코드 조건 확인을 런타임 재현으로 표현하지 않는다.

부위 파괴의 원작 직접 근거는 Apes `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip`, Yetuga `Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip`의 CS `Properties.PartDestruction[0]`이다. 두 종 모두 `Key=EGrDefenseGroup::Group1`, `MaxDestructionNum=1`, `NormalGroggySkill=null`이며 `BigGroggySkill`은 각각 `SI_ApesStoneHand_E_PartGroggy`와 `SI_Yetuga_PartGroggy`다. `Durability/SecondDurability` 원시값은 Apes `1/200`, Yetuga `350/350`이다. HP 임계값 분기 flag는 둘 다 false다. CB의 `Group1 bWeakPointDamageBox` 원본 부착 bone/상대 transform은 Apes 등·머리 2개, Yetuga 등·양팔 쪽 3개를 해당 `DA_Character_*`에 기록했다.

현재 프로젝트는 Player 공격의 실제 overlap/sweep가 해당 약점 박스를 맞히고, Guard/Dodge/Capture가 아니며 피해 GE가 성공했을 때만 Group1 내구도를 누적한다. `HPDamage × 20`은 원작의 native 부위 피해 환산식이 없어서 선택한 **임시 튜닝 배율**(무차원)이며 두 Definition에서 조정할 수 있다. 원본 CB에 기본 box half extent가 없어 `32 cm`도 **임시 충돌 크기**다. 이 설정에서 기존 10 HP 공격을 약점에 맞히면 Apes는 첫 타, Yetuga는 두 번째 타에 원작 `Durability` 문턱을 넘는다. `SecondDurability`의 native 의미/재파괴 조건은 미확인이라 적용하지 않았다. 두 몬스터의 `MaxDestructionNum=1`을 현재 Group1 1회 파괴로 해석하고, 파괴 뒤 프로젝트 약점 query box를 비활성화한다. 이를 원작 전체 native 판정과 동일하다고 주장하지 않는다.

문턱 도달 시 기존 `Event_Combat_Hit_Short` → `UKZHitReactionAbility` 경로에 두 종 전용 PartGroggy montage를 전달한다. 이 Ability가 Action 취소·`State_HitReacting`/입력 제한·종료 cleanup을 소유하므로 새 상태 머신이나 재생 관리자를 만들지 않았다. PartGroggy가 일반 additive 움찔보다 우선한다. Start/Loop/End 원본 clip과 notify를 재사용한 montage 길이는 Apes 6.033333초, Yetuga 8.033333초이며 Loop 길이는 Apes 원본 count 미확인으로 임시 1회, Yetuga 원본 skill bundle count 2회다. `KZAnimNotify_CombatEffect.cpp`는 변경하지 않고 현행 renderer를 재사용했다.

Main에는 `Metadata/GiantReaction_20261014/MainDelivery.json`의 소유 Source/asset 13개만 baseline hash 확인·백업 뒤 반영했다. Main `KhazanEditor Win64 Development` 빌드 성공, fresh Main 로드 DLL SHA-256 `f8f02ba8b0500f01a7ca5b0f515509cdbefd4906c0621552ffbffa089989576b`다. `MainPIEFinal/Driver.json`의 RHI `Khazan.GiantReaction.PIE`는 두 종의 원본 bone 약점 box 개수/충돌 query/내구도 문턱/전용 montage/1회 제한/종료 태그 해제를 통과했고 화면 8장을 남겼다. `MainGiantHit01/Driver.json`과 `Native.json`은 일반 피격·Exhaustion 회귀 25/25 통과다. 부위 파괴 테스트는 실제 약점 query와 피해 환산·Ability 실행을 확인하지만, 저장된 Player 공격 montage를 통한 최종 조작 입력 전체는 별도 실전 QA 범위다. 원본 native 환산식·SecondDurability·기본 box 크기와 완전한 픽셀/청감 일치는 여전히 미확인이다.

## 2026-10-14 — 임시 약점 크기 설정화 및 최종 Main 재검증

원본 CB 기본 box 크기 미확인에 따른 32 cm half extent를 코드 내부 literal에서 `FKZMonsterStaminaSettings.PartGroup1BaseHalfExtentCm`의 `EditAnywhere` 기본값으로 옮겼다. 두 몬스터 Definition에서 편집 가능하며 런타임은 양수·finite 값만 받아 약점 box를 만든다. 피해 환산 `PartGroup1DamageScale`과 함께 임시값 출처/조정 위치를 한곳에 둔다. 변경 3개 Source는 `TuningSettingDelivery.json`으로 별도 hash 기록해 Work/Main 양쪽에 일치시켰다.

변경 후 Main 재빌드 성공(45 action), fresh Main RHI `MainPIETuningFinal/Driver.json`의 Apes/Yetuga 2case 성공·material compile failure 0, 8장 화면을 확인했다. 새 기본 크기 32 cm를 두 실제 Definition이 읽는 테스트도 통과했다. 앞 절의 이전 DLL/PIE 기록은 당시의 성공 기록으로 보존하되, **최종 로드 DLL SHA-256은 `7f7202126372cd963c4486c795185b9f2e07b85fdb67b290144544da35e2b63d`**다. 저장된 Main 분기·notify 재감사 `MainAuditFinal/Audit.json`도 통과했다. Main 13개 소유 파일의 초기 전달 + 후속 변경을 합친 최종 해시는 `FinalVerificationTuning.json`에서 13/13 일치한다. 기존 GiantHit 25/25는 후속 변경이 약점 box 설정/검증에만 국한되어 앞 절의 별도 Main 실행 결과를 유지한다.
