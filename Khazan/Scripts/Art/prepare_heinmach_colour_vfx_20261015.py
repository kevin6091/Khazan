"""Current Main hardlink snapshot; explicit author targets are independently copied."""
from pathlib import Path
import hashlib,json,os,shutil

main=Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=main/'Metadata/HeinMachColourVFX_20261015'
assert not work.exists(),work
usage=json.loads((out/'BaselineAudit02/Usage.json').read_text(encoding='utf-8'))
assert usage['status']=='passed'
targets={'Content/Maps/L_HeinMach_Environment.umap','Content/Maps/DevMap.umap',
         'Content/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround.uasset'}
for row in usage['definitions']:
    targets.add('Content/'+row['asset'].removeprefix('/Game/')+'.uasset')
for row in usage['roots']:
    if row['material'].startswith('/Game/'):
        targets.add('Content/'+row['material'].removeprefix('/Game/')+'.uasset')
for row in usage['monster_defaults']:
    package=row['class'].split('.')[0]
    targets.add('Content/'+package.removeprefix('/Game/')+'.uasset')
work.mkdir(parents=True)
shutil.copy2(main/'Khazan.uproject',work/'Khazan.uproject')
for folder in ('Source','Config'):
    shutil.copytree(main/folder,work/folder,ignore=shutil.ignore_patterns('__pycache__'))
for folder in ('Content','Plugins'):
    for base,dirs,files in os.walk(main/folder):
        dirs[:]=[d for d in dirs if d not in ('Intermediate','Saved','DerivedDataCache')]
        dest=work/Path(base).relative_to(main);dest.mkdir(parents=True,exist_ok=True)
        for name in files:os.link(Path(base)/name,dest/name)
manifest=json.loads((main/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
binary=manifest['Modules']['Khazan'];dest=work/'Binaries/Win64';dest.mkdir(parents=True)
for name in ('UnrealEditor.modules',binary):shutil.copy2(main/'Binaries/Win64'/name,dest/name)
receipt={'main':str(main),'work':str(work),'targets':{},'binary':binary}
for rel in sorted(targets):
    source=main/rel;dest=work/rel;assert source.exists(),rel
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    backup=out/'Before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    dest.unlink();shutil.copy2(source,dest);assert not os.path.samefile(source,dest)
    receipt['targets'][rel]=digest
(out/'Preparation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('HEIN_COLOUR_PREPARED',len(targets),flush=True)
