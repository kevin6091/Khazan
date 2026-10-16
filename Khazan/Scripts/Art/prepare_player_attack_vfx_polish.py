"""Reuse the writable private VFX project and preserve the latest Main baseline."""
from pathlib import Path
import ctypes
import datetime
import hashlib
import json
import os
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008'
folders = ('Source', 'Config', 'Content/_Art/Effects', 'Content/_Art/Player/Animation/InGame/DAS')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inventory = lambda root, folder: {p.relative_to(root).as_posix(): sha(p) for p in (root / folder).rglob('*') if p.is_file()}
for folder in folders:
    target = WORK / folder
    assert target.is_dir() and target.resolve().is_relative_to(WORK.resolve())
    assert not target.stat().st_file_attributes & 0x400, 'Private writable target must not be a junction'
OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT / 'PrivateReady.json').exists(), 'Do not overwrite a started polish baseline'
baseline = {folder: inventory(MAIN, folder) for folder in folders}
baseline['uproject'] = {'Khazan.uproject': sha(MAIN / 'Khazan.uproject')}
baseline['native'] = inventory(MAIN, 'Binaries/Win64')
before = {folder: inventory(WORK, folder) for folder in folders}
changes = []
for folder in folders:
    extra = set(before[folder]) - set(baseline[folder])
    assert not extra, 'Unexpected private-only product files: ' + repr(sorted(extra))
    for relative, digest in baseline[folder].items():
        source, target = MAIN / relative, WORK / relative
        if before[folder].get(relative) != digest:
            assert sha(source) == digest
            if target.exists():
                backup = OUT / 'PrivateBeforeSync' / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                assert not backup.exists()
                shutil.copy2(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if folder == 'Source': os.utime(target, None)
            assert sha(target) == digest
            changes.append(dict(file=relative, before=before[folder].get(relative), after=digest))
for folder in folders:
    assert inventory(MAIN, folder) == baseline[folder], 'Main changed during read-only intake'
    assert inventory(WORK, folder) == baseline[folder], 'Private intake is incomplete'
assert sha(MAIN / 'Khazan.uproject') == baseline['uproject']['Khazan.uproject']
assert inventory(MAIN, 'Binaries/Win64') == baseline['native']
for relative, digest in baseline['Source'].items():
    backup = OUT / 'MainSourceBefore' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAIN / relative, backup)
    assert sha(backup) == digest
record = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='PrivateReady',
    main=str(MAIN), work=str(WORK), baseline=baseline, source_count=len(baseline['Source']),
    private_sync_changes=changes, Main_product_writes=0, old_task_reports_preserved=True,
    writable_targets=list(folders), read_only_Content_junctions='Never save shared Content/Data/Maps/Monsters or other junctions',
    latest_BrutalHPDamage_policy='User changed six Main definitions to total HP50 at19:48 KST; shared junctions read current values, do not restore old0 receipts.')
(OUT / 'PrivateReady.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(status=record['status'], source_count=record['source_count'], synced_files=len(changes))))
