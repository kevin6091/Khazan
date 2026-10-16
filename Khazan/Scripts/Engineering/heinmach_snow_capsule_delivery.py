"""Publish the verified capsule-only native change without replacing a loaded DLL."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT = ROOT / 'Saved/ImportReports/HeinMachSnow_20261006/PlayerCapsule_20261008'
ALIAS = 'UnrealEditor-KhazanSnowPlayerCapsule20261008.dll'
MANIFEST = 'Binaries/Win64/UnrealEditor.modules'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def source_hashes(root):
    return {p.relative_to(root).as_posix(): sha(p)
            for p in (root / 'Source').rglob('*') if p.is_file()}


def publish():
    assert not (OUT / 'Delivery.json').exists(), 'Preserve the existing delivery receipt'
    baseline = read(OUT / 'DeliveryBaseline.json')
    proof = read(OUT / 'NativeBuildProof.json')
    assert proof['success'], 'Native build and private PIE must pass first'
    current = source_hashes(ROOT)
    compiled = source_hashes(STAGE)
    assert current == compiled == proof['source'], 'Compile the latest complete Main Source'
    for path, expected in baseline['source_non_owned'].items():
        assert current[path] == expected, ('Concurrent non-owned source changed', path)
    for path, expected in baseline['protected'].items():
        assert sha(ROOT / path) == expected, ('Protected file changed', path)
    log = OUT / 'StagePIE.log'
    native_log = log.read_text(encoding='utf-8', errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in native_log
    assert 'Test Completed. Result={Fail} Name={PIE} Path={Khazan.Snow.PIE}' not in native_log
    module = STAGE / 'Binaries/Win64/UnrealEditor-Khazan.dll'
    assert sha(module) == proof['module_sha256']
    assert log.stat().st_mtime > module.stat().st_mtime, 'PIE must use this build'
    manifest = read(STAGE / MANIFEST)
    assert manifest['BuildId'] == read(ROOT / MANIFEST)['BuildId']
    target = ROOT / 'Binaries/Win64' / ALIAS
    assert not target.exists(), 'Never overwrite a previous or loaded alias'
    backup = OUT / 'Backup'
    backup.mkdir(exist_ok=True)
    shutil.copy2(ROOT / MANIFEST, backup / 'UnrealEditor.modules')
    shutil.copy2(module, target)
    pdb = module.with_suffix('.pdb')
    if pdb.exists():
        shutil.copy2(pdb, target.with_suffix('.pdb'))
    manifest['Modules']['Khazan'] = ALIAS
    temporary = (ROOT / MANIFEST).with_suffix('.capsule_pending')
    temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    os.replace(temporary, ROOT / MANIFEST)
    for path, expected in baseline['protected'].items():
        if path != MANIFEST:
            assert sha(ROOT / path) == expected, ('Protected file changed', path)
    hashes = dict(current)
    hashes.update({path: sha(ROOT / path) for path in baseline['protected']})
    hashes['Binaries/Win64/' + ALIAS] = sha(target)
    receipt = dict(success=True, module=str(target), module_sha256=sha(target), hashes=hashes,
                   source=current, map_sha256=sha(ROOT / 'Content/Maps/L_HeinMach_Environment.umap'),
                   manifest_sha256=sha(ROOT / MANIFEST), asset_changes=0,
                   normal_module_preserved=True, user_editor_untouched=True,
                   protected_editor_pid=baseline['protected_editor_pid'],
                   restart_required_for_running_editor=True, native_main_pie_verified=False,
                   utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (OUT / 'Delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('CAPSULE_NATIVE_PUBLISHED', target, receipt['module_sha256'])


if __name__ == '__main__':
    publish()
