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
