"""Publish the verified shallow library and archive only unchanged prior task packages."""
from pathlib import Path
import json
import runpy
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']


def main():
    audit = json.loads((META / 'StageOrganizedAudit.json').read_text())
    assert audit['status'] == 'passed', 'Fresh staging audit must pass before Main publication'
    assert json.loads((META / 'MainOwnership.json').read_text())['outside_referencers'] == []
    manifest = json.loads((META / 'InputManifest.json').read_text())
    prior = [r for r in manifest if r['prior_main']]
    outputs = []
    for file in sorted((STAGE / 'Content').rglob('*')):
        if not file.is_file() or file.suffix.lower() not in ('.uasset', '.umap', '.ubulk', '.uexp', '.uptnl'):
            continue
        rel = file.relative_to(STAGE / 'Content').as_posix()
        if rel.startswith(('VFX/', '__ExternalActors__/VFX/', '__ExternalObjects__/VFX/')):
            outputs.append({'source': str(file), 'relative_path': rel, 'sha256': SHA(file), 'bytes': file.stat().st_size})
    assert outputs and sum(r['relative_path'].startswith('VFX/') for r in outputs) >= audit['processed']
    # No directory moves or deletes. Every file's resolved paths and hashes are
    # checked before copying or moving it inside this workspace.
    for row in prior:
        file = ROOT / 'Content' / row['relative_path']
        assert file.resolve().is_relative_to((ROOT / 'Content').resolve()), file
        retired = META / 'Retired/Content' / row['relative_path']
        assert retired.resolve().is_relative_to((META / 'Retired').resolve()), retired
        if file.exists():
            assert SHA(file) == row['sha256'], ('Main changed during preparation', file)
        else:
            assert retired.exists() and SHA(retired) == row['sha256'], file
    for row in outputs:
        target = ROOT / 'Content' / row['relative_path']
        assert target.resolve().is_relative_to((ROOT / 'Content').resolve()), target
        if target.exists():
            assert SHA(target) == row['sha256'], ('New namespace conflict', target)
    (META / 'PublishPlan.json').write_text(json.dumps(outputs, indent=2), encoding='utf-8')
    receipt = {'status': 'running', 'files': [], 'retired': [], 'source_config_writes': 0, 'foreign_asset_writes': 0}
    for index, row in enumerate(outputs):
        source = Path(row['source'])
        target = ROOT / 'Content' / row['relative_path']
        assert source.resolve().is_relative_to((STAGE / 'Content').resolve()), source
        assert target.resolve().is_relative_to((ROOT / 'Content').resolve()), target
        assert source.drive.lower() == target.drive.lower(), 'Publication must stay on one volume'
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            # Preserve all bytes and avoid another full-size copy under disk
            # pressure. The supplied source packs and Before backup remain.
            shutil.move(str(source), str(target))
        assert SHA(target) == row['sha256'], target
        receipt['files'].append(dict(row, target=str(target)))
        if index % 100 == 0:
            (META / 'PublishReceipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    for row in prior:
        source = ROOT / 'Content' / row['relative_path']
        retired = META / 'Retired/Content' / row['relative_path']
        retired.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            assert not retired.exists(), retired
            shutil.move(str(source), str(retired))
        assert SHA(retired) == row['sha256'], retired
        receipt['retired'].append({'old': str(source), 'archive': str(retired), 'sha256': row['sha256']})
    receipt.update(status='published', timestamp=time.time(), files_count=len(outputs), retired_count=len(prior), bytes=sum(r['bytes'] for r in outputs), same_volume_move=True)
    (META / 'PublishReceipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('files','retired')}), flush=True)


if __name__ == '__main__':
    main()
