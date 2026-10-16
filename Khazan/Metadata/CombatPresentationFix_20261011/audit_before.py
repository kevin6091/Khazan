from pathlib import Path
import json, os, traceback, unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_CLEAN_OUTPUT'])
report = {'project':str(root), 'saved':0, 'success':False}
def props(obj, names):
    values = {}
    for name in names:
        try: values[name] = str(obj.get_editor_property(name))
        except Exception as e: values[name] = {'unavailable':str(e)}
    return values
try:
    assert root == Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
    paths = ['/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack',
        '/Game/_Art/Player/Animation/InGame/DAS/FallAttack/CA_P_Kazan_DualAxeSword_Com_FallAtk',
        '/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalFront',
        '/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalBack']
    report['animations'] = {}
    exporter = unreal.ObjectExporterT3D()
    for path in paths:
        asset = unreal.load_asset(path); assert asset, path
        report['animations'][path] = props(asset, ['rate_scale','blend_in','blend_out','blend_out_trigger_time',
            'enable_auto_blend_out','composite_sections','slot_anim_tracks','notifies','enable_root_motion','root_motion_root_lock'])
        task=unreal.AssetExportTask();task.object=asset;task.filename=str(out/(asset.get_name()+'.t3d'))
        task.automated=True;task.prompt=False;task.exporter=exporter
        unreal.Exporter.run_asset_export_task(task)
    world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment');assert world
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    report['actor_count']=len(actors);report['environment']=[]
    for actor in actors:
        if isinstance(actor,unreal.KZSnowDeformation):
            report['snow']={'actor':actor.get_path_name(),'settings':props(actor,
                ['surface_contact_samples','foot_compression','weapon_compression','foot_radius_cm',
                'weapon_radius_cm','surface_tag','field_resolution','texel_size_cm'])}
        if isinstance(actor,(unreal.SkyLight,unreal.DirectionalLight,unreal.ExponentialHeightFog,unreal.PostProcessVolume)):
            row={'actor':actor.get_path_name(),'label':actor.get_actor_label(),'class':actor.get_class().get_name(), 'components':[]}
            for comp in actor.get_components_by_class(unreal.ActorComponent):
                if isinstance(comp,unreal.LightComponentBase):
                    row['components'].append({'name':comp.get_name(),'values':props(comp,['intensity','light_color',
                        'indirect_lighting_intensity','volumetric_scattering_intensity','cast_shadows',
                        'shadow_bias','shadow_slope_bias','shadow_sharpen','contact_shadow_length',
                        'source_angle','source_soft_angle','lower_hemisphere_is_black',
                        'lower_hemisphere_color','real_time_capture','source_type','cubemap'])})
                if isinstance(comp,unreal.ExponentialHeightFogComponent):
                    row['components'].append({'name':comp.get_name(),'values':props(comp,
                        ['fog_density','fog_height_falloff','fog_inscattering_color','volumetric_fog',
                         'volumetric_fog_scattering_distribution','volumetric_fog_albedo'])})
            report['environment'].append(row)
    report['dirty_maps']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    report['dirty_content']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report['success']=True
except Exception:
    report['error']=traceback.format_exc();unreal.log_error(report['error'])
(out/'Before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
