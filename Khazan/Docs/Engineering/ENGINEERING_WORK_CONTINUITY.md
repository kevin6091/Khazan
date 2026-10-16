# Engineering 작업 연속성

> 코드·BP·Config·컴파일·런타임·피직스 작업이 중단되거나 완료되지 않았을 때만 하단에 인수인계를 추가한다.

## 2026-08-31 DevMap Crash 인수인계

- 정본 진단: `Docs/Engineering/BUILD_RUNTIME_DIAGNOSTICS.md`
- 현재 Config에는 `GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C`가 존재한다.
- 다음 blocker는 `AssetLabel.PreLoad`가 runtime `AssetLabelToSet`에 없고 `GetAssetSetByLabel()`이 ensure 뒤 null을 역참조하는 문제다.
- 마지막 표적 확인에서 `PDA_AssetData.AssetGroupNameToSet` source group은 1개다.
- C++ 수정은 아직 적용하지 않았다.

### 정확한 재개 절차

1. `ENGINEERING_PROJECT_STATE.md`, `UE5_ENGINEERING_RULES.md`, `BUILD_RUNTIME_DIAGNOSTICS.md`만 읽는다.
2. 사용자 변경이 있는 `KhazanAssetData.*`, `KhazanAssetManager.*`, `KhazanPlayerController.*` diff를 확인해 보존한다.
3. `RebuildRuntimeIndexes()`와 `PostLoad()` 기반 runtime cache 생성을 구현한다.
4. 두 getter와 `LoadSyncByLabel()`의 null 안전 API를 구현한다.
5. 빌드 후 Editor를 완전 재시작하고 DevMap PIE/Standalone 검증 절차를 수행한다.
6. 결과와 새 시그니처가 있으면 Engineering 진단 문서 하단에만 추가한다.

## 2026-09-02 Locomotion 완료 기준점

- 정본 문서: `Docs/Animation/ANIMATION_LOCOMOTION.md`.
- 구현 소스: `KhazanAnimInstance.h/.cpp`, `KhazanLocomotionProfile.h`, `KhazanPlayer.cpp`.
- 에셋 생성/감사: `Scripts/Animation/build_dual_axe_locomotion_assets.py`, `audit_khazan_locomotion.py`, `run_locomotion_pie_trace.py`.
- 현재 프로필: `DA_Locomotion_DualAxeSword`; runtime clip 16개; `Hard` 0개.
- 마지막 PIE trace는 `all_checks_passed=true`; 관찰 상태 `IDLE,MOVING_TURN,RUN,START,STOP,WALK`, 발 `LEFT,RIGHT`다.
- 다음 무기 작업은 Content/FModel 전수조사 대신 새 무기의 Locomotion 폴더만 표적 조사하고 동일 역할 clip을 profile에 매핑한다.
- 현재 남은 애니메이션 범위는 Jump/Fall/Land pose, Hard/스태미나 상태, 충분한 다방향 데이터 확보 후 Motion Matching 전환이다.
- 최종 상태에서 Editor를 정상 저장·종료한 뒤 `KhazanEditor Win64 Development` 전체 빌드가 성공했다.

## 2026-09-03 Locomotion 롤백 이후 인수인계

> 2026-09-02 Locomotion 완료 기준점은 롤백 전 이력이며 재개 기준이 아니다. 현재 정본은 `Docs/Animation/ANIMATION_LOCOMOTION.md`의 2026-09-03 섹션과 `Docs/Engineering/ENGINEERING_PROJECT_STATE.md`의 최신 섹션이다.

- 수동 상태 머신, LF/RF 발 위상, 방향별 클립 선택, Dynamic Montage 로코모션 제어는 `UKhazanAnimInstance`에서 제거됐다.
- `KhazanLocomotionProfile.h`와 `DA_Locomotion_DualAxeSword`는 제거됐다.
- DualAxeSword `RT_DAS_*` 런타임 클립 16개와 `ABP_Player`는 보존됐다.
- 기존 asset build/audit/PIE trace 스크립트는 롤백 전 구조 전용이다. 제거된 프로필을 재생성하거나 구형 상태를 검사하므로 실행하지 않는다.
- 마지막 정적 확인은 현재 소스 및 파일 존재 여부까지다. 롤백 후 전체 UBT 빌드, `ABP_Player` Compile, PIE 기본 이동 검증은 남아 있다.

### 정확한 재개 절차

1. `0_DOCUMENT_ROUTER.md`, `Docs/Animation/ANIMATION_LOCOMOTION.md`, `Docs/Engineering/UE5_ENGINEERING_RULES.md`, `Docs/Engineering/ENGINEERING_PROJECT_STATE.md`, `Docs/Engineering/SOURCE_BP_CONFIG_ARCHITECTURE.md`의 최신 날짜 섹션을 읽는다.
2. 최신 롤백 소스로 비-Live-Coding `KhazanEditor Win64 Development` 전체 빌드를 수행한다.
3. Editor 완전 재시작 후 `ABP_Player`를 열어 Compile하고, 끊어진 프로필/변수 참조가 없는지 확인한다.
4. DevMap PIE에서 Idle과 기본 이동이 치명 오류 없이 동작하는지 확인하고 결과를 정본 문서 하단에 추가한다.
5. 검증이 끝난 뒤에만 새 Locomotion 데이터 계약 설계를 시작한다. 구형 프로필이나 C++ Dynamic Montage 구조는 복구하지 않는다.

## 2026-09-07 대용량 main Push 복구 진행

- 사용자 요청은 현재 작업 전체를 GitHub `kevin6091/Khazan`의 `main`에 반영하는 것이다.
- 작업 스냅샷 `afa0976bf6e3da4de983124a91a80f46895c9d5f`를 생성했다. 기존 미푸시 커밋 `35b81ec`도 포함하며, 스냅샷의 341개 파일 변경에 대해 `git diff --cached --check`가 통과했다.
- 최초 `git push origin main`은 2.43 GiB 전송 후 `RPC failed; HTTP 500`, `unexpected disconnect`, `remote end hung up unexpectedly`로 실패했다. 마지막 `ls-remote`에서 원격 `main`은 `ab30c2fddb9909274f094ffe794f526755a61032`였다. 새 LFS 객체 1개 업로드는 성공했다.
- GitHub 단일 Push 제한은 2 GiB다: https://docs.github.com/en/get-started/using-git/troubleshooting-the-2-gb-push-limit . 이번 전송 크기는 이 제한을 넘었다.
- 기존 커밋과 실제 작업 트리를 유지하기 위해, 전송 대상 blob 8,353개를 원본 크기 최대 1,500 MiB씩 4개 임시 커밋으로 나눴다. 임시 원격 브랜치는 `codex/upload-main-20260907-afa0976`이며, 준비 시 원격에 없음을 확인했다.
- 재개 스크립트: 저장소 루트의 `.git/codex-main-upload-20260907.ps1`. 상태 및 배치 커밋: `.git/codex-main-upload-20260907.json`. 두 파일은 로컬 복구 보조 파일이며 프로젝트 커밋에는 포함하지 않는다.

### 정확한 재개 절차

1. `git status --short --branch`와 `git ls-remote --heads origin main codex/upload-main-20260907-afa0976`으로 최신 상태를 확인한다. 아래에 완료 기록이 있으면 이 복구 절차를 반복하지 않는다.
2. 상태 JSON의 `Batches`와 원격 임시 브랜치 hash를 비교해 아직 전송되지 않은 배치부터 진행한다. 순서는 `820186a` → `5abf3ec` → `da0ff04` → `e17550c`다.
3. 각 배치를 순서대로 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\Desktop\GitProject\Khazan\.git\codex-main-upload-20260907.ps1 -PushBatch N`으로 전송하고 매번 성공을 확인한다. `-Prepare`를 다시 실행하지 않는다.
4. 4개 배치가 모두 원격에 반영되면 `git push origin main`을 실행한다. `git ls-remote --heads origin main`이 로컬 `main`과 일치하는지 확인한다.
5. 원격 `main` 반영 성공 후 이 작업에서 만든 임시 브랜치만 `git push origin --delete codex/upload-main-20260907-afa0976`으로 정리한다.
6. 완료 결과를 Engineering 상태/연속성 문서 하단에 추가하고, 해당 기록도 커밋·푸시한 뒤 작업 트리와 원격 동기화를 확인한다. UE 빌드/PIE 검증은 이번 업로드 범위에 포함하지 않는다.

### 2026-09-07 분할 전송 후 연결 단계 추가

- 위 재개 절차 4번의 `git push origin main` 전에 연결 커밋 전송을 한 번 수행해야 한다. 배치 객체만 담은 트리와 실제 프로젝트 트리는 경로가 달라, 이 단계를 통해 기존 스냅샷까지 원격에서 도달 가능하게 만든다.
- 연결 커밋은 `ab015b2cfbfb412c94ea9c043c7fbc6a7ecbed7a`이며 상태 JSON의 `BridgeCommit`에 저장했다. 마지막 임시 배치 `e17550c`와 실제 스냅샷 `afa0976`을 부모로 갖고, 트리는 실제 스냅샷과 동일하다. 이 커밋은 임시 브랜치에만 전송하며 `main` 이력에는 추가하지 않는다.
- 배치 4까지 성공한 뒤 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\Desktop\GitProject\Khazan\.git\codex-main-upload-20260907.ps1 -PushBridge`를 실행하고, 성공 후 기존 절차 4~6을 따른다.
- 연결 커밋의 마지막 배치 이후 전송 후보 크기는 `git rev-list --disk-usage=human --objects-edge`로 약 319 KiB임을 확인했다.

### 2026-09-07 main Push 복구 완료

- 배치 1~4와 연결 커밋을 모두 정상 전송했다. 이후 `git push origin main`이 `ab30c2f..afa0976 main -> main`으로 성공했다.
- 원격 조회에서 `refs/heads/main`이 `afa0976bf6e3da4de983124a91a80f46895c9d5f`임을 확인했다. 원래 `35b81ec` 및 작업 스냅샷 `afa0976`의 이력과 내용을 보존했다.
- 이 작업에서 생성한 원격 임시 브랜치 `codex/upload-main-20260907-afa0976`를 삭제했다. 임시 전송 및 연결 커밋은 `main` 이력에 추가하지 않았다.
- Push 복구는 종료됐다. 위 배치 재개 절차를 다시 실행하지 않는다. 이후 개발 재개 시 기존 애니메이션 정본과 빌드/PIE 검증 대기 항목을 따른다.

## 2026-09-08 Stop 검증 중 실행 상태 확인 필요

- 요청: 사용자가 구현한 Stop을 테스트하고 다음 SprintStart 절차를 설명한다. C++/ABP/시퀀스 구현 수정 권한은 없으며 실제 게임 코드와 에셋은 변경하지 않았다.
- 마지막 확정 검증: 새 UBT KhazanEditor Win64 Development 빌드 성공(15:53:56 DLL), 새 Editor PID 27064의 PIE. Enhanced Input의 Move/Sprint 액션을 주입하고 C++ 중단점/스택/값을 확인했다. Walk 170→0에서도 StopEntrySpeed=170/StopGait=Walk/EnterStop=true, Run 470→392.245에서 470/Run/true, Sprint 600→502.936에서 600/Sprint/true. Foot Right/Left/Right, Foreground Worker #0/#1 실행 확인.
- 첫 검증 Editor PID 17032는 15:49:25에 어시스턴트가 Python에서 GetCurrentStateName의 인덱스를 0/1로 가정해 조회하는 과정에서 접근 위반으로 종료됐다. 로컬 엔진의 인자는 단순 상태 머신 순번이 아닌 역방향 AnimNode property index다. 이 잘못된 검증 호출은 반복하지 않는다. Engine PDB가 없어 정확한 예외 명령어는 확정하지 않았으며 사용자 Stop 코드의 결함으로 취급하지 않는다. Crash: Saved/Crashes/UECC-Windows-4D79FB1A47642F610BCC2E8CE52D4159_0001. 이후 새 빌드/Editor로 위 세 중단점 검증을 수행했다.
- 16:02:07 새 PIE에서 Scripts/Animation/verify_ingame_stop_pie_20260908.py의 32초 입력 검사를 예약하고 ShowDebug Animation을 켰다. 이어 viewport 캡처 요청과 이후 Rider debugger status 요청이 반환되지 않았다. 마지막 OS 확인은 UnrealEditor Responding=false, Rider 창 제목은 Khazan - Khazan (디스어셈블리)다. 정확한 중단 위치/예외명은 회수하지 못했다. 캡처 자체와 별도 실행 예외 중 원인은 아직 확정하지 않는다.
- 남은 검증: 연속 입력 검사 결과 회수, 실제 ABP 상태/원샷 완료/재입력 시각 검증, LF/RF 모든 조합, 현재 발 튐의 원인 분리. 예약된 32초 검사를 통과로 기록하지 않는다.
- 리포트: Saved/ImportReports/Khazan_InGame_Stop_Verification_20260908.json. 사용자 예외 breakpoint 8개는 변경하지 않았다. 식별자가 중복돼 임의 일괄 비활성화도 하지 않았다.

### 정확한 재개/정리 절차

1. 사용자에게 Rider Debug 창의 현재 예외명/중단 사유 또는 화면을 받아 확인한다. 에디터 강제 종료, 사용자 에셋 복원, 설정 변경은 임의 수행하지 않는다.
2. Rider 응답이 복구되면 execute_tool의 xdebug_get_debugger_status로 현재 sessionId를 새로 조회한다. 중단 중이면 xdebug_get_stack과 값부터 읽는다. 이전 Khazan 세션/PID가 그대로라고 가정하지 않는다.
3. 이 작업의 agent-owned breakpoint는 KhazanAnimInstance.cpp 41행 하나다. 149행은 이미 제거했다. xdebug_remove_breakpoint --owner agent로 정리하고 원래 사용자 예외 breakpoint는 보존한다. UI로 정리해야 한다면 41행만 제거한다.
4. 에디터가 실행 가능한 상태가 된 후 ue_health를 먼저 확인한다. builtins._khazan_ingame_stop_verification의 done/error/events/samples를 읽는다. done=false이면 해당 handle만 unregister_slate_post_tick_callback으로 해제한다. 과거 _khazan_stop_probe는 extended 검사 시작 시 중단했다. 액션은 프레임별 주입이라 callback 중단 후 지속 주입 설정은 남기지 않는다.
5. 결과 회수 후 이 작업에서 시작한 PIE를 정상 종료한다. 이는 임시 ShowDebug Animation 표시와 테스트 Pawn도 정리한다. 에디터/사용자 미저장 에셋을 일괄 저장/종료하지 않는다.
6. viewport 캡처와 추측한 인덱스의 GetCurrentStateName 호출은 재시도하지 않는다. 상태 조회가 필요하면 검증된 이름→실제 anim-node index 경로 또는 사용자 ABP Debug Filter/State Machine 화면을 사용한다.
7. 증거가 없는 원샷 완료/발 동기화는 사용자 확인 또는 안전한 후속 테스트로 보충한다. 5단계 안내는 준비용이며 현재 전체 검증 완료 선언이 아니다.

## 2026-09-08 Tag–Ability v2 문서 확정 및 M1 적용 대기

### 현재 상태와 마지막 검증

- 요청한 MD 확립/마이그레이션 설계/M1 안내는 완료했다. 전체 목표는 [v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2), 단계는 [M0–M10](CHARACTER_TAG_ABILITY_MIGRATION.md), 첫 안내는 [M1 공통 ASC](CHARACTER_TAG_ABILITY_STEP_1.md)다.
- 현행 게임 구현은 변경하지 않았다. M1 사용자 적용/빌드/PIE가 대기 상태이며, 작업 실패로 중단한 것은 아니다.
- 저장된 표적 리포트 대상 Source/Config/uproject/ABP_Player 39개 파일이 동일 hash였고 주요 코드/모듈/UE 5.8.2 ActorInfo API를 대조했다. 문서 코드가 실제 빌드/실행된 것으로 기록하지 않는다.
- 앞선 Stop 디버거/예약 callback/시각 검증 대기 항목의 해결 여부는 이번 문서 작업으로 확인하지 않았다. 과거 PID/세션을 현재 것으로 취급하지 않는다.

### 정확한 재개 절차

1. Router → 아키텍처 v2 → M0–M10의 현재 단계 → M1 가이드를 읽는다. v1 A1의 HFSM State 생성이나 이전 Pivot 관측 멤버 추가부터 시작하지 않는다.
2. 사용자 적용 여부를 현재 `Khazan.uproject`, `Khazan.Build.cs`, `KhazanCharacter.h/.cpp`와 git diff로 확인한다. 이미 적용된 조각을 중복 삽입하지 않는다.
3. M1은 엔진 UAbilitySystemComponent/IAbilitySystemInterface, PostInitialize 최초 연결, 빙의 후 Refresh, EndPlay DestroyActiveState다. 아직 Ability/Attribute/태그 상태가 없어도 안내 범위상 정상이다.
4. 실제 에디터/빌드/디버깅을 재개할 때만 이전 실행 상태를 현재 도구로 확인하고 필요한 정리를 한다. 사용자 미저장 변경을 임의로 일괄 저장/종료하거나 강제 종료하지 않는다.
5. 사용자 적용 후 전체 KhazanEditor Win64 Development 빌드와 Player/Monster ASC·Owner/Avatar·Controller/종료, 기존 이동 회귀를 확인하고 결과를 기록한다. 게임 코드 직접 수정은 사용자가 요청한 범위에서만 한다.
6. M1 완료가 확인되면 M2 최소 태그/공통 이동의 작은 소단계로 진행한다. 이후 실제 상태/수명 변화는 v2와 현행 정본에 날짜별로 추가한다.



## 2026-09-09 — M1 공동 구현 재개, 사용자 적용 대기

- 현재 결정: 자체 Tag-FSM 제안은 사용자 요청으로 철회. 기존 GAS v2 / M0–M10을 유지한다.
- 완료한 일: M1 안내의 엔진/현재 소스 대조와 [상세 보충](CHARACTER_TAG_ABILITY_STEP_1.md#m1-resume-detail-20260909). 문서 설명 완료이며 런타임 마이그레이션 완료가 아니다.
- 마지막 검증: 현재 Character/Build.cs/uproject에 M1 미적용, 표적 게임 파일 39개 hash 일치, UE 5.8.2 ActorInfo/Pawn lifecycle 정적 검토. 신규 빌드/PIE 결과와 작업 실패는 없다.
- 남은 작업: 사용자가 네 파일 적용 → 전체 KhazanEditor 빌드 → 새 Editor에서 Player/Monster 각 ASC/인터페이스/Owner/Avatar·Controller 갱신·종료·기존 이동 검사.
- 정확한 재개: Router → v2의 GAS 유지 결정 → Migration 최신 M1 기록 → Step 1 본문/2026-09-09 보충 → 실제 네 파일 diff를 읽는다. 이미 적용한 코드/플러그인을 중복 삽입하지 않는다. M1을 통과한 뒤 M2로 이동한다.
- 실제 Editor/디버깅을 수행하기 전에는 이전 Stop 진단 항목을 현재 세션 기준으로 확인한다. 이번 문서 작업은 과거 디버거/예약 callback의 현재 상태 확인이나 종료 정리를 수행하지 않았다.


### 같은 작업 후속 확인 — 다음 재개 위치 조정

- Khazan.uproject의 GameplayAbilities 활성화 항목은 현재 디스크에 있다. Build.cs/Character의 나머지 M1 적용은 마지막 확인 시 대기다. 다음 재개는 실제 네 파일을 먼저 대조하고, 플러그인을 중복 추가하지 않은 채 Step 1의 3.3 이후부터 이어간다. uproject 설정의 파일 반영과 엔진 로드/빌드/PIE 성공은 별개다.



## 2026-09-09 — M1 완료 보고 후 M2.1 적용 안내 대기

- 현재 상태: M1 사용자 완료 보고 + 네 파일 핵심 구현 반영 확인. M2는 [새 가이드](CHARACTER_TAG_ABILITY_STEP_2.md)의 M2.1부터 사용자 공동 구현으로 진행한다.
- 완료한 일: 현재 이동 입력 소실 경로/공통화 잔여 분석, M2.1–M2.4 범위, M2.1 코드/각 줄/데이터 수명/UE 5.8 효과 설정/중첩 검사 안내.
- 마지막 검증: Source/엔진 API 정적 확인. M1의 개별 빌드/PIE 결과는 이번에 독립 회수하지 않았고, M2 적용/빌드/PIE는 아직 없다. 작업 실패로 중단된 것은 아니다.
- 다음 재개: Router → v2 최신 M2 계약 → Migration 현재 M2.1 → Step 2 → 실제 GameplayTags/LocomotionType/Character Component/Player/Anim GT 소스를 읽는다. 이미 추가한 tag/콜백을 중복 생성하지 않는다.
- 사용자 적용 후 전체 빌드와 효과 A/B의 독립 handle 제거, 원시 입력 보존/실제 Released, 초기 조회/종료/GT 경계를 확인한다. M2.1 통과 후 M2.2의 BP/CDO 수치·CharacterDefinition·CMC 작성자로 진행한다.
- M2.3 AI 구동과 M2.4 통합 검증 전에는 M2 전체 완료로 기록하지 않는다. 실제 runtime 도구를 사용할 때는 현재 에디터/디버거 세션 상태를 새로 확인하며 과거 PID/예약 callback을 재사용하지 않는다.


## 2026-09-09 — M2.1 PIE 종료 crash 수정·재검증 대기

- 현재 상태: 최신 두 PIE 종료가 `ActorComponent.cpp:1668`, `Assertion failed: bHasBegunPlay`로 반복 종료됐다. crash 원인은 `UKhazanLocomotionComponent::EndPlay()`의 `Super::EndPlay()` 2회 호출로 확정했다.
- 추가 실패: BeginPlay에서 `RegisterGameplayTagEvent()` 반환 참조를 지역 delegate로 값 복사한 뒤 AddUObject했다. 실제 ASC delegate에 callback이 없으므로 동적 태그 변화 시험은 유효하지 않다.
- 마지막 검증: 최신 crash dump/로그, UE 5.8.2 ActorComponent와 AbilitySystemComponent 선언, 현재 Source/diff, test GE binary token과 과거 validation log를 정적으로 대조했다. Editor는 현재 종료 상태다. 새 빌드·수정 후 PIE는 수행하지 않았다.
- 정확한 재개 1: Router → v2 → Migration M2.1 → Step 2의 17절 → `KhazanLocomotionComponent.cpp`를 연다. EndPlay 첫 Super를 제거하고 마지막 Super 하나만 남긴다.
- 정확한 재개 2: BeginPlay의 지역 `FOnGameplayEffectTagCountChanged Event` 값 복사 블록을 제거하고 `ASC->RegisterGameplayTagEvent(...).AddUObject(...)` 직접 체인으로 handle을 저장한다.
- 정확한 재개 3: Editor를 완전히 닫은 상태에서 전체 KhazanEditor Win64 Development를 빌드하고 새 Editor에서 무효과 PIE 시작/이동/종료를 먼저 검사한다.
- 정확한 재개 4: A/B를 별도 handle로 적용해 count 0→1→2→1→0, callback은 0→1과 1→0에서만 호출, 허용 true→false→false→false→true, 원시 입력 보존/Released, Stop PIE와 두 번째 PIE 종료를 확인한다.
- 합격 전 제한: M2.1 완료 또는 M2.2 시작으로 기록하지 않는다. Player BP의 최신 로그에는 handle/count 결과가 없으므로 화면상 움직임만으로 합격시키지 않는다.


## 2026-09-09 — M2.1 핵심 재검증 통과, 수동 입력·전체 빌드 대기

- 현재 상태: 이전 두 C++ 결함은 사용자 수정본에서 해결됐다. 실제 Test GE의 중첩 count/개별 handle 제거/허용 캐시, 활성 효과를 남긴 Stop PIE, 새 PIE의 깨끗한 시작과 재종료까지 통과했다. 새 crash report가 없고 Editor PID 23328은 응답 중이며 PIE Idle이다.
- 마지막 검증: A/B runtime handle 11/12는 별도 효과로 적용·제거됐고 count/효과 수/허용은 `0/0/true → 1/1/false → 2/2/false → 1/1/false → 0/0/true`였다. 활성 handle 13을 둔 종료도 정상이고 다음 PIE는 `0/0/true`였다. Player BP 자체 handle 14/15도 둘 다 적용 성공이고 서로 달랐다.
- 현재 BP 한계: BeginPlay의 Sequence가 A와 B를 적용한 직후 같은 호출에서 A와 B를 제거한다. BP는 정상 실행되지만 사람이 이동을 시험할 프레임이 없어 화면만으로 차단 여부를 판단할 수 없다.
- 자동 입력 확인 한계: Enhanced Input 연속 주입이 허용 상태에서도 `IA_Move` binding에 도달하지 않아 변위/InputAmount가 모두 0이었다. 이 결과를 gameplay 결함으로 기록하지 않으며 실제 입력 검증 근거에도 쓰지 않는다. 사용한 연속 주입은 중단했고 임시 Python 참조도 제거했다.
- 정확한 재개 1: BeginPlay에는 `GetAbilitySystemComponent` → `Set TestASC` → `IsValid`만 남긴다. 기존 적용/제거 노드는 삭제할 필요 없이 네 Custom Event `Test_ApplyA`, `Test_ApplyB`, `Test_RemoveA`, `Test_RemoveB`에 각각 옮겨도 된다.
- 정확한 재개 2: PIE에서 이동 가능 → ApplyA 뒤 이동 차단 → ApplyB 뒤 계속 차단 → RemoveA 뒤 계속 차단 → RemoveB 뒤 다음 입력부터 재개를 키보드/패드로 관찰한다. 차단 중 Move Released 뒤 Intent의 벡터와 양도 0인지 확인한다.
- 정확한 재개 3: Editor를 완전히 종료하고 `KhazanEditor Win64 Development` 전체 빌드 후 새 Editor에서 위 순서를 한 번 더 시작·종료한다. 현재 검증은 성공한 Live Coding patch 기준이다.
- 완료 조건: 위 수동 입력과 전체 빌드가 통과하면 M2.1을 닫고 M2.2의 데이터/CMC 작성자와 제약 정책으로 진행한다. C++ tag/count/EndPlay probe는 관련 코드가 다시 바뀌지 않았다면 반복할 필요가 없다.

### 같은 세션 후속 — 실제 입력 확인 해결

- 앞 절의 수동 입력 미확인은 해결됐다. 실제 `IA_Move` action에 벡터를 프레임별 주입해 차단 중 원시 입력 도달과 CMC 출력 차단, 효과 제거 뒤 이동 재개, 주입 종료 뒤 Released 정리를 모두 관측했다.
- 차단 상태는 count 1 / 허용 false / InputAmount 1.0 / 변위·속도·가속도 0이다. 해제 상태는 count 0 / 허용 true / InputAmount 1.0 / 변위 387.214 uu / 속도 `(0,470,0)` uu/s / 가속도 `(0,1800,0)` uu/s²다. 이는 현재 실행 관측값이다.
- 마지막 검증 뒤 Test GE handle을 제거했고, action 주입 callback과 모든 임시 Python 참조를 정리했으며 PIE는 정상 종료했다. Editor PID 23328은 Idle/응답 상태다.
- 현재 남은 작업은 Editor를 완전히 종료한 상태에서 전체 `KhazanEditor Win64 Development` 빌드 후 새 Editor 시작·PIE 종료를 한 번 확인하는 것이다. 사용자 Editor를 임의 종료하지 않았으므로 이번 세션에서는 수행하지 않았다.
- 전체 빌드가 성공하면 M2.1을 완료 처리하고 [M2.2](CHARACTER_TAG_ABILITY_STEP_2.md)의 데이터/CMC 작성자·제약 정책 설명으로 재개한다. 현재 BP를 네 Custom Event로 분리하는 작업은 화면상 수동 재현이 필요할 때만 하는 테스트 개선이며 필수 기능 수정이 아니다.


## 2026-09-09 — M2.1 완료, M2.2 적용 대기

- 현재 상태: M2.1의 마지막 조건인 Editor 종료 상태 전체 Development Editor 빌드가 성공했다. M2.1은 완료이며 현재 공동 구현 범위는 [M2.2와 M2.3 상세 가이드](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)다.
- 마지막 정적 조사: `Saved/ImportReports/M2_2_3_CurrentCDO_20260909.json`에서 Player BP 부모/실제 CDO와 수입 적 BP 부모를 확인했다. Player CDO CMC는 아직 base class이고 MaxWalkSpeed 300이다. Swordsman/Archer 시각 BP는 AActor 부모다.
- 적용 순서 1: M2.2 type/CharacterDefinition/Character/Locomotion/Player/Anim GT를 사용자 적용한다. Editor 종료 전체 빌드 → `PDA_Character_Khazan` 생성·할당 → Player/constraint/token/PIE 종료 검증을 먼저 통과시킨다.
- 적용 순서 2: M2.3 Build.cs/Khazan CMC/ObjectInitializer/AIController/Monster를 적용한다. 다시 전체 빌드 → 시험 Monster Definition/BP/Blackboard/BT/NavMesh/진단 ABP를 연결한다.
- 필수 런타임: RequestPathMove와 RequestDirectMove 둘 다 검사하고, Block A/B `0→1→2→1→0`, 차단 중 새 request, abort 후 미재개, 도착/실패 cleanup, 다른 pause 소유, UnPossess/Repossess와 반복 PIE를 확인한다.
- 게임 파일은 이번 가이드 작성에서 수정하지 않았다. 사용자 적용 결과를 받으면 현재 소스와 실제 CDO를 먼저 다시 읽고 문서 예제와 차이를 설명한다. M2.4 통합 전에는 M2 전체 완료나 M3 시작으로 기록하지 않는다.


## 2026-09-09 — M2.2 `KhazanLocomotionType.h` 사용자 적용 중

- 현재 상태: 사용자가 M2.2의 `KhazanLocomotionType.h`를 수정 중이다. 명시적 gait 값, intent source enum, 요청 회전, constraint, resolved policy, config 뼈대는 반영됐다. 프로젝트는 의도적인 중간 상태라 전체 빌드 성공을 기대하지 않는다.
- 현재 정정 1: raw intent에 남은 `bMovementAllowed`를 삭제한다. ASC tag projection은 `FKhazanResolvedMovementPolicy::bMovementAllowedByTags`, 최종 허용은 `IsMovementInputAllowed()`가 소유한다.
- 현재 정정 2: config의 `MinAnalogWalkSpeed=170.f`를 현재 Player CDO 이관값 `15.f`로 바꾼다. Walk gait 최대 속도 170과 다른 CMC 필드이며 둘 다 원작 metadata 직접 확인값은 아니다.
- 재개 문서: [M2.2 순서형 공동 구현 실습판](CHARACTER_TAG_ABILITY_M2_2_WALKTHROUGH.md). A(Type header) → B(Type cpp) → C(Definition) → D/E(LocomotionComponent) → F(Character) → G(Player) → H(Anim GT)까지 적용한 뒤 처음으로 Editor 종료 전체 빌드를 한다.
- 예상 중간 오류: 옛 `Intent.MaxAllowedGait`, `Intent.RotationMode`, `Intent.bMovementAllowed`, 인자 없는 setter 참조가 Component/Player/Anim에 남아서 발생한다. 삭제 필드를 복구하지 않고 각 소비자를 새 policy/handle API로 이관한다.
- 어시스턴트 검증 범위: 현재 source와 diff의 정적 대조 및 문서 작성만 수행했다. 게임 소스·BP·asset 수정, 현재 중간 상태 빌드, PIE는 수행하지 않았다.


## 2026-09-09 — M2.2 20.2~20.5 정적 검토, 다음은 20.6

- 사용자 진행: `KhazanLocomotionType.h/.cpp`, `KhazanCharacterDefinition.h/.cpp`, `KhazanCharacter.h/.cpp`까지 작성했고 다음 공동 구현 지점은 `KhazanLocomotionComponent.h`의 두 handle 선언이다.
- 통과: config/raw intent/constraint/resolved policy 분리, `MinAnalogWalkSpeed=15.f`, raw intent의 허용 bool 제거, config 검증·gait 속도 매핑, 최소 Character Definition의 const getter와 property는 계약과 일치한다.
- 20.6 전에 수정 1: `AKhazanCharacter::GetLocomotionComponent()` 위에 `UFUNCTION(BlueprintPure, Category = "Character|Locomotion")`을 추가한다. M2 시험 BP가 공통 component를 읽는 실제 소비가 있다.
- 20.6 전에 수정 2: `PostInitializeComponents()`는 `if (!World || !World->IsGameWorld()) { return; }`로 먼저 빠져나온 뒤 ASC ActorInfo와 Definition/Locomotion config를 모두 초기화해야 한다. 현재 소스는 ASC 초기화만 GameWorld 분기 안에 있고 config 초기화가 바깥에 있어 preview/editor world에서도 실행될 수 있다.
- 예상 중간 오류: `InitializeMovementConfig`가 Component에 아직 선언되지 않은 것은 20.7 이전의 정상적인 미완성 상태다. 임시 stub이나 삭제 필드 복구 없이 20.6 handle → 20.7 public 계약으로 이어간다.
- 검증 범위: 읽기 전용 소스/diff 정적 검토만 수행했다. 중간 빌드, PIE, 사용자 C++·BP·asset 수정은 수행하지 않았다.


## 2026-09-09 — M2.2 20.6 두 handle 사용자 반영 확인

- 사용자 진행: `KhazanLocomotionComponent.h`의 `FKhazanLocomotionIntentHandle`, reflected `FKhazanMovementConstraintHandle`, native `FKhazanMovementInputPermissionChanged` 선언이 반영됐다. Component forward declaration, weak issuing-component pointer, private GUID, friend 접근, constraint handle의 Transient property 구성이 계약과 일치한다.
- 직전 정정 확인: Character의 Locomotion getter에 `BlueprintPure`가 추가됐고 `PostInitializeComponents()`는 non-GameWorld 조기 return 뒤 ASC와 locomotion config를 함께 초기화한다.
- 현재 이해 경계: Handle의 `Owner`는 gameplay 원인 Source나 ASC OwnerActor가 아니라 해당 handle을 발급한 LocomotionComponent다. `Handle::IsValid()`는 포인터/GUID의 구조적 유효성이고 현재 active ID/map membership은 이후 Component API가 별도로 판정한다.
- 다음 구현 지점은 20.7 Component public 계약이지만, 사용자의 요청에 따라 이번 응답은 Source/Target/Owner/Effect/Handle/GUID와 config→intent/constraint→policy→CMC 흐름의 개념 설명만 수행한다.
- 검증 범위: 소스 정적 대조만 수행했다. 진행 중 전체 빌드·PIE와 게임 파일 수정은 수행하지 않았다.

## 2026-09-10 — M2.2 Component 정책 체크포인트, Player·Anim 이관 대기

- 현재 상태: `FKhazanLocomotionConfig`, raw Intent, 원인별 Constraint, ResolvedPolicy와 Component의 intent token/constraint 장부/policy→CMC 적용/tag projection/EndPlay가 사용자 작업 트리에 반영됐다. M2.2 §20.16까지의 중간 상태이며 Player §20.17과 AnimInstance §20.18은 아직 옛 API를 사용한다.
- 마지막 검증: Editor 종료 상태에서 전체 `KhazanEditor Win64 Development` 빌드를 실행했다. UHT는 통과했지만 `KhazanPlayer.cpp`의 handle 없는 setter 및 삭제된 `GetIntent`/`SetTargetGait`, `KhazanAnimInstance.cpp`의 삭제된 `GetIntent`/`MaxAllowedGait`/`RotationMode` 참조로 exit 1이었다. Component/Type/Character/Definition은 이 실행에서 compile 단계가 완료됐다.
- 실패 원인: 순서형 마이그레이션에서 producer/공통 policy API가 먼저 바뀌었고 두 소비자가 아직 새 계약으로 이관되지 않았다. 삭제된 호환 API를 되살리는 방식으로 해결하지 않는다.
- 남은 작업: Player가 Possess 수명에 맞춰 `FKhazanLocomotionIntentHandle`을 발급·종료하고 모든 raw intent write에 전달하도록 §20.17을 적용한다. AnimInstance GT snapshot은 raw Intent와 ResolvedPolicy를 각각 읽도록 §20.18을 적용한다. 기존 trailing whitespace도 최종 변경 전에 정리한다.
- 정확한 재개: Router → 아키텍처 v2 → Migration 현재 M2.2 → `CHARACTER_TAG_ABILITY_STEP_2.md` §20.17/§20.18 → 실제 Player/Anim/Component 헤더와 소스를 대조한다. 두 소비자 이관 후 전체 빌드 → `PDA_Character_Khazan` 연결 → token/constraint/ASC 중첩/UnPossess·EndPlay/기존 로코모션 PIE 순으로 검증하고, 그 전에는 M2.2 완료나 M2.3 시작으로 기록하지 않는다.
- Git 의도: 사용자의 요청에 따라 현재 컴파일 실패를 숨기지 않는 WIP 체크포인트로 전체 변경을 main에 전달한다. 빌드 산출물은 Git 대상에 포함하지 않는다.


## 2026-09-11 — AssetManager 복원 완료, Definition 사용자 연결 대기

- 현재 상태: 과잉 보강은 Git HEAD의 기존 AssetManager API/FName cache로 복원했고 PostLoad index rebuild/null 안전성/batch cache·release 대칭만 남겼다. 직접 수정은 AssetManager/AssetData/Controller의 과잉 보강 묶음으로 끝났다.
- 수정 직전 다섯 소스의 원본 백업: `Saved/CodeBackups/AssetManager_20260911_170505/`. Git HEAD를 전체 checkout하지 않았고 Character/Player/Anim/Component/Definition의 사용자 변경은 유지했다.
- 마지막 검증: 최종 전체 Development Editor 빌드 exit 0, 새 프로세스 DevMap 로드/종료 exit 0. 근거는 `Saved/Logs/AssetManagerRollback_Build_20260911.log`와 `AssetManagerRollback_Startup_Final_20260911.log`. IDE 문서의 지연 저장을 발견해 동기화/재검증했으므로 이전 Startup 로그를 최종 근거로 사용하지 않는다.
- 남은 검증 한계: Python에서 `AssetNameToPath`는 protected라 내부 map 비교를 수행하지 못했다. map 개방/새 debug API를 게임 코드에 추가하지 않았다. 미등록 tag/path의 negative runtime 검사, 실제 이동/Stop/반복 PIE는 미검증이다.
- 다음 미완료 원인: Player/시험 Monster의 CharacterDefinition이 아직 없고 Player의 locomotion intent 획득도 실패한다. 새 에셋 파일은 있으나 tag/selector/catalog/BP 연결이 아직 없다. 이번 승인으로 이 후속 코드를 직접 구현하지 않는다.
- 정확한 재개: Router → v2 ARCH-16/17의 마지막 복원 결정 → Migration M2.2 → [Step 2 §27](CHARACTER_TAG_ABILITY_STEP_2.md#asset-manager-rollback-next-20260911). 실제 native tag → 필요 최소 로드 선택 인자 → Character selector/runtime pointer/초기화 조회 → cold build → catalog entry/Player BP tag → Player 이동 회귀 순으로 사용자가 적용한다. 아직 소스에 없는 optional 인자나 tag를 이미 구현된 것으로 가정하지 않는다.
- 실행 정리: 실행한 Build/Startup/Python commandlet 프로세스는 종료됐다. 디버거/PIE callback은 만들지 않았다. 이번에 uasset/Config를 저장하지 않았으며 새 gameplay 수치는 없다.

## 2026-09-15 M2.2 Definition 연결 완료 후 패드 없는 검증 재개 지점

- 현재 상태: Character Definition native tag, AssetManager의 비강제 조회, Character selector/runtime 참조, catalog entry, Player BP selector, Definition LocomotionConfig 저장까지 반영됐다. 실제 저장값도 읽기 전용으로 확인했다.
- 마지막 정적 검증: KhazanCharacter.h/.cpp, KhazanAssetManager.h, gameplay tag 선언·정의가 서로 일치하며 CMC 주요 이동 속성의 직접 작성자는 LocomotionComponent 하나다. Rider 분석 오류는 0이지만 현재 변경분의 cold build 성공을 새로 확정하지는 않았다.
- 런타임 미검증 사유: 현재 사용할 물리 패드가 없고 IMC_Default의 Move/Sprint에는 키보드 매핑이 없다. 이는 진행 차단 사유가 아니며 Enhanced Input 콘솔 주입으로 실제 Gamepad 매핑과 Input Action callback 경로를 검증할 수 있다.
- 정확한 재개 절차: Editor 완전 종료 → KhazanEditor Win64 Development cold build → Editor 재실행/DevMap PIE → Input.+key Gamepad_Left2D와 Input.-key로 Walk/Run/Stop 확인 → Thumbstick 입력으로 토글 Sprint 확인 → /Game/Test/M2/BP_M2MovementProbe에서 gait/rotation constraint A/B 중첩·역순 제거·중복 제거와 Block GE A/B를 검증 → constraint/GE를 남긴 PIE 종료와 재PIE cleanup을 확인한다.
- 완료 조건: Definition 오류 없이 Player가 시작하고, snapshot·CMC 결과가 config 및 제한 정책과 일치하며, A/B 중첩과 개별 handle 제거, 태그 차단 중 raw intent 보존, 재PIE 초기화가 모두 통과해야 한다. 그 뒤에만 M2.3의 custom CMC/AIController 구현으로 이동한다.
- 이번 기록에서는 게임 Source, BP, DataAsset을 추가 수정하지 않았다.

## 2026-09-15 M2.2 테스트 이벤트 인수 완료, M2.3 재개 지점

- 현재 상태: M2.2 Player runtime 행렬은 통과했다. `/Game/Test/BP_M2MovementProbe`는 compile/save됐고, 실제 입력 mapping/action, gait·rotation constraint A/B, Block GE A/B, UnPossess/Repossess, Stop PIE/새 PIE cleanup을 확인했다. PIE는 종료돼 Idle이며 테스트 effect/constraint/forced input은 남아 있지 않다.
- 마지막 검증: 새 PIE 기준 `InputAmount=0`, Block tag count `0`, 허용 true, MaxAllowedGait Sprint, ResolvedGait Walk, ResolvedRotationMode VelocityDirection, 정책/CMC MaxWalkSpeed `170`, Velocity `0`이다. gameplay assertion/fatal과 Probe 수리 뒤 BP compile error는 없다. API 탐색 중 Python 오류와 별도 WildBoar import 경고는 분리 기록했다. 전체 raw 결과는 `Saved/Reports/M2_2_RuntimeProbe_20260915.json`이다.
- 테스트 한계: 물리 패드가 없어 하드웨어 이벤트는 직접 누르지 않았다. `Gamepad_Left2D`/`Gamepad_LeftThumbstick` 실제 mapping과 `IA_Move` action은 콘솔로 주입했다. UE 5.8의 `Input.-key` 아날로그 상쇄 샘플은 엔진 소스로 확인해 별도 진단으로 분리했고, action 제거로 Completed 정리를 검증했다.
- 빌드 상태: 정식 Editor 모듈의 생성 시각이 모든 현재 Source보다 뒤이고 실제 검증 Editor가 그 뒤 시작됐다. 현재 소스가 반영된 정식 모듈에서 PIE한 사실은 확인했지만 이번 인수 중 새 cold-build 명령 transcript는 만들지 않았다.
- 정확한 재개 1: Router → `CHARACTER_GAMEPLAY_ARCHITECTURE.md` v2 → `CHARACTER_TAG_ABILITY_MIGRATION.md` M2 → `CHARACTER_TAG_ABILITY_STEP_2.md` 21절을 순서대로 읽고 M2.3만 범위로 잡는다.
- 정확한 재개 2: 실제 일반 적 기반을 다시 대조한다. 수입 Swordsman/Archer가 여전히 `AActor` 부모라면 억지 reparent하지 않고 `AKhazanMonster` 기반 최소 시험 Pawn, Definition, AIController, Blackboard/BT, NavMesh의 필요한 최소 자산만 만든다.
- 정확한 재개 3: 공통 `UKhazanCharacterMovementComponent`의 `RequestPathMove`/`RequestDirectMove` gate와 `AKhazanAIController`의 concrete `FAIRequestID`, Block tag delegate, 자기 pause 소유권/cleanup을 구현한다. Player의 통과한 입력·정책 코드를 다시 고치지 않는다.
- 정확한 재개 4: 정상 MoveTo, A/B `0→1→2→1→0`, 차단 중 새 요청, 같은 request만 resume, Abort/실패/AlreadyAtGoal, 다른 pause 원인, Path/Direct 두 모드, AI UnPossess/Repossess, 반복 PIE를 21.15–21.24 순서로 검증한다. 그 뒤 M2.4 통합 전에는 M3로 넘어가지 않는다.
## 2026-09-15 M2.3-A 사용자 구현 대기

- 현재 상태: M2.2 runtime 행렬은 앞선 기록대로 완료됐고, M2.3-A의 현행 심볼 및 AI 자동 빙의 초기화 순서 보강안을 설명할 준비가 끝났다. 게임 Source에는 아직 적용되지 않았다.
- 마지막 정적 검증: 현재 Character/Locomotion/Player/Monster/Build.cs와 UE 5.8.2의 `APawn::PostInitializeComponents`, `AAIController::RequestMove`, `UPathFollowingComponent::PauseMove/ResumeMove`, `UCharacterMovementComponent::RequestPathMove/RequestDirectMove`를 대조했다.
- 남은 작업: 사용자가 M2.3-A의 Build.cs, 공통 CMC, Character 생성/초기화 순서, AIController, Monster 기본값을 적용한다. 이어 Editor 종료 cold build와 Player CDO/PIE 회귀를 확인한다.
- 정확한 재개 절차: 실제 적용된 다섯 영역의 diff와 첫 build 결과를 확인한다. 성공하면 `/Game/Test/M2` test controller/monster 및 BB/BT/NavMesh를 만들고 기존 `/Game/Test/BP_M2MovementProbe`의 TargetCharacter를 Monster로 지정해 이동, tag block 중 raw intent 보존·감속·동일 request pause/resume, 중첩 effect, 목표 교체, 완료/Abort/UnPossess/PIE cleanup을 검증한다.


## 2026-09-15 Player 우선 전투 아키텍처 재검토 완료, P1 재개 지점

- [현재 상태] 사용자 요청으로 M2.3-A AIController 선행 구현을 보류했다. `UKhazanCharacterMovementComponent`, `AKhazanAIController`, Monster 자동 빙의, Blackboard/Behavior Tree는 아직 적용되지 않았으므로 게임 소스 롤백 대상이 없다. 직전 M2.3-A 구현 대기 절은 과거 계획이다.
- [보존 기준] M1/M2.1과 M2.2 Player runtime 행렬은 완료 상태를 유지한다. 현재 `AKhazanCharacter`는 엔진 ASC와 LocomotionComponent/Definition을 공통 소유하고, PlayerController의 Attack은 비어 있으며 Jump는 직접 호출/시험 진동, Monster는 빈 Character shell, SprintPivot/Combo/Stamina/CombatResponse/Ability는 미구현이다.
- [새 결정] ASC/Ability/Attribute/CombatResult/Locomotion/Anim/Progression의 상태 축을 분리하고, Player 입력에서 공통 ActionRequest와 한 Basic Attack 실행을 먼저 검증한다. AI는 같은 요청 계약의 두 번째 의도 생성자로 A1/A2에서 연결한다. 세부 계약은 Architecture `2026-09-15 v2.1 ARCH-20–29`, 실행 순서는 Migration `2026-09-15 Player 우선 순서 개정`이 정본이다.
- [정확한 재개 1] Router → Architecture 최신 v2.1 → Migration 최신 P1 → 현재 `KhazanGameplayTags`, `KhazanCharacter`, `KhazanPlayerController`, `KhazanPlayer`, `KhazanCharacterDefinitionData`, ASC 초기화 소스를 표적 대조한다. Step 2 21절의 AI 코드를 적용하지 않는다.
- [정확한 재개 2] P1 상세 공동 구현 가이드를 현재 소스 기준으로 작성한다. 실제 Basic Attack 소비와 함께 `UKhazanAbilitySystemComponent`, Ability base, 최소 grant/input mapping, Ready, 요청/실행 ID와 전신 action lane을 단계별로 만들고 Attack/Jump 직접 우회를 이관한다. 미사용 Combo/Parry/AI 타입은 선행 생성하지 않는다.
- [정확한 재개 3] 사용자가 P1을 적용한 뒤 Editor 종료 전체 build → ASC subobject/CDO → ActorInfo/Definition/grant/Ready → Attack 단일 요청·실행 → 반복 입력/차단/실패 결과 → 정상/중단/UnPossess/EndPlay cleanup → M2.2 이동 표적 회귀 순으로 확인한다.
- [이번 검증 범위] 이번에는 아키텍처/마이그레이션/라우터/Step 2/Locomotion 정본만 갱신했다. Source, Config, BP, DataAsset, 애니메이션 에셋을 수정하거나 신규 build/PIE를 실행하지 않았다. 기존 에셋 작업 트리 변경은 건드리지 않았다.

## 2026-09-15 P1-A 사용자 적용 대기

- [현재 상태] P1 시작 전 실제 소스 대조와 Editor 종료 전체 Development Editor 빌드가 통과했다. P1 코드는 아직 없고 기존 M1/M2.1/M2.2 구현과 사용자 작업 트리 변경은 보존돼 있다.
- [별도 진단] 직전 Editor는 Content Browser rename assert로 종료됐지만 P1 gameplay/Source와 무관하다. 현재 UnrealEditor/LiveCodingConsole 프로세스는 없으며 P1-A를 시작할 수 있다.
- [정확한 재개] [P1 실습판](CHARACTER_TAG_ABILITY_P1_WALKTHROUGH.md) §4–5에 따라 기존 native tag의 선언/정의 위치를 보존해 P1에서 즉시 소비할 tag만 추가하고, `Source/Khazan/Ability/KhazanActionTypes.h`를 작성한다. 사용자가 저장한 두 tag 파일과 새 type header를 정적 대조한 뒤 P1-B의 custom ASC/base Ability로 이동한다.
- [검증 경계] P1-A 단독 build를 완료 조건으로 요구하지 않는다. P1-E까지 C++ 계약을 닫은 뒤 Editor 종료 전체 build를 수행한다. 이번 턴에는 게임 Source, BP, DataAsset, Animation asset을 수정하지 않았다.

## 2026-09-15 P1 아키텍처 재검토 — 기존 P1-A 보류

- [현재 상태] 사용자 요청으로 StateTree + GAS tag 관계 + Input Buffer/AnimNotify 구성과 현행 v2/P1을 다시 대조했다. 게임 Source/BP/DataAsset/Animation asset은 변경하지 않았고 P1 코드는 아직 적용되지 않았다.
- [판정] StateTree는 공식 범용 HFSM이지만 Player 전투/콤보 최상위 제어기의 공식 1순위 표준이라는 근거는 확인되지 않았다. v2의 GAS 중심 책임 분리는 타당하나 P1 실습판의 custom request/execution 추적 계층은 첫 수직 절편에 과하다.
- [중단 지점] 기존 P1 실습판의 P1-A tag와 `KhazanActionTypes.h`를 적용하지 않는다. 실습판 하단의 `중요: 이 실습판 적용 보류` 절을 따른다.
- [재개 절차] 사용자가 방향을 결정하면 Architecture의 `StateTree·GAS·입력 버퍼 대조 검토와 P1 단순화 제안`을 기준으로 ARCH-22/P1 계약을 교체하고, 최소 custom ASC + InputTag + AbilitySet + BasicAttack/Jump Ability의 새 단계별 실습판을 작성한다. 그 뒤 사용자가 첫 소단계를 구현하고 정적 검토부터 재개한다.
- [남은 결정] Player combat StateTree는 도입하지 않는 권고, P1 custom request ledger 제거, 콤보 buffer의 활성 Combo Ability 지역 소유를 채택할지 확정해야 한다. StateTree는 A2 AI 상위 판단 또는 보스/Scripted orchestration의 실제 필요가 생길 때 별도 검토한다.

## 2026-09-15 GAS v2.2 채택 — 최소 P1 실습판 재작성 대기

- [결정 완료] 사용자가 GAS 중심 구조 유지, Player 전투 StateTree 미도입, 기능에 필요 없는 거대 구조·복잡한 관계·불명확한 명명 배제를 확정했다. 이전 절의 `남은 결정`은 해소됐다.
- [최신 정본] Architecture의 `v2.2 GAS 중심 구조와 단순성 불변식`과 Migration의 `v2.2 최소 P1 계약`을 사용한다. 과거 P1 ActionRequest 실습판은 폐기 상태다.
- [현재 Source] P1 Ability 코드는 아직 없다. 엔진 ASC, 빈 Attack, Controller 직접 Jump/시험 진동, 검증된 M2.2 Locomotion이 그대로이며 롤백할 P1 Source는 없다.
- [다음 작업] 새 최소 P1을 의존 순서대로 작은 소단계로 다시 작성한다. 각 단계에서 현재 소비가 없는 class/tag/DataAsset/delegate/handle은 제외하고 사용자가 구현한 뒤 정적 대조한다.
- [검증 경계] 이번 감사에서는 게임 Source/BP/DataAsset/Animation asset을 수정하거나 build/PIE하지 않았다. 문서 diff와 현행 Source 사용처만 검사했다.


## 2026-09-15 — v2.3 P1.1 사용자 적용 대기

- 현재 상태: Architecture v2.3 capability component 계약과 Migration v2.3 P1 실행 순서, 새 `CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md`를 작성했다.
- 마지막 확인: `Khazan.uproject`의 UE 5.8/GameplayAbilities enabled, `Khazan.Build.cs`의 GameplayTags/GameplayAbilities/GameplayTasks dependency, 기존 base ASC subobject와 ActorInfo lifecycle을 표적 대조했다. 설치된 UE 5.8 header/source에서 `FScopedAbilityListLock`, `GetActivatableAbilities`, `GetDynamicSpecSourceTags`, `TryActivateAbility` signature를 확인했다.
- 게임 적용 상태: 새 `UKhazanAbilitySystemComponent` Source와 Character concrete subobject 교체는 설명만 했으며 아직 적용·compile·PIE 확인되지 않았다. 게임 Source/BP/asset은 이 작업에서 직접 수정하지 않았다.
- 정확한 재개 절차: Router 최신 절 → Architecture v2.3 → Migration v2.3 → P1 최소 실습판의 P1.1 순으로 읽는다. 사용자가 두 새 Source 파일과 Character cpp 한 줄 교체를 적용하고 Editor/Live Coding을 닫은 cold build 결과를 제공하면 파일을 실제 대조한다.
- P1.1 합격 조건: UHT/C++ build 성공, 기존 ASC subobject 한 개가 `UKhazanAbilitySystemComponent` concrete class로 생성, duplicate/invalid ASC 오류 없음, M2.2 locomotion 회귀 없음.
- 다음 단계: P1.1 합격 뒤 Ability class + 기존 Input Tag만 가진 최소 `UKhazanAbilitySet`과 CharacterDefinition grant를 P1.2로 설명한다. CombatComponent는 P3.1 첫 실제 hit까지 생성하지 않는다.


## 2026-09-15 — P1.2 직접 Definition grant 사용자 적용 대기

- 최신 결정: CombatComponent 중심 해석을 철회하고 모든 Component에 capability 기준을 적용한다. CombatComponent와 다른 후보 Component는 해당 단계의 실제 독립 능력/상태/cleanup이 확인될 때만 만든다.
- P1.1 실제 상태: 새 Khazan ASC 두 파일과 Character concrete class 교체가 적용됐고 UE 5.8.2 전체 build가 `Result: Succeeded`다. 새 Editor/PIE와 M2.2 runtime 회귀 증거는 아직 없다.
- P1.2 변경: 별도 `UKhazanAbilitySet`을 만들지 않는다. `UKhazanCharacterDefinitionData`에 `FKhazanInitialAbilityGrant { AbilityClass, InputTag }` 배열을 직접 추가하고 Character가 ActorInfo/Definition/Locomotion 성공 뒤 authority에서 한 번 `GiveAbility`한다.
- 정확한 재개: Router 최신 절 → Architecture v2.4 → Migration v2.4 → P1 최소 실습판 `p1-1-applied-p1-2-direct-grants-20260915` 순으로 읽고 Definition h/cpp와 Character cpp 세 파일만 적용한다.
- P1.2 합격: UHT/build 성공, 기존 Definition locomotion 값 보존, 새 `Initial Ability Grants` 배열이 보이며 크기 0, PIE 무효과와 기존 이동 유지, Definition/ASC 오류 없음.
- 다음 단계: P1.3에서 직접 `UGameplayAbility`를 상속하는 BasicAttack class 하나를 만들고 첫 Definition entry를 추가한다. Montage/hit/cost/constraint/input 연결은 아직 넣지 않는다.
- 이번 턴에는 문서만 append했다. 사용자가 적용한 P1.1 Source와 Content를 어시스턴트가 수정하지 않았고 P1.2 build/PIE도 실행하지 않았다.


## 2026-09-15 — P1.3 사용자 적용 대기

- 현재 상태: P1.2 Source는 적용됐고 UE 5.8.2 cold build가 19:36 `Result: Succeeded`다. 새 PIE/runtime 증거는 없다.
- 마지막 대조: Definition은 `AbilityClass + InputTag` 배열을 const reference로 제공하고 Character는 필수 초기화 성공 뒤 authority에서만 Spec을 만들어 `GiveAbility()`한다. `KhazanCharacter.cpp`의 `ParticleHelper.h`는 미사용 include다.
- 정확한 재개: Router 최신 절 → Architecture v2.4 → Migration `p1-3-basic-attack-spec-20260915` → P1 최소 실습판 `p1-2-applied-p1-3-basic-attack-spec-20260915` 순으로 읽는다. 사용자가 미사용 include를 제거하고 BasicAttack h/cpp를 작성해 cold build한 뒤 기존 CharacterDefinition에 native class와 `Input.Action.Attack` entry 한 개를 넣는다.
- P1.3 합격: build 성공, 기존 Definition locomotion 값 보존, ASC debug Ability 목록에 inactive BasicAttack Spec 정확히 한 개, activation log 0회, 기존 이동/PIE 종료 회귀 없음.
- 다음 단계: P1.4에서만 PlayerController Attack의 `Started`를 ASC InputTag activation에 연결한다.
- 이번 작업은 Engineering 문서만 append했다. 게임 Source/BP/DataAsset은 수정하지 않았다.

## 2026-09-17 — P6-A WeakAttack 단순화 적용 대기

- 현재 상태: `UKhazanWeakAttackAbility`는 `Attack01→Attack02`를 실행하기 위해 515줄과 두 window depth, Montage instance ID, task 재생 수명을 직접 관리한다. 정적 검토에서 제품 범위에 비해 과도하다고 판정했고 Architecture ARCH-42와 Migration 최신 절에 단순화 계약을 기록했다.
- 마지막 검증: UBT `-SingleFile`로 `KhazanWeakAttackAbility.cpp` compile 성공. `KhazanAbilitySystemComponent.cpp`와 `KhazanGameplayTags.cpp`도 compile됐으며 ASC에는 `AbilitySpec.ActivationInfo` deprecation warning 두 건이 있다. `KhazanPlayerController.cpp:30`은 `Engine/LocalPlayer.h` 누락으로 C2027/C2059/C2143 오류가 재현됐다.
- 남은 작업: 게임 Source와 Montage는 이번 설명 작업에서 수정하지 않았다. PlayerController include를 먼저 고친 뒤 WeakAttack의 `InputReservation`/`ComboAdvance` NotifyState Begin/End를 `ComboInputOpen`/`ComboCommit` 점 Notify로 교체하고 1–5 section index 구조로 정리해야 한다.
- 정확한 재개 절차: Router → Architecture ARCH-42 → Migration의 `P6-A 재감사` → 현재 WeakAttack h/cpp 순으로 읽는다. include 수정 후 에디터와 Live Coding을 완전히 종료한 cold build를 실행한다. 그 다음 코드 축소와 Montage Notify 배치를 적용하고 다시 cold build, PIE의 L/LL/LLLL/잠금 전후 LLLLL·mash·interrupt·Root Motion 연속성을 확인한다.

## 2026-09-17 — P6 브랜치 컷 재개 기준 갱신

- 최신 설계 정본은 Architecture `ARCH-43`이다. ARCH-41의 section별 Montage task 재생과 ARCH-42의 재생 기반 전환은 조사 이력으로 남지만 구현 기본안에서는 대체됐다.
- 확정 방향은 전체 회수 시퀀스, `Attack01`–`Attack05` unlinked section, 타수별 `ComboInputOpen`/`ComboCommit` point, Ability-local 한 칸 tag buffer, 한 번의 `PlayMontageAndWait`, 고정 Commit에서 `UGameplayAbility::MontageJumpToSection()` 호출이다.
- ASC loose state tag, window Gameplay Event, custom ANS, 전역 input buffer, Combo Manager는 만들지 않는다. Jump에는 자동 cross-fade가 없으므로 authored cut의 pose와 Root Motion 연속성 검증이 완료 gate다.
- 현재 Source는 아직 이전 구조 그대로다. 재개 순서는 Router → Architecture ARCH-43 → Migration의 `P6 브랜치 컷 최종 재검토` → 현재 WeakAttack h/cpp다. 먼저 `KhazanPlayerController.cpp`의 `Engine/LocalPlayer.h` include와 cold build를 확인한 뒤, Montage와 Ability를 한 task 구조로 함께 바꾸고 다시 cold build·PIE 품질 검증을 수행한다.

## 2026-09-18 — P6-v3.1 정확한 재개점

- 현재 Source/Content에는 v3가 아직 적용되지 않았다. 실제 Montage는 Attack01 하나와 Notify 0개이고, 현행 Ability는 존재하지 않는 Attack02와 구 window 이름을 기대한다.
- 먼저 `KhazanPlayerController.cpp`에 `Engine/LocalPlayer.h`를 추가하고 ASC의 deprecated Spec ActivationInfo fallback을 제거한다. 두 single-file compile과 full Development Editor build를 통과하기 전 combo 파일을 바꾸지 않는다.
- 다음으로 Migration의 [P6-v3.1](CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-1-current-checkpoint-20260918)에 따라 WeakAttack 두 Source 파일을 한-task 구조로 교체하고 build한다. 빈 `UKhazanGameplayAbility`는 `GA_GamePlayAbility` asset 정리 전 삭제하지 않는다.
- Editor에서 Attack02 segment/section, `ComboInputOpen`/`ComboCommit` point, `DefaultSlot → Inertialization`을 적용하고 저장한 뒤 PIE의 단발/정상 2타/조기·지연 입력/mash/interruption/Root Motion/locomotion 회귀를 확인한다.
- Source와 Content를 사용자가 적용한 뒤 실제 diff·build·asset 저장값을 다시 대조한다. 이번 턴에는 설명·read-only 검사·build 진단만 수행했다.

## 2026-09-18 — P6-v3.1 2타 미전환 보정 대기

- 현재 상태: Attack01과 Attack02 segment/section, `ComboInputOpen`/`ComboCommit` point는 저장돼 있으나 WeakAttack Source가 첫 타 시작 시 `CurrentComboStepIndex`를 0으로 설정하지 않는다. runtime index가 `-1`인 채 Commit에 들어가 유효 index 검사에서 반환하므로 2타가 실행되지 않는다.
- 정확한 재개: `StartWeakAttackMontage()`에서 task delegate 세 개를 연결한 뒤 `Task->ReadyForActivation()` 전에 `CurrentComboStepIndex = KhazanWeakAttackAbilityPrivate::Attack01Index;`를 추가한다. Montage의 두 point는 Tick Type을 `Queued`에서 `Branching Point`로 바꾼다.
- 적용 후 에디터와 Live Coding을 닫고 Development Editor cold build를 통과한다. PIE에서 한 번 입력은 Attack01 full recovery, Open–Commit 사이 두 번째 입력은 Attack02 Jump, Open 전과 Commit 뒤 입력은 미예약, mash는 한 건만 소비되는지 확인한다.
- 실패가 남으면 다음 debugger 관측점은 ASC `AbilitySpecInputPressed`, Ability `InputPressed`, `SubmitComboInput`의 buffer 대입, `HandleMontageNotifyBegin`, `TryCommitBufferedTransition` 순서다. 이번에는 원인이 정적 제어 흐름에서 결정적으로 드러나 attach를 수행하지 않았다.
- 이번 점검에서 게임 Source와 Content asset은 수정하지 않았다. 저장 asset read-only inspection과 Engineering 문서 append만 수행했다.

## 2026-09-18 — P6-v3.2 적용 대기

- 현재 상태: index 초기화 보정으로 01→02 Jump는 동작한다. 현재 Source는 Commit에서 입력 창을 즉시 닫으므로 Commit 뒤 입력은 버리고, Attack02에는 locomotion recovery handoff가 없어 Root Motion Montage 전체 종료 뒤에야 일반 이동이 보인다.
- 첫 재개는 Migration의 [P6-v3.2](CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-2-three-phase-input-recovery-exit-20260918)다. 먼저 `ComboInputEnd`와 `bComboCommitReached`만 추가해 3상태 콤보를 build/PIE 검증한다.
- 3상태 gate 통과 뒤 `RecoveryCancelOpen`을 Attack02에 먼저 배치하고, 이미 유지 중인 move intent와 point 이후 Move Started semantic event로 early exit를 검증한다. 이동 전환과 Strong/Dodge Ability handoff를 한 번에 구현하지 않는다.
- 현재 디스크 Montage의 Open/Commit은 아직 `Queued`다. 세 combo point와 recovery point는 gameplay 분기이므로 저장 전에 `Branching Point`인지 확인한다.
- 이번 작업은 read-only Source/asset/UE 5.8.2 engine 검사와 문서 append다. 게임 Source와 Content asset, build와 PIE는 변경·실행하지 않았다.

## 2026-09-23 — Art package root 후속 정리 대기

- `_Art/Kazan` → `_Art/Player` 전환을 위해 `Config/DefaultEngine.ini`의 `[CoreRedirects]`에 wildcard `PackageRedirects`를 추가했다. 이전 root가 사라진 뒤에도 저장되지 않은 외부 package 참조를 `/Game/_Art/Player`로 해석하기 위한 호환 경계다.
- `Scripts`에서 이전 `/Game/_Art/Kazan`·`Content/_Art/Kazan` 경로 216곳, 87개 파일을 새 root로 기계적으로 갱신했다. 갱신 뒤 233개 Python 파일 전체를 `ast.parse`로 검사했고 실패는 0이다. `Source`와 `Scripts`에는 이전 경로가 남지 않았고 `Config`에는 redirect의 `OldName` 한 곳만 의도적으로 남아 있다.
- `KZComboAttackAbility.h/.cpp`에는 Art package 경로 literal이 없고 asset 참조는 설정 가능한 property로 연결되므로 수정하지 않았다. 이번 복구에서 gameplay Source 변경은 필요하지 않다.
- 남은 검증은 Unreal Editor 정상 종료 뒤 이전 Content root를 quarantine으로 이동한 상태에서 commandlet을 재실행해 redirect 구문, Asset Registry 이전 참조 0, 대표 package load를 함께 확인하는 것이다. 현재 blocker와 정확한 파일 이동 재개 순서는 `Docs/Art/ART_WORK_CONTINUITY.md`의 2026-09-23 절에 기록했다.
- main push 전 검증에서 233개 Python 파일의 `ast.parse`와 Source/Config/Docs/Scripts staged diff check가 통과했다. UE 5.8.2 Development Editor build는 UHT와 22개 C++ compile action이 모두 성공했고, 실행 중인 PID 8020이 `Binaries/Win64/UnrealEditor-Khazan.dll`을 잠가 최종 link만 `LNK1104`로 중단됐다. 이 결과를 코드 컴파일 실패나 완전한 build 성공으로 확대하지 않는다.

## 2026-09-23 — Player package root 전환 검증 완료

- 이전 Content root 제거 뒤 UE 5.8.2 commandlet에서 Player asset 9,458개, 이전 root asset 0개, 이전 root dependency edge 0개를 확인했다. SkeletalMesh·AnimMontage·HeinMach World·StormPass World 대표 package load와 wildcard Package Redirect load가 모두 성공했다.
- Source/Config/Scripts의 이전 경로는 Core Redirect의 `OldName`을 제외하고 제거됐고, `KZComboAttackAbility`를 포함한 KZ Source는 UHT와 개별 C++ compile action을 통과했다. 최종 DLL link 성공 여부는 에디터가 닫힌 상태의 후속 cold build에서 별도로 확인해야 하며, 앞선 `LNK1104`는 열린 Editor의 DLL lock 결과다.
- 대용량 Git 전송은 Player asset을 여섯 묶음으로 먼저 올린 뒤 코드·설정·이전 root 삭제를 마지막 커밋으로 반영했다. `main`의 최종 트리는 `Content/_Art/Kazan` 0개, `Content/_Art/Player` 9,491개 파일을 가진다.
- 에디터 종료 뒤 `Build.bat KhazanEditor Win64 Development ... -WaitMutex -NoHotReloadFromIDE`를 다시 실행해 `UnrealEditor-Khazan.dll` link와 target metadata 작성까지 `Result: Succeeded`를 확인했다. PIE 플레이 검증은 이번 폴더 복구 범위에 포함하지 않았다.

## 2026-09-23 — StrongCharge 수직 절편 적용 대기

- 목표 동작: Y press에서 Charge 시작, `ChargeReady` 전 정상 release는 `StrongAttack01`, 이후 release는 `StrongChargeAttack`, release 없이 `ChargeEnd`까지 유지해도 `StrongChargeAttack`으로 전환한다. `Canceled`는 공격 edge가 아니다.
- 마지막 정적 확인: `UKZComboAttackAbility`는 command held set과 Open/Commit/End 창, 한 칸 pending, same-Montage section jump를 이미 소유한다. `AuthoredEventEdges`와 node-lifetime immediate command edge는 아직 없다. Strong native class는 빈 migration shim이다.
- 마지막 asset 확인: 별도 UE 5.8.2 read-only commandlet 보고서 `Saved/KZStrongChargeInspect.json`의 내부 status는 `passed`다. Strong Montage는 Attack01–03만 포함하고 길이는 `14.366667 s`; Charge/ChargeAttack sequence는 각각 `1.5 s`와 `5.433333 s`; GA entry는 `StrongAttack01`; Definition에는 charge node가 없다. commandlet 종료 코드 1은 기존 `GameFeatures.GameFeatureData` startup ensure이며 검사 script 실패가 아니다.
- 선행 불일치: 사용자가 Source tag를 `Input.Action.X/Y`, `Command.Player.Attack.X/Y`로 바꿨지만 `DA_InputData`, `DA_CharacterDefinition_Player`, `DA_Player_Combo_Definition`에는 이전 Weak/Strong tag가 저장돼 있다. 세 asset을 새 tag로 재저장하거나 redirect를 적용하기 전에는 입력 Spec과 Combo edge가 일치하지 않는다.
- 정확한 재개 절차: (1) 열린 Editor에서 사용자 변경을 보존해 저장한 뒤 Editor/Live Coding을 종료하고 새 tag Source를 cold build한다. (2) Editor를 다시 열어 위 세 asset의 Input/Command tag를 X/Y로 바꾸고 Weak/Strong 회귀를 확인한다. (3) `KZComboDefinitionData`에 command timing과 authored-event edge를, `KZComboAttackAbility`에 immediate edge 처리·authored edge resolver·same-presentation logical transition을 적용하고 cold build한다. (4) Strong Montage에 Charge/ChargeAttack segment와 section, `ChargeReady=0.600000 s`, `ChargeEnd=1.178113 s` Branching Point를 추가한다. (5) Definition에 `StrongChargeStart`, `StrongChargeReady`, `StrongChargeAttack` node/edge를 만들고 GA entry를 `StrongChargeStart`로 바꾼다.
- PIE 합격 행렬: 0.600 s 전 release→StrongAttack01, 0.600 s 후 release→StrongChargeAttack, 1.178113 s까지 hold→자동 StrongChargeAttack, Canceled→공격 분기 없음, mash 1회 소비, 기존 Strong01→02→03와 Weak01→05 회귀, interruption/EndAbility 후 held·pending·delegate 잔존 0을 확인한다.
- 이번 작업에서 어시스턴트는 게임 Source/Config/Content를 수정하지 않았다. Engineering 문서만 append했고 실제 C++ build와 PIE는 사용자 적용 뒤 검증해야 한다.

## 2026-09-23 — StrongCharge 선행 tag 불일치 해소 및 Spec tag 판정

- 사용자가 에셋을 다시 저장한 뒤 raw on-disk 확인에서 `DA_InputData`, `DA_CharacterDefinition_Player`는 `Input.Action.X/Y`, `DA_Player_Combo_Definition`은 `Command.Player.Attack.X/Y`를 가진다. 바로 앞 절의 Weak/Strong 저장 불일치는 이전 검사 시점 기록이며 현재 해소됐다.
- `GetDynamicSpecSourceTags()`의 InputTag는 granted Spec의 Player 입력 binding으로 유지한다. `Ability.Action.Attack` Asset Tag는 block/cancel/query용 Ability 분류이므로 Y 입력 Spec 검색에 사용하지 않는다.
- StrongCharge의 command timing/authored-event C++ 확장, Montage section/notify, charge node와 GA entry 변경은 아직 적용하지 않았다. 재개는 바로 앞 절의 절차 (3)부터 시작한다.

## 2026-09-23 — StrongCharge 과확장안 철회

- `FKZComboAuthoredEventEdge`, `EKZComboCommandTiming`, same-section logical node를 추가하는 미적용 제안은 철회했다. `HeldCommands`는 지속 여부만 알며 경과 시간을 측정하지 않는다는 누락을 범용 graph 확장으로 덮지 않는다.
- 재개 구현은 (1) ASC가 같은 InputTag 후보 중 활성 Spec 하나 또는 첫 활성화 성공 Spec 하나만 선택하고 실패 Spec의 `InputPressed`를 복구하며 release/cancel도 선택 Spec만 처리, (2) 미사용 `TryActivateAbilityByInputTag()` 제거 여부 확인, (3) 공통 Combo base에 narrow unhandled-notify hook과 node transition 접근만 제공, (4) `UKZStrongAttackAbility`에서 `WaitInputRelease` 및 `Charging/Ready/Resolved` phase로 tap/charged 분기, (5) Montage에 `ChargeReady`와 `ChargeEnd` 두 authored point 추가 순서다.
- `Cancel`은 charge release로 소비하지 않고 활성 Combo Ability를 canceled 종료하여 task/delegate/held/pending을 정리한다. Combo Definition schema는 현재 `FKZComboNode`와 `FKZComboCommandEdge` 그대로 유지한다.
- 이전 proposal diff는 적용 검사만 했으며 게임 Source에 적용된 적이 없다. 수정된 설계를 실제 적용·cold build·PIE한 결과도 아직 없다.

## 2026-09-23 — StrongCharge/StrongAttack 실행 분리 재정정

- 사용자가 `Y Begin`에는 별도 StrongCharge Ability가 실행되고, 최소 charge 전 release에서 기존 StrongAttack Ability가 새로 활성화되는 실행 모델임을 명시했다. 기존 StrongAttack class 안에 charge phase를 넣는 ARCH-61 제안은 철회하고 Architecture ARCH-62로 대체했다.
- 현행 `AbilityInputTagPressed()` 사용자 적용본은 활성 동일 입력 Spec을 처리한 뒤 `return`이 없어 비활성 Y 후보 루프까지 내려갈 수 있다. Pressed는 활성 Spec 처리 직후 반환하고, Released/Canceled는 exact InputTag이면서 `InputPressed == true`인 선택 Spec 하나만 처리한 뒤 반환해야 한다.
- 재개 순서는 ASC 세 입력 함수의 단일 Spec 소유권 완성, Combo base의 `ProcessMontageNotify` 확장점과 protected transition/finish, held Cancel 종료, 새 `UKZStrongChargeAbility`, `GA_Player_StrongCharge`와 Definition/Montage 설정 순이다. 실패 release는 Charge 종료 뒤 exact granted `GA_Player_StrongAttack` class를 활성화하고, 성공 release/timeout은 Charge 실행 안의 `StrongChargeAttack` node로 이동한다.
- 이번 정정에서는 게임 Source/Content를 수정하거나 build/PIE하지 않았다.

## 2026-09-23 — Input Canceled 선택 Spec 종료 보정

- `AbilityInputTagCanceled()`는 선택 Spec의 `InputPressed`를 false로 만든 뒤 활성 상태면 `CancelAbilityHandle()`로 그 Spec만 canceled 종료한다. `InputReleased` replicated event는 보내지 않아 charge release 분기를 깨우지 않는다.
- 공통 Combo base의 기존 `Cancel` command 처리는 held/pending cleanup으로 유지한다. Charge 취소를 위해 모든 Combo 실행을 광범위하게 종료하는 변경은 적용하지 않는다.
- 게임 Source/Content 수정과 build/PIE는 아직 없다.

## 2026-09-23 — Combo hold Edge 구조 재설계 대기

- 사용자 확인으로 `UKZStrongChargeAbility`가 성공/실패를 직접 분기하는 구현은 폐기 대상이 됐다. 모든 Node→Node 전이는 하나의 Combo Edge schema와 공통 runtime으로 처리해야 하며, 별도 authored-event Edge 배열을 만들지 않는다.
- 현행 한계는 Ability-local `HeldCommands`, command 도착 순간에만 수행되는 Edge 검사, 닫힌 window에서 입력 후보를 버리는 처리, same-Montage만 허용하는 `TransitionToNode()`다. 이 때문에 `RequiredHeldCommands`만으로 `WeakAttack01 도중 Y hold → authored 종료 시 StrongCharge`를 표현할 수 없다.
- 정본 계약은 Architecture ARCH-64다. 재개 순서는 (1) ASC에 command held/start-time ledger와 release duration snapshot 추가, (2) 기존 Edge 하나에 Command/HoldThreshold/NodeEvent trigger와 command/node 시간 조건 및 optional target Ability 추가, (3) node event와 hold threshold에서 같은 resolver 호출, (4) cross-Montage node player와 generic Ability handoff 구현, (5) `UKZStrongChargeAbility`의 charge 전용 state/task/notify/hardcoded target 제거, (6) DataAsset Edge 재작성, (7) cold build와 PIE 행렬 검증이다.
- 필요한 데이터 예시는 WeakAttack01 node event + RequiredHeld Y → GA_Player_StrongCharge/StrongCharge, StrongCharge의 early Y Release → GA_Player_StrongAttack/StrongAttack01, ready Y Release → StrongChargeAttack, held timeout → StrongChargeAttack이다.
- 이번 정정에서는 게임 Source/Content를 수정하지 않았고 build/PIE도 수행하지 않았다.

## 2026-09-23 — 최소 InputEnd/Combo Edge 계약으로 재정리

- ARCH-64의 범용 trigger/min-max/duration-origin/target-Ability 프로퍼티 제안은 과도하여 Architecture ARCH-65로 대체했다.
- 공통 `UKZActionAbility`는 `bInputEnded` 하나로 모든 주요 Montage Action의 교체 가능 시점을 연다. 기존 Combo의 `bCanExitToLocomotion`을 대체하고, `ComboInputOpen/ComboCommit`은 Combo 전용으로 유지하며 `ComboInputEnd`는 공통 `InputEnd`로 바꾼다.
- 기존 Edge는 현재 다섯 필드를 유지하고 `CommandPhase`의 Hold/InputEnd, `HoldTime`, Begin 순간 `Move(Any/Stand/Walk/Run/Sprint)`만 추가한다. 시간은 항상 current node 안에서 command가 연속 held였던 시간 하나로 계산하고 Edge 배열의 첫 일치 항목을 소비한다.
- ASC runtime state는 `CommandTag -> {BeginTime, Move}` map 하나다. Combo Ability에는 node enter time과 다음 Hold edge timer만 추가하고 Ability-local `HeldCommands` 및 StrongCharge 전용 state/task/notify/hardcoded handoff는 제거한다.
- target Ability 필드는 추가하지 않는다. target node가 다른 granted Combo Ability의 고유 EntryNodeId이면 공통 handoff하고, 아니면 현재 Ability 안에서 전환한다.
- Monster는 별도 hold/Combo 기반을 선행 생성하지 않는다. Player 입력 adapter와 Monster AI 결정은 분리하되 공통 Action Ability의 InputEnd/Montage/GAS 수명은 공유한다.
- 게임 Source/Content 수정, build와 PIE는 아직 수행하지 않았다.

## 2026-09-24 — Move/Hold/Release 계약 보정

- Architecture ARCH-66이 ARCH-65의 Begin 시점 Move snapshot을 폐기했다. Edge의 Move는 검사 순간 `LocomotionIntent.InputAmount`와 `RequestedGait`에서 읽으며, ASC에는 `CommandTag -> BeginTime`만 저장한다.
- Hold는 매 frame 전달되는 입력이나 bool이 아니라 Edge의 HoldTime에 예약한 timer 사건이다. HoldTime은 실시간 누적 멤버가 아니며 Release/Hold/InputEnd에서 `Now - max(BeginTime, NodeEnterTime)`으로 계산한다.
- Enhanced Input `Completed`가 Release를 명시한다. Release는 계산한 HeldTime을 일회성 command 값으로 넘기고 held map을 정리한다. `Canceled`는 map만 정리하고 Release Edge를 실행하지 않는다.
- StrongCharge는 ready 이상 Release, 0초 Release fallback, max-time Hold의 세 Edge로 early release/charged release/held timeout을 구분한다. InputEnd는 release가 아니라 Montage의 교체 및 held handoff 경계다.
- 이번 보정에서도 게임 Source/Content를 수정하거나 build/PIE하지 않았다.

## 2026-09-24 — Montage Notify 기반 Hold 계약으로 단순화

- Architecture ARCH-67이 ARCH-65/66의 HoldTime, BeginTime, NodeEnterTime, hold timer와 transient HeldTime을 폐기했다. 현재 StrongCharge는 node 진입부터 Y held를 보장하므로 Montage authored 경계가 충분하다.
- 인식할 Notify 역할은 `InputOpen`, `InputCommit`, `InputEnd`, `HoldCommit`, `HoldEnd` 다섯 종류다. Input의 buffer 시간축과 Hold의 charge 시간축은 독립이며, 각 section은 필요한 Notify만 가진다.
- ASC에는 held CommandTag set만 남기고 활성 Combo node에는 `bHoldCommitted` 하나만 둔다. HoldCommit 전/후 Release Edge와 held 상태의 HoldEnd Edge를 같은 resolver에서 처리한다.
- StrongCharge Edge는 Y/Release+BeforeCommit→StrongAttack01, Y/Release+AfterCommit→StrongChargeAttack, Y/HoldEnd+AfterCommit→StrongChargeAttack이다. InputEnd/HoldEnd 사건은 현재 held command만 생성하므로 같은 command를 RequiredHeldCommands에 중복 작성하지 않는다.
- 시간 측정은 미래에 node 중간의 늦은 Begin부터 command별 실제 경과 시간을 요구할 때만 다시 도입한다. 이번 검토에서는 게임 Source/Content를 수정하거나 build/PIE하지 않았다.

## 2026-09-24 — Notify Hold Edge 사용자 구현 절차 작성

- Migration의 P6-D3 절에 현재 Source에서 ARCH-67로 이관하는 네 checkpoint를 기록했다: 값 타입/ASC/Controller, Action InputEnd/Combo resolver, 공통 node·Ability handoff, StrongCharge 하드코딩 제거/asset 작성이다.
- 현재 저장 `AM_DAS_StrongChargeAttack`에는 `ChargeReady`, `ChargeEnd`, `ComboInputEnd`가 있고 Definition에는 `StrongCharge`, `StrongChargeAttack` node가 있음을 raw asset 문자열로 표적 확인했다. 새 asset 생성 대신 같은 authored frame의 역할 이름을 이관한다.
- 구현상 핵심 보정은 Begin만 input buffer를 사용하고 Release/Notify event는 즉시 resolver로 보내는 것, held set을 ASC에 두는 것, InputEnd handoff 전에 action block을 여는 것이다.
- 이번 작업에서는 설명 문서만 append했다. 게임 Source/Content, build와 PIE는 사용자가 각 checkpoint를 적용한 뒤 검증해야 한다.
- 현재 grant 선택은 `StrongCharge=Input.Action.Y`, `StrongAttack=InputTag 없음`으로 고정했다. idle Y는 StrongCharge 하나만 시작하고 StrongAttack은 Release Edge handoff로만 활성화한다.

## 2026-09-26 — Notify Hold Edge 사용자 적용본 전수 점검

- P6-D3 사용자 적용본은 아직 중간 이관 상태다. `HasComboEntry()`는 본문과 반환이 없고 `TryActivateComboEntry()`는 찾지 않은 `TargetSpec`을 사용한다. Combo 쪽에는 제거된 `HeldCommands`, `bCanExitToLocomotion` 참조와 선언·정의되지 않은 `RunHeld()` 호출이 남아 있다.
- 2026-09-26 UE 5.8 `KhazanEditor Win64 Development` cold build는 위 항목에서 컴파일 오류 10개로 실패했다. `KZActionAbility`, Controller, Character와 값 타입 자체의 compile action은 통과했지만 전체 build 성공은 아니다.
- 컴파일 오류 뒤의 동작 누락도 확인했다. Edge 검색이 `Hold`와 `Move`를 호출하지 않고, pending tag를 지운 뒤 실행하며, local node 전환에서 `bHoldCommitted`와 `InputEnd`를 reset하지 않는다. ASC Release는 선택 Spec 종료 뒤 다음 후보로 계속 진행하고, Cancel은 `InputPressed` 소유권을 검사하지 않는다. active 동일 Spec의 InputEnd 이후 재입력과 local cross-Montage 재생도 아직 없다.
- 저장 Content는 새 계약으로 이관되지 않았다. Character Definition에는 StrongCharge와 StrongAttack이 모두 `Input.Action.Y`로 남아 있고, StrongCharge Montage는 `ChargeReady/ChargeEnd/ComboInputEnd`, 일반 공격 Montage는 `ComboInputOpen/ComboCommit/ComboInputEnd`를 사용한다. Definition에는 새 `Hold/Move` 값과 StrongCharge 세 Edge가 저장되지 않았다.
- 현재 Combo Source에는 적중 판정이나 피해 GameplayEffect 적용 경로가 없다. `StrongChargeAttack`을 별도 node로 고르는 것까지가 이번 graph 범위이며, 일반 StrongAttack과 다른 피해값은 이후 Combat 실행 데이터에서 node별로 연결해야 한다. Edge에 피해 수치를 섞지 않는다.
- 이번 점검에서 게임 동작 로직과 Content는 수정하지 않았다. `KZComboTypes`, Definition, ASC, Action, Combo, Controller와 빈 StrongCharge wrapper에 역할을 설명하는 쉬운 주석만 추가했다.
- 재개 순서는 ASC 단일 Spec 소유권과 Combo Entry 검색 완성 → 공통 Edge 조건/held Notify resolver와 node reset 완성 → same/cross Montage 전환 완성 → cold build → Editor에서 grant·Definition·Notify 이관/저장 → Blueprint compile → PIE 검증 행렬이다.

## 2026-09-27 — Cancel pending·같은 Spec 재입력·held Notify 설명 보정

- Cancel에서 `PendingCommandTag == canceled CommandTag` 검사는 취소된 trigger 자체를 버린다. Begin Edge는 trigger command 자체의 held 여부를 요구하지 않으므로 일반 `FindMatchingCommandEdge()` 재검사만으로는 이 경우를 잡지 못한다. 아래 재검사는 별도의 canceled command가 pending Edge의 `RequiredHeldCommands`를 깨뜨린 경우를 처리한다.
- 같은 InputTag/같은 active Action Spec의 재입력은 `InputEnd` 전에는 기존 generic press와 Combo Begin으로 처리하고, `InputEnd` 뒤에는 기존 실행을 취소한 다음 같은 Spec Handle을 다시 활성화한다. 실패해도 다른 동일 InputTag 후보로 한 press를 넘기지 않는다.
- `RunHeld()`는 CommandTag가 없는 `InputEnd/HoldCommit/HoldEnd` Montage 사건을 ASC held set과 현재 node의 Edge 배열로 결합한다. held tag 순회가 아니라 Edge 배열 순서로 검사해 authored 우선순위를 유지하며, 첫 성공 전이 뒤 즉시 반환한다.
- 이번 보정은 설명과 production comment만 갱신했다. `RunHeld()` 본문과 ASC 재입력 분기는 아직 사용자 구현 대상이며 build/PIE 완료로 기록하지 않는다.

## 2026-09-27 — P6-D3 사용자 구현 완료 확인과 재개 지점

- 앞 절의 “`RunHeld()`와 재입력 미구현” 상태는 이후 사용자 구현으로 해소됐다. 현재 Source에는 ASC 선택 Spec 소유권, 같은 Spec InputEnd 뒤 재활성화, held Notify resolver, Hold/Move/held/tag Edge 조건, Entry Ability handoff와 node reset이 들어 있다.
- 최신 PIE 로그는 WeakAttack01→02→03→04, StrongAttack01→02→03, StrongCharge→StrongChargeAttack을 기록했고 해당 PIE 세션은 Combo 오류 없이 종료됐다. 사용자는 콤보 시스템 동작 완료를 확인했다.
- `KhazanEditor Win64 Development` UBT는 성공하며 target은 up-to-date였다. 최신 module DLL 생성 시각은 최신 ASC/Combo Source보다 뒤다.
- 남은 P6 제한은 같은 Ability 안의 cross-Montage node 전환 거부, `NonRun/Run`만 있는 Move 분류, Combo Definition/Notify의 편집 시점 validation 부재다. 현재 Player graph 동작을 막지는 않으므로 실제 소비 없이 새 구조를 추가하지 않는다.
- 전체 아키텍처는 미완료다. 다음 재개는 Router → Architecture의 2026-09-27 적용 감사 → Migration의 2026-09-27 P6-D3 상태를 읽고, P2 최소 Stamina/WeakAttack Cost 한 경로부터 시작한다. 그 뒤 P3 WeakAttack01 hit window→damage→HitReact→Death→Cue를 한 단계씩 구현한다.
- StrongCharge/StrongAttack handoff는 서로 다른 Ability activation을 만들고 각 activation이 현재 `CommitAbility()`를 호출한다. 비용을 추가할 때 원작의 비용 단위가 확인되기 전 양쪽 Ability에 같은 Cost를 복제하지 않는다.

## 2026-09-27 — Stamina·LockOn·Dodge 계획 뒤 재개 지점

- 사용자 새 우선순위는 `Stamina/Cost → LockOn Walk·Run 8방 → Dodge → P3 hit/damage`다. Architecture ARCH-68, Migration의 같은 날짜 구현 순서, Animation 정본의 후보 감사부터 읽는다.
- 실제 게임 Source/Content에는 아직 세 기능을 적용하지 않았다. 이번 변경은 설명 준비, read-only asset 검사와 문서 기록뿐이다.
- 재개 1: `UKZAttributeSet`의 Stamina/MaxStamina 등록 → 초기 Instant GE → WeakAttack Cost GE → 부족/경계값 검증. Strong/Charge Cost는 보류한다.
- 재개 2: Player가 외부 target과 한 movement constraint handle을 소유하는 최소 LockOn 진입/해제 → target yaw → Walk/Run 1D Blend Space와 ABP 전이 → cleanup을 검증한다.
- 재개 3: `UKZActionAbility`의 공통 InputEnd notify bind/filter를 두 번째 소비자인 Dodge에 맞게 이관한 뒤 기존 Combo 회귀를 먼저 실행한다. 그 다음 InGame에 복제한 M1 8방 시퀀스로 Dodge Montage/Ability/Input/Cost를 연결한다.
- 마지막 gate는 Player mesh scale 0.009 아래의 local/world root-motion delta와 capsule 변위다. 애니메이션 translation을 component scale의 역수로 보정하지 않는다.

## 2026-09-29 — LockOn L1 상세 설명 재개 지점

- 사용자 보고상 P2-C Stamina regen Effect 작성은 끝났다. 정적으로 관련 AttributeSet/태그/Effect asset 존재만 확인했으며 새 build와 PIE 검증은 하지 않았다.
- 현재 `KZPlayer.cpp`의 `StartLockOn`, `StopLockOn`, `UpdateLockOnFacing`, `IsLockedOn`은 골격 상태다. `StartLockOn`과 `IsLockedOn`에는 반환문도 아직 없다. `Tick`은 빈 override이고 `UnPossessed`는 LockOn handle을 회수하지 않는다.
- 재개 1: `StartLockOn`에서 target·동일 world·Locomotion 유효성을 검사하고, 부분 상태를 정리한 뒤 Run 상한/LockOn 회전 constraint를 `this` source로 한 번 취득한다. 이미 정상 LockOn이면 handle을 재발급하지 않고 target만 교체한다.
- 재개 2: `UpdateLockOnFacing`은 target/handle/Controller가 하나라도 무효면 `StopLockOn`으로 정리한다. 유효하면 target-player 벡터의 Z를 제거하고, 0벡터가 아닐 때 Controller의 기존 Pitch/Roll을 보존한 채 Yaw만 target 방향으로 쓴다.
- 재개 3: `Tick`에서 target 또는 handle 상태가 남아 있을 때 facing을 갱신하고, `UnPossessed`에서 intent source 종료 전에 `StopLockOn`을 호출한다. `StopLockOn`은 자기 handle 한 건만 LocomotionComponent에 반환하고 target을 reset한다.
- 재개 4: L1 build/PIE에서 Run 상한, 전후좌우 이동 중 target facing, target Destroy, 반복 Stop, UnPossess, 다른 gait/rotation constraint 공존을 확인한다. 통과 뒤 L2 Blend Space/ABP로 간다.
- 설명 작업에서 게임 파일을 직접 고치지 않았다.

## 2026-09-29 — LockOn 획득·anchor·camera 개정 후 재개점

### 현재 상태

- 저장 `KZPlayer.cpp`에는 외부 actor를 받는 `StartLockOn`, target/constraint, 평면 yaw 즉시 갱신이 구현돼 있다. 새 ARCH-69의 화면 검색·Monster anchor·camera pitch/보간·toggle input은 아직 적용되지 않았다.
- `AKZMonster`는 현재 빈 기반에 가깝고 `LockOnTargetPoint`가 없다. Input GameplayTag, InputAction, IMC/DA_InputData 항목과 Controller bind도 없다.
- 사용자는 Stamina 재생 GameplayEffect를 완료했다고 보고했다. 이번 LockOn 감사에서 별도 runtime 확인은 하지 않았다.

### 마지막 검증

- 현재 C++를 읽어 target Z를 Player Z로 덮어쓰는 코드, Yaw 즉시 SetControlRotation, UnPossess cleanup과 constraint 소유를 확인했다.
- 원작 인간형/Yetuga/Apes/WildDog/WildBoar metadata에서 `xxLockOnSphereComponent`와 다수의 `bUseRotToTargetLockOnSphereLocation=true`를 확인했다.
- UE 5.8 read-only 검사에서 Yetuga 7, Apes 7, WildDog 5, WildBoar 9, BigBear 0개의 현재 mesh socket을 확인했으며 공통 LockOn socket은 없었다. `BP_Player` SpringArm의 Pawn Control Rotation=true, rotation lag=false도 확인했다.
- 검사 Python은 정상 완료했다. commandlet 종료 코드 1은 기존 `/Script/GameFeatures.GameFeatureData` ensure이며 asset은 저장하지 않았다.

### 남은 작업과 정확한 재개 순서

1. `AKZMonster`에 capsule/root 부착 `LockOnTargetPoint` SceneComponent와 world-location getter를 추가한다. gameplay Monster BP별 위치는 현재 capsule/mesh transform을 확인해 설정하고 원본 raw 위치를 무검증 복사하지 않는다.
2. Player에 `UKZTargetingComponent`를 만들고 target weak reference, movement constraint handle, `Toggle/TryStart/Stop`, tick enable/disable와 EndPlay cleanup을 옮긴다. 기존 Player의 중복 target/handle은 이관 뒤 제거한다.
3. 첫 입력에서만 활성 `AKZMonster`를 순회하고 actual view forward, viewport projection/bounds, Visibility trace, normalized center score 순으로 한 대상을 고른다.
4. `Input.Action.LockOn`, InputAction, IMC mapping, DA_InputData entry와 Controller Started bind를 추가한다. 실제 물리 키는 사용자가 선택한 mapping을 사용한다.
5. full 3D target point로 camera LookAt을 만들고 `LockOnViewInterpSpeed` 한 설정값으로 `RInterpTo`한다. 임시 시작값 `12.0 1/s`를 원작 미확인 값으로 표시한다. Lock 중 `Input_TurnCamera`는 무시한다.
6. build 후 PIE에서 중앙/좌우/상하 높이 차, 벽 뒤 후보 제외, 후보 없음, 두 번째 입력 해제, target Destroy, UnPossess, Stop 뒤 camera 입력과 constraint 잔존 0을 확인한다.
7. L1이 닫힌 뒤 기존 L2 Walk/Run 8방 Blend Space와 ABP 선택을 연결한다.

## 2026-09-29 — LockOn Targeting 사용자 적용 순서 확정

- 이번 공동 구현 설명의 적용 순서는 `AKZMonster` anchor → 새 `UKZTargetingComponent` → `AKZPlayer` 조립/기존 직접 소유 제거 → GameplayTag와 `AKZPlayerController` Started toggle → `IA_LockOn`/`IMC_Default`/`DA_InputData` → gameplay Monster BP별 anchor 위치 → cold build/PIE 검증이다.
- `UKZLocomotionComponent`의 공개 제약 API와 `EKZRotationMode::LockOn` 적용 경로는 그대로 소비한다. Target, camera view, screen projection, visibility trace를 LocomotionComponent에 추가하지 않는다.
- TargetingComponent는 비잠금 상태에서 tick하지 않는다. 첫 Started에서만 `AKZMonster`를 순회하며, 잠금 뒤 tick은 target validity와 full 3D camera LookAt 보간만 담당한다. 순간적인 화면 이탈이나 가림은 이번 단계의 자동 해제 원인이 아니다.
- `AKZPlayer`의 현 `StartLockOn(AActor*)`, `UpdateLockOnFacing()`, `LockOnTarget`, `LockOnConstraintHandle`은 Component 이관 뒤 제거한다. Player에는 `ToggleLockOn/StopLockOn/IsLockedOn`의 얇은 전달과 native component 조립만 남긴다.
- 에디터 입력 설정은 native `Input.Action.LockOn`이 로드된 cold build 뒤 진행한다. 물리 키는 사용자 매핑 결정이며, Action은 Boolean, Controller bind는 `Started` 한 번이다.
- `LockOnViewInterpSpeed=12.0 1/s`는 원작 미확인 임시값이다. 기존 CharacterDefinition의 yaw `RotationRate=540 deg/s`와 역할이 다르며 두 값 모두 실제 PIE 회전 감각과 frame-rate 변화에서 별도로 확인한다.
- 이번 절은 적용 순서와 책임을 기록한 것이다. 게임 Source/Content는 수정하지 않았고 새 build/PIE 결과도 없다.

## 2026-09-29 — `KZLockOnComponent` 부분 적용과 최신 빌드 실패 재개점

### 현재 상태

- `AKZMonster`에는 capsule에 부착된 `LockOnTargetPoint`와 const getter가 실제 Source에 추가됐다.
- 새 `UKZLockOnComponent`에는 기본 비활성 component tick, toggle 진입, 활성 `AKZMonster` 순회, actual camera view 전방 검사, viewport 투영/경계, Visibility trace, 정규화 화면 중심 점수와 camera 거리 tie-break가 작성됐다.
- `LockOnViewInterpSpeed=12.0 1/s`는 원작 미확인 임시 튜닝값으로 선언됐다.
- `StopLockOn()`, `IsLockedOn()`, `StartLockOn()`, `UpdateLockOnFacing()` 본문은 아직 비어 있다. 새 Component도 `AKZPlayer`에 조립되지 않았고 기존 Player의 직접 target/constraint 소유 구현이 남아 있다.
- `Input.Action.LockOn`, InputAction, IMC/DA_InputData row와 Controller `Started` bind는 아직 없다.
- GAS 쪽 현재 경계는 유지된다. Action/Combo Ability, exact InputTag 단일 Spec, held command, Move `GameplayEvent`→`WaitGameplayEvent`, 다섯 Montage Notify와 Block/Delay/Ability 태그는 기존 검증 상태이며 LockOn 입력 수명과 합치지 않는다.

### 마지막 검증과 실패 원인

- 2026-09-29 22:14 `KhazanEditor Win64 Development`에서 UHT는 성공했다.
- C++ compile은 `KZLockOnComponent.cpp`의 `IsLockedOn()`과 `StartLockOn()`이 bool 값을 반환하지 않아 C4716 두 건으로 실패했다. 최종 결과는 `Result: Failed (OtherCompilationError)`다.
- 마지막 module DLL은 21:28 생성본이고 `KZLockOnComponent.cpp` 최종 저장 시각 22:11보다 오래됐다. 따라서 신규 Component가 실행 모듈에 반영됐거나 PIE에서 검증됐다고 기록하지 않는다.

### 정확한 재개 순서

1. `StopLockOn()`에 자기 movement constraint handle 반환, target/handle reset, tick disable을 구현한다.
2. `IsLockedOn()`의 target+handle 동시 유효성 반환과 `StartLockOn()`의 owner/target/world/Locomotion 검증, 부분 상태 cleanup, Run 상한·LockOn rotation constraint 취득, target 저장, tick enable을 구현한다.
3. `UpdateLockOnFacing()`에서 invalid 상태를 `StopLockOn()`으로 정리하고 Monster anchor full 3D LookAt을 `RInterpTo`로 Controller rotation에 출력한다.
4. cold build를 먼저 통과시킨 뒤 `AKZPlayer`에 Component를 조립하고 기존 직접 LockOn 필드/함수를 제거해 단일 소유권으로 이관한다.
5. `Input.Action.LockOn`과 InputAction/IMC/DA_InputData/Controller toggle을 연결하고 Lock 중 manual camera turn 차단을 적용한다.
6. 다시 cold build한 뒤 중앙·가장자리·뒤쪽·벽 뒤·높이 차·후보 없음·두 번째 toggle·target Destroy·UnPossess·EndPlay·constraint 공존을 PIE에서 확인한다.
7. L1이 닫힌 뒤 기존 `RotationMode`와 `MovementDirectionAngle`을 소비하는 LockOn Walk/Run 8방으로 진행한다.

## 2026-09-30 — LockOn 8방 L2 사용자 적용 재개 지점

- 현재 `UKZLockOnComponent::StartLockOn()`은 Run 상한과 `EKZRotationMode::LockOn` constraint를 취득한다. AnimInstance에는 이미 `RotationMode`, `LocomotionGait`, `MovementDirectionAngle`이 있으므로 L2를 위해 C++ 멤버를 추가하지 않는다.
- 사용자가 만든 `BS_DAS_Player_LockOn_Run` 저장본은 sample 0개의 2D `BlendSpace`다. 첫 재개 작업은 이를 보존 이름으로 옮기거나 제거한 뒤 `SK_Player`용 `BlendSpace 1D`로 다시 만들고, Walk 폴더에도 `BS_DAS_Player_LockOn_Walk` 1D를 만드는 것이다.
- 두 에셋의 Direction 축은 `-180..180`, Grid 8, Wrap/Snap 활성이다. Back을 -180/+180에 중복하고 나머지 7방을 45도 간격으로 배치한다. angle smoothing/weight smoothing은 정확성 검증 동안 0, sample Rate Scale은 1.0이다. 세부 파일 대응은 Animation 정본의 2026-09-30 절을 따른다.
- 다음으로 `ABP_Player → AnimGraph → Locomotion → Grounded → GroundedLocomotion → WalkRun`에서 기존 normal Walk/Run gait-select를 보존한다. 별도 LockOn Walk/Run gait-select를 만들고 두 결과를 최종 `Blend Poses by Bool`에 연결한다. `RotationMode == LockOn`이 True, normal이 False다. Bool blend는 현행 WalkRun 저장 설정 `0.10 s / Hermite Cubic / Standard Blend`를 우선 복제한다.
- 새 Blend Space Player 둘은 `Direction=MovementDirectionAngle`, Loop true, Sync Method `Sync Group`, Group `Locomotion`, Role `Can Be Leader`로 둔다. Idle/Stop/Sprint/Airborne state와 기존 전이는 바꾸지 않는다.
- 적용 뒤 Compile/Save 후 PIE에서 LockOn on/off를 정지·Walk·Run 각각 시험하고 F/FR/R/BR/B/BL/L/FL, ±180 경계, target 선회 중 방향, 입력 해제 Stop, LockOn 중 Sprint 차단, target 소멸 cleanup을 확인한다. Anim Debug에서 `RotationMode`, `LocomotionGait`, `MovementDirectionAngle`을 함께 본다.
- LockOn Walk 8개에는 좌우 발 marker가 있지만 Run 8개에는 marker가 없다. Run의 발 pop이 확인될 때만 실제 접지 frame을 찾아 marker를 추가한다. 임의 시간을 넣거나 Walk marker 시간을 그대로 복사하지 않는다.
- 이번 감사 산출물은 `Saved/ImportReports/KZ_LockOnLocomotion_ReadOnly_20260930.json`이다. 게임 Source/Content/ABP는 수정하지 않았고 build/PIE도 실행하지 않았다.

## 2026-09-30 — LockOn Pitch 제한 적용 후 런타임 검증 재개점

- 현재 `KZLockOnComponent.h/.cpp`에 거리 대신 각도 기준의 LockOn 내려다보기 제한이 적용돼 있다. `MaxLookDownAngleDegrees=20°`는 원작 미확인 임시 튜닝값이며 `BP_Player`의 inherited component defaults에서 조절할 수 있다. 기존 Player pivot `+250 cm`는 보존했다.
- 마지막 검증: UE 5.8 Editor target의 UHT 및 변경 C++ compile 성공, Editor DLL link는 실행 중인 Unreal Editor의 점유 때문에 `LNK1104` 실패. Game target도 변경 C++ compile 성공, 전체 build는 변경하지 않은 `KZLocomotionComponent.cpp:8`의 `InterchangeResult.h` 누락 `C1083`으로 실패. PIE는 수행하지 못했다.
- 재개 1: 사용자 작업을 저장한 뒤 Unreal Editor를 정상 종료한다. `Build.bat KhazanEditor Win64 Development -Project=<Khazan.uproject 절대 경로> -WaitMutex -NoHotReloadFromIDE`로 Editor target을 다시 빌드한다. Game target의 기존 `InterchangeResult.h` 문제는 별도 빌드 범위에서 해결한다.
- 재개 2: 새 Editor 프로세스로 `BP_Player`의 `LockOnComponent > MaxLookDownAngleDegrees` 설정을 확인한다. PIE에서 같은 높이 적을 근거리·원거리에서 잠그고 Controller/Camera Pitch가 음수 `-20°` 아래로 내려가지 않는지, SpringArm의 과도한 상승이 사라졌는지 확인한다. 높은 곳의 target은 양수 Pitch로 올려다볼 수 있어야 한다. LockOn 해제 뒤 일반 camera 입력도 확인한다.
- 재개 3: 카메라 높이와 framing이 원하는 정도와 다르면 이 임시 각도를 component defaults에서 조절하고, target anchor/BP SpringArm offset·collision의 별도 영향을 확인한다. 원작 카메라 Pitch metadata가 확보되면 같은 의미·조건인지 확인한 후 임시값 교체를 판단한다.

## 2026-09-30 — Dodge/DodgeAttack 공동 구현 설계 후 재개점

- 현재 상태: ARCH-71과 Migration D4에 8방 Dodge Ability, LockOn/비잠금 방향 선택, 기존 Combo Edge 재사용, 해금형 DodgeAttack handoff 및 최소 공통 Combo Action base 이관을 **제안**했다. Source/Content 적용은 없다.
- 마지막 검증: `KZComboAttackAbility`, `KZAbilitySystemComponent`, Controller, CharacterDefinition, LockOn/Locomotion 현행 Source와 InGame Dodge/DodgeAttack 파일 존재를 정적으로 확인했다. Dodge M1 8방의 기존 저장 감사만 이용했다. DodgeAttack Sequence의 Root Motion/Notify/원작 대각선 규칙, 새 Cost/해금 progression과 실제 PIE는 확인하지 않았다. 이번 설계로 build/PIE는 실행하지 않았다.
- 남은 결정: 현재 DodgeAttack motion은 F/B/L/R 네 방향만 확인되므로, 대각선 Dodge의 공격을 이 네 공격 중 어디에 연결할지 또는 8개 공격 Ability를 만들지 확정해야 한다. 문서의 첫 임시 후보는 FR/FL→F, BR/BL→B이며 원작 근거가 없다. `Unlock.Skill.DAS.DodgeAttack`을 실제로 부여할 Progression/Save producer도 아직 없다.
- 정확한 재개: Migration D4의 1단계 DataAsset 검증과 해당 Sequence 표적 검사 → 공통 Combo Action 추출 후 기존 Weak/Strong/Charge 회귀 → 방향별 Dodge Spec 선택과 IA_Dodge 연결 → Montage/Cost/8방 PIE → DodgeAttack Edge·unlock on/off·X/Y 입력 순서 회귀 순서로 진행한다. 기존 사용자 작업과 미저장 BP를 보존하며 에디터 종료가 필요한 cold build는 저장·정상 종료 후 수행한다.

## 2026-10-01 — Dodge 초기 타입 반영 후 Weak/Strong 해금형 Combo 재개점

- 현재 상태: 사용자가 UKZDodgeAbility native skeleton, A/Dodge tags와 8개 방향 BP를 생성했다. ctor 외에 실행/방향/Combo 기능은 아직 없다. 설명 요청에 따라 이번 턴은 게임 파일을 편집하지 않고 ARCH-72와 Migration D4 후속 절차를 추가했다.
- 마지막 검증: 현재 Source, 8개 BP의 UKZDodgeAbility 상속, 표적 InGame sequence/입력/Ability asset 존재를 읽기 전용 확인했다. 기존 저장 UBT 2026-10-01 10:29 Live Coding 성공과 8 BP compile 로그를 확인했다. 새 cold build/PIE는 수행하지 않았다. Rider F/R BP property 조회 빈 결과는 전체 BP 내용 검증이 아니다.
- 남은 사유: 공통 Combo base, 방향 선택/ASC dispatch, IA_Dodge/IMC/DA_InputData, Montage/graph/Cost/notify, X/Y 소비 중재, 특수 공격/해금 producer와 실행 cleanup이 연결되지 않아 제품 Dodge/특수 공격은 미완료다. 두 특수 가족의 원작 모션 대응/대각선 매핑/비용/창 frame과 해금 전 기본 회피공격 유무도 미확인이다.
- 정확한 재개 1: 현행 UKZComboAttackAbility 실행 부분을 UKZComboActionAbility로 이관하고 Attack wrapper/기존 BP 경로를 보존한다. Dodge parent와 ASC entry cast를 공통 base로 연결하고 graph/entry 사전 검증 및 local Cost 실패 전환을 보완한다. 저장·Editor 정상 종료 후 cold build와 기존 X/Y/Charge 회귀를 먼저 닫는다.
- 정확한 재개 2: 현재 Input.Action.A와 8개 BP 이름을 사용해 방향 enum/defaults·현재 Move action read·Player const 계산·ASC 방향 선택을 구현한다. IA_Dodge Started, shared DA_Player_Combo_Definition의 8 Dodge node, AM_DAS_Dodge/Next=None/Branching Point Notify와 8 graph-only grant/비용을 연결한다.
- 정확한 재개 3: SubmitComboCommand 소비 반환/Begin command 선행/generic activation·same-spec restart gate/graph-only InputPressed 보정을 구현한다. Dodge_F의 X→DodgeWeakAttack_F, Y→DodgeStrongAttack_F 두 Entry와 별도 Unlock.Skill.DAS.DodgeAttack.Weak/Strong 태그를 시험한 뒤 확인된 방향 데이터로 확장한다. 특수 target의 ActivationRequiredTags와 처음부터 granted spec을 함께 유지한다.
- 정확한 재개 4: 미해금/Weak만/Strong만/둘 다, 입력창/비용 실패/일반 fallback, 방향·벽·경사·LockOn yaw, 재입력/regen delay와 UnPossessed Action cancel/Stop PIE 무잔존을 확인한다. Save/해금 producer 및 P3 무적/피해 연동은 구현·검증된 범위만 완료 처리한다.
- 주의할 기존 결과: TryActivate true가 target Commit/몽타주 완료를 뜻하지 않는다. 기존 Source는 local Cost 실패 뒤에도 section jump를 실행하므로 최신 문서의 gate 보완이 실제 적용됐는지 확인한다. 게임 파일과 기존 사용자의 작업은 문서에 맞춰 임의 복원하지 않는다.

## 2026-10-01 — 공통 Combo Action 부분 적용 이후 상세 코드 설명 재개점

- 현재 상태: 사용자 Source에 UKZComboActionAbility 실행/h 상태가 이미 옮겨졌고 Attack/Dodge 파생 ctor와 ASC entry cast도 새 상속을 사용한다. 앞선 "추출부터 시작" 기록을 그대로 반복 적용하지 않는다.
- 마지막 검증: 해당 h/cpp, Action base/ASC/Controller/Definition을 읽고 설치 UE 5.8 CanActivate/PreActivate/Cost/EndAbility/Task API를 대조했다. 게임 Source/BP/Content를 수정하거나 새 cold build/PIE를 실행하지 않았다.
- 남은 원인: CanActivate는 아직 공통 base에 override되지 않았고 local Cost 실패가 jump를 막지 않는다. 전체 코드 보완안은 Docs/Engineering/Examples/ComboAction_20261001/KZComboActionAbility.h.txt와 .cpp.txt에 있다. 해당 파일은 제안이며 Source 적용 증거가 아니다.
- 정확한 재개 1: 사용자가 header CanActivate 선언/cpp 정의를 추가하고 TransitionToNode를 보완안과 비교해 Cost gate를 state 변경 전에 둔다. 기존 local node마다 ApplyCost 정책과 shared OwnedTags/Attack·Dodge AssetTags 경계를 유지한다. 이후 저장/Editor 정상 종료/cold build/새 Editor BP Compile·Save/기존 X·Y·Charge 비용·Notify·자연 종료·이동 복귀·interrupt 회귀를 수행한다.
- 정확한 재개 2: Source와 첨부가 다른지 다시 확인하고 bConsumed 전체 입력 경로, graph-only InputPressed, editor Definition validation 및 UnPossessed Action 취소를 별도 실제 적용 단위로 닫는다. 그 뒤 기존 A 태그/8 BP로 Dodge 방향 선택과 Montage/entry grant/Cost/특수 Weak·Strong 해금 Edge를 연결한다.
- 주의: CommitPendingCommand는 실행 전에 pending을 지우므로 Cost 부족이 예약 자동 재시도를 뜻하지 않는다. 사전 검사/activation true는 target Task 재생 실패 rollback을 보장하지 않는다. 관성화 설정 0.08 s/0.24 s는 기존 임시값을 보존했으며 원작 동일값은 미확인이다.

## 2026-10-01 — Dodge 입력과 해금형 특별 공격 상세 안내 이후 재개

- 현재 상태: 사용자가 공통 ComboAction CanActivate/Transition 비용 gate를 적용했다. 설명 작업은 완료했고 Examples/DodgeSpecialAttack_20261001에 16개 전체 source 제안과 1,311행 GUIDE, baseline/정적 검증 기록을 남겼다. 게임 기능을 어시스턴트가 적용한 상태가 아니다.
- 마지막 검증: Source/API 정적 대조, 기하학 11예제, Source 15개 SHA256 동일·신규 runtime enum 미생성 확인. UE cold build/PIE는 수행하지 않았다. asset primitive 조회는 빈 결과여서 InGame root/Notify/Skeleton/slot 검증으로 간주하지 않는다.
- 남은 원인: 사용자가 새 source/API와 BP/DataAsset/Montage/GE를 직접 적용해야 한다. 원작 비용/창 frame/Weak·Strong 모션/대각선 규칙, 특별 공격 cancel/피해/무적 및 Save producer는 미확인·미구현 범위를 유지한다.
- 정확한 재개 1: Router → Architecture ARCH-72 최신 절 → Migration D4 최신 절 → GUIDE를 읽고 실제 Source가 baseline 이후 변경됐는지 비교한다. 과거 공통 base 추출/CanActivate 적용을 반복하거나 사용자 변경을 덮어쓰지 않는다.
- 정확한 재개 2: GUIDE의 IsDataValid/enum/Dodge getter/Player 계산/ASC 네 함수/Controller binding·라우팅/Combo handler·ApplyEdge/Character cleanup/native unlock tags를 전체 API 묶음으로 적용한다. 저장·Editor 정상 종료 후 Development Editor cold build와 BP Compile/Save, 기존 X/Y/Charge/Release/Cancel 회귀를 확인한다.
- 정확한 재개 3: InputData A→IA_Dodge, IMC, shared Definition의 8 Dodge nodes, AM_DAS_Dodge 8 sections/Next None/point Branching Notify, BP 방향·Entry defaults와 graph-only grant를 연결한다. 임시 Notify frame은 실제 InGame rate/length를 확인한 뒤 authoring한다.
- 정확한 재개 4: F Weak/Strong 특별 공격 두 Entry를 grant하고 Edge RequireTags와 target ActivationRequiredTags를 연결한다. 두 Infinite dev unlock GE의 없음/Weak/Strong/둘 다를 새 PIE에서 검사한다. 이후 임시 대응임을 유지한 채 필요한 방향으로 확장한다.
- 정확한 재개 5: Cost GE 연결 후 실패 보존, 같은 Spec restart, root-motion capsule/벽/경사/LockOn yaw, interrupt/UnPossess/Stop PIE 무잔존을 검사한다. TryActivate true를 target Commit/Task 성공 및 원상 복구 보장으로 기록하지 않는다.

## 2026-10-01 — Dodge 최소 변경 재검토 뒤 재개 절차

- 현재 상태: 사용자 Source에 ComboAction 공통 실행/CanActivate/local Cost gate 및 Dodge enum/defaults/getter가 있다. 입력 binding, 지역 방향 계산, ASC 요청 대상 필터와 특별 공격 데이터 연결은 미적용이다.
- 마지막 검증: ASC/Controller/Action/ComboAction/Dodge/Definition/grant/tag Source를 읽고 앞선 전체 제안과 비교했다. 새 runtime 파일 없이 기존 입력 경로를 확장할 수 있는 설계를 ARCH-72와 Migration D4 하단에 추가했다. 게임 파일 편집과 build/PIE는 없다.
- 재검토 원인: 기존 기반 코드 전체 사본과 editor validation/입력 소유권/cleanup을 한 번에 제시해 Dodge 자체의 필수 변경보다 적용 범위가 커졌다. 이전 전체 16파일 일괄 교체 순서를 최신 절차로 사용하지 않는다.
- 정확한 재개: Router → Architecture 하단 ARCH-72 최소 변경 → Migration 하단 D4 변경 범위 축소 → 실제 Source 비교. 공통 base/이미 적용된 gate/enum을 반복 생성하지 않는다. F의 기존 base 재생 → 현재 입력의 8방 선택과 기존 press RequestedHandle 필터 → X/Y 소비·handoff 입력 기록의 공통 보정/해금 Edge 순서로 작은 diff를 제시한다.
- 새 계약: Dodge 8 BP는 동일 Input.Action.A binding으로 기존 Release/Cancel을 사용한다. 특별 공격 target은 graph-only다. Controller 선택 실패/중복은 press 전 거절하고 invalid handle을 일반 A activation으로 흘리지 않는다. 새 KZDodgeTypes.h/Dodge ASC 전용 activation wrapper/독립 실행기/공통 math helper는 선행 생성하지 않는다.
- 적용 후 확인: 8방/비LockOn F/동일 frame Move+A, 같은·다른 방향 InputEnd 전후, 비용 실패 시 기존 action 보존, A 해제·취소, X/Y 한 번 입력에 하나의 전환, graph-only 입력 기록, 기존 Charge와 UnPossess/EndPlay 수명. 원작 비용/창/모션 대응/Save·피해·무적은 기존 미확인 경계를 유지한다.


## 2026-10-01 — 최소 Dodge 재개점의 X/Y 선행 조건 정정

- 같은 날짜 바로 위 재개 절차의 “X/Y 소비 공통 보정 필수”는 Architecture 마지막 ARCH-72 절에 따라 축소한다. 현행 Action block/InputEnd Closed 계약이면 기존 X/Y 라우팅과 ComboAction command event/handler를 유지한다.
- 재개는 현재 enum/base를 유지 → Controller A binding/Player 현재 입력 방향/ASC optional Spec Handle 필터 → 기존 graph의 X/Y 해금 Edge/graph-only target 입력 기록 → 방향·InputEnd 전후·비용·Release/Cancel/Charge·cleanup PIE다. 새 bConsumed event/CommandTag API 전체 이관/IsDataValid 선행을 이 최소안에 일괄 적용하지 않는다.
- 아직 source 적용/build/PIE를 하지 않았다. 결론은 native 제어 흐름과 엔진 tag block의 정적 확인이며 BP가 이 정책을 유지하는지와 실제 데이터는 사용자 적용 후 검사한다.



## 2026-10-01 — 최소 Dodge 코드·MD 안내 작성 후 정확한 재개점

- 현재 상태: 전 기능 최소 변경/MD 인지 원칙을 AGENTS·Engineering 규칙·Router에 기록했다. [최소 Dodge 공동 구현 안내](DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md)와 [기존 파일 patch](Examples/DodgeMinimal_20261001.patch)는 준비됐고 사용자가 아직 게임 파일에 적용한 것으로 확인하지 않았다.
- 마지막 검증: 현재 Source 9개 baseline과 종료 SHA256이 모두 동일하다. 설치 UE 5.8 API/현행 Action block·InputEnd·grant 경로와 표적 에셋 존재를 확인했다. git apply --check --ignore-space-change 문맥 검사는 통과했다. 새 compile/PIE/미저장 BP properties 검증은 없다.
- 실패/미완료: 이번 설명 작업의 막힘은 없다. 적용·실행 검증은 사용자 후속 단계다. 원작 Notify 타이밍/특별 가족 대응/대각선 규칙·비용·무적·피해·Save producer는 미확인 또는 이번 구현 연결 범위 밖이다.
- 정확한 재개: Router → Architecture 마지막 ARCH-72 절 → Migration 마지막 D4 절 → 새 GUIDE → 현재 Source 변경분 비교. 이전 전체 첨부를 덮어쓰거나 이미 존재하는 ComboAction/CanActivate/Dodge enum을 재생성하지 않는다. Source가 변했으면 patch를 무조건 적용하지 않고 관련 함수만 대조한다.
- 다음 적용: 기존 7파일의 작은 수정/코드 cold build → F 입력·몽타주·node·A grant → 8방 데이터 → F 특별 X/Y Entry·해금 네 조합 → 실제 Cost/Release/Cancel/UnPossess/CMC root motion 및 기존 Weak/Strong/Charge 회귀다. X/Y 순서/OneParam event는 현행 InputEnd 정책에서 유지한다.

## 2026-10-01 — WeakAttack01 → LockOn L 튐 직접 PIE 검사 재개점

- 현재 상태: 사용자는 InputEnd 전에 L 입력을 유지한 공격→Run L 복귀의 포즈 튐을 보고했다. 2.5초는 사용자가 잠시 늘린 진단값이고 보존한다. 관련 실제 Source/라이브 ABP 최종 연결/설치 엔진 관성화 알고리즘을 읽었지만 원인은 미확정이다. 상세 근거는 `BUILD_RUNTIME_DIAGNOSTICS.md`의 같은 날짜 절에 있다.
- 마지막 검증: Player raw intent 저장과 CMC gate, Controller Move 처리 순서, ComboAction InputEnd/종료, AnimInstance 실제 속도각 및 Walk/Run 선택을 정적으로 확인했다. ABP 최종 연결은 Locomotion→Slot→Inertialization→Output이다. 직접 키 WeakAttack→L/F 비교 및 튐 프레임 기록은 없다.
- 실패 원인: Rider native debugger는 유효한 Source frame values를 제공하지 못했다. Windows 직접 제어는 초기화/재초기화 뒤에도 native pipe unavailable(os error 2)이다. UE MCP connected false, UnrealEditor 프로세스 없음이 마지막 상태다. Editor 종료 원인은 미확인이다. 사용자에게 현재 종료 상황을 질문했다.
- 정리: agent 중단점 두 개를 제거했고 user exception 8개는 유지했다. 이전 Python callback은 진단 코드 오류를 내었으며 수집 frame 0이다. Editor 프로세스 종료로 callback은 더 이상 동작하지 않는다. 다시 주입 코드를 실행하지 않는다.
- 재개 1: Router → 아키텍처 최신 절 → Migration 현 단계 → Locomotion 현행 정본 → 위 Diagnostics의 2026-10-01 절을 읽고 실제 관련 Source 변경분을 대조한다. 과거 설명의 방향/시간 숫자를 현행값으로 가정하지 않는다.
- 재개 2: UE `ue_health`와 debugger session/중단점 baseline을 확인하고, `computer-use`의 문서화된 JS API로 반환된 정확한 Editor 창을 선택한다. helper가 없으면 직접 조작 가능하다고 주장하거나 Python 이동 주입으로 대체하지 않는다. 기본 PIE mode/net 설정을 저장해 덮어쓰는 도구 옵션도 피한다.
- 재개 3: 실제 입력 매핑을 확인한 뒤 키로 LockOn, WeakAttack01, InputEnd 전 L 유지의 순서로 재현한다. 같은 시작 조건에서 F를 비교한다. 관측은 읽기 전용으로 `MoveInputWorld`, CMC Velocity/Acceleration, Actor Yaw, `GroundSpeed`, `bHasMovementInput`, `MovementDirectionAngle`, `LocomotionGait`, montage/Slot weight, active state/clip/sample weight·phase, 관성화 actual duration·normalized time·추가 request를 맞춰 수집한다. game-thread 샘플을 정확한 anim evaluation frame과 같다고 무조건 가정하지 않는다.
- 재개 4: 튐과 angle F→L 또는 Walk→Run의 일치 여부를 먼저 판정한다. 불일치면 Slot source 재개/clip phase·loop seam, 본별 보정·filter/profile·중단 요청 및 capsule/mesh 회전·위치를 구분한다. 원인별 수정 후보 하나만 A/B 확인하고 사용자가 확정한 2.5초 실험값을 원인으로 자동 되돌리지 않는다.
- 남은 작업: 직접 재현/원인 확정/최소 수정 제안/실제 효과 검증이다. 이번 조사는 게임 Source/BP/에셋 수정 및 build를 수행한 상태가 아니다.

## 2026-10-01 — 실제 패드의 F 중간 선택 확인 뒤 적용/검증 재개점

- 현재 상태: 앞 절의 Editor 미연결은 Rider 기존 Khazan 구성으로 해결했다(PID 19616). native Windows 입력 helper는 계속 불가여서 실제 패드 조작을 읽기 전용으로 기록했다. 공격 복귀 때 L 입력인데 F 방향을 쓰는 현행 경로와 후속 gait 전환이 확인됐다. 상세 수치/코드는 Diagnostics 최신 후속 절, 표현 계약 제안은 ARCH-73이다.
- 마지막 검증: full L 첫 종료 관측 9599에서 입력 -91.35도/세기 1/유효 true/컴포넌트 Resolved Run, native 방향 약 0도/속도 92.62/Anim Walk. 9607은 -82.03도/Run이다. F/Walk L/R/B 사례도 기록했다. 3,444 engine-frame raw/summary JSON을 Saved/ImportReports/WeakAttackLockOnExit_20261001_{raw,summary}.json에 저장했다.
- 정리: 성공한 callback의 error null, handle 해제/closure·builtins의 actor 참조 제거를 확인했다. 마지막 UE connected true/PIE Idle, debugger session은 시작하지 않았으며 새 중단점이 없다. Python 입력 주입/Ability 실행/anim property 덮어쓰기는 하지 않았다.
- 미완료 범위: 첫 F/Walk 중간 선택은 실측이지만 화면 bone-pose 튐의 정확한 frame·clip phase/관성화 상태 및 수정 효과는 아직 미검증이다. 게임 Source/BP/에셋 적용/수정안 build는 없다.
- 재개 1: Router → Architecture ARCH-73 제안 → Migration 현재 D4/Animation 정본 최신 절 → 실제 KZAnimInstance.cpp 두 함수 비교. 기존 기록의 아직 적용 전 actual-velocity 각도/hysteresis와 새 제안을 구분한다.
- 재개 2: Examples/LockOnRecoveryPose_20261001.patch의 방향 hunk만 먼저 사용자가 적용한다. 설치 API/문맥 검사는 완료됐다. ActorYawRotation은 기존 지역 값을 재사용하고 아직 갱신 전인 RotationMode member 대신 Snapshot.RotationMode를 조건에서 사용한다. UE 정상 종료 후 현재 Editor target build/BP compile, 새 PIE에서 InputEnd 전 full L을 유지해 첫 복귀 각도가 L인지 확인한다.
- 재개 3: gait hunk를 적용하고 full L 첫 복귀부터 Run, 약한 입력은 기존 Resolved Walk인지 확인한다. 2.5초 실험값을 유지해 변인을 구분하고 연속 공격과 분리된 한 번 공격을 모두 비교한다. 실제 속도/가속도/CMC와 non-LockOn hysteresis를 변경하지 않는다.
- 재개 4: F/R/B/대각선, LockOn 일반 방향/세기 변화의 발 미끄러짐, 입력 해제 Stop, LockOn toggle/non-LockOn Walk/Run/Sprint를 회귀 확인한다. F/Walk 중간 선택이 제거돼도 튐이 남으면 rendered pose/clip phase·loop seam/Slot source 재개/관성화 actual state를 추가 관측한다.
- patch 검사 경로 주의: 실제 Git prefix는 Khazan/이다. 새 patch는 a/Khazan/Source/... 헤더이며 프로젝트 cwd에서 verbose check의 실제 Checking patch와 1파일 +12/-3를 확인했다. 예전 Source/... 헤더로 cwd에서 수행한 체크는 Skipped patch가 될 수 있어 종료 코드 0만으로 문맥 통과라고 판단하지 않는다. 앞선 Dodge 자료의 문맥 검사 완료 기록은 이 이유로 유효한 변경 건수 확인 근거가 없으며, 그 guide/patch를 재개할 때 현재 Source에 이미 적용된 변경을 확인하고 올바른 Git 루트/--directory로 대상 검사를 다시 해야 한다.

## 2026-10-02 — Definition 배열 제목 적용 뒤 화면 확인 재개점

- 현재 상태: 헤더 2개/배열 metadata 3곳의 실제 수정과 UHT 생성 확인, Editor target 빌드 검증은 완료됐다. 자세한 계약은 `SOURCE_BP_CONFIG_ARCHITECTURE.md`의 같은 날짜 절이다. 기존 사용자 Source/에셋 변경은 보존했다.
- 마지막 검증: 3개 `TitleProperty`가 UHT `.gen.cpp`에 생성됐고 `UnrealEditor-Khazan.dll`이 갱신됐다. Rider 상태는 false/diagnostic 없음이었으나 UBT 로그는 Succeeded이며, 엔진 Build.bat 직접 실행은 exit 0/Target is up to date/Result: Succeeded다.
- 남은 확인과 제한: Editor는 연결되지 않은 종료 상태다. 실제 Details 화면의 표시/폭은 확인하지 않았다. metadata 수정의 컴파일 실패나 gameplay PIE 실패가 발생한 것은 아니다.
- 재개 1: 새 Unreal Editor에서 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`을 열고 Nodes 배열을 펼친 상태로 개별 원소를 접어 NodeId 제목을 확인한다. 한 노드의 CommandEdges 배열을 펼치고 각 Edge를 접어 command/phase/Hold/Move/target 문자열을 확인한다.
- 재개 2: `/Game/Data/Character/DA_CharacterDefinition_Player`의 InitialAbilityGrants를 같은 방식으로 확인한다. 입력 A를 공유하는 방향별 grant는 AbilityClass로 구분되고 graph-only grant의 빈 InputTag는 유지된다. 제목이 없으면 새 DLL을 로드한 프로세스인지/UHT metadata/해당 배열의 UPROPERTY를 표적 확인한다. 이름이 None이면 실제 데이터 필드 값을 확인하며 임의 이름을 채우지 않는다.

## 2026-10-02 — DodgeAttack_F Entry 설정 확인 후 재개

- 현재 상태: 사용자 4방 DodgeAttack 연결 중 F 실패의 직접 설정 원인과 기존 PIE 로그의 실패 분기를 확인했다. Editor live F CDO `EntryNodeId=None`이 shared graph의 `DodgeAttack_F` target과 불일치한다. 게임 Source/BP/에셋을 직접 수정하지 않았다.
- 마지막 검증: B/L/R Entry 설정 비교, F node/section/몽타주/초기 grant 존재, `HasComboEntry=false → TransitionToNode → cross-Montage reject`의 현재 Source 및 2026.10.02-04.03.40/42/43 UTC 기존 gameplay 로그를 확인했다. 재현용 Python 입력/Ability 실행은 하지 않았다.
- 재개: `/Game/Bluprints/AbilitySystem/Abilities/Player/DodgeAttack/GA_Player_DodgeAttack_F`의 Class Defaults → Combo → Entry Node Id를 `DodgeAttack_F`로 설정/Compile/Save한다. PIE 종료 후 새 PIE에서 LockOn F/RF/LF Dodge 뒤 X와 Y를 각각 입력해 해당 DodgeAttack 실행 및 cross-Montage reject 소멸을 확인한다. 문제가 남으면 변경 후 CDO/새 Pawn의 grant/같은 시도의 로그만 표적 확인한다.
- 남은 작업은 위 사용자 설정 적용과 수정 후 PIE 검증이다. 현재 진단을 그 적용/실행 성공으로 기록하지 않는다. 세부 근거는 Diagnostics의 같은 날짜 F 진단 절을 따른다.

## 2026-10-02 — 사용자 PIE 조작 / L Dodge → Idle 관측 재개점

- 현재 요청은 F DodgeAttack 설정 수정이 아니라 **L Dodge 뒤 Idle 복귀 튐의 원인 조사**다. 사용자가 PIE를 직접 조작하고 어시스턴트가 상태를 읽기로 명시했다. 입력/Ability 실행 주입은 하지 않는다. 먼저 Router → Architecture v2/Migration 현재 단계 → Animation 정본/이번 Diagnostics 절 → 현재 Source와 저장 report 순으로 재개한다.
- 마지막 검증: 연결 PID 27896/PIE Idle. v1 5,771 frame와 v2 1,165 frame/error null을 저장했다. v2의 무입력 L 4/R 1 종료는 Slot weight가 연속 감소했다. 이동 중단 L의 큰 pose 변화와 자연 종료의 작은 반대 속도/Idle 후보 재변화를 분리했다. 실제 활성 SM state/상체 튐 frame/사용자 시각적 증상과의 대응은 미확인이다. 게임 C++/BP/에셋 수정, 해결 검증과 새 build는 하지 않았다.
- 디버거 제한: Native kind는 없고 LLDB attach는 source/locals를 제공하지 못했다. 두 agent breakpoint는 제거했고 attach를 STOP해 분리했으며 user exception 8개를 보존했다. Editor는 살아 있다. native computer-use pipe도 os error 2여서 자동 조작 증거로 사용하지 않는다. 이 제한을 해결됐다고 표현하지 않는다.
- 저장 자료: `Saved/ImportReports/DodgeIdleLive_20261002_v1_latest.json`, `_raw.json`, `_v2.json`; `DodgeIdleInspection_20261002.json`, `DodgeIdleMontageDetail_20261002.json`, `DodgeIdlePoseCompare_20261002.json`; ABP/Montage `.t3d` 및 `DodgeIdleABPTransitions_20261002.json`. 재조사 대신 이 자료를 먼저 분석한다.
- v3 관측은 머리·골반·발/Root에 Spine1/2, 좌우 clavicle/upper arm/hand를 추가한다. read-only Slate post-tick callback이며 최대 24,000 sample은 진단 메모리 제한이지 gameplay 수치가 아니다. 마지막 설치 직후 v3 sample 0/error null/running true다. 입력 없는 종료와 잠시 L 이동 후 해제를 따로 재현하고 사용자가 지목한 튐 순간/부위를 matching해야 한다. 미확인 경로를 임의로 자연 종료라고 가정하지 않는다.
- 살아 있는 key: `builtins._kz_dodge_idle_probe_v3_20261002`. 이전 v1/v2 callback handle은 해제했다. 새 Editor process에는 이 key가 없다. callback을 재설치하기 전에 기존 자료를 JSON으로 저장한다. 재사용 스크립트는 `Saved/ImportReports/DodgeIdleProbe_20261002.py`이며 game input을 쓰지 않는다. installer는 기존 v3를 우선 조회하고 없으면 v2를 조회해 이전 handle을 unregister한다. 재설치는 새 samples를 시작하므로 저장부터 한다.
- 관측 요약도 `Saved/ImportReports/DodgeIdleLive_20261002_summary.json`에 보존했다. 마지막 확인은 v3 sample 0/error null/running true이며 PIE 재개 후 상체까지 기록할 준비 상태다. 이전 v1/v2 실제 재현을 새 v3 재현 완료로 기록하지 않는다.
- 저장/해제 절차: `ue_health` 확인 → `ue_execute_python`에서 builtins key를 조회 → samples/error를 JSON으로 Saved/ImportReports의 새 v3 report에 저장 → `unreal.unregister_slate_post_tick_callback(s['handle'])` 후 handle=None → 필요하면 builtins v1/v2/v3 key를 제거해 closure/object 참조를 정리한다. 사용자 PIE를 Stop/Start하거나 debugger를 다시 붙이는 조작은 이 관측과 섞지 않는다. 종료 또는 추가 관측이 불필요할 때 해제 여부를 MD에 추가한다.
- 아직 원인 확정이 아니므로 Slot AlwaysUpdate/BlendMode/시간/원본 clip을 바꾸지 않았다. 실제 발생 frame을 근거로 기존 함수 또는 해당 에셋 한 설정의 작은 변경만 제안한다. 입력 없이 자연 종료할 때 LocomotionExitInertializationDuration을 바꾸는 것은 그 경로의 해결책이 아니다.

### 2026-10-02 — 사용자 관측 상태 질문 직후 재확인

- `ue_health`는 같은 PID 27896/connected true, `ue_play state`는 Idle(캐릭터 Idle이 아니라 PIE 종료 상태)다. v3 callback handle은 존재하고 error null이지만 samples=0/last=None이다. 이전 v1/v2의 총 6,936 sample 관측 사실과 새 v3의 아직 미수집 상태를 구분해 보고한다. 최신 새 조작을 수집했다고 표현하지 않는다.
- 현재 v3 상태를 `Saved/ImportReports/DodgeIdleLive_20261002_v3.json`에 저장했다(빈 samples). 관측기는 유지하며 다음 실제 PIE 실행에서 sample 증가와 callback error를 즉시 확인해야 한다. 게임 파일/에셋 변경 및 원인 확정은 없다.

### 2026-10-02 — 사용자 새 PIE 관측 성공 및 Actor Yaw 원인 대조

- 앞선 sample 0 뒤 사용자 새 PIE를 실제 수집했다. v3 1,084 frame/error null, WeakAttack 2/L Dodge 3/R Dodge 2회다. v3 JSON은 이 실제 기록으로 저장됐다. Editor 같은 PID 27896/PIE Idle이다. 상체/손까지 component/world pose를 기록했다.
- L 종료 후 세 번 모두 +720 deg/s/R 두 번 모두 -720 deg/s의 Actor Yaw 보정이 보인다. 첫 L frame 183579는 Actor +7.012585 deg/로컬 머리 약 0.046093 deg, input=0/speed=0/slot=0이다. 큰 변화는 Actor/capsule 회전이다. 현재 Definition의 yaw rate 720 및 Root Motion 중 PhysicsRotation을 막는 엔진 분기/BP CDO false와 대조했다. 함수 hit 증거 또는 사용자 화면 튐의 정확한 직접 표시로 과장하지 않는다.
- report: `DodgeIdleLive_20261002_v3.json`, `_v3_endstats.json`, `_v3_worldstats.json`, `DodgeIdleRotationSettings_20261002.json`, `DodgeIdleRotationDiagnosis_20261002.json`. Source/설정/원작 미검증 표시/작은 checkbox 비교 절차는 Diagnostics의 새 1,084 frame 절을 먼저 읽는다. 게임 파일/에셋 직접 수정과 변경 후 효과 검증은 없다.
- v3 handle은 저장 뒤 해제했고 **현재 관측 key는 `builtins._kz_dodge_idle_probe_v4_20261002`**다. v4는 동일 본 관측에 controller yaw/실제 CMC yaw rate/AllowPhysicsRotation flag/desired rotation flag/Actor root-motion API 값을 추가한다. 새 installer는 `Saved/ImportReports/DodgeIdleRotationProbe_20261002.py`다. 재설치 전 현재 v4 자료를 저장한다. installer는 v4 우선/v3 fallback의 이전 handle을 unregister한다. 최대 24,000 sample 뒤 자동 해제하는 진단 상한을 유지한다.
- 다음 재개: v4 수집 증가/error를 확인하고 같은 무입력 L/R을 기록한다. 사용자에게 기존 CharacterMovement checkbox만 비교하도록 안내한 경우 설정 적용 여부를 먼저 확인한다. 본 포즈/Slot blend 수치는 유지하며 회피 중 controller–actor yaw 차이와 종료 step 감소를 비교한다. WeakAttack/콤보의 authored root rotation도 확인한 뒤 영구 적용 범위를 정한다. v4의 Slate post-tick root-motion API 값을 CMC 함수 내부 gate 순간과 동일시하지 않는다.
- 종료 정리: v4 sample을 새 JSON에 저장 → v4 handle unregister/None → 필요하면 builtins v1/v2/v3/v4 key 삭제. 사용자 조작은 유지하며 PIE 입력/Ability 실행을 주입하거나 승인 없이 CMC gameplay 설정을 변경하지 않는다.

### 2026-10-02 — Art 애니메이션 작업으로 전환하며 관측기 정리

- 새 사용자 요청의 애니메이션 편집 전에 v4 관측 자료 7,382 sample을 `Saved/ImportReports/DodgeIdleLive_20261002_v4.json`에 저장했다. Slate post-tick callback을 unregister하고 builtins v1/v2/v3/v4 상태 참조를 해제했다. 이후 이 callback이 관측 중이라고 표현하지 않는다.
- 이 정리는 읽기 전용 진단기의 수명 종료이며 CMC 설정/게임 C++/BP/애니메이션을 바꾸지 않았다. v4의 추가 frame 분석 및 Allow Physics Rotation 비교는 아직 수행하지 않았고 이전 Actor Yaw 가설의 검증 범위는 유지된다. 재개 시 저장 v4를 먼저 분석하고 필요할 때만 기존 installer로 다시 설치한다.


## 2026-10-02 — Guard 직접 구현 / 실행 검증 직전

- 사용자 직접 수정 권한으로 Guard Ability 1개와 기존 ASC/Controller/AnimInstance/태그 연결을 적용했다. Guard BP·상태/성공 비용 GE·IA_Guard·Montage·방향 BS와 기존 InputData/CharacterDefinition/IMC/ABP 연결을 저장했다. Guard 17 시퀀스에는 InputEnd 표시를 추가했고 pose/root/rate는 편집하지 않았다.
- 최신 source 계약은 ARCH-74와 Source/Khazan/Ability/PlayerAbility/KZGuardAbility.{h,cpp}다. Start/성공의 끝에 계속 held면 ABP 유지, Release 즉시 GuardState GE/Walk 제약 해제, InputEnd에서 End 전환/이동/다른 Action 허용이다. 성공은 ASC.TryGuardHit(공격 소유 StaminaDamage, Attacker)→SetByCaller Stamina 차감→기존 회복 지연 GE 0.5초→랜덤 Suc_F/L/R다.
- 저장 검수 중 Montage 길이 변경이 Notify Link를 옮기는 문제, FGuid decimal overflow, UE 배열 원소 struct copy 수정 누락을 수정했다. Montage 5 InputEnd 실제 절대시간은 0.223059 / 0.519837 / 0.936445 / 1.353704 / 1.698715초다. 비용 modifier는 SetByCaller로 확인했다. ABP true pose=0/false pose=1을 설치 엔진 Source로 확인하여 연결했다.
- Live Coding UBT Succeeded를 확인했으나 Rider build 결과는 diagnostics 없는 false였다. 확정용 cold UBT build 진행 중이며 Editor를 dirty package 0 확인 후 정상 종료했다. DevMap 새 프로세스에서 Khazan.Guard.PIE 자동화 통합 검사(physical input/화면 품질 검증 아님)를 실행할 예정이다.
- 다음 재개: cold build 로그 확인→UE5.8 Editor Khazan.uproject /Game/Maps/DevMap 실행→RiderLink health→에셋/Notify/GE/BP 저장 후 재로드 감사→PIE 시작→native Automation RunTests Khazan.Guard.PIE→Automation 로그와 Guard tag/수명/비용/8방 검사 결과 확보→PIE 중지→이전 /Game/Maps/L_StormPass_Environment 복귀→완료 문서 추가.
- Windows 직접 조작은 computer-use sky.list_apps native pipe os error 2로 불가했다. Python 키/이동 조작으로 대체하지 않는다. Source test는 native Ability entry를 호출하는 통합검사이며 키보드/패드 입력 또는 visual pass로 표현하지 않는다.
- 시작 스냅샷 29파일: Saved/GuardImplementation_20261002/Before/Manifest.json, 기존 AnimGraph export, InputEndPlan.json과 setup_guard_20261002.py가 재개 근거다. 기존 Source/BP 사용자 변경과 동시 환경/렌더링 변경을 보존한다.


## 2026-10-02 — Guard 구현 완료 / 화면·적 타격 후속 검증

- 현재 상태: [GUARD_IMPLEMENTATION_20261002.md](GUARD_IMPLEMENTATION_20261002.md)의 Source·입력·GE·Montage/BS/ABP를 실제 적용/저장했다. 새 클래스는 Guard 실행자 하나이며 existing 8 Source에 연결했다. 이전 이 문서의 “실행 검증 직전” 절은 당시 작업 상태로 보존한다.
- 마지막 검증: 초기 gameplay cold build Succeeded, 최종 테스트 cold build Succeeded. 새 Editor PID33588/UE5.8.2에서 asset audit passed, 17 Guard pose/root/playback/frame grid 보존 passed. 10:39:05~10:39:21 UTC 실제 DevMap PIE Khazan.Guard.PIE Result=Success. held/8방향/Cost/성공/release/InputEnd/Move/X/tap/cancel/자연 종료/UnPossess를 검사했다.
- 초기 테스트 시행착오: Automation이 이전 PIE를 닫는 동작에 맞춰 Test Started 뒤 새 PIE를 시작하도록 변경했다. 첫 activation 미관측 시도와 디버거 정지로 watchdog이 지난 시도는 성공으로 세지 않는다. 실제 디버거에서 지상/섹션 CanActivate 통과·Guard GE/Start/snapshot을 확인했다. 테스트는 지상 Player/ASC/AnimInstance readiness를 기다린다. DevMap 기존 미설정 TEST_Monster 4개의 정확한 오류 메시지 2종만 각각 4회 expected error로 명시했으며 Guard/다른 오류는 계속 실패한다.
- 저장 근거: Metadata/GuardImplementation_20261002의 RuntimeResult.json, PIETest.log, GuardAssetAudit.json, GuardPoseAudit.json, InputEndPlan.json, OriginalTimingEvidence.json, FinalAnimGraph.txt, GuardMontage.t3d, 두 cold build log. 작업 전 29파일 백업은 Saved/GuardImplementation_20261002/Before/Manifest.json 및 하위 경로다. 과거 전체 InGame playback audit는 Guard marker 추가 전 역사 기록이며 현재 Guard 검사와 구분한다.
- 정리: agent breakpoint 3개 제거, user exception 8개 보존, debugger detached. PIE Idle. 기존 /Game/Maps/L_StormPass_Environment 복귀 완료. dirty content/map package=0. 동시 환경/렌더링 작업 파일을 저장/복원하지 않았다.
- 미검증/실패 원인: Windows computer-use helper pipe unavailable(os error2)로 물리 키·마우스/패드와 화면 QA를 수행하지 못했다. Python 키/이동 주입으로 대체하지 않았다. PIE 검사는 native C++ gameplay entry 호출이다. 실제 몬스터 타격·방어 각도·HP 생략·GuardBreak/JustGuard 및 별도 Actor 파괴 테스트는 미구현/미검증이다.
- 정확한 재개: Router → Architecture 최신 ARCH-74 → Migration 최신 Guard 적용 → 새 Guard 문서 → 관련 Source/현재 BP property와 저장 report를 읽는다. authoring setup()을 반복하지 않는다. 직접 입력 가능 시 LShift/LB tap/hold/release와 LockOn 8방향·비LockOn, InputEnd 전후 X/Y/A/이동을 화면 비교한다. 기존 Start/Stop/Dodge 로직을 Guard 문서에 맞춰 임의 교체하지 않는다.
- 자동 재검사: DevMap을 열고 Automation RunTests Khazan.Guard.PIE 실행 → Test Started/“waiting for PIE” 뒤 새 PIE 시작. 30초 readiness watchdog 내 시작한다. 결과 log의 실제 Success와 Guard assertion 오류를 확인하고 PIE 종료/원래 맵 복귀한다. 기존 fixture 몬스터 구성이 바뀌면 expected 오류 횟수를 그 변경에 맞춰 재검토한다.
- 미래 공격 연결: 호출자가 방어 가능/방향/타격 여부를 먼저 판정하고 VictimASC.TryGuardHit(공격 데이터의 StaminaDamage, Attacker)를 호출한다. true면 그 타격의 HP 피해를 생략, false면 기존 피해/GuardBreak 정책으로 진행한다. 현재 정상 Guard Cost로 JustGuard 값14 또는 임의 고정치를 넣지 않는다.


## 2026-10-06 — Guard 중단 작업 재개 완료 / 실제 방향 재생 검증

- 현재 상태: Guard 직접 구현의 방향별 실제 재생 오류를 해결했고 기존 기능 회귀까지 통과했다. 10월 2일의 완료 기록 중 8방향은 각도/배치 검사라는 범위를 이번 기록으로 정정한다. 당시 실제 motion playback까지 확인하지 않았기 때문에 복제 BS의 stale segment index가 남아 있었다.
- 마지막 검증: KhazanEditor Win64 Development cold build 성공, 새 PID24936/UE5.8.2 saved BS reload 일치. 실제 DevMap Khazan.Guard.PIE 2026-10-06 01:01:11.865~01:01:38.080 UTC Result=Success. 8방향 clip/weight1/재생 진행, ±179 경계, camera/actor yaw 차이, nonLock F/stop Loop와 12 checkpoint×227본 pose 일치. 기존 cost/success/release/InputEnd/X/cancel/natural End/UnPossess 검사도 통과했다.
- 실패 원인/실제 수정: SampleData를 각도순 교체한 뒤 복제된 BlendSpaceData.Segments가 예전 sample order 0,7,5,3,2,4,6,8,1을 유지했다. 디버거 0도/index2/L/weight1을 확인하고 Guard BS의 native UBlendSpace::ResampleData로 0–1…7–8을 생성/저장했다. authoring script에서 같은 호출을 누락하지 않도록 수정했다. test의 pose 비교 quaternion은 정규화해 수치 비교 오류를 바로잡았고 gameplay 수치/자산 rate를 바꾸지 않았다.
- 보존/백업: 작업 시작의 ABP_Player dirty/live graph 전체 .copy와 disk7파일을 Saved/GuardLocomotion_20261006/Before에 보존했다. 현재 Guard Ability/AnimInstance/ABP SHA256은 시작과 동일, BS derived data와 기존 개발 test가 변경됐다. RuntimeResult/ChangeManifest/DebuggerEvidence/전후 log/BS copy/두 성공 build log는 Metadata/GuardLocomotion_20261006이다.
- 최종 정리: 작업 시작 맵 /Game/Maps/DevMap 유지, PIE Idle, game world None, dirty content/map0, ABP UP_TO_DATE, agent 중단점 제거, user exception8 상태 보존, debugger detached. 다른 환경/렌더링/로코모션 변경을 되돌리거나 save-all하지 않았다.
- 남은 별도 범위: Windows computer-use pipe unavailable(os error2)로 물리 LShift/LB와 연속 화면 품질은 미검증이다. native C++가 gameplay API를 호출한 검사이며 Python 키/이동 주입은 하지 않았다. 실제 targeting/적 hit·HP·방어 방향·GuardBreak/JustGuard는 이번 Guard foundation 소비자를 구현할 때 검증한다.
- 정확한 재개: Router → Architecture 최신 ARCH-74/10월6일 범위 정정 → Migration 최신 Guard → GUARD_IMPLEMENTATION_20261002.md의 10월6일 절 → 해당 current Source/Metadata/GuardLocomotion_20261006부터 확인한다. 전체 Art/Source를 재조사하거나 authoring setup()을 반복하지 않는다.
- 자동 재검사: DevMap에서 Automation RunTests Khazan.Guard.PIE 실행 → Test Started 후 30초 readiness watchdog 안에 새 PIE 시작 → 최종 Success/Guard assertions 확인 → PIE 종료/시작 맵 유지. fixture의 LockOn mode는 기존 constraint override이며 실제 targeting 버튼 검사가 아니다. 몬스터 fixture 구성 변경 때만 expected error2종×4의 전제를 재검토한다.
- Guard BS의 SampleData를 이후 script로 바꾼 경우 정확한 Guard path/버전 확인 후 기존 resample_guard_blendspace(bs) → 해당 BS save → 재시작/방향 검사 순서로 진행한다. 보간 시간을 늘리거나 Player 방향식을 바꾸는 것으로 stale cache를 숨기지 않는다. 직접 플레이 QA가 가능하면 8방향 중심/대각/뒤 경계/idle 전환 및 InputEnd 전후 행동 교체 화면을 비교한다.


### 2026-10-06 — 검증 종료 뒤 에디터 상태 추가 관측

위 PIE Idle 정리는 01:01:38 UTC Automation 완료 직후의 상태다. 이후 이 에이전트가 실행하지 않은 별도 PIE 세션이 다시 시작/종료됐고, 01:07:36.906553 UTC 마지막 읽기 전용 관측에는 /Game/Maps/UEDPIE_0_DevMap.DevMap이 실행 중이었다. dirty content/map은 계속 0이다. 이 추가 세션을 종료하거나 입력을 주입하지 않았다. 이때 MCP ue_play(state)의 Idle 응답과 실제 UnrealEditorSubsystem game world가 일치하지 않아 native world 관측을 기록한다. 추가 세션의 물리 입력/화면 품질을 자동 테스트 결과로 계산하지 않는다. FinalEditorState.json과 RuntimeResult.json은 Automation 종료 상태와 마지막 관측 상태를 구분해 저장했다.

### 2026-10-06 — Guard 이동 중 Start/End 생략 적용, 검증 진행 중

- 현재 요청은 사용자 직접 수정이다. Guard cpp의 PlaySection/InputReleased/기존 HandleMoveInput만 보완했다. 허용된 기존 이동 intent가 있으면 Start를 건너뛰고 held 상태를 유지하며, release/End는 바로 Ability를 정리한다. Start/End 재생 중 이동 입력에도 InputEnd를 기다리지 않는다. held 성공 반응은 유지한다.
- 기존 PIE test에 이동 press/release/tap, Start/End InputEnd 전 이동, 성공 중 이동/release, 실제 Guard/base pose 출력과 늦은 callback cleanup 검사를 추가했다. 아직 이 변경의 build/PIE 완료를 주장하지 않는다. 백업은 `Saved/GuardMovementPolicy_20261006/Before/Manifest.json`, 결과 저장 위치는 `Metadata/GuardMovementPolicy_20261006/`이다.
- 마지막 에디터 관측은 native game world 없음, dirty content/map 없음이다. 변경 코드를 확실히 로드하려고 에디터 정상 종료를 요청했다. 재개: UE5.8 Build.bat KhazanEditor Win64 Development (NoHotReload/DisableLiveCoding) → DevMap 에디터 실행 → Automation RunTests Khazan.Guard.PIE → Test Started 확인 뒤 PIE 시작 → Result와 모든 오류 확인 → scoped MD에 실제 결과 추가. 기존 Guard setup/재생률/ResampleData 작업은 재실행하지 않는다.


### 2026-10-06 — Guard 최종 PIE 대기와 에디터 throttle 임시 조치

첫 PIE의 유일한 신규 실패는 일반 로코모션을 ungrouped 목록에서만 검사한 개발 테스트 관측 범위였다. 디버거에서 bIsGuarding=false/InputAmount=1을 확인한 뒤 기존 Locomotion Sync Group까지 읽도록 test만 보완했고 재빌드 성공했다. PID24736의 최종 Automation은 아직 test 시작 전 백그라운드 throttle(3 FPS) 대기 중이다. 확인한 `/Script/UnrealEd.EditorPerformanceSettings` CDO의 `bThrottleCPUWhenNotForeground=true`를 테스트 동안만 false로 바꾸고 종료 후 true로 복원한다. gameplay tuning/config/에셋 변경 목적이 아니며 SaveConfig를 호출하지 않는다. 중단 시 해당 CDO의 원래 true를 먼저 복구하고 native game world/dirty 상태를 확인한다. 최종 Success는 아직 미확인이다.


### 2026-10-06 — Guard 이동 Start/End 생략 작업 완료·재개 지점

- 위 검증 진행/대기 절의 작업은 완료됐다. 최종 cold build 성공, PID24736 DevMap Khazan.Guard.PIE 2026-10-06 01:31:55.038~01:32:08.870 UTC Success. 기존 Guard cpp 3함수·개발 test만 변경했고 Start/End 이동 생략, held 성공/비용, 8방향 actual clip/mesh, 기본 group 출력과 cleanup을 확인했다.
- 최초 실패는 test가 일반 로코모션의 Sync Group을 관측하지 않은 범위 문제였다. 디버거 state 확인→test 보완→cold 재빌드→최종 Success까지 진행했다. 두 실패/디버거 실행 log도 보존한다. background throttle은 notify NEVER로만 변경했고 원래 true를 복원했으며 SaveConfig/프로젝트 config 수정은 하지 않았다.
- 마지막 검증 01:32:42.411668 UTC: native game world 없음, editor DevMap, dirty content/map=0, ABP UP_TO_DATE, debugger 없음, agent breakpoint0/user exception8 보존. 결과/백업: Metadata/GuardMovementPolicy_20261006/RuntimeResult.json·PIE_Final.log·FinalEditorState.json·ChangeManifest.json / Saved/GuardMovementPolicy_20261006/Before/Manifest.json.
- 다음 작업은 실제 LShift/LB 및 화면 QA다. 정지 press/release → 이동 입력을 유지한 press/release → Start/End InputEnd 전 이동 → held Suc 중 이동/해제 순서로 본다. 자동 회귀가 필요하면 최신 Guard 문서/Source를 확인한 뒤 기존 Automation RunTests Khazan.Guard.PIE를 보내고 Test Started 이후 PIE를 시작한다. start 전 background FPS 대기가 생기면 원래 editor throttle 값을 기록하고 notify NEVER로 잠시 해제한 뒤 반드시 복원한다. Guard setup·RateScale·root·resample은 재실행하지 않는다.

### 2026-10-06 — 다른 동작 중 held Guard 자동 실행 적용, 검증 진행 중

- 사용자 직접 수정 요청에 따라 기존 Controller Input_GuardPressed 한 콜백을 보완했다. 실제 Source의 Triggered binding을 유지하며 State.Guarding=false일 때 기존 ASC press를 재시도하고 true일 때 held Guard의 InputEnd restart를 막는다. 새 runtime 파일/held 상태/queue/timer/ASC API는 없다. Guard/ASC/직전 이동 Start·End 코드도 변경하지 않았다.
- 기존 개발 test에서 엔진 GetActionEventBindings/Execute로 실제 Controller callback을 호출한다. blocked WeakAttack/Dodge 중 held 유지, 기존 InputEnd 허가 때 자동 활성화, 유지 중 Start 반복 방지, 중간 공격 후 복귀, 허가 전 release/cancel 뒤 미실행을 추가했다. 아직 새 build/PIE 완료가 아니다. Saved/GuardHeldInput_20261006/Before/Manifest.json과 Metadata/GuardHeldInput_20261006/가 이번 작업의 백업/증거 경로다.
- 현 저장 mapping은 LeftShift/Gamepad_LeftShoulder(LB), IA/IMC triggers=[]다. 사용자 표현 RB와의 키 변경 여부만 비동기 선택 질문으로 확인 중이며 핵심 코드 작업은 독립적으로 진행한다. 별도 답변이 없으면 기존 mapping을 보존한다.
- 재개: 현재 소스/backup 비교 → native world/dirty 확인 후 정상 editor 종료 → UE5.8 KhazanEditor Win64 Development cold build(NoHotReload/DisableLiveCoding) → DevMap 재실행 → 기존 Khazan.Guard.PIE Automation/Test Started 뒤 PIE 시작 → 모든 assertion/결과 확인 → 결과와 실제 키를 scoped MD에 추가. 필요하면 editor throttle의 원래 값을 기록하고 notify NEVER로 임시 해제/복원한다. setup/RateScale/root/resample을 실행하지 않는다.


### 2026-10-06 — held Guard 자동 실행 완료·검증과 재개

- 위 진행 중 절은 완료됐다. 기존 Controller Input_GuardPressed 한 콜백/개발 test만 변경했다. 실제 Triggered binding을 유지하고 기존 State.Guarding/ASC 허가로 held 재시도·중복 restart 방지를 처리했다. h/ASC/Guard cpp·h/IA/IMC의 backup hash를 보존했다.
- cold build 성공. editor 종료가 완료되기 전 첫 link LNK1104를 만나 종료 확인 후 동일 build를 성공시켰다. 이후에는 quit 요청 뒤 대상 process 실제 종료를 확인한 후 link한다. 최초 Automation은 PIE 요청이 늦어 준비 timeout만 발생했다. Test Started→PIE 요청을 한 functions.exec에서 연속 처리해 2026-10-06 03:02:17.808~03:02:36.401 UTC Khazan.Guard.PIE Success를 확인했다.
- 실제 Controller binding callback으로 WeakAttack/Dodge 불허/허가 뒤 자동 Guard, held Start 미반복, 중간 공격 후 복귀, 허가 전 release/cancel 미실행을 확인했다. 기존 Guard 이동·8방향·비용/취소/자연 End/UnPossess 검사도 통과했다. 물리 장치·연속 화면·모든 액션 전수 검사는 별도다.
- 최종 2026-10-06T03:03:47.447678+00:00: PID26692, native game world 없음, editor DevMap, dirty content/map=0, 원래 background throttle true 복원(notify NEVER/SaveConfig 없음). 자료는 Metadata/GuardHeldInput_20261006/RuntimeResult.json·PIE_Final.log·FinalEditorState.json·ChangeManifest.json·ColdBuild.log, 시작 backup은 Saved/GuardHeldInput_20261006/Before/Manifest.json이다.
- 현재 매핑 LShift/LB를 보존했다. 사용자 표현 RB와 달라 선택 질문을 보냈으나 아직 응답이 없다. 뒤늦게 RB 변경을 요청하면 현재 IMC_Default DefaultKeyMappings의 IA_Guard와 다른 RB binding 여부를 표적 확인하고 해당 키만 바꾼다. Guard setup/RateScale/root/resample은 재실행하지 않는다.
- 다음은 실제 입력 QA: 약공격/회피 전부터 현재 가드 키 유지 → 기존 InputEnd 때 자동 전환 → 가드 유지 중 Start 미반복 → 공격 교체 후 재복귀 → 허가 전 release/cancel 뒤 미실행. 자동 재검사가 필요하면 Router→Architecture/Migration 최신 절→Guard 정본/Source 순서로 확인하고 Test Started와 PIE 요청을 한 도구 실행에서 연결한다.

### 2026-10-06 — Heal 직접 구현 진행 중, 기존 에디터 격리

요청: HP/MaxHP=200, 무제한 +100 물약, DPad Down, 이동 가능/하체 로코모션+상체 Heal. Router→Architecture/Migration 최신 절→Engineering 상태/규칙/Guard·Locomotion 현행→Attribute/Controller/Action/Character 현재 소스를 읽었다. 원본 Heal 시퀀스 NumFrames45/SequenceLength1.4666667/RateScale 비직렬화·기존 rate1/root-motion=false/Notifies 없음은 Saved/Extracted/InGame_Playback_20261002의 원본 JSON·PlaybackPlan에서 확인했다. 회복/InputEnd 시점은 아직 원작 미확인이며 임시 Montage authoring 값으로 구분한다.

백업: Saved/HealImplementation_20261006/Before/Manifest.json. 메인 기존 PID9596·별도 아트 PID13632는 이번 작업에서 사용/종료/PIE 제어하지 않는다. 새 snapshot: C:/Users/user/Desktop/GitProject/Khazan_HealWork_20261006/Khazan, robocopy 23.215GB 완료. 필요 로그/보고서는 Metadata/HealImplementation_20261006에 저장한다. 다음: 최소 Source 적용→snapshot Source 동기화→snapshot cold build→숨김 새 editor의 명시된 project-dir 확인 뒤 author/test→원본 target hash 비교와 저장 asset 선택 복사→새 과정 결과/한계/정확한 재개 추가. 메인 locked DLL을 교체하지 않으며 기존 에디터에 MCP UE command를 보내지 않는다.

### 2026-10-06 — Heal Source 적용·격리 authoring 재시도 지점

Source 실제 적용: KZAttributeSet HP/MaxHP 접근자·양쪽 pre clamp·MaxHP post clamp·instant GE 후 clamp, Controller Heal Started/Completed/Canceled, native Input.Action.Heal/Ability.Action.Heal, 새 KZHealAbility h/cpp. Heal은 한 PlayMontageAndWait/instance ID 필터/회복 1회 bool·자기 Walk 제약 handle을 갖고 기존 Action InputEnd/cancel/UnPossess 경로를 사용한다. 개발 전용 KZHealAbilityPIETest.cpp는 실제 Controller 콜백·CMC 이동·하체 Walk/손 Heal pose·HP·취소·재사용을 검사한다. 게임 코드 검증은 아직 완료하지 않았다.

메인 Build.cs는 변경하지 않았다. Scripts/Engineering/HealAuthorEditor.cpp는 snapshot Source/Tests로만 복사한 one-shot editor tool이며 snapshot Build.cs에만 UnrealEd/AnimGraph/BlueprintGraph/AssetRegistry/LevelEditor/AnimGraphRuntime을 추가했다. 두 초기 compile 오류(FindFPropertyChecked 미지원, TSubclassOf 명시 변환)를 수정해 ColdBuild_Author 성공했다. 새 숨김 RenderOffscreen editor PID21096/DevMap에서 mailbox Ready project-dir/PID를 확인한 뒤 Author를 보냈다. author는 모든 10개 대상 중 ABP 외 에셋을 저장한 뒤 CachedPose extension 등록 누락으로 ABP compile fatal(Cast nullptr to AnimBlueprintExtension_CachedPose)했다. main Content는 아직 모두 시작 hash와 동일하다. 사용자 PID9596와 아트 작업 에디터는 사용하지 않았다.

실패 원인은 설치 UE AnimGraphNode_Base::PostPlacedNewNode의 RequestExtensionsForNode lifecycle 누락으로 로그/engine source가 특정했다. tool의 Node 생성에 PostPlacedNewNode를 추가했다. PID21096 종료 확인 후 실패된 작업 에셋만 snapshot Saved/HealAuthorRetryBackup에 복사했고 known snapshot Content prefix 검증 뒤 새 5개 에셋 삭제/기존 5개는 시작 백업에서 복원했다. 재build session78961 진행. 실패 로그는 Metadata/HealImplementation_20261006/Author_CachedPoseInitFailure.log. 메인 Content/DLL과 기존 editor state를 바꾸지 않았다.

재개: snapshot cold build 종료 확인→새 숨김 editor launch(RenderOffscreen, DisablePlugins RiderLink/ModelContextProtocol, Python boot 절대경로, GameFeatures enable)→Ready.json의 새 PID/정확한 project identity 확인→새 mailbox request 이름으로 Automation RunTests Khazan.Heal.Author→Author Success 뒤 native Khazan.Heal.PIE/Khazan.Guard.PIE→boot가 각 Test Started 감지 후 동일 process에서 PIE를 시작함. 기존 Ready/response는 이전 process 기록이며 현재 검증으로 사용하지 않는다. author setup은 실패 복원 없이 중복 실행하면 안 된다. 테스트/저장 reload 통과 뒤에만 main Content target hash 확인과 선택 복사를 한다. 종료 시 work editor throttle 원래값 복원, work PIE Stop/quit, 실제 process 종료 확인. 마지막에는 isolated editor tool을 snapshot Source에서 제거하고 메인과 동일한 Build.cs로 빌드해 제품 의존성이 늘지 않음을 검증한다.

### 2026-10-06 — Heal Source·격리 build/PIE/reload 완료, 파일 잠금 해제 후 자동 반영 대기

앞선 Heal 재시도 단계는 해결됐다. CachedPose PostPlacedNewNode/Montage RefreshCacheData를 authoring에 적용하고 걷기 진입·Started→Canceled test fixture를 보완했다. 보호된 proxy/Notifies 직접 읽기를 제거했다. 원래 Build.cs의 제품 의존성 cold build Succeeded, PID11600 Heal PIE 05:19:29.000 UTC/Guard 회귀 05:20:57.182 UTC Success, 새 PID27900 saved reload/ABP UP_TO_DATE/DevMap/dirty0. 원본 clip·기존 AnimInstance/ASC/Guard cpp/Build.cs SHA를 보존했다.

메인 Source는 적용됐다. 메인 Content 선택 copy는 SK_Player.uasset Windows sharing violation으로 실패했고 원자적 Replace도 실패했다. 기존 5개 에셋·원본 clip은 시작 hash다. 메인 editor에 MCP/UI/종료/LiveCoding을 사용하지 않았다. work PID27900은 throttle true 복원 후 정상 종료해 work editor는 없다.

10개 검증 파일은 Saved/HealImplementation_20261006/ReadyContent, before/prepared/source SHA는 ApplyManifest.json이다. Scripts/Engineering/apply_heal_20261006.ps1 validation 후 숨김 PID28144 -WaitForEditorExit를 실행했다. 최초 WaitingForEditorExit/main PID25196. 모든 메인 project editor exit 후 사용자 저장 충돌 재확인→정확한 10개 copy/hash→메인 cold build를 수행한다. editor를 강제 종료/다시 열지 않는다.

정확한 재개: Router→Architecture/Migration ARCH-75→HEAL_IMPLEMENTATION_20261006.md→Metadata/HealImplementation_20261006/ApplyStatus.json. Complete이면 AssetInstallManifest.json 10개 installed SHA와 ColdBuild_MainAfterApply.log Succeeded를 확인한 뒤 다시 연다. Waiting이면 ApplyHelper.json PID가 실제 ps1을 실행하는지 확인하고 사용 종료를 기다린다. Stopped이면 details.error의 사용자 변경/빌드 실패를 먼저 확인한다. helper가 없고 미완료면 메인 editor 종료 뒤 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Engineering/apply_heal_20261006.ps1" -WaitForEditorExit만 실행한다. author setup/graph 노드/Sequence retime/캐시 수리를 반복하지 않는다.

다음 QA는 물리 DPad→걷는 중 사용→HP50→150/150→200→회복 전 취소→InputEnd 뒤 공격/가드의 연속 화면이다. full HP에서도 모션은 실행하므로 적 없이 키를 확인할 수 있다. 적 피해/사망/UI는 별도 구현이다. 격리 결과와 메인 pending은 RuntimeResult/ChangeManifest/FinalEditorState에 분리 기록했다. main 반영 대기를 완료로 표기하지 않는다.

### 2026-10-06 — Heal 메인 반영·재시작 완료, 직접 테스트로 전환

사용자 후속 지시 “메인에 추가해줘. 직접 테스트 해보고싶어.”를 수행했다. 메인 PID25196의 정확한 project/DevMap, dirty content·map0/game world 없음과 Source·asset 충돌 없음을 확인한 뒤 정상 QUIT_EDITOR했다. helper PID28144가 exit를 확인하고 prepared 10개를 copy/hash 검증한 후 메인 cold build Succeeded/Complete(05:48:35.668 UTC,38.90초)로 종료했다. 원본 clip·검사 Source SHA 보존. 강제 종료/LiveCoding/추가 author setup은 없었다.

새 메인 PID27568 DevMap을 열고 Native Heal class/GA Montage·GE/no cost·cooldown/IA DPad Down1/Definition Heal grant1·Health init/ABP UP_TO_DATE를 읽기 전용 검사했다. MainReadyAudit의 native game world 없음/dirty0과 실제 editor 화면을 확인했고 PIE는 시작하지 않았다. 사용자가 Play→DPad 아래→보행 중 사용을 수행할 상태다. startup에는 -EnablePlugins=GameFeatures를 사용했고 config/uproject는 바꾸지 않았다.

앞선 Waiting/Prepared와 격리 검증 보고서는 역사로 보존한다. 현재 정본 증거는 Metadata/HealImplementation_20261006/MainAppliedResult.json·MainReadyAudit.json·MainReady_Editor.png·AssetInstallManifest.json·ColdBuild_MainAfterApply.log 및 ApplyStatus=Complete다. 더 이상 helper 대기/복사/build/author setup을 재실행할 필요가 없다.

다음: Router→Architecture/Migration ARCH-75→Heal 문서 메인 완료 절→사용자의 물리 DPad/걷는 상·하체 전환 화면 QA. 초기 full HP에서도 모션은 실행한다. 회복량/상한/취소/교체는 기존 격리 native PIE에서 통과했고 실제 적 damage·death·HP UI는 별도 범위다. 사용자가 이후 PIE를 실행하면 그 세션을 자동 테스트나 정리 대상으로 취급하지 않는다.

## 2026-10-06 — Heal 무기 수납·발도 진행 중

사용자 직접 요청으로 기존 Heal h/cpp와 개발 PIE test를 확장 중이다. 현재 메인 Source는 수정됐지만 메인 DLL/Content는 이전 Heal이다. 게임 기능의 최종 메인 적용 완료 기록으로 읽지 않는다. ARCH-76 착수 계약을 따른다. 시작 백업 Saved/HealWeapon_20261006/Before/Manifest.json. 작업 project C:/Users/user/Desktop/GitProject/Khazan_HealWeaponWork_20261006/Khazan. editor PID8164 / Saved/HealMailbox / Saved/Logs/HealWorkEditor.log, 메인 PID27568와 별개다.

마지막 검증: ColdBuild_Author2 Succeeded; Khazan.HealWeapon.Audit Success는 실제 SCS hand socket/0.009, 두 BackPack aux가 socket object가 아닌 Skeleton bone임을 확인했다. 두 Equip Sequence UE rename 완료, Khazan.HealWeapon.Author Success로 기존 Heal Montage Stow→Heal/새 HealDraw Arms Montage/Skeleton Arms slot/ABP cached Arms 마스크/GA DrawMontage를 저장했다. 원작 Notify timing 미확인, Stow/Draw 0.5s는 source 궤적의 접점에 둔 임시 표현값. clip 키/1s/rate1/.01 body·.009 weapon 유지.

남은 작업: native Khazan.Heal.PIE(queued 021) 결과/수리; Guard 회귀; Stock Build.cs/임시 author cpp 제거 뒤 cold build와 새 saved reload; hash 충돌 확인/정상 main editor 종료 필요 시 최소 에셋 8개 선택 반영·main build·재열람; Engineering/Animation/Art 결과 기록. 재개는 먼저 work log의 최신 Test Completed/Ready PID 확인, main Source를 이전 문서에 맞춰 되돌리거나 Author one-shot을 반복하지 않는다. 이미 생성한 HealDraw가 있으면 Author는 거부한다. mailbox project는 Windows backslash full path를 넣고 기존 response가 없는 새 request 이름을 사용한다. Python은 editor lifecycle/asset만 처리, player 이동·키 입력은 native test다. 실패 로그 1st audit build FFrameTime, 1st author build GetAllGraphs 오류는 수정돼 최종 build 성공; original 실패 로그 보존.
## 2026-10-06 — Heal 무기 수납·발도 작업 완료 (앞 진행 중 기록 대체)

기존 Heal h/cpp의 attachment snapshot/상체 수납·Heal/양팔 발도/InputEnd 우선 전환/cleanup을 적용했다. 새 runtime 파일0. 정확한 정본 Docs/Engineering/HEAL_WEAPON_PRESENTATION_20261006.md 최신 완료 절, 증거 Metadata/HealWeapon_20261006/RuntimeResult.json·HealPIE_Final.log·GuardPIE_Final.log·SavedAssetAudit_Final.json·DeliveryVerification.json·MainReadyAudit.json이다.

마지막 검증: stock work Build.cs/author cpp 제거 cold build Succeeded, work PID6008 실제 Heal PIE06:29:18.543 UTC/Guard 회귀06:31:27.946 UTC Success. saved reload UP_TO_DATE/dirty0. work editor는 원래 throttle을 복구하고 정상 종료했다. main dirty0/PIE 없음 정상 exit 뒤 prepared package7개 SHA 확인 copy/old unreferenced Equip paths2개 백업 확인 제거, main cold build06:35:05 UTC Succeeded/ApplyStatus=Complete. main PID27916/DevMap은 새 native DrawMontage·ABP·두 InGame Equip clip 실제 reload/dirty0/native game world 없음. 자동 gameplay 검사는 main에서 실행하지 않았다. 다른 editor/helper가 반영 대기 중인 상태가 아니다.

해결된 실패: FFrameTime/GetAllGraphs editor author API, fixture quaternion 정규화/graph-only StrongAttack predicate, PS mailbox Script를 plain string으로 전달. rename 후 옛 file이 없었던 것은 참조0 move의 정상 결과이며, 최초 redirector 계획·ready null row 대신 최종 manifest는 copy7/remove2다. 실패 로그는 보존돼 있다. 실행 policy는 helper process만 -ExecutionPolicy Bypass로 실행했고 전역 설정을 변경하지 않았다.

남은 후속 범위: 물리 DPad/LB/키보드와 전체 연속 화면의 전환 품질, 원작 Notify/Blend timing match, 실제 enemy hit/damage/death 연결. 구현/메인 반영 작업은 남아 있지 않다. 재개는 새 증상/요청을 정본과 현재 source 기준으로 좁힌다. Author one-shot·apply helper·클립 이동·전체 retime을 다시 실행하지 않는다. 필요 시 Metadata/HealWeapon_20261006/SourceDeliveryManifest 및 Before backup으로 변경 전후만 대조한다. player 조작을 Python으로 주입하지 않는다.
## 2026-10-06 — 첫 4종 몬스터 AI 직접 구현 진행 중

사용자 요청: DevMap에서 Idle/배회→플레이어 감지/전투 진입→nav 접근→LockOn 거리 유지/좌우 이동/대기→원작 단일/콤보 공격→재추적. 피해/피격을 연결하지 않는다. Router/Architecture v3/Migration/현재 Source·Animation 정본/Enemy saved library를 확인했다. ARCH-77의 StateTree/기존 ComboAction/공통 Locomotion 경계를 채택했다.

현재 Source: 기존 Monster class defaults/auto AI/모듈식 armor leader pose와 AIController/StateTree nodes h/cpp 4개, native Definition tags4, AIModule/StateTreeModule/GameplayStateTreeModule·plugin 연결을 적용 중이다. 새 AttackAbility/AnimInstance/Manager/FSM은 없다. 원작 Skill 전환·시간은 Metadata/MonsterAI_20261006/OriginalSkillAudit.json/AuthoringPlan.json. AI 설정은 원본 AIData 미확보의 명시적 임시 튜닝값이다.

마지막 검증: 격리 프로젝트 Khazan_MonsterWork_20261006 첫 cold build Succeeded. 별도 PID26040 public read-only intake로 네 Art BP body/장비/skeleton/scale와 DevMap floor bounds±4000을 확인했다. Heavy는 Elite empty pose carrier+armor3+weapon이며 1.3 scale, Human2종1.2/Halberd1.0을 보존한다. PID26040은 mailbox 정상 quit했다. Editor-only MonsterAuthorEditor.cpp를 work Source/Tests에만 복사해 asset authoring 빌드를 진행하고 있다. 메인 editor PID27916의 gameplay 입력/asset 편집은 실행하지 않았다.

일시 실패/보완: UE5.8 editor API의 FindFProperty/EditorGetAssetTags/public NavMovementProperties accessor/protected property reflection/shared JSON keys를 맞췄다. ColdBuild_Author.log 실패는 보존하고 ColdBuild_Author2.log가 현재 build다. asset authoring/PIE/메인 전달은 아직 완료 아니다.

정확한 재개: 현재 build log 끝을 확인→work editor를 monster_isolated_editor.py mailbox로 실행→Automation RunTests Khazan.Monster.Author→asset errors/Root track/attachment/ABP·StateTree compiled/nav 완료를 표적 확인→실제 4종 native PIE 테스트와 기존 Heal/Guard 회귀→author cpp 제거/stock Build.cs 빌드·saved fresh reload→ChangedAssets 및 protected SHA 기준 선택 전달/메인 cold build·DevMap 준비. 메인 dirty/PIE 없음을 재확인하기 전 종료하지 않는다. Scripts/Engineering의 author와 Offline manifest generator는 work-only/read-only 역할을 유지한다. Python으로 player 이동/키 입력을 주입하지 않는다.

## 2026-10-06 — 몬스터 격리 실제 PIE 성공·최종 전달 준비

Khazan.Monster.PIE 10:43:55.445 UTC Success. 네 종류의 실제 Sight/Nav/CMC/Alert/Chase/Attack/Standoff/재추적, 후보13개 모든 section, movement block 해제, UnPossess/repossess·held cleanup, HP 불변과 lateral 대치를 확인했다. 현재 Source/격리 에셋은 적용됐으나 메인 Content/DLL 전달은 아직 완료가 아니다. 정본 MONSTER_AI_IMPLEMENTATION_20261006.md의 완료 구분을 따른다. 성공 로그 MonsterPIE_AuthorBuild_Success.log, 원본 Art clip60개 main/work SHA 일치 OriginalClipHashes.json.

해결: 빈 nav brush를 public UActorFactory::CreateBrushForVolumeActor로 생성, bounds±3900/Z±300·nav projection 검증. 두 번째 PIE의 world X 배치가 배회 후 시선과 맞지 않아 actor forward/실제 nav 바닥으로 fixture 수정/20s 관측. PIE 중 외부 asset API 호출 오류도 재실행에서 제외했다. Sight config constructor 준비로 listener registration 경고를 해소했다. 실패 기록은 보존한다. 원작 SI.EndCooltime/SB TargetCondition 별도 raw 근거는 OriginalSkillContext.json이며 global AI interval과 동일시하지 않는다.

재개점: Main PID27916와 work PID27088은 별개. SkeletonSlotBaseline.json/BeforeSkeletonSlots에 현재 main skeleton3개를 backup/hash하고 닫힌 work에 snapshot했다. ColdBuild_SkeletonSlots2 Succeeded; 첫 slot helper compile namespace 오류는 해결했다. 새 work Ready PID27088 확인→Khazan.Monster.SkeletonSlots→SlotAssets.txt와 ChangedAssets.txt 합치기(재author 후 slot 누락 방지)→saved ABP/Tree/nav audit→quit/임시 author 제거/stock Build.cs 빌드→fresh native Monster·Heal·Guard PIE→protected conflict/hash/선택 main 전달·main cold build·새 DevMap 준비. 아직 최종 전달/회귀 완료가 아니다. Python은 asset/editor lifecycle만, 이동 fixture는 native C++이다.

## 2026-10-06 — HeinMach snow runtime 격리 검증 진행

새 environment Actor 한 타입의 h/cpp2파일만 work Source에 있다. KZCharacter/Player/ASC/CMC/AI gameplay 변경 없음. private RHI/CSV SnowTick, owned transient texture/MID/world tile cache, GT finalized skeletal contact와 static weapon path를 사용한다. work는 Khazan_SnowWork_20261006, 정본 HEINMACH_SNOW_IMPLEMENTATION_20261006.md. main runtime 반영·실제 contact QA 완료는 아니다.

ColdBuild_ExposedSurfaceQA Succeeded 후 own hidden verify mailbox/Khazan.Snow.PIE가 다음이다. 원작 weight255 좌표에 실제 바위가 있던 fixture 실패를 native hit 값으로 확인하고 노출 눈 표면 선택으로 수정했다. 디버거는 isolated LLDB attach 뒤 source executable mapping/stack symbols 불가로 fallback했다. own breakpoint/session 제거 완료. 다른 AI의 main Source/config/map를 오래된 stage copy로 덮어쓰지 않는다. native depth 변화+foot/dodge/air weapon/ground sweep/cache scroll/repeat/EndPlay 결과와 PNG를 확인한 뒤 latest main 대상으로 선택 전달/cold build/fresh audit한다. user live StormPass/dirty/PIE 상태는 전달 직전 다시 확인한다.
## 2026-10-06 — 몬스터 작업 완료 (앞 진행 중 기록 대체)

Source/격리 authoring/최종 제품 검증/메인 전달을 모두 완료했다. product Guard10:59:29.428 UTC/Heal10:59:57.988/Monster11:02:54.097 및 최종 capture Monster11:16:15.957 Success. 실제4종 자연행동·13후보 모든 section·cleanup·HP 불변, stock cold build·saved reload를 검사했다. slot merge/main before5 hash backup→137package 선택 install→Main cold build Succeeded→PID11000 DevMap BP/ABP UP_TO_DATE/legacy0/dirty0/gameworldNone. work PID8348 정상 exit/원래 throttle 복구. pending helper/asset copy/author/rebuild는 없다.

정확한 결과/출처/현재 Source와 다음 물리 화면 QA는 MONSTER_AI_IMPLEMENTATION_20261006.md 마지막 완료 절, RuntimeResult/MainReadyAudit/FinalHashVerification/DeliveryVerification이다. Before backup5/ReadyContent 및 AssetInstallManifest137은 증거이며 이미 완료된 install을 다시 실행하지 않는다. stock 첫 실패 cached author source와 PCH paging1455는 NoUBTMakefiles/rule timestamp·NoXGE MaxParallelActions1로 해결했으며 이전 실패 로그를 보존했다. 추가 runtime 변경은 캡처 보완 과정에서 없고 native test 카메라/restore 순서만 바꿨다. Damage/피격·원작 AIData/선택 cooldown 일치·전체 연속 motion QA는 후속 요청 범위다. User가 새로 PIE를 시작하면 해당 세션을 cleanup하지 않는다.

## 2026-10-07 — 몬스터 재개 요청의 완료 상태 재확인

사용자 재개 요청에 따라 Router→ARCH-77→Migration→Monster 정본/최신 continuity와 실제 파일을 확인했다. SourceDeliveryManifest의 13파일 및 AssetInstallManifest의 137package를 현재 main SHA256과 비교했으며 누락/차이가 모두 0이다. ColdBuild_Main의 Succeeded와 제품 Monster·Heal·Guard PIE Success 로그를 확인했다. 증거는 `Metadata/MonsterAI_20261006/ResumeAudit_20261007.json`이다.

확인 시각 00:18:34 UTC에 실행 중인 UnrealEditor.exe가 없었고 Rider UE 연결도 없었다. 따라서 이번 턴은 디스크 상태/기존 성공 증거 확인이며 새 build/PIE/에디터 reload를 수행한 것이 아니다. Source/BP/에셋을 재작성·재설치하지 않았다. 몬스터 구현/메인 반영의 미완료 단계는 없으며 다음은 메인 DevMap을 열어 Outliner `DevMap/Monster AI`의 네 몬스터에 접근·대치·후퇴하는 사용자 화면 QA다. 피해/피격 및 원작 AI 정책 일치의 미검증 범위는 유지한다.

## 2026-10-07 — Player Original 파츠/physics 격리 작업 착수

정본 PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md. 독립 Khazan_PlayerPartsWork_20261007/Khazan을 생성했으며 아직 게임/메인 에셋 적용은 없다. Scripts/Engineering/PlayerPartsAuthorEditor.cpp를 work Source/Tests에 복사하고 work Build.cs에만 editor dependency를 넣어 ColdBuild_Author.log를 MaxParallelActions1로 빌드 중이다. 첫 work PID15412는 ExecutePythonScript 자동 종료로 정상 exit했고 장기 실행은 ExecCmds=py Saved/player_parts_isolated_editor.py를 사용한다. Ready.json의 이전 PID를 준비 완료 증거로 재사용하지 않는다. 미처리 quit003은 mailbox/Archived에 있다. 다음은 build 결과→새 work PID/Ready identity→Khazan.PlayerParts.Audit→Native body/constraint/ref scale 근거로 author→실제 PIE/화면/저장 재로드→BeforeManifest의 main SHA conflict check→필요 package만 전달이다. 현재 메인 PID7220와 다른 Snow/Monster 작업 editor에 입력/저장/종료를 요청하지 않는다.

## 2026-10-07 — 몬스터 대기/걷기 수정 진행 중 (ARCH-78)

실제 원인: isolated LLDB에서 Swordsman worker snapshot의 GroundSpeed=90cm/s를 확인했다. 이후 native PIE public active player probe에서 네 몬스터 모두 실제 이동 중에도 BlendSpace X=0/Y=0, Peace Basic Loop weight=1이었다. editor author Node helper의 PostPlacedNewNode 누락으로 binding/extension 초기화가 빠졌다. 과거 자연행동 테스트 성공은 최종 포즈 입력 검증을 포함하지 않았다. 증거 Metadata/MonsterIdle_20261007/DebuggerEvidence.json·LocomotionProbe_Before.log. engine BlendSpace breakpoint는 AnimGraphRuntime PDB 부재로 매핑되지 않았으며 본인 breakpoint4개와 debugger session은 제거했다.

현재 main Source에는 Definition UnawareRoutines/placement mutual Talk roles/ComboAction read-only current node/Command.AI.Alert/Idle Loop→End·Patrol 분리·pair 동시 활성화와 loss cleanup이 적용 중이다. 새 runtime class/file0. 에셋은 아직 main에 전달하지 않았다. editor-only author는 기존 MonsterAuthorEditor.cpp의 별도 Khazan.Monster.UnawareAuthor이며 기존 전체 Author를 다시 실행하지 않는다. 원본 메타데이터 선택32clip/16routine manifest는 IdleAuthoringPlan.json. walk Stand/Move 분리·실제 VelocityLocal 방향·속도 기반 rate와 FK stance-foot 계산은 아직 build/PIE 미검증이다. 계산값을 원작 AI speed 직접값으로 표시하지 않는다.

재개점: work closed 상태에서 최신 main DevMap과 scoped Source9파일/author/plan을 Khazan_MonsterWork_20261006/Khazan에 복사했다. BeforeAssets와 AssetBaseline.json128monster+DevMap129package backup, ComboAction header 별도 backup 완료. ColdBuild_UnawareAuthor.log build가 진행 중이다. build 결과→own hidden editor launch/Ready PID 검증→Khazan.Monster.UnawareAuthor→StrideAnalysis/ChangedAssets 확인→기존 test의 DevAI_4actor 필터 및 실제 pose/방향·대기 pair 검증 보강→author 제거/stock build·fresh Monster/Heal/Guard→main SHA conflict/dirty audit 후 scoped delivery·main cold build·saved reload. 실패 baseline 자연행동 coverage1건은 보존한다. main PID7220와 Snow PID1888 등 타 작업 editor는 조작하지 않는다. Python은 editor/asset/lifecycle에 한정하며 native test만 gameplay fixture를 수행한다.

## 2026-10-07 — ARCH-78 격리 대기 검증 통과·최종 stride 검사 중

정본 MONSTER_UNAWARE_LOCOMOTION_20261007.md. PID2720 UnawareAuthor02:34:53 UTC/WaitingPIE02:36:19/MonsterPIE binding fixed02:39:15 Success. 네 Solo Loop/End·pair 동시 실행/상대 UnPossess→End/Solo·공동 발견을 검사했다. 첫 이동 검사는32mesh pose가 맞았으나 Halberd/Heavy의 target memory 만료로 explicit focus가 풀려 일부 nav8방을 실제 F로 평가했다. 전체8방 완료로 기록하지 않으며 현재 test에 지속 focus/기대 방향 assertion과 contact world-foot 기록을 추가했다.

ColdBuild_FinalAuthor Succeeded, fresh PID6836 UnawareAuthor02:44:45 Success. 평상시/전투 Stand 분리와 90° blend의 diagonal stride magnitude 보정을 저장했다. 현재 105-stride-pie.request는 Khazan.Monster.PIE 실제 이동/32pose/foot residual을 실행한다. 남은 작업은 결과 분석→필요 시 보정→own quit/throttle restore→work-only author cpp와 editor deps 제거/stock cold build→fresh saved reload/Waiting·Monster·Heal·Guard→선택 hash 전달/main dirty audit·cold build/DevMap 재로드다. Main7220는 read-only audit에서 DevMap/PIE없음/dirty0이었다. Snow8592 등 다른 editor를 종료하지 않는다. Source/에셋 main 최종 반영은 아직 완료 아니다.

## 2026-10-07 — HeinMach Snow / collision 보완 중간 체크포인트

사용자 direct 구현 요청의 격리 상태는 Art continuity 2026-10-07 눈 변형 절과 `Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md` 기존 계약을 따른다. 새 runtime 파일은 level presentation Actor h/cpp 2뿐, dev test 1. Character/ASC/Locomotion/AnimInstance 상태나 수명을 추가하지 않는다. 최신 main Monster Source 8 파일을 격리로 다시 받았으며 C4458 Role shadow / UGameplayAbility incomplete type 때문에 **main Monster.cpp에 include 한 줄과 local RoutineRole 이름 보완만 실제 적용**했다. 사용자의 Unaware/Talk/Patrol 동작은 보존한다.

Stage의 actual PIE 02:26:18 UTC Success에서 Player run/dodge, actual attached weapon air/ground, actual BP_Monster_Swordsman foot/lying torso MOVE_None, GPU dent/collision agreement, repeated/cache restore/EndPlay material cleanup를 확인했다. 별도 authored knockdown ability/physics ragdoll 완료 검증이 아니다. Nanite terrain proxy가 collider와 어긋났던 문제는 MaxEdgeLengthFactor2 + high precision/full fallback/own recook로 해결됐으며 상세 native failure/success log를 보존했다.

최신 Actor cpp는 toroidal texture를 쓴다: world tile modulo addressing / overlap 유지 / 새 strips만 publish / zero tile 128 KiB를 여러 regions에 공유해 full 32 MiB CPU clear를 제거 / clear command 먼저 enqueue 후 nonzero upload. material FIELD_CODE v2와 같은 계약이며 cold build 성공, **최적화 후 runtime/성능 결과는 pending**. field ownership/lifetime은 기존 Actor/weak contacts/MID restore와 같다.

낮은 stone dressing 17은 level component에서만 Pawn Ignore + navigation false. source geometry/shared mesh/Character CMC를 전역 변경하지 않는다. CPU/GPU field는 gameplay collision/nav를 프레임마다 deform하지 않는다. 렌더 눈층이 substrate까지 눌리므로 character collision은 stable substrate에 남는다. Nav rebuild/save 및 actual 이동 보완은 아직 최종 검증 전이다. MainSource/DLL/48 snow assets/map 전달은 아직 미완료; live PID7220에 자동 hot reload/닫기/SaveAll/PIE를 하지 않는다.

## 2026-10-07 — Player Original 파츠 중간 검증 / 보조 물리 단위 보정

세부 정본: `PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md`의 최신 절. 메인 에셋 전달은 아직 없음. 작업 경로 `C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan`. own PID20820 정상 종료와 throttle restore 완료, debugger detach/agent breakpoint 제거 완료. Author 첫 성공, PIE assertion 성공은 화면/bounds 실패로 기각했다. 재개 시 `Metadata/PlayerParts_20261007/ColdBuild_Author7.log` 성공 확인 후 ExecCmds mailbox로 별도 work editor 실행. 013 이후 번호로 Author → 강화된 PlayerParts.PIE → own end PIE → Guard/Heal → 신규 프로세스 재로드 → BeforeManifest와 현재 main hash 일치 확인 후 필요한 에셋만 전달한다. 현재 main BP_Player/ABP_Player/Original PA를 덮어쓴 적 없으며 mesh/skeleton/source/config/map/Imperial은 변경하지 않았다. hardlink Content의 Player/Character 밖 패키지는 절대 저장하지 않는다.

## 2026-10-07 — ARCH-78 제품 검증 통과 후 Foot Placement 보완 진행

격리 stock fresh PID26160: WaitingPIE 03:17:06 / Monster.PIE 03:24:28 / Heal.PIE 03:27:08 / Guard.PIE 03:29:08 UTC 모두 Success. 로그 MonsterPIE_Product.log / PlayerRegression_Product.log. 실제32방향 nav/BlendSpace 최종 pose/marker/rate가 통과했으나 골 발 joint의 낮은 contact-band median drift는 대각선에서 일부20~69%까지 남았다. 이를 무발밀림 완료로 표기하지 않는다. 기존 engine Foot Placement + Leg IK를 Walk branch에만 보완하는 계약을 Architecture ARCH-78 하단에 추가했다. native 새파일0; 기존 AnimInstance에 engine parallel 평가 정책 bool+override만 추가(플레이어 false 유지, NPC true). 바닥/owner를 읽는 엔진 평가를 GT로 한정한다.

현재 main assets 미전달. PID26160 normal quit/throttle true 복구, work-only author를 Source로 복원하고 AnimationWarping plugin/temporary author dependencies만 work에 적용했다. ColdBuild_FootPlacementAuthor.log 빌드 session19977 진행 중이다. 스켈레톤 기존 bone/slot/socket 보존을 위해 Virtual Bone target L/R만 추가 예정; 세 스켈레톤 main/work SHA 일치 baseline/backup은 SkeletonBaseline.json과 BeforeAssets, 기존 126prepared asset manifest와 baseline4BP supplement도 보존했다. FootBeforePlacement/32csv는 이전 실제 drift 근거다.

재개: author build 결과→own hidden fresh editor/Ready PID→Khazan.Monster.FootAuthor(전체 Author/UnawareAuthor 재실행 불필요)→FootChangedAssets/StrideAnalysis_FootPlacement 확인→강화 Monster.PIE(실제 contact curve와 IK 미제어 bone pose 확인, world-foot drift 개선)→필요 시 보완→own quit→author Saved archive 이동·stock rules timestamp 갱신/build→fresh Waiting·Monster·Heal·Guard→saved audit/hash scoped delivery 및 main dirty/PIE 확인 후 통합. Main7220/다른 Snow/PlayerParts editor는 아직 조작하지 않았다. 다른 작업의 Source/config/map을 덮어쓰지 않는다. virtual bone/curve/Foot node의 수치와 의미는 원작 직접값 아닌 계산/엔진 기본 표현 설정으로 기록한다.

## 2026-10-07 — Player Original 파츠 최종 재개 지점: Windows main file lock 4패키지

- 작업/검증 자체 완료: PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md 최신 절과 Verification.json 참조. PID13368 final Author/physics/Guard, stock PID17564 NullRHI Heal+actual config readback 성공. own editor 정상 종료, user PID7220는 그대로다.
- 현재 main 14 중10 SHA 완료. 남은 BP_Player/Torso·Leg·Hair Original PA4개는 before SHA이며 exact prepared pending 파일 있음. Restart Manager FileLocks.json은 main PID7220 하나를 반환. main Blueprint 부착 완료로 승격하지 말 것.
- 사용자에게 main 작업 저장 후 종료를 async 요청했다. main 종료 후 cwd=C:/Users/user/Desktop/GitProject/Khazan/Khazan에서 `& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' 'Scripts/Engineering/deliver_player_original_parts.py'` 실행. journal 재개 가능: already delivered10을 보존, pending digest 확인, 남은4만 atomic replace, 마지막 BP_Player 저장. complete=true/14 of14 및 각각 target SHA=prepared 확인.
- current main hash가 baseline과 달라졌으면 script가 conflict로 중단한다. 사용자 저장 내용을 덮어쓰지 말고 latest main BP/PA를 independent work에 들여 SCS/physics 변경만 다시 author/PIE·stock reload 검증, 새 baseline 작성 후 전달. unrelated Source/Config/Map/Imperial/hardlinked content는 저장/복사하지 않는다.
- completed append를 State/Physics/전용정본/continuity에 남긴 뒤 사용자에게 main 재시작 확인 안내. 원작 physics 파라미터 동일성/네트워크/hardware 연속검증은 완료로 기록하지 않는다. 이미 성공한 임포트/build/native tests를 근거 없이 반복하지 않는다.

## 2026-10-07 — Snow 최종 전달 직전 체크포인트 12:59 KST

- 저장본 SceneFinalAudit 통과: 9,869 actors, 기존 9,868 pose 동일, snow46/material2, micro dressing65, fire258, route wall2,281, NavBounds242/Null26/Links24. Main baseline SHA f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442 그대로다.
- Recast 원작 MoveTo63/points1,485/segments1,422 모두 통과. 표적65개의 Pawn만 제외한다. private 이전 작업의 미기록16개는 main 원본의 응답/nav/tag로 복구했고, 81 component의 8개 노출 표준 collision channel을 원본 대비 저장/reload 검사했다. 프로젝트 custom channel 설정 없음. CollisionChannelsPreserved.json 참조.
- native Khazan.Snow.PIE 최종 Success 2026-10-07 03:57:20 UTC: Player run/dodge, 실제4종 Monster 발/누운 torso/원본 장비 weapon bone vertex, air negative, GPU 깊이14.5cm, Nanite/fallback substrate<1cm, 반복/창 이동 이력/EndPlay material restore. Torso와 장비의 독립 pose fixture이며 실제 gameplay knockdown montage 검증은 아니다. Foot reach12cm 유지; 측정 minToePivotGap=-7.954cm. 회피 fixture는 눈 위 재배치 및 실제 Ability 종료/착지 대기. writer 접촉 판정 자체를 임의 완화하지 않았다.
- Native CPU CSV: baseline warm mean .5019ms/p95 .8648ms; toroidal 최초 cold run .1.7657ms/p95 4.2218/max51.2731, 3개 editor/페이지·skinned asset compile 영향. shipping FPS/GPU 비용 확정으로 쓰지 않는다. 변경 없는 겹친 GPU tile 유지, 새 strip만 upload, full-clear는 공유 zero tile region batch, CPU/GPU48/32MiB budget.
- 별도 Player Original parts/Monster 변경 보존. Main PID7220 DevMap, PIE없음/dirty0를03:58:49 UTC read-only 확인. own PID26584 정상 종료. Main KZAnimInstance.h와 Monster dev test의 최신 변경을 수령해 ColdBuild_LatestMainFinal 진행 중. Main Snow source/assets/map 아직 전달 전이다.
- 재개: 위 cold build Success 확인 → Source snapshot/map hash 변경 없음 확인 → Scripts/Art/heinmach_snow_deliver.py(48native+map+Source3+RHI/Nanite+manifest-selected DLL) → heinmach_snow_launch_main_verify.py로 main 별도 백그라운드 reload/PIE. user 기존 DLL/에디터는 유지하며 새 class 확인은 재시작 필요. 동일 prefix의 HotReload suffix DLL을 추가하지 않는다. MainVerification success 이후 정본/State/continuity에 완료 추가. delivery 도중 lock이면 정확한 pending/backup/hash를 기록하고 user 편집을 덮어쓰지 않는다.
- source shader/HLSL 및 원작 같은 프레임 snow 변형 비교는 미확보. radius/접촉/rim/압축색/roughness/cache는 명시된 native 임시값,15/7.5는 원작 계수의 native cm 해석이다. 원작 cm 실행 직접 검증 또는 픽셀 동일 완료로 기록하지 않는다.

## 2026-10-07 — 접지 첫32방향 성공 / 제품 fresh 재검증 준비

FootAuthor pin수정 후25640에서 03:40:36 UTC Success, 실제 Monster.PIE 03:47:30 Success. 32nav방향은 최종 Walk sample/위상·속도·미제어 pose/GT 평가/접지 curve/13공격과 cleanup을 통과했다. FootPlacementFirst/32csv의 각 contact-band median 발 joint drift 최대0.011558448cm/s, min sample4이다. 접지 시작/끝과 같은 개별 frame 속도는 이 중앙값과 구분한다. 최종 시험은 유한차분의 양 끝 frame 모두 contact일 때만 접지 interval로 분류하고 1cm/s median 기술적 QA 기준·실제 diagonal camera4를 추가했다. 이는 gameplay 임시 튜닝값이 아니다.

ColdBuild_FootPlacementProduct 44action/Succeeded 및 Author Source 제거/stock Build.cs 일치 확인했다. 추가 원본 보존 audit에서 기존 10/6 hash 중 Swordsman BasicLoop01 하나와 이번 선택11 Swordsman source disk가 main/work에서 다름을 확인했다. main 변경 timestamp는01:36~01:43 UTC(이번 source 수정/LLDB 전에 존재)이며 예시 End03는 main root motion=true, RateScale1/70keys/69frames다. Main Art를 과거 파일로 되돌리지 않는다. OriginalWaitingDiskDifferences.json을 보존한다. source bytes의 동일성으로 현재32원본의 포즈 보존을 주장하지 않고 native SourceAnimationAudit가 최신 main을 임시 read-only mount로 읽어 raw key/FPS/RateScale를 비교하도록 했다. 첫 audit는 runtime-init CharacterDefinition을 CDO에서 읽어 null이었던 fixture 오류로 Fail(SourceAudit_CDOFailure.log); explicit DA_Character 로드를 사용하도록 test만 수정했다. RF_Transient package API 컴파일 오류도 개발 test에서 수정했으며 게임 구현 오류로 확장하지 않는다.

현재 own15440 normal quit/throttle 복구, ColdBuild_ProductSourceAudit3.log(1test cpp incremental) 진행, 다음125 이후 request로 fresh 제품 editor→SourceAnimationAudit→WaitingPIE→Monster.PIE→Heal/Guard→saved audit/hash 검증이다. Native author runtime source는 없고 FootChangedAssets와 prepared129(79new/50existing) plain JSON/ReadyContent sha 일치, conflicts0. Main7220 최신 read-only audit에서도 DevMap/PIE없음/dirty0이었다. Main에 새asset/plugin/DLL을 전달하지 않았다. 남은 단계와 Main scope는 이전 절을 따르며 다른 Snow/PlayerParts 변경을 보존한다.

## 2026-10-07 — Monster 대기/보행 메인 반영·접지 마지막 한 경우 조사

Main7220의 DevMap/PIE없음/dirty0를 확인하고 정상 종료한 뒤, baseline 충돌0인 scoped129패키지(79new/50existing)를 04:16:32 UTC 반영했다. 준비 SHA 일치, 원본32 waiting clips의 현재 main hash 보존을 확인했다. AnimationWarping plugin만 명시적으로 enabled 추가. Main cold build 재시도는 21action/120.91초/Succeeded; 첫 startup 종료1 로그는 보존하고 실패 원인을 임의 확정하지 않는다. Main PID17552를 사용자의 직접 테스트용으로 정상 표시 재실행했고 04:27:15 read-only MainReadyAudit는 DevMap, 10몬스터/정확한4 Solo/상호 Talk pair/Patrol1/NPC GT evaluation=true, PIE없음/dirty0를 확인했다. 메인에서 자동 PIE는 하지 않는다.

Own stock PID8248 SourceAnimationAudit 04:04:42/WaitingPIE 04:06:15 Success. 마지막 Monster 첫 실행은 관측 script의 PIE 중 editor-world API 호출 오류 때문에 Fail였으며 구현 assertion은 통과했다. 관측 오류를 제거한 04:23:22 실행은 31방향 통과, HalberdElite case1의 접지 ankle median2.117039803cm/s(14 samples)가 기술 QA<1cm/s를 넘겨 Fail이다. 완료/32방향 전부 성공으로 기록하지 않는다. MonsterPIE_Final_ContactFailure.log와 해당32 CSV를 보존하고 virtual target/실제 ankle/toe의 read-only GT 관측으로 잠금·heel 보정 원인을 좁히는 중이다. AnimationWarpingRuntime engine PDB가 없어 내부 평가 breakpoint mapping은 사용하지 못한다. GameThread pose bool/기존 clip/rate를 무작정 바꾸지 않는다.

재개: own131-support-native 실행 종료 후 Saved/MonsterIdle/FootSupportDiagnostic.json 분석 → 필요한 최소 보완 및 scope별 검증 → 최종 Heal/Guard 회귀 → 원본/129 SHA와 saved audit → own motion blur3/background throttle 원상복구·정상 종료 → 실제 결과를 정본/State/Migration/Animation 하단에 추가. Main 현재 reopen/root/audit는 위와 같으며 사용자가 PIE 중이면 editor-world 조회/저장/종료를 수행하지 않는다. Snow/PlayerParts의 별도 변경을 보존한다.

## 2026-10-07 — Monster 접지/회귀 후속 재개: 저장본 재로드 PID26976

131-support-native는 04:33:35 UTC Success, 32 contact CSV median 최대0/min sample4였다. FootSupportDiagnostic(발목/발끝/Virtual target read-only 관측)을 보존했다. 직전 case1 2.117cm/s 실패는 폐기하지 않는다. Halberd F/R204 raw plane samples의 contact mask0/2와 Foot Placement 입력 plane을 표적 대조한 HalberdInputPlantPlane.json은 stance 최대3.023136611 component cm/ground default10 초과0을 확인했으며, 모든 blend frame의 내부 plant branch를 디버거로 관측했다고 주장하지 않는다.

Halberd 기존 Foot Placement 한 항목 MaxExtensionRatio0.5→1.0을 명시된 임시 표현 설정으로 시험한다. GetMaxLimbExtension의 남은 bone-chain 길이를 전부 사용하는 비율이며 뼈 길이를 새로 확대하지 않는다. 135 Python 작업은 property notify와 즉시 compile이 겹친 BlueprintCompilationManager QueuedRequests ensure/CDO 오류로 04:37:09 종료됐고 saved ABP SHA는 준비본 그대로였다. EditorCompileQueueFailure.log 보존, 메인 변경/에디터 종료 없음. fresh PID20960에서 notify NEVER로 설정→다음 request에서 compile/save 분리해 04:41:57 성공. normal quit/render3/background throttle true 복구 확인. Source author helper에도 같은 한 항목을 기록했다. 아직 Main ABP에 이 보완은 미반영이다.

Heal 첫 회귀는 2.7초의 고정 observer에서 actual Draw 시작을 놓쳐 Fail(HealPIE_ObserverTimingFailure.log). 게임 Heal 로직 변경 없이 개발 테스트가 Stage9/11/13/15의 실제 HasInputEnded handoff를 기다리도록 보완했다. Monster 개발 test는 HalberdPIE 별칭으로 같은 nav8/공격/cleanup fixture를 재사용하고, 전체 다리가 보이도록 임시 camera가 Actor 중심을 바라보게 했다. ColdBuild_ObserverCondition(5action/23.79초) 및 ColdBuild_FinalCamera(4action/10.86초) Succeeded. native author Source/dependencies는 여전히 없다.

현재 fresh stock PID26976/MonsterMailbox141 saved reload 감사 준비 중. 이어142 Monster.PIE → HalberdPIE → Heal.PIE → Guard.PIE(서로 PIE 종료 확인 후 순차) → saved/129 hash·original32 보존/clear native captures·contact 수치 기록 → Main17552 PIE/dirty0 재확인 시 정상 종료, 보완 ABP1만 baseline 충돌검사 후 전달·Main 개발 test2cpp cold build·사용자용 정상 표시 재실행 → own render3/throttle true 정상 종료 → 완료 MD 추가. 메인 자동 PIE를 하지 않으며 사용자의 dirty/PIE 상태를 강제 정리하지 않는다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

Snow 자체의 메인 Source3/RHI/Nanite/48assets/map/aliasDLL 전달 완료, final main PID27452 Khazan.Snow.PIE Success04:22:07 UTC와 source/module SHA passed. 최신 Actor cppSHAa0b29dec3a1ab141fb5ffbd76e20af4cb93f32927e3efcb4d0981b6bb12afe97, aliasDLL c7670337...2e2f859ac6af0e3ce, map4560f07a...2cfda8256129. FinalVerification20261007.json과 HEINMACH_SNOW_IMPLEMENTATION_20261006.md 마지막 절이 재개 정본이다. native foot/toe·4family/body/actualequipment/airnegative/depth/cache/repeat/EndPlay 통과. 앞선 두 main Dodge 실패는 보완 전 기록으로 보존한다.

65 supported micro stone Pawn/Nav 제외, 표적 외 private16개 복원,81×8 표준 collision response 저장/reload passed. 원작63 MoveTo/1,485point/1,422segment passed. actual CMC 표적 차분RMS17.23% 감소. 마지막 CSV1094 active mean.9884/P95 3.0408ms; shipping GPU/전체FPS 및 모든 knockdown/attack montage parity는 미검증이다. Original shader/same-frame 미확보/2D cache budget 한계는 유지한다.

Snow own background editor 정상 종료; 새 main17552(독립 작업이 실행)를 read-only 관측해 native class/DevMap/dirty0/PIE없음 확인, 사용자 Play 준비 상태는 변경하지 않았다. initial deliver.py 재실행 금지. 후속 Source 수정 시 최신 main Source/Config를 snow stage에 받아 필요분만 유지→stage ColdBuild→update_module.py가 current ownSHA/다른 runtimeSource를 검증해 ownalias만 갱신→launch_main_verify.py로 background main QA. 타 작업의 Monster dev test snapshot 차이는 명시해서만 제외하며 runtime Source 차이는 수령 후 재빌드한다. 일반 DLL을 이전 snapshot으로 덮어쓰지 않는다. 다른 Monster foot/PlayerParts pending 진행은 그 정본을 따르며 여기서 완료로 읽지 않는다.

## 2026-10-07 — Monster 최종 완료·재개 기준

마지막 SourceAudit32/879799(04:04:42), Waiting(04:06:15), stock Monster32(04:53:47),12FPS Halberd8(04:58:01), Heal(04:59:37), Guard(05:00:48) 전부 Success. final contact32/min11·반복8/min12의 최대 case median0.0cm/s이며 이전2.117 실패/관측 API 오류/compile queue crash는 삭제하지 않았다. source author 및 extra dependencies 없는 제품 테스트다. Halberd Foot ratio1 한 항목/실제 handoff를 기다리는 Heal 개발 test/재사용 Halberd test alias·camera 범위 보완이 마지막 diff다. scope·provenance·실패 보존은 MONSTER_UNAWARE_LOCOMOTION_20261007.md 완료 절을 읽는다.

Main17552 clean normal exit 후 Halberd ABP1만 before/candidate SHA 충돌검사·backup 후 적용, 최종129 준비 SHA·원본32 hash 보존. Main cold build 상대경로 실패 로그를 보존하고 절대 경로5action/27.82초/Succeeded 재시도했다. Main26644 정상 표시 재실행→05:05:41 read-only FinalMainReadyAudit: DevMap/10몬스터/4 Solo/mutual Talk01·02/Patrol1/NPC GT/Player false/Halberd ratio1/PIE없음/dirty0. 자동 main PIE 없음. own26976 render3/maxFPS0/throttle true 복구·05:03:45 정상 종료, live process는 사용자용 main 하나다. 전달/author/helper/추가 빌드 pending 없음.

결과 RuntimeResult.json/MainAppliedResult.json(status Complete), FinalMainHashVerification.json/FinalPreparedAssetManifest.json/FinalSavedAudit.json/FinalMainReadyAudit.json, 실제 PIE logs/FootFinal·FootHalberdRepeat·FinalCaptures. 새 C++ runtime 파일·Ability subclass·Component·Manager0의 의미이며 data-only ComboAction GA16/ComboDefinition16/Montage16은 루틴 데이터로 생성했다. 다른 Snow/PlayerParts 기록·source/assets를 덮어쓰지 않았다.

다음 재개는 사용자의 새 증상에서 시작한다. 먼저 Router→Architecture→Migration→이번 정본 최신 완료 절/metadata→해당 Source를 읽는다. DevMap 직접 Play 시 DevAI_Swordsman Guard/DevIdle_Basic·Search·Sit/Talk01·02/Patrol을 확인한다. 이미 성공한 전수 author/retime/전체 전달을 반복하지 않으며 원작 AI 전체·피해/피격·네트워크·all terrain/sole vertex/hardware QA를 완료로 확대하지 않는다.

## 2026-10-07 — Player Original 파츠 Main 통합 완료·재개 기준

사용자 요청의 메인 통합은 완료됐다. 이전 10/14·PID7220 잠금4개 pending 절은 당시 이력이며 현재 DeliveryManifest complete=true/14 of14다. 새 메인 PID8292/DevMap에서 Original5 SCS·메시/PA/ABP·본체 기존 설정·BP/ABP compile status를 read-only 확인했다. MainReadyAudit의 마지막 상태는 PIE 없음/dirty0. FinalMainHashVerification은 prepared14개 SHA 일치, Source84/Config5/uproject1/DevMap·본체ABP·본체PA3/Binaries2의 보호95개 unchanged다. 제품 Source에 PlayerPartsPIEEditor.cpp를 넣거나 작업 DLL을 이관하지 않았다.

재개 시 Router→Architecture→Migration→PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md의 최신 Main 완료 절→Metadata/PlayerParts_20261007/{DeliveryManifest,MainReadyAudit,FinalMainHashVerification}.json을 본다. 완료된 author/shape 보정/14패키지 전달을 반복하지 않는다. 다음은 열린 DevMap에서 사용자가 직접 Play해 Original 머리·망토·옷자락의 이동/회피/Guard/Heal 연속 화면을 확인하는 것이다. 새로운 증상이 있으면 현재 PID/PIE/dirty를 다시 확인하고 해당 파츠·구간부터 표적 진단한다. 앞선 격리 test 성공, 이번 메인 저장본 load/config/hash, 아직 미확인인 원작 physics 일치·hardware 연속 QA를 구분한다.

## 2026-10-07 — Player Original 파츠 메인 최종 완료 / 잠금 대기 해소

사용자 후속 Main 반영 요청으로 main26644 clean/PIE Idle을 재확인하고 정상 종료→guarded delivery 재개→main8292 DevMap 재실행했다. BP_Player·Torso/Leg/Hair Original PA를 포함한14/14 target SHA가 prepared와 일치한다. MainIntegrationResult.Status=Complete, MainReadyAudit.Success(Original5 CharacterMesh0 parent/mesh·PA·ABP/relative1/no world simulation/본체 PA/6 BP UP_TO_DATE/dirty0/game world 없음), 보호95파일 SHA 보존이다. 자동 main PIE/강제 종료/SaveAll/격리 Source·DLL 전달은 없었다. 이번 완료 절이 이전 “main7220 lock4 pending” 재개 지점을 대체한다.

현재 main8292만 열린 사용자용 DevMap이다. PlayerParts 전달/빌드/helper cleanup pending은 없다. 기존 Physics/Guard/Heal 실제 검증은 격리 로그이고 이번 saved reload와 구분한다. 다음은 열린 DevMap에서 사용자 Play/연속 화면 확인 또는 새 증상에 대한 표적 조사다. 완료한 author/전체 delivery/검증을 반복하거나 work DLL을 main에 복사하지 않는다. 발생한 새 사용자 변경을 보존하고, root scale/mesh import 조건이 변하면 joint unit 보정을 먼저 재감사한다. 정본 PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md 최신 완료 절과 Metadata/PlayerParts_20261007/{MainReadyAudit,MainIntegrationResult,DeliveryManifest}.json 참조.

## 2026-10-07 — Player 파츠 몸 관통/잔흔들림 후속 착수

사용자가 실제 physics 동작은 정상임을 확인하고 몸 관통 방지와 아주 소폭의 빳빳함/찰랑거림 감소를 직접 요청했다. 기존 CopyPose/RigidBody와 derived PA3개를 재사용한다. 현재 main8292를 조작하지 않고 기존 PlayerPartsWork를 최신 main Source/Config/uproject·Player/Character 독립복사로 갱신했다. work Build.cs에만 기존 editor dependency를 유지하며 RHI 등 현재 main 의존성도 보존했다. BodyCollisionTuning/BeforeManifest와 Before에 derived PA3 baseline/backup, SourceSnapshot.json에 최신 Source/Config SHA를 보존했다. main 제품 Source/DLL/BP는 미수정이다.

원작 Player PA/감쇠/constraint metadata는 현 Engineering 저장 기록과 Desktop 카잔/프로젝트 추출 자료에서 아직 확인 못 했다. 별도 정본 위치를 async 질문했으며 미확인 값을 원작으로 표시하지 않는다. 현재 work ColdBuild_CollisionAudit.log(1action 병렬도)로 editor-only CollisionAudit를 빌드 중이다. 다음은 own mailbox032부터 독립 editor→CollisionAudit의 실제 BodyCollision response/disable pairs/몸 bone coverage/drive 확인→필요한 몸 Kinematic colliders와 충돌쌍만 derived PA3에 보완·명시된 소폭 damping tune→실제 PIE contact/관통/잔움직임·화면·공격/Guard/Heal 확인→stock saved reload→main baseline 충돌 확인 후 선택3 전달·clean main 정상 재시작이다. 기존 root100 joint Pos1/Pos2 보정과 shape 단위를 유지한다. 다른 Content hardlink/Source/DLL/맵/Imperial에 저장하지 않는다.

## 2026-10-07 — 몸 충돌 후속: 엔진 외부 충돌 소스로 범위 확정

독립 native CollisionAudit(05:53 UTC, own PID22524)은 Torso15/Leg32/Hair21의 모든 내부 쌍105/496/210이 비활성임을 확인했다. part ref skeleton에는 일부 몸 뼈 자체가 없어 해당 PA에 몸을 복제하는 대신 기존 engine AddClothCollisionSource(actual Mesh, Player_PhysicsAsset)와 RigidBody bUseExternalClothCollision을 사용한다. BP_Player 기존 ConstructionScript에 세 등록 호출을 삽입하고 기존 실행 링크를 보존한다. 변경 후보는 기존 derived PA3/part ABP3/BP_Player1, 제품 C++0이다. BeforeManifest/Before는7패키지다. 초기 snapshot 이후 Main BP가06:07UTC 저장돼 이전 work와 달랐으므로 최신 saved main을 work에 다시 가져와 변경을 보존했고 CurrentBPRebase에 기록했다. 메인8292 및 다른 Snow 독립 프로세스는 건드리지 않는다.

선정값은 원작 직접 확인이 아닌 명시적 임시 튜닝: linear damping0.01→0.05, angular0→0.35(s^-1), collision capsule radius cloth1cm/hair0.75cm. 원래 자동 맞춤 캡슐을 mass-only로 유지하고 nonmass 얇은 contact proxy를 추가해 질량/관성/관절 각도 제한을 유지한다. 본체 PA와 원본 Original PA는 수정하지 않는다. Scripts/Engineering/{PlayerPartsAuthorEditor,PlayerPartsPIEEditor}.cpp를 work Source/Tests에 복사했고 외부18 collider 크기/현재 pose/contact/mass 관측을 추가했다. 첫 incremental build는 QA의 ClothCollisionSource.h include 누락으로 실패(로그 보존); include 보완 후 재빌드 중이다. 다음: 독립 baseline PIE(접촉0 예상 실패 보존)→CollisionAuthor→PIE/렌더 검증→stock saved reload→7선택 메인 전달. 아직 에셋 author/main 적용 전이다.

## 2026-10-07 — Snow broad brush private build·saved tuning, main 미반영
private AKZSnowDeformation h/cpp에서 radius/reach 기본값을 확대하고 WeaponContactHeightCm를 추가해 weapon radius와 vertical trace reach를 분리했다. broad brush quarter-min-radius spacing/누적한 previous position, tile별1회 lookup/변경 tile만 dirty로 큰 범위 비용을 제한한다. 새 runtime 파일0. ColdBuild_BroadBrush20261007 및 ColdBuild_BroadBrushQA20261007 Succeeded; 추가 native QA는 실제 blade보다 떨어진(60,50)cm 지점의 압축>0.1을 확인한다. 숫자는 user look 요청에 대한 assistant 임시 설정/기술 간격이고 gameplay tuning이 아니다.
현재 own background private PID24332, Saved/SnowMailbox/Ready.json session=b9d90bfa53fc4ce1b5277e7c77d4d5af. fresh Ready PID/session을 확인하고 Scripts/Art/heinmach_snow_request.py로만 접속한다. Automation RunTests Khazan.Snow.PIE는 helper가 TestStarted 뒤 PIE를 재생한다. main8292 DevMap/PIE없음/dirty content1/map0를 read-only 관측, 건드리지 않는다. private map SHA b9802151fccf3fd5d4c21073506014f7cba8d5d532be703d06b12c47d1b76b00, main baseline4560f07a...6129. BroadBrush20261007/Backup에 main Source3/map/modules 원본 보존. main Source/map/DLL 아직 이전 상태다.
다음: verify.log 실제 Success→StagePIEPassed.json/PNG/CSV 증거 보존→own editor 정상 quit→heinmach_snow_broad_brush.py publish(guarded ownSource3/map + new UnrealEditor-KhazanSnowBroad20261007.dll + manifest; normal loaded DLL 보존)→launch_main_verify.py로 fresh background main actual QA. 현재 user editor에는 새 UPROPERTY layout이 없으므로 완료 후 사용자가 저장·재시작해야 한다. Source/API 충돌 또는 현재 main mapSHA 변경 시 강제로 덮어쓰지 않고 최신분을 private에 합쳐 재검증한다.


## 2026-10-07 ? Enemy ?? ????? ?? ????? ?? ? Chase ??

?? Architecture ARCH-78 ?? ??? MONSTER_UNAWARE_LOCOMOTION_20261007.md ?? ?? ?? ???. Main8292? ??/test??? ???? ???. ?? ?? MonsterWork? ?? Source84/Config/uproject/DevMap/ST/PlayerParts14? ?? ??3??? atomic copy??. baseline/backup? Metadata/MonsterCombatPolicy_20261007/{BeforeManifest,Before,WorkSnapshot}. ?? main Source/Content? ?? ?????.

Work? Controller h/cpp?? SightLostAt? ??/leash ?? BattleTarget ??? ???? weak target ???/lifetime cleanup? ????. Standoff Tick? ??/CanAttack ?? ?? ??, ?? timer ????? ? ??? local goal ??, Enter Tick0? ? nav ??? ?? ?? ????. ?? ?? test ??? CombatPolicyPIE? ????. ColdBuild_Work.log ?? ??? first Build.bat mutex wait? ?? ?? build ?? ? ????. ??? ?? BP ?? ??? ??? ?? ? gameplay tune ??.

??: Work build ???work-only MonsterCombatPolicyAuthorEditor.cpp? ?? Source?? ?? incremental compile?Scripts/Engineering/monster_isolated_editor.py ExecCmds mailbox hidden NullRHI editor?monster_combat_policy_assets.py(Definition2 Basic-only/Halberd02 InGame2)?CombatPolicyAuthor(existing Montage1)?author Source ??/stock ????fresh same-root mailbox?CombatPolicyPIE(4? ?? Sight/End, standoff ??, sight/leash ? memory ?? ?? ??, ?? ?? ? Chase, UnPossess cleanup)?saved readback/hash?main ?? baseline/dirty/PIE ??? ? source4/package5? ?? ???main cold build?? DevMap. ?? helper/DLL? Main? ???? ??? ?? PlayerParts physics ??? Source/??/???? ????. build/test ?? ??? ???? ??? ?? ?? ??? PID? ?? ????.

### 후속 검증 에디터 시작 지연 (2026-10-07)

ColdBuild_ExternalCollision_IncludeFix는4actions/47.91s Succeeded. own NullRHI26160은 TurnkeySupport DLL load 마지막 로그 뒤 수분간 진행하지 않아 native debugger attach→GameThread pause를 확인했으나 엔진/OS symbols 불충분으로 stack1개 주소만 나왔고 locals가 없었다. ntdll.dll offset0x160E44 위치라는 OS module 매핑까지만 확인했으며 root cause를 확정하지 않는다. 기존 사용자 exception breakpoint8개는 동일opaqueID로 개별변경 불가라 전부 보존했다. agent breakpoint 생성0, STOP detach 후 sessions0 확인. package load/author 전 own26160만 identity guard 후 종료; 다음 own23800에서도 같은 시작 지연, 로그2개 보존. main8292/Snow/Monster 프로세스 제어 없음. 현재 Offscreen 방식 ownPID는 OwnRenderedEditor.json을 보며 최신 Ready PID 일치 확인 후034 baseline PIE→035 종료→036 CollisionAuthor로 진행한다. 아직7에셋 author/main 전달은 없다.

### 2026-10-07 — 접촉 baseline과 author 핀 보완

직접 K2 class import를 제거하고 기존 FEdGraphUtilities paste/reflection 경로로 바꾼 ColdBuild_ReflectionAuthor(4actions/28.90s) 뒤 own27492 NullRHI가 정상 시작했다. startup 차분에서 도구 의존성이 원인 후보지만 engine/OS 내부 stack·locals 증거가 없어 단일 root cause 확정으로 표현하지 않는다. Baseline native PlayerParts.PIE(06:24:19 UTC)는 Hair/Torso/Leg contacts0/impulse0을 직접 기록했고 대표 mass1.645364/12.054688/5.860874kg를 보존했다. 실패는 접촉6 assertion 외에도 최신 Monster Source와 아직 설정 중인 InitialAbilityGrant의 empty class 로그가 포함됐다. Player 검증 범위이므로 별도 editor-world의 몬스터10개를 제거한 미저장 fixture로 다음 검사한다. main/map/data는 수정하지 않는다.

CollisionAuthor(06:25:35)는 derived PA3/ABP3 저장까지 적용했으나 BP compile Target 미연결3개로 실패했다. FEdGraphUtilities::ImportNodesFromText가 이미 ReconstructNode를 호출하는데 helper가 AllocateDefaultPins를 다시 호출해 중복 핀을 만든 것이 로컬 소스로 확인됐다. 해당 호출을 제거하고 TryCreateConnection 결과와 Graph text export를 추가했다. 실패 BP는 저장되지 않아 before SHA를 유지했고 own27492를 정상 quit/throttle true 복구했다. ColdBuild_ReflectionPinFix 중. 다음 own editor→038 fixture+CollisionAuthor→성공 후039 actual-body PIE→18 external transforms/shapes/contact/mass→render→stock reload→7 main SHA guard 전달. main 적용은 아직 없다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

이전 확대 진행 checkpoint의 main 미반영/QA pending은 해소됐다. Source3/map과 새 aliasDLL 선택 반영 완료, fresh main28460 actual contact PIE06:28:20 UTC Success/4설정readback/SHA passed. private24332/main28460 정상 종료. latest SHA는 BroadBrush20261007/Delivery.json, Backup/StagePIE/main_verify.log/FinalVerification.json. nativeSource09e7c3cb...e6b581b1, module3163ae85...bd54817, mapb9802151...d1b76b00. 일반 loaded DLL 보존, user8292 dirty ComboDefinition1은 건드리지 않았다. 새 class layout 확인에는 user 저장·재시작 필요. CPU active376평균1.3529/P95 3.5578ms, GPU/shipping 미검증.
현재 main을 기준으로 후속 설정만 바꾸고 초기 author/full-map/delivery/finalize helper를 재실행하지 않는다. 새로운 Source 변경은 최신 Source+Config를 private에 받아 current own hash backup→stage build→contact/범위/airnegative/saved settings QA→unique aliasDLL와 targetmap만 선택 전달→fresh background main QA. body/장비 fixture를 gameplay 넘어짐·공격 전체 검증으로 읽지 않는다. tagged PlayerPartsPIEEditor.cpp 및 PlayerParts source/dirty ComboDefinition은 이 작업 범위가 아니며 변경하지 않았다.

### 2026-10-07 — 외부18 몸 접촉 통과, 두꺼운 mass-only 형상은 화면 품질 실패

own10468 CollisionAuthor06:29:24/PlayerParts.PIE06:30:16 UTC Success. 각 파츠 external18개 모두 현재 실제 몸뼈 poseError0cm/원래 몸 collider 크기/등록1회 확인, Hair6116/Torso685/Leg10674 manifold points와 양의 impulses 관측. 대표 질량1.645364/12.054688/5.860874kg는 baseline과 같고 runtime damping .05/.35이다. 그러나 Collision_Idle/Moving 화면에서 옷자락이 과하게 밀려났다. 따라서 접촉 numeric success를 최종 품질 완료로 취급하지 않는다. 첫 CollisionAuthor/PIE 로그·화면을 보존한다.

정확한 근거는 UE5.8 ImmediatePhysicsActorHandle_Chaos.cpp CreateParticleHandle: ActorSetup.Shapes를 버리고 Geometry에서 새 shapes를 만들며 전부 CollisionData.bSimCollision=1로 설정한다. 따라서 기존 mass-only/NoCollision capsule도 RBAN에서는 충돌에 다시 포함된다. 이 안을 폐기하고 derived PA의 각 simulated body를 **얇은 capsule1개**로 바꾸며 engine adapter에서 원래 import PA의 단위 actor mass/CoM/body-space inertia diagonal을 계산해 mass override와 InertiaTensorScale에 복원한다. InertiaTensorScale은 직접 inertia 배율이 아니라 ScaleInertia(true)의 공간 스케일이다. q_i=(.5 trace(I_old)-I_old,i)/(.5 trace(I_thin)-I_thin,i), detS=(qX*qY*qZ)^(1/5), S_i=sqrt(q_i/detS)로 body 축 주대각을 복원한다. 전체 off-diagonal tensor/고유축의 완전 동일성을 주장하지 않는다. 수학적 보정값은 원작 직접 수치가 아닌 현행 임포트/engine 계산값이다. original PA/본체PA/관절/제품 C++는 유지한다. Source helper에52 mass/CoM/diag 비교 및 runtime shape1 검사를 추가했고 own10468 정상 quit/throttle true 복구 후 재빌드한다. 다음042 fixture+author→043contact/render PIE→quality 화면→stock reload→7 main 전달.

## 2026-10-07 — Enemy 고정 대기·영구 전투 타깃·행동 완료 후 Chase: 메인 완료

이 주제의 이전 착수/빌드·저장·Main 적용 대기 기록은 해소됐다. 착수 문단의 한글 인코딩 손상 이력은 보존하고 ARCH-78 후속 완료 절/[Monster 정본](MONSTER_UNAWARE_LOCOMOTION_20261007.md)을 읽을 수 있는 최신 계약으로 사용한다. Source 4개/package 5개를 Main에 반영했고 신규 runtime 파일 0이다. Heavy03/Halberd02 단일 Basic, 유효 Player target 영구 유지, 선택 대치/Attack 완료 후 재추격이다.

마지막 검증: CombatPolicyPIE 06:32:02.734 UTC 4종 Success; WaitingPIE 06:43:56.397 UTC Success; stock 임시 author 없는 재빌드 및 fresh saved audit Success; Main9 SHA/미관련89 보존/cold build10action 68.30초 Succeeded; MainReadyAudit 06:51:21.279651 UTC/PID29556/DevMap/4BP UP_TO_DATE/03·02 segment/PIE 없음/dirty0. own MonsterWork26036은 06:46:57.243906 UTC throttle true 복구·정상 종료했고 clean main8292는 정상 재시작했다. 다른 PlayerParts/Snow 프로세스·진행 기록은 건드리지 않는다.

실패 원인과 해결: author save 중 mailbox 재진입→processing guard; temp author 제거 후 UBT stale makefile C1083→work-only timestamp regen/stock 성공; Waiting fixture의 4초 forget 가정→각 actor Sight/Controller 수명 격리 뒤 원래 assertion 회귀 성공. 원인/실패 로그는 Metadata/MonsterCombatPolicy_20261007에 보존했고 gameplay 정책을 되돌리지 않았다.

남은 이 주제의 구현/build/asset 전달은 없다. 자동 Main PIE를 수행하지 않았으므로 사용자가 현재 DevMap에서 Play해 고정 대기/발견 End/멀리 이탈 후 전투 유지/대치나 공격 완료 후 Chase를 직접 확인한다. 추가 증상 재개 절차는 MainAppliedResult.json→해당 실제 Controller callback/Tick 또는 Standoff/Attack Task만 확인→필요한 단일 관측이다. 완료 author helper/전체 Content 복사/원본 retime/전수조사를 재실행하지 않는다. 임시 author cpp는 work Source에도 없고 Saved/MonsterCombatPolicy/AuthorSource에 보관했다. Main 현재 PID가 바뀌면 도구 health/process의 실제 project/PID/PIE/dirty 상태를 먼저 확인한다.

### 2026-10-07 — 몸 충돌 최종 검증과 메인7 전달

SingleThin author06:42:47/PlayerParts.PIE06:44:13/Guard06:48:44/Heal06:51:41 UTC 모두 Success. 52 source capsule의 mass/CoM/body-axis inertia diagonal 복원 비교 통과, runtime simulated shape1 및 각 part external18 current-bone pose/원래 몸 geometry 비교 통과. Hair4537/Torso613/Leg3320 contact points 및 양의 impulses 확인. Thin_Idle/Moving 및 최신 stock 뒤쪽 Stock_Back 화면을 직접 확인했다. 수정한 cloth 형태는 mass-only 안의 과한 부풀음이 줄었다. 아직 모든 mesh 정점/모든 전투 pose/원작 physics 일치를 검증했다는 뜻이 아니다.

다른 전투 작업에서 갱신한 최신 mainDLL2F27C046...183773E를 **work에만** 복사했고 own29184 stock saved/runtime readback07:05:24 Success: 7 candidate SHA, Original5 실제 컴포넌트, QueryOnly/no ragdoll, finite secondary Torso12/Leg59/Hair72 bones 확인. 첫 stock parent 비교는 본체에 없는 파츠 전용 뼈를 비교해 Torso0으로 실패한 검사 오류이며050 response를 보존하고 비교를 실제 part pose finite 검사로 교정했다. 같은 mainDLL이므로 재빌드/재검증을 반복하지 않는다. own29184 normal quit/throttle true 복구 완료.

현재 main은 다른 작업의29556에서 사용자용28172로 바뀌어 PID를 다시 확인했다. 동일 최신DLL/DevMap/PIE 없음/dirty0이며 QUIT 직전에 root/PID/PIE/dirty/7before SHA를 재검증했다. main28172 정상 종료→SHA guard로 **7/7 에셋 전달 complete=true**→사용자용 MainRestartProcess PID로 DevMap 재실행했다. Source/Config/Maps/primaryABP·PA/non-target Player content/currentDLL 등155 보호파일 snapshot은 IntegrationProtectedBefore다. 다음은 새 Main의 read-only BP compile/SCS/graph 및7SHA/155보호SHA 확인, 완료 MD4개 추가다. main 자동PIE/force quit/SaveAll/workDLL 전달 없음.

## 2026-10-07 — 몸 충돌 후속 최종 완료 / 재개 기준

7/7 BodyCollisionTuning DeliveryManifest complete=true, finalMainHash target7/보호155 모두 통과. Main19684 사용자용 DevMap에 관련7 BP UP_TO_DATE/Original5 stored components 및 CharacterMesh0 parent/외부 body collision3 flag를 read-only 확인했다. 마지막 game world 없음/dirty0. main 자동PIE/actor spawn/compile/save 없이 저장본 검증이며, 공유 로그의 일부 이후 gameplay 시작 출처는 확정하지 않는다. Subobject inspection에서 override null을 오류로 본 첫 검사는 mesh defaultPA fallback와 GetAssociatedObject로 교정; 제품 변경 없음. 전체 graph export10000자 truncation은 RigidBody node만 표적 export해 flag 확인했다.

요청 완료, 전달/빌드/helper cleanup pending0. own stock29184는 정상 종료/throttle true 복구. 현재main Source·DLL과 work stockSHA는2F27C046...183773E, work author helper binary는 Saved/PlayerPartsCollisionAuthorBinary에 보존되지만 **main에 복사하지 않는다**. 다음 사용자가 새 증상을 제시하면 Router→Architecture/Migration→PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md 최신 몸 충돌 완료 절→BodyCollisionTuning provenance/verification→관련PA/ABP만 표적 확인한다. 완료 author/전수 metadata 검색/전체 전달을 반복하지 않는다. 직접 Play에서 느낌을 추가 조정할 경우 먼저 세 derived PA damping과 구체 pose/부위를 확인한다. 원작 export가 새로 제공되면 기존 임시값과 source/bone/단위/버전을 비교한다. 필요시 격리 author 재개는 editor 정상 종료 후 work helper binary만 복원, 최신 main Source/Config 및 선택7 baseline을 새 backup으로 보존하고 현재 helper 복사→1action parallel build→fixture의 비대상몬스터 미저장 제거→native mass/contact/shape/render→현재stock reload→SHAguard 순이다. 기존Pos1/Pos2 .01 변환은 재적용하지 않는다.

## 2026-10-07 — Hair의 세밀한 반응·작은 진폭 요청 착수

사용자 직접 수정 요청: 굵은 덩어리·큰 휘날림을 줄이고 부드러운 결을 표현한다. 기존 external 몸 충돌은 보존한다. Metadata/PlayerParts_20261007/HairRefinement/BeforeManifest.json은 머리 derived PA 한 패키지 baseline이며 ProtectedBefore.json은 비대상161파일이다. 메인은 아직 수정하지 않았다. 기존 격리 프로젝트를 최신 Source/Config/Character로 갱신했고, editor-only 기존 helper에 HairAudit/HairAuthor 및 실제 이동의 연속 머리 관측을 추가했다. 새 제품 runtime 파일은0이다.

현재 work cold build: HairRefinement/ColdBuild.log, MaxParallelActions1/BelowNormal. 다음: 빌드 결과→own offscreen editor/mailbox→HairAudit의 실제 vertex weight 확인→기존 PA baseline native PIE/화면/진폭→HairAuthor→동일 native PIE/진폭/몸 contact/화면 비교→현재 stock binary saved reload→메인 fresh PID/PIE/dirty/SHA 확인 후 선택 전달 및 재로드. HairAuthor는 isolated Saved/PlayerHairRefinement.ini에 명시된 assistant 임시값만 읽고 기존 머리 PA에 저장한다. 원작 게임 물리 metadata가 확인되지 않은 기존 조사 범위는 유지한다. joint translation의 wrapper100 단위 보정은 새 관절에만 적용하며 기존 PA 보정을 중복 실행하지 않는다. 메인 Rider health가 현재 disconnected이므로 메인 종료 전에 반드시 실제 상태 조회 경로를 확보해야 한다. 강제 종료·미저장 폐기하지 않는다.

## 2026-10-07 — Enemy 애니메이션 전체 정리·Root Motion·공격/재추격 후속 착수

Main19684는 L_HeinMach_Environment PIE/dirty0이어서 조작하지 않는다. 별도 MonsterWork27240(Entry/NullRHI/mailbox)이 작업 에디터다. Inventory769=Art676+gameplay93, BeforeManifest982/byte backup, RenamePlan unknown0이다. root-motion skill18대표 audit는 index0 Root 및 scale1이고 static-root/움직이는 pelvis 경고는 의도된 in-place motion과 구분한다. 모든769의 구조/extraction/settings·referencer preflight와 duplicate probe가 아직 남았다. 첫 ExecutePythonScript launch23180은 script 자동 종료여서 ExecCmds launch로 교체했고 실패 로그를 보존했다.

다음: saved source/rename plan 표적 확인→reference packages backup/sync→전체 baseline/probe→UE rename/RootMotion options→기존 데이터 기반 공격 추가/owner 튜닝/Chase Task TimeRemaining 반응 대기→stock build·PIE/새 saved reload→Main 현재 변경/PIE/dirty 검사와 선택 전달. root 소비 범위 사용자 비동기 질문은 pending이며 기본은 Nav보행 유지+Montage Root Motion이다. own27240과 mailbox400-response identity를 확인하고 새 요청 번호401부터 쓴다. Source2/개발 regression만 변경하며 새 runtime class를 추가하지 않는다. Art 상세는 ENEMY_ANIMATION_ORGANIZATION_20261007.md에 분리 기록한다.


## 2026-10-07 16:42 KST — 깊은 눈 후속 runtime checkpoint

메인 runtime 파일은 미반영. private AKZSnowDeformation 기존 h/cpp에 FootCompression .7 조정값과 foot/body stamp 분기만 추가(새 runtime 파일0). body/weapon은 기존1, max compaction/cache/tile upload/EndPlay 유지. dev QA는 partial foot readback 및 실제 weighted layer 기반 비율 검사를 추가했다. 첫 cold build81.49s Succeeded, 첫 GPU foot40.5/weapon58cm였으나 pure60cm fixture 가정으로2assert 실패; 검사 수정 후 ColdBuild_DeepSnowQA20261007 진행 중. Art 재질/60·36·18cm provenance와 shader smoothing은 Art 정본에 분리 기록 예정.

정확한 재개는 Art continuity 같은 checkpoint 절 및 Scripts/Art/heinmach_snow_deep.py. Source3/map/material2 mainSHA guard와 최신 다른 runtime source 일치 여부를 검사한 후에만 새 alias UnrealEditor-KhazanSnowDeep20261007.dll 선택 전달. 정상 DLL2f27c046...183773e와 다른 source/assets 보호. 독립 root의 build를 종료하지 않는다. 메인 적용·PIE·GPU/shipping performance 완료로 기록하지 않는다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

이번 checkpoint의 미반영/QA pending은 해소됐다. latest 자료와 source 계약은 해당 snow 정본의 “두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료” 절 및 DeepSnow20261007/FinalVerification.json을 따른다. own 검증 에디터는 정상 종료한다. 사용자 live save/reload/PIE/close는 실행하지 않는다. 실행 중인 editor에서 새 FootCompression 사용에는 사용자 저장·재시작이 필요하다. 후속 크기·높이 변경은 해당 material scalars/level Actor 설정에서 시작하고 original pixel parity/shippingGPU 완료로 확대하지 않는다.


## 2026-10-07 17:13 KST — 깊은 눈 최종 종료 확인

Fresh main15340은 PIE Success 뒤 exit0으로 정상 종료했다. private18624/26860/16088도 exit0, 실패 초기 verifier17840은 위 완료 절의 사유로 own process만 정리했다. 최종 process 목록에 snow editor가 남지 않았고 사용자19684/독립 PlayerParts13904는 보존했다. Rider health disconnected이므로 user live dirty/PIE를 직접 조회했다고 주장하지 않는다. live save/reload/PIE/camera/close 실행0. FinalVerification/ProcessCleanup.json이 최종 완료 증거다. 새 설정 확인에는 사용자가 미저장 작업만 저장하고 editor를 재시작한 뒤 /Game/Maps/L_HeinMach_Environment를 연다.


## 2026-10-07 ? Hair ?? ????? ?? ?? ?? ?? / ?? ??

?? ??? ?? ??? ?? ??? ????. HairRefinement DeliveryManifest complete=true/candidate1 main SHA ??/protected161 unchanged, Main21248 read-only7 BP UP_TO_DATE/Original5/dirty0/gameworldNone. work1516 stock Guard/Heal/readback ?? ? normal quit/throttle true ??, helper binary? work Saved/PlayerHairHelperBinary? ???? Main?? ???? ???. runtime C++0/PA1??, author/??/cleanup pending0.

?? PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md ?? Hair ?? ? ? HairRefinement TuningProvenance/Verification/AppliedPerBone_InertiaConditioned ? ?? Hair derived PA ??? ????. ?? ??? simulated65/14 ponytail strands+kin3, ?? ??4 CopyPose??. 69?? simulation/SetDefaultProfile ??/face lock head overlap/thin natural inertia ??? ????? ???. failed logs/candidate history/? positional Rotator Python ??? enum formatting ??? ????. Root/Tip damping?SLERP support?limits? ?? virtual inertia? assistant ???? ??? ????.

? ?? ?? ?? ? isolated editor? ????? ????? target PA ? ? ? baseline/??? ??SHA??? Source/Config/Character ?? ???helper ?? ? work??? 1action build?saved65 profile/real movement?local flip/contact/frame/render ???? ??? current main module? work?? ??/stock reload??? main PID/root/targetSHA ????? ??/???dirty ?? ?? target CAS ???? main read-only audit/??SHA ???. ??/?? ??/?? Original parts/full body author? ????? ???. ? joint Pos ?? ??? .01? ?? ??? ???? ???. ?? exports? ???? ??? bone/field/version/unit/??? ??? ? ????.

?? Main19684? Rider disconnected?? pre-exit PIE/dirty0 ?? ??? ?? ???. ?? OS window close? ???? save/discard/force? ???? ???? ?? normal Exiting/process ??+CAS? ????. ??? main? Rider ??? ? ?? dirty0/PIE??? ????. ?? ??? Source/Snow/module4 ??? integration snapshot? ?? ????. future main? dirty/????/PIE ?? target concurrent change? ??????? ??? ??? ?? ?? ?? ?? ???? ????. ?? ???? ?? ?? ???/?? mesh vertex????LOD???? hardware QA?? ??? ?? ??? ??? ???.


## 2026-10-07 17:52 KST — Enemy 정리 적용 및 stock 검증 checkpoint

별도 MonsterWork21492/DevMap/renderoffscreen에서 검증 중이다. Source2+development test1만 수정, 신규 runtime 파일0. author helper cpp/dependency 제거 및 최신 Main 비관련 Source/Config intake89 완료, stock cold build10action/30.36초 Succeeded. 22 신규 data-only ComboAction 패턴 생성 성공, 기존13을 더해35(5/3/7/20), Attack68클립 saved readback coverage 완료. interval2..4→2/1.1..4/1.1초, combo.75→.85, ChaseReactionSeconds.4초는 임시 조정값이다. 현재 행동 완료 계약을 보존하고 Chase Task의 기존 TimeRemaining으로 반응 대기를 처리한다.

SourceAudit는813시퀀스/18,958,755 raw transforms와 곡선·마커·재생률/메타데이터 비교가 동일하다. 압축 루트 샘플44 translation+1 quaternion 항목은 과도하게 엄격한 기술 허용 오차로 실패했고 실패 로그를 보존했다. 실제 최대 positional 차이는.0060654cm이므로 최종 test는 .01cm 및 normalized quaternion angular1e-4rad QA 허용치를 사용한다(게임 수치가 아니다). 변경 test는 아직 새 build 전이다. 실제4종/35attack/8방향 보행/HP/cleanup Monster.PIE가 현재 진행 중이며 관측420에서 새 BackDashCounter Action의 capsule velocity/변위를 확인했다.

Main21248은 최신 read-only audit에서 DevMap/PIE없음/dirty0였다. 제품 코드·에셋 Main 전달은 아직 없다. 다음: native PIE 결과 저장→CombatPolicyPIE/WaitingPIE 및 Heal/Guard 필요한 회귀→own 정상 종료→최종 stock QA precision build/SourceAudit success→최신 Main SHA guard/선택 전달/현재 Main build와 saved reload. Main의 Snow/PlayerParts와 기존 모듈 alias를 보존한다. mailbox 다음421, owned PID21492만 제어한다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

ARCH-79 실제 완료다. 기존 StateTree/AISettings/CharacterDefinition grants/ComboAction/ComboDefinition/Montage를 재사용했다. runtime 새 파일·class·component·manager는0, 실제 gameplay Source는 KZMonster.h와 KZMonsterStateTreeNodes.cpp 두 파일이며 기존 development KZMonsterAIPIETest.cpp를 보완했다. Player/ASC/ComboAction 실행 코드를 재작성하지 않았다.

공격은13→35(Swordsman5, SwordShield3, Heavy7, Halberd20)이며 해당4종 Attack68클립을 모두 연결했다. finite 준비/loop/타격/회복은 같은 Action 안에서 필수 순서를 유지하고 실제 combo만 기존 held X/InputEnd로 잇는다. 신규 combo6개의 끝 경계 InputEnd 실패는 montage data에서 마지막 sample 이전으로 보완했다. 정확한 시간식과 원작 SB/file/field는 MONSTER_ATTACK_ROOT_MOTION_20261007.md 및 AttackExpansionPlan.json/AllSavedSkillAudit.json을 따른다. 원작 hit/guard 조건 producer나 피해/피격을 새로 구현한 것은 아니다.

현재 공격 선택에는 독립 RNG probability가 없고 거리/각도/cooldown gate를 쓴다. 기존 임시 interval2..4초를1.1로 나눠1.8181818..3.6363636초로, combo continuation .75→.85(+10percentage points)로 설정했다. 전체 공격 빈도의 정확한10%를 보장하는 통계 수치가 아니다. ChaseReactionSeconds .4초는 assistant 임시 tuning이며4BP AISettings에 저장했다. 선택 Standoff/Attack을 끝낸 뒤 Chase에 진입하고 기존 task TimeRemaining을 Enter에서 설정/Tick에서 감소시켜 nav 요청을 잠시 보류한다. 첫 Chase에도 적용한다. 타깃 유지/기존 cleanup을 보존한다.

stock SourceAnimationAudit813/18,958,755 raw transforms·곡선/선택 metadata 동일 Success; compressed root QA .01cm/normalized angular1e-4rad는 기술 허용 오차다. raw tolerance1e-6와 구분하며 실제 최대 압축 positional 차이.0060654cm였다. AttackPatternsPIE 최종35개/모든 section/actual root travel/HP 불변·취소 cleanup·네 종 실제 rechase Success. CombatPolicyPIE 네 종 선택 행동 완료/시야 밖 target 유지/.4초 nav hold/후속 물리 추격 Success, Waiting/Heal/Guard PIE Success. 최초 full Monster.PIE의32 방향보행/contact sample min11·median0cm/s는 통과했으며 montage notify만 보완한 뒤 중복 walk 검사는 반복하지 않았다. retreat fixture는 Root lunge로700cm를 따라잡는 문제와 nav 밖5000cm 배치 문제를 각각 보존하고, 최종8후보 projection+complete path 및 Chase 진입 이후 physical advance로 검사했다.

Main 선택 전달은 파일981개(기존69/신규경로912), 이름 변경 옛 파일802개를 정확한 path/hash guard 뒤 제거했다. backup Before와 실패 로그를 보존한다. 미관련 Source/Config86 및 Archer177개 hash를 보존했다. Main stock cold build Succeeded, fresh Main PID3528 /DevMap/4BP·ABP UP_TO_DATE/813 options·35 grants·68 clips/저장값 재확인/PIE없음/dirty0이다. 자동 Main PIE는 실행하지 않았다. Main에 사용자 직접 Play용 DevMap이 열려 있다. 최종 manifest와 증거는 Metadata/EnemyAnimationOrganization_20261007/FinalVerification.json, DeliveredManifest.json, MainReadyAudit.json을 따른다.

Main 최초 read-only 검사에서 DevAI_ label 접두사에 Navigation volume까지 포함해 actor수5로 실패했다. 4 BP/ABP·813 options 검사는 이미 통과한 상태였고, exact4family actor label로 QA 식을 고친 뒤 같은 fresh editor에서 전체 read-only 검사를 다시 통과했다. 실패 JSON/MainReload log를 보존했고 이 과정에서 게임 코드·map·asset save/PIE는 수행하지 않았다. raw tolerance의 정확한 값은1e-6이며 이전 Art 본문의 최초 .001cm 언급은 엄격한 compressed probe와 혼동한 설명이다. 최종 compressed .01cm와 raw 검사를 구분한다.

완료이며 pending helper/추가 에셋 전달이 없다. 최종 Main PID3528은 DevMap/PIE없음/dirty0/4BP·ABP UP_TO_DATE다. owned MonsterWork editor는 preview ScreenPercentage87/MotionBlur3와 원래 foreground throttle을 복구하고 정상 종료했다. 초기 실패 로그는 보존한다. 후속은 Router→Architecture ARCH-79 완료→Migration→MONSTER_ATTACK_ROOT_MOTION_20261007.md/Art ENEMY_ANIMATION_ORGANIZATION_20261007.md→CurrentAnimationLibrary.csv 및 실제 Source 순서다. rename/authoring/fixup/copy setup을 재실행하지 않는다. 직접 확인은 열린 Main DevMap에서 Play하고 감지→End→approach/좌우 대치→다양한 공격→거리 이탈 때 기존 행동 완료+.4초 후 재추격을 본다. 원작 AI 확률/모든 지형·연속 포즈/물리 pad/적 피격·네트워크는 미검증 후속이다.
 
## 2026-10-07 — Hair 기준 Torso/Leg 천 조정 착수

사용자 직접 수정 요청으로 Hair를 보존하고 Torso 망토/Leg 옷자락·가죽 장식을 같은 세밀한 관절/감쇠 방식으로 조정한다. Hair보다 움직임을 조금 더 허용하되 몸 충돌을 유지한다. Shoes/Arm은 저장 bone audit에 secondary cloth 뼈가 없고 animation-driven이므로 신규 sim을 선행 추가하지 않는다. 새 제품 runtime 파일/클래스는0이며 기존 derived PA 두 개를 변경 대상으로 한다.

별도 PlayerPartsWork를 최신 Main Source/Config/Player Character로 갱신하고 대상2 before backup 및 나머지160 파일 SHA를 ClothRefinement에 기록했다. Main3528의 read-only 상태는 PIE없음/dirty0. Main에는 아직 변경하지 않았다. 자체 native ClothAudit cold build 진행 중이며, Leg의 일부01→02 뼈 길이0 때문에 Hair의 단순 세그먼트 추출을 그대로 적용하지 않고 실제 skin weights와 hierarchy를 먼저 검사한다.

중단 시 Metadata/PlayerParts_20261007/ClothRefinement/{BeforeManifest,Preparation}.json과 ColdBuild_Audit.log부터 확인한다. prepare_player_cloth_refinement.py를 다시 실행하지 않는다. own project/PID를 확인하고 ClothAudit→baseline native PIE→ClothAuthor→saved reload/actual contacts/finite motion→latest Main stock readback 순서로 이어간다. 전달 전 최신 Main 대상 before SHA와 보호파일을 다시 검사하고 정상 종료 후 선택2만 CAS 전달한다. 기존 HairAuthor/CollisionAuthor/full parts author를 재실행하지 않는다. 수치 출처는 저장 원작 physics export 미확인, 임시 조정값으로 구분한다.

## 2026-10-07 — Contact55 격리 QA 실패·미반영 재개 체크포인트

현재 Main 반영은 하지 않았다. latest Main을 intake한 C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan의 Source/Khazan/Environment/KZSnowDeformation.h/.cpp 및 Tests/KZSnowDeformationPIETest.cpp가 작업본이다. 사용자 결정55/35/50cm, normalized field R reference55, FootCompression35/55/WeaponCompression50/55/body1, foot brush8/1.4×5/1.4cm/trace reach8cm를 기존 owner에 적용했다. 새 runtime 타입0이며 ComboActionAbility source는 변경하지 않았다. authoring/전달 기준은 Main Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/{RequestedContract,Baseline,SavedSettings}.json, helper Scripts/Art/heinmach_snow_contact55.py다.

own private PID19200/session f217e1163ec84df48c1cfc2805b44502에서 11:18:25 UTC Khazan.Snow.PIE Fail. foot GPU0cm가35cm 목표에 못 미쳤다. Monster3종의 실패는 foot contacts0이 아니라 이동거리>50cm predicate다: Swordsman0cm/contacts54, Heavy10.38cm/contacts112, Halberd0cm/contacts34; SwordShield255.92cm/contacts872 passed. reach8cm를20cm로 되돌리거나 새 sole offset을 추가할 근거가 아니다. Controller Tick은 early auto-possession 때 Definition 미완성으로 BoundLocomotion이 invalid면 다음 Tick에 StartMonsterLogic을 실행하므로 SpawnMonster 직후 StopLogic만으로는 늦은 bootstrap을 막지 못한다.

격리 development-only SpawnMonster fixture에만 StopLogic 이후 AI StopMovement/SetActorTickEnabled(false), ASC CancelAllAbilities/ClearComboCommands를 추가했다. existing MonsterAIPIETest cleanup과 같은 API이며 fixture actor는 검사 후 파괴한다. 제품 AI/controller/runtime class 또는 사용자 캐릭터는 변경하지 않았다. 이 추가 소스는 아직 재빌드·재PIE 검증 전이며 loaded PID19200 DLL은 이를 포함하지 않는다. 신규 fixture 적용 성공으로 기록하지 않는다.

정확한 다음 절차: 실패 verify.log/RuntimeGeometry/PNG 보존→root가 own editor19200을 정상 종료→latest private Source3 보존 상태에서 ColdBuild_Contact55 후속 QA build→Scripts/Art/heinmach_snow_stage.py verify로 fresh hidden editor→Ready.json의 새 PID/session 확인→shader 문제와 fixture를 actual real-RHI Khazan.Snow.PIE로 재검사. tinyGPU depth/actual contacts/동일fraction repeat/cache/fullclear/airweapon/EndPlay 전체 성공 뒤에만 Contact55 stage_passed/publish/finalize를 진행한다. publish 전에 latest Main current target/protected SHA·dirty를 확인하고 unrelated Source/normalDLL/loaded Deep material을 보존한다. FinalVerification.json success 이전에는 완료 doc appender를 실행하지 않는다. 초기 intake/old broad/deep delivery를 반복하지 않는다. 실제 foot8cm 바로 위 고립 airborne negative/GPU shipping 성능은 미검증이다.

## 2026-10-07 20:57 KST — ClothRefinement 실제 관절 QA 실패·미반영 체크포인트

Main 반영 전이다. 별도 PlayerPartsWork의 PA2 후보와 Scripts/Engineering 개발용 author/검증 helper만 작업 중이며 Hair/제품 Source/BP/ABP는 변경하지 않는다. owned editor21588은 정상 종료했다. Main3528의 마지막 read-only 상태는 clean/PIE없음이다. ClothRefinement/ConcurrentChangesBeforeIntegration.json의 Snow Source3와 현재 module alias 변경을 동시 작업으로 관측했으며 최신 파일을 보존한다. 최초 protected snapshot과 다르다는 이유로 이전 Source/DLL을 Main에 복원하지 않는다.

마지막 검증은 저장된 실제 constraint parent/RefFrame1·2의 world quaternion을 비교한 angular metric이다. 같은 metric의 PIE_Before.log는 Success: Torso RMS41.374413/peak85.471614deg, Leg45.678938/91.794114deg. PIE_JointFrames_Failed.log는 Fail: Hair RMS8.601943/peak27.320723deg와65 responding joints, Torso11.414027/21.337577deg와8 simulated cloth joints, Leg19.547727/83.167543deg와30 simulated cloth joints였다. 실제 simulated B_Cloth_03_03_F_Pelvis의 큰 굽힘이 남아 후보를 완료로 기록하지 않는다. 이전 immediate skeleton-parent/reference metric 및 Iron/kinematic 포함 로그와 수치를 혼합하지 않는다.

해당 Leg attachment 한 뼈를 임시 pin으로 안정화하는 INI/author 정책을 구현 중이다. 이는 원작값 또는 ref-pose embedded 증명이 아니라 실제 runtime flip에 대응하는 어시스턴트 임시 튜닝이다. collision review의 해당 ref clearance minimum은4.816cm였으므로 몸 proxy 내부여서 고정했다고 설명하지 않는다. 아직 후속 author 저장·재검증 성공 전이다. PA.solver_settings의 fixed step/iterations 및 Leg nonlinear solver는 보존된 Iron2에도 영향을 주므로 Iron geometry/mass/constraint 입력 보존을 동작 불변으로 확대하지 않는다. InitialPhi0/cached manifold gap은 모든 현재 shape/skin 정점의 관통0을 증명하지 않는다.

정확한 재개: 최신 TemporaryTuning.ini와 helper의 pin 정책 확인→own editor 종료 상태에서 MaxParallelActions1/BelowNormal cold build→fresh own PID/root/mailbox 확인→ClothAuthor→solver 설정/저장 profile readback→fresh saved native actual joint-frame QA 및 finite/몸 collider/화면 검사→현재 Main stock module을 work에만 복사해 Guard/Heal/readback. 전체 성공 뒤 최신 Main PID/root/PIE/dirty와 대상2 before SHA를 다시 확인하고 정상 종료 후 PA2만 CAS 선택 전달하며 새 Main read-only audit/보호SHA를 검사한다. Main Source/Config/ABP/게임 DLL을 격리 작업본으로 교체하지 않는다. prepare/full parts/CollisionAuthor/HairAuthor를 재실행하지 않고 Before/실패 로그/CandidateHistory를 보존한다. 최종 stock/Main 반영 완료 문서는 실제 결과가 확보된 뒤 별도 추가한다.

## 2026-10-07 — Contact55 Preview 전달·canonical 잠금 대기와 Halberd fixture 보완

Main Source/Khazan/Environment/KZSnowDeformation.h/.cpp와 Tests/KZSnowDeformationPIETest.cpp, Preview map/material2 및 unique 첫 alias는11:48:58 UTC 선택 전달됐다. 현재 delivery는 Main Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/Delivery.json이다. 원본 Content/Maps/L_HeinMach_Environment.umap은 Main 사용자 PID3528(HeinMach/dirty0/PIE없음) file lock 때문에 미적용이며 baseline SHA 그대로 보호한다. pending authored canonical은 같은 report 폴더 PendingCanonical/L_HeinMach_Environment.umap에 보존했다. 사용자 editor는 조작하지 않았다. canonical 적용·wait_apply worker 시작은 아직 수행하지 않았다.

첫 own background Main Preview PID2492는 정상 종료0/전체 Khazan.Snow.PIE Fail이다. GPU foot34cm/weapon50cm와4종 gait 등은 통과했지만 Halberd lying torso fixture 하나가 실패했다. test case15는 walking pelvis를 배치한 뒤 animation을1초 계속 재생해 drift할 수 있었다. C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan/Source/Khazan/Tests/KZSnowDeformationPIETest.cpp의 case15에서 bPauseAnims=true를 pose placement 전에 추가했다. 이미 merged weapon case17이 같은 고정을 사용한다. 제품 body/AI/CMC/Ability 코드와 에셋·map은 이번 fixture 수정0이다. 후속 private QA build Succeeded17.98s, 새 own private PID8672에서 실제 재검증 중이며 이 수정의 성공 Main PIE는 아직 없다.

helper Scripts/Art/heinmach_snow_contact55.py update_fixture_module은 새 StagePIEPassed DLL SHA, 현재 Delivery 대상/기존 Deep/normal/기존 alias/manifest/Stage BuildId 및 test 이외 Source byte 동일을 검사한 뒤 devtest와 새 unique KhazanSnowContact55QA_20261007 DLL/PDB만 전달한다. assets/maps는 재전달하지 않는다. receipt fixture_revision_utc를 추가하고 asset delivery UTC를 보존하며 finalize는 새 module과 revision 뒤 Main native/CSV만 인정한다. 정확한 다음 절차는 verify.log에서 private8672 성공 확인→stage_passed8672→own 정상 종료→update_fixture_module→hidden fresh Main Preview native/CSV→finalize다. 실패 로그와 이전 module을 삭제하거나 덮어쓰지 않는다.

Preview native가 통과해도 canonical pending이면 FinalVerification.success=false/preview_verified=true이며 완료 appender를 실행하지 않는다. wait_apply는 root가 Preview proof를 확인한 후 별도 hidden worker로 시작한다. 사용자3528가 살아 있는 동안 원본 map을 변경하지 않고, 종료 후 canonical baseline SHA가 같을 때만 pending blob을 atomic 교체한다. SHA mismatch는 사용자 map을 보존하고 BlockedCanonicalChanged, 파일 lock은 WaitingForCanonicalUnlock로 기록한다. 적용 뒤 receipt/hash 갱신→finalize→완료 appender 순이며 canonical map 새 Main PIE를 실행했다고 확대하지 않는다. GPU/shipping·isolated actual foot8cm airborne negative는 미검증이다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Main Source3/? Contact55 material2/Preview map/UnrealEditor-KhazanSnowContact55QA_20261007.dll? ?? ????. ?? native PIE ?? ?? /Game/Maps/L_HeinMach_Environment_Contact55_20261007, fresh background Main PID24660, 12:08:02 UTC Khazan.Snow.PIE Success?. GPU ?? ?34.000cm/??50.000cm?? ?? canonical /Game/Maps/L_HeinMach_Environment? ?? ???? ???. ??? Main PID3528? HeinMach/dirty0/PIE???? ??? ???? ?? file lock? ????. ??? save/reload/PIE/camera/close? ???? ???. FinalVerification? success=false/preview_verified=true/canonical_map_pending=true? ??? Preview ??? ????.

?? ?? ??? Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/FinalVerification.json/Delivery.json/PendingApplyStatus.json ? MainPIE.log/MainPreview?. hidden worker2256?12:08:54 UTC wait_apply? ???? ???3528 ??? ????. source/?? ????PIE ????user editor ?? close? ?? ???. ?? PendingApplyStatus.state? ?? WaitingForUserEditorExit?? ??? ?? ?????? ????, WaitingForCanonicalUnlock?? ?? lock? ?? ??? ????. BlockedCanonicalChanged? ??? map? ???? ? baseline/??? ??? ??? ?? ????. known pending canonical? ?? ?? PendingCanonical/L_HeinMach_Environment.umap?? baseline SHA 700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba? ?? ?? atomic ????.

worker? ???? Delivery.canonical_map_pending=false/??SHA, finalize? ?? appender? ????. AppliedVerificationPending?? canonical ??? ?? ?????? ?? copy?? ?? ?? module/normalDLL/Source hash? ??? verification blocker? ????. ?? canonical ? Main PIE? Preview native ??? ?? ????. ?? prepare/publish_unlocked/old alias overwrite? ???? ???. ??? Preview ?? ????? ?? ???? ?? ??? ???. GPU/shipping?actual foot8cm airborne negative? ??? ????.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
최신 정본은 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007의 FinalVerification.json/Delivery.json/PendingApplyStatus.json 및 MainPIE.log/MainPreview다. worker2256은 사용자3528 종료를 기다린다. 현재 WaitingForUserEditorExit이며 기존 Source/asset 재전달·PIE 반복·사용자 강제 close를 하지 않는다. 잠금 반환 뒤 canonical baseline SHA700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba가 같을 때만 known PendingCanonical/L_HeinMach_Environment.umap을 atomic 적용한다. 변경된 사용자 map은 보존·BlockedCanonicalChanged다.

worker 적용 뒤 Delivery.canonical_map_pending=false/적용SHA와 finalize/완료 appender를 확인한다. AppliedVerificationPending이면 파일은 이미 적용됐으므로 다시 copy하지 말고 current module/normalDLL/Source hash·verification blocker를 확인한다. Preview native 성공과 원본 canonical SHA handoff를 분리하며 원본 새 Main PIE는 수행되지 않았다. 초기 prepare/publish_unlocked/기존 alias overwrite를 반복하지 않는다. GPU/shipping·actual foot8cm airborne negative는 미검증 후속이다. 현재는 Preview 검증 성공·원본 적용 대기이며 canonical 완료 기록이 아니다.

## 2026-10-07 22:23 KST — Cloth surface 직접 probe·Leg flip 지속, 관성 후속 검증 전

ClothRefinement는 여전히 미완료이며 Main의 PA2는 미반영이다. Main3528은 실행 중이고 Hair hash를 보존한다. 최신 Snow Source3/module alias와 다른 채팅의 canonical-map 대기를 존중하며 Main을 종료하지 않았다. 이전20:57 checkpoint 이후 attachment pin/solver/관절 관측/terminal 형상 후속과 실패 로그를 Metadata/PlayerParts_20261007/ClothRefinement에 보존했다. Main 제품 runtime/ABP/몸 PA를 수정한 작업으로 기록하지 않는다.

최신 DominantSkinWeightVertices terminal 후보와 fixed30 probe의 실제 PIE는13:12:40 UTC Fail이다. Leg simulated cloth joint peak111.050873deg로45deg QA를 넘었고, peak bone은 B_Cloth_01_06_F_Pelvis다. Torso peak24.009739deg, Hair peak31.588255deg/65 responding joints는 각 QA 범위지만 전체 성공을 의미하지 않는다. 변경하지 않은 Hair의 이 관측을 새로운 Hair 튜닝 적용으로 표현하지 않는다. 해당 로그는 own Saved/Logs/PlayerPartsWorkEditor.log의13:12:40 구간 및 ClothRefinement의 후속 보존 로그를 기준으로 찾는다.

현재 pose의 LOD0 linear-skin vertex 중 직접 simulated cloth에 양의 weight가 있는 정점을 actual external18 anatomy implicit geometry의 Phi와 비교했다. stage3/4/5의 Leg5772정점 sample 최소Phi는 각각-12.113855/-12.598690/-10.363999cm, inside vertex 수471/860/760이었다. Torso867정점은 세 snapshot 모두 inside0이고 최소Phi0.588902/0.747034/0.883688cm다. cached manifold gap보다 직접적인 현재 skin-to-proxy 관측이지만 body proxy와 실제 몸 표면은 다르며 sampled simulated 영역·LOD0·세 pose 범위다. 기존 baseline의 동일 surface probe는 미측정이므로 관통 개선 또는 기존보다 악화했다고 확정하지 않는다. Torso contact0 또한 모든 상황의 충돌/관통0을 뜻하지 않는다.

다음 조정은 회전 불변의 최소 principal inertia 보강이다. 어시스턴트 임시 conditioning 정책 UniformScale=(Imax/Imin)^(1/5)을 existing author helper에서 구현 중이며 아직 후속 build/author/runtime 통과 전이다. Imax/Imin은 thin actor의 실제 engine/import 계산 principal inertia 입력이다. Engine ScaleInertia의 uniform S^5 변환을 이용해 full tensor와 off-diagonal을 함께 스케일하는 계산이며 대각값만 보강한 기존 정책과 구분한다. 모든 principal moment를 같은 비율로 바꾸므로 완전 isotropic tensor를 만들었다고 기록하지 않는다. 원작 physics 값이 확인되거나 사용자가 직접 지정한 수치가 아니다.

정확한 재개: latest helper/INI의 최소principal 정책과 finite-positive 입력 확인→owned editor 종료 후1action/BelowNormal cold build→fresh own identity/mailbox→ClothAuthor/solver 설정 재적용→candidate 저장 profile·관성·parent/shape readback→fresh saved native actual joint-frame QA와 같은 stage surface probe/화면→필요한 동일 baseline surface 측정→현재 Main stock Guard/Heal/runtime readback. 검증 성공 전 Main 전달하지 않는다. 성공 후 fresh Main identity/PIE/dirty/대상2 before SHA를 검사하고 selective ReloadPackages(PA2)로 반영하는 방식을 우선 검토한다. 이는 다른 채팅의 최신 Snow module과 실행 중 Main을 보존하려는 계획이며 reload/반영이 이미 완료된 상태가 아니다. reload에 필요한 안전한 파일잠금 반환·CAS·참조/dirty 조건을 확인하지 못하면 Main을 임의 종료하거나 강제로 덮어쓰지 말고 정확한 차단 상태를 추가한다. 준비/author 전체 반복 및 과거 Source/DLL 복원은 하지 않는다. 최종 완료는 실제 stock 검증·Main PA2 SHA/read-only 재로드 증거 뒤에 별도 기록한다.

## 2026-10-07 23:14 KST — FullStrip Floor4 native 통과·Root24 비교 및 Main 미반영

Main3528은 기존 HeinMach world/clean/noPIE 상태를 유지하며 PA2 반영·Main 종료를 하지 않았다. read-only MainSelectiveSnapshot.json의 최신 보호161개는 현재 Snow QA disk alias와 실제 loaded UnrealEditor-Khazan.dll을 구분한다. 새 module/Source를 이전 상태로 되돌리지 않는다. 최종 후보는 아직 결정 전이며 own13684/BelowNormal에서 Root24 비교를 진행 중이다.

PIE_FullStrip_Floor4_Success.log의14:09:43 UTC native PIE는 Success: Torso angular RMS3.764723/peak11.961719deg, Leg11.351859/29.522254deg. 같은 fixed30/actual constraint-frame baseline(PIE_Before_Fixed30.log)은 Torso39.288148/82.928390, Leg46.299694/129.865832deg다. Hair RMS8.687415/peak31.588255deg와65 responding joints는 이 비교 baseline과 동일하고 파일 hash도 보존했다. 이는 격리 native 성공이며 stock 검증·Main 반영 완료가 아니다.

FullStrip Floor4에도 Leg의 실제 external18 body proxy overlap이 남는다. dominant-direct-sim skin subset3835정점 중 stage3/4/5 inside 수는131/613/618, stage4 minimumPhi=-11.773709cm다. kinematic 소수weight 혼합만으로 설명할 수 없는 dominant sim overlap을 함께 기록한다. Torso dominant sim subset은 세 snapshot에서 inside0이다. 제한된 LOD0/current-pose/몸 proxy 관측이므로 실제 몸 표면·모든 mesh/pose/LOD의 관통0으로 확대하지 않는다. native angular Success만으로 사용자 몸 관통 요구를 모두 해결했다고 기록하지 않는다.

후속 Root24는 Depth0 body만 보강해 cloth 뿌리의 body 접촉 안정성을 비교하는 어시스턴트 임시 정책이며 원작 metadata 직접 값이 아니다. trial 저장본이 최종 확정됐거나 성공했다고 아직 기록하지 않는다. 기존 최종 후보·실패·baseline 자료와 적용한 INI/geometry/inertia provenance를 보존한다.

남은 순서: Root24 final native/surface/화면 비교→선정 후보 저장·새 프로세스 reload native 및 실제 normal displacement 관측→own stock Guard/Heal/runtime readback→선정 PA2 hash와 native/stock 보고서 binding→최종 CandidateManifest 재prepare 후 최신 MainSelectiveSnapshot 재생성→fresh Main PID/root/world/noPIE/dirty/보호SHA 확인→검증 전제 selective PA2 handoff/ASSUME_NEGATIVE reload→Main read-only Original parts/solver/대상SHA·world 보존 audit→Engineering 정본/상태/진단/continuity 최종 기록. 현재 snapshot은 이전 Candidate4 manifest에 묶여 있어 최종 candidate reprepare 뒤 그대로 재사용하지 않는다. Main handoff helper는 준비·오프라인 syntax 검사 및 read-only snapshot까지 완료했으며 실제 handoff와 Verification stock 완료는 아직 없다. 전체 prepare/HairAuthor/CollisionAuthor/제품Source·DLL 복원을 반복하지 않는다.


## 2026-10-07 23:36 KST — Cloth 작업 반영·검증 완료 및 재개 기준

23:14의 pending 단계 이후 최종 FullDominant bounds/FloorLeg4/Depth0Root32를 저장·검증하고 Main에 PA2만 반영했다. `Verification.json` status=MainIntegrated, fixed30/새 프로세스 일반 시간 간격/Stock Guard·Heal/Original5·finite bone·Hair SHA 검사 PASS. `MainSelectiveHandoff.json` 및 `MainReadyAudit.json`은 Main3528/HeinMach world·선택·dirty0/noPIE·보호161파일과 기존 Source/DLL/Snow alias 보존을 확인한다. Main은 종료하지 않았으며 작업용 에디터는 정상 종료·background throttle 복구했다.

재개 시 이번 Player physics 정본과 `TuningProvenance.json`, `AppliedPerBone.txt`, `CandidateManifest.json`/`DeliveryManifest.json`을 먼저 읽는다. Torso 전달SHA=BC422363C3B491B5E9F6618763CE52C3D544ED494189A7870530842A31F8C34F, Leg=936CF02F30FD6EF66649660C3405EAA13B7F7B178795069C5152E3A864A28960다. 변경 전은 `Before/`, 최종은 `FinalCandidate/`, 중간 시험 로그는 그대로 보존했다. 기존 pending draft/Stock 실패 응답165는 최종 성공 readback168과 완료 보고서로 대체된다(165는 automation 종료 후 game world가 없어 readback을 시작하지 못한 시점 오류이며 에셋 오류가 아니다).

Leg에는 sampled dominant3835 중111/390/350의 body-proxy overlap이 남아 있다. proxy와 실제 피부·anchor 주요 가중치·포즈·물리 joint를 구분해 관측 pose만 표적 확인한다. 전수 재임포트/prepare/HairAuthor/본체 PA 덮어쓰기/Main force quit을 재개 절차로 삼지 않는다. 후속 변경은 별도 에디터에서 saved/일반 시간 간격 검사→새 manifest/stock 검증→최신 Main PID/world/dirty/CAS 보호→선택 반영 순으로 진행한다. 제품 runtime 새 파일0이다.


<!-- ApesYetugaBehaviorResearch_20261008 -->
## 2026-10-08 — Apes·Yetuga 연구 완료·미확인 계약 후속

분석정본은 APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md의스킬/방어최종보완절이다. 마지막검증은ResearchVerification.json 및Skill75/Defense40개원본SHA·참조검증이다. Source/BP/assets/build/PIE적용은없다. 기록된미확인은실패한구현이아니라 native소비자료/통제실험이없는범위다.

재개:(1)Router→Architecture최신/현재Migration→본정본과저장Art/report를읽는다.(2)요청이추가분석인지직접구현인지구분한다.(3)native의HPraw65/60/50·ratio/default·고갈timer/Brutal·Rate/조건결합·AttackSuccess/OnAttack·group reset·실행중중단을표적확인한다.(4)추가영상은버전/난이도/HP/기력/거리/각도/방어결과를고정한다.(5)구현시기존StateTree/Definition/ComboAction에서필요부분만확장하며무조건콤보/단일Phase2bool/새manager를선행생성하지않는다. 기존4NPC·사용자변경·다른continuity작업을보존한다.

## 2026-10-08 — NPC4 보간·공격 회전 진행 중 / 재개점

ARCH-80 계약으로 별도 MonsterWork의 기존 runtime Source6 및 기존 native Test 한 파일을 수정했다. 새 runtime 파일/class는0이다. Main Source/asset는 아직 전달 전이다. 4 Combat BS는 원작 직접 speed6/10/10/5를 Work에서 저장·readback했다. 저장 ABP graph reflection은 Python에 노출되지 않아 readback_complete=false로 정확히 남겼으며 ABP는 수정/저장하지 않았다. 최신 관련 문서는 MONSTER_FACING_SMOOTHING_20261008.md(작성 중)이다.

Baseline stock build Success, 실제 LLDB pause는 DevAI_Swordsman Attack_Kick/타깃 BP_Player0/CMC desiredRotation1/rootphysics0/rootMontage를 확인했다. 수정 전 CombatPolicyPIE4종 Success다. agent breakpoint는 제거하고 사용자 exception8개 enabled 상태를 보존, own worker3672 정상quit/디버그세션0이다. Work build 첫 실패는 test local AI shadow C4458이고 수정했다. FinalBuild.log Success(53.75s). Montage DataModel-null 후보는 test SamplingFrameRate API로 교체했다.

현재 own worker26136 /DevMap RenderOffscreen, monster_isolated_editor mailbox Ready.pid/project 대조 완료, Khazan.Monster.FacingPIE 진행 중이다. 해당 test는 4종35공격·실제Sight·CMC소비root분리·±180wrap·콤보직전강한조준·끝cleanup CSV를 저장한다. Source GetDesiredRotation의 UKismetMathLibrary 래퍼 적용은 현재 binary 이후이며 다음 cold build에 반영해야 한다. Montage timing은 EffectivePlayRate를 사용해 RateScale을 포함한다.

정확 재개: Metadata/MonsterMotion_20261008의 OwnedBaseline/AssetBaseline/WorkIntake/DebuggerBaseline/BaselinePIE/FinalBuild 확인 → worker26136 살아있는지+Ready대조 → work log에서 FacingPIE Test Completed 확인 및 Saved/MonsterAI/FacingPIE.csv 보존 → pre/post tick의 준비구간 경계 때문에 slow-rate 검사가 실패하면 runtime과 QA 분류를 분리해 확인(lead+dt/nodechanged). 이번 작업 agent apes_public_patterns가 이 경계의 Engine TickCharacterPose→PhysicsRotation 순서를 확인했다. test 수정 필요 시 own worker만 mailbox quit 후 build/relaunch → Facing/CombatPolicy/기존Monster.PIE(32보행+root)/Heal/Guard 순서로 검증 → SHA/CAS로 이번 owned Source7/BS4/script만 Main 선택 전달, unrelated Snow/PlayerParts 보호 → MD 완료절 기록. Main 사용 editor PID3528, 외부 SnowWork25768/PlayerPartsWork2204는 조작하지 않는다. 이전 10/7 delivery manifest 전체 재실행 금지.

<!-- LeftShoulderCloth_20261008_pending_handoff -->
## 2026-10-08 10:35 KST — 왼쪽 어깨 천 미세 조정, Main 전달 잠금 대기

- 사용자 직접 수정 요청으로 Torso의 기존 왼쪽 Cape 관절 8개 `AngularDrive.SlerpDrive.Stiffness`만 기존값×0.95로 조정했다. 어시스턴트 임시 튜닝이며 원작 해당 수치는 미확인이다. damping/limits/inertia/geometry/collision/solver와 Hair·Leg는 유지했다.
- 마지막 검증: 동일 fixed30 baseline/candidate native PIE Success, profile8 stiffness-only/default 일치, fresh saved fixed30 native Success, 실제 Main 모듈(A95C…) stock Original5/finite Torso12·Leg59·Hair72 readback Success. Work 에디터 종료 및 helper DLL/PDB/modules 복원 완료. `Metadata/PlayerParts_20261008/LeftShoulderCloth/Verification.json` 참조.
- 별도 관측: 일반 시간 간격 NullRHI 후보2회/원래 Torso 대조1회 모두 수정하지 않은 Hair의 35deg QA만 실패했다. Hair peak60.079030/59.592638/71.877890deg, Torso는 모두45deg 미만. timing 원인 확정/모든 조건 통과로 기록하지 않는다. `NormalDeltaObservation.json`에 보존했으며 Hair 변경은 없다.
- Main PID3528 `/Game/Maps/DevMap.DevMap`, PIE/dirty0에서 snapshot 후 fully-load/reset-loader를 실행했으나 atomic replace WinError5로 중단됐다. Main Torso SHA는 여전히 `BC422363C3B491B5E9F6618763CE52C3D544ED494189A7870530842A31F8C34F`다. 후보 SHA는 `7560A4A740D8AD99370F7D210CC7A444A828EC0F14C4939141A8CD50A23CFCDE`, pending 파일은 동일 후보다. Main 파일 교체/재로드는 아직 완료하지 않았다.
- 읽기 전용 Restart Manager 조사에서 잠금 소유자는 SnowWork 검증 에디터 PID13888이었다. 다른 작업 에디터를 종료/조작하지 않고 자연 해제까지 기다린다. `MainSelectiveHandoff.json` 실패 기록을 보존한다. 초기 protected162 중 별도 작업의 `Config/DefaultEditor.ini` 변경은 되돌리지 않고 최신 snapshot에 포함했다.
- 정확한 재개: 기존 `Scripts/Engineering/player_parts_file_locks.ps1`의 읽기 전용 inquiry로 Torso 및 pending 잠금 해제를 확인 → Rider health로 실제 Main PID/world/PIE/dirty 확인 → existing `player_cloth_main_selective_handoff.py`를 snapshot, handoff 순서로 같은 GameThread call에서 실행한다. globals: report=`Metadata/PlayerParts_20261008/LeftShoulderCloth`, targets=(Torso relative PA path,), motion_parts=('Torso',), required fields=native_pie_passed/native_saved_reload_passed/stock_saved_reload_passed, expected_pid=실제 Main, expected_world=실제 world. 정상 fresh MainReady audit와 protected/SHA 최종 보고서를 기록한다. 전체 ClothAuthor 재실행이나 Hair/Leg 변경으로 재개하지 않는다.


<!-- LeftShoulderCloth_20261008_complete -->
## 2026-10-08 10:38 KST — 왼쪽 어깨 천 완료, 10:35 전달 대기 해소

앞선 잠금 대기는 SnowWork 정상 종료로 해소했다. 검증 후보 Torso PA1 SHA `7560A4A740D8AD99370F7D210CC7A444A828EC0F14C4939141A8CD50A23CFCDE`를 Main PID3528 `/Game/Maps/DevMap.DevMap`에 전달·재로드 완료했다. MainReady Original5/BP7·solver1/60/24/4/4/linear=true, actor/선택/loaded DLL/보호162 유지, PIE/dirty0 확인. Work 에디터 종료·helper binary 복원 완료. `FinalCompletion.json`이 완료 근거이며 immutable pre-delivery `Verification.json`의 pending 표시는 이 완료 기록이 대체한다.

다음 어깨 작업은 현재 PA/profile8과 `Metadata/PlayerParts_20261008/LeftShoulderCloth`에서 시작한다. 이미 adjusted이므로 scale을 재적용하거나 full ClothAuthor로 재작성하지 않는다. 현재 scope는 spring-only이고 baseline backup/actual audit/전후 PNG/failed 및 success handoff history가 보존돼 있다. 별도 작업의 DefaultEditor.ini 최신 변경도 되돌리지 않았다.

남은 **별도 Hair 문제**: 일반 시간 간격 NullRHI cap60에서 기존 Hair35deg QA 초과가 후보2회 및 original-Torso 대조1회 재현됐으며 원인 미확정이다. 재개하려면 Main을 그대로 보존하고 별도 Work에서 현재 native helper/Original5/source를 사용, 몬스터만 Work에서 제거하고 고정 timestep 없는 같은 PIE 입력을 재현한다. 3개 원문 log와 NormalDeltaObservation의 실제 Hair/torso 관절·scope·35/45deg 검사를 출발점으로 삼아 timestep/초기화/실제 관절 상태 증거를 수집한다. fixed30 성공을 일반 시간 간격 성공으로 바꾸거나 이번 어깨 조정을 되돌려 해결했다고 기록하지 않는다. 이번 요청에서는 Hair/Leg tuning을 추가하지 않았다.


<!-- HeinMachSnow_AttackContact_20261008_complete -->
## 2026-10-08 10:52 KST — HeinMach 접촉/canonical 완료·정확한 후속

무기 파임을 기존 active Attack Spec의 asset tag와 실제 지역 눈 표면 접촉에 제한했다. 비공격 이동 이력은 무기만 끊고 발/몸은 보존한다. 기본 HeinMach에 사용자55/35/50cm·rim 포함 발 반경축8×5cm 및 CPU 접촉 profile2를 반영해 이전 Contact55 canonical 대기를 완료했다. 새 runtime class/file0, CMC/ASC/Ability/AI/AnimInstance gameplay 변경0.

정본은 HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 같은 날짜 절과 Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/{Delivery,FinalVerification,MainVerification,NativeBuildProof}.json이다. private27636 및 fresh canonical Main652 Khazan.Snow.PIE Success, 메인 saved reload/정상 종료 확인. 이동 maximum35/55·공격 접촉50/55, GPU 발34/무기50cm. SnowTick CPU active1530 평균0.420499/P95 .817/max6.0138ms; 고정 공격 fixture를 포함한 Development Editor 측정이며 빠른 실전 sweep/GPU/shipping 검증은 아니다.

현재 canonical SHA57d8319…771ea7, manifest alias UnrealEditor-KhazanSnowWeaponContact20261008.dll SHAf6b86d4…8c2a2. 원래 DLL·이전 Preview/alias·머테리얼/캐릭터/ghosting Config와 비소유 Source를 보존했다. 이전 worker2256 중지·status archive 후 PendingApplyStatus는 SupersededByAttackContact20261008이다. 옛 Preview FinalVerification의 pending=true는 당시 증거이며 새 canonical 완료 근거는 이번 FinalVerification이다. 사용자 세션은 조작하지 않았고 마지막01:50:20 UTC에는 UE 연결/프로세스가 없었다. 다음 새 에디터에서 기본 HeinMach를 확인한다.

이미 완료한 old Contact55 wait_apply/initial installer/finalize·pending blob 전달을 반복하지 않는다. 최신 Main Source/map/module·이번 receipt에서 시작하고, 새 Source intake 전에 Snow Source3을 보존해 독립 변경을 포함한 native build를 만든다. Weight/UV/height/rim이 변한 경우에만 surface script bake→private author→fresh audit→RHI→guarded selected delivery→fresh canonical Main QA를 수행한다. 새 헤더/layout을 이전 loaded native module에 강제 reload하지 않는다.

남은 별도 검증은 자연 공격 montage의 빠른 sweep 최악 비용·실제 장비 형상의 중심선 probe 근사·source weight mip/face-vs-smooth normal·원작 pixel parity/GPU/shipping이다. 이번 무기 비공격 파임 수정과 canonical 반영은 완료이며 재개 대기가 아니다. 실패한 기존 Run/Dodge reader의 방향 원인과 교정은 구현 정본과 보존한 두 Stage fail 로그를 따른다.


## 2026-10-08 11:01 KST — NPC4 최종 통합 빌드·35공격 회전 검증 통과, 보행 회귀 진행

앞선 NPC4 진행 절의 worker26136/미빌드 Kismet 상태는 이 checkpoint로 대체한다. 최신 Main의 별도 Snow Source3 변경을 Work에 추가 intake했고, IntegratedFinalBuild.log에서 cold build Succeeded(36.47s)를 확인했다. 복사된 헤더의 과거 timestamp 때문에 최초 통합 UHT가 이전 generated.h를 재사용한 실패를 IntegrationBuild.log에 보존했으며, Work 헤더만 touch/-ForceHeaderGeneration으로 새 생성 후 통과했다. Main Snow 코드를 되돌리거나 편집하지 않았다.

own worker27376 /DevMap RenderOffscreen/Ready identity를 확인했다. 최종 Khazan.Monster.FacingPIE는 01:54:58 UTC Success이며 Swordsman5/SwordShield3/Heavy7/Halberd20 모든35공격·각 authored node/±180 wrap/slow/fast/자연 종료 일반회전 복귀를 검사했다. Facing_Final.log/csv는 해당 최종 run의 원본 보존이다. 첫 실패는 pre-tick phase를 PhysicsRotation phase처럼 판정한 테스트 분류 오류였다. TickCharacterPose의 montage/notify 갱신 뒤 실제 root conversion callback에서 분류하도록 고쳤으며, source root quaternion은 mesh world basis에서 비교한다. 게임 회전 속도를 실패에 맞춰 늘리지 않았다.

현재 같은 own worker에서 기존 Khazan.Monster.PIE의32방향 이동·실제포즈·접지·자연AI/재추격·35패턴·cleanup 회귀를 진행 중이다. Main Source/BS4는 아직 전달 전이다. delivery/새Main검증 스크립트는 문법 검사만 완료했으며 VerifiedDeliveryProof.json이 준비되기 전 실행하지 않는다. 실제 프로세스 조회에서 사용자 Main3528는 자연 종료돼 없고 root가 종료하지 않았다. 재개는 own27376 Ready 대조→MonsterWorkEditor.log의 exact Test Completed Success 확인/원본 보존→최종 compiled Source inventory와 Main의 비소유 Source 재대조→proof 작성→guarded preflight/deliver→별도 새Main에서 저장값/로드alias/native CombatPolicy·Heal·Guard 검증→완료 MD 추가 순서다. 기존 전체 authoring/10월7일 delivery를 반복하지 않는다.

<!-- HeinMachSnow_AttackContact_20261008_normal_rebuild_verified -->
## 2026-10-08 11:01 KST — 후속 일반 Main DLL 빌드도 새 접촉 검증 완료

전달 뒤01:49:41 UTC Main 프로젝트 native build가 새로 실행돼 normal DLL과 manifest가 갱신됐다. 이 빌드는 본 작업이 시작한 것이 아니며 되돌리지 않았다. 최신 전체 Main Source가 본 작업의 검증된 NativeBuildProof와 byte 일치하고 canonical/Source3/기존 보호 asset·Config도 동일함을 확인했다. 현재 manifest는 `UnrealEditor-Khazan.dll`, SHA `4ca0cc527b9d94c6812246befd974e5ce268ec5ece23207add6394d369cde354`다. 앞 절의 alias 선택·원래 DLL 보존은 당시 전달 사실이며 현재 선택 모듈 정본은 이 절이다. 이전 성공 Delivery/FinalVerification을 수정하지 않았다.

새 hidden MainPID19372에서 실제 normal DLL 경로·저장 canonical profile2/55cm·작은 발 범위/scene9,869를 재검증했고01:58:40 UTC `Khazan.Snow.PIE` Success 및 정상 종료했다. Player Run142/Dodge236 표본 maximum35/55, Player/4NPC active 공격 지면 양성/공중·비공격·취소 음성과 기존 GPU 발34/무기50cm/cache/EndPlay 회귀가 통과했다. 자료는 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/NormalMainRebuild_20261008`의 snapshot Delivery(not_a_delivery), MainColdBuild.log, MainVerification/Exit, MainVerify.log다. 이번 Snow 수정·canonical 반영은 완료이고 old worker/preview pending을 재개하지 않는다. 기존 모듈 변경 및 source 보존 절차·원작/mip/normal/자연 fast sweep/GPU/shipping 미검증 범위는 유지한다.

같은 Development Editor/frozen attack scope의 normal DLL SnowTick은 active929 평균0.507301/P95 1.033800/max4.364200ms, `Profile(20261008_105739).csv`다. 이전 .420499ms와 조건이 다른 별도 관측이며 개선율로 비교하지 않는다. 사용자 에디터를 저장/종료/재시작하거나 예전 alias로 manifest를 되돌리지 않았다. 새 에디터에서 기본 HeinMach를 확인한다.

<!-- WaistJitter_20261008_probe_build -->
## 2026-10-08 11:10 KST — 허리 장식 떨림 표적 진단 진행

사용자가 허리춤 메시의 지속적인 떨림을 진단하고 직접 수정하도록 요청했다. 대상은 Player Original Leg 물리이며 첨부된 Monster AI는 수정 대상이 아니다. 최신 Main Leg SHA936CF02F…를 WaistJitter/BeforeManifest.json과 Before/에 백업하고 Source/Config/Original Character161개를 보호했다. Torso의 최신 왼쪽 어깨 stiffness*.95와 Hair는 보존한다.

현재 원인은 미확정이다. Iron2는 simulated이며 기존 천 관절 QA의 제외 대상이었다. 기존 editor-only helper의 IronAudit 및 optional PlayerWaistJitterProbe로 physics-off/정지후반/입력해제후반의32body 관절 변화·부모 움직임·실제actor와 active contact를 관찰하고, 진단용 NoIronContact에서만 두 Iron actor 접촉을 끄고 cleanup에서 복원한다. Main Source와 물리 에셋 수정0, 원작 physics field 미확인, 아직 해결 완료가 아니다.

최초 private cold build 실패는 stale Snow generated.h와 진단 helper TObjectPtr/Chaos float-vector 타입 오류였다. Work-only Snow header touch/-ForceHeaderGeneration 및 helper5줄 수정 후 ColdBuild_Probe_Retry.log 빌드 중이다. 재개는 own build결과 확인→PlayerPartsWork 별도 hidden/BelowNormal editor→Ready.pid/project 확인→job187 work-only AI 제거·IronAudit→job188 native PIE baseline 보존→자연 종료→같은조건 NoIronContact 대조→측정근거의 최소 asset수정→saved/native/stock 검증→Main Leg PA1만 최신동시변경 보호 전달 순서다. Main/Snow/Monster 에디터를 임의 종료하거나 예전 Source/Config/DLL로 되돌리지 않는다. 이전 Hair 일반시간간격 실패는 별도 미해결이며 full PASS로 덮지 않는다.

## 2026-10-08 11:14 KST — NPC4 전체 회귀의 fixture 감지 격리 보완 / 재개점

첫 Monster.PIE는 02:08:34 UTC Fail이었다. Monster_First.log에 원본을 보존했다. 32방향 실제 보행/포즈/contact(모든 medianSlip0)·35공격 section/root travel/cleanup은 통과했으나, 마지막 Swordsman의 최초 무인지 및 Alert 관측 두 assertion이 실패했다. 자기 검사 시작02:05:45 이전에 같은 actor가 01:59:26 Loop→End 및02:00:45 Step2→Step3를 이미 실행한 로그가 있어, 앞선 가족 검사 배치 중의 사전 발견이 확인됐다. 정확한 Sight event/획득 좌표가 없으므로 특정 retreat 좌표를 원인으로 단정하지 않는다. 타깃 유지 runtime를 되돌리거나 assertion을 완화하지 않았다.

기존 development-only FMonsterPIECommand에서 가족별 Sight 원래 enable bool만 저장하고, 자기 검사 때만 enable하며 완료 가족도 다시 disable하도록 보완했다. Cleanup/destructor에서 원래 sense 값을 복구한다. 현재 가족의 실제 Sight/Controller/StateTree 자연 흐름과 모든 기존 assertion은 유지한다. 새 runtime 파일0, 게임 Source6은 Facing 통과 당시와 byte hash 동일하다. Facing class부터 파일 끝30,434bytes도 동일이며 FacingPassed_KZMonsterAIPIETest.cpp/FacingPassedProof.json/IntegratedBuild_FacingPassed.log로 이전 정확 module·source·log·CSV를 보존했다. 이전 DLL에서 수행한 Facing Success를 새 DLL에서 다시 실행했다고 표시하지 않는다.

격리 수정 cold build IntegratedFinalBuild.log Succeeded(23.45s). 최신 Source/Config89 파일 snapshot에서 모든 비소유 Main/Work 파일은 동일하다. own27376는 throttle 복구 후 정상 종료됐고 새 own16676를 같은 /DevMap RenderOffscreen으로 실행했다. 재개는 이 PID와 MonsterMailbox Ready의 identity 대조→Khazan.Monster.PIE exact Success를 확인해 Monster_Final.log 보존→기존 통과 Facing runtime6/해당 test body의 동일성을 명시한 proof→guarded 전달→새 Main 저장값/loaded alias 및 CombatPolicy·Heal·Guard native 회귀다. Main 반영은 아직 전이며 기존 전체 authoring/이전 delivery를 반복하지 않는다.
## 2026-10-08 11:50 KST — NPC4 최종 병합 준비, Main 파일 잠금 대기

Monster.PIE 격리 수정 재검사는02:24:03 UTC Success다. Monster_Final.log/MonsterSummary.json의32방향·35공격·자연 Sight/대치/재추격/cleanup을 확인했고 contact sample 최소5/보고 median slip 최대0.000cm/s다. 기존 Facing 통과 후 사용자 Main에 새 SpinningAttack h/cpp 및 공통 ComboAction의 DoJump/Down notify 처리가 저장되어, 사용자 최신본을 Work에 intake/병합했다. CPP Main→Work 실제 diff는 우리 IsApproachingComboTransition 조회 추가뿐이며 사용자 현재 DoJump800/Down-500 LaunchCharacter 값은 사용자 코드에서 온 값이고 이번 어시스턴트 튜닝이 아니다. 원래 OwnedBaseline은 OwnedBaseline_Initial.json로 보존했으며 현재 CPP before CAS는 최신 사용자 저장본7F1F776…141F로 갱신했다. ConcurrentUser_ComboAction_Latest.cpp와 각 이전 snapshot을 보존한다.

최신 통합 cold build IntegratedFinalBuild.log Succeeded40.41s, module SHA c2a575f25fb9d107825b67ce00a14ec3c35a5e53cc7d417915e6c3839d2ac3f5다. 현재 Source86(owned7/비소유79)·Config5를 검증했고 사용자 새 native class2 및 Snow Source3을 포함한다. 구 Facing/Monster 테스트와 새 DLL의 차이를 VerifiedDeliveryProof에 명시했으며 최종 Main Facing35/CombatPolicy/Heal/Guard를 추가 검증해야 한다.

guarded preflight는 통과했다. 첫 전달 guard는 자신의 Source 하위 임시 staging 파일을 inventory 변경으로 감지한 오류였으며 Source 밖 Metadata/Staging으로 고쳤다. 그 후 전달은 첫 asset BS_Combat_Swordsman atomic replace에서 WinError5로 중단됐다. DeliveryFailure_20261008T024627432756Z.json에서 rollback={} / 새 alias없음 / needrestart=false, Main Source/BS/manifest 미변경을 확인했다. Build log는 Windows PowerShell UTF-16이므로 BOM에 맞춰 decode하도록 helper만 수정했으며 원본 log bytes는 보존했다.

읽기 전용 Windows Restart Manager는 Main editor PID13700이 Content/Monsters/Swordsman/Animations/BS_Combat_Swordsman.uasset의 잠금 소유자임을 확인했다. 기존 Main과 겹치지 않는 작업 지시를 지켜 해당 editor를 종료하거나 조작하지 않는다. 사용자에게 작업 저장 후 잠시 종료가 필요한 이유를 설명했고 응답을 기다리는 상태다. 별도 PlayerPartsWork28748도 조작하지 않는다. 잠금 대기 동안 최신 병합 DLL의 Facing 검증을 위해 own17772 /DevMap RenderOffscreen을 실행했다. Ready.pid/project를 대조한 뒤 FacingPIE를 진행한다.

정확 재개: own17772의 Ready 및 최신 log Test Completed 확인/새 Facing log·CSV를 별도 보존→Main PID13700 자연 종료/잠금 해제를 read-only inquiry로 확인→현재 Main Source와 before CAS/비소유79가 일치하는지 확인(사용자 CPP가 바뀌었으면 최신 저장본에 우리 조회만 재병합·Work build; 사용자 변경 덮어쓰기 금지)→deliver_monster_facing_20261008.py preflight/deliver→receipt15hash/alias 확인→verify_monster_facing_main_20261008.py를 정확한 별도 MainFresh abslog/ExecCmds로 새 background Main에서 실행→Facing/CombatPolicy/Heal/Guard Success/dirty0/ownquit 확인→최종 완료 MD 기록. 전달 성공 전 Delivery.json을 수동 생성하지 않는다. 사용자 Main13700/외부work는 종료하지 않으며 이전 전체 authoring/delivery를 반복하지 않는다.
## 2026-10-08 12:00 KST — 허리 장식 충돌 떨림 Center2 후보 적용·재실행 검증 중

`WaistJitter_20261008_probe_build` 중간 기록 이후 native 접촉 대조로 Iron2(`B_Iron_01_01_R/L_Pelvis`)의 외부 anatomy 충돌이 원인임을 확인했다. 진단용 접촉 비활성 대조만 안정화되며 최종 후보에서는 collision/simulation을 유지한다. Body/Leg 공통 골반 기준으로 ref 좌표를 맞춘 Center 검색이 통과했다. Work 파생 Leg PA의 두 capsule Center만 변경/저장했고, 모든 나머지 body/constraint/solver 필드의 동일성 검사를 통과했다. 최종 CandidateNative PIE는 Success이며 IdleLate/AfterReleaseLate Iron parent-relative step RMS는 0.1677~0.2072도/positive-delta frame, actor enabled/collision은 모두1이고 접촉 샘플도 존재한다. 기존 Baseline은78.8445~82.5556도다. 최신 BP/Source Work intake 및 probe 초기 bypass 수정이 있으므로 그 차이를 PA 단독 인과 효과로 단정하지 않는다.

Main target은 아직 before SHA256(`936CF…8960`)이며 Main 게임 Source/Config/에셋 수정0이다. Work candidate SHA256은 `6D3B02FDB05C1D11A4DC3B2A0C5E2799313434EB6E898CC4475E565BCDAFDEF0`. 기존 Hair/Torso 변경은 유지했다. 원작 physics 값은 미확인이며 새 Center는 LOD0 dominant support와 anatomy18에 기초한 어시스턴트 계산/임시 정책이다. `Metadata/PlayerParts_20261008/WaistJitter/CenterApplied.json`, `Comparison_Candidate.json`, `CandidateManifest.json`이 재개 정본이다.

현재 owned Work27052 /SavedReload fixed30 NullRHI 시작 단계다. 재개: Ready exact PID/project 확인 → `start_reload_jobs.py` mailbox 실행 → SavedReload native Success/CSV 및 collision flags 확인 → normal delta Iron 안정성 검사(기존 Hair 문제는 별도 기록) → actual selected Main base DLL의 isolated stock 저장 재로딩/Original5 확인 → fresh Main PID/world/noPIE/dirty/protected snapshot 후 기존 selective handoff를 Leg1개만 적용 → target CAS/hash/loaded값 및 사용자 최신 변경 보존 검증 → own editor 종료/stock fixture 복원 → 완료 append. 다른 Main/MonsterWork editor는 종료하지 않는다. baseline/NoIronContact의 과거 `PhysicsOff` label 구간은 초기화용 CVar 오류로 결론에서 제외한다. 관절 Frame2 1/100은 UE 보정과 일치하여 수정하지 않았다.
## 2026-10-08 12:07 KST — WaistJitter_20261008 최종 완료·재개 절차

앞선 11:10/12:00 중간 상태의 남은 실행·전달은 완료됐다. Center 모드만 실제 적용했고 SparseSpheres는 적용하지 않았다. Candidate / SavedReload / NormalDelta native 모두 Success, Stock Original5 + finite Torso12·Leg59·Hair72 / Iron idle150 positive samples도 통과했다. `FinalReceipt.json` complete=true, Main target SHA256 `6D3B02FDB05C1D11A4DC3B2A0C5E2799313434EB6E898CC4475E565BCDAFDEF0`, MainSelectiveHandoff/ReadyAudit success=true다. 보존된 `Verification.json`의 pending=true는 전달 전 QA 시점의 기록이며 최종 상태는 FinalReceipt를 따른다.

Main13700은 DevMap 그대로, PIE/종료/전체 저장/명시적 compile을 요청하지 않았고 protected163/dirty0/actor identity·selection을 보존했다. unrelated MonsterWork17772는 조작하지 않았다. Work stock fixture는 StockBinding.status=Restored 및 backup SHA로 복구했고 own editor1120 종료/전 own processes 종료를 확인했다. Hair/Torso PA hashes는 각각 `46F21D56060CAA90092C99B1F9722162A777B60DB6D9B06F3C0C2E2BA3D6857A` / `7560A4A740D8AD99370F7D210CC7A444A828EC0F14C4939141A8CD50A23CFCDE`를 유지했다.

다음은 사용자 Main PIE에서 재현하던 동작의 허리 육안 확인이다. 추가 떨림이 있으면 Router→physics 최신 정본→본 보고서의 exact PA SHA/Original node override를 먼저 확인하고, 해당 동작만 positive-delta native Iron2 probe로 측정한다. cached contact gap을 skin penetration으로 해석하지 않는다. 관절 Frame2 1/100은 현행 UE 보정과 일치하며 바꾸지 않는다. baseline/NoIronContact의 과거 PhysicsOff label은 초기화용 CVar 오류로 제외하고, 최신 probe의 EnableSimulation bypass/settling window를 사용한다. 이전 전체 ClothAuthor/HairAuthor/CollisionAuthor/shoulder author 또는 before PA를 다시 적용하지 않는다. rollback이 명시적으로 필요할 경우에만 현재 target을 final SHA로 CAS 확인한 뒤 이 report의 Before target1로 복구하고 Main의 선택 PA 재로딩을 시행한다. Main/다른 task editor를 임의 종료하지 않는다.
## 2026-10-08 — NPC4 최종 작업본 준비 / Main13700 파일 잠금으로 전달 대기

요청 세 기능은 MonsterWork에 구현/검증됐다. 현재 Main 게임 Source/BS/DLL/manifest 반영0, 성공 Delivery.json 없음이다. 최종 정본은 MONSTER_FACING_SMOOTHING_20261008.md의 마지막 절과 Metadata/MonsterMotion_20261008/VerifiedDeliveryProof.json이다. MainAssetLock_Final.json은 read-only Restart Manager로 BS_Combat_Swordsman.uasset 잠금 소유자13700을 확인한다. 사용자에게 저장·종료를 요청한 상태이며 사용 중인 Main을 임의 제어/종료하지 않았다.

마지막 build IntegratedFinalBuild.log Succeeded19.78s, 최종 Work DLL SHA a6bed111a0f59ae2ce46cb8978a6e1582e17dd3730c13bfdfbfb5ee8aadd49d7. Source8(런타임6·개발용test2), BS4, mailbox1, aliasDLL/PDB/manifest의16개 전달 대상이다. Snapshot91/비소유 Source78·Config5와 before CAS 검사가 통과했고 Preflight_Final.json success=true다. OwnedBaseline_BeforeHealFixture.json은 앞선7개 baseline 보존본이며 현재 OwnedBaseline.json은 올바른 flat8 rows다.

검증은 모듈별로 구분한다. c060 Monster.PIE02:24:03.446 Success(32방향·35공격/자연행동), c2a Facing02:57:16.698/Policy03:00:44.909/Guard03:10:18.987 Success, 최종a6 Heal03:25:43.152 Success다. 최종 rebuild의 변경은 기존 Heal test의 실제 Draw checkpoint 및 Stage5/8 자연 종료 gate뿐이며 runtime6/Monster test는 c2a와 동일하다. 과거 Heal 관측 시점 실패를 삭제하지 않았고 Player 제품 코드는 변경0이다.

own17772와 최종own25368은 정상 quit/throttle 복원, debugger session 및 agent breakpoint0이다. 현재 실행중인 사용자 Main13700만 남았다. 사용자 최신 SpinningAttack2/DoJump800·DoDown-500 및 unrelated Snow/PlayerParts 변경을 보존한다.

정확 재개: Router → Architecture 최신 → Migration → 위 최종 보고서/본 절 → 사용자 Main 저장·종료 여부 및 asset lock 확인 → 최신 Source/Config/before hashes 재검사(새 저장은 덮지 말고 재병합/build) → guarded preflight/deliver → 실제16hash receipt/alias → 별도 MainFresh editor exact ExecCmds/abslog/자기PID 확인 → loaded module SHA/CDO/BS 저장값/dirty0 및 Facing·Policy·Heal·Guard4 native Success → own 정상 quit → 실제 Main 완료 append. 실패 receipt는 수동 성공으로 바꾸지 않는다. Source8 전달 정의와 verifier SOURCE_FILES8이 이미 반영돼 있다.


## 2026-10-08 14:03 KST — ShoulderSoftening_20261008: 왼쪽 어깨 천 proximal 유연화 진행 중

사용자가 왼쪽 어깨 천이 특히 부착점 가까이 일자로 서서 뻣뻣하므로 더 펄럭이게 직접 수정 요청했다. Engineering physics 요청이며 Controller CPP는 대상이 아니다. Router/Engineering rules/current physics 정본의 최신 shoulder·waist 완료를 읽었다. 새 보고 폴더는 `Metadata/PlayerParts_20261008/ShoulderSoftening`이다. Main Torso before SHA7560A4…FCDE, Leg는 이전 허리 Center2 최종6D3B02…FDEF0, Hair46F21D…6857A를 보존한다. Main protected165 snapshot 및 target1 exact backup을 만들고 Main→Work Source/Config 표적 intake10개를 적용했다(Main 수정0). 사용자가 동시에 저장한 OverFury/Spinning/Controller/tags를 Work에 복사했으며 덮어쓰지 않는다.

현재 근거: 두 Root1은 몸과 겹침을 보호하는 kinematic animation anchor, 바로 아래01_02/02_02가 첫 sim이다. root anchor를 풀지 않고 기존8관절의 SLERP 강성/감쇠를 부착점 쪽에서 더 낮추고 proximal2 swing 여유를 늘리는 임시 조정이다. 원작 해당physics 값은 미확인이다. 기존 `LeftShoulderSpring` author와 optional shoulder metric에만 작은 확장을 준비 중이며 새 runtime 구조는 없다. 새 LongProximal01_02 group은 기존 quat를 재사용하고 QA cutoff를 바꾸지 않는다.

남은 절차: 두 helper 편집 완료→private cold build(single action/BelowNormal, Main compile 금지)→fresh baseline profile·PIE/shoulder4groups/Torso surface/Iron2 확인→Apply candidate Torso1 및 native 동일 fixture 비교→현상이 충분히 유연해지고 inside0/기존Hair35·cloth45/waist collision 유지면 saved fresh 및 normal-delta→Main selected DLL stock saved Original5→fresh Main PID/world/dirty/protected guard로 Torso1만 selective CAS/reload→final hashes/privatefixture복원/ownquit/완료MD. 현재 Main PID24552, own PlayerParts editor0이며 다른 editor를 종료/조작하지 않는다. 재개 시 Ready의 PID/project와 latest log를 대조하고 이전 full ClothAuthor/HairAuthor/CollisionAuthor 또는 *.95 baseline 재적용은 하지 않는다.
## 2026-10-08 — 플레이어 캡슐 눈 파임 및 기존 콤보 문제 후속 진행 중

사용자 직접 요청으로 기존 Snow owner의 h/cpp 및 개발용 Snow PIE test만 보완했다. PlayerControlled 캐릭터는 실제 scaled capsule의 바닥/반경과 기존 지역 눈 표면 profile을 사용한다. 플레이어 발별 stamp는 대체하고, 몬스터 발/몸 및 공격 중 실제 접촉 무기를 보존한다. 이동35cm/무기50cm/최대층55cm와 기존 C2 brush·rim·tile/cache·EndPlay 계약은 유지한다. 새 runtime 파일/class/component/UPROPERTY 및 map/material 변경은 없다. 기울어진 바닥에서의 원형 footprint는 지역 평면과 캡슐 하단의 근사이며 원작 직접 수치 또는 완전한 체적 교차라고 주장하지 않는다.

현재 Source3 실제 수정 및 static 검토까지 진행됐다. 아직 build/PIE/메인 native 전달 완료가 아니다. 최신 cpp에는 player 제어 해제 시 해당 capsule contact history만 지우는 cleanup도 포함한다. 정확 자료는 Saved/ImportReports/HeinMachSnow_20261006/PlayerCapsule_20261008/{Before,DeliveryBaseline,SourceIntake}. NativeBuildProof 및 StagePIE가 성공해야 Scripts/Engineering/heinmach_snow_capsule_delivery.py를 실행할 수 있다. 새 고유 alias만 발행하며 loaded normal DLL·사용자24552는 보존한다. 이후 같은 폴더 run_verification.py main으로 새 token/PID 소유 hidden Main 검증, 실제 Snow PIE·정상 종료·보호 hash를 확인하고 완료 기록을 추가한다. 이전 Snow Contact55/AttackContact의 완료 delivery를 재실행하지 않는다.

앞선 ChargeAttack03/SpinningAttack 요청도 유지된다. 현재 Main read-only 데이터는 Y/Spinning graph-only grant와 RB/OverFury grant가 정상이며 Charge02→03 edge 및 section도 존재한다. WeakAttack05에 InputOpen/InputCommit가 없어 Y edge가 실행 불가능한 정적 문제는 확인했지만 전체 증상의 원인으로 확대하지 않는다. 별도 Khazan_ComboWork_20261008/Khazan의 최신 cold build가 성공했고 own26416에서 debugger와 실제 입력 확인 중이다. Main 사용자 editor에는 breakpoint/PIE/저장/재로딩을 실행하지 않는다. Saved/ImportReports/PlayerComboRepair_20261008의 live JSON/CDO·montage T3D가 재개 데이터다. 실제 paused location/stack/value로 원인을 확정한 뒤 최소 변경 및 별도 검증으로 진행한다.

## 2026-10-08 14:26 KST — 플레이어 capsule Snow 후속 최종 완료

직전 진행 절의 Snow 작업은 완료됐다. Source3/Main alias 선택/canonical 보존/최신88Source cold build/Stage27416·freshMain19372 full Snow PIE/정상 종료/보호 hash 확인이 모두 성공했다. CompletionValidation.json complete=true 및 native Main actual loaded DLL a237a02f…7b58가 근거다. 상세 수식·scope·CPU 성능·수치 출처는 Snow 정본의 같은 날짜 완료 절을 따른다. 사용자24552는 계속 DevMap/noPIE/dirty0이며 save/reload/PIE/close하지 않았다. 새 코드 사용에는 그 running editor의 정상 재시작이 필요하다.

다음 Snow 후속은 현재 capsule Source/manifest/canonical에서 시작한다. 실행 중인 이전 DLL을 강제 교체하거나 옛 AttackContact/Contact55 helper를 재실행하지 않는다. 이번 publish도 기존 receipt가 있으므로 반복하지 않는다. Slot/Profile/map/material을 바꾸지 않았으며 현재 원작 pixel parity·모든 경사 체적 교차·자연 공격 전체 sweep 및 GPU/shipping 성능은 미검증 범위다. 별도 ComboWork26416의 Charge/Spinning 검증은 아직 진행 중이며 그 결과를 이번 Snow 완료로 합치지 않는다.

## 2026-10-08 14:39 KST — ShoulderSoftening_20261008 최종 Main 완료

이 문서의 14:03 KST ShoulderSoftening 진행 기록은 완료 상태로 대체한다. Torso PA1만 현재 Main24552/DevMap에 실제 전달·reload했고 protected166, dirty0, actor/selection 보존 및 MainReady BP7/Original5를 확인했다. 완료 receipt는 Metadata/PlayerParts_20261008/ShoulderSoftening/FinalReceipt.json이다. Hair·Leg/Iron 최신 보정과 고정 부착2개/충돌/solver를 보존했다. runtime 게임 소스·새 class/component 변경0이다.

마지막 검증은 Work native baseline/candidate Success → 새 프로세스 saved profile Adjusted readback 및 PIE Success → Main 실제 mapped C251AC base DLL stock finite Original5/허리 관측 → Main PA1 CAS/reload Success → private binary exact restore/owned editor0이다. helper는 Spring/Damping/Swing1/Swing2와 그 saved default profile 외 authored fields를 full-copy 비교했다. 짧은 첫 관절 speed RMS+29.82%, 긴 첫 관절+2.72%이며 긴 천의 지속 flutter 증가를 확정할 정도의 time-series는 없다. Torso 세 표본 inside0이며 전 pose/skin 충돌0 보증은 아니다. 수치는 원작 미확인 임시 튜닝으로 TemporaryTuning.ini/CandidateProfileAudit.json에 정확히 남겼다.

재현 과정 실패 기록은 보존했다. 처음 native 실행의 Input.Action.RB 오류는 오래된 Work 입력 에셋을 Main 최신 DA_InputData/IA_RB/IMC_Default로 동기화해 해결했다(Main 쓰기0). 근접 카메라 default property notify 뒤 파츠 관측0은 NEVER notify 재시험에서 정상 관측으로 돌아왔다; 재구성 실제 호출을 계측하지 않았으므로 source상 가능한 원인과 실제 재시험을 구분한다. 첫 Main rename WinError5는 target old hash 유지 상태에서 재시도해 성공했다. 실패 native/log/receipt를 성공 결과로 덮어 쓰지 않고 별도 파일·MainSelectiveHistory에 보존했다. Stock 카메라 회전 positional 실패도 named Rotator로 고쳐 StockClose.png를 별도 확인했다.

미완료된 필수 cloth 작업은 없다. 후속 요청 시 FinalReceipt → 정본 이번 완료 절 → NativeComparison과 저장 후보 profile에서 시작한다. 현재 Torso 후보 hash와 Hair/Leg protected hash를 먼저 확인하고 필요한 Cape 관절만 새 baseline으로 삼는다. 이전 full ClothAuthor/HairAuthor/CollisionAuthor·waist 전체 튜닝/배송을 재실행하지 않는다. 현재 Main 세션에는 재시작이 필요 없는 PA reload가 완료돼 있다. Snow의 별도 새 DLL 재시작 필요 기록은 해당 작업 범위이며 이번 cloth 완료와 합치지 않는다.

## 2026-10-08 14:39 KST — ComboWork 후속 Main 최종 완료

직전 ComboWork 진행 기록의 남은 authoring/전달/최신 Main 검증은 완료됐다. Weak05 Y 실패 before/after 증거와 원작 reserve→dilation/normalized timing의 계산 출처를 확보했고 montage1개만 2notify 추가해 Main6f75…966ad9로 전달했다. 첫 atomic copy WinError5는 원본을 바꾸지 않았고, clean/noPIE 상태에서 선택 montage의 FullyLoadPackages/CAS/ReloadPackages로 해결했다. 기존13 notify/모든 segment/section/Source/Data/BP와 actor identity/selection/dirty0를 유지했다. 전체 사용자 editor scope는 MainSelectiveHandoff.json이며 disk publisher 단독의 editor_reload=false/untouched 문구로 전체 handoff를 해석하지 않는다.

Fresh Main7164 suite7이 성공하고 Source/asset192 before/after 및 종료 후도 동일하다. actual capsule aliasa237…7b58/정상quit/PIE끝/dirty0/throttle복원/agent breakpoints0, user24552 유지다. CompletionValidation.json complete=true와 FreshMain/MainVerification/Cleanup.json이 최종 근거다. Snow capsule 후속도 이미 완료됐으며 새 native code에는 사용자 running editor의 정상 재시작이 필요하다. 자동종료/강제LiveCoding은 실행하지 않는다.

후속 재현은 현재 saved montage/alias에서 시작한다. 이전 일반 Weak01/Charge/RB live 실패는 latest cold/Main에서 재현되지 않아 원인 미확정이다. 너무 이른Y는 실제로 창 밖에서 무시되지만 당시 사용자 timing 답은 미확인이다. 추가 증상이 있으면 동일 실제 입력의 실패 node/window/held phase를 수집하고 필요시 own background debugger를 사용한다. Controller global remap/command-first 구조 또는 임의 추가 buffer를 근거 없이 적용하지 않는다. 이미 완료한 data writer/delivery/Main full suite를 되풀이하지 않는다.


## 2026-10-08 15:00 KST ? ??? ?? ?? / ?? NPC4 ?? ?? ? ?? Source ??

?? ??? ???6? HP?Stamina **???**? Main ??12asset?fresh Main27884 saved reload24modifier?dirty0?normal quit???95 SHA ??? ????. ???/???? ?? ??? ?? ??. ??? Main24552? ?? ???? ?? ???? ???? ?????? ??/???? ???. own Work15348/28116 ? Main27884? ???? ?? ?? Unreal process0??. ?? ???? ??? ??? PID? ??24552/13700?? ???? ???. FinalVerification.json ? MONSTER_AI_IMPLEMENTATION_20261006.md ?? ?? ?? ?? ???? stats authoring/??? ????? ???. Apes/Yetuga? ??? ??? ??, gameplay actor/registry ????? ????? ??? ?? ????.

?? NPC4 ????? ?? ARCH-80? ??? Main ?? ???. ? ??? ?? Main lock ?? ??? ?? ?? ?? ??? ???. ?? ?? `Metadata/MonsterMotion_20261008/ResumeIntakeAfterStats_20261008.json` ???? ?? motion proof ?? Main Source8?? ??? OverFury h/cpp2? ????. ?? ??? KZGameplayTags h/cpp, ComboActionAbility cpp, Snow h/cpp/test, PlayerController h/cpp?. ?? Source/??? ??? Work DLL ?? non_owned_source snapshot?? ???? ???. ?? stats ??? ? Source? ??? ???.

?? motion ??? ?? Main Source/Config/???????? input/??/OverFury/Snow? ??? ?? snapshot??? motion ?? diff? ?? Work? ?? ??(?? ComboActionAbility ??? notify/?? ??)?? integrated cold build ? ??? Facing/Monster/CombatPolicy/Heal/Guard ???? evidence/proof? ??? inventory ??????/?? editor identity??? CAS ???motion ?? ?? ???fresh Main ?? ???. ?? deliver helper? strict inventory guard? ? proof ?? ???? ? ??. ?? ??? DA/GE12? motion ?? ??? ?? ?? ????. ?? ?? author/retime/Source ?????Module manifest rollback? ???? ???.

## 2026-10-08 — PlayerAttackCollision 진행 중 / 재개 기준

현재 root task: 모든 현재 Player ComboAttack collider, duration/multihit 정책, Editor damage, Green debug, monster HP/Stamina. 최신 기준 ARCH-81. 작업 Source는 Khazan_ComboWork_20261008/Khazan의 KZComboDefinitionData.h와 KZComboActionAbility.h/cpp 3파일이며 Main Source/Content 아직 미전달. SourceBefore.json이 시작 Main/Work hash이다. original 추출/Box extent 증거는 Metadata/PlayerAttackCollision_20261008/Original. 새 damage GE는 Work에만 생성했고 준비된 사용자 MonsterStats 초기 효과4종을 재사용했다.

첫 Work build는 FOverlapResult 헤더 누락으로 실패, Engine/OverlapResult.h 추가 후 cold build 성공했다. 이어 timer 중복·section handoff flush 수정은 아직 재build 전이다. 첫 own editor6528은 ExecutePythonScript의 정상 autoquit로 종료됐으며 log 보존. 현재 own editor30120은 ComboWork /Game/Maps/DevMap / hidden RenderOffscreen / BelowNormal / RiderLink disabled, 기존 Scripts/Engineering/combo_isolated_editor.py PID+session mailbox만 사용한다. Metadata/PlayerAttackCollision_20261008/mail_job.py 30120 SCRIPT_PATH로 현재 Ready.json의 PID/session guard 뒤 요청한다. shared Main editor 자동 PIE/compile/save-all/close 금지.

다음: agent CurrentNodeMapping.json과 collision author script → Work data author/pose QA → own editor 정상 종료 → 최종 Source+dev PIE fixture cold build → fresh own PIE 실제 hit/window/group/outside/cancel/clamp 및 Guard/Heal/기존 Combo 회귀 → saved reload → 최신 Main CAS/선택 backup/copy/build/새 자체 Main saved audit. 문서/actual build/PIE/Main 완료를 분리한다. 위 임시 HP10/Stamina5 및 source 미확인 shape/time fallback은 Source 필드와 원작/계산/임시 설정 보고서에 명시한다. 이전 PlayerParts/Snow/Monster 변경과 몬스터 전체 definition/grants/AI/locomotion은 덮어쓰지 않는다.


## 2026-10-08 15:52 KST — MonsterStamina 작업 중 및 이전 stats 기록 가독성 보충


기존 15:00 KST 몬스터 초기 수치 기록의 일부 한국어가 작성 과정에서 물음표로 손실되어 이 절에 가독성 있는 사실을 추가한다. 이전 기록은 삭제하지 않는다. 몬스터6의 GE_Init/CharacterDefinition 12개는 이미 Main 적용과 fresh saved readback을 완료했다. 값은 Swordsman/SwordShield HP100·Stamina50, HeavySwordsman/HalberdElite HP200·Stamina50, Apes HP400·Stamina100, Yetuga HP1000·Stamina150이고 모두 current=max이다. 근거는 Metadata/MonsterStats_20261008/FinalVerification.json complete=true 및 WorkSavedReload/MainSavedReload.json이다. 그 작업은 설정만 한 것으로 소진/회복/피격 기능 완료와 구분한다. Player 초기 GE2와 당시 Source/Config를 보존했다. Apes/Yetuga 당시에는 Definition/GE만 있고 gameplay BP/registry 연결은 없었다.

새 사용자 요청은 여섯 몬스터 공통 무자동회복·무공격Cost, 편집 가능한 피격/패링 감소량, 스태미너0 소진, 브루탈 어택의 양쪽 정상 완료 후 생존 MaxStamina 회복이다. 상세 계약과 수치 출처/미확인은 Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md를 따른다. 현재 native 구현은 별도 Khazan_MonsterWork_20261006/Khazan에만 있으며 Main 게임 Source/에셋 미전달이다. 첫 빌드는 다른 editor의 전역 LiveCoding mutex로 거부되어 독립 Work 출력에 NoHotReloadFromIDE로 재시도 중이다. 실제 성공 전 build/PIE 완료로 쓰지 않는다.

현재 소유: root는 Work CharacterDefinition·Tags·Action·ASC·Monster·AIController 및 BrutalAbility를, yetuga_public_patterns는 ExhaustionAbility와 새 native PIE test 하나를, apes_public_patterns는 Main Scripts/Engineering의 scoped author helper를 담당한다. 원작 조사 결과19packages/CS6/AP6는 저장 evidence를 재사용한다. 새 전체 Content 조사/재추출/재임포트는 하지 않는다.

정확 재개: NativeInitialBuild_NoHotReload.log 결과 확인→선택 author helper를 Work 임시 Editor deps/include로 컴파일→Work 자기PID/project/mailbox만으로 작성→새 프로세스 저장 재로드→native Stamina PIE 실제 피해·패링hook·소진·paired 완료/취소/죽음 테스트→Editor helper/deps 제거 후 stock build→최신 Main Source/asset CAS 및 외부 Combo 피해 작업과 교차 병합→선택 전달→별도 자기 Main 검증·정상 quit→완료 기록. 현재 Main user PID31344와 외부 Combo26104/AttackVFX9424는 비소유이며 조작/종료하지 않는다. PID는 재개 시 새로 조회한다.

이전 NPC4 Facing/보간 Main 전달도 미완료다. 최신 Main Source intake가 필요해 WorkBefore에 이전 Work Source/Config/DLL/PDB를 보존한 뒤 현행 Main93 Source/Config를 Work에 복사했다. MainSourceBefore.json과 WorkBefore.json이 정확한 시작점이다. 예전 Motion DLL a6bed... 및 VerifiedDeliveryProof는 현행 전체 Source와 달라 그대로 전달하면 안 된다. 이번 초기 stats의12asset을 반복 authoring하지 않는다. 원래 별도 Facing 재병합·검증 의무는 보존하며 이번 스태미너 완료와 혼동하지 않는다.


## 2026-10-08 — Player Combo 공격 충돌 구현·전달 완료 / 구 Main 재시작 절차

- 상태: runtime3기존파일+DEVfixture1+DA/GE2 선택 전달 완료. 원작 기반 node18/window60/key553 및 editor damage/green draw 설정 포함. 별도 최신 compile/link Success, 충돌13case 재검증 Success, input6양성+1예상 거절, Guard/Heal Success, 새 Main 저장 readback Success.
- 마지막 검증: 새 Main PID2512가 전달 alias module로 전체 저장 schema/GE/Player BP/dirty없음을 확인하고 정상 종료했다. 실행 중 Main PID31344는 stock old DLL 유지; shared PIE/compile/save-all/restart 없음. 보호146files와 stock binary hash 보존. 정확한 후보/이전본/native source snapshot은 Metadata/PlayerAttackCollision_20261008/의 PreparedDeliveryManifest.json, SourceContentDelivered.json, NativeAliasDelivered.json, FinalDeliveryVerification.json, Before/를 사용한다.
- 별도 캡처 helper는 미노출 Python API 오류로 gameplay 검증에서 제외했다. ActualWeakNormalTarget.json 기록은 product 실패/원작 시각 일치 근거가 아니다. 원작 Cylinder 높이/미직렬화 Shape/OverFury 첫 mapping/절대 damage·Guard 근거는 여전히 미확인 또는 임시다.
- 정확한 다음 절차: (1) 사용자 Main을 정상 재시작한다. (2) /Game/Data/ComboCommand/DA_Player_Combo_Definition → Nodes → AttackWindows에서 HPDamage/StaminaDamage/shape/extent/window/keys를 확인하고 Draw Attack Collision checkbox로 green draw를 제어한다. (3) 정상 capsule Monster를 대상으로 실제 플레이해 범위·Cylinder 높이·첫 OverFury 타이밍과 피해량만 필요한 만큼 조정한다. (4) 결과를 현행 구현 정본 하단에 추가한다. 구 schema editor로 해당 DA를 저장하거나 이미 전달한 전체 asset/Source를 다시 덮어쓰지 않는다.
- 다른 Task가 module manifest나 Source를 새로 바꾸면 그 최신 구현을 보존하고 해당 task build를 사용한다. 과거 stock DLL로 되돌리거나 본 task alias를 무조건 재복사하지 않는다. 원작 source metadata·성공 fixture·author 작업을 근거 없이 반복하지 않는다.

## 2026-10-08 — Player 공격 VFX 최종 렌더 검사 중 / Main 미전달

- 작업: 현재 Player 공격18node의 원작 메타데이터 Particle297/Decal50 재생 이관. 자세한 계약은 `PLAYER_ATTACK_VFX_RUNTIME_20261008.md`, Art는 `../Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md`다. private project는 `Khazan_AttackVFXWork_20261008/Khazan`이며 Main Source/Content를 아직 변경하지 않았다.
- 완료 검증: private native compile/link Success, precise notify author6몽타주, fresh SavedAssetAudit347EventId/694Start-End/원래 gameplay GUID별 정확한 native BP trigger 보존, Weak·Spinning 전체139bone prefix 검증. 실제 RHI `Khazan.CombatEffect.PIE`는 두 번 Success; 최신 실행은 `Saved/ImportReports/PlayerAttackVFX_20261008/RuntimePIE`의 Driver/Exit/PrivatePIE.log, 공격18node와 실제 Monster HP110→100 및 조건부 PSC2. 모든347effect의 visual positive를 주장하는 테스트가 아니다.
- 미완료 원인: 최종 실제 OverFury montage1.0086839초 `RuntimePIE/121_AM_DAS_Player_OverFury_OverFury.png`에서 거대한 검은 slash/dust 면이 발견됐다. 특정 혈흔 master의 부모 Masked/자식 Translucent MP_Opacity 누락은 private에서 수정했으나 다른 공격 master의 같은 누락을 조사 중이다. Native 성공을 전체 visual 성공으로 기록하지 않는다.
- 전달 상태: `MainDelivery_BeforeOverFuryAlphaFix`는 준비·백업만 한 후보 기록이며 Main에 적용하지 않았다. 후보 art hash 변경 후 예전 Prepared를 재사용하지 않는다. 사용자 Main PID22560은 작업 외부에서 종료돼 마지막 census에 Main 프로세스가 없었으며 Root는 사용자 에디터를 종료하지 않았다. 전달 helper는 running clean exact-package release 또는 실제 closed-mode census/exclusive file proof를 요구한다.
- 정확한 재개: shader agent의 source-confirmed targeted alpha input 보완→새 ArtCandidateManifest 및 실제 OverFury render→필요한 Saved/Native proof 갱신(소스가 바뀌지 않으면 불필요한 빌드 반복 없음)→최종 private RHI/asset QA→`deliver_player_attack_vfx.py --prepare` 새 후보/backup→fresh MainRelease(실제 process census)→Root `--apply`→자기 fresh Main `run_player_attack_vfx_pie.py --main` 검증/정상 종료→문서 최종 완료 추가. 현재 Source/Config/Data/Maps와 별도 collision·monster 작업의 최신 변경을 CAS로 보존한다. old normal DLL이나 다른 task manifest를 임의 복원하지 않는다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

이번 요청의 Main 전달·검증은 완료다. 기존 다른 Task의 미완료 상태를 이 절로 취소하거나 완료 처리하지 않는다. 최종 evidence: Metadata/MonsterStamina_20261008/FinalVerification.json complete=true, NativePIE.json 453/0실패, IntegratedRegression.json 회귀5종 Success, StockDeliveryBuild.log Succeeded, DeliveryReceipt.json105행, MainSavedReload.json 실제 alias/CDO/BS4/dirty0. 새 Main readback PID16924는 commandlet 성공 exit0으로 종료했다. 사용자가 쓰던 editor는 조작하지 않았고 별도 Work30028/11040만 정상 quit했다.

최초 native 실패는 초기 intent fixture 문제, 최초 충돌 실패는 Work에 없는 최신 Main montage/sequence 참조 문제였다. NativePIE_FirstFailure와 첫 Regression log를 보존했다. 최신 Main 참조30개 중 누락10+stale3를 Work에만 가져온 LatestCollisionClipIntake.json 이후 충돌13case가 Success다. Main 기존 collision Source/DA/GE를 다시 author하거나 입력을 Python으로 주입하지 않았다.

다음 사용 절차: (1) Main 프로젝트를 정상 새 실행한다. (2) DA_Character_<family> → Monster Stamina에서 parry/timeout/BrutalHPDamage/range를 조절한다. (3) DA_Player_Combo_Definition → Nodes → AttackWindows에서 공격별 StaminaDamage를 설정한다. (4) 공격으로 0까지 소진시킨 뒤 가까이 앞/뒤에서 X로 Brutal을 실행한다. 생존 시 양쪽 완료와 End 후 Max 회복, 죽으면 회복 없음이 예상 결과다. BrutalHPDamage는 현재 미할당0이므로 원하는 피해값을 먼저 설정한다. 기회 시간을 무기한으로 원하는 경우 ExhaustionSeconds=0으로 바꾼다.

실제 패링 판정 생산자가 생기면 성공한 사건 한 번에 AKZMonster::ReportAttackParried(Defender)를 호출한다. 일반 Guard 성공에는 연결하지 않는다. Apes/Yetuga 시험은 해당 BP를 DevMap에 배치할 수 있으나 자율 AI는 후속 구현이다. 별도 lethal Execution 연출과 pose-contact 원작 동일성은 완료로 보지 않는다.

정확한 재검사: 격리 Work에서 Scripts/Engineering/MonsterStaminaPIEEditor.cpp만 Source/Khazan/Tests로 복사하고 Work Build.cs에 QA용 Json dependency를 임시 추가한 뒤 cold build한다. 전용 mailbox editor를 새 실행하고 그 Ready.json의 PID/project를 확인해 Automation RunTests Khazan.Monster.StaminaPIE와 native PIE를 실행한다. fixture의 실제 source SHA8ba086cd0e52a291d662e592435765fd65f291667ebf41b93d0df14a24e9efca를 확인한다. author cpp 두 개는 이미 적용된 에셋 재작성 용도이므로 테스트만을 위해 복사/실행하지 않는다. 테스트 후 임시 fixture/Build.cs 변경을 제거하고 stock build한다. 사용자 editor에 mailbox/test/compile/save-all을 보내지 않는다. 새로운 Source/manifest 변경이 있으면 최신 작업을 보존하고 과거 payload를 재전달하지 않는다.


<!-- MonsterStaminaConcurrentMainBuildVerified_20261008 -->
## 2026-10-08 17:39 KST — 후속 Main 기본 DLL 빌드 보존·재검증

전달 완료 뒤 본 작업이 시작하지 않은 Main native build가 새 canonical DLL과 manifest를 만들었다. 해당 build는 Succeeded이고 선택 모듈은 현재 `UnrealEditor-Khazan.dll`, SHA `3a2b4942da22fdf94cc7cf6581da3b5fb04f63475315c675d66ef6c4782e758d`다. 이전 unique alias 전달·canonical 보존은 당시 사실이며 현재 모듈 선택을 과거 alias로 되돌리지 않았다. 전달105행과 전체 Source/Config가 검증한 현재 구현과 동일한 것을 확인했다.

별도 fresh Main commandlet에서 현재 canonical DLL을 실제 로드해 저장 Definition6+Player1/montage20/sequence49/attackBP35/body2 및 NPC4 BS·CMC/AI CDO·dirty0를 다시 확인했고 exit0으로 종료했다. 증거는 Metadata/MonsterStamina_20261008/{ConcurrentMainRebuild,FinalVerification_CurrentMain,MainSavedReload_ConcurrentBuild}.json과 ConcurrentMainBuild.log다. 이 새 DLL에서 native453/회귀5종을 다시 실행한 것은 아니며 동일한 제품 Source의 이전 Work runtime 결과와 새 Main saved readback을 구분한다. 사용자 Main19576은 읽기 inventory로만 확인했으며 제어·PIE·저장·종료하지 않았다. 이제 현재 Main 기본 DLL을 사용하고 과거 전달/authoring helper를 재실행하지 않는다.

## 2026-10-08 18:37 KST — 최신 병행 변경 동기화·Brutal VFX 추가 검증 진행

이전18node 성공 검사 뒤 최신 RuntimePIE는 FAIL이다. 최근 Main에 전달된 KZBrutalAttackAbility/KZExhaustionAbility 및 Brutal DAS7개가 private snapshot에 없어서 InitialAbilityGrant AbilityClass=None/몽타주 의존 누락이 발생했다. 최신 Main Source93개와 unowned14Source/새DAS7개를 private에 guarded intake했고, Combo2는 보존된 이전 intake를 base로 exact three-way 병합했다. 증거는 SourceIntakeHistory/20261008T092852045375Z/Applied.json 및 RuntimeAudit/LatestSourceRebase/20261008T092216Z/CASProof.json이다. Main Source/Content는 아직 VFX 작업으로 쓰지 않았다.

동일 RHI에서는 FM_World_SubUV_color_A의 활성 Custom UV 입력 누락으로 SM6 child가 DefaultMaterial/checkerboard가 됐다. 이전 parent compile0을 actual child/render 성공으로 해석하지 않는다. 실패 Driver/Exit/log/139PNG를 보존하고 private shader에서 연결을 수정 중이다.

최신 실제 Player Front/Back Brutal도 현재 모든 공격 요청에 포함한다. 원본 Common/Grapple5 composite에서54개(Particle48/Decal6) window를 추가 분석하며 기존347개/6몽타주 author는 보존한다. 현재 모든 family BrutalHPDamage0 설정은 임의 변경하지 않는다. 적중 조건10Particle+6Decal은 actual negative HP GE 성공에서만 재생한다. 공유 spawn/stop/cleanup은 기존 ActionAbility로 이동하며 Combo 전용 hit/node/execution 관측은 기존 소유자에 남긴다(ARCH-83). 아직 build/Brutal author/새 native RHI/Main 전달은 미완료다.

정확 재개: 현재 agents의 private Action2/Brutal2/Combo2 공유 구현+기존devtest확장, 독립 Brutal54plan/2몽타주 precise author/8몽타주 fresh audit, SM6 smoke UV 보완 완료를 확인→소유 author editor 정상 종료 후 private build→11Source/8몽타주/401event 후보 proof→새 private 실제 RHI 전체18node+Front/Back+취소/positive hit/HP0 검사→현재15Art hash를 actual attack/floor 제한QA에 결합→선택34파일/23패키지 Main clean loader release/CAS/고유 DLL alias 전달→own freshMain RHI/저장 재로드→완료 추가 기록. 사용자의 Main PID16572는 read-only DevMap/PIEfalse/dirty0이며 강제 저장/종료/PIE/native reload를 하지 않는다. 옛 proof/pass/12Art 후보를 재사용하지 않는다.

<!-- PlayerAttackVFXMainComplete_20261008_1911 -->
## 2026-10-08 19:11 KST — Player 공격 VFX Main 완료 / 정상 재시작 절차

상태는 Main 선택 전달 및 fresh Main runtime/saved 검증 완료다. 이전18:37의 missing native grant/SM6 checkerboard와 통합 대기를 완료 상태로 대체한다. 실패·이전 proof는 보존하며 재사용하지 않는다. 최신 전체 Source build Success 이후11Source(runtime10/dev1)+8몽타주+15Art=34파일/23패키지만 전달했고, 독립 Main 변경·Config·기존 canonical DLL을 보존했다. 실제 선택 alias SHA는 `ece6db2ebaaaa98fbbd0235553bba1691d5e520a12a563410aad2ee082032a99`다.

마지막 검증은 hidden Main12708의 실제 alias 로드·18 Combo+Brutal5case Success/176captures/compile·default fallback0/save0/exit0, 별도 Main32404의8몽타주401ID·802start/end·8,308field 저장 재로드 Success/save0/exit0다. 제품 BrutalHPDamage0의 조건부 혈흔0은 VFX 실패가 아니다. transient HP/16=6.25 fixture에서만 실제 피해·조건부 효과 양성을 확인했으며 saved Definition 피해량은0을 유지했다. 상세 계약·adapter·한계는 [실행 정본](PLAYER_ATTACK_VFX_RUNTIME_20261008.md)의19:11 완료 절, 증거는 [FinalVerification](../../Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json)과 같은 task의 MainDelivery/Delivered, MainRuntimePIE/ActualNativeModule·Driver, MainCombinedSavedAssetAudit를 따른다.

사용자 PID16572의 마지막 읽기 상태는 DevMap/PIEfalse/dirty0이며 save/PIE/close/reload를 보내지 않았다. 남은 사용 절차는 현재 Main 에디터를 사용자가 정상 종료·재실행하고 새 모듈/schema에서 공격 몽타주를 확인하는 것이다. 구 모듈 에디터에서 새 Notify 몽타주를 저장하지 않는다. 원작과의 픽셀 일치·BattleEffectIndex/첫 Brutal 적중 연결·멀티플레이는 별도 미검증 범위다.

정확 재검사: Router→Architecture ARCH-83 완료→Migration→실행 정본19:11과 현재 Source/선택 모듈을 먼저 확인한다. 현재 snapshot과 일치하는 별도 task-owned hidden 프로세스에서 `Scripts/Art/player_attack_vfx_pie.py`의 `Khazan.CombatEffect.PIE` 및 `player_attack_vfx_main_combined_saved_audit.py`의 읽기 감사를 실행한다. PID/project/actual module guard와 package save0을 유지한다. 원본 재추출·전체 author·retime·delivery helper·옛 module manifest 복원은 재검사의 전제 작업이 아니다. 후속 Source/에셋 변경이 있다면 최신 전체 snapshot을 다시 보존·빌드·검증하며 과거 DLL/proof를 그대로 전달하지 않는다.


<!-- MonsterBrutalDamage50_20261008 -->
## 2026-10-08 19:48 KST — 브루탈 어택 총 HP 피해 임시50 설정

사용자 요청으로 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga의 `/Game/Monsters/<family>/Data/DA_Character_<family>` → Monster Stamina → `BrutalHPDamage`를0에서50으로 저장했다. 단위는 HP 절대량이고 원작 환산값이 아닌 사용자 지정 임시 튜닝이다. 앞/뒤 공통 브루탈1회당 총량이며 기존 `BrutalHit2`에서 한 번 적용한다. 패링·일반 공격의 Stamina 감소량과는 별개다. 이전 미할당0/조건부혈흔0 기록은 당시 검증 상태로 보존하며 현재 설정은 이 절의50을 따른다.

수정은 CharacterDefinition6개의 해당 필드뿐이다. 다른 stamina 설정·LocomotionConfig·UnawareRoutines·InitialAbilityGrants·InitialEffects를 수정 전후 및 새 별도 Main commandlet 재로드에서 동일하게 확인했다. Source/런타임 클래스/몽타주/모듈 선택은 편집하지 않았다. metadata 증거는 `Metadata/MonsterBrutalDamage50_20261008/Authoring.json`, `FreshSavedReadback.json`이며 원본6파일은 같은 경로 Before에 보존했다. 두 commandlet은 별도 프로세스로 성공 종료했고 사용자 에디터를 제어하지 않았다.

이번 검증은 저장된 값50과 다른 필드 보존의 읽기 검사다. 기존 양수 피해/중복 방지/양쪽 완료 native 검사와 VFX transient6.25 검사는 과거 결과이며50으로 PIE를 새 실행한 것으로 기록하지 않는다. 기존 확정 적중을 읽는 VFX 정책은 이제 실제 양수50 피해에 적용될 수 있으며 VFX가 추가 피해를 만들지 않는다. 조정은 같은 DA의 BrutalHPDamage에서 수행하고, 과거0인 author receipt/asset payload를 현재 설정 위에 다시 전달하지 않는다.


## 2026-10-08 — CombatReaction 진행·재개

Router→Architecture/Migration/현재 Source와 저장된 metadata를 읽었다. Main을 건드리지 않고 기존 Khazan_MonsterWork_20261006에 최신 Source/Config와 표적 Content를 guarded stage했다. Metadata/CombatReaction_20261008/StageBaseline.json(709행,49복사)이 현재 Main CAS 기준이다. Work 기존 파일은 WorkBefore에 보존했다. 최신 ARCH-83 VFX 및6 Definition의 BrutalHPDamage50을 보존한다. 사용자 editor를 제어하지 않는다.

현재 Work에 CharacterDefinition 반응 pool/종류 enum, native event6개, Combo window 반응 종류·노드 SystemGuardWindows만 추가했다. 단일 HitReactionAbility를 병행 구현 중이고 Art 분류221enemy/24player 및 Shield/Brutal 원본 보고서를 표적 조사했다. 아직 현재 task build/author/PIE/Main 전달을 실행하지 않았다. 재개: 같은 Work 새 native HitAbility→Combo 양방향 피격/Shield→기존Brutal swept 접근→별도 소유 editor에서 InGame player reaction·montage/Definition 데이터 작성→native/저장 재로드 검사→임시editor helper 제외 stock build→StageBaseline/CAS 선택 Main 전달→새 독립 Main검사→완료 기록. 과거 stamina/VFX DLL과 proof를 이번 검사로 재사용하지 않는다.

## 2026-10-08 20:20 KST — Monster6 VFX 작업 착수

현재 혼합 작업의 런타임 계약은 ARCH-84이며 별도 C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan을 생성했다. Main Source/Config·Player/Maps/Data·6가족/Effects의 baseline14304파일과 기존 native module SHA는 Saved/ImportReports/MonsterVFX_20261008/WorkBaseline.json에 보존한다. 다른 Content junction은 읽기 전용이다. 기존 Main actor/editor·모듈을 재시작/PIE/저장하지 않는다.

현재는 원작 notify/시각 의존성 조사와 최소 runtime 작성 전 단계다. Metadata/MonsterVFX_20261008/{HumanOriginal,ApesYetugaOriginal,RuntimeAudit.json}을 재사용하고 전체 추출/retime/기존PlayerVFX author를 반복하지 않는다. Human629clip 및 ApesYetuga212clip에서 원본 이벤트를 표적 읽으며 추가49개의 gameplay copy와 타이밍/조건은 각 manifest를 따른다. importer는 Effects 전용 private 폴더만, runtime은 private Source만, 최종 sequence author는6family private폴더만 저장한다. 실제 성공·실패/마지막build/남은작업은 후속 날짜별 기록과 단계별 report에 추가한다.
<!-- PlayerAttackVFXPolish_20261008_Checkpoint_2104 -->
## 2026-10-08 21:04 KST — 공격 VFX 품질 수정 private 검증 진행

현재 직접 요청은 Art/Engineering 양쪽이며 새 증거는 `Saved/ImportReports/PlayerAttackVFXPolish_20261008`에 분리한다. Main 제품 Source/에셋/모듈은 아직 미변경이다. 현행 KZActionAbility sourceLocal×첫 sourceCorrection inverse×live anchor 계산을 확인했다. UE transform 곱 순서·Scale 분리·source particle rotation24개는 일치하며 근거 없는 전역 yaw/scale 변경은 하지 않았다. 원본6 correction sample을 현재 첫 sample만 쓰는 adapter와 실제 montage/socket timing을 추가 검토 중이다.

Private 변경 Source는 개발 검사 `Tests/KZCombatEffectPIETest.cpp`1개다(SHA9868de5b89c589a09b94c0b1215efce6a5d09835db746f819ec04c1ae8557155). 기존 HP0 고정 assertion을 transient0 negative case와 현재 저장된 BrutalHPDamage50 positive/cancel case로 구분하고 원래 Definition 보존을 검사한다. Optional transform JSONL은 개발 검사에만 있으며 runtime API/schema/생산 능력 코드는 아직 미변경이다. Build exit0(17.594s), private native SHA47058389f14eb8b70122e04f61891de9d29d30bef399a9924bfeeae6e07ed8e9. After01 PID1364 실제 RHI134.508s exit0, native CombatEffect.PIE Success, material fallback0,285캡처/100transform observation이다. 캡처 비용 때문에 실제 프레임이 명목30Hz보다 느리므로 짧은 slash 가시성/원작 pixel parity 완료 근거로 사용하지 않는다.

재개 순서는 Art continuity의 남은 ground/direction 보완→후보 고정→현재 수정한 runner의 actual loaded module+전후 Source/Config/Effects/DAS/uproject/native SHA 증거→새 saved8/401 및 Art audit→Root review/새 guarded delivery helper다. 사용자 에디터와 다른 task editor는 제어하지 않는다. 이전 author/old delivery를 재실행하지 않으며 현재 Main 몬스터6의 BrutalHPDamage50 및 별도 MonsterVFX 작업을 보존한다. 생산 transform 수정을 결정하면 해당 증거와 최소 계약 변경을 먼저 기록하고 Source scope를 명시적으로 늘린 뒤 새 build/RHI를 검증한다.


## 2026-10-08 21:10 KST — CombatReaction Work author 완료·PIE 진행

Main runtime/Content는 아직 수정하지 않았다. Work RuntimeBuild02, AuthorBuild03/04 성공이며 현재 task-owned UnrealEditor22364가 nullRHI/noLiveCoding/hidden으로 DevMap을 연 상태다. Saved/MonsterMailbox Ready.pid22364를 확인한다. py mailbox는 Saved/CombatReaction/isolated_mailbox.py, 로그는 Saved/Logs/CombatReactionEditor.log다. 다른 editor를 제어하지 않는다.

첫 ReactionAuthor 성공91saved(24PlayerClone/57Montage/7Def/3ComboGuard), CollisionAuthor 성공36ComboDef(113MonsterBox/1498keys, Player60windows 분류만 수정). receipt는 Metadata/CombatReaction_20261008/Authoring01.json/SourceProbe01.json/CollisionAuthoring01.json에 보존했다. 원본 기존43package BeforeAuthor 백업 및 Main CAS StageBaseline709row를 유지한다. 첫 author의 null recovery array 경고와 HalberdElite Knockback/Launch pool 누락을 발견했고 /root/yetuga_public_patterns가 exactAP2Air/수평adapter/giant NoAirNoBlow fallback 및 일반 DownLoop .3s 임시 hold를 보완 중이다. 재작성 전 현재 native ReactionPIE32반응/15브루탈검사를 실행 중이며 /root/apes_original_patterns가 실패 원인을 읽기 검사한다.

RMS는 HitReaction 실행에 engine JumpForce/IgnoreRootMotion 조건복원으로 연결됐고 .01배율을 이동에 재적용하지 않는다. 임시 이동250/120/150cm는 Header/DataAsset 설정이며 원본값으로 주장하지 않는다. 실제 Static root/childRoot를 확인했으므로 animation/bone repair는 하지 않았다. 현재 native Source에 class1/파일2만 새 runtime이고 temporary author2/test1은 Work에서만 사용한다.

정확 재개: owned22364 test 로그·Saved/CombatReaction runtime 보고서→실패 fixture/runtime 원인 분리→authorplan/helper 보완 후 mailbox quit 정상 종료→필요 Source만 수정/Build05→새 소유 editor에 보완 ReactionAuthor→native ReactionPIE/현재collision·Guard·Heal 회귀와 RHI pose 검증→helper2/test1을 Scripts에 보존하고 Work Source에서 제거·stockBuild.cs 복원/stock build→현재 Main 변경 CAS 검사/선택 전달(기존50/VFX보존)→새 Main 실제모듈·저장재로드 읽기 검증→Engineering/Art 완료append. 현재 author/빌드 성공을 최종 PIE나 Main 완료로 해석하지 않는다.

## 2026-10-08 21:35 KST — Monster6 VFX private build 완료·author API 보완

ARCH-84의 runtime9파일(신규 NotifyState2 포함)·DEV2파일을 private에 구현했고 stock Build Attempt5 exit0/38.812s, private/Main Source·Config·uproject input 불변이다. Main Source/Content/native 전달은 아직 없다. Art 신규457자원/import gap0, 계획857clip/3071source occurrence/2855지원구간/487수정clip/487기술적수명경계다. 조건구간43, 원본 미확인/대체는 MONSTER_VFX_RUNTIME_20261008.md에 구분했다.

readonly probe에서 RuntimeFloatCurve ExportText의 기본0값 생략, Python 비노출 CompositeSections를 exporter로 검사하도록 author를 보완했다. 최종 probe Attempt5 exit0/state_probe_passed/asset_mutations0이다. 첫 apply Attempt1은 첫 asset의 in-memory 검증에서 inherited AnimNotifyEvent.LinkValue Python getter 미노출로 실패했다. 실제 저장 전에 실패한 journal·backup/hash를 확인한 뒤 exporter 기반 getter로 보완해 재실행한다. 실패 report와 log를 보존한다.

재개: PrivateAuthoring.json/mutation_journal 실제 saved 여부→cloth_bone_audit 소유 author/getter 보완→root run_monster_vfx_commandlet으로 author→fresh saved readback→run_monster_vfx_pie actualRHI·35공격/6사망/cleanup→Player CombatEffect 회귀→PNG QA→NativeCandidateIntegrity→attack_metadata 소유 guarded delivery prepare/apply→fresh Main saved/RHI 검증이다. 다른 채팅 Source·Definition·Effects 변경을 CAS로 보존하고 충돌하면 최신본 통합/build/proof를 다시 만든다. 사용자 열어둔 Main/다른 editor 제어·PIE·저장 및 canonical DLL 덮어쓰기는 하지 않는다. 각 verification editor는 task-owned 별도 process다.


## 2026-10-08 — CombatReaction 2차 검증·현재 재개 지점

CombatReaction은 이후 ARCH-85다(동시 MonsterVFX ARCH-84와 구분). Main runtime/Content는 아직 쓰지 않았다. task-owned nullRHI editor22364/32332를 mailbox로 정상 종료하고 throttle을 복구했다. Build05 성공, ReactionAuthor03 성공97unique saves(24Player clone/63unique montage/7Def/3ComboGuard), 계획65montage행은 giant fallback alias2를 포함한다. Swordsman/SwordShield Knockback4는 Loop 시작 HitLand를 추가해 .3s 임시 prone hold 동안 이동하지 않도록 했다.

NativePIE01은694/696 PASS, 02는32reaction/5Brutal pair 완료 뒤 실패2개다. 첫8 case의 .166s 일부 section은 tick 사이를 지나므로 native test에서 같은 실제 instance의 position interval과 직접 관측을 구분하도록 보완했다. Pair5 Heavy back은 약42.65s stage timeout으로 끝났고 원인 미확정이다. global120s 문제라는 가설은 철회한다(실제 global600s). 정상 front/back0~4는50 one hit/both completion/End 이후 Max refill1을 통과했다. 실패 receipt/log는 NativePIE01/02로 보존했다.

최신 Main Player BP8개를 읽기 hash intake해 Work5개만 갱신했다(PlayerBlueprintIntake.json). DevMap은 동일했다. 테스트 cpp는 PairOnly5/실제 몽타주·claim·취소 진단/actual Monster→Player collision3case를 추가했고 screenshot 선택 flag를 준비 중이다. root는 Rider debugger status empty/user exception breakpoint baseline8을 확인하고 Work Brutal EndAbility303에 agent breakpoint1을 생성했다. 아직 debugger attach/paused 증거/제품 원인 수정은 없다. 사용자 breakpoint는 변경하지 않았다.

Monster attack kind의 원본 SD17/27개 참조는 캐시에 실제 SD0이어서 원작 강도 확정 불가다. 기존 supported Box4개만 명시된 어시스턴트 임시 종류로 보완했다: Heavy SwordSwing01 Step4 box2 Knockback, Halberd DownUpperSlash Step2 box2 Launch. 계획109Short/2Knock/2Launch/1498keys, 기존 geometry/time/group/damage/blockable/제외 목록 불변이다. helper는 기존 reaction field reader를 그대로 재사용한다.

재개 순서: test editor source freeze→Build06→새 owned editor의 ReactionCollisionAuthor02→PairOnly5를 debugger attach로 원인 확인→필요 최소 제품 수정/build→전체32reaction/15pair/3collision+Guard/Heal/PlayerCollision 회귀, RHI screenshot→fresh 저장 verifier verify_saved_reactions.py 성공→temporary editor2/test1 archive/remove 및 stockBuild.cs 복원/build→TestedSource/SavedReload/회귀 gate 충족 후 prepare_delivery.py/publish_delivery.py 선택 CAS 전달→새 Main 실제 DLL/저장 readback→완료 MD append. source stock test class와 원본 source245가 변경되지 않았는지 확인한다. 실행 중 별도 MonsterVFX가 shared Source/Def/source animation을 Main에 전달할 경우 baseline mismatch를 보존하고 최신 통합/재빌드/실행 증거가 선행해야 한다. 문서의 다른 작업 완료를 이 기능의 검증으로 재사용하지 않는다.

## 2026-10-08 22:20 KST — CombatReaction Pair3 blocker 확정·현재 재개 지점

Root 소유 Work PID29476의 GameThread LLDB 관측에서 SwordShield 뒤 브루탈 접근 sweep의 `HitObjectHandle.ReferenceObject`가 `AlignmentTarget`인 `BP_Monster_SwordShield1`과 같았다. 최적화된 `Hit.GetActor()` 대신 직접 handle로 확인한 근거는 [DebuggerShieldBack.json](../../Metadata/CombatReaction_20261008/DebuggerShieldBack.json), 상세 계약은 [런타임 정본의 진단 절](COMBAT_REACTION_RUNTIME_20261008.md)이다. 사용자 breakpoint8개는 보존했고 agent breakpoint 제거·detach·소유 process 종료가 Root에 의해 정리됐다. 사용자 editor를 제어하지 않았다.

마지막 저장 검증은 fresh Work PID23920의 `WorkSavedReadback_PrePIE02.json` success=true, 654,552검사/실패0/미지원0이다. verifier SHA `5ba973745034aaeef58026e6f33aa7902cbdecb41d33daedca1d7db441c649b7`는 freeze한다. 전체 native PIE는 아직 완료 전이며 앞선 실패를 성공으로 대체하지 않는다. 현재 작은 제품 보완은 Work Exhaustion h/cpp2개가 짝 capsule의 reciprocal ignore를 자기 추가분만 소유/복구하도록 하는 단계다. 새 runtime 파일은 없고 최종 선택 범위는 HitReaction 신규2+기존14=16파일이다. 이 기록 시점에 새 보완의 build/PIE/Main 전달은 미확인이다.

정확 재개: Exhaustion2 변경 freeze/소스 리뷰 → 이전 membership 보존과 양쪽 실제 task 수명/cleanup을 public capsule API로 검사하는 native fixture → 새 Work build 및 owned RHI에서 pair3와 전체 reaction/pair/collision·기존 회귀 → temporary author/helper 제외 stock build → fresh Work 저장 readback → 최신 Main Source/Config·사용자/다른 task 공유 asset CAS 확인·16 runtime 선택 전달 → 새 독립 Main의 actual selected DLL/hash/native schema·같은 saved verifier → 실제 결과에 맞춰 완료 append. 이전 author 전체 재실행이나 수치/원본 raw track 재작성은 필요하지 않다. 저장 pass만으로 runtime 수명·전체 PIE·Main 완료를 선언하지 않는다.

## 2026-10-08 22:31 KST — Monster6 VFX 실제 RHI 실패 지점과 재개

private Build10 및 fresh SavedReadback3은 통과했다(487 Sequence, 3342 state, 6 death presentation, 모든 NotifyStateBehaviorFlags 0, selected bytes 불변). PrivateMonsterRuntimePIE/Attempt2는 실제35 human Ability와37 representative clip, paired2 및 ordinary death6을 끝까지 실행했지만 native assertion 6건과 light material usage fallback으로 실패했다. 종료 PID21756/exit0은 테스트 성공을 의미하지 않는다. Main Source/Content/native는 아직 전달하지 않았다.

실패는 representative material consumer2, Apes paired lethal consumer2, Apes death execution consumer2다. TerminalDeath Execution raw800은 기록됐지만 Consumers0이다. source material binding을 실제 BP slot과 비교해 보완 중이며 assertion을 완화하지 않는다. light-only M_MonsterLightOnly에 ParticleSprites usage가 빠진 RHI 문제는 별도 task-owned commandlet으로 수정 중이다. 기존 457 manifest/audit를 갱신하되 47 adapter identity map과 ExecutionRadiusRevision 원본 proof는 보존하고 LightUsageRevision 체인으로 연결한다.

정확한 다음 절차: material consumer 원인 수정 → private build → light usage revision 성공 확인 → 별도 PrivateMonster RHI 재검사(이미지 전체 상한2400으로 올려 Apes/Yetuga/Execution/Frozen도 캡처) → player regression → root 실제 PNG 검토/VisualQA → NativeCandidateIntegrity → guarded MainDelivery → fresh Main saved/RHI. 기존 실패 Attempt2는 보존한다. 다른 task editor PID8952와 사용자 editor는 조작하지 않는다. 상세 source/원작 수치 계약은 MONSTER_VFX_RUNTIME_20261008.md 최신 절을 따른다.

## 2026-10-10 — ARCH-85 CombatReaction 중단 지점 확인·재개

정확한 중단 지점은 Work의 최종 native 피격·브루탈 검사 통과 후, 기존 몬스터 행동 정책 회귀를 조사하던 단계다. [NativePIE_Final.json](../../Metadata/CombatReaction_20261008/NativePIE_Final.json)은 task-owned PID8952에서 실제 RHI로 일반 피격32case·브루탈15case·Monster→Player 충돌3case를 모두 완료했다. 기존 Guard·Heal·PlayerAttackCollision 회귀도 통과했다. 다만 `Khazan.Monster.CombatPolicyPIE`는 Heavy의 stage4/5 timeout으로 실패하여 원인 조사가 남아 있다. 따라서 전체 회귀·stock build·Main 전달 완료로 기록하지 않는다.

중단 후 남아 있던 소유 editor8952는 2026-10-10 08:34 UTC에 GPU device removed로 종료됐다. 이 오류는 앞서 기록된 행동 정책 실패 이후에 발생한 것이므로 해당 timeout의 원인으로 확정하거나 실패를 무효화하지 않는다. 당시 로그는 [InterruptedEditorLog_20261010.log](../../Metadata/CombatReaction_20261008/InterruptedEditorLog_20261010.log)로 보존했다. Root가 별도 소유 hidden/nullRHI editor23912를 새로 실행해 정책 회귀를 조사한다. 재개 시 PID는 해당 프로젝트의 Ready와 실제 process identity를 다시 확인하고, 사용자/다른 task editor를 제어하지 않는다.

읽기 재개 감사 [ResumeDriftAudit_20261010.json](../../Metadata/CombatReaction_20261008/ResumeDriftAudit_20261010.json)은 Main baseline709행·기존 author 대상43개·표적 dependency268개 모두 drift0, Work native 당시 Source/Config106개 모두 SHA 동일을 확인했다. runtime16개와 native fixture `be418e7ed8386c1be2f8fca4bf7f595238a8815658cc699bd79bc7bb1f42964b`도 동일하다. Work 선택 DLL SHA `7b84183296ba741ad03fac5520b127fe6ed0e8bfd4502608ef8a4fefdc191dde`는 최종 native snapshot과 같다. Main은 현재 canonical `UnrealEditor-Khazan.dll`, SHA `de899bc2f831f8fe009aaaff1b86fb4f7bbe68451ed75dd0388d74b3b4840597`이며 이번 runtime16개·asset130개는 아직 Main 미전달이다. 이 disk 감사는 새 프로세스의 실제 loaded module 검증을 대체하지 않는다.

정확한 재개 순서: (1) 새 소유 editor에서 CombatPolicy Heavy 실패를 debugger/실제 상태로 확인한다. (2) 증거가 확인한 최소 runtime 수정 또는 fixture 오류만 보완하고 필요한 build와 영향 회귀를 다시 통과시킨다. (3) 전체 회귀 성공을 전달 gate로 확정한다. (4) 이미 [PrivateTestSources/Hashes.json](../../Metadata/CombatReaction_20261008/PrivateTestSources/Hashes.json)에 현재 SHA 검증하여 보존한 임시 author2/test1 세 파일만 Work Source에서 제거하고 stock Build.cs를 최신 Main 원본으로 복원한다. (5) stock build→새 Work saved readback을 수행한다. (6) 최신 Main CAS를 다시 확인하고 runtime16+asset130=146파일만 prepare/publish한다. (7) 자기 fresh Main 프로세스의 실제 선택 모듈·저장값·dirty0 readback과 정상 종료를 확인한 뒤 Engineering/Art 완료를 각각 append한다.

기존 author/원작 추출/retime/에셋 전체 작성은 반복하지 않는다. stock 복원 전 author/test가 포함된 DLL이나 이전 회귀 실패를 최종 제품 성공으로 해석하지 않는다. 새 Main 변경이 발생하면 사용자 변경을 보존하고 필요한 범위만 재병합·빌드·검증한다. 현재 새 구조를 더 추가하기로 결정한 내용은 없다.

## 2026-10-10 19:48 KST — Monster6 정확 재개: 표적 Apes 수정 및 Build11 통과

Main/private Source·Config·uproject는 이전 Build10 입력과 동일했고 실행 중 editor0이었다. 이전 RHI2/Probe 실패 report는 그대로 보존했다. Apes binding revision probe2→apply가 통과했고 State5/Sequence2만 저장했다. PreparedPlaybackPlan과 PrivateAuthoring의 현재 revision을 갱신하되 original Main-before journal499·나머지497파일·schema58d...·원본 curve/time은 보존했다. 기존 slot MID에 current baseline uniforms를 복사하는 소수 줄과 DEV 실제 winter 조건 fixture를 추가했고 private Build11 exit0/37.578s 및 입력 불변을 확인했다. Source 범위11파일은 유지된다.

현재 root-owned fresh saved audit가 진행 중이다. 정확 다음은 SavedReadback4 status 통과→PrivateMonsterRHI3(2400cap/actual loaded-module evidence)→PrivatePlayer regression→root 실제 PNG QA/VisualQA→NativeCandidateIntegrity→guarded delivery prepare/apply→새 Main saved·Monster/PlayerRHI→Main PNG QA→finalize_monster_vfx_main_verification_20261008.py 및 완료 문서다. 487전체author/import/retime를 재실행하지 않는다. Main 제품은 아직 미반영이다.


## 2026-10-10 19:51 KST ? Player VFX polish ?? ?? ??

???? ?? ?? ?? ???? Router?Architecture/ Migration??? Player VFX/runtime ? continuity? ????. ?? private? Main intake ?? Source96?Config5?Effects5874?DAS161?native105 ??0?? ?? CombatReaction/MonsterVFX Work? ???? ???. ?? Source3/BuildFinal01? ??? ????. Agent ??2?? ? ?? Spear author? receipt ??? ???? ???? ?? parent baseline bytes? ??? ? hidden Cmd PID28068/token976250df018a4b568045cf03dc53f58c? ? parent? ????. positive SM6/exit0?? ?? ??? ??? ?? ??? ?? ??? ?? ???.

?? `Processes/ResumePrivate01`? task-owned ?? RHI? 13 Art ??? Source3? 18??/5Brutal ?? ? ?? ??? ?? ???. Main ?? ??0. `FrozenCandidateManifest.json`? ??10 snapshot? Resume_20261010? ??? ? Recovery2/Spear1? ???13 ??? ????? visual pending? ????. ??? ResumePrivate01 receipt/Brutal ?? ???Spear curve/UV/?? dynamic source contract ?? ?????? ? parent? ????13 saved RHI ??/18+5/firstpose13?root visual evidence ???guarded helper prepare/apply?fresh Main RHI/saved?finalize ???. ?? 8???/401??/??? BrutalHP50 ? ?? ??? ????. ?? failed captures? saved0 author ??? ???? ???.

## 2026-10-10 20:09 KST — MonsterVFX RHI3의 정확한 실패 및 후속 검증

Private Build12와 새 SavedReadback4는 통과했다. 실제 RHI3은 공격35개, 대표 clip37개, 실제 Apes paired2개, HP0 사망6개를 재생하고 PNG1551개를 남겼지만 native/Driver는 failed다. 재질 compile fallback은 0이다. 실패20건은 paired 완료 후 두 번 검사한 5slot의 FinalBlow replacement parent/Execution 기대값에 한정된다. ordinary Apes Death는 실제 consumer5와 원작 raw Execution=800 유지가 두 번 관측됐다. 실패 report를 성공으로 바꾸지 않는다.

실제 저장 AM_BrutalVictimFront는 Damage_Grapple_Atk_01/02, Back은 Damage_Grapple_Atk_B_01/02를 재생한다. 원본 ZIP과 현재 plan의 각 Grapple는 particle4개이고 execution material 이벤트는 없다. 별개 library Damage_FinalBlow를 paired consumer로 가정한 DEV fixture가 잘못됐다. 제품 Grapple에 원작 근거 없는 dissolve 이벤트를 추가하지 않고 실제 baseline 재질 유지·피해·paired 완료·최종 pose/cleanup을 검증하도록 DEV만 보완한다. ordinary Death 및 standalone FinalBlow의 기존 원본 material 검증은 유지한다. 현행 paired terminal material transfer는 실제 producer가 없는 경로이며 이 두 pair로 양성 검증했다고 설명하지 않는다.

Halberd Damage_Disease의 Rim은 원본 WeaponV2 skeleton의 weapon_r track 대상이다. 기존 representative37에는 해당 clip이 없으므로 이전 자료만으로 Rim 화면 pass를 주장하지 않는다. 별도 own real-RHI QA가 실제 BP의 동일 skeleton 컴포넌트 존재·overlay fade·복구와 PNG를 표적 확인한다. body에 잘못 강제 재생하지 않는다. Main 제품은 아직 미전달이다.

정확 재개: source identity probe pass 확인→DEV paired 기대 보완→stock private build→최신 Monster/Player RHI와 필요한 Rim owner QA→root PNG 확인→current SHA integrity→guarded Main 전달→fresh Main saved/RHI/PNG→final report. 전체 author/추출/retime는 반복하지 않는다. 다른 task Main 변경은 CAS로 보존한다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — ARCH-85 정확 재개 작업 완료·재실행 금지 범위

중단 지점은 전용 native RHI 통과 후 Heavy CombatPolicy timeout 조사였다. 새 owned PID23912에서 debugger 실제 상태를 확인했으며 debug/undebugged 두 정책 실행은 인간4종까지 Success였다. 이후 stock Guard/Heal/PlayerAttackCollision/CombatPolicy4종 모두 통과했다. 원래 실패 원인은 미확인이고 제품 AI 변경은 없었다. 이전 실패/GPU crash/debugger 증거는 보존했다. 사용자 breakpoint8개는 유지하고 agent breakpoint3개 제거/detach·owned23912 정상 종료했다.

archive SHA 확인→임시 helper3 정확 제거→Build.cs exact Main 복원→stock build Succeeded→TestedSource103→fresh Work29152 저장 검사 성공/종료→Main baseline709/공유 asset CAS→runtime16+asset130=146 선택 전달→fresh Main16544 actual stock alias+654,552검사 성공/dirty0/종료→FinalVerification 성공까지 완료했다. 사용자/다른 작업 editor는 제어하지 않았다. 현재 [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)의 MainDeliveredAndFreshVerified를 읽는다. 기존 pending/PreparedDelivery는 과거 단계의 receipt이며 전체 author/import/retime/prepare/publish를 다시 실행하지 않는다.

후속 작업은 Router→Architecture ARCH-85 최신 완료→Migration→runtime 정본/UserGuide→최신 실제 Main Source/Definition 순으로 시작한다. 조정 가능한 pool/거리·높이/BrutalAlignmentSeconds/BrutalHPDamage/공격 window 수치는 기존 데이터에서 변경한다. 이후 다른 chat가 shared Source/Definition이나 모듈을 전달한 경우 이 alias로 임의 되돌리지 말고 새 current module/source SHA를 확인한다. 남은 미검증은 원작 full contact/pixel fidelity·멀티플레이·실제 패링 producer·별도 Player 사망, Heavy matching Air 및 제외 shape의 원본 geometry 확보다. 이는 이번 승인 범위의 미완료 전달이 아니다.

## 2026-10-10 20:19 KST — MonsterVFX RHI4 기능 assertion 통과·기존 Player 시작 로그 분리

PrivateMonsterRuntimePIE/Attempt4는 native 기능 assertion 오류0, paired 실제 Grapple source2/각 visual4/execution0, baseline5 유지와 ordinary Apes death raw800/consumer5를 모두 확인했다. 그러나 native/Driver는 failed이며 유일한 자동 검사 오류는 기존 saved DA_CharacterDefinition_Player의 빈 InitialAbilityGrant가 내는 정확한 BP_Player_C_0 시작 LogDefaultError1회다. 이 실패와 기존 VAT TextureCube→Texture2D linker warnings는 보고서를 보존하고 숨기지 않는다.

DEV 두 RunTest만 실제 saved PlayerDefinition의 null AbilityClass/InputTag Empty 행수를 읽어 해당 완전한 오류 문장만 exact count/IsRegex=false로 등록했다. InputTag가 있는 잘못된 null 행은 여전히 실패하고 다른 오류도 허용하지 않는다. 게임 로그 severity·Definition 에셋·Ability 부여 동작은 수정하지 않았다. 이 DEV 보완 후 Build14와 full native RHI5/Player 회귀가 필요하다.

Rim3는 runtime/fade/restore/actualRGB(2,0,0,0)/fallback0/save0 통과지만 QA 조명5000cd로 영상이 포화되어 visual pass는 보류했다. QA만 fill을 끄고 actualweapon closeup을 다시 확인한다. Yetuga 일부 actorbounds 영상은 transientPSC의 큰 bounds로 camera가 멀어져 시각 검증에 부적합했다. QA driver만 실제 bodymesh bounds로 수정했고 original Source/pose/FX/scale을 바꾸지 않았다. Yetuga 공격2+NI 원본이 실제 있는 Recovery1의 별도 own-PIE 시각 QA도 준비했다.

정확한 남은 순서: Build14→full PrivateMonster RHI5→PrivatePlayer RHI→동일 최종DLL의 Rim/Yetuga targeted RHI→root actualPNG VisualQA→추가 두 proof를 포함한 NativeCandidateIntegrity→current Main CAS/guarded prepare/apply→fresh Main saved/Monster/Player 및 Rim/Yetuga RHI→Main PNG/finalize/도메인 완료 기록. author487·resource457·alias revision은 재실행하지 않는다. Main은 미전달이다.


## 2026-10-10 20:37 KST — Player 공격 VFX 정확 재개·최신 코드 통합·녹색 데칼 보완

이전 10/10 작성 중 한국어가 물음표로 손실된 기록은 보존하고, 이 UTF-8 절을 최신 조회점으로 사용한다. Main CombatReaction 전달을 보존하여 Source16/DAS42만 AttackVFXWork에 정확 intake했다. Main Source98/Config5/DAS203/Effects5874가 baseline이며 기존 8개 VFX 몽타주·401구간 byte는 동일하다. PrivateReady SHA는 `871aa3e2ab67ce7d9c41bd27baa561222ac6a312b65e6d44dadf1aeea98023a1`; 이전 Ready/Frozen은 CombatReactionRebase/Prepared_20261010T112008612951Z/History에 보존했다. 본 작업의 Main 제품 전달은 아직 0이다.

Private Source 변경은 기존 ActionAbility h/cpp와 개발 CombatEffectPIETest cpp 3개뿐이다. 비부착 world-owner9 보정과 부착13의 최초 bone-finalized callback/해제 계약은 ARCH-83 기존 표현 수명에 남는다. Debug PID28888의 실제 브루탈 `KZFX_ea52bee547d07b167dccc25d`에서 올바른 MID/부모/DeferredDecal/Unlit 및 SM6 master resource의 game/render complete=false, compile ID182, submission None를 읽었다. 엔진 Renderer PDB가 없어 해당 fallback 함수 자체는 직접 step하지 못했다. `GreenDecalRuntimeDebugger.json`에 보존했다. 기존 사용자 breakpoint8개는 유지하고 agent3개를 제거/디버거 종료했다. 진단 실행은 정지 때문에 테스트 deadline으로 실패했으므로 완료 증거로 쓰지 않는다.

기존 데칼 생성 직전에 `#if WITH_EDITOR`의 엔진 `EnsureIsComplete()` 호출만 추가했다. 원작 재질 색·도메인·크기·수명/재생 시각 및 cooked 빌드 경로는 보존했다. BuildResumeFinal02 exit0, ResumeSavedPrivate03 exit0/Art13/8몽타주/401구간/8,308field pass, ResumePrivateFinal03 exit0/native18+Brutal5 Success/material compile failures0/제품 SHA 보존을 확인했다. 최초 부착 포즈13은 FirstPoseResumePrivateFinal03.json에서 모두 확인되고 최대 각도 잔차는 약0.00000171도다. Root가 실제 Final03 Front147/Back156 PNG에서 녹색 투영 면 소실과 붉은 혈흔을 확인했다. 기존 null AbilityGrant 오류는 최신 intake 실행에서 발생하지 않아 Saved DEV 제안은 적용하지 않았다.

아직 전달 전이다. 실제 Front146(2.513초)에 남은 큰 반투명 각진 면의 Art producer를 표적 재검사한다. 정확 재개는 Art 최신 continuity/새 후보 확인 → 필요 parent1만 보완 → 최종 SHA 재동결 → 새 실제 RHI·저장 감사·Root PNG 검토 → 15개 proof 결속 및 guarded prepare/apply → fresh Main RHI·저장·PNG → finalize와 완료 기록이다. 전체 원본 추출·401구간 author·retime·과거 delivery를 반복하지 않는다. 다른 작업의 Main 변경은 CAS로 보존하고 사용자 에디터를 제어하지 않는다.


<!-- MonsterVFX_GuardedRebase_Checkpoint_20261010_2045 -->
## 2026-10-10 20:45 KST — MonsterVFX 최신 Main 병합·Definition 표적 복원 및 시각 검증 대기

별도 ARCH-85 CombatReaction의 Main146 완료를 보존하여 guarded Source intake를 수행했다. 최신 Main Source98/private Source101이며 원래 Source96 baseline을 덮어쓰지 않았다. [MainRebaseIntake](../../Saved/ImportReports/MonsterVFX_20261008/MainRebase/MainRebaseIntake.json)는 Main Source 쓰기0/private Source16 병합·백업·CAS를 기록한다. Build15는119.359초/exit0, Main/private 입력 불변이며 실제 private DLL SHA는 `5c6b3e40a2226e1aa044bb3eaf96fc0bb7fc08082f22a0ec19f7a79075dfabe2`다. MonsterVFX의 Main 전달은 아직 하지 않았다.

Reaction130 asset은 private 물리86개만 복사하고 Main read-only junction44개는 현재 SHA 확인만 했다. 여섯 CharacterDefinition에는 새 Reaction 설정을 유지한 채 기존 authored DeathPresentationMontage만 typed 복원했다. probe PID5680/19.031초와 apply PID30712/30.703초가 통과했고 [ContentRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/ContentRebaseRevision.json)은6 package saves/6 field mutations/Main mutation0, 전체 T3D의 다른 Definition field 보존·나머지493 author 파일 SHA 불변을 증명한다. original PrivateAuthoring499/Main-before journal·PreparedPlaybackPlan·Apes Applied·schema는 그대로다. saved/delivery는 이 별도 report의 정확한6행 before/merged-after override만 소비해야 하며 원래 journal을 새 baseline으로 다시 쓰지 않는다.

PrivateMonsterRuntimePIE Attempt5는1552 PNG/fallback0/523.187초로 통과했지만 Build14의 이전 DLL 결과이므로 최종 병합 Build15의 전달 증거로 대체하지 않는다. 최신 SavedAudit6는 새6행 override를 포함한 결과를 확인하는 단계다. [PrivateRimQA Attempt6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt6/Driver.json)는 Build15 실제 모듈에서 compatible EnemyWeapon_R의 원래 RGB·weight 감쇠·baseline 및 transient diagnostic 복구, package0/fallback0을 확인했으나 화면의 Rim 가시성은 아직 확정하지 못했다. Yetuga의 흰색 화면과 snow writer 표시를 구분하는 표적 시각 RCA도 남아 있어 visual pass/기능 전체 완료로 기록하지 않는다.

정확 재개는 최신 SavedAudit6/loaded-DLL·6행 override 확인 → Rim6 실제 PNG와 Yetuga snow writer/시각 producer의 원인 분리·필요한 최소 보완 → 최종 DLL의 Monster full native 및 Player 회귀·표적 Rim/Yetuga RHI와 Root PNG 검토 → 원래 author/plan/Art457 및 Source intake·ContentRebaseRevision을 결속한 integrity → 최신 Main Source/Content/module CAS 재확인·guarded 선택 전달 → fresh Main saved/Monster/Player/표적 시각 검증이다. 실패·이전 후보와 baseline/backup을 보존하고 전체487 author·457 import·원본 추출/retime·Apes alias apply를 반복하지 않는다. 원작 Grapple의 material0을 바꾸거나 producer가 없는 paired Execution retention을 검증 완료로 승격하지 않는다.

## 2026-10-10 20:58 KST — 공격 VFX 재개, Final04 통과와 혈흔 ribbon 시각 보류

이 작업은 중단된 Player 공격 VFX polish의 재개다. MonsterWork의 첨부 파일을 별도 Brutal gameplay 수정 요청으로 해석하지 않았다. 현재 Main 게임 파일 반영은 0이며 Rider/user 에디터 및 다른 작업 에디터를 제어하지 않았다.

PrivateReady SHA `871aa3e2ab67ce7d9c41bd27baa561222ac6a312b65e6d44dadf1aeea98023a1`, Source98/Config5/Effects5874/DAS203 baseline이다. Main CombatReaction 변경 58개를 Private에 정확히 intake한 상태이며 이를 되돌리지 않는다. Source3의 최신 BuildResumeFinal02 exit0 및 DLL `97aa1de8219bb57287bcf99be35912df53ce4b1ef9f2d6f3b17b51e1422d7fd5`를 사용한다. 에디터 최초 혈흔의 shader fallback은 실제 LLDB 상태로 미완료 shader map을 확인했고, WITH_EDITOR에서 기존 EnsureIsComplete API를 사용한 최소 수정으로 Final03/04에서 초록색 오류가 사라졌다. cooked 경로의 호출은 없다.

ResumePrivateFinal04 PID26444 exit0/229.742407초: native 18개 및 Brutal 5개 통과, PNG113장, package saves0, material_compile_failures[], RuntimeIntegrity passed. ResumeSavedPrivate04 PID27444 exit0/33.763501초: Art13 및 변경하지 않은 PD3 resource readback, 몽타주8/구간401/field8308 passed, 저장0. FirstPoseResumePrivateFinal04.json은 attached13/13, rotation residual0도다. 이 수학적 검증은 전체401구간의 pixel parity 검증이 아니다.

Root는 PNG104 Front2.531553초에서 기존 회색 sky plane 소실을 확인했지만 큰 붉은 경사 ribbon 모서리가 드러나므로 최종 visual pass 및 Main delivery를 보류했다. event KZFX_b3be5ec1f2c206deb8400356(원본 Grapple_Atk_02 Notifies[19], 2.179462–2.835103초) → PP_Dmg_Blood_Trail → FMI_blood_trail_red → FM_blood_trail이 유력하다. 추가 Private parent FM_blood_trail 한 개의 source/UV/gradient/dissolve 표적 진단과 최소 복구만 허용했다. 원작 shader graph는 stripped이므로 adapter를 원작 shader 직접 복원으로 표현하지 않는다. 원본 damage50/notify timing/8montage401/PS lifetime은 유지한다.

재개 절차: Art continuity의 Spear early 검증과 새 ribbon 후보를 확인 → 필요하면 Art14 Frozen에 source provenance/before/after SHA를 추가 → 변경 이후 새 Final05 actual/saved readback 및 Root PNG 확인 → 현재 Main drift를 다시 검토하고 필요한 exact intake/build → evidence15 binding → closed Main census/CAS prepare/apply → 새 Main actual/saved → finalize 및 날짜별 완료 문서. Main user PID9460 및 다른 작업 probe PID9316이 열린 것으로 관측돼 현재 closed-census gate도 미해결이다. 사용자 작업을 저장하거나 닫거나 외부 프로세스를 종료하지 않는다. Final04Pending binder는 보존하되 이후 후보의 최종 증거로 재사용하지 않는다.


<!-- MonsterVFX_VictimRimBuild18_Checkpoint_20261010 -->
## 2026-10-10 21:17 KST — MonsterVFX Decal 정책 표적 적용·Rim 컴파일 완료 근거·Main 전달 전

이 절은 20:45 MonsterVFX checkpoint 이후의 실제 결과다. 별도 CombatReaction과 PlayerVFX 작업의 Main 변경은 보존했다. MonsterVFX Main 전달은 0이며, Root가 관측한 사용자 Main PID9460은 열린 상태다. 사용자 에디터의 저장·PIE·종료를 수행하지 않았다.

[VictimDecalPolicyRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VictimDecalPolicyRevision.json)은 probe PID29200와 apply PID30084가 통과했다. 최종 SHA는 `9b3609b797c23f64cf66169515f1d456d9783b4ad522c39fab7e2231fe7516ec`다. Damage26/Death17의 정확한 Decal43개에서 Effect의 `bOnAttackSuccessed=true→false`만 바꾸고 Sequence26개를 저장했다(Main mutation0). 전체 before/after/saved T3D의 단일 bool 차이, 다른 Effect/State field·Notify 시간/GUID·raw pose/curve/settings 보존과 나머지 author473개 SHA 불변을 검증했다. 원본43개 export Properties에는 해당 field가 모두 없지만 원작 CDO 기본값은 미확인이다. 이전 Blood 이름 기반 success guard는 원작 확인값이 아닌 프로젝트 추론이었으며, 이번 명시적 프로젝트 정책은 피해자 Damage/Death animation이 원래 Decal 창의 표현 수명을 소유하도록 이를 대체한다. 가짜 적중·새 피해 상태/타이머/producer를 추가하지 않았다. original author499/Main-before journal·PreparedPlaybackPlan·Apes Applied·ContentRebaseRevision은 수정하지 않고 별도 revision override만 소비한다.

새 [SavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)은 PID6036, Sequence487/State3342/Death6 및 victim revision43/26 marker를 통과했다(SHA `b6c3c8fda3dae75879bcd7d1b91743fe9e8445bc0cd2e9818ccb7b7e1b49d890`, 저장0·선택 byte 불변). 해당 saved 프로세스 종료 후 Build17의 DLL 파일 잠금 LNK1104를 해소했다. Build17 exit6/108.515초는 보존하고 성공 증거로 사용하지 않는다. 최신 [Build18](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt18/Exit.json)은 PID22032/5.234초/exit0, Main/private inputs 불변이다. 현재 DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`다.

[Rim8 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/Driver.json)는 실제 DLL16 `11dd0c914b84132f2785e274d70738f631b38d6de5b9e31040f4a08752e58805`로 capture63/package0/asset mutation0/material compile failures[]를 통과했다. Root는 [PNG24](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/024_Halberd_Rim_Diagnostic_StatisticsSynced_SourceOverlay_WeaponFrontOblique.png)의 실제 EnemyWeapon_R 붉은 Rim을 확인했다. 같은 source RGB/weight에서 GetStatistics의 compilation 완료 후, 명시적 RecompileMaterial 전에 이미 붉은 윤곽이 나타났고 이후 원래 exposure의 PNG27에서도 나타났다. 이는 Editor 최초 shader readiness 원인이라는 추론을 지지하며 실제 breakpoint로 그 resource 상태를 읽은 증거는 아니다. 원작 색/강도·shader asset·exposure를 제품 설정으로 바꾸지 않았다. Root는 private `KZMonster::AcquireBinding`의 기존 첫 MID 생성 직전에 WITH_EDITOR `Replacement->EnsureIsComplete()`만 추가했다. Build18의 regular Rim9는 GetStatistics/RecompileMaterial 없이 실행 중이며, 첫 화면 가시성은 아직 판정 전이다.

[Yetuga2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/Driver.json)는 failed/capture38/save0이다. Root는 actual writer component의 main/depth/shadow=false와 [PNG10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/0010_Yetuga_Attack_NormalAtk01_03_Playing_011_FrontOblique.png)의 dome 소실을 확인했다. 종료 뒤 Breath2/BodyDust1 active 관측으로 cleanup 검사가 실패했으며 전체 통과가 아니다. 1초 QA 관측 간격이 raw finite Breath 최대3.5초와 충돌한다는 표적 RCA가 진행 중이고 BodyDust의 실제 lifetime/sentinel 근거를 확인한 뒤 QA 관측 여유만 수정한다. gameplay 수명 predicate를 임의 변경하지 않는다.

정확 재개: Build18의 current loaded-DLL과 saved/revision43/26 marker 결속 → regular Rim9 최초 화면 및 Root PNG 검토 → Yetuga lifetime 근거·QA 관측 여유 보완과 새 actual RHI cleanup/PNG → 같은 최종 DLL의 full Monster native와 Player 회귀 → original plan/author499/Art457·Main source intake·ContentRebase6·Victim26 및 모든 fresh runtime/supplemental SHA를 묶은 NativeCandidateIntegrity → closed Main census/current Source·Content·module CAS 및 guarded 선택 전달 → fresh Main saved/Monster·Player/regular Rim·Yetuga 실제 RHI·Root visual/finalize. 전체 author487·import457·원본 추출/retime·Apes alias apply를 반복하지 않는다. 현 checkpoint는 최종 구현/화면 품질/Main 반영 완료를 주장하지 않는다.


<!-- MonsterVFX_RegularRim9_Positive_20261010 -->
## 2026-10-10 21:18 KST — Build18 일반 Rim 최초 표시 실제 통과·전체 검증 진행 중

앞선 checkpoint 직후 [PrivateRimQA Attempt9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Driver.json)가 passed로 종료했다. actual loaded DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`, diagnostic_mode=false, PNG30/package saves0/asset mutations0/material compile failures[]이며 [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Exit.json)는62.594초/exit0이다. Driver SHA는 `cd5af174d284ec6e6696a31c313f4b8f5e673eaf43c816e13e7e344169365a0f`다. Root는 [Active03 Front PNG006](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/006_Halberd_Rim_Active_03_WeaponFrontOblique.png)와 [Active06 Front PNG009](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/009_Halberd_Rim_Active_06_WeaponFrontOblique.png)를 직접 보고 첫 표시의 강한 붉은 Rim을 확인했다. 별도 GetStatistics/RecompileMaterial/노출 변경 없이 기존 editor shader 준비 보완이 실제 첫 화면에서 작동했다. 원작 RGB/weight/시간·저장 shader asset을 변경한 결과가 아니다.

이 결과로 regular Rim의 최초 표시·fade/복원 검증은 통과했지만 MonsterVFX 전체/Main 전달 완료는 아니다. Root가 같은 Build18의 PrivateMonster full RHI6을 시작했고 Player 회귀 및 원본 lifetime에 맞춘 Yetuga cleanup/시각 재검증이 뒤따른다. 최종 candidate SHA 결속·closed Main CAS/guarded 전달·fresh Main saved/실제 RHI/Root visual/finalizer까지 앞 절의 재개 순서를 유지한다. Source/Art 후보는 Build18 이후 동일하고 이번 보충은 문서만 추가했다.


<!-- MonsterVFX_CurrentQAExternalB_Checkpoint_20261010 -->
## 2026-10-10 21:39 KST — MonsterVFX 표적 QA 통과·Input B 저장 후 전체 재검증 진행

[DeliveryReadiness](../../Saved/ImportReports/MonsterVFX_20261008/DeliveryReadiness.json)은 complete=false이며 Main/Work Source·Config·uproject와 Build18/current DLL1506의 일치, private SavedReadback의487 Sequence/3342 State/Death6 및 Victim43/26 marker를 확인했다. MonsterVFX Main 전달은0이다. 최신 Main 프로세스 관측은 외부 작업의 Null 검증 PID16396이며 다른 채팅 소유라 제어하지 않는다. 과거 사용자 에디터 open 관측을 현행 상태로 가정하지 않는다.

[Native6 Interruption](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt6/Interruption.json)은 InterruptedKnownFailedCandidate다. owned PID23356은387.719초 뒤 중단됐고 [log](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt6/PrivatePIE.log)의 Input.Action.B 미연결 Error 때문에 성공으로 사용하지 않는다. 외부 Authoring07/08은 nav 검증 실패·saved0이었으나 최신 [Authoring09](../../Metadata/BrutalInputDevMap_20261010/Authoring09.json)은 IMC/InputData/PlayerDefinition/IA_BrutalAttack/DevMap의5 unique asset 저장에 성공했다. Main 및 private 공유 경로의 실제 afterSHA가 모두 일치한다. Root는 이 baseline을 소비하는 fresh Native7을 session72778로 재시작했으며 결과는 아직 미확정이다.

현재 [Yetuga3](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt3/Driver.json)은82.578초/104PNG/actual DLL1506/package0으로 통과했고 regular Rim9도 actual DLL1506에서 통과했다. 이 표적 검증은 전체 Monster·Player 회귀/Main 검증을 대체하지 않는다. 원작 lifetime 기반 QA 관측 여유의 상세 출처는 Art 정본과 TailLifetimeEvidence에 둔다.

정확 재개: native source/artifact·proof schema 표적 RCA → 현재 baseline의 Native7 실제 종료/입력 Error0 확인 → fresh Player real-RHI 회귀 → Root 전체 PNG 검토/VisualQA와 Victim revision SHA 결속 → candidate integrity → 최신 Main Source·Content·module CAS/process census와 선택 전달 → fresh Main saved/Monster·Player/Rim·Yetuga/loaded alias/PNG/finalize. candidate가 FinalResourceAudit의 없는 status를 읽는 불일치는 아직 수정 전이다. Error masking·Controller 변경으로 우회하지 않으며 전체 추출/import487 재실행도 하지 않는다.

범위 표기 보충: 위 재개 절차의 import 대상은 Art457개, author 대상은 Sequence487개다. 두 전체 작업 모두 반복하지 않고 남은 검증과 전달만 진행한다.


<!-- PlayerAttackVFXPolish_Final07_BFixture_20261010 -->
## 2026-10-10 21:43 KST — 공격 VFX 최종 후보 고정·현재 B 입력 회귀 검증 재개

이번 작업의 중단 지점은 Player 공격 VFX polish의 Main 선택 전달 전이다. Art14개와 기존 KZActionAbility 두 파일의 표현 수정은 private에서 고정했고 Main 게임 파일 수정은 아직0이다. 현재 PrivateReady SHA는 `6aae46e88cbda08d60368f613ff92937634c4b3b45cf40dd75fbdc5227389509`, Frozen SHA는 `edb6961e6c3b6d7e80a1bc7d7835be39eb54656f3466fd6efbc1a54396efe8ae`다. 별도 CombatReaction 및 B 입력/DevMap 작업의 저장 결과를 보존했다.

[Final05](../../Processes/ResumePrivateFinal05/Driver.json)는 실제 VFX 근접 화면에서 Root가 빨간 불투명 판·회색 창 면·초록 데칼이 사라지고 피 입자와 가는 혈흔 리본이 유지됨을 확인했지만, 당시 B 입력 에셋 미저장 오류로 전체 자동화 통과가 아니었다. 별도 작업의 Authoring09가5 unique 입력/맵 에셋을 저장한 뒤 [Final06](../../Processes/ResumePrivateFinal06/Driver.json)을 다시 실행했다. Final06은 material compile error0·RuntimeIntegrity 통과 및 [Saved06](../../Processes/ResumeSavedPrivate06/SavedArtAudit.json)의 Art14/원본8 Montage·401 창·8308 필드 통과에도 불구하고, DEV test가 예전 X grant/dispatch를 단언해 실패했다. 두 실패를 성공 자료로 재사용하지 않는다.

Root는 private `KZCombatEffectPIETest.cpp`의337/338/340/383 네 줄만 현재 실제 B grant/ASC Press·Release와 문구로 변경했다. 실제 실행·front/back pairing·HP0 transient 음성/현재 HP50 양성·cancel cleanup 및18+5 공격 검사는 그대로다. 직접 Ability 활성화나 오류 숨김은 없다. 새 test SHA는 `daf20550902f229b1ca252b56eba6dc06cb5a67d23ec5cc33c1c2562efebef78`다. [BuildResumeFinal04](../BuildResumeFinal04/Exit.json)는 exit0·41.078초·104개 입력 불변이며 DLL SHA는 `d1957a4bd437fa5f717f99ad41122c8336707ecdc4a45819df2bd0a3c9d09361`이다. 실제 새 RHI Final07 PID32308와 saved readback07 PID24360은 실행 중이며 아직 최종 통과 판정 전이다.

정확 재개: Final07 actual loaded DLL/Driver/native18+Brutal5·runtime byte 불변과 Saved07 Art14/8·401·8308 결과 확인 → Root actual PNG/first finalized pose 검수 → Final07 Saved-only binder로15개 SHA 증거 결속 → fresh Main closed census 및 현재 Source98/Effects5874/DAS203/native109 CAS 확인 → helper 선택17개(Art14+Source3) staging/Root prepared 검수/apply → fresh Main RHI/saved/Root PNG/Input13 before-after 불변 → finalizer·각 도메인 완료 기록. 다른 owner 에디터 종료·저장·입력을 제어하지 않는다. 전체 추출/재임포트/401 창 retime은 반복하지 않는다.

<!-- BrutalInputDevMapComplete_20261010 -->
## 2026-10-10 — B 입력·DevMap 요청 완료 및 재개 기준

이번 요청은 완료다. Source KZGameplayTags.h/cpp·KZPlayerController.h/cpp4개, 고유 저장 에셋5개(IA_BrutalAttack 신규·IMC_Default·DA_InputData·Player Definition·DevMap)를 Main에 적용했다. [FinalVerification](../../Metadata/BrutalInputDevMap_20261010/FinalVerification.json) success=true, fresh saved28/dirty0와 PIE6종12마리/초기 stats·native 인간4종 policy 성공·저장 byte 불변·작업용 author/verifier 정상 종료가 마지막 검증이다. 최종 실제 로드 DLL은 UnrealEditor-Khazan-20261010.dll / b6e6cae57236e8c44fd750a747ac461d8eafb0884cb5f3ede04065acbd35c1d3다.

후속은 Router→Architecture/Migration→COMBAT_REACTION_RUNTIME_20261008.md의 이번 B 절과 README/FinalVerification→현행 Source/InputData/Player grant 순서다. 먼저 current manifest·Source와 Main 변경을 확인하고, 이미 성공한 author.py·과거 CombatReaction/Monster 전체 authoring/delivery/retime를 반복하지 않는다. 사용자 테스트는 새 Main 에디터에서 DevMap을 열고 소진된 몬스터 근처에서 패드 B를 누른다. 실제 물리 B 누름 검사는 이번 자동검증 범위가 아니다. Apes/Yetuga 자율 AI는 아직 None이며 이번 배치 완료와 구분한다.

초기 반사 API 오류·navigation timeout 기록은 보존했다. navigation flags0x20의 정확한 의미는 AsyncLoadLock으로, 자동 갱신 꺼짐이라는 초기 추론을 정정했다. Author09는 lock 해제 뒤 rebuild/projection을 확인한 뒤 저장했다. Author08은 receipt 없이 종료해 원인을 확정하지 않았으며 종료 후 대상 byte가 원본과 같았다. 첫 Verify의 native test는 성공했지만 observer 종료 처리 버그 때문에 PID16396만 종료하고 완료 이벤트 우선/PIE 요청1회로 보완한 새 PID21416에서 같은 검사를 다시 통과했다. 제품 코드는 이 helper 문제로 변경하지 않았다. 상세는 Metadata/BrutalInputDevMap_20261010/README.md와 실패/정상 로그를 따른다.


<!-- MonsterVFX_SharedPolishIntake_Native7QA_20261010 -->
## 2026-10-10 22:00 KST — MonsterVFX Native7의 오래된 X QA와 외부 변경 반입 checkpoint

[Native7 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt7/Driver.json)는 failed다. [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt7/Exit.json)의 PID22164/449.312초/exit0·1390 captures는 프로세스 정상 종료이며 테스트 통과가 아니다. 유일한 실패 단언은 `Actual granted player Brutal claims actual Apes exhaustion`이다. Root가 확인한 원인은 QA가 예전 X를 눌렀지만 최신 Player Definition의 실제 grant가 B인 불일치이며 제품 Brutal 고장의 증거로 해석하지 않는다. private DEV2의 B 경로 보완은 준비됐고 새 build/실행 증거는 아직 결속 전이다.

별도 Player polish의 [Delivered17](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json)은 UTC12:47:50의 Source3+Art14 전달 기록(SHA `a75fa980…7ed7fa9`)이며 상태는 `SelectedPolishDeliveredFreshMainValidationPending`이다. 그 작업의 최종 Main 검증 완료를 주장하지 않는다. MonsterVFX의 Source semantic intake는 진행 중이고, [SharedEffectsRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1…bb422`로 exact saved Art14의 private byte 반입은 완료됐다. 기존 Effects2034=승인 갱신14+불변2020, own Art457 SHA/Main-before CAS·원본 보고서 불변, 본 반입 Main 제품 변경0이다.

Yetuga [Diagnostic1](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt1/Driver.json)은 failed다. pause_anims editor setter가 SingleNode pose를0초로 재설정하여 same_pose=false였고 game time/camera는 그대로였다. 저장 shader bytes 및 Source/asset 변경0인 진단이며 잘못된 pose A/B를 품질 통과로 쓰지 않는다. 기존 SingleNodeInstance.set_playing(False)를 사용하고 정확한 상태를 복원하는 QA 보완은 준비만 됐으며 아직 실제 pass가 아니다. 반입 전 shared shader에도 atlas mask가 실제 연결되어 있었으므로 MI02 inherited white만으로 full-card alpha를 추론한 해석은 철회한다(상세 Art 정본).

정확 재개: 최신 Main3 Source semantic merge/DEV B fixture를 새 Build19에 결속 → 반입 Art14의 fresh saved readback/실제 graph와 Yetuga 동일 pose 비교 → current DLL의 full Monster·Player·Rim·Yetuga RHI → Root 전체 PNG/VisualQA와 revision SHA·candidate integrity → 최신 Main Source/Content/native CAS 및 guarded 선택 전달 → fresh Main saved/RHI/Root visual/finalizer. 과거 Native7/Diagnostic1을 성공 증거로 재사용하거나 전체487 author/457 import를 반복하지 않는다. **본 MonsterVFX Main 전달0이며 최종 완료가 아니다.**

<!-- PlayerAttackVFXPolish_MainVisualHold_20261010_2209 -->
## 2026-10-10 22:09 KST — 공격 VFX 선택 전달 완료·새 Main 화면의 잔여 결함 복구 중

앞선21:43 기록 이후 Art14·Source3의 선택17파일을 Main에 전달했다. [Delivered](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json)의 SHA는 `a75fa9803d7a40c1d0682b27dc1a085724477c38d2b2c73f632991ddb7ed7fa9`이고 상태는 `SelectedPolishDeliveredFreshMainValidationPending`이다. 이 전달 사실을 최종 품질 완료로 읽지 않는다. Build04 exit0과 현재 native DLL `d1957a4bd437fa5f717f99ad41122c8336707ecdc4a45819df2bd0a3c9d09361`, Source3를 사용했다. 다른 Input B/DevMap·몬스터·나머지 Effects 변경은 보존했다.

[새 Main 실제 재생](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Processes/ResumeMainFinal01/Driver.json)은 PID29700/exit0·283PNG·native18+Brutal5·저장0·compile failure0으로 통과했다. [새 Main 저장 검증](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Processes/ResumeSavedMain01/CombinedSavedAudit.json)은 PID5876/exit0·8montage/401창/8308field·Art14/PD3·저장0/byte 불변으로 통과했다. 그러나 Root가 직접 본 Main123/124의 SpinningAttack 바닥 흰 원판과 Main221의 BrutalFront 검은 사각 면 때문에 **전체 visual pass·Completion·finalize는 보류**한다. 데이터·runtime 통과가 이 결함을 부정하지 않는다.

흰 원판은 원본 smash_strong의 `refrac` emitter가 사용하는 `FMI_MashRefractionShock_01_DepthFade_03`의 굴절용 부모를 importer가 ParticleColor 흰 발광/opacity로 변환한 경로가 유력하다. 원본 Ref_str 곡선·900cm size·size-over-life·child ring/depth-fade를 표적 확보했다. 검은 면은 PP_Grapple/Spear/Ghostarm 입자군을 분리한 실제RHI 진단을 실행 중이며 아직 producer를 확정하지 않는다. 기존 효과를 통째로 삭제하거나 원본 시간·색·크기를 임의 변경하지 않는다.

정확 재개는 Saved `Resume_20261010/ResidualProducerIsolation/557a719fe4c047b7a6a26e9a1bdc7db4`의 owned PID26416 결과/PNG/T3D 확인 → producer 확정 후 기존 부모만 작은 Private shader 복구/전후SHA·SM6·isolated PNG → 새 후보 Art 증거(원본/계산/adapter/임시값 분리) → fresh Private 실제/saved/Root 화면 → 기존 Delivered를 보존한 별도 Art-only guarded follow-up 전달 → fresh Main 실제/saved/Root 화면·Input B13 불변 → 새 완료 receipt·Art/Engineering 정본 append 순서다. Source3/native가 바뀌지 않는 Art-only 복구로 새 runtime class/file를 만들지 않는다. 사용자의 Rider 에디터는 제어하지 않고 Root가 시작한 숨김 background만 사용한다. 이전 snapshot·실패·후보·Delivered는 덮어쓰지 않는다.


<!-- MonsterVFX_Build19_Saved7_Diagnostic2_Native8_20261010 -->
## 2026-10-10 22:16 KST — MonsterVFX current Build19 전체 Native8 통과·Player 회귀 진행

[Build19](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt19/Exit.json)은85.828초/exit0·Main104/private107 입력 불변이며 current DLL은 `b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a`다. [Source intake](../../Saved/ImportReports/MonsterVFX_20261008/MainRebase/PlayerPolishSourceIntake.json) SHA `4a44ccc68c1d8969c6e5f6ac369d3eb06b0077eac44493ca07c64335d77c08e4`의 외부 Source3 semantic merge와 private DEV B 경로를 이 build에 결속했다. 앞22:00의 build/semantic 검증 대기는 이 후속 실제 결과로 보충하며 원본 receipt의 당시 pending flag를 다시 쓰지 않는다.

[Saved7](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)은 PID12728/85.813초·487 Sequence/3342 State/Death6·Victim43/26·shared2034를 passed로 확인했고 saves/mutations0·선택499/공유bytes 불변이다. [SharedEffects revision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1012742b376300dee3398a9755889027d1d80e8057ff0a38bcabbb422`를 소비한다. [Build19 readiness](../../Saved/ImportReports/MonsterVFX_20261008/DeliveryReadiness_Build19.json)는 Main/Work 입력 및 bounded native7/private3·2034 reuse(승인14+보존2020)/own Art457와 Main-before CAS 유지, 네 frozen helper의 syntax/pure marker 검증을 기록한 전달 전 snapshot이다. snapshot 작성 당시 Native8은 실행 중이었다.

이후 [Native8 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Driver.json)는 actual loaded current DLL로 `Khazan.MonsterVisual.PIE` Result=Success/passed,1568PNG/package saves0/material compile failures[]다. [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Exit.json)는 PID30504/492.813초/exit0이다. Native7의 obsolete X QA 실패를 성공으로 재해석하지 않고 새 B 경로의 이 독립 실행을 사용한다. Yetuga Diagnostic2는62.625초/102PNG·두 pose/time/camera 불변식을 passed로 확인했으며 시각 범위는 Art 정본에 분리했다.

Root의 current Player 실제 RHI 회귀 wrapper session45759는 실행 중이며 통과 결과는 아직 확인하지 않았다. 정확 재개: 그 Driver/Exit·current loaded DLL/표현 회귀 확인 → Root 전체 representative PNG/VisualQA의 최신 revision 결속 → candidate integrity/최신 Main Source·Content·native CAS와 process census → guarded 선택 전달 → fresh Main saved/Monster·Player/실제 PNG/finalize다. 외부 Player polish22:09의 잔여 시각 결함 조사 및 그 owner 변경을 보존한다. **본 MonsterVFX Main 전달0·전체 완료/최종 visual pass는 아직 아니다.** 전체487 author/457 import를 반복하지 않는다.


<!-- MonsterVFX_CurrentQA_RecoveryDeathVisualHold_20261010 -->
## 2026-10-10 22:22 KST — current Player·Rim 통과 후 Yetuga 실제 시각 결함으로 전달 보류

앞22:16 이후 [Player Attempt1](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt1/Driver.json)은 actual current DLL `b84df875…e311a`의 Khazan.CombatEffect.PIE Result=Success/passed·389PNG/package saves0/compile failures[]로 종료했다. [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt1/Exit.json)는 PID29848/162.5초/exit0이다. [regular Rim10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt10/Driver.json)도 같은 DLL에서 diagnostic_mode=false·24PNG/saves0/mutations0/compile failures[]·48.921초/exit0(PID17084)으로 passed다. Native8/Saved7/Build19의 실제 통과 기록은 유지하며 이 추가 결과를 whole visual pass로 사용하지 않는다.

Root가 Native8 Yetuga Recovery1262/1264의 불투명 검은 spiral card와 Death1348의 큰 흰 hard rectangle을 실제 화면에서 확인했다. Recovery 당시 own tagged `KZMVFX_5906a257e7e402000dea3611`/FP_Boss_Yetuga_Roar_01 PSC가 존재하나 정확한 pixel producer는 include/exclude 진단으로 확인해야 한다. Death rectangle 원인 조사는 delivery_review가 소유한다. **Root VisualQA는 미통과, MainDelivery/Prepared.json 미생성, 본 MonsterVFX Main 전달0**이다. 자동화 Success·compile0이 이 시각 결함을 부정하지 않는다.

[LateRecoveryScriptRevision](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/LateRecoveryScriptRevision.json) SHA `46f57bca…fde521b8`로 기존 Yetuga QA 두 파일만 최소 확장·py_compile/세 mode AST 검증 후 고정했다. Root wrapper `run_monster_vfx_yetuga_pie_20261010.py --diagnostic-late` 또는 driver의 KZ_MONSTER_VFX_YETUGA_DIAGNOSTIC_LATE_RECOVERY=1은 Recovery를 자연0초부터 재생해 actual mesh pose>=2.2초에서 멈춘다. 2.2초는 요청 범위2.0–2.35초 내 명시적 QA 선택이며 원작 gameplay 값이 아니다. Native8 Sequence의 position_seconds300.822/301.622는 world time이라 exact source pose로 사용하지 않는다. named OnlyOwnRoar01/WithoutOwnRoar01·exact own inventory·same pose/time/camera/restore·shader0를 유지하고 regular3-case/early2-case 경로는 그대로다. 이 문서 작업의 Source/native/asset/editor 변경은0이다.

정확 재개: Root가 실행하는 late 진단의 실제 Driver/PNG로 Roar01 pixel 소유와 phase를 확정 → Death rectangle 원본/현재 material chain 표적 조사 → 필요한 경우 해당 producer의 가장 작은 private 표현 수정/원본·adapter 구분 및 before/after 증거 → current saved/runtime/실제 전후 PNG 재검증 → Root VisualQA·candidate 결속 → 최신 외부 변경/Main CAS 확인·guarded 전달 → fresh Main actual saved/RHI/visual/finalize다. 실패 화면을 숨기거나 원본 이벤트를 통째로 지우지 않으며 Source/Content 과거 전체 author/import를 반복하지 않는다.

## 2026-10-10 22:49 KST — 공격 VFX 재개, 잔여 면 경계 검증 중

- 이번 재개 대상은 Player 공격 VFX 보정이다. MonsterWork의 첨부 파일은 별도 Monster 구현으로 전환하는 지시로 해석하지 않았다. 기존 Source3 + Art14의 Main 전달은 `MainDelivery/Delivered.json`에 보존된 provisional 상태이며, 최종 Completion은 아직 없다.
- Private08(PID27052, exit0, 134.928307초)은 native18 + Brutal5 기술 검증과 first-pose13/13 검사를 통과했다. SavedPrivate08의 정확한 파일명은 `CombinedSavedAssetAudit.json`이며, Montage8 / 이벤트401 / 원본8308 검사와 Saved Art16 검사에 통과했다. 앞선 기록의 `CombinedSavedAudit.json` 표기는 이 정확한 파일명으로 읽는다.
- Root가 실제 PNG를 확인했다. Spinning123/124의 불투명 흰 원판과 Front221의 큰 검은 하늘 면은 사라졌지만 Front223/224에 옅은 직선 다각형 경계가 남아 Private08의 시각 승인은 보류했다. 성공 로그만으로 완료 처리하지 않았다.
- Shock 부모는 Private에서 순수 굴절로 보정된 SHA `3d2269e5a1efad4b53c6ca04cab5be1b8a8603be0853fc61f4760d6e571c6e32`이다. 원본 곡선/자식 값은 보존했고, PixelNormalOffset/CoverageIgnored와 radial normal은 원작 그래프 미확인에 따른 엔진 복원 adapter다. 실제 굴절파의 가시성은 아직 미확인이다. early paired captures `ResidualProducerIsolation/108b6dce35ea4e5da34b406f74197179` 및 dense15프레임 `6429022674b84f4eab00444d947d9b40`은 원판 제거만으로 굴절파 복원 통과를 주장하지 않는다.
- SubUV 부모는 PC.A를 먼저 saturate한 Private08 값에서, 원본 Ghostarm `ParticleModuleParameterDynamic_7.DynamicParams[2].Opa_dissolve`를 마지막 atlas opacity에 연결했다. 원본 table `[0,.21508475,.31788456,.34419835]`/TimeScale3은 보존했다. `saturate(atlas.R - DP.Opa_dissolve)` 연결은 제거된 원작 노드 그래프에 대한 명시적 복원 adapter다. 현재 Private SHA `e9cfc1b53d34ff0f8eed7e183282659e72c49a307b4ba1918563654f5dffd1b8`, author PID25072/exit0/36.469초/부모1개만 저장/다른 Effects2033개 불변. Main의 추가 부모2개는 아직 수정하지 않았다.
- Active Frozen16 SHA `4df6f3f20adbfdd42607d0de39f873c2ee5788ee5d91899b68daedee76d7079e`; 이전 Frozen/author/실패/보류 증거는 Saved History와 각 프로세스 폴더에 보존했다. Source3/BuildResumeFinal04/native DLL `d1957a4b…`는 그대로다. Root가 숨긴 `ResumePrivateFinal09` 전체 공격 실행을 시작했다. 사용자 에디터는 조작하지 않았다.
- 정확한 재개: Private09 종료/RuntimeIntegrity/PNG223–225와 Spin123–124를 Root가 확인 → 필요하면 Shock pure-refraction 무저장 기술 진단으로 가시성 원인 확인 → 현재 해시로 fresh Saved 감사 → root visual16 + 실제11 proof를 `Resume_20261010/Tools/art_followup_exact.py`에 연결 → 닫힌 Main의 전체 CAS/원본 receipt 불변 확인 후 Art 부모2개만 follow-up prepare/apply → fresh Main actual/saved/first-pose/Input13 불변 검사 → 새 follow-up Completion과 도메인 문서에 실제 결과 추가. 기존 Main17 receipt를 다시 쓰거나 Private08 보류를 현재 통과 증거로 사용하지 않는다.


<!-- MonsterVFX_PrivateMaterialRepair_LateDiagnostic_D00Tail_20261010 -->
## 2026-10-10 22:52 KST — MonsterVFX 재질3 private 수정 후 전체 검증·Main 전달 대기

현재 private 표현 수정은 WPO1+Decal2로 실제 저장 완료다. [WPO Repair](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Roar02/Attempt1/Repair.json)·[Decal Repair](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply1/Repair.json)의 SM6 compile/statistics·PS/MI/나머지455 Art·author499/Main 불변을 확인했다. Root의 JointVisualMaterialRepairRevision SHA `138dc65c…e107a`/현재 assembler `6af29…`는 Source11+499+457+reused WPO1=968 선택 후보를 결속한다. 원본 보고서 및 Definition6/Victim43/Shared14 revision은 그대로이며 이번 기록은 Source/DLL/에셋/UE를 조작하지 않는다.

이전 실패를 보존한다. Roar01은 시간상 함께 존재했을 뿐 actual template-only/exclude에서 pixel producer가 아니었고 Roar02로 정정됐다(Art 정본). D00 QA1은 pixel 포함/제외·동일 pose/time/camera/복구가 유효했지만 clipend+9+1초에서 수명30초 혈흔까지 소멸을 요구한 QA 때문에 failed다. D00 원본9초/혈흔30초를 유지한 [tail QA 수정](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/TailObservationRevision/TailObservationRevision.json)과 수정 전 스크립트·실패 Attempt1을 보존했다.

가장 최근 제한 결과는 [LateDiag4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt4/Driver.json)의49.469초/50PNG·후반 same-pose passed, Root0022 Normal/0034 OnlyRoar02의 검은 면 없음이다. 문서 작성 중 [D00 QA2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt2/Driver.json)/[Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt2/Exit.json)도PID13520/90.187초·passed로 저장됐다. D00+10.0014초/전체+31.0109초 자연 소멸0, 모든 복구/byte 불변·저장0이지만 overall_visual_pass=false다. 이전 Native8/Player1/Rim10 성공을 재질3 이후 fresh 전체 성공으로 재사용하지 않는다.

정확 재개: 재질3의 current SHA/Joint revision·원본 immutable/Main-before CAS 재확인 → fresh Saved readback과 실제 current DLL의 full Monster·Player·regular Rim·regular Yetuga 네 회귀 → Root 실제 대표 PNG/전체 VisualQA → candidate integrity·revision launch freshness → 최신 다른 task Source/Content/native·process census/CAS 보존 확인 → guarded 선택 전달 → fresh Main saved/RHI/실제 PNG·finalizer다. D00 제한 통과와 late clean pose만으로 candidate를 passed로 만들지 않는다. **본 MonsterVFX Main 전달0이며 최종 완료가 아니다.** 전체487 author/457 import는 반복하지 않는다.


### 2026-10-10 22:53 KST — 재개 입력의 정확한 filename

재개 시 소비할 실제 파일은 [Authoring/VisualMaterialRepairRevision.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json), SHA `138dc65c…e107a`다(앞 JointVisual 표기 정정). Root가 D00QA2 종료를 확인했고 fresh 네 회귀를 새로 준비한다. 이 receipt의 passed를 전체 시각 통과로 읽지 않는다. Roar02 positive visibility·fresh Saved/Monster/Player/Rim/Yetuga·RootVisual/candidate·Main 전달/fresh Main은 별도로 완료해야 한다.

## 2026-10-10 23:24 KST — Player VFX Art 후속 검증·실행 코드 보존

기존 Player 공격 VFX 선택 Source3/BuildResumeFinal04/native DLL `d1957a4b…`와 Main17 provisional receipt는 보존했다. 새 runtime 파일/class·게임 코드 변경은0이다. 이번 후속은 Art 부모의 private shader 연결 보정이며 자세한 출처/현재 SHA/화면 HOLD는 Art continuity의 같은 날짜23:24 절을 따른다.

Fresh Private10 실제 native18+Brutal5(PID12264/exit0/136.062294초)와 SavedPrivate10(PID27468/exit0/94.155499초)은 기술 검사를 통과했다. Saved montage 감사의 정확한 filename은 `CombinedSavedAssetAudit.json`이다. Root가 후반 흰 particle 카드로 visual HOLD를 유지하여 기술 통과를 최종 완료로 읽지 않는다. Main 추가 부모 전달·fresh Main02·최종 Completion은 아직 없다.

Root owned `BlackProducerActual06`은 같은 native 포즈/time/camera에서 SceneCapture의 숨김 목록만 바꾸는 producer 진단이다. 게임 시간/포즈/PSC/product 변경0, native 전체 완료 자료와 구분한다. 실행 결과를 받은 뒤 Art-only v2 전달 도구의 현재 Source/native 보존·전체 Main CAS/closed gate를 확인하고, fresh Main actual/saved/first-pose/Input13 보호 결과를 얻어야 완료할 수 있다. 이전 Main17 Prepared/Delivered와 실패·보류 기록은 덮어쓰지 않는다.


<!-- MonsterVFX_138_FourFreshRHI_D00Hold_202610102348 -->
## 2026-10-10 23:48 KST — 재질 revision 이후 네 실제 회귀 통과·D00 바닥 양성 검증 보류

[Build19](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt19/Exit.json)과 [PlayerPolishSourceIntake](../../Saved/ImportReports/MonsterVFX_20261008/MainRebase/PlayerPolishSourceIntake.json) SHA `4a44ccc68c1d8969c6e5f6ac369d3eb06b0077eac44493ca07c64335d77c08e4`를 유지한다. 현재 Main98/private101 Source, 전체 Main104/private107 Source+Config+uproject 및 native3는 Build19 actual input/출력과 정확히 같다. Source11(기존 runtime9+DEV2) 선택 범위에 새 runtime class/manager/state 복사본을 추가하지 않았다. DLL은 `b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a`, BuildId55116800이다. [VisualMaterialRepairRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json) SHA `138dc65c…e107a`는 private 표현 수정3만 별도로 결속하고 원본 plan/author499/Definition6/Victim43·26/Shared14를 보존한다.

[Saved8 readback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)는3342 State/487 Sequence/Death6 및 revision readback3·선택 bytes 불변/저장0/all_checks_passed다. 재질 revision 이후 [Native9 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt9/Driver.json)는 PID31392/581.219초/1549PNG, [Player2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt2/Driver.json)는 PID18124/144초/388PNG, [regular Rim11](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt11/Driver.json)은 PID19200/40.109초/27PNG, [regular Yetuga5](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt5/Driver.json)는 PID28536/80.438초/106PNG로 모두 passed/exit0/package saves0/material compile failures[]이며 실제 loaded DLL SHA가 위 Build19와 일치한다. Native7 QA 실패·이전 Native8 성공을 이번 통과로 덮어쓰지 않는다. runtime pass와 원작 pixel parity/Root 최종 화면 승인을 구분한다.

[D00 QA4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt4/Driver.json)는 DecalComponent.get_component_location 미노출 API로 failed/0PNG였고 모든 기존 visibility/animation/capture/postprocess 상태 finally 복구와 saved bytes 불변은 true다. failed Driver/Exit를 보존한 API 보완 뒤 [D00 QA6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt6/Driver.json)는 same pose/time/camera·복구/수명·저장0을 passed로 확인했다. Root가 확인한 Roar02 positive helix는 Art 정본을 따른다. D00 순수 바닥 양성 화면은 아직 미확정이며 Source의 incoming-hit producer나 임의 게임 수치/새 timer로 이를 대신하지 않는다.

읽기 분석 정정도 보존한다. P5=.2/미연결 FadeOut 설명은 잘못된 node index 대조라 철회했고 actual 두 부모 FadeOut=1/P0 상수 RGBA1을 saved pin으로 확인했다. Particle.Color alpha0 가설은 Engine MaterialTemplate.ush664–669의 initialized RGBA1 및 실제 P0 상수 양쪽에서 제외됐다. Shader source/polar 원작 일치 미확인과 화면 진단의 자세한 한계는 [Art 정본](../Art/MONSTER_VFX_PLAYBACK_20261008.md)을 따른다.

23:39:44 KST readonly preflight는 Source11+author499+Art457+reused WPO1=968 live selected CAS·Shared2034/current native/input·Saved marker·frozen critical helper4를 passed로 확인했다. 외부 Player ArtFollowup Main2 receipt는 없고 Main Shock/SubUV bytes는 이전 값이다. 다른 절대경로 PlayerPrivate editor PID30020을 helper census가 delivery blocker로 분류한다는 앞 설명은 철회한다. 실제 frozen census_gate는 unknown/우리 private 및 정확 Main identity만 검사한다. 23:43:09 KST 실제 census empty/closed-Main gate passed이며 다른 task 프로세스를 종료/조작하지 않았다.

**현재 Root VisualQA/candidate/Prepared/Delivered 미생성·이번 MonsterVFX Main 전달0**이다. 정확 재개: Root owned D00 MID-only 분리 진단·pure floor 양성/기존 상태 복구 확인 → 필요시 최소 수정과 새 immutable revision/actual saved·current DLL 네 회귀 → Root VisualQA/candidate → 최신 Main Source/Content/native 및 외부2 receipt/process CAS 재확인 → guarded968 alias/선택 전달 → fresh Main saved/Monster·Player·regular Rim·regular Yetuga/Root PNG → finalizer. Source/runtime/header/schema/원본499/457 전체 author를 반복하지 않는다.



<!-- MonsterVFX_DecalReauthorStaging2_202610102357 -->
## 2026-10-10 23:57 KST — QA8 알파 분리·staging 보존과 새 Decal2 적용, 전체 검증 대기

[ReauthorStaging2/Staging.json](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/ReauthorStaging2/Staging.json), SHA `5dbc6a39…1af1e0`는23:51:21 KST 원본2 복원 당시 기록이다. 원본2 backup 및 이전 수정2 backup을 정확 SHA로 보존했고 original138도 보존했다. append 직전 Root의 Probe2/Apply2 실제 passed/save0·2를 확인했으므로 현재2가 아직 original이라는 설명은 사용하지 않는다. [Apply2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply2/Repair.json), SHA `8783a5a9…5790a4`의 after2는 `52d746d6…474dc0a`/`c4eb1ca6…5d33798`와 실제 일치한다. Main/Source/native mutation0·원본455 Art/499 author와 이전 보고서를 보존했다.

마지막 제한 진단 [QA8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt8/Driver.json)는24PNG/74.672초·passed/모든 상태 복원/save0다. Root D0020/E0022 관측으로 Param alpha 가설을 제외했지만 정상 설정 D00 positive는 아직 최종 승인되지 않았다. 기존138 기반 Saved8/네 회귀 성공을 새 Apply2 후보 승인으로 재사용하지 않는다.

정확 재개는 새 helper 동결 → Root probe2/apply2(실제 완료) → staging에서 보존한 기존138의 immutable archive 및 Main/Work mirror 새 current를 같은 assembler로 결속 → fresh Saved 및 Monster·Player·regular Rim·regular Yetuga → 정상 D00 positive·Root 실제 PNG → 최신968/Main-before/process CAS 확인 및 guarded 전달 → fresh Main saved/회귀/Root/finalizer다. rollback은 프로세스가 닫힌 상태에서 Staging.json의 PreviousRevision2Assets exact2/previous_sha256만 private 두 경로에 CAS 복원한다. Main을 복원/변경하거나487/457 전체 author를 반복하지 않는다. 이번 MonsterVFX Main 전달0·전체 완료 아님이다.


### 2026-10-10 23:58 KST — current revision6309 실제 결속 추가 확인

새 assembler 결속은 이미 완료됐다: [current revision6309](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json), SHA `6309ef7d…21be60e`, 기존138은 [Revision1_138dc65c/Archive.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairHistory/Revision1_138dc65c/Archive.json)의 MainSaved/PrivateSaved 두 immutable bytes로 보존됐다. 따라서 위 재개 목록의 archive/새 current 결속은 완료 단계로 읽고 다음은 Root QA9(owned session19559)의 정상 D00 positive → current6309 fresh Saved/실제 네 회귀 → RootVisual/candidate·최신CAS/guarded968·fresh Main이다. receipt의 passed를 시각 통과로 읽지 않으며 이번 Main 전달0다.


<!-- MonsterVFX_6309_Saved9_QA10_PSCBlocker_202610110018 -->
## 2026-10-11 00:18 KST — Saved9·D00 제한 승인 뒤 QA10 완료, Native10 진행

현재 Source11/runtime9+DEV2와 Build19 native는 그대로다. current6309의 [Saved9](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)는 PID31520/99.75초/exit0·actual graph3/bytes 불변/save0 passed다. [QA9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/Driver.json)(PID23764/84.985초/24PNG/exit0) 복구와 [RootD00Review](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/RootD00Review.json) SHA `6e68bf2d…fab27e0`의 정상0008 D00 soft-circle vs0012 pure-floor 양성을 확인했다. Normal0000 검은 PSC 카드는 visual HOLD다.

마지막 [QA10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt10/Driver.json)은 PID17540/89.328초/30PNG/exit0·복원/save0 passed이며 Root가 FP_DeathEffect와 world fall2 모두의 검은 카드 양성을 확인했다. burst12만으로 원인을 확정하지 않는다. actual slot3/6/6·current native graph/원인 readback은 대기고 Root Native10 current6309/PID10736은 실행 중이다. source alpha·기존 복원 코드 [SourceEvidence](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/QA9BlackCardSourceAudit/SourceEvidence.json)는 잠재 약점 근거로 유지한다.

정확 재개는 QA10 실제 identity와 native graph 표적 확인 → Native10 actual regular와 비교해 원인·최소 수정 필요 여부 결정/필요시 새 immutable revision → 해당 current의 fresh Saved·Native10/Player3/Rim12/Yetuga6 → Root VisualQA/candidate → 최신 Main Source/Content/native·외부 receipt·process CAS → guarded968 → fresh Main saved/실제 네 회귀/Root/finalize다. 이전138 네 회귀로6309를 승인하지 않는다. [QA7 sidecar](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/QA7PixelAnalysis/ReferenceResolution.json)는 `fc5fb913…dd00e0a` 원본 분석을 바꾸지 않고 archived138에 연결했다. 문서 외 제품/Source/helper 수정·agent UE 실행0, MonsterVFX Main 전달0·전체 완료 아님이다. [runtime 정본](MONSTER_VFX_RUNTIME_20261008.md)과 [Art continuity](../Art/ART_WORK_CONTINUITY.md)의 같은 checkpoint를 따른다.

## 2026-10-11 — Apes·Yetuga 전투/플레이어 낙하 착수 체크포인트

- 요청과 소스/원본 자료 확인 완료. Main을 별도 `C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan`에 실제 파일 복사했고 mutable 에셋 hardlink는 사용하지 않았다. BaselineHashes는 별도 프로젝트 Metadata/GiantCombatFall_20261011에 저장했다.
- 마지막 확인: 다른 MonsterVFX 전용 에디터 PID19764 실행 중; 제어/종료하지 않음. Main B 브루탈 입력 및 DevMap 몬스터 12배치를 보존해야 한다. 별도 프로젝트에서만 구현/저장/PIE 후 Main 최신 해시를 비교해 소유 변경만 합친다.
- 실제 게임 편집/빌드/PIE는 아직 시작 전. 다음은 원본 SB/AC 조건·원본 시간→현재 타임라인 계획 생성, 기존 StateTree/Combo 계층 확장, 기존 InGame/DAS Fall/FallAttack 클립 연결, 높은 발판 및 실제 낙하 X/착지 회귀 검사다.
- 정확한 재개 위치: 별도 프로젝트 Source는 현재 Main 복사본이며 Metadata/GiantCombatFall_20261011/BaselineHashes.json이 비교 기준. 기존 MonsterWork/VFXWork 소스를 Main에 통째로 복사하지 않는다.

<!-- PlayerAttackVFXPolish_Private11_ArtHold_202610110040 -->
## 2026-10-11 00:40 KST — Player VFX 기존 런타임 검증 유지·Art 후속 화면 HOLD

기존 ARCH-83 표현 수정의 Source3/Main/private bytes와 BuildResumeFinal04 native d195/PDB95e4는 그대로다. 기존 Main Source3+Art14 provisional 전달 후 추가 Art-only 후보는17개이며, 새 Private11 native18+Brutal5와 Saved11의8몽타주/401구간/8,308field 및 저장0·파일 불변 검사가 통과했다. 이번 재개 중 새 runtime 파일·class·gameplay 계약·Source/native/module 변경은 없다.

Root는 회복 리본의 흰 카드 producer와 private 부모1 보완을 확인했으나 회전 공격의 faint triangle 때문에 Art 화면 HOLD를 유지한다. 전체 원인·후보 해시·Actual11 비교 조건 차이·Actual13 target miss·현재 owned Actual14와 정확한 부모4 후속 전달 절차는 [Art continuity의 00:39 절](../Art/ART_WORK_CONTINUITY.md)에 기록했다. 추가 Main 전달/fresh Main02/final Completion은 아직 없으며, 이전 build/기술 통과를 최종 화면 품질 완료로 확대하지 않는다. 사용자 및 다른 작업 에디터를 제어하지 않았다.


<!-- MonsterVFX_MainDelivered_MainSavedFailed_20261011010443 -->
## 2026-10-11 01:04 KST — MonsterVFX 적용 완료·MainSaved 실패 재개점

[Delivered968](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/Delivered.json), SHA `12f3af9d…c86603a`의 실제 전달은 완료됐다. alias `UnrealEditor-KhazanMonsterVFX20261008.dll`/manifest `6424d461…dc993`가 선택됐고 Source intake4a/Config·native·B/DevMap·외부 Source3/Shared14를 보존했다. current6309 private Saved9·Native10/Player3/Rim12/Yetuga6·RootVisualQA는 passed다. QA10 카드 HOLD는 QA11 shader 준비/8 asset bytes 불변 뒤 해소됐고 새 alpha-mask 제품 수정은 없다.

최신 실패는 fresh MainSaved PID31324/Exit1/status=failed·저장0/변경0, Effect data_fields assertion(line156)이다. event `KZMVFX_f3af66febacc3ab35102cf8b`의 Halberd FinalBlow와 FP_BloodSplit_01 Main 누락을 Root가 식별했고 정확 object field/재사용 resource closure 감사를 진행 중이다. [MainSavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/MainSavedReadback.json)의 당시 SHA `1d8535b0…dfa50`를 보존한다. MainMonster PID30664의 runtime은 계속 검증 중이다.

재개는 failed field export·필요 의존성 exact Main/private/원본 manifest/SHA 확인 → 필요한 최소 추가 전달을 별도 revision으로 guarded 처리(original968 보존) → fresh Main saved 및 actual Monster/Player/Rim/Yetuga 네 RHI → Root MainVisualQA/finalizer다. actual `FinalVerification.status=MainDeliveredAndFreshVerified` 전에는 완료9문서를 쓰지 않는다. 기존 prepared/delivered를 전체 재실행하지 않으며 새 ARCH-86·외부 Player 부모4 Art HOLD 및 latest Main을 CAS로 보존한다. 초기968 성공과 현재 Main 검증 실패를 분리한다.


<!-- MonsterVFX_AdapterSupplement972_FreshMainPending_20261011012157 -->
## 2026-10-11 01:21 KST — MonsterVFX supplement4 완료·Main972 fresh 검증 재개점

[SupplementalDelivered](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json), SHA `d7487b5085e02d8ea1da66d80cd9a0383ca66e0df8d4e1fd25478a130bc1ed44`, 상태 `FourAdapterDependenciesDeliveredFreshMainRequired`로 absent Main adapter4를 exact copy해 총972=original968+별도4다. 네 파일은 Blood/FP_BloodSplit_01/02, FP_Dmg_Blood_Base, FP_Dmg_Blood_Base_BK다. 원래968/Art457/6309 영수증은 그대로이며 Source/native/material graph/private package 변경0, 이번 asset copy4·save0이다. 기존 private Saved9/Native10/Player3/Rim12/Yetuga6/RootVisualQA는 private bytes가 불변인 범위에서 유지하고 새 Main 검증을 대체하지 않는다. original delivery 후 보호 입력 H.check도 passed이며 alias·Config·Source intake4a/ARCH85/B 입력/DevMap·외부 Source3/Shared14를 보존했다.

[Main1 exact](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Main1/Readback.json), SHA `e0fa8f00…5de5b`의 f3af66fe event ParticleTemplate null만 불일치이고 [Private1 registry](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Private1/Readback.json), SHA `2d4fc32b…6b8`는 consumer316/closure22=동일18+missing4다. Union reused_native=true/existing_native_sha256=null 재사용 분류가 누락 원인이다. [ToolRevision](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/HelperRevision/ToolRevision.json), SHA `df7925cc…8aa26`가 supplement helper 및 finalizer fresh Main gate를 기록하며 원래 deliver/saved/candidate helper는 불변이다. [FailureHistory](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/FailureHistory/Archive.json), SHA `cc4c51ad…66323`에 first saved failure와 pre-supplement runtime Success1560/517.265초를 exact archive했고 final proof에서 제외한다.

fresh MainSaved2는 Exit0/PID30360로 종료됐고 최종 검증은 대기다, MainMonster2는 진행 중이며 아직 Exit이 관측되지 않았다. FinalVerification은 아직 없다. canonical MainSaved가 첫 failed 값이면 archive로 보존한 역사 값이며 새 시도 완료로 읽지 않는다. 이미 실행 중인 두 session을 먼저 확인한다. 아래 명령은 **Root 재개용 기록이며 이 문서 작업에서 실행하지 않았다**. 현재 저장/Monster를 중복 실행하지 않고 해당 시도가 종료·실패해 새 시도가 필요한 때만 앞 두 wrapper를 사용한다. 이후 QA는 자기 hidden 프로세스만 순차 실행하고 다른 작업 에디터를 제어하지 않는다.

```powershell
$taskPython = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe'
# cwd: C:/Users/user/Desktop/GitProject/Khazan/Khazan
& $taskPython Scripts/Art/supplement_monster_vfx_adapter_dependencies_20261011.py --check
& $taskPython Scripts/Art/run_monster_vfx_commandlet_20261008.py Scripts/Art/monster_vfx_saved_audit_20261008.py --main
& $taskPython Scripts/Art/run_monster_vfx_pie_20261008.py --main
& $taskPython Scripts/Art/run_monster_vfx_pie_20261008.py --main --player
& $taskPython Scripts/Art/run_monster_vfx_rim_pie_20261010.py --main
& $taskPython Scripts/Art/run_monster_vfx_yetuga_pie_20261010.py --main
# fresh 네 proof와 Root MainVisualQA.json의 실제 승인 후:
& $taskPython Scripts/Art/finalize_monster_vfx_main_verification_20261008.py
```

각 Latest/Launch/Exit/Driver와 MainSavedReadback은 supplement 이후 생성됐는지 확인한다. Root actual MainVisualQA와 `FinalVerification.status=MainDeliveredAndFreshVerified` 확인 전에는 최종9문서/전체 완료를 쓰지 않는다. ARCH86/GiantFall 및 외부 Player 별도 Art 후보/후속 CAS는 보존하고 full import/author/initial968/supplement apply를 재실행하지 않는다.

## 2026-10-11 — Apes·Yetuga/낙하 분리 구현 진행 체크포인트

- Main 게임 Source/Content 미반영. 실제 작업본: `C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan` (완전 복사, hardlink 아님). 다른 Main 에디터 PID 18232의 MonsterVFX 회귀 테스트 관측; 제어/종료/재사용하지 않음.
- 기존 StateTree Task/Condition, Monster AI, ComboDefinition/ComboAction, 캐릭터 Definition/ASC 입력 경로를 재사용. 신규 runtime은 PatternAbility h/cpp, FallAbility h/cpp, 독립 비행/필드 수명의 SkillObject Actor h/cpp. 새 Manager/FSM 없음.
- 저장 원작 기준 Apes 48/Yetuga 81 단계(각 JustGuardReaction 포함), 19/24 Skill entry, Apes Early 가중 후보/Yetuga 순서 후보, 후속 거리/각도/벽/HP/쿨다운 조건 계획 JSON 생성. 원시 HP 65/60/50은 비율로 바꾸지 않음.
- 낙하 Start/Loop/Land는 CMC movement mode와 실제 LandedDelegate. 공중 X는 FallAttack 우선; 버튼 release와 착지를 분리. 원작 FallAtk AC Start의 .5/.005 속도와 End .42649162 InputEnd 사용. 점프 금지, DevMap 플랫폼/높은 PlayerStart author 준비. 기존 B 브루탈/12 몬스터 roster 보존.
- WorkBuild05 성공 이후 기능 보완 중. WorkBuild06은 UAnimMontage 섹션 API 이름 오류 수정, 07은 PatternAbility ASC include 오류 수정. 08 빌드 진행 중. 에셋 author/PIE는 아직 실행 전; 작성/빌드/런타임/원작 native 일치 상태를 혼동하지 않음.
- 다음: 08 결과 확인 → 전용 Work UnrealEditor에서 `Khazan.GiantFall.Author` → 저장 에셋 readback → native `Khazan.GiantFall.PIE` (Python은 에디터 수명/관측만, 조작은 C++ EnhancedInput/CMC fixture) → 실제 포즈/조건/취소 검증 → Main baseline CAS 및 기존 동시 변경 병합/별도 모듈 빌드 후 반영. 보고서는 `Metadata/GiantCombatFall_20261011`.
- 원작 native opaque/default는 확정하지 않음. 투사체 curve 적용/부재 Apes projectile mesh 시각 대체, 잡기 ragdoll 재현, target direct damage/capture/field의 남은 검증 범위를 완료 문서에 명시해야 함.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — MonsterVFX 실제 Main 완료·재개 기준 전환

[FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)은 실제 `MainDeliveredAndFreshVerified`다. 최종 선택972(Source11/runtime9+DEV2·author499·Art457·reused WPO1·adapter supplement4)의 guarded 전달과 fresh Main saved Sequence487/State3342/Death6·Monster/Player/Rim/Yetuga 네 RHI·Root 표본 검토를 완료했다. current6309 private 네 검증과 Main 검증을 분리 보존했다. QA11 shader 준비 후8 asset bytes 불변으로 QA10 카드 HOLD를 해소했고 새 alpha-mask 제품 수정은 없다.

후속은 [runtime 최종 절](MONSTER_VFX_RUNTIME_20261008.md) → FinalVerification/Delivered → 현재 Main Source/Config/selected/manifest·alias `UnrealEditor-KhazanMonsterVFX20261008.dll`를 확인한다. Build19 DLL·Source intake4a·Shared14·Definition6/Victim43·26/current6309가 인수 근거다. old Main98·구 alias/138 성공·전체 private Source를 다시 적용하지 않는다. ARCH-85/B input/DevMap·외부 Source3/Shared14·새 ARCH-86를 보존하고 필요한 후속만 최신 CAS/backup/검증으로 진행한다. 원작 shader/native/NI/full pixel parity·unsupported216/shipping 성능은 별도 미검증이다.

첫 MainSaved의 ParticleTemplate=null/원본 union reuse 판정 오류는 누락4 adapter의 [별도 전달](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json)로 해결했다. original968/Art457·pre-supplement Main 실패와 runtime Attempt1을 보존하며, 그 이전 Main Success는 최종 승인으로 재사용하지 않는다. 최종 인수는972 및 supplement 이후 Main proofs다. private bytes/Source/native/material graph는 불변이라 기존 private6309 proof를 유지했다.

최종14 gate·MainSaved2/Monster2/Player1/Rim1/Yetuga1 및 Root MainVisualQA11+6은 모두 supplement 이후 passed다. 확정 2026-10-11 01:41:38 KST, FinalVerification SHA `e4b2390f…5b994`, supplement SHA `d7487b50…1ed44`를 기준으로 재개한다. 상세 실제 시간/PNG 수는 runtime 최종 절과 증거를 따른다.

## 2026-10-11 01:50 KST — Player VFX 재개: 외부 Monster native 이관 보존·현재 Main 검증 대기

중단 재개 시 최신 Main의 외부 Monster VFX 전달을 확인했다. 원래 Player polish의 Source3/Build04 정본 위에 Source11 변경이 성공한 Monster Build19의 compiled Source101과 함께 Main에 전달됐고, 현재 선택 모듈은 `UnrealEditor-KhazanMonsterVFX20261008.dll` SHA b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a이다. 외부 immutable receipt는 `Saved/ImportReports/MonsterVFX_20261008/MainDelivery/Delivered.json` SHA12f3af9d…이다. 기존 Player alias·PDB는 보존돼 있다. Root가 해당 성공 build·Main Source101·Config5/DAS203·module manifest·private98/d195를 exact hash로 확인하고 `Resume_20261010/ExternalMonsterRebase/ExternalNativeRebase_RootAccepted_20261011.json` SHAe0e4eb60…에 결속했다. 이 재개에서 Source/native/modules 쓰기0이며 과거 Player Source를 Main 위에 덮어쓰지 않았다.

현행 표현 생성은 외부 공유 factory `UKZAnimNotify_CombatEffect::SpawnComponent`에 이관됐고, ActionAbility는 동일하게 sampled source-local 값을 component에서 복원해 최초 pose callback을 Activate 전에 연결한다. source random을 다시 뽑지 않는다. world/top-owner9 해석과 attached13의 첫 bone-finalized 보정·기존 자원별 cancel/end cleanup을 유지한다. `EnsureIsComplete` 보완은 WITH_EDITOR의 decal material 자원에만 있었다. PSC Activate 전에도 같은 API가 있었다는 이전 독립 검토 문구는 잘못됐으며 실제 old/new PSC 경로에 그런 호출은 없다. 새 runtime class/helper/상태 사본을 이 작업에서 추가하지 않았다.

최신 Effects 의존성461개와 외부 WPO1의 private 동기화는 Art continuity의 실제 receipt를 따른다. Private12는 preserved Source98/d195에서 실제 RHI18+Brutal5 passed/PID4828/155.920535초/exit0, FirstPose13/13 잔차0, Saved12 Art18/8몽타주401 검사를 통과했다. 이는 예비 Art 회귀 증거이며 최신 Main Source101 runtime 통과를 대신하지 않는다.

Root가 선택 Art6만 Main에 반영한 receipt `MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/FollowupDelivered.json` SHA1b0693eb…는 FreshMainValidationPending이다. 현재 숨김 `ResumeSavedMain02`가 진행 중이고 이후 `ResumeMainFinal02` current b84 RHI18+5/first-pose/Input13/Root PNG 검사와 별도 V5 finalize가 남아 있다. 사용자/외부 에디터 제어0이며 B 입력·맵·Definition 등 다른 작업은 보존한다. 최종 완료로 보고하거나 과거 original14 helper를 finalize하지 않는다.

## 2026-10-11 — ARCH-83 Player VFX polish 최신 Main 실행 검증 완료

[Art-only 완료 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json)의6개 머테리얼 후속 전달과 최신 Main Source101/b84 actual RHI18+Brutal5·FirstPose13·Saved401/Art18·Input13 보존 검사를 완료했다. Source/native/modules 쓰기0이며 외부 Monster Build19/Source11 migration 및 기존 Player alias를 보존했다. Private98/d195는 예비 Art 회귀 증거, fresh Main02가 현재 실행 증거다. shared factory의 동일 sampled-local 복원과 일회 pose callback/cleanup을 확인했고 새 runtime 구조는 추가하지 않았다. 현재 코드/검증과 decal-only EnsureIsComplete 정정은 [VFX runtime 정본](PLAYER_ATTACK_VFX_RUNTIME_20261008.md)의 같은 날짜 추가 절을 따른다. 원작 shader/pixel/Shipping 성능 한계는 Art 정본에 기록했다. 사용자/외부 에디터 제어0.

후속은 이번 completed receipt/actual02를 재사용하되 당시 이후 current manifest/Source 차이를 먼저 확인한다. Art 품질 보정은 해당 도메인 최신 continuity를 읽고, 과거 native/alias/old14 전달을 복원하지 않는다.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — ARCH-86 GiantFall runtime 검증 재개 체크포인트

- 정확한 작업 사본: `C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan`. Main Source/Content는 이 작업에서 아직 전달하지 않았다. 다른 작업의 최신 Main MonsterVFX/Player VFX 소스와 사망 presentation 필드·에셋을 Work에 병합했으며 Main module alias를 되돌리지 않는다.
- 새 runtime는 PatternAbility/FallAbility/SkillObject h/cpp 6개. 기존 StateTree/AI/ComboDefinition/ComboAction/ASC/CMC를 재사용한다. 구현 설명: [APES_YETUGA_FALL_IMPLEMENTATION_20261011.md](APES_YETUGA_FALL_IMPLEMENTATION_20261011.md).
- WorkBuild09/10/11 성공. Author01–04 저장 성공. 첫 RHI PrivatePIE02는 낙하/착지, 실제 gamepad X 낙하공격/착지/release 지속, 지상 X/브루탈 B, spawned Apes/Yetuga Sight→Roar→ST Attack 관측 성공. **배치된 giant의 빈 per-instance CombatPatterns로 count=0, 전체 test는 Fail**. Author03 이후 배치 설정 갱신. 최초 PrivatePIE01은 Python EditorPerformanceSettings API 오류로 PIE 자체가 시작되지 않았고 그 자체 소유 PID만 종료했다.
- 현재 WorkBuild12 실행 중. 마지막 source 추가는 다른 스킬 쿨다운(+15/+20 원본), Ice Step8 파괴/폭발, 오브젝트 source-run 소유 등록. Targeted extractor로 공통 curve 2개를 확보하여 MoveCurveMissing 20건을 해소했다. 19개 native 미지원 기록은 계획 JSON에 남으며 사용자 적 stamina 규칙 override를 원작 구현 누락과 구분해야 한다.
- 재개 순서: Build12 결과 확인 → 실패면 해당 compile 오류만 수정 → 최신 plan으로 owned NullRHI `Khazan.GiantFall.Author`(Author05) → 새 owned RHI native `Khazan.GiantFall.PIE`(다음 PrivatePIE03). PIE driver는 `Scripts/Engineering/giant_fall_pie_20261011.py`; Python은 editor lifecycle만, 입력/이동은 native fixture. 기존 로그/PIEResult를 번호별 보존하고 이전 성공을 최신 검증으로 재사용하지 않는다.
- native 추가 검증 7개: NormalAtk02 near/far 후속, Yetuga Dempsey 마지막 window 안/밖 accepted parry, Apes FastMove 실제 이동/후속, Yetuga rock 발사, Ice child field, CloseGrab 실제 collision→capture→cancel cleanup. 테스트 전용 review camera PNG를 확인한다. 전체 test 통과 후 필요한 회귀/에셋 cold readback 및 Main latest-hash CAS/backup/소스 병합/별도 module build로 전달한다.
- Main 전달 시 `KZActionAbility`, CombatEffect/MonsterVisual/Death, 최신 CharacterDefinition의 DeathPresentationMontage, 물약/브루탈 B/12-roster 및 타 작업 Art6 변경을 보존한다. Work 전체 Source/Content 복사는 금지한다. 새 Main background editor만 사용하며 외부 프로세스를 제어하지 않는다.

## 2026-10-11 03:08 KST — ARCH-86 Main 파일 반영, 최종 빌드·PIE 진행 중

- Main에 소유 Source20(기존13+새 runtime h/cpp6+native test1), Content151, 도구/증거를 포함한 선택237개를 CAS 후 반영했다. 백업은 `Saved/GiantFallBackup_20261011/20261011_030609`, 전달 receipt는 `Metadata/GiantCombatFall_20261011/DeliveryReceipt.json`이다. 이 기록 시점의 상태는 `DeliveredNeedsFreshMainBuildAndReadback`이며 완료로 해석하지 않는다.
- WorkBuild18 성공. Author08 성공. PrivatePIE08는 낙하/착지, 실제 controller X/release 낙하공격/착지, 지상 X/브루탈 B, 두 giant의 실제 Sight→Roar→StateTree 공격 및 개별8사례를 모두 통과했다. 8사례는 Apes Normal02 near/far, Yetuga Dempsey 마지막 패링 창, Apes FastMove 실제 이동, Apes/Yetuga 돌 발사·실제 비행, Yetuga Ice 장판의 바닥 배치, CloseGrab 적중·취소/자원 해제다.
- Cold SavedAudit04는 asset150+DevMap, 노드48/81·일반 후보10/28·쿨다운 전용9/6·GA19/24·부여/분기/사용자 Brutal50·기존 DeathPresentation 참조·12마리 배치·플랫폼/Start를 통과했다. 첫 saved audit에서 Work의 기존 DA 두 개에 최신 DeathPresentation이 누락된 것이 확인돼, Main 최신 두 Definition을 가져온 뒤 own author만 재적용했다. 초기 null 보존 주장은 이 검사 결과로 대체한다.
- 중간 실패 원인은 Montage local float 시작 경계 재검사에 의한 Apes Spawn 누락, Yetuga pickup/throw 두 단계의 잘못된 자동 생성 연결, 현재 손 pose가 바닥 아래일 때 floor trace 실패였다. 일치 Notify의 중복 시간 조건 제거, pickup Spawn/다음 단계의 명시 Use, capsule 위에서 floor trace로 수정했다. Yetuga pickup의 생략된 native enum 기본값 Spawn 해석은 원본 CDO 미확보에 따른 추론이다. 같은 시각 source 이벤트는 한 UE branching marker로 묶어 조건/행동은 모두 유지했다.
- Rider LLDB에 소유 Work PID만 attach했으나 Work source 중단점 bind 불가·스택 unknown·값 없음으로 실제 debugger 근거를 얻지 못했다. 만든 agent breakpoint2는 삭제했고 user breakpoint8 변경0. 소유 attach session을 종료한 뒤 실패 지점을 source/실행 로그/저장 검사로 확인했다. 외부 에디터 제어0.
- 재개: `MainBuild01.log`와 현재 module manifest부터 확인한다. Main build는 `-NoHotReloadFromIDE -ModuleWithSuffix=Khazan,20261011 -MaxParallelActions=2`로 시작했다. 성공 후 별도 hidden Main editor/NoLiveCoding/NoAutoSave/RiderLink·MCP disabled에서 `giant_fall_saved_audit_20261011.py`를 읽기 전용 실행 → 같은 별도 RHI editor에서 `giant_fall_pie_20261011.py`, 로그는 MainPIE.log → fresh module/path/PIE8/saved/hash 보존 확인 → 구현/Architecture/Engineering 및 Art 문서 하단에 실제 완료 결과를 추가한다. Work author wrapper·방대한 editor Build.cs 의존성은 Main으로 복사하지 않았다.

## 2026-10-11 — ARCH-86 Main 최종 실행 검사 종료 / 원작 동일성 후속 경계

- `Metadata/GiantCombatFall_20261011/FinalVerification.json` 및 `DeliveryReceipt.json`은 MainDeliveredAndFreshVerified. MainBuild02 성공, 새 Main DLL 실제 로드의 saved150+map 검사 성공, MainPIE 실제 RHI 전체8사례 및 낙하/착지/실제 X/release/두 giant 자율 StateTree 공격 성공이다. Source21(runtime19+DEV1+editor Json rule1), Content151이다. 해시 제품176/보호 Source84/VFX Content965 불일치0. 검사 프로세스 정상 종료, 외부 에디터 제어0이다.
- current module `UnrealEditor-Khazan-20261011.dll`, 백업 `Saved/GiantFallBackup_20261011/20261011_030609`(native before build 포함). MainBuild01은 native test의 Json 링크 의존성 부족으로 실패했고 editor-only Json 한 줄 추가 후 MainBuild02 성공했다. WorkBuild18/Author08/PrivatePIE08/SavedAudit04는 예비 증거이며 실제 Main 결과와 구분한다.
- 현재 동작/타입·함수·원본/임시 수치·검증/테스트는 [구현 문서의 마지막 절](APES_YETUGA_FALL_IMPLEMENTATION_20261011.md)을 따른다. Main 파일 전달/실행 검사는 끝났지만 **원작 전체 native BT와 완전히 동일한 구현이라는 목표까지 완료 확인한 것은 아니다**. 일부 Yetuga MoveTo→NoCool/선택 substep/fallback은 공통 Chase/평탄화 후보로 대체되며 원작 grab/MoveTo/RNG/BlendAlpha/native Spell·camera, Apes level bindings·누락 projectile model은 확인/추가 구현 경계다. 패링 API 후속은 검증했고 새 perfect-guard 입력 판정은 구현 범위 밖이다.
- 정확한 동일성 후속 재개: Router→Architecture ARCH-86→이 구현 문서 마지막 절→`Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/BehaviorTreeResolved.txt`와 AIContractSummary의 전용 Sequence/SelectedSkillSubStateSteps→현행 AIController/StateTreeTask/ComboDefinition을 대조한다. 이미 구현된129노드와 새 six runtime 파일을 재생성하거나 전체 import/retime하지 않는다. 전용 MoveTo/후속 선택에 실제 필요한 기존 타입의 작은 확장부터 적용하며 새 만능 Manager를 선행 생성하지 않는다. native 기본값/단위는 exact 추가 metadata·원작 영상/실측으로 확인해 현재 추론/임시 어댑터와 구분한다.


## 2026-10-11 — HeinMach 후처리 제거 및 공격 이펙트 재검토 착수

최신 사용자 요청은 기존 룩을 유지하는 보정이 아니라 HeinMach의 모든 authored 후처리·툰/외곽선 제거를 먼저 진행하는 것이다. 이전 Player VFX 완료의 표본은 차지 시작의 굴절 사각 경계 및 OverFury 종료의 VAT 큐브를 충분히 포함하지 않았다. 새 actual RHI에서 두 문제를 재현했고 과거 품질 통과를 이 구간에 확대하지 않는다. 혈액 증량은 데칼 추가가 아닌 분출/비산 파티클을 뜻한다.

`Saved/ImportReports/HeinMachCleanPresentation_20261011`가 새 작업 증거 루트다. PPAudit01: 저장 world `/Game/Maps/L_HeinMach_Environment`, actor9869, active PP8, PostProcessComponent0, 초기 dirty0. PPRemove01은 PP8 및 연결된 지역 룩/툰/외곽선만 삭제하여 actor9861을 저장했고 비PP 전체 actor pose/class 및 mesh/material/light/fog/weather component 설정을 동일하게 확인했다. map SHA `57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7` → `0c887cad2110c867724e1b90b9c0404d4229d18ecadd7c32235b2358b644220d`; 원본은 PPRemove01/Before_L_HeinMach_Environment.umap에 있다. PPColdReadback01은 새 프로세스에서 PP0/component0/actor9861을 확인했다. Sky/Fog/fire/snow/terrain 설정은 유지했다. 엔진 화면 출력 변환·AA와 authored 룩을 구분하며 모든 렌더 연산을 중지했다고 주장하지 않는다.

VFXBaseline01은 현재 Main native의 실제 Ability/Notify18+Brutal5 Success, material fallback0, 354 PNG를 남겼다. 011 Charge에서 큰 반투명 사각 평면, 222/224 OverFury에서 우측 혈액 VAT 삼각형 큐브를 확인했다. `P_kazan_charge_start` slot3의 FM_RefractionShock_01은 현재 ParticleColor RGB/A만 출력하고 Refraction consumer가 누락됐다. Fatalblood slash의 MI_BloodVAT4_1 → M_BloodVAT에는 original MF_VAT_DynamicRemeshing consumer/WPO가 없었다. 원본 VAT tex/mesh/DP Param1 1→90 및 MI manual playback·legacy bounds는 저장된 CombatEffects_20261006 metadata/Precision에서 재사용한다. SideFX 공식 VAT3 decoder 자료는 Saved-only로 받아 git blob/hash를 결속했고 원작 stripped graph 자체와 구분한다. 새 함수가 필요하면 실제 VAT 소비자만 /Game에 복제하고 런타임 플러그인을 추가하지 않는다.

현재 효과 수정은 author/검증 진행 중이다. ChargeVATRepair01은 plugin source duplicate lookup 실패로 save0 종료했고 현재 저장 에셋 수정 증거가 아니다. ChargeVATRepair02는 직접 로드된 function duplicate 방식으로 재시도한다. 후속은 해당 Applied/Exit와 실제 saved hashes 확인 → 차지/OverFury/혈액 mask 보정 및 fresh RHI 화면 → 몬스터 실제 사용 animation의 root-motion flag 감사/수정 → 몬스터 Camera 응답 Ignore → 빌드·cold readback/HeinMach·DevMap 실제 검증이다. 다른 작업 Source/native/DevMap/몬스터 구현을 구버전으로 되돌리지 않는다. Root-motion track repair와 단순 enable flag는 구분한다. 사용자/Rider/타 작업 editor 제어0, 새 hidden task editor만 사용한다.

<!-- HeinMachCleanPresentation_20261011_PPRemoved -->

## 2026-10-11 — CombatPresentationFix 작업 중간 재개 지점

최신 사용자 요청은 낙하 내려치기 완결, 브루탈 거리/각도와 관통 방지, 몬스터 혈흔/피격과 DAS VFX 증량, HeinMach 눈 40cm·파임 확대 및 색감/그림자 개선이다. 최신 Main을 `Khazan_GiantFallWork_20261011/Khazan` 소유 복사본으로 재동기화했다. Main의 clean presentation/Camera Ignore/노출 보정/PP 제거/원작 notify 창을 보존한다. 이번 게임 파일은 아직 Main에 전달하지 않았다. 모든 Source/Config/Content 전 상태는 `Metadata/CombatPresentationFix_20261011/Baseline.json`에 저장했다.

확인된 낙하 원인은 이미 5.7666669초로 재생률을 베이크한 InGame 시퀀스에 원본 2.7333333초 구간/rate를 다시 적용한 montage다. 저장된 `Metadata/InGamePlayback_20261002/PlaybackPlan.json`의 inverse_map을 재사용하여 Start/Loop/Land를 현재 시간축으로 변환했다. 원시 시퀀스/Player scale .01은 수정하지 않았다. Work의 AuthorFall 성공, 실제 CMC 낙하/X/착지 후 Land 3.7417676→5.7666669 끝 구간 재생을 NativeAfter02에서 확인했다.

브루탈은 정렬 뒤 두 montage의 root travel, 소진 Start의 잔여 이동과 blend-out이 간격을 무너뜨린다. Work의 플레이어 Brutal/몬스터 Exhaustion이 기존 HitReaction과 같은 방식으로 AnimInstance root mode의 소유/이전값 복구를 갖도록 작은 수정했다. NativeAfter02에서 인간4종·Yetuga 정/후면 간격은 유지, Apes 후면은 7.77cm 부족했다. UpdateAlignment가 claim 전 위치가 아니라 live victim을 기준으로 목적지를 갱신하도록 보완했다. QA의 이전 root mode 비교도 실제 시작값을 기록하도록 고쳤다(플레이어 mode를 몬스터와 같다고 하드코딩한 QA 오류). 마지막 성공 빌드는 WorkBuild07이며 이후 소스 수정은 아직 빌드 전이다.

재개 절차: `Metadata/CombatPresentationFix_20261011/HeinMachBefore01` 소유 에디터 Launch/Exit를 먼저 확인한다. 종료 후 Work의 private `Scripts/Engineering/CombatPresentationEditor.cpp` VFX author와 runtime 수정 빌드 → NativeAfter03(기존 Native 결과는 실행 전에 별도 복사) → 눈 author/실제 Snow.PIE, VFX 실제 PIE/RHI, 조명 동일 카메라 전후 비교 → Main 파일별 기존 SHA 대조 및 백업 후 whitelist 전달/새 native 빌드/검증 순서다. private heavy Build.cs/author wrapper는 Main에 전달하지 않는다. 외부 에디터·Rider·사용자 breakpoints는 제어하지 않는다.

Art 쪽 진행/실패/수치 출처는 Art continuity에 별도로 기록한다. 완료 시 본 중간 절 뒤에 최종 증거를 추가한다.


## 2026-10-11 04:35 KST — clean presentation Engineering 적용 및 최종 확인 중

기존 AKZMonster ctor의 Capsule/Mesh, BeginPlay의 실제 UPrimitiveComponent 전체에 Camera channel Ignore만 적용했다. source1파일/새 runtime file0, Pawn·Visibility·World collision 및 SpringArm probe는 유지한다. MainBuild02 source snapshot 불변/exit0, 현재 alias는 UnrealEditor-Khazan-2026101101.dll이다. FinalVFXPIE02의 실제12monster 전체 component Camera Ignore, player camera authored override0, native18+Brutal5 Success를 확인했다. FinalVFXPIE01은 CollisionResponseType 이름을 QA가 잘못 비교한 harness 오류이지 runtime collision 실패가 아니다.

MonsterAnimationAudit02는 /Game/Bluprints 전체 중 실제 KZMonster subclass7(legacy TEST 포함)의 hard/soft package closure1380에서 사용 AnimSequence238·ABP6을 확인했고 disabled root-motion0이다. 전부 이미 enabled였으므로 animation/root data 재임포트/flag 일괄 덮어쓰기는 하지 않았다. RootMotionFromMontagesOnly/force-root-lock/rate/length를 유지하며 모든 sequence flag on을 RootMotionFromEverything 또는 root-track displacement 검증으로 혼동하지 않는다.

Config는 최종 장면 기본 metering을 유지하고 Effects128 emissive에서 native inverse로 보정한다. AutoExposure=False trial은 실제 HeinMach snow clipping 때문에 철회했다. source C++/Combo/Notify timing/Ability lifetime은 추가 변경하지 않았다. 최종 남은 확인과 정확한 재개 명령은 Art continuity의 동일 시간 절과 Saved/ImportReports/HeinMachCleanPresentation_20261011을 따른다. FinalVFXPIE03은 현재 진행 중이며 full original shader/pixel parity·Shipping 성능 완료를 기록하지 않는다.

<!-- HeinMachCleanPresentation_20261011_Exposure128PendingFinal -->

## 2026-10-11 — HeinMach clean presentation: 카메라·루트모션 검증 완료

기존 AKZMonster ctor의 Capsule/Mesh 및 BeginPlay의 실제 UPrimitiveComponent 전체에 ECC_Camera=Ignore를 적용했다. Blueprint collision profile/modular parts 초기화 뒤에도 유지하며 Pawn/Visibility/World 응답과 SpringArm probe는 변경하지 않는다. 작성자/소비자는 기존 Monster 초기화/기존 SpringArm이고 game thread의 Pawn 수명에 묶여 새 상태/handle/cleanup/Ability 수명은 필요 없다. Source1파일, 새 runtime 파일0이며 ARCH-83/v2의 효과 생성·실행/취소·피해 책임은 유지했다. 현재 KZActionAbility/Combo/Notify timing은 이번 작업에서 편집하지 않았다.

MainBuild02 성공/입력 해시 불변, 현재 Main 모듈 UnrealEditor-Khazan-2026101101.dll. 실제 FinalVFXPIE03 native18+Brutal5 Success/compile·fallback0/save0이며12마리 모든 PrimitiveComponent Camera Ignore를 확인했다. 기존 GiantCombatFall/MonsterVFX/Player alias 및 gameplay 구현 위에서 빌드했으며 옛 private native alias로 되돌리지 않았다.

MonsterAnimationAudit02의 BP7/hard·soft closure1380에 연결된 사용 AnimSequence238은 전부 이미 root motion enabled, disabled0이었다. animation write0, ABP6의 RootMotionFromMontagesOnly/force-lock/rate/length는 유지했다. RootMotionFromEverything 전환이나 root displacement repair를 한 것으로 표기하지 않는다.

Art의 PP8 제거/nonPP9861 유지, exposure128, 차지/OverFury/혈액 교정·원본/TEMP 수치와 검증 범위는 [Art 정본](../Art/HEINMACH_CLEAN_PRESENTATION_20261011.md)에 분리했다. Engine 기본 exposure/HDR/AA/Fog는 유지하며 프로젝트 Bloom/MotionBlur/LensFlare/LocalExposure 기본값은 Art 요청을 위해 조정했다. [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json), [정확한 Source/Config diff](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/OwnSourceChanges.patch)가 최신 적용 증거다.


앞선 Exposure128PendingFinal의 진행 상태는 최종 focused charge RHI/BloodBakedRate01/FinalAssetReadback02/HeinMachRHI03의 완료 증거로 보충했다. 필수 잔여 작업은 없다. 후속 재개는 현재 Main source와 Completion hash를 먼저 대조하고 Art 정본의 고유 run/explicit canonical map 절차를 따른다. 사용자 Rider/외부 editor 제어0이며 작업 background editor 모두 종료했다. 원작 shader/pixel·Shipping 성능은 미확인으로 남긴다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](../Art/HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->


## 2026-10-11 ? Combat UI ARCH-87 ?? / Main ?? ??

?? Main Source? UKZCombatHUDWidget h/cpp2 + Controller h/cpp + LockOn getter h/cpp + Monster UI ?? h + Brutal FindBrutalTarget? eligible locked ?? + Build UMG/Slate? ????. ? DEV ??? Tests/KZCombatUIPIEEditor.cpp?. Baseline? Metadata/CombatUI_20261011/Baseline.json/byte backup??, Build02 ????. warning ??? FVector2D ???? ?? ???? ?? build? ????. ?? ???15/UI??? material2? Main Content/UI/Combat?? ImportEditor01 exit0/Import01.json? ????.

ConfigureEditor01/02? Python ??? API get_mesh/get_bone_names ??? ???? ?? BP ?? ?? ????. get_editor_property(Mesh)/get_num_bones/get_bone_name? ?? ConfigureEditor03? ?? ???. ?? ??? ?? Exit/SavedReadback/Editor.log ?? ?? ? ?? ??? ?? ? ? ?? run?? configure ? stock build ? combat_ui_owned_editor_20261011.py PIEEditorNN Scripts/Engineering/combat_ui_pie_20261011.py rhi?. ?? editor ??/PIE/??? ?? ???. ?? ????/??? ? Launch.json??.

??? MonsterVFX/GiantFall/PlayerVFXPolish/HeinMachCleanPresentation Main receipt4?? BackgroundMainAudit01.json? ???? ?? whole worktree? ????? ???. CombatPresentationFix_20261011? ?? ??? ?? ?? ??? ?? verified delivery? ??. ? ??? Brutal alignment ??? ??? ? ARCH-87? FindBrutalTarget/LockOn include ? Monster UI ??? ???? ??? ?? merge? ???? ??. ?? UI ??? RHI/?? ??? ?? ????.
## 2026-10-11 — Combat UI 전체 통과 / 미전달 후속 작업 재개

ARCH-87 UI는 Main Build06 및 `Metadata/CombatUI_20261011/PIEEditor03` 전체 실제 RHI 검사에 통과했다. Exit0, 실제 HUD class는 `/Game/UI/Combat/WBP_CombatHUD.WBP_CombatHUD_C`다. ASC 양방향 보간, TargetPoint 록온, 실제 B 적격 판정/Ability 실행, lethal 감소·소멸, Max0, UnPossess/RePossess를 확인했다. 직전 일부 중간 기록의 문자 인코딩 손상은 이 UTF-8 추가 기록과 UI 정본으로 보충하며 기존 기록은 보존한다.

완료 receipt가 있는 기존 MonsterVFX/GiantFall/PlayerVFXPolish/HeinMachCleanPresentation은 이미 Main이다. 유일한 미전달 CombatPresentationFix를 채택해 재개했다. WorkBuild08은 실제로 link/완료 전 중단되어 NativeResume03이 이전 DLL을 검증한 실패였다. Private author의 C4456/TObjectPtr loop 오류를 최소 수정하고 WorkBuildResume10/11을 성공시켰다. 원본 혈흔의 첫 emitter는 sprite가 아니므로 첫 index 가정을 실제 material/type 기반 선택으로 수정했다. Main 소스는 아직 전달 전이며 `MainResume/SourcePlan.json`에 8개 선택 파일을 staging했다. Brutal locked-target 선택을 보존한 함수 병합이며 private heavy Build.cs/author wrapper는 제외한다.

SnowAuthorResume01은 Private에서 material2/map만 저장해 사용자 눈 최대40cm·발35cm·weapon substrate cap, 기존 해석 padding15cm 및 profile2를 적용했다. PP0/actor9861/모든 actor transform을 보존했다. Sun5000/Sky1.1은 어시스턴트 임시 표시 튜닝이다. 다음은 VFXAuthorResume02 완료 확인 → 새 DLL의 NativeResume04 12 paired cases → snow 실제 RHI와 동일 카메라 전후 확인 → baseline SHA/byte backup/선택 전달 → Main stock build/새 PIE/UI 회귀 검사다. 모든 에디터는 이번 작업이 새로 시작한 hidden 프로세스이며 외부 에디터는 제어하지 않는다.
## 2026-10-11 — 후속 Main 27파일 반영 / 새 프로세스 검증 진행

Private NativeResume04는 최신 WorkBuildResume12 DLL로 실제 낙하 완결과 몬스터6종 전후방 브루탈12사례에 통과했다. 모든 minimum capsule spacing은 각 실제 capsule 합과 같고 player/victim 이전 root mode 복구를 확인했다. NativeResume03은 완료되지 않은 WorkBuild08의 이전 DLL 검사였으므로 최신 source 실패로 해석하지 않는다.

Main에 Source8/Content19를 선택 전달했고 기존 ARCH-87 UI 파일36개와 locked target 선택을 보존했다. 새 runtime 파일0/private author wrapper·heavy Build.cs 전달0/old native binary 복사0이다. MainBuild01은 stock canonical DLL 빌드 성공, MainSavedResume01은 저장된 UI·VFX14·snow profile2/40cm/PP0/9861 actor의 새 read-only 확인 성공이다. backup `Saved/CombatPresentationMainBackup_20261011/20261011_114106`, 정확한 파일 해시/수정은 `MainResume/{DeliveryReceipt,SourcePlan,AssetPlan,UIProtected}.json`을 따른다.

현재 MainNativeResume01에서 새 Main DLL의 낙하/paired12 회귀 검사를 수행한다. 재개 시 해당 Launch/Exit/PIEDriver를 먼저 확인하고 중복 실행하지 않는다. 다음은 Main UI regression → Snow.PIE → CombatEffect 실제18+Brutal5 및 동일 카메라 HeinMach after → FinalVerification/docs 완료 기록이다. 다른 editor/Rider/process를 제어하거나 기존 author 증량을 반복 실행하지 않는다.
## 2026-10-11 — Main UI·Snow 실제 완료 / 마지막 VFX observer 재검사

UI 최종 `PIEEditor05_FinalShader`는 전체 기능/Shader fallback0/Exit0에 통과했다. 앞선 기능 검사에서 누락된 BrutalRing mask default-pin 두 연결을 후속 RHI 검사에서 발견해 수정했고, Native UI driver도 fallback을 실패로 검사한다. UI37 파일/current DLL 해시는 `CombatUI_20261011/FinalVerification.json`이다. Source 또는 gameplay 수치 변경은 없다.

Snow 첫 MainSnowResume01은 startup이 DevMap을 다시 열어 owner가 없었으므로 native driver에서 canonical map을 직접 load/verify하도록 수정했다. MainSnowResume02는 GPU40cm/발 목표35cm(측정34cm, 기존 GPU 표본 허용오차 내)를 통과했으나 확대된 capsule probe의 +X 지점이 바위에 막혔다. Source의 기존 DEV fixture만 노출된 네 radial axis 중 하나를 선택하도록 보완했고 gameplay는 바꾸지 않았다. MainBuild02 성공 후 MainSnowResume03 전체 Success/Exit0: 실제 capsule 범위/바깥0/달리기·회피·공격·공중·몬스터4종 접촉을 확인했다. 기존 SnowQA는 MainResume/SnowQABefore에 보존하고 새 결과는 MainSnowResume03/NativeSnowQA에 복사했다.

MainNativeResume01의 paired12/낙하와 MainSavedResume01의 새 readback도 통과했다. MainVFXResume01은 native18+Brutal5 Success/383 PNG이나 UI 링 fallback 때문에 전체 observer가 실패했고 원인은 위 UI 수정으로 해소했다. MainHeinMachAfterResume01은 동일 카메라3/PP0/actor9861/save0/Exit0 확인을 완료했다. 현재 마지막 MainVFXResume02 실행의 Driver/Exit를 확인한 뒤 MainResume FinalVerification과 state/knowledge/router 완료 절을 추가한다. 증량 author를 다시 실행하지 않는다. 파일27/보호 UI36의 의도된 후속 변경은 DEV Snow fixture1 및 UI ring1뿐이며 receipt에 분리 기록했다.
## 2026-10-11 — Main 통합·UI 최종 종료 / 필수 잔여 없음

MainVFXResume02도 native18+Brutal5 Success/392 PNG/material fallback0/Exit0으로 완료됐다. 직전 pending은 해소됐고 `Metadata/CombatPresentationFix_20261011/MainResume/FinalVerification.json` 및 `Metadata/CombatUI_20261011/FinalVerification.json` 모두 MainDeliveredAndFreshVerified다. MainBuild02/current canonical DLL/Source·Content final SHA/backup과 paired12/Snow/UI/saved/환경 검사를 결속했다. 모든 owned editor 종료/다른 editor·Rider 제어0이다.

추가 사용자 요청에서 재개할 때는 Router→최신 Architecture/Migration→UI 또는 후속 정본/이 receipt→현재 Source 순으로 확인한다. author 증량·원본 sequence 재임포트·전체 private 복사·예전 alias 복원은 하지 않는다. original shader/native/pixel/frame·멀티플레이·Shipping 미검증은 후속 과제로 남으며 이번 요청의 미완료 필수 작업을 뜻하지 않는다.

## 2026-10-11 21:38 KST — KZFallAbility 첨부 기준 중단 위치 재확인

사용자의 중단 위치 재개 요청을 받아 Main의 최신 Architecture/Migration/후속 정본·continuity와 첨부된 GiantFallWork의 실제 KZFallAbility.h/.cpp를 대조했다. 확인된 과거 중단은 `Metadata/CombatPresentationFix_20261011/WorkBuild08.log`가 최종 link/result 전에 끝난 지점이다. NativeResume03은 이전 DLL을 사용했으며, 이후 WorkBuildResume12 성공과 Main 전달·검증 완료 기록이 이미 존재한다. 이번 확인을 새 구현·빌드·PIE 완료로 기록하지 않는다.

현재 Main 후속 선택27파일/최종 proof6개/UI ring 수정1개 및 module manifest가 선택한 canonical DLL의 SHA가 FinalVerification과 모두 일치한다. 첨부된 Work의 Fall h/cpp도 Main과 각각 동일하다. 낙하·착지와 paired12의 기존 MainNativeResume01 Driver는 passed이며 proof SHA도 일치한다. 기록은 [ResumeAudit_20261011_213824.json](../../Metadata/CombatPresentationFix_20261011/MainResume/ResumeAudit_20261011_213824.json)이다. 이번 실제 변경은 이 재확인 보고서와 Engineering continuity 추가뿐이며 게임 Source/BP/asset 변경 및 새 제안0이다.

필수 잔여 작업은 없다. GiantFallWork의 복사된 문서는 Main 완료 이전 기록이므로 그 중간 pending을 현행 완료 상태로 대체해 읽는다. 정확한 후속 재개는 Router→현재 Main Architecture/Migration→COMBAT_PRESENTATION_FOLLOWUP_20261011.md/FinalVerification→현재 Main Source 순서다. 기존 author 증량·전체 private 전달·구 DLL 복원을 반복하지 않는다. 원작 전체 동등성/Shipping 성능은 기존 미확인 범위로 유지한다.

## 2026-10-11 — ARCH-88 Monster 표현·UI 전면 재검사 착수

새 사용자 직접 수정 범위는 Architecture ARCH-88이다. 기존 완료 기록은 당시 표본/기능 검증이고 이번 위치·방향·alpha 품질의 합격 근거로 재사용하지 않는다. 원작 Monster PreparedPlaybackPlan의 Attack198 assets/1577 occurrence와 실제 Source를 대조 중이다. UI TargetPoint가 Capsule에 부착되고 전체 resource fill이 .35초 표시 보간을 쓰는 현행 원인을 확인했다. Monster CurBar의 원작 Background alpha0과 별도 BG material을 확인했으며 현재 source의 opaque crimson rectangle과 구분한다.

다음은 `Scripts/Engineering/stage_monster_presentation_repair_20261011.py`로 Main baseline/Work Source backup 및 private snapshot → 표적 asset/socket/material/particle probe → 기존 owner의 작은 diff → 새 DLL/RHI 전 공격 위치·방향 검사와 hit/death/UI 품질 검사 → 최신 Main CAS/선택 전달/메인 build·fresh 검증이다. Metadata/MonsterPresentationRepair_20261011의 Stage/Baseline부터 실제 단계 확인 후 이어간다. Main의 별도 BrutalAlphaMainPIE editor는 외부 task이므로 종료/조작하지 않는다. 현재 게임 파일의 새 Main 적용은 아직 없다.

## 2026-10-11 — 사운드 실제 재생 Mixed 요청: 실행 구조 조사 중

FModel 사운드 추출·임포트와 Player/Monster 행동·상호작용/HeinMach 환경음 실제 재생 요청이다. Router→Architecture 최신 ARCH-83/84/85/86와 Migration→현재 Source를 확인 중이다. 기존 Source에 Sound/PlaySound/AudioComponent 경로가 발견되지 않았고 runtime 수정은 아직0이다. ActionAbility의 실행/취소·확정 hit, Monster actual anim context/Death, 엔진 audio/component/notify 수명을 먼저 재사용하며 새 만능 AudioManager/FSM/MainAnimInstance 상태 사본을 만들지 않는다.

원작 AkEvent/음원/수치 조사 상태와 exact extraction resume는 Docs/Art/ART_WORK_CONTINUITY.md의 같은 작업 절을 따른다. 현재 Main module UnrealEditor-Khazan-2026101101.dll과 기존 source/asset을 보존한다. 현재 준비 단계이며 build/PIE/audio 검증 완료가 아니다. 사용자 Rider 에디터 제어 없이 task-owned hidden process만 사용한다.

<!-- GameplayAudio_20261011_DiscoveryCheckpoint -->

## 2026-10-11 — ARCH-88 전수 RHI 실패와 수정 checkpoint

private Build07/08/09까지 성공했다. native ParticleAuthor02는5 skeleton UI_Chest와 hit blood/ash2개, 실제 FM_MeshDecal/FS_Blood_box 기반 기존16 PS의 floor receiver16개만 변경했다. 최초56 PS/mesh emitter105개 제거는 범위가 넓어 전체를 unchanged Main에서 private로 복구한 뒤 좁혀 재저작했으며 Main 반영0이다. MaterialAuthor05는9 master의 기존 BaseColor RGB/Opacity A output을 보존해 shader를 확장했다. 기존 UI graph 재삭제에서 발생한 UE rooted expression assert는 graph 재사용으로 회피했다. Source9 master/원작노이즈/기존 material parameter baseline0을 보존한다.

SavedAudit02는 새 프로세스로 Attack198/1577 source socket·offset·rotation·scale/attach/window/resource를 대조했고 blood decal state42의 Effect None, socket6종/Corpse master9/UI 원작 gradient 값을 확인했다. package save0이다. AssetSelection.json은 표적59 package만 선택한 준비 상태다.

Runtime01은 새 post-bone-finalize callback의 capture/receipt 주소를 unregister·Spawn 재진입 뒤 사용해 crash했다. captures를 stack local에 복사하고 factory 뒤 receipt를 다시 찾는 Work fix를 적용했다. Runtime02는 crash 없이 Attack198/1577 및 normal/paired completion6을 끝냈지만 **failed**다. 원인은 grayscale 노이즈의 Linear Color sampler로 SM6 shader fallback이 발생하고, pose-step fixture의 backward timeline ensure/일부 비교가 다음 자동 pose update와 겹친 점이다. SamplerRepair01로 Linear Grayscale을 사용하고, fixture에 explicit PreviousTime/mesh 자동 tick 정지,1600x900 floating PIE 요청을 적용했다. Build10 진행 중이며 그 후 Runtime03·CombatUI.PIE·actual-hit 회귀 및 PNG 검토가 필요하다. 현재 Main 게임 파일 반영0, 검증 완료0이다. 기존 사운드 신규 Source6 및 Combo guard/impact2 hunk를 Work에 보존했다.

## 2026-10-11 — ARCH-88 private source 수정·검증 준비 checkpoint

Stage.json은 passed이며 Main Source/Config/Content를 idle GiantFallWork에 복사한 출발11813 hash를 Baseline.json에 보존했다. Probe01은 Python protected Notifies getter로 실패, 공개 AnimationLibrary getter로 바꾼 Probe02는 Attack198/1577 saved event와 socket 누락0을 확인했다. PoseBasis01/CorrectionProbe01·02는 읽기만 수행했다. Halberd correction52의 TM을 현재 bone/시간·수평 basis 후보와 비교했으나 정확한 대응을 찾지 못했다. Root bone이라고 임의 적용하지 않는다.

현재 실제 runtime 수정은 Work의 KZMonster.h/cpp, KZCombatHUDWidget.h/cpp, ComboActionAbility.cpp, BrutalAttackAbility.cpp다. UI는 실제 resource 즉시 갱신/감소 잔상만 보간, CurBar NoDraw background/별도 source gradient, compact Elite124x22 임시 표현, UI_Chest socket projection이다. Monster는 first FX spawn을 bone-finalize 뒤로 이동하고 handle을 cancel/end/EndPlay에 해제한다. accepted hit/Brutal HP50에 finite blood, normal/paired death 완료에 corpse MID progress/black ash/Destroy를 연결했다. 새 runtime class/file0이다.

Build01/02 실패 원인은 private author TObjectPtr auto pointer 추론 및 ACharacter Mesh 이름 shadow이고 해당 코드를 수정했다. Build03 진행 중. MaterialAuthor01은 protected Skeleton.Sockets 접근에서 실패했고 package save0이다. sockets는 public native C++ author로 옮겼다. private author 파일은 Scripts/Engineering/MonsterPresentationRepairEditor.cpp, 기존 KZGiantFallAuthor wrapper의 추가 include다. Main에 전달하지 않는다. 새 actual PIE fixture는 Tests/KZMonsterPresentationRepairPIETest.cpp이며 다음 build에 포함한다.

정확한 재개: Build03 종료/로그 확인 → 새 fixture 포함 private incremental build → owned asset_editor에서 Khazan.MonsterRepair.AuthorParticles → MaterialAuthor02 공개 API shader author → fresh saved readback → owned RHI Khazan.MonsterRepair.PIE/CombatUI.PIE 및 실제 hit 회귀 → PNG 직접 검토/수정 → Main 현재 변경 CAS/작은 hunk 반영/선택 asset만 전달 → Main 새 build/fresh 검증. 이 checkpoint에서 Main 게임 파일 적용0이며 새 PIE 합격을 주장하지 않는다. 별도 Main 작업이 ComboActionAbility.cpp와 manifest를 바꾼 것이 확인됐으므로 현재 Main을 통째 덮어쓰지 않는다.


## 2026-10-11T23:25:56+09:00 — ARCH-89 사운드 runtime 적용·빌드 checkpoint

적용 파일은 Audio Notify/NotifyState h·cpp4(신규 runtime class2), 기존 ComboDefinitionData.h/ComboActionAbility.cpp2와 editor-only KZGameplayAudioEditor.cpp1이다. Build06 exit0이다. 실제 Actor engine AudioComponent, mesh/engine notify ID tag로 loop 취소·clip 교체를 정리하고 finite tail은 자연 종료한다. source stop target cue 목록과 source fade, local/locked guardbreak 조건 및 원본 발소리230 속도 분기의 authored field를 추가했다. 새 Manager/FSM/MainAnimInstance 상태·Tick0이다. 피해/guard sounds는 실제 승인된 window result에서만 소비하고 DataAsset 값은 아직 연결 전이다.

Source/runtime build 완료와 asset/timing/PIE 완료를 구분한다. 현재 NativeImport03 검증 → 표적 author/확정 hit/환경음 → 실 mixer/취소/tail/EndPlay/coverage 검사 → 최신 Source/module/hash receipt가 남았다. art 상태/원본 DSP adapter는 Art continuity를 따른다. 사용자 Rider/foreign editor는 제어하지 않았다. exact evidence/resume는 Saved/ImportReports/GameplayAudio_20261011/ResumeState02.json이다.

## 2026-10-11 — ARCH-88 공격 전수 검사·혈액 실제 입자·동시 사운드 병합 checkpoint

Runtime04는 native assertion에서 Attack198/1577의 finalized socket transform/resource와 사망6종을 통과했다. 그러나 driver는 blank startup grant를 무조건 기대한 fixture 때문에 failed이며 최종 합격으로 기록하지 않는다. 실제 camera location은 requested camera와 동일하고 fallback0이다. bSuppressNotifyEventDispatch로 자동/수동 Notify 중복을 분리하고 deactivated particle tail을 새 active spawn으로 집계하지 않는다. 새 test의 startup 예상 로그는 저장 Definition의 실제 빈 grant 수가 있을 때만 등록하도록 수정했다.

QuickVisual01은 actual live particle를 검사했으며 **blood0 / ash630**로 failed다. 호출만 존재하는 것을 혈액 품질 완료로 취급하지 않는다. Work private native author에 즉시 burst/scale/enabled/delay,192개/1.2s/1.4–3.5cm 임시 튜닝을 추가했고 원작 velocity/gravity/collision/texture를 유지했다. ash는 world XYZ[-60,60],Z[50,100]cm/s·size2–4.5cm 임시 분산을 적용한다. Build16 succeeded, NativeParticleAuthor03 owned PID6220 진행 중이다. Root material9 dissolve는 실제 late image에서 사라지는 진행을 관측했다.

Main 전달 준비 중 동시 사운드 작업이 선택 Animation24개를 갱신한 것을 CAS로 검출했다. Main 게임 변경0을 유지한 채 최신24개를 Work로 옮기고 그 audio reference가 null로 저장되지 않도록 Audio dependencies2078을 함께 읽기 복사했다. ConcurrentAnimationMerge.json과 AnimationMergeBackups에 원본/current/private hash를 보존했다. Source의 Guard/Impact sound hunk도 보존했다. 선택59개 전체를 무조건 덮어쓰지 않는다.

정확한 재개: NativeParticleAuthor03 종료/ParticleAuthor/log에서 원래 burst/lifetime 값을 확인 → MaterialAuthor06으로 최신 animation24개에 혈흔 Effect None만 다시 적용 → SavedAudit03(198/1577/42 plus 새 sound Notify 보존) → QuickVisual02 live blood/ash 및 PNG → UI02/PlayerAttackCollision actual approved hit/miss/dedup blood 회귀 → 최신 CAS Plan 준비 → Main 소스10/asset59만 적용·Main build → Main fresh audit/RHI198·6종/UI/실hit → receipt와 양 도메인 완료 기록. Private wrapper/Build.cs author dependencies는 Main에 전달하지 않는다. Fall 파일은 이번 수정 대상이 아니다.


## 2026-10-12T00:17:33+09:00 — ARCH-89 최소 body hit 계약 UTF-8 보충 / checkpoint

직전 Architecture의 body hit 추가 절은 PowerShell stdin 인코딩으로 일부 문자가 물음표가 되었으므로 이 UTF-8 절로 보충한다. FKZHitReactionSettings의 선택적인 ImpactSound1개는 실제 승인된 HP 피해의 Combo/SkillObject/Brutal 세 소비자가 대상 Definition에서 읽는다. miss/guard/stamina-only는 body hit을 만들지 않는다. 신규 gameplay class/file0·manager/state 사본/tick0이며 source material-name의 현행 family mapping은 native adapter다. 원본 native caller의 동일성은 미확인이다. projectile audio는 기존 SkillObject의 실제 launch/impact/Actor component 수명으로 재생·종료한다.

Build13은 exit0이다. 기존 순수 Audio Notify/NotifyState 두 class/h·cpp4와 현재 owner의 작은 확장, editor-only finalizer 및 DEV PIE test를 적용했다. NativeImport05의 영구 wave 참조 수정은 위 Art checkpoint를 따른다. AudioPIE01 논리 관측 Success와 실제 녹음 peak0을 구분한다. 다음은 BindingAuthor02_Persistent 종료/새 mixer 출력·취소·실제 hit/guard 회귀와 saved 보존 검사다. exact 재개는 ResumeState03.json이며 사용자/다른 task editor 제어0이다.

## 2026-10-12 00:18 KST — ARCH-88 실입자 저장 원인 해결·Main 전달 준비

혈액 분사가 0이던 원인은 엔진 UParticleSystem::PreSave가 SoloTracking에 저장된 원래 disabled LOD를 복구한 것이었다. debugging-code로 own QuickVisual03 native breakpoint의 실제 LOD0=false를 확인했다. BloodDebuggerEvidence.json에 값·call stack·정확한 소유 PID와 정리 결과를 보존했다. 어시스턴트 breakpoint만 제거했고 기존 사용자 exception breakpoint 8개/활성5개는 유지했다. own LLDB/PIE와 해당 프로세스는 종료됐다.

SetupSoloing으로 emitter/LOD 수정 후의 캐시를 재구축한 NativeParticleAuthor04와 QuickVisual04가 실제 성공했다. 6종의 live blood는115/128/168/191/192/192개이며 live ash는 각630개, shader fallback0이다. Blood_HalberdElite 및 late-death PNG를 직접 검사했다. 기본 corpse noise가 큰 면적을 한 번에 지우는 것을 줄이려고 원작 FT_Noise_Dissolve에 KZDeathNoiseTiling=6이라는 명시된 임시 UV 배율을 추가했다. DissolveGrain01은 MaterialEditingLibrary의 축약 pin 이름 UVs 대신 Coordinates를 써서 save0 실패했고, 엔진 GetShortenPinName 근거로 수정한 DissolveGrain02는9 master save/pass다. 새 QuickVisual05로 해당 shader/입자를 검사 중이다.

최신 Main audio Notify reflection 필드를 private Build17 이후 보존하여24 animation을 다시 staging하고 blood Effect None만 재적용했다. AudioCensusMainBefore01/AudioCensusWork02의 전체 animations dictionary가 정확히 같으며 모든 audio GUID·timing·property를 보존했다. 현재 DeliveryPreparation Plan은Source10/Content59/conflicts0이고 아직 Main 게임 파일 적용0이다. Combo/Brutal에는 최신 Main BodyImpactSound 재생을 유지한 단일 혈액 호출만 병합한다. Fall 및 외부 B ring material은 변경하지 않는다.

정확한 재개: QuickVisual05 Driver/Exit 및 late ash PNG 검사 → 새 prepare CAS → 선택69파일 delivery → Main canonical/필요 시 안전한 suffix build → Main saved audit/audio census, 실제 RHI Attack198/1577·death6, CombatUI 및 PlayerAttackCollision approved-hit/miss/dedup 혈액 회귀 → 파일/DLL receipt와 두 도메인 완료 절. quick preview의 Attack0을 전수 검증으로 표시하지 않는다. Halberd source correction52의 native TM/bone 계약 미확인은 그대로 분리하며 원작 pixel 일치로 주장하지 않는다.

## 2026-10-12 01:01 KST — ARCH-88 Main 적용·fresh 검증 종료

FinalVerification.json은 MainDeliveredAndFreshVerified다. Main Source10/asset59, 새 runtime 파일0/private author 전달0이다. 원본 백업은 MainDelivery/Before, 실제 최종 source diff는 MainDelivery/FinalSource.diff다. 기존 Fall cpp 및 외부 B ring material SHA c4d6ff…는 유지했다. 게임 실행 Source6/QA3/Build.cs는 final full PIE launch 이후 hash 동일하다.

MainBuild01–04는 모두 exit0이다. 동시 사운드 editor/DLL과 충돌하지 않게 suffix 모듈을 사용했으며 private binary는 전달하지 않았다. 실제 MainRuntime02(loaded suffix2026101205/SHA f9c210…), MainActualHit01(suffix2026101202/SHA ac073f…), MainUI02(당시 suffix2026101291/SHA58eced…)는 모두 native Success/fallback0/Exit0이다. 사운드 작업은 shared suffix91 파일과 manifest를 후속 build로 갱신할 수 있으므로 과거 load-time SHA와 현재 파일 SHA를 구분했다. 최신 manifest를 오래된 alias로 되돌리지 않았다. 각 증거의 실제 loaded module은 Driver.json/FinalVerification.json에서 확인한다.

전수 실제 검사: Attack198 asset/1577 source occurrence, deterministic pose/socket 변환1483건, source resource identity와 finite transform, normal/paired death6종, live blood/ash와 progressive MID/Destroy가 통과했다. 최종 attack PNG192개/contact sheet8장을 모두 직접 검사했고 blood/ash/late dissolve18장도 검사했다. 나머지6개 Start/Ready/Loop 등 component 없는 case는 native/saved 검사에 포함하며192장을198장이라고 기록하지 않는다. MainRuntime01의 동명 raw/runtime 이미지 덮어쓰기131장은 QA filename에 index를 붙인02로 보완했다. root-travel raw pose가 fixed QA capsule에서 멀어지는 화면은 evaluated pelvis/head 중심 카메라로 보완했으며 제품 이동·카메라·숫자는 변경하지 않았다.

실제 accepted-hit regression13 case에서 Box/Cylinder/Sphere 명중/빗나감, hit-group dedup, 다중 창, HP0, clamp, cancel 및 authored7/19 multi-hit의 HP 적용 수와 blood burst 수가 일치했다. MainUI02는 실제 HalberdElite의 visible normal ring/B chest projection·즉시 damage/recovery·CanActivate/B 실행·lethal0/Max0/UnPossess/RePossess를 통과했다. 02_DamagedGauges/03_ActualLockOn/04_BrutalAvailable_B를 직접 검사했다.

최신 MainSavedAudit02가 save0으로198/1577/42 Effect None, chest6·skeleton5, master9/P0/tiling6/Linear Grayscale/UI gradient를 다시 확인했다. 사운드 작업이 이후24 raw animation을 다시 저장하며67 audio Notify GUID만 재생성했다. AudioCensusMainAfter02는 GUID를 제외한 모든 event field·timing·playback·sound/attach/stop 값이 최초 census와 같다. Own Main 전달 당시 MainAfter01은 GUID까지 완전히 같았다. 최신 GUID를 보존했으며 과거 private animation/오디오를 재전달하지 않았다. Final asset SHA는 이 최신24개를 포함한다.

이번 구현·Main 검증의 필수 잔여는 없다. 정확한 후속 조회는 Router → Architecture v2/ARCH-88 이 완료 절 → FinalVerification.json → 실제 Main Source/asset이다. author/stager/delivery/과거 alias 복구를 반복하지 않는다. 미확인 원작 범위는 Halberd CorrectionInfos52의 기준 bone/TM native 계약, stripped shader/VM/executable/pixel/frame parity와 Shipping 성능이다. source bone-finalized 변환 검사를 원작 실행 파일과의 완전 일치라고 해석하지 않는다.


## 2026-10-12T01:30:45+09:00 — ARCH-89 백그라운드 무음 원인 해결·새 출력 검증 checkpoint

LLDB에서 작업용 PID20716의 KZAnimNotify_PlayAudio.cpp:92/실제 cue·persistent wave·PIE device2·bAllowAudioPlayback1·base submix 연결을 확인했다. Engine FAudioDevice type/PDB가 없어서 mute/volume field 평가가 실패해 소유 audio thread의 DEV probe로 좁혔다. GameSound1/Muted0/TransientGain1인데 FApp AppGain0/PrimaryGain0이었다. EditorEngine.cpp의 focus/bAllowBackgroundAudio 분기가 원인이며 작업용 fixture에서만 in-memory flag와 focus gain을 보존·복구한다. 사용자 설정/사용자 에디터 수정0이다. 임시 breakpoint1 제거/agent-owned debugger 종료, 기존 user8 exception breakpoint5 enabled/3 disabled를 그대로 유지했다.

Build24_NativeCapture exit0/current alias2026101299다. 신규 runtime는 기존 checkpoint의 stateless notify2 class/h·cpp4뿐이며 BodyHit/Projectile는 기존 owner의 작은 optional data/소비 확장이다. 실행/피해/guard/cancel 수명은 기존 GAS 경계다. AudioPIE06 실제7 family/8 case의 출력 nonzero/clipping0, native cancel/loop 정리와 Art fresh saved 검증은 통과했다. 원본 시간 변환994와17 추가/환경 RHI는 Art의 같은 날짜 절을 따른다. CombatEffect actual18/5 pair/natural confirmed hit은 passed다. 후속 test마다 Automation StopTestSession이 PIE를 끝내므로03에서 새 PIE를 다시 요청한다. Python World GC wrapper를 capture 수명으로 쓰지 않고 DEV-only FAudioDeviceHandle로 기록/종료한다. 남은 것은 RegressionPIE03 종료/최종 source·module receipt와 문서다. ResumeState04.json에 정확한 재개를 저장했다.


## 2026-10-12 ? ARCH-90 ?? ?? ?? checkpoint

Router ? ?? Architecture v3/ARCH-88?89 ? Migration ? Guard/MonsterStamina ??? ?? Source? ???. Metadata/Parry_20261012/Baseline.json ? Before? ?? Main ????. ? private project Khazan_ParryWork_20261012/Khazan? Guard Ability BP/Guard ?????/GuardParry effects? ?? writable copies?? ?? Content? ?? ?? junction??. ??? Main PID19752? ???? ???.

Probe01 saved asset readback Exit0: source JustGuard L/R? .5?/15frames/?? Root topology adapter, current GuardStart? .25??. OriginalEvidence.json? source notify/skill/route? SHA? ????. private Source6 ?? ??? Main runtime ??0/build?PIE ?????. stage ??? stdout? CP949 ??? ??? baseline/?? ??? ????? ?? ASCII ???? ???. stage? ?? ???? ???.

??? ??: Baseline/OriginalEvidence/Probe01 ? private Source diff ? source-backed Parry L/R bake?Guard montage append?effect local copy/edge alpha/GA ?? ? private cold build/actual RHI gameplay tests ? ?? Main Source ? audio ?? ???/CAS ?? ? Main suffix build/fresh RHI/saved audit ? ? ??? ?? ?. ?? Content junction ??/SaveAll/??? ??? ??/??? DLL alias ?? ??.


## 2026-10-12T02:04:36+09:00 — ARCH-89 사운드 저장 누락 정확 재개 / 준비본 검증 완료

신규 runtime는 stateless Audio Notify/NotifyState2 class/h·cpp4개이며 기존 ComboDefinition/ComboAction·CharacterDefinition/Brutal·MonsterSkillObject6 runtime 파일의 선택적 Sound/확정 HP·guard/launch·impact 수명만 확장했다. GT Actor/Mesh/engine notify instance 소유 AudioComponent와 engine AutoDestroy/StopWhenOwnerDestroyed를 재사용한다. finite tail은 자연 종료하며 loop/explicit stop만 자기 occurrence에서 정리한다. 새 Manager/Subsystem/Tick/gameplay 상태 사본0이다. 기존 ARCH-86 Fall/paired Brutal·ARCH-87/88 HUD/Monster repair·latest Source를 보존했다.

중단 지점 후 fresh binding readback에서37 DataAsset의 window/object audio 참조가 None임을 발견했다. 원인은 Unreal Python 배열 iteration의 구조체 사본을 바꾼 뒤 windows[i]/nodes[i]/objects[i]에 재대입하지 않은 것이다. author helper를 수정하고 최신 Main에서 비오디오 field 동일성을 검사한 prepared package를 저장했다. SaveBindingCopy/MountBindingCopies는 기존 editor-only 도구 파일의 표적 복사·새 process 검사 기능이며 Shipping runtime 책임을 추가하지 않는다. Build29_PreparedProjectileQA/current UnrealEditor-Khazan-2026101303.dll은 exit0이며 제품 runtime 및 자체 editor/QA Source hash가 build input과 동일하다. 다른 작업의 DEV 검사2파일 후속 변경은 그대로 보존하고 PreparedVerification01의 concurrent_foreign_editor_only_changes에 분리했다. test에서 즉시 Impact로 Destroy되는 Apes weak actor를 다음 phase에서 다시 dereference하지 않도록 IsValid로 검사했다.

SavedAudit06_PreparedBindings/AudioPIE07_PreparedProjectile은 fresh prepared37의 impact61/guard405/object guard4/projectile2 및 실제7 family/8 cancel sample, loop cleanup, 원본 cue를 실제 Shoot에서 재생하고 Impact에서 종료하는2 녹음이 passed/nonzero/clipping0이다. 이 검사는 prepared 바인딩을 명시적으로 mount한 DEV fixture이며 Main 바인딩 완료가 아니다. 기존 Main Animation/Body7/HeinMach source 환경음은 실제 saved/출력 검증됐다. prior CombatEffect actual18+5 paired/natural hit Success와 RegressionPIE03의 실제 PlayerAttackCollision/GiantFall/Guard Success/출력도 보존하되 새37 바인딩 반영 전 회귀임을 구분한다.

남은 외부 조건은 Rider Main PID19752의 파일 잠금이다. owned author 종료 후 hash CAS 교체도37개 모두 Error32로 실패했고 conflict0이다. PreparedVerification01.json complete=false/PreparedVerified_MainBindingsLocked, ResumeState05.json에 준비본 SHA/현재 Main SHA/증거/재개 절차를 저장했다. 기존 사용자 editor/debugger/foreign private editor는 조작하지 않았다. 필요 질문은 Windows 파일 잠금 해제를 위한 저장 후 editor 종료이며 자동 승인 거절이나 skill 승인 규칙 때문이 아니다.

정확한 재개: 미저장 작업을 사용자가 저장하고 Rider editor를 닫은 뒤 `apply_prepared_gameplay_audio_bindings.py BindingRepair03_Prepared Delivery02.json`을 실행한다. SHA가 달라진 package는 과거 준비본으로 덮어쓰지 말고 최신 Main에서 audio field만 새 prepared run으로 재작성한다. KZ_AUDIO_BINDING_COPIES를 해제한 fresh Main saved audit→Audio PIE→전체 CombatEffect/PlayerAttackCollision/GiantFall/Guard mixer 회귀 후 Main hash/loaded module과 실제 출력을 FinalVerification.json에 결속하고 날짜별 완료를 추가한다. 이미 성공한 전체 audio extraction/import/animation retime/환경 author와 과거 private Source·DLL 복원은 반복하지 않는다.


## 2026-10-12 — 사진 기준 Monster 혈액/지면 혈흔 후속 진행 checkpoint

사진/원본 packed RGB texture 표적 검토와 Work 혈액3층/새 재질2 저작이 끝났고 Main 전송 전이다. 최신 floor blood 제거 지시는 이번 사진 요청 범위에서 대체한다. 사망/UI/사운드/낙하 설정은 되돌리지 않는다. WorkBuild04가 외부 ParryWork의 UBT mutex를 기다린다. 외부 editor/build를 종료하지 않는다. 지금 Main에는 DEV 검사2파일만 수정했고 제품 runtime2는 Work에만 있다. 마지막 검증·실패/대기 원인·정확 재개 명령/다음 범위는 Metadata/MonsterBloodReference_20261012/ResumeState.json을 따른다. ParticleAuthor02는 fade 수정 전 DLL의 성공이므로 최종곡선 저작 완료로 읽지 않는다. Baseline/Before bytes와 이전 작업 FinalVerification은 보존한다.


## 2026-10-12 — ARCH-90 패링 준비본: 실제 검증 / Main 잠금

기존 Guard/ASC/Combo/MonsterSkillObject 6 runtime 파일의 작은 확장으로 시작 후 0.146초 전방 blockable 적중을 패링한다. 원작 raw 0.292초를 현재 GuardStart inverse_map으로 계산했으며 비용 배율 0.5와 effect detach 0.06초는 직접 source 값이다. 기존 몬스터 Definition의 사용자 결정 ParryStaminaDamage와 Pattern Parried/고갈 정책을 재사용한다. 새 runtime class/file/태그/GE/Manager는 0개이며 새 DEV test 1개다. Source·책임·cleanup·값 구분·에디터 설정·검증은 [PARRY_IMPLEMENTATION_20261012.md](PARRY_IMPLEMENTATION_20261012.md)에 기록했다.

task-owned ParryWork의 실제 melee/field 15개 상황과 6종 몬스터, 고갈/좌측 response/비용/동일 HitGroup/독립 연타/Release/Cancel/UnPossess를 확인했다. 기존 Guard와 PlayerAttackCollision도 성공했다. 기존 5개 재생 segment·notify는 fresh reload로 동일하며 Montage refresh의 Suc_R 파생 cache 차이는 따로 기록했다. 원작 normal Guard의 JustGuard 설정을 그대로 복원한 것이 아니라 사용자 요청에 따른 시작 창 adapter다.

**Main 구현 반영은 미완료다.** GA_Player_Guard와 AM_DAS_Player_Guard가 기존 Main editor PID19752의 Windows 공유 잠금(error32)으로 대기한다. 대상 SHA 충돌0이며 Source·package를 부분 복사하지 않았다. 사용자/foreign editor 종료·제어0, private DLL/과거 manifest 복원0이다. 현재 잠금과 candidate SHA는 Metadata/Parry_20261012/DeliveryPreflight.json, 준비본 검증과 정확한 재개는 PreparedVerification.json/ResumeState.json을 따른다.



## 2026-10-12 — 패링 최종 준비본 검증 확정 / Main 2개 잠금 유지

최종 Build08/PIE03(15 case 및 6종 Definition)/SavedAudit03/AlphaPreview07는 Exit0·passed다. native 실제 loaded module SHA는 PreparedVerification.json에 있고 현재 준비 Source7은 Build08 input과 동일하다. Gameplay 제품 Source6은 앞서 성공한 GuardRegression01/CollisionRegression01과 같은 코드다. source MI base-property overrides가 복원된 saved reload, DefaultParticle ellipse power2와 .04 UV/1.25px edge 연결을 확인했다. 실제 game viewport의 .13/.24초 효과 및 dark RHI burst를 직접 열어 원판·불투명 card 경계가 없음을 확인했다. Source shader/pixel 완전 일치와 실제 스피커 출력/Shipping/network 검증을 완료한 것은 아니다.

**Main product Source/package 변경0, 적용 완료가 아니다.** 마지막 preflight는 대상 SHA 충돌0·GA_Player_Guard/AM_DAS_Player_Guard의 Windows error32 2개다. 기존 Main editor PID19752가 계속 실행 중이다. 사용자에게 작업 저장 후 종료 상태만 요청했고 에디터를 임의로 종료하거나 잠금 handle을 강제로 닫지 않았다. exact resume는 Metadata/Parry_20261012/ResumeState.json, review diff는 PreparedSource.patch다. 잠금 해제 이후 해당 Source7/asset13만 반영하고 fresh Main build/PIE/audit를 추가한다. 전체 저작/추출과 과거 DLL 복원은 반복하지 않는다.


## 2026-10-12 — 사진 혈액 후속 Main 적용 / 첫 피격 shader 검증 중

초기 ResumeState.json의 Main 미반영 기록은 이 절에서 대체한다. runtime2/DEV2와 유효 신규 혈액 package5는 Main 반영됐고 사용 안 하는 초기 package2는 원본/무참조 SHA 확인 뒤 task backup으로 옮겼다. MainBuild10(2026101249)은 성공·input 동일이다. MainSnowVisual04는6종/지면 수명 정책을 통과했지만 QA가 셰이더 완비를 강제한 검사이며 최종 색 이전이다. 첫 검은 사각형은 ODSC 부분 shader map의 fallback이었다. 기존 Monster BeginPlay의 background cache 보완 뒤 강제 warm 없는 MainSnowVisual05와 fresh MainSaved05가 진행 중이다. 마지막 검증·실패 원인·현재 정확한 own PID/남은 검사/재개는 Metadata/MonsterBloodReference_20261012/ResumeState02.json에 있다. 사용자 PID19752/foreign editor 제어0, 사운드/패링 준비본을 덮어쓰지 않았다. 이전 전체 author/delivery 및 archive 스크립트를 다시 실행하지 않는다.


## 2026-10-12T04:22:44+09:00 — 사진 기준 몬스터 혈액·지면 혈흔 Main 완료

Main runtime2/DEV2/신규 유효 package5·build2026101254·fresh saved/CDO6·실제 눈 RHI6종/24혈액·12소멸/지면 lifetime·actual collision13을 완료했다. 이전 ResumeState/ResumeState02의 pending은 이 절에서 대체한다. 정확한 현재 SHA/loaded module·수치 출처·한계는 Metadata/MonsterBloodReference_20261012/FinalVerification.json, 다음 절차는 ResumeState03.json과 Architecture 최신 ARCH-88 및 Art 정본을 따른다. 첫 shader fallback/몸 안쪽 발생/횃불 과노출을 기존 owner·재질만 보완했다. 사용자 PID19752/foreign editor 제어0이며 새 C++를 사용하려면 사용자 editor의 정상 재시작이 필요하다. 남은 필수 구현0; 원작 native/pixel/frame parity·Shipping stress는 별도다. 기존 사운드/패링 준비본을 덮어쓰거나 완료된 broad author/delivery/archive를 반복하지 않는다.

## 2026-10-12 — ARCH-90 패링 Main 전달 / 검증 진행

사용자의 Main 반영 요청에 따라 재확인한 파일 잠금0·SHA 충돌0을 확인하고 준비 Source7(runtime6/DEV1)과 package13(기존2/신규11)을 Main에 전달했다. `Metadata/Parry_20261012/Delivery.json`과 `DeliveryBefore`가 전달 증거·백업이다. 이전 Main 미반영/잠금 대기는 이 범위에서 해소됐으나 fresh Main build/PIE/saved audit 완료 전이다. 이후 혈액 작업의 KZMonster runtime2/DEV2 및 다른 Source·Config·Plugins는 그대로 보존했다. 이전/private DLL은 전달하지 않는다.

현재 `parry_task_20261012.py main_build MainBuild01`이 최신 Main 전체 Source로 suffix2026101290을 생성 중이다. 실패/중단 시 이 실행의 Launch/Exit/stdout부터 확인하고 같은 이름의 실행 폴더를 덮어쓰지 않는다. 빌드가 성공하면 `main_rhi MainPIE01 Scripts/Engineering/parry_pie_driver_20261012.py` 및 `main_commandlet MainSavedAudit01 Scripts/Art/audit_player_parry_20261012.py`, 기존 Guard/PlayerAttackCollision 회귀를 실행하고 현재 Source/assets/actual DLL을 결속해 완료 기록을 추가한다. 이미 성공한 전체 author·Source 전달·원작 추출은 반복하지 않는다.


## 2026-10-12T08:12:54+09:00 — 사진 혈액 작업의 실제 메인 에디터 적용 완료

후속 사용자 요청으로 기존 Rider Khazan Run configuration에서 Main editor PID23736를 열었다. 이전 사용자 PID19752는 작업 시작 때 이미 종료돼 있었고 강제 종료/기존 세션 저장/ResetLoaders/hot reload는 하지 않았다. 실제 연결된 editor의 project_dir은 Main, world는 /Game/Maps/DevMap.DevMap, 실제 로드 DLL은 UnrealEditor-Khazan.dll, SHA256=fca93bc83565103f376db28049c628fb63950acfc62840a9b6baae94e155a405다. 몬스터6 CDO가 FP_Monster_HitBloodReference/M_Monster_HitBloodGround와 UI_Chest를 읽는 것을 해당 프로세스 안에서 확인했다. dirty content0/map0, asset save0이다.

다른 작업의 Guard/ASC·패링 Source 반영 뒤 UHT generated header가 Guard UCLASS15/GENERATED_BODY18과 달리 이전13/16으로 남아 합본 빌드가 실패한 상태였다. Source 내용 변경 없이 Guard/ASC header의 timestamp만 갱신하여 UHT를 재실행했다. MainEditorBuild01(2026101255)은 exit0/input동일이며 생성 macro도15/18로 일치했다. 이후 다른 작업의 성공한 current1290 선택을 보존했고 그 DLL에서 actual PlayerAttackCollision13을 fresh Main으로 다시 통과했다. Rider 실행은 현재 canonical DLL을 선택·로드했다. 서로 다른 DLL SHA를 같은 바이너리로 표현하지 않고 동일한 current 전체 Source hash와 각 실제 loaded module을 별도로 기록했다. 혈액 Source4/package5는 앞선 FinalVerification와 동일하다.

이 절은 이전 혈액 완료 기록의 '사용자 Main 미재시작/정상 재시작 필요'만 대체한다. 새 runtime 파일/제품 코드 편집0, 기존 사운드·패링 내용의 롤백0이다. GUI/viewport screenshot API는 inactive Slate 때문에 실패했으므로 화면을 직접 검토했다고 기록하지 않는다. 실제 PID/project/world/native loaded module/CDO로 적용 확인을 완료했고 Main editor는 열어 둔다. 정확한 증거는 Metadata/MonsterBloodReference_20261012/MainEditorIntegration/Result.json, 최신 재개 상태는 ResumeState04.json이다. 앞선 실제 시각 검증24혈액/12소멸·수치/한계는 기존 FinalVerification.json과 Art 정본 최신 절을 유지한다.


## 2026-10-12T08:17:34+09:00 — ARCH-90 패링 Main 적용·fresh 검증 완료

이전 준비본/Main 잠금 대기는 패링 범위에서 해소됐다. Main Source7(runtime6/DEV1)/package13(기존2/신규11)을 SHA 확인·백업 후 전달했다. 현재 전체 Main Source/Config로 MainBuild02가 성공한 뒤 일반 stock build가 현재 모듈 UnrealEditor-Khazan.dll을 선택했다. 이를 과거 suffix로 되돌리지 않고 현재 모듈에서도 다시 검증했으며 actual loaded DLL과 동일한 Source/13 asset SHA가 FinalVerification.json에 결속됐다. MainBuild01은 copy2의 과거 mtime 때문에 구 UHT PROLOG13/BODY16을 재사용하여 실패했다. 두 전달 헤더의 시각만 갱신해 PROLOG15/BODY18을 생성했고 제품 코드 내용은 바꾸지 않았다. 후속 전달 도구는 현재 write time을 사용한다.

새 MainPIE02의 Parry15개 상황/6종 Definition 소비·고갈·비용·연타·이동 Guard·좌측 response·release/cancel/UnPossess, 기존 Guard와 PlayerAttackCollision 회귀가 모두 성공했다. MainSavedAudit02는 저장0으로 설정/원본 5 playback segment·notify/7 section/source tag를 reload 검사했다. 실제 .13/.24초 화면에서 모션/weapon contact flash/연속 alpha를 직접 검수했다. 정상 가드 후 성공으로 창을 다시 열지 않으며 전방 blockable 공격만 패링한다. 기본 .146초는 기존 source→current inverse_map 계산, 비용 .5와 detach .06초는 source 값, 몬스터 ST 피해는 기존 Definition 사용자 결정이다.

이후 혈액 작업의 KZMonster runtime2/기존 DEV2와 모든 다른 Source/Config를 보존했다. 사용자/foreign editor 제어0·private DLL 복원0·Audio Notify 수정0이다. 초기 RHI에 GPU memory budget/낮은 FPS 표시가 관측됐으며 이번 fixed-step 기능 검사로 성능을 검증했다고 주장하지 않는다. 실제 스피커 출력(-nosound), 원작 shader/pixel/impact-point 완전 일치와 Shipping/network는 미확인이다. 필수 잔여0이며 최신 결과는 Metadata/Parry_20261012/FinalVerification.json과 ResumeState.json을 따른다. 과거 전체 author/추출/옛 alias를 다시 적용하지 않는다.



## 2026-10-12T09:50:12+09:00 — ARCH-91 몬스터 Root/공격 판정/이펙트 후속 검사 중

사용자의 직접 수정 요청이다. 최신 Main의 6종 실제 소비자를 재조회했다: 시퀀스395/Definition57/Node220/window405/montage126. MainUsageAudit02/RootAudit는 asset save0/dirty0이며 모두 EnableRootMotion/ForceRootLock=true, true skeleton root index0/track0 정상이다. pelvis 등의 child 움직임184개를 root 이관 근거로 사용하지 않는다. 아직 런타임의 모든 root 이동이 정상이라고 주장하지 않는다.

기존 ComboAction·엔진 timer/shape·GAS dedup/피해·Monster/Notify의 표시 수명을 재사용한다. private에서 닫힌 끝 경계의 재검사와 마지막 window 이후 callback 예약을 차단하고, 기존 actor 축/locked-root baked collision 좌표에 현행 mesh relative scale을 한 번 반영했다. Source339 pose 비교는 actor 축의 root-stripped anchor가 원본 baked anchor와 맞으며 mesh yaw/root travel을 다시 더하면 오차가 커짐을 확인했다. 새 gameplay 수치를 넣지 않고 실제 body transform을 사용한다. VFX는 Monster의 socket 없는 actor 기준/실제 몸 크기와 source-correction의 같은 프레임 final bone을 사용하도록 기존 owner를 보완했다. 새 runtime file/class/manager0이다. LatestSourceTime은 GT notify clock→GT bone-finalize의 실제 지연 소비값이며 End/취소/EndPlay의 기존 delegate cleanup을 사용한다. Player/audio/UI/혈액·사망 값은 보존한다.

현재 Main Source/asset 수정0이다. Main을 idle GiantFallWork에 한 번 snapshot했고 baseline native late hit fixture를 보존했다. BaselineLateHit01의 paused-boundary HP7과 world-clock 기반 normal/OverFury 실패를 구분한다. QA를 실제 montage clock 기준으로 보완한 FixBuild01은 성공·input동일이고 FixedLateHit01이 실행 중이다. giant PatternMoves54의800/2000cm vertical curves와 Walking 소비의 실제 확인, six-family runtime/FX/저장 보존/CAS Main 전달·fresh build/실제 테스트가 남는다. 현재 상태/실패/정확한 다음 절차는 Metadata/MonsterRootCollisionRepair_20261012/ResumeState01.json을 따른다. 완료된 old stage/author/delivery를 반복하거나 private DLL을 Main에 전달하지 않는다.


## 2026-10-12T10:45:24+09:00 — ARCH-91 실제 원인 확정·private 검증 / Main 미반영
9:50의 Root 옵션·track 정상 판정은 루트 잠금 포즈 정렬의 완료 판정이 아니었다. 실제 사용395개(몸체392/별도 prop3)를 메시에서 시작·중간·끝1176포즈로 검사했다. AnimFirstFrame 잠금이 누적 시작 root 좌표를 유지했고, Yetuga ChargeTackle_End 7157.4663cm / Apes Run_Loop_Stone 5157.4663cm가 실제 몸체에서 재현됐다. 현재 imported RAW Root 첫 transform과 skeleton reference transform의 차이를 RootLockPlan.json에 고정하고, 88개 RootMotionRootLock만 RefPose로 변경했다. EnableRootMotion/ForceRootLock/normalized scale, raw channels, timing, montage/definition/window/damage/group/audio는 유지한다. 원작 신규 튜닝값이 아니라 UE FRootMotionReset의 기준 포즈 adapter이며 raw source key를 transfer/재작성하지 않았다.
RootAssetsBefore exact SHA backup / disposable duplicate probe / fresh native RootPreservationAfter02 Success 완료다. 몸체392개 전체 DataModel(모든 track/key/curve/attribute) 및 notify event·notify object 직렬화 SHA가 변경 전과 전부 동일하다. raw 판정 .01cm/.001deg와 기존 compressed 기술 허용 .01cm/1e-4rad를 구분한다. RoundAttack의 기존 .0020149deg 압축 오차만 raw tolerance를 잘못 적용한 첫 QA 실패였으며 해당 에셋을 추가 변경하지 않았다. collider는 source actor axes/root-stripped geometry에 live mesh relative scale을 한 번 곱한다. 마지막 window End 동등 경계와 이후 timer를 닫아 paused-end late query를 차단한다. monster socket 없는 VFX는 actor rotation + mesh origin, local offset/size는 live body scale, source correction은 current finalized bone pose를 소비한다. LatestSourceTime은 기존 receipt 내부 GT notify→GT bone-finalize 전달 값이다. 새 runtime file/class/manager0이다.
VerticalPattern.PIE는 기존 Walking/RMS 경로에서 원본800cm 곡선을 소비하며 실제 capsule +659.906cm/관측1.51555s를 확인했다. 최대 곡선 값의 정확 재현이나 전체 궤적 일치 판정이 아니며, Flying mode 전환을 제안/적용하지 않는다. 기존 이동 소스를 보존한다. common PlayerAttackCollision 실제16경로(종료·pause·cancel·Spin7/Fury19) Success다. SixFamilyContacts02는30경로중 Shield case4에 별도 Step1 HP10이 섞였다. source log로 기존 controller의 deferred StartMonsterLogic 재시작을 확인하고 검사 소유 controller tick을 끈 fixture03을 실행중이다. 게임 AI는 변경하지 않았다.
현재 Main Source/asset 반영0. private FinalPrivateBuild04 Success/input unchanged; six contacts03 및 all198 attack assets/current-pose correction/사망 검사는 실행중이다. 재개는 Metadata/MonsterRootCollisionRepair_20261012/ResumeState02.json을 따른다. 저장된 baseline/failed 로그를 삭제하거나 stage/author를 무조건 재실행하지 않는다. Main에는 현재 전체 Source로 canonical build하며 오래된 private DLL/Config/다른 작업을 전달하지 않는다.


## 2026-10-12T11:04:18+09:00 — ARCH-91 Root·공격 콜라이더·VFX Main 완료
Main에 Source7(runtime4/DEV3) 및 RootMotionRootLock 옵션만 바꾼 Animation88 package를 exact SHA/CAS로 반영했다. 새 runtime file/class/manager0, 다른 baseline610파일 보존, private DLL/Config 전달0. MainBuild01은 source 오류 없이 PCH virtual-memory C3859/C1076로 실패했고, 병렬1/noXGE MainBuild02는 Succeeded/input unchanged다. 현재 canonical UnrealEditor-Khazan.dll SHA `e14ca4b34c8a8a8042c2087fca2e646196b51e617d906c1884bee4e6c29cf511`를 사용한다.
실제 사용395 Root enabled/force lock/true-root·track0 및 Body392의1176포즈를 확인했다. 첫 프레임 누적 origin88개만 RefPose lock으로 정렬했으며 근거는 RootLockPlan의 imported RAW root first transform와 skeleton reference pose/UE FRootMotionReset이다. RootAssetBefore 및 MainBefore 백업을 보존한다. 전체 DataModel 모든 key/curve/attribute와 notify event/object SHA392개가 변경 전=private 후=Main fresh로 동일하다. source montage126/definition57/node220/window405의 geometry key·time·HP/Stamina·group·audio와 rate/나머지옵션이 fresh saved audit에서 동일하다. Props3는 다른 skeleton으로 body1176포즈에서 분리하고395 옵션/track audit에 포함했다.
Main actual RootPoses/MonsterHits30/PlayerAttackCollision16 Success. monster30은6종별 한 window 안1회 / 종료 후접근0 / exact-end pause후접근0 / 취소후접근0 / live mesh scale와actor yaw 반영을 실제 HP GE로 확인한다. player16의 기존 Spin7/Fury19와blood13 기반행동도 보존한다. source scale/last-End 경계·timer 종료만 기존 ComboAction에 보완했다. VFX198 assets/1577 source occurrences 및Death6는 동일 delivered Source의 private 실제RHI Success, finite world transforms / deterministic uncorrected source geometry max position3.46e-13cm·angle4.83e-6deg / template identity / body size를 확인했다. 이 보고서의 active correction-curve row는0이므로 해당 branch의 per-pose 실행을 실제 데이터 검증했다고 표현하지 않는다. source 없는 VFX actor axes/mesh origin 및 body scale은 적용했으며 curve branch는 기존 receipt의 latest GT clock→finalized-bone callback으로 구조 보완했다. 원작 native shader/pixel parity·전체두레벨연속전투·network는 검증 완료 범위가 아니다.
Main 파일·canonical build·fresh saved/actual runtime 완료. FinalVerification.json / ResumeState03.json 및 exact Delivered95를 재개 정본으로 읽는다. stage/old alias/full author/retime/reimport를 반복하지 않는다. Main editor 정상 재시작 후 직접 Play에서 green debug volume이 실제 공격 window에서만 나타나고 칼의 크기·방향/몸체 alignment를 확인할 수 있다.


## 2026-10-12T11:13:19+09:00 — Main editor ready
Rider Run opened Main PID32684; read-only RiderLink confirms /Game/Maps/DevMap, current canonical DLL matches MainBuild02 SHA, all88 RefPose settings loaded, dirty content0, asset saves0, PIE not started. MainEditorReady.json / FinalVerification.json / ResumeState03.json contain the exact result.


## 2026-10-12 — ARCH-92 진행 checkpoint

Main Source121/표적 asset bytes를 보존했다. DeathBaseline01 actual PIE는 정상6 terminal pose 오차0, interruption6의 서 있는 freeze를 약0.27초/오차167–441cm로 재현했다. Monster 사망 retry·기존 혈흔6방향 표시 설정 및 Brutal live chest 접촉 위치를 Source에 적용했고 serial FixBuild01 검증 중이다. 다른 작업의 Fab stage editor를 제어하지 않는다. 짝 사망 terminal pose·내려찍기/다른 액션 효과 저작·native regression/화면·Main fresh editor는 아직 미완료다. exact resume는 Metadata/CombatFinishFollowup_20261012/ResumeState01.json을 따른다. 완료된 이전 root/blood/parry 전체 저작을 반복하지 않는다.


## 2026-10-12 — ARCH-92 Main Source/표시 에셋 적용·검증 중

일반 사망 중단6의 잘못된 freeze뿐 아니라 실제 Front/Back12 브루탈의 종료 블렌드 후 terminal pose 오차8–113cm도 재현했다. 해당 lethal instance만 auto blend-out을 막고 기존 Monster GT tick이 마지막 포즈를 확인하여 Exhaustion의 기존 완료 경로를 호출한다. 비치명타 recovery/공유 montage asset는 유지한다. 새 runtime 파일0. Main Source6 runtime/DEV4 및 표시 montage8에 55개 추가 window(공격44/회피8/낙하3)를 적용했다. 기존 event GUID/trigger/필드와 playback 원본은 보존했고, ground strong source2 marker는 weak variants·weapon tip·walkable projection으로 변경했다. TEMP scale/count/distance는 Notify/Monster 기본 설정이며 원작 값이라고 표현하지 않는다. Author01은 저장 전 보존 검사로 종료, Author02의4개 저장 이후 중단점에서 SHA 확인으로 재개하여 Author03 Exit0/8 완료다. authored checkpoint를 재저작하지 않는다. exact resume는 ResumeState02.json이며 actual RHI와 saved/화면 검증은 진행 중이다.


## 2026-10-12T13:12:55+09:00 — ARCH-92 사망·브루탈·액션 VFX Main 완료

Main Source10(runtime6/DEV4), montage8, 새 runtime 파일0을 적용했다. baseline Source121 중 무관111파일을 보존했고 원본 Root88/게임플레이 공격 창·피해·오디오·UI·애니메이션 raw pose는 변경하지 않았다. FinalBuild05 current canonical build/input동일, fresh SavedAudit02 8/55/dirty0/save0가 통과했다. Main 기존 파일을 직접 보완했으며 private DLL/Config 전달0이다.

일반 사망은 interruption을 완료로 간주해 현재 포즈를 멈추던 것이 원인이었다. 기존 RefreshCombatState로 다음 tick에 사망 동작을 재시작한다. DeathBaseline01의 중단6 오차167–441cm → DeathFixed02의 정상6/중단6 terminal pose 오차0. 짝 사망은 task blend-out 완료 시 source 마지막 pose가 이미 idle로 섞이는 문제가 있었다. HP0인 자기 victim instance만 auto blend-out을 끄고 Monster의 기존 GT tick이 finite end를 관측하여 Exhaustion의 기존 완료를 호출한다. shared asset/비치명타 recovery/정상·취소·EndPlay cleanup은 유지한다. LethalPairFixed01 실제 Front/Back12 terminal pose 최대0.015341 model cm, 접촉 XY offset0이 통과했다. 이는 사용자 전체 플레이에서 interruption 빈도를 계측한 결과가 아니다.

Brutal Root particle의 원본 source offset은 현재 capsule 짝 간격/수입 mesh yaw와 맞지 않았다. 기존 effect receipt만 찾아 detach/world XY 두 actor 중점·Z 두 chest 평균에 배치하고 기존 composed rotation/scale·피해·시간·수명은 유지했다. PresentationFinal02는 실제 LockOn→B 6종 Front/Back12, 비치명타 recovery/root-mode 복원 및 실제 낙하/착지/벽 옆 ground debris를 통과했다. EffectsFinal01 기존18+Brutal5, CollisionFinal01 실제16(Spin7/Fury19/miss/cancel/끝 접근), ParryFinal01 실제15/6종 정책도 통과했다. DEV-only viewport readback 추가 이후로만 실제 게임 화면을 판단한다. LethalPairFixed01의 이전 전역 screenshot은 editor viewport였으므로 시각 근거에서 제외한다.

혈흔은 기존 accepted-hit particle1회와 ground projector/fade/snow·walkable 계약을 유지하며 class 설정의6개 작은 satellite를90–280cm 범위/전체 방위로 생성한다. 독립 FRandomStream, 장애물/바닥/가파른 면 제외를 사용한다. DeathFixed01의 scatter0은 QA floor의 Static mobility로 scale이 반영되지 않은 fixture 문제였고 Movable fixture의 DeathFixed02 실제6종에서 main+6=7 /네 방향/범위/하향 normal을 확인했다. 제품 collision/지형을 바꾸지 않았다.

수치와 resource/표시 변경은 Art 최신 절을 따른다. 정확한 변경/각 실제 DLL/원본 보존/실패 기록은 Metadata/CombatFinishFollowup_20261012/FinalVerification.json에 있다. 원작 shader/pixel 완전 일치·Shipping stress/두 레벨 연속 전투는 이번 범위가 아니다. 이후는 현행 Main과 이 receipt에서 시작하며 stage/전체 author/Root·Parry 이전 전달을 반복하지 않는다. Main 정상 editor ready 여부는 후속 기록으로 분리한다.


## 2026-10-12T13:16:18+09:00 — ARCH-92 메인 에디터 적용 확인 완료

Rider normal Khazan Run으로 Main PID16504/DevMap을 열었다. read-only RiderLink가 실제 canonical DLL SHA a247fac8a6c457a90d336ceb9ed90a5445bca878295d941b1c5081a375977f9b와 FinalBuild05 일치, 6종 CDO scatter6/radius90–280cm, dirty content/map0를 확인했다. asset save0, PIE 미시작이며 에디터를 열어 둔다. FinalVerification.json은 MainDelivered_Built_Validated_EditorReady, ResumeState04.json은 complete/잔여0이다. 사용자 이전 Main은 착수 때 종료돼 있었고 강제 종료/HotReload/기존 session 저장0이다. 모든 실제 테스트·동일 runtime source·Art TEMP와 원작 한계는 앞선 완료 절을 유지한다.

## 2026-10-12 — ARCH-93 확정 피격 섬광 착수

Main Source121 baseline을 보존했다. 현재 canonical module/기존 producer를 변경하지 않고 기존 몬스터 피격 PS와 최근 추가 montage child만 표적 수정한다. Main PID16504/DevMap은 열려 있고 무관한 BP_Cursed_Magic_Character dirty1을 확인했다. 해당 BP 저장/에디터 종료/PIE 제어는 하지 않는다. 추가 색상54 제거·3층 짧은 섬광 저작·saved 원본 보존·실제 RHI/적중과 miss 검증이 남아 있다. Scripts/Art/author_monster_hit_flash_20261012.py와 Metadata/HitFlashCorrection_20261012의 최신 checkpoint에서 재개한다. 완료된 root/death/blood/parry/scene/Fab 전체 작업을 재적용하지 않는다.

## 2026-10-12 — ARCH-93 화면 alpha 보완 중 Main OOM / 복구 진행

확정 피격 연결은 Source0 변경으로 최근 색상54 window 삭제와 기존 혈액 PS3+자체 flash3 추가까지 적용됐다. actual Collision01 16/SaveAudit02(8 montage·6종·3/6 emitter) Success다. Visual01/02는 native 검사 Success지만 첫 화면에서 flash 가독성이 부족하여 최종 시각 합격으로 사용하지 않는다. source parry MI의 OPA_Depthfade300cm를 읽었고 자체 표시 material·짧은 거리 fade와 정지된 outward clearance로 보완 중이다.

Main PID16504는 14:28 native MaterialInstance duplicate 요청 중 Foreground Worker #1에서 1GiB allocation failure로 종료됐다. 기록된 UsedVirtual71.65GiB / AvailableVirtual0.73GiB와 paging-file 부족이 직접 로그다. 객체/worker 근본 메모리 누적 원인은 미확정이다. shader 작업을 활성 사용자 editor에서 실행했던 절차를 중단하고 owned NullRHI author → owned actual D3D12 검증 → normal Main 복구로 전환했다. 이미 저장된 Source/게임 파일은 삭제·롤백하지 않는다. 무관한 dirty BP_Cursed_Magic_Character는 저장/편집하지 않았으며 autosave 대상 파일 없음, PackageRestoreData RestoreEnabled=false/Packages=[]를 확인했다. 직접 수정 여부를 사용자에게 확인 중이고 미저장 내용 복원을 완료했다고 주장하지 않는다. 현재 증거는 Metadata/HitFlashCorrection_20261012/MainCrash01·Authored.json, 보완은 Visibility01/VisibilityRefined.json이다. author 전체 재실행/옛 DLL 복원/다른 작업 SceneLook 이관은 금지한다. 다음은 새 material·6 static flash module 저장 확인, fresh saved audit, Visual03 실제 프레임 검수, Source121 동일·선택 asset SHA·Main 재개 확인과 완료 기록이다.


## 2026-10-12T14:40:04.303632+09:00 — ARCH-94 착수 / 정밀 StateTree·Dodge 검증 준비

정본은 Architecture ARCH-94와 기존 APES_YETUGA_FALL_IMPLEMENTATION_20261011 / 행동 분석 및 CombatReaction runtime이다. C:\Users\user\Desktop\GitProject\Khazan_BeastDodgeWork_20261012\Khazan를 새로 준비했고 Main Source/Config/uproject 및 소유 asset roots의 baseline을 Metadata/BeastDodge_20261012/Baseline.json과 Before에 보존했다. 복사 asset 약154MB이며 나머지 Content는 read-only junction이다. Main 제품 쓰기0/에디터 제어0/빌드·PIE 미실행이다. 이전 미완료/성공 원본 패턴 자료를 전수 재추출하지 않는다.

남은 작업: 원본 BT121 export의 StateTree 구조/분기·선택 substep 계획, 기존 Source의 작은 확장, player .1s TEMP 피격 제한·사용자 .1s Dodge 및 실제 성공 feedback, 소유 에셋 설정, 새 cold build, 경계·종료·반복·후속·모든 pattern native 테스트/회귀 및 화면, Main CAS/fresh 검증, 최종 Mixed 문서. 정확 재개는 Metadata/BeastDodge_20261012/ResumeState.json이다. Stage 최초 junction 인자 전달 실패는 소유 partial staging에서 환경변수 기반 native New-Item으로 수정했고 Stage가 성공했다. 부분 Work를 다시 삭제/전체 Main Content를 복사하지 않는다.


## 2026-10-12T14:44:13+09:00 — 검병 발차기·돌진 제외 Main 완료 / 방패병 동작 식별 대기

사용자 요청으로 검병 GA_Kick와 GA_Rush를 기존 BP_Monster_Swordsman.AttackAbilities 및 DA_Character_Swordsman.InitialAbilityGrants에서 제외했다. 공격 후보5→3, 초기 grant14→12다. 남은 GA_EmpireSword_Early_Slash/Early_Smash/Pierce 및 Alert/Idle/Exhaustion/HitReaction은 유지한다. 기존 ARCH-77 StateTree 선택→ASC Spec 활성화→ComboAction 실행을 재사용하며 runtime C++/Tag/Config/DLL 변경0이다. 게임 리소스 삭제·montage/animation/collider/VFX/피해 설정 수정0, 새 runtime file/class0이다. 별도 Khazan_AttackFilterWork_20261012에서 두 asset만 저장했고 Main에 exact SHA/CAS로 전달했다. Prepared02 및 새 MainSaved01 Success/Exit0, AttackAbilities/InitialAbilityGrants와 보호된 AI/Locomotion/HitReactions/MonsterStamina/Unaware/InitialEffects의 원본 보존을 확인했다. DevMap 배치 검병7개 모두 후보3, 방패병1개 후보3을 fresh load로 확인했다. HeinMach에서 해당 두 BP의 배치 actor는0이다. 이는 saved policy 검증이며 새 PIE 실행·제자리 달리기 체감 검증으로 기록하지 않는다. 방패병은 수정 전후 모두 SwordCombo/Pierce/ShieldCrash 후보3, 초기 grant8이며 Kick 클래스가 없다. 두 방패병 asset의 byte SHA는 원본과 동일하다. 사용 중4개 sequence의 raw 발/골반 포즈41시점은 Probe02에 보관했지만, 수치만으로 사용자가 말한 발차기 동작을 확정하지 않는다. 방패치기인지 검 연속공격인지 사용자에게 동작 식별을 질문한 상태다. 임의로 sword swing이나 ShieldCrash를 제거하지 않았으며 방패 동작 제외는 미완료/식별 대기다. 정본은 Metadata/MonsterAttackFilter_20261012/FinalVerification.json 및 ResumeState.json. 확인 후 current Main의 해당 후보/grant 또는 실제 kick node만 작은 data 변경으로 제외하고 새 saved/배치 actor 검증을 수행한다.

<!-- MonsterAttackFilter_20261012_SwordsmanMainVerified -->


## 2026-10-12T15:41:28+09:00 — 플레이어 내려찍기 KZ_Parring_Distort 바닥 연결 착수

기존 ARCH-83/92의 바닥 trace·WPO snow 및 Action receipt를 재사용한다. 요청 에셋은 Niagara이므로 기존 CombatEffect에 nullable NiagaraTemplate과 inactive factory spawn, 기존 Action의 FX 공통 activate/deactivate만 작은 확장으로 추가했다. runtime/build4·기존 DEV1은 별도 Khazan_SlamDistortWork_20261012에만 적용됐으며 Main 제품 쓰기0이다. 기존 KZExtra_PlungeGround 창3.741868–3.863043초를 재사용하고 gameplay 타이밍·피해·Input·Tag·애니메이션은 변경하지 않는다. 원본 Niagara는 보존하고 바닥용 clone의 local-space sprite facing/기하학적90도 회전을 저작한다. Probe01의 UObject.export_text API 실패는 저장0이며 Probe02에서 필드 조회로 수정했다. PrivateBuild01 실행 중; author/fresh saved/실제 plunge+Cascade 회귀/Main CAS와 current build·새 검증은 남아 있다. 정확 재개는 Metadata/PlayerSlamDistort_20261012/ResumeState.json과 Scripts/Engineering/player_slam_distort_task_20261012.py다. 이미 실행한 stage를 반복하거나 private DLL/Source 전체를 Main에 전달하지 않는다.

<!-- PlayerSlamDistort_20261012_PrivateStarted -->


## 2026-10-12T15:54:08.699020+09:00 — ARCH-94 Source·원본 트리 계획 / 빌드 진행 checkpoint

Main 제품 파일 쓰기0, source/config/owned roots는 새 BeastDodgeWork에서만 수정했다. PlayerBuild01은 suffix가 int32 범위를 넘어 실패했고 2026101294의 PlayerBuild02는 Exit0/input unchanged/DLL330907fc…로 통과했다. 기존 HitReaction의 player 제어 timer .1s TEMP와 Dodge의 .1s 사용자값·자기 tag/count/timer/정확 deadline·3 피해 producer 방어·성공 Niagara/SFX 연결을 적용했다. 아직 실제 PIE/에셋 설정/화면 검증은 없다.

StateTree 계획은 YetugaStateTreePlan.json의121노드(Route11/Gate49/UseSkill46/MoveTo10/LockOnMove5)와 exact source SHA/원시 링크다. Work의 기존 Task/Condition/Controller/Monster/Definition/Pattern에 source task/gate, pending damage SideMove, definition tree 우선권과 NoCool SI alias를 작은 확장으로 넣었다. 새 runtime class0, 데이터 struct2, 새 DEV DefensePIE1 및 staging-only author cpp1이다. SourceGraph의 native/defaults/part destruction/selected-map float/timeout 및 passive >=/reset 어댑터는 ResumeState/plan에 명시하며 원작 전체 무오차로 기록하지 않는다.

SourceBuild03 (runner64881, suffix2026101295)는181개 unit의 cold rebuild로 진행 중이며 현재128 이후는 Build.log/Exit에서 확인한다. Source/Khazan을 수정하기 전 active build 입력 hash를 보존한다. 동일 suffix 재사용/stock owned build로 다음 과도한 전체 plugin rebuild를 줄일 수 있다. Plugins junction의 공유 build cache 및 template module manifest는 build가 갱신했으나 Main 게임 Source/Content/Config를 전달하지 않았다. 마지막 inventory에서 foreign editor는 없었지만 후속은 다시 process/args 확인한다. SourceBuild03 완료→run_beast_dodge_editor_20261012.py Author01 author_beast_dodge_assets→Native DefensePIE/Recovery/StateTree·패턴 회귀/RHI→Main 현재 drift field merge·CAS/stock/fresh→완료 기록 순이다.

Source author 계획은 Yetuga의 NoCool alias, forced SideMove Step2/Dempsey Step3, 8 Dodge BP 참조, 두 Definition/tree와 Apes passive3행이다. 기존 grants의 field는 ability_class이다. Editor-only author cpp와 그 StateTreeEditor/JsonUtilities/AssetRegistry build 의존성은 stock 전달 전에 제거·원복한다. first-try parser/Stage 실패를 숨기지 않고 saved receipts를 보존한다. SourceWave는 Feedback/Player_Dodge_Success.wav(.18s 어시스턴트 음향 TEMP/48000Hz/clipping0/zero ends)이며 원작 SFX가 아니다.

## 2026-10-12 — ARCH-95 최신 요청으로 섬광 취소·범위 확장

ARCH-93은 미완료/취소이며 이전 flash 화면 검증을 성공으로 기록하지 않는다. 새 섬광 emitter/material/template와 임시 HitFlashRuntime DEV9줄을 제거한다. 혈액3·지면 scatter·사망/UI/audio/Root/54 unconditional accent 제거는 보존한다. Main PID14100은 DevMap/dirty0이고 요청 Niagara2·parry clips2가 존재한다. Spin 원통5개 X=-200cm, 마지막2 Y=-60cm를 확인했고 Fury20개의 actor-local box 전방 확장을 준비한다. 신규 author/build/검증은 Metadata/CombatImpactUpgrade_20261012만 사용한다. Source baseline부터 저장→현 소유자 작은 diff→별도 새 에디터 author/saved/gameplay/RHI→Main current editor 정상 재로딩→완료 기록 순으로 진행한다. 이전 전체 author/alias/flash helper 실행부를 재실행하지 않는다.


## 2026-10-12T17:36:17.753185+09:00 — ARCH-94 Apes·Yetuga StateTree / 플레이어 피격·회피 진행 체크포인트

정본 metadata는 `Metadata/BeastDodge_20261012/ResumeState.json`과 NativeBatch01/Patterns01/FinalWorkQA01이다. Main 게임 Source/Content/Config 전달은 아직 0이다. 분리 프로젝트 Khazan_BeastDodgeWork_20261012에서 원본121개 BT 노드·49 gate·46 skill·10 MoveTo·5 LockOnMove를 보존하고, 선택 실패를 원본 failure edge로 돌리는 실행 상태를 별도로 둔다. Yetuga runtime tree173 state/Apes9 state, 기존 PatternAbility/AIController/Definition을 재사용한다. 새로운 runtime 파일/class는0, 개발용 QA 파일3이다.

Patterns01의 Apes19/Yetuga28(원본24+SI/step alias4) 실제 GAS 실행47건 및 실제 Sight→Roar→전투가 통과했다. NativeBatch01의 SourceAudit, 실제7피격 SideMove passive, 실제 근접/장판/투사체 회피11건·8방향 취소/비용 실패·타 기여 보존, 마지막 피격 후 잠금/이동/회피 복구6건이 통과했다. 피격 잠금0.1초는 어시스턴트 TEMP, Dodge 시작0.1초 무적은 사용자 지정이다. 피격 montage blend-out의 Root Motion만 비활성화하여 이동을 방해하지 않게 한다.

FinalWorkQA01에서는 최초4 및 Guard/CombatPolicy 통과, Parry는 기존 native test의 자체 PIE 요청과 driver 요청이 중복되어 World가 교체된 실패(Driver에서 수정), PlayerAttackCollision은 OverFury19 기대/18 관측으로 재검증이 남았다. 기대값을 낮추거나 성공으로 기록하지 않는다. 새 Main Niagara/피격 표현 Source 변경을 Rebase02로 병합했고 Build.cs는 Main의 기존 Niagara 항목을 그대로 채택했다. 현재 병합본의 잘못된 FXSystemComponent.h include가 컴파일 실패했으며 실제 UFXSystemComponent 선언은 기존 ParticleSystemComponent.h에 있다. 이 한 줄을 제거하고 stock rebuild한다. 생성용 author CPP/추가 editor dependencies는 제거했고 원문은 Completion에 보관했다.

회피 효과는 Fab CursedMagic Dash1/Blink1을 재사용하고 새 유한 .18초 WAV를 제작했다. 원본 VFX 파일은 변경0이며 User.Scale_All의 preset 값을 TEMP 배율 .12/.15로 곱해 설정하는 보완본을 최종 화면 검수한다. 원작 전용 SFX/VFX 또는 pixel 일치를 주장하지 않는다.

메인 에디터 재시작 승인을 비동기로 요청했으며 응답 전 종료/강제 종료를 하지 않는다. 응답 후 최신 PID/프로젝트/dirty/PIE를 재확인하고 정상 종료→최신 Source/Data CAS→canonical stock build→fresh Main SourceAudit/피격/회피/AI/회귀→원래 map 재실행 순이다. Main 소스가 계속 변경되면 작은 3-way 병합을 반복하고 사용자 변경을 보존한다. 원작 custom BT의 native RNG/abort/생략 기본값, Group1 부위 파괴 생성자, 원작 물리·이동·selected-step float 의미는 미확인이다. 현재 엔진 실행 및 저장 구조의 검증과 원작 완전 일치를 구분한다.


## 2026-10-12T18:08:30.145524+09:00 — 몬스터 넉백·전체 몽타주 프레임 증폭 수정 진행 중

읽기 전용 전체 registry 감사와 계획/선택 asset·Source/Config632행 백업을 완료했다. 기존 소유 SlamDistortWork를 재사용하고 선택461 시퀀스/45 의존 몽타주만 writable copy로 확장했다. Main 기존 editor PID14100은 저장/종료/PIE/reload하지 않는다. 제품 Main 쓰기는 이 새 요청 범위에서0이다. 기존 내려찍기 VFX는 별도 PlayerSlamDistort receipt의 Main 전달8/build03/saved 완료 뒤 마지막 RHI 중이다.

현재 PrivateBuild02가 최종 header/UHT 및 editor-only clock/test를 빌드 중이다. Build01의 source-midbuild macro mismatch 실패를 보존했다. 다음은 실제 sampling inventory → native clock author → fresh frame-index key/실제 시간 보존·모든 montage 표시율 검사와6종 넉백 actual PIE → 필요 회귀 → 선택 CAS Main 병합/build/새 Main 검사다. 정확한 경로/실패/명령은 Metadata/AnimationTimingKnockback_20261012/ResumeState.json. 과거 전체 reimport/Root repair/다른 private Source·DLL 전달을 반복하지 않는다.


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 KZ_Parring_Distort Main 완료

기존 FallAttack의 Start3.741868019104004/End3.8630430698394775 branching 부모 안에 KZExtra_PlungeDistort child 한 쌍을 추가했다. 기존 source ground dust·GUID·section/segment·공격 판정/피해/오디오·RateScale은 보존했다. 최신 Main ARCH-95의 NiagaraTemplate/공통 UFX 실행·종료·module 의존성을 재사용하고 shared factory에 실제 traced floor normal의 User.KZFloorNormal와 sort/dilation 처리만 합쳤다. UObject receipt·끝/취소 cleanup은 기존 ActionAbility 소유다. UE5.8에서는 UFXSystemComponent가 기존 ParticleSystemComponent.h에 선언되므로 없는 별도 include 두 줄을 제거했다. 새 runtime class/file/tag0이다.

선택 전달8행(기존 runtime factory1/DEV1/asset6)과 include 보완2, MainBuild03 exit0, fresh MainSaved01 저장0, MainPIE02 actual input fall→landing의 유효1개·바닥/분리/normal·정지·기존 dust 유지가 통과했다. 실제 loaded current canonical module와 파일 SHA는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json에 있다. 초기 floor rotation90도 trial은 철회했고 최종 RelativeRotation0/Scale1과 normal binding을 사용한다. 사용자/foreign editor 저장·종료·reload0이며 후속 stock build의 current manifest를 보존했다. 필수 잔여0; 전체 author/과거 alias 전달은 반복하지 않는다.

## 2026-10-12 — ARCH-95 Main 데이터106 반영 / 실전 확인 진행

Metadata/CombatImpactUpgrade_20261012의 Delivered.json은 검증한 package106개 Main CAS/백업 전달 완료다. Source는 현행 Main 소유자에 작은 diff로 직접 적용했고 old private DLL/Source 전체 전달0이다. MainBuild02 canonical350f3558/input unchanged/exit0, WorkSaved01은106 saved package/원본 timing·GUID/정면 Spin/정확한 Niagara2/flash template 참조0를 확인했다. WorkGameplay01의 PlayerCollision16/Parry17은 Success이며 quick release/moving release의 성공 포즈 유지도 포함한다. 별도 SlamDistort의 floor normal/sort/dilation factory 보완 및 Main montage child는 보존했다.

실전 Plunge 테스트는 첫 fixture의 잘못된 BP 경로로 초기화 실패했다. 실제 경로 /Game/Bluprints/Monsters/BP_Monster_Swordsman으로 수정한 DEV와 WorkBuild06은 성공했으며 실제 바닥 착지/취소 복구를 재검증한다. 첫 GPU 불똥 screenshot은 가시성 합격이 아니다. 새 CPU burst 보완은 원본 재질/색을 유지하고 GPU bounds/vector-field 의존성만 제거하여 CPUBurst02에서 저작 중이다. 숫자120/.18–.38초/1000–1800cm_s/8–18cm는 어시스턴트 TEMP다. 정확 재개는 ResumeState.json의 남은 단계이며 완료한106 전체 author/delivery를 재실행하지 않는다. 사용자 미저장 Knockback2개는 저장/종료하지 않았고 Main14100은 이후 외부에서 종료됐다. 다른 작업 editor16468 등은 제어하지 않는다.


## 2026-10-12T19:20:23.056916+09:00 — ARCH-96 Main516 선택 반영 / 최종 검증 중

Main에 Source5(runtime2/DEV2/Build1)와 asset511(정수 FPS sequence461/연결 montage45/Definition4/감속 curve1)을 SHA/CAS로 반영했다. dll·Config 전달0이다. Main 동시 수정88개를 최신 Source package에서 다시 보정하여 신규 공격 Niagara/notify를 보존했고 원본3854855 raw bone key가 동일하다. Source도 ARCH-94 Player0.1초/ground-hit 분류/OriginalPatternStateTree 추가를 보존했다. User/foreign editor 저장·종료·PIE/reload0이다.

PrivateSaved03: 모든158 montage의 actual sampling/display가 integer이며 재생 시간 차이0;461 sequence raw key/notify GUID·시간 재로드 검사 성공. KnockbackAfter02의6종11case(인간 F/B8/Giant2/벽1)·recover/retrigger/cancel 성공. 인간 기존250cm는 유지하고 normalized curve2u-u² TEMP로 감속한다. 실제 baseline GI root 이동 Apes−278.01cm/Yetuga−222.11cm는 원작 NoAir/NoBlow의 unpaired 대체 실행 instance만 root extraction을 막아 최종0cm로 개선됐다. Source에 함수·manager·태그 추가0이다.

MainBuild01와 별도 private MonsterHits 회귀가 진행 중이며 아직 Main fresh 완료가 아니다. 남은 exact commands는 Metadata/AnimationTimingKnockback_20261012/ResumeState.json. 완전 author/reimport/old DLL·private 전체 전달은 반복하지 않는다. native Author02 cache·Author03 montage-model grid trial 실패와 수정·백업을 보존했다. montage precision DataModel은 기존 값을 유지하고 실제 displayed sampling만 sequence의 정수 FPS로 갱신한다.


## 2026-10-12T19:30:36.993088+09:00 — ARCH-96 몬스터 넉백·전체 FPS Main 완료

Main516행=기존 runtime2(KZHitReactionAbility.cpp/CharacterDefinition h)+DEV2/Build editor dependency1+asset511을 선택 적용하고 새 Main build/reload/실제 RHI를 확인했다. 기존 ASC·HitReaction/JumpForce Task·Definition과 취소/root-mode·회복 수명을 재사용했다. 새 runtime class/file/manager/tag0, private DLL·Config 전달0이다. 다른 작업의 Player0.1초 제어 제한/ground-hit 분류/원작 StateTree 추가와 최신 공격 VFX88개를 보존했다.

MainBuild01 exit0, MainSaved01의461 sequence3854855 bone key/notify GUID·시각·158 montage의 actual sampling 및 재생 시간 차이0, MainKnockback01의6종11case(인간 F/B8/Giant2/벽1)·회복/재피격/cancel/root-mode 복구, 기존 실제 monster collision 회귀가 성공했다. MainInventory01의 전체2674 sequence/158 montage에서 소수 sequence/model·sampling0,100000fps fallback0이다. native loaded module/516SHA/각 evidence는 Metadata/AnimationTimingKnockback_20261012/FinalVerification.json에 결속했다.

인간4종은 기존250cm와 실제 HitLand 시간을 유지하며 Definition.KnockbackTimeMappingCurve에서 normalized2u-u² TEMP 감속을 조정한다. baseline 착지 직전 약278–375cm/s의 일정속도 → 최종 약8–28cm/s로 줄어든다. RootSource 제거는 엔진의 MarkedForRemoval/다음 이동 tick 삭제를 구분해 검증했다. Apes/Yetuga는 NoAir/NoBlow 대체 clip의 짝 grapple root 이동을 해당 실행 instance만 PushDisableRootMotion으로 억제하여 baseline−278.01/−222.11cm →0cm다. source clip/raw/root 옵션 및 Short fallback·정상 Launch Task는 보존했다.

필수 잔여0이다. 현재 editor는 정상 재시작으로 새 C++/asset cache를 로딩한다. 사용자/foreign editor 제어0이며 이전 pending·failed trial 기록은 이 완료로 대체한다. 원작 curve keys/전체 pose·native/network/shipping parity는 미확인이고 TEMP를 원작 수치라고 부르지 않는다. 과거 author/추출/원본 retime/root repair/옛 DLL 전달을 다시 실행하지 않는다.


## 2026-10-12T19:50:49.391255+09:00 — ARCH-94 Main 반영·현재 실행 검증 완료 / 원작 전체 동일성 미확인

정본은 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`과 최신 `ResumeState.json`이다. Source22/asset19 실제 반영, MainBuild04 Exit0/runtime input hash 일치, MainFinalQA04의 SourceAudit/Passive/Defense/Recovery/47기술/PlayerAttackCollision 모두 성공, Guard/Parry·GiantFall 회귀도 성공했다. 과거 Main미반영/OverFury/Parry/최종 검사 대기는 이 검증으로 대체한다. QA03의 불필요한 synchronous 감사 PIE 요청은 driver만 수정해 QA04로 검증했다. 임시 author는 제거됐고 private DLL 전달·Config/map/원본 VFX 수정0이다. 동시 ARCH-95/96 변경을 보존했다.

원작 native RNG/abort/생략값·Group1 부위 파괴 producer·selected float/물리 동일성은 남아 있다. Group1 gate만으로 완성 경로라고 부르지 않는다. 후속은 보고서→기존 정확 metadata→부족한 native 계약/원작 통제 자료 확보 순서다. 현재 검사를 재현할 때 `run_beast_dodge_editor_20261012.py`에 새 고유 label, `beast_dodge_batch_driver_20261012.py`, `--main --pie`, MainFinalQA04/Driver.json의 test목록을 사용한다. 과거 prepare/author/install 및 Work DLL 복사를 다시 실행하지 않는다. foreign editor 저장·종료·reload0이며 pending 재시작 승인을 받았다고 기록하지 않는다.

<!-- BeastDodge_20261012_MainCompleted -->


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

사용자 최신 지시로 몬스터의 지정 Niagara 교체를 철회하고 원본120개 효과 occurrence를 복구했다. Player 원본50 start/stop쌍을 복구하고 별도 KZWeaponSlash child50쌍만 추가했다. immutable before package와220개 객체×21개 수정 field를 비교해 차이0이다. 원래 notify GUID/clock, ARCH-96 FPS·넉백, ARCH-94 방어/AI, SlamDistort·혈액/사망/UI/오디오를 보존했다. 과거 패키지 bytes 전체 또는 private DLL을 Main으로 덮어쓰지 않았다.

추가 Slash는 기존 Action effect receipt와 finalized-bone delegate로 소유한다. 실제 Weapon_L/R 뼈에 reference cutting-edge geometry를 연결하고 successive actor-space tip pose에서 이동을 뺀 swing tangent를 계산한다. FX marker의 별도 animation track은 실제 장착 무기의 대체 pose로 사용하지 않는다. X는 실제 접선, Y는 절삭면이며 requested mesh의200cm reference span/renderer yaw180·centre를 보정한다. Niagara component의 CurveRotation0/CurveScale1·Rotation0만 neutralise하고 shared Niagara asset은 보존한다. 정상/취소/node 교체·사망/UnPossess/EndPlay cleanup은 기존 receipt가 처리한다. 새 runtime class/component/manager/tag0, 새 개발 plunge QA1이다.

Native Player18+Brutal5/실제 승인 hit blood, collision16/Parry17·received-hit feedback/monster-overlap plunge ground·cancel, human33 actual attacks 및 original4-family FX·requested Niagara0이 통과했다. saved100 package에서 original monster120/player100+added player100을 확인했다. 실제 코드·에셋·loaded module 및 모든 검증은 Metadata/CombatImpactUpgrade_20261012/FinalVerification.json이다. 최신 normal Main editor를 열고 loaded module·dirty0 및 설정을 확인했다. Runtime Source가 같은 전체 suite와 DEV-only isolated4 preview를 구분한다. 이전 replace33 검증·실패 camera API·tail assertion은 최신 완료 계약의 근거로 쓰지 않는다.

## 2026-10-13 — ARCH-97 StrongCombo VictimFront 적용·검증 진행

최신 요청은 StrongCombo만 인간형 정면 피해자 모션으로 고정하는 것이다. Router→Architecture v2/ARCH-85·94·96→Migration→CombatReaction runtime/UserGuide→현재 Main을 확인했다. RiderLink 연결=false, 진행 시작 시 기존 Unreal editor process0이다. Main runtime3파일(Data/KZCharacterDefinitionData.h, Character/KZCharacter.cpp, Ability/KZHitReactionAbility.cpp)을 좁게 수정했다. enum 끝에 VictimFront를 추가하고 Definition 선택값→기존 Short event.OptionalObject→기존 HitReaction Task로 고정 재생한다. unpaired montage instance의 root travel을 억제하며 설정 없는 거대형은 기존 Knockback으로 fallback한다. 새 runtime file/class/tag0, 새 gameplay 수치0이다.

Main 저장 probe Probe02는 StrongAttack01–03 각2window Knockback과 인간형 기존 AM_BrutalVictimFront의 Damage1/2를 확인했다. Probe01은 Python에 composite_sections가 노출되지 않아 exit1, 저장0이며 get_num_sections/get_section_name으로 수정한02가 exit0이다. 변경 전8파일/Baseline.json·Before와 기존 DEV KZKnockbackPIETest.cpp 사본을 보존했다. 현재 DEV 기존 파일에 실제 saved StrongCombo12case(4종×3타)·고정/취소/재피격·Short/Knockback 보존/거대형 fallback 검사를 추가한 Build01(session58451)이 진행 중이다. 에셋5개는 아직 author하지 않았다.

정확한 재개: Metadata/StrongComboVictimFront_20261013/Build01/Exit.json과 Build.log 확인→build 성공 후 strong_combo_victim_front_task_20261013.py probe Author01 Scripts/Engineering/author_strong_combo_victim_front_20261013.py 실행→6window/4setting/5save 및 보존 assert 확인→같은 runner probe 새 고유 label로 probe_strong_combo_victim_front_20261013.py fresh reload→runner rhi 새 label Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py Khazan.CombatReaction.StrongVictimFrontPIE→actual12case·Driver/StrongVictimRuntime.json 검토→필요시 기존 PlayerAttackCollisionPIE 회귀→현재 Main source/asset/hash 및 최종 결과/문서 기록. 진행 중 build 입력을 수정하지 않는다. 과거 broad author/retime/Root 복구/VFX 재전달/private DLL 복사를 반복하지 않는다. 적용/build/PIE를 실제 완료 결과와 구분한다.

## 2026-10-13 — ARCH-97 Main 저장·첫 실제 재생 검사 / DEV 기대값 보완

Build01 exit0/input동일(233.921초), Main canonical module SHA b2be03237dbc719ac61d4ade9b070cf90c4286562d74cf7e457e6570ed35c8f4다. Author01은6window/4setting/5save, fresh Saved01은 original node 전체/Definition의 피격·AI·GAS grant·소진/브루탈·이동 설정 보존과 거대형 optional 미설정/저장0을 통과했다. 현재 정면 victim 두 source segment에 execution material notify0이어서 생존 중 dissolve adapter를 추가하지 않았다.

ActualStrong01은 실제12case(4종×3타)에서 모두2회 accepted hit를 관측했으나 DEV 기대값 두 군데가 잘못돼 Fail이다. HitGroup=None은 공통 group1이 아니라 window별 독립 판정2이며, GetCurrentActiveMontage는 IsActive=false인 blend-out instance를 제외해 NULL을 반환한다(엔진 AnimInstance.cpp:3618). AbilityTask는 OnCompleted까지 자기 hit tag를 유지한다. 테스트를 None 개수+named unique group으로 정정하고, 실제 active montage가 있으면 Expected와 비교/자기 root-disable 검사, 정상 tail NULL은 별도 계수하되 실제 active front 관측은 필수로 유지했다. 제품 runtime3파일/저장5package는 추가 변경0이다.

Build02(session14238)는 수정 DEV1파일만 재빌드하며 타 프로젝트 Khazan_PlayerPartsWork_20261007의 UBT10844 -WaitMutex 뒤에서 기다리는 상태다. 해당 build/외부 editor를 종료하지 않았다. 재개는 Build02 Exit/input SHA→같은 native test ActualStrong02 고유 label→성공 시 기존 Khazan.Combat.PlayerAttackCollisionPIE 회귀/최종 evidence·현재 Main SHA·완료 MD 기록이다. Author01은 이미 성공했으므로 baseline CAS가 필요한 author를 재실행하지 않는다.


## 2026-10-13T01:40:50.930443+09:00 — ARCH-97 StrongCombo 인간형 VictimFront Main 완료

사용자 요청을 Main에 적용했다. StrongAttack01–03 각2개, 총6개 AttackWindow만 VictimFront로 변경하고 인간형4종(Swordsman/SwordShield/HeavySwordsman/HalberdElite)의 HitReactions.VictimFront에 기존 AM_BrutalVictimFront를 연결했다. 정면 피해자 모션 Damage1→Damage2를 기존 일반 HitReaction Ability/Task로 고정 재생하며 짝 브루탈을 시작하지 않는다. 해당 자기 montage instance의 paired root travel만 억제하고 Knockback/Launch RMS를 만들지 않는다. 설정 없는 Apes/Yetuga는 이전 Knockback pool을 유지한다. 사망·소진·guard 및 피해 승인/dedup/HP·ST/기존 효과는 기존 계약을 따른다.

runtime3파일/기존 DEV1/저장5package 수정이며 새 runtime file/class/태그/manager 및 새 gameplay 수치0이다. enum을 끝에 추가하여 None/Short/Knockback/Launch의 기존 ordinal을 보존했다. Character의 Short event.OptionalObject가 명시한 montage를 Ability가 선택하며, 정상·재피격·취소의 기존 제약/tag/montage cleanup을 재사용했다. 다른 Player window/몬스터 공격·브루탈/Definition의 원래 모든 피격·이동·AI·grant·소진 설정은 fresh Saved01 readback으로 보존 확인했다. 정면 클립에 execution material notify0도 확인해 추가 사망/재질 adapter를 만들지 않았다.

Build02 exit0/input동일, actual RHI ActualStrong02의4종×3타=12case/24승인 적중·어느 target facing에서도 고정 pose·자기 root-disable·RMS 없음·자연 완료/재피격/취소·다른 Short/Knockback pool·거대형 fallback과 기존 PlayerAttackCollision16 회귀가 성공했다. 실제 loaded module SHA는 `b8f1d59008558802324c3b8e7a1cdaba9a526f02efd36f852788a9fd25bbc4b5`이며 전체 Source/선택5asset·저장/실행 evidence는 Metadata/StrongComboVictimFront_20261013/FinalVerification.json과 Changes.patch다. Actor 크기/높은 평면은 격리 QA fixture이며 원작 pixel/전체 pose 일치 검증으로 표현하지 않는다.

필수 잔여0이다. Probe01의 Python 미노출 property/ActualStrong01의 DEV None-group·blend-out 기대값 실패는 역사로 보존하고02의 성공으로 대체한다. CollisionRegression01은 등록명을 잘못 입력해 matched test0이며 Launch PID/CommandLine을 확인한 task-owned process만 종료했다. 정확한 등록명으로 실행한02의 성공을 근거로 한다. 제품 runtime은 첫 실제 검사 이후 추가 변경0이며 Build02는 DEV 보완이다. 기존 editor process0에서 시작했고 외부/사용자 editor 제어0이다. 이후 조정은 최신 Main Definition의 VictimFront와 Player StrongCombo의6window만 표적 확인한다. 완료한 author/과거 VFX·Root·retime/private DLL 전달을 재실행하지 않는다.


## 2026-10-13 — 몬스터 보조 물리 준비·실행 품질 조사 중

사용자 직접 요청으로 player의 현재 물리 설정을 재사용한다. Router/Architecture/Migration/Physics/PlayerParts 정본과 저장 metadata에서 시작했다. 기존 gameplay6종 PhysicsAsset None을 확인했고, imported35 SK 전체에 PA35/secondary post-process20/Elite CopyPose1 및 기존 BP6 설정을 작업본에 생성했다. 신규 runtime class/component/manager/tag0이며 기존 KZMonster.BeginPlay의 modular follower 초기화만 작은 보완을 준비했다. 현재 Main 게임 에셋·Source 반영은0이다.

정확한 상태는 `Metadata/MonsterSecondaryPhysics_20261013`과 `Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md`다. NativeAudit01/Author01/HeavyCollision01 Success, PrivateBuild01/03/05 Success. 컴파일 도구 타입 오류 Build02/04는 실패 로그로 보존했다. 첫 PhysicsPIE01은6종 모두 finite/실제 simulation·반응/접촉을 관측했지만 Heavy Hair49.34°, Halberd142.77°, Apes90.63°, Yetuga177.71°가 기존 cloth45° QA를 넘어 **Fail**이다. 조작한 QA를 성공으로 기록하지 않는다. 새 candidate97 packages는 아직 전달하지 않는다.

별도 owned29816/LLDB에서 GameThread `FPhysicsRun::Sample` line110과 PA24/4/4·fixed1/60, active acceleration SLERP·hard angular limits·projection 값과 Halberd idle47.04°를 직접 관측했다. Engine/PDB 하위 stack은 미해결이며 root cause 확정 전이다. `DebuggerEvidence.json`을 보존하고 agent breakpoint 제거/session detach, 기존 user exception8 상태를 유지했다. Debug01은 중단시간 영향을 받는 진단 run이며 생산 성능/정상 타이밍 검증이 아니다.

재개: PrivateBuild06 확인 → 최신 owned process 목록/실제 project 확인 → `KZ_MONSTER_PHYSICS_NO_CONTACT=1` 진단 전용 PhysicsPIE 대조 → 같은 saved candidate의 접촉 활성 대조/worst bone·stage 비교 → geometry/관절 충돌을 근거에 따라 최소 수정 → flag 없는 fresh saved/native/RHI 및 실제 PlayerAttackCollision 회귀 → 최신 Main SHA/CAS·필드 병합과 별도 Main module build/검증 → 완료 기록. 기존 full Author는 existing-result guard가 있으며 반복 실행하지 않는다. 사용 중인 다른 ParticleAlpha/Main 작업 editor를 종료/저장/제어하지 않는다. 원작 anatomy17/17/16 capsule 형상은 `OriginalAnatomyShapes.json`의 field/raw 값, feel은 현재 player의 명시된 TEMP 재사용이다. 전체 원작 물리/skin 관통0 검증은 미완료다.

<!-- MonsterSecondaryPhysics_20261013_intake -->

## 2026-10-13 — ARCH-98 Giant VFX private 구현/초기 build 보완

새 Work는 최신 Main Source/Config/Binaries와 두 종237asset을 snapshot했다. Probe01은 Python bool property의 b_attached 이름 미노출로 저장0/exit1, C++ 원명 bAttached로 수정한 Probe02는137sequence/49system·129node/objects를 저장0으로 확인했다. ParticleExports01은49actual PS T3D export를 완료했고 ParticleModuleSummary/ParticleObjectCatalog를 재사용한다. Blueprint 본체/캐스터와 별도 객체의 source actor 소유자를 구분했다.

private runtime7파일에 world-particle-unit 선택값, SkillObject Spawn/Flight/Impact 표현, 실제 Prop notify의 finalized-bone callback/weak receipt/정상·clip전환·EndPlay cleanup, 실제 StaticMesh bounds로 기존 radius를 맞추는 작은 보완을 작성했다. Gameplay effect/피해/curve/time/속도/geometry/ASC/AI/root는 변경0이며 Main 게임 Source/asset 반영0이다. 기존 DEV MonsterPresentationRepair 파일에 actual game viewport의 animation/particle/object 검토를 추가했다. WorkBuild01은 Plugins가 Main junction임을 확인해 own UBT31088/descendants만 중단했다. CogDebug 등의 생성 build output이 공용 plugin path에서 생성된 사실은 보존하고 과거 DLL을 덮어써 복원하지 않았다. junction object만 Work/BorrowedPluginsBeforeIsolation에 보존하고 Plugins source/binaries를 private physical copy로 전환했으며 이후 shared plugin output path0이다. prepare script도 같은 physical-copy 방식으로 수정했다.

현재 WorkBuild02(session 주 실행 로그)가 진행 중이다. 정확 재개는 WorkBuild02/Build.log·Exit.json 확인→오류 있으면 현재 관련 Source만 보완/새labelbuild→giant_vfx_task rhi WorkBefore01 giant_vfx_review_driver_20261013.py Khazan.GiantVFX.ReviewPIE 실행(기본 before)→실제PNG의 단위·sprite 카드·각도/위치 식별→private 최소 asset author/material clone→all after actual animation/49PS/objects 검토→값/계약/cleanup 검사→최신 Main CAS 선택병합과 fresh build/saved/actual RHI. 완료한 prepare/Source fullcopy/원작전체추출/RootFPSauthor/old DLL 전달을 반복하지 않는다. ParticleAlpha_20261013와 SecondaryPhysics_20261013의 private/main 변경을 덮지 않는다. Art 대상·숫자·시각 검토는 새 Art 정본에 별도 기록한다.


## 2026-10-13 — 저장 후보의 품질 조정 / 메인 전달 전

현재 PA35 / SK35 / post-process20 / Elite CopyPose1 / 기존 gameplay BP6의97 package는 격리 작업본에만 있다. 초기378개에서 giant의 미분류 facial/muscle controls61개를 animation-driven으로 되돌려 explicit cloth/hair317개다. Main 게임 Source/asset 반영0이다. 기존 skeletal vertex/skeleton/animation/texture/material 재임포트0이다.

enemy reference root35개 모두1을 확인하여 player wrapper100용 world-space 설정 대신 ComponentSpace를 사용했다. thin capsule 관성은 실제 dominant skin support의 uniform box 관성으로 보완하고 player mass-per-length·반경·spring/damping/각도·24/4/4·1/60 solver 값을 유지했다. hair angular projection은 현재 player Torso의0.8을 사용한 기술적 어댑터다. 중검병 분리 head/upper는 내부 anatomy 중복 접촉을 제거하고 full parent17 anatomy를 AddClothCollisionSource로 받는다.

PhysicsPIE04~08에서 검병/방패병/중검병/할버드/Apes5 family는 finite/실제 simulation·반응·body contact 및 기존 cloth45도 QA를 통과한다. PhysicsPIE08 peak는32.426/29.823/중검 upper30.800 head25.621/할버드30.265/Apes39.931도다. Yetuga178.218도는 실패이며 Main 전달 근거로 사용하지 않는다. ProjectionBound01/02와 nonlinear 전체 Stability trial은 품질 실패 기록으로 보존한다. alpha1은 철회하고 current player Hair profile + Torso alpha0.8로 복원했다. Yetuga의 single-bone tuft는 머리→attachment 거리를 hair 길이로 쓰지 않도록 FurSupport01에서 실제 skin AABB 길이를 사용한다(예 Hair14:88.627→52.621cm, mass0.177253→0.105242kg). Yetuga만 nonlinear angular solver 적용 FurSolver01 후 fresh PhysicsPIE09를 검증 중이다. 변경은 원작 직접 수치라고 표현하지 않는다.

NoContactControl01~03은 source/body contact 분리 진단용이며 비활성 접촉 설정을 package에 저장하지 않았다. Source36/variant 및 original shape17/17/16 capsule 근거는 기존 report를 재사용한다. debugger session/agent breakpoint 정리 및 user exceptions 보존 완료다. PrivateBuild13은 foreign UBT writer 공유 실패로 unique -Log로 해결했고 foreign build mutex는 기다렸다. PrivateBuild18의 native Saved 검사 TSubclassOf 타입 오류는 도구 오류이며 PrivateBuild19/20 성공으로 보완했다. 최신 Main Source126개를 다시 intake했고 변경은 기존 modular BeginPlay block 하나다. 별도 editor만 사용한다.

정확한 재개: PhysicsPIE09 Driver/Runtime 실제 결과 확인 → 실패면 Yetuga worst bone·stage·rendered_joint_peak와 Saved 검사에서 실제 scale/inertia/contact geometry를 표적 검토(다른5 family 보존) → flag 없는 saved + 실제6종 PIE/RHI 및 PlayerAttackCollision 회귀 → current Main/source/assets SHA/CAS 검증 → 선택97 package/runtime1/DEV1 전달·Main build/새 loader/PIE 확인 → 완료 기록. full Author/구 metadata export/Player 전체 author/FPS/root/VFX author 재실행 금지. PreparedVerification은 실제 품질 통과 후에만 true로 만든다.

<!-- MonsterSecondaryPhysics_20261013_quality09 -->

## 2026-10-13 — ARCH-98 private 렌더링/부착 원인 확인, Main 반영 전

정확 상태는 Metadata/GiantVFX_20261013/ResumeState.json이다. WorkBuild05는 canonical private module cf9e5199…088db/exit0이다. MainBeforeAudit01→WorkAudit02의84 sequence는 raw model T3D SHA·root/FPS/settings·원래 event/notify export가 모두 같고 original object gameplay fields도 보존했다. 실제 사용 renderer의 null mesh/material0이다. 신규 private 리소스는 original field PS2와 FModel mesh2, 두 종 전용 PS/material copies다. WorkPatterns01은 실제 grant/GAS/perception callback 8개 기술 + 투석/필드3개를 통과했지만 당시 필드 화면은 미완료였고 기술 통과를 품질 승인으로 해석하지 않는다.

LLDB own PID2200에서 SkillObject.Tick:245 GameThread의 Age.5, core emitter alive3/size(.602,.644,.663)/local Z-200.48, parent world(400,0,10110)와 FX world(800,0,20120)를 직접 확인했다. 새 private state-FX attachment의 absolute→relative 전환을 attach 이후에 하여 부모 좌표가 이중 합산된 문제였으며 순서를 수정했다. raw engine/PDB 상위 stack은 미해결이고 확인된 stack top/value만 FieldDebuggerEvidence.json에 기록했다. agent breakpoint 제거/own debug session STOP, user exception8 상태를 보존했다. 중단 영향 Debug01은 생산 검증이 아니다.

SnowStone01은 remaining world snow sprite leaves를 source density/PC alpha의 bounded shader로 연결하고 Apes 투석의 ice horn 대신 원래 burst/motion+3D rock mesh/별도 lit stone을 사용했다. 표시 TEMP 및 원작 shader 미복구를 Art 정본에 구분한다. 현재 WorkAll02 owned20716/155case review가 진행 중이며 아직 Main 게임 source/asset write0이다. header comment-only edit가 running source hash에 영향을 주었으므로 최종 Main 검증은 fresh canonical build 뒤 진행한다. DeliveryPlan은8 source(DEV1 포함)/86 changed asset/100 new reachable dependencies이며 compare-and-swap gate를 통과했다. exact 재개는 ResumeState를 따르며 완료한 author, 준비, Root/FPS/전체 원작 import 또는 stale DLL 전달을 반복하지 않는다.

## 2026-10-13 — Main 선택 전달 완료 / 최종 Main 검증 대기

97 package(PA35/SK35/post-process20/Elite CopyPose1/기존 BP6) + 기존 KZMonster.cpp의 파츠 초기화 block1 + DEV 검증1의99행을 SHA/CAS로 Main에 전달했다. 새 runtime class/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. 최신 Source126 intake와 보호된 Player/Config/기타 Source를 보존했다. MainBuild01을 별도로 실행 중이며 완료 기록은 아직 아니다.

PrivateFinalQA02 fresh saved/RHI의 실제6 family 모두 finite/실제 simulation·반응·접촉/45도 envelope 통과, PlayerAttackCollision 회귀 Success다. 실제 peak: 검병29.073/방패29.836/중검 upper30.802 head25.621/할버드32.513/Apes39.391/Yetuga37.864도. PrivateFinalQA01의 Yetuga cloth49.669도 실패를 보존하고 cloth 관성만 보완했다. 최종317 simulated 설정이며 Yetuga37 single-bone fur +4 cloth는 모두 활성 상태다. 현재 정상 actor 전체 world ragdoll은 off다.

일반19 post-process는 ComponentSpace, Yetuga1은 WorldSpace다. Yetuga의 짧은 털은 source player spring784/damping56/8·8·3도/몸 damping0.1·1.5를 유지하되 hard angular limit·exact solver·실제 dominant skin tip 반경0.5cm 접촉을 적용했다. 원래 고정점에서 겹치는 몸 proxy pair는 분리했고 나머지 몸 접촉은 유지한다. 피부 support uniform-box와 pivot parallel-axis를 합산한 virtual inertia + 어시스턴트 TEMP 배율2를 사용한다. 큰 cloth4에도 기존 관성 TEMP2를 적용했다. 이는 사용자 지정/원작 직접 수치가 아니며 PA의 InertiaTensorScale에 저장된 기술적 안정화다. 원작 metadata50 anatomy capsule만 직접 출처이며 feel은 기존 Player TEMP 재사용이다.

실패한 broad nonlinear/alpha1/soft limit/geometry 후보와 compile/link 도구 오류는 모두 report에 보존했다. FurActual02 실제 body inertia·velocity·PA hard flags를 관측했다. ParticleConstraints count0은 immediate mode에서 등록하지 않는 engine 경로의 값이므로 관절 미생성 증거로 해석하지 않는다. 제약 존재/정확 engine 내부 cause·원작 전체 physics parity와 모든 skin triangle 관통0은 단정하지 않는다.

재개: MainBuild01 Exit/UBT Result 확인 → owned process 목록 확인 → main_commandlet MainSaved01(verify_monster_physics_main_saved_20261013.py, 저장0) → main_rhi MainFinalQA01에서 MonsterSecondaryPhysics.PIE/PlayerAttackCollision.PIE 실제2검사(별도 owned process) → 99SHA/actual module/보호 파일 확인 → 완료 MD/ResumeState 기록. PreparedVerification.json은 실제 PrivateFinalQA02의3검사/6 PNG/원본 Source/99SHA 검증으로 true다. full Author/과거 PA/FPS/root/VFX 재추출·재임포트·private DLL 전달은 반복하지 않는다.

<!-- MonsterSecondaryPhysics_20261013_delivered_pending_main -->


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset / 천·Hair Main 완료

사용자 요청을 Main에 적용했다. imported SK35 전부 PA35를 연결했고, explicit cloth/hair가 있는20 메시에는 engine RigidBody post-process, 중검병3 모듈에는 shared CopyPose1을 연결했다. 기존 gameplay BP6와 SK35 수정, 신규 PA35/ABP21의97 package + 기존 KZMonster.BeginPlay 파츠 block1 + DEV 검증1의99행을 exact SHA/CAS로 전달했다. 신규 runtime class/file/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. protected Player/Config/기타 Source SHA 차이0이다. 기존 GAS/AI/Ability/피해·몽타주·root motion·VFX 소유자는 유지한다.

MainBuild01 Exit0, MainSaved02 저장0·35 링크/게임플레이 파츠 연결, MainFinalQA01 실제6 family 이동→방향 전환→authored attack section 모션→피격→회복·finite/물리 반응/몸 접촉/중검 CopyPose 및 PlayerAttackCollision 회귀2검사 Success다. 실제 loaded canonical Main module SHA와99 target SHA는 `Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json`이다. 최종 실제 peak: Swordsman:29.93° / SwordShield:29.18° / HeavySwordsman:30.80°,25.62° / HalberdElite:30.26° / ApesStoneHandElite:39.39° / Yetuga:37.86°. 정상 캐릭터 전체 world ragdoll은 off이고 engine post-process가 보조 뼈317개의 수명/취소/EndPlay를 소유한다. 테스트 floor/camera/fixture와 검사 settings는 별도 owned process에서만 사용했고 map/asset 저장0, user/foreign editor 제어0이다.

수치/형상 출처: Human Adult17/Elite17/Halberd16 원작 anatomy capsule은 OriginalAnatomyShapes.json의 package/export field/raw Center·Rotation·Radius·Length/SHA다. 해당 reference bone에만 사용하고 source NoCollision policy는 몸 접촉 목적의 활성 collision으로 변경했다. 그 외 anatomy는 실제 LOD0 dominant skin AABB에서 계산했다. feel은 현재 Player_Original_Hair/Torso_RigidBody_PhysicsAsset의 player TEMP spring/damping/각도/몸 damping·반경·mass-per-length와24/4/4·1/60을 재사용한 것이다. source original physics 전체 동일값으로 기록하지 않는다.

일반19 post-process는 unit enemy ComponentSpace, Yetuga1은 WorldSpace다. Yetuga37 짧은 털의 source784/56·8/8/3도·0.1/1.5·0.5cm는 유지하고 hard angular bounds/exact solver/실제 dominant skin tip sphere를 사용했다. skin uniform-box + pivot parallel-axis virtual inertia와 어시스턴트 TEMP 배율2로 과한 뒤집힘을 줄였고 큰 cloth4는 기존 virtual inertia TEMP2를 적용했다. 근거/수식/원시 support와 각 저장 값은 위 final report의 sources 및 saved native report다. 원래 고정점에서 겹치는 anatomy proxy pairs는 분리하고 그 외 몸 접촉을 유지한다. PA editor의 DefaultInstance.InertiaTensorScale, constraints의 spring/damping/limits/collision을 조정 위치로 사용한다. 새 gameplay tuning literal/runtime settings owner는 추가하지 않았다.

PrivateFinalQA01 Yetuga cloth49.67° 실패는 geometry/숫자를 바꾸지 않고 QA를 느슨하게 통과시킨 것이 아니다. cloth 관성만 보완한 PrivateFinalQA02의 fresh saved/RHI/gameplay3검사와 Main 최종 검증으로 대체한다. 이전 broad nonlinear/alpha1/geometry/soft limit 및 도구 compile/link 실패는 보존했다. ParticleConstraints count0은 immediate-mode의 등록 경로 차이이므로 관절 미생성으로 확정하지 않는다. debugger session/agent breakpoint는 정리하고 user exception 상태는 유지했다.

필수 잔여0이다. 현재 gameplay6 family runtime 검증과 그 외 저장 library variants 설정을 구분한다. 전체 source-game physics parity/모든 skin 삼각형 관통0/network/shipping은 검증하지 않았다. 후속은 이 완료 → final evidence → 대상 PA의 설정만 표적 확인한다. full author/메타데이터 전수 추출/원본 재임포트/Player 전체 author/FPS/root/VFX 재실행·옛 DLL 전달은 하지 않는다. 앞선 Main 미반영/검증 대기 절은 이 완료로 대체한다.

<!-- MonsterSecondaryPhysics_20261013_main_complete -->

## 2026-10-13 — GiantVFX 검수 중단 지점 재개

GiantVFX는 Main 미반영이다. private WorkBuild07의 module8e56cac7…152b3f4 / WorkQuality01(114case342PNG) / WorkFocus01(16case48PNG) 기술 검사 통과와 실제 검은 Yetuga 눈먼지·Roar axis 시각 실패를 구분한다. Field SetAbsolute-before-attach 수정은 실제 runtime debugger와 화면에서 확인했다. LOD2 구재질 원인 추정은 actual material pointer 및 LODAudit01에 의해 철회했고 DustDiagnosisCorrection.json에 보존했다.

정확한 재개: RendererIsolationRHI01의 Launch/Exit/Driver 및 8 emitter PNG → 검정 branch 원인 수정 → 기술 axis 저장 후 fresh 확인 → focused RHI/actual GAS patterns → fresh saved preservation84 및 의존 closure → 최신 Main KZMonster.cpp의 완료된 SecondaryPhysics block을 보존해 작은 merge → delivery CAS·Main stock build·Main fresh RHI/PlayerAttackCollision. 기존 delivery script는 WorkAudit03와 옛 quality gates를 사용하므로 그대로 apply하지 않는다. Main 게임 파일 write0. 전수 author/import/root/FPS/별도 physics 재실행 및 private DLL 전달을 하지 않는다. metadata의 최신 ResumeState.json을 현재 재개 포인터로 사용한다.

## 2026-10-13 — GiantVFX Main 선택 반영 / Main 새 빌드 검증 대기

WorkBuild09 current private module4da21e21…fdf41dd, WorkFocusFinal03 16case/48PNG, WorkPatternsFinal01 actual GAS8+object3/취소, WorkAuditFinal03 원본 raw/settings/event84 및 기존 object gameplay fields 보존·enabled 모든 LOD null binding0가 통과했다. private 시각 검수는 PrivateVisualReview.json의 documented limits와 함께 수락했다. 범용 manager/class/runtime file 추가0, source7runtime+기존DEVtest1이다.

MainDelivery.json의 source8/기존asset86/새reachable102 =196 파일만 backup+SHA/CAS로 반영했다. KZMonster.cpp는 최신 Main의 완료된 secondary physics 초기화 전체를 보존하고 VFX scale 한 줄만 병합했다. private DLL/manifest/Config/맵/공용 소재/Player source 전달0이다. 현재 MainBuild01 owned12716 실행 중이며 아직 Main 검증 완료가 아니다.

재개: MainBuild01 Exit/UBT Result → MainSaved01 read-only saved audit/Preservation84 → MainAll01 all155 실제 RHI/PNG → MainPatterns01 GAS8 및 object3 → MainCollision01 Khazan.Combat.PlayerAttackCollision.PIE → 실제 Main module/196 target/보호 Source SHA → FinalVerification·도메인 MD 완료 기록. 완료된 author/메타데이터 전수/원본 재추출/Root/FPS 또는 delivery apply를 반복하지 않는다. 자세한 시각/TEMP/원작 미확인 경계는 Art/GIANT_VFX_REFINEMENT_20261013.md 최신 절이다.

## 2026-10-13 — Main UHT timestamp 오류 수정 / 재빌드

MainBuild01은 exit6/GENERATED_BODY C4430 실패다. 전달에 copy2를 사용해 reflected header의 private 수정 시간이 Main의 최근 UHT 완료 시간보다 오래된 상태로 들어갔고, UHT가 skip되어 새 struct line175/201/218 macro와 SpawnEffect 등이 생성되지 않았다. generated.h와 build log로 source-obvious 원인을 확인했다. MainHeaderTimestampRepair.json은 SHA가 일치하는 전달 Source8만 LastWriteTimeUtc를 현재로 갱신한 기록이며 소스 내용 수정0이다. 후속 delivery script에는 Source touch를 추가했다. MainBuild02는 UHT가 실제 재실행되어 새 line175 macro와 SpawnEffect property 생성이 확인됐으며 현재 실행 중이다. MainBuild01 실패를 성공으로 덮어쓰지 않는다. 나머지 재개 절차는 이전 절과 같고 MainBuild02 결과부터 진행한다.


## 2026-10-13 ? ???? ?? VFX ?? ?? / ?? ?

Router ? Architecture/Migration ? Heal ?? ??? ???? ?? ?? ??? ????. ? runtime class/component/manager/tag0, ?? Heal? notify callback?? Action feedback receipt? ????. ?? SB_Kazan_Recovery.UpperAnim=AC_Kazan_Recovery? ??5?? native11 bone adapter? ????? current Heal/Stow/HP/weapon/input/audio ??? ??? ????. cooked Niagara ??/VM shader graph ???? ??? ?? source mesh3/texture FT_Trail/G density/ShaderLUT? source effect ???? native Cascade? ?????. ?? TEMP/skin sampling ??? ?? ????.

Main ?? Source/asset ??0??. ??? ??/??/?? ??? Metadata/HealVFX_20261013/ResumeState.json, ???? Khazan_HealVFXWork_20261013??. WorkBuild01 ??, Author03 ??? ?? ??, fresh Saved/?? RHI/??/??/?? Main ??? ???. ?? editor/???? ???? ???. ?? ????? ??????? VFX/physics/FPS/root author? ???? ???.


## 2026-10-13 ? ?? VFX Main ??/??/?? ??, ?? Main ?? ?

15 target(runtime1/?? DEV1/asset13)? exact SHA/CAS? byte backup?? Main? ????. protected Source/Config/?? Heal?Draw ??0, private DLL/Config ??0??. MainBuild01 exit0/22.04s, MainSaved01 ??0??? notify/GUID/clock ?11bone/22 paired child? ????. ?? MainFinalPIE01? ?? owned editor?? ?? ??? ?? Main ?? ?? ??? ???. ?? source5 role/mesh3/FT_Trail.G/ShaderLUT? ???soft alpha TEMP? ??? ?? ??? PrivatePolished01??. ?? ??? ??? Metadata/HealVFX_20261013/ResumeState.json: MainFinalPIE01 Driver/Exit???PNG ?? ?15SHA/loaded DLL/???? ??? ??. ??? author/??/physics/root/FPS/?? VFX/old DLL? ???? ???.


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery?5 effect role/core?burst???????light flash? ?? Heal/Stow ??? ????. source raw LinkValue+?? Stow offset/rate? ???? ?? HP/InputEnd/weapon/??/?? ??/FPS/root/audio? ????. runtime1/?? DEV1/asset13(??12+?? Heal Montage1)?15 ??? exact SHA/CAS? ????. ? runtime file/class/component/manager/tag0, private DLL/Config/Build ??0, ?? 133 ?? SHA ??0??. ? Source? Main?? canonical build??.

MainBuild01 exit0/22.04s, MainSaved01 save0??? notify/GUID/?? ?11bone/22pair, MainFinalPIE01 ?? Khazan.Heal.PIE/Khazan.Combat.PlayerAttackCollision.PIE Success?. ??11 child emit?parent bone?finite values/HP????????? ?????/???UnPossess cleanup? ???? actual loaded canonical DLL SHA? 39ab3b029cc36dd7c78213f55fc2e22446110268952cbd932571a6a96488a46d?. shader errors0/pixel instructions179?189?207, Main ?? Core1.3667s/hand burst1.9667s ??? energy/continuous edge? ????. missing ParticleSprites/MeshParticles usage ?? default fallback warning0??. ?? editor/???/??/??? owned process fixture, package/map ??0, ???/foreign editor ??0??.

Source mesh3/FT_Trail.G/ShaderLUT?source numeric? clock ??/TEMP? PLAYER_HEAL_VFX_SOURCE_20261013.md? ????. cooked Niagara/VM/material/WPO graph ???? ?? native Cascade? ??? ????? original skin sampling/light/full shader/pixel ????? camera/Shipping/network/??? ???? ???. ExposureCompensation1/EmissiveGain8/feather0.04???1.25px/DepthFade8cm ?? ????? TEMP?. Source Dilation1.3497161s? ?? raw Heal1.4666667s? ???? ??? retime?? ???. ?? ??/???? ???? ?? ?? ? Main ???? ????.

?? ??0. ?? evidence? Metadata/HealVFX_20261013/FinalVerification.json, ResumeState.json, Changes.patch?. ??? ?? ???current /Game/HealVFX/Materials?Particles ? Heal marker? ?? ????. ?? full author/?? ??/?? ????/?? VFX?physics/root/FPS ?? private DLL ??? ???? ???. ?? ??/???/?? ??? ? ??? ????.

## 2026-10-13 — PlayerReceivedHitVFXRemoval 완료·후속 기준

Main Player Definition의 HitReactions.ImpactEffect=None을 저장했고 exported 기타 필드 동일/보호 공유3asset SHA 동일이다. Main build/새 프로세스 Native02의17사례·실제피격5에서 수신자 추가효과0·HP/ST/패링 보존이 통과했다. 완료/백업/loaded module/실패 증거는 Metadata/PlayerReceivedHitVFXRemoval_20261013/FinalVerification.json 및 Apply02의 Before asset을 따른다. Apply01의 default-field export 처리 오류와 Native01의 중복 PIE driver 실패는 해결되어 보존한다. 필수 프로젝트 잔여0이다. 사용자의 기존 editor cache는 API 연결이 없어 갱신 여부 미확인이다. 해당 세션에서 효과가 남으면 Player Definition만 Reload하며 공유 PS/Guard GA/몬스터 혈액을 삭제하지 않는다. 이미 완료한 apply/build/전체 VFX author를 반복하지 않는다. 재검증이 필요한 새 변경이 생겼을 때만 Scripts/Engineering/player_received_hit_vfx_task_20261013.py에 새 label과 rhi를 주어 자기 프로세스를 실행한다. 공식 Python remote discovery node0/foreign editor 제어0이다.

<!-- PlayerReceivedHitVFXRemoval_20261013_complete -->

## 2026-10-13 — Notion 보고 완료·후속 갱신 기준

NotionProgress_20261013는 complete/remaining0이다. 일일21개 생성·12개 보완, 주간6개 및 프로젝트4/업무7의 필수내용·관계·이미지·53페이지 readback과 날짜 공백/중복0을 확인했다. 확인자료가 없는11일은 미확인이다. 현재 주간: https://app.notion.com/p/3f8ec99d2c54819e92aeffcad36b4b57?pvs=204

이 작업은 기록 작성이며 runtime/Content/Config 변경·새 build/PIE0이다. GiantVFX/사운드/패링 광막/방패병 후속의 게임 완료 상태를 이 Notion 완료와 혼동하지 않는다. 다음은 Router→필요한 최신 domain/evidence→현재 Notion rows/content→해당 날짜 append/관계 보완→readback. 기존 날짜/스크린샷을 중복 생성하거나 과거 author/import/old DLL 전달을 반복하지 않는다. 정확 ID/현재 문서/검증은 Metadata/NotionProgress_20261013/FinalVerification.json과 ResumeState.json이다.

<!-- NotionProgress_20261013_report_backfill_complete -->


## 2026-10-13 — ARCH-95 OverFury 추가 Slash 철회·나머지 무기 궤적 정렬 착수

사용자 직접 수정 요청이다. OverFury의 KZWeaponSlash17 start/end쌍만 제거하고 원작 notify/효과·입력/피해/시간축은 보존한다. 나머지 추가 Slash는 공유 KZ_Slash asset을 유지하며 기존 Action receipt의 GT finalized pose/cleanup에서 실제 장착 grip/칼끝·무기 reach를 사용해 링 끝점/크기/스윙면을 검증한다. 새로운 runtime class/file/manager/tag0이다. actor-space pose가 빼던 몸통 회전과 bounding-centre 앵커의 차이를 실제 여러 프레임/시점에서 먼저 관측한다. 새 gameplay 튜닝값이 아니라 현재 Fab mesh radius100/diameter200cm·renderer yaw180 및 실제 무기 geometry의 변환/계산이다.

Main source/asset 수정0, fresh 별도 Khazan_PlayerSlashWork_20261013의 source/config/binary 사본·Content hardlink 중 6target montage는 링크를 끊어 안전하게 분리했다. Probe01 saved/export은 passed. 현재 baseline DEV 계측 build와 그 뒤 before RHI 진행 단계다. 정확 재개는 Metadata/PlayerSlashAlignment_20261013/ResumeState.json. 기존 source VFX/피해/오디오/Physics/FPS/Parry·다른 작업은 보존하며 full reauthor/reimport나 외부 editor 제어를 하지 않는다.


## 2026-10-13T12:06:39+09:00 — ARCH-89 SFX coverage·natural tail 작은 확장

현재 직접 요청은 Player와 인간형4종의 모든 현행 action/interaction을 대상으로 한다. 기존 ASC/Ability/Task/피해·Guard/Dodge 승인·Animation ownership를 유지한다. 새로운 runtime class/file/component/manager/tick0이다. 기존 PlayAudio Notify의 optional VolumeMultiplier(default1)와 PreserveFiniteTailOnOwnerDestroyed(defaultfalse)를 추가했다. per-source bank gain 위에 asset-authored TEMP trim을 곱하고, 적용한 finite one-shot만 actor destroy 후 자연 drain한다. loops/명시 stop은 이전 cleanup을 유지한다. EndSound도 같은 정책/볼륨을 소비한다. defaults는 scope 밖 giant 기존 data를 보존한다. 엔진 AudioComponent::OnUnregister는 owner destruction의 one-shot에 bStopWhenOwnerDestroyed=false를 지원하고 BeginDestroy는 loop만 stop한다는 source 근거를 확인했다.

임시 voice0.85/footstep0.90/weapon1은 숫자 출처를 PlaybackPlan01 profile에 모았으며 원작 gain과 구분한다. 아직 실제 믹서 조정/완료 검증이 아니다. 이후 현재5 family data에만 적용하고 peak/tails/combination/cancel/loop/death output으로 조정한다. 이전 미전달37 DataAsset bytes를 복사하지 않고 최신 Main에서 audio field만 수정하여 StrongVictimFront/Root/FPS/physics/VFX·Parry 후속을 보존한다. source3 수정·build 진행/새 asset0이며 exact resume는 Metadata/HumanoidSFX_20261013/ResumeState01.json과 Art 같은 날짜 절이다. 사용자·foreign editor 제어0이다.


## 2026-10-13T12:35:17.064758+09:00 ? ARCH-95 Slash geometry Main ??, ?? ??

MainApply01?? ?? ?? SHA? ?? ??? ? ActionAbility.cpp/h, CombatEffect notify.cpp, ?? DEV CombatEffectPIETest.cpp? montage6? atomic ????. Source runtime ?? class/file/tag0, ?? ASC ??0, private DLL ??0??. ?? Ability receipt? finalized-pose history? world tip?actor translation?? ??? body/root yaw? ???? ?? blade-tip?projected grip radius? ???. Niagara initial yaw90/XYscale2? renderer yaw180? ??? addon yaw90/span400cm ? component ScaleLerp0? ????. ??? ?? asset? ?? metadata/????? ?? gameplay ?????? ???? ???.

?? private SavedWork04?? original1359 objects?37 fields/clock/GUID, addon33?/Over0? ????. FinalRHI02?18+Brutal5, ?? ?? hit/??/? avatar ??? Success?? ?? GPU70 samples/17 non-Fury nodes? endpoint ?? ??0.000031cm ? rendered radial-axis? ????.216 game screenshots ? ?? ??????/?? ??? ????. ? component-only AfterRHI01 ??? GPU ?? ????? ?? ?? ???? ?? ???. NativeGPUBefore01?250?318cm? ?? private ?? ??? ?? GPU ???? ?? Main ?? ???? ???? ???.

?? MainBuild01 PID4480/session70310 ?? ?. Metadata/PlayerSlashAlignment_20261013/ResumeState.json ? MainApply01/Applied.json?? ????. build ?? ? main_commandlet SavedMain01 verify_saved_player_slash_alignment_20261013.py ? main_rhi MainRHI01 player_slash_alignment_driver_20261013.py (INSPECT/REQUIRE_ENDPOINT/GPU_PROBE/REQUIRE_GPU_ENDPOINT=1, PREVIEW_ONLY=0) ? PlayerAttackCollision.PIE ??. ?? editor ??/?? author ?? ???/?? KZ_Slash ??? ?? ???.

## 2026-10-13 — ARCH-95 패링 카메라 적용 / 광막 외관 검증 진행 중

Main 기존 KZGuardAbility에 ParryCameraShake 설정1개와 성공 분기의 local controller ClientStartCameraShake 호출만 추가했다. 엔진의 finite camera modifier가 만료를 소유하며 새 runtime class/component/tag는 없다. 원작 Just_L xxCameraMod_Shake의 duration .35907653s, fade .17953826s, LocY -100 × FinalScale .1=-10cm, FOV 3 × .1=.3deg, frequency 원시25/offsetzero를 LegacyCameraShake로 어댑트했다. 원작 R별 동일값 및 원작 camera stack/frame parity는 미확인이다.

Build01/Native05에서 실제 UnrealEditor-Khazan-731302.dll(SHA ea04f8fb53e38febb566692fb76baa910ef188818b2ad6a7f3145be8a2b9805f)로 패링17상황·성공 전용 카메라·실제 FOV 변화·만료·피격 VFX 제거 유지가 통과했다. `Metadata/ParryPhoto_20261013`과 Art continuity가 정확한 에셋/화면 상태를 기록한다. 외관은 미완료이며 Native06은 cold shader 영향을 분리하는 검사다. C++ gameplay 판정·비용·창·HP를 바꾸지 않았다. 모든 기록은 실제 적용/빌드/판정 검사와 외관 합격을 구분한다. 재개는 Native06 확인 후 로컬 Art 후보만 표적 보정하고 최신 실제 RHI/저장 검증을 결속한다. 기존 사용자/동시 작업 Source·에셋과 과거 증거를 보존한다.


## 2026-10-13T12:57:55.018345+09:00 ? GiantVFX ?? ?? ?? ?? ????? ??

GiantVFX? Main 196?? ?? ??? MainBuild02, MainSaved02 ??84, ??155case/GAS8?objects3/?? ??? ????. Grab mesh ?? ??1PS? MainGrabFixed01? ?? ???? ????. MainRefractionFixed01? ?? ??? ???? Armageddon_Jump_End? ? ?? ?? ??. ?? FinalVerification? passed=true? ?? ??? ?? ???? ?? ????. ?? ??? Metadata/GiantVFX_20261013/ResumeState.json ? MainRefractionFixed01/013_Attack_Armageddon_Jump_End_01.png? ?? ??? ????. ?? ????? ?? refraction MI3 ????? ????? ???? ???. ?? author/delivery/?? DLL ??? ???? ?? ?? PlayerSlash?Heal?Parry?SFX? ????.


## 2026-10-13T12:58:40.411493+09:00 — GiantVFX 재개 기록 인코딩 보완·시각 미완료

앞의 12:57:55 추가 절은 PowerShell 표준입력 인코딩 때문에 문자가 손상됐다. 원문 기록은 보존한다. GiantVFX Main 선택 반영196 및 build/saved84/actual155/GAS8·objects3/충돌 기술 검사는 통과했다. Grab mesh 1PS 후속은 실제 MainGrabFixed01 화면에서 확인했다. 그러나 MainRefractionFixed01의 Armageddon_Jump_End 흰 판은 미해결이다. FinalVerification의 전체 passed=true를 false로 정정하고 technical_passed=true 및 visual_status=pending_armageddon_white_plane로 분리했다. 정확 재개는 Metadata/GiantVFX_20261013/ResumeState.json 및 MainRefractionFixed01/013_Attack_Armageddon_Jump_End_01.png의 실제 소유자 확인이다. 최신 PlayerSlash·Heal·Parry·SFX를 보존한다. 전체 author/delivery/과거 DLL 전달을 반복하지 않는다.


## 2026-10-13T13:13:52.789080+09:00 — PlayerSlashAlignment 정확 재개 검증 완료

PlayerSlashAlignment 재개 검증을 완료했다. 이미 반영된 runtime3/DEV1/몽타주6의 SHA를 확인하고 새 Main SavedMain02/실제 MainRHI02 GPU70·17공격·216화면 및 ResumeCollision01 충돌16(Spin7/Fury19, 끝/취소 접근0)을 통과했다. 각 실행의 실제 DLL과 SHA를 별도로 결속했고 동시 build로 모듈 목록이 바뀐 MainCollisionRHI03 시작 실패를 숨기지 않았다. 해당 own13088만 종료하고 actual-loaded-module 어댑터로 재검증했다. Source/Config/공유 VFX를 추가 수정하지 않았다. Saved의1359 objects×37 fields/clock/GUID를 보존했다. 최신 정확 정본은 Metadata/PlayerSlashAlignment_20261013/ResumeVerification.json 및 ResumeState.json이며 기존 author/전체 전달/old DLL 복사는 반복하지 않는다. 별도 GiantVFX 시각 잔여와 이 요청 완료를 구분한다.


## 2026-10-13T13:18:40.096195+09:00 — PlayerSlashAlignment 완료·12:35 기록 인코딩 보완

앞의 12:35:17 추가 절은 PowerShell native pipe 인코딩으로 한글이 손상됐다. 기존 기록을 보존하며 이 절과 FinalVerification.json을 정본으로 사용한다. Main 적용은 ActionAbility.cpp/h·CombatEffect notify.cpp·기존 DEV CombatEffectPIETest.cpp와 montage6이다. runtime 새 파일/class/manager/tag0, ASC/피해/콜라이더 변경0. OverFury17쌍 제거, 나머지33쌍 유지 및 actual tip/world sweep(translation만 제외)/effective radius·particle initial rotation90/XYscale2+renderer180 보정을 완료했다. data yaw90/span400/location0 및 component ScaleLerp0은 현 asset 근거의 변환/계산이며 원작 gameplay 숫자가 아니다.

Main saved original1359×37/clocks/GUID, full player18+Brutal5/actual hit/cancel·두 avatar, 실제 GPU70 samples/17 nodes 및 공중 Spin, native collision16/Spin7·Fury19를 확인했다. 병행 Source와 새 suffix module은 보존하고 MainRHI04ComposedPreview로 재검증했다. Blueprint/assets/현재 소스에서 시작하며 기존 author/full reimport/old private DLL 전달을 반복하지 않는다. exact evidence·최종 loaded module은 Metadata/PlayerSlashAlignment_20261013/FinalVerification.json과 ResumeState.json. 이번 요청의 필수 잔여0.

별도 진단: MainCollisionRHI01/Editor.log의 M_Parry_Distortion 및 MI_FMI_fluid_A_162(GuardParry/PlayerParry/Reference)는 TextureSampleParameter2D Linear Color와 FT_PerlinNoise_RG의 Color 기대가 불일치하여 PCD3D_SM6 fallback을 기록했다. native collider Success와 엄격한 editor driver failed를 분리한다. 다른 Parry 작업이 진행 중이므로 이번에 해당 parent/texture를 건드리지 않았다. Parry 담당은 현재 candidate와 기존 metadata를 먼저 확인하고 sampler/texture 색공간 계약을 표적 수정 후 shader/RHI를 확인한다.

<!-- PlayerSlashAlignment_20261013_complete -->

## 2026-10-13 — PlayerSlashAlignment 최종 결속 보충

기존 완료 기록과 실패 진단은 보존한다. 병행 재개 검증의 Metadata/PlayerSlashAlignment_20261013/ResumeVerification.json에서 새 Main SavedMain02, 실제 MainRHI02의 GPU70·17공격·216화면 및 ResumeCollision01의 충돌16(Spin7/Fury19)이 모두 passed이며 후속 collision material compile failures는0이다. 과거 MainCollisionRHI01의 Parry sampler 실패를 삭제하거나 합격으로 바꾸지 않는다. 최신 suffix2026101353의 대표 약공격4/실제 GPU도 MainRHI04ComposedPreview에서 passed다. 이전 composed 전체 반복의300초 fixture timeout은 별도 실패로 보존했다.

현재 전달된 runtime3/DEV1/몽타주6 SHA는 두 완료 receipt와 일치한다. 병행 SFX/Parry/Giant Source·에셋·build를 보존했다. 정확한 최종 근거는 CompletionEvidenceIndex.json → FinalVerification.json 및 ResumeVerification.json이며 요청의 필수 잔여0이다. 과거 author/전체 재전달/private DLL 복사를 반복하지 않는다.

## 2026-10-13T13:36:48+09:00 — ARCH-89 SFX 실행·검증 후속, Main 완료 전

기존 Notify의 optional volume/finite-owner-tail3 source 변경과 기존 approved hit/Guard/Dodge owner를 유지한다. 기존 DEV Audio PIE에 환경 sample plan·범위 밖 giant projectile 제외·모든 예상 cue 관측·AT 실제 owner destroy 후 finite ActiveSound 유지와 PCM tail 검사를 추가했다. Dodge 성공 QA는 합성음 파일명 하드코딩 대신 실제 authored SuccessSound property를 관측한다. protected Python Notifies 수정 실패 때문에 기존 DEV Audio Editor에 class2-only clear/no-save command를 추가했다. 새 runtime class/file/component/manager/tick0이며 Source3 외의 실행 구조 확장은 없다. 현재 Source와 Root/FPS/physics/VictimFront·Slash/Parry·Player 피격 VFX 제거를 보존하고 Main 최신 파일에서 audio field만 수정한다.

사본에서527sequence/35combo/8Dodge BP를 실제 저장했고 fresh audit는 기존 중복 contact 문제를 발견하여 후속 재검증 중이다. Main의 독립 RHI 프로세스 파일 잠금에는 제어/종료를 하지 않았다. 원작으로 표시한 bank/clock과 TEMP mix/callback adapter, 준비/저장/실제 QA/Main 완료를 구분한다. 정확한 Build04 이후 재개와 남은 절차는 Metadata/HumanoidSFX_20261013/ResumeState02.json에 있다. 아직 완료가 아니다.


## 2026-10-13T13:50:50.382128+09:00 — GiantVFX 흰 투영의 비파티클 원인 분리

GiantVFX 재개: latest MainSavedResume01 raw/root/FPS/notify/objectgameplay84 보존 및 allLOD null0 통과. 최신 플레이어 추가 Slash factory 변경은 사용자 승인 MainApply01/ResumeVerification의23c27… hash로 보존했고 나머지195 Giant target은 일치한다. 단독 Armageddon3에서는 흰 판이 없지만 연속23에서 재현된다. ShockRendererIsolation01(MI3 required를 메모리에서 숨김)과 AllParticleHideIsolation01(모든 PSC 숨김)에서도 흰 바닥 strip/몸체 투영이 남았다. 파티클/LOD/MI3 원인 가설은 철회한다. 현재 exact resume는 Metadata/GiantVFX_20261013/ResumeState.json, 다음 DecalHideIsolation01의 실제 경로/material/location/size와 PNG 비교다. owner 미확정, game source/asset 추가 수정0이며 모든 agent BP를 제거하고 사용자 baseline8/활성5를 유지했다.

## 2026-10-13 — 패링 사진 후속 최신 재개 지점

현재 구현·검증 영수증은 Metadata/ParryPhoto_20261013/CurrentVerification.json이다. 최신 native14/Shader02는 passed이며 정확한 원작 외관은 unverified다. 저장된 후보는 Reference 폴더17+GuardGA1, 명시적 CPU halo slot/life .2s/source growth22/extent125cm/halo intensity4, 별도 PNO distortion/IOR .06/relative-age fade다. Player received-hit None와 공유 공격/혈액 SHA는 보존됐다. SourceCameraShake는 성공 분기에 연결돼17상황/FOV/만료를 통과했다. 전체 original source/실제/임시 수치와 실패 증거는 Art PLAYER_PARRY_SOURCE/Engineering PARRY_IMPLEMENTATION 최신 절에 분리 기록했다.

마지막 asset 저장은 CPUHalo03이며 Extent01의 원본 X250 복원은 error32로 적용0이다. Native13/14와 Isolate02에서 경계 없는 glow/arc를 보았으나 broad violet halo의 실제 DevMap 가독성은 사진보다 약하고 HeinMach 비교는 아직 없다. 다음은 (1) 현재 module manifest가 가리키는 DLL 존재와 다른 editor 잠금/현재 asset SHA 확인, (2) 실제 HeinMach 전투 camera에서 현재 Guard 성공을 캡처하고 광막 mask·밝기·footprint·occlusion을 비교, (3) 필요 시 현재 로컬 M_Parry_Halo/CPU size만 표적 보정. source X250을 그대로 CPU equal axes에 쓰려면 잠금 해제 후 set_parry_photo_source_extent_20261013.py를 새 immutable label로 실행하고 반드시 fresh native/RHI로 검증. 현재125cm를 원작 확인값으로 표현하지 않는다. (4) 굴절만 켠 checker/background 비교는 최신 preview emitter-name 필터(ParryPhotoHalo 포함)를 사용. Isolate02 refraction-only는 오염돼 proof 불가, (5) 최신 camera/17 native/saved shader 검증과 실제 결과를 문서에 추가한다. 원작 shader 자료가 없으면 pixel 동일성은 계속 미확인이다.

다른 Main 작업이 source/manifest를 계속 바꾸므로 오래된 DLL/Blueprint/공유 material 또는 전체 author를 덮어쓰지 않는다. 다른 user/foreign editor를 임의 종료하지 않는다. 정확한 원작 외관이 확인되지 않은 상태를 완료로 기록하지 않는다.


## 2026-10-13T14:14:46+09:00 — ARCH-89 current humanoid·Player SFX Main 완료

실행 상태/승인은 기존 ASC/Ability/Task·attack hit group/Guard/Dodge가 소유하고 표현은 기존 PlayAudio Notify를 재사용한다. runtime Source3에 optional VolumeMultiplier(default1), finite owner-tail(defaultfalse)와 EndSound 동일 정책만 확장했다. 해당5family authored Notify만 finite tail을 보존하며 scope 밖 default/giant data는 이전 계약을 유지한다. Body impact는 수신자 Definition, 무기 impact/Guard는 현재 attack window, 회피 성공은 기존 TryAvoidHit once-per-execution이 소유한다. 같은 성공 SFX를 Suc pose에서 또 재생하지 않는다. 새 runtime class/file/component/manager/tick0이다.

기존 DEV Audio Editor에 protected Python array 대신 audio class2-only clear/no-save command, Audio PIE에 sample-plan/actual cue coverage/owner destroy tail, Dodge QA에 실제 authored SuccessSound reflection만 추가했다. build01–04 성공, 현재 Main final saved1682/527/174/8/238cue, full fresh pose/root/curve/FPS/nonaudio notify/GUID 보존 및 실제78 mixer·메인 melee/Guard/Parry17/Dodge11이 passed다. Source/자산/검증 hash·실패/버전은 Metadata/HumanoidSFX_20261013/FinalVerification.json 정본이다. 실제 핵심 root/FPS/physics/VictimFront·Parry/Slash/피격 VFX 제거 변경을 유지했고 기존37prepared bytes를 덮어쓰지 않았다.

유한음은 owner destroy/몬타주 취소 후 자연 drain, loops/명시 source stop만 fade하며 새 shared mutable notify state나 MainAnimInstance member/timer를 만들지 않는다. source 수치/계산과 명시 TEMP .85/.9/1/.08s 및 측정 기반 parry cue.5·미직렬화72callback first-pose adapter를 구분한다. 원작 DSP/sample/frame 전체 동일·Shipping·전 장치 청취는 별도 검증 범위다. 필수 잔여0이며 사용자 editor·foreign process 제어0, 현재 완료를 이전 pending37/locked/prepared 기록보다 우선한다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

GiantVFX ARCH-98 재개 작업의 현재 구현/검수를 완료했다. Main198 distinct target(Source8/changedasset86/newasset104)의 SHA를 최종 전달 및 승인된 PlayerSlash source receipt에 맞춰 확인했다. MainSavedSnowDecal01의 original84/raw/root/FPS/event/원래 object gameplay, allLOD null0, MainSnowDecalFinal01 연속23/69실제화면, MainArmageddonGASFinal01 실제grant·perception·Armageddon·cancel cleanup이 통과했다. 현재 실제 모듈 SHA7d57bd17…9462592이며 각 이전 실행은 별도 실제 DLL/SHA로 결속한다. no private DLL/Config/Map 전달이며 이번 재개 gameSource 수정0이다. 흰 판은 Armageddon_Start가 남긴 단일 deferred decal였고 파티클/LOD 원인 가설은 제어 실험으로 철회했다. 전용 parent/MI2와 기존 notify DecalMaterial 한 필드만 후속 적용했다. 모든 agent BP/session 제거, 사용자 baseline8/활성5 보존. 최신 PlayerSlash/Heal/Parry/SFX/physics의 현재 Main을 보존했다. 정확 정본은 Metadata/GiantVFX_20261013/FinalVerification.json 및 ResumeState.json(status=complete_current_implementation_and_review/remaining0). 과거 finalize_giant_vfx의 old-source 가정, full author/delivery/root/FPS/import/old DLL 복사는 반복하지 않는다. 원작 cooked shader/pixel 완전 일치와 Shipping/stress/모든 프레임 검증은 완료로 표현하지 않는다.

## 2026-10-13 — WeakAttack01 사용자 사진 후속 방향·전방 확대 착수

사용자 사진에서 첫 약공격의 두 효과 방향이 어긋나고 하나가 몸에 붙는 문제가 확인됐다. 앞선 SlashAlignment의 축/GPU 끝점 합격만으로 이 장면의 실제 밝은 궤적 방향을 합격 처리한 판단은 부족했으며 이번 시각 수정의 완료 근거로 사용하지 않는다. 기존 기록은 보존한다.

현재 소유 범위는 WeakAttack01의 KZFX_bab7be8e310a56b59c0b9461 원래 PlaneSlash와 KZWeaponSlash 추가 효과의 start/end4 객체, 기존 Action receipt/Notify 설명 및 기존 DEV 검수다. 새 runtime class/file/component/manager/tag0이다. 공유 Niagara/mesh/material은 읽기만 한다. Metadata/WeakAttack01Slash_20261013/Before 및 Baseline.json에 실제 이전 파일을 보존하고 Khazan_WeakSlashWork_20261013에서 별도 editor로 작업한다. RuntimeMainApplied.json의 기존 Source3(실행1/설명1/DEV1) 작은 변경만 Main에 적용했고 asset0, 빌드 진행 중이다. 양수 scale·zero offset의 다른 공격 동작은 그대로다. 음향/패링/거대 VFX 작업과 외부 editor를 제어하지 않는다.

후보는 음수 X scale로 radial UV/head를 반사하며 대응 끝점을 선택하고 기존 RelativeLocation을 avatar-local cm로 소비하는 방식이다. 첫 타격 전방35cm/평면 크기1.15배는 사용자 요청에 따른 TEMP 시각 튜닝이며 원작 직접 수치가 아니다. 이 후보는 아직 실제 시각 검증/최종 asset 반영 완료가 아니다. MeshProbe01의 두 Mesh OBJ/UV와 source PlaneSlash를 표적 조회했다. BeforeComposed01은 실제 baseline 성공이나 사진의 문제를 해소했다는 증거가 아니다. 원래 효과 단독 진단01은 생성 문자열 문법 오류,02는 TextureExporterTGA의 unsupported texture assertion으로 실패했고 제품 asset 저장0이다. 해당 own process만 종료/자연 crash 종료했으며 texture exporter는 진단에서 제거했다.

정확 재개: MainBuild01 결과→새 Main module을 별도 작업본에 가져옴→original-only 재생으로 두 효과 식별→author_weak_attack01_slash_20261013.py 후보를 task-private montage에 적용→세 시점/초기·중기·후기 실제 장면과 signed GPU endpoint·forward offset 확인→최신 Main asset의 audio 등 병행 변경을 보존한 선택 반영→fresh saved/Main 실제 RHI→완료 기록. 개인 에디터를 재사용하거나 과거 montage6/full author/private DLL을 Main에 복사하지 않는다.

## 2026-10-13T15:06:26.891782+09:00 — ARCH-95 Sequencer 기반 공격 Niagara 편집 계약 착수

사용자 직접 구현 지시다. 코드의 수치/방향 보정을 계속 덧붙이는 대신 LevelSequence를 편집 원본으로 사용하고, editor 적용 명령이 Niagara별 Transform 곡선과 Life Cycle 창을 기존 CombatEffect notify에 저장한다. runtime은 기존 Action receipt/GT finalized pose·MontageInstance 검증/정상·취소·사망·EndPlay cleanup을 재사용한다. 사용자가 편집해 적용한 효과는 weapon-sweep 자동 계산을 우회하며 avatar-local cm / Euler degrees / dimensionless scale / montage seconds 계약을 사용한다. 원래 source 효과/오디오/피해/판정/애니메이션 포즈·Root·FPS는 보존한다. 새 runtime class/component/manager/tag는 만들지 않는다. 기존 notify에 optional editor-authored transform channels와 editor-only apply API만 추가할 계획이며, Python editor menu/LevelSequence 엔진 도구로 시각 편집을 제공한다. 불필요한 매게임 LevelSequence player/character animation override는 사용하지 않는다.

WeakAttack02 수동 offset 작업은 이 편집 workflow 요청으로 대체됐다. 이전 Before02은 기존 배치의 실제 관측만 passed이며 위치 수정/후보 적용0이다. 메뉴·Sequence·데이터 apply·fresh native 비교 완료 전에는 구현 완료로 기록하지 않는다. 정확 재개/실패/프로세스는 Metadata/CombatVFXSequencer_20261013/ResumeState.json을 따른다. 새 수치가 필요한 경우 원작/현재 asset geometry/TEMP를 구분한다.

## 2026-10-13 — ARCH-95 WeakAttack01 방향·전방 표현 Main 완료

사용자 사진의 반대 방향 Slash를 수정했다. 월드 좌표로 재생하는 원래 PlaneSlash의 CorrectionBoneName=Weapon_L을 추가 Slash의 공격 손으로 해석한 이전 author 휴리스틱이 원인이다. 실제 첫 약공격의 0.35→0.40초 포즈에서 Weapon_L 쪽 FX tip은 위로 회수되고 Weapon_R 쪽은 우측 위에서 좌측 아래로 이동한다. 이는 현재 실제 포즈 관측이며 원작 실행 코드의 확인으로 표현하지 않는다. 정확한 데이터·근거는 Metadata/WeakAttack01Slash_20261013/CuttingHandEvidence.json과 EquippedGeometryObservation.json이다. addon SourceField의 기존 L 문구는 초기 생성 이력이며 현행 Near/Tip 설정과 이번 override를 우선한다.

AM_DAS_WeakAttackCombo의 첫 KZFX_bab7be8e310a56b59c0b9461 및 KZWeaponSlash start/end4 객체만 변경했다. 추가 효과 Near/Tip을 FX_R_Sword_02/01로 바꾸어 실제 내려베는 Weapon_R을 따른다. 기존 RelativeLocation을 Action finalized-pose receipt에서 avatar-local cm로 더하는 작은 계산만 추가했다. 양수 scale/zero offset의 나머지 공격과 기존 수명/취소 cleanup은 유지한다. 새 runtime 파일/class/component/manager/tag0이며 실행 Source1/Notify 설명1/기존 DEV1/asset1이다. 중간 음수 scale 반전 후보는 시각 실패로 철회했고 관련 product 코드도 제거했다.

전방35cm·평면 크기1.15배는 요청한 전방 확대를 위한 TEMP이며 원작 직접값이 아니다. 에디터에서 첫 notify child의 RelativeLocation/Scale3D로 조정한다. 최신 Main montage 사본에 선택 저작하고 전체 직렬화 diff를 검사한 뒤 SHA CAS/atomic replace로 반영했다. Main SavedMain01은 FinalAuthor01 전체 export와 완전히 동일하다. notify clock/GUID·다른 효과와 오디오/HP/ST/피해/콜라이더/Physics 및 다른 montage5는 보존한다.

MainBuild04 성공, 실제 MainRHI01의18 natural node·Brutal4/실제 승인 HP110→100·두 avatar/조건부 효과·정상 종료/취소 및 실제 GPU70개·17공격은 성공했다. 세 actor-relative 시점·초기/중기/후기 장면289개를 검수했고, MainYaw90RHI01에서 actor를90도 회전시킨 첫 약공격도 성공했다. 각 프로세스의 실제 DLL df9764361d10eec695f0855e34b0dacfb98da06138303a1c8db17cbd7a1f0ed3를 결속했다. GPU 최대0.000031cm는 reference marker+명시된35cm offset에 대한 검수 오차이며 실제 메시 vertex와 완전 일치라는 뜻이 아니다. 현재 Imperial_R tip과 가상 marker의 가장 가까운 vertex 차13.147cm 및 원작 shader/pixel parity 미확인 경계를 보고서에 명시했다.

정본은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json, 재개는 ResumeState.json이다. 필수 잔여0, own editor0, 외부 editor 제어0이다. 실패한 TGA/NullRHI FBX export·문자열 진단·mirror 후보 및 중단한 private 전체 build는 보존한다. 이후 현재 Main Source/first4 객체에서 시작하고 stale private Source/DLL·전체6 montage author·mirror 후보를 전달하지 않는다. 앞선 SlashAlignment의 축/GPU 합격이 사용자 사진의 반대 방향을 해소했다는 판단은 이번 actual hand/시각 검증으로 대체한다.

<!-- WeakAttack01Slash_20261013_complete -->
### 2026-10-13 — WeakAttack01 최종 영수증의 병행 Source 경계

최종 영수증 생성 시 별도 WeakAttack02 Sequencer 작업이 공유 CombatEffect Notify header와 기존 DEV 검수를 추가 수정한 것을 확인했다. 해당 변경을 덮어쓰거나 그 editor(PID19948/WeakAttack02Slash Before03)를 제어하지 않았다. 본 작업의 Action.cpp/Weak montage SHA는 실제 검증 snapshot과 동일하고 avatar-local offset 설명/expected-offset 검사도 보존됐다. FinalVerification.json은 실제 MainBuild04 및 MainRHI01/MainYaw90RHI01의 loaded DLL df9764361d10eec695f0855e34b0dacfb98da06138303a1c8db17cbd7a1f0ed3에 결속하며, 이후 별도 Sequencer 기능까지 본 작업에서 build/검증했다고 표현하지 않는다. CurrentVerification의 pending-yaw 상태는 FinalVerification/ResumeState의 완료로 대체됐으며 WeakAttack01 필수 잔여0이다.
## 2026-10-13 — Apes/Yetuga 일반 피격 가산 표현 작업 중

요청: 일반 피격이 공격/AI를 취소하지 않고 현재 포즈에 움찔하는 delta를 더할 것. 마지막 검증: 별도 Work commandlet Probe01이 두 Definition/ABP 및 기존 0.733333s Normal_D_F full-pose clip을 확인, 두 원본 CS의 super-armour/stamina 및 PartDestruction 원시 필드를 저장했다. 아직 게임 Source/asset 적용·build·PIE 미완료. 실패 원인은 현재 공통 HitReaction Ability의 PreActivate Action cancel, Input block 및 StopMovementImmediately다. 진행 경로: 원본 full-pose를 보존한 additive 복사본8 → 독립 Slot Group2/ABP2 → Definition pool2 → Character 직접 표현/수명 정리 및 AI 실제 action montage 참조 → fresh Main build module의 별도 Work PIE → CAS asset 전달/fresh Main 확인. 작업 root C:/Users/user/Desktop/GitProject/Khazan_GiantHitOverlayWork_20261013/Khazan, reports Metadata/GiantHitOverlay_20261013, 실행 Scripts/Engineering/giant_hit_overlay_task_20261013.py. 재개는 ResumeState.json/OriginalConditions.json/Probe01/SavedProbe.json부터 읽고 외부 editor/process를 조작하지 않는다. Source/Animation/Notifies/KZAnimNotify_CombatEffect 및 기존 Tests/KZCombatEffectPIETest의 동시 WeakAttack02 수정은 이 작업 범위가 아니다.


<!-- CombatVFXSequencer_20261013_Continuity -->
## 2026-10-13 18:10 KST — 시퀀서 공격 VFX 편집 경로 후속 검증 위치

Main 적용·빌드·실제 공격 검증은 완료됐다. 목표 파일은 Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h/.cpp, Source/Khazan/Ability/KZActionAbility.cpp, Content/Python/kz_combat_vfx_sequencer.py, Content/Tools/CombatVFX/LS_DAS_Player_WeakAttack02_VFX.uasset, 현재 Main WeakAttackCombo 몽타주다. 마지막 저장 검증은 Metadata/CombatVFXSequencer_20261013/FreshSavedPIE01/Driver.json, FreshSavedReadback.json, IndependentTransformComparison.json: exit0, 실제 효과 35프레임, 편집 곡선 오차 0.00013 cm 이하. MainApply01/SavedScopeAudit.json은 기존 116 GUID 보존과 새 2개만 확인했다. 테스트 임시 조정은 저장하지 않았다.

남은 시각 검증: 자동 오프스크린 에디터 캡처 EditorVisualMiddle09 및 EditorPlayingPreview12에서 Niagara Actor 기즈모와 Active/DesiredAge는 보이나 Slash 입자 형상은 뚜렷하지 않다. 대화형 UE 에디터에서 /Game/Tools/CombatVFX/LS_DAS_Player_WeakAttack02_VFX를 열고 Niagara compile 후 효과 Life Cycle 0.193708~0.676667초 구간을 재생·스크럽하여 실제 픽셀을 확인한다. 보이지 않으면 Niagara component renderer 상태/particle count, stock 시스템의 editor preview, User parameter/DI curve 전달을 표적 확인한다. 소스 하드코딩 offset 또는 공유 KZ_Slash 자산 수정을 근거 없이 반복하지 않는다. Metadata/CombatVFXSequencer_20261013/ResumeState.json을 재개 시작점으로 사용한다. 다른 작업의 Main montage/Source/DLL을 덮어쓰지 않는다.


<!-- CombatVFXSequencer_20261013_VisualResolved -->
## 2026-10-13 18:31 KST — 시퀀서 미리보기 후속 해결

앞 절에서 남겨 둔 오프스크린 미리보기 Slash 형상 미확인은 해결됐다. Metadata/CombatVFXSequencer_20261013/EditorAutoVisual18/PlayingPreview.png는 실제 재생 중 붉은 Slash를 보이고, EditorScrubVisual19/Before.png와 After.png는 정지 프레임 Additive 50cm QA 편집의 시각적 이동을 보인다. ScrubVisualReport.json은 actor X 이동 50.0cm, saved false, exit0을 기록한다. 현재 메인 적용과 실제 공격은 MainApply01 및 FreshSavedPIE01 증거가 정본이다. 이어서 다른 공격을 편집할 때는 Tools → Khazan VFX에서 선택한 애니메이션을 열고 기존 효과의 정적 시작 배치와 montage segment를 확인한 뒤 Apply한다. 이전 Visual 미확인 문단은 당시 상태 기록으로 보존한다.

## 2026-10-13 — Apes/Yetuga 비중단 피격 검증 완료, Main 에셋 잠금 대기

마지막 성공: 별도 Work `CPU02/Driver.json` Success 및 native25조건(2 giant×12, human1). 실제 HP/ST GE 피해, 진행 중인 같은 공격 Ability/ASC montage/instance 시간 연속성, 4방향 additive pose, Short/Knockback/Launch/VictimFront/None, 반복, ST0 Exhaustion, HP0 Death, UnPossessed/EndPlay와 outgoing crossfade 정리를 확인했다. RHI02는 giant22 실제 동작/화면을 확보했으나 human fixture 초기 액션 충돌로 전체 test Fail이다. RHI03은 동시 렌더 부하 watchdog으로 일부만 완료했다. 이후 테스트 fixture를 지면에 배치하고 spawn 이후 시작한 액션을 자극 직전에 정리했으며 CPU02 25개가 모두 성공했다. 이 조정은 development fixture만 변경했다.

Source runtime 기존6 파일 + Editor-only Build.cs dependency 및 DEV helper2가 Main에 이미 적용됐다. stock Build03/04/06 성공 기록이 있고, 최종 Source/object compile은 이후 Main 기본 DLL mapping 때문에 Link만 LNK1104다. 기존 process를 reload하지 않으려고 최종 stock Main linker response의 OUT/PDB만 독립 output으로 바꿔 MainObjectsLink10에서 link exit0, DLL sha bd16ea80453fa880e46cff39b0ca42962ad24d58e26074de2f8b657b7995aad6 및 실제 Work loaded module을 확인했다. Private DLL을 Main source build로 위장하지 않았다. 자세한 계약/원작 특별 경직은 GIANT_NONINTERRUPTING_HIT_20261013.md와 OriginalConditions.json이다.

남은 작업: DeliveryPlan22 Main CAS publish → fresh Main CPU/저장 readback → FinalVerification/완료 기록. 실패 원인은 Main interactive editor PID30156가 `DA_Character_ApesStoneHandElite.uasset` 등 파일을 share-delete 없이 열어 둔 Windows 잠금이다. os.replace WinError5, FileRenameInfoEx/Posix WinError32. 강제로 handle/process를 닫거나 shared hardlink를 in-place truncate하지 않았다. 실제 첫 asset 교체도 실패했으므로 Main asset 22개는 모두 미적용이다. `.uasset.GiantHitDelivery` 첫 temp만 hash가 맞는 상태로 준비돼 있다. 무관한 Source/에디터를 건드리지 않았다. 사용자에게 Main 저장/닫음을 async로 요청했다. 잘못 시작한 owned MainCPU01 PID8280만 확인 후 종료했으며 유효한 검증으로 집계하지 않는다.

정확한 재개: 사용자가 Main을 저장/종료한 뒤 현재 process와 대상 파일의 baseline hash를 확인한다. `Scripts/Engineering/deliver_giant_hit_overlay_20261013.py`에서 기존 첫 temp를 hash 확인 후 재사용하도록 적용해 실행한다. 원본 Main SHA는 AssetBaseline.json/DeliveryPlan.json. 모든 target AbsolutePath가 Main/Content 안이고 Work/new copied file은 단독 inode임을 유지한다. CPU02에서 실제 검증한 MainObjectsLink10 DLL을 Main 별도 alias로 전달/manifest CAS한다. fresh Main hidden NullRHI process를 giant_hit_overlay_task의 main_asset_editor, mode nullrhi, test Khazan.GiantHit.PIE로 실행한다. 마지막 검증은 Source/asset hash와 original16 유지 및 저장 파일의 pool/group/no-root-motion/frame/FPS를 확인한다. 완료 전 Main editor 반영 완료라고 기록하지 않는다.

## 2026-10-13 — Apes/Yetuga 피격 작업 재개 및 완료

사용자의 Main editor 종료 후 파일 잠금이 해소됐다. 중단 지점의 첫 임시 에셋을 hash 검사해 재사용하고 나머지 대상과 함께 22/22 Main 에셋을 반영했다. Main-object DLL도 별도 이름으로 전달했다. fresh Main `MainCPU02` 실제 로드 DLL SHA 일치, PIE 25/25 및 종료 코드 0, Source 6/6·원본 16/16 hash 보존을 확인했다. `ResumeState.json`은 `complete_main_verified`, `remaining=[]`로 갱신했다. 최종 정본은 `Metadata/GiantHitOverlay_20261013/FinalVerification.json` 및 `Docs/Engineering/GIANT_NONINTERRUPTING_HIT_20261013.md`. 이 작업의 중단 사유와 재개 절차는 해결된 과거 기록으로 남긴다.

## 2026-10-13 패링 피드백 가시성 후속 재개 지점
Main GuardAbility.h/.cpp, Guard GA, 전용 화면 재질 저장 및 HeinCameraBuild03/HeinCameraRHI03 통과를 VisibilityFollowupVerification.json의 hash/실제 DLL로 확인했다. 패링 17건과 카메라 활성·FOV/위치 변화·만료, 화면 volume 성공 한정·만료 확인. 초기 보고의 생성 여부 검사만으로 화면 가시성을 완료라고 판단한 것은 부정확했다. 후속은 Art continuity의 원작 광막 외관 비교를 처리하고 일반 플레이어 HeinMach 카메라에서 재촬영한다. KZAnimNotify_CombatEffect.cpp 수정, 범용 camera manager 신설, 이전 QA DLL 복원은 필요하지 않다. 새로운 pixel-accurate 원작 shader 근거가 확보되기 전에는 현행 임시 배율을 원작값으로 설명하지 않는다.

## 2026-10-13 — Apes·Yetuga 잡기·Armageddon Main 완료 범위와 정확 재개 지점

최신 완료 범위: `Metadata/GiantGrabs_20261013/FinalVerificationVisualRepair.json`에서 Main/Work 8 asset·13 Source SHA 일치, 저장 검증 각42항목, DevMap Main NullRHI·RHI `Khazan.GiantFall.PIE` 각각13패턴 성공이다. 실제 별도 Main module을 로드했고 Rider 실행 에디터는 사용하지 않았다. `VisualRepairDelivery.json`의 2 C++·2 Yetuga GA만 후속 전달했고 직전본은 `BeforeVisualRepair`에 있다. 실제 사용자 플레이/원작 영상 프레임 일대일 검수는 수행하지 않았다. Main을 열어 둔 사용자의 에디터에는 이전 로드 객체가 남을 수 있으므로, 사용자 미저장 작업을 먼저 보존하고 해당 네 grab GA와 두 monster pattern data asset을 재로드한 뒤 직접 확인해야 한다.

남은 원작 동등성 항목은 Apes `Dodge_A` passive 선택 원본 조건(현재 weight1/0~400cm 임시), FastBall 정확 mesh, 원본 `FallDown` PhysicsAsset 및 HoldAttachComponent 흔들림, Armageddon 원본 피해·offset 해석, 0.1초 Dodge 원본 길이, 전체 Apes/Yetuga 행동 전이의 영상 비교다. 현재 runtime의 잡기 부착·해제/후속·Tackle 차단·착지 판정이 통과했다는 사실과 위 미확인 항목을 구별한다. 재개는 Router→Architecture v2/Migration의 현재 단계→`APES_YETUGA_FALL_IMPLEMENTATION_20261011.md` 최신 절→최종 receipt/`AuthoringPlan.json` 표적 row 순으로 시작한다. 두 chunk의 필요한 원본 asset만 추출하거나 원본 영상 시간을 측정하고, 현행 Source·BP SHA와 사용자 편집 상태를 비교한 다음 독립 Work/숨김 editor에서 작은 수정 및 Main CAS 전달, 저장 readback42와 RHI PIE13을 반복한다. 불필요한 새 manager/FSM이나 전체 animation 재임포트는 재개 절차가 아니다.

## 2026-10-13 Apes·Yetuga 이동 단계 전환 후속 완료/재개

`KZMonsterPatternAbility.cpp` 한 파일에서 `EnterPatternNode`의 새 이동 window 등록을 기존 다음 Tick 대기에서 전환 직후로 앞당겼다. Main 이전 SHA `7651D58D...`는 `Metadata/GiantGrabs_20261013/BeforeImmediateMove`에 보존했고 최종 SHA는 `99DD8EB2...`다. Work/Main UE5.8 Editor 빌드와 별도 숨김 NullRHI DevMap `Khazan.GiantFall.PIE` 13 fixture 각각 Success, Main actual DLL 경로 확인. `ImmediateMoveVerification.json`에서 직전 receipt의 21 파일 중 이 Source만 SHA가 달라지고 나머지 20개가 동일함을 확인했다. 129 node/118 clip 감사와 source blend 일치는 Art 정본 및 해당 Engineering 구현 문서 하단에 분리 기록했다.

남은 원작 동일성 작업은 실제 발생하는 끊김 프레임을 좁혀 동일 카메라의 원작 자료·actor/socket 시간축을 비교하는 것이다. 즉시 이동 등록은 코드상 가능한 추가 CMC 프레임 공백을 제거한 것이며 전체129 전이의 visual continuity 성공 측정은 아니다. 다음 작업은 Router → Architecture v2/Migration 현재 단계 → `APES_YETUGA_FALL_IMPLEMENTATION_20261011.md` 최신 절 → 두 audit/receipt → 대상 전이만 RHI 측정 순서로 한다. 기존 asset을 일괄 root repair/retime하지 않는다. 사용자 Rider editor에는 손대지 않았다.

2026-10-13 최종 RHI 추가: 즉시 이동 등록이 반영된 Main 숨김 D3D12 editor의 DevMap 패턴 13사례 Success, exit 0. 로그·DLL 경로는 `ImmediateMoveVerification.json`에 보존했다. 원작 전체 화면 비교 미실시라는 경계는 그대로다.

2026-10-13 표적 원본 추출 보충: `SourceAssetTrace.json`에 두 pak의 기본 Player PhysicsAsset와 HoldSpine2 별도 PhysicsAsset의 raw/SHA·shape 개수를 기록했다. `ECommonPhysicsAsset::FallDown`→HoldSpine2 직접 매핑은 확인되지 않았고 Apes COI의 정확 visual mesh property도 없다. 현재 검증된 손·몸통 고정/애니메이션 경로를 근거 없이 물리로 교체하지 않는다. 게임 에셋 변경0이며 C++/PIE 최신 성공은 `ImmediateMoveVerification.json`을 따른다.

## 2026-10-13T23:23+09:00 — ARCH-89 Apes·Yetuga SFX 기존 실행 경로 보수 및 검증

기존 `KZAnimNotify_PlayAudio`/`KZAnimNotifyState_PlayAudio`가 애니메이션 음향 실행·유한 꼬리/상태 종료를, `KZComboActionAbility`가 승인된 공격/Guard 결과를, `KZMonsterSkillObject`가 FastBall 비행·충돌 종료를 계속 소유한다. 사용자가 지목한 `KZAnimNotify_CombatEffect.cpp`는 VFX 경로이며 이번 SFX 결손의 수정 위치가 아니다. 새 gameplay runtime 파일/class/manager/상태0, 효과/입력/피해/AI 계산은 변경하지 않았다. 기존 두 giant `DA_OriginalPatterns_*`의 Audio field만 최신 Main에서 고쳐 GuardSound 294창·4 object와 비행음2를 연결하고 비오디오 필드를 보존했다. 기존 수신자 `DA_Character_*` impact는 변경하지 않았다.

기존 DEV `Khazan.Audio.PIE`가 sample plan에서 저장 montage+section을 선택할 수 있게 작은 선택 경로만 추가했다. 시퀀스 단독 dynamic montage에서 초반 Notify가 첫 업데이트 안에 묻혀 실패한 진단은 `EarlyCueDiagnosticRHI03/04/06`, `MainExtendedAudioRHI01`에 보존했다. 브랜칭 포인트의 transient 실험은 초반 재생 호출을 증명했지만 transient montage ensure를 일으켜 제품 수정을 채택하지 않았다. `bCanBeFilteredViaRequest=false` 실험도 실패했다. 반대로 실제 Pattern Definition이 참조하는 저장 montage의 Apes Dodge/Turn/JustGuard/Roar 및 Apes·Yetuga 12패턴은 `SavedGiantActionFourRHI01`, `SavedGiantPatternsRHI01`에서 expected cue가 모두 관측됐다. 실제 `FinalMainAudioRHI01`은 26 sample(거인22/Player4), cancel2, projectile2, PCM 무음0/클리핑0, native Success; `MainGiantSavedAuditFinal`은 701 source event/212 sequence 및 294+4+2 bind 결손0이다. Player/인간형의 이전 78 mixer/실제 Guard·Parry·공격 테스트는 `Metadata/HumanoidSFX_20261013/FinalVerification.json` 근거를 재사용한다. Main module SHA와 두 asset SHA, 원본 backup·scope·미검증은 `Metadata/GiantSFX_20261013/FinalVerification.json`에 고정했다.

Swordsman Ballista animation의 cue 자체는 단독 PIE 재생을 확인했으나 Source에서 상자/문/발리스타 월드 상호작용 owner·호출이 발견되지 않았다. 오브젝트 상호작용 gameplay 및 그때의 SFX 완료를 의미하지 않는다. 모든 701 cue의 실제 각 action/연속 전이 및 Wwise 글로벌 RTPC/DSP 완전 재현은 미검증이다. 현재 SFX 재개 시 Router→Architecture v2/ARCH-89→Migration 최신 단계→Art의 같은 날짜 절/FinalVerification→해당 원본 row와 현재 Main Source/에셋을 표적 비교한다. 새 월드 상호작용이 구현되면 해당 결과 owner에서 음향 호출을 붙이고 실제 사용·취소·종료 RHI를 검증한다. 시퀀스 단독 fixture의 실패를 근거로 저장 패턴 시간을 일괄 변경하지 않는다.

## 2026-10-14T00:13+09:00 — 플레이어 일반 적중음과 브루탈 치명 사망 수정

사용자 청취 지적을 따라 Player Combo 60창의 공통 `SC_efx_pc_dualaxesword_com_impact`와 대상 Definition의 재질별 `SC_efx_pc_enemy_hit_*`가 승인 적중마다 겹치는 것을 확인했다. `KZComboActionAbility`의 기존 적중 지점에서 Player의 해당 exact cue만 재생을 억제한다. 다른 Window ImpactSound·Monster 공격/Guard·브루탈 전용 audio/anim notify와 body hit은 건드리지 않았다. 기존 `KZAnimNotify_CombatEffect.cpp`는 VFX 소유자여서 수정하지 않았다. Main Combo 에셋은 현재 외부 에디터 잠금으로 원본 SHA `0dbdfd3f…`/60bind를 유지한다. Audio 필드만 비운 수정본 `Saved/ImportReports/GameplayAudio_20261011/PlayerImpactReview_20261013/Prepared/Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset`은 fresh readback에서 26node·60창·비오디오 필드 동일/중복0으로 검증했다. 기존 사용자 에디터/외부 프로세스를 종료·제어하지 않았다.

`KZExhaustionAbility::FinishDeath`는 완료된 치명 브루탈의 Damage2 포즈를 바로 얼리던 경로 대신 기존 짝 정리 후 Monster 사망 몽타주를 실행한다. 기존 DEV `KZCombatPresentationPIETest`는 실제 사망 몽타주 재생·terminal pose·화면 캡처를 검사하도록 확장했다. stock build는 열린 메인 DLL 잠금으로 link 실패했으며 소스 컴파일 오류가 아니다. 별도 suffix build `UnrealEditor-Khazan-2026101401.dll` 성공; 새 프로세스 Main DevMap에서 치명 front/back 6종12/12·사망 최종화면12, 일반 사망 정상/중단12/12, PlayerAttackCollision 실제 믹서 성공을 확인했다. 오디오 장치에서 재질 body hit 양성/중복 common impact 0, PCM peak0.24237/clipping0이다. 브루탈 terminal pose 최대 오차 4.55e-13 model cm는 저장 사망 asset과의 비교이며 원작 게임 프레임별 동일성 검증은 아니다.

정본은 `Metadata/PlayerImpactSFX_20261013/FinalVerification.json`; 작업 결과 상태는 **새 모듈 런타임 구현·검증 완료, Main DataAsset 정리 및 기존 열린 에디터 로드 대기**다. 재개 순서: 사용자 에디터가 정상 종료되어 파일 잠금이 해제된 뒤 Main Combo 에셋 현재 SHA를 `Author02/PlayerImpactReview.json.before_sha256`과 비교한다. 일치하면 준비본을 선택 반영하고 fresh 60창/non-audio readback, exact-cue 임시 runtime 분기 제거, build/PlayerAttackCollision audio/브루탈12·일반사망12를 다시 확인한다. SHA가 다르면 최신 Main을 다시 읽어 Audio 필드만 병합한다. 기존 열린 에디터는 구 모듈을 유지하므로 사용자가 저장 후 정상 재시작해야 새 실행 경로를 볼 수 있다.

## 2026-10-14 — JustGuard 원본 후처리·메인 Guard 연결 검증, 시간축 정합 잔여

현재 Main의 UKZGuardAbility::TryGuardHit 패링 성공 분기는 원본 CPP_PC_JustGuard_C Settings의 SceneFringeIntensity=1.5, ChromaticAberrationStartOffset=.25 및 override를 기존 일시적 APostProcessVolume에 적용한다. GA_Player_Guard.ParryImpactEffect는 PP_Player_JustGuard_Halo로 저장됐고 기존 화면 radial blur·camera shake 참조는 유지됐다. 새 runtime class/component는 없다. 실제 로드된 UnrealEditor-Khazan-2026101401.dll SHA와 GA/PS/material/source SHA는 Metadata/ParryVFXRebuild_20261013/FinalVerification.json에 있다.

마지막 검증: 새 프로세스 JustGuardMainRHI01의 저장 asset readback 및 실제 HeinMach D3D12 Khazan.Parry.PIE 17/17 통과, 테스트 asset save0. 성공 시 1회 효과와 카메라/화면 반응, 일반·실패 Guard의 전용 반응0, 만료를 확인했다. 원본 xxPostprocessVol BlendIn=.05초/BlendOut=.25초와 현행 radial volume 수명은 동일하지 않아 원본 시간축 완전 재현은 미완료다. Shipping/network/성능도 미검증이다.

재개 절차: Router→아키텍처 v2/현행 Migration→PARRY_IMPLEMENTATION 최신 절→FinalVerification.json과 현재 Main 파일 hash 확인. CPP 원본 xxPostprocessVol 타이밍을 적용할 경우 기존 Guard 성공 branch·volume의 수명 안에서 해결하고, radial blur의 별도 원본 .16745299초/.02초/.3초와 혼동하지 않는다. 기존 사용자 변경을 보존하고 격리 build→fresh saved GA readback→HeinMach D3D12 Khazan.Parry.PIE 17건 및 만료 검사를 반복한다. KZAnimNotify_CombatEffect.cpp는 범용 통로여서 이번 수정 대상이 아니다.

## 2026-10-14 03:28 KST — PlayerImpact Main 전달 재개 완료

앞선 Main Combo 에셋 잠금/임시 C++ 차단 대기는 해소됐다. 준비본 적용 전 원본 SHA 대조와 backup을 마쳤고 `KZComboActionAbility.cpp`의 정확한 common-cue 예외 분기만 제거했다. Main stock 빌드, 새 프로세스 저장 에셋 readback, 실제 오디오 믹서 PlayerAttackCollision, D3D12 브루탈 12건, 일반·중단 사망 12건 모두 성공했다. 마지막 Main DataAsset/source/표준 DLL SHA와 검증 경로는 `Metadata/MainIntegration_20261014/FinalVerification.json`. 병행 작업이 같은 표준 DLL을 이후 재빌드했으므로 이 영수증은 실제 각 런의 로드 경로 및 현재 디스크 해시를 분리해 기록한다. 이 항목의 남은 Main 전달 단계는 없다. 별도 진행 중 GiantGrabWarning/GiantCamera의 최종 완료를 이 검사에서 주장하지 않는다.


## 2026-10-14 — ARCH-99 Yetuga·Apes/패링 카메라 완료 범위와 원작 일치 잔여

현재 Main에는 UKZCombatCameraModifier와 기존 MonsterVisual notify의 카메라 분기, Guard의 원본 JustGuard 기반 카메라·내려찍기 Niagara 연결이 적용됐다. 원본 xxCameraMod_Shake 88개 중 현행 AnimSequence를 식별한 86개를 48개 저장 에셋에 넣었고, 최종 fresh readback은 원본 raw 축/주파수/배율/시간과 Guard Niagara 참조를 통과했다. 다른 잡기 작업의 최신 4개 애니메이션도 재검토해 카메라 누락0이다. 마지막 검증은 Build07 Succeeded/up to date, 실제 현재 DLL SHA 171da52aae49b500b6d3a579124c20989b73bbd6f4132f6197abe64876ec794f에서 D3D12 Khazan.GiantCamera.PIE 4개 및 Khazan.Parry.PIE 17개 Success, 테스트 저장0이다. 정확한 파일/리포트는 Metadata/GiantCamera_20261014/FinalVerification.json.

남은 원작 완전 일치 근거는 원본 xxCameraMod 실행 코드의 축 합성·거리·fade 수명, Apes CloseGrab_Success_01과 Apes/08_DashAtk 아래 AC_Yetuga_RushGrab의 현행 재생 AnimSequence 대응이다. 둘을 다른 이름의 클립에 추정 결속하지 않는다. 재개할 때 Router→CHARACTER_GAMEPLAY_ARCHITECTURE ARCH-99→MONSTER_VFX_RUNTIME 최신 절→OriginalCameraEvents.json/SavedReadback.json을 순서대로 보고, 해당 원본 package/실행 코드를 표적 확보한다. 확인한 의미·단위·시간 조건에 따라 TEMP modifier 설정만 교체하고 기존 86개 트랙을 중복 author하지 않는다. 변경 전 최신 Main asset SHA 확인·백업, 새 프로세스 readback48/86, stock build, 두 RHI PIE를 반복한다. 실제 게임 전체 카메라 체감과 network/Shipping은 추가 검증 범위다.


## Apes·Yetuga 잡기 경고 통합 검증 잔여 (2026-10-14)

저장 공격창의 `bBlockable=false`와 `KZComboActionAbility` short-circuit상 가드/패링이 호출되지 않는 것은 확인했다. 마지막 Main UE 빌드 `Metadata/GiantGrabWarning_20261014/Build02.log`, 7개 Notify 저장 재검사 `SavedReadback.json`, D3D12 전투 fixture `PIE/RuntimeReport.json` 모두 성공이다. 특정 잡기 창에 대해 실제 Guard 입력을 지속하는 플레이어의 HP·스태미너/Parry callback을 계측한 별도 PIE 사례는 아직 없다. 원본 네이티브 UI 내부 배치도 직접 확인되지 않았다.

재개 순서: `0_DOCUMENT_ROUTER.md` → `Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md` → `CHARACTER_TAG_ABILITY_MIGRATION.md`의 현행 단계 → `APES_YETUGA_FALL_IMPLEMENTATION_20261011.md` 이번 절 → `KZComboActionAbility.cpp:1344`·`KZAbilitySystemComponent.cpp:16`과 `FreshReadback.json`을 확인한다. 필요 시 기존 GiantFall/Parry fixture에 Guard held + Apes/Yetuga grab 실제 접촉 한 사례씩만 추가해 HP 감소, Guard/Parry 반응 미발생, 회피 성공 예외를 검증한다. 같은 Yetuga clip을 바꾸는 GiantCamera `OverlapMergeFinal.json`과 본 `SavedReadback.json`의 양쪽 Notify가 유지되는지도 새 프로세스에서 확인한다. 수정 후 Main 빌드와 대상 PIE를 다시 돌리고 Engineering 문서 하단에 실제 결과를 추가한다.


## 2026-10-14 — ARCH-95 Player KZ_Slash 바깥 배치 Main 검증 완료

현행 Action finalized-pose receipt에 Notify별 캐릭터→무기 tip의 지면 평면 바깥 거리만 추가했다. Main 빌드, 별도 백그라운드 메인 D3D12 `Khazan.CombatEffect.PIE`, 실제 GPU endpoint68/최대 오차0.000042cm, 저장 에셋5/원래 효과882/Notify 시간·GUID 검사가 성공했다. 마지막 실제 DLL/asset/source SHA와 백업은 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`·`MainApply/Receipt.json`이다. 작업 소유 에디터는 모두 종료했다. 후속 시각 조정은 Router→Architecture ARCH-95 최신 절→COMBAT_PRESENTATION_FOLLOWUP 최신 절→현재 Main Source/asset SHA 순으로 시작하고, 임시 숫자를 원작 근거로 격상하지 않는다. 새로운 조정 후 표준 빌드·저장 readback·실제 GPU PIE를 다시 실행한다. 원작 게임 픽셀 동일성 및 Shipping/network 성능은 별도 검증 범위다.

## 2026-10-15 — Main 반영 중단 여부 재검증 완료

현재 메인 표준 DLL은 PlayerSlashOuter의 마지막 검증 SHA와 같고 기존 PlayerImpact Source/Combo 수정도 유지된다. 오늘 stock 빌드 up to date/Succeeded 후 새 NullRHI 프로세스에서 57개 파일 SHA와 카메라·잡기 경고·Player Combo·Slash 저장 계약을 재확인해 모두 통과했다. 게임 Source/에셋 수정 및 새 RHI PIE는 없다. 통합 전달 재개 단계는 남아 있지 않으며 기존 원작 일치/Guard held 접촉 fixture의 추가 검증 한계는 유지한다. 정확한 현재 범위와 로그는 `Metadata/MainIntegration_20261015/FinalVerification.json`, `Build.log`, `SavedVerification.json`이다.

## 2026-10-15 — ARCH-95 Player KZ_Slash Main 소스·모듈 재확인

Main의 ActionAbility/CombatEffect Notify header/기존 PIE 소스 3개와 표준 `UnrealEditor-Khazan.dll`의 SHA를 마지막 실제 Main 검증본과 비교해 모두 동일함을 확인했다. 바깥 배치 계산과 Notify 설정은 Main에 유지돼 있으며 미반영 또는 중단된 전달 단계가 없다. 이전 Main 빌드·저장 readback·D3D12 PIE 성공 근거를 재사용했고, 변경이 없어 이번에는 빌드/PIE를 다시 실행하지 않았다. 게임 코드·에셋 수정0, 근거는 `Metadata/PlayerSlashOuter_20261014/ResumeVerification_20261015.json`이다.


## 2026-10-15 — 잡기 경고 Main 적용 중단분 없음 재확인

7개 경고 애니메이션과 7 capture node/12 창의 방어 불가 설정, 중복 4개 camera Notify를 새 프로세스에서 확인했다. 소스·에셋 재적용 없이 검사가 통과했고 검사 중 game asset save 0이다(`Metadata/GiantGrabWarning_20261015/SavedReadback.json`). 현재 Main 반영을 위해 재개해야 할 저장/전달/빌드 작업은 없다. 위 2026-10-14 Guard-held 별도 통합 사례는 추가 검증의 미확인 범위로 유지한다. 오늘 검사를 새로운 PIE·원작 동일성 검증으로 확대하지 않는다.


## 2026-10-15 — ARCH-99 Main 재확인 완료, 중단된 반영 작업 없음

사용자의 Main 반영/중단 여부 요청에 따라 현재 Source, 저장 애니메이션48/이벤트86 및 Guard distortion binding을 새 프로세스에서 재검사했다. 2026-10-14 완료본 asset SHA와 동일하며 Main 표준 빌드 Succeeded/up to date다. 최신 DLL SHA 6f1c6bfe41382cb6f6308130e403ce568b6b76f560e2b154707f4f9810b2d25e에서 D3D12 GiantCamera 대표4/Parry17 실제 PIE가 모두 Success, 저장 package0이다. 메인 반영 대기0이고 이번 게임 파일 변경0이다.

정확한 최신 재개 근거는 Metadata/GiantCamera_20261015/FinalVerification.json이다. 기존 구현을 중복 author/전달하거나 옛 DLL로 되돌리지 않는다. 후속 원작 완전 일치 조사는 ARCH-99 이전 절의 native camera 실행 의미와 source package2 대응 확인 범위만 남는다. 그 자료가 생기면 Router→Architecture ARCH-99→MONSTER_VFX_RUNTIME/PARRY_IMPLEMENTATION 최신 절→새 receipt/current source hash 순서로 표적 확인한다.

## 2026-10-15 — 사망 흰 원판 오류 Main 에셋 적용 / 재생 회귀 검증 진행

요청: 일부 몬스터 사망 때 바닥에 나타나는 큰 흰 원판의 원인 확인 및 오류 제거. Router → Architecture v2 → Migration → MONSTER_VFX_RUNTIME/MonsterPresentationRepair 기존 metadata 순서로 확인했다. SavedAudit.json의 18개 사망 시퀀스와 6종 CDO만 표적 검사했고 전수 재추출하지 않았다.

마지막 확정 검증: Metadata/MonsterDeathWhiteDisc_20261015/IsolationRHI01/RuntimeReport.json이 D3D12 실제 재생 18개/데칼 9개 개별 숨김 비교로 passed. D00/D02 재질 8개는 해당 컴포넌트 하나만 숨겼을 때 흰 원판이 소실된다. 정상 dirt mark 1개는 유지 대상이다. Main 사망 AnimSequence 8개의 내장 UKZAnimNotify_CombatEffect.DecalMaterial만 None으로 저장했다(Authoring.json passed, save8/source0). T3D 전체 차이는 해당 포인터만이며 Notify GUID/시각/길이와 나머지 10개 사망 패키지 SHA가 보존됐다. Backup/Content에 수정 직전 파일을 보존했다. 실패 원인 없음.

남은 작업: AfterRHI01의 새 프로세스 저장 readback + 18개 사망 실제 재생, 기존 Khazan.MonsterRepair.PIE quick visual의 6종 혈흔/ash/dissolve 회귀, 결과 문서 기록. 재개할 때 Authoring.json과 AfterRHI01/RuntimeReport.json부터 읽고 authoring을 다시 실행하지 않는다(이미 적용, 재실행 backup guard 있음). AfterRHI01이 중단됐으면 KZ_DEATH_DISC_OUT=<새 Metadata/MonsterDeathWhiteDisc_20261015/AfterRHI 폴더>, KZ_DEATH_DISC_ISOLATE=0으로 Metadata/MonsterDeathWhiteDisc_20261015/review_death_floor.py를 main UE5.8 UnrealEditor.exe -RenderOffscreen -d3d12 -ExecCmds="py <해당 절대 script 경로>"에서 실행한다. 최종 결론은 아직 재생 회귀 검증 완료가 아니다.

## 2026-10-15 — 사망 흰 원판 Main 적용 및 회귀 완료

앞의 같은 날짜 진행 중 기록을 대체하는 최종 상태: Main 사망 시퀀스 8개 저장 완료, fresh readback/전체 Notify·나머지 데이터 보존, 실제 D3D12 사망 변형18 Success/문제 흰 데칼0/정상 dirt1 유지, 기존 quick HP=0 혈흔·ash·dissolve 6종 및 경사면/접지 없음/독립 혈흔 수명 회귀 Success. shader compile/fallback 실패0. 작업 소유 editor는 종료했고 미완료/실패/전달 대기 없음. runtime C++ 및 공유 shader 변경이 없어 이번 빌드는 재실행하지 않았다. 실제 로드 Main DLL SHA는 기존 성공 빌드와 같으며 FinalVerification.json에 기록했다.

재개 근거: Metadata/MonsterDeathWhiteDisc_20261015/FinalVerification.json → 해당 도메인 지식 문서의 같은 날짜 최종 절 → 관련 EventId/패키지/Before·After T3D. 완료된 authoring을 반복 실행하거나 Backup 파일을 Main에 일괄 덮어쓰지 않는다. 후속 시각 변경이 실제 필요하면 대상 바인딩을 먼저 확인한 후 필요한 재생 검증만 반복한다.

## 2026-10-15 — 패링 교체·선형 카메라·거인 패턴/모션 후속 진행

사용자의 현재 직접 수정 요청 범위는 KZ_Parring_Distort + 기존 Brutal 파티클, 모든 기존 카메라 힘의 선형 보간, Yetuga/Apes 원거리 재공격·Yetuga Armageddon 확률·긴 잡기, 약점 root/그로기·brutal 사망·combo 연결이다. 메인 Source에 기존 소유자를 보완했다. Architecture 마지막 ARCH-99/85/92/94 후속 절을 따른다. 새 runtime class/file/manager 0개. 원작 데이터 자체의 full fidelity 완료를 아직 주장하지 않는다.

현재 Build02 Succeeded. 추가 실제 경로 QA(기존 GiantFall/Camera 파일)의 Build03은 include와 shadow warning을 수정했고 Build04 결과를 확인하는 단계다. Metadata/CombatFeel_20261015/Author01/Author.json: 메인 Guard BP와 두 giant BP만 백업 후 저장 성공, Guard는 현재 BrutalFront의 non-floor particle 9개 원본 data를 복사하고 정확한 KZ_Parring_Distort을 참조한다. 원거리 설정은 Yetuga 800~5000cm(저장 original 거리 경계), chance .3/쿨타임20s TEMP, 두 giant direct path fallback true다. 원작 StateTree/슬래시/스태미너/피해/잡기 unblockable 데이터는 보존한다.

약점 root read-only RootAudit는 16 sequence의 enable/track0/extraction 정상. Rider LLDB PID9068 실제 Apes PartGroggy: RootMotionFromMontagesOnly, montage AM_ApesStoneHandElite_PartGroggy, DisableRootMotionCount0, MOVE_Walking, root translation scale1, mesh relative scale1, 0.8s actor X=-344.76/Y=-9.79. 이미 capsule root 이동하므로 이를 missing root track으로 재베이크하지 않았다. 디버깅 소유 session은 STOP, agent breakpoints 제거, 기존 user exception breakpoints 8개 그대로 유지. DebugBefore 첫 실행은 ExecutePythonScript 자동 quit와 콜백 __file__ 문제로 실패했으며 DebugBefore02의 ExecCmds/직접 Python 실행에서 관측했다. 중단 debugger test는 정식 통과 증거로 쓰지 않는다.

정확한 다음 절차: (1) Build04.log 결과 확인, 실패 시 해당 compiler diagnostic만 수정/build. (2) Scripts/Engineering/audit_combat_feel_20261015.py를 fresh read-only commandlet로 AuditAfter에 실행해 saved CDO와 particle data를 검증. (3) task-owned RHI editor에서 Scripts/Engineering/monster_physics_validation_driver_20261013.py를 사용, KZ_MONSTER_PHYSICS_TESTS=Khazan.LinearCamera.PIE,Khazan.GiantCombatFeel.PIE,Khazan.GiantReaction.PIE,Khazan.GiantCamera.PIE,Khazan.Parry.PIE; 새 PIE별로 실행. (4) 실패 원인을 actual log/runtime values로 좁히고 작은 수정, 그 수정 관련 suite만 반복. (5) KZ_COMBAT_FINISH_LETHAL=1의 기존 CombatPresentation.PIE 6종 front/back 12case로 death 연결 및 캡처 확인. (6) 원거리 기본 .3 확률/20s 재선택과 source combo 실제 부드러움 RHI 검수. (7) 완료/미확인 범위를 domain docs에 append, FinalVerification.json와 main actual module hash 결속. 다른 세션의 HeinColourVFX/MonsterDeathWhiteDisc editor/build/asset은 종료하거나 덮어쓰지 않는다.

## 2026-10-15 — HeinMach 색감·브루탈 피격 파티클 후속 진행 중

현재 직접 runtime 수정은 KZCharacter.cpp의 승인 피격 spawn을 기존 수신자 캡슐 표면으로 옮기는 작은 계산뿐이며 새 gameplay 상태/클래스/manager가 없다. Source 이전본은 Metadata/HeinMachColourVFX_20261015/Before/Source에 보존했다. Work Definition7에 현재 브루탈 PP_Dmg_Blood_Trail_Sub를 연결한 후보를 저장했으나 Main DataAsset 전달은 아직 0이다. MainBuild01의 생성 헤더 줄 불일치 후 공유 헤더 재생성은 됐고, MainBuild02/03은 동시 DEV 소스의 API/컴파일 오류로 실패했다. 이 파일들은 병행 소유자가 수정 중이므로 임의 덮어쓰지 않았다. 성공한 공유 CombatFeel Build02 DLL을 Work에 stage했으며 마지막 모듈/소스는 RuntimeStage01.json이다. 안정된 최종 Main 빌드와 피격·GAS 회귀/새 Main RHI는 아직 남았다. 소량 colour probe의 초기 Python setup 실패는 game save0이며 own process만 종료했다. 정확한 마지막 상태·실패·다음 명령은 Metadata/HeinMachColourVFX_20261015/ResumeState.json을 따른다.
## 2026-10-15 — CombatFeel 진행 갱신: 분기/효과 문제 재현 후 보완

앞선 9개 파티클 연결은 RHI에서 ghosthand 팔 잔상의 큰 회색 geometry와 혈흔/무기 면이 화면을 가리는 것을 확인해 대체했다. Author02는 Guard에 기존 Brutal 접촉 파티클 PP_AtkEx_Grapple_01/02 + PP_Dmg_Blood_Trail_Sub 3개만 복사 저장, 사용자 지정 KZ_Parring_Distort 원본 참조 유지다. RequestedNiagaraOnly/BrutalMeshOnly/FP_Kazan_ghosthand_arm_01Only/BrutalContactsOnly는 저장0의 개별 시각 진단이며 기능 통과 결과가 아니다. shared Brutal montage/PS/material 원본은 보존했다. Niagara emission .5s TEMP 후 자연 drain, 미완료 emitter의 최종 수명 2.5s TEMP bound를 Guard 설정에 추가했다.

원거리 RNG는 진입 실패 대신 SourceGate의 선택 결과를 같은 frame의 true/false 양쪽에서 공유하도록 기존 AIController에 작은 choice receipt를 보관한다. 과거 '실행 진입에서 한 번 RNG' 설명은 이 실제 수정으로 대체한다. 추가로 SourceGate가 DisabledPatternSkills에 있는 ChargeTackle을 양쪽 모두 false 처리해 source false continuation까지 막던 버그를 return bInvert로 수정했다. ChargeTackle 비활성화 자체는 유지한다.

Build08/09 Succeeded (NoXGE/MaxParallelActions2). Build05의 C3859/C1076는 병렬 PCH 메모리 부족이었고 Build06부터 제한해 성공했다. Physics03에서 LinearCamera 4, GiantReaction(Part capsule Apes526.796cm/Yetuga526.790cm 및 groggy237/405 연속 samples), GiantCamera4, GiantFall13 case는 성공. GiantCombatFeel은 Apes 4km 추격/두 giant 20m 실제 grab/원거리 full-HP Armageddon이 성공했으나 Yetuga zero-chance fallback은 BT070 nav moving 상태에서 이동량1.935cm라 실패한다. 현재 PursuitTelemetry의 실제 CMC max speed/mode/velocity/requested/root mode/active montage/intent log로 마지막 원인을 좁히는 중이다.

Rider DebugPursuit는 최적화된 this/조건 평가 때문에 의도한 Yetuga frame을 확인하지 못했으며 agent breakpoints 제거/소유 debugger STOP했다. 해당 debugger probe는 완료 검증으로 취급하지 않는다. 다음은 PursuitTelemetry/Editor.log의 GIANT_PURSUIT_RUNTIME 행 확인 → 그 실제 원인만 수정 → 관련 suite 재실행이다. FinalRHI01은 메인 표준 Build09 모듈에서 Parry17 후 CombatPresentation lethal6종 front/back12case와 새 DeathJoin 캡처를 실행 중이다. 모든 결과를 확인 후 FinalVerification 및 도메인 완료 기록을 추가해야 한다. 기존 RHI/physics 실패 기록은 보존한다. 현재 실제 전수/원작 전체 parity 완료로 표시하지 않는다.


## 2026-10-15 ? HeinMach ????? Main ??, ??? ?? ??

Main KZCharacter.cpp ?? ?? ?? ?? ??? Definition7 exact Brutal Trail_Sub ?? ?? ??. MainBuildFinal Succeeded/up to date, MainSaved01 ??. ActualHitsHein02? Parry17/6? ??/PlayerAttackCollision? ??. CombatEffect ??? ?? HeinMach? 4? fixture? ?? ?? seed AI? ???? ???? QA ??? ??? ?? ??/fixed60 ActualAttacksHein03?? ??? ???. gameplay ??? ? ??? ?? ?? ???? ???. MainHitsHein01 ? ??? colour subset ??? ??? ? ?? ??? append??. ??? ??? Metadata/HeinMachColourVFX_20261015/ResumeState02.json.


## 2026-10-15 ? CombatFeel ??? ?? ?? ?? ? ??/?? ?? ??

?? Source/3 BP? ???? ??. `Metadata/CombatFeel_20261015/FinalRHI01/Driver.json`? ?? ?? standard DLL(7f2e1da8...)? Parry 17 fixture ? CombatPresentation 6???? 12 lethal pair ?? Success, saved_packages=0??. Author02? Brutal ?? ??? 3?? ?? Niagara? ?? ???? ????. Physics03?? LinearCamera/GiantReaction/GiantCamera/GiantFall? ?? Success??, ?? suite? GiantCombatFeel ??? ??? ????.

?? ??? ??: PursuitProbe03?? Yetuga? Walking, MaxWalkSpeed470cm/s, MaxAcceleration1800cm/s?, MontagesOnly, ?? ???/????? ???? ??, IgnoreMoveInput=false?? pending/last Pawn ??0???. baked navmesh ???? MoveTo? abstract path? ???? Moving? ???? ?? ??? ???? ???. ? manager ?? ?? AIController? ??? ?? task? DirectMoveGoal? ???? Tick?? ?? Locomotion intent? Pawn/CMC AddMovementInput?? ????? ????. ?? ??/?? Exit/Unpossess?? ?? StopRequestedMove? ? ??? ??? ?? ????. ?? navmesh ?? ?? ? ?? MoveTo? ????. disabled ChargeTackle? inverted source gate? ?? false? ?? ??? bInvert ???? ????, Armageddon ??? ?? frame ? true/false gate? ??? RNG ??? ????(?? task Enter?? RNG? ?? ?? ??? ??).

??? ??: Build10.log ??? ????. ?? QA `SawPursuit`? direct locomotion intent? ????? ? ?? ?? ? PatternAbility ?? ??? Build10 ????? incremental Build11? `-NoXGE -MaxParallelActions=2`? ????. ??? hidden main NullRHI editor?? `combat_feel_validation_driver_20261015.py`, tests=`Khazan.GiantCombatFeel.PIE,Khazan.BeastDodge.SourceAudit,Khazan.GiantFall.PIE`? PursuitFinal? ????. ?? 4500cm ?? ??, source StateTree Armageddon, ? ??? 2000cm capture? ????. ?? ? audit_combat_feel_20261015.py? AuditFinal?? read-only ??, ?? hash/??? ??? ??? ????. ?? ?? editor/Source/asset? ????? ???? ???. ?? ??? ??? ?? ?? PIE ?? ???.


## 2026-10-15 — CombatFeel 최종 완료 및 재개 기준

앞선 같은 날짜 진행 중 기록을 완료 상태로 대체한다. Build10 표준 DLL 잠금은 보존했고 타 세션을 종료하지 않았다. 잠금 해소 후 Build11 표준 및 Build12 suffix 성공, 후속 다른 빌드가 표준 manifest로 복귀한 뒤 FinalMain01에서 실제 UnrealEditor-Khazan.dll SHA 73fed22564f0657a1d1bc7b2c56d8c6637b7f2279974645e13d1c354313d40cd로 GiantCombatFeel/BeastDodge.SourceAudit/GiantFall 모두 Success, 저장0을 다시 확인했다. PursuitFinal suffix 성공도 원시 기록 그대로 보존한다. 다른 run의 모듈을 현재 모듈 테스트로 재명명하지 않는다.

최종 상태 complete_main_verified/remaining=[]는 `Metadata/CombatFeel_20261015/FinalVerification.json`다. 패링/카메라/약점 root·groggy/콤보/치명 브루탈 전환, 두 giant 거리 복귀/잡기와 Yetuga source Armageddon 적용 완료다. 작업 소유 editor/commandlet은 정상 종료했고 breakpoint/debug session도 이전 root 진단 후 정리했다. 원작 shader pixel 일치와 moving-target capture 회피 등의 검증 범위는 최종 report limits이며 필수 미반영 작업이 아니다.

다음 관련 요청은 Router→Architecture v2/Migration→관련 현행 문서 최신 날짜 절→FinalVerification의 현재 Source/3 BP SHA 및 AuditFinal에서 시작한다. 완료 author 스크립트/전체 root 재임포트/이전 DLL 복원은 반복하지 않는다. 실제 추가 수정이 생기면 변경한 소유자와 해당 suite만 검증하며 타 세션 변경을 보존한다. write_final_verification.py는 완료된 receipts를 검사할 뿐 게임 파일을 수정하지 않는다.



## 2026-10-15 — HeinMach 승인 피격·색 검증 Main 최종 완료

앞선 HeinMach 관련 Main 미반영/최종 RHI 대기 기록은 complete_main_verified/remaining=[]로 대체한다. 정본은 Metadata/HeinMachColourVFX_20261015/FinalVerification.json, 재개 기준은 ResumeState03.json이다. Main105 package 현재 SHA/저장 readback 성공, 표준 MainCaptureBuild02 성공. MainHitsHein01의 Parry/MonsterRepair/PlayerAttackCollision3 suite 성공과 후속 DEV-only capture helper 빌드·새 native 촬영을 구분했다. 현재 canonical DLL은73fed22564f0657a1d1bc7b2c56d8c6637b7f2279974645e13d1c354313d40cd다. 실제 gameplay 검사 당시 DLL은 report의 별도 hash를 사용한다.

초기 concurrent header/DEV 오류·foreign suffix DLL 잠금 build 실패, 잘못된 editor viewport Shot, fixture/seed AI 간섭/시간초과 broad CombatEffect partial은 진단 기록으로 남겼다. 최종 targeted suite/색 검증의 성공을 이 실패 실행에 소급하지 않는다. 필수 미반영 작업은 없고 작업 소유 editor0/foreign·Rider 제어0이다.

다음 요청은 Router→Architecture/Migration 관련 현행 단계→현재 Source/feature 최종 절→FinalVerification의 task-before diff2개/해당 QA metadata 순으로 시작한다. 완료 author/delivery 및 stale Source/DLL/worktree 복원을 반복하지 않으며 실제 새 변경 소유자와 관련 suite만 검사한다. Art 색 수치는 해당 Art 정본에서 확인한다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 ? GiantRootUsage ?? ??170? ?? ? ?? ?? ??

??? ?? ?? ???? Yetuga/Apes? ?? ?? ???? ?? ????. ?? AllPatternRootAudit118 ? CombatFeel?16 ???? ?? ????? ??? CDO CombatPatterns/Definition grants?reaction(Additive/VictimFront ??)?Stamina?ABP graph dependency? ???. AuditBefore? ??170 sequence/30 montage/2 combo definition, body skeleton ???0, true root/track0 ??0, force root lock off0, AnimBP mode ? ? MontagesOnly?. ?????162?? enable_root_motion=true?? off8?? A_*_HitAdditive_[D/L/R/U]?? root ?? ??0? ?? ?? ?????. AKZCharacter::PlayHitReaction? ?? !Montage->HasRootMotion() ???? ?? ??/CMC? ????? ???8? flag? ?? ?? ??? ????? root montage? ???. ?? ?? Source/asset ??0??.

Rider LLDB? ?? RuntimeBefore PID29576? PatternAbility307?308, HandleMontageNotifyBegin758 ???? ?? mode3/?? IgnoreRootMotion/disable count0/?? montage/Walking? CMC RMS target250cm? ????. ? Ignore? source MoveTo? ?? ???? ??? ?? ?? adapter?. getter native expression ?? ? ?? ?? ????? TickPattern200 access violation?? ???? ?? ??? ???? ???. debugger?agent breakpoint ???? ???8 exception breakpoint? ????.

?? RuntimeBefore02 ?? PID9060? ??? ?? ?? RootPoses.PIE170/510 pose ? BeastDodge.PatternsPIE47 actual GAS entry? ?? ???. Scripts/Engineering/probe_giant_root_runtime_20261015.py? ?? AnimBP pose? Root/Bip001 component transform? mesh relative/actor/section/mode? ????. ?? ??? Metadata/GiantRootUsage_20261015/ResumeState.json ? RuntimeBefore02/{Driver,Progress,RuntimeRoots,RootPoses}.json ? Editor.log?. ????? ?? ??? ? ?? ??? async? ???? ?? ?? ??? ?? ??? ?? ????. ?? ?? ??? ?? ???? ????? ??? ?? ??? ?? ??? ?? ???. ?? mutation ?? ? ?? hash/backup/duplicate probe? ?? ????.


## 2026-10-15 ? GiantRootUsage ?? ??4? ?? ????? ?? ? ?? ?

RuntimeBefore02? ??170/510 RootPoses?? ? ???? Damage_PartGroggy_Loop/End ? ??522.148cm root offset? ????. ?? suite?47 GAS entry? ?? Success?. ??? ?? ?? ??? ??? ????. ? clip? root_motion=true/force_lock=true/track0? ???? ANIM_FIRST_FRAME ??? imported first root(-2.670138,-522.141235,0)? ??? pose? ???. skeleton ref root?(0,0,0)??. ?? CombatFeel? root ??/?? ?? ????? ? loop/end ?? ??? ?? ??? ????.

RepairPlan? ??4package SHA/?? byte backup ? temporary Yetuga Loop duplicate ?? RAW frame?bone/metadata ?? ? fresh native ProbeNative offset0/Success ? Applied.json? main4 RootMotionRootLock=REF_POSE ??? ????. gameplay C++/BP/??????Skeleton ??0, raw channels written0?? off8?? ??? Additive? ????. ??? ??/?? ??? ResumeState.json ? RuntimeAfter/ActualPartRHI??. ?? final ??? ???? ???.


## 2026-10-15 ? GiantRootUsage ?? Main ?? / ?? ?? ??

?? ?????/?? ? ?? ? ??? ?? ??? ????. `Metadata/GiantRootUsage_20261015/FinalVerification.json` ? ResumeState.json? complete_main_verified/remaining=[]?. ??170/30montage/2definition?? ?? root pose? ??? PartGroggy Loop/End4??522.148?0cm? ???, Source??/???/???? ??0??. RootEnable/RootExtraction? ????4????? ?? flag audit? ?? PartGroggy Start ?? ????? ?? ?? ??? ??? ??? ????.

?? ?? Main ?? DLL73fed225...? RuntimeAfter RootPoses170/510, GiantReaction2, GiantFall13 Success, ?? ActualPartRHI GiantReaction2 ?6?? Success/Loop?End0cm?. Native model/notify170/?????166 SHA? ????. RuntimeBefore02? RootPoses4 ?????47 GAS entry Success? ?? ?? ???? ???, LLDB getter ?? ? ??? RuntimeBefore? diagnostic-only?? ?? ??? ???? ???. agent breakpoint/session ?????8 exception breakpoint ??, ?? editor/commandlet ?? ? ?? probe ???? ????.

??? Router?Architecture/Migration?MONSTER_ATTACK_ROOT_MOTION ?? ??FinalVerification ? AuditAfter/??4package SHA ???. ??? ?? ?????? repair apply/probe/full import/Root data ????/?? asset ?? DLL ??? ???? ???. ?? ? ?? ??? ?? locked root? ?? skeleton ref? ??? ?? ?? ?? ??? ?? ????. backup4?? Before? ??? ??? rollback? ??? ?? ???? ?? SHA? ???? ????.



## 2026-10-15 — HeinMach 포탈 완료 / 재개 기준

Main 저장·Main suffix Build07·RHI06의 실제 Player intent/CMC walking·암전·전장 이동 및 실패/EndPlay count cleanup, Readback04의 저장 계약 검증이 완료됐다. 상태는 Metadata/HeinMachPortal_20261015/FinalVerification.json 및 ResumeState.json, 상세는 HEINMACH_YETUGA_PORTAL_20261015.md가 정본이다. 현재 필수 미완료0이다.

후속은 Router → 관련 Architecture/현행 문서 → FinalVerification → 현재 map/Source의 해당 필드만 읽는다. 단순 확인은 readback_heinmach_portal_20261015.py, 실제 재실행은 새 KZ_PORTAL_OUT과 KZ_PORTAL_CAPTURE=1의 heinmach_portal_validation_driver_20261015.py를 사용한다. 과거 실패 autorun/old DLL/old Work map을 전달하지 않는다. Source의 runtime 좌표 hardcode0/자원 owner는 portal 한 개이며 별도 manager나 Interact Ability를 선행 추가하지 않는다. Art 배치/노출·공유원본 보호는 Art 동명 문서를 따른다. 동시 look 작업이 Main map을 바꿀 때 portal2 actor와 새 Niagara 참조를 보존해야 한다.

<!-- HeinMachPortal_20261015_complete -->

## 2026-10-15 — 컨트롤러 진동: source_applied_unverified_user_requested

- 사용자 직접 구현 요청에 따라 Main 기존7파일에 진동 경로를 추가했다. 정확한 파일·생산자·수명·TEMP 조정값은 Metadata/ControllerRumble_20261015/Implementation.json 및 COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 진동 절.
- 마지막 실행 검증: 없음. 이번 요청은 명시적으로 검증 생략이므로 build/PIE/test/정적검사/장치 확인을 수행하지 않았다. 실패가 확인된 상태가 아니라 의도적으로 미실행한 상태다.
- 적용: Source만. 새 runtime/asset0, editor/DLL reload0. 기존 실행 바이너리에 즉시 반영됐다고 설명하지 않는다.
- 향후 사용자가 검증을 요청했을 때만 현재 Main을 빌드/정상 재시작하고 컨트롤러 UE Force Feedback 인식/설정, Weak/Strong/Spin/OverFury/승인 패링, 실제 거인/Elite 행동·HitGroup 중복/취소/거리 감쇠를 확인한다. 요청 전 자동으로 이 검증을 시작하지 않는다.
- 다음 조정은 AKZPlayerController Class Defaults의 KZ|Feedback|Temporary에서 수행한다. 원작 rumble metadata 미확인/TEMP와 실제 장치 체감을 구분하며 완료된 원본 효과/AI/입력/자산 author를 반복하지 않는다.


## 2026-10-15 — Readback05 최종 스냅샷 보충

동시 Main 저장 뒤 fresh Readback05(save0)가 포탈/arrival2 actor의 참조·transform·범위·암전 시간과 전용4asset/공유 원본 보존을 다시 통과했다. 최종 확인 map SHA는 `62e48f3c26be58069ddfc9d3458787048d51bc7e8714eda9e5ca640e74c5938a`, 영수증 시각은 `2026-10-15T04:28:08.040073+00:00`다. 기존10009 actor 동일과 별도 PlayerStart1 수정, 이 작업 밖의 추가 actor 10개를 구분해 보존했다. 앞선 Readback04 기록은 해당 시점의 기록으로 유지하며 최신 근거는 FinalVerification.json의 Readback05/RHI06이다. 실제 walking·암전·전장 이동·복구 Success 이후 게임 Source/자산을 추가 수정하거나 사용 중인 editor를 reload/save하지 않았다. 현재 요청의 필수 잔여0이다.

<!-- HeinMachPortal_20261015_readback05 -->

## 2026-10-15 — 초록색 콜라이더 표시 삭제 완료

현재 Main `KZComboActionAbility.cpp`에서 3종 초록색 debug shape 그리기와 include를 제거했고 공유 Player/Monster 충돌·피해 계산은 보존했다. Before 백업 대비 10줄 삭제, production draw 참조 0, Main build exit0/Succeeded다. 이번 검사에서 새 PIE·진동 실기 검증은 없고 외부 Work 에디터를 제어하지 않았다. 남은 Main 전달 단계는 없다. 정확한 현재 Source/표준 DLL SHA와 재개 근거는 `Metadata/AttackCollisionDebugRemoval_20261015/FinalVerification.json`; 과거 초록색 debug draw 요구는 사용자 최신 삭제 요청으로 대체됐다.


## 2026-10-15 — Spinning 표현 데이터 교체·검수 진행

Metadata/HeinMachLookSpin_20261015/SpinRefinedRHI05의 표준 모듈73fed225...에서 실제 Khazan.CombatEffect.PIE(Spinning 선택 및 기존 공유 수명/취소/적중·브루탈 회귀)와 PlayerAttackCollision이 Success다. 변경은 기존 CombatEffect 데이터: 여섯 KZ_Slash 대신 OverFury 사본6/Charge streak3/vortex2 쌍, 원래176 객체·clock/GUID 및 피해/입력/section/audio 보존이다. source/runtime/config/DLL 저작0, 새로운 gameplay 구조0이다. 공유 PS를 바꾸지 않고 Helix2 재질만 가린 전용 PS1이 추가됐다. 현재 Main 게임 에셋 반영0이다.

색 촬영의 pause 직후 ReadPixels/디버그 문구 혼입을 QA Python의 렌더 완료 대기·메시지 숨김으로 보정하고 Final03 두 맵 검수 중이다. 게임 shader나 PP를 촬영 결함에 맞춰 변경하지 않는다. 기능 테스트 완료와 Main 선택 전달/새 Main 검수 대기를 구분한다. 정확한 재개는 Art continuity의 같은 날짜 renderer corrected 절과 Metadata/HeinMachLookSpin_20261015/ResumeState02.json이다. 완료 author 및 이전 Source/DLL 복원을 반복하지 않으며 foreign/Rider editor는 제어하지 않는다.

<!-- HeinMachLookSpin_20261015_renderer_corrected_pending -->


## 2026-10-15 — Spinning 데이터 교체 Main 최종 완료

앞선 Main 미반영/Final03 진행 중 기록을 완료로 대체한다. MainDelivery02의3개 선택 전달, MainSaved01의 현재10022 actor/10021 label pose·포탈 계약 보존, 실제 Main DevMap CombatEffect(Spin 선택+공통 cleanup 회귀)/PlayerAttackCollision 두 suite가 Success다. HeinMach는 자연 Spin29event/3section·boundary cleanup/충돌을 완료했고 이후 rear-Brutal B fixture 실패는 그대로 남긴다. 현재 실제 module SHA는a8df6850908f08e84b6c8cc8a555c92d46b5c34ba75b136f9eac1b841a325069로 초기 Work73fed...와 구분한다. 이번 신규 Source/Config/DLL 저작·전달/build0이며 현재 사용자/동시 변경을 보존했다.

재개 기준은 Metadata/HeinMachLookSpin_20261015/FinalVerification.json→ResumeState03.json 및 Art feature 정본이다. 필수 잔여=[];42개 조건별 외관/원작 shader·pixel/Shipping FPS는 검증 한계다. MainDelivery01 충돌은 쓰기 전 거절/최신 map 재적용으로 해결했다. MainHeinSpin01은 준비 전 QA 바닥 fixture(save0) 실패이고02에서 warmup 뒤 실제 바닥으로 검사했다. 완료 author/delivery/전체 source·DLL/old Work map 복원을 반복하지 않는다. 사용자/Rider/foreign editor 제어0, 모든 final own editor 정상 종료다.


추가 동시 저장본은 MainLatest01에서 poses/montage/light/fog/PP 동일, MainLatestSaved02에서 현재 저장·포탈 계약을 확인해 보존했다. 최종 현재 map SHA는7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728이며 이전 전달 SHA와 구분한다. 최신 파일을 옛 전달 바이트로 복구하지 않는다.

<!-- HeinMachLookSpin_20261015_complete -->

## 2026-10-15 — Yetuga BGM runtime Main 빌드 완료

AKZBossPortal runtime2파일에 성공한 도착 후 World 2D music 시작만 추가했다. 사용자 정정으로 HP/사망/보스 처치/거리/이탈 종료 조건은 없고 재진입은 기존 IsPlaying receipt로 중복을 억제한다. 초기 안내의 자동 종료 계획은 구현하지 않았다. Main4 음악 asset 저장과 stock KhazanEditor Win64 Development Build01 Succeeded(exit0)가 완료됐다. 새 runtime class/file/manager/tick0, map save0, 사용자 editor 제어0, 새 PIE/게임 청취0이다. 필수 delivery 잔여0이며 실제 청취/원작 scheduler/DSP 일치는 미확인이다.

정확한 기준은 HEINMACH_YETUGA_PORTAL_20261015.md 최신 절 → Art YETUGA_BGM_SOURCE_20261015.md → Metadata/YetugaBGM_20261015/Implementation.json이다. 후속 증상은 현재 메인 DLL로 정상 실행해 기존 HM_Yetuga_EntrancePortal을 통과한 뒤 실제 음악을 표적 관측한다. 이미 실행 중인 에디터가 이전 DLL을 로드한 경우 사용자 정상 재시작이 필요하다. 사망/처치/이탈 종료 로직을 다시 추가하거나 과거 DLL/맵을 복원하지 않는다. 이번 compile 성공은 이전 진동·현재 BGM의 실기 동작 검증을 뜻하지 않는다.

## 2026-10-15 — Windows Shipping 패키징 진행 중 / Epic 품질

사용자가 게임 릴리즈 패키징과 결과 경로를 요청했고 후속으로 시네마틱 바로 아래 품질을 명시했다. Config/DefaultGameUserSettings.ini의 모든 sg quality3(Epic), resolution100%, desktop borderless/VSync를 사용한다. GameDefaultMap은 최신 /Game/Maps/L_HeinMach_Environment로 직접 지정했고 HeinMach/StormPass2 map 및 /Game/Data·Yetuga music을 cook 대상으로 설정했다. Pak/IoStore/Oodle lossless, prerequisite 포함/디버그 파일 제외다. 원작 게임 수치 재현이나 Cinematic4 설정이 아니다.

현재 Scripts/Engineering/package_release_20261015.py Package02가 진행 중이다. 출력 목적지 C:/Users/user/Desktop/Khazan_Release_20261015, 로그 Metadata/Release_20261015/Package02/UAT.log, 소유PID/인자는 Launch.json이다. 최초 Package01 Shipping compile은 unused InterchangeResult.h와 editor-only Niagara UpdateLUT에서 실패했다. 관련2 cpp만 작은 수정: unused include 제거; 기존 상수 회전0/배율1 curve를 runtime SetDefaultLUT/UpdateTimeRanges와 reflected ShaderLUT 한 sample/MarkRenderDataDirty로 동일하게 전달한다. 새 runtime class/파일0이며 raw source/config 백업은 Before다. Package02 Shipping compile26.16s Succeeded 후 cook가 시작됐다. 아직 패키징 완료/실행 성공으로 기록하지 않는다.

재개: 먼저 Package02/Exit.json과 UAT.log 최신 끝/소유 프로세스를 확인한다. 진행 중이면 중복 UAT를 실행하지 않고 해당 session을 기다린다. 종료 실패면 원래 log를 보존하고 실제 최초 오류만 표적 수정해 Package03 등 새 run에 재실행한다. 완료된 Shipping compile 재사용이 타당한 데이터-only 재시도는 --skipbuild 옵션을 사용할 수 있다. C: 초기 여유 약27GB이며 중복 archive copy 없이 staging 자체를 최종 배포 폴더로 사용한다. 사용자 프로젝트/추출원본/기존 worktree/백업을 삭제하지 않는다. 최종 engine prerequisite·실행파일·pak/IoStore 구성과 시작 맵/설정을 확인하고 이 절 뒤에 실제 완료 결과를 추가한다.

### 2026-10-15 — Package03 재개 지점

Package02는 Shipping compile 성공 뒤 cook에서 `GameInstanceClass contains a redirected reference`와 `/Script/GameFeatures.GameFeatureData` 미로드 ensure를 발견해 소유 cook PID30244만 종료했다(Exit25). Config의 GameInstanceClass를 실제 /Game/Bluprints/GameSystem/BP_GameInstance로 교체하고 기존 AssetManager 선언이 필요로 하는 GameFeatures 플러그인을 uproject에서 활성화했다. 사용자/외부 editor·process 종료0이다. Package03가 새 Shipping build 후 cook에 진입했다. 재개 시 Package03/Launch.json·UAT.log·Exit.json이 우선이며 이전 Package02를 새로 실행하지 않는다. 품질은 사용자 후속의 시네마틱 바로 아래=Epic3/100%다.

### 2026-10-15 — 사용자 최신 범위: HeinMach 단일 레벨 / Package05

사용자가 HeinMach 레벨만 패키징하도록 범위를 정정했다. DefaultGame.ini MapsToCook와 release runner -map을 /Game/Maps/L_HeinMach_Environment 하나로 축소했다. StormPass 레벨을 포함하던 Package03의 소유 cook PID15100만 ancestor chain 확인 후 종료했고 Exit25는 이 의도적인 중단이다. 직후 Package04는 이전 AutomationTool 종료 직전 mutex 충돌로 Exit1이었다(게임/콘텐츠 오류 아님). 이전 UAT가 완전히 종료됐음을 확인한 뒤 Package05 --skipbuild를 시작했다. GameFeatures 활성화를 포함해 이미 성공한 Package03 Shipping build20.63s를 재사용하며 clean cook로 이전 StormPass map 출력을 제거한다. Epic3/100%, Yetuga 음악 및 기존 게임 기능은 유지한다.

현재 재개 기준은 Metadata/Release_20261015/Package05/{Launch.json,UAT.log,Exit.json}이다. 완료 전 실제 최종 cook/stage map에 HeinMach만 포함되는지, 실행파일/IoStore/prerequisite와 배포 설정을 확인한다. 출력 예정 C:/Users/user/Desktop/Khazan_Release_20261015. 아직 배포 완료가 아니며 새 gameplay/장치 실기 검증을 했다는 뜻도 아니다. 이전 두 맵 범위 기록은 시점별 이력으로 보존한다.

## 2026-10-15 — HeinMach 단일 레벨 Shipping 패키징 최종 완료

최신 요청은 HeinMach만 포함하고 시네마틱 바로 아래 Epic 품질로 배포하는 것이다. Package05의 clean cook는 8,590 package/533.78s, 0 error·6 warning으로 완료했고 UAT 전체 exit0/BUILD SUCCESSFUL(676.52826s)이다. 이전 Package03의 두 맵 범위와 진행 중 상태는 이 절로 대체한다. Package03의 GameFeatures 포함 Shipping compile20.63s 성공 바이너리를 재사용했고 최신 Source 중 바이너리보다 새로운 파일0이며 메인/배포 Shipping exe SHA는 b3e4bf1d37746a116784b56fa9be58b41fdcf04766e760bd93457662be930bbc로 동일하다.

실제 배포 폴더는 C:/Users/user/Desktop/Khazan_Release_20261015/Windows, 사용자 실행 파일은 그 안의 Khazan.exe다. 총41파일/2,410,104,666bytes(약2.25GiB), Pak·IoStore/Oodle 압축, VC prerequisite 포함, PDB 제외, 실행안내.txt 포함이다. 이 Windows 폴더 전체가 배포 단위다. IoStoreContents.csv의 게임 map은 L_HeinMach_Environment 하나이며 StormPass.umap0; Engine Entry map은 엔진 필수 bootstrap map이다. Yetuga 음악4asset도 최종 container에서 확인했다. 최종 pak에서 추출한 설정은 직접 GameInstance/GameDefaultMap과 Epic11 quality group=3(UE5.8 Landscape 포함)·ResolutionQuality100이다. 최종 source map SHA7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728로 기존 맵 변경0이다.

Shipping exe를 별도 UserDir·RenderOffscreen·1280x720·nosound로90.07s 실행해 프로세스 생존/Responding 및 새 crash dump/context0을 관측하고 정확한 exe/PID/시작 시각을 확인해 자기 프로세스만 종료했다. 자연 exit0, 실제 화면 외관·전투·FPS·진동·BGM 청취를 검증했다는 뜻은 아니다. 사용자 editor/게임 세이브/다른 프로세스 제어0이며 Editor DLL을 새 Shipping 수정본으로 rebuild했다고 기록하지 않는다.

재개 기준은 Metadata/Release_20261015/FinalVerification.json → Package05/UAT.log·Exit.json → IoStoreContents.csv·PackagedConfig·Files.json·Smoke01/Result.json이다. 필수 잔여0이며 이미 완성된 패키지를 이유 없이 다시 cook하거나 이전 두 맵 출력으로 복구하지 않는다. 소스/콘텐츠 후속 변경이 있으면 새로운 배포본으로 build/cook한다. 기존 6 cook warning은 project Lumen atlas 우선순위, VFX SM_PortalPlane의 비어 있는 convex collision, GameplayCueNotifyPaths 기본 검색 경로이며 별도 gameplay/asset 수정으로 확대하지 않았다. 모든 실패·중단 run과 Before 백업은 보존했다.

## 2026-10-15 — 진동 2배·HP0/Yetuga 잡기 LockOn 및 HeinMach 패키징 착수

Router→최신 Architecture/Migration→Engineering 규칙/상태/관련 UI·소스 확인 완료. 사용자 중단 뒤 재개했으며 아직 제품 변경 전이다. task 백업은 Metadata/LockOnRumble_20261015/Before와 BeforeHashes.json. 기존 배포 C:/Users/user/Desktop/Khazan_Release_20261015/Windows 및 Metadata/Release_20261015/FinalVerification.json은 이전 완료본이다. 이번 코드 변경을 반영한 재패키징은 별도로 완료해야 한다.

남은 순서: 계약에 따른 기존6 runtime 파일 수정→기존 native 테스트에 HP0 즉시 해제·Yetuga 성공/취소/종료 assertions 추가→stock Editor build와 소유 PIE 검증→기존 Scripts/Engineering/package_release_20261015.py의 새 Package run을 -build 포함 실행→최종 container/Shipping 시작 확인→완료 기록. 실행 중 editor/UAT 없음 확인, C: 여유 약18GB. 기존 사용자의 소스/자산과 원래 패키징 설정 보존. 과거 author/metadata/asset 전체 전달은 하지 않는다.

### 2026-10-15 — 구현 및 Editor build 완료, PIE 진행

실제 변경은 runtime5(Character.h, LockOn h/cpp, MonsterPattern h/cpp)+Config/DefaultGame.ini1+기존 DEV test2다. APlayerController.ForceFeedbackScale은 config property이고 Engine/Config/BaseGame.ini의1.0이 생성자값을 덮으므로, 생성자 변경은 제거하고 프로젝트 DefaultGame의 /Script/Engine.PlayerController ForceFeedbackScale=2.0만 사용한다. PlayerController.cpp는 착수 전 SHA와 동일하다. 기존 Engine PostProcessInput의 최종 clamp가 적용된다.

EditorBuild01/02 모두 Succeeded, 최종02는13.97초. Metadata/LockOnRumble_20261015/run_pie.py PIE01로 소유 hidden RHI editor PID6284에서 CombatUI.PIE/GiantFall.PIE를 실행 중이다. 테스트 전용 HP2000은 잡기 생존을 위한 fixture 값이며 제품 값이 아니다. 로그/actual DLL은 PIE01/Editor.log 및 Driver.json. 아직 PIE 통과/패키징 완료 전이다.

재개는 PIE01/Exit.json·Driver.json·Editor.log와 소유PID 확인부터 한다. running이면 중복 editor를 실행하지 않는다. 통과 후 기존 release runner의 새 Package06_LockOnRumble를 -build 포함 실행한다. Windows 기본 python alias가 없으므로 C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe를 사용한다.

### 2026-10-15 — PIE01 결과와 사망 fixture 보정

PIE01에서 CombatUI.PIE Success: 실제 PC ForceFeedbackScale2, HP0 동기 해제/추적 tick 종료/죽은 대상 거절/이전 대상 HP delegate 제거를 확인했다. GiantFall.PIE의 새 Yetuga 잠금·잡기 성공/정상/취소/죽은 captor 재잠금 차단 검사는 통과했으나, 추가한 lethal case에서 기존 HasRootMotionSources=false assertion 하나가 실패했다. 설치 엔진 CharacterMovementComponent.cpp:12124는 이 API가 RMS뿐 아니라 CharacterOwner.IsPlayingRootMotion(사망 montage)도 포함함을 보여준다. Monster.FinishDeathPresentation이 기존 사망 montage를 실행하므로 제품 cleanup 오류로 단정하지 않았다.

기존 DEV test의 lethal case에 한해 CurrentRootMotion의 OriginalPatternMoveTo가 없거나 MarkedForRemoval인지 검사하도록 정정했고 일반 case의 기존 검사는 유지했다. 게임 runtime/Config 추가 변경0. EditorBuild03 Succeeded(9.93초). 현재 PIE02_Giant 소유 PID10828에서 GiantFall.PIE만 재검사 중이다. 최종결과는 해당 Driver.json/Editor.log/PIEResult.json부터 확인한다. 원래 실패 로그는 PIE01에 보존했다. 패키징은 이 재검사 완료 후 시작한다.

### 2026-10-15 — PIE 완료, HeinMach Package06_LockOnRumble 진행

PIE02_Giant의 전체14패턴/기존 낙하 흐름 Success, Driver.status=passed, editor exit0. CombatUI는 PIE01 Success이고 이후 제품 runtime/Config 변경0, DEV death assertion만 보정했다. 최종 module36069192717ac0060328f3bf9fec406c4d425913e07a194604bc4e1dc7c300c5, Changes.patch/ChangedFiles.json이 현재 적용본이다.

기존 release runner를 Package06_LockOnRumble로 -build 포함 실행했다. 로그 Metadata/Release_20261015/Package06_LockOnRumble/UAT.log, 소유PID/인자 Launch.json, 종료 Exit.json이 재개 기준이다. 출력은 기존 C:/Users/user/Desktop/Khazan_Release_20261015/Windows. 재개 시 중복 UAT 금지, 완료 전 package완료로 기록하지 않는다. UATexit0 뒤 Metadata/LockOnRumble_20261015/verify_release.py로 새 container 단일map/ForceFeedbackScale2/바이너리 동일성/Shipping90초 시작을 검사한다. 이 스크립트의 Smoke01은 아직 생성 전이며 실행은 엔진 내장 Python으로 한다. 최종 파일 manifest와 완료 기록을 추가해야 한다.


## 2026-10-15 — 진동 2배·HP0/Yetuga 잡기 LockOn·HeinMach 재패키징 완료

사용자 직접 요청을 기존 runtime5/Config1/DEV2의 작은 변경으로 완료했다. 신규 runtime 파일/class0, BP/애니메이션/맵 저장0이다. 진동은 기존 엔진 config `/Script/Engine.PlayerController.ForceFeedbackScale=2.0`을 사용하며 생성자 변경은 남기지 않았다. 배율2는 사용자 지정, 최종0..1 상한은 엔진 장치 출력 범위다. 기존 pulse duration/몬스터 거리 감쇠는 그대로다.

LockOn은 대상 ASC HP<=0 callback에서 즉시 해제하고 살아 있는 대상만 선택/유지한다. Yetuga의 승인된 잡기 성공 시 피해 Player의 잠금을 풀고, 기존 잡기 cleanup 후 양쪽 생존·동일 Controller/Pawn이면 동일 Yetuga에 자동 재잠금한다. 잡기 중 신규 잠금, 죽은 target 및 소멸/소유권 변경 후 재잠금은 거절한다. ASC/Ability 상태와 이동 제약의 기존 작성자를 유지하며 delegate/constraint/controller receipt는 각 소유자가 정리한다.

EditorBuild01~03 Succeeded, 실제 RHI CombatUI.PIE 및 GiantFall.PIE(14패턴/기존 낙하 포함) Success. UI 검증 후 변경은 DEV death assertion뿐이며 제품 runtime/config는 동일하다. 초기 lethal fixture가 사망 montage까지 포함한 HasRootMotionSources 검사에서 실패한 기록은 보존하고 자기 OriginalPatternMoveTo 제거 검사로 보정해 재통과했다. 정확한 각 DLL/Source hash와 범위는 `Metadata/LockOnRumble_20261015/FinalVerification.json` 및 Changes.patch/ChangedFiles.json/PIE01/PIE02_Giant를 따른다.

Package06_LockOnRumble의 새 Shipping compile51.47초, cook8590/91.98초/0error·6warning, UATexit0(276.15초)으로 완료했다. 최종 container의 게임 map은 HeinMach 하나, 설정은 진동2/Epic11그룹3/해상도100%, packaged Shipping exe는 현재 build SHA와 동일하다. 배포 폴더 `C:/Users/user/Desktop/Khazan_Release_20261015/Windows`, 실행 `Khazan.exe`, 전체41파일/2,410,106,779bytes다. VC x64 prerequisite와 실행안내 포함, 배포는 Windows 폴더 전체 단위다. 기존 map SHA7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728 보존.

소유 Shipping 프로세스의 별도 UserDir/offscreen/nosound 90초 생존과 새 crash0을 확인한 뒤 해당 프로세스만 종료했다. 자연 종료/전체 패키지 전투·FPS·오디오·실물 패드 체감은 검증한 것으로 확대하지 않는다. 기존6 cook 경고는 이전 release와 같은 Lumen priority/장식 PortalPlane convex/GameplayCue 검색 경로다. 필수 잔여0이며 이후 재개는 위 FinalVerification → 새 요청 범위의 현재 Source/Config부터 한다. 이전 배포 완료본을 현재 바이너리로 오인하거나 과거 package/asset/DLL 전체를 복원하지 않는다.

<!-- LockOnRumble_20261015_complete -->

## 2026-10-16 — 게임 설명 Google Slides 초안 / 연결 대기

사용자 요청은 카잔 아트 콘셉트·보라/빨강 기반 Google Slides 발표자료다. 최신 Architecture/Migration/관련 Source·저장 metadata를 표적 확인했고 게임 Source/Content/Config 수정·build·PIE는 실행하지 않았다. 원고15장은 게임패드 조작, ASC/Ability/Effect/Attribute/Tag 책임, 실행·취소, 공격/가드/패링/회피, StateTree/MonsterPattern 분기, Yetuga 잡기와 록온 복귀, 브루탈, 포탈, 눈 접촉/필드/Nanite 변위, 눈 높이에 맞춘 혈흔 투영을 포함한다. 출처와 한계는 Metadata/GamePresentation_20261016/deck.json의 notes에 기록했다.

현재 결과는 내용 JSON, 이미지8종·RGB 표시용 파생2종, 1280×720 HTML 디자인 초안과 PNG15장이다. 15장을 개별 검수하고 표 간격·CSS 충돌·캡처 alpha 문제를 보정했다. Google Slides/PPTX는 아직 생성하지 않았다. Google Drive는 최종 검색에서도 installed=false이고 브라우저 surface0이다. 연결 제안1회와 대안 방식 질문은 답변 대기다. 로컬 authoring의 load_workspace_dependencies 도구와 @oai/artifact-tool 모듈도 제공되지 않아 PPTX 완료를 주장하지 않는다.

재개: Metadata/GamePresentation_20261016/ResumeState.json → 사용자 최신 연결/대안 답변 → 연결 도구와 Google Slides skill/import schema를 확인한다. 정상 경로는 검수 PPTX의 native_google_slides import이며 다른 방식은 사용자 답변에 따른다. 기존 deck.json/preview/index.html/PNG15장/AssetManifest.json을 재사용해 편집 가능한 Slides를 생성하고 변환 결과를 검수해 URL을 전달한다. HTML 초안을 Google Slides 완료물로 보고하거나 완료된 게임 패키징/소스 작업을 반복하지 않는다.

<!-- GamePresentation_20261016_prepared_waiting_connection -->

## 2026-10-16 — 게임 발표자료 Google Drive 설치 확인 / 현재 세션 도구 미반영

사용자가 Google 계정 연결 완료를 보고했다. 새 search 결과 Google Drive installed=true/ENABLED를 확인했고 새 google-drive 0.1.20의 Drive/Slides SKILL을 읽었다. 앞선 installed=false와 계정 연결 대기는 현재 상태가 아니다. 설치나 재연결을 다시 요청하지 않는다. 다만 이 기존 세션의 가용 도구 목록에는 Google Drive/Slides/import와 tool search·workspace dependency loader가 없고, 새 @oai/artifact-tool import도 Module not found다. 따라서 실제 Google Slides/PPTX 생성은0이며 기존15장 원고/검수 HTML/이미지는 보존했다.

현재 근거 Metadata/GamePresentation_20261016/ConnectionCheck02.json 및 갱신 ResumeState.json. 재개는 설치 플러그인이 로드되는 ChatGPT 데스크톱의 같은 Khazan 프로젝트 새 채팅에서 위 receipt → 새 Google Drive import schema/제작 runtime 확인 → 기존 deck.json/preview 재사용 → native Google Slides 생성·전장 검수·URL 전달이다. 사용자 연결 실패로 오인하거나 완료된 게임 소스/패키징 작업을 반복하지 않는다. 게임 Source/Config/Content 수정·build·PIE0.

<!-- GamePresentation_20261016_drive_installed_session_tools_missing -->


## 2026-10-16 — 정리된 HeinMach Epic Shipping 재패키징 착수

사용자가 최신 HeinMach를 에픽 품질로 다시 패키징하도록 요청했다. 현재 Main map SHA1d224b14ae0ec39b90229e2a122b174b672ca64d976f3c0ef0032236c47f7c00와 Source/Config/uproject 입력 SHA를 Metadata/Release_20261016/Baseline.json에 기록했다. 기존 Epic11그룹3/해상도100%, 단일 MapsToCook, Shipping/Pak/IoStore/prerequisite/진동2 설정을 재사용한다. 게임 Source·에셋·Config 변경0이며 기존 release runner에 task/output 환경 변수만 추가했다.

실행은 Scripts/Engineering/package_release_20261015.py Package01, KZ_RELEASE_TASK=Metadata/Release_20261016 절대경로, KZ_RELEASE_DEST=C:/Users/user/Desktop/Khazan_Release_20261016이다. 정확한 소유 PID/인자는 Package01/Launch.json, 진행은 UAT.log, 종료는 Exit.json이다. 중복 UAT를 실행하지 않는다. 완료 후 container 단일 HeinMach·Epic 설정·Yetuga 음악·현재 Shipping 바이너리/입력 동일성·기본 실행을 확인하고 최종 경로를 전달한다. 기존20261015 배포본은 유지한다.

## 2026-10-16 — 게임 발표자료 Google Slides 완료

기존 deck.json의 15장을 편집 가능한 Google Slides로 제작했다. URL: https://docs.google.com/presentation/d/1F9iM_KFZIao1aY22sxEIrZAujQy-xS84r3enfs0pblE/edit?usp=drivesdk . My Drive/ChatGPT 폴더에 저장했다. 본문 native text·표4개·출처/범위 speaker notes15개를 readback 확인했고, 변환 PDF15장 전체를 개별 검수했다. 구조 검사 issue0, 잔여 시각 결함0이다. 로컬 준비 PPTX는 내부 제작용이며 사용자 최종 산출물은 native Slides다. FinalVerification.json 및 build/raw-output.json·output-issues.json·validation.json과 build/google-render가 증거다. 이전 도구/runtime 미제공 대기는 해소됐다. 새 Source/BP/asset 변경·게임 build/PIE0이며 발표용 기존 구현 설명만 사용했다. 후속 수정은 이 presentation ID를 열어 필요한 내용만 편집한다. 아트 기록은 Docs/Art/ART_WORK_CONTINUITY.md의 같은 날짜 완료 절을 참조한다.


## 2026-10-16 — HeinMach Epic 재패키징 완료·재개 기준

앞선 착수 상태는 완료로 대체한다. Package01 UATexit0(239.366s), 실제 container/ini/binary 검증, 최신 정리본 map hash·cooked chunk 변경/크기 감소, 별도 UserDir Shipping90.234초 시작 관측/crash0이 완료됐다. 결과 C:/Users/user/Desktop/Khazan_Release_20261016/Windows 전체 폴더(41파일/2,111,968,044bytes), 실행 Khazan.exe. 소유 패키징/검사 프로세스는 종료됐고 기존20261015 배포본과 게임 Source/Config/자산은 보존했다.

정확한 재개 근거는 Metadata/Release_20261016/FinalVerification.json·Baseline.json·Package01/{Launch,Exit}.json·UAT.log·PackageReadback.json·IoStoreContents.csv·ReleaseFiles.json·Smoke01/{Launch,Result}.json이다. 필수 잔여=[]. Epic11그룹3/해상도100%, HeinMach 단일 game map, BGM4asset, 진동배율2가 실제 패키지에 포함된다. 정리본 map SHA1d224b14...이다. 시작 관측은 전체 전투/시각/FPS/음악/실물 컨트롤러 검증이 아니다.

후속은 현재 Main과 새 요청을 먼저 확인하고 새 run/output 경로를 사용한다. 기존 runner Scripts/Engineering/package_release_20261015.py에 KZ_RELEASE_TASK/KZ_RELEASE_DEST 환경 경로를 지정할 수 있으며 기본20261015 동작은 유지했다. 완료된 run/검사 output을 재사용해 덮어쓰거나 이미 종료한 PID를 다시 제어하지 않는다.


## 2026-10-16 — 현재 프로젝트 Git main 분할 Push 진행

사용자 요청으로 현재 로컬 프로젝트를 origin/main에 분할 업로드한다. 시작 local/remote main은 7d7cc2db2ad66a9a316169e9736eb979bb57a731로 동일하며 기존 staged 변경은0이다. 초기 변경72,536개/42,891,644,962bytes 중 실제 Source/Config/Content/Docs/Scripts/uproject와 텍스트 Metadata30,553개/9,846,030,742bytes를 선택했다. 과거 에셋 백업·검사 이미지/영상·로그·브라우저 프로필·생성 캐시는41,983개/33,045,614,220bytes이며 로컬에 보존하고 업로드하지 않는다. 기존 추적 파일의 수정/삭제는 모두 포함한다. 이 제외 범위를 사용자에게 안내하고 선택 질문을 제시했으며 별도 응답 없이 안내한 기본 범위로 진행했다. 기존 ignore 정책을 바꾸거나 로컬 파일을 삭제하지 않는다.

전송은 원시 크기 최대768MiB의15개 순차 커밋(VFX7, Art3, gameplay asset1, 텍스트 metadata3, Source/Config/Docs/Scripts1)이다. 기존 Git LFS의 SK*.uasset 규칙과 원래 이력을 유지하고 각 push 뒤 ls-remote로 해당 SHA를 검증한다. 명시 첨부 Source/Khazan/AI/KZMonsterAIController.cpp도 마지막 묶음에 포함된다. 게임 코드/에셋 자체를 수정하거나 새 build/BP compile/PIE를 실행한 작업이 아니다.

중단 시 저장소 루트 .git/codex-main-upload-20261016/{inventory,plan,omitted}.json과 batch-NN.json·batch-NN-push.log를 먼저 읽는다. 정확한 실행은 UE Python(C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe)으로 .git/codex-main-upload-20261016/upload.py batch N이다. 이미 pushed=true인 배치를 반복 준비하지 않고 마지막 원격 main/로컬 HEAD/receipt를 대조해 최초 미완료 N부터 순서대로 재개한다. commit이 저장돼 있고 push만 실패하면 같은 N이 기존 commit의 push만 재개한다. index/HEAD 불일치는 다른 변경 여부부터 확인하고 reset/force-push하지 않는다. 전체 전송 뒤 남은 tracked 변경/선택 누락 및 원격 일치를 검사하고 완료 기록을 추가해 별도로 push한다.

<!-- GitMainSplitPush_20261016_started -->


## 2026-10-16 — 현재 프로젝트 Git main 분할 Push 완료

사용자 요청의 프로젝트 스냅샷을15개 묶음으로 순차 commit/push했고, 각 묶음의 원격 main SHA를 검증했다. 시작은7d7cc2db2ad66a9a316169e9736eb979bb57a731, 최종 스냅샷은0305b6a9a138c7875578042e52b231302983ef89다. 2026-10-16 17:50 KST 검사에서 local HEAD와 ls-remote의 refs/heads/main이 동일했다. 이 완료 문서 기록은 별도 후속 커밋으로 전송한다.

초기 선택30,553개와 base→최종 commit의 변경 경로30,553개가 정확히 일치했다. 선택 누락0, 계획 외 commit0, 잔여 tracked/staged 변경0이다. Source/Config/Content/Docs/Scripts/uproject와 텍스트 Metadata가 포함되며, 첨부한 Source/Khazan/AI/KZMonsterAIController.cpp도 반영됐다. 선택 파일의 초기 원시 크기는9,846,030,742bytes이며 실제 네트워크 전송량으로 해석하지 않는다. 기존 이력·Git LFS SK*.uasset 규칙을 유지하고 강제 push/기존 commit 재작성은 하지 않았다.

제외 목록41,983개/초기33,045,614,220bytes는 검사 시 모두 미추적 상태로 로컬에 남아 있고, 제외 파일이 새로 추적된 사례나 추가 미분류 잔여는0이다. 대상은 과거 binary 에셋 백업, 검사 이미지/영상/오디오, 로그, 브라우저 프로필과 신규 생성 캐시다. 텍스트 Metadata의 원본 근거·보고서·과거 소스/충돌 진단 기록은 보존했다. 기존 ignore 설정을 바꾸거나 제외 파일을 삭제하지 않았다. 전체 working tree가 clean하다는 뜻은 아니며, 프로젝트의 선택 업로드 범위가 완료됐다는 뜻이다.

Git 검증: batch1–11의 staged diff check는 성공했다. batch12–15에는 기존 텍스트의 whitespace/EOF 경고가 있어 그대로 보존했다. conflict-marker12개는 Metadata/BeastDodge_20261012/Rebase02·03/Conflicts 아래 과거 충돌 진단2파일뿐이고, 이번 선택의 현행 Source에는 해당 표식이0이다. 검사 결과를 전체 diff-check 성공이나 새 C++ 빌드 성공으로 표현하지 않는다. 이번 작업의 새 gameplay Source/BP/asset 편집0, UE build/BP compile/PIE0이며 문서에 Git 결과만 추가했다.

로컬 상세 증거는 저장소 루트 .git/codex-main-upload-20261016/{inventory,plan,omitted,snapshot-verification}.json, batch-01.json부터 batch-15.json 및 각 push/diff-check 로그다. 모든 batch의 pushed=true를 확인했다. 앞선 진행/재개 절차는 완료 상태로 대체하며 prepare나 기존 batch를 다시 실행하지 않는다. 후속은 새 요청의 현재 Git 변경과 원격 main부터 확인하고, 로컬 보존 자료까지 추가 업로드하는 작업은 별도 범위로 판단한다.

<!-- GitMainSplitPush_20261016_completed -->
