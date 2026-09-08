# 2026-09-08 Khazan 본 삭제 후 애니메이션 복구

## 확인한 원인과 완료 결과

`SK_Khazan`과 `SKM_Khazan`은 작업 시작 시점부터 Git HEAD와 SHA-256이 같았다. 현재 계층은 `C_P_Kazan → Root → Bip001`이며, `C_P_Kazan`의 reference scale은 `(100, 100, 100)`이다.

InGame AnimSequence 63개 중 사용자 작업본 8개에서 몸과 팔다리 트랙이 삭제되어 `root` 하나만 남았다. 나머지 55개와 대응하는 Weapons 원본 8개는 226개 트랙을 유지했다. 따라서 스켈레톤만 복원하거나 AnimInstance를 수정해도 삭제된 애니메이션 트랙은 돌아오지 않는다.

로컬 UE 5.8.2의 `AnimSequencerController.cpp`에서 skeleton update는 새 계층에 없는 본 트랙을 `RemoveBoneTracksMissingFromSkeleton()`으로 제거한다. 현재의 손상 형태는 이 동작 및 사용자의 본 삭제 이력과 일치한다. 삭제 순간의 모든 분기를 debugger로 재현한 것은 아니다.

정상 Weapons 원본에서 누락된 225개 본의 로컬 포즈를 기존 24 fps 샘플 시각에 평가하여 해당 트랙만 복구했다. 먼저 별도 복사본 8개를 검증한 뒤 현재 작업본에 적용하고 저장했다. 기존 root 키 전체, 시퀀스 길이, 마커 이름/시간/트랙, Notify, Curve 수, metadata와 시퀀스 설정은 보존 검사를 통과했다. C++/ABP/스켈레톤/메시는 수정하지 않았다.

## 복구한 작업본

공통 경로: `/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion`.
프레임 구간은 마지막 프레임 인덱스이며, 샘플 키 수는 각 값에 1을 더한 수다.

| 상대 경로 | 프레임 구간 | 길이(초) | Sync Marker | 복구 후 트랙 |
| --- | ---: | ---: | ---: | ---: |
| Walk/DAS_Khazan_Walk_Loop | 33 | 1.375 | 2 | 226 |
| Run/DAS_Khazan_Run_Loop | 119 | 4.958333 | 12 | 226 |
| Sprint/DAS_Khazan_Sprint_Loop | 119 | 4.958333 | 16 | 226 |
| Walk/DAS_Khazan_Walk_Stop_LF | 40 | 1.666667 | 0 | 226 |
| Walk/DAS_Khazan_Walk_Stop_RF | 249 | 10.375 | 0 | 226 |
| Run/DAS_Khazan_Run_Stop_LF | 95 | 3.958333 | 0 | 226 |
| Run/DAS_Khazan_Run_Stop_RF | 249 | 10.375 | 0 | 226 |
| Sprint/DAS_Khazan_Sprint_Stop_LF | 249 | 10.375 | 0 | 226 |

Sprint Stop의 import provenance는 `CA_P_Kazan_DualAxeSword_Sprint_Stop_F_02.fbx`다. 실제 대응 원본도 `_02`를 사용했다. 이름의 LF를 근거로 첫 번째 Sprint Stop 원본을 가져오지 않았다.

Sprint Stop은 이번 작업 시작 시점에 이미 249프레임 구간/10.375초였다. 직전 작업 문서의 114프레임 구간/4.75초와 다르다. 사용자에게 길이를 질문했으며 답변이 없는 현재는 시작 시점의 저장 길이를 보존했다. 4.75초 tail 편집까지 복원했다고 기록하지 않는다. Walk/Run RF도 현재 저장 길이 10.375초를 보존했다.

## 검증 및 백업

- `Saved/ArtBackups/Khazan_SkeletonRecovery_20260908_132146/manifest.json`: InGame 현재 파일, SK/SKM/ABP와 해당 자동 저장본 82개, 492,441,030 bytes. 복사 후 파일별 SHA-256 일치를 확인했다.
- `Saved/ImportReports/Khazan_SkeletonRecovery_InGame_Before_20260908.json`: 표적 63개 시퀀스의 복구 전 트랙 수와 길이.
- `Saved/ImportReports/Khazan_SkeletonRecovery_prepare_20260908.json`: `/Game/_Recovery/KhazanSkeleton_20260908`의 검토용 복사본 8개 검증.
- `Saved/ImportReports/Khazan_SkeletonRecovery_apply_20260908.json`: 실제 작업본 8개 적용과 기존 root 키 SHA-256.
- `Saved/ImportReports/Khazan_SkeletonRecovery_FreshAudit_20260908.json`: 별도 프로세스에서 8개 저장 파일을 다시 읽은 최종 검증. 복구한 모든 본/프레임의 RAW 포즈 비교, 기존 root 키/설정/마커 보존, SKM_Khazan을 사용한 compressed pose와 실제 발 회전 변화 검사를 통과했다. 보호 대상 Content 파일 61개는 백업과 SHA-256이 동일하다.
- `Saved/Logs/Khazan_SkeletonRecovery_FreshAudit_Final_20260908.log`: commandlet exit code 0, 엔진 오류 0. Lumen scalability 우선순위 경고 1개는 기존 설정이다. 첫 실행은 데이터 검사에 통과했지만 실행 중인 Editor의 MCP 18080 포트와 충돌해 exit 1이었으며, 최종 실행에만 MCP auto-start를 끄는 command-line INI override를 사용했다. 프로젝트 설정은 수정하지 않았다.
- `Saved/Screenshots/WindowsEditor/RiderMCP/20260908-043222_preview_DAS_Khazan_Walk_Loop.png`: 복구한 Walk의 live thumbnail. 압축 애니메이션 동작은 포즈 평가로 확인했고, 새 PIE 입력/전이/발 접지 품질까지 검증한 것은 아니다.

RAW 복구 오차의 전체 최댓값은 로컬 위치 0.000099 UE 단위 미만, 회전 0.0018도 미만이다. 저장 후 다시 읽어도 검사를 통과했다. 상위 본의 scale 100 때문에 mesh-space 거리 수치를 게임 내 캡슐 이동 거리로 해석하지 않는다.

## 재실행과 추가 복구

구현은 `Scripts/Animation/recover_khazan_missing_bone_tracks.py`, 읽기 전용 검증은 `Scripts/Animation/verify_khazan_bone_track_recovery.py`다. 복구 스크립트는 해당 날짜의 8개와 백업 manifest에 한정하며, 현재 정상화된 파일에 무조건 재실행하는 일반 임포터가 아니다. `prepare` 복사본 8개 검증 및 적용 전 원본 hash/dirty 여부를 확인한 뒤에만 `apply`가 허용된다. 현재는 이미 적용되어 시작 시점 hash와 다르므로 재적용이 차단되는 것이 정상이다.

검증 재실행 명령(PowerShell):

```powershell
& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  'C:/Users/user/Desktop/GitProject/Khazan/Khazan/Khazan.uproject' `
  -run=pythonscript `
  -script='C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Animation/verify_khazan_bone_track_recovery.py' `
  -nullrhi -unattended -nosound -nosplash -nop4 `
  '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
```

추가 편집 후에는 기존 검사 기준의 길이/마커와 달라질 수 있으므로 실패를 곧바로 재손상으로 판정하지 않는다. 이번 시작 시점의 바이너리 백업은 손상 상태와 사용자 편집을 보존한 자료이며, 정상 원본 애니메이션 전체를 의미하지 않는다.

## Root를 실제 최상위로 만들 때

이번 복구 기준은 원래 계층이다. 기존 공유 스켈레톤에서 `C_P_Kazan`을 다시 삭제하는 방식은 사용하지 않는다. 최상위 본의 scale 100도 있어 이름이나 부모 관계만 바꾸면 포즈/스케일의 의미가 달라질 수 있다.

별도 Skeleton/Mesh 복사본에서 상위 본의 reference transform과 애니메이션 transform을 함께 반영하여 새 Root 계층으로 변환하고, 같은 계층에 맞춘 애니메이션을 bake 또는 retarget한다. 공유하는 모듈 파츠, skinning, skeleton 참조, 길이와 marker 시각을 함께 검증한 뒤 런타임 참조를 옮긴다. 이 계층 변경은 이번 복구에서 수행하지 않았다.

[Epic Skeletons 문서](https://dev.epicgames.com/documentation/unreal-engine/skeletons-in-unreal-engine?lang=en-US)는 Skeleton이 계층과 애니메이션 데이터를 연결하며, 다른 본 계층/이름의 메시는 별도 Skeleton이 필요함을 설명한다. 편집 도구는 [Epic Skeleton Editing 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/skeleton-editing-in-unreal-engine)를 참고한다.

## 2026-09-08 추가 복구: Control Rig로 맞춘 loop 처음/끝 포즈

사용자가 세 loop를 Control Rig에서 0번 키를 마지막 프레임에 복사해 Bake했다는 추가 정보를 제공했다. 앞선 복구는 삭제된 본 트랙을 Weapons 원본으로 채워 재생을 복구했으며, 이 끝 프레임 수동 편집까지 재현하지 못했다. 따라서 앞선 완료 기록은 사용자가 Bake한 포즈 편집 전체의 복구를 뜻하지 않는다.

현재 세 시퀀스의 첫/끝 RAW 포즈를 비교한 결과 차이가 있었으며, 본 회전의 최대 차이는 Walk 15.0393도, Run 16.1999도, Sprint 41.6792도였다. 사용자 지시대로 현재 0번 프레임의 본 위치·회전·스케일을 마지막 샘플에 복사하여 AnimSequence 결과를 복원하고 저장했다.

| 시퀀스 | 복사 | 길이 유지 | Sync Marker 유지 | 저장 후 RAW/Compressed 처음·끝 차이 |
| --- | --- | ---: | ---: | --- |
| DAS_Khazan_Walk_Loop | 0 → 33 | 1.375초 | 2 | 위치/회전/스케일 0 |
| DAS_Khazan_Run_Loop | 0 → 119 | 4.958333초 | 12 | 위치/회전/스케일 0 |
| DAS_Khazan_Sprint_Loop | 0 → 119 | 4.958333초 | 16 | 위치/회전/스케일 0 |

- 세 시퀀스의 226개 본 트랙에 적용했다. 마지막 프레임을 추가하지 않았으며 기존 마지막 sample을 사용했다. 길이, fps, 키 수, root 정책, 마커 이름/시간/트랙, Notify, Curve/metadata와 설정은 유지했다.
- 0번부터 마지막 직전까지 모든 본/프레임을 변경 전 스냅샷과 비교했다. 위치와 스케일 차이는 0, 회전 차이의 최댓값은 Quaternion↔Euler 재기록에 따른 0.000542도 미만이다. 중간 동작을 원본에서 다시 가져오거나 타이밍을 바꾸지 않았다.
- 현재 loop와 기존 Driving Level Sequence 3개, 총 6개 파일(21,537,733 bytes)을 Saved/ArtBackups/DAS_LoopClosure_20260908_134814에 백업하고 SHA-256을 확인했다. loop_pose_before.json에는 모든 변경 전 RAW 본/프레임과 설정을 저장했다.
- 구현: Scripts/Animation/restore_das_loop_end_pose.py. 기본 실행은 읽기 전용 verify이며, 실제 적용은 이미 완료했다. baseline이 있으면 apply 재실행을 차단한다.
- 적용 리포트: Saved/ImportReports/Khazan_DAS_LoopClosure_apply_20260908.json.
- 최종 리포트: Saved/ImportReports/Khazan_DAS_LoopClosure_verify_20260908.json. 별도 프로세스에서 저장된 파일을 다시 읽고 3/3 통과했다. RAW와 SKM_Khazan을 사용한 compressed pose 모두 처음·끝 차이 0이고, 보호 대상 Content 파일 66개는 변경 전과 SHA-256이 같다.
- 최종 로그: Saved/Logs/Khazan_DAS_LoopClosure_FreshAudit_20260908.log. commandlet exit 0, 엔진 오류 0이다. 기존 Lumen scalability 우선순위 경고 1개만 남았다.
- 복구 범위는 사용자가 설명한 첫 포즈 → 마지막 프레임 복사 결과다. 외부 Control Rig/Sequencer의 편집 이력이나 그래프를 복원한 것은 아니며, 기존 Driving Level Sequence는 수정하지 않았다. 추가 전이/접지/속도 연속성 조정은 하지 않았다. Stop 시퀀스, C++/ABP/스켈레톤/메시도 수정하지 않았다.

앞선 Khazan_SkeletonRecovery_FreshAudit_20260908.json은 이번 끝 프레임 편집 전의 검증 이력이다. 이제 세 loop의 마지막 프레임은 의도적으로 Weapons 원본과 다르므로 이전 source-equality 스크립트를 현행 loop 끝 포즈의 정답 검사로 사용하지 않는다. 현재는 위 loop closure verify를 사용한다. 별도 프로세스 재검증 시 이전 명령의 script만 Scripts/Animation/restore_das_loop_end_pose.py로 교체하며, MCP auto-start override는 그대로 해당 프로세스에만 적용한다.
