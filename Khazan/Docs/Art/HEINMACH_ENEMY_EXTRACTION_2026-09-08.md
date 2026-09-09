# HeinMach 튜토리얼 인간형 Enemy 추출·외형 조립

## 2026-09-08 대상과 실제 결과

사용자 요청은 HeinMach에서 DAS 기본 전투를 배우는 구간의 인간형 Enemy 외형·장비·머티리얼·텍스처·메타데이터를 추출하고, 조합하여 프로젝트에 임포트하는 것이다. 이번 결과는 **외형용 Actor Blueprint와 SkeletalMesh 라이브러리**다. 공격/피격/AI/전투용 Character 구현을 완료한 기록이 아니다.

원본 `HeinMach_Spawn_Main01`의 actor 1066 `SA_EmpireSword_Early3_Item`은 `CB_EmpireSword_Early`와 `AI_EmpireSword_Tutorial_Signal_1`, actor 1055 `SA_Empire_SwordShield_2`는 `CB_Empire_SwordShield`와 `AI_Empire_SwordShield_Tutorial_Signal_1`을 참조한다. 이름이 비슷한 다른 적을 튜토리얼 대상으로 대체하지 않았다. 원본 47개 spawn handler의 참조는 `Metadata/SourceSpawnActors.json`에 보존했다.

HeinMach에서 별도로 확인되는 `CB_EmpireHalberd_E_Early`도 `HalberdElite`로 분리했다. 원본 이름은 Halberd이며, 기본 튜토리얼 검병의 도끼 변형이라고 단정하지 않는다.

| 결과 | 수량 | 내용 |
|---|---:|---|
| 검병 외형 | 40 | 머리 2 × 얼굴 5 × 상의 2 × 하의 2 |
| 검·방패병 외형 | 4 | 투구 1 × 상의 2 × 하의 2. 원본 목록에 없는 얼굴은 추가하지 않음 |
| 할버드 정예 | 1 | 본체 `C_M_HalberdV2`, 무기 `C_I_Halberd_WeaponV2` |
| 조합된 전신 SkeletalMesh | 44 | 검병/방패병의 source 허용 파츠 조합 |
| 개별 source SkeletalMesh | 17 | 파츠·장비·할버드 본체·pose carrier 포함 |
| Texture2D | 149 | 원본 PNG와 원본 패키지 참조 보존 |
| source 대응 머티리얼 | 36 | replacement Material 3 + MaterialInstance 33 |
| 보조 머티리얼 | 1 | 파츠 분석용 carrier의 투명 처리 |
| 대기 AnimSequence | 3 | 검병, 방패병, 할버드의 원작 클립 |
| source ActorX mesh 파일 | 49 | 원본 LOD0/LOD1/LOD2 파일. UE의 LOD 병합 완료 수가 아님 |
| source MorphTarget record | 380 | 원본 metadata/PSK 보존. UE MorphTarget 생성 완료 수가 아님 |

## 폴더와 이름

UE 루트는 `/Game/_Art/Enemies/HeinMach`다. 기존 Player 및 환경 폴더와 구분한다.

```text
Enemies/HeinMach/
  Empire/
    Assemblies/Sword/          BP_EN_Empire_Sword_H01_F01_U01_L01 ...
    Assemblies/SwordShield/    BP_EN_Empire_SwordShield_H01_U01_L01 ...
    CombinedMeshes/            SK_EN_Empire_Sword_... / SK_EN_Empire_SwordShield_...
    Parts/                    Face, Hair, Upper, Lower, PoseCarrier
    Equipment/                검과 방패의 개별 SK_EN_ 에셋
    Skeletons/                SKEL_EN_EmpireHuman
    Animation/                A_EN_Sword_Idle, A_EN_SwordShield_Idle
  HalberdElite/
    Assemblies/               BP_EN_Empire_HalberdElite
    Meshes/, Equipment/, Animation/
  Shared/Textures/            T_EN_...
  Shared/Materials/           Parents, Instances
  Preview/                   L_HeinMach_EnemyCatalogue
  Metadata/                  JSON 원본·source/target 대응표·출처·검증 자료
```

`EN`은 Enemy, `H/F/U/L`은 해당 recipe의 Head/Face/Upper/Lower 목록에서 **1부터 시작하는 선택 번호**다. 번호를 원작 런타임의 랜덤 seed 또는 actor 고정 variant ID로 해석하지 않는다. 각 Blueprint는 `EnemyBody` 하나가 전신 포즈를 재생하고 `EnemyWeapon_R`, 방패병의 `EnemyShield_L`을 부착한다. 파츠 원본은 별도 메시로 유지한다.

확인용 맵에서 원하는 `BP_EN_...`를 선택하거나 다른 레벨에 같은 Blueprint를 배치할 수 있다. 확인용 맵은 기존 HeinMach/StormPass 환경 맵을 수정하지 않고 별도로 만들었다. 조명·간격은 전시용이며 원작 레벨의 전투 배치가 아니다. 대기 애니메이션을 계속 재생하려면 시뮬레이션하거나 SkeletalMesh/Animation 에디터에서 확인한다. 이 Actor에는 적 AI나 피격 판정이 없다.

## 원작 근거와 수치 계약

이 절의 `BBQ/Content/` 경로는 `Metadata/Source/` 아래 같은 경로의 JSON, 그리고 외부 추출 archive의 동일 경로로 연결된다.

- 검병 CB: `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/EmpireSword/Base_Setting/CB_EmpireSword_Early`.
- 방패병 CB: `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/Empire_SwordShield/Base_Setting/CB_Empire_SwordShield`.
- 할버드 CB: `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/EmpireHalberd_E/Base_Setting/CB_EmpireHalberd_E_Early`.
- 외형 recipe 폴더: `BBQ/Content/_Kazan_/Art/Character/CHA_Data/RandomLookInfo/Monster_HumanType/`.
- 검병 recipe는 `CD_RD_Human_Adult_M_EmpireWounded_001`, 방패병 recipe는 `CD_RD_Human_Adult_M_EmpireWoounded_SwordShield_001`이다. `Woounded`는 원본의 철자를 보존했다. 각 `Properties.*PartsList[*].Mesh`가 조합의 직접 근거다.

| 값/적용 | 출처 상태 및 정확한 근거 |
|---|---|
| 검병/방패병 scale 1.2 | 직접 확인. 각 CB의 `Default__..._C.Properties.Scale=1.2`, 무차원. 완성 Actor의 EnemyBody에 적용 |
| 무기 소켓 | 직접 확인. 검병 `WS_EmpireSword_Early_Equip`의 장비 참조, 방패병/할버드 CB의 SCS attachment. 검 `Weapon_R`, 방패 `Weapon_L` |
| 방패병 검 위치 | 직접 확인. 방패병 CB의 검 SkeletalMeshComponent `RelativeLocation=(-2.2943702, 2.0527954, 7.965602e-06)` cm |
| 방패병 검 scale | 같은 component `RelativeScale3D=(1,1,0.8)`, 무차원 |
| 본체 yaw -90° | CB 본체 SkeletalMeshComponent의 원본 상대 회전. UE 좌표로 돌아온 PSK 메시 component에 적용 |
| 원본 본체 Z -85 cm | capsule 중심 기준 원본 component offset. 완성 외형 Actor는 발 기준 원점이므로 이 offset을 적용하지 않음. 원작 Actor 전체 transform을 복원했다고 표현하지 않음 |
| 할버드 scale 1.0 | 외형 조립의 기술적 기본 scale. 해당 CDO에서 Scale override를 직접 찾지 못했으며, 원작 상속 최종값 확인으로 취급하지 않음 |
| mask clip 0.3333 | `.../CHA_Material/Material/Base/BASE_AllMaster_AK` 및 실제 source MI의 `Properties.BasePropertyOverrides.OpacityMaskClipValue`, 무차원. MI별 BlendMode/TwoSided/clip을 보존 |
| eye roughness 0.25 | 어시스턴트 임시 표시값. 원작 roughness 변환 근거 미확인. `PreviewEyeRoughness`에서 조정하며 눈의 과도한 광택/거칠기를 검수 기준으로 삼음 |

원본 대기 클립 경로는 `BBQ/Content/_Kazan_/Art/Character/CHA_Model/` 기준 다음과 같다.

| 파일 | 직접 기록 `Properties.SequenceLength` | 추출 sample 수 | UE 시간축 |
|---|---:|---:|---|
| `Monster_Human/Adult/Adult_M/Animation/EmpireSword3/CA_M_EmpSwd_Stand_F` | 7.0 s | 211 | 210 frame 구간 / 30 fps |
| `Monster_Human/Adult/Adult_M/Animation/EmpireSwordShield/CA_M_EmpireSwordShield_Stand_F` | 1.6666666 s | 51 | 50 frame 구간 / 30 fps, source float 오차 범위 |
| `Monster_Human/Named/Halberd/Animation/CA_M_Halberd_Stand_F` | 4.0 s | 121 | 120 frame 구간 / 30 fps |

fps는 `(PSA NumRawFrames - 1) / 원본 SequenceLength`로 계산한 값이다. PSA에 기록된 `NumRawFrames/Length` 계열 rate를 그대로 UE sample 간격으로 쓰지 않았다. ActorX → UE는 위치 `(X,-Y,Z)`, quaternion `(X,-Y,Z,W)`와 최상위 W 부호 복귀를 사용한다. 추출 quaternion은 `q / sqrt(dot(q,q))`로 정규화한 뒤 Sequencer controller에 넣는다. 정규화 전 골반 회전의 Euler 변환 오차를 발견하여 수정했고 원본 ActorX 파일은 변경하지 않았다.

## 조합 메시의 보존 범위

`CombinedMeshManifest.json`은 각 part의 full package key, 정점/삼각형 수, point/wedge/material offset, material slot 대응을 저장한다. 조합은 정점 위치·normal·UV0·삼각형·weight 값을 이어 붙이고 인덱스를 재배치한다. bone index는 이름으로 원작 Human Skeleton의 185개 bone tree에 매핑한다. 원본 EmptyMesh에 있던 82개 본과 전체 Skeleton의 관계는 `EnemyImportManifest.json`의 carrier normalization에 기록한다.

공유 본의 bind 위치 차이는 최대 `0.00009894371032714844 cm`였다. 이는 source float 직렬화/변환 차이의 검사 결과이며 gameplay offset으로 넣은 값이 아니다. 없는 vertex color는 neutral white, 없는 추가 UV 채널은 그 파츠의 UV0로 채운다. 이 두 보충은 조합 파일의 형식을 맞추기 위한 처리이며 원작에 그 attribute가 있었다고 주장하지 않는다. carrier의 원본 `None` 슬롯명은 UE가 `MaterialSlot`으로 정규화한다.

## 추출 파일과 재현 한계

- FModel 추출 루트의 전용 묶음: `C:/Users/user/Desktop/카잔/EnemyExtracts/HeinMach_20260908`.
- 프로젝트 작업 archive: `Saved/Extracted/HeinMachEnemies`.
- `Assets`, `Animation`, `Metadata`, `RawCookedArchive`, `Derived`를 구분하여 보존한다. 기존 FModel의 다른 추출 파일을 덮어쓰지 않는다.
- FModel에 설정된 설치 게임과 키를 로컬에서 읽는 CUE4Parse 기반 표적 exporter를 사용했다. GUI 수동 내보내기를 수행했다고 기록하지 않는다. 키는 복사하거나 보고서에 기록하지 않는다.
- 선택한 dependency closure는 327 package, missing 0, art export 168 성공이다. 별도 idle export 3 성공. raw cooked archive는 초기 식별용 관련 메타데이터까지 포함한 347 package다. 이 수를 347개의 캐릭터나 모델로 해석하지 않는다.
- 설치 Pak의 경로/크기/수정 시각과 추출 파일별 SHA-256은 `FinalExtractionReport.json`, `SourceFileHashes.json`에 보존한다. 설치 원본 snapshot을 특정하는 자료이며 판매 버전 문자열을 추정하지 않는다.

**완전 재현으로 표시하지 않는 항목:**

1. 원작 `MSM_BBQCartoon` 및 전용 material function/shader 구현은 UE 5.8 기본 렌더러에 없다. source parent chain, scalar/vector/texture 값과 원본 전체 JSON을 보존하고 DefaultLit/Unlit 표시용 material을 만들었다. 일반 재질은 `Tex_D RGB/A`, `Tex_N`, `Tex_S.R=specular`, `1-Tex_S.G=roughness`를 사용하는 표시용 해석이다. 마지막 두 채널 해석은 원작 shader topology를 직접 복구한 결과가 아니다. 눈 역시 Tex_E와 원본 eye color parameter를 사용하는 근사 그래프다.
2. 색상 preset 3개와 BoneMod/FaceShapeWeight 데이터는 보존했다. 원작 AvatarColor mask 처리, 원작 랜덤 선택 분포, 체형·얼굴 morph 적용까지 재현하지 않았다. 40/4개는 **geometry 조합 수**다.
3. 원본 LOD 전체 및 facial MorphTarget record/ActorX chunk는 추출했으나 현 프로젝트 PSK importer는 이를 UE LOD 체인·MorphTarget으로 자동 생성하지 않는다. 현재 UE 메시에는 LOD0이 있다.
4. Skeleton socket/PhysicsAsset/cloth 및 관련 설정은 원본 metadata/raw에 보존했다. 실제 weapon attachment는 사용한 bone 소켓 `Weapon_R/Weapon_L`을 확인했다. 전체 physics/cloth/ragdoll과 모든 보조 socket을 UE runtime 데이터로 재구축하지 않았다.
5. 전투 동작 전체 애니메이션 라이브러리나 원본 cooked Blueprint의 실행 로직 복원은 이번 외형 임포트 결과에 포함되지 않는다. 원본 장비·AI·animation profile 참조는 metadata에서 추적할 수 있다.

## 재개·재실행 순서

기존 에셋을 검수할 때는 재추출/재임포트하지 않고 저장된 manifest와 감사 보고서부터 읽는다. 이미 완료한 에셋에 사용자 편집이 추가되면 generator를 무조건 재실행하지 않는다.

새 환경에서의 생성 순서는 다음과 같다.

1. `.NET 10`으로 `Scripts/Enemies/EnemyExtractor/EnemyExtractor.csproj`를 restore/build한다. 현재 실행 파일은 `C:/Users/user/.dotnet/dotnet.exe`. `CUE4Parse-Natives.dll`은 FModel이 사용하는 호환 빌드를 exporter 출력 폴더에 둔다. 이번 빌드의 hash는 최종 extraction report에 있다. ACL decode에는 `LoadVirtualPaths()`도 필요하다.
2. 보존된 `InitialMetadataRequests.json`, `LookMetadataRequests.json`, `VisualMetadataRequests.json` 등을 사용해 필요한 원본 JSON을 확보한 후 `prepare_enemy_sources.py`를 실행한다. 게임 전체 검색을 다시 하지 않는다. idle 3개는 `IdleAnimationRequests.json`으로 export하고 metadata도 확보한다.
3. UE 번들 Python으로 `build_enemy_import_manifest.py` → `combine_enemy_meshes.py`를 실행한다.
4. 서로 분리된 UE commandlet에서 `import_enemy_library.py` → `import_combined_enemy_meshes.py` → `build_enemy_assemblies.py` → `audit_enemy_library.py` 순서로 실행한다.
5. `verify_enemy_render_assets.py`는 `-nullrhi` 대신 `-AllowCommandletRendering -RenderOffscreen`으로 실행한다. 생성 staging 중 외부 참조가 없는 항목만 정리한다.
6. `finalize_enemy_sources.py`로 외부 FModel archive 복사와 SHA-256 대조를 수행한다.

commandlet의 공통 인자는 `Khazan.uproject -run=pythonscript -script=<절대 script 경로> -unattended -nosound -nosplash -nop4`다. 일반 import/audit에는 `-nullrhi`를 사용한다. 기존 Editor와 MCP 포트가 충돌하지 않도록 실행 프로세스에만 `-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False`를 전달한다. bundle Python은 `C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe -X utf8`이다.

`reset_generated_enemy_assemblies.py`는 작업 중 초기 prototype을 최종 combined body 방식으로 이관할 때 사용한 일회성 도구다. 현재 version 2 Blueprint에는 동작하지 않으며 일반 재검증 단계가 아니다.

## 2026-09-08 마지막 검증과 남은 확인

- `HeinMachEnemy_LibraryBuild.json`: source 메시 17, texture 149, material 36 저장 성공.
- `HeinMachEnemy_CombinedBodies.json`: 조합 전신 메시 44 저장 성공.
- `HeinMachEnemy_AssemblyBuild.json`: Blueprint 45 저장 성공.
- `HeinMachEnemy_FreshAudit.json`: 별도 프로세스에서 source asset 참조, animation 3개의 모든 sample/bone RAW·COMPRESSED pose, 완성 Blueprint 45개의 spawn/weapon socket 검사 통과. 확인용 새 맵 저장 완료.
- 그래픽 RHI material compile 및 확인용 맵 재로드 감사는 이 절 작성 시 진행 중이다. 완료 결과는 아래 날짜별 추가 기록과 `HeinMachEnemy_RenderAssetAudit.json`을 확인한다.
- 시작 시 `ProtectedBaseline.json`에 실제 저장된 보호 hash는 HeinMach/StormPass 완성 환경 맵 **2개**다. 앞선 continuity의 '기존 변경 파일 전체 hash 보존' 문장은 실제 파일 범위를 과장했으므로 정정한다. C++/기존 Player 에셋을 직접 편집하지 않았다는 작업 범위와 전체 파일 hash 검증을 구분한다.

## 2026-09-08 그래픽 검증 최종 완료

- `HeinMachEnemy_RenderAssetAudit.json`은 **passed**다. 실제 D3D SM6 RHI에서 material 37개 모두 유효한 vertex/pixel shader instruction을 확인했다. `HeinMachEnemy_RenderAssetAudit.log`는 exit 0이며 material compile error가 없다.
- 저장된 확인용 맵을 새 프로세스에서 다시 열어 Blueprint 45개의 본체·idle 참조·검/방패 소켓을 검사했다. 사용하지 않는 import companion Skeleton 12개는 외부 참조가 없음을 확인하고 삭제했다. 최종 파일은 `.uasset` 300개와 확인용 `.umap` 1개다.
- 원작과의 화면 비교 또는 전투 PIE 합격으로 확대하지 않는다. 실제 수행한 검증은 source/geometry 참조, animation pose, actor 구성, shader compile, 저장 맵 재로드다.
- `HeinMachEnemy_ProtectedMaps.json`: 기존 HeinMach/StormPass 환경 맵 2/2의 SHA-256이 시작 시점과 일치한다.
- 추출·조립·임포트·확인용 맵 생성은 완료했다. 앞서 명시한 custom shader/색상·체형/morph·LOD/cloth·physics의 원작 완전 재현 범위는 여전히 미완료다. 후속 작업은 이미 보존된 source metadata/PSK/raw에서 시작하며 원본 전수 추출을 반복하지 않는다.

### 2026-09-08 추가 출처·정리 기록

- Halberd CB의 `CharacterMesh0.Properties.RelativeLocation.Z=-140.0 cm`, yaw=-90°도 표적 확인했다. 검병/방패병의 -85 cm와 구분한다. 완성 외형 Actor는 두 경우 모두 발 기준 원점을 사용한다.
- staging의 미참조 Skeleton 12개 삭제는 UE 에셋 도구로 완료했다. 이후 빈 `_ImportStaging` 디렉터리를 지우는 PowerShell 명령은 자동 승인 검토에서 정책상 거부됐다. 삭제를 우회하지 않고 빈 디렉터리만 남겼다. 최종 에셋 참조나 임포트 결과에는 영향이 없다.
