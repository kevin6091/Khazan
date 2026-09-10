# HeinMach·StormPass BigBear Enemy 추출 및 애니메이션 복원 (2026-09-10)

## 완료 범위

- HeinMach와 StormPass의 실제 스폰 메타데이터에서 곰 Enemy를 표적 확인했다.
- 두 레벨이 공통으로 참조하는 `CB_BigBear_E`의 메시, 스켈레톤, 원작 외형 변형 3종, 머티리얼 파라미터, 텍스처 25개와 재생용 애니메이션 102개를 Unreal 프로젝트에 저장했다.
- 공용 경로는 `/Game/_Art/Enemies/Shared/Beasts/BigBear`다. 같은 캐릭터를 레벨별로 복제하지 않고, 서로 다른 스폰·AI 맥락은 metadata로 보존했다.
- 결과는 별도 Unreal 프로세스의 에셋 감사와 D3D12/SM6 렌더 감사에서 통과했다. 이 작업은 `KhazanLocomotionComponent`, Player C++, 기존 인간형 Enemy 자산을 수정하지 않는다.

## 원작 레벨 확인 근거

| 레벨 | 원작 스폰 Actor | 공통 Character BP | AIData | 종속 레벨 및 별도 설정 |
| --- | --- | --- | --- | --- |
| HeinMach | `HeinMach_Spawn_Main01.SA_BigBear_E_2` | `.../BigBear_E/Base_Setting/CB_BigBear_E` | `AI_BigBear_E_NoneBurst` | `HeinMach_SubLV05_Escape_1`; 시작 `AC_BigBear_Basic_Loop_05`, 경계 반응 `AC_BigBear_Basic_End_05` |
| StormPass | `StormPass_Spawn_Main01.SA_BigBear_E` | `.../BigBear_E/Base_Setting/CB_BigBear_E` | `AI_BigBear_E_BurstTutorial` | `StormPass_SubLV05`; PeaceSkill/Patrol 단계와 사망·신호 delegate가 별도 설정됨 |

정확한 property 원문과 전체 object path는 `Metadata/Extraction_20260910/LevelPresence.json`에 있다. 두 스폰의 `ActorBP_Soft`와 `SpawnInfo`가 같으므로 외형·애니메이션은 하나의 BigBear 라이브러리로 관리한다. AI profile 차이는 이 시각 조립 BP에 구현하지 않았다.

## 프로젝트 폴더와 네이밍

```text
/Game/_Art/Enemies/Shared/Beasts/BigBear
├─ Animations/Playback   A_EN_PLAY_* 102개
├─ Blueprints           BP_EN_BigBear_V01~V03 3개
├─ Materials/Masters    M_EN_BigBear_*Preview 2개
├─ Materials/Instances  MI_EN_BigBear_* 10개
├─ Meshes               SK_EN_BigBear 1개
├─ Skeletons            SKEL_EN_BigBear 1개
├─ Textures             T_EN_BigBear_* 25개
├─ Preview              L_EN_BigBear_Catalogue 1개
└─ Metadata/Extraction_20260910
```

Asset Registry 기준 결과는 145개다. AnimSequence 102, Blueprint 3, Material/MI 12, SkeletalMesh 1, Skeleton 1, Texture2D 25, preview map 1이며 staging 또는 redirector 자산은 없다.

## 외형과 머티리얼

- 원작의 유효 조립 recipe는 `CD_RD_M_BigBear_001`, 본체 메시 슬롯은 `Head`, `Upper`, `Lower`, `Eye`다.
- `BP_EN_BigBear_V01`, `V02`, `V03`은 원작 leaf material의 V1/V2/V3 조합이다. 얼굴만 임의 조합한 변형이 아니라 머리·상체·하체의 원작 material variation을 한 세트로 적용한다.
- `C_M_BigBearV2`는 recipe editor inventory에만 있었고 실제 조립 메시로 선택되지 않아 프로젝트에는 중복 본체로 넣지 않았다. `C_M_BigBear_EmptyMesh`도 carrier/archive 성격이라 독립 캐릭터로 만들지 않았다. 두 원본과 metadata는 외부 archive에 보존한다.
- `SK_EN_BigBear`의 LOD0은 30,023 vertices와 material slot 4개를 갖는다. 원작 PSK LOD0/1/2는 archive에 모두 보존했지만 현재 ActorX 임포터가 source LOD chain을 자동 구성하지 않아 프로젝트 메시에는 검증된 LOD0 하나만 있다.
- cooked `M_AKCartoonCharacter`와 `M_BBQCartoonEye`의 proprietary graph topology는 추출물에 없다. 프로젝트의 `M_EN_BigBear_SurfacePreview`, `M_EN_BigBear_EyePreview`가 표시 가능한 UE graph를 제공하며 leaf MI의 scalar 84, vector 16, texture 47 override와 원작 parent path를 metadata로 보존한다. 이를 원작 shader graph의 완전 복원으로 취급하지 않는다.
- 텍스처는 추출 PNG의 실제 cooked payload 크기로 임포트했다. 원작 metadata의 authoring `ImportedSize`와 cooked `SizeX/SizeY`가 다른 항목은 15개다. 예를 들어 V3 Head D는 `ImportedSize=2048×2048`, cooked payload와 프로젝트 자산은 `512×512`다. 없는 고해상도 데이터를 임의 upscale하지 않았다.

## 스켈레톤 복원

원본 메시 PSK에는 71개 reference/weighted bone이 있었지만 76개 PSA가 공통으로 사용하는 레이아웃은 79개였다. 메시 기준 71개만 사용하면 귀·눈꺼풀·털·눈 보조 트랙이 유실되므로, PSA reference pose를 ActorX 좌표계로 변환해 아래 8개 helper bone을 파생 PSK 끝에 추가했다.

- `B_Ear_01_01_Head2`, `B_Ear_02_01_Head2`
- `B_Eyelid_01_01_Head2`, `B_Eyelid_02_01_Head2`
- `B_Hair_01_01_Head2`, `B_Hair_03_01_Neck2`
- `Muscle_L_Eyeball2`, `Muscle_R_Eyeball2`

geometry, skin weight, material과 기존 71개 reference pose는 유지했다. 모든 PSA가 같은 79-bone 순서인지 확인했고, 공통 prefix의 변환 후 reference pose 최대 차이는 약 `5.96e-8`이었다. 프로젝트 정본은 `SK_EN_BigBear`와 `SKEL_EN_BigBear`다.

## 애니메이션과 재생 속도

최종 102개는 모두 `/Animations/Playback/A_EN_PLAY_*`에 있으며 인게임 소비용으로 구성했다.

- `DirectOriginalTimeline` 12개: Stand, Walk F/FL/FR, Run F/FL/FR, LockOnMove F/B/L/R, AddWeak Head. 원작 `NumFrames / SequenceLength`가 모두 30fps 계약이며 그대로 임포트했다.
- `CompositeBake` 90개: 원작 Composite의 `AnimSegmentStartTime`, `AnimStartTime`, `AnimEndTime`, `AnimPlayRate`, `LoopingCount`를 적용하고 활성 `DilationCurve`의 `T_Original/T_Dilation` 시간 매핑까지 포즈 sample에 구웠다.
- 길이 정밀도를 유지하도록 각 결과의 `(samples - 1) / playback_seconds`를 유리수 frame rate로 저장했다. 102개 전체에는 36종의 정확한 FPS 계약이 있고 그중 59개는 `30/1`이다. 비 30fps 자산을 임의 배속한 것이 아니라 Composite 최종 시간축을 자산 자체에 담은 결과다. 모든 재생용 자산의 `RateScale`은 1.0이다.
- 활성 DilationCurve가 적용된 Composite는 38개이며, 그중 최종 duration이 source와 실제로 달라진 것은 37개다. 한 항목은 곡선이 활성이어도 적분된 전체 길이가 같아 두 수가 다르다.
- 원작에서 파생한 설정은 root motion 95개, force root lock 3개(`Peace_Sleep_1/2/3`), local-space/ref-pose additive 1개(`CA_M_BigBear_AddWeak_Head`)다.
- 원작 Notify/event 시간 1,164행은 `PlaybackEventTimes.json`에 보존했다. proprietary Notify class, hit 판정, VFX, audio, AI state rate, actor time dilation과 hit-stop 실행 로직은 AnimSequence만으로 재현되지 않는다.

`AnimationLibrary.csv`는 현재 경로, 유래, source package, frame rate, sample 수, 길이와 root/additive 계약을 조회하는 표다. `AnimationImportManifest.json`은 bake 입력, `AnimationTimingAudit.json`은 계산 결과, `PlaybackEventTimes.json`은 event 시간을 담는다.

## Blueprint 내용

세 Blueprint는 에디터 확인과 이후 gameplay 캐릭터 조립을 위한 시각 Actor다.

- 부모 클래스: `Actor`
- 컴포넌트: `EnemyBody` SkeletalMeshComponent 하나
- 메시/스켈레톤: 공통 `SK_EN_BigBear` / `SKEL_EN_BigBear`
- 머티리얼: 각 V01~V03의 Head/Upper/Lower와 공통 Eye 4개
- 기본 표시 애니메이션: `A_EN_PLAY_CA_M_BigBear_Stand_F`, loop/play 활성, play rate 1.0
- preview transform: location 0, scale 1, yaw -90도
- collision: 비활성
- metadata role: `EnemyArtRole=VisualAssembly_NoGameplayAI`

AI, GAS Ability, 피해·공격 collision, ragdoll, 원작 AnimGraph와 Notify 실행은 들어 있지 않다. 각 Blueprint에는 HeinMach/StormPass의 source actor, AIData, dependent level 경로가 metadata로 기록되어 있어 외형이 어느 Enemy에서 왔는지 추적할 수 있다.

## 검증 결과

- `ValidationSummary.json`: 145/145 registered asset, temporary 0, texture 25, material 12, 79 bones, 30,023 vertices, animation 102, Blueprint 3 모두 통과.
- 애니메이션 102개 각각의 첫/중간/마지막 sample에서 모든 bone을 RAW와 COMPRESSED로 평가했다. 최대 오차는 위치 `9.9658966e-5 cm`, quaternion component `7.5748563e-4`, scale `6.1571598e-5`, 길이 `1.1981201e-7 s`다.
- `RenderValidationSummary.json`: D3D12/SM6, RTX 3060 Ti에서 12개 material의 VS/PS compile과 sampler 사용을 확인했고 3개 BP의 mesh/material/animation 재로드를 통과했다. material/shader compiler/fatal/Python 오류는 없었다.
- preview map의 650cm 간격, 조명 세기 3.0/1.0과 카메라 FOV 70도는 원작 gameplay 수치가 아니라 카탈로그 표시를 위한 어시스턴트 선정값이다.

## 사용 및 재현 자료

1. Content Browser에서 `/Game/_Art/Enemies/Shared/Beasts/BigBear/Preview/L_EN_BigBear_Catalogue`를 열면 V01~V03을 함께 볼 수 있다.
2. 실제 캐릭터 기반에는 원하는 `BP_EN_BigBear_V*`의 공통 mesh와 material 구성을 사용한다.
3. 동작 선택은 `Metadata/Extraction_20260910/AnimationLibrary.csv`에서 찾고 `/Animations/Playback/A_EN_PLAY_*`를 1.0배로 재생한다.
4. 전투에 연결할 때는 프로젝트의 AI/Ability/AnimBP·Montage/Notify/Cue 계약을 별도로 구현한다. 시각 Blueprint 자체를 전투 AI 완성본으로 사용하지 않는다.

원본 cooked 309 package/644개 파일, ActorX, PNG, 전체 metadata, 파생 PSK, 보고서와 재현 스크립트는 `C:/Users/user/Desktop/카잔/EnemyExtracts/BigBear_20260910`에 보존한다. `ArchiveSHA256.json`으로 파일별 무결성을 검증하며 프로젝트 정본 보고서는 `Content/_Art/Enemies/Shared/Beasts/BigBear/Metadata/Extraction_20260910/FinalExtractionReport.json`이다.
