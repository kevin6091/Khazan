"""Copy exact missing dependency packages from the supplied library, without substitutes."""
from pathlib import Path
import json
import shutil
import runpy

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_20261012'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']
audit = json.loads((META / 'StageDependencies.json').read_text(encoding='utf-8'))
index = json.loads((META / 'SourcePackageIndex.json').read_text(encoding='utf-8'))
manifest = json.loads((META / 'StageManifest.json').read_text(encoding='utf-8'))
added, unavailable = [], []
for dependency in audit['missing_game_dependencies']:
    sources = index.get(dependency['package'], [])
    if not sources:
        unavailable.append(dependency)
        continue
    assert len(sources) == 1, ('Ambiguous source dependency', dependency['package'])
    source = Path(sources[0]['source'])
    rel = sources[0]['relative_path']
    checksum = SHA(source)
    target = ROOT / 'Content' / rel
    if target.exists():
        assert SHA(target) == checksum, ('Existing project conflict', target)
    staged = STAGE / 'Content' / rel
    staged.parent.mkdir(parents=True, exist_ok=True)
    if staged.exists():
        assert SHA(staged) == checksum, staged
    else:
        shutil.copy2(source, staged)
    assert SHA(staged) == checksum
    row = {'source': str(source), 'source_project': str(source.parents[len(Path(rel).parts)]), 'relative_path': rel, 'listing_id': None, 'bytes': source.stat().st_size, 'sha256': checksum, 'dependency_of': dependency['referencers']}
    if rel not in {r['relative_path'] for r in manifest}:
        manifest.append(row)
        added.append(row)
(META / 'StageManifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
n = len(list(META.glob('DependencySupplement*.json'))) + 1
(META / ('DependencySupplement%02d.json' % n)).write_text(json.dumps({'added': added, 'unavailable_in_supplied_source': unavailable}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'added_packages': len(added), 'unavailable_source_packages': [r['package'] for r in unavailable], 'total_files': len(manifest)}), flush=True)
