"""Reuse the saved single-map inventory to prepare conservative spatial candidates."""
from pathlib import Path
import collections, itertools, json, math, re
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'Metadata/HeinMachRoutePrune_20261016'
data=json.loads((TASK/'Inventory01/Inventory.json').read_text(encoding='utf-8'))
actors=data['actors']
byname={a['name']:a for a in actors}
route=[a for a in actors if (a['label'].startswith('BP_Monster') and 'Yetuga' not in a['label'])
       or a['label'] in ['PlayerStart','HM_Yetuga_EntrancePortal']]
boss=next(a for a in actors if a['label']=='BP_Monster_Yetuga')['location']
# These are conservative authoring/QA envelopes, not original gameplay tuning.
zones=[dict(name='StartToPortal',low=[min(a['location'][0] for a in route)-1800,
    min(a['location'][1] for a in route)-1800,-2000],high=[max(a['location'][0] for a in route)+1800,
    max(a['location'][1] for a in route)+1800,4500]),
    dict(name='YetugaArena',low=[boss[0]-5000,boss[1]-5000,-7000],high=[boss[0]+5000,boss[1]+5000,1500])]

def intersects(bounds,zone,extra=0):
    p,e=bounds
    return all(p[i]+e[i]+extra>=zone['low'][i] and p[i]-e[i]-extra<=zone['high'][i] for i in range(3))

def in_zone(bounds,extra=0):return any(intersects(bounds,z,extra) for z in zones)

def instance_bounds(text,meshbox):
    fields=re.findall(r'(?:X|Y|Z|W)=([-+\d.eE]+)',text)
    q=list(map(float,fields[:4]));t=list(map(float,fields[4:7]));s=list(map(float,fields[7:10]))
    x,y,z,w=q
    matrix=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    center=[(meshbox[0][i]+meshbox[1][i])*.5*s[i] for i in range(3)]
    extent=[abs((meshbox[1][i]-meshbox[0][i])*.5*s[i]) for i in range(3)]
    return [[t[i]+sum(matrix[i][j]*center[j] for j in range(3)) for i in range(3)],
            [sum(abs(matrix[i][j])*extent[j] for j in range(3)) for i in range(3)]]

entries=[];camera_anchors=[]
global_classes=['DirectionalLight','SkyLight','SkyAtmosphere','ExponentialHeightFog','PostProcessVolume',
    'PlayerStart','TargetPoint','KZBossPortal','KZSnowDeformation','KZLevelRouteCollisionActor','RecastNavMesh','NiagaraActor']
for a in actors:
    if a in route or a['label'] in ['HM_Yetuga_ArenaArrival','BP_Monster_Yetuga']:
        camera_anchors.append(dict(name=a['name'],label=a['label'],position=a['location'],kind='authored_gameplay'))
    if a['cls'].endswith('KZNavMeshBoundsBox') and in_zone(a['bounds']):
        p=a['bounds'][0]
        # Avoid expanding the camera survey into the unused original route.
        route_core=(11000<=p[0]<=20000 and 3200<=p[1]<=15000 and -600<=p[2]<=1500)
        arena_core=(boss[0]-3600<=p[0]<=boss[0]+3600 and boss[1]-3600<=p[1]<=boss[1]+3600 and p[2]<-2500)
        if route_core or arena_core:
            if all(math.dist(p,c['position'])>1200 for c in camera_anchors):
                camera_anchors.append(dict(name=a['name'],label=a['label'],position=p,kind='saved_navigation_volume'))
    instanced=False
    for c in a['components']:
        if 'instances' not in c:continue
        instanced=True
        for i,t in enumerate(c['instances']):
            b=instance_bounds(t,c['mesh_local_bounds'])
            entries.append(dict(key=a['name']+'|'+c['name']+'|'+str(i),actor=a['name'],label=a['label'],
                component=c['name'],index=i,kind='instance',bounds=b,
                reason='used_zone' if in_zone(b) else 'candidate'))
    if instanced:continue
    reason='candidate'
    cls=a['cls'].split('.')[-1]
    b=a['bounds']
    if cls in global_classes or a['label'].startswith('BP_Monster') or a['label']=='GateCube':reason='gameplay_or_global'
    elif a['label'].startswith('HM_Terrain_'):reason='shared_ground'
    elif in_zone(b):reason='used_zone'
    light=next((c['light'] for c in a['components'] if 'light' in c),None)
    if light and cls in ['PointLight','SpotLight']:
        radius=float(light['attenuation_radius'])
        b=[a['location'],[radius]*3]
        if in_zone(b,1500):reason='light_reaches_used_zone'
    # Ambient attenuation is checked against its native settings in the UE probe.
    entries.append(dict(key=a['name'],actor=a['name'],label=a['label'],kind='actor',bounds=b,
                        cls=a['cls'],folder=a['folder'],reason=reason))

# Shadow preservation: project each candidate's AABB along the saved sun direction
# onto both protected gameplay elevation bands; this intentionally over-retains.
sun=next(a for a in actors if a['cls'].endswith('.DirectionalLight'))
q=list(map(float,re.findall(r'(?:X|Y|Z|W)=([-+\d.eE]+)',sun['pose'])[:4]))
x,y,z,w=q;direction=[1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w)]
for e in entries:
    if e['reason']!='candidate' or direction[2]>=-.01:continue
    p,h=e['bounds']
    for zone in zones:
        plane=0 if zone['name']=='StartToPortal' else -4600
        shadows=[]
        for signs in itertools.product((-1,1),repeat=3):
            v=[p[i]+signs[i]*h[i] for i in range(3)]
            t=max(0,(plane-v[2])/direction[2])
            shadows.append([v[i]+t*direction[i] for i in range(3)])
        if all(max(v[i] for v in shadows)>=zone['low'][i]-600 and min(v[i] for v in shadows)<=zone['high'][i]+600 for i in (0,1)):
            e['reason']='potential_shadow';break

plan=dict(map=data['map'],source='Inventory01/Inventory.json',zones=zones,camera_anchors=camera_anchors,
    entries=entries,sun_direction=direction,qa_policy=dict(route_margin_cm=1800,arena_half_extent_cm=5000,
    light_extra_margin_cm=1500,shadow_margin_cm=600,anchor_spacing_cm=1200,
    numeric_source='Assistant selected conservative deletion/QA margins; not original-game or runtime tuning'),
    counts=dict(collections.Counter(e['reason'] for e in entries)))
(TASK/'Plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(entities=len(entries),anchors=len(camera_anchors),counts=plan['counts']),ensure_ascii=False))

image=Image.new('RGB',(1400,1000),(20,25,32));draw=ImageDraw.Draw(image)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
def px(v):return (int(80+(v[0]+20000)*.022),int(920-(v[1]+26000)*.016))
for e in entries:
    p,h=e['bounds'];xx,yy=px(p)
    color=(69,77,88) if e['reason']=='candidate' else (80,143,173)
    if 0<=xx<1400 and 0<=yy<1000:draw.ellipse((xx-1,yy-1,xx+1,yy+1),fill=color)
for zone in zones:
    x1,y2=px(zone['low']);x2,y1=px(zone['high'])
    draw.rectangle((x1,y1,x2,y2),outline=(88,225,143),width=3)
    draw.text((x1,y1-22),zone['name'],fill=(130,245,160),font=font)
for i,c in enumerate(camera_anchors):
    x,y=px(c['position']);draw.ellipse((x-4,y-4,x+4,y+4),fill=(255,175,70))
    if c['kind']=='authored_gameplay':draw.text((x+5,y-5),c['label'].replace('BP_Monster_',''),fill=(255,220,130),font=font)
draw.text((20,12),'HeinMach: green = protected envelope / blue = protected / gray = candidates / orange = camera anchors',fill='white',font=font)
image.save(TASK/'SpatialPlan.png')
