"""Restore source blend contracts; soften the source untextured spark cards."""
from pathlib import Path
import json, os, unreal as u
MAIN=Path(os.environ['KZ_PARRY_MAIN']);ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_PARRY_OUT'])
assert ROOT==MAIN.parent.parent/'Khazan_ParryWork_20261012/Khazan'
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/';LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
R={'status':'running','materials':[],'reason':'Black disc was the unsaved QA DefaultPawn, confirmed by hidden_fixture_pawns and AlphaPreview06. Remove unnecessary blend/visibility repairs; keep continuous edge alpha.'}
for name in ['FMI_fluid_A_133','FMI_fluid_A_11','FMI_fluid_A_13','FMI_fluid_A_15','FMI_Subuv_Atlas_B_01']:
    folder='Fluid' if 'fluid' in name else 'SubUV'
    original=u.load_asset('/Game/_Art/Effects/Shared/Materials/'+folder+'/MI/'+name);mi=u.load_asset(BASE+name)
    assert original and mi
    mi.set_editor_property('base_property_overrides',original.get_editor_property('base_property_overrides'))
    LIB.update_material_instance(mi)
    EAL.set_metadata_tag(mi,'KZParryRefractionAdapter','REMOVED: black sphere was QA DefaultPawn, not a particle material fault. Source base-property overrides restored.')
    assert EAL.save_loaded_asset(mi,only_if_is_dirty=False)
    R['materials'].append({'path':mi.get_path_name(),'source_overrides':mi.get_editor_property('base_property_overrides').export_text()})
fluid=u.load_asset(BASE+'FM_fluid_A');nodes=list(LIB.get_material_expressions(fluid))
gate=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'TEMP stripped-refraction' in str(n.get_editor_property('description')))
terminal=LIB.get_material_property_input_node(fluid,u.MaterialProperty.MP_OPACITY)
base=next(n for n in nodes if isinstance(n,u.MaterialExpressionMultiply) and n.get_name()=='MaterialExpressionMultiply_0')
assert any(isinstance(n,u.MaterialExpressionDepthFade) for n in LIB.get_inputs_for_material_expression(fluid,base))
assert LIB.connect_material_property(base,'',u.MaterialProperty.MP_OPACITY)
LIB.delete_material_expression(fluid,terminal);LIB.delete_material_expression(fluid,gate)
assert not list(LIB.recompile_material(fluid));assert EAL.save_loaded_asset(fluid,only_if_is_dirty=False)
spark=u.load_asset(BASE+'DefaultParticle');nodes=list(LIB.get_material_expressions(spark))
edge=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'smooth particle boundary' in str(n.get_editor_property('description')))
uv=next(n for n in reversed(nodes) if isinstance(n,u.MaterialExpressionTextureCoordinate))
width=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='ParryEdgeFeatherUV')
px=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='ParryEdgeSoftnessPixels')
soft=LIB.create_material_expression(spark,u.MaterialExpressionScalarParameter,450,470)
soft.set_editor_property('parameter_name','ParrySparkSoftnessPower');soft.set_editor_property('default_value',2.0)
inputs=[]
for name in ['UV','Width','Pixels','Softness']:
    i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
edge.set_editor_property('inputs',inputs)
edge.set_editor_property('code','float2 d=min(UV,1.0-UV); float w=max(Width,max(fwidth(UV.x),fwidth(UV.y))*Pixels); float edge=smoothstep(0.0,max(w,0.00001),min(d.x,d.y)); float2 p=UV*2.0-1.0; return edge*pow(saturate(1.0-dot(p,p)),Softness);')
for n,p in [(uv,'UV'),(width,'Width'),(px,'Pixels'),(soft,'Softness')]:assert LIB.connect_material_expressions(n,'',edge,p)
EAL.set_metadata_tag(spark,'KZParrySparkAlpha','TEMP user-requested rounded soft spark card: elliptic alpha power 2; .04 inward UV / 1.25 minimum pixels. Source particle RGB/curve/size retained; no masked threshold.')
assert not list(LIB.recompile_material(spark));assert EAL.save_loaded_asset(spark,only_if_is_dirty=False)
R['status']='passed';R['temporary_spark_alpha_power']=2.0
(OUT/'FinalAlpha.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
