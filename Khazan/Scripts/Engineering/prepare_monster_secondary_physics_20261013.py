"""Reuse the idle, isolated PlayerParts build cache, with copied writable assets."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
assert WORK.is_dir()
assert not (OUT/'Preparation.json').exists(), 'Do not restage an active task'
processes=subprocess.run(['powershell.exe','-NoProfile','-Command',
    "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' } | Select-Object -ExpandProperty CommandLine"],capture_output=True,text=True).stdout
assert str(WORK).replace('\\','/').lower() not in processes.replace('\\','/').lower()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def separate(rel):
    source=MAIN/rel
    dest=WORK/rel
    assert source.is_file(),rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Existing Content hardlinks are read-only. Replace the directory entry before UE saves.
    temp=dest.with_name(dest.name+'.monsterphysics_copy')
    shutil.copy2(source,temp)
    os.replace(temp,dest)
    return sha(source)
targets=[p.relative_to(MAIN).as_posix() for p in (MAIN/'Content/_Art/Enemies').rglob('*.uasset')
    if p.name.startswith('SK_') and '/Metadata/' not in p.as_posix()]
targets += [p.relative_to(MAIN).as_posix() for p in (MAIN/'Content/Bluprints/Monsters').glob('*.uasset')]
baseline={}
for rel in targets:
    baseline[rel]=separate(rel)
    b=OUT/'Before'/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/rel,b)
# Latest source/config and player tuning inputs, all independent copies.
for folder in ('Source','Config'):
    for p in (MAIN/folder).rglob('*'):
        if p.is_file(): separate(p.relative_to(MAIN).as_posix())
for p in (WORK/'Source/Khazan/Tests').glob('PlayerParts*Editor.cpp'):
    archive=OUT/'BeforeWork'/p.relative_to(WORK)
    archive.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,archive)
    p.unlink()  # Work-only obsolete author/tests are archived, never deleted from Main.
separate('Khazan.uproject')
for p in (MAIN/'Content/_Art/Player/Character').rglob('*.uasset'):
    separate(p.relative_to(MAIN).as_posix())
build=WORK/'Source/Khazan/Khazan.Build.cs'
source=build.read_text(encoding='utf-8')
source=source.replace('"Json", "UnrealEd", "MovieScene"','"Json", "UnrealEd", "MovieScene", "AnimGraph", "BlueprintGraph", "KismetCompiler", "JsonUtilities", "AssetRegistry"')
build.write_text(source,encoding='utf-8')
plan=dict(main=str(MAIN),work=str(WORK),meshes=['/Game/'+r.removeprefix('Content/').removesuffix('.uasset') for r in targets if Path(r).name.startswith('SK_')],
    blueprints=['/Game/'+r.removeprefix('Content/').removesuffix('.uasset') for r in targets if Path(r).name.startswith('BP_')],baseline=baseline)
(OUT/'Preparation.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(WORK/'Saved/MonsterSecondaryPhysicsPlan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
shutil.copy2(MAIN/'Scripts/Engineering/MonsterSecondaryPhysicsEditor.cpp',WORK/'Source/Khazan/Tests/MonsterSecondaryPhysicsEditor.cpp')
print('MONSTER PHYSICS PREPARED',len(plan['meshes']),len(plan['blueprints']))
