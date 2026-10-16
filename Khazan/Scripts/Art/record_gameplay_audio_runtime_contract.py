"""Append the concrete runtime ownership contract before applying its small diff."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil

root=Path(__file__).resolve().parents[2]
out=root/'Saved/ImportReports/GameplayAudio_20261011'
files=['Source/Khazan/Ability/Combo/KZComboTypes.h',
       'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
       'Source/Khazan/Khazan.Build.cs']
baseline={}
for rel in files:
    p=root/rel
    dest=out/'BeforeRuntime'/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    assert not dest.exists(),str(dest)
    shutil.copy2(p,dest)
    baseline[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'RuntimeBaseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
text='''
## 2026-10-11 — ARCH-89 원작 사운드 재생 계약 (적용 전)

현재 사운드 직접 구현 요청은 기존 GAS/Ability/Task/CMC/피해 승인 경계를 유지하는 Presentation 확장이다. 새 runtime 파일은 stateless Audio Notify/NotifyState h·cpp4개다. 데이터는 SoundCue·SoundWave·엔진 attenuation/concurrency가 소유한다. 일반 유한음은 실제 Actor의 엔진 AudioComponent가 원본 끝음까지 재생·자동 정리하며, 반복/명시적 stop 구간은 실제 Mesh와 engine notify occurrence ID의 component tag로 자기 컴포넌트만 찾아 종료한다. Notify UObject에 공유 재생 상태나 원장, 전역 manager/FSM/MainAnimInstance 상태·Tick을 추가하지 않는다. Actor 파괴는 엔진 StopWhenOwnerDestroyed, 애니메이션 교체/취소는 NotifyState End로 정리한다.

원본 xxAkEvent/Footstep/PostAudioEvent/UntilAnimEnd의 시작·종료는 원본 AnimationTrack의 trim/rate/loop 및 SourceDilationCurve를 현행 baked sequence에 한 번만 변환한다. Montage와 그 child sequence에 같은 사운드를 중복 저작하지 않는다. 발소리의 실제 지면 선택은 CMC 범위 trace/PhysicalMaterial·기존 Snow owner이며 원본 physical_material switch를 native SoundCue 정수 파라미터로 선택한다. 피해/막기 소리는 기존 FKZAttackCollisionWindow의 선택적인 SoundBase2개와 실제 승인 결과만 소비한다. 공격 실패/단순 이동은 적중 소리를 만들지 않는다.

Wwise bank mix의 gain/delay/layer·한국어 kz 분기와 랜덤 변형은 오프라인 복원 후 UE cue로 재생한다. 수학적 unity1 및 cm/s 단위 변환을 튜닝으로 혼동하지 않는다. 원본 수치가 없는 취소 anti-click fade·native 공간/리버브/voice budget은 조정 가능한 명시적 임시 표현 설정으로 기록하고 원작 SDK·플러그인 DSP 동일성으로 표현하지 않는다. 후처리/조명·눈/RootMotion/UI/gameplay 수치는 이번 사운드 작업으로 되돌리지 않는다. 이 절은 적용 전 계약이며 import/build/PIE 완료가 아니다.
'''
p=root/'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md'
with p.open('a',encoding='utf-8') as f:f.write(text)
print('ARCH-89 appended; preserved current runtime snapshot',len(files))
