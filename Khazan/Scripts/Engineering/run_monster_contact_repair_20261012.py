"""Journal one owned process for the monster root/collision repair."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,subprocess,time
MAIN=Path(__file__).resolve().parents[2]
name,entry,mode=sys.argv[1:4]
root=MAIN if mode.startswith('main_') else Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
mode=mode.removeprefix('main_');out=MAIN/'Metadata/MonsterRootCollisionRepair_20261012'/name
out.mkdir(parents=True,exist_ok=False)
exe='UnrealEditor-Cmd.exe' if mode=='commandlet' else 'UnrealEditor.exe'
cmd=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/'+exe,str(root/'Khazan.uproject'),'-unattended','-nosplash','-nosound','-NoSourceControl','-NoLiveCoding','-NoAutoSave','-EnablePlugins=GameFeatures','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-abslog='+str(out/'Editor.log')]
if mode=='commandlet':cmd+=['-NullRHI','-run=pythonscript','-script='+str(MAIN/entry)]
else:cmd+=['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-ExecCmds=py '+str(MAIN/entry)]
env=dict(os.environ,KZ_MONSTER_CONTACT_OUT=str(out),PYTHONUTF8='1',UE_SKIP_UBT_SDK_SETUP='1')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
p=subprocess.Popen(cmd,env=env,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
sources={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'Source/Khazan').rglob('*') if f.suffix in ['.h','.cpp','.cs']}
(out/'Launch.json').write_text(json.dumps({'pid':p.pid,'command':cmd,'utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sources},indent=2),encoding='utf-8')
print('OWNED_MONSTER_CONTACT_EDITOR',p.pid,flush=True);start=time.monotonic()
try:code=p.wait(timeout=1200)
except subprocess.TimeoutExpired:p.terminate();code=p.wait(timeout=30)
(out/'Exit.json').write_text(json.dumps({'pid':p.pid,'exit':code,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')
print('OWNED_MONSTER_CONTACT_EXIT',code,flush=True);sys.exit(code)
