# Enemy 에셋 라이브러리 구조 정리 — 2026-09-15

## 결과

`/Game/_Art/Enemies`의 현재 UE 에셋 1,940개를 실제 참조와 Asset Registry 기준으로 정리했다. 비어 있던 import/source/archive 폴더와 이동 후 비게 된 상위 폴더까지 63개 디렉터리를 제거했다. 살아 있는 에셋은 삭제하지 않았으며, 옛 루트에 있던 공용 에셋 10개와 공용 애니메이션 9개, MageHard 변형 2개를 UE `AssetTools.rename_assets`로 현재 구조에 옮겼다.

최종 구조는 다음과 같다.

```text
/Game/_Art/Enemies
├─ Metadata/Structure_20260915
├─ HeinMach
│  ├─ Bosses/Yetuga
│  ├─ Humanoids
│  │  ├─ Archer
│  │  ├─ HalberdElite
│  │  ├─ HeavySwordsman
│  │  ├─ SwordShield
│  │  └─ Swordsman
│  ├─ Shared
│  │  ├─ Animations/Playback
│  │  ├─ Equipment
│  │  ├─ Materials
│  │  ├─ PoseCarriers
│  │  ├─ Skeletons
│  │  └─ Textures
│  ├─ Metadata
│  └─ Preview
├─ OtherRegions/Humanoids
│  ├─ EliteShield
│  └─ Mage
└─ Shared
   ├─ Beasts
   │  ├─ BigBear
   │  ├─ WildBoar
   │  └─ WildDog
   └─ Elites/ApesStoneHandElite
```

각 캐릭터 폴더 안에서는 `Animations/Playback`, `Blueprints`, `Materials`, `Meshes`, `Skeletons`, `Textures`, `Metadata`, `Preview`처럼 역할별 하위 폴더를 유지한다. 특정 캐릭터에 속하지 않고 여러 인간형이 소비하는 자산은 `HeinMach/Shared`에 둔다.

## 이동 내역

| 구분 | 이전 위치 | 현재 위치 | 수량 |
|---|---|---|---:|
| HeinMach 공용 장비 | `HeinMach/Empire/Equipment` | `HeinMach/Shared/Equipment` | 4 |
| HeinMach 공용 rig/pose carrier | `HeinMach/Empire/{Skeletons,Parts/PoseCarrier}` | `HeinMach/Shared/{Skeletons,PoseCarriers}` | 2 |
| HalberdElite | `HeinMach/HalberdElite` | `HeinMach/Humanoids/HalberdElite` | 4 |
| 공용 재생 애니메이션 | `HeinMach/Humanoids/Shared/Animations/Playback` | `HeinMach/Shared/Animations/Playback` | 9 |
| MageHard 외형 | `OtherRegions/Humanoids/MageHard` | `OtherRegions/Humanoids/Mage` | 2 |

`MageHard`는 삭제 대상이 아니라 Mage의 난이도 변형이다. 구분에 필요한 `BP_EN_MageHard_*`, `SK_EN_MageHard_*` basename은 유지하고 폴더만 Mage 가족 아래로 합쳤다. HalberdElite도 기존 정식 병종 폴더와 옛 최상위 폴더가 중복되어 후자를 전자에 합쳤다.

이동 전 옛 Empire skeleton과 pose carrier는 각각 수백 개 애니메이션/메시에서 사용 중이었다. 이름이나 폴더만 보고 Legacy로 삭제하면 전체 인간형 라이브러리가 끊기므로 참조를 보존해 이동했다. `L_HeinMach_EnemyCatalogue`는 옮긴 MageHard Blueprint generated class를 새 경로로 직렬화하기 위해 다시 저장했다.

## 빈 폴더와 Legacy 처리 기준

처음 확인한 빈 leaf 폴더는 37개였다. `_ImportStaging`, `SourceSequences`, `PlaybackClips`, `SharedSourceReferences`, `EliteShield_SourceReferences`, `Archive/FaceVariants_20260908`와 빈 조립/파츠 폴더가 포함된다. 에셋 이동 뒤 비게 된 `Empire`, 옛 `HalberdElite`, `Humanoids/Shared`, `MageHard` 상위 계층까지 하위부터 제거해 최종 빈 디렉터리와 Legacy 명칭 디렉터리는 모두 0개다.

`LegacyIdleDuplicates.json`, `LegacyAssetMoves.json`, `ArchiveSummary.json`은 UE 런타임 에셋이 아니라 과거 삭제·이동·원본 보관의 근거다. 이 기록은 삭제하지 않았다. 과거 import manifest와 builder의 옛 destination 역시 당시 작업을 재현하는 이력으로 유지하며, 현재 경로 조회에는 새 `Metadata/Structure_20260915`만 사용한다.

## 현재 조회 자료

`Content/_Art/Enemies/Metadata/Structure_20260915`에 다음 자료를 발행한다.

- `CurrentAssets.json`: 현재 1,940개 package path, class, 파일 SHA-256
- `AssetLibrary.csv`: 검색 가능한 현재 에셋 표
- `RenameMap.json`: 옛 경로 21개와 현재 경로의 정확한 대응
- `FolderStructure.json`: family·폴더·class별 수량
- `EmptyDirectoryCleanup.json`: 제거 전후 디렉터리 기록
- `ValidationSummary.json`: fresh Unreal 감사 결과
- `WorkspacePreservation.json`: 작업 범위 밖 사용자 변경 보존 기록

후속 C++·Blueprint·도구가 정확한 현재 경로를 필요로 하면 `CurrentAssets.json` 또는 `RenameMap.json`을 사용한다. 2026-09-09 이전 metadata의 destination을 현재 경로로 간주하지 않는다.

## 검증

이동 전 영향 범위 678개, 468,397,155바이트를 `Desktop/카잔/EnemyExtracts/EnemyAssetStructureCleanup_20260915`에 복사하고 SHA-256을 확인했다. Git 이력과 별도로 이동 전 package를 직접 복원할 수 있다.

별도 Unreal 5.8 commandlet에서 다음을 확인했다.

- 총 1,940개: AnimSequence 1,354, Blueprint 28, Material 17, MaterialInstanceConstant 113, SkeletalMesh 35, Skeleton 16, Texture2D 371, World 6
- redirector 0, 빈 디렉터리 0, Legacy 명칭 디렉터리 0, 누락된 Enemy 내부 dependency 0
- 영향 없는 Enemy package 1,262개의 SHA-256 일치
- 영향 범위 678개 전부 로드 성공
- 애니메이션 1,354개의 Skeleton, rational FPS, sample/frame 수, 길이, RateScale, root motion/lock 설정 일치
- SkeletalMesh 35개의 Skeleton, bone 수, LOD 수, material slot 이름·참조 일치
- Blueprint 28개의 SkeletalMeshComponent mesh·animation·재생률·loop·transform·material·collision 계약 일치
- 수치 계약 최대 오차 0, 계약 불일치 0
- HeinMach, Yetuga, BigBear, WildDog, WildBoar, ApesStoneHandElite 카탈로그 6개 로드 성공
- 최종 commandlet process exit 0, `Success - 0 error(s)`

감사 시작 시 Enemy dirty package는 0개였다. 카탈로그를 포함해 전체 계약을 읽는 과정에서 기존 Yetuga/Apes 애니메이션 197개가 `PostLoad` 파생 데이터 때문에 메모리에서 dirty로 표시됐지만 감사 도구는 이를 저장하지 않았다. 디스크의 애니메이션 데이터나 재생 속도는 변경하지 않았다.

이번 작업은 Enemy Content 경로와 참조만 정리했다. 캐릭터 C++, Player Blueprint, 프로젝트 Config를 수정하지 않았다. 작업 도중 별도로 변경된 `KhazanLocomotionComponent.h`는 감지한 상태 그대로 보존하고 이 Art 변경에 포함하지 않는다.

재현 도구는 `Scripts/Enemies/inspect_enemy_asset_structure.py`와 `Scripts/Enemies/*_enemy_asset_structure_cleanup.py`다. 적용은 반드시 외부 백업 후 독립 Unreal 프로세스에서 수행하고, 완료 판정은 fresh audit의 Asset Registry와 계약 비교 결과를 따른다.
