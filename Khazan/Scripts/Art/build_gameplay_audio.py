from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
folder=OUT/(sys.argv[1] if len(sys.argv)>1 else 'Build01')
folder.mkdir(exist_ok=False)
engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine')
args=[str(engine/'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),
      str(engine/'Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'),
      'KhazanEditor','Win64','Development','-Project='+str(ROOT/'Khazan.uproject'),
      '-WaitMutex','-NoHotReloadFromIDE','-NoUBA','-NoXGE','-ModuleWithSuffix=Khazan,'+(sys.argv[2] if len(sys.argv)>2 else '2026101291')]
inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Source').rglob('*') if p.is_file()}
startup=subprocess.STARTUPINFO()
startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow=subprocess.SW_HIDE
env=dict(os.environ,UE_SKIP_UBT_SDK_SETUP='1')
start=time.monotonic()
with (folder/'Build.log').open('w',encoding='utf-8') as stream:
    proc=subprocess.Popen(args,env=env,stdout=stream,stderr=subprocess.STDOUT,
                          startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
    (folder/'Launch.json').write_text(json.dumps({'pid':proc.pid,'args':args,'source_inputs':inputs},indent=2),encoding='utf-8')
    code=proc.wait()
(folder/'Exit.json').write_text(json.dumps({'pid':proc.pid,'exit_code':code,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')
print('AUDIO BUILD',code,flush=True)
raise SystemExit(code)
