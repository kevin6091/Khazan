"""Read-only original Yetuga design metadata inspection; never edits game assets."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import zipfile

ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
SOURCE = ROOT / 'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911'
OUT = ROOT / 'Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal'
OUT.mkdir(parents=True, exist_ok=True)
index = json.loads((SOURCE / 'SourceMetadataIndex.json').read_text(encoding='utf-8-sig'))
selected = [p for p in index if '/Design/Monster/Boss/01_Yetuga/' in p]
basename_counts = Counter(p.split('/')[-1] for p in selected)
records = []
with zipfile.ZipFile(SOURCE / 'SourceMetadata.zip') as archive:
    names = set(archive.namelist())
    for package in selected:
        candidates = [n for n in names if n.endswith(package + '.json') or n == package + '.json']
        if not candidates:
            candidates = [n for n in names if n.endswith('/' + package.split('/')[-1] + '.json')]
        assert len(candidates) == 1, (package, candidates)
        entry = candidates[0]
        raw = archive.read(entry)
        assert hashlib.sha256(raw).hexdigest() == index[package]['sha256'], package
        exports = json.loads(raw.decode('utf-8-sig'))
        basename = package.split('/')[-1]
        if basename_counts[basename] > 1:
            suffix = package.split('/Design/Monster/Boss/01_Yetuga/', 1)[1]
            local_path = 'PackageCopies/' + suffix + '.json'
        else:
            local_path = basename + '.json'
        destination = OUT / local_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        records.append(dict(package=package, zip_entry=entry, local_path=local_path, sha256=index[package]['sha256'],
                            exports=[dict(name=e.get('Name'), type=e.get('Type'),
                                          property_keys=list(e.get('Properties', {}))) for e in exports]))
(OUT / 'Index.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
print('Selected original design packages:', len(records))
print('Duplicate basenames stored by full package suffix:',
      [name for name, count in basename_counts.items() if count > 1])
