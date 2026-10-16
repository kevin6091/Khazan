"""Refresh only the snow clones' collision after changing their Nanite fallback precision."""
from pathlib import Path
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
meshes={c.static_mesh.get_path_name():c.static_mesh for a in E.get_all_level_actors()
    for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.component_has_tag('HeinMachSnowSurface')}
for m in meshes.values():
    unreal.KZSnowDeformation.rebuild_surface_collision(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007')
(out/'SurfaceCollisionRecook.json').write_text(json.dumps(dict(meshes=list(meshes),count=len(meshes)),indent=2),encoding='utf-8')
print('SNOW_COLLISION_RECOOKED',len(meshes))
