import json, os, pathlib, unreal
root = pathlib.Path(unreal.Paths.project_dir()).resolve()
assert root == pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
assert unreal.EditorLevelLibrary.get_game_world() is None
d = unreal.load_asset('/Game/Data/Ability/DA_Player_Combo_Definition')
if not d:
    matches = [a for a in unreal.AssetRegistryHelpers.get_asset_registry().get_all_assets() if str(a.asset_name) == 'DA_Player_Combo_Definition']
    assert len(matches) == 1
    d = matches[0].get_asset()
rows = []
for n in d.get_editor_property('nodes'):
    m = n.get_editor_property('montage')
    rows.append(dict(node=str(n.get_editor_property('node_id')), montage=m.get_path_name() if m else None,
                     section=str(n.get_editor_property('section_name'))))
path = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/MonsterStamina_20261008/ActualWorkComboReferences.json')
path.write_text(json.dumps(dict(pid=os.getpid(), definition=d.get_path_name(), rows=rows), indent=2), encoding='utf-8')
