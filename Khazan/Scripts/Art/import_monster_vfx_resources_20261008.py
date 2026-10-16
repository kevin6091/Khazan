"""Task-owned delta restoration. Never executes the old importer entry point.

Run in Khazan_MonsterVFXWork_20261008 only, with -KZMVFXPhase=all|...
Original source graphs/metadata and exchange payloads are read-only in Main.
Cooked Niagara without editor graphs is explicitly adapted, never called exact.
"""
from pathlib import Path
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
import os
import re
import struct
import traceback
import zipfile
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert ROOT.parent.name == 'Khazan_MonsterVFXWork_20261008', ROOT
OUT = ROOT / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
OUT.mkdir(parents=True, exist_ok=True)
match = re.search(r'-KZMVFXPhase=(\w+)', unreal.SystemLibrary.get_command_line())
PHASE = match.group(1) if match else 'all'
REPORT = {'schema': 'Khazan.MonsterVFX.NativeDelta.v1', 'phase': PHASE,
          'pid': os.getpid(), 'project': str(ROOT), 'assets': [], 'failures': [],
          'material_recoveries': [], 'detail_mask_migrations': [], 'issues': [],
          'boundary': 'Private delta only. Original shader/NI editor graphs unavailable; source contracts and explicit native recovery distinguished.'}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write(name, value):
    p = OUT / (name + '.json')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

original = (MAIN / 'Scripts/Art/combat_effects_import.py').read_text(encoding='utf-8')
prefix = original.split('\ntry:\n    main()')[0]
assert len(prefix) < len(original)
# Scratch objects are never saved, and must not even target the metadata junction.
prefix = prefix.replace("task.destination_path = '/Game/_Art/Effects/Metadata'",
                        "task.destination_path = '/Game/_Art/Effects/Shared/Data/MonsterScratch'")
prefix = prefix.replace("next(r for r in ROWS if r['destination'] == texture.get_path_name().split('.')[0])",
                        "next(r for r in LOOKUP.values() if r['destination'] == texture.get_path_name().split('.')[0])")
prefix = prefix.replace("'xxDtbVectorParticleParameter': 'DistributionVectorParticleParameter'",
                        "'xxDtbFloatParticleParameter': 'DistributionFloatParticleParameter', 'xxDtbVectorParticleParameter': 'DistributionVectorParticleParameter'")
prefix = prefix.replace("put(obj, 'MirrorFlags', ['EDVMF_Different'] * 3)",
                        "obj.set_editor_property('mirror_flags', [type(obj.get_editor_property('mirror_flags')[0]).EDVMF_DIFFERENT] * 3)")
H = {}
exec(compile(prefix, 'combat_effects_import_definitions_only', 'exec'), H)

GLOBAL = json.loads((MAIN / 'Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json').read_text(encoding='utf-8'))
union = {r['source_package']: dict(r, reused_native=(ROOT / 'Content' / (r['destination'].removeprefix('/Game/') + '.uasset')).is_file(), task_scope=False) for r in GLOBAL}
for folder in ('HumanOriginal', 'ApesYetugaOriginal'):
    p = MAIN / 'Metadata/MonsterVFX_20261008' / folder / 'ImportReadyAssetManifest.json'
    if p.is_file():
        content = json.loads(p.read_text(encoding='utf-8'))
        rows = content if isinstance(content, list) else content.get('assets', content.get('resources', []))
        for row in rows:
            key = row['source_package']
            if key in union and union[key].get('reused_native'):
                # Original global native identity wins; do not clone/reimport it.
                union[key].update({k: v for k, v in row.items() if k not in ('destination', 'reused_native')})
                union[key]['task_scope'] = True
            else:
                union[key] = dict(row, task_scope=True)
LOOKUP = union
ALL = list(union.values())
DELTA = [r for r in ALL if r.get('task_scope') and not r.get('reused_native') and not r.get('audit_only_actor_context')]
ALLOWED = {r['destination'] for r in DELTA}
assert len(ALLOWED) == len(DELTA), 'Delta destination collision'
REPORT['source_count'] = len(ALL)
REPORT['delta_types'] = dict(Counter(r['source_type'] for r in DELTA))
write('UnionAssetManifest', ALL)

@lru_cache(maxsize=None)
def read_exports(path):
    p = Path(path)
    if not p.is_absolute():
        p = MAIN / p
    return json.loads(p.read_text(encoding='utf-8-sig'))

def native_file(row):
    return ROOT / 'Content' / (row['destination'].removeprefix('/Game/') + '.uasset')

BASELINE = {}
for row in ALL:
    p = native_file(row)
    if row.get('reused_native') and p.is_file():
        BASELINE[row['destination']] = sha(p)

old_make, old_save = H['make'], H['save']
def make(row, cls, factory):
    assert row['destination'] in ALLOWED, 'Refuse non-delta create: ' + row['destination']
    assert row['destination'].startswith('/Game/_Art/Effects/')
    return old_make(row, cls, factory)

def save(obj):
    dest = obj.get_path_name().split('.')[0]
    assert dest in ALLOWED, 'Refuse non-delta save: ' + dest
    return old_save(obj)

H.update(ROOT=ROOT, BASE=OUT / 'Staging', META=OUT, ROWS=DELTA, LOOKUP=LOOKUP,
         PHASE=PHASE, REPORT=REPORT, ISSUES=REPORT['issues'], read_exports=read_exports,
         make=make, save=save, write=write)
H['BASE'].mkdir(parents=True, exist_ok=True)
LIB, FX = H['LIB'], H['FX']
put, ref, source, exports = H['put'], H['ref'], H['source'], H['exports']
old_master, old_instance = H['master'], H['instance']
adapter_file = OUT / 'NativeAdapterMap.json'
ADAPTERS = [r for r in json.loads(adapter_file.read_text(encoding='utf-8')).get('adapters', []) if r.get('adapter_kind') != 'shared_decal_gpu_curve_variant'] if adapter_file.is_file() else []
CURVES = []
curve_names = ['FC_Decal_FadeOut', 'FC_Decal_FadeOut_SlowIn', 'FC_Decal_FastIn_SlowOut', 'FC_Decal_FadeOut_Fast',
               'FC_Decal_FadeInFadeOut_Fast', 'FC_Decal_FadeOut_SlowIn_2', 'FC_Fade_Out']
for index, name in enumerate(curve_names):
    row = next((r for r in ALL if r['name'] == name and r['source_type'] == 'CurveFloat'), None)
    path = Path(row['source_json']) if row else MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/DecalCurveExtraction/BBQ/Content/_Kazan_/Art/VFX/VFX_Data/Curve/BBQ_Curve' / (name + '.json')
    if not path.is_absolute():
        path = MAIN / path
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    obj = next(e for e in raw if e['Type'] == 'CurveFloat')
    keys = obj['Properties']['FloatCurve']['Keys']
    assert len(keys) >= 2 and all(k.get('TangentWeightMode', 'RCTWM_WeightedNone') == 'RCTWM_WeightedNone' for k in keys)
    CURVES.append({'index': index, 'name': name, 'source_package': row['source_package'] if row else obj['Package'],
                   'source_json': str(path), 'source_sha256': sha(path), 'keys': keys, 'last_time_seconds': keys[-1]['Time']})
write('DecalCurveRegistry', CURVES)

def curve_hlsl():
    result = ['if(CurveIndex<0 || LifeSpan<=0)return 1;']
    for curve in CURVES:
        keys = curve['keys']
        result += ['if(CurveIndex<' + repr(curve['index'] + .5) + '){',
                   'float t=saturate(max(0,Time-SpawnTime)*TimeScale/max(LifeSpan,0.00001))*' + repr(float(keys[-1]['Time'])) + ';',
                   'if(t<=' + repr(float(keys[0]['Time'])) + ')return ' + repr(float(keys[0]['Value'])) + ';']
        for left, right in zip(keys, keys[1:]):
            span = right['Time'] - left['Time']
            assert span > 0
            result.append('if(t<' + repr(float(right['Time'])) + '){float u=(t-' + repr(float(left['Time'])) + ')/' + repr(float(span)) + ';')
            mode = left['InterpMode']
            if mode == 'RCIM_Constant':
                result.append('return ' + repr(float(left['Value'])) + ';')
            elif mode == 'RCIM_Linear':
                result.append('return lerp(' + repr(float(left['Value'])) + ',' + repr(float(right['Value'])) + ',u);')
            else:
                assert mode == 'RCIM_Cubic', mode
                result.append('float u2=u*u,u3=u2*u;return (2*u3-3*u2+1)*' + repr(float(left['Value'])) + '+(u3-2*u2+u)*' + repr(float(span * left['LeaveTangent'])) + '+(-2*u3+3*u2)*' + repr(float(right['Value'])) + '+(u3-u2)*' + repr(float(span * right['ArriveTangent'])) + ';')
            result.append('}')
        result += ['return ' + repr(float(keys[-1]['Value'])) + ';', '}']
    result.append('return 1;')
    return '\n'.join(result)

CURVE_CODE = curve_hlsl()
(OUT / 'SourceDecalCurves.hlsl').write_text(CURVE_CODE + '\n', encoding='utf-8')

def prepare_decal_variants():
    """Clone only shared decal dependency chains; retain source identity."""
    selected = set()
    for row in ALL:
        if row.get('task_scope') and row['source_type'] in ('Material', 'MaterialInstanceConstant'):
            ancestor = row
            seen = set()
            while ancestor and ancestor['source_package'] not in seen:
                seen.add(ancestor['source_package'])
                props = source(ancestor).get('Properties', {})
                if ancestor['source_type'] == 'Material':
                    if props.get('MaterialDomain') == 'MD_DeferredDecal':
                        selected.update(seen)
                    break
                ancestor = LOOKUP.get(props.get('Parent', {}).get('ObjectPath', '').split('.')[0])
    for key in sorted(selected):
        row = LOOKUP[key]
        if row['destination'] in ALLOWED:
            continue
        native = row['destination']
        variant = dict(row, reused_native=False, author_variant=True, variant_template=native,
                       destination='/Game/_Art/Effects/Monsters/Materials/' + row['name'] + '_MonsterCurve_' + hashlib.sha256(key.encode()).hexdigest()[:8])
        LOOKUP[key] = variant
        for i, existing in enumerate(ALL):
            if existing['source_package'] == key:
                ALL[i] = variant
                break
        DELTA.append(variant)
        ALLOWED.add(variant['destination'])
        ADAPTERS.append({'source_package': key, 'source_sha256': row['source_sha256'], 'source_type': row['source_type'],
                         'native_destination': variant['destination'], 'native_type': row['source_type'],
                         'adapter_kind': 'shared_decal_gpu_curve_variant', 'template': native,
                         'boundary': 'Only task-specific clone gets expanded GPU lifetime registry; original Player/shared assets remain byte-identical.'})

prepare_decal_variants()
write('NativeAdapterMap', {'schema': 'Khazan.MonsterVFX.NativeAdapters.v1', 'adapters': ADAPTERS})

def master(row):
    if row['destination'] not in ALLOWED:
        asset = unreal.load_asset(row['destination'])
        assert asset and isinstance(asset, unreal.Material), row['destination']
        return asset
    return recover_master(row)

def instance(row, force=False):
    if row['destination'] not in ALLOWED:
        asset = unreal.load_asset(row['destination'])
        assert asset and isinstance(asset, unreal.MaterialInstanceConstant), row['destination']
        return asset
    return old_instance(row, force)

H.update(master=master, instance=instance)

def recover_master(row):
    """Source parameter preservation plus explicit reconstructed mask/UV wiring."""
    m = make(row, unreal.Material, unreal.MaterialFactoryNew())
    needs_static = row['name'] in ('FM_Base_PP_Grass_Random_001', 'PP_Snow_Powder')
    if unreal.EditorAssetLibrary.get_metadata_tag(m, 'KZFXMaterialRecovery') == 'monster-source-contracts-v1' and (not needs_static or unreal.EditorAssetLibrary.get_metadata_tag(m, 'KZFXStaticTextureRecovery')):
        return m
    original = source(row)
    props = original.get('Properties', {})
    if row.get('variant_template') and row['name'] in ('Base_Blood_Decal', 'Base_Decal_BottomCrack'):
        # These verified Player graphs already have source mask/channel wiring.
        # Duplicate into the new private path and update only its curve registry.
        template = unreal.load_asset(row['variant_template'])
        assert template
        # make() may have created an empty shell; replace it before use, never the template.
        assert unreal.EditorAssetLibrary.delete_loaded_asset(m)
        folder, name = row['destination'].rsplit('/', 1)
        m = H['TOOLS'].duplicate_asset(name, folder, template)
        assert m
        curve_node = unreal.find_object(m, 'MaterialExpressionCustom_0')
        if not curve_node:
            curve_node = unreal.find_object(None, m.get_path_name() + ':MaterialExpressionCustom_0')
        assert curve_node and 'CurveIndex' in curve_node.get_editor_property('code'), row
        curve_node.set_editor_property('code', CURVE_CODE)
        unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXSourcePackage', row['source_package'])
        unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXSourceSHA256', row['source_sha256'])
        unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXMaterialRecovery', 'monster-source-contracts-v1')
        errors = LIB.recompile_material(m)
        assert not errors, errors
        save(m)
        REPORT['material_recoveries'].append({'source_package': row['source_package'], 'source_sha256': row['source_sha256'],
                                               'destination': row['destination'], 'template': row['variant_template'],
                                               'compile_errors': [], 'curve_registry_count': len(CURVES),
                                               'boundary': 'Existing verified mask/UV shader copied; only GPU curve lookup expanded.'})
        return m
    defaults = H['parameters'](original)
    static_textures = []
    if not defaults['TextureValues']:
        for index, value in enumerate(props.get('CachedExpressionData', original.get('CachedExpressionData', {})).get('ReferencedTextures', [])):
            if value and value.get('ObjectPath', '').startswith('BBQ/'):
                name = 'KZSourceReferencedTexture' + str(index)
                defaults['TextureValues'][name] = value
                static_textures.append({'native_technical_parameter': name, 'source_field': 'CachedExpressionData.ReferencedTextures[' + str(index) + ']', 'raw_reference': value})
    descendants = {row['source_package']}
    changed = True
    while changed:
        changed = False
        for child in ALL:
            if child['source_type'] != 'MaterialInstanceConstant' or child['source_package'] in descendants:
                continue
            cp = source(child).get('Properties', {})
            if cp.get('Parent', {}).get('ObjectPath', '').split('.')[0] in descendants:
                descendants.add(child['source_package'])
                changed = True
                for key, target in [('ScalarParameterValues', 'ScalarValues'), ('VectorParameterValues', 'VectorValues'), ('TextureParameterValues', 'TextureValues')]:
                    for value in cp.get(key, []):
                        pn = value['ParameterInfo']['Name']
                        if pn not in defaults[target] or defaults[target][pn] is None:
                            defaults[target][pn] = value['ParameterValue']
    m.modify()
    LIB.delete_all_material_expressions(m)
    for key in ('BlendMode', 'TwoSided', 'OpacityMaskClipValue'):
        if key in props:
            put(m, key, props[key])
    decal = props.get('MaterialDomain') == 'MD_DeferredDecal'
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL if decal else unreal.MaterialDomain.MD_SURFACE)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    for usage in (unreal.MaterialUsage.MATUSAGE_PARTICLE_SPRITES, unreal.MaterialUsage.MATUSAGE_MESH_PARTICLES,
                  unreal.MaterialUsage.MATUSAGE_BEAM_TRAILS, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,
                  unreal.MaterialUsage.MATUSAGE_NIAGARA_MESH_PARTICLES, unreal.MaterialUsage.MATUSAGE_NIAGARA_RIBBONS):
        LIB.set_material_usage(m, usage)
    n = 0
    nodes, inputs = {}, {}
    def node(cls, **values):
        nonlocal n
        obj = LIB.create_material_expression(m, cls, -1400 + (n % 6) * 220, (n // 6) * 140)
        n += 1
        for k, v in values.items():
            obj.set_editor_property(k, v)
        return obj
    for name, value in defaults['ScalarValues'].items():
        nodes['S:' + name] = (node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value), '')
    for name, value in defaults['VectorValues'].items():
        nodes['V:' + name] = (node(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                                  default_value=unreal.LinearColor(*[value.get(c, 0) for c in 'RGBA'])), 'RGBA')
    textures = {}
    for name, value in defaults['TextureValues'].items():
        texture = ref(value)
        if not value:
            REPORT['issues'].append({'kind': 'source_null_texture_parameter', 'source': row['source_package'], 'parameter': name})
            continue
        assert texture, (row['name'], name, value)
        cls = unreal.MaterialExpressionTextureObjectParameter
        obj = node(cls, parameter_name=name, texture=texture, sampler_type=H['sampler'](texture))
        nodes['T:' + name] = (obj, '')
        textures[name] = value
    nodes['UV'] = (node(unreal.MaterialExpressionTextureCoordinate), '')
    nodes['Time'] = (node(unreal.MaterialExpressionTime), '')
    nodes['Age'] = (node(unreal.MaterialExpressionParticleRelativeTime), '')
    nodes['PC'] = (node(unreal.MaterialExpressionConstant4Vector, constant=unreal.LinearColor(1, 1, 1, 1)) if decal else node(unreal.MaterialExpressionParticleColor), 'RGBA')
    dynamic = props.get('CachedExpressionData', {}).get('DynamicParameterNames') or []
    if len(dynamic) == 4:
        dp = node(unreal.MaterialExpressionDynamicParameter, param_names=dynamic, parameter_index=0)
        output_names = list(LIB.get_material_expression_output_names(dp))[:4]
        for i, name in enumerate(output_names):
            nodes['DP:' + dynamic[i]] = (dp, name)
    def inp(key):
        if key not in inputs:
            assert key in nodes, (row['name'], key)
            inputs[key] = ('P' + str(len(inputs)), nodes[key])
        return inputs[key][0]
    def scalar(names, fallback):
        key = next(('S:' + name for name in names if 'S:' + name in nodes), None)
        return inp(key) if key else fallback
    def vector(names, fallback):
        key = next(('V:' + name for name in names if 'V:' + name in nodes), None)
        return inp(key) + '.rgb' if key else fallback
    def dp_name(token, fallback):
        key = next(('DP:' + name for name in dynamic if token in name.lower()), None)
        return inp(key) if key else fallback
    def uv_for(name):
        uv = inp('UV')
        prefix = 'Opa' if 'opa' in name.lower() else ('Emi' if 'emi' in name.lower() else 'Base')
        u = scalar([prefix + '_Utile', prefix + '_TilingU', 'U_Tile', 'U_tile', 'Base_Tile_U', 'Base_UT'], '1')
        v = scalar([prefix + '_Vtile', prefix + '_TilingV', 'V_Tile', 'V_tile', 'Base_Tile_V', 'Base_VT'], '1')
        su = scalar([prefix + '_Uspeed', prefix + '_SpeedU', 'Base_USpeed'], '0')
        sv = scalar([prefix + '_Vspeed', prefix + '_SpeedV', 'Base_VSpeed', 'Base_VS'], '0')
        ou = scalar([prefix + '_Uoff', prefix + '_OffsetU'], '0')
        ov = scalar([prefix + '_Voff', prefix + '_OffsetV'], '0')
        if len(dynamic) == 4 and any(t in dynamic[0].lower() for t in ('uoffset', 'offset')):
            ou = '(' + ou + '+' + inp('DP:' + dynamic[0]) + ')'
        result = '(' + uv + '*float2(' + u + ',' + v + ')+' + inp('Time') + '*float2(' + su + ',' + sv + ')+float2(' + ou + ',' + ov + '))'
        control = next(('V:' + k for k in (prefix + '_UVcontrol', 'MaskTexUV') if 'V:' + k in nodes), None)
        if control:
            result = '(' + result + '*' + inp(control) + '.rg+' + inp(control) + '.ba)'
        cols = next((k for k in ('SubUV_Columns', 'SubUV_U', 'Columns') if 'S:' + k in nodes), None)
        rows = next((k for k in ('SubUV_Rows', 'SubUV_V', 'Rows') if 'S:' + k in nodes), None)
        if cols and rows and ('subuv' in name.lower() or 'subuv' in row['name'].lower()):
            frame = dp_name('subuv_ani', inp('Age'))
            c, r = inp('S:' + cols), inp('S:' + rows)
            result = '((' + result + '+float2(fmod(min(floor(saturate(' + frame + ')*max(' + c + '*' + r + ',1)),max(' + c + '*' + r + '-1,0)),max(' + c + ',1)),floor(min(floor(saturate(' + frame + ')*max(' + c + '*' + r + ',1)),max(' + c + '*' + r + '-1,0))/max(' + c + ',1))))/max(float2(' + c + ',' + r + '),1))'
        return result
    def tex(name):
        key = inp('T:' + name)
        return 'Texture2DSample(' + key + ',' + key + 'Sampler,' + uv_for(name) + ')'
    preferred = ('Tex_Emi', 'Emi_Main_Tex', 'Emi_Tex', 'Tex_SubUV', 'MainSubUVTex', 'DecalTexture', 'BaseTex', 'Base_Texture', 'Tex_Base', 'MaskTex', 'Opa_Tex', 'Tex_Opa')
    color_name = next((k for k in preferred if k in textures), None)
    if color_name is None:
        color_name = next((k for k in textures if not any(t in k.lower() for t in ('position', 'rotation', 'lookup', 'normal', 'dist', 'noise', 'refraction'))), None)
    opacity_name = next((k for k in ('Tex_OPA', 'Tex_Opa', 'Opa_Tex', 'MaskTex', 'DecalTexture', 'MainSubUVTex') if k in textures), color_name)
    code = 'float4 pc=' + inp('PC') + '; float3 image=' + (tex(color_name) + '.rgb' if color_name else 'float3(1,1,1)') + ';\n'
    if opacity_name:
        code += 'float4 maskSample=' + tex(opacity_name) + '; float density=max(maskSample.r,max(maskSample.g,maskSample.b));\n'
        if 'SubUV_channel_count' in defaults['ScalarValues'] and defaults['ScalarValues']['SubUV_channel_count'] == 4:
            random = dp_name('random', '0')
            code += 'int channel=(int)floor(saturate(' + random + ')*3.999); density=channel==0?maskSample.r:(channel==1?maskSample.g:(channel==2?maskSample.b:maskSample.a));\n'
    else:
        code += 'float density=1;\n'
    code += 'density=pow(saturate(density),' + scalar(['Opa_pow', 'OPA_Pow', 'DecalPow', 'Pow'], '1') + ');\n'
    dissolve = dp_name('dissolve', '0')
    code += 'float opacity=saturate(density-' + dissolve + ')*' + scalar(['Opa_str', 'OPA_str', 'MasterOpacity', 'DecalStrangth', 'FadeOut'], '1') + '*pc.a;\n'
    tint = vector(['Emi_MainColor', 'Main_Color', 'OverallColor', 'BaseColor', 'Base_Color', 'Base_color', 'Inner_Color'], 'float3(1,1,1)')
    code += 'float3 color=image*' + tint + '*' + scalar(['Emi_pow', 'Emi_Pow', 'Emi_str', 'Base_Pow'], '1') + '*pc.rgb;\n'
    if 'Emi_Sub_Tex' in textures:
        code += 'color+=' + tex('Emi_Sub_Tex') + '.rgb*' + vector(['Emi_SubColor'], 'float3(1,1,1)') + '*' + scalar(['Emi_sub_pow'], '1') + '*pc.rgb;\n'
    code += 'return float4(color,opacity);'
    custom = node(unreal.MaterialExpressionCustom, code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                  description='Original parameters/textures; interpreted density, DP dissolve, source UV pan/atlas recovery')
    custom.set_editor_property('inputs', [H['custom_input'](alias) for alias, value in inputs.values()])
    for alias, (obj, output) in inputs.values():
        H['connect'](obj, output, custom, alias)
    rgb = node(unreal.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    opacity = node(unreal.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    H['connect'](custom, '', rgb, '')
    H['connect'](custom, '', opacity, '')
    assert LIB.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if decal:
        assert LIB.connect_material_property(rgb, '', unreal.MaterialProperty.MP_BASE_COLOR)
    blend = m.get_editor_property('blend_mode')
    if blend != unreal.BlendMode.BLEND_OPAQUE:
        final_opacity = opacity
        if decal:
            curve_inputs = {'Time': nodes['Time']}
            for name, pin, value in [('KZDecalSpawnTime', 'SpawnTime', 0.0), ('KZDecalTimeScale', 'TimeScale', 1.0),
                                     ('KZDecalLifeSpan', 'LifeSpan', 0.0), ('KZDecalCurveIndex', 'CurveIndex', -1.0)]:
                curve_inputs[pin] = (node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value), '')
            curve = node(unreal.MaterialExpressionCustom, code=CURVE_CODE, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                         inputs=[H['custom_input'](pin) for pin in curve_inputs], description='Exact raw source curve keys; lifespan-normalized GPU reconstruction')
            for pin, (expr, output) in curve_inputs.items():
                H['connect'](expr, output, curve, pin)
            final_opacity = node(unreal.MaterialExpressionMultiply)
            H['connect'](opacity, '', final_opacity, 'A')
            H['connect'](curve, '', final_opacity, 'B')
        assert LIB.connect_material_property(final_opacity, '', unreal.MaterialProperty.MP_OPACITY)
        if blend == unreal.BlendMode.BLEND_MASKED:
            assert LIB.connect_material_property(final_opacity, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXMaterialRecovery', 'monster-source-contracts-v1')
    if static_textures:
        unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXStaticTextureRecovery', 'Exact original static texture identities, reconstructed native UV/mask; no original static parameter names asserted.')
    unreal.EditorAssetLibrary.set_metadata_tag(m, 'KZFXRecoveryBoundary', 'Cooked topology absent; exact declared parameters/texture dependencies, reconstructed RGB density, source UV pan/grid and named DP dissolve. VAT/refraction/dynamic remesh not exact.')
    errors = LIB.recompile_material(m)
    assert not errors, (row['name'], [str(e) for e in errors])
    save(m)
    record = {'source_package': row['source_package'], 'source_sha256': row['source_sha256'], 'destination': row['destination'],
              'declared_parameters': {k: list(v) for k, v in defaults.items()}, 'connected_inputs': list(inputs),
              'color_texture': color_name, 'opacity_texture': opacity_name, 'dynamic_parameter_names': dynamic,
              'static_texture_recovery': static_textures,
              'compile_errors': [], 'boundary': 'Reconstructed shader; source conditional/static-switch/VAT graphs unavailable.'}
    REPORT['material_recoveries'].append(record)
    (OUT / (row['name'] + '.hlsl')).write_text(code + '\n', encoding='utf-8')
    return m

def one(row, action):
    REPORT['current'] = {'source_package': row['source_package'], 'source_sha256': row['source_sha256'],
                         'source_json': row['source_json'], 'destination': row['destination'], 'stage': action.__name__}
    write('ImportReport', REPORT)
    print('KZ_MONSTER_VFX_IMPORT ' + row['destination'] + ' ' + action.__name__, flush=True)
    try:
        action(row)
    except Exception:
        REPORT['failures'].append(dict(REPORT['current'], error=traceback.format_exc()))
        unreal.log_error(REPORT['failures'][-1]['error'])
    write('ImportReport', REPORT)

def dependencies(row):
    typ = row['source_type']
    if typ == 'VectorFieldStatic':
        info = row.get('vector_field_conversion', {})
        files = [MAIN / info['fga']] if info.get('fga') else [MAIN / 'Metadata/MonsterVFX_20261008/HumanOriginal/VectorFields' / (row['name'] + '.fga')]
        obj = H['payload'](row, files, unreal.VectorFieldStaticFactory())
    else:
        files = [MAIN / v['file'] for v in row.get('payload_files', []) if Path(v['file']).suffix.lower() in ('.png', '.hdr', '.exr', '.dds')]
        assert files, row
        factory = unreal.TextureFactory()
        put(factory, 'HDRImportShouldBeLongLatCubeMap', 'NoAll')
        obj = H['payload'](row, files, factory)
        props = source(row).get('Properties', {})
        for key in ('SRGB', 'CompressionSettings', 'AddressX', 'AddressY', 'Filter', 'LODGroup'):
            if key in props:
                put(obj, key, props[key])
    save(obj)
    REPORT['assets'].append({'source': row['source_package'], 'source_sha256': row['source_sha256'],
                             'destination': row['destination'], 'type': obj.get_class().get_name(),
                             'payload_files': row.get('payload_files', [])})

def meshes(row):
    files = [MAIN / f['file'] for f in row.get('payload_files', []) if f['file'].lower().endswith('.pskx')]
    assert files, row
    raw = bytearray(files[0].read_bytes())
    offset = 0
    while offset < len(raw):
        chunk, flags, size, count = struct.unpack_from('<20siii', raw, offset)
        offset += 32
        if chunk.rstrip(b'\0') == b'MATT0000':
            for i in range(count):
                start = offset + i * size
                raw[start:start + 64] = ('KZFX_Temporary_' + str(i)).encode('ascii').ljust(64, b'\0')
        offset += size * count
    path = H['BASE'] / (row['name'] + '.pskx')
    path.write_bytes(raw)
    obj = H['payload'](row, [path], unreal.PSKXFactory())
    original = source(row)
    mats = original.get('Materials', original.get('Properties', {}).get('StaticMaterials', []))
    assert mats, row
    for i, value in enumerate(mats):
        mat = value.get('MaterialInterface', value.get('Material')) if isinstance(value, dict) else value
        obj.set_material(i, ref(mat))
    if all(isinstance(v, dict) and 'MaterialInterface' in v for v in mats):
        put(obj, 'StaticMaterials', [{k: v[k] for k in ('MaterialInterface', 'MaterialSlotName', 'ImportedMaterialSlotName') if k in v} for v in mats])
    save(obj)
    REPORT['assets'].append({'source': row['source_package'], 'source_sha256': row['source_sha256'],
                             'destination': row['destination'], 'type': 'StaticMesh', 'materials': len(mats)})

def data():
    previous = H['ROWS']
    H['ROWS'] = [r for r in DELTA if r['source_type'] in ('CurveLinearColor', 'CurveFloat', 'CurveLinearColorAtlas', 'MaterialParameterCollection')]
    try:
        if H['ROWS']:
            H['data_assets']()
    finally:
        H['ROWS'] = previous

def particles(row):
    obj = H['cascade'](row)
    changed = []
    # UE4.27 3-quality mask 7 corresponds to UE5.8 low/medium/high/epic mask15.
    # Add Epic only when source enabled High; retain originally disabled bits.
    for emitter in FX.get_cascade_system_emitters(obj):
        value = int(emitter.get_editor_property('detail_mode_bitmask'))
        migrated = value | (8 if value & 4 else 0)
        if migrated != value:
            emitter.set_editor_property('detail_mode_bitmask', migrated)
            changed.append({'object': emitter.get_path_name(), 'source_mask': value, 'native_mask': migrated})
    originals = exports(row)
    root_index = originals.index(source(row))
    paths = {root_index: obj}
    def find(i):
        if i not in paths:
            o = originals[i]
            outer = find(int(o['Outer']['ObjectPath'].rsplit('.', 1)[1]))
            name = o['Name'] if len(outer.get_path_name()) + len(o['Name']) + 1 < 240 else 'E' + str(i)
            paths[i] = unreal.find_object(outer, name)
        assert paths[i], i
        return paths[i]
    for i, original in enumerate(originals):
        props = original.get('Properties', {})
        if any(k.startswith('ParamModes[') for k in props):
            native = find(i)
            values = list(native.get_editor_property('param_modes'))
            for k, raw in props.items():
                if k == 'ParamModes':
                    index = 0
                elif k.startswith('ParamModes['):
                    index = int(k.split('[', 1)[1].rstrip(']'))
                else:
                    continue
                values[index] = getattr(unreal.DistributionParamMode, raw.rsplit('::', 1)[-1].upper())
            native.set_editor_property('param_modes', values)
            changed.append({'object': native.get_path_name(), 'fixed_array': 'ParamModes', 'native': [str(v) for v in values]})
    if changed:
        save(obj)
    REPORT['detail_mask_migrations'].append({'source': row['source_package'], 'destination': row['destination'], 'changes': changed})

def decode_user_defaults(data):
    records = []
    def walk(v, field):
        if isinstance(v, dict):
            params, raw = v.get('SortedParameterOffsets'), v.get('ParameterData')
            if params and isinstance(raw, list):
                blob = bytes(raw)
                for p in params:
                    name, off = p['Name'], p['Offset']
                    typ = p.get('TypeDef', {}).get('ClassStructOrEnum', {}).get('ObjectName', '')
                    value = None
                    if 'NiagaraFloat' in typ and off + 4 <= len(blob):
                        value = struct.unpack_from('<f', blob, off)[0]
                    elif "'Vector'" in typ and off + 12 <= len(blob):
                        value = list(struct.unpack_from('<3f', blob, off))
                    elif 'LinearColor' in typ and off + 16 <= len(blob):
                        value = list(struct.unpack_from('<4f', blob, off))
                    if name.startswith('User.') and value is not None:
                        records.append({'field': field, 'name': name, 'offset': off, 'type': typ, 'value': value})
            for k, c in v.items():
                walk(c, field + '.' + k)
        elif isinstance(v, list):
            for i, c in enumerate(v):
                walk(c, field + '[' + str(i) + ']')
    walk(data, 'Exports')
    values = {r['name']: r for r in records if 'InstanceParamStore' in r['field'] or 'ExposedParameters' in r['field']}
    return values, records

def invisible_light_sprite_material(source_row):
    row = dict(source_row, name='M_MonsterLightOnly', source_type='NativeLightMaterialAdapter', reused_native=False, author_variant=True,
               destination='/Game/_Art/Effects/Monsters/Light/M_MonsterLightOnly')
    if row['destination'] not in ALLOWED:
        ALLOWED.add(row['destination']); DELTA.append(row)
    material = make(row, unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'KZFXNativeAdapter') != 'source-component-light-no-sprite-v1':
        LIB.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        zero = LIB.create_material_expression(material, unreal.MaterialExpressionConstant, 0, 0)
        zero.set_editor_property('r', 0.0)
        assert LIB.connect_material_property(zero, '', unreal.MaterialProperty.MP_OPACITY)
        assert LIB.connect_material_property(zero, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXNativeAdapter', 'source-component-light-no-sprite-v1')
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXRecoveryBoundary', 'Source NI ComponentRenderer renders PointLight only. Zero-opacity Cascade sprite suppresses the additional native default white quad; light module remains active.')
    # Required by the native Cascade sprite renderer even for a zero-opacity
    # light-only adapter. Apply outside the construction tag guard so existing
    # adapters also receive the engine usage flag on explicit regeneration.
    LIB.set_material_usage(material, unreal.MaterialUsage.MATUSAGE_PARTICLE_SPRITES)
    assert not LIB.recompile_material(material)
    save(material)
    return material

def niagara_adapter(row):
    data, original = exports(row), source(row)
    user, records = decode_user_defaults(data)
    duration_key = next((k for k in ('User.EmitterLoopDuration', 'User.LoopDuration', 'User.lifetime_max')
                         if k in user and isinstance(user[k]['value'], (int, float)) and user[k]['value'] > 0), None)
    duration = user[duration_key]['value'] if duration_key else 1.0
    temporary = [{'field': 'emitter_loops', 'value': 1, 'reason': 'Finite feedback burst; original NI execution graph unavailable.'},
                 {'field': 'initial_velocity_cm_s', 'value': [0, 0, 0], 'reason': 'Native initialization; original NI simulation graph unavailable.'},
                 {'field': 'sprite_diameter_cm', 'value': 24.0, 'reason': 'Conservative visible fallback; original per-particle size not available.'},
                 {'field': 'burst_count', 'sprite_value': 12, 'mesh_value': 1, 'reason': 'Visible adapter; compiled zero SpawnRate is not runtime spawn behavior.'}]
    if not duration_key:
        temporary.append({'field': 'particle_lifetime_seconds', 'value': duration, 'reason': 'Finite fallback; original graph unavailable.'})
    graph = [{'Type': 'ParticleSystem', 'Name': row['name'], 'Properties': {'Emitters': []}}]
    package = row['source_package']
    def token(i):
        return {'ObjectPath': package + '.' + str(i)}
    def add(typ, outer, props):
        i = len(graph)
        graph.append({'Type': typ, 'Name': 'A' + str(i), 'Outer': token(outer), 'Properties': props})
        return i
    def distribution(module, vector, value):
        typ = 'DistributionVectorConstant' if vector else 'DistributionFloatConstant'
        return {'Distribution': token(add(typ, module, {'Constant': dict(zip('XYZ', value)) if vector else value}))}
    renderers = []
    for handle in original.get('Properties', {}).get('EmitterHandles', []):
        if not handle.get('bIsEnabled', True):
            continue
        em = data[int(handle['Instance']['ObjectPath'].rsplit('.', 1)[1])]
        ep = em.get('Properties', {})
        for ri, renderer_ref in enumerate(ep.get('RendererProperties', [])):
            renderer_index = int(renderer_ref['ObjectPath'].rsplit('.', 1)[1])
            renderer = data[renderer_index]
            rp, typ = renderer.get('Properties', {}), renderer['Type']
            assert typ in ('NiagaraSpriteRendererProperties', 'NiagaraMeshRendererProperties', 'NiagaraComponentRendererProperties', 'NiagaraRibbonRendererProperties'), typ
            mesh_rows = rp.get('Meshes', []) if typ == 'NiagaraMeshRendererProperties' else [None]
            for mi, mesh_row in enumerate(mesh_rows):
                ei = add('ParticleSpriteEmitter', 0, {'EmitterName': handle.get('Name', 'NI') + '_' + str(ri) + '_' + str(mi), 'DetailModeBitmask': 15})
                li = add('ParticleLODLevel', 0, {'Level': 0, 'bEnabled': True})
                graph[ei]['Properties']['LODLevels'] = [token(li)]
                material = rp.get('Material')
                if mesh_row:
                    mesh_source = LOOKUP.get(mesh_row['Mesh']['ObjectPath'].split('.')[0])
                    assert mesh_source, mesh_row
                    mesh_original = source(mesh_source)
                    slots = mesh_original.get('Materials', mesh_original.get('Properties', {}).get('StaticMaterials', []))
                    if slots:
                        material = slots[0].get('MaterialInterface', slots[0].get('Material')) if isinstance(slots[0], dict) else slots[0]
                required = add('ParticleModuleRequired', 0, {'Material': material, 'EmitterDuration': duration, 'EmitterLoops': 1,
                               'bUseLocalSpace': ep.get('bLocalSpace', False), 'bKillOnCompleted': False})
                spawn = add('ParticleModuleSpawn', 0, {'BurstList': [{'Count': rp.get('ComponentCountLimit', 1) if typ == 'NiagaraComponentRendererProperties' else (1 if mesh_row else 12), 'CountLow': -1, 'Time': 0.0}]})
                graph[spawn]['Properties']['Rate'] = distribution(spawn, False, 0.0)
                lifetime = add('ParticleModuleLifetime', 0, {})
                graph[lifetime]['Properties']['Lifetime'] = distribution(lifetime, False, duration)
                size = add('ParticleModuleSize', 0, {})
                scale = [mesh_row.get('Scale', {}).get(k, 1.0) for k in 'XYZ'] if mesh_row else [24.0] * 3
                graph[size]['Properties']['StartSize'] = distribution(size, True, scale)
                modules = [token(lifetime), token(size)]
                if mesh_row:
                    td = add('ParticleModuleTypeDataMesh', 0, {'Mesh': mesh_row['Mesh'], 'bOverrideMaterial': False})
                    graph[li]['Properties']['TypeDataModule'] = token(td)
                    pivot = mesh_row.get('PivotOffset', {})
                    if any(pivot.get(k, 0) for k in 'XYZ'):
                        location = add('ParticleModuleLocation', 0, {})
                        graph[location]['Properties']['StartLocation'] = distribution(location, True, [pivot.get(k, 0.0) for k in 'XYZ'])
                        modules.append(token(location))
                if typ == 'NiagaraComponentRendererProperties':
                    point = next((o for o in data if 'PointLightComponent' in o['Type']), None)
                    if point:
                        pp = point.get('Properties', {})
                        light = add('ParticleModuleLight', 0, {'bUseInverseSquaredFalloff': pp.get('bUseInverseSquaredFalloff', True)})
                        graph[light]['Properties']['BrightnessOverLife'] = distribution(light, False, pp.get('Intensity', 1.0))
                        graph[light]['Properties']['RadiusScale'] = distribution(light, False, pp.get('AttenuationRadius', 24.0) / 24.0)
                        lc = pp.get('LightColor', {})
                        graph[light]['Properties']['ColorScaleOverLife'] = distribution(light, True, [lc.get(k, 255) / 255.0 for k in 'RGB'])
                        if 'Intensity' not in pp:
                            temporary.append({'field': 'light_brightness', 'value': 1.0, 'reason': 'Original xxPointLightComponent Intensity omitted; original inherited/runtime NI light intensity unavailable.'})
                        temporary.append({'field': 'light_radius_scale', 'value': pp.get('AttenuationRadius', 24.0) / 24.0,
                                          'source': {'field': 'xxPointLightComponent.Properties.AttenuationRadius', 'raw_cm': pp.get('AttenuationRadius')},
                                          'reason': 'Source radius / temporary particle24cm size. Cascade radius scaling interpretation requires real-RHI inspection.'})
                        modules.append(token(light))
                graph[li]['Properties'].update(RequiredModule=token(required), SpawnModule=token(spawn), Modules=modules)
                graph[0]['Properties']['Emitters'].append(token(ei))
                renderers.append({'source_renderer_export_index': renderer_index, 'source_type': typ, 'raw_renderer': rp,
                                  'material_reference': material, 'mesh_scale_or_temporary_sprite_size': scale})
    assert renderers, 'No source renderer: ' + package
    graph_file = OUT / 'NiagaraDerivedGraphs' / (row['name'] + '_' + row['source_sha256'][:8] + '.json')
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    graph_file.write_text(json.dumps(graph, indent=2) + '\n', encoding='utf-8')
    obj = H['cascade'](dict(row, source_type='ParticleSystem', source_json=str(graph_file)))
    native_light_materials = []
    for index, renderer in enumerate(renderers):
        if renderer['source_type'] != 'NiagaraComponentRendererProperties':
            continue
        emitter = FX.get_cascade_system_emitters(obj)[index]
        lod = FX.get_cascade_emitter_lod_level(emitter, 0)
        required = FX.get_lod_level_required_module(lod)
        invisible = invisible_light_sprite_material(row)
        required.set_editor_property('material', invisible)
        count = renderer['raw_renderer'].get('ComponentCountLimit', 1)
        put(FX.get_lod_level_spawn_module(lod), 'BurstList', [{'Count': count, 'CountLow': -1, 'Time': 0.0}])
        native_light_materials.append({'source_renderer_export_index': renderer['source_renderer_export_index'],
                                       'source_field': 'NiagaraComponentRendererProperties.Properties.ComponentCountLimit',
                                       'raw_count': renderer['raw_renderer'].get('ComponentCountLimit'), 'native_count': count,
                                       'native_invisible_sprite_material': invisible.get_path_name(),
                                       'boundary': 'Native Cascade light-only translation suppresses additional sprite geometry; original NI per-frame light attribute graph unavailable.'})
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXOriginalClass', 'NiagaraSystem')
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXNativeAdapter', 'source-renderer-Cascade-v1')
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'KZFXRecoveryBoundary', 'Original NI editor graph unavailable; exact renderer material/mesh/local-space references, finite temporary simulation, not original NI parity.')
    save(obj)
    ADAPTERS.append({'source_package': package, 'source_sha256': row['source_sha256'], 'source_json': row['source_json'],
                     'source_type': 'NiagaraSystem', 'native_destination': row['destination'], 'native_type': 'ParticleSystem',
                     'adapter_kind': 'source_renderer_Cascade', 'original_parameter_stores': records,
                     'lifetime': {'seconds': duration, 'source_field': user[duration_key] if duration_key else None,
                                  'boundary': 'Source default reused as duration; original graph linkage unverified.'},
                     'renderers': renderers, 'temporary_fields': temporary,
                     'native_component_light_adapters': native_light_materials,
                     'derived_graph': str(graph_file), 'derived_graph_sha256': sha(graph_file),
                     'boundary': 'Visible native adapter. Original simulation/VAT/skeletal sampling/component graphs unavailable.'})
    write('NativeAdapterMap', {'schema': 'Khazan.MonsterVFX.NativeAdapters.v1', 'adapters': ADAPTERS})

def rim_adapter():
    events = json.loads((MAIN / 'Metadata/MonsterVFX_20261008/HumanOriginal/AnimationEffectNotifies.json').read_text(encoding='utf-8'))
    event = next(e for e in events if e['notify_type'] == 'xxAnimNotify_RimLight')
    color = event['notify_properties']['CustomColor']
    base = {'source_package': event['source_package'], 'source_sha256': event['source_sha256'], 'source_json': event['source_file'],
            'source_type': 'xxAnimNotify_RimLight', 'reused_native': False, 'author_variant': True}
    master_row = dict(base, name='M_MonsterRim', destination='/Game/_Art/Effects/Monsters/Rim/M_MonsterRim')
    instance_row = dict(base, name='MI_MonsterRim', destination='/Game/_Art/Effects/Monsters/Rim/MI_MonsterRim')
    for row in (master_row, instance_row):
        if row['destination'] not in ALLOWED:
            ALLOWED.add(row['destination'])
            DELTA.append(row)
    material = make(master_row, unreal.Material, unreal.MaterialFactoryNew())
    material.modify()
    LIB.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    LIB.set_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    fresnel = LIB.create_material_expression(material, unreal.MaterialExpressionFresnel, -800, 0)
    weight = LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -800, 120)
    weight.set_editor_property('parameter_name', 'KZVisualRimWeight')
    weight.set_editor_property('default_value', 0.0)
    tint = LIB.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -800, 240)
    tint.set_editor_property('parameter_name', 'KZVisualRimColor')
    tint.set_editor_property('default_value', unreal.LinearColor(color['R'], color['G'], color['B'], color['A']))
    a = LIB.create_material_expression(material, unreal.MaterialExpressionMultiply, -400, 0)
    b = LIB.create_material_expression(material, unreal.MaterialExpressionMultiply, -200, 0)
    H['connect'](fresnel, '', a, 'A'); H['connect'](weight, '', a, 'B')
    H['connect'](a, '', b, 'A'); H['connect'](tint, 'RGB', b, 'B')
    assert LIB.connect_material_property(b, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity = LIB.create_material_expression(material, unreal.MaterialExpressionConstant, -200, 200)
    opacity.set_editor_property('r', 1.0)
    assert LIB.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXNativeAdapter', 'source-RimLight-Overlay-Fresnel')
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXRecoveryBoundary', 'Raw notify RGB and source duration/fade retained. Additive overlay ignores source alpha0; Fresnel engine exponent5 is a temporary rendering adapter, original rim shader unavailable.')
    errors = LIB.recompile_material(material)
    assert not errors, errors
    save(material)
    mi = make(instance_row, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(mi, material)
    LIB.update_material_instance(mi)
    save(mi)
    ADAPTERS.append({'source_package': base['source_package'], 'source_sha256': base['source_sha256'], 'source_json': base['source_json'],
                     'source_field': event['field'], 'source_type': base['source_type'], 'native_destination': instance_row['destination'],
                     'native_type': 'MaterialInstanceConstant', 'adapter_kind': 'source_rim_overlay',
                     'raw_notify_properties': event['notify_properties'], 'runtime_weight_parameter': 'KZVisualRimWeight',
                     'temporary_fields': [{'field': 'FresnelExponent', 'value': 5.0, 'reason': 'Engine material-expression default; original rim falloff shader unavailable.'}],
                     'boundary': 'Visible additive overlay, rawRGB2 and exact sourcefade; not originalgame lighting shader parity.'})
    REPORT['material_recoveries'].append({'destination': master_row['destination'], 'source_package': base['source_package'],
                                          'source_sha256': base['source_sha256'], 'compile_errors': [], 'adapter_kind': 'source_rim_overlay'})

def execution_adapters():
    evidence_file = MAIN / 'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/ApesExecutionMaterialEvidence.json'
    evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
    cache_zip = MAIN / 'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip'
    def actor_source_row(package):
        if package in LOOKUP:
            return LOOKUP[package]
        with zipfile.ZipFile(cache_zip) as archive:
            entry_name = next(n for n in archive.namelist() if n.replace('\\', '/').endswith(package + '.json'))
            raw = archive.read(entry_name)
        cached = OUT / 'ExecutionSource' / (package + '.json')
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(raw)
        data = json.loads(raw.decode('utf-8-sig'))
        obj = next(o for o in data if not o.get('Outer') and o['Type'] in ('Material', 'MaterialInstanceConstant'))
        row = {'source_package': package, 'source_type': obj['Type'], 'name': obj['Name'], 'source_json': str(cached),
               'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_cache_zip': str(cache_zip),
               'source_cache_zip_entry': entry_name, 'source_cache_zip_sha256': sha(cache_zip), 'reused_native': True}
        LOOKUP[package] = row
        return row
    masters = {}
    for entry in evidence['materials']:
        template = unreal.load_asset(entry['native_destination'])
        assert isinstance(template, unreal.MaterialInstanceConstant), entry
        parent = template.get_editor_property('parent')
        parent_instances = []
        while isinstance(parent, unreal.MaterialInstanceConstant):
            parent_instances.append(parent)
            parent = parent.get_editor_property('parent')
        assert isinstance(parent, unreal.Material), parent
        parent_path = parent.get_path_name().split('.')[0]
        for dest in (entry['native_destination'], parent_path):
            f = ROOT / 'Content' / (dest.removeprefix('/Game/') + '.uasset')
            if f.is_file():
                BASELINE.setdefault(dest, sha(f))
        raw_row = actor_source_row(entry['source_package'])
        if parent_path not in masters:
            original_parent = actor_source_row(entry['source_parent'])
            dest = '/Game/_Art/Effects/Monsters/Execution/' + parent.get_name() + '_Execution'
            row = dict(original_parent, destination=dest, name=dest.rsplit('/', 1)[1], source_type='NativeExecutionMaterialAdapter',
                       reused_native=False, author_variant=True, variant_template=parent_path)
            ALLOWED.add(dest); DELTA.append(row)
            material = unreal.load_asset(dest)
            if not material:
                folder, name = dest.rsplit('/', 1)
                material = H['TOOLS'].duplicate_asset(name, folder, parent)
            assert material
            if unreal.EditorAssetLibrary.get_metadata_tag(material, 'KZFXNativeAdapter') != 'source-execution-dissolve-v1':
                baseline_alpha = LIB.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY_MASK)
                baseline_output = LIB.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_OPACITY_MASK)
                assert baseline_alpha, material
                nodes = {}
                def node(cls, **values):
                    obj = LIB.create_material_expression(material, cls, 1600, 140 * len(nodes))
                    for key, value in values.items():
                        obj.set_editor_property(key, value)
                    return obj
                for name in ('execution', 'executionO'):
                    nodes[name] = (node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=0.0), '')
                nodes['ExecutionOffset_radius'] = (node(unreal.MaterialExpressionVectorParameter, parameter_name='ExecutionOffset_radius', default_value=unreal.LinearColor(0, 0, 0, 0)), 'RGBA')
                nodes['UV'] = (node(unreal.MaterialExpressionTextureCoordinate), '')
                nodes['WorldPosition'] = (node(unreal.MaterialExpressionWorldPosition), 'XYZ')
                # Raw Execution/O is not normalized opacity. Original units and
                # topology are unavailable; this explicit adapter uses world-cm
                # radius and a narrow editable noise boundary, never gameplay.
                nodes['Radius'] = (node(unreal.MaterialExpressionScalarParameter, parameter_name='KZExecutionBoundaryWidth', default_value=10.0), '')
                nodes['UVScale'] = (node(unreal.MaterialExpressionScalarParameter, parameter_name='DissolveTexUVScale', default_value=3.0), '')
                nodes['PreviousAlpha'] = (baseline_alpha, baseline_output)
                selected = entry['effective_selected_parameters']['TextureParameterValues']
                for name in ('DissolveTex', 'DissolveMask'):
                    value = next((v['ParameterValue'] for v in selected if v['ParameterInfo']['Name'] == name), None)
                    if value is None:
                        # Eye source has only DissolveTex. Unity mask is a neutral
                        # native adapter term, not recovered original eye topology.
                        assert name == 'DissolveMask', entry
                        continue
                    texture = LIB.get_material_instance_texture_parameter_value(template, name) or ref(value)
                    assert texture, (name, value)
                    nodes[name] = (node(unreal.MaterialExpressionTextureObjectParameter, parameter_name=name, texture=texture, sampler_type=H['sampler'](texture)), '')
                code = 'float radius=max(0.0,max(Execution,ExecutionO)); if(radius<=0)return PreviousAlpha;\n'
                code += 'float width=max(Radius,0.00001); float distanceToOrigin=length(WorldPosition-Offset.rgb);\n'
                mask_code = 'Texture2DSample(DissolveMask,DissolveMaskSampler,UV).r' if 'DissolveMask' in nodes else '1'
                code += 'float mask=' + mask_code + '; float noise=Texture2DSample(DissolveTex,DissolveTexSampler,UV*UVScale).r;\n'
                code += 'float edgeNoise=(saturate(mask*noise)-0.5)*width;\n'
                code += 'float dissolved=smoothstep(-0.5*width,0.5*width,radius-distanceToOrigin+edgeNoise);\n'
                code += 'return PreviousAlpha*(1.0-dissolved);'
                binds = {pin: nodes[key] for pin, key in [('Execution', 'execution'), ('ExecutionO', 'executionO'), ('Offset', 'ExecutionOffset_radius'),
                                                         ('Radius', 'Radius'), ('WorldPosition', 'WorldPosition'), ('UV', 'UV'), ('UVScale', 'UVScale'),
                                                         ('PreviousAlpha', 'PreviousAlpha'), ('DissolveTex', 'DissolveTex')]}
                if 'DissolveMask' in nodes:
                    binds['DissolveMask'] = nodes['DissolveMask']
                custom = node(unreal.MaterialExpressionCustom, code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                              inputs=[H['custom_input'](pin) for pin in binds], description='Explicit source-parameter execution dissolve recovery; original cooked topology absent')
                for pin, (expr, output) in binds.items():
                    H['connect'](expr, output, custom, pin)
                assert LIB.connect_material_property(custom, '', unreal.MaterialProperty.MP_OPACITY_MASK)
                unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXSourcePackage', row['source_package'])
                unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXSourceSHA256', row['source_sha256'])
                unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXNativeAdapter', 'source-execution-dissolve-v1')
                unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXRecoveryBoundary', 'Original BaseColor/normal/roughness copied unchanged. Positive source raw Execution/O interpreted as world-cm expanding radius about source bone XYZ;10cm noise boundary is editable temporary renderer tuning. Original shader units/topology unavailable; scalar1 is not completed opacity.')
                unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXExecutionRadiusRevision', 'source-raw-world-radius-v2')
                errors = LIB.recompile_material(material)
                assert not errors, errors
                (OUT / (row['name'] + '.hlsl')).write_text(code + '\n', encoding='utf-8')
            save(material)
            masters[parent_path] = material
            REPORT['material_recoveries'].append({'destination': dest, 'source_package': row['source_package'], 'source_sha256': row['source_sha256'],
                                                  'template': parent_path, 'compile_errors': [], 'adapter_kind': 'source_execution_dissolve',
                                                  'temporary_fields': {'KZExecutionBoundaryWidth_cm': 10.0, 'raw_positive_execution_interpreted_as_world_cm_radius': True},
                                                  'consumer_inputs': ['execution', 'executionO', 'ExecutionOffset_radius', 'DissolveTex', 'DissolveMask']})
        dest = '/Game/_Art/Effects/Monsters/Execution/' + template.get_name() + '_Execution'
        row = dict(raw_row, destination=dest, name=dest.rsplit('/', 1)[1], source_type='NativeExecutionMaterialInstanceAdapter',
                   reused_native=False, author_variant=True, variant_template=entry['native_destination'])
        ALLOWED.add(dest); DELTA.append(row)
        mi = unreal.load_asset(dest)
        if not mi:
            folder, name = dest.rsplit('/', 1)
            mi = H['TOOLS'].duplicate_asset(name, folder, template)
        assert mi
        LIB.set_material_instance_parent(mi, masters[parent_path])
        # Flatten inherited native MI overrides when replacing the old chain.
        # Copy engine-resolved values, with the original source names; leaf wins.
        effective = {'scalar_parameter_values': {}, 'vector_parameter_values': {}, 'texture_parameter_values': {}}
        for inherited in list(reversed(parent_instances)) + [template]:
            for field in effective:
                for parameter in inherited.get_editor_property(field):
                    info = parameter.get_editor_property('parameter_info')
                    effective[field][str(info.get_editor_property('name'))] = parameter
        for field, values in effective.items():
            mi.set_editor_property(field, list(values.values()))
        LIB.update_material_instance(mi)
        unreal.EditorAssetLibrary.set_metadata_tag(mi, 'KZFXSourcePackage', row['source_package'])
        unreal.EditorAssetLibrary.set_metadata_tag(mi, 'KZFXSourceSHA256', row['source_sha256'])
        unreal.EditorAssetLibrary.set_metadata_tag(mi, 'KZFXNativeAdapter', 'source-execution-dissolve-v1')
        save(mi)
        ADAPTERS.append({'source_package': row['source_package'], 'source_sha256': row['source_sha256'], 'source_json': row['source_json'],
                         'source_type': raw_row['source_type'], 'native_destination': dest, 'native_type': 'MaterialInstanceConstant',
                         'adapter_kind': 'source_execution_dissolve', 'template': entry['native_destination'], 'parent_template': parent_path,
                         'source_evidence': str(evidence_file), 'source_evidence_sha256': sha(evidence_file),
                         'boundary': 'Existing shaded body MI exact parameters/textures retained; temporary source-driven opacity shader only active via scoped runtime slot override.'})

def finish():
    preserved = []
    for dest, before in BASELINE.items():
        p = ROOT / 'Content' / (dest.removeprefix('/Game/') + '.uasset')
        after = sha(p)
        if before != after:
            preserved.append({'destination': dest, 'before': before, 'after': after})
    REPORT['unexpected_reused_asset_changes'] = preserved
    REPORT['status'] = 'completed' if not REPORT['failures'] and not preserved else 'completed_with_errors'
    REPORT['native_assets'] = []
    for row in DELTA:
        p = native_file(row)
        if p.is_file():
            obj = unreal.load_asset(row['destination'])
            REPORT['native_assets'].append({'source_package': row['source_package'], 'source_sha256': row['source_sha256'],
                                           'destination': row['destination'], 'native_type': obj.get_class().get_name() if obj else None,
                                           'file': str(p), 'sha256': sha(p)})
    verification = {'schema': 'Khazan.MonsterVFX.NativeResourceVerification.v1',
                    'scope': 'Task-owned Effects delta plus read-only reused resources',
                    'boundary': 'Native reference/graph inspection in NullRHI; no assertion of real-RHI rendering or original cooked shader/NI parity.',
                    'native_class_counts': dict(Counter(a['native_type'] for a in REPORT['native_assets'])),
                    'particles': [], 'material_instances': [], 'meshes': [], 'missing_native_resources': [], 'inspection_errors': []}
    native_types = {'Texture2D', 'TextureCube', 'VectorFieldStatic', 'CurveFloat', 'CurveLinearColor', 'CurveLinearColorAtlas',
                    'StaticMesh', 'Material', 'MaterialInstanceConstant', 'ParticleSystem', 'NiagaraSystem',
                    'NativeExecutionMaterialAdapter', 'NativeExecutionMaterialInstanceAdapter', 'NativeLightMaterialAdapter', 'xxAnimNotify_RimLight'}
    for row in DELTA:
        if row['source_type'] not in native_types:
            continue
        obj = unreal.load_asset(row['destination'])
        if not obj:
            verification['missing_native_resources'].append({'source_package': row['source_package'], 'destination': row['destination'], 'source_type': row['source_type']})
            continue
        try:
            if isinstance(obj, unreal.ParticleSystem):
                emitters = FX.get_cascade_system_emitters(obj)
                modules = []
                for emitter in emitters:
                    lod = FX.get_cascade_emitter_lod_level(emitter, 0)
                    required = FX.get_lod_level_required_module(lod) if lod else None
                    spawn = FX.get_lod_level_spawn_module(lod) if lod else None
                    material = required.get_editor_property('material') if required else None
                    modules.append({'emitter': emitter.get_path_name(), 'lod0_present': bool(lod), 'required_present': bool(required),
                                    'spawn_present': bool(spawn), 'material': material.get_path_name() if material else None})
                verification['particles'].append({'source_package': row['source_package'], 'destination': row['destination'],
                                                  'original_class': row['source_type'], 'emitter_count': len(emitters), 'lod0_render_modules': modules})
            elif isinstance(obj, unreal.MaterialInstanceConstant):
                parent = obj.get_editor_property('parent')
                verification['material_instances'].append({'source_package': row['source_package'], 'destination': row['destination'],
                                                           'parent': parent.get_path_name() if parent else None,
                                                           'texture_overrides': [{'parameter': str(v.get_editor_property('parameter_info').get_editor_property('name')),
                                                                                 'texture': v.get_editor_property('parameter_value').get_path_name() if v.get_editor_property('parameter_value') else None}
                                                                                for v in obj.get_editor_property('texture_parameter_values')]})
            elif isinstance(obj, unreal.StaticMesh):
                materials = [v.get_editor_property('material_interface') for v in obj.get_editor_property('static_materials')]
                verification['meshes'].append({'source_package': row['source_package'], 'destination': row['destination'],
                                               'material_slots': [v.get_path_name() if v else None for v in materials]})
        except Exception:
            verification['inspection_errors'].append({'source_package': row['source_package'], 'destination': row['destination'], 'error': traceback.format_exc()})
    write('NativeResourceVerification', verification)
    REPORT['missing_native_resources'] = verification['missing_native_resources']
    if verification['missing_native_resources']:
        REPORT['status'] = 'completed_with_errors'
    candidates = []
    for asset in REPORT['native_assets']:
        p = Path(asset['file'])
        relative = p.relative_to(ROOT).as_posix()
        main_file = MAIN / relative
        candidates.append(dict(asset, relative_file=relative, native_sha256=asset['sha256'],
                               before_main_sha256=sha(main_file) if main_file.is_file() else None))
    write('ArtCandidateManifest', {'schema': 'Khazan.MonsterVFX.ArtCandidates.v1', 'project': str(ROOT),
                                   'assets': candidates, 'reused_native_checked': len(BASELINE),
                                   'unexpected_reused_asset_changes': preserved,
                                   'boundary': 'Only listed task delta files permitted for guarded delivery; current private import status is separately recorded.'})
    unique_adapters = {(r['source_package'], r['adapter_kind']): r for r in ADAPTERS}
    write('NativeAdapterMap', {'schema': 'Khazan.MonsterVFX.NativeAdapters.v1', 'adapters': list(unique_adapters.values())})
    write('ImportReport', REPORT)
    write('Import_' + PHASE, REPORT)
    print('KZ_MONSTER_VFX_FINISHED ' + REPORT['status'], flush=True)

try:
    if PHASE in ('all', 'dependencies'):
        for row in DELTA:
            if row['source_type'] in ('Texture2D', 'TextureCube', 'VectorFieldStatic'):
                one(row, dependencies)
    if PHASE in ('all', 'data'):
        try:
            data()
        except Exception:
            REPORT['failures'].append({'stage': 'data', 'error': traceback.format_exc()})
    if PHASE in ('all', 'materials', 'repair'):
        for row in DELTA:
            if row['source_type'] == 'Material':
                one(row, master)
        for row in DELTA:
            if row['source_type'] == 'MaterialInstanceConstant':
                one(row, instance)
    if PHASE in ('all', 'meshes'):
        for row in DELTA:
            if row['source_type'] == 'StaticMesh':
                one(row, meshes)
    if PHASE in ('all', 'particles'):
        for row in DELTA:
            if row['source_type'] == 'ParticleSystem':
                one(row, particles)
    if PHASE in ('all', 'niagara', 'adapters', 'repair'):
        for row in DELTA:
            if row['source_type'] == 'NiagaraSystem':
                one(row, niagara_adapter)
    if PHASE in ('all', 'adapters', 'repair'):
        try:
            rim_adapter()
        except Exception:
            REPORT['failures'].append({'stage': 'rim_adapter', 'error': traceback.format_exc()})
        try:
            execution_adapters()
        except Exception:
            REPORT['failures'].append({'stage': 'execution_adapters', 'error': traceback.format_exc()})
finally:
    finish()
