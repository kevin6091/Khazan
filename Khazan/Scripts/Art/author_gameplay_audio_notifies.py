"""Add only the KZAudio track, preserve existing animation/visual/gameplay data."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib
import json
import os
import shutil
import traceback
import unreal as u
ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plan=read(os.environ.get('KZ_AUDIO_AUTHOR_PLAN') or OUT/'AudioAuthoringPlan01.json');lib=u.EditorAssetLibrary;al=u.AnimationLibrary
report={'success':False,'assets':[],'errors':[]};by_asset=defaultdict(list)
for e in plan['events']:by_asset[e['asset']].append(e)
backup=OUT/'BeforeAudioNotifies';backup.mkdir(exist_ok=True)
try:
    for asset,events in by_asset.items():
        file=Path(plan['before_assets'][asset]['file']);prior=plan['before_assets'][asset]['sha256']
        saved=backup/file.relative_to(ROOT)
        if not saved.exists():
            assert hashlib.sha256(file.read_bytes()).hexdigest()==prior,'Concurrent change: '+asset
            saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,saved)
        obj=lib.load_asset(asset);assert obj,asset
        existing=list(al.get_animation_notify_events(obj))
        oldnon=[n.export_text() for n in existing if not str(n.get_editor_property('notify_name')).startswith('KZA_')]
        # Reruns replace only the dedicated source-audio track, never existing VFX
        # tracks, gameplay notify states, pose/curves/root settings/sections.
        tracks=[str(x) for x in al.get_animation_notify_track_names(obj)]
        if 'KZAudio' in tracks:al.remove_animation_notify_events_by_track(obj,'KZAudio')
        else:al.add_animation_notify_track(obj,'KZAudio',u.LinearColor(0.18,0.6,0.85,1.))
        made=[]
        for e in sorted(events,key=lambda e:(e['start'],e['event_id'])):
            sound=lib.load_asset(e['cue']) if e['cue'] else None
            assert sound or e['stop_sounds'],(asset,e['cue'])
            if e['state']:
                state=u.new_object(u.KZAnimNotifyState_PlayAudio,outer=obj,name=e['event_id'])
                playback=u.new_object(u.KZAnimNotify_PlayAudio,outer=state,name='Playback')
                state.set_editor_property('playback',playback);state.set_editor_property('end_sound',lib.load_asset(e['end_cue']) if e['end_cue'] else None)
                state.set_editor_property('stop_at_end',e['stop_at_end']);state.set_editor_property('fade_out_seconds',e['fade_seconds'])
                al.add_animation_notify_state_event_object(obj,e['start'],e['duration'],state,'KZAudio')
            else:
                playback=u.new_object(u.KZAnimNotify_PlayAudio,outer=obj,name=e['event_id'])
                al.add_animation_notify_event_object(obj,e['start'],playback,'KZAudio')
            for name,value in (('sound',sound),('attach_name',e['anchor']),('follow',e['follow']),('ground_material_switch',e['ground_switch']),
                ('footstep_speed_threshold',230. if e['event_package'].endswith('/Play_PLYR_Footsteps') else 0.),
                ('only_for_local_or_locked_target',e['only_local_or_locked']),('stop_sounds',[lib.load_asset(p) for p in e['stop_sounds']]),
                ('stop_fade_seconds',e['stop_fade_seconds']),('source_package',e['source']['source_package']),('source_field',e['source']['field'])):
                playback.set_editor_property(name,value)
            made.append({'event_id':e['event_id'],'start':e['start'],'duration':e['duration'] if e['state'] else 0.,'cue':e['cue'],'state':e['state']})
        after=list(al.get_animation_notify_events(obj))
        # Native UAnimNotify names differ from object names; compare tracks and
        # pre-existing concrete notify object identity/serialized data.
        oldobjects={n.get_editor_property('notify') or n.get_editor_property('notify_state_class') for n in existing
                    if not (n.get_editor_property('notify') or n.get_editor_property('notify_state_class')) or
                    not isinstance(n.get_editor_property('notify') or n.get_editor_property('notify_state_class'),(u.KZAnimNotify_PlayAudio,u.KZAnimNotifyState_PlayAudio))}
        afterobjects={n.get_editor_property('notify') or n.get_editor_property('notify_state_class') for n in after}
        assert oldobjects<=afterobjects,'Existing non-audio notifies lost: '+asset
        lib.set_metadata_tag(obj,'OriginalAudioTiming','Source LinkValue/EndLink + source segments/rates/dilation; current legacy3 frame clock documented in plan')
        lib.set_metadata_tag(obj,'OriginalAudioAuthorPlan','GameplayAudio_20261011/AudioAuthoringPlan01.json')
        assert lib.save_loaded_asset(obj,only_if_is_dirty=False),asset
        report['assets'].append({'asset':asset,'before_sha256':prior,'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'events':made,'existing_non_audio_preserved':True})
        if len(report['assets'])%40==0:
            (RUN/'NotifyProgress.json').write_text(json.dumps({'done':len(report['assets']),'total':len(by_asset)}),encoding='utf-8');u.log('KZAudio Authored sequences '+str(len(report['assets'])))
    report['success']=True
except Exception:
    report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Notifies.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('KZAudio notify author failed')
