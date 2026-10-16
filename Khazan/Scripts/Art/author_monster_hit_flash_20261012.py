"""Owned local Cascade flash; remove only ARCH-92's extra colour children."""
from pathlib import Path
import ctypes, hashlib, json, math, re, runpy, shutil, traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/HitFlashCorrection_20261012'
OUT.mkdir(exist_ok=True)
DEST = '/Game/_Art/Effects/Combat/AttackContact/PP_Monster_HitFlameFlash'
BLOOD = '/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference'
SOURCE = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success'
PLAN = json.loads((ROOT/'Metadata/CombatFinishFollowup_20261012/Authored.json').read_text(encoding='utf-8'))
EAL = u.EditorAssetLibrary
AL = u.AnimationLibrary
KEEP = []
PREVIOUS = json.loads((OUT/'Authored.json').read_text(encoding='utf-8')) if (OUT/'Authored.json').exists() else None
if PREVIOUS and not PREVIOUS.get('montages') and (OUT/'AuthorCheckpoint.json').exists():
    PREVIOUS = json.loads((OUT/'AuthorCheckpoint.json').read_text(encoding='utf-8'))
report = {'status': 'running', 'particle': {}, 'montages': [], 'removed_windows': [],
          'numeric_policy': 'Assistant temporary presentation tuning, not original metadata values.'}

def file(path):
    return ROOT / ('Content/' + path.split('.')[0].removeprefix('/Game/') + '.uasset')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def export(obj, name):
    t = u.AssetExportTask()
    t.object = obj
    t.filename = str(OUT/name)
    t.exporter = u.ObjectExporterT3D()
    t.automated = True
    t.prompt = False
    assert u.Exporter.run_asset_export_task(t)
    return (OUT/name).read_text(encoding='utf-8-sig')

def set_owned(obj, field, value):
    path = obj.get_path_name()
    assert (path.startswith(DEST+'.') or path.startswith(BLOOD+'.')) and len(path) < 256, path
    assert '\n' not in value and '\r' not in value
    # Use the same native property serializer as the montage author. Editor Exec
    # can accept SETNOPEC without applying it; every import here consumes text.
    types = {'Emitters':'FArrayProperty','Modules':'FArrayProperty','BurstList':'FArrayProperty',
             'TypeDataModule':'FObjectPropertyBase','SpawnModule':'FObjectPropertyBase','RequiredModule':'FObjectPropertyBase',
             'bEnabled':'FBoolProperty'}
    if field in ['Rate','Lifetime','StartSize','StartLocation','LifeMultiplier','ColorOverLife','AlphaOverLife','ConstantCurve'] or value.startswith('(X='):
        kind = 'FStructProperty'
    else:
        kind = types.get(field)
    if not kind:
        if value in ('True','False'): parsed = value=='True'
        elif field=='EmitterName': parsed = u.Name(value)
        elif field in ('EmitterLoops','DetailModeBitmask'): parsed = int(value)
        else: parsed = float(value)
        obj.set_editor_property(field, parsed)
        got=obj.get_editor_property(field)
        assert (math.isclose(got,parsed,rel_tol=1e-6,abs_tol=1e-7) if isinstance(parsed,float) else got==parsed), (path,field,got,parsed)
        return
    assert u.SystemLibrary.get_engine_version().startswith('5.8.2-')
    class View(ctypes.Structure):
        _fields_ = [('data',ctypes.c_void_p),('size',ctypes.c_int32)]
    dll = Path(u.Paths.engine_dir()).resolve()/'Binaries/Win64'
    core = ctypes.WinDLL(str(dll/'UnrealEditor-Core.dll'))
    objects = ctypes.WinDLL(str(dll/'UnrealEditor-CoreUObject.dll'))
    find = getattr(objects,'?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
    find.argtypes,find.restype = [ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(View),ctypes.c_uint32],ctypes.c_void_p
    def exact(p):
        buf = ctypes.create_unicode_buffer(p)
        view = View(ctypes.cast(buf,ctypes.c_void_p),len(p))
        return find(None,None,ctypes.byref(view),0)
    make_name = getattr(core,'??0FName@@QEAA@PEB_W@Z')
    make_name.argtypes,make_name.restype = [ctypes.c_void_p,ctypes.c_wchar_p],ctypes.c_void_p
    fn = ctypes.create_string_buffer(16)
    make_name(fn,field)
    fp = getattr(objects,'?FindPropertyByName@UStruct@@QEBAPEAVFProperty@@VFName@@@Z')
    fp.argtypes,fp.restype = [ctypes.c_void_p,ctypes.c_void_p],ctypes.c_void_p
    obj_ptr = exact(path)
    prop = fp(exact(obj.get_class().get_path_name()),fn)
    assert obj_ptr and prop
    imp = getattr(objects,'?ImportText_Internal@'+kind+'@@MEBAPEB_WPEB_WU?$TNotNull@PEAX@@W4EPropertyPointerType@@PEAVUObject@@HPEAVFOutputDevice@@@Z')
    imp.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int32,ctypes.c_void_p,ctypes.c_int32,ctypes.c_void_p]
    imp.restype = ctypes.c_void_p
    buf = ctypes.create_unicode_buffer(value)
    warn = ctypes.c_void_p.in_dll(core,'?GWarn@@3PEAVFFeedbackContext@@EA').value
    assert imp(prop,buf,obj_ptr,1,obj_ptr,0,warn)==ctypes.addressof(buf)+len(value)*ctypes.sizeof(ctypes.c_wchar), (path,field,value)

def token(obj):
    return '"'+obj.get_class().get_path_name()+"'"+obj.get_path_name()+"'\""

def new(cls, outer, name):
    a = u.new_object(u.load_class(None, '/Script/Engine.'+cls), outer=outer, name=name)
    assert a
    KEEP.append(a)
    return a

def dist(module, field, cls, data):
    a = new(cls, module, 'D_'+field)
    for k, v in data.items():
        set_owned(a, k, v)
    set_owned(module, field, '(Distribution='+token(a)+')')
    return a

def points(values, vector=False):
    result = []
    for t, value in values:
        v = ('(X=%s,Y=%s,Z=%s)' % (value, value, value)) if vector else str(value)
        result.append('(InVal=%s,OutVal=%s,InterpMode=CIM_Linear)' % (t, v))
    return '(Points=('+','.join(result)+'))'

def rebuild(asset):
    # Exact exported engine APIs, no UObject layout writes or property-flag changes.
    assert u.SystemLibrary.get_engine_version().startswith('5.8.2-')
    class View(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_int32)]
    dll = Path(u.Paths.engine_dir()).resolve()/'Binaries/Win64'
    core = ctypes.WinDLL(str(dll/'UnrealEditor-CoreUObject.dll'))
    engine = ctypes.WinDLL(str(dll/'UnrealEditor-Engine.dll'))
    find = getattr(core, '?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
    find.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(View), ctypes.c_uint32]
    find.restype = ctypes.c_void_p
    name = ctypes.create_unicode_buffer(asset.get_path_name())
    view = View(ctypes.cast(name, ctypes.c_void_p), len(asset.get_path_name()))
    ptr = find(None, None, ctypes.byref(view), 0)
    assert ptr and asset.get_path_name().split('.')[0] in (DEST, BLOOD)
    for method in ['UpdateAllModuleLists', 'SetupSoloing', 'BuildEmitters']:
        call = getattr(engine, '?'+method+'@UParticleSystem@@QEAAXXZ')
        call.argtypes = [ctypes.c_void_p]
        call.restype = None
        call(ptr)

def particle():
    if EAL.does_asset_exist(DEST):
        failed = PREVIOUS
        assert failed
        a = u.load_asset(DEST)
        if failed['particle']:
            assert sha(file(DEST))==failed['particle']['sha256']
    else:
        a = EAL.duplicate_asset(SOURCE, DEST)
    assert a
    KEEP.append(a)
    before = export(a, 'FlashCloneBefore.t3d')
    emitters = []
    # Existing feathered circular flare materials; no spark/streak/light emitter.
    # Sizes/lifetimes/colour/normalized-age curves below are TEMP visual tuning.
    presets = [(1, 48, .18, (.035, .12, .65)),
               (14, 56, .22, (.24, .008, .38)),
               (2, 34, .14, (.18, .002, .012))]
    for index, size, life, colour in presets:
        e = u.load_object(None, a.get_path_name()+':ParticleSpriteEmitter_'+str(index))
        lod = u.load_object(None, e.get_path_name()+'.ParticleLODLevel_0')
        # Use the existing exact required/material and UV-animation module.
        block = re.search(r'^   Begin Object Name="ParticleSpriteEmitter_'+str(index)+r'" .*?^   End Object', before, re.M|re.S).group(0)
        required_path = re.search(r'RequiredModule="[^\']+\'([^\']+)\'"', block).group(1)
        required = u.load_object(None, required_path)
        dynamic_path = re.search(r'Modules\(\d+\)="/Script/Engine.ParticleModuleParameterDynamic\'([^\']+)\'"', block)
        set_owned(e, 'DetailModeBitmask', '15')
        set_owned(lod, 'bEnabled', 'True')
        set_owned(lod, 'TypeDataModule', 'None')
        for field, value in [('EmitterLoops','1'), ('EmitterDuration','.22'), ('EmitterDelay','0'),
                             ('bUseLocalSpace','False'), ('bKillOnCompleted','False'), ('bUseMaxDrawCount','False')]:
            set_owned(required, field, value)
        spawn = new('ParticleModuleSpawn', a, 'HitFlashSpawn_'+str(index))
        set_owned(spawn, 'BurstList', '((Count=1,CountLow=-1,Time=0))')
        dist(spawn, 'Rate', 'DistributionFloatConstant', {'Constant':'0'})
        set_owned(lod, 'SpawnModule', token(spawn))
        lifetime = new('ParticleModuleLifetime', a, 'HitFlashLifetime_'+str(index))
        dist(lifetime, 'Lifetime', 'DistributionFloatConstant', {'Constant':str(life)})
        initial_size = new('ParticleModuleSize', a, 'HitFlashSize_'+str(index))
        dist(initial_size, 'StartSize', 'DistributionVectorConstant', {'Constant':'(X=%s,Y=%s,Z=%s)'%(size,size,size)})
        growth = new('ParticleModuleSizeMultiplyLife', a, 'HitFlashGrowth_'+str(index))
        dist(growth, 'LifeMultiplier', 'DistributionVectorConstantCurve',
             {'ConstantCurve':points([(0,.3),(.16,1),(.65,1.18),(1,1.25)], True)})
        col = new('ParticleModuleColorOverLife', a, 'HitFlashColour_'+str(index))
        dist(col, 'ColorOverLife', 'DistributionVectorConstant', {'Constant':'(X=%s,Y=%s,Z=%s)'%colour})
        dist(col, 'AlphaOverLife', 'DistributionFloatConstantCurve',
             {'ConstantCurve':points([(0,0),(.08,1),(.3,.85),(1,0)])})
        modules = [lifetime, initial_size, growth, col]
        if dynamic_path:
            modules.append(u.load_object(None, dynamic_path.group(1)))
        set_owned(lod, 'Modules', '('+','.join(token(x) for x in modules)+')')
        emitters.append(e)
    set_owned(a, 'Emitters', '('+','.join(token(x) for x in emitters)+')')
    set_owned(a, 'bUseFixedRelativeBoundingBox', 'False')
    rebuild(a)
    EAL.set_metadata_tag(a, 'KZHitFlashSource', SOURCE)
    EAL.set_metadata_tag(a, 'KZHitFlashTuning', json.dumps(presets))
    EAL.set_metadata_tag(a, 'KZHitFlashContract', 'Accepted monster hit only; 3 stationary circular flame/flash sprites; Rate0/Burst1; finite .14-.22s; no travelling spark, velocity, light, collision, trail or refraction module. Assistant TEMP.')
    final_text = export(a, 'FlashAuthored.t3d')
    assert len(re.findall(r'^   Emitters\(',final_text,re.M))==3
    assert 'BurstList(0)=(Count=1' in final_text and 'EmitterLoops=1' in final_text
    assert EAL.save_loaded_asset(a, only_if_is_dirty=False)
    report['particle'] = {'path':DEST, 'source':SOURCE, 'presets':presets, 'sha256':sha(file(DEST))}
    return a

def install_on_existing_hit(particle_asset):
    # The current confirmed-hit producer already plays this PS at the monster's
    # contact surface. Add finite flash emitters there; no new runtime API/state.
    blood = u.load_asset(BLOOD)
    assert blood
    backup = OUT/'AssetsBefore'/file(BLOOD).relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists(): shutil.copy2(file(BLOOD), backup)
    before_sha = sha(file(BLOOD))
    before = export(blood, 'BloodBefore.t3d')
    existing = re.findall(r'^   Emitters\(\d+\)="[^\']+\'([^\']+)\'"', before, re.M)
    assert len(existing) == 3, 'Preserve an unexpected newer blood implementation'
    class View(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_int32)]
    dll = Path(u.Paths.engine_dir()).resolve()/'Binaries/Win64'
    core = ctypes.WinDLL(str(dll/'UnrealEditor-CoreUObject.dll'))
    names = ctypes.WinDLL(str(dll/'UnrealEditor-Core.dll'))
    find = getattr(core, '?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
    find.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(View),ctypes.c_uint32]
    find.restype = ctypes.c_void_p
    make_name = getattr(names, '??0FName@@QEAA@PEB_W@Z')
    make_name.argtypes = [ctypes.c_void_p,ctypes.c_wchar_p]
    make_name.restype = ctypes.c_void_p
    duplicate = getattr(core, '?StaticDuplicateObject@@YAPEAVUObject@@PEBV1@PEAV1@VFName@@W4EObjectFlags@@PEAVUClass@@W4Type@EDuplicateMode@@W4EInternalObjectFlags@@@Z')
    duplicate.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int32,ctypes.c_int32]
    duplicate.restype = ctypes.c_void_p
    def ptr(obj):
        name = ctypes.create_unicode_buffer(obj.get_path_name())
        view = View(ctypes.cast(name,ctypes.c_void_p),len(obj.get_path_name()))
        result = find(None,None,ctypes.byref(view),0)
        assert result
        return result
    def clone(obj, outer, name):
        assert outer.get_path_name().startswith(BLOOD+'.')
        fn = ctypes.create_string_buffer(16)
        make_name(fn, name)
        # Technical enum masks from this engine's ObjectMacros.h; no tuning.
        assert duplicate(ptr(obj),ptr(outer),fn,0xffffffff,None,0,0)
        result = u.load_object(None,outer.get_path_name()+('.' if ':' in outer.get_path_name() else ':')+name)
        assert result
        KEEP.append(result)
        return result
    src_text = export(particle_asset,'FlashForMerge.t3d')
    merged = [u.load_object(None,p if p.startswith('/') else blood.get_path_name()+':'+p) for p in existing]
    assert all(merged)
    for index, name in [(1,'KZHitFlashBlue'),(14,'KZHitFlashPurple'),(2,'KZHitFlashRed')]:
        source_emitter = u.load_object(None,particle_asset.get_path_name()+':ParticleSpriteEmitter_'+str(index))
        e = clone(source_emitter,blood,name)
        block = re.search(r'^   Begin Object Name="ParticleSpriteEmitter_'+str(index)+r'" .*?^   End Object',src_text,re.M|re.S).group(0)
        lod = u.load_object(None,e.get_path_name()+'.ParticleLODLevel_0')
        required_path = re.search(r'RequiredModule="[^\']+\'([^\']+)\'"',block).group(1)
        required = clone(u.load_object(None,required_path),blood,name+'_Required')
        set_owned(lod,'RequiredModule',token(required))
        dynamic_path = re.search(r'Modules\(\d+\)="/Script/Engine.ParticleModuleParameterDynamic\'([^\']+)\'"',block)
        modules = [clone(u.load_object(None,particle_asset.get_path_name()+':'+n+'_'+str(index)),blood,name+'_'+n)
                   for n in ['HitFlashLifetime','HitFlashSize','HitFlashGrowth','HitFlashColour']]
        spawn = clone(u.load_object(None,particle_asset.get_path_name()+':HitFlashSpawn_'+str(index)),blood,name+'_Spawn')
        set_owned(lod,'SpawnModule',token(spawn))
        if dynamic_path:
            modules.append(clone(u.load_object(None,dynamic_path.group(1)),blood,name+'_Dynamic'))
        set_owned(lod,'Modules','('+','.join(token(m) for m in modules)+')')
        set_owned(e,'EmitterName',name)
        merged.append(e)
    set_owned(blood,'Emitters','('+','.join(token(e) for e in merged)+')')
    rebuild(blood)
    after = export(blood,'BloodWithFlash.t3d')
    assert len(re.findall(r'^   Emitters\(',after,re.M))==6
    # Existing blood module/particle data stay byte-for-byte in export text.
    def blocks(txt):
        return {m.group(1):m.group(0) for m in re.finditer(r'^   Begin Object Name="([^"]+)" .*?^   End Object',txt,re.M|re.S)}
    old_blocks,new_blocks = blocks(before),blocks(after)
    changed = [name for name,text in old_blocks.items() if new_blocks.get(name)!=text]
    assert not changed, 'Original blood subobject changed: '+str(changed)
    EAL.set_metadata_tag(blood,'KZHitFlashContract','Existing accepted-hit owner only; source blood3 unchanged + deep-owned stationary flash3; whiff/dodge/land alone create no flash; .14-.22s TEMP.')
    assert EAL.save_loaded_asset(blood,only_if_is_dirty=False)
    report['blood_binding'] = {'path':BLOOD,'before':before_sha,'after':sha(file(BLOOD)),
                             'original_emitters':3,'flash_emitters':3,'preserved_original_subobjects':len(old_blocks)}

def montages():
    bridge = runpy.run_path(str(ROOT/'Scripts/Animation/setup_guard_20261002.py'))['import_guard_array']
    bridge.__globals__['GUARD'] = '/Game/_Art/Player/Animation/InGame/DAS'
    for row in PLAN['montages']:
        path = row['path']
        f = file(path)
        current_sha = sha(f)
        done = next((x for x in (PREVIOUS or {}).get('montages',[]) if x['path']==path),None)
        if done:
            assert current_sha==done['after']
            report['montages'].append(done)
            report['removed_windows']+=done['removed_windows']
            continue
        assert current_sha == row['after'], 'Concurrent montage change: '+path
        backup = OUT/'AssetsBefore'/f.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, backup)
        m = u.load_asset(path)
        events = list(AL.get_animation_notify_events(m))
        original_events = [e.export_text() for e in events]
        original_children = {}
        removed = set()
        for event in events:
            parent = event.get_editor_property('notify')
            if not isinstance(parent, u.KZAnimNotify_CombatEffect):
                continue
            retained = []
            for child in list(parent.get_editor_property('BatchedEffects')):
                key = str(child.get_editor_property('EventId'))
                if key.startswith('KZExtra_') and key != 'KZExtra_PlungeGround':
                    removed.add(key)
                else:
                    original_children[child.get_path_name()] = export(child, 'ChildBefore.t3d')
                    retained.append(child)
            parent.set_editor_property('BatchedEffects', retained)
            # Extra-only parent markers are harmless if emptied; retain every
            # engine GUID, timestamp and original input marker exactly.
            key = str(parent.get_editor_property('EventId'))
            assert not (key.startswith('KZExtra_') and key != 'KZExtra_PlungeGround'), key
        assert [e.export_text() for e in AL.get_animation_notify_events(m)] == original_events
        bridge(m, 'Notifies', original_events)
        AL.add_animation_notify_track(m, '__HitFlashRefresh')
        AL.remove_animation_notify_track(m, '__HitFlashRefresh')
        assert [e.export_text() for e in AL.get_animation_notify_events(m)] == original_events
        assert EAL.save_loaded_asset(m, only_if_is_dirty=False)
        report['montages'].append({'path':path,'before':current_sha,'after':sha(f),
                                   'events':len(events),'removed_windows':sorted(removed)})
        report['removed_windows'] += sorted(removed)
        (OUT/'AuthorCheckpoint.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert len(report['removed_windows']) == 54

try:
    flash = particle()
    install_on_existing_hit(flash)
    montages()
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    raise
finally:
    (OUT/'Authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HIT_FLASH_AUTHORED', report['status'], len(report['removed_windows']))
