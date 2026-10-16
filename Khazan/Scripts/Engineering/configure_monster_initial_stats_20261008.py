"""Data-only initial stats; run in the explicitly isolated MonsterWork editor.

Values are the user's 2026-10-08 settings, not original-game metadata.
No damage, costs, regeneration, AI, registry, actor or player changes.
"""
from pathlib import Path
import json
import os
import re
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
EXPECTED = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
if ROOT != EXPECTED:
    raise RuntimeError('Initial stats authoring requires the isolated MonsterWork editor')
if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Initial stats authoring requires no PIE world')

VALUES = (('Swordsman', 100.0, 50.0), ('SwordShield', 100.0, 50.0),
          ('HeavySwordsman', 200.0, 50.0), ('HalberdElite', 200.0, 50.0),
          ('ApesStoneHandElite', 400.0, 100.0), ('Yetuga', 1000.0, 150.0))
ATTRIBUTES = ('MaxHP', 'HP', 'MaxStamina', 'Stamina')
TEMPLATES = ('/Game/Bluprints/AbilitySystem/Effects/GE_Init_PlayerHealth',
             '/Game/Bluprints/AbilitySystem/Effects/GE_Init_PlayerStamina')


def effect_class(path):
    result = unreal.EditorAssetLibrary.load_blueprint_class(path)
    if not result:
        raise RuntimeError('Missing effect class: ' + path)
    return result


def modifiers(path):
    return unreal.get_default_object(effect_class(path)).get_editor_property('modifiers')


def describe(mods):
    result = []
    for modifier in mods:
        attribute = modifier.get_editor_property('attribute')
        magnitude = modifier.get_editor_property('modifier_magnitude')
        scalar = magnitude.get_editor_property('scalable_float_magnitude')
        result.append(dict(attribute=str(attribute.get_editor_property('attribute_name')),
                           op=str(modifier.get_editor_property('modifier_op')),
                           value=scalar.get_editor_property('value')))
    return result


def with_value(source, value):
    # EditDefaultsOnly nested magnitude fields reject instance setters in UE Python.
    # Import the reviewed scalar into a copied struct; keep its real attribute path.
    modifier = source.copy()
    text, count = re.subn(r'(ScalableFloatMagnitude=\(Value=)[^,)]+',
                         lambda match: match.group(1) + str(value), source.export_text(), count=1)
    if count != 1:
        raise RuntimeError('Unexpected scalable magnitude export')
    modifier.import_text(text)
    return modifier


def unchanged_definition_data(definition):
    return dict(locomotion=definition.get_editor_property('locomotion_config').export_text(),
                grants=[item.export_text() for item in definition.get_editor_property('initial_ability_grants')],
                routines=[item.export_text() for item in definition.get_editor_property('unaware_routines')])


template_mods = list(modifiers(TEMPLATES[0])) + list(modifiers(TEMPLATES[1]))
template_before = describe(template_mods)
if tuple(item['attribute'] for item in template_before) != ATTRIBUTES:
    raise RuntimeError('Unexpected template attribute order')
if any(mod.get_editor_property('modifier_op') != unreal.GameplayModOp.OVERRIDE for mod in template_mods):
    raise RuntimeError('Initial stat templates must use Override')

tools = unreal.AssetToolsHelpers.get_asset_tools()
report = dict(pid=os.getpid(), project=str(ROOT), source='User settings 2026-10-08',
              player_templates_before=template_before, families=[])
for family, hp, stamina in VALUES:
    effect_path = '/Game/Monsters/' + family + '/Effects/GE_Init_' + family
    definition_path = '/Game/Monsters/' + family + '/Data/DA_Character_' + family
    if unreal.EditorAssetLibrary.does_asset_exist(effect_path):
        raise RuntimeError('Existing initializer requires explicit before-hash review: ' + effect_path)
    blueprint = unreal.EditorAssetLibrary.duplicate_asset(TEMPLATES[0], effect_path)
    if not blueprint:
        raise RuntimeError('Failed to duplicate initial effect: ' + effect_path)
    cdo = unreal.get_default_object(effect_class(effect_path))
    expected = (hp, hp, stamina, stamina)
    cdo.set_editor_property('duration_policy', unreal.GameplayEffectDurationType.INSTANT)
    cdo.set_editor_property('modifiers', [with_value(mod, value) for mod, value in zip(template_mods, expected)])
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    cdo = unreal.get_default_object(effect_class(effect_path))
    actual = describe(cdo.get_editor_property('modifiers'))
    if tuple(item['attribute'] for item in actual) != ATTRIBUTES or tuple(item['value'] for item in actual) != expected:
        raise RuntimeError('Compiled initial effect defaults differ: ' + effect_path)

    definition = unreal.load_asset(definition_path) if unreal.EditorAssetLibrary.does_asset_exist(definition_path) else None
    created = definition is None
    if created:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.load_class(None, '/Script/Khazan.KZCharacterDefinitionData'))
        folder, name = definition_path.rsplit('/', 1)
        definition = tools.create_asset(name, folder, unreal.DataAsset, factory)
    if not definition or definition.get_class().get_path_name() != '/Script/Khazan.KZCharacterDefinitionData':
        raise RuntimeError('Incorrect CharacterDefinition type: ' + definition_path)
    before = unchanged_definition_data(definition)
    effects = list(definition.get_editor_property('initial_effects'))
    effect = effect_class(effect_path)
    if effect not in effects:
        effects.append(effect)
    definition.set_editor_property('initial_effects', effects)
    if unchanged_definition_data(definition) != before:
        raise RuntimeError('Unrelated CharacterDefinition data changed')
    if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False):
        raise RuntimeError('Failed to save effect')
    if not unreal.EditorAssetLibrary.save_loaded_asset(definition, False):
        raise RuntimeError('Failed to save CharacterDefinition')
    report['families'].append(dict(family=family, HP=hp, MaxHP=hp, Stamina=stamina, MaxStamina=stamina,
                                  definition=definition_path, effect=effect_path, modifiers=actual,
                                  definition_created=created, gameplay_actor_connected=not created,
                                  unrelated_definition_data_unchanged=True,
                                  effect_status=str(blueprint.get_editor_property('status'))))

report['player_templates_after'] = describe(list(modifiers(TEMPLATES[0])) + list(modifiers(TEMPLATES[1])))
if report['player_templates_after'] != template_before:
    raise RuntimeError('Player templates changed')
report['dirty_content'] = [item.get_path_name() for item in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
report['dirty_map'] = [item.get_path_name() for item in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
out = ROOT / 'Saved/MonsterStats_20261008/Configured.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
