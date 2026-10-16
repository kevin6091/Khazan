from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = root / 'Saved/ImportReports/GameplayAudio_20261011'
out.mkdir(parents=True, exist_ok=True)
original = root / 'Saved/Extracted/GameplayAudio_20261011'
original.mkdir(parents=True, exist_ok=True)
backup = out / 'Before'
backup.mkdir(exist_ok=True)
tool = root / 'Scripts/Enemies/EnemyExtractor/Program.cs'
text = tool.read_text(encoding='utf-8-sig')
# Recover only the two newly inserted inspection modes for the before snapshot;
# preserve every byte-level source decision outside these exact inserted ranges.
for start, end in [('        if (args[0] == "audio-api")', '        if (args[0] == "api")'),
                   ('        if (args[0] == "audio-index")', '        if (args[0] == "font-data")')]:
    i, j = text.index(start), text.index(end)
    assert i < j
    text = text[:i] + text[j:]
before_tool = backup / 'EnemyExtractor.Program.cs'
if not before_tool.exists():
    before_tool.write_text(text, encoding='utf-8')
for relative in ['Binaries/Win64/UnrealEditor.modules', 'Config/DefaultEngine.ini']:
    target = backup / Path(relative).name
    if not target.exists():
        target.write_bytes((root / relative).read_bytes())
state = {'task': 'GameplayAudio_20261011', 'started_utc': datetime.now(timezone.utc).isoformat(),
         'phase': 'FModel dual-chunk audio index and original-event/timing analysis',
         'initial_sound_related_packages': 23536, 'sound_exports': 0, 'imports': 0,
         'runtime_source_edits': 0, 'background_editor_only': True,
         'source_tool': str(tool), 'source_before_sha256': hashlib.sha256(before_tool.read_bytes()).hexdigest()}
(out / 'ResumeState.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
marker = '<!-- GameplayAudio_20261011_DiscoveryCheckpoint -->'
art = '''
## 2026-10-11 — Player/Monster/HeinMach 원작 사운드 작업 시작·중단 재개점

사용자는 FModel chunk0/chunk1 모두에서 필요한 음원과 metadata를 추출·임포트하고 현행 Player/Monster6 행동·상호작용 및 HeinMach 환경음을 실제 타이밍에 연결하도록 직접 요청했다. 최신 Main의 Sky/Fog와 후처리 제거·공격 VFX 보정, root flags·카메라 변경을 보존한다. 원작 숫자를 우선하고 미확인 audio 튜닝은 TEMP로 분리한다.

현재 FModel GAME_UE4_27/DesktopMobile provider와 active GameDirectory/AES를 로컬 설정에서 재사용한다. AES는 출력/문서에 쓰지 않는다. 설치 paks는 pakchunk0-WindowsNoEditor.pak(29,171,917,980 bytes), pakchunk1-WindowsNoEditor.pak(21,454,569,878 bytes), tiny optional chunk0다. 기존 sound 지식/구현/UE Sound assets는 발견하지 못했다. 기존 EnemyExtractor index에서 sound 관련23536 package를 얻었고 원작 xxAnimNotify_AkEvent를 cached BindingSource에서 확인했다. 초기 중단은 이 read-only discovery 단계였고 음원 추출/임포트/runtime 수정0이었다.

현재 추출 도구에 audio-api/audio-index inspection을 추가하고 build·실제 archive owner/음원 데이터·Event→media→timeline을 확인하는 중이다. 증거는 Saved/Extracted/GameplayAudio_20261011/Index01, Saved/ImportReports/GameplayAudio_20261011/ResumeState.json 및 Before에 보존한다. 아직 완성/원작 음향 일치를 기록하지 않는다. 재개: tool build/API dump→archive별 audio index→현행 행동 source notify와 HeinMach sound actor metadata→필요 event closure만 extract/decode→품질/끝음/볼륨/reverb 계획→import→기존 실행 owner에 연결→별도 background editor build/saved/native audio 검증. 기존 전체 mesh/VFX authoring이나 과거 private Source 전달을 반복하지 않는다.
'''
engineering = '''
## 2026-10-11 — 사운드 실제 재생 Mixed 요청: 실행 구조 조사 중

FModel 사운드 추출·임포트와 Player/Monster 행동·상호작용/HeinMach 환경음 실제 재생 요청이다. Router→Architecture 최신 ARCH-83/84/85/86와 Migration→현재 Source를 확인 중이다. 기존 Source에 Sound/PlaySound/AudioComponent 경로가 발견되지 않았고 runtime 수정은 아직0이다. ActionAbility의 실행/취소·확정 hit, Monster actual anim context/Death, 엔진 audio/component/notify 수명을 먼저 재사용하며 새 만능 AudioManager/FSM/MainAnimInstance 상태 사본을 만들지 않는다.

원작 AkEvent/음원/수치 조사 상태와 exact extraction resume는 Docs/Art/ART_WORK_CONTINUITY.md의 같은 작업 절을 따른다. 현재 Main module UnrealEditor-Khazan-2026101101.dll과 기존 source/asset을 보존한다. 현재 준비 단계이며 build/PIE/audio 검증 완료가 아니다. 사용자 Rider 에디터 제어 없이 task-owned hidden process만 사용한다.
'''
for relative, body in [('Docs/Art/ART_WORK_CONTINUITY.md', art),
                       ('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md', engineering)]:
    file = root / relative
    if marker not in file.read_text(encoding='utf-8'):
        with file.open('a', encoding='utf-8') as stream:
            stream.write('\n' + body.strip() + '\n\n' + marker + '\n')
print('Audio task checkpoint recorded; no imported sounds or runtime edits yet.')
