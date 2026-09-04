# FModel 에셋 분석 및 정리 규칙

> 적용 범위: `C:\Users\user\Desktop\카잔`에서 추출한 Khazan 에셋의 식별, 교차 참조, 정리 및 UE5 임포트 작업
> 이 문서는 실제 추출물에서 확인한 규칙을 기록한다. 기존 내용은 수정·삭제하지 않고 새 발견을 문서 하단에 날짜별로 추가한다.
> FModel/에셋 작업 전에는 `1_PROJECT_STATE.md`, `2_UE5_RULES.md`, `3_ARCHITECTURE.md`와 이 문서를 먼저 확인한다.

## 표기 기준

- `[관찰]`: 현재 추출 파일, 경로 또는 참조에서 직접 확인했다.
- `[추정]`: 반복 패턴으로 의미를 강하게 추정할 수 있으나 원본 제작 규칙으로 확정하지 않았다.
- `[미확정]`: 토큰은 확인했지만 정확한 의미를 아직 판정하지 않았다.
- 원본 표기 오류와 불일치도 식별자의 일부로 취급한다. 예: `OrigianlWounded`, `Frendly`, `Shose`, 이중 밑줄.

## 2026-08-31 추출물 기준 스냅샷

추출 루트 전체를 확장자 기준으로 집계한 값이다. 이후 추가 추출 시 달라질 수 있다.

| 형식 | 수량 | 주 용도 |
| --- | ---: | --- |
| `.png` | 4,347 | 텍스처 |
| `.json` | 1,988 | 머티리얼 요약, UObject 속성, 액터/인스턴스 정보 |
| `.fbx` | 544 | `Blender` 아래에서 생성한 변환·작업 파생본 |
| `.psa` | 528 | 캐릭터/무기 애니메이션 |
| `.usda` | 210 | 월드 메시, 머티리얼, 레벨 배치/합성 |
| `.hdr` | 66 | HDR 텍스처 |
| `.uexp` | 50 | Cooked 패키지 조각 |
| `.umap` | 34 | Cooked 맵 패키지 |
| `.psk` | 21 | 캐릭터 파츠 및 무기 Skeletal Mesh |
| `.uasset` | 16 | Cooked 에셋 패키지 |

## 원본 패키지와 추출 경로

### 경로 매핑

| 원본 논리 경로 | FModel 추출 경로 | 취급 |
| --- | --- | --- |
| `/Game/<경로>` | `C:\Users\user\Desktop\카잔\BBQ\Content\<경로>` | 변환된 원본 에셋의 기준 경로 |
| `/Engine/<경로>` | `C:\Users\user\Desktop\카잔\Engine\Content\<경로>` | 엔진 공용 의존성 경로 |
| `/Game/<경로>` 속성 덤프 | `C:\Users\user\Desktop\카잔\Exports\BBQ\Content\<경로>` | UObject/액터/머티리얼 참조 분석용 JSON |
| 변환 작업물 | `C:\Users\user\Desktop\카잔\Blender` | FBX 등 파생본; 원본 식별 기준으로 사용하지 않음 |

### 경로 처리 규칙

- `[관찰]` `BBQ\Content`와 `Exports\BBQ\Content`는 동일한 패키지 계층을 서로 다른 표현으로 보존한다.
- 에셋의 정식 식별자는 파일명만이 아니라 `마운트 + 상대 패키지 경로 + 오브젝트명`으로 기록한다.
- 같은 basename이 서로 다른 패키지에 존재할 수 있으므로 폴더를 제거한 채 병합하지 않는다.
- `BBQ`, `_Kazan_`, `Art`, `Character`, `Level` 같은 원본 폴더 토큰은 임의로 번역하거나 정규화하지 않는다.
- `.uasset`, `.uexp`, `.umap`은 Cooked 조각이므로 일반 UE5 프로젝트의 원본 에셋처럼 직접 복사·임포트하지 않는다.
- `.fbx`는 현재 모두 `Blender` 작업 계층의 파생 결과이므로 PSK/PSA/USDA/PNG/JSON보다 원본 우선순위가 낮다.

## 공통 이름 구성

대부분 다음 구조를 변형해 사용한다.

```text
<종류 Prefix>_<소속/세트>_<대상 또는 의미>_<상태/크기/형태>_<번호>_<변형>
```

- 밑줄은 의미 단위 구분자로 사용되지만 모든 이름이 같은 필드 수를 갖지는 않는다.
- 숫자는 보통 `001`, `002`처럼 3자리이며 애니메이션 변형은 `_1`, `_2`, `_01`, `_02`도 사용한다.
- `_L`, `_R`은 좌우가 분리된 에셋에서 사용한다.
- `_a`, `_b`, `_c`, `_va1`, `_pt1`, `_bk1`, `V2`, `V3`, `V4` 등은 변형 토큰이다. 의미를 추측해 제거하지 않는다.
- `_Inst`, `_Inst1`은 인스턴스/템플릿 계열 이름이며 원본 메시 이름과 동일시하지 않는다.
- `_LOD1`, `_LOD2`, `_LOD3`은 LOD용 리소스 또는 머티리얼 변형이다. 별도 LOD 지오메트리가 있다는 뜻으로 단정하지 않는다.

## 확인된 Prefix

아래 의미는 경로와 실제 참조를 함께 대조한 결과이며 공식 원본 명세는 아니다.

| Prefix | 관찰된 역할 | 예시 |
| --- | --- | --- |
| `C_` | 캐릭터/장비 Skeletal Mesh 계열 | `C_P_Kazan`, `C_I_DualAxeSword_...` |
| `C_P_` | 플레이어 캐릭터 메시 | `C_P_Kazan` |
| `C_I_` | 아이템/무기 메시 | `C_I_DualAxeSword_Original_L` |
| `CM_` | 캐릭터 머티리얼/머티리얼 인스턴스 | `CM_P_...` |
| `CT_` | 캐릭터 텍스처 | `CT_P_..._D` |
| `CA_` | 캐릭터/아이템 애니메이션 | `CA_P_Kazan_...` |
| `WP_` | 월드 Prop/Static Mesh | `WP_VFS_Rock_Small_002` |
| `WM_` | 월드 머티리얼 | `WM_VFS_Rock_Middle_001` |
| `WT_` | 월드 텍스처 | `WT_COM_..._N` |
| `WBP_` | 월드 Blueprint/Prop 템플릿 계열 | `WBP_CTR_...` |
| `FMI_` | VFX 머티리얼 인스턴스 | `FMI_...` |
| `FS_` | VFX Static Mesh | `FS_FogSheet_Plane` |
| `FT_` | VFX 텍스처 | `FT_Noise_...` |
| `BASE_` | 공유 베이스 리소스 | `BASE_PCHair_AK` |
| `HeinMach_` | HeinMach 레벨/레이어 패키지 | `HeinMach_SubLV03_Cave_2` |
| `LandscapeComponent_` | 개별 Landscape Component 지오메트리 | `LandscapeComponent_...` |
| `MaterialInstanceDynamic_` | 액터별 동적 머티리얼 override 추출물 | `MaterialInstanceDynamic_0` |

- `[미확정]` `WSP_`, `WLP_`도 월드 계열에서 확인되지만 정확한 역할은 참조를 더 확인하기 전까지 확장하지 않는다.
- `[추정]` `COM`, `VFS`, `CTR`, `BANTU`, `WOD`, `Castle`, `EMPIRE` 등은 지역·세트·제작군을 구분하는 family code다.
- `COM`은 공유 리소스에서 반복되지만 코드나 폴더명을 `Common`으로 자동 치환하지 않는다.
- family code의 자연어 의미가 확인되지 않은 경우 원문 토큰 그대로 저장한다.

## 캐릭터 에셋 구조와 메시 분할

### 기준 경로

```text
BBQ\Content\_Kazan_\Art\Character\CHA_Model
├─ PC\Kazan\Model\Arm
├─ PC\Kazan\Model\Face
├─ PC\Kazan\Model\Hair
├─ PC\Kazan\Model\Leg
├─ PC\Kazan\Model\Shoes
├─ PC\Kazan\Model\Torso
├─ PC\Kazan\Animation
└─ Item\DualAxeSword\Model
```

머티리얼과 텍스처는 다음 계층에 별도로 존재한다.

```text
BBQ\Content\_Kazan_\Art\Character\CHA_Material\Material
BBQ\Content\_Kazan_\Art\Character\CHA_Material\Texture
```

### Skeletal Mesh 분할 규칙

- `[관찰]` `C_P_Kazan.psk`가 카잔의 베이스 메시다.
- `[관찰]` 외형은 `Arm`, `Face`, `Hair`, `Leg`, `Shoes`, `Torso`별 독립 PSK로 분할된다.
- 파츠 폴더 아래에서 `BC_Original`, `ImperialGeneral`, `Prisoner`, `Original`, `OrigianlWounded` 같은 의상/상태 변형을 구분한다.
- 파츠 PSK를 하나의 메시로 합치지 않는다. UE5에서는 베이스 `SKM_Khazan`과 공통 포즈를 사용하고 각 파츠를 Leader Pose Component로 동기화한다.
- 파츠 교체 키는 최소한 `BodyPart + Variant + 원본 패키지 경로`를 포함해야 한다.
- `[관찰]` Dual Axe Sword는 외형 변형과 손 방향을 기준으로 파일이 나뉘며 `_L`, `_R`을 별도 무기로 유지한다.
- 좌우 또는 의상명이 빠진 경우 다른 파일의 규칙을 적용해 이름을 보충하지 않는다.
- 임포트 시 Skeleton 호환성을 검증한다. 현재 PSK 21개는 각각 유효한 Skeletal Mesh와 Skeleton으로 임포트되었지만, 파일명만으로 Skeleton 공유를 가정하지 않는다.

### 애니메이션 경로와 이름

```text
PC\Kazan\Animation\Normal
PC\Kazan\Animation\DualAxeSword
PC\Kazan\Animation\DualAxeSword\Style\Flow
PC\Kazan\Animation\DualAxeSword\Style\Yaksha
```

- `[관찰]` PSA 528개 중 `DualAxeSword` 직속 417개, `Normal` 70개, `Style\Flow` 29개, Animation 루트 10개, `Style\Yaksha` 2개다.
- `[관찰]` 이름 Prefix는 `CA_P_Kazan` 512개, `CA_PC_Kazan` 9개, `CA_I_Axe` 4개, `CA_Kazan_DualAxeSword` 2개, `Pose_Kazan_NonCombat` 1개다.
- 주 패턴은 다음과 같다.

```text
CA_P_Kazan_<WeaponOrState>_<Category>_<Action>_<PhaseOrDirection>_<Index>
```

- 상태/범주 예: `Normal`, `NonCombat`, `LockOn`, `DualAxeSword`, `DASword`, `Flow`, `Yaksha`.
- 동작 예: `Atk`, `Guard`, `Dodge`, `Walk`, `Run`, `Sprint`, `Fall`, `Stand`.
- 구간 예: `Start`, `Loop`, `End`, `Ready`, `Charge`.
- 방향 예: `F`, `B`, `L`, `R`, `FL`, `FR`, `BL`, `BR`, `L_180`, `R_180`.
- 발 기준 토큰 `LF`, `RF`, 변형 번호, `M1` 같은 보조 토큰도 식별자에 포함한다.
- `[미확정]` `A`, `B`, `M1`의 정확한 게임플레이 의미는 코드/몽타주 참조 전에는 임의로 확정하지 않는다.
- PSA 자동 분류는 이름 토큰을 사용할 수 있지만 Skeleton, 길이, 트랙 및 실제 참조를 검증한 뒤 연결한다.

## 월드 에셋 구조와 이름

### 기준 경로

```text
BBQ\Content\Art\World\World_Model\Prop\<분류>\WP_*.usda
BBQ\Content\Art\World\World_Material\Prop\Material\WM_*.usda
BBQ\Content\Art\World\World_Material\Prop\Texture\WT_*.png
Exports\BBQ\Content\Art\Terrain\Prop_Instances\<분류>\*_Inst.json
```

- Prop 분류에는 `Rock`, `Tree`, `Building`, `Ice`, `Ground`, `House`, `Deco`, `Weapon` 등이 있다.
- 월드 메시의 주 패턴은 다음과 같다.

```text
WP_<FamilyCode>_<SemanticType>_<SizeOrForm>_<3DigitIndex>[_Variant]
```

- 예: `WP_VFS_Rock_Small_002`, `WP_COM_Plants_Base_001_02_a`, `WP_CTR_Stoneset_Small_002`.
- 메시, 머티리얼, 텍스처 stem이 항상 같지는 않다. 이름 유사도 대신 USDA/JSON의 실제 참조를 우선한다.
- 예를 들어 `WP_COM_Plants_Base_002_03_b`가 `WM_COM_Plants_Base_002_03`을 참조하거나, `WP_VFS_Rock_Small_003`이 `WM_VFS_Rock_Middle_001`을 참조할 수 있다.
- Pivot Painter 텍스처는 `Texture\PivotPainter` 계층과 `_P2` 같은 suffix로 관찰되었다.

## 머티리얼과 텍스처 규칙

### 월드 머티리얼

- `[관찰]` `WM_*` USDA는 `UsdPreviewSurface` 네트워크를 사용한다.
- `_D`: diffuse/base color. Alpha가 opacity에 연결될 수 있으며 관찰된 threshold는 `0.333`이다.
- `_N`: normal. 관찰된 USDA에서 raw color space로 처리된다.
- `_S`: packed surface mask. 현재 확인한 월드 머티리얼에서는 `B → Roughness`, `G → Metallic`이다.
- `_S`의 R 채널이나 다른 family의 채널 배치는 확인 전까지 동일하다고 가정하지 않는다.
- `_LOD1` 샘플 중 텍스처 없이 `Roughness=1`만 가진 단순화 머티리얼이 있으므로 누락으로 자동 판정하지 않는다.

### 캐릭터 머티리얼

- `[관찰]` 캐릭터 머티리얼 JSON은 `Tex_D`, `Tex_S`, `Tex_N`, `Tex_I`, `Tex_E` 파라미터를 사용한다.
- `_E`는 `PM_Emissive` 계열에 연결되는 emissive 텍스처다.
- `_I`는 ID/제어 성격의 추가 텍스처로 보이지만 채널별 의미는 `[미확정]`이다.
- `_R`, `_F1`, `_F2`, `_NTP`, `_P2` 등 다른 suffix도 존재하므로 suffix만 보고 슬롯을 결정하지 않는다.
- 머티리얼의 parent, blend mode, two-sided, opacity clip, scalar/vector/static switch 파라미터를 JSON에서 함께 보존한다.
- Hair 샘플은 `Masked`, `TwoSided`, opacity clip `0.3333`, `MSM_BBQCartoon`, parent `BASE_PCHair_AK`, local wind/anisotropy 파라미터를 가진다.

### 매핑 우선순위

1. 머티리얼/레벨 USDA의 명시적 `material:binding` 또는 asset reference
2. verbose Export JSON의 Parent 및 Texture/Scalar/Vector Parameter 참조
3. compact material JSON의 `Textures`와 `Parameters`
4. 동일 package stem
5. suffix 추정

하위 단계는 상위 단계의 명시적 참조를 덮어쓰지 않는다.

## USDA 메시 및 레벨 분할 규칙

### Static Mesh 파일

- `[관찰]` 조사한 `World_Model` USDA 19개는 각각 `def Mesh` 1개와 `GeomSubset "Section_0"` 1개를 가진다.
- 조사 표본의 Section은 `unrealMaterialIndex=0`, `unrealCastShadow`, `material:binding`을 포함한다.
- 조사 표본은 `metersPerUnit=0.01`, `upAxis="Z"`이며 point, normal, UV, `doubleSided` 정보가 파일 안에 있다.
- 이 결과는 현재 표본에 대한 규칙이다. 새 파일을 임포트할 때 Mesh prim과 Section 수를 다시 계산한다.
- foliage 파일에서 `_LOD1`, `_LOD2` 머티리얼 참조가 보여도 현재 USDA에 별도 LOD 지오메트리가 보존되었다고 단정하지 않는다.
- USD prim/component명 때문에 UE에서 일반적인 이름이 생성될 수 있으므로 원본 package path를 최종 식별 메타데이터에 남긴다.

### Level 및 인스턴스 파일

- 레벨 USDA는 배치/합성 정보이고 `WP_*` 같은 asset USDA가 실제 geometry source다.
- `PointInstancer`는 `protoIndices`, `positions`, `orientations`, `scales`와 `Prototypes/FoliageInstancedStaticMeshComponent_*` 참조를 사용한다.
- 인스턴스 또는 액터별 머티리얼은 `OverrideMaterials` 아래의 `WM_*_LOD*` 또는 중첩된 `MaterialInstanceDynamic_0.usda`로 덮어쓸 수 있다.
- Fog sheet는 공유 `FS_FogSheet_Plane.usda`와 액터별 동적 머티리얼을 함께 사용한다.
- 비어 있는 Scope는 export 가능한 geometry가 없는 액터/컴포넌트일 수 있으므로 오류 메시로 만들지 않는다.
- Landscape는 컴포넌트 단위로 분할된다. HeinMach에서는 `LandscapeComponent_*.usda` 57개를 확인했다: Landscape1 18개, Landscape2 39개.

## HeinMach 레벨 구조

기준 경로:

```text
C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Level\HeinMach
```

- `HeinMach_All`은 subLayer를 모으는 합성 루트다.
- 환경/게임플레이 레이어에는 `Light`, `Chrcollision`, `Landscape1`, `Landscape2`, `SubLV01`~`SubLV07`, `SubLV99_Extra`가 있다.
- 서브레벨 이름은 주로 `SubLV<2자리>_<의미>[_변형 번호]` 형식이다. 예: `SubLV02_Blizzard_1`, `SubLV03_Cave_2`, `SubLV04_WaterfallUp_1`.
- 중첩 export는 보통 `<Level>/PersistentLevel/<Actor>/<Component>/<Resource>.usda` 구조를 따른다.
- `Spawn_Main01`, `Sound`, `BGM`, `POS`, `MoveCustomSpline`과 모든 `Cine_*`는 현재 환경 재구성 범위에서 제외한다.
- 주인공의 맨손 비틀거림 및 기본 이동 전용 장면은 레벨 배치/시퀀스 구성에 포함하지 않는다.

## JSON 종류와 사용법

- `BBQ\Content\...\*.json`: FModel이 만든 compact 요약 형식. 머티리얼의 `Textures`, `Parameters`를 빠르게 확인할 때 사용한다.
- `Exports\BBQ\Content\...\*.json`: UObject 배열, `Type`, `Class`, `Package`, `Properties`, parent와 parameter array를 담는 verbose 형식이다.
- Prop instance JSON은 template/object reference와 transform을 보존하므로 basename 기반 검색보다 우선한다.
- HeinMach 속성 JSON은 액터 및 컴포넌트의 원본 참조를 복원하는 근거로 사용한다.
- compact JSON과 verbose JSON이 다르면 원본 package/object reference를 보존한 verbose 속성을 먼저 검토한다.

## UE5 임포트 및 프로젝트 정리 규칙

### 원본 보존

- FModel 추출 폴더는 read-only 원본/스테이징으로 취급하고 이름이나 계층을 바꾸지 않는다.
- 임포트 자동화는 원본 상대 경로, 원본 object/package명, 변환 파일 경로를 로그 또는 메타데이터에 남긴다.
- 원본 오탈자를 자동 수정하지 않는다. 보기 좋은 Display Name이 필요하면 원본 식별자와 별도로 둔다.
- 같은 basename 충돌 시 임의 숫자를 붙이기 전에 원본 패키지 계층을 UE 폴더에 반영하거나 결정론적 source key를 사용한다.

### 프로젝트 대상 경로

- ActorX 임포트: `/Game/_Art/Kazan/FModel/PSK`
- HeinMach 환경: `/Game/_Art/Kazan/Environment/HeinMach`
- 새 분류를 추가해도 `Character`, `Item/Weapon`, `Animation`, `World/Environment`, `Material`, `Texture`, `Metadata`의 역할을 섞지 않는다.
- raw import 결과와 조립된 게임용 에셋/맵을 구분한다.
- 재실행 시 기존 유효 에셋을 덮어쓰지 않고 클래스, 참조, 머티리얼 슬롯, 액터 수를 검증한다.

### 재구성 순서

1. 원본 package path와 object명을 source key로 수집한다.
2. 레벨/인스턴스의 prototype reference를 실제 `WP_*` USDA에 연결한다.
3. `material:binding`과 override를 실제 `WM_*` 또는 동적 머티리얼에 연결한다.
4. 머티리얼 USDA/JSON에서 텍스처와 파라미터를 연결한다.
5. 좌표계, scale, section, material slot, LOD 표현을 검증한다.
6. UE 에셋을 저장한 뒤 로드 재검증하고 결과 보고서를 남긴다.

## `UKhazanAssetManager` 연동 규칙

현재 구조:

- `UKhazanAssetManager`는 `UAssetManager`를 상속하며 `LoadedAssetData`와 `NameToLoadedAsset`을 가진다.
- `UKhazanAssetData`의 `FAssetEntry`는 `FGameplayTag AssetName`, `FSoftObjectPath AssetPath`, `AssetLabels`를 사용한다.
- `PreSave()`는 Gameplay Tag의 이름을 key로 `AssetNameToPath`를 만들고 label별 set을 생성한다.
- `BP_`, `B_`, `GE_`, `GA_`로 시작하는 에셋은 class soft path가 되도록 `_C`를 붙인다.
- Static Mesh, Skeletal Mesh, Material, Texture, Animation 같은 일반 object asset에는 `_C`를 붙이지 않는다.
- `UKhazanAssetManager::Initialize()`의 실제 로딩은 아직 구현되어 있지 않다.

### 권장 Gameplay Tag key

원본 basename만 key로 쓰지 않고 안정적인 의미 태그를 사용한다.

```text
Asset.Character.Khazan.Mesh.Base
Asset.Character.Khazan.Mesh.Torso.Prisoner
Asset.Item.DualAxeSword.Mesh.Original.Left
Asset.Animation.Khazan.DualAxeSword.Guard.Start
Asset.World.HeinMach.Prop.Rock.VFS.002
```

- `AssetName`은 런타임 조회용 의미 key다.
- 원본 FModel 파일명과 package path는 별도 provenance/metadata로 보존한다.
- `NameToLoadedAsset`가 `FName` key 하나를 사용하므로 서로 다른 패키지의 같은 basename을 직접 key로 사용하지 않는다.
- `AssetLabels`는 `Character.Part.Torso`, `Weapon.DualAxeSword`, `Level.HeinMach`, `Source.FModel`처럼 다중 분류에 사용한다.

## 금지 및 검증 체크리스트

- basename만으로 메시와 머티리얼을 자동 연결하지 않는다.
- 확인되지 않은 family code나 texture channel 의미를 풀어 쓰지 않는다.
- source typo, 좌우 suffix, variant, LOD suffix를 삭제하거나 합치지 않는다.
- 레벨 USD의 Scope를 모두 독립 Static Mesh로 만들지 않는다.
- `MaterialInstanceDynamic_*` override를 공용 원본 머티리얼로 덮어쓰지 않는다.
- `PSK = 캐릭터 전체`, `USDA = 메시 하나`, `_LOD* = 별도 지오메트리`라고 전역 가정하지 않는다.
- 임포트 후 asset class, source count, Skeleton, material slot, texture reference, transform과 재실행 안정성을 검증한다.
- 새 규칙을 발견하면 근거 파일/경로와 `[관찰]`, `[추정]`, `[미확정]` 상태를 함께 이 문서 하단에 추가한다.

## 2026-08-31 HeinMach 심화 추출 규칙

- [관찰] corrected source import 대상은 서로 다른 source USDA 183개이며 결과는 Static Mesh 183개, Material Instance 334개, Texture 955개다. asset sharing이나 material-slot merging을 켜면 서로 다른 source가 합쳐지므로 이 데이터셋에서는 비활성화한다.
- [관찰] 일반 렌더 배치는 source root StaticMeshComponent 기준 2,665개다. 원본 layer, actor, component, mesh package와 transform을 합친 placement manifest를 식별 기준으로 사용한다.
- [관찰] root가 아닌 visible StaticMeshComponent는 총 128개다. 이 중 113개는 foliage PointInstancer이고 나머지 15개는 table 9, carriage break 5, bridge 1의 실제 child render mesh다.
- [관찰] foliage는 15개 source level의 113 PointInstancer batch, 19 prototype, 12,495 instance로 구성된다. protoIndices, positions, orientations, scales를 유지하고 HISM batch로 복원한다.
- [관찰] foliage override material은 source mesh의 기본 slot과 별개일 수 있다. source binding과 override reference를 우선하고, imported UE slot index만으로 연결하지 않는다.
- [관찰] 비시네마틱 WBP_FogSheet_C는 50개다. FModel은 actor transform, sort priority, dynamic scalar/vector parameter와 smoke-noise texture reference를 보존하지만 custom parent shader graph는 보존하지 않는다.
- [관찰] fog의 MaterialInstanceDynamic USD는 opaque preview stub이므로 원본 fog shader가 아니다. source JSON parameter를 보존한 별도 translucent preview material로 취급한다.
- [관찰] HeinMach landscape는 Landscape1 18개와 Landscape2 39개, 합계 57 LandscapeComponent geometry로 분할되어 있다. component USDA에는 points, normals, tangents, UV0/UV1이 있으나 원본 WLM, weightmap, layer blend graph는 추출되지 않았다.
- [관찰] aggregate terrain mesh의 MI_DisplayColor 및 MI_DisplayColor_Translucent는 원본 지형 셰이더가 아니라 placeholder다. 원본 layer 자료가 없을 때는 geometry와 transform을 유지한 별도 preview material만 적용하고 근사치임을 기록한다.
- [관찰] 원본 Static Mesh 190개 winding audit는 positive 1,986,738, negative 6,597, near-zero 2, parser error 0이다. 전체 triangle이 역전된 mesh는 확인되지 않았다.
- [관찰] negative triangle이 섞인 vegetation은 대체로 authored two-sided foliage다. 일부 negative triangle 또는 actor의 negative determinant만으로 mesh 전체 winding을 뒤집지 않는다.
- [관찰] mirrored source placement 341개는 negative determinant transform을 가진다. 원본 scale sign을 유지하고 UE의 mirrored transform 처리 결과를 감사한다.
- [검증 규칙] placement 복원 후 일반 prop transform/mesh/surface, HISM instance transform digest, child relative transform, fog transform/sort priority, terrain material을 서로 독립된 report로 검증한다.
- [범위 제외] HeinMach_Cine_*와 주인공 맨손 비틀거림·기본 이동 전용 장면은 source inventory와 복원 수량에 포함하지 않는다.

## 2026-08-31 기존 조사 재사용 규칙

- FModel 전체 또는 HeinMach 전체를 탐색하기 전에 6_SURVEY_KNOWLEDGE_BASE.md에서 기존 snapshot과 질문별 canonical JSON을 확인한다.
- 특정 actor, mesh, material, texture, transform은 basename 전체 검색 대신 metadata의 source package, object path, managed label로 부분 조회한다.
- 기존 snapshot은 FModel 전체 확장자 수량, HeinMach world JSON 35개, placement 11,065개, render candidate 2,782개, live prop 2,665개와 USD graph를 이미 보존한다.
- source file set 또는 metadata schema가 바뀌지 않았다면 같은 수량을 확인하기 위한 전수 집계를 반복하지 않는다.
- 새 전수조사 결과는 조사한 source root, 포함/제외 규칙, 생성 script, 상세 JSON, 오류와 미확정 항목, 기존 결과 대체 여부를 6_SURVEY_KNOWLEDGE_BASE.md에 기록한다.
