"""Exclude only supported shallow stone dressing from HeinMach Pawn collision/nav."""
from pathlib import Path
import datetime
import json
import math
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007'
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert W.get_name()=='L_HeinMach_Environment'
# Native temporary selection limits, not original values. Every candidate needs underlying support.
MAX_BOUNDS_HEIGHT_CM=60.0
MAX_XY_CM=800.0
MAX_EXPOSED_BUMP_CM=12.0
MIN_NORMAL_Z=math.cos(math.radians(44.0)) # Existing saved HeinMach nav slope, not original provenance.
TAG='HeinMachMicroDressing'
def vec(p):return [p.x,p.y,p.z]
def trace(p,ignore):
    h=unreal.SystemLibrary.line_trace_single_by_profile(W,p+unreal.Vector(0,0,100),p-unreal.Vector(0,0,1000),
        'Pawn',True,ignore,unreal.DrawDebugTrace.NONE,True)
    if not h or not h.to_dict().get('blocking_hit'):return None
    b=unreal.get_default_object(unreal.GameplayStatics).call_method('BreakHitResult',args=(h,))
    return dict(point=b[4],normal=b[6],actor=b[9],component=b[10])
rows=[];rejected=[];apply=[]
for a in E.get_all_level_actors():
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    if not c or not c.static_mesh or 'Stoneset' not in c.static_mesh.get_name():continue
    if c.component_has_tag(TAG):continue
    if c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)!=unreal.CollisionResponseType.ECR_BLOCK:continue
    center,ext=a.get_actor_bounds(False,False)
    if ext.z*2>MAX_BOUNDS_HEIGHT_CM or max(ext.x,ext.y)*2>MAX_XY_CM:continue
    samples=[];reason=None;active=0
    for x in (-0.85,0,0.85):
        for y in (-0.85,0,0.85):
            p=unreal.Vector(center.x+x*ext.x,center.y+y*ext.y,center.z+ext.z)
            top=trace(p,[])
            # A bounding-box corner outside the visible stone footprint is not
            # a removed floor. Validate support only where this stone blocks Pawn.
            if not top or top['actor']!=a:continue
            base=trace(p,[a])
            if not base or base['normal'].z<MIN_NORMAL_Z:
                reason='no walkable underlying support';break
            row=dict(x=p.x,y=p.y,underlying=base['actor'].get_actor_label(),base_z=base['point'].z,normal_z=base['normal'].z)
            if top and top['actor']==a:
                active+=1;row['top_z']=top['point'].z;row['bump_cm']=top['point'].z-base['point'].z
                if row['bump_cm']>MAX_EXPOSED_BUMP_CM:
                    reason='exposed height exceeds micro dressing limit';break
            samples.append(row)
        if reason:break
    if reason or not active:
        rejected.append(dict(label=a.get_actor_label(),reason=reason or 'no visible Pawn floor samples'));continue
    apply.append(c)
    rows.append(dict(label=a.get_actor_label(),actor=a.get_path_name(),component=c.get_path_name(),mesh=c.static_mesh.get_path_name(),
        bounds_size=vec(ext*2),samples=samples,pawn='Ignore',nav=False,visibility=str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))))
assert rows,'No verified supported micro dressing was found; do not claim smoothing'
for c in apply:
    c.modify()
    c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,unreal.CollisionResponseType.ECR_IGNORE)
    try:c.set_can_ever_affect_navigation(False)
    except AttributeError:c.set_editor_property('can_ever_affect_navigation',False)
    c.set_editor_property('component_tags',list(c.component_tags)+[unreal.Name(TAG)])
unreal.SystemLibrary.execute_console_command(W,'RebuildNavigation')
assert unreal.EditorLoadingAndSavingUtils.save_map(W,'/Game/Maps/L_HeinMach_Environment')
previous=json.loads((OUT/'MicroDressing.json').read_text(encoding='utf-8')) if (OUT/'MicroDressing.json').exists() else {}
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),changed=previous.get('changed',[])+rows,rejected=rejected,
    temporary_limits=dict(bounds_height_cm=MAX_BOUNDS_HEIGHT_CM,xy_cm=MAX_XY_CM,exposed_bump_cm=MAX_EXPOSED_BUMP_CM),
    selection='Only exposed Pawn-blocking samples within the actual stone footprint require underlying walkable support; outside bounding-box samples do not remove a floor.',
    preserved='Actor poses, visibility/other collision channels, large rocks, terrain, route walls and NavLinks unchanged')
(OUT/'MicroDressing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEINMACH_MICRO_DRESSING_SAVED',len(rows),'rejected',len(rejected))
