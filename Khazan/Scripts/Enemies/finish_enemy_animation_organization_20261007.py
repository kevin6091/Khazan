"""Finish scoped gameplay montage names and immutable-source audit pairs."""
from pathlib import Path
import json, unreal

WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
OUT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/EnemyAnimationOrganization_20261007')
prefixes = dict(Swordsman='EmpireSword_', SwordShield='Empire_SwordShield_',
                HeavySwordsman='EmpireSwordHArmor_', HalberdElite='EmpireHalberd_E_')
rows = []
for family, prefix in prefixes.items():
    folder = '/Game/Monsters/' + family + '/Animations'
    for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
        asset = unreal.load_asset(path)
        if not isinstance(asset, unreal.AnimMontage) or not asset.get_name().startswith('AM_'):
            continue
        label = asset.get_name().removeprefix('AM_').removeprefix(prefix)
        category = 'Idle' if label.startswith('Idle_') else 'Alert' if label == 'Alert' else 'Attack'
        name = label if category != 'Attack' else 'Attack_' + label
        old = asset.get_path_name().split('.')[0]
        new = folder + '/' + category + '/Montages/' + name
        relative = 'Content/' + old.removeprefix('/Game/') + '.uasset'
        assert (OUT / 'Before' / relative).is_file(), old
        assert not unreal.EditorAssetLibrary.does_asset_exist(new), new
        rows.append(dict(family=family, category=category, old=old, new=new))
assert len(rows) == 33, len(rows)
(OUT / 'MontageRenamePlan.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
for row in rows:
    assert unreal.EditorAssetLibrary.rename_asset(row['old'], row['new']), row
    assert unreal.EditorAssetLibrary.save_asset(row['new'], only_if_is_dirty=False), row
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
folder = WORK / 'Saved/EnemyAnimationOrganization'
with (folder / 'OldAssets.txt').open('a', encoding='utf-8') as stream:
    stream.write(''.join(row['old'] + '\n' for row in rows))
pairs = {line.split('|')[0]: line for line in (folder / 'AssetPairs.tsv').read_text(encoding='utf-8').splitlines()}
patterns = json.loads((OUT / 'AttackExpansionPlan.json').read_text(encoding='utf-8'))
for pattern in patterns:
    for step in pattern['steps']:
        current = step['game_destination']
        assert unreal.EditorAssetLibrary.does_asset_exist(current), current
        pairs.setdefault(current, current + '|' + step['original_playback'])
(folder / 'AssetPairs.tsv').write_text('\n'.join(pairs.values()) + '\n', encoding='utf-8')
(OUT / 'MontageRenameApplied.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print(json.dumps(dict(montages=len(rows), sequence_audit_pairs=len(pairs))))
