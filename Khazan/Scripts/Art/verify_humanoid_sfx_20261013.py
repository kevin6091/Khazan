"""Fresh native graph/pose preservation and scoped saved audio contracts."""
from pathlib import Path
from collections import defaultdict
import json
import os
import re
import traceback
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Metadata/HumanoidSFX_20261013';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
lib=u.EditorAssetLibrary;al=u.AnimationLibrary
plan=read(OUT/'AudioAuthoringPlan01.json');inventory=read(OUT/'Inventory02/Inventory.json')
report={'success':False,'package_saves':0,'events':0,'sequences':0,'windows':0,'abilities':0,'errors':[]}
by=defaultdict(list)
for e in plan['events']:by[e['asset']].append(e)
for e in plan.get('callback_owned_events',[]):by.setdefault(e['asset'],[])

try:
    cues={e['cue'] for e in plan['events'] if e['cue']}
    cues.update(e['end_cue'] for e in plan['events'] if e['end_cue'])
    cues.update(p for e in plan['events'] for p in e['stop_sounds'])
    cues.update(c['asset'] for c in read(OUT/'NativeCuePlan01.json')['cues'])
    cues.add('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_JustGuard_Suc')
    native_plan={'cues':sorted(cues),'sequences':sorted(by),'backup_content':str(OUT/'Before/Content'),
        'output':str(RUN/'NativeSavedAudit.json')}
    file=RUN/'NativeSavedAuditPlan.json';file.write_text(json.dumps(native_plan),encoding='utf-8')
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.AuditSaved "'+str(file)+'"')
    native=read(RUN/'NativeSavedAudit.json');assert native['success'],native.get('errors')
    for path,expected in by.items():
        seq=lib.load_asset(path);assert seq
        actual={}
        for event in al.get_animation_notify_events(seq):
            obj=event.get_editor_property('notify') or event.get_editor_property('notify_state_class')
            if isinstance(obj,(u.KZAnimNotify_PlayAudio,u.KZAnimNotifyState_PlayAudio)):actual[obj.get_name()]=(obj,event)
        if set(actual)!={e['event_id'] for e in expected}:
            report['occurrence_mismatch']={'asset':path,'missing':sorted({e['event_id'] for e in expected}-set(actual)),
                'extra':sorted(set(actual)-{e['event_id'] for e in expected})}
            raise AssertionError(('Audio occurrence set',report['occurrence_mismatch']))
        for e in expected:
            obj,event=actual[e['event_id']];state=isinstance(obj,u.KZAnimNotifyState_PlayAudio)
            assert state==e['state'],e['event_id']
            play=obj.get_editor_property('playback') if state else obj
            sound=play.get_editor_property('sound')
            assert (sound.get_path_name().split('.')[0] if sound else '')==e['cue'],e['event_id']
            start=float(re.findall(r'LinkValue=([-+0-9.eE]+)',event.export_text())[-1])
            assert abs(start-e['start'])<.001,(path,e['event_id'],start,e['start'])
            assert abs(play.get_editor_property('volume_multiplier')-e['volume_multiplier'])<.0001,e['event_id']
            assert play.get_editor_property('preserve_finite_tail_on_owner_destroyed'),e['event_id']
            assert {x.get_path_name().split('.')[0] for x in play.get_editor_property('stop_sounds')}==set(e['stop_sounds']),e['event_id']
            assert abs(play.get_editor_property('stop_fade_seconds')-e['stop_fade_seconds'])<.0001,e['event_id']
            if state:
                duration=float(re.search(r'Duration=([-+0-9.eE]+)',event.export_text()).group(1))
                assert abs(duration-e['duration'])<.001,e['event_id']
                assert obj.get_editor_property('stop_at_end')==e['stop_at_end'],e['event_id']
                assert abs(obj.get_editor_property('fade_out_seconds')-e['fade_seconds'])<.0001,e['event_id']
            report['events']+=1
        report['sequences']+=1
    for row in inventory['combos']:
        if not any(n['windows'] for n in row['nodes']):continue
        obj=lib.load_asset(row['asset'])
        for n in obj.get_editor_property('nodes'):
            for w in n.get_editor_property('attack_windows'):
                guard=w.get_editor_property('guard_sound');assert guard,row['asset']
                expected='SC_efx_empireswordshield_s_guard' if row['family']=='Player' else 'SC_Play_PLYR_DualAxeSword_Guard_Suc'
                assert guard.get_name()==expected,row['asset']
                if row['family']=='Player':assert w.get_editor_property('impact_sound').get_name()=='SC_efx_pc_dualaxesword_com_impact',row['asset']
                report['windows']+=1
        assert not obj.get_editor_property('pattern_objects'),'Unexpected humanoid skill-object audio consumer: '+row['asset']
    for row in inventory['ability_defaults']:
        if '/Player/Dodge/' not in row['class']:continue
        cdo=u.get_default_object(lib.load_blueprint_class(row['class'].split('.')[0]))
        assert cdo.get_editor_property('success_sound').get_name()=='SC_efx_pc_common_justdodge',row['class']
        report['abilities']+=1
    for row in inventory['definitions']:
        obj=lib.load_asset(row['asset']);actual=obj.get_editor_property('hit_reactions').get_editor_property('impact_sound')
        assert actual and actual.get_path_name().split('.')[0]==row['impact']['asset'],row['asset']
    if os.environ.get('KZ_AUDIO_REQUIRE_FINAL_MIX')=='1':
        cue=lib.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_JustGuard_Suc')
        assert cue.get_editor_property('volume_multiplier')==.5,'Measured parry headroom trim not saved'
    report['cues']=len(cues);report['success']=True
except Exception:report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'SavedAudit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['success'],report['errors']
