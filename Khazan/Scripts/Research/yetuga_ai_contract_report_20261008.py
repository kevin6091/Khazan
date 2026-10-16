"""Build a read-only evidence index for the original custom Yetuga AI graph."""
from collections import Counter
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal'

def read(name):
    return json.loads((OUT / (name + '.json')).read_text(encoding='utf-8-sig'))

def short(value):
    if isinstance(value, dict):
        if 'ObjectPath' in value:
            return value['ObjectPath'].split('/')[-1]
        if 'AssetPathName' in value:
            return value['AssetPathName'].split('/')[-1]
        return {k: short(v) for k, v in value.items()}
    if isinstance(value, list):
        return [short(v) for v in value]
    return value

tree = read('BT_Yetuga')
infos = read('SkillAvailability')
conditions = []
for i, e in enumerate(tree):
    if e['Type'] == 'xxNBTCondition_CanUseSkill':
        p = e.get('Properties', {})
        conditions.append({'export_index': i, 'export_name': e['Name'],
                           'fields': {k: v for k, v in p.items()
                                      if k not in ('NodeID', 'NodeHash', 'ExecutionIndex', 'TreeDepth', 'NodePosition')}})
summary = []
for info in infos:
    p = info['properties']
    summary.append({'skill': info['skill_info'],
                    'name': p.get('SkillName', {}).get('SourceString'),
                    'availability_fields': {k: v for k, v in p.items()
                          if k in ('SkillStatePtr', 'EndCooltime', 'BattleStartCooltime',
                                   'InputConditions', 'SkillStateSubType', 'bEnableParringSkill',
                                   'StatusChangeInfoList', 'SpellInfoList', 'CostList')},
                    'input_condition_exports': info['conditions']})
report = {
    'scope': 'Original cooked serialized properties; no native game execution or UE edits',
    'original_package': tree[0]['Package'],
    'node_count_excluding_asset_export': len(tree) - 1,
    'node_types': dict(Counter(e['Type'] for e in tree[1:])),
    'root_export_index': 2,
    'root_children_export_indices': [37, 56],
    'distance_partition_nodes': [
        {'index': 58, 'raw_min': 0, 'raw_max': 800},
        {'index': 55, 'raw_min': 799, 'raw_max': 2500},
        {'index': 56, 'raw_min': 0, 'raw_max': 500}
    ],
    'rear_angle_nodes': [
        {'index': 13, 'base_degree': 180, 'left_degree': 70, 'right_degree': 70},
        {'index': 12, 'base_degree': 180, 'left_degree': 70, 'right_degree': 70}
    ],
    'near_front_can_use_chain': [40, 25, 49, 53, 45, 14, 46, 52, 38, 16, 22, 24, 39, 20],
    'middle_front_can_use_chain': [43, 23, 50, 44, 26, 36, 47, 48, 15, 31],
    'can_use_skill_conditions': conditions,
    'skill_info_summary': summary,
    'limits': [
        'Custom xxNBehaviorTree is not the stock Unreal UBehaviorTree implementation.',
        'Serialized child/true/false order is verified; native reevaluation/interrupt/result semantics are unavailable.',
        'Range fields remain raw custom-engine distances; no unsupported conversion to metres.',
        'BT StatusConditions bCompareRate=false with raw HP values 65/60/50 must not be labelled percent.',
        'SI omitted ratio defaults and custom status unit scaling are unresolved.',
        'This archive is identified by package SHA, not a verified public game patch version.'
    ]
}
(OUT / 'AIContractSummary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('Nodes', len(tree)-1, 'CanUseSkill conditions', len(conditions), 'SI', len(summary))
for row in summary:
    f = row['availability_fields']
    print(row['skill'], row['name'], 'end_cooldown=', f.get('EndCooltime'),
          'battle_start_cooldown=', f.get('BattleStartCooltime'), 'parry=', f.get('bEnableParringSkill'))

