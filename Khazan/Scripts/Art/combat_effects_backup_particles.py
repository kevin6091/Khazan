"""Back up only extraction-owned particle assets before fixing cooked editor graphs."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
allowed = (ROOT / 'Content/_Art/Effects').resolve()
out = ROOT / 'Saved/ArtBackups/CombatEffects_20261006/Cascade_before_editor_distribution_repair'
rows = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
report = []
for row in rows:
    if row['source_type'] != 'ParticleSystem':
        continue
    assert row['destination'].startswith('/Game/_Art/Effects/')
    path = (ROOT / 'Content' / (row['destination'][len('/Game/'):] + '.uasset')).resolve()
    assert path.is_relative_to(allowed), path
    if not path.exists():
        continue
    raw = path.read_bytes()
    assert b'KZFXSourcePackage' in raw and row['source_package'].encode('ascii') in raw, path
    backup = out / path.relative_to(allowed)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        assert backup.read_bytes() == raw, ('Backup differs; do not replace it', backup)
    else:
        shutil.copy2(path, backup)
    entry = {'asset': row['destination'], 'source_package': row['source_package'],
             'original_file': str(path), 'backup_file': str(backup),
             'sha256': hashlib.sha256(raw).hexdigest(), 'removed_for_reimport': '--apply' in sys.argv}
    report.append(entry)
    if '--apply' in sys.argv:
        path.unlink()
out.mkdir(parents=True, exist_ok=True)
(out / 'BackupManifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'backup_count': len(report), 'applied': '--apply' in sys.argv, 'report': str(out / 'BackupManifest.json')}))
