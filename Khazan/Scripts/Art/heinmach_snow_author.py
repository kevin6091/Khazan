"""Add smooth, contact-driven snow to the isolated HeinMach terrain; preserve base graphs."""
from pathlib import Path
import hashlib
import json
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006'
DEST='/Game/_Art/Player/Environment/Rendering/HeinMachSnow'
LIB=unreal.MaterialEditingLibrary
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()

def node(mat,cls,x=0,y=0,**values):
    n=LIB.create_material_expression(mat,cls,x,y)
    for k,v in values.items():n.set_editor_property(k,v)
    return n

def link(a,b,pin='',output=''):
    assert LIB.connect_material_expressions(a,output,b,pin),(a,b,pin,output)

def scalar(mat,name,value):
    return node(mat,unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)

def mul(mat,a,b):
    n=node(mat,unreal.MaterialExpressionMultiply);link(a,n,'A');link(b,n,'B');return n

def add(mat,values):
    result=values[0]
    for value in values[1:]:
        n=node(mat,unreal.MaterialExpressionAdd);link(result,n,'A');link(value,n,'B');result=n
    return result

def custom(mat,names,code,kind=unreal.CustomMaterialOutputType.CMOT_FLOAT3):
    n=node(mat,unreal.MaterialExpressionCustom,output_type=kind,code=code)
    inputs=[]
    for name in names:
        i=unreal.CustomInput();i.set_editor_property('input_name',unreal.Name(name));inputs.append(i)
    n.set_editor_property('inputs',inputs)
    return n

def own_duplicate(source,name,folder):
    path=folder+'/'+name
    if unreal.EditorAssetLibrary.does_asset_exist(path):return unreal.load_asset(path)
    asset=TOOLS.duplicate_asset(name,folder,source)
    assert asset
    return asset

def verify_displacement(material):
    task=unreal.AssetExportTask();task.object=material;task.exporter=unreal.ObjectExporterT3D()
    task.filename=str(OUT/(material.get_name()+'.t3d'));task.automated=True;task.prompt=False
    assert unreal.Exporter.run_asset_export_task(task)
    output=Path(task.filename).read_text(encoding='utf-8-sig')
    assert 'Displacement=(Expression=' in output,'Displacement input was not set'

FIELD_CODE='''
float2 windowUV = (World.xy-Transform.xy)/max(Transform.z,1.0);
float2 uv = frac(World.xy/max(Transform.z,1.0));
float4 field = Texture2DSampleLevel(Field,FieldSampler,uv,0);
float2 edge = min(windowUV,1.0-windowUV)*Transform.z/max(Transform.w,0.01);
float inside = saturate(min(edge.x,edge.y)/16.0);
inside = inside*inside*(3.0-2.0*inside);
float altitude = 1.0-smoothstep(HeightTolerance*0.75,HeightTolerance,abs(World.z-field.b));
float valid = field.a*inside*altitude;
float compression = saturate(field.r)*valid;
float rim = saturate(field.g)*valid;
return float3(SnowHeight*(1.0-compression)+RimHeight*rim*SnowMask,compression*SnowMask,rim*SnowMask);
'''
NORMAL_CODE='''
float3 dx=ddx(World), dy=ddy(World);
float determinant=dx.x*dy.y-dx.y*dy.x;
float2 slope=0.0;
if (abs(determinant)>0.00001)
{
    float dhx=ddx(Height), dhy=ddy(Height);
    slope=float2(dhx*dy.y-dhy*dx.y,dhy*dx.x-dhx*dy.x)/determinant;
}
return normalize(BaseNormal+float3(-slope,0.0));
'''

def build_material(group,plan):
    source=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachTerrain/Materials/M_HM_SourceWeighted_'+group)
    material=own_duplicate(source,'M_HM_Deformable_'+group,DEST+'/Materials')
    version=unreal.EditorAssetLibrary.get_metadata_tag(material,'SnowDeformationVersion')
    if version in ('1','2','3'):
        expressions=LIB.get_material_expressions(material)
        field_height=next(n for n in expressions if isinstance(n,unreal.MaterialExpressionCustom) and
            'float4 field = Texture2DSampleLevel' in n.get_editor_property('code'))
        transform=next(n for n in expressions if isinstance(n,unreal.MaterialExpressionVectorParameter) and
            str(n.get_editor_property('parameter_name'))=='HM_FieldTransform')
        field_height.set_editor_property('code',FIELD_CODE)
        link(transform,field_height,'Transform','RGBA')
        expression=next(n for n in LIB.get_material_expressions(material) if
            isinstance(n,unreal.MaterialExpressionDivide) and n.get_editor_property('const_b') in (18.0,75.0))
        unreal.KZSnowDeformation.configure_material_displacement(material,expression)
        unreal.EditorAssetLibrary.set_metadata_tag(material,'SnowDeformationVersion','3' if version=='3' else '2')
        LIB.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
        verify_displacement(material)
        return material
    # The duplicate starts with the exact currently delivered graph and parameter values.
    original={p:LIB.get_material_property_input_node(material,p) for p in (
      unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_NORMAL,unreal.MaterialProperty.MP_ROUGHNESS)}
    weights={str(n.get_editor_property('parameter_name')):n for n in LIB.get_material_expressions(material)
             if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D) and
             str(n.get_editor_property('parameter_name')).startswith('Weight_')}
    channel_weights={}
    for name,sample in weights.items():
        n=node(material,unreal.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False)
        link(sample,n,output='R');channel_weights[name[7:]]=n
    total=add(material,[n for k,n in channel_weights.items() if k!='Puddle'])
    max_total=node(material,unreal.MaterialExpressionMax,const_b=0.00001);link(total,max_total,'A')
    snow=[];height=[]
    for layer in plan['layers']:
        name=layer['layer_name']
        if 'Snow' not in layer['textures']['diffuse']['object_name'] or name not in channel_weights:continue
        weight=channel_weights[name];snow.append(weight)
        depth=7.5 if name=='DeepSnow2' else (15.0 if name=='DeepSnow' else 4.0)
        # 15/7.5 reuse source displacement coefficients as native cm; 4 is temporary thin snow.
        height.append(mul(material,weight,scalar(material,'SnowHeightCm_'+name,depth)))
    snow_mask=node(material,unreal.MaterialExpressionDivide);link(add(material,snow),snow_mask,'A');link(max_total,snow_mask,'B')
    snow_height=node(material,unreal.MaterialExpressionDivide);link(add(material,height),snow_height,'A');link(max_total,snow_height,'B')
    world=node(material,unreal.MaterialExpressionWorldPosition,
               world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    transform=node(material,unreal.MaterialExpressionVectorParameter,parameter_name='HM_FieldTransform',
                   default_value=unreal.LinearColor(0,0,4096,2))
    field=node(material,unreal.MaterialExpressionTextureObjectParameter,parameter_name='HM_SnowField',
               texture=unreal.load_asset('/Engine/EngineResources/Black'),
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    field_height=custom(material,['World','Transform','Field','SnowHeight','SnowMask','RimHeight','HeightTolerance'],FIELD_CODE)
    for name,value in [('World',world),('Transform',transform),('Field',field),('SnowHeight',snow_height),
                       ('SnowMask',snow_mask),('RimHeight',scalar(material,'SnowRimHeightCm_Temporary',2.5)),
                       ('HeightTolerance',scalar(material,'HM_LayerHeightToleranceCm',32.0))]:link(value,field_height,name)
    link(transform,field_height,'Transform','RGBA')
    height_channel=node(material,unreal.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False)
    link(field_height,height_channel)
    compression=node(material,unreal.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False)
    link(field_height,compression)
    # Transform the existing source tangent normal into WS before adding the height derivative.
    base_world=node(material,unreal.MaterialExpressionTransform,
      transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
      transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    link(original[unreal.MaterialProperty.MP_NORMAL],base_world)
    normal=custom(material,['World','Height','BaseNormal'],NORMAL_CODE)
    for name,value in [('World',world),('Height',height_channel),('BaseNormal',base_world)]:link(value,normal,name)
    material.set_editor_property('tangent_space_normal',False)
    LIB.connect_material_property(normal,'',unreal.MaterialProperty.MP_NORMAL)
    color=custom(material,['Base','Compression','Darkening'],
       'return Base*(1.0-saturate(Compression)*Darkening);')
    for name,value in [('Base',original[unreal.MaterialProperty.MP_BASE_COLOR]),('Compression',compression),
                       ('Darkening',scalar(material,'SnowCompactionDarkening_Temporary',0.06))]:link(value,color,name)
    LIB.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=custom(material,['Base','Compression','Adjustment'],
       'return saturate(Base+Compression*Adjustment);',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    for name,value in [('Base',original[unreal.MaterialProperty.MP_ROUGHNESS]),('Compression',compression),
                       ('Adjustment',scalar(material,'SnowCompactionRoughness_Temporary',0.08))]:link(value,rough,name)
    LIB.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    displacement=node(material,unreal.MaterialExpressionDivide,const_b=18.0);link(height_channel,displacement,'A')
    material.set_editor_property('enable_tessellation',True)
    scaling=material.get_editor_property('displacement_scaling')
    scaling.set_editor_property('magnitude',0.18);scaling.set_editor_property('center',0.0)
    material.set_editor_property('displacement_scaling',scaling)
    # MP_Displacement is hidden from UE Python's enum; use the native owned input.
    unreal.KZSnowDeformation.configure_material_displacement(material,displacement)
    LIB.recompile_material(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material,'SnowDeformationVersion','2')
    unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    verify_displacement(material)
    return material

def main():
    world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    def pose(a):
        p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
        return [p.x,p.y,p.z,r.roll,r.pitch,r.yaw,s.x,s.y,s.z]
    before={a.get_path_name():pose(a) for a in actors}
    plans=json.loads((MAIN/'Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002/HeinMachTerrainPlan.json').read_text(encoding='utf-8-sig'))
    materials={p['group']:build_material(p['group'],p) for p in plans}
    mesh_subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    changes=[];meshes={}
    original_paths={r['actor']:r['mesh'] for r in json.loads((OUT/'Topology.json').read_text(encoding='utf-8'))['terrain']}
    for actor in actors:
        if not actor.get_actor_label().startswith('HM_Landscape_'):continue
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            original=comp.static_mesh
            if not original:continue
            group=next((g for g in materials if any(comp.get_material(i) and
                any(prefix+g in comp.get_material(i).get_name() for prefix in ('SourceWeighted_','Deformable_'))
                for i in range(comp.get_num_materials()))),None)
            if not group:continue
            key=original_paths.get(actor.get_path_name(),original.get_path_name())
            assert not key.startswith(DEST+'/'),'Missing original terrain provenance'
            if key not in meshes:
                suffix=hashlib.sha256(key.encode()).hexdigest()[:10]
                mesh=own_duplicate(unreal.load_asset(key),'SM_HM_Snow_'+suffix,DEST+'/Meshes')
                settings=mesh.get_editor_property('nanite_settings');settings.set_editor_property('enabled',True)
                # CMC/complex traces must keep the source surface, not a coarse Nanite proxy.
                settings.set_editor_property('fallback_relative_error',0.0)
                settings.set_editor_property('fallback_percent_triangles',1.0)
                # Actor scale100: 2^-12 object units = 0.024414cm world precision.
                settings.set_editor_property('position_precision',12)
                settings.set_editor_property('max_edge_length_factor',2.0)
                mesh_subsystem.set_nanite_settings(mesh,settings,apply_changes=True)
                unreal.KZSnowDeformation.rebuild_surface_collision(mesh)
                for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,materials[group])
                unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
                meshes[key]=mesh
            comp.set_static_mesh(meshes[key])
            for i in range(comp.get_num_materials()):comp.set_material(i,materials[group])
            tags=list(comp.get_editor_property('component_tags'))
            if 'HeinMachSnowSurface' not in [str(t) for t in tags]:tags.append(unreal.Name('HeinMachSnowSurface'))
            comp.set_editor_property('component_tags',tags)
            changes.append({'actor':actor.get_path_name(),'old_mesh':key,'new_mesh':meshes[key].get_path_name(),'group':group})
    cls=unreal.load_class(None,'/Script/Khazan.KZSnowDeformation');assert cls
    field=next((a for a in actors if a.get_actor_label()=='HM_SnowDeformation'),None)
    if not field:
        start=next(a for a in actors if isinstance(a,unreal.PlayerStart))
        field=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(cls,start.get_actor_location())
        field.set_actor_label('HM_SnowDeformation');field.set_folder_path('HeinMach/Environment/Snow')
    changed=[{'actor':a.get_path_name(),'before':before[a.get_path_name()],'after':pose(a)}
        for a in actors if max(abs(x-y) for x,y in zip(pose(a),before[a.get_path_name()]))>0.00001]
    (OUT/'AuthoringPoseDelta.json').write_text(json.dumps(changed,indent=2),encoding='utf-8')
    assert not changed,'Existing actor pose changed: '+str(changed[:3])
    # Mesh assignment sets the Nanite usage flag after initial material creation.
    for material in materials.values():
        unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/L_HeinMach_Environment')
    (OUT/'Authoring.json').write_text(json.dumps({'success':True,'terrain_components':changes,
      'materials':[m.get_path_name() for m in materials.values()], 'new_meshes':len(meshes),
      'existing_actor_transforms_changed':0,'added_actor':field.get_path_name(),
      'isolated_project':str(ROOT)},indent=2),encoding='utf-8')
    (OUT/'AuthoringFailure.json').unlink(missing_ok=True)
    print('SNOW_AUTHORING_COMPLETE',len(changes))

if __name__=='__main__':
    try:
        main()
    except Exception:
        (OUT/'AuthoringFailure.json').write_text(json.dumps({'error':traceback.format_exc()},indent=2),encoding='utf-8')
        unreal.log_error(traceback.format_exc())
    finally:
        unreal.SystemLibrary.execute_console_command(None,'QUIT_EDITOR')
