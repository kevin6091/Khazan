"""Isolated HeinMach map work; explicit owned processes and hash-checked delivery."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess, sys, time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_HeinMachPrune_20261016/Khazan'
OUT = MAIN / 'Metadata/HeinMachRoutePrune_20261016'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
MAP = Path('Content/Maps/L_HeinMach_Environment.umap')

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def junction(source, dest):
    assert not dest.exists()
    subprocess.run(['powershell', '-NoProfile', '-Command',
        "New-Item -ItemType Junction -Path '" + str(dest) + "' -Target '" + str(source) + "' | Out-Null"], check=True)

def stage():
    assert not WORK.exists(), 'Do not overwrite an existing work project'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'Before').mkdir(exist_ok=True)
    shutil.copy2(MAIN/MAP, OUT/'Before'/MAP.name)
    WORK.mkdir(parents=True)
    shutil.copy2(MAIN/'Khazan.uproject', WORK/'Khazan.uproject')
    shutil.copytree(MAIN/'Config', WORK/'Config')
    binary = WORK/'Binaries/Win64'; binary.mkdir(parents=True)
    modules = json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text())
    for name in ['UnrealEditor.modules', *modules['Modules'].values()]:
        shutil.copy2(MAIN/'Binaries/Win64'/name, binary/name)
    for name in ['Source', 'Plugins']:
        junction(MAIN/name, WORK/name)
    (WORK/'Content').mkdir()
    for child in (MAIN/'Content').iterdir():
        target = WORK/'Content'/child.name
        if child.name == 'Maps': shutil.copytree(child, target)
        elif child.is_dir(): junction(child, target)
        else: shutil.copy2(child, target)
    write(OUT/'Baseline.json', dict(main=str(MAIN), work=str(WORK), map=str(MAP),
        map_sha=sha(MAIN/MAP), modules=modules,
        source_config_sha={p.relative_to(MAIN).as_posix():sha(p) for folder in ['Source','Config']
            for p in (MAIN/folder).rglob('*') if p.is_file()},
        utc=datetime.now(timezone.utc).isoformat()))
    print('STAGED', WORK, flush=True)

def run(name, mode, use_main=False):
    dest=OUT/name; dest.mkdir(exist_ok=False)
    project=MAIN if use_main else WORK
    graphical=mode in ['probe','capture','author','verify_scene']
    cmd=[str(ENGINE/'Binaries/Win64'/('UnrealEditor.exe' if graphical else 'UnrealEditor-Cmd.exe')),
        str(project/'Khazan.uproject'), '-unattended','-nosplash','-nosound','-NoSourceControl',
        '-NoLiveCoding','-NoAutoSave','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
        '-abslog='+str(dest/'Editor.log')]
    script=str(MAIN/'Scripts/Art/heinmach_route_prune_20261016.py')
    if graphical:
        cmd += ['/Engine/Maps/Entry','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720',
                '-ForceRes','-ExecCmds=py '+script]
    else: cmd += ['-NullRHI','-run=pythonscript','-script='+script]
    env=dict(os.environ, PYTHONUTF8='1', KZ_PRUNE_MAIN=str(MAIN), KZ_PRUNE_OUT=str(dest),
             KZ_PRUNE_MODE=mode)
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    start=time.monotonic()
    with (dest/'stdout.txt').open('w',encoding='utf-8') as stream:
        proc=subprocess.Popen(cmd,env=env,stdout=stream,stderr=subprocess.STDOUT,
                              startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
        write(dest/'Launch.json',dict(pid=proc.pid, args=cmd, map_sha=sha(project/MAP),
                                     utc=datetime.now(timezone.utc).isoformat()))
        print('OWNED_EDITOR',proc.pid,flush=True)
        code=proc.wait()
    write(dest/'Exit.json',dict(pid=proc.pid,exit_code=code,seconds=time.monotonic()-start))
    print('EXIT',code,flush=True)
    return code

if __name__=='__main__':
    if sys.argv[1]=='stage': stage()
    else: sys.exit(run(sys.argv[1],sys.argv[2],'--main' in sys.argv))
