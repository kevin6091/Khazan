"""Bind the actual prepared/Main distinction to hashes, evidence and continuity."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
author=read(OUT/'AudioAuthoringPlan01.json')
bindings=read(OUT/'BindingAuthor02_Persistent/Bindings.json')
prepared=read(OUT/'BindingRepair03_Prepared/Bindings.json')
delivery=read(OUT/'BindingRepair03_Prepared/Delivery01.json')
saved=read(OUT/'SavedAudit06_PreparedBindings/SavedAudit.json')
native=read(OUT/'SavedAudit06_PreparedBindings/NativeSavedAudit.json')
audio=read(OUT/'AudioPIE07_PreparedProjectile/Driver.json')
environment=read(OUT/'EnvironmentPIE04_RHI/EnvironmentPIE.json')
regression=read(OUT/'RegressionPIE03_FreshSessions/Regression.json')
assert prepared['success'] and saved['success'] and native['success']
assert audio['status']==environment['status']==regression['status']=='passed'
assert saved['binding_source']==audio['binding_source']=='prepared'
assert read(OUT/'Build29_PreparedProjectileQA/Exit.json')['exit_code']==0
runtime=[
    'Animation/Notifies/KZAnimNotify_PlayAudio.h','Animation/Notifies/KZAnimNotify_PlayAudio.cpp',
    'Animation/Notifies/KZAnimNotifyState_PlayAudio.h','Animation/Notifies/KZAnimNotifyState_PlayAudio.cpp',
    'Ability/Combo/KZComboDefinitionData.h','Ability/Combo/KZComboActionAbility.cpp',
    'Ability/MonsterAbility/KZMonsterSkillObject.h','Ability/MonsterAbility/KZMonsterSkillObject.cpp',
    'Data/KZCharacterDefinitionData.h','Ability/PlayerAbility/KZBrutalAttackAbility.cpp']
dev=['Tests/KZGameplayAudioEditor.cpp','Tests/KZGameplayAudioPIETest.cpp']
source={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Source').rglob('*') if p.is_file()}
build_inputs=read(OUT/'Build29_PreparedProjectileQA/Launch.json')['source_inputs']
source_delta={k:{'verified_build':build_inputs.get(k),'current':source.get(k)} for k in source.keys()|build_inputs.keys() if source.get(k)!=build_inputs.get(k)}
assert all(k.startswith('Source/Khazan/Tests/') for k in source_delta),'Concurrent product source change requires a new build/validation'
assert all(source['Source/Khazan/'+p]==build_inputs['Source/Khazan/'+p] for p in runtime+dev)
assets={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in (ROOT/'Content/Audio/Original').rglob('*.uasset')}
audio_asset_count=len(assets)
for path in list(author['before_assets'])+[r['asset'] for r in bindings['combos']]+[r['asset'] for r in bindings['definitions']]:
    file=ROOT/'Content'/(path[6:]+'.uasset')
    assets[file.relative_to(ROOT).as_posix()]={'sha256':sha(file),'bytes':file.stat().st_size}
mapfile=ROOT/'Content/Maps/L_HeinMach_Environment.umap'
assets[mapfile.relative_to(ROOT).as_posix()]={'sha256':sha(mapfile),'bytes':mapfile.stat().st_size}
prepared_hashes={r['asset']:{'main_sha256':sha(ROOT/'Content'/(r['asset'][6:]+'.uasset')),
    'prepared_sha256':r['prepared_sha256'],'prepared':r['prepared'],'non_audio_fields_unchanged':r['non_audio_fields_unchanged']}
    for r in prepared['combos'] if any(r.get(k) for k in ('player_impacts','monster_guards','object_guards','projectiles'))}
assert len(prepared_hashes)==37
indexfile=ROOT/'Saved/Extracted/GameplayAudio_20261011/Index03/AudioPackageIndex.json'
index=read(indexfile);archives=Counter(r['archive'] for r in index)
decoded=read(OUT/'NativeDecodedManifest01.json')
evidence_files=[
    'Build29_PreparedProjectileQA/Launch.json','Build29_PreparedProjectileQA/Exit.json',
    'SavedAudit06_PreparedBindings/SavedAudit.json','SavedAudit06_PreparedBindings/NativeSavedAudit.json',
    'AudioPIE07_PreparedProjectile/Driver.json','EnvironmentPIE04_RHI/EnvironmentPIE.json',
    'RegressionPIE03_FreshSessions/Regression.json','BindingRepair03_Prepared/Bindings.json',
    'BindingRepair03_Prepared/Delivery01.json','NativeCuePlan01.json','AudioAuthoringPlan01.json',
    'NativeDecodedManifest01.json','ProjectileAudioPlan01.json','SourcePlayFadePlan01.json',
    'EnvironmentAuthoringPlan01.json','SpatialAudioPlan01.json','PlaybackPlan.json']
waves=[audio['output']]+audio['family_captures']+audio['projectile_captures']
waves += [r['output'] for r in regression['tests']]
waves += environment['captures']
wav_hashes={}
for r in waves:
    path=r.get('wave') or r.get('file')
    if path and Path(path).is_file():wav_hashes[str(Path(path).relative_to(ROOT))]=sha(path)
receipt={'time':now,'status':'PreparedVerified_MainBindingsLocked','complete':False,
    'original_request':'Both FModel chunk0/chunk1, current Player/monster6 actions and HeinMach ambience',
    'current_main_module':read(ROOT/'Binaries/Win64/UnrealEditor.modules')['Modules']['Khazan'],
    'source_inputs_match_verified_build':not source_delta,'audio_runtime_and_owned_qa_match_verified_build':True,
    'concurrent_foreign_editor_only_changes':source_delta,'runtime_files':runtime,'editor_only_files':dev,
    'new_runtime_classes':2,'new_runtime_files':4,'audio_asset_count':audio_asset_count,
    'asset_hash_count':len(assets),'assets':assets,'source_sha256':source,'prepared_bindings':prepared_hashes,
    'archives':dict(archives),'indexed_audio_files':len(index),'indexed_uassets':sum(r['path'].endswith('.uasset') for r in index),
    'archive_index_sha256':sha(indexfile),'decoded_waves':len(decoded),
    'decode_sample_rates_hz':sorted(set(r['sample_rate'] for r in decoded)),
    'source_pcm_clipped_samples_preserved':sum(r['clipped_samples'] for r in decoded),
    'saved_audit':saved,'audio_output':audio,'environment':environment,'regression_before_binding_repair':regression,
    'pending_main_bindings':delivery['pending'],'conflicts':delivery['conflicts'],
    'evidence_sha256':{p:sha(OUT/p) for p in evidence_files},'recording_sha256':wav_hashes,
    'preservation':'645 animation pose/curve GUID, RateScale, root flags, non-audio notify data; map protected9861, authored PP0, latest Snow40cm/Sky/Fog/UI/Fall/Brutal preserved',
    'native_adapters':[
        'Original Wwise bank gains/delays/weights/media/timestamps/maximum radii preserved; no additional lossy encode or source tail trim.',
        'Source linear play fades16; Log1/Exp1 two fade shapes approximated by sqrt(t)/t^2 with source duration.',
        'Native material mapping for body hits and original projectile launch callback; original executable caller is not serialized.',
        'Wwise random avoidRepeat1 uses UE without-replacement bag; source one-post/one-item sequence uses a finite random bag, not original global sequential order.',
        'Wwise DSP/global RTPCs/filters/above-surface layer and plugin tone output are not fully reproduced; silent timing branch retained where needed.',
        'Native attenuation source curve points97/max radii480; interpolation except constant is linear approximation.',
        'Temporary native mix gain0.5(-6.0206dB), concurrency SFX64/Ambient24/Fire8, reverb sends0.05..0.15.',
        'Temporary finite ambience delay12..28s, fire gain0.35/pitch0.99..1.01; source ambient actor repost code is unavailable.',
        'Original reverb aux identity/transforms/bounds preserved; native cave3.2s/boss2s/outside0.35s DSP profiles, wet0.30/0.08 and fade1.5s are temporary adapters.'
    ],
    'unverified':read(OUT/'PlaybackPlan.json')['missing_source'],
    'limits':'No sample-exact SDK/IR/complete audible game parity or Shipping performance claim. Concurrency settings are not a measured renderer voice count.',
    'backup_roots':['BeforeAudioNotifies','BeforeAudioBindings','BeforeAudioEnvironment','BeforeRuntime','BindingRepair03_Prepared/Before'],
    'resume':[
        'Save unsaved work and close the Rider-launched editor; never terminate or force-reload it automatically.',
        'Run apply_prepared_gameplay_audio_bindings.py BindingRepair03_Prepared Delivery02.json after file locks release.',
        'If a concurrent saved hash changed, re-author only audio binding fields from that latest Main package into a new prepared run; do not overwrite it with the old copy.',
        'Run fresh saved audit with KZ_AUDIO_BINDING_COPIES unset, then actual audio/projectile fixture and full CombatEffect/PlayerAttackCollision/GiantFall/Guard regression with current Main bindings.',
        'Bind exact Main hashes and passed output to FinalVerification.json, append dated Main completion to domain docs; do not re-extract/import/retime or restore old DLLs.'
    ]}
file=OUT/'PreparedVerification01.json';assert not file.exists()
file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
state={k:receipt[k] for k in ('time','status','complete','current_main_module','pending_main_bindings','conflicts','resume')}
state['verification']='PreparedVerification01.json; SavedAudit06_PreparedBindings and AudioPIE07_PreparedProjectile both passed; Main37 binding delivery remains pending'
state['user_editor']='Rider-launched Main PID19752 left untouched. Foreign private editors are outside this task.'
(OUT/'ResumeState05.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')

art=f'''

## {now} — 원작 사운드 재개: 저장 배열 누락 수정본 검증 / Main 잠금 대기

chunk0/chunk1의 실제 audio index {len(index)}파일/{receipt['indexed_uassets']} uasset를 확인했고 chunk1의 sound package2도 조사했다. 음원은 chunk0 소유다. source bank/event/game-sync/aux와 현재 source notify는 저장 metadata/report를 재사용하며 전체 리소스를 다시 조사하지 않았다. 한국어 KR 분기를 사용했다. Native decoded WAV1644는 원본48kHz/채널·gain·loop·끝음을 보존하는 PCM16이며 normalization/tail trim/추가 lossy encode0이다. 원본 PCM의 clipping4153 samples는 보존했으며 새 믹서 clipping과 구분한다. 현재 Audio/Original 에셋2147은 source cue480/wave1644+timing silence1/ambient wrapper10/native reverb6/기타 settings6이다.

645 sequence의 KZAudio point1958/state205 총2163 event는 saved import contract의 실제 dilation 여부와 원본 T_Original→T_Dilation piecewise linear table로 현재 baked clock에 한 번만 계산했다. 원본 CAkActionPlay TransitionTime(ms)/1000의18 fade는16 Linear와2 Log1/Exp1을 구분한다. 후자의 sqrt(t)/t² shape는 명시된 native 임시 근사다. 숫자/package/field/원시값·hash는 AudioAuthoringPlan01/PlaybackPlan/SourcePlayFadePlan01/NativeCuePlan01/SpatialAudioPlan01/ProjectileAudioPlan01에 보존했다. bank→media recipe는 엔진 최대32 child 기술 제약에 맞춰 그룹화했다. SoundWaveAssetPtr의 영구 참조4663개는 fresh process에서 검증했다.

중단점의 검증 중 이전 Python 배열 iteration으로 바꾼 구조체 사본이 배열에 재기록되지 않아37 ComboDefinition의 ImpactSound/GuardSound/ProjectileSound가 None으로 남은 것을 발견했다. index별 windows/nodes/pattern_objects 재대입으로 수정했고 모든 비오디오 export field를 전후 대조했다. 수정본은 BindingRepair03_Prepared/Prepared/Content에 있다. SavedAudit06_PreparedBindings가 player impact61/monster guard405/object guard4/projectile2 및 기존645 pose·curve GUID/RateScale/root/non-audio notify 보존을 새 프로세스로 확인했다. 새 AudioPIE07_PreparedProjectile은7 family+cancel8, original source loop 정리, 실제 Shoot/Impact의 두 비행음 녹음이 nonzero/clipping0으로 통과했다. 투사체의 source state Rock/Snow와 duration1.6503333/1.536s, source event maximum radius3000/5000cm를 보존했다. original SoundData.ProjectileRTPC80/60·SphereRadius2000의 원작 native 제어 의미와 global RTPC 완전 재현은 미확인이다.

Main HeinMach 환경음은 source actor39+기존 fire FX anchor95=134 ambient와 reverb13을 이미 저장했다. EnvironmentPIE04_RHI의 숲/절벽/동굴/보스룸/배치 fire7 실제 listener·reverb 출력은 passed/새 clipping0이며 기존9861 actor class/label/transform/PP0와 최신Snow40cm/Sky/Fog/UI를 보존했다. native reverb·총량 headroom·repetition·voice budget은 어시스턴트 임시값이다: SC_Original gain0.5(-6.0206dB), SFX64/Ambient24/Fire8, character wet send0.05–0.15, finite ambience12–28s, fire gain0.35/pitch0.99–1.01, cave3.2s/boss2s/outside0.35s/volume0.30·0.08/fade1.5s. 전체 native reverb parameter profile은 EnvironmentAuthor01/Environment.json과 author script에 있으며 원본 Wwise aux/room bounds와 구분한다. source attenuation point97의 normalized distance=distance_cm/max_radius, scaling2 gain=To+1을 사용하되 nonconstant curve의 native linear 보간은 근사다. source random avoidRepeat1의 native bag 및75 one-post/one-item sequence의 bag은 원본 전역 순서와 같다고 주장하지 않는다.

**Main37 수정 바인딩은 아직 미반영이다.** 새 Rider Main PID19752가 파일을 잠그고 있어 Delivery01의37행은 모두 Windows error32로 대기하며 saved hash 충돌0이다. 사용자 에디터 제어·저장·종료0이다. 수정본 검증을 Main 완료로 표현하지 않는다. source music fallback12는 자동 BGM으로 재생하지 않았고 미확인 parent source8/above-surface layer58/비사용 projectile switch3/native DSP·global RTPC·plugin tone output/Shipping 성능은 한계로 남긴다. 완전 SDK/IR/sample parity를 주장하지 않는다. 재개 근거는 PreparedVerification01.json과 ResumeState05.json이다.
'''
eng=f'''

## {now} — ARCH-89 사운드 저장 누락 정확 재개 / 준비본 검증 완료

신규 runtime는 stateless Audio Notify/NotifyState2 class/h·cpp4개이며 기존 ComboDefinition/ComboAction·CharacterDefinition/Brutal·MonsterSkillObject6 runtime 파일의 선택적 Sound/확정 HP·guard/launch·impact 수명만 확장했다. GT Actor/Mesh/engine notify instance 소유 AudioComponent와 engine AutoDestroy/StopWhenOwnerDestroyed를 재사용한다. finite tail은 자연 종료하며 loop/explicit stop만 자기 occurrence에서 정리한다. 새 Manager/Subsystem/Tick/gameplay 상태 사본0이다. 기존 ARCH-86 Fall/paired Brutal·ARCH-87/88 HUD/Monster repair·latest Source를 보존했다.

중단 지점 후 fresh binding readback에서37 DataAsset의 window/object audio 참조가 None임을 발견했다. 원인은 Unreal Python 배열 iteration의 구조체 사본을 바꾼 뒤 windows[i]/nodes[i]/objects[i]에 재대입하지 않은 것이다. author helper를 수정하고 최신 Main에서 비오디오 field 동일성을 검사한 prepared package를 저장했다. SaveBindingCopy/MountBindingCopies는 기존 editor-only 도구 파일의 표적 복사·새 process 검사 기능이며 Shipping runtime 책임을 추가하지 않는다. Build29_PreparedProjectileQA/current UnrealEditor-Khazan-2026101303.dll은 exit0이며 제품 runtime 및 자체 editor/QA Source hash가 build input과 동일하다. 다른 작업의 DEV 검사2파일 후속 변경은 그대로 보존하고 PreparedVerification01의 concurrent_foreign_editor_only_changes에 분리했다. test에서 즉시 Impact로 Destroy되는 Apes weak actor를 다음 phase에서 다시 dereference하지 않도록 IsValid로 검사했다.

SavedAudit06_PreparedBindings/AudioPIE07_PreparedProjectile은 fresh prepared37의 impact61/guard405/object guard4/projectile2 및 실제7 family/8 cancel sample, loop cleanup, 원본 cue를 실제 Shoot에서 재생하고 Impact에서 종료하는2 녹음이 passed/nonzero/clipping0이다. 이 검사는 prepared 바인딩을 명시적으로 mount한 DEV fixture이며 Main 바인딩 완료가 아니다. 기존 Main Animation/Body7/HeinMach source 환경음은 실제 saved/출력 검증됐다. prior CombatEffect actual18+5 paired/natural hit Success와 RegressionPIE03의 실제 PlayerAttackCollision/GiantFall/Guard Success/출력도 보존하되 새37 바인딩 반영 전 회귀임을 구분한다.

남은 외부 조건은 Rider Main PID19752의 파일 잠금이다. owned author 종료 후 hash CAS 교체도37개 모두 Error32로 실패했고 conflict0이다. PreparedVerification01.json complete=false/PreparedVerified_MainBindingsLocked, ResumeState05.json에 준비본 SHA/현재 Main SHA/증거/재개 절차를 저장했다. 기존 사용자 editor/debugger/foreign private editor는 조작하지 않았다. 필요 질문은 Windows 파일 잠금 해제를 위한 저장 후 editor 종료이며 자동 승인 거절이나 skill 승인 규칙 때문이 아니다.

정확한 재개: 미저장 작업을 사용자가 저장하고 Rider editor를 닫은 뒤 `apply_prepared_gameplay_audio_bindings.py BindingRepair03_Prepared Delivery02.json`을 실행한다. SHA가 달라진 package는 과거 준비본으로 덮어쓰지 말고 최신 Main에서 audio field만 새 prepared run으로 재작성한다. KZ_AUDIO_BINDING_COPIES를 해제한 fresh Main saved audit→Audio PIE→전체 CombatEffect/PlayerAttackCollision/GiantFall/Guard mixer 회귀 후 Main hash/loaded module과 실제 출력을 FinalVerification.json에 결속하고 날짜별 완료를 추가한다. 이미 성공한 전체 audio extraction/import/animation retime/환경 author와 과거 private Source·DLL 복원은 반복하지 않는다.
'''
for rel,text in [('Docs/Art/ART_WORK_CONTINUITY.md',art),('Docs/Art/ART_KNOWLEDGE_INDEX.md',art),
                 ('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',eng),('Docs/Engineering/BUILD_RUNTIME_DIAGNOSTICS.md',eng)]:
    with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(text)
artstate=f'''\n\n## {now} — 원작 사운드 Main 에셋·출력 및 수정 바인딩 준비본 검증\n\nAudio/Original2147/source wave1644·cue480/645 sequence2163 event/HeinMach134 ambient·13 reverb는 Main 저장·fresh 검증됐다. 전체 원본 chunk0/chunk1 index를 재사용했다. 마지막37 ComboDefinition 배열 참조 누락을 수정한 준비본은 fresh saved/실제 flight 포함 audio PIE에서 검증됐지만 Rider editor의 Windows error32로 Main 교체 대기다. 완료로 확대하지 않는다. 원본/TEMP·Wwise DSP 한계/검증과 exact resume는 ART_WORK_CONTINUITY 마지막 사운드 절 및 Saved/ImportReports/GameplayAudio_20261011/{{PreparedVerification01,ResumeState05}}.json을 따른다. 기존PP0/Sky/Fog/Snow40cm/UI/원본 기록을 유지했다.\n'''
engstate=f'''\n\n## {now} — ARCH-89 사운드 runtime build·준비본 검증 / Main37 잠금\n\nBuild29/current alias2026101303는 성공했고 제품 runtime 및 자체 audio editor/QA는 그 build input과 동일하다. 이후 다른 작업의 DEV2 변경은 보존하고 전체 현재 Source 일치와 구분한다. Notify2 class/새 runtime4 및 기존 owner6파일의 작은 확장으로 타이밍·확정 피해/guard·비행음·cancel/EndPlay를 연결했다. 실제 family/cancel/loop/flight 및 기존 gameplay 회귀 출력은 검증됐다. Python 배열 사본 재기록 누락의37 asset 수정본은 prepared 검증 완료·Main 잠금 대기이며 complete=false다. 상세 계약·현재/원작 미확인 범위와 exact resume는 Engineering continuity 마지막 ARCH-89 및 ResumeState05/PreparedVerification01을 따른다. 사용자/foreign editor 제어0, 무관한 Source/feature rollback0이다.\n'''
for rel,text in [('Docs/Art/ART_PROJECT_STATE.md',artstate),('Docs/Engineering/ENGINEERING_PROJECT_STATE.md',engstate),
                 ('Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md',engstate),('Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md',engstate)]:
    with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(text)
animation=f'''\n\n## {now} — 사운드 전용 Notify 실제 저작·검증\n\nMain645 sequence의 전용KZAudio track에 point1958/state205를 추가했다. 기존 pose·curve model GUID/RateScale/root flag·non-audio notify/Player Start 제외·Stop/Turn/Foot Placement 계약은 fresh native 저장 검사에서 동일했다. 원본 raw clock은 saved import dilation contract/표 T_Original→T_Dilation에 따라 한 번만 변환했으며3 legacy clip은 기존 saved frame-clock 배율을 사용했다. 애니메이션 pose 재임포트·rate/root 재작성0이다. SoundSource·raw/timing 계산/engine occurrence cleanup은 AudioAuthoringPlan01/PlaybackPlan과 Engineering ARCH-89를 따른다. 현재37 hit/guard/projectile 바인딩은 별개 prepared 수정본으로 Main 파일 잠금 대기이며 완료가 아니다.\n'''
with (ROOT/'Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md').open('a',encoding='utf-8') as f:f.write(animation)
router=f'''\n\n## {now} — Player/monster6/HeinMach 사운드 정확 재개 조회\n\n사운드 추출·임포트와 행동별 재생은 Mixed다. Architecture 최신ARCH-89→Migration→Engineering/Art continuity의 최신 사운드 절→Saved/ImportReports/GameplayAudio_20261011/ResumeState05.json 및 PreparedVerification01.json을 읽는다. chunk0/chunk1/원본 metadata·bank/media/timing의 재사용 경로는 Art knowledge index에 있다. Main cue/wave/2163 notify·HeinMach 환경음은 저장됐고 새37 audio-array binding 수정본은 fresh/실제 PIE 검증 완료지만 Rider Main 파일 잠금으로 반영 대기다. 준비본을 Main 완료로 읽거나 전체 re-extract/import/retime/옛 DLL 전달을 반복하지 않는다.\n'''
with (ROOT/'0_DOCUMENT_ROUTER.md').open('a',encoding='utf-8') as f:f.write(router)
print(json.dumps({'time':now,'status':receipt['status'],'audio_assets':audio_asset_count,'total_hashes':len(assets),'pending':len(delivery['pending']),'complete':False}),flush=True)
