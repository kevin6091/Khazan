"""Read-only Original mesh/PhysicsAsset/Blueprint audit in the isolated editor."""
import json
import pathlib
import unreal

root = pathlib.Path(unreal.Paths.project_dir()).resolve()
if 'Khazan_PlayerPartsWork_20261007' not in str(root):
    raise RuntimeError('Player parts audit requires its isolated editor')
out = root / 'Saved/PlayerPartsAudit.json'
audit = {}

def prop(obj, name):
    try:
        value = obj.get_editor_property(name)
        if isinstance(value, unreal.Object):
            return value.get_path_name()
        if hasattr(value, 'export_text'):
            return value.export_text()
        return str(value)
    except Exception as e:
        return 'not_exposed: ' + str(e)

paths = ['/Game/_Art/Player/Character/Meshs/SKM_Player', '/Game/_Art/Player/Character/Meshs/Player_PhysicsAsset']
for part in ('Torso', 'Shoes', 'Leg', 'Hair', 'Arm'):
    base = '/Game/_Art/Player/Character/Meshs/' + part + '/Player_Original_' + part
    paths += [base, base + '_PhysicsAsset']
for path in paths:
    asset = unreal.load_asset(path)
    if not asset:
        audit[path] = {'missing': True}
        continue
    row = {'class': asset.get_class().get_name()}
    if isinstance(asset, unreal.SkeletalMesh):
        row.update({k: prop(asset, k) for k in ('skeleton', 'physics_asset', 'post_process_anim_blueprint')})
        row['root_children'] = [str(n) for n in unreal.SkeletalMeshEditorSubsystem.get_bone_children(asset, 'root')]
    else:
        row.update({k: prop(asset, k) for k in ('skeletal_body_setups', 'constraint_setup', 'preview_skeletal_mesh')})
    audit[path] = row
bp = unreal.load_asset('/Game/_Art/Player/Character/Bluprints/BP_Player')
handles = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).k2_gather_subobject_data_for_blueprint(bp)
audit['bp_components'] = []
for h in handles:
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
    obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
    row = {'object': obj.get_path_name(), 'class': obj.get_class().get_name()}
    if isinstance(obj, unreal.SceneComponent):
        row.update({k: prop(obj, k) for k in ('relative_location', 'relative_rotation', 'relative_scale3d')})
    if isinstance(obj, unreal.SkeletalMeshComponent):
        row.update({k: prop(obj, k) for k in ('skeletal_mesh_asset', 'anim_class', 'physics_asset_override', 'animation_mode', 'visibility_based_anim_tick_option')})
    audit['bp_components'].append(row)
out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print('Saved PlayerPartsAudit:', out)
