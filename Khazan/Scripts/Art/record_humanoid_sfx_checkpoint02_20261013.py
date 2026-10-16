from pathlib import Path
import datetime
import json

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/HumanoidSFX_20261013'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
plan=read(OUT/'AudioAuthoringPlan01.json');stage=read(OUT/'Stage01.json')
state={'time':now,'scope':plan['scope'],'excluded':['Yetuga','ApesStoneHandElite'],
    'status':'New resources imported to Main; scoped audio prepared in fresh isolated current project. Saved audit and actual mixer QA in progress; Main delivery remains.',
    'evidence':'Inventory02 / PlaybackPlan01 / AudioAuthoringPlan01 / NativeCuePlan01 / NativeDecodedImport01 / Stage01 / AuthorStage02 / RuntimeSamples01 / Coverage01',
    'counts':{'source_inventory_animations':936,'source_inventory_combos':58,'source_inventory_definitions':5,
        'audio_occurrences':len(plan['events']),'audio_sequences':524,'cleared_callback_only_sequences':3,'combo_assets':35,'dodge_blueprints':8,
        'new_original_cues':51,'native_wave_recipes':262,'mixer_fixtures':78,'isolated_stage_assets':len(stage['isolated'])},
    'project':stage['project'],'failures_preserved':['NativeImport03 relative path failure, fixed with absolute environment paths.',
        'SpatialAuthor02/Author02 Main Win32 error32 caused by independent background render file locks.',
        'SavedStage01/02 found duplicate same-foot audio notify surviving outside KZAudio.',
        'AuthorStage03_Contacts protected Python Notifies array; existing DEV audio editor gets narrow class-only clear command.'],
    'main_saved':'Author01 500 sequence/35 combo;51 new source cues/waves and spatial settings saved. Final new plan remains prepared until verified delivery.',
    'runtime_source_files':['KZAnimNotify_PlayAudio.h','KZAnimNotify_PlayAudio.cpp','KZAnimNotifyState_PlayAudio.cpp'],
    'numeric_policy':'Source bank gains/randomization/media endings/attenuation curves preserved. Explicit TEMP voice.85/foot.9/weapon1, stop minimum.08s, callback adapters at first actual pose; same-frame same-contact/voice dedup.',
    'next':['Finish Build_HumanoidSFX04 in old report root; copy only its new DLL/modules to the isolated project, never old source back to Main.',
        'AuthorStage04 class-only clear for WeakAttack03/05, fresh SavedStage04 all1682/527/35/8 preservation checks.',
        'Run owned isolated --pie --nullrhi --audio with absolute KZ_AUDIO_SAMPLE_PLAN RuntimeSamples01.json;78 actual clips, cue coverage, loop/cancel and owner-destruction tail.',
        'Run actual humanoid melee/Guard/Parry/Dodge interaction regressions and compare actual PCM peaks/tails. No asset/map saves in these fixtures.',
        'Only after verification: per-asset Stage01 baseline-SHA guard and atomic delivery, retry locked targets without touching independent editors. Fresh Main saved/audio validation; append domain completion and FinalVerification.']}
(OUT/'ResumeState02.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
art=f'''\n\n## {now} — 인간형·Player SFX 후속: 원본 추가 임포트, 현재 사본 검증 중\n\n원작 상위 Composite를 포함한 현재 계획은1682 sound/control occurrence·524 audio sequence다. 승인된 Guard 성공은 기존 attack window의 GuardSound가 한 번 재생하며 Suc pose의 중복3은 제거한다. 원작 sound event 추가51cue/262 leaf recipe를 표적 bank/media 추출로 임포트했고 fallback recipe0이다. 신규 Source raw 총196+6+82+45 파일, 기존 정확 hash/trim media를 재사용한다. Doom/Charge 후반·회전 마무리·회피8방·무기 입출납·약한 피격/착지까지 포함하며 Yetuga/Apes/map은 재저장 대상이 아니다. 원작 기본 idle/공중 hold에 임의 반복음을 넣지 않는다. 원작 callback 시각 미직렬화72 adapter는 원본 media를 쓰되 TEMP first-pose dispatch로 표시했다. Voice .85/foot .9/weapon1, source stop 최소.08초, native reverb send 및 Wwise DSP 차이는 TEMP이며 완전 원작 음향 일치로 기록하지 않는다.\n\nMain Author01의500seq/35combo와51새 cue·추가 media·거리 설정은 저장했다. 최종 계획의 현재 사본은 신규 Khazan_HumanoidSFXWork_20261013/Khazan이며 현재 Main을 새로 읽어570수정 대상만 독립 파일로 복사했다. Old37 prepared payload는 재사용하지 않았다. Main의 독립 background RHI들이 Win32 error32 잠금을 보유해 두 저장 실패는 보존하고 사본 검증으로 계속한다. SavedStage01/02는 이전 같은 발의 중복 audio notify가 KZAudio 밖에 남아 있는 문제를 실제로 검출했다. protected Python Notifies setter는 실패했으며 native DEV editor의 클래스2만 제거하는 작은 authoring command로 수정한다. 아직 Main 최종 완료/믹서 검증 완료가 아니다. 정확한 재개는 ResumeState02.json이며78개 actual-mixer fixture/끝음 actor destroy/loop/cancel과 실제 hit/Guard/Parry/Dodge를 수행한 뒤 baseline hash 보호로 선택 전달한다.\n'''
eng=f'''\n\n## {now} — ARCH-89 SFX 실행·검증 후속, Main 완료 전\n\n기존 Notify의 optional volume/finite-owner-tail3 source 변경과 기존 approved hit/Guard/Dodge owner를 유지한다. 기존 DEV Audio PIE에 환경 sample plan·범위 밖 giant projectile 제외·모든 예상 cue 관측·AT 실제 owner destroy 후 finite ActiveSound 유지와 PCM tail 검사를 추가했다. Dodge 성공 QA는 합성음 파일명 하드코딩 대신 실제 authored SuccessSound property를 관측한다. protected Python Notifies 수정 실패 때문에 기존 DEV Audio Editor에 class2-only clear/no-save command를 추가했다. 새 runtime class/file/component/manager/tick0이며 Source3 외의 실행 구조 확장은 없다. 현재 Source와 Root/FPS/physics/VictimFront·Slash/Parry·Player 피격 VFX 제거를 보존하고 Main 최신 파일에서 audio field만 수정한다.\n\n사본에서527sequence/35combo/8Dodge BP를 실제 저장했고 fresh audit는 기존 중복 contact 문제를 발견하여 후속 재검증 중이다. Main의 독립 RHI 프로세스 파일 잠금에는 제어/종료를 하지 않았다. 원작으로 표시한 bank/clock과 TEMP mix/callback adapter, 준비/저장/실제 QA/Main 완료를 구분한다. 정확한 Build04 이후 재개와 남은 절차는 Metadata/HumanoidSFX_20261013/ResumeState02.json에 있다. 아직 완료가 아니다.\n'''
for rel,body in [('Docs/Art/ART_WORK_CONTINUITY.md',art),('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',eng)]:
    with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(body)
print('Checkpoint02',now)
