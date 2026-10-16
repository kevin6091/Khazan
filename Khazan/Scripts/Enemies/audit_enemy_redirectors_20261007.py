"""Read only remaining scoped redirectors in a fresh independent commandlet."""
from pathlib import Path
import json, unreal
work = Path(unreal.Paths.project_dir()).resolve()
assert work == Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
out = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/EnemyAnimationOrganization_20261007')
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True)
rows = []
packages = set()
for old in (work / 'Saved/EnemyAnimationOrganization/OldAssets.txt').read_text(encoding='utf-8').splitlines():
    if not (work / ('Content/' + old.removeprefix('/Game/') + '.uasset')).exists():
        continue
    refs = [str(x) for x in registry.get_referencers(old, options)]
    asset = unreal.load_asset(old)
    rows.append(dict(old=old, resolved=asset.get_path_name() if asset else None, referencers=refs))
    packages.add(old)
    packages.update(refs)
    if asset:
        packages.add(asset.get_path_name().split('.')[0])
(out / 'RemainingRedirectors.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
(work / 'Saved/EnemyAnimationOrganization/RemainingFixupPackages.txt').write_text('\n'.join(sorted(packages)) + '\n', encoding='utf-8')
print(json.dumps(rows))
