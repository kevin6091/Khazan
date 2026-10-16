"""Own target Content directories and Cog binaries; unrelated Content is read-only."""
from pathlib import Path
import csv, hashlib, json, shutil, subprocess
MAIN=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')
OUT=MAIN/'Metadata/CombatImpactUpgrade_20261012'
assert not WORK.exists()
WORK.mkdir(parents=True)
for directory in ('Source','Config','Binaries'):
    shutil.copytree(MAIN/directory,WORK/directory)
shutil.copy2(MAIN/'Khazan.uproject',WORK/'Khazan.uproject')
def junction(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    command="New-Item -ItemType Junction -Path $env:KZ_LINK_DEST -Target $env:KZ_LINK_SOURCE | Out-Null"
    import os
    env=dict(os.environ,KZ_LINK_DEST=str(dst),KZ_LINK_SOURCE=str(src))
    subprocess.run(['powershell','-NoProfile','-Command',command],env=env,check=True,capture_output=True)
for item in (MAIN/'Plugins').iterdir():
    dest=WORK/'Plugins'/item.name
    if item.name!='Cog': junction(item,dest); continue
    dest.mkdir(parents=True)
    for child in item.iterdir():
        if child.name=='Intermediate':continue
        if child.is_dir():shutil.copytree(child,dest/child.name)
        else:shutil.copy2(child,dest/child.name)
owned=set()
def own(package):
    owned.add(Path(package.split('.')[0].removeprefix('/Game/')+'.uasset'))
for row in csv.DictReader((MAIN/'Saved/ImportReports/MonsterVFX_20261008/NativePlaybackCases.tsv').open(encoding='utf-8-sig'),delimiter='\t'):
    if row['family'] in ('Swordsman','SwordShield','HeavySwordsman','HalberdElite') and row['category']=='Attack':own(row['asset'])
for row in json.loads((MAIN/'Metadata/CombatFinishFollowup_20261012/Authored.json').read_text(encoding='utf-8'))['montages']:own(row['path'])
for p in ['/Game/_Art/Player/Animation/InGame/DAS/Guard/AM_DAS_Player_Guard',
          '/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference',
          '/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst',
          '/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard',
          '/Game/Data/ComboCommand/DA_Player_Combo_Definition',
          '/Game/Data/Character/DA_CharacterDefinition_Player',
          '/Game/VFX/01_ARPGEssentials/Materials/MM_VFX_MaskedParticles']:
    own(p)
def stage(src,dst,relative=Path()):
    dst.mkdir(parents=True,exist_ok=True)
    for child in src.iterdir():
        rel=relative/child.name; target=dst/child.name
        if child.is_dir():
            if any(rel in p.parents for p in owned):stage(child,target,rel)
            else:junction(child,target)
        else:shutil.copy2(child,target)
stage(MAIN/'Content',WORK/'Content')
for directory in ('Scripts','Metadata','Docs'):junction(MAIN/directory,WORK/directory)
baseline={str(p):hashlib.sha256((MAIN/'Content'/p).read_bytes()).hexdigest() for p in owned if (MAIN/'Content'/p).exists()}
for p in baseline:
    assert hashlib.sha256((WORK/'Content'/p).read_bytes()).hexdigest()==baseline[p]
(OUT/'Stage.json').write_text(json.dumps({'work':str(WORK),'owned_assets':baseline,'source_sha256':{str(p.relative_to(MAIN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (MAIN/'Source').rglob('*') if p.is_file()},'cog':'separate copied source/binaries; no Main/plugin build output'},indent=2),encoding='utf-8')
print('STAGED',len(baseline),'target packages; unrelated Content junctions read only')
