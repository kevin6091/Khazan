# HeinMach Yetuga 보스 에셋 — 2026-09-11

## 사용 위치

- 에셋 루트: `/Game/_Art/Enemies/HeinMach/Bosses/Yetuga`
- 배치용 시각 Blueprint: `Blueprints/BP_EN_Boss_Yetuga`
- 비교 맵: `Preview/L_EN_Yetuga_Catalogue`
- 본체: `Meshes/SK_EN_Yetuga`, `Skeletons/SKEL_EN_Yetuga`
- 소형 얼음 투척물: `Meshes/SK_EN_Yetuga_IceRock`, `Skeletons/SKEL_EN_Yetuga_IceRock`
- 재생 시퀀스: `Animations/Playback/A_EN_PLAY_*`. 현재 프로젝트에서 재생할 시퀀스만 보관한다.
- 조사·검증 문서: `Metadata/Extraction_20260911`. `AnimationLibrary.csv`에서 이름, 원작 package, FPS 분수, 프레임 수, 길이, RateScale을 조회한다.

## 원작 식별과 범위

`BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01`의 `SA_Yetuga`는 `ActorBP_Soft.AssetPathName=/Game/_Kazan_/Design/Monster/Boss/01_Yetuga/Base_Setting/CB_Yetuga.CB_Yetuga_C`를 참조한다. `SpawnIDX=82`, `TIDX=283005`, `DependentLevelPath=/Game/_Kazan_/Level/HeinMach/HeinMach_Landscape2`가 직렬화돼 있다. 수치는 식별용 원본 필드이며 새 gameplay 설정으로 적용하지 않았다.

`CB_Yetuga.CharacterMesh0.SkeletalMesh`는 `BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/Yetuga/Model/C_M_Yetuga`다. 해당 메시의 원본 import filename도 YetugaBoss 모델을 가리킨다. 일반/Sub/Ghost 외형을 섞어 보스의 외형이라고 만들지 않았다.

본체와 원작 스킬이 참조하는 `C_I_YetugaRock_Small`을 선택했다. 두 메시의 Skeleton은 각각 `C_M_Yetuga_Skeleton`, `C_I_YetugaRock_Small_Skeleton`이다. 두 메시의 재질 상속·텍스처·스켈레톤·애니메이션 및 보스 Base_Setting/Moving/Skill의 표적 참조를 추적했다. 관련 package 581개에서 JSON을 확보했고 원본 cooked package도 보존했다.

다음 두 파일은 폴더 이름이 다른 몬스터이지만 **원본 Skeleton 필드가 C_M_Yetuga_Skeleton**이므로 Yetuga 재생에 포함한다.

- `BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/ApesStoneHandElite/Animation/CA_M_ApesStoneHandElite_DamageGrapple_Atk_B_01`
- 같은 폴더의 `CA_M_ApesStoneHandElite_DamageGrapple_Atk_B_02`

공통 `Missile_Skeleton`/`Missile_Idle`을 참조하는 투사체 gameplay carrier Composite 6개는 본체·얼음 메시용 시퀀스가 아니다. JSON과 관련 보스 스킬 맥락은 남기고 Yetuga 본체 스켈레톤에 억지로 임포트하지 않았다.

## 메시와 재질

| 구분 | 복원 내용 |
|---|---|
| 본체 | 원본 PSKX 198 bone에 PSA 전용 비가중 reference bone 255개를 추가하여 453 bone 사용 |
| 얼음 투척물 | 원본 20 bone 그대로 사용 |
| 본체 재질 슬롯 | Ice_Dissove, Fur, EyeR, Ice, Face, EyeL, Body의 원본 순서·slot name 유지 |
| 텍스처 | 실제 2D parameter에 사용되는 cooked payload 56개; 원본 sRGB·압축·LOD group 복원 |
| Material Instance | 본체 슬롯 7종, 얼음 재질 1종과 상속 부모 6종, 총 14개 |
| 셰이더 어댑터 | Surface/Eye/Prop 3개. 원작 전용 셰이딩 모델을 stock UE에서 표시하는 명시적 대체 그래프 |
| 소켓 | 원본 7개 이름·parent bone·local transform을 본체의 mesh socket으로 복원 |
| LOD | 원본은 각 메시 LOD0/1/2. 현행 PSK 임포터로 LOD0을 임포트하며 원본 세 LOD 파일을 archive에 보관 |

선택한 PSA 전체의 bone 이름·순서와 메시 공통 reference prefix의 parent/transform을 대조한 후 파생 메시를 생성했다. 기존 geometry·weight·UV·material chunk는 보존한다. CUE4Parse의 PSK/PSA reference 좌표계 차이를 보정하고 공통 prefix가 맞지 않으면 중단한다. 원본 PSKX의 32-bit FACE3200을 유지하며, 프로젝트 PSKFactory가 인식하는 `.psk` 확장자로 파생 파일을 저장한다. PSKXFactory는 static mesh용이므로 이 스켈레탈 메시에는 사용하지 않는다.

원본 스켈레톤 소켓과 이름·뼈·변환이 같은 mesh socket을 사용한다. UE 5.8의 `AddSocket(..., true)`는 mesh/skeleton 양쪽에 복제하므로 이 라이브러리에서는 단일 mesh 소켓을 만든다. 원래 소유 위치와 전체 원본 JSON은 `SourceSocketsJSON`, `SocketOwnershipContract`, source archive에 보존한다.

Material Instance의 부모 경로를 따라 원작 master의 `CachedExpressionData.Parameters.RuntimeEntries[*].ParameterInfos`와 `ScalarValues/VectorValues/TextureValues`를 같은 인덱스로 결합했다. 이후 부모→자식 override를 적용했다. 네이티브 MI parent 연결, effective scalar/vector/2D texture parameter, 털의 TwoSided와 OpacityMaskClipValue를 복원한다. 값별 출처는 `ImportManifest.json`의 `parameter_origins`, 에셋의 `OriginalPropertiesJSON`/`EffectivePropertiesJSON`에 있다.

텍스처 해상도는 PNG와 cooked `SizeX/SizeY` 기준이다. 예를 들어 `CT_M_YetugaBoss_Body_D`의 추출 payload는 1024×1024이다. 원본 authoring `ImportedSize`와 다르더라도 없는 픽셀을 확대 생성하지 않는다.

원본의 `MSM_BBQCartoon`/`MSM_BBQHalfCartoon` 구현과 cooked 셰이더의 노드 연결은 JSON만으로 완전히 되살릴 수 없다. 어댑터는 표시용 diffuse/normal/specular/roughness/alpha 및 eye 색을 연결하고 나머지 복원 parameter는 주소와 값을 보존한다. static switch가 제어하던 원작 wind/dissolve/rim/death 동작을 구현했다고 간주하지 않는다. 원작 parent 기본값 중 CurveAtlas/Cube/Engine/게임 플러그인 texture 참조 등 일반 Texture2D binding으로 복원하지 않은 항목은 `metadata_only_texture_parameters`에 명시했다. 슬롯 2D 텍스처의 누락을 이 예외로 숨기지 않는다.

## 애니메이션 시간축

원본 PSA 91개를 입력으로 재생용 시퀀스 120개를 만들었다. 본체 117개와 소형 얼음 3개다. 직접 시간축을 사용하는 9개는 AP/BlendSpace 등 원작의 직접 참조를 근거로 선택했고, 나머지 111개는 원작 Composite별 재생 구간과 속도를 반영한 결과다. 별도의 임포트 원본 AnimSequence는 프로젝트에 만들지 않는다.

- 직접 시퀀스: 원본 `NumFrames`, `SequenceLength`, `RateScale`을 보존한다. 샘플 FPS는 `(NumFrames-1)/SequenceLength`; PSA의 `NumFrames/SequenceLength` 비율을 샘플 FPS로 사용하지 않는다. 직접 재생 9개는 모두 30/1 FPS다.
- Composite: `AnimationTrack.AnimSegments`의 `StartPos`, `AnimStartTime`, `AnimEndTime`, `AnimPlayRate`, `LoopingCount`를 적용한다. 활성 `BakedDilationCurveName`/`ApplyDilationCurveType` 조건과 `DilationCurve.DilationAnimPositions`의 `T_Original→T_Dilation` 표를 읽어 시간축을 변환한다.
- 활성 dilation을 반영한 결과는 66개이며, 그중 원본 Composite `SequenceLength`와 최종 길이가 달라진 것은 57개다. 최종 sample interval 수와 길이로 유리수 FPS를 정해 원작 asset 시간축을 유지한다. 전체 FPS 계약은 60종이다.
- 모든 결과의 `RateScale=1.0`은 확인된 원작 값이다. 원본 구간 배속과 dilation은 이미 pose sampling에 반영했으므로 같은 배속을 한 번 더 곱하지 않는다.
- source root motion flag 99개, force root lock 68개, additive 1개를 시퀀스별로 복원했다. 두 root 관련 집계는 서로 배타적인 분류가 아니다.
- 원작 notify/event 2,324행의 시간과 자료는 `PlaybackEventTimes.json`에 보존했다. 원작 전용 notify 클래스의 공격 판정·음향·VFX 실행 코드를 생성한 것은 아니다.

시간축 사례: `BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Moving/Move/AC_M_Yetuga_Turn_L`은 원본 `SequenceLength=1.6666666 s`, 활성 곡선의 `DilationSequenceLength=1.0040345 s`다. 최종 61 sample/60 interval을 `4785971/80088 FPS`로 저장한다. 입력 필드와 변환 표는 동일 package의 원본 JSON, `AnimationImportManifest.json`, `AnimationTimingAudit.json`에서 확인한다. 이는 원작 기반 계산값이며 임의 이동/회전 튜닝값이 아니다.

게임 실행 중 actor time dilation, hit-stop, AI 상태별 배속·블렌드·Notify 기반 효과는 별도 gameplay 계약이다. 이번 검증은 추출한 원본/Composite의 asset 시간축과 저장된 시퀀스 사이의 일치이며 원작 게임 전체의 실행 속도를 실측 검증한 것으로 표현하지 않는다.

## Blueprint 내용

`BP_EN_Boss_Yetuga`는 Actor 기반의 시각 조립이다. `EnemyBody` SkeletalMeshComponent에 본체와 원본 슬롯 재질을 설정하고 `A_EN_PLAY_CA_M_Yetuga_Stand_F`를 single-node/loop/playing/배속 1.0으로 지정한다. Event Graph에 보스 AI·공격·피격·이동·GAS를 구현하지 않았다. 충돌 피해 판정도 포함하지 않는다.

원본 `CharacterMesh0`의 `RelativeRotation.Yaw=-90°`를 적용한다. 원본 capsule 기준 offset `(0, 0.000031, -265) cm`는 metadata에 보존하고 비교용 Actor의 발 기준 표시 원점은 `(0,0,0)`으로 둔다. 비교 맵의 배치 간격·조명·카메라·투척물 높이는 어시스턴트가 선택한 표시용 설정이며 gameplay 원작 수치가 아니다.

## 원본 보관과 재현

- 프로젝트 metadata의 `SourceMetadata.zip` / `SourceMetadataIndex.json`: 원본 package 581개의 JSON과 SHA-256. Git으로 함께 전달한다.
- 외부 원본: `C:/Users/user/Desktop/카잔/EnemyExtracts/Yetuga_20260911`. cooked package, 전체 추출 PNG/PSK/PSKX/PSA, LOD, 파생 pose 데이터, script, report와 `ArchiveSHA256.json`을 보관한다.
- physics asset, cloth/Kawaii limits, postprocess animation blueprint/control rig, 보스 AI/skill/spawn, custom notify, VFX/audio 등의 원본 정보를 보존한다. stock UE에서 구현되지 않은 원작 클래스가 자동으로 복원됐다고 간주하지 않는다.
- 게임 키나 FModel 설정 파일 전체를 프로젝트/외부 archive에 복사하지 않는다.

재현 순서: `prepare_yetuga_sources.py discover` → `export` → `build_yetuga_import_manifest.py` → `prepare_yetuga_animation_timing.py` → Unreal Python commandlet `import_yetuga_library.py` → `run_yetuga_animation_batches.py` → `build_yetuga_assemblies.py` → `audit_yetuga_library.py` → 실제 RHI의 `verify_yetuga_render.py` → `archive_yetuga_sources.py`.

검증 스크립트는 기존 Yetuga 버전 metadata가 없는 대상 에셋을 덮어쓰지 않는다. 재개 시 animation batch report의 version/status/count가 맞는 완료 batch를 재사용한다. 최종 검증은 저장 후 새로운 Unreal 프로세스에서 수행한다.

## 확인된 검증

120개 animation import batch가 모두 종료 코드 0/pass로 끝났다. 각 시퀀스의 FPS 분자/분모, sample/frame 수, 길이, RateScale, RAW/COMPRESSED의 처음·중간·끝 bone pose를 대조했다. 최대 길이 오차는 `1.9073486345888568e-7 s`, 위치 성분 오차는 `0.0001239776611328125 cm`, quaternion 성분 오차는 `0.000697791576385498`, scale 오차는 `9.5367431640625e-7`이다. 이 오차는 import/compression 수치 검증 결과이며 gameplay 허용값이 아니다.

저장 에셋 재로드/재질/소켓/구조 및 실제 RHI 검증의 최종 결과는 아래 후속 검증 절과 `ValidationSummary.json`, `RenderValidationSummary.json`, `FinalExtractionReport.json`을 따른다. 초기 단계의 진행 중 report를 최종 완료 근거로 사용하지 않는다.

### 2026-09-11 실제 에디터 렌더 확인

일반 UnrealEditor에서 저장된 비교 맵을 로드하고 editor frame을 진행한 뒤 `capture_yetuga_editor_preview.py`로 캡처했다. 본체의 흰 털·피부·얼굴·눈과 검은 얼음 돌기, 별도 얼음 투척물의 텍스처/실루엣 표시를 확인했다. 원작의 전용 shader effect까지 동일하다고 판정한 것은 아니다. D3D12/SM6에서 master 3개/MI 14개 총 17개가 실제 shader instruction을 가지며 material fallback 경고가 없는 것도 확인했다.

frame 0 commandlet의 즉시 SceneCapture에서는 본체 표면이 보이지 않았지만 transient opaque diagnostic에서는 mesh 실루엣이 표시됐고, 동일한 저장 에셋이 일반 editor frame 이후 정상적으로 표시됐다. 따라서 초기 즉시 캡처를 mesh 손상이나 원작 texture 누락의 근거로 사용하지 않는다. 수치 보존 그래프의 bounded 처리도 이 현상의 확정 원인/해결책이라고 기록하지 않는다.

최종 화면은 metadata의 `Preview/Yetuga_RenderPreview_20260911.png`와 `Yetuga_BaseColorPreview_20260911.png`다. 원본값을 보존하는 master 최종 버전은 `20260911_YetugaPreviewV4_BoundedParameterRetention`이다. 마지막 capture는 commandlet 대신 일반 에디터를 숨김/offscreen으로 시작하고 `-ExecCmds="py C:/.../Scripts/Enemies/capture_yetuga_editor_preview.py" -AllowCommandletRendering -NoTextureStreaming`를 사용한다. 스크립트는 capture 후 자신이 시작된 에디터를 종료한다.

### 2026-09-11 최종 저장 검증 완료

최종 V4 material과 base-property 검사를 포함한 fresh process가 종료 코드 0/pass로 끝났다. 199개 asset, texture 56개, material instance 14개의 scalar 2,381/vector 482/2D texture binding 329개를 원본 기반 effective 값과 대조했다. 본체/얼음 skeleton, 소켓 7개, BP와 모든 시퀀스의 FPS·길이·RAW/COMPRESSED pose를 통과했고 임시 UE package는 0개다. source skeleton별로 선택 PSA의 BONENAMES 전체 record hash도 동일함을 확인해 이름뿐 아니라 parent/reference pose의 일치를 검증했다.

원작 자료에서 복원한 데이터와 표시용 shader/배치 설정을 구분하는 위 제한은 유지한다. 게임 C++/Config를 수정하거나 새로 빌드하지 않았으며, 작업 전 사용자 변경 22개 파일과 Source/Config 보호 hash를 별도로 대조했다.
