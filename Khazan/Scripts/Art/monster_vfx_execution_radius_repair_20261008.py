"""Private two-master correction; no Source/MI/sequence/NativeAdapterMap writes.

Raw Execution curves are not normalized opacity. Original shader units/topology
are unavailable. This explicit renderer adapter interprets positive raw values
as world-space radius in cm about source bone XYZ, with editable 10cm boundary.
Run only after task-owned editor/author/audit processes have closed.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import shutil
import unreal

MAIN = Path(__file__).resolve().parents[2]
WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == MAIN.parent.parent / 'Khazan_MonsterVFXWork_20261008/Khazan'
OUT = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
LIB = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
STAMP = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
MASTERS = ['M_EN_ApesStoneHandElite_SurfacePreview_Execution', 'M_EN_ApesStoneHandElite_EyePreview_Execution']
MANIFEST = OUT / 'ArtCandidateManifest.json'
AUDIT = OUT / 'FinalResourceAudit.json'
MAP = OUT / 'NativeAdapterMap.json'
BEFORE = OUT / 'ExecutionRadiusRevisions' / STAMP
BEFORE.mkdir(parents=True)
manifest, audit = read(MANIFEST), read(AUDIT)
assert len(manifest['assets']) == 457 and audit['passed'] is True
map_sha = sha(MAP)
source_plan = read(MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json')
curve_proofs = [{'event_id': e['event_id'], 'asset': e['asset'], 'source_package': e['source']['source_package'],
                 'source_sha256': e['source']['source_sha256'], 'source_zip': e['source'].get('source_zip'),
                 'source_zip_entry': e['source'].get('source_zip_entry'), 'source_notify_field': e['source']['field'],
                 'source_curve_name': e['state_fields']['ScalarCurveName'], 'applied_raw_curve': e['state_fields']['ScalarCurve'],
                 'units': 'Raw scalar units unconfirmed; cm-radius is renderer adapter interpretation, not direct original metadata.'}
                for e in source_plan['events'] if e.get('family') == 'ApesStoneHandElite'
                and e.get('state_fields', {}).get('ScalarParameterName') in ('Execution', 'ExecutionO')]
assert len(curve_proofs) == 3
for p in (MANIFEST, AUDIT, OUT / 'ImportReport.json', OUT / 'NativeRestorationSummary.json'):
    shutil.copy2(p, BEFORE / p.name)
report = {'schema': 'Khazan.MonsterVFX.ExecutionRadiusRevision.v1', 'status': 'running', 'pid': os.getpid(),
    'project': str(WORK), 'source_plan_sha256': sha(MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json'),
    'source_evidence_sha256': sha(MAIN / 'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/ApesExecutionMaterialEvidence.json'),
    'native_adapter_map_before_sha256': map_sha, 'archive': str(BEFORE), 'materials': [], 'raw_curve_provenance': curve_proofs,
    'supersedes': ['ImportReport material_recoveries normalized_complete_value_1_forces_zero_opacity',
                   'NativeRestorationSummary Execution normalized-complete1 opacity interpretation'],
    'boundary': 'Original scalar curves/MI defaults retained. Radius/world-cm interpretation and10cm noise boundary are explicit temporary rendering adapters; original shader units/topology unconfirmed.'}

try:
    for name in MASTERS:
        relative = 'Content/_Art/Effects/Monsters/Execution/' + name + '.uasset'
        file = WORK / relative
        assert file.resolve() == file and file.is_file()
        candidate = next(a for a in manifest['assets'] if a['relative_file'] == relative)
        assert sha(file) == candidate['native_sha256']
        backup = BEFORE / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
        material = unreal.load_asset('/Game/' + relative.removeprefix('Content/').removesuffix('.uasset'))
        assert isinstance(material, unreal.Material)
        expressions = LIB.get_material_expressions(material)
        custom_nodes = [n for n in expressions if isinstance(n, unreal.MaterialExpressionCustom)
                        and 'PreviousAlpha' in n.get_editor_property('code') and 'ExecutionO' in n.get_editor_property('code')]
        assert len(custom_nodes) == 1
        custom = custom_nodes[0]
        width_nodes = [n for n in expressions if isinstance(n, unreal.MaterialExpressionScalarParameter)
                       and str(n.get_editor_property('parameter_name')) in ('KZExecutionRadius', 'KZExecutionBoundaryWidth')]
        assert len(width_nodes) == 1
        width = width_nodes[0]
        input_names = LIB.get_material_expression_input_names(custom)
        inputs_before = [n.get_path_name() if n else None for n in LIB.get_inputs_for_material_expression(material, custom)]
        assert 'Radius' in input_names and 'PreviousAlpha' in input_names and 'DissolveTex' in input_names
        before_code = custom.get_editor_property('code')
        material.modify()
        width.set_editor_property('parameter_name', 'KZExecutionBoundaryWidth')
        width.set_editor_property('default_value', 10.0)
        code = 'float radius=max(0.0,max(Execution,ExecutionO)); if(radius<=0)return PreviousAlpha;\n'
        code += 'float width=max(Radius,0.00001); float distanceToOrigin=length(WorldPosition-Offset.rgb);\n'
        mask = 'Texture2DSample(DissolveMask,DissolveMaskSampler,UV).r' if 'DissolveMask' in input_names else '1.0'
        code += 'float mask=' + mask + '; float noise=Texture2DSample(DissolveTex,DissolveTexSampler,UV*UVScale).r;\n'
        code += 'float edgeNoise=(saturate(mask*noise)-0.5)*width;\n'
        code += 'float dissolved=smoothstep(-0.5*width,0.5*width,radius-distanceToOrigin+edgeNoise);\n'
        code += 'return PreviousAlpha*(1.0-dissolved);'
        custom.set_editor_property('code', code)
        custom.set_editor_property('description', 'Source raw Execution/O interpreted as expanding world radius; explicit10cm noisy-edge adapter, original units/topology unknown')
        assert inputs_before == [n.get_path_name() if n else None for n in LIB.get_inputs_for_material_expression(material, custom)]
        EAL.set_metadata_tag(material, 'KZFXExecutionRadiusRevision', 'source-raw-world-radius-v2')
        EAL.set_metadata_tag(material, 'KZFXRecoveryBoundary', report['boundary'])
        errors = LIB.recompile_material(material)
        assert not errors, errors
        assert EAL.save_loaded_asset(material, False)
        new_sha = sha(file)
        candidate['native_sha256'] = new_sha
        candidate['sha256'] = new_sha
        (OUT / (name + '.hlsl')).write_text(code + '\n', encoding='utf-8')
        report['materials'].append({'relative_file': relative, 'source_package': candidate['source_package'],
            'source_sha256': candidate['source_sha256'], 'before_sha256': sha(backup), 'after_sha256': new_sha,
            'before_code': before_code, 'after_code': code, 'shader_inputs_preserved': inputs_before,
            'compile_errors_nullrhi': [], 'temporary_parameter': {'name': 'KZExecutionBoundaryWidth', 'cm': 10.0,
                'reason': 'Narrow noisy transition on body scale. Assistant rendering choice, not original scalar150/20 or recovered units.'}})
    assert sha(MAP) == map_sha, 'Frozen47-adapter identity map must remain unchanged'
    for a in manifest['assets']:
        assert sha(a['file']) == a['native_sha256'], a['relative_file']
    manifest['execution_radius_revision'] = 'ExecutionRadiusRevision.json'
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    audit['candidate_sha_mismatch'] = []
    audit['execution_radius_revision'] = {'materials': report['materials'], 'adapter_map_sha256_unchanged': map_sha,
                                         'all_457_candidate_hashes_checked': True}
    AUDIT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    report['native_adapter_map_after_sha256'] = sha(MAP)
    report['art_candidate_manifest_sha256'] = sha(MANIFEST)
    report['final_resource_audit_sha256'] = sha(AUDIT)
    report['status'] = 'passed'
except Exception:
    import traceback
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    unreal.log_error(report['error'])
finally:
    path = OUT / 'ExecutionRadiusRevision.json'
    if path.exists():
        shutil.copy2(path, BEFORE / 'PriorExecutionRadiusRevision.json')
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    summary_file = OUT / 'NativeRestorationSummary.json'
    if report['status'] == 'passed':
        summary = read(summary_file)
        summary['source_numeric_contracts']['Execution'] = report['boundary']
        summary['execution_radius_revision'] = {'path': str(path), 'sha256': sha(path)}
        for name in ('ArtCandidateManifest', 'FinalResourceAudit'):
            summary['final_reports'][name]['sha256'] = sha(OUT / (name + '.json'))
        summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('KZ_MONSTER_EXECUTION_RADIUS_' + report['status'].upper(), flush=True)
    assert report['status'] == 'passed', report.get('error')
