"""Guarded update of the owned snow implementation, without touching the live loaded DLL."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
ROOT=Path(__file__).resolve().parents[2]
STAGE=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=ROOT/'Saved/ImportReports/HeinMachSnow_20261006'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
delivery=json.loads((OUT/'Delivery20261007.json').read_text())
rel=Path('Source/Khazan/Environment/KZSnowDeformation.cpp')
old=next(r['sha256'] for r in delivery['files'] if r['path']==rel.as_posix())
previous=OUT/'SnowContactModuleUpdate.json'
if previous.exists():old=json.loads(previous.read_text())['source_sha256']
assert sha(ROOT/rel)==old,'Owned source changed externally'
for p in (ROOT/'Source').rglob('*'):
    if not p.is_file() or p==ROOT/rel or p.name=='KZMonsterAIPIETest.cpp':continue
    assert sha(p)==sha(STAGE/p.relative_to(ROOT)),str(p)
manifest=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text())
assert manifest['Modules']['Khazan'] in ('UnrealEditor-Khazan.dll','UnrealEditor-KhazanSnow20261007.dll')
target=ROOT/'Binaries/Win64/UnrealEditor-KhazanSnow20261007.dll'
normal=ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll';normal_sha=sha(normal)
backup=OUT/('ModuleBeforeContact_'+datetime.datetime.now().strftime('%H%M%S')+'.dll');shutil.copy2(target,backup)
shutil.copy2(STAGE/rel,ROOT/rel)
temp=target.with_suffix('.snowtmp');shutil.copy2(STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll',temp);temp.replace(target)
shutil.copy2(STAGE/'Binaries/Win64/UnrealEditor-Khazan.pdb',target.with_suffix('.pdb'))
assert sha(target)==sha(STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')
manifest['Modules']['Khazan']=target.name
manifest_temp=ROOT/'Binaries/Win64/UnrealEditor.modules.snowtmp'
manifest_temp.write_text(json.dumps(manifest,indent=2),encoding='utf-8');manifest_temp.replace(ROOT/'Binaries/Win64/UnrealEditor.modules')
assert sha(normal)==normal_sha
report=dict(success=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=sha(ROOT/rel),
    module_sha256=sha(target),previous_module_backup=str(backup),map_sha256=sha(ROOT/'Content/Maps/L_HeinMach_Environment.umap'),
    current_normal_module_preserved_sha256=normal_sha)
previous.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SNOW_CONTACT_MODULE_UPDATED',report['module_sha256'])
