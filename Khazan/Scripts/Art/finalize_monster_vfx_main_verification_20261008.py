"""Read-only final checks after guarded delivery and fresh Main validation."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import runpy

MAIN = Path(__file__).resolve().parents[2]
OUT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
evidence = {}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def record(name, path):
    path = Path(path).resolve()
    evidence[name] = {'path': str(path), 'sha256': sha(path)}
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.suffix == '.json' else None

H = runpy.run_path(str(MAIN / 'Scripts/Art/deliver_monster_vfx_main_20261008.py'))
prepared = record('PreparedDelivery', OUT / 'MainDelivery/Prepared.json')
delivery = record('Delivered', OUT / 'MainDelivery/Delivered.json')
assert delivery['status'] == 'SourceContentAndNativeAliasDelivered'
adapter_supplement = None
supplement_file = OUT / 'MainDelivery/AdapterSupplement/SupplementalDelivered.json'
verification_prepared = prepared
if supplement_file.exists():
    S = runpy.run_path(str(MAIN / 'Scripts/Art/supplement_monster_vfx_adapter_dependencies_20261011.py'))
    verification_prepared, supplement_file, adapter_supplement = S['verification_view'](prepared)
    record('AdapterSupplementHelper', MAIN / 'Scripts/Art/supplement_monster_vfx_adapter_dependencies_20261011.py')
    record('AdapterSupplementDelivered', supplement_file)
    record('AdapterSupplementPrepared', supplement_file.parent / 'Prepared.json')
    record('InitialMainFailureArchive', adapter_supplement['failure_archive']['path'])
    helper_revision = record('AdapterSupplementHelperRevision', OUT / 'MainDelivery/AdapterSupplement/HelperRevision/ToolRevision.json')
    assert helper_revision['finalizer_after_sha256'] == sha(__file__)
    assert helper_revision['supplement_helper_sha256'] == evidence['AdapterSupplementHelper']['sha256']
    assert helper_revision['unchanged_deliver_helper_sha256'] == prepared['helper_sha256']
H['check'](verification_prepared, delivered=True)
material_revision=H['visual_material_repair_revision'](delivered=True)
assert len(delivery['files']) == (968 if material_revision else 967)
candidate = record('PrivateCandidateIntegrity', OUT / 'NativeCandidateIntegrity.json')
assert candidate['status'] == 'passed'
saved = record('MainSavedReadback', OUT / 'Authoring/MainSavedReadback.json')
assert saved['status'] == 'passed' and saved['all_checks_passed']
assert saved['all_selected_bytes_unchanged'] and saved['asset_saves'] == saved['asset_mutations'] == 0
assert Path(saved['project']).resolve() == MAIN
assert len(saved['events']) == 3342 and len(saved['sequences']) == 487 and len(saved['death_presentations']) == 6
assert saved['plan_sha256'] == sha(OUT / 'PreparedPlaybackPlan.json')
if adapter_supplement:
    assert (OUT / 'Authoring/MainSavedReadback.json').stat().st_mtime >= supplement_file.stat().st_mtime
    saved_attempt = Path(record('MainSavedLatest', OUT / 'Processes/Main_monster_vfx_saved_audit_20261008/Latest.json')['attempt']).resolve()
    assert saved_attempt.is_relative_to((OUT / 'Processes/Main_monster_vfx_saved_audit_20261008').resolve())
    assert (saved_attempt / 'Launch.json').stat().st_mtime >= supplement_file.stat().st_mtime
    record('MainSavedLaunch', saved_attempt / 'Launch.json')
    assert record('MainSavedExit', saved_attempt / 'Exit.json')['exit_code'] == 0
shared=H['shared_effects_rebase_revision'](delivered=True)
H['verify_saved_shared_revision'](shared,saved)
H['verify_saved_visual_revision'](material_revision,saved)
if material_revision:
    record('VisualMaterialRepairRevision',material_revision['file'])
    assert candidate.get('visual_material_repair_revision_sha256')==material_revision['sha256']
    assert delivery.get('visual_material_repair_revision_sha256')==prepared.get('visual_material_repair_revision_sha256')==material_revision['sha256']
    assert (OUT/'Authoring/MainSavedReadback.json').stat().st_mtime>=max(material_revision['file'].stat().st_mtime,(OUT/'MainDelivery/Delivered.json').stat().st_mtime)
source_intake_file=Path(candidate['main_rebase_intake']).resolve() if candidate.get('main_rebase_intake') else None
if source_intake_file:
    record('MainRebaseIntake',source_intake_file)
    H['verify_player_polish_source_intake'](source_intake_file,prepared['private_source'])
if shared:
    record('SharedEffectsRebaseRevision',shared['file'])
    record('PlayerPolishExternalDelivery',shared['external_file'])
    assert candidate.get('shared_effects_rebase_revision_sha256')==shared['sha256']
    assert (OUT/'Authoring/MainSavedReadback.json').stat().st_mtime>=max(shared['file'].stat().st_mtime,(OUT/'MainDelivery/Delivered.json').stat().st_mtime)
victim=H['victim_decal_revision_rows'](record('PrivateAuthoring',OUT/'Authoring/PrivateAuthoring.json'),
                                      record('PreparedPlaybackPlan',OUT/'PreparedPlaybackPlan.json'))
H['verify_saved_victim_revision'](victim,saved)
if victim:
    record('VictimDecalPolicyRevision',victim['file'])
    assert candidate.get('victim_decal_policy_revision_sha256')==victim['sha256']
    assert (OUT/'Authoring/MainSavedReadback.json').stat().st_mtime>=victim['file'].stat().st_mtime
    assert evidence['MainSavedReadback']['path'] and (OUT/'Authoring/MainSavedReadback.json').stat().st_mtime>=(OUT/'MainDelivery/Delivered.json').stat().st_mtime
content_revision_file=OUT/'Authoring/ContentRebaseRevision.json'
if content_revision_file.exists():
    record('ContentRebaseRevision',content_revision_file)
    assert saved.get('content_rebase_revision_sha256')==sha(content_revision_file)
drivers = {}
for name in ('MainMonsterRuntimePIE', 'MainPlayerRegression'):
    attempt = Path(record(name + 'Latest', OUT / name / 'Latest.json')['attempt'])
    driver = record(name + 'Driver', attempt / 'Driver.json')
    receipt = record(name + 'Exit', attempt / 'Exit.json')
    record(name + 'Launch', attempt / 'Launch.json')
    record(name + 'Log', attempt / 'PrivatePIE.log')
    if adapter_supplement:
        assert (attempt / 'Launch.json').stat().st_mtime >= supplement_file.stat().st_mtime, 'Main runtime predates adapter supplement'
    if victim:
        assert (attempt/'Launch.json').stat().st_mtime>=max(victim['file'].stat().st_mtime,(OUT/'MainDelivery/Delivered.json').stat().st_mtime), 'Main runtime predates delivered victim revision'
    for revision_file in ([shared['file']] if shared else [])+([source_intake_file] if source_intake_file else [])+([material_revision['file']] if material_revision else []):
        assert (attempt/'Launch.json').stat().st_mtime>=max(revision_file.stat().st_mtime,(OUT/'MainDelivery/Delivered.json').stat().st_mtime), 'Main runtime predates delivered shared/source intake'
    assert driver['status'] == 'passed' and receipt['exit_code'] == 0
    assert driver['package_saves'] == 0 and not driver.get('material_compile_failures')
    assert driver['verification'] == 'fresh_saved_Main'
    loaded = driver['loaded_native_module']
    assert loaded['name'] == delivery['module'] and loaded['build_id'] == delivery['BuildId']
    assert loaded['sha256'] == candidate['native']['UnrealEditor-Khazan.dll']
    assert loaded['manifest_sha256'] == delivery['module_manifest_sha256']
    drivers[name] = (attempt, driver)
visual = record('MainVisualQA', OUT / 'MainVisualQA.json')
assert visual['status'] == 'passed' and visual['visual_review_passed']
if adapter_supplement:
    assert visual.get('adapter_dependency_supplement_sha256') == evidence['AdapterSupplementDelivered']['sha256']
    assert (OUT / 'MainVisualQA.json').stat().st_mtime >= supplement_file.stat().st_mtime
if victim:
    assert visual.get('victim_decal_policy_revision_sha256')==victim['sha256']
if shared:
    assert visual.get('shared_effects_rebase_revision_sha256')==shared['sha256']
if material_revision:
    assert visual.get('visual_material_repair_revision_sha256')==material_revision['sha256']
assert visual['reviewed_images']
for name, key in (('MainMonsterRuntimePIE', 'monster_runtime_driver_sha256'),
                  ('MainPlayerRegression', 'player_runtime_driver_sha256')):
    assert visual[key] == evidence[name + 'Driver']['sha256']
    assert any(Path(row['path']).resolve().is_relative_to(drivers[name][0]) for row in visual['reviewed_images'])
for row in visual['reviewed_images']:
    assert Path(row['path']).suffix.lower() == '.png' and sha(row['path']) == row['sha256']
supplemental_attempts = {}
for name in ('MainRimQA', 'MainYetugaQA'):
    attempt = Path(record(name + 'Latest', OUT / name / 'Latest.json')['attempt']).resolve()
    driver = record(name + 'Driver', attempt / 'Driver.json')
    receipt = record(name + 'Exit', attempt / 'Exit.json')
    record(name + 'Launch', attempt / 'Launch.json')
    record(name + 'Log', attempt / 'PrivatePIE.log')
    if adapter_supplement:
        assert (attempt / 'Launch.json').stat().st_mtime >= supplement_file.stat().st_mtime, 'Main targeted QA predates adapter supplement'
    if victim:
        assert (attempt/'Launch.json').stat().st_mtime>=max(victim['file'].stat().st_mtime,(OUT/'MainDelivery/Delivered.json').stat().st_mtime), 'Main supplemental QA predates delivered victim revision'
    for revision_file in ([shared['file']] if shared else [])+([source_intake_file] if source_intake_file else [])+([material_revision['file']] if material_revision else []):
        assert (attempt/'Launch.json').stat().st_mtime>=max(revision_file.stat().st_mtime,(OUT/'MainDelivery/Delivered.json').stat().st_mtime), 'Main supplemental QA predates delivered shared/source intake'
    assert driver['status'] == 'passed' and receipt['exit_code'] == 0
    assert driver['package_saves'] == driver['asset_mutations'] == 0 and not driver.get('material_compile_failures')
    assert driver['loaded_native_module']['name'] == delivery['module']
    assert driver['loaded_native_module']['sha256'] == candidate['native']['UnrealEditor-Khazan.dll']
    assert driver['loaded_native_module']['manifest_sha256'] == delivery['module_manifest_sha256']
    assert visual['supplemental_driver_sha256'][name] == evidence[name + 'Driver']['sha256']
    supplemental_attempts[name] = attempt
supplemental_owners = set()
for row in visual['reviewed_supplemental_images']:
    path = Path(row['path']).resolve()
    assert path.suffix.lower() == '.png' and sha(path) == row['sha256']
    owner = next((name for name, attempt in supplemental_attempts.items() if path.is_relative_to(attempt)), None)
    assert owner is not None
    supplemental_owners.add(owner)
assert supplemental_owners == set(supplemental_attempts)
record('PreparedPlaybackPlan', OUT / 'PreparedPlaybackPlan.json')
record('PrivateAuthoring', OUT / 'Authoring/PrivateAuthoring.json')
checks = {name: True for name in ('guarded_delivery', 'selected_'+str(968 if material_revision else 967)+'_bytes', 'protected_main_unchanged',
    'existing_native_preserved', 'fresh_main_saved_readback', 'main_monster_rhi', 'main_player_regression_rhi',
    'actual_loaded_module', 'main_png_visual_review')}
checks['main_rim_and_yetuga_targeted_rhi_visual_review'] = True
if victim:
    checks['main_victim_decal_policy_revision_saved_and_runtime_fresh']=True
if shared:
    checks['main_shared_dependency_intake_saved_runtime_and_visual_fresh']=True
if material_revision:
    checks['main_visual_material_repair_saved_runtime_and_visual_fresh']=True
result = {'status': 'MainDeliveredAndFreshVerified', 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'checks': checks, 'evidence': evidence, 'module': delivery['module'],
    'source_files': 11, 'art_files': 457, 'authored_files': 499,
    'authored_sequences': 487, 'source_visual_events': 2855, 'technical_lifetime_sentinels': 487,
    'families': sorted(H['FAMILIES']), 'user_editor_controlled': False,
    'limits': visual.get('limits', [])}
if victim:
    result['victim_decal_policy_revision_sha256']=victim['sha256']
if shared:
    result['shared_effects_rebase_revision_sha256']=shared['sha256']
if material_revision:
    result['visual_material_repair_revision_sha256']=material_revision['sha256']
    result['reused_material_dependencies']=1
    result['selected_delivery_count']=968
if adapter_supplement:
    checks['adapter_dependency_supplement_exact_four_and_fresh_main_proofs'] = True
    result['adapter_dependency_supplement_sha256'] = evidence['AdapterSupplementDelivered']['sha256']
    result['original_selected_delivery_count'] = 968
    result['supplemental_adapter_files'] = 4
    result['selected_delivery_count'] = 972
target = OUT / 'FinalVerification.json'
temporary = target.with_suffix('.json.tmp')
temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
os.replace(temporary, target)
print(json.dumps({'status': result['status'], 'checks': checks}, ensure_ascii=False))
