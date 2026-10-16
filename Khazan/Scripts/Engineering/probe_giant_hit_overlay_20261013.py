import unreal,json,os,traceback
from pathlib import Path
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT']); report={}
try:
 for family,art in [('ApesStoneHandElite','Shared/Elites/ApesStoneHandElite'),('Yetuga','HeinMach/Bosses/Yetuga')]:
  def read(path,fields):
   a=unreal.load_asset(path);data={'path':path,'class':a.get_class().get_name() if a else None}
   for f in fields:
    try:
     v=a.get_editor_property(f)
     data[f]=v.get_path_name() if isinstance(v,unreal.Object) else str(v)
    except Exception as e:data[f]=str(e)
   return data
  report[family]={
   'definition':read('/Game/Monsters/'+family+'/Data/DA_Character_'+family,['hit_reactions','monster_stamina']),
   'abp':read('/Game/Monsters/'+family+'/Animations/ABP_'+family,['target_skeleton','parent_class']),
   'clip':read('/Game/_Art/Enemies/'+art+'/Animations/Damage/Damage_Normal_D_F',['skeleton','additive_anim_type','ref_pose_type','ref_frame_index','ref_pose_seq','enable_root_motion','force_root_lock','rate_scale']),
   'montage':read('/Game/Monsters/'+family+'/Animations/Reaction/Montages/AM_'+family+'_Hit_Damage_Normal_D_F',['blend_in','blend_out','slot_anim_tracks'])}
except Exception:report['error']=traceback.format_exc()
(out/'SavedProbe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()