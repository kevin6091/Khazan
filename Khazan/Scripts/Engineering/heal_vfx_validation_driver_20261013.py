"""Existing fresh-PIE native regression runner, scoped to the recovery workspace."""
from pathlib import Path
import os
MAIN=Path(__file__).resolve().parents[2]
source=(MAIN/'Scripts/Engineering/monster_physics_validation_driver_20261013.py').read_text(encoding='utf-8')
source=source.replace('Khazan_PlayerPartsWork_20261007','Khazan_HealVFXWork_20261013')
source=source.replace('KZ_MONSTER_PHYSICS_OUT','KZ_HEAL_VFX_OUT')
source=source.replace("os.environ['KZ_MONSTER_PHYSICS_TESTS'].split(',')", "os.environ.get('KZ_HEAL_VFX_TESTS','Khazan.Heal.PIE,Khazan.Combat.PlayerAttackCollision.PIE').split(',')")
source=source.replace("START=LAST=time.monotonic()", """report['shaders']=[]
for material_name in ['M_Heal_SoftGlow','M_Heal_OriginalTrail','M_Heal_CoreFresnel']:
    material=unreal.load_asset('/Game/HealVFX/Materials/'+material_name)
    errors=list(unreal.MaterialEditingLibrary.recompile_material(material))
    stats=unreal.MaterialEditingLibrary.get_statistics(material)
    row=dict(path=material.get_path_name(),errors=errors,pixel_instructions=stats.num_pixel_shader_instructions,vertex_instructions=stats.num_vertex_shader_instructions)
    report['shaders'].append(row)
    assert not errors and row['pixel_instructions']>0,row
START=LAST=time.monotonic()""")
exec(compile(source,__file__,'exec'),dict(__file__=__file__,__name__='__main__'))
