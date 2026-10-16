"""Actual CMC before/after traversal of supported micro dressing, in own PIE only."""
from pathlib import Path
import datetime
import json
import math
import time
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007')
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert W
player=unreal.GameplayStatics.get_player_character(W,0);assert player
cmc=player.get_component_by_class(unreal.CharacterMovementComponent)
parts=[a.get_component_by_class(unreal.StaticMeshComponent) for a in unreal.GameplayStatics.get_all_actors_of_class(W,unreal.StaticMeshActor)
       if a.get_component_by_class(unreal.StaticMeshComponent).component_has_tag('HeinMachMicroDressing')]
rows=json.loads((OUT/'MicroDressing.json').read_text(encoding='utf-8'))['changed']
row=max(rows,key=lambda r:max(s.get('bump_cm',0) for s in r['samples']))
sample=max(row['samples'],key=lambda s:s.get('bump_cm',0))
X,Y=sample['x'],sample['y'];length=max(row['bounds_size'][0],200)+160
start_x=X-length*.5
saved=player.get_actor_location();saved_rotation=player.get_actor_rotation()
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),component=row['component'],
    reported_exposed_bump_cm=sample['bump_cm'],native_cmc=True,passes=[],temporary_test_distance_cm=length)
state=dict(phase='start',pass_index=0,next=0,deadline=time.monotonic()+180,samples=[])
def collision(block):
    for c in parts:c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,
        unreal.CollisionResponseType.ECR_BLOCK if block else unreal.CollisionResponseType.ECR_IGNORE)
def finish(error=None):
    collision(False);cmc.stop_movement_immediately()
    player.set_actor_location(saved,False,True);player.set_actor_rotation(saved_rotation,True)
    if error:report['error']=error
    report['success']=not error
    (OUT/'FloorCMCBeforeAfter.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    print('SNOW_CMC_FLOOR_QA',report['success'],[(p['mode'],p['distance_cm'],p['height_second_difference_rms_cm']) for p in report['passes']])
def summarize():
    samples=state['samples'];assert len(samples)>5
    x0=samples[0][0];x1=samples[-1][0]
    values=[];j=0
    for k in range(int((x1-x0)/10)+1):
        x=x0+k*10
        while j+1<len(samples) and samples[j+1][0]<x:j+=1
        if j+1>=len(samples):break
        a,b=samples[j],samples[j+1]
        if b[0]<=a[0]:continue
        values.append(a[2]+(b[2]-a[2])*(x-a[0])/(b[0]-a[0]))
    d2=[values[i-1]-2*values[i]+values[i+1] for i in range(1,len(values)-1)]
    return dict(mode='original_small_stone_collision' if state['pass_index']==0 else 'supported_ground_collision',
        distance_cm=x1-x0,samples_cm=samples,resampling_cm=10,
        height_second_difference_rms_cm=math.sqrt(sum(v*v for v in d2)/max(len(d2),1)))
def floor_tick(delta):
    try:
        now=unreal.GameplayStatics.get_time_seconds(W)
        if time.monotonic()>state['deadline']:return finish('Actual CMC traversal timed out')
        if state['phase']=='start':
            collision(state['pass_index']==0);cmc.stop_movement_immediately()
            hit=unreal.SystemLibrary.line_trace_single_by_profile(W,unreal.Vector(start_x,Y,sample['base_z']+500),
                unreal.Vector(start_x,Y,sample['base_z']-1000),'Pawn',True,[player],unreal.DrawDebugTrace.NONE,True)
            assert hit and hit.to_dict().get('blocking_hit'),'Fixture start has no Pawn floor'
            b=unreal.get_default_object(unreal.GameplayStatics).call_method('BreakHitResult',args=(hit,))
            half=player.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
            player.set_actor_location(unreal.Vector(start_x,Y,b[4].z+half+2),False,True)
            cmc.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
            state.update(phase='settle',next=now+1,samples=[]);return
        if state['phase']=='settle':
            if now<state['next']:return
            state.update(phase='move',next=now+6);return
        p=player.get_actor_location();state['samples'].append([p.x,p.y,p.z])
        if p.x-start_x<length and now<state['next']:
            player.add_movement_input(unreal.Vector(1,0,0),1.0,True);return
        cmc.stop_movement_immediately()
        result=summarize();report['passes'].append(result)
        if result['distance_cm']<length*.8:return finish('CMC did not traverse the selected supported path')
        if state['pass_index']==0:state.update(pass_index=1,phase='start');return
        before,after=report['passes']
        report['roughness_ratio']=after['height_second_difference_rms_cm']/max(before['height_second_difference_rms_cm'],1e-9)
        finish()
    except Exception as error:finish(str(error))
HANDLE=unreal.register_slate_post_tick_callback(floor_tick)
print('SNOW_CMC_FLOOR_QA_ARMED',row['label'])
