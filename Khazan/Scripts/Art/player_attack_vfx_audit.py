"""Read current player combat assets in a task-owned commandlet. No asset writes."""
from pathlib import Path
import hashlib
import json
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008/CurrentAssets'
OUT.mkdir(parents=True, exist_ok=True)

def prop(obj, key):
    return obj.get_editor_property(key)

def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    if hasattr(value, 'export_text'):
        return value.export_text()
    return str(value)

def export(obj):
    filename = OUT / (obj.get_name() + '.t3d')
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(filename)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(task), obj.get_path_name()
    return str(filename.relative_to(ROOT))

report = {'status': 'running', 'asset_saves': False, 'project': str(ROOT)}
try:
    definition = unreal.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    combo = unreal.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
    assert definition and combo
    report['grants'] = [x.export_text() for x in prop(definition, 'initial_ability_grants')]
    report['nodes'] = []
    montages = {}
    for node in prop(combo, 'nodes'):
        montage = prop(node, 'montage')
        report['nodes'].append({'node': str(prop(node, 'node_id')), 'section': str(prop(node, 'section_name')),
                                'montage': serial(montage), 'raw': node.export_text()})
        if montage:
            montages[montage.get_path_name()] = montage
    report['montages'] = []
    report['sequences'] = []
    sequences = {}
    for path, montage in montages.items():
        row = {'path': path, 'sections': [str(montage.get_section_name(i)) for i in range(montage.get_num_sections())],
               'notifies': [n.export_text() for n in unreal.AnimationLibrary.get_animation_notify_events(montage)],
               'export': export(montage), 'metadata': {str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_metadata_tag_values(montage).items()}}
        package_file = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
        row['sha256'] = hashlib.sha256(package_file.read_bytes()).hexdigest()
        report['montages'].append(row)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=False)
    for path in montages:
        for package in registry.get_dependencies(path.split('.')[0], options):
            asset = unreal.load_asset(str(package))
            if isinstance(asset, unreal.AnimSequence):
                sequences[asset.get_path_name()] = asset
    for path, sequence in sequences.items():
        report['sequences'].append({'path': path, 'length': sequence.get_play_length(), 'rate_scale': prop(sequence, 'RateScale'),
                                    'metadata': {str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_metadata_tag_values(sequence).items()},
                                    'notifies': [n.export_text() for n in unreal.AnimationLibrary.get_animation_notify_events(sequence)]})
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    unreal.log_error(report['error'])
(OUT / 'CurrentPlayerAssets.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('KZ_PLAYER_ATTACK_VFX_AUDIT_' + report['status'].upper(), flush=True)
