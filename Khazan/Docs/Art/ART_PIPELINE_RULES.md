# Art / Resource 파이프라인 규칙

## 공통 원칙

- FModel 추출 루트는 `C:\Users\user\Desktop\카잔`이다.
- 원본 package path, object name, component hierarchy, material slot, transform, source 파일 경로를 provenance로 보존한다.
- basename만으로 에셋을 병합하지 않는다. 동일 이름이라도 원본 package path가 다르면 별도 source key로 취급한다.
- 임포트, 머티리얼 복원, 배치, Level 저장은 단계별로 분리하고 각 단계에 재실행 가능한 script와 JSON report를 남긴다.
- 기존 canonical metadata/report로 답할 수 있으면 Content나 FModel root를 다시 전수조사하지 않는다.

## 캐릭터와 ActorX

- FModel PSK 입력: `C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Art\Character\CHA_Model`
- UE 출력: `/Game/_Art/Kazan/FModel/PSK`
- 임포터: `Plugins/UnrealPSKPSA`
- 자동화 entry point: `Scripts/import_fmodel_psk.py`
- 카잔 원본 base: `C_P_Kazan.psk`; UE 조립 base: `/Game/_Art/Kazan/Character/Meshs/SKM_Khazan`
- Arm, Face, Hair, Leg, Shoes, Torso는 독립 파츠이며 의상·상태 variant를 별도 메시로 유지한다.

## HeinMach 복원

- source Level/asset root: `C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Level\HeinMach`
- 라이브 Level: `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment`
- corrected source: `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets`
- override material: `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials`
- foliage: `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FoliageBatches`
- fog: `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FogSheets`
- terrain preview: `/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/TerrainPreview`
- `Before*`, `LightingOnly`, `FoliageImportSandbox` Level은 백업 또는 staging이며 완성본으로 사용하지 않는다.
- negative scale만 보고 reverse culling이나 winding 반전을 일괄 적용하지 않는다. source winding, determinant, material TwoSided를 함께 표적 검사한다.
- 생성 머티리얼은 저장만으로 완료 처리하지 않고 compile error, WorldGrid fallback, blend mode, TwoSided, viewport 표현을 확인한다.
- source/target world를 같은 Python 실행에서 반복 load하지 않는다. target 저장 후 Editor를 재시작하고 라이브 Level에서 감사한다.

## 완료 판정

- 우선 검증 script: `Scripts/HeinMach/audit_heinmach_final_reconstruction.py`
- 우선 canonical report: `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`
- `all_checks_passed == false`일 때만 mismatch 목록으로 조사 범위를 좁힌다.
- 원본 WLM/weightmap 또는 custom shader graph가 없으면 preview를 원본 완전 복원으로 기록하지 않는다.

## 2026-09-01 HeinMach 후속 규칙

- 정적 환경 누락 판단은 먼저 `Saved/ImportReports/HeinMach_StaticCoverage_Closure_Audit.json`을 확인한다. `unresolved_non_fog_static_mesh_count == 0`이면 FModel/Content 전수조사를 반복하지 않는다.
- 최종 live 기준은 `Saved/ImportReports/HeinMach_Final_Reconstruction_Audit.json`의 액터 9,449개와 31/31 통과다. 과거 2,938개 기준은 더 이상 완료 판정에 사용하지 않는다.
- root Prop은 `HeinMach_RootTemplateCoverage_Audit.json`의 resolved placement 9,104개를 기준으로 한다. 미해결 record 수만 보고 정적 메시 누락으로 판정하지 않고 `root_component_type`과 actor type을 함께 본다.
- BaseColor에 alpha channel이 있다는 이유만으로 Translucent parent를 유지하지 않는다. FModel material JSON의 `BasePropertyOverrides.BlendMode`, `TwoSided`, `OpacityMaskClipValue`를 authoritative source로 사용한다.
- Khazan 환경 packed `*_S` texture는 AO=R, Roughness=G, Metallic=B다. UE 머티리얼의 component vector와 texture enable scalar까지 함께 검증한다.
- 머티리얼의 effective blend/TwoSided를 검사할 때 ultimate base Material만 보지 않는다. 중간 parent Material Instance의 base-property override까지 전체 상속 체인을 해석한다.
- source surface가 `BLEND_Masked`이면 MI에 Masked override와 source clip 값을 적용하고 alpha texture 사용을 유지한다. 나무·천·거미줄 등 source TwoSided=true 항목만 TwoSided로 복구한다.
- Landscape geometry 기준은 원본 JSON 2개와 USDA component 57개다. 57개 모두 `M_HeinMach_Landscape_Recovery`를 사용하며 WorldGrid fallback은 허용하지 않는다.
- foliage 전용 감사에서 전체 map actor 수를 고정 비교하지 않는다. 후속 root/Landscape/light pass가 액터를 추가할 수 있으므로 foliage의 113배치·12,495 instance와 자체 transform/material mismatch만 검증한다.
- 시각 검수는 `HeinMach_PlayableCameraAnchors.json`의 6개 source PlayerStart 좌표와 source-facing rotation을 우선 사용한다. 원본 시작점이 벽이나 식생에 가깝더라도 미관상 임의 이동하지 않는다.
- 카메라 캡처 전 actor selection을 해제하고 viewport realtime/redraw를 보장한다. 이 상태는 편집기 임시 상태이며 Level에 저장할 설정이 아니다.
- Fog 요청이 명시되지 않은 Art 작업에서는 Fog actor/material을 제외하고 전후 count 50 및 SHA-256을 검증만 한다.
- 머티리얼 수정 전 바이너리는 `Saved/ArtBackups/HeinMach_MaterialRendering_PreFix`와 `Saved/ArtBackups/HeinMach_AlphaSurface_PreFix`에 보존한다.
- 저장 후 UE Editor를 재시작하고 material, root, child, Landscape, foliage, final audit 순으로 재검증해야 완료다.

## 2026-09-02 Fog / Lighting 및 안전 검수 규칙

- Fog/Light 폴리싱 정본 script는 `Scripts/HeinMach/polish_heinmach_fog_lighting.py`, 정본 report는 `Saved/ImportReports/HeinMach_FogLighting_Polish.json`이다.
- Fog sheet 원본 배치를 바꾸지 않는다. 50개 transform hash `3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48`을 전후 비교한다.
- source light 89개는 FModel metadata 값을 우선하며 preview route fill은 `HeinMach/Reconstructed/PreviewLighting/RouteFill` 폴더에 격리한다.
- 원본 `xxVolumetricMist` shader가 없으므로 `HM_PreviewVolumetricFog`는 명시적으로 preview approximation으로 유지한다.
- `M_HeinMach_FogSheet_Preview`의 TextureSample UV 입력명은 UE 5.8에서 `UVs`다. `Coordinates`로 연결하면 graph가 조용히 끊기므로 사용하지 않는다.
- Fog preview material은 metadata tag `KhazanFogPreviewVersion=4`, Landscape recovery material은 `KhazanLandscapeRecoveryVersion=2`로 재생성 여부를 판정한다.
- Final audit가 다른 맵을 직접 load한 직후에는 actor 등록이 한 editor tick 이상 늦을 수 있다. 액터 수가 9,452 미만이면 재임포트하지 말고 먼저 로딩 완료 후 동일 audit를 한 번 더 실행한다.
- 시각 캡처는 필수 검증이 아니다. report/log로 판정 가능하면 생략한다.
- 캡처가 반드시 필요할 때만 `ue_health` 확인 후 active viewport에 Rider 단일 `take_screenshot`을 사용한다. HighResScreenshot automation API와 다중 viewport config 변경은 금지한다.
- 캡처용 actor, selection, realtime/view mode 변경은 임시 상태이며 Level에 저장하지 않는다.
- 현재 최종 기준은 actor 9,452, root 9,104, child 27, foliage 113/12,495, Landscape 57, terrain 2, Fog 50, source light 89, preview environment 4, route fill 5, preview volumetric fog 1이다.

## 2026-09-02 사용자 편집 보존 및 최적화 규칙

- HeinMach 복원·배치·감사 전에 `HeinMach_UserExclusions.json`, `HeinMach_OptimizationExclusions.json`, `HeinMach_ManualOverrides.json`을 반드시 읽는다.
- user exclusion 10개와 optimization exclusion 109개는 metadata에 원본 record가 남아 있어도 재생성하지 않는다.
- `do_not_reset=true`인 transform override는 raw source transform보다 `preserved_transform`을 우선한다.
- 최적화 삭제는 단일 StaticMeshComponent Prop 사이에서 mesh, resolved material, transform, visibility, render flag, shadow, reverse culling, mobility, collision state, tag가 모두 같은 exact duplicate에만 허용한다.
- 이름의 `Collision`, 경로 거리, occlusion 추정, source layer만으로 액터를 제거하지 않는다. 경로에서 보이는 오브젝트는 보존한다.
- FModel `LightColor` byte는 raw `unreal.Color`로 component property에 직접 기록한다. byte를 정규화한 뒤 `SetLightColor(..., True)`를 호출하지 않는다.
- 코드에서 linear color로 선언한 preview light만 sRGB 변환 경로를 사용하며, source light와 preview light를 같은 변환 정책으로 처리하지 않는다.
- `IsNull=true`이고 texture가 비어 있는 inherited LOD material이 WhiteSquare로 보이면 원본 흰색으로 확정하지 않는다. 같은 material family의 textured sibling과 base-property override를 표적 비교한 뒤 별도 recovered material로 복구한다.
- 튜토리얼 Art 복원은 source PlayerStart와 spawn anchor/환경까지다. AI, UI, gate, loadout은 Engineering 작업으로 분리한다.
- 최신 완료 기준은 actor 9,336, root 8,992, child 27, foliage 113/12,495, Landscape 51, terrain 1, Fog 50, source light 89, preview environment 4, route fill 5, preview volumetric fog 1, tutorial 3이다.

## 2026-09-03 DAS AnimSequence 런타임 준비 규칙

- 임포트 원본 AnimSequence를 직접 자르거나 marker를 추가하지 않는다. `/Game/_Art/Kazan/Animation/Locomotion/Runtime/<Weapon>`에 런타임 복사본을 만들고 원본 package path를 metadata로 보존한다.
- DAS 로코모션의 선택 기준은 basename 키워드가 아니라 Dual Axe Sword 아래 package path에 `Locomotion`이 포함되는지다. 공격·스킬·장착 package에서 우연히 Idle, Walk, Run 같은 단어가 일치해도 포함하지 않는다.
- 런타임 이름은 `RT_<WeaponAbbreviation>_<Context>_<Motion>_<Direction>_<Role>` 순서를 기본으로 한다. Dual Axe Sword 약어는 `DAS`, 반복 재생 클립의 suffix는 `Loop`다.
- 현재 FBX가 모두 249 frame이라고 해서 249 frame 전체를 사용하지 않는다. PSA `NumRawFrames`와 실제 반복 주기를 먼저 확인하고, 현재 DAS 변환본의 일반 cutoff는 마지막 중복 sample을 제외한 `NumRawFrames - 2` frame index다.
- 긴 반복 take는 전신 pose가 다시 이어지는 첫 완전 주기를 선택한다. 발 위치만 가까운 지점에서 자르지 말고 골반과 상체 주기도 함께 확인한다.
- source가 원본 PSA보다 짧으면 없는 pose를 보간으로 만들어 완료 처리하지 않는다. 사용 가능한 범위를 보존하고 audit warning과 재-export 필요 frame 수를 기록한다.
- 인플레이스 런타임 복사본은 Root Motion을 끄고 Force Root Lock과 Ref Pose lock을 적용한다. 전이 클립의 authored root track 이동은 허용하되 실제 추출이 꺼졌는지 확인하고, 순환 loop의 root는 별도로 정지 여부를 감사한다.
- 순환 loop의 발 접촉은 UE native `FootstepAnimEventsModifier`로 고해상도 평가한 뒤 중복 구간을 합치고 실제 import frame rate에 스냅한다. detector 결과가 불안정한 클립은 반대발 위상 추정만으로 확정하지 않고 pose/contact 후보를 함께 기록한다.
- Sync Marker 이름은 `LeftFoot`, `RightFoot`, marker track은 `LocomotionSync`로 통일한다. Anim Graph의 Sync Group `Locomotion`은 에셋 track과 별도로 설정한다.
- builder는 정확한 runtime target만 교체하는 idempotent 작업이어야 한다. 원본 수량·길이·marker 무변경, runtime inventory, skeleton, trim, naming, root 설정, metadata와 marker를 fresh-process audit로 확인한다.
- DAS 정본 builder는 `Scripts/Animation/build_das_locomotion_runtime_library.py`, 정본 audit는 `Scripts/Animation/audit_das_locomotion_runtime_library.py`다. 최신 결과는 각각 `Khazan_DAS_Locomotion_RuntimeBuild.json`과 `Khazan_DAS_Locomotion_RuntimeAudit.json`이다.

## 2026-09-09 Enemy 임포트의 검증된 주의점

- Enemy source lookup은 full package path를 키로 사용한다. basename이 같은 `BASE_Normal`과 몸체/무기 `CA_M_EmpBow_Stand_F`도 다른 원본이다. 기존 destination 이름도 신규 이름 충돌 검사에 예약한다.
- 원본 `NumFrames`, `SequenceLength`, `RateScale`, composite segment 배속, 활성 DilationCurve를 분리 보존한다. CUE ActorX의 `N/L` AnimRate를 `(N-1)/L` sample rate 대신 적용하지 않는다. `PlaybackClips`는 시간 보정을 bake했으므로 동일 보정을 다시 곱하지 않는다.
- UE 5.8의 AnimSequence factory는 압축 target frame rate도 초기화한다. 임의 rational rate를 controller에만 뒤늦게 설정하는 방식과 공약수 bridge는 압축 ensure/fatal을 일으킬 수 있다. 신규 자산 생성 동안만 AnimationSettings CDO의 default rate를 목표값으로 설정하고 NEVER notify로 즉시 복원한다. Config 저장은 하지 않으며 hash로 확인한다.
- 긴 임포트는 작은 commandlet 배치로 수행한다. Python 보고서가 passed여도 비동기 압축 작업이 나중에 실패할 수 있으므로 프로세스 정상 종료까지 확인한다. 현재 정본은 `Scripts/Enemies/import_enemy_expansion_animations.py`, `run_enemy_animation_batches.py`다.
- Python `unreal.Rotator`는 모든 축을 keyword 인자로 명시한다. UE 5.8에서 `(0,-90,0)`은 yaw가 아니라 pitch를 바꾼다. 뼈 pose 검사와 별도로 실제 BP component rotation, head/pelvis 높이, 장비 부착을 확인한다.
- 파츠 통합 전 실제 사용 bone의 bind transform 일치를 검사한다. 빈 carrier의 미사용 cloth bone을 무조건 기준으로 삼지 않는다. 서로 다른 source bind를 가진 중갑 파츠는 각 skin을 보존하고 동일 애니메이션 시간으로 재생한다.
- 예전 조합을 Archive로 이동한 뒤 destination 저장만으로 redirector가 디스크에 남았다고 가정하지 않는다. 이동 대응표와 저장된 destination을 확인하고 과거 metadata lookup에 적용한다.
- 재조사 전 `HeinMachEnemyV2_FinalAudit.json`과 각 manifest를 읽고 실패한 항목만 표적 검증한다. 원본 전용 shader/RNG/physics 구현이 없는 상태를 완전한 원작 재현으로 표시하지 않는다.

### 2026-09-09 Enemy 정리 이후 적용 규칙

- 현재 에셋 기준은 `Metadata/Cleanup_20260909/RetainedAssets.json`과 `HeinMachEnemy_CleanupAudit_20260909.json`이다. 이전 import manifest·archive 이동표는 추출/이동 당시의 기록이며 현재 존재 목록이 아니다. 사용자가 제거한 미사용 자산을 전체 builder 재실행으로 되살리지 않는다.
- 캐릭터 삭제는 사용할 BP·보존 애니메이션·카탈로그 및 외부 참조를 root로 두고 hard/soft dependency closure를 구한 뒤 수행한다. 개별 source 파츠라도 중갑/무기/preview/pose carrier에 필요하면 남긴다.
- `DeleteLoadedAssets`의 성공값만으로 디스크 삭제를 확정하지 않는다. 이번에는 미참조 texture 1개가 남아 UE 종료 후 백업/hash/정확한 경로를 확인하고 단일 파일을 정리했다. 별도 UE 프로세스에서 남긴 자산 hash·BP 재로드·누락 참조를 확인한다.
- 재생용 시퀀스 중 `EquivalentSourceTimeline`은 후속 통합 후보이며, sample 수·포즈·소비 참조까지 확인한 뒤 canonical 자산을 선택한다. 이번에 시퀀스를 삭제하지 않았고 시간축이 변경된 271개와 동일한 451개를 구분했다.

### 2026-09-09 원본 애니메이션 삭제의 확인된 경계

- `SourceSequences`라는 폴더명만으로 인게임 미사용이라고 가정하지 않는다. 현재 BP와 원작 AP/BlendSpace/WeaponSlot/Notify에 직접 원본 참조가 존재한다. `AnimationPruning_20260909`의 소비 분석과 현재 UE 참조를 함께 확인한다.
- Composite의 body bake는 내부 Weapon Notify가 참조하는 별도 무기 시퀀스를 대체하지 않는다. 현재 미참조라도 대응 재생용이 없는 동작은 불필요하다고 확정하지 않는다.
- 최신 UE inventory는 `Metadata/AnimationPruning_20260909/RetainedAssets.json`이다. 확인된 backing source 549개를 제거하고 Playback 722/Source 162/기존 Idle 3개를 남겼다. 전체 importer로 삭제 대상을 되살리지 않는다.
- UE 5.8 AnimSequence는 `data_model`이 비어 있고 `AnimationSequencerDataModel`을 사용할 수 있다. 읽기 검증 시 `seq.controller.get_model_interface().get_frame_rate()` 및 `get_number_of_keys()`를 사용한다.
- GUI와 별도 감사 commandlet을 함께 실행할 때 실험적 ModelContextProtocol의 동일 포트 충돌이 발생하면 감사 프로세스에만 `-DisablePlugins=ModelContextProtocol`을 적용한다. 프로젝트/GUI 설정을 바꾸지 않는다. Python passed와 최종 process exit/로그 오류 수를 함께 확인한다.

### 2026-09-09 Enemy 재생 라이브러리 현행 규칙

- 현행 Enemy AnimSequence는 병종별 `<family>/Animations/Playback` 한 폴더와 `A_EN_PLAY_*` 접두사를 사용한다. `SourceSequences`, `PlaybackClips`, `*SourceReferences` 애니메이션 경로를 신규 소비자에 사용하지 않는다.
- `A_EN_PLAY_AC_*`는 주로 Composite bake, `A_EN_PLAY_CA_*`는 직접 원본 시간축이다. AC/CA는 원작 basename이므로 의미를 이름만으로 추정하지 않고 `PlaybackDerivation`, `OriginalPackage`, `TimingContract`를 읽는다.
- rename은 UE AssetTools로 수행해 Blueprint hard/soft 참조를 함께 갱신한다. old package에 참조 또는 ObjectRedirector가 남지 않았는지 fresh registry에서 확인하고, JSON/CSV history를 redirector 대신 런타임 경로로 사용하지 않는다.
- 동일 원본의 중복 자산 삭제는 Skeleton/FPS/sample/길이/root 계약과 모든 프레임·bone의 RAW/COMPRESSED pose를 확인한 뒤 수행한다. 수치 허용치는 gameplay 튜닝값과 구분해 보고한다.
- 최신 inventory는 `Metadata/AnimationStructure_20260909/CurrentAssets.json`, current animation lookup은 `AnimationLibrary.csv`와 `RenameMap.json`이다. 이전 전체 importer를 실행해 옛 두 폴더를 복구하지 않는다.

## 2026-09-10 비인간형 Enemy 추출에서 확인한 규칙

- 여러 레벨의 스폰이 같은 `ActorBP_Soft`/character recipe를 참조하면 메시·머티리얼·애니메이션을 레벨별로 복제하지 않는다. 공용 라이브러리를 만들고 각 source actor, AIData, dependent level, 시작 동작 같은 차이를 metadata에 분리 기록한다.
- SkeletalMesh PSK bone 수만으로 animation skeleton을 정하지 않는다. 선택한 모든 PSA의 bone 이름·순서·parent와 reference pose를 먼저 비교한다. PSA 전용 helper bone이 있으면 메시의 geometry/weight와 기존 prefix를 보존한 채 변환된 PSA reference pose로 추가하고, 모든 animation이 같은 레이아웃인지 검증한다.
- texture metadata의 authoring `ImportedSize`와 cooked `SizeX/SizeY` 및 실제 PNG payload를 구분한다. UE에는 추출된 cooked payload를 정확히 임포트하며 원본 데이터가 없는 큰 해상도를 생성하지 않는다. 차이는 resolution contract 보고서에 남긴다.
- Composite bake마다 root motion, force root lock, additive 등 property dictionary를 새로 초기화한다. 이전 clip 값이 다음 clip에 남지 않도록 source-derived flag를 asset별로 다시 읽고 최종 inventory에서 개수를 검증한다.
- UE 5.8 Python에서 `AnimSequence.get_data_model()`이 없으면 `sequence.controller.get_model_interface()`로 frame rate와 key 수를 읽는다. 저장 후 fresh process에서 RAW와 COMPRESSED 포즈를 모두 평가한다.
- Composite의 segment trim, play rate, repeat와 DilationCurve를 포즈 시간축에 bake한 자산은 정확한 최종 길이를 표현하는 frame-rate contract를 저장하고 RateScale 1.0으로 소비한다. 30fps source라는 이유로 모든 baked 결과를 30fps로 강제하지 않는다.
