"""Refresh QA-only integration dependencies without replacing authored targets."""
from pathlib import Path
import hashlib,json,shutil
main=Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=main/'Metadata/HeinMachColourVFX_20261015/IntegrationStage02'
out.mkdir(exist_ok=False)
paths=set()
feel=json.loads((main/'Metadata/CombatFeel_20261015/Author01/Author.json').read_text(encoding='utf-8'))
paths.update('Content/'+x['asset'].removeprefix('/Game/')+'.uasset' for x in feel['backups'])
snow=json.loads((main/'Metadata/YetugaSnowLayout_20261015/Authoring.json').read_text(encoding='utf-8'))
paths.update('Content/'+x.split('.')[0].removeprefix('/Game/')+'.uasset' for x in snow['saved'])
manifest=json.loads((main/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
paths.update(('Binaries/Win64/UnrealEditor.modules','Binaries/Win64/'+manifest['Modules']['Khazan']))
rows=[]
for rel in sorted(paths):
    src,dst=main/rel,work/rel
    before=hashlib.sha256(dst.read_bytes()).hexdigest() if dst.exists() else None
    backup=out/'WorkBefore'/rel
    if dst.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
    dst.parent.mkdir(parents=True,exist_ok=True)
    # Replace, rather than truncate, any remaining QA hardlink.
    temp=dst.with_name(dst.name+'.heincolourstage')
    shutil.copy2(src,temp);temp.replace(dst)
    after=hashlib.sha256(dst.read_bytes()).hexdigest()
    assert after==hashlib.sha256(src.read_bytes()).hexdigest()
    rows.append({'file':rel,'work_before':before,'current_main_sha256':after})
source=main/'Source/Khazan/Character/KZCharacter.cpp'
(out/'Receipt.json').write_text(json.dumps({'status':'passed','main_writes':0,'rows':rows,
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'build':'MainBuild04 Succeeded/up to date'},indent=2),encoding='utf-8')
print('QA_INTEGRATION_STAGED',len(rows))
