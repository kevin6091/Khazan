"""Use Unreal rename APIs in the isolated library, with scoped value snapshots."""
from pathlib import Path
import json
import re
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
STAGE = MAIN / 'Saved/ArtStaging/FabVFX_Complete_20261012'
assert Path(unreal.Paths.project_dir()).resolve() == STAGE
PLAN = json.loads((META / 'RenamePlan.json').read_text())
PILOT = '-VFXPilot' in unreal.SystemLibrary.get_command_line()
report = {'status': 'running', 'pilot': PILOT, 'renamed': [], 'errors': [], 'property_checks': []}
BEFORE_FILE = META / 'PropertiesBefore.json'
before = json.loads(BEFORE_FILE.read_text()) if BEFORE_FILE.exists() else {}


def value(v):
    if isinstance(v, unreal.Box):
        return {'min': [v.min.x, v.min.y, v.min.z], 'max': [v.max.x, v.max.y, v.max.z], 'valid': v.is_valid}
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    return str(v)


def snapshot(asset, cls):
    props = {
        'NiagaraSystem': ('fixed_bounds', 'warmup_time', 'warmup_tick_count', 'warmup_tick_delta'),
        'Material': ('blend_mode', 'two_sided', 'shading_model', 'opacity_mask_clip_value'),
        'Texture2D': ('srgb', 'compression_settings', 'lod_group'),
        'AnimSequence': ('sequence_length', 'rate_scale', 'enable_root_motion', 'force_root_lock', 'root_motion_root_lock'),
    }.get(cls, ())
    out = {}
    for prop in props:
        try:
            out[prop] = value(asset.get_editor_property(prop))
        except Exception as error:
            out[prop] = {'unreadable': str(error)}
    return out


try:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(synchronous_search=True)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    if PILOT:
        selected = []
        for cls, root in [('NiagaraSystem', 'ARPGEssentials'), ('NiagaraSystem', 'NiagaraVFXBundle'), ('Material', 'DynamicCollisionVFX'), ('MaterialInstanceConstant', 'SlashFX'), ('Texture2D', 'Roar_Spell_VFX'), ('Blueprint', 'ARPGEssentials'), ('World', 'Cursed_Magic')]:
            selected.append(next(r for r in PLAN if r['class'] == cls and r['package'].startswith('/Game/' + root + '/')))
    else:
        selected = PLAN
    # Worlds are last so their owned external packages follow the final asset refs.
    selected = sorted(selected, key=lambda r: (r['class'] == 'World', r['package']))
    held, renames, moved_rows = [], [], []
    for index, row in enumerate(selected):
        if unreal.EditorAssetLibrary.does_asset_exist(row['new_package']):
            obj = unreal.load_asset(row['new_object_path'])
            assert obj and obj.get_class().get_name() == row['class'], row
            report['renamed'].append({'old': row['package'], 'new': row['new_package'], 'already_moved': True})
            continue
        obj = unreal.load_asset(row['object_path'])
        assert obj and obj.get_class().get_name() == row['class'], row
        held.append(obj)
        before.setdefault(row['package'], snapshot(obj, row['class']))
        renames.append(unreal.AssetRenameData(asset=obj, new_package_path=row['target_folder'], new_name=row['new_name']))
        moved_rows.append(row)
        if index % 100 == 0:
            print('VFX_RENAME_LOAD ' + str(index+1) + '/' + str(len(selected)), flush=True)
    BEFORE_FILE.write_text(json.dumps(before, indent=2), encoding='utf-8')
    if renames:
        assert tools.rename_assets(renames), 'AssetTools rename batch returned false'
    # Save only staging packages; no Main project package is open in this process.
    for row in moved_rows:
        obj = unreal.load_asset(row['new_object_path'])
        assert obj and obj.get_class().get_name() == row['class'], row
        observed = snapshot(obj, row['class'])
        assert observed == before[row['package']], ('Value changed during rename', row['package'], before[row['package']], observed)
        assert unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=True), row
        report['renamed'].append({'old': row['package'], 'new': row['new_package'], 'already_moved': False})
        report['property_checks'].append({'old': row['package'], 'properties': observed})
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=True, save_content_packages=True)
    registry.scan_paths_synchronous(['/Game'], force_rescan=True)
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['errors'].append(traceback.format_exc())
    unreal.log_error(report['errors'][-1])
(META / ('PilotRename.json' if PILOT else 'StageRename.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VFX_RENAME_FINAL ' + json.dumps({'status': report['status'], 'pilot': PILOT, 'renamed': len(report['renamed']), 'errors': report['errors']}), flush=True)
