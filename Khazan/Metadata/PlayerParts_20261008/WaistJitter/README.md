# WaistJitter 보고서 재확인

`native_motion.py`는 로그·CSV를 읽어 JSON 보고서만 작성한다. 에디터·에셋·게임 코드는 변경하지 않는다.

PowerShell에서 프로젝트 루트를 기준으로 실행한다. 일반 Windows `python` 별칭 대신 UE의 Python을 사용할 수 있다.

```powershell
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' 'Metadata/PlayerParts_20261008/WaistJitter/native_motion.py' Candidate
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' 'Metadata/PlayerParts_20261008/WaistJitter/native_motion.py' SavedReload
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' 'Metadata/PlayerParts_20261008/WaistJitter/native_motion.py' NormalDelta --normal-delta
```

기본 입력은 `{Label}Native.log`, `PlayerWaistJitter_{Label}.csv`, `CauseProof.json`이다. 실제 speed 기준은 `Comparison_Baseline_NoIronContact.json`의 저장 RMS다. `--log`, `--csv`, `--cause-proof`, `--reference-comparison`, `--output`으로 경로를 지정할 수 있다. 출력은 `{Label}MotionVerification.json`이며 전체 검사 통과는 exit0, 실패는 exit1이다.

최신 `Khazan.PlayerParts.PIE` 시작에 대응하는 완료 이벤트만 선택한다. 최신 실행이 미완료이면 과거 성공 기록으로 대체하지 않는다. 결과·automation 오류, Hair65/35도 미만, Torso8·Leg30/45도 미만과 실제 saved joint scope를 검사한다. 이 각도는 현재 native QA 기준이며 원작 물리값이 아니다.

Iron 비교는 `IdleLate`·`AfterReleaseLate`의 positive delta, 이전 quaternion, 유효 actor 표본만 사용한다. 초기 `PhysicsOff` 오표기는 제외한다. 고정30은90/60 표본을 요구하고 일반 시간 간격은 양수 표본과 실제 평균 delta를 기록한다. 모든 후보에서 actor enabled/collision은1이어야 한다.

`--normal-delta`는 프레임당 각도가 아닌 실제 초당 속도 RMS를 비교한다. 표본 수와 시간 간격이 다른 고정 기준 대비 감소율은 설명용 관측이며 동일 시간 간격의 통제 개선율이 아니다. CauseProof의 동시 Source/BP 차이 제한도 출력에 보존한다. `allChecksPassed`는 해당 검사와 기준 대비 떨림 감소를 뜻하며 전체 시각 품질·모든 동작의 관통0을 증명하지 않는다.
