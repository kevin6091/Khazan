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

## 2026-09-08 현재 Stop 부분 검증과 SprintStart 안내

- 최신 소스의 bHasPreviousKinematicFrame 조건은 올바른 양수 조건이다. 과거 조건 반전 기록은 현재 결함으로 반복하지 않는다.
- 새 UBT KhazanEditor Win64 Development compile/link/metadata 성공과 새 Editor 실행을 확인했다. DLL 시간 15:53:56, UBT Log.txt Result: Succeeded. 앞선 Rider Live Coding build state의 실패 응답과 달리 Engine 로그에도 Live coding succeeded가 있었으며, 최종 근거는 새 UBT 빌드다.
- Enhanced Input 액션 주입 후 실제 C++ 중단점/스택/멤버로 Walk/Run/Sprint 해제를 확인했다. 직전/현재/고정 속도는 170/0/170, 470/392.245117/470, 600/502.935822/600이다. 각각 StopGait Walk/Run/Sprint와 bShouldEnterStop=true. Foot은 Right/Left/Right. NativeThreadSafeUpdateAnimation→UpdateTransitionData_AnyThread가 Foreground Worker #0/#1에서 실행된 사례다.
- 위 결과는 입력 해제와 Stop 진입 데이터의 검증이다. 실제 모든 ABP 상태 전이, 각 클립 완주, LF/RF 접지, 물리 컨트롤러/IMC 매핑 전수 검증으로 확대 해석하지 않는다.
- 검증 도구의 부적절한 상태 머신 인덱스 조회로 첫 Editor가 종료됐고, 새 실행에서 추가 입력 검사/viewport 캡처 이후 디버거 통신이 중단됐다. 나머지 자동 검사 결과는 회수하지 못했다. 원인 미확정인 두 번째 정지/정리 항목은 ENGINEERING_WORK_CONTINUITY.md의 같은 날짜 섹션을 따른다.
- 리포트: Saved/ImportReports/Khazan_InGame_Stop_Verification_20260908.json. 진단 스크립트: Scripts/Animation/verify_ingame_stop_pie_20260908.py. 전체 테스트 통과 상태가 아니다.
- 다음 사용자가 구현할 SprintStart 기본형은 Docs/Animation/INGAME_LOCOMOTION_STEP_5.md에 기록했다. 기존 스냅샷/Stop을 유지하고 AnimInstance의 새 지상 Sprint 요청 edge/진입 속도/입력 방향각과 ABP 원샷 전이를 설명한다. 실제 C++/ABP/시퀀스는 변경하지 않았다. 현재 실행 상태 복구와 Start 에셋 적합성 확인 후 적용한다.

## 2026-09-08 로코모션 데이터 계약 정본화

- 사용자 요청에 따라 `Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md`를 현재 구현 정본으로 추가했다. Router/AGENTS에서 로코모션 요청의 첫 도메인 문서로 지정한다.
- 현재 소스를 대조해 Controller/Player/Character/LocomotionComponent/CMC/AnimInstance/ABP 책임, Intent→GT snapshot→AnyThread 계산, loop enum과 Stop 진입 데이터/이력의 의미를 정리했다. 과거 가이드의 미적용 변수 이름을 현재 소스 이름으로 오인하지 않는다.
- 최신 사용자 방침은 Walk/Run/Sprint Start 모두 제외다. 현재 bShouldPlayStart=false를 유지하고 앞선 SprintStart 제안을 취소한다. 다음 구현 주제는 Turn이며 이번에 구현하지 않았다.
- 이번 변경은 문서와 작업 지침뿐이다. C++/BP/Config/시퀀스 변경 및 새 빌드/PIE는 수행하지 않았다. 기존 Stop의 실제 진입 데이터 검증과 나머지 미검증/실행 상태 정리 항목은 그대로 구분해 보존했다.

## 2026-09-08 전체 게임플레이 아키텍처 v1 정본 작성 완료

- [설계 완료/구현 미적용] [CHARACTER_GAMEPLAY_ARCHITECTURE.md](CHARACTER_GAMEPLAY_ARCHITECTURE.md)를 후속 캐릭터 기능의 목표 구조 정본으로 추가했다.
- 클래스 기반 제어 HFSM, GAS 액션 수명/취소·비용·적중, 공통 이동 제약/CMC 적용, Main/Locomotion 애니메이션 분리, Player/AI 공유, 보스/레벨 진행과 저장 경계를 확립했다.
- 새 파일을 생성할 시점, 현재 변수/함수의 이관 위치, 취소/실패/사망/늦은 callback 검증, A0–A7 마이그레이션 및 새 필드 제안 checklist를 기록했다.
- [확인] 주요 현행 소스를 다시 읽고 Source/Config/uproject/ABP_Player 39개 파일이 앞선 표적 검토 기준과 동일한 hash임을 확인했다. 이번 문서 작업은 기존 ABP 검사 리포트를 재사용했으며 새 Editor/PIE 검사를 수행하지 않았다.
- [변경 없음] C++/BP/애니메이션/Config/Build.cs를 수정하지 않았다. 빌드/PIE/성능 검증 및 이전 실행 진단 정리 완료를 주장하지 않는다.
- 다음 공동 구현은 공통 이동/제어 기반 A1의 작은 소단계다. 모든 Start 제외, Walk 좌/우 Turn, Run Turn 제외, 별도 SprintPivot, InGame 시퀀스와 현행 root-locked Stop 방침은 유지한다.

## 2026-09-08 사용자 7계층 Tag–Ability 아키텍처 적용성 검토 완료

- [검토 완료/구현 미적용] [설계 정본 하단](CHARACTER_GAMEPLAY_ARCHITECTURE.md)의 “사용자 7계층 Tag–Ability 아키텍처 적용성 검토”에 판정과 보완 계약을 추가했다. 태그/GAS/Effect/Linked Layer/Cue/공간 타격/인터페이스 상호작용 방향은 적용 가능하다.
- [정정] CancelAbilitiesWithTag의 방향과 Asset Tags/Owned Tags 차이를 UE 5.8.2 로컬 소스로 확인했다. 이벤트 전송은 능력 부여/승인 우회/모든 실행의 무조건 취소를 뜻하지 않는다. Notify만으로 프레임 오차가 없어지는 것, arbitrary DataAsset 자동 적용, 체형별 데이터 없이 Ability 공유를 보장하는 설명은 채택하지 않는다.
- [설계 차이] 기존 ARCH-02의 필수 제어 HFSM과 문자 그대로의 전면 태그화는 충돌한다. 공통 태그/효과 원본과 제어·이동 정책의 단일 작성자를 권고했으며 HFSM 유지/축소/폐기는 이번에 확정하지 않았다. 후속 A1은 이 경계를 구체화한 뒤 작은 공통 이동/전투 단계로 진행하고 빈 State 파일부터 생성하지 않는다.
- [검증] 현재 주요 소스와 Build.cs/uproject를 읽었고 저장 리포트가 지정한 39개 게임 파일 hash가 현재 디스크 파일과 일치했다. ABP는 저장 검사를 재사용했다. Editor 미저장 상태, 빌드/PIE/성능/원작 수치의 신규 확인은 없다.
- [변경 범위] Engineering 설계/상태와 Animation 현행 정본에 검토 결과만 추가했다. Source/BP/애니메이션/Config/Build.cs/uproject는 수정하지 않았다. 이번 설명을 직접 게임 구현 요청으로 해석하지 않았다.


## 2026-09-08 아키텍처 v2 채택과 M1 공동 구현 준비 완료

- [설계 확정/게임 적용 전] [아키텍처 v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2)를 필수 개발 기준으로 확정했다. ASC 태그/효과를 공유 상태 원본으로 사용하고, 별도 제어 HFSM을 이번 목표 구조/마이그레이션에서 제거했다. 현행에 FSM 파일이 있던 것은 아니므로 실제 코드 삭제는 없다.
- v2 ARCH-01–19에 Ability/효과/CombatResponse/공통 이동/Main·Linked Layer/Cue/공간/상호작용/AI·진행/초기화·취소 책임을 명시했다. 과거 “미확정” 기록과 v1 A1 선행 State 생성은 이제 현재 개발 절차가 아니다.
- [마이그레이션](CHARACTER_TAG_ABILITY_MIGRATION.md)의 M0–M10과 [M1 가이드](CHARACTER_TAG_ABILITY_STEP_1.md)를 작성했다. 첫 단계는 공통 Character의 엔진 ASC와 인터페이스/ActorInfo lifecycle 연결이다. 사용자가 수정할 예정 파일은 uproject/Build.cs/Character.h/.cpp이며 이번에 적용하지 않았다.
- 현행 Controller Input_Jump의 직접 Jump와 테스트 ForceFeedback 호출도 M3 액션 요청/피드백 이관 항목으로 추가했다. 새 공격만 GAS로 만들고 기존 점프가 승인 규칙을 우회하는 계획을 남기지 않는다.
- [확인] 주요 현행 소스와 저장 검사, UE 5.8.2의 ASC/Interface/ActorInfo/종료 구현을 대조했다. 표적 리포트 대상 39개 게임 파일은 동일 hash다.
- [미수행] 제안 코드 적용/UHT·빌드/BP Compile/PIE/성능/원작 수치 신규 검증. 문서/작업 규칙만 갱신했으며 현재 이동/애니메이션 검증 상태는 유지한다.



## 2026-09-09 GAS와 자체 태그 액션 시스템 비교 검토

- [검토 완료/구현 변경 없음] [구조 정본의 GAS 비교 기록](CHARACTER_GAMEPLAY_ARCHITECTURE.md#gas-versus-custom-action-review-20260909)에 독립 GameplayTags 사용 가능 여부, 제시된 TryAttack/ANS 예제의 생략 책임, 현재 프로젝트의 권고를 기록했다.
- 7계층은 자체 구현도 가능하다. 현재 권고는 Player/적/보스의 실행·효과 수명 요구를 기준으로 GAS를 필요한 범위부터 사용하는 것이다. “싱글이면 GAS가 부적절”, “업계에서 자체 Tag-FSM이 보편적”, “태그/ANS가 자동으로 예외를 없앤다”는 주장은 채택하지 않는다.
- 이번 질문은 대안 검토이며 v2 및 M단계의 변경 결정이 아니다. M1은 여전히 사용자 적용 전이다. 자체 실행기로 전환을 선택할 경우 필요한 ARCH 계약/이관 범위만 조건부로 기록했다.
- [정적 확인] 현재 Character에 ASC/Interface가 없고 Build.cs는 GameplayTags만 직접 사용한다. AnimInstance의 GT snapshot/AnyThread 경계도 유지된다. 저장 리포트가 지정한 게임 파일 39개의 SHA256이 일치했다.
- [검증 한계] 문서만 추가했다. 게임 코드/에셋/Config 변경, 새로운 빌드·PIE·성능 측정 및 미저장 BP 검사는 없다.



## 2026-09-09 자체 Tag-FSM 제안 철회 및 M1 상세 안내 재개

- [사용자 결정] 자체 태그 FSM/액션 실행기로 전환하자는 대안을 철회했다. GAS 기반 v2 / M0–M10이 계속 필수 기준이며 기존 아키텍처를 바꾸는 작업은 없다.
- [설명 완료/적용 대기] [M1 가이드](CHARACTER_TAG_ABILITY_STEP_1.md#m1-resume-detail-20260909)에 Owner/Avatar/Controller 구분, 인터페이스, 헤더 조립 위치, 초기화와 빙의 순서, 종료 수명, 구체적인 사용자 확인 절차를 보충했다.
- 현재 Character/모듈/uproject는 M1 적용 전이다. 사용자가 따라 적용할 범위는 기존 네 파일이며 게임 소스/BP 직접 편집 권한으로 확대하지 않았다.
- [정적 확인] UE 5.8.2 선언/구현과 Epic 공식 API를 대조했고 저장 리포트 대상 게임 파일 39개가 동일 hash다. 이번에 빌드/PIE/새 BP Compile 또는 이전 실행 진단 정리를 수행하지 않았다.
- 다음은 사용자 M1 적용 결과 확인이다. 같은 ASC의 인터페이스 조회, 각 Pawn Owner/Avatar, Controller 갱신, EndPlay와 기존 이동 확인을 거쳐 M2로 진행한다.


### 같은 작업 후속 확인 — M1 플러그인 부분 반영

- Khazan.uproject에 GameplayAbilities / Enabled=true가 추가됨을 확인했다. 마지막 확인 기준 Build.cs/Character는 미적용이며 M1 완료는 아니다. 표적 39개 중 uproject 한 파일만 기준과 다르다. 어시스턴트의 게임 파일 변경은 없으며 신규 빌드/런타임 검증도 없다.



## 2026-09-09 M1 소스 적용 확인, M2.1 상세 가이드

- [사용자 완료 보고/소스 확인] GAS 플러그인·모듈·Character ASC/Interface·ActorInfo 수명이 실제 소스에 반영됐다. M1의 이전 적용 대기 기록은 당시 상태이며 현재는 M2로 진행한다.
- [안내 완료/게임 미적용] [M2 가이드](CHARACTER_TAG_ABILITY_STEP_2.md)를 추가했다. 이번 실제 따라 할 범위는 M2.1 태그 기반 입력 제한/원시 입력 보존/공통 허용 조회/효과별 해제다.
- [후속 미구현] M2.2 데이터·CMC 작성자/제약, M2.3 AI 구동, M2.4 통합 검증이 남는다. Player의 기존 MaxWalkSpeed 쓰기와 AI 직접 이동 경로를 이번 태그 bridge가 이미 해결했다고 기록하지 않는다.
- [소스 근거] SetMovementAllowed/SetMoveInputWorld/Player의 기존 허용 gate가 입력을 지우는 것을 확인했고 native 호출/Anim snapshot 소비를 표적 조사했다. UE 5.8.2 TagEvent/Effect/입력 소비 API를 대조했다.
- [검증 범위] 이번에는 문서만 작성했다. M1 빌드·PIE의 독립 재검사와 M2 Source/BP/에셋 편집·빌드·PIE는 수행하지 않았다. 새 gameplay 튜닝값도 추가하지 않았다.


## 2026-09-09 M2.1 사용자 적용본 crash 원인 확정

- [사용자 적용 확인] Gameplay tag, Locomotion Intent/gate, Player 입력 순서, Anim GT snapshot, `GE_Test_BlockMovement`, Player BP 테스트 노드가 작업 트리에 존재한다. 실행 DLL은 해당 Locomotion cpp보다 뒤에 생성됐고 PIE world도 시작됐다.
- [종료 실패 원인] `UKhazanLocomotionComponent::EndPlay()`의 중복 `Super::EndPlay()`가 UE 5.8.2 `bHasBegunPlay` assert를 일으킨다. 최신 두 crash가 같은 종료 signature를 반복했다.
- [기능 검증 실패] `RegisterGameplayTagEvent()` 반환 delegate를 값 복사한 지역 변수에 callback을 추가했다. ASC 소유 delegate에는 구독이 없으므로 BeginPlay 뒤 Block tag 변화가 Locomotion에 전달되지 않는다.
- [부분 통과] Locomotion ASC 누락 오류 없이 PIE와 Player가 시작됐다. 현재 GE asset은 Infinite/Target Tag/None 설정 데이터를 가진다. 이는 A/B 적용·해제와 이동 차단이 통과했다는 증거는 아니다.
- [현재 단계] M2.1은 수정·전체 빌드·count/handle/이동/종료 재검증 대기다. M2.2로 진행하지 않는다. 게임 C++/BP/asset은 이번 진단에서 직접 수정하지 않았다.


## 2026-09-09 M2.1 수정본 핵심 bridge·종료 수명 통과

- [실제 런타임 통과] 수정된 ASC tag delegate 구독이 동작했다. 실제 Test GE A/B 적용·개별 해제에서 count `0→1→2→1→0`, 활성 효과 `0→1→2→1→0`, Locomotion의 캐시된 허용 `true→false→false→false→true`를 확인했다.
- [종료 통과] 차단 효과를 남긴 Stop PIE와 다음 PIE 시작·종료가 모두 정상이다. 이전 `bHasBegunPlay` assert 이후 새 crash report가 없고 Editor는 계속 응답한다. 이전 PIE의 효과/구독도 두 번째 PIE에 남지 않았다.
- [BP 확인] `BP_KhazanPlayer`는 최신 compile 상태이며 error/warning 0이다. TestASC와 별도 A/B handle이 런타임에 유효했다. 현재 BeginPlay가 적용과 제거를 같은 호출에서 끝내므로 화면상 차단을 관찰할 수 없는 구조다.
- [남은 M2.1 확인] A/B 적용·제거를 네 Custom Event로 분리해 실제 키보드/패드 이동, 차단 중 Released 정리, 최종 재개를 관찰한다. 자동 입력 주입은 프로젝트 binding에 도달하지 않아 합격 근거에서 제외했다. Editor 완전 종료 뒤 전체 Development Editor 빌드도 남는다.
- [단계 경계] 핵심 bridge/효과 handle/종료 수명은 통과했지만 위 수동 입력·전체 빌드 전에는 M2.1 전체 완료로 닫지 않고 M2.2를 시작하지 않는다. 어시스턴트는 게임 Source/BP/asset을 수정하지 않았고 검증 기록만 추가했다.

### 같은 작업 후속 — M2.1 기능 런타임 합격

- 실제 `IA_Move` action 벡터 주입이 프로젝트 binding에 도달했다. Block count 1에서 원시 InputAmount는 1.0으로 보존됐지만 변위/속도/가속도는 0이었고, 효과 제거 후 같은 입력은 387.214 uu 이동과 현재 CMC 속도/가속도를 만들었다.
- 주입 종료 뒤 원시 입력 벡터와 양이 0으로 정리됐으며, 마지막 Stop PIE도 정상 종료했다. 이로써 원시 입력 보존, 출력 gate, 해제 후 재개, Released, 효과/구독 cleanup의 런타임 조건은 통과했다.
- 현재 BP가 효과를 한 프레임 안에 적용·제거해 화면으로 보기 어려운 점은 테스트 UX 문제다. BP compile/실행과 별도 handle 생성 자체는 정상이다.
- M2.1에서 남은 항목은 Editor 완전 종료 후 전체 Development Editor 빌드뿐이다. 그 결과가 성공하면 M2.1을 닫고 M2.2로 진행한다. 이번 추가 검사도 게임 Source/BP/asset을 저장·수정하지 않았다.


## 2026-09-09 M2.1 완료, M2.2·M2.3 상세 구현 안내

- [완료] Editor 종료 상태 전체 `KhazanEditor Win64 Development` 빌드가 `Succeeded / Target is up to date / exit 0`으로 끝났다. 기존 IA_Move, A/B effect count/handle, Released, 반복 PIE 종료와 합쳐 M2.1을 닫는다.
- [표적 조사] `BP_KhazanPlayer`의 실제 부모와 CDO, CMC 값을 commandlet로 읽었다. 소스 생성자 600, BP CDO MaxWalkSpeed 300, BeginPlay 170, 입력 때 gait별 값이 같은 속도를 여러 위치에서 작성하고 있다. 수입 Swordsman/Archer BP 두 종은 `AActor` 부모로 Character/Monster가 아니다.
- [설명 완료/게임 미적용] [M2.2·M2.3 상세 가이드](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-m2-3-detailed-guide-20260909)에 CharacterDefinition, raw intent/resolved policy, intent·constraint handle, CMC 단일 작성자, Player 이관, Anim GT snapshot, Khazan CMC, AIController request ID, PathFollowing pause/resume, Monster/BT/NavMesh/시험 절차를 기록했다.
- M2.2는 먼저 별도 전체 빌드/Player 검증을 거친다. 그 뒤 M2.3을 적용해 RequestPathMove/RequestDirectMove, 차단 중 새 MoveTo, A/B 중첩, abort/도착/실패, 다른 pause, 빙의/종료를 검증한다.
- 이번 요청은 공동 구현 설명이므로 게임 Source/Build.cs/BP/asset에는 제안 코드를 직접 적용하지 않았다. M2.2/2.3은 사용자 적용·빌드·PIE 전이며 M2 전체와 M3도 미완료다.


## 2026-09-11 AssetManager 과잉 보강 복원 후 상태

- 이번만 직접 수정하라는 사용자 승인에 따라 AssetManager/AssetData와 연결된 Controller getter를 Git HEAD의 기존 설계로 복원하고 실제 오류 수정만 남겼다. `GetAssetByName`, 경로 API, FName cache를 다시 사용한다. 구현 계약은 [Source/BP/Config 문서](SOURCE_BP_CONFIG_ARCHITECTURE.md)의 같은 날짜 마지막 절을 따른다.
- 최종 Development Editor 전체 빌드와 DevMap 새 프로세스 시작·종료는 통과했다. Python의 protected index 비교는 수행 불가였으며 실제 이동/Stop PIE는 아직 검증하지 않았다.
- 다음은 M2.2의 Character Definition catalog 연결이다. 실제 `DA_CharacterDefinition_Khazan`은 존재하지만 Character는 여전히 직접 pointer 방식이며 selector/native tag/catalog/BP 연결은 이번에 구현하지 않았다. 시작 검사에서도 Player/Monster Definition 누락이 확인됐다.
- 다음 사용자 적용 안내: [복원 후 Definition 연결 순서](CHARACTER_TAG_ABILITY_STEP_2.md#asset-manager-rollback-next-20260911). 다음 gameplay 코드/에셋을 어시스턴트가 직접 구현할 권한으로 확장하지 않는다.

## 2026-09-15 Definition 선택자/조회 사용자 반영, 에디터 연결 안내

- 사용자 소스에서 Definition native tag, getter의 로드 허용 bool, Character의 선택 태그 및 false 조회/config 전달을 확인했다. `CharacterDefinition` 객체 포인터는 아직 `EditDefaultsOnly`이므로 Transient runtime 참조로 마무리하는 항목이 남는다.
- 다음 사용자 실습은 [Step 2 §29](CHARACTER_TAG_ABILITY_STEP_2.md#definition-editor-followthrough-20260915)의 property 마무리 → cold build → 기존 catalog entry → Player BP tag → 새 프로세스/PIE 검증이다. 추가 이동/AI 클래스를 만드는 단계로 넘어가지 않는다.
- 세 대상 에셋 파일은 존재한다. Rider asset-property 조회가 빈 목록을 반환하고 RiderLink가 미연결이라 catalog/BP의 저장된 선택값과 runtime 상태는 이번에 확정하지 못했다. 빈 tool 결과를 빈 에셋 데이터로 판정하지 않는다.
- `KhazanCharacter.cpp` IDE 오류 분석은 0건이다. 이번 전체 빌드/PIE는 미실행이며 9월 11일 복원본의 검증 결과를 새 사용자 변경의 합격 근거로 사용하지 않는다.
- 게임 파일·수치는 직접 수정하지 않았다. M2.2의 Definition 연결/Player 검증이 진행 중이며 M2.3과 M3는 미착수다.

## 2026-09-15 M2.2 Definition 저장 연결 완료, 런타임 정책 행렬 검증 대기

- PDA_AssetData에는 AssetData.CharacterDefinition.Khazan 항목과 Preload label이 저장됐고, BP_KhazanPlayer selector도 같은 태그를 사용한다. Definition의 이동 config 저장값과 Character의 runtime Definition 계약을 확인했다.
- 현재 입력 자산은 Move/Sprint에 Gamepad만 매핑한다. 키보드 생산 매핑을 추가하지 않고 Enhanced Input 콘솔 주입과 테스트 전용 M2 probe로 Player 입력·제약·태그 차단·cleanup을 검증한다.
- 최근 로그에서 Definition이 없는 시험 Monster 경고는 Player Definition 연결 실패와 구분한다. 현재 변경분의 cold build와 M2.2 전체 PIE 행렬은 아직 통과로 기록하지 않는다.
- 다음 단계는 M2.2 검증 완료이며, M2.3 AI 구동과 M3 공통 액션은 아직 시작하지 않았다.

## 2026-09-15 M2.2 Player 런타임 행렬 통과

- [테스트 BP 직접 정리] `/Game/Test/BP_M2MovementProbe`의 미연결 constraint struct를 보완하고 Gait A 획득/해제를 handle 기반으로 완성했다. 반복 획득 전 이전 handle을 해제하며 BP는 `BS_UP_TO_DATE`로 저장됐다. 수정 전 에셋은 `Saved/CodexBackups/BP_M2MovementProbe_before_takeover_20260915_141814.uasset`에 있다.
- [실제 PIE 통과] Definition→Locomotion→CMC 값 일치, Gamepad mapping을 통한 Walk `170`/Run `470`/Sprint `600`, `IA_Move Completed`의 raw input 정리, gait/rotation 제약 A/B 우선순위와 개별 해제, Block GE count `0→1→2→1→0`, 차단 중 raw input 보존과 해제 후 자동 재개를 확인했다.
- [수명 통과] Sprint/이동 중 UnPossess에서 raw intent/source가 정리됐고 Repossess 뒤 옛 입력 없이 새 input token이 동작했다. Stop PIE 뒤 새 세션은 effect/constraint/input 잔존 없이 시작했다. gameplay assertion/fatal과 Probe 수리 뒤 BP compile error는 없다. 자동화 API 탐색 실패와 별도 WildBoar import 경고는 런타임 합격 판정에서 분리했다.
- [빌드 근거] 정식 `UnrealEditor-Khazan.dll`이 전체 현재 Source보다 새롭고 검증 Editor가 그 모듈 생성 뒤 시작됐다. 이번 턴에 별도 cold-build 명령은 재실행하지 않았다. 물리 패드는 없어 하드웨어 이벤트만 미검증이며 실제 mapping/action은 UE Enhanced Input 콘솔 주입으로 검사했다.
- [현재 단계] M2.2를 완료로 닫는다. 상세 결과는 [Step 2 §31](CHARACTER_TAG_ABILITY_STEP_2.md#m2-2-runtime-result-20260915)과 `Saved/Reports/M2_2_RuntimeProbe_20260915.json`에 있다. 다음은 M2.3 일반 적의 CMC/AIController/PathFollowing 공통 이동 구동이며 M3는 아직 시작하지 않는다.
## 2026-09-15 M2.3-A 현행 구현 안내 준비

- M2.2 완료 뒤 다음 사용자 구현 범위를 M2.3-A native AI 이동 접속으로 확정했다. 공통 CMC, AIController, Character default subobject 교체, Monster 자동 빙의와 첫 cold build가 이번 checkpoint다.
- 기존 M2.3 초안의 낡은 intent 함수명/Definition object 연결을 현행 `BeginLocomotionIntentSource` 계열과 AssetManager selector 계약으로 정정했다. 직접 사용하지 않는 `NavigationSystem` dependency와 테스트 전용 native Definition tag도 이번 범위에서 제외했다.
- UE 5.8.2의 `APawn::PostInitializeComponents()`가 부모 호출 중 AIController를 자동 생성하는 순서를 확인했다. 현행 Character가 부모 호출 뒤 config를 준비하면 AI intent 발급이 먼저 실패하므로, gameplay-world ASC/Definition/Locomotion 초기화를 부모 호출보다 먼저 완료하되 부모 호출은 항상 한 번 수행하는 보강을 필수로 판정했다.
- 이번 작업은 문서와 사용자 구현 설명만 갱신했다. Source/Build.cs/BP/Content는 수정하지 않았고 새 build/PIE도 수행하지 않았다.

## 2026-09-15 P1 진입 재검증 완료, P1-A 사용자 구현 시작

- 최신 v2.1/P1 문서와 실제 GameplayTag, Character, Controller, Definition, Locomotion, Build.cs를 다시 대조했다. P1 Source는 아직 미적용이며 M2.3 AI/custom CMC도 적용되지 않았다.
- Editor 종료 상태에서 현재 작업 트리의 `KhazanEditor Win64 Development` 전체 빌드를 실행했고 UHT, compile, link가 모두 통과해 exit 0 / `Result: Succeeded`였다. XGE license 미활성 경고는 standalone executor 전환 뒤 빌드 성공과 분리한다.
- 직전 Editor 종료 원인은 Content Browser asset rename 중 엔진 `SAssetView.cpp` assert다. P1 코드 실행 실패가 아니므로 P1 선행 차단으로 보지 않는다.
- 현재 공동 구현은 [P1 실습판](CHARACTER_TAG_ABILITY_P1_WALKTHROUGH.md)의 P1-A부터 사용자가 단계별로 적용한다. 어시스턴트는 이번 확인에서 게임 Source/BP/DataAsset/Animation asset을 수정하지 않았다.

## 2026-09-15 GAS 아키텍처 v2.2와 단순성 기준 확정

- [채택] Player 공격·콤보·회피·패링·피격·취소의 실행 권위는 GAS Ability/Task/Tag/Effect에 두고, 이동 물리는 CMC, 이동 제약은 LocomotionComponent, 표현은 Animation, 전투 결과 계산은 해당 Combat 책임에 둔다. Player 전투용 StateTree는 추가하지 않는다.
- [폐기] 기존 P1 ActionRequest/Result, Request/Execution ID 원장, pending handshake, request source 기반 Ready, custom full-body lane 실습판은 미적용 과거 제안으로 확정했다.
- [새 P1] 기존 Input Tag → 최소 Khazan ASC → granted Ability spec → BasicAttack/Jump Ability → Montage Task/Locomotion constraint → GAS failure/end 관측 경로만 구현한다. custom Ability base는 실제 공통 소비가 있을 때만 만든다.
- [감사] 미래 전용 Combat/Response/Targeting/Relationship/Combo graph/AI 타입은 첫 실제 소비까지 보류한다. 현행 Locomotion handle은 검증된 중첩·stale source 소비가 있어 유지하고, 빈 Tick/BeginPlay·미사용 enum/include·불명확한 지역 변수 이름은 다음 관련 Source 정리 후보로 분류했다.
- [적용 범위] 이번에는 Architecture/Migration/연속성 문서만 갱신했다. 게임 Source/BP/DataAsset/Animation asset을 수정하거나 새 build/PIE를 수행하지 않았다.


## 2026-09-15 — capability component 계약 확정과 P1.1 실습판 작성

- 사용자 결정에 따라 Component는 호환 owner에 부착했을 때 이름에 맞는 재사용 능력을 제공하도록 설계하고, 전투를 다수의 미세 Component로 분해하지 않는 원칙을 아키텍처 v2.3으로 추가했다.
- 미래 `UKhazanCombatComponent`는 `IAbilitySystemInterface`를 통해 유효한 ASC를 제공하는 Actor의 공통 hit/damage 교환 경계 한 개로 정의했다. 입력, Ability 수명, combo, montage, Attribute 계산, locomotion, animation, AI/targeting/equipment는 소유하지 않는다.
- 현재 P1에는 다른 Actor와 교환할 hit/damage 소비가 없으므로 CombatComponent는 만들지 않는다. P3.1의 첫 실제 접촉 후보와 같은 변경에서 Player와 적이 함께 쓰는 Component로 도입한다.
- P1을 P1.1–P1.7 cold-build checkpoint로 재편했다. 현재 진입점 P1.1은 `UKhazanAbilitySystemComponent::TryActivateAbilitiesByInputTag` 한 기능과 `AKhazanCharacter` default subobject의 concrete class 교체다.
- `CHARACTER_TAG_ABILITY_P1_MINIMAL_WALKTHROUGH.md`에 파일 위치, 전체 코드, 의미 있는 각 줄, 수명, cold build, Editor/PIE 검증과 실패 진단을 기록했다.
- 이번 기록에서는 게임 Source/BP/asset, `Khazan.uproject`, `Khazan.Build.cs`를 수정하지 않았고 build/PIE를 실행하지 않았다. 실제 적용 결과를 받기 전에는 P1.1 구현 완료로 취급하지 않는다.


## 2026-09-15 — P1.1 build 확인, 전역 Component 기준 정정, P1.2 안내

- 사용자가 P1.1의 `UKhazanAbilitySystemComponent`와 Character concrete subobject 교체를 적용했다. Source는 실습 계약과 일치한다.
- 최신 UBT `Log.txt`에서 UE 5.8.2 UHT, 새 ASC/Character compile, module/DLL link, metadata와 `Result: Succeeded`를 확인했다. XGE license 미활성은 standalone 전환 경고이며 build 실패가 아니다.
- 새 gameplay log/PIE 결과는 아직 확인되지 않아 runtime component class와 M2.2 이동 회귀는 누적 검증 대기다.
- 사용자는 CombatComponent가 특정 설계 요청이 아니라 모든 Component에 적용할 예시였음을 정정했다. Architecture v2.4에서 전역 capability 원칙을 확정하고 P3 CombatComponent 필수 생성을 철회했다.
- 모든 새 Component는 호환 owner에 붙여 완결된 능력, 독립 상태와 cleanup, 공통 API를 실제 제공할 때만 만든다. Ability/Task 지역 상태나 기존 owner의 응집된 함수로 충분하면 Component로 분할하지 않는다.
- 같은 기준으로 P1.2의 별도 `UKhazanAbilitySet`도 보류했다. 현재는 기존 CharacterDefinition에 `InitialAbilityGrants`를 직접 두고 Character가 authority에서 한 번 grant한다.
- 새 P1.2 전체 코드를 실습판에 append했다. 이번 턴에는 사용자가 적용한 P1.1 Source를 변경하지 않았고 새 P1.2 Source/BP/asset도 직접 수정하거나 build/PIE하지 않았다.


## 2026-09-15 — P1.2 build 확인과 P1.3 안내

- P1.2의 `FKhazanInitialAbilityGrant`, Definition getter/배열, Character authority grant loop가 실제 Source에 적용됐고 설계 계약과 일치한다.
- 최신 UE 5.8.2 UBT에서 UHT, compile, DLL link, metadata가 `Result: Succeeded`다. 새 Editor/PIE 증거는 없어 P1.2 runtime과 M2.2 이동 회귀는 누적 검증 대기다.
- 다음 사용자 구현은 P1.3이다. `UKhazanBasicAttackAbility`가 `UGameplayAbility`를 직접 상속하고 `InstancedPerActor`와 Commit/즉시 End 관측만 제공한다. build 뒤 기존 Definition에 native class + `Input.Action.Attack` entry 한 개를 작성한다.
- 이번에는 안내 문서만 append했다. 게임 Source/BP/DataAsset을 어시스턴트가 수정하거나 build/PIE를 새로 실행하지 않았다.

## 2026-09-16 — 싱글 플레이 제품 계약과 WeakAttack native rename 적용

- 프로젝트 목표를 The First Berserker: Khazan의 액션을 실제 완성도로 재현하는 Standalone 싱글 플레이 모작으로 재확정했다. 단계별 test/probe는 품질 gate이며 최종 gameplay를 대체하지 않는다.
- GAS 구현은 tranek/GASDocumentation의 ASC·Spec·Ability instance·AbilityTask 구분을 적극 참고한다. 해당 자료는 UE 5.3 비공식 multiplayer sample 설명이므로 네트워크 구조를 그대로 이식하지 않고, UE 5.8.2 engine source와 현재 싱글 플레이 Architecture를 최종 기준으로 둔다.
- `UKhazanBasicAttackAbility`와 두 Source 파일을 `UKhazanWeakAttackAbility`, `KhazanWeakAttackAbility.h/.cpp`로 직접 변경했다. `InstancedPerActor`를 유지하고 `NetExecutionPolicy=ServerOnly`를 명시했다.
- `DefaultEngine.ini`에 옛 native class path에서 새 path로 가는 class redirect를 추가했다. `DA_CharacterDefinition_Khazan`은 아직 옛 문자열을 직렬화하고 있으나 다음 module build와 Editor load/save에서 redirect로 이관할 수 있다.
- 기존 `Input.Action.Attack`과 CharacterDefinition의 한 grant 구조는 유지한다. 실제 `GA_WeakAttack_Khazan` asset은 아직 없고 P1.5 playback Sequence/Montage/Root Motion 구현도 미적용이다.
- 이번 rename 뒤 cold build, Definition resave, PIE는 실행하지 않았다. 작업 트리에 이미 있던 PlayerController와 `FastAtk04_M1.uasset` 사용자 변경은 수정하지 않았다.

## 2026-09-16 P1.5 최신 절차 재검토

- 사용자가 아직 P1.5를 적용하지 않았다고 확인해 실제 Source와 원작 WeakAtk01 metadata, UE 5.8 `AbilityTask_PlayMontageAndWait` 구현을 다시 대조했다.
- 제품 P1.5에서 원작 근거 없는 `MaxAllowedGait=Run` 임시 constraint를 제거했다. 현재 범위의 실행 자원은 Dilation·Root track이 bake된 playback Sequence를 재생하는 Montage task 한 건이다.
- UE 5.8의 blend-out 뒤 interrupt 누락 조건을 확인해 task의 `bAllowInterruptAfterBlendOut`을 `true`로 정정했다. 종료 delegate는 completed/interrupted/cancelled만 사용하고 Blend Out 자체에서는 Ability를 끝내지 않는다.
- 원작 `Step1.AnimBlendAlpha=0.1`과 `RigRotToTarget.StartBlendTime=0.24/EndBlendTime=0.3`의 소유 객체가 서로 다름을 확인했다. 후자는 Montage blend 근거가 아니다.
- 이번 작업은 설명과 Engineering 문서 보정만 수행했다. 게임 Source/BP/AnimSequence/Montage는 추가 수정하지 않았고 build·PIE도 실행하지 않았다.

## 2026-09-17 P1.5 Montage 시작 확인 및 추상화 검토

- 사용자가 P1.5 절차를 적용해 좌클릭 시 WeakAttack Montage가 재생됨을 확인했다. 현재 Source와 로그에서도 `PlayMontageAndWait`를 통한 `Attack01` 시작 경로를 확인했다.
- 시작 재생은 확인됐지만 강제 cancel, 다른 Montage interrupt, Blend Out 직후 interrupt, PIE 재진입 cleanup은 이번 검토에서 실행하지 않았다.
- 별도 Montage interface나 정적 utility는 현재 한 소비자와 엔진 `UAbilityTask_PlayMontageAndWait`의 기존 책임을 고려해 추가하지 않는 것으로 판단했다. 우선 가능한 정리는 Ability 내부 task 시작 함수 추출과 중복 abort callback 통합이다.
- P3/P6에서 Montage와 GameplayEvent 대기 계약이 여러 Ability에 실제로 반복되면 game-specific AbilityTask 공통화를 다시 판단한다.
- 이번 작업은 설명과 Engineering 문서 상태 갱신만 수행했다. 게임 Source/BP/asset은 수정하지 않았다.

## 2026-09-17 공격 조합·유지 입력 아키텍처 감사와 다음 단계

- 실제 Source는 여전히 단일 `Input.Action.Attack`의 `Started`만 ASC `TryActivateAbility()`에 전달하며 active Spec press/release, Right Mouse Button, combo buffer와 charge release 소비가 없다. 실제 `AM_DAS_WeakAtkCombo`도 `Attack01` segment/section 한 개만 가진다.
- 원작 metadata에서 Weak=`SkillM01/FastAttack`, Strong=`SkillM02/StrongAttack`, 혼합 `SkillM01 + SecondInputType SkillM02`, `Pressed`, Strong `Released`, charge step을 확인했다. 따라서 기존 아키텍처의 Ability-local node/window/buffer 소유 방향은 유효하지만 단일 Attack tag/input phase 계약은 불충분하다고 판정했다.
- ARCH-33/34/35로 Weak/Strong 의미 입력, Started/Completed/Canceled 번역, ASC의 GAS generic press/release protocol, Ability-local combo/charge 상태, 혼합 입력의 typed Gameplay Event 지연 도입을 확정했다. `InputBufferComponent`, 전역 FIFO, 거대 ComboManager, Enhanced Input Hold trigger는 도입하지 않는다.
- 저장된 `PlaybackEvents.json`에서 WeakAtk01의 별도 `ReserveInput`/`SkillInputProg` 후보와 Strong Start/Charge release 창의 Dilation 변환 시간을 확인했다. Weak Step1의 Pressed→Step2 graph 연결과 NotifyEnable 조건도 확인해 reservation/capture와 progression/consume을 두 지역 window로 분리하기로 했다. 정확한 proprietary begin/end 부작용과 Strong state branch는 원작 runtime 소비 연결을 더 확인한 뒤 적용하며 임의 buffer/hold 임계값을 넣지 않는다.
- 다음 사용자 구현은 P1.6-A다. native Weak/Strong tag 추가와 asset 이관 후 ASC `AbilityInputTagPressed/Released`, Controller의 양쪽 키 Started/Completed/Canceled를 연결한다. 이 단계에서는 2타나 Strong Ability를 가짜로 실행하지 않는다.
- 이후 P6-A에서 `DAS_Khazan_WeakAtk02`와 `Attack02`, `WaitInputPress(false)`, 지역 buffer/window로 01→02 한 edge를 검증하고, Strong과 혼합 branch는 독립 checkpoint로 확장한다.

## 2026-09-17 — Enhanced Input Combo와 연타 queue 아키텍처 검토

- 실제 Source는 여전히 단일 `Input.Action.Attack/Started` 활성화만 지원하며 현재 입력 queue는 없다. 활성 WeakAttack 중 추가 클릭은 Ability에 전달되지 않고 미래 section용으로 보존되지 않는다.
- 로컬 UE 5.8에서 `UInputTriggerCombo`와 관련 step/cancel 타입이 deprecated이며 validation도 미래 제거 warning을 발생시키는 것을 확인했다. 이 기능은 순서 패턴만 인식하고 montage window, Ability 수명, unlock/cost를 알지 못하므로 전투 콤보 기반으로 채택하지 않았다.
- Enhanced Input은 Weak/Strong의 press/release/cancel edge까지만 만들고, ASC는 Spec 입력 protocol을 중계하며, 활성 Attack Ability가 원작 Notify window와 read-only Combo Definition을 사용해 branch를 결정하는 계약을 유지했다.
- P6의 연타 queue는 node-local 단일 slot과 `first accepted input wins`로 시작한다. 추가 난타를 FIFO로 쌓아 여러 미래 타를 자동 실행하지 않으며, section 진입 뒤 재arm하고 cancel/interruption/end에서 reset한다. 원작 overwrite 정책은 미확인으로 남겼다.
- `CombatInputBufferComponent`가 montage/window/tree를 중재하는 안은 상태 이중화 때문에 채택하지 않았다. 실제 cross-Ability recovery queue나 공유 command history가 생길 때 semantic event history만 소유하는 작은 구조를 다시 검토한다.
- 이번 검토에서는 게임 Source, BP, InputAction, Montage asset을 수정하거나 build/PIE를 수행하지 않았다. 다음 적용 단계는 기존 P1.6-A이며 InputAction에 Combo/Hold/Chord trigger를 추가하지 않는다.
- 이번 작업은 Engineering 문서만 append했다. 게임 Source, InputAction, MappingContext, DataAsset, Blueprint, Montage는 수정하지 않았고 build·PIE도 수행하지 않았다.

## 2026-09-17 — P1.6-A 착수 직전 실제 이름과 Source 재확인

- 현재 실제 asset은 `GA_Player_WeakAttack`, `AM_DAS_WeakAtkCombo`이며 이번 단계에서 이름을 변경하지 않는다.
- 현재 `UKhazanWeakAttackAbility`는 지역 `UAbilityTask_PlayMontageAndWait* Task`만 사용한다. 선언되지 않은 `MontageTask` 대입은 최신 디스크 Source에 없으므로 별도 수정이 필요하지 않다.
- 현재 task의 `OnCancelled`가 기존 abort handler에 연결되지 않은 P1.5 잔여 결함을 확인했다. Montage 시작 실패와 external task cancel 뒤 active Ability 잔류를 막기 위해 첫 cold build 전에 해당 delegate bind 한 줄을 추가해야 한다.
- P1.6-A의 적용 범위는 native Weak/Strong input tag, 두 InputAction과 IMC/DataAsset 연결, ASC의 pressed/released Spec protocol, PlayerController의 Started/Completed/Canceled 번역이다. Ability combo state와 Strong Ability는 아직 추가하지 않는다.
- 이번 작업은 실제 프로젝트 재확인과 공동 구현 절차 보강만 수행했다. 게임 Source/asset 변경, cold build, PIE 검증은 사용자가 절차를 적용한 뒤 수행한다.

## 2026-09-17 — P1.6-A 사용자 적용 감사와 P6-A 안내

- 새 Weak/Strong native tag, InputAction 둘, IMC와 InputData 연결, Weak CharacterDefinition grant, ASC generic press/release adapter, Controller phase callback이 실제 Source/asset에 반영됐다. UBT `Result: Succeeded`, 새 module DLL, PIE의 반복된 WeakAttack `Attack01` 시작을 확인했다.
- 완료 gate에는 두 보정이 남았다. `Input_WeakAttackCanceled()`가 press를 재호출하는 오타를 release로 고쳐야 하며, `DA_InputData`에서 누락된 `Input.Action.Jump → IA_Jump` row를 복구해야 한다. 현재 PIE 로그에도 Jump lookup error가 있다.
- 다음 공격 구현은 P6-A다. `DAS_Khazan_WeakAtk02`를 `AM_DAS_WeakAtkCombo`에 추가하고, generic begin/end GameplayEvent window NotifyState, 네 event tag, Weak Ability의 reservation/advance depth·buffer 한 건·`WaitInputPress(false)`·`Attack01→Attack02` section 확정을 연결한다.
- 겹치는 원작 reservation 창 때문에 bool 대신 지역 depth counter를 사용한다. ASC, Controller, AnimInstance, 별도 Buffer Component에는 combo mutable state를 추가하지 않는다.
- 이번 턴에는 설명과 Engineering 문서만 갱신했다. 게임 Source/asset, build, PIE는 직접 변경하거나 실행하지 않았다.

## 2026-09-17 — P6-A window transport 단순화 감사

- 사용자가 Jump DataAsset row 삭제가 의도된 시험 기능 제거라고 확인했다. 이전 Jump row 복구 항목은 취소됐다. 실제 Controller의 Weak Canceled callback은 현재 Released 전달로 보정돼 있다.
- UE 5.8 engine source와 현재 Montage를 다시 확인해, P6-A에는 custom GameplayEventWindow NotifyState와 window event tag 네 개를 추가하지 않기로 했다. 내장 `Montage Notify Window`의 두 Notify Name과 AnimInstance Begin/End delegate를 활성 WeakAttack Ability가 직접 구독한다.
- 원작 `ReserveInput`/`SkillInputProg` playback 구간, 서로 다른 두 의미, depth counter, Ability-local one-slot buffer와 runtime section link 계약은 유지한다. ASC는 현재 pressed/released Spec protocol 이상으로 확장하지 않는다.
- 현재 `AM_DAS_WeakAtkCombo`는 Attack01 section/segment 한 개, notify 0개이며 Attack02 Sequence는 Root Motion/Force Root Lock true, Rate Scale 1.0, 길이 3.3280539513 s다. UE는 새 section을 이전 section의 next로 자동 연결하므로 editor에서 authored link를 None으로 되돌리는 절차가 필요하다.
- 이번 재검토는 read-only Source/asset/engine 검사와 Engineering 문서 append만 수행했다. 게임 Source와 Content asset은 수정하지 않았고 build/PIE도 새로 실행하지 않았다.

## 2026-09-17 — 지속 가능한 최소 설계 기준 확정

- 모든 후속 Source·아키텍처 제안은 새 타입을 제시하기 전에 엔진 기능과 기존 owner로 해결 가능한지, 확인된 카잔 최종 기능을 감당하는지, 마이그레이션 전용 구조가 남는지를 필수 심사한다. 적은 코드 자체보다 확정된 제품 범위를 유지하는 최소 계약을 선택한다.
- P6-A는 custom event/notify/task 계층을 만들지 않되 2타 전용 bool과 함수로도 고정하지 않는다. 활성 WeakAttack Ability의 한 칸 `FGameplayTag` buffer와 현재 section 기반 transition 함수가 1–5타 및 확인된 혼합 입력까지 같은 책임 경계로 확장된다.
- 이번 반영은 설계 정본과 절차 문서만 갱신했다. 게임 Source, Blueprint, Montage와 Input asset은 수정하지 않았고 build·PIE도 수행하지 않았다.

## 2026-09-17 — P6-A 조기 combo cross-fade 설계 확정

- 사용자가 지적한 full recovery sequence 사이의 부자연스러운 끝 연결을 반영해 UE 5.8.2 montage section 이동과 montage replay 동작을 표적 확인했다. section next/jump에는 segment cross-fade가 없으므로 기존 `Attack01 -> Attack02` runtime next-section 안을 폐기했다.
- 최종 P6-A는 full Attack01/02 segment와 authored Next `None`을 유지한다. 합법 window 입력 시 현재 `PlayMontageAndWait` task를 `EndTask()`하고 같은 `AM_DAS_WeakAtkCombo`를 `Attack02` section에서 다시 재생해 현재 `0.1 s Hermite Cubic` Blend In으로 조기 교차 전환한다. 무입력 Attack01은 full recovery까지 완료한다.
- 같은 asset의 이전 montage instance가 blend-out 중 남을 수 있으므로 Ability가 active montage instance ID를 저장하고 Notify payload의 asset과 ID를 함께 검사한다. root motion은 새 Attack02 montage instance가 이어받으며 translation scale은 `1.0`을 유지한다.
- current ASC가 active Spec의 Ability `InputPressed()`를 이미 호출하므로 P6-A는 `WaitInputPress` task를 추가하지 않는다. 즉시 section/instance가 교체되므로 별도 `bTransitionCommitted`도 추가하지 않는다. custom notify/event/task와 전역 buffer component 역시 만들지 않는다.
- 이번 작업은 read-only 원작 metadata·현재 asset·UE engine source 검사와 Engineering 문서 append만 수행했다. 게임 Source와 Content asset은 수정하지 않았고 build·PIE도 새로 수행하지 않았다.

## 2026-09-17 — 캐릭터 아키텍처 v3 전면 재감사

- UE 5.8.2 engine source 기준으로 `Montage_JumpToSection`은 대상 section 위치로 즉시 `SetPosition()`하며 Montage Blend In/Out을 다시 적용하지 않는 것을 확인했다.
- Inertialization은 section jump의 pose pop 완화에 유효하지만, 다음 section 첫 frame Notify 방식은 경계 marker 누락 가능성과 현재 설치본에 해당 내장 Notify가 없다는 이유로 제외했다. 최신안은 `ComboCommit` 코드에서 `RequestMontageInertialization()`을 요청한 뒤 GAS의 `MontageJumpToSection()`을 호출한다.
- 현재 ABP의 Inertialization 노드는 `DefaultSlot`보다 앞에 있어 Slot request를 받을 수 없다. 기존 노드를 `DefaultSlot` 뒤, 향후 IK 전으로 이동하는 안을 문서에 확정했으며 asset에는 아직 적용하지 않았다.
- 현행 WeakAttack 515줄 실행, 빈 Ability base, 복제 input callback, custom asset registry, 빈 Tick/BeginPlay, 미사용 Anim snapshot, native presentation hardcode, 미래 Manager/Component 선행안 등을 단순화 대상으로 집계했다. Locomotion constraint handle, ASC exact tag→Spec scan, 한 칸 buffer, Root Motion, Game Thread snapshot 경계는 유지 대상으로 판정했다.
- [Architecture v3](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v3-native-minimal-20260917), [P6 v3 이관](CHARACTER_TAG_ABILITY_MIGRATION.md#p6-native-inertialization-v3-20260917), [Source/BP asset 이관](SOURCE_BP_CONFIG_ARCHITECTURE.md), Animation 현행 정본을 갱신했다. Source·Config·Blueprint·Montage·AnimSequence는 수정하지 않았고 cold build/PIE도 새로 수행하지 않았다.

## 2026-09-18 — P6-v3.1 적용 직전 실물 재확인

- 실제 Montage는 `Attack01`/segment 하나/Notify 0개이며 Source만 `Attack02`와 구 window를 가정한다. Sequence 01–05의 Root Motion과 Force Root Lock, Rate Scale 1.0은 유지돼 있다.
- 증분 전체 build는 성공했지만 Controller가 재컴파일되지 않았다. Controller single-file compile로 `Engine/LocalPlayer.h` 누락 오류를 재현했고 ASC single-file compile로 `AbilitySpec.ActivationInfo` deprecation 두 건을 재현했다.
- 빈 native Ability base를 직접 부모로 삼는 `GA_GamePlayAbility` asset이 있으므로 base 삭제는 현재 combo 이관에서 제외했다. 참조 asset 정리와 함께 별도 checkpoint로 수행한다.
- 최신 실제 적용 절차는 Migration의 [P6-v3.1 체크포인트](CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-1-current-checkpoint-20260918)다. 첫 gate는 01→02 한 task Jump, code-side inertialization, Root Motion/locomotion 회귀까지다.
- 이번 확인은 Source/Content를 수정하지 않았고 PIE를 수행하지 않았다.

## 2026-09-18 — P6-v3.1 2타 미전환 원인 확정

- 사용자 적용본은 `AM_DAS_WeakAtkCombo`에 `Attack01`/`Attack02`와 이름이 정확한 `ComboInputOpen`/`ComboCommit` 점 Notify를 저장했다.
- `UKhazanWeakAttackAbility`는 activation에서 runtime state를 `INDEX_NONE`으로 reset한 뒤 Attack01 재생 성공 시 `CurrentComboStepIndex=0`을 설정하지 않는다. 이 때문에 Commit마다 유효 index 검사에서 반환해 Jump가 실행되지 않는다.
- 최소 보정은 첫 task `ReadyForActivation()` 전에 `CurrentComboStepIndex = Attack01Index`를 설정하는 한 문장이다. 새 상태나 타입은 필요하지 않다.
- 저장된 두 Notify의 Tick Type은 `Queued`로 확인됐다. 현 증상의 원인은 아니지만 확정 contract의 `Branching Point`와 다르므로 코드 보정 뒤 함께 바로잡아야 한다.
- 자세한 흐름과 검증 gate는 Migration의 [P6-v3.1 01→02 전환 차단 원인](CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-1-attack02-blocker-20260918)에 기록했다. 이번 점검은 read-only Source/asset 검사와 문서 갱신만 수행했다.

## 2026-09-18 — P6-v3.2 콤보 후반 입력과 Root Motion recovery 전환 확정

- 사용자 보정 후 Attack01→Attack02는 동작한다. 다음 결함은 Commit 뒤 입력이 버려지는 좁은 콤보 창과 Attack02 Root Motion Montage가 자연 종료될 때까지 locomotion capsule 구동이 나타나지 않는 것이다.
- WeakAttack/Blueprint에는 이동 차단 tag가 없고 raw move intent는 계속 기록된다. ABP가 `Root Motion from Montages Only`이고 CMC가 Anim Root Motion velocity로 일반 velocity를 덮는 것이 현재 정지의 직접 원인이다.
- ARCH-44에서 콤보를 `ComboInputOpen → ComboCommit → ComboInputEnd`의 3상태 입력으로 개정했다. Open–Commit은 고정 Commit까지 buffer, Commit–End는 입력 즉시 Jump, End 뒤에는 닫는다.
- 외부 행동 전환은 combo End와 분리한다. 첫 수직 절편은 `RecoveryCancelOpen` 한 point, 보존된 Locomotion raw intent, point 이후 Move Started event로 WeakAttack을 조기 종료하고 task의 native Montage Blend Out으로 locomotion에 복귀한다.
- 현재 저장 Montage의 두 point는 각각 `0.220553502 s`, `0.529886901 s`, Tick Type `Queued`다. 새 End/Recovery point와 Branching Point 전환은 아직 적용되지 않았다.
- 상세 계약과 다음 적용 순서는 Architecture [ARCH-44](CHARACTER_GAMEPLAY_ARCHITECTURE.md#arch-44-three-phase-combo-and-recovery-exit-20260918)와 Migration [P6-v3.2](CHARACTER_TAG_ABILITY_MIGRATION.md#p6-v3-2-three-phase-input-recovery-exit-20260918)이다.

## 2026-09-27 — Notify/Edge 기반 Player 콤보 수직 절편 동작 확인

- 현재 Source와 Content에는 `InputOpen/InputCommit/InputEnd/HoldCommit/HoldEnd`, held command set, 공통 Action InputEnd, Edge 조건의 Hold·Move·추가 held·owner tag, local section 전환과 Combo Entry Ability handoff가 적용됐다.
- 사용자는 콤보 시스템 동작을 확인했다. 같은 날 PIE 로그에도 Weak 1→4, Strong 1→3, StrongCharge→StrongChargeAttack 전환과 정상 PIE teardown이 남아 있다.
- `KhazanEditor Win64 Development` UBT 검사는 성공했으며 현재 module DLL은 최신 Source 뒤에 생성됐다.
- 현재 Player 콤보/차지 실행 기반은 다음 기능을 올릴 수 있는 상태다. 전체 캐릭터 아키텍처 구현은 완료되지 않았다. Stamina/Cost, hit·damage·HP, HitReact/Death/Cue, Jump 경로의 제품 필요성 판정·정리, Monster AI, 회피·방어, 타깃·워핑, 상호작용과 Encounter가 남아 있다.
- 다음 우선순위는 P2 최소 Stamina Cost 한 경로, 이어서 P3 WeakAttack01의 실제 적중→피해→반응→사망→Cue 수직 절편이다. Combo 쪽은 새 추상화를 늘리지 않고 DataAsset validation과 실제로 필요한 cross-Montage Edge만 요구가 생길 때 보강한다.

## 2026-09-27 — 다음 제작 우선순위 변경

- 사용자 결정으로 다음 순서는 `P2 Stamina/Cost → LockOn Walk·Run 8방 → Dodge motion/cost → P3 hit·damage`다.
- 현재 세 기능은 미구현이다. LockOn enum/policy/snapshot과 InGame 8방 Walk·Run 시퀀스는 존재하지만 target 수명과 ABP pose 소비가 없고, AttributeSet/Cost GE/Dodge Ability·Input·Montage는 없다.
- read-only asset 검사에서 LockOn 16개는 in-place loop 세트, Combat Dodge M1 8개는 root-first Root Motion 세트로 확인됐다. 세부 수치와 경로는 Animation 현행 정본의 2026-09-27 절에 기록했다.

## 2026-09-29 — Stamina regen 완료 보고 후 LockOn 진입 상태

- 사용자는 Stamina regen GameplayEffect를 마저 완성했다고 보고했다. 정적 저장본에는 `Stamina/MaxStamina` AttributeSet, 초기 Stamina Effect, Regen/Delay Effect와 관련 태그가 존재한다. 이번 점검에서 수치와 PIE 동작은 새로 검증하지 않았다.
- 현재 작업 대상은 LockOn L1이다. `KZPlayer.h/.cpp`에는 target weak pointer, movement constraint handle과 함수 골격이 추가됐지만 함수 본문, 매 프레임 target yaw 갱신, target invalid/UnPossess cleanup은 아직 구현되지 않았다.
- LockOn 정책은 Player가 target 수명과 자기 constraint handle을 소유하고, LocomotionComponent가 Run 상한·LockOn 회전 정책을 합성하며, CMC가 실제 capsule 회전을 수행하는 기존 ARCH-68 경계를 유지한다.
- 이번 설명 작업은 Source/Content를 수정하지 않았고 build/PIE를 수행하지 않았다.

## 2026-09-29 — LockOn 화면 중앙 획득 계약 확정

- [설계] 화면에 투영되고 Visibility가 확보된 `AKZMonster` 중 정규화 화면 중심 거리 제곱이 가장 작은 한 대상을 첫 LockOn target으로 선택한다. 검색은 입력 Started 시 한 번만 수행한다.
- [구조] 검색·현재 target·anchor·camera·constraint cleanup이라는 독립 수명이 생겨 `UKZTargetingComponent`를 Player에 두기로 했다. ARCH-68의 Player 직접 소유 최소안은 ARCH-69가 대체한다.
- [높이] `TargetLocation.Z=PlayerLocation.Z` 계약은 폐기했다. Monster별 `LockOnTargetPoint`의 full 3D 위치를 camera LookAt에 사용하고 capsule은 기존 CMC Yaw 경로로만 회전한다.
- [원작] 공통 LockOn skeleton socket은 확인되지 않았다. 원작 Character metadata에는 캐릭터별 `xxLockOnSphereComponent`가 있고 `LookAt01`은 별도 머리 시선 socket이다. Art 정본은 `Docs/Art/LOCKON_TARGET_ANCHOR_AUDIT_20260929.md`다.
- [camera] 현재 `BP_Player` SpringArm은 Pawn Control Rotation 사용, camera/rotation lag off다. Controller full LookAt을 `RInterpTo`로 보간하고 CMC는 그 Yaw를 기존 RotationRate로 따른다. 첫 임시 보간값은 `12.0 1/s`이며 원작값이 아니다.
- [toggle] 첫 입력은 검색 후 Start, 두 번째 입력은 검색 없이 Stop한다. Lock 중 manual turn은 차단하고 Stop 뒤 현재 camera 방향에서 수동 입력을 재개한다.
- [Stamina] 사용자는 Stamina 재생 GameplayEffect 완료를 보고했다. 이번 작업에서는 해당 asset의 runtime 재검증을 수행하지 않았다.
- [변경 경계] 게임 Source/Content/Input asset은 수정하지 않았다. 문서와 read-only metadata/asset 감사만 갱신했으며 build/PIE는 미실행이다.

## 2026-09-29 — HeinMach 공통 월드 이동 기반 적용·검증 완료

- `AKZLevelRouteCollisionActor`가 원작 route wall 2,281개를 hidden HISM collision으로 저장하고, `AKZNavMeshBoundsBox` 242개와 `AKZNavModifierBox` 26개가 source box transform을 직렬화한다. `NavigationSystem` module 의존성을 추가했다.
- 맵에는 원작 NavLink 14개와 원본 자동 경로에서 계산한 forward compatibility link 10개가 있으며, Player/AI별 이동 코드를 복제하지 않고 CMC와 PathFollowing이 같은 월드 데이터를 소비한다.
- HeinMach World Settings는 `BP_GameMode`, 프로젝트 `GameDefaultMap`은 HeinMach다. `EditorStartupMap`은 DevMap을 유지한다.
- 일반 Editor에서 Recast build/save 후 원작 1,485점·1,422구간과 source link 필수 방향 19/19가 통과했다. PIE `BP_Player`는 DualAxeSword 장착 상태로 약 `706.74 cm` 지상 이동했고 source wall이 Pawn을 막았다.
- `KhazanEditor Win64 Development`와 4개 HeinMach Python script compile이 성공했다. commandlet exit 1은 script 실패가 아니라 기존 `GameFeatureData` ensure이며 report status를 별도로 확인했다.
- Encounter/적 spawn/전투 학습, 상호작용, 특수 drop 실행은 이번 월드 이동 기반에 포함하지 않았다. 구조 계약은 Architecture의 ARCH-70, 원본 수치는 Art의 `HEINMACH_PLAYABILITY_COLLISION_20260929.md`를 따른다.

## 2026-09-30 — Player·보스 camera attachment read-only 분석

- 현재 `BP_Player`는 `CollisionCylinder → SpringArm → Camera` 구조다. SpringArm과 Camera의 Socket Name은 `None`이며 gameplay camera는 animated mesh에 직접 붙지 않는다.
- Player mesh의 `Cine_Cam_Start/End`는 authored socket이 아닌 `Root` 직속 reference bone이지만 UE attach API에서 유효하다. 원작 StormPass metadata는 별도 CineCameraActor가 `Cine_Cam_End`를 실제 사용한 사례를 보존한다.
- `UKZLockOnComponent`는 target 검색에서 현재 view를 읽는다. 매 프레임 활성 경로는 Player actor 위치와 Monster `LockOnTargetPoint`로 control rotation을 계산하며, camera 위치 pivot 블록은 현재 주석 상태다. CameraComponent/SpringArm의 parent나 attachment는 변경하지 않는다. `LockOnTargetPoint`는 view target anchor이며 camera mount가 아니다.
- Yetuga/BigBear Blueprint에는 camera/spring arm component가 없고, Yetuga 본체·IceRock 보조 mesh와 BigBear 및 원작 Skeleton metadata에는 camera/cine 전용 socket이 없다. `LookAt01`은 머리 시선 기준으로 유지한다.
- 세부 애셋 근거는 Art의 [CHARACTER_CAMERA_MOUNT_AUDIT_20260930.md](../Art/CHARACTER_CAMERA_MOUNT_AUDIT_20260930.md)다. 이번 분석에서 C++/Blueprint/Content는 수정하지 않았고 build/PIE도 수행하지 않았다.

## 2026-09-30 — LockOn 카메라 내려다보기 각도 제한 적용

- 현행 `UKZLockOnComponent::UpdateLockOnFacing()`의 `ToTarget.Z` 거리 범위 제한 `[-50, 250] cm`를 제거했다. 수평 거리가 짧아지면 같은 높이 차도 급한 음수 Pitch가 되던 원인을 각도 한계로 바꿨다. `Player actor + 250 cm` pivot, target anchor, yaw 보간, SpringArm attachment와 LockOn 수명은 유지했다.
- Component defaults에 `MaxLookDownAngleDegrees=20°`를 추가했다. 원작 metadata 미확인 **임시 튜닝값**이며 양의 크기로 저장하고 실제 음수 Pitch 하한에 적용한다. 목표 Pitch와 `RInterpTo` 출력 모두 하한을 제한하므로 거리와 무관하게 내려다보기 각도가 제한된다. 양의 Pitch에는 LockOn 전용 제한을 두지 않았다. 수치 변경 이유·영향은 Architecture의 2026-09-30 ARCH-69 개정 절에 기록했다.
- UE 5.8 `KhazanEditor Win64 Development`에서 UHT와 변경 Source compile은 통과했으나, 열린 Unreal Editor가 `UnrealEditor-Khazan.dll`을 점유해 link `LNK1104`로 실패했다. `Khazan Win64 Development`에서도 변경 Source compile은 통과했으나 기존 `KZLocomotionComponent.cpp:8`의 `InterchangeResult.h` 누락 `C1083`으로 전체 target build가 실패했다. 이 작업 범위에서 해당 파일은 수정하지 않았다. 새 Editor binary 적용과 PIE 카메라 동작은 아직 검증하지 않았다.

## 2026-09-30 — 방향별 Dodge/DodgeAttack Combo 설계 감사

- 현재 Source의 `UKZComboAttackAbility`와 단일 `FKZComboCommandEdge`는 node별 Command/phase, held, Move, owner-tag 조건과 다른 Entry Ability handoff를 이미 처리한다. Dodge/방향을 Edge 범용 조건으로 추가할 필요는 없다. 방향은 activation 때 선택된 Dodge EntryNodeId에 고정하고, 각 Dodge node의 공격 Edge가 해당 DodgeAttack Entry를 가리키는 설계를 ARCH-71에 기록했다.
- 현재 `RouteAttackInput()`은 X/Y Begin에서 일반 Spec press를 Combo Command보다 먼저 제출한다. DodgeAttack과 일반 공격이 경쟁할 수 있으므로 입력 순서 회귀가 선행돼야 한다. `UKZComboAttackAbility`는 Attack AssetTag를 constructor에서 부여하므로 Dodge를 직접 파생시키지 않고 공통 Combo Action 실행 부분만 추출하는 방안을 채택했다.
- 현재 InGame에는 Dodge M1 8방과 DodgeAttack F/B/L/R 시퀀스 파일이 있다. 대각선 DodgeAttack의 원작 연결, DodgeAttack unlock producer, 비용/Notify 지점은 확인되지 않았다. 첫 제품 구조는 8 Dodge Blueprint Ability와 4 cardinal DodgeAttack Blueprint Ability, 하나의 Dodge Combo Definition을 전제로 하며 대각선 연결은 임시 데이터로 표시한다.
- 이번 작업은 현행 Source/Content와 저장 Engineering·Animation 기록의 표적 감사 및 설계 문서 추가만 했다. 게임 C++/BP/Montage/Input asset은 수정하지 않았고 새 build/PIE도 수행하지 않았다. 파일별 적용 순서는 Migration의 2026-09-30 D4 절에 기록했다.

## 2026-10-01 — Dodge 현재 적용과 Weak/Strong 해금형 Combo 후속 절차

- [현재 Source] UKZDodgeAbility는 UKZActionAbility 파생이며 Dodge AssetTag와 이동 입력/스태미나 회복 차단 태그만 설정한다. 사용자가 Input.Action.A, Command.Player.Dodge.A, Ability.Action.Dodge를 추가했다. KZComboAttackAbility에도 Block.StaminaRegen이 추가됐다. Combo 공통 base, Dodge direction/activation/몽타주와 Controller binding은 아직 없다.
- [저장 asset] `/Game/Bluprints/AbilitySystem/Abilities/Player/Dodge/GA_Player_DodgeAbility_{F,RF,R,RB,B,LB,L,LF}` 8개와 UKZDodgeAbility 상속을 확인했다. 현재 표적 경로에 IA_Dodge/AM_DAS_Dodge, Dodge Cost/Unlock GE, DodgeAttack Ability는 확인되지 않았다. InGame Dodge/DodgeAttack sequence는 존재한다. BP 전체 EventGraph/미저장 에디터 상태는 검사하지 않았다.
- [마지막 저장 검증] 2026-10-01 10:29 UBT Log.txt는 KZDodgeAbility/KZGameplayTags C++ 및 UHT의 Live Coding 빌드 Succeeded다. 에디터 로그에는 8 Dodge BP 재컴파일이 기록돼 있다. 본체 DLL은 09:50 저장본이며 Live Coding patch와 cold build를 구분한다. 이번 턴은 build/PIE를 새로 실행하지 않았고 Dodge 동작을 입증하는 PIE 결과도 확인하지 않았다.
- [새 요구] Dodge→Weak와 Dodge→Strong의 특수 스킬에 별도 해금 태그/Edge를 두는 계약을 ARCH-72에 기록했다. 방향은 현재 Dodge node가 보존하므로 범용 IsDodging/DodgeDirection Edge 필드는 추가하지 않는다. 두 특수 가족의 실제 스킬/모션 대응과 방향별 분기는 아직 미확인이다.
- [구조 제안] 기존 Combo 실행을 UKZComboActionAbility로 이관하고 기존 Attack 부모 class를 유지한다. 8 Dodge BP와 확인된 특수 Entry는 기존 DA_Player_Combo_Definition을 공유하고 CharacterDefinition에서 graph-only grant한다. 잠긴 특수 공격은 grant 회수가 아니라 Edge/Ability의 요구 태그로 제한한다.
- [선행 보완] Command 소비 반환/Begin 순서, 소비된 press의 동일 Spec restart 금지, graph-only InputPressed 보정, local 전환 Cost 실패 시 jump 거절, editor graph 검증 및 UnPossessed Action 취소를 함께 확인해야 한다. UE PreActivate 취소는 target Commit/몽타주보다 먼저이므로 TryActivate true를 완전한 전환 성공이나 rollback으로 설명하지 않는다.
- [해금 전 동작] 기본 회피공격 유무는 사용자에게 선택 질문을 남겼다. 답변 전 설명의 임시 가정은 특수 Edge 차단/InputEnd 전 Dodge 유지/InputEnd 이후 일반 공격 진입이며 원작 확인값이 아니다.
- [완료 경계] 현재 진행상황 감사와 공동 구현 절차 문서만 완료했다. 게임 Source/Content/BP를 변경하지 않았다. 적용 체크포인트·필드·에디터 경로·PIE 기대 결과는 Migration의 2026-10-01 D4 절을 따른다.

## 2026-10-01 — Combo Action 사용자 부분 적용 재확인·전체 코드 보완안 제공

- 앞선 초기 상태 기록 이후 사용자 Source에는 UKZComboActionAbility가 생성돼 기존 Combo 실행을 소유한다. UKZComboAttackAbility는 Attack AssetTag ctor만 남고 UKZDodgeAbility는 새 base를 상속한다. ASC HasComboEntry/TryActivateComboEntry의 include/cast도 새 base다. 이를 실제 Source로 확인했으며 사용자 코드를 편집하지 않았다.
- 공통 CanActivate 사전 데이터 검사와 local 전환의 CheckCost 실패 return은 아직 Source에 없다. 현재 비용 부족에도 CurrentNodeId/section을 변경하는 분기를 확인했다. per-node ApplyCost를 보존한 전체 h/cpp 보완안을 Docs/Engineering/Examples/ComboAction_20261001에 첨부했다.
- 현재 bConsumed/Begin command 선행/graph-only InputPressed 보정, Definition validation과 UnPossessed Action cancel은 미반영이다. Dodge 방향/defaults/입력/몽타주/특수 스킬·해금은 이번에 구현하지 않았다.
- 설명과 검증 범위는 Migration의 하단 D4 코드 첨부 절에 기록했다. 설치 UE 5.8 GAS API와 제안 파일을 정적으로 대조했으며 새 build/PIE 결과는 없다. 전체 첨부는 설명용 제안이고 게임 Source 적용 완료가 아니다.

## 2026-10-01 — Dodge 특별 공격 공동 구현 설명 산출물

- 공통 ComboAction의 CanActivate/비용 조기 반환은 현재 사용자 Source에 적용돼 있다. 앞선 미적용 상태 기록은 과거 검사 시점이다.
- Dodge input/direction dispatch, X/Y 소비 중재, 실제 binding 기반 Spec 입력 이관, graph validation, 수명 cleanup과 별도 Weak/Strong unlock gate의 전체 코드/에디터 안내를 Examples/DodgeSpecialAttack_20261001/GUIDE.md와 코드 zip으로 첨부했다.
- 이번 실제 수정은 Engineering 설명 문서/코드 사본뿐이다. 게임 Source 15개 hash는 동일하고 새 runtime enum도 미생성이다. 새 build/PIE는 없다.
- 임시 4/8/24-frame Notify와 특별 공격 motion/direction 대응을 원작값과 분리했다. 비용, 무적/피해/Cue, 제품 Save producer와 방향별 root-motion 품질은 해당 자료/실제 실행에 따라 후속 검증한다.

## 2026-10-01 — Dodge 기존 구조 재사용·최소 변경 재검토

- 사용자 요청으로 현재 Source와 앞선 전체 제안을 재검토했다. ComboAction 공통 실행/CanActivate/Cost gate 및 Dodge enum/defaults/getter는 이미 있다. 이를 반복 구현하지 않는다.
- 새 runtime 파일 없이 기존 Player/Controller/ASC h/cpp에서 방향 계산/지역 Spec 선택/기존 press의 optional Spec Handle 필터로 연결하는 제안을 ARCH-72 하단에 기록했다. Dodge 8 grant는 같은 A binding, 특별 공격은 graph-only로 구분한다.
- 현행 InputEnd 전 Action block/InputEnd 때 ComboWindow Closed를 유지하면 기존 X/Y 라우팅과 ComboAction handler로 해금 Edge를 처리할 수 있다. 앞선 bConsumed/입력 순서 변경/전체 파일 교체·IsDataValid 선행은 현재 Dodge의 필수로 삼지 않는다.
- 기존 graph node/edge/owner tag 요구/Ability 요구 태그/GE/Task를 재사용한다. graph-only 입력 기록, restart 비용 사전 승인 및 Character 수명 누락은 기존 함수의 작은 보완으로 구분한다.
- 설명·설계 문서만 갱신했다. 게임 Source/BP/에셋 적용, 새 build/PIE는 없다. 정확한 재개는 Migration/Continuity 마지막 절을 따른다.



## 2026-10-01 — 전 기능 최소 변경 원칙 명시와 Dodge 상세 안내

- 사용자 요청에 따라 AGENTS/Engineering 규칙/Router에 모든 구현·기능 추가의 기존 구조 재사용·작은 수정 원칙과 MD 기반 최신 상태/방향/스타일 확인 방침을 날짜별로 추가했다. 설명 요청은 계속 사용자가 직접 적용하는 공동 구현 방식이다.
- Dodge 최신 안내: [DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md](DODGE_MINIMAL_IMPLEMENTATION_GUIDE_20261001.md). 소스는 [기존 7파일 변경 patch](Examples/DodgeMinimal_20261001.patch)로 첨부했다. 새 runtime 파일/클래스 0개, 현재 ComboAction 실행/입력창/비용/Edge 재사용, 8 BP와 같은 A grant 유지, 해금형 target은 graph-only다.
- 이번 완료 범위는 정책 MD·구현 설명·참조 patch 작성과 정적 확인이다. patch 문맥 검사 통과 및 시작 대비 게임 Source 9개 SHA256 동일을 확인했다. C++/BP/Config/에셋 적용, cold build/PIE, InGame 실제 root-motion/비용·무적·피해·Save는 완료로 기록하지 않는다.

## 2026-10-01 — WeakAttack01 → LockOn L 포즈 튐 원인 조사 진행 상태

- 사용자의 2.5초는 복귀 관성화 진단 실험이고 보존한다. 실제 Source의 Move 처리→GameplayEvent 순서, 공격 이동 gate/종료, 실제 속도 기반 방향과 Walk→Run 중간 선택 및 라이브 ABP 최종 관성화 경로를 확인했다.
- 방향/gait/샘플 변화와 관성화 본별 보정·추가 요청을 분리해야 한다. 코드상 후보이며 직접 튐 프레임과 일치하는 증거는 아직 없다. 관성화 한계 또는 단일 원인으로 확정하지 않는다.
- 직접 키 PIE 요청은 미완료다. Windows 제어 helper native pipe 오류와 UE Editor 종료/연결 끊김 때문에 수행하지 못했다. 초기 Python probe 오류는 수집 frame 0이며 증거에서 제외했다. agent 중단점은 정리했고 user 중단점은 보존했다.
- 변경은 관련 MD 기록뿐이며 게임 Source/BP/에셋과 설정은 수정하지 않았다. 근거는 `BUILD_RUNTIME_DIAGNOSTICS.md`, 정확한 재개는 `ENGINEERING_WORK_CONTINUITY.md`의 같은 날짜 절을 따른다.

## 2026-10-01 — 공격 복귀의 실제 L 입력/F 방향 선택 확인 후 수정안 준비

- Editor 재실행/연결 후 실제 패드 PIE를 읽기 전용으로 관측했다. 3,444 frame, error null이다. full L 입력/Resolved Run에도 공격 종료 첫 native 방향은 F/Anim gait Walk였고 8 frame 뒤 L 근처/Run으로 바뀌었다. 속도 0 기본값이 아닌 공격의 전진 속도 경로다. F 비교는 방향 변화가 작았고 Walk L도 F 중간 선택이 있었다.
- 새 runtime 파일/멤버 없이 KZAnimInstance.cpp 두 곳에서 LockOn의 방향을 기존 입력 snapshot, gait를 기존 ResolvedGait로 고르는 ARCH-73 제안과 Examples/LockOnRecoveryPose_20261001.patch를 준비했다. 실제 target 문맥 검사/1파일 +12/-3 확인이 완료됐다.
- 게임 Source/BP/에셋 적용과 수정안 build/수정 후 PIE는 아직 없다. 첫 F/Walk 중간 선택은 확인했지만 모든 시각적 튐의 원인/수정 효과를 확정하지 않는다. 방향→gait 순서의 사용자 적용/단일 공격 A/B와 일반 이동 회귀가 다음이다.
- Raw/summary는 Saved/ImportReports/WeakAttackLockOnExit_20261001_{raw,summary}.json이다. callback/참조를 정리했고 마지막 Editor connected/PIE Idle이다. Diagnostics/Animation 정본/Architecture/Continuity에 사실·제안·검증 경계를 날짜별 추가했다.

## 2026-10-02 — Ability Definition 배열 원소 식별용 metadata 적용

- 직접 수정 완료: `KZComboDefinitionData.h`의 `Nodes`/`CommandEdges`, `KZCharacterDefinitionData.h`의 `InitialAbilityGrants`에 UE 네이티브 `TitleProperty`를 추가했다. 접힌 원소의 제목은 각각 NodeId, 명령·phase·Hold·Move·target, AbilityClass·InputTag다. 새 runtime 타입/표시 이름 저장/Editor customization 없이 기존 멤버를 재사용했다.
- 설치 UE 5.8 PropertyEditor formatter와 UHT 생성 metadata를 확인했다. 모듈 DLL이 갱신됐고 직접 `KhazanEditor Win64 Development` 빌드 명령의 exit 0/`Result: Succeeded`를 확인했다. Rider 상태의 false/진단 없음은 UBT 성공과 분리 기록한다.
- 에디터는 연결되지 않은 종료 상태였으며 실제 Details 화면은 아직 미확인이다. 새 Editor에서 `DA_Player_Combo_Definition`의 Nodes/CommandEdges와 `DA_CharacterDefinition_Player`의 InitialAbilityGrants를 펼치고 개별 원소를 접어 제목을 확인한다. 구현 근거/정확한 문자열/배열 적용 위치는 `SOURCE_BP_CONFIG_ARCHITECTURE.md`의 같은 날짜 절이다.
- 이번 작업의 `KZAnimInstance.cpp`와 두 Definition uasset의 시작/종료 hash가 동일하다. 기존 사용자 gameplay 변경을 보존했고 새 PIE는 수행하지 않았다.

## 2026-10-02 — 사용자 DodgeAttack 4방 연결 및 F 실패 원인 확인

- 사용자 보고로 4방 DodgeAttack 연결과 B/L/R 동작을 확인했다. 실제 Source에는 `UKZDodgeAttackAbility : UKZComboAttackAbility`가 추가돼 있고 F/B/L/R Blueprint Ability 및 shared Definition 노드/초기 grant가 있다. 이번 조사 자체에서 B/L/R 플레이를 새로 재현한 것은 아니다.
- F만의 설정 차이: Editor live CDO의 `GA_Player_DodgeAttack_F.EntryNodeId=None`, 나머지는 각각 `DodgeAttack_B/L/R`다. F target node는 `DodgeAttack_F`로 존재한다. 기존 PIE 로그와 현재 Source를 대조해 ASC가 F Entry를 찾지 못한 뒤 다른 montage의 local 전환을 거절하는 경로를 확인했다.
- 안내한 최소 수정은 F BP Class Defaults의 Entry Node Id를 `DodgeAttack_F`로 설정/Compile/Save하고 새 PIE에서 확인하는 것이다. gameplay 코드/에셋 직접 수정과 수정 후 PIE는 수행하지 않았다. 상세 근거와 정확한 실패 경로는 `BUILD_RUNTIME_DIAGNOSTICS.md`의 같은 날짜 F 진단 절이다.

## 2026-10-02 — LockOn L Dodge → Idle 사용자 조작 관측 진행

- 사용자가 PIE를 직접 조작하고 어시스턴트가 읽기 전용 callback으로 상태를 수집했다. v1 5,771 frame/v2 1,165 frame/error null을 Saved/ImportReports에 보존했다. 게임 Source/BP/에셋 직접 수정과 수정 효과 확인은 없다.
- 무입력 자연 종료는 몽타주 Standard 0.25 s 블렌드이며 이동 입력의 조기 중단만 기존 0.24 s 관성화 요청을 사용한다. 자연 종료의 Slot weight는 연속 감소하고 작은 반대 속도 때문에 Idle 후보가 재변화한다. 이동 중단 L에는 별도로 큰 frame 간 본 회전 변화가 있다. 두 경로를 구분했고 화면 튐의 직접 원인은 아직 확정하지 않았다.
- 실제 현행 `KZAnimInstance.cpp`에 이전 ARCH-73의 LockOn 유효 입력 기반 방향 및 ResolvedGait 선택이 반영돼 있음을 Source로 확인했다. 이전 날짜의 미적용 기록은 그때의 사실로 보존하며 현재 소스를 옛 설명에 맞춰 되돌리지 않는다. 이번에 해당 코드를 작성/빌드한 것은 아니다.
- 머리·골반·발만으로 상체/무기 튐까지 배제하지 않는다. 어깨·팔·손을 포함한 v3 observer를 준비했다. 원인 후보/설정 출처/디버거 한계/정확한 재개와 정리는 Diagnostics와 Continuity의 같은 날짜 L Dodge 절을 따른다.

## 2026-10-02 — 새 L/R Dodge 관측: 종료 후 Actor 회전 확인

- 사용자 새 PIE에서 v3 1,084 frame/error null을 실제 확보했다. WeakAttack 2회/L Dodge 3회/R Dodge 2회, 상체/손의 component/world pose 포함이다. `Saved/ImportReports/DodgeIdleLive_20261002_v3.json`을 저장했다.
- L 세 번 모두 회피 중 고정된 Actor Yaw가 종료 후 한 frame 약 +7 deg, R 두 번은 약 -7 deg로 보정된다. 측정 각속도 ±720 deg/s는 실제 CharacterDefinition의 LocomotionConfig.RotationRate.Yaw=720과 일치한다. 첫 L은 로컬 머리 회전 변화 약 0.046 deg에 대해 전체 world Root가 약 7.013 deg 돌아갔다. 큰 종료 변화는 Actor/capsule 회전에서 관측됐다.
- Source/CDO는 Root Motion 동안 CMC PhysicsRotation을 중지하고 종료 뒤 LockOn desired rotation을 따라잡는 경로와 일치한다. 원인 검증의 작은 다음 단계는 기존 CharacterMovement의 Allow Physics Rotation During Anim Root Motion checkbox 비교다. 어시스턴트는 게임 설정/Source를 바꾸지 않았고 수정 후 해결은 검증하지 않았다. 자세한 근거/범위는 Diagnostics의 새 1,084 frame 절이다.
- v3 저장 후 v4 read-only 관측으로 전환했다. 추가 Controller/CMC 회전/root-motion 관측과 사용자 화면상의 튐 순간 대응은 후속 비교 항목이다. 책임/실행 수명 구조를 새로 확장하지 않았다.

## 2026-10-02 — DodgeAttack handoff 블렌드 설정 확인

- 사용자 시간 소유자 질문에 대해 actual handoff Source/엔진 API/live montage 설정을 확인했다. 현재 Dodge → 다른 DodgeAttack Ability는 ComboTransitionInertializationDuration을 사용하지 않고 새 montage의 Standard Blend In을 사용한다. AM_DAS_Player_DodgeAttack Blend In과 outgoing AM_DAS_Player_Dodge Blend Out은 모두 현재 0.25 s/HermiteCubic다. 원작 검증값이 아닌 현 프로젝트 에셋값이다.
- 같은 montage section jump의 native 0.08 s와 이동 복귀 중단의 native 0.24 s를 이 handoff와 구분한다. 설정 report/엔진 중단 규칙/직접 조절 위치는 Diagnostics의 같은 날짜 DodgeAttack 블렌드 절이다. 게임 Source/BP/에셋 변경이나 변경 효과의 PIE 검증은 없다.


## 2026-10-02 — Guard 직접 구현 완료

- LShift/LB Guard 입력·Ability grant·Start→held→release End를 직접 연결했다. LockOn은 기존 입력각의 8방향, 비LockOn은 F다. Guard 17 시퀀스에 InputEnd marker, Montage 5개 branching InputEnd를 추가했다. 기존 Root/pose/rate/frame grid와 mesh 0.01을 보존했다.
- 런타임 신규 타입은 UKZGuardAbility 1개다. 기존 Action block/cancel·ASC 입력 Spec·Locomotion constraint·GT snapshot·DefaultSlot/관성화를 재사용하며 기존 8개 Source에 연결만 더했다. Guard Manager/피해 프레임워크/별도 방향 계산은 추가하지 않았다.
- 활성화/유지 무료, 방어 성공은 공격이 전달한 StaminaDamage를 SetByCaller로 차감하고 무작위 Suc_F/L/R, 원작 확인 0.5초 regen 지연을 적용한다. ASC.TryGuardHit의 true를 미래 HP 피해 생략에 연결한다. 방어 각도/불가 공격/GuardBreak/적 hit producer는 아직 별도 구현 대상이다.
- cold build 및 새 프로세스 실제 PIE Khazan.Guard.PIE Success. 8방향·성공/차감·release/이동/공격/tap/Cancel/자연 종료/UnPossess 검사를 통과했다. 새 프로세스 asset audit와 17 pose/root/playback 보존 검사도 통과했다. native helper 오류로 물리 키·패드/화면 blend와 실제 적 타격/HP routing은 미검증이다.
- 현행 상세는 [GUARD_IMPLEMENTATION_20261002.md](GUARD_IMPLEMENTATION_20261002.md), 재사용 보고는 Metadata/GuardImplementation_20261002다. 마지막 Editor는 StormPass, PIE Idle, dirty package=0이며 user 중단점/동시 환경 변경을 보존했다.


## 2026-10-06 — Guard 재개 완료 / 방향별 실제 클립 수정

- [실제 적용] 기존 Guard 실행 구조를 재사용해 BS_DAS_Player_Guard의 오래된 BlendSpaceData.Segments 인덱스만 재생성/저장했다. F 입력→L, L 입력→RF 등의 오선택이 해결됐다. authoring script에 ResampleData를 추가하고 기존 개발 전용 PIE test를 실제 sample/227본 pose 검사로 보완했다. 새 gameplay runtime 파일/클래스=0. Guard Ability/AnimInstance/ABP와 source pose/rate/root/mesh scale은 시작 SHA256/배치를 보존했다.
- [검증 정정] 10월 2일 8방향 검사는 각도/배치였으며 실제 sample cache를 검사하지 않았다. 이번 cold build와 새 Editor saved-asset reload 후 01:01:38.080 UTC Khazan.Guard.PIE Success에서 8 clip/뒤 경계/카메라 상대방향/비LockOn F/정지 Loop 및 기존 Guard 비용·InputEnd·cleanup을 확인했다.
- [근거] Docs/Engineering/GUARD_IMPLEMENTATION_20261002.md의 10월 6일 추가 절, Metadata/GuardLocomotion_20261006/RuntimeResult.json·DebuggerEvidence.json·PIE_AfterFix.log·FinalColdBuild.log. 물리 키/패드와 연속 화면 품질/실제 적 hit·HP/GuardBreak는 별도 범위다.
- [정리] 작업 시작의 DevMap 유지, PIE Idle, dirty content/map0, user breakpoint8 보존/agent0/debugger detached. setup_guard_20261002.py의 전체 setup()을 반복하지 않는다.


### 2026-10-06 — 검증 종료 뒤 에디터 상태 추가 관측

위 PIE Idle 정리는 01:01:38 UTC Automation 완료 직후의 상태다. 이후 이 에이전트가 실행하지 않은 별도 PIE 세션이 다시 시작/종료됐고, 01:07:36.906553 UTC 마지막 읽기 전용 관측에는 /Game/Maps/UEDPIE_0_DevMap.DevMap이 실행 중이었다. dirty content/map은 계속 0이다. 이 추가 세션을 종료하거나 입력을 주입하지 않았다. 이때 MCP ue_play(state)의 Idle 응답과 실제 UnrealEditorSubsystem game world가 일치하지 않아 native world 관측을 기록한다. 추가 세션의 물리 입력/화면 품질을 자동 테스트 결과로 계산하지 않는다. FinalEditorState.json과 RuntimeResult.json은 Automation 종료 상태와 마지막 관측 상태를 구분해 저장했다.


## 2026-10-06 — Guard 이동 중 Start/End 생략 완료

- 허용된 기존 이동 intent가 있는 press는 Start 없이 GuardLocomotion, release는 End 없이 기본 로코모션으로 전환한다. Start/End 도중 이동에도 InputEnd를 기다리지 않는다. Start 중단은 가드/Walk/Ability를 유지하며 End/release는 자기 수명을 정리한다. 정지 절차·held 성공 반응과 확정 비용은 유지한다.
- 기존 Guard cpp 3함수만 runtime 수정하고 기존 개발 test를 확장했다. h/BP/animation asset/new runtime file 변경은 없다. cold build 성공, PID24736 DevMap Khazan.Guard.PIE 2026-10-06 01:32:08.870 UTC Success.
- 실제 Guard clip/mesh와 기존 8방향 및 비용/취소/cleanup 검사를 통과했다. 이동 release의 실제 기본 group 출력은 Locomotion / DAS_Player_Walk_Loop / weight1이다. 최초 test-only ungrouped 관측 실패는 Sync Group까지 검사하도록 보완했다.
- 최종 PIE 없음/DevMap/dirty0, 임시 editor throttle 원래 true 복원, debugger detached/agent BP0/user exceptions8 보존. 증거·정확한 동작은 [Guard 정본](GUARD_IMPLEMENTATION_20261002.md) 및 Metadata/GuardMovementPolicy_20261006/RuntimeResult.json이다. 물리 키/LB·연속 화면·적 타격은 다음 QA다.


## 2026-10-06 — 다른 동작 중부터 유지한 가드 입력 자동 실행 완료

- Controller Input_GuardPressed 한 콜백만 runtime 수정했다. 실제 Source의 Triggered binding을 유지해 불허 중 기존 ASC press를 재시도하고 State.Guarding=true면 추가 press를 막는다. 다른 동작 InputEnd 허가/자연 종료 후 새 press 없이 Guard가 실행되며 방어 중 Start를 반복하지 않는다. 새 상태/queue/timer/API/Guard Ability/asset 변경은 없다.
- 기존 개발 test에 실제 Controller binding Execute 경로를 추가했다. cold build 성공, PID26692 DevMap Khazan.Guard.PIE 2026-10-06 03:02:36.401 UTC Success. WeakAttack/Dodge 중 held → 허가 후 자동 가드, 중간 공격 뒤 복귀, release/cancel 미실행과 기존 Guard 이동·8방향·비용·cleanup을 검사했다.
- 최초 DLL link lock과 Automation 준비 timeout은 해결하고 로그를 보존했다. 키는 기존 IA_Guard의 LShift/LB이며 키 선택 질문에 별도 응답 없어 mapping을 보존했다. 마지막 native world 없음/DevMap/dirty0, 임시 editor throttle true 복원. 증거·실제 범위·후속 QA는 [Guard 정본](GUARD_IMPLEMENTATION_20261002.md), Metadata/GuardHeldInput_20261006/RuntimeResult.json이다.

## 2026-10-06 — Heal Source·격리 검증 완료 / 메인 에셋 파일 잠금 대기

- 기존 Attribute/Tags/Controller h·cpp 6개와 새 KZHealAbility h·cpp 2개로 DPad Down/무제한/무비용/HP·MaxHP200/+100/회복 Notify 1회/InputEnd/자기 Walk handle cleanup을 구현했다. 기존 실행·입력·이동 구조를 재사용했다.
- 격리 새 Montage/GA/GE 2개/IA와 기존 Skeleton/ABP/IMC/InputData/Definition을 작성했다. bip001-spine 상체 Heal/기존 하체 locomotion이다. 원본 Sequence·RateScale·root·mesh scale, 기존 AnimInstance/ASC/Guard cpp/Build.cs를 보존했다.
- 기존 의존성 cold build Succeeded, PID11600 Heal PIE 05:19:29.000 UTC/Guard PIE 05:20:57.182 UTC Success, 새 PID27900 saved reload/ABP UP_TO_DATE/dirty0. 실제 하체7본·양손2본/CMC/HP·취소·교체·재사용·cleanup을 검사했다. work editor 종료/throttle 복원을 확인했다.
- 메인 Content는 file lock으로 아직 시작 hash다. ReadyContent의 10개 파일과 숨김 helper PID28144가 메인 editor exit 후 재검사·적용·build한다. 최신 단계는 Metadata/HealImplementation_20261006/ApplyStatus.json의 WaitingForEditorExit/Complete/Stopped다. 기존 editor/DLL은 사용·교체하지 않았다.
- [Heal 정본](HEAL_IMPLEMENTATION_20261006.md), Metadata/HealImplementation_20261006/RuntimeResult.json·ChangeManifest.json·AssetAudit_Fresh.json이 기준이다. 물리 DPad/연속 화면/적 damage·death·HP UI/임시 timing 원작 일치는 별도다.

## 2026-10-06 — Heal 메인 반영 완료, 직접 PIE 테스트 준비

- 사용자 후속 요청으로 clean DevMap/native game world 없음 상태의 메인 editor를 정상 종료했다. 반영 helper가 정확한 에셋10개를 적용/hash 검사하고 메인 KhazanEditor cold build를 성공시켰다. ApplyStatus=Complete(05:48:35.668 UTC), 원본 clip/검사한 Source SHA 보존.
- 새 메인 PID27568 DevMap에서 native KZHealAbility, GA Montage/GE/no cost·cooldown, DPad Down1/Heal grant1/Health 초기 GE, ABP UP_TO_DATE/dirty0을 확인했다. PIE는 시작하지 않아 사용자가 바로 Play할 수 있다. 앞선 메인 대기 상태는 해소됐다.
- 최신 근거는 MainAppliedResult.json·MainReadyAudit.json·MainReady_Editor.png·AssetInstallManifest.json·ColdBuild_MainAfterApply.log와 [Heal 정본의 메인 완료 절](HEAL_IMPLEMENTATION_20261006.md)이다. 기존 격리 Heal/Guard PIE Success는 유지되며 물리 DPad·연속 화면 QA는 사용자 테스트다.

## 2026-10-06 — Heal 무기 수납·발도 후속 적용

- 빈손 Heal을 위한 기존 무기 BackPack 재부착/실행 snapshot/cleanup, 기존 UpperBody Stow→Heal 뒤 Arms 발도, 발도 시작 Walk 제한 반환·InputEnd unblock을 기존 Heal h/cpp에 구현했다. 새 runtime 파일/클래스0, Main AnimInstance/ASC/Controller 상태 추가0.
- 격리 stock build/Heal PIE Success06:29:18.543 UTC·Guard 회귀 Success06:31:27.946 UTC/saved reload UP_TO_DATE·dirty0. 메인 에셋7개 선택 copy/원래 미참조 Equip asset2개 실제 이동으로 제거/hash/Main cold build Succeeded06:35:05 UTC. user editor는 dirty0/PIE 없음에서 정상 재시작만 했고 자동 gameplay 검사는 격리에서 수행했다.
- 정본 [HEAL_WEAPON_PRESENTATION_20261006.md](HEAL_WEAPON_PRESENTATION_20261006.md), Metadata/HealWeapon_20261006의 Final 로그/SourceDelivery/DeliveryVerification/ApplyStatus. 물리 입력·연속 화면·임시 Notify 원작 일치·실제 적 hit는 별도 후속 QA다.
## 2026-10-06 — DevMap 몬스터4종 구현·메인 준비 완료

Swordsman/SwordShield/HeavySwordsman/HalberdElite: Idle/배회→Sight 감지/준비→추적→LockOn 대치·좌우 걷기/정지·원작 후보13개 단일/콤보→재추적을 StateTree와 기존 GAS/Locomotion/AnimInstance로 구현했다. 피해/피격은 없다. product build/actual Monster·Heal·Guard PIE, source clip60개/Player파일4개 보존, 메인137package 선택 hash/cold build/saved reload를 통과했다. 새 main PID11000 DevMap·PIE 없음/dirty0, 별도 work editor 종료. [Monster 구현 정본](MONSTER_AI_IMPLEMENTATION_20261006.md) 최신 완료 절/Metadata/MonsterAI_20261006부터 후속 작업을 시작한다. AI 거리/주기/확률은 원작 AIData 미확보의 명시된 임시 owner 설정이다.

## 2026-10-07 — Notion 보고 작업 재개 및 최신 상태 반영 완료

- 실제 변경: 사용자 Notion의 김민재 [언리얼11기] 아래 보고 DB에 누락된 10/1·10/2·10/6과 오늘 10/7 일일보고, 10월 2주차(10/6~10/12, 10/7 현재 기준)를 작성했다. 9월 5주차에는 해당 기간의 10/1~10/2 후속 기록만 날짜별로 추가해 기존 보고/화면을 보존했다.
- 템플릿: 일일보고의 목표/구현/누적/검증/리스크/다음 작업, 주간보고의 목표/진행/검증/리스크/계획/현황 화면을 채웠다. 전투·로코모션 업무 및 콤보·스킬·로코모션 프로젝트에 최신 절을 추가하고 프로젝트 요약 노트를 갱신했다. 비어 있던 몬스터 애니메이션 업무의 목표/방법/성과/이후 액션/레퍼런스를 채웠다. 기존 업무/프로젝트의 하위 DB는 보존했다.
- 화면: Khazan_MonsterWork_20261006/Khazan/Saved의 10/6 실제 Monster HalberdElite/Swordsman 및 HealWeapon_Stowed/Draw PNG 4장을 Notion 자체 파일로 업로드/첨부했다. 저해상도 고정 프레임의 범위를 명시했다. 새 에디터/PIE/캡처/게임 Source·BP·에셋 변경은 하지 않았다.
- 검증: 새 보고 5개와 기존 갱신 페이지 7개를 재조회했다. 각 날짜/관련 업무·필수 항목, 이번 주 이미지4개/기존 주간 이미지2개·하위 DB 보존 및 프로젝트 노트 저장을 확인했다. API insert_content의 속성 인자는 노트에 반영되지 않아 별도 update_properties로 처리 후 실제 값을 재검증했다.
- 상태 구분: Guard/Heal/무기 표현/Monster의 기존 메인 적용·cold build·제품 PIE 증거와 10/7 저장 ResumeAudit를 사용했다. 재개 턴의 새 build/PIE로 표현하지 않았다. 적중→피해/HP·Guard 분기·피격/사망/Cue, F 회피공격 재시험·Dodge 종료 회전 비교·물리 입력/연속 화면·원작 AIData 일치와 눈 변형 격리 contact QA는 미완료/미확인으로 기록했다.
- 제안만 한 부분: 다음 DevMap 연속 화면 QA와 기존 ASC/ComboAction을 사용하는 피해 수직 절편의 순서만 보고했다. 게임 기능 구현 제안/설정 비교를 적용 완료로 승격하지 않았다.
- 정확한 다음 절차: 이후 개발 결과가 생기면 Router→Architecture/Migration→해당 최신 정본·결과 파일에서 시작해 같은 Notion 업무/프로젝트에 날짜별로 추가한다. 이번 보고 작성의 pending 단계는 없다. 완료된 Monster 전달/author/build를 반복하지 않는다.
- 오늘 보고: https://app.notion.com/p/3f2ec99d2c54817ebb04d78ae3d793b1
- 주간 보고: https://app.notion.com/p/3f2ec99d2c5481079646c157b66220dd


## 2026-10-07 — BP_Player Original 파츠 보조 물리 / 검증 완료, 잠금4패키지 전달 대기

- 실제 work 구현: Torso/Shoes/Leg/Hair/Arm Original 5종, CopyPose ABP5, Torso/Leg/Hair의 엔진 RigidBody/Original-derived joint unit PA3. 새 제품 Source/class/manager 없음. main ABP/mesh/Skeleton/body PA/무기 수명과 GAS 구조 유지.
- 검증: cold build / 실제 파츠·본·collider·bounds·동적 pose / 화면 / Guard Success. stock main DLL의 새 work process에서 NullRHI Heal 전체와 actual saved/runtime 6컴포넌트 readback Success. rendered Heal 고정 시각 checkpoint 실패2개 로그는 보존하고 연속/hardware/original parity QA는 미확인으로 남긴다.
- 메인 전달: 14패키지 중10개 SHA 검증 완료. BP_Player와 Torso/Leg/Hair Original PA는 사용자 main PID7220의 Windows lock으로 기존 상태다. 현재 main에 5파츠 부착 완료라고 기록하지 않는다. 검증 결과·journal·진단 정본은 Metadata/PlayerParts_20261007 / PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md.
- 다음: 사용자 main 저장·종료 후 Scripts/Engineering/deliver_player_original_parts.py 1회. journal complete=true/14 of14 확인 후 실제 완료 append. 파일이 before/prepared SHA와 다르면 최신 사용자 변경을 work에 반영해 재검증하며 덮어쓰지 않는다. own editor는 정상 종료했다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

새 runtime 파일2(h/cpp)의 AKZSnowDeformation level Actor와 dev QA1을 실제 메인에 반영, finalized contact→bounded CPU tile/toroidal GPU field→material 경로다. character gameplay source/상태·CMC 전역 tuning은 추가하지 않았다. 작은 돌65개의 실제 Pawn/Nav 기여를 제외하고 원작63 MoveTo/1,422 segments 통과, 표적 CMC 높이 차분17.23% 개선. main Khazan.Snow.PIE Success04:22:07 UTC/PID27452, aliasDLL/source/48asset/map SHA 및 native scene passed. SnowTick Development Editor 평균.9884ms/P95 3.0408ms, shipping GPU/FPS 미검증. [구현 정본](HEINMACH_SNOW_IMPLEMENTATION_20261006.md) 마지막 절과 Saved/ImportReports/HeinMachSnow_20261006/FinalVerification20261007.json을 따른다. 새 main PID17552는 native class가 있는 DevMap/dirty0/PIE없음으로 read-only 확인했다.

## 2026-10-07 — Monster 정지 대기·대화 쌍·방향 보행 수정 완료

- Idle/Patrol 분리, Swordsman Guard/Basic03/Search/Sit01의 정확한 Loop→End, Talk01/02 mutual pair 및 partner 상실 End→Solo를 적용했다. 다른 병종은 자기 skeleton에 있는 대응 루틴만 구성한다. Definition/grants/ComboAction/StateTree/Controller/Locomotion을 재사용하며 추가 C++ runtime 파일·Ability/Component/Manager0, data-only 루틴 GA/Combo/Montage 각16이다.
- 물리 이동 중 Idle 포즈였던 원인은 author의 PostPlacedNewNode 입력 binding 초기화 누락이었다. ABP4의 실제 방향/Walk row/속도·위상/전투 Stand·Run/Slot/접지를 보완했다. Foot Placement/Leg IK는 Walk branch이며 NPC만 GT 평가, Player default false 유지다.
- 마지막 stock Waiting/SourceAudit(32seq/879799 raw transforms)/Monster32/12FPS Halberd8/Heal/Guard Success. 계산 contact interval ankle median 최대0.0cm/s(32/min sample11, 반복8/min12); 모든 sole vertex·transient·지형/원작 연속 포즈 동일성을 의미하지 않는다. 이전 실패 로그 보존.
- 메인 scoped129(79new/50existing)·원본32 hash 보존, 마지막 Halberd ABP1 보완/메인 build5action/27.82초/Succeeded. Main26644 정상 표시 DevMap/10몬스터·exact Solo/pair/Patrol/NPC GT/Player false/Ratio1/PIE없음/dirty0; 자동 main PIE 없음. own26976 정상 종료(render3/maxFPS0/throttle true 복구). pending 작업 없음.
- 현재 정본 [MONSTER_UNAWARE_LOCOMOTION_20261007.md](MONSTER_UNAWARE_LOCOMOTION_20261007.md) 완료 절과 Metadata/MonsterIdle_20261007/RuntimeResult.json/FinalMainReadyAudit.json/FinalMainHashVerification.json. 다음은 열린 DevMap 직접 Play와 각 대기 actor 접근 화면 QA. 피해/피격·원작 AIData 전체·네트워크는 별도 범위이며 완료 author/retime/전체 복사를 반복하지 않는다. 다른 Snow/PlayerParts 변경을 보존했다.

## 2026-10-07 — Player Original 파츠 Main 통합 완료

- 이전 잠금4패키지 전달 대기는 해소됐다. DeliveryManifest complete=true, 최종 메인 14/14 prepared SHA 일치. BP_Player에 Original Torso/Shoes/Leg/Hair/Arm이 실제 저장·로드됐다.
- 새 메인 PID8292/DevMap에서 BP_Player·본체와 파츠 ABP6의 BS_UP_TO_DATE, 메시/PA/ABP와 SCS 부모 CharacterMesh0, 파츠 상대 scale1/본체 .01 유지, PIE 없음/dirty0을 확인했다.
- 제품 C++ 수정·helper DLL 이관·새 build는 없다. 통합 전 보호파일95개 SHA unchanged이며 현행 Monster/Snow Source/Config/uproject/DevMap을 보존했다. 기존 격리 physics/Guard/stock Heal 검증을 재사용했고 이번 확인은 메인 load/config/hash다.
- 현재 근거는 [Player Original 정본](PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md)의 Main 완료 절과 Metadata/PlayerParts_20261007/{DeliveryManifest,MainReadyAudit,FinalMainHashVerification}.json. 열린 DevMap 직접 Play의 연속 화면 QA로 이어간다.

## 2026-10-07 — BP_Player Original 파츠 메인 반영 완료

사용자 후속 Main 반영 요청으로 clean/PIE Idle main26644를 정상 재시작하고 남은4패키지를 전달했다. BP_Player Original Torso/Shoes/Leg/Hair/Arm 부착, Original PA와 파츠 ABP5/derived joint-unit PA3까지 14/14 SHA 적용 완료다. 최신 Source/Config/DevMap/본체 ABP·PA/modules/DLL 등95파일은 보존했다. 격리 테스트 helper/DLL은 메인에 추가하지 않았다.

새 main8292 DevMap에서 5파츠의 CharacterMesh0 parent/Original mesh·PA·ABP/relative1/no world simulation 및 본체 PA, 기존 무기2개를 read-only 확인했다. BP_Player+ABP5 UP_TO_DATE/dirty0/game world 없음. 실제 물리/이동/Guard/Heal은 앞선 격리 PIE 성공, 이번 main은 저장본 재로드 성공이다. 자동 main PIE는 시작하지 않아 바로 사용자 Play할 수 있다. 10/14 잠금 대기 기록은 해소됐고 MainIntegrationResult.Status=Complete/MainReadyAudit.Success다. 정본 PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md 최신 완료 절을 따른다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

Snow broad contact: 기존 owner h/cpp와 devtest만 수정, 새 runtime 타입0. foot40×32/reach20cm, weapon100/reach24cm 분리, tile lookup/dirty 최적화와 quarter-radius 누적 sampling. private build/PIE와 fresh main actual PIE06:28:20 UTC Success, actor poses/nav/collision 보존. CPU Development Editor 평균1.3529/P95 3.5578ms(376active), shipping/GPU cost 미검증. 새 aliasDLL/Source3/map selected delivery 완료; user8292의 미저장 ComboDefinition은 그대로며 새 UPROPERTY 사용에 저장·재시작 필요. 현재 SHA/범위는 HEINMACH_SNOW_IMPLEMENTATION_20261006.md 후속 확대 절/BroadBrush20261007/FinalVerification.json을 따른다.

## 2026-10-07 — Enemy 고정 대기·발견 후 전투 유지·행동 완료 후 Chase 메인 완료

사용자 요청을 실제 Main에 반영했다. HeavySwordsman Basic_Loop_03→End_03, HalberdElite Basic_Loop_02→End_02의 단일 Basic 루틴이고 기존 GA/Combo/Montage를 재사용한다. 발견 후 유효 Player 타깃은 시야/기억 시간/leash로 해제되지 않는다. 선택한 좌/정지/우 대치 구간 또는 Attack Spec 수명이 끝난 뒤 Root가 재추격을 판단한다. 신규 runtime 파일/추가 Manager/Chase 지연값은 없다.

격리 stock CombatPolicyPIE 4종 및 WaitingPIE 회귀 Success. Main 4 Source+5 package 선택 전달/9 SHA 일치/미관련89 보존, Main cold build10action/68.30초 Succeeded. fresh Main PID29556 DevMap의 4 BP UP_TO_DATE/고정03·02 segment/dirty0/PIE 없음을 06:51:21 UTC 확인했다. 사용자 직접 Play 상태이며 own Monster editor 정상 종료·설정 복구/대기 중 helper 없음이다. 상세·수치 출처·남은 화면 QA는 [Monster 정본 후속 완료 절](MONSTER_UNAWARE_LOCOMOTION_20261007.md)과 Metadata/MonsterCombatPolicy_20261007/MainAppliedResult.json을 따른다. 다른 PlayerParts/Snow 작업의 진행 상태는 해당 최신 절을 그대로 유지한다.

## 2026-10-07 — Player 파츠 몸 충돌·소폭 감쇠 메인 반영 완료

사용자 직접 요청으로 망토/옷자락/머리의 실제 몸 collider 반응과 소폭 감쇠를 완료했다. 기존 BP/ABP/derivedPA7만 변경하며 Gameplay/GAS/Ability/Event/Tag/Locomotion·새 runtime C++는 변경0. 세part에 actualparent18 anatomy collider를 엔진 기능으로 공급하고 single thin capsule로 과한 부풀음을 방지했다. linear damping.05/angular.35, cloth radius1cm/hair.75cm는 명시적 임시값이며 원작 export는 저장 자료 범위에서 미확인. 기존 mass/CoM/body-axis inertia diagonal은 sourceimport+engine 계산으로 복원 검증했다.

native SingleThin/Guard/Heal와 최신mainDLL stock reload가 성공했고 이미지3개 확인. Main28172 clean normal exit→7/7 SHAguard 전달→Main19684 DevMap 재시작/read-only7BP UP_TO_DATE/Original5 hierarchy/외부collision3 enabled. 보호155파일 SHA 유지; 다른 전투/Snow Source·맵·DLL은 보존. 원작physics/전체tensor·모든 mesh vertex·모든 combat/LOD·장기 hardware 동일성은 미검증이다. PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md 최신 완료 절과 Metadata/PlayerParts_20261007/BodyCollisionTuning의 Verification/DeliveryManifest/MainReadyAudit/FinalMainHashVerification이 현재 정본이다. 이전14asset journal은 선행 구현 이력이다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

Snow existing owner h/cpp에 FootCompression만 추가, 새 runtime 타입0. DeepSnow actual main PIE PID15340 Success, CPU 평균1.2863/P95 3.7207ms(Development/cold). Source3/map/material2+unique alias selective delivery, normal DLL 보존. 새 property는 사용자 저장·재시작 필요. 현재 proof는 snow Engineering 정본 최신 절/DeepSnow20261007/FinalVerification.json.


## 2026-10-07 ? Player Hair? ???? ?? ????? ??? ??

??? ?? ???? ?? Hair derived PA ? ?? ????? ????. ?? weighted ponytail65 bone/14?? ?? body/??? ??, ?? support/? flexibility/?? angular limits/??/virtual inertia conditioning? ????. Head/root3 kin??? ?4 CopyPose/Original source PA/? external18 collision ??. Runtime C++?BP/ABP???/Skeleton/???GAS??? ?? ??0??.

native ? saved process movement/turn/stop ? finite/bounds/shape/actual body contact Success, tip peak25.21?16.50cm/RMS8.81?7.20cm, independently responding18?65. ?? stock alias? Guard/Heal/saved actual72 hair bones?face lock4 pose ?? Success. Main21248 DevMap? read-only7 BP UP_TO_DATE/Original5/candidate1/dirty0/PIE?? ??, integration ?? ??161?? ??. ???? ?? gameplay PIE? ?? ??? ??? ???? ???. ?? ?????/?? ????? ??? PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md? Hair ?? ?? HairRefinement/{Verification,TuningProvenance,DeliveryManifest}.json? ????. ?? physics ?? ????? ?? pose/LOD/vertex QA? ???? ???.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

ARCH-79 실제 완료다. 기존 StateTree/AISettings/CharacterDefinition grants/ComboAction/ComboDefinition/Montage를 재사용했다. runtime 새 파일·class·component·manager는0, 실제 gameplay Source는 KZMonster.h와 KZMonsterStateTreeNodes.cpp 두 파일이며 기존 development KZMonsterAIPIETest.cpp를 보완했다. Player/ASC/ComboAction 실행 코드를 재작성하지 않았다.

공격은13→35(Swordsman5, SwordShield3, Heavy7, Halberd20)이며 해당4종 Attack68클립을 모두 연결했다. finite 준비/loop/타격/회복은 같은 Action 안에서 필수 순서를 유지하고 실제 combo만 기존 held X/InputEnd로 잇는다. 신규 combo6개의 끝 경계 InputEnd 실패는 montage data에서 마지막 sample 이전으로 보완했다. 정확한 시간식과 원작 SB/file/field는 MONSTER_ATTACK_ROOT_MOTION_20261007.md 및 AttackExpansionPlan.json/AllSavedSkillAudit.json을 따른다. 원작 hit/guard 조건 producer나 피해/피격을 새로 구현한 것은 아니다.

현재 공격 선택에는 독립 RNG probability가 없고 거리/각도/cooldown gate를 쓴다. 기존 임시 interval2..4초를1.1로 나눠1.8181818..3.6363636초로, combo continuation .75→.85(+10percentage points)로 설정했다. 전체 공격 빈도의 정확한10%를 보장하는 통계 수치가 아니다. ChaseReactionSeconds .4초는 assistant 임시 tuning이며4BP AISettings에 저장했다. 선택 Standoff/Attack을 끝낸 뒤 Chase에 진입하고 기존 task TimeRemaining을 Enter에서 설정/Tick에서 감소시켜 nav 요청을 잠시 보류한다. 첫 Chase에도 적용한다. 타깃 유지/기존 cleanup을 보존한다.

stock SourceAnimationAudit813/18,958,755 raw transforms·곡선/선택 metadata 동일 Success; compressed root QA .01cm/normalized angular1e-4rad는 기술 허용 오차다. raw tolerance1e-6와 구분하며 실제 최대 압축 positional 차이.0060654cm였다. AttackPatternsPIE 최종35개/모든 section/actual root travel/HP 불변·취소 cleanup·네 종 실제 rechase Success. CombatPolicyPIE 네 종 선택 행동 완료/시야 밖 target 유지/.4초 nav hold/후속 물리 추격 Success, Waiting/Heal/Guard PIE Success. 최초 full Monster.PIE의32 방향보행/contact sample min11·median0cm/s는 통과했으며 montage notify만 보완한 뒤 중복 walk 검사는 반복하지 않았다. retreat fixture는 Root lunge로700cm를 따라잡는 문제와 nav 밖5000cm 배치 문제를 각각 보존하고, 최종8후보 projection+complete path 및 Chase 진입 이후 physical advance로 검사했다.

Main 선택 전달은 파일981개(기존69/신규경로912), 이름 변경 옛 파일802개를 정확한 path/hash guard 뒤 제거했다. backup Before와 실패 로그를 보존한다. 미관련 Source/Config86 및 Archer177개 hash를 보존했다. Main stock cold build Succeeded, fresh Main PID3528 /DevMap/4BP·ABP UP_TO_DATE/813 options·35 grants·68 clips/저장값 재확인/PIE없음/dirty0이다. 자동 Main PIE는 실행하지 않았다. Main에 사용자 직접 Play용 DevMap이 열려 있다. 최종 manifest와 증거는 Metadata/EnemyAnimationOrganization_20261007/FinalVerification.json, DeliveredManifest.json, MainReadyAudit.json을 따른다.

Main 최초 read-only 검사에서 DevAI_ label 접두사에 Navigation volume까지 포함해 actor수5로 실패했다. 4 BP/ABP·813 options 검사는 이미 통과한 상태였고, exact4family actor label로 QA 식을 고친 뒤 같은 fresh editor에서 전체 read-only 검사를 다시 통과했다. 실패 JSON/MainReload log를 보존했고 이 과정에서 게임 코드·map·asset save/PIE는 수행하지 않았다. raw tolerance의 정확한 값은1e-6이며 이전 Art 본문의 최초 .001cm 언급은 엄격한 compressed probe와 혼동한 설명이다. 최종 compressed .01cm와 raw 검사를 구분한다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Main Source3/? Contact55 material2/Preview map/UnrealEditor-KhazanSnowContact55QA_20261007.dll? ?? ????. ?? native PIE ?? ?? /Game/Maps/L_HeinMach_Environment_Contact55_20261007, fresh background Main PID24660, 12:08:02 UTC Khazan.Snow.PIE Success?. GPU ?? ?34.000cm/??50.000cm?? ?? canonical /Game/Maps/L_HeinMach_Environment? ?? ???? ???. ??? Main PID3528? HeinMach/dirty0/PIE???? ??? ???? ?? file lock? ????. ??? save/reload/PIE/camera/close? ???? ???. FinalVerification? success=false/preview_verified=true/canonical_map_pending=true? ??? Preview ??? ????.
Snow existing owner/?runtime0, QA posefreeze? ??. ?? CPU ??0.702610/P95 1.859600ms(Development Editor), GPU/shipping?. ?? proof?worker2256/??CAS???canonical? Snow Engineering ?? ?? pending ?? ???.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
Snow existing owner/새runtime0, torso QA posefreeze만 후속 수정했다. 실제 CPU 평균0.702610/P95 1.859600ms(Development Editor), GPU/shipping 미검증. 현재proof·worker2256/안전CAS·남은canonical은 Snow Engineering 정본 이번 pending 절을 따른다.


## 2026-10-07 23:36 KST — Torso·Leg 천 조정 Main 반영

`PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md`의 이번 완료 절과 `Metadata/PlayerParts_20261007/ClothRefinement/Verification.json`을 따른다. 기존 PA2에 Hair 기준 복원·감쇠, 실측 Leg full-strip contact, uniform principal-inertia floor(Torso1/Leg4), Leg Depth0 swing32deg와 solver24/4/4를 적용했다. 원작 physics 직접값은 미확인이며 임시값/계산값을 구분했다. Hair·본체·BP/ABP·Main Source/DLL은 보존했다.

fixed30 및 fresh 일반 시간 간격 native PASS, 메인 실제 모듈의 Stock Guard/Heal와 Original5 runtime readback PASS. Main3528에서 PA2만 CAS/선택 reload 및 ready audit를 완료했고 HeinMach world·선택·dirty0/noPIE·보호161파일을 유지했다. Torso867정점은 세 표본 inside0, Leg dominant3835정점은111/390/350이 body proxy 내부다. 관통 완전 제거/모든 전투 pose 검증을 완료했다고 표현하지 않는다. 숫자·shape·inertia·Python readback 한계와 정확한 SHA/증거는 정본 및 보고서에 기록했다.


<!-- HeinMachGhosting_20261008_applied -->
## 2026-10-08 — HeinMach 이동 캐릭터 선명도·잔상 수정

SOURCE_BP_CONFIG_ARCHITECTURE.md의 이번 절을 따른다. 변경은 BP_Player template7의 기존254 mask 복원과 프로젝트 Config2이며 runtime Source/build0이다. Main3528 선택 reload 후8template254/dirty0 및 fresh saved-config·actual-input runtime 검증 성공. Original5 CopyPose/RigidBody·PA2, 열린 HeinMach map 및 Snow canonical pending guard를 보존했다.


<!-- ApesYetugaBehaviorResearch_20261008 -->
## 2026-10-08 — Apes·Yetuga 행동/공격 원작 분석 완료

APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md 최신보완절을따른다. Apes Early/Standard 가중군·피격횡이동/후퇴·연계, Yetuga custom121node/40CanUseSkill·거리/후방·조건부연속공격/두잡기/얼음/브레스·방어/부위파괴/고갈을원본과공개프레임으로대조했다. BT HPraw65/60/50단위·native event/취소·Rate/group reset·실제Brutal창은미확인이다. 공식고갈5→8초와CS term8이일치하지만 회복SI6.4와동일parameter가아니다.

이번패턴연구의게임Source/BP/asset수정·build·PIE는0회다. 기존ARCH-79의4NPC구현/StateTree/ComboAction·사용자변경을유지했다. Yetuga/Apes는library만있으며신규AI를적용했다고기록하지않는다. source/공개증거검증은ResearchVerification.json, 최초동명이름cache실패와정확package분리도보존했다. 직접구현후속은별도사용자요청과기존최소구조기준으로진행한다.


<!-- LeftShoulderCloth_20261008_complete -->
## 2026-10-08 10:38 KST — 플레이어 왼쪽 어깨 천 소폭 완화 완료

- Torso 왼쪽 Cape8 active SLERP stiffness만×0.95(어시스턴트 임시 튜닝, 원작 값 미확인). damping/limits/inertia/충돌/solver와 Hair·Leg, Main runtime Source/DLL 보존. Torso derived PA1을 Main PID3528에 전달·재로드 완료했다.
- fixed30 baseline/candidate, fresh saved native PIE 및 stock Original5 readback 통과. 짧은 패널 speed RMS+0.517%, Torso bend RMS+2.020%/tip RMS+3.319%의 작은 변화, 표본 Torso inside0. Main Original5/BP7/solver와 protected162 유지, PIE/dirty0.
- 일반 시간 간격의 기존 Hair35deg QA 실패는 원래 Torso 대조에도 재현됐다. Hair를 변경하거나 전체 조건 통과로 기록하지 않았다. `Metadata/PlayerParts_20261008/LeftShoulderCloth`의 `FinalCompletion.json`/`NativeComparison.json`/`NormalDeltaObservation.json` 및 physics 정본의 같은 날짜 절이 근거다.


<!-- HeinMachSnow_AttackContact_20261008_complete -->
## 2026-10-08 10:52 KST — HeinMach 무기 비공격 파임 수정 완료

무기 파임을 기존 active Attack Spec의 asset tag와 실제 지역 눈 표면 접촉에 제한했다. 비공격 이동 이력은 무기만 끊고 발/몸은 보존한다. 기본 HeinMach에 사용자55/35/50cm·rim 포함 발 반경축8×5cm 및 CPU 접촉 profile2를 반영해 이전 Contact55 canonical 대기를 완료했다. 새 runtime class/file0, CMC/ASC/Ability/AI/AnimInstance gameplay 변경0.

정본은 HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 같은 날짜 절과 Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/{Delivery,FinalVerification,MainVerification,NativeBuildProof}.json이다. private27636 및 fresh canonical Main652 Khazan.Snow.PIE Success, 메인 saved reload/정상 종료 확인. 이동 maximum35/55·공격 접촉50/55, GPU 발34/무기50cm. SnowTick CPU active1530 평균0.420499/P95 .817/max6.0138ms; 고정 공격 fixture를 포함한 Development Editor 측정이며 빠른 실전 sweep/GPU/shipping 검증은 아니다.

현재 canonical SHA57d8319…771ea7, manifest alias UnrealEditor-KhazanSnowWeaponContact20261008.dll SHAf6b86d4…8c2a2. 원래 DLL·이전 Preview/alias·머테리얼/캐릭터/ghosting Config와 비소유 Source를 보존했다. 이전 worker2256 중지·status archive 후 PendingApplyStatus는 SupersededByAttackContact20261008이다. 옛 Preview FinalVerification의 pending=true는 당시 증거이며 새 canonical 완료 근거는 이번 FinalVerification이다. 사용자 세션은 조작하지 않았고 마지막01:50:20 UTC에는 UE 연결/프로세스가 없었다. 다음 새 에디터에서 기본 HeinMach를 확인한다.



<!-- HeinMachSnow_AttackContact_20261008_normal_rebuild_verified -->
## 2026-10-08 11:01 KST — 후속 일반 Main DLL 빌드도 새 접촉 검증 완료

전달 뒤01:49:41 UTC Main 프로젝트 native build가 새로 실행돼 normal DLL과 manifest가 갱신됐다. 이 빌드는 본 작업이 시작한 것이 아니며 되돌리지 않았다. 최신 전체 Main Source가 본 작업의 검증된 NativeBuildProof와 byte 일치하고 canonical/Source3/기존 보호 asset·Config도 동일함을 확인했다. 현재 manifest는 `UnrealEditor-Khazan.dll`, SHA `4ca0cc527b9d94c6812246befd974e5ce268ec5ece23207add6394d369cde354`다. 앞 절의 alias 선택·원래 DLL 보존은 당시 전달 사실이며 현재 선택 모듈 정본은 이 절이다. 이전 성공 Delivery/FinalVerification을 수정하지 않았다.

새 hidden MainPID19372에서 실제 normal DLL 경로·저장 canonical profile2/55cm·작은 발 범위/scene9,869를 재검증했고01:58:40 UTC `Khazan.Snow.PIE` Success 및 정상 종료했다. Player Run142/Dodge236 표본 maximum35/55, Player/4NPC active 공격 지면 양성/공중·비공격·취소 음성과 기존 GPU 발34/무기50cm/cache/EndPlay 회귀가 통과했다. 자료는 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/NormalMainRebuild_20261008`의 snapshot Delivery(not_a_delivery), MainColdBuild.log, MainVerification/Exit, MainVerify.log다. 이번 Snow 수정·canonical 반영은 완료이고 old worker/preview pending을 재개하지 않는다. 기존 모듈 변경 및 source 보존 절차·원작/mip/normal/자연 fast sweep/GPU/shipping 미검증 범위는 유지한다.

같은 Development Editor/frozen attack scope의 normal DLL SnowTick은 active929 평균0.507301/P95 1.033800/max4.364200ms, `Profile(20261008_105739).csv`다. 이전 .420499ms와 조건이 다른 별도 관측이며 개선율로 비교하지 않는다. 사용자 에디터를 저장/종료/재시작하거나 예전 alias로 manifest를 되돌리지 않았다. 새 에디터에서 기본 HeinMach를 확인한다.

## 2026-10-08 — NPC4 보간·실시간 타깃 조준·공격/콤보 재조준, Main 전달 잠금 대기

직접 요청을 Work에서 구현했다. 기존 Controller GetDesiredRotation override/CMC root montage 회전 허용/ComboAction의 읽기 전용 InputEnd 선행 조회와 기존 AISettings3(임시60/180deg/s,.15s)을 사용한다. 새 runtime class/file/component/state 사본0이다. Combat BS sample weight 속도는 원작 Properties.TargetWeightInterpolationSpeedPerSec의 Swordsman6/SwordShield10/Heavy10/Halberd5를 적용했다. 유효 target 기억과 선택 행동 완료 후 재추격 정책을 유지하고 실제 현재 target 위치를 CMC desired yaw로 읽는다.

35공격/55node Facing 및32보행·접지/35패턴/자연AI·재추격·cleanup을 검증했다. 첫32 회귀의 Swordsman 사전 발견 fixture 오류는 감지 격리로 수정해 Success다. 이후 사용자 SpinningAttack2 및 공유 Combo의 최신 DoJump/Down 처리를 보존해 통합 build Succeeded40.41s, 최신 DLL c2a575…c3f5의 Facing 재검사도02:57:16 UTC Success다. scalar800/-500은 사용자 코드이며 이번 회전 튜닝값이 아니다.

Main Source/BS/manifest는 아직 미전달이다. Windows Restart Manager 확인 Main13700이 Swordsman BS 파일을 잠근 상태다. 사용자 editor를 조작/종료하지 않고 별도 검증을 계속한다. 최신 정본 MONSTER_FACING_SMOOTHING_20261008.md와 Engineering Continuity/DeliveryFailure/VerifiedDeliveryProof를 따르며 완료 receipt 없는 상태를 Main 완료로 표시하지 않는다.
## 2026-10-08 12:07 KST — 플레이어 허리 장식 충돌 떨림 수정·Main 반영 완료

- 현상/원인: Leg의 Iron2(`B_Iron_01_01_R_Pelvis` / `B_Iron_01_01_L_Pelvis`) collision capsule이 몸통 anatomy와 잘못 겹쳐 정지에도 빠른 회전 떨림이 지속됐다. 접촉만 끈 진단 대조로 원인을 분리했고, 최종에는 collision/simulation을 유지했다.
- 실제 변경: `Content/_Art/Player/Character/Meshs/Leg/Player_Original_Leg_RigidBody_PhysicsAsset.uasset` 하나의 capsule Center2만 변경했다. 질량·관성 scale·관절/drive·damping·solver 및 다른 body는 보존했다. 새 Center는 current imported LOD0 dominant 정점과 공통 골반 기준 anatomy18에서 계산한 임시 보정이며 원작 physics 직접 확인값은 아니다. runtime Source/Config 새 수정0, 새 runtime 파일0이다.
- 검증: 별도 Work native Candidate / fresh saved fixed30 / fresh normal delta 모두 PIE Success. Iron의 정지·이동 후 step RMS는 fixed30 0.168~0.207도/프레임이며 실제 actor collision/enabled=1 및 contact samples가 남는다. normal delta speed RMS4.65~6.04도/초다. Hair65 / Torso8 / Leg30의 기존 각도 검사도 통과했다. 이전 baseline 약78.84~82.56도/프레임과의 수치 비교는 동시 BP/Source intake 및 test bypass 차이가 있어 PA 단독 효과율로 단정하지 않는다.
- 반영: Main PID13700 / DevMap / noPIE에서 Leg1개 CAS 전달·선택 재로딩 Success, protected163 파일 동일성/dirty content·map0/actor·selection 보존. MainReadyAudit의 BP7·Original5도 통과했다. Main DLL을 Work에 묶은 별도 stock 확인은 base DLL 기준이며 Main의 Live Coding patch와 동일 실행이라고 주장하지 않는다. private DLL/PDB/modules는 exact hash로 복원했고 owned Work editor는 모두 종료했다.
- 기존 Hair PA 및 최신 Torso 왼쪽 어깨 조정은 unchanged다. 측정 범위는 정지·이동·해제 fixture와 body proxies이며 모든 pose/skin triangle 관통0을 보증하지 않는다. 정본은 `PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md` 최신 절, 상세 증거는 `Metadata/PlayerParts_20261008/WaistJitter/FinalReceipt.json` 및 같은 폴더 native/stock/Main reports다.
## 2026-10-08 — NPC4 이동 보간·타깃 조준 최종 작업본, Main 반영 대기

MonsterWork에서 기존 runtimeSource6/CombatBS4를 보완했다. root montage 중 CMC 회전 허용, 현재 타깃 위치의 desired yaw, 공격60deg/s·InputEnd 전 .15s 및 section 준비180deg/s 조준(명시된 임시값), 원작 BS sample weight 보간6/10/10/5다. 기존 StateTree·타깃 기억·행동 완료 후 Chase·원본 root를 유지한다. 새 runtime 파일0이다.

32방향/35공격 및 Facing·CombatPolicy·Guard가 통과했고, 기존 Heal 개발용 검사의 실제 phase/자연 종료 gate 보완 후 최종 DLL a6bed111…49d7에서 Heal도 통과했다. 정확 모듈별 실제 검사/이전 실패/해시/수치 출처는 MONSTER_FACING_SMOOTHING_20261008.md와 VerifiedDeliveryProof.json을 따른다. 사용자 동시에 저장한 SpinningAttack/DoJump·DoDown 코드는 보존했다.

Main Source/BS/DLL/manifest는 아직 미반영이다. Main13700이 Swordsman CombatBS를 잠그므로 사용자의 저장·종료가 필요하다. 최종16개 preflight는 통과했고 별도 own editor는 모두 정상 종료했다. 재개 절차는 ENGINEERING_WORK_CONTINUITY.md 마지막 NPC4 절이다. Main 적용·새 Main PIE 완료로 해석하지 않는다.


<!-- HeinMachSnow_PlayerCapsule_20261008_complete -->
## 2026-10-08 14:26 KST — 플레이어 capsule 눈 파임 완료

기존 Snow h/cpp2와 development test1을 보완했다. PlayerControlled capsule의 실제 바닥/반경과 지역 눈 높이에 따른 부드러운 원형 이동 footprint로 플레이어 발별 stamp를 대체했고, 몬스터 발/몸과 공격 중 접촉한 무기 경로를 유지했다. 이동35/55·무기50/55, capsule 실제R34cm 관측이며 새 radius tuning/UPROPERTY/asset0이다. layer55·shader/cache/field 예산은 유지한다.

Private cold build/전체 Stage 및 fresh Main Snow PIE/exit0가 통과했다. capsule 중심35cm·범위 밖/공중0·stationary bound·actual Run/Dodge, 기존 NPC/GPU/무기 비공격·취소 회귀 성공이다. Main CPU SnowTick 평균.747ms/P95 1.574ms(full Development fixture; FPS/GPU benchmark 아님). 새 alias a237a02f…7b58를 선택했고 canonical57d8319e…71ea7·map/Config/Original Player/Leg PA/normal DLL·비소유Source85를 보존했다. 사용자24552 DevMap/noPIE/dirty0는 조작하지 않았다. 현재 running editor는 재시작 후 새 native code를 적용한다. 정본 HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 같은 날짜 완료 절과 PlayerCapsule_20261008/CompletionValidation.json·QASummary.json을 따른다.

## 2026-10-08 14:39 KST — 왼쪽 어깨 천 추가 유연화 Main 완료

사용자 요청으로 Torso derived Physics Asset의 기존 Cape simulated 관절8개만 더 유연하게 조정했다. 어깨 바로 아래2개는 spring 615.537109→369.322266, damping 50.909088→39.434010, swing1/2 8.8→13.2도이며 중간2개와 끝4개에는 더 작은 강성·감쇠 조정을 적용했다. 원작 physics 수치 미확인 상태의 어시스턴트 임시 튜닝이다. 고정 부착2개·몸 충돌체·mass/inertia·twist·solver·Hair·Leg/Iron을 보존했고 새 Main runtime 파일/게임 소스 변경은 없다.

별도 Work cold build, 동일 fixed30 baseline/candidate 이동·해제 PIE, fresh saved-reload PIE와 실제 Main mapped DLL stock 확인을 통과했다. 짧은 천 첫 관절 speed RMS는 +29.82%, 긴 천 첫 관절은 +2.72%로 증가폭이 작다. Torso bend peak13.201777도, Hair65/Leg30 반응 유지, Hair·Leg·허리64 late windows는 baseline과 정확히 동일했다. Torso LOD0 양의 sim867·dominant735 정점의 세 anatomy18 snapshot은 inside0이다. 전환 순간을 포함한 관측이며 지속 flutter 비율·모든 pose의 skin 관통0·원작 수치 일치를 주장하지 않는다.

Main PID24552 DevMap에서 PA1 CAS 전달·선택 reload Success, protected166·actor/selection 유지, dirty content/map0. MainReadyAudit BP7/Original5도 통과했다. Main의 새 Snow module 선언과 실제 loaded base DLL은 달라 stock 검증은 현재 loaded C251AC…EC660 기준이다. 새 Snow DLL 실행 검증을 이번 cloth 작업으로 주장하지 않는다. private DLL/PDB/modules exact 복원과 owned editor0 확인을 마쳤다. 실제 완료 근거: Metadata/PlayerParts_20261008/ShoulderSoftening/FinalReceipt.json 및 같은 폴더 NativeComparison/SavedReloadComparison/CandidateProfileAudit/MainSelectiveHandoff/MainReadyAudit. 자세한 관절 계약은 PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md의 이번 완료 절을 따른다.

<!-- PlayerComboRepair_20261008_complete -->
## 2026-10-08 14:39 KST — 콤보 진단 및 마지막 약공격 Y 입력창 완료

Weak05에 존재하던 YBegin→Spinning edge가 InputOpen/Commit 누락으로 실행 불가능했다. 기존 Weak montage1개에 원작 Weak05 reserve metadata를 현행 timing으로 변환한 notify2개만 추가했다. 기존13 notify·Source/Controller/ASC/Ability/Data/BP·사용자 Spinning/DoJumpDown·모든 sequence/section은 보존했다. Main loader lock은 dirty0/noPIE 확인 후 해당 montage만 선택 fully-load/CAS/reload하여 해결했고 map/actor/selection/미저장을 유지했다.

new hidden Main7164/current capsule aliasa237…7b58의 실제 EnhancedInput7case가 통과했다. Weak01/Weak05 Y→Spinning, Charge02→03→04, RB→OverFury 및 창 이전Y 음성을 확인했고 보호192 동일/ownquit/dirty0이다. 일반 Weak01/Charge/RB의 이전 live 실패 원인은 미확정이며 stale DLL이나 입력 순서를 확정 원인이라고 주장하지 않는다. 정본은 SOURCE_BP_CONFIG_ARCHITECTURE.md의 같은 날짜 절과 PlayerComboRepair_20261008/CompletionValidation.json·FreshMain/MainVerification/Cleanup.json이다. current running 사용자 editor는 native capsule code를 위해 정상 재시작해야 한다.


## 2026-10-08 15:00 KST ? ??? HP?Stamina ?? ??

??4?+Apes+Yetuga? HP/MaxHP ? Stamina/MaxStamina? ??? ??? Main? ????. Swordsman/SwordShield100?50, HeavySwordsman/HalberdElite200?50, ApesStoneHandElite400?100, Yetuga1000?150??. ?? ??? ?? ??? ????. ?? AttributeSet/CharacterDefinition.InitialEffects? Instant Override GE? ????? C++ ??0, data asset12?? ????. Apes/Yetuga? DA+GE? ????? gameplay Actor/registry ??? ?? ???.

? Work28116 ? Main27884? saved reload?? ??24attribute field?????/dirty0? ???? own ?? ????. ?? Source/Config/??DLL/manifest95? Player template2? SHA ????. ??/???? ?????/??/UI/AI ?? ? ? build/PIE? ?? ??? ??. ??? MONSTER_AI_IMPLEMENTATION_20261006.md? ?? ?? ?? ?, ?? ??? Metadata/MonsterStats_20261008/FinalVerification.json??. ?? NPC4 ????? ?? ??? Main ??? ??? ? ??? ?? ??? ???? ???.


## 2026-10-08 15:52 KST — MonsterStamina 작업 중 및 이전 stats 기록 가독성 보충


기존 15:00 KST 몬스터 초기 수치 기록의 일부 한국어가 작성 과정에서 물음표로 손실되어 이 절에 가독성 있는 사실을 추가한다. 이전 기록은 삭제하지 않는다. 몬스터6의 GE_Init/CharacterDefinition 12개는 이미 Main 적용과 fresh saved readback을 완료했다. 값은 Swordsman/SwordShield HP100·Stamina50, HeavySwordsman/HalberdElite HP200·Stamina50, Apes HP400·Stamina100, Yetuga HP1000·Stamina150이고 모두 current=max이다. 근거는 Metadata/MonsterStats_20261008/FinalVerification.json complete=true 및 WorkSavedReload/MainSavedReload.json이다. 그 작업은 설정만 한 것으로 소진/회복/피격 기능 완료와 구분한다. Player 초기 GE2와 당시 Source/Config를 보존했다. Apes/Yetuga 당시에는 Definition/GE만 있고 gameplay BP/registry 연결은 없었다.

새 사용자 요청은 여섯 몬스터 공통 무자동회복·무공격Cost, 편집 가능한 피격/패링 감소량, 스태미너0 소진, 브루탈 어택의 양쪽 정상 완료 후 생존 MaxStamina 회복이다. 상세 계약과 수치 출처/미확인은 Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md를 따른다. 현재 native 구현은 별도 Khazan_MonsterWork_20261006/Khazan에만 있으며 Main 게임 Source/에셋 미전달이다. 첫 빌드는 다른 editor의 전역 LiveCoding mutex로 거부되어 독립 Work 출력에 NoHotReloadFromIDE로 재시도 중이다. 실제 성공 전 build/PIE 완료로 쓰지 않는다.


## 2026-10-08 — Player Combo 공격 충돌 Main 적용 완료

- 기존 Combo Ability/Definition의 작은 확장으로 공격 node18에 window60/key553, 공격별 편집 가능한 HP/Stamina damage와 초록색 debug draw를 연결했다. 기존 Monster ASC/Attribute/Guard를 재사용한다. 새 runtime class/component/manager는 없다.
- 최신 Source cold compile/link, 충돌 native13case, 실제 입력 전환6+조기입력 거절1, 기존 Guard/Heal 및 새 Main 저장 readback을 확인했다. 선택 전달6파일 외 보호146파일과 기존 stock DLL은 유지한다.
- 현행 정본: `Docs/Engineering/PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md`. 원작 근거와 임시 Cylinder/OverFury/피해/Guard 설정, 검증 한계, 정확한 전달·build·PIE 증거는 이 문서를 사용한다.
- 실행 중 Main은 구 DLL이므로 정상 재시작 후 새 DA를 편집/PIE한다. 다른 작업용 구 schema editor에서 해당 Player ComboDefinition을 다시 저장하지 않는다.


<!-- MonsterStaminaMainComplete_20261008 -->
## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료

여섯 몬스터의 stamina 정책·0 소진·전후 Brutal pair·양쪽 정상 완료 후 생존 Max 회복을 Main에 적용했다. 패링 hook은 실제 GE 감소/소진까지 검증했고 실제 Monster→Player 적중·패링 생산자는 아직 없다. 일반 Guard 성공을 패링으로 취급하지 않는다. 편집값은 각 DA_Character_<family>의 Monster Stamina와 Player ComboDefinition의 Nodes → AttackWindows → StaminaDamage다. Parry5는 사용자값, BrutalHPDamage0은 미할당, ExhaustionSeconds5/8은 저장 원작 값의 기회 시간 채택이며 0이면 무기한이다.

pending NPC4 Motion도 최신 Source와 같이 반영했다. native453/0실패, 회귀 Facing/Policy/Guard/Heal/Collision5종 Success, stock link 및 Main fresh readback/CDO/BS4/dirty0가 완료됐다. FinalVerification.json이 최종 증거다. 선택105행 외 보호 Source/Config82·asset138package·기존 canonical DLL은 hash 동일하다. 실제 선택 DLL은 UnrealEditor-KhazanStamina20261008-70158bc21dbb.dll이며 이전 task alias를 무조건 복원하지 않는다. 현재 사용자 editor를 제어/저장/PIE/종료하지 않았고 마지막 inventory에는 열린 UnrealEditor.exe가 없다.

Apes/Yetuga는 기존 Art body를 사용하는 gameplay BP/ABP/registry가 추가됐지만 autonomous AI/StateTree/DevMap 배치는 추가하지 않았다. 정확한 사용법·미검증 범위는 소진 정본 최신 절을 읽는다.


<!-- MonsterStaminaConcurrentMainBuildVerified_20261008 -->
## 2026-10-08 17:39 KST — 후속 Main 기본 DLL 빌드 보존·재검증

전달 완료 뒤 본 작업이 시작하지 않은 Main native build가 새 canonical DLL과 manifest를 만들었다. 해당 build는 Succeeded이고 선택 모듈은 현재 `UnrealEditor-Khazan.dll`, SHA `3a2b4942da22fdf94cc7cf6581da3b5fb04f63475315c675d66ef6c4782e758d`다. 이전 unique alias 전달·canonical 보존은 당시 사실이며 현재 모듈 선택을 과거 alias로 되돌리지 않았다. 전달105행과 전체 Source/Config가 검증한 현재 구현과 동일한 것을 확인했다.

별도 fresh Main commandlet에서 현재 canonical DLL을 실제 로드해 저장 Definition6+Player1/montage20/sequence49/attackBP35/body2 및 NPC4 BS·CMC/AI CDO·dirty0를 다시 확인했고 exit0으로 종료했다. 증거는 Metadata/MonsterStamina_20261008/{ConcurrentMainRebuild,FinalVerification_CurrentMain,MainSavedReload_ConcurrentBuild}.json과 ConcurrentMainBuild.log다. 이 새 DLL에서 native453/회귀5종을 다시 실행한 것은 아니며 동일한 제품 Source의 이전 Work runtime 결과와 새 Main saved readback을 구분한다. 사용자 Main19576은 읽기 inventory로만 확인했으며 제어·PIE·저장·종료하지 않았다. 이제 현재 Main 기본 DLL을 사용하고 과거 전달/authoring helper를 재실행하지 않는다.

<!-- PlayerAttackVFXMainComplete_20261008_1911 -->
## 2026-10-08 19:11 KST — Player 공격 VFX Main 완료

현재18 Combo 진입 및 Front/Back Brutal의 원본 효과 occurrence를 Main에 연결했다. 선택 전달은11Source(runtime10/dev1)+8몽타주+15Art, 총34파일/23패키지다. 최신 전체Source/build와 독립 Main 변경·기존 canonical DLL/Config를 보존했고 새 고유 alias를 실제 fresh Main에서 검증했다. native18+Brutal5case Success/176captures/머테리얼 fallback0/save0/exit0, 저장 몽타주401ID·8,308field 재로드 Success다.

Brutal의 현재 피해0에서는 조건부 혈흔0이 정상이며 제품 피해 설정을 바꾸지 않았다.6.25 양성은 transient 개발 fixture다. 원작 shader topology·픽셀 일치/BattleEffectIndex/멀티플레이는 완료 주장에 포함하지 않는다. 사용자 Main16572는 마지막 읽기 확인에서 clean/noPIE였고 저장·종료·reload하지 않았다. 구 모듈 에디터는 정상 재시작 후 새 Notify schema를 사용한다. 현행 계약·한계·재개는 [실행 정본](PLAYER_ATTACK_VFX_RUNTIME_20261008.md)의19:11 완료 절과 [Continuity](ENGINEERING_WORK_CONTINUITY.md), 최종 증거는 [FinalVerification](../../Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json)을 따른다. 이전 추출/author/retime/alias delivery를 반복하지 않는다.


<!-- MonsterBrutalDamage50_20261008 -->
## 2026-10-08 19:48 KST — 브루탈 어택 총 HP 피해 임시50 설정

사용자 요청으로 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga의 `/Game/Monsters/<family>/Data/DA_Character_<family>` → Monster Stamina → `BrutalHPDamage`를0에서50으로 저장했다. 단위는 HP 절대량이고 원작 환산값이 아닌 사용자 지정 임시 튜닝이다. 앞/뒤 공통 브루탈1회당 총량이며 기존 `BrutalHit2`에서 한 번 적용한다. 패링·일반 공격의 Stamina 감소량과는 별개다. 이전 미할당0/조건부혈흔0 기록은 당시 검증 상태로 보존하며 현재 설정은 이 절의50을 따른다.

수정은 CharacterDefinition6개의 해당 필드뿐이다. 다른 stamina 설정·LocomotionConfig·UnawareRoutines·InitialAbilityGrants·InitialEffects를 수정 전후 및 새 별도 Main commandlet 재로드에서 동일하게 확인했다. Source/런타임 클래스/몽타주/모듈 선택은 편집하지 않았다. metadata 증거는 `Metadata/MonsterBrutalDamage50_20261008/Authoring.json`, `FreshSavedReadback.json`이며 원본6파일은 같은 경로 Before에 보존했다. 두 commandlet은 별도 프로세스로 성공 종료했고 사용자 에디터를 제어하지 않았다.

이번 검증은 저장된 값50과 다른 필드 보존의 읽기 검사다. 기존 양수 피해/중복 방지/양쪽 완료 native 검사와 VFX transient6.25 검사는 과거 결과이며50으로 PIE를 새 실행한 것으로 기록하지 않는다. 기존 확정 적중을 읽는 VFX 정책은 이제 실제 양수50 피해에 적용될 수 있으며 VFX가 추가 피해를 만들지 않는다. 조정은 같은 DA의 BrutalHPDamage에서 수행하고, 과거0인 author receipt/asset payload를 현재 설정 위에 다시 전달하지 않는다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — 일반 피격·Shield 방어·브루탈 Main 완료

Main에 runtime16개와 에셋130개를 실제 전달했다. Player/Monster6의 종류별 랜덤 피격·지원하는 쓰러짐/기상, SwordShield 전방/노드 방어, 기존 Guard 랜덤, 브루탈 접근·짝 피해 모션·사용자 HP50·양쪽 완료 후 생존 스태미나 회복을 연결했다. 신규 class1개이며 기존 구조를 재사용했다. 임시 helper3은 제품 Source에 없고 Build.cs/Config를 보존했다.

stock build와 RHI32/15/3·회귀4종·fresh Main654,552검사/실패0/dirty0 완료다. 현재 Main 선택 모듈은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`이며 canonical은 보존했다. [정본](COMBAT_REACTION_RUNTIME_20261008.md), [사용/조정 설명](../../Metadata/CombatReaction_20261008/UserGuide_20261010.md), [최종 증거](../../Metadata/CombatReaction_20261008/FinalVerification.json)를 따른다. Heavy Launch·Giant 전용 fallback과 임시 world 이동/Monster 피해값의 출처를 원작 완전 복원으로 해석하지 않는다. 별도 VFX 작업의 완료 상태는 그 작업 문서를 따른다.

<!-- BrutalInputDevMapComplete_20261010 -->
## 2026-10-10 — 브루탈 B 입력 Main 적용 완료

현행 브루탈은 패드 B(Input.Action.B)다. 기존 Controller/ASC/Brutal 경로를 Source4개의 작은 추가와 InputAction1개·기존 입력/Player grant 설정으로 연결했다. 새 runtime class/file0개, X 약공격·Y 강공격·A 회피 유지다. [runtime 정본 최신 절](COMBAT_REACTION_RUNTIME_20261008.md)과 [최종 증거](../../Metadata/BrutalInputDevMap_20261010/FinalVerification.json)를 따른다. Main build·fresh saved28/dirty0·PIE6종12마리 초기화·인간4종 CombatPolicyPIE 성공, 작업용 에디터 정상 종료와 byte 불변을 확인했다. 실제 패드 B 누름은 사용자 직접 테스트 범위다.

현재 선택 모듈은 UnrealEditor-Khazan-20261010.dll이다. 이 선택은 이번 검증 시점이며 후속 작업은 current manifest/Source를 먼저 확인한다. DevMap 바닥/배치의 실제 저장 결과와 원작 근거 없는 임시 배치 수치는 Art state의 같은 날짜 절에 분리했다.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — 몬스터 VFX Main 전달·새 모듈 검증 완료

기존 GAS Action/Exhaustion·Monster·Definition·engine Notify를 재사용한 runtime9(신규 Notify h/cpp2 포함)+DEV2, author499, Art457, reused WPO1 및 adapter supplement4 총972개를 전달했다. Sequence487·source2855+sentinel487=State3342·Death6의 fresh Main saved/네 실제 RHI·Root 표본 검토는 [FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)의 실제 `MainDeliveredAndFreshVerified`다. 선택 alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`다. ARCH-85/B 입력/DevMap·외부 Source3/Shared14·사용자 피해50을 보존했고 fake hit/새 AI/FSM/Manager를 만들지 않았다. adapter·미검증 범위는 [실행 정본](MONSTER_VFX_RUNTIME_20261008.md), 새 ARCH-86와 외부 follow-up은 별도다.

초기968/Art457은 보존하고 Main 누락 adapter4를 별도 strict supplement로 추가한 최종972 기준이다. Source/native/material graph와 private proof는 유지했으며 새 Main 최종 검증은 추가 전달 이후 결과다.

## 2026-10-11 — ARCH-83 Player VFX polish 최신 Main 실행 검증 완료

[Art-only 완료 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json)의6개 머테리얼 후속 전달과 최신 Main Source101/b84 actual RHI18+Brutal5·FirstPose13·Saved401/Art18·Input13 보존 검사를 완료했다. Source/native/modules 쓰기0이며 외부 Monster Build19/Source11 migration 및 기존 Player alias를 보존했다. Private98/d195는 예비 Art 회귀 증거, fresh Main02가 현재 실행 증거다. shared factory의 동일 sampled-local 복원과 일회 pose callback/cleanup을 확인했고 새 runtime 구조는 추가하지 않았다. 현재 코드/검증과 decal-only EnsureIsComplete 정정은 [VFX runtime 정본](PLAYER_ATTACK_VFX_RUNTIME_20261008.md)의 같은 날짜 추가 절을 따른다. 원작 shader/pixel/Shipping 성능 한계는 Art 정본에 기록했다. 사용자/외부 에디터 제어0.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — ARCH-86 Apes·Yetuga StateTree / 플레이어 낙하 Main 반영

[FinalVerification](../../Metadata/GiantCombatFall_20261011/FinalVerification.json)은 MainDeliveredAndFreshVerified다. current module UnrealEditor-Khazan-20261011.dll/MainBuild02·fresh saved150+DevMap·실제 Main RHI 낙하·X 낙하공격·전투8사례를 통과했다. runtime 기존13+새 h/cpp6·DEV1·editor Json rule1, Content151이며 별도 FSM/Manager/컴포넌트 추가0이다. 제품176/보호 Source84/VFX Content965 해시를 확인했다. 원본 sequence/기존 VFX·DeathPresentation·Player .01·Brutal B/50·12마리 배치를 보존했다. Work author helper/heavy module rule은 Main으로 전달하지 않았다.

[구현 정본](APES_YETUGA_FALL_IMPLEMENTATION_20261011.md) 마지막 절의 source48/81노드·일반 후보10/28·조건/쿨다운/이벤트·실제 CMC 착지 계약 및 원작 동일성 경계를 따른다. DevMap Engine Cube1 top1200/Start(-350,0,1292)는 사용자 낙하 테스트용 임시 배치다. 모든 native BT sequence와 MoveTo/grab/Spell/camera 및 source 누락 모델을 완전히 재현한 상태라고 표현하지 않는다. 타/사용자 에디터 제어0, Python gameplay 조작0, 검사 에디터 정상 종료다.

## 2026-10-11 — HeinMach clean presentation: 카메라·루트모션 검증 완료

기존 AKZMonster ctor의 Capsule/Mesh 및 BeginPlay의 실제 UPrimitiveComponent 전체에 ECC_Camera=Ignore를 적용했다. Blueprint collision profile/modular parts 초기화 뒤에도 유지하며 Pawn/Visibility/World 응답과 SpringArm probe는 변경하지 않는다. 작성자/소비자는 기존 Monster 초기화/기존 SpringArm이고 game thread의 Pawn 수명에 묶여 새 상태/handle/cleanup/Ability 수명은 필요 없다. Source1파일, 새 runtime 파일0이며 ARCH-83/v2의 효과 생성·실행/취소·피해 책임은 유지했다. 현재 KZActionAbility/Combo/Notify timing은 이번 작업에서 편집하지 않았다.

MainBuild02 성공/입력 해시 불변, 현재 Main 모듈 UnrealEditor-Khazan-2026101101.dll. 실제 FinalVFXPIE03 native18+Brutal5 Success/compile·fallback0/save0이며12마리 모든 PrimitiveComponent Camera Ignore를 확인했다. 기존 GiantCombatFall/MonsterVFX/Player alias 및 gameplay 구현 위에서 빌드했으며 옛 private native alias로 되돌리지 않았다.

MonsterAnimationAudit02의 BP7/hard·soft closure1380에 연결된 사용 AnimSequence238은 전부 이미 root motion enabled, disabled0이었다. animation write0, ABP6의 RootMotionFromMontagesOnly/force-lock/rate/length는 유지했다. RootMotionFromEverything 전환이나 root displacement repair를 한 것으로 표기하지 않는다.

Art의 PP8 제거/nonPP9861 유지, exposure128, 차지/OverFury/혈액 교정·원본/TEMP 수치와 검증 범위는 [Art 정본](../Art/HEINMACH_CLEAN_PRESENTATION_20261011.md)에 분리했다. Engine 기본 exposure/HDR/AA/Fog는 유지하며 프로젝트 Bloom/MotionBlur/LensFlare/LocalExposure 기본값은 Art 요청을 위해 조정했다. [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json), [정확한 Source/Config diff](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/OwnSourceChanges.patch)가 최신 적용 증거다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](../Art/HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->
## 2026-10-11 — Main 통합 및 Combat UI 완료

미전달 CombatPresentationFix source8/content19를 최신 Main에 선택 병합하고 fresh stock build/saved readback/paired12/Snow/UI/VFX18+Brutal5를 완료했다. 최종 VFX392 captures/material fallback0, canonical DLL SHA `c908da8696b7844df39c7d476aa3ea8c10b96d206137b359c9252940d13c98bf`다. 기존 완료 MonsterVFX/GiantFall/PlayerVFXPolish/HeinMachCleanPresentation을 유지했다. 구현/수치/backup/정확한 검증은 [후속 정본](COMBAT_PRESENTATION_FOLLOWUP_20261011.md) 및 [UI 정본](COMBAT_UI_RUNTIME_20261011.md), 각 FinalVerification을 따른다.

Combat HUD는 원작 texture16/font1/material adapter2로 actual TargetPoint 록온·적격 B 전환·player/normal overhead/Yetuga top HP·Stamina 및 양방향 표시 보간을 구현했다. Source10/Content27과 실제 WBP 소비를 검증했다. gameplay HP·Stamina/Ability 수명은 ASC/기존 Ability 소유다. 표시 `.35초`와 head/discovery·Art 후속 수치는 명시된 임시값/원작 기반 계산값을 구분한다. 필수 잔여 작업0/own editor0이며 원작 전체 pixel/frame·멀티플레이·Shipping 성능 완료를 뜻하지 않는다.

## 2026-10-12 — ARCH-88 Monster VFX·피격/사망·Combat UI Main 완료

Main Source10/asset59, 새 runtime 파일0이다. 공격 첫 spawn을 finalized bone pose 뒤로 옮기고 혈흔 floor producer42/mesh receiver16을 제거했다. 실제 accepted hit의 검붉은 피, normal/paired death 완료 뒤 black ash·3초 TEMP dissolve·Destroy, UI_Chest에 매 프레임 붙는 LockOn/B, immediate HP/ST와 감소 잔상, transparent CurBar/별도 gradient dark track, compact Elite124×22를 적용했다. 실제 build·fresh RHI Attack198/1577/death6/actual hit13/UI02/fallback0/Exit0 및 최신 saved audit가 통과했다.

출처·TEMP·표시 검수는 Docs/Art/MONSTER_PRESENTATION_REPAIR_20261011.md, runtime/cleanup/정확한 resume는 Engineering ARCH-88 완료 절, 최종 source/asset SHA·loaded module·동시 audio67 보존은 Metadata/MonsterPresentationRepair_20261011/FinalVerification.json을 따른다. Source/selected visual field는 검증 이후 동일하며 사운드 작업의 후속 GUID 재생성24는 최신 파일로 보존했다. 필수 잔여0이다. 원작 native correction52/stripped shader·pixel/frame 완전 일치 및 Shipping 성능 완료를 뜻하지 않는다.


## 2026-10-12T02:04:36+09:00 — ARCH-89 사운드 runtime build·준비본 검증 / Main37 잠금

Build29/current alias2026101303는 성공했고 제품 runtime 및 자체 audio editor/QA는 그 build input과 동일하다. 이후 다른 작업의 DEV2 변경은 보존하고 전체 현재 Source 일치와 구분한다. Notify2 class/새 runtime4 및 기존 owner6파일의 작은 확장으로 타이밍·확정 피해/guard·비행음·cancel/EndPlay를 연결했다. 실제 family/cancel/loop/flight 및 기존 gameplay 회귀 출력은 검증됐다. Python 배열 사본 재기록 누락의37 asset 수정본은 prepared 검증 완료·Main 잠금 대기이며 complete=false다. 상세 계약·현재/원작 미확인 범위와 exact resume는 Engineering continuity 마지막 ARCH-89 및 ResumeState05/PreparedVerification01을 따른다. 사용자/foreign editor 제어0, 무관한 Source/feature rollback0이다.


## 2026-10-12 — ARCH-90 패링 준비본: 실제 검증 / Main 잠금

기존 Guard/ASC/Combo/MonsterSkillObject 6 runtime 파일의 작은 확장으로 시작 후 0.146초 전방 blockable 적중을 패링한다. 원작 raw 0.292초를 현재 GuardStart inverse_map으로 계산했으며 비용 배율 0.5와 effect detach 0.06초는 직접 source 값이다. 기존 몬스터 Definition의 사용자 결정 ParryStaminaDamage와 Pattern Parried/고갈 정책을 재사용한다. 새 runtime class/file/태그/GE/Manager는 0개이며 새 DEV test 1개다. Source·책임·cleanup·값 구분·에디터 설정·검증은 [PARRY_IMPLEMENTATION_20261012.md](PARRY_IMPLEMENTATION_20261012.md)에 기록했다.

task-owned ParryWork의 실제 melee/field 15개 상황과 6종 몬스터, 고갈/좌측 response/비용/동일 HitGroup/독립 연타/Release/Cancel/UnPossess를 확인했다. 기존 Guard와 PlayerAttackCollision도 성공했다. 기존 5개 재생 segment·notify는 fresh reload로 동일하며 Montage refresh의 Suc_R 파생 cache 차이는 따로 기록했다. 원작 normal Guard의 JustGuard 설정을 그대로 복원한 것이 아니라 사용자 요청에 따른 시작 창 adapter다.

**Main 구현 반영은 미완료다.** GA_Player_Guard와 AM_DAS_Player_Guard가 기존 Main editor PID19752의 Windows 공유 잠금(error32)으로 대기한다. 대상 SHA 충돌0이며 Source·package를 부분 복사하지 않았다. 사용자/foreign editor 종료·제어0, private DLL/과거 manifest 복원0이다. 현재 잠금과 candidate SHA는 Metadata/Parry_20261012/DeliveryPreflight.json, 준비본 검증과 정확한 재개는 PreparedVerification.json/ResumeState.json을 따른다.



## 2026-10-12T04:22:44+09:00 — 사진 기준 몬스터 혈액·지면 혈흔 Main 완료

Main runtime2/DEV2/신규 유효 package5·build2026101254·fresh saved/CDO6·실제 눈 RHI6종/24혈액·12소멸/지면 lifetime·actual collision13을 완료했다. 이전 ResumeState/ResumeState02의 pending은 이 절에서 대체한다. 정확한 현재 SHA/loaded module·수치 출처·한계는 Metadata/MonsterBloodReference_20261012/FinalVerification.json, 다음 절차는 ResumeState03.json과 Architecture 최신 ARCH-88 및 Art 정본을 따른다. 첫 shader fallback/몸 안쪽 발생/횃불 과노출을 기존 owner·재질만 보완했다. 사용자 PID19752/foreign editor 제어0이며 새 C++를 사용하려면 사용자 editor의 정상 재시작이 필요하다. 남은 필수 구현0; 원작 native/pixel/frame parity·Shipping stress는 별도다. 기존 사운드/패링 준비본을 덮어쓰거나 완료된 broad author/delivery/archive를 반복하지 않는다.


## 2026-10-12T08:12:54+09:00 — 사진 혈액 작업의 실제 메인 에디터 적용 완료

후속 사용자 요청으로 기존 Rider Khazan Run configuration에서 Main editor PID23736를 열었다. 이전 사용자 PID19752는 작업 시작 때 이미 종료돼 있었고 강제 종료/기존 세션 저장/ResetLoaders/hot reload는 하지 않았다. 실제 연결된 editor의 project_dir은 Main, world는 /Game/Maps/DevMap.DevMap, 실제 로드 DLL은 UnrealEditor-Khazan.dll, SHA256=fca93bc83565103f376db28049c628fb63950acfc62840a9b6baae94e155a405다. 몬스터6 CDO가 FP_Monster_HitBloodReference/M_Monster_HitBloodGround와 UI_Chest를 읽는 것을 해당 프로세스 안에서 확인했다. dirty content0/map0, asset save0이다.

다른 작업의 Guard/ASC·패링 Source 반영 뒤 UHT generated header가 Guard UCLASS15/GENERATED_BODY18과 달리 이전13/16으로 남아 합본 빌드가 실패한 상태였다. Source 내용 변경 없이 Guard/ASC header의 timestamp만 갱신하여 UHT를 재실행했다. MainEditorBuild01(2026101255)은 exit0/input동일이며 생성 macro도15/18로 일치했다. 이후 다른 작업의 성공한 current1290 선택을 보존했고 그 DLL에서 actual PlayerAttackCollision13을 fresh Main으로 다시 통과했다. Rider 실행은 현재 canonical DLL을 선택·로드했다. 서로 다른 DLL SHA를 같은 바이너리로 표현하지 않고 동일한 current 전체 Source hash와 각 실제 loaded module을 별도로 기록했다. 혈액 Source4/package5는 앞선 FinalVerification와 동일하다.

이 절은 이전 혈액 완료 기록의 '사용자 Main 미재시작/정상 재시작 필요'만 대체한다. 새 runtime 파일/제품 코드 편집0, 기존 사운드·패링 내용의 롤백0이다. GUI/viewport screenshot API는 inactive Slate 때문에 실패했으므로 화면을 직접 검토했다고 기록하지 않는다. 실제 PID/project/world/native loaded module/CDO로 적용 확인을 완료했고 Main editor는 열어 둔다. 정확한 증거는 Metadata/MonsterBloodReference_20261012/MainEditorIntegration/Result.json, 최신 재개 상태는 ResumeState04.json이다. 앞선 실제 시각 검증24혈액/12소멸·수치/한계는 기존 FinalVerification.json과 Art 정본 최신 절을 유지한다.


## 2026-10-12T08:17:34+09:00 — ARCH-90 패링 Main 적용·fresh 검증 완료

이전 준비본/Main 잠금 대기는 패링 범위에서 해소됐다. Main Source7(runtime6/DEV1)/package13(기존2/신규11)을 SHA 확인·백업 후 전달했다. 현재 전체 Main Source/Config로 MainBuild02가 성공한 뒤 일반 stock build가 현재 모듈 UnrealEditor-Khazan.dll을 선택했다. 이를 과거 suffix로 되돌리지 않고 현재 모듈에서도 다시 검증했으며 actual loaded DLL과 동일한 Source/13 asset SHA가 FinalVerification.json에 결속됐다. MainBuild01은 copy2의 과거 mtime 때문에 구 UHT PROLOG13/BODY16을 재사용하여 실패했다. 두 전달 헤더의 시각만 갱신해 PROLOG15/BODY18을 생성했고 제품 코드 내용은 바꾸지 않았다. 후속 전달 도구는 현재 write time을 사용한다.

새 MainPIE02의 Parry15개 상황/6종 Definition 소비·고갈·비용·연타·이동 Guard·좌측 response·release/cancel/UnPossess, 기존 Guard와 PlayerAttackCollision 회귀가 모두 성공했다. MainSavedAudit02는 저장0으로 설정/원본 5 playback segment·notify/7 section/source tag를 reload 검사했다. 실제 .13/.24초 화면에서 모션/weapon contact flash/연속 alpha를 직접 검수했다. 정상 가드 후 성공으로 창을 다시 열지 않으며 전방 blockable 공격만 패링한다. 기본 .146초는 기존 source→current inverse_map 계산, 비용 .5와 detach .06초는 source 값, 몬스터 ST 피해는 기존 Definition 사용자 결정이다.

이후 혈액 작업의 KZMonster runtime2/기존 DEV2와 모든 다른 Source/Config를 보존했다. 사용자/foreign editor 제어0·private DLL 복원0·Audio Notify 수정0이다. 초기 RHI에 GPU memory budget/낮은 FPS 표시가 관측됐으며 이번 fixed-step 기능 검사로 성능을 검증했다고 주장하지 않는다. 실제 스피커 출력(-nosound), 원작 shader/pixel/impact-point 완전 일치와 Shipping/network는 미확인이다. 필수 잔여0이며 최신 결과는 Metadata/Parry_20261012/FinalVerification.json과 ResumeState.json을 따른다. 과거 전체 author/추출/옛 alias를 다시 적용하지 않는다.



## 2026-10-12T11:04:18+09:00 — ARCH-91 Root·공격 콜라이더·VFX Main 완료
Main에 Source7(runtime4/DEV3) 및 RootMotionRootLock 옵션만 바꾼 Animation88 package를 exact SHA/CAS로 반영했다. 새 runtime file/class/manager0, 다른 baseline610파일 보존, private DLL/Config 전달0. MainBuild01은 source 오류 없이 PCH virtual-memory C3859/C1076로 실패했고, 병렬1/noXGE MainBuild02는 Succeeded/input unchanged다. 현재 canonical UnrealEditor-Khazan.dll SHA `e14ca4b34c8a8a8042c2087fca2e646196b51e617d906c1884bee4e6c29cf511`를 사용한다.
실제 사용395 Root enabled/force lock/true-root·track0 및 Body392의1176포즈를 확인했다. 첫 프레임 누적 origin88개만 RefPose lock으로 정렬했으며 근거는 RootLockPlan의 imported RAW root first transform와 skeleton reference pose/UE FRootMotionReset이다. RootAssetBefore 및 MainBefore 백업을 보존한다. 전체 DataModel 모든 key/curve/attribute와 notify event/object SHA392개가 변경 전=private 후=Main fresh로 동일하다. source montage126/definition57/node220/window405의 geometry key·time·HP/Stamina·group·audio와 rate/나머지옵션이 fresh saved audit에서 동일하다. Props3는 다른 skeleton으로 body1176포즈에서 분리하고395 옵션/track audit에 포함했다.
Main actual RootPoses/MonsterHits30/PlayerAttackCollision16 Success. monster30은6종별 한 window 안1회 / 종료 후접근0 / exact-end pause후접근0 / 취소후접근0 / live mesh scale와actor yaw 반영을 실제 HP GE로 확인한다. player16의 기존 Spin7/Fury19와blood13 기반행동도 보존한다. source scale/last-End 경계·timer 종료만 기존 ComboAction에 보완했다. VFX198 assets/1577 source occurrences 및Death6는 동일 delivered Source의 private 실제RHI Success, finite world transforms / deterministic uncorrected source geometry max position3.46e-13cm·angle4.83e-6deg / template identity / body size를 확인했다. 이 보고서의 active correction-curve row는0이므로 해당 branch의 per-pose 실행을 실제 데이터 검증했다고 표현하지 않는다. source 없는 VFX actor axes/mesh origin 및 body scale은 적용했으며 curve branch는 기존 receipt의 latest GT clock→finalized-bone callback으로 구조 보완했다. 원작 native shader/pixel parity·전체두레벨연속전투·network는 검증 완료 범위가 아니다.
Main 파일·canonical build·fresh saved/actual runtime 완료. FinalVerification.json / ResumeState03.json 및 exact Delivered95를 재개 정본으로 읽는다. stage/old alias/full author/retime/reimport를 반복하지 않는다. Main editor 정상 재시작 후 직접 Play에서 green debug volume이 실제 공격 window에서만 나타나고 칼의 크기·방향/몸체 alignment를 확인할 수 있다.


## 2026-10-12T13:12:55+09:00 — ARCH-92 사망·브루탈·액션 VFX Main 완료

Main Source10(runtime6/DEV4), montage8, 새 runtime 파일0을 적용했다. baseline Source121 중 무관111파일을 보존했고 원본 Root88/게임플레이 공격 창·피해·오디오·UI·애니메이션 raw pose는 변경하지 않았다. FinalBuild05 current canonical build/input동일, fresh SavedAudit02 8/55/dirty0/save0가 통과했다. Main 기존 파일을 직접 보완했으며 private DLL/Config 전달0이다.

일반 사망은 interruption을 완료로 간주해 현재 포즈를 멈추던 것이 원인이었다. 기존 RefreshCombatState로 다음 tick에 사망 동작을 재시작한다. DeathBaseline01의 중단6 오차167–441cm → DeathFixed02의 정상6/중단6 terminal pose 오차0. 짝 사망은 task blend-out 완료 시 source 마지막 pose가 이미 idle로 섞이는 문제가 있었다. HP0인 자기 victim instance만 auto blend-out을 끄고 Monster의 기존 GT tick이 finite end를 관측하여 Exhaustion의 기존 완료를 호출한다. shared asset/비치명타 recovery/정상·취소·EndPlay cleanup은 유지한다. LethalPairFixed01 실제 Front/Back12 terminal pose 최대0.015341 model cm, 접촉 XY offset0이 통과했다. 이는 사용자 전체 플레이에서 interruption 빈도를 계측한 결과가 아니다.

Brutal Root particle의 원본 source offset은 현재 capsule 짝 간격/수입 mesh yaw와 맞지 않았다. 기존 effect receipt만 찾아 detach/world XY 두 actor 중점·Z 두 chest 평균에 배치하고 기존 composed rotation/scale·피해·시간·수명은 유지했다. PresentationFinal02는 실제 LockOn→B 6종 Front/Back12, 비치명타 recovery/root-mode 복원 및 실제 낙하/착지/벽 옆 ground debris를 통과했다. EffectsFinal01 기존18+Brutal5, CollisionFinal01 실제16(Spin7/Fury19/miss/cancel/끝 접근), ParryFinal01 실제15/6종 정책도 통과했다. DEV-only viewport readback 추가 이후로만 실제 게임 화면을 판단한다. LethalPairFixed01의 이전 전역 screenshot은 editor viewport였으므로 시각 근거에서 제외한다.

혈흔은 기존 accepted-hit particle1회와 ground projector/fade/snow·walkable 계약을 유지하며 class 설정의6개 작은 satellite를90–280cm 범위/전체 방위로 생성한다. 독립 FRandomStream, 장애물/바닥/가파른 면 제외를 사용한다. DeathFixed01의 scatter0은 QA floor의 Static mobility로 scale이 반영되지 않은 fixture 문제였고 Movable fixture의 DeathFixed02 실제6종에서 main+6=7 /네 방향/범위/하향 normal을 확인했다. 제품 collision/지형을 바꾸지 않았다.

수치와 resource/표시 변경은 Art 최신 절을 따른다. 정확한 변경/각 실제 DLL/원본 보존/실패 기록은 Metadata/CombatFinishFollowup_20261012/FinalVerification.json에 있다. 원작 shader/pixel 완전 일치·Shipping stress/두 레벨 연속 전투는 이번 범위가 아니다. 이후는 현행 Main과 이 receipt에서 시작하며 stage/전체 author/Root·Parry 이전 전달을 반복하지 않는다. Main 정상 editor ready 여부는 후속 기록으로 분리한다.


## 2026-10-12T13:16:18+09:00 — ARCH-92 메인 에디터 적용 확인 완료

Rider normal Khazan Run으로 Main PID16504/DevMap을 열었다. read-only RiderLink가 실제 canonical DLL SHA a247fac8a6c457a90d336ceb9ed90a5445bca878295d941b1c5081a375977f9b와 FinalBuild05 일치, 6종 CDO scatter6/radius90–280cm, dirty content/map0를 확인했다. asset save0, PIE 미시작이며 에디터를 열어 둔다. FinalVerification.json은 MainDelivered_Built_Validated_EditorReady, ResumeState04.json은 complete/잔여0이다. 사용자 이전 Main은 착수 때 종료돼 있었고 강제 종료/HotReload/기존 session 저장0이다. 모든 실제 테스트·동일 runtime source·Art TEMP와 원작 한계는 앞선 완료 절을 유지한다.


## 2026-10-12T14:44:13+09:00 — 검병 발차기·돌진 제외 Main 완료 / 방패병 동작 식별 대기

사용자 요청으로 검병 GA_Kick와 GA_Rush를 기존 BP_Monster_Swordsman.AttackAbilities 및 DA_Character_Swordsman.InitialAbilityGrants에서 제외했다. 공격 후보5→3, 초기 grant14→12다. 남은 GA_EmpireSword_Early_Slash/Early_Smash/Pierce 및 Alert/Idle/Exhaustion/HitReaction은 유지한다. 기존 ARCH-77 StateTree 선택→ASC Spec 활성화→ComboAction 실행을 재사용하며 runtime C++/Tag/Config/DLL 변경0이다. 게임 리소스 삭제·montage/animation/collider/VFX/피해 설정 수정0, 새 runtime file/class0이다. 별도 Khazan_AttackFilterWork_20261012에서 두 asset만 저장했고 Main에 exact SHA/CAS로 전달했다. Prepared02 및 새 MainSaved01 Success/Exit0, AttackAbilities/InitialAbilityGrants와 보호된 AI/Locomotion/HitReactions/MonsterStamina/Unaware/InitialEffects의 원본 보존을 확인했다. DevMap 배치 검병7개 모두 후보3, 방패병1개 후보3을 fresh load로 확인했다. HeinMach에서 해당 두 BP의 배치 actor는0이다. 이는 saved policy 검증이며 새 PIE 실행·제자리 달리기 체감 검증으로 기록하지 않는다. 방패병은 수정 전후 모두 SwordCombo/Pierce/ShieldCrash 후보3, 초기 grant8이며 Kick 클래스가 없다. 두 방패병 asset의 byte SHA는 원본과 동일하다. 사용 중4개 sequence의 raw 발/골반 포즈41시점은 Probe02에 보관했지만, 수치만으로 사용자가 말한 발차기 동작을 확정하지 않는다. 방패치기인지 검 연속공격인지 사용자에게 동작 식별을 질문한 상태다. 임의로 sword swing이나 ShieldCrash를 제거하지 않았으며 방패 동작 제외는 미완료/식별 대기다. 정본은 Metadata/MonsterAttackFilter_20261012/FinalVerification.json 및 ResumeState.json. 확인 후 current Main의 해당 후보/grant 또는 실제 kick node만 작은 data 변경으로 제외하고 새 saved/배치 actor 검증을 수행한다.

<!-- MonsterAttackFilter_20261012_SwordsmanMainVerified -->


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 KZ_Parring_Distort Main 완료

기존 FallAttack의 Start3.741868019104004/End3.8630430698394775 branching 부모 안에 KZExtra_PlungeDistort child 한 쌍을 추가했다. 기존 source ground dust·GUID·section/segment·공격 판정/피해/오디오·RateScale은 보존했다. 최신 Main ARCH-95의 NiagaraTemplate/공통 UFX 실행·종료·module 의존성을 재사용하고 shared factory에 실제 traced floor normal의 User.KZFloorNormal와 sort/dilation 처리만 합쳤다. UObject receipt·끝/취소 cleanup은 기존 ActionAbility 소유다. UE5.8에서는 UFXSystemComponent가 기존 ParticleSystemComponent.h에 선언되므로 없는 별도 include 두 줄을 제거했다. 새 runtime class/file/tag0이다.

선택 전달8행(기존 runtime factory1/DEV1/asset6)과 include 보완2, MainBuild03 exit0, fresh MainSaved01 저장0, MainPIE02 actual input fall→landing의 유효1개·바닥/분리/normal·정지·기존 dust 유지가 통과했다. 실제 loaded current canonical module와 파일 SHA는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json에 있다. 초기 floor rotation90도 trial은 철회했고 최종 RelativeRotation0/Scale1과 normal binding을 사용한다. 사용자/foreign editor 저장·종료·reload0이며 후속 stock build의 current manifest를 보존했다. 필수 잔여0; 전체 author/과거 alias 전달은 반복하지 않는다.


## 2026-10-12T19:30:36.993088+09:00 — ARCH-96 몬스터 넉백·전체 FPS Main 완료

Main516행=기존 runtime2(KZHitReactionAbility.cpp/CharacterDefinition h)+DEV2/Build editor dependency1+asset511을 선택 적용하고 새 Main build/reload/실제 RHI를 확인했다. 기존 ASC·HitReaction/JumpForce Task·Definition과 취소/root-mode·회복 수명을 재사용했다. 새 runtime class/file/manager/tag0, private DLL·Config 전달0이다. 다른 작업의 Player0.1초 제어 제한/ground-hit 분류/원작 StateTree 추가와 최신 공격 VFX88개를 보존했다.

MainBuild01 exit0, MainSaved01의461 sequence3854855 bone key/notify GUID·시각·158 montage의 actual sampling 및 재생 시간 차이0, MainKnockback01의6종11case(인간 F/B8/Giant2/벽1)·회복/재피격/cancel/root-mode 복구, 기존 실제 monster collision 회귀가 성공했다. MainInventory01의 전체2674 sequence/158 montage에서 소수 sequence/model·sampling0,100000fps fallback0이다. native loaded module/516SHA/각 evidence는 Metadata/AnimationTimingKnockback_20261012/FinalVerification.json에 결속했다.

인간4종은 기존250cm와 실제 HitLand 시간을 유지하며 Definition.KnockbackTimeMappingCurve에서 normalized2u-u² TEMP 감속을 조정한다. baseline 착지 직전 약278–375cm/s의 일정속도 → 최종 약8–28cm/s로 줄어든다. RootSource 제거는 엔진의 MarkedForRemoval/다음 이동 tick 삭제를 구분해 검증했다. Apes/Yetuga는 NoAir/NoBlow 대체 clip의 짝 grapple root 이동을 해당 실행 instance만 PushDisableRootMotion으로 억제하여 baseline−278.01/−222.11cm →0cm다. source clip/raw/root 옵션 및 Short fallback·정상 Launch Task는 보존했다.

필수 잔여0이다. 현재 editor는 정상 재시작으로 새 C++/asset cache를 로딩한다. 사용자/foreign editor 제어0이며 이전 pending·failed trial 기록은 이 완료로 대체한다. 원작 curve keys/전체 pose·native/network/shipping parity는 미확인이고 TEMP를 원작 수치라고 부르지 않는다. 과거 author/추출/원본 retime/root repair/옛 DLL 전달을 다시 실행하지 않는다.


## 2026-10-12T19:50:49.391255+09:00 — ARCH-94 Apes·Yetuga StateTree / 짧은 피격·Dodge Main 완료

메인에 선택 Source21/asset19를 CAS 전달했고 기존 PlayerAttackCollision 개발 검사의 몽타주 시계 대기만 추가 수정했다(게임 Source/asset 총41, 새 runtime 파일·class·manager0, 신규 개발 QA3). `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`을 후속 정본으로 사용한다. 과거 Main 미반영·검사 대기 기록은 이 완료 절로 대체하며 원래 실패·중간 보고서는 보존한다.

Yetuga 원본 BT121노드(Route11/Gate49/UseSkill46/MoveTo10/LockOnMove5)를 source export·원시 property·성공/실패 후속과 함께 StateTree173상태로 구체화했다. 깊은 조건/route와 skill 선택 proxy는 선택 시 transition을 따라가고 실행 leaf46개는 실제 GAS 완료/취소 결과를 반환한다. MoveTo 성공 뒤 사용할 수 없는 기술은 원래 실패 후속으로 진행한다. Apes9상태는 기존 Early 후보/추격을 재사용하며 실제 HP 피해 이력의 SideMove passive3행을 연결한다. Definition의 OriginalPatternStateTree가 기존 배치 override보다 우선한다. Apes19/Yetuga28(24+NoCool/선택 step alias4) 기술을 기존 PatternAbility·Combo/Notify/발사체/필드로 실행한다.

플레이어 non-shield 피격의 마지막 실행에서0.1초 뒤 자기 montage/RMS/제약·root mode를 정리하고 다음 이동·회피를 허용한다. 이0.1초는 어시스턴트 TEMP이며 실제 조정 위치는 `KZHitReactionAbility.PlayerControlLockSeconds`다. 착수 계약의 Definition 소유 제안은 실제 구현과 달라 이 Ability 설정으로 정정한다. 몬스터/Shield 수명은 이번 단축 대상이 아니다. 동시 ARCH-96의 몬스터 curve/자기 montage root disable을 보존했다.

Dodge 시작0.1초 무적은 사용자 지정값이다. `State.Invulnerable`의 자기 기여만 추가/회수하며 실제 world-time deadline을 검사해 timer 지연이 무적 시간을 늘리지 않는다. melee/field/projectile/직접 capture 피해는 Guard·HP/ST·피격 적용 전에 ASC의 동일 승인 경로를 소비한다. 같은 공격 group의 회피 접촉을 소비하고 성공 표현은 한 Dodge 실행에서1회다. 종료/취소/실패의 timer·태그·자기 VFX cleanup과 타 원인의 무적 기여 보존을 확인했다.

MainBuild04 stock canonical build Exit0, runtime Source hash 일치다. 기다리는 동안 동시 개발 QA 파일만 바뀐 사실은 보고서에 따로 남겼다. 최신 MainFinalQA04의 compiled SourceAudit·실제7피격 SideMove·방어11사례/8방향 취소·피격 복구6사례·Sight→Roar→전투 및 실제47기술·PlayerAttackCollision(OverFury19회)이 모두 성공했다. Guard/Parry MainGuardQA02와 낙하/거대 몬스터 연계 MainQA01 성공도 보존한다. QA03은 synchronous 감사 뒤 불필요한 PIE 요청의 viewport 종료 race였고 driver만 수정해 QA04로 대체했다. 실제 native 실행이며 저장된 테스트 actor/fixture는 없다. Shipping/network 검증은 수행하지 않았다.

원작 custom BT의 native RNG/abort/CDO 생략값, Group1 부위 파괴 producer, selected-step float 및 원작 navigation/physics 의미는 미확인이다. Apes >=임계·history reset·독립 난수는 명시된 프로젝트 어댑터다. 원본 조건/연계 자료와 현재 UE 실행 검증을 원작 전체 무오차 동일성으로 확대하지 않는다. 후속은 이 보고서→기존 원작 metadata→필요한 native/원작 통제 자료만 표적 확보한다. 전체 재추출/과거 author·install/Work DLL 전달·재임포트는 반복하지 않는다.

<!-- BeastDodge_20261012_MainCompleted -->


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

사용자 최신 지시로 몬스터의 지정 Niagara 교체를 철회하고 원본120개 효과 occurrence를 복구했다. Player 원본50 start/stop쌍을 복구하고 별도 KZWeaponSlash child50쌍만 추가했다. immutable before package와220개 객체×21개 수정 field를 비교해 차이0이다. 원래 notify GUID/clock, ARCH-96 FPS·넉백, ARCH-94 방어/AI, SlamDistort·혈액/사망/UI/오디오를 보존했다. 과거 패키지 bytes 전체 또는 private DLL을 Main으로 덮어쓰지 않았다.

추가 Slash는 기존 Action effect receipt와 finalized-bone delegate로 소유한다. 실제 Weapon_L/R 뼈에 reference cutting-edge geometry를 연결하고 successive actor-space tip pose에서 이동을 뺀 swing tangent를 계산한다. FX marker의 별도 animation track은 실제 장착 무기의 대체 pose로 사용하지 않는다. X는 실제 접선, Y는 절삭면이며 requested mesh의200cm reference span/renderer yaw180·centre를 보정한다. Niagara component의 CurveRotation0/CurveScale1·Rotation0만 neutralise하고 shared Niagara asset은 보존한다. 정상/취소/node 교체·사망/UnPossess/EndPlay cleanup은 기존 receipt가 처리한다. 새 runtime class/component/manager/tag0, 새 개발 plunge QA1이다.

Native Player18+Brutal5/실제 승인 hit blood, collision16/Parry17·received-hit feedback/monster-overlap plunge ground·cancel, human33 actual attacks 및 original4-family FX·requested Niagara0이 통과했다. saved100 package에서 original monster120/player100+added player100을 확인했다. 실제 코드·에셋·loaded module 및 모든 검증은 Metadata/CombatImpactUpgrade_20261012/FinalVerification.json이다. 최신 normal Main editor를 열고 loaded module·dirty0 및 설정을 확인했다. Runtime Source가 같은 전체 suite와 DEV-only isolated4 preview를 구분한다. 이전 replace33 검증·실패 camera API·tail assertion은 최신 완료 계약의 근거로 쓰지 않는다.


## 2026-10-13T01:40:50.930443+09:00 — ARCH-97 StrongCombo 정면 반응 Main 검증 완료

StrongCombo 1·2·3타의6window를 인간형4종의 기존 정면 피해자 모션으로 고정했다. 기존 확정 피해/event/HitReaction Ability·Task와 cleanup을 재사용하며 새 runtime class/tag/manager·gameplay 수치0이다. 거대형/다른 공격 반응은 보존했다. Main runtime3/기존 DEV1/asset5, build·fresh saved·actual12case/24hit 및 기존 collision16 회귀 성공. 현행 사용법은 COMBAT_REACTION_RUNTIME_20261008.md 마지막 ARCH-97, exact SHA/실행 evidence는 Metadata/StrongComboVictimFront_20261013/FinalVerification.json이다. 필수 잔여0이며 과거 author/retime/delivery를 재실행하지 않는다.


## 2026-10-13 — 몬스터 보조 물리 준비·실행 품질 조사 중

사용자 직접 요청으로 player의 현재 물리 설정을 재사용한다. Router/Architecture/Migration/Physics/PlayerParts 정본과 저장 metadata에서 시작했다. 기존 gameplay6종 PhysicsAsset None을 확인했고, imported35 SK 전체에 PA35/secondary post-process20/Elite CopyPose1 및 기존 BP6 설정을 작업본에 생성했다. 신규 runtime class/component/manager/tag0이며 기존 KZMonster.BeginPlay의 modular follower 초기화만 작은 보완을 준비했다. 현재 Main 게임 에셋·Source 반영은0이다.

정확한 상태는 `Metadata/MonsterSecondaryPhysics_20261013`과 `Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md`다. NativeAudit01/Author01/HeavyCollision01 Success, PrivateBuild01/03/05 Success. 컴파일 도구 타입 오류 Build02/04는 실패 로그로 보존했다. 첫 PhysicsPIE01은6종 모두 finite/실제 simulation·반응/접촉을 관측했지만 Heavy Hair49.34°, Halberd142.77°, Apes90.63°, Yetuga177.71°가 기존 cloth45° QA를 넘어 **Fail**이다. 조작한 QA를 성공으로 기록하지 않는다. 새 candidate97 packages는 아직 전달하지 않는다.

별도 owned29816/LLDB에서 GameThread `FPhysicsRun::Sample` line110과 PA24/4/4·fixed1/60, active acceleration SLERP·hard angular limits·projection 값과 Halberd idle47.04°를 직접 관측했다. Engine/PDB 하위 stack은 미해결이며 root cause 확정 전이다. `DebuggerEvidence.json`을 보존하고 agent breakpoint 제거/session detach, 기존 user exception8 상태를 유지했다. Debug01은 중단시간 영향을 받는 진단 run이며 생산 성능/정상 타이밍 검증이 아니다.

재개: PrivateBuild06 확인 → 최신 owned process 목록/실제 project 확인 → `KZ_MONSTER_PHYSICS_NO_CONTACT=1` 진단 전용 PhysicsPIE 대조 → 같은 saved candidate의 접촉 활성 대조/worst bone·stage 비교 → geometry/관절 충돌을 근거에 따라 최소 수정 → flag 없는 fresh saved/native/RHI 및 실제 PlayerAttackCollision 회귀 → 최신 Main SHA/CAS·필드 병합과 별도 Main module build/검증 → 완료 기록. 기존 full Author는 existing-result guard가 있으며 반복 실행하지 않는다. 사용 중인 다른 ParticleAlpha/Main 작업 editor를 종료/저장/제어하지 않는다. 원작 anatomy17/17/16 capsule 형상은 `OriginalAnatomyShapes.json`의 field/raw 값, feel은 현재 player의 명시된 TEMP 재사용이다. 전체 원작 물리/skin 관통0 검증은 미완료다.

<!-- MonsterSecondaryPhysics_20261013_intake -->


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset / 천·Hair Main 완료

사용자 요청을 Main에 적용했다. imported SK35 전부 PA35를 연결했고, explicit cloth/hair가 있는20 메시에는 engine RigidBody post-process, 중검병3 모듈에는 shared CopyPose1을 연결했다. 기존 gameplay BP6와 SK35 수정, 신규 PA35/ABP21의97 package + 기존 KZMonster.BeginPlay 파츠 block1 + DEV 검증1의99행을 exact SHA/CAS로 전달했다. 신규 runtime class/file/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. protected Player/Config/기타 Source SHA 차이0이다. 기존 GAS/AI/Ability/피해·몽타주·root motion·VFX 소유자는 유지한다.

MainBuild01 Exit0, MainSaved02 저장0·35 링크/게임플레이 파츠 연결, MainFinalQA01 실제6 family 이동→방향 전환→authored attack section 모션→피격→회복·finite/물리 반응/몸 접촉/중검 CopyPose 및 PlayerAttackCollision 회귀2검사 Success다. 실제 loaded canonical Main module SHA와99 target SHA는 `Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json`이다. 최종 실제 peak: Swordsman:29.93° / SwordShield:29.18° / HeavySwordsman:30.80°,25.62° / HalberdElite:30.26° / ApesStoneHandElite:39.39° / Yetuga:37.86°. 정상 캐릭터 전체 world ragdoll은 off이고 engine post-process가 보조 뼈317개의 수명/취소/EndPlay를 소유한다. 테스트 floor/camera/fixture와 검사 settings는 별도 owned process에서만 사용했고 map/asset 저장0, user/foreign editor 제어0이다.

수치/형상 출처: Human Adult17/Elite17/Halberd16 원작 anatomy capsule은 OriginalAnatomyShapes.json의 package/export field/raw Center·Rotation·Radius·Length/SHA다. 해당 reference bone에만 사용하고 source NoCollision policy는 몸 접촉 목적의 활성 collision으로 변경했다. 그 외 anatomy는 실제 LOD0 dominant skin AABB에서 계산했다. feel은 현재 Player_Original_Hair/Torso_RigidBody_PhysicsAsset의 player TEMP spring/damping/각도/몸 damping·반경·mass-per-length와24/4/4·1/60을 재사용한 것이다. source original physics 전체 동일값으로 기록하지 않는다.

일반19 post-process는 unit enemy ComponentSpace, Yetuga1은 WorldSpace다. Yetuga37 짧은 털의 source784/56·8/8/3도·0.1/1.5·0.5cm는 유지하고 hard angular bounds/exact solver/실제 dominant skin tip sphere를 사용했다. skin uniform-box + pivot parallel-axis virtual inertia와 어시스턴트 TEMP 배율2로 과한 뒤집힘을 줄였고 큰 cloth4는 기존 virtual inertia TEMP2를 적용했다. 근거/수식/원시 support와 각 저장 값은 위 final report의 sources 및 saved native report다. 원래 고정점에서 겹치는 anatomy proxy pairs는 분리하고 그 외 몸 접촉을 유지한다. PA editor의 DefaultInstance.InertiaTensorScale, constraints의 spring/damping/limits/collision을 조정 위치로 사용한다. 새 gameplay tuning literal/runtime settings owner는 추가하지 않았다.

PrivateFinalQA01 Yetuga cloth49.67° 실패는 geometry/숫자를 바꾸지 않고 QA를 느슨하게 통과시킨 것이 아니다. cloth 관성만 보완한 PrivateFinalQA02의 fresh saved/RHI/gameplay3검사와 Main 최종 검증으로 대체한다. 이전 broad nonlinear/alpha1/geometry/soft limit 및 도구 compile/link 실패는 보존했다. ParticleConstraints count0은 immediate-mode의 등록 경로 차이이므로 관절 미생성으로 확정하지 않는다. debugger session/agent breakpoint는 정리하고 user exception 상태는 유지했다.

필수 잔여0이다. 현재 gameplay6 family runtime 검증과 그 외 저장 library variants 설정을 구분한다. 전체 source-game physics parity/모든 skin 삼각형 관통0/network/shipping은 검증하지 않았다. 후속은 이 완료 → final evidence → 대상 PA의 설정만 표적 확인한다. full author/메타데이터 전수 추출/원본 재임포트/Player 전체 author/FPS/root/VFX 재실행·옛 DLL 전달은 하지 않는다. 앞선 Main 미반영/검증 대기 절은 이 완료로 대체한다.

<!-- MonsterSecondaryPhysics_20261013_main_complete -->


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery5 role / mesh3 / FT_Trail.G / RGBA ShaderLUT? ?? Heal ??? ????. ?? Heal?Action receipt? ??, runtime1/DEV1/asset13 ?? ??, ? runtime class/tag/manager0. Main build/saved/actual Heal?PlayerAttackCollision2 ?? ?11 effect/alpha ?? ?? ??, ?? ?? ??0. ?? cooked graph ???? ?? native ???/TEMP ??? ?? ???? ????. ??: Art PLAYER_HEAL_VFX_SOURCE_20261013.md / Engineering PLAYER_HEAL_VFX_RUNTIME_20261013.md; evidence Metadata/HealVFX_20261013/FinalVerification.json, ??0.

## 2026-10-13 — 플레이어 피격 추가 불꽃 제거 완료

사용자 요청을 Main에 적용했다. Player Definition.HitReactions.ImpactEffect의 공통 burst 참조만 None으로 해제했다. ASC/Character/Ability runtime 수정0, 기존 Parry DEV 기대값1줄/asset1이다. 피격의 HP/ST·모션·짧은 제어 제한과 공격 적중/패링 공유 PS·GA는 보존했다. Build01 및 fresh Main Native02의17사례/실제피격5 추가효과0이 Success/Exit0이다. 정본은 COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 절과 Metadata/PlayerReceivedHitVFXRemoval_20261013/FinalVerification.json이다. 사용자 editor 제어0이며 이미 로드된 세션에서 구효과가 남으면 Player Definition Reload가 필요하다.

<!-- PlayerReceivedHitVFXRemoval_20261013_complete -->

## 2026-10-13 — Notion 누적 개발보고·템플릿 갱신 완료

사용자 요청의 김민재[언리얼11기] Notion에 현재 작업 기록을 직접 작성했다. 활성 보고 범위 2026-09-08~2026-10-13의 누락 일일21개를 생성하고 기존 일일12개를 날짜별 근거로 보완했다. 현재 일일36개/주간6개이며 날짜 공백·중복0이다. 근거 미확인11일은 작업을 추정하지 않고 미확인으로 남겼다. 주간2개 신규/기존4개 보완, 프로젝트4개·세부업무7개에 목표/KPI·실행·성과·개선점/후속·레퍼런스와 보고 관계를 채웠다. 기존 본문·child DB·보관함은 유지하고 빈 안내문만 실제 내용으로 교체했다.

ASC의 선택 Spec/held/입력·Guard/Dodge hit 중재, Action/ComboAction/Ability·Notify/Event/Tag/Effect, 실제 공격 HP/ST·피격/사망/소진/Brutal/UI, Root/FPS/넉백·보조 물리·Heal의 완료 범위와 검증 근거를 구분해 기록했다. GiantVFX 추가 Main 최종검증, audio binding37 Main 적용/검증, 패링 참고 광막 및 방패병 모션 식별은 완료로 표시하지 않았다. Source의 GameplayCue 전면 이관 완료도 주장하지 않았다.

검증은 Notion53페이지 재조회·필수항목·날짜/중복·기존 본문 보존, 신규 이미지4종의 실제 file-block 결속, local reference41개 존재 확인이다. 기존 미지원 bookmark1개는 변경하지 않고 보존했다. 이 보고 작업에서 게임 C++/Content/Config 변경·새 build/PIE·사용자/다른 작업 editor 제어0이다. 사용한 runtime/화면 증거는 기존 완료 보고다.

대상: https://app.notion.com/p/d6dec99d2c5482c9814081799cabadcc
현재 주간: https://app.notion.com/p/3f8ec99d2c54819e92aeffcad36b4b57?pvs=204
정본: Metadata/NotionProgress_20261013/FinalVerification.json 및 ResumeState.json(status=complete/remaining0); 초기 본문 보존본은 NotionBefore.json. 후속 갱신은 Router→해당 domain 완료/evidence→Notion 현재 rows/content를 먼저 읽고 기존 날짜를 append한다. 오래된 pending/gameplay 완료를 다시 적용하거나 매번 새 build/전체 자산 조사를 실행하지 않는다.

<!-- NotionProgress_20261013_report_backfill_complete -->


## 2026-10-13T13:11:51.008812+09:00 — GiantVFX Main 실제 반영·시각 잔여 분리

GiantVFX ARCH-98 runtime/asset 선택 반영196 및 새 Main build/saved/실제155·GAS8/충돌 기술 검사는 통과했다. 시각 Armageddon 흰 판은 남아 전체 완료 상태가 아니다. 최신 PlayerSlash·Heal·Parry·SFX의 Main 변경을 보존하며 실제 소유자 확인부터 재개한다. exact SHA/실패/후속 전달은 Metadata/GiantVFX_20261013 및 해당 continuity에 기록했다.


## 2026-10-13T13:18:40.096195+09:00 — PlayerSlashAlignment Main 완료

OverFury 추가 Slash17쌍 제거/원래 VFX 유지, 나머지33쌍의 실제 무기 tip·sweep·effective size 보정 완료. 기존 Action receipt와 notify 설정만 확장했다. shared KZ_Slash/mesh/Player Definition SHA 보존 및 original1359×37/clocks/GUID fresh Main 확인. Main build/full presentation·GPU·공중 Spin/native collision16(7/19) 증거는 Metadata/PlayerSlashAlignment_20261013/FinalVerification.json. 병행 SFX/Parry/Giant 변경을 되돌리지 않았다.

별도 Parry sampler mismatch2 materials가 collision editor driver에 기록됐다. native 판정 Success와 해당 shader failed를 분리하며 Parry 담당 continuity로 인계할 근거를 남겼다. 이번 Slash 요청의 필수 잔여0이다.

<!-- PlayerSlashAlignment_20261013_complete -->

## 2026-10-13 — 패링 사진 후속 구현 반영 / 외관 일치 검증 잔여

Reference 폴더17+Guard GA1 및 기존 runtime2/DEV1에 패링 광막·별도 굴절·finite camera shake/FOV를 반영했다. 최신 Native14(17상황/camera/FOV/만료)/Shader02(parent6/MI9) passed, CurrentVerification.json에 현재 SHA와 보존/한계를 기록했다. 실제 밝은 DevMap에서 broad violet halo의 사진 일치는 아직 미확정이고 HeinMach 비교가 남았다. 원작 stripped shader/임시 CPU·색·alpha adapter를 구분하며 완전 동일/완료로 기록하지 않는다. 자세한 도메인 정본과 continuity의 최신 패링 절을 따른다.


## 2026-10-13T14:14:46+09:00 — ARCH-89 current humanoid·Player SFX Main 완료

실행 상태/승인은 기존 ASC/Ability/Task·attack hit group/Guard/Dodge가 소유하고 표현은 기존 PlayAudio Notify를 재사용한다. runtime Source3에 optional VolumeMultiplier(default1), finite owner-tail(defaultfalse)와 EndSound 동일 정책만 확장했다. 해당5family authored Notify만 finite tail을 보존하며 scope 밖 default/giant data는 이전 계약을 유지한다. Body impact는 수신자 Definition, 무기 impact/Guard는 현재 attack window, 회피 성공은 기존 TryAvoidHit once-per-execution이 소유한다. 같은 성공 SFX를 Suc pose에서 또 재생하지 않는다. 새 runtime class/file/component/manager/tick0이다.

기존 DEV Audio Editor에 protected Python array 대신 audio class2-only clear/no-save command, Audio PIE에 sample-plan/actual cue coverage/owner destroy tail, Dodge QA에 실제 authored SuccessSound reflection만 추가했다. build01–04 성공, 현재 Main final saved1682/527/174/8/238cue, full fresh pose/root/curve/FPS/nonaudio notify/GUID 보존 및 실제78 mixer·메인 melee/Guard/Parry17/Dodge11이 passed다. Source/자산/검증 hash·실패/버전은 Metadata/HumanoidSFX_20261013/FinalVerification.json 정본이다. 실제 핵심 root/FPS/physics/VictimFront·Parry/Slash/피격 VFX 제거 변경을 유지했고 기존37prepared bytes를 덮어쓰지 않았다.

유한음은 owner destroy/몬타주 취소 후 자연 drain, loops/명시 source stop만 fade하며 새 shared mutable notify state나 MainAnimInstance member/timer를 만들지 않는다. source 수치/계산과 명시 TEMP .85/.9/1/.08s 및 측정 기반 parry cue.5·미직렬화72callback first-pose adapter를 구분한다. 원작 DSP/sample/frame 전체 동일·Shipping·전 장치 청취는 별도 검증 범위다. 필수 잔여0이며 사용자 editor·foreign process 제어0, 현재 완료를 이전 pending37/locked/prepared 기록보다 우선한다.

<!-- HumanoidSFX_20261013_MainComplete -->


## 2026-10-13T14:19:12.378913+09:00 — GiantVFX/PlayerSlash Main 재개 완료 기준

GiantVFX ARCH-98 재개 작업의 현재 구현/검수를 완료했다. Main198 distinct target(Source8/changedasset86/newasset104)의 SHA를 최종 전달 및 승인된 PlayerSlash source receipt에 맞춰 확인했다. MainSavedSnowDecal01의 original84/raw/root/FPS/event/원래 object gameplay, allLOD null0, MainSnowDecalFinal01 연속23/69실제화면, MainArmageddonGASFinal01 실제grant·perception·Armageddon·cancel cleanup이 통과했다. 현재 실제 모듈 SHA7d57bd17…9462592이며 각 이전 실행은 별도 실제 DLL/SHA로 결속한다. no private DLL/Config/Map 전달이며 이번 재개 gameSource 수정0이다. 흰 판은 Armageddon_Start가 남긴 단일 deferred decal였고 파티클/LOD 원인 가설은 제어 실험으로 철회했다. 전용 parent/MI2와 기존 notify DecalMaterial 한 필드만 후속 적용했다. 모든 agent BP/session 제거, 사용자 baseline8/활성5 보존. 최신 PlayerSlash/Heal/Parry/SFX/physics의 현재 Main을 보존했다. 정확 정본은 Metadata/GiantVFX_20261013/FinalVerification.json 및 ResumeState.json(status=complete_current_implementation_and_review/remaining0). 과거 finalize_giant_vfx의 old-source 가정, full author/delivery/root/FPS/import/old DLL 복사는 반복하지 않는다. 원작 cooked shader/pixel 완전 일치와 Shipping/stress/모든 프레임 검증은 완료로 표현하지 않는다.

## 2026-10-13 — WeakAttack01 Slash 후속 Main 완료

첫 약공격 추가 Slash의 추적 손을 실제 내려베는 Weapon_R로 수정하고 원래/추가 첫 타격4 객체에 TEMP 전방35cm·XY1.15배를 적용했다. 실행1/Notify 설명1/기존 DEV1/asset1이며 새 runtime 구조0. Main build/fresh saved/actual18+Brutal4·GPU70/actor yaw90 성공, 다른 효과/clock/GUID/audio/피해/Physics 및 OverFury 상태 보존. 정확 상태·한계·후속은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json과 ResumeState.json, 해당 도메인 표현 정본 마지막 절이다. 이전 mirror 후보/stale private Source/DLL 전달을 반복하지 않는다.

## 2026-10-13 — Apes/Yetuga 비중단 일반 피격 Main 완료

원본 반응 메타데이터를 확인하고 두 거인의 일반 피격을 독립 additive Slot 표현으로 분리했다. 기존 피해 GE·공격 Ability·AI는 유지하며 ST0/HP0은 기존 소진·사망 경로가 우선한다. Main 에셋 22개, Source 6개 및 Main-object DLL 반영 후 fresh Main PIE 25/25 통과, 원본 full-pose 16개 보존을 확인했다. 원작 특수 경직·부위 그로기 조건의 확인/미확인 범위는 `GIANT_NONINTERRUPTING_HIT_20261013.md`; 정확한 hash·검증은 `Metadata/GiantHitOverlay_20261013/FinalVerification.json`을 따른다.

## 2026-10-14 — Apes/Yetuga 부위 파괴·특수 반응 Main 반영

일반 비중단 피격 및 원작 5/8초 Exhaustion을 유지하며, Apes DempseyRoll Just Guard 분기와 Yetuga ChargeTackle 비보행성 벽 충돌 Stun 경로를 확인·보완했다. 원작 Group1 약점 위치/내구도를 두 종 Definition에 연결하고 기존 HitReaction Ability로 1회 PartGroggy를 실행한다. 원작 미확인 피해 환산 `×20`과 box half extent `32 cm`는 편집 가능한 임시 adapter이며 `SecondDurability` native 조건은 미구현/미확인이다. Main 빌드 성공, fresh RHI PartGroggy 두 종과 기존 GiantHit 25/25 통과. 근거·파일·검증 한계는 `GIANT_NONINTERRUPTING_HIT_20261013.md`의 2026-10-14 절과 `Metadata/GiantReaction_20261014/MainDelivery.json`, `MainPIEFinal`, `MainGiantHit01`을 따른다.

## 2026-10-14 — Group1 임시 박스 크기 설정화 후 최종 상태

32 cm 임시 half extent를 `PartGroup1BaseHalfExtentCm` 편집 설정으로 옮기고 Main 재빌드/RHI 두 종 테스트를 다시 통과했다. 최종 DLL SHA·13/13 소유 파일 hash·기존 일반 피격 25/25·저장 에셋 감사는 `Metadata/GiantReaction_20261014/FinalVerificationTuning.json`이 정본이다. 실제 Just Guard/벽 충돌 물리 트리거와 Player 조작 입력부터 약점 파괴까지는 이번 자동화 테스트에 포함되지 않았으며, 원본 환산/SecondDurability도 미확인이다.

## 2026-10-14 — Combat HUD 표시 크기·선명도 개선

원본 고해상도 UI 텍스처와 저장된 원작 위젯 크기는 보존하고 프로젝트 `DefaultEngine.ini`의 DPI 곡선만 조정했다. 900px 화면의 표시 배율은 기본 약 .833에서 임시 1.15로 올라가며, 1080px은 임시 1.3이다. 별도 Main D3D12 PIE의 변경 전후 `Khazan.CombatUI.PIE`가 모두 Success/material fallback0이고 Boss HP/B 실제 픽셀 영역이 확대된 것을 화면으로 확인했다. 적용 범위, 임시값 출처, 전후 캡처와 개별 해상도 검증 한계는 `COMBAT_UI_RUNTIME_20261011.md`의 같은 날짜 절과 `Metadata/UIQuality_20261014/{BaselinePIE02,ImprovedPIE01}`을 따른다.

## 2026-10-14 — 플레이어 적중음 최종 Main 반영

잠금이 해제된 Main Combo DataAsset에 검증된 오디오 필드만 적용한 후 `KZComboActionAbility.cpp`의 exact-cue 임시 차단 분기를 제거했다. stock `KhazanEditor Win64 Development` 빌드 성공, fresh 저장 에셋 readback 26 node/60창·비오디오 동일, 실제 PlayerAttackCollision 오디오 PIE 성공(body hit 관측/common 중복음 0/clipping 0)이다. D3D12 브루탈 치명 사망 12건과 일반·중단 사망 12건도 각각 성공했다. 병행 GiantCamera 작업이 뒤이어 Main 표준 DLL을 재빌드했으며 그 빌드도 성공했다. 경로·현재 SHA·각 검증의 범위는 `Metadata/MainIntegration_20261014/FinalVerification.json`; 진행 중인 별도 GiantGrabWarning/GiantCamera의 완료 판정은 여기 포함하지 않는다.

## 2026-10-15 — 현재 Main 통합 상태 재검증

Main Combo 및 `KZComboActionAbility.cpp`는 이전 최종 SHA와 동일하다. 이후 완료된 GiantCamera/GrabWarning과 PlayerSlashOuter 결과를 확인하고 현재 표준 DLL SHA `6f1c6bfe…`를 실제 새 프로세스에서 로드했다. stock 빌드는 Target up to date/Succeeded, 최종 영수증 대상 57개 파일 SHA 불일치 0, 저장 계약 재검사 4종 모두 성공이다. 게임 Source 수정·에셋 저장·새 RHI PIE 0이며 검토한 범위에서 미반영 준비본은 없다. 상세 범위는 `Metadata/MainIntegration_20261015/FinalVerification.json`; 실제 Guard held 잡기 통합 사례와 원작 native/pixel 동일성 같은 기존 추가 검증 한계는 별개다.


## 2026-10-15 — Apes·Yetuga 잡기 경고 Main 반영 유지 확인

현재 Main `KZAnimNotify_CombatEffect.cpp/.h`의 경고 camera-facing 분기가 존재하며, 새 UE 에디터 프로세스에서 7개 애니메이션의 VFX/audio state 설정을 재확인했다. 두 종의 7개 capture node/12개 판정창은 모두 bBeginsCapture=true·bBlockable=false이며 기존 Combo 적중 분기가 일반 가드/패링 호출을 건너뛴다. 병행 GiantCamera의 중복 대상 4개 clip/4개 camera event도 누락 0이다. 검사 asset save 0·전후 SHA 동일, 이전 최종 7개 애니메이션 SHA 일치, 미반영 중단분 0이다. 오늘 근거는 `Metadata/GiantGrabWarning_20261015/SavedReadback.json`과 `MainSavedEditor.log`(exit 0). 이전 Main 빌드와 실제 D3D12 PIE 근거는 `Metadata/GiantGrabWarning_20261014/Build02.log`, `PIE/RuntimeReport.json`이며 오늘 다시 빌드/PIE한 결과와 구분한다. 직접 Guard-held 잡기 통합 사례와 원작 shader/DSP 전체 일치는 기존 미검증 범위를 유지한다.


## 2026-10-15 — ARCH-99 카메라·패링 Main 반영 재확인

현재 Main의 카메라 modifier/MonsterVisual notify/Guard 성공 실행 경로와 저장 애니메이션48개·카메라 이벤트86개·Guard Niagara binding이 유지돼 있다. 48개 package와 Guard는 2026-10-14 최종 완료본 SHA와 일치했다. 이후 다른 작업으로 바뀐 표준 DLL을 실제 로드해 새 readback48/86 및 D3D12 Khazan.GiantCamera.PIE 대표4개, Khazan.Parry.PIE17개를 다시 통과했다. MainBuild는 Succeeded/Target is up to date, 실제 모듈 SHA는 6f1c6bfe41382cb6f6308130e403ce568b6b76f560e2b154707f4f9810b2d25e다.

메인 반영 대기0, 이번 runtime Source/asset 수정0·테스트 package 저장0이다. 재확인 정본은 Metadata/GiantCamera_20261015/FinalVerification.json과 MainSavedReadback.json/MainPIE_RHI/Driver.json이다. 원본 camera modifier 실행 코드 및 대응되지 않은 source package2의 원작 완전 일치 한계는 이전 기록대로 남으며 메인 미반영으로 해석하지 않는다.


## 2026-10-15 — CombatFeel 메인 구현·검증 완료

패링 사용자 지정 Niagara/Brutal burst, 모든 현행 선형 camera force/return, Apes/Yetuga 원거리 추적과 장거리 capture, Yetuga 원거리 Armageddon TEMP policy, groggy runtime loop 및 giant 콤보/6종 lethal death inertia를 메인 기존 소유자에 적용했다. unique BP3개/새 runtime 파일·class0. PartGroggy root data는 정상이며16 clip audit 동일 및 실제 캡슐 이동 검증을 통과했다. Build11/12, 표준 메인 UnrealEditor-Khazan.dll(SHA 73fed22564f0657a1d1bc7b2c56d8c6637b7f2279974645e13d1c354313d40cd)의 FinalMain01 3 suite Success; 이전 RHI Parry17/Brutal12와 camera/root/groggy suite는 각 module identity를 유지해 별도로 기록한다. 정본: `Metadata/CombatFeel_20261015/FinalVerification.json` 및 PARRY_IMPLEMENTATION/APES_YETUGA_FALL_IMPLEMENTATION/COMBAT_PRESENTATION_FOLLOWUP 같은 날짜 최신 절. 필수 잔여0.



## 2026-10-15 — HeinMach 승인 피격 VFX 후속 완료

ARCH-88/95의 기존 PlayHitReaction 발생점만 scaled capsule 표면으로 보완하고 Definition7에 exact Brutal Trail_Sub를 연결했다. 새 runtime class/file/상태 없음. 기존 DEV QA 파일의 실제 game viewport capture command로 잘못된 Shot viewport 촬영을 해결했다. MainCaptureBuild02 성공, MainHitsHein01의 실제 Parry/MonsterRepair/PlayerAttackCollision3 suite 성공이며 각 모듈 hash/QA 추가 시점은 구분했다. Main105 package·saved readback·native VFX321×2맵과 왜곡 반복 검증 완료. 넓은 기존 CombatEffect montage suite의 이번 부분 실행은 전체 성공으로 계산하지 않는다. 상세/정확한 재개는 COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 절 및 Metadata/HeinMachColourVFX_20261015/FinalVerification.json, ResumeState03.json이다.

<!-- HeinMachColourVFX_20261015_complete -->


## 2026-10-15 ? GiantRootUsage ?? ??4? Main ?? ??

??170?/510?? ??? ? giant PartGroggy Loop/End4?? first-frame locked root?522.148cm ???? ???? RootMotionRootLock=REF_POSE? ????. EnableRootMotion/ForceRootLock? ?? ??? ???? ??? Additive8?? ?? ?? ??? ????. Main4package/?? C++?BP??/???0, complete model/notify170 ? ?????166 ??, fresh pose170/510?GiantReaction2?GiantFall13??? D3D12 ?? weak-part2/6?? Success?. ? ?? CombatFeel root ?? ? Loop/End pose origin ??? ??? ? ??? ????. ?? ??0, ?? ?? `Metadata/GiantRootUsage_20261015/FinalVerification.json` ? MONSTER_ATTACK_ROOT_MOTION_20261007.md ?? ?.


## 2026-10-15 — Notion 누적 구현·검증·일감·PROTO 갱신 완료

사용자 요청으로 기존 김민재[언리얼11기] Notion(https://app.notion.com/p/d6dec99d2c5482c9814081799cabadcc)의 실제 schema/Project·Task 템플릿을 확인한 뒤, 최신 Main 적용/빌드/saved/native PIE/원작 일치의 범위를 분리해 작성했다. 통합 PROTO(https://app.notion.com/p/3faec99d2c548131b97bd0bbd32b8b9f)와 후속 PROTO(https://app.notion.com/p/3faec99d2c54813ab44bf825823f1c50), 신규 범위별 완료19/후속8일감 및10/14·15일일보고2개를 추가했다. 기존4프로젝트/7상위일감/10/13일일/현재10월3주차/메인에는 날짜별 최신 절을 추가했고 기존 본문은 삭제하지 않았다.

현재 DB는 프로젝트6/일감34/보고44(기존42+신규2)다. 신규31페이지·기존14페이지, 총45페이지 readback과27 Task의 목표/실행/성과/인사이트/레퍼런스·상태/완료일/Project,27개 내장 report self filter를 확인했다.10/14·15 일일보고는 각1개/중복0, 이전본문13개 전체 보존·메인DB6개 보존이며 신규PROTO 목차/고유사진12/근거JSON1이 실제 저장됐다. 과거 사운드37준비본/GiantVFX대기/패링분석 단계는 이후 완료 영수증으로 대체됨을 추가했다.

Source/자원·제어 수명·StateTree/Ability·카메라·거인 약점/그로기/root/Brutal·SFX·UI의 실제 결과와 TEMP/미확인값을 상세 일감에 기록했다. 실제 움직이는 대상/Guard-held/약점파괴·벽충돌·SecondDurability, 두 레벨 연속 플레이, 조건 의존46 VFX, 원작 shader/DSP 비교, Shipping 성능 및 Turn/SprintPivot은 후속8개이며 임의 담당/기한/전체 게임 완성률을 만들지 않았다.

새 Main HeinMach 환경3장은 소유 프로세스에서 read-only capture/asset save0/dirty0/정상종료다. 이번 문서화에서 게임C++/BP/에셋/Config 변경·새 build·전투 자동화 재실행·다른 editor 제어0이다. 현재 표준 DLL 파일SHA73fed22564f0657a1d1bc7b2c56d8c6637b7f2279974645e13d1c354313d40cd를 확인했으나 모든 과거 suite를 이 module로 다시 실행했다고 소급하지 않는다.

정본은 Metadata/NotionProgress_20261015/FinalVerification.json과ResumeState.json(status=complete/remaining_documentation_actions=[])이다. NotionBefore/Additional/After,CreatedPages,TaskSpecs,EvidenceIndex,ScreenshotManifest/Files,ReferenceAudit와새CaptureHeinMain01을재사용한다. 후속은Router→새도메인완료영수증→현재Notion rows/content를먼저읽고날짜별append한다. 이미끝난import/author/gameplay수정·옛DLL전달을반복하지않는다.

<!-- NotionProgress_20261015_complete -->


## 2026-10-15 — HeinMach GateCube → Yetuga 전장 포탈 Main 완료

배치 Actor KZBossPortal(runtime2/DEV1)로 실제 capsule 진입·암전·같은 월드 이동·복원 및 원인별 입력/ASC cleanup을 구현했다. Main suffix Build07/새 Main D3D12 RHI06 실제 walking suite/fresh Readback04가 통과했다. 기존 combat Source/Config 수정0이며 실제 목적지는 Boss_Start 통로가 아닌 Yetuga_TargetPoint 기준 전장 내부다. 조절 위치·TEMP·검증 한계는 HEINMACH_YETUGA_PORTAL_20261015.md, 정확 SHA/범위는 Metadata/HeinMachPortal_20261015/FinalVerification.json을 따른다. 필수 잔여0이다.

<!-- HeinMachPortal_20261015_complete -->

## 2026-10-15 — 컨트롤러 진동 Main 소스 반영 / 사용자 요청으로 검증 생략

WeakAttack의 약한60ms 진동, StrongAttack·Charge·Spinning·OverFury·패링의 강한100ms 진동 및 Yetuga/Apes/Elite의 준비/발걸음·공격/충격 진동을 기존 ComboAction/Guard/MonsterVisual/PlayAudio 경로에 연결했다. 기존 PlayerController가 UE finite Dynamic Force Feedback과 TEMP 조정값을 소유하며 거리 감쇠/로컬 장치 출력·HitGroup별1회를 적용한다. intensity/duration은 약공격.22/.06s, 강공격·패링.90/.10s, 몬스터약.14/.045s·강.65/.12s, 거리400~3000cm이며 원작 직접값/실기 확인값이 아니다.

실제 수정은 기존runtime7파일·신규runtime/class/asset0이다. MonsterPatternAbility 자체의 판단 코드는 변경하지 않고 상속된 ComboAction 경로로 처리한다. 사용자가 검증 생략을 명시했으므로 build/PIE/test/정적검사/실기 확인0이며 현재 DLL/사용자 editor는 제어하지 않았다. **소스 반영만 완료, 바이너리 재빌드·실기 동작 미확인**으로 구분한다. 상세 계약·튜닝·파일 목록은 COMBAT_PRESENTATION_FOLLOWUP_20261011.md의 같은 날짜 진동 절 및 Metadata/ControllerRumble_20261015/Implementation.json이다.

## 2026-10-15 — 초록색 공격 콜라이더 디버그 표시 제거 Main 반영

사용자 요청으로 공통 ComboAction 충돌 조회의 초록색 Box/Cylinder/Sphere DrawDebug 분기와 include만 제거했다. 상속된 MonsterPatternAbility를 포함해 Player/Monster에 공통 적용되며 실제 충돌 조회·피해·판정 데이터·진동 코드는 그대로다. production draw 참조 잔여 0, 백업과 현재 파일의 차이는 10줄 삭제뿐이다. Main 빌드는 다른 작업의 mutex 대기 후 Succeeded/Target up to date로 완료했다. 새 PIE/장치 검증은 실행하지 않았고 진동 동작의 검증으로 확대하지 않는다. 상세는 PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md 최신 절과 `Metadata/AttackCollisionDebugRemoval_20261015/FinalVerification.json`이다.


## 2026-10-15 — HeinMach/Spinning asset-only 후속 완료

기존 ARCH-83/95 CombatEffect 데이터만 사용해 Main3 asset을 반영했다. 신규 gameplay Source/Config/DLL/build0, 기존176 효과·clock/GUID·공격/입력/오디오 보존이다. MainSaved01과 실제 MainDevSpin01의2 suite Success, HeinMach 자연 Spin/cleanup·충돌 확인, 별도 rear-Brutal fixture 실패, 포탈 저장 계약 보존 및 actual modulea8df6850...는 Metadata/HeinMachLookSpin_20261015/FinalVerification.json에 있다. 다른 세션의 진동 장치 검증/포탈 재구현을 이번 범위에 포함하지 않는다. 외관·TEMP는 Art 정본, 필수 잔여0이다.

<!-- HeinMachLookSpin_20261015_complete -->

## 2026-10-15 — Yetuga 전장 BGM Main 구현·빌드 완료

기존 AKZBossPortal의 전장 이동 성공 시 원작 Yetuga music cue를 World 2D로 한 번 시작한다. 사용자 최신 지시대로 사망/처치/전장 이탈 시 Stop/FadeOut하지 않고 원본 loop를 계속 재생한다. 재진입 중복은 transient playback receipt로 억제하며 신규 runtime file/class/manager/tick0이다. Main runtime2 소스·음악4asset 저장 및 stock DLL build Succeeded; map save0, PIE/전투 청취0이다. 상세는 HEINMACH_YETUGA_PORTAL_20261015.md 최신 절 / Art YETUGA_BGM_SOURCE_20261015.md / Metadata/YetugaBGM_20261015/Implementation.json. 사용자의 현재 세션이 이전 DLL을 이미 로드했다면 정상 재시작 후 새 DLL을 사용한다.

## 2026-10-15 — HeinMach 전용 Epic Shipping 릴리즈 패키징 완료

최신 메인 소스/자산으로 Windows x64 Shipping을 만들었다. 사용자 최신 범위대로 게임 레벨은 HeinMach 하나이며 Epic(시네마틱 바로 아래)11그룹3/렌더링100%를 실제 최종 pak에서 확인했다. Yetuga BGM4asset 포함, VC prerequisite·Pak/IoStore·실행안내 포함, PDB 제외다. GameDefaultMap/GameInstance redirect를 직접 경로로 갱신하고 기존 GameFeatureData 선언용 GameFeatures를 활성화했으며 Shipping-only compile 오류2개를 기존 cpp2개에서 작게 보정했다. 새 runtime class/file0, 맵/Content 원본 저장0이다.

배포: C:/Users/user/Desktop/Khazan_Release_20261015/Windows 전체 폴더, 실행 Khazan.exe. 41파일/2,410,104,666bytes(약2.25GiB). Shipping build Succeeded와 cook8,590/0error·6warning/UATexit0, 최종 container map·config·바이너리 SHA 확인, offscreen 시작90.07s 생존/새 crash0을 기록했다. 실제 전투·외관/FPS·진동·음악 청취는 이번 패키징에서 검증하지 않았다. 최종 증거는 Metadata/Release_20261015/FinalVerification.json이며 필수 잔여0이다. 이전 두 맵 패키징 진행 중 기록은 최신 HeinMach 단일 완료 기록으로 대체한다.


## 2026-10-15 — 진동 2배·HP0/Yetuga 잡기 LockOn·HeinMach 재패키징 완료

사용자 직접 요청을 기존 runtime5/Config1/DEV2의 작은 변경으로 완료했다. 신규 runtime 파일/class0, BP/애니메이션/맵 저장0이다. 진동은 기존 엔진 config `/Script/Engine.PlayerController.ForceFeedbackScale=2.0`을 사용하며 생성자 변경은 남기지 않았다. 배율2는 사용자 지정, 최종0..1 상한은 엔진 장치 출력 범위다. 기존 pulse duration/몬스터 거리 감쇠는 그대로다.

LockOn은 대상 ASC HP<=0 callback에서 즉시 해제하고 살아 있는 대상만 선택/유지한다. Yetuga의 승인된 잡기 성공 시 피해 Player의 잠금을 풀고, 기존 잡기 cleanup 후 양쪽 생존·동일 Controller/Pawn이면 동일 Yetuga에 자동 재잠금한다. 잡기 중 신규 잠금, 죽은 target 및 소멸/소유권 변경 후 재잠금은 거절한다. ASC/Ability 상태와 이동 제약의 기존 작성자를 유지하며 delegate/constraint/controller receipt는 각 소유자가 정리한다.

EditorBuild01~03 Succeeded, 실제 RHI CombatUI.PIE 및 GiantFall.PIE(14패턴/기존 낙하 포함) Success. UI 검증 후 변경은 DEV death assertion뿐이며 제품 runtime/config는 동일하다. 초기 lethal fixture가 사망 montage까지 포함한 HasRootMotionSources 검사에서 실패한 기록은 보존하고 자기 OriginalPatternMoveTo 제거 검사로 보정해 재통과했다. 정확한 각 DLL/Source hash와 범위는 `Metadata/LockOnRumble_20261015/FinalVerification.json` 및 Changes.patch/ChangedFiles.json/PIE01/PIE02_Giant를 따른다.

Package06_LockOnRumble의 새 Shipping compile51.47초, cook8590/91.98초/0error·6warning, UATexit0(276.15초)으로 완료했다. 최종 container의 게임 map은 HeinMach 하나, 설정은 진동2/Epic11그룹3/해상도100%, packaged Shipping exe는 현재 build SHA와 동일하다. 배포 폴더 `C:/Users/user/Desktop/Khazan_Release_20261015/Windows`, 실행 `Khazan.exe`, 전체41파일/2,410,106,779bytes다. VC x64 prerequisite와 실행안내 포함, 배포는 Windows 폴더 전체 단위다. 기존 map SHA7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728 보존.

소유 Shipping 프로세스의 별도 UserDir/offscreen/nosound 90초 생존과 새 crash0을 확인한 뒤 해당 프로세스만 종료했다. 자연 종료/전체 패키지 전투·FPS·오디오·실물 패드 체감은 검증한 것으로 확대하지 않는다. 기존6 cook 경고는 이전 release와 같은 Lumen priority/장식 PortalPlane convex/GameplayCue 검색 경로다. 필수 잔여0이며 이후 재개는 위 FinalVerification → 새 요청 범위의 현재 Source/Config부터 한다. 이전 배포 완료본을 현재 바이너리로 오인하거나 과거 package/asset/DLL 전체를 복원하지 않는다.

<!-- LockOnRumble_20261015_complete -->


## 2026-10-16 — 최신 HeinMach 정리본 Epic Shipping 패키징 완료

사용자 요청대로 현재 Main의 HeinMach 단일 레벨을 Windows x64 Shipping/Epic으로 새 패키징했다. 배포 폴더는 C:/Users/user/Desktop/Khazan_Release_20261016/Windows, 실행은 Khazan.exe다. 기존20261015 배포본은 유지했다. 실제 container에서 game map1, Epic11그룹3/해상도100%, Yetuga 음악4asset/진동배율2를 확인했다. Main map SHA1d224b14...의 정리본이며 cooked map14,577,381→9,527,965bytes 및 chunk hash 변경으로 이전 맵 재사용이 아님을 확인했다.

Shipping target up to date/Succeeded2.68초, cook7619/103.02초/0error·기존6warning, UATexit0/239.366초다. 전체41파일2,111,968,044bytes(약2.11GB), VC prerequisite·실행안내 포함/PDB0. 새 패키지의 소유 Shipping 프로세스는 별도 UserDir/offscreen/nosound에서90.234초 생존·crash0 후 해당 프로세스만 종료했다. 실제 전투·외관/FPS·패드·음악 청취까지 검증했다고 확대하지 않는다.

게임 Source/Config/자산 변경0이며 전체 입력 SHA 유지다. 기존 packaging runner에 출력/task 환경 변수만 추가해 재사용했다. 정본 Metadata/Release_20261016/FinalVerification.json·PackageReadback.json·ReleaseFiles.json·Smoke01/Result.json. 필수 잔여0.


## 2026-10-16 — 현재 프로젝트 Git main 분할 Push 완료

사용자 요청의 프로젝트 스냅샷을15개 묶음으로 순차 commit/push했고, 각 묶음의 원격 main SHA를 검증했다. 시작은7d7cc2db2ad66a9a316169e9736eb979bb57a731, 최종 스냅샷은0305b6a9a138c7875578042e52b231302983ef89다. 2026-10-16 17:50 KST 검사에서 local HEAD와 ls-remote의 refs/heads/main이 동일했다. 이 완료 문서 기록은 별도 후속 커밋으로 전송한다.

초기 선택30,553개와 base→최종 commit의 변경 경로30,553개가 정확히 일치했다. 선택 누락0, 계획 외 commit0, 잔여 tracked/staged 변경0이다. Source/Config/Content/Docs/Scripts/uproject와 텍스트 Metadata가 포함되며, 첨부한 Source/Khazan/AI/KZMonsterAIController.cpp도 반영됐다. 선택 파일의 초기 원시 크기는9,846,030,742bytes이며 실제 네트워크 전송량으로 해석하지 않는다. 기존 이력·Git LFS SK*.uasset 규칙을 유지하고 강제 push/기존 commit 재작성은 하지 않았다.

제외 목록41,983개/초기33,045,614,220bytes는 검사 시 모두 미추적 상태로 로컬에 남아 있고, 제외 파일이 새로 추적된 사례나 추가 미분류 잔여는0이다. 대상은 과거 binary 에셋 백업, 검사 이미지/영상/오디오, 로그, 브라우저 프로필과 신규 생성 캐시다. 텍스트 Metadata의 원본 근거·보고서·과거 소스/충돌 진단 기록은 보존했다. 기존 ignore 설정을 바꾸거나 제외 파일을 삭제하지 않았다. 전체 working tree가 clean하다는 뜻은 아니며, 프로젝트의 선택 업로드 범위가 완료됐다는 뜻이다.

Git 검증: batch1–11의 staged diff check는 성공했다. batch12–15에는 기존 텍스트의 whitespace/EOF 경고가 있어 그대로 보존했다. conflict-marker12개는 Metadata/BeastDodge_20261012/Rebase02·03/Conflicts 아래 과거 충돌 진단2파일뿐이고, 이번 선택의 현행 Source에는 해당 표식이0이다. 검사 결과를 전체 diff-check 성공이나 새 C++ 빌드 성공으로 표현하지 않는다. 이번 작업의 새 gameplay Source/BP/asset 편집0, UE build/BP compile/PIE0이며 문서에 Git 결과만 추가했다.

로컬 상세 증거는 저장소 루트 .git/codex-main-upload-20261016/{inventory,plan,omitted,snapshot-verification}.json, batch-01.json부터 batch-15.json 및 각 push/diff-check 로그다. 모든 batch의 pushed=true를 확인했다. 앞선 진행/재개 절차는 완료 상태로 대체하며 prepare나 기존 batch를 다시 실행하지 않는다. 후속은 새 요청의 현재 Git 변경과 원격 main부터 확인하고, 로컬 보존 자료까지 추가 업로드하는 작업은 별도 범위로 판단한다.

<!-- GitMainSplitPush_20261016_completed -->
