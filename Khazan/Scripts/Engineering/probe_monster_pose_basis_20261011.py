from pathlib import Path
import json, os, traceback, unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
d={'status':'running','public_api':str(unreal.AnimationLibrary.get_bone_pose_for_time.__doc__),'poses':[]}
try:
    p=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
    for f in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
        e=next(e for e in p['events'] if e['family']==f and e['category']=='Attack')
        a=unreal.load_asset(e['asset'])
        cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+f+'.BP_Monster_'+f+'_C')
        m=unreal.get_default_object(cls).get_editor_property('Mesh')
        chain=[];b='Bip001-Spine2'
        while b and b!='None':
            chain.append({'bone':b,'parent':str(m.get_parent_bone(b)),'pose':str(unreal.AnimationLibrary.get_bone_pose_for_time(a,b,e['start_time'],False)),'reference_world':str(m.get_socket_transform(b,unreal.RelativeTransformSpace.RTS_WORLD))})
            b=str(m.get_parent_bone(b))
        d['poses'].append({'family':f,'asset':e['asset'],'time':e['start_time'],'mesh':str(m.get_editor_property('relative_rotation')),'chain':chain})
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'PoseBasis.json').write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
