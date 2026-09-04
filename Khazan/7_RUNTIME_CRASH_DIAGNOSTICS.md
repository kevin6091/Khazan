# 런타임 크래시 진단 기록

> 런타임 크래시는 이 문서에서 날짜·레벨·시그니처별로 누적 관리한다.
> 새 조사에서는 프로젝트 문서 1–7과 최신 `Saved/Crashes`의 동일 시그니처를 먼저 확인하고, 기존 기록으로 설명되지 않을 때만 조사 범위를 넓힌다.
> 기존 기록은 덮어쓰거나 삭제하지 않고 하단에 추가한다.

## 2026-08-31 DevMap PIE 시작 직후 Assert

### 결론

- 기본 레벨은 `/Game/Maps/DevMap`이며 PIE GameMode는 `BP_GameMode_C`다.
- 직접 크래시 시그니처는 `UKhazanAssetManager::GetAssetByName<UKhazanInputData>()`의 `check(AssetData)`다.
- 해당 시점의 실제 실패 값은 `UKhazanAssetManager::LoadedAssetData == nullptr`다.
- `AKhazanPlayerController::SetupInputComponent()`가 `AssetData.InputData`를 요청하지만, 그 전에 `UKhazanAssetManager::Initialize()`가 실행되지 않았다.
- `UKhazanAssetManager::Initialize()`는 현재 `UKhazanGameInstance::Init()`에서만 호출된다.
- `BP_GameInstance`는 `UKhazanGameInstance`를 부모로 갖지만 `Config/DefaultEngine.ini`의 `GameMapsSettings`에 `GameInstanceClass`가 지정되어 있지 않다. 따라서 기본 `UGameInstance`가 사용되고 커스텀 `Init()`이 호출되지 않는 것이 근본 원인이다.
- `PDA_AssetData`, `DA_InputData`, `IA_Move`, `IA_Turn`, `IMC_Default`와 `AssetData.InputData` 매핑은 존재한다. 이번 Assert는 에셋 파일 누락이 아니라 초기화 생명주기 누락이다.

### 재현 및 증거

- 최신 크래시: `Saved/Crashes/UECC-Windows-2075EB2B46750EBF6FC211B263A51EF5_0000`
- 직전 동일 크래시: `Saved/Crashes/UECC-Windows-E76C87044E586E565D88C6B5F299E5DB_0000`
- 두 보고서 모두 `KhazanAssetManager.h:57 -> KhazanPlayerController.cpp:36` 순서의 동일 Assert다.
- 호출 경로: `DevMap -> BP_GameMode_C -> BP_KhazanPlayerController -> SetupInputComponent -> GetAssetByName -> check(LoadedAssetData)`.
- 이번 조사는 위 두 크래시 보고서, 관련 Config/C++ 파일, `BP_GameInstance`, `PDA_AssetData`, `DA_InputData`만 표적 확인했다. 프로젝트나 Content 전수조사는 수행하지 않았다.

### 우선 해결안

1. 즉시 복구는 `[/Script/EngineSettings.GameMapsSettings]`에 다음 설정을 추가하는 것이다.

   ```ini
   GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C
   ```

   실제 폴더명이 `Bluprints`이므로 위 경로 철자를 그대로 사용한다. Blueprint 계층이 필요 없다면 `/Script/Khazan.KhazanGameInstance`도 가능하지만, 현재 존재하는 BP를 유지하는 구성을 우선한다.

2. 구조적 해결은 `UKhazanAssetManager::StartInitialLoading()`을 override하고 `Super::StartInitialLoading()` 뒤에 프리로드를 수행하는 것이다. UE 5.8 엔진은 커스텀 AssetManager 생성 직후 이 훅을 호출하며, AssetManager가 자신의 필수 데이터를 초기화하게 하면 GameInstance 프로젝트 설정 누락에 의존하지 않는다.

3. `check(AssetData)`만 제거하는 것은 해결책이 아니다. 초기화 누락을 숨기고 입력만 비활성화할 수 있다. 다만 별도 방어 코드로 null, 잘못된 GameplayTag, InputAction, MappingContext, LocalPlayer, Pawn을 검사하고 원인을 포함한 로그를 남기는 것은 필요하다.

### 후속 위험과 하드닝 대상

- `UKhazanAssetData::GetAssetPathByName()`과 `GetAssetSetByLabel()`은 `ensureAlwaysMsgf` 실패 뒤 null 포인터를 역참조한다. 실패 시 빈 값 또는 nullable 결과를 반환하도록 바꿔야 한다.
- `LoadPreloadAssets()`의 `LoadPrimaryAssetsWithType(...)->GetLoadedAsset()`은 타입에 여러 Primary Asset이 생기면 모호하다. 명시적인 PrimaryAssetId 또는 `GetPrimaryAssetObject()` 기반으로 고정하는 편이 안전하다.
- `SetupInputComponent()`는 EnhancedInputComponent와 두 InputAction의 유효성을, `BeginPlay()`는 LocalPlayer와 MappingContext를, `Input_Move()`는 Pawn을 검사해야 한다.

### 수정 후 검증 절차

1. Editor를 완전히 종료하고 다시 실행한다.
2. DevMap에서 PIE를 시작한다.
3. `UKhazanGameInstance::Init()` 또는 AssetManager의 `StartInitialLoading()`이 `SetupInputComponent()`보다 먼저 실행되는지 확인한다.
4. `LoadedAssetData`가 `PDA_AssetData`이며 `AssetData.InputData`가 `/Game/Data/DA_InputData`로 해석되는지 확인한다.
5. `IMC_Default`, `IA_Move`, `IA_Turn`이 null이 아니고 이동·회전 입력이 동작하는지 확인한다.
6. 새 Editor 세션의 PIE와 Standalone을 각각 한 번 실행해 같은 시그니처가 재발하지 않는지 확인한다.

### 현재 적용 상태

- 진단은 완료했다.
- 사용자의 요청이 원인 조사와 해결안 모색이므로 이번 단계에서는 C++과 Config를 변경하지 않았다.
- 구현 시에는 우선 `GameInstanceClass` 설정으로 즉시 복구한 뒤, AssetManager 자체 초기화와 null 방어를 별도 변경으로 진행한다.
