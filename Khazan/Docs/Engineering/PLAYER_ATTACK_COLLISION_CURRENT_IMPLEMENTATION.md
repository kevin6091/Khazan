# Player Combo 공격 충돌 현재 구현

## 2026-10-08 — 격리 구현·PIE 검증 완료, Main 반영 대기

이 문서는 `Khazan_ComboWork_20261008/Khazan`에서 실제 적용하고 검증한 Player 공격 충돌의 정본이다. 기준 계약은 `CHARACTER_GAMEPLAY_ARCHITECTURE.md`의 ARCH-81이다. **이 기록 시점에는 Main Source/Content 전달, Main 최종 빌드와 실행 에디터의 새 native schema 반영이 아직 완료되지 않았다.** 전달 완료는 후속 날짜별 기록으로 추가한다. 격리 검증을 Main 적용 완료로 해석하지 않는다.

현재 Combo node 26개 중 공격·준비 node 18개에 충돌 구간 60개와 key 553개를 작성했다. 단순 Dodge 8개에는 공격 판정을 넣지 않았다. 기존 입력·콤보 Ability 구조를 유지하면서 범위, 시간, Group, HP·Stamina 피해량과 초록색 debug draw를 데이터로 편집할 수 있다.

### 실제 변경 범위와 책임

기존 product C++ 3파일을 확장했다.

| 파일 | 책임 |
|---|---|
| `Source/Khazan/Ability/Combo/KZComboDefinitionData.h` | 기존 node에 shape/window/key/피해/출처 데이터와 `CollisionToActor`를 추가한다. Definition이 공통 damage GE와 debug 표시 선택을 보유한다. |
| `Source/Khazan/Ability/Combo/KZComboActionAbility.h` | 활성 Ability의 충돌 갱신·조회·정리 함수, timer, 이전 clock/actor transform, 대상별 적중 기록과 실행 번호를 선언한다. |
| `Source/Khazan/Ability/Combo/KZComboActionAbility.cpp` | 현재 montage clock으로 구간을 조회하고 authority에서 Monster 피해를 승인한다. 전환·정상 종료 flush와 취소 cleanup을 소유한다. |

새 runtime class/component/manager/AbilityTask/태그는 추가하지 않았다. `EKZAttackCollisionShape`, `FKZAttackCollisionKey`, `FKZAttackCollisionWindow`는 기존 데이터 헤더 안의 작은 타입 확장이다. 공통 피해 에셋 1개 `GE_ComboAttack_Damage`와 DEV automation 전용 `Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp` 1개를 추가했다. 테스트는 `WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS` 범위다.

에셋 작성 대상은 기존 `DA_Player_Combo_Definition`과 새 damage GE이다. Monster는 기존 공통 ASC/AttributeSet과 이미 작성된 초기 HP·Stamina 효과를 사용한다. 몬스터의 definition/grants/AI/locomotion, Player 의상/물리, 다른 작업의 Snow 기능을 이번 기능으로 덮어쓰지 않는다.

### 에디터에서 조정하는 위치

Content Browser에서 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`을 연다. `Nodes` 배열에서 `Node Id`로 공격을 찾고 `Attack Windows`를 펼친다. 실제 C++ 필드명과 의미는 다음과 같다.

| 필드 | 의미와 편집 기준 |
|---|---|
| `StartTime`, `EndTime` | 해당 node의 시작 section을 0으로 한 재생 시간(s). 자동 NextSection 구간은 같은 node clock을 계속 사용한다. `EndTime`이 `StartTime`보다 앞서면 판정하지 않는다. |
| `Shape` | Box / Cylinder / Sphere 선택. |
| `Extent` | cm. Box는 각 축 half extent, Cylinder는 X/Y 반경·Z half height, Sphere는 X 반경이다. Cylinder 조회는 `max(X,Y)` 반경을 사용하며 작성본은 X/Y를 같게 넣었다. |
| `HitGroup` | `None`이면 이 window에서 대상당 1회. 같은 node의 동일한 비어 있지 않은 Group은 적중 기록을 공유한다. 반복 타격마다 다른 Group/window가 필요하다. |
| `HPDamage`, `StaminaDamage` | 절대 Attribute 피해량. 유한한 0 이상의 값으로 편집한다. 작성본은 각각 10/5의 임시값이다. |
| `bBlockable` | 에디터의 `Blockable`. 기존 Guard 처리를 허용한다. 작성본은 true의 임시 정책이다. |
| `Keys[].Time` | 위와 같은 node-local 시간(s), 시간순 배열. |
| `Keys[].Center`, `Rotation` | 충돌 shape 중심의 local cm와 Unreal degree 회전. 원작 ground frame 또는 현재 pose에서 파생한 값이다. |
| `Source` | 읽기 전용 출처 문자열. 원본 package/file/SHA/export, 원작·현재 시간, 변환, geometry 경로와 임시 해석을 저장한다. |
| node의 `CollisionToActor` | key의 ground/model frame을 actor-local로 변환한다. 작성본은 현재 BP mesh의 relative location만 사용하고 회전 identity/scale 1이다. |

Definition의 `Attack Damage Effect`에는 `/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C`를 지정했다. `Draw Attack Collision` 체크박스(`bDrawAttackCollision`)로 초록색 판정 shape 표시를 켜고 끈다. 현재 작성본은 켜져 있다. 판정 갱신 때 Box/Cylinder/Sphere를 그리며, 별도의 mesh/Actor 충돌체를 Spawn하지 않는다. 정지 에디터의 상시 preview가 아니라 실행 중 debug draw이다.

### 현재 node별 작성 범위

| Node | Window 수 | 범위 |
|---|---:|---|
| `WeakAttack01` / `02` / `03` / `04` / `05` | 1 / 1 / 2 / 2 / 2 | 각 `Com_WeakAtk01~05`의 CompositePlayback 시간축. |
| `StrongAttack01` / `02` / `03` | 2 / 2 / 2 | 정확한 현재 CA를 참조하는 일반 Strong AC. Strong01 Start AC에는 공격 구간이 없고 Normal AC의 2개를 사용한다. |
| `StrongCharge` | 4 | 준비 section에서 자동 `ChargeAttack`으로 진행하는 구간을 포함한다. 준비 pose 자체의 범위 밖 공격 구간은 제외한다. |
| `StrongChargeAttack` | 4 | `Flow_Flow_StrongAtk01`의 Group1/Group2 구간. |
| `ChargeAttack02` / `03` | 3 / 4 | 03은 자동 `ChargeAttack04`까지 포함한다. |
| `DodgeAttack_F` / `R` / `B` / `L` | 각 1 | 방향별 `Com_DodgeAtk` AC. |
| `SpinningAttack01` | 7 | 일반 Spinning Start 3개와 자동 Finish 4개. 다른 BeastRush/SuperSpeed 및 UltimateSlash 변형을 합치지 않는다. |
| `OverFury` | 20 | 현재 montage의 6개 segment occurrence. 첫 동작 임시 Start 3개, 네 Loop occurrence 각각 4개, Finish 1개. 첫 동작의 공유 Group 때문에 실제 대상별 적중 수는 window 수와 다르다. |

OverFury `Loop01/Loop02`는 같은 원본 CA의 서로 다른 source 시간 범위를 사용한다. `_02_2`, `_02_3`, 반복 `_02_3` occurrence마다 Group 이름에 segment 번호를 붙였다. 같은 동작의 공유 Group은 유지하고, 다음 반복까지 같은 적중 기록으로 막지 않는다. Spinning/Charge의 자동 section chain을 첫 section 길이로 자르지 않는다.

### 판정·피해·수명 계약

활성 ComboAction이 다음 tick timer를 사용해 montage position을 읽는다. node clock은 `MontagePosition - 시작 SectionStart`이다. 이전 시간부터 현재 시간 사이에 들어오는 window 양 끝과 **통과한 모든 baked key**를 조회한다. key 사이의 Center/Rotation과 actor transform을 보간해 현재 world shape를 구한다. 큰 frame 간격에서 window 전체를 지나도 조회 기회를 보존한다. window는 지속 구간이며 매 key가 새로운 피해 횟수를 의미하지 않는다.

대상 Actor는 window 또는 동일 Group에서 1회만 소비한다. 적중 기록은 피해/Guard callback 전에 넣어 재진입에 의한 중복을 방지한다. 별도의 window/Group은 같은 Monster를 다시 때릴 수 있다. 이 정책은 원작 `1회 공격`·Group 기록에서 채택한 프로젝트 해석이며 원작 native target dedup 구현을 직접 확인한 것은 아니다.

authority game thread에서 `ECC_Pawn` object query 후 유효한 `AKZMonster`만 수신자로 사용한다. 자기 Actor, 이미 소비한 대상, ASC/Attribute가 없는 대상, MaxHP가 초기화되지 않았거나 HP가 0인 대상은 제외한다. Box/Sphere는 overlap과 key 사이 이동 sweep을 사용한다. Cylinder는 box broadphase 뒤 회전된 유한 Cylinder와 Monster capsule의 거리 검사를 사용한다. Box 회전 전체의 연속 sweep 및 Cylinder key 사이의 연속 회전/이동 판정까지 원작과 같다고 검증하지는 않았다.

차단 가능한 공격이고 Monster가 공격자를 정면으로 보고 있으면 기존 `TryGuardHit(StaminaDamage, Avatar)`를 시도한다. 성공 시 기존 Guard가 Stamina 비용을 처리하고 일반 HP/Stamina damage GE를 중복 적용하지 않는다. 거부되면 일반 피해를 적용한다. 정면 판단은 dot ≥ 0의 임시 프로젝트 정책이며 원작 Guard 각도 근거는 미확인이다.

일반 피해는 source ASC의 GE spec에 `KZAttackHPDamage=-HPDamage`, `KZAttackStaminaDamage=-StaminaDamage`를 SetByCaller로 설정해 target ASC에 적용한다. 기존 AttributeSet이 HP/Stamina 하한·상한을 처리한다. 피격 연출, Dead/Invincible 태그 생성, 사망 AI 정리, GuardBreak와 UI는 이번 수치 피해 구현의 완료 범위에 포함하지 않는다. 현재 Ability의 standalone 실행을 검증했으며 multiplayer 동작은 별도 검증하지 않았다.

node 전환·다른 Entry Ability 활성화 직전에 기존 구간을 flush한다. 정상 montage 종료에는 제거된 montage instance가 position 0을 반환할 수 있으므로 마지막 authored window endpoint까지 남은 clock을 소비한다. 중단/취소에는 이 완료 flush를 하지 않는다. reset은 timer·hit set·이전 clock을 지우고 실행 번호를 증가시킨다. 피해 callback이 실행을 끝내거나 교체하면 이전 실행의 처리를 중단한다. 기존 EndAbility/UnPossess/EndPlay 경로를 재사용하며 Notify End만 기다리지 않는다.

### 원작 수치와 계산 출처

원본 조사 정본은 `Metadata/PlayerAttackCollision_20261008/Original/SourceAttackWindows.json`이다. 이미 저장된 AC 83개/170구간/1,153 key를 인덱싱했고 SI 6개·SD 85개를 필요한 package만 표적 추출했다. 원본 JSON 경로와 SHA를 기록했다. 변형까지 조사한 수가 현재 적용 수를 의미하지는 않는다.

| 구분 | 정확한 출처·필드·원시 값과 적용 |
|---|---|
| 원작 직접값 예: Weak01 | `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/WeakAtk/AC_Kazan_DualAxeSword_Com_WeakAtk01`, attack export 6. `Notifies.LinkValue=0.33789843`, `EndLink.LinkValue=0.4137547` seconds. `Size=(21,17,80)`, `BoneName=Weapon_L`, `RelativeOffset=(0,0,50)` cm. 원본 파일은 `Saved/Extracted/InGame_Playback_20261002/Metadata/` 아래 동일 package JSON이다. |
| Box 크기 계산·검증 | `Original/BoxSemantics.json`. `PostCleaningAttackInfo.AttackBoxList[].Value.LocalCenterPos/LocalRotator`, `Size`, `RelativeOffset`, `AbsoluteOffset`, 원본 철자 `RelativeRotatoion`과 `PostCleaningAttackInfo.Bounds`를 사용했다. 116/116 구간의 Bounds가 0.001cm 비교 허용 오차 안에서 재구성됐다. 0.001cm는 수치 비교 정밀도이며 gameplay 튜닝값이 아니다. |
| Box center/rotation 계산 | `C = LocalCenterPos + Qraw.Rotate(RelativeOffset) + AbsoluteOffset`, `Q = Qraw × Qrelative`. `Size`를 그대로 Box half extent로 사용한다. baked LocalCenterPos는 최종 충돌 중심이 아니라 부착점 transform이다. |
| Weak Composite 시간 변환 | `AssetAudit/CurrentNodeMapping.json`의 `timing_contract`, 원본 AC `DilationCurve.DilationAnimPositions[].T_Original/T_Dilation`. dilation 결과에 `contract.duration / authored_duration`을 적용한다. Weak01 전체 baked duration 3.4333333333s, authored 3.4326434135s를 유지해 raw 0.33789843s → current 0.3075364714s이다. 현재 user crop 2s는 범위 자르기에만 사용한다. |
| 다른 retime 시간 변환 | 원본 `AnimationTrack.AnimSegments`로 `sourceCA = AnimStartTime + (rawAC - StartPos) × AnimPlayRate`를 구한다. `Metadata/InGamePlayback_20261002/PlaybackPlan.json`의 exact package에 해당하는 `inverse_map`에서 sourceCA→playback을 보간하고 `target_duration/authored_duration`을 적용한다. 이후 현재 Sequence RateScale·montage AnimPlayRate·occurrence offset을 적용한다. 현재 crop 길이로 전체 시간축을 압축하지 않는다. |
| 현재 actor 좌표 변환 | `Original/CoordinateCrosscheck.json` 및 `PoseWeak01.json`. 원본 PSA Root 이동 제거 후 yaw −90°와 baked 부착점 비교에서 첫 위치 오차 1.780cm, 회전 오차 1.014°. native current pose의 retimed 시각도 방향을 뒷받침한다. 정확한 원작 native frame 코드는 미확인이고 기존 PSA/임포트의 잔차는 남아 있다. |
| 현재 BP 설정 | `AuthorReport.json.mesh_relative_transform`: 현재 `BP_Player` mesh relative Z=-88cm, yaw=-90°, scale=.01. baked key에는 relative location만 한 번 적용한다. 원본 metadata cm에 .01 또는 yaw를 다시 적용하지 않는다. 현재 pose fallback에는 실제 mesh scale/rotation을 적용한다. 이는 현재 프로젝트 설정이며 원작 직접값이 아니다. |
| 원작 raw 피해 값 | `Original/Source/.../SD_Kazan_DualAxeSword_Com_WeakAtk01.json`의 `AttackInfo.SkillPowerBonus=100000`, `StaminaAttackRate=3000` 등. 원작 절대 HP/Stamina 피해 공식·divisor는 미확인이다. 현재 10/5 피해를 이 raw 값의 환산으로 표현하지 않는다. |

`AssetAudit/CurrentNodeMapping.json`에는 현재 node/sequence와 원본 CA/AC 관계, 전체 inverse map과 선택 근거가 있다. 최종 작성 결과는 `AuthorReport.json`의 각 window에 원본·현재 시간, rate, crop 정책, geometry 방식, key 수·extent를 기록한다. 에셋 `Source` 문자열도 이를 보유한다.

### 임시 해석과 원작 미확인 범위

- **Cylinder:** 원본 Spinning 예의 `Size=(200,50,100)`, `CylinderShapeInfo.EndRadius=200`은 직접 확인했다. 그러나 조사한 Cylinder 34개 모두 유효한 baked Bounds가 없어 radius/height 소비 방식은 증명하지 못했다. 작성본은 반경=EndRadius, halfheight=Size.Z÷2, 즉 이 예에서는 200/50cm로 해석한다. 원본 Size.Y를 소비하지 않는 것까지 포함한 어시스턴트 임시 해석이며 실제 범위와 접촉 높이를 확인해 조정해야 한다.
- **미직렬화 Shape:** 원작 native default를 확인하지 못한 구간은 임시 Box로 작성한다. serialized Box와 같은 확정 상태로 표현하지 않는다. 의미 있는 baked geometry가 없으면 현재 root-locked bone pose와 원본 offset을 사용한다. BoneName 누락 시 Root 선택도 임시 해석이다.
- **절대 피해·Guard:** 각 window의 HP10/Stamina5, Blockable=true와 정면 반구 허용은 편집 가능한 임시값/정책이다. 원작 피해 formula·Guard 각도와 일치 검증이 아니다.
- **OverFury 첫 동작:** 현재 `CA_P_Kazan_DASword_B_OverFury_01`은 원작 `CA_P_Kazan_DualAxeSword_Yaksha_OverFury_Start`와 다른 CA다. `raw Start 구간 × 현재 0.666667s / 원작 AC 0.62s`로 같은 계열 window 비율을 적용하고 현재 bone pose에서 geometry를 얻는다. 원작과 같은 동작으로 확정하지 않으며 눈으로 타격 시점 확인이 필요하다.
- **적중 정책:** duration와 `1회 공격`·Group 설명은 원작 기록이다. 수신자별 dedup, query channel, 팀·장애물·면역 정책, callback 순서와 re-hit 내부 처리는 원작 native code를 추출하지 못했다. 현재 프로젝트의 별도 window/Group 1회 정책을 원작 내부 구현이라고 설명하지 않는다. auxiliary UltimateSlash의 `AttackCount=6/43msec`를 현재 Spinning에 임의 합치지 않았다.

### 실제 검증 결과와 한계

격리 Work cold build 및 native DEV PIE `Khazan.Combat.PlayerAttackCollision.PIE` 핵심 13개가 통과했다. 근거는 `Metadata/PlayerAttackCollision_20261008/OwnedPIEEditor.log`의 마지막 해당 test Success와 case 결과다. 첫 fixture PIE 시작 타이밍 실패는 이후 정상 시작으로 해결됐으며 초기 실패 로그도 보존한다.

| 검증 | 실제 결과 |
|---|---|
| 여러 frame의 동일 Box, 동일 Group의 두 window | 대상당 1회 HP/Stamina 피해. |
| 별도 window | 같은 대상에 두 번 피해. |
| Box/Cylinder/Sphere 적중·범위 밖 제외 | 정상 capsule을 사용한 controlled range case 통과. |
| HP0 제외, HP/Stamina 하한 | 무효 추가 피해 제외와 기존 clamp 통과. |
| 중간 취소 후 늦은 window | 취소 이후 추가 피해 없음. |
| 작성된 Spinning / OverFury | HP/Stamina 변화와 각각 대상별 7회/19회 적중 확인. 이 총횟수 검증은 큰 target capsule을 사용했으므로 정상 크기 Monster가 모든 window에 실제 접촉한다는 증거는 아니다. |

실제 입력 회귀는 `ComboRegression/SuiteState.json`과 case별 `Runtime_*.json`에 보존했다. buffered/committed Weak→Spinning, Charge02→03/자동04, RB→OverFury, Weak05의 일반/committed 후속 전환 등 **양성 경로 6개**를 관측했다. `weak5_y_early`는 Weak01~05만 관측했고 너무 이른 Y로 후속 montage가 나타나지 않았다. probe에는 `Target montage/section not observed before QA deadline` 오류 문자열이 남으므로 이 음성 관측을 양성 전환 성공과 섞어 7개 무조건 PASS로 표현하지 않는다. 별도 최종 판정 보고가 추가되면 그 출처를 후속 기록에 붙인다.

기존 `Khazan.Guard.PIE`, `Khazan.Heal.PIE`는 각각 Success이며 `GuardHealRegression.json`에 기록했다. 실제 일반 Weak 공격의 정상 크기 target/debug helper 최종 검증은 이 기록 시점에 완료 근거가 없어 주장하지 않는다. draw 코드와 작성본 checkbox 활성은 확인했지만 시각적 원작 일치 판정까지 완료한 것은 아니다.

### Main 전달과 정확한 후속 절차

현재는 private 구현·저장 에셋·격리 검증 단계까지 완료했다. root가 최신 Main Source/asset SHA와 다른 작업의 변경을 비교한 뒤 필요한 파일만 선택 전달하고 최종 build/saved audit 결과를 하단에 추가한다. 이 문서 작성 시 Source 89개 경로를 비교했고, 비소유 파일은 `SourceBefore.json`과 `LatestMainSourceSync.json`의 Snow2 변경을 반영한 기준과 일치했다. 새 비소유 차이는 없었다.

Main 실행 에디터가 구 schema를 로드한 상태에서 새 property가 즉시 사용 가능하다고 가정하지 않는다. 전달 완료·native 재로딩/재시작 결과를 확인한 뒤 위 DataAsset 경로에서 window/피해/debug 옵션을 검토한다. 현재 user montage crop과 다른 채팅의 수정은 유지한다. 이후 정상 크기의 여러 Monster에 실제 플레이 입력으로 범위·첫 OverFury 타격 시점·Cylinder 높이를 확인하고 임시값을 조정한다. 원작 값이 추가 확보되면 raw 단위·조건·변환 의미가 일치하는지 확인한 뒤 해당 임시 설정만 교체한다.

작업이 중단되면 이 문서의 private 완료 범위와 `ENGINEERING_WORK_CONTINUITY.md`의 마지막 기록부터 재개한다. 이미 성공한 추출/작성/fixture 전체를 근거 없이 반복하지 않고, Main 전달 영수증·빌드·saved 검증이 추가됐는지 먼저 확인한다.


## 2026-10-08 — Main 선택 반영 및 최종 검증 완료 (15:55 KST)

- 최신 Main Snow 변경 2개를 private Source에 읽어들인 뒤 실제 compile/link를 수행했다. `Build_FinalMatchedMainSource.log`는 11개 action과 Result: Succeeded를 기록한다. 이 module로 새 Work process에서 native 충돌 13개 case를 재실행해 Success를 확인했다(`FrozenFinalPlayerCollisionPIE.log`).
- 정상 실제 입력 전환 6건과 Weak05 조기 입력 거절 1건의 최종 판정을 `VerifiedComboExpectations.json`에 남겼다. Y press/release 9.701347~9.752812s는 현행 InputOpen 9.884994s 이전이며, raw timeout 기록을 성공 문자열로 고치지 않았다. Guard/Heal Success는 `FrozenRegressionPIE.log`와 `GuardHealRegression.json`에 보존한다.
- 검증된 기존 runtime Source 3개, DEV fixture 1개, Player ComboDefinition 및 신규 공통 Damage GE 2개를 Main에 선택 반영했다. 다른 Source/Config/Player BP·ABP·무기·physics/Monster 초기화 등 146개 보호 파일은 그대로 유지됐다. Main/Work 전체 Source hash 일치도 확인했다. `PreparedDeliveryManifest.json`, `SourceContentDelivered.json` 및 `Before/`가 정확한 범위와 이전 bytes를 보존한다.
- 실행 중 Main PID31344의 stock DLL은 바꾸지 않았다. 일치하는 private build를 별도 `UnrealEditor-KhazanPlayerAttackCollision20261008.dll/.pdb`로 전달하고 module manifest만 다음 실행에 맞췄다. BuildId 55116800과 기존 stock binary는 보존했다(`NativeAliasDelivered.json`). 기존 Main에 compile/PIE/native reload/save-all/close를 실행하지 않았다.
- 별도 새 Main PID2512가 전달 module을 실제 로드했다. 저장된 26 nodes 중 공격 node18, windows60, keys553, green draw=true, instant GE의 HP/Stamina SetByCaller modifier 2개, BP_Player UpToDate와 dirty content 없음이 모두 확인됐다(`MainFreshSavedReadback.json`, `MainFreshSavedEditor.log`). 읽기 전용 검사 후 이 소유 프로세스는 정상 종료했다.
- 현재 열린 Main PID31344는 여전히 `UnrealEditor-Khazan.dll`을 로드한다. **Main을 정상 재시작한 다음 Player ComboDefinition을 편집/PIE한다.** 구 native schema로 새 Player ComboDefinition을 다시 저장하지 않는다. 다른 작업용 editor도 새 schema를 반영한 native build 없이 해당 DA를 저장하지 않는다.
- 추가 화면 캡처 helper는 Python에 노출되지 않은 AbilitySystemBlueprintLibrary API를 사용해 완료하지 못했다. `ActualWeakNormalTarget.json`에 helper 실패를 기록했고 실제 gameplay 검증에 포함하지 않았다. 녹색 draw의 최종 화면 캡처나 정상 크기 target에서 모든 authored window의 시각적 정합 검증을 완료했다고 표현하지 않는다. 기존 native shape/range 검사 및 연타 횟수 검증과 구분한다.
- 남은 사용자 튜닝/원작 확인 범위는 Cylinder 높이, 미직렬화 Shape, OverFury 첫 CA 매핑, 절대 피해량/Guard 정책이다. 새 기능 추가나 자동 재작성 없이 기존 window editor 값으로 조정한다. 전체 재추출·재임포트는 필요하지 않다.

## 2026-10-15 — 초록색 공격 콜라이더 디버그 표시 제거

사용자 최신 요청으로 실행 중 초록색 Box/Cylinder/Sphere 표시를 삭제했다. `KZComboActionAbility.cpp::QueryAttackCollision`의 DrawDebug 분기와 전용 include만 제거했으며 diff는 기존 파일 1개/10줄 삭제다. Player와 이를 상속한 MonsterPatternAbility가 같은 경로를 사용하므로 양쪽 공격 표시가 함께 사라진다. Overlap/Sweep/유한 원통 판정, HP·Stamina 피해, 공격창·shape·크기·시간·Group과 에셋은 변경하지 않았다.

기존 `bDrawAttackCollision`/getter는 저장 에셋과 기존 DEV 소비의 호환성을 위해 남아 있지만 실제 게임의 그리기 경로에서는 더 이상 사용하지 않는다. 위 과거 절의 체크박스로 초록색 표시를 켤 수 있다는 설명은 이 변경 이후 적용되지 않는다. production Source의 DrawDebug/Green/EDrawDebugTrace 검색 잔여 0, Main stock build Succeeded/Target up to date다. 새 PIE·화면 검수는 실행하지 않았다. 정확한 소스·모듈 SHA/백업/빌드 로그는 `Metadata/AttackCollisionDebugRemoval_20261015/FinalVerification.json`이다.
