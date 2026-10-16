"""Read-only saved/runtime configuration check in the isolated PlayerParts editor."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
if root != Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan').resolve():
    raise RuntimeError('PlayerParts readback requires its isolated editor')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not world:
    raise RuntimeError('Start isolated PIE first; readback never starts gameplay itself')
player_class = unreal.load_class(None, '/Game/_Art/Player/Character/Bluprints/BP_Player.BP_Player_C')
players = unreal.GameplayStatics.get_all_actors_of_class(world, player_class)
if len(players) != 1:
    raise RuntimeError('Expected one actual BP_Player pawn')
player = players[0]
components = player.get_components_by_class(unreal.SkeletalMeshComponent)
data = {'project': str(root), 'player': player.get_path_name(), 'components': []}
for component in components:
    name = component.get_name()
    if name not in ('CharacterMesh0', 'Torso', 'Shoes', 'Leg', 'Hair', 'Arm'):
        continue
    mesh = component.get_editor_property('skeletal_mesh_asset')
    physics = component.get_editor_property('physics_asset_override') or mesh.get_editor_property('physics_asset')
    anim = component.get_anim_instance()
    row = {'name': name, 'mesh': mesh.get_path_name(), 'physics': physics.get_path_name(),
           'animation': anim.get_class().get_path_name() if anim else None,
           'parent': component.get_attach_parent().get_name() if component.get_attach_parent() else None,
           'relative_scale': str(component.get_editor_property('relative_scale3d')),
           'world_scale': str(component.get_world_scale()),
           'collision': str(component.get_collision_enabled()),
           'world_simulation': component.is_any_simulating_physics()}
    # Socket transforms are actual final rendered bone transforms, read only.
    row['bone_samples'] = {str(bone): str(component.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD))
                           for bone in component.get_all_socket_names()
                           if str(bone).startswith(('B_Cape_', 'B_Cloth_', 'Hair_'))}
    data['components'].append(row)
names = {row['name'] for row in data['components']}
assert names == {'CharacterMesh0', 'Torso', 'Shoes', 'Leg', 'Hair', 'Arm'}, names
for row in data['components']:
    if row['name'] != 'CharacterMesh0':
        assert row['mesh'].endswith('Player_Original_' + row['name']), row
        assert row['physics'].endswith('Player_Original_' + row['name'] + '_PhysicsAsset'), row
        assert row['parent'] == 'CharacterMesh0', row
        assert row['animation'].endswith('ABP_Player_Original_' + row['name'] + '_C'), row
    else:
        assert row['physics'].endswith('Player_PhysicsAsset'), row
    assert not row['world_simulation'], row
out = root / 'Saved/PlayerPartsRuntimeReadback.json'
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Actual saved/runtime Original-part configuration checked:', out)
