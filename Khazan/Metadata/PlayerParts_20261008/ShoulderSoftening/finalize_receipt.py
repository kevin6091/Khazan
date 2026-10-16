"""Read-back the completed single-package Main handoff and private recovery."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
report = Path(__file__).resolve().parent
main = report.parents[2]
def read(name): return json.loads((report/name).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
handoff, ready = read('MainSelectiveHandoff.json'), read('MainReadyAudit.json')
assert handoff['success'] and ready['success'] and handoff['pid'] == ready['pid'] == 24552
assert handoff['dirty_content'] == handoff['dirty_map'] == 0 and not handoff['game_world']
assert handoff['selected_actors_preserved'] and not handoff['main_close']
assert not handoff['explicit_compile_or_save']
snapshot, manifest = read('MainSelectiveSnapshot.json'), read('CandidateManifest.json')
changed = [p['path'] for p in snapshot['protected'] if sha(main/p['path']) != p['sha256']]
assert not changed, changed
assert len(snapshot['protected']) == handoff['protected_unchanged'] == 166
assert len(manifest['packages']) == 1
for entry in manifest['packages']:
    assert sha(main/entry['path']) == entry['preparedSha256']
    assert not (main/(entry['path']+'.clothrefinement_pending')).exists()
binding = read('StockBinding.json')
assert binding['status'] == 'Restored'
work = Path(binding['workRoot'])
for entry in binding['workFilesBefore']:
    assert sha(work/entry['relativePath']) == entry['sha256'] if entry['existed'] else not (work/entry['relativePath']).exists()
assert read('OwnedEditorExit.json')['activeOwnedEditorCount'] == 0
initial_changes = [p['path'] for p in read('ProtectedBefore.json') if sha(main/p['path']) != p['sha256']]
receipt = dict(utc=datetime.now(timezone.utc).isoformat(), complete=True, main_pid=24552,
    main_world=handoff['world'], single_torso_pa_delivered=True, packages=manifest['packages'],
    protected_during_handoff_unchanged=166, protected_final_readback_unchanged=True,
    initial_baseline_concurrent_changes=initial_changes,
    initial_changes_scope='Concurrent unrelated user/other-task edits preserved by fresh handoff snapshot.',
    main_ready=True, private_binaries_restored=True, owned_editor_processes_remaining=0,
    dirty_content=0, dirty_map=0, main_pie_started=False, main_closed=False,
    native_verification=read('Verification.json'),
    numeric_source='Assistant temporary tuning; original-game physics metadata unverified.',
    limitation='Fixed30 idle/move/release fixture and three anatomy-proxy snapshots, not every gameplay pose/skin collision.')
(report/'FinalReceipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('Complete: Main Torso PA1 reloaded, protected166 unchanged, private binaries restored, owned editors0.')
