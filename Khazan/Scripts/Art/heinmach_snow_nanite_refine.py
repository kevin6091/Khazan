"""Keep displaced terrain's Nanite base geometry from simplifying away from its collision."""
from pathlib import Path
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
W=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
S=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
meshes={c.static_mesh.get_path_name():c.static_mesh for a in E.get_all_level_actors()
    for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.component_has_tag('HeinMachSnowSurface')}
for m in meshes.values():
    settings=m.get_editor_property('nanite_settings')
    # Temporary technical limit in screen-space; UE MaxEdgeLengthFactor preserves deformation geometry.
    settings.set_editor_property('max_edge_length_factor',2.0)
    S.set_nanite_settings(m,settings,apply_changes=True)
    unreal.KZSnowDeformation.rebuild_surface_collision(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007')
(out/'NaniteRefinement.json').write_text(json.dumps(dict(meshes=list(meshes),max_edge_length_factor=2.0,
    provenance='native technical setting; not an original coefficient'),indent=2),encoding='utf-8')
print('SNOW_NANITE_REFINED',len(meshes))
