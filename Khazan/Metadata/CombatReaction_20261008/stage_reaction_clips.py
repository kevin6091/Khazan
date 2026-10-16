import hashlib,json,pathlib,shutil
main=pathlib.Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_MonsterWork_20261006/Khazan'
out=main/'Metadata/CombatReaction_20261008'
d=json.loads((out/'AnimationClassification.json').read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
assets=[r['CurrentAsset'] for r in d['enemy_clips']]+[r['current_path'] for r in d['player']['reaction_source_clips']]
files=['Content/'+a.split('.')[0].removeprefix('/Game/')+'.uasset' for a in assets]
vfx=json.loads((main/'Saved/ImportReports/PlayerAttackVFX_20261008/MainDelivery/Delivered.json').read_text(encoding='utf8'))
files += [r['file'] for r in vfx['files'] if r['file'].startswith('Content/')]
rows=[]
for rel in sorted(set(files)):
 s,t=main/rel,work/rel
 before=sha(t); expected=sha(s)
 assert expected,rel
 if expected!=before:
  if t.is_file():
   b=out/'DependencyWorkBefore'/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(t,b)
  t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,t)
 assert sha(t)==expected
 rows.append(dict(relative=rel,main=expected,work_before=before,copied=expected!=before))
(out/'DependencyStage.json').write_text(json.dumps(dict(rows=rows),indent=2),encoding='utf8')
print('Dependencies checked',len(rows),'copied',sum(r['copied'] for r in rows))
