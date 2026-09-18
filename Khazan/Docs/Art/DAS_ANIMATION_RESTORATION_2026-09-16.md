# DualAxeSword 원본 시간축·Dilation·Root Motion 복원

## 2026-09-16 작업 범위

- 원작 `DualAxeSword` Art 폴더의 `AnimSequence` 453개와 DualAxeSword 스킬 Composite가 참조하는 외부 카잔 시퀀스 4개, 합계 457개를 cooked metadata 및 ActorX PSA와 대조했다.
- 프로젝트에 이미 있는 444개 source AnimSequence 가운데 현재/의미상 로코모션 107개는 검사만 하고 쓰기 대상에서 제외했다.
- 비로코모션은 기존 패키지 337개를 같은 경로에서 교체하고, 누락 source 13개를 `Recovered`에 생성하는 계약을 만들었다. 기존 패키지를 제자리 교체하므로 수정 전 Content 사본이 중복으로 남지 않으며 참조 경로는 유지된다.
- 원작 DualAxeSword 스킬 `AnimComposite` 397개도 조사했다. 카잔 또는 현재 Imperial 우측 무기 스켈레톤에 대응 가능한 360개는 별도 playback AnimSequence 생성 대상으로 준비했다. `Missile_Idle` 또는 아직 추출하지 않은 Design 전용 무기 애니메이션을 쓰는 오브젝트 Composite 37개는 캐릭터 스켈레톤에 잘못 배정하지 않고 metadata-only로 남겼다.

## 원본 근거와 전수 비교 결과

- 원본 Art metadata: `Saved/Extracted/DualAxeSword_20260916/MetadataArt`
- 외부 카잔 source metadata: `Saved/Extracted/DualAxeSword_20260916/MetadataExternal`
- 스킬 metadata: `Saved/Extracted/DualAxeSword_20260916/MetadataSkill`
- ActorX 원본 pose: 기존 PSA 448개와 표적 재추출 9개를 합친 457개
- UE 읽기 전용 inventory: `Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json`
- 원본 비교 보고서: `Saved/ImportReports/Khazan_DAS_OriginalMetadataAudit_20260916.json`
- source CSV: `Saved/ImportReports/Khazan_DAS_SourceTimingComparison_20260916.csv`
- Composite CSV: `Saved/ImportReports/Khazan_DAS_CompositeTimingComparison_20260916.csv`

현재 source AnimSequence 444개는 모두 공통 24 fps/250 samples/10.375초 형태로 잘못 들어가 있었고, 원본의 sample count·길이·sample rate와 모두 달랐다. Root Motion flag 불일치 269개, Force Root Lock 불일치 221개, RateScale 불일치 8개도 확인했다. RateScale 8개는 모두 이번에 보호한 locomotion source다.

원본 Composite 397개 중 253개가 활성 Dilation mapping을 가진다. 지원 가능한 360개 가운데 250개가 활성 Dilation을 사용한다. 구간 자르기, 반복, segment play rate 또는 Dilation 때문에 source와 별도 재생 시간축이 필요한 Composite는 전체 268개다. 따라서 단일 `RateScale`이나 ASC tick으로 원작 속도를 재현하지 않고 Composite별 playback AnimSequence에 원작 시간 매핑을 한 번만 bake한다.

## 임포트 계약

- source timing은 cooked `NumFrames`와 `SequenceLength`를 사용하며 sample rate는 `(NumFrames - 1) / SequenceLength`다. serialized `RateScale`은 별도 속성으로 보존한다.
- Composite는 segment trim, loop count, `AnimPlayRate`, 활성 `DilationAnimPositions(T_Dilation -> T_Original)`을 모든 유지 bone에 적용한다. 생성 후 Sequence/Montage/Ability task의 추가 재생 배율은 1.0을 전제로 한다.
- 현재 `SK_Khazan`은 원본 카잔 PSA의 1,528-bone layout 가운데 138개 track을 표현할 수 있다. 나머지는 현재 프로젝트 스켈레톤에 없는 외형/의상 계열 bone이므로 스켈레톤을 확장해 locomotion까지 흔들지 않고, 현재 스켈레톤과 이름이 일치하는 138개를 복원한다.
- 원본 캐릭터 최상위 motion bone `Root` 위에는 현재 스켈레톤의 `C_P_Kazan`이 삽입돼 있다. `Root` 움직임을 그대로 쓰면 UE가 정지한 bone index 0에서 Root Motion을 추출한다. 임포터는 `Root_ref * C_P_Kazan_new = Root_source(t) * C_P_Kazan_ref`를 만족하도록 움직임을 `C_P_Kazan`에 옮기고 `Root`를 reference pose에 둔다. 모든 frame에서 component pose 보존 오차를 검사한다.
- 캐릭터 Composite playback 351개는 사용자 방침에 따라 Root Motion을 활성화한다. 원본 우측 Imperial 보조 무기 스켈레톤용 source 4개와 Composite 9개는 `/Game/_Art/Kazan/Item/Imperial/DualAxeSword_Imperial_R_Skeleton`을 사용하고 캐릭터 Root Motion 정책을 적용하지 않는다.
- 원작 Composite notify 11,783개는 원작 클래스 실행 코드를 현재 프로젝트에 임의 생성하지 않고 `Saved/Extracted/DualAxeSword_20260916/PlaybackEvents.json`에 원본/변환 시간을 보존했다.

준비된 최종 write manifest는 `Saved/Extracted/DualAxeSword_20260916/AnimationImportManifest.json`이다. 총 710개로 source 복원 350개와 Composite playback 360개이며, 보호 locomotion package와 destination 교집합은 0개다. pose `.npy` 710개의 합계는 326,384,560 bytes다.

## 현재 로코모션 검사 결과와 보호 경계

현재 `ABP_Player` dependency closure가 직접 쓰는 DAS AnimSequence는 다음 9개다.

- `InGame/DAS/Locomotion/Idle/CA_P_Kazan_DualAxeSword_Off_Stand`
- `InGame/DAS/Locomotion/Walk/DAS_Khazan_Walk_Loop`
- `InGame/DAS/Locomotion/Walk/DAS_Khazan_Walk_Stop_LF`
- `InGame/DAS/Locomotion/Walk/DAS_Khazan_Walk_Stop_RF`
- `InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Loop`
- `InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Stop_LF`
- `InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Stop_RF`
- `InGame/DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Loop`
- `InGame/DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Stop`

9개 모두 24 fps key grid와 RateScale 1.25를 사용해 유효 재생 cadence는 30 fps다. 따라서 현재 보이는 속도만으로 전부 느리다고 판정할 수 없다. 다만 원본 cooked source와 비교하면 key 수/유효 길이가 다르고 Stop의 Root Motion·Force Root Lock 설정도 현행 root-locked CMC 정책 때문에 원본과 다르다. 정확한 차이는 원본 비교 보고서의 `current_locomotion_audit`에 기록했다. 이번 작업에서는 이 9개와 source `/Locomotion/`, 전용 runtime library를 합친 AnimSequence 280개를 보호하며 직접 수정하지 않는다.

## 2026-09-16 현재 중단 지점

- metadata 추출, 전수 비교, pose/Composite bake 데이터 생성, import/backup/batch/fresh-audit 스크립트 작성과 Python syntax 검사는 완료했다.
- UE package는 아직 하나도 수정하거나 생성하지 않았다. 일반 Unreal Editor PID 13372가 열려 있어 동일 `.uasset`을 commandlet가 저장하면 라이브 에디터의 메모리 사본이 나중에 다시 덮어쓸 수 있기 때문이다.
- Computer Use에는 현재 Windows 앱 surface가 노출되지 않아 에디터의 Save All/정상 종료를 자동 실행할 수 없었다.

에디터를 저장 후 종료하면 다음 순서로 재개한다.

1. 일반 `UnrealEditor.exe`가 없는지 확인한다.
2. 읽기 전용 inventory → metadata analyzer → pose preparation을 다시 실행해 종료 직전 저장분을 반영한다.
3. `backup_das_animation_timing.py`로 기존 변경 대상 337개를 `Saved/ArtBackups/DAS_Animation_PreTimingFix_<timestamp>`에 hash 검증 복사하고, 보호 locomotion 280개의 pre-hash를 고정한다. Git에서 이미 수정 상태인 `FastAtk04_M1`도 이 백업에 포함한다.
4. 첫 10개 batch로 일반 카잔 source와 스켈레톤을 바로잡는 Imperial weapon source 4개를 함께 검증한다.
5. 첫 batch가 timeline/property/topology/RAW+COMPRESSED pose 검사를 통과하면 나머지 700개를 checkpoint batch로 실행한다.
6. 별도 fresh commandlet에서 710개 전부를 다시 읽고 첫/중간/마지막 RAW+COMPRESSED pose, timing/property/metadata, 기존 비본 데이터 보존, playback inventory, 보호 locomotion hash, 현재 9개 ABP dependency를 검사한다.

## 2026-09-16 읽기 전용 import preflight 통과

- `Scripts/Animation/preflight_das_animation_import.py`를 UE 5.8 commandlet에서 실행해 manifest 710개 전부의 NPY SHA-256·shape·유한값, target skeleton bone, 삽입 root와 source motion bone의 직접 부모/자식 관계, frame grid와 원본 duration, destination 중복 및 보호 locomotion 교집합을 검사했다.
- 기존 교체 337개, 현재 없는 생성 대상 373개, source timeline 350개, Composite playback 360개, active Dilation bake 250개, Root Motion 활성 대상 591개가 manifest와 일치했다. 기존 생성 playback은 0개였다.
- `C_P_Kazan → Root` 및 `C_I_DualAxeSword_ImperialGuard001_R → Weapon_R` topology 이관을 실제 UE `FTransform` 연산으로 전수 계산했다. component pose 보존 최대 오차는 위치 `1.02280922446851e-16 cm`, quaternion 성분 `3.33066907387547e-16`, scale `1.4210854715202e-14`다.
- 첫 실행은 UE 5.8 Python `Transform` 생성자가 quaternion 대신 Rotator를 요구하는 API 차이를 검출했다. importer는 Euler 왕복 없이 기본 Transform의 native `rotation` 필드에 quaternion을 직접 기록하도록 수정했다. duration 비교는 cooked float 표기의 7번째 소수점 차이를 허용하되 rational frame grid 자체를 기준으로 검사한다.
- 최종 report는 `Saved/ImportReports/Khazan_DAS_AnimationImportPreflight_20260916.json`, commandlet exit는 0이다. 이 검사는 asset을 생성·dirty·save하지 않았고, 현재 Content 변경은 사용자가 이미 수정한 `FastAtk04_M1` 한 건 그대로다.
- 실제 package write 대기는 계속 유효하다. 일반 Unreal Editor가 열린 상태이므로 Save All 후 완전 종료된 다음 종료 직전 disk 상태를 다시 inventory/analyze/prepare하고 백업부터 시작한다.

## 2026-09-16 사용자 범위 정정 및 최종 임포트 완료

앞 절의 “locomotion 280개 전체 보호”와 710개 manifest는 이후 사용자 정정 전 기록이다. 최신 경계는 **현재 `ABP_Player` dependency closure가 실제로 참조하는 9개만 보호**하고, 나머지 미사용 locomotion 271개는 검사 결과에 따라 복원하는 것이다.

- 전체 DAS locomotion AnimSequence 280개를 다시 조사했다. 현재 참조 9개, 미사용 271개이며 load failure는 0개다.
- 미사용 271개는 원본 이름의 source locomotion 107개, 미사용 InGame 파생본 57개, 기존 `RT_DAS_*` runtime 파생본 107개다.
- source locomotion 107개는 원본 AnimSequence 457개 복원 묶음에 포함했고, InGame 57개와 runtime 107개는 `UnusedLocomotionReplacement` 164개로 별도 처리했다.
- InGame/Runtime 파생본은 기존 package와 이름을 유지했다. 기존 crop·loop 역할과 root-lock 정책을 유지하면서 원본 ActorX pose와 원본 source rate로 다시 작성했고, Sync Marker는 기존 프레임 위치를 새 시간축으로 변환했다.

현재 참조 9개도 수정 필요 여부를 실제 데이터로 검사했다.

- 9개 모두 저장 grid는 24 fps이고 `RateScale=1.25`여서 유효 cadence는 30 fps다. 따라서 재생 속도 문제만 보면 이미 보상되어 있다.
- 그러나 9개 모두 대응 원본과 sample 수 또는 유효 길이가 다르며 `current_locomotion_audit.needs_future_exact_source_rebuild_review=true`다. 원작과 정확히 같은 timeline으로 만들려면 별도의 marker-aware migration이 필요하다.
- 실제 AnimNotify event는 9개 모두 0개다. Idle을 제외한 8개에는 Sync Marker가 합계 37개 있고, 이것이 현재 작업본의 발 위상/Stop 계약을 보존해야 하는 핵심 비본 데이터다.
- 현재 9개는 이번 manifest에서 제외했고 작업 전/후 SHA-256 9개가 모두 일치했다.

최종 manifest와 적용 결과는 다음과 같다.

| 구분 | 수량 | 결과 |
| --- | ---: | --- |
| 원본 source timeline | 457 | 기존 444개 같은 package 교체, 누락 13개 원본 이름으로 생성 |
| 미사용 파생 locomotion | 164 | InGame 57개 + Runtime 107개 같은 package 교체 |
| 원작 Composite playback | 360 | 원작 `AC_...` basename 그대로 생성 |
| 합계 | 981 | 기존 교체 608개 + 신규 생성 373개 |

- 원작 segment trim/rate/loop 및 Dilation을 bake한 Composite는 360개 중 250개다. runtime Sequence/Montage/Ability 중복 배속을 요구하지 않는 `1.0x` 재생 계약이다.
- 캐릭터 playback은 Root track도 같은 시간 mapping으로 재표본화하고 `C_P_Kazan` root로 이관해 사용자 방침의 Root Motion을 유지한다.
- `Missile_Idle` 또는 추출되지 않은 Design 전용 무기 animation을 쓰는 Object Composite 37개는 SK_Khazan에 잘못 생성하지 않았고 원본 metadata/event만 보존했다.
- 기존 에셋 608개는 `Saved/ArtBackups/DAS_Animation_PreTimingFix_20260916_182555`에 SHA-256 검증 백업했다. 보호 9개의 pre-hash도 같은 manifest에 고정했다.
- UE 5.8 읽기 전용 preflight는 981/981개를 통과했다. 실제 import는 50개 checkpoint batch로 981/981개 모두 통과했다.
- 별도 새 Unreal process의 final audit도 981/981개, backup file 608개, 보호 locomotion 9개, playback inventory를 모두 검증해 `passed`다. 실패는 0개다.
- 최종 최대 오차는 duration `3.0154418961814144e-07 s`, RAW/COMPRESSED pose 위치 `9.918212890625e-05 cm`, quaternion 성분 `0.0006949901580810547`, scale `9.047985076904297e-05`다. topology component-pose 이관 최대 오차는 위치 `1.0228092244685127e-16 cm`, quaternion 성분 `3.3306690738754696e-16`, scale `1.4210854715202004e-14`다.

최종 기계 판독 결과는 `Saved/ImportReports/Khazan_DAS_AnimationImportAudit_20260916.json`과 `Saved/ImportReports/Khazan_DAS_AnimationFinalAudit_20260916.json`이다. 이번 작업은 Content import와 검증까지 완료했으며 게임 C++/Blueprint/Montage 연결 및 PIE 액션 품질 평가는 별도 후속 단계다.

## 2026-09-17 Root Motion 이동량 결함 재현·V4 재임포트

### 기존 품질 판정 정정

- 2026-09-16의 `passed` 판정은 package 저장, 시간축, 전 bone pose, 압축 결과와 topology component pose를 검사했지만 `UCharacterMovementComponent`가 실제 월드에 적용한 Root Motion 이동량은 검사하지 않았다. 따라서 당시 판정을 “애니메이션 이동 품질까지 통과”로 해석한 것은 잘못이었다.
- Unreal PIE에서 실제 Character를 움직여 재현한 결과, 기존 임포트에는 서로 독립적인 두 결함이 있었다. 이 절의 V4 결과가 이동량에 대한 최신 정본이다.

### 확인한 두 원인

1. Composite bake가 각 segment의 절대 Root pose를 그대로 이어 붙여 segment 교체·loop 지점에서 Root가 원점으로 되돌아갔다. `AC_Kazan_DualAxeSword_Flow_Flow_StrongAtk03_01`은 원본 첫 구간 끝 `146.5287`에서 다음 구간의 `0`으로 바뀌어 프로젝트 월드에서 약 `131.88 cm` 역방향 이동을 만들었다. `OverFury_Chain_Start`에도 같은 유형의 reset이 있었다.
2. `SK_Khazan`의 삽입 최상위 bone `C_P_Kazan` reference scale은 `100`이고 `AKhazanPlayer` Mesh scale은 `0.009`다. source `Root`를 `C_P_Kazan`으로 이관한 기존 topology adapter는 component pose만 보존했고 CharacterMovement Root Motion 추출 단위는 검사하지 않았다. 그 결과 PIE 월드 이동이 source 의도보다 약 100배 큰 상태였다.

### V4 변환 계약

- Composite Root는 UE `FTransform` 순서로 각 segment의 trim, reverse, loop와 Dilation 시간축을 평가하고 이전 segment의 누적 delta 위에 이어 붙인다. 독립 재생 시작점은 reference origin으로 rebase한다.
- Root Motion이 활성화된 플레이어 시퀀스는 이관된 `C_P_Kazan` translation에만 reference origin 기준 `0.01`을 곱한다. 이는 삽입 root scale `100`을 상쇄하는 애셋 단위 정규화다. Root rotation·scale과 모든 비Root bone track은 바꾸지 않는다.
- 캐릭터 Mesh scale `0.009`와 런타임 `AnimRootMotionTranslationScale=1.0`은 유지한다. 최종 CharacterMovement 이동은 source Root 변위의 `100 × 0.009 = 0.9`배가 된다. ASC나 Ability가 애니메이션별 보정 배율을 소유하지 않는다.
- 정규화 대상은 630개다. source 270개, 미사용 파생 locomotion 9개, 캐릭터 Composite 351개이며 모두 `bEnableRootMotion=true`인 플레이어 스켈레톤 행이다. 현재 `ABP_Player`가 참조하는 보호 locomotion 9개는 manifest에서 제외했고 최종 SHA-256이 작업 전과 같다.
- Composite Root 누적 bake는 351개이며 실제 불연속을 교정한 interval은 3개다. 최대 interval contract 오차는 translation `1.8115356374411762e-14`, quaternion dot distance `0`이다.

### 이동량 전수 검사와 콤보 표적 값

`Saved/ImportReports/Khazan_DAS_PreparedMovementAudit_20260917.json`은 플레이어 스켈레톤 968개 행과 Root Motion 630개를 검사했고 failure 0이다. 아래 값은 source Root와 프로젝트의 `0.9` 월드 계수로 계산한 값이며 임의로 줄인 튜닝값이 아니다.

| 시퀀스 | 최대 원점 거리 | 종료 변위 |
| --- | ---: | ---: |
| `FastAtk01_M1` | `129.10 cm` | `118.39 cm` |
| 표준 2타 `FastAtk02_M1` | `132.03 cm` | `109.86 cm` |
| 별도 variant `FastAtk02_Loop` | `149.23 cm` | `126.63 cm` |
| `FastAtk03_M1` | `130.87 cm` | `128.51 cm` |
| `FastAtk04_M1` | `221.61 cm` | `198.00 cm` |
| 해금 5타 `Com_WeakAtk05` | `206.93 cm` | `187.79 cm` |

- 전수 검사에서 가장 큰 이동은 `VoidCleave_Flash_Final` 계열의 약 `15.30 m`다. V4 scale 오류가 아니라 source Root 자체가 약 `17.00 m` 이동하는 flash 기술이므로 임의 clamp하지 않았다. 실제 스킬 타깃·Motion Warping 계약과의 적합성은 해당 Ability를 연결한 뒤 별도로 판단한다.

### 적용·검증 결과

- 준비 데이터 V3 백업: `Saved/ArtBackups/DAS_PreRootScaleFix_20260917_1031`.
- 원본 package 백업: `Saved/ArtBackups/DAS_Animation_PreTimingFix_20260916_182555`.
- V4 manifest SHA-256: `77A177D8ADCBCA85ECDA72C7A26663EE801574553D4AC73C54C6787AE9E46206`.
- 읽기 전용 preflight: `Saved/ImportReports/Khazan_DAS_RootMotionScalePreflight_20260917.json`, 981/981, failure 0.
- 메인 Content 재임포트: `Saved/ImportReports/Khazan_DAS_RootMotionScaleImport_20260917.json`, 981/981, 정규화 630개, 이미 현재 버전이라 재작성하지 않은 351개, failure 0.
- 별도 새 UE 프로세스 final audit: `Saved/ImportReports/Khazan_DAS_RootMotionScaleFinalAudit_20260917.json`, 981/981, backup 608개, 보호 locomotion 9개, failure 0. 최대 duration 오차 `3.0154418961814144e-07 s`, pose 위치 오차 `9.918212890625e-05 cm`다.
- 격리 복사 프로젝트의 실제 CharacterMovement PIE: `Saved/ImportReports/Khazan_DAS_RootMotionPIEProbe_20260917.json`. Mesh scale `0.009`, 런타임 Root Motion 배율 `1.0`에서 `FastAtk01_M1` 종료 변위는 기대 `118.39229 cm` 대비 `118.39194 cm`로 오차 `0.00035 cm`였다. `Flow_StrongAtk03_01`은 segment 경계 직후와 종료가 모두 기대값 `135.0 cm`, 오차 `0 cm`로 원점 복귀가 사라졌다.

PIE 검사는 실제 UE CharacterMovement Root Motion 경로를 사용한 진단 proxy이며 아직 `UKhazanWeakAttackAbility`의 Montage/콤보 실행을 통과한 검사는 아니다. 메인 Content의 전수 수치·package 검증과 대표 런타임 이동 검증은 완료됐고, 다음 품질 단계는 실제 Ability/Montage 연결 후 카메라가 있는 플레이 화면에서 1–5타 연결, 회전, 충돌, 타격 정지와 원작 화면을 함께 평가하는 것이다.

## 2026-09-17 Mesh Component scale 전제 제거 정정

앞 절에서 `AKhazanPlayer`의 임시 Mesh scale `0.009`를 사용해 월드 이동량을 표로 환산하고 이를 V4 변환 계약과 함께 설명한 것은 경계를 잘못 잡은 기록이다. 그 표와 기존 `Khazan_DAS_PreparedMovementAudit_20260917.json`, 단일 scale PIE 보고서는 **당시 런타임 조립 상태에서 관측한 값**으로만 남긴다. 애니메이션 에셋의 기준값 또는 재가공 입력값으로는 더 이상 사용하지 않는다.

정정된 계약은 다음과 같다.

- Character Mesh Component scale은 애니메이션 preparation, import, preflight, final audit의 입력이 아니다. 현재 코드의 `0.009`는 이번 정정에서 변경하지 않았으며 언제든 별도 캐릭터 조립 작업으로 바뀔 수 있다.
- 현행 player topology adapter의 translation 보정 `0.01`은 `0.009`에서 계산된 값이 아니다. UE에서 직접 읽은 `SK_Khazan` Skeleton reference pose의 최상위 `C_P_Kazan` uniform scale이 `100`이므로 `1 / 100`으로 정해진 값이다.
- UE preflight와 final audit는 manifest의 `root_motion_translation_scale`이 라이브 Skeleton에서 읽은 삽입 root scale의 정확한 역수인지 검사한다. Skeleton 계약이 달라지면 검사에 실패하며 preparation과 import를 다시 해야 한다.
- 런타임 월드 변위는 현재 component transform을 통해 결정된다. 검증식은 `월드 변위 = source-root 변위 × 삽입 root reference scale × 현재 Mesh Component scale`이며, component scale은 이 마지막 런타임 단계에서만 변수로 둔다.
- Mesh Component scale만 변경되는 경우 에셋 재가공이나 재임포트 대상이 아니다. 보이는 캐릭터 크기와 Root Motion 월드 이동이 같은 비율로 변하는 것이 UE transform 계약이다.

검증 도구도 이 계약에 맞춰 수정했다.

- `prepare_das_animation_timing.py`는 component scale 상수를 갖지 않으며 현재 Skeleton 계약 `100`의 역수로 보정값을 표현한다.
- `preflight_das_animation_import.py`와 `audit_das_animation_timing_import.py`는 실제 `SK_Khazan` reference pose에서 `C_P_Kazan` scale을 읽고 manifest의 역수 관계를 검사한다.
- `Khazan_DAS_AssetSpaceMovementAudit_20260917.json`은 968개 player 준비 데이터와 Root Motion 630개를 component scale 없이 다시 검사했고 failure 0으로 통과했다.
- 격리 CharacterMovement PIE는 임의의 component scale `0.005`, `0.01`, `0.02` 세 값에서 실행했다. `FastAtk01_M1` 종료 변위는 각각 `65.77388`, `131.54701`, `263.09402 cm`였고 scale을 제거해 정규화하면 모두 source 값 약 `131.547`로 수렴했다. Composite 표적은 각각 `75`, `150`, `300 cm`였고 정규화 결과는 모두 `150`이다. 최대 정규화 오차는 `0.00077` source unit 미만이다.
- 새 런타임 보고서 `Khazan_DAS_RootMotionScaleIndependencePIE_20260917.json`은 삽입 root scale을 상수로 믿지 않고 라이브 Skeleton에서 읽었으며 `temporary_player_mesh_scale_used_as_asset_input=false`를 기록한다.

따라서 이미 임포트한 V4 630개 Root Motion 에셋의 `0.01`은 현재 Skeleton 계약에 맞아 유효하다. 이번 정정에서는 Content를 다시 저장하거나 재임포트하지 않았다. 같은 트랙을 다시 쓰는 것은 결과를 바꾸지 않으며, 열린 메인 Editor의 사용자 상태에도 손대지 않았다.

## 2026-09-17 Composite 재생본의 정확한 60 Hz 교정

### 기존 시간축 계약의 결함과 원인

- 사용자 확인대로 이전 Composite bake의 `SamplingFrameRate`는 고정 `60/1`이 아니었다. `intervals = round(duration × target_rate)`를 정한 뒤 `fps = intervals / duration`을 다시 분수화했기 때문에, 구간별 Dilation을 bake한 재생본마다 `5110687/85161 = 60.0120595...`, `5341547/89107 = 59.9453129...` 같은 서로 다른 sample rate가 기록됐다.
- Dilation에 따른 가감속과 출력 sample rate는 서로 다른 계약이다. 가감속은 `T_Dilation → T_Original` pose sampling map 안에 있어야 하며, AnimSequence data model의 sample rate는 고정 격자여야 한다. 이전 생성식과 “manifest 값과 일치하는가”만 검사한 audit는 잘못 만든 manifest 자체를 정답으로 받아들였으므로 이 결함을 잡지 못했다.
- 수정 전 `PlaybackDerivation=CompositePlayback` 360개 가운데 exact `60/1`은 1개뿐이었다. 359개는 다른 분수였고, 그중 249개는 약 `55–65 fps` 범위의 비정수 60 근사값이었다. source timeline과 locomotion은 별도 원본 cadence 계약이므로 이번 60 Hz 일괄 대상에 포함하지 않았다.

### V5 변환 계약

- 모든 Composite playback은 `SamplingFrameRate=60/1` 및 모든 platform target frame rate `60/1`을 사용한다.
- 새 interval 수는 `N = round(이전 재생 길이 × 60)`이고 새 길이는 정확히 `N / 60 s`다. 길이 양자화 오차의 절대 최대값은 `0.00833328862984975 s`로 60 Hz 반 프레임보다 작다.
- 새 frame `i`가 읽는 이전 시간은 `old_duration × i / N`이다. 따라서 frame 0과 마지막 frame의 자세 및 Root Motion endpoint를 정확히 보존하고, 기존에 bake된 구간별 속도 변화는 정규화된 전체 시간축 안에서 유지한다.
- `RateScale`, Root Motion, Force Root Lock, additive/retarget/compression property와 package/name은 보존한다. 현재 Character Mesh Component scale은 sampling 입력이 아니며 `temporary_mesh_component_scale_used=false`다.
- `prepare_das_animation_timing.py`도 같은 계약으로 수정했다. 앞으로는 Composite의 authored/Dilation 길이를 가장 가까운 60 Hz 길이로 양자화하고, 원본 event time도 같은 timeline scale로 변환한다. `fps = intervals / duration` 방식은 사용하지 않는다.

### WeakAttack 1–5 결과

| 재생본 | 수정 전 FPS | 수정 후 frame/key | 수정 후 길이 | 길이 변화 |
| --- | ---: | ---: | ---: | ---: |
| `DAS_Khazan_WeakAtk01` | `60.0120595108` | `206 / 207` | `3.4333333969 s` | `+0.0006899198 s` |
| `DAS_Khazan_WeakAtk02` | `60.0951787441` | `200 / 201` | `3.3333332539 s` | `+0.0052793821 s` |
| `DAS_Khazan_WeakAtk03` | `60.0603312072` | `298 / 299` | `4.9666666985 s` | `+0.0049891154 s` |
| `DAS_Khazan_WeakAtk04` | `59.9453129384` | `269 / 270` | `4.4833331108 s` | `-0.0040900866 s` |
| `DAS_Khazan_WeakAtk05` | `60.0000461538` | `156 / 157` | `2.5999999046 s` | `+0.0000020027 s` |

- 5개 모두 Root Motion과 Force Root Lock이 계속 활성화돼 있다.
- 현재 `AM_DAS_WeakAtkCombo`는 사용자 저장 상태대로 `Attack01` section과 1번 segment 하나를 유지한다. 1번 교체 후 segment `AnimEndTime`, `CachedPlayLength`, Montage 자체 길이를 모두 새 시퀀스 길이 `3.4333333969 s`로 갱신했고 Sequence/Montage rate는 `1.0`이다.

### 적용·복구·독립 검증

- 수정 전 Composite playback 360개와 현재 Montage 1개, 합계 361 package를 `Saved/ArtBackups/DAS_Composite_PreExact60_20260917_184000`에 SHA-256 검증 백업했다. 총 크기는 약 `0.506 GiB`다.
- 라이브 에디터에서 85번째 처리 중 `EditorAssetLibrary.DeleteAsset`의 반복 Force Delete가 TaskGraph recursion assertion을 일으켜 에디터가 종료됐다. 해당 지점은 기존 package와 검증 완료 임시 package가 모두 남아 있어 원본 손실이 없었다. 이후 20개 이하의 독립 `UnrealEditor-Cmd` checkpoint로 전환했고 모든 process가 exit `0`으로 끝났다.
- import report `Saved/ImportReports/Khazan_DAS_CompositeExact60_Import_20260917.json`은 360/360 `passed`다. 이전 재생본과 새 재생본의 5개 checkpoint RAW/COMPRESSED pose 비교 최대 오차는 위치 `3.0517578125e-05 cm`, quaternion 성분 `1.15297395636427e-05`, scale `1.18017196655273e-05`다.
- 별도 새 Unreal process의 `Saved/ImportReports/Khazan_DAS_CompositeExact60_FinalAudit_20260917.json`은 360/360 exact `60/1`, backup 361개, 프레임/키/길이/metadata/platform rate/Root Motion property, Montage timing, 임시 asset 0개를 확인해 `passed`다. 캐릭터 Root Motion 재생본은 351개이고 보조 무기 역할 9개는 기존 비활성 정책을 보존했다.
- 최종 감사는 에셋 시간축과 포즈 보존을 검증한 것이다. 실제 1–5타 Montage 연결 위치와 플레이 화면의 액션 품질 검수는 콤보 Montage 구현 단계에서 계속 수행한다.
<a id="2026-09-18-current-stop-root-motion-targeted-migration"></a>
## 2026-09-18 — 현재 Run/Sprint Stop 3종의 표적 Root Motion 이관

### 대상과 기존 보호 정책

이번 대상은 현재 `ABP_Player`가 직접 참조하는 다음 세 asset으로 한정한다.

- `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Stop_LF`
- `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Stop_RF`
- `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Stop`

이 세 asset은 2026-09-16 복원에서 current locomotion dependency 보호 목록에 들어가 V4 root-motion correction 대상에서 제외됐다. 일반 보호를 제거해 9종 전체를 다시 import하지 않는다. 세 package만 명시한 manifest/opt-in을 새로 두고 preflight가 그 정확한 집합만 허용하게 한다.

2026-09-18 현재 기존 `Saved/Extracted/DualAxeSword_20260916`와 2026-09-16 감사·인벤토리 JSON은 workspace에 남아 있지 않으므로 예전 script를 바로 실행할 수 없다. 원본 폴더에는 Run Stop LF/RF와 Sprint Stop PSA가 남아 있다. 세 PSA만 대상으로 source hash, bone layout, frame count/rate, Root track을 다시 읽는 read-only 단계부터 재생성해야 한다. 기존 ActorX→Unreal 변환과 같이 Y 부호를 뒤집은 좌표에서 직접 읽은 원본 `Root` 시작→끝 translation은 LF `(0, 50, 0)`, RF `(0, 50, 0)`, Sprint `(0, 약 148.995651, 0)` source units다. 이 endpoint는 trim 전 원시 값이므로 그대로 게임 이동 거리로 쓰지 않는다.

### 변환 계약

- root motion translation의 `0.01`은 삽입된 top bone `C_P_Kazan` reference scale 100의 역수다.
- 캐릭터 Mesh Component의 임시 `0.009`는 변환식에 포함하지 않는다.
- 임시 component scale은 런타임 local-to-world 결과에는 실제로 영향을 주므로 canonical asset이 현재 PIE에서 작게 이동할 수 있다. 이 현상을 asset translation에 `1 / 0.009`를 bake하는 방식으로 보상하지 않고, 캐릭터 조립 scale 이관과 별도로 검증한다.
- source Root transform을 `C_P_Kazan`에 옮기고 child Root를 reference pose에 고정한다.
- timeline, 24 fps key grid, 현 trim, marker, import/compression 설정과 asset path/name을 보존한다.
- Root Motion/Force Root Lock/Ref Pose/normalized scale 설정은 현재 값을 유지하며, 재생률 변경은 이번 이관 범위가 아니다.

### 검증 산출물

fresh process audit report에는 source/destination hash, bone 0 이름과 reference scale, 적용 배율, 시작·끝·누적 root delta, frame count/rate, marker 수와 이름, Root Motion property를 각각 남긴다. PIE에서 측정한 capsule 월드 이동량은 asset-space delta와 별도 필드에 기록한다. 이번 절은 이관 계약이며 실제 asset 재임포트 완료 기록은 아니다.
