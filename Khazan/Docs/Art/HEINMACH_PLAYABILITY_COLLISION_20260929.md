# HeinMach 원작 진행 경로·충돌·Navigation 복원 — 2026-09-29

## 1. 적용 범위와 완료 판정

- 대상 맵은 `/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment`다.
- 원작의 맨손 오프닝을 시작점으로 되돌리지 않았다. 현 프로젝트 방침에 맞춰 DualAxeSword를 든 Player가 인간형 적 튜토리얼로 진입하는 `MISSION01_START`를 게임 시작점으로 유지했다.
- 지형·배치물 collision, 원작 진행 경계, NavMesh bounds, `NavModifierVolume`, 원작 NavLink와 복원 맵 보정용 link를 맵에 저장하고 Recast를 다시 만들었다.
- 실제 `BP_Player`를 PIE에서 possess해 프로젝트 `IA_Move` 입력으로 지상 이동과 원작 경계벽 차단을 확인했다.
- 이번 범위는 월드 이동 기반이다. 두 인간형 적의 원본 위치 anchor는 유지했지만 Encounter가 실제 적을 spawn하고 기본 액션 학습을 진행하는 mission/AI 스크립트는 새로 구현하지 않았다.

## 2. 첫 시작 구간의 원작 근거

### 2.1 Player 시작점

FModel 원본 `C:/Users/user/Desktop/카잔/Exports/BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01.json`과 저장 metadata의 `MISSION01_START`를 사용했다.

| 구분 | 값 | 출처 상태 |
|---|---:|---|
| 원본 actor | `MISSION01_START` | 원작 직접 확인 |
| 원본 위치 | `(12073.493, 24725.363, 303.5308) cm` | 원작 `RelativeLocation` 직접 확인 |
| 원본 Yaw | `245.0138°` (`-114.9862°`) | 원작 `RelativeRotation.Yaw` 직접 확인 |
| 현재 label | `HM_Tutorial_PlayerStart_DualAxeSword` | 복원 맵 계약 |
| Pawn trace 지면 | `Z=354.703175679 cm` | 복원 Landscape의 Pawn-profile 실측 |
| `BP_Player` capsule half-height | `88 cm` | 현재 CDO 직접 확인 |
| spawn 여유 | `8 cm` | 원작값이 아닌 임시 튜닝값 |
| 적용 capsule 중심 | `(12073.493, 24725.363, 450.703175679) cm` | `지면 Z + 88 + 8` 계산값 |

`8 cm`은 시작점의 경사면 normal과 반지름 `34 cm` capsule의 초기 관통을 피하기 위한 spawn 전용 여유다. gameplay 이동 수치가 아니며, 지형이나 capsule 조립이 바뀌면 Pawn trace와 초기 overlap을 다시 확인한다.

### 2.2 인간형 튜토리얼 anchor

- `SA_EmpireSword_Early3_Item` → `HM_TutorialSpawn_01_EmpireSword`, `(14443.049, 11226.91, 202.70361) cm`, `AI_EmpireSword_Tutorial_Signal_1`.
- `SA_Empire_SwordShield_2` → `HM_TutorialSpawn_02_EmpireSwordShield`, `(18664.227, 3837.669, 35.0254) cm`, `AI_Empire_SwordShield_Tutorial_Signal_1`.
- 저장 맵에는 두 위치가 `TargetPoint`로 남아 있다. 이는 원본 spawn/AI 종류와 위치를 보존하는 anchor이며 살아 있는 적 actor나 Encounter 완료 판정이 아니다.

### 2.3 원작 자동 진행 기록으로 확인한 순서

`HeinMach_Spawn_Main01`의 `xxAutomationTestActor_1`을 전용 추출기로 읽었다. 기록은 총 125 actions이며 `MoveTo 63`, `HuntMonster 37`, `PickupItem 13`, `InteractionLevelObject 7`, `InteractionTombStone 3`, `BreakChaosProp 1`, `HitLevelObject 1`이다.

- 첫 이동 `xxAutomationAction_MoveTo_8`(source index `625`)은 167점이며 첫 점 `(12072.891, 24724.762, 289.15) cm`이 `MISSION01_START` 바로 옆에서 시작한다.
- 다음 이동 `xxAutomationAction_MoveTo_9`(source index `626`)은 37점이며 마지막 점 `(14523.5468, 11223.1497, 211.2411) cm`이 첫 EmpireSword tutorial anchor 인근이다.
- 따라서 현재 시작점은 맨손 오프닝 뒤의 DualAxeSword 기본 전투 튜토리얼 진입 구간이다. 기계 판독 원본은 `Saved/ImportReports/HeinMach_OriginalAutomationRoute.json`이다.

## 3. 물리 이동 surface와 진행 경계

### 3.1 지형과 배치물

- 복원 Landscape static mesh actor 48개를 `BlockAll`, `QueryAndPhysics`, navigation 기여 상태로 저장했다. 대응 mesh BodySetup은 `ComplexAsSimple`과 cooked collision/nav data를 사용한다.
- 저장된 root-template audit의 원본 배치 9,104개에서 기존 사용자 제외 117개를 보존해 8,987개를 처리했다.
- 실제 결과는 collision enabled 7,599개, disabled 1,388개, collision mesh 293종이다.
- 판정 우선순위는 source `BodyInstance.CollisionEnabled` → source `CollisionPrimaryType/CollisionAdjectiveType/CollisionUseless` tag다. `Useless` prop 전체를 편의상 활성화하지 않았다.
- source collision tag가 없는 visible rock 23개만 낙하 방지를 위해 collision을 켰다. 이 23개는 **원작 근거 미확인 임시 fallback**이며 report에 별도 집계된다.

### 3.2 원작 route wall

원본 `HeinMach_Chrcollision.json`에는 `xxWallComponent` 3,206개가 있다.

- half extent 한 축이 `0.01 cm` 이하인 924개는 비체적/degenerate component라 제외했다.
- owner `xxSplineVolumeActor81`의 `bWallCollisionEnabled=false`에 속한 비degenerate wall 1개는 원작 지시에 따라 제외했다.
- 남은 2,281개를 `HM_RouteCollision_Source_Chrcollision` 한 actor의 hidden HISM box로 저장했다.
- 각 instance의 source component/owner, 중심, 회전, half extent는 `Saved/ImportReports/HeinMach_RouteCollision_SourceMapping.json`에 2,281건으로 보존했다.
- actor는 `WorldStatic`, `QueryOnly`이고 Pawn 이동을 막는다. Visibility, Camera, PhysicsBody, Destructible trace에는 응답하지 않아 보이지 않는 진행 벽이 카메라나 조준 trace를 가리지 않는다.

`AKZLevelRouteCollisionActor`는 맵 데이터를 압축 저장하는 역할만 한다. Player와 미래 Character의 실제 이동과 충돌 해결은 각자의 CharacterMovementComponent 책임이다.

## 4. Navigation 복원

### 4.1 원작 직접 복원

- `xxNavMeshBoundsVolume` 242개의 root transform을 `AKZNavMeshBoundsBox`로 저장했다.
- `NavModifierVolume` 26개는 각 BodySetup의 단일 convex가 로컬 `-100..100 cm` box임을 확인하고, 같은 위치·회전·scale의 `AKZNavModifierBox`/`NavArea_Null`로 저장했다.
- `NavLinkProxy`/`xxNavLinkProxy` 14개를 원본 endpoint와 방향으로 저장했다. 양방향을 포함한 필수 연결 방향 19/19가 실제 Recast path로 연결됐다.
- source index `828`의 `NavLinkProxy6`만 원본 snap radius `30 cm`에서 적용값 `50 cm`로 보정했다. 복원 Recast edge가 원본 endpoint에서 `31.4 cm` 떨어져 원본 반경보다 `1.4 cm` 밖이기 때문이다. 이는 원본값과 분리 기록한 복원 전용 임시 보정이다.

### 4.2 원본 자동 경로 기반 복원 보정

원작 자동 경로 1,485점을 복원 Recast에 연속 높이로 투영한 뒤, static mesh 변환 때문에 끊어진 10개 구간에 forward-only link를 추가했다.

- 직접 원본 NavLink가 아니라 `원작 route point + 현재 복원 Recast projection`에서 계산한 값이다.
- endpoint, source action/segment, `forward_drop`/`local_recast_gap` 분류는 `Content/_Art/Player/Environment/HeinMach/Metadata/HeinMach_AutomationRouteNavCompatibility.json`에 저장했다.
- snap radius `50 cm`은 복원용 임시값이다. 링크는 원작 진행 방향인 `LeftToRight`만 허용한다.
- 이 link는 path connectivity를 제공한다. 낙하·상호작용의 전용 animation, Ability/Task, 착지 결과를 대신 실행하지 않는다.

## 5. 게임 시작 연결

- 맵 World Settings GameMode는 `/Game/Bluprints/GameSystem/BP_GameMode`다.
- 프로젝트 `GameDefaultMap`을 HeinMach 맵으로 바꿨다. `EditorStartupMap`은 개발 편의를 위해 `/Game/Maps/DevMap`을 유지한다.
- 런타임 default pawn은 `/Game/_Art/Player/Character/Bluprints/BP_Player`이며 `DA_CharacterDefinition_Player`를 사용한다.
- PIE에서 `DualAxeSword_Original_R`과 `DualAxeSword_Original_L` mesh가 Player mesh에 부착된 상태를 확인했다.

## 6. 최종 검증

최종 저장 맵은 9,622 actors이며 SHA-256은 `E592ECA579B758B60CE6668751EE025BE29995E0554AB7CB0DC03AD15231F4FD`다.

| 검사 | 결과 |
|---|---:|
| route wall instances | `2,281 / 2,281` |
| NavMesh bounds | `242 / 242` |
| NavArea_Null modifiers | `26 / 26` |
| 원작 NavLink actors | `14 / 14`, 필수 방향 `19 / 19` |
| 복원 route compatibility links | `10 / 10` |
| 원작 MoveTo actions | `63 / 63` |
| Recast 투영 route points | `1,485 / 1,485` |
| 연결 route segments | `1,422 / 1,422` |
| 실패 actions | `0` |
| 첫 tutorial actions 625/626 | 통과 |
| PIE Player 평면 이동 | `706.740701 cm`, 입력 해제 뒤 grounded |
| hidden route wall의 Pawn 차단 | 통과 |
| `KhazanEditor Win64 Development` | 성공 |

`17`개 인접 segment는 투영 결과의 거리가 `1 cm` 이하라 같은 Recast 점으로 collapse됐고 정상 연결로 계산했다. 검증 정본은 `Saved/ImportReports/HeinMach_Playability_RuntimeVerification.json`이다.

## 7. 재현 자료와 경계

- 원본 route 추출: `Scripts/HeinMach/extract_heinmach_automation_route.py`.
- 맵 복원: `Scripts/HeinMach/restore_heinmach_playability.py`.
- 읽기 전용 inventory: `Scripts/HeinMach/audit_heinmach_playability.py`.
- 일반 Editor Recast build·PIE: `Scripts/HeinMach/build_and_verify_heinmach_playability.py`.
- 복원 report: `Saved/ImportReports/HeinMach_Playability_Restoration.json`.
- 읽기 전용 report: `Saved/ImportReports/HeinMach_Playability_Audit.json`.
- 작업 전 map backup: `Saved/ArtBackups/HeinMach_Playability_PreRestore_20260929/L_HeinMach_Environment.umap`, SHA-256 `D7146BB247B867F3BD61E78DB7114345825E24B944D162E40E8C9884BF0EB4BA`.

Python commandlet 자체는 정상 완료하고 report/map을 저장한다. process exit `1`은 이 프로젝트의 기존 `/Script/GameFeatures.GameFeatureData` load ensure가 error count로 집계되기 때문이다. Recast와 PIE의 최종 합격 판정은 해당 build lock이 없는 일반 `UnrealEditor.exe` 검증 report를 기준으로 한다.

현재 보장 범위는 원본 경로의 물리 surface, 진행 차단, Recast 연결과 실제 Player 이동이다. Enemy spawn/AI 전투, 학습 UI, mission gate, TombStone·level object 상호작용과 drop 전용 동작은 각 gameplay 소유자에서 후속 구현해야 한다.
