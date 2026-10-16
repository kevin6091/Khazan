"""Verify delivered native files, source archives and task-owned backups."""
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
BASE = ROOT / 'Saved/Extracted/CombatEffects_20261006'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

rows = read(META / 'AssetManifest.json')
audit = read(META / 'FreshSavedAssetAudit.json')
shader = read(META / 'ShaderVerification.json')
preview = read(META / 'RepresentativeEffectRendering.json')
assert audit['status'] == shader['status'] == preview['status'] == 'passed'
assert audit['native_total'] == 2028 and len(audit['assets']) == 2028
assert audit['distribution_checks'] == 80874 and audit['curve_key_checks'] == 117
assert not audit['distribution_shape_changes']
expected_native = set()
for item in audit['assets']:
    file = ROOT / 'Content' / (item['asset'][len('/Game/'):] + '.uasset')
    assert sha(file) == item['file_sha256'], file
    expected_native.add(file.resolve())
actual_native = {p.resolve() for p in (ROOT / 'Content/_Art/Effects').rglob('*.uasset')}
assert actual_native == expected_native, ('Unexpected native files', actual_native ^ expected_native)
for row in rows:
    assert sha(ROOT / row['source_json']) == row['source_sha256'], row['source_package']
    copy = META / 'Source' / (row['source_package'] + '.json')
    assert copy.exists() and sha(copy) == row['source_sha256'], copy
    if row['source_type'] in ('MaterialFunction', 'NiagaraSystem'):
        assert not (ROOT / 'Content' / (row['destination'][len('/Game/'):] + '.uasset')).exists(), row['name']
archive_counts = {}
for name, expected in [('OriginalRaw', 2313), ('OriginalBindingRaw', 733), ('Payload', 600)]:
    report = read(BASE / name / 'ExportReport.json')
    assert len(report) == expected and all(r['Success'] for r in report), name
    files = [Path(p) for r in report for p in r['DiskFilePaths']]
    assert all(p.is_file() and p.stat().st_size > 0 for p in files), name
    archive_counts[name] = {'packages': expected, 'files': len(files), 'failures': 0}
backup_count = 0
for name in ('Import_numericprobe', 'Import_numeric', 'Import_numericdata'):
    for item in read(META / (name + '.json')).get('backups', []):
        assert sha(Path(item['backup'])) == (item.get('backup_sha256') or item.get('sha256')), item['backup']
        backup_count += 1
cleanup = read(META / 'ObsoleteTextureCleanup.json')
assert cleanup['status'] == 'passed' and len(cleanup['assets']) == 3
for item in cleanup['assets']:
    assert sha(Path(item['backup'])) == item['sha256'], item['backup']
    assert not (ROOT / 'Content' / (item['obsolete'][len('/Game/'):] + '.uasset')).exists()
images = [Path(c['image']) for effect in preview['effects'] for c in effect['captures']]
assert len(preview['effects']) == 9 and len(images) == 45 and all(p.is_file() for p in images)
scripts = [p for p in (ROOT / 'Scripts/Art').glob('combat_effects_*.py')]
scripts += [ROOT / 'Scripts/Art/prepare_combat_effects.py', ROOT / 'Scripts/Art/run_combat_effects_background.py']
for file in scripts:
    compile(file.read_text(encoding='utf-8'), str(file), 'exec')
report = {'status': 'passed', 'native_total': 2028, 'native_counts': audit['native_counts'],
          'source_packages': len(rows), 'source_only_counts': dict(Counter(r['source_type'] for r in rows if r['source_type'] in ('NiagaraSystem', 'MaterialFunction'))),
          'archives': archive_counts, 'source_sha_checks': len(rows), 'native_sha_checks': len(expected_native),
          'distribution_table_checks': audit['distribution_checks'],
          'protected_gpu_fields_unreadable': len(audit['distribution_read_errors']),
          'color_curve_key_checks': audit['curve_key_checks'],
          'representative_runtime_effects': 9, 'inspection_PNGs': len(images),
          'backup_checks': backup_count, 'obsolete_owned_textures_removed': 3,
          'script_syntax_checks': len(scripts),
          'boundary': 'Native import and representative standalone rendering verified. Original shader topology, 21 Niagara systems, runtime owner parameters, weapon attachments, combat/surface event hookups and original appearance equivalence remain incomplete or unverified.',
          'user_editor_controlled': False, 'gameplay_or_existing_map_changes': False}
(META / 'DeliveryVerification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report), flush=True)
