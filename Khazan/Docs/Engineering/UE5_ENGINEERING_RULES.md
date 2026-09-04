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
