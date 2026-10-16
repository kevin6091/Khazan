"""Apply per-cloth solver precision settings in the explicitly private editor."""
from pathlib import Path
import configparser, json
import unreal
root = Path(unreal.Paths.project_dir()).resolve()
assert root == Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan').resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
config = configparser.ConfigParser()
config.read(root / 'Saved/PlayerClothRefinement.ini', encoding='utf-8-sig')
step = config.getfloat('ClothRefinement', 'FixedTimeStepSeconds')
iterations = config.getint('ClothRefinement', 'PositionIterations')
velocity_iterations = config.getint('ClothRefinement', 'VelocityIterations')
projection_iterations = config.getint('ClothRefinement', 'ProjectionIterations')
assert step > 0 and iterations > 0
assert velocity_iterations > 0 and projection_iterations > 0
rows = []
keys = ('fixed_time_step', 'position_iterations', 'velocity_iterations', 'projection_iterations', 'use_linear_joint_solver', 'use_manifolds')
for part in ('Torso', 'Leg'):
    asset = unreal.load_asset('/Game/_Art/Player/Character/Meshs/'+part+'/Player_Original_'+part+'_RigidBody_PhysicsAsset')
    settings = asset.get_editor_property('solver_settings')
    before = {k: settings.get_editor_property(k) for k in keys}
    settings.set_editor_property('fixed_time_step', step)
    settings.set_editor_property('position_iterations', iterations)
    settings.set_editor_property('velocity_iterations', velocity_iterations)
    settings.set_editor_property('projection_iterations', projection_iterations)
    settings.set_editor_property('use_linear_joint_solver', config.getboolean('ClothRefinement', 'UseLinearJointSolver' + part))
    asset.set_editor_property('solver_settings', settings)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
    rows.append(dict(part=part, before=before, after={k: settings.get_editor_property(k) for k in keys}, source='Assistant temporary stability tuning; not original game metadata'))
(root / 'Saved/PlayerClothSolverAuthor.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print(json.dumps(rows, indent=2))
