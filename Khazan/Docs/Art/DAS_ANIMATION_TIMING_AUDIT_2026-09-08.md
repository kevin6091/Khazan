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

