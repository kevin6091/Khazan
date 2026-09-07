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
