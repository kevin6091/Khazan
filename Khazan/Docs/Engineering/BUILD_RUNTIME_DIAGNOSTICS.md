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

## 2026-10-01 — WeakAttack01 → LockOn 이동 포즈 튐 조사 (원인 미확정)

- [사용자 재현] LockOn에서 WeakAttack01을 실행하고 InputEnd 전에 L 이동 입력을 유지하면 LockOn Run L 복귀 중 포즈가 두드러지게 튄다. 다른 방향은 정도가 다르고 F는 튐이 잘 보이지 않는다. `LocomotionExitInertializationDuration=2.5 s`는 원인을 분리하려고 사용자가 잠시 늘린 값이다. 사용자는 약 2.4초 이전에도 튐을 보았다고 설명했다. 이 시간 변경을 원인이나 수정 대상으로 단정하지 않는다.
- [범위] 게임 C++/BP/Animation 에셋은 편집·저장하지 않았다. 기존 Router → 아키텍처 v3 최신 절/Migration D4 → Animation 현행 정본과 관련 실제 Source만 표적 확인했다. 새 실행 클래스/helper/관측 멤버를 추가하지 않았다.

### 실제 코드에서 확인한 입력·복귀 경로

1. `KZPlayerController.cpp:219–230`은 `HandleInputMove()`를 먼저 호출하고 그 뒤 `Input.Action.Move` GameplayEvent를 보낸다.
2. `KZPlayer.cpp:105–125`는 공격 중에도 `Intent.MoveInputWorld`를 먼저 보존하지만 `IsMovementInputAllowed()==false`이면 CMC의 `AddMovementInput()`까지 가지 않는다.
3. `KZComboActionAbility.cpp:634–646`의 InputEnd는 `SetInputEnded()`로 다른 Action 활성화 차단을 푼다. 이는 실행 중 소유한 `Block.Movement.Input` 제거와 다르다. 그 태그의 제거는 Ability 종료 수명에 속한다.
4. `KZComboActionAbility.cpp:691–718`은 InputEnd 이후 Move event를 받으면 montage 관성화를 요청하고 `Montage_Stop(0)` 뒤 `FinishAbility(true)`로 끝낸다. 같은 event를 처리한 앞쪽 Player 호출은 이미 이동 차단으로 돌아갔을 수 있으므로, 복귀 직후 snapshot의 실제 속도가 그 프레임의 L 입력 방향과 일치한다고 보장할 수 없다. 정확한 프레임 수/속도는 아직 관측하지 않았다.
5. `KZAnimInstance.cpp:85–120`의 `MovementDirectionAngle`은 입력이 아닌 Actor-local 실제 CMC 속도각이다. 속도가 `MovingSpeedThreshold` 이하이면 `0 deg`(F)다. `GatherGameThreadData():264`에 이미 들어오는 `Snapshot.MoveInputWorld`는 현재 각도 계산에 사용하지 않는다.
6. `KZAnimInstance.cpp:162–182`는 유효 입력이 돌아와도 실제로 움직이지 않으면 Walk를 선택하고, 이후 실제 속도 hysteresis로 Run을 선택한다. 따라서 복귀 중 F→L 방향 샘플 변화 및 Walk→Run 변화가 겹칠 수 있다. 이 경로의 존재는 정적 확인이고, 사용자의 튐 순간과 일치한다는 PIE 증거는 아직 없다.
- 방향의 `0/-90 deg`는 이 프로젝트 좌표계의 전방/왼쪽 기하학 값이다. 현 BP에서 읽은 `RunEnterSpeed=220`, `RunExitSpeed=190 cm/s`와 WeakAttack CDO의 `2.5 s`는 현 프로젝트 설정 관측이며 원작 메타데이터 값이 아니다. 새 튜닝값은 제안하지 않았다.

### ABP·설치 엔진 소스 확인과 해석 범위

- 연결 중 읽은 `/Game/_Art/Player/Character/Bluprints/ABP_Player.ABP_Player` 최종 연결은 `Locomotion StateMachine → DefaultSlot → Inertialization → Output`이다. Slot 앞에 관성화 노드를 둔 잘못된 배치로 설명할 근거는 없다.
- 설치 UE 5.8의 `Engine/Source/Runtime/Engine/Private/Animation/AnimNode_Inertialization.cpp:645–687`은 새 요청 시 자세 차이를 초기화하고 현재 입력 포즈에 그 보정을 적용한다. `ApplyTo():1049–1057`은 현재 target pose에 translation 보정을 더하고 rotation 보정을 곱한다. 기존 공격 종료 요청 하나가 후속 Blend Space 방향/Walk→Run 변화의 새 불연속마다 자동으로 새 보정을 계산하는 것은 아니다.
- 같은 파일 `CalcInertialFloat():167–174`에는 수렴 방향의 초기 속도가 충분할 때 `t1=min(t1,-5*x0/v0)`로 개별 보정 시간을 줄이는 코드가 있다. 수학식의 5는 엔진 알고리즘 계수이며 gameplay 튜닝 제안이 아니다. 보정은 종료 시 값·미분이 0이 되도록 계산되므로 이 분기의 존재만으로 갑작스러운 튐을 확정하지 않는다.
- `Evaluate_AnyThread():476–563`은 추가 요청·중단 및 bone profile을 처리하며 같은 평가의 요청들은 더 짧은 시간으로 병합될 수 있다. 따라서 설정 `2.5 s`와 실제 활성 요청/개별 본 보정 시간이 같다고 전제할 수 없다. 이 재현에서 추가 요청·profile·중단이 있었다는 관측은 없다.
- `AnimGraphRuntime/Private/AnimNodes/AnimNode_Slot.cpp:79–85`에서 Source update는 SourceWeight 또는 Always Update Source Pose에 달려 있다. 내보낸 Slot의 `Node`에는 비기본 override가 없고 엔진 생성자의 해당 flag 기본값은 false다. 런타임 source weight/그래프 재초기화/clip phase는 미확인이다. 설정을 임의로 켜거나 원인으로 확정하지 않았다.
- 현재 우선 후보는 복귀 대상의 속도각·gait·샘플/phase 변화다. 방향별 차이를 설명할 수 있지만, 관성화의 본별 보정·추가 요청·Slot source 재개와 실제 clip 포즈도 프레임 증거로 분리해야 한다. “관성화 한계”나 단일 원인으로 확정하지 않는다.

### 테스트 실패와 정리

- 초기 PIE를 열고 LockOn 선택은 확인했지만, WeakAttack01→L/F 비교를 직접 키 조작으로 완료하지 못했다. 이후 사용자 요청에 따라 Python 입력 주입 테스트를 중단했다.
- 초기 진단용 Slate callback은 Python 전역 수명 오류로 `NameError: state is not defined`를 반복했다. tick count 0 / sample 0이며 공격→복귀 프레임 증거가 아니다. 이 오류는 어시스턴트의 진단 코드 오류로 게임 포즈의 원인과 혼동하지 않는다.
- Rider LLDB는 두 표적 중단점에서 유효한 Source stack/frame values를 얻지 못했다. debugger 결과로 원인을 확정하지 않는다. 후속 status는 session 0이며, 추가했던 `KZComboActionAbility.cpp:701`, `KZAnimInstance.cpp:127` agent 중단점은 제거했다. 최종 목록의 user exception 8개와 활성 상태는 그대로 보존했다.
- 직접 Windows 제어는 `computer-use` 스킬의 `@oai/sky`로 시도했다. list 앱/창 호출과 JS 재초기화 후에도 `Computer Use native pipe is unavailable ... os error 2`로 실패했다. 당시 `ue_health`는 connected false이고 UnrealEditor 프로세스도 없었다. Editor 종료로 기존 process-local callback도 더 이상 실행 중이지 않다. 종료 원인은 미확인이며 crash로 단정하지 않는다.
- 직접 키 PIE 재현, 튐 프레임의 포즈·활성 Inertialization·clip phase, 수정 효과 검증은 미완료다. 상세 재개는 `ENGINEERING_WORK_CONTINUITY.md`의 같은 날짜 절을 따른다.

## 2026-10-01 — 후속: 실제 패드 PIE에서 L 입력의 F 방향 선택 확인, 최소 수정안 준비

### 검사 방식과 확보한 증거

- 앞 절의 Editor 미연결 상태를 해결하려고 Rider의 기존 `Khazan` 실행 구성을 사용했다. 새 Editor PID는 19616이고 UE MCP 연결을 확인했다. 기존 PIE 설정으로 DevMap을 시작했다. Windows 직접 입력 helper는 계속 pipe 오류라 실제 입력은 사용자 패드 조작으로 발생했고, 어시스턴트는 Python으로 값을 읽기만 했다. Input 주입, 이동 함수 호출, Ability 활성화 호출, pawn 위치/회전 또는 anim property 덮어쓰기는 하지 않았다.
- 현재 `IMC_Default.DefaultKeyMappings.Mappings`에서 IA_Move는 Gamepad Left Thumbstick 2D-Axis, IA_LockOn은 Gamepad Right Thumbstick Button, IA_WeakAttack은 Gamepad Face Button Left/Left Mouse Button이다. WASD 매핑은 확인되지 않았다. 구버전 `Mappings` 배열은 비어 있으며 deprecated이고 실제 defaults는 위 새 struct 안에 있다.
- 성공한 관측은 180초 제한의 읽기 전용 Slate post-tick callback이다. `SystemLibrary.GetFrameCount`, 현재 intent/policy 복사본, Actor Yaw/position/velocity, AnimInstance의 실제 속도·방향·gait·유효 입력, active montage/position, 실제 키 상태를 3,444개의 서로 다른 engine frame에서 기록했다. callback error는 null이고 종료/참조 해제를 확인했다. 초기 Key struct 생성 시도는 등록 전에 실패했으며 최종 자료와 구분한다.
- Raw: `Saved/ImportReports/WeakAttackLockOnExit_20261001_raw.json`. 요약과 현재 Blend Space 설정: `Saved/ImportReports/WeakAttackLockOnExit_20261001_summary.json`. `input_angle`은 관측 시점의 Intent.MoveInputWorld와 Actor Yaw로 계산한 진단값이고 실제 AnimInstance 각도와 구분한다. worker snapshot/CMC 값에 관측 순서 차이가 있으므로 이 기록을 bone-pose 평가 frame이나 캡처 영상으로 표현하지 않는다. L 입력은 종료 전부터 유지돼 이 차이가 F/L 판정을 뒤집지 않는다.
- Live GA_Player_WeakAttack CDO의 exit duration은 여전히 2.5초다. 이 설정을 변경하지 않았다. 수치는 사용자 실험 설정/현재 프로젝트 관측이며 원작 metadata 값이 아니다.

| Engine frame | 입력각(deg) | 선택각(deg) | 속도(cm/s) | 컴포넌트 ResolvedGait | Anim LocomotionGait |
|---|---:|---:|---:|---|---|
| 9597 (공격 중, 이동 차단) | -94.67 | 약 0 | 60.66 | Run | Walk |
| 9598 (공격 중, 이동 차단) | -94.67 | 약 0 | 90.94 | Run | Walk |
| 9599 (montage 없음, 유효 입력 true) | -91.35 | 약 0 | 92.62 | Run | Walk |
| 9601 | -91.35 | -29.67 | 68.97 | Run | Walk |
| 9603 | -91.35 | -64.56 | 117.01 | Run | Walk |
| 9607 | -91.35 | -82.03 | 244.18 | Run | Run |

- 첫 복귀 관측 9599의 입력 세기는 1.0이고 `movement_allowed_by_tags/has_movement_input` 모두 true다. native Anim VelocityLocal은 `(92.61909268, 0.000000172, 0)`이다. `bIsMoving=true` 경로에서 전진 속도를 각도로 바꾼 결과가 F이며 `!bIsMoving`의 0도 fallback이 아니다. 첫 Run 선택까지 8 engine frame, 수집 wall-clock으로 약 0.0667341초다. 이 시간은 gameplay blend 설정값/원작값이 아니다.
- F 비교의 첫 복귀 9855에서는 입력 -1.98도/선택 약 0도/97.65 cm/s/Walk이고, 9857은 입력 -2.67도/선택 -3.65도, 9861은 선택 -2.90도/Run이다. F도 gait 전환은 있지만 방향 변화가 작다. 이는 방향별 증상 차이를 설명하는 확인된 데이터 차이다.
- Walk L에서도 8304에 입력 -86.98도/선택 약 0도/91.04 cm/s/Resolved Walk/Anim Walk를 관측했다. 이 종료는 이전 종료보다 수집 wall-clock 약 3.70초 뒤다. 따라서 F 선택 문제는 Walk→Run 변경이 있을 때만 생기는 것이 아니다. 본별/중단 관성화 상태 자체는 기록하지 않았으므로 그 영향까지 배제하지 않는다.
- 현재 LockOn Walk/Run 두 Blend Space 모두 X축 interpolation time=0, target weight interpolation speed=0, Allow Marker Based Sync=false다. X=0/Y=0 sample은 각각 DAS_Player_LockOn_Walk_F / DAS_Player_LockOn_Run_F다. 여기에 들어갈 native 방향값의 F 중간 선택을 확인했다. 런타임 sample weight/clip phase와 실제 화면 튐 frame을 직접 캡처한 것은 아니다.

### 해결안: 기존 KZAnimInstance.cpp 두 곳, 새 runtime 파일/멤버 없음

ARCH-73의 제안 계약이며 실제 적용은 아직 아니다. [patch](Examples/LockOnRecoveryPose_20261001.patch)는 Git root 기준 `Khazan/Source/Khazan/Animation/KZAnimInstance.cpp` 하나에 +12/-3이다. Player에서 이동 방향을 다시 저장하거나 CMC 속도를 강제로 초기화하는 변경이 필요하지 않다.

1. `UpdateKinematics_AnyThread`의 기존 `if (bIsMoving)` 방향 분기 앞에 LockOn 입력 방향 분기를 넣는다. 같은 함수 앞에서 이미 만든 ActorYawRotation과 const Snapshot을 쓴다.

```cpp
if (bIsGrounded && bHasMovementInput &&
    Snapshot.RotationMode == EKZRotationMode::LockOn)
{
    const FVector InputLocal =
        ActorYawRotation.UnrotateVector(Snapshot.MoveInputWorld);

    MovementDirectionAngle = static_cast<float>(
        UKismetMathLibrary::DegAtan2(InputLocal.Y, InputLocal.X));
}
else if (bIsMoving)
{
    MovementDirectionAngle = static_cast<float>(
        UKismetMathLibrary::DegAtan2(VelocityLocal.Y, VelocityLocal.X));
}
else
{
    MovementDirectionAngle = 0.f;
}
```

- `bIsGrounded`는 이번 LockOn 지상 이동 포즈의 범위를 고정한다. `bHasMovementInput`에는 기존 허용 여부와 입력 유효성 검사가 이미 포함돼 있다. 기존 raw input을 보존하더라도 차단 중에는 이 분기를 쓰지 않는다.
- `Snapshot.RotationMode`를 읽는 이유는 이 코드 아래에서 member RotationMode를 갱신하기 때문이다. 이전 frame의 member를 앞당겨 읽지 않는다.
- `InputLocal`은 새 멤버가 아닌 지역 `const FVector`다. 작성자는 이 AnyThread 호출, 소비자는 아래 atan2이며 호출 종료 때 사라진다. world 입력을 캐릭터 yaw 기준으로 역회전해 전방 X/오른쪽 Y 성분으로 만든다. 입력 세기는 방향각에 영향을 주지 않고 기존 유효성 검사 뒤 계산하므로 normalize가 필요 없다. yaw가 0일 때 `(0,-1,0)` 입력은 -90도로 L이다. 이 수치는 기하학 예이며 튜닝값이 아니다.
- atan2의 결과를 기존 float MovementDirectionAngle에 쓴다. VelocityWorld/Local, GroundSpeed, AccelerationWorld와 실제 CMC 제어는 계속 현재 데이터를 사용한다. 새 Actor/ASC worker 접근이나 방향 Reset 수명은 없다.

2. `UpdateLocomotionSelection_AnyThread`에서 기존 첫 Sprint 분기를 다음처럼 바꾸고, 그 뒤 실제 속도 기반 else-if들은 유지한다.

```cpp
if (ResolvedGait == EKZGait::Sprint ||
    RotationMode == EKZRotationMode::LockOn)
{
    LocomotionGait = ResolvedGait;
}
```

- 함수의 기존 outer `bHasGroundedMovementInput` 조건 안에 둔다. 새 Run 강제값이 아니라 이미 계산한 gait를 사용한다. 약한 스틱 입력의 Resolved Walk는 Walk, 이번 full L의 Resolved Run은 복귀 첫 frame부터 Run을 선택한다. LockOn constraint가 가진 기존 Run 상한도 그대로다.
- 이 함수 호출 전에는 member RotationMode/ResolvedGait가 이미 snapshot으로 갱신돼 있으므로 여기서는 기존 member를 읽는다. non-LockOn의 속도 hysteresis는 기존 else-if에서 계속 실행되고 Sprint 결과도 기존과 같다.
- 이 변경은 LockOn 가속/감속 중의 포즈도 의도된 gait로 즉시 표시하는 정책이다. 일반 방향 변경·약한/강한 입력·발 미끄러짐을 함께 검증한다. State/Ability 실행 수명과 공유 gameplay 태그를 새로 만들지 않는다.

### 실제 검증 범위와 다음 적용 순서

- 설치 UE 5.8 `Core/Public/Math/Rotator.h:306`의 const UnrotateVector API와 기존 enum/snapshot/helper 선언을 확인했다. patch는 `git apply --verbose --check --ignore-space-change`에서 실제 대상 검사와 1파일 +12/-3 통계가 확인됐다. 게임 Source 적용/수정안 C++ build/수정 후 PIE는 수행하지 않았다.
- 먼저 방향 hunk만 적용하고 같은 입력으로 첫 복귀 선택각이 L인지 확인한다. 그 다음 gait hunk를 적용해 full L이 첫 복귀부터 Run인지 확인한다. 기존 2.5초 실험 설정을 유지해 한 번에 변인을 구분한다. 연속 공격은 앞 관성화와 겹칠 수 있으므로 서로 분리한 단일 공격 비교도 한다.
- 이후 F/R/B/대각선, LockOn 일반 방향 변경, 스틱 세기 변경, 입력 해제 Stop, LockOn on/off 및 non-LockOn Walk/Run/Sprint를 확인한다. 확인된 중간 선택이 제거돼도 화면 튐이 남으면 그 frame의 pose/clip phase/Slot source 재개/관성화 실제 상태를 추가로 검사한다. 이번 자료만으로 모든 시각적 튐이 해결됐다고 기록하지 않는다.
- 최종 Editor는 연결돼 있고 PIE는 Idle이다. 관측 callback과 builtins의 actor/anim 참조를 해제했다. 게임 C++/BP/Animation 에셋은 수정하지 않았다.

## 2026-10-02 — DodgeAttack_F 전환 실패: F Ability EntryNodeId 미설정

- 사용자 보고: LockOn 방향별 Dodge 뒤 X/Y의 4방 DodgeAttack 중 F만 실행되지 않는다. 이번 조사에서는 gameplay Source/BP/에셋을 수정하지 않았다. UE 연결 PID 27896에서 Python은 설정을 읽는 용도로만 사용했으며 입력/Ability 활성화를 주입하지 않았다.
- 실제 live CDO 비교: `/Game/Bluprints/AbilitySystem/Abilities/Player/DodgeAttack/GA_Player_DodgeAttack_F`의 `EntryNodeId=None`, B/L/R은 각각 `DodgeAttack_B/L/R`다. 네 Ability의 `ComboDefinition`은 모두 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`이다. Definition의 F 노드는 `NodeId=DodgeAttack_F`, `SectionName=DodgeAttack_F`, `Montage=AM_DAS_Player_DodgeAttack`으로 존재하며 F/RF Dodge Edge의 target도 `DodgeAttack_F`다. CharacterDefinition 초기 grant 목록에는 F Ability class도 있다.
- 기존 사용자 PIE 로그 `Saved/Logs/Khazan.log`: 2026.10.02-04.03.40 UTC `Dodge_RF -> DodgeAttack_F`, 04.03.42 및 04.03.43 UTC `Dodge_F -> DodgeAttack_F`에서 `rejected cross-Montage Combo edge`를 확인했다. 조사 Python의 LogPython 출력과 기존 gameplay 로그를 구분한다.
- 실패 경로: `KZAbilitySystemComponent.cpp:31`의 Definition/Entry 일치 비교에서 F의 `None`은 요청 `DodgeAttack_F`와 맞지 않는다. `KZComboActionAbility.cpp:291`에서 `HasComboEntry=false`이므로 `TransitionToNode`로 진입한다. Dodge montage와 DodgeAttack montage가 달라 `:525`의 비교/`:527`의 로그 경로로 거절된다. Edge 입력 검사 이후 발생한 실패이며, 이 사례의 해결은 cross-Montage local Jump 제한 제거가 아니다.
- 최소 해결 안내: `GA_Player_DodgeAttack_F` → Class Defaults → Combo → Entry Node Id를 `DodgeAttack_F`로 설정하고 Compile/Save한다. 이후 PIE를 종료/새로 시작해 초기 grant를 다시 만든 뒤 F/RF/LF Dodge에서 X/Y를 각각 확인한다. C++ 변경은 필요 없다. 이번에는 해당 값을 적용하거나 수정 후 PIE 성공을 검증하지 않았다.
- 캐시의 `get_asset_properties`는 요청한 F 필드 값을 반환하지 않아 디스크 값의 독립 검증으로 사용하지 않았다. 진단의 직접 설정 근거는 Editor live CDO와 현재 Definition, 실행 경로의 근거는 기존 사용자 PIE 로그/현재 Source다. `KZWeakAttackAbility.cpp`와 `KZDodgeAttackAbility.cpp`는 현재 include만 있으며 F 전용 실행 분기가 없다.

## 2026-10-02 — 사용자 조작 PIE: LockOn L Dodge → Idle 관측 진행

- 사용자가 직접 PIE를 조작하고 어시스턴트가 상태를 읽는 방식으로 진행했다. 입력/Ability 실행을 Python으로 주입하지 않았고 게임 C++/BP/에셋을 수정하지 않았다. 연결 Editor는 PID 27896이다. `KZWeakAttackAbility.cpp`에는 실행 분기가 없으며 공통 `UKZComboActionAbility`의 종료와 현재 ABP를 조사했다.
- 직접 Windows 제어는 computer-use의 native pipe unavailable/os error 2로 실패했다. LLDB attach는 됐지만 수동 정지에서 source 없는 GameThread 주소만 반환했고 `GFrameCounter`와 locals를 읽지 못했다. 조정한 두 agent breakpoint도 실제 hit 증거가 없다. 두 breakpoint를 제거하고 attach 세션을 분리했으며 기존 8개 사용자 exception breakpoint를 보존했다. 중단점으로 종료 함수를 확인했다고 기록하지 않는다.
- 실제 사용자 조작 기록 v1: 5,771 frame/error null, Dodge 21회(무입력 종료 후보 L 9/R 5/F 1/B 1, 이동 입력이 남은 조기 종료 L 3/R 2). v2: 1,165 frame/error null, 무입력 종료 L 4/R 1. `Saved/ImportReports/DodgeIdleLive_20261002_v1_latest.json`, `_v2.json`에 저장했다. 초기 v1의 앞 2,561 frame은 `_raw.json`에 별도 보존했다. 샘플 분류는 position/입력/속도에 따른 관측 분류이며 debugger 함수 hit의 대체 증거로 표현하지 않는다.
- v1은 frame/시간/CMC velocity/Actor 위치·회전/active montage 및 position/native AnimInstance 변수/머리·골반·두 발·Root component pose를 읽는다. v2는 game-world time/DefaultSlot local montage weight/mesh scale/world bone pose를 추가했다. Slate post-tick에서 읽은 완료 pose와 관측 변수이므로 모든 값이 같은 worker update의 원자적 snapshot이라고 보장하지 않는다. `get_current_active_montage()`의 None은 pose weight 0을 뜻하지 않는다. 실제 자연 종료 첫 None frame에도 slot weight는 1이고 이어 감소했다.
- 에셋 직접 확인값: `/Game/_Art/Player/Animation/InGame/DAS/Dodge/AM_DAS_Player_Dodge`, Blend In/Out 모두 Standard/HermiteCubic/0.25 s, auto blend out true/trigger -1, L segment 시작 6.400000095 s, 길이 1.066666722 s, 다음 LF segment 시작 7.466666698 s. 네 F/B/L/R Dodge Ability CDO의 LocomotionExitInertializationDuration=0.2399999946 s, ComboTransitionInertializationDuration=0.0799999982 s다. **현재 프로젝트 설정이며 원작 직접 확인값 또는 새 튜닝 제안이 아니다.** 설정/segment/pose는 `DodgeIdleInspection_20261002.json`, `DodgeIdleMontageDetail_20261002.json`, `DodgeIdlePoseCompare_20261002.json`에 저장했다.
- 자연 복귀와 이동 중단 경로를 구분한다. Task는 OnCompleted/OnInterrupted/OnCancelled를 연결하고 OnBlendOut에 FinishAbility를 연결하지 않는다. 자연 완료는 `HandleMontageCompleted → FinishAbility(false)`다. `HandleMoveInput`은 active/InputEnd 이후에만 0.24 s 요청 뒤 Montage_Stop(0)을 수행한다. 따라서 무입력 자연 복귀에서 해당 duration을 늘리면 같은 경로의 블렌드가 늘어난다고 설명하면 안 된다.
- 무입력 L의 반복 관측: frame 164334에서 speed 약 0.49 cm/s/angle 0/Idle 후보 true, 164337에서 speed 7.61 cm/s/angle +90/Idle 후보 false, 164346에서 speed 1.62 cm/s/angle 0/Idle 후보 true. 해당 구간 입력은 0, Stop 진입 pulse는 없다. L 끝부분의 작은 반대 방향 capsule 이동과 Idle 후보 재변화가 존재한다. R에도 유사한 반대 속도 변화가 있다. 이 후보 bool의 변경만으로 실제 SM이 Idle ↔ WalkRun을 왕복했다고 단정하지 않는다. Idle → WalkRun 규칙은 bShouldWalkRun이고 여기서는 false다.
- v2 L 4회의 종료 구간에서 DefaultSlot weight는 연속 감소했다. 기록한 머리·골반·발의 큰 단일 frame 불연속은 확인되지 않았다. 이는 어깨/팔/무기나 화면 전체의 튐까지 없다고 판정한 결과가 아니다. 반면 v1 이동 중단 L에서는 frame 160867 pelvis 약 13.73 deg/왼발 약 16.50 deg의 frame 간 변화가 확인됐다. 그 시도는 입력 1인 조기 복귀이므로 무입력 자연 Idle 복귀와 섞지 않는다.
- 현재 `/Game/_Art/Player/Character/Bluprints/ABP_Player`의 최종 경로는 Locomotion → DefaultSlot → Inertialization → Output이다. Slot에 bAlwaysUpdateSourcePose override가 없고 엔진 기본 false다. 엔진 Slot은 source weight가 relevant하거나 AlwaysUpdate가 켜졌을 때만 source를 update한다. SM에는 재진입 시 reset 경로가 있다. source 정지/재개 및 clip phase는 추가 확인 후보이며 **원인 확정 또는 설정 변경 완료가 아니다.** 실제 CVar Inertialization.Enable=1/IgnoreVelocity=0/StateMachine.EnableRelevancyReset=1을 읽었다.
- ABP/Montage의 읽기 전용 T3D export는 `DodgeIdleABP_20261002.t3d`, `DodgeIdleMontage_20261002.t3d`, 전이 정리는 `DodgeIdleABPTransitions_20261002.json`이다. 보호된 CompositeSections를 억지로 읽거나 전체 프로젝트를 전수조사하지 않고 대상 export를 재사용한다.
- 현재 결론: 자연 종료의 Standard blend, 반복되는 작은 반대 root-motion/capsule 속도, 이동 중단의 큰 pose 변화는 구분됐다. 사용자가 본 튐의 정확한 경로/상체 frame과 대응은 아직 미확인이다. 관성화 한계/원본 L clip 결함/다음 LF section 재생을 확정하지 않는다. 새 helper/멤버/클래스/애셋 수치 변경 없이 표적 관측을 이어간다. 어깨·팔·손을 추가한 v3 read-only observer를 설치했으며 상세 재개/해제는 Continuity에 기록한다.

## 2026-10-02 — 새 사용자 PIE 1,084 frame: Dodge 종료의 Actor Yaw 보정 확인

- 사용자가 “방금 PIE 켜서 테스트했다”고 한 직후 v3 실제 sample 증가를 확인했다. 총 1,084 frame/error null, WeakAttack 2회/L Dodge 3회/R Dodge 2회다. 원본은 `Saved/ImportReports/DodgeIdleLive_20261002_v3.json`에 저장했다. 앞선 v3=0 확인 이후의 새 기록이며 이전 기록과 혼동하지 않는다. 어깨/팔/손의 component/world pose도 포함한다.
- 세 L 모두 회피 중 Actor Yaw가 일정하고 몽타주 길이 약 1.066667 s가 끝난 직후 큰 **Actor/capsule Yaw** 변화가 발생했다. frame 183579: +7.012584686 deg/0.0097397007 s, 183731: +7.495346069 deg/0.0104102008 s, 183878: +7.087390900 deg/0.0098435991 s. 계산된 각속도는 각각 약 +720 deg/s다. R frame 184038/184191도 약 -720 deg/s의 종료 보정이 있다. 단위/시간축은 v3의 Actor rotation/game-world time이며 원작값이 아니다.
- 첫 L의 실제 연속 frame: 183578 Yaw=20.974447/slot=0, 183579=27.987032, 183580=34.668991, 183581=37.046185 deg. 전체 약 16.071737 deg가 약 0.0285604 s에 보정됐다. 첫 큰 회전 frame은 input=0/speed=0/slot=0이다. 그 frame 머리의 component-space 회전 변화는 약 0.046093 deg지만 world-space Root 변화는 약 7.012585 deg다. 본 로컬 포즈 보간과 별개로 전체 캐릭터가 회전했음이 확인됐다. 종료 후 전체 방향 보정은 현재 증상의 구체적 원인 후보이며, 화면 튐의 순간에 대한 사용자 직접 지목은 아직 대기다.
- 현재 설정 출처: `/Game/Data/Character/DA_CharacterDefinition_Player.DA_CharacterDefinition_Player`, `LocomotionConfig.RotationRate=(Pitch=0,Yaw=720,Roll=0)` deg/s. `KZLocomotionComponent.cpp:520`이 이 값을 CMC에 적용한다. BP_Player CMC CDO의 360 deg/s/Native struct 초기값 540 deg/s는 실행 시 CharacterDefinition 값의 대체 근거로 쓰지 않는다. 720은 현재 프로젝트 에셋 확인값이며 원작 metadata 일치가 검증된 값 또는 새 튜닝 제안이 아니다. 설정 report는 `DodgeIdleRotationSettings_20261002.json`이다.
- 코드 경로: `KZLockOnComponent.cpp:293–299`는 target 방향으로 ControlRotation을 계속 갱신한다. `KZLocomotionComponent.cpp:539–541`은 LockOn에서 `bUseControllerDesiredRotation=true`로 CMC 회전 경로를 선택한다. 설치 UE 5.8 `CharacterMovementComponent.cpp:3044`는 `bAllowPhysicsRotationDuringAnimRootMotion || !HasAnimRootMotion()`일 때만 PhysicsRotation을 호출한다. BP_Player CMC CDO의 Allow Physics Rotation During Anim Root Motion은 false다. `:6601`의 GetDeltaRotation은 RotationRate × DeltaTime을 계산하고 `:6630`의 PhysicsRotation은 desired controller rotation으로 FixedTurn한다.
- 위 Source/CDO와 회피 전체 기간의 Yaw 고정/종료 시각/실측 720 deg/s를 함께 보면 **Root Motion 중 CMC 일반 회전 중지 → 측면 회피로 target Yaw 차이 누적 → 종료 후 빠른 LockOn 방향 보정** 경로와 일치한다. F는 타깃을 향하는 선을 따라 이동하면 Yaw 차이가 적고 측면은 커질 수 있다는 기하학적 설명이 가능하다. 원작 내부 구현 확인이나 debugger 함수 hit로 표현하지 않는다. v3에는 실제 frame별 controller yaw/CMC 회전 허용 flag/HasAnimRootMotion이 없으므로 이 세 값의 직접 branch 검증은 추가 항목이다.
- 관성화는 AnimGraph 본 포즈를 처리하며 CMC Actor/capsule 회전 정책의 지연 자체를 제거하지 않는다. 따라서 이 종료 보정을 고치기 위해 자연 Blend Out/관성화 duration을 무작정 늘리는 변경을 우선하지 않는다. `KZWeakAttackAbility.cpp`에 L 전용 코드를 추가할 근거도 없다.
- **최소 원인 검증 제안/아직 미적용:** `/Game/_Art/Player/Character/Bluprints/BP_Player` → Components의 CharacterMovement → Details 검색 `Allow Physics Rotation During Anim Root Motion` → 기존 checkbox를 켜 Compile/Save → 새 PIE에서 L/R의 종료 Yaw spike를 비교한다. 회피 중 target-facing 회전이 이어지고 종료의 누적 보정이 줄어드는지 본다. 이 설정은 다른 Root Motion 공격에도 적용되므로 WeakAttack/콤보의 authored rotation을 함께 확인해야 한다. 현재 어시스턴트는 checkbox/C++/수치/에셋을 변경하지 않았다. 영구 정책을 정할 때는 기존 Locomotion의 단일 CMC 작성 경계에서 적용 범위를 확정하며 새 Manager/타입/중복 상태를 선행 추가하지 않는다.
- 정리된 분석: `DodgeIdleLive_20261002_v3_endstats.json`, `_worldstats.json`, `DodgeIdleRotationDiagnosis_20261002.json`. v3 기록을 저장한 뒤 해당 callback을 해제하고 v4 read-only observer를 설치했다. v4에는 Controller yaw/실제 CMC RotationRate/회전 허용 flag/desired rotation flag/Actor root-motion 관측 API 값을 추가해 후속 비교를 준비했다. 이 API는 Slate post-tick 관측이므로 CMC 내부 HasAnimRootMotion branch 순간의 원자적 값으로 단정하지 않는다.

## 2026-10-02 — Dodge → DodgeAttack의 현재 블렌드 시간 소유자 확인

- 설명 요청에 대해 현재 Source/엔진 Source/Editor live 설정을 읽었다. 게임 C++/BP/몽타주를 수정하지 않았고 이번 질의에서 전환 PIE를 새로 재현하지 않았다. `KZWeakAttackAbility.cpp`와 `KZDodgeAttackAbility`에는 해당 전환 시간을 정하는 별도 실행 코드가 없다.
- `UKZComboActionAbility::ApplyEdge():291–313`은 target이 다른 granted Ability의 Entry이면 `TryActivateComboEntry`로 handoff한다. ASC는 target Spec을 활성화하고 target은 상속된 `StartEntryMontage():167`에서 새 PlayMontageAndWait task를 만든다. 이 경로에는 `ComboTransitionInertializationDuration`이나 `RequestMontageInertialization` 호출이 없다. 해당 0.08 s native 초기값은 `TransitionToNode():574–584`의 **같은 montage section jump**에서만 사용된다. `LocomotionExitInertializationDuration` native 0.24 s는 `HandleMoveInput`의 이동 복귀 중단에만 사용된다. BP override 여부와 기본값은 구분한다.
- `DA_Player_Combo_Definition`의 DodgeAttack_F/R/B/L은 모두 `/Game/_Art/Player/Animation/InGame/DAS/DodgeAttack/AM_DAS_Player_DodgeAttack`을 참조한다. Editor live 해당 montage의 `BlendIn=(BlendTime=0.25 s,BlendOption=HermiteCubic)`, `BlendModeIn=Standard`; outgoing `/Game/_Art/Player/Animation/InGame/DAS/Dodge/AM_DAS_Player_Dodge`의 `BlendOut=0.25 s/HermiteCubic`, `BlendModeOut=Standard`를 확인했다. 두 montage의 In/Out은 이번 확인에서 모두 0.25 s이고 BlendProfile/CustomCurve는 None이다. 이것은 현재 프로젝트 에셋 직접 확인값이며 원작 검증값 또는 새로 선정한 튜닝값이 아니다. `Saved/ImportReports/DodgeAttackBlendSettings_20261002.json`에 저장했다.
- 엔진 경로: PlayMontageAndWait::Activate → ASC::PlayMontage → UAnimInstance::Montage_Play는 **새 montage의 BlendIn/BlendModeIn/BlendProfileIn**을 사용한다. source Action의 Cancel/Ability End에서 PlayMontageAndWait::StopPlayingMontage → ASC::CurrentMontageStop()은 override가 없으므로 source montage의 BlendOut을 사용한다. 현재 task는 bStopWhenAbilityEnds=true이고 proxy에는 blend time 인자가 없다. 전달된 0.0f는 StartTimeSeconds다.
- 두 fade는 겹쳐 진행하므로 0.25+0.25=0.5 s로 계산하지 않는다. 엔진은 새 montage 재생 시 같은 group의 이전 montage를 새 BlendInSettings로 중단할 수도 있으며 이미 중단 중이면 더 짧은 요청으로 기존 fade 시간을 줄인다. 따라서 두 값을 다르게 바꾼 뒤 source fade가 항상 source asset의 BlendOut과 독립적으로 유지된다고 단정하지 않는다. outgoing이 이미 자연 blend-out 중인지/입력 시점/기존 가중치도 실제 경과에 영향을 준다.
- 현재 Dodge → DodgeAttack의 진입 blend를 조절할 직접 에디터 위치는 **AM_DAS_Player_DodgeAttack의 Asset Details → Blend In → Blend Time/Blend Mode In**이다. outgoing도 함께 볼 때는 AM_DAS_Player_Dodge의 Blend Out을 확인한다. ComboTransitionInertializationDuration을 바꾸는 것은 현재 Ability handoff의 시간을 바꾸지 않는다. 노드/Edge/ASC가 별도의 handoff 관성화 시간을 소유하도록 새 구조를 적용한 것은 아니다.
