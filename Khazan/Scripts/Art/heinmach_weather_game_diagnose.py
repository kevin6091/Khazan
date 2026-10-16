"""Actual viewport A/B for remaining dark world shading; no asset writes."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
OUT=ROOT/'Saved/ImportReports/HeinMachWeather_20261006'
START=time.monotonic()
HANDLE=None
WORLD=None
FRAMES=0
INDEX=0
KEEP=[]
CONFIGS=['NeutralMI','SourceGradeParent','SourceGradeShadow2','SourceGradeShadow4','SourceGradeShadow8']
REPORT={'unsaved':True,'actual_game':True,'tests':[]}
LIB=unreal.MaterialEditingLibrary
ORIGINAL_FLAGS={}
GRADE_FIELDS=('color_saturation','color_saturation_shadows','color_saturation_midtones','color_saturation_highlights',
              'color_contrast','color_contrast_shadows','color_contrast_midtones','color_contrast_highlights',
              'color_gain','color_gain_shadows','color_gain_midtones','color_gain_highlights',
              'color_gamma','color_gamma_shadows','color_gamma_midtones','color_gamma_highlights',
              'color_offset','color_offset_shadows','color_offset_midtones','color_offset_highlights',
              'scene_color_tint','film_slope','film_toe','film_shoulder','ambient_occlusion_intensity')


def diagnostic_material(signal=False):
    # MaterialFactoryNew initializes editor-only data; constructing a bare
    # transient Material in -game does not and can crash graph compilation.
    m=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/_QA/M_QA_'+('Signal' if signal else 'Albedo'))
    assert m,'Run heinmach_weather_qa_materials in the isolated editor first.'
    return m


def configure():
    kind=CONFIGS[INDEX]
    if kind in ('Signal','Albedo'):material=diagnostic_material(kind=='Signal')
    elif kind in ('SourceRegionalSolo','SourceGradeParent'):material=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/M_HM_RegionalLook')
    elif kind=='NeutralMI':material=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/MI_HM_RegionalLook_OP')
    elif kind.startswith('SourceGradeShadow'):material=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/_QA/MI_QA_Shadow'+kind[-1])
    else:material=None
    for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.PostProcessVolume):
        s=a.get_editor_property('settings')
        if a not in ORIGINAL_FLAGS:ORIGINAL_FLAGS[a]={f:s.get_editor_property('override_'+f) for f in GRADE_FIELDS}
        for f in GRADE_FIELDS:
            s.set_editor_property('override_'+f,ORIGINAL_FLAGS[a][f] if kind.startswith('SourceGrade') else False)
        s.set_editor_property('weighted_blendables',unreal.WeightedBlendables(array=[unreal.WeightedBlendable(weight=1,object=material)] if material else []))
        a.set_editor_property('settings',s)
    if kind=='NeutralCube':
        sky=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.SkyLight) if a.get_actor_label()=='HM_PreviewSkyLight')
        c=sky.get_component_by_class(unreal.SkyLightComponent)
        c.set_editor_property('real_time_capture',False)
        c.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        c.set_cubemap(unreal.load_asset('/Engine/EngineResources/GrayTextureCube'))
        c.set_intensity(64)
        c.recapture_sky()
    REPORT['tests'].append({'kind':kind,'material':str(material),'pixel_instructions':LIB.get_statistics(material).num_pixel_shader_instructions if isinstance(material,unreal.Material) else None})


def finish(error=None):
    if error:REPORT['error']=error;unreal.log_error(error)
    (META/'NativeDiagnosisShadowCalibration.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')


def tick(delta):
    global WORLD,FRAMES,INDEX
    try:
        if time.monotonic()-START<10:return
        if time.monotonic()-START>240:finish('Diagnostic timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            assert WORLD
            unreal.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
            snow=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.NiagaraActor) if a.get_actor_label()=='HM_Environment_SourceSnow')
            snow.get_component_by_class(unreal.NiagaraComponent).set_asset(None)
            configure()
        FRAMES+=1
        if FRAMES<120:return
        if FRAMES==120:
            target=OUT/('ActualGame_Diagnose_'+CONFIGS[INDEX]+'.png')
            unreal.SystemLibrary.execute_console_command(WORLD,'HighResShot 1280x720 filename="'+str(target)+'"')
            REPORT['tests'][-1]['image']=str(target)
        if FRAMES<124:return
        INDEX+=1;FRAMES=0
        if INDEX==len(CONFIGS):finish()
        else:configure()
    except Exception:finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
