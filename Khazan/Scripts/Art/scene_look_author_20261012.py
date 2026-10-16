"""Small saved scene adjustments; all artistic quantities are TEMP, not BBQ values."""
from pathlib import Path
import hashlib,json,os,re,traceback,unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_LOOK_MAIN']);OUT=Path(os.environ['KZ_LOOK_OUT'])
assert ROOT != MAIN, 'Author only in task-owned isolated copy'
LEVEL=os.environ['KZ_LOOK_LEVEL'];MAP='/Game/Maps/'+('DevMap' if LEVEL=='DevMap' else 'L_HeinMach_Environment')
world=unreal.EditorLoadingAndSavingUtils.load_map(MAP);assert world
ac=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);actors=ac.get_all_level_actors();by={a.get_actor_label():a for a in actors}
report={'success':False,'map':MAP,'changes':[],'saved':[],'masked_usd':[]}
# Assistant TEMP look calibration, following the user's realistic visual direction.
# Scene owners expose every value in Details. No gameplay literals or runtime code.
POLICY={
    'DevMap':{'sun_lux':6000.0,'sun_angle_deg':2.5,'sky_intensity':8.0,'ev_min':7.0,'ev_max':14.0,'exposure_bias_ev':0.65},
    'HeinMach':{'sun_lux':2500.0,'sun_angle_deg':3.0,'sky_intensity':4.0,'ev_min':4.0,'ev_max':13.0,'exposure_bias_ev':-0.6,'local_light_multiplier':0.3,'shadow_contrast':0.75},
    'shared':{'film_toe':0.45,'highlight_contrast':0.9,'shadow_contrast':0.95,'ao_intensity':0.35,
        'lumen_scene_lighting_quality':2.0,'lumen_final_gather_quality':2.0,'lumen_reflection_quality':2.0}}
report['policy_TEMP']=POLICY

def prop(obj,key,value):
    old=obj.get_editor_property(key)
    obj.set_editor_property(key,value)
    new=obj.get_editor_property(key)
    def val(v):return v if isinstance(v,(int,float,bool,str)) else (v.export_text() if hasattr(v,'export_text') else str(v))
    report['changes'].append({'object':obj.get_path_name(),'field':key,'before':val(old),'after':val(new)})

def masked_usd(m):
    chain=[];obj=m
    while isinstance(obj,unreal.MaterialInstanceConstant):
        chain.append(obj);obj=obj.get_editor_property('parent')
    if not isinstance(obj,unreal.Material) or obj.get_path_name()!='/USDCore/Materials/UsdPreviewSurface.UsdPreviewSurface':return None
    blend='BLEND_Opaque'
    for child in reversed(chain):
        text=child.get_editor_property('base_property_overrides').export_text()
        if 'bOverride_BlendMode=True' in text:
            blend=re.search(r'(?<!_)BlendMode=(BLEND_\w+)',text).group(1)
    if blend=='BLEND_Masked':return {'material':m.get_path_name(),'parent':m.get_editor_property('parent').get_path_name(),
        'chain':[c.get_path_name() for c in chain],'opacity_mask_connected':False}

try:
    policy=POLICY[LEVEL]
    sun=by['DirectionalLight' if LEVEL=='DevMap' else 'HM_PreviewSun'].get_component_by_class(unreal.DirectionalLightComponent)
    prop(sun,'intensity',policy['sun_lux']);prop(sun,'light_source_angle',policy['sun_angle_deg'])
    prop(sun,'specular_scale',1.0)
    sky=by['SkyLight' if LEVEL=='DevMap' else 'HM_PreviewSkyLight'].get_component_by_class(unreal.SkyLightComponent)
    prop(sky,'intensity',policy['sky_intensity'])
    # Neutral light coefficient avoids multiplying an already colored captured sky twice.
    prop(sky,'light_color',unreal.Color(255,255,255,255))
    dome=by['SM_SkySphere' if LEVEL=='DevMap' else 'HM_Environment_SourceSkyMesh'].get_component_by_class(unreal.StaticMeshComponent)
    for key in ['cast_shadow','affect_distance_field_lighting','affect_dynamic_indirect_lighting','visible_in_ray_tracing']:
        prop(dome,key,False)
    if LEVEL=='HeinMach':
        baseline=json.loads((MAIN/'Metadata/SceneLook_20261012/HeinBefore01/SavedScene.json').read_text())
        baseline_lights={r['component']:r['properties']['intensity'] for r in baseline['lights']}
        for a in actors:
            if a.get_actor_label().startswith(('HM_SourceLight_','HM_FireLight_')):
                for c in a.get_components_by_class(unreal.LightComponent):
                    prop(c,'intensity',float(baseline_lights[c.get_path_name()])*policy['local_light_multiplier'])
    # One neutral exposure/quality owner per map. No toon, outline or custom blendable.
    label='Art_NaturalLighting_'+LEVEL
    pp=by.get(label) or ac.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector())
    pp.set_actor_label(label);pp.set_folder_path('Art/Lighting');pp.set_editor_property('unbound',True)
    pp.set_editor_property('priority',0.0)
    settings=pp.get_editor_property('settings')
    pp_fields={'auto_exposure_min_brightness':policy['ev_min'],'auto_exposure_max_brightness':policy['ev_max'],
        'auto_exposure_bias':policy['exposure_bias_ev'],'auto_exposure_speed_up':1.0,'auto_exposure_speed_down':1.0,
        'film_toe':POLICY['shared']['film_toe'],'local_exposure_highlight_contrast_scale':POLICY['shared']['highlight_contrast'],
        'local_exposure_shadow_contrast_scale':policy.get('shadow_contrast',POLICY['shared']['shadow_contrast']),'ambient_occlusion_intensity':POLICY['shared']['ao_intensity'],
        **{k:v for k,v in POLICY['shared'].items() if k.startswith('lumen_')}}
    for key,value in pp_fields.items():settings.set_editor_property(key,value);settings.set_editor_property('override_'+key,True)
    pp.set_editor_property('settings',settings);report['pp_fields']=pp_fields
    sky.recapture_sky()
    unique={}
    for a in actors:
        for c in a.get_components_by_class(unreal.MeshComponent):
            for i in range(c.get_num_materials()):
                m=c.get_material(i)
                if m and m.get_path_name() not in unique:unique[m.get_path_name()]=m
    for m in unique.values():
        row=masked_usd(m)
        if row:report['masked_usd'].append(row)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,MAP),'Cannot save own map'
    report['saved'].append(MAP);report['success']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'Authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
