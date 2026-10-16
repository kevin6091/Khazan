"""Purpose names from existing source identities; never discard the source mapping."""
from pathlib import Path
from collections import Counter, defaultdict
import json, re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/EnemyAnimationOrganization_20261007'
inv = json.loads((OUT / 'Inventory.json').read_text(encoding='utf-8'))

def label(asset):
    name = Path(asset).name.removeprefix('A_EN_PLAY_')
    name = re.sub(r'^(?:(?:AC|CA|M|EN|Boss)_)+', '', name)
    name = re.sub(r'^(?:Empire_?SwordHArmor|Empire_?SwordShield|Empire_?Sword|ESwordHArmor|EmpSword|EmpSwd|EmpireHalberd(?:_E)?|Halberd|Yetuga|ApesStoneHandElite|ApesStoneHand_E)(?:_E)?_', '', name)
    name = re.sub(r'_[0-9a-f]{8}$', '', name)
    name = name.replace('YetugaRock_', 'IceRock_')
    return name

def classify(name, package):
    low = name.lower()
    if low.startswith('lod_pose'): return 'Pose'
    if low.startswith('icerock'): return 'Prop'
    if low.startswith('ballista'): return 'Interaction'
    if re.search(r'(^|_)(die|death)', low): return 'Death'
    if low.startswith('downupperslash'): return 'Attack'
    if re.search(r'(damage|damfinal|parried|justguardreaction|groggy|sick|disease|addweak|^down|^getup|^fall)', low): return 'Damage'
    if re.search(r'(vigilant|freakout|lookaround|watchout|roar|^fear)', low): return 'Alert'
    if low.startswith('basic') or low.startswith('idle') or low.startswith('nobattlepain') or low == 'social': return 'Idle'
    if low.startswith('staminarecover'): return 'Recovery'
    if re.search(r'(guardcounter|backdashcounter)', low): return 'Attack'
    if low.startswith('guard') or low.startswith('shieldguard'): return 'Guard'
    if re.search(r'(weapon|equip|unarmed|armed|footsword)', low): return 'Equip'
    if 'lockonwalk' in low or 'lockonmove' in low: return 'Locomotion'
    if re.search(r'(dempsey|closegrab|fastball|icebreath|armageddon)', low): return 'Attack'
    if re.search(r'(attack|atk|slash|smash|pierce|swing|sting|push|punch|kick|crash|throw|grip|tackle|bite|shoot|stomp|rush|strike|sweep|combo)', low): return 'Attack'
    if re.search(r'(lockon|^walk|^run|^sprint|^stand|^turn|^dash|^dodge|^move|^backmov|^backjump|^fastmove|^sidemove|^step|^jump|^land|^climb)', low): return 'Locomotion'
    if re.search(r'(cine|cinematic|^cs_|^sc_|bossintro)', low) or '/cinema' in package.lower(): return 'Cinematic'
    return None

art = [r for r in inv['rows'] if r['scope'] == 'ArtLibrary']
groups = defaultdict(list)
unknown = []
for row in art:
    row['label'] = label(row['old'])
    row['category'] = classify(row['label'], row['original_package'])
    if not row['category']:
        unknown.append(dict(family=row['family'], label=row['label'], package=row['original_package']))
        continue
    semantic = re.sub(r'^Basic_', '', row['label']) if row['category'] == 'Idle' else row['label']
    semantic = re.sub(r'^Damage(?=[A-Z])', 'Damage_', semantic)
    semantic = re.sub(r'^DamFinalblow', 'Damage_FinalBlow', semantic, flags=re.I)
    row['name'] = semantic if semantic.startswith(row['category'] + '_') else row['category'] + '_' + semantic
    groups[(row['family'], row['category'], row['name'])].append(row)
for rows in groups.values():
    if len(rows) > 1:
        for row in rows:
            row['name'] += '_Original' if row['derivation'] == 'DirectOriginalTimeline' else '_Composite'
        duplicated = Counter(row['name'] for row in rows)
        for name, count in duplicated.items():
            if count > 1:
                variants = sorted((r for r in rows if r['name'] == name), key=lambda r:r['old'])
                for index, row in enumerate(variants, 1): row['name'] += f'_Variant{index:02}'
for row in art:
    if row.get('name'):
        row['new'] = row['old'].split('/Animations/')[0] + '/Animations/' + row['category'] + '/' + row['name']
lookup = {(r['family'], Path(r['old']).name):r for r in art}
game = []
for row in inv['rows']:
    if row['scope'] != 'Gameplay': continue
    source = lookup[(row['family'], Path(row['old']).name)]
    row.update({k:source[k] for k in ['label','category','name','new'] if k in source})
    if row.get('new'):
        row['new'] = row['old'].split('/Animations/InGame/')[0] + '/Animations/InGame/' + row['category'] + '/' + row['name']
    game.append(row)
plan = dict(status='NeedsClassification' if unknown else 'PreflightReady', rows=art+game, unknown=unknown)
(OUT / 'RenamePlan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(unknown=unknown, categories=dict(Counter(r.get('category') or 'Unknown' for r in art)),
                      attacks={f:[r['label'] for r in art if r['family']==f and r.get('category')=='Attack'] for f in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite']}), indent=2))
