import datetime, hashlib, json, math
from pathlib import Path
r=Path(__file__).resolve().parent
def read(name): return json.loads((r/name).read_text(encoding='utf-8-sig'))
c,s,n=(read(name+'MotionVerification.json') for name in ('Candidate','SavedReload','NormalDelta'))
assert all(x['allChecksPassed'] is True for x in (c,s,n))
author=read('CenterApplied.json')
assert author['success'] and author['asset_saved'] and author['only_approved_changes_verified']
assert author['modified_center_count']==2 and author['modified_inertia_scale_count']==0 and author['modified_sparse_geometry_count']==0
stock,parts,binding=read('StockObservation.json'),read('StockSavedReadback.json'),read('StockBinding.json')
assert stock['success'] and parts['success'] and not stock['cleanupErrors']
assert stock['selectedMainSHA']==binding['selectedMainSHA']
assert all(v['samples']==150 and math.isfinite(v['speedRmsDegreesPerSecond']) for v in stock['metrics'].values())
manifest=read('CandidateManifest.json')
work=Path(binding['workRoot'])
assert len(manifest['packages'])==1
for entry in manifest['packages']:
    assert hashlib.sha256((work/entry['path']).read_bytes()).hexdigest().upper()==entry['preparedSha256']
data={
    'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'native_pie_passed':True,'native_saved_reload_passed':True,'stock_saved_reload_passed':True,
    'normal_delta_all_parts_passed':True,
    'native_saved_reload_conditions':'Fresh fixed 1/30-s NullRHI process; original colliding simulated Iron2 plus Original5 and Hair/Torso/Leg native QA.',
    'hair_motion':s['native']['hair'],
    'motion':{part:{'after':row} for part,row in s['native']['cloth'].items()},
    'only_two_capsule_centers_changed':True,'physics_source':'Assistant geometry-derived temporary repair; original-game physics unverified.',
    'native_reports':['CandidateMotionVerification.json','SavedReloadMotionVerification.json','NormalDeltaMotionVerification.json'],
    'stock_report':'StockSavedReadback.json','stock_idle_iron':'StockObservation.json',
    'stock_selected_main_base_dll_sha256':binding['selectedMainSHA'],
    'stock_limitation':binding['limitation'],
    'main_handoff_pending':True,
    'scope_limitations':['Limited idle/moving/release samples; not all animation poses or mesh triangle collision.', 'Baseline/control used earlier BP/source; final candidate also uses latest Work intake and corrected test bypass.', 'Native contact flags measured in native fixture; stock Python observes published final poses.'],
    'guard_heal':'Not repeated: game runtime Source/Config unchanged by this physics data repair.'
}
assert datetime.datetime.fromisoformat(data['utc'])>=datetime.datetime.fromisoformat(manifest['utc'])
(r/'Verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Verified native, saved reload, normal delta and stock Original5; final Main Leg handoff is pending.')
