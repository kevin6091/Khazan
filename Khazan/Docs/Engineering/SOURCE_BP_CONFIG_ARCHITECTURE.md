# Source / Blueprint / Config 아키텍처

## 런타임 클래스와 BP

| 역할 | C++ | Blueprint / Asset |
| --- | --- | --- |
| GameMode | `AKhazanGameMode` | `/Game/Bluprints/BP_GameMode` |
| PlayerController | `AKhazanPlayerController` | `/Game/Bluprints/BP_KhazanPlayerController` |
| Player Character | 프로젝트 캐릭터 클래스 | `/Game/Bluprints/BP_KhazanCharacter` |
| GameInstance | `UKhazanGameInstance` | `/Game/Bluprints/BP_GameInstance` |
| AssetManager | `UKhazanAssetManager` | Config 지정 C++ singleton |
| Primary Asset Data | `UKhazanAssetData` | `/Game/Data/PDA_AssetData` |
| Input Data | `UKhazanInputData` | `/Game/Data/DA_InputData` |

실제 Content 폴더명이 `Bluprints`이므로 경로 철자를 임의로 `Blueprints`로 고치지 않는다.

## 시작 경로

1. `DefaultEngine.ini`의 기본 맵은 `/Game/Maps/DevMap`이다.
2. `BP_GameMode`가 `BP_KhazanPlayerController`와 `BP_KhazanCharacter`를 선택한다.
3. `BP_GameInstance`의 native parent는 `UKhazanGameInstance`다.
4. `UKhazanGameInstance::Init()`이 현재 `UKhazanAssetManager::Initialize()`를 호출한다.
5. AssetManager는 `PDA_AssetData`를 로드하고 `AssetLabel.PreLoad` 그룹을 프리로드한다.
6. PlayerController는 `AssetData.InputData` GameplayTag로 `DA_InputData`를 얻어 `IMC_Default`, `IA_Move`, `IA_Turn`을 설정한다.

## Config 정본

- `Config/DefaultEngine.ini`
  - `GameDefaultMap=/Game/Maps/DevMap.DevMap`
  - `EditorStartupMap=/Game/Maps/DevMap.DevMap`
  - `GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C`
  - `AssetManagerClassName=/Script/Khazan.KhazanAssetManager`
- `Config/DefaultGame.ini`
  - PrimaryAssetType `KhazanAssetData`
  - Specific asset `/Game/Data/PDA_AssetData.PDA_AssetData`

## 소스 책임

- `Source/Khazan/System/KhazanAssetManager.*`: Primary Asset 조회, 프리로드, 동기 로드와 release
- `Source/Khazan/System/KhazanGameInstance.*`: 현재 AssetManager 초기화 진입점
- `Source/Khazan/Data/KhazanAssetData.*`: source group과 GameplayTag 기반 runtime index
- `Source/Khazan/Data/KhazanInputData.*`: MappingContext와 InputAction 조회
- `Source/Khazan/Player/KhazanPlayerController.*`: Enhanced Input 등록과 이동·회전 입력 처리
- `Source/Khazan/KhazanGameplayTags.*`: Asset/Input GameplayTag의 선언과 정의

## 2026-09-02 Animation 런타임 구조

| 역할 | 구현/에셋 |
| --- | --- |
| 공통 상태·발 위상 제어 | `UKhazanAnimInstance` |
| 무기별 clip/tuning | `UKhazanLocomotionProfile : UDataAsset` |
| 현재 프로필 | `/Game/_Art/Kazan/Animation/Locomotion/Profiles/DA_Locomotion_DualAxeSword` |
| 런타임 clip | `/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword` |
| 출력 ABP | `/Game/_Art/Kazan/Character/Bluprints/ABP_Player` |

- `NativeUpdateAnimation()`이 `CharacterMovementComponent`의 velocity/acceleration/falling을 읽어 gait, 상태, 방향 차이와 발 위상을 갱신한다.
- C++이 선택한 sequence는 `PlaySlotAnimationAsDynamicMontage()`로 프로필의 `DefaultSlot`에 재생된다.
- `SetLocomotionProfile()`은 현재 montage를 정리하고 동일한 ABP에서 무기 데이터만 교체한다.
- 대검처럼 pose만 다른 무기는 새 profile로 추가한다. 무기별 상태 흐름 자체가 달라질 때만 Linked Anim Layer를 도입한다.
- 수학 연산은 `UKismetMathLibrary::MakeRotFromX`와 `NormalizedDeltaRotator`, 주 데이터는 `FVector`를 사용한다.

## 2026-09-03 Animation 런타임 아키텍처 전환 기준

> 이 섹션은 2026-09-02 Animation 런타임 구조를 현재 아키텍처로 대체한다. 이전 섹션은 롤백 전 구현 이력으로만 보존한다.

### 현재 구조

| 역할 | 현재 구현/상태 |
| --- | --- |
| 최소 런타임 관측값 | `UKhazanAnimInstance`의 `Velocity`, `GroundSpeed`, `bShouldMove`, `bIsFalling` |
| 미완성 관측값 | `Acceleration`은 선언만 되어 있고 현재 갱신되지 않음 |
| 무기별 Locomotion Profile | 없음. `UKhazanLocomotionProfile` 타입과 DualAxeSword 프로필 에셋 제거됨 |
| 보존 애니메이션 데이터 | `/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword`의 `RT_DAS_*` 16개 |
| 출력 ABP | `/Game/_Art/Kazan/Character/Bluprints/ABP_Player` 보존, 롤백 후 Compile/PIE 재검증 대기 |
| Motion Matching / Chooser | 미도입 |
| Linked Anim Graph / Layer | 미도입 |

현재 C++은 `NativeUpdateAnimation()`에서 최소 이동 값을 수집할 뿐, animation sequence를 선택하거나 `PlaySlotAnimationAsDynamicMontage()`로 Locomotion을 구동하지 않는다.

### 목표 책임 경계

| 계층 | 책임 |
| --- | --- |
| PlayerController / Character / Gameplay Component | 이동 입력 의도, 회전 의도, 이동 모드, 장착 무기처럼 게임플레이 권한이 필요한 상태를 결정한다. |
| AnimInstance 게임 스레드 수집 | `CharacterMovementComponent` 등 UObject에서 애니메이션에 필요한 값을 안전하게 스냅샷한다. |
| AnimInstance thread-safe 파생 계산 | 스냅샷만 사용해 속도 방향, 가속/감속, 로컬 방향, trajectory 입력용 파생값을 계산한다. UObject 직접 접근은 하지 않는다. |
| Main ABP | 공통 pose 파이프라인, 캐시, inertialization, additive/slot 합성을 소유한다. |
| Chooser / Pose Search / Motion Matching | 장착 무기와 이동 조건에 맞는 데이터베이스 및 최적 pose를 선택한다. 데이터 확보와 품질 감사 뒤 도입한다. |
| Linked Anim Graph / Layer | 무기별로 그래프 구조나 상체/전신 규칙이 실제로 다를 때만 하위 Anim BP를 교체한다. |

- Locomotion clip을 C++ 조건문과 Dynamic Montage로 직접 지시하는 방식을 다시 도입하지 않는다.
- Montage/Slot은 공격, 회피, 피격, 처형처럼 명시적 액션 재생 계층에 사용한다.
- 무기 차이가 clip/DB 선택뿐이면 Chooser 또는 데이터 자산으로 해결하고, 단순 데이터 차이 때문에 하위 ABP를 복제하지 않는다.
- `Scripts/Animation/build_dual_axe_locomotion_assets.py` 및 기존 감사/PIE 추적 스크립트는 롤백 전 구조 전용이다. 새 데이터 계약과 ABP가 확정될 때까지 현재 자동화로 취급하지 않는다.

## 2026-09-08 캐릭터 전체 확장성 검토 — 설계 제안, 미적용

- 최신 사용자 범위는 HeinMach/StormPass의 플레이어·일반 적·보스와 이동/액션/피격까지 포함한다. 현재 로코모션 상태는 [정본](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md), 리팩터링 검토는 [CHARACTER_ARCHITECTURE_REVIEW_20260908.md](CHARACTER_ARCHITECTURE_REVIEW_20260908.md)를 따른다.
- 실제 현행: 공통 Character가 LocomotionComponent를 소유하지만 CMC gait 속도 적용은 Player에 남아 있다. Monster의 native 구현과 Controller Input_Attack는 비어 있다. Khazan native GAS/AttributeSet 구현과 GameplayAbilities/GameplayTasks 모듈 연결은 확인되지 않았고 ABP_Player에는 Linked Anim 노드가 없다.
- 권장안은 공통 이동 정책/제약 합성, GAS 중심 액션 수명, 공통 관측과 세트별 Linked Layer 표현 분리, 캐릭터 정의 데이터와 AI/Encounter 소비자 분리다. 구체적 클래스/에셋 후보는 아직 구현·사용자 승인된 현행 구조가 아니다.
- 별도 LocomotionMath와 AnimInstance 입력각 관측부터 늘리던 제안은 철회한다. 실제 소비 없는 프로퍼티는 BP/Redirect 참조 검사 후 정리하고 게임플레이 이동과 포즈 선택을 서로 다른 소유 영역에 둔다.
- 이번에는 native/현재 ABP 읽기와 Epic 공식 문서 비교, 문서/검사 리포트 작성만 했다. 게임 코드/ABP/에셋/Config 변경, 빌드/PIE/성능 측정은 없다.

## 2026-09-08 전체 목표 구조 v1 확립 — 런타임 이관 전

- 사용자 요청에 따른 채택 구조/책임/파일 배치/구현 순서 정본은 [CHARACTER_GAMEPLAY_ARCHITECTURE.md](CHARACTER_GAMEPLAY_ARCHITECTURE.md)다. 앞선 검토 섹션의 설계 후보를 후속 구현 기준으로 구체화했다.
- 목표: Character 소유 제어 HFSM + GAS 실행 계층 + 공통 Locomotion/CMC 정책 + Main 관측/Locomotion Linked Layer + 데이터 기반 Player/Monster/Boss 구성. 공격 수명을 별도 AttackState와 Ability가 중복 소유하지 않는다.
- v1은 싱글플레이와 Character 소유 ASC를 설계 전제로 삼는다. AI는 BT/Blackboard에서 같은 요청 계약을 사용하고, 보스 페이즈와 Encounter/Checkpoint/저장은 별도 gameplay 소유자에 둔다.
- 현행 Source/BP/Config는 바꾸지 않았다. GAS 및 새 FSM/Linked Layer는 아직 미구현이며, 현행 로코모션 계약은 [현재 구현 정본](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md)이다.
- 다음 구현은 새 정본의 A1부터 작은 단위로 진행한다. 이전 개별 Pivot 가이드의 필드 추가부터 재개하지 않는다.

## 2026-09-08 목표 구조 v2 확정 — 현행 게임 파일 변경 없음

- 목표 정본은 [Tag–Ability v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2)다. v1의 필수 제어 HFSM과 A0–A7은 [M0–M10](CHARACTER_TAG_ABILITY_MIGRATION.md) 및 ASC 태그/효과 중심 상태 계약으로 대체한다.
- 현행은 계속 Character의 LocomotionComponent, Player의 CMC 속도 적용, Main AnimInstance의 관측/loop·Stop 선택이다. Khazan ASC/Ability/AttributeSet/CombatResponse/Linked Layer가 이미 구현됐다고 해석하지 않는다.
- [M1 안내](CHARACTER_TAG_ABILITY_STEP_1.md): GameplayAbilities 플러그인과 GameplayAbilities/GameplayTasks 모듈을 명시하고, Character에 엔진 ASC/IAbilitySystemInterface를 연결한다. PostInitializeComponents에서 최초 ActorInfo, 빙의 변화에서 Refresh, EndPlay에서 실행 정리를 설명했다. 아직 Source/uproject/Build.cs에 적용하지 않았다.
- 추가로 확인한 현행 우회는 Controller의 Input_Jump→Character.Jump 및 테스트 PlayDynamicForceFeedback다. M3에 공통 액션 요청과 결과 기반 피드백으로 이관한다.
- M2 태그/공통 이동, M3 최소 Player/적 전투, M4 애니메이션 분리 이후 장비/워핑/상호작용/Turn·Pivot/보스·진행을 확장한다. 실제 파일/에셋 생성은 각 소비 단계에서 한다.



## 2026-09-09 M1 현재 구현과 M2.1 예정 소비 경계

- [현재] Khazan.uproject의 GameplayAbilities, Build.cs의 GameplayAbilities/GameplayTasks, Character의 IAbilitySystemInterface/UAbilitySystemComponent 및 ActorInfo Init/Refresh/EndPlay가 실제 반영됐다. Player/Monster는 공통 부모를 상속한다.
- [제안/미적용] [M2.1](CHARACTER_TAG_ABILITY_STEP_2.md)은 기존 Character/Component/KhazanLocomotionComponent에 ASC tag 관측과 입력 허용 조회를 추가하고, Player/Anim GT가 이를 소비하게 한다. 새 CharacterStateMachine/Khazan ASC subclass는 생성하지 않는다.
- 이동 태그는 Block.Movement.Input, 검사 효과 제안 경로는 /Game/Tests/Gameplay/GE_Test_BlockMovement다. 효과 자산과 BP 검사 노드는 아직 생성하지 않았다.
- [남음] Player의 CMC MaxWalkSpeed/회전 설정, CharacterDefinition 데이터, AI PathFollowing 구동은 M2 후속 소단계다. ActorInfo가 연결됐다는 이유로 이 데이터/정책과 GameplayReady가 이미 준비됐다고 보지 않는다.


## 2026-09-09 M2.2·M2.3 제안 파일/BP 경계

- [현재 조사] `BP_KhazanPlayer`는 KhazanPlayer 부모이며 CDO의 MovementComponent는 base CharacterMovementComponent다. Walk/Run/Sprint 170/470/600과 CMC 300/15/1800/1800/Yaw540의 다중 작성 상태를 `Saved/ImportReports/M2_2_3_CurrentCDO_20260909.json`에 기록했다.
- [현재 조사] 표적 Swordsman/Archer 수입 BP는 AActor 부모다. 기존 시각 에셋을 M2.3에서 임의 reparent하지 않는다.
- [제안/미적용 C++] `Data/KhazanCharacterDefinition`, `Character/Movement/KhazanCharacterMovementComponent`, `AI/KhazanAIController`를 실제 소비와 함께 추가한다. Character는 Definition 선택, Locomotion은 policy/CMC 작성, Player/AI는 intent adapter, AIController는 path request 수명을 소유한다.
- [제안/미적용 BP] `/Game/Data/Character/PDA_Character_Khazan`, `/Game/Data/Character/PDA_Character_M2TestMonster`, `/Game/Test/M2/BP_KhazanMonster_M2Test`, 시험 AIController/Blackboard/BT/Probe/진단 ABP를 단계별로 만든다. Test 자산을 생산 Player/적 로직의 영구 의존으로 연결하지 않는다.
- M2.2 빌드/Player 검증 뒤 M2.3 default subobject class를 변경하고 다시 전체 빌드한다. 기존 inherited CharacterMovement를 삭제하거나 두 번째 movement component를 만들지 않는다.
- 세부 코드는 [Step 2의 연속 가이드](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)에 있다. 현재 게임 파일/에셋에는 적용하지 않았다.


## 2026-09-11 Character Definition Data Asset 생성과 이름 정리

- `/Game/Data/Character/DA_Character_Khazan`이 `UKhazanCharacterDefinitionData : UDataAsset` 인스턴스로 생성됐다. 아직 `PDA_AssetData` 또는 Player BP에 연결되지 않았다.
- 책임 중심 에셋 이름 규칙 `<Prefix>_<Responsibility>[_Variant]`에 따라 최종 권장 경로는 `/Game/Data/Character/DA_CharacterDefinition_Khazan`이다.
- C++ 타입 `UKhazanCharacterDefinitionData`, catalog key `AssetData.CharacterDefinition.Khazan`, selector `CharacterDefinitionAssetName`, 내부 필드 `LocomotionConfig`는 각각 타입·lookup key·선택자·하위 설정의 다른 책임을 나타낸다.
- 이번 기록은 실제 파일 존재와 미참조 상태를 확인한 명명 안내다. 에셋 rename, catalog/BP 연결, 빌드/PIE는 수행하지 않았다.


## 2026-09-11 Character Definition 에셋 rename 완료 확인

- 실제 콘텐츠는 `/Game/Data/Character/DA_CharacterDefinition_Khazan` 하나이며 이전 `DA_Character_Khazan`은 없다. 현재 catalog와 Player BP에는 아직 연결되지 않았다.
- 다음 소스 checkpoint는 `UKhazanAssetData`의 PostLoad runtime lookup 재구축·nullable Find API와 `UKhazanAssetManager`의 GameplayTag 기준 단일 cache다. 기존 InputData 소비자는 preload된 cache만 읽는 `FindLoadedAssetByName()`으로 이관한다.
- 이번 기록에서는 Source/BP/Config/uasset을 직접 수정하거나 빌드/PIE하지 않았다.


## 2026-09-11 AssetManager 과잉 보강 복원 완료

- 사용자 승인 범위에서 `KhazanAssetManager.h/.cpp`, `KhazanAssetData.h/.cpp`, Controller의 두 getter 사용처를 복원했다. 기준은 Git HEAD의 기존 설계이며, Manager cpp는 341줄에서 204줄로 줄였다(원래 192줄).
- `GetAssetByName()`의 ResolveObject→필요 시 TryLoad, public path/name/label load·release, `TMap<FName, TObjectPtr<const UObject>> NameToLoadedAsset`를 복원했다. `FindLoadedAssetByName`/private `LoadAssetByPath`/tag cache/반복 stale 검사/타입 오류 로그 확장은 제거했다. Controller는 이번 정리 후 HEAD와 동일하다.
- 남긴 차이: PostLoad/PreSave 공통 index rebuild, 누락 path의 빈 값 반환, 누락 label의 nullable pointer 반환, catalog 누락 시 안전한 return, 데이터 로드 실패 Error 로그, label load의 중복 개별 IO 제거 및 batch handle의 지역 보존, path FName 기준 cache·release 대칭이다. BP `_C` 보정은 기존의 수정된 로컬 `AssetEntry`를 name/label 양쪽에 넣는 본문으로 복원했다.
- `ReleaseByName(FName)`은 기존 경로의 asset leaf name을 받는다. `AssetData.InputData`와 같은 catalog tag를 넣는 API가 아니다. Release는 manager의 보관 참조를 제거하며 다른 UObject 참조까지 강제로 해제하지 않는다.
- 최종 저장본의 전체 Development Editor 빌드 및 DevMap 새 프로세스 시작/종료는 통과했다. 상세 로그와 Python 보조 검사의 접근 제한은 [진단 기록](BUILD_RUNTIME_DIAGNOSTICS.md)의 같은 날짜 절에 기록했다.
- Character Definition tag/selector/catalog/BP 연결과 gameplay 값은 수정하지 않았다. 다음 사용자 적용 절차는 [Step 2 복원 후 연결 절차](CHARACTER_TAG_ABILITY_STEP_2.md#asset-manager-rollback-next-20260911)를 따른다. 앞 절의 tag cache/FindLoaded 이관 안내는 이 절이 대체한다.
