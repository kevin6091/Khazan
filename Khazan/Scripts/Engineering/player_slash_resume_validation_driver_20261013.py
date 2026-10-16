"""Owned resumed validation binds the loaded DLL despite concurrent manifest writes."""
from pathlib import Path
import os

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out = os.environ['KZ_MONSTER_PHYSICS_OUT']
os.environ.update(KZ_MONSTER_REPAIR_OUT=out, KZ_MONSTER_REPAIR_MODE='rhi',
                  KZ_MONSTER_REPAIR_TEST=os.environ.get('KZ_SLASH_TEST', 'Khazan.CombatEffect.PIE'))
source = (main / 'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
old = "buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"
new = """report['manifest_snapshot_module']=str(module)
candidates=[p for p in (ROOT/'Binaries/Win64').glob('UnrealEditor-Khazan*.dll') if kernel.GetModuleHandleW(p.name)]
assert len(candidates)==1, candidates
module=candidates[0]
report['manifest_module']=str(module)
report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
report['module_binding']='Actual loaded process module; manifest snapshot may change during other builds'
buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"""
assert source.count(old) == 1
source = source.replace(old, new, 1)
exec(compile(source, __file__, 'exec'), globals())
