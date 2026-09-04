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
