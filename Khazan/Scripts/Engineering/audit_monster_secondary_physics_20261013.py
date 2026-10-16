"""Read-only saved component inventory in this task's separate editor process."""
from pathlib import Path
import json, os, unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
fn = unreal.SubobjectDataBlueprintFunctionLibrary
rows, meshes, physics = [], {}, {}

def path(obj):
    return obj.get_path_name() if obj else None

def property_or_none(obj, field):
    try:
        return obj.get_editor_property(field)
    except Exception:
        return None

def inspect_bp(package):
    bp = unreal.load_asset(package)
    if not bp:
        return
    components = []
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj = fn.get_associated_object(fn.get_data(handle))
        if not isinstance(obj, unreal.SkeletalMeshComponent):
            continue
        mesh = obj.get_editor_property('skeletal_mesh_asset')
        override = obj.get_editor_property('physics_asset_override')
        pa = override or (mesh.get_editor_property('physics_asset') if mesh else None)
        components.append(dict(name=obj.get_name(), mesh=path(mesh), physics=path(pa),
            override=path(override), animation=path(obj.get_editor_property('anim_class')),
            scale=str(obj.get_editor_property('relative_scale3d')),
            collision=str(obj.get_collision_enabled()),
            tags=[str(x) for x in obj.get_editor_property('component_tags')]))
        if mesh and path(mesh) not in meshes:
            meshes[path(mesh)] = dict(skeleton=path(mesh.get_editor_property('skeleton')),
                physics=path(mesh.get_editor_property('physics_asset')),
                post_process=path(property_or_none(mesh, 'post_process_anim_blueprint')),
                bones=[])
        if pa and path(pa) not in physics:
            physics[path(pa)] = dict(text=unreal.EditorAssetLibrary.get_metadata_tag(pa, 'OriginalSource'))
    rows.append(dict(blueprint=package,
        status=str(bp.get_editor_property('status')), components=components))

for item in sorted((root/'Content/Bluprints/Monsters').glob('*.uasset')):
    inspect_bp('/Game/Bluprints/Monsters/'+item.stem)
inspect_bp('/Game/_Art/Player/Character/Bluprints/BP_Player')
# No existing physics package was found by the stored enemy library search.
# Include all imported enemy body/part meshes to detect skins sharing gameplay BPs.
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
enemy_assets = registry.get_assets_by_path('/Game/_Art/Enemies/HeinMach', recursive=True)
asset_list = [dict(path=str(a.package_name), kind=str(a.asset_class_path.asset_name))
    for a in enemy_assets if str(a.asset_class_path.asset_name) in ('SkeletalMesh', 'PhysicsAsset', 'AnimBlueprint', 'Blueprint')]
data = dict(project=str(root), pid=os.getpid(), read_only=True, blueprints=rows,
    meshes=meshes, physics=physics, enemy_assets=asset_list)
(out/'Inventory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('MONSTER_SECONDARY_INVENTORY', len(rows), len(meshes), len(asset_list))
