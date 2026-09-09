# 2026-09-08 Stop 시퀀스 Root → C_P_Kazan Bake

## 요청 범위와 생성 결과

사용자 요청대로 원본 세 시퀀스를 같은 폴더에 `_New`로 복사하고 Root/C_P_Kazan의 애니메이션 트랙만 수정했다. 실제 스켈레톤 계층은 유지한다.

공통 경로: `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion`.

| 생성 시퀀스 | 프레임 구간 / sample keys | 길이 | Sync Marker |
| --- | --- | ---: | ---: |
| Run/DAS_Khazan_Run_Stop_LF_New | 95 / 96 | 3.958333초 | 원본 0개 유지 |
| Run/DAS_Khazan_Run_Stop_RF_New | 91 / 92 | 3.791667초 | 원본 0개 유지 |
| Sprint/DAS_Khazan_Sprint_Stop_New | 114 / 115 | 4.75초 | 원본 0개 유지 |

현재 원본의 이름은 `DAS_Khazan_Sprint_Stop`이다. RF와 Sprint 길이도 이번 작업 시작 시점의 사용자 편집값을 읽었으며, 이전 복구 문서의 길이로 되돌리지 않았다. 세 시퀀스 모두 24 fps다.

## 두 본의 처리

- 기존 계층: `C_P_Kazan → Root → Bip001/기타 자식`. C_P_Kazan의 직접 자식은 Root 하나이며 reference scale은 `(100,100,100)`이다.
- 각 프레임의 Root와 C_P_Kazan 변환을 합성하여 C_P_Kazan의 새 FK Control Rig 키를 작성했다. 단순 숫자 복사로 상위 scale 100을 누락하지 않았다.
- Root의 **애니메이션 트랙만 제거**하여 해당 본을 Skeleton reference pose로 평가하게 했다. Root 본과 자식 본을 삭제하거나 스켈레톤을 편집하지 않았다.
- 원본 226개 트랙 중 Root 하나가 C_P_Kazan으로 교체되어 `_New`도 226개 트랙이다. 나머지 225개 본의 FK Control Rig 채널 2,025개는 키 시간·값·보간·탄젠트·기본값·외삽 설정까지 원본과 동일하다.

UE의 local * parent 변환 순서에서 다음 관계를 사용했다.

```text
Parent_new(t) = Root_ref^-1 * Root_old(t) * Parent_old(t)
Root_new(t)   = Root_ref

Root_new(t) * Parent_new(t) = Root_old(t) * Parent_old(t)
```

따라서 Root 이하의 컴포넌트 공간 포즈와 이동 궤적은 원본을 유지하면서 최상위 C_P_Kazan 트랙에 움직임이 들어간다. 구현은 UE 5.8 `AnimationSequencerDataModel`의 내부 FK Control Rig를 `AnimationDataController`로 편집해 AnimSequence에 저장하고 압축하는 방식이다. 별도 FBX 재임포트나 전체 본 재샘플링은 하지 않았다. 새로 Bake한 본은 C_P_Kazan 하나이며 Root 트랙만 비웠다.

## 보존과 검증

- 세 원본은 수정하지 않았다. 나머지 InGame 파일, SK_Khazan/SKM_Khazan, ABP_Player, KhazanAnimInstance.h/.cpp를 포함한 보호 파일 71개가 작업 전 SHA-256과 동일하다.
- 일반 속성 및 시퀀스/임포트 정보 스냅샷 35개 항목을 비교했다. 길이, fps, sample 수, Rate Scale, Sync Marker/Notify, Curve/metadata, 압축 설정, root 정책 등의 원본값이 유지된다.
- 원본과 `_New`의 Root/C_P_Kazan 이외 Control Rig 채널은 정확히 동일하다. 중간 프레임이나 사용자 포즈 키를 원본 추출본으로 대체하지 않았다.
- 모든 프레임에서 Root 이하 RAW 컴포넌트 포즈를 비교했다. 최대 위치 차이는 LF/RF 약 0.0002442, Sprint 약 0.0004883 UE mesh-space 단위이며 float 저장 오차 범위다. 최대 회전 차이는 약 0.00000242도, scale 차이는 0이다.
- SKM_Khazan을 지정한 압축 포즈도 모든 프레임에서 비교했다. 재압축에 따른 최대 컴포넌트 위치 차이는 0.032568 UE mesh-space 단위 미만, 회전 차이는 0.002839도 미만이다. Root는 reference pose로 유지되고 C_P_Kazan 트랙의 처음/끝 이동이 확인된다.
- 별도 UnrealEditor-Cmd 프로세스에서 저장본 검증 3/3을 통과했다. Exit code 0, 엔진 오류 0이다. 기존 Lumen scalability 우선순위 경고 1개는 이 작업과 무관하다.

원본의 **Enable Root Motion=false**, **Force Root Lock=false**, **Use Normalized Root Motion Scale=true**, **Root Lock=Ref Pose**도 그대로 보존했다. 사용자 지시가 본 키 편집에 한정되므로 활성화/스케일 정규화 옵션은 변경하지 않았다. 이 작업의 검증 범위는 본 데이터 이관 및 포즈 보존이며, CharacterMovement의 실제 Root Motion 추출 거리·활성화·PIE 이동까지 완료한 것은 아니다. 상위 본의 scale 100과 root motion scale 정규화 옵션을 고려하지 않고 mesh-space 이동량을 게임 내 이동 거리로 읽지 않는다.

## 백업과 재검증

- 백업: `Saved/ArtBackups/DAS_StopRootTransfer_20260908_141845`. 원본 3개, 6,077,827 bytes를 복사한 뒤 SHA-256을 확인했다. `manifest.json`은 보호 파일 해시, `baseline.json`은 원본 속성과 기타 채널 해시다.
- 구현: `Scripts/Animation/bake_das_stop_root_to_dummy.py`.
- 생성 리포트: `Saved/ImportReports/Khazan_DAS_StopRootTransfer_build_20260908.json`.
- 최종 검증: `Saved/ImportReports/Khazan_DAS_StopRootTransfer_verify_20260908.json` (`passed`, `commandlet=true`).
- 최종 로그: `Saved/Logs/Khazan_DAS_StopRootTransfer_FreshAudit_20260908.log`.

기본 실행은 읽기 전용 `verify`다. 이미 생성된 `_New`나 baseline이 있으면 `build`를 거부하여 사용자 파일을 덮어쓰지 않는다. 이후 사용자가 수정한 자산은 기존 baseline과 달라질 수 있으므로 검사 실패를 무조건 손상으로 판단하지 않는다.

```powershell
& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  'C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' `
  -run=pythonscript `
  -script='C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Animation/bake_das_stop_root_to_dummy.py' `
  -nullrhi -unattended -nosound -nosplash -nop4 `
  '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
```

마지막 인자는 실행 중 Editor와 MCP 포트가 충돌하지 않도록 commandlet에만 적용한다. 프로젝트 설정 파일은 변경하지 않는다.
