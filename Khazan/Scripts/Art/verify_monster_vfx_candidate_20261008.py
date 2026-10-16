"""Freeze private saved/RHI/visual/native proofs before guarded Main delivery."""
from pathlib import Path
import hashlib
import json
import os
import runpy

MAIN = Path(__file__).resolve().parents[2]
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
OUT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
RES = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
evidence = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(name, path):
    path = Path(path).resolve()
    assert path.is_file(), path
    evidence[name] = {'path': str(path), 'sha256': sha(path)}
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.suffix == '.json' else None


def inputs(root):
    values = {p.relative_to(root).as_posix(): sha(p)
              for folder in ('Source', 'Config') for p in (root / folder).rglob('*') if p.is_file()}
    values['Khazan.uproject'] = sha(root / 'Khazan.uproject')
    return values


build_path = Path(record('BuildLatest', OUT / 'Build/Latest.json')['attempt'])
build = record('BuildExit', build_path / 'Exit.json')
record('BuildLaunch', build_path / 'Launch.json')
record('BuildLog', build_path / 'PrivateBuild.log')
assert build['exit_code'] == 0 and build['private_inputs_unchanged'] and build['main_inputs_unchanged']
assert inputs(MAIN) == build['main_inputs'], 'Main concurrent input changes require integration/rebuild'
assert inputs(WORK) == build['private_inputs'], 'Private inputs changed after compiled proof'
source_intake_file=Path(os.environ.get('KZ_MONSTER_VFX_SOURCE_INTAKE',str(
    OUT/'MainRebase/PlayerPolishSourceIntake.json' if (OUT/'MainRebase/PlayerPolishSourceIntake.json').exists()
    else OUT/'MainRebase/BrutalInputSourceIntake.json' if (OUT/'MainRebase/BrutalInputSourceIntake.json').exists()
    else OUT/'MainRebase/MainRebaseIntake.json'))).resolve()
source_intake=None
if source_intake_file.exists():
    assert source_intake_file.is_relative_to((OUT/'MainRebase').resolve())
    source_intake=record('MainRebaseIntake',source_intake_file)
    assert source_intake['status']=='passed'
    assert source_intake['original_baseline_sha256']==sha(OUT/'WorkBaseline.json')
    assert source_intake['main_source']=={p:h for p,h in build['main_inputs'].items() if p.startswith('Source/')}
    if source_intake.get('prior_main_rebase_intake'):
        prior=source_intake['prior_main_rebase_intake'];record('PriorMainRebaseIntake',prior['path'])
        assert sha(prior['path'])==prior['sha256'], 'Prior explicit source intake changed'
native = {name: sha(WORK / 'Binaries/Win64' / name) for name in build['native']}
assert native == build['native'], 'Native candidate changed after build'
plan = record('PreparedPlaybackPlan', OUT / 'PreparedPlaybackPlan.json')
author = record('PrivateAuthoring', OUT / 'Authoring/PrivateAuthoring.json')
saved = record('SavedReadback', OUT / 'Authoring/SavedReadback.json')
assert author['status'] == 'passed' and saved['status'] == 'passed'
assert author['plan_sha256'] == sha(OUT / 'PreparedPlaybackPlan.json')
assert not plan['blockers']
D=runpy.run_path(str(MAIN/'Scripts/Art/deliver_monster_vfx_main_20261008.py'),run_name='monster_visual_delivery_readonly_helpers')
if source_intake:
    D['verify_player_polish_source_intake'](source_intake_file,{p:h for p,h in build['private_inputs'].items() if p.startswith('Source/')})
shared=D['shared_effects_rebase_revision']()
D['verify_saved_shared_revision'](shared,saved)
material_revision=shared['visual_revision'] if shared else D['visual_material_repair_revision']()
D['verify_saved_visual_revision'](material_revision,saved)
if material_revision:
    record('VisualMaterialRepairRevision',material_revision['file'])
    for index,row in enumerate(material_revision['receipts']):
        record('VisualMaterialAuthorReceipt'+str(index),row['path'])
    assert (OUT/'Authoring/SavedReadback.json').stat().st_mtime>=material_revision['file'].stat().st_mtime, 'Saved audit predates material repair'
if shared:
    record('SharedEffectsRebaseRevision',shared['file'])
    record('PlayerPolishExternalDelivery',shared['external_file'])
    assert (OUT/'Authoring/SavedReadback.json').stat().st_mtime>=shared['file'].stat().st_mtime, 'Saved audit predates shared dependency intake'
if source_intake:
    assert (build_path/'Launch.json').stat().st_mtime>=source_intake_file.stat().st_mtime, 'Native build predates source intake'
victim=D['victim_decal_revision_rows'](author,plan)
D['verify_saved_victim_revision'](victim,saved)
if victim:
    record('VictimDecalPolicyRevision',victim['file'])
    assert (OUT/'Authoring/SavedReadback.json').stat().st_mtime>=victim['file'].stat().st_mtime, 'Saved audit predates victim revision'
content_revision_file=OUT/'Authoring/ContentRebaseRevision.json'
if content_revision_file.exists():
    content_revision=record('ContentRebaseRevision',content_revision_file)
    assert content_revision['status']=='passed' and content_revision['mode']=='apply'
    assert content_revision['author_before_sha256']==sha(OUT/'Authoring/PrivateAuthoring.json')
    assert content_revision['plan_sha256']==sha(OUT/'PreparedPlaybackPlan.json')
    assert content_revision['original_author_journal_preserved'] and content_revision['untouched493_sha_preserved']
    assert content_revision['main_mutations']==0 and content_revision['package_saves']==6
    assert saved.get('content_rebase_revision_sha256')==sha(content_revision_file), 'Fresh saved readback must verify the merged definitions'
    record('ContentRebaseIntake',content_revision['contentintake'])
    assert sha(content_revision['contentintake'])==content_revision['contentintake_sha256']
    assert len(content_revision['rows'])==6
    D['rebased_definition_rows'](author,plan,victim['sequences'] if victim else None)
    for row in content_revision['rows']:
        assert row['all_other_definition_fields_preserved']
        assert sha(MAIN/row['relative'])==row['main_before_sha256']
        assert sha(WORK/row['relative'])==row['merged_after_sha256']
        assert sha(row['main_backup_path'])==row['main_before_sha256']
        assert sha(row['private_backup_path'])==row['prior_private_sha256']
binding_path = OUT / 'Authoring/ApesCurrentMaterialBindingRevision/Applied.json'
if binding_path.exists():
    binding = record('ApesCurrentMaterialBindingRevision', binding_path)
    assert binding['status'] == 'passed' and binding['mode'] == 'apply'
    assert binding['plan_after_sha256'] == sha(OUT / 'PreparedPlaybackPlan.json')
    assert binding['author_after_sha256'] == sha(OUT / 'Authoring/PrivateAuthoring.json')
    assert binding['original_main_before_journal_preserved'] and binding['source_schema_unchanged']
    assert binding['asset_saves'] == 2 and binding['asset_mutations'] == 5
art = record('ArtCandidateManifest', RES / 'ArtCandidateManifest.json')
resource = record('FinalResourceAudit', RES / 'FinalResourceAudit.json')
assert resource['schema'] == 'Khazan.MonsterVFX.FinalResourceAudit.v1' and resource.get('passed') is True
record('NativeAdapterMap', RES / 'NativeAdapterMap.json')
record('DecalCurveRegistry', RES / 'DecalCurveRegistry.json')
for name in ('PrivateMonsterRuntimePIE', 'PrivatePlayerRegression'):
    path = Path(record(name + 'Latest', OUT / name / 'Latest.json')['attempt'])
    driver = record(name + 'Driver', path / 'Driver.json')
    exit_receipt = record(name + 'Exit', path / 'Exit.json')
    record(name + 'Launch', path / 'Launch.json')
    record(name + 'Log', path / 'PrivatePIE.log')
    if content_revision_file.exists():
        assert (path/'Launch.json').stat().st_mtime>=content_revision_file.stat().st_mtime, 'Runtime predates merged definitions'
    if victim:
        assert (path/'Launch.json').stat().st_mtime>=victim['file'].stat().st_mtime, 'Runtime predates victim revision'
    for revision_file in ([shared['file']] if shared else [])+([source_intake_file] if source_intake else [])+([material_revision['file']] if material_revision else []):
        assert (path/'Launch.json').stat().st_mtime>=revision_file.stat().st_mtime, 'Runtime predates shared/source intake'
    assert driver['status'] == 'passed' and exit_receipt['exit_code'] == 0, name
    assert not driver.get('material_compile_failures'), name
    loaded = driver['loaded_native_module']
    assert loaded['sha256'] == native['UnrealEditor-Khazan.dll'], name + ': wrong loaded native module'
    assert loaded['manifest_sha256'] == native['UnrealEditor.modules'], name + ': wrong module manifest'
    assert loaded['build_id'] == '55116800'
supplemental_attempts = {}
for name in ('PrivateRimQA', 'PrivateYetugaQA'):
    path = Path(record(name + 'Latest', OUT / name / 'Latest.json')['attempt'])
    driver = record(name + 'Driver', path / 'Driver.json')
    receipt = record(name + 'Exit', path / 'Exit.json')
    record(name + 'Launch', path / 'Launch.json')
    record(name + 'Log', path / 'PrivatePIE.log')
    if content_revision_file.exists():
        assert (path/'Launch.json').stat().st_mtime>=content_revision_file.stat().st_mtime, 'Supplemental QA predates merged definitions'
    if victim:
        assert (path/'Launch.json').stat().st_mtime>=victim['file'].stat().st_mtime, 'Supplemental QA predates victim revision'
    for revision_file in ([shared['file']] if shared else [])+([source_intake_file] if source_intake else [])+([material_revision['file']] if material_revision else []):
        assert (path/'Launch.json').stat().st_mtime>=revision_file.stat().st_mtime, 'Supplemental QA predates shared/source intake'
    assert driver['status'] == 'passed' and receipt['exit_code'] == 0, name
    assert driver['package_saves'] == driver['asset_mutations'] == 0
    assert not driver.get('material_compile_failures') and driver['captures']
    loaded = driver['loaded_native_module']
    assert loaded['sha256'] == native['UnrealEditor-Khazan.dll']
    assert loaded['manifest_sha256'] == native['UnrealEditor.modules']
    supplemental_attempts[name] = path.resolve()
visual = record('VisualQA', OUT / 'VisualQA.json')
assert visual['status'] == 'passed' and visual['visual_review_passed'] and visual['reviewed_images'], 'Actual PNG review required'
if victim:
    assert visual.get('victim_decal_policy_revision_sha256')==victim['sha256'], 'PNG review predates victim revision'
if shared:
    assert visual.get('shared_effects_rebase_revision_sha256')==shared['sha256'], 'PNG review predates shared dependency intake'
if material_revision:
    assert visual.get('visual_material_repair_revision_sha256')==material_revision['sha256'], 'PNG review predates material repair'
for row in visual['reviewed_images']:
    assert sha(row['path']) == row['sha256'], row['path']
for key, path in {'art_candidate_manifest_sha256': RES / 'ArtCandidateManifest.json',
                  'authoring_sha256': OUT / 'Authoring/PrivateAuthoring.json',
                  'plan_sha256': OUT / 'PreparedPlaybackPlan.json'}.items():
    assert visual[key] == sha(path), 'Visual review belongs to a different candidate: ' + key
for name, key in [('PrivateMonsterRuntimePIE', 'monster_runtime_driver_sha256'),
                  ('PrivatePlayerRegression', 'player_runtime_driver_sha256')]:
    assert visual[key] == evidence[name + 'Driver']['sha256'], key
supplemental_owners = set()
for row in visual['reviewed_supplemental_images']:
    path = Path(row['path']).resolve()
    assert path.suffix.lower() == '.png' and sha(path) == row['sha256']
    owner = next((name for name, attempt in supplemental_attempts.items() if path.is_relative_to(attempt)), None)
    assert owner is not None
    supplemental_owners.add(owner)
assert supplemental_owners == set(supplemental_attempts)
for name in supplemental_attempts:
    assert visual['supplemental_driver_sha256'][name] == evidence[name + 'Driver']['sha256']
revision = RES / 'ExecutionRadiusRevision.json'
if revision.exists():
    record('ExecutionRadiusRevision', revision)
light_revision = RES / 'LightUsageRevision.json'
if light_revision.exists():
    light = record('LightUsageRevision', light_revision)
    assert light['status'] == 'passed'
checks = {name: True for name in ('private_build', 'compiled_inputs_unchanged', 'native_unchanged',
          'private_author', 'fresh_saved_readback', 'resource_audit', 'monster_rhi',
          'player_regression_rhi', 'png_visual_review', 'main_inputs_unchanged')}
checks['rim_and_yetuga_targeted_rhi_visual_review'] = True
if victim:
    checks['victim_decal_policy_revision_saved_and_runtime_fresh']=True
if shared:
    checks['shared_dependency_intake_saved_runtime_and_visual_fresh']=True
if material_revision:
    checks['visual_material_repair_saved_runtime_and_visual_fresh']=True
result = {'status': 'passed', 'checks': checks, 'evidence': evidence, 'native': native,
          'build_attempt': str(build_path), 'main_inputs': build['main_inputs'],
          'private_inputs': build['private_inputs'], 'visual_review': visual}
if source_intake:
    result['main_rebase_intake']=str(source_intake_file.resolve())
if victim:
    result['victim_decal_policy_revision_sha256']=victim['sha256']
if shared:
    result['shared_effects_rebase_revision_sha256']=shared['sha256']
if material_revision:
    result['visual_material_repair_revision_sha256']=material_revision['sha256']
    result['selected_delivery_count']=968
target = OUT / 'NativeCandidateIntegrity.json'
temp = target.with_suffix('.json.tmp')
temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
os.replace(temp, target)
print(json.dumps({'status': result['status'], 'checks': checks}, ensure_ascii=False))
