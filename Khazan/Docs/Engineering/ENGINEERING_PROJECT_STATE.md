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

## 2026-09-07 InGame 로코모션 마이그레이션 재정의

- 사용자 확정: Animation Sequence는 `/Game/_Art/Kazan/Animation/InGame`만 사용하며, Start는 Sprint에만 적용한다. Walk/Run은 loop로 직접 진입하고 Stop/Turn은 유지한다.
- 현행 마이그레이션과 자세한 첫 절차는 `Docs/Animation/INGAME_LOCOMOTION_MIGRATION.md`에 작성했다. 에셋 목록/marker/RAW pose 표적 검사 결과는 Animation 문서와 `Saved/ImportReports/Khazan_InGame_Locomotion_Audit_20260907.json`을 참조한다.
- 현재 `UKhazanAnimInstance`에는 GameThread snapshot과 AnyThread 파생 계산이 있다. 전면 재작성하지 않고 새 입력/gait/Start 정책에 맞춰 정리하는 계획이다.
- 후속 소스 교정 대상: `KhazanPlayer::HandleInputMove()`의 입력량과 속도 170/470 혼용, Run까지 허용하는 `ResolvedGait != Walk` Start 조건, Sprint 입력/허용 상한 연결, Stop 진입 시 직전 유효 속도와 발 상태 보존.
- 현재 `ABP_Player`는 Walk/Run Sequence Player를 Bool로 선택한다. InGame 밖 Idle/Stop 참조와 loop의 Do Not Sync 설정은 후속 그래프 단계에서 교체한다.
- 사용자 직접 구현 방식에 따라 이번에 C++/BP/시퀀스는 수정하지 않았다. 첨부된 `KhazanGameMode.cpp`의 Cog 창 등록도 변경하지 않았다. 이번 작업 범위에 빌드, BP Compile, PIE 실행은 포함하지 않았다.

### 2026-09-07 2단 고정 속도와 L3 Sprint 요구사항

- 사용자 확정 속도: 왼쪽 스틱의 유효 기울기에서 Walk 170 cm/s, Run 임계값 이상에서 Run 470 cm/s. Sprint 요청은 L3에서만 생성한다.
- 구현 방침: 스틱 크기는 입력 의도/모드 선택에 보존하고, 단위 방향 + AddMovementInput ScaleValue 1과 gait별 MaxWalkSpeed로 고정 목표 속도를 적용한다. 속도 벡터를 강제로 덮어써 가감속을 제거하지 않는다.
- 현재 `MovementInput.Length() <= 170.f`와 입력 벡터의 170/470 배율은 의도한 속도 제어를 만들지 못한다. IA_Move Axis2D와 IMC_Default 기본 Move 매핑(Swizzle), UE 5.8 ScaleInputAcceleration의 최대 길이 1 제한을 표적 확인했다.
- 후속 준비: IA_Sprint Digital(bool), Gamepad_LeftThumbstick(L3) 매핑, Input.Action.Sprint 태그, KhazanInputData 액션 항목, Controller→Player 요청 전달, MaxAllowedGait와 요청 분리. 상세는 Animation 마이그레이션 문서 참조.
- Run 임계값/Sprint 속도/L3 유지 방식은 아직 미확정이다. 이번에는 문서만 추가했으며 사용자 C++/에셋을 수정하거나 PIE를 실행하지 않았다.

### 2026-09-07 HandleInputMove 재검토와 입력/gait 2단계 가이드

- 최신 사용자 코드는 입력 길이 <=0.6에서 MaxWalkSpeed=170, >0.6에서 470을 설정한다. 이전 170과의 입력 비교 문제는 현재 코드의 문제로 반복 보고하지 않는다.
- 남은 핵심: AddMovementInput(WorldInput, 1)에는 원래 스틱 크기가 남는다. 원래 크기는 Intent용으로 보존하고 CMC에는 GetSafeNormal2D 결과를 전달해야 2단 고정 목표 속도가 된다. 로컬 UE 5.8의 ScaleInputAcceleration/ComputeAnalogInputModifier/CalcVelocity에서 근거를 확인했다.
- 아직 SetTargetGait 호출과 L3 요청/바인딩이 없고 MaxAllowedGait는 Run이다. 프로젝트 bMovementAllowed도 CMC가 자동 해석하지 않으므로 이동 입력 경로에서 gate가 필요하다.
- 설명 가이드는 `Docs/Animation/INGAME_LOCOMOTION_STEP_2.md`다. 기존 LocomotionComponent와 GT→AnyThread snapshot은 유지하고 Player의 공통 요청/허용 gait→속도 갱신, Controller 이벤트 전달, native Sprint tag, IA/IMC/DA 연결, AnimInstance bool 소비를 안내한다.
- 실제 DA_InputData는 `/Game/Data/DA_InputData`이며 현재 Move/Turn/Jump/Attack 4개 항목이다. IMC_Default의 Move는 Gamepad_Left2D + YXZ Swizzle이고 action/mapping의 명시적 Dead Zone/Trigger는 없다. 새 IA_Sprint/L3 설정은 예제이지 현재 구현 완료 상태가 아니다.
- 가이드의 SprintSpeed=600, DeadZone=0.1, bToggleSprint=true는 제안 기본값이며 사용자 확정 수치/조작 방식이 아니다. Run 0.6 경계는 현재 사용자 소스를 따른다.
- loop marker/ABP 참조 상세 결과는 Animation 문서와 새 감사 리포트를 참조한다. 이번에는 문서/리포트만 작성했고 C++/BP/에셋에 쓰기, 빌드, Compile, PIE를 수행하지 않았다.

### 2026-09-07 사용자 2단계 테스트 완료와 3단계 책임 분리 안내

- 사용자 보고: 입력/속도/gait 2단계 테스트 완료. 어시스턴트는 현재 코드와 ABP 설정을 읽기 전용으로 확인했으며 별도 빌드/PIE 재검증을 수행한 것으로 기록하지 않는다.
- 현재 Player는 입력 gate/원래 크기 저장/GetSafeNormal2D/ResolvedGait별 속도를 적용한다. HandleInputSprint는 Started 콜백과 일치한다. 실제 Intent의 초기값은 Walk/상한 Sprint이고 AnimInstance 일반 Start는 false다.
- 3단계 안내는 `Docs/Animation/INGAME_LOCOMOTION_STEP_3.md`다. Player는 조작 정책, LocomotionComponent는 요청/허용, CMC는 물리, AnimInstance는 관측/시각 선택, ABP는 재생/전이를 소유하도록 설명했다.
- 새 제안은 AnimInstance에 bIsGrounded/bShouldSprintLoop/RunEnterSpeed/RunExitSpeed 및 내부 UpdateLocomotionSelection_AnyThread 추가다. 기존 snapshot으로 충분하며 Player/Controller에 애니메이션 상태나 재생 시계를 추가하지 않는다.
- 기존 Stop→이동 전이의 미연결 핀을 확인해 3단계 재입력 연결 항목에 포함했다. Stop→Idle의 Automatic Rule은 보존하고 원샷 길이/발 선택은 4단계 작업으로 구분한다.
- UE 5.8 소스에서 ChildUpateMode=Default와 Always Reset on Entry의 조건부 초기화를 확인했다. 제안 bool 16조합과 속도 히스테리시스 예제의 계산 검사는 UE 빌드/PIE 검증을 대신하지 않는다.
- 이번 변경은 문서/리포트뿐이며 사용자의 C++/BP/시퀀스 변경은 보존했다. 3단계 적용과 런타임 검증은 사용자 구현 후 진행한다.

## 2026-09-07 Stop 선택 진단과 enum 기반 4단계 안내

- 현재 코드의 bUseRunStop은 release edge AND bIsStopping에서만 갱신하며 매 프레임 로그는 그 이전 선택값과 현재 속도를 함께 출력한다. ABP CDO 기준값 315와 기존 로그의 600/false→504/true, 이후 0/true를 확인했다. 개별 release 당시 분기/인스턴스는 기존 로그만으로 확정하지 않았다.
- 구조상 취약점은 release snapshot의 감속, 같은 update 내 속도 0으로 인한 조건 불통과, loop 220/190과 Stop 315 경계 불일치, bool 한 개로 세 gait를 표현할 수 없다는 점이다.
- 사용자 직접 적용 가이드: Docs/Animation/INGAME_LOCOMOTION_STEP_4.md. AnimInstance에 loop enum 선택/진입 StopGait·속도·발/지상 입력 이력을 두고 Player/Controller gameplay 책임은 바꾸지 않는다. 독립 사실과 전이 조건은 bool로 남긴다.
- UE 5.8 로컬 소스에서 enum→pose index 조회, GetSyncGroupPosition의 BlueprintThreadSafe/proxy read buffer, NativeThreadSafeUpdate와 asset tick 순서 및 leader 위치 override를 확인했다. 함수 이름만으로 외부 UObject 접근을 thread-safe로 취급하지 않는다.
- 현재 ABP의 Stop 재입력 핀은 연결되어 있다. 실제 사용 상태 이름은 Sprint이고 bool은 bShouldSprint다. 이전 미연결 기준선을 현재 결함으로 반복 보고하지 않는다.
- 어시스턴트 변경은 문서/표적 리포트뿐이다. C++/ABP/시퀀스 변경, 신규 빌드/Compile/PIE를 수행하지 않았고 사용자 변경을 보존했다. 제안 로직의 14개 독립 snapshot 계산 검사는 UE 런타임 검증을 대체하지 않는다.

## 2026-09-08 Stop 이력 조건 반전과 Root Motion 선택 안내

- 현재 사용자 소스는 enum/Stop 진입 이력을 추가했으나 UpdateTransitionData_AnyThread 내부 이력 비교를 if (!bHasPreviousKinematicFrame)으로 감쌌다. 첫 update에는 입력 이력이 false이며 이후에는 비교를 건너뛰므로 일반 release에서 bShouldEnterStop이 발생하지 않는다. 이 비교 블록은 if (bHasPreviousKinematicFrame)이어야 한다. 소스상 확인 가능한 오류이며 디버거 재현이나 직접 수정은 하지 않았다.
- ABP의 현재 Root Motion Mode는 Root Motion from Montages Only다. 일반 Stop Sequence Player의 Enable Root Motion 하나만 켜는 것으로 캡슐 구동 적용까지 완료되는 것은 아니다.
- 사용자 확인에 따라 Sprint Stop은 단일 클립이다. 애니메이션별 연결/마커/root lock 권장안은 Docs/Animation/INGAME_LOCOMOTION_STEP_4.md의 2026-09-08 섹션을 따른다.
- CMC 소스에서 애니메이션 Root Motion 시 일반 CalcVelocity 생략 및 root delta/DeltaSeconds 기반 속도 적용을 확인했다. Root Motion 적용도 CMC 충돌 경로를 사용하며 기존 감속과 무조건 가산되는 것으로 설명하지 않는다.
- 현재 단계는 CMC 제동 유지와 root-locked 인플레이스 Stop을 권장했다. Root Motion Stop을 채택하려면 속도/제동 거리/재입력 handoff/스케일/충돌을 별도 검증해야 한다. NeedsImmediateUpdate의 Everything+유효 root motion 요구 조건에서 Game Thread 실행 경로도 확인했다.
- 어시스턴트는 문서만 추가했다. C++/ABP/에셋을 변경하거나 새 빌드/Compile/PIE를 수행하지 않았다.
