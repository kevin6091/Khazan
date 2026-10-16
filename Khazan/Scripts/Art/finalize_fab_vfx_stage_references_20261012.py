"""Update the single pilot demo map referencer after its GameMode moves."""
from pathlib import Path
import json
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
STAGE = MAIN / 'Saved/ArtStaging/FabVFX_Complete_20261012'
assert Path(unreal.Paths.project_dir()).resolve() == STAGE
plan = json.loads((META / 'RenamePlan.json').read_text())
world_row = next(r for r in plan if r['package'] == '/Game/Cursed_Magic/Maps/Cursed_Magic')
mode_row = next(r for r in plan if r['package'] == '/Game/Cursed_Magic/Blueprints/BP_Cursed_Magic_GameMode')
world = unreal.load_asset(world_row['new_object_path'])
mode = unreal.load_class(None, mode_row['new_object_path'] + '_C')
assert world and mode
settings = world.get_world_settings()
old = settings.get_editor_property('default_game_mode')
settings.set_editor_property('default_game_mode', mode)
assert unreal.EditorAssetLibrary.save_loaded_asset(world, only_if_is_dirty=False)
result = {'status': 'passed', 'map': world_row['new_package'], 'old_effective_class': old.get_path_name() if old else None, 'new_class': mode.get_path_name(), 'scope': 'Same authored demo GameMode at its relocated path; no game map or gameplay policy change.'}
(META / 'FinalMapReference.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result), flush=True)
