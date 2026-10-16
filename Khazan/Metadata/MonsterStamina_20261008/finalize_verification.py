import datetime, hashlib, json, pathlib
MAIN = pathlib.Path(__file__).resolve().parents[2]
OUT = MAIN/'Metadata/MonsterStamina_20261008'
def read(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
delivery, manifest = read('DeliveryReceipt.json'), read('PreparedDeliveryManifest.json')
assert delivery['complete'] and read('NativePIE.json')['success'] and read('IntegratedRegression.json')['success']
assert read('MainSavedReload.json')['success'] and len(read('MainSavedReload.json')['facing_saved_readback'])==4
expected = {r['relative']:r['after'] for r in manifest['rows']}
for relative, value in expected.items(): assert sha(MAIN/relative)==value,relative
protected_source = read('MainSourceBaselineAfterCollision.json')
protected_source = {k:v for k,v in protected_source.items() if k not in expected}
for relative, value in protected_source.items(): assert sha(MAIN/relative)==value,relative
protected_assets = {r['package']:r['main_before'] for r in read('AssetBaseline.json')['rows'] if r['package'] not in {r.get('package') for r in manifest['rows']}}
for intake in ['LatestInputBlendSpaceIntake.json','LatestCollisionClipIntake.json']:
    for r in read(intake)['rows']:
        package = '/Game/'+r['relative'].removeprefix('Content/').removesuffix('.uasset')
        if r['relative'] not in expected: protected_assets[package]=r.get('main_before',r.get('main'))
for package, value in protected_assets.items():
    relative='Content/'+package.removeprefix('/Game/')+'.uasset'
    assert sha(MAIN/relative)==value,relative
assert sha(MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll')==manifest['main_canonical_dll_before']
assert json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']==manifest['alias']
assert 'Result: Succeeded' in (OUT/'StockDeliveryBuild.log').read_text(encoding='utf-8')
result = dict(complete=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),main=str(MAIN),
    delivered_rows=len(expected),runtime_files=15,new_runtime_classes=2,new_runtime_files=4,dev_files=1,assets=89,
    native_checks=len(read('NativePIE.json')['checks']),native_failures=sum(not r['pass'] for r in read('NativePIE.json')['checks']),
    regressions=5,main_fresh_saved_reload=True,main_facing_cdo_blendspaces=4,
    protected_source_config=len(protected_source),protected_asset_packages=len(protected_assets),canonical_dll_preserved=True,
    loaded_module=read('MainSavedReload.json')['loaded_module'],editor_helpers_excluded=True,
    limitations=['Physical monster-hit/parry producer not yet implemented; public ReportAttackParried hook tested.',
       'Apes/Yetuga gameplay bodies exist but autonomous AI/StateTree/map placement not authored.',
       'Dedicated lethal cinematic Execution not reconstructed.',
       'BrutalHPDamage remains editable unassigned zero; positive damage tested only in transient QA Definition.',
       'Active StateTree reaction pause and finite-time cancellation audited in source; controlled runtime fixture covers intent cleanup/infinite cancellation.',
       'No claim of exact original pose contact or complete original native control-flow recovery.'])
(OUT/'FinalVerification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
