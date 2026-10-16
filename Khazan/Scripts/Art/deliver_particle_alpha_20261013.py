"""Exact CAS-selected asset delivery; preserve current Main and all other files."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,shutil
MAIN=Path(__file__).resolve().parents[2];ROOT=MAIN/'Metadata/ParticleAlpha_20261013'
WORK=MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan'
read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read('RepairPlan.json');prepare=read('Preparation.json');verify=read('ShaderVerify01/Verification.json')
assert verify['status']=='passed' and len(verify['masters'])==86 and not verify['errors']
for name,key in [('GameCardsBefore02/Cards.json','actual_standalone_game'),('GameCardsAfter02/Cards.json','actual_standalone_game'),('SnowBefore02/Capture.json','actual_game_viewport'),('SnowAfter01/Capture.json','actual_game_viewport')]:
    d=read(name);assert d['status']=='passed' and d[key]
assert not (ROOT/'Delivery.json').exists(),'Never repeat installation'
budget='Content/_Art/Player/Environment/Rendering/HeinMachWeather/NET_HM_WeatherBudget.uasset'
before=dict(plan['before']);before[budget]=next(r['before_sha256'] for r in prepare['targets'] if r['path']==budget)
rows=[]
for rel,h in sorted(before.items()):
    current,source=MAIN/rel,WORK/rel
    assert source.resolve().is_relative_to(WORK.resolve())
    assert sha(current)==h,('Main changed; merge/review instead of overwriting',rel)
    rows.append({'relative':rel,'before_sha256':h,'after_sha256':sha(source),'bytes':source.stat().st_size})
assert len(rows)==30 and all(r['before_sha256']!=r['after_sha256'] for r in rows)
assert sha(MAIN/'Content/Maps/L_HeinMach_Environment.umap')==prepare['main_map_sha256']
for row in rows:
    backup=ROOT/'InstallBefore'/row['relative'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/row['relative'],backup)
    tmp=(MAIN/row['relative']).with_suffix('.alpha20261013.tmp')
    shutil.copy2(WORK/row['relative'],tmp);assert sha(tmp)==row['after_sha256']
    assert sha(MAIN/row['relative'])==row['before_sha256']
    os.replace(tmp,MAIN/row['relative']);assert sha(MAIN/row['relative'])==row['after_sha256']
report={'status':'installed','at':datetime.now().astimezone().isoformat(),'files':rows,
        'material_masters':13,'material_instances':16,'snow_effect_type':1,'source_config_map_particle_texture_binary_writes':0,'qa_assets_delivered':0}
(ROOT/'Delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':'installed','files':len(rows),'bytes':sum(r['bytes'] for r in rows)}))
