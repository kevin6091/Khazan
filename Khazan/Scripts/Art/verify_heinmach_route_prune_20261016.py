"""Compare fresh saved-map records against the exact removal manifest."""
from pathlib import Path
import collections, json, re, sys

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'Metadata/HeinMachRoutePrune_20261016'
run=TASK/sys.argv[1]
before_run=sys.argv[2] if len(sys.argv)>2 else 'Inventory01'
before=json.loads((TASK/before_run/'Inventory.json').read_text(encoding='utf-8'))
after=json.loads((run/'Inventory.json').read_text(encoding='utf-8'))
selection=json.loads((TASK/'Selection.json').read_text(encoding='utf-8'))
applied=json.loads((TASK/'Author01/Author.json').read_text(encoding='utf-8'))['applied']
deleted=set(applied['removed_actors']+applied['empty_instance_actors'])
instance_indices=collections.defaultdict(set)
for e in selection['deleted']:
    if e['kind']=='instance':instance_indices[(e['actor'],e['component'])].add(e['index'])
def stable(value):
    if isinstance(value,str):return re.sub(r'0x[0-9a-fA-F]+','<memory>',value)
    if isinstance(value,list):return [stable(v) for v in value]
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items()}
    return value

old={a['name']:stable(a) for a in before['actors']};new={a['name']:stable(a) for a in after['actors']}
errors=[]
missing=set(old)-deleted-set(new);extra=set(new)-(set(old)-deleted)
if missing:errors.append(dict(missing=sorted(missing)))
if extra:errors.append(dict(unexpected=sorted(extra)))
for name in sorted(set(old)&set(new)):
    b=old[name];a=new[name]
    for key in ['label','cls','folder','pose','hidden','tags','parent','postprocess','actor_collision_enabled']:
        if b.get(key)!=a.get(key):errors.append(dict(actor=name,field=key,before=b.get(key),after=a.get(key)))
    bc={c['name']:c for c in b['components']};ac={c['name']:c for c in a['components']}
    if set(bc)!=set(ac):errors.append(dict(actor=name,component_names_changed=True))
    for cname in sorted(set(bc)&set(ac)):
        bb=bc[cname];aa=ac[cname]
        for key in set(bb)|set(aa):
            if key in ['bounds','instances']:continue  # Renderer-computed bounds vary with initialization.
            if bb.get(key)!=aa.get(key):errors.append(dict(actor=name,component=cname,field=key,before=bb.get(key),after=aa.get(key)))
        if 'instances' in bb:
            expected=collections.Counter(t for i,t in enumerate(bb['instances']) if i not in instance_indices[(name,cname)])
            actual=collections.Counter(aa.get('instances',[]))
            if expected!=actual:errors.append(dict(actor=name,component=cname,instance_transform_mismatch=True,
                missing=sum((expected-actual).values()),extra=sum((actual-expected).values())))
counts=lambda rows:sum(len(c.get('instances',[])) for a in rows for c in a['components'])
report=dict(success=not errors,baseline=before_run,before_actors=len(old),after_actors=len(new),removed_actors=len(deleted),
    removed_empty_instance_actors=len(applied['empty_instance_actors']),before_instances=counts(before['actors']),
    after_instances=counts(after['actors']),removed_instances=applied['removed_instances'],
    protected_monsters=[a['name'] for a in after['actors'] if a['label'].startswith('BP_Monster')],
    player_starts=[a['name'] for a in after['actors'] if a['cls'].endswith('.PlayerStart')],
    errors=errors)
(run/'InventoryVerification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['protected_monsters','errors']},ensure_ascii=False))
if errors:print(json.dumps(errors[:8],ensure_ascii=False,indent=2));sys.exit(1)
