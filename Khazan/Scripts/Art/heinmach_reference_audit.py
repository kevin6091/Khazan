"""Fresh saved-scene check; no asset saves and no interactive editor changes."""
from pathlib import Path
import json
import runpy
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
BASE=json.loads((OUT/'BaselineProbe.json').read_text(encoding='utf-8'))
APPLIED=json.loads((OUT/'AppliedTrial.json').read_text(encoding='utf-8'))
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py'))
ASSETS='/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
LIB=unreal.MaterialEditingLibrary

world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
poses={a.get_actor_label():CONF['OLD']['pose'](a) for a in actors}
flat={label:value['location']+value['rotation']+value['scale'] for label,value in poses.items()}
assert flat.keys()==BASE['actor_poses'].keys(),'Actor set changed'
max_delta=max(abs(a-b) for label,value in flat.items() for a,b in zip(value,BASE['actor_poses'][label]))
# Floating point quaternion/rotator readback tolerance; not a gameplay tuning.
assert max_delta<0.0000001,('Current user poses changed',max_delta)
report={'passed':False,'project':str(ROOT),'actor_count':len(actors),
        'all_actor_poses_preserved':True,'PlayerStart':poses.get('PlayerStart'),
        'maximum_pose_readback_delta':max_delta,
        'postprocess':[],'regional_materials':[],'snow_materials':[],
        'boundary':'Fresh serialization only; real shader/game/performance reports are separate.'}
for actor in actors:
    if not isinstance(actor,unreal.PostProcessVolume):continue
    settings=actor.get_editor_property('settings')
    label=actor.get_actor_label()
    assert settings.get_editor_property('motion_blur_amount')==0
    assert settings.get_editor_property('scene_fringe_intensity')==0
    profile={209:'Blizzard1',210:'Blizzard2',211:'Boss',212:'Cave1',213:'Cave1',214:'Escape',215:'OP'}[int(label.rsplit('_',1)[-1])] if label.startswith('HM_Environment_PP_') else 'OP'
    if label.startswith('HM_Environment_PP_'):
        assert actor.get_editor_property('priority')==APPLIED['native_volume_priorities'][profile]
    entries=settings.get_editor_property('weighted_blendables').get_editor_property('array')
    assert len(entries)==1 and isinstance(entries[0].get_editor_property('object'),unreal.MaterialInstanceConstant)
    report['postprocess'].append({'label':label,'profile':profile,'priority':actor.get_editor_property('priority'),
                                'material':entries[0].get_editor_property('object').get_path_name()})
assert len(report['postprocess'])==8
master=unreal.load_asset(ASSETS+'/M_HM_RegionalLook')
assert master.get_editor_property('blendable_location')==unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF
assert master.get_editor_property('disable_pre_exposure_scale')
report['postprocess_pass']='BeforeDOF (before TSR)'
for profile in APPLIED['native_tints']:
    mi=unreal.load_asset(ASSETS+'/MI_HM_RegionalLook_'+profile)
    values={str(name):LIB.get_material_instance_scalar_parameter_value(mi,name)
            for name in LIB.get_scalar_parameter_names(mi)}
    for name in ('WorldToonWeight','CharacterToonWeight','WorldOutlineOpacity','CharacterOutlineOpacity','ShadeSmoothness'):
        assert abs(values[name]-APPLIED['native_fit'][name])<0.000001,name
    report['regional_materials'].append({'profile':profile,'scalars':values})
for name in ('M_HM_SourceSnow','M_HM_SourceDust'):
    mat=unreal.load_asset(ASSETS+'/'+name)
    assert not mat.get_editor_property('output_translucent_velocity')
    assert mat.get_editor_property('translucency_pass')==unreal.MaterialTranslucencyPass.MTP_BEFORE_DOF
    assert mat.get_editor_property('enable_responsive_aa')
    opacity=LIB.get_material_property_input_node(mat,unreal.MaterialProperty.MP_OPACITY)
    assert isinstance(opacity,unreal.MaterialExpressionComponentMask)
    assert opacity.get_editor_property('a') and not any(opacity.get_editor_property(c) for c in ('r','g','b'))
    color=next(n for n in LIB.get_material_expressions(mat) if isinstance(n,unreal.MaterialExpressionCustom)
               and 'sourceAlpha' in n.get_editor_property('code'))
    inputs=LIB.get_inputs_for_material_expression(mat,color)
    assert any(isinstance(n,unreal.MaterialExpressionTextureSample) for n in inputs),'Missing snow atlas input'
    report['snow_materials'].append({'asset':mat.get_path_name(),'output_depth_velocity':False,
                                    'responsive_aa':True,'opacity':'Atlas/lifetime alpha only','pass':'BeforeDOF'})
system=unreal.load_asset(ASSETS+'/NS_HM_SourceSnow_TwoLayers')
effect=system.get_editor_property('effect_type')
assert effect.get_path_name().split('.')[0]==ASSETS+'/NET_HM_WeatherBudget'
settings=effect.get_editor_property('emitter_scalability_settings').get_editor_property('settings')
assert len(settings)==1 and settings[0].get_editor_property('scale_spawn_count')
assert settings[0].get_editor_property('spawn_count_scale')==APPLIED['native_fit']['SpawnCountScale']
report['snow_budget']={'effect_type':effect.get_path_name(),'spawn_count_scale':settings[0].get_editor_property('spawn_count_scale')}
sun=next(a for a in actors if a.get_actor_label()=='HM_PreviewSun').get_component_by_class(unreal.DirectionalLightComponent)
assert abs(sun.get_editor_property('intensity')-APPLIED['native_fit']['SunLux'])<0.001
assert abs(sun.get_editor_property('specular_scale')-.01)<0.000001
report['sun']={'lux':sun.get_editor_property('intensity'),'source_angle_degrees':sun.get_editor_property('light_source_angle'),
               'source_OP_specular_scale':sun.get_editor_property('specular_scale')}
report['passed']=True
(OUT/'FreshSavedSceneAudit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('KZ_HEINMACH_REFERENCE_AUDIT_PASSED')
