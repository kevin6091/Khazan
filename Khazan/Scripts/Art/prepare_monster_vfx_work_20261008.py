"""Create a private six-family VFX authoring tree; other content stays read-only."""
import csv,datetime,hashlib,json,shutil,subprocess
from pathlib import Path
MAIN=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
OUT=MAIN/'Saved/ImportReports/MonsterVFX_20261008'
FAMILIES={'Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga'}
assert MAIN==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert not WORK.exists(),'Existing work is never replaced'
OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'WorkBaseline.json').exists()
PRIVATE={f'Monsters/{name}' for name in FAMILIES}
for file in (MAIN/'Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv',
             MAIN/'Metadata/EnemyBehaviorResearch_20261008/CurrentApesYetugaLibrary.csv'):
    for row in csv.DictReader(file.open(encoding='utf-8-sig')):
        if row['Family'] in FAMILIES:
            PRIVATE.add(row['CurrentAsset'].removeprefix('/Game/').split('/Animations/')[0])
PRIVATE.update(('_Art/Effects/Combat','_Art/Effects/DualAxeSword','_Art/Effects/Movement','_Art/Effects/Shared',
                '_Art/Enemies/HeinMach/Shared','_Art/Enemies/Shared'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def junction(src,dest):
    assert src.resolve().is_relative_to(MAIN) and dest.absolute().is_relative_to(WORK)
    assert not dest.exists()
    srcq=str(src.resolve()).replace("'","''");destq=str(dest.absolute()).replace("'","''")
    subprocess.run(['powershell','-NoProfile','-Command',
       "New-Item -ItemType Junction -Path '"+destq+"' -Target '"+srcq+"' | Out-Null"],check=True)
def tree(src,dest,relative=''):
    dest.mkdir()
    for entry in src.iterdir():
        rel=(relative+'/'+entry.name).strip('/');candidate=dest/entry.name
        if not entry.is_dir():shutil.copy2(entry,candidate)
        elif rel in PRIVATE:shutil.copytree(entry,candidate)
        elif any(p.startswith(rel+'/') for p in PRIVATE):tree(entry,candidate,rel)
        else:junction(entry,candidate)
WORK.mkdir(parents=True)
for folder in ('Source','Config'):
    shutil.copytree(MAIN/folder,WORK/folder)
shutil.copytree(MAIN/'Plugins',WORK/'Plugins',ignore=shutil.ignore_patterns('Intermediate','Saved','DerivedDataCache'))
shutil.copy2(MAIN/'Khazan.uproject',WORK/'Khazan.uproject')
tree(MAIN/'Content',WORK/'Content')
modules=json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
binary=modules['Modules']['Khazan']
(WORK/'Binaries/Win64').mkdir(parents=True)
for name in (binary,Path(binary).with_suffix('.pdb').name,'UnrealEditor.modules'):
    if (MAIN/'Binaries/Win64'/name).is_file():shutil.copy2(MAIN/'Binaries/Win64'/name,WORK/'Binaries/Win64'/name)
snapshot={}
for folder in ('Source','Config'):
    for p in (MAIN/folder).rglob('*'):
        if p.is_file():snapshot[p.relative_to(MAIN).as_posix()]=sha(p)
snapshot['Khazan.uproject']=sha(MAIN/'Khazan.uproject')
for rel in sorted(PRIVATE):
    folder=MAIN/'Content'/rel
    if folder.is_dir():
        for p in folder.rglob('*'):
            if p.is_file():snapshot[p.relative_to(MAIN).as_posix()]=sha(p)
for folder in ('Content/_Art/Player','Content/Maps','Content/Data','Content/Bluprints/AbilitySystem',
               'Content/_Art/Enemies/HeinMach/Humanoids/Archer'):
    if (MAIN/folder).is_dir():
        for p in (MAIN/folder).rglob('*.uasset'):
            snapshot[p.relative_to(MAIN).as_posix()]=sha(p)
        for p in (MAIN/folder).rglob('*.umap'):
            snapshot[p.relative_to(MAIN).as_posix()]=sha(p)
stock={p.relative_to(MAIN).as_posix():sha(p) for p in (MAIN/'Binaries/Win64').glob('UnrealEditor-Khazan*') if p.is_file()}
stock['Binaries/Win64/UnrealEditor.modules']=sha(MAIN/'Binaries/Win64/UnrealEditor.modules')
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main':str(MAIN),'work':str(WORK),
 'private_content':sorted(PRIVATE),'main_sha256':snapshot,'main_native_sha256':stock,
 'copied_module':binary,'shared_content':'All other junctions are read-only; no shared asset save, rename or delete',
 'main_source_content_changed':False,'main_editor_started_or_controlled':False}
(OUT/'WorkBaseline.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'work':str(WORK),'baseline_files':len(snapshot),'private_folders':len(PRIVATE)},indent=2))
