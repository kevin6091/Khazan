"""Snapshot current Main into the existing, idle GiantFall private project."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT = MAIN / 'Metadata/MonsterPresentationRepair_20261011'
OUT.mkdir(exist_ok=True)
assert not (OUT/'Stage.json').exists(), 'Completed stage must not be replayed over working changes'
assert WORK.is_dir() and WORK != MAIN
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
if (OUT/'Baseline.json').exists():
    before=json.loads((OUT/'Baseline.json').read_text(encoding='utf-8'))['files']
else:
    before = {}
    for folder in ['Source', 'Config', 'Content/Monsters', 'Content/UI', 'Content/_Art/Effects', 'Content/_Art/Enemies']:
        for p in (MAIN / folder).rglob('*'):
            if p.is_file(): before[p.relative_to(MAIN).as_posix()] = sha(p)
    for name in ['Khazan.uproject', 'Binaries/Win64/UnrealEditor.modules']:
        before[name] = sha(MAIN / name)
    (OUT/'Baseline.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(), 'main':str(MAIN), 'work':str(WORK), 'files':before},indent=2),encoding='utf-8')
    shutil.copytree(WORK/'Source', OUT/'WorkSourceBefore')
for folder in ['Source', 'Config', 'Docs']:
    shutil.copytree(MAIN/folder, WORK/folder, dirs_exist_ok=True)
shutil.copy2(MAIN/'Khazan.uproject', WORK/'Khazan.uproject')
cmd=['robocopy',str(MAIN/'Content'),str(WORK/'Content'),'/E','/COPY:DAT','/DCOPY:DAT','/R:1','/W:1','/XJ','/MT:2','/NFL','/NDL','/NP','/LOG:'+str(OUT/'ContentSnapshot.log')]
result=subprocess.run(cmd, capture_output=True, text=True)
assert result.returncode < 8, (result.returncode,result.stdout,result.stderr)
# Existing private author includes require these editor modules, never delivered to Main.
build=WORK/'Source/Khazan/Khazan.Build.cs'
text=build.read_text(encoding='utf-8-sig')
needed=['UnrealEd','AssetRegistry','AssetTools','JsonUtilities','KismetCompiler','BlueprintGraph','AnimGraph','StateTreeEditorModule','PropertyBindingUtils','AnimationWarpingRuntime','AnimationWarpingEditor']
missing=[n for n in needed if '"'+n+'"' not in text]
if missing:
    text,n=re.subn(r'(// Native PIE report serialization only\.)',lambda m:m[1]+'\n\t\tif (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new string[] { '+', '.join('"'+n+'"' for n in missing)+' });',text,count=1)
    assert n == 1
    build.write_text(text,encoding='utf-8')
(WORK/'Metadata/MonsterPresentationRepair_20261011').mkdir(parents=True,exist_ok=True)
manifest=json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
original=manifest['Modules']['Khazan']
alias='UnrealEditor-KhazanMonsterPresentationBaseline20261011.dll'
shutil.copy2(WORK/'Binaries/Win64/UnrealEditor.modules',OUT/'WorkModulesBefore.json')
shutil.copy2(MAIN/'Binaries/Win64'/original,WORK/'Binaries/Win64'/alias)
manifest['Modules']['Khazan']=alias
(WORK/'Binaries/Win64/UnrealEditor.modules').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
report={'status':'staged', 'baseline_files':len(before),'robocopy_exit':result.returncode,'private_editor_dependencies':missing,'utc':datetime.now(timezone.utc).isoformat()}
(OUT/'Stage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
