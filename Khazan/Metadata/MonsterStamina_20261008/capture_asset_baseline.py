import hashlib, json, pathlib, shutil
MAIN = pathlib.Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterWork_20261006' / 'Khazan'
OUT = MAIN / 'Metadata/MonsterStamina_20261008'
target = OUT / 'AssetBaseline.json'
if target.exists():
    raise RuntimeError('Preserve the existing pre-authoring baseline')
plan = json.loads((OUT / 'AnimationPlan.json').read_text(encoding='utf-8'))
paths, sources = set(), set()
for clip in plan['player_clips']:
    paths.add(clip['proposed_duplicate_path']); sources.add(clip['current_path'])
for direction in plan['player_front_back_montages']:
    paths.add('/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_Brutal' + direction['direction'])
for family in plan['families']:
    name = family['family']; base = '/Game/Monsters/' + name
    paths.add(base + '/Data/DA_Character_' + name)
    paths.add(base + '/Animations/AM_Exhaustion')
    for section in family['exhaustion']['sections']:
        source = section['clip']['current_path']; sources.add(source)
        paths.add(base + '/Animations/InGame/Damage/' + source.rsplit('/', 1)[-1])
    for direction in family['brutal_victim']:
        paths.add(base + '/Animations/AM_BrutalVictim' + direction['direction'])
        for section in direction['sections']:
            source = section['clip']['current_path']; sources.add(source)
            paths.add(base + '/Animations/InGame/Damage/' + source.rsplit('/', 1)[-1])
paths.update(['/Game/Monsters/Effects/GE_DeadState', '/Game/Monsters/Effects/GE_MonsterStaminaPolicy',
    '/Game/Data/PDA_AssetData', '/Game/Data/Character/DA_Character_Player'])
# Exact existing Player Definition path is resolved from the authoring helper below.
tool = (MAIN / 'Scripts/Engineering/MonsterStaminaAuthorEditor.cpp').read_text(encoding='utf-8')
import re
for p in re.findall(r'TEXT\("(/Game/[^"\n]+)"\)', tool):
    if 'DA_Character' in p and not p.endswith('_'):
        paths.add(p)
for name, art in [('ApesStoneHandElite', '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite'),
                  ('Yetuga', '/Game/_Art/Enemies/HeinMach/Bosses/Yetuga')]:
    paths.add(art + '/Skeletons/SKEL_EN_' + name)
    paths.add('/Game/Bluprints/Monsters/BP_Monster_' + name)
    paths.add('/Game/Monsters/' + name + '/Animations/ABP_' + name)
    idle = 'Locomotion_Stand_F_Original_Variant02' if name.startswith('Apes') else 'Locomotion_Stand_F'
    paths.add('/Game/Monsters/' + name + '/Animations/InGame/Idle/' + idle)
    sources.add(art + '/Animations/Locomotion/' + idle)
for name in ['Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite']:
    folder = MAIN / 'Content/Monsters' / name / 'Abilities'
    if folder.exists():
        for p in folder.glob('*.uasset'):
            paths.add('/Game/' + p.relative_to(MAIN / 'Content').with_suffix('').as_posix())
def disk(root, package):
    return root / 'Content' / (package.removeprefix('/Game/') + '.uasset')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
rows = []
for package in sorted(paths | sources):
    a, b = disk(MAIN, package), disk(WORK, package)
    row = dict(package=package, main_before=sha(a), work_before=sha(b), authored_candidate=package in paths)
    if a.is_file() and package in paths:
        backup = OUT / 'BeforeAssets' / a.relative_to(MAIN)
        backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(a, backup)
    rows.append(row)
target.write_text(json.dumps(dict(main=str(MAIN), work=str(WORK), rows=rows), indent=2), encoding='utf-8')
print(json.dumps(dict(target=str(target), packages=len(rows), source_clips=len(sources), candidates=len(paths))))
