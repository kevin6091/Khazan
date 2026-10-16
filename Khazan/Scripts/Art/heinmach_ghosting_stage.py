"""Task-owned real-RHI game; main assets and the user's editor stay untouched."""
from pathlib import Path
import json
import os
import runpy
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'Saved/ArtStaging/HeinMachGhosting_20261008'
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008'
PY='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'

def setup():
    old=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_reference_stage.py'))
    owner=old['setup'].__globals__;owner.update(STAGE=STAGE,OUT=OUT)
    old['setup']()

def launch():
    assert (OUT/'StageSetup.json').is_file()
    shutil.copy2(ROOT/'Scripts/Art/heinmach_ghosting_game.py',STAGE/'Scripts/Art/heinmach_ghosting_game.py')
    args=[PY,str(STAGE/'Khazan.uproject'),'/Game/Maps/L_HeinMach_Environment','-game','-unattended','-nosound','-nosplash',
      '-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-NoSourceControl','-NoLiveCoding',
      '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-EnablePlugins=GameFeatures,PythonScriptPlugin',
      '-abslog='+str(OUT/'game.log'),'-ExecCmds=py '+str(STAGE/'Scripts/Art/heinmach_ghosting_game.py')]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    env=dict(os.environ,UE_SKIP_UBT_SDK_SETUP='1',PYTHONUTF8='1')
    p=subprocess.Popen(args,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW,env=env)
    (OUT/'Launch.json').write_text(json.dumps(dict(pid=p.pid,args=args),indent=2),encoding='utf-8')
    print('GHOST_BACKGROUND_GAME',p.pid,flush=True);p.wait();print('GHOST_BACKGROUND_EXIT',p.returncode,flush=True)

if __name__=='__main__':{'setup':setup,'launch':launch}[sys.argv[1]]()
