"""Owned-process build/run journal; never closes an existing editor or changes config."""
from pathlib import Path
from datetime import datetime, timezone
import sys, os, json, hashlib, subprocess, time, shutil
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/CombatFinishFollowup_20261012'
OUT.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sources(): return {str(p.relative_to(ROOT)): sha(p) for p in (ROOT/'Source').rglob('*') if p.is_file()}
mode, name = sys.argv[1:3]
folder = OUT/name
folder.mkdir(exist_ok=False)
if mode == 'baseline':
    shutil.copytree(ROOT/'Source', folder/'Source')
    (folder/'Files.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(), 'files':sources()},indent=2),encoding='utf-8')
    print('BASELINE_SAVED',len(sources())); sys.exit(0)
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
env = dict(os.environ, PYTHONUTF8='1', KZ_COMBAT_FINISH_OUT=str(folder), KZ_MONSTER_CONTACT_OUT=str(folder), KZ_CLEAN_OUTPUT=str(folder))
if len(sys.argv)>5 and sys.argv[5]=='lethal':env['KZ_COMBAT_FINISH_LETHAL']='1'
if mode == 'build':
    cmd = [str(engine/'Build/BatchFiles/Build.bat'),'KhazanEditor','Win64','Development',str(ROOT/'Khazan.uproject'),'-WaitMutex','-NoHotReloadFromIDE','-MaxParallelActions=1','-NoXGE']
else:
    entry = ROOT/sys.argv[3]
    exe = 'UnrealEditor-Cmd.exe' if mode=='probe' else 'UnrealEditor.exe'
    cmd = [str(engine/'Binaries/Win64'/exe),str(ROOT/'Khazan.uproject'),'-unattended','-nosplash','-nosound','-NoSourceControl','-NoLiveCoding','-NoAutoSave','-EnablePlugins=GameFeatures','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-abslog='+str(folder/'Editor.log')]
    if mode=='probe': cmd += ['-NullRHI','-run=pythonscript','-script='+str(entry)]
    else:
        cmd += ['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-ExecCmds=py '+str(entry),'-d3d12']
        env.update(KZ_MONSTER_REPAIR_OUT=str(folder),KZ_MONSTER_REPAIR_MODE='rhi',KZ_MONSTER_REPAIR_TEST=sys.argv[4],KZ_MONSTER_CONTACT_TEST=sys.argv[4])
before=sources(); startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
start=time.monotonic()
with (folder/('Build.log' if mode=='build' else 'Process.log')).open('wb') as log:
    p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
    (folder/'Launch.json').write_text(json.dumps({'pid':p.pid,'command':cmd,'utc':datetime.now(timezone.utc).isoformat(),'source_sha256':before},indent=2),encoding='utf-8')
    print('OWNED_PROCESS',p.pid,flush=True)
    try:code=p.wait(timeout=1300)
    except subprocess.TimeoutExpired:p.terminate();code=p.wait(timeout=30)
module_name=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']
module=ROOT/'Binaries/Win64'/module_name
(folder/'Exit.json').write_text(json.dumps({'exit':code,'seconds':time.monotonic()-start,'input_unchanged':before==sources(),'module':str(module),'module_sha256':sha(module)},indent=2),encoding='utf-8')
print('OWNED_EXIT',code,flush=True);sys.exit(code)
