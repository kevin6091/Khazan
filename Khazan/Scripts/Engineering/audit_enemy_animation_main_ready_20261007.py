"""Read-only Main delivery audit. Never compiles, saves, or starts PIE."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
assert Path(unreal.Paths.project_dir()).resolve() == MAIN
OUT = MAIN / 'Metadata/EnemyAnimationOrganization_20261007'
report = dict(pid=os.getpid(), project=str(MAIN), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              automatic_pie=False, compile_or_save=False, sequences=[], families=[])
try:
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert editor.get_game_world() is None
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    report['map'] = editor.get_editor_world().get_path_name()
    assert report['map'] == '/Game/Maps/DevMap.DevMap', report['map']
    saved = json.loads((OUT / 'SavedAnimationAudit.json').read_text(encoding='utf-8'))
    for row in saved['sequences']:
        clip = unreal.load_asset(row['asset'])
        assert isinstance(clip, unreal.AnimSequence), row['asset']
        assert clip.get_editor_property('enable_root_motion'), row['asset']
        assert clip.get_editor_property('force_root_lock'), row['asset']
        assert clip.get_editor_property('root_motion_root_lock') == unreal.RootMotionRootLock.ANIM_FIRST_FRAME
        assert clip.get_editor_property('rate_scale') == row['rate_scale'], row['asset']
        assert abs(clip.get_play_length() - row['length']) < 1.e-6, row['asset']
        report['sequences'].append(row['asset'])
    assert len(report['sequences']) == 813
    for expected in saved['families']:
        family = expected['family']
        bp = unreal.load_asset('/Game/Bluprints/Monsters/BP_Monster_' + family)
        abp = unreal.load_asset('/Game/Monsters/' + family + '/Animations/ABP_' + family)
        for asset in (bp, abp):
            assert asset.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, asset.get_path_name()
        cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(bp.get_path_name()))
        anim = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(abp.get_path_name()))
        assert anim.get_editor_property('RootMotionMode') == unreal.RootMotionMode.ROOT_MOTION_FROM_MONTAGES_ONLY
        settings = cdo.get_editor_property('AISettings')
        interval = settings.get_editor_property('AttackIntervalSeconds')
        assert abs(interval.x - expected['interval'][0]) < 1.e-5 and abs(interval.y - expected['interval'][1]) < 1.e-5
        assert abs(settings.get_editor_property('ContinueComboChance') - .85) < 1.e-6
        assert abs(settings.get_editor_property('ChaseReactionSeconds') - .4) < 1.e-6
        attacks = cdo.get_editor_property('AttackAbilities')
        assert len(attacks) == expected['attack_count']
        character_definition = unreal.load_asset('/Game/Monsters/' + family + '/Data/DA_Character_' + family)
        granted = {entry.get_editor_property('AbilityClass').get_path_name()
                   for entry in character_definition.get_editor_property('InitialAbilityGrants')}
        used = set()
        for ability in attacks:
            assert ability.get_path_name() in granted, ability.get_path_name()
            definition = unreal.get_default_object(ability).get_editor_property('ComboDefinition')
            for node in definition.get_editor_property('Nodes'):
                montage = node.get_editor_property('Montage')
                for track in montage.get_editor_property('SlotAnimTracks'):
                    for segment in track.get_editor_property('AnimTrack').get_editor_property('AnimSegments'):
                        used.add(segment.get_editor_property('AnimReference').get_path_name().split('.')[0])
        assert used == set(expected['used_attack_clips']), family
        report['families'].append(dict(family=family, attack_count=len(attacks), attack_clips=len(used),
                                       bp_status=str(bp.get_editor_property('status')), abp_status=str(abp.get_editor_property('status')),
                                       interval=[interval.x, interval.y], combo=settings.get_editor_property('ContinueComboChance'),
                                       chase_reaction=settings.get_editor_property('ChaseReactionSeconds')))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    expected_labels = {'DevAI_' + row['family'] for row in saved['families']}
    report['dev_monsters'] = [a.get_actor_label() for a in actors if a.get_actor_label() in expected_labels]
    assert set(report['dev_monsters']) == expected_labels and len(report['dev_monsters']) == 4
    manifest = json.loads((OUT / 'DeliveredManifest.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        assert hashlib.sha256((MAIN / row['path']).read_bytes()).hexdigest() == row['prepared_sha256'], row['path']
    for row in manifest['deleted']:
        assert not (MAIN / row['path']).exists(), row['path']
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    report.update(success=True, game_world=None, dirty_content=[], dirty_maps=[])
except Exception as error:
    report.update(success=False, error=repr(error))
    raise
finally:
    (OUT / 'MainReadyAudit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Enemy Main saved audit:', report.get('success'), os.getpid(), len(report['sequences']), report['families'])
