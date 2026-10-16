"""One journaled build of the owned private repair; no old Main DLL delivery."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,sys,time
MAIN=Path(__file__).resolve().parents[2];ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
name,suffix=sys.argv[1:3];out=MAIN/'Metadata/MonsterRootCollisionRepair_20261012'/name;out.mkdir(exist_ok=False)
def sources():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Source/Khazan').rglob('*') if p.suffix in ['.h','.cpp','.cs']}
before=sources();cmd=['C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat','KhazanEditor','Win64','Development',str(ROOT/'Khazan.uproject'),'-WaitMutex','-NoHotReloadFromIDE','-MaxParallelActions=2','-ModuleWithSuffix=Khazan,'+suffix]
(out/'Input.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'command':cmd,'source_sha256':before},indent=2),encoding='utf-8')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
start=time.monotonic()
with (out/'Build.log').open('wb') as log:
    p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW);code=p.wait()
module=ROOT/'Binaries/Win64'/('UnrealEditor-Khazan-'+suffix+'.dll')
(out/'Exit.json').write_text(json.dumps({'exit':code,'seconds':time.monotonic()-start,'input_unchanged':before==sources(),'module':str(module),'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest() if module.exists() else None},indent=2),encoding='utf-8')
print('CONTACT_BUILD',code,'input_unchanged',before==sources(),flush=True);sys.exit(code)
