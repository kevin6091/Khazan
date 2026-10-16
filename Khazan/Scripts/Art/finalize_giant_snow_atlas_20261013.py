"""Per-renderer atlas UV recovery, snow palette and exact debug-axis suppression."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';lib=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();fx=u.FXConverterUtilitiesLibrary
mat=u.load_asset(root+'/Materials/M_KZGiant_SoftSnowMist');assert mat
nodes=list(lib.get_material_expressions(mat));alpha=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom))
cols=lib.create_material_expression(mat,u.MaterialExpressionScalarParameter);cols.set_editor_property('parameter_name','AtlasColumns');cols.set_editor_property('default_value',1)
rows=lib.create_material_expression(mat,u.MaterialExpressionScalarParameter);rows.set_editor_property('parameter_name','AtlasRows');rows.set_editor_property('default_value',1)
inputs=list(alpha.get_editor_property('inputs'))
for name in ['Columns','Rows']:
    i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
alpha.set_editor_property('inputs',inputs)
# UE ParticleSpriteVertexFactory.ush lines562/319 supplies atlas-space UV0.
# Recover each frame's card UV; a plain UV0 radial mask leaves hard quad edges.
alpha.set_editor_property('code','float2 uv=frac(UV*float2(max(Columns,1.0),max(Rows,1.0))); float2 p=uv*2.0-1.0; return pow(saturate(1.0-dot(p,p)),2.0)*saturate(Density)*saturate(ParticleAlpha);')
assert lib.connect_material_expressions(cols,'',alpha,'Columns');assert lib.connect_material_expressions(rows,'',alpha,'Rows')
pc=next(n for n in nodes if isinstance(n,u.MaterialExpressionParticleColor))
tint=lib.create_material_expression(mat,u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','SnowTint');tint.set_editor_property('default_value',u.LinearColor(.68,.74,.8,1))
weight=lib.create_material_expression(mat,u.MaterialExpressionScalarParameter);weight.set_editor_property('parameter_name','ParticleTintInfluence');weight.set_editor_property('default_value',.25)
mix=lib.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
assert lib.connect_material_expressions(tint,'RGB',mix,'A');assert lib.connect_material_expressions(pc,'RGB',mix,'B');assert lib.connect_material_expressions(weight,'',mix,'Alpha');assert lib.connect_material_property(mix,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
u.EditorAssetLibrary.set_metadata_tag(mat,'KZGiantVFXRecovery','Native atlas UV0 -> per-card UV; source R density/PC alpha. TEMP SnowTint .68/.74/.8 and ParticleTintInfluence .25 replace unavailable source winter scene-colour shader. Not original shader parity.')
assert not list(lib.recompile_material(mat));assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
report={'atlas_bindings':[],'technical_renderers_hidden':[],'temporary_visual_values':{'SnowTint':[.68,.74,.8],'ParticleTintInfluence':.25}}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
for asset in u.EditorAssetLibrary.list_assets(root+'/Particles',recursive=True)+u.EditorAssetLibrary.list_assets(root+'/OriginalObjects',recursive=True):
    ps=u.load_asset(asset)
    if not isinstance(ps,u.ParticleSystem):continue
    changed=False
    for e in fx.get_cascade_system_emitters(ps):
        lod=fx.get_cascade_emitter_lod_level(e,0);req=fx.get_lod_level_required_module(lod);m=req.get_editor_property('Material')
        if not m:continue
        if m.get_name()=='Base_Axis':
            assert len(lod.get_path_name())<256
            u.SystemLibrary.execute_console_command(world,'SETNOPEC "'+lod.get_path_name()+'" bEnabled False');assert not fx.get_lod_level_is_enabled(lod);changed=True
            report['technical_renderers_hidden'].append({'lod':lod.get_path_name(),'material':'Base_Axis'});continue
        if m!=mat and not(isinstance(m,u.MaterialInstanceConstant) and m.get_editor_property('parent')==mat):continue
        h=max(req.get_editor_property('SubImages_Horizontal'),1);v=max(req.get_editor_property('SubImages_Vertical'),1)
        name='MI_Atlas_'+m.get_name()+'_'+str(h)+'x'+str(v);path=root+'/Materials/'+name
        mi=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else at.duplicate_asset(name,root+'/Materials',m) if isinstance(m,u.MaterialInstanceConstant) else at.create_asset(name,root+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(mi,mat);lib.set_material_instance_scalar_parameter_value(mi,'AtlasColumns',h);lib.set_material_instance_scalar_parameter_value(mi,'AtlasRows',v)
        lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
        req.set_editor_property('Material',mi);changed=True
        report['atlas_bindings'].append({'required':req.get_path_name(),'grid':[h,v],'material':mi.get_path_name()})
    if changed:assert u.EditorAssetLibrary.save_loaded_asset(ps,only_if_is_dirty=False)
(out/'SnowAtlas.json').write_text(json.dumps(report,indent=2),encoding='utf-8');u.log('GIANT_SNOW_ATLAS_COMPLETE '+str(len(report['atlas_bindings'])))
