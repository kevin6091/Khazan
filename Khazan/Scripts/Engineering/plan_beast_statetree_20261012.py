"""Translate saved original BT links into reviewable StateTree routing data."""
from pathlib import Path
from collections import Counter
import hashlib
import json

MAIN = Path(__file__).resolve().parents[2]
OUT = MAIN / 'Metadata/BeastDodge_20261012'
SOURCE = MAIN / 'Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/BT_Yetuga.json'
bt = json.loads(SOURCE.read_text(encoding='utf-8-sig'))


def index(ref):
    return int(ref['ObjectPath'].rsplit('.', 1)[-1]) if ref else None


def skill(ref):
    return ref['ObjectPath'].rsplit('.', 1)[0].rsplit('/', 1)[-1].removeprefix('SI_Yetuga_') if ref else ''


def gate(raw, is_task=False):
    angle = raw.get('AngleCondition', {})
    range_ = raw.get('Range', {})
    check = raw.get('bRangeCheck' if is_task else 'bCheckRange', True)
    wall = raw.get('SkillTraceCondition', {})
    result = {'MinDistance': range_.get('Min', raw.get('RangeMin', 0)) if check else 0,
        'MaxDistance': range_.get('Max', raw.get('RangeMax', 0)) if check else 0,
        'BaseYaw': angle.get('BaseDegree', 0), 'LeftYaw': angle.get('LeftDegree', 180), 'RightYaw': angle.get('RightDegree', 180),
        'MaxHP': -1, 'MinStamina': 0, 'MaxStamina': -1}
    for s in raw.get('StatusConditions', []):
        kind, op = s['StatusCheckType'].split('::')[-1], s['CompareOper'].split('::')[-1]
        assert s.get('bCompareRate') is False, s
        if kind == 'HealthPoint' and op == 'LessThanOrEqualTo': result['MaxHP'] = s['Value']
        elif kind == 'Stamina' and op == 'GreaterThanOrEqualTo': result['MinStamina'] = s['Value']
        else: raise ValueError(('Unhandled exact status condition', s))
    if wall.get('bLineTraceToTarget') is False:
        result.update(WallCheckYaw=wall.get('LineTraceAngle', 0), WallCheckDistance=wall['LineTraceDist'], bRequireClearWall=True)
    return result


states, links = {}, {}


def emit(i, success, failure):
    assert i not in states, ('Original graph has multiple parents; do not silently flatten', i)
    n, p = bt[i], bt[i].get('Properties', {})
    kind = n['Type'].removeprefix('xxNBT')
    row = {'id': 'BT%03d' % i, 'source_export': i, 'source_type': n['Type'], 'source_properties': p, 'success': success, 'failure': failure}
    states[i] = row
    if kind in ('Composite_Selector', 'Composite_Sequence', 'Composite_RandomSelector'):
        children = [index(c) for c in p['Children']]
        row.update(kind='Route', children=children, selection=kind)
        if kind == 'Composite_RandomSelector':
            assert len(children) == 2 and p['RandomRate'] == [1, 1]
            # Engine random condition selects the first branch; the other is
            # the fallback if it cannot be selected. Native RNG remains unverified.
            row['random_threshold'] = p['RandomRate'][0] / sum(p['RandomRate'])
            emit(children[1], success, failure)
            emit(children[0], success, 'BT%03d' % children[1])
        else:
            for pos, child in enumerate(children):
                next_child = 'BT%03d' % children[pos+1] if pos+1 < len(children) else None
                emit(child, next_child or success if kind == 'Composite_Sequence' else success,
                     next_child or failure if kind == 'Composite_Selector' else failure)
    elif kind.startswith('Condition_'):
        row.update(kind='Gate', true='BT%03d' % index(p['TrueChild']), false='BT%03d' % index(p['FalseChild']))
        if kind == 'Condition_CanUseSkill':
            row.update(gate=gate(p), required_skill=skill(p['UseSkill']))
        elif kind == 'Condition_DistanceToTarget':
            row['gate'] = {'MinDistance': p['MinDist'], 'MaxDistance': p['MaxDist']}
        elif kind == 'Condition_Angle':
            row['gate'] = gate({'bCheckRange': False, 'AngleCondition': p['AngleCondition']})
        else: raise ValueError(n['Type'])
        emit(index(p['TrueChild']), success, failure)
        emit(index(p['FalseChild']), success, failure)
    elif kind == 'Task_UseSkill':
        info = p['SkillInfo']
        sid = skill(info['SkillSetting']['SkillInfo'])
        selected = info.get('SelectedSkillSubStateSteps', [])
        forced = next((s['Key'].split('::')[-1] for s in selected if s['Key'].split('::')[-1] != 'None'), None)
        row.update(kind='UseSkill', skill=sid, gate=gate(info, True), selected_steps=selected, forced_step=forced,
            part_conditions=info.get('PartDestructionConditions', []), bForceChange=info.get('bForceChange', False))
    elif kind == 'Task_MoveToTarget':
        row.update(kind='MoveTo', acceptance=p['AcceptanceRadius'], limit=p.get('MoveLimitTime', 0) if p.get('bUseMoveLimitTime') else 0,
            follow_update_distance=p.get('FollowUpdateDistance', 0), gait=p.get('MoveOption', 'NativeDefaultUnconfirmed').split('::')[-1])
    elif kind == 'Task_LockOnMove':
        row.update(kind='LockOnMove', move_settings=p['MoveSetting'])
    else: raise ValueError(n['Type'])
    links[row['id']] = [x for x in (row.get('true'), row.get('false'), success, failure) if x]


emit(index(bt[0]['Properties']['RootNode']), 'CombatRestart', 'CombatRestart')
assert len(states) == len(bt) - 1 == 121
all_ids = {r['id'] for r in states.values()} | {'CombatRestart'}
for destinations in links.values():
    assert all(d in all_ids for d in destinations)
result = {'status': 'planned', 'source': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'original_nodes': len(states), 'states': [states[i] for i in sorted(states)], 'node_types': dict(Counter(r['kind'] for r in states.values())),
    'runtime_asset': '/Game/Monsters/Yetuga/AI/ST_Yetuga_Original',
    'original_graph_links_preserved': True,
    'explicit_adapters': ['Source custom BT success/failure/abort/RNG native semantics unavailable; engine StateTree routing is explicit.',
        'Omitted source range/angle/move defaults are not independently verified.',
        'SelectedSkillSubStateSteps key selects an authored GA entry; native meaning of the map float is unconfirmed.',
        'MoveLimitTime timeout maps to task failure; native result unavailable.',
        'Group1 back-part destruction producer is not present in current gameplay and must remain an explicit fidelity boundary.']}
(OUT / 'YetugaStateTreePlan.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'original_nodes': len(states), 'node_types': result['node_types']}), flush=True)
