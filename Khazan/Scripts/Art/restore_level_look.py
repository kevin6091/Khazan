"""Source-backed native rendering adapters for the two reconstructed levels.

Run named functions through RiderLink in the existing editor. This is an Art
authoring tool, not a gameplay controller. Cooked BBQ shader implementations
are unavailable: the native formulas below are explicitly an approximation.
Original values, derived placement and authoring controls stay separate.
"""

from pathlib import Path
import copy
import hashlib
import json
import math
import re
import runpy
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path.home() / 'Desktop' / '\uce74\uc794' / 'Exports'
EXTRACT = ROOT / 'Saved/Extracted/LookRestoration_20261002/Source'
REPORT = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002'
BACKUP = ROOT / 'Saved/ArtBackups/LevelLook_PreRestore_20261002'
ASSETS = '/Game/_Art/Player/Environment/Rendering'
MAPS = {'StormPass': '/Game/Maps/L_StormPass_Environment',
        'HeinMach': '/Game/Maps/L_HeinMach_Environment'}
SPMETA = ROOT / 'Content/_Art/Player/Environment/StormPass/Metadata'
HMETA = ROOT / 'Content/_Art/Player/Environment/HeinMach/Metadata'
STENCIL = 254  # Native rendering reservation; not a source gameplay value.

# All new author-selected values are centralized here and copied into reports.
# These are not claimed to be the missing proprietary shader's implementation.
NATIVE = {
    'WorldToonWeight': 0.16, 'CharacterToonWeight': 1.0,
    'WorldOutlineOpacity': 0.16, 'CharacterOutlineOpacity': 0.8,
    'DepthEdgeThreshold': 0.004, 'NormalEdgeThreshold': 0.3,
    'StencilDepthToleranceCm': 2.0,
    'FogDensityScale': 0.01, 'FogFalloffScale': 0.10,
    'LocalFogDensityScale': 0.15, 'Phase2LocalFogDensityScale': 0.60,
    'Phase1LocalFogRadiusCm': 7500.0, 'Phase2LocalFogRadiusCm': 6000.0,
    'CoveringColorWeight': 0.85,
    # Native masks/coefficient adapters: original cooked expression graph is
    # unavailable. The source red covering/pollution colors remain separate.
    'SnowLuminanceStart': 0.03, 'SnowLuminanceEnd': 0.20,
    'SnowNeutralityTolerance': 0.50, 'SnowUpNormalWeight': 0.35,
    'WorldCoveringBaseMask': 0.30, 'FoliageCoveringBaseMask': 0.0,
    'CoveringGlowScale': 0.002,
    'WaterPollutionWeight': 0.85, 'WaterPollutionAbsorptionPerCm': 0.02,
    'NativeHazeStartCm': 1000.0, 'NativeHazeLuminanceScale': 8.0,
    'SkySunBackgroundScale': 0.25,
    'SkyNebulaNoiseStrengthUV': 0.02,
    # Native extended-luminance auto exposure brightened the source night
    # palette into daylight (Rider viewport 20261002-084227). Fixed EV100 and
    # native bloom correction preserve darkness; these are not original EVs.
    'Phase2FixedEV100': 2.5, 'Phase2BloomIntensity': 0.5,
    'Phase2SaturationNative': 0.85, 'Phase2ShadowSaturationNative': 0.85,
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name, value):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / (name + '.json')).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def backup_file(path):
    path = Path(path)
    target = BACKUP / path.relative_to(ROOT)
    if path.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        records = read(BACKUP / 'AdditionalAssets.json') if (BACKUP / 'AdditionalAssets.json').exists() else []
        records.append({'file': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                        'sha256': digest(target)})
        (BACKUP / 'AdditionalAssets.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')


def backup_asset(asset):
    package = asset.get_path_name().split('.')[0]
    if not package.startswith('/Game/'):
        raise RuntimeError('Only project assets can be edited: ' + package)
    backup_file(ROOT / ('Content/' + package[6:] + '.uasset'))


def merge(base, overrides):
    out = copy.deepcopy(base)
    for k, v in overrides.items():
        out[k] = merge(out[k], v) if isinstance(out.get(k), dict) and isinstance(v, dict) else copy.deepcopy(v)
    return out


def source_manifest():
    """Resolve exact exported CDO/templates, including inherited components."""
    used = {}
    cache = {}

    def objects(package):
        package = package.rsplit('.', 1)[0] if package.rsplit('.', 1)[-1].isdigit() else package
        if package not in cache:
            path = EXTRACT / (package + '.json')
            if not path.exists():
                path = SOURCE / (package + '.json')
            if not path.exists():
                raise FileNotFoundError(path)
            cache[package] = read(path)
            used[package] = {'json': str(path), 'sha256': digest(path)}
        return cache[package]

    def resolve(package, index, seen=()):
        key = (package, index)
        if key in seen:
            raise RuntimeError('Source inheritance cycle: ' + repr(key))
        obj = objects(package)[index]
        base = {}
        ref = (obj.get('Template') or {}).get('ObjectPath', '')
        if ref:
            parent, tail = ref.rsplit('.', 1)
            if tail.isdigit():
                base = resolve(parent, int(tail), seen + (key,))
        return merge(base, obj.get('Properties') or {})

    hein = {}
    wep_dir = 'BBQ/Content/Art/ArtRendering/AR_PostProcess/WEP/'
    for key in ('OP', 'Blizzard1', 'Blizzard2', 'Boss', 'Cave1', 'Escape'):
        package = wep_dir + 'WEP_HeinMach_' + key
        data = objects(package)
        cls = next(x['Name'] for x in data if x['Type'] == 'BlueprintGeneratedClass')
        cdo = next(i for i, x in enumerate(data) if x['Type'] == cls and x['Name'].startswith('Default__'))
        components = {}
        for prefix, label in (('EMP_', 'environment_material'), ('ERP_', 'render_parameters'),
                              ('FOG_', 'fog'), ('WDL_', 'directional_light'), ('WSL_', 'sky_light')):
            found = [(i, x) for i, x in enumerate(data) if x.get('Type', '').startswith(prefix)]
            if not found:
                # Some child WEPs inherit the entire ERP without exporting it.
                base = objects('BBQ/Content/Art/ArtRendering/AR_Data/PostProcess/WEP_Base_PostProcess')
                found_base = [(i, x) for i, x in enumerate(base) if x.get('Type', '').startswith(prefix)]
                if len(found_base) != 1:
                    raise RuntimeError('Ambiguous inherited component ' + prefix)
                i, obj = found_base[0]
                properties = resolve('BBQ/Content/Art/ArtRendering/AR_Data/PostProcess/WEP_Base_PostProcess', i)
            else:
                if len(found) != 1:
                    raise RuntimeError('Ambiguous ' + prefix + ' in ' + package)
                i, obj = found[0]
                # Component template may point to a WEP archetype; its template
                # then resolves the component-class CDO. Preserve that chain.
                properties = resolve(package, i)
            components[label] = {'source_type': obj['Type'], 'properties': properties}
        hein[key] = {'source_package': package, 'default_properties': resolve(package, cdo),
                     'components': components}

    level_package = 'BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Light'
    data = objects(level_package)
    helper = runpy.run_path(str(ROOT / 'Scripts/StormPass/analyze_stormpass_environment_profiles.py'))
    volumes = []
    for index, actor in enumerate(data):
        if not actor.get('Type', '').startswith('WEP_HeinMach_'):
            continue
        props = actor.get('Properties') or {}
        model_index = int(props['Brush']['ObjectPath'].rsplit('.', 1)[-1])
        model = data[model_index]
        volumes.append({'source_actor_index': index, 'source_actor_name': actor['Name'],
                        'profile': actor['Type'].removeprefix('WEP_HeinMach_').removesuffix('_C'),
                        'transform': helper['world_actor_transform'](actor, data),
                        'model_origin_cm': model['Bounds']['Origin'],
                        'model_box_extent_cm': model['Bounds']['BoxExtent'],
                        'axis_aligned_box_model': helper['is_axis_aligned_box'](model),
                        'priority': props.get('Priority', 0.0),
                        'blend_radius': props.get('BlendRadius', 100.0),
                        'blend_weight': props.get('BlendWeight', 1.0),
                        'unbound': props.get('bUnbound', False), 'enabled': props.get('bEnabled', True)})

    toon_package = 'BBQ/Content/_Kazan_/BaseMaterials/Character/M_AKCartoonCharacter'
    master = objects(toon_package)[0]
    params = master['CachedExpressionData']['Parameters']
    scalars = {n['Name']: v for n, v in zip(params['RuntimeEntries']['ParameterInfos'], params['ScalarValues'])}
    vectors = {n['Name']: v for n, v in zip(params['RuntimeEntries[1]']['ParameterInfos'], params['VectorValues'])}
    source_values = {name: scalars[name] for name in ('Shading Width', 'Shading Intensity',
                        'ShadingSmoothness', 'CellShadingThreshold', 'NTPThreshold', 'CameraLightWeight')}
    storm = read(SPMETA / 'StormPass_EnvironmentProfile.json')['profiles']
    payload = {'date': '2026-10-02', 'HeinMach': hein, 'HeinMach_volumes': volumes,
               'StormPass': {k: storm[k] for k in ('boss_phase_1', 'boss_phase_2')},
               'toon_master': {'source_package': toon_package, 'field': 'CachedExpressionData.Parameters',
                               'shading_model': master['Properties']['ShadingModel'],
                               'master_scalar_defaults': source_values,
                               'master_vector_defaults': {k: vectors[k] for k in ('LightDirection', 'ShadingColor', 'RimLightColor')},
                               'boundary': 'Master defaults, not verified per-character leaf overrides. No MaterialExpression exports or executable shader source.'},
               'source_files': used, 'native_authoring_controls': NATIVE,
               'native_control_status': 'Assistant temporary controls. Formula and unit interpretation are not proprietary BBQ renderer reconstruction.'}
    write('SourceManifest', payload)
    print(json.dumps({'source_files': len(used), 'HeinMach_profiles': len(hein), 'HeinMach_volumes': len(volumes), 'toon_defaults': source_values}))
    return payload


def hein_terrain_plan():
    """Exact layer maps and textures; native linear blending is an adapter."""
    extraction = read(ROOT / 'Saved/Extracted/LookRestoration_20261002/HeinLandscape/TargetedLandscapeWeightmaps.json')
    package_root = 'BBQ/Content/_Kazan_/Art/Terrain/Terrain_Material/Landscape_Material/'
    parent = read(EXTRACT / (package_root + 'WLM_Base_Terrain5_Inst.json'))[0]['Properties']
    master = read(EXTRACT / 'BBQ/Content/BaseMaterials/Terrain/Base_Terrain5.json')[0]
    cached = master.get('CachedExpressionData', {}).get('Parameters', {})
    scalar_defaults = {x['Name']: v for x, v in zip(cached.get('RuntimeEntries', {}).get('ParameterInfos', []), cached.get('ScalarValues', []))}
    vector_defaults = {x['Name']: v for x, v in zip(cached.get('RuntimeEntries[1]', {}).get('ParameterInfos', []), cached.get('VectorValues', []))}
    plans = []
    textures_to_extract = set()
    for landscape in extraction['landscapes']:
        suffix = landscape['output_name'][-1]
        material_name = 'WLM_HeinMach' + ('2' if suffix == '2' else '')
        path = EXTRACT / (package_root + material_name + '.json')
        native = read(path)[0]['Properties']
        scalars = dict(scalar_defaults)
        vectors = dict(vector_defaults)
        textures = {}
        for p in (parent, native):
            scalars.update({r['ParameterInfo']['Name']: r['ParameterValue'] for r in p.get('ScalarParameterValues', [])})
            vectors.update({r['ParameterInfo']['Name']: r['ParameterValue'] for r in p.get('VectorParameterValues', [])})
            textures.update({r['ParameterInfo']['Name']: r['ParameterValue'] for r in p.get('TextureParameterValues', [])})
        source_package = 'BBQ/Content/_Kazan_/Level/HeinMach/' + landscape['output_name']
        objects = read(SOURCE / (source_package + '.json'))
        actor = next(x for x in objects if x.get('Type') == 'Landscape')
        root_index = int(actor['Properties']['RootComponent']['ObjectPath'].rsplit('.', 1)[-1])
        root_properties = objects[root_index]['Properties']
        components = []
        for reference in actor['Properties']['LandscapeComponents']:
            obj = objects[int(reference['ObjectPath'].rsplit('.', 1)[-1])]
            props = obj['Properties']
            components.append({'name': obj['Name'], 'section_x': props.get('SectionBaseX', 0),
                               'section_y': props.get('SectionBaseY', 0)})
        mapping = {row['exported_layer_name']: row['material_layer_names'][0] for row in landscape['layer_info_mappings']}
        weight_rows = []
        layers = []
        for row in landscape['layers']:
            if row['layer_name'] == 'NormalMap_DX':
                continue
            name = mapping[row['layer_name']]
            weight_rows.append({**row, 'material_layer_name': name})
            if name == 'Puddle':
                continue
            texture_bindings = {}
            for semantic, letter in [('diffuse', 'D'), ('normal', 'N'), ('surface', 'S')]:
                parameter = 'BaseGroundTex_' + letter if name == 'Layer1' else 'Tex_' + letter + '-' + name
                ref = textures[parameter]
                package = ref['ObjectPath'].rsplit('.', 1)[0]
                textures_to_extract.add(package)
                texture_bindings[semantic] = {'parameter': parameter, 'object_path': ref['ObjectPath'],
                                              'object_name': package.rsplit('/', 1)[-1], 'source_package': package}
            layers.append({'layer_name': name, 'textures': texture_bindings,
                           'tiling_meters': scalars['Tiling-' + name]})
        puddle_color = vectors['Puddle1Color']
        plans.append({'group': 'Landscape' + suffix, 'source_package': source_package,
                      'source_material': package_root + material_name, 'source_material_sha256': digest(path),
                      'root_location': root_properties['RelativeLocation'], 'root_scale': root_properties['RelativeScale3D'],
                      'min_section': [min(r['section_x'] for r in components), min(r['section_y'] for r in components)],
                      'dimensions': [landscape['layers'][0]['width'], landscape['layers'][0]['height']],
                      'weight_layers': weight_rows, 'layers': layers,
                      'puddle': {'weight_layer': 'Puddle', 'wet_surface_darkness': scalars['WetSurfaceDarkness'],
                                 'roughness': scalars['Puddle1Roughness'], 'metallic': scalars['Puddle1Metalic'],
                                 'color': {k.lower(): puddle_color[k] for k in ('R', 'G', 'B', 'A')}},
                      'source_covering': {'SnowHeight': scalars['SnowHeight'],
                                          'LocalEnvCoverWeight': scalars['LocalEnvCoverWeight']},
                      'boundary': 'Original weightmaps/textures/tiling and grid. Native normalized linear layer blend; original height blending, displacement, RVT and covering engine shader unavailable.'})
    write('HeinMachTerrainPlan', plans)
    request = ROOT / 'Saved/Extracted/LookRestoration_20261002/HeinTerrainTextureRequests.json'
    request.write_text(json.dumps(sorted(textures_to_extract), indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'landscapes': len(plans), 'layers': [len(x['layers']) for x in plans], 'source_texture_packages': len(textures_to_extract)}))
    return plans


def ue():
    import unreal
    return unreal


def actors():
    return ue().get_editor_subsystem(ue().EditorActorSubsystem).get_all_level_actors()


def pose(actor):
    p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    return {'location': [p.x, p.y, p.z], 'rotation': [r.pitch, r.yaw, r.roll], 'scale': [s.x, s.y, s.z]}


def snapshot(level):
    unreal = ue()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0] == MAPS[level]
    rows = []
    for a in actors():
        row = {'label': a.get_actor_label(), 'class': a.get_class().get_name(), 'pose': pose(a),
               'hidden': a.get_editor_property('hidden'), 'materials': []}
        for c in a.get_components_by_class(unreal.MeshComponent):
            row['materials'].append({'component': c.get_name(), 'slots':
                                    [c.get_material(i).get_path_name() if c.get_material(i) else None
                                     for i in range(c.get_num_materials())]})
        rows.append(row)
    name = level + '_Before'
    if not (REPORT / (name + '.json')).exists():
        write(name, rows)
    print(json.dumps({'level': level, 'actors': len(rows), 'PlayerStart': [r for r in rows if r['class'] == 'PlayerStart']}))
    return rows


def expression(material, cls, x=0, y=0):
    return ue().MaterialEditingLibrary.create_material_expression(material, cls, x, y)


def connect(a, output, b, input_name):
    if not ue().MaterialEditingLibrary.connect_material_expressions(a, output, b, input_name):
        raise RuntimeError('Material connection failed: ' + input_name)


def scalar(material, name, value, x, y):
    node = expression(material, ue().MaterialExpressionScalarParameter, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', float(value))
    return node


def vector(material, name, value, x, y):
    node = expression(material, ue().MaterialExpressionVectorParameter, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', ue().LinearColor(*value))
    return node


def custom_input(name):
    value = ue().CustomInput()
    value.set_editor_property('input_name', name)
    return value


def new_asset(path, cls, factory):
    unreal = ue()
    asset = unreal.load_asset(path)
    if asset:
        backup_asset(asset)
    else:
        folder, name = path.rsplit('/', 1)
        unreal.EditorAssetLibrary.make_directory(folder)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, cls, factory)
    if not asset:
        raise RuntimeError('Could not create ' + path)
    return asset


def compile_save(material):
    unreal = ue()
    unreal.MaterialEditingLibrary.recompile_material(material)
    stats = unreal.MaterialEditingLibrary.get_statistics(material)
    report = {'asset': material.get_path_name(), 'pixel_instructions': stats.num_pixel_shader_instructions,
              'vertex_instructions': stats.num_vertex_shader_instructions}
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return report


# SceneTexture IDs are Unreal engine API constants. All tuning lives in NATIVE
# or named material inputs. Luminance and safe denominators are mathematical
# operations, not claims about Khazan's source lighting model.
TOON_CODE = r'''
float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float2 stepUV = InvSize.xy * OutlineWidth;
float3 n = normalize(Normal.xyz);
float stencil = Stencil.r;
float isCharacter = (abs(stencil - CharacterStencil) < 0.5 && abs(Depth.r - CustomDepth.r) < StencilDepthToleranceCm) ? 1.0 : 0.0;
float valid = (Depth.r < OutlineDistance && dot(Normal.xyz, Normal.xyz) > 0.1) ? 1.0 : 0.0;
float lambert = saturate(dot(n, normalize(LightDirection.xyz)) * 0.5 + 0.5);
float lowerBand = 1.0 - ShadeIntensity;
float quantized = lerp(lowerBand, 1.0, smoothstep(ShadeWidth - ShadeSmoothness, ShadeWidth + ShadeSmoothness, lambert));
float continuous = lerp(lowerBand, 1.0, lambert);
float weight = lerp(WorldToonWeight, CharacterToonWeight, isCharacter) * valid;
float3 color = SceneColor.rgb * lerp(1.0, quantized / max(continuous, 0.001), weight);
float edge = 0.0;
float charEdge = 0.0;
float2 offsets[4] = {float2(stepUV.x, 0), float2(-stepUV.x, 0), float2(0, stepUV.y), float2(0, -stepUV.y)};
[unroll] for (int i = 0; i < 4; ++i)
{
    float2 nuv = saturate(uv + offsets[i]);
    float nd = SceneTextureLookup(nuv, 1, false).r;
    float3 nn = SceneTextureLookup(nuv, 8, false).xyz;
    float ns = SceneTextureLookup(nuv, 25, false).r;
    float ncd = SceneTextureLookup(nuv, 13, false).r;
    float nc = (abs(ns - CharacterStencil) < 0.5 && abs(nd - ncd) < StencilDepthToleranceCm) ? 1.0 : 0.0;
    float de = abs(Depth.r - nd) / max(Depth.r, 1.0);
    float ne = 1.0 - saturate(dot(n, normalize(nn + 0.000001)));
    edge = max(edge, max(step(DepthEdgeThreshold, de), step(NormalEdgeThreshold, ne)));
    charEdge = max(charEdge, abs(isCharacter - nc));
}
float opacity = lerp(WorldOutlineOpacity, CharacterOutlineOpacity, isCharacter);
float outline = saturate(max(edge, charEdge) * opacity) * valid;
color *= (1.0 - outline);
// Source volumetric emissive palette, native depth-fog fallback for Phase2.
// Source density/view distance are inputs; this exponential is not recovered
// BBQ WEP shader code. Scene color here is pre-exposed HDR.
float travel = max(Depth.r-NativeHazeStartCm,0.0);
float haze = min(HazeMaxOpacity,1.0-exp(-travel*HazeDensity/max(HazeViewDistance,1.0)))*HazeWeight;
return lerp(color,HazeColor.rgb*NativeHazeLuminanceScale*View.PreExposure,saturate(haze));
'''


def build_toon():
    unreal = ue()
    source = read(REPORT / 'SourceManifest.json')
    defaults = source['toon_master']['master_scalar_defaults']
    erp = source['HeinMach']['OP']['components']['render_parameters']['properties']
    material = new_asset(ASSETS + '/Materials/M_KZ_NativeCartoonOutline', unreal.Material, unreal.MaterialFactoryNew())
    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    material.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_BLOOM)
    material.set_editor_property('blendable_priority', 0)
    custom = expression(material, unreal.MaterialExpressionCustom, 400, 0)
    custom.set_editor_property('description', 'Native BBQCartoon/HalfCartoon adapter; source parameters, approximate formula')
    custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property('code', TOON_CODE)
    definitions = []
    links = []
    for i, (name, identifier, output) in enumerate([
        ('SceneColor', unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0, 'Color'),
        ('Normal', unreal.SceneTextureId.PPI_WORLD_NORMAL, 'Color'),
        ('Depth', unreal.SceneTextureId.PPI_SCENE_DEPTH, 'Color'),
        ('Stencil', unreal.SceneTextureId.PPI_CUSTOM_STENCIL, 'Color'),
        ('CustomDepth', unreal.SceneTextureId.PPI_CUSTOM_DEPTH, 'Color'),
        ('InvSize', unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0, 'InvSize')]):
        node = expression(material, unreal.MaterialExpressionSceneTexture, -700, i * 130)
        node.set_editor_property('scene_texture_id', identifier)
        definitions.append(custom_input(name))
        links.append((node, output, name))
    inputs = {'ShadeWidth': defaults['Shading Width'], 'ShadeIntensity': defaults['Shading Intensity'],
              'ShadeSmoothness': defaults['ShadingSmoothness'],
              'OutlineWidth': erp['CartoonOutlineWidth'], 'OutlineDistance': erp['CartoonOutlineDistance'],
              'CharacterStencil': STENCIL,
              'HazeWeight': 0.0, 'HazeDensity': 1.0,
              'HazeViewDistance': 5000.0, 'HazeMaxOpacity': 0.9}
    inputs.update({k: v for k, v in NATIVE.items() if k in TOON_CODE})
    for i, (name, value) in enumerate(inputs.items()):
        node = scalar(material, name, value, -400, i * 100)
        definitions.append(custom_input(name))
        links.append((node, '', name))
    light = vector(material, 'LightDirection', (0.5, 0.5, 1, 1), -700, 900)
    definitions.append(custom_input('LightDirection'))
    links.append((light, 'RGB', 'LightDirection'))
    haze_color = vector(material, 'HazeColor', (0, 0, 0, 1), -700, 1050)
    definitions.append(custom_input('HazeColor'))
    links.append((haze_color, 'RGB', 'HazeColor'))
    custom.set_editor_property('inputs', definitions)
    for node, output, name in links:
        connect(node, output, custom, name)
    if not unreal.MaterialEditingLibrary.connect_material_property(custom, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Could not connect PP output')
    result = compile_save(material)
    write('ToonShaderCompilation', result)
    print(json.dumps(result))
    return material


def toon_instance(level, key, direction=None):
    unreal = ue()
    source = read(REPORT / 'SourceManifest.json')
    profile = source[level][key]
    erp = profile['components']['render_parameters']['properties']
    parent = unreal.load_asset(ASSETS + '/Materials/M_KZ_NativeCartoonOutline')
    if not parent:
        raise RuntimeError('Build toon material before applying a level')
    instance = new_asset(ASSETS + '/Materials/MI_KZ_Toon_' + level + '_' + key,
                         unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    library = unreal.MaterialEditingLibrary
    library.set_material_instance_parent(instance, parent)
    for name in ('NativeHazeStartCm', 'NativeHazeLuminanceScale'):
        library.set_material_instance_scalar_parameter_value(instance, name, NATIVE[name])
    for name, field in [('OutlineWidth', 'CartoonOutlineWidth'), ('OutlineDistance', 'CartoonOutlineDistance')]:
        library.set_material_instance_scalar_parameter_value(instance, name, float(erp[field]))
    if direction is None:
        rotation = profile['components']['directional_light']['properties'].get('RelativeRotation') or {}
        p = math.radians(rotation.get('Pitch', 0))
        y = math.radians(rotation.get('Yaw', 0))
        # Engine directional light illuminates opposite its actor forward axis.
        direction = [-math.cos(p)*math.cos(y), -math.cos(p)*math.sin(y), -math.sin(p)]
    library.set_material_instance_vector_parameter_value(instance, 'LightDirection', unreal.LinearColor(*direction, 1))
    haze = level == 'StormPass' and key == 'boss_phase_2'
    library.set_material_instance_scalar_parameter_value(instance, 'HazeWeight', float(haze))
    if haze:
        fog = profile['components']['fog']['properties']
        for name, value in [('HazeDensity', fog['FogDensity']), ('HazeViewDistance', fog['VolumetricFogDistance']),
                            ('HazeMaxOpacity', fog['FogMaxOpacity'])]:
            library.set_material_instance_scalar_parameter_value(instance, name, value)
        fc = fog['VolumetricFogEmissive']
        library.set_material_instance_vector_parameter_value(instance, 'HazeColor', unreal.LinearColor(fc['R'],fc['G'],fc['B'],1))
    unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
    return instance


def bind_toon(actor, instance):
    unreal = ue()
    settings = actor.get_editor_property('settings')
    weighted = settings.get_editor_property('weighted_blendables')
    previous = [x for x in weighted.get_editor_property('array')
                if not (x.object and '/Environment/Rendering/Materials/MI_KZ_Toon_' in x.object.get_path_name())]
    previous.append(unreal.WeightedBlendable(weight=1.0, object=instance))
    weighted.set_editor_property('array', previous)
    settings.set_editor_property('weighted_blendables', weighted)
    actor.set_editor_property('settings', settings)


def enable_character_stencils():
    """Set rendering templates only; preserve assembly and gameplay graphs."""
    unreal = ue()
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    candidates = ['/Game/_Art/Player/Character/Bluprints/BP_Player']
    candidates += [str(row.package_name) for row in registry.get_assets_by_path('/Game/_Art/Enemies', True)
                   if str(row.asset_class_path.asset_name) == 'Blueprint' and
                   '/Blueprints/BP_EN_' in str(row.package_name)]
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    changes = []
    for path in sorted(set(candidates)):
        bp = unreal.load_asset(path)
        if not bp:
            continue
        handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
        entries = []
        objects_seen = set()
        for handle in handles:
            data = lib.get_data(handle)
            obj = lib.get_object_for_blueprint(data, bp)
            if not isinstance(obj, unreal.SkeletalMeshComponent) or obj.get_path_name() in objects_seen:
                continue
            objects_seen.add(obj.get_path_name())
            if not obj.get_editor_property('visible') or not obj.get_editor_property('skeletal_mesh_asset'):
                continue
            entries.append((obj, {'component': obj.get_name(),
                                 'render_custom_depth': obj.get_editor_property('render_custom_depth'),
                                 'stencil': obj.get_editor_property('custom_depth_stencil_value')}))
        if not entries:
            continue
        backup_asset(bp)
        bp.modify()
        for obj, old in entries:
            if old['stencil'] not in (0, STENCIL):
                raise RuntimeError('Existing stencil reservation in ' + path + ': ' + repr(old))
            obj.modify()
            obj.set_editor_property('render_custom_depth', True)
            obj.set_editor_property('custom_depth_stencil_value', STENCIL)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)
        changes.append({'asset': path, 'before': [old for obj, old in entries], 'after_stencil': STENCIL})
    write('CharacterStencilTemplates', {'status': 'Native selective toon rendering mask; no animation/gameplay/scale edits', 'blueprints': changes})
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, 'r.CustomDepth 3')
    print(json.dumps({'blueprints': len(changes), 'mesh_components': sum(len(r['before']) for r in changes),
                      'r.CustomDepth': unreal.SystemLibrary.get_console_variable_int_value('r.CustomDepth')}))
    return changes


def build_light_masks():
    """Spatial masks let both arenas illuminate ordinary channel-0 Pawns."""
    unreal = ue()
    layout = read(SPMETA / 'BladePhantom_SideBySide_20261002/Layout.json')
    boundary = 169790.0 + layout['clearance_cm'] * 0.5
    report = []
    for phase in (1, 2):
        material = new_asset(ASSETS + '/Materials/M_SP_Phase%d_SunMask' % phase, unreal.Material, unreal.MaterialFactoryNew())
        unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
        material.set_editor_property('material_domain', unreal.MaterialDomain.MD_LIGHT_FUNCTION)
        world = expression(material, unreal.MaterialExpressionWorldPosition, -700, 0)
        split = scalar(material, 'ArenaSplitX_Cm', boundary, -700, 180)
        custom = expression(material, unreal.MaterialExpressionCustom, -200, 0)
        custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        custom.set_editor_property('inputs', [custom_input('WorldPosition'), custom_input('SplitX')])
        custom.set_editor_property('code', 'return ' + ('1.0 - ' if phase == 1 else '') + 'step(SplitX, WorldPosition.x);')
        connect(world, '', custom, 'WorldPosition')
        connect(split, '', custom, 'SplitX')
        unreal.MaterialEditingLibrary.connect_material_property(custom, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        report.append(compile_save(material))
    write('LightMaskCompilation', {'split_x_cm': boundary, 'status': 'Derived midpoint of the authored gap; not original phase locations', 'materials': report})
    print(json.dumps(report))


def native_pp_settings(actor, profile):
    """Copy supported source PP fields, with explicit native color-grade caveat."""
    unreal = ue()
    bridge = runpy.run_path(str(ROOT / 'Scripts/StormPass/restore_stormpass_environment_profile.py'))
    source = copy.deepcopy(profile['default_properties'].get('Settings') or {})
    mapping = dict(bridge['POST_PROCESS_FIELDS'])
    mapping.update({'ColorContrast': ('color_contrast', 'vector4'),
                    'FilmToe': ('film_toe', 'float'), 'FilmShoulder': ('film_shoulder', 'float'),
                    'FilmBlackClip': ('film_black_clip', 'float'), 'FilmWhiteClip': ('film_white_clip', 'float'),
                    'ExpandGamut': ('expand_gamut', 'float'), 'BlueCorrection': ('blue_correction', 'float')})
    settings = actor.get_editor_property('settings')
    copied, unsupported = [], []
    for name, value in source.items():
        if name.startswith('bOverride_') or name == 'WeightedBlendables':
            continue
        if name not in mapping:
            unsupported.append(name)
            continue
        field, kind = mapping[name]
        try:
            # A serialized value does not make an inactive source override active.
            # This preserves inherited engine/WEP policy when copying profiles.
            if source.get('bOverride_' + name) is False:
                settings.set_editor_property('override_' + field, False)
                continue
            settings.set_editor_property(field, bridge['convert_post_value'](value, kind))
            settings.set_editor_property('override_' + field, True)
            copied.append(field)
        except Exception as error:
            unsupported.append(name + ': ' + str(error))
    # BBQ's cooked Film/color grade differs from the native UE5 renderer.
    # Some source shadow/highlight gains are zero. Direct native application
    # erases all HDR light; retain neutral gains, recorded as native adaptation.
    neutral = []
    for field in ('color_gain_shadows', 'color_gain_highlights'):
        current = settings.get_editor_property(field)
        if max(abs(current.x), abs(current.y), abs(current.z)) == 0:
            settings.set_editor_property(field, unreal.Vector4(1, 1, 1, 1))
            neutral.append(field)
    actor.set_editor_property('settings', settings)
    return {'copied_source_fields': copied, 'unsupported_source_fields': unsupported,
            'neutralized_zero_gain': neutral, 'boundary': 'Native UE color grade, not recovered proprietary tonemapper or CACAO shader'}


def local_fog(label, location, radius_cm, profile, folder, density_scale=None):
    unreal = ue()
    by = {a.get_actor_label(): a for a in actors()}
    actor = by.get(label)
    if not actor:
        actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.LocalFogVolume, unreal.Vector(*location))
        actor.set_actor_label(label)
    actor.set_actor_location(unreal.Vector(*location), False, False)
    actor.set_actor_rotation(unreal.Rotator(), False)
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    actor.set_folder_path(folder)
    # Actor bounds contain its editor sprite, not the fog sphere. Engine 5.8
    # LocalFogVolumeComponent.h:GetBaseVolumeRadius fixes the sphere at 500cm.
    base_radius = 500.0
    actor.set_actor_scale3d(unreal.Vector(*([radius_cm / base_radius] * 3)))
    c = actor.get_component_by_class(unreal.LocalFogVolumeComponent)
    source = profile['components']['fog']['properties']
    bridge = runpy.run_path(str(ROOT / 'Scripts/StormPass/restore_stormpass_environment_profile.py'))
    color = source['VolumetricFogAlbedo']
    # LocalFog expects a linear color; the source ExponentialFog field is FColor.
    rgb = [color[k] / 255.0 for k in ('R', 'G', 'B')]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    c.set_editor_property('fog_albedo', unreal.LinearColor(*linear, 1))
    c.set_editor_property('fog_emissive', bridge['linear_color'](source['VolumetricFogEmissive']))
    c.set_editor_property('fog_phase_g', float(source['VolumetricFogScatteringDistribution']))
    c.set_editor_property('height_fog_falloff', max(1.0, float(source['FogHeightFalloff'])))
    c.set_editor_property('height_fog_offset', 0.0)
    density_scale = NATIVE['LocalFogDensityScale'] if density_scale is None else density_scale
    c.set_editor_property('height_fog_extinction', float(source['FogDensity']) * density_scale)
    c.set_editor_property('radial_fog_extinction', 0.0)
    return {'label': label, 'pose': pose(actor), 'radius_cm': radius_cm,
            'fog_density_source': source['FogDensity'], 'density_native_scale': density_scale,
            'boundary': 'Native spherical local fog, source color/phase. Density conversion and sphere are authoring approximations.'}


def import_hein_terrain_textures():
    unreal = ue()
    plans = read(REPORT / 'HeinMachTerrainPlan.json')
    decoded = {r['source_object_path'].rsplit('.', 1)[0]: r for r in
               read(ROOT / 'Saved/Extracted/LookRestoration_20261002/HeinSurface/TargetedTextureManifest.json')}
    assets = {}
    packages = {}
    for plan in plans:
        for layer in plan['layers']:
            for semantic, reference in layer['textures'].items():
                packages[reference['source_package']] = semantic
    for package, semantic in sorted(packages.items()):
        row = decoded[package]
        # Two different source WLT_Snow_003A_D packages must not collide.
        key = row['source_object_name'] + '_' + hashlib.sha256(package.encode()).hexdigest()[:8]
        path = ASSETS + '/HeinMachTerrain/Textures/T_' + key
        asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        if not asset:
            task = unreal.AssetImportTask()
            task.set_editor_property('filename', row['path'])
            task.set_editor_property('destination_path', path.rsplit('/', 1)[0])
            task.set_editor_property('destination_name', path.rsplit('/', 1)[1])
            task.set_editor_property('automated', True)
            task.set_editor_property('factory', unreal.TextureFactory())
            task.set_editor_property('replace_existing', False)
            task.set_editor_property('save', False)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            asset = unreal.load_asset(path)
        if not asset:
            raise RuntimeError('Import failed: ' + package)
        compression = {'diffuse': unreal.TextureCompressionSettings.TC_DEFAULT,
                       'normal': unreal.TextureCompressionSettings.TC_NORMALMAP,
                       'surface': unreal.TextureCompressionSettings.TC_MASKS}[semantic]
        asset.set_editor_property('compression_settings', compression)
        asset.set_editor_property('srgb', semantic == 'diffuse')
        unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
        assets[package] = {'asset': path, 'key': key, 'source': row, 'semantic': semantic}
    weights = {}
    for plan in plans:
        for row in plan['weight_layers']:
            path = ASSETS + '/HeinMachTerrain/Weights/T_HM_' + plan['group'] + '_' + row['material_layer_name']
            asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
            if not asset:
                task = unreal.AssetImportTask()
                task.set_editor_property('factory', unreal.TextureFactory())
                for field, value in [('filename', row['path']), ('destination_path', path.rsplit('/', 1)[0]),
                                      ('destination_name', path.rsplit('/', 1)[1]), ('automated', True), ('save', False)]:
                    task.set_editor_property(field, value)
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                asset = unreal.load_asset(path)
            if not asset:
                raise RuntimeError('Weightmap import failed')
            asset.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
            asset.set_editor_property('srgb', False)
            asset.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
            asset.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
            unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
            weights[plan['group'] + '/' + row['material_layer_name']] = path
    write('HeinMachTerrainTextures', {'surface': assets, 'weights': weights})
    print(json.dumps({'surface_textures': len(assets), 'weightmaps': len(weights)}))


def build_hein_terrain():
    unreal = ue()
    plans = read(REPORT / 'HeinMachTerrainPlan.json')
    native = read(REPORT / 'HeinMachTerrainTextures.json')
    h = runpy.run_path(str(ROOT / 'Scripts/StormPass/restore_stormpass_landscape.py'))
    surface = {r['key']: unreal.load_asset(r['asset']) for r in native['surface'].values()}
    result = []
    for original_plan in plans:
        plan = copy.deepcopy(original_plan)
        group = plan['group']
        for layer in plan['layers']:
            for reference in layer['textures'].values():
                reference['object_name'] = native['surface'][reference['source_package']]['key']
        material = new_asset(ASSETS + '/HeinMachTerrain/Materials/M_HM_SourceWeighted_' + group,
                             unreal.Material, unreal.MaterialFactoryNew())
        unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
        material.set_editor_property('tangent_space_normal', True)
        world = expression(material, unreal.MaterialExpressionWorldPosition, -2600, -800)
        xy = h['pin'](world, 'XY')
        location = plan['root_location']
        scale = plan['root_scale']
        local = h['divide'](material, h['subtract'](material, xy,
                h['constant2'](material, location['X'], location['Y'], -2600, -600), -2300, -800),
                h['constant2'](material, scale['X'], scale['Y'], -2300, -600), -2000, -800)
        center = h['add'](material, h['subtract'](material, local,
                 h['constant2'](material, *plan['min_section'], -2000, -600), -1750, -800),
                 h['constant2'](material, 0.5, 0.5, -1750, -600), -1500, -800)
        uv = h['divide'](material, center, h['constant2'](material, *plan['dimensions'], -1500, -600), -1250, -800)
        landscape = {'weight_layers': plan['weight_layers']}
        weights = {(group, r['material_layer_name']): unreal.load_asset(native['weights'][group+'/'+r['material_layer_name']])
                   for r in plan['weight_layers']}
        samples, used_weights = h['create_weight_samples'](material, group, landscape, uv, weights)
        # Puddle is applied after blending the ground. It is not a fallback
        # layer and must not invalidate the generic ground-layer contract.
        base_samples = {k: v for k, v in samples.items() if k != 'Puddle'}
        outputs, used_surface = h['build_weight_blend'](material, group, plan, xy, base_samples, surface)
        outputs, puddle = h['apply_puddle'](material, outputs, plan, samples)
        h['connect_outputs'](material, outputs)
        specular = scalar(material, 'GlobalSpecular_Source_OP', 0.5, 2600, 1800)
        unreal.MaterialEditingLibrary.connect_material_property(specular, '', unreal.MaterialProperty.MP_SPECULAR)
        stats = compile_save(material)
        result.append({**stats, 'group': group, 'source_material': plan['source_material'],
                       'layers': len(plan['layers']), 'source_texture_count': len(used_weights | used_surface),
                       'source_weight_uv_formula': '((WorldXY - SourceRootXY) / SourceScaleXY - MinSectionXY + 0.5) / DimensionsXY',
                       'root_location': location, 'min_section': plan['min_section'], 'dimensions': plan['dimensions'],
                       'puddle': puddle, 'boundary': plan['boundary']})
    write('HeinMachTerrainCompilation', result)
    print(json.dumps(result))


def build_hein_sky():
    unreal = ue()
    path = EXTRACT / 'BBQ/Content/Art/ArtRendering/AR_Data/SkyMaterial/SCM_SkyColor_GloomySunset.json'
    source = read(path)[0]['Properties']
    parent = unreal.load_asset('/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/Materials/M_SP_SourceSky_V2')
    assert parent
    instance = new_asset(ASSETS + '/Materials/MI_HM_SourceSky_GloomySunset',
                         unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(instance, parent)
    scalars = set(str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(parent))
    vectors = set(str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(parent))
    omitted = []
    for row in source.get('ScalarParameterValues', []):
        name = row['ParameterInfo']['Name']
        if name in scalars:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, name, row['ParameterValue'])
        else:
            omitted.append(name)
    for row in source.get('VectorParameterValues', []):
        name = row['ParameterInfo']['Name']
        if name in vectors:
            value = row['ParameterValue']
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(instance, name,
                  unreal.LinearColor(*(value.get(c, 1 if c == 'A' else 0) for c in ('R', 'G', 'B', 'A'))))
        else:
            omitted.append(name)
    unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
    write('HeinMachSky', {'asset': instance.get_path_name(), 'source_json': str(path),
                        'source_sha256': digest(path), 'omitted_parameters': omitted,
                        'boundary': 'Native sky gradient adapter; original procedural sky functions are unavailable.'})
    return instance


def load_level(level):
    unreal = ue()
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None:
        raise RuntimeError('Editor has no authoring world. Do not run during PIE.')
    if world.get_path_name().split('.')[0] != MAPS[level]:
        dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        if dirty:
            raise RuntimeError('Preserve current dirty map before switching: ' + repr([p.get_name() for p in dirty]))
        if not subsystem.load_level(MAPS[level]):
            raise RuntimeError('Could not load ' + MAPS[level])
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def apply_hein():
    unreal = ue()
    world = load_level('HeinMach')
    by = {a.get_actor_label(): a for a in actors()}
    before = read(REPORT / 'HeinMach_Before.json')
    original_start = next(r for r in before if r['class'] == 'PlayerStart')
    assert pose(by[original_start['label']]) == original_start['pose'], 'Preserve user-moved HeinMach PlayerStart'
    source = read(REPORT / 'SourceManifest.json')
    bridge = runpy.run_path(str(ROOT / 'Scripts/StormPass/restore_stormpass_environment_profile.py'))
    ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rows = []
    for row in source['HeinMach_volumes']:
        label = 'HM_Environment_PP_HeinMach_Light_' + str(row['source_actor_index'])
        actor = by.get(label)
        if not actor:
            actor = ac.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
            actor.set_actor_label(label)
        actor.set_folder_path('HeinMach/Reconstructed/Environment/PostProcess/' + row['profile'])
        center, rotation, scale = bridge['volume_proxy_transform'](row)
        actor.set_actor_location(center, False, False)
        actor.set_actor_rotation(rotation, False)
        actor.set_actor_scale3d(scale)
        for name in ('unbound', 'priority', 'blend_radius', 'blend_weight', 'enabled'):
            actor.set_editor_property(name, row[name])
        settings_report = native_pp_settings(actor, source['HeinMach'][row['profile']])
        instance = toon_instance('HeinMach', row['profile'])
        bind_toon(actor, instance)
        rows.append({'label': label, 'pose': pose(actor), 'source': row, 'post_process': settings_report,
                     'toon_instance': instance.get_path_name()})
    fallback = by['HM_PreviewPostProcess']
    fallback.set_editor_property('priority', -100.0)
    fallback.set_editor_property('unbound', True)
    # Keep fallback exposure calibrated by the prior restoration. The source
    # bounded WEPs own their individual exposure and color grade overrides.
    bind_toon(fallback, toon_instance('HeinMach', 'OP'))
    profile = source['HeinMach']['OP']
    d = profile['components']['directional_light']['properties']
    c = by['HM_PreviewSun'].get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property('light_color', bridge['fcolor'](d['LightColor']))
    native_sun_lux = c.get_editor_property('intensity')
    r = d.get('RelativeRotation') or {}
    by['HM_PreviewSun'].set_actor_rotation(unreal.Rotator(pitch=r.get('Pitch', 0), yaw=r.get('Yaw', 0), roll=r.get('Roll', 0)), False)
    # Retain current native lux: BBQ light intensity does not expose a proven
    # physical unit conversion. Color/rotation are directly source-backed.
    s = profile['components']['sky_light']['properties']
    sky = by['HM_PreviewSkyLight'].get_component_by_class(unreal.SkyLightComponent)
    sky.set_editor_property('light_color', bridge['fcolor'](s['LightColor']))
    sky.set_editor_property('intensity', float(s['Intensity']))
    sky.set_editor_property('lower_hemisphere_color', bridge['linear_color'](s['LowerHemisphereColor']))
    sky.set_editor_property('lower_hemisphere_is_black', False)
    material = unreal.load_asset(ASSETS + '/Materials/MI_HM_SourceSky_GloomySunset')
    assert material
    actor = by.get('HM_Environment_SourceSkyMesh')
    if not actor:
        actor = ac.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
        actor.set_actor_label('HM_Environment_SourceSkyMesh')
    actor.set_folder_path('HeinMach/Reconstructed/Environment/Sky')
    mesh = unreal.load_asset('/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/Meshes/WAS_SkyMesh/WAS_SkyMesh/StaticMeshes/SM_WAS_SkyMesh')
    mc = actor.get_component_by_class(unreal.StaticMeshComponent)
    mc.set_static_mesh(mesh)
    mc.set_material(0, material)
    mc.set_editor_property('cast_shadow', False)
    mc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    # Fit the original shared sky proxy around all remaining terrain/props.
    # Radius is derived from the existing scene envelope, not a source scale.
    existing = [a for a in actors() if a.get_actor_label().startswith(('HM_Prop_', 'HM_Landscape_'))]
    extent = max(max(abs(center.x) + bounds.x, abs(center.y) + bounds.y)
                 for a in existing for center, bounds in [a.get_actor_bounds(False)])
    _, native_extent = actor.get_actor_bounds(False)
    scale = max(1.0, (extent * 2) / max(native_extent.x, native_extent.y))
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    by['HM_PreviewSkyAtmosphere'].set_actor_hidden_in_game(True)
    for comp in by['HM_PreviewSkyAtmosphere'].get_components_by_class(unreal.SceneComponent):
        comp.set_visibility(False, True)
    sky.recapture_sky()
    fog = profile['components']['fog']['properties']
    actor_fog = by['HM_PreviewVolumetricFog']
    component = actor_fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_settings = [('fog_density', fog['FogDensity'] * NATIVE['FogDensityScale']),
                    ('fog_height_falloff', fog['FogHeightFalloff'] * NATIVE['FogFalloffScale']),
                    ('fog_inscattering_luminance', bridge['linear_color'](fog['FogInscatteringColor'])),
                    ('fog_max_opacity', fog['FogMaxOpacity']), ('enable_volumetric_fog', True),
                    ('volumetric_fog_albedo', bridge['fcolor'](fog['VolumetricFogAlbedo'])),
                    ('volumetric_fog_emissive', bridge['linear_color'](fog['VolumetricFogEmissive'])),
                    ('volumetric_fog_distance', fog['VolumetricFogDistance']),
                    ('volumetric_fog_extinction_scale', fog['VolumetricFogExtinctionScale'])]
    for name, value in fog_settings:
        component.set_editor_property(name, value)
    terrain_assignments = []
    for a in actors():
        label = a.get_actor_label()
        group = next((n for n in ('Landscape1', 'Landscape2') if label.startswith('HM_Landscape_'+n+'_') or label == 'HM_Terrain_'+n), None)
        if not group:
            continue
        material = unreal.load_asset(ASSETS + '/HeinMachTerrain/Materials/M_HM_SourceWeighted_' + group)
        if not material:
            raise RuntimeError('Build weighted terrain first')
        for c in a.get_components_by_class(unreal.MeshComponent):
            for i in range(c.get_num_materials()):
                c.set_material(i, material)
        terrain_assignments.append({'label': label, 'material': material.get_path_name()})
    assert pose(by[original_start['label']]) == original_start['pose']
    unreal.SystemLibrary.execute_console_command(world, 'r.CustomDepth 3')
    unreal.SystemLibrary.execute_console_command(world, 'r.VolumetricFog 1')
    write('HeinMachApplied', {'post_process': rows, 'terrain_assignments': terrain_assignments,
                            'preserved_PlayerStart': original_start,
                            'source_OP_sun_color': d['LightColor'], 'retained_native_sun_lux': native_sun_lux,
                            'global_environment_boundary': 'Startup OP sky/fog/direct light. Bounded source WEP color-grade and toon profiles restored; runtime WEP light/fog blending remains unavailable.'})
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
        raise RuntimeError('Could not save HeinMach')
    print(json.dumps({'level': 'HeinMach', 'bounded_source_PP': len(rows), 'terrain_actors': len(terrain_assignments), 'actor_count': len(actors()), 'PlayerStart_preserved': True}))


def shifted_background_material():
    unreal = ue()
    src = '/Game/_Art/Player/Environment/StormPass/Reconstructed/Landscape/Materials/M_SP_Landscape_Main'
    dst = ASSETS + '/Materials/M_SP_Phase2_DistantLandscape'
    material = unreal.load_asset(dst) if unreal.EditorAssetLibrary.does_asset_exist(dst) else None
    if not material:
        material = unreal.EditorAssetLibrary.duplicate_asset(src, dst)
    assert material
    delta = read(SPMETA / 'BladePhantom_SideBySide_20261002/Layout.json')['source_phase2_translation_cm'][0]
    # Only the weight-grid origin changes. Surface tile UV is compensated
    # independently, preserving original texture phase after translation.
    for node in unreal.MaterialEditingLibrary.get_material_expressions(material):
        if isinstance(node, unreal.MaterialExpressionConstant2Vector):
            if node.get_editor_property('r') == -25200 and node.get_editor_property('g') == -25200:
                node.set_editor_property('r', -25200 + delta)
    compensate_surface_uv(material, delta)
    compile_save(material)
    return material


def compensate_surface_uv(material, delta):
    unreal = ue()
    lib = unreal.MaterialEditingLibrary
    nodes = list(lib.get_material_expressions(material))
    if any(n.get_editor_property('desc') == 'KZ source surface UV translation compensation' for n in nodes):
        return
    world_nodes = [n for n in nodes if isinstance(n, unreal.MaterialExpressionWorldPosition)]
    for world in world_nodes:
        targets = [n for n in nodes if isinstance(n, unreal.MaterialExpressionDivide) and
                   world in list(lib.get_inputs_for_material_expression(material, n))]
        if not targets:
            continue
        offset = expression(material, unreal.MaterialExpressionConstant2Vector, -2600, 4500)
        offset.set_editor_property('r', delta)
        offset.set_editor_property('g', 0.0)
        subtract = expression(material, unreal.MaterialExpressionSubtract, -2300, 4500)
        subtract.set_editor_property('desc', 'KZ source surface UV translation compensation')
        connect(world, 'XY', subtract, 'A')
        connect(offset, '', subtract, 'B')
        for target in targets:
            connect(subtract, '', target, 'A')


def apply_storm():
    unreal = ue()
    world = load_level('StormPass')
    by = {a.get_actor_label(): a for a in actors()}
    source = read(REPORT / 'SourceManifest.json')
    layout = read(SPMETA / 'BladePhantom_SideBySide_20261002/Layout.json')
    bridge = runpy.run_path(str(ROOT / 'Scripts/StormPass/restore_stormpass_environment_profile.py'))
    profiles = source['StormPass']
    rows = []
    for phase, label in [(1, 'SP_Environment_PP_StormPass_Boss_Phase_1_117'),
                         (2, 'SP_Environment_PP_StormPass_Boss_Phase_2_244')]:
        actor = by[label]
        key = 'boss_phase_' + str(phase)
        # Preserve the user's reviewed dark castle exposure/torch treatment.
        settings = native_pp_settings(actor, profiles[key]) if phase == 2 else {'preserved_phase1_light_review': True}
        if phase == 2:
            native = actor.get_editor_property('settings')
            for field, value in [('auto_exposure_min_brightness', NATIVE['Phase2FixedEV100']),
                                 ('auto_exposure_max_brightness', NATIVE['Phase2FixedEV100']),
                                 ('bloom_intensity', NATIVE['Phase2BloomIntensity']),
                                 ('color_saturation', unreal.Vector4(NATIVE['Phase2SaturationNative'], NATIVE['Phase2SaturationNative'], NATIVE['Phase2SaturationNative'], 1)),
                                 ('color_saturation_shadows', unreal.Vector4(NATIVE['Phase2ShadowSaturationNative'], NATIVE['Phase2ShadowSaturationNative'], NATIVE['Phase2ShadowSaturationNative'], 1))]:
                native.set_editor_property(field, value)
                native.set_editor_property('override_' + field, True)
            actor.set_editor_property('settings', native)
            settings['temporary_native_exposure_correction'] = {k: NATIVE[k] for k in ('Phase2FixedEV100', 'Phase2BloomIntensity', 'Phase2SaturationNative', 'Phase2ShadowSaturationNative')}
        bind_toon(actor, toon_instance('StormPass', key))
        actor.set_editor_property('enabled', True)
        rows.append({'label': label, 'post_process': settings})
    fallback = by['SP_Environment_PostProcessFallback']
    fallback.set_editor_property('settings', unreal.PostProcessSettings())
    fallback.set_editor_property('priority', -100.0)
    bind_toon(fallback, toon_instance('StormPass', 'boss_phase_2'))
    for phase, label in [(1, 'SP_Environment_DirectionalLight'), (2, 'SP_BP_Phase2_Sun')]:
        actor = by[label]
        c = actor.get_component_by_class(unreal.DirectionalLightComponent)
        material = unreal.load_asset(ASSETS + '/Materials/M_SP_Phase%d_SunMask' % phase)
        assert material
        c.set_editor_property('light_function_material', material)
        c.set_editor_property('disabled_brightness', 0.0)
        environment_scalars = {r['ParameterName']: r['ScalarValue'] for r in profiles['boss_phase_2']['components']['environment_material']['properties']['ScalarValues']}
        c.set_editor_property('light_function_fade_distance', environment_scalars['WorldPropDistanceMax'])
        c.set_lighting_channels(True, True, False)
        c.set_editor_property('forward_shading_priority', phase - 1)
        d = profiles['boss_phase_' + str(phase)]['components']['directional_light']['properties']
        c.set_editor_property('light_color', bridge['fcolor'](d['LightColor']))
    sky_report = read(SPMETA / 'BladePhantom_ArenaPolish_20261001/SkyPresets.json')
    sky_material = unreal.load_asset(sky_report['assets']['boss_phase_2']['asset'])
    assert sky_material
    backup_asset(sky_material)
    # Previously the source StarBrightness was stored but the native branch
    # was multiplied by a preview-only zero, so the night sky had no stars.
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(sky_material, 'PreviewStarVisibility', 1.0)
    unreal.EditorAssetLibrary.save_loaded_asset(sky_material, only_if_is_dirty=False)
    by['SP_Environment_SkyMesh'].get_component_by_class(unreal.StaticMeshComponent).set_material(0, sky_material)
    profile = profiles['boss_phase_2']
    s = profile['components']['sky_light']['properties']
    sky = by['SP_Environment_SkyLight'].get_component_by_class(unreal.SkyLightComponent)
    sky.set_editor_property('intensity', s['Intensity'])
    sky.set_editor_property('light_color', bridge['fcolor'](s['LightColor']))
    sky.set_editor_property('lower_hemisphere_color', bridge['linear_color'](s['LowerHemisphereColor']))
    sky.set_editor_property('lower_hemisphere_is_black', False)
    sky.recapture_sky()
    for label in ('SP_Environment_Cloud_0', 'SP_Environment_Cloud_1'):
        by[label].set_actor_hidden_in_game(True)  # Both source cloud intensities are zero.
    fog = profile['components']['fog']['properties']
    actor = by['SP_Environment_HeightFog']
    floor = layout['collision_floors'][1]['support_top_z_cm']
    actor.set_actor_location(unreal.Vector(183040, 51600, floor + fog['CameraFollowOffset']['Z']), False, False)
    c = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    values = [('fog_density', fog['FogDensity'] * NATIVE['FogDensityScale']),
              ('fog_height_falloff', fog['FogHeightFalloff'] * NATIVE['FogFalloffScale']),
              ('fog_inscattering_luminance', bridge['linear_color'](fog['FogInscatteringColor'])),
              ('fog_max_opacity', fog['FogMaxOpacity']), ('enable_volumetric_fog', True),
              ('volumetric_fog_albedo', bridge['fcolor'](fog['VolumetricFogAlbedo'])),
              ('volumetric_fog_emissive', bridge['linear_color'](fog['VolumetricFogEmissive'])),
              ('volumetric_fog_distance', fog['VolumetricFogDistance']),
              ('volumetric_fog_extinction_scale', fog['VolumetricFogExtinctionScale'])]
    for name, value in values:
        c.set_editor_property(name, value)
    local = []
    for phase, radius in [(1, NATIVE['Phase1LocalFogRadiusCm']), (2, NATIVE['Phase2LocalFogRadiusCm'])]:
        # Author-selected local spheres fit inside the separated arena scene.
        # Radii are temporary scene adapters, not original fog volume shapes.
        center = layout['markers'][phase-1]['location_cm']
        local.append(local_fog('SP_BP_Phase%d_LocalFog' % phase, center, radius,
                               profiles['boss_phase_'+str(phase)], 'StormPass/01_BladePhantom/Environment',
                               NATIVE['Phase2LocalFogDensityScale'] if phase == 2 else NATIVE['LocalFogDensityScale']))
    native_landscape = unreal.load_asset(layout['landscape_material'])
    backup_asset(native_landscape)
    compensate_surface_uv(native_landscape, layout['source_phase2_translation_cm'][0])
    # The source covering color had no native material consumer.
    # Weight is a recorded temporary native interpretation of the global tint.
    lib = unreal.MaterialEditingLibrary
    nodes = list(lib.get_material_expressions(native_landscape))
    cover = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name')) == 'Covering_Diffuse')
    outputs = [n for n in nodes if isinstance(n, unreal.MaterialExpressionLinearInterpolate) and cover in list(lib.get_inputs_for_material_expression(native_landscape, n))]
    global_vectors = {r['ParameterName']: r['VectorValue'] for r in profile['components']['environment_material']['properties']['VectorValues']}
    if not any(n.get_editor_property('desc') == 'KZ source covering color native adapter' for n in nodes):
        color = vector(native_landscape, 'CoveringColor_Source_Phase2', [global_vectors['CoveringColor'][k] for k in ('R', 'G', 'B', 'A')], -950, 5300)
        weight = scalar(native_landscape, 'CoveringColorWeight_Native', NATIVE['CoveringColorWeight'], -950, 5450)
        tint = expression(native_landscape, unreal.MaterialExpressionCustom, -650, 5300)
        tint.set_editor_property('desc', 'KZ source covering color native adapter')
        tint.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        tint.set_editor_property('inputs', [custom_input('Diffuse'), custom_input('SourceColor'), custom_input('Weight')])
        tint.set_editor_property('code', 'return Diffuse.rgb * lerp(float3(1,1,1), SourceColor.rgb, saturate(Weight));')
        connect(cover, 'RGB', tint, 'Diffuse')
        connect(color, 'RGB', tint, 'SourceColor')
        connect(weight, '', tint, 'Weight')
        for target in outputs:
            connect(tint, '', target, 'B')
    for node in lib.get_material_expressions(native_landscape):
        if isinstance(node, unreal.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name')) == 'CoveringColorWeight_Native':
            node.set_editor_property('default_value', NATIVE['CoveringColorWeight'])
    compile_save(native_landscape)
    background = read(REPORT / 'StormPassBackgroundPlan.json')
    background_material = shifted_background_material()
    for row in background['retained_main_components']:
        a = by[row['label']]
        p = row['pose']['location']
        a.set_actor_location(unreal.Vector(p[0] + layout['source_phase2_translation_cm'][0], p[1], p[2]), False, False)
        component = a.get_component_by_class(unreal.StaticMeshComponent)
        component.set_material(0, background_material)
        component.set_lighting_channels(False, True, False)
        a.set_folder_path('StormPass/01_BladePhantom/Phase2/BackgroundTerrain')
    start = next(a for a in by.values() if isinstance(a, unreal.PlayerStart))
    # Old mission-route spawn would be outside the retained boss-only scene.
    entry = by['SP_BP_Phase1_PlayerEntry_Mission02_Start_BossZone']
    old_start = next(r['pose'] for r in read(REPORT / 'StormPass_Before.json') if r['label'] == start.get_actor_label())
    start.set_actor_location(entry.get_actor_location(), False, False)
    start.set_actor_rotation(entry.get_actor_rotation(), False)
    write('StormPassApplied', {'post_process': rows, 'global_sky': sky_material.get_path_name(),
                             'global_sky_source': sky_report['source_presets']['SkyColor_DeepNight'],
                             'local_fog': local, 'covering_color_source': global_vectors['CoveringColor'],
                             'covering_color_weight_native': NATIVE['CoveringColorWeight'],
                             'background_components': [r['label'] for r in background['retained_main_components']],
                             'PlayerStart_before': old_start, 'PlayerStart_after': pose(start), 'PlayerStart_source_entry': entry.get_actor_label(),
                             'boundary': 'Source phase palette/sky/fog settings; native spherical fog and shared Phase2 skylight/GI. Full runtime proprietary WEP blend remains unavailable.'})
    unreal.SystemLibrary.execute_console_command(world, 'r.CustomDepth 3')
    unreal.SystemLibrary.execute_console_command(world, 'r.VolumetricFog 1')
    print(json.dumps({'StormPass_environment_applied': True, 'local_fog': len(local), 'background_components': len(background['retained_main_components']), 'PlayerStart': pose(start)}))


def phase2_surface_adapters():
    """Consume missing EMP covering/pollution globals only in Phase2.

    Source colors and weights are exact; mask, glow scaling and native water
    coefficients are authoring formulas, not recovered cooked BBQ expressions.
    Phase1 parents and shared source instances are never rewritten here.
    """
    unreal = ue()
    load_level('StormPass')
    lib = unreal.MaterialEditingLibrary
    profile = read(REPORT / 'SourceManifest.json')['StormPass']['boss_phase_2']
    emp = profile['components']['environment_material']['properties']
    sv = {r['ParameterName']: r['VectorValue'] for r in emp['VectorValues']}
    ss = {r['ParameterName']: r['ScalarValue'] for r in emp['ScalarValues']}
    def color(key):
        return [sv[key][k] for k in ('R', 'G', 'B', 'A')]
    def duplicate(src, dst):
        asset = unreal.load_asset(dst)
        if asset:
            backup_asset(asset)
        else:
            asset = unreal.EditorAssetLibrary.duplicate_asset(src, dst)
        if not asset:
            raise RuntimeError('Duplicate failed: ' + dst)
        return asset
    parents = {}
    compiled = []
    for key, src in [
        ('World', '/Game/_Art/Player/Environment/StormPass/Reconstructed/MaterialRepairs/Surfaces/M_SP_WorldSurface_Native'),
        ('Trees', '/Game/_Art/Player/Environment/StormPass/Reconstructed/MaterialRepairs/Trees/M_SP_SourceTreeFoliage_V2')]:
        parent = duplicate(src, ASSETS + '/Materials/M_SP_Phase2_' + key + '_Covering')
        nodes = list(lib.get_material_expressions(parent))
        tint = next((n for n in nodes if n.get_editor_property('desc') == 'KZ Phase2 source covering; native snow mask'), None)
        if not tint:
            base = lib.get_material_property_input_node(parent, unreal.MaterialProperty.MP_BASE_COLOR)
            out = lib.get_material_property_input_node_output_name(parent, unreal.MaterialProperty.MP_BASE_COLOR)
            if not base:
                raise RuntimeError('Native parent has no base-color input')
            tint = expression(parent, unreal.MaterialExpressionCustom, 2200, 0)
            tint.set_editor_property('desc', 'KZ Phase2 source covering; native snow mask')
            tint.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
            tint.set_editor_property('inputs', [custom_input(n) for n in ('Diffuse', 'UpNormal', 'SourceColor', 'SourceWeight', 'Weight', 'LumaStart', 'LumaEnd', 'Neutrality', 'UpWeight', 'BaseMask')])
            tint.set_editor_property('code', '''
float luma = dot(Diffuse.rgb, float3(0.2126,0.7152,0.0722));
float spread = max(Diffuse.r,max(Diffuse.g,Diffuse.b))-min(Diffuse.r,min(Diffuse.g,Diffuse.b));
float neutral = 1.0-saturate(spread/max(Neutrality,0.0001));
float up = saturate(normalize(UpNormal.xyz).z);
float mask = max(BaseMask,smoothstep(LumaStart,LumaEnd,luma)*neutral)*lerp(1.0,up,saturate(UpWeight));
return Diffuse.rgb*lerp(float3(1,1,1),SourceColor.rgb,saturate(mask*SourceWeight*Weight));
''')
            connect(base, out, tint, 'Diffuse')
            normal = expression(parent, unreal.MaterialExpressionVertexNormalWS, 1600, 500)
            connect(normal, '', tint, 'UpNormal')
            c = vector(parent, 'KZ_CoveringColor_Source', color('CoveringColor'), 1400, 600)
            connect(c, 'RGB', tint, 'SourceColor')
            defs = [('SourceWeight', 'KZ_EnvCoverWeight_Source', ss['EnvCoverWeight']),
                    ('Weight', 'KZ_CoveringWeight_Native', NATIVE['CoveringColorWeight']),
                    ('LumaStart', 'KZ_SnowLumaStart_Native', NATIVE['SnowLuminanceStart']),
                    ('LumaEnd', 'KZ_SnowLumaEnd_Native', NATIVE['SnowLuminanceEnd']),
                    ('Neutrality', 'KZ_SnowNeutrality_Native', NATIVE['SnowNeutralityTolerance']),
                    ('UpWeight', 'KZ_SnowUpWeight_Native', NATIVE['SnowUpNormalWeight']),
                    ('BaseMask', 'KZ_CoveringBaseMask_Native', NATIVE['WorldCoveringBaseMask'] if key == 'World' else NATIVE['FoliageCoveringBaseMask'])]
            for i, (pin, name, value) in enumerate(defs):
                connect(scalar(parent, name, value, 1400, 800+i*120), '', tint, pin)
            if not lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR):
                raise RuntimeError('Cover tint output failed')
            # Reuse the exact native mask for the missing global glow. Existing
            # material emissive remains intact; 300 is not used as direct HDR.
            glow = expression(parent, unreal.MaterialExpressionCustom, 2450, 600)
            glow.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
            glow.set_editor_property('inputs', [custom_input(n) for n in ('Diffuse','Tinted','SourceGlow','Scale')])
            glow.set_editor_property('code', 'float m=saturate((Diffuse.g-Tinted.g)/max(Diffuse.g,0.0001)); return SourceGlow.rgb*Scale*m;')
            connect(base, out, glow, 'Diffuse')
            connect(tint, '', glow, 'Tinted')
            connect(vector(parent, 'KZ_CoveringGlowColor_Source', color('CoveringGlowColor'), 2000, 900), 'RGB', glow, 'SourceGlow')
            connect(scalar(parent, 'KZ_CoveringGlowScale_Native', NATIVE['CoveringGlowScale'], 2000, 1050), '', glow, 'Scale')
            old_e = lib.get_material_property_input_node(parent, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            if old_e:
                old_out = lib.get_material_property_input_node_output_name(parent, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                add = expression(parent, unreal.MaterialExpressionAdd, 2750, 600)
                connect(old_e, old_out, add, 'A')
                connect(glow, '', add, 'B')
                glow = add
            lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        parents[src] = parent
        compiled.append(compile_save(parent))
    assignments = []
    originals = {}
    by = {a.get_actor_label(): a for a in actors()}
    for a in by.values():
        if 'StormPass_Boss_Phase_2' not in a.get_actor_label():
            continue
        for component in a.get_components_by_class(unreal.MeshComponent):
            for slot in range(component.get_num_materials()):
                mi = component.get_material(slot)
                if not isinstance(mi, unreal.MaterialInstanceConstant):
                    continue
                p = mi.get_editor_property('parent')
                parent = parents.get(p.get_path_name().split('.')[0]) if p else None
                if not parent:
                    continue
                src = mi.get_path_name().split('.')[0]
                originals.setdefault(src, p.get_path_name())
                if '/BladePhantomPolish/Phase2/Materials/' in src:
                    backup_asset(mi)
                    dst = mi
                else:
                    suffix = hashlib.sha256(src.encode()).hexdigest()[:8]
                    dst = duplicate(src, ASSETS + '/Phase2Covering/MI_' + mi.get_name().removeprefix('MI_') + '_' + suffix)
                lib.set_material_instance_parent(dst, parent)
                unreal.EditorAssetLibrary.save_loaded_asset(dst, only_if_is_dirty=False)
                component.set_material(slot, dst)
                assignments.append({'actor': a.get_actor_label(), 'component': component.get_name(), 'slot': slot,
                                    'before': src, 'after': dst.get_path_name()})
    # Flatten the effective water MI into a dedicated Phase2 native parent;
    # its original albedo, absorption, textures and all source parameters remain
    # present. Add the WEP pollution consumer instead of overwriting raw values.
    water_src = '/Game/_Art/Player/Environment/StormPass/Reconstructed/WaterAssets/Materials/M_SP_Water_Material_AK_Preview'
    water = duplicate(water_src, ASSETS + '/Materials/M_SP_Phase2_SourcePollution_Water')
    nodes = list(lib.get_material_expressions(water))
    if not any(n.get_editor_property('desc') == 'KZ source pollution native water adapter' for n in nodes):
        base = lib.get_material_property_input_node(water, unreal.MaterialProperty.MP_BASE_COLOR)
        out = lib.get_material_property_input_node_output_name(water, unreal.MaterialProperty.MP_BASE_COLOR)
        pollution = vector(water, 'KZ_SurfacePollutionColorHeight_Source', color('SurfacePollutionColorHeight'), 3000, 300)
        weight = scalar(water, 'KZ_WaterPollutionWeight_Native', NATIVE['WaterPollutionWeight'], 3000, 450)
        tint = expression(water, unreal.MaterialExpressionCustom, 3350, 0)
        tint.set_editor_property('desc', 'KZ source pollution native water adapter')
        tint.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        tint.set_editor_property('inputs', [custom_input(n) for n in ('Base','Color','Weight')])
        tint.set_editor_property('code', 'float luma=dot(Base.rgb,float3(0.2126,0.7152,0.0722)); return lerp(Base.rgb,Color.rgb*lerp(0.5,1.0,saturate(luma*4.0)),saturate(Weight));')
        connect(base, out, tint, 'Base')
        connect(pollution, 'RGB', tint, 'Color')
        connect(weight, '', tint, 'Weight')
        lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
        wo = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionSingleLayerWaterMaterialOutput))
        input_names = [str(x) for x in lib.get_material_expression_input_names(wo)]
        absorption_pin = next(x for x in input_names if 'absorption' in x.lower())
        albedo_pin = next(x for x in input_names if 'color' in x.lower())
        source_abs = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name')) == 'Absorption')
        albedo = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name')) == 'Water Albedo')
        absorb = expression(water, unreal.MaterialExpressionCustom, 3350, 600)
        absorb.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        absorb.set_editor_property('inputs', [custom_input(n) for n in ('SourceAbsorption','Color','Weight','Density')])
        absorb.set_editor_property('code', 'return lerp(SourceAbsorption.rgb*0.002,(1.0-saturate(Color.rgb))*Density,saturate(Weight));')
        connect(source_abs, 'RGB', absorb, 'SourceAbsorption')
        connect(pollution, 'RGB', absorb, 'Color')
        connect(weight, '', absorb, 'Weight')
        connect(scalar(water, 'KZ_PollutionAbsorptionPerCm_Native', NATIVE['WaterPollutionAbsorptionPerCm'], 3000, 900), '', absorb, 'Density')
        connect(absorb, '', wo, absorption_pin)
        behind = expression(water, unreal.MaterialExpressionLinearInterpolate, 3350, 1050)
        connect(albedo, 'RGB', behind, 'A')
        connect(pollution, 'RGB', behind, 'B')
        connect(weight, '', behind, 'Alpha')
        connect(behind, '', wo, albedo_pin)
    compiled.append(compile_save(water))
    original_path = '/Game/_Art/Player/Environment/StormPass/Reconstructed/WaterAssets/Materials/MI_SP_Water_Boss_Phase_2_Actor_02538'
    original = unreal.load_asset(original_path)
    dst = duplicate(original_path, ASSETS + '/Phase2Covering/MI_SP_Phase2_SourcePollution_Water')
    lib.set_material_instance_parent(dst, water)
    for name in lib.get_scalar_parameter_names(original):
        lib.set_material_instance_scalar_parameter_value(dst, name, lib.get_material_instance_scalar_parameter_value(original, name))
    for name in lib.get_vector_parameter_names(original):
        lib.set_material_instance_vector_parameter_value(dst, name, lib.get_material_instance_vector_parameter_value(original, name))
    for name in lib.get_texture_parameter_names(original):
        value = lib.get_material_instance_texture_parameter_value(original, name)
        if value:
            lib.set_material_instance_texture_parameter_value(dst, name, value)
    unreal.EditorAssetLibrary.save_loaded_asset(dst, only_if_is_dirty=False)
    wa = by['SP_ChildProp_StormPass_Boss_Phase_2_02538_00179']
    wa.get_component_by_class(unreal.StaticMeshComponent).set_material(0, dst)
    write('Phase2GlobalMaterialConsumers', {'source_EMP': emp, 'native_controls': NATIVE,
           'surface_assignments': assignments, 'original_parents': originals,
           'compiled': compiled, 'water_original': original_path, 'water_native': dst.get_path_name(),
           'boundary': 'Source covering/glow/pollution colors exact; diffuse-neutrality snow mask, HDR glow scale and SingleLayerWater coefficients are native approximations. No source engine shader recovered.'})
    print(json.dumps({'phase2_surface_slots': len(assignments), 'phase2_unique_source_MIs': len(originals),
                      'water': dst.get_path_name(), 'compiled': compiled}))


def storm_prune_plan():
    unreal = ue()
    load_level('StormPass')
    current = {a.get_actor_label(): a for a in actors()}
    before = {r['label']: r for r in read(REPORT / 'StormPass_Before.json')}
    baseline = read(SPMETA / 'StormPass_PhaseVisibilityBaseline_20260907.json')
    keep = {r['label'] for r in baseline['actors'] if r['variant'] in ('boss_phase_1', 'boss_phase_2')}
    keep.update(r['label'] for r in read(REPORT / 'StormPassBackgroundPlan.json')['retained_main_components'])
    keep.update(n for n in current if n.startswith('SP_BP_'))
    keep.update(n for n, a in current.items() if isinstance(a, unreal.PlayerStart))
    keep.update({'SP_Environment_DirectionalLight', 'SP_Environment_SkyLight', 'SP_Environment_SkyMesh',
                 'SP_Environment_HeightFog', 'SP_Environment_Cloud_0', 'SP_Environment_Cloud_1',
                 'SP_Environment_Wind', 'SP_Environment_PostProcessFallback'})
    removed = [row for n, row in before.items() if n in current and n.startswith('SP_') and n not in keep]
    # Never delete new user-created actors not present in the immutable snapshot.
    result = {'scope': 'User authorized boss-only StormPass; keep both arenas and their source background objects/foliage/terrain',
              'keep_labels': sorted(n for n in keep if n in current), 'remove': removed,
              'protected_new_or_nonmanaged': sorted(n for n in current if n not in before or not n.startswith('SP_')),
              'count_before': len(current), 'remove_count': len(removed)}
    write('StormPassPrunePlan', result)
    print(json.dumps({'actor_count': len(current), 'keep': len(result['keep_labels']), 'remove': len(removed),
                      'both_markers_retained': all(m['label'] in keep for m in read(SPMETA / 'BladePhantom_SideBySide_20261002/Layout.json')['markers'])}))
    return result


def prune_storm_batch(offset=0, limit=2000):
    unreal = ue()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world and world.get_path_name().split('.')[0] == MAPS['StormPass']
    plan = read(REPORT / 'StormPassPrunePlan.json')
    by = {a.get_actor_label(): a for a in actors()}
    ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    deleted = 0
    for row in plan['remove'][offset:offset+limit]:
        a = by.get(row['label'])
        if a:
            if not ac.destroy_actor(a):
                raise RuntimeError('Could not remove ' + row['label'])
            deleted += 1
    print(json.dumps({'offset': offset, 'deleted': deleted, 'remaining_actors': len(actors()), 'prune_plan_total': len(plan['remove'])}))


def connect_source_sky_controls():
    """Add real native consumers for previously stored-only sky controls."""
    unreal = ue()
    lib = unreal.MaterialEditingLibrary
    source_path = '/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/Materials/M_SP_SourceSky_V2'
    dst = ASSETS + '/Materials/M_KZ_SourceSky_Adapter'
    m = unreal.load_asset(dst)
    if not m:
        m = unreal.EditorAssetLibrary.duplicate_asset(source_path, dst)
    else:
        backup_asset(m)
    nodes = list(lib.get_material_expressions(m))
    added = next((n for n in nodes if n.get_editor_property('desc') == 'KZ source sky controls; native procedural formulas'), None)
    def parameter(name):
        return next(n for n in nodes if isinstance(n,(unreal.MaterialExpressionVectorParameter,unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionTextureSampleParameter2D)) and str(n.get_editor_property('parameter_name')) == name)
    if not added:
        base = lib.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        base_out = lib.get_material_property_input_node_output_name(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        star_color = parameter('StarBaseColor')
        old_star = next(n for n in nodes if isinstance(n,unreal.MaterialExpressionMultiply) and star_color in list(lib.get_inputs_for_material_expression(m,n)))
        raw_star = next(n for n in lib.get_inputs_for_material_expression(m,old_star) if n != star_color)
        added = expression(m, unreal.MaterialExpressionCustom, 3300, 0)
        added.set_editor_property('desc','KZ source sky controls; native procedural formulas')
        added.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        pins = ('Base','OldStar','RawStar','StarColor','StarColorWeight','BlinkWeight','BlinkSpeed','BlinkUVScale','HMin','HMax','SunColor','SunIntensity','SunRadius','SunScale','SunDirection','World','Center','UV','Time')
        added.set_editor_property('inputs',[custom_input(p) for p in pins])
        added.set_editor_property('code','''
float phase=Time*BlinkSpeed+(UV.x+UV.y)*BlinkUVScale*6.28318530718;
float blink=lerp(1.0,0.5+0.5*sin(phase),saturate(BlinkWeight));
float horizon=smoothstep(HMin,max(HMax,HMin+1.0),World.z-Center.z);
float3 star=RawStar*lerp(float3(1,1,1),StarColor.rgb,saturate(StarColorWeight))*blink*horizon;
float3 dir=normalize(World.xyz-Center.xyz);
float sun=pow(saturate(dot(dir,normalize(SunDirection.xyz))),1.0/max(SunRadius,0.0001));
return max(Base.rgb-OldStar.rgb,0.0)+star+SunColor.rgb*SunIntensity*SunScale*sun;
''')
        for node,out,pin in [(base,base_out,'Base'),(old_star,'','OldStar'),(raw_star,'','RawStar'),(star_color,'RGB','StarColor'),
                             (parameter('StarColorWeight'),'','StarColorWeight'),(parameter('StarBlinkWeight'),'','BlinkWeight'),
                             (parameter('StarBlinkSpeed'),'','BlinkSpeed'),(parameter('StarBlinkUVScale'),'','BlinkUVScale'),
                             (parameter('StarHorizonHeightMin'),'','HMin'),(parameter('StarHorizonHeightMax'),'','HMax'),
                             (parameter('SunSideColor'),'RGB','SunColor'),(parameter('SunlightBackgroundIntensity'),'','SunIntensity'),
                             (parameter('SunlightBackgroundRadius'),'','SunRadius')]:
            connect(node,out,added,pin)
        connect(scalar(m,'KZ_SkySunBackgroundScale_Native',NATIVE['SkySunBackgroundScale'],2900,800),'',added,'SunScale')
        connect(vector(m,'KZ_SkySunDirection_SourceDerived',(0,0,1,1),2900,950),'RGB',added,'SunDirection')
        for cls,pin in [(unreal.MaterialExpressionWorldPosition,'World'),(unreal.MaterialExpressionActorPositionWS,'Center'),
                        (unreal.MaterialExpressionTextureCoordinate,'UV'),(unreal.MaterialExpressionTime,'Time')]:
            connect(expression(m,cls,2900,1100),'',added,pin)
        if not lib.connect_material_property(added,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError('Sky control output connection failed')
    # Original FTW noise/distortion textures were already imported by the
    # environment pass, but NebulaNoiseUVScale/Desaturation had no consumers.
    nodes = list(lib.get_material_expressions(m))
    nebula = parameter('SkyNebulaTexture')
    if not any(n.get_editor_property('desc') == 'KZ native nebula source noise UV' for n in nodes):
        old_uv = list(lib.get_inputs_for_material_expression(m,nebula))[0]
        noise_uv = expression(m,unreal.MaterialExpressionMultiply,2200,1800)
        texcoord = expression(m,unreal.MaterialExpressionTextureCoordinate,1800,1800)
        connect(texcoord,'',noise_uv,'A')
        connect(parameter('NebulaNoiseUVScale'),'',noise_uv,'B')
        texnodes=[]
        for name,asset in [('KZ_SkyNoise_Source','T_SP_Sky_Smoke_Noise'),('KZ_SkyDistortion_Source','T_SP_Sky_Cloud_Distortion')]:
            texture=unreal.load_asset('/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/Textures/'+asset)
            if not texture:raise RuntimeError('Missing original sky texture: '+asset)
            tex=expression(m,unreal.MaterialExpressionTextureSampleParameter2D,2450,1800)
            tex.set_editor_property('parameter_name',name)
            tex.set_editor_property('texture',texture)
            tex.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if name == 'KZ_SkyNoise_Source' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
            connect(noise_uv,'',tex,'UVs')
            texnodes.append(tex)
        distort=expression(m,unreal.MaterialExpressionCustom,2700,1800)
        distort.set_editor_property('desc','KZ native nebula source noise UV')
        distort.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        distort.set_editor_property('inputs',[custom_input(p) for p in ('UV','Noise','Distortion','Strength')])
        distort.set_editor_property('code','return UV.xy+(Distortion.rg-0.5)*(Noise.r-0.5)*Strength;')
        connect(old_uv,'',distort,'UV')
        connect(texnodes[0],'R',distort,'Noise')
        connect(texnodes[1],'RGB',distort,'Distortion')
        connect(scalar(m,'KZ_NebulaNoiseStrengthUV_Native',NATIVE['SkyNebulaNoiseStrengthUV'],2450,2200),'',distort,'Strength')
        connect(distort,'',nebula,'UVs')
        mask = next(n for n in nodes if isinstance(n,unreal.MaterialExpressionComponentMask) and nebula in list(lib.get_inputs_for_material_expression(m,n)))
        old_neb = next(n for n in nodes if isinstance(n,unreal.MaterialExpressionMultiply) and mask in list(lib.get_inputs_for_material_expression(m,n)))
        inputs=list(added.get_editor_property('inputs'))
        for pin in ('OldNeb','NebulaRGB','NebulaDesaturation','NebulaIntensity','NebulaInfluence'):
            inputs.append(custom_input(pin))
        added.set_editor_property('inputs',inputs)
        for node,out,pin in [(old_neb,'','OldNeb'),(nebula,'RGB','NebulaRGB'),(parameter('NebulaDesaturation'),'','NebulaDesaturation'),
                              (parameter('NebulaIntensity'),'','NebulaIntensity'),(parameter('PreviewNebulaInfluence'),'','NebulaInfluence')]:
            connect(node,out,added,pin)
        code=added.get_editor_property('code')
        code=code.replace('return max(Base.rgb-OldStar.rgb,0.0)+star+',
             'float nLuma=dot(NebulaRGB.rgb,float3(0.2126,0.7152,0.0722));\nfloat3 nColor=lerp(NebulaRGB.rgb,float3(nLuma,nLuma,nLuma),saturate(NebulaDesaturation))*NebulaIntensity*NebulaInfluence;\nreturn max(Base.rgb-OldStar.rgb-float3(OldNeb,OldNeb,OldNeb),0.0)+nColor+star+')
        added.set_editor_property('code',code)
    for node in lib.get_material_expressions(m):
        if isinstance(node,unreal.MaterialExpressionTextureSampleParameter2D):
            key=str(node.get_editor_property('parameter_name'))
            if key=='KZ_SkyNoise_Source':node.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
            if key=='KZ_SkyDistortion_Source':node.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    compiled = compile_save(m)
    if not compiled['pixel_instructions']:
        raise RuntimeError('Sky adapter has no compiled shader; inspect material errors before continuing')
    source = read(REPORT/'SourceManifest.json')
    rows = []
    for level,key,path in [('StormPass','boss_phase_2','/Game/_Art/Player/Environment/StormPass/Reconstructed/BladePhantomPolish/Sky/MI_SP_BP_SkyColor_DeepNight'),
                           ('HeinMach','OP',ASSETS+'/Materials/MI_HM_SourceSky_GloomySunset')]:
        mi = unreal.load_asset(path)
        backup_asset(mi)
        lib.set_material_instance_parent(mi,m)
        rot = source[level][key]['components']['directional_light']['properties']['RelativeRotation']
        pitch,yaw = math.radians(rot['Pitch']),math.radians(rot['Yaw'])
        direction = [-math.cos(pitch)*math.cos(yaw),-math.cos(pitch)*math.sin(yaw),-math.sin(pitch)]
        lib.set_material_instance_vector_parameter_value(mi,'KZ_SkySunDirection_SourceDerived',unreal.LinearColor(*direction,1))
        lib.set_material_instance_scalar_parameter_value(mi,'KZ_SkySunBackgroundScale_Native',NATIVE['SkySunBackgroundScale'])
        unreal.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
        # A parameter existing in the asset is not proof that its value renders.
        visited=set()
        def visit(node):
            if not node or node in visited:return
            visited.add(node)
            for child in lib.get_inputs_for_material_expression(m,node):visit(child)
        visit(lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_EMISSIVE_COLOR))
        used = sorted(str(n.get_editor_property('parameter_name')) for n in visited if isinstance(n,(unreal.MaterialExpressionVectorParameter,unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionTextureSampleParameter2D)))
        stored = sorted(str(n.get_editor_property('parameter_name')) for n in lib.get_material_expressions(m) if isinstance(n,(unreal.MaterialExpressionVectorParameter,unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionTextureSampleParameter2D)))
        rows.append({'level':level,'instance':mi.get_path_name(),'connected_parameters':used,'stored_only_parameters':sorted(set(stored)-set(used)),
                     'sun_direction_derived_from_WDL_rotation':direction})
    write('SourceSkyConsumers',{'compiled':compiled,'instances':rows,'native_controls':NATIVE,
          'boundary':'Native gradient/star blink/horizon/sun-background formulas. Original noise/distortion/refraction functions unavailable; stored-only parameters explicitly listed.'})
    print(json.dumps({'source_sky_controls_connected':True,'compiled':compiled,'instances':rows}))


def audit_restored_level(level, name='Reloaded'):
    """Used-scene audit, never a whole Content rebuild or source resurvey."""
    unreal = ue()
    load_level(level)
    current = {a.get_actor_label(): a for a in actors()}
    before = {r['label']: r for r in read(REPORT / (level + '_Before.json'))}
    missing_before = [n for n in before if n not in current]
    moved = [n for n in before if n in current and before[n]['pose'] != pose(current[n])]
    missing_slots = []
    materials = {}
    pp = []
    lib = unreal.MaterialEditingLibrary
    for label, a in current.items():
        for c in a.get_components_by_class(unreal.MeshComponent):
            for i in range(c.get_num_materials()):
                m = c.get_material(i)
                if not m:
                    missing_slots.append({'actor': label, 'component': c.get_name(), 'slot': i})
                else:
                    materials[m.get_path_name()] = m
        if isinstance(a, unreal.PostProcessVolume):
            s = a.get_editor_property('settings')
            pp.append({'actor': label, 'enabled': a.get_editor_property('enabled'),
                       'unbound': a.get_editor_property('unbound'), 'priority': a.get_editor_property('priority'),
                       'blendables': [{'weight': x.weight, 'material': x.object.get_path_name() if x.object else None}
                                     for x in s.get_editor_property('weighted_blendables').get_editor_property('array')],
                       'native_ev_min': s.get_editor_property('auto_exposure_min_brightness'),
                       'native_ev_max': s.get_editor_property('auto_exposure_max_brightness')})
    packed = []
    packed_issues = []
    for path, m in materials.items():
        if not isinstance(m, unreal.MaterialInstanceConstant):
            continue
        rough = lib.get_material_instance_texture_parameter_value(m, 'RoughnessTexture')
        metal = lib.get_material_instance_texture_parameter_value(m, 'MetallicTexture')
        if not rough or rough != metal or not rough.get_path_name().startswith('/Game/_Art/'):
            continue
        root = m
        while isinstance(root, unreal.MaterialInstanceConstant):
            root = root.get_editor_property('parent')
        if root and ('TreeFoliage' in root.get_name() or 'Trees_Covering' in root.get_name()):
            packed.append({'material': path, 'policy': 'Native foliage graph roughness=G, AO=R, nonmetallic; obsolete USD selectors ignored'})
            continue
        values = {}
        for key in ('RoughnessTextureComponent','MetallicTextureComponent','AmbientOcclusionTextureComponent'):
            v = lib.get_material_instance_vector_parameter_value(m, key)
            values[key] = [v.r,v.g,v.b,v.a]
        expected = {'RoughnessTextureComponent':[0,1,0,0], 'MetallicTextureComponent':[0,0,1,0], 'AmbientOcclusionTextureComponent':[1,0,0,0]}
        good = values == expected
        row = {'material': path, 'packed_texture': rough.get_path_name(), 'selectors': values, 'matches_source_RGB_contract': good}
        packed.append(row)
        if not good:
            packed_issues.append(row)
    checks = {'missing_mesh_material_slots': missing_slots, 'packed_input_mismatches': packed_issues}
    if level == 'StormPass':
        plan = read(REPORT / 'StormPassPrunePlan.json')
        checks['deleted_plan_actors_still_present'] = [r['label'] for r in plan['remove'] if r['label'] in current]
        checks['missing_preserved_actors'] = [n for n in plan['keep_labels'] if n not in current]
        layout = read(SPMETA / 'BladePhantom_SideBySide_20261002/Layout.json')
        refs = [r['label'] for r in layout['markers']]
        refs += ['SP_BP_Phase1_PlayerEntry_Mission02_Start_BossZone']
        refs += [a.get_actor_label() for a in current.values() if isinstance(a, unreal.PlayerStart)]
        ground = []
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        for n in refs:
            a = current[n]
            p = a.get_actor_location()
            for complex_trace in (False,True):
                result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(p.x,p.y,p.z+1000), unreal.Vector(p.x,p.y,p.z-2000),
                         unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, complex_trace, [], unreal.DrawDebugTrace.NONE, True)
                hit = result.to_dict()
                hp = hit.get('impact_point')
                ha = hit.get('hit_actor')
                ground.append({'actor':n, 'complex':complex_trace,'hit':bool(hit.get('blocking_hit')),
                               'impact_cm':[hp.x,hp.y,hp.z] if hp else None,
                               'hit_actor':ha.get_actor_label() if ha else None,
                               'boundary':'Diagnostic Visibility trace, not Character/AI movement or original collision proof'})
        checks['ground_support'] = ground
    else:
        checks['restored_tombstones'] = [r['label'] for file in ('HeinMach_UserExclusions.json','HeinMach_OptimizationExclusions.json')
                                     for r in read(HMETA / file)['exclusions'] if r['label'] in current]
        overrides = read(HMETA / 'HeinMach_ManualOverrides.json')['transform_overrides']
        checks['manual_override_changes_since_snapshot'] = [r['label'] for r in overrides if r['label'] in moved or r['label'] not in current]
        checks['PlayerStart_changes_since_snapshot'] = [n for n in moved if isinstance(current[n],unreal.PlayerStart)]
    payload = {'level':level,'map':MAPS[level], 'actor_count':len(current), 'material_count_used':len(materials),
               'source_snapshot_missing_count':len(missing_before), 'moved_existing_actors':moved,
               'PlayerStart':[{'label':n,'pose':pose(a)} for n,a in current.items() if isinstance(a,unreal.PlayerStart)],
               'post_process':pp,'packed_material_inputs':packed,'checks':checks,
               'native_controls_final':NATIVE, 'custom_depth_session':unreal.SystemLibrary.get_console_variable_int_value('r.CustomDepth'),
               'boundary':'Reload/readback and used-material contracts only; no original engine shader or combat PIE equivalence claim'}
    write(level + '_' + name, payload)
    print(json.dumps({'level':level,'actors':len(current),'used_materials':len(materials),'missing_slots':len(missing_slots),
                      'packed_mismatches':len(packed_issues), 'moved_existing':moved,
                      'check_counts':{k:len(v) for k,v in checks.items()}}))
    return payload


if __name__ == '__main__':
    source_manifest()
