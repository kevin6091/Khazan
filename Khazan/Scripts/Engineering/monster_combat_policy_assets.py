"""Scoped asset preparation in the existing independent MonsterWork editor."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
assert root == Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
report = root / 'Saved/MonsterCombatPolicy'
report.mkdir(parents=True, exist_ok=True)
rows = []
for family in ('HeavySwordsman', 'HalberdElite'):
    path = '/Game/Monsters/' + family + '/Data/DA_Character_' + family
    definition = unreal.load_asset(path)
    routines = definition.get_editor_property('UnawareRoutines')
    basic = [r for r in routines if str(r.get_editor_property('Name')) == 'Basic']
    assert len(basic) == 1
    definition.set_editor_property('UnawareRoutines', basic)
    assert unreal.EditorAssetLibrary.save_loaded_asset(definition)
    rows.append({'definition': path, 'unaware_routine': 'Basic', 'candidate_count': 1})
for phase in ('Loop', 'End'):
    name = 'A_EN_PLAY_AC_EmpireHalberd_Basic_' + phase + '_02'
    source_path = '/Game/_Art/Enemies/HeinMach/Humanoids/HalberdElite/Animations/Playback/' + name
    target_path = '/Game/Monsters/HalberdElite/Animations/InGame/' + name
    source = unreal.load_asset(source_path)
    assert source
    clip = unreal.load_asset(target_path) if unreal.EditorAssetLibrary.does_asset_exist(target_path) else unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    assert clip
    # Same nav-driven contract as the existing gameplay clones; retain pose/FPS/RateScale.
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', unreal.RootMotionRootLock.REF_POSE)
    assert unreal.EditorAssetLibrary.save_loaded_asset(clip)
    rows.append({'source': source_path, 'gameplay': target_path,
                 'source_length_seconds': source.get_play_length(), 'gameplay_length_seconds': clip.get_play_length(),
                 'source_rate_scale': source.get_editor_property('rate_scale'), 'gameplay_rate_scale': clip.get_editor_property('rate_scale')})
(report / 'AssetPreparation.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(rows))
