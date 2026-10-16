"""Deliver only reviewed owned packages, with compare-and-swap and rollback."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
main=Path(__file__).resolve().parents[2];base=main/'Metadata/HeinMachColourVFX_20261015'
prep=json.loads((base/'Preparation.json').read_text(encoding='utf-8'))
work=Path(prep['work']);out=base/sys.argv[1];out.mkdir(exist_ok=False)
saved=json.loads((base/'CandidateSaved06/SavedVerification.json').read_text(encoding='utf-8'))
assert saved['status']=='passed'
expected=dict(prep['targets']);extra=json.loads((base/'FogCompleteness02/FogCompletion.json').read_text(encoding='utf-8'))
expected.update(extra['additional_targets'])
catalog=json.loads((base/'CandidateAudit03/Usage.json').read_text(encoding='utf-8'))
paths={'Content/'+row['material'].removeprefix('/Game/')+'.uasset' for row in catalog['roots'] if row['material'].startswith('/Game/')}
paths.update('Content/'+row['asset'].removeprefix('/Game/')+'.uasset' for row in catalog['definitions'])
paths.update(('Content/Maps/DevMap.umap','Content/Maps/L_HeinMach_Environment.umap','Content/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround.uasset'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
rows=[]
for rel in sorted(paths):
    target,source=main/rel,work/rel
    assert target.resolve().is_relative_to(main.resolve()) and source.resolve().is_relative_to(work.resolve()),rel
    current=sha(target);assert current==expected[rel],(rel,'current Main differs: preserve and merge owned fields first')
    rows.append({'file':rel,'before_sha256':current,'after_sha256':sha(source)})
report={'status':'prepared','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':rows,'main_source_writes':0,'dll_writes':0}
(out/'Receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
completed=[]
try:
    for row in rows:
        rel=row['file'];target=main/rel;backup=out/'Before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        assert sha(target)==row['before_sha256'],rel
        shutil.copy2(target,backup)
        temporary=target.with_name(target.name+'.heincolourstage')
        shutil.copy2(work/rel,temporary)
        assert sha(temporary)==row['after_sha256'],rel
        temporary.replace(target);completed.append(row)
        assert sha(target)==row['after_sha256'],rel
    report['status']='delivered';report['sha256_matches']=len(rows)
except Exception as error:
    report['status']='rolled_back';report['error']=str(error);report['completed_before_error']=len(completed)
    for row in reversed(completed):
        target=main/row['file'];assert sha(target)==row['after_sha256'],row['file']
        temporary=target.with_name(target.name+'.heincolourrollback')
        shutil.copy2(out/'Before'/row['file'],temporary);temporary.replace(target)
        assert sha(target)==row['before_sha256'],row['file']
finally:
    (out/'Receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['status']=='delivered',report
print('HEIN_COLOUR_DELIVERED',len(rows))
