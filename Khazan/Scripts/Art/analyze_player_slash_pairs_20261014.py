"""Summarize actual per-window weapon motion and effect placement from PIE."""
from collections import defaultdict
from pathlib import Path
import json
import math
import sys

root = Path(__file__).resolve().parents[2]
out = root/'Metadata/PlayerSlashOuter_20261014'
run = out/sys.argv[1]
inventory = json.loads((out/'Audit01/Inventory.json').read_text(encoding='utf-8'))
authored = {}
for asset in inventory['rows']:
    for item in asset['addons']:
        if not item['bEndEvent']:
            authored[item['EventId']] = {'asset': asset['asset'], 'start': item['WindowStartTime'],
                                         'near': item['WeaponEdgeNearSocket'],
                                         'sequencer': item['bUseSequencerTransform']}
groups = defaultdict(list)
for line in (run/'PairPose.jsonl').read_text(encoding='utf-8').splitlines():
    row = json.loads(line)
    groups[(row['node'], row['id'])].append(row)

def length(v):
    return math.sqrt(sum(x*x for x in v))

def sub(a, b):
    return [x-y for x,y in zip(a,b)]

report = []
for (node, effect_id), rows in sorted(groups.items()):
    a = authored[effect_id]
    sides = sorted(set(r['side'] for r in rows))
    motion = {'L':0., 'R':0.}
    radial = []
    for prev, row in zip(rows, rows[1:]):
        if row['frame'] <= prev['frame'] or row['frame']-prev['frame'] > 2:
            continue
        actor_step = sub(row['actor'], prev['actor'])
        for hand, key in [('L','left_tip'), ('R','right_tip')]:
            motion[hand] += length(sub(sub(row[key],prev[key]),actor_step))
    for row in rows:
        key = 'right_tip' if row['side']=='Weapon_R' else 'left_tip'
        tip_vec = sub(row[key],row['actor'])
        unit = [x/length(tip_vec) for x in tip_vec] if length(tip_vec) else [0,0,0]
        radial.append(sum(x*y for x,y in zip(sub(row['effect'],row['actor']),unit)))
    report.append({'node':node,'id':effect_id,'asset':a['asset'],'start':a['start'],
                   'authored_near':a['near'],'sequencer':a['sequencer'],
                   'observed_sides':sides,'samples':len(rows),
                   'motion_cm':{k:round(v,2) for k,v in motion.items()},
                   'effect_radial_cm':round(sum(radial)/len(radial),2),
                   'mean_scale':round(sum(r['scale'][0] for r in rows)/len(rows),3)})
(run/'PairAnalysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('UNIQUE',len({r['id'] for r in report}),'GROUPS',len(report))
for r in report:
    print(f"{r['node']:<20} {r['id'][-8:]} {','.join(r['observed_sides']):<9} "
          f"L={r['motion_cm']['L']:6.1f} R={r['motion_cm']['R']:6.1f} "
          f"radial={r['effect_radial_cm']:6.1f} scale={r['mean_scale']:.2f}")
