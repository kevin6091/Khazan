# WildBoar 실사용 에셋 — 2026-09-15

## 결과와 프로젝트 위치

- 루트: `/Game/_Art/Enemies/Shared/Beasts/WildBoar`
- 공용 본체: `Meshes/SK_EN_WildBoar`, `Skeletons/SKEL_EN_WildBoar`
- 시각 조립 BP: `Blueprints/BP_EN_WildBoar_CoatV1`, `BP_EN_WildBoar_CoatV2`, `BP_EN_WildBoar_CoatV3`
- 재생용 시퀀스: `Animations/Playback/A_EN_PLAY_*`
- 비교 맵: `Preview/L_EN_WildBoar_Catalogue`
- 원본 근거와 검증 자료: `Metadata/Extraction_20260915`

최종 Unreal 라이브러리는 Asset Registry 기준 109개다. SkeletalMesh/Skeleton 각 1개, Texture2D 20개, source Material Instance 7개, 표시용 master 2개, 재생용 AnimSequence 74개, 외형 BP 3개와 catalogue map 1개로 구성된다. 작업용 원본 AnimSequence나 임시 package는 남기지 않았다.

## 레벨 사용처와 버전 판정

표적 레벨 JSON `BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01`과 `BBQ/Content/_Kazan_/Level/StormPass/StormPass_Spawn_Main01`을 조사했다. HeinMach에는 WildBoar spawn이 없고, StormPass에는 `ActorBP_Soft=/Game/_Kazan_/Design/Monster/Beast/WildBoar_New/Base_Setting/CB_WildBoar_New`인 spawn handler 2개가 있다. 이번 실사용 정본은 `CB_WildBoar_New`다.

사용자 관찰처럼 캐릭터 종류와 geometry는 하나지만, 원본 RandomLook 데이터에는 coat가 하나만 있지 않다. `CB_WildBoar_New`의 SCS component `CD_RD_M_WildBoar_001_GEN_VARIABLE`은 `CD_RD_M_WildBoar_001` CDO의 `FaceMesh`, `FacePartsList[0].MaterialVariations`, `PartsIndexCache[ENPCParts::Face].IndexTable`을 그대로 사용한다. cache key 0, 1, 2가 V1/V2/V3 재질과 정렬되어 있어 세 결과 모두 live 선택 대상이다.

| 프로젝트 외형 | 원본 material index | 실제 재질 조합 |
|---|---:|---|
| `CoatV1` | 0 | `CM_M_WildBoar`, `CM_M_WildBoar_Eye` |
| `CoatV2` | 1 | `CM_M_WildBoarV2`, `CM_M_WildBoar_Eye` |
| `CoatV3` | 2 | `CM_M_WildBoarV3`, `CM_M_WildBoar_Eye` |

레시피의 단일 `FaceMeshSelectedIdx=1`이나 `MaterialSelectedIdx=2`만 보고 한 외형으로 고정하지 않았다. 실제 선택 범위는 `PartsIndexCache`를 함께 읽어 판정했다. CDO 원문, effective recipe, 세 조합과 spawn 증거는 `VariantUsage.json` 및 `LevelPresence.json`에 보존했다.

`C_M_WildBoar_EmptyMesh`는 원작 모듈 조립·애니메이션 carrier다. `C_M_WildBoar_BodyHit`, `_IKHit`, `_PA`, `_CtrlRig`는 hit/physics/control 보조 자료이며 표시 캐릭터 geometry가 아니다. 원본 metadata는 보관하되 UE 시각 BP의 추가 mesh로 만들지 않았다.

## 메시·스켈레톤·LOD

`C_M_WildBoar`, `C_M_WildBoarV2`, `C_M_WildBoarV3` ActorX를 비교했다. 세 파일은 `MATT0000`을 제외한 geometry, UV, normal, vertex color, skin weight, bone, socket payload가 바이트 단위로 같다. 따라서 공용 `SK_EN_WildBoar` 하나에 세 material override BP를 구성했다. 버전명이 다르다는 이유로 동일 geometry를 세 벌 저장하지 않는다.

원본 mesh bind 71개와 skin weight 12,528행을 독립 감사했고 bone 추가는 0개다. 원본 LOD0은 points 7,402, wedges 9,004, faces 13,562이며 UE LOD0 render vertex는 9,012개다. 원본 socket 9개의 이름·parent·local transform도 확인했다.

원본 LOD0/1/2는 외부 archive에 보관한다. 현재 프로젝트에는 검증한 LOD0 하나만 임포트했으며 자동 생성 LOD를 원본 LOD라고 표시하지 않는다.

## 재질·텍스처·셰이더

선택된 coat 세 조합과 부모를 따라 Texture2D 20개와 Material Instance 7개를 임포트했다. 부모 parameter 선언과 scalar/vector/texture 배열을 결합하고 부모→자식 override를 적용했다. fresh audit에서 scalar 924개, vector 266개, Texture2D binding 106개를 effective source 값과 대조했다. 원본 sRGB, compression, LOD group과 cooked payload 해상도를 사용하며 authoring `ImportedSize`로 임의 확대하지 않았다.

원작의 cooked BBQ 전용 shader graph와 custom shading model 실행 코드는 편집 가능한 형태로 복구할 수 없다. `M_EN_WildBoar_SurfacePreview`와 `M_EN_WildBoar_EyePreview`는 보존된 원본 texture/scalar/vector/base-property를 Unreal에서 표시하는 adapter다. 전용 static switch, dissolve와 특수 효과를 원본과 동일하게 구현했다고 간주하지 않는다. 원본 부모·상속값·미지원 texture parameter는 metadata와 raw cooked archive에 남겼다.

## 애니메이션 시간축

`AP_WildBoar_New`에서 도달 가능한 원본 PSA 61개와 Composite 63개를 추적했다. 최종 UE에는 실제 재생 결과 **74개**만 둔다.

- `DirectOriginalTimeline` 11개는 원본 `NumFrames`, `SequenceLength`, `RateScale`을 사용하며 `(NumFrames-1)/SequenceLength`가 모두 30/1 FPS다.
- `CompositeBake` 63개는 source segment의 구간, 반복, `AnimPlayRate`와 활성 `DilationCurve.DilationAnimPositions`를 포즈 시간축에 반영한다. 최종 길이를 정확히 표현하는 rational sample rate로 저장하고 UE `RateScale=1.0`에서 재생한다.
- 원본 Composite 표시 길이와 bake 결과가 달라진 18개는 source segment/dilation 적용 결과이며 임의 속도 튜닝이 아니다.
- root motion 26개, force root lock 9개, additive 0개를 원본 property와 대조했다.
- 원본 notify/event 460행의 원시 시간과 bake 후 대응 시간은 `PlaybackEventTimes.json`에 보존했다. 원작 custom notify 실행 코드를 구현한 것은 아니다.

74개 전부의 저장 FPS 분수, sample 수, 길이, root 설정과 처음/중간/끝의 RAW·COMPRESSED 전 bone pose를 검사했다. 최대 길이 오차는 `1.1080932615925576e-7 s`, 위치 성분 `9.1552734375e-5 cm`, quaternion 성분 `9.894371032714844e-5`, scale `7.62939453125e-5`다. 이 검증은 asset 시간축과 포즈 복원에 관한 것이며 runtime hit-stop, actor dilation, AI 상태별 재생률까지 측정한 결과는 아니다.

## Blueprint 역할과 원본 수치

각 BP는 Actor 아래 `EnemyBody` SkeletalMeshComponent 하나만 가진 시각 조립 에셋이다. 공용 mesh, 해당 coat의 2개 material override와 `A_EN_PLAY_CA_M_WildBoar_Stand_F`를 single-node 방식으로 연결하고 play rate는 1.0이다. AI, 공격 판정, 이동, GAS, 피해, 부위 파괴와 원작 notify 실행은 포함하지 않는다.

원본 `CharacterMesh0` component transform은 `RelativeLocation=(-40, 0, -200) cm`, `RelativeRotation=(0, -90, 0)°`다. `CB_WildBoar_New` JSON에는 serialized `Scale` property가 없으므로 catalogue의 1.0은 **표시용 fallback**이다. 원작 gameplay scale이라고 주장하지 않는다. catalogue의 배치 간격, 카메라와 조명도 표시용 수치로 별도 기록했다.

## 검증과 보관

선택 closure는 283 package, metadata failure는 0이다. 별도 UE 프로세스에서 library, animation batch, assembly, fresh audit를 모두 exit 0으로 완료했고 등록 에셋 109개, 예상 에셋 109개, 임시 package 0개를 확인했다. 일반 UnrealEditor의 실제 frame/resource warmup 뒤 D3D12/SM6에서 master/MI 9개를 compile·reload하고 세 BP의 mesh/material/idle을 다시 로드했다. 최종 lit와 base-color PNG에서 짙은색, 밝은색, 갈색 계열 coat 세 가지가 구분되는 것을 직접 확인했다.

재현 순서는 `prepare_wild_boar_sources.py` → `build_wild_boar_import_manifest.py` → `prepare_wild_boar_animation_timing.py` → UE library → animation batches → assemblies → fresh audit → 실제 editor render → archive다. UE 단계는 `run_wild_boar_editor_stage.py`, 애니메이션은 `run_wild_boar_animation_batches.py`로 실행한다. 프로세스에는 `-DisablePlugins=ModelContextProtocol -EnablePlugins=GameFeatures -NoSourceControl`을 사용하며 프로젝트 Config/uproject는 바꾸지 않는다.

작업 원본은 `Saved/Extracted/WildBoar_20260915`, 외부 archive는 `C:/Users/user/Desktop/카잔/EnemyExtracts/WildBoar_20260915`다. 선택 package의 raw cooked 파일, 변환 PSK/PSA/PNG, 모든 분류 JSON, 파생 포즈, 스크립트와 보고서를 SHA-256 목록과 함께 보관한다. Git에는 원본 JSON 전체를 `SourceMetadata.zip`과 `SourceMetadataIndex.json`으로 포함한다. 최종 판정은 `ValidationSummary.json`, `RenderValidationSummary.json`, `FinalExtractionReport.json`, `ArchiveSummary.json`을 따른다.
