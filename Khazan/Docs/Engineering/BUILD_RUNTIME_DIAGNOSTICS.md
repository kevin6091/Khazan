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


## 2026-09-09 M2.1 PIE 종료 `bHasBegunPlay` assert

- 증상: DevMap PIE는 시작되지만 Stop PIE의 `BeginTearingDown` 직후 Editor가 종료된다.
- 반복 증거: `Saved/Crashes/UECC-Windows-5507E58445FD1FB5866451848C33073A_0000`(14:45:01), `Saved/Crashes/UECC-Windows-582F3E9048CD1E1EA461AA80BE12322E_0000`(14:45:41) 모두 `ActorComponent.cpp:1668`, `Assertion failed: bHasBegunPlay`다.
- 엔진 계약: UE 5.8.2 `UActorComponent::EndPlay()`는 진입 시 `bHasBegunPlay`를 검사하고 종료 시 false로 바꾼다.
- 프로젝트 원인: 사용자 적용본 `UKhazanLocomotionComponent::EndPlay()`가 시작과 끝에서 `Super::EndPlay()`를 두 번 호출한다. 첫 호출 뒤 두 번째 호출이 assert한다.
- 수정 계약: 자신의 delegate 구독/weak reference/Intent를 정리한 뒤 `Super::EndPlay(EndPlayReason)`를 마지막에 한 번만 호출한다.
- 함께 발견한 별도 오류: `RegisterGameplayTagEvent()`가 반환한 ASC 소유 delegate 참조를 지역 변수에 값 복사하고 그 복사본에 AddUObject했다. crash 원인은 아니지만 실제 태그 변화 callback이 등록되지 않아 M2.1 기능 검증을 무효화한다. ASC 반환값에 직접 `AddUObject`하거나 명시적 참조에 연결한다.
- 현재 검증 판정: PIE 시작과 ASC 탐색 오류 부재까지만 통과. GE asset은 현재 Infinite/Target Tag/None 데이터를 가진다. A/B handle, count 0→1→2→1→0, 허용 결과, 재 PIE 종료는 수정 후 다시 검사해야 한다.


## 2026-09-09 M2.1 종료 assert 수정 후 재검증

- 사용자 수정본은 delegate를 `FOnGameplayEffectTagCountChanged&`로 받아 ASC 소유 delegate에 구독하고, `EndPlay()` 마지막의 `Super::EndPlay()` 한 번만 남긴다.
- 15:00:23 Live Coding patch 성공 뒤 실제 `GE_Test_BlockMovement`를 A/B 두 handle로 적용·해제했다. tag count / 활성 효과 수 / 캐시된 이동 허용값은 `0/0/true → 1/1/false → 2/2/false → 1/1/false → 0/0/true`였다. 두 handle은 서로 달랐고 개별 제거도 성공했다.
- 별도 차단 효과를 활성 상태로 남긴 채 PIE를 종료했으며 `BeginTearingDown`과 `CleanupWorld for DevMap` 뒤 Editor가 유지됐다. 두 번째 PIE도 count 0, 효과 0, 허용 true로 새로 시작하고 정상 종료됐다.
- 새 crash report는 생기지 않았다. `Saved/Crashes` 최신 항목은 수정 전 `UECC-Windows-582F3E9048CD1E1EA461AA80BE12322E_0000`(14:45:41)이며 현재 Editor PID 23328은 응답 중이고 PIE Idle이다. 따라서 이 항목의 `bHasBegunPlay` assert는 수정본 런타임에서 재발하지 않았다.
- Player BP는 compile error/warning 없이 실행됐고 서로 다른 A/B handle을 만들었다. 현재 그래프가 BeginPlay 한 호출에서 적용과 제거를 모두 끝내므로 실제 이동 차단을 눈으로 볼 수 없다는 테스트 구성 한계가 있다.
- 자동 Enhanced Input 주입은 허용 상태에서도 프로젝트 `IA_Move` binding에 도달하지 않아 실제 입력 gate 판정에 쓰지 않았다. 분리된 BP 이벤트를 통한 키보드/패드 시험과 Editor 종료 후 전체 Development Editor 빌드는 남는다.

### 같은 세션 후속 — Enhanced Input 경로 합격

- `InjectInputVectorForAction(IA_Move, (0,1,0))`을 12프레임 사용한 두 번째 probe는 프로젝트의 실제 action binding에 도달했다.
- Block count 1에서는 캐시 허용 false와 원시 InputAmount 1.0을 동시에 관측했고 변위/속도/가속도는 모두 0이었다. 같은 효과를 handle로 제거한 count 0에서는 허용 true, InputAmount 1.0, 변위 387.214 uu, 속도 `(0,470,0)` uu/s, 가속도 `(0,1800,0)` uu/s²였다.
- 주입 종료 뒤 InputAmount와 MoveInputWorld가 0으로 돌아와 Released 정리도 확인했다. 수치는 이 실행의 관측값이며 원작값 또는 튜닝 제안이 아니다.
- 초기 probe 과정의 Python `AttributeError`/`NameError`는 노출되지 않은 helper와 callback 전역 수명 사용에서 발생한 진단 코드 오류다. callback을 명시적으로 해제하고 해당 PIE를 종료해 활성 Test GE를 정리한 뒤, 보존된 `builtins` 참조 방식으로 재검증했다. 게임 C++ assert나 BP compile 오류가 아니다.
- 최종 PIE 종료도 정상이며 임시 callback/참조가 없다. M2.1 기능 런타임은 통과했고, 남은 빌드 검증은 Editor 종료 상태의 전체 `KhazanEditor Win64 Development` 한 번이다.


## 2026-09-09 M2.1 Editor 종료 상태 전체 빌드 완료

- Editor가 종료된 상태에서 `Build.bat KhazanEditor Win64 Development Khazan.uproject -WaitMutex -FromMsBuild`를 실행했다.
- 결과는 `Succeeded`, `Target is up to date`, exit code 0이다. 앞서 확인한 실제 IA_Move gate, 효과 A/B count/handle, 반복 PIE 종료 결과와 합쳐 M2.1을 완료 처리한다.
- M2.2/2.3 설명 준비를 위한 별도 `UnrealEditor-Cmd -run=pythonscript -nullrhi` CDO probe도 exit code 0, commandlet error 0으로 끝났다. 결과는 `Saved/ImportReports/M2_2_3_CurrentCDO_20260909.json`이다.
- Probe는 Player CDO의 Walk/Run/Sprint 170/470/600, CMC MaxWalkSpeed 300, MinAnalog 15, MaxAcceleration/Braking 1800/1800, Yaw 540과 현재 base CharacterMovementComponent를 읽었다. 수치는 현재 프로젝트 관측/이관값이며 원작 검증값이 아니다.
- 게임 Source/BP/asset은 이 확인에서 저장·수정하지 않았다. 다음 C++/BP 작업은 [M2.2·M2.3 공동 구현 가이드](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)의 사용자 적용 대기다.


## 2026-09-11 Asset catalog Crash 경계 보강 재개

- 2026-08-31의 `AssetLabel.PreLoad` lookup null 역참조 문제가 새 Character Definition catalog 연결의 선행 차단 항목으로 다시 확인됐다. 현재 Source에는 여전히 `PreSave()` 전용 파생 map 생성과 ensure 뒤 null 역참조가 남아 있다.
- 다음 사용자 적용은 `PostLoad`/`PreSave` 공통 rebuild, nullable `Find` 반환, tag 기준 단일 loaded cache, cache-only typed Find와 명시적 sync load 분리다. 기존 public path cache API는 현재 외부 소비자가 없고 label load에서 중복 cache 원인이므로 제거 대상이다.
- 수정 후 먼저 기존 `PDA_AssetData`의 Preload label과 `DA_InputData`를 cold build/PIE에서 회귀 확인한다. Character Definition entry를 추가한 결과와 섞어서 원인을 가리지 않는다.
- 이번 기록은 안내이며 C++ 수정, build, Editor 실행, PIE는 수행하지 않았다.


## 2026-09-11 AssetManager 최소 복원본 검증

- 최종 소스: 기존 path/name/label API와 FName cache로 복원하고 PostLoad index rebuild, lookup null 안전성, batch IO/cache·release 대칭만 보강했다. 어시스턴트 직접 수정 범위는 이 보강 묶음에 한정했다.
- IDE semantic rename 뒤 아직 저장되지 않은 문서가 디스크 패치를 나중에 덮어쓰는 현상을 발견했다. Rider `apply_patch`로 네 파일의 IDE 문서/디스크를 함께 일치시켰고 최종 저장본을 재빌드했다. 처음의 빌드/Startup 로그는 최종 검증 근거로 사용하지 않는다.
- 최종 빌드: `Build.bat KhazanEditor Win64 Development Khazan.uproject -WaitMutex -FromMsBuild`, exit 0 / `Result: Succeeded`, DLL 링크 완료. 로그: `Saved/Logs/AssetManagerRollback_Build_20260911.log`. XGE 라이선스 경고는 standalone build로 처리됐다.
- 최종 시작 검사: `UnrealEditor-Cmd Khazan.uproject /Game/Maps/DevMap -game -nullrhi -unattended -nosound -NoSplash -ExecCmds=Quit`, exit 0. DevMap LoadMap, World cleanup, Game engine shut down을 확인했다. 로그: `Saved/Logs/AssetManagerRollback_Startup_Final_20260911.log`.
- 이 실행에서 AssetManager catalog/label/path 실패, InputData의 동기 fallback 경고, ensure/assert/crash는 없었다. 입력 setup 이후 한 프레임 종료 검사이며 실제 이동 입력/Stop/반복 PIE를 검증한 것은 아니다.
- 기존 미완료 상태 확인: `KhazanMonster_1 has no CharacterDefinition`, `BP_KhazanPlayer_C_0 has no CharacterDefinition`, `could not acquire a locomotion intent source`가 남았다. 다음 Definition 연결 단계의 미구현이며 이번 복원에서 Character/BP를 임의로 수정하지 않았다. 따라서 이동 회귀 검사는 Definition 연결 후 수행한다.
- 별도 보조 검사: `Saved/CodeBackups/verify_asset_catalog_20260911.py`로 index map을 읽으려 했으나 Python에서 `AssetNameToPath`가 protected로 차단됐다(exit 1). snake_case 첫 시도는 property-name lookup 실패였다. 접근 제한을 풀기 위해 게임 코드를 추가하지 않았으며 map 전수 비교/누락 키 fault injection의 런타임 통과를 주장하지 않는다. 로그: `Saved/Logs/AssetManagerRollback_Catalog_Final_20260911.log`.
- 정적 검증: 최종 네 파일이 작성한 복원본과 일치하고 해당 C++ diff의 whitespace 오류는 없다. 신규 lookup 분기는 source로 확인했다. 실제 API 호출을 건너뛰고 `ensure` 뒤 null 역참조를 허용하지 않는 근거는 [Epic Asserts 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/asserts-in-unreal-engine)의 ensure 후 실행 지속 계약과 일치한다.
