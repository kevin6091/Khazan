"""Owned projector shader repair; source clock, geometry and cleanup stay intact."""
from pathlib import Path
import json, os, unreal as u

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
probe=json.loads((main/'Metadata/GiantVFX_20261013/SnowDecalProbe01/SnowDecalProbe.json').read_text(encoding='utf-8'))
assert len(probe['rows'])==1 and len(probe['materials'])==1
entry=probe['materials'][0]
folder='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials'
assert not u.EditorAssetLibrary.does_asset_exist(folder+'/M_KZGiant_BoundedSnowDecal')
parent=tools.duplicate_asset('M_KZGiant_BoundedSnowDecal',folder,u.load_asset(entry['parent']))
mi=tools.duplicate_asset('MI_KZGiant_BoundedSnowDecal',folder,u.load_asset(entry['material']))
lib.set_material_instance_parent(mi,parent)
old_alpha=lib.get_material_property_input_node(parent,u.MaterialProperty.MP_OPACITY)
old_output=lib.get_material_property_input_node_output_name(parent,u.MaterialProperty.MP_OPACITY)
old_colour=lib.get_material_property_input_node(parent,u.MaterialProperty.MP_EMISSIVE_COLOR)
colour_output=lib.get_material_property_input_node_output_name(parent,u.MaterialProperty.MP_EMISSIVE_COLOR)
assert old_alpha and old_colour
# The cooked distortion graph is unavailable. This is an explicit, editable
# frost-mark adapter: suppress emission and retain source temporal alpha/colour.
parent.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
assert lib.connect_material_property(old_colour,colour_output,u.MaterialProperty.MP_BASE_COLOR)
zero=lib.create_material_expression(parent,u.MaterialExpressionConstant);zero.set_editor_property('r',0)
assert lib.connect_material_property(zero,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
uv=lib.create_material_expression(parent,u.MaterialExpressionTextureCoordinate)
noise=lib.create_material_expression(parent,u.MaterialExpressionTextureSampleParameter2D)
noise.set_editor_property('parameter_name','KZGiantDecalDensity')
texture=u.load_asset('/Game/_Art/Effects/Shared/Textures/MonsterHuman/FT_Dirt_Tex_01');assert texture
noise.set_editor_property('texture',texture)
noise.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
assert lib.connect_material_expressions(uv,'',noise,'UVs')
strength=lib.create_material_expression(parent,u.MaterialExpressionScalarParameter)
strength.set_editor_property('parameter_name','KZGiantDecalOpacity')
strength.set_editor_property('default_value',.12)
alpha=lib.create_material_expression(parent,u.MaterialExpressionCustom)
inputs=[]
for name in ['UV','Density','OriginalAlpha','Strength']:
    pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
alpha.set_editor_property('inputs',inputs)
alpha.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
alpha.set_editor_property('code','float2 p=UV*2.0-1.0; float support=pow(saturate(1.0-dot(p,p)),2.0); return support*saturate(Density)*saturate(OriginalAlpha)*saturate(Strength);')
alpha.set_editor_property('description','TEMP: source FT_Dirt_Tex_01.R with inward radial support; KZGiantDecalOpacity .12 is editable presentation tuning, not recovered shader parity. Original temporal alpha retained.')
for node,output,pin in [(uv,'','UV'),(noise,'R','Density'),(old_alpha,old_output,'OriginalAlpha'),(strength,'','Strength')]:
    assert lib.connect_material_expressions(node,output,alpha,pin)
assert lib.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
assert not list(lib.recompile_material(parent))
lib.update_material_instance(mi)
assert u.EditorAssetLibrary.save_loaded_asset(parent,only_if_is_dirty=False)
assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
row=probe['rows'][0];seq=u.load_asset(row['asset']);effect=u.load_object(None,row['effect'])
assert effect and effect.get_editor_property('decal_material').get_path_name()==entry['material']
clock=[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(seq)]
effect.set_editor_property('decal_material',mi)
assert [e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(seq)]==clock
assert u.EditorAssetLibrary.save_loaded_asset(seq,only_if_is_dirty=False)
(out/'SnowDecalRepair.json').write_text(json.dumps({'source_material':entry['material'],'material':mi.get_path_name(),'parent':parent.get_path_name(),'changed_sequence':row['asset'],'effect':row['effect'],'event_clock_guid':clock,'changed_fields':['DecalMaterial'],'temporary_opacity':.12,'original_texture':texture.get_path_name(),'original_roughness':.1,'source_status':'Current imported source geometry/clock and original texture/roughness retained; radial envelope and non-emissive frost appearance are an explicit TEMP adapter for unrecovered distortion graph'},indent=2),encoding='utf-8')
