from pathlib import Path
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007')
before=json.loads((out/'SceneBefore.json').read_text())
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
rows=[]
for name,p in before['poses'].items():
    a=actors[name];v=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    now=[v.x,v.y,v.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
    if max(abs(x-y) for x,y in zip(now,p))>1e-6:rows.append(dict(actor=name,before=p,after=now,delta=[x-y for x,y in zip(now,p)]))
(out/'SavedPoseDeltas.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('SAVED_POSE_DELTA_ROWS',len(rows),json.dumps(rows[:4]))
