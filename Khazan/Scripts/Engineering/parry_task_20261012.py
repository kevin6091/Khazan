"""Isolate author/build/PIE; journal only processes owned by this task."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess, sys, time
MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_ParryWork_20261012/Khazan'
OUT = MAIN / 'Metadata/Parry_20261012'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
WRITE_DIRS = ['Content/Bluprints/AbilitySystem/Abilities/Player/Guard',
              'Content/_Art/Player/Animation/InGame/DAS/Guard',
              'Content/_Art/Effects/Combat/GuardParry']
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def inputs(root):
    return {p.relative_to(root).as_posix():sha(p) for folder in ['Source','Config'] for p in (root/folder).rglob('*') if p.is_file()}

def parry_assets(root):
    author=OUT/'Author01/Authoring.json'
    if not author.exists():return {}
    paths=['Content/'+p.removeprefix('/Game/')+'.uasset' for p in json.loads(author.read_text(encoding='utf-8'))['saved']]
    return {p:sha(root/p) for p in paths if (root/p).is_file()}
def hidden():
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    return {'startupinfo':startup,'creationflags':subprocess.CREATE_NO_WINDOW}
def stage():
    assert not WORK.exists(), 'Preserve a previously started private task'
    WORK.mkdir(parents=True)
    baseline=inputs(MAIN)
    baseline['Khazan.uproject']=sha(MAIN/'Khazan.uproject')
    for folder in WRITE_DIRS:
        baseline.update({p.relative_to(MAIN).as_posix():sha(p) for p in (MAIN/folder).rglob('*') if p.is_file()})
    for rel in baseline:
        dest=OUT/'Before'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/rel,dest)
    for folder in ['Source','Config','Binaries']:
        shutil.copytree(MAIN/folder,WORK/folder)
    shutil.copy2(MAIN/'Khazan.uproject',WORK/'Khazan.uproject')
    # Writable assets are real copies. All other Content is read-only for this task.
    def tree(source,dest,rel):
        relevant=any(w==rel or w.startswith(rel+'/') for w in WRITE_DIRS)
        if not relevant:
            result=subprocess.run(['powershell.exe','-NoProfile','-Command',
                "New-Item -ItemType Junction -Path '"+str(dest)+"' -Target '"+str(source)+"' | Out-Null"],capture_output=True,**hidden())
            assert result.returncode==0,result.stderr
        elif rel in WRITE_DIRS:shutil.copytree(source,dest)
        else:
            dest.mkdir()
            for child in source.iterdir():
                if child.is_dir():tree(child,dest/child.name,rel+'/'+child.name)
                else:shutil.copy2(child,dest/child.name)
    tree(MAIN/'Content',WORK/'Content','Content')
    shutil.copytree(MAIN/'Plugins',WORK/'Plugins',ignore=shutil.ignore_patterns('Intermediate','.git','Saved'))
    for folder in ['Saved','Metadata','Scripts']:(WORK/folder).mkdir(exist_ok=True)
    (OUT/'Baseline.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'main':str(MAIN),'work':str(WORK),'files':baseline,'writable_dirs':WRITE_DIRS},indent=2),encoding='utf-8')
    print('PARRY STAGED',len(baseline),flush=True)
def run(kind,name,entry=None):
    out=OUT/name;out.mkdir(exist_ok=False)
    project=MAIN if kind.startswith('main_') else WORK;kind=kind.removeprefix('main_')
    if kind=='build':
        cmd=[str(ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(ENGINE/'Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'),
             'KhazanEditor','Win64','Development','-Project='+str(project/'Khazan.uproject'),'-WaitMutex','-NoHotReloadFromIDE','-NoUBA','-NoXGE']
        if project==MAIN:cmd+=['-ModuleWithSuffix=Khazan,2026101290']
    else:
        commandlet=kind=='commandlet'
        cmd=[str(ENGINE/'Binaries/Win64'/('UnrealEditor-Cmd.exe' if commandlet else 'UnrealEditor.exe')),str(project/'Khazan.uproject'),
             '-unattended','-nosplash','-NoSourceControl','-NoLiveCoding','-NoAutoSave','-EnablePlugins=GameFeatures,CascadeToNiagaraConverter',
             '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-abslog='+str(out/'Editor.log')]
        if commandlet:cmd+=['-NullRHI','-run=pythonscript','-script='+str((MAIN/entry).resolve())]
        else:
            cmd+=['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-ExecCmds=py '+str((MAIN/entry).resolve())]
            if kind=='asset_editor':cmd+=['-NullRHI']
        if kind!='audio':cmd+=['-nosound']
    env=dict(os.environ,UE_SKIP_UBT_SDK_SETUP='1',PYTHONUTF8='1',KZ_PARRY_OUT=str(out),KZ_PARRY_MAIN=str(MAIN),KZ_PARRY_MODE=kind)
    start=time.monotonic()
    with (out/'stdout.txt').open('w',encoding='utf-8') as log:
        p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,**hidden())
        (out/'Launch.json').write_text(json.dumps({'pid':p.pid,'command':cmd,'utc':datetime.now(timezone.utc).isoformat(),'source':inputs(project),'parry_assets':parry_assets(project)},indent=2),encoding='utf-8')
        print('OWNED_PARRY_PROCESS',p.pid,flush=True)
        try:rc=p.wait(timeout=1200)
        except subprocess.TimeoutExpired:p.terminate();rc=p.wait(timeout=30)
    (out/'Exit.json').write_text(json.dumps({'pid':p.pid,'exit':rc,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')
    print('OWNED_PARRY_EXIT',rc,flush=True);return rc
if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    if sys.argv[1]=='stage':stage()
    else:sys.exit(run(*sys.argv[1:]))
