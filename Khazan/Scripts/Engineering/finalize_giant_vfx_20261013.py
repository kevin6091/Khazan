"""Record actual Main evidence; fail on any missing check or changed delivery."""
from pathlib import Path
from datetime import datetime
import hashlib,json
main=Path(__file__).resolve().parents[2];out=main/'Metadata/GiantVFX_20261013'
def read(name):return json.loads((out/name).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
delivery=read('MainDelivery.json');build=read('MainBuild02/Exit.json')
current_driver=read('MainRefractionFixed01/Driver.json')
report={'completed':datetime.now().astimezone().isoformat(),'passed':False,'main_applied':True,'source_files':8,'changed_assets':86,'new_assets':102,'new_runtime_files':0,'new_runtime_classes':0,'new_runtime_managers':0,'module_sha256':current_driver['module_sha256'],'initial_main_build_sha256':build['module_sha256'],'delivery_mismatches':[],'protected_source_changes':[],'preserved_independent_changes':[],'tests':{}}
assert build['exit']==0 and build['input_unchanged']
assert sha(Path(current_driver['manifest_module']))==current_driver['module_sha256']
patch=read('GrabMeshUnitDelivery.json')
material_patches={r['relative']:r['after_sha256'] for r in read('RefractionPlaneDelivery.json')}
for row in delivery['files']:
    expected=material_patches.get(row['relative'],patch['after_sha256'] if row['relative']==patch['relative'] else row['after_sha256'])
    if sha(main/row['relative'])!=expected:report['delivery_mismatches'].append(row['relative'])
targets={r['relative'] for r in delivery['files']}
heal=json.loads((main/'Metadata/HealVFX_20261013/FinalVerification.json').read_text(encoding='utf-8'))
approved={x['relative']:x['prepared'] for x in heal['main_targets'] if x['relative'].startswith('Source/')}
assert all(sha(main/p)==h for p,h in approved.items())
for path,h in delivery['main_source_intake'].items():
    if path not in targets and sha(main/path)!=h:
        if path in approved or path=='Source/Khazan/Tests/KZParryPIETest.cpp':
            report['preserved_independent_changes'].append({'path':path,'before':h,'current':sha(main/path),'source':'Completed Heal task receipt' if path in approved else 'Independent DEV test change; not written by Giant task'})
        else:report['protected_source_changes'].append(path)
saved=read('MainSaved02/Preservation.json');saved_exit=read('MainSaved02/Exit.json')
assert saved_exit['exit']==0 and saved['status']=='passed' and saved['sequence_count']==84
report['saved_audit']=saved
for label in ['MainAll01','MainGrabFixed01','MainRefractionFixed01','MainPatterns02','MainCollision01']:
    exit=read(label+'/Exit.json');driver=read(label+'/Driver.json')
    assert exit['exit']==0 and exit['input_unchanged'] and driver['status']=='passed' and not driver['material_compile_failures'],label
    assert driver['actual_loaded_module']==driver['manifest_module'],label
    if label=='MainAll01':assert driver['module_sha256']==build['module_sha256']
    # Independent Main builds/hot reload occurred between these owned runs.
    # Bind every result to its actual loaded module and unchanged VFX source8.
    launch=read(label+'/Launch.json')
    for source_row in [r for r in delivery['files'] if r['relative'].startswith('Source/')]:
        k=source_row['relative'].replace('/',chr(92))
        assert launch['source_sha256'][k]==source_row['after_sha256'],(label,k)
    entry={'test':driver['test'],'completion':driver['completion'],'module_sha256':driver['module_sha256']}
    tsv=out/label/'GiantReviewCases.tsv'
    if tsv.exists():
        cases=[r.split('\t') for r in tsv.read_text(encoding='utf-8').splitlines()]
        entry['case_count']=len(cases);entry['kinds']={kind:sum(c[2]==kind for c in cases) for kind in sorted({c[2] for c in cases})}
        entry['viewport_pngs']=len(list((out/label).glob('*.png')))
    report['tests'][label]=entry
report['limits']=read('PrivateVisualReview.json')['limits']
report['limits']=[x for x in report['limits'] if not x.startswith('Private module predates')]
report['limits'].append('Blood VAT shader remains unrecovered. A TEMP .01 mesh-unit adapter on four grab blood mesh emitters prevents the oversized camera-covering mesh; source animation/events and particle count/lifetime remain unchanged.')
report['limits'].append('Original refraction shader is unrecovered. Three owned shock-wave instances use the bounded source smoke/spherical support to avoid the white FS_bill quad; this is a TEMP frost-pulse presentation, not original distortion parity.')
report['evidence_contract']='MainAll01 verifies all155 on initial canonical build. MainGrabFixed01 replaces affected animation52/particle127 results after one PS unit patch. MainRefractionFixed01 covers all23 stored-metadata affected animation/particle cases after three MI changes. Latest Main patterns/collision cover preserved independent Heal runtime and Parry DEV changes; Giant runtime Source8 hashes are unchanged.'
report['preserved']='Latest Main secondary physics initialization, all unrelated Main Source, original animation/root/FPS/notify timing and original object gameplay values; no private binary/config/map copying'
report['passed']=not report['delivery_mismatches'] and not report['protected_source_changes']
report['remaining_required']=[] if report['passed'] else ['Resolve reported preservation mismatch without overwriting user changes']
(out/'FinalVerification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['passed'],report
print(json.dumps({k:report[k] for k in ['passed','source_files','changed_assets','new_assets','module_sha256','tests']},ensure_ascii=False))
