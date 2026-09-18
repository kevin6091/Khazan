# DAS 애니메이션 시간축 검사 — 2026-09-08

## 1. 결론과 검사 경계

현재 InGame 애니메이션의 **24 fps는 임포트 결과의 시간축**이다. 검사한 원본 PSA 11개의 시간 정보와 추출기 계산 규칙으로 복원한 **유효 sample 간격은 약 30 fps**다. 따라서 24 fps를 원작의 정확한 속도로 간주한 이전 해석은 근거가 부족했다.

이는 FPS 숫자만 다른 정상적인 리샘플링으로 설명되지 않는다. FBX 6개의 실제 키 시간은 1/24초 격자이고, 원본/현재 InGame 각각 5개 시퀀스의 표적 본 회전 변화는 PSA의 연속 프레임과 일대일로 대응한다. 검사 구간에서 같은 동작 진행을 24 fps 시간축에 배치한 증거가 있다.

- 수행: 기존 metadata 재사용 → 필요한 PSA 11개 직접 읽기 → FBX 6개 binary 시간 정보 읽기 → 현재 Editor의 InGame 11개/ABP Sequence Player 10개 읽기 → 5개 원본과 5개 InGame의 표적 RAW 본 회전 변화 대조.
- 미수행: 모든 DAS 파일 전수조사, 원작 실행 영상의 시간 계측, 원작 ABP/Montage/동적 RateScale 확인, PIE, 시각적 속도/접지 합격 판정.
- 변경: 이 문서/색인/상태/Animation 정본 및 새 감사 JSON만 작성. PSA, FBX, C++, ABP, 시퀀스는 변경하거나 저장하지 않았다.
- 감사 JSON: [Khazan_Locomotion_Timing_Audit_20260908.json](../../Saved/ImportReports/Khazan_Locomotion_Timing_Audit_20260908.json).
- 현재 구현 정본: [LOCOMOTION_CURRENT_IMPLEMENTATION.md](../Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md).

## 2. PSA 값은 어떻게 해석했는가

PSA 위치:

`C:/Users/user/Desktop/카잔/BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword`

기존 [PSA metadata](../../Saved/ImportReports/Khazan_DAS_PSA_SourceMetadata.json)에서 대상만 선택하고 [기존 parser](../../Scripts/Animation/extract_das_psa_metadata.py)의 `parse_psa` 함수로 실제 파일을 다시 읽었다. 전체 448개를 재조사하거나 기존 JSON을 덮어쓰지 않았다.

CUE4Parse의 검사일 master(commit `89ef88f6a3cf9437e599838e68b990e341a329d3`)는 다음 규칙을 사용한다.

```text
R = AnimRate = N / SequenceLength * Max(1, OriginalSequence.RateScale)
N = NumRawFrames = NumFrames
TrackTime = N
```

따라서 `TrackTime`을 초 단위 길이로 읽으면 안 된다. `R` 자체도 끝점 포함 키 개수와 구간 개수를 구분하지 않는 일반적인 정수 sample rate가 아니다.

```text
PSA로부터 복원한 유효 길이 = N / R
끝점 사이 유효 sample rate = (N - 1) / (N / R)
                           = (N - 1) * R / N
```

원본 asset RateScale이 1이면 `N/R`는 SequenceLength에 해당한다. 현재 공개 exporter는 RateScale이 1보다 크면 반영하고 1보다 작으면 1로 취급한다. 실제 사용된 FModel/exporter binary 버전 및 원작의 RateScale을 이번에 독립적으로 확인하지 않았으므로, **원작의 nominal sample rate와 최종 런타임 속도까지 모두 증명한 공식으로 쓰지 않는다.** 아래 값들은 원본 PSA와 공개 exporter 규칙에서 복원한 유효 기준이다.

아래 이름은 `CA_P_Kazan_DualAxeSword_` 이후 부분이다.

| 시퀀스 | PSA 키 수 N | 저장된 AnimRate R | N/R 유효 길이(초) | (N-1)R/N |
| --- | ---: | ---: | ---: | ---: |
| Off_Stand | 265 | 30.113636 | 8.800000 | 약 30 |
| Walk_F | 35 | 30.882353 | 1.133333 | 약 30 |
| Run_F | 121 | 30.25 | 4.000000 | 30 |
| Sprint_F | 121 | 30.25 | 4.000000 | 30 |
| Walk_Stop_F_LF | 42 | 30.731707 | 1.366667 | 약 30 |
| Walk_Stop_F_RF | 42 | 30.731707 | 1.366667 | 약 30 |
| Run_Stop_F_LF | 97 | 30.3125 | 3.200000 | 30 |
| Run_Stop_F_RF | 93 | 30.326088 | 3.066667 | 약 30 |
| Sprint_Stop_F_02 | 116 | 30.260870 | 3.833333 | 약 30 |
| Walk_StandTurn_L_180 | 16 | 32 | 0.500000 | 30 |
| Walk_StandTurn_R_180 | 16 | 32 | 0.500000 | 30 |

**Walk Turn이 32 fps이고 Run이 30.25 fps라고 곧바로 설정하지 않는다.** 예를 들어 Turn의 16개 키는 15개 구간이고, 15 / 0.5 = 30이다.

기존 parser/report의 `duration_seconds=(N-1)/AnimRate`는 PSA 필드에 특정 해석을 적용한 계산값이다. 위 CUE4Parse 규칙에서 복원하는 `N/R`와 다르므로 원작 SequenceLength의 독립 실측값으로 사용하지 않는다. 기존 조사 기록은 삭제하지 않았으며, 시간축 판단에서는 이번 보완을 우선한다.

출처: [CUE4Parse CAnimSequence](https://github.com/FabianFG/CUE4Parse/blob/89ef88f6a3cf9437e599838e68b990e341a329d3/CUE4Parse-Conversion/Writers/ActorX/Structs/Animations/CAnimSequence.cs), [ActorXAnim](https://github.com/FabianFG/CUE4Parse/blob/89ef88f6a3cf9437e599838e68b990e341a329d3/CUE4Parse-Conversion/Writers/ActorX/ActorXAnim.cs).

## 3. FBX와 현재 UE 에셋의 직접 확인

검사한 FBX는 `C:/Users/user/Desktop/카잔/Blender/Animation/Part_08_351_to_400/`의 Run_F, Walk_F, Sprint_F, Sprint_Stop_F_02, Walk_StandTurn_L_180, Off_Stand다.

- 모두 binary FBX 7400.
- TimeMode=11, CustomFrameRate=24.
- AnimationStack LocalStart=1/24초, LocalStop=250/24초. 차이는 249/24=10.375초다.
- 각 파일의 AnimationCurve 2,034개에서 KeyTime을 읽었다. 최소 키 간격은 1/24초이고, 모든 인접 키 시간차는 그 격자의 정수 배수다.
- 따라서 UE에 들어오기 전 FBX 단계에서 이미 24 fps 시간 정보가 존재했다. 정확히 Blender의 어느 설정/스크립트가 이를 만들었는지는 이번에 확인하지 않았다.

현재 Editor PID 27064의 InGame 시퀀스 11개는 모두 data model FrameRate=24/1, RateScale=1.0이다. 대상은 Idle, Walk/Run/Sprint loop, Stop 5개, Walk StandTurn 2개다. 길이/키/marker/Root Lock/실제 import 경로는 감사 JSON에 보관했다.

ABP_Player의 Sequence Player 10개(공중 임시 Idle 포함)는 저장된 PlayRate=1.0, PlayRateBasis=1.0이고 PlayRate 입력 핀의 외부 연결은 없다. 이는 그래프 정적 설정 검사다. Sync Group의 leader/follower 보정, 원작 런타임, Time Dilation을 측정한 결과는 아니다.

Epic 문서상 Target Frame Rate는 생성/임포트 시간축을 나타내며, Rate Scale은 재생 속도다. Import Custom Sample Rate를 바꾸는 리샘플링과 시간을 압축하는 리타이밍은 구분해야 한다. **이미 느린 시간으로 만들어진 FBX를 30 fps로 리샘플링한다고 원래 시간이 자동 복구된다고 보장할 수 없다.**

출처: [Epic Animation Sequence Editor](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-sequence-editor-in-unreal-engine).

## 4. 프레임 진행의 일대일 대응 검사

PSA와 UE의 좌표축/rest transform 차이 때문에 quaternion 값을 직접 동일 비교하지 않았다. 인접 두 프레임 quaternion의 회전각 차이를 비교했다. 고정된 좌표축 변환과 quaternion 부호 변화는 이 회전각 크기를 바꾸지 않는다.

검사 본: `bip001-l-calf`, `bip001-r-calf`, `bip001-spine1`, `bip001-l-thigh`.

검사 구간:

- Run_F, Sprint_F, Sprint_Stop_F_02: UE 0~41 프레임.
- Walk_F: UE 0~29 프레임.
- Walk_StandTurn_L_180: UE 0~11 프레임.

Weapons의 미편집 import와 현재 InGame 작업본 각각에서 RAW pose를 읽었다. 리타게팅/Root Motion 추출은 하지 않았다. PSA frame offset 0/1/2 중 모두 **+1**이 가장 잘 맞았다. 즉 검사한 구간의 UE frame i는 PSA frame i+1의 동작 진행에 대응한다.

현재 InGame 종아리 본의 인접 회전각 변화 오차는 최대 약 0.000138도, 검사한 네 본 전체 최대 오차는 Walk 왼쪽 허벅지에서 약 0.019468도다. 시간 보간으로 30→24 fps 리샘플링한 것보다 연속 원본 키를 24 fps에 그대로 배치한 해석을 지지한다.

이 결과는 **선택한 본/구간의 시간 대응 검사**다. 모든 본 위치/회전의 완전 일치, 모든 프레임의 보존, 압축 pose나 시각적 접지 품질의 전수 합격은 아니다. 끝점 복사 편집은 의도적으로 검사 범위에서 제외했다.

한 프레임 offset은 FBX의 1~250 export 구간과도 일치한다. 따라서 현재 편집본의 전체 길이를 PSA 전체 길이와 그대로 나누어 배속을 정하면 안 된다. 첫 프레임 누락, 사용자 trim 및 마지막 pose 복사로 비교 구간이 다르다.

## 5. 제안하는 비교 방법 — 아직 적용하지 않음

동일한 키 구간을 기준으로 하면:

```text
현재 시간 / 30 fps 기준 시간 = (구간 수 / 24) / (구간 수 / 30)
                             = 30 / 24 = 1.25
현재 동작 진행 속도 / 기준 속도 = 24 / 30 = 0.8
```

따라서 같은 구간은 약 25% 더 오래 걸리고, 동작 진행은 약 20% 느리다. **RateScale 또는 node PlayRate 중 한 곳에 1.25를 적용하는 비교 테스트**가 근거 있는 첫 후보다. 두 곳에 모두 적용하면 1.5625배가 되므로 중복 보정하지 않는다.

| 현재 작업본 | 현재 asset 길이 | 1.25배 재생 시 실제 시간 |
| --- | ---: | ---: |
| Walk loop | 1.375초 | 1.100초 |
| Run loop | 4.958333초 | 약 3.966667초 |
| Sprint loop | 4.958333초 | 약 3.966667초 |
| Sprint Stop | 4.750초 | 3.800초 |

RateScale만 바꿔도 asset에 저장된 길이/marker 시간이 위 오른쪽 값으로 바뀌는 것은 아니다. 재생 시 시간을 더 빠르게 통과하는 것이다.

안전한 비교 순서:

1. 현재 InGame Run loop를 임시 비교 복사본으로 준비하고 기존 ABP 참조는 유지한다.
2. 미리보기 배속을 1.0으로 맞추고 복사본의 RateScale 1.0 / 1.25를 비교한다. 이 시점에서는 원본/기존 loop/Stop을 일괄 변경하지 않는다.
3. 기본 속도 차이와 원작의 추가 연출/ABP 배속 차이를 구분한다. 원작과 완전히 같은 최종 속도를 원하면 동일 동작 구간의 원작 시간 자료가 추가로 필요하다.
4. 채택 전 loop와 Stop의 접지·Sync·기존 170/470/600 이동 속도와 보폭을 함께 검사한다. 배속 보정이 자동으로 발 미끄러짐까지 해결하지는 않는다.
5. 장기적인 source 시간축 수정은 별도 작업으로 수행한다. 기존 시퀀스에 대한 무검사 Reimport는 금지한다.

보존해야 하는 편집: loop 마지막 pose 복사, Sync Marker/Notify/curve, 사용자 clip trim, Stop Root→C_P_Kazan 변환 및 Root Lock, 현재 ABP 참조.

RateScale만 변경하는 경우 marker를 따로 0.8배 위치로 옮기지 않는다. 포즈와 marker가 같은 asset 시간축을 더 빨리 통과한다. **같은 구간의 asset 시간을 실제로 0.8배로 리타이밍**하는 작업을 선택할 때는 marker/notify/curve 시간도 함께 변환해야 한다. 누락 sample 복원/구간 변경까지 한다면 단순 0.8배 공식만으로 처리하지 않는다.

## 6. 재개 조건과 원작 속도 확정의 한계

- 이번 요청의 FPS 진단은 위 증거 수준에서 완료했다. 속도 수정/전수 보정은 사용자가 요청하지 않아 적용하지 않았다.
- 먼저 1.25배 비교 기준을 확인한 뒤 Walk Turn의 유효 구간, SprintPivot의 제동 구간/해제 시점을 설계한다. 시간축이 정해지기 전에 절대 초 단위 Pivot timer를 확정하지 않는다.
- Walk StandTurn 두 시퀀스는 현재도 249구간/10.375초로 임포트되어 있다. PSA는 16키이므로 전체 임포트 길이를 실제 Turn 동작 길이로 사용하지 않는다. 이번에 무의미 구간을 삭제하거나 root를 편집하지 않았다.
- 원작 실행 시 최종 PlayRate, Time Dilation, montage/graph 조정, PSA를 추출한 정확한 exporter 버전은 미확인이다. 따라서 최종 원작 속도까지 100% 동일하다고 보장하지 않는다.
- 동일 질문은 이 문서와 감사 JSON을 먼저 읽는다. source snapshot이나 현재 에셋이 바뀐 경우에만 해당 파일을 표적 재검사한다.

## 7. 2026-09-16 — WeakAtk01 구간별 재생 속도 표적 확인

이번 확인은 일반 locomotion 시퀀스의 고정 배속과 별개로, 원작 DualAxeSword 약공격 Composite가 시간축을 어떻게 바꾸는지 표적 조사한 결과다. 원본 package와 계산 결과는 `Saved/ImportReports/Khazan_DAS_WeakAttack_Timing_20260916.json`에 보존했다.

### 원본 데이터 계약

- 원작 gameplay asset은 `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/WeakAtk/AC_Kazan_DualAxeSword_Com_WeakAtk01`이며 class는 `AnimComposite`다.
- Composite의 단일 segment는 `CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1`의 `0.0–3.53 s`를 `AnimPlayRate=1.0`, `LoopingCount=1`로 사용한다.
- source AnimSequence 직접값은 `SequenceLength=3.5333333 s`, `NumFrames=107`, `bEnableRootMotion=true`, `bForceRootLock=true`다. Composite는 마지막 약 `0.0033333 s`를 제외한 `3.53 s`를 소비한다.
- source와 Composite 모두 별도 `RateScale` override가 직렬화돼 있지 않다. 구간별 속도 변화의 근거는 AnimSequence `RateScale`이나 segment `AnimPlayRate`가 아니라 Composite의 저장된 `DilationCurve`다.
- `DilationCurve.TimePerFrame=0.016666668 s`, `DilationSequenceLength=3.4326434 s`, `BakedDilationCurveName=Dilation`, 저장 mapping point는 213개다. 이 table은 `T_Original → T_Dilation`을 직접 제공한다.
- raw float curve의 linear key는 `(0.0027076453, -0.10675841)`, `(0.4, 0.4170467)`, `(0.53995734, 0.4170467)`, `(0.59256727, 0.0)`다. 재현에는 raw 네 key를 임의 공식으로 다시 적분하지 않고 저장된 213-point table을 정본으로 사용한다.

table의 인접 구간에서 계산한 실제 source 진행률 `ΔT_Original / ΔT_Dilation`은 약 `0.911179–1.417051`이다. 전체 평균만 계산하면 `3.53 / 3.4326434 = 1.02836199`지만, 이 고정 배율 하나는 전체 길이만 같게 만들 뿐 처음의 느린 준비와 중간 가속을 재현하지 못한다.

| 실제 재생 경과 `T_Dilation` | 평가할 source 위치 `T_Original` | 해당 table 구간의 source 진행률 |
| ---: | ---: | ---: |
| `0.000000 s` | `0.000000 s` | 약 `0.911179x` |
| `0.100000 s` | `0.095550 s` | 약 `1.010529x` |
| `0.200000 s` | `0.204107 s` | 약 `1.164346x` |
| `0.300000 s` | `0.327971 s` | 약 `1.318163x` |
| `0.400000 s` | `0.467117 s` | 약 `1.417048x` |
| `0.495476 s` | `0.592567 s` | 약 `1.036595x` |
| `0.600000 s` | `0.697354 s` | 약 `1.0x` |
| `3.4326434 s` | `3.530000 s` | 약 `1.0x` |

### 프로젝트용 재생 에셋 계산 계약

UE 5.8의 Montage Time Stretch Curve는 non-default Montage play rate일 때 사용하는 별도 weight 계약이고 음수 원본 Dilation key를 그대로 복사하는 필드가 아니다. `Montage_SetPlayRate()`를 Tick에서 계속 갱신하면 Ability에 별도 시간 상태와 취소/동기화 경계를 추가한다. P1.5에서는 이미 Enemy 재생 라이브러리에서 검증한 방식대로 원작 mapping을 pose에 bake한 별도 AnimSequence를 사용한다.

1. 출력 시간 `T_Dilation`을 `0–3.4326434 s`에서 균일 표본화한다.
2. 저장된 mapping의 역함수를 구간 선형 보간해 각 출력 시각의 `T_Original`을 구한다.
3. source segment `0–3.53 s`의 pose를 해당 위치에서 평가한다. translation/scale은 선형, quaternion은 같은 반구를 선택한 정규화 선형 보간을 사용한다.
4. 원본 `TimePerFrame`의 60 Hz를 목표로 `round(3.4326434 × 60)=206` interval, 207 sample을 만든다. 길이를 정확히 유지하는 계산 frame rate는 `5110687/85161 ≈ 60.01205951 fps`다.
5. 출력 AnimSequence `RateScale`, Montage segment `AnimPlayRate`, Ability task `Rate`는 모두 `1.0`으로 둔다. 어느 한 곳에서도 평균 배율 `1.02836199`를 다시 곱하지 않는다.

원작 Composite에는 notify 45개가 있지만 P1.5는 표현 재생과 Ability 수명만 다룬다. hit/cancel/move/VFX 등 notify 의미를 자동 이식하지 않으며 P3/P6에서 필요한 이벤트만 `T_Original → T_Dilation`으로 변환해 별도 gameplay 계약으로 구현한다. 원작 source의 root-motion flag도 직접 확인됐지만 P1.5의 현재 CMC 구동 범위에서는 root 이동을 활성화하지 않는다. 따라서 이 단계의 결과는 원작 **포즈 시간축** 재현이며 원작 공간 이동까지 완료한 결과가 아니다.

### 후속 공격에 재사용할 표적 결과

| Composite | source 구간 | Composite 길이 | Dilation 길이 | 인접 table 진행률 범위 |
| --- | --- | ---: | ---: | ---: |
| `WeakAtk01` | `FastAtk01_M1`, `0–3.53`, `+1.0x` | `3.53` | `3.4326434` | `0.911179–1.417051x` |
| `WeakAtk01_Block` | `FastAtk01_M1`, `0–0.365`, `-1.0x` | `0.365` | `0.7411443` | `0.285714–1.000001x` |
| `WeakAtk02` | `FastAtk02_M1`, `0–3.47`, `+1.0x` | `3.47` | `3.328054` | `0.999970–1.489833x` |
| `WeakAtk02_Block` | `FastAtk02_M1`, `0–0.307143`, `-1.0x` | `0.307143` | `0.5568775` | `0.357143–1.000004x` |
| `WeakAtk02_Loop` | `FastAtk02_Loop`, `0–2.0`, `+1.0x` | `2.0` | 없음 | 고정 `1.0x` |
| `WeakAtk03` | `FastAtk03_M1`, `0–4.9`, `+1.0x` | `4.9` | `4.9616776` | `0.584378–1.000024x` |
| `WeakAtk04` | `FastAtk04_M1`, `0–4.33`, `+1.0x` | `4.33` | `4.4874234` | `0.465587–1.000024x` |
| `WeakAtk05` | `Com_WeakAtk05`, `0–2.6`, `+1.0x` | `2.6` | `2.599998` | 사실상 `1.0x` |

이번 작업은 원본 package metadata의 읽기 전용 표적 확인과 report 작성이다. project AnimSequence/Montage, C++, Blueprint는 생성·수정·빌드·PIE하지 않았다.

## 8. 2026-09-16 — WeakAtk 콤보 source와 Root Motion 추가 확인

원작 `SB_Kazan_DualAxeSword_Com_WeakAtk`의 CDO `SubStateInfos`와 각 `xxChangeNextStepFunc`를 표적 대조했다.

| 원작 sub-state | Composite | 표준 press 결과/조건 |
| --- | --- | --- |
| `Step1` | `WeakAtk01` | `Step2` |
| `Step2` | `WeakAtk02` | `Step3` |
| `Step3` | `WeakAtk03` | `Step4` |
| `Step4` | `WeakAtk04` | `SP_Kazan_DualAxeSword_Flow_HyperMaster` 활성 시 `SpecialSubStateTag=Step5` |
| `Step5` | `WeakAtk04` | press 시 `Step6` |
| `Step6` | `WeakAtk05` | 마지막 공격 |

따라서 공격 번호 기준 원작 표준 source는 `FastAtk01_M1`, `FastAtk02_M1`, `FastAtk03_M1`, `FastAtk04_M1`, `Com_WeakAtk05`다. `FastAtk02_Loop`를 사용하는 별도 `WeakAtk02_Loop` Composite는 이 Skill Blueprint의 `SubStateInfos` 어디에서도 참조되지 않는다. 해당 Composite에는 `EInputType::Absorb`인 `xxSkillInputProg`가 별도로 있으므로 표준 2타와 합치지 않고 특수 분기 후보로 보존한다. 정확한 진입 owner는 이번 자료만으로 확정하지 않았다.

`Step1`–`Step6`의 직접값은 모두 `AnimPlayRate=1.0`, `AnimLoopCount=1`, `bApplyAttackSpeed=true`다. 이 `bApplyAttackSpeed`는 캐릭터의 gameplay 공격 속도 배율을 적용할 수 있다는 별도 계약이며, 각 Composite 내부의 Dilation mapping과 같은 값이 아니다. 현재 프로젝트에는 확정된 Attack Speed attribute가 없으므로 P1.5 runtime task rate는 항등값 `1.0`으로 유지한다.

선정 source의 PSA `Root` 첫/끝 translation과 전 구간 이동을 계산했다. 아래 값은 PSA 좌표에서 Y 부호를 프로젝트 변환 규칙에 맞춘 **원본 기반 계산값**이며, 실제 UE world forward 축과 collision 결과는 import 후 검증한다.

| source | samples | root 시작→끝 변위 `(cm)` | root path distance `(cm)` |
| --- | ---: | ---: | ---: |
| `FastAtk01_M1` | 107 | `(0, 131.546982, 0)` | `181.456085` |
| `FastAtk02_M1` | 102 | `(0, 122.070999, 0)` | `185.975418` |
| `FastAtk03_M1` | 147 | `(0, 142.787994, 0)` | `220.271576` |
| `FastAtk04_M1` | 131 | `(0, 220.000000, 0)` | `300.872437` |
| `Com_WeakAtk05` | 79 | `(0, 208.660980, 0)` | `251.408783` |

1–4타 source package는 모두 `bEnableRootMotion=true`, `bForceRootLock=true`를 직접 직렬화한다. 5타 source package의 해당 flag는 현재 표적 추출본에 없지만 PSA Root track의 실변위는 위와 같다. 사용자가 모든 스킬에 Root Motion을 사용한다고 확정했으므로 파생 playback Sequence는 몸 pose와 Root track을 같은 Dilation 시간축으로 재표본화하고 `Enable Root Motion=true`로 만든다.

이 절은 위 §7의 `P1.5에서는 root 이동을 활성화하지 않는다`는 프로젝트 적용 결론을 대체한다. §7의 원본 Dilation table, 길이, source rate 계산은 그대로 유효하다. Float Curve/AnimNotifyState에서 매 tick Montage rate를 바꾸지 않으며, Sequence/Montage/Ability task의 상수 배율은 모두 `1.0`이다.

이번 확인은 `Saved/OriginalAttackTiming/Metadata/.../SB_Kazan_DualAxeSword_Com_WeakAtk.json`, 각 WeakAtk Composite/source AnimSequence metadata, `Saved/ImportReports/Khazan_DAS_PSA_SourceMetadata.json`의 읽기 전용 분석이다. project AnimSequence/Montage/C++/Blueprint/build/PIE는 변경·실행하지 않았다.

## 9. 2026-09-16 전수 시간축 복원 적용 결과

§7–8은 당시 읽기 전용 분석 범위를 설명한다. 이후 사용자의 직접 임포트 요청에 따라 원본 시간축 복원을 실제 Content에 적용했다.

- 원본 source 457개, 미사용 파생 locomotion 164개, Composite playback 360개, 총 981개를 저장했다.
- Composite playback 360개 중 250개에는 원작 Dilation mapping이 pose와 Root track에 함께 bake됐다. playback basename은 원작 `AC_...` 이름을 유지한다.
- 현재 ABP가 참조하는 locomotion 9개는 별도로 전수 검사하고 hash 보호했다. 24 fps × `RateScale 1.25`로 유효 30 fps지만 원본과 sample 수/유효 길이가 달라 marker-aware exact-source migration 검토가 필요하다.
- 미사용 locomotion 271개는 source 107개 + InGame 57개 + Runtime 107개이며 모두 복원했다. 파생본의 Sync Marker는 프레임 위치 기준으로 새 시간축에 이관했다.
- 최종 fresh-process audit는 981/981개와 보호 locomotion 9개를 검증해 `passed`다. 정본은 `Saved/ImportReports/Khazan_DAS_AnimationFinalAudit_20260916.json`이다.
- 이 적용은 Animation Content 복원까지다. Montage/Ability event 연결과 PIE에서의 콤보·Root Motion·피격/VFX 품질 판정은 아직 후속 범위다.
