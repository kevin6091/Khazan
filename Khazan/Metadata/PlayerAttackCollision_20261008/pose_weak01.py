import unreal,json
from pathlib import Path
da=unreal.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
node=da.get_editor_property('nodes')[0]
montage=node.get_editor_property('montage')
track=montage.get_editor_property('slot_anim_tracks')[0]
print('TRACK',track.export_text()[:1200])
seq=track.get_editor_property('anim_track').get_editor_property('anim_segments')[0].get_editor_property('anim_reference')
result={'sequence':seq.get_path_name(),'samples':[]}
for time in (.33789843,.30753647142681184):
  for extract in (False,True):
    opts=unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW,extract_root_motion=extract,incorporate_root_motion_into_pose=False,should_retarget=False)
    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,time,opts)
    bones={}
    for bone in ('C_P_Kazan','Root','root','Weapon_L','Weapon_R'):
      t=unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD)
      bones[bone]=t.export_text()
    result['samples'].append({'time':time,'extract':extract,'bones':bones})
Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerAttackCollision_20261008/PoseWeak01.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result)
