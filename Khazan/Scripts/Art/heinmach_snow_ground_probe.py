"""Saved HeinMach ground/collision evidence; no asset or map authoring."""
from pathlib import Path
from collections import Counter
import datetime
import json
import math
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007'
OUT.mkdir(exist_ok=True)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world and world.get_name()=='L_HeinMach_Environment', 'Run in the warmed task-owned editor'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
def vec(v):return [v.x,v.y,v.z]
def pose(a):
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
start=next(a for a in actors if isinstance(a,unreal.PlayerStart))
snapshot=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actors=len(actors),
    poses={a.get_actor_label():pose(a) for a in actors},player_start=pose(start),
    snow_surface_count=sum(c.component_has_tag('HeinMachSnowSurface') for a in actors for c in a.get_components_by_class(unreal.StaticMeshComponent)))
(OUT/'SceneSnowStaged.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
profiles=[];colliders={}
origin=start.get_actor_location()
for angle in (0,45,90,135):
    samples=[]
    for i in range(-60,121):
        p=origin+unreal.Vector(math.cos(math.radians(angle))*i*10,math.sin(math.radians(angle))*i*10,0)
        hit=unreal.SystemLibrary.line_trace_single_by_profile(world,p+unreal.Vector(0,0,1200),p-unreal.Vector(0,0,1800),
            'Pawn',True,[],unreal.DrawDebugTrace.NONE,True)
        data=hit.to_dict() if hit else {}
        actor=data.get('hit_actor');point=data.get('impact_point');component=data.get('hit_component') or data.get('component')
        # UE's break node exposes UObject references omitted by some HitResult.to_dict bindings.
        if data.get('blocking_hit'):
            broken=unreal.get_default_object(unreal.GameplayStatics).call_method('BreakHitResult',args=(hit,))
            actor=broken[9];component=broken[10];point=broken[4]
        label=actor.get_actor_label() if actor else None
        samples.append(dict(x=p.x,y=p.y,hit=bool(data.get('blocking_hit')),label=label,point=vec(point) if point else None))
        if actor and component and label not in colliders:
            center,extent=actor.get_actor_bounds(False,False)
            mesh=component.static_mesh if isinstance(component,unreal.StaticMeshComponent) else None
            colliders[label]=dict(actor=actor.get_path_name(),component=component.get_path_name(),mesh=mesh.get_path_name() if mesh else None,
                bounds_center=vec(center),bounds_size=vec(extent*2),tags=[str(t) for t in actor.tags],
                pawn_response=str(component.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)),
                step_up=str(component.get_editor_property('can_character_step_up_on')))
    profiles.append(dict(angle=angle,spacing_cm=10,samples=samples))
assert colliders, 'Ground probe found no blocking collision; physics evidence invalid'
report=dict(utc=snapshot['utc'],profiles=profiles,colliders=colliders,trace='Pawn profile, complex; trace evidence only, not CMC trajectory')
(OUT/'GroundBaseline.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEINMACH_GROUND_PROBE_PASSED',json.dumps(dict(actors=len(actors),colliders=len(colliders),
    labels=Counter(p['label'] for path in profiles for p in path['samples']))))
