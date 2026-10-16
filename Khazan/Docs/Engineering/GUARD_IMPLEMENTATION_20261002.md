# Guard 구현 — 2026-10-02

사용자의 직접 수정 요청으로 적용한 현행 구현이다. 입력·GAS·이동 제약·AnimInstance snapshot·기존 Slot/관성화를 재사용했다. 실행 수명은 `UKZGuardAbility` 하나가 소유한다. Guard Manager, 별도 상태 머신, 새 AbilityTask, 피해 프레임워크는 추가하지 않았다.

관련 계약은 [아키텍처 ARCH-74](CHARACTER_GAMEPLAY_ARCHITECTURE.md), 이동/표현 정본은 [LOCOMOTION_CURRENT_IMPLEMENTATION.md](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md)다.

## 1. 실제 동작

- LShift / Gamepad LB 시작 → Guard Ability 활성화 → `Guard_Start`.
- 누른 상태 유지 → Start 종료 후 ABP의 `Player_Guard_Loop`. 이동 입력이 있으면 Guard Blend Space.
- LockOn 이동 → 기존 캐릭터 기준 입력 각도의 8방향. 비LockOn 이동 → F 모션.
- 키 해제 → 즉시 방어 태그와 Guard의 Walk 상한 해제. 현재 Start/성공 모션이 InputEnd 전이면 해당 InputEnd에서 End로 넘어가고, 이미 InputEnd 이후면 즉시 `Guard_End`.
- End의 InputEnd부터 이동 또는 다른 Action으로 회복부 중단. 무입력은 End 전체를 마친 뒤 정상 종료.
- 활성화·유지 Cost/Cooldown은 없다. 성공한 타격에만 공격이 전달한 스태미너 피해량을 소모하고 Suc_F/L/R 중 하나를 무작위 재생한다.
- 일반 지상 Guard이다. 현재 CanActivate는 CMC의 지상 이동 상태를 요구한다. 공중 Guard·GuardBreak·JustGuard·방어 각도·HP/적 타격 처리는 이번 실행 범위에 없다.

여기서 “InputEnd”는 현재 프로젝트에서 다른 Action을 허용하는 경계다. 원작 cancel Notify를 그 계약에 대응시켰으며 원작 게임 내부의 모든 취소 규칙을 복원했다고 의미하지 않는다.

## 2. 수정 파일과 책임

| 파일 | 실제 변경 / 책임 |
| --- | --- |
| [KZGuardAbility.h](../../Source/Khazan/Ability/PlayerAbility/KZGuardAbility.h), [cpp](../../Source/Khazan/Ability/PlayerAbility/KZGuardAbility.cpp) | 새 런타임 파일 2개. Guard 실행, held/해제, Start/성공/End 전환, 자기 handle 정리 |
| [KZPlayerController.h](../../Source/Khazan/Player/KZPlayerController.h), [cpp](../../Source/Khazan/Player/KZPlayerController.cpp) | 기존 InputData에서 Guard를 찾고 Started/Completed/Canceled를 기존 ASC 입력 API로 전달 |
| [KZAbilitySystemComponent.h](../../Source/Khazan/Ability/KZAbilitySystemComponent.h), [cpp](../../Source/Khazan/Ability/KZAbilitySystemComponent.cpp) | BlueprintCallable `TryGuardHit`. 활성 Guard 인스턴스에 위임. 순회 중 기존 FScopedAbilityListLock 사용 |
| [KZGameplayTags.h](../../Source/Khazan/KZGameplayTags.h), [cpp](../../Source/Khazan/KZGameplayTags.cpp) | Input.Action.Guard / Ability.Action.Guard / State.Guarding 네이티브 등록 |
| [KZAnimInstance.h](../../Source/Khazan/Animation/KZAnimInstance.h), [cpp](../../Source/Khazan/Animation/KZAnimInstance.cpp) | GT 방어 태그 snapshot과 읽기 전용 표현 bool/각도. 새로운 방향 계산은 없음 |
| [KZGuardAbilityPIETest.cpp](../../Source/Khazan/Tests/KZGuardAbilityPIETest.cpp) | 개발 빌드 전용 실제 PIE 통합 검사. 게임 기능의 실행 구조를 소유하지 않음 |
| [setup_guard_20261002.py](../../Scripts/Animation/setup_guard_20261002.py) | 에디터 asset 작성 도구. 에셋은 이미 생성됨. setup() 재실행 금지; 기존 에셋 보호 검사 포함 |

Guard는 `UKZActionAbility`를 상속한다. `UKZComboActionAbility`는 공격의 이동 차단/콤보 창을 소유하므로 Guard의 유지 이동과 다른 수명이다. 공통 Action의 InputEnd block/cancel을 사용하면서 Guard의 held·release·반복 성공 수명만 새 Ability에 둔 이유다. KZPlayer, Dodge/Weak/Strong/Charge 및 기존 ComboDefinition 코드는 이번 작업에서 바꾸지 않았다.

## 3. 입력과 태그 계약

`IA_Guard`는 Boolean이고 추가 Hold Trigger는 없다. Started가 즉시 시작하고 Completed가 해제하며 Canceled는 End 재생 없이 실행을 취소한다. 누르는 동안 매 Tick Ability를 다시 실행하지 않는다. 눌림 사실은 기존 `FGameplayAbilitySpec::InputPressed`를 재사용한다.

| 태그 | 작성자 | 소비자 / 의미 |
| --- | --- | --- |
| Input.Action.Guard | InputData/CharacterDefinition grant 및 Controller | 기존 ASC의 exact InputTag press/release/cancel |
| Ability.Action.Guard | Guard Ability의 Asset Tags | 기존 Ability.Action 부모 block/cancel 규칙. 소유 상태 태그가 아님 |
| State.Guarding | Guard Ability가 적용한 infinite GE | 미래 피격 처리와 GT Anim snapshot이 읽는 실제 방어 상태 |

세 태그는 네이티브 선언/정의다. 문자열을 붙이는 것만으로 Guard가 실행되는 것이 아니라 InputAction 매핑 → Controller binding → grant된 Spec → Ability 활성화가 모두 연결돼 있다.

## 4. Guard Ability의 변수

| 변수 / 타입 | 단위·초기 의도 | 작성 / 소비 / 정리 |
| --- | --- | --- |
| GuardMontage : TObjectPtr<UAnimMontage> | 에셋 참조 | Guard BP defaults. CanActivate가 필수 섹션 확인, PlaySection이 재생 |
| GuardStateEffect : TSubclassOf<UGameplayEffect> | infinite·modifier 없음 | BP에서 GE_State_Guard 지정. held 방어 태그만 부여 |
| GuardHitStaminaEffect : TSubclassOf<UGameplayEffect> | instant | GE_GuardHit_Stamina 지정. 공격별 SetByCaller 피해량 적용 |
| GuardHitRecoveryDelayEffect : TSubclassOf<UGameplayEffect> | duration | 기존 GE_Player_StaminaRegenDelay 재사용. 원본 GE 에셋 duration은 편집하지 않음 |
| GuardStaminaRecoveryDelay : float | 초, 0.5 | 원작 일반 Guard 직접 확인값. 성공 Spec의 duration override |
| LocomotionExitInertializationDuration : float | 초, 0.24 | 기존 Combo 이동 복귀 설정을 재사용한 임시 표현값. End 조기 이동 중단에 사용 |
| ActiveMontageTask : Transient TObjectPtr | 초기 nullptr | 현재 섹션의 PlayMontageAndWait Task. 새 섹션 전에 이전 Task EndTask; 완료/Ability 종료 때 비움 |
| BoundAnimInstance : TWeakObjectPtr<UAnimInstance> | 초기 invalid | 활성화 시 Notify delegate 연결, 종료 시 해제/Reset. 캐릭터 수명을 연장하지 않음 |
| GuardStateHandle : FActiveGameplayEffectHandle | 초기 invalid | 적용한 Guard GE 하나를 식별. Release/종료에서 자기 GE만 제거/Invalidate |
| GuardMovementHandle : FKZMovementConstraintHandle | 초기 invalid | 기존 LocomotionComponent의 Walk 상한. Release/종료에서 자기 constraint만 해제/Reset |
| CurrentSection : FName | 초기 None | 현재 Start/Suc_F/Suc_L/Suc_R/End 구분. 유지 ABP로 돌아가면 None, 종료 때 None |
| ActiveMontageInstanceId : int32 | INDEX_NONE | Task 활성화 후 실제 Montage 인스턴스 ID 기록. 이전 재생의 늦은 Notify를 거절, 새 섹션/종료 때 무효화 |

`KZGuard::Start/End/InputEnd`는 섹션/Notify 이름이다. `StaminaDamage`는 GE SetByCaller의 DataName `GuardStaminaDamage`다. `SuccessSections` 배열은 Suc_F/L/R 이름 3개이며 `FMath::RandHelper`로 인덱스 하나를 선택한다. 배열 길이·INDEX_NONE·재생률 1은 엔진/선택 계약이고 새로운 스태미너 튜닝값이 아니다.

별도 bIsGuardHeld/bReleasePending을 만들지 않았다. release 예약은 기존 Spec.InputPressed=false와 현재 섹션/InputEnd 상태로 판정한다. GA 인스턴스의 CurrentSection은 실행 내부 상태이고, 공유 방어 사실은 GE 태그다.

## 5. 함수와 실행 순서

모든 gameplay 함수·GE·constraint·Montage callback은 게임 스레드에서 동작한다. 기존 프로젝트처럼 LocalOnly/InstancedPerActor이다. AI도 같은 Character/ASC와 Ability를 부여하면 이 실행 기반을 사용할 수 있지만 AI 입력·멀티플레이 예측/복제는 이번 검증 범위가 아니다.

| 함수 | 역할 / 주요 분기 |
| --- | --- |
| 생성자 | Ability.Action.Guard Asset Tag 추가. 기존 Action 부모의 block/cancel·인스턴싱 정책 상속 |
| CanActivateAbility(...) const | 부모의 block/Cost gate와 ActorInfo, 4개 필수 에셋, Character/Locomotion/AnimInstance, CMC 지상, Start/End/Suc 3섹션 검사. 실패 시 실행 자원을 만들지 않음 |
| ActivateAbility(...) | Commit → GuardState GE → Walk constraint → Notify 연결 → 기존 WaitGameplayEvent(Move) → Start Task. GE/constraint callback 중 취소돼도 방금 반환된 자기 handle 정리 |
| IsGuardInputHeld() const | 현재 Spec Handle로 ASC Spec을 조회해 InputPressed 반환. 입력 상태를 수정하지 않는 조회 |
| InputReleased(...) | 먼저 방어/Walk 해제. InputEnd 이후 또는 Task가 없으면 End; 그 전이면 다음 InputEnd까지 Spec의 release 상태를 사용 |
| PlaySection(FName) | 이전 Task를 EndTask, 섹션/instance ID 갱신, ResetInputEnd로 Action block 재설정, 기존 PlayMontageAndWait 생성/연결/ReadyForActivation, 실제 인스턴스 ID 확보 |
| HandleMontageNotify(...) | 활성 여부·Montage asset·instance ID·InputEnd 이름 모두 일치해야 처리. SetInputEnded로 다른 Action 허용; release 예약이면 End, End이면 기존 이동 의도를 즉시 확인 |
| HandleMontageCompleted() | End면 정상 종료. 다른 섹션 완료 시 release면 End, held면 섹션 None + InputEnded로 ABP 유지 |
| HandleMontageAborted() | 중단/재생 실패 시 취소 종료 |
| HandleMoveInput(FGameplayEventData) | End + InputEnded + 유효/허용 이동 의도인 경우에만 기존 관성화 요청 → Montage_Stop(0) → Ability 종료. held Guard의 이동은 계속 허용 |
| TryGuardHit(float, AActor*) | 방어 중·held·자기 GE 존재·유한 양수 피해량·충분한 스태미너 확인 → Cost Spec → 성공 재생/regen 지연. 아래 미래 타격 계약 참조 |
| ReleaseGuardState() | 자기 GE handle과 constraint handle 해제 후 무효화. 공용 태그를 일괄 Remove하지 않음 |
| FinishAbility(bool) | 아직 active일 때만 현재 Spec/ActorInfo/ActivationInfo로 EndAbility 호출 |
| EndAbility(...) | Notify 해제 → 자기 GE/constraint 정리 → 약한 참조/섹션/instance ID Reset → 기존 부모의 Task/Action 정리 → Task 포인터 비움 |

FName 인자는 작은 값 타입이다. ActorInfo/GameplayTagContainer 인자 포인터는 엔진 override 계약이며 함수가 보관하지 않는다. Notify payload의 const 참조는 엔진이 제공한 Montage 식별 정보를 읽기만 한다. `bWasCancelled`는 이번 종료의 원인이지 방어 상태 저장값이 아니다.

섹션마다 Task를 교체하는 이유는 같은 Montage라도 Start 완료 callback이 나중의 성공/End 수명을 끝내지 않도록 하기 위해서다. Notify에는 추가 instance ID 필터를 둬 이전 Montage 재생의 사건을 현재 실행에 적용하지 않는다.

Release 이후 End 회복 중에는 State.Guarding이 없으므로 피해를 막지 않는다. InputEnd에서 태그를 다시 부여하지 않는다. 입력 Cancel, 공격 교체, 빙의 해제, 부모 DestroyActiveState의 취소 경로는 EndAbility로 동일한 자기 자원을 정리한다.

## 6. 가드 성공을 후속 공격에 연결

현재 공개 API는 ASC에 있다.

```cpp
UFUNCTION(BlueprintCallable, Category="KZ|Combat|Guard")
bool TryGuardHit(float StaminaDamage, AActor* Attacker = nullptr);
```

- 호출자: 미래 적 공격/피격 판정.
- StaminaDamage: 해당 공격 데이터가 정한 양수 스태미너 피해량. 활성화 Cost가 아니며 이번에 고정 숫자를 새로 만들지 않았다.
- Attacker: 선택적 공격자 참조. Cost Effect Context의 SourceObject에 넣는다. 실제 피해/Instigator 전체 규약을 이번에 구현한 것은 아니다.
- true: Cost가 실제 적용돼 이 타격을 방어함. 이어진 Montage 실패/다른 callback 취소로 HP 피해를 다시 적용하면 안 됨.
- false: 방어 중이 아니거나 release됨, GE 없음, 비유한/0/음수 피해량, 스태미너 부족, Cost Spec/적용 실패. 후속 일반 피해/GuardBreak 판정의 소유자는 공격·피격 시스템이다.

후속 코드의 연결 형태는 다음과 같다. 아래 두 변수는 미래 공격 데이터/공격자에서 가져오는 값이며 신규 현재 프로젝트 심볼의 선언이 아니다.

```cpp
if (VictimASC->TryGuardHit(AttackStaminaDamage, Attacker))
{
    return; // 이 타격의 HP 피해 적용 단계를 건너뛴다.
}
// 기존 일반 피격 처리로 진행한다.
```

호출 전에 공격자가 “이 공격이 방어 가능하며 방향·타격 조건이 맞는가”를 검증해야 한다. 현 API는 Attacker 위치를 보고 자동으로 전방 공격인지 판단하지 않는다. 스태미너 부족 상태에서 GuardBreak를 자동으로 재생하지도 않는다.

GE_GuardHit_Stamina는 Stamina의 AddBase modifier에 SetByCaller DataName을 사용한다. Ability가 `-StaminaDamage`를 전달하므로 차감한다. instant Effect handle은 IsValid가 false여도 정상 적용될 수 있어 `WasSuccessfullyApplied()`로 성공을 판정한다. 성공 후 기존 regen delay GE의 새 Spec에만 0.5초 duration을 설정한다. 연속 피격도 새 성공 반응과 차감을 적용한다.

## 7. 에디터 에셋과 ABP

새 에셋:

- `/Game/Input/IA_Guard`
- `/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard`
- `/Game/Bluprints/AbilitySystem/Effects/Guard/GE_State_Guard`
- `/Game/Bluprints/AbilitySystem/Effects/Guard/GE_GuardHit_Stamina`
- `/Game/_Art/Player/Animation/InGame/DAS/Guard/AM_DAS_Player_Guard`
- `/Game/_Art/Player/Animation/InGame/DAS/Guard/Locomotion/BS_DAS_Player_Guard`

기존 연결 에셋:

- IMC_Default: LeftShift / Gamepad_LeftShoulder → IA_Guard.
- DA_InputData: Input.Action.Guard → IA_Guard.
- DA_CharacterDefinition_Player: GA_Player_Guard 1회 grant, InputTag=Input.Action.Guard.
- ABP_Player: 기존 locomotion StateMachine 앞뒤를 교체하지 않고 DefaultSlot의 Source 선택에 Guard 포즈를 추가.

GA_Player_Guard Class Defaults에는 Cost/Cooldown=None, GuardMontage 및 3개 GE 참조를 지정했다. GuardState GE는 infinite이고 modifier가 없으며 State.Guarding만 부여한다. 기존 regen delay GE 에셋의 설정은 보존했다.

ABP의 GameThread Gather가 ASC State.Guarding을 `FKZAnimGameThreadData::bGuarding`에 복사한다. worker는 이 snapshot에서 `bIsGuarding`을 작성하고, 기존 `MovementDirectionAngle`을 재사용해 LockOn일 때만 `GuardMovementDirectionAngle`을 제공한다. 비LockOn은 0도(F)다. 새 atan 계산이나 worker의 ASC/Actor 접근은 없다. snapshot이 무효면 두 표현 값은 false/0으로 Reset된다.

최종 포즈 경로:

```text
기존 Locomotion ───────────────┐
Guard Loop / Guard 이동 BS ────┴─ Guard_SelectPose
                                → 기존 DefaultSlot → 기존 Inertialization → Output
```

- Guard_SelectMove: bHasMovementInput=true면 Guard_Walk BS, false면 Guard_Idle Loop.
- Guard_SelectPose: bIsGuarding=true면 Guard_SelectMove, false면 기존 locomotion.
- UE BlendListByBool의 true pose는 BlendPose_0, false는 BlendPose_1이다. 두 노드에 같은 규칙으로 실제 연결했다.
- Guard_Walk의 X는 GuardMovementDirectionAngle, Y=0이다. BS는 현재 LockOn Walk BS의 보간/격자 설정을 복제해 9개 sample(-180 B ~ 180 B)을 배치했다. ±180 중복은 각도 경계 연결이며 모션은 8개다.
- asset 이름의 `Wark` 철자는 기존 이름 그대로 사용했다.
- Guard의 Walk 상한은 현행 LocomotionComponent/CharacterDefinition의 Walk 정책이다. 관측된 MaxWalkSpeed=170 cm/s를 새 Guard 전용 원작 속도라고 주장하지 않는다. 별도 speed literal은 추가하지 않았다.

## 8. InputEnd와 수치 출처

원작 cache 기준 경로:

`Saved/Extracted/InGame_Playback_20261002/Metadata/BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Guard/`

추출일 2026-10-02를 식별자로 사용한다. 이 cache만으로 원작 게임의 정확한 배포 build 번호는 식별하지 못했다. 파일 SHA256, 실제 원본 field/값/Dilation 자료를 [OriginalTimingEvidence.json](../../Metadata/GuardImplementation_20261002/OriginalTimingEvidence.json)에 저장했다.

| 모션 | 원본 composite / property | 원시 시간(초) | 현재 시퀀스 InputEnd(초) |
| --- | --- | ---: | ---: |
| Start | AC_Kazan_DualAxeSword_Com_Guard_Normal_Start / Properties.Notifies[4].LinkValue, xxCancelGroupAnimTiming | 0.446119 | 0.223059 |
| Suc_F | AC_Kazan_DualAxeSword_Com_Guard_Suc_U_Normal / Properties.Notifies[12].LinkValue, xxEnableCancelSK | 0.20352352 | 0.269837 |
| Suc_L | AC_Kazan_DualAxeSword_Com_Guard_Suc_R_Normal / Properties.Notifies[11].LinkValue, xxEnableCancelSK | 0.20348024 | 0.269778 |
| Suc_R | AC_Kazan_DualAxeSword_Com_Guard_Suc_L_Normal / Properties.Notifies[11].LinkValue, xxEnableCancelSK | 0.20391607 | 0.270371 |
| End | AC_Kazan_DualAxeSword_Com_Guard_End / Properties.Notifies[6].LinkValue, xxEnableCancelSK | 0.19871478 | 0.198715 |

Suc_L/R는 앞선 PlaybackPlan의 실제 원본 consumer 매핑을 유지한다. 비슷한 이름으로 임의 교환하지 않았다.

원작 Notify는 source 시간축이다. 이미 보정된 Guard source를 다시 retime하지 않고 기존 [PlaybackPlan](../../Metadata/InGamePlayback_20261002/PlaybackPlan.json)의 inverse_map으로 시간을 대응했다. (playback, source) 인접 표본을 찾고 선형 보간한다.

```text
t_playback = p0 + (p1 - p0) * (t_source - s0) / (s1 - s0)
```

Start의 segment AnimPlayRate는 원본 1이다. 이전 속도 보정의 0.5초→0.25초는 원작 Dilation 시간축에서 온 것이며 “원본 segment Rate=2”라고 설명하지 않는다. Suc의 Dilation 길이는 0.41662917초이고 기존 bake 계획이 60fps 25frame=0.41666667초로 맞췄다. 곡선 속도 변화가 있어 단순히 Notify에 하나의 배율을 곱하지 않는다. 이 작업은 그 보정된 pose/rate/frame grid를 보존했다.

Montage 전체 타임라인은 Start 0 / Suc_F 0.25 / Suc_L 0.66666667 / Suc_R 1.08333333 / End 1.5초이며 총 4.1초다. 각 섹션 Next=None. 실제 저장된 branching InputEnd 절대 시간은 0.223059 / 0.519837 / 0.936445 / 1.353704 / 1.698715초다.

전체 Guard 17 시퀀스에 InputEnd 이름의 point marker를 추가했다. 실제 Ability 이벤트는 위 Montage의 PlayMontageNotify branching point 5개에서 받는다. Loop/8방 이동은 회복부 없는 유지 포즈로 0초 표시 정책이며, Ability가 Start/성공 종료 후 InputEnded 상태를 유지한다. 시퀀스 point marker 자체를 Montage delegate 발생기로 설명하지 않는다. 0초 표시의 TriggerTimeOffset=0.0001초는 시작 경계 Notify의 기술적 offset이며 새로운 gameplay 대기 시간은 아니다.

GuardBreak Start/End에는 현재 clip 길이의 80% 위치를 임시 marker로 표시했다(각각 1.17333336 / 0.8초). 원작 취소 경계는 미확인이고 GuardBreak는 runtime에 아직 연결하지 않았다. Break Loop는 0초 표시다. 이후 실제 GuardBreak를 구현할 때 원작/피격 정책과 함께 확정해야 한다.

추가 수치:

| 값 | 지위 / 이유 / 조정 위치 |
| --- | --- |
| 성공 regen 지연 0.5초 | 원작 직접 확인: New/SB_Kazan_DualAxeSword_Com_Guard_Normal_New.json의 xxGuardSkillInfo.Properties.GuardStaminaRecoveryDelayTime. GA defaults의 GuardStaminaRecoveryDelay |
| Montage Blend In/Out 0.1초 | 어시스턴트가 선택한 임시 표현값. 원작 일치 미검증. 짧은 0.25초 Start의 cancel 경계를 보존하며 빠른 전환을 위한 값. Montage에서 조정 |
| ABP Guard 포즈/이동 선택 0.1초 | 임시 표현값. BlendListByBool Inertialization 및 ResetChildOnActivation. 방향 전환/무기·상체 pop/발 미끄러짐을 실제 화면으로 조정 |
| End 이동 복귀 관성화 0.24초 | 기존 Combo 복귀 정책 재사용. 원작 Guard 동일값 미확인. GA defaults에서 조정 |
| BlendOutTriggerTime=0 | 새 게임 타이밍 추정이 아닌 clip 끝에서 blend 시작하는 에셋 정책. 짧은 Start의 InputEnd 이전 조기 blend를 피함 |
| Montage/BS rate 1 | 이전 작업에서 이미 bake한 source를 그대로 재생. Player mesh 0.01을 시간 배율로 사용하지 않음 |
| 스태미너 피해량 | 호출 공격의 데이터 값. 고정 정상 Guard 성공 Cost는 이번 metadata에서 확정하지 않음. JustGuard의 14를 정상 Guard Cost로 사용하지 않음 |

## 9. 실제 검증과 남은 범위

- KhazanEditor Win64 Development cold build 성공. 초기 gameplay 변경 빌드와 최종 테스트 변경 빌드를 모두 저장했다.
- 새 Editor 프로세스에서 Cost/Cooldown 없음, key/grant 각 1회, GE modifier/태그, Montage 5 Notify, 9 BS sample, ABP UP_TO_DATE 재검사.
- Guard 17 시퀀스의 기존 root/playback 속성·frame grid 보존. 앞선 retime된 Start/Suc 4개는 RAW/압축 전체 본의 기존 5개 checkpoint와 대조했다. marker 추가 외 pose 재작성 없음.
- 2026-10-02 10:39:05~10:39:21 UTC 실제 DevMap PIE의 `Khazan.Guard.PIE` Automation 결과 Success. 활성화/유지 무료, Start 이후 유지, 8방향 및 비LockOn F, 부적절/과다 Cost 거절, 연속 3회 성공과 정확한 차감·Suc 선택, regen 지연, release 방어 즉시 해제, 성공 중 release→End, End InputEnd 이동 중단, X 공격 교체, tap, 입력 Cancel, 늦은 callback, End 자연 종료/재활성화, UnPossess 정리를 검사했다.
- 최종 random 관측은 F/F/R이며 앞선 동일 로직 실행에서는 F/L/L이었다. 세 섹션이 모두 관측됐으나 이 표본으로 통계적 분포를 검증했다고 의미하지 않는다.
- DevMap의 기존 TEST_Monster 4개는 CharacterDefinition=None 오류 2종을 각각 4회 낸다. 테스트에 정확한 기존 fixture 메시지만 expected error로 명시했다. Guard assertions/다른 오류를 무시하는 설정은 아니다. 최초 자동 검사 실패와 디버거 중 정지로 watchdog이 지난 시도는 성공 자료에서 제외했다.
- 디버거에서 실제 Guard CanActivate 지상/섹션 통과, GE handle 적용, Start 인스턴스/Anim snapshot을 확인했다. agent 중단점은 제거, user exception 중단점 8개 보존, attach 종료.
- PIE를 종료하고 이전 /Game/Maps/L_StormPass_Environment로 복귀했다. dirty content/map package=0. 기존 환경/렌더링의 동시 변경은 보존했다.

물리 LShift/LB 입력 및 화면의 blend 품질은 미검증이다. computer-use의 Windows native helper가 pipe unavailable(os error 2)이어서 직접 키/마우스를 제어하지 못했다. 위 PIE는 새 개발 전용 C++ 테스트가 native gameplay API를 호출한 검사이며 Python으로 이동/키 입력을 주입하지 않았다.

실제 적의 타격→방어 방향/방어 불가 판정→HP 피해 생략은 아직 소비자가 없어 미검증이다. EndPlay는 기존 DestroyActiveState→Ability 취소의 정리 경로를 사용하며 이번에 별도의 파괴 테스트를 실행하지 않았다. 기존 X 공격의 Guard 교체는 검사했지만 모든 Dodge/Charge/스킬 조합의 화면 회귀까지 완료한 것은 아니다.

직접 플레이 QA: Guard 키를 짧게/길게 누르고 해제, LockOn 8방향 및 비LockOn, Start/Suc/End InputEnd 전후 X/Y/A/이동을 비교한다. 실제 적 공격 구현 때 TryGuardHit 반환에 따른 HP 처리와 스태미너 부족/GuardBreak를 연결한다. 상태는 GE/Spec/Ability가 소유하도록 유지한다.

## 10. 재개 자료

- [GuardAssetAudit.json](../../Metadata/GuardImplementation_20261002/GuardAssetAudit.json)
- [GuardPoseAudit.json](../../Metadata/GuardImplementation_20261002/GuardPoseAudit.json)
- [InputEndPlan.json](../../Metadata/GuardImplementation_20261002/InputEndPlan.json), [OriginalTimingEvidence.json](../../Metadata/GuardImplementation_20261002/OriginalTimingEvidence.json)
- [RuntimeResult.json](../../Metadata/GuardImplementation_20261002/RuntimeResult.json), [PIETest.log](../../Metadata/GuardImplementation_20261002/PIETest.log)
- [FinalAnimGraph.txt](../../Metadata/GuardImplementation_20261002/FinalAnimGraph.txt), [GuardMontage.t3d](../../Metadata/GuardImplementation_20261002/GuardMontage.t3d)
- [ColdBuild.log](../../Metadata/GuardImplementation_20261002/ColdBuild.log), [FinalColdBuild.log](../../Metadata/GuardImplementation_20261002/FinalColdBuild.log)
- 작업 전 29개 파일 백업: Saved/GuardImplementation_20261002/Before/Manifest.json 및 동일 하위 경로. 기존 기록/변경 보존용이며 현재 파일 위에 일괄 복원하지 않는다.

테스트 재실행은 DevMap에서 `Automation RunTests Khazan.Guard.PIE` → Test Started 이후 새 PIE 시작 순서다. Automation은 앞선 PIE를 닫는다. 지상 Player/ASC/AnimInstance 준비를 기다린 후 검사하며 30초는 테스트 watchdog이다. 이 숫자/방향 표본 각도/Cost 계산은 검사 fixture이고 gameplay tuning 값이 아니다.


## 2026-10-06 — GuardLocomotion 실제 재생 오류 수정 및 검증 완료

### 이전 검증 범위의 정정과 확인한 문제

10월 2일 기록의 “8방향 통과”는 AnimInstance의 GuardMovementDirectionAngle과 에셋 SampleData 배치를 검사한 결과다. 실제 Blend Space 노드의 sample cache/재생 클립/출력 포즈까지 검사한 결과가 아니었다. 기존 기록은 보존하며, 이 절로 그 검증 범위를 정정한다.

10월 6일 실제 PIE에서 방향각은 올바르지만 다음 클립이 재생됐다.

| 캐릭터 기준 입력 | 입력 각도(도) | 수정 전 실제 재생 | 수정 후 실제 재생 |
| --- | ---: | --- | --- |
| F | 0 | Wark_L | Wark_F |
| RF | 45 | Wark_F | Wark_RF |
| R | 90 | Wark_R | Wark_R |
| RB | 135 | Wark_B | Wark_RB |
| B | -180/180 | Wark_B | Wark_B |
| LB | -135 | Wark_RB | Wark_LB |
| L | -90 | Wark_RF | Wark_L |
| LF | -45 | Wark_LF | Wark_LF |

Wark는 기존 에셋 철자다. 경로는 /Game/_Art/Player/Animation/InGame/DAS/Guard/Locomotion/Player_Guard_Wark_<방향>이다.

원인은 BS_DAS_Player_Guard의 SampleData와 BlendSpaceData.Segments가 서로 다른 배열 순서를 참조한 것이다. 기존 LockOn Walk BS를 복제한 뒤 새 SampleData를 각도순으로 교체했지만 복제된 segment index는 예전 배열 순서 0,7,5,3,2,4,6,8,1을 유지했다. 그래서 정면 0도에서 index 4(F)가 아닌 index 2(L)를 읽었다. 실제 디버거에서 KZGuardAbilityPIETest.cpp:249에 정지하고 GameThread의 Active.BlendSpacePositionX=0, cache SampleDataIndex=2 / Player_Guard_Wark_L / TotalWeight=1을 확인했다. 최적화 빌드의 stack은 CheckGuardMotion 한 프레임만 노출했으며 더 긴 호출 경로를 관측했다고 주장하지 않는다. 증거는 [DebuggerEvidence.json](../../Metadata/GuardLocomotion_20261006/DebuggerEvidence.json)이다.

설치된 UE5.8.2 Engine/Private/Animation/BlendSpace.cpp의 UBlendSpace::PostEditChangeProperty는 SampleData 교체 시 ResampleData를 호출하지 않는다. PostLoad의 ValidateSampleData도 최신 asset의 segment index를 다시 생성하는 경로가 아니다. 입력/카메라 각도나 캐릭터 스케일을 고칠 문제가 아니었다.

### 실제 변경과 보존

- 게임 에셋 변경은 Guard BS 한 개의 파생 BlendSpaceData.Segments 재생성이다. UBlendSpace::ResampleData를 호출해 인접 index 0–1, 1–2, …, 7–8로 다시 만들고 저장했다. 재시작 후 재출력 결과도 일치한다.
- 기존 authoring script의 author_blendspace에 resample_guard_blendspace 호출을 추가해 같은 오류의 재생성을 막았다. Python에 노출되지 않은 non-UFUNCTION이므로 설치 UE5.8.2 Win64의 exported native API를 정확한 Guard BS 경로/타입/버전 검증 뒤 호출한다. UObject layout/segment 메모리를 직접 덮어쓰지 않는다. 스크립트 helper만 추가했으며 새 runtime class/helper는 없다.
- 개발 전용 KZGuardAbilityPIETest.cpp를 보완했다. UAnimInstance::GetUngroupedActivePlayersRead의 공개 API로 실제 노드의 cache를 읽는다. 이 API는 진행 중인 parallel animation task 완료를 기다린다. 테스트가 별도로 방향→클립 가중치를 계산한 값을 실제 cache라고 기록하지 않는다.
- Guard Ability/AnimInstance C++와 ABP_Player의 작업 시작 대비 SHA256은 동일하다. ABP의 시작 시 dirty 표시 때문에 disk 7파일과 live Blueprint 전체 .copy를 백업했으며, 재시작 뒤 현재 ABP를 그대로 유지했다. graph export tool의 길이 제한으로 잘린 AnimGraph.txt만을 전체 백업으로 취급하지 않는다.
- 9 sample의 위치/에셋/RateScale, interpolation/wrap, 원작 기반 bake, Guard 17 source, mesh 0.01 및 root data를 변경하지 않았다. 전후 BS .copy 차이는 BlendSpaceData 한 property뿐이다.
- 백업은 Saved/GuardLocomotion_20261006/Before/Manifest.json, ABP_Player.copy, BS_DAS_Player_Guard.copy다. [ChangeManifest.json](../../Metadata/GuardLocomotion_20261006/ChangeManifest.json)은 실제 보존/변경 파일을 구분한다.

### 이번에 통과한 실제 검사

KhazanEditor Win64 Development cold build 성공 후 새 Editor PID24936/UE5.8.2에서 저장된 BS를 reload했다. DevMap PIE의 Khazan.Guard.PIE는 2026-10-06 01:01:11.865~01:01:38.080 UTC에 Result=Success다.

- 8방 중심에서 실제 재생 clip이 모두 위 수정 후 표와 일치하고 sample weight=1, 노드의 output 기여 weight=1이다. looping과 직전 tick 대비 sample time의 진행도 검사했다.
- 179도는 B 0.977778 + RB 0.022222, -179도는 B 0.977778 + LB 0.022222였다. 1/45와 44/45는 현행 45도 간격의 선형 샘플 블렌드에서 계산한 검증값이다. 원작 gameplay 임계값이 아니다.
- 카메라 yaw 90/Actor yaw 0에 카메라 전진 입력이면 R, 카메라 yaw 0/Actor yaw 90에 카메라 전진 입력이면 L이다. fixture는 기존 LocomotionComponent constraint로 LockOn rotation mode를 선택하고 Controller yaw로 Actor facing을 유지한다. 실제 타깃 획득/LockOn 버튼/카메라 입력 장치를 조작한 검사가 아니다.
- 비LockOn에서 측면 입력을 줘도 실제 F clip이며, 이동 입력 해제 뒤 Guard_Loop sequence가 출력에 기여한다.
- 위 단일 clip checkpoint 12개에서 실제 mesh local pose와 해당 압축 sequence의 실제 재생 시각 포즈를 동일 RequiredBones/retarget/root 정책으로 대조했다. 각 checkpoint 227본, 최대 local translation 차이=0, scale 차이=0, 정규화 quaternion 각도 차이 약 0.000002415도다. 뒤 경계 두 사례는 2clip 혼합이므로 단일 clip 비교에서 제외했다.
- 첫 테스트의 0.03~0.05도 quaternion 오차는 비단위 float pose quaternion에 AngularDistance를 적용한 비교식 문제였다. 양쪽 quaternion을 정규화해 수정했고 허용치를 느슨하게 변경하지 않았다. 허용치/0.25초 관측 margin/검사 watchdog은 검증용 값이며 게임 동작 수치가 아니다.
- 기존 무료 활성화·유지, 잘못된/과다 stamina 피해 거절, 연속 3회 성공/정확한 차감/Suc 선택/회복 지연, release 즉시 방어 해제, success 중 release→End, End InputEnd 후 이동 중단, X로 교체, tap, input cancel, late callback, End 자연 종료/재활성화/UnPossess cleanup도 함께 통과했다.

자료: [RuntimeResult.json](../../Metadata/GuardLocomotion_20261006/RuntimeResult.json), [PIE_AfterFix.log](../../Metadata/GuardLocomotion_20261006/PIE_AfterFix.log), [수정 전 실패 log](../../Metadata/GuardLocomotion_20261006/PIE_BeforeFix.log), [BlendSpaceAudit.json](../../Metadata/GuardLocomotion_20261006/BlendSpaceAudit.json), [FinalColdBuild.log](../../Metadata/GuardLocomotion_20261006/FinalColdBuild.log), [BS_Reloaded.copy](../../Metadata/GuardLocomotion_20261006/BS_Reloaded.copy).

### 현재 사용 동작과 소비자

입력은 IMC_Default의 DefaultKeyMappings.Mappings에 LeftShift와 Gamepad_LeftShoulder가 IA_Guard로 각 1회 연결된다. UE5.8의 deprecated 최상위 Mappings는 비어 있어 실제 키 조사에 사용하지 않는다.

Started→Controller.Input_GuardStarted→ASC.AbilityInputTagPressed(Input.Action.Guard)→Guard Activate 순서다. GuardStateEffect의 자기 handle로 State.Guarding을 부여하고 기존 Walk 상한 constraint를 얻으며 Start를 재생한다. 입력을 누른 사실은 별도 bool이 아니라 Spec.InputPressed를 읽는다. Start가 끝나도 held면 Ability는 계속 살아 있고 ABP가 Loop/이동을 재생한다.

ABP는 bIsGuarding=true면 Guard source, 그 안의 bHasMovementInput=true면 Guard BS/false면 Guard_Loop을 선택한다. 기존 DefaultSlot은 이 source 위에 Start/Suc/End Montage를 재생하고 기존 Inertialization으로 출력한다. GameThread가 ASC tag를 snapshot에 복사하며 worker는 snapshot만 소비한다.

Completed/release는 Spec.InputPressed를 false로 만들고 InputReleased를 부른다. 그 순간 자기 Guard GE/Walk handle을 제거해 더 이상 방어하지 않는다. 현재 Start/Suc가 InputEnd 이전이면 false인 Spec을 기억하고 해당 InputEnd에서 End로 전환한다. 이미 InputEnd면 즉시 End다. End도 InputEnd에서 다음 Action을 허용하고, 유효 이동 의도가 있으면 기존 montage inertialization 요청으로 회복부를 중단한다. 입력 없이 두면 End 자연 종료 후 Ability를 끝낸다. Canceled/공격 교체/UnPossess도 자기 handle·task·delegate를 정리한다.

미래 hit resolver는 공격의 방어 가능/방향 판정 뒤 다음 실제 ASC API를 호출한다.

```cpp
bool TryGuardHit(float StaminaDamage, AActor* Attacker = nullptr);
```

StaminaDamage는 공격 데이터가 정한 양수 float다. true면 이 타격의 방어 비용을 확정한 것이므로 호출자는 동일 타격의 HP 피해를 생략한다. 성공 Ability는 GE의 GuardStaminaDamage SetByCaller에 음수 피해량을 넣고 기존 regen delay GE를 적용한 뒤 Suc_F/L/R 중 하나를 선택한다. Guard 입력/유지에는 Cost가 없고, 성공 시에만 공격 소유의 stamina 피해량을 지불한다. false는 미방어/비활성/해제/부적절한 값/스태미너 부족 등의 결과다. HP 계산이나 GuardBreak를 이 bool만으로 엔진이 자동 처리하지 않는다.

원작 0.5초 회복 지연, 원작 시간축에서 계산한 InputEnd, 기존 임시 Montage/ABP 0.1초와 복귀 0.24초의 지위/조정 위치는 8절을 유지한다. 이번 BS 수리는 새 gameplay 시간이나 임계값을 선정한 작업이 아니다.

최종 PIE Idle, editor map은 작업 시작의 DevMap, dirty content/map=0, ABP UP_TO_DATE, agent breakpoint=0, user exception 8개 보존, debugger detached다. [FinalEditorState.json](../../Metadata/GuardLocomotion_20261006/FinalEditorState.json)에 기록했다.

미검증 범위는 물리 LShift/LB 장치 입력, 연속 화면의 방향 전환/발 미끄러짐 품질, 실제 적 타격·HP·방어 각도·GuardBreak/JustGuard다. computer-use native helper는 pipe unavailable(os error2)이었다. native C++ PIE 호출로 실제 재생/포즈를 검사했으며 Python 이동·키 입력을 주입하지 않았다. 성공 시각은 mesh checkpoint 검증이며 모든 전환 frame의 시각 QA 완료를 뜻하지 않는다.


### 2026-10-06 — 검증 종료 뒤 에디터 상태 추가 관측

위 PIE Idle 정리는 01:01:38 UTC Automation 완료 직후의 상태다. 이후 이 에이전트가 실행하지 않은 별도 PIE 세션이 다시 시작/종료됐고, 01:07:36.906553 UTC 마지막 읽기 전용 관측에는 /Game/Maps/UEDPIE_0_DevMap.DevMap이 실행 중이었다. dirty content/map은 계속 0이다. 이 추가 세션을 종료하거나 입력을 주입하지 않았다. 이때 MCP ue_play(state)의 Idle 응답과 실제 UnrealEditorSubsystem game world가 일치하지 않아 native world 관측을 기록한다. 추가 세션의 물리 입력/화면 품질을 자동 테스트 결과로 계산하지 않는다. FinalEditorState.json과 RuntimeResult.json은 Automation 종료 상태와 마지막 관측 상태를 구분해 저장했다.


## 2026-10-06 — 이동 입력 중 Guard Start/End 생략 실제 적용 완료

사용자 직접 수정 요청을 적용했다. 이동 판정은 실제 CMC 속도가 아니라 기존 Player deadzone 처리 후 LocomotionComponent에 남아 있는 허용된 이동 intent다. 정지/이동 정책은 이 입력을 기준으로 하며 이전의 End 이동 전환 InputEnd 대기 정책을 아래 범위에서 대체한다.

| 시점 | 유효한 이동 입력 없음 | 허용된 이동 입력 있음 |
| --- | --- | --- |
| Guard press | 기존 Start → 유지 포즈 | Start 없이 GuardLocomotion |
| Guard release | 기존 InputEnd/End 절차 | End 없이 기본 로코모션 |
| Start 재생 중 이동 입력 발생 | 해당 없음 | Start 중단, held Guard 유지 |
| End 재생 중 이동 입력 발생 | 해당 없음 | InputEnd 전에도 End 중단·Ability 종료 |

### 실제 Source 변경과 소유 수명

runtime 수정은 기존 `KZGuardAbility.cpp`의 `InputReleased`, `PlaySection`, `HandleMoveInput` 3함수다. h/new runtime file/새 held·moving 멤버/공통 helper/BP/애니메이션 에셋 변경은 없다. 기존 ASC Spec.InputPressed, Guard GE·Walk constraint handle, 이동 이벤트 Task, InputEnd 및 ABP Guard 분기를 재사용한다.

- InputReleased: 자기 Guard GE/Walk handle을 즉시 해제한 뒤 기존 HandleMoveInput을 먼저 호출한다. 입력이 남아 있으면 종료돼 End를 예약하지 않는다. 입력이 없을 때는 기존 정지 release 예약/End 경로다.
- PlaySection: Start/End를 생성하기 전에 CurrentSection을 설정하고 동일한 이동 처리 함수를 호출한다. Start를 생략하면 CurrentSection=None인 active held Ability로 반환하고, End를 생략하면 inactive로 반환한다. Notify/Completed에서 들어오는 End도 같은 입구로 검사한다. Suc 섹션에는 이 생략 분기를 적용하지 않는다.
- HandleMoveInput: `IsMovementInputAllowed() && Intent.InputAmount > 0`인 경우 Start/End, 또는 release된 현재 반응을 정리한다. held 상태의 Suc/유지에는 적용하지 않는다. `bContinueGuard = CurrentSection == Start && IsGuardInputHeld()`인 경우만 유지한다.
- bContinueGuard는 함수 내부 bool이며 작성·소비가 같은 GameThread 호출에 있다. 원본 상태는 기존 CurrentSection과 Spec이다. 별도 Reset/취소 handle은 추가하지 않는다. Start 생략/중단에는 SetInputEnded로 다른 Action 교체를 허용한다.
- montage 중단 전 ActiveMontageTask.EndTask → pointer null → section/instance ID 무효화 순서로 진행한다. UE5.8 PlayMontageAndWait의 수동 EndTask는 OnDestroy(AbilityEnded=false)라 montage를 자동 중단하지 않고, 종료된 Task의 Interrupted 방송도 차단한다. 그 뒤 기존 RequestMontageInertialization/Montage_Stop을 호출해 Guard 전체가 잘못 종료되는 것을 막는다.
- held 유지에서는 Guard GE/Walk constraint/Move event Task를 보존한다. release/End 이동에서는 기존 FinishAbility/EndAbility가 자기 handle과 Task/Notify binding을 정리한다. 늦은 Notify는 기존 instance ID 검사로 거른다. 성공 비용은 이미 확정된 결과로 유지하며 held Suc는 이동만으로 끊지 않는다. 이동 중 release하면 Suc에서 End 없이 복귀한다.

새 gameplay 임계값/시간은 선정하지 않았다. 복귀 관성화는 기존 `LocomotionExitInertializationDuration` 0.24초(원작 확인값이 아닌 기존 임시 표현 설정)를 재사용한다. 이미 Start/End를 재생한 경우의 중단에만 요청하며 처음부터 이동 press로 생략한 Start에는 montage가 없어 이 요청을 하지 않는다. 원작 0.5초 성공 회복 지연/기존 계산 InputEnd/RateScale/0.01 scale/8방향 BS 설정은 기존 계약이다.

### 실제 검증과 범위

- KhazanEditor Win64 Development cold build 성공. 개발 전용 기존 PIE test에 이동 press/release/tap, Start/End InputEnd 이전 이동, release 예약 중 이동, held Suc 이동/해제, 늦은 callback/Walk handle cleanup을 추가했다.
- 첫 PIE의 신규 실패 1개는 일반 로코모션을 ungrouped 목록에서만 찾은 test 관측 범위였다. 디버거 GameThread Update:215에서 bIsGuarding=false/InputAmount=1/bHasMovementInput=true를 확인했다. 엔진 proxy 함수·필드 일부는 디버거 심볼이 없어 직접 평가되지 않았다. 기존 일반 loop의 Locomotion Sync Group까지 읽도록 test만 보완하고 재빌드했다.
- 최종 PID24736, DevMap, `Khazan.Guard.PIE`: **2026-10-06 01:31:55.038~01:32:08.870 UTC Success**. 새 이동 정책 assertions와 기존 비용·성공·InputEnd·공격 교체·자연 End·Input Cancel·UnPossess 검사가 통과했다.
- 이동 press/Start 조기 중단 후 실제 Guard F clip/mesh checkpoint, 이동 release 후 실제 `Locomotion / DAS_Player_Walk_Loop / nodeWeight=1.000000`을 확인했다. 기본 이동은 tick record/출력 가중치 검사이고 기본 이동 mesh 전체 비교 완료로 확장하지 않는다. 기존 8방향 중심/뒤 경계/상대 camera·actor yaw/비LockOn F/Loop 검사를 함께 통과했다. 단일 Guard clip mesh 비교는 신규 2개 포함 14 checkpoint×227본이다.
- test fixture는 native C++ gameplay 입력 함수를 호출한다. 매 프레임 물리 Enhanced Input/CMC 주행을 재현한 검사가 아니며 물리 LShift/LB·연속 전환 화면/발 미끄러짐·실제 적 타격/HP는 미검증이다. Python 이동/키 입력 주입은 하지 않았다.
- 최종 Automation 전 background throttle 대기(3 FPS)를 해소하려고 EditorPerformanceSettings CDO의 원래 true를 notify NEVER로 잠시 false로 바꿨다. SaveConfig를 호출하지 않았고 종료 후 true로 복원했다. 최종 native game world=None, DevMap, dirty content/map=0, ABP UP_TO_DATE, agent breakpoint=0, user exception 8개 그대로, debugger detached다.

증거는 [RuntimeResult.json](../../Metadata/GuardMovementPolicy_20261006/RuntimeResult.json), [PIE_Final.log](../../Metadata/GuardMovementPolicy_20261006/PIE_Final.log), [DebuggerEvidence.json](../../Metadata/GuardMovementPolicy_20261006/DebuggerEvidence.json), [ChangeManifest.json](../../Metadata/GuardMovementPolicy_20261006/ChangeManifest.json)이다. 시작 백업은 `Saved/GuardMovementPolicy_20261006/Before/Manifest.json`이다. 다음은 실제 장치로 정지/이동 press·release 및 Start/End 도중 이동 화면을 확인하는 QA다. Guard setup/재생률/resample을 다시 수행할 필요는 없다.


## 2026-10-06 — 다른 동작 중부터 유지한 가드 입력 자동 실행 완료

사용자 직접 수정 요청을 기존 Controller 콜백 한 곳에 적용했다. 가드를 실행할 수 없는 공격/회피 중부터 입력을 유지하면 기존 Action InputEnd 또는 자연 종료 등으로 GAS 허가가 열리는 첫 Triggered update에서 Guard를 실행한다. 전체 회복 애니메이션의 끝을 별도로 기다리는 새 정책이 아니라 기존 InputEnd 전환 규칙을 재사용한다. 허가 전에 release/cancel하면 이후 자동 실행하지 않는다.

### 실제 코드와 의도

실제 Source는 작업 시작 시 이미 `GuardAction / ETriggerEvent::Triggered / Input_GuardPressed`였다. 이 binding을 유지했다. 당시 로드된 DLL의 과거 binding을 검사하지 않았으므로 기존 증상을 Started binding 하나로 확정하지 않는다. 변경은 `KZPlayerController.cpp::Input_GuardPressed`다.

```cpp
UKZAbilitySystemComponent* ASC = GetKZAbilitySystemComponent();
if (IsValid(ASC) && !ASC->HasMatchingGameplayTag(KZGameplayTags::State_Guarding))
{
    ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_Guard);
}
```

- Engine Triggered는 현 IA/IMC의 trigger 없는 Boolean 입력에서 누르는 동안 반복 호출된다. Controller는 현재 Pawn의 ASC를 기존 getter로 매번 조회한다. ASC 포인터는 지역 raw pointer로 수명을 새로 소유하지 않으며 IsValid로 사용 가능 여부를 확인한다. 인자의 const FInputActionValue 참조와 함수 이름/signature는 기존 그대로다. 현재 값은 callback 내부에서 별도 저장하지 않는다.
- State.Guarding은 Guard Ability가 자기 GE로 작성하는 공유 방어 사실이다. true면 현재 held 방어를 유지하며 추가 press를 보내지 않는다. 매 update의 일반 press가 기존 ASC의 InputEnd 동일 Spec restart에 들어가 Start/Task를 반복 생성하는 것을 막는다. Controller bool을 새로 만들지 않는다.
- false면 기존 ASC press를 재시도한다. ASC가 능력 태그 block/CanActivate/Cost 등 기존 조건을 검사하며 실패할 때 Spec.InputPressed를 원래 비소유 false로 되돌린다. 이후 Triggered update가 다시 검사한다. 성공하면 기존 Guard GE가 태그를 부여해 다음 update의 재시도가 중단된다. 허가를 무시한 강제 취소/활성화는 없다.
- Completed/Canceled는 기존 release/cancel callback을 사용하며 Triggered 반복이 끝나므로 뒤늦은 예약 실행이 없다. Guard End 중에는 State.Guarding=false라 실제 재입력 유지 시 기존 InputEnd restart 허가에 따라 다시 실행할 수 있다. UnPossess/EndPlay의 기존 Action/Spec cleanup을 유지하고 과거 Pawn 요청을 queue에 남기지 않는다.
- runtime 파일/held bool/queue/timer/ASC API/Guard Ability/몽타주 변경은 추가하지 않았다. 현재 콜백은 GameThread 입력 경로다. 태그 소유·Ability 수명·Locomotion/snapshot/ABP 책임을 바꾸지 않았고 새 gameplay 수치도 없다.

### 실제 검증·현재 키

- cold build 성공. 최초 link는 editor 종료 처리 중 DLL이 아직 잠겨 LNK1104였고, 프로세스 종료 확인 후 같은 build를 다시 실행해 성공했다. Source compile 오류가 아니며 설정을 교체하지 않았다.
- 최초 Automation은 PIE 시작 요청이 대기 한도를 지나 준비 단계에서 종료됐으며 gameplay 검사를 시작하지 않았다. 이후 Test Started→PIE 요청을 같은 도구 실행에서 연결했다. 새 native PIE: **PID26692 / DevMap / Khazan.Guard.PIE / 2026-10-06 03:02:17.808~03:02:36.401 UTC Success**.
- 기존 개발 test를 확장해 GetActionEventBindings/Execute로 실제 private Controller callback을 엔진의 공개 binding API를 통해 호출했다. native fixture가 held 동안 매 update Triggered를 재현한다. WeakAttack/Dodge InputEnd 전 불허 → 허가 관측 → 자동 Guard, 유지 중 Start 반복 없음, held Guard를 공격으로 교체한 뒤 동일 hold로 복귀, 허가 전 release/cancel 미실행, active Guard의 Canceled cleanup을 검사했다.
- 기존 이동 Start/End 생략 18개 assertion, 8방향 actual sample/mesh·뒤 경계/상대 yaw/비LockOn F/Loop, 기본 Locomotion Sync Group 출력, 성공 비용/자연 End/UnPossess도 함께 통과했다. 새 held 검사의 숫자·observer margin·watchdog은 개발 test 절차이며 gameplay tuning으로 이관하지 않는다.
- 현재 실제 키는 `/Game/Input/IMC_Default` DefaultKeyMappings의 `IA_Guard → LeftShift / Gamepad_LeftShoulder(LB)`다. IA_Guard와 해당 mapping triggers=[]다. 사용자 표현 RB와 달라 비동기 키 선택 질문을 보냈지만 별도 응답이 없어 현행 mapping을 보존했다. 키 변경은 적용하지 않았고 IMC/IA SHA256도 backup과 동일하다.
- 물리 LB/LShift 장치 입력과 Enhanced Input의 실제 키 상태 판정/매 frame CMC 주행·연속 화면 QA는 native callback 검사와 구분한다. Python 이동/키 입력 주입은 없다. 모든 공격/스킬/피격 상황의 전수 회귀를 완료했다고 확장하지 않는다.
- 테스트 동안 editor background throttle의 원래 true를 notify NEVER로만 잠시 해제했다. SaveConfig를 호출하지 않았고 원래 true를 복원했다. 최종 관측 2026-10-06T03:03:47.447678+00:00: native game world 없음, DevMap, dirty content/map=0.

증거: [RuntimeResult.json](../../Metadata/GuardHeldInput_20261006/RuntimeResult.json), [PIE_Final.log](../../Metadata/GuardHeldInput_20261006/PIE_Final.log), [ChangeManifest.json](../../Metadata/GuardHeldInput_20261006/ChangeManifest.json). 백업: `Saved/GuardHeldInput_20261006/Before/Manifest.json`. 다음 화면 QA는 공격·회피 전부터 가드를 유지 → InputEnd 전환 → held 유지 → 중간 공격 후 가드 복귀 → 허가 전 release/cancel 순서다.


## 2026-10-12 — ARCH-90 패링 준비본: 실제 검증 / Main 잠금

기존 Guard/ASC/Combo/MonsterSkillObject 6 runtime 파일의 작은 확장으로 시작 후 0.146초 전방 blockable 적중을 패링한다. 원작 raw 0.292초를 현재 GuardStart inverse_map으로 계산했으며 비용 배율 0.5와 effect detach 0.06초는 직접 source 값이다. 기존 몬스터 Definition의 사용자 결정 ParryStaminaDamage와 Pattern Parried/고갈 정책을 재사용한다. 새 runtime class/file/태그/GE/Manager는 0개이며 새 DEV test 1개다. Source·책임·cleanup·값 구분·에디터 설정·검증은 [PARRY_IMPLEMENTATION_20261012.md](PARRY_IMPLEMENTATION_20261012.md)에 기록했다.

task-owned ParryWork의 실제 melee/field 15개 상황과 6종 몬스터, 고갈/좌측 response/비용/동일 HitGroup/독립 연타/Release/Cancel/UnPossess를 확인했다. 기존 Guard와 PlayerAttackCollision도 성공했다. 기존 5개 재생 segment·notify는 fresh reload로 동일하며 Montage refresh의 Suc_R 파생 cache 차이는 따로 기록했다. 원작 normal Guard의 JustGuard 설정을 그대로 복원한 것이 아니라 사용자 요청에 따른 시작 창 adapter다.

**Main 구현 반영은 미완료다.** GA_Player_Guard와 AM_DAS_Player_Guard가 기존 Main editor PID19752의 Windows 공유 잠금(error32)으로 대기한다. 대상 SHA 충돌0이며 Source·package를 부분 복사하지 않았다. 사용자/foreign editor 종료·제어0, private DLL/과거 manifest 복원0이다. 현재 잠금과 candidate SHA는 Metadata/Parry_20261012/DeliveryPreflight.json, 준비본 검증과 정확한 재개는 PreparedVerification.json/ResumeState.json을 따른다.



## 2026-10-12T08:17:34+09:00 — ARCH-90 패링 Main 적용·fresh 검증 완료

이전 준비본/Main 잠금 대기는 패링 범위에서 해소됐다. Main Source7(runtime6/DEV1)/package13(기존2/신규11)을 SHA 확인·백업 후 전달했다. 현재 전체 Main Source/Config로 MainBuild02가 성공한 뒤 일반 stock build가 현재 모듈 UnrealEditor-Khazan.dll을 선택했다. 이를 과거 suffix로 되돌리지 않고 현재 모듈에서도 다시 검증했으며 actual loaded DLL과 동일한 Source/13 asset SHA가 FinalVerification.json에 결속됐다. MainBuild01은 copy2의 과거 mtime 때문에 구 UHT PROLOG13/BODY16을 재사용하여 실패했다. 두 전달 헤더의 시각만 갱신해 PROLOG15/BODY18을 생성했고 제품 코드 내용은 바꾸지 않았다. 후속 전달 도구는 현재 write time을 사용한다.

새 MainPIE02의 Parry15개 상황/6종 Definition 소비·고갈·비용·연타·이동 Guard·좌측 response·release/cancel/UnPossess, 기존 Guard와 PlayerAttackCollision 회귀가 모두 성공했다. MainSavedAudit02는 저장0으로 설정/원본 5 playback segment·notify/7 section/source tag를 reload 검사했다. 실제 .13/.24초 화면에서 모션/weapon contact flash/연속 alpha를 직접 검수했다. 정상 가드 후 성공으로 창을 다시 열지 않으며 전방 blockable 공격만 패링한다. 기본 .146초는 기존 source→current inverse_map 계산, 비용 .5와 detach .06초는 source 값, 몬스터 ST 피해는 기존 Definition 사용자 결정이다.

이후 혈액 작업의 KZMonster runtime2/기존 DEV2와 모든 다른 Source/Config를 보존했다. 사용자/foreign editor 제어0·private DLL 복원0·Audio Notify 수정0이다. 초기 RHI에 GPU memory budget/낮은 FPS 표시가 관측됐으며 이번 fixed-step 기능 검사로 성능을 검증했다고 주장하지 않는다. 실제 스피커 출력(-nosound), 원작 shader/pixel/impact-point 완전 일치와 Shipping/network는 미확인이다. 필수 잔여0이며 최신 결과는 Metadata/Parry_20261012/FinalVerification.json과 ResumeState.json을 따른다. 과거 전체 author/추출/옛 alias를 다시 적용하지 않는다.

