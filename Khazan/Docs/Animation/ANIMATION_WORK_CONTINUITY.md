# Animation 작업 연속성

## 2026-09-08 Stop 검증과 SprintStart 안내

- 현재 완료: 실제 InGame Stop 5개/loop/ABP 설정의 표적 읽기, 새 UBT 빌드, PIE C++ 중단점에서 Walk/Run/Sprint Stop 진입 속도/Gait/Foot/요청 확인. 상세는 ANIMATION_LOCOMOTION.md와 Saved/ImportReports/Khazan_InGame_Stop_Verification_20260908.json.
- 현재 미완료: 32초 추가 입력 검사 결과 회수, 전체 ABP 전이/원샷 완료, 모든 발 variant와 시각 품질 검증. 이를 통과로 기록하지 않는다.
- 마지막 실패/중단: 첫 Editor는 잘못된 진단용 anim-node index 조회 과정에서 종료됐다. 새 Editor에서 기본 세 진입 검증 후 viewport 캡처/디버거 통신이 멈췄다. 정확한 두 번째 중단 사유는 미확인이다. 런타임 C++/ABP/시퀀스는 어시스턴트가 수정하지 않았다.
- 재개 전 필수: Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md의 2026-09-08 실행/중단점/callback 정리 절차를 따른다. 추측한 0/1 인덱스로 GetCurrentStateName을 다시 호출하지 않는다. 사용자 에셋 복원/삭제/일괄 저장을 임의 수행하지 않는다.
- 다음 안내: INGAME_LOCOMOTION_STEP_5.md. 저속 전방 SprintStart 자산 준비, AnimInstance의 새 지상 Sprint 요청/진입 데이터, ABP 원샷 진입과 중단을 줄별로 설명했다. 실제 구현은 미적용이며 멈춘 검사 상태 복구와 Start 클립 적합성 검토가 먼저다.

## 2026-09-08 정본 통합 완료와 Turn 설명 재개 기준

- 최신 요청: Turn 작업 전에 현재까지의 공동 구현, 변수/함수 용도, 검증 상태를 정본으로 정리한다. [LOCOMOTION_CURRENT_IMPLEMENTATION.md](LOCOMOTION_CURRENT_IMPLEMENTATION.md)를 추가하고 Router/AGENTS에 선행 읽기 규칙을 연결했다.
- 사용자 결정으로 모든 Start를 제외한다. 앞선 다음 작업 SprintStart 안내는 취소됐다. 다음 구현 주제는 기존 6단계 Turn이다.
- 완료한 것은 현재 소스/저장 리포트 대조와 문서 정리다. 새 Turn 코드/ABP/에셋을 적용하거나 새 빌드/PIE를 수행하지 않았다. 중단된 Turn 설명의 후보 설계는 현재 구현으로 채택하지 않았다.
- 마지막 실측 검증과 미회수 32초 검사/실행 상태 문제는 위 기록 및 Engineering continuity에 남아 있다. 이번 문서 요청에서는 Editor/디버거에 다시 연결하지 않았으므로 정리 완료나 여전히 같은 PID로 중단 중이라고 단정하지 않는다.
- 정확한 재개: Router → 새 정본 → 현재 AnimInstance/Player/LocomotionType의 변경분 확인 → 사용자 요청 범위에서 Turn을 상세 설명한다. 실PIE 검사까지 요청받으면 그때 Engineering continuity의 세션/중단점/callback 정리 절차부터 확인한다. SprintStart나 구형 C++ 상태 재생 방식을 복원하지 않는다.

## 2026-09-08 Walk Turn / Sprint 반전 정책 확인 대기

- 최신 요청은 Walk Turn 두 동작, Sprint 전용 Turn 미사용이다. Run 포함/제외 표현이 충돌해 마지막 제외 문장을 우선하는 것으로 안내했다. 모든 Start 제외는 유지한다.
- 정본 전체와 현재 Stop 요청/Player Sprint 해제 코드를 읽었다. 입력 유지 중 방향 변경은 현재 Stop 요청 원인이 아니며, 입력 해제는 토글 Sprint 요청을 끈다는 것을 확인했다.
- 상세 설계 진행 전 확인할 내용: Sprint의 "Stop모션을 취소"가 Stop 즉시 중단/반대 방향 Sprint인지, Stop 제동 동작을 거친 Sprint 재개인지다. 어느 쪽도 확정된 구현으로 기록하지 않는다.
- 게임 코드/ABP/에셋 변경과 빌드/PIE는 없다. 다음에는 사용자 답변을 정본 하단에 반영한 후 Walk 두 Turn과 확정된 Sprint 정책의 변수/함수/클래스 책임/에디터 절차를 자세히 설명한다. 이전의 모든 gait MovingTurn 계획이나 SprintStart를 복원하지 않는다.

## 2026-09-08 SprintPivot 의도 확정 / 24 fps 진단 완료

- Sprint 의미 대기는 해소됐다. Sprint 중 급반전에서 Stop 시퀀스의 제동 구간을 잠깐 쓰고 반대 Sprint로 이어가며 일반 Stop 상태에는 들어가지 않는다. `SprintPivot`은 제안명이고 아직 구현하지 않았다.
- Walk 두 Turn/Run Turn 제외/모든 Start 제외를 유지한다. 게임 코드/ABP/에셋을 어시스턴트가 변경하지 않았다.
- FPS 검사 완료: PSA 11개, FBX 6개, 현재 InGame 11개 및 Sequence Player 10개, source/InGame 각각 5개 표적 회전 변화. 24 fps import 시간축과 약 30 fps PSA 유효 시간축 차이가 확인됐다. 정확한 원작 런타임 배속은 미검증이며 1.25배 비교/보정은 미적용이다.
- 정본: [LOCOMOTION_CURRENT_IMPLEMENTATION.md](LOCOMOTION_CURRENT_IMPLEMENTATION.md)의 최신 절, [DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md](../Art/DAS_ANIMATION_TIMING_AUDIT_2026-09-08.md), `Saved/ImportReports/Khazan_Locomotion_Timing_Audit_20260908.json`.
- 이번 Editor health는 connected/PID 27064, 프로세스 Responding=true이고 metadata/RAW pose 읽기가 성공했다. 과거 미회수 32초 PIE, 중단점/callback 정리 및 전체 Stop 시각 테스트를 재개/완료한 것은 아니다.
- 남은 작업: 1.25배 비교 기준 확인/필요한 보정 선택 → Walk Turn 유효 구간과 Sprint Stop 제동 구간 확인 → 클래스별 데이터/함수/CMC/ABP 구현을 사용자에게 자세히 설명.
- 정확한 재개: Router → 현재 구현 정본 최신 절 → Art 시간축 검사 → 이후 사용자가 수정한 해당 파일/에셋만 표적 확인. FPS/유효 구간 확정 전에 고정 초 Pivot timer를 단정하지 않는다. input intent 삭제로 Stop 진입을 위장하지 않으며 L스틱 중앙 통과 시 토글 Sprint가 꺼지는 현행 입력 정책을 함께 다룬다.

## 2026-09-08 SprintPivot 방향 비교 가이드 준비 / 원작 gameplay metadata 대기

- 현재 요청: Sprint 중 급반전에 Sprint Stop의 짧은 제동 구간을 사용한 뒤 반대 Sprint로 연결한다. 일반 Stop 상태가 아니다. 사용자가 직접 구현하도록 한 줄씩 설명하는 방식은 AGENTS.md에 고정했다.
- 완료: 현재 Player/Locomotion/AnimInstance/Build.cs 확인, 기존 report 및 원본의 필요한 경로만 표적 확인, live asset metadata 읽기, 방향 각도 수학의 8개 엔진 참조 사례 확인. [INGAME_SPRINT_PIVOT_STEP_1.md](INGAME_SPRINT_PIVOT_STEP_1.md)에 새 공통 수학 함수와 AnimInstance 관측 두 멤버를 사용자가 추가할 절차를 작성했다.
- Source의 새 helper/관측 멤버/실제 Pivot state는 어시스턴트가 적용하지 않았다. 게임 코드/ABP/시퀀스 변경과 새 C++ 빌드/PIE는 없다. 제안 단계와 구현 완료를 혼동하지 않는다.
- 마지막 live 관측: Editor PID 32936, InGame Sprint Loop/Stop FrameRate 24/1 및 RateScale 1.25. Stop EnableRootMotion=false/ForceRootLock=true. 새로 읽은 현재 값이며 이번 어시스턴트 수정이 아니다. [준비 리포트](../../Saved/ImportReports/Khazan_SprintPivot_Preparation_20260908.json)에 저장했다.
- 미완료 원인: 현재 확인한 자료에 원작 Pivot 진입 각도, 제동/회전/해제 조건·시점, 입력 중앙 통과 Sprint 유지 정책의 근거가 없다. PSA 길이/발 marker로 시간을 임의 생성하지 않는다. 원작 전체를 전수조사한 것은 아니며 사용자에게 관련 BP/DA/DT JSON 위치를 요청했다.
- 남은 작업: 사용자 첫 단계 적용 확인 → 원작 gameplay 자료 확인 → game-thread의 입력 명령 적용 전 Pivot 판정/방향 보존/제동·회전·재가속 → snapshot 전달 → ABP 별도 SprintPivot 상태/중단/완료 → 일반 Stop/L3/중앙 통과/공중/재진입 회귀 검사.
- 정확한 재개: 0_DOCUMENT_ROUTER.md → LOCOMOTION_CURRENT_IMPLEMENTATION.md 최신 절 → INGAME_SPRINT_PIVOT_STEP_1.md → 현재 사용자 소스(제안 파일이 실제 생성됐는지부터) → 제공받은 원본 package/JSON의 필요한 field를 확인한다. 진입 각도/시간에 임시 기본값을 넣거나 AnimInstance worker에서 CMC를 제어하지 않는다.
- 이전 미회수 32초 Stop PIE/중단점/callback 정리 문제는 이번 read-only 연결만으로 완료 처리하지 않는다. 실제 실행 검증을 재개할 때는 Engineering continuity의 관련 절차와 현재 프로세스를 다시 확인한다.

## 2026-09-08 SprintPivot 수치 대기 해소 — 임시 튜닝값 명시 후 진행 허용

- 최신 사용자 지시로 원작 metadata 우선 원칙은 유지하되 필요한 임의값의 선정/사용이 허용됐다. 원작 자료 미확인만으로 SprintPivot 설명을 중단할 필요가 없어졌으며 BP/DA/DT JSON 제공은 필수 재개 조건이 아니다.
- 다음 재개: Router → 로코모션 정본 최신 수치 정책 → 가이드 최신 추가 절 → 사용자가 실제 작성한 LocomotionComponent/Player/AnimInstance/공통 수학 함수를 확인한다. 기존 원작 report의 필요한 정보부터 재사용하고 없는 필수 값은 임시 튜닝값으로 명시해 상세 구현 설명을 진행한다.
- 각 임시값의 선정 이유·단위·영향·조정 기준을 제시하고 조정 가능한 설정에 모은다. 실제 Pivot 단계는 game-thread 제어 → snapshot → ABP 별도 SprintPivot → 회귀 검증 순으로 진행한다.
- 이번에는 문서 규칙만 갱신했고 새 gameplay 값/코드/에셋 적용과 빌드/PIE는 없다. 이전의 미완료 실행 검사/중단점/callback 정리 상태는 수치 대기 해소와 별개이며 완료 처리하지 않는다.

## 2026-09-08 Pivot 증분 작업에서 캐릭터 전체 아키텍처 검토로 전환

- 최신 요청은 단순 Pivot 추가가 아니라 Player/다수 몬스터·보스와 대시/공격/스킬/피격을 수용하는 구조 검토다. [CHARACTER_ARCHITECTURE_REVIEW_20260908.md](../Engineering/CHARACTER_ARCHITECTURE_REVIEW_20260908.md)에 검토를 완료했고 권장안은 아직 적용하지 않았다.
- 앞선 LocomotionMath와 AnimInstance 입력각 관측 추가 절차는 철회했다. 현재 Source에는 제안 파일/멤버가 없다. 사용자 파일을 삭제하거나 원래 로코모션을 롤백하지 않았다.
- 마지막 확인은 현재 native 코드와 Editor PID 32936의 전체 ABP export 검사다. MovementDirectionAngle 등 소비 없는 후보와 실제 사용 중인 9종 BP 멤버를 구분했다. 빌드/PIE/성능 측정 및 이전 중단점/callback 정리는 이번에 하지 않았다.
- 재개: Router → 로코모션 정본 최신 절 → Engineering 캐릭터 아키텍처 검토 → 사용자가 확정한 책임/수명 계약과 실제 파일을 확인한다. 이후 공통 이동 정책과 입력/AI 어댑터를 먼저 설명하고 공통 액션/표현의 작은 검증 단위로 진행한다.
- GAS/Linked Layers 도입을 이미 구현된 것처럼 가정하지 않고, 모든 Start 제외/InGame 한정/단일 Sprint Stop의 별도 Pivot 재사용 의도와 명시된 임시 수치 허용은 유지한다.
