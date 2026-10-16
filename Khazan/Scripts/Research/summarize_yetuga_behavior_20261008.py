"""Resolve original cooked Yetuga graph and skill records without UE execution."""
from pathlib import Path
import json

ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal'
SKIP = {'NodeID', 'NodeHash', 'ExecutionIndex', 'TreeDepth', 'NodePosition'}


def read(name):
    return json.loads((OUT / (name + '.json')).read_text(encoding='utf-8-sig'))


def short(value):
    if isinstance(value, dict):
        if 'ObjectPath' in value:
            return value['ObjectPath'].split('/')[-1]
        if 'AssetPathName' in value:
            return value['AssetPathName'].split('/')[-1]
        return {k: short(v) for k, v in value.items() if k not in SKIP}
    if isinstance(value, list):
        return [short(v) for v in value]
    return value


tree = read('BT_Yetuga')
root_index = int(tree[0]['Properties']['RootNode']['ObjectPath'].rsplit('.', 1)[1])
graph = []
for index, export in enumerate(tree):
    if index:
        graph.append(dict(index=index, name=export['Name'], type=export['Type'],
                          properties=export.get('Properties', {})))
(OUT / 'BehaviorGraph.json').write_text(json.dumps(dict(root_index=root_index, nodes=graph), ensure_ascii=False, indent=2), encoding='utf-8')
lines = []


def walk(index, label='', depth=0, ancestors=()):
    if index in ancestors:
        lines.append('  '*depth + label + 'cycle ' + str(index))
        return
    export = tree[index]
    props = export.get('Properties', {})
    children = []
    for key in ('Children', 'TrueChild', 'FalseChild', 'Child', 'ChildNode'):
        refs = props.get(key, [])
        if isinstance(refs, dict):
            refs = [refs]
        for n, ref in enumerate(refs):
            if ref and ref.get('ObjectPath', '').rsplit('.', 1)[0].endswith('/BT_Yetuga'):
                children.append((key + (str(n) if key == 'Children' else ''), int(ref['ObjectPath'].rsplit('.', 1)[1])))
    info = {k: v for k, v in props.items() if k not in SKIP and k not in ('Children', 'TrueChild', 'FalseChild', 'Child', 'ChildNode')}
    lines.append('  '*depth + label + f' [{index}] ' + export['Type'] + ' ' + json.dumps(short(info), ensure_ascii=False))
    for key, child in children:
        walk(child, key, depth+1, ancestors+(index,))


walk(root_index)
(OUT / 'BehaviorTreeResolved.txt').write_text('\n'.join(lines), encoding='utf-8')
skills = []
for file in sorted(OUT.glob('SB_*.json')):
    exports = read(file.stem)
    cdos = [e for e in exports if e.get('Name', '').startswith('Default__')]
    if not cdos:
        continue
    props = cdos[0].get('Properties', {})
    states = []
    for pair in props.get('SubStateInfos', []):
        value = pair['Value']
        states.append(dict(step=pair['Key'], next=value.get('NextSubStateStep'), animation=value.get('SkillAnimation'),
                           play_rate=value.get('AnimPlayRate'), loops=value.get('AnimLoopCount'),
                           event_map=value.get('SkillEventMap', []), specials=value.get('SpecialSubStateInfo'),
                           special_animation=value.get('SpecialSkillAnimInfo'),
                           parry_override=value.get('bUseEnableParringStep'), parry_enabled=value.get('bEnableParringStep')))
    skills.append(dict(skill=file.stem, cdo_properties=props, steps=states,
                       functions_conditions=[e for e in exports if e is not cdos[0] and e['Type'] != 'BlueprintGeneratedClass']))
(OUT / 'SkillStepsBranches.json').write_text(json.dumps(skills, ensure_ascii=False, indent=2), encoding='utf-8')
infos = []
for file in sorted(OUT.glob('SI_*.json')):
    exports = read(file.stem)
    info = next((e for e in exports if e['Type'] == 'xxSkillInfo'), None)
    if info:
        infos.append(dict(skill_info=file.stem, properties=info.get('Properties', {}),
                          conditions=[e for e in exports if e is not info]))
(OUT / 'SkillAvailability.json').write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding='utf-8')
print('Graph nodes:', len(graph), 'SB:', len(skills), 'SI:', len(infos))
print('ROOT PRIORITY')
for line in lines[:7]:
    print(line)
print('STEPS')
for skill in skills:
    print(skill['skill'], [(s['step'].split('::')[-1], s['next'].split('::')[-1] if s['next'] else None, short(s['animation']), len(s['event_map'])) for s in skill['steps']])
print('SPECIAL INPUT CONDITIONS')
for info in infos:
    if info['conditions']:
        print(info['skill_info'], short(info['conditions']))
