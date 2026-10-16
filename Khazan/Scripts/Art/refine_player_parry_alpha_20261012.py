"""Local recovery fix: black non-emissive refraction pixels cannot occlude."""
from pathlib import Path
import json, os, unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_PARRY_MAIN']);OUT=Path(os.environ['KZ_PARRY_OUT'])
assert ROOT==MAIN.parent.parent/'Khazan_ParryWork_20261012/Khazan'
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary;BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/'
R={'status':'running','materials':[],'tuning':'TEMP presentation adapter: inward feather at least 1.25 pixels; black emissive visibility gate for stripped refraction recovery. Original texture/curve/tint kept.'}
for name in ['FM_fluid_A','FM_Subuv_Atlas_B','DefaultParticle']:
    m=u.load_asset(BASE+name);assert m
    nodes=list(LIB.get_material_expressions(m))
    custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'smooth particle boundary' in str(n.get_editor_property('description')))
    uv=next(n for n in reversed(nodes) if isinstance(n,u.MaterialExpressionTextureCoordinate))
    # Existing edge custom input links are explicitly reconnected after inputs change.
    width=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='ParryEdgeFeatherUV')
    px=LIB.create_material_expression(m,u.MaterialExpressionScalarParameter,400,380);px.set_editor_property('parameter_name','ParryEdgeSoftnessPixels');px.set_editor_property('default_value',1.25)
    ins=[]
    for n in ['UV','Width','Pixels']:
        x=u.CustomInput();x.set_editor_property('input_name',n);ins.append(x)
    custom.set_editor_property('inputs',ins)
    custom.set_editor_property('code','float2 d=min(UV,1.0-UV); float w=max(Width,max(fwidth(UV.x),fwidth(UV.y))*Pixels); return smoothstep(0.0,max(w,0.00001),min(d.x,d.y));')
    for n,p in [(uv,'UV'),(width,'Width'),(px,'Pixels')]:assert LIB.connect_material_expressions(n,'',custom,p)
    if name=='FM_fluid_A':
        alpha=LIB.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY);aout=LIB.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY)
        color=LIB.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR);cout=LIB.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
        gate=LIB.create_material_expression(m,u.MaterialExpressionCustom,880,350);inp=u.CustomInput();inp.set_editor_property('input_name','Color');gate.set_editor_property('inputs',[inp])
        gate.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
        gate.set_editor_property('description','TEMP stripped-refraction recovery: zero-emissive black pixels remain transparent')
        gate.set_editor_property('code','return saturate(max(Color.r,max(Color.g,Color.b)));')
        assert LIB.connect_material_expressions(color,cout,gate,'Color')
        mul=LIB.create_material_expression(m,u.MaterialExpressionMultiply,1120,100)
        assert LIB.connect_material_expressions(alpha,aout,mul,'A');assert LIB.connect_material_expressions(gate,'',mul,'B')
        assert LIB.connect_material_property(mul,'',u.MaterialProperty.MP_OPACITY)
    errs=list(LIB.recompile_material(m));assert not errs,errs
    EAL.set_metadata_tag(m,'KZParryAlphaRefinement',R['tuning']);assert EAL.save_loaded_asset(m,only_if_is_dirty=False)
    R['materials'].append({'path':m.get_path_name(),'errors':errs})
R['status']='passed';(OUT/'AlphaRefinement.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
