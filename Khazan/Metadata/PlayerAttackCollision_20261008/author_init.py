from pathlib import Path
import unreal
assert str(Path(unreal.Paths.project_dir()).resolve()) == str(Path('C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan'))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')
namespace={}
exec(Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Engineering/player_attack_damage_author_20261008.py').read_text(encoding='utf-8'),namespace)
print(namespace['author_damage_assets']())
print('POSE_OPTIONS',unreal.AnimPoseEvaluationOptions.__doc__)
print('POSE_FUNCTION',unreal.AnimPoseExtensions.get_anim_pose_at_time.__doc__)
