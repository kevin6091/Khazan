"""Read-only native audit of the relocated Cursed World Partition demo."""
from pathlib import Path
from collections import Counter
import json
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
PROJECT = Path(unreal.Paths.project_dir()).resolve()
LABEL = 'Main' if PROJECT == MAIN else 'Stage'
OLD = '/Game/Cursed_Magic/Maps/Cursed_Magic'
NEW = '/Game/VFX/05_CursedMagic/Demo/Cursed_Magic'
PLAN = json.loads((META / 'RenamePlan.json').read_text())
REMAP = {r['package']: r['new_package'] for r in PLAN}
report = {'status': 'running', 'project': str(PROJECT), 'errors': [], 'packages': [], 'old_references': [], 'missing_references': []}


def normalize(text):
    text = str(text)
    for source in sorted(REMAP, key=len, reverse=True):
        if text == source or text.startswith(source + '.') or text.startswith(source + ':'):
            return REMAP[source] + text[len(source):]
    return text


def vector(v):
    return [v.x, v.y, v.z]


def describe_world(package):
    world = unreal.EditorLoadingAndSavingUtils.load_map(package)
    assert world, ('World load failed', package)
    descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    assert descs is not None, ('World Partition descriptors missing', package)
    rows = []
    for d in descs:
        b = d.get_editor_property('bounds')
        rows.append({
            'name': str(d.get_editor_property('name')),
            'label': str(d.get_editor_property('label')),
            'class': normalize(d.get_editor_property('class').export_text().strip('\"\'')),
            'native_class': d.get_editor_property('native_class').get_path_name(),
            'bounds': {'min': vector(b.min), 'max': vector(b.max), 'valid': b.is_valid},
            'runtime_grid': str(d.get_editor_property('runtime_grid')),
            'spatially_loaded': d.get_editor_property('is_spatially_loaded'),
            'editor_only': d.get_editor_property('actor_is_editor_only'),
            'data_layers': [normalize(x.export_text().strip('\"\'')) for x in d.get_editor_property('data_layer_assets')],
            'package': str(d.get_editor_property('actor_package')),
            'guid': d.get_editor_property('guid').export_text(),
        })
    unreal.WorldPartitionBlueprintLibrary.load_actors([d.get_editor_property('guid') for d in descs])
    actors_by_guid = {}
    identical_transient_duplicates = []
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if not a.get_path_name().startswith(package + '.') or a.get_editor_property('actor_guid').export_text() not in {r['guid'] for r in rows}:
            continue
        rot = a.get_actor_rotation()
        actor_row = {'name': a.get_name(), 'class': normalize(a.get_class().get_path_name()), 'location': vector(a.get_actor_location()), 'rotation': [rot.pitch, rot.yaw, rot.roll], 'scale': vector(a.get_actor_scale3d()), 'niagara_systems': sorted(normalize(c.get_editor_property('asset').get_path_name()) for c in a.get_components_by_class(unreal.NiagaraComponent) if c.get_editor_property('asset'))}
        guid = a.get_editor_property('actor_guid').export_text()
        if guid in actors_by_guid:
            assert actors_by_guid[guid] == actor_row, ('Different loaded actors share a GUID', guid)
            identical_transient_duplicates.append({'guid': guid, 'path': a.get_path_name()})
        else:
            actors_by_guid[guid] = actor_row
    actors = list(actors_by_guid.values())
    (META / (LABEL + 'WPWorldProbe_' + ('Original' if package == OLD else 'Relocated') + '.json')).write_text(json.dumps({'descriptors': rows, 'actors': actors, 'identical_transient_duplicates': identical_transient_duplicates}, indent=2), encoding='utf-8')
    assert len(actors) == len(rows), ('Some descriptor actors did not load', len(rows), len(actors))
    return {'descriptors': sorted(rows, key=lambda r: r['name']), 'actors': sorted(actors, key=lambda r: r['name']), 'classes': dict(Counter(r['class'] for r in rows))}


try:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.search_all_assets(synchronous_search=True)
    reg.scan_paths_synchronous(['/Game/VFX', '/Game/__ExternalActors__/VFX', '/Game/__ExternalObjects__/VFX'], force_rescan=True)
    both = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    hard = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=False, include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    for category in ('__ExternalActors__', '__ExternalObjects__'):
        root = PROJECT / ('Content/' + category + '/VFX/05_CursedMagic/Demo/Cursed_Magic')
        files = sorted(root.rglob('*.uasset'))
        report[category + '_files'] = len(files)
        for file in files:
            package = '/Game/' + file.relative_to(PROJECT / 'Content').with_suffix('').as_posix()
            assets = reg.get_assets_by_package_name(package, include_only_on_disk_assets=True)
            assert assets, ('External package not registered', package)
            hd = {str(x) for x in reg.get_dependencies(package, hard)}
            deps = [str(x) for x in reg.get_dependencies(package, both)]
            report['packages'].append({'package': package, 'classes': [str(a.asset_class_path.asset_name) for a in assets], 'dependencies': deps})
            for dep in deps:
                if dep in REMAP or dep.startswith('/Game/__ExternalActors__/Cursed_Magic/') or dep.startswith('/Game/__ExternalObjects__/Cursed_Magic/'):
                    report['old_references'].append({'package': package, 'dependency': dep})
                if dep.startswith('/Game/') and not any((PROJECT / 'Content' / (dep.removeprefix('/Game/') + e)).is_file() for e in ('.uasset', '.umap')):
                    report['missing_references'].append({'package': package, 'dependency': dep, 'kind': 'hard' if dep in hd else 'soft'})
    if LABEL == 'Stage':
        report['original_world'] = describe_world(OLD)
        (META / 'WPOriginalWorld.json').write_text(json.dumps(report['original_world'], indent=2), encoding='utf-8')
    else:
        report['original_world'] = json.loads((META / 'WPOriginalWorld.json').read_text())
    report['relocated_world'] = describe_world(NEW)
    original = report['original_world']
    relocated = report['relocated_world']
    assert original['actors'] == relocated['actors'], 'Loaded actor transforms/classes/Niagara selections differ'
    # The engine regenerates editor streaming bounds and resolves redirected
    # Blueprint descriptor classes when saving. Actual loaded actor classes,
    # transforms and Niagara selections above must remain exactly equal.
    relocated_by_name = {r['name']: r for r in relocated['descriptors']}
    report['derived_descriptor_changes'] = [{'name': r['name'], 'field': k, 'original': r[k], 'relocated': relocated_by_name[r['name']][k]} for r in original['descriptors'] for k in ('bounds', 'class') if r[k] != relocated_by_name[r['name']][k]]
    actors_by_name = {r['name']: r for r in relocated['actors']}
    assert all(r['class'] == actors_by_name[r['name']]['class'] for r in relocated['descriptors']), 'Saved descriptor class does not match loaded actor'
    def semantic(rows):
        return [{k: v for k, v in r.items() if k not in ('package', 'guid', 'bounds', 'class')} for r in rows]
    assert semantic(original['descriptors']) == semantic(relocated['descriptors']), 'Actor descriptor authored values differ'
    assert report['__ExternalActors___files'] == len(relocated['descriptors']), 'Duplicate/unregistered actor packages remain'
    assert not report['old_references'] and not report['missing_references']
    report.update(status='passed', actors=len(relocated['actors']), authored_actor_values_equal=True)
except Exception:
    report['status'] = 'failed'
    report['errors'].append(traceback.format_exc())
(META / (LABEL + 'WPDemoAudit.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VFX_WP_DEMO_AUDIT ' + json.dumps({k: v for k, v in report.items() if k not in ('packages', 'original_world', 'relocated_world', 'derived_descriptor_changes')}, default=str), flush=True)
if report['status'] != 'passed':
    raise RuntimeError('VFX WP demo audit failed; see ' + LABEL + 'WPDemoAudit.json')
