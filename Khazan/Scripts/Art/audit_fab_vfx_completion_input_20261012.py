"""Read the staged seven-pack registry and the actual file dependency closure."""
from pathlib import Path
from collections import Counter
import json
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
STAGE = MAIN / 'Saved/ArtStaging/FabVFX_Complete_20261012'
report = {'status': 'running', 'assets': [], 'missing': [], 'errors': []}
try:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(synchronous_search=True)
    registry.scan_paths_synchronous(['/Game'], force_rescan=True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    hard = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=False, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    classes, missing = Counter(), {}
    for data in registry.get_assets_by_path('/Game', recursive=True):
        package = str(data.package_name)
        cls = str(data.asset_class_path.asset_name)
        deps = sorted(str(p) for p in registry.get_dependencies(package, options))
        hd = set(str(p) for p in registry.get_dependencies(package, hard))
        refs = sorted(str(p) for p in registry.get_referencers(package, options))
        report['assets'].append({'package': package, 'object_path': package + '.' + str(data.asset_name), 'name': str(data.asset_name), 'class': cls, 'dependencies': deps, 'hard_dependencies': sorted(hd), 'referencers': refs})
        classes[cls] += 1
        for dependency in deps:
            if not dependency.startswith('/Game/'):
                continue
            rel = dependency.removeprefix('/Game/')
            if not any((STAGE / 'Content' / (rel + ext)).is_file() for ext in ('.uasset', '.umap')):
                missing.setdefault(dependency, []).append({'package': package, 'kind': 'hard' if dependency in hd else 'soft'})
    report.update(status='dependencies_required' if missing else 'passed', classes=dict(classes), assets_count=len(report['assets']), missing=[{'package': p, 'referencers': refs} for p, refs in sorted(missing.items())], engine_version=unreal.SystemLibrary.get_engine_version())
    # Collect the real installed binding names rather than assume a Python API.
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    report['asset_tools_api'] = [n for n in dir(tools) if any(s in n.lower() for s in ('rename', 'redirect', 'fixup'))]
    report['niagara_properties_probe'] = {}
    sample = next(r for r in report['assets'] if r['class'] == 'NiagaraSystem')
    asset = unreal.load_asset(sample['object_path'])
    for name in ('fixed_bounds', 'warmup_time', 'warmup_tick_count', 'warmup_tick_delta', 'emitter_handles'):
        try:
            value = asset.get_editor_property(name)
            report['niagara_properties_probe'][name] = str(value)
        except Exception as error:
            report['niagara_properties_probe'][name] = 'unreadable: ' + str(error)
except Exception:
    report['status'] = 'failed'
    report['errors'].append(traceback.format_exc())
(META / 'InputRegistry.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FAB_VFX_COMPLETION_INPUT ' + json.dumps({k: v for k, v in report.items() if k not in ('assets', 'missing', 'niagara_properties_probe')}), flush=True)
