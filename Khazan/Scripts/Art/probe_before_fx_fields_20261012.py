"""Load one immutable before package under an owned temporary namespace."""
from pathlib import Path
import shutil,os,json
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);BASE=ROOT/'Metadata/CombatImpactUpgrade_20261012'
rel='Content/_Art/Player/Animation/InGame/DAS/DodgeAttack/AM_DAS_Player_DodgeAttack.uasset'
target=ROOT/'Content/__KZImpactBaseline/AM_DAS_Player_DodgeAttack.uasset';target.parent.mkdir(exist_ok=True);assert not target.exists();shutil.copyfile(BASE/'WorkBefore'/rel,target)
original=u.load_object(None,'/Game/__KZImpactBaseline/AM_DAS_Player_DodgeAttack.AM_DAS_Player_DodgeAttack');assert original
current=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/DodgeAttack/AM_DAS_Player_DodgeAttack')
fields=json.loads((BASE/'RestoreOriginalFX01/Restored.json').read_text(encoding='utf-8'))['restored_fields']
def effect_map(a):
 result={}
 for ev in u.AnimationLibrary.get_animation_notify_events(a):
  p=ev.get_editor_property('Notify')
  if isinstance(p,u.KZAnimNotify_CombatEffect):
   for e in [p]+list(p.get_editor_property('BatchedEffects')):result[(str(e.get_editor_property('EventId')),bool(e.get_editor_property('bEndEvent')))]=e
 return result
def value(v):
 if isinstance(v,u.Object):return v.get_path_name()
 if isinstance(v,u.Vector):return [v.x,v.y,v.z]
 if isinstance(v,u.Rotator):return [v.pitch,v.yaw,v.roll]
 return str(v)
old,now=effect_map(original),effect_map(current);diff=[]
for key,e in old.items():
 if key not in now:continue
 for f in fields:
  a,b=value(e.get_editor_property(f)),value(now[key].get_editor_property(f))
  if a!=b:diff.append({'id':key,'field':f,'before':a,'current':b})
(OUT/'BeforeFieldProbe.json').write_text(json.dumps({'status':'passed','differences':diff,'original_objects':len(old),'temporary_file':str(target)},indent=2),encoding='utf-8');print('EXACT_BEFORE_FIELDS',len(diff))
