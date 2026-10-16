"""Repair one private Cascade material usage flag; never run against Main.

No shader, source parameters, particle, montage or original metadata changes.
Run only after the task-owned RHI/editor processes have closed. The immutable
radius correction proof is chained through this new current-candidate proof.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import shutil
import traceback
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
MANIFEST, AUDIT, MAP = [OUT / (n + '.json') for n in ('ArtCandidateManifest', 'FinalResourceAudit', 'NativeAdapterMap')]
RADIUS = OUT / 'ExecutionRadiusRevision.json'
SUMMARY = OUT / 'NativeRestorationSummary.json'
REVISION = OUT / 'LightUsageRevision.json'
RELATIVE = 'Content/_Art/Effects/Monsters/Light/M_MonsterLightOnly.uasset'
DESTINATION = '/Game/_Art/Effects/Monsters/Light/M_MonsterLightOnly'
FILE = WORK / RELATIVE
assert FILE.resolve() == FILE and FILE.is_file()
manifest, audit, radius = read(MANIFEST), read(AUDIT), read(RADIUS)
assert len(manifest['assets']) == 457 and audit['passed'] is True
assert radius['status'] == 'passed' and len(radius['materials']) == 2
assert radius['art_candidate_manifest_sha256'] == sha(MANIFEST)
assert radius['final_resource_audit_sha256'] == sha(AUDIT)
assert not REVISION.exists(), 'One-shot revision already exists; review the archived/current chain before another repair'
candidate = next(a for a in manifest['assets'] if a['relative_file'] == RELATIVE)
assert sha(FILE) == candidate['native_sha256']
map_sha, radius_sha = sha(MAP), sha(RADIUS)
assert radius['native_adapter_map_before_sha256'] == radius['native_adapter_map_after_sha256'] == map_sha
radius_files = {m['relative_file']: sha(WORK / m['relative_file']) for m in radius['materials']}
assert all(radius_files[m['relative_file']] == m['after_sha256'] for m in radius['materials'])
effects_before = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'Content/_Art/Effects').rglob('*.uasset')}
source_before = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'Source').rglob('*') if p.is_file()}
BEFORE = OUT / 'LightUsageRevisions' / STAMP
BEFORE.mkdir(parents=True)
for p in (MANIFEST, AUDIT, MAP, RADIUS, SUMMARY, OUT / 'ImportReport.json'):
    shutil.copy2(p, BEFORE / p.name)
backup = BEFORE / RELATIVE
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(FILE, backup)
report = {'schema': 'Khazan.MonsterVFX.LightUsageRevision.v1', 'status': 'running', 'pid': os.getpid(),
    'project': str(WORK), 'archive': str(BEFORE), 'materials': [],
    'art_candidate_manifest_before_sha256': sha(MANIFEST), 'final_resource_audit_before_sha256': sha(AUDIT),
    'native_adapter_map_before_sha256': map_sha, 'execution_radius_revision_sha256': radius_sha,
    'radius_material_sha256_unchanged': radius_files,
    'trigger_evidence': {'path': str(MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt2/PrivatePIE.log'),
        'diagnostic': 'M_MonsterLightOnly missing usage flag ParticleSprites! Default Material will be used in game.'},
    'boundary': 'Engine renderer usage correction only. The original NI component-light adapter, zero-opacity shader, original numeric source values and raw-radius interpretation remain unchanged. NullRHI save/compile is not a subsequent actual RHI visual pass.'}
trigger_log = Path(report['trigger_evidence']['path'])
assert trigger_log.is_file()
report['trigger_evidence']['sha256'] = sha(trigger_log)

try:
    material = unreal.load_asset(DESTINATION)
    assert isinstance(material, unreal.Material)
    assert EAL.get_metadata_tag(material, 'KZFXNativeAdapter') == 'source-component-light-no-sprite-v1'
    expressions = LIB.get_material_expressions(material)
    assert len(expressions) == 1 and isinstance(expressions[0], unreal.MaterialExpressionConstant)
    assert expressions[0].get_editor_property('r') == 0.0
    before_topology = [(n.get_path_name(), n.get_class().get_name(), [i.get_path_name() if i else None
        for i in LIB.get_inputs_for_material_expression(material, n)]) for n in expressions]
    usage_before = bool(material.get_editor_property('used_with_particle_sprites'))
    material.modify()
    LIB.set_material_usage(material, unreal.MaterialUsage.MATUSAGE_PARTICLE_SPRITES)
    assert material.get_editor_property('used_with_particle_sprites') is True
    compile_errors = LIB.recompile_material(material)
    assert not compile_errors, compile_errors
    assert before_topology == [(n.get_path_name(), n.get_class().get_name(), [i.get_path_name() if i else None
        for i in LIB.get_inputs_for_material_expression(material, n)]) for n in LIB.get_material_expressions(material)]
    assert expressions[0].get_editor_property('r') == 0.0
    assert EAL.save_loaded_asset(material, False)
    after_sha = sha(FILE)
    candidate['native_sha256'] = candidate['sha256'] = after_sha
    effects_after = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'Content/_Art/Effects').rglob('*.uasset')}
    changed = sorted(k for k in set(effects_before) | set(effects_after) if effects_before.get(k) != effects_after.get(k))
    assert changed == [str(Path(RELATIVE))], changed
    assert source_before == {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'Source').rglob('*') if p.is_file()}
    assert sha(MAP) == map_sha and sha(RADIUS) == radius_sha
    assert all(sha(WORK / p) == h for p, h in radius_files.items())
    for a in manifest['assets']:
        assert sha(a['file']) == a['native_sha256'], a['relative_file']
    report['materials'].append({'relative_file': RELATIVE, 'destination': DESTINATION,
        'source_package': candidate['source_package'], 'source_sha256': candidate['source_sha256'],
        'before_sha256': sha(backup), 'after_sha256': after_sha,
        'usage_field': 'UMaterial.bUsedWithParticleSprites', 'usage_before': usage_before, 'usage_after': True,
        'shader_expression_topology_preserved': before_topology, 'compile_errors_nullrhi': []})
    report['all_457_candidate_hashes_checked'] = True
    report['private_effects_changed'] = changed
    report['private_other_effects_unchanged_count'] = len(effects_before) - 1
    report['private_source_unchanged_count'] = len(source_before)
    report['native_adapter_map_after_sha256'] = sha(MAP)
    manifest['light_usage_revision'] = REVISION.name
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    audit['candidate_sha_mismatch'] = []
    audit['light_usage_revision'] = {'materials': report['materials'], 'all_457_candidate_hashes_checked': True,
        'adapter_map_sha256_unchanged': map_sha, 'execution_radius_revision_sha256_unchanged': radius_sha}
    AUDIT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    report['art_candidate_manifest_sha256'] = sha(MANIFEST)
    report['final_resource_audit_sha256'] = sha(AUDIT)
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    unreal.log_error(report['error'])
finally:
    REVISION.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if report['status'] == 'passed':
        summary = read(SUMMARY)
        summary['light_usage_revision'] = {'path': str(REVISION), 'sha256': sha(REVISION)}
        for name in ('ArtCandidateManifest', 'FinalResourceAudit'):
            summary['final_reports'][name]['sha256'] = sha(OUT / (name + '.json'))
        SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('KZ_MONSTER_LIGHT_USAGE_' + report['status'].upper(), flush=True)
    assert report['status'] == 'passed', report.get('error')
