"""Read-only original PSA FK and current native-pose coordinate crosscheck."""
from pathlib import Path
import struct
import math
import json
import hashlib
import re
from check_box_semantics import quat, mul, rotate, vec

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PSA = Path('C:/Users/user/Desktop/카잔/BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1.psa')


def norm(q):
    m = math.sqrt(sum(v*v for v in q))
    return [v/m for v in q]


def slerp(a, b, t):
    dot = sum(x*y for x,y in zip(a,b))
    if dot < 0:
        b, dot = [-v for v in b], -dot
    if dot > .9995:
        return norm([x+(y-x)*t for x,y in zip(a,b)])
    angle = math.acos(max(-1,min(1,dot)))
    return [(x*math.sin((1-t)*angle)+y*math.sin(t*angle))/math.sin(angle) for x,y in zip(a,b)]


def main():
    data = PSA.read_bytes()
    chunks = {}
    offset = 0
    while offset+32 <= len(data):
        name, flags, size, count = struct.unpack_from('<20s3i', data, offset)
        offset += 32
        chunks[name.split(b'\0')[0].decode()] = (size, count, offset)
        offset += size*count
    size,n,offset = chunks['BONENAMES']
    bones = [struct.unpack_from('<64s3i11f',data,offset+i*size) for i in range(n)]
    names = [r[0].split(b'\0')[0].decode() for r in bones]
    size,count,offset = chunks['ANIMINFO']
    info = struct.unpack_from('<64s64s4i3f3i',data,offset)
    frames = info[-1]
    key_size,key_count,key_offset = chunks['ANIMKEYS']
    scale_size,scale_count,scale_offset = chunks['SCALEKEYS']
    report = json.loads((HERE/'SourceAttackWindows.json').read_text(encoding='utf-8'))
    composite = next(c for c in report['composites'] if c['package'].endswith('AC_Kazan_DualAxeSword_Com_WeakAtk01'))
    length = composite['animation_track_raw']['AnimSegments'][0]['AnimEndTime']
    fps = (frames-1)/length
    window = next(w for w in composite['attack_windows'] if w['bone_name_raw']=='Weapon_L')
    yaw = quat({'Yaw':-90})

    def local(index,time):
        f = min(max(time*fps,0),frames-1)
        lo,hi = int(f),min(int(f)+1,frames-1)
        out=[]
        for frame in (lo,hi):
            k=struct.unpack_from('<8f',data,key_offset+(frame*n+index)*key_size)
            p=[k[0],-k[1],k[2]]
            q=norm([k[3],-k[4],k[5],-k[6] if index==0 else k[6]])
            s=struct.unpack_from('<4f',data,scale_offset+(frame*n+index)*scale_size)[:3]
            out.append((p,q,s))
        alpha=f-lo
        p=[a+(b-a)*alpha for a,b in zip(out[0][0],out[1][0])]
        q=slerp(out[0][1],out[1][1],alpha)
        s=[a+(b-a)*alpha for a,b in zip(out[0][2],out[1][2])]
        return p,q,s

    def component(index,time):
        p,q,s=local(index,time)
        parent=bones[index][3]
        if parent<0 or parent==index:
            return p,q,s
        pp,pq,ps=component(parent,time)
        dp=rotate(pq,[x*y for x,y in zip(p,ps)])
        return [a+b for a,b in zip(pp,dp)],mul(pq,q),[a*b for a,b in zip(ps,s)]

    root_index=names.index('Root')
    weapon_index=names.index('Weapon_L')
    rows=[]
    for key in window['baked_keys']:
        time=key['time_seconds_raw']
        p,q,s=component(weapon_index,time)
        rp,rq,rs=component(root_index,time)
        root_inverse=[-rq[0],-rq[1],-rq[2],rq[3]]
        ground = rotate(yaw,rotate(root_inverse,[(a-b)/c for a,b,c in zip(p,rp,rs)]))
        ground_q=norm(mul(yaw,mul(root_inverse,q)))
        raw_q=quat(key['local_rotator_degrees_raw'])
        angle=math.degrees(2*math.acos(min(1,abs(sum(a*b for a,b in zip(ground_q,raw_q))))))
        raw=vec(key['local_center_pos_raw'])
        rows.append({'original_seconds':time,'psa_component_weapon_cm':p,'psa_root_translation_cm':rp,
                     'psa_root_removed_yaw_minus90_weapon_cm':ground,'original_baked_attachment_cm':raw,
                     'distance_cm':math.dist(ground,raw),
                     'psa_root_removed_yaw_minus90_quaternion_xyzw':ground_q,
                     'original_baked_quaternion_xyzw':raw_q,'rotation_difference_degrees':angle})

    pose_file=HERE.parent/'PoseWeak01.json'
    native=[]
    if pose_file.exists():
        pose=json.loads(pose_file.read_text(encoding='utf-8'))
        for sample in pose['samples']:
            t=sample['bones']['Weapon_L']
            pos=re.search(r'Translation=\(X=([^,]+),Y=([^,]+),Z=([^\)]+)\)',t)
            p=[float(v)*.01 for v in pos.groups()]
            ground=rotate(yaw,p)
            raw=vec(window['baked_keys'][0]['local_center_pos_raw'])
            native.append({'current_sequence':pose['sequence'],'current_time_seconds':sample['time'],
                           'extract_root_motion':sample['extract'],'component_translation_times_observed_mesh_scale_cm':p,
                           'component_times_scale_then_mesh_yaw_minus90_cm':ground,
                           'distance_to_first_original_baked_attachment_cm':math.dist(ground,raw)})
    result={'schema':1,'source_psa':str(PSA),'source_psa_sha256':hashlib.sha256(data).hexdigest(),
            'source_composite':{k:composite[k] for k in ('package','metadata_file','metadata_sha256','animation_track_raw')},
            'psa_chunks':{k:{'record_size':v[0],'records':v[1]} for k,v in chunks.items()},
            'sample_rate':{'psa_frames':frames,'original_composite_source_length_seconds':length,
                           'calculation':'(PSA frames - 1) / AnimTrack.AnimSegments[0].AnimEndTime',
                           'sample_fps_derived':fps,'psa_anim_rate_raw_not_used':info[8]},
            'import_conversion_source':'Plugins/UnrealPSKPSA/Source/UnrealPSKPSA/Private/PSAFactory.cpp:81-83',
            'import_conversion':'Position=(x,-y,z); Quaternion=(x,-y,z,root?-w:w).Normalize(); scale from SCALEKEYS.',
            'psa_crosscheck':rows,'current_native_pose_file':str(pose_file.relative_to(ROOT)),
            'current_native_pose_sha256':hashlib.sha256(pose_file.read_bytes()).hexdigest() if pose_file.exists() else None,
            'current_native_pose_crosscheck':native,
            'conclusions':{
                'status':'Coordinate origin is an inferred mapping corroborated by original PSA and current native pose; original native collision C++ is unavailable.',
                'already_actor_forward':'Baked ground keys approximately match source root-motion-removed pose rotated -90deg to actor-forward. Do not rotate baked keys -90deg a second time.',
                'spatial_scale':'Original metadata spatial numbers are already centimeters; do not multiply them by current mesh scale .01. Mesh pose scale .01 only applies to current imported component pose crosscheck.',
                'actor_origin':'Baked keys are ground/skeleton-root local rather than current capsule-center actor local. Add actual current BP mesh ground offset once before applying actor transform.',
                'current_bp_offset':'Parent own-editor30120 reports CharacterMesh0 RelativeZ=-88cm, Yaw=-90deg, scale=.01. This is current project configuration, not original metadata.',
                'residual':'PSA is older/coarse export (107 samples), current import/timing differs; centimeter residuals prevent calling this an exact skeletal equivalence proof.',
                'box_center':'This test compares attachment origins. Final box center must additionally compose RelativeOffset/AbsoluteOffset and RelativeRotatoion as proven by BoxSemantics.json.',
                'cylinder':'All34 original Cylinder attack windows in SourceAttackWindows.json have no valid baked Bounds. Cylinder radius/height convention cannot be proven by Bounds/Size.'}}
    (HERE/'CoordinateCrosscheck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'psa_rows':len(rows),'psa_first_distance_cm':rows[0]['distance_cm'],
                      'psa_first_rotation_difference_degrees':rows[0]['rotation_difference_degrees'],
                      'native_samples':len(native),'native_distances_cm':[x['distance_to_first_original_baked_attachment_cm'] for x in native]}))


if __name__=='__main__':
    main()
