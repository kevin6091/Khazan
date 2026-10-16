"""Targeted rock/dressing collision inventory in the isolated warm editor."""
from pathlib import Path
from collections import defaultdict
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
records=[];groups=defaultdict(list)
def v(p):return [p.x,p.y,p.z]
for a in E.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        m=c.static_mesh
        if not m or not any(k in m.get_name().lower() for k in ('rock','stone','ground','deco','pebble')):continue
        if c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)!=unreal.CollisionResponseType.ECR_BLOCK:continue
        center,extent=a.get_actor_bounds(False,False)
        row=dict(label=a.get_actor_label(),actor=a.get_path_name(),component=c.get_path_name(),mesh=m.get_path_name(),
            center=v(center),size=v(extent*2),tags=[str(t) for t in a.tags],step_up=str(c.get_editor_property('can_character_step_up_on')))
        records.append(row);groups[m.get_name()].append(row)
nav=[]
for a in E.get_all_level_actors():
    if isinstance(a,unreal.RecastNavMesh):
        row=dict(actor=a.get_path_name())
        for p in ('cell_size','cell_height','agent_radius','agent_height','agent_max_slope','agent_max_step_height','max_simplification_error'):
            try:row[p]=a.get_editor_property(p)
            except Exception as ex:row[p]=str(ex)
        nav.append(row)
summary={k:dict(count=len(rows),min_height_cm=min(r['size'][2] for r in rows),max_height_cm=max(r['size'][2] for r in rows),
    min_xy_cm=min(max(r['size'][:2]) for r in rows)) for k,rows in groups.items()}
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/GroundCandidates.json')
out.write_text(json.dumps(dict(records=records,groups=summary,nav=nav),indent=2),encoding='utf-8')
print(json.dumps(dict(records=len(records),groups=summary,nav=nav)))
