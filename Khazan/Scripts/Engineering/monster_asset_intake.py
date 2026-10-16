"""Read-only public editor API audit in the isolated monster editor."""
import json
import pathlib
import unreal

root = pathlib.Path(unreal.Paths.project_dir()).resolve()
if 'Khazan_MonsterWork_20261006' not in str(root):
    raise RuntimeError('Work project only')
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
rows = []
for family, name in [('Swordsman', 'BP_EN_Swordsman_U01_L01'), ('SwordShield', 'BP_EN_SwordShield_U01_L01'), ('HeavySwordsman', 'BP_EN_HeavySwordsman_U01_L01'), ('HalberdElite', 'BP_EN_HalberdElite')]:
    bp = unreal.load_asset('/Game/_Art/Enemies/HeinMach/Humanoids/' + family + '/Blueprints/' + name)
    components = []
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        data = library.get_data(handle)
        obj = library.get_object_for_blueprint(data, bp)
        if isinstance(obj, unreal.SceneComponent):
            entry = {'name': obj.get_name(), 'class': obj.get_class().get_path_name(), 'location': str(obj.relative_location), 'rotation': str(obj.relative_rotation), 'scale': str(obj.relative_scale3d)}
            if isinstance(obj, unreal.SkeletalMeshComponent):
                entry.update(mesh=str(obj.skeletal_mesh_asset), skeleton=str(obj.skeletal_mesh_asset.skeleton) if obj.skeletal_mesh_asset else None, mode=str(obj.animation_mode), leader=str(obj.leader_pose_component))
            components.append(entry)
    rows.append({'family': family, 'components': components})
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
floor = next(a for a in actors if a.get_actor_label() == 'Floor')
result = {'assemblies': rows, 'floor_bounds': str(floor.get_actor_bounds(False)), 'state_tree_class': str(unreal.load_class(None, '/Script/Khazan.KZMonsterAIController'))}
out = root / 'Saved/MonsterAI/Intake.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
