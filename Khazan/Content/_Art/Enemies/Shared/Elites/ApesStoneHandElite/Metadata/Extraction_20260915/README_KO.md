# ApesStoneHandElite 실사용 에셋 — 2026-09-15

## 대상과 사용 위치

- 루트: `/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite`
- 시각 조립 BP: `Blueprints/BP_EN_ApesStoneHandElite_Early`, `BP_EN_ApesStoneHandElite_Standard`
- 공용 본체: `Meshes/SK_EN_ApesStoneHandElite`, `Skeletons/SKEL_EN_ApesStoneHandElite`
- 재생용 시퀀스: `Animations/Playback/A_EN_PLAY_*`
- 비교 맵: `Preview/L_EN_ApesStoneHandElite_Catalogue`
- 조사/검증 자료: `Metadata/Extraction_20260915`

원작 package 이름은 `ApesStoneHandElite`, 실제 디자인 폴더는 `BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E`다. `SA_ApesStoneHand_E.Properties.ActorName`은 `바위 원인_정예`, `TIDX=282004`이고 Early는 `원인_바위_정예_Early`, `TIDX=282009`다. 식별값이며 새 gameplay 수치로 적용하지 않는다.

## 버전의 실제 사용 판정

| 원본 종류 | 확인한 용도와 근거 | UE 처리 |
|---|---|---|
| `C_M_ApesStoneHandElite` 및 기본 재질 | `CB_ApesStoneHand_E_Early.CD_RD_M_ApesStoneHandElite_Early_001_GEN_VARIABLE.Properties.FacePartsList[0]`의 최종 mesh/material | Early BP |
| `C_M_ApesStoneHandEliteV3` 및 V3 재질 | `CB_ApesStoneHand_E.CD_RD_M_ApesStoneHandElite_001_GEN_VARIABLE.Properties.FacePartsList[0]`이 V3를 명시 | Standard BP |
| V2 | `CD_RD_M_ApesStoneHandElite_001` CDO의 기본값이지만 위 Standard CB component가 V3로 override | 조사 JSON만 보존; 선택한 실사용 조립에 임포트하지 않음 |
| Early 레시피 CDO의 추가 V3 재질 조합 | 레시피 기본값에는 두 material variation이 있으나 Early CB component가 기본 재질 한 조합으로 배열을 교체 | 임의 조합 생성하지 않음 |
| `C_M_ApesStoneHandElite_EmptyMesh` | CB CharacterMesh0/레시피 BaseMesh의 모듈 조립·애니메이션 carrier | 원본 계약은 보존하고 시각 BP는 실제 전신 메시를 직접 사용 |
| `CM_M_Ghost_ApesStoneHandElite_*`, `AP_ApesStoneHand_E_Wraith` | Ghost/Wraith 특수 표현 관련 자료. 선택 CB·스폰에서 소비 참조를 확인하지 못함 | 조사 JSON 보존, 현재 살아 있는 적 라이브러리에서 제외 |
| `WP_COM_ApesStoneHandElite_Dead_002/003` | StaticMesh 및 환경 배치용 BP 시체 프롭 | 살아 있는 적 모델/애니메이션으로 임포트하지 않음 |
| ControlRig/후처리 AnimBlueprint | 원본 보조 뼈·표현 처리 자료 | JSON/원본 보관, 게임 전용 실행 클래스를 복원한 것으로 간주하지 않음 |

**레시피 CDO만 읽으면 잘못된 버전을 선택한다.** 상속 기본값과 CB의 SCS component template override를 합친 결과가 정본이다. `VariantUsage.json`은 두 레시피 기본값, 각 component override, effective recipe와 제외 이유를 함께 기록한다. V2/Ghost/Wraith가 게임 전체에서 절대 사용되지 않는다는 전수 판정은 아니다.

기존 추출 Level JSON에서 HeinMach의 `SA_ApesStoneHand_E_Early`, `Early2`, `Early3`와 StormPass의 `SA_ApesStoneHand_E_Early`가 모두 `ActorBP_Soft=CB_ApesStoneHand_E_Early`를 참조한다. HeinMach의 스폰 시작 돌진, 대기/경계 동작 및 StormPass의 다른 대기/경계 동작 참조는 `LevelPresence.json`에 그대로 보존한다. Standard는 실제 CB의 최종 구성으로 복원했으며, 위 두 레벨에서 Standard가 스폰된다고 주장하지 않는다.

## 메시 공유와 스켈레톤

기본 메시와 V3의 ActorX chunk를 비교했으며 `MATT0000` 이외의 geometry·UV·vertex color·normal·skin weight·bone·socket chunk는 바이트가 같다. 따라서 전신 메시 하나를 공유하고 BP material override로 두 외형을 구성한다. 원본 두 package와 각 LOD 파일은 외부 archive에 보관한다.

메시의 원본 reference bone은 97개, 선택한 PSA의 공통 레이아웃은 453개다. Yetuga 때처럼 prefix에 helper를 추가하는 방식으로는 맞지 않는다. 모든 mesh bone이 PSA에 존재하고 parent 관계가 이름 기준으로 같은 것을 확인한 뒤 전체 PSA 순서로 재배열했다. `RAWWEIGHTS`의 bone index만 같은 이름의 새 index로 바꾸며 weight 수치·vertex index는 보존한다. 없는 356개 bone은 비가중 helper로 추가한다.

원본 메시 bind transform과 PSA skeleton reference transform에는 실제 차이가 있다. 예를 들어 `Weapon_L`에서 위치 성분 차이가 약 9.53 cm다. 이를 손상으로 간주해 원본 메시 bind를 덮어쓰지 않는다. 공통 bone은 원본 mesh bind를 유지하며, 추가 helper에만 PSA→PSK 좌표 변환을 적용한다. 비교한 원시 변환·index 대응·PSA reference hash는 `ImportManifest.json.body.shared_reference_comparison`, `bone_index_remap`, `animation_reference_layout_sha256`에 있다.

원본 skeleton은 `BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/Yetuga/Model/C_M_Yetuga_Skeleton`이다. Apes 폴더의 애니메이션도 같은 skeleton을 명시한다. 기존 Yetuga 프로젝트 에셋은 수정하지 않고 Apes 라이브러리 자체의 skeleton을 사용한다. 원본 socket 7개 이름·parent·local transform을 mesh-owned socket으로 복원한다. 원본은 skeleton 소유였음을 metadata에 명시한다.

원본 LOD0/1/2는 보관하고 현재 PSK 임포터로 LOD0을 임포트한다. 자동 생성 LOD를 원본 LOD라고 표시하지 않는다.

## 재질·텍스처 복원 범위

선택된 기본/V3 재질 슬롯 Face, Body, Leg, Eye, Damage와 부모를 추적하여 Material Instance 13개, Surface/Eye 표시용 master 2개, 실제 Texture2D binding 31개를 구성한다. 부모의 `CachedExpressionData.Parameters.RuntimeEntries[*].ParameterInfos`와 대응 parameter 값 배열을 결합하고 부모→자식 override를 적용한다. 모든 값의 출처 package는 `parameter_origins`에 있다.

PNG payload와 cooked `SizeX/SizeY` 해상도, 원본 sRGB·compression·LOD group, material 슬롯 순서·이름·scalar/vector/2D texture binding 및 base-property를 검증한다. 저해상도 cooked texture를 authoring `ImportedSize`로 임의 확대하지 않는다.

원작 BBQ 전용 셰이딩 모델의 실행 코드/편집 가능한 graph 연결은 cooked JSON에 없으므로 Surface/Eye master는 명시적인 UE 표시용 재구성이다. 원본 static switch, dissolve·특수 효과 동작을 동일하게 복원했다고 표현하지 않는다. 2D가 아닌 CurveAtlas/Cube/엔진·플러그인 참조의 metadata 전용 처리는 별도로 기록한다.

## 애니메이션 시간축

현재 선택 결과는 원본 PSA 79개를 입력으로 한 **재생용 92개**다. 원작 AP/BlendSpace의 직접 소비 10개와 도달 가능한 Composite 82개다. 전체 이름 검색으로 발견한 모든 원본/Composite를 임포트하지 않는다. Composite의 backing source를 별도 UE 원본 시퀀스로 중복 생성하지 않는다.

- 직접 소비: 원본 `NumFrames`, `SequenceLength`, `RateScale` 기준. sample rate는 `(NumFrames-1)/SequenceLength`이며 10개 모두 30/1 FPS다. PSA의 N/L 표기를 실제 sample FPS로 사용하지 않는다.
- Composite: `AnimationTrack.AnimSegments`의 시작·끝·반복·`AnimPlayRate`와 활성 `DilationCurve.DilationAnimPositions`를 반영한다. 최종 길이를 표현하는 rational FPS로 저장하고 보정 배속을 다시 곱하지 않는다.
- 원본 Composite 길이와 bake 후 길이가 다른 결과는 43개다. 이는 원작 배속/시간축 자료의 적용 결과이며 임의 속도 튜닝이 아니다.
- 원작 AP의 Idle이 `CA_M_Yetuga_Stand_F`를 직접 참조한다. 이름을 바꿔 Apes 자체 원본으로 위장하지 않고 실제 출처를 기록한다.
- 공용 Missile skeleton의 gameplay carrier Composite 6개는 본체 애니메이션이 아니다. JSON을 보관하고 본체 skeleton에 임포트하지 않는다.
- 원본 notify/event 1,000행은 시각/게임플레이 재구현을 위한 metadata이며 원작 custom notify의 실행 코드를 임포트한 것은 아니다.

검증은 저장된 FPS 분수·길이·sample 수·RateScale·root/additive 설정과 모든 시퀀스의 처음/중간/끝 RAW·COMPRESSED 전 bone pose다. 실행 중 hit-stop, actor dilation, AI 상태별 속도/블렌드까지 원작 게임에서 실측한 검증은 아니다.

## Blueprint와 원본 추가 계약

두 BP는 Actor + EnemyBody SkeletalMeshComponent의 시각 조립이며 해당 기본/V3 재질과 원본 AP Idle의 재생용 시퀀스를 설정한다. 시퀀스 RateScale과 single-node play rate의 중복 배속이 없도록 검사한다. AI·전투·이동·피해·GAS 실행 로직은 포함하지 않는다.

원본 `CharacterMesh0.RelativeRotation.Yaw=-90°`를 표시 component에 반영한다. capsule 기준 `RelativeLocation=(-50,0,-240) cm`와 CB의 `Scale=0.8`은 원본 property로 보존한다. 비교용 Actor의 발 원점과 상대 크기는 표시 설정이며 해당 gameplay Scale의 실제 적용 순서를 복원한 것으로 표현하지 않는다.

Early 레시피의 `CD_M_ApesStoneHandElite_Base_001`, Standard의 `CD_M_ApesStoneHandElite_Muscle_001`을 원본 JSON으로 보존한다. Base에도 오른손 손가락 scale override가 있고 Muscle의 `Bip001-Spine1.BoneScale.Z=0` 등 일반적인 bone scale로 무조건 적용하면 외형이 무너질 수 있는 값이 있다. 원작 `xxBoneModPreset`의 0/축 의미와 소비 코드를 확인하지 못했으므로 실행 형태를 임의로 추정해 bake하지 않는다. 따라서 BP 재질 외형과 원작 BoneMod 적용 체형의 완전 일치는 별도 검증 대상이다.

## 재현·보관·검증 진행

기존 Yetuga/BigBear 파이프라인을 바탕으로 `Scripts/Enemies/*apes_stone_hand*.py`를 사용한다. 원본 설정/게임 키는 복사하거나 출력하지 않는다.

작업 루트 `Saved/Extracted/ApesStoneHandElite_20260915`, 외부 보관 `C:/Users/user/Desktop/카잔/EnemyExtracts/ApesStoneHandElite_20260915`다. `discover`는 실제 CB/스폰 참조를 따라가고 `export`는 선택한 모델·PSA·텍스처를 변환한다. 이어서 import manifest → animation timing → UE library → animation batches → assemblies → fresh audit → 실제 editor frame 이후 render → archive 순서다.

현재 원본 참조 closure 387 package와 metadata failure 0을 확인했다. 초기 명칭별 분류 metadata와 최종 선택 closure를 구분한다. 최종 완료 판정은 아래 날짜별 절과 `ValidationSummary.json`, `RenderValidationSummary.json`, `FinalExtractionReport.json`의 실제 성공 결과를 따른다.

### 2026-09-15 저장·시간축·렌더 검증 완료

총 143개 UE 에셋을 저장하고 fresh process에서 검증했다. 메시/스켈레톤 각 1개, 텍스처 31개, MI 13개/master 2개, 재생용 시퀀스 92개, BP 2개/map 1개이며 임시 package는 없다. material parameter는 scalar 1,791개, vector 504개, Texture2D binding 209개를 원본 effective 값과 대조했다. Masked/opacity clip/dithered LOD 등 stock UE base-property도 확인했다.

mesh bind 97개와 skin weight 45,190행의 vertex·가중치 수치·bone 이름 대응을 독립 비교했다. geometry/UV/color/material chunk의 무변경과 기본/V3 geometry 공유 조건도 확인했다. UE LOD0은 24,862 vertices이고 소켓 7개를 대조했다. `audit_apes_stone_hand_sources.py`가 재현 가능한 원본 감사다.

92개 애니메이션의 저장·RAW/COMPRESSED 검사와 각 batch의 실제 process exit 0을 확인했다. direct 10/composite 82, 활성 dilation 44, root motion 70, force root lock 51, additive 1이며 FPS 계약은 40종이다. 최대 길이 오차 `1.9421386721063527e-7 s`, 위치 성분 오차 `0.00010585784912109375 cm`, quaternion 성분 오차 `0.000697791576385498`, scale 오차 `9.5367431640625e-7`이다. 이는 수치 검증 결과이며 gameplay 튜닝값이 아니다.

일반 UnrealEditor의 실제 frame/resource warmup 이후 D3D12/SM6에서 master/MI 15개와 두 BP의 렌더링을 확인했다. 최종 lit/base-color PNG를 직접 열어 몸체·팔다리·머리·바위·피부/털과 눈 색 차이가 표시되는 것을 검사했다. 원작 게임 화면을 캡처해 pixel 단위로 비교한 검증은 아니다.

초기 PNG는 선형 `RTF_RGBA8`로 내보내 어두웠다. 엔진 `TextureRenderTarget2D.cpp`의 sRGB/linear gamma 처리를 확인하고 최종 검수용 target을 `RTF_RGBA8_SRGB`로 변경했다. 중간에 시험한 수동 노출 override는 최종 스크립트에서 제거했다. 에셋의 texture sRGB나 source material 값을 밝게 바꾼 것이 아니다. 최종 캡처·검수 기록은 `RenderValidationSummary.json`, `Reports/ApesStoneHandElite_VisualReview_20260915.json`, `Preview/*.png`다.

재현 시 UE 단계는 `run_apes_stone_hand_editor_stage.py library|assemblies|audit|render`를 사용한다. 애니메이션은 `run_apes_stone_hand_animation_batches.py`로 별도 실행한다. 이 runner는 기존 설정의 GameFeatureData 로드 문제를 피하기 위해 해당 process에서만 `-EnablePlugins=GameFeatures`를 지정한다. 프로젝트 Config/uproject는 변경하지 않는다. 최초 사용자 변경 9개와 Source/Config 41개 파일의 SHA-256이 작업 전과 같음을 확인했다.
