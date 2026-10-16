"""Read-only proof aggregation after selective delivery and fresh Main reload."""
from pathlib import Path
import hashlib, json, datetime

out = Path(__file__).resolve().parent
main = out.parents[1]
target = out / 'FinalVerification.json'
assert not target.exists(), 'Preserve final verification receipt'

def read(name):
    return json.loads((out / name).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

prepared = read('PreparedDelivery.json')
work = Path(prepared['work'])
receipt = read('DeliveryReceipt.json')
assert receipt['complete'] and receipt['canonical_dll_preserved']
assert len(prepared['rows']) == len(receipt['rows']) == 146
assert (prepared['runtime_source_count'], prepared['asset_count']) == (16, 130)
owned = {r['relative']: r for r in prepared['rows']}
for row in prepared['rows']:
    assert sha(main / row['relative']) == sha(work / row['relative']) == row['after'], row['relative']

baseline = read('StageBaseline.json')
protected = []
for row in baseline['rows']:
    if row['relative'] not in owned:
        assert sha(main / row['relative']) == row['main'], row['relative']
        protected.append(row['relative'])
dependencies = read('DependencyStage.json')['rows']
for row in dependencies:
    assert sha(main / row['relative']) == row['main'], row['relative']
for row in read('PlayerBlueprintIntake.json')['rows']:
    assert sha(main / row['relative']) == row['main_sha256'], row['relative']

tested = read('TestedSource.json')
source_config = {p.relative_to(main).as_posix(): sha(p)
                 for directory in ('Source', 'Config')
                 for p in (main / directory).rglob('*') if p.is_file()}
assert source_config == tested['source_config']
native_source = read('BeforeNativePIE06.json')['source_config']
removed = {f'Source/Khazan/Tests/{row["file"]}'
           for row in read('TemporaryHelpersRemoved_20261010.json')['removed']}
assert set(native_source) - set(source_config) == removed
assert set(source_config) - set(native_source) == set()
changed = {rel for rel in source_config if source_config[rel] != native_source[rel]}
assert changed == {'Source/Khazan/Khazan.Build.cs'}, changed
for rel in removed:
    assert not (main / rel).exists() and not (work / rel).exists()
assert sha(main / 'Source/Khazan/Khazan.Build.cs') == sha(work / 'Source/Khazan/Khazan.Build.cs')

native = read('NativePIE_Final.json')
assert native['success'] and not native['partial_scope']
assert (native['completed_reaction_cases'], native['completed_pair_cases'], native['completed_collision_cases']) == (32, 15, 3)
assert not native['authored_assets_modified'] and not native['private_completion_mutated']
assert all(row['passed'] for row in native['checks'])
regression = read('IntegratedRegression.json')
assert regression['success'] and len(regression['tests']) == 4
assert all(row['success'] and row['engine_result'] == 'Success' for row in regression['tests'])
assert 'Result: Succeeded' in (out / 'StockBuild.log').read_text(encoding='utf-8-sig')

reloads = {}
for label in ('Work', 'Main'):
    report = read(label + 'SavedReload.json')
    assert report['success'] and not report['failures'] and not report['unavailable_required']
    assert report['checks'] == 654552
    assert not report['final_dirty']['content'] and not report['final_dirty']['maps']
    assert report['loaded_module']['sha256'] == prepared['dll_sha256'] == tested['dll_sha256']
    log = (out / (label + 'SavedReload.log')).read_text(encoding='utf-8-sig', errors='replace')
    assert 'LogExit: Exiting.' in log and 'Log file closed' in log
    assert 'Fatal error' not in log and 'LogWindows: Error:' not in log
    reloads[label] = dict(process=read(label + 'SavedReloadProcess.json')['pid'],
                         checks=report['checks'], loaded_module=report['loaded_module'],
                         counts=report['counts'], dirty=report['final_dirty'],
                         report_sha256=sha(out / (label + 'SavedReload.json')))

module = main / 'Binaries/Win64/UnrealEditor.modules'
selected = json.loads(module.read_text(encoding='utf-8-sig'))
assert selected['Modules']['Khazan'] == prepared['alias']
assert sha(module) == receipt['modules_sha256']
assert reloads['Main']['loaded_module']['selected'] == prepared['alias']
assert sha(main / 'Binaries/Win64' / prepared['alias']) == prepared['dll_sha256']
assert sha(main / 'Binaries/Win64/UnrealEditor-Khazan.dll') == prepared['main_canonical_dll_before']
screenshots = sorted((out / 'Screenshots').glob('*.png'))
assert len(screenshots) == native['native_rhi_screenshots_requested'] == 7

result = dict(success=True, status='MainDeliveredAndFreshVerified',
              utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              delivered_files=146, runtime_files=16, new_runtime_classes=1, assets=130,
              protected_baseline_files=len(protected), protected_dependency_files=len(dependencies),
              source_config_count=len(source_config), all_source_config_match_tested=True,
              native_to_stock_delta=dict(removed=sorted(removed), changed=sorted(changed), production_runtime_unchanged=True),
              stock_build_success=True, selected_module=selected, canonical_dll_preserved=True,
              native_rhi=dict(reactions=32, pairs=15, collisions=3, variants=native['observed_reaction_variants'],
                              checks=len(native['checks']), report_sha256=sha(out/'NativePIE_Final.json')),
              regression_tests=[dict(test=r['test'], result=r['engine_result']) for r in regression['tests']],
              reloads=reloads, screenshots=[dict(file=p.name, sha256=sha(p)) for p in screenshots],
              user_or_other_task_editor_controlled=False,
              prior_policy_timeout=dict(reproduced_in_fresh_runs=False, production_ai_changed=False,
                                        original_timeout_cause_confirmed=False),
              limits=['Original pixel/contact fidelity and multiplayer were not established.',
                      'Full RHI PIE used pre-trim DLL with identical production runtime source; final stock Work/Main used saved reload.',
                      'Heavy Launch uses Short fallback; Apes/Yetuga use dedicated Grapple fallback.',
                      'Original unsupported collision shape occurrences11 remain explicitly excluded.',
                      'Player separate death implementation and actual parry producer remain outside this change.'])
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(success=True, files=146, runtime=16, assets=130,
                     source_config=len(source_config), main_checks=reloads['Main']['checks'],
                     selected=prepared['alias'])))
