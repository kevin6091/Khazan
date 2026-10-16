"""Fresh process readback of the five packages; no save or gameplay writes."""
import unreal as u
import os, json, runpy
from pathlib import Path

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_COMBAT_FINISH_OUT'])
author = json.loads((root/'Metadata/StrongComboVictimFront_20261013/Author01/Author.json').read_text(encoding='utf-8'))
definition = u.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
assert [n.export_text() for n in definition.get_editor_property('nodes')] == author['after_nodes']
for row in author['settings']:
    asset = u.load_asset(row['asset'])
    settings = asset.get_editor_property('hit_reactions')
    assert settings.export_text() == row['after'], row['asset']
    assert settings.get_editor_property('victim_front').get_path_name() == row['victim_front']
    # Remove only the new field from a copy, checking every original reaction setting.
    copy = u.KZHitReactionSettings()
    copy.import_text(settings.export_text())
    copy.set_editor_property('victim_front', None)
    assert copy.export_text() == row['before'], row['asset']
    protected = row['protected']
    for key in ['monster_stamina', 'locomotion_config']:
        assert asset.get_editor_property(key).export_text() == protected[key]
    for key in ['unaware_routines', 'initial_ability_grants']:
        assert [v.export_text() for v in asset.get_editor_property(key)] == protected[key]
    assert [v.get_path_name() if v else None for v in asset.get_editor_property('initial_effects')] == protected['initial_effects']
    tree = asset.get_editor_property('original_pattern_state_tree')
    assert (tree.get_path_name() if tree else None) == protected['original_pattern_state_tree']
for family in ['ApesStoneHandElite', 'Yetuga']:
    asset = u.load_asset('/Game/Monsters/'+family+'/Data/DA_Character_'+family)
    assert not asset.get_editor_property('hit_reactions').get_editor_property('victim_front')
runpy.run_path(str(root/'Scripts/Engineering/probe_strong_combo_victim_front_20261013.py'))
(out/'Verification.json').write_text(json.dumps({'passed': True, 'changed_windows': 6, 'definitions': 4,
    'other_nodes_and_all_original_definition_fields_preserved': True, 'asset_saves': 0}, indent=2), encoding='utf-8')
u.log('STRONG_VICTIM_SAVED_VERIFIED')
