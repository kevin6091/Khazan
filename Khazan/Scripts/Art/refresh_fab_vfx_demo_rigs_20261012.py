"""Rebuild demo-only RigVM generated storage in staging, preserving authored graphs."""
from pathlib import Path
import json
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
STAGE = MAIN / 'Saved/ArtStaging/FabVFX_Complete_20261012'
assert Path(unreal.Paths.project_dir()).resolve() == STAGE
plan = json.loads((META / 'RenamePlan.json').read_text())
report = {'status': 'running', 'rigs': [], 'errors': [], 'scope': 'Demo RigVM cache recompile; no authored control graph or gameplay changes.'}
try:
    for row in plan:
        if row['class'] != 'ControlRigBlueprint':
            continue
        path = row['new_object_path'] if unreal.EditorAssetLibrary.does_asset_exist(row['new_package']) else row['object_path']
        asset = unreal.load_asset(path)
        assert isinstance(asset, unreal.ControlRigBlueprint), path
        models = list(asset.get_all_models())
        before = [(m.get_name(), len(m.get_nodes())) for m in models]
        asset.recompile_vm()
        unreal.BlueprintEditorLibrary.compile_blueprint(asset)
        after = [(m.get_name(), len(m.get_nodes())) for m in asset.get_all_models()]
        assert before == after, (path, before, after)
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), path
        report['rigs'].append({'path': path, 'model_node_counts': before, 'preserved': before == after})
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['errors'].append(traceback.format_exc())
    unreal.log_error(report['errors'][-1])
number = len(list(META.glob('RigRefresh*.json'))) + 1
(META / ('RigRefresh%02d.json' % number)).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VFX_DEMO_RIG_REFRESH ' + json.dumps(report), flush=True)
