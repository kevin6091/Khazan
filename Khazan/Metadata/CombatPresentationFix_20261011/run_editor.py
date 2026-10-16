from pathlib import Path
import os,sys,subprocess,json,time
base=Path(__file__).resolve().parent
main=base.parents[1]
project=Path(os.environ.get('KZ_PRESENTATION_PROJECT','C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan'))
assert project in [main,Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')]
name,script=sys.argv[1:3];out=base/name;out.mkdir(exist_ok=False)
engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
interactive='--pie' in sys.argv
map_asset=os.environ.get('KZ_PRESENTATION_MAP','/Game/Maps/DevMap')
assert map_asset in ('/Game/Maps/DevMap','/Game/Maps/L_HeinMach_Environment')
args=[str(engine/('UnrealEditor.exe' if interactive else 'UnrealEditor-Cmd.exe')),str(project/'Khazan.uproject'),
 '-unattended','-nosound','-nosplash','-NoLiveCoding','-NoSourceControl','-NoAutoSave',
 '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
 '-abslog='+str(out/'Editor.log')]
if interactive:args+=[map_asset,'-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-ExecCmds=py '+str(Path(script).resolve())]
else:args+=['-RenderOffscreen' if '--rhi' in sys.argv else '-nullrhi','-AllowCommandletRendering','-run=pythonscript','-script='+str(Path(script).resolve())]
env=dict(os.environ,KZ_CLEAN_OUTPUT=str(out),KZ_CLEAN_MAIN=str(main),UE_SKIP_UBT_SDK_SETUP='1')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=subprocess.SW_HIDE
start=time.monotonic()
with (out/'Stdout.txt').open('w',encoding='utf-8') as f:
 p=subprocess.Popen(args,env=env,stdout=f,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
 (out/'Launch.json').write_text(json.dumps({'pid':p.pid,'project':str(project),'args':args},indent=2),encoding='utf-8');rc=p.wait()
(out/'Exit.json').write_text(json.dumps({'pid':p.pid,'exit_code':rc,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')
print(name,'exit',rc,flush=True);raise SystemExit(rc)
