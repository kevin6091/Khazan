"""Read the saved humanoid policies and remove only explicitly unwanted attacks."""
from pathlib import Path
import json, os, traceback, unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
MAIN = Path(os.environ['KZ_ATTACK_FILTER_MAIN'])
OUT = Path(os.environ['KZ_ATTACK_FILTER_OUT'])
MODE = os.environ['KZ_ATTACK_FILTER_MODE']
SWORD_KICK = '/Game/Monsters/Swordsman/Abilities/GA_Kick.GA_Kick_C'
SWORD_RUSH = '/Game/Monsters/Swordsman/Abilities/GA_Rush.GA_Rush_C'
report = {'success':False, 'project':str(ROOT), 'mode':MODE, 'families':{}, 'saved':[]}

def path(obj): return obj.get_path_name() if obj else None

def value(obj):
    if isinstance(obj, unreal.Object): return path(obj)
    if hasattr(obj, 'export_text'): return obj.export_text()
    if isinstance(obj, (unreal.Array, list)): return [value(x) for x in obj]
    return str(obj)

def protected(cdo, definition):
    return {'bp':{key:value(cdo.get_editor_property(key)) for key in ['character_definition','ai_state_tree','ai_settings','alert_ability']},
        'definition':{key:value(definition.get_editor_property(key)) for key in ['locomotion_config','hit_reactions','monster_stamina','unaware_routines','initial_effects']}}

try:
    if MODE == 'author':
        assert ROOT == MAIN.parent.parent / 'Khazan_AttackFilterWork_20261012/Khazan'
    for family in ['Swordsman', 'SwordShield']:
        bp_path = '/Game/Bluprints/Monsters/BP_Monster_' + family
        bp = unreal.load_asset(bp_path)
        cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(bp_path))
        definition = unreal.load_asset('/Game/Monsters/' + family + '/Data/DA_Character_' + family)
        attacks = list(cdo.get_editor_property('attack_abilities'))
        grants = list(definition.get_editor_property('initial_ability_grants'))
        old = {'attacks':[path(x) for x in attacks], 'grants':[x.export_text() for x in grants],
            'patterns':[x.export_text() for x in cdo.get_editor_property('combat_patterns')]}
        old_protected = protected(cdo, definition)
        banned = {SWORD_KICK, SWORD_RUSH} if family == 'Swordsman' else {SWORD_KICK}
        # Shield-specific kick classes, if present, must also be excluded. There
        # is no name-based rule in the game; this is one-time data authoring.
        if family == 'SwordShield':
            banned.update(path(x) for x in attacks if 'kick' in x.get_name().lower())
            banned.update(path(x.get_editor_property('ability_class')) for x in grants
                if x.get_editor_property('ability_class') and 'kick' in x.get_editor_property('ability_class').get_name().lower())
        kept_attacks = [x for x in attacks if path(x) not in banned]
        kept_grants = [x for x in grants if path(x.get_editor_property('ability_class')) not in banned]
        if MODE == 'author':
            if len(kept_attacks) != len(attacks):
                cdo.set_editor_property('attack_abilities', kept_attacks)
                unreal.BlueprintEditorLibrary.compile_blueprint(bp)
                assert unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)
                report['saved'].append(bp_path)
            if len(kept_grants) != len(grants):
                definition.set_editor_property('initial_ability_grants', kept_grants)
                assert unreal.EditorAssetLibrary.save_loaded_asset(definition, only_if_is_dirty=False)
                report['saved'].append(definition.get_path_name())
        new = {'attacks':[path(x) for x in cdo.get_editor_property('attack_abilities')],
            'grants':[x.export_text() for x in definition.get_editor_property('initial_ability_grants')],
            'patterns':[x.export_text() for x in cdo.get_editor_property('combat_patterns')]}
        new_protected = protected(cdo, definition)
        assert old_protected == new_protected
        if MODE != 'probe':
            assert new['attacks'] == [path(x) for x in kept_attacks]
            assert new['grants'] == [x.export_text() for x in kept_grants]
            assert new['patterns'] == old['patterns']
            assert not any(x in banned for x in new['attacks'])
            assert new['attacks'], 'Do not leave a monster without attacks'
        report['families'][family] = {'before':old, 'after':new, 'excluded':sorted(banned),
            'protected':new_protected,
            'removed_attacks':[path(x) for x in attacks if path(x) in banned],
            'removed_grants':[path(x.get_editor_property('ability_class')) for x in grants if path(x.get_editor_property('ability_class')) in banned]}
        if MODE == 'verify':
            authored = json.loads((MAIN / 'Metadata/MonsterAttackFilter_20261012/Author01/Report.json').read_text(encoding='utf-8'))['families'][family]
            assert new == authored['after']
            baseline = json.loads((MAIN / 'Metadata/MonsterAttackFilter_20261012/Probe02/Report.json').read_text(encoding='utf-8'))['families'][family]
            assert new_protected == baseline['protected']
    if MODE == 'verify' and ROOT == MAIN:
        report['placed_actors'] = []
        for level in ['/Game/Maps/DevMap','/Game/Maps/L_HeinMach_Environment']:
            assert unreal.EditorLoadingAndSavingUtils.load_map(level)
            for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
                name = actor.get_class().get_name()
                family = next((f for f in report['families'] if name == 'BP_Monster_' + f + '_C'), None)
                if family:
                    selected = [path(x) for x in actor.get_editor_property('attack_abilities')]
                    assert selected == report['families'][family]['after']['attacks'], (level,actor.get_actor_label(),selected)
                    report['placed_actors'].append({'level':level,'actor':actor.get_actor_label(),'family':family,'attacks':selected})
    # Record the actual shield feet relative to its pelvis; the current shield
    # library has no separately selected Kick ability. Do not delete a sword
    # swing because a historical name or another monster suggests a kick.
    if MODE == 'probe':
        report['shield_motion'] = []
        options = unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW,
            should_retarget=False, extract_root_motion=False, incorporate_root_motion_into_pose=True)
        for name in ['Attack_SwordCombo_01','Attack_SwordCombo_02','Attack_Pierce','Attack_ShieldCrash']:
            asset = unreal.load_asset('/Game/Monsters/SwordShield/Animations/InGame/Attack/' + name)
            bones = [str(b) for b in asset.get_editor_property('skeleton').get_reference_pose().get_bone_names()]
            wanted = [b for b in bones if b.startswith('Bip001') and any(s in b.lower() for s in ['foot','calf','thigh','pelvis'])]
            frames = []
            for index in range(41):
                t = asset.get_play_length() * index / 40
                pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
                positions = {}
                for bone in wanted:
                    p = pose.get_bone_pose(bone, unreal.AnimPoseSpaces.WORLD).translation
                    positions[bone] = [p.x, p.y, p.z]
                frames.append({'t':t, 'bones':positions})
            report['shield_motion'].append({'asset':path(asset), 'frames':frames})
    report['success'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'Report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('ATTACK_FILTER_RESULT', report['success'], report.get('error',''))
if not report['success']: raise RuntimeError(report.get('error','Attack policy verification failed'))
