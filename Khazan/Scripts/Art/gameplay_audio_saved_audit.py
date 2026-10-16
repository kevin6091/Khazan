"""Fresh-package closure/timing/settings audit; never saves assets."""
from pathlib import Path
import json
import os
import re
import traceback
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
RUN=Path(os.environ['KZ_AUDIO_OUTPUT']);lib=u.EditorAssetLibrary;al=u.AnimationLibrary
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
report={'success':False,'package_saves':0,'events':0,'errors':[]}
try:
    author=read(OUT/'AudioAuthoringPlan01.json')
    cues=[c['asset'] for c in read(OUT/'NativeCuePlan01.json')['cues']]
    cues += [w['target'] for w in read(OUT/'BindingAuthor02_Persistent/Bindings.json')['wrappers']]
    plan={'cues':cues,'sequences':list(author['before_assets']),
          'backup_content':str(OUT/'BeforeAudioNotifies/Content'),
          'output':str(RUN/'NativeSavedAudit.json')}
    file=RUN/'NativeSavedAuditPlan.json';file.write_text(json.dumps(plan),encoding='utf-8')
    reuse=os.environ.get('KZ_AUDIO_NATIVE_AUDIT')
    if not reuse:u.SystemLibrary.execute_console_command(None,'KZ.Audio.AuditSaved "'+str(file)+'"')
    native=read(reuse or RUN/'NativeSavedAudit.json')
    report['native_evidence']=reuse or str(RUN/'NativeSavedAudit.json')
    assert native['success'],'Persistent graph/animation preservation audit failed'
    by_asset={}
    for e in author['events']:by_asset.setdefault(e['asset'],[]).append(e)
    for asset,expected in by_asset.items():
        sequence=lib.load_asset(asset)
        actual={}
        for event in al.get_animation_notify_events(sequence):
            obj=event.get_editor_property('notify') or event.get_editor_property('notify_state_class')
            if isinstance(obj,(u.KZAnimNotify_PlayAudio,u.KZAnimNotifyState_PlayAudio)):actual[obj.get_name()]=(obj,event)
        assert set(actual)=={e['event_id'] for e in expected},asset
        for e in expected:
            obj,event=actual[e['event_id']]
            is_state=isinstance(obj,u.KZAnimNotifyState_PlayAudio)
            playback=obj.get_editor_property('playback') if is_state else obj
            sound=playback.get_editor_property('sound')
            assert (sound.get_path_name().split('.')[0] if sound else '')==e['cue'],e['event_id']
            # AnimNotifyEvent's native GetTriggerTime is not Python exposed.
            # LinkValue is the authored absolute sequence clock; trigger offsets
            # are engine dispatch details, not the original authored timestamp.
            link=float(re.findall(r'LinkValue=([-+0-9.eE]+)',event.export_text())[-1])
            if abs(link-e['start']) >= 0.001:
                report['timing_mismatch']={'asset':asset,'event_id':e['event_id'],'expected':e['start'],'stored':link,'text':event.export_text()}
            assert abs(link-e['start']) < 0.001,(e['event_id'],asset,e['start'],link)
            if is_state:
                duration=float(re.search(r'Duration=([-+0-9.eE]+)',event.export_text()).group(1))
                assert abs(duration-e['duration']) < 0.001,e['event_id']
                assert obj.get_editor_property('stop_at_end')==e['stop_at_end'],e['event_id']
            report['events']+=1
    bindings=read(OUT/'BindingAuthor02_Persistent/Bindings.json')
    for r in bindings['definitions']:
        obj=lib.load_asset(r['asset']);sound=obj.get_editor_property('hit_reactions').get_editor_property('impact_sound')
        assert sound and sound.get_path_name()==r['sound'],r['asset']
    copies=os.environ.get('KZ_AUDIO_BINDING_COPIES')
    if copies:u.SystemLibrary.execute_console_command(None,'KZ.Audio.MountBindingCopies "'+copies+'"')
    report['binding_source']='prepared' if copies else 'main'
    report['attack_impacts']=report['attack_guards']=report['object_guards']=report['projectiles']=0
    projectiles={r['object_id']:r for r in read(OUT/'ProjectileAudioPlan01.json')}
    cue_map={r['event_package']:r['asset'] for r in read(OUT/'NativeCuePlan01.json')['cues']}
    impact='/Game/Audio/Original/Events/SC_efx_pc_dualaxesword_com_impact'
    guard='/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_Guard_Suc'
    for r in bindings['combos']:
        path=r['asset'];test_path=path.replace('/Game/','/KZAudioBindingStage/',1) if copies else path
        obj=u.load_object(None,test_path+'.'+test_path.rsplit('/',1)[-1]);assert obj,path
        player=path.startswith('/Game/Data/ComboCommand/DA_Player_') or '/Player/' in path
        count=0
        for n in obj.get_editor_property('nodes'):
            for w in n.get_editor_property('attack_windows'):
                sound=w.get_editor_property('impact_sound' if player else 'guard_sound')
                assert sound and sound.get_path_name().split('.')[0]==(impact if player else guard),path
                count+=1
                if player:report['attack_impacts']+=1
                else:report['attack_guards']+=1
        assert count==r['windows'],path
        for o in obj.get_editor_property('pattern_objects'):
            sound=o.get_editor_property('guard_sound')
            assert sound and sound.get_path_name().split('.')[0]==guard,path
            report['object_guards']+=1
            source=projectiles.get(str(o.get_editor_property('id')))
            if source:
                sound=o.get_editor_property('projectile_sound')
                assert sound and sound.get_path_name().split('.')[0]==cue_map[source['event']],path
                assert o.get_editor_property('projectile_stop_fade_seconds')==0.,path
                report['projectiles']+=1
    assert report['projectiles']==len(projectiles)
    report['combos']=len(bindings['combos'])
    report['sequences']=len(by_asset);report['cues']=len(cues);report['definitions']=len(bindings['definitions'])
    report['success']=True
except Exception:
    report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'SavedAudit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['success'],report['errors']
