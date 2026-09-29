# LockOn Target Anchor Audit — 2026-09-29

## 조사 범위

LockOn 대상의 높이를 `ActorLocation`이나 공통 스켈레톤 소켓으로 정할 수 있는지 확인하기 위해 저장된 원작 Enemy metadata와 현재 복원된 SkeletalMesh 소켓을 표적 조사했다. 게임 C++, Blueprint, SkeletalMesh와 Skeleton은 수정하지 않았다. 기계 판독 요약은 `Saved/ImportReports/KZ_LockOnTargetAnchorAudit_20260929.json`에 있다.

## 결론

- 조사한 현재 Enemy SkeletalMesh에는 `LockOnTarget`, `LockOn`, `Target`이라는 공통 LockOn 소켓이 없다.
- Yetuga, ApesStoneHandElite, WildDog, WildBoar에는 머리 뼈의 `LookAt01` 소켓이 있지만, 원작 Character Blueprint에는 이 소켓과 별도로 `xxLockOnSphereComponent`가 존재한다. 따라서 `LookAt01`을 LockOn 정본으로 재해석하지 않는다.
- 원작에서 직접 확인된 LockOn 기준은 캐릭터별 `xxLockOnSphereComponent`다. 여러 Character CDO에 `bUseRotToTargetLockOnSphereLocation=true`가 함께 기록돼 있다.
- 현 프로젝트 gameplay 구현은 원본 class의 미확인 sphere radius나 선택 로직을 추정하지 않고, `AKZMonster`가 소유하는 캐릭터별 `LockOnTargetPoint` SceneComponent 한 점으로 이 위치 계약을 옮긴다. 기본 부착 부모는 capsule/root이며 각 Monster BP가 위치를 저작한다.
- 원작 상대 위치는 원본 Character BP의 root/capsule 계약 안에서만 의미가 있다. 현재 gameplay capsule과 mesh transform이 원본과 일치하는지 확인하기 전에는 아래 원시 값을 그대로 복사하지 않는다.

## 원작 LockOn 컴포넌트 근거

아래 값은 저장 metadata의 `xxLockOnSphereComponent.Properties.RelativeLocation` 원시 값이며 Unreal 상대 위치 단위다.

| Character source | RelativeLocation | 추가 근거 |
| --- | ---: | --- |
| `CB_Yetuga` | `(-16.125305, -9.706822, 6.2725754)` | `bUseRotToTargetLockOnSphereLocation=true` |
| `CB_ApesStoneHand_E` | `(-30.159283, -12.388883, -0.000039507504)` | 같은 flag `true` |
| `CB_PicaroonDog` | `(3.7001915, -59.362957, -2.9828582)` | 같은 flag `true` |
| `CB_WildBoar_New` | `(0, 5, 0)` | 같은 flag `true` |
| `CB_EmpireSword_Early` | `(-9.964111, -0.000011901322, -0.000004798174)` | 같은 flag `true` |
| `CB_EmpireMagic` | `(-5.3863754, 0.00018589199, -0.000000834465)` | 같은 flag `true` |
| `CB_EmpireHalberd_E_Early` | `(-16.584461, -0.37706015, 0.000051638188)` | 같은 flag `true` |

Yetuga/Apes/WildDog/WildBoar 원본은 각 `Metadata/Extraction_*/SourceMetadata.zip`의 `Design/Monster/.../Base_Setting/CB_*.json`에서 확인했다. 인간형 적은 `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/.../Base_Setting/CB_*.json`에서 확인했다. BigBear의 저장 `SourceClosure.json`은 `CB_BigBear_E` export type에 `xxLockOnSphereComponent`가 있음을 확인하지만 현재 저장 report만으로 정확한 상대 위치는 복원하지 않는다.

## 현재 복원 에셋의 실제 소켓

UE 5.8 Python API로 저장 asset을 읽어 확인했다.

| 현재 SkeletalMesh | 소켓 수 | 확인된 소켓 |
| --- | ---: | --- |
| `SK_EN_Yetuga` | 7 | `Projectile-L-Hand`, `Holding`, `LookAt01`, 경험치 FX 4개 |
| `SK_EN_ApesStoneHandElite` | 7 | Yetuga skeleton과 같은 7개 |
| `SK_EN_WildDog` | 5 | `LookAt01`, 경험치 FX 4개 |
| `SK_EN_WildBoar` | 9 | `LookAt01`, 경험치 FX 4개, 코 VFX 4개 |
| `SK_EN_BigBear` | 0 | 현재 mesh-owned socket 없음 |

`LookAt01`은 위 네 메시 모두 `Bip001-Head`에 붙는다. 머리 애니메이션을 그대로 따라가는 이 소켓을 카메라 LockOn 기준으로 사용하면 피격·공격·고개 모션이 카메라 조준점에 섞인다. 별도 원작 LockOn 컴포넌트가 확인됐으므로 현재 구현도 안정된 캐릭터별 SceneComponent를 사용한다.

## 확인 한계

- `xxLockOnSphereComponent`의 class default sphere radius와 원작 Player의 후보 검색 거리·점수·카메라 보간 수치는 현재 저장 metadata에서 확인하지 못했다.
- 현재 Art Blueprint는 복원/미리보기 자산이며 `AKZMonster` gameplay 기반과 LockOn anchor를 아직 연결하지 않았다.
- 읽기 전용 UE 검사 Python은 정상 완료했지만 commandlet process는 기존 `/Script/GameFeatures.GameFeatureData` AssetManager ensure 때문에 종료 코드 1을 반환했다. 소켓/카메라 결과 파일은 스크립트 완료 뒤 생성됐으며 asset save는 수행하지 않았다.
