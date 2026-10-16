"""Replace recovered DefaultParticle preview dots only in owned giant effects."""
import unreal as u
from pathlib import Path
import os,json
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';lib=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();fx=u.FXConverterUtilitiesLibrary
name='M_KZGiant_SoftPowder';assert not u.EditorAssetLibrary.does_asset_exist(root+'/Materials/'+name)
m=at.create_asset(name,root+'/Materials',u.Material,u.MaterialFactoryNew());m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);m.set_editor_property('two_sided',True)
uv=lib.create_material_expression(m,u.MaterialExpressionTextureCoordinate);pc=lib.create_material_expression(m,u.MaterialExpressionParticleColor)
tile=lib.create_material_expression(m,u.MaterialExpressionMultiply);grid=lib.create_material_expression(m,u.MaterialExpressionConstant);grid.set_editor_property('r',1/9)
assert lib.connect_material_expressions(uv,'',tile,'A');assert lib.connect_material_expressions(grid,'',tile,'B')
tex=lib.create_material_expression(m,u.MaterialExpressionTextureSample);tex.set_editor_property('texture',u.load_asset('/Game/_Art/Effects/Shared/Textures/BBQ_Texture/SubUV/T_Smoke03_SubUV_9x9'));assert lib.connect_material_expressions(tile,'',tex,'UVs')
a=lib.create_material_expression(m,u.MaterialExpressionCustom);inputs=[]
for n in ['UV','Density','Alpha']:
    i=u.CustomInput();i.set_editor_property('input_name',n);inputs.append(i)
a.set_editor_property('inputs',inputs);a.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1);a.set_editor_property('code','float2 p=UV*2.0-1.0; return pow(saturate(1.0-dot(p,p)),2.0)*saturate(Density)*saturate(Alpha);')
for s,pin,target in [(uv,'','UV'),(tex,'R','Density'),(pc,'A','Alpha')]:assert lib.connect_material_expressions(s,pin,a,target)
fade=lib.create_material_expression(m,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',12);assert lib.connect_material_expressions(a,'',fade,'Opacity');assert lib.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
c=lib.create_material_expression(m,u.MaterialExpressionVectorParameter);c.set_editor_property('parameter_name','SnowTint');c.set_editor_property('default_value',u.LinearColor(.68,.74,.8,1));assert lib.connect_material_property(c,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
for usage in [u.MaterialUsage.MATUSAGE_PARTICLE_SPRITES,u.MaterialUsage.MATUSAGE_MESH_PARTICLES]:lib.set_material_usage(m,usage)
assert not list(lib.recompile_material(m));u.EditorAssetLibrary.set_metadata_tag(m,'KZGiantVFXRecovery','TEMP natural powder: original smoke atlas first frame (1/9 grid), bounded PC.A, soft support, snow tint .68/.74/.8, depth12cm; no original shader parity asserted.')
assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);report=[]
for asset in u.EditorAssetLibrary.list_assets(root+'/Particles',recursive=True)+u.EditorAssetLibrary.list_assets(root+'/OriginalObjects',recursive=True):
    p=u.load_asset(asset)
    if not isinstance(p,u.ParticleSystem):continue
    changed=False
    for e in fx.get_cascade_system_emitters(p):
        lod=fx.get_cascade_emitter_lod_level(e,0);req=fx.get_lod_level_required_module(lod);old=req.get_editor_property('Material')
        if old and 'DefaultParticle' in old.get_name():
            req.set_editor_property('Material',m);changed=True;report.append(req.get_path_name())
    if changed:assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
(out/'PreviewDotReplacement.json').write_text(json.dumps(report,indent=2),encoding='utf-8');u.log('GIANT_PREVIEW_DOTS_REPLACED '+str(len(report)))
