"""HeinMach-only native look correction, in an isolated authoring process."""
from pathlib import Path
import hashlib
import json
import math
import runpy
import shutil
import sys
import time
import traceback
import unreal

sys.dont_write_bytecode = True
ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
BACKUP = ROOT / 'Saved/ArtBackups/HeinMachWeather_20261006'
ASSETS = '/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
SOURCE = ROOT / 'Saved/Extracted/HeinMachWeather_20261006/Source'
OLD = runpy.run_path(str(ROOT / 'Scripts/Art/restore_level_look.py'))
MANIFEST = OLD['read'](OLD['REPORT'] / 'SourceManifest.json')
LIB = unreal.MaterialEditingLibrary
# Assistant native-renderer calibration, NOT recovered original EV/luminance.
# Fixed EV preserves snow detail while moving between dark rock and bright snow.
# Radiance = 2**EV keeps source sky RGB meaningful under this native exposure.
NATIVE = {'OutdoorEV100': 8.0, 'CaveEV100': 4.0, 'BloomIntensity': 0.15,
          'LensFlareIntensity': 0.0, 'DirtMaskIntensity': 0.0,
          # User-requested realistic lighting with a small toon contribution.
          # Assistant tuning, not original BBQ values. The old fill of 8 was
          # calibrated with the strongly desaturated source grade on Medium.
          'WorldOutlineOpacity': 0.02, 'WorldToonWeight': 0.03,
          'CharacterOutlineOpacity': 0.08, 'CharacterToonWeight': 0.16,
          'ShadeSmoothness': 0.12, 'HM_NativeShadowFillScale': 2.0,
          'SunSpecularScale': 0.15}
REFINE_META = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachLookRefinement_20261006'
# All are explicitly native artistic choices following the latest user request.
# Neutral channel gains preserve the source texture colors and snow highlights.
REALISM_GRADE = {
    # The old OP scene tint (.488729,.477538,.796875) both dimmed the
    # source albedo and shifted it strongly blue. Keep only a subtle cool cast.
    'scene_color_tint': (0.98, 0.99, 1.0, 1),
    'color_saturation': (0.95, 0.95, 0.95, 1),
    'color_saturation_shadows': (0.92, 0.92, 0.92, 1),
    'color_saturation_midtones': (1.04, 1.04, 1.04, 1),
    'color_saturation_highlights': (0.96, 0.96, 0.96, 1),
    'color_contrast': (1.02, 1.02, 1.02, 1),
    'color_contrast_shadows': (1, 1, 1, 1),
    'color_contrast_midtones': (1, 1, 1, 1),
    'color_contrast_highlights': (1, 1, 1, 1),
    **{field: (1, 1, 1, 1) for field in (
        'color_gamma', 'color_gamma_shadows', 'color_gamma_midtones', 'color_gamma_highlights',
        'color_gain', 'color_gain_shadows', 'color_gain_midtones', 'color_gain_highlights')},
    **{field: (0, 0, 0, 0) for field in (
        'color_offset', 'color_offset_shadows', 'color_offset_midtones', 'color_offset_highlights')},
    # UE5.8 Scene.cpp FPostProcessSettings ACES defaults, deliberately selected
    # for this native look. Engine defaults are not original Khazan values.
    'film_slope': 0.88, 'film_toe': 0.55, 'film_shoulder': 0.26,
    'film_black_clip': 0.0, 'film_white_clip': 0.04,
    'film_grain_intensity': 0.0, 'motion_blur_amount': 0.08,
    'motion_blur_max': 1.0, 'bloom_intensity': NATIVE['BloomIntensity']}
# Local quality preset; saved through GameUserSettings, not a level tick/BP.
# High shading/GI/shadows, native-resolution TSR, texture budget below Epic's
# unrestricted memory use on the available RTX 3060 Ti. No forced ray tracing.
QUALITY_PREVIEW = {'sg.ResolutionQuality': 100, 'sg.AntiAliasingQuality': 3, 'sg.TextureQuality': 2,
                   'sg.PostProcessQuality': 2, 'sg.ShadowQuality': 2,
                   'sg.GlobalIlluminationQuality': 2, 'sg.ReflectionQuality': 2,
                   'sg.EffectsQuality': 2, 'sg.ViewDistanceQuality': 2,
                   'sg.FoliageQuality': 2, 'sg.ShadingQuality': 2,
                   'r.ScreenPercentage': 100, 'r.AntiAliasingMethod': 4,
                   'r.TemporalAA.Quality': 2, 'r.MaxAnisotropy': 8,
                   'r.Streaming.MipBias': 0, 'r.Streaming.PoolSize': 1600,
                   'r.Tonemapper.Sharpen': 0.25}


def realism_settings(settings):
    for field, value in REALISM_GRADE.items():
        prop = (unreal.LinearColor(*value) if field == 'scene_color_tint' else
                unreal.Vector4(*value)) if isinstance(value, tuple) else value
        settings.set_editor_property(field, prop)
        settings.set_editor_property('override_' + field, True)
    return settings


def refine_saved_look():
    """Change existing HeinMach owners only; preserve all geometry/actor poses."""
    REFINE_META.mkdir(parents=True, exist_ok=True)
    world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before = {a.get_actor_label(): OLD['pose'](a) for a in ac.get_all_level_actors()}
    by = {a.get_actor_label(): a for a in ac.get_all_level_actors()}
    pose_snapshot=REFINE_META/'BeforeApplyActorPoses.json'
    if not pose_snapshot.exists():
        pose_snapshot.write_text(json.dumps({'actors':before,'PlayerStarts':[
            {'label':a.get_actor_label(),'pose':OLD['pose'](a)} for a in by.values()
            if isinstance(a,unreal.PlayerStart)]},indent=2)+'\n',encoding='utf-8')
    files = [ROOT / 'Content/Maps/L_HeinMach_Environment.umap'] + [
        ROOT / ('Content/_Art/Player/Environment/Rendering/HeinMachWeather/MI_HM_RegionalLook_'+p+'.uasset')
        for p in ('OP', 'Blizzard1', 'Blizzard2', 'Boss', 'Cave1', 'Escape')]
    backups = []
    for path in files:
        target = ROOT / 'Saved/ArtBackups/HeinMachLookRefinement_20261006' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists(): shutil.copy2(path, target)
        backups.append({'path': str(path), 'backup': str(target),
                        'backup_sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    rows = []
    for profile in ('OP', 'Blizzard1', 'Blizzard2', 'Boss', 'Cave1', 'Escape'):
        mi = unreal.load_asset(ASSETS+'/MI_HM_RegionalLook_'+profile)
        assert mi
        for name in ('WorldOutlineOpacity', 'WorldToonWeight', 'CharacterOutlineOpacity',
                     'CharacterToonWeight', 'ShadeSmoothness', 'HM_NativeShadowFillScale'):
            LIB.set_material_instance_scalar_parameter_value(mi, name, NATIVE[name])
        LIB.update_material_instance(mi)
        save(mi)
        rows.append({'profile': profile, 'asset': mi.get_path_name()})
    volumes = []
    for a in by.values():
        if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label().startswith(('HM_Environment_PP_', 'HM_PreviewPostProcess')):
            a.set_editor_property('settings', realism_settings(a.get_editor_property('settings')))
            volumes.append(a.get_actor_label())
    assert len(volumes) == 8
    # Recover a controlled amount of DefaultLit specular; the original .01
    # was intended for BBQ's different light model. This is native tuning.
    sun = by['HM_PreviewSun'].get_component_by_class(unreal.DirectionalLightComponent)
    original_specular = sun.get_editor_property('specular_scale')
    sun.set_editor_property('specular_scale', NATIVE['SunSpecularScale'])
    after = {a.get_actor_label(): OLD['pose'](a) for a in ac.get_all_level_actors()}
    assert before == after, 'Actor set/poses changed during color/lighting refinement'
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, '/Game/Maps/L_HeinMach_Environment')
    report = {'purpose': 'Latest user direction: realistic material/light detail with very subtle toon. Native artistic tuning, not exact-original reconstruction.',
              'native_controls': NATIVE, 'native_grade': REALISM_GRADE, 'quality_preview': QUALITY_PREVIEW,
              'materials': rows, 'volumes': volumes, 'sun_specular_scale': {'before': original_specular, 'native': NATIVE['SunSpecularScale']},
              'actors': len(after), 'all_actor_poses_preserved': True, 'backups': backups,
              'before_actor_snapshot':str(pose_snapshot),
              'changed_packages': [str(p.relative_to(ROOT)) for p in files]}
    (REFINE_META/'Applied.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('KZ_HEINMACH_REALISM_REFINED')


def write(name, data):
    (META / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def backup(path):
    target = BACKUP / path.relative_to(ROOT)
    if path.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def save(asset):
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)


def clone(src, dst):
    asset = unreal.load_asset(dst)
    if asset:
        backup(ROOT / ('Content/' + dst[6:] + '.uasset'))
        return asset
    unreal.EditorAssetLibrary.make_directory(dst.rsplit('/', 1)[0])
    asset = unreal.EditorAssetLibrary.duplicate_asset(src, dst)
    assert asset, (src, dst)
    return asset


def instance(src, dst, parent):
    mi = clone(src, dst)
    LIB.set_material_instance_parent(mi, parent)
    return mi


def values(ref):
    props = json.loads((SOURCE / (ref['ObjectPath'].rsplit('.', 1)[0] + '.json')).read_text(encoding='utf-8-sig'))[0]['Properties']
    return {r['ParameterInfo']['Name']: r['ParameterValue'] for k in ('ScalarParameterValues', 'VectorParameterValues') for r in props.get(k, [])}


def color(v):
    return unreal.LinearColor(v['R'], v['G'], v['B'], v.get('A', 1))


def sky_material():
    m = clone('/Game/_Art/Player/Environment/Rendering/Materials/M_KZ_SourceSky_Adapter', ASSETS + '/M_HM_SourceSky')
    nodes = list(LIB.get_material_expressions(m))
    output = LIB.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if not any(n.get_editor_property('desc') == 'HM native physical radiance adapter' for n in nodes):
        mul = OLD['expression'](m, unreal.MaterialExpressionMultiply, 3800, 0)
        mul.set_editor_property('desc', 'HM native physical radiance adapter')
        OLD['connect'](output, LIB.get_material_property_input_node_output_name(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR), mul, 'A')
        OLD['connect'](OLD['scalar'](m, 'HM_NativeSkyRadiance', 2**NATIVE['OutdoorEV100'], 3500, 800), '', mul, 'B')
        assert LIB.connect_material_property(mul, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(m)
    save(m)
    mi = instance('/Game/_Art/Player/Environment/Rendering/Materials/MI_HM_SourceSky_GloomySunset', ASSETS + '/MI_HM_SourceSky_OP', m)
    LIB.set_material_instance_scalar_parameter_value(mi, 'HM_NativeSkyRadiance', 2**NATIVE['OutdoorEV100'])
    save(mi)
    return mi


def region_sky_material():
    """Engine PP-volume blending owns regional palettes; no weather manager."""
    m = clone('/Game/_Art/Player/Environment/Rendering/Materials/M_KZ_NativeCartoonOutline', ASSETS + '/M_HM_RegionalLook')
    # This adapter consumes/produces pre-exposed HDR. UE5's default PP shader
    # rescales inputs and multiplies the output by PreExposure. Explicitly
    # disable that automatic scaling to avoid exposing sky/shadow terms twice.
    # Engine evidence: PostProcessMaterialShaders.usf 387 and MaterialTemplate.ush.
    m.set_editor_property('disable_pre_exposure_scale',True)
    nodes = list(LIB.get_material_expressions(m))
    node = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom))
    if 'HM_SkyRadiance' not in node.get_editor_property('code'):
        inputs = list(node.get_editor_property('inputs'))
        links = []
        for name, val in [('HM_SkyRadiance', 2**NATIVE['OutdoorEV100']), ('HM_HorizonFalloff', 0.75),
                          ('HM_CloudAmount', 0.0), ('HM_CloudSpeed', 0.001)]:
            inputs.append(OLD['custom_input'](name))
            links.append((OLD['scalar'](m, name, val, -100, 2400), '', name))
        for name, val in [('HM_SkyColor', (0.328125, 0.29994, 0.306533, 1)),
                          ('HM_HorizonColor', (0.567708, 0.455114, 0.397441, 1)),
                          ('HM_OverallColor', (0.536361, 0.557292, 0.537648, 1)),
                          ('HM_CloudColor', (0, 0, 0, 1))]:
            inputs.append(OLD['custom_input'](name))
            links.append((OLD['vector'](m, name, val, -100, 2900), 'RGB', name))
        for cls, name in [(unreal.MaterialExpressionWorldPosition, 'HM_World'),
                          (unreal.MaterialExpressionCameraPositionWS, 'HM_Camera'),
                          (unreal.MaterialExpressionTime, 'HM_Time')]:
            inputs.append(OLD['custom_input'](name))
            links.append((OLD['expression'](m, cls, -100, 3400), '', name))
        texture = OLD['expression'](m, unreal.MaterialExpressionTextureObjectParameter, -100, 3600)
        texture.set_editor_property('parameter_name', 'HM_CloudTexture')
        texture.set_editor_property('texture', unreal.load_asset('/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/Textures/T_SP_Sky_Smoke_Noise'))
        inputs.append(OLD['custom_input']('HM_CloudTexture'))
        links.append((texture, '', 'HM_CloudTexture'))
        node.set_editor_property('inputs', inputs)
        for src, out, pin in links:
            OLD['connect'](src, out, node, pin)
        code = node.get_editor_property('code')
        code = code.replace('float2 uv =', '''// Native regional sky formulas; source palettes/cloud motion, not cooked BBQ shader.
if (Depth.r > 200000.0) {
    float3 dir = normalize(HM_World.xyz-HM_Camera.xyz);
    float h = pow(saturate(dir.z), max(HM_HorizonFalloff, 0.001));
    float3 sky = lerp(HM_HorizonColor.rgb, HM_SkyColor.rgb, h)*HM_OverallColor.rgb;
    float2 suv = float2(atan2(dir.y,dir.x)/6.28318530718, acos(clamp(dir.z,-1.0,1.0))/3.14159265359);
    float noise = Texture2DSample(HM_CloudTexture,HM_CloudTextureSampler,suv*8.0+float2(HM_Time*HM_CloudSpeed,0)).r;
    sky = lerp(sky,HM_CloudColor.rgb,saturate(noise*HM_CloudAmount)*smoothstep(0.0,0.3,dir.z));
    return sky*HM_SkyRadiance*View.PreExposure;
}
float2 uv =''', 1)
        node.set_editor_property('code', code)
    code = node.get_editor_property('code').replace('if (Depth.r > 200000.0)', 'if (abs(Stencil.r-252.0)<0.5 && abs(Depth.r-CustomDepth.r)<StencilDepthToleranceCm)')
    if 'HM_CloudAmount2' not in code:
        inputs = list(node.get_editor_property('inputs'))
        for name, value in [('HM_CloudAmount2', 0.0), ('HM_CloudSpeed2', 0.00125), ('HM_CloudUVScale1', 8.0), ('HM_CloudUVScale2', 7.0)]:
            inputs.append(OLD['custom_input'](name))
        inputs.append(OLD['custom_input']('HM_CloudColor2'))
        node.set_editor_property('inputs', inputs)
        for name, value in [('HM_CloudAmount2', 0.0), ('HM_CloudSpeed2', 0.00125), ('HM_CloudUVScale1', 8.0), ('HM_CloudUVScale2', 7.0)]:
            OLD['connect'](OLD['scalar'](m, name, value, -100, 3800), '', node, name)
        OLD['connect'](OLD['vector'](m, 'HM_CloudColor2', (0,0,0,1), -100, 4200), 'RGB', node, 'HM_CloudColor2')
        code = code.replace('suv*8.0+', 'suv*HM_CloudUVScale1+')
        code = code.replace('return sky*HM_SkyRadiance', '''float noise2=Texture2DSample(HM_CloudTexture,HM_CloudTextureSampler,suv*HM_CloudUVScale2+float2(HM_Time*HM_CloudSpeed2,0.0)).r;
    sky=lerp(sky,HM_CloudColor2.rgb,saturate(noise2*HM_CloudAmount2)*smoothstep(0.0,0.3,dir.z));
    return sky*HM_SkyRadiance''')
    if 'HM_StarBrightness' not in code:
        scalar_defaults={'HM_StarBrightness':0.0,'HM_StarPower':4.0,'HM_StarUVScale':2.0,
                         'HM_StarBlinkWeight':0.5,'HM_StarBlinkSpeed':2.0,'HM_StarBlinkUVScale':10.0,
                         'HM_StarColorWeight':0.75,'HM_StarHorizonHeightMin':0.0,'HM_StarHorizonHeightMax':50000.0,
                         'HM_NebulaIntensity':0.5,'HM_NebulaUVScale':0.25,'HM_NebulaDesaturation':0.0,
                         'HM_SourceShadowBrightness':0.45,'HM_SourceShadowAmbient':0.5,
                         'HM_NativeShadowFillScale':NATIVE['HM_NativeShadowFillScale']}
        inputs=list(node.get_editor_property('inputs'))
        links=[]
        for name,value in scalar_defaults.items():
            inputs.append(OLD['custom_input'](name))
            links.append((OLD['scalar'](m,name,value,-1200,4400),'',name))
        inputs.append(OLD['custom_input']('HM_StarColor'))
        links.append((OLD['vector'](m,'HM_StarColor',(1,0.702458,0.233331,1),-1200,4500),'RGB','HM_StarColor'))
        for name,asset_name in [('HM_StarTexture','T_SP_Sky_Star_Mask'),('HM_NebulaTexture','T_SP_Sky_Nebula')]:
            tex=OLD['expression'](m,unreal.MaterialExpressionTextureObjectParameter,-1200,4800)
            tex.set_editor_property('parameter_name',name)
            tex.set_editor_property('texture',unreal.load_asset('/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/Textures/'+asset_name))
            inputs.append(OLD['custom_input'](name));links.append((tex,'',name))
        base=OLD['expression'](m,unreal.MaterialExpressionSceneTexture,-1200,5000)
        base.set_editor_property('scene_texture_id',unreal.SceneTextureId.PPI_BASE_COLOR)
        inputs.append(OLD['custom_input']('HM_BaseColor'));links.append((base,'Color','HM_BaseColor'))
        node.set_editor_property('inputs',inputs)
        for src,out,pin in links:OLD['connect'](src,out,node,pin)
        code=code.replace('float noise =', '''float3 nebula=Texture2DSample(HM_NebulaTexture,HM_NebulaTextureSampler,suv*HM_NebulaUVScale).rgb;
    float nebulaLuma=dot(nebula,float3(0.2126,0.7152,0.0722));
    nebula=lerp(nebula,nebulaLuma.xxx,saturate(HM_NebulaDesaturation));
    sky+=nebula*HM_NebulaIntensity;
    float starMask=Texture2DSample(HM_StarTexture,HM_StarTextureSampler,suv*HM_StarUVScale).r;
    float blink=lerp(1.0,0.5+0.5*sin(HM_Time*HM_StarBlinkSpeed+(suv.x+suv.y)*HM_StarBlinkUVScale*6.28318530718),saturate(HM_StarBlinkWeight));
    float skyHeight=HM_World.z-(-13768.473);
    float starHorizon=smoothstep(HM_StarHorizonHeightMin,max(HM_StarHorizonHeightMax,HM_StarHorizonHeightMin+1.0),skyHeight);
    sky+=pow(saturate(starMask),HM_StarPower)*HM_StarBrightness*lerp(float3(1,1,1),HM_StarColor.rgb,HM_StarColorWeight)*blink*starHorizon;
    float noise =''')
        code=code.replace('color *= (1.0 - outline);', '''color *= (1.0 - outline);
// Native substitute for BBQCartoon's source shadow brightness/ambient terms.
// UE DefaultLit lacks that light model. This is an explicit native formula,
// restricted to world surfaces; the character stencil retains its own model.
float3 nativeShadow=HM_BaseColor.rgb*HM_SourceShadowBrightness*HM_SourceShadowAmbient*HM_NativeShadowFillScale*HM_SkyRadiance*View.PreExposure;
color=lerp(max(color,nativeShadow),color,isCharacter);''')
    node.set_editor_property('code', code)
    if 'HM_NativeShadowRadiance' not in code:
        inputs=list(node.get_editor_property('inputs'))
        inputs.append(OLD['custom_input']('HM_NativeShadowRadiance'))
        node.set_editor_property('inputs',inputs)
        code=code.replace('*HM_NativeShadowFillScale*HM_SkyRadiance*View.PreExposure',
                          '*HM_NativeShadowFillScale*HM_NativeShadowRadiance*View.PreExposure')
        node.set_editor_property('code',code)
        OLD['scalar'](m,'HM_NativeShadowRadiance',2**NATIVE['OutdoorEV100'],-1200,5300)
    # Reconnect after Custom code reconstruction. Changing its reflected
    # input array can leave newly added inputs unlinked in the editor graph.
    for expression in LIB.get_material_expressions(m):
        if isinstance(expression,(unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionVectorParameter,unreal.MaterialExpressionTextureObjectParameter)):
            name=str(expression.get_editor_property('parameter_name'))
            if name in {str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs')}:
                OLD['connect'](expression,'RGB' if isinstance(expression,unreal.MaterialExpressionVectorParameter) else '',node,name)
        if isinstance(expression,unreal.MaterialExpressionSceneTexture) and expression.get_editor_property('scene_texture_id') == unreal.SceneTextureId.PPI_BASE_COLOR:
            OLD['connect'](expression,'Color',node,'HM_BaseColor')
    errors=LIB.recompile_material(m)
    assert not errors,str(errors)
    stats=LIB.get_statistics(m)
    assert stats.num_pixel_shader_instructions > 0,'Regional material failed to compile; do not replace the saved look'
    save(m)
    return m


def main():
    if '-HMWeatherRefine' in unreal.SystemLibrary.get_command_line():
        refine_saved_look()
        return
    if '-HMWeatherMaterialOnly' in unreal.SystemLibrary.get_command_line():
        m=region_sky_material()
        rows=[]
        for profile in ('OP','Blizzard1','Blizzard2','Boss','Cave1','Escape'):
            mi=unreal.load_asset(ASSETS+'/MI_HM_RegionalLook_'+profile)
            assert mi
            ev=NATIVE['CaveEV100'] if profile=='Cave1' else NATIVE['OutdoorEV100']
            LIB.set_material_instance_scalar_parameter_value(mi,'HM_NativeShadowFillScale',NATIVE['HM_NativeShadowFillScale'])
            LIB.set_material_instance_scalar_parameter_value(mi,'HM_NativeShadowRadiance',2**ev)
            LIB.update_material_instance(mi)
            save(mi)
            rows.append({'profile':profile,'shadow_radiance_native':2**ev})
        write('ExposureContractCorrection',{'material':m.get_path_name(),'disable_pre_exposure_scale':m.get_editor_property('disable_pre_exposure_scale'),
              'contract':'PostProcessInput0 and custom sky/shadow outputs stay in pre-exposed HDR. No second engine PreExposure multiplication.',
              'engine_evidence':'UE5.8 PostProcessMaterialShaders.usf 387-389; MaterialTemplate.ush SceneTextureLookup pre-exposure scaling.',
              'pixel_shader_instructions':LIB.get_statistics(m).num_pixel_shader_instructions,'map_edited':False,
              'native_controls':NATIVE,'profiles':rows,
              'calibration_evidence':'NativeDiagnosisShadowCalibration.json and actual game screenshots. 8 is native calibration, not a recovered BBQ field.'})
        print('KZ_HEINMACH_EXPOSURE_CONTRACT_FIXED')
        return
    world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before = {a.get_actor_label(): OLD['pose'](a) for a in ac.get_all_level_actors()}
    by = {a.get_actor_label(): a for a in ac.get_all_level_actors()}
    backup(ROOT / 'Content/Maps/L_HeinMach_Environment.umap')
    source_skymi = sky_material()
    parent = region_sky_material()
    discovery = json.loads((META / 'SourceDiscovery.json').read_text())
    topology = {r['source_actor_index']: r for r in json.loads((META / 'OriginalBrushTopology.json').read_text())['volumes']}
    builder_backup = ROOT / 'Saved/ArtBackups/HeinMachWeather_20261006/BuilderBrush.t3d'
    unreal.SystemLibrary.execute_console_command(world, 'BRUSH EXPORT FILE="'+str(builder_backup)+'"')
    fallback = by['HM_PreviewPostProcess']
    rows = []
    for row in MANIFEST['HeinMach_volumes'] + [{'source_actor_index': None, 'profile': 'OP'}]:
        key = row['profile']
        label = 'HM_Environment_PP_HeinMach_Light_' + str(row['source_actor_index']) if row['source_actor_index'] else 'HM_PreviewPostProcess'
        actor = by[label]
        if row['source_actor_index']:
            # Rebuild the original BSP polygons, including irregular/concave
            # profiles, through the native editor brush importer and factory.
            existing = {a.get_path_name() for a in ac.get_all_level_actors()}
            unreal.SystemLibrary.execute_console_command(world, 'BRUSH IMPORT FILE="'+topology[row['source_actor_index']]['brush']+'"')
            unreal.SystemLibrary.execute_console_command(world, 'BRUSH ADDVOLUME CLASS=PostProcessVolume')
            created = [a for a in ac.get_all_level_actors() if a.get_path_name() not in existing and isinstance(a, unreal.PostProcessVolume)]
            assert len(created) == 1, 'Original brush factory did not create exactly one PP volume'
            new = created[0]
            assert ac.destroy_actor(actor)
            actor = new
            actor.set_actor_label(label)
            tr = row['transform']
            loc = unreal.Vector(*[tr['location_cm'][c] for c in 'xyz'])
            rot = unreal.Rotator(**tr['rotation_degrees'])
            sc = [tr['scale'][c] for c in 'xyz']
            actor.set_actor_location(loc, False, False)
            actor.set_actor_rotation(rot, False)
            actor.set_actor_scale3d(unreal.Vector(*sc))
            for f in ('unbound', 'priority', 'blend_radius', 'blend_weight', 'enabled'):
                actor.set_editor_property(f, row[f])
            actor.set_folder_path('HeinMach/Reconstructed/Environment/PostProcess/' + key)
        result = OLD['native_pp_settings'](actor, MANIFEST['HeinMach'][key])
        settings = actor.get_editor_property('settings')
        # Native per-view material flag: source Cave1 geometry owns snow
        # suppression. No polling actor, trigger BP, or weather subsystem.
        settings.set_editor_property('user_flags', 1 if key == 'Cave1' else 0)
        settings.set_editor_property('override_user_flags', True)
        ev = NATIVE['CaveEV100'] if key == 'Cave1' else NATIVE['OutdoorEV100']
        for f, val in [('auto_exposure_min_brightness', ev), ('auto_exposure_max_brightness', ev),
                       ('auto_exposure_bias', 0.0), ('bloom_intensity', NATIVE['BloomIntensity']),
                       ('lens_flare_intensity', NATIVE['LensFlareIntensity']), ('bloom_dirt_mask_intensity', NATIVE['DirtMaskIntensity'])]:
            settings.set_editor_property(f, val)
            settings.set_editor_property('override_' + f, True)
        mi = instance('/Game/_Art/Player/Environment/Rendering/Materials/MI_KZ_Toon_HeinMach_' + key, ASSETS + '/MI_HM_RegionalLook_' + key, parent)
        params = values(discovery['profiles'][key]['weather_references']['SkyBoxMaterial'])
        cloud = values(discovery['profiles'][key]['weather_references']['CloudMaterialLayer1'])
        cloud2 = values(discovery['profiles'][key]['weather_references']['CloudMaterialLayer2'])
        for name, val in [('HM_SkyRadiance', 2**NATIVE['OutdoorEV100']), ('HM_HorizonFalloff', params['Horizon Falloff']),
                          ('HM_CloudAmount', cloud['CloudIntensity']), ('HM_CloudSpeed', discovery['profiles'][key]['weather_references']['CloudRotationSpeed1']),
                          ('HM_CloudAmount2', cloud2['CloudIntensity']), ('HM_CloudSpeed2', discovery['profiles'][key]['weather_references']['CloudRotationSpeed2']),
                          ('HM_CloudUVScale1', cloud['DiffuseTexScaleU']), ('HM_CloudUVScale2', cloud2['DiffuseTexScaleU'])] + list(NATIVE.items()):
            LIB.set_material_instance_scalar_parameter_value(mi, name, val)
        for name in ('StarBrightness','StarPower','StarUVScale','StarBlinkWeight','StarBlinkSpeed','StarBlinkUVScale','StarColorWeight','StarHorizonHeightMin','StarHorizonHeightMax','NebulaIntensity','NebulaUVScale','NebulaDesaturation'):
            LIB.set_material_instance_scalar_parameter_value(mi,'HM_'+name,params[name])
        lights=MANIFEST['HeinMach'][key]['components']
        LIB.set_material_instance_scalar_parameter_value(mi,'HM_SourceShadowBrightness',lights['directional_light']['properties']['BBQCartoonShadingBrightness'])
        LIB.set_material_instance_scalar_parameter_value(mi,'HM_SourceShadowAmbient',lights['sky_light']['properties']['BBQCartoonShadowAmbientIntensity'])
        LIB.set_material_instance_vector_parameter_value(mi,'HM_StarColor',color(params['StarBaseColor']))
        LIB.set_material_instance_scalar_parameter_value(mi,'HM_NativeShadowFillScale',NATIVE['HM_NativeShadowFillScale'])
        LIB.set_material_instance_scalar_parameter_value(mi,'HM_NativeShadowRadiance',2**ev)
        for name, val in [('HM_SkyColor', params['Sky Color']), ('HM_HorizonColor', params['Bottom color']),
                          ('HM_OverallColor', params['Overall Color']), ('HM_CloudColor', cloud['CloudBaseColor']), ('HM_CloudColor2', cloud2['CloudBaseColor'])]:
            LIB.set_material_instance_vector_parameter_value(mi, name, color(val))
        save(mi)
        settings.set_editor_property('weighted_blendables', unreal.WeightedBlendables(array=[unreal.WeightedBlendable(weight=1, object=mi)]))
        actor.set_editor_property('settings', settings)
        if (REFINE_META/'Applied.json').exists():
            actor.set_editor_property('settings', realism_settings(settings))
        bounds = actor.get_actor_bounds(False)
        assert min(bounds[1].x, bounds[1].y, bounds[1].z) > 0
        rows.append({'label': label, 'profile': key, 'bounds': str(bounds), 'settings_copy': result,
                     'native_EV100': ev, 'instance': mi.get_path_name(), 'shape_status': 'Original BSP Node vertex rings, source actor transform, original priority/blend policy.'})
    unreal.SystemLibrary.execute_console_command(world, 'BRUSH IMPORT FILE="'+str(builder_backup)+'"')
    sky = by['HM_Environment_SourceSkyMesh']
    sky.set_actor_location(unreal.Vector(7917.611, -10604.79, -13768.473), False, False)
    sky.set_actor_scale3d(unreal.Vector(50, 50, 50))
    skycomponent = sky.get_component_by_class(unreal.StaticMeshComponent)
    skycomponent.set_material(0, source_skymi)
    # Rendering-only reservation: identify the source sky precisely instead
    # of treating every distant mesh as sky. Character reservation stays 254.
    skycomponent.set_render_custom_depth(True)
    skycomponent.set_custom_depth_stencil_value(252)
    by['HM_PreviewSun'].get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('specular_scale',NATIVE['SunSpecularScale'] if (REFINE_META/'Applied.json').exists() else MANIFEST['HeinMach']['OP']['components']['directional_light']['properties']['SpecularScale'])
    by['HM_PreviewSkyLight'].get_component_by_class(unreal.SkyLightComponent).recapture_sky()
    changed = {r['label'] for r in rows} | {'HM_Environment_SourceSkyMesh'}
    after = {a.get_actor_label(): OLD['pose'](a) for a in ac.get_all_level_actors()}
    assert set(before) == set(after)
    assert all(after[k] == v for k, v in before.items() if k not in changed), 'Unrelated actor transform changed'
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, '/Game/Maps/L_HeinMach_Environment')
    write('LookApplied', {'actors': len(after), 'volumes': rows, 'native_controls': NATIVE,
                         'source_sky_pose': 'HeinMach_Light.394 xxSkyMeshComponent, RelativeLocation and RelativeScale3D',
                         'preserved_unrelated_actors': True, 'background_only': True})
    print('KZ_HEINMACH_LOOK_APPLIED ' + str(len(rows)))


if __name__ == '__main__' and '-RenderOffscreen' in unreal.SystemLibrary.get_command_line():
    started = time.monotonic()
    handle = None
    def tick(delta):
        if time.monotonic() - started < 10:
            return
        unreal.unregister_slate_post_tick_callback(handle)
        try:
            main()
        except Exception:
            write('LookFailure', {'error': traceback.format_exc()})
            unreal.log_error(traceback.format_exc())
        unreal.SystemLibrary.quit_editor()
    handle = unreal.register_slate_post_tick_callback(tick)
elif __name__ == '__main__':
    main()
