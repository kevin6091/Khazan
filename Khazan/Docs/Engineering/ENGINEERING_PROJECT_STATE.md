# Engineering 프로젝트 상태

> C++, Gameplay BP, Config, 컴파일·런타임, 입력, 피직스 상태만 기록한다.
> FModel 추출, 머티리얼·Level 복원 수량은 기록하지 않는다.

## 2026-08-31 기준

- 기본 맵: `/Game/Maps/DevMap`
- 기본 GameMode: `/Game/Bluprints/BP_GameMode`
- PlayerController: `AKhazanPlayerController` / `/Game/Bluprints/BP_KhazanPlayerController`
- GameInstance: `UKhazanGameInstance` / `/Game/Bluprints/BP_GameInstance`
- AssetManager: `UKhazanAssetManager`
- `DefaultEngine.ini`에 `AssetManagerClassName=/Script/Khazan.KhazanAssetManager`가 설정되어 있다.
- 현재 `DefaultEngine.ini`에는 `GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C`도 존재한다.
- [진단 진행] DevMap 시작 Crash의 첫 원인인 GameInstance 미설정은 현재 Config에 반영됐지만, 프리로드 중 `AssetLabel.PreLoad` 런타임 인덱스 조회 실패와 null 역참조가 후속 Crash를 만든다.
- [수정 미적용] 이번 단계에서는 사용자 요청에 따라 문서 체계만 분리했으며 C++ Crash 수정은 아직 적용하지 않았다.

## 현재 우선순위

1. `UKhazanAssetData`의 runtime index를 asset 재저장에 의존하지 않도록 `PostLoad()` 또는 명시적인 rebuild 함수에서 생성한다.
2. `GetAssetPathByName()`과 `GetAssetSetByLabel()`의 ensure 후 null 역참조를 제거한다.
3. DevMap PIE와 Standalone에서 AssetManager 초기화, InputData, InputAction을 검증한다.
4. 장기적으로 프리로드 책임을 `UKhazanAssetManager::StartInitialLoading()`으로 이동한다.

## 2026-09-02 Locomotion 구현

- [완료] `UKhazanAnimInstance`에 `Idle`, `Start`, `Walk`, `Run`, `Stop`, `TurnInPlace`, `MovingTurn`, `Airborne` 상태 제어를 구현했다.
- [완료] `UKhazanLocomotionProfile` Data Asset 타입을 추가해 무기별 clip/tuning을 런타임 로직과 분리했다.
- [완료] `ABP_Player`는 `UKhazanAnimInstance`를 parent로 사용하며 fallback Idle State Machine 뒤 `DefaultSlot`을 통과한다.
- [완료] `AKhazanPlayer` 이동 설정은 Orient Rotation to Movement, Yaw 540 deg/s, MaxWalkSpeed 600, MaxAcceleration/Braking 1800이다.
- [검증] 정적 감사 `Khazan_Locomotion_Audit.json`이 전체 통과했다.
- [검증] 8.875초 PIE 입력 추적에서 Idle/Walk/Run/Start/Stop, LF/RF, 90/180 MovingTurn과 held-input 비반복을 확인했다.
- 상세 설계와 애니메이션 네이밍은 `Docs/Animation/ANIMATION_LOCOMOTION.md`가 정본이다.

### 2026-09-02 최종 빌드

- UE 5.8 `KhazanEditor Win64 Development` 전체 UBT 빌드 성공.
- Live Coding 산출물에 의존하지 않고 `UnrealEditor-Khazan.dll` 링크와 target metadata 생성을 완료했다.

## 2026-09-03 Locomotion 롤백 및 재설계 상태

> 2026-09-02 Locomotion 구현과 최종 빌드 기록은 당시 결과의 이력이다. 아래 항목이 현재 Locomotion 상태를 대체한다.

- [소스 롤백 완료] `UKhazanAnimInstance`의 수동 상태 머신, gait/발 위상 계산, turn 클립 선택, Dynamic Montage 로코모션 재생을 제거했다.
- [제거 확인] `UKhazanLocomotionProfile` C++ 타입과 `DA_Locomotion_DualAxeSword` 프로필 에셋은 현재 프로젝트에 없다.
- [현재 기준선] `UKhazanAnimInstance`는 소유 캐릭터와 `CharacterMovementComponent`를 캐시하고 `Velocity`, `GroundSpeed`, `bShouldMove`, `bIsFalling`만 갱신한다. 선언된 `Acceleration`은 아직 갱신하지 않는다.
- [보존] DualAxeSword `RT_DAS_*` 런타임 클립 16개와 `ABP_Player`는 후속 데이터 기반 구조의 재료로 남아 있다.
- [변경 없음] `AKhazanPlayer`의 Orient Rotation to Movement, Yaw 540 deg/s, MaxWalkSpeed 600, MaxAcceleration/Braking 1800 설정은 이번 롤백 범위에서 변경하지 않았다.
- [구형 도구] 2026-09-02 빌드/감사/PIE 스크립트와 리포트는 제거된 프로필 및 상태 제어를 전제로 하므로 현재 구조의 재생성·검증에 사용하지 않는다.
- [검증 대기] 최신 롤백 소스의 비-Live-Coding 전체 UBT 빌드와 Editor 내 `ABP_Player` Compile/PIE 확인은 아직 수행 완료로 기록하지 않는다.

### 다음 우선순위

1. 이동 의도와 애니메이션 관측값을 분리한 Locomotion 데이터 계약을 확정한다.
2. 게임 스레드 UObject 수집과 thread-safe 파생 계산의 경계를 만든다.
3. ABP 소비 구조를 정리한 뒤 애니메이션 데이터 품질을 감사한다.
4. 감사 결과가 Motion Matching 검색에 충분할 때 Pose Search/Chooser를 구성한다.
5. 무기별 그래프 구조가 실제로 달라지는 범위에만 Linked Anim Graph/Layer를 적용한다.

상세 현재값과 마이그레이션 원칙은 `Docs/Animation/ANIMATION_LOCOMOTION.md`를 정본으로 삼는다.

## 2026-09-07 Git main 작업 스냅샷

- 사용자 요청에 따라 저장된 현재 작업을 `origin`의 `main` 브랜치에 반영하는 스냅샷이다. 원격 저장소는 `https://github.com/kevin6091/Khazan.git`이다.
- 시작 기준은 로컬 `35b81ec`, fetch로 확인한 원격 `ab30c2f`이며, 기존 미푸시 커밋 1개도 반영 범위에 포함한다.
- 문서 기록 추가 전 변경은 신규 178개, 수정 5개, 삭제 157개다. 애니메이션 및 플레이어 BP, UnrealPSKPSA 플러그인 구성 파일, 기존 에셋 삭제 상태를 함께 보존한다.
- 첨부된 `Source/Khazan/Animation/KhazanAnimInstance.cpp`는 추적 중이며 원격 `main`과 차이가 없다. 이번 작업에서 C++ 동작은 변경하지 않았다.
- 확인 범위는 Git 변경 목록, 원격 브랜치 관계, 전송 대상 파일 크기다. 이번 업로드 작업에서는 UE 빌드, BP Compile, PIE를 실행하지 않았으며 기존 런타임 검증 대기 상태는 유지한다.

### 2026-09-07 GitHub main 반영 완료

- 작업 스냅샷 `afa0976bf6e3da4de983124a91a80f46895c9d5f`의 Push가 성공했고, `git ls-remote --heads origin main`으로 동일한 원격 hash를 확인했다. 기존 `35b81ec` 커밋도 원래 이력을 유지한 채 반영됐다.
- 대용량 전송은 임시 브랜치를 이용한 분할 업로드로 완료했으며, 사용한 원격 임시 브랜치는 삭제했다. 복구 과정은 `Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md`의 2026-09-07 기록을 참조한다.
- 실제 작업 내용에 추가한 변경은 Engineering 작업 기록뿐이며, 이번 업로드로 빌드·런타임 검증 상태가 바뀌지는 않는다.
