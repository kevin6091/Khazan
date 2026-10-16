# 몬스터 스태미너 소진·브루탈 어택

## 2026-10-08 — 요구사항과 작업 중 계약

이 문서는 구현 진행 기록이다. 현재 native 수정은 `Khazan_MonsterWork_20261006/Khazan`에 있으며 Main 게임 코드·에셋 전달과 PIE 검증은 아직 완료하지 않았다. 원본 자료는 `Metadata/EnemyStaminaResearch_20261008/TargetedFindings.json`, `StatusAndHoldingSupplement.json`, 애니메이션 계획은 `Metadata/MonsterStamina_20261008/AnimationPlan.json`이다.

### 사용자 결정과 원작 확인의 구분

- 여섯 몬스터 모두 스태미너를 공격 Cost로 쓰지 않고 자동 회복시키지 않는 것은 이번 프로젝트의 사용자 정책이다. 원작은 일반 적의 Stamina와 일부 강적의 Fortitude를 구분한다. 저장된 일반 인간형 CS에는 양의 자연 회복량이 있으므로 원작의 모든 적이 같은 규칙이라고 설명하지 않는다.
- 패링 감소량 `5`와 일반 피격의 공격별 감소량은 사용자 조정값이다. 원작 패링 표의 ratio를 절대량 5의 출처로 사용하지 않는다.
- 0이면 exhaustion Start/Loop, 브루탈 어택 실행 중에는 상대 피격 Damage1/2, 양쪽 정상 완료 후 생존이면 End 회복 모션 뒤 현재 MaxStamina로 충전한다. 정확한 양쪽 완료 의존관계와 최대치 충전은 native 원본에서 확인하지 못했으며 사용자 요청을 계약으로 삼았다.
- 원작 저장 CS의 `StaminaExhaustionInfo.StaminaExhaustionTerm`은 인간형4/Apes `5`, Yetuga `8`이다. 초로 해석한 유한 기회 시간은 잠정 채택이며 `ExhaustionSeconds=0`으로 설정하면 브루탈 어택까지 무기한 대기한다. paired 실행 동안 남은 시간을 일시 정지한다. 원작 native 타이머 시작 지점은 미확인이다.
- 브루탈 HP 피해량은 사용자 답변 전 미할당 `0`이다. 원작 피해 ratio에서 임의 HP 값을 만들지 않는다. 임시 탐색 범위는 인간형 `180 cm`, Apes `260 cm`, Yetuga `400 cm`이며 원작 거리 미확인 상태의 캡슐·캐릭터 크기 기반 튜닝이다. 정렬 간격 0은 양쪽 현재 캡슐 반경 합을 사용한다. 실제 시각 접촉 검증 후 조정해야 한다.

### 기존 구조의 재사용과 책임

`UKZAttributeSet`의 HP/MaxHP/Stamina/MaxStamina, 기존 ASC, CharacterDefinition 초기 효과·Ability 부여, 공유 Instant 피해 GE, `UAbilityTask_PlayMontageAndWait`, 기존 Locomotion 제약 handle과 StateTree Pause/Resume를 재사용한다. 새 상태 머신·manager·component는 만들지 않는다.

새 runtime 클래스는 실행 수명이 실제로 다른 두 개뿐이다. `UKZExhaustionAbility`는 몬스터의 소진·피격·회복과 timer를 소유한다. `UKZBrutalAttackAbility`는 플레이어의 입력 활성화·타깃 선정·몽타주 타격 notify를 소유한다. Shared 상태는 ASC의 `State.Exhausted`, `State.Dead`이고 Ability 내부 phase/completion bool은 자기 실행의 순서만 나타낸다.

`AKZMonster`는 HP/Stamina 변경을 다음 tick으로 묶어 한 피해 효과의 전체 결과를 확인한다. HP 0을 소진보다 먼저 처리한다. 현재 공격의 HP와 Stamina modifier 순서가 바뀌어도 죽은 몬스터의 소진 회복을 시작하지 않는 목적이다. `AKZMonsterAIController`는 소진/사망 중 StateTree를 일시 정지하고 기존 BattleTarget을 보존한다.

### 피해·패링 연결 계약

공유 GE는 `/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage`이며 `KZAttackHPDamage`, `KZAttackStaminaDamage` SetByCaller에 음수 피해량을 전달한다. PlayerAttackCollision ARCH-81의 ComboAttack 데이터 소유권을 침범하지 않는다. 그 별도 작업의 실제 hit 적용 이후 ASC attribute delegate가 이번 소진을 시작한다.

`AKZMonster::ReportAttackParried(Defender)`는 성공 패링을 판정한 실제 생산자가 한 번 호출할 hook이다. 현재 정상 Guard 성공은 패링이 아니며 `TryGuardHit`에 이 hook을 잘못 연결하지 않는다. 현재 프로젝트에는 Monster→Player 실제 적중·패링 생산자가 없으므로 물리적 공격 패링의 end-to-end 작동은 후속 범위다. hook 자체와 소진 연동은 native 검증한다.

### 브루탈 어택과 회복

임시 입력은 기존 `Input.Action.X`이다. ASC는 일반 X Ability를 활성화하기 전에 가까운 유효 소진 타깃이 있는 Brutal Ability를 시도하고 실패하면 기존 X 처리로 돌아간다. 명시한 Ability handle 요청은 이 우선순위의 영향을 받지 않는다.

탐색은 플레이어 전방 반공간의 가장 가까운 살아 있는 소진 몬스터이며 visibility를 확인한다. 타깃의 전후에 따라 기존 front/back 클립을 선택한다. 플레이어 .01 mesh 계약과 이미 시간 보정된 Playback 클립을 보존하며 재생률이나 root translation에 추가 100배 보정을 하지 않는다.

Player 몽타주의 `BrutalHit1/BrutalHit2`는 원작 damage window를 기존 dilation→60fps 시간축으로 계산한 위치다. 첫 notify는 피해자 Damage1, 둘째는 Damage2와 설정된 총 HP 피해를 한 번 적용한다. 몬스터의 피격 클립 길이를 플레이어 클립 길이에 맞춰 임의 배속하지 않는다. 원작 여러 hit ratio와 cinematic lethal Execution 분기는 별도이므로 이번 단일 HP 값과 생존 검사로 모두 재현했다고 주장하지 않는다.

양쪽 실제 Task 완료가 모여야 회복을 시작한다. 취소는 최대치 회복을 하지 않으며 소진 Loop와 남은 기회 시간으로 돌아간다. 사망은 회복 없이 양쪽 presentation 완료 뒤 마지막 포즈를 고정한다. UnPossessed/EndPlay는 자기 timer/delegate/Task/제약을 정리한다. 회복의 직접 Stamina 설정은 정상 End 완료 한 곳에서만 실행한다.

### 현재 검증 범위와 다음 절차

원작 표적 metadata 분석과 현재 Source 기반 구현 초안 검토를 수행했다. 첫 cold build는 다른 에디터의 전역 Live Coding mutex로 UBT가 거부했다. 사용자 에디터를 건드리지 않고 독립 Work 출력에 `-NoHotReloadFromIDE`로 다시 빌드 중이다. 아직 컴파일/에셋 작성/PIE 성공으로 기록하지 않는다.

다음: Work native 컴파일 → 선택 클립·몽타주/정책 GE·CharacterDefinition 작성 → 저장 후 재로드 → 여섯 종류 실제 native PIE에서 피해·패링 hook·소진·양쪽 완료·취소·사망 검사 → 최신 Main CAS 병합·stock build → 자체 별도 Main 재로드·PIE 검증. 기존 별도 MonsterMotion proof는 최신 Main Source와 달라 재사용하지 않는다.

## 2026-10-08 16:36 KST — 컴파일·Work authoring 완료, PIE 시작 전

Native/Editor helper 컴파일은 성공했다. 빌드 로그는 `NativeInitialBuild_NoHotReload.log`, `SlotAndLateAbortBuild.log`이며 기존 Main은 조작하지 않았다. ARCH-81 PlayerAttackCollision의 완료된 Main Source3/fixture1/DA1을 읽어 Work에 가져왔고 공유 damage GE는 동일 hash였다. 현행 Source/Config baseline은 `MainSourceBaselineAfterCollision.json`이다. 이전 collision 초안을 덮어쓰지 않는다.

첫 author preflight는 Apes DefaultSlot 부재로 저장 전에 실패했다. 필요한 두 Skeleton 슬롯만 등록하는 Art 수정 후 authoring78 packages와 body authoring7 packages가 실제 성공했다. 클립49개(첫47+idle2)는 기존 시간/root 옵션을 복제해 재사용했다. Body는 Apes/Yetuga에 최소 gameplay BP·기존 UKZAnimInstance 기반 ABP·registry entry를 연결하는 작업이며 AI 공격 패턴·맵 배치를 추가하지 않는다. 두 종류도 native 소진/피격을 시험할 수 있는 실제 actor가 된다. 기록은 `Authoring.json`, `BodiesAuthoring.json`이며 아직 Main 전달/PIE 성공은 아니다.

플레이어 montage Front/Back은 저장 후 별도 로드에서 autoBlendOut=true와 길이 3.6166665554/3.6333334446초를 직접 확인했다. 독립 수명의 Task OnCompleted를 사용한다. 이전 몬스터의 늦은 cleanup이 같은 InstancedPerActor 플레이어 Ability의 새 다른 피해자를 취소하지 않도록 `AbortFromVictim(NotifyingVictim)`는 현재 VictimAbility와 동일한 caller만 처리한다. 실제 이전 피해자를 이용한 회귀 fixture를 추가했다.

PIE fixture의 Montage_IsActive는 blend-out 시작에 false가 될 수 있으므로 Task 완료 증거와 동등하지 않다. 이를 실제 montage instance lifetime으로 보완 중이며 테스트 수정 뒤 재컴파일·실제 실행해야 한다. 제품 양쪽 완료 gate는 이미 실제 Task OnCompleted만 사용한다.

## 2026-10-08 — 실제 Main 반영·검증 완료와 사용 방법

이 절이 앞선 작업 중·PIE 시작 전 상태를 갱신한다. 몬스터6의 스태미너 정책, 소진, 플레이어 앞/뒤 브루탈 어택과 취소·사망 정리를 실제 Main Source와 저장 에셋에 반영했다. 격리 Work의 native 통합 검사453개와 기존 회귀5종이 모두 통과했고, 임시 author/test helper를 제거한 stock editor build 및 별도 fresh Main의 저장 에셋·로드 모듈 확인도 완료했다. 아래의 런타임 검사는 Work PIE 결과이며, fresh Main 검사는 읽기 전용 saved readback이다.

### 실행 책임과 추가 파일

새 runtime 클래스는 다음 두 개, h/cpp 네 파일이다. 기존 ASC/AttributeSet/CharacterDefinition/ComboAction/Locomotion/AIController와 엔진 MontageTask를 재사용한다.

| Main 파일 | 실제 책임 |
| --- | --- |
| `Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.h`, `.cpp` | 피해자의 Start/Loop, 피격 Damage1/2, 유한 timer, End 회복, 양쪽 완료 gate와 자기 Task·제약·partner 정리. |
| `Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.h`, `.cpp` | 기존 입력의 유효 타깃 선택, 앞/뒤 결정과 정렬, 플레이어 몽타주, 실제 타격 notify·총 HP 피해, 자기 실행 종료. |

`AKZMonster::BindCombatAttributes/RequestCombatStateRefresh/RefreshCombatState`는 실제 ASC의 HP·Stamina 변경을 다음 tick으로 모아 HP0 사망을 Stamina0 소진보다 먼저 처리한다. 같은 GE의 modifier 적용 순서에 따라 사망자가 회복되는 문제를 막는다. `State.Exhausted`와 `State.Dead`는 ASC가 소유하며, Ability 내부 phase는 해당 실행의 순서만 관리한다. AI/AnimInstance의 별도 소진 상태 사본이나 새 manager/FSM은 추가하지 않았다.

Main 선택 전달은 runtime Source15개·기존 DEV 테스트1개·에셋89개, 합계105개다. Source15에는 이전 미전달 NPC 회전/보간 변경의 병합도 포함된다. 이를 소진 기능이 runtime 파일15개를 새로 생성한 것으로 해석하지 않는다. 정확한 파일별 before/after SHA는 `Metadata/MonsterStamina_20261008/DeliveryReceipt.json`의105개 rows에 있다.

### 몬스터 전용 자원 정책

여섯 몬스터의 Definition `InitialEffects`에 `/Game/Monsters/Effects/GE_MonsterStaminaPolicy`를 부여했다. 이 Infinite GE가 `Block.StaminaRegen`을 유지한다. 소진이 끝나 자기 Owned tag를 반환해도 이 별도 정책은 남으므로 평상시 자동 회복이 다시 시작되지 않는다. 초기 HP/MaxHP/Stamina/MaxStamina는 기존 각 몬스터의 `GE_Init_<family>`가 계속 맡는다.

기존 몬스터 공격 BP35개의 `CostGameplayEffectClass`와 `OnEndAbilityGameplayEffect`를 비워 공격 비용·공격 종료 후 회복을 제거했다. HP/Stamina 자체를 다른 변수로 복제하거나 공통 Player 비용을 일괄 끄지 않았다. Player Definition의 기존 초기 효과·회복·일반 공격 비용은 유지하며, 브루탈 실행 중에만 그 Ability가 자기 `Block.Movement.Input`과 `Block.StaminaRegen`을 소유한다. 원작 전체 적의 자원 규칙을 확인한 결과가 아니라 이번 사용자의 monster-only 정책이다.

### 에디터에서 조정할 정확한 위치

Content Browser에서 아래 Data Asset을 열고 **Character → Monster Stamina**의 `MonsterStamina` 설정을 펼친다. 표의 값은 `MainSavedReload.json`에서 실제 저장본을 다시 읽은 값이다.

| 몬스터 | CharacterDefinition 에셋 경로 | `ExhaustionSeconds` (s) | `BrutalAttackRange` (cm) |
| --- | --- | ---: | ---: |
| Swordsman | `/Game/Monsters/Swordsman/Data/DA_Character_Swordsman` | 5 | 180 |
| SwordShield | `/Game/Monsters/SwordShield/Data/DA_Character_SwordShield` | 5 | 180 |
| HeavySwordsman | `/Game/Monsters/HeavySwordsman/Data/DA_Character_HeavySwordsman` | 5 | 180 |
| HalberdElite | `/Game/Monsters/HalberdElite/Data/DA_Character_HalberdElite` | 5 | 180 |
| ApesStoneHandElite | `/Game/Monsters/ApesStoneHandElite/Data/DA_Character_ApesStoneHandElite` | 5 | 260 |
| Yetuga | `/Game/Monsters/Yetuga/Data/DA_Character_Yetuga` | 8 | 400 |

모두 `bEnabled=true`, `ParryStaminaDamage=5`, `BrutalHPDamage=0`, `BrutalAlignmentDistance=0`으로 저장했다. 실제 C++ 구조는 `Source/Khazan/Data/KZCharacterDefinitionData.h`의 `FKZMonsterStaminaSettings`다.

| 설정 | 편집 의미 |
| --- | --- |
| `ParryStaminaDamage` | 성공 패링 보고 한 번당 공격자에게 적용할 절대 Stamina 감소량. 현재5는 사용자 조정값이며 원작 ratio의 환산값이 아니다. |
| `ExhaustionSeconds` | 소진 활성화 때 Start를 포함해 시작하는 유한 timer의 초 단위 시간. 0이면 timer 없이 Start/Loop에서 브루탈 어택을 기다린다. paired 실행 동안 남은 시간을 정지한다. |
| `BrutalHPDamage` | `BrutalHit2`에 적용할 총 절대 HP 피해량. 앞/뒤 모두 이 몬스터 설정을 읽는다. 현재 미지정0이므로 모션·소진 회복은 실행되지만 브루탈 자체의 HP 감소는 없다. |
| `BrutalAttackRange` | 타깃과 Player actor 위치 사이 3D 탐색 거리. 180/260/400cm는 원작 거리 미확인의 크기 기반 임시 튜닝값이다. |
| `BrutalAlignmentDistance` | 정렬 간격(cm). 0이면 양쪽 live capsule 반경 합을 최소 간격으로 사용하고, 양수 설정도 그 반경 합보다 작게 정렬하지 않는다. |
| `ExhaustionMontage` | 실제 `/Game/Monsters/<family>/Animations/AM_Exhaustion`의 Start/Loop/End section. |
| `BrutalFront/BackPlayerMontage` | `/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalFront`, `AM_DAS_BrutalBack`. |
| `BrutalFront/BackVictimMontage` | `/Game/Monsters/<family>/Animations/AM_BrutalVictimFront`, `AM_BrutalVictimBack`의 Damage1/2 section. |
| `DamageEffect`, `DeadStateEffect` | 공통 `/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage`, 몬스터 `/Game/Monsters/Effects/GE_DeadState`. |

일반 공격의 피격별 소진량은 위 `ParryStaminaDamage`나 `BrutalHPDamage`가 아니다. `/Game/Data/ComboCommand/DA_Player_Combo_Definition` → `Nodes` → 원하는 `Node Id` → `Attack Windows` → 각 원소의 `StaminaDamage`를 편집한다. 같은 위치의 `HPDamage`는 그 적중의 HP 피해량이다. 실제 경로는 `FKZComboNode::AttackWindows[]`의 `FKZAttackCollisionWindow::StaminaDamage/HPDamage`이며 `Source/Khazan/Ability/Combo/KZComboDefinitionData.h`에 있다. 시간·shape·HitGroup·원작 출처는 [공격 collision 현행 정본](PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md)을 따른다. 이번 소진 기능은 그 기존 판정/GE가 적용한 수치 결과를 관측하며 공격 판정을 다시 구현하지 않는다.

유한5/8의 원본 근거는 CS export의 `Properties.StaminaStatus[]`, `Key=EStateBattleStance::Battle` → `Value.StaminaExhaustionInfo.StaminaExhaustionTerm`이다. 인간형4 원본 JSON은 `Metadata/EnemyStaminaResearch_20261008/TargetedOriginal_01/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/` 아래 각 CS이며 `TargetedFindings.json`에 package/file/SHA가 있다. Apes는 `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip`의 `BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/Base_Setting/CS_ApesStoneHand_E.json` export0 값5, Yetuga는 `Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip`의 `BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Base_Setting/CS_Yetuga.json` export0 값8이다. 정확한 기록은 `StatusAndHoldingSupplement.json`의 `stored_status_profiles`다. 이를 초로 채택했으나 원작 native timer 시작 지점·paired pause·완료 후 현재 Max 충전은 직접 확인하지 못했으며 이번 프로젝트 계약과 구분한다.

현재5/8초 설정에서는 **브루탈 어택을 하지 않아도** 유한 시간이 만료되면 End 회복 모션을 시작하고, 살아 있는 End의 실제 완료 뒤 현재 MaxStamina로 충전한다. paired 실행 중에는 만료되지 않는다. 반대로0은 자동 timeout 회복이 없는 무기한 소진이며, 정상 브루탈 완료 또는 사망/외부 수명 정리까지 기다린다.

### X 앞/뒤 실행과 양쪽 완료

Player의 `/Game/Data/Character/DA_CharacterDefinition_Player` → `InitialAbilityGrants`에 native `/Script/Khazan.KZBrutalAttackAbility`를 기존 `Input.Action.X`로 부여했다. 새 물리 입력 타입을 만들지 않았다. `UKZAbilitySystemComponent::AbilityInputTagPressed`는 해당 입력의 비활성 Brutal grant를 먼저 시도하고 유효 타깃/활성화가 없으면 기존 일반 X 경로로 돌아간다. 명시한 Spec Handle 요청은 기존 의미를 유지한다.

1. 살아 있는 몬스터의 Stamina가0이 되면 기존 공격을 취소·차단하고 Exhaustion Start→Loop를 재생한다. `State.Exhausted`·입력 차단·VelocityDirection 회전 제약을 소유한다. 유한 시간 만료도 아래 End 회복 과정을 거친다.
2. Player가 지상에서 유효 몬스터를 향해 X를 누르면 전방 반공간·설정 거리·Visibility를 만족하는 가장 가까운 소진 대상을 선택한다. 이미 partner가 있거나 End 회복 중인 대상은 제외한다. 몬스터 forward와 Player 상대 위치의 dot 부호로 앞/뒤를 시작 때 결정하며 실행 중 다시 바꾸지 않는다.
3. 현재 양쪽 capsule과 `BrutalAlignmentDistance`로 정렬할 공간을 확인하고 대상을 claim한다. 유한 timer의 남은 시간은 pause하며 첫 타격 전에는 기존 Start/Loop를 유지한다. 플레이어 앞/뒤 몽타주와 자기 입력/회전 제약을 실행한다.
4. 해당 플레이어 montage instance의 실제 `BrutalHit1`은 피해자 Damage1, `BrutalHit2`는 Damage2와 설정 총 HP 피해 GE를 한 번 실행한다. notify별 중복 guard와 instance/asset 검사를 사용한다. 기존 retimed 클립의 시간·root 설정을 재사용하며 길이를 맞추기 위해 몬스터 피격 모션을 임의 배속하지 않았다.
5. 피해자 Damage1 종료는 회복 완료가 아니다. 플레이어의 정상 MontageTask `OnCompleted`와 피해자 Damage2의 실제 Task `OnCompleted`가 모두 모이고 HP>0·Dead tag 없음일 때만 소진 End를 시작한다. End의 실제 완료 시 **그 시점의 현재 MaxStamina**를 읽어 Stamina를 한 번 설정하고 자기 태그/제약을 반환한다. 타격 notify, blend-out 시작, 둘 중 먼저 끝난 한 Task만으로 회복하지 않는다.

HP0이면 회복·refill을 하지 않는다. paired lethal에서는 Dead GE로 gameplay를 차단하되 partner가 남은 동안 피격 presentation을 조기에 취소/고정하지 않고, 양쪽 완료와 자기 montage cleanup 뒤 `AKZMonster::FinishDeathPresentation()`으로 마지막 피해자 포즈를 고정한다. unpaired HP0/Stamina0은 death를 우선한다.

취소·실패는 즉시 최대치 회복을 하지 않는다. 살아 있는 paired 취소는 partner를 먼저 끊고 소진 Loop와 유한 timer의 남은 시간으로 돌아가며,0 설정은 계속 무기한이다. 외부 소진 취소 뒤에도 possessed/alive/Stamina0이면 Monster의 기존 refresh 경로가 소진을 다시 시도한다. UnPossess/EndPlay는 attribute 구독·timer·notify·Task callback·자기 constraint를 정리하고 unbound actor의 재진입을 막는다. 이전 피해자의 늦은 종료가 같은 InstancedPerActor 플레이어 Ability의 다른 새 pair를 취소하지 않도록 `AbortFromVictim(NotifyingVictim)`는 실제 현재 피해자 일치도 확인한다.

### 실제 검증과 Main 전달 근거

아래 파일은 모두 `Metadata/MonsterStamina_20261008/` 아래에 보존했다.

| 근거 | 확인 결과와 범위 |
| --- | --- |
| `NativePIE.json`, `NativePIE_IntegratedSuccess.log` | Work 실제 PIE `success=true`,453 checks·실패0. 실제6종 BP/Definition, GE 피격/패링 hook, no-regen·공격 CDO audit/인간형 실제 공격, 유한 timeout·현재 Max 변경 후1회 refill, 앞/뒤 actual notify/Task, 이전 실제 피해자의 late-abort,0무기한·취소·재진입·UnPossess·EndPlay·paired/unpaired 사망을 확인했다. |
| `IntegratedRegression.json`와 각 `Regression_*.log` | `Khazan.Monster.FacingPIE`, `Khazan.Monster.CombatPolicyPIE`, `Khazan.Guard.PIE`, `Khazan.Heal.PIE`, `Khazan.Combat.PlayerAttackCollision.PIE` 모두 실제 `Test Completed. Result={Success}`. Collision은 최신 Main 공격 클립 intake 뒤 마지막 재검사 성공 기록을 사용한다. |
| `StockDeliveryBuild.log`, `StockDeliveryBuild.json` | 임시 helper 제거 후 stock `KhazanEditor Win64 Development` 빌드 `Result: Succeeded`. JSON 파일은 UBT JSON-lines 로그이며 단일 receipt JSON이 아니다. |
| `DeliveryReceipt.json` | `complete=true`, Main105개 선택 전달/hash, `canonical_dll_preserved=true`, `loaded_user_editor_reloaded=false`. 새 alias DLL과 manifest를 선택 전달했으며 사용자 실행 editor를 reload/재시작하지 않았다. |
| `MainSavedReload.json` | 마지막 별도 fresh Main commandlet PID16924의 읽기 전용 결과 `success=true`. 몬스터 Definition6·Player Definition1·Montage20·Sequence copy49·공격 BP35·신규 body2를 재로드했으며 `dirty_content=[]`, `dirty_map=[]`이다. 기존 Facing readback도 재사용해 Combat BS4의6/10/10/5·BP/ABP 저장 상태·CMC root 회전 flag·현행 AI 회전 설정을 확인했다. |
| `FinalVerification.json` | `complete=true`,453 checks·실패0·회귀5·전달105 rows·fresh Main saved reload 완료를 종합한다. 전달 외 Source/Config82개와 에셋138개 보존, canonical DLL 보존, editor helper 제외도 확인했다. |

fresh Main이 실제 로드한 모듈은 `Binaries/Win64/UnrealEditor-KhazanStamina20261008-70158bc21dbb.dll`, SHA256 `70158bc21dbbb65c9090e4f749ef2560aebcb347c448ad9a9b9be0af2ff3fe18`로 DeliveryReceipt와 일치한다. 기존 canonical `UnrealEditor-Khazan.dll`은 보존했다. 정상적으로 프로젝트를 새로 열면 전달된 manifest의 새 모듈을 사용한다. 저장본·로드 모듈 확인을 사용자 물리 패드/화면 전투까지 검증한 것으로 확대하지 않는다.

첫 native 실패18개는 모든 family의 회복 후 `IsMovementInputAllowed` 검사였다. 초기 full Stamina에서도 false였고 fixture가 Definition 준비 뒤 첫 Controller Tick 전에 AI Tick을 꺼 실제 intent source 바인딩을 생략한 것이 원인이었다. StateTree가 있는4종은 기존 public `Controller->Tick(0.f)` 초기화를 거친 뒤 AI를 중지했다. StateTree가 없는2종은 fixture가 public `BeginLocomotionIntentSource`의 실제 handle을 소유하고 UnPossess/Destroy/reset 전에 반환했다. 초기 이동 허용 assertion을 추가했으며 기존 회복 조건을 완화하거나 제품 이동 gate를 수정하지 않았다.

453개 검사에서 양수 브루탈 피해 경로는 원본 설정0인 뒤 공격에만 transient Definition 복사본의 `BrutalHPDamage=현재 HP/16`을 사용했다. 이는 QA 파생값이고 authored DA0을 유지했다. 실제 HP 감소와 설정 총량1회 일치를 확인하여 중복 피해도 검출한다. Task 완료 순서 증거는 실제 Damage2 instance ID를 잡아 blend-out까지 `GetMontageInstanceForID` 잔존 여부와 플레이어 Ability 종료를 함께 관측했다. 같은 sample에서 둘 다 끝난 경우 정확한 callback 선후를 단정하지 않는다. 완료 flag나 montage timing을 가짜로 조작하지 않았다.

### 남은 범위와 다음 사용

- `ReportAttackParried(Defender)`의 유효 성공 보고가 Stamina5를 감소시키는 hook과 편집값 반영은 통과했다. 현재 Monster→Player 실제 적중·패링 판정 생산자는 아직 연결되지 않았으므로 물리적 패링 성공의 전체 경로 완료를 뜻하지 않는다. 정상 `TryGuardHit` 성공을 패링으로 바꾸지 않았다.
- cinematic lethal Execution, 카메라/무기 전환 연출, 원작 전체 hit ratio/최종 피해 공식은 이번 구현에 포함하지 않았다. `BrutalHPDamage`는 사용자 피해량 결정 후 해당 몬스터 DA에서 조정한다.
- `/Game/Bluprints/Monsters/BP_Monster_ApesStoneHandElite`, `BP_Monster_Yetuga`는 실제 Definition/ASC·소진·피격·브루탈용 body/ABP·registry 연결을 갖추었지만 autonomous StateTree/공격 패턴·맵 배치는 없다. 두 종류의 fixture-owned intent를 자율 AI 구현 완료로 설명하지 않는다. 실제 인간형4종 AI의 Pause/Resume 코드는 유지했으나 소진 fixture는 자율 판단을 중지하므로 그 판단 진행 전체까지453개 검사 범위로 확대하지 않는다.
- 유한 paired 취소 후 남은 timer 재개는 현재 Source에서 확인한 계약이다. 실제 취소 fixture는0무기한 설정을 사용했으므로 유한 취소의 wall-clock 전체 검증까지 완료했다고 기록하지 않는다.
- 다음 사용은 새 Main DevMap에서 기존4종을 공격해 Stamina0→앞/뒤 X→End 회복을 확인하고, 미배치 신규2종은 위 정확한 BP를 배치해 body/접촉 높이·정렬·모션을 확인하는 것이다. 자동회복·공격 비용 정책과 피격별 `AttackWindows[].StaminaDamage`, 패링 hook, 브루탈 HP 피해 설정은 각각의 위 소유 경로에서 조정한다. 기존 authoring·retime·전체 리소스 조사나 전달 helper를 반복 실행할 필요는 없다.

## 2026-10-08 17:34 KST — 공격 BP 감사 표현 보충

위 “기존 몬스터 공격 BP35개의 CostGameplayEffectClass와 OnEndAbilityGameplayEffect를 비워”라는 표현은 결과 정책을 설명한 것이다. 정확한 작업 이력은35개가 이미 None인 것을 감사해 확인했고 해당 공격 BP는 이번에 저장/수정하지 않았다는 것이다. `Authoring.json.monster_attack_audits`와 Main saved readback의35개 검사 및 보호 asset hash가 근거다. 새 Infinite 정책 GE가 평상시 regeneration을 차단하는 실제 변경과 기존 Cost 없음의 검증을 구분한다.


<!-- MonsterStaminaConcurrentMainBuildVerified_20261008 -->
## 2026-10-08 17:39 KST — 후속 Main 기본 DLL 빌드 보존·재검증

전달 완료 뒤 본 작업이 시작하지 않은 Main native build가 새 canonical DLL과 manifest를 만들었다. 해당 build는 Succeeded이고 선택 모듈은 현재 `UnrealEditor-Khazan.dll`, SHA `3a2b4942da22fdf94cc7cf6581da3b5fb04f63475315c675d66ef6c4782e758d`다. 이전 unique alias 전달·canonical 보존은 당시 사실이며 현재 모듈 선택을 과거 alias로 되돌리지 않았다. 전달105행과 전체 Source/Config가 검증한 현재 구현과 동일한 것을 확인했다.

별도 fresh Main commandlet에서 현재 canonical DLL을 실제 로드해 저장 Definition6+Player1/montage20/sequence49/attackBP35/body2 및 NPC4 BS·CMC/AI CDO·dirty0를 다시 확인했고 exit0으로 종료했다. 증거는 Metadata/MonsterStamina_20261008/{ConcurrentMainRebuild,FinalVerification_CurrentMain,MainSavedReload_ConcurrentBuild}.json과 ConcurrentMainBuild.log다. 이 새 DLL에서 native453/회귀5종을 다시 실행한 것은 아니며 동일한 제품 Source의 이전 Work runtime 결과와 새 Main saved readback을 구분한다. 사용자 Main19576은 읽기 inventory로만 확인했으며 제어·PIE·저장·종료하지 않았다. 이제 현재 Main 기본 DLL을 사용하고 과거 전달/authoring helper를 재실행하지 않는다.


<!-- MonsterBrutalDamage50_20261008 -->
## 2026-10-08 19:48 KST — 브루탈 어택 총 HP 피해 임시50 설정

사용자 요청으로 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga의 `/Game/Monsters/<family>/Data/DA_Character_<family>` → Monster Stamina → `BrutalHPDamage`를0에서50으로 저장했다. 단위는 HP 절대량이고 원작 환산값이 아닌 사용자 지정 임시 튜닝이다. 앞/뒤 공통 브루탈1회당 총량이며 기존 `BrutalHit2`에서 한 번 적용한다. 패링·일반 공격의 Stamina 감소량과는 별개다. 이전 미할당0/조건부혈흔0 기록은 당시 검증 상태로 보존하며 현재 설정은 이 절의50을 따른다.

수정은 CharacterDefinition6개의 해당 필드뿐이다. 다른 stamina 설정·LocomotionConfig·UnawareRoutines·InitialAbilityGrants·InitialEffects를 수정 전후 및 새 별도 Main commandlet 재로드에서 동일하게 확인했다. Source/런타임 클래스/몽타주/모듈 선택은 편집하지 않았다. metadata 증거는 `Metadata/MonsterBrutalDamage50_20261008/Authoring.json`, `FreshSavedReadback.json`이며 원본6파일은 같은 경로 Before에 보존했다. 두 commandlet은 별도 프로세스로 성공 종료했고 사용자 에디터를 제어하지 않았다.

이번 검증은 저장된 값50과 다른 필드 보존의 읽기 검사다. 기존 양수 피해/중복 방지/양쪽 완료 native 검사와 VFX transient6.25 검사는 과거 결과이며50으로 PIE를 새 실행한 것으로 기록하지 않는다. 기존 확정 적중을 읽는 VFX 정책은 이제 실제 양수50 피해에 적용될 수 있으며 VFX가 추가 피해를 만들지 않는다. 조정은 같은 DA의 BrutalHPDamage에서 수행하고, 과거0인 author receipt/asset payload를 현재 설정 위에 다시 전달하지 않는다.
