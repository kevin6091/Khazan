"""Read-only source/rendering contracts for the isolated current HeinMach map."""
from pathlib import Path
import json
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/ImportReports/HeinMachReference_20261006'
OUT.mkdir(parents=True, exist_ok=True)
LIB = unreal.MaterialEditingLibrary


def props(obj, fields):
    result = {}
    for name in fields:
        try:
            value = obj.get_editor_property(name)
            result[name] = value if isinstance(value, (float, int, str, bool)) else str(value)
        except Exception:
            pass
    return result


def main():
    world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    report = {'actor_poses': {}, 'environment': [], 'postprocess': [], 'materials': {}, 'api': {}}
    material_slots = {}
    for actor in actors:
        label = actor.get_actor_label()
        p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
        report['actor_poses'][label] = [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            for slot in range(comp.get_num_materials()):
                mat = comp.get_material(slot)
                if mat:
                    material_slots.setdefault(mat.get_path_name(), []).append(label)
        if isinstance(actor, unreal.PostProcessVolume):
            settings = actor.get_editor_property('settings')
            fields = ['scene_color_tint','color_saturation','color_contrast','color_gain',
                      'auto_exposure_min_brightness','auto_exposure_max_brightness','motion_blur_amount',
                      'motion_blur_per_object_size','scene_fringe_intensity','sharpen','weighted_blendables']
            report['postprocess'].append({'label':label, 'settings': props(settings,fields),
                                          'policy':props(actor,['unbound','priority','blend_radius','blend_weight'])})
        if label.startswith(('HM_Preview','HM_Environment')):
            components=[]
            for comp in actor.get_components_by_class(unreal.SceneComponent):
                fields=['intensity','light_color','indirect_lighting_intensity','specular_scale',
                        'source_angle','source_soft_angle','shadow_amount','cast_shadows','source_type',
                        'cubemap','real_time_capture','lower_hemisphere_color','fog_density','fog_height_falloff',
                        'fog_inscattering_luminance','fog_max_opacity','start_distance','volumetric_fog_emissive',
                        'volumetric_fog_distance','volumetric_fog_albedo','mobility']
                components.append({'class':comp.get_class().get_name(),'properties':props(comp,fields)})
            report['environment'].append({'label':label,'components':components})
    for path, labels in material_slots.items():
        if '/_Art/Player/Environment/' not in path:
            continue
        mat=unreal.load_object(None,path)
        row={'actor_count':len(labels),'examples':labels[:3], 'class':mat.get_class().get_name()}
        if isinstance(mat,unreal.MaterialInstanceConstant):
            row.update(parent=str(mat.get_editor_property('parent')),parameters={})
            for name in LIB.get_scalar_parameter_names(mat):
                row['parameters'][str(name)]=LIB.get_material_instance_scalar_parameter_value(mat,name)
            row['texture_parameters']={str(name):str(LIB.get_material_instance_texture_parameter_value(mat,name))
                                       for name in LIB.get_texture_parameter_names(mat)}
            row['vector_parameters']={str(name):str(LIB.get_material_instance_vector_parameter_value(mat,name))
                                      for name in LIB.get_vector_parameter_names(mat)}
        report['materials'][path]=row
    for name in ('M_HM_RegionalLook','M_HM_SourceSnow','M_HM_SourceDust'):
        mat=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/'+name)
        report[name]=props(mat,['blendable_location','blendable_priority','disable_pre_exposure_scale',
                               'output_translucent_velocity','translucency_pass','opacity_mask_clip_value',
                               'enable_responsive_aa'])
        report[name]['custom_code']=[n.get_editor_property('code') for n in LIB.get_material_expressions(mat)
                                    if isinstance(n,unreal.MaterialExpressionCustom)]
    system=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NS_HM_SourceSnow_TwoLayers')
    task=unreal.AssetExportTask()
    for key,value in [('object',system),('filename',str(OUT/'SnowBaseline.t3d')),
                      ('exporter',unreal.ObjectExporterT3D()),('automated',True),('prompt',False)]:
        task.set_editor_property(key,value)
    unreal.Exporter.run_asset_export_task(task)
    usd=unreal.load_asset('/USDCore/Materials/UsdPreviewSurface')
    task.set_editor_property('object',usd)
    task.set_editor_property('filename',str(OUT/'UsdPreviewSurface.t3d'))
    unreal.Exporter.run_asset_export_task(task)
    report['USD_root']={str(p):str(LIB.get_material_property_input_node(usd,p)) for p in
                        (unreal.MaterialProperty.MP_NORMAL,unreal.MaterialProperty.MP_ROUGHNESS,
                         unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)}
    report['bounds']={a.get_actor_label():str(a.get_actor_bounds(False)) for a in actors
                      if isinstance(a,unreal.PostProcessVolume)}
    for name in ('NiagaraEmitterConversionContext','NiagaraScriptConversionContext','FXConverterUtilitiesLibrary'):
        cls=getattr(unreal,name)
        report['api'][name]={n:getattr(getattr(cls,n),'__doc__','') for n in dir(cls)
                            if any(t in n for t in ('emitter','module','parameter','script_context')) and not n.startswith('_')}
    (OUT/'BaselineProbe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('KZ_HEINMACH_REFERENCE_PROBE_PASSED')


main()
