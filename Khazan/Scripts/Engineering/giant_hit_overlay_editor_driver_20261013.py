from pathlib import Path
import os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=os.environ['KZ_MONSTER_PHYSICS_OUT']
os.environ.update(KZ_MONSTER_REPAIR_OUT=out,KZ_MONSTER_REPAIR_MODE=os.environ.get('KZ_GIANT_HIT_MODE','rhi'),KZ_MONSTER_REPAIR_TEST=os.environ.get('KZ_GIANT_HIT_TEST','Khazan.GiantHit.PIE'))
s=(main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
s=s.replace("Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')","Path('C:/Users/user/Desktop/GitProject/Khazan_GiantHitOverlayWork_20261013/Khazan')")
a="buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"
b="""report['manifest_snapshot_module']=str(module)
candidates=[p for p in (ROOT/'Binaries/Win64').glob('UnrealEditor-Khazan*.dll') if kernel.GetModuleHandleW(p.name)]
assert len(candidates)==1,candidates
module=candidates[0]
report['manifest_module']=str(module)
report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
report['module_binding']='Actual loaded module, independent of concurrent manifest changes'
buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"""
assert s.count(a)==1;s=s.replace(a,b)
exec(compile(s,__file__,'exec'),globals())