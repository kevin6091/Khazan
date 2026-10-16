"""Prepare only matched packs in a neutral UE 5.8 staging project."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_20261012'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    mappings = json.loads((META / 'ListingMap.json').read_text(encoding='utf-8'))
    selected = []
    for pack in mappings:
        if pack['status'] != 'matched_local':
            continue
        content = Path(pack['source_project']) / 'Content'
        roots = [Path(pack['source_content_root'])]
        # World Partition demo actors/objects have a separate package tree.
        name = pack['target_package_root'].split('/')[-1]
        for extra in ('__ExternalActors__', '__ExternalObjects__'):
            folder = content / extra / name
            if folder.is_dir():
                roots.append(folder)
        for folder in roots:
            for file in sorted(folder.rglob('*')):
                if file.is_file():
                    rel = file.relative_to(content).as_posix()
                    selected.append({'source': str(file), 'source_project': pack['source_project'], 'relative_path': rel, 'listing_id': pack['listing_id'], 'bytes': file.stat().st_size, 'sha256': sha(file)})
    assert selected and len({r['relative_path'] for r in selected}) == len(selected)
    conflicts = []
    existing = []
    for row in selected:
        target = ROOT / 'Content' / row['relative_path']
        if target.exists():
            same = sha(target) == row['sha256']
            existing.append({'path': str(target), 'identical': same})
            if not same:
                conflicts.append(str(target))
    (META / 'Preflight.json').write_text(json.dumps({'selected_files': len(selected), 'selected_bytes': sum(r['bytes'] for r in selected), 'existing_targets': existing, 'conflicts': conflicts, 'overwrite_existing': False}, indent=2) + '\n', encoding='utf-8')
    assert not conflicts, conflicts
    STAGE.mkdir(parents=True, exist_ok=True)
    project = {'FileVersion': 3, 'EngineAssociation': '5.8', 'Plugins': [{'Name': p, 'Enabled': True} for p in ('PythonScriptPlugin', 'EditorScriptingUtilities', 'Niagara')]}
    (STAGE / 'FabVFXImport.uproject').write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8')
    for row in selected:
        target = STAGE / 'Content' / row['relative_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert sha(target) == row['sha256'], target
        else:
            shutil.copy2(row['source'], target)
        assert sha(target) == row['sha256']
    (META / 'StageManifest.json').write_text(json.dumps(selected, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'staged', 'files': len(selected), 'bytes': sum(r['bytes'] for r in selected), 'stage': str(STAGE), 'target_conflicts': 0}), flush=True)


if __name__ == '__main__':
    main()
