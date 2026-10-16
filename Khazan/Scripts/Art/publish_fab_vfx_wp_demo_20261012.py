"""Publish only the natively repaired demo map and its external packages."""
from pathlib import Path
import json
import runpy
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']
MAP = 'VFX/05_CursedMagic/Demo/Cursed_Magic.umap'
PREFIXES = ('__ExternalActors__/VFX/05_CursedMagic/Demo/Cursed_Magic/', '__ExternalObjects__/VFX/05_CursedMagic/Demo/Cursed_Magic/')


def affected(rel):
    return rel == MAP or rel.startswith(PREFIXES)


def main():
    audit = json.loads((META / 'StageWPDemoAudit.json').read_text())
    assert audit['status'] == 'passed' and audit['authored_actor_values_equal']
    assert json.loads((META / 'WPStageAudit05/Exit.json').read_text())['exit_code'] == 0
    receipt = json.loads((META / 'PublishReceipt.json').read_text())
    assert receipt['status'] == 'published' and 'wp_supplement' not in receipt
    before = [r for r in receipt['files'] if affected(r['relative_path'])]
    before_by_path = {r['relative_path']: r for r in before}
    output_files = [STAGE / 'Content' / MAP]
    for prefix in PREFIXES:
        output_files += sorted((STAGE / 'Content' / prefix).rglob('*.uasset'))
    assert len(output_files) == 1 + audit['__ExternalActors___files'] + audit['__ExternalObjects___files']
    outputs = []
    for source in output_files:
        assert source.resolve().is_relative_to((STAGE / 'Content').resolve())
        rel = source.relative_to(STAGE / 'Content').as_posix()
        target = ROOT / 'Content' / rel
        assert target.resolve().is_relative_to((ROOT / 'Content').resolve())
        if target.exists():
            assert rel in before_by_path and SHA(target) == before_by_path[rel]['sha256'], target
        outputs.append({'source': str(source), 'relative_path': rel, 'sha256': SHA(source), 'bytes': source.stat().st_size, 'target': str(target)})
    for row in before:
        assert SHA(Path(row['target'])) == row['sha256'], row['target']
        backup = META / 'WPBeforeMain/Content' / row['relative_path']
        assert backup.resolve().is_relative_to((META / 'WPBeforeMain').resolve())
        assert not backup.exists(), backup
    assert not (META / 'PublishReceiptBeforeWP.json').exists()
    (META / 'PublishReceiptBeforeWP.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    archives = []
    for row in before:
        target = Path(row['target'])
        backup = META / 'WPBeforeMain/Content' / row['relative_path']
        backup.parent.mkdir(parents=True, exist_ok=True)
        # Every previous task-owned map/external package stays recoverable.
        shutil.move(str(target), str(backup))
        assert SHA(backup) == row['sha256'], backup
        archives.append({'archive': str(backup), 'sha256': row['sha256'], 'old_target': row['target']})
    for row in outputs:
        source, target = Path(row['source']), Path(row['target'])
        target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists(), target
        shutil.copy2(source, target)
        assert SHA(target) == row['sha256'], target
    receipt['files'] = sorted([r for r in receipt['files'] if not affected(r['relative_path'])] + outputs, key=lambda r: r['relative_path'])
    receipt['wp_supplement'] = {'status': 'published', 'timestamp': time.time(), 'files': len(outputs), 'actors': audit['actors'], 'external_objects': audit['__ExternalObjects___files'], 'previous_task_files_archived': archives, 'authored_actor_values_equal': True, 'stage_audit_run': 'WPStageAudit05', 'native_builder_run': 'WPBuilder02', 'material_package_writes': 0}
    receipt.update(files_count=len(receipt['files']), bytes=sum(r['bytes'] for r in receipt['files']))
    (META / 'PublishReceipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'files': receipt['files_count'], 'wp_files': len(outputs), 'actors': audit['actors'], 'bytes': receipt['bytes']}), flush=True)


if __name__ == '__main__':
    main()
