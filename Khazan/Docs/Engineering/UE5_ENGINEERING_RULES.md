# UE5 Engineering 규칙

## C++ 수학과 Include

- 회전·방향 벡터 등 수학 연산은 `UKismetMathLibrary`를 사용하고 데이터 표현은 `FVector`를 우선한다.
- `FVector` Ambiguous 오류가 발생하면 전역 네임스페이스를 명시한 `::FVector`를 사용한다.
- 자동 완성으로 `Aossoa.isph` 등 Unreal 내부 ISPC/SIMD 헤더가 Include되지 않도록 확인한다.
- `check`와 `CastChecked`는 복구 불가능한 프로그래머 불변식에만 사용한다. Config·Data Asset·GameplayTag처럼 프로젝트 데이터에 의존하는 경로는 실패 원인을 로그로 남기고 안전하게 반환한다.

## 진단과 변경

- Crash 조사 순서는 Engineering 문서 → 최신 동일 시그니처의 `Saved/Crashes` → 관련 Config와 호출 경로 → 필요한 경우에만 디버거다.
- 로그가 실패 값과 정확한 호출 줄을 이미 제공하면 같은 정보를 얻기 위한 디버거 실행을 반복하지 않는다.
- 원인 조사 요청에서는 원인과 해결안을 먼저 기록하고, 사용자가 수정을 요청한 경우에만 C++·BP·Config를 변경한다.
- 기존 사용자 변경을 보존하며 관련 없는 파일의 포맷·Include·BP·Config를 함께 수정하지 않는다.
- 수정 후에는 Editor 완전 재시작이 필요한 설정인지 구분하고 PIE, Standalone, 새 프로세스 중 위험에 맞는 검증을 수행한다.

## 문서 경계

- 소스·Gameplay BP·Config·컴파일·런타임·피직스 결과만 `Docs/Engineering`에 추가한다.
- FModel, 임포트, 머티리얼, 환경 Level 복원 세부 정보는 읽거나 복사하지 않고 필요하면 `Docs/Art` 경로만 참조한다.

## 2026-09-08 게임 수치의 원작 출처와 미확인 값 처리

- 게임플레이/로코모션 수치 설명·구현은 AGENTS.md의 “수치의 원작 메타데이터 출처 필수” 규칙을 따른다. 임의의 이동 속도, 가감속, 회전 속도, threshold, timer, blend time 등을 테스트용 기본값이라는 이유로 새로 제안하지 않는다.
- 원작 파일/에셋 경로 + property/field + 원시 값/단위 + 적용 조건을 제시한다. 계산값이면 원본 입력/수식/변환/가정도 제시하고 원작에 직접 저장된 값과 구분한다.
- 원본 근거가 없으면 미확인으로 남긴다. 해당 수치가 꼭 필요한 구현 단계는 원본 자료 확보 또는 사용자의 명시적 대체값 결정이 먼저다. 코드 예제에서 임의 literal이나 의미가 달라지는 임시 0으로 구멍을 채우지 않는다.
- 기존 프로젝트 수치의 적용 성공은 원작 일치/애니메이션 적합성 검증이 아니다. 현재 값은 보존하고 출처 상태를 먼저 명시한다. 로코모션의 현 값과 후속 절차는 Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md 최신 절을 따른다.
- 이번 반영은 작업 지침 문서만 추가한 것이다. 기존 C++/BP/Config/에셋 수치를 바꾸거나 원작 수치 조사를 완료한 것으로 기록하지 않는다.

## 2026-09-08 수치 처리 개정 — 명시적 임시값 사용 허용

- 최신 사용자 지시로 AGENTS.md의 “수치 정책 개정 — 원작 우선, 명시된 임시 튜닝값 허용”을 따른다. 앞선 원작 자료 확보 전 일률적 보류와 임시값 금지 조건을 대체한다.
- 원작 metadata/report를 우선 확인하되 필요한 값이 없으면 어시스턴트가 임시 튜닝값을 선정해 설명/제안 코드에 사용할 수 있다. 원작값·원작 기반 계산값·임시값의 출처 상태를 분리하며 임시값의 이유, 단위, 동작 영향, 검증/조정 기준을 함께 설명한다.
- 조정값은 책임 있는 클래스의 설정이나 적절한 DataAsset에 모으고 코드 주석에서도 임시값임을 명시한다. 원본 자료 미확인만으로 설명을 중단하거나 같은 범위의 임시값 사용을 반복 승인 요청하지 않는다.
- 이번에는 수치 취급 규칙만 갱신했다. 구체적인 gameplay 값을 새로 선정/적용하거나 C++/BP/Config/에셋을 수정하고 빌드/PIE를 수행한 것은 아니다.

## 2026-09-08 캐릭터 책임·수명 아키텍처 규칙

- 캐릭터 기능의 목표 구조는 [CHARACTER_GAMEPLAY_ARCHITECTURE.md](CHARACTER_GAMEPLAY_ARCHITECTURE.md)의 ARCH-01–12와 14절 변경 절차를 따른다. 현재 적용 상태는 현행 도메인 문서/소스로 확인한다.
- 제어 HFSM/액션 Ability/공통 이동/애니메이션 표현/AI 판단/레벨 진행의 단일 작성자 경계를 유지한다. 새 기능을 Main AnimInstance나 LocomotionComponent 한 파일에 모두 모으지 않는다.
- 원인별 제약 handle, 실행/전이 식별자, 정상·취소·실패·EndPlay 정리, Player/AI 공통 사용을 새 기능의 계약에 포함한다. 늦은 애니메이션 callback으로 gameplay 상태를 복구하지 않는다.
- 신규 semantic refactoring은 BP/직렬화/Redirect/부모 클래스 소비를 함께 검증한다. bool 제거·enum 전환·Linked Layer 도입을 자체 성능 개선으로 단정하지 않고 실제 컴파일/프로파일 근거를 구분한다.
- 새 타입/함수는 실제 소비와 독립 수명이 생기는 단계에서만 추가한다. 설계 정본의 목표 파일 표 전체를 한 번에 생성하지 않는다.

## 2026-09-08 Tag–Ability 아키텍처 v2 우선 적용

- 이후 캐릭터/전투/이동/AI/상호작용은 [아키텍처 v2](CHARACTER_GAMEPLAY_ARCHITECTURE.md#character-architecture-v2)의 ARCH-01–19를 따른다. 앞선 이 파일의 제어 HFSM 전제는 v2의 ASC 태그/효과 원본과 공통 이동/반응 계약으로 대체한다.
- [M0–M10 마이그레이션](CHARACTER_TAG_ABILITY_MIGRATION.md)에 따라 실제 소비가 생기는 단계에서 타입/태그/데이터를 추가한다. M1은 엔진 ASC 접속, M3에서 실제 공통 요청을 가진 Khazan ASC를 구현한다.
- Character/Controller는 조립·입력 의도·요청 전달을 맡고, 액션은 Ability, 수치/반응은 Effect·Attribute·CombatResponse, 이동은 Locomotion/CMC, 표현은 Main/Linked Layer/Cue, 상호작용 결과는 대상이 소유한다.
- 내부 bool/enum을 일괄 금지하지 않고 공개 gameplay 상태의 중복 작성자를 금지한다. Asset/Owned/Event/Cue 태그, effect count/handle, 요청/실행 수명과 GT/worker 경계를 구분한다.
- ActorInfo 연결/참조 갱신/GameplayReady를 구분한다. 같은 Avatar의 단순 갱신을 이유로 InitAbilityActorInfo를 반복 호출해 몽타주 상태를 초기화하지 않는다.
- 기존 수치 출처/임시값 표시, 사용자 변경 보존, 공동 구현의 한 줄 설명과 적용·검증 분리는 계속 적용한다. 문서만 변경한 작업을 게임 파일 적용/빌드 통과로 기록하지 않는다.

