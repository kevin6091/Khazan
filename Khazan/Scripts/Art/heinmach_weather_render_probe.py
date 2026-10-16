"""Read saved render graphs/volume state in an isolated real-RHI process."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
EXTRACT=ROOT/'Saved/Extracted/HeinMachWeather_20261006'
REFINE_META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachLookRefinement_20261006'
if (REFINE_META/'Applied.json').exists():
    META=REFINE_META
    EXTRACT=ROOT/'Saved/Extracted/HeinMachLookRefinement_20261006'
    EXTRACT.mkdir(parents=True,exist_ok=True)
START=time.monotonic()
HANDLE=None

def main():
    world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    lib=unreal.MaterialEditingLibrary
    report={'materials':[], 'volumes':[], 'lighting':[]}
    for name in ('M_HM_RegionalLook','M_HM_SourceSky','M_HM_SourceSnow','M_HM_SourceDust'):
        m=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/'+name)
        root=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        row={'name':name,'root':str(root),'pixel_instructions':lib.get_statistics(m).num_pixel_shader_instructions,
             'domain':str(m.get_editor_property('material_domain'))}
        if name=='M_HM_RegionalLook':
            code=next(n.get_editor_property('code') for n in lib.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionCustom))
            row['native_shadow_code_present']='nativeShadow' in code
            row['source_sky_code_present']='HM_StarBrightness' in code
            row['disable_pre_exposure_scale']=m.get_editor_property('disable_pre_exposure_scale')
        if name in ('M_HM_SourceSnow','M_HM_SourceDust'):
            opacity=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_OPACITY)
            row['opacity_root']=str(opacity)
            row['alpha_only_masks']=[{'name':n.get_name(),'r':n.get_editor_property('r'),'g':n.get_editor_property('g'),'b':n.get_editor_property('b'),'a':n.get_editor_property('a')}
                                     for n in lib.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionComponentMask) and n.get_editor_property('a')]
            row['translucency_pass']=str(m.get_editor_property('translucency_pass'))
        if '-nullrhi' not in unreal.SystemLibrary.get_command_line().lower():
            row['compile_errors']=list(lib.recompile_material(m))
            assert not row['compile_errors'],row
            assert lib.get_statistics(m).num_pixel_shader_instructions>0,row
        task=unreal.AssetExportTask()
        for k,v in [('object',m),('filename',str(EXTRACT/(name+'.t3d'))),('exporter',unreal.ObjectExporterT3D()),('automated',True),('prompt',False)]:task.set_editor_property(k,v)
        row['exported']=unreal.Exporter.run_asset_export_task(task)
        report['materials'].append(row)
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() in ('HM_PreviewSkyLight','HM_PreviewSun','HM_Environment_SourceSkyMesh'):
            row={'label':a.get_actor_label(),'actor_hidden':a.get_editor_property('hidden'), 'components':[]}
            for c in a.get_components_by_class(unreal.SceneComponent):
                cr={'name':c.get_name()}
                for f in ('intensity','visible','hidden_in_game','affects_world','mobility','indirect_lighting_intensity','source_type','cubemap','real_time_capture','lower_hemisphere_is_black','cast_shadows','visible_in_real_time_sky_captures','visible_in_reflection_captures','render_in_main_pass'):
                    try:cr[f]=str(c.get_editor_property(f))
                    except:pass
                row['components'].append(cr)
            report['lighting'].append(row)
        if not isinstance(a,unreal.PostProcessVolume):continue
        s=a.get_editor_property('settings')
        row={'label':a.get_actor_label()}
        for f in ('priority','blend_weight','blend_radius','unbound','enabled'):row[f]=a.get_editor_property(f)
        for f in ('auto_exposure_min_brightness','auto_exposure_max_brightness','color_gain','color_gain_shadows','color_gain_highlights','user_flags'):
            row[f]=str(s.get_editor_property(f));row['override_'+f]=s.get_editor_property('override_'+f)
        row['blendables']=[{'weight':b.weight,'object':str(b.object)} for b in s.get_editor_property('weighted_blendables').array]
        report['volumes'].append(row)
    (META/('NativeLightingVerification.json' if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower() else 'RenderGraphVerification.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('KZ_HEINMACH_RENDER_GRAPHS_VERIFIED')

def tick(delta):
    if time.monotonic()-START<10:return
    unreal.unregister_slate_post_tick_callback(HANDLE)
    try:main()
    except Exception:
        unreal.log_error(traceback.format_exc())
    unreal.SystemLibrary.quit_editor()

if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower():main()
else:HANDLE=unreal.register_slate_post_tick_callback(tick)
