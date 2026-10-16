"""Exact recovery-only CAS delivery, gated by native functional and visual review."""
from pathlib import Path
import hashlib, json, os, shutil, sys
from datetime import datetime
MAIN=Path(__file__).resolve().parents[2]
OUT=MAIN/'Metadata/HealVFX_20261013'
WORK=MAIN.parent.parent/'Khazan_HealVFXWork_20261013/Khazan'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
baseline=read(OUT/'Baseline.json')
source=['Source/Khazan/Ability/PlayerAbility/KZHealAbility.cpp','Source/Khazan/Tests/KZHealAbilityPIETest.cpp']
assets=[p.relative_to(WORK).as_posix() for p in (WORK/'Content/HealVFX').rglob('*.uasset')]
assets.append('Content/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal.uasset')
assert len(assets)==13 and len(set(assets))==13
rows=[]
for rel in source+sorted(assets):
    before=(baseline['source'] if rel.startswith('Source/') else baseline['assets']).get(rel)
    assert sha(MAIN/rel)==before,'Main CAS conflict: '+rel
    rows.append(dict(relative=rel,before=before,prepared=sha(WORK/rel)))
protected={r:sha(MAIN/r) for r in baseline['source'] if r not in source}
protected.update({r:sha(MAIN/r) for r in baseline['config']})
protected.update({r:sha(MAIN/r) for r in baseline['assets'] if r not in assets})
report=dict(status='prepared',rows=rows,protected=protected,date=datetime.now().astimezone().isoformat())
(OUT/'DeliveryPlan.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if sys.argv[1]=='preflight':print('CAS ready',len(rows));sys.exit(0)
assert sys.argv[1]=='apply'
quality=read(OUT/'VisualReview.json');assert quality['approved'] and quality['candidate_sha256']=={r['relative']:r['prepared'] for r in rows}
qa=read(OUT/quality['native_validation']/'Driver.json');assert qa['status']=='passed' and all(t['passed'] for t in qa['tests'])
backup=OUT/'MainBeforeDelivery';backup.mkdir(exist_ok=False)
for row in rows:
    p=MAIN/row['relative']
    if p.exists():
        target=backup/row['relative'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for row in rows:
    rel=row['relative'];p=MAIN/rel;assert sha(p)==row['before'] and sha(WORK/rel)==row['prepared']
    p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.HealVFX.tmp');assert not temp.exists()
    shutil.copyfile(WORK/rel,temp);assert sha(temp)==row['prepared'];os.replace(temp,p)
    if rel.startswith('Source/'):os.utime(p,None)
    assert sha(p)==row['prepared']
assert all(sha(MAIN/r)==v for r,v in protected.items())
report.update(status='applied',protected_changed=0,private_dll_config_transferred=0)
(OUT/'Delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Main recovery delivery',len(rows),'files',flush=True)
