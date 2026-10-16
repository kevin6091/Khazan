"""Fresh native asset/reference audit. No asset saves and no live editor access."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import struct
import re
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
ROWS = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
BY_PACKAGE = {r['source_package']: r for r in ROWS}
FX = unreal.FXConverterUtilitiesLibrary
LIB = unreal.MaterialEditingLibrary
KEEP = []
REPORT = {'status': 'running', 'fresh_process': True, 'actual_RHI': False,
          'asset_saves': False, 'user_editor_untouched': True, 'assets': [],
          'particle_systems': [], 'errors': [], 'source_only': [], 'distribution_checks': 0,
          'distribution_read_errors': [], 'distribution_shape_changes': [], 'curve_key_checks': 0,
          'boundary': 'Native serialization, classes, emitter/LOD/module counts and source references. Rendering and original appearance equivalence are separate.'}
ADAPTERS = {'xxParticleModuleMeshMaterialOverride': 'ParticleModuleMeshMaterial',
            'xxDtbVectorParticleParameter': 'DistributionVectorParticleParameter'}

def source_data(row):
    data = json.loads((ROOT / row['source_json']).read_text(encoding='utf-8-sig'))
    source = next(o for o in data if o['Type'] == row['source_type'] and not o.get('Outer'))
    return data, source

def expected_ref(value):
    if value is None:
        return None
    p = value['ObjectPath'].split('.')[0]
    if p in BY_PACKAGE:
        return BY_PACKAGE[p]['destination']
    if p.startswith('Engine/Content/'):
        return '/Engine/' + p[len('Engine/Content/'):]
    raise AssertionError(('Visual reference outside extracted closure', value))

def same_float(a, b):
    # Compare source JSON doubles after the engine's serialized float conversion.
    return math.isclose(float(a), struct.unpack('<f', struct.pack('<f', b))[0], rel_tol=2e-6, abs_tol=2e-6)

def check_ref(native, original):
    expected = expected_ref(original)
    assert (native.get_path_name().split('.')[0] if native else None) == expected, (str(native), expected)


def distribution_tables(value):
    if isinstance(value, dict):
        if 'Distribution' in value and 'Table' in value:
            return [value['Table']]
        return [t for v in value.values() for t in distribution_tables(v)]
    return [t for v in value for t in distribution_tables(v)] if isinstance(value, list) else []


def raw_distributions(asset, row, data, original):
    paths = {data.index(original): asset.get_path_name()}
    def object_path(i):
        if i not in paths:
            e = data[i]
            outer = object_path(int(e['Outer']['ObjectPath'].rsplit('.', 1)[1]))
            name = e['Name'] if len(outer) + len(e['Name']) + 1 < 240 else 'E' + str(i)
            paths[i] = outer + (':' if outer == asset.get_path_name() else '.') + name
        return paths[i]
    for i, export in enumerate(data):
        fields = {k: (v, distribution_tables(v)) for k, v in export.get('Properties', {}).items() if distribution_tables(v)}
        if not fields:
            continue
        obj = unreal.find_object(None, object_path(i))
        assert obj, object_path(i)
        for key, (value, source_tables) in fields.items():
            try:
                native = obj.get_editor_property(key)
                native_text = native.export_text() if hasattr(native, 'export_text') else '\n'.join(v.export_text() for v in native)
            except Exception as e:
                REPORT['distribution_read_errors'].append({'asset': row['destination'], 'object': str(obj), 'field': key, 'error': str(e)})
                continue
            tables = re.findall(r'Table=\(([^()]*(?:Values=\([^()]*\))[^()]*)\)', native_text)
            assert len(tables) == len(source_tables), (obj, key, len(tables), len(source_tables))
            for table_text, source_table in zip(tables, source_tables):
                values = re.search(r'Values=\(([^()]*)\)', table_text)
                values = [float(v) for v in values.group(1).split(',') if v] if values else []
                count = re.search(r'EntryCount=(\d+)', table_text)
                stride = re.search(r'EntryStride=(\d+)', table_text)
                count = int(count.group(1)) if count else 0
                stride = int(stride.group(1)) if stride else 0
                # LookupTable.Empty() keeps its value allocation but disables
                # the table with EntryCount=0; evaluation uses the editor object.
                assert count == 0 or len(values) == count * stride, ('Invalid native distribution', obj, key, len(values), count, stride)
                REPORT['distribution_checks'] += 1
                if count != source_table.get('EntryCount', 0) or stride != source_table.get('EntryStride', 0):
                    REPORT['distribution_shape_changes'].append({'asset': row['destination'], 'object': str(obj), 'field': key,
                         'source_count': source_table.get('EntryCount', 0), 'native_count': count,
                         'source_stride': source_table.get('EntryStride', 0), 'native_stride': stride})


def instance(asset, original):
    props = original['Properties']
    check_ref(asset.get_editor_property('parent'), props.get('Parent'))
    for key, native_key in [('TextureParameterValues', 'texture_parameter_values'),
                            ('ScalarParameterValues', 'scalar_parameter_values'),
                            ('VectorParameterValues', 'vector_parameter_values')]:
        native = asset.get_editor_property(native_key)
        source = props.get(key, [])
        assert len(native) == len(source), (asset, key, len(native), len(source))
        for n, s in zip(native, source):
            info = n.get_editor_property('parameter_info')
            assert str(info.get_editor_property('name')).casefold() == s['ParameterInfo']['Name'].casefold(), (asset, key, s)
            assert info.get_editor_property('index') == s['ParameterInfo'].get('Index', -1), (asset, key, s)
            value = n.get_editor_property('parameter_value')
            if key == 'TextureParameterValues':
                check_ref(value, s['ParameterValue'])
            elif key == 'ScalarParameterValues':
                assert value == struct.unpack('<f', struct.pack('<f', s['ParameterValue']))[0], (asset, s, value)
            else:
                assert all(getattr(value, c.lower()) == struct.unpack('<f', struct.pack('<f', s['ParameterValue'].get(c, 0)))[0] for c in 'RGBA'), (asset, s, value)


def color_curve(asset, original):
    # Evaluate each authored key using the native curve API. The protected
    # fixed array itself cannot be read through the Python property wrapper.
    for index, curve in enumerate(original['FloatCurves']):
        channel = 'rgba'[index]
        for key in curve.get('Keys', []):
            value = getattr(asset.get_unadjusted_linear_color_value(key['Time']), channel)
            assert same_float(value, key['Value']), (asset, index, key, value)
            REPORT['curve_key_checks'] += 1

def particles(asset, row, data, source):
    emitters = FX.get_cascade_system_emitters(asset)
    originals = source.get('Properties', {}).get('Emitters', [])
    assert len(emitters) == len(originals), row['name']
    counts = Counter()
    for emitter, e_ref in zip(emitters, originals):
        original = data[int(e_ref['ObjectPath'].rsplit('.', 1)[1])]
        props = original['Properties']
        if 'EmitterName' in props:
            native_name = str(FX.get_cascade_emitter_name(emitter))
            # UE FName identity is case-insensitive; its displayed casing may
            # reflect an earlier loaded name. Source JSON keeps original casing.
            assert native_name.casefold() == props['EmitterName'].casefold(), (emitter, native_name, props['EmitterName'])
        for li, lod_ref in enumerate(props['LODLevels']):
            lod_source = data[int(lod_ref['ObjectPath'].rsplit('.', 1)[1])]['Properties']
            lod = FX.get_cascade_emitter_lod_level(emitter, li)
            assert lod, (row['name'], li)
            required = FX.get_lod_level_required_module(lod)
            spawn = FX.get_lod_level_spawn_module(lod)
            assert required and spawn, row['name']
            req_source = data[int(lod_source['RequiredModule']['ObjectPath'].rsplit('.', 1)[1])]['Properties']
            if 'Material' in req_source:
                check_ref(required.get_editor_property('material'), req_source['Material'])
            modules = FX.get_lod_level_modules(lod)
            assert len(modules) == len(lod_source.get('Modules', [])), (row['name'], li, len(modules), len(lod_source.get('Modules', [])))
            for module, m_ref in zip(modules, lod_source.get('Modules', [])):
                ms = data[int(m_ref['ObjectPath'].rsplit('.', 1)[1])]
                assert module.get_class().get_name() == ADAPTERS.get(ms['Type'], ms['Type']), (row['name'], ms['Type'], module)
                counts[ms['Type']] += 1
            counts['LODLevels'] += 1
    recovery = META / 'Recovery/Cascade' / (row['source_sha256'] + '.json')
    REPORT['particle_systems'].append({'asset': row['destination'], 'emitters': len(emitters),
                                       'counts': dict(counts), 'editor_distribution_report': str(recovery.relative_to(ROOT)) if recovery.exists() else None})

def material(asset, original):
    cached = original.get('CachedExpressionData', {}).get('Parameters', {})
    expressions = LIB.get_material_expressions(asset)
    declared = {}
    for kind, cls in [('scalar', unreal.MaterialExpressionScalarParameter), ('vector', unreal.MaterialExpressionVectorParameter), ('texture', unreal.MaterialExpressionTextureSampleParameter)]:
        for node in expressions:
            if isinstance(node, cls):
                declared[kind, str(node.get_editor_property('parameter_name'))] = node
    for key, values, kind in [('RuntimeEntries', 'ScalarValues', 'scalar'), ('RuntimeEntries[1]', 'VectorValues', 'vector'), ('RuntimeEntries[2]', 'TextureValues', 'texture')]:
        for info, value in zip(cached.get(key, {}).get('ParameterInfos', []), cached.get(values, [])):
            node = declared[kind, info['Name']]
            if kind == 'scalar':
                assert same_float(node.get_editor_property('default_value'), value), info['Name']
            elif kind == 'vector':
                native = node.get_editor_property('default_value')
                assert all(same_float(getattr(native, c.lower()), value.get(c, 0)) for c in 'RGBA'), info['Name']
            else:
                check_ref(node.get_editor_property('texture'), value)
    decal = original.get('Properties', {}).get('MaterialDomain') == 'MD_DeferredDecal'
    assert asset.get_editor_property('material_domain') == (unreal.MaterialDomain.MD_DEFERRED_DECAL if decal else unreal.MaterialDomain.MD_SURFACE)
    assert unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXMaterialRecovery') == 'source-parameters-native-v3'

def main():
    counts = Counter()
    for row in ROWS:
        typ = row['source_type']
        if typ in ('MaterialFunction', 'NiagaraSystem'):
            REPORT['source_only'].append({'source': row['source_package'], 'type': typ})
            continue
        print('KZFX_AUDIT ' + row['destination'], flush=True)
        asset = unreal.load_asset(row['destination'])
        assert asset and asset.get_class().get_name() == typ, (row['destination'], str(asset))
        KEEP.append(asset)
        assert unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXSourcePackage') == row['source_package'], row['name']
        assert unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXSourceSHA256') == row['source_sha256'], row['name']
        data, original = source_data(row)
        if typ == 'ParticleSystem':
            assert unreal.EditorAssetLibrary.get_metadata_tag(asset, 'KZFXGraphImported') == row['source_sha256'] + '|editor-distributions-v2', row['name']
            particles(asset, row, data, original)
            raw_distributions(asset, row, data, original)
        elif typ == 'Material':
            material(asset, original)
        elif typ == 'MaterialInstanceConstant':
            instance(asset, original)
        elif typ == 'CurveLinearColor':
            color_curve(asset, original)
        elif typ == 'StaticMesh':
            native = asset.get_editor_property('static_materials')
            source = original.get('Materials', original.get('Properties', {}).get('StaticMaterials', []))
            assert len(native) == len(source), row['name']
            for n, s in zip(native, source):
                ref = s.get('MaterialInterface', s.get('Material')) if isinstance(s, dict) else s
                check_ref(n.get_editor_property('material_interface'), ref)
                if isinstance(s, dict) and 'MaterialSlotName' in s:
                    assert str(n.get_editor_property('material_slot_name')) == s['MaterialSlotName'], row['name']
        file = ROOT / 'Content' / (row['destination'][len('/Game/'):] + '.uasset')
        assert file.is_file(), file
        REPORT['assets'].append({'asset': row['destination'], 'type': typ,
                                 'file_sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
        counts[typ] += 1
    REPORT['native_counts'] = dict(counts)
    REPORT['native_total'] = sum(counts.values())
    REPORT['status'] = 'passed'
    print('KZ_COMBAT_EFFECTS_FRESH_AUDIT_PASSED', flush=True)

try:
    main()
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
    unreal.log_error(REPORT['error'])
finally:
    (META / 'FreshSavedAssetAudit.json').write_text(json.dumps(REPORT, indent=2) + '\n', encoding='utf-8')
if REPORT['status'] != 'passed':
    raise RuntimeError(REPORT.get('error', 'Asset audit failed'))
