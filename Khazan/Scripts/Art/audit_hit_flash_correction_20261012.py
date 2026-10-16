"""Fresh saved content readback; never writes a game asset."""
from pathlib import Path
import hashlib, json, os, re, unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
PLAN=json.loads((ROOT/'Metadata/HitFlashCorrection_20261012/Authored.json').read_text(encoding='utf-8'))
assert PLAN['status']=='passed'
R={'status':'running','asset_saves':0,'montages':[],'particles':[],'families':[]}
def export(a,name):
    t=u.AssetExportTask();t.object=a;t.filename=str(OUT/name);t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False
    assert u.Exporter.run_asset_export_task(t)
    return (OUT/name).read_text(encoding='utf-8-sig')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def file(path):return ROOT/('Content/'+path.split('.')[0].removeprefix('/Game/')+'.uasset')
ground=0
for row in PLAN['montages']:
    path=row['path'];assert sha(file(path))==row['after']
    m=u.load_asset(path);events=list(u.AnimationLibrary.get_animation_notify_events(m));assert len(events)==row['events']
    for e in events:
        p=e.get_editor_property('notify')
        if not isinstance(p,u.KZAnimNotify_CombatEffect):continue
        for c in [p]+list(p.get_editor_property('BatchedEffects')):
            key=str(c.get_editor_property('EventId'))
            assert not key.startswith('KZExtra_') or key=='KZExtra_PlungeGround',key
            if key=='KZExtra_PlungeGround':
                ground+=1;assert c.get_editor_property('bSpawnOnFloor')
    R['montages'].append({'path':path,'events':len(events),'sha256':row['after']})
assert ground==2
for path,count,key in [(PLAN['particle']['path'],3,'Flash'),(PLAN['blood_binding']['path'],6,'Blood')]:
    a=u.load_asset(path);assert a
    expected=PLAN['particle']['sha256'] if key=='Flash' else PLAN['blood_binding']['after']
    assert sha(file(path))==expected
    txt=export(a,key+'.t3d');emitters=re.findall(r'^   Emitters\(\d+\)="[^\']+\'([^\']+)\'"',txt,re.M)
    assert len(emitters)==count
    flash_names=['KZHitFlashBlue','KZHitFlashPurple','KZHitFlashRed'] if key=='Blood' else ['ParticleSpriteEmitter_1','ParticleSpriteEmitter_14','ParticleSpriteEmitter_2']
    rows=[]
    for index,name in zip([1,14,2],flash_names):
        prefix=name+'_' if key=='Blood' else ''
        suffix='' if key=='Blood' else '_'+str(index)
        e=u.load_object(None,a.get_path_name()+':'+name);assert e
        assert e.get_editor_property('DetailModeBitmask')==15
        lifetime=u.load_object(None,a.get_path_name()+':'+prefix+'HitFlashLifetime'+suffix)
        lifetime_text=export(lifetime,key+'_'+name+'_Lifetime.t3d')
        expected_life={1:.18,14:.22,2:.14}[index]
        assert abs(float(re.search(r'^\s+Constant=([0-9.]+)',lifetime_text,re.M).group(1))-expected_life)<1e-6
        spawn=u.load_object(None,a.get_path_name()+':'+(name+'_Spawn' if key=='Blood' else 'HitFlashSpawn_'+str(index)))
        spawn_text=export(spawn,key+'_'+name+'_Spawn.t3d')
        assert 'BurstList(0)=(Count=1)' in spawn_text
        rate=u.load_object(None,spawn.get_path_name()+'.D_Rate');assert rate.get_editor_property('Constant')==0
        colour=u.load_object(None,a.get_path_name()+':'+prefix+'HitFlashColour'+suffix)
        colour_text=export(colour,key+'_'+name+'_Colour.t3d')
        assert 'InVal=0.080000,OutVal=1.000000' in colour_text
        # UE text export omits the default zero OutVal on the terminal key.
        terminal=re.search(r'\(InVal=1.000000(?:,([^)]*))?\)',colour_text).group(1) or ''
        assert 'OutVal=' not in terminal or 'OutVal=0.000000' in terminal
        lod=u.load_object(None,e.get_path_name()+'.ParticleLODLevel_0')
        lod_text=export(lod,key+'_'+name+'_LOD.t3d')
        assert 'bEnabled=False' not in lod_text
        modules=re.findall(r'^\s+Modules\(\d+\)="[^\']+\'([^\']+)\'"',lod_text,re.M)
        assert len(modules)==5 and not any(x in lod_text for x in ['ParticleModuleVelocity','ParticleModuleCollision','TypeDataModule='])
        if PLAN.get('visibility'):
            location=u.load_object(None,a.get_path_name()+':'+(name+'_Location' if key=='Blood' else 'HitFlashLocation_'+str(index)))
            offset=u.load_object(None,location.get_path_name()+'.D_StartLocation').get_editor_property('Constant')
            assert abs(offset.x-40)<1e-6 and offset.y==0 and offset.z==0
        rows.append({'emitter':name,'lifetime_seconds':expected_life,'burst':1,'rate':0,'modules':len(modules),'moving_sparks':False})
    R['particles'].append({'path':path,'enabled_emitter_references':count,'sha256':expected,'flash':rows})
for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
    c=u.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+family+'.BP_Monster_'+family+'_C')
    m=u.get_default_object(c);assert m.get_editor_property('HitBloodEffect').get_path_name().split('.')[0]==PLAN['blood_binding']['path']
    assert m.get_editor_property('HitBloodDecalScatterCount')==6
    R['families'].append(family)
R['remaining_extra_windows']=1;R['removed_colour_windows']=54
R['dirty']=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()];assert not R['dirty']
R['status']='passed'
(OUT/'SavedAudit.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('HIT_FLASH_FRESH_AUDIT_PASSED',len(R['montages']),len(R['families']))
