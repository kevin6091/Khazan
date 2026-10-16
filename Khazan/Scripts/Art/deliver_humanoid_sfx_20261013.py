"""Guarded atomic scoped delivery; leave locks and newer edits untouched."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/HumanoidSFX_20261013'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
stage=read(OUT/'Stage01.json');WORK=Path(stage['project'])
assert read(OUT/'SavedStage04/SavedAudit.json')['success'],'Fresh prepared asset audit must pass first.'
name=sys.argv[1];directory=OUT/name;directory.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'complete':False,'applied':[],'already_applied':[],'locked':[],'conflicts':[],'errors':[]}
for row in stage['isolated']:
    target=ROOT/row['relative'];source=WORK/row['relative']
    assert target.resolve().is_relative_to((ROOT/'Content').resolve()),str(target)
    assert source.resolve().is_relative_to((WORK/'Content').resolve()),str(source)
    desired=sha(source);current=sha(target)
    if current==desired:report['already_applied'].append(dict(row,sha256=desired));continue
    if current!=row['baseline_sha256']:
        report['conflicts'].append(dict(row,current_sha256=current,desired_sha256=desired));continue
    pending=target.with_name(target.name+'.HumanoidSFX.pending')
    try:
        shutil.copy2(source,pending)
        # Recheck after preparing the exact bytes to guard concurrent edits.
        if sha(target)!=row['baseline_sha256']:
            report['conflicts'].append(dict(row,reason='Changed during atomic preparation'));continue
        os.replace(pending,target)
        assert sha(target)==desired
        report['applied'].append(dict(row,sha256=desired))
    except PermissionError as e:report['locked'].append(dict(row,reason=str(e)))
    except Exception as e:report['errors'].append(dict(row,reason=str(e)))
    finally:
        if pending.exists():pending.unlink()
report['complete']=not report['locked'] and not report['conflicts'] and not report['errors']
(directory/'Delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print({k:len(v) if isinstance(v,list) else v for k,v in report.items()})
