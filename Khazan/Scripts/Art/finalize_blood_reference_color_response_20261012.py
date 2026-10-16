"""Keep the supplied dark liquid tone independent of near-fire forward-lighting overexposure."""
from pathlib import Path
import unreal,os,json,traceback
root=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(root)
out=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);d={'status':'running'}
try:
    m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodFluid');assert m
    lib=unreal.MaterialEditingLibrary
    color=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_BASE_COLOR);assert color
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    assert lib.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    d.update(status='passed',saved=m.get_path_name(),response='Unlit, finite translucent atlas; existing per-pixel packed-channel color variation preserved',inactive_parameters=['BloodRoughness','BloodMetallic','BloodSpecular'],reason='The actual surface spray near the delivered fire overexposed the lit sheets. The reference requires stable dark wine blood; scene lights and original assets are preserved. Inactive wet-lighting nodes are retained because the commandlet cannot delete Python-rooted expressions safely.')
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(out/'ColorResponse.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
