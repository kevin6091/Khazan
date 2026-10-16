"""Reference fitting on existing HeinMach owners in the isolated art project."""
from pathlib import Path
import json
import runpy
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
assert 'ArtStaging/HeinMachReference_20261006' in ROOT.as_posix(), 'Author only in isolated project'
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
ASSETS='/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
LIB=unreal.MaterialEditingLibrary
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py'))
SOURCE=CONF['MANIFEST']['HeinMach']

# Native visual fits to supplied reference photos, NOT recovered BBQ shader values.
# Grouped here so subsequent original evidence can replace them without magic numbers.
FIT={'SunLux':7000.0,'SunSourceAngleDeg':5.0,'WorldToonWeight':.08,'CharacterToonWeight':.45,
     'WorldOutlineOpacity':.04,'CharacterOutlineOpacity':.22,'ShadeSmoothness':.06,
     'ShadowFillScale':2.0,'Saturation':.55,'Contrast':.96,'Bloom':.12,
     'SpawnCountScale':.25,'NearFadeCm':150.0,'HazeWeight':.75}
TINT={'OP':(.65,.78,1,1),'Blizzard1':(.48,.70,1,1),'Blizzard2':(.75,.82,1,1),
      'Boss':(.88,.92,1,1),'Cave1':(.92,.84,.80,1),'Escape':(.88,.86,.84,1)}
HAZE_EMISSION_MIX={'OP':.2,'Blizzard1':.8,'Blizzard2':.25,'Boss':.2,'Cave1':.8,'Escape':.8}
PROFILE={209:'Blizzard1',210:'Blizzard2',211:'Boss',212:'Cave1',213:'Cave1',214:'Escape',215:'OP'}
# Native volume routing, not a recovered BBQ runtime weather-controller priority.
# Baseline OP=100 masked Blizzard1=12 in their large overlap at the entry.
PRIORITY={'OP':10.0,'Blizzard1':12.0,'Blizzard2':13.0,'Escape':30.0,'Boss':40.0,'Cave1':50.0}


def save(asset):
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False),asset.get_path_name()


def duplicate(source,target):
    result=unreal.load_asset(target)
    if not result:result=unreal.EditorAssetLibrary.duplicate_asset(source,target)
    assert result,target
    return result


def snow_scale(system):
    # The engine's EmitterHandles/VersionData are protected Python properties.
    # Use Niagara's supported EffectType scaling without replacing any graph.
    path=ASSETS+'/NET_HM_WeatherBudget'
    budget=unreal.load_asset(path)
    if budget is None:
        budget=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'NET_HM_WeatherBudget',ASSETS,unreal.NiagaraEffectType,unreal.NiagaraEffectTypeFactoryNew())
    assert budget
    setting=unreal.NiagaraEmitterScalabilitySettings()
    setting.set_editor_property('scale_spawn_count',True)
    setting.set_editor_property('spawn_count_scale',FIT['SpawnCountScale'])
    platforms=setting.get_editor_property('platforms')
    platforms.set_editor_property('quality_level_mask',31) # Engine quality bit mask, not a source tuning value.
    setting.set_editor_property('platforms',platforms)
    settings=unreal.NiagaraEmitterScalabilitySettingsArray()
    settings.set_editor_property('settings',[setting])
    budget.set_editor_property('emitter_scalability_settings',settings)
    save(budget)
    system.set_editor_property('effect_type',budget)
    save(system)
    return {'effect_type':budget.get_path_name(),'native_spawn_count_scale':FIT['SpawnCountScale'],
            'both_existing_emitters':True,'graph_rebuilt':False,'source_rate_per_second':[1250,2500],
            'native_rate_per_second':[1250*FIT['SpawnCountScale'],2500*FIT['SpawnCountScale']]}


def main():
    world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    poses={a.get_actor_label():CONF['OLD']['pose'](a) for a in actors}
    by={a.get_actor_label():a for a in actors}
    report={'native_fit':FIT,'native_tints':TINT,'source_shader_port':False,'QA_only':[],
            'modified_assets':[],'source_numeric_fields':[]}
    # Preserve a compiled legacy parent and regional MICs for temporal A/B.
    legacy=duplicate(ASSETS+'/M_HM_RegionalLook', '/Game/__HeinMachQA/M_Regional_Legacy')
    save(legacy)
    for profile in TINT:
        qa=duplicate(ASSETS+'/MI_HM_RegionalLook_'+profile,'/Game/__HeinMachQA/MI_Legacy_'+profile)
        LIB.set_material_instance_parent(qa,legacy);save(qa)
        report['QA_only'].append(qa.get_path_name())
    master=unreal.load_asset(ASSETS+'/M_HM_RegionalLook')
    master.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
    custom=next(n for n in LIB.get_material_expressions(master) if isinstance(n,unreal.MaterialExpressionCustom))
    code=custom.get_editor_property('code')
    old='if (abs(Stencil.r-252.0)<0.5 && abs(Depth.r-CustomDepth.r)<StencilDepthToleranceCm)'
    new='if (abs(Stencil.r-252.0)<0.5 && Depth.r>=CustomDepth.r-max(StencilDepthToleranceCm,CustomDepth.r*0.00002))'
    # Visible sky may leave SceneDepth at the far clear value. Test occlusion
    # against its custom depth rather than requiring those depths to be equal.
    # The relative term is native depth precision tolerance, not a BBQ parameter.
    if old in code:custom.set_editor_property('code',code.replace(old,new,1))
    assert new in custom.get_editor_property('code')
    LIB.recompile_material(master)
    save(master);report['modified_assets'].append(master.get_path_name())
    # Source bEnableSeparateTranslucency=false: retain BeforeDOF composition.
    # Disable depth/velocity writes to preserve the underlying opaque character.
    for name in ('M_HM_SourceSnow','M_HM_SourceDust'):
        mat=unreal.load_asset(ASSETS+'/'+name)
        qa=duplicate(mat.get_path_name().split('.')[0],'/Game/__HeinMachQA/'+name+'_Legacy')
        save(qa)
        mat.set_editor_property('output_translucent_velocity',False)
        mat.set_editor_property('translucency_pass',unreal.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        nodes=list(LIB.get_material_expressions(mat))
        for node in nodes:
            if isinstance(node,unreal.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name'))=='CameraFade_SourceCm':
                node.set_editor_property('default_value',FIT['NearFadeCm'])
        # Revalidate the serialized Custom inputs, including the atlas texture.
        # In the failed trial the game compiler lost Mask and used DefaultMaterial.
        color=next(n for n in nodes if isinstance(n,unreal.MaterialExpressionCustom) and 'sourceAlpha' in n.get_editor_property('code'))
        for cls,out,pin in [(unreal.MaterialExpressionTextureSample,'R','Mask'),
                            (unreal.MaterialExpressionParticleColor,'RGBA','Particle'),
                            (unreal.MaterialExpressionWorldPosition,'','World'),
                            (unreal.MaterialExpressionCameraPositionWS,'','Camera'),
                            (unreal.MaterialExpressionParticleRelativeTime,'','Age')]:
            assert LIB.connect_material_expressions(next(n for n in nodes if isinstance(n,cls)),out,color,pin),pin
        for parameter,pin in [('CameraFade_SourceCm','CameraFade'),('Radiance_Native','Radiance')]:
            node=next(n for n in nodes if isinstance(n,unreal.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))==parameter)
            assert LIB.connect_material_expressions(node,'',color,pin),pin
        opacity=LIB.get_material_property_input_node(mat,unreal.MaterialProperty.MP_OPACITY)
        # Preserve the source atlas/lifetime opacity contract. Source DepthFade
        # 10 is metadata only; its cooked active graph has not been recovered.
        fade=next((n for n in LIB.get_material_expressions(mat) if isinstance(n,unreal.MaterialExpressionDepthFade)),None)
        if isinstance(opacity,unreal.MaterialExpressionDepthFade):
            opacity=next(n for n in LIB.get_material_expressions(mat) if isinstance(n,unreal.MaterialExpressionComponentMask) and n.get_editor_property('a'))
        assert isinstance(opacity,unreal.MaterialExpressionComponentMask)
        assert LIB.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
        if fade:LIB.delete_material_expression(mat,fade)
        LIB.recompile_material(mat)
        save(mat);report['modified_assets'].append(mat.get_path_name())
    system=unreal.load_asset(ASSETS+'/NS_HM_SourceSnow_TwoLayers')
    legacy_system=duplicate(ASSETS+'/NS_HM_SourceSnow_TwoLayers','/Game/__HeinMachQA/NS_HM_LegacySnow')
    legacy_system.set_editor_property('effect_type',None)
    for emitter,renderer,material in [('Source_Flakes_Fast_Large_0','NiagaraSpriteRendererProperties_0','M_HM_SourceSnow'),
                                      ('Source_Dust_0','NiagaraSpriteRendererProperties_1','M_HM_SourceDust')]:
        obj=unreal.load_object(None,legacy_system.get_path_name()+':'+emitter+'.'+renderer)
        assert obj
        obj.set_editor_property('material',unreal.load_asset('/Game/__HeinMachQA/'+material+'_Legacy'))
    save(legacy_system)
    report['snow']=snow_scale(system)
    report['modified_assets'].append(ASSETS+'/NET_HM_WeatherBudget.NET_HM_WeatherBudget')
    report['modified_assets'].append(system.get_path_name())
    for profile in TINT:
        mi=unreal.load_asset(ASSETS+'/MI_HM_RegionalLook_'+profile)
        for name in ('WorldToonWeight','CharacterToonWeight','WorldOutlineOpacity','CharacterOutlineOpacity','ShadeSmoothness'):
            LIB.set_material_instance_scalar_parameter_value(mi,name,FIT[name])
        LIB.set_material_instance_scalar_parameter_value(mi,'HM_NativeShadowFillScale',FIT['ShadowFillScale'])
        fog=SOURCE[profile]['components']['fog']['properties']
        LIB.set_material_instance_scalar_parameter_value(mi,'HazeDensity',float(fog['FogDensity']))
        LIB.set_material_instance_scalar_parameter_value(mi,'HazeViewDistance',float(fog['VolumetricFogDistance']))
        LIB.set_material_instance_scalar_parameter_value(mi,'HazeMaxOpacity',float(fog.get('FogMaxOpacity',.6)))
        LIB.set_material_instance_scalar_parameter_value(mi,'HazeWeight',FIT['HazeWeight'])
        LIB.set_material_instance_scalar_parameter_value(mi,'NativeHazeLuminanceScale',2**(CONF['NATIVE']['CaveEV100'] if profile=='Cave1' else CONF['NATIVE']['OutdoorEV100']))
        # The source regional volumetric emissive palette is missing from the
        # single global OP fog. This depth term approximates its view contribution.
        ins=fog['FogInscatteringColor'];em=fog['VolumetricFogEmissive'];mix=HAZE_EMISSION_MIX[profile]
        col=[ins[channel]*(1-mix)+em[channel]*mix for channel in ('R','G','B')]
        LIB.set_material_instance_vector_parameter_value(mi,'HazeColor',unreal.LinearColor(*col,1))
        LIB.update_material_instance(mi);save(mi)
        report['modified_assets'].append(mi.get_path_name())
    for actor in actors:
        if not isinstance(actor,unreal.PostProcessVolume):continue
        label=actor.get_actor_label()
        profile=PROFILE[int(label.rsplit('_',1)[-1])] if label.startswith('HM_Environment_PP_') else 'OP'
        if label.startswith('HM_Environment_PP_'):actor.set_editor_property('priority',PRIORITY[profile])
        settings=CONF['realism_settings'](actor.get_editor_property('settings'))
        for field,value in [('scene_color_tint',unreal.LinearColor(*TINT[profile])),
                            ('color_saturation',unreal.Vector4(*([FIT['Saturation']]*3+[1]))),
                            ('color_saturation_shadows',unreal.Vector4(*([FIT['Saturation']]*3+[1]))),
                            ('color_saturation_midtones',unreal.Vector4(1,1,1,1)),
                            ('color_saturation_highlights',unreal.Vector4(1,1,1,1)),
                            ('color_contrast',unreal.Vector4(*([FIT['Contrast']]*3+[1]))),
                            ('motion_blur_amount',0.0),('scene_fringe_intensity',0.0),('bloom_intensity',FIT['Bloom'])]:
            settings.set_editor_property(field,value);settings.set_editor_property('override_'+field,True)
        actor.set_editor_property('settings',settings)
    light=by['HM_PreviewSun'].get_component_by_class(unreal.DirectionalLightComponent)
    light.set_editor_property('intensity',FIT['SunLux'])
    light.set_editor_property('light_source_angle',FIT['SunSourceAngleDeg'])
    light.set_editor_property('specular_scale',SOURCE['OP']['components']['directional_light']['properties']['SpecularScale'])
    report['source_numeric_fields'].append({'package':'WEP_HeinMach_OP','field':'directional_light.SpecularScale','raw':.01,'unit':'multiplier'})
    # Preserve every current user transform and actor (including the new Start).
    after={a.get_actor_label():CONF['OLD']['pose'](a) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    assert poses==after,'Actor poses/sets changed'
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/L_HeinMach_Environment')
    report.update(actor_count=len(after),all_actor_poses_preserved=True,actor_poses=after)
    report['native_volume_priorities']=PRIORITY
    report['native_haze_emission_mix']=HAZE_EMISSION_MIX
    report['sky_visibility_contract']='Stencil252 and opaque SceneDepth at or beyond sky CustomDepth, with native depth precision tolerance.'
    (OUT/'AppliedTrial.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('KZ_HEINMACH_REFERENCE_AUTHOR_PASSED')


main()
