"""Fill exact staged dependencies, using targeted source lookups only."""
from pathlib import Path
import json
import runpy
import shutil

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012'
SOURCE = Path('C:/Users/user/Desktop/VFX/Assets/Content')
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']
audit = json.loads((META / 'InputRegistry.json').read_text())
manifest = json.loads((META / 'InputManifest.json').read_text())
oldindex = json.loads((META.parent / 'SourcePackageIndex.json').read_text())
added, missing = [], []
for dependency in audit['missing']:
    rel = dependency['package'].removeprefix('/Game/')
    candidates = [SOURCE / (rel + ext) for ext in ('.uasset', '.umap')]
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        candidates = [Path(r['source']) for r in oldindex.get(dependency['package'], [])]
    if not candidates:
        # Existing project content is used only when the exact package is needed.
        candidates = [ROOT / 'Content' / (rel + ext) for ext in ('.uasset', '.umap') if (ROOT / 'Content' / (rel + ext)).is_file()]
    if not candidates:
        missing.append(dependency)
        continue
    assert len(candidates) == 1, ('Ambiguous exact dependency', dependency['package'])
    source = candidates[0]
    relative = rel + source.suffix
    checksum = SHA(source)
    target = STAGE / 'Content' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert SHA(target) == checksum
    else:
        shutil.copy2(source, target)
    row = {'source': str(source), 'relative_path': relative, 'sha256': checksum, 'bytes': source.stat().st_size, 'prior_main': source.is_relative_to(ROOT / 'Content'), 'listing_id': None, 'dependency_of': dependency['referencers']}
    assert relative not in {r['relative_path'] for r in manifest}
    manifest.append(row)
    added.append(row)
    if row['prior_main']:
        backup = META / 'Before/Content' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup)
(META / 'InputManifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
number = len(list(META.glob('Supplement*.json'))) + 1
(META / ('Supplement%02d.json' % number)).write_text(json.dumps({'added': added, 'unavailable': missing}, indent=2), encoding='utf-8')
print(json.dumps({'added': len(added), 'missing': [{'package': r['package'], 'kinds': list(set(x['kind'] for x in r['referencers']))} for r in missing], 'total': len(manifest)}), flush=True)
