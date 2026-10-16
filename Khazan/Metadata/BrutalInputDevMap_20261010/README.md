# 2026-10-10 — Main 브루탈 B 입력·DevMap 확장

사용자 요청으로 Main 프로젝트에 적용했다. 기존 입력 → Controller → ASC → 부여된 Ability 경로를 재사용하며, 새 runtime 파일·class는 없다.

## 입력 동작

- 패드 **B**(`Gamepad_FaceButton_Right`) → `/Game/Input/IA_BrutalAttack` → `Input.Action.B` → 기존 `UKZBrutalAttackAbility`.
- X는 기존 약공격, Y는 강공격, A는 회피 입력을 유지한다. 이번 요청에 새 키보드 브루탈 키를 추가하지 않았다.
- B의 Started/Completed/Canceled를 기존 Controller의 AbilityInputTagPressed/Released/Canceled로 전달한다. 새 입력 수명·매니저·상태 사본을 만들지 않았다.
- Player Definition의 기존 브루탈 grant만 X→B로 바꿨다. ASC의 기존 로직이 grant의 입력 태그를 비교하므로 ASC/브루탈 구현은 수정하지 않았다.
- 기존 소진·대상 거리·활성화 조건을 충족할 때 실행한다. 접근·피해50·피해자 모션·양쪽 완료 후 생존 스태미나 회복은 기존 동작이다. 회복 조건을 B 변경과 함께 새로 구현한 것은 아니다.

변경한 Source는 `KZGameplayTags.h/cpp`, `KZPlayerController.h/cpp` 네 개다. 저장한 에셋은 InputAction 신규1개, IMC_Default, DA_InputData, Player CharacterDefinition, DevMap의 고유5개다. 입력 외 Definition grant와 기존 입력 행은 전후·fresh reload에서 동일하게 확인했다.

## DevMap

`/Game/Maps/DevMap`의 `Floor` XY scale을 `(8,8)`→`(32,32)`로 바꿨다. 바닥은 약 **80m × 80m → 320m × 320m**, 면적16배다. Z scale8, 위치·높이·메시·충돌 설정을 보존했다. `DevAI_Navigation` XY scale도1→4로 확대해 약312m × 312m를 포함하고 실제 내비게이션을 재생성했다.

이 크기와 아래 XY 좌표는 사용자 요청에 따른 **어시스턴트의 테스트 배치값**이다. 원작 DevMap 크기·배치 메타데이터 값이 아니다. Z는 각 기존 BP의 live capsule half-height를 사용했다.

| 종류 | 수 | 새로 추가한 위치(cm) |
|---|---:|---|
| Swordsman | 7 | 기존 배치 유지 |
| SwordShield(ShieldMan) | 1 | 기존 배치 유지 |
| HeavySwordsman | 1 | 기존 배치 유지 |
| HalberdElite | 1 | 기존 배치 유지 |
| ApesStoneHandElite | 1 | `(5500,-2200,240)`, Yaw180° |
| Yetuga | 1 | `(5500,2200,265)`, Yaw180° |

총12마리이며 인간10마리의 기존 대기·순찰·Talk01/02 배치를 유지했다. 새 두 마리는 `DevMap/Monsters/Beasts` 폴더에 `DevTest_ApesStoneHandElite`, `DevTest_Yetuga`라는 Actor Label로 찾을 수 있다. PlayerStart를 기준으로 월드 +X 방향55m 지점의 좌우다.

Apes/Yetuga는 기존 gameplay BP·Definition·ASC·피격·소진·브루탈 기능을 가진 테스트 캐릭터다. 기존 BP의 AIStateTree는 None이며 이번 배치 작업에서 별도의 자율 전투 패턴을 만들지 않았다. 인간 네 종류는 기존 AI를 사용한다. 애니메이션 클립·재생률·Player 메시0.01 배율은 편집하지 않았다.

## 검증·기록

- [BuildUnique.log](BuildUnique.log): Main `KhazanEditor Win64 Development` 빌드 성공. 기존 실행 중 에디터의 canonical DLL 잠금은 고유 suffix 모듈로 해결했다. 사용자 에디터를 종료하거나 Live Coding하지 않았다.
- [Authoring09.json](Authoring09.json): 고유5개 저장 완료, dirty0, 넓어진 영역의 ±140m 네 지점과 짐승 두 배치 지점에 실제 nav projection 성공. 작업용 설정 복구 완료.
- [FreshSavedVerification02.json](FreshSavedVerification02.json): 별도 새 Main 프로세스에서 실제 선택 DLL 로드·B 입력/Player grant·기존 행 보존·바닥·12마리/6종·저장된 navmesh를 읽기 확인. 28검사, dirty0.
- [FreshPIEVerification02.json](FreshPIEVerification02.json): Python 입력/이동 주입 없이 12마리의 live ASC/Definition/AnimInstance와 종별 HP·Stamina 초기화를 관측했다. 기존 C++ `Khazan.Monster.CombatPolicyPIE`가 인간4종의 발견→End→대치, 유효 타깃 유지, 행동 완료 후 재추적과 공격 완료를 검사했다. 결과와 테스트 종료·byte 불변은 이 receipt를 따른다.
- [SourceChanges.json](SourceChanges.json): 이번 Source4개의 전후 hash. [FinalVerification.json](FinalVerification.json)은 최종 저장 상태·프로세스 종료·현재 모듈 검증을 결속한다.

이번 PIE는 패드 B의 실제 물리 버튼 누름 검사가 아니다. 버튼 연결은 현재 Source 빌드와 새 프로세스의 직렬화된 입력/부여 계약으로 확인했다. 사용자 직접 테스트는 Main 에디터를 새로 열어 DevMap에서 소진된 몬스터 근처에 접근한 뒤 B를 누르면 된다.

실패·중단 기록은 보존했다. 초기 navigation rebuild의 잠금0x20은 `ENavigationBuildLock::AsyncLoadLock`이었다(UE5.8 `NavigationSystem.h` / `NavigationSystem.cpp`). 원인은 자동 갱신 설정 꺼짐이라는 초기 추론과 달랐다. 최종 author는 실제 build/load lock 해제 뒤 bounds update와 rebuild를 요청했다. 초기 Python API/reflection 실패와 저장 전 timeout은 saved0이었다. Author08은 receipt 없이 종료돼 원인을 확정하지 않았으며 종료 후5개 디스크 대상이 원본 hash와 같음을 확인했다.

Author09의 `saved`에는 Slate save 재진입으로 고유5개가 세 번 기록되어 있다. 해당 helper는 save 전 callback을 해제하도록 보완했고, 이미 완료된 authoring을 재실행하지 않았다. 최종 값은 새 프로세스에서 직접 읽어 검증했다. 첫 Verify의 native 검사는 성공했지만 observer가 종료 이벤트 처리 중 PIE를 재시작하여 작업용 PID16396만 종료했다. [VerifyAttempt01Status.json](VerifyAttempt01Status.json)을 보존하고, 완료 이벤트를 먼저 처리하며 PIE 시작을 한 번만 요청하는 별도 새 프로세스로 다시 검사했다. 제품 코드/에셋을 이 관측 helper 문제 때문에 재수정하지 않았다.
