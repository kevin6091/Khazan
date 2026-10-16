"""Adjust only this task's owned fluid material after the actual snow review."""
from pathlib import Path
import unreal,os,json,traceback
root=Path(unreal.Paths.project_dir()).resolve()
assert 'Khazan_GiantFallWork_20261011' in str(root)
out=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);d={'status':'running'}
try:
    m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodFluid');assert m
    nodes=[n for n in unreal.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='BloodColor']
    assert len(nodes)==1
    nodes[0].set_editor_property('default_value',unreal.LinearColor(.035,.0008,.002,1))
    unreal.MaterialEditingLibrary.recompile_material(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    d.update(status='passed',saved=m.get_path_name(),temporary_linear_rgb=[.035,.0008,.002],reason='The actual snow review was too bright red compared with the supplied dark wine blood. Density, atlas, alpha and ground material remain unchanged.')
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(out/'FinalTint.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
