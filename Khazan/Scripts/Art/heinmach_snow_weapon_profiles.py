"""Author rigid weapon points from the four delivered Monster Blueprints."""
from pathlib import Path
import datetime
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
U=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not U.get_game_world(),'End the task-owned PIE before saving'
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
snow=next(a for a in E.get_all_level_actors() if isinstance(a,unreal.KZSnowDeformation))
meshes={};families=[];spawned=[]
try:
    for name in ('Swordsman','SwordShield','HeavySwordsman','HalberdElite'):
        cls=unreal.load_class(None,f'/Game/Bluprints/Monsters/BP_Monster_{name}.BP_Monster_{name}_C')
        actor=E.spawn_actor_from_class(cls,unreal.Vector(0,0,50000));spawned.append(actor)
        parts=[]
        for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            m=c.get_editor_property('skeletal_mesh_asset')
            if not m:continue
            meshes[m.get_path_name()]=m
            parts.append(dict(component=c.get_name(),mesh=m.get_path_name()))
        families.append(dict(family=name,parts=parts))
    count=snow.author_merged_weapon_contacts(list(meshes.values()))
    assert count>0
    rows=[]
    for p in snow.get_editor_property('merged_weapon_contacts'):
        mesh=p.get_editor_property('mesh')
        rows.append(dict(mesh=mesh.get_path_name(),bone=str(p.get_editor_property('bone')),
            bone_local_points_cm=[[v.x,v.y,v.z] for v in p.get_editor_property('points')]))
finally:
    for actor in spawned:E.destroy_actor(actor)
assert unreal.EditorLoadingAndSavingUtils.save_map(U.get_editor_world(),'/Game/Maps/L_HeinMach_Environment')
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/MergedWeaponProfiles.json')
out.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),profiles=count,
    mesh_inputs=list(meshes),families=families,points=rows,
    provenance='Native imported LOD0 soft vertices: dominant weapon bone weight >= half of summed weights; reference-pose inverse bone transform; centre and actual XYZ extremes. Authored once, no per-frame vertex skinning.'),indent=2),encoding='utf-8')
print('SNOW_MERGED_WEAPON_PROFILES_SAVED',count,len(meshes))
