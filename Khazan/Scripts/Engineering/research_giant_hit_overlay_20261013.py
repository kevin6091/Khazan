import json,zipfile,hashlib,re
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'Metadata/GiantHitOverlay_20261013';report={}
for family,relative,cs,ap in [('Apes','Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip','CS_ApesStoneHand_E','AP_ApesStoneHand_E'),('Yetuga','Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip','CS_Yetuga','AP_Yetuga')]:
 data={'zip':relative,'sources':[],'condition_fields':[],'skill_metadata':[],'normal_hits':[]}
 def walk(v,path,rows):
  if isinstance(v,dict):
   for k,x in v.items():
    p=path+'.'+k
    if re.search(r'Fortitude|SuperArm|Groggy|DamageReaction|Exhaust|Stun|Stagger|Tough|WeakPoint|BreakPart|PartDamage|Parring',k,re.I):
     rows.append({'field':p,'value':x})
    if isinstance(x,(dict,list)):walk(x,p,rows)
  elif isinstance(v,list):
   for i,x in enumerate(v):walk(x,path+'['+str(i)+']',rows)
 with zipfile.ZipFile(root/relative) as z:
  for name in z.namelist():
   if not name.endswith('.json'):continue
   stem=Path(name).stem
   if stem in [cs,ap] or (('/00_PartGroggy/' in name or '/25_Groggy/' in name or '/ChargeTackle/' in name) and not stem.startswith(('AC_','CA_'))):
    raw=z.read(name);d=json.loads(raw);rows=[];walk(d,'exports',rows)
    data['sources'].append({'entry':name,'sha256':hashlib.sha256(raw).hexdigest()})
    for row in rows:row['entry']=name
    data['condition_fields']+=rows
   if stem.startswith(('SD_','SDT_','SK_','AS_','Skill_','SM_','SS_')) and ('Groggy' in stem or 'ChargeTackle' in stem):data['skill_metadata'].append(name)
   if ('DamageNormal_' in stem) and stem.startswith('CA_'):
    d=json.loads(z.read(name));data['normal_hits'].append({'entry':name,'sequences':[{'name':e.get('Name'),'properties':{k:v for k,v in e.get('Properties',{}).items() if k in ['AdditiveAnimType','RefPoseType','RefFrameIndex','RefPoseSeq','NumFrames','SequenceLength','RateScale','bEnableRootMotion']}} for e in d if e.get('Type')=='AnimSequence']})
 report[family]=data
 print(family,'condition entries',len(data['sources']),'field matches',len(data['condition_fields']),'skills',data['skill_metadata'])
 for row in data['condition_fields']:
  value=row['value']
  if not isinstance(value,(dict,list)) or 'StaminaExhaustionTerm' in row['field']:print(row['entry'],row['field'],value)
(out/'OriginalConditions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')