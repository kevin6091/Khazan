from pathlib import Path
import json
import os
import subprocess
import time
import uuid
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/HeinMachSnow_20261006'
assert json.loads((OUT/'Delivery20261007.json').read_text())['success']
token=uuid.uuid4().hex
args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',str(ROOT/'Khazan.uproject'),
    '/Engine/Maps/Entry','-unattended','-nosplash','-nosound','-RenderOffscreen','-NoSourceControl',
    '-windowed','-ResX=1280','-ResY=720','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
    '-EnablePlugins=GameFeatures','-abslog='+str(OUT/'main_verify.log'),
    '-ExecCmds=py '+str(ROOT/'Scripts/Art/heinmach_snow_main_verify_entry.py')]
env=dict(os.environ,KZ_SNOW_MAIN_VERIFY_TOKEN=token,UE_SKIP_UBT_SDK_SETUP='1',PYTHONUTF8='1')
si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
process=subprocess.Popen(args,env=env,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW)
(OUT/'MainVerificationLaunch.json').write_text(json.dumps(dict(token=token,pid=process.pid,command=args),indent=2),encoding='utf-8')
print('OWN_MAIN_BACKGROUND_VERIFIER',process.pid,flush=True)
process.wait();print('OWN_MAIN_BACKGROUND_EXIT',process.returncode,flush=True)
