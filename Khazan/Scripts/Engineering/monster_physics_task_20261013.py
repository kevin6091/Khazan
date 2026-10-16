"""Separate, hidden, low-priority editor processes; never control foreign editors."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT = MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')

def run(kind, name, entry=None):
    out=OUT/name
    out.mkdir(parents=True,exist_ok=False)
    project=MAIN if kind.startswith('main_') else WORK
    kind=kind.removeprefix('main_')
    if kind=='build':
        cmd=[str(ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),
            str(ENGINE/'Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'),
            'KhazanEditor','Win64','Development','-Project='+str(project/'Khazan.uproject'),
            '-WaitMutex','-NoHotReloadFromIDE','-NoHotReload','-NoUBA','-NoXGE','-MaxParallelActions=1','-Log='+str(out/'UnrealBuildTool.log')]
    else:
        cmd=[str(ENGINE/'Binaries/Win64'/('UnrealEditor-Cmd.exe' if kind=='commandlet' else 'UnrealEditor.exe')),
            str(project/'Khazan.uproject'),'-unattended','-nosplash','-NoSourceControl','-NoLiveCoding',
            '-NoAutoSave','-EnablePlugins=GameFeatures','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
            '-abslog='+str(out/'Editor.log'),'-nosound']
        if kind=='commandlet':
            cmd+=['-NullRHI','-run=pythonscript','-script='+str(MAIN/entry)]
        else:
            cmd+=['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900',
                '-ExecCmds=py '+str(MAIN/entry)]
            if kind=='asset_editor':cmd+=['-NullRHI']
            if kind=='rhi':cmd+=['-UseFixedTimeStep','-FPS=60']
    startup=subprocess.STARTUPINFO()
    startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow=0
    env=dict(os.environ,PYTHONUTF8='1',UE_SKIP_UBT_SDK_SETUP='1',KZ_MONSTER_PHYSICS_OUT=str(out))
    start=time.monotonic()
    with (out/'stdout.txt').open('w',encoding='utf-8') as log:
        p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        (out/'Launch.json').write_text(json.dumps(dict(pid=p.pid,command=cmd,
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2),encoding='utf-8')
        print('OWNED_MONSTER_PHYSICS_PROCESS',p.pid,flush=True)
        rc=p.wait()
    (out/'Exit.json').write_text(json.dumps(dict(pid=p.pid,exit=rc,seconds=time.monotonic()-start),indent=2),encoding='utf-8')
    print('OWNED_MONSTER_PHYSICS_EXIT',rc,flush=True)
    return rc

if __name__=='__main__':
    sys.exit(run(*sys.argv[1:]))
