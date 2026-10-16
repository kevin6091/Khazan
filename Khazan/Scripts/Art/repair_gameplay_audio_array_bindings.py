"""Commit copied UE Python array structs, preserving every non-audio field."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import traceback
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN'])
OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
lib=u.EditorAssetLibrary
report={'success':False,'combos':[],'pending':[],'errors':[]}

def non_audio(text):
    return re.sub(r',?(ImpactSound|GuardSound|ProjectileSound|ProjectileStopFadeSeconds)=[^,)]*','',text)

try:
    impact=lib.load_asset('/Game/Audio/Original/Events/SC_efx_pc_dualaxesword_com_impact')
    guard=lib.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_Guard_Suc')
    assert impact and guard
    projectiles={r['object_id']:r for r in read(OUT/'ProjectileAudioPlan01.json')}
    cues={r['event_package']:r for r in read(OUT/'NativeCuePlan01.json')['cues']}
    for row in read(OUT/'Bindings01/Bindings.json')['combos']:
        path=row['asset'];obj=lib.load_asset(path)
        nodes=obj.get_editor_property('nodes');objects=obj.get_editor_property('pattern_objects')
        if not objects and not any(n.get_editor_property('attack_windows') for n in nodes):continue
        before_nodes=[non_audio(n.export_text()) for n in nodes]
        before_objects=[non_audio(o.export_text()) for o in objects]
        player=path.startswith('/Game/Data/ComboCommand/DA_Player_') or '/Player/' in path
        hits=guards=flights=0
        for ni,n in enumerate(nodes):
            windows=n.get_editor_property('attack_windows')
            for wi,w in enumerate(windows):
                w.set_editor_property('impact_sound' if player else 'guard_sound',impact if player else guard)
                windows[wi]=w
                if player:hits+=1
                else:guards+=1
            n.set_editor_property('attack_windows',windows)
            nodes[ni]=n
        for oi,o in enumerate(objects):
            o.set_editor_property('guard_sound',guard)
            source=projectiles.get(str(o.get_editor_property('id')))
            if source:
                sound=lib.load_asset(cues[source['event']]['asset']);assert sound
                o.set_editor_property('projectile_sound',sound)
                o.set_editor_property('projectile_stop_fade_seconds',0.)
                flights+=1
            objects[oi]=o
        after_nodes=[non_audio(n.export_text()) for n in nodes]
        after_objects=[non_audio(o.export_text()) for o in objects]
        if before_nodes!=after_nodes or before_objects!=after_objects:
            (RUN/'UnexpectedNonAudioDiff.json').write_text(json.dumps({'asset':path,'before_nodes':before_nodes,
                'after_nodes':after_nodes,'before_objects':before_objects,'after_objects':after_objects},indent=2),encoding='utf-8')
        assert before_nodes==after_nodes
        assert before_objects==after_objects
        file=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        copy=RUN/'Before'/file.relative_to(ROOT);copy.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,copy)
        before_sha=hashlib.sha256(file.read_bytes()).hexdigest()
        obj.set_editor_property('nodes',nodes);obj.set_editor_property('pattern_objects',objects)
        content=RUN/'Prepared/Content'
        prepared=content/file.relative_to(ROOT/'Content')
        u.SystemLibrary.execute_console_command(None,'KZ.Audio.SaveBindingCopy "'+path+'" "'+str(content)+'"')
        assert prepared.exists(),path
        prepared_sha=hashlib.sha256(prepared.read_bytes()).hexdigest()
        pending=RUN/'Replace'/file.relative_to(ROOT);pending.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(prepared,pending)
        assert hashlib.sha256(file.read_bytes()).hexdigest()==before_sha,'Concurrent saved change: '+path
        try:
            os.replace(pending,file)
            applied=True
        except PermissionError:
            applied=False;report['pending'].append(path)
        report['combos'].append({'asset':path,'player_impacts':hits,'monster_guards':guards,'projectiles':flights,
            'object_guards':len(objects),'non_audio_fields_unchanged':True,'before_sha256':before_sha,
            'prepared_sha256':prepared_sha,'applied':applied,'prepared':str(prepared),
            'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    assert sum(r['projectiles'] for r in report['combos'])==len(projectiles)
    report['success']=True
except Exception:
    report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Bindings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('Audio struct-array binding repair failed')
