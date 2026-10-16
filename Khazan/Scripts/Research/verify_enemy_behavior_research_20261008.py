"""Audit preserved research evidence only; never load/save Unreal packages."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/EnemyBehaviorResearch_20261008'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

library = ROOT / 'Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv'
with library.open(encoding='utf-8-sig', newline='') as stream:
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    rows = [r for r in reader if r['Family'] in ('Yetuga', 'ApesStoneHandElite')]
with (OUT / 'CurrentApesYetugaLibrary.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
assert Counter(r['Family'] for r in rows) == {'Yetuga': 120, 'ApesStoneHandElite': 92}
assert len({r['CurrentAsset'] for r in rows}) == 212
assert all((ROOT / 'Content' / (r['CurrentAsset'].removeprefix('/Game/')+'.uasset')).is_file() for r in rows)

original_index = read(OUT / 'YetugaOriginal/Index.json')
assert len({r['local_path'] for r in original_index}) == len(original_index)
for r in original_index:
    assert sha(OUT / 'YetugaOriginal' / r['local_path']) == r['sha256'], r['package']
apes = read(OUT / 'ApesOriginalEvidence.json')
assert all(r['matches'] and r['actual_sha256']==r['index_sha256'] for r in apes['package_hash_checks'])

yetuga_public = read(OUT / 'PublicYetuga/manifest.json')
assert len(yetuga_public) == 27
for r in yetuga_public:
    assert sha(Path(r['file'])) == r['sha256'], r['id']
    assert Path(r['sheet']).is_file(), r['id']
apes_public = read(OUT / 'PublicApes/ArtifactSha256Manifest.json')
for r in apes_public['artifacts']:
    path = OUT / 'PublicApes' / r['path']
    assert path.is_file() and sha(path) == r['sha256'], str(path)

docs = [ROOT / 'Docs/Art/APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md',
        ROOT / 'Docs/Engineering/APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md']
local_links = []
for path in docs:
    content = path.read_text(encoding='utf-8-sig')
    assert '\ufffd' not in content
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if not target.startswith(('https://', 'http://')):
            linked = (path.parent / target.split('#')[0]).resolve()
            assert linked.is_file(), str(linked)
            local_links.append(str(linked.relative_to(ROOT)))

json_reports = sorted(OUT.glob('**/*.json'))
for path in json_reports:
    read(path)

report = {
    'date': '2026-10-08',
    'scope': 'Research-only static evidence validation; no game Source/BP/asset edits or build/PIE',
    'result': 'Passed',
    'yetuga_original_indexed_packages': len(original_index),
    'yetuga_original_sha_matches': len(original_index),
    'source_filename_collision_disambiguated': 'Moving/Reaction and Skill/13_Armageddon AC_Yetuga_DamageParry_F use Index.local_path',
    'apes_original_hash_checks': len(apes['package_hash_checks']),
    'public_yetuga_original_clips_verified': len(yetuga_public),
    'public_apes_manifest_files_verified': len(apes_public['artifacts']),
    'current_library_counts': dict(Counter(r['Family'] for r in rows)),
    'current_asset_files_present': len(rows),
    'source_current_library_sha256': sha(library),
    'derived_library_sha256': sha(OUT / 'CurrentApesYetugaLibrary.csv'),
    'parseable_json_count': len(json_reports),
    'local_doc_links_verified': local_links,
    'documents': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in docs],
    'original_patch_identification': 'Unconfirmed; original package SHA/extraction provenance preserved',
    'limits': ['Native status units/defaults/condition combination/interrupt/group reset are unverified',
               'Public visual observation used selected frames/contact sheets, not controlled runtime experiments',
               'Research completion does not imply implementation or all difficulties/current patch fidelity']
}
(OUT / 'ResearchVerification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k.endswith(('verified', 'packages', 'checks', 'counts', 'present', 'count')) or k == 'result'}, ensure_ascii=False))
