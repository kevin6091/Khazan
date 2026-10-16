"""Launch only task-owned hidden editors; author only the independent work copy."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time

main=Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
root=main/'Metadata/HeinMachColourVFX_20261015'
engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
mode,label,entry=sys.argv[1:4]
project=work if mode.startswith('work_') else main
commandlet=mode.endswith('audit') or mode.endswith('author')
out=root/label;out.mkdir(parents=True,exist_ok=False)
cmd=[str(engine/('UnrealEditor-Cmd.exe' if commandlet else 'UnrealEditor.exe')),str(project/'Khazan.uproject'),
     '-unattended','-nosplash','-nosound','-NoSourceControl','-NoLiveCoding','-NoAutoSave','-EnablePlugins=GameFeatures',
     '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-abslog='+str(out/'Editor.log')]
if commandlet:cmd+=['-NullRHI','-run=pythonscript','-script='+str(main/entry)]
else:cmd+=['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-d3d12',
           '-ExecCmds=py '+str(main/entry)]
if not commandlet and os.environ.get('KZ_HM_COLOUR_FIXED')=='1':cmd+=['-UseFixedTimeStep','-FPS=60']
env=dict(os.environ,KZ_HM_COLOUR_OUT=str(out),KZ_HM_COLOUR_MAIN=str(main),KZ_HM_COLOUR_MODE=mode,
         PYTHONUTF8='1',UE_SKIP_UBT_SDK_SETUP='1')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
started=time.monotonic()
with (out/'stdout.txt').open('w',encoding='utf-8') as stream:
    process=subprocess.Popen(cmd,env=env,stdout=stream,stderr=subprocess.STDOUT,startupinfo=startup,
                             creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    (out/'Launch.json').write_text(json.dumps({'pid':process.pid,'project':str(project),'command':cmd,
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2),encoding='utf-8')
    print('HEIN_COLOUR_OWNED_EDITOR',process.pid,flush=True)
    while process.poll() is None:
        time.sleep(1)
        if not commandlet and (out/'Editor.log').exists():
            tail=(out/'Editor.log').read_text(encoding='utf-8',errors='replace')[-18000:]
            if 'LogPython: Error: Traceback' in tail and not any((out/name).exists() for name in ('Probe.json','Driver.json','Capture.json')):
                (out/'StartupFailure.json').write_text(json.dumps({'error':'Python startup failed before runtime callback registration','log_tail':tail[-5000:]}),encoding='utf-8')
                process.terminate()
    code=process.wait()
(out/'Exit.json').write_text(json.dumps({'pid':process.pid,'exit':code,'seconds':time.monotonic()-started},indent=2),encoding='utf-8')
print('HEIN_COLOUR_EXIT',code,flush=True)
sys.exit(code)
