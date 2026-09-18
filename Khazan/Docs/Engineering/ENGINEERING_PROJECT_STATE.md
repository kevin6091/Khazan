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
