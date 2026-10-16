"""Refresh only the owned checkout from current Main; retain its author/build tooling."""
from pathlib import Path
import hashlib,json,shutil
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
namespace={}
exec(compile((MAIN/'Scripts/Engineering/monster_physics_delivery_20261013.py').read_text(encoding='utf-8'),str(MAIN/'Scripts/Engineering/monster_physics_delivery_20261013.py'),'exec'),{'__file__':str(MAIN/'Scripts/Engineering/monster_physics_delivery_20261013.py'),'__name__':'delivery_import'},namespace)
old,new=namespace['OLD'],namespace['NEW']
rows=[]
for source in sorted((MAIN/'Source').rglob('*')):
    if not source.is_file() or source.name=='Khazan.Build.cs':continue
    rel=source.relative_to(MAIN);target=WORK/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if rel.as_posix()=='Source/Khazan/Character/KZMonster.cpp':
        text=source.read_text(encoding='utf-8-sig');assert text.count(old)==1
        target.write_text(text.replace(old,new),encoding='utf-8')
    elif not target.exists() or sha(source)!=sha(target):shutil.copy2(source,target)
    rows.append(dict(path=rel.as_posix(),main=sha(source),work=sha(target)))
for name in ('MonsterSecondaryPhysicsEditor.cpp','KZMonsterSecondaryPhysicsPIETest.cpp'):
    shutil.copy2(MAIN/'Scripts/Engineering'/name,WORK/'Source/Khazan/Tests'/name)
(OUT/'LatestSourceIntake.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('LATEST MAIN SOURCE INTAKE',len(rows),'with only modular physics runtime patch')
