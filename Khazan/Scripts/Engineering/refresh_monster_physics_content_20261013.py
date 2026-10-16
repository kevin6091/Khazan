"""Replace the work project's old read-only snapshot with current Main dependencies."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
plan=json.loads((OUT/'Preparation.json').read_text(encoding='utf-8'))
old=WORK/'Content';archive=WORK/'Saved/MonsterSecondaryPhysicsPriorContent_20261013'
assert old.resolve().is_relative_to(WORK.resolve()) and archive.resolve().is_relative_to(WORK.resolve())
assert not archive.exists()
processes=subprocess.run(['powershell.exe','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' } | Select-Object -ExpandProperty CommandLine"],capture_output=True,text=True).stdout
assert str(WORK).replace('\\','/').lower() not in processes.replace('\\','/').lower()
os.rename(old,archive)
write_dirs=sorted(set(str(Path(rel).parent).replace('\\','/') for rel in plan['baseline']))
write_dirs+=['Content/Monsters/Shared/Physics']
def tree(source,dest,rel):
    if rel in write_dirs:
        if source.exists():shutil.copytree(source,dest)
        else:dest.mkdir(parents=True)
        return
    if not any(w.startswith(rel+'/') for w in write_dirs):
        result=subprocess.run(['powershell.exe','-NoProfile','-Command',
            "New-Item -ItemType Junction -Path '"+str(dest)+"' -Target '"+str(source)+"' | Out-Null"],capture_output=True)
        assert result.returncode==0,result.stderr
        return
    dest.mkdir()
    children={p.name:p for p in source.iterdir()}
    for w in write_dirs:
        if w.startswith(rel+'/'):
            name=w[len(rel)+1:].split('/')[0]
            children.setdefault(name,source/name)
    for name,child in children.items():
        if child.is_file():shutil.copy2(child,dest/name)
        else:tree(child,dest/name,rel+'/'+name)
tree(MAIN/'Content',WORK/'Content','Content')
current={rel:hashlib.sha256((MAIN/rel).read_bytes()).hexdigest() for rel in plan['baseline']}
assert current==plan['baseline'], 'Concurrent target change: rebase before editing'
(OUT/'CurrentContentIntake.json').write_text(json.dumps(dict(archive=str(archive),writable_dirs=write_dirs,target_hashes=current),indent=2),encoding='utf-8')
print('FRESH CURRENT CONTENT',len(write_dirs))
