"""Private BP_Player rendering-mask authoring; no main package writes."""
from pathlib import Path
import json
import os
import runpy
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'Saved/ArtStaging/HeinMachGhostingParts_20261008'
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008/Parts'
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')

def setup():
    old=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_reference_stage.py'))
    owner=old['setup'].__globals__
    owner.update(STAGE=STAGE,OUT=OUT,
                 MUTABLE=old['MUTABLE']+('_Art/Player/Character/Bluprints',))
    old['setup']()

def run(kind):
    assert kind in ('author','audit','config')
    assert (OUT/'StageSetup.json').is_file()
    script='heinmach_ghosting_config_audit.py' if kind=='config' else 'heinmach_ghosting_parts_author.py'
    if kind=='config':
        for name in ('DefaultEngine.ini','DefaultEditor.ini'):
            shutil.copy2(ROOT/'Config'/name,STAGE/'Config'/name)
    shutil.copy2(ROOT/'Scripts/Art'/script,STAGE/'Scripts/Art'/script)
    args=[str(ENGINE/'UnrealEditor-Cmd.exe'),str(STAGE/'Khazan.uproject'),
          '-nullrhi','-unattended','-nosound','-nosplash','-NoSourceControl','-NoLiveCoding',
          '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
          '-EnablePlugins=GameFeatures,PythonScriptPlugin',
          '-abslog='+str(OUT/(kind+'.log')),'-run=pythonscript',
          '-script='+str(STAGE/'Scripts/Art'/script),'-GhostPartsMode='+kind]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    env=dict(os.environ,UE_SKIP_UBT_SDK_SETUP='1',PYTHONUTF8='1')
    p=subprocess.Popen(args,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW,env=env)
    (OUT/(kind+'Launch.json')).write_text(json.dumps(dict(pid=p.pid,args=args),indent=2),encoding='utf-8')
    print('GHOST_PARTS_BACKGROUND',kind,p.pid,flush=True)
    p.wait()
    report_path=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008/FreshConfigAudit.json' if kind=='config' else OUT/(kind+'Report.json')
    report=json.loads(report_path.read_text(encoding='utf-8'))
    assert p.returncode==0 and report['success'],report
    print(json.dumps({'mode':kind,'exit_code':p.returncode,'report':str(report_path)}),flush=True)

if __name__=='__main__':
    setup() if sys.argv[1]=='setup' else run(sys.argv[1])
