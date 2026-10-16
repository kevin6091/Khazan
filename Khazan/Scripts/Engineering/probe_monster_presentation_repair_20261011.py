"""Read current sockets, body parents and every saved attack visual occurrence."""
from pathlib import Path
from collections import Counter
import json, os, traceback, unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
report={'status':'running','project':str(WORK),'families':[],'attack_assets':[],'missing_socket_events':[],'package_saves':0}
try:
    plan=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
    rows=[e for e in plan['events'] if e['category']=='Attack']
    by_family={}
    for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
        path='/Game/Bluprints/Monsters/BP_Monster_'+family
        cls=unreal.load_class(None,path+'.BP_Monster_'+family+'_C');assert cls,path
        cdo=unreal.get_default_object(cls);mesh=cdo.get_editor_property('Mesh')
        by_family[family]=mesh
        body=[]
        for m in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
            sk=m.get_editor_property('skeletal_mesh')
            if not sk:continue
            mats=[]
            for i in range(m.get_num_materials()):
                mat=m.get_material(i)
                parent=mat.get_editor_property('parent') if isinstance(mat,unreal.MaterialInstanceConstant) else mat
                mats.append({'slot':i,'material':mat.get_path_name() if mat else None,'parent':parent.get_path_name() if parent else None})
            body.append({'component':m.get_name(),'skeletal_mesh':sk.get_path_name(),'materials':mats})
        bones=[str(mesh.get_bone_name(i)) for i in range(mesh.get_num_bones())]
        report['families'].append({'family':family,'bones':bones,'body':body,'mesh_rotation':str(mesh.get_editor_property('relative_rotation')),'mesh_scale':str(mesh.get_editor_property('relative_scale3d'))})
    for asset in sorted(set(e['asset'] for e in rows)):
        seq=unreal.load_asset(asset);assert seq,asset
        saved=[]
        for evt in unreal.AnimationLibrary.get_animation_notify_events(seq):
            data=evt.get_editor_property('notify_state_class')
            if not isinstance(data,unreal.KZAnimNotifyState_MonsterVisual):continue
            effect=data.get_editor_property('Effect')
            if not effect:continue
            eid=str(effect.get_editor_property('EventId'))
            authored=next((e for e in rows if e['event_id']==eid),None)
            if not authored:continue
            socket=str(effect.get_editor_property('SourceSocket'))
            mesh=by_family[authored['family']]
            exists=socket=='None' or mesh.does_socket_exist(socket)
            if not exists:report['missing_socket_events'].append({'asset':asset,'event':eid,'socket':socket})
            saved.append({'event':eid,'socket':socket,'socket_exists':exists,'attached':bool(effect.get_editor_property('bAttached')),'absolute_rotation':bool(effect.get_editor_property('bAbsoluteRotation')),'source_world_owner':authored['source']['properties'].get('bConvert_bWorldOwner'),'source_correction_infos':len(authored['source']['properties'].get('CorrectionInfos',[])),'runtime_source_correction':bool(effect.get_editor_property('bUseSourceCorrection'))})
        report['attack_assets'].append({'asset':asset,'events':saved})
    report['attack_occurrences']=len(rows)
    report['saved_attack_occurrences']=sum(len(a['events']) for a in report['attack_assets'])
    report['status']='passed'
except Exception:
    report['status']='failed';report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'Probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if os.environ['KZ_MONSTER_REPAIR_MODE']!='commandlet':unreal.SystemLibrary.quit_editor()
