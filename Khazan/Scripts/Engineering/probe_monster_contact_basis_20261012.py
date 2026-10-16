"""Compare serialized attack anchors with raw/locked skeleton poses; no asset writes."""
from pathlib import Path
import unreal,json,os,traceback,math
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');OUT=Path(os.environ['KZ_MONSTER_CONTACT_OUT'])
d={'status':'running','asset_saves':0,'rows':[],'montages':[]}
def v(x):return [float(x.x),float(x.y),float(x.z)]
def rawvec(x):return unreal.Vector(*[float((x or {}).get(a,0)) for a in 'XYZ'])
def prop(o,n):return o.get_editor_property(n)
try:
    plan=json.loads((MAIN/'Metadata/CombatReaction_20261008/MonsterAttackCollisionPlan.json').read_text(encoding='utf-8'))
    usage=json.loads((MAIN/'Metadata/MonsterRootCollisionRepair_20261012/MainUsageAudit02/Usage.json').read_text(encoding='utf-8'))
    source={(s['package'],w['attack_export_index']):w for s in plan['original_source_clips'] for w in s['windows']}
    raw=unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False,incorporate_root_motion_into_pose=True)
    locked=unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=True,incorporate_root_motion_into_pose=False)
    for pattern in plan['monster_patterns']:
        if pattern['family'] not in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite']:continue
        cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+pattern['family']+'.BP_Monster_'+pattern['family']+'_C')
        mesh=prop(unreal.get_default_object(cls),'Mesh');mapping=mesh.get_relative_transform()
        for node in pattern['nodes']:
            for w in node['windows']:
                package,index=w['source_window'].split('#');orig=source[(package,int(index))]
                step=next(s for s in node['source_steps'] if s['package']==package);clip=unreal.load_asset(step['clip'])
                bone=(orig['attack_properties_raw'].get('BoneName') or 'Root')
                for k in [orig['derived_geometry_keys'][0],orig['derived_geometry_keys'][len(orig['derived_geometry_keys'])//2],orig['derived_geometry_keys'][-1]]:
                    t=float(k['baked_time_seconds']);idx=orig['derived_geometry_keys'].index(k);anchor=rawvec(orig['baked_keys'][idx]['local_center_pos_raw'])
                    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(clip,t,raw)
                    stripped=unreal.AnimPoseExtensions.get_anim_pose_at_time(clip,t,locked)
                    a=pose.get_bone_pose(bone,unreal.AnimPoseSpaces.WORLD)
                    b=stripped.get_bone_pose(bone,unreal.AnimPoseSpaces.WORLD)
                    model_root=str(prop(clip,'skeleton').get_reference_pose().get_bone_names()[0])
                    root0=unreal.AnimationLibrary.extract_root_track_transform(clip,0)
                    rootat=unreal.AnimationLibrary.extract_root_track_transform(clip,t)
                    mapped_raw=mapping.transform_location(a.translation);mapped_locked=mapping.transform_location(b.translation)
                    unit=unreal.Transform();unit.rotation=mapping.rotation;unit.translation=unreal.Vector();unit.scale3d=unreal.Vector(1,1,1)
                    d['rows'].append({'family':pattern['family'],'definition':pattern['definition'],'node':node['node_id'],'clip':step['clip'],'bone':bone,'time':t,'source_anchor':v(anchor),'raw_bone_model':v(a.translation),'locked_bone_model':v(b.translation),'root0':v(root0.translation),'rootat':v(rootat.translation),'unit_rotated_raw':v(unit.transform_location(a.translation)),'unit_rotated_locked':v(unit.transform_location(b.translation)),'mesh_mapped_raw':v(mapped_raw),'mesh_mapped_locked':v(mapped_locked),'legacy_actor_anchor':v(anchor+mapping.translation),'raw_direct_error':(anchor-a.translation).length(),'raw_rotated_error':(anchor-unit.transform_location(a.translation)).length(),'locked_rotated_error':(anchor-unit.transform_location(b.translation)).length()})
    for row in usage['montages']:
        m=unreal.load_asset(row['asset'])
        d['montages'].append({'asset':row['asset'],'auto_blend_out':prop(m,'enable_auto_blend_out'),'seconds':m.get_play_length(),'sections':row['sections']})
    d['status']='passed'
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'Basis.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('CONTACT_BASIS',d['status'],len(d['rows']))
