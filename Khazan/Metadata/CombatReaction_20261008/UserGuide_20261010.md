# 피격·가드 성공·브루탈 어택 사용 설명

## 2026-10-10 작성 시점의 적용 상태

이 문서는 **현재 MonsterWork에 실제 구현한 동작**을 설명한다. Main에 이번 변경을 전달하기 전 작성한 사용 설명 초안이다. Main 완료 여부는 후속 날짜별 절과 최종 전달·fresh readback receipt로 판단한다. 기존 문서의 과거 적용 상태를 덮어쓰지 않는다.

Work의 마지막 실제 RHI 검사는 일반 피격32case·브루탈15case·Monster→Player 충돌3case를 통과했다. Guard·Heal·PlayerAttackCollision 회귀도 통과했다. Heavy의 기존 CombatPolicy 회귀 timeout 조사가 남아 있으며, stock 빌드·새 Work 저장 재로드·Main 선택 전달·새 Main 저장 재로드는 아직 완료로 기록하지 않는다. 근거는 [NativePIE_Final.json](NativePIE_Final.json), [재개 감사](ResumeDriftAudit_20261010.json), [Engineering continuity](../../Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md)의 2026-10-10 절이다.

새 runtime 클래스는 공통 `UKZHitReactionAbility` 하나다. 신규 h/cpp2개와 기존14개, 총16파일의 변경으로 기존 CharacterDefinition·ASC event·Combo collision·GAS Task·Locomotion constraint·Exhaustion/Brutal 수명을 사용한다. 별도 피격 Manager나 상태 머신은 추가하지 않았다. 임시 author2개와 native test1개는 제품 전달 대상이 아니다.

## 먼저 에디터에서 열 대상

Content Browser의 `/Game`은 프로젝트 디스크의 `Content`에 대응한다. 아래 경로는 **DataAsset 에셋 경로**다.

| 캐릭터 | CharacterDefinition |
| --- | --- |
| Player | `/Game/Data/Character/DA_CharacterDefinition_Player` |
| Swordsman | `/Game/Monsters/Swordsman/Data/DA_Character_Swordsman` |
| ShieldMan의 실제 family인 SwordShield | `/Game/Monsters/SwordShield/Data/DA_Character_SwordShield` |
| HeavySwordsman | `/Game/Monsters/HeavySwordsman/Data/DA_Character_HeavySwordsman` |
| HalberdElite | `/Game/Monsters/HalberdElite/Data/DA_Character_HalberdElite` |
| Apes | `/Game/Monsters/ApesStoneHandElite/Data/DA_Character_ApesStoneHandElite` |
| Yetuga | `/Game/Monsters/Yetuga/Data/DA_Character_Yetuga` |

Definition의 Details에서 `Character → Hit Reactions`를 펼친다. `Short Hits`, `Knockbacks`, `Launches`가 이번 일반 피격 후보 배열이다. C++ 이름은 각각 `ShortHits`, `Knockbacks`, `Launches`다. `Shield Blocks`는 SwordShield의 방패 성공 반응 배열이며 Player Guard 성공 배열과 별개다. `Initial Ability Grants`에는 공통 native HitReaction이 부여되어 있다. 새 피격 BP Ability를 종마다 따로 만드는 구조가 아니다.

공격 종류를 바꿀 때는 공격자의 ComboDefinition을 연다. Player는 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`이고, 몬스터는 `/Game/Monsters/<family>/Data/DA_Combo_*`다. `Nodes → 해당 노드 → Attack Windows → 해당 원소 → Hit Reaction`에서 `None / Short / Knockback / Launch`를 선택한다. 배열 제목에도 종류가 표시된다. `HP Damage`, `Stamina Damage`, `Blockable`은 같은 원소의 별도 설정이다. 피격 종류를 바꿨다고 피해량까지 바뀌지는 않는다.

## 일반 피격이 재생되는 순서

기존 `UKZComboActionAbility::QueryAttackCollision`이 공격 window의 형상과 실제 재생 시간을 사용해 접촉을 확인한다. Player→Monster와 Monster→Player만 소비하며, 한 window/hit group에서 중복 적중하는 기존 방지를 유지한다. 방어가 성공했으면 그 접촉은 Guard/SystemGuard 경로로 끝난다. 방어되지 않았고 피해 GameplayEffect 적용이 승인되었으면 공격 window의 `HitReaction`을 피해자에게 전달한다. 승인된 0 피해 접촉도 종류가 None이 아니면 반응할 수 있다.

피해자는 `AKZCharacter::PlayHitReaction`에서 생존·소진 상태를 확인하고 자기 ASC에 정확한 피격 event를 보낸다. 아래는 Work에 적용한 현재 함수다.

```cpp
void AKZCharacter::PlayHitReaction(const EKZHitReactionType Type, AActor* Attacker)
{
    if (!HasAuthority() || Type == EKZHitReactionType::None || !IsValid(Attacker) ||
        !AbilitySystemComponent || AbilitySystemComponent->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f ||
        AbilitySystemComponent->HasMatchingGameplayTag(KZGameplayTags::State_Dead) ||
        AbilitySystemComponent->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) ||
        (IsA<AKZMonster>() && AbilitySystemComponent->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) <= 0.f)) return;
    FGameplayEventData Event;
    Event.Instigator = Attacker;
    Event.Target = this;
    Event.EventTag = Type == EKZHitReactionType::Launch ? KZGameplayTags::Event_Combat_Hit_Launch :
        (Type == EKZHitReactionType::Knockback ? KZGameplayTags::Event_Combat_Hit_Knockback : KZGameplayTags::Event_Combat_Hit_Short);
    AbilitySystemComponent->HandleGameplayEvent(Event.EventTag, &Event);
}
```

`Type`은 공격 데이터에서 받은 반응 선택값이고 값 타입으로 전달한다. `Attacker`는 공격자 Actor 포인터다. 반응의 출처와 물리 이동 방향에 쓰며 랜덤 포즈 선택 방향을 정하지 않는다. 첫 분기는 None·유효하지 않은 공격자·ASC 없음·HP0·Dead·Exhausted를 거절한다. 마지막 Stamina0 조건은 몬스터만 검사한다. 플레이어의 Stamina0을 몬스터 넉다운 정책으로 처리하지 않는다.

`FGameplayEventData`는 이 호출에서 만든 지역 payload다. `Instigator`는 공격자, `Target`은 피격 캐릭터다. `EventTag`는 요청한 종류에 해당하는 정확한 event를 선택한다. `HandleGameplayEvent`가 이미 부여된 HitReactionAbility를 실행한다. 이 함수는 피해량을 추가로 깎거나 별도 상태 bool을 만들지 않는다. gameplay·선택·Task callback은 게임 스레드에서 수행하며 AnimInstance worker에 ASC 조작을 맡기지 않는다.

`UKZHitReactionAbility::SelectMontage`는 선택한 종류 배열에서 null을 제외한 유효 원소 수를 세고 `FMath::RandHelper(Count)`로 한 원소를 고른다. 종류 배열이 비어 있으면 `ShortHits`로 fallback한다. Short까지 비어 있으면 실행하지 않는다. 배열 원소별 확률이 같으므로 같은 몽타주를 중복 등록하면 그 몽타주의 비중이 커진다. 현재 랜덤 선택은 **한 피격 실행을 시작할 때 한 번** 수행한다.

반응 실행 중에는 `State.HitReacting`과 기존 입력·Stamina regen 제한을 소유한다. 기존 Action을 취소하고 새 Action을 차단한다. 재피격은 현재 반응을 정리하고 새 반응을 시작할 수 있다. HP0/몬스터 Stamina0이면 일반 반응보다 기존 사망/Exhaustion 처리가 우선한다. 몬스터 AI는 기존 incapacitation Pause/Resume를 사용하며 전투 타깃을 버리는 새 상태를 만들지 않는다.

## 세 종류와 실제 지원 범위

| 캐릭터 | Short | Knockback | Launch |
| --- | --- | --- | --- |
| Player | 14후보 | F/B 2후보, Down→Loop→Getup | F/B 2후보, Up→Loop→Getup |
| Swordsman | 8후보 | F/B 2후보, Down→Loop→Getup | F/B 2후보, Up→Peak→Down→Land→Loop→Getup |
| SwordShield | 4후보 | F/B 2후보, Down→Loop→Getup | F/B 2후보, Up→Peak→Down→Land→Loop→Getup |
| HeavySwordsman | 4후보 | F/B 2후보, Down→Loop→Getup | Launch pool 없음: Short 랜덤 fallback |
| HalberdElite | 4후보 | F/B 2후보, Down→Loop→Getup | 원본 AP의 F/B 2후보, Up→Peak→Down→Land→Getup |
| ApesStoneHandElite | 4후보 | 원본 NoBlowDamage 지정 Grapple_Atk_02 대체 1개 | 원본 NoAirDamage 지정 동일 대체 1개 |
| Yetuga | 4후보 | 원본 NoBlowDamage 지정 Grapple_Atk_02 대체 1개 | 원본 NoAirDamage 지정 동일 대체 1개 |

Short는 짧은 포즈 반응이다. Player의 원본 파일명 `DamageWeak / DamageNormal / DamageStrong`은 현재 모두 Short 후보에 정리되어 있다. 그 이름이 프로젝트의 Short/Knockback/Launch 세 종류를 자동으로 결정하지 않는다.

Knockback은 물리적으로 뒤로 밀린 뒤 Down→Loop→Getup을 완료한다. 일반 DownLoop는 몽타주 segment만 0.3초로 잘라 사용한다. **0.3초는 어시스턴트 임시 prone hold**다. 원본 Loop 시퀀스의 전체 길이·키·RateScale은 변경하지 않았다. 기존 Stamina0의 Exhaustion Loop도 이 값으로 자르지 않았다.

Launch는 해당 몸의 원본 상승/정점/하강/착지/회복 클립 순서를 사용한다. Player 원본은 짧은 Air 상승 클립→DownLoop→Getup 형태이며 인간 몬스터의 6단계 구조를 억지로 복제하지 않았다. Heavy에는 확인한 segmented Air 자료가 없어 Short fallback을 사용한다.

Apes/Yetuga의 `NoAirDamage / NoBlowDamage`는 bool 면역 필드가 아니라 원본 AP의 대체 애니메이션 참조다. 두 종류 모두 해당 종의 정확한 `Damage_Grapple_Atk_02` 단일 Hit 몽타주를 재생한다. 이 대체 반응에는 인간형 Launch의 Flying/RootMotionSource를 추가하지 않는다. 기존 애니메이션 root가 가진 수평 이동은 보존한다. 따라서 Giant의 Launch 요청을 받았다고 사람처럼 공중으로 날리는 구현은 아니다.

원본 이름의 F/B/L/R은 후보의 포즈 식별이다. 공격이 왼쪽에서 들어왔다고 L 포즈를 고르는 분기는 없다. 반면 **실제 밀리는 방향**은 피해자 위치−공격자 위치를 XY 평면에서 normalize한 away vector를 사용한다. 둘이 겹쳐 방향을 얻지 못하면 피해자의 뒤쪽을 사용한다. 랜덤 포즈와 물리 방향을 의도적으로 별도 입력으로 취급한다.

## 날림과 회복의 이동·재생 시간

해당 Player Air와 일부 인간형 클립은 true root가 이동하지 않는 in-place 포즈였다. 스켈레톤 root를 수리하거나 Bip001의 포즈 이동을 root로 옮기지 않았다. 필요한 world 이동은 HitReaction 실행이 엔진 `UAbilityTask_ApplyRootMotionJumpForce`의 RootMotionSource로 소유한다.

| 조절 필드 | 현재 값 | 단위·출처 | 효과 |
| --- | --- | --- | --- |
| `KnockbackDistance` | 250 | world cm, 어시스턴트 임시 튜닝 | 지원하는 Knockback 체인의 수평 목표 이동량 |
| `LaunchDistance` | 120 | world cm, 어시스턴트 임시 튜닝 | 지원하는 Launch 체인의 수평 목표 이동량 |
| `LaunchHeight` | 150 | world cm, 어시스턴트 임시 튜닝 | 지원하는 Launch의 수직 곡선 높이 |
| 일반 `DownLoop` segment crop | 0.3 | 초, 어시스턴트 임시 튜닝 | 쓰러진 뒤 짧게 유지하는 몽타주 segment; RMS duration과 별개 |

이 값은 원작 절대 거리/높이를 직접 확인한 수치가 아니다. Definition의 `Hit Reactions`에서 종별로 조절한다. 물리 이동 duration은 현재 몽타주의 실제 위치부터 `HitLand`까지의 시간을 실제 play rate로 나눈 값이다. `HitLand`가 없으면 Getup 시작을 사용한다. 임의의 별도 이동 timer 길이를 넣지 않는다. Knockback의 HitLand는 Loop 시작이어서 prone hold와 기상 동안 계속 밀리지 않는다.

원본 root와 RMS를 동시에 더하지 않도록 자기 force 중에만 AnimInstance의 이전 root-motion mode를 보존하고 `IgnoreRootMotion`을 사용한다. 지원하는 Launch의 Up 구간에서는 필요한 경우 CMC Flying을 소유한다. 착지 Notify·완료·취소에서 자기 Task/constraint/mode를 정리하며 다른 원인이 바꾼 값을 무조건 덮어쓰지 않는다. 복귀는 몽타주 전체 실제 완료를 기준으로 한다. BlendOut 시작을 기상 완료로 오인하지 않는다.

Player mesh의 0.01 scale을 world 거리나 초에 다시 곱하지 않는다. 위 250/120/150은 actor/capsule 좌표의 cm다. 클립 raw·기존 재생률도 보존한다. 벽과 바닥 충돌 때문에 실제 이동량은 목표보다 줄어들 수 있으므로 조정할 때 실제 capsule 경로와 착지를 함께 확인한다.

## Player Guard 성공

기존 `/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard`를 재사용한다. Guard montage는 `/Game/_Art/Player/Animation/InGame/DAS/Guard/AM_DAS_Player_Guard`다. 성공 section `Suc_F / Suc_L / Suc_R` 중 하나를 기존 `UKZGuardAbility::TryGuardHit`의 RandHelper로 균등 선택한다. 해당 클립은 같은 폴더의 `Player_Guard_Suc_F / Player_Guard_Suc_L / Player_Guard_Suc_R`다.

Guard 시작·유지는 Cost가 없고 성공한 공격의 `StaminaDamage`만 기존 GuardHit GE에서 소모한다. 현재 Guard 유지·방어 가능한 접촉·충분한 Stamina 조건이 충족돼야 성공 반응을 선택한다. 공격의 bBlockable=false 또는 방어 실패이면 일반 피격 경로로 넘어간다. 랜덤 방향을 위해 새 Guard Ability나 성공 상태 변수를 추가하지 않았다.

## SwordShield 방패 방어

SwordShield Definition의 `Hit Reactions → System Guard On Lock On`(`bSystemGuardOnLockOn`)을 켠다. `System Guard Front Angle`의 현재180°는 원본 Battle `LockOnMoveInfoMap.SystemGuardFrontAngle=180`에서 확인한 값이다. 프로젝트는 이를 **전체 cone 180°, 좌우 반각90°의 전방 반원**으로 해석한다. 원본 native가 같은 cone 해석을 한다는 사실까지 확인한 것은 아니다.

방패 방어는 전투 타깃을 발견한 대치/이동 상태에서 허용한다. 아직 플레이어를 발견하지 않은 Normal 이동에는 자동 적용하지 않는다. Action을 실행 중이면 현재 Combo node의 `SystemGuardWindows` 안에서만 허용한다. 방패 Hit→End 반응 도중 재접촉은 다시 방어할 수 있다. 일반 피격 반응·Exhaustion·Dead·Stamina0 중에는 허용하지 않는다.

원본 `CustomDamageType=SystemGuard` Notify를 기존 재생률 계약으로 변환한 구간은 다음 세 ComboDefinition에 있다.

- `/Game/Monsters/SwordShield/Data/DA_Combo_Empire_SwordShield_SwordCombo`
- `/Game/Monsters/SwordShield/Data/DA_Combo_Empire_SwordShield_Pierce`
- `/Game/Monsters/SwordShield/Data/DA_Combo_Empire_SwordShield_ShieldCrash`

Details의 `Nodes → 해당 노드 → System Guard Windows`에서 X=start/Y=end를 설정한다. 단위는 **그 노드 section 시작을 0으로 하는 재생 초**다. 현재 section의 실제 montage 위치에서 section 시작을 뺀 시간을 검사하므로 wallclock 타이머 값이나 montage 전체 절대 시각을 넣지 않는다. 원본 9구간/중첩 union8의 정확한 출처·변환은 [ReactionAuthoringPlan.json](ReactionAuthoringPlan.json)의 `system_guard_windows`에 있다.

성공한 blockable 전방 공격은 HP 피해를0으로 만들고 공격 window의 StaminaDamage만 소모한다. 같은 접촉에 일반 HP 피해를 다시 더하지 않는다. Stamina가 남으면 `AM_SwordShield_ShieldBlock`의 Hit→End를 재생한다. 소모로0이 되면 그 공격의 HP 방어는 유지하고 기존 Exhaustion으로 전환한다. 원본 ActiveGuard FrontAngle60이나 GuardStaminaConsumeRate1.8을 이 passive 방어에 섞지 않았다. 절대 Stamina 소모 공식은 원작 native 미확인이므로 현재 공격 데이터의 명시값을 사용한다.

## 브루탈 어택 입력·짝 반응·회복

기존 Player `UKZBrutalAttackAbility`를 확장했고 피해자 쪽은 기존 `UKZExhaustionAbility`가 소유한다. Player의 기존 **X 공격 입력**은 부여된 Brutal을 먼저 시도한다. 가능한 대상이 없거나 activation이 거절되면 기존 일반 X 공격으로 이어진다. 새 입력 키나 두 번째 공격 상태 머신은 없다.

대상은 Stamina0으로 현재 Exhaustion 기회가 열린 몬스터이며, 살아 있고 다른 Brutal에 claim되지 않아야 한다. 플레이어는 지상에 있어야 한다. 기존 대상 선택은 플레이어 정면 반공간의 가까운 유효 대상, actor 위치 사이 3D 거리, 가시선 검사다. range는 인간4종180cm/Apes260cm/Yetuga400cm의 기존 크기 기반 임시 튜닝이다. LockOn target만 고르는 선택 로직은 아니다.

실행 순서는 다음과 같다.

1. 앞/뒤 위치 관계를 한 번 결정하고 victim을 claim한다. 일반 피격 랜덤 방향 정책으로 이 paired front/back을 섞지 않는다.
2. Player Start를 재생하며 capsule이 자연스러운 목적 위치로 점진적으로 접근·회전한다. 두 캡슐의 상대 충돌만 짝 수명 동안 기존 entry 보존 방식으로 제외한다. world 벽 충돌과 목적지 overlap 검사는 유지한다.
3. Player `BrutalHit1`에서 victim `Damage1`을 재생한다.
4. Player `BrutalHit2`에서 victim `Damage2`를 재생하고 `BrutalHPDamage`를 정확히 한 번 적용한다. 현재6종 모두 **50HP: 사용자 지정 임시값**이다. Stamina 피해는 여기서 추가하지 않는다.
5. Player 몽타주 완료와 victim Damage2 완료를 둘 다 기다린다. 피해자 반응이 아직 끝나지 않았다면 회복/다음 동작으로 조기 전환하지 않는다.
6. 생존했으면 victim Exhaustion End를 재생한다. **End까지 실제 완료한 뒤** Stamina를 MaxStamina로 복구한다. HP0이면 생존 회복을 하지 않는다. 취소/실패에서도 claim·timer·자기 추가 collision ignore·이동 제약을 정리한다.

몬스터 Stamina는 일반 공격 Cost로 소모하거나 자동 regen으로 채우지 않는다. 공격 적중과 실제 패링 hook으로 줄어들며 패링 감소5는 사용자 결정값이다. `ExhaustionSeconds`가 양수이면 기존 기회 timeout 후 End로 회복할 수 있다. Brutal까지 무기한 기다리게 하려면 해당 Definition에서0으로 설정한다. 이 timeout 회복과 일반 자동 Stamina regen은 다른 경로다.

브루탈 전용 에셋은 Player의 `/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalFront`와 `AM_DAS_BrutalBack`, 피해자의 `/Game/Monsters/<family>/Animations/AM_BrutalVictimFront`와 `AM_BrutalVictimBack`이다. 몬스터 소진 전용은 같은 폴더의 `AM_Exhaustion`이다. 이 몽타주를 일반 Short/Knockback/Launch 배열에 넣지 않는다. Giant의 일반 NoAirNoBlow 대체가 동일 원본 Grapple_Atk_02 클립을 사용하더라도, 일반 반응 몽타주와 paired victim 몽타주의 실행 계약은 각각 유지한다.

### 부드러운 접근의 수치 출처

원본 `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Grapple/AC_Kazan_DualSwordAxe_Com_Grapple_Start`의 `Notifies[6]` MoveTo는 LinkValue0.03356초, Duration0.433283초, CubicInOut를 저장한다. 현재 Start에는 dilation이 없어서 marker를 현재 montage 초로 사용한다. 원본 파일·export·field는 [BrutalAlignmentResearch.json](BrutalAlignmentResearch.json)의 `player_composites`에 있다.

현재 구현은 `Alpha=Clamp((실제 montage 위치−0.03356)/BrutalAlignmentSeconds, 0, 1)`을 계산하고 cubic ease로 위치 Lerp와 회전 Slerp를 수행한다. cubic exponent3은 수학적 표현이다. 이 시간/블렌드 종류를 참고한 swept 정렬은 **프로젝트 adapter**이며 원본 native 위치 처리 전체를 재현했다고 주장하지 않는다.

목적 간격은 `Max(Player capsule radius+Monster capsule radius, BrutalAlignmentDistance)`다. Z는 양쪽 capsule half-height 차이를 보정한다. 원본의 DestPosition350/near75를 현재 paired 최종 간격이라고 단정하지 않았다. `BrutalAlignmentDistance`와 `BrutalAlignmentSeconds`는 각 monster Definition의 `Monster Stamina → Brutal Attack`에서 조절한다. Seconds가0이면 보간 alpha를 즉시1로 만들지만 벽 sweep은 유지한다.

## 피해량과 종류의 현재 데이터

| 위치 | 현재 값 | 출처 상태 |
| --- | --- | --- |
| Player Combo18node/60window | HP10 / Stamina5 | 기존 저장값 보존. 이번 작업에서 새로 설정한 값이 아니며 원작 절대 피해 근거·최초 사용자 선택 여부는 미확인 |
| 인간4종 공격113window | HP10 / Stamina5 / blockable=true | 어시스턴트 임시 튜닝. 원본 공격 형상/시간에 절대 피해량을 임의 환산하지 않음 |
| 몬스터 BrutalHPDamage6종 | 50HP | 사용자가 명시한 임시 총 피해량, Hit2 한 번 |
| ParryStaminaDamage | 5Stamina | 사용자 지정값. 일반 Guard와 실제 패링 hook을 구분 |

Player의 현재 종류 분류는 Short34/Knockback23/Launch3이고 형상/시간/10·5는 보존했다. 인간4종은 Short109/Knockback2/Launch2다. Heavy SwordSwing01 Step4 일부 window를 Knockback, Halberd DownUpperSlash Step2 일부 window를 Launch로 지정한 강도 해석은 어시스턴트 임시 분류다. 원본 SD index 이름을 원작 확정 넉백 강도로 표현하지 않는다. 조정은 `Nodes → Attack Windows → Hit Reaction`에서 한다.

이 충돌 구현은 원본 Box로 재구성 가능한 window를 대상으로 한다. 원본8개의 unsupported shape/Bounds 부족 항목은 명시적으로 제외했으며 모든 원작 공격 접촉을 구현했다고 주장하지 않는다. 준비 전용 node에는 근거 없는 hit window를 추가하지 않았다. 근거와 예외는 [MonsterAttackCollisionPlan.json](MonsterAttackCollisionPlan.json)의 `limits`와 node별 skipped 항목에 있다. Apes/Yetuga 자율 전투 AI 전체와 새 공격 producer는 별도 작업이다.

## 소스에서 확인할 책임

아래 Main 상대 링크는 기존 파일의 **최종 전달 목적 위치**다. 현재 설명한 변경 함수는 Work 구현을 기준으로 하며, Main 전달 전 기존 Main 파일을 열면 이전 구현일 수 있다. 새 HitReaction2개는 Main에 아직 없으므로 실제 존재하는 Work 링크를 붙였다. 최종 전달 후 Root가 Main 파일 존재·SHA를 확인하고 링크/완료 절을 보충한다.

| 책임 | 소스 |
| --- | --- |
| pool·물리 튜닝·Shield·Brutal 정적 설정 | [KZCharacterDefinitionData.h](../../Source/Khazan/Data/KZCharacterDefinitionData.h) |
| 공격 window의 피격 종류·노드 방패 구간 | [KZComboDefinitionData.h](../../Source/Khazan/Ability/Combo/KZComboDefinitionData.h) |
| 접촉/방어/GE 승인 후 반응 호출 | [KZComboActionAbility.cpp](../../Source/Khazan/Ability/Combo/KZComboActionAbility.cpp) |
| 공통 event 전송·생존/소진 우선순위 | [KZCharacter.cpp](../../Source/Khazan/Character/KZCharacter.cpp) |
| 랜덤 pool·몽타주·RMS·착지·cancel cleanup | [Work KZHitReactionAbility.cpp](C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/Source/Khazan/Ability/KZHitReactionAbility.cpp), [Work header](C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan/Source/Khazan/Ability/KZHitReactionAbility.h) |
| SystemGuard 조건과 HP/Stamina 처리·AI pause | [KZMonster.cpp](../../Source/Khazan/Character/KZMonster.cpp) |
| 대상 선택·접근·Hit1/Hit2·Player 몽타주 완료 | [KZBrutalAttackAbility.cpp](../../Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.cpp) |
| victim claim·반응·paired 완료·End/Max refill·collision ignore | [KZExhaustionAbility.cpp](../../Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.cpp) |
| 기존 X 입력 Brutal 우선 시도 | [KZAbilitySystemComponent.cpp](../../Source/Khazan/Ability/KZAbilitySystemComponent.cpp), 이번 task에서 해당 우선 경로는 재작성하지 않음 |
| 기존 Guard 성공 F/L/R 랜덤 | [KZGuardAbility.cpp](../../Source/Khazan/Ability/PlayerAbility/KZGuardAbility.cpp), 이번 task에서 랜덤 코드를 중복 추가하지 않음 |

## 실제 플레이 확인 순서

Main 전달과 fresh readback 완료 후 새 모듈로 프로젝트를 정상 실행한다. 전달 전 이 절은 Work 동작 확인 절차다. 사용자 에디터의 PIE를 어시스턴트가 실제 조작 완료한 기록으로 해석하지 않는다.

1. 원하는 공격 window의 HitReaction을 Short로 설정해 짧은 랜덤 반응 후 복귀를 확인한다. 반복 피격의 재시작·다른 Action 취소도 확인한다.
2. 같은 공격을 Knockback/Launch로 바꾸고 종별 지원표의 체인을 확인한다. 포즈 후보가 달라져도 물리 이동은 공격자 반대 방향인지, 벽에서 과도하게 이동하지 않는지 확인한다.
3. SwordShield가 플레이어를 발견한 뒤 전방/후방 및 bBlockable=true/false 접촉을 비교한다. 성공 시 HP 유지·Stamina 감소·ShieldBlock, Stamina0이면 Exhaustion이 예상 결과다. 공격 중에는 해당 node의 방패 window 안/밖을 비교한다.
4. Player Guard 성공을 반복해 Suc_F/L/R 후보 안에서 선택되는지 확인한다. 몇 회 안에 세 후보가 반드시 모두 나와야 한다는 RNG 보장은 없다.
5. 몬스터 Stamina를0으로 만들고 가까이 앞/뒤에서 X를 누른다. 점진 접근→맞는 front/back pair→50 한 번→양쪽 완료→victim End 후 Max refill을 확인한다. HP50 이하인 경우 생존 refill이 없어야 한다. 벽 막힘·강제 취소 뒤 claim/제약이 남지 않아야 한다.

피격 asset 경로와 각 section의 실제 클립은 아래 목록 및 [ReactionAuthoringPlan.json](ReactionAuthoringPlan.json)의 `bodies[].montages[].sections`가 정확한 확인 기준이다. 분류 원본은 [AnimationClassification.json](AnimationClassification.json)이다. 몽타주의 source clip을 변경할 때 해당 skeleton·section chain·HitLand·rate 계약을 함께 확인한다.

## 정리된 일반 피격 에셋 목록

이 절은 저장된 ReactionAuthoringPlan에서 다음 후속 문서 작업으로 생성한 목록이다. 폴더 아래 이름을 그대로 이어 붙이면 정확한 `/Game/...` 에셋 경로가 된다. 동일 Giant fallback이 두 pool에 등장하므로 계획65행/실제 unique 몽타주63개다. Player의 사용 clip24개는 모두 `/Game/_Art/Player/Animation/InGame/DAS/Reaction/Clips`에 있다. QuickStand F/B/L/R 4개도 이 폴더로 정리했지만 현재 ordinary recovery chain에는 연결하지 않았다.

### Swordsman

정확한 몽타주 폴더: `/Game/Monsters/Swordsman/Animations/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_Swordsman_Hit_Damage_Normal_L_F` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_L_F_2` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_R_F` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_R_F_2` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_D_F` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_D_F_2` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_U_F` | Hit |
| Short | `AM_Swordsman_Hit_Damage_Normal_U_F_2` | Hit |
| Knockback | `AM_Swordsman_Knockback_F` | Down → Loop → Getup |
| Launch | `AM_Swordsman_Launch_F` | Up → Peak → Down → Land → Loop → Getup |
| Knockback | `AM_Swordsman_Knockback_B` | Down → Loop → Getup |
| Launch | `AM_Swordsman_Launch_B` | Up → Peak → Down → Land → Loop → Getup |

### SwordShield

정확한 몽타주 폴더: `/Game/Monsters/SwordShield/Animations/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_SwordShield_Hit_Damage_Normal_L_F` | Hit |
| Short | `AM_SwordShield_Hit_Damage_Normal_R_F` | Hit |
| Short | `AM_SwordShield_Hit_Damage_Normal_D_F` | Hit |
| Short | `AM_SwordShield_Hit_Damage_Normal_U_F` | Hit |
| Knockback | `AM_SwordShield_Knockback_F` | Down → Loop → Getup |
| Launch | `AM_SwordShield_Launch_F` | Up → Peak → Down → Land → Loop → Getup |
| Knockback | `AM_SwordShield_Knockback_B` | Down → Loop → Getup |
| Launch | `AM_SwordShield_Launch_B` | Up → Peak → Down → Land → Loop → Getup |
| ShieldBlock | `AM_SwordShield_ShieldBlock` | Hit → End |

### HeavySwordsman

정확한 몽타주 폴더: `/Game/Monsters/HeavySwordsman/Animations/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_HeavySwordsman_Hit_Damage_Normal_L_F` | Hit |
| Short | `AM_HeavySwordsman_Hit_Damage_Normal_R_F` | Hit |
| Short | `AM_HeavySwordsman_Hit_Damage_Normal_D_F_Composite` | Hit |
| Short | `AM_HeavySwordsman_Hit_Damage_Normal_U_F` | Hit |
| Knockback | `AM_HeavySwordsman_Knockback_F` | Down → Loop → Getup |
| Knockback | `AM_HeavySwordsman_Knockback_B` | Down → Loop → Getup |

### HalberdElite

정확한 몽타주 폴더: `/Game/Monsters/HalberdElite/Animations/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_HalberdElite_Hit_Damage_Normal_L_F` | Hit |
| Short | `AM_HalberdElite_Hit_Damage_Normal_R_F` | Hit |
| Short | `AM_HalberdElite_Hit_Damage_Normal_D_F` | Hit |
| Short | `AM_HalberdElite_Hit_Damage_Normal_U_F` | Hit |
| Launch | `AM_HalberdElite_Launch_F` | Up → Peak → Down → Land → Getup |
| Knockback | `AM_HalberdElite_Knockback_F` | Down → Loop → Getup |
| Launch | `AM_HalberdElite_Launch_B` | Up → Peak → Down → Land → Getup |
| Knockback | `AM_HalberdElite_Knockback_B` | Down → Loop → Getup |

### ApesStoneHandElite

정확한 몽타주 폴더: `/Game/Monsters/ApesStoneHandElite/Animations/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_ApesStoneHandElite_Hit_Damage_Normal_L_F` | Hit |
| Short | `AM_ApesStoneHandElite_Hit_Damage_Normal_R_F` | Hit |
| Short | `AM_ApesStoneHandElite_Hit_Damage_Normal_D_F` | Hit |
| Short | `AM_ApesStoneHandElite_Hit_Damage_Normal_U_F` | Hit |
| Knockback | `AM_ApesStoneHandElite_NoAirNoBlow` | Hit |
| Launch | `AM_ApesStoneHandElite_NoAirNoBlow` | Hit |

### Yetuga

정확한 몽타주 폴더: `/Game/Monsters/Yetuga/Animations/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_Yetuga_Hit_Damage_Normal_L_F` | Hit |
| Short | `AM_Yetuga_Hit_Damage_Normal_R_F` | Hit |
| Short | `AM_Yetuga_Hit_Damage_Normal_D_F` | Hit |
| Short | `AM_Yetuga_Hit_Damage_Normal_U_F` | Hit |
| Knockback | `AM_Yetuga_NoAirNoBlow` | Hit |
| Launch | `AM_Yetuga_NoAirNoBlow` | Hit |

### Player

정확한 몽타주 폴더: `/Game/_Art/Player/Animation/InGame/DAS/Reaction/Montages`

| 종류 | 이 폴더의 에셋 이름 | section chain |
| --- | --- | --- |
| Short | `AM_Player_Hit_DamageNormal_D_B` | Hit |
| Short | `AM_Player_Hit_DamageNormal_D_F` | Hit |
| Short | `AM_Player_Hit_DamageNormal_L_F` | Hit |
| Short | `AM_Player_Hit_DamageNormal_R_F` | Hit |
| Short | `AM_Player_Hit_DamageNormal_U_B` | Hit |
| Short | `AM_Player_Hit_DamageNormal_U_F` | Hit |
| Short | `AM_Player_Hit_DamageStrong_D_F` | Hit |
| Short | `AM_Player_Hit_DamageStrong_L_F` | Hit |
| Short | `AM_Player_Hit_DamageStrong_R_F` | Hit |
| Short | `AM_Player_Hit_DamageStrong_U_F` | Hit |
| Short | `AM_Player_Hit_DamageWeak_D_F` | Hit |
| Short | `AM_Player_Hit_DamageWeak_L_F` | Hit |
| Short | `AM_Player_Hit_DamageWeak_R_F` | Hit |
| Short | `AM_Player_Hit_DamageWeak_U_F` | Hit |
| Knockback | `AM_Player_Knockback_F` | Down → Loop → Getup |
| Launch | `AM_Player_Launch_F` | Up → Loop → Getup |
| Knockback | `AM_Player_Knockback_B` | Down → Loop → Getup |
| Launch | `AM_Player_Launch_B` | Up → Loop → Getup |

### Player InGame clip24개

정확한 clip 폴더: `/Game/_Art/Player/Animation/InGame/DAS/Reaction/Clips`

| 에셋 이름 | 연결 상태 |
| --- | --- |
| `CA_P_Kazan_DualAxeSword_Off_DamageNormal_D_B` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageNormal_D_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageNormal_L_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageNormal_R_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageNormal_U_B` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageNormal_U_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageStrong_D_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageStrong_L_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageStrong_R_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageStrong_U_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageWeak_D_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageWeak_L_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageWeak_R_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageWeak_U_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageAir_B` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_DamageAir_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_Down_Loop_B` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_Down_Loop_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_Getup_B` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_Getup_F` | 일반 피격 몽타주 section에서 사용 |
| `CA_P_Kazan_DualAxeSword_Off_QuickStand_B` | 정리한 QuickStand 후보, 현재 chain 미연결 |
| `CA_P_Kazan_DualAxeSword_Off_QuickStand_F` | 정리한 QuickStand 후보, 현재 chain 미연결 |
| `CA_P_Kazan_DualAxeSword_Off_QuickStand_L` | 정리한 QuickStand 후보, 현재 chain 미연결 |
| `CA_P_Kazan_DualAxeSword_Off_QuickStand_R` | 정리한 QuickStand 후보, 현재 chain 미연결 |

## 2026-10-10 — Main 전달·새 프로세스 검증 완료

**현재 상태는 Main 적용 완료다.** 문서 첫 절의 Work 구현/Main 미전달·Heavy 회귀 조사 중 설명은 작성 당시 기록으로 보존하며, 현재 적용 상태는 이 절이 대체한다. [FinalVerification.json](FinalVerification.json)의 상태는 `success=true`, `MainDeliveredAndFreshVerified`다. 아래 사용·조절 절차와 앞의 에셋 목록을 이제 Main에서 확인할 수 있다.

runtime16파일과 에셋130개, 총146파일을 선택 전달했다. 새 runtime 클래스는 공통 HitReaction 하나이며 임시 author2/test1은 제품 Source에서 제거하고 stock Build.cs를 복원했다. stock build는 성공했고 기존 canonical DLL과 미관련 Main 변경을 보존했다. 상세 변경 코드는 [RuntimeChanges.patch](RuntimeChanges.patch)에 있다. 사용자 및 다른 task 에디터에는 PIE·저장·종료·reload를 보내지 않았다.

Main의 현재 선택 모듈은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`이다. 자기 새 Main reader PID16544가 이 모듈을 실제 로드했으며 SHA는 `74a069363f9100a4784ac03a4941214f0a98f732b4dc296d3f7198c7e62d2983`다. fresh Work PID29152와 Main PID16544는 각각654,552개의 저장 읽기 검사에서 실패0·미지원0·dirty package0을 확인하고 정상 종료했다. [WorkSavedReload.json](WorkSavedReload.json), [MainSavedReload.json](MainSavedReload.json)이 해당 실제 증거다. 사용자 에디터가 구 모듈로 계속 켜져 있다면 사용자가 정상 종료·재실행한 뒤 새 native schema의 에셋을 확인한다.

실제 RHI native 결과는 일반 피격32·브루탈15·Monster→Player 충돌3case, 1,066검사와 캡처7장이다. [NativePIE_Final.json](NativePIE_Final.json)과 최종 Verification에 결과를 보존했다. fresh PID23912의 기존 Guard·Heal·PlayerAttackCollision·MonsterCombatPolicy 회귀4종도 모두 Success다([IntegratedRegression.json](IntegratedRegression.json)). 이전 Heavy timeout은 새 실행에서 재현되지 않았고 최초 원인은 미확정이다. 이를 해결했다는 명목으로 AI 제품 코드를 바꾸지 않았다. 전체 RHI는 helper 제거 전 DLL에서 실행했으며 **동일한 제품 runtime Source**의 최종 stock Work/Main은 fresh saved readback으로 검증했다. 최종 Main에서 RHI 전체를 새로 반복했다고 기록하지 않는다.

### Main의 현재 구현 소스

아래 링크는 실제 전달된 Main 파일의 존재를 확인했다. 앞의 Work HitReaction 링크는 초안의 검사 위치로 보존하며 현재 Main 구현을 보려면 이 절을 사용한다.

- [KZHitReactionAbility.cpp](../../Source/Khazan/Ability/KZHitReactionAbility.cpp): 랜덤 종류 pool 선택, 몽타주/RMS 실행, 착지·재피격·취소 정리.
- [KZHitReactionAbility.h](../../Source/Khazan/Ability/KZHitReactionAbility.h): 공통 반응 실행이 소유하는 Task·instance·constraint·mode 수명.
- [KZBrutalAttackAbility.cpp](../../Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.cpp): 기존 X 우선 Ability, 대상 선택, swept 점진 접근, Hit1/Hit2와50 단일 피해, Player 완료.
- [KZExhaustionAbility.cpp](../../Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.cpp): 피해자 반응·짝 claim/완료·생존 End 뒤 MaxStamina 회복·상대 capsule ignore cleanup.
- [KZCharacterDefinitionData.h](../../Source/Khazan/Data/KZCharacterDefinitionData.h): 종류별 pool과 아래 조절 필드의 실제 선언.
- [KZComboDefinitionData.h](../../Source/Khazan/Ability/Combo/KZComboDefinitionData.h): 공격 window별 `HitReaction`/피해량/`bBlockable`, node-local `SystemGuardWindows`.

### 지금 조절할 위치와 예상 결과

| 조절 목적 | Main 에디터 위치 | 현재 값·의미 |
| --- | --- | --- |
| 공격별 피격 종류/피해/방어 가능 여부 | 해당 `DA_Combo_* → Nodes → Attack Windows` | `HitReaction`, `HPDamage`, `StaminaDamage`, `bBlockable`. Player 기존10/5 보존, 인간 몬스터10/5는 임시 튜닝 |
| 종별 포즈 후보 | 위7개 CharacterDefinition → `Hit Reactions` | `ShortHits / Knockbacks / Launches`; 방향 포즈는 유효 후보에서 랜덤 |
| 날림 이동량 | 같은 Definition → `Hit Reactions` | `KnockbackDistance=250cm`, `LaunchDistance=120cm`, `LaunchHeight=150cm`: 어시스턴트 임시 world 수치. Player .01을 재적용하지 않음 |
| ShieldMan 방패 | SwordShield Definition → `Hit Reactions` | `bSystemGuardOnLockOn=true`, `SystemGuardFrontAngle=180°`. 원본180을 full cone으로 해석한 프로젝트 adapter |
| 공격 중 방패 유지 구간 | SwordShield의3개 ComboDefinition → `Nodes → System Guard Windows` | `X=start / Y=end`, 해당 node section 시작 기준 초 |
| 브루탈 피해/접근 | 각 monster Definition → `Monster Stamina` | `BrutalHPDamage=50` 사용자 임시값, `BrutalAlignmentDistance` capsule 간격, `BrutalAlignmentSeconds=0.433283초` 원본 duration 참고 |
| 소진 기회 유지 | 같은 `Monster Stamina` | `ExhaustionSeconds`;0이면 Brutal 기회를 무기한 대기, 양수이면 기존 timeout 후 End 회복 |

Main에서 몬스터 Stamina를0으로 만든 뒤 유효한 거리의 앞/뒤에서 X를 누르면 대응하는 Player/victim 짝이 재생된다. Hit2에서50을 한 번 적용하고 양쪽 몽타주가 완료한 다음, 생존한 victim의 End 완료 뒤 MaxStamina로 복구한다. 일반 피격은 공격 방향으로 포즈를 고르지 않으며 Short/Knockback/Launch 종류 안에서 랜덤이다. 물리 이동은 공격자 반대 방향을 별도로 사용한다. Player Guard 성공은 기존 Suc_F/L/R 랜덤이다. ShieldMan은 전방의 blockable 공격에서 HP를 막고 Stamina를 소모하며0이면 Exhaustion으로 전환한다.

종별 지원 한계는 앞의 표 그대로다. Heavy Launch는 Short fallback이고 Apes/Yetuga의 Launch/Knockback은 원본 NoAir/NoBlow 지정 Grapple2 대체다. 제외한 원본 unsupported collision11발생·별도 Player 사망 구현·실제 패링 판정 producer·원작 pose/contact 완전 일치·멀티플레이는 이번 완료 범위에 포함하지 않는다. 새 타격별 강도나 임시 이동량을 조절한 후에는 실제 capsule 이동/회복·wall sweep·짝 취소 cleanup을 다시 확인한다.

<!-- BrutalBInputUpdate_20261010 -->
## 2026-10-10 — 현행 브루탈 키 B 및 새 DevMap 배치

사용자 후속 요청으로 브루탈 입력을 X에서 **패드 B(Gamepad_FaceButton_Right)**로 변경해 Main build/saved reload를 완료했다. 앞선 본문의 X는 당시 조작이며 현재 X는 약공격이다. 소진된 유효 대상·거리·접근·피해50·짝 모션과 양쪽 완료 후 생존 회복 조건은 기존과 같다. 실제 물리 B 누름은 사용자 직접 확인 범위다.

DevMap은 약320m×320m 바닥/nav 확장과 기존 인간10마리+Apes/Yetuga 각1마리로 총12마리/6종 배치를 저장했다. 짐승 둘은 기존 gameplay 테스트 캐릭터이며 자율 AIStateTree는 None이다. 최신 [입력·배치 설명](../BrutalInputDevMap_20261010/README.md)과 [최종 검증](../BrutalInputDevMap_20261010/FinalVerification.json)을 따른다. 별도 새 Main PIE6종 초기화·인간4종 native AI 검사 성공, 작업용 프로세스 정상 종료·dirty0·byte 불변을 확인했다.
