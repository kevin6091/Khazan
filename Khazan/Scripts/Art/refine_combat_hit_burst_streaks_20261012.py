"""Thin original spark cards with controlled saturation; no new flash material."""
from pathlib import Path
import os,json,hashlib,shutil,re
import unreal as u
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);H={}
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')
s=(MAIN/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
s=s.replace("assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')",'assert ROOT == Path('+repr(str(ROOT))+')')
s=s.replace("'bEnabled':'FBoolProperty'", "'bEnabled':'FBoolProperty','LODValidity':'FByteProperty','bIsDirty':'FBoolProperty'")
exec(compile(s,'serializer_definitions_only','exec'),H);H.update(OUT=OUT,DEST='/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst')
report={'status':'running','assets':[],'TEMP':{'streak_width_cm':[2,4],'streak_length_cm':[16,30],'colours':[(.04,.28,3),(1.4,.025,2.4),(2,.012,.035)],'alpha_life_curve':[(0,.95),(.55,.7),(1,0)]}}
for path in [H['DEST'],H['BLOOD']]:
 a=u.load_asset(path);f=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset');shutil.copy2(f,OUT/(a.get_name()+'_Before.uasset'))
 t=H['export'](a,a.get_name()+'_Before.t3d');blocks={m.group(1):m.group(0) for m in re.finditer(r'^   Begin Object Name="([^"]+)" .*?^   End Object',t,re.M|re.S)}
 for index,name in enumerate(('KZHitFireBlue','KZHitFirePurple','KZHitFireRed')):
  emitter_block=blocks[name];ln=re.search(r'LODLevels\(0\)="[^\']+\'([^\']+)\'"',emitter_block).group(1).rsplit(':',1)[-1].rsplit('.',1)[-1]
  lod=u.load_object(None,a.get_path_name()+':'+name+'.'+ln);modules=[];size_count=0
  for ref in re.findall(r'Modules\(\d+\)="[^\']+\'([^\']+)\'"',emitter_block):
   m=u.load_object(None,ref if ref.startswith('/') else a.get_path_name()+':'+ref.rsplit(':',1)[-1]);assert m
   if m.get_class().get_name() in ('ParticleModuleColor','ParticleModuleColorScaleOverLife','ParticleModuleColorOverLife'):continue
   if m.get_class().get_name()=='ParticleModuleSize':
    # A fresh local size module avoids the old raw lookup table. Changing the
    # loaded distribution's limits alone does not rebuild that serialized table.
    fresh=H['new']('ParticleModuleSize',a,name+'_StreakSize2')
    H['dist'](fresh,'StartSize','DistributionVectorUniform',{'Min':'(X=2,Y=16,Z=2)','Max':'(X=4,Y=30,Z=4)'})
    H['set_owned'](fresh,'LODValidity','1');modules.append(fresh);size_count+=1
    continue
   modules.append(m)
  assert size_count==1
  # All three source RequiredModules already use PSA_Velocity; retain that enum.
  colour=u.load_object(None,a.get_path_name()+':'+name+'_StreakColour')
  existed=bool(colour)
  if not existed:colour=H['new']('ParticleModuleColorOverLife',a,name+'_StreakColour')
  rgb=report['TEMP']['colours'][index]
  if existed:
   H['set_owned'](u.load_object(None,colour.get_path_name()+'.D_ColorOverLife'),'Constant','(X=%s,Y=%s,Z=%s)'%tuple(rgb))
   H['set_owned'](u.load_object(None,colour.get_path_name()+'.D_AlphaOverLife'),'ConstantCurve',H['points'](report['TEMP']['alpha_life_curve']))
  else:
   H['dist'](colour,'ColorOverLife','DistributionVectorConstant',{'Constant':'(X=%s,Y=%s,Z=%s)'%tuple(rgb)})
   H['dist'](colour,'AlphaOverLife','DistributionFloatConstantCurve',{'ConstantCurve':H['points'](report['TEMP']['alpha_life_curve'])})
  H['set_owned'](colour,'LODValidity','1')
  modules.append(colour);H['set_owned'](lod,'Modules','('+','.join(H['token'](m) for m in modules)+')')
 H['rebuild'](a);assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
 H['export'](a,a.get_name()+'_After.t3d')
 report['assets'].append({'path':path,'file':str(f.relative_to(ROOT)),'after':hashlib.sha256(f.read_bytes()).hexdigest()})
 (OUT/'Checkpoint.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
report['status']='passed';(OUT/'Applied.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('STREAK_BURST_REFINED')
