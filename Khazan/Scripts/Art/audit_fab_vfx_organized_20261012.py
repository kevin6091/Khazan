"""Fresh-load organized assets, check paths/references, and compare recorded values."""
from pathlib import Path
from collections import Counter
import json
import runpy
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
PROJECT = Path(unreal.Paths.project_dir()).resolve()
IS_MAIN = PROJECT == MAIN
LABEL = 'Main' if IS_MAIN else 'Stage'
PLAN = json.loads((META / 'RenamePlan.json').read_text())
BEFORE = json.loads((META / 'PropertiesBefore.json').read_text())
BASE_MISSING = {r['package'] for r in json.loads((META / 'InputRegistry.json').read_text())['missing']}
report = {'status': 'running', 'project': str(PROJECT), 'assets': [], 'errors': [], 'old_references': [], 'missing_hard_references': [], 'remaining_source_soft_refs': [], 'classes': {}, 'value_checks': 0}


def value(v):
    if isinstance(v, unreal.Box):
        return {'min': [v.min.x, v.min.y, v.min.z], 'max': [v.max.x, v.max.y, v.max.z], 'valid': v.is_valid}
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    return str(v)


try:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.search_all_assets(synchronous_search=True)
    reg.scan_paths_synchronous(['/Game/VFX', '/Game/__ExternalActors__/VFX', '/Game/__ExternalObjects__/VFX'], force_rescan=True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    hard = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=False, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    old_names = {r['package'] for r in PLAN}
    classes = Counter()
    for index, row in enumerate(PLAN):
        item = {'package': row['new_package'], 'class': row['class']}
        try:
            asset = unreal.load_asset(row['new_object_path'])
            assert asset and asset.get_class().get_name() == row['class'], ('Load/class failure', row)
            item['loaded'] = True
            for prop, expected in BEFORE.get(row['package'], {}).items():
                if isinstance(expected, dict) and 'unreadable' in expected:
                    continue
                observed = value(asset.get_editor_property(prop))
                assert observed == expected, ('Value changed', row['new_package'], prop, expected, observed)
                report['value_checks'] += 1
            deps = [str(x) for x in reg.get_dependencies(row['new_package'], options)]
            hd = {str(x) for x in reg.get_dependencies(row['new_package'], hard)}
            item['dependencies'] = deps
            for dep in deps:
                if dep in old_names:
                    report['old_references'].append({'package': row['new_package'], 'dependency': dep, 'kind': 'hard' if dep in hd else 'soft'})
                if dep.startswith('/Game/'):
                    exists = any((PROJECT / 'Content' / (dep.removeprefix('/Game/') + ext)).is_file() for ext in ('.uasset', '.umap'))
                    if not exists:
                        finding = {'package': row['new_package'], 'dependency': dep}
                        if dep in hd:
                            report['missing_hard_references'].append(finding)
                        elif dep in BASE_MISSING:
                            report['remaining_source_soft_refs'].append(finding)
                        else:
                            report['errors'].append({'new_missing_soft_ref': finding})
            classes[row['class']] += 1
        except Exception:
            item['error'] = traceback.format_exc()
            report['errors'].append(item)
        report['assets'].append(item)
        if index % 25 == 24:
            asset = None
            unreal.SystemLibrary.collect_garbage()
        if index % 100 == 0:
            report.update(processed=index+1, classes=dict(classes))
            (META / (LABEL + 'OrganizedAudit.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
            print('VFX_ORGANIZED_AUDIT ' + str(index+1) + '/' + str(len(PLAN)), flush=True)
    actual = reg.get_assets_by_path('/Game/VFX', recursive=True)
    report.update(classes=dict(classes), processed=len(PLAN), vfx_registry_classes=dict(Counter(str(d.asset_class_path.asset_name) for d in actual)), redirectors=[str(d.package_name) for d in actual if str(d.asset_class_path.asset_name) == 'ObjectRedirector'])
    report['status'] = 'passed' if not any(report[k] for k in ('errors', 'old_references', 'missing_hard_references', 'redirectors')) else 'failed'
except Exception:
    report['status'] = 'failed'
    report['errors'].append({'error': traceback.format_exc()})
(META / (LABEL + 'OrganizedAudit.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VFX_ORGANIZED_FINAL ' + json.dumps({k: v for k, v in report.items() if k not in ('assets', 'remaining_source_soft_refs', 'old_references')}), flush=True)
if report['status'] != 'passed':
    raise RuntimeError('Organized VFX library audit failed')
if '-VFXWorldPartition' in unreal.SystemLibrary.get_command_line():
    runpy.run_path(str(MAIN / 'Scripts/Art/audit_fab_vfx_wp_demo_20261012.py'))
