"""Select representative current giant/player audio clips from saved source plans."""
from collections import defaultdict
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/GiantSFX_20261013'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
giant = read(ROOT / 'Saved/ImportReports/GameplayAudio_20261011/AudioAuthoringPlan01.json')
humanoid = read(ROOT / 'Metadata/HumanoidSFX_20261013/AudioAuthoringPlan01.json')
inventory = read(ROOT / 'Metadata/HumanoidSFX_20261013/Inventory02/Inventory.json')
current_seconds = {r['asset']: r['seconds'] for r in inventory['animations']}
by_asset = defaultdict(list)
for e in giant['events']:
    if e['family'] in ('Yetuga', 'ApesStoneHandElite'):
        by_asset[e['asset']].append(e)
for e in humanoid['events']:
    if e['family'] == 'Player':
        by_asset[e['asset']].append(e)

selections = [
    ('ApesStoneHandElite', 'Alert_Roar_Composite_Variant01', False),
    ('ApesStoneHandElite', 'Attack_NormalAtk02_01', False),
    ('ApesStoneHandElite', 'Attack_FastBall_Shoot', False),
    ('ApesStoneHandElite', 'Attack_CloseGrab_Start', False),
    ('ApesStoneHandElite', 'Locomotion_Dodge', False),
    ('ApesStoneHandElite', 'Damage_Grapple_Atk_01', True),
    ('ApesStoneHandElite', 'Death_Die_F', False),
    ('ApesStoneHandElite', 'Locomotion_LockOnMove_F', False),
    ('Yetuga', 'Alert_Roar', False),
    ('Yetuga', 'Attack_DempseyRoll', False),
    ('Yetuga', 'Attack_FastBall_Shoot', False),
    ('Yetuga', 'Attack_IceBreath_01', False),
    ('Yetuga', 'Attack_CloseGrab_Success_02', False),
    ('Yetuga', 'Attack_RushGrab_Dash', False),
    ('Yetuga', 'Attack_Armageddon_Start', False),
    ('Yetuga', 'Damage_Grapple_Atk_01', True),
    ('Yetuga', 'Death_Die_F', False),
    ('Yetuga', 'Locomotion_LockOnMove_F', False),
    ('Player', 'CA_P_Kazan_DualAxeSword_Heal_01', False),
    ('Player', 'CA_P_Kazan_DualAxeSword_Off_Dodge_F_M1', False),
    ('Player', 'Player_Guard_Start', False),
    ('Player', 'AC_Kazan_DualAxeSword_Com_Grapple_Atk_01', False),
]
rows = []
for family, name, in_game in selections:
    matches = [(p, e) for p, e in by_asset.items() if p.endswith('/' + name)
               and e[0]['family'] == family and
               (('/Game/Monsters/' in p) == in_game if family != 'Player' else True)]
    assert len(matches) == 1, (family, name, in_game, [p for p, _ in matches])
    asset, events = matches[0]
    expected = [{'start': e['start'], 'cue': e['cue'], 'state': e['is_state']}
                for e in events if e['cue']]
    assert expected, (family, asset)
    seconds = float(current_seconds[asset]) if family == 'Player' else max(float(e['clip']['seconds']) for e in events)
    rows.append({'family': family, 'asset': asset, 'seconds': seconds,
                 'expected': expected, 'source_event_count': len(events)})
output = OUT / 'ExtendedMixer01'
output.mkdir(parents=True, exist_ok=True)
plan = {'samples': rows, 'submix': '/Game/Audio/Original/Settings/SM_Original',
        'output': str(output), 'projectile_count': 2, 'timeout_seconds': 300,
        'qa_policy': 'Saved original/current cue rows, transient montage on real DevMap actors; actual mixer output and current FastBall Shoot/Impact.'}
path = OUT / 'ExtendedRuntimeSamples.json'
assert not path.exists(), path
path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'samples': len(rows), 'expected_cues': sum(len(r['expected']) for r in rows),
                  'families': sorted({r['family'] for r in rows}), 'path': str(path)}))
