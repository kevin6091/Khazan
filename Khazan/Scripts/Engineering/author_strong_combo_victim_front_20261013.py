"""Change only six StrongCombo reactions and four optional victim pose settings."""
import unreal as u
import json, os, hashlib
from pathlib import Path

root = Path(u.Paths.project_dir()).resolve()
assert root == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out = Path(os.environ['KZ_COMBAT_FINISH_OUT'])
def other_settings(asset):
    return {'monster_stamina': asset.get_editor_property('monster_stamina').export_text(),
            'locomotion_config': asset.get_editor_property('locomotion_config').export_text(),
            'unaware_routines': [r.export_text() for r in asset.get_editor_property('unaware_routines')],
            'initial_ability_grants': [r.export_text() for r in asset.get_editor_property('initial_ability_grants')],
            'initial_effects': [e.get_path_name() if e else None for e in asset.get_editor_property('initial_effects')],
            'original_pattern_state_tree': (asset.get_editor_property('original_pattern_state_tree').get_path_name()
                                            if asset.get_editor_property('original_pattern_state_tree') else None)}
baseline = json.loads((root/'Metadata/StrongComboVictimFront_20261013/Baseline.json').read_text(encoding='utf-8-sig'))
for row in baseline:
    if row['file'].startswith('Content/'):
        assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest() == row['sha256'], row['file']

definition = u.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
nodes = list(definition.get_editor_property('nodes'))
report = {'before_nodes': [n.export_text() for n in nodes], 'settings': [], 'changed_windows': []}
for node in nodes:
    node_id = str(node.get_editor_property('node_id'))
    if node_id not in ['StrongAttack01', 'StrongAttack02', 'StrongAttack03']:
        continue
    assert node.get_editor_property('montage').get_name() == 'AM_DAS_StrongAttackCombo'
    windows = list(node.get_editor_property('attack_windows'))
    assert len(windows) == 2
    for index, window in enumerate(windows):
        assert window.get_editor_property('hit_reaction') == u.KZHitReactionType.KNOCKBACK
        before = window.export_text()
        window.set_editor_property('hit_reaction', u.KZHitReactionType.VICTIM_FRONT)
        assert window.export_text() == before.replace('HitReaction=Knockback', 'HitReaction=VictimFront')
        report['changed_windows'].append({'node': node_id, 'window': index, 'before': before, 'after': window.export_text()})
    node.set_editor_property('attack_windows', windows)
definition.set_editor_property('nodes', nodes)
report['after_nodes'] = [n.export_text() for n in definition.get_editor_property('nodes')]
for before, after in zip(report['before_nodes'], report['after_nodes']):
    assert after.replace('HitReaction=VictimFront', 'HitReaction=Knockback') == before
targets = [definition]
for family in ['Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite']:
    character = u.load_asset('/Game/Monsters/'+family+'/Data/DA_Character_'+family)
    front = u.load_asset('/Game/Monsters/'+family+'/Animations/AM_BrutalVictimFront')
    assert front and front.get_num_sections() == 2
    assert str(front.get_section_name(0)) == 'Damage1' and str(front.get_section_name(1)) == 'Damage2'
    settings = character.get_editor_property('hit_reactions')
    before = settings.export_text()
    protected = other_settings(character)
    settings.set_editor_property('victim_front', front)
    character.set_editor_property('hit_reactions', settings)
    assert other_settings(character) == protected
    report['settings'].append({'asset': character.get_path_name(), 'before': before, 'after': settings.export_text(),
                              'victim_front': front.get_path_name(), 'protected': protected})
    targets.append(character)
assert len(report['changed_windows']) == 6
report['saved'] = []
for asset in targets:
    assert u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), asset.get_path_name()
    report['saved'].append(asset.get_path_name())
(out/'Author.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('STRONG_VICTIM_AUTHOR_DONE: 6 windows, 4 settings, 5 saves')
