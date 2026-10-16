"""Correct one live emissive audit gap and tone down the too-bright stain."""
from pathlib import Path
import hashlib,json,os
import unreal as u
main=Path(os.environ['KZ_HM_COLOUR_MAIN']);root=Path(u.Paths.project_dir()).resolve()
assert root==main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=Path(os.environ['KZ_HM_COLOUR_OUT']);lib=u.MaterialEditingLibrary;rows=[]
for path in ('/Game/VFX/03_SlashHit/Materials/M_shokW_basic','/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround'):
    material=u.load_asset(path);assert material
    file=root/('Content/'+path.removeprefix('/Game/')+'.uasset');before=hashlib.sha256(file.read_bytes()).hexdigest()
    if path.endswith('M_shokW_basic'):
        emission=lib.get_material_property_input_node(material,u.MaterialProperty.MP_EMISSIVE_COLOR);assert emission
        assert not any(isinstance(node,u.MaterialExpressionEyeAdaptationInverse) for node in lib.get_material_expressions(material))
        inverse=lib.create_material_expression(material,u.MaterialExpressionEyeAdaptationInverse)
        one=lib.create_material_expression(material,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
        names=list(lib.get_material_expression_input_names(inverse))
        assert lib.connect_material_expressions(emission,'',inverse,next(name for name in names if 'Light' in name))
        assert lib.connect_material_expressions(one,'',inverse,next(name for name in names if 'Alpha' in name))
        assert lib.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        parameters={str(node.get_editor_property('parameter_name')):node for node in lib.get_material_expressions(material)
                    if isinstance(node,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter))}
        # TEMP: the first native snow review showed a paint-like bright red.
        # Keep a red body and a small shadow readability floor, without a glow.
        parameters['BloodColor'].set_editor_property('default_value',u.LinearColor(r=.08,g=.0016,b=.003,a=1))
        parameters['BloodShadowReadabilityEmission'].set_editor_property('default_value',.04)
    assert not list(lib.recompile_material(material))
    assert u.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    rows.append({'asset':path,'before_sha256':before,'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
(out/'Polish.json').write_text(json.dumps({'status':'passed','rows':rows,
    'blood_TEMP':{'linear_rgb':[.08,.0016,.003],'shadow_readability_emission':.04}},indent=2),encoding='utf-8')
