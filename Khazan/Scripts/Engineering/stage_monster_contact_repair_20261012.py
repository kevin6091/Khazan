"""Rebase the idle private project once, preserving current Main and prior private source."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess
MAIN=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=MAIN/'Metadata/MonsterRootCollisionRepair_20261012';assert not (OUT/'Stage.json').exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inventory=json.loads((OUT/'MainUsageAudit02/Usage.json').read_text(encoding='utf-8'));assert inventory['status']=='passed'
paths={r['asset'].split('.')[0] for r in inventory['sequences']+inventory['montages']+inventory['definitions']}
paths.update('/Game/Monsters/'+r['family']+'/Data/DA_Character_'+r['family'] for r in inventory['families'])
before={str(p.relative_to(MAIN)):sha(p) for p in (MAIN/'Source').rglob('*') if p.is_file()}
for asset in sorted(paths):
    p=MAIN/('Content/'+asset.removeprefix('/Game/')+'.uasset');assert p.exists(),p
    before[str(p.relative_to(MAIN))]=sha(p)
(OUT/'Baseline.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'main':str(MAIN),'work':str(WORK),'files':before,'usage':'MainUsageAudit02/Usage.json'},indent=2),encoding='utf-8')
shutil.copytree(WORK/'Source',OUT/'WorkSourceBefore')
for folder in ['Source','Config']:shutil.copytree(MAIN/folder,WORK/folder,dirs_exist_ok=True)
shutil.copy2(MAIN/'Khazan.uproject',WORK/'Khazan.uproject')
cmd=['robocopy',str(MAIN/'Content'),str(WORK/'Content'),'/E','/COPY:DAT','/DCOPY:DAT','/R:1','/W:1','/XJ','/MT:2','/NFL','/NDL','/NP','/LOG:'+str(OUT/'ContentSnapshot.log')]
result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode<8,result.returncode
manifest=json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));old=manifest['Modules']['Khazan']
alias='UnrealEditor-KhazanMonsterContactBaseline20261012.dll'
shutil.copy2(MAIN/'Binaries/Win64'/old,WORK/'Binaries/Win64'/alias)
manifest['Modules']['Khazan']=alias;(WORK/'Binaries/Win64/UnrealEditor.modules').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# This inherited private author is stale and not part of current Main. Retain it in the exact backup.
extra=WORK/'Source/Khazan/Tests/KZGiantFallAuthor.cpp'
if extra.exists() and not (MAIN/'Source/Khazan/Tests/KZGiantFallAuthor.cpp').exists():
    assert extra.resolve().is_relative_to(WORK.resolve())
    assert sha(extra)==sha(OUT/'WorkSourceBefore/Khazan/Tests/KZGiantFallAuthor.cpp');extra.unlink()
report={'utc':datetime.now(timezone.utc).isoformat(),'status':'staged','source_files':len([p for p in before if p.startswith('Source')]),'selected_packages':len(paths),'robocopy_exit':result.returncode,'baseline_module':alias,'new_runtime_files':0}
(OUT/'Stage.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
