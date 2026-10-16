"""Release only two fully loaded packages' readers; do not alter their live objects or PIE."""
from pathlib import Path
import ctypes,json,os,datetime
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=ROOT/'Metadata/CombatImpactUpgrade_20261012'
paths=['/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst','/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference']
dirty=[p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
assert not set(paths).intersection(dirty)
assert u.SystemLibrary.get_engine_version().startswith('5.8.2-')
class View(ctypes.Structure):_fields_=[('data',ctypes.c_void_p),('size',ctypes.c_int32)]
core=ctypes.WinDLL(str(Path(u.Paths.engine_dir()).resolve()/'Binaries/Win64/UnrealEditor-CoreUObject.dll'))
find=getattr(core,'?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
find.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(View),ctypes.c_uint32];find.restype=ctypes.c_void_p
# Official ResetLoaders(UObject*), Linker.cpp:844. It flushes pending loading
# and detaches the loader. It does not change the ParticleSystem or its instances.
reset=getattr(core,'?ResetLoaders@@YAXPEAVUObject@@@Z');reset.argtypes=[ctypes.c_void_p];reset.restype=None
for path in paths:
 asset=u.EditorAssetLibrary.load_asset(path);assert asset
 name=ctypes.create_unicode_buffer(asset.get_path_name());view=View(ctypes.cast(name,ctypes.c_void_p),len(asset.get_path_name()))
 ptr=find(None,None,ctypes.byref(view),0);assert ptr;reset(ptr)
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'paths':paths,'dirty_preserved':dirty,'game_world_active':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'live_object_edits':0,'saves':0,'pie_controls':0,'operation':'CoreUObject ResetLoaders(UObject*) for fully loaded owned PS packages only'}
(OUT/'LivePackageReadersReleased.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
