# Build / Runtime 진단 기록

> 컴파일·링크·Assert·Crash는 날짜와 시그니처별로 하단에 누적한다. 동일 시그니처는 기존 기록과 최신 Crash report를 먼저 비교한다.

## 2026-08-31 DevMap 시작 Crash 연쇄

### 1단계: AssetManager 초기화 누락

- 시그니처: `UKhazanAssetManager::GetAssetByName<UKhazanInputData>()`의 `check(AssetData)`.
- 실패 값: `UKhazanAssetManager::LoadedAssetData == nullptr`.
- 호출: `AKhazanPlayerController::SetupInputComponent()` (`KhazanPlayerController.cpp:36`) → `GetAssetByName()` (`KhazanAssetManager.h:57`).
- 원인: 당시 `DefaultEngine.ini`에 `GameInstanceClass`가 없어 `UKhazanGameInstance::Init()`과 `UKhazanAssetManager::Initialize()`가 실행되지 않았다.
- 증거 Crash:
  - `Saved/Crashes/UECC-Windows-2075EB2B46750EBF6FC211B263A51EF5_0000`
  - `Saved/Crashes/UECC-Windows-E76C87044E586E565D88C6B5F299E5DB_0000`
- 현재 상태: `GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C`가 Config에 존재해 이 단계는 통과한다.

### 2단계: PreLoad label runtime index 누락과 null 역참조

- 최초 실패: `UKhazanAssetData::GetAssetSetByLabel()`의 `AssetLabelToSet.Find(AssetLabel.PreLoad)`가 null이다.
- Ensure: `KhazanAssetData.cpp:53`, `Cant find Asset Set from Label [AssetLabel.PreLoad]`.
- 실제 Crash: ensure 뒤 `return *AssetSet`을 실행해 null address Access Violation이 발생한다.
- 호출: `GetAssetSetByLabel()` → `UKhazanAssetManager::LoadSyncByLabel()` (`KhazanAssetManager.cpp:82/83`) → `LoadPreloadAssets()` (`:174`).
- 증거 Crash:
  - Ensure: `Saved/Crashes/UECC-Windows-A2836D9D4E0C7E96E4AF88A51505E452_0000`
  - Access Violation: `Saved/Crashes/UECC-Windows-A2836D9D4E0C7E96E4AF88A51505E452_0001`
- 표적 확인: `/Game/Data/PDA_AssetData`의 source `AssetGroupNameToSet`은 1개 그룹을 보유하지만 runtime label index에는 `AssetLabel.PreLoad` 키가 없다.
- 유력 원인: `AssetLabelToSet`과 `AssetNameToPath`가 `PreSave()`에서만 재생성되므로 새 C++ 필드가 추가된 기존 Data Asset을 재저장하지 않았거나, 런타임 로드 시 캐시 생성이 보장되지 않는다.

### 권장 수정 순서

1. `UKhazanAssetData::RebuildRuntimeIndexes()`를 만들고 `PostLoad()`에서 호출한다. Editor 저장용 `PreSave()`도 같은 helper를 호출해 로직을 한 곳에 둔다.
2. `GetAssetPathByName()`은 lookup 실패 시 빈 `FSoftObjectPath`를 반환한다.
3. `GetAssetSetByLabel()`은 포인터/optional/`TryGet` 형태로 바꾸고, `LoadSyncByLabel()`이 누락 label을 로그 후 안전하게 중단하게 한다. `ensure` 후 역참조는 금지한다.
4. 단기 확인용으로 `PDA_AssetData`를 새 코드 상태에서 한 번 저장할 수 있지만, 이것만으로 해결하면 asset 재저장 의존성이 남으므로 구조적 수정으로 완료 처리하지 않는다.
5. 장기적으로 `UKhazanAssetManager::StartInitialLoading()`에서 `Super` 호출 뒤 프리로드해 GameInstance 설정 누락과 초기화 순서 결합을 제거한다.
6. PlayerController에서 InputData, MappingContext, EnhancedInputComponent, InputAction, LocalPlayer, Pawn을 각각 검증한다.

### 수정 후 검증

1. Editor 완전 종료 후 C++ 빌드와 새 Editor 실행.
2. 초기화 로그에서 AssetManager class, `PDA_AssetData`, source group 수, name/label index 수를 확인.
3. DevMap PIE에서 `AssetLabel.PreLoad`와 `AssetData.InputData`가 정상 해석되는지 확인.
4. `IMC_Default`, `IA_Move`, `IA_Turn` null 여부와 이동·회전 입력을 확인.
5. PIE 종료/재실행과 Standalone 새 프로세스에서 두 Crash 시그니처가 재발하지 않는지 확인.

### 현재 적용 상태

- Config에는 GameInstanceClass가 존재한다.
- 2단계 C++ 수정과 검증은 아직 수행하지 않았다.
- 로그와 호출 스택이 실패 값과 줄을 직접 특정했으므로 동일 사실을 얻기 위한 디버거 attach는 수행하지 않았다.

## 2026-09-02 Editor 캡처 도구 실패와 금지 규칙

### 확인된 실패

- Rider 경유 `unreal.AutomationLibrary.take_high_res_screenshot()` 호출은 background automation 문맥에서 실행되어 `AppTime.cpp:38`, `Ensure condition failed: IsInGameThread()`을 발생시켰고 파일도 남기지 못했다.
- 여러 editor viewport config key를 순회·변경한 Python은 `EditorViewportClient.cpp:748`, `Ensure condition failed: !bCheckMissingOverride || bRemoved`로 Editor를 종료시켰다.
- 이때 노출된 `{"detail":"Bad Request"}`는 위 실패/연결 단절을 전달하던 도구 transport 응답이며 Khazan 게임 API나 프로젝트 런타임 오류가 아니다.

### 이후 안전 규칙

- 위 두 방식은 재시도하지 않는다: HighResScreenshot automation API 금지, 다중 viewport config 순회/변경 금지.
- 캡처가 반드시 필요할 때만 먼저 `ue_health`로 연결을 확인하고, active viewport가 확실한 상태에서 Rider의 단일 `take_screenshot`을 한 번 호출한다.
- viewport 선택이 불확실하거나 로그/감사 report로 검증 가능한 경우 캡처를 생략한다.
- 캡처용 임시 actor나 editor 상태를 Level에 저장하지 않는다.

### 안전 방식 확인

- 단일 Rider 캡처로 생성된 검수 파일: `Saved/Screenshots/WindowsEditor/RiderMCP/20260902-053101_editor_window.png`.
- 이후 Fog/Lighting 최종 판정은 스크린샷 API 재호출 없이 정적 report, source transform hash, material compile log와 Level audit를 사용했다.

## 2026-09-02 Locomotion 전체 빌드 결과

- 명령 대상: `KhazanEditor Win64 Development`, UE 5.8 UBT, `-WaitMutex -FromMsBuild`.
- 결과: `Succeeded`; `UnrealEditor-Khazan.lib/.dll` 링크와 `KhazanEditor.target` metadata 생성 완료.
- 신규 Locomotion C++과 기존 프로젝트 모듈을 포함한 non-unity adaptive build에서 compile/link error 0건.
