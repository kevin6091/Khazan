"""Replace the enabled GPU-origin halo slot with an explicit finite CPU sprite."""
from pathlib import Path
import json,os,re,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';DEST=BASE+'/PP_Player_Parry_Reference'
H={};s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
s=s.replace("'bEnabled':'FBoolProperty'","'bEnabled':'FBoolProperty','LODLevels':'FArrayProperty','Material':'FObjectPropertyBase'")
s=s.replace("'ColorOverLife','AlphaOverLife'","'StartColor','StartAlpha','ColorOverLife','AlphaOverLife'")
exec(compile(s,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);assert ps
shutil.copy2(ROOT/('Content/'+DEST.removeprefix('/Game/')+'.uasset'),OUT/'ParticleBefore.uasset')
text=H['export'](ps,'Before.t3d')
def new(cls,outer,name):return H['new'](cls,outer,name)
def setp(a,k,v):H['set_owned'](a,k,v)
def dist(a,k,cls,v):return H['dist'](a,k,cls,v)
def token(a):return H['token'](a)
e=new('ParticleSpriteEmitter',ps,'KZPhotoHaloCPU')
lod=new('ParticleLODLevel',e,'LOD0')
req=new('ParticleModuleRequired',ps,'KZPhotoHaloRequired')
setp(req,'Material',token(u.load_asset(BASE+'/M_Parry_Halo')))
for k,v in [('EmitterDuration','.1'),('EmitterLoops','1'),('EmitterDelay','0'),('bUseLocalSpace','False')]:setp(req,k,v)
spawn=new('ParticleModuleSpawn',ps,'KZPhotoHaloSpawn');setp(spawn,'BurstList','((Count=1,CountLow=-1,Time=0))');dist(spawn,'Rate','DistributionFloatConstant',{'Constant':'0'})
life=new('ParticleModuleLifetime',ps,'KZPhotoHaloLife');dist(life,'Lifetime','DistributionFloatConstant',{'Constant':'.2'})
size=new('ParticleModuleSize',ps,'KZPhotoHaloSize');dist(size,'StartSize','DistributionVectorConstant',{'Constant':'(X=125,Y=125,Z=125)'})
growth=u.load_object(None,ps.get_path_name()+':ParticleModuleSizeMultiplyLife_22');assert growth
colour=new('ParticleModuleColor',ps,'KZPhotoHaloColour');dist(colour,'StartColor','DistributionVectorConstant',{'Constant':'(X=.421875,Y=.323095,Z=.193952)'});dist(colour,'StartAlpha','DistributionFloatConstant',{'Constant':'.7'})
fade=new('ParticleModuleColorOverLife',ps,'KZPhotoHaloFade');dist(fade,'ColorOverLife','DistributionVectorConstant',{'Constant':'(X=.421875,Y=.323095,Z=.193952)'});dist(fade,'AlphaOverLife','DistributionFloatConstantCurve',{'ConstantCurve':H['points']([(0,.7),(.354839,.7),(1,0)])})
setp(lod,'RequiredModule',token(req));setp(lod,'SpawnModule',token(spawn));setp(lod,'TypeDataModule','None');setp(lod,'Modules','('+','.join(token(x) for x in [life,size,growth,colour,fade])+')');setp(lod,'bEnabled','True')
setp(e,'LODLevels','('+token(lod)+')');setp(e,'EmitterName','ParryPhotoHalo');setp(e,'DetailModeBitmask','15')
refs=re.findall(r'^   Emitters\(\d+\)="[^\x27]+\x27([^\x27]+)\x27"',text,re.M);assert len(refs)==12
emitters=[u.load_object(None,r if r.startswith('/') else ps.get_path_name()+':'+r.split(':')[-1]) for r in refs];assert all(emitters)
slot=next(i for i,x in enumerate(emitters) if x.get_name()=='ParticleSpriteEmitter_13');emitters[slot]=e
setp(ps,'Emitters','('+','.join(token(x) for x in emitters)+')');H['rebuild'](ps);assert u.EditorAssetLibrary.save_loaded_asset(ps,only_if_is_dirty=False)
(OUT/'CPUHalo.json').write_text(json.dumps({'status':'saved','rhi_pending':True,'replaced_slot':slot,'original_subobjects_preserved':True,'emitters':12,'source_life_s':.2,'source_colour':[.421875,.323095,.193952],'source_alpha':.7,'cpu_size_temporary_cm':[125,125,125],'growth_curve':'Existing complete source module ParticleModuleSizeMultiplyLife_22 reused','alpha_curve':'Assistant finite fade based on source .2s life; native shader stripped'},indent=2),encoding='utf-8')
