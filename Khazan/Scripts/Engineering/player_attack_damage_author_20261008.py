"""Author the shared instant attack GE in the owned ComboWork editor only.

Call author_damage_assets() after the isolated editor has loaded the new native
attack schema, before PIE. Existing MonsterStats initializers are reused; their
CharacterDefinition files are never copied over current ComboWork definitions.
This helper does not run on import, launch an editor, or write to Main.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import unreal


COMBO_ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan')
MAIN_ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
STATS_ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
REPORT_RELATIVE = 'Metadata/PlayerAttackCollision_20261008'
DAMAGE_ASSET = '/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage'
DAMAGE_NAMES = (('HP', 'KZAttackHPDamage'), ('Stamina', 'KZAttackStaminaDamage'))
GUARD_TEMPLATE = '/Game/Bluprints/AbilitySystem/Effects/Guard/GE_GuardHit_Stamina'
HEALTH_TEMPLATE = '/Game/Bluprints/AbilitySystem/Effects/GE_Init_PlayerHealth'
STAMINA_TEMPLATE = '/Game/Bluprints/AbilitySystem/Effects/GE_Init_PlayerStamina'
GAMEPLAY_FAMILIES = ('Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite')


def _file(root, asset_path):
    if not asset_path.startswith('/Game/') or '..' in asset_path:
        raise RuntimeError('Invalid managed asset path: ' + asset_path)
    return root / ('Content/' + asset_path[len('/Game/'):] + '.uasset')


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _effect(path):
    blueprint = unreal.load_asset(path)
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    if not blueprint or not cls:
        raise RuntimeError('Missing effect Blueprint: ' + path)
    return blueprint, cls, unreal.get_default_object(cls)


def _modifiers(cdo):
    return list(cdo.get_editor_property('modifiers'))


def _damage_readback():
    bp, cls, cdo = _effect(DAMAGE_ASSET)
    if bp.get_editor_property('status') != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError('Damage Blueprint is not compiled')
    if cdo.get_editor_property('duration_policy') != unreal.GameplayEffectDurationType.INSTANT:
        raise RuntimeError('Damage GE must be instant')
    if cdo.get_editor_property('ge_components') or cdo.get_editor_property('executions'):
        raise RuntimeError('Shared damage GE has unexpected additional behaviour')
    if cdo.get_editor_property('period').get_editor_property('value') != 0.0:
        raise RuntimeError('Shared damage GE must not be periodic')
    mods = _modifiers(cdo)
    if len(mods) != len(DAMAGE_NAMES):
        raise RuntimeError('Shared damage GE must have exactly HP and Stamina modifiers')
    rows = []
    for mod, (attribute, data_name) in zip(mods, DAMAGE_NAMES):
        text = mod.export_text()
        if ('Attribute=/Script/Khazan.KZAttributeSet:' + attribute not in text or
                'ModifierOp=AddBase' not in text or
                'MagnitudeCalculationType=SetByCaller' not in text or
                'SetByCallerMagnitude=(DataName="' + data_name + '",DataTag=(TagName=""))' not in text):
            raise RuntimeError('Unexpected attack damage modifier: ' + text)
        rows.append(dict(attribute=attribute, data_name=data_name, modifier=text))
    return dict(asset=DAMAGE_ASSET, effect_class=cls.get_path_name(), duration='Instant',
                components=[], modifiers=rows, magnitude_contract='Caller supplies negative damage values')


def _definition_other_data(definition):
    return dict(locomotion=definition.get_editor_property('locomotion_config').export_text(),
                grants=[x.export_text() for x in definition.get_editor_property('initial_ability_grants')],
                routines=[x.export_text() for x in definition.get_editor_property('unaware_routines')])


def _audit_initializer(path, expected):
    bp, cls, cdo = _effect(path)
    if bp.get_editor_property('status') != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError('Initializer is not compiled: ' + path)
    if cdo.get_editor_property('duration_policy') != unreal.GameplayEffectDurationType.INSTANT:
        raise RuntimeError('Initializer is not instant: ' + path)
    mods = _modifiers(cdo)
    names = ('MaxHP', 'HP', 'MaxStamina', 'Stamina')
    values = (expected['HP'], expected['HP'], expected['Stamina'], expected['Stamina'])
    if len(mods) != len(names):
        raise RuntimeError('Unexpected initializer modifier count: ' + path)
    rows = []
    for mod, name, value in zip(mods, names, values):
        text = mod.export_text()
        scalar = mod.get_editor_property('modifier_magnitude').get_editor_property('scalable_float_magnitude')
        if ('Attribute=/Script/Khazan.KZAttributeSet:' + name not in text or
                'ModifierOp=Override' not in text or 'MagnitudeCalculationType=ScalableFloat' not in text or
                scalar.get_editor_property('value') != value):
            raise RuntimeError('Prepared user initializer differs: ' + path + ' / ' + name)
        rows.append(dict(attribute=name, value=value, modifier=text))
    return cls, rows


def author_damage_assets(root=None, report_directory=None, stats_source_root=None,
                         stats_manifest_path=None, connect_prepared_stats=True):
    """Create/audit one damage GE, append prepared initializers for four actors.

    All initial Effects and unrelated current CharacterDefinition data survive.
    With connect_prepared_stats=False only the common damage asset is authored.
    The returned manifest enumerates every managed file before/after, including
    reused files; changed_files is the exact set to consider for later delivery.
    """
    actual = Path(unreal.Paths.project_dir()).resolve()
    root = Path(root).resolve() if root is not None else actual
    if root != COMBO_ROOT.resolve() or actual != root:
        raise RuntimeError('Attack damage authoring requires the isolated ComboWork editor')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Attack damage authoring requires no PIE')
    out = Path(report_directory).resolve() if report_directory is not None else root / REPORT_RELATIVE
    if not out.is_relative_to(root):
        raise RuntimeError('Author report must remain inside ComboWork')
    out.mkdir(parents=True, exist_ok=True)

    stats_root = Path(stats_source_root).resolve() if stats_source_root is not None else STATS_ROOT.resolve()
    manifest_path = Path(stats_manifest_path).resolve() if stats_manifest_path is not None else MAIN_ROOT / 'Metadata/MonsterStats_20261008/PreparedManifest.json'
    prepared = json.loads(manifest_path.read_text(encoding='utf-8-sig')) if connect_prepared_stats else None
    saved = json.loads((manifest_path.parent / 'WorkSavedReload.json').read_text(encoding='utf-8-sig')) if prepared else None
    if saved and not saved.get('success'):
        raise RuntimeError('MonsterStats has no successful saved reload')
    stats_rows = {row['family']: row for row in saved['families']} if saved else {}
    prepared_files = {row['file']: row for row in prepared['files']} if prepared else {}
    managed = [DAMAGE_ASSET]
    if prepared:
        for family in GAMEPLAY_FAMILIES:
            managed.extend(('/Game/Monsters/' + family + '/Effects/GE_Init_' + family,
                            '/Game/Monsters/' + family + '/Data/DA_Character_' + family))
    protected = (GUARD_TEMPLATE, HEALTH_TEMPLATE, STAMINA_TEMPLATE)
    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(managed + list(protected)):
        raise RuntimeError('Managed/template packages have existing unsaved edits')
    before = {path: _hash(_file(root, path)) for path in managed}
    template_hashes = {path: _hash(_file(root, path)) for path in protected}
    for path, sha in template_hashes.items():
        if sha is None:
            raise RuntimeError('Missing protected template: ' + path)

    # Preflight all prepared bytes/current definitions before making any asset.
    imports = []
    for family in GAMEPLAY_FAMILIES if prepared else ():
        base = '/Game/Monsters/' + family
        definition_path = base + '/Data/DA_Character_' + family
        effect_path = base + '/Effects/GE_Init_' + family
        if not _file(root, definition_path).is_file():
            raise RuntimeError('Existing gameplay definition is missing: ' + definition_path)
        row = prepared_files['Content/' + effect_path[len('/Game/'):] + '.uasset']
        source = stats_root / row['file']
        if _hash(source) != row['after'].lower():
            raise RuntimeError('Prepared MonsterStats source changed: ' + str(source))
        if not _file(root, effect_path).exists():
            imports.append((source, _file(root, effect_path)))
    for source, target in imports:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if _hash(target) != _hash(source):
            raise RuntimeError('Initializer import hash mismatch: ' + str(target))
    if imports:
        unreal.AssetRegistryHelpers.get_asset_registry().scan_files_synchronous([str(target) for _, target in imports], True)

    _, _, guard = _effect(GUARD_TEMPLATE)
    guard_mods = _modifiers(guard)
    if len(guard_mods) != 1 or guard.get_editor_property('ge_components') or guard.get_editor_property('executions'):
        raise RuntimeError('Guard hit template has unexpected behaviour')
    guard_text = guard_mods[0].export_text()
    if 'MagnitudeCalculationType=SetByCaller' not in guard_text or 'ModifierOp=AddBase' not in guard_text:
        raise RuntimeError('Guard template is not the expected additive SetByCaller modifier')
    _, _, health = _effect(HEALTH_TEMPLATE)
    attributes = {'Stamina': guard_mods[0].get_editor_property('attribute')}
    hp_mods = [m for m in _modifiers(health) if m.get_editor_property('attribute').get_editor_property('attribute_name') == 'HP']
    if len(hp_mods) != 1:
        raise RuntimeError('Health template lacks one real HP attribute')
    attributes['HP'] = hp_mods[0].get_editor_property('attribute')
    damage_created = not unreal.EditorAssetLibrary.does_asset_exist(DAMAGE_ASSET)
    if damage_created:
        blueprint = unreal.EditorAssetLibrary.duplicate_asset(GUARD_TEMPLATE, DAMAGE_ASSET)
        if not blueprint:
            raise RuntimeError('Failed to duplicate shared damage effect')
        _, _, damage = _effect(DAMAGE_ASSET)
        damage_mods = []
        for attribute, name in DAMAGE_NAMES:
            old = 'Attribute=' + attributes['Stamina'].export_text()
            new = 'Attribute=' + attributes[attribute].export_text()
            if guard_text.count(old) != 1:
                raise RuntimeError('Unexpected attribute export in Guard modifier')
            text = guard_text.replace(old, new, 1)
            text, count = re.subn(r'(SetByCallerMagnitude=\(DataName=)"GuardStaminaDamage"',
                                 lambda match: match.group(1) + '"' + name + '"', text, count=1)
            if count != 1:
                raise RuntimeError('Guard template DataName differs')
            modifier = guard_mods[0].copy()
            modifier.import_text(text)
            damage_mods.append(modifier)
        damage.set_editor_property('duration_policy', unreal.GameplayEffectDurationType.INSTANT)
        damage.set_editor_property('modifiers', damage_mods)
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        _damage_readback()
        if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False):
            raise RuntimeError('Failed to save shared damage effect')
    damage_report = _damage_readback()

    families = []
    for family in GAMEPLAY_FAMILIES if prepared else ():
        base = '/Game/Monsters/' + family
        definition_path = base + '/Data/DA_Character_' + family
        effect_path = base + '/Effects/GE_Init_' + family
        stats = stats_rows[family]
        expected = {m['attribute']: m['value'] for m in stats['modifiers']}
        cls, mods = _audit_initializer(effect_path, expected)
        definition = unreal.load_asset(definition_path)
        if not definition or definition.get_class().get_path_name() != '/Script/Khazan.KZCharacterDefinitionData':
            raise RuntimeError('Incorrect gameplay definition type: ' + definition_path)
        untouched = _definition_other_data(definition)
        effects = list(definition.get_editor_property('initial_effects'))
        old_paths = [x.get_path_name() if x else None for x in effects]
        appended = cls not in effects
        if appended:
            effects.append(cls)
            definition.set_editor_property('initial_effects', effects)
        new_paths = [x.get_path_name() if x else None for x in definition.get_editor_property('initial_effects')]
        if _definition_other_data(definition) != untouched or new_paths != old_paths + ([cls.get_path_name()] if appended else []):
            raise RuntimeError('Unrelated definition or initial Effect order changed: ' + definition_path)
        if appended and not unreal.EditorAssetLibrary.save_loaded_asset(definition, False):
            raise RuntimeError('Failed to save initializer connection: ' + definition_path)
        families.append(dict(family=family, definition=definition_path, initializer=effect_path,
                             appended=appended, initial_effects_before=old_paths, initial_effects_after=new_paths,
                             modifiers=mods, unrelated_definition_data_preserved=True,
                             value_source='User settings 2026-10-08; prepared MonsterStats GE reused'))
    if template_hashes != {path: _hash(_file(root, path)) for path in protected}:
        raise RuntimeError('Protected Player/Guard templates changed')
    if _modifiers(guard)[0].export_text() != guard_text:
        raise RuntimeError('Guard source modifier changed in memory')
    files = [dict(asset=path, file=str(_file(root, path).relative_to(root)).replace('\\', '/'),
                  before=before[path], after=_hash(_file(root, path))) for path in managed]
    report = dict(pid=os.getpid(), project=str(root), success=True, damage_created=damage_created,
                  damage=damage_report, monster_initializers=families, files=files,
                  changed_files=[row for row in files if row['before'] != row['after']],
                  protected_templates=template_hashes, main_written=False, automatic_pie=False,
                  stats_prepared_manifest=str(manifest_path) if prepared else None,
                  stats_imports=[str(target.relative_to(root)).replace('\\', '/') for _, target in imports],
                  other_prepared_families='Apes/Yetuga remain their separate MonsterStats data preparation scope')
    (out / 'DamageAssetsAuthor.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
