"""Bind this task's saved montage, build, and real GPU PIE receipts."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = root/'Metadata/PlayerSlashOuter_20261014'
apply = json.loads((out/'MainApply/Receipt.json').read_text(encoding='utf-8'))
saved = json.loads((out/'MainSavedReadback01/SavedReadback.json').read_text(encoding='utf-8'))
first = json.loads((out/'AuthorCandidate01/Author.json').read_text(encoding='utf-8'))
second = json.loads((out/'RetuneCandidate02/Retune.json').read_text(encoding='utf-8'))
work_only = json.loads((out/'Candidate3OnlyRHI01/Driver.json').read_text(encoding='utf-8'))
work_both = json.loads((out/'Candidate3ComposedRHI01/Driver.json').read_text(encoding='utf-8'))
main = json.loads((out/'MainRHI01/Driver.json').read_text(encoding='utf-8'))
assert apply['status'] == 'applied' and saved['status'] == 'passed'
assert work_only['status'] == work_both['status'] == main['status'] == 'passed'
assert saved['slash_pairs'] == 33 and saved['original_effect_objects_unchanged'] == 882
assert saved['changed_slash_start_end_objects'] == 64
assert len(list((out/'Candidate3OnlyRHI01').glob('Pair_*.png'))) == 99
assert len(list((out/'Candidate3ComposedRHI01').glob('Pair_*.png'))) == 99
assert len(list((out/'MainRHI01').glob('Slash_*.png'))) == 288
assert 'Result: Succeeded' in (out/'WorkBuild04/stdout.txt').read_text(encoding='utf-16')
assert 'Result: Succeeded' in (out/'MainBuild01/stdout.txt').read_text(encoding='utf-16')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for rel, row in apply['targets'].items():
    assert sha(root/rel) == row['after_sha256']

def gpu(name):
    rows = [json.loads(line) for line in (out/name/'GPUWeaponEndpoint.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 68
    highest = max(row['actual_gpu_tip_error_cm'] for row in rows)
    assert highest < 0.1
    return {'rows':len(rows),'max_error_cm':highest}

tuning = {}
for row in first['rows']:
    for obj in row['changes']:
        if obj['end']:continue
        tuning[obj['id']] = {'side':obj['side'],'outward_cm':obj['outward_cm'],
                             'xy_scale':obj['xy_scale'],'asset':row['asset']}
for row in second['rows']:
    for obj in row['changes']:
        if obj['end']:continue
        assert obj['id'] in tuning
        tuning[obj['id']].update(outward_cm=obj['outward_cm'],xy_scale=obj['xy_scale'])
assert len(tuning) == 32

result = {
    'status':'main_applied_and_validated',
    'target':'all current player gameplay montages referencing KZ_Slash',
    'asset_receipt':'MainApply/Receipt.json',
    'saved_readback':'MainSavedReadback01/SavedReadback.json',
    'target_montages':len(apply['targets']),
    'slash_pairs_reviewed':33,'tuned_pairs':32,
    'untouched_hand_authored_sequencer_pair':'b7016da5',
    'original_effect_objects_unchanged':882,
    'event_clock_guid_unchanged':True,
    'work_build':'WorkBuild04/stdout.txt',
    'main_build':'MainBuild01/stdout.txt',
    'work_added_only':{'report':'Candidate3OnlyRHI01/Driver.json',**gpu('Candidate3OnlyRHI01')},
    'work_composed':{'report':'Candidate3ComposedRHI01/Driver.json',**gpu('Candidate3ComposedRHI01')},
    'main_composed':{'report':'MainRHI01/Driver.json',**gpu('MainRHI01'),
                     'loaded_module':main['actual_loaded_module'],
                     'module_sha256':main['module_sha256']},
    'visual_review':'All 33 start windows, three frame/view captures per pair, four addition-only and four composite contact sheets reviewed; Main 288 node captures available.',
    'source_of_numbers':'TEMP visual tuning, not original game metadata; imported KZ_Slash mesh geometry is a separate asset measurement',
    'tuning':tuning,
    'source_sha256':{
        str(path.relative_to(root)):sha(path) for path in [
            root/'Source/Khazan/Ability/KZActionAbility.cpp',
            root/'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h',
            root/'Source/Khazan/Tests/KZCombatEffectPIETest.cpp']},
    'scope_limit':'Current project attack animations and D3D12 PIE; original game pixel/shader parity, Shipping/network performance not established.'
}
(out/'FinalVerification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('SLASH_OUTER_FINAL',len(tuning),result['main_composed']['max_error_cm'])
