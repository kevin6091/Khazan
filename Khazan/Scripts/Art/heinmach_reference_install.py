"""Install only the verified HeinMach packages, preserving concurrent user edits."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'Saved/ArtStaging/HeinMachReference_20261006'
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
QA=STAGE/'Saved/ImportReports/HeinMachReference_20261006'
BACKUP=ROOT/'Saved/ArtBackups/HeinMachReference_20261006'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    setup=json.loads((OUT/'StageSetup.json').read_text())
    applied=json.loads((QA/'AppliedTrial.json').read_text())
    audit=json.loads((QA/'FreshSavedSceneAudit.json').read_text())
    assert audit['passed'] and audit['all_actor_poses_preserved']
    for kind in ('compile','capture','motion','performance','audit'):
        assert json.loads((OUT/(kind+'Process.json')).read_text())['passed'],kind
    packages=['Content/Maps/L_HeinMach_Environment.umap']
    for asset in applied['modified_assets']:
        packages.append('Content/'+asset.removeprefix('/Game/').split('.')[0]+'.uasset')
    packages=sorted(set(packages))
    assert len(packages)==12,len(packages)
    assert all('__HeinMachQA' not in name for name in packages)
    baseline={item['path'].replace('\\','/'):item['sha256'] for item in setup['baseline_packages']}
    # No other copied package may have been edited by this task.
    unexpected=[name for name,digest in baseline.items() if name not in packages and sha(STAGE/name)!=digest]
    assert not unexpected,unexpected
    rows=[]
    for name in packages:
        source=STAGE/name;target=ROOT/name
        assert source.is_file() and source.resolve().is_relative_to(STAGE)
        if name in baseline:
            assert target.is_file() and sha(target)==baseline[name],('Concurrent main edit; rebase required',name)
            # Read/write open checks Windows sharing without changing any bytes.
            with target.open('r+b'):pass
        else:
            assert not target.exists(),('New target already exists; do not replace',name)
        rows.append({'path':name,'before':baseline.get(name),'after':sha(source)})
    result={'status':'Prepared','packages':rows,'backup':str(BACKUP),
            'QA_assets_installed':False,'user_editor_modified':False,
            'other_copied_packages_unchanged':len(baseline)-sum(n in baseline for n in packages)}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'InstallManifest.json').write_text(json.dumps(result,indent=2)+'\n')
    if sys.argv[1]=='prepare':
        print(json.dumps({'status':'Prepared','packages':len(rows),'all_current_main_hashes_match':True}));return
    assert sys.argv[1]=='apply'
    # Back up every selected original before the first mutation.
    for row in rows:
        if not row['before']:continue
        dest=BACKUP/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert sha(dest)==row['before']
        else:shutil.copy2(ROOT/row['path'],dest)
        assert sha(dest)==row['before']
    installed=[]
    try:
        for row in rows:
            dest=ROOT/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            temp=dest.with_name(dest.name+'.HeinMachReference.tmp')
            assert not temp.exists()
            shutil.copy2(STAGE/row['path'],temp)
            assert sha(temp)==row['after']
            os.replace(temp,dest)
            installed.append(row)
            assert sha(dest)==row['after']
    except Exception:
        # Restore only packages already replaced by this task.
        for row in reversed(installed):
            dest=ROOT/row['path']
            if row['before']:shutil.copy2(BACKUP/row['path'],dest)
            else:dest.unlink()
        raise
    for name in ('BaselineProbe.json','AppliedTrial.json','FreshSavedSceneAudit.json','ShaderVerification.json','PerformanceCapture.json'):
        shutil.copy2(QA/name,OUT/name)
    result.update(status='Applied',timestamp=datetime.datetime.now().astimezone().isoformat(),
                  main_map_sha256=sha(ROOT/'Content/Maps/L_HeinMach_Environment.umap'))
    (OUT/'InstallManifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'Applied','packages':len(rows),'backup':str(BACKUP),'poses_preserved':True}))


if __name__=='__main__':main()
