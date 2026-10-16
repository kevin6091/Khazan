from pathlib import Path
import json,zipfile,hashlib
root=Path(__file__).resolve().parents[2];out=root/'Metadata/GiantHitOverlay_20261013';report=json.loads((out/'OriginalConditions.json').read_text(encoding='utf-8'))
for family,ab in [('Apes','AB_ApesStoneHand_E'),('Yetuga','AB_Yetuga')]:
 with zipfile.ZipFile(root/report[family]['zip']) as z:
  entry=next(n for n in z.namelist() if Path(n).stem==ab and n.endswith('.json'));raw=z.read(entry)
  rows=[dict(entry=entry,export_index=i,export_name=e['Name'],field='Properties.'+k,value=v) for i,e in enumerate(json.loads(raw)) for k,v in e.get('Properties',{}).items() if 'AdditiveBlend' in k]
  report[family]['original_additive_graph']=dict(entry=entry,sha256=hashlib.sha256(raw).hexdigest(),nodes=rows)
  cs=next(s['entry'] for s in report[family]['sources'] if '/CS_' in s['entry']);report[family]['part_destruction']=json.loads(z.read(cs))[0]['Properties']['PartDestruction']
p=root/'Metadata/EnemyBehaviorResearch_20261008/ApesOriginalResolvedBranches.json';d=json.loads(p.read_text(encoding='utf-8'))
report['specific_ap es_parry'.replace(' ','')]=[r for r in d['skill_event_branches'] if 'ParryingReaction' in str(r['skill_event_tag'])]
p=root/'Metadata/EnemyBehaviorResearch_20261008/YetugaOriginalDefenseRecovery.json';d=json.loads(p.read_text(encoding='utf-8'))
exports=[r for r in d['exports'] if Path(r['package']).name=='SB_Yetuga_ChargeTackle'];indices={r['export_index']:r for r in exports}
def resolve(ref):
 if isinstance(ref,dict) and ref.get('ObjectPath'):return indices.get(int(ref['ObjectPath'].rsplit('.',1)[-1]))
 return None
cdo=next(r for r in exports if r['export_name'].startswith('Default__'))
steps=[];branches=[]
for s in cdo['properties']['SubStateInfos']:
 v=s['Value'];steps.append(dict(step=s['Key'],next_step=v.get('NextSubStateStep'),animation=v.get('SkillAnimation')))
 for event in v.get('SkillEventMap',[]):
  value=event['Value'];refs=[]
  def findrefs(v):
   if isinstance(v,dict):
    if 'ObjectPath' in v:refs.append(v)
    for x in v.values():findrefs(x)
   elif isinstance(v,list):
    for x in v:findrefs(x)
  findrefs(value);resolved=[resolve(r) for r in refs];resolved=[r for r in resolved if r]
  if any('CollisionWall' in r['export_type'] or 'SkillReaction' in r['export_type'] for r in resolved):
   branches.append(dict(step=s['Key'],event_key=event['Key'],raw_event=value,resolved=resolved));print(s['Key'],[(r['export_index'],r['export_type'],r['properties']) for r in resolved])
report['specific_yetuga_charge_wall']=dict(source_file=p.relative_to(root).as_posix(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),steps=steps,branches=branches)
(out/'OriginalConditions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('Recorded original additive graphs, part-destruction fields and special-reaction branches')