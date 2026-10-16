"""Restore source Cascade object graphs and visual dependencies without runtime code."""
from pathlib import Path
from collections import Counter
import json
import re
import traceback
import struct
import math
import hashlib
import shutil
from decimal import Decimal
from functools import lru_cache
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
BASE = ROOT / 'Saved/Extracted/CombatEffects_20261006'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
ROWS = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
LOOKUP = {r['source_package']: r for r in ROWS}
FX = unreal.FXConverterUtilitiesLibrary
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
WORLD = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
KEEP = []
ISSUES = []
PHASE = re.search(r'-KZFXPhase=(\w+)', unreal.SystemLibrary.get_command_line())
PHASE = PHASE.group(1) if PHASE else 'probe'
REPORT = {'phase': PHASE, 'assets': [], 'issues': ISSUES}


def write(name, data):
    path = META / (name + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


@lru_cache(maxsize=None)
def read_exports(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def exports(row):
    return read_exports(row['source_json'])


def source(row):
    return next(o for o in exports(row) if o['Type'] == row['source_type'] and not o.get('Outer'))


def make(row, cls, factory):
    path = row['destination']
    old = unreal.load_asset(path)
    if old:
        assert unreal.EditorAssetLibrary.get_metadata_tag(old, 'KZFXSourcePackage') == row['source_package'], 'Existing asset is not owned by this extraction: ' + path
        return old
    folder, name = path.rsplit('/', 1)
    unreal.EditorAssetLibrary.make_directory(folder)
    obj = TOOLS.create_asset(name, folder, cls, factory)
    assert obj, path
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXSourcePackage', row['source_package'])
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXSourceSHA256', row['source_sha256'])
    KEEP.append(obj)
    return obj


def save(obj):
    assert obj.get_path_name().startswith('/Game/_Art/Effects/'), obj
    assert unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False), obj


def ref(value, local=None):
    if not value:
        return None
    path = value['ObjectPath']
    if local and path in local:
        return local[path]
    package = path.split('.')[0]
    row = LOOKUP.get(package)
    if row:
        asset = unreal.load_asset(row['destination'])
        if asset:
            return asset
    if package.startswith('Engine/Content/'):
        asset = unreal.load_asset('/Engine/' + package[len('Engine/Content/'):])
        if asset:
            return asset
    ISSUES.append({'kind': 'reference_not_loaded', 'source_reference': value})
    return None


def text(value, local=None):
    if value is None:
        return 'None'
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if isinstance(value, float):
        # FNumericProperty::ImportText_Internal does not advance past an
        # exponent. Decimal spelling retains the value and the complete array.
        assert math.isfinite(value), value
        return format(Decimal(str(value)), 'f')
    if isinstance(value, int):
        return repr(value)
    if isinstance(value, str):
        if '::' in value:
            return value.rsplit('::', 1)[-1]
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return '(' + ','.join(text(v, local) for v in value) + ')'
    if isinstance(value, dict):
        if 'ObjectPath' in value:
            obj = ref(value, local)
            return "'" + obj.get_path_name() + "'" if obj else 'None'
        return '(' + ','.join(k + '=' + text(v, local) for k, v in value.items() if k != 'Hex') + ')'
    raise TypeError(type(value))


def put(obj, key, value, local=None):
    # CoreUObject's SETNOPEC imports a single named object's reflected property.
    # Full object paths prevent any class-wide/CDO change. Only task-owned objects
    # in this separate process are used. It also supports protected Cascade data.
    path = obj.get_path_name()
    assert path.startswith('/Game/_Art/Effects/') or path.startswith('/Engine/Transient.'), path
    assert len(path) < 256, 'SET object-token capacity: ' + path
    encoded = text(value, local)
    if isinstance(value, str):
        try:
            field = obj.get_editor_property(key)
            if isinstance(field, unreal.Name):
                # Direct FName import uses PPF_None and takes the entire input;
                # quoting here would make the quote marks part of the name.
                assert '\n' not in value and '\r' not in value
                encoded = value
        except Exception as e:
            if isinstance(e, AssertionError):
                raise
    unreal.SystemLibrary.execute_console_command(WORLD, 'SETNOPEC "' + path + '" ' + key + ' ' + encoded)


def export_text(obj, path):
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(path)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(task), path


def cascade(row):
    data = exports(row)
    root = source(row)
    asset = make(row, unreal.ParticleSystem, unreal.ParticleSystemFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXGraphImported') == row['source_sha256'] + '|editor-distributions-v2':
        return asset
    local = {}
    root_index = data.index(root)
    local[row['source_package'] + '.' + str(root_index)] = asset
    replacements = {'xxParticleModuleMeshMaterialOverride': 'ParticleModuleMeshMaterial',
                    'xxDtbVectorParticleParameter': 'DistributionVectorParticleParameter'}

    def create(i):
        key = row['source_package'] + '.' + str(i)
        if key in local:
            return local[key]
        original = data[i]
        outer_index = int(original['Outer']['ObjectPath'].rsplit('.', 1)[1])
        outer = create(outer_index)
        typ = replacements.get(original['Type'], original['Type'])
        cls = unreal.load_class(None, '/Script/Engine.' + typ)
        assert cls, original['Type']
        # Some source distribution exports are editor-stripped and unreferenced;
        # keeping their object identity is still useful for the source graph.
        obj_name = original['Name']
        if len(outer.get_path_name()) + len(obj_name) + 1 >= 240:
            obj_name = 'E' + str(i)
        obj = unreal.new_object(cls, outer=outer, name=obj_name)
        local[key] = obj
        KEEP.append(obj)
        if typ != original['Type']:
            ISSUES.append({'kind': 'proprietary_class_adapter', 'package': row['source_package'],
                           'original': original['Type'], 'native': typ})
        return obj

    for i in range(len(data)):
        create(i)
    derived = []

    def restore_editor_distributions(value, owner, field):
        if isinstance(value, list):
            return [restore_editor_distributions(v, owner, field + '[' + str(i) + ']') for i, v in enumerate(value)]
        if not isinstance(value, dict):
            return value
        if 'Distribution' not in value or 'Table' not in value or value['Distribution']:
            return {k: restore_editor_distributions(v, owner, field + '.' + k) for k, v in value.items()}
        table = value['Table']
        count = table.get('EntryCount', 0)
        stride = table.get('EntryStride', 0)
        sub = table.get('SubEntryStride', 0)
        operation = table.get('Op', 0)
        channels = stride - sub
        assert count and channels in (1, 3) and operation in (1, 2, 3), (row['name'], field, table)
        assert len(table['Values']) == count * stride, (field, table)
        vector = channels == 3
        uniform = operation in (2, 3)
        typ = 'Distribution' + ('Vector' if vector else 'Float') + ('Uniform' if uniform else 'Constant') + ('Curve' if count > 1 else '')
        cls = unreal.load_class(None, '/Script/Engine.' + typ)
        name = 'D' + str(len(derived))
        # These native editor objects are derived from the archived cooked table,
        # not recovered original editor keyframes. GPU editor compilation requires
        # a non-null Distribution even though CPU cooked evaluation accepts tables.
        obj = unreal.new_object(cls, outer=owner, name=name)
        assert len(obj.get_path_name()) < 256, obj.get_path_name()
        KEEP.append(obj)
        token = 'KZFXEditor.' + name
        local[token] = obj

        def point(values):
            if vector:
                first = dict(zip(('X', 'Y', 'Z'), values[:3]))
                return {'v1': first, 'v2': dict(zip(('X', 'Y', 'Z'), values[3:]))} if uniform else first
            return {'X': values[0], 'Y': values[1]} if uniform else values[0]

        if count == 1:
            values = table['Values']
            if uniform:
                put(obj, 'Min', dict(zip(('X', 'Y', 'Z'), values[:3])) if vector else values[0])
                put(obj, 'Max', dict(zip(('X', 'Y', 'Z'), values[3:])) if vector else values[1])
            else:
                put(obj, 'Constant', point(values))
        else:
            scale = table['TimeScale']
            bias = table.get('TimeBias', 0.0)
            assert scale > 0, (field, scale)
            # Engine FDistributionLookupTable::GetEntry uses (time-bias)*scale;
            # the inverse gives each original sample's input time. CIM_Linear
            # reproduces its interpolation and clamped endpoint semantics.
            points = [{'InVal': bias + i / scale, 'OutVal': point(table['Values'][i * stride:(i + 1) * stride]),
                       'InterpMode': 'CIM_Linear'} for i in range(count)]
            put(obj, 'ConstantCurve', {'Points': points, 'bIsLooped': False})
        if vector:
            lock = table.get('LockFlag', 0)
            if typ.endswith('UniformCurve'):
                put(obj, 'LockedAxes', [lock, lock])
            elif typ.endswith(('Uniform', 'Constant')):
                put(obj, 'LockedAxes', lock)
            if uniform:
                put(obj, 'MirrorFlags', ['EDVMF_Different'] * 3)
                put(obj, 'bUseExtremes', operation == 3)
            # Preserve the original table for CPU evaluation. GPU compilation
            # explicitly builds its own tables from the equivalent editor curve.
            put(obj, 'bIsDirty', False)
        replacement = dict(value)
        replacement['Distribution'] = {'ObjectPath': token}
        derived.append({'source_field': field, 'native_object': obj.get_path_name(), 'native_type': typ,
                        'operation': operation, 'sample_count': count,
                        'time_bias': table.get('TimeBias', 0), 'time_scale': table.get('TimeScale', 0),
                        'lock_flag': table.get('LockFlag', 0),
                        'method': 'inverse lookup time grid, linear interpolation; cooked table retained'})
        return replacement

    # Bind the root last, once all LOD/module references are valid.
    for i, original in enumerate(data):
        if i == root_index:
            continue
        obj = local[row['source_package'] + '.' + str(i)]
        for key, value in original.get('Properties', {}).items():
            put(obj, key, restore_editor_distributions(value, obj, 'exports[' + str(i) + '].Properties.' + key), local)
    for key, value in root.get('Properties', {}).items():
        put(asset, key, value, local)
    expected = root.get('Properties', {}).get('Emitters', [])
    actual = FX.get_cascade_system_emitters(asset)
    assert len(actual) == len(expected), (row['name'], len(expected), len(actual))
    for emitter in actual:
        lod = FX.get_cascade_emitter_lod_level(emitter, 0)
        assert lod and FX.get_lod_level_required_module(lod) and FX.get_lod_level_spawn_module(lod), emitter
    unreal.EditorAssetLibrary.set_metadata_tag(asset, 'KZFXGraphImported', row['source_sha256'] + '|editor-distributions-v2')
    unreal.EditorAssetLibrary.set_metadata_tag(asset, 'KZFXRecoveryBoundary', 'Source Cascade fields and cooked tables; native editor distributions derived from source tables; reconstructed material shaders; class adapters recorded.')
    save(asset)
    recovery_file = 'Recovery/Cascade/' + row['source_sha256']
    write(recovery_file, {'source': row['source_package'], 'destination': row['destination'],
                          'derived_editor_distributions': derived,
                          'boundary': 'Editor curves reconstructed from cooked samples; original pre-cook editor keys are not available.'})
    REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'],
                             'emitters': len(actual), 'subobjects': len(data) - 1,
                             'derived_editor_distribution_count': len(derived), 'recovery_report': recovery_file + '.json',
                             'compact_names': [{'source_export_index': i, 'source_name': o['Name'], 'native_path': local[row['source_package'] + '.' + str(i)].get_path_name()}
                                               for i, o in enumerate(data) if local[row['source_package'] + '.' + str(i)].get_name() != o['Name']]})
    return asset


def payload(row, files, factory, force=False):
    old = unreal.load_asset(row['destination'])
    if old:
        assert unreal.EditorAssetLibrary.get_metadata_tag(old, 'KZFXSourcePackage') == row['source_package']
        if old.get_class().get_name() == row['source_type'] and not force:
            return old
        # Repair only this task's incorrectly classified HDR texture import.
        if old.get_class().get_name() != row['source_type']:
            assert isinstance(old, unreal.Texture) and row['source_type'] in ('Texture2D', 'TextureCube')
            assert unreal.EditorAssetLibrary.delete_asset(row['destination']), row['destination']
    folder, name = row['destination'].rsplit('/', 1)
    task = unreal.AssetImportTask()
    for key, value in [('filename', str(files[0])), ('destination_path', folder), ('destination_name', name),
                       ('automated', True), ('replace_existing', force), ('save', False), ('factory', factory)]:
        task.set_editor_property(key, value)
    TOOLS.import_asset_tasks([task])
    obj = unreal.load_asset(row['destination'])
    if not obj:
        imported = list(task.get_objects())
        assert len(imported) == 1, [o.get_path_name() for o in imported]
        obj = imported[0]
        assert unreal.EditorAssetLibrary.rename_asset(obj.get_path_name(), row['destination']), row['destination']
        obj = unreal.load_asset(row['destination'])
    assert obj, row['destination']
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXSourcePackage', row['source_package'])
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXSourceSHA256', row['source_sha256'])
    KEEP.append(obj)
    return obj


def dependencies():
    payloads = json.loads((BASE / 'Payload/ExportReport.json').read_text())
    files = {p['ObjectPath'].split('.')[0]: [Path(f) for f in p['DiskFilePaths']] for p in payloads if p['Success']}
    precision = {p['source_package']: p for p in json.loads((META / 'PrecisionTextureExtraction.json').read_text())} if (META / 'PrecisionTextureExtraction.json').is_file() else {}
    cubes = {p['source_package']: p for p in json.loads((META / 'PrecisionCubeExtraction.json').read_text())} if (META / 'PrecisionCubeExtraction.json').is_file() else {}
    for row in ROWS:
        if row['source_type'] in ('Texture2D', 'TextureCube'):
            if (PHASE == 'cube') != (row['source_type'] == 'TextureCube'):
                continue
            factory = unreal.TextureFactory()
            put(factory, 'HDRImportShouldBeLongLatCubeMap', 'YesAll' if row['source_type'] == 'TextureCube' else 'NoAll')
            exact = precision.get(row['source_package']) or cubes.get(row['source_package'])
            exact_sha = (exact.get('exr_sha256') or exact.get('dds_sha256')) if exact else None
            old = unreal.load_asset(row['destination'])
            force = bool(exact and old and unreal.EditorAssetLibrary.get_metadata_tag(old, 'KZFXPrecisionSHA256') != exact_sha)
            obj = payload(row, [ROOT / exact['path']] if exact else files[row['source_package']], factory, force)
            if exact:
                unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXPrecisionSHA256', exact_sha)
            props = source(row).get('Properties', {})
            for key in ('SRGB', 'CompressionSettings', 'AddressX', 'AddressY', 'Filter', 'LODGroup'):
                if key in props:
                    put(obj, key, props[key])
            save(obj)
            assert obj.get_class().get_name() == row['source_type'], (row['name'], obj.get_class().get_name())
            REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': row['source_type']})
        elif row['source_type'] == 'VectorFieldStatic' and PHASE != 'cube':
            obj = payload(row, [BASE / 'VectorFields' / (row['name'] + '.fga')], unreal.VectorFieldStaticFactory())
            save(obj)
            REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': 'VectorFieldStatic'})


def parameters(props):
    cached = props.get('CachedExpressionData', {}).get('Parameters', {})
    result = {}
    for key, values in [('RuntimeEntries', 'ScalarValues'), ('RuntimeEntries[1]', 'VectorValues'), ('RuntimeEntries[2]', 'TextureValues')]:
        result[values] = dict(zip([v['Name'] for v in cached.get(key, {}).get('ParameterInfos', [])], cached.get(values, [])))
    return result


def node(material, cls, index):
    return LIB.create_material_expression(material, cls, -800 + (index % 4) * 220, (index // 4) * 130)


def connect(a, output, b, pin):
    assert LIB.connect_material_expressions(a, output, b, pin), (a, output, b, pin)


def sampler(texture):
    comp = texture.get_editor_property('compression_settings')
    if comp == unreal.TextureCompressionSettings.TC_ALPHA:
        return unreal.MaterialSamplerType.SAMPLERTYPE_ALPHA
    if comp == unreal.TextureCompressionSettings.TC_DISTANCE_FIELD_FONT:
        return unreal.MaterialSamplerType.SAMPLERTYPE_DISTANCE_FIELD_FONT
    if comp == unreal.TextureCompressionSettings.TC_NORMALMAP:
        return unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
    if comp == unreal.TextureCompressionSettings.TC_MASKS:
        return unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
    if comp == unreal.TextureCompressionSettings.TC_GRAYSCALE:
        return unreal.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE if texture.get_editor_property('srgb') else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
    return unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR


def custom_input(name):
    value = unreal.CustomInput()
    value.set_editor_property('input_name', name)
    return value


def master(row):
    m = make(row, unreal.Material, unreal.MaterialFactoryNew())
    original = source(row)
    props = original.get('Properties', {})
    if unreal.EditorAssetLibrary.get_metadata_tag(m, 'KZFXMaterialRecovery') == 'source-parameters-native-v3':
        return m
    defaults = parameters(original)
    # Preserve child-only parameters as editable native declarations, too.
    descendants = set([row['source_package']])
    changed = True
    while changed:
        changed = False
        for child in ROWS:
            if child['source_type'] != 'MaterialInstanceConstant' or child['source_package'] in descendants:
                continue
            cp = source(child).get('Properties', {})
            parent = cp.get('Parent', {}).get('ObjectPath', '').split('.')[0]
            if parent in descendants:
                descendants.add(child['source_package'])
                changed = True
                for key, name in [('ScalarParameterValues', 'ScalarValues'), ('VectorParameterValues', 'VectorValues'), ('TextureParameterValues', 'TextureValues')]:
                    for v in cp.get(key, []):
                        defaults[name].setdefault(v['ParameterInfo']['Name'], v['ParameterValue'])
    m.modify()
    LIB.delete_all_material_expressions(m)
    # Shader topology was stripped by the original game's cook. These nodes
    # are an explicit native recovery using original textures/parameters.
    for key in ('BlendMode', 'TwoSided', 'OpacityMaskClipValue'):
        if key in props:
            put(m, key, props[key])
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    decal = props.get('MaterialDomain') == 'MD_DeferredDecal'
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL if decal else unreal.MaterialDomain.MD_SURFACE)
    for usage in (unreal.MaterialUsage.MATUSAGE_PARTICLE_SPRITES, unreal.MaterialUsage.MATUSAGE_MESH_PARTICLES,
                  unreal.MaterialUsage.MATUSAGE_BEAM_TRAILS, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,
                  unreal.MaterialUsage.MATUSAGE_NIAGARA_MESH_PARTICLES, unreal.MaterialUsage.MATUSAGE_NIAGARA_RIBBONS):
        LIB.set_material_usage(m, usage)
    scalars, vectors, textures = {}, {}, {}
    n = 0
    for name, value in defaults['ScalarValues'].items():
        obj = node(m, unreal.MaterialExpressionScalarParameter, n); n += 1
        obj.set_editor_property('parameter_name', name)
        obj.set_editor_property('default_value', value)
        scalars[name] = obj
    for name, value in defaults['VectorValues'].items():
        obj = node(m, unreal.MaterialExpressionVectorParameter, n); n += 1
        obj.set_editor_property('parameter_name', name)
        obj.set_editor_property('default_value', unreal.LinearColor(value.get('R', 0), value.get('G', 0), value.get('B', 0), value.get('A', 0)))
        vectors[name] = obj
    for name, value in defaults['TextureValues'].items():
        texture = ref(value)
        if not texture:
            continue
        obj = node(m, unreal.MaterialExpressionTextureSampleParameterCube if isinstance(texture, unreal.TextureCube) else unreal.MaterialExpressionTextureSampleParameter2D, n); n += 1
        obj.set_editor_property('parameter_name', name)
        obj.set_editor_property('texture', texture)
        obj.set_editor_property('sampler_type', sampler(texture))
        textures[name] = obj
    uv = node(m, unreal.MaterialExpressionTextureCoordinate, n); n += 1
    age = node(m, unreal.MaterialExpressionParticleRelativeTime, n); n += 1
    time = node(m, unreal.MaterialExpressionTime, n); n += 1
    atlas_cols = next((scalars[k] for k in ('SubUV_U', 'SubUV_Columns') if k in scalars), None)
    atlas_rows = next((scalars[k] for k in ('SubUV_V', 'SubUV_Rows') if k in scalars), None)
    if atlas_cols and atlas_rows:
        atlas = node(m, unreal.MaterialExpressionCustom, n); n += 1
        atlas.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        atlas.set_editor_property('description', 'Recovery: source grid, normalized particle age; stripped shader timing is not exact')
        atlas.set_editor_property('inputs', [custom_input(k) for k in ('UV', 'Age', 'Columns', 'Rows')])
        atlas.set_editor_property('code', 'float2 grid=max(float2(Columns,Rows),1); float count=grid.x*grid.y; float frame=min(floor(saturate(Age)*count),count-1); return (UV+float2(fmod(frame,grid.x),floor(frame/grid.x)))/grid;')
        for a, pin in ((uv, 'UV'), (age, 'Age'), (atlas_cols, 'Columns'), (atlas_rows, 'Rows')):
            connect(a, '', atlas, pin)
        for name, tex in textures.items():
            if 'sub' in name.lower() or name in ('Base_Texture', 'Tex_Emi', 'Tex_OPA'):
                connect(atlas, '', tex, 'UVs')
    elif row['name'].startswith(('Base_SubUV', 'FM_Base_Subuv', 'PP_Powder_SubUV', 'Base_GPU_3Color_SubUV', 'FM_Base_World_GPU_Particle')):
        subuv = node(m, unreal.MaterialExpressionParticleSubUVProperties, n); n += 1
        for tex in textures.values():
            connect(subuv, 'TextureCoordinate0', tex, 'UVs')
    else:
        # Restore clear linear pan/tiling contracts using the exact source parameters.
        for name, prefix in (('Tex_Emi', 'Emi'), ('Tex_OPA', 'Opa')):
            if name not in textures or not all(prefix + k in scalars for k in ('_TilingU', '_TilingV', '_SpeedU', '_SpeedV', '_OffsetU', '_OffsetV')):
                continue
            pan = node(m, unreal.MaterialExpressionCustom, n); n += 1
            pins = ('UV', 'Time', 'TilingU', 'TilingV', 'SpeedU', 'SpeedV', 'OffsetU', 'OffsetV')
            pan.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
            pan.set_editor_property('inputs', [custom_input(k) for k in pins])
            pan.set_editor_property('code', 'return UV*float2(TilingU,TilingV)+Time*float2(SpeedU,SpeedV)+float2(OffsetU,OffsetV);')
            connect(uv, '', pan, 'UV'); connect(time, '', pan, 'Time')
            for pin in pins[2:]:
                connect(scalars[prefix + '_' + pin], '', pan, pin)
            connect(pan, '', textures[name], 'UVs')
    pc = node(m, unreal.MaterialExpressionConstant4Vector if decal else unreal.MaterialExpressionParticleColor, n); n += 1
    if decal:
        pc.set_editor_property('constant', unreal.LinearColor(1, 1, 1, 1))
    consumed = []
    tex_name = next((k for k in ('Tex_Emi', 'Tex_SubUV', 'BaseTex', 'Base_Texture', 'Tex_Base', 'BaseTexture', 'Texture', 'Tex') if k in textures), None)
    if not tex_name:
        tex_name = next((k for k in textures if not any(t in k.lower() for t in ('normal', 'pos', 'rot', 'dist', 'noise', 'refrac'))), None)
    rgb = pc
    if tex_name:
        tex = textures[tex_name]
        consumed.append(tex_name)
        rgb = node(m, unreal.MaterialExpressionMultiply, n); n += 1
        connect(tex, 'RGB', rgb, 'A'); connect(pc, 'RGB', rgb, 'B')
    # Native shader uses explicit source tint and strength where the semantic
    # contract is clear. Complex distortion/dissolve/VAT remain source metadata.
    for name in ('BaseColor', 'Base_color', 'Base_Color', 'EmissiveColor', 'Color'):
        if name in vectors:
            mul = node(m, unreal.MaterialExpressionMultiply, n); n += 1
            connect(rgb, '' if rgb != pc else 'RGB', mul, 'A'); connect(vectors[name], 'RGB', mul, 'B')
            rgb = mul; consumed.append(name); break
    for name in ('Emi_pow', 'Emi_str', 'Emi_Pow', 'Emissive_Power', 'EmissivePower'):
        if name in scalars:
            mul = node(m, unreal.MaterialExpressionMultiply, n); n += 1
            connect(rgb, '' if rgb != pc else 'RGB', mul, 'A'); connect(scalars[name], '', mul, 'B')
            rgb = mul; consumed.append(name); break
    assert LIB.connect_material_property(rgb, '' if rgb != pc else 'RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if decal:
        assert LIB.connect_material_property(rgb, '' if rgb != pc else 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    opacity_name = next((k for k in ('Tex_OPA', 'Tex_Opa', 'Tex_Opacity', 'OpacityTex') if k in textures), tex_name)
    opacity = pc
    opacity_output = 'A'
    if opacity_name:
        mask_tex = textures[opacity_name]
        texture = mask_tex.get_editor_property('texture')
        # G8/R8 and authored mask textures use R; color atlases use their A.
        src = next(r for r in ROWS if r['destination'] == texture.get_path_name().split('.')[0])
        mask_channel = 'R' if source(src).get('PixelFormat') in ('PF_G8', 'PF_R8') or opacity_name != tex_name or 'subuv' in opacity_name.lower() else 'A'
        opacity = node(m, unreal.MaterialExpressionMultiply, n); n += 1
        connect(mask_tex, mask_channel, opacity, 'A'); connect(pc, 'A', opacity, 'B')
        opacity_output = ''; consumed.append(opacity_name)
    for name in ('Opa_Str', 'OPA_str', 'MasterOpacity', 'Opacity'):
        if name in scalars:
            mul = node(m, unreal.MaterialExpressionMultiply, n); n += 1
            connect(opacity, opacity_output, mul, 'A'); connect(scalars[name], '', mul, 'B')
            opacity = mul; opacity_output = ''; consumed.append(name); break
    blend = m.get_editor_property('blend_mode')
    if blend != unreal.BlendMode.BLEND_OPAQUE:
        assert LIB.connect_material_property(opacity, opacity_output, unreal.MaterialProperty.MP_OPACITY_MASK if blend == unreal.BlendMode.BLEND_MASKED else unreal.MaterialProperty.MP_OPACITY)
    unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXMaterialRecovery', 'source-parameters-native-v3')
    unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXRecoveryBoundary', 'Cooked shader graph unavailable. Native particle texture/color/opacity recovery; source parameters preserved. Distortion/dissolve/VAT topology not exact.')
    LIB.recompile_material(m)
    save(m)
    REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': 'Material',
                             'consumed_parameters': sorted(set(consumed)), 'all_declared_parameters': {k: list(v) for k, v in defaults.items()},
                             'graph_status': 'native_recovery_not_original_shader'})
    return m


def instance(row, force=False):
    old = unreal.load_asset(row['destination'])
    if old and unreal.EditorAssetLibrary.get_metadata_tag(old, 'KZFXInstanceImported') and not force:
        return old
    props = source(row).get('Properties', {})
    parent_ref = props.get('Parent')
    assert parent_ref, row['name']
    parent_row = LOOKUP[parent_ref['ObjectPath'].split('.')[0]]
    parent = master(parent_row) if parent_row['source_type'] == 'Material' else instance(parent_row)
    m = make(row, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(m, parent)
    for key in ('BasePropertyOverrides', 'ScalarParameterValues', 'VectorParameterValues', 'TextureParameterValues'):
        if key in props:
            put(m, key, props[key])
    LIB.update_material_instance(m)
    unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXInstanceImported', row['source_sha256'])
    save(m)
    REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': 'MaterialInstanceConstant'})
    return m


def meshes():
    payloads = json.loads((BASE / 'Payload/ExportReport.json').read_text())
    files = {p['ObjectPath'].split('.')[0]: [Path(f) for f in p['DiskFilePaths'] if f.endswith('.pskx')] for p in payloads if p['Success']}
    for row in ROWS:
        if row['source_type'] != 'StaticMesh':
            continue
        # The installed ActorX importer cannot create an asset named 'None'.
        # Rename only its temporary material tokens, leaving geometry bytes intact.
        raw = bytearray(files[row['source_package']][0].read_bytes())
        offset = 0
        while offset < len(raw):
            chunk, flags, size, count = struct.unpack_from('<20siii', raw, offset)
            offset += 32
            if chunk.rstrip(b'\0') == b'MATT0000':
                for i in range(count):
                    start = offset + i * size
                    token = ('KZFX_Temporary_' + str(i)).encode('ascii')
                    raw[start:start + 64] = token.ljust(64, b'\0')
            offset += size * count
        staged = BASE / 'ImportStaging' / (row['name'] + '.pskx')
        staged.parent.mkdir(exist_ok=True)
        staged.write_bytes(raw)
        obj = payload(row, [staged], unreal.PSKXFactory())
        original = source(row)
        mats = original.get('Materials', original.get('Properties', {}).get('StaticMaterials', []))
        resolved = []
        for value in mats:
            mat_ref = value.get('MaterialInterface', value.get('Material')) if isinstance(value, dict) else value
            resolved.append(ref(mat_ref))
        assert resolved, row['name']
        for i, m in enumerate(resolved):
            obj.set_material(i, m)
        if all(isinstance(v, dict) and 'MaterialInterface' in v for v in mats):
            # ImportedMaterialSlotName is read-only through Python. Import the
            # reflected native array in full, using exact source slot identities.
            put(obj, 'StaticMaterials', [{k: v[k] for k in ('MaterialInterface', 'MaterialSlotName', 'ImportedMaterialSlotName') if k in v} for v in mats])
        save(obj)
        REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': 'StaticMesh', 'materials': len(resolved)})


def data_assets():
    # The native T3D property importer supports indexed fixed arrays, whereas
    # Python setters and SETNOPEC cannot write CurveLinearColor.FloatCurves[4].
    # Import into scratch actors in this process's unsaved world, then duplicate
    # just the curve UObjects into their native asset packages.
    curve_rows = [r for r in ROWS if r['source_type'] == 'CurveLinearColor']
    lines = ['Begin Map Name=KZFXUnsavedCurveScratch', 'Begin Level Name=PersistentLevel']
    for i, row in enumerate(curve_rows):
        original = source(row)
        lines += ['Begin Actor Class=/Script/Engine.Actor Name=KZFXCurveScratch' + str(i),
                  'Begin Object Class=/Script/Engine.CurveLinearColor Name=SourceCurve' + str(i)]
        for idx, value in enumerate(original['FloatCurves']):
            lines.append('FloatCurves(' + str(idx) + ')=' + text(value))
        lines += ['End Object', 'End Actor']
    lines += ['End Level', 'End Map']
    staged = BASE / 'CurveScratch.t3d'
    staged.write_text('\n'.join(lines), encoding='utf-8')
    task = unreal.AssetImportTask()
    task.filename = str(staged)
    task.destination_path = '/Game/_Art/Effects/Metadata'
    task.destination_name = 'KZFXUnsavedCurveScratch'
    task.automated = True
    task.save = False
    task.factory = unreal.LevelFactory()
    TOOLS.import_asset_tasks([task])
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    curves = [next((unreal.find_object(a, 'SourceCurve' + str(i)) for a in actors if unreal.find_object(a, 'SourceCurve' + str(i))), None)
              for i in range(len(curve_rows))]
    assert all(curves), curves
    # Outer ownership alone does not retain otherwise unreferenced UObjects
    # across the collection performed while replacing extraction-owned curves.
    KEEP.extend(curves)
    REPORT['scratch_actors'] = [a.get_path_name() for a in actors]
    REPORT['scratch_import_objects'] = [a.get_path_name() for a in task.get_objects()]
    for i, row in enumerate(curve_rows):
        curve = curves[i]
        assert curve, row['name']
        old = unreal.load_asset(row['destination'])
        if old and PHASE not in ('numeric', 'numericdata'):
            assert unreal.EditorAssetLibrary.get_metadata_tag(old, 'KZFXSourcePackage') == row['source_package']
            obj = old
        else:
            if old:
                backup_owned(row, old)
                registry = unreal.AssetRegistryHelpers.get_asset_registry()
                options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True)
                referencers = [str(p) for p in (registry.get_referencers(row['destination'], options) or []) if str(p) != row['destination']]
                for path in referencers:
                    assert path.startswith('/Game/_Art/Effects/'), (row['name'], path)
                    dependent = unreal.load_asset(path)
                    assert dependent and unreal.EditorAssetLibrary.get_metadata_tag(dependent, 'KZFXSourcePackage'), path
                    assert isinstance(dependent, unreal.CurveLinearColorAtlas), (row['name'], path)
                # Python cannot write the protected fixed array. Recreate only
                # this extraction-owned curve from the corrected scratch graph;
                # the source atlas references are restored in the loop below.
                file = (ROOT / 'Content' / (row['destination'][len('/Game/'):] + '.uasset')).resolve()
                assert file.is_relative_to((ROOT / 'Content/_Art/Effects').resolve())
                before = file.read_bytes()
                assert unreal.EditorAssetLibrary.delete_loaded_asset(old), row['name']
                if file.exists():
                    assert file.read_bytes() == before, file
                    file.unlink()
                old = None
                unreal.SystemLibrary.collect_garbage()
            folder, name = row['destination'].rsplit('/', 1)
            obj = TOOLS.duplicate_asset(name, folder, curve)
        assert obj, row['name']
        unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXSourcePackage', row['source_package'])
        unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXSourceSHA256', row['source_sha256'])
        save(obj)
        export_text(obj, BASE / ('Curve_' + row['name'] + '.t3d'))
        REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': 'CurveLinearColor'})
    for typ, cls, factory in (
        ('CurveFloat', unreal.CurveFloat, unreal.CurveFloatFactory),
        ('MaterialParameterCollection', unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew),
        ('CurveLinearColorAtlas', unreal.CurveLinearColorAtlas, unreal.CurveLinearColorAtlasFactory)):
        for row in ROWS:
            if row['source_type'] != typ:
                continue
            obj = make(row, cls, factory())
            original = source(row)
            props = original.get('Properties', {})
            if typ == 'CurveFloat':
                for key, value in props.items():
                    put(obj, key, value)
            else:
                for key, value in props.items():
                    if key not in ('StateId', 'ImportedSize', 'LightingGuid'):
                        put(obj, key, value)
                if typ == 'CurveLinearColorAtlas':
                    obj.set_editor_property('gradient_curves', [ref(v) for v in props['GradientCurves']])
                else:
                    obj.set_editor_property('scalar_parameters', obj.get_editor_property('scalar_parameters'))
            save(obj)
            REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': typ})


def buffers():
    for row in ROWS:
        typ = row['source_type']
        if typ not in ('TextureRenderTarget2D', 'PhysicalMaterial'):
            continue
        cls, factory = (unreal.TextureRenderTarget2D, unreal.TextureRenderTargetFactoryNew()) if typ == 'TextureRenderTarget2D' else (unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
        obj = make(row, cls, factory)
        props = source(row).get('Properties', {})
        for key, value in props.items():
            if key != 'LightingGuid':
                put(obj, key, value)
        if typ == 'TextureRenderTarget2D':
            obj.set_editor_property('size_x', props['SizeX'])
            unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXRecoveryBoundary', 'Original render-target configuration and clear color; runtime writer and generated buffer contents are not imported.')
        save(obj)
        REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'type': typ})


def rebind():
    # Only repair references that were absent before the typed dependency closure.
    target = 'BBQ/Content/Art/World/World_Material/Prop/Material/WM_SKL_Ice_Special_008'
    def contains(value):
        if isinstance(value, dict):
            return value.get('ObjectPath', '').split('.')[0] == target or any(contains(v) for v in value.values())
        return isinstance(value, list) and any(contains(v) for v in value)
    for row in ROWS:
        if row['source_type'] != 'ParticleSystem':
            continue
        original = exports(row)
        touched = []
        asset = None
        for i, export in enumerate(original):
            for key, value in export.get('Properties', {}).items():
                if not contains(value):
                    continue
                if asset is None:
                    asset = unreal.load_asset(row['destination'])
                    assert asset and unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXSourcePackage') == row['source_package']
                # The affected fields are direct material refs on Required modules.
                assert export['Type'] == 'ParticleModuleRequired' and key == 'Material', (row['name'], export, key)
                module = unreal.find_object(asset, export['Name'])
                assert module, export['Name']
                put(module, key, value)
                assert module.get_editor_property('material') == ref(value), module
                touched.append({'source_export_index': i, 'property': key, 'material': ref(value).get_path_name()})
        if touched:
            save(asset)
            REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'rebound': touched})


def samplers():
    for row in ROWS:
        if row['source_type'] != 'Material':
            continue
        asset = unreal.load_asset(row['destination'])
        changed = []
        for expression in LIB.get_material_expressions(asset):
            if not isinstance(expression, unreal.MaterialExpressionTextureSample):
                continue
            texture = expression.get_editor_property('texture')
            if not texture:
                continue
            before = expression.get_editor_property('sampler_type')
            # Match Engine MaterialExpressionUtils::GetSamplerTypeForTexture.
            # Setting the same texture pointer does not dispatch a Python change.
            expression.set_editor_property('sampler_type', sampler(texture))
            after = expression.get_editor_property('sampler_type')
            if before != after:
                changed.append({'expression': expression.get_name(), 'before': str(before), 'after': str(after), 'texture': texture.get_path_name()})
        if changed:
            LIB.recompile_material(asset)
            save(asset)
            REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'samplers': changed})


def names():
    compact = {v['source']: {n['source_export_index']: n['native_path'] for n in v.get('compact_names', [])}
               for v in json.loads((META / 'Import_particles.json').read_text())['assets']}
    for row in ROWS:
        if row['source_type'] != 'ParticleSystem':
            continue
        original = exports(row)
        asset = unreal.load_asset(row['destination'])
        assert asset
        root = source(row)
        paths = {original.index(root): asset.get_path_name()}
        def object_path(i):
            if i in paths:
                return paths[i]
            e = original[i]
            outer = object_path(int(e['Outer']['ObjectPath'].rsplit('.', 1)[1]))
            name = e['Name'] if len(outer) + len(e['Name']) + 1 < 240 else 'E' + str(i)
            paths[i] = compact.get(row['source_package'], {}).get(i, outer + (':' if outer == asset.get_path_name() else '.') + name)
            return paths[i]
        changed = []
        for i, export in enumerate(original):
            strings = [(k, v) for k, v in export.get('Properties', {}).items() if isinstance(v, str)]
            if not strings:
                continue
            obj = unreal.find_object(None, object_path(i))
            assert obj, (row['name'], object_path(i))
            for key, value in strings:
                try:
                    current = obj.get_editor_property(key)
                except Exception:
                    continue
                if isinstance(current, unreal.Name) and str(current).casefold() != value.casefold():
                    put(obj, key, value)
                    assert str(obj.get_editor_property(key)).casefold() == value.casefold(), (obj, key, value)
                    changed.append({'object': obj.get_path_name(), 'property': key, 'source': value, 'previous': str(current)})
        if changed:
            save(asset)
            REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'], 'names': changed})


def scientific(value):
    if isinstance(value, float):
        return 'e' in repr(value).lower()
    if isinstance(value, dict):
        return any(scientific(v) for v in value.values())
    return isinstance(value, list) and any(scientific(v) for v in value)


def backup_owned(row, asset):
    assert unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXSourcePackage') == row['source_package']
    path = (ROOT / 'Content' / (row['destination'][len('/Game/'):] + '.uasset')).resolve()
    assert path.is_relative_to((ROOT / 'Content/_Art/Effects').resolve())
    raw = path.read_bytes()
    assert row['source_package'].encode('ascii') in raw and b'KZFXSourcePackage' in raw
    dest = ROOT / 'Saved/ArtBackups/CombatEffects_20261006/BeforeDecimalRepair' / path.relative_to(ROOT / 'Content')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        previous = dest.read_bytes()
        assert row['source_package'].encode('ascii') in previous and b'KZFXSourcePackage' in previous, dest
    else:
        shutil.copy2(path, dest)
    REPORT.setdefault('backups', []).append({'asset': row['destination'], 'backup': str(dest),
                                           'backup_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                                           'before_this_phase_sha256': hashlib.sha256(raw).hexdigest()})


def numeric_particles(row):
    original = exports(row)
    root = source(row)
    asset = unreal.load_asset(row['destination'])
    assert asset and unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXSourcePackage') == row['source_package']
    paths = {original.index(root): asset.get_path_name()}
    local = {}
    def object_path(i):
        if i not in paths:
            e = original[i]
            outer = object_path(int(e['Outer']['ObjectPath'].rsplit('.', 1)[1]))
            name = e['Name'] if len(outer) + len(e['Name']) + 1 < 240 else 'E' + str(i)
            paths[i] = outer + (':' if outer == asset.get_path_name() else '.') + name
        return paths[i]
    for i in range(len(original)):
        local[row['source_package'] + '.' + str(i)] = unreal.find_object(None, object_path(i))
        assert local[row['source_package'] + '.' + str(i)], object_path(i)
    recovery = json.loads((META / 'Recovery/Cascade' / (row['source_sha256'] + '.json')).read_text())
    derived = {d['source_field']: d for d in recovery['derived_editor_distributions']}
    changed = []
    editor_changed = []
    backed_up = False
    def before_change():
        nonlocal backed_up
        if not backed_up:
            backup_owned(row, asset)
            backed_up = True
    def restore(value, field):
        if isinstance(value, list):
            return [restore(v, field + '[' + str(i) + ']') for i, v in enumerate(value)]
        if not isinstance(value, dict):
            return value
        if 'Distribution' not in value or 'Table' not in value or value['Distribution']:
            return {k: restore(v, field + '.' + k) for k, v in value.items()}
        record = derived[field]
        distribution = unreal.find_object(None, record['native_object'])
        assert distribution, record
        token = record['native_object']
        local[token] = distribution
        table = value['Table']
        count, stride, sub = (table.get(k, 0) for k in ('EntryCount', 'EntryStride', 'SubEntryStride'))
        vector = stride - sub == 3
        uniform = table['Op'] in (2, 3)
        def point(values):
            if vector:
                first = dict(zip(('X', 'Y', 'Z'), values[:3]))
                return {'v1': first, 'v2': dict(zip(('X', 'Y', 'Z'), values[3:]))} if uniform else first
            return {'X': values[0], 'Y': values[1]} if uniform else values[0]
        if count > 1:
            points = [{'InVal': table.get('TimeBias', 0) + i / table['TimeScale'],
                       'OutVal': point(table['Values'][i * stride:(i + 1) * stride]),
                       'InterpMode': 'CIM_Linear'} for i in range(count)]
            if scientific(points):
                before_change()
                put(distribution, 'ConstantCurve', {'Points': points, 'bIsLooped': False})
                put(distribution, 'bIsDirty', False)
                editor_changed.append(field)
        elif scientific(table['Values']):
            before_change()
            values = table['Values']
            if uniform:
                put(distribution, 'Min', dict(zip(('X', 'Y', 'Z'), values[:3])) if vector else values[0])
                put(distribution, 'Max', dict(zip(('X', 'Y', 'Z'), values[3:])) if vector else values[1])
            else:
                put(distribution, 'Constant', point(values))
            put(distribution, 'bIsDirty', False)
            editor_changed.append(field)
        result = dict(value)
        result['Distribution'] = {'ObjectPath': token}
        return result
    for i, export in enumerate(original):
        obj = local[row['source_package'] + '.' + str(i)]
        for key, value in export.get('Properties', {}).items():
            replacement = restore(value, 'exports[' + str(i) + '].Properties.' + key)
            if scientific(value):
                before_change()
                put(obj, key, replacement, local)
                changed.append({'object': obj.get_path_name(), 'property': key})
    if backed_up:
        save(asset)
        REPORT['assets'].append({'source': row['source_package'], 'destination': row['destination'],
                                 'source_fields': changed, 'derived_editor_fields': editor_changed})


def numeric():
    rows = [r for r in ROWS if r['source_type'] == 'ParticleSystem']
    if PHASE == 'numericprobe':
        rows = [r for r in rows if r['name'] == 'PP_AtkEx_Guard']
    for row in rows:
        print('KZFX_DECIMAL_REPAIR ' + row['destination'], flush=True)
        numeric_particles(row)
    if PHASE == 'numericprobe':
        return
    for row in ROWS:
        typ = row['source_type']
        if typ == 'MaterialInstanceConstant':
            asset = unreal.load_asset(row['destination'])
            props = source(row).get('Properties', {})
            stale = any(ref(v['ParameterValue']) != n.get_editor_property('parameter_value')
                        for v, n in zip(props.get('TextureParameterValues', []), asset.get_editor_property('texture_parameter_values')))
            if scientific(props) or stale:
                backup_owned(row, asset)
                instance(row, force=True)
        elif typ == 'StaticMesh':
            props = source(row).get('Properties', {})
            affected = {k: v for k, v in props.items() if scientific(v)}
            if affected:
                asset = unreal.load_asset(row['destination'])
                backup_owned(row, asset)
                for k, v in affected.items():
                    put(asset, k, v)
                save(asset)
                REPORT['assets'].append({'destination': row['destination'], 'fields': list(affected)})
    data_assets()


def main():
    if PHASE in ('dependencies', 'cube'):
        dependencies()
    elif PHASE == 'materials':
        for row in ROWS:
            if row['source_type'] == 'Material':
                master(row)
        for row in ROWS:
            if row['source_type'] == 'MaterialInstanceConstant':
                instance(row)
    elif PHASE == 'meshes':
        meshes()
    elif PHASE == 'data':
        data_assets()
    elif PHASE == 'buffers':
        buffers()
    elif PHASE == 'rebind':
        rebind()
    elif PHASE == 'samplers':
        samplers()
    elif PHASE == 'names':
        names()
    elif PHASE in ('numeric', 'numericprobe'):
        numeric()
    elif PHASE == 'numericdata':
        data_assets()
    elif PHASE in ('probe', 'bloodprobe', 'particles'):
        rows = [r for r in ROWS if r['source_type'] == 'ParticleSystem']
        if PHASE == 'probe':
            rows = [r for r in rows if r['name'] == 'PP_AtkEx_Guard']
        elif PHASE == 'bloodprobe':
            rows = [r for r in rows if r['name'] == 'FP_BloodBleed_001']
        for row in rows:
            print('KZFX_IMPORTING ' + row['destination'], flush=True)
            (META / 'ParticleImportCurrent.json').write_text(json.dumps({'source': row['source_package'], 'destination': row['destination']}), encoding='utf-8')
            obj = cascade(row)
            if PHASE == 'probe':
                export_text(obj, BASE / 'CascadeProbe.t3d')
            elif PHASE == 'bloodprobe':
                export_text(obj, BASE / 'CascadeBloodProbe.t3d')
    else:
        raise ValueError(PHASE)
    REPORT['status'] = 'completed'
    write('Import_' + PHASE, REPORT)
    print('KZ_COMBAT_EFFECTS_' + PHASE.upper() + '_COMPLETE')


try:
    main()
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
    write('Import_' + PHASE, REPORT)
    raise
