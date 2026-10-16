from pathlib import Path
import json, shutil, hashlib
main=Path(__file__).resolve().parents[2]; work=main.parent.parent/'Khazan_MonsterWork_20261006/Khazan'
target=main/'Metadata/CombatReaction_20261008/ReactionAuthoringPlan.json'
plan=json.loads(target.read_text(encoding='utf8'))
changed=[]
for body in plan['bodies']:
    if body['body']!='HeavySwordsman': continue
    for montage in body['montages']:
        if montage['pool']!='Knockbacks': continue
        assert [s['name'] for s in montage['sections']]==['Down','Loop','Getup']
        assert montage['hit_land_section']==''
        montage['hit_land_section']='Loop'
        montage['provenance']+=' Project landing boundary is Loop start after the finite Down clip; the temporary prone hold is excluded from force duration, not an original native Blow-chain assertion.'
        changed.append(montage['destination'])
assert len(changed)==2
target.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
shutil.copy2(target,work/'Metadata/CombatReaction_20261008/ReactionAuthoringPlan.json')
print(json.dumps(dict(changed=changed,sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
