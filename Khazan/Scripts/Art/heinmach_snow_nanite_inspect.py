from pathlib import Path
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
a=next(a for a in actors if a.get_name()=='StaticMeshActor_9221')
c=a.get_component_by_class(unreal.StaticMeshComponent);m=c.static_mesh
s=m.get_editor_property('nanite_settings')
print('NaniteSettings',s)
print('cooked',m.get_editor_property('lod_for_collision'),m.get_editor_property('complex_collision_mesh'))
for cls in (unreal.StaticMeshEditorSubsystem,unreal.EditorStaticMeshLibrary):
    print(cls.__name__,[n for n in dir(cls) if any(k in n for k in ('nanite','build','lod','compile'))])
print('material',c.get_material(0),c.get_material(0).get_editor_property('displacement_scaling'))
