"""Root-launched two-private-master visual repair; default probe saves nothing.

Only Custom_0 code/inputs change. Existing source declarations, MI/particle
bytes, authored timing, geometry and lifetime-curve graph stay unchanged.
Polar topology is an explicit reconstruction: the cooked function is stripped.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
assert Path(unreal.Paths.project_dir()).resolve() == WORK
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
TASK = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
RES = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
BASE = TASK / 'MaterialVisualRepairRevision/Decal'
OUTPUT = Path(os.environ['KZ_MONSTER_VFX_DECAL_REPAIR_OUTPUT']).resolve()
assert OUTPUT.is_relative_to(BASE.resolve()) and OUTPUT != BASE.resolve()
assert not OUTPUT.exists()
OUTPUT.mkdir(parents=True)
MODE = os.environ.get('KZ_MONSTER_VFX_DECAL_REPAIR_MODE', 'probe')
assert MODE in ('probe', 'apply')
LIB = unreal.MaterialEditingLibrary
NAMES = ('M_New_Decal_Deferred_D', 'FM_Decal_Deferred_D')
PREFIX = '/Game/_Art/Effects/Shared/Materials/MonsterHuman/'
HLSL = '''// Interpreted polar adapter; original cooked graph/function topology is absent.
// 2, 1, .5 and 2*pi normalize unit UV/angle; they are mathematical constants.
float2 centered=P2*2.0-1.0;
float radius=length(centered);
// The unit disk is the mathematical domain of the centered polar adapter.
// Outside it there is no decal contribution, independently of texture wrap.
if(radius>=1.0) return float4(0.0,0.0,0.0,0.0);
float angle=atan2(centered.y,centered.x)/6.283185307179586+0.5;
float2 polar=float2(angle,radius);
// Preserve source tiling/offsets. Exact UV1 wraps back to white UV0 with a
// Wrap sampler, so clamp to the actual texture's outer texel centers.
uint width,height,awidth,aheight;
P1.GetDimensions(width,height);
P7.GetDimensions(awidth,aheight);
float2 halfTexel=0.5/float2(width,height);
float2 ahalfTexel=0.5/float2(awidth,aheight);
float2 uv=clamp(polar*P4.rg+P4.ba,halfTexel,1.0-halfTexel);
float2 auv=clamp(polar*P8.rg+P8.ba,ahalfTexel,1.0-ahalfTexel);
float4 maskSample=Texture2DSample(P1,P1Sampler,uv);
float mask=maskSample.r;
float amask=Texture2DSample(P7,P7Sampler,auv).r;
float opacity=saturate(mask*amask)*P5*P0.a;
// The generic Param vector RGB-tint interpretation is WITHDRAWN: the
// original cooked graph is stripped and does not prove that usage.
// Retain the prior project adapter imageRGB*particleColorRGB without gain;
// this neutral-color adapter is not proof of the original shader topology.
float3 color=maskSample.rgb*P0.rgb;
return float4(color,opacity);'''
REPORT = {'schema': 'Khazan.MonsterVFX.DecalMaterialVisualRepair.v1',
    'status': 'running', 'mode': MODE, 'utc': datetime.now(timezone.utc).isoformat(),
    'pid': os.getpid(), 'project': str(WORK), 'package_saves': 0,
    'main_mutations': 0, 'source_writes': 0, 'modified_own_art_count': 2,
    'new_material_nodes': 0, 'selected_assets': [], 'hlsl': HLSL,
    'allowed_changes': ['MaterialExpressionCustom_0.code', 'MaterialExpressionCustom_0.inputs'],
    'boundary': 'Source parameter values retained; centered polar UV and mask multiplication are interpreted project presentation adapters. Original cooked topology and exact original pixel parity are unconfirmed.'}


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def read(file):
    return json.loads(Path(file).read_text(encoding='utf-8-sig'))


def hash_or_none(file):
    return sha(file) if Path(file).is_file() else None


def disk(asset):
    return 'Content/' + asset.removeprefix('/Game/') + '.uasset'


def export(obj, name):
    file = OUTPUT / (name + '.t3d')
    file.parent.mkdir(parents=True, exist_ok=True)
    assert not file.exists()
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(file)
    task.exporter = unreal.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    task.replace_identical = False
    assert unreal.Exporter.run_asset_export_task(task)
    return {'path': str(file), 'sha256': sha(file)}


def graph(master):
    roots = {label: (obj.get_path_name() if obj else None) for label, prop in
        [('BaseColor', unreal.MaterialProperty.MP_BASE_COLOR),
         ('EmissiveColor', unreal.MaterialProperty.MP_EMISSIVE_COLOR),
         ('Opacity', unreal.MaterialProperty.MP_OPACITY),
         ('Normal', unreal.MaterialProperty.MP_NORMAL)]
        for obj in [LIB.get_material_property_input_node(master, prop)]}
    nodes = {}
    for obj in LIB.get_material_expressions(master):
        pins = list(LIB.get_material_expression_input_names(obj))
        values = list(LIB.get_inputs_for_material_expression(master, obj))
        assert len(pins) == len(values)
        nodes[obj.get_name()] = {'class': obj.get_class().get_name(),
            'inputs': {str(k): v.get_path_name() if v else None for k, v in zip(pins, values)}}
    return {'settings': {name: str(master.get_editor_property(name)) for name in
        ('material_domain', 'blend_mode', 'shading_model', 'two_sided', 'use_material_attributes')},
        'roots': roots, 'nodes': nodes}


def named(master, cls, parameter):
    rows = [n for n in LIB.get_material_expressions(master) if isinstance(n, cls)
            and str(n.get_editor_property('parameter_name')) == parameter]
    assert len(rows) == 1, (master.get_name(), parameter, len(rows))
    return rows[0]


def immutable_files():
    files = [TASK / 'WorkBaseline.json', TASK / 'PreparedPlaybackPlan.json',
        TASK / 'Authoring/PrivateAuthoring.json', TASK / 'Authoring/ApesCurrentMaterialBindingRevision/Applied.json',
        TASK / 'Authoring/ContentRebaseRevision.json', TASK / 'Authoring/VictimDecalPolicyRevision.json',
        TASK / 'Authoring/SharedEffectsRebaseRevision.json', TASK / 'MainRebase/PlayerPolishSourceIntake.json']
    files += [RES / name for name in ('ArtCandidateManifest.json', 'UnionAssetManifest.json',
        'FinalResourceAudit.json', 'NativeAdapterMap.json', 'ExecutionRadiusRevision.json', 'LightUsageRevision.json')]
    return {str(p): sha(p) for p in files}


try:
    art = read(RES / 'ArtCandidateManifest.json')['assets']
    assert len(art) == 457
    art_rows = {r['relative_file']: r for r in art}
    before_art = {r: sha(WORK / r) for r in art_rows}
    assert before_art == {r: x['sha256'] for r, x in art_rows.items()}, 'Original457 bytes changed before Decal author'
    REPORT['art_before_sha256'] = before_art
    REPORT['main_art_before_sha256'] = {r: hash_or_none(MAIN / r) for r in art_rows}
    REPORT['immutable_report_sha256'] = immutable_files()
    union = read(RES / 'UnionAssetManifest.json')
    protected = {disk(r['destination']) for r in union if r['source_type'] in ('ParticleSystem', 'MaterialInstanceConstant', 'Texture2D', 'StaticMesh') and r.get('task_scope') and (WORK / disk(r['destination'])).is_file()}
    protected.update(r['relative'] for r in read(TASK / 'Authoring/PrivateAuthoring.json')['mutation_journal'])
    REPORT['protected_private_before'] = {r: sha(WORK / r) for r in sorted(protected)}
    native = ('UnrealEditor-Khazan.dll', 'UnrealEditor-Khazan.pdb', 'UnrealEditor.modules')
    REPORT['native_before'] = {n: sha(WORK / 'Binaries/Win64' / n) for n in native}
    for name in NAMES:
        asset = PREFIX + name
        relative = disk(asset)
        row = art_rows[relative]
        source_row = next(r for r in union if r['destination'] == asset)
        source = MAIN / source_row['source_json']
        assert sha(source) == row['source_sha256'] == source_row['source_sha256']
        material = unreal.load_asset(asset)
        assert isinstance(material, unreal.Material)
        before_graph = graph(material)
        custom = unreal.find_object(material, 'MaterialExpressionCustom_0')
        assert isinstance(custom, unreal.MaterialExpressionCustom)
        old_inputs = list(custom.get_editor_property('inputs'))
        assert [str(x.get_editor_property('input_name')) for x in old_inputs] == ['P' + str(i) for i in range(6)]
        old_code = custom.get_editor_property('code')
        assert 'float3 color=image*float3(1,1,1)*1*pc.rgb;' in old_code
        assert 'P2*float2(1,1)' in old_code
        param = named(material, unreal.MaterialExpressionVectorParameter, 'Param')
        value = param.get_editor_property('default_value')
        assert all(abs(v - expected) < 1.e-6 for v, expected in zip((value.r,value.g,value.b,value.a), (.12,.12,.12,0.)))
        mask = named(material, unreal.MaterialExpressionTextureObjectParameter, 'MaskATex')
        mask_uv = named(material, unreal.MaterialExpressionVectorParameter, 'MaskATexUV')
        node_exports_before = {n.get_name(): export(n, name + '/NodesBefore/' + n.get_name()) for n in LIB.get_material_expressions(material)}
        backup = OUTPUT / 'Before' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WORK / relative, backup)
        assert sha(backup) == before_art[relative]
        entry = {'asset': asset, 'relative': relative, 'kind': 'OriginalArtOverride',
            'before_private_sha256': before_art[relative], 'before_main_sha256': hash_or_none(MAIN / relative),
            'backup_path': str(backup), 'backup_sha256': sha(backup),
            'source_json': str(source), 'source_sha256': sha(source), 'source_package': row['source_package'],
            'graph_before': before_graph, 'export_before': export(material, name + '/Before'),
            'node_exports_before': node_exports_before, 'code_before': old_code, 'code_after': HLSL}
        REPORT['selected_assets'].append(entry)
        if MODE == 'apply':
            proof = Path(os.environ['KZ_MONSTER_VFX_DECAL_PIXEL_PROOF']).resolve()
            assert proof.is_relative_to(TASK.resolve()) and proof.is_file()
            assert sha(proof) == os.environ['KZ_MONSTER_VFX_DECAL_PIXEL_PROOF_SHA256']
            assert os.environ.get('KZ_MONSTER_VFX_DECAL_PIXEL_OWNER_CONFIRMED') == '1', 'Root actual OnlyD00/WithoutD00 image review is required'
            REPORT['root_pixel_attribution'] = {'path': str(proof), 'sha256': sha(proof),
                'event_id': 'KZMVFX_d3f1b3f723e1c147b406fa5c', 'root_confirmed': True,
                'boundary': 'Root explicit confirmation binds actual OnlyD00/WithoutD00 image evidence; this author script does not itself inspect pixels.'}
            probe = Path(os.environ['KZ_MONSTER_VFX_DECAL_REPAIR_PROBE']).resolve()
            assert probe.is_relative_to(BASE.resolve()) and sha(probe) == os.environ['KZ_MONSTER_VFX_DECAL_REPAIR_PROBE_SHA256']
            probe_data = read(probe)
            assert probe_data['status'] == 'passed' and probe_data['mode'] == 'probe' and probe_data['package_saves'] == 0
            assert probe_data['art_before_sha256'] == before_art and probe_data['hlsl'] == HLSL
            REPORT['probe'] = {'path': str(probe), 'sha256': sha(probe)}
            material.modify()
            additions = []
            for pin in ('P6', 'P7', 'P8'):
                item = unreal.CustomInput()
                item.set_editor_property('input_name', pin)
                additions.append(item)
            custom.set_editor_property('inputs', old_inputs + additions)
            custom.set_editor_property('code', HLSL)
            for node, output, pin in [(param, 'RGBA', 'P6'), (mask, '', 'P7'), (mask_uv, 'RGBA', 'P8')]:
                assert LIB.connect_material_expressions(node, output, custom, pin)
            assert LIB.recompile_material(material) == []
            # Wait for actual compilation before saving and recording statistics.
            stats = LIB.get_statistics(material)
            entry['statistics'] = {key: int(getattr(stats,key)) for key in ('num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers')}
            assert unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
            REPORT['package_saves'] += 1
        entry['graph_after'] = graph(material)
        entry['export_after'] = export(material, name + '/After')
        entry['node_exports_after'] = {n.get_name(): export(n, name + '/NodesAfter/' + n.get_name()) for n in LIB.get_material_expressions(material)}
        assert entry['graph_after']['settings'] == before_graph['settings']
        assert entry['graph_after']['roots'] == before_graph['roots']
        assert entry['graph_after']['nodes'].keys() == before_graph['nodes'].keys()
        for node, old in before_graph['nodes'].items():
            if node != 'MaterialExpressionCustom_0':
                assert entry['graph_after']['nodes'][node] == old
                assert node_exports_before[node]['sha256'] == entry['node_exports_after'][node]['sha256'], 'Existing node declaration/default changed: ' + node
        if MODE == 'apply':
            assert custom.get_editor_property('code') == HLSL
            expected = dict(before_graph['nodes']['MaterialExpressionCustom_0']['inputs'])
            expected.update(P6=param.get_path_name(), P7=mask.get_path_name(), P8=mask_uv.get_path_name())
            assert entry['graph_after']['nodes']['MaterialExpressionCustom_0']['inputs'] == expected
        entry['after_sha256'] = sha(WORK / relative)
        entry['all_other_nodes_defaults_roots_settings_preserved'] = True
    REPORT['art_after_sha256'] = {r: sha(WORK / r) for r in art_rows}
    changed = {r for r in art_rows if REPORT['art_after_sha256'][r] != before_art[r]}
    expected_changed = {disk(PREFIX + name) for name in NAMES} if MODE == 'apply' else set()
    assert changed == expected_changed
    REPORT['protected_private_after'] = {r: sha(WORK / r) for r in sorted(protected)}
    assert REPORT['protected_private_after'] == REPORT['protected_private_before']
    REPORT['main_art_after_sha256'] = {r: hash_or_none(MAIN / r) for r in art_rows}
    assert REPORT['main_art_after_sha256'] == REPORT['main_art_before_sha256']
    REPORT['immutable_report_after_sha256'] = immutable_files()
    assert REPORT['immutable_report_after_sha256'] == REPORT['immutable_report_sha256']
    REPORT['native_after'] = {n: sha(WORK / 'Binaries/Win64' / n) for n in native}
    assert REPORT['native_after'] == REPORT['native_before']
    REPORT.update(status='passed', main_unchanged=True, original_particle_MI_timing_unchanged=True,
        all_other_455_art_unchanged=True, original_reports_immutable=True, build19_native_preserved=True)
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
finally:
    (OUTPUT / 'Repair.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('Monster VFX Decal repair ' + MODE + ': ' + REPORT['status'] + ' ' + str(OUTPUT / 'Repair.json'))
    if os.environ.get('KZ_MONSTER_VFX_DECAL_REPAIR_QUIT_OWN_PROCESS') == '1':
        unreal.SystemLibrary.quit_editor()
