from pathlib import Path
import json, os, traceback, unreal, math
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'); OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
d={'status':'running','rows':[]}
try:
    p=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
    cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_HalberdElite.BP_Monster_HalberdElite_C')
    m=unreal.get_default_object(cls).get_editor_property('Mesh'); bones=[str(m.get_bone_name(i)) for i in range(m.get_num_bones())]
    for e in p['events']:
        infos=e['source']['properties'].get('CorrectionInfos',[])
        if e['category']!='Attack' or not infos:continue
        a=unreal.load_asset(e['asset']); pts=e['source'].get('source_timing',{}).get('dilation_curve_raw',{}).get('DilationAnimPositions',[])
        candidates={b+'@'+str(y):[] for b in bones for y in (0,-90,90,180)};times=[]
        for info in infos:
            t=info['fTime'];mapped=t
            for x,y in zip(pts,pts[1:]):
                if x['T_Original']<=t<=y['T_Original']:
                    w=(t-x['T_Original'])/(y['T_Original']-x['T_Original']);mapped=x['T_Dilation']+(y['T_Dilation']-x['T_Dilation'])*w;break
            times.append(mapped); cs={}
            for b in bones:
                local=unreal.AnimationLibrary.get_bone_pose_for_time(a,b,mapped,False)
                parent=str(m.get_parent_bone(b))
                cs[b]=unreal.MathLibrary.compose_transforms(local,cs[parent]) if parent in cs else local
            tm=info['TM']; tr=tm['Translation']; q=tm['Rotation']
            for b,rawpose in cs.items():
                for yaw in (0,-90,90,180):
                    pose=unreal.MathLibrary.compose_transforms(rawpose,unreal.Transform(rotation=unreal.Rotator(yaw=yaw)))
                    v=pose.translation;r=pose.rotation
                    dist=math.sqrt((v.x-tr['X'])**2+(v.y-tr['Y'])**2+(v.z-tr['Z'])**2)
                    dot=min(1,abs(r.x*q['X']+r.y*q['Y']+r.z*q['Z']+r.w*q['W']))
                    candidates[b+'@'+str(yaw)].append({'cm':dist,'degrees':math.degrees(2*math.acos(dot))})
        ranked=sorted(candidates,key=lambda b:sum(x['cm']+x['degrees'] for x in candidates[b]))[:4]
        d['rows'].append({'event':e['event_id'],'asset':e['asset'],'baked_times':times,'nearest':[{'bone':b,'errors':candidates[b]} for b in ranked]})
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'CorrectionProbe.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
