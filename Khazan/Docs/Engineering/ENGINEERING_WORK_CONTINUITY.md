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
