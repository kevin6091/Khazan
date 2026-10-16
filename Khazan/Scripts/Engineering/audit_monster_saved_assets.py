"""Read-only saved monster assets/map audit, run with no PIE world."""
import json
import os
import pathlib
import unreal

root = pathlib.Path(unreal.Paths.project_dir()).resolve()
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Saved asset audit requires PIE to be stopped')
world = editor.get_editor_world()
families = ['Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite']
report = {'pid': os.getpid(), 'project': str(root), 'map': world.get_path_name(),
          'families': [], 'sequences': []}
for family in families:
    bp_path = '/Game/Bluprints/Monsters/BP_Monster_' + family
    abp_path = '/Game/Monsters/' + family + '/Animations/ABP_' + family
    bp = unreal.load_asset(bp_path)
    abp = unreal.load_asset(abp_path)
    cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(bp_path))
    report['families'].append({'family': family, 'bp_status': str(bp.get_editor_property('status')),
                              'abp_status': str(abp.get_editor_property('status')),
                              'controller': cdo.get_editor_property('AIControllerClass').get_path_name(),
                              'auto_possess': str(cdo.get_editor_property('AutoPossessAI')),
                              'tree': cdo.get_editor_property('AIStateTree').get_path_name(),
                              'attack_count': len(cdo.get_editor_property('AttackAbilities'))})
    for path in unreal.EditorAssetLibrary.list_assets('/Game/Monsters/' + family + '/Animations/InGame', True, False):
        a = unreal.load_asset(path)
        tracks = unreal.AnimationLibrary.get_animation_track_names(a)
        count = unreal.AnimationLibrary.get_num_frames(a)
        bone = tracks[0]
        poses = []
        for frame in (0, count // 2, max(0, count - 1)):
            t = unreal.AnimationLibrary.get_bone_pose_for_frame(a, bone, frame, False)
            poses.append({'frame': frame, 'translation_cm': [t.translation.x, t.translation.y, t.translation.z],
                          'rotation_xyzw': [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w]})
        report['sequences'].append({'asset': path, 'frames': count,
                                    'length_seconds': unreal.AnimationLibrary.get_sequence_length(a),
                                    'rate_scale': a.get_editor_property('rate_scale'),
                                    'root_motion': a.get_editor_property('enable_root_motion'),
                                    'force_root_lock': a.get_editor_property('force_root_lock'),
                                    'root_lock_mode': str(a.get_editor_property('root_motion_root_lock')),
                                    'root_path': [str(n) for n in unreal.AnimationLibrary.find_bone_path_to_root(a, bone)],
                                    'root_poses': poses})
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report['map_actors'] = [{'label': a.get_actor_label(), 'class': a.get_class().get_path_name(),
                         'location': str(a.get_actor_location()),
                         'bounds': str(a.get_actor_bounds(False))}
                        for a in actors if a.get_actor_label().startswith('DevAI_')]
report['legacy_fixture_count'] = sum(a.get_class().get_path_name() == '/Game/Bluprints/TEST_Monster.TEST_Monster_C' for a in actors)
report['dirty_map'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
report['dirty_content'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
out = root / 'Saved/MonsterAI/SavedAssetAudit.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k not in ('sequences', 'map_actors')}, ensure_ascii=False))
print('Sequences', len(report['sequences']), 'Map actors', len(report['map_actors']), 'Report', out)
