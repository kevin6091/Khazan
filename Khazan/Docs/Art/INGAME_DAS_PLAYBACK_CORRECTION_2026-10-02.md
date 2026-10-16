# 2026-10-02 InGame DAS 재생 속도 보정 결과

추가 이동한 애니메이션을 포함해 `/Game/_Art/Player/Animation/InGame`의 기존 AnimSequence 140개를 분석했다. 실제 수정은 시퀀스 40개와 강공격 Montage 2개다. 반복 순서를 한 원본의 RateScale로 표현할 수 없는 동작은 InGame에 완성 재생본 2개를 복사했다. 최종 시퀀스 142개, Montage 5개이며 새 프로세스의 저장 파일 검사가 passed다.

## 1. 범위와 보존 계약

- 22개: 기본 분기의 원작 segment 배속과 Dilation을 기존 본 포즈의 시간축에 bake. 출력 60/1 fps, RateScale 1.0.
- 18개: 기존 24 fps 키를 보존하고 원작 30 fps cadence에 맞춰 RateScale 1.25 적용.
- 100개: 기존 패키지 SHA-256 동일. 이미 보정된 9개 현행 locomotion과 사용자가 crop한 WeakAttack 5개 포함.
- Montage 2개: StrongAttackCombo/StrongChargeAttack의 segment·section·notify·branching point 시간만 포즈 시점에 맞춰 이관. Blend/Notify GUID·이름·payload·트랙·Skeleton 등 비시간 속성 보존.
- InGame 밖 애니메이션 870개는 수정 전후 크기/mtime 동일. Source/Skeleton/mesh에 이 작업의 편집 없음. Player/BP 설정을 저장하지 않음.
- 현재 BP_Player Mesh relative scale 재확인: 세 축 모두 0.009999999776482582. SK_Player C_P_Kazan reference scale 100과 기존 root track의 공간 계약 유지. component 0.01은 시간 계산 입력이 아니며 root translation에 다시 곱하지 않음.
- 기본/일반 분기를 기준으로 선택했다. 강화·Fast 등 다른 소비 문맥의 별도 배속을 기본 시퀀스에 중첩하지 않는다. 새 재생본의 Ability/몽타주 연결은 이번 에셋 보정에 포함하지 않았다.

## 2. 근거와 시간 계산

기존 [DAS 복원 정본](DAS_ANIMATION_RESTORATION_2026-09-16.md)의 V4 공간 계약과 V5 exact 60 Hz 작업을 재사용했다. 예전 추출 폴더가 현재 없어 정확한 OriginalPackage 및 남아 있던 report로 필요한 원본 metadata를 재추출했다. 원본 package basename과 export Object Name이 다른 StrongAttack/Guard 이동은 full package 참조로 대응시켰다.

원작 직접 확인 필드는 AnimSequence의 `Properties.NumFrames`, `SequenceLength`, AnimComposite의 `Properties.AnimationTrack.AnimSegments[i].AnimReference`, `StartPos`, `AnimStartTime`, `AnimEndTime`, `AnimPlayRate`, `LoopingCount`와 `Properties.DilationCurve`의 `DilationSequenceLength`, `DilationAnimPositions[i].T_Original/T_Dilation`이다. NumFrames/LoopingCount는 개수, 시간 필드는 초, AnimPlayRate는 무차원 배율이다. 원작의 serialized RateScale override는 조회 집합에서 없었다. 1.0은 parser/엔진의 부재 시 기본 계약이며 원작 파일에 1.0이 명시됐다는 뜻이 아니다.

- 원작 cadence 계산값: `(NumFrames - 1) / SequenceLength`. cook float 오차와 직접 저장된 필드를 구분한다.
- segment의 원본 Composite 시각: `p = StartPos + (sourceTime - AnimStartTime) / (sourceRateScale × AnimPlayRate)`.
- 유효한 저장 Dilation table 구간은 `p`를 `T_Original → T_Dilation`으로 변환한다. 표 사이에서는 선형 보간하며 table 부재/identity 경로는 해당 source cadence를 유지한다.
- 단일 source에서 사용되는 구간은 source 포즈 순서로 이어 붙인다. 여러 source를 합치거나 같은 source 구간을 반복/재배치하는 원작 Composite 전체와 이 full-source 어댑터를 구분한다.
- Composite가 소비하지 않는 기존 prefix/tail은 현재 source cadence로 보존한다. 원본 trim 범위를 가져와 현재 사용자 범위를 삭제하지 않는다.
- 기존 60 Hz 계약에 따라 `N = round(authoredDuration × 60)`, 출력 길이 `N/60`. source-time mapping을 출력 길이에 맞춰 같은 비율로 정규화해 처음/끝 포즈를 보존한다. 최대 길이 양자화 차이는 `0.007895853333357294 s`로 60 Hz 반 프레임보다 작다. 이 값은 원작의 직접 재생 길이가 아니라 계산/양자화 결과다.
- gameplay 임시 배율을 새로 선정하지 않았다. RateScale 1.25는 원작 30 / 현행 24로 계산한 값이다. 60 Hz 출력과 비교 허용 오차는 기존 에셋 처리/검사 계약이며 gameplay 튜닝 수치가 아니다.

낙하 공격의 직접 사례: `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/FallAtk/AC_Kazan_DualAxeSword_Com_FallAtk_Start`의 segment 0은 source 0–0.273 s / AnimPlayRate 0.5, segment 1은 source 0.273–0.29 s / AnimPlayRate 0.005다. DilationCurve.TimePerFrame=0.016666668 s, DilationSequenceLength=3.7446527 s이며 DilationAnimPositions 238개, 마지막 pair=(3.945998, 3.7446527)다. End Composite의 0.29–2.7333333 s 구간을 추가 적용한 full-source 계산 길이는 5.7711130230759995 s, 출력은 346 frames / 5.766666666666667 s다. 이를 0.01 배율이나 하나의 균일 RateScale로 치환하지 않았다.

모든 대상의 정확한 원본 파일·field·원시 값·선택 Composite와 범위·미소비 구간·변환 sample은 [PlaybackPlan.json](../../Metadata/InGamePlayback_20261002/PlaybackPlan.json)에 있다. 재추출물의 SHA-256과 원본 시간 필드 488 package를 [OriginalTimingFields.json](../../Metadata/InGamePlayback_20261002/OriginalTimingFields.json)에 보존했다. 필요한 package만 조회하며 전체 JSON을 매번 읽지 않는다. 사용한 FModel provider의 원본을 기준으로 하며 게임 build ID를 새로 확인했다고 주장하지 않는다.

## 3. 실제 retime 22개

원작 열은 NumFrames / SequenceLength 초의 직접 확인값이다. 전후 길이는 현재 source 범위를 보존한 프로젝트 시퀀스 길이이며 원작 Composite 전체의 실행 길이와 구분한다. 모두 output fps=60/1, RateScale=1.0이다. 출력 frames는 모델 NumberOfFrames의 시간 간격 수이며 실제 NumberOfKeys는 frames+1이다.

| InGame 상대 경로 | 원작 frames / 초 | 이전 길이(초) | 저장 길이(초) | 출력 frames |
|---|---:|---:|---:|---:|
| `DAS/FallAttack/CA_P_Kazan_DualAxeSword_Com_FallAtk` | 83 / 2.733333 | 2.733333 | 5.766667 | 346 |
| `DAS/FlowStrongAttack/Player_StrongAttack_Upgrade_01` | 142 / 4.700000 | 4.700000 | 4.633333 | 278 |
| `DAS/FlowStrongAttack/Player_StrongAttack_Upgrade_02` | 135 / 4.466667 | 4.466667 | 4.350000 | 261 |
| `DAS/FlowStrongAttack/Player_StrongAttack_Upgrade_03End` | 22 / 0.700000 | 0.700000 | 0.833333 | 50 |
| `DAS/Guard/Player_Guard_Start` | 16 / 0.500000 | 0.500000 | 0.250000 | 15 |
| `DAS/Guard/Player_Guard_Suc_F` | 11 / 0.333333 | 0.333333 | 0.416667 | 25 |
| `DAS/Guard/Player_Guard_Suc_L` | 11 / 0.333333 | 0.333333 | 0.416667 | 25 |
| `DAS/Guard/Player_Guard_Suc_R` | 11 / 0.333333 | 0.333333 | 0.416667 | 25 |
| `DAS/OverFury/CA_P_Kazan_DASword_B_OverFury_03` | 111 / 3.666667 | 3.666667 | 4.316667 | 259 |
| `DAS/OverFury/CA_P_Kazan_DASword_B_OverFury_05` | 57 / 1.866667 | 1.866667 | 2.216667 | 133 |
| `DAS/OverFury/CA_P_Kazan_DualAxeSword_Yaksha_OverFury_Chain_Start` | 7 / 0.200000 | 0.200000 | 0.333333 | 20 |
| `DAS/OverFury/CA_P_Kazan_DualAxeSword_Yaksha_OverFury_End` | 101 / 3.333333 | 3.333333 | 3.450000 | 207 |
| `DAS/OverFury/CA_P_Kazan_DualAxeSword_Yaksha_OverFury_Start` | 21 / 0.666667 | 0.666667 | 0.450000 | 27 |
| `DAS/SpinningBeast/CA_P_Kazan_DualAxeSword_Yaksha_SpinningBeast01` | 119 / 3.933333 | 3.933333 | 4.016667 | 241 |
| `DAS/SpinningBeast/CA_P_Kazan_DualAxeSword_Yaksha_SpinningBeastFall_End` | 22 / 0.700000 | 0.700000 | 0.833333 | 50 |
| `DAS/SpinningBeast/CA_P_Kazan_DualAxeSword_Yaksha_SpinningBeast_US_End_ToIdle` | 116 / 3.833333 | 3.833333 | 3.833333 | 230 |
| `DAS/SpinningBeast/CA_P_Kazan_DualAxeSword_Yaksha_SpinningBeast_UltimateSlash_End_A` | 73 / 2.400000 | 2.400000 | 1.766667 | 106 |
| `DAS/SpinningBeast/CA_P_Kazan_DualAxeSword_Yaksha_SpinningBeast_UltimateSlash_Fail` | 91 / 3.000000 | 3.000000 | 3.000000 | 180 |
| `DAS/StrongAttack/DAS_Player_StrongAttack01` | 137 / 4.533333 | 4.533333 | 4.550000 | 273 |
| `DAS/StrongAttack/DAS_Player_StrongAttack03` | 158 / 5.233333 | 5.233333 | 5.300000 | 318 |
| `DAS/StrongAttack/DAS_Player_StrongCharge` | 46 / 1.500000 | 1.500000 | 1.383333 | 83 |
| `DAS/StrongAttack/DAS_Player_StrongChargeAttack` | 164 / 5.433333 | 5.433333 | 5.100000 | 306 |

Guard Suc_L과 Suc_R의 원작 소비 Composite 이름은 반대 방향 명칭을 사용한다. 이름만 보고 L/R을 교환하지 않고 AnimReference full package 대응을 사용했다. OverFury의 일반/BurstFury/Fast 등 다른 소비 속도는 SkillStateConsumptions/ScopeMapping에 남겼다. CA_P_Kazan_DASword_B_OverFury_05는 해당 포즈를 사용하는 BurstFury Finish segment를 선택했다.

## 4. RateScale만 보정한 18개

모두 InGame/DAS/Locomotion/Sprint 아래이며 native grid 24 fps를 유지한다. 현재 crop/padding·키·marker·root 옵션을 보존했다. 사용하지 않는 Start/Legacy 파일의 시간 보정이 gameplay에서 Start를 다시 사용하는 변경은 아니다.

| 시퀀스 | 원작 frames / 초 | 유지한 native frames | RateScale |
|---|---:|---:|---:|
| `CA_P_Kazan_DualAxeSword_Sprint_BL_Start` | 28 / 0.900000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_BR_Start` | 28 / 0.900000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_B_Start` | 28 / 0.900000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_F` | 121 / 4.000000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_FL_Start` | 35 / 1.133333 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_FR_Start` | 35 / 1.133333 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_F_Start_TEST` | 30 / 0.966667 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_L_Start` | 14 / 0.433333 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_180` | 13 / 0.400000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_90` | 14 / 0.433333 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_R_180` | 13 / 0.400000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_R_90` | 14 / 0.433333 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_R_Start` | 15 / 0.466667 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_Start` | 35 / 1.133333 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_Start_F_LF` | 16 / 0.500000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_Start_F_RF` | 19 / 0.600000 | 249 | 1.0 → 1.25 |
| `CA_P_Kazan_DualAxeSword_Sprint_Stop_F` | 101 / 3.333333 | 249 | 1.0 → 1.25 |
| `DAS_Player_Sprint_Stop_Legacy` | 101 / 3.333333 | 114 | 1.0 → 1.25 |

원작 full length와 현행 padding이 다른 파일은 padding을 유지했으므로 출력 전체 길이를 원작 Composite 길이와 동일하다고 설명하지 않는다. 실제 선택은 기존 locomotion 소비 에셋과 분리한다. 이 18개는 기존 TimingContract/DASTimingVersion을 보존하고 별도 `InGameCadenceCorrection` metadata에 이번 보정을 기록했다. 현행 판단은 이 태그와 실제 모델 fps/RateScale을 함께 사용한다.

## 5. 반복 재생이 필요한 2개

- 읽은 기존 라이브러리: `/Game/_Art/Player/Animation/Playback/DualAxeSword/Composite/Yaksha/AC_Kazan_DualAxeSword_Yaksha_SpinningBeast_UltimateSlash_Air`
  - 저장 위치: `/Game/_Art/Player/Animation/InGame/DAS/SpinningBeast/AuxiliaryObject/AC_Kazan_DualAxeSword_Yaksha_SpinningBeast_UltimateSlash_Air`
- 읽은 기존 라이브러리: `/Game/_Art/Player/Animation/Playback/DualAxeSword/Composite/Yaksha/AC_Kazan_DualAxeSword_Yaksha_SpinningBeast_UltimateSlash_Loop`
  - 저장 위치: `/Game/_Art/Player/Animation/InGame/DAS/SpinningBeast/AC_Kazan_DualAxeSword_Yaksha_SpinningBeast_UltimateSlash_Loop`

두 파일은 기존 `20260917_DAS_CompositeExact60HzV5` 완성 재생본의 pose·root·시간을 복사했고 RateScale 1.0이다. UltimateSlash Loop는 같은 raw source에서 0–0.2 s 및 0.3–0.6 s를 두 번 소비한다. Air의 같은 weapon source는 첫 등장과 뒤 등장에서 다른 Dilation을 사용한다. 한 raw source의 단일 배율로 이 순서/반복/서로 다른 속도를 표현할 수 없어 기존 완성본을 재사용했다. 원래 raw source와 weapon Skeleton의 scale은 보존했다.

## 6. Montage와 검사

- StrongAttackCombo: 저장 길이 14.449999809265137 s, section 3 / notify 7 / branching marker 7.
- StrongChargeAttack: 저장 길이 6.483333110809326 s, section 2 / notify 3 / branching marker 3.
- 원래 notify가 가리킨 source 포즈 시각을 역 mapping으로 옮겼다. section 경계와 segment 시작/끝도 같은 mapping을 사용했다. EndLink 미연결 상태를 임의로 Montage에 연결하지 않았다.
- live 복사본으로 먼저 증명했다. UE 5.8.2 Python에 노출되지 않은 두 montage 배열은 설치 엔진의 정확한 Win64 ABI/export를 확인한 scoped property serializer로 이관했다. UObject layout/메모리를 직접 patch하거나 class 전체 SET을 하지 않았다. 기존 notify 객체·GUID/payload를 유지했다. 다른 UE 버전에서는 bridge를 재검증해야 한다.
- 새 UnrealEditor-Cmd 프로세스에서 시퀀스 142개와 Montage 5개를 로드했다. retime 22개 및 복사 2개는 5개 시점의 모든 본을 RAW/COMPRESSED와 원본 sample에 비교했다. frame/key 수·fps·길이·본 순서·root 옵션·compression 참조도 확인했다.
- 관측 최대 차이: local position 0.000025272369384765625 cm, quaternion component 0.000008454845296879121, local scale 0.000011801719665527344. 기존 pose 검사 허용 범위 이내다. 모든 frame을 원작 게임 화면과 대조한 결과는 아니다.
- 저장 Montage의 segment·section·notify·branching cache 검사와 비시간 export 속성 검사가 passed다. 엔진 재로드의 segment 정렬에서 약 1 μs 반올림이 있어 기존 1e-5 s 비교 허용 범위로 수치를 비교했다. 문자열 동일성으로 실패한 초기 검사와 최종 통과를 구분한다.
- 임시 InGame probe 2개 제거, 대상 저장 후 dirty content 없음. C++ 빌드나 실제 Ability PIE 동작/원작 runtime attack-speed 배율 일치 검증은 이번 결과가 아니다.

## 7. 재사용 자료와 복구

- 지속 자료: [Metadata/InGamePlayback_20261002](../../Metadata/InGamePlayback_20261002/PlaybackPlan.json)의 PlaybackPlan, OriginalTimingFields, ScopeMapping, SkillStateRates/Consumptions, ApplyReport, FreshProcessAudit, DiskPreservationAudit, MontageNonTimingPropertyAudit, Expected_*.
- helper: `Scripts/Animation/retime_ingame_from_metadata.py`, `audit_ingame_metadata_playback.py`. 기존 `fix_das_composite_playback_60fps.py`에는 선택적 source_times 인자만 추가해 기존 호출 계약을 유지했다. 게임 runtime 구조/관측 멤버/클래스 추가 없음.
- 원래 150 package byte backup: `Saved/ArtBackups/InGame_Playback_PreFix_20261002`. 150/150 SHA-256 재검증. frozen plan hash: `025685c35683ea09e93081a5e232969a1e4e8e9e0a0f7dc45fc30636cd1c0d91`.
- 이후 추가 이동/사용자 수정 대상은 새 snapshot·원본 소비 문맥·backup으로 별도 계획을 만든다. 기존 DASTimingVersion/TimingContract를 읽어 이미 bake한 Dilation을 중복 적용하지 않는다. 이 계획을 이미 수정한 전체에 다시 적용하는 절차로 사용하지 않는다.
- 동시에 진행된 다른 편집에서 Config/DefaultEngine.ini·BP_Player와 DodgeAttack Montage의 baseline hash 차이가 있었다. 이 작업은 해당 파일에 쓰지 않았으며 다른 변경을 복구하지 않았다. 현재 Player mesh 0.01을 재확인했다. 게임 Source/Skeleton/mesh와 범위 밖 animation 870개의 보존을 별도로 검사했다.
- 미완료 에셋 적용 단계 없음. 다른 스킬 분기 강화율 선택, 새 standalone의 gameplay 연결, 실제 PIE 시각 확인은 해당 요청/실행 문맥에서 진행한다.
