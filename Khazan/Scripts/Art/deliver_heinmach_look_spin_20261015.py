"""CAS the three reviewed assets only; backup and rollback preserve current Main."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
main=Path(__file__).resolve().parents[2];base=main/'Metadata/HeinMachLookSpin_20261015'
prep=json.loads((base/'Preparation.json').read_text());work=Path(prep['work'])
out=base/sys.argv[1];out.mkdir(exist_ok=False)
for file in ['CandidateSaved02/Verification.json','SpinRefinedRHI05/Driver.json']:
    assert json.loads((base/file).read_text())['status']=='passed',file
review=json.loads((base/'ColourComparison01/Review.json').read_text())
assert review['status']=='review_complete' and not review['unresolved']
targets=dict(prep['targets']);targets.update(json.loads((base/'AdditionalTargets.json').read_text())['targets'])
if (base/'MapRebase.json').exists():
    assert json.loads((base/'RebasedSaved02/Verification.json').read_text())['status']=='passed'
    targets.update(json.loads((base/'MapRebase.json').read_text())['targets'])
assert len(targets)==3
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for rel,digest in prep['protected'].items():assert sha(main/rel)==digest,rel
rows=[]
for relative,digest in sorted(targets.items()):
    source,target=work/relative,main/relative
    assert source.resolve().is_relative_to(work.resolve()) and target.resolve().is_relative_to(main.resolve())
    current=sha(target) if target.exists() else None
    assert current==digest,(relative,'Current Main changed; preserve and rebase owned fields')
    rows.append(dict(file=relative,before_sha256=current,after_sha256=sha(source)))
report=dict(status='prepared',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,
            main_source_writes=0,dll_writes=0,completed=[])
def receipt():
    (out/'Receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
receipt()
try:
    for row in rows:
        target=main/row['file'];source=work/row['file'];target.parent.mkdir(parents=True,exist_ok=True)
        current=sha(target) if target.exists() else None
        assert current==row['before_sha256'],row['file']
        if target.exists():
            backup=out/'Before'/row['file'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
        temp=target.with_name(target.name+'.lookspinstage')
        shutil.copy2(source,temp);assert sha(temp)==row['after_sha256']
        temp.replace(target);report['completed'].append(row['file']);receipt()
        assert sha(target)==row['after_sha256']
    report['status']='delivered';report['sha256_matches']=3
except Exception as error:
    report['status']='rolling_back';report['error']=str(error);receipt()
    for row in reversed(rows):
        if row['file'] not in report['completed']:continue
        target=main/row['file'];assert sha(target)==row['after_sha256'],row['file']
        if row['before_sha256'] is None:target.unlink()
        else:
            temp=target.with_name(target.name+'.lookspinrollback')
            shutil.copy2(out/'Before'/row['file'],temp);temp.replace(target)
            assert sha(target)==row['before_sha256']
    report['status']='rolled_back'
finally:receipt()
assert report['status']=='delivered',report
print('LOOK_SPIN_MAIN_DELIVERED',len(rows))
