# Heal의 무기 수납·발도 — 2026-10-06

## 요구사항과 구현 범위

| 사용자 요구 | 실제 구현 책임 |
| --- | --- |
| 물약은 빈손으로 사용, 무기는 등에 수납 | 기존 Player의 두 무기 Mesh Component를 기존 BackPack 본으로 재부착. Heal Ability가 변경 전 상태를 저장 |
| 수납 → Heal → 발도 → 다음 동작 | 기존 UpperBody Montage의 Stow/Heal 섹션 뒤 Arms Montage를 같은 Heal Ability에서 재생 |
| 발도는 팔만, 나머지는 이동 입력에 따라 움직임 | ABP의 Arms Slot/양쪽 clavicle Branch Filter. 발도 시작에는 Heal Walk 상한도 반환 |
| 발도 중 공격·회피·가드·피격에 즉시 양보 | 발도 시작 SetInputEnded → 기존 GAS Action block 해제/cancel. End에서 무기 복구 및 이전 instance만 blend 0 종료 |
| 클립은 InGame/DAS 사용 | Armed/UnArmed 두 Sequence를 UE rename으로 InGame/DAS/Equip 이동. 원래 위치는 redirector |

원래 HP/MaxHP 200, 회복 +100, 무제한·Cost 없음, DPad Down 입력은 유지한다. 자동 다음 액션을 새로 queue하는 기능은 만들지 않았다. 이동은 계속되고, 발도 중 들어온 전투 입력은 즉시 기존 Ability를 실행한다. 물약 사용이 끝나기 전의 Action 차단은 유지한다. 현재 피격 Ability/적 공격·HP 피해 시스템은 없으므로 **미래 피격이 이 취소 경로를 사용할 기반**까지 구현하며 실제 적 공격 시험 완료로 표현하지 않는다.

## 작은 변경의 구성

새 runtime 파일/클래스/Component/Task/Manager/장비 상태 태그는 **0개**다. 기존 [KZHealAbility.h](../../Source/Khazan/Ability/PlayerAbility/KZHealAbility.h)·[cpp](../../Source/Khazan/Ability/PlayerAbility/KZHealAbility.cpp)만 게임 C++에서 확장했다. 개발 검증은 기존 KZHealAbilityPIETest.cpp에 추가했다. Controller/ASC/AttributeSet/Character/LocomotionComponent/AnimInstance는 이번 기능 때문에 수정하지 않는다.

Heal과 발도는 필요한 본 범위가 다르다. 기존 Heal은 spine 아래 상체 전체, 발도는 양팔만이다. 서로 다른 Slot을 사용해야 하므로 **발도 Montage 1개**를 추가했다. 별도 Draw Ability 대신 기존 PlayMontageAndWait를 두 단계에서 재사용한다. Task factory를 기존 클래스의 PlayHealMontage 함수로 옮겼다. 처음 Task의 완료는 발도 시작, 두 번째 Task의 완료는 Heal 실행 종료다. 실행 단계는 이미 필요한 HasInputEnded로 구분하며 별도 phase enum/bool을 만들지 않았다.

Armed/UnArmed는 원래 존재한 클립이다. BP_Player의 실제 SCS 컴포넌트는 DualAxeSword_Original_L/R, parent CharacterMesh0, hand bone Weapon_L/R, relative transform 위치·회전 0/scale 0.009다. Body Mesh Component는 0.01이다. Weapon_L/R는 각 Hand 아래, BackPack는 Spine2 아래다. 이름의 `소켓` 접미사가 붙은 BackPack 부착점도 UE Socket UObject가 아닌 **Skeleton의 자식 본**이었다. 기존 Bone 이름을 그대로 사용하며 Socket UObject를 중복 생성하지 않았다. 시작 감사: Metadata/HealWeapon_20261006/EquipAudit.log.

## 실행 순서

1. DPad Down → 기존 Controller → ASC의 Heal Spec → CanActivateAbility/CommitAbility.
2. 기존 Walk 제한 handle을 얻고 UpperBody HealMontage를 시작한다. Stow 섹션은 UnArmed다. 아직 손을 등에 가져가는 중에는 무기가 손에 있다.
3. WeaponStow Notify: 두 무기의 원래 부착을 먼저 저장한 뒤 BackPack 본에 붙인다. 두 Mesh는 숨기거나 복제하지 않는다.
4. HealStart Notify: 같은 Montage의 기존 BlendIn 시간으로 관성화를 요청해 Stow→Heal의 segment 경계 포즈 전환을 완화한다. Heal 섹션은 기존 Heal_01이다.
5. Heal Notify: 기존 bHealApplied를 먼저 true로 만들고 기존 instant GE를 한 번 적용한다. 이후 같은 Notify가 반복돼도 두 번 회복하지 않는다.
6. UpperBody Montage 완료: DrawMontage/Armed Task 시작 → Walk handle 반환 → SetInputEnded. 이제 일반 gait와 다른 Action 활성화가 허용된다.
7. WeaponDraw Notify: 원래 hand bone/relative transform을 복구한다. Armed는 무기를 손에 쥔 채 발도 후반을 계속한다.
8. 입력이 없으면 Armed 끝까지 재생하고 EndAbility. 전투 액션이 시작되면 기존 GAS가 Heal을 취소하고 해당 액션을 실행한다. 무기는 Notify를 기다리지 않고 취소 즉시 손으로 복구한다.

회복 전에 강제 취소되면 HP는 증가하지 않는다. 회복 후 발도를 취소해도 이미 적용한 HP는 유지된다. 정상 탭의 Completed는 기존처럼 물약 실행을 취소하지 않는다. UnPossess/EndPlay는 기존 ASC 실행 취소가 같은 EndAbility 정리를 사용한다.

## 변수의 용도와 수명

| 멤버 | 타입·값·작성자/소비자·정리 시점 |
| --- | --- |
| HealMontage | TObjectPtr<UAnimMontage>, GA defaults가 설정, Ability/엔진 Task가 소비. 기존 에셋에 Stow와 Heal을 연결 |
| DrawMontage | TObjectPtr<UAnimMontage>, GA defaults에서 새 Arms Montage 설정. 첫 Task 완료 시 재생. 장비 상태 사본이 아닌 표현 데이터 참조 |
| HealEffect | TSubclassOf<UGameplayEffect>, 기존 GE_Player_Heal. 회복량의 실제 작성자는 GE modifier이며 C++에 100을 중복 보관하지 않음 |
| LeftBackSocket/RightBackSocket | FName, 기존 Weapon_L_BackPack소켓/Weapon_R_BackPack소켓. Ability defaults에서 조정할 수 있는 부착점 이름. Socket API는 Skeleton bone도 지원 |
| StoredWeapons | TArray<FStoredWeapon>, 이번 실행이 실제 변경한 두 부착의 snapshot. WeaponStow에서 작성, WeaponDraw/End에서 소비 후 Reset. 글로벌 equipped bool이 아님 |
| FStoredWeapon.Component | TWeakObjectPtr<USceneComponent>, 기존 무기 component. Ability가 객체 수명을 연장하지 않음 |
| FStoredWeapon.Parent | TWeakObjectPtr<USceneComponent>, 변경 전 mesh parent. cleanup 시 살아 있는 경우에만 재부착 |
| FStoredWeapon.HandSocket | FName, 변경 전 hand bone. 좌우를 component 이름 추정 대신 실제 attachment socket으로 구분 |
| FStoredWeapon.RelativeTransform | FTransform, 변경 전 위치·회전·scale. 정상/강제 취소 때 정확히 원래 값 복구. 0.009를 C++에 다시 상수로 넣지 않음 |
| BoundAnimInstance | 기존 weak ptr. 이번 avatar의 notify delegate를 구독하고 End에서 자기 delegate만 해제 |
| ActiveMontageInstanceId | 기존 int32, Task 재생 뒤 엔진 instance ID. 단계 전환마다 INDEX_NONE→새 ID, End에서 Reset. 같은 asset의 다른 실행에서 오는 Notify를 차단 |
| MovementHandle | 기존 FKZMovementConstraintHandle. 물약 단계만 Walk 상한을 소유, 발도 시작 또는 취소/실패에서 자기 handle 반환 |
| bHealApplied | 기존 bool, 이번 실행의 회복 1회 guard. activation/End에서 false, GE 적용 전에 true |

모든 attachment 변경/Notify/Task callback은 game thread에서 처리한다. AnimInstance에 장비 bool/Heal bool을 추가하거나 worker에서 Actor·ASC·component를 읽지 않는다. ABP는 엔진 Slot 평가와 기존 cached pose만 소비한다.

## 함수별 변경과 코드 의도

### CanActivateAbility / ActivateAbility / PlayHealMontage

CanActivateAbility는 기존 grounded/live HP/ASC·AnimInstance·data 검사에 DrawMontage 존재만 추가한다. 미설정 상태에서 물약을 시작하고 중간 발도가 실패하는 일을 막는다. const 함수는 데이터/현재 상태를 읽고 변경하지 않는다.

ActivateAbility의 Commit/Walk handle/notify binding은 기존 구현이다. 기존 Task 생성 부분만 PlayHealMontage(HealMontage)로 호출한다. PlayHealMontage(UAnimMontage* Montage)는 재생할 asset pointer를 받으며 소유권을 이전하지 않는다. ActiveMontageInstanceId를 먼저 비우고 기존 PlayMontageAndWait를 만들고 Completed/Interrupted/Cancelled delegate를 연결한다. ReadyForActivation 뒤에도 IsActive/weak ptr를 다시 확인한다. 동기 실패 callback이 이미 Ability를 종료할 수 있기 때문이다. 성공 시 실제 엔진 instance의 ID를 저장한다.

### StoreWeapons

```cpp
// 핵심 변경. 전체 현재 함수는 실제 cpp의 StoreWeapons를 기준으로 한다.
for (USceneComponent* Child : Mesh->GetAttachChildren())
{
    if (!Child || (Child->GetAttachSocketName() != TEXT("Weapon_L") &&
                   Child->GetAttachSocketName() != TEXT("Weapon_R"))) continue;
    StoredWeapons.Add({Child, Mesh, Child->GetAttachSocketName(), Child->GetRelativeTransform()});
}
```

먼저 기존 snapshot이 있으면 true로 돌아가 같은 Notify 중복 처리로 원래 parent를 덮어쓰지 않는다. Character/mesh와 두 BackPack 부착점이 유효한지 검사한다. 직접 자식 중 실제 hand bone에 붙은 두 component만 선택한다. 루프 중 재부착하지 않는 이유는 GetAttachChildren 목록이 변경될 수 있기 때문이다. 먼저 두 개를 snapshot한 뒤 별도 루프에서 재부착한다. 현재 DualAxeSword 데이터 계약은 두 손에 한 무기씩이므로 정확히 2개가 아니면 snapshot을 비우고 false를 반환한다.

두 번째 루프의 const FStoredWeapon&는 snapshot을 복사/변경하지 않는 읽기 참조다. 좌우 hand 이름에 따라 defaults의 BackPack 이름을 선택한다. SnapToTargetIncludingScale로 socket 위치·회전으로 붙이고, 곧바로 **저장한 relative scale**을 다시 적용한다. 임포트된 Player/무기의 다른 크기 보정을 손상시키지 않는다. 한쪽 attach가 실패하면 false로 End를 실행하고, 이미 변경된 쪽도 저장 정보로 복구한다.

### RestoreWeapons

살아 있는 component와 parent만 복구한다. KeepRelativeTransform로 원래 hand bone에 붙인 뒤 저장한 전체 relative transform을 적용한다. 수납 중의 값은 원래 hand offset이 아니므로 마지막 SetRelativeTransform이 필요하다. 이후 StoredWeapons.Reset으로 이번 실행의 변경 기록을 비운다. WeaponDraw와 End가 둘 다 호출해도 두 번째 호출은 빈 목록이라 안전하다.

### HandleMontageNotify

IsActive, Payload.SequenceAsset==GetCurrentMontage(), Payload.MontageInstanceID==ActiveMontageInstanceId를 모두 만족할 때만 실행한다. Heal asset 하나만 비교하던 기존 코드를 현재 단계의 Montage로 좁혀 Draw Notify도 처리한다. 이름별 분기는 WeaponStow→StoreWeapons/실패 종료, WeaponDraw→RestoreWeapons, HealStart→기존 Montage BlendIn으로 관성화, Heal→기존 once GE다. 애니메이션 시간과 HP·부착 결과는 Montage Notify가 연결한다. 매 tick timer나 Heal 상태 사본을 만들지 않는다.

### HandleMontageCompleted

```cpp
if (!IsActive()) return;
if (!HasInputEnded())
{
    PlayHealMontage(DrawMontage);
    if (IsActive())
    {
        // 현 소스처럼 자기 LocomotionComponent handle만 반환.
        Character->GetLocomotionComponent()->ReleaseMovementConstraint(MovementHandle);
        SetInputEnded();
    }
    return;
}
EndAbility(..., false, false);
```

위 발췌의 Character/null 검사와 End 인자는 실제 cpp에 있다. 첫 완료까지 InputEnd를 열지 않으므로 false면 물약 단계의 종료다. Draw Task 실패 시 callback이 이미 End할 수 있어 IsActive를 다시 확인한다. Walk 상한을 반환해 다른 부위의 일반 이동을 허용하고 기존 SetInputEnded로 Action block을 해제한다. 두 번째 완료에서는 HasInputEnded가 true여서 정상 종료한다. 별도 phase 상태를 중복 관리하지 않는다.

### EndAbility / HandleMontageAborted

End 시작에 BoundAnimInstance/instance ID를 지역 변수로 보존한다. notify delegate를 해제하고 기존 실행 변수 Reset, RestoreWeapons, 자기 Walk handle 반환 순으로 정리한다. Super::EndAbility가 엔진 Task를 정리한 **뒤** 취소된 이전 instance ID만 찾아 Stop(FAlphaBlend(0.f))한다. Task가 살아 있을 때 먼저 Stop하면 Interrupted callback이 재진입할 수 있으므로 이 순서가 필요하다. 같은 asset/새 montage 전체를 Montage_Stop으로 멈추지 않는다. 이미 시작한 다른 액션을 중단하지 않도록 **종료하는 instance ID**를 사용한다. 0은 새 gameplay tuning 시간이 아니라 사용자 요구의 즉시 취소를 엔진에 표현한 값이다.

정상 완료에는 0 stop을 강제하지 않고 Montage의 기존 자연 blend-out을 유지한다. Aborted는 기존 IsActive guard로 취소 End를 호출한다. 회복 GE를 역으로 적용하거나 다른 원인의 태그/제약을 일괄 지우지 않는다.

## 에셋과 ABP 연결

경로 `/Game/_Art/Player/Animation/InGame/DAS/Equip/CA_P_Kazan_DualAxeSword_Armed`, `..._UnArmed`. Heal_01은 기존 DAS/Heal 경로 그대로다. `/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal`은 UpperBody의 UnArmed→Heal, 새 `AM_DAS_Player_HealDraw`는 Arms의 Armed다. GA_Player_Heal의 DrawMontage를 새 에셋에 연결했다. Cost/Cooldown/HealEffect/Input/Definition은 변경하지 않는다.

Skeleton에 DefaultGroup.Arms를 등록했다. 기본 공격 DefaultSlot/Heal UpperBody와 같은 group이므로 엔진의 같은 group montage 교체도 기존 경로를 따른다. ABP의 기존 UpperBody Blend 출력을 Save Cached Pose `HealUpperBase`로 저장한다. UseCachedPose 두 개를 Arms Layer의 BasePose와 Arms Slot의 Source에 각각 연결하고 Arms Slot 출력을 Layer Pose0, Layer 출력을 기존 최종 Inertialization에 연결한다. 추가 노드는 5개다. Source를 항상 update한다. Arms가 없을 때 Slot도 같은 cached base를 반환해 기존 Heal 상체를 덮어쓰지 않는다.

Arms Branch Filter 두 개는 실제 Skeleton의 bip001-l-clavicle/r-clavicle, Depth0이다. 이 hierarchy 아래 손·손가락·Weapon_L/R도 포함한다. spine/neck/head/pelvis/legs는 제외한다. Arms Layer의 MeshSpaceRotationBlend=false로 각 팔의 source local 회전을 적용하고 몸통은 base를 유지한다. RootMotionBasedOnRootBone=true. 기존 UpperBody Blend의 spine/mesh-space 설정과 기존 locomotion/Guard/DefaultSlot/최종 Inertialization은 유지한다. 두 Sequence의 EnableRootMotion=false를 변경하지 않는다.

## 수치 출처와 검증 구분

| 값 | 근거와 조정 위치 |
| --- | --- |
| Armed/UnArmed 31 keys, 30 frames, 30 fps, 1s, RateScale1 | 기존 저장 Sequence의 DataModel과 기존 SourceTimelineReplacement TimingContract 실제 감사. 원작 gameplay의 equip rate/Notify timing을 직접 확인한 값이라고 표현하지 않음 |
| PSA ANIMINFO 31 samples/AnimRate31 | 원본 FModel export PSA의 원시 header. Metadata/HealWeapon_20261006/EquipPSASource.json에 원시값/hash. `(31-1)/31` 계산 결과와 기존 Sequence 1s는 서로 다르며 export header만으로 현재 source timeline을 임의 재보정하지 않음 |
| Heal_01 45 keys, 44 frames/30fps, 1.4666667s | 기존 InGame Sequence/Heal 구현 metadata. 이전 Heal 문서의 원작 NumFrames/SequenceLength 출처 유지 |
| WeaponStow0.5s, WeaponDraw0.5s | **임시 표현 설정**. 원작 Notify 미확인. UnArmed 손이 등에 도달하는 지점과 Armed 손이 등을 떠나기 시작하는 접점에 각 clip 길이×0.5. 각 Montage Notify에서 조정 |
| Heal Notify 1.7333333s | 기존 임시 Heal local `HealLength×0.5` 보존 + 기존 StowLength1s. 원작 직접 회복 시점 아님 |
| HealStart1s | Stow clip 길이로부터 계산한 segment 경계. 새 임의 timer가 아님 |
| BlendIn/Out0.1s | 기존 Heal/Guard의 임시 표현 tuning 재사용. Montage 편집으로 조정. 원작 직접 값 아님 |
| Player0.01/무기0.009 | 이번 시작의 실제 BP/component 관측값. 변경하지 않으며 playback rate에 곱하지 않음 |
| Walk→일반 gait | 기존 LocomotionComponent constraint handle 수명 변경. 새 속도·입력 deadzone 없음 |

노티파이를 추가한 에셋은 공개 RefreshCacheData로 branching cache를 생성한 뒤 저장했다. source bone key/order/RateScale/Root/topology adapter는 보존한다. Inspector 표시 상태, 실제 saved reload, build, PIE, 물리 패드/원작 일치 검증을 구분한다.

## 검증·반영 진행

착수 백업 Saved/HealWeapon_20261006/Before/Manifest.json. author tool은 Scripts/Engineering/HealWeaponAuthorEditor.cpp로 보존하되 작업용 Source에만 임시 컴파일한다. 제품 Build.cs에 editor 모듈을 추가하지 않는다. 격리 project는 C:/Users/user/Desktop/GitProject/Khazan_HealWeaponWork_20261006/Khazan이다. Python mailbox는 asset authoring/read·PIE 시작/종료만 수행한다. 플레이어 이동·키 이벤트는 개발 C++가 실제 Controller binding과 기존 Player 함수를 사용한다.

아래 후속 날짜 섹션을 실제 완료/메인 적용 정본으로 사용한다. 이 문서의 절차·코드 해설은 Source/asset 적용과 구분하며 실패 로그도 보존한다.

## 2026-10-06 — 실제 적용·검증 완료, 이동 결과 정정

- 기존 Heal runtime h/cpp만 수정했다. 새 runtime 파일/클래스0, 개발 test만 기존 파일 확장. 발도 시 Walk handle을 반환하고 SetInputEnded를 호출하므로 물약은 Walk/발도는 일반 gait다. 양쪽 BackPack 부착은 실제 Skeleton bone, 상대 component scale/hand offset을 실행마다 저장·복구했다.
- 격리 stock Build.cs/제품 의존성의 ColdBuild_Final Succeeded(14.65s), Heal PIE Success 06:29:18.543 UTC, Guard PIE Success 06:31:27.946 UTC. 새 프로세스 PID6008에서 저장 ABP/GA/두 Montage/두 이동 Sequence를 실제 로드했고 ABP UP_TO_DATE/dirty0/native game world 없음이었다. 임시 author cpp는 work Source에서 제거했고 메인에는 추가하지 않았다.
- 실제 walking checkpoint: Heal의 pelvis·양쪽 thigh/calf/foot7본은 Walk/양손2본은 Heal, Armed의 같은 하체7본과 spine/spine1/spine2/neck/head5본은 Walk/양손은 Armed. normalized local position/rotation 비교 오차0. Armed가 실제 움직이는 약0.7s 구간을 포함한다. Notify 전 무기BackPack/Notify 후 hand, visible 유지/scale·transform 복원, X 공격·Y Charge→graph-only StrongAttack·Dodge·held Guard/ASC 강제 cancel, 이전 Arms instance weight0, 회복 전 cancel/회복후 HP보존/중복Notify/자연종료/fullHP 반복/UnPossess를 검사했다. Guard는 기존8방 실제 clip·227본 pose/Start·End 이동 생략/held 재시도/성공 비용·cleanup 회귀 통과.
- 네 취소 관측의 Armed0.107~0.162s에서 실제 mesh hand/back 거리 약0.28~0.76cm였다. 관측값이며 gameplay threshold나 원작 수치가 아니다. 실제 GameViewport 캡처 HealWeapon_Stowed.png/HealWeapon_Draw.png에서 등에 두 무기를 보이고 걷는 동안 팔 발도가 재생되는 것을 확인했다. 캡처 해상도644×191의 제한된 두 프레임이며 연속 전체 화면·원작 제어 비교/물리 패드 QA 완료를 의미하지 않는다.
- **경로 이동 결과 정정:** 위 절에서 기존 위치를 redirector라고 계획했으나, UE rename은 참조가 없어 원래 두 파일을 제거했다. main AssetRegistry hard/soft/management referencers도 두 개 모두0(MainPreApplyState.json). 최종은 실제 에셋7개 선택 복사 + 백업/hash 확인한 옛 경로2개 제거다. 원래 Equip 폴더에 실제 Sequence/redirector를 남기지 않았다. 다른 source-library 클립은 이동하지 않았다.
- 메인 PID27568은 identity/DevMap/native game world 없음/dirty0을 재확인한 뒤 정상 QUIT_EDITOR로 종료했다. 새 에셋7개 installed SHA와 old paths2개 부재, 원본 Heal Sequence SHA 불변, 기존 Build.cs 동일을 검증했다. 메인 cold build Succeeded 06:35:05 UTC(33.48s), ApplyStatus=Complete. 메인은 사용자 직접 확인용 새 PID27916/DevMap으로 열었으며 메인에서 자동 PIE는 실행하지 않는다.
- 첫 감사 빌드의 FFrameTime 생성자와 author의 GetAllGraphs owner 오용은 공개 API로 수정했다. 첫 PIE의 목 비교는 비정규화 quaternion을 사용한 test 오류였고 normalized 비교로 수정; Y release 뒤 InputTag가 없는 graph-only StrongAttack을 active Input.Y로 찾던 test도 실제 Charge/StrongAttack 경계에 맞게 수정했다. runtime 로직을 잘못된 fixture에 맞춰 변경하거나 허용오차를 늘리지 않았다. 실패·최종 로그는 모두 Metadata/HealWeapon_20261006에 보존했다.
- 임시 Stow/Draw/회복 Notify·Blend의 원작 timing 일치, 물리 DPad/LB/키보드·연속 전이 품질, 실제 적 피격·피해·사망은 미검증. 피격 producer를 만들면 기존 Ability.Action 기반 cancel 또는 ASC forced cancellation을 사용하고 실제 enemy hit에서 같은 cleanup을 검사한다. 새 장비 Manager를 먼저 추가하는 다음 단계가 아니다.
## 2026-10-06 — Heal 수납·발도 메인 saved reload 최종 확인

메인 PID27916/DevMap에서 /Script/Khazan.KZHealAbility의 새 DrawMontage defaults, UpperBody Stow→Heal 길이2.4666667s, Arms Armed1s, 두 InGame/DAS/Equip sequence/rate1/rootfalse, old package paths 부재, GA의 기존 HealEffect/Cost·Cooldown None, ABP UP_TO_DATE를 읽기 전용으로 확인했다. native game world 없음/dirty content·map0이고 메인 Play는 시작하지 않았다. MainReadyAudit.json과 RuntimeResult.json이 최종 실제 상태다.

현재 사용자 확인 절차: DevMap Play → DPad Down 탭 → 이동을 유지해 UnArmed 수납/빈손 Heal/양팔 Armed와 일반 이동을 관찰. Armed 중 X/Y/A 또는 LB·LShift를 눌러 전투 우선 전환을 확인한다. 아무 전투 입력이 없으면 발도 끝까지 재생하고 종료한다. 물약 초기 full HP에서도 모션이 재생된다. 이전 두 screenshot는 제한된 정지 관측이며 이 연속 시각 QA/물리 입력을 대신하지 않는다.