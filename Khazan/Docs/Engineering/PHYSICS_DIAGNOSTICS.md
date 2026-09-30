# Physics 진단 기록

> 런타임 movement physics, collision, physical animation, ragdoll, constraint 문제만 기록한다.
> 메시 임포트 단계의 collision/physics asset 생성은 Art 작업으로 분류한다.

## 2026-08-31 기준

- 아직 별도 physics 진단 기록이 없다.
- 새 진단 시 증상, 재현 Level/BP, collision preset과 channel, simulation 주체, authority/network 조건, 관련 body/constraint, 로그 또는 디버거 증거, 수정과 검증 결과를 날짜별로 추가한다.

## 2026-09-29 HeinMach CharacterMovement collision 복원

- 재현 Level은 `/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment`, Pawn은 `BP_Player`, capsule은 radius `34 cm`/half-height `88 cm`다.
- 원인은 복원된 Landscape/prop mesh의 gameplay collision·navigation data와 원작 `HeinMach_Chrcollision` route wall이 플레이용 맵에 완결되게 연결되지 않은 상태였다.
- Landscape 48개와 source 판정 prop에 collision을 적용하고, 활성 비degenerate `xxWallComponent` 2,281개를 `WorldStatic/QueryOnly` hidden HISM으로 저장했다. source에서 명시적으로 disabled인 wall 1개와 degenerate 924개는 제외했다.
- PIE에서 `IA_Move` 2초 입력으로 평면 `706.740701 cm`, 수직 `56.102992 cm` 이동하고 입력 해제 뒤 `is_moving_on_ground=true`를 확인했다. source wall instance `2229`를 향한 Pawn profile trace가 `BoundaryCollision`에 blocking hit를 반환했다.
- 최종 물리·경로 report는 `Saved/ImportReports/HeinMach_Playability_RuntimeVerification.json`, instance provenance는 `HeinMach_RouteCollision_SourceMapping.json`이다.
