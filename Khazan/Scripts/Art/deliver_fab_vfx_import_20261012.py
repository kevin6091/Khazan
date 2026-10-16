"""Copy verified native packs at their original package paths; no overwrites."""
from pathlib import Path
import json
import runpy
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_20261012'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']


def main():
    manifest = json.loads((META / 'StageManifest.json').read_text(encoding='utf-8'))
    audit = json.loads((META / 'StageDependencies.json').read_text(encoding='utf-8'))
    index = json.loads((META / 'SourcePackageIndex.json').read_text(encoding='utf-8'))
    assert audit['expected_packages'] == audit['registered_packages'] == len(manifest)
    assert not audit['errors'] and not audit['not_registered']
    for dependency in audit['missing_game_dependencies']:
        assert not index.get(dependency['package']), ('Available dependency not staged', dependency['package'])
        assert all(r['kind'] == 'soft' for r in dependency['referencers']), ('Required dependency unavailable', dependency)
    protected = {}
    for folder in ('Source', 'Config'):
        for file in sorted((ROOT / folder).rglob('*')):
            if file.is_file():
                protected[file.relative_to(ROOT).as_posix()] = SHA(file)
    protected['Khazan.uproject'] = SHA(ROOT / 'Khazan.uproject')
    if not (META / 'ProtectedBefore.json').exists():
        (META / 'ProtectedBefore.json').write_text(json.dumps(protected, indent=2) + '\n', encoding='utf-8')
    # Whole-batch preflight before any project write.
    rows = []
    for row in manifest:
        rel = row['relative_path']
        source = STAGE / 'Content' / rel
        target = ROOT / 'Content' / rel
        assert target.resolve().is_relative_to((ROOT / 'Content').resolve()), target
        assert SHA(source) == row['sha256'], source
        if target.exists():
            assert SHA(target) == row['sha256'], ('Project target conflict', target)
        rows.append(dict(row, target=str(target), existed_before=target.exists()))
    report = {'status': 'running', 'files': [], 'source_soft_reference_warnings': audit['missing_game_dependencies'], 'overwrite_count': 0, 'runtime_source_changes': 0}
    (META / 'DeliveryPlan.json').write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    for i, row in enumerate(rows):
        source = STAGE / 'Content' / row['relative_path']
        target = Path(row['target'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            # Exclusive destination creation also protects changes after preflight.
            with source.open('rb') as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            shutil.copystat(source, target)
        assert SHA(target) == row['sha256'], target
        report['files'].append(row)
        if i % 100 == 0:
            (META / 'Delivery.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    report.update(status='delivered', delivered_files=len(rows), bytes=sum(r['bytes'] for r in rows), timestamp=time.time())
    (META / 'Delivery.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('files', 'source_soft_reference_warnings')}), flush=True)


if __name__ == '__main__':
    main()
