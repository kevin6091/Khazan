"""Read-only saved-data verification in a newly launched editor/commandlet."""
from pathlib import Path
import json
import os
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
if ROOT not in (MAIN, WORK):
    raise RuntimeError('Unexpected stats verification project')
if os.getpid() in (13700, 24552):
    raise RuntimeError('Do not use the existing user Main editor')
if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Saved stats verification requires no PIE')

VALUES = (('Swordsman', 100.0, 50.0), ('SwordShield', 100.0, 50.0),
          ('HeavySwordsman', 200.0, 50.0), ('HalberdElite', 200.0, 50.0),
          ('ApesStoneHandElite', 400.0, 100.0), ('Yetuga', 1000.0, 150.0))
ATTRIBUTES = ('MaxHP', 'HP', 'MaxStamina', 'Stamina')
report = dict(pid=os.getpid(), project=str(ROOT), read_only=True, families=[])
for family, hp, stamina in VALUES:
    base = '/Game/Monsters/' + family
    effect_path = base + '/Effects/GE_Init_' + family
    definition_path = base + '/Data/DA_Character_' + family
    blueprint = unreal.load_asset(effect_path)
    effect_class = unreal.EditorAssetLibrary.load_blueprint_class(effect_path)
    cdo = unreal.get_default_object(effect_class)
    definition = unreal.load_asset(definition_path)
    assert blueprint and effect_class and cdo and definition, family
    assert blueprint.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, family
    assert cdo.get_editor_property('duration_policy') == unreal.GameplayEffectDurationType.INSTANT, family
    mods = cdo.get_editor_property('modifiers')
    assert len(mods) == len(ATTRIBUTES), family
    actual = []
    for modifier, name, value in zip(mods, ATTRIBUTES, (hp, hp, stamina, stamina)):
        attribute = modifier.get_editor_property('attribute')
        assert attribute.get_editor_property('attribute_name') == name, family
        # Check the real field path, not just its cached display name.
        export = attribute.export_text()
        assert 'Attribute=/Script/Khazan.KZAttributeSet:' + name in export, export
        assert modifier.get_editor_property('modifier_op') == unreal.GameplayModOp.OVERRIDE, family
        scalar = modifier.get_editor_property('modifier_magnitude').get_editor_property('scalable_float_magnitude')
        actual_value = scalar.get_editor_property('value')
        assert actual_value == value, (family, name, actual_value, value)
        actual.append(dict(attribute=name, value=actual_value, field=export))
    effects = list(definition.get_editor_property('initial_effects'))
    assert effect_class in effects, family
    report['families'].append(dict(family=family, definition=definition_path,
                                  effect=effect_path, modifiers=actual,
                                  initial_effects=[item.get_path_name() for item in effects],
                                  actor_integration='Existing human definition' if family not in ('ApesStoneHandElite', 'Yetuga') else 'Data prepared; no gameplay actor/registry integration'))
report['dirty_content'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
report['dirty_map'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
assert not report['dirty_content'] and not report['dirty_map'], 'Read-only verification dirtied packages'
report['success'] = True
out = ROOT / ('Metadata/MonsterStats_20261008/MainSavedReload.json' if ROOT == MAIN else 'Saved/MonsterStats_20261008/SavedReload.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('MonsterStatsSavedReload Success: 6 families, 24 attribute modifiers, no gameplay execution')
