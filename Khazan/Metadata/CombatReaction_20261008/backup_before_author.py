import pathlib,json,hashlib,shutil
main=pathlib.Path(__file__).resolve().parents[2];out=main/'Metadata/CombatReaction_20261008'
work=main.parent.parent/'Khazan_MonsterWork_20261006/Khazan'
plan=json.loads((out/'ReactionAuthoringPlan.json').read_text(encoding='utf8'))
collision=json.loads((out/'MonsterAttackCollisionPlan.json').read_text(encoding='utf8'))
paths={b['definition'] for b in plan['bodies']}|{p['definition'] for p in collision['monster_patterns']}|{collision['player_definition']}
rows=[]
for asset in sorted(paths):
 rel='Content/'+asset.removeprefix('/Game/').split('.')[0]+'.uasset'
 s=work/rel;assert s.is_file(),rel
 target=out/'BeforeAuthor'/rel;assert not target.exists(),rel
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,target)
 rows.append({'relative':rel,'sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'main_sha256':hashlib.sha256((main/rel).read_bytes()).hexdigest()})
(out/'BeforeAuthor.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('Backed up',len(rows),'existing packages')
