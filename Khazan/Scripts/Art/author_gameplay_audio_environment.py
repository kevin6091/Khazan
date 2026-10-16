"""Native ambient points, source volume extents, placed-fire anchors. No visual edits."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import traceback
import unreal as u
ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
lib=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools();actors=u.get_editor_subsystem(u.EditorActorSubsystem)
editor=u.get_editor_subsystem(u.LevelEditorSubsystem);report={'success':False,'ambient':[],'fire':[],'reverb':[],'errors':[]}
TAG='KZOriginalHeinMachAudio';MAP='/Game/Maps/L_HeinMach_Environment'
def prop(o,k,v):o.set_editor_property(k,v)
def vec(d):return u.Vector(*[float(d[k]) for k in ('X','Y','Z')])
def rot(d):return u.Rotator(float(d['Pitch']),float(d['Yaw']),float(d['Roll']))
def asset(path,cls,factory):
    if lib.does_asset_exist(path):return lib.load_asset(path)
    parent,name=path.rsplit('/',1);o=tools.create_asset(name,parent,cls,factory);assert o;return o
def save(o):assert lib.save_loaded_asset(o,only_if_is_dirty=False),o.get_path_name()
def concurrency(name,count):
    obj=asset('/Game/Audio/Original/Settings/'+name,u.SoundConcurrency,u.SoundConcurrencyFactory());p=obj.get_editor_property('concurrency')
    prop(p,'max_count',count);prop(p,'resolution_rule',type(p.get_editor_property('resolution_rule')).STOP_QUIETEST);prop(obj,'concurrency',p);save(obj);return obj
def wrapped(source,name,delay=None,fire=False):
    path='/Game/Audio/Original/Environment/'+name
    obj=lib.load_asset(path) if lib.does_asset_exist(path) else lib.duplicate_asset(source,path);assert obj
    # New wrapper construction starts from a fresh duplicate exactly once.
    if lib.get_metadata_tag(obj,'OriginalAmbientWrapper')!='GameplayAudio_20261011':
        first=obj.get_editor_property('first_node')
        if delay:
            d=u.new_object(u.SoundNodeDelay,outer=obj);prop(d,'child_nodes',[first]);prop(d,'delay_min',delay[0]);prop(d,'delay_max',delay[1])
            loop=u.new_object(u.SoundNodeLooping,outer=obj);prop(loop,'child_nodes',[d]);prop(loop,'loop_indefinitely',True);first=loop
        if fire:
            # Temporary subtle phase decorrelation: synchronous repeated copies
            # of the same source fire loop otherwise sum coherently.
            mod=u.new_object(u.SoundNodeModulator,outer=obj);prop(mod,'child_nodes',[first]);prop(mod,'pitch_min',.99);prop(mod,'pitch_max',1.01);prop(mod,'volume_min',.35);prop(mod,'volume_max',.35);first=mod
        prop(obj,'first_node',first);lib.set_metadata_tag(obj,'OriginalAmbientWrapper','GameplayAudio_20261011')
        lib.set_metadata_tag(obj,'NativeAmbientAdapter','Temporary repetition delay12–28s' if delay else 'Temporary fire decorrelation pitch .99–1.01, gain .35; original source cue remains intact')
        plan=RUN/(name+'_Graph.json');plan.write_text(json.dumps({'cue_paths':[path]}),encoding='utf-8')
        u.SystemLibrary.execute_console_command(None,'KZ.Audio.FinalizeCues "'+str(plan)+'"')
        prop(obj,'virtualization_mode',u.VirtualizationMode.RESTART);save(obj)
    return obj

def snapshot():
    return {a.get_path_name():{'class':a.get_class().get_name(),'label':a.get_actor_label(),'transform':a.get_actor_transform().export_text()}
        for a in actors.get_all_level_actors() if TAG not in [str(t) for t in a.get_editor_property('tags')]}
def spawn(cls,name,location,rotation=u.Rotator()):
    a=actors.spawn_actor_from_class(cls,location,rotation);assert a
    a.set_actor_label('HM_Audio_'+name);prop(a,'tags',[TAG]);return a
try:
    f=ROOT/'Content/Maps/L_HeinMach_Environment.umap';before_hash=hashlib.sha256(f.read_bytes()).hexdigest()
    backup=OUT/'BeforeAudioEnvironment/Content/Maps/L_HeinMach_Environment.umap'
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,backup)
    assert editor.load_level(MAP)
    before=snapshot();report['before_actor_count']=len(before);report['before_map_sha256']=before_hash
    (RUN/'BeforeActors.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
    # Reruns replace only this task's native audio actors, never existing source.
    for a in list(actors.get_all_level_actors()):
        if TAG in [str(t) for t in a.get_editor_property('tags')]:actors.destroy_actor(a)
    ambient_budget=concurrency('CON_HeinMachAmbient',24);fire_budget=concurrency('CON_HeinMachFire',8)
    source_by={c['event_package']:c for c in read(OUT/'NativeCuePlan01.json')['cues']}
    for row in read(OUT/'EnvironmentAuthoringPlan01.json')['actors']:
        cue=lib.load_asset(row['cue']);assert cue
        if row['repeat_adapter']:cue=wrapped(row['cue'],'SC_Repeat_'+cue.get_name(),row['repeat_delay_seconds'])
        a=spawn(u.AmbientSound,row['source_actor'],vec(row['location']),rot(row['rotation']))
        component=a.get_editor_property('audio_component');component.set_sound(cue);component.set_auto_activate(True)
        prop(component,'concurrency_set',[ambient_budget])
        if row['outer_extent']:
            settings=u.SoundAttenuationSettings();prop(settings,'attenuate',True);prop(settings,'spatialize',False)
            prop(settings,'attenuation_shape',u.AttenuationShape.BOX)
            prop(settings,'attenuation_shape_extents',vec({k:row['inner_extent'][k]*abs(row['scale'][k]) for k in ('X','Y','Z')}))
            prop(settings,'falloff_distance',row['box_falloff_cm']);prop(settings,'distance_algorithm',u.AttenuationDistanceModel.LINEAR)
            prop(settings,'enable_reverb_send',False);component.adjust_attenuation(settings)
        prop(a,'tags',[TAG,'SourceActor:'+row['source_actor'],'SourceEvent:'+row['event']])
        report['ambient'].append({'actor':a.get_actor_label(),'source':row,'cue':cue.get_path_name(),'source_radius_cm':source_by[row['event']]['source']['duration_properties'].get('MaxAttenuationRadius')})
        reverb=row['source_reverb_components'];enabled=bool(reverb) and reverb[0].get('Properties',{}).get('bEnable',True)
        if row['outer_extent'] and row['source_aux_bus'] and enabled:
            aux=row['source_aux_bus'].rsplit('/',1)[-1];cave='cave' in aux;boss='bossroom' in aux
            effect=asset('/Game/Audio/Original/Environment/RE_'+aux,u.ReverbEffect,u.ReverbEffectFactory())
            # Native reverb is an explicitly temporary DSP approximation to the
            # original Wwise aux route; no baked IR/tail is added to source WAVs.
            profile={'decay_time':3.2 if cave else 2. if boss else .35,'density':1.,'diffusion':1.,'gain':.35,
                'gain_hf':.45,'decay_hf_ratio':.65,'reflections_gain':.035,'late_gain':.7,'reflections_delay':.015 if cave else .005,'late_delay':.025 if cave else .01}
            for key,value in profile.items():prop(effect,key,value)
            lib.set_metadata_tag(effect,'OriginalAuxBus',row['source_aux_bus']);lib.set_metadata_tag(effect,'NativeReverbPolicy','Temporary UE DSP profile; source aux identity and room extents preserved');save(effect)
            volume=spawn(u.AudioVolume,row['source_actor']+'_Reverb',vec(row['location']),rot(row['rotation']))
            origin,ext=volume.get_actor_bounds(False)
            desired={k:row['outer_extent'][k]*abs(row['scale'][k]) for k in ('X','Y','Z')}
            # Factory creates a real box brush; scale from its measured extent.
            volume.set_actor_scale3d(u.Vector(desired['X']/ext.x,desired['Y']/ext.y,desired['Z']/ext.z))
            settings=volume.get_editor_property('settings');prop(settings,'apply_reverb',True);prop(settings,'reverb_effect',effect);prop(settings,'volume',.3 if cave or boss else .08);prop(settings,'fade_time',1.5)
            volume.set_reverb_settings(settings);volume.set_priority(2. if cave or boss else 1.)
            report['reverb'].append({'actor':volume.get_actor_label(),'source_aux':row['source_aux_bus'],'profile':profile,'wet':.3 if cave or boss else .08,'desired_extent_cm':desired,'bounds':volume.get_actor_bounds(False)[1].to_tuple()})
    fire=wrapped('/Game/Audio/Original/Events/SC_Play_Chaos_LOBJ_Fire_Loop','SC_HeinMachFire_Native',fire=True)
    for anchor in list(actors.get_all_level_actors()):
        if 'KZHeinMachTutorialFire' not in [str(t) for t in anchor.get_editor_property('tags')]:continue
        if not isinstance(anchor,u.Emitter):continue
        a=spawn(u.AmbientSound,'Fire_'+anchor.get_name(),anchor.get_actor_location());component=a.get_editor_property('audio_component')
        component.set_sound(fire);component.set_auto_activate(True);prop(component,'concurrency_set',[fire_budget])
        prop(a,'tags',[TAG,'SourceFireActor:'+anchor.get_actor_label()])
        report['fire'].append({'actor':a.get_actor_label(),'source_fire':anchor.get_path_name(),'location':anchor.get_actor_location().to_tuple()})
    after=snapshot();assert before==after,'Existing actor/class/transform changed'
    assert hashlib.sha256(f.read_bytes()).hexdigest()==before_hash,'Concurrent map edit; refuse to overwrite'
    assert editor.save_current_level()
    report['after_map_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();report['preserved_existing_actors']=len(before);report['after_actor_count']=len(actors.get_all_level_actors())
    report['success']=True
except Exception:report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Environment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('HeinMach audio author failed')
