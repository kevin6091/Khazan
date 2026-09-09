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
