"""Conservative AABB depth occlusion over the recorded six-direction views."""
from pathlib import Path
import array, collections, json, math, sys

ROOT=Path(__file__).resolve().parents[2];TASK=ROOT/'Metadata/HeinMachRoutePrune_20261016'
plan=json.loads((TASK/'Plan.json').read_text())
DEPTH=sys.argv[1] if len(sys.argv)>1 else 'Depth02'
survey=json.loads((TASK/DEPTH/'DepthViews.json').read_text())
assert survey['success'] and len(survey['views'])==len(survey['anchors'])*6
inventory=json.loads((TASK/'Inventory01/Inventory.json').read_text())
actors={a['name']:a for a in inventory['actors']}
audio={a['actor']:a for a in json.loads((TASK/DEPTH/'AudioInfluence.json').read_text())}
N=survey['resolution'];pending={};retained={};nonvisual=[]
nonvisual_classes=['KZNavMeshBoundsBox','KZNavModifierBox','NavLinkProxy','AudioVolume']
for e in plan['entries']:
    a=actors[e['actor']]
    shadow=any(c.get('mesh') and c.get('cast_shadow') for c in a['components'])
    if e['reason']=='potential_shadow' and not shadow:e['reason']='candidate'
    if e['reason']!='candidate':retained[e['key']]=dict(e,retain_reason=e['reason']);continue
    if a['cls'].split('.')[-1] in nonvisual_classes:
        nonvisual.append(dict(e,delete_reason='outside_protected_gameplay_volume'));continue
    if a['cls'].endswith('.AmbientSound'):
        radius=audio.get(a['name'],{}).get('cached_max_distance')
        # SoundBase caches the full static cue-graph maximum on editor load.
        # Unknown/unbounded sound is retained; no cue graph or gain is changed.
        if radius is None or radius<=0 or radius>=1000000:
            retained[e['key']]=dict(e,retain_reason='unbounded_or_unknown_audio');continue
        reaches=any(all(a['location'][i]+radius+1500>=zone['low'][i] and a['location'][i]-radius-1500<=zone['high'][i]
                        for i in range(3)) for zone in plan['zones'])
        if reaches:retained[e['key']]=dict(e,retain_reason='audio_reaches_used_zone',radius_cm=radius)
        else:nonvisual.append(dict(e,delete_reason='audio_outside_used_zone_and_radius',radius_cm=radius))
        continue
    pending[e['key']]=e

def pyramid(values):
    levels=[(N,[v if math.isfinite(v) and v>0 else 1e30 for v in values])]
    while levels[-1][0]>1:
        n,old=levels[-1];m=n//2
        new=[max(old[(2*y)*n+2*x],old[(2*y)*n+2*x+1],old[(2*y+1)*n+2*x],old[(2*y+1)*n+2*x+1])
             for y in range(m) for x in range(m)]
        levels.append((m,new))
    return levels

def maximum(levels,x0,y0,x1,y1):
    level=max(0,int(math.log2(max(1,min(x1-x0+1,y1-y0+1)))))
    scale=1<<level;n,values=levels[level]
    return max(values[y*n+x] for y in range(y0//scale,y1//scale+1) for x in range(x0//scale,x1//scale+1))

coverage=collections.Counter()
for view in survey['views']:
    depths=array.array('f');depths.frombytes((TASK/DEPTH/view['file']).read_bytes())
    assert len(depths)==N*N and max(depths)>0
    levels=pyramid(depths)
    f,r,u=view['forward'],view['right'],view['up'];eye=view['eye']
    for key,e in list(pending.items()):
        center,half=e['bounds'];d=[center[i]-eye[i] for i in range(3)]
        # QA-only expansion protects animated vegetation and camera/depth raster uncertainty.
        h=[v+100 for v in half]
        x=sum(d[i]*r[i] for i in range(3));y=sum(d[i]*u[i] for i in range(3));z=sum(d[i]*f[i] for i in range(3))
        ex=sum(h[i]*abs(r[i]) for i in range(3));ey=sum(h[i]*abs(u[i]) for i in range(3));ez=sum(h[i]*abs(f[i]) for i in range(3))
        near,far=z-ez,z+ez
        if far<=0 or x-ex>far or x+ex<-far or y-ey>far or y+ey<-far:continue
        coverage[key]+=1
        if near<=10:
            retained[key]=dict(e,retain_reason='intersects_camera_near_plane',view=view['index']);del pending[key];continue
        xs=[(x+s*ex)/depth for s in [-1,1] for depth in [near,far]]
        ys=[(y+s*ey)/depth for s in [-1,1] for depth in [near,far]]
        x0=max(0,int(math.floor((min(xs)+1)*N/2))-3);x1=min(N-1,int(math.ceil((max(xs)+1)*N/2))+3)
        y0=max(0,int(math.floor((1-max(ys))*N/2))-3);y1=min(N-1,int(math.ceil((1-min(ys))*N/2))+3)
        if x0>x1 or y0>y1:continue
        scene_max=maximum(levels,x0,y0,x1,y1)
        if scene_max>=near-max(100,near*.02):
            retained[key]=dict(e,retain_reason='potentially_visible',view=view['index']);del pending[key]
    if view['index']%24==23:print('VIEWS',view['index']+1,'remaining hidden candidates',len(pending),flush=True)

deleted=[]
for key,e in pending.items():
    assert coverage[key]>0,key
    deleted.append(dict(e,delete_reason='occluded_in_all_sampled_views',tested_views=coverage[key]))
deleted+=nonvisual
# Attached actors cannot lose their surviving parent.
retained_actors={e['actor'] for e in retained.values()}
parent_names={actors[name]['parent'].rsplit('.',1)[-1] for name in retained_actors if actors[name]['parent']}
for e in list(deleted):
    if e['kind']=='actor' and e['actor'] in parent_names:
        deleted.remove(e);retained[e['key']]=dict(e,retain_reason='parent_of_retained_actor')
result=dict(status='candidate_for_visual_review',depth_source=DEPTH,views=len(survey['views']),qa_margins=dict(bounds_cm=100,pixels=3,depth_cm=100,depth_ratio=.02),
    deleted=deleted,retained=list(retained.values()),
    counts=dict(removed_actors=sum(e['kind']=='actor' for e in deleted),removed_instances=sum(e['kind']=='instance' for e in deleted),
    retained=len(retained)),removed_classes=dict(collections.Counter(e.get('cls','HISM instance') for e in deleted)),
    reasons=dict(collections.Counter(e['retain_reason'] for e in retained.values())))
(TASK/('VisibilityCandidates_'+DEPTH+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ['counts','removed_classes','reasons']},ensure_ascii=False,indent=2))
