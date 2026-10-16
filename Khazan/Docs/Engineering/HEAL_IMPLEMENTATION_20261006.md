# Heal 구현 — 2026-10-06

사용자 직접 구현 요청: HP/MaxHP 200, 회복량 100, 무제한 물약, Gamepad DPad Down, 이동 가능한 상체 Heal. 아키텍처 계약은 CHARACTER_GAMEPLAY_ARCHITECTURE.md의 ARCH-75다. 기존 Action/ASC/CharacterDefinition/LocomotionComponent/ABP를 재사용한다. 아래는 실제 작성한 Source와 작업용 에디터에서 저장한 에셋 계약이다. 최종 메인 적용·빌드·PIE 결과는 하단 날짜별 완료 기록으로 구분한다.

## 변경 범위와 소유자

| 파일/에셋 | 책임 |
| --- | --- |
| 기존 KZAttributeSet.h/.cpp | HP/MaxHP 원본 수치와 범위 보정. Stamina 경로 보존 |
| 기존 KZPlayerController.h/.cpp | Heal Started/Completed/Canceled를 기존 ASC 입력 함수로 전달 |
| 기존 KZGameplayTags.h/.cpp | Input.Action.Heal과 Ability.Action.Heal의 실제 두 소비자 등록 |
| 새 Ability/PlayerAbility/KZHealAbility.h/.cpp | 물약 한 실행, Montage task, 회복 Notify 1회, InputEnd, 자기 Walk 제약 cleanup |
| GE_Init_PlayerHealth, GE_Player_Heal | 사용자 지정 초기값과 회복량을 데이터로 소유 |
| 기존 DA_CharacterDefinition_Player | 기존 InitialEffects/InitialAbilityGrants에 Heal 연결을 추가 |
| IA_Heal, 기존 IMC_Default/DA_InputData | Boolean DPad Down 입력과 Spec의 exact InputTag 연결 |
| AM_DAS_Player_Heal, 기존 SK_Player/ABP_Player | 상체 Slot/마스크와 포즈 재생. 실제 애니메이션·스케일은 변경하지 않음 |

새 runtime 파일은 Heal h/cpp 2개다. Manager/Component/FSM/AbilityTask/대기열/수량·HP 사본은 없다. Main AnimInstance에 Heal bool을 추가하지 않았다. 개발 test는 게임 실행 구조와 별개다. Scripts/Engineering/HealAuthorEditor.cpp는 공개 UE editor API로 에셋을 만드는 일회성 도구로, 작업용 프로젝트에만 임시 컴파일한다. 메인 Build.cs나 runtime 모듈의 editor 의존성을 늘리지 않는다.

## 실제 입력·사용 동작

`IA_Heal → Input.Action.Heal → Controller → ASC exact InputTag Spec → GA_Player_Heal` 경로다. 입력 키는 `/Game/Input/IMC_Default`의 `Gamepad_DPad_Down` 하나다. 사용자 요청 없는 키보드 키를 추가하지 않는다.

Started 한 번에 실행하고 Completed는 입력 소유만 해제한다. 정상적인 짧은 탭도 물약 모션을 끝까지 진행한다. Triggered 반복은 연결하지 않아서 누르고 있는 동안 반복 소비하지 않는다. 다시 사용하려면 새 Started가 필요하며 InputEnd 이전의 추가 press는 기존 Action 규칙으로 처리된다. Canceled는 아직 눌림을 소유하는 Spec만 기존 ASC가 취소한다. Completed 뒤에 같은 hold의 Canceled를 인위적으로 보내는 것은 유효한 실제 입력 사이클이 아니다.

지상에서 HP가 양수이고 유효한 ASC/Attribute/Montage/Effect가 있을 때 실행한다. HP 0은 이 Ability가 부활시키지 않는다. 별도 Death/피해 시스템을 이번에 구현한 뜻은 아니다. **물약 수량·Cost·Cooldown이 없으므로 최대 체력에서도 모션을 실행할 수 있다.** HP 결과는 MaxHP를 넘지 않는다. 초기부터 HP 200인 현재 프로젝트에서 DPad Down으로 모션을 직접 확인할 수 있게 한 프로젝트 정책이며 원작의 최대 체력 사용 규칙 확인값은 아니다.

## Attribute의 의미와 보정

- `HP`, `MaxHP`: 기존 AttributeSet의 `FGameplayAttributeData`, 단위 HP point. Native 생성 상태는 0이며 CharacterDefinition의 초기 instant GE가 MaxHP부터 200, 이어 HP 200으로 설정한다. 초기화 없이 모든 캐릭터 CDO에 200을 고정하지 않는다.
- `ATTRIBUTE_ACCESSORS_BASIC`: 기존 Stamina와 같은 GAS attribute 식별자/Get/Set/Init 접근자를 제공한다. Controller/Player/AnimInstance에 체력 멤버를 따로 두지 않는다.
- `PreAttributeChange`, `PreAttributeBaseChange`의 기존 `ClampValue`에 두 분기를 추가한다. MaxHP는 0 이상, HP는 `[0, MaxHP]`다. 엔진 기본/current 값 변경 경로 둘 다 보정한다.
- `PostAttributeChange(MaxHP)`는 실제 새 최대값으로 현재 HP를 다시 제한한다. instant GE뿐 아니라 ASC의 직접 base 변경/집계 변경으로 MaxHP가 낮아지는 경우에도 HP가 초과하지 않게 한다.
- `PostGameplayEffectExecute`는 HP instant modifier 적용 후 최종 HP를 보정한다. 기존 Stamina/MaxStamina 후처리는 보존한다.

`GE_Init_PlayerHealth`는 MaxHP Override 200 → HP Override 200 순서다. HP부터 적용하면 초기 MaxHP=0에 의해 HP가 0으로 제한되므로 이 순서가 필요하다. `GE_Player_Heal`은 instant HP AddBase +100이다. 예: 50→150, 150→200, 200→200. 200/100은 사용자 지정값이며 원작 HP/회복량을 추출한 결과가 아니다.

## Heal Ability의 변수·수명

| 변수 | 작성·소비·정리 |
| --- | --- |
| HealMontage : TObjectPtr<UAnimMontage> | GA Blueprint defaults가 지정. PlayMontageAndWait와 Notify asset 필터가 읽는 정적 데이터 |
| HealEffect : TSubclassOf<UGameplayEffect> | GA defaults의 GE_Player_Heal. 회복량은 GE가 소유하며 Ability에 100 literal을 넣지 않음 |
| BoundAnimInstance : TWeakObjectPtr<UAnimInstance> | Activate에서 현재 ActorInfo의 AnimInstance를 기억하고 Notify delegate를 연결. End에서 해제·Reset |
| MovementHandle : FKZMovementConstraintHandle | Activate가 기존 LocomotionComponent의 Walk 상한을 acquire. 다른 원인의 제한을 건드리지 않고 자기 handle만 End/실패/취소에서 release |
| ActiveMontageInstanceId : int32 | Task Ready 뒤 현재 Montage instance ID를 고정. Notify가 같은 asset/실행인지 확인하고 End에 INDEX_NONE으로 Reset |
| bHealApplied : bool | 해당 실행의 중복 Notify 방지. Activate false → Heal Effect 적용 전에 true → End false. 공유 체력/상태 사본이 아님 |
| HasInputEnded() | 기존 Action base의 전환 허가. 새 실행 Reset, InputEnd Notify에서 Set, End에서 base가 정리 |

모든 UObject/ASC/CMC/Notify 처리는 Game Thread다. Worker는 기존 ABP pose graph만 평가한다. 새로운 worker의 ASC/Actor 접근은 없다. Player/미래 AI의 의도 생성자는 다르지만 동일한 캐릭터 ASC에 부여한 Heal Spec을 사용할 수 있다. Player Blueprint에 독립 실행 상태를 만들지 않는다.

## 함수·실행 순서와 취소

1. Constructor는 `Ability.Action.Heal` Asset Tag를 설정한다. 공유 `State.Healing` 소유 태그를 추가한 것이 아니다. 부모 Action의 block/cancel, InstancedPerActor/LocalOnly를 재사용한다.
2. `CanActivateAbility`는 부모 GAS 조건부터 검사하고 설정·ActorInfo·지상·Attribute·HP를 확인한다. 실패한 새 요청이 기존 동작을 먼저 종료하지 않도록 기존 ASC 승인을 그대로 사용한다.
3. `ActivateAbility`는 실행별 once/ID/InputEnd를 초기화하고 Commit한다. Walk 상한 constraint를 acquire하되 이동 입력은 허용한다. 이동·회전·gait 판정은 기존 LocomotionComponent/CMC가 계속 담당한다.
4. 현재 AnimInstance에 Montage Notify Begin delegate를 연결하고 엔진 `PlayMontageAndWait` 하나를 생성한다. Completed는 정상 End, Interrupted/Cancelled는 취소 End다. Task가 재생에 실패하면 같은 취소 cleanup 경로를 사용한다.
5. `HandleMontageNotify`는 활성 여부와 asset/instance ID를 먼저 확인한다. 다른 Montage/이전 실행의 늦은 Notify를 무시한다.
6. Heal Notify는 아직 적용하지 않았을 때만 GE Spec을 만든다. `bHealApplied=true`를 Effect 적용 전에 써서 Attribute callback의 재진입·중복 이벤트에 대비한다. Instant GE의 handle 유효성 대신 `WasSuccessfullyApplied()`를 사용한다. 적용 실패는 취소 End다.
7. InputEnd Notify는 부모 `SetInputEnded()`만 호출한다. 이후 공격·회피·가드 등 기존 Action 전환이 가능하다. 이미 적용한 회복은 이후 취소에도 되돌리지 않는다.
8. `EndAbility`는 Notify delegate, weak ref, ID/once 상태와 자기 Walk handle을 정리한 뒤 부모에게 끝냄을 전달한다. 부모/엔진이 task와 Action block 수명을 정리한다. UnPossess/EndPlay는 기존 Character의 Action 취소/DestroyActiveState를 그대로 쓴다.

정상 Completed(버튼 Release)에는 모션을 중단하지 않는다. 회복 전에 실행을 취소하면 HP가 오르지 않는다. 회복 후 취소하면 이미 확정된 +100 결과를 보존한다. 지속 GE handle이나 물약 재고 handle은 필요 없다.

## 상체·하체 AnimGraph 계약

대상 ABP: `/Game/_Art/Player/Character/Bluprints/ABP_Player`. Skeleton: `/Game/_Art/Player/Character/Meshs/SK_Player`. 기존 Slot group에 `DefaultGroup.UpperBody`를 등록하고 Heal Montage만 이 Slot을 사용한다. GAS Action은 여전히 하나씩 실행하며 새로운 전투 lane을 만들지 않는다.

```text
기존 Locomotion/Guard source → 기존 DefaultSlot → Save Cached Pose(ActionBase)
                                                       │
                               Use ActionBase ──────────┼─→ Layered Blend Base
                               Use ActionBase → UpperBody Slot → Blend Pose 0
                                                             │
                                   Layered Blend → 기존 Inertialization → Output
```

Save/Use Cached Pose로 기존 source를 한 frame에 중복 진행하지 않는다. UpperBody Slot의 Always Update Source Pose는 true다. Branch Filter는 실제 Skeleton의 `bip001-spine`을 시작점으로 하며 BlendDepth=0은 해당 가지부터 전체 적용하는 엔진 구조 선택이다. 골반·하체·루트는 이 가지의 바깥이라 base pose를 유지한다. Mesh Space Rotation Blend=true, Blend Root Motion Based on Root Bone=true다. Heal source의 기존 EnableRootMotion=false도 유지한다.

최종 Inertialization과 기존 Guard/Locomotion/Stop graph는 교체하지 않는다. Main AnimInstance에 새 변수를 넣지 않는다. 모든 Start 제외/Walk·Run 발별 Stop/Sprint 단일 Stop 정책을 유지한다. Player mesh scale 0.01을 애니메이션 재생률 계산에 섞지 않는다.

## 수치 출처와 편집 위치

| 값 | 출처·단위·변경 위치 |
| --- | --- |
| HP/MaxHP 200 | 사용자 지정 HP point. GE_Init_PlayerHealth Modifiers의 MaxHP/HP Override |
| 회복량 +100 | 사용자 지정 HP point. GE_Player_Heal Modifiers의 HP AddBase magnitude |
| 45 keys / 1.4666667 s | 원작 직접 metadata: Saved/Extracted/InGame_Playback_20261002/Metadata/BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/CA_P_Kazan_DualAxeSword_Heal_01.json, NumFrames/SequenceLength |
| 현재 RateScale 1 / root motion=false | 기존 저장 PlaybackPlan의 Heal row·작업용 loaded clip 관측. 원본 JSON에 RateScale override/Notifies가 직접 기록되지 않았음을 구분 |
| Heal 0.733333349 s | 임시 편집값: 보존된 clip 길이 × 0.5. 회복을 모션 중간에 두는 초기 선택, 원작 회복 시점 미확인. AM_DAS_Player_Heal의 Heal branching Notify에서 조정 |
| InputEnd 1.100000024 s | 임시 편집값: 보존된 clip 길이 × 0.75. 회복 이후 회수 모션 일부를 양보하는 선택, 원작 cancel 시점 미확인. 같은 Montage InputEnd branching Notify에서 조정 |
| Blend In/Out 0.1 s | 기존 Guard의 임시 표현값을 재사용한 시작 설정. AM_DAS_Player_Heal Blend In/Out에서 연속 화면의 허리/손 전환 품질로 조정 |
| Walk 속도·제약 | 현재 Definition/LocomotionComponent 설정 재사용. 새 Heal 속도 수치를 넣지 않음 |

Clip 키/RateScale/root/mesh scale은 보존한다. 새 Notify는 원본 Sequence를 편집하지 않고 새 Montage에만 둔다. Authoring은 Notifies 추가 뒤 공개 `UAnimMontage::RefreshCacheData()`로 branching cache를 갱신해야 한다. Cached Pose 노드는 공개 `PostPlacedNewNode()`로 필요한 AnimBlueprint extension을 등록해야 한다. 게임 실행에 캐시 수리 코드를 넣지 않는다.

## 검증 자료와 사용 범위

자료: `Saved/HealImplementation_20261006/Before/Manifest.json`, `Metadata/HealImplementation_20261006/`. 테스트는 `Source/Khazan/Tests/KZHealAbilityPIETest.cpp`의 `Khazan.Heal.PIE`다. 실제 Controller binding Execute로 native 콜백을 호출하며 C++에서 기존 Player 입력 경로를 frame별로 호출해 CMC 걷기와 실제 mesh pose를 검사한다. Python으로 이동/키 입력을 주입하지 않는다. 물리 DPad 장치와 전체 연속 화면 품질은 이 자동 검사와 구분한다.

첫 pose 비교는 Idle→Walk 진입 블렌드를 포함한 상태를 단일 Walk clip과 비교해 실패했다. 테스트는 이동 진입을 먼저 안정시킨 뒤 Walk effective weight 1을 확인하고 동일 source time의 compressed pose와 비교하도록 보완했다. 오차 허용치를 늘리지 않았다. 보호된 AnimInstance proxy를 직접 읽으려던 개발 test 시도는 compile 실패 후 제거했으며 runtime의 공개 API를 테스트 목적으로 늘리지 않았다.

메인 에디터는 조작하지 않는다. 작업용 snapshot/에디터에서만 build/author/PIE를 수행하고 메인 disk의 대상 hash가 작업 시작과 동일한지 확인한 뒤 선택 에셋을 적용한다. 메인의 실행 중 DLL이나 현재 열린 에셋을 강제 교체·재로드하지 않는다. 현재 열린 에디터가 이전 DLL을 사용하는 상태와 저장된 새 Source/asset의 적용 상태를 구분해야 한다.

## 2026-10-06 — Source·격리 검증 완료 / 메인 파일 잠금으로 최종 반영 대기

- 메인 Source에 기존 runtime 6파일(Attribute/Controller/Tags h·cpp)을 수정하고 Heal h·cpp 2파일을 추가했다. 개발 test는 별도다. 새 Manager/Component/FSM/Task/상태 사본 없이 기존 Action/ASC/Definition/LocomotionComponent와 PlayMontageAndWait를 재사용했다.
- 작업용 프로젝트에서 새 Montage/GA/GE 2개/IA와 기존 Skeleton/ABP/IMC/InputData/Definition, 합계 10개 에셋을 저장했다. MaxHP Override200→HP Override200/+100 instant GE, Cost/Cooldown 없음, DPad Down 단일 mapping/Heal grant를 확인했다.
- 임시 editor author cpp를 작업 Source에서 제거하고 메인과 동일한 Build.cs로 cold build Succeeded(ColdBuild_Product.log, 62.58초). 제품 모듈에 editor 의존성을 추가하지 않았다. 메인의 사용 중 DLL을 교체한 빌드와 구분한다.
- PID11600 DevMap Khazan.Heal.PIE는 05:19:13.460→05:19:29.000 UTC Success였다. 실제 Controller callback/CMC 걷기/HP·MaxHP/+100·상한/회복 전 취소/중복 Notify/InputEnd 교체/자연 종료/재사용/UnPossess cleanup을 확인했다. Walk weight1 checkpoint에서 골반·다리 7본은 Walk, 손 2본은 Heal 압축 pose와 translation/angle 차이0이었다.
- 같은 PID Khazan.Guard.PIE는 05:20:36.122→05:20:57.182 UTC Success였다. 기존 방향별 실제 clip/227본 pose, 이동 Start/End 생략, held 입력 재시도, 비용·교체·cleanup을 유지했다.
- 제품 의존성 빌드 뒤 새 PID27900에서 05:26:55.919 UTC 저장 에셋을 다시 읽었다. GE/GA/input/grant/clip 설정, ABP BS_UP_TO_DATE, DevMap/native game world 없음/dirty content·map0을 확인했다. work editor는 throttle 원래 true를 복원하고 정상 종료했다.

### 메인 에셋 적용 경계와 재개

열린 메인 에디터가 SK_Player.uasset의 Windows 파일 잠금을 유지한다. Copy와 원자적 Replace가 sharing violation으로 실패했으며 메인 대상 5개/원본 Heal Sequence는 시작 SHA256과 동일했다. **메인 Source는 적용됐지만 메인 Content 10개와 메인 DLL은 아직 반영되지 않았다.** 기존 에디터에 MCP/UI/종료/LiveCoding을 사용하지 않았다.

`Saved/HealImplementation_20261006/ReadyContent/`에 10개 검증 파일, `ApplyManifest.json`에 before/prepared/source SHA256을 저장했다. `Scripts/Engineering/apply_heal_20261006.ps1`을 validation한 뒤 숨김 helper PID28144로 -WaitForEditorExit 실행했다. 모든 메인 project editor가 exit할 때까지 기다리고, exit 후 Source/대상 hash를 다시 확인해 사용자 저장으로 달라졌다면 덮어쓰지 않는다. 정상일 때만 10개 선택 복사·hash 검사→메인 KhazanEditor cold build를 진행하며 editor를 자동 종료/재실행하지 않는다.

최신 반영 단계 정본은 `Metadata/HealImplementation_20261006/ApplyStatus.json`이다. 최초 WaitingForEditorExit/main PID25196. Complete이면 AssetInstallManifest.json의 10개 installed SHA와 ColdBuild_MainAfterApply.log의 Succeeded가 실제 메인 적용 증거다. Stopped이면 details.error의 파일/빌드 원인을 확인한다. 에디터 사용을 끝내고 Complete가 된 다음 프로젝트를 다시 연다.

helper가 없고 반영이 미완료면 다음 명령만 실행한다. author 전체 setup/graph 추가/Sequence retime을 반복하지 않는다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\Desktop\GitProject\Khazan\Khazan\Scripts\Engineering\apply_heal_20261006.ps1" -WaitForEditorExit
```

### 해결된 실패와 미검증

Cached Pose PostPlacedNewNode 누락, Montage RefreshCacheData 누락, 복사 Source timestamp로 인한 UBT 재컴파일 누락, Idle→Walk 진입을 단일 clip과 비교한 fixture, Completed 뒤 Canceled를 보낸 fixture는 수정하고 최종 검사했다. 보호된 AnimInstance proxy/AnimMontage Notifies 직접 읽기는 제거했다. Python은 격리 editor lifecycle/읽기 audit용이고 player 이동/키를 주입하지 않는다. 실패 로그는 Metadata/HealImplementation_20261006에 보존했다.

물리 DPad 장치, 연속 화면의 상체 전환/발 미끄러짐, 적 damage/death·HP UI와 임시 Notify/Blend timing의 원작 일치는 미검증이다. 격리 검증과 메인 pending 적용을 RuntimeResult.json·ChangeManifest.json·FinalEditorState.json에 분리 기록했다.

## 2026-10-06 — 사용자 요청으로 메인 반영·빌드·재시작 완료

후속 사용자 지시: “메인에 추가해줘. 직접 테스트 해보고싶어.” 앞선 대기 상태를 해소하고 메인에 실제 반영했다. 메인 PID25196의 project identity/DevMap/dirty content·map0/native game world 없음을 확인하고 정상 QUIT_EDITOR로 종료했다. 저장되지 않은 변경을 잃거나 실행 중 PIE를 중단하지 않았다. 기존 작업용 에디터에서 수행한 gameplay 테스트를 메인에서 반복하지 않았다.

반영 helper는 05:47:56 UTC에 10개 에셋을 copy/hash 검증했고 메인 KhazanEditor cold build가 05:48:35.668 UTC Complete/Succeeded였다(38.90초). AssetInstallManifest.json의 모든 10개 파일이 prepared SHA와 동일하고 검사한 Source/원본 Heal clip의 SHA도 보존됐다. 이 절은 앞선 메인 pending 기록의 후속 실제 완료 결과다.

메인 프로젝트를 새 PID27568/DevMap으로 다시 열었다. 메인에서 /Script/Khazan.KZHealAbility, GA의 Montage/GE/Cost·Cooldown None, DPad Down 단일 mapping/Heal grant/Health 초기 GE, ABP BS_UP_TO_DATE를 읽기 전용으로 확인했다. native game world 없음/dirty0, editor 화면의 Play 버튼과 DevMap을 확인했고 PIE는 시작하지 않았다. Editor launch는 시작 로그의 기존 GameFeatures startup 문제를 피하는 -EnablePlugins=GameFeatures를 사용했으며 uproject/config를 편집하지 않았다.

현재 실제 완료 증거는 Metadata/HealImplementation_20261006/MainAppliedResult.json·MainReadyAudit.json·MainReady_Editor.png·AssetInstallManifest.json·ColdBuild_MainAfterApply.log다. 앞선 RuntimeResult/ChangeManifest/FinalEditorState는 격리 검증과 대기 시점의 역사적 기록으로 보존한다. ApplyStatus.json=Complete이고 반영 helper는 종료했다.

직접 테스트: 현재 DevMap의 Play → 게임패드 DPad 아래 한 번 → 이동 입력을 유지하며 다시 사용. 상체는 물약, 하체는 Walk이고 버튼을 떼어도 정상 탭 모션은 계속된다. full HP에서도 모션을 허용하므로 초기 HP200 상태에서 바로 확인할 수 있다. HP 회복량·상한은 GE200/+100이고 실제 회복 시점은 Montage Heal Notify다. 물리 패드/연속 화면 품질은 사용자의 이번 직접 테스트 범위이며 자동 검증 완료로 선행 기록하지 않는다.

## 2026-10-06 — 후속 Heal 무기 수납·팔 발도 구현

후속 사용자 요청으로 빈손 Heal/등 수납/Armed 팔 발도/발도 중 전투 우선 전환을 기존 Heal h/cpp만 확장해 적용했다. 기존 HealMontage는 UnArmed→Heal, 새 HealDraw는 Arms→Armed이며 Main AnimInstance에 상태를 추가하지 않았다. 기존 Heal local HP notify×0.5는 유지하되 전체 타임라인은 Stow1s가 앞에 추가됐다. **이 문서의 이전 InputEnd=Heal×0.75/Walk를 종료까지 유지하는 계약은 해당 범위에서 대체:** 지금은 발도 시작에 InputEnd/Walk handle 반환, 발도는 일반 이동 허용이고 다른 Action에 즉시 양보한다.

무기 parent/socket/relative transform은 Ability 실행 snapshot에만 저장하고 Notify/종료/취소에 복구한다. HP200/+100/무제한·Cost 없음/DPad Down은 그대로다. 격리 stock build/Heal PIE·Guard 회귀와 saved reload, 메인 선택 package7개/old Equip path2개 제거/hash/main cold build가 실제 완료됐다. 변수·함수·각 단계·ABP/수치 출처·검증·미검증의 현재 정본은 [HEAL_WEAPON_PRESENTATION_20261006.md](HEAL_WEAPON_PRESENTATION_20261006.md), 자료는 Metadata/HealWeapon_20261006이다. 사용 클립은 DAS/Equip의 Armed/UnArmed이며 원본 Heal Sequence SHA는 유지됐다. 실제 적 피격은 미구현, 취소 기반만 검사했다.