"""Only current Player/humanoid audio tracks and approved-hit audio fields."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import os
import re
import shutil
import traceback
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Metadata/HumanoidSFX_20261013';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
lib=u.EditorAssetLibrary;al=u.AnimationLibrary
plan=read(OUT/'AudioAuthoringPlan01.json');inventory=read(OUT/'Inventory02/Inventory.json')
report={'success':False,'animations':[],'combos':[],'abilities':[],'errors':[]}
by=defaultdict(list)
for e in plan['events']:by[e['asset']].append(e)
for e in plan.get('callback_owned_events',[]):by.setdefault(e['asset'],[])
selected=set(os.environ.get('KZ_AUDIO_AUTHOR_ASSETS','').split(',')) if os.environ.get('KZ_AUDIO_AUTHOR_ASSETS') else None

def preserve(path):
    file=ROOT/'Content'/(path[6:]+'.uasset');dst=OUT/'Before/Content'/file.relative_to(ROOT/'Content')
    if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dst)
    return hashlib.sha256(file.read_bytes()).hexdigest()

def audio(e):
    obj=e.get_editor_property('notify') or e.get_editor_property('notify_state_class')
    return isinstance(obj,(u.KZAnimNotify_PlayAudio,u.KZAnimNotifyState_PlayAudio))

def non_audio(text):
    return re.sub(r',?(ImpactSound|GuardSound|ProjectileSound|ProjectileStopFadeSeconds)=[^,)]*','',text)

try:
    for path,events in by.items():
        if selected and path not in selected:continue
        assert not any(t in path for t in ('Yetuga','ApesStoneHand'))
        before=preserve(path);seq=lib.load_asset(path);assert seq
        current=list(al.get_animation_notify_events(seq))
        non=[e.export_text() for e in current if not audio(e)]
        # Earlier duplicate contacts were moved off KZAudio by cache refresh.
        # Remove only these two audio classes across tracks; retain all other
        # notify objects/fields/clocks, including original VFX and gameplay.
        u.SystemLibrary.execute_console_command(None,'KZ.Audio.ClearNotifyClasses "'+path+'"')
        tracks=[str(x) for x in al.get_animation_notify_track_names(seq)]
        if 'KZAudio' in tracks:al.remove_animation_notify_events_by_track(seq,'KZAudio')
        else:al.add_animation_notify_track(seq,'KZAudio',u.LinearColor(.18,.6,.85,1.))
        for e in sorted(events,key=lambda e:(e['start'],e['event_id'])):
            sound=lib.load_asset(e['cue']) if e['cue'] else None
            assert sound or e['stop_sounds'],(path,e['cue'])
            if e['state']:
                notify=u.new_object(u.KZAnimNotifyState_PlayAudio,outer=seq,name=e['event_id']);play=u.new_object(u.KZAnimNotify_PlayAudio,outer=notify,name='Playback')
                notify.set_editor_property('playback',play);notify.set_editor_property('end_sound',lib.load_asset(e['end_cue']) if e['end_cue'] else None)
                notify.set_editor_property('stop_at_end',e['stop_at_end']);notify.set_editor_property('fade_out_seconds',e['fade_seconds'])
                al.add_animation_notify_state_event_object(seq,e['start'],e['duration'],notify,'KZAudio')
            else:
                play=u.new_object(u.KZAnimNotify_PlayAudio,outer=seq,name=e['event_id']);al.add_animation_notify_event_object(seq,e['start'],play,'KZAudio')
            for key,value in [('sound',sound),('volume_multiplier',e['volume_multiplier']),('preserve_finite_tail_on_owner_destroyed',True),
                ('attach_name',e['anchor']),('follow',e['follow']),('ground_material_switch',e['ground_switch']),
                ('footstep_speed_threshold',230. if e['event_package'].endswith('/Play_PLYR_Footsteps') else 0.),
                ('only_for_local_or_locked_target',e['only_local_or_locked']),('stop_sounds',[lib.load_asset(p) for p in e['stop_sounds']]),
                ('stop_fade_seconds',e['stop_fade_seconds']),('source_package',e['source']['source_package']),('source_field',e['source']['field'])]:play.set_editor_property(key,value)
        after=list(al.get_animation_notify_events(seq))
        assert non==[e.export_text() for e in after if not audio(e)],'Non-audio changed: '+path
        assert lib.save_loaded_asset(seq,only_if_is_dirty=False),path
        report['animations'].append({'asset':path,'events':len(events),'before_sha256':before,'non_audio_unchanged':True})
    impact=lib.load_asset('/Game/Audio/Original/Events/SC_efx_pc_dualaxesword_com_impact')
    playerguard=lib.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_Guard_Suc')
    shieldguard=lib.load_asset('/Game/Audio/Original/Events/SC_efx_empireswordshield_s_guard')
    assert impact and playerguard and shieldguard
    for row in inventory['combos']:
        if selected:continue
        if not any(n['windows'] for n in row['nodes']):continue
        path=row['asset'];before=preserve(path);obj=lib.load_asset(path);nodes=obj.get_editor_property('nodes')
        before_non=[non_audio(n.export_text()) for n in nodes];count=0
        for ni,n in enumerate(nodes):
            windows=n.get_editor_property('attack_windows')
            for wi,w in enumerate(windows):
                if row['family']=='Player':
                    w.set_editor_property('impact_sound',impact)
                    # Current player attacks can be system-blocked by SwordShield.
                    # Its body/weapon event is different from player guard success.
                    w.set_editor_property('guard_sound',shieldguard)
                else:w.set_editor_property('guard_sound',playerguard)
                windows[wi]=w;count+=1
            n.set_editor_property('attack_windows',windows);nodes[ni]=n
        assert before_non==[non_audio(n.export_text()) for n in nodes]
        obj.set_editor_property('nodes',nodes);assert lib.save_loaded_asset(obj,only_if_is_dirty=False),path
        report['combos'].append({'asset':path,'windows':count,'before_sha256':before,'non_audio_unchanged':True})
    success=lib.load_asset('/Game/Audio/Original/Events/SC_efx_pc_common_justdodge');assert success
    for row in inventory['ability_defaults']:
        if selected:continue
        if '/Player/Dodge/' not in row['class']:continue
        path=row['class'].split('.')[0];before=preserve(path)
        bp=lib.load_asset(path);cls=lib.load_blueprint_class(path);cdo=u.get_default_object(cls)
        # Reuse the approved-success owner; never play this cue on every dodge.
        cdo.set_editor_property('success_sound',success)
        assert lib.save_loaded_asset(bp,only_if_is_dirty=False),path
        report['abilities'].append({'asset':path,'before_sha256':before,'success_sound':success.get_path_name(),
            'dispatch':'Existing TryAvoidHit approved success, once per execution'})
    report['success']=True
except Exception:report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Author.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('Humanoid scoped SFX author failed')
