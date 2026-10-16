from pathlib import Path
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
rows=[]
for name in ('Swordsman','SwordShield','HeavySwordsman','HalberdElite'):
    cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+name+'.BP_Monster_'+name+'_C')
    obj=unreal.get_default_object(cls)
    parts=[]
    for c in obj.get_components_by_class(unreal.SkeletalMeshComponent):
        m=c.get_editor_property('skeletal_mesh_asset')
        if not m:continue
        bones=[str(c.get_bone_name(i)) for i in range(c.get_num_bones())]
        parts.append(dict(component=c.get_name(),asset=m.get_path_name(),socket=str(c.get_attach_socket_name()),
            relevant_bones=[b for b in bones if any(k in b.lower() for k in ('weapon','sword','axe','halberd','foot','pelvis'))]))
    rows.append(dict(family=name,parts=parts))
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/MonsterContactRigs.json')
out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows))
