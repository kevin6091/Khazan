# WildDog 실사용 에셋 — 2026-09-15

## 결과와 프로젝트 위치

- 루트: `/Game/_Art/Enemies/Shared/Beasts/WildDog`
- 공용 본체: `Meshes/SK_EN_WildDog`, `Skeletons/SKEL_EN_WildDog`
- 시각 조립 BP: `Blueprints/BP_EN_WildDog_CoatV1`, `BP_EN_WildDog_CoatV2`, `BP_EN_WildDog_CoatV3`
- 재생용 시퀀스: `Animations/Playback/A_EN_PLAY_*`
- 비교 맵: `Preview/L_EN_WildDog_Catalogue`
- 원본 근거와 검증 자료: `Metadata/Extraction_20260915`

최종 Unreal 라이브러리는 Asset Registry 기준 125개다. SkeletalMesh/Skeleton 각 1개, Texture2D 25개, source Material Instance 10개, 표시용 master 2개, 재생용 AnimSequence 82개, 외형 BP 3개와 catalogue map 1개로 구성된다. 작업용 원본 AnimSequence나 임시 package는 남기지 않았다.

## 레벨 사용처와 버전 판정

표적 레벨 JSON `BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01`과 `BBQ/Content/_Kazan_/Level/StormPass/StormPass_Spawn_Main01`을 조사했다. HeinMach에는 WildDog/WhiteDog spawn이 없고, StormPass에는 `ActorBP_Soft=/Game/_Kazan_/Design/Monster/Beast/WhiteDog/Base_Setting/CB_WhiteDog`인 spawn handler 17개가 있다. 따라서 이번 실사용 정본은 이름 검색으로 발견한 모든 개 계열이 아니라 StormPass의 `CB_WhiteDog`다.

`CB_WhiteDog`의 SCS component template `CD_RD_M_WildDog_White_001_GEN_VARIABLE`까지 상속값을 합쳐 확인했다. 이 component가 레시피 CDO의 배열을 V3/V2/V1 메시와 대응 재질 세트로 교체하고 `PartsIndexCache[ENPCParts::Hair].IndexTable`의 key 0, 1, 2를 모두 유지한다. 세 key가 실제 RandomLook 선택 결과이므로 외형 세 가지를 보존했다.

| 프로젝트 외형 | 원본 material index | 실제 재질 조합 |
|---|---:|---|
| `CoatV1` | 2 | `CM_M_WildDog_Head`, `CM_M_WildDog_Body`, `CM_M_WildDog_Eye` |
| `CoatV2` | 1 | `CM_M_WildDogV2_Head`, `CM_M_WildDogV2_Body`, `CM_M_WildDog_Eye` |
| `CoatV3` | 0 | `CM_M_WildDogV3_Head`, `CM_M_WildDogV3_Body`, `CM_M_WildDog_Eye` |

component 배열 순서가 V3→V2→V1이므로 source index와 프로젝트의 외형 번호 방향이 반대다. BP 이름은 사람이 확인하기 쉬운 실제 재질 버전을 따른다. 이 대응과 레시피 CDO, component override, effective recipe 원문은 `VariantUsage.json`에 보존했다.

일반 `CB_PicaroonDog`와 `C_M_PicaroonDog*`는 조사한 HeinMach/StormPass spawn에서 참조되지 않았다. Ghost PicaroonDog/WildDog도 live `CB_WhiteDog` closure 밖이다. 이들은 현재 두 레벨용 UE 캐릭터에는 넣지 않았고 분류 JSON과 원본 metadata만 보존했다. 이것은 게임 전체에서 절대 미사용이라는 전수 판정이 아니다. `C_M_PicaroonDog_EmptyMesh`는 원작의 모듈 조립·애니메이션 carrier이므로 보존 자료에는 포함하지만 표시 BP는 실제 전신 메시를 직접 사용한다.

## 메시·스켈레톤·LOD

`C_M_WildDog`, `C_M_WildDogV2`, `C_M_WildDogV3`의 ActorX chunk를 비교했다. 세 파일은 `MATT0000`을 제외한 geometry, UV, normal, vertex color, skin weight, bone, socket payload가 바이트 단위로 같다. 그래서 중복 SkeletalMesh 세 개를 만들지 않고 `SK_EN_WildDog` 하나와 BP material override 세 조합을 사용한다. 이 동일성 판정과 alias 목록은 `ImportManifest.json` 및 `MeshDerivationAudit.json`에 있다.

원본 mesh bind 48개와 skin weight 35,029행을 독립 감사했고 bone 추가는 0개다. 원본 LOD0은 points 16,179, wedges 19,363, faces 26,080이며 UE가 만든 LOD0 render vertex는 19,399개다. 원본 socket 5개의 이름·parent·local transform도 확인했다.

원본 LOD0/1/2 파일은 외부 archive에 보관한다. 현재 프로젝트에는 검증한 LOD0 하나만 임포트했으며 엔진 자동 LOD를 원본 LOD라고 표시하지 않는다.

## 재질·텍스처·셰이더

선택된 세 외형과 부모를 따라 Texture2D 25개와 Material Instance 10개를 임포트했다. 부모 `CachedExpressionData.Parameters.RuntimeEntries[*].ParameterInfos`와 scalar/vector/texture 배열을 결합하고 부모→자식 override를 적용했다. fresh audit에서 scalar 1,410개, vector 392개, Texture2D binding 166개를 effective source 값과 대조했다. 원본 sRGB, compression, LOD group과 cooked payload 해상도를 사용하며 authoring `ImportedSize`가 더 큰 일부 텍스처를 임의 확대하지 않았다.

원작의 cooked BBQ 전용 shader graph와 custom shading model 실행 코드는 편집 가능한 형태로 복구할 수 없다. `M_EN_WildDog_SurfacePreview`와 `M_EN_WildDog_EyePreview`는 저장한 원본 texture/scalar/vector/base-property를 Unreal에서 표시하기 위한 명시적 adapter다. 전용 static switch, dissolve, 특수 VFX 동작을 원본과 동일하게 구현했다고 간주하지 않는다. 원본 부모·상속값·미지원 texture parameter는 metadata와 raw cooked archive에 남겼다.

## 애니메이션 시간축

`AP_WhiteDog`에서 도달 가능한 원본 PSA 61개와 Composite 65개를 추적했다. 최종 UE에는 실제 재생 결과 **82개**만 둔다.

- `DirectOriginalTimeline` 17개는 원본 `NumFrames`, `SequenceLength`, `RateScale`을 사용하며 `(NumFrames-1)/SequenceLength`가 모두 30/1 FPS다.
- `CompositeBake` 65개는 `AnimationTrack.AnimSegments`의 구간, 반복, `AnimPlayRate`와 활성 `DilationCurve.DilationAnimPositions`를 포즈 시간축에 반영했다. 최종 길이를 정확히 표현하는 rational sample rate로 저장하고 UE `RateScale=1.0`에서 재생한다.
- 원본 Composite 표시 길이와 bake 결과가 달라진 14개는 source segment/dilation 적용 결과다. 임의 재생 속도 보정이 아니다.
- root motion 25개, force root lock 0개, additive 0개를 원본 property와 대조했다.
- 원본 notify/event 429행의 원시 시간과 bake 후 대응 시간은 `PlaybackEventTimes.json`에 보존했다. 원작 custom notify 실행 코드를 구현한 것은 아니다.

82개 전부의 저장 FPS 분수, sample 수, 길이, root 설정과 처음/중간/끝의 RAW·COMPRESSED 전 bone pose를 검사했다. 최대 길이 오차는 `9.536743172944284e-8 s`, 위치 성분 `9.918212890625e-5 cm`, quaternion 성분 `9.877979755401611e-5`, scale `9.799003601074219e-5`다. 이 검증은 asset 시간축과 포즈 복원에 관한 것이며 runtime hit-stop, actor dilation, AI 상태별 재생률까지 측정한 결과는 아니다.

## Blueprint 역할과 원본 수치

각 BP는 Actor 아래 `EnemyBody` SkeletalMeshComponent 하나만 가진 시각 조립 에셋이다. 공용 mesh, 해당 coat의 3개 material override와 `A_EN_PLAY_AC_M_PicaDog_Normal_Stand_F`를 single-node 방식으로 연결하고 play rate는 1.0이다. AI, 공격 판정, 이동, GAS, 피해, 원작 notify 실행은 포함하지 않는다.

원본 `CharacterMesh0`의 component transform은 `RelativeLocation=(0, 0.00000046424162, -70) cm`, `RelativeRotation=(0, -90, 0)°`이며 `CB_WhiteDog.Properties.Scale=1.15`도 serialized source 값으로 기록했다. catalogue에서 바닥과 카메라에 맞춘 위치·간격·FOV는 표시용 값이며 원작 gameplay 배치 수치가 아니다.

레시피의 `CD_M_Dog_Muscle_001` BoneMod preset은 JSON으로 보존했다. 원작 `xxBoneModPreset`의 축/0 처리와 실행 순서를 확인하지 못했으므로 체형에 임의로 bake하지 않았다.

## 검증과 보관

선택 closure는 311 package, metadata failure는 0이다. 별도 UE 프로세스에서 library, animation batch, assembly, fresh audit를 모두 exit 0으로 완료했고 등록 에셋 125개, 예상 에셋 125개, 임시 package 0개를 확인했다. 일반 UnrealEditor의 실제 frame/resource warmup 뒤 D3D12/SM6에서 master/MI 12개를 compile·reload하고 세 BP의 mesh/material/idle을 다시 로드했다. 최종 lit와 base-color PNG에서 흰색, 회색, 어두운 갈색 계열 외형 세 가지가 구분되는 것을 직접 확인했다.

재현 순서는 `prepare_wild_dog_sources.py` → `build_wild_dog_import_manifest.py` → `prepare_wild_dog_animation_timing.py` → UE library → animation batches → assemblies → fresh audit → 실제 editor render → archive다. UE 단계는 `run_wild_dog_editor_stage.py`, 애니메이션은 `run_wild_dog_animation_batches.py`로 실행한다. 프로세스에는 `-DisablePlugins=ModelContextProtocol -EnablePlugins=GameFeatures -NoSourceControl`을 사용하며 프로젝트 Config/uproject는 바꾸지 않는다.

작업 원본은 `Saved/Extracted/WildDog_20260915`, 외부 archive는 `C:/Users/user/Desktop/카잔/EnemyExtracts/WildDog_20260915`다. 선택 package의 raw cooked 파일, 변환 PSK/PSA/PNG, 모든 분류 JSON, 파생 포즈, 스크립트와 보고서를 SHA-256 목록과 함께 보관한다. Git에는 원본 JSON 전체를 `SourceMetadata.zip`과 `SourceMetadataIndex.json`으로 포함한다. 최종 판정은 `ValidationSummary.json`, `RenderValidationSummary.json`, `FinalExtractionReport.json`, `ArchiveSummary.json`을 따른다.
