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
