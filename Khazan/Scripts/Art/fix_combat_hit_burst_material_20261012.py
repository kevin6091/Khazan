"""Use the already-rendered, feathered original parry spark fallback material."""
from pathlib import Path
import os,json,hashlib,shutil
import unreal as u
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);H={}
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')
s=(MAIN/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
s=s.replace("assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')",'assert ROOT == Path('+repr(str(ROOT))+')')
s=s.replace("'bEnabled':'FBoolProperty'", "'bEnabled':'FBoolProperty','Material':'FObjectPropertyBase'")
exec(compile(s,'serializer_definitions_only','exec'),H);H.update(OUT=OUT,DEST='/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst')
material=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/DefaultParticle');assert material
report={'status':'running','material':material.get_path_name(),'assets':[],'reason':'Runtime120 particles/size9-16cm/alpha.22-.87/velocity>1000 verified; fluid material not visibly rendering. Reuse existing original Parry DefaultParticle feathered spark adapter, no new flash material.'}
for path in [H['DEST'],H['BLOOD']]:
 a=u.load_asset(path);f=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset');shutil.copy2(f,OUT/(a.get_name()+'_Before.uasset'))
 for name in ('KZHitFireBlue','KZHitFirePurple','KZHitFireRed'):
  required=u.load_object(None,a.get_path_name()+':'+name+'_RequiredModule');assert required
  H['set_owned'](required,'Material',H['token'](material))
 H['rebuild'](a);assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
 report['assets'].append({'path':path,'file':str(f.relative_to(ROOT)),'after':hashlib.sha256(f.read_bytes()).hexdigest()})
report['status']='passed';(OUT/'Applied.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('EXISTING_SPARK_MATERIAL_APPLIED')
