from pathlib import Path
import datetime
import json
from prepare_gameplay_audio_scope import ROOT,OUT,EXTRACT,read
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
native=read(OUT/'NativeCuePlan01.json');author=read(OUT/'AudioAuthoringPlan01.json')
state={'time':now,'status':'NativeImport03 running; animation/map author pending',
    'native_cues':len(native['cues']),'decoded_media':len(read(OUT/'NativeDecodedManifest01.json')),
    'source_packages_both_chunks':str(EXTRACT/'Index03/AudioPackageIndex.json'),
    'timelines':author['counts'],'last_build':'Build06 exit0','last_full_import':'NativeImport02 source voice concatenator child75>32 detected, corrected to one-item sequence-step adaptation',
    'remaining':['NativeImport03 exit/finalized473','Notify author645/2146 with Before hash CAS','Confirmed hit/guard DataAsset assignment','HeinMach audio actors39/fire/reverb','Fresh saved and real AudioMixer PIE checks','Domain docs/final receipt'],
    'resume_commands':['Read NativeImport03/Exit.json and Import.json and FinalizedCues count','run_gameplay_audio.py NotifyAuthor01 author_gameplay_audio_notifies.py','Do not repeat original extraction or restore old Main Source/module/map'],
    'foreign_editor_policy':'Do not operate Rider editor/other task editor; task-owned hidden process only'}
(OUT/'ResumeState02.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
art=f'''\n\n## {now} — 사운드 재개 checkpoint: 음원·native cue 변환\n\n최신 사운드 요청을 계속 처리 중이다. chunk0·chunk1 실제 archive index와 기존 source metadata를 재사용했고 NativeCuePlan01은 cue{len(native['cues'])}/decoded media1600이다. 한국어 언어ID3721600213/kz 분기, source gain·delay·random playlist weight·layer와 source physical surfaces17종을 확인했다. 발소리 layer의 duplicate230 속도 key를 보존했다. source Wwise step-sequence는 한 post에 한 항목이므로 source75 전체를 concatenator로 이어 재생하지 않는다; native one-item shuffle bag은 원본의 순차 순서와 다른 명시적 adapter다. 원본 gain/끝음을 normalize/trim하지 않고 PCM16으로 보존했다.\n\nNativeImport02는 파형1600/cue473 저장 뒤 voice concatenate75>UE max32가 검출되어 exit1이다. 전체 완료가 아니다. 수정 뒤 NativeImport03이 진행 중이다. 현재 Animation/HeinMach map author는 아직 전이며 기존 PP0/최근 Snow40cm·UI/낙하/Brutal을 되돌리지 않는다. exact 재개는 Saved/ImportReports/GameplayAudio_20261011/ResumeState02.json 및 NativeImport03/Exit.json·Import.json/FinalizedCues473 → author plan645sequence/2146notify → 환경39source·현재fire·native reverb → fresh saved/실제 audio PIE다. 기존 전체 추출을 반복하지 않는다.\n'''
eng=f'''\n\n## {now} — ARCH-89 사운드 runtime 적용·빌드 checkpoint\n\n적용 파일은 Audio Notify/NotifyState h·cpp4(신규 runtime class2), 기존 ComboDefinitionData.h/ComboActionAbility.cpp2와 editor-only KZGameplayAudioEditor.cpp1이다. Build06 exit0이다. 실제 Actor engine AudioComponent, mesh/engine notify ID tag로 loop 취소·clip 교체를 정리하고 finite tail은 자연 종료한다. source stop target cue 목록과 source fade, local/locked guardbreak 조건 및 원본 발소리230 속도 분기의 authored field를 추가했다. 새 Manager/FSM/MainAnimInstance 상태·Tick0이다. 피해/guard sounds는 실제 승인된 window result에서만 소비하고 DataAsset 값은 아직 연결 전이다.\n\nSource/runtime build 완료와 asset/timing/PIE 완료를 구분한다. 현재 NativeImport03 검증 → 표적 author/확정 hit/환경음 → 실 mixer/취소/tail/EndPlay/coverage 검사 → 최신 Source/module/hash receipt가 남았다. art 상태/원본 DSP adapter는 Art continuity를 따른다. 사용자 Rider/foreign editor는 제어하지 않았다. exact evidence/resume는 Saved/ImportReports/GameplayAudio_20261011/ResumeState02.json이다.\n'''
for rel,body in (('Docs/Art/ART_WORK_CONTINUITY.md',art),('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',eng)):
    with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(body)
print('Checkpoint',now)
