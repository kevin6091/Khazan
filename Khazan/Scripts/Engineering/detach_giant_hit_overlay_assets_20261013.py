from pathlib import Path
import os,json,hashlib,shutil
m=Path(__file__).resolve().parents[2];w=m.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan';o=m/'Metadata/GiantHitOverlay_20261013'
assets=[]
for f,art,sk in [('ApesStoneHandElite','Shared/Elites/ApesStoneHandElite','SKEL_EN_ApesStoneHandElite'),('Yetuga','HeinMach/Bosses/Yetuga','SKEL_EN_Yetuga')]:
 assets += ['Content/Monsters/'+f+'/Data/DA_Character_'+f+'.uasset','Content/Monsters/'+f+'/Animations/ABP_'+f+'.uasset','Content/_Art/Enemies/'+art+'/Skeletons/'+sk+'.uasset']
receipt={'targets':{},'original_preservation':{}}
for a in assets:
 src=m/a;dst=w/a;before=o/'Before'/a;before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,before)
 tmp=dst.with_name(dst.name+'.GiantHitDetach');assert not tmp.exists();shutil.copy2(src,tmp);os.replace(tmp,dst)
 receipt['targets'][a]=hashlib.sha256(src.read_bytes()).hexdigest();assert dst.stat().st_nlink==1
for f,art in [('ApesStoneHandElite','Shared/Elites/ApesStoneHandElite'),('Yetuga','HeinMach/Bosses/Yetuga')]:
 for d in 'LRDU':
  for a in ['Content/_Art/Enemies/'+art+'/Animations/Damage/Damage_Normal_'+d+'_F.uasset','Content/Monsters/'+f+'/Animations/Reaction/Montages/AM_'+f+'_Hit_Damage_Normal_'+d+'_F.uasset']:
   receipt['original_preservation'][a]=hashlib.sha256((m/a).read_bytes()).hexdigest()
(o/'AssetBaseline.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('Detached',len(assets),'targets; protected',len(receipt['original_preservation']),'originals')