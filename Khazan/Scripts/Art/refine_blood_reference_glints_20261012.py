"""Remove the large white forward-lighting glint seen in the actual hit-surface review."""
from pathlib import Path
import unreal,os,json,traceback
root=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(root)
out=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);d={'status':'running'}
try:
    m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodFluid');assert m
    lib=unreal.MaterialEditingLibrary;nodes=lib.get_material_expressions(m)
    rough=[n for n in nodes if isinstance(n,unreal.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='BloodRoughness'];assert len(rough)==1
    rough[0].set_editor_property('default_value',.28)
    spec=[n for n in nodes if isinstance(n,unreal.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='BloodSpecular'];assert len(spec)<=1
    p=spec[0] if spec else lib.create_material_expression(m,unreal.MaterialExpressionScalarParameter,-500,560)
    p.set_editor_property('parameter_name','BloodSpecular');p.set_editor_property('default_value',.1)
    assert lib.connect_material_property(p,'',unreal.MaterialProperty.MP_SPECULAR)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    d.update(status='passed',saved=m.get_path_name(),temporary={'BloodRoughness':.28,'BloodSpecular':.1},reason='The capsule surface makes the spray visible; a near fire exposed an oversized white specular hotspot unlike the supplied dark liquid. Retain small wet highlights without changing scene lighting.')
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(out/'GlintRevision.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
