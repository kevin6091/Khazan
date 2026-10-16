"""Replace the cancelled flash with owned copies of original radial sparks."""
from pathlib import Path
import ctypes, hashlib, json, re, shutil, traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT/'Metadata/CombatImpactUpgrade_20261012'
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
HELP = {}
definitions = (ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
definitions = definitions.replace("'AlphaOverLife','ConstantCurve']", "'AlphaOverLife','ConstantCurve','StartRadius','VelocityScale']")
exec(compile(definitions, 'particle_serializer_definitions_only', 'exec'), HELP)
DEST = '/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst'
BLOOD = '/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference'
HELP.update(OUT=OUT, DEST=DEST)
set_owned, new, dist, token, export, rebuild = [HELP[k] for k in ('set_owned','new','dist','token','export','rebuild')]
EAL = u.EditorAssetLibrary
KEEP = []

def file(path):
    return ROOT/('Content/'+path.split('.')[0].removeprefix('/Game/')+'.uasset')

def backup(obj):
    p=file(obj.get_path_name()); target=OUT/'Before'/p.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists(): shutil.copy2(p,target)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def blocks(text):
    return {m.group(1):m.group(0) for m in re.finditer(r'^   Begin Object Name="([^"]+)" .*?^   End Object',text,re.M|re.S)}

class View(ctypes.Structure):
    _fields_=[('data',ctypes.c_void_p),('size',ctypes.c_int32)]
DLL=Path(u.Paths.engine_dir()).resolve()/'Binaries/Win64'
CORE=ctypes.WinDLL(str(DLL/'UnrealEditor-CoreUObject.dll'))
NAMES=ctypes.WinDLL(str(DLL/'UnrealEditor-Core.dll'))
FIND=getattr(CORE,'?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
FIND.argtypes,FIND.restype=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(View),ctypes.c_uint32],ctypes.c_void_p
NAME=getattr(NAMES,'??0FName@@QEAA@PEB_W@Z')
NAME.argtypes,NAME.restype=[ctypes.c_void_p,ctypes.c_wchar_p],ctypes.c_void_p
DUP=getattr(CORE,'?StaticDuplicateObject@@YAPEAVUObject@@PEBV1@PEAV1@VFName@@W4EObjectFlags@@PEAVUClass@@W4Type@EDuplicateMode@@W4EInternalObjectFlags@@@Z')
DUP.argtypes,DUP.restype=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int32,ctypes.c_int32],ctypes.c_void_p

def ptr(obj):
    p=obj.get_path_name(); b=ctypes.create_unicode_buffer(p); v=View(ctypes.cast(b,ctypes.c_void_p),len(p))
    result=FIND(None,None,ctypes.byref(v),0); assert result; return result

def clone(obj, outer, name):
    assert outer.get_path_name().split('.')[0] in (DEST,BLOOD)
    assert not u.find_object(None,outer.get_path_name()+':'+name)
    fn=ctypes.create_string_buffer(16); NAME(fn,name)
    assert DUP(ptr(obj),ptr(outer),fn,0xffffffff,None,0,0)
    a=u.load_object(None,outer.get_path_name()+':'+name); assert a; KEEP.append(a); return a

def deep_emitter(ps, source, source_text, source_name, dest_name):
    declared={n:p for n,p in re.findall(r'Name="([^"]+)" ExportPath="[^\']+\'([^\']+)\'"',source_text)}
    def resolve(p):
        return u.load_object(None,p if p.startswith('/') else declared[p.rsplit(':',1)[-1].rsplit('.',1)[-1]])
    block=blocks(source_text)[source_name]
    emitter=clone(resolve(declared[source_name]),ps,dest_name)
    lod_ref=re.search(r'LODLevels\(0\)="[^\']+\'([^\']+)\'"',block).group(1)
    lod=u.load_object(None,emitter.get_path_name()+'.'+lod_ref.rsplit(':',1)[-1].rsplit('.',1)[-1]); assert lod, (source_name,lod_ref,emitter.get_path_name())
    for field in ('RequiredModule','SpawnModule','TypeDataModule'):
        m=re.search(field+r'="[^\']+\'([^\']+)\'"',block)
        if m: set_owned(lod,field,token(clone(resolve(m.group(1)),ps,dest_name+'_'+field)))
    modules=[]
    for i,p in enumerate(re.findall(r'Modules\(\d+\)="[^\']+\'([^\']+)\'"',block)):
        modules.append(clone(resolve(p),ps,dest_name+'_Module'+str(i)))
    set_owned(lod,'Modules','('+','.join(token(m) for m in modules)+')')
    set_owned(emitter,'EmitterName',dest_name)
    set_owned(emitter,'DetailModeBitmask','15')
    return emitter,lod,modules

try:
    assert not (OUT/'HitBurstAuthored.json').exists()
    if EAL.does_asset_exist(DEST):
        assert not file(DEST).exists() and (OUT/'HitBurstAuthorFailed.json').exists()
        assert EAL.delete_asset(DEST), 'Remove only this failed, unsaved factory product'
    sources=[('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success','ParticleSpriteEmitter_16','KZHitFireBlue'),
             ('/Game/_Art/Effects/Combat/AttackContact/PP_AtkEx_Grapple_01','ParticleSpriteEmitter_3','KZHitFirePurple'),
             ('/Game/_Art/Effects/Combat/AttackContact/PP_AtkEx_Grapple_02','ParticleSpriteEmitter_3','KZHitFireRed')]
    ps=u.AssetToolsHelpers.get_asset_tools().create_asset(DEST.rsplit('/',1)[-1],DEST.rsplit('/',1)[0],u.ParticleSystem,u.ParticleSystemFactoryNew()); assert ps
    source_hashes={}; emitters=[]
    # Centralized asset TEMP: 3 x 40 particles, .18-.38s life, radial 1000-1800cm/s,
    # 8-18cm sprite size. Original colours/materials/dynamic parameters stay intact.
    for path,source_name,name in sources:
        source=u.load_asset(path); assert source
        source_hashes[path]=hashlib.sha256(file(path).read_bytes()).hexdigest()
        text=export(source,name+'_Source.t3d')
        emitter,lod,modules=deep_emitter(ps,source,text,source_name,name)
        required=u.load_object(None,ps.get_path_name()+':'+name+'_RequiredModule')
        spawn=u.load_object(None,ps.get_path_name()+':'+name+'_SpawnModule')
        set_owned(required,'bUseLocalSpace','False'); set_owned(required,'EmitterLoops','1'); set_owned(required,'EmitterDuration','0.38')
        dist(spawn,'Rate','DistributionFloatConstant',{'Constant':'0'})
        set_owned(spawn,'BurstList','((Count=40,CountLow=40,Time=0))')
        modules=[m for m in modules if not m.get_class().get_name().startswith(('ParticleModuleLocation','ParticleModuleVelocity','ParticleModuleLifetime','ParticleModuleSize'))]
        life=new('ParticleModuleLifetime',ps,name+'_Lifetime'); dist(life,'Lifetime','DistributionFloatUniform',{'Min':'0.18','Max':'0.38'})
        size=new('ParticleModuleSize',ps,name+'_Size'); dist(size,'StartSize','DistributionVectorUniform',{'Min':'(X=8,Y=8,Z=8)','Max':'(X=18,Y=18,Z=18)'})
        sphere=new('ParticleModuleLocationPrimitiveSphere',ps,name+'_Radial')
        sphere.set_editor_property('Velocity',True); sphere.set_editor_property('SurfaceOnly',True)
        for axis in ('Positive_X','Positive_Y','Positive_Z','Negative_X','Negative_Y','Negative_Z'):
            sphere.set_editor_property(axis,True)
        dist(sphere,'StartRadius','DistributionFloatConstant',{'Constant':'1'})
        dist(sphere,'VelocityScale','DistributionFloatUniform',{'Min':'1000','Max':'1800'})
        modules += [life,size,sphere]
        set_owned(lod,'Modules','('+','.join(token(m) for m in modules)+')')
        set_owned(lod,'bEnabled','True'); emitters.append(emitter)
    set_owned(ps,'Emitters','('+','.join(token(e) for e in emitters)+')'); rebuild(ps)
    EAL.set_metadata_tag(ps,'KZNumericPolicy','Assistant TEMP burst120/life.18-.38s/radial1000-1800cm_s/size8-18cm; original spark colours/materials. Approved hit/parry only.')
    assert EAL.save_loaded_asset(ps,only_if_is_dirty=False)
    text=export(ps,'HitBurstAuthored.t3d')
    blood=u.load_asset(BLOOD); before_sha=backup(blood); before=export(blood,'BloodBefore.t3d')
    original=[u.load_object(None,blood.get_path_name()+':ParticleSpriteEmitter_'+str(i)) for i in (2,3,4)]; assert all(original)
    merged=list(original)
    for e in emitters:
        copied,_,_=deep_emitter(blood,ps,text,e.get_name(),e.get_name()); merged.append(copied)
    set_owned(blood,'Emitters','('+','.join(token(e) for e in merged)+')'); rebuild(blood)
    EAL.remove_metadata_tag(blood,'KZHitFlashContract')
    EAL.set_metadata_tag(blood,'KZHitFireContract','Original blood3 plus original radial sparks3; only accepted Monster::PlayHitBlood. No new flash or unconditional accent.')
    after=export(blood,'BloodWithFire.t3d')
    old=blocks(before); current=blocks(after)
    # T3D may hoist the same EventGenerator declaration out of the first emitter
    # after new objects are added. Its reference and full standalone data remain.
    normalize=lambda s: re.sub(r'^ +Begin Object Name="ParticleModuleEventGenerator_1" .*?^ +End Object\n?', '', s, flags=re.M|re.S)
    original_names=[n for n in old if not n.startswith('KZHitFlash')]
    assert all(normalize(current.get(n,''))==normalize(old[n]) for n in original_names), 'Original live blood subobject must remain identical'
    assert EAL.save_loaded_asset(blood,only_if_is_dirty=False)
    report={'status':'passed','path':DEST,'sha256':hashlib.sha256(file(DEST).read_bytes()).hexdigest(),'blood':{'path':BLOOD,'before':before_sha,'after':hashlib.sha256(file(BLOOD).read_bytes()).hexdigest(),'original_blood_preserved':len(old),'removed_flash':3,'fire_emitters':3},'sources':source_hashes,'TEMP':{'burst_per_colour':40,'life_s':[.18,.38],'radial_speed_cm_s':[1000,1800],'size_cm':[8,18]}}
    assert all(hashlib.sha256(file(p).read_bytes()).hexdigest()==v for p,v in source_hashes.items())
    (OUT/'HitBurstAuthored.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('HIT_BURST_AUTHORED',report['blood'])
except Exception:
    (OUT/'HitBurstAuthorFailed.json').write_text(traceback.format_exc(),encoding='utf-8'); raise
