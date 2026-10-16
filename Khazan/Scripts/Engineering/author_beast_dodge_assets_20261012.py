"""Author only owned gameplay asset roots in the isolated current-source project."""
from pathlib import Path
import json
import copy
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == MAIN.parent.parent / 'Khazan_BeastDodgeWork_20261012/Khazan'
OUT = MAIN / 'Metadata/BeastDodge_20261012'
report = {'status': 'running', 'project': str(WORK), 'saved_packages': [], 'aliases': []}


def save(obj):
    path = obj.get_path_name().split('.')[0]
    assert path.startswith(('/Game/Monsters/', '/Game/Data/', '/Game/Bluprints/'))
    assert unreal.EditorAssetLibrary.save_loaded_asset(obj)
    report['saved_packages'].append(path)


def cdo(bp):
    return unreal.get_default_object(unreal.load_class(None, bp.get_path_name() + '_C'))


sound_task = unreal.AssetImportTask()
sound_task.filename = str(OUT / 'Feedback/Player_Dodge_Success.wav')
sound_task.destination_path = '/Game/Monsters/Shared/Feedback'
sound_task.destination_name = 'SW_Player_DodgeSuccess'
sound_task.automated = True; sound_task.save = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([sound_task])
sound = unreal.load_asset('/Game/Monsters/Shared/Feedback/SW_Player_DodgeSuccess')
assert sound
report['saved_packages'].append('/Game/Monsters/Shared/Feedback/SW_Player_DodgeSuccess')
dash = unreal.load_asset('/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Dash1')
blink = unreal.load_asset('/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Blink1')
assert dash and blink
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(synchronous_search=True)
for data in registry.get_assets_by_path('/Game/Bluprints/AbilitySystem/Abilities/Player', recursive=True):
    if str(data.asset_class_path.asset_name) != 'Blueprint': continue
    bp = data.get_asset(); defaults = cdo(bp)
    if isinstance(defaults, unreal.KZDodgeAbility):
        defaults.set_editor_property('invulnerability_seconds', .1) # User value.
        defaults.set_editor_property('dodge_effect', dash)
        defaults.set_editor_property('success_effect', blink)
        defaults.set_editor_property('success_sound', sound)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp); save(bp)
assert len([p for p in report['saved_packages'] if '/Player/' in p]) == 8
plan = json.loads((OUT / 'YetugaStateTreePlan.json').read_text())
base = '/Game/Monsters/Yetuga'
combo = unreal.load_asset(base + '/Data/DA_OriginalPatterns_Yetuga')
definition = unreal.load_asset(base + '/Data/DA_Character_Yetuga')
assert combo and definition
grants = list(definition.get_editor_property('initial_ability_grants'))
body_bp = unreal.load_asset('/Game/Bluprints/Monsters/BP_Monster_Yetuga')
body = cdo(body_bp)
choices = list(body.get_editor_property('combat_patterns'))
aliases = {}
si_aliases = {'NormalAtk02_NoCoolTime': 'NormalAtk02', 'TurnBackRun_Short_Nocool': 'TurnBackRun_Short'}
for row in plan['states']:
    if row['kind'] != 'UseSkill': continue
    sid = row['skill']
    original_sid = si_aliases.get(sid, sid)
    original = base + '/Abilities/GA_Original_' + original_sid
    selected = row.get('forced_step')
    key = sid + ('_' + selected if selected else '')
    destination = base + '/Abilities/GA_Original_' + key
    if sid != original_sid or selected:
        if key not in aliases:
            bp = unreal.load_asset(destination) if unreal.EditorAssetLibrary.does_asset_exist(destination) else unreal.EditorAssetLibrary.duplicate_asset(original, destination)
            assert bp
            defaults = cdo(bp)
            if selected: defaults.set_editor_property('entry_node_id', original_sid + '_' + selected)
            if sid != original_sid: defaults.set_editor_property('cooldown_skill_override', sid)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp); save(bp)
            ability_class = unreal.load_class(None, bp.get_path_name() + '_C')
            grant = unreal.KZInitialAbilityGrant(); grant.set_editor_property('ability_class', ability_class)
            if not any(g.get_editor_property('ability_class') == ability_class for g in grants): grants.append(grant)
            aliases[key] = ability_class
            report['aliases'].append({'skill': sid, 'selected_step': selected, 'class': ability_class.get_path_name()})
            if sid != original_sid:
                choice = unreal.KZMonsterSkillChoice()
                choice.set_editor_property('skill', sid); choice.set_editor_property('ability', ability_class)
                choice.set_editor_property('weight', 0.)
                choice.set_editor_property('source', 'Original BT/SI: same SB, named no-cooldown alias; omitted native cooldown defaults mapped to project zero')
                choices = [c for c in choices if str(c.get_editor_property('skill')) != sid] + [choice]
        row['ability_class'] = aliases[key].get_path_name()
    else:
        row['ability_class'] = original + '.GA_Original_' + original_sid + '_C'
definition.set_editor_property('initial_ability_grants', grants); save(definition)
body.set_editor_property('combat_patterns', choices)
unreal.BlueprintEditorLibrary.compile_blueprint(body_bp); save(body_bp)
(OUT / 'YetugaStateTreeAuthor.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.SystemLibrary.execute_console_command(None, 'KZ.BeastDodge.AuthorTree "' + str(OUT / 'YetugaStateTreeAuthor.json') + '" /Game/Monsters/Yetuga/AI/ST_Yetuga_Original')
tree = unreal.load_asset('/Game/Monsters/Yetuga/AI/ST_Yetuga_Original')
assert tree
definition.set_editor_property('original_pattern_state_tree', tree); save(definition)
report['saved_packages'].append('/Game/Monsters/Yetuga/AI/ST_Yetuga_Original')
apes_plan = {'family': 'Apes', 'states': []}
(OUT / 'ApesStateTreeAuthor.json').write_text(json.dumps(apes_plan), encoding='utf-8')
unreal.SystemLibrary.execute_console_command(None, 'KZ.BeastDodge.AuthorTree "' + str(OUT / 'ApesStateTreeAuthor.json') + '" /Game/Monsters/ApesStoneHandElite/AI/ST_Apes_Original')
apes_tree = unreal.load_asset('/Game/Monsters/ApesStoneHandElite/AI/ST_Apes_Original')
assert apes_tree
apes_definition = unreal.load_asset('/Game/Monsters/ApesStoneHandElite/Data/DA_Character_ApesStoneHandElite')
apes_definition.set_editor_property('original_pattern_state_tree', apes_tree); save(apes_definition)
apes_bp = unreal.load_asset('/Game/Bluprints/Monsters/BP_Monster_ApesStoneHandElite')
apes_defaults = cdo(apes_bp)
passives = []
for seconds, count, chance in [(4., 5, .5), (4., 6, .7), (5., 7, 1.)]:
    row = unreal.KZMonsterDamagePassive()
    row.set_editor_property('skill', 'SideMove')
    row.set_editor_property('hit_window_seconds', seconds); row.set_editor_property('hit_count', count)
    row.set_editor_property('chance', chance); row.set_editor_property('pending_seconds', .1)
    row.set_editor_property('source', 'SB_ApesStoneHand_E_DodgeSkill_Early source counts/RNG/pending; >=/reset project adapter')
    passives.append(row)
apes_defaults.set_editor_property('damage_passives', passives)
unreal.BlueprintEditorLibrary.compile_blueprint(apes_bp); save(apes_bp)
report['saved_packages'].append('/Game/Monsters/ApesStoneHandElite/AI/ST_Apes_Original')
report['status'] = 'authored'
(OUT / 'AuthoringReport.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BEAST_DODGE_ASSETS ' + json.dumps(report), flush=True)
