# HeinMach 사용 구간 밖 배치 정리

## 2026-10-16 — Main 반영 완료

사용자 요청에 따라 `/Game/Maps/L_HeinMach_Environment`의 **PlayerStart부터 Yetuga 입구 포탈까지의 이동·전투 구간 및 Yetuga 전장**을 사용 영역으로 삼았다. 그 밖에서 사용 시야·조명·그림자·음향에 영향이 없는 배치를 제거했다. 사용 구간에서 보이는 외부 배경, 공통 Landscape, 전역 날씨·하늘·안개·PostProcess는 유지했다. 공유 Content의 메시·재질·음원 원본은 삭제하지 않았다.

결과 정본은 `Metadata/HeinMachRoutePrune_20261016/FinalVerification.json`이다. 몬스터10, PlayerStart1, 포탈과 도착점, GateCube 메시 제거 상태, Yetuga BGM 진입 후 지속 재생 계약을 유지했다. 초기 한글 문서 출력 오류본은 `DocumentationEncodingBackup`에 보존하고 이 신규 문서를 UTF-8로 바로잡았다. 기존 도메인 문서에는 올바른 날짜별 정정 절을 추가했다.

### 실제 삭제 결과

| 항목 | 이전 | 이후 | 삭제 |
|---|---:|---:|---:|
| 레벨 액터 | 10,022 | 5,764 | 4,258 |
| HISM 인스턴스 전체 | 14,776 | 5,639 | 9,137 |
| 풀·나무 인스턴스 | 12,495 | 4,199 | 8,296 |
| 경로 충돌 인스턴스 | 2,281 | 1,440 | 841 |

액터 삭제: StaticMeshActor3,870, PointLight38, Emitter50, Decal10, NavBounds152, NavLink17, NavModifier26, AmbientSound48, AudioVolume5, 비어진 HISM 배치42개. 마지막42개는 액터4,258개에 포함된다. 인스턴스9,137개 전체를 풀·나무로 불렀던 진행 안내는 위 세부 분류로 정정한다. 경로 충돌841개는 미사용 이전 루트에 해당하며, 사용 루트의 나머지 충돌과 소유 Actor는 유지했다.

맵 파일은37,790,567→22,693,731bytes로 약39.95% 줄었다. 이는 `.umap` 크기이며 패키지 크기나 FPS 개선율이 아니다. 이전20261015 Shipping 배포본은 이번 요청에서 재패키징하지 않았다.

### 선택 근거와 검수

기존 Art 정본과 saved metadata를 먼저 확인했다. 이전 pose 보고서만으로 가시성·HISM bounds를 판단할 수 없어 현재 단일 맵만 Inventory01으로 조사했다. FModel/전체 Content 전수조사는0이다. `Plan.json`, `Selection.json`, `SpatialPlan.png`에 유지/삭제 근거를 저장했고, 중복 Talk actor label 대신 실제 actor name으로 식별했다.

- 현재 PlayerStart·몬스터·포탈·보스 좌표와 NavBounds가 기준이다. route 경계 여유1,800cm, 보스 중심 반폭5,000cm, light 여유1,500cm와 sun shadow 여유600cm는 **어시스턴트가 선정한 보수적인 삭제/QA 임시값**이다. 원작 메타데이터 값이나 runtime gameplay 튜닝이 아니다.
- NullRHI HISM actor bounds가0인 경우를 그대로 쓰지 않고 mesh local AABB와 각 instance의 world scale/quaternion/translation으로 bounds를 계산했다. 원래 transform은 Inventory01에 보관했다.
- Depth03은 실제 SceneDepth256×256을92지점×6방향=552뷰로 수집했다. 기본40지점과 authored13지점의 XY±400cm 위치52개다. 실제 지면+300cm 높이, bounds100cm/pixel3/depth100cm 또는2% 여유도 QA 임시값이다. 근평면·잠재 가시성은 유지 쪽으로 분류했다.
- 사용 영역에 닿는 light attenuation, 현재 sun 방향의 잠재 shadow caster, 실제 SoundCue attenuation/max-distance를 보존했다. 무한/미확인 음향은 삭제하지 않았다. 이름이나 거리만으로 배경을 제거하지 않았다.
- Compare02는 같은 disposable PIE에서 삭제 전후48시야를 촬영했다. 실제 출력749×381이며 요청 window1280×720과 구분한다. Epic11그룹3/해상도100%, 동일 camera pose, simulation dilation0.0001과 캐릭터/UI 숨김은 촬영 세션에만 적용해 맵에 저장하지 않았다.
- `Compare02/Sheet_00.png`~`Sheet_05.png`의48쌍을 직접 검토했다. 새 배경 구멍·빈 면·누락 조명은 관측하지 않았다. 눈/포탈 입자 영역의 차이와 작은 temporal 렌더 차이가 남으므로 픽셀 일치는 주장하지 않는다. 포탈 중앙 일부 시야가 입자에 가려지는 한계는 인접 접근 시야와 깊이 검사로 보완했다.

### 저작·Main 전달과 실제 검증

`Khazan_HeinMachPrune_20261016/Khazan`의 독립 Content/Maps 사본에서 Author01을 수행했다. Source/Plugins/다른 Content junction은 읽기용이다. 원본 백업·SHA 확인 후 선택 배치를 삭제하고 RebuildNavigation을 완료해 맵 하나만 저장했다. 잔존 인스턴스는 배열 재정렬 가능성을 고려해 transform multiset으로 원본에서 삭제 대상을 뺀 결과와 비교했다.

Author01 삭제 전후, WorkSaved02와 MainSaved01의 새 프로세스에서 지면40/40, nav projection13/13, 경로11개를 검사했다. 기존 완전 연결8개가 유지됐다. 포탈/Apes/Sit까지의3개 partial path는 원래부터 동일하며 새 회귀가 아니다. 전체 AI/전투/NavMesh 문제 해결이나 플레이어 전체 루트 주행 검증으로 확대하지 않는다.

최종 retained-state 비교는 **같은 warm full-editor 조건의 MainBaselineScene01 → WorkSaved02 → MainSaved01**이다. 삭제 외 모든 actor name/class/folder/transform/hidden/tag/parent, component mesh/material/visibility/collision/shadow/light, PostProcess 및 잔존 instance transform이 일치했다. 포탈 목적지·Box·VFX·암전·음악, 전역 fog/navigation 설정도 보존했다. collision 차이를 무시해 통과시키지 않았고, Python struct repr의 프로세스별 메모리 주소만 정규화했다.

MainDelivery01은 Main SHA가 착수본과 동일하고 Main editor process가 없는 것을 확인한 뒤 검증된 맵만 atomic 교체했다. Source/Config hash 차이0, 게임 C++/신규 runtime 파일 변경0, 공유 resource asset 저장0이다. 사용자/Rider/외부 editor 종료·강제 저장은0이다.

### 실패 및 검사 방식 보정

Depth01은 HiddenActors property 직접 대입 오류, Compare01은 Python에 없는 get_character_movement 호출 오류였으며 모두 map save0이었다. 공개 hide_actor_components 및 CharacterMovementComponent 조회로 고쳐 별도 성공 run을 남겼다. Depth02의 높은 지면 ray가 포탈 동굴 지붕을 잡은 문제는 Depth03에서 authored Z+50cm부터 아래로 검사하도록 보정했다.

Inventory01/WorkNull01·02의 즉시 NullRHI collision snapshot은 warm RHI와 일부 값이 달랐다. 원본 MainBaselineDetails01/MainBaselineScene01도 다시 읽어 동일 RHI 조건에서 원본과 변경본이 일치함을 확인했다. 세부 엔진 초기화 원인을 단정하지 않는다. PlayerStart Sprite2는 엔진 PlayerStart.cpp 생성자의 `!IsRunningCommandlet()` 분기에서 숨기는 editor-only bad sprite였다. 간이 snapshot에 맞춰 게임 충돌이나 sprite를 수정하지 않았다. 과거 실패 report를 삭제하거나 통과로 덮어쓰지 않았다.

### 재생성 방지·복구·다음 절차

`Content/_Art/Player/Environment/HeinMach/Metadata/HeinMach_RoutePruneExclusions_20261016.json`에 actor4,258개와90 component의 제거 instance9,137개를 기록했다. 원래 index는 baseline 맵에서만 유효하며 actor/component/world transform 및 transform hash로 식별한다. 기존 User/Optimization/ManualOverrides 기록은 유지했다.

`Scripts/HeinMach/heinmach_exclusions.py`의 오래된 Kazan metadata 경로를 실제 Player 경로로 맞추고 새 목록을 추가했다. 등록 label4,385개에서 이번4,258개를 모두 읽는다. 기존 whole-batch foliage 복원기는 이 목록이 있으면 실행을 거절한다. 과거 전량 복원/actor count audit를 현재 정본으로 삼지 않으며 경로 충돌 등을 재구축할 때도 개별 tombstone을 소비해야 한다.

원본 백업: `Metadata/HeinMachRoutePrune_20261016/Before/L_HeinMach_Environment.umap`.

- 원본 SHA: `7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728`.
- Main 완료 SHA: `1d224b14ae0ec39b90229e2a122b174b672ca64d976f3c0ef0032236c47f7c00`.

복구가 명시적으로 필요하면 먼저 최신 Main을 별도 백업하고 이후 변경 유무를 확인한다. 전체 복구는 위 원본을 동일 `/Game/Maps` package 경로에 복원해 fresh readback하고 tombstone 적용 상태도 날짜별로 기록한다. 이후 사용자 변경이 있는 Main을 무조건 옛 백업으로 덮어쓰지 않는다. 부분 복구는 독립 프로젝트에서 원본을 열어 actor name/component/transform 단위로 선택 이관한다. 완료 author/delivery를 그대로 반복하지 않는다.

필수 잔여는0이다. 가시성은 표본 시야에서의 검수 결과이며 모든 자유 카메라 위치의 동일성을 보증하지 않는다. Shipping FPS/재패키징은 이번 작업 범위 밖이다.
