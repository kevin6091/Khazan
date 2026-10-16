"""UE registry dependency closure for the exact staged vendor packages."""
from pathlib import Path
from collections import Counter
import json
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012'
STAGE = MAIN / 'Saved/ArtStaging/FabVFX_20261012'
report = {'status': 'running', 'errors': [], 'assets': [], 'missing_game_dependencies': [], 'external_dependencies': [], 'classes': {}}
try:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(synchronous_search=True)
    registry.scan_paths_synchronous(['/Game'], force_rescan=True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    hard_options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=False, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    data = registry.get_assets_by_path('/Game', recursive=True)
    classes = Counter()
    package_names = set()
    external = set()
    missing = {}
    for asset in data:
        package = str(asset.package_name)
        class_name = str(asset.asset_class_path.asset_name)
        classes[class_name] += 1
        package_names.add(package)
        dependencies = sorted(str(p) for p in registry.get_dependencies(package, options))
        hard_dependencies = {str(p) for p in registry.get_dependencies(package, hard_options)}
        report['assets'].append({'package': package, 'object_path': package + '.' + str(asset.asset_name), 'class': class_name, 'dependencies': dependencies, 'hard_dependencies': sorted(hard_dependencies)})
        for dependency in dependencies:
            if dependency.startswith('/Game/'):
                relative = dependency[len('/Game/'):]
                if not any((STAGE / 'Content' / (relative + ext)).is_file() for ext in ('.uasset', '.umap')):
                    missing.setdefault(dependency, []).append({'package': package, 'kind': 'hard' if dependency in hard_dependencies else 'soft'})
            else:
                external.add(dependency)
    manifest = json.loads((META / 'StageManifest.json').read_text(encoding='utf-8'))
    expected = {'/Game/' + str(Path(r['relative_path']).with_suffix('')).replace('\\', '/') for r in manifest if Path(r['relative_path']).suffix.lower() in ('.uasset', '.umap')}
    report.update(status='dependencies_required' if missing else 'passed', classes=dict(classes), registered_packages=len(package_names), expected_packages=len(expected), not_registered=sorted(expected-package_names), missing_game_dependencies=[{'package': p, 'referencers': refs} for p, refs in sorted(missing.items())], external_dependencies=sorted(external), engine_version=unreal.SystemLibrary.get_engine_version())
    source_index = json.loads((META / 'SourcePackageIndex.json').read_text(encoding='utf-8'))
    if missing and all(not source_index.get(p) and all(r['kind'] == 'soft' for r in refs) for p, refs in missing.items()):
        report['status'] = 'passed_with_source_soft_reference_warnings'
    report['niagara_api'] = {name: [m for m in dir(getattr(unreal, name)) if any(s in m.lower() for s in ('compile', 'valid', 'ready', 'simulation'))] for name in ('NiagaraSystem', 'NiagaraComponent')}
    if report['not_registered']:
        report['status'] = 'registration_failed'
except Exception:
    report['status'] = 'failed'
    report['errors'].append(traceback.format_exc())
(META / 'StageDependencies.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('FAB_VFX_DEPENDENCIES ' + json.dumps({k: v for k, v in report.items() if k not in ('assets', 'external_dependencies', 'missing_game_dependencies')}), flush=True)
