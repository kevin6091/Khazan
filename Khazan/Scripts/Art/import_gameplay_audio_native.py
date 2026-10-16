"""Author original media/cue assets in a task-owned Unreal commandlet."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import math
import os
import traceback
import wave
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
RUN=Path(os.environ['KZ_AUDIO_OUTPUT']);tools=u.AssetToolsHelpers.get_asset_tools();lib=u.EditorAssetLibrary
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
plan=read(os.environ.get('KZ_AUDIO_CUE_PLAN') or OUT/'NativeCuePlan01.json');decoded=read(os.environ.get('KZ_AUDIO_DECODE_PLAN') or OUT/'NativeDecodedManifest01.json')
assert all(r['status']=='decoded' for r in decoded),'Decode closure must pass before import'
report={'success':False,'waves':[],'cues':[],'created':[],'errors':[]}
probe=os.environ.get('KZ_AUDIO_IMPORT_PROBE')=='1'
def create(path,cls,factory):
    if lib.does_asset_exist(path):return lib.load_asset(path)
    parent,name=path.rsplit('/',1);obj=tools.create_asset(name,parent,cls,factory)
    assert obj,path
    report['created'].append(path);return obj
def save(obj):
    assert lib.save_loaded_asset(obj,only_if_is_dirty=False),obj.get_path_name()
def prop(obj,name,value):obj.set_editor_property(name,value)

try:
    soundclass=create('/Game/Audio/Original/Settings/SC_Original',u.SoundClass,u.SoundClassFactory())
    properties=soundclass.get_editor_property('properties')
    # Temporary native mix headroom. Original per-leaf bank gain remains unchanged.
    # Half gain is -6.0206dB; protects the summed near-field fight/ambient mix.
    if os.environ.get('KZ_AUDIO_PRESERVE_SETTINGS')!='1':
        prop(properties,'volume',0.5);prop(soundclass,'properties',properties);save(soundclass)
    attenuation=create('/Game/Audio/Original/Settings/ATT_Character',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation')
    # Fallback only, native spatial adapter until a unique source attenuation can
    # be assigned. Unit cm. Keeps nearby character layers coherent.
    prop(settings,'attenuate',True);prop(settings,'spatialize',True)
    prop(settings,'attenuation_shape',u.AttenuationShape.SPHERE)
    prop(settings,'attenuation_shape_extents',u.Vector(100.,0.,0.));prop(settings,'falloff_distance',1900.)
    prop(settings,'distance_algorithm',u.AttenuationDistanceModel.LOGARITHMIC)
    prop(settings,'enable_reverb_send',True);prop(settings,'reverb_wet_level_min',0.05);prop(settings,'reverb_wet_level_max',0.15)
    if os.environ.get('KZ_AUDIO_PRESERVE_SETTINGS')!='1':prop(attenuation,'attenuation',settings);save(attenuation)
    concurrency=create('/Game/Audio/Original/Settings/CON_OriginalSFX',u.SoundConcurrency,u.SoundConcurrencyFactory())
    cs=concurrency.get_editor_property('concurrency')
    # Temporary voice budget, not an original Wwise limit. Quiet distant voices
    # give way to actual nearby attacks. Long ambience uses its own concurrency.
    prop(cs,'max_count',64);prop(cs,'resolution_rule',type(cs.get_editor_property('resolution_rule')).STOP_QUIETEST)
    if os.environ.get('KZ_AUDIO_PRESERVE_SETTINGS')!='1':prop(concurrency,'concurrency',cs);save(concurrency)
    submix=create('/Game/Audio/Original/Settings/SM_Original',u.SoundSubmix,u.SoundSubmixFactory())
    if os.environ.get('KZ_AUDIO_PRESERVE_SETTINGS')!='1':save(submix)
    selected_cues=plan['cues']
    if probe:selected_cues=[c for c in selected_cues if c['event_name'] in ('Play_PLYR_Footsteps','Play_PLYR_VO_Dmg','Play_PLYR_DualAxeSword_Guard_Suc')]
    if os.environ.get('KZ_AUDIO_IMPORT_NAMES'):
        names=set(os.environ['KZ_AUDIO_IMPORT_NAMES'].split(','))
        selected_cues=[c for c in selected_cues if c['event_name'] in names]
    needed=set()
    def gather(n):
        if n['kind']=='wave':needed.add(n['wave_key'])
        for c in n.get('children',[]):gather(c)
        if n['kind']=='surface_switch':
            for c in list(n['branches'].values())+[n['default']]:gather(c)
    for c in selected_cues:gather(c['graph'])
    wave_objects={};decoded_by={r['key']:r for r in decoded}
    import_rows=[]
    for row in decoded:
        if row['key'] not in needed:continue
        import_rows.append(row)
        import_rows.extend(dict(p,key=row['key']+'_'+p['kind'],seconds=(p['end_frame']-p['start_frame'])/row['sample_rate']) for p in row.get('loop_parts',[]))
    tasks=[]
    for row in import_rows:
        if lib.does_asset_exist(row['asset']):continue
        task=u.AssetImportTask();parent,name=row['asset'].rsplit('/',1)
        for key,value in (('filename',row['wave_file']),('destination_path',parent),('destination_name',name),('automated',True),('replace_existing',False),('save',False)):prop(task,key,value)
        task.set_editor_property('factory',u.SoundFactory());tasks.append(task)
    # Modest batches keep transient editor import memory bounded.
    for i in range(0,len(tasks),100):
        tools.import_asset_tasks(tasks[i:i+100]);u.log('KZAudio Imported wave batch '+str(i//100+1))
    for row in import_rows:
        obj=lib.load_asset(row['asset']);assert isinstance(obj,u.SoundWave),row['asset']
        if os.environ.get('KZ_AUDIO_PRESERVE_EXISTING_WAVES')=='1' and row['asset'] not in report['created'] and row['key'] in set(r.get('key') for r in decoded if r.get('reused_existing')):
            wave_objects[row['key']]=obj;continue
        prop(obj,'volume',1.);prop(obj,'pitch',1.)
        prop(obj,'sound_asset_compression_type',u.SoundAssetCompressionType.PCM)
        prop(obj,'compression_quality',100)
        # PCM avoids an additional lossy encode of already compressed originals.
        # UE5.8 derives stream caching from its loading behavior/platform policy;
        # the legacy bStreaming property is no longer reflected.
        prop(obj,'loading_behavior',u.SoundWaveLoadingBehavior.LOAD_ON_DEMAND)
        prop(obj,'sound_class_object',soundclass)
        lib.set_metadata_tag(obj,'OriginalAudioSource',row.get('media','Source loop region'))
        lib.set_metadata_tag(obj,'OriginalDecodedSHA256',row['wave_sha256'])
        lib.set_metadata_tag(obj,'AudioConversion','Original WEM -> PCM16, source rate/channels, no normalization/tail trim; cue gain separate')
        save(obj);wave_objects[row['key']]=obj
        report['waves'].append({'asset':row['asset'],'key':row['key'],'duration':obj.get_editor_property('duration'),'source_seconds':row['seconds']})
    serial=[0]
    def node(cls,cue,children=None):
        serial[0]+=1;n=u.new_object(cls,outer=cue)
        if children is not None:prop(n,'child_nodes',children)
        return n
    silence_cache={}
    def silent(seconds,cue):
        if seconds<=0:return None
        key=str(seconds)
        if key not in silence_cache:
            ident=hashlib.sha256(key.encode()).hexdigest()[:12];path='/Game/Audio/Original/Media/SW_Silence_'+ident
            file=OUT/('Silence_'+ident+'.wav')
            if not file.exists():
                with wave.open(str(file),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000);f.writeframes(bytes(round(seconds*48000)*2))
            if not lib.does_asset_exist(path):
                task=u.AssetImportTask();prop(task,'filename',str(file));prop(task,'destination_path',path.rsplit('/',1)[0]);prop(task,'destination_name',path.rsplit('/',1)[1]);prop(task,'automated',True);prop(task,'save',False);tools.import_asset_tasks([task])
            obj=lib.load_asset(path);save(obj);silence_cache[key]=obj
        player=node(u.SoundNodeWavePlayer,cue);prop(player,'sound_wave',silence_cache[key]);return player
    def random(children,weights,cue,avoid):
        if len(children)==1:return children[0]
        if len(children)>32:
            buckets=[children[i:i+32] for i in range(0,len(children),32)];wb=[weights[i:i+32] for i in range(0,len(weights),32)]
            return random([random(c,w,cue,avoid) for c,w in zip(buckets,wb)],[sum(w) for w in wb],cue,avoid)
        n=node(u.SoundNodeRandom,cue,children);prop(n,'weights',weights);prop(n,'randomize_without_replacement',avoid>0);prop(n,'preselect_at_level_load',0);return n
    def combine(cls,children,cue):
        if len(children)==1:return children[0]
        if len(children)>32:children=[combine(cls,children[i:i+32],cue) for i in range(0,len(children),32)]
        n=node(cls,cue,children);prop(n,'input_volume',[1.]*len(children));return n
    def graph(spec,cue):
        kind=spec['kind'];n=None
        if kind=='wave':
            d=decoded_by[spec['wave_key']]
            if spec.get('loop') and d.get('loop_parts'):
                parts=[]
                for p in d['loop_parts']:
                    player=node(u.SoundNodeWavePlayer,cue);prop(player,'sound_wave',wave_objects[d['key']+'_'+p['kind']]);prop(player,'looping',p['kind']=='Loop');parts.append(player)
                n=parts[0] if len(parts)==1 else node(u.SoundNodeConcatenator,cue,parts)
                if len(parts)>1:prop(n,'input_volume',[1.]*len(parts))
            else:
                n=node(u.SoundNodeWavePlayer,cue);prop(n,'sound_wave',wave_objects[spec['wave_key']]);prop(n,'looping',spec.get('loop',False))
        elif kind=='silence':return silent(spec['seconds'],cue)
        elif kind=='surface_switch':
            default=graph(spec['default'],cue);maxsurface=max(int(k) for k in spec['branches'])
            branches=[default]+[graph(spec['branches'].get(str(i),spec['default']),cue) for i in range(maxsurface+1)]
            n=node(u.SoundNodeSwitch,cue,branches);prop(n,'int_parameter_name','KZPhysicalSurface')
        else:
            children=[graph(c,cue) for c in spec['children']]
            if spec.get('rtpc_layer'):
                curves=spec['rtpc_layer']['curves']
                # Source layer has a hard speed transition at duplicate230 keys.
                # Native bool band is produced from actual owner velocity.
                slow=next((i for i,c in enumerate(curves) if c[0]['To']>0),None)
                fast=next((i for i,c in enumerate(curves) if c[0]['To']==0 and c[-1]['To']>0),None)
                assert slow is not None and fast is not None,(spec.get('source_node'),curves)
                n=node(u.SoundNodeSwitch,cue,[children[slow],children[slow],children[fast]]);prop(n,'int_parameter_name','KZFootstepBand')
            elif kind=='random':
                filtered=[(c,w) for c,w in zip(children,spec.get('weights',[1.]*len(children))) if c]
                if not filtered:return None
                n=random([c for c,w in filtered],[w for c,w in filtered],cue,spec.get('avoid_repeat',0))
            else:
                children=[c for c in children if c]
                if not children:return None
                if len(children)==1:n=children[0]
                else:
                    n=combine(u.SoundNodeMixer if kind=='mixer' else u.SoundNodeConcatenator,children,cue)
            if spec.get('loop'):
                n=node(u.SoundNodeLooping,cue,[n]);prop(n,'loop_indefinitely',True)
        if spec.get('gain_db',0.) and n:
            gain=math.pow(10.,spec['gain_db']/20.)
            n=node(u.SoundNodeModulator,cue,[n]);prop(n,'volume_min',gain);prop(n,'volume_max',gain);prop(n,'pitch_min',1.);prop(n,'pitch_max',1.)
        if spec.get('pad_before') and n:
            n=node(u.SoundNodeDelay,cue,[n]);prop(n,'delay_min',spec['pad_before']);prop(n,'delay_max',spec['pad_before'])
        if spec.get('pad_after') and n:
            n=node(u.SoundNodeConcatenator,cue,[n,silent(spec['pad_after'],cue)]);prop(n,'input_volume',[1.,1.])
        return n
    for c in selected_cues:
        cue=create(c['asset'],u.SoundCue,u.SoundCueFactoryNew());serial[0]=0
        root=graph(c['graph'],cue);assert root,c['event_name']
        prop(cue,'first_node',root);prop(cue,'volume_multiplier',1.);prop(cue,'pitch_multiplier',1.)
        prop(cue,'sound_class_object',soundclass);prop(cue,'sound_submix_object',submix)
        prop(cue,'attenuation_settings',None if '/Ui/' in c['event_package'] else attenuation)
        prop(cue,'concurrency_set',[] if c['loop'] else [concurrency])
        prop(cue,'virtualization_mode',u.VirtualizationMode.PLAY_WHEN_SILENT if c['loop'] else u.VirtualizationMode.DISABLED)
        lib.set_metadata_tag(cue,'OriginalEventPackage',c['event_package']);lib.set_metadata_tag(cue,'OriginalEventID',c['event_id'])
        lib.set_metadata_tag(cue,'OriginalRecipeSources',json.dumps(c['recipes']))
        lib.set_metadata_tag(cue,'NativeAudioAdaptation','Source gain/delay/layer/random weights, source230 speed band; native spatial/reverb and random bag differ from Wwise DSP')
        report['cues'].append({'asset':c['asset'],'event_id':c['event_id'],'event_package':c['event_package'],'nodes':serial[0],'loop_expected':c['loop']})
    finalize=RUN/'Finalize.json';finalize.write_text(json.dumps({'cue_paths':[r['asset'] for r in report['cues']]},indent=2),encoding='utf-8')
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.FinalizeCues '+str(finalize).replace('\\','/'))
    for row in report['cues']:
        cue=lib.load_asset(row['asset']);save(cue);row['duration']=cue.get_editor_property('duration');row['max_distance']=cue.get_editor_property('max_distance')
    report['success']=True
except Exception:
    report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
finally:
    (RUN/'Import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    u.log('KZAudio Import '+str(report['success'])+' waves='+str(len(report['waves']))+' cues='+str(len(report['cues'])))
if not report['success']:raise RuntimeError('KZAudio import failed; see Import.json')
