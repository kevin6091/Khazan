"""Append original VFX states and six death presentations in the private project."""
from collections import Counter, defaultdict, deque
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import runpy
import shutil
import struct
import traceback
from datetime import datetime, timezone
from decimal import Decimal
import unreal

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path(unreal.Paths.project_dir()).resolve()
EXPECTED=Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
assert WORK==EXPECTED,'Main/shared editor authoring blocked'
OUT=MAIN/'Saved/ImportReports/MonsterVFX_20261008/Authoring'
OUT.mkdir(parents=True,exist_ok=True)
PLANFILE=OUT.parent/'PreparedPlaybackPlan.json'
PLAN=json.loads(PLANFILE.read_text(encoding='utf-8-sig'))
MODE=globals().get('KZ_MONSTER_VFX_AUTHOR_MODE','apply')
assert MODE in ('probe','apply')
if MODE=='apply':
    assert not PLAN['blockers'],PLAN['blockers'][:5]
    assert PLAN['resource_reports_present'],'Native adapter/GPU registry receipt required'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
STATE=unreal.load_class(None,'/Script/Khazan.KZAnimNotifyState_MonsterVisual')
EFFECT=unreal.load_class(None,'/Script/Khazan.KZAnimNotify_CombatEffect')
assert STATE and EFFECT

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write(name,value):
    p=OUT/name;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(t,p)

def relative(asset):
    return 'Content/'+asset.split('.')[0].removeprefix('/Game/')+'.uasset'

def private(asset):
    p=WORK/relative(asset)
    assert p.resolve().is_relative_to(WORK),'Shared content save blocked: '+asset
    assert any(asset.startswith('/Game/Monsters/'+f+'/') or ('/Animations/' in asset and ('/'+f+'/Animations/') in asset)
        for f in ('Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga'))
    return p

# Reuse typed particle/decal field assignment and exact UE numeric formatting.
SOURCE=MAIN/'Scripts/Art/player_attack_vfx_author.py'
needed={'vector','decimal','transform','surface_text','routes','float_parameters','assign','guid','f32','trigger','precise_time_text','export'}
tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed],type_ignores=[]),str(SOURCE),'exec'),globals())
ARRAY_BRIDGE=runpy.run_path(str(MAIN/'Scripts/Animation/setup_guard_20261002.py'))['import_guard_array']

def routes(values):
    # Source explicit null entries suppress emission on that surface; they are
    # not missing imports and must not fall through to another physical route.
    result=[]
    for raw in values:
        row=unreal.KZCombatEffectSurfaceRoute();row.import_text(surface_text(raw['Surface']))
        if 'ParticleTemplate' in raw:
            particle=unreal.load_asset(raw['ParticleTemplate']) if raw['ParticleTemplate'] else None
            assert particle or raw['ParticleTemplate'] is None
            row.set_editor_property('ParticleTemplate',particle)
        if 'DecalMaterial' in raw:
            material=unreal.load_asset(raw['DecalMaterial']) if raw['DecalMaterial'] else None
            assert material or raw['DecalMaterial'] is None
            row.set_editor_property('DecalMaterial',material)
        if 'bSuppressParticle' in raw:
            row.set_editor_property('bSuppressParticle',raw['bSuppressParticle'])
        if 'bSuppressDecal' in raw:
            row.set_editor_property('bSuppressDecal',raw['bSuppressDecal'])
        row.set_editor_property('FloatParameters',float_parameters(raw.get('FloatParameters',[])))
        result.append(row)
    return result

def rich_text(v):
    if isinstance(v,bool):return 'True' if v else 'False'
    if isinstance(v,(float,int)):return decimal(v)
    if isinstance(v,str):return v.rsplit('::',1)[-1] if '::' in v else json.dumps(v,ensure_ascii=False)
    if isinstance(v,list):return '('+','.join(rich_text(x) for x in v)+')'
    if isinstance(v,dict):return '('+','.join(k+'='+rich_text(x) for k,x in v.items())+')'
    raise TypeError(type(v))

def exported_curve_keys(text):
    # UE ExportText omits default-valued fields: (Value=1) is a real Time=0
    # key, and (Time=1.2) is a real Value=0 key. Split actual key structs rather
    # than requiring both numbers to be present in their text.
    match=re.search(r'\bKeys=\(',text)
    if not match:return []
    start=match.end();depth=1;end=start
    while end<len(text) and depth:
        depth+=(text[end]=='(')-(text[end]==')');end+=1
    assert depth==0,'Unbalanced rich-curve ExportText'
    body=text[start:end-1];rows=[];depth=0;begin=0
    for i,c in enumerate(body):
        depth+=(c=='(')-(c==')')
        if c==',' and depth==0:
            rows.append(body[begin:i]);begin=i+1
    if body[begin:].strip():rows.append(body[begin:])
    result=[]
    for row in rows:
        assert row.startswith('(') and row.endswith(')'),row
        fields=dict(re.findall(r'(\w+)=([^,()]+)',row))
        result.append(fields)
    return result

def assign_extra(obj,fields):
    ordinary={k:v for k,v in fields.items() if k not in ('TrailMesh','TrailMaterial','MaterialOverlay','MaterialOverrides','ScalarCurve','SourceCorrectionTranslation','SourceCorrectionRotation','SourceCorrectionScale')}
    assign(obj,ordinary)
    for k,v in fields.items():
        if k in ('TrailMesh','TrailMaterial','MaterialOverlay'):
            value=unreal.load_asset(v) if v else None
            assert value or not v,(k,v)
            obj.set_editor_property(k,value)
        elif k in ('ScalarCurve','SourceCorrectionTranslation','SourceCorrectionRotation','SourceCorrectionScale'):
            typ=unreal.RuntimeFloatCurve if k=='ScalarCurve' else unreal.RuntimeVectorCurve
            value=typ();value.import_text(rich_text(v))
            if k=='ScalarCurve':
                keys=v['EditorCurveData'].get('Keys',[]);text=value.export_text()
                actual=exported_curve_keys(text)
                assert len(actual)==len(keys),'Rich-curve import dropped keys: '+text
                # ExportText rounds float text; this checks serialization, not
                # a new gameplay tolerance or source tuning value.
                for raw,key in zip(keys,actual):
                    for field in ('Time','Value','ArriveTangent','LeaveTangent','ArriveTangentWeight','LeaveTangentWeight'):
                        expected=raw.get(field,0);key_value=float(key.get(field,0))
                        assert abs(key_value-f32(expected))<=1e-6*max(1,abs(expected)),(field,key_value,expected)
                    # These defaults are FRichCurveKey's reflected defaults,
                    # not gameplay values. Nondefault modes must be explicit.
                    defaults={'InterpMode':'RCIM_Linear','TangentMode':'RCTM_Auto','TangentWeightMode':'RCTWM_WeightedNone'}
                    for field,default in defaults.items():
                        expected=raw.get(field,default).rsplit('::',1)[-1]
                        assert key.get(field,default).strip('"')==expected,(field,key,expected)
            obj.set_editor_property(k,value)
        elif k=='MaterialOverrides':
            values=[]
            for raw in v:
                value=unreal.KZMonsterVisualMaterialOverride()
                for field,path in raw.items():
                    material=unreal.load_asset(path);assert material,(field,path)
                    value.set_editor_property(field,material)
                values.append(value)
            obj.set_editor_property(k,values)

def encode(value):
    if value is None or isinstance(value,(str,bool,int,float)):
        return value
    if hasattr(value,'get_path_name'):
        return value.get_path_name()
    if hasattr(value,'export_text'):
        return value.export_text()
    if isinstance(value,unreal.Vector):
        return {'X':value.x,'Y':value.y,'Z':value.z}
    if isinstance(value,unreal.Rotator):
        return {'Pitch':value.pitch,'Yaw':value.yaw,'Roll':value.roll}
    try:
        return [encode(v) for v in value]
    except TypeError:
        return str(value)

def data_fields(obj,fields):
    return {k:encode(obj.get_editor_property(k)) for k in fields}

def track_names(asset):
    return [str(n) for n in unreal.AnimationLibrary.get_animation_notify_track_names(asset)]

def state_events(asset):
    return list(unreal.AnimationLibrary.get_animation_notify_events(asset))

def exported_struct_fields(text):
    assert text.startswith('(') and text.endswith(')'),text
    body=text[1:-1];parts=[];depth=0;quoted=False;escaped=False;begin=0
    for i,c in enumerate(body):
        if escaped:escaped=False;continue
        if c=='\\' and quoted:escaped=True;continue
        if c=='"':quoted=not quoted;continue
        if quoted:continue
        depth+=(c=='(')-(c==')')
        if c==',' and depth==0:parts.append(body[begin:i]);begin=i+1
    if body[begin:].strip():parts.append(body[begin:])
    return dict(p.split('=',1) for p in parts if '=' in p)

def actual_event(e):
    text=e.export_text();fields=exported_struct_fields(text)
    ending=exported_struct_fields(fields.get('EndLink','()'))
    offset=f32(float(fields.get('TriggerTimeOffset',0)))
    trigger=unreal.AnimationLibrary.get_anim_notify_event_trigger_time(e)
    start=f32(trigger-offset);assert f32(start+offset)==trigger,'Cannot reconstruct exact native start trigger'
    duration=unreal.AnimationLibrary.get_anim_notify_event_duration(e)
    return {'text':text,'guid':guid(text),'trigger':trigger,'duration':duration,
        'link_value':start,'trigger_offset':offset,'end_link_value':f32(float(ending.get('LinkValue',0))),
        'end_offset':f32(float(fields.get('EndTriggerTimeOffset',0))),
        'end_link_precision':'UE exported decimal field; native GetTriggerTime and stored Duration checked separately',
        'start_plus_stored_duration':f32(start+duration)}

def raw_snapshot(asset):
    model=asset.controller.get_model_interface()
    rate=model.get_frame_rate()
    # UE's object exporter captures the full reflected model, including all
    # raw animation channels/curve keys, without selecting pose samples only.
    scratch=OUT/'_RawModelScratch.t3d'
    export(model,scratch)
    raw=sha(scratch)
    return {'model_class':model.get_class().get_path_name(),'model_path':model.get_path_name(),
        'raw_model_t3d_sha256':raw,'bone_track_names':[str(n) for n in model.get_bone_track_names()],
        'float_curves':model.get_number_of_float_curves(),'transform_curves':model.get_number_of_transform_curves(),
        'frame_rate':[rate.numerator,rate.denominator],'frames':model.get_number_of_frames(),'keys':model.get_number_of_keys(),
        'seconds':asset.get_play_length(),'skeleton':asset.get_editor_property('skeleton').get_path_name(),
        'settings':{n:str(asset.get_editor_property(n)) for n in ('enable_root_motion','force_root_lock','root_motion_root_lock','rate_scale','interpolation','additive_anim_type','ref_pose_type')},
        'metadata':{str(k):str(v) for k,v in unreal.EditorAssetLibrary.get_metadata_tag_values(asset).items()}}

def preserved_snapshot(asset):
    return {'raw':raw_snapshot(asset),'tracks':track_names(asset),
        'sync_markers':{n:[{'name':str(v.marker_name),'time':v.time} for v in unreal.AnimationLibrary.get_animation_sync_markers_for_track(asset,n)] for n in track_names(asset)},
        'notifies':[actual_event(e) for e in state_events(asset)]}

def exact_notify_text(event,start,end,duration=None,start_offset=0,end_offset=0):
    # Source offsets were included in the original→baked plan already. States
    # use exact mapped float32 start/duration/end once, without double offsets.
    text=precise_time_text(event,f32(start),start_offset)
    text=re.sub(r'(?<=,)Duration=[-+0-9.eE]+', 'Duration='+decimal(f32(end-start) if duration is None else duration),text)
    text=re.sub(r'(?<=,)EndTriggerTimeOffset=[-+0-9.eE]+','EndTriggerTimeOffset='+decimal(end_offset),text)
    # EndLink nested linkage is established by UE's add-state API; its LinkValue
    # is overwritten at full decimal precision through the reflected struct.
    text=re.sub(r'(EndLink=\([^)]*?LinkValue=)[-+0-9.eE]+',lambda m:m.group(1)+decimal(f32(end)),text)
    return text

def verify_preserved(asset,before):
    now=preserved_snapshot(asset)
    assert now['raw']==before['raw'],'Raw channels/curves/settings changed: '+asset.get_path_name()
    assert now['sync_markers']==dict(before['sync_markers'],**{'MonsterVisual':[]}) or all(now['sync_markers'][k]==v for k,v in before['sync_markers'].items())
    assert all(n in now['tracks'] for n in before['tracks'])
    # Legacy assets may contain repeated/unassigned GUIDs. Preserve the full
    # event multiset, not just the last entry indexed by GUID.
    key=lambda r:json.dumps(r,sort_keys=True,separators=(',',':'))
    old=Counter(key(r) for r in before['notifies']);current=Counter(key(r) for r in now['notifies'])
    assert all(current[k]>=n for k,n in old.items()),'Existing notify GUID/fields/actual triggers changed'
    return now

def state_readback(state):
    effect=state.get_editor_property('Effect')
    return {'state_export_text':state.export_text() if hasattr(state,'export_text') else None,
        'effect_path':effect.get_path_name() if effect else None}

def montage_sections(asset):
    # CompositeSections has only UPROPERTY(), without editor/Python exposure.
    # Reuse the established Player VFX author's UE ObjectExporterT3D approach.
    file=OUT/'_MontageSectionsScratch.t3d';export(asset,file)
    return [line.strip() for line in file.read_text(encoding='utf-8-sig').splitlines()
        if line.strip().startswith('CompositeSections(')]

def semantic_montage_sections(lines):
    # UAnimMontage::PostLoad links sections back to this montage and fills
    # segment caches. Those derived references do not change section timing,
    # slot choice, name, next-section routing or metadata.
    derived={'LinkedMontage','LinkedSequence','SegmentIndex','SegmentBeginTime','SegmentLength','CachedLinkMethod'}
    result=[]
    for line in lines:
        index,body=line.split('=',1)
        fields=exported_struct_fields(body)
        fields={k:v for k,v in fields.items() if k not in derived}
        fields['LinkValue']=float(fields.get('LinkValue',0))
        fields['SlotIndex']=int(fields.get('SlotIndex',0))
        fields['LinkMethod']=fields.get('LinkMethod','Absolute').rsplit('::',1)[-1]
        for key in ('SectionName','NextSectionName'):
            fields[key]=fields.get(key,'None').strip('"')
        result.append({'index':int(re.search(r'\((\d+)\)',index).group(1)),'fields':fields})
    return result

def preflight(report):
    for path,expected in PLAN.get('source_inputs',{}).items():
        assert sha(path)==expected,'Prepared source/report input changed: '+path
    resources={r['native_destination']:r['native_sha256'] for e in PLAN['events'] for r in e.get('resource_resolution',[])
        if r.get('native_destination') and r.get('native_sha256')}
    for asset,expected in resources.items():
        file=WORK/relative(asset)
        assert file.resolve().is_relative_to(WORK) and sha(file)==expected,'Native resource changed after plan: '+asset
    targets=sorted({e['asset'] for e in PLAN['events']+PLAN.get('lifetime_sentinels',[])})
    for path in targets:
        file=private(path);expected=PLAN['asset_baseline'][relative(path)]
        assert expected and sha(file)==expected,'Independent private sequence change: '+path
    for d in PLAN['death_presentations']:
        file=private(d['definition']);expected=PLAN['definition_baseline'][relative(d['definition'])]
        assert expected and sha(file)==expected,'Independent CharacterDefinition change: '+d['definition']
        assert not private(d['montage']).exists(),'Existing death presentation is not replaced'
    report['preflight']={'sequence_targets':len(targets),'definitions':len(PLAN['death_presentations']),
        'native_resources':len(resources),'new_montages_absent':True,'all_before_sha256_matched':True}

def journal_asset(report,path,created=False):
    file=private(path)
    row={'path':path,'relative':relative(path),'created':created,'before_sha256':sha(file) if file.exists() else None}
    if not created:
        backup=OUT/'Before'/relative(path);backup.parent.mkdir(parents=True,exist_ok=True)
        assert not backup.exists() or sha(backup)==row['before_sha256'],'Conflicting retained author backup: '+path
        if not backup.exists():shutil.copy2(file,backup)
        row['backup_path']=str(backup);row['backup_sha256']=sha(backup)
    report['mutation_journal'].append(row)
    write('PrivateAuthoringProgress.json',{'status':report['status'],'pid':report['pid'],
        'plan_sha256':report['plan_sha256'],'mutation_journal':report['mutation_journal'],
        'saved_sequence_count':len(report['sequences']),'event_count':len(report['events'])})
    return row

def author_sequences(report):
    groups=defaultdict(list)
    for e in PLAN['events']+PLAN.get('lifetime_sentinels',[]):
        groups[e['asset']].append(e)
    for index,(path,events) in enumerate(groups.items()):
        file=private(path);before_hash=sha(file);asset=unreal.load_asset(path)
        assert isinstance(asset,unreal.AnimSequence),path
        before=preserved_snapshot(asset)
        track='MonsterVisual';assert track not in before['tracks'],'Task notifies already exist; do not duplicate'
        journal=journal_asset(report,path)
        unreal.AnimationLibrary.add_animation_notify_track(asset,track,unreal.LinearColor(0.2,0.6,1,1))
        added=[]
        for e in events:
            start,end=f32(e['start_time']),f32(e['end_time']);assert 0<=start<end<=asset.get_play_length()+1e-5
            state=unreal.AnimationLibrary.add_animation_notify_state_event(asset,track,start,f32(end-start),STATE)
            assert state
            if e['effect_fields']:
                effect=unreal.new_object(EFFECT,outer=state);assign_extra(effect,e['effect_fields']);state.set_editor_property('Effect',effect)
            assign_extra(state,e['state_fields'])
            event=next(n for n in state_events(asset) if n.get_editor_property('notify_state_class')==state)
            event.import_text(exact_notify_text(event,start,end));added.append(event)
            report['events'].append({'asset':path,'event_id':e['event_id'],'guid':guid(event.export_text()),
                'start_time':start,'end_time':end,'effect_fields':e['effect_fields'],'state_fields':e['state_fields'],
                'kind':e.get('project_adapter_kind','original_source_window'),
                'effect_readback':data_fields(state.get_editor_property('Effect'),e['effect_fields']) if e['effect_fields'] else {},
                'state_readback':data_fields(state,e['state_fields'])})
        values=state_events(asset)
        added_by_guid={guid(e.export_text()):e for e in added}
        # Existing events are used verbatim. Only new state structs use precise
        # mapped linkage; this task never replaces a gameplay notify object.
        old_by_guid=defaultdict(deque)
        for r in before['notifies']:old_by_guid[r['guid']].append(r)
        new_by_guid={r['guid']:r for r in report['events'] if r['asset']==path}
        texts=[]
        for event in values:
            g=guid(event.export_text())
            if g in added_by_guid:
                r=new_by_guid[g];texts.append(exact_notify_text(event,r['start_time'],r['end_time']))
            else:
                r=old_by_guid[g].popleft();texts.append(exact_notify_text(event,r['link_value'],r['end_link_value'],r['duration'],r['trigger_offset'],r['end_offset']))
        assert not any(old_by_guid.values()),'Existing notify was lost before serialization'
        ARRAY_BRIDGE.__globals__['GUARD']=path.rsplit('/',1)[0]
        ARRAY_BRIDGE(asset,'Notifies',texts)
        refresh='__MonsterVisualCacheRefresh';unreal.AnimationLibrary.add_animation_notify_track(asset,refresh);unreal.AnimationLibrary.remove_animation_notify_track(asset,refresh)
        after=verify_preserved(asset,before)
        assert len(after['notifies'])==len(before['notifies'])+len(events)
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
        journal['saved_sha256']=sha(file)
        report['sequences'].append({'path':path,'relative':relative(path),'before_sha256':before_hash,'after_sha256':sha(file),
            'before':before,'after':after,'added_states':len(events),'raw_pose_curves_settings_unchanged':True,'existing_gameplay_notifies_unchanged':True})
        if index%25==0:
            unreal.log('KZ_MONSTER_VFX_AUTHOR_PROGRESS '+str(index+1)+'/'+str(len(groups)))
            write('PrivateAuthoringProgress.json',report)

def author_death(report):
    for d in PLAN['death_presentations']:
        file=private(d['definition']);assert sha(file)==PLAN['definition_baseline'][relative(d['definition'])]
        destination=private(d['montage']);assert not destination.exists(),'Existing death presentation is not replaced'
    for d in PLAN['death_presentations']:
        definition=unreal.load_asset(d['definition']);assert definition
        file=private(d['definition']);before_hash=sha(file);before_file=OUT/(d['family']+'_Definition_Before.t3d');export(definition,before_file)
        definition_journal=journal_asset(report,d['definition'])
        montage_journal=journal_asset(report,d['montage'],created=True)
        settings=definition.get_editor_property('MonsterStamina');prior=settings.export_text()
        template=settings.get_editor_property('ExhaustionMontage');sequence=unreal.load_asset(d['source_sequence'])
        assert template and sequence
        factory=unreal.AnimMontageFactory();factory.set_editor_property('source_animation',sequence);factory.set_editor_property('target_skeleton',sequence.get_editor_property('skeleton'))
        folder,name=d['montage'].rsplit('/',1)
        montage=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.AnimMontage,factory);assert montage
        for p in ('blend_in','blend_out'):
            montage.set_editor_property(p,template.get_editor_property(p))
        montage.set_editor_property('enable_auto_blend_out',False)
        assert abs(montage.get_play_length()-sequence.get_play_length())<1e-5
        slots=montage.get_editor_property('slot_anim_tracks');assert len(slots)==1 and str(slots[0].get_editor_property('slot_name'))=='DefaultSlot'
        sections=montage_sections(montage);assert len(sections)==1
        next_section=re.search(r'\bNextSectionName=(?:"([^"]*)"|([^,)]+))',sections[0])
        assert next_section is None or (next_section.group(1) or next_section.group(2))=='None','Death presentation must be finite'
        settings.set_editor_property('DeathPresentationMontage',montage)
        # Preserve every pre-existing stamina/Brutal/resource policy field.
        def remove_death(text):
            return re.sub(r'(?:,)?DeathPresentationMontage=[^,)]+','',text)
        assert remove_death(settings.export_text())==remove_death(prior)
        definition.set_editor_property('MonsterStamina',settings)
        assert unreal.EditorAssetLibrary.save_loaded_asset(montage,False)
        assert unreal.EditorAssetLibrary.save_loaded_asset(definition,False)
        definition_journal['saved_sha256']=sha(file);montage_journal['saved_sha256']=sha(private(d['montage']))
        after_file=OUT/(d['family']+'_Definition_After.t3d');export(definition,after_file)
        assert remove_death(before_file.read_text(encoding='utf-8-sig'))==remove_death(after_file.read_text(encoding='utf-8-sig')),'Other CharacterDefinition fields changed'
        report['death_presentations'].append(dict(d,definition_relative=relative(d['definition']),definition_before_sha256=before_hash,
            definition_after_sha256=sha(file),montage_relative=relative(d['montage']),montage_after_sha256=sha(private(d['montage'])),
            settings_before=prior,settings_after=settings.export_text(),existing_settings_preserved=True,
            blend_in=montage.get_default_blend_in_time(),blend_out=montage.get_default_blend_out_time(),
            definition_all_other_fields_preserved=True,montage_slot_tracks=[v.export_text() for v in slots],
            montage_sections=sections))

def main():
    report={'schema':'Khazan.MonsterVFX.PrivateAuthoring.v1','status':'running','pid':os.getpid(),'project':str(WORK),
        'plan_sha256':sha(PLANFILE),'source_helper_sha256':sha(SOURCE),'author_script_sha256':sha(__file__),
        'sequences':[],'events':[],'death_presentations':[],'mutation_journal':[]}
    try:
        if MODE=='probe':
            asset=unreal.load_asset(PLAN['events'][0]['asset']);assert asset
            report['probe_asset']=asset.get_path_name();report['probe_snapshot']=preserved_snapshot(asset)
            transient=unreal.new_object(unreal.AnimSequence)
            unreal.AnimationLibrary.add_animation_notify_track(transient,'TransientVisualProbe')
            teststate=unreal.AnimationLibrary.add_animation_notify_state_event(transient,'TransientVisualProbe',0,0,STATE)
            assert teststate
            report['transient_notify_probe']=actual_event(state_events(transient)[0])
            report['transient_only_notify_probe_mutations']=True
            state=unreal.new_object(STATE);effect=unreal.new_object(EFFECT,outer=state)
            assign_extra(effect,PLAN['events'][0]['effect_fields']);state.set_editor_property('Effect',effect)
            material=next(e for e in PLAN['events'] if e['state_fields'].get('ScalarCurve'))
            assign_extra(state,material['state_fields'])
            report['scalar_curve_probe_readback']=data_fields(state,material['state_fields'])
            decal=next(e for e in PLAN['events'] if any('DecalMaterial' in r for r in e['effect_fields'].get('SurfaceRoutes',[])))
            assign_extra(effect,decal['effect_fields']);report['decal_route_probe_readback']=data_fields(effect,decal['effect_fields'])
            for d in PLAN['death_presentations']:
                settings=unreal.load_asset(d['definition']).get_editor_property('MonsterStamina')
                template=settings.get_editor_property('ExhaustionMontage');assert template
                assert settings.get_editor_property('DeathPresentationMontage') is None
                assert template.get_editor_property('slot_anim_tracks')
                assert montage_sections(template)
            report['state_probe_passed']=True;report['asset_mutations']=0
        else:
            preflight(report);author_sequences(report);author_death(report)
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();unreal.log_error(report['error'])
        for row in report['mutation_journal']:
            file=private(row['path']);row['failure_current_sha256']=sha(file) if file.exists() else None
            row['disk_changed']=row['failure_current_sha256']!=row['before_sha256']
        report['retry_contract']={'automatic_retry':False,'automatic_rollback':False,
            'procedure':'Close only the owned private editor without saving. CAS each disk_changed journal row against failure_current_sha256, restore verified Before backup; remove only created files with exact captured hash. Then verify all planned before SHA/absent montages and launch fresh private author. Never operate on Main.',
            'loaded_dirty_changes':'Unsaved objects may exist after failure; a fresh private process is required even when disk_changed is false.'}
    name='AuthorApiProbe.json' if MODE=='probe' else 'PrivateAuthoring.json'
    write(name,report)
    if report['status']=='failed':
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        write(name.removesuffix('.json')+'_Failed_'+stamp+'.json',report)
    private_reports=WORK/'Saved/ImportReports/MonsterVFX_20261008/Authoring';private_reports.mkdir(parents=True,exist_ok=True)
    (private_reports/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('KZ_MONSTER_VFX_AUTHOR_'+report['status'].upper(),flush=True)

if __name__=='__main__':
    main()
