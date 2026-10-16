"""Read only the saved animation library and selected original reaction composites."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Content/_Art/Enemies/HeinMach/Metadata'
OUT = ROOT / 'Metadata/MonsterIdle_20261007'
OUT.mkdir(parents=True, exist_ok=True)
with (META / 'AnimationStructure_20260909/AnimationLibrary.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
families = {
    'Swordsman': ('EmpireSword', 'EmpireSword', [('Guard', 'Guard_01'), ('Basic', '03'), ('Search', 'Search_01'), ('Sit', 'Sit_01'), ('Talk01', 'Talk_01'), ('Talk02', 'Talk_02')]),
    'SwordShield': ('Empire_SwordShield', 'EmpireSwordShield', [('Basic', '03'), ('Sit', 'Sit_01')]),
    'HeavySwordsman': ('Empire_SwordHArmor', 'EmpireSwordHArmor', [('Basic', '03'), ('Search', 'Search_01'), ('Sit', 'Sit_01')]),
    'HalberdElite': ('EmpireHalberd_E', 'EmpireHalberd', [('Basic', '01'), ('Guard', 'Guard_01'), ('Search', 'Search_01'), ('Talk01', 'Talk_01'), ('Talk02', 'Talk_02')]),
}
plan = []
for family, (folder, prefix, pairs) in families.items():
    available = {Path(r['PlaybackAsset']).name: r for r in rows if r['Family'] == family}
    routines = []
    for name, suffix in pairs:
        category, number = suffix.rsplit('_', 1) if '_' in suffix else ('', suffix)
        stem = f'AC_{prefix}_Basic_' + (category + '_' if category else '')
        steps = []
        for phase in ('Loop', 'End'):
            clip_name = f'{stem}{phase}_{number}'
            row = available['A_EN_PLAY_' + clip_name]
            source = META / 'Expansion_20260909/Source' / (row['OriginalPackage'] + '.json')
            original = json.loads(source.read_text(encoding='utf-8-sig'))
            composite = next(o for o in original if o['Type'] == 'AnimComposite')
            track = composite['Properties']['AnimationTrack']['AnimSegments']
            steps.append({'phase': phase, 'playback': row['PlaybackAsset'], 'seconds': float(row['Seconds']),
                          'rate_scale': float(row['RateScale']), 'fps': row['FPS'],
                          'original_file': str(source.relative_to(ROOT)).replace('\\', '/'),
                          'original_segments': track})
        routines.append({'id': name, 'role': 'Talk01' if name == 'Talk01' else 'Talk02' if name == 'Talk02' else 'Solo', 'steps': steps})
    plan.append({'family': family, 'routines': routines})
(OUT / 'IdleAuthoringPlan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
for entry in plan:
    print(entry['family'], ', '.join(r['id'] for r in entry['routines']))
