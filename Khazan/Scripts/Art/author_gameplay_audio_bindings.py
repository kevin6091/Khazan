"""Saved cue spatial data and approved hit/guard/object result bindings."""
from pathlib import Path
import json
import os
import shutil
import hashlib
import traceback
import unreal as u
ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
lib=u.EditorAssetLibrary;report={'success':False,'spatial':[],'combos':[],'definitions':[],'wrappers':[],'errors':[]}
backup=OUT/'BeforeAudioBindings'
def preserve(path):
    f=ROOT/'Content'/((path[6:])+'.uasset');d=backup/f.relative_to(ROOT)
    if not d.exists():d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
    return hashlib.sha256(f.read_bytes()).hexdigest()
try:
    spatial=read(OUT/'SpatialAudioPlan01.json')
    for r in spatial['cues']:preserve(r['cue'])
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.ApplySpatialPlan "'+str(OUT/'SpatialAudioPlan01.json')+'"')
    for r in spatial['cues']:
        obj=lib.load_asset(r['cue']);assert obj
        lib.set_metadata_tag(obj,'OriginalAudioSpatialSource',r['source_package']+'; MaxAttenuationRadius='+str(r['max_distance_cm'])+'cm; '+r['policy'])
        assert lib.save_loaded_asset(obj,only_if_is_dirty=False)
        report['spatial'].append({'asset':r['cue'],'max_distance':obj.get_editor_property('max_distance'),'source_radius':r['max_distance_cm'],'source_curve':bool(r['selected_curve'])})
    wrappers={}
    for r in read(OUT/'EnvironmentAuthoringPlan01.json')['actors']:
        if r['repeat_adapter']:
            target='/Game/Audio/Original/Environment/SC_Repeat_'+r['cue'].rsplit('/',1)[-1]
            wrappers[target]={'source':r['cue'],'target':target,'repeat':True,'fire':False,'delay_min':12.,'delay_max':28.}
    target='/Game/Audio/Original/Environment/SC_HeinMachFire_Native'
    wrappers[target]={'source':'/Game/Audio/Original/Events/SC_Play_Chaos_LOBJ_Fire_Loop','target':target,'repeat':False,'fire':True,'pitch_min':.99,'pitch_max':1.01,'gain':.35}
    assert all(lib.does_asset_exist(p) for p in wrappers)
    wp=RUN/'AmbientWrappers.json';wp.write_text(json.dumps({'wrappers':list(wrappers.values())}),encoding='utf-8')
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.BuildAmbientWrappers "'+str(wp)+'"')
    fp=RUN/'FinalizeWrappers.json';fp.write_text(json.dumps({'cue_paths':list(wrappers)}),encoding='utf-8')
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.FinalizeCues "'+str(fp)+'"')
    for path in wrappers:saveobj=lib.load_asset(path);assert lib.save_loaded_asset(saveobj,only_if_is_dirty=False)
    report['wrappers']=list(wrappers.values())
    registry=u.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
    for ad in registry.get_assets_by_class(u.TopLevelAssetPath('/Script/Khazan','KZCharacterDefinitionData'),True):
        path=str(ad.package_name);name=path.lower();material=None
        for token,value in (('yetuga','yetuga'),('apes','rock'),('heavysword','metal'),('halberd','metal'),('swordshield','metal'),('shieldman','metal'),('swordsman','leather'),('player','skin'),('khazan','skin'),('kazan','skin')):
            if token in name:material=value;break
        if not material:continue
        before=preserve(path);definition=ad.get_asset();settings=definition.get_editor_property('hit_reactions')
        sound=lib.load_asset('/Game/Audio/Original/Events/SC_efx_pc_enemy_hit_'+material);assert sound
        settings.set_editor_property('impact_sound',sound);definition.set_editor_property('hit_reactions',settings)
        lib.set_metadata_tag(definition,'OriginalBodyHitAudio','Source Player_Hit event '+material+'; native current-family material mapping, original internal caller unverified')
        assert lib.save_loaded_asset(definition,only_if_is_dirty=False)
        report['definitions'].append({'asset':path,'sound':sound.get_path_name(),'material_adapter':material,'before_sha256':before})
    impact=lib.load_asset('/Game/Audio/Original/Events/SC_efx_pc_dualaxesword_com_impact')
    guard=lib.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_Guard_Suc');assert impact and guard
    projectiles={r['object_id']:r for r in read(OUT/'ProjectileAudioPlan01.json')}
    cues={r['event_package']:r for r in read(OUT/'NativeCuePlan01.json')['cues']}
    for r in read(OUT/'Bindings01/Bindings.json')['combos']:
        asset=r['asset'];obj=lib.load_asset(asset);nodes=obj.get_editor_property('nodes');objects=obj.get_editor_property('pattern_objects')
        player=asset.startswith('/Game/Data/ComboCommand/DA_Player_') or '/Player/' in asset
        count=0;hits=0
        for ni,n in enumerate(nodes):
            windows=n.get_editor_property('attack_windows')
            for wi,w in enumerate(windows):
                if player:w.set_editor_property('impact_sound',impact);hits+=1
                else:w.set_editor_property('guard_sound',guard)
                windows[wi]=w
                count+=1
            n.set_editor_property('attack_windows',windows)
            nodes[ni]=n
        for oi,o in enumerate(objects):
            o.set_editor_property('guard_sound',guard)
            source=projectiles.get(str(o.get_editor_property('id')))
            if source:
                cue=cues[source['event']];o.set_editor_property('projectile_sound',lib.load_asset(cue['asset']))
                # Yetuga source explosion has an explicit move_stop action.
                # No serialized transition time means an immediate source stop.
                o.set_editor_property('projectile_stop_fade_seconds',0.)
            objects[oi]=o
        if count or objects:
            before=preserve(asset);obj.set_editor_property('nodes',nodes);obj.set_editor_property('pattern_objects',objects)
            lib.set_metadata_tag(obj,'OriginalAudioHitPolicy','Player original DAS common impact at approved HP damage; original DAS guard-success at approved player guard. Collision/miss do not post hit sounds.')
            assert lib.save_loaded_asset(obj,only_if_is_dirty=False)
            report['combos'].append({'asset':asset,'before_sha256':before,'windows':count,'player_impacts':hits,'objects':len(objects)})
    report['success']=True
except Exception:report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Bindings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('Original audio binding author failed')
