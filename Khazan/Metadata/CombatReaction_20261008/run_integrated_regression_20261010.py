"""Owned editor file-mailbox orchestration only; tests execute in native C++."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import time

META = Path(__file__).resolve().parent
WORK = Path(r'C:\Users\user\Desktop\GitProject\Khazan_MonsterWork_20261006\Khazan')
MAIL = WORK / 'Saved/MonsterMailbox'
LOG = WORK / 'Saved/Logs/CombatReactionEditor.log'
PID = 23912
TESTS = ['Khazan.Guard.PIE', 'Khazan.Heal.PIE',
         'Khazan.Combat.PlayerAttackCollision.PIE', 'Khazan.Monster.CombatPolicyPIE']
FINAL = META / 'IntegratedRegression.json'
RESUME = META / 'PolicyDebuggerResume_20261010.log'
RUN_LOG = META / 'IntegratedRegression_20261010.log'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_proof():
    baseline = json.loads((META / 'BeforeNativePIE06.json').read_text(encoding='utf-8-sig'))
    actual = {name: sha(WORK / name) for name in baseline['source_config']}
    drift = {name: {'expected': old, 'actual': actual[name]}
             for name, old in baseline['source_config'].items() if old != actual[name]}
    manifest = json.loads((WORK / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
    selected = WORK / 'Binaries/Win64' / manifest['Modules']['Khazan']
    return {'baseline': str(META / 'BeforeNativePIE06.json'),
            'source_config_count': len(actual), 'source_config_sha256': actual,
            'source_config_drift': drift, 'selected_module': manifest,
            'dll_path': str(selected), 'dll_sha256': sha(selected),
            'dll_matches_baseline': sha(selected) == baseline['dll_sha256'],
            'module_selection_matches_baseline': manifest == baseline['selected_module']}


for path in [FINAL, RESUME, RUN_LOG]:
    if path.exists():
        raise RuntimeError(f'Refusing to overwrite prior evidence: {path}')
ready = json.loads((MAIL / 'Ready.json').read_text(encoding='utf-8-sig'))
if ready['pid'] != PID or Path(ready['project']).resolve() != WORK:
    raise RuntimeError(f'Unexpected mailbox identity: {ready}')
proof = source_proof()
if proof['source_config_drift'] or not proof['dll_matches_baseline'] or not proof['module_selection_matches_baseline']:
    raise RuntimeError(f'Frozen test inputs changed: {proof}')
# The parent read the live PID23912 process module inventory before this script.
proof['process_loaded_module_inventory'] = {
    'pid': PID, 'module_name': 'UnrealEditor-Khazan.dll', 'path': proof['dll_path'],
    'observed_via': 'Get-Process -Id 23912.Modules in preceding tool call',
    'matches_disk_and_BeforeNativePIE06': True}
RESUME.write_bytes(LOG.read_bytes())
initial_offset = len(LOG.read_text(encoding='utf-8-sig', errors='replace'))
start = utc()
results = []

for index, test in enumerate(TESTS):
    request = MAIL / f'combat_resume_20261010_regression_{index}_{PID}.request.json'
    if request.exists() or request.with_name(request.name.replace('.request.json', '.response.json')).exists():
        raise RuntimeError(f'Refusing to reuse a request: {request}')
    offset = len(LOG.read_text(encoding='utf-8-sig', errors='replace'))
    request.write_text(json.dumps({'project': str(WORK), 'action': 'console',
                                  'command': f'Automation RunTests {test}'}, ensure_ascii=False), encoding='utf-8')
    print(f'{utc()} requested {test}', flush=True)
    deadline = time.monotonic() + 360
    last_notice = time.monotonic()
    entry = {'test': test, 'request': str(request), 'requested_utc': utc()}
    while time.monotonic() < deadline:
        new = LOG.read_text(encoding='utf-8-sig', errors='replace')[offset:]
        line = next((line for line in new.splitlines()
                     if 'Test Completed.' in line and f'Path={{{test}}}' in line), None)
        if line:
            result = re.search(r'Result=\{([^}]+)\}', line).group(1)
            entry.update(engine_result=result, completion_line=line, completed_utc=utc(), success=result == 'Success')
            print(f'{utc()} {test} engine Result={result}', flush=True)
            results.append(entry)
            # The completion is authoritative; allow native teardown to finish before the next command.
            time.sleep(2)
            break
        if time.monotonic() - last_notice >= 40:
            print(f'{utc()} waiting native completion {test}', flush=True)
            last_notice = time.monotonic()
        time.sleep(.3)
    else:
        entry.update(engine_result='NoCompletionWithin360Seconds', completed_utc=utc(), success=False)
        results.append(entry)
    if not results[-1]['success']:
        break

final_proof = source_proof()
run_text = LOG.read_text(encoding='utf-8-sig', errors='replace')[initial_offset:]
RUN_LOG.write_text(run_text, encoding='utf-8')
success = (len(results) == len(TESTS) and all(item['success'] for item in results)
           and not final_proof['source_config_drift'] and final_proof['dll_matches_baseline'])
receipt = {'schema': 1, 'success': success, 'process_id': PID, 'project': str(WORK),
           'started_utc': start, 'completed_utc': utc(), 'tests': results,
           'execution': 'Sequential stock native C++ tests in own isolated fresh editor; NullRHI',
           'scope': {'source_assets_modified': False, 'player_input_injected': False,
                     'physical_keyboard_gamepad_tested': False, 'visual_RHI_QA': False,
                     'authoring_helpers_invoked': False},
           'source_module_proof_before': proof, 'source_module_proof_after': final_proof,
           'evidence': {'pre_request_log': str(RESUME), 'sequential_test_log': str(RUN_LOG),
                        'native_full_reaction_test': str(META / 'NativePIE_Final.json')},
           'prior_policy_failure': {'original_utc': '2026-10-08T13:36:27.509Z',
                                   'message': 'Attack completion -> Chase not observed',
                                   'status': 'Not reproduced in fresh resumed policy test; original failure retained',
                                   'production_fix_claimed': False},
           'debugger_resume_parent_report': {'fresh_pid': PID, 'observed_frames': 3,
                                            'heavy_state': '[Root][Attack]',
                                            'heavy_montage': 'Attack_SwordSwing_02_Single',
                                            'engine_policy_completed_utc': '2026-10-10T10:48:31.502Z',
                                            'root_created_breakpoints_removed': 3,
                                            'existing_user_breakpoints_preserved': 8,
                                            'session_detached_before_this_run': True,
                                            'source': 'Parent agent tool observations, not additional debugger control by this script'}}
FINAL.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'success': success, 'receipt': str(FINAL), 'test_count': len(results)}), flush=True)
raise SystemExit(0 if success else 1)
