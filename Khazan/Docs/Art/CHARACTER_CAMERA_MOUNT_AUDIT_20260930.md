# Character camera mount 감사 — 2026-09-30

## 1. 목적과 범위

현재 Player와 HeinMach 보스에 카메라를 붙일 수 있는 저장 지점이 있는지, 그 지점이 일반 gameplay camera용인지 컷씬용인지 구분했다. 현재 Unreal 애셋과 Blueprint CDO, 게임 Source, 저장된 원작 ActorX/FModel metadata를 읽기 전용으로 대조했다.

- 현재 Player: `/Game/_Art/Player/Character/Meshs/SKM_Player`, `/Game/_Art/Player/Character/Bluprints/BP_Player`
- 현재 보스/대조군: Yetuga, BigBear, ApesStoneHandElite의 SkeletalMesh와 Yetuga/BigBear Blueprint
- 원작 자료: Player PSK/PSA, Yetuga·BigBear Skeleton JSON, 저장된 Level JSON 138개
- 게임 Source/Content asset은 수정하거나 저장하지 않았다.

## 2. 판정 요약

| 대상 | 현재 저장 지점 | Unreal attach 가능 | 확인된 실제 용도 | 판정 |
|---|---|---:|---|---|
| Player `Cine_Cam_Start` | `Root` 직속 reference bone | 예 | 저장된 Level metadata에서는 사용처 미확인 | 컷씬 부착 후보 |
| Player `Cine_Cam_End` | `Root` 직속 reference bone | 예 | 원작 StormPass `CineCameraActor1`이 이 이름으로 Player mesh에 부착 | 확인된 컷씬 부착점 |
| Player `LookAt01` | 머리 하위 reference bone | 예 | 시선 기준 이름 | camera mount로 판정하지 않음 |
| Yetuga `LookAt01` | 머리의 authored socket | 예 | 시선/머리 기준 계열 | camera mount로 판정하지 않음 |
| BigBear | 현재 authored socket 0개, camera 명칭 bone 없음 | 아니요 | 원작 Skeleton metadata에도 camera/cine 명칭 없음 | 전용 부착점 없음 |
| ApesStoneHandElite `LookAt01` | 머리의 authored socket | 예 | Yetuga와 같은 시선 기준 계열 | camera mount로 판정하지 않음 |

핵심은 Player의 `Cine_Cam_Start`와 `Cine_Cam_End`가 현재 `USkeletalMeshSocket` 객체가 아니라 **reference bone**이라는 점이다. `USkeletalMeshComponent::DoesSocketExist()`는 두 이름 모두 `true`를 반환했다. 따라서 `AttachToComponent`와 Blueprint Attach 노드의 Socket Name에 bone 이름을 넣는 방식으로 실제 부착할 수 있다.

## 3. 현재 Player 애셋

`SKM_Player`는 reference bone 227개와 authored socket 0개를 가진다. camera 관련 reference pose는 다음과 같다.

| 이름 | bone index | 부모 | current local translation (cm) | current local rotation (deg) |
|---|---:|---|---|---|
| `Cine_Cam_Start` | 219 | `Root` | `(0, -180, 198)` | `Pitch -10, Yaw 90, Roll 0` |
| `Cine_Cam_End` | 220 | `Root` | `(0, -500, 250)` | `Pitch -10, Yaw 90, Roll 0` |
| `LookAt01` | 32 | `Bip001-Head` | `(6.3021, -10.9738, 0.00034)` | 시선용 reference orientation |

위 값은 **현재 import된 reference pose의 직접 확인값**이다. `BP_Player`의 mesh component는 capsule 아래에서 location `(0, 0, -88)`, yaw `-90°`, scale 약 `0.009`를 쓴다. 따라서 source bone 숫자만 복사해 컷씬 framing을 확정하지 않고, 실제 Level Sequence shot에서 component transform까지 합성해 확인해야 한다.

현재 일반 camera 조립은 다음과 같다.

```text
CollisionCylinder (Capsule)
└─ SpringArm  [socket=None, arm=600 cm, Pawn Control Rotation=true]
   └─ Camera  [socket=None, FOV=90°]
```

camera lag와 camera rotation lag는 현재 모두 꺼져 있다. 즉 일반 gameplay camera는 animated Player mesh나 `Cine_Cam_*` bone을 따라가지 않고 capsule을 기준으로 움직인다. 이 구성은 locomotion pose의 상체 흔들림을 camera에 직접 전달하지 않는다.

## 4. 원작 Player와 컷씬 근거

원작 `C_P_Kazan.psk`의 `REFSKELT` 226개 record 중 다음 항목이 있다.

| source record | 부모 | source reference translation |
|---|---|---|
| 170 `Cine_Cam_Start` | `Root` | `(0, 180, 198)` |
| 171 `Cine_Cam_End` | `Root` | `(0, 500, 250)` |

source와 current import의 Y 부호는 반대다. ActorX→Unreal import 좌표 변환과 현재 BP mesh transform을 함께 고려해야 하므로 source 수치를 current component offset으로 직접 대입하지 않는다. 원작 `CA_P_Kazan_Stand.psa`의 `BONENAMES` 1,528 record에는 `Cine_Cam_Start`, `Cine_Cam_End`, `LookAt01`이 없다. 저장 자료 범위에서는 이 항목들이 Stand animation track이 아니라 mesh/reference 쪽의 정적 부착 helper라는 해석을 지지한다. PSK만으로 원작 package 안에서의 최종 UObject 형식까지 복원했다고 보지는 않는다.

저장된 Level JSON 138개를 전수 검사했고 parse 실패는 없었다. `CineCameraActor`는 9개였다.

- HeinMach Opening01 4개, Opening02 4개는 rig/root 또는 연출용 static mesh component에 직접 붙으며 Socket Name은 없다.
- StormPass `StormPass_Cinema_LvEvent01`의 `CineCameraActor1` root는 Player `xxSkeletalMeshComponent0`에 붙고 `AttachSocketName="Cine_Cam_End"`를 사용한다. Player 부착점의 실제 사용이 확인된 사례다.
- `Cine_Cam_Start`의 직접 사용은 이 저장 Level 집합에서 찾지 못했다.

## 5. 보스 애셋과 보스 컷씬

### Yetuga

현재 본체 mesh는 reference bone 453개, authored socket 7개다. socket은 `Projectile-L-Hand`, `Holding`, `LookAt01`, 네 개의 FX 지점이며 camera/cine 명칭은 없다. `LookAt01`은 `Bip001-Head`에 붙은 머리 시선 지점이다. 같은 보스 폴더의 `SK_EN_Yetuga_IceRock`도 확인했으며 reference bone 20개, authored socket 0개, camera 명칭 후보 0개다. 현재 `BP_EN_Boss_Yetuga`에는 `CameraComponent`, `CineCameraComponent`, `SpringArmComponent`가 없다. 원작 Yetuga Skeleton JSON의 socket 목록도 같은 7개이며 camera 전용 socket은 없다.

### BigBear

현재 mesh는 reference bone 79개, authored socket 0개이며 camera 명칭 후보가 없다. 현재 `BP_EN_BigBear_V01`에도 camera 또는 spring arm component가 없다. 원작 Skeleton JSON에는 `LookAt01`, `Holding`, 네 개의 FX socket이 있지만 camera/cine 명칭은 없다. 현재 import에서 원작의 이 6개 socket이 복원되지 않은 차이는 별도 애셋 복원 이슈이며, camera 부착점 유무 판정은 달라지지 않는다.

### 보스 컷씬 metadata의 한계

`HeinMach_Cine_BossStart.json`과 `HeinMach_Cine_BossEnd.json`에는 `bUseCutSceneLevelSequence=true`가 있으나, 해당 Level export 안에는 직렬화된 `CineCameraActor`와 `AttachSocketName`이 없다. 검사한 138개 Level JSON에서도 보스 mesh에 직접 붙은 camera를 찾지 못했다. 카메라 transform이나 binding이 외부 LevelSequence package에 있을 가능성은 있지만, 현재 저장 metadata만으로는 그 방식을 확정할 수 없다.

## 6. LockOn camera와의 관계

현재 `UKZLockOnComponent`는 target 검색 때 `GetPlayerViewPoint()`로 실제 view를 읽는다. 매 프레임 회전의 활성 경로는 Player actor 위치를 pivot으로 삼아 Monster의 `LockOnTargetPoint`를 향한 rotation을 계산하고 `SetControlRotation()`을 호출한다. camera 위치를 pivot으로 쓰던 블록은 현재 주석 상태다. 어느 경로에도 Camera/SpringArm을 target이나 socket에 attach하는 코드는 없다.

`AKZMonster::LockOnTargetPoint`는 capsule에 붙은 `USceneComponent`이며, camera가 바라볼 target anchor다. camera가 올라가는 mount가 아니다. 따라서 아래 세 지점을 서로 바꾸어 쓰지 않는다.

- `Cine_Cam_Start/End`: Player 컷씬 camera 부착 후보
- `LookAt01`: 얼굴/머리 시선 기준
- `LockOnTargetPoint`: gameplay LockOn 조준점

## 7. 적용 방향

- 일반 gameplay는 현재의 `Capsule → SpringArm → Camera` 구성을 유지한다. 캐릭터 animation bone에 camera를 상시 붙이면 pose 진동과 root/mesh transform이 그대로 camera에 전달된다.
- Player 컷씬은 별도의 `CineCameraActor`를 Level Sequence가 제어하고, 필요한 shot 구간에만 `Cine_Cam_End` 또는 검증 후 `Cine_Cam_Start`에 attach할 수 있다. 부착된 shot 동안에는 해당 bone을 hard-follow하며, shot 종료 시 view target과 attachment를 복구해야 한다.
- 보스에 붙어 움직이는 shot이 실제로 필요하면 보스 Blueprint의 안정된 root/capsule 아래에 명시적 `CinematicCameraAnchor` SceneComponent를 두거나, animation을 따라야 하는 shot에만 전용 authored socket을 만든다. `LookAt01`과 `LockOnTargetPoint`는 재사용하지 않는다.

이번 감사에서는 위 구조를 제안만 했고 보스 Blueprint나 Skeleton에 새 지점을 만들지 않았다.

## 8. 검증 자료

- 현재 UE 애셋 report: `Saved/ImportReports/KZ_CharacterCameraMountAudit_20260930.json` (`status=passed`)
- 원작 ActorX/FModel report: `Saved/ImportReports/KZ_OriginalCharacterCameraMountAudit_20260930.json` (`status=passed`)
- 현재 애셋 감사: `Scripts/Character/audit_character_camera_mounts.py`
- 원작 자료 감사: `Scripts/Character/audit_original_character_camera_mounts.py`
- 현재 UE 감사 본문은 완료됐으며 commandlet의 최종 exit 1은 기존 `/Script/GameFeatures.GameFeatureData` AssetManager ensure다. report는 예외 없이 `passed`로 저장됐다.
- 원작 metadata 감사는 process exit 0으로 완료됐다.
