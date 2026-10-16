"""Correct explicit FColor RGB channels and soften the rejected dark candidate."""
from pathlib import Path
import hashlib,json,os
import unreal as u
main=Path(os.environ['KZ_HM_COLOUR_MAIN']);root=Path(u.Paths.project_dir()).resolve()
assert root==main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=Path(os.environ['KZ_HM_COLOUR_OUT'])
path='/Game/Maps/L_HeinMach_Environment';file=root/'Content/Maps/L_HeinMach_Environment.umap'
before=hashlib.sha256(file.read_bytes()).hexdigest()
world=u.EditorLoadingAndSavingUtils.load_map(path);assert world
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
# TEMP second visual candidate, not original lighting values.
policy={'sun_lux':1800.,'sky_intensity':8.0,'exposure_bias_ev':-1.1,
        'sun_rgb_srgb':[205,225,255],'sky_rgb_srgb':[195,218,255],
        'volumetric_fog_emissive_linear':[.025,.04,.06]}
changes=[];fog=[]
for actor in actors:
    for component in actor.get_components_by_class(u.DirectionalLightComponent):
        component.set_editor_property('intensity',policy['sun_lux'])
        r,g,b=policy['sun_rgb_srgb'];component.set_editor_property('light_color',u.Color(r=r,g=g,b=b,a=255))
        colour=component.get_editor_property('light_color');assert colour.r==r and colour.b==b
        changes.append({'actor':actor.get_actor_label(),'intensity':component.get_editor_property('intensity'),'colour':colour.export_text()})
    for component in actor.get_components_by_class(u.SkyLightComponent):
        component.set_editor_property('intensity',policy['sky_intensity'])
        r,g,b=policy['sky_rgb_srgb'];component.set_editor_property('light_color',u.Color(r=r,g=g,b=b,a=255))
        colour=component.get_editor_property('light_color');assert colour.r==r and colour.b==b
        component.recapture_sky()
        changes.append({'actor':actor.get_actor_label(),'intensity':component.get_editor_property('intensity'),'colour':colour.export_text()})
    if isinstance(actor,u.PostProcessVolume) and actor.get_actor_label().startswith('Art_NaturalLighting_'):
        settings=actor.get_editor_property('settings')
        blendables=settings.get_editor_property('weighted_blendables').get_editor_property('array')
        for item in blendables:
            obj=item.get_editor_property('object');assert obj and '/_RND_ArcanePP/' in obj.get_path_name(),obj
            for material in (obj,obj.get_editor_property('parent')):
                task=u.AssetExportTask();task.object=material;task.filename=str(out/(material.get_name()+'.t3d'))
                task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
                assert u.Exporter.run_asset_export_task(task)
            changes.append({'actor':actor.get_actor_label(),'removed_blendable':obj.get_path_name(),
                            'before_weight':item.get_editor_property('weight')})
        settings.set_editor_property('weighted_blendables',u.WeightedBlendables())
        settings.set_editor_property('auto_exposure_bias',policy['exposure_bias_ev'])
        actor.set_editor_property('settings',settings)
    for component in actor.get_components_by_class(u.ExponentialHeightFogComponent):
        item={'actor':actor.get_actor_label()}
        item['before_volumetric_emissive']=component.get_editor_property('volumetric_fog_emissive').export_text()
        colour=policy['volumetric_fog_emissive_linear']
        component.set_editor_property('volumetric_fog_emissive',u.LinearColor(r=colour[0],g=colour[1],b=colour[2],a=1))
        for key in ('fog_density','fog_inscattering_luminance','fog_max_opacity','fog_height_falloff','start_distance',
                    'directional_inscattering_luminance','volumetric_fog_emissive'):
            try:
                value=component.get_editor_property(key);item[key]=value.export_text() if hasattr(value,'export_text') else value
            except Exception:pass
        fog.append(item)
assert u.EditorLoadingAndSavingUtils.save_map(world,path)
(out/'Retune.json').write_text(json.dumps({'status':'candidate2_saved','policy_TEMP':policy,'changes':changes,'fog_read_only':fog,
    'before_sha256':before,'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print('HEIN_COLD_LIGHT_RETUNED')
