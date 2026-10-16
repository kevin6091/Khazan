"""Unique DLL build for fresh own Main verification; no control of the interactive editor."""
from pathlib import Path
from datetime import datetime, timezone
import os,subprocess,hashlib,json,time,sys
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'Metadata/MonsterBloodReference_20261012'/sys.argv[1];out.mkdir(exist_ok=False)
suffix=sys.argv[2]
cmd=['C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat','KhazanEditor','Win64','Development',str(ROOT/'Khazan.uproject'),'-WaitMutex','-NoHotReloadFromIDE','-MaxParallelActions=2','-ModuleWithSuffix=Khazan,'+suffix]
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Source/Khazan').rglob('*') if p.suffix in ['.h','.cpp','.cs']}
(out/'Input.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'command':cmd,'source_sha256':before},indent=2),encoding='utf-8')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
start=time.monotonic()
with (out/'Build.log').open('wb') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW);code=p.wait()
after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Source/Khazan').rglob('*') if p.suffix in ['.h','.cpp','.cs']}
module=ROOT/'Binaries/Win64'/('UnrealEditor-Khazan-'+suffix+'.dll')
(out/'Exit.json').write_text(json.dumps({'exit':code,'seconds':time.monotonic()-start,'input_unchanged':before==after,'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest() if module.exists() else None,'module':str(module)},indent=2),encoding='utf-8')
print('MAIN_BLOOD_BUILD',code,'input_unchanged',before==after,flush=True);sys.exit(code)
