"""Targeted saved PBR and sky sampling audit. Never save packages."""
from pathlib import Path
import json,os,traceback,unreal
OUT=Path(os.environ['KZ_LOOK_OUT']);MAIN=Path(os.environ['KZ_LOOK_MAIN'])
lib=unreal.MaterialEditingLibrary
report={'success':False,'asset_saves':0,'materials':{},'textures':{},'scene':[],'errors':[]}

def properties(obj,keys):
    values={}
    for key in keys:
        try:
            v=obj.get_editor_property(key)
            values[key]=v if isinstance(v,(bool,int,float,str)) else (v.export_text() if hasattr(v,'export_text') else str(v))
        except Exception:pass
    return values

def texture(t):
    if t and t.get_path_name() not in report['textures']:
        report['textures'][t.get_path_name()]=properties(t,['srgb','compression_settings','lod_group','mip_gen_settings','never_stream'])

def material(m):
    if not m or m.get_path_name() in report['materials']:return
    path=m.get_path_name();row={'class':m.get_class().get_name()};report['materials'][path]=row
    if isinstance(m,unreal.MaterialInstanceConstant):
        parent=m.get_editor_property('parent');row['parent']=parent.get_path_name() if parent else None
        row['overrides']=properties(m,['base_property_overrides'])
        row['scalar_parameters']={str(n):lib.get_material_instance_scalar_parameter_value(m,n) for n in lib.get_scalar_parameter_names(m)}
        row['texture_parameters']={}
        for n in lib.get_texture_parameter_names(m):
            t=lib.get_material_instance_texture_parameter_value(m,n)
            row['texture_parameters'][str(n)]=t.get_path_name() if t else None;texture(t)
        material(parent)
    elif isinstance(m,unreal.Material):
        row.update(properties(m,['blend_mode','two_sided','shading_model','use_material_attributes','is_sky']))
        row['outputs']={}
        for name in ['BASE_COLOR','METALLIC','SPECULAR','ROUGHNESS','NORMAL','AMBIENT_OCCLUSION','EMISSIVE_COLOR','OPACITY','OPACITY_MASK']:
            key=getattr(unreal.MaterialProperty,'MP_'+name)
            node=lib.get_material_property_input_node(m,key)
            row['outputs'][name]={'node':node.get_name(),'class':node.get_class().get_name(),'output':lib.get_material_property_input_node_output_name(m,key)} if node else None
        row['nodes']=[]
        for node in lib.get_material_expressions(m):
            data={'name':node.get_name(),'class':node.get_class().get_name()}
            data.update(properties(node,['parameter_name','default_value','texture','sampler_type','r','g','b','a','code','desc']))
            data['input_nodes']=[n.get_name() if n else None for n in lib.get_inputs_for_material_expression(m,node)]
            if isinstance(node,unreal.MaterialExpressionTextureSample):texture(node.get_editor_property('texture'))
            row['nodes'].append(data)

try:
    capture=json.loads((MAIN/'Metadata/SceneLook_20261012/DevBefore01/Capture.json').read_text())
    for row in capture['player_materials']:
        for p in row['materials']:material(unreal.load_asset(p))
    for level in ['/Game/Maps/DevMap','/Game/Maps/L_HeinMach_Environment']:
        world=unreal.EditorLoadingAndSavingUtils.load_map(level);assert world
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        selected=[]
        for a in actors:
            label=a.get_actor_label()
            if 'Sky' in label or 'Floor'==label:
                selected.append(a)
            if 'Sun' in label or isinstance(a,unreal.DirectionalLight):
                for c in a.get_components_by_class(unreal.DirectionalLightComponent):
                    report['scene'].append({'level':level,'actor':label,'properties':properties(c,['atmosphere_sun_light','cast_cloud_shadows','cloud_shadow_strength'])})
        if 'HeinMach' in level:
            static=[a for a in actors if a.get_components_by_class(unreal.StaticMeshComponent) and 'Sky' not in a.get_actor_label()]
            static.sort(key=lambda a:(a.get_actor_location()-unreal.Vector(12370.713034,12849.819799,312.732826)).length())
            selected+=static[:45]
            selected+=next(([a] for a in actors if a.get_actor_label().startswith('HM_Landscape_')),[])
        for a in selected:
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                mats=[c.get_material(i) for i in range(c.get_num_materials())]
                report['scene'].append({'level':level,'actor':a.get_actor_label(),'component':c.get_name(),'properties':properties(c,['cast_shadow','visible','affect_distance_field_lighting','visible_in_real_time_sky_captures']),
                    'materials':[m.get_path_name() if m else None for m in mats]})
                for m in mats:material(m)
    report['dirty_content']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report['success']=True
except Exception:report['errors'].append(traceback.format_exc());unreal.log_error(report['errors'][-1])
(OUT/'Materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report['errors']
