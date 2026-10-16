"""Selected montage-only polish. Original events/sections/pose data stay intact."""
from pathlib import Path
from decimal import Decimal
import os,json,csv,re,struct,runpy,hashlib,shutil,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert not (ROOT/'Metadata/CombatFinishFollowup_20261012/Authored.json').exists()
AL=u.AnimationLibrary;CLASS=u.load_class(None,'/Script/Khazan.KZAnimNotify_CombatEffect')
BRIDGE=runpy.run_path(str(ROOT/'Scripts/Animation/setup_guard_20261002.py'))['import_guard_array'];BRIDGE.__globals__['GUARD']='/Game/_Art/Player/Animation/InGame/DAS'
BLUE=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success')
PURPLE=u.load_asset('/Game/_Art/Effects/Combat/AttackContact/PP_AtkEx_Grapple_01')
RED=u.load_asset('/Game/_Art/Effects/Combat/AttackContact/PP_AtkEx_Grapple_02')
assert BLUE and PURPLE and RED
report={'status':'running','montages':[],'extra_effects':[],'changed_ground_effects':[],'numeric_policy':'All new scales and styling are assistant temporary tuning; timing uses existing source windows or section entry.'}
checkpoint=ROOT/'Metadata/CombatFinishFollowup_20261012/AuthorProgress.json'
if checkpoint.exists():report=json.loads(checkpoint.read_text(encoding='utf-8'))
elif (ROOT/'Metadata/CombatFinishFollowup_20261012/Author02/AuthorCheckpoint.json').exists():
    report=json.loads((ROOT/'Metadata/CombatFinishFollowup_20261012/Author02/AuthorCheckpoint.json').read_text(encoding='utf-8'))
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def guid(e):return re.search(r'Guid=([A-Fa-f0-9]+)',e.export_text()).group(1)
def trigger(e):return AL.get_anim_notify_event_trigger_time(e)
def precise(e,time_override=None,offset_override=None):
    # Retain exact float32 LinkValue/TriggerTimeOffset when importing the array.
    text=e.export_text();m=re.search(r'(?:^\(|,)TriggerTimeOffset=([-+0-9.eE]+)',text);offset=f32(float(m.group(1))) if m else 0.
    absolute=f32(trigger(e)-offset)
    if time_override is not None:absolute=f32(time_override)
    if offset_override is not None:offset=f32(offset_override)
    body=text[1:-1];depth=0;quoted=False;start=0;fields=[]
    for index,char in enumerate(body):
        if char=='"':quoted=not quoted
        elif not quoted:
            if char=='(':depth+=1
            elif char==')':depth-=1
            elif char==',' and depth==0:fields.append(body[start:index]);start=index+1
    fields.append(body[start:]);fields=[field for field in fields if field.split('=',1)[0] not in ('LinkValue','TriggerTimeOffset')]
    fields+=['LinkValue='+format(Decimal(str(absolute)),'f'),'TriggerTimeOffset='+format(Decimal(str(offset)),'f')]
    return '('+','.join(fields)+')'
def entries(m):
    for event in AL.get_animation_notify_events(m):
        parent=event.get_editor_property('notify')
        if isinstance(parent,u.KZAnimNotify_CombatEffect):
            yield parent
            yield from parent.get_editor_property('batched_effects')
def backup(m):
    p=ROOT/('Content/'+m.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    dest=ROOT/'Metadata/CombatFinishFollowup_20261012/AssetsBefore'/p.relative_to(ROOT)
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    return hashlib.sha256(p.read_bytes()).hexdigest()
def add(m,events,start,end,template,socket,scale,identifier,floor=False,location=None,routes=None):
    start=f32(start);end=f32(end);assert start<end
    for ending,at in [(False,start),(True,end)]:
        # Reuse an existing equal-time branching marker. Its original input name/GUID survive.
        event=next((e for e in events if abs(trigger(e)-at)<1e-7),None)
        if event is None:
            parent=AL.add_animation_notify_event(m,'KZExtraFX',at,CLASS)
            event=next(e for e in AL.get_animation_notify_events(m) if e.get_editor_property('notify')==parent)
            event.set_editor_property('montage_tick_type',u.MontageNotifyTickType.BRANCHING_POINT);events.append(event)
            event.import_text(precise(event,at,0.))
        else:
            parent=event.get_editor_property('notify')
            if not isinstance(parent,u.KZAnimNotify_CombatEffect):
                oldname=str(parent.get_editor_property('notify_name'))
                parent=u.new_object(CLASS,outer=m);parent.set_editor_property('notify_name',oldname);event.set_editor_property('notify',parent)
        child=u.new_object(CLASS,outer=parent)
        for key,value in {'EventId':identifier,'WindowStartTime':start,'WindowEndTime':end,'bEndEvent':ending,'ParticleTemplate':template,'SourceSocket':socket,'Scale3D':u.Vector(scale,scale,scale),'bAttached':not floor,'bOnlyStartAttach':True,'bSpawnOnFloor':floor,'bDestroyOnNotifyEnd':True,'bDestroyOnNotifyEndDeactived':True,'SourcePackage':'Project/CombatFinishFollowup_20261012','SourceField':'Assistant TEMP styling; source timing '+identifier}.items():child.set_editor_property(key,value)
        if location is not None:child.set_editor_property('relative_location',location)
        if routes is not None:child.set_editor_property('surface_routes',routes)
        if floor:child.set_editor_property('bAbsoluteRotation',True)
        children=list(parent.get_editor_property('batched_effects'));children.append(child);parent.set_editor_property('batched_effects',children)
    report['extra_effects'].append({'montage':m.get_path_name(),'id':identifier,'start':start,'end':end,'template':template.get_path_name() if template else 'surface routes','socket':socket,'scale':scale,'floor':floor})
rows=list(csv.DictReader((ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv').open(encoding='utf-8-sig')))
paths=sorted({r['montage'] for r in rows if 'BrutalAttack' not in r['montage']})
paths+=['/Game/_Art/Player/Animation/InGame/DAS/Dodge/AM_DAS_Player_Dodge','/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack']
source_ground=None
for path in paths:
    m=u.load_asset(path);assert m;before_sha=backup(m)
    done=next((row for row in report['montages'] if row['path']==path),None)
    if done:
        assert done['after']==before_sha,'Concurrent montage edit after author checkpoint'
        if '/SpinningAttack/' in path:
            source_ground=next(list(child.get_editor_property('surface_routes')) for child in entries(m) if str(child.get_editor_property('event_id'))=='KZFX_76d2fac806c3b73a46d3141c')
        continue
    original=list(AL.get_animation_notify_events(m));original_text={guid(e):e.export_text() for e in original};original_trigger={guid(e):trigger(e) for e in original}
    events=list(original)
    AL.add_animation_notify_track(m,'KZExtraFX',u.LinearColor(.45,.05,.8,1))
    for child in list(entries(m)):
        routes=list(child.get_editor_property('surface_routes'))
        if any(route.get_editor_property('particle_template') and '_smash_strong' in route.get_editor_property('particle_template').get_name().lower() for route in routes):
            for route in routes:
                ps=route.get_editor_property('particle_template')
                if ps and '_smash_strong' in ps.get_name().lower():
                    target=ps.get_path_name().replace('_smash_strong','_smash_weak').replace('_Smash_strong','_smash_weak')
                    replacement=u.load_asset(target)
                    if not replacement:replacement=u.load_asset(target.replace('_smash_weak','_Smash_weak'))
                    assert replacement,target;route.set_editor_property('particle_template',replacement)
            child.set_editor_property('surface_routes',routes);child.set_editor_property('source_socket','Weapon_R');child.set_editor_property('relative_location',u.Vector(0,0,100));child.set_editor_property('bSpawnOnFloor',True);child.set_editor_property('bAttached',False);child.set_editor_property('Scale3D',u.Vector(.8,.8,.8))
            child.set_editor_property('bAbsoluteRotation',True)
            source_ground=routes
            report['changed_ground_effects'].append({'montage':path,'id':str(child.get_editor_property('event_id')),'end':child.get_editor_property('bEndEvent'),'scale':.8,'socket':'Weapon_R','tip_cm':100,'resource':'original smash_weak surface variants'})
    if '/Dodge/' in path:
        # Each original directional entry receives one small blue/violet burst.
        task=u.AssetExportTask();task.object=m;task.filename=str(OUT/'DodgeBefore.t3d');task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;assert u.Exporter.run_asset_export_task(task)
        text=(OUT/'DodgeBefore.t3d').read_text(encoding='utf-8-sig')
        sections=[(re.search(r'SectionName="([^"]+)"',line).group(1),float(re.search(r'LinkValue=([-+0-9.eE]+)',line).group(1)) if 'LinkValue=' in line else 0.) for line in text.splitlines() if line.strip().startswith('CompositeSections(')]
        for index,(name,start) in enumerate(sections):
            end=next((at for _,at in sections[index+1:]),m.get_play_length())
            add(m,events,start+1e-4,end-1e-4,BLUE,'Bip001-Spine2',.25,'KZExtra_Dodge_'+name)
    elif '/FallAttack/' in path:
        assert source_ground
        text=(ROOT/'Metadata/CombatFinishFollowup_20261012/Inputs03/Fall_AM_DAS_FallAttack.t3d').read_text(encoding='utf-8-sig')
        land=next(line for line in text.splitlines() if 'CompositeSections(' in line and 'SectionName="Land"' in line)
        start=float(re.search(r'LinkValue=([-+0-9.eE]+)',land).group(1))+1e-4
        duration=json.loads((ROOT/'Metadata/GiantCombatFall_20261011/AuthoringPlan.json').read_text(encoding='utf-8'))['plunge_windows'][0]['end']
        add(m,events,start,start+duration,None,'Weapon_R',1.,'KZExtra_PlungeGround',True,u.Vector(0,0,100),source_ground)
        add(m,events,start,start+duration,BLUE,'Weapon_R',.5,'KZExtra_PlungeBlue')
        add(m,events,start,start+duration,PURPLE,'Weapon_L',.4,'KZExtra_PlungePurple')
    else:
        selected={}
        for row in rows:
            if row['montage']==path and row['success_only']=='True' and row['socket'].startswith('Weapon_') and 'Blood' in row['particle_template']:
                selected.setdefault(row['segment_index'],row)
        for segment,row in selected.items():
            start=float(row['montage_start_sec']);end=float(row['montage_end_sec']);heavy=any(s in path for s in ['Strong','Spinning','OverFury'])
            add(m,events,start,end,BLUE,row['socket'],.5 if heavy else .35,'KZExtra_Blue_'+row['event_id'])
            add(m,events,start,end,PURPLE if heavy else RED,'Weapon_L',.35 if heavy else .25,'KZExtra_Accent_'+row['event_id'])
    BRIDGE(m,'Notifies',[precise(e) for e in events]);AL.add_animation_notify_track(m,'__KZExtraRefresh');AL.remove_animation_notify_track(m,'__KZExtraRefresh')
    current=list(AL.get_animation_notify_events(m));by_guid={guid(e):e for e in current}
    for identifier,old in original_text.items():
        assert identifier in by_guid
        assert trigger(by_guid[identifier])==original_trigger[identifier]
        # Existing non-effect input remains identical except its data subclass where batching is needed.
        after_text=by_guid[identifier].export_text()
        if re.sub(r'Notify="[^"]*"','Notify="<object>"',after_text)!=re.sub(r'Notify="[^"]*"','Notify="<object>"',old):
            (OUT/'UnexpectedEventChange.json').write_text(json.dumps({'montage':path,'guid':identifier,'before':old,'after':after_text},indent=2),encoding='utf-8')
            raise AssertionError('Original event field changed; asset not saved')
    assert len({trigger(e) for e in current})==len(current),'Overlapping branching markers'
    assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    file=ROOT/('Content/'+m.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    report['montages'].append({'path':path,'before':before_sha,'after':hashlib.sha256(file.read_bytes()).hexdigest(),'old_events':len(original),'new_events':len(current)})
    (OUT/'AuthorCheckpoint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    checkpoint.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
report['status']='passed'
(OUT/'Authored.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Metadata/CombatFinishFollowup_20261012/Authored.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('POLISH_AUTHORED',len(report['montages']),len(report['extra_effects']))
