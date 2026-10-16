"""Owned hidden UE process; selective isolated map authoring and CAS delivery."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, stat, subprocess, sys, time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_SceneLookWork_20261012/Khazan'
OUT = MAIN / 'Metadata/SceneLook_20261012'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
MAP_FILES = ['Content/Maps/DevMap.umap', 'Content/Maps/L_HeinMach_Environment.umap']

def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def stage():
    assert not WORK.exists(), 'Existing task workspace must be preserved'
    WORK.mkdir(parents=True)
    baseline = {rel: sha(MAIN/rel) for rel in MAP_FILES}
    for rel in MAP_FILES:
        dst = OUT/'Before'/rel; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MAIN/rel, dst)
    shutil.copy2(MAIN/'Khazan.uproject', WORK/'Khazan.uproject')
    shutil.copytree(MAIN/'Config', WORK/'Config')
    shutil.copytree(MAIN/'Binaries', WORK/'Binaries', ignore=shutil.ignore_patterns('*.pdb'))
    for name in ['Source', 'Plugins']:
        subprocess.run(['powershell','-NoProfile','-Command',
            'New-Item -ItemType Junction -Path "'+str(WORK/name)+'" -Target "'+str(MAIN/name)+'" | Out-Null'], check=True)
    def content(source, dest, rel):
        if not (rel=='Content' or rel=='Content/Maps'):
            subprocess.run(['powershell','-NoProfile','-Command',
                'New-Item -ItemType Junction -Path "'+str(dest)+'" -Target "'+str(source)+'" | Out-Null'], check=True)
            return
        dest.mkdir()
        for child in source.iterdir():
            if child.is_dir(): content(child, dest/child.name, rel+'/'+child.name)
            else: shutil.copy2(child, dest/child.name)
    content(MAIN/'Content', WORK/'Content', 'Content')
    # Inherit existing editor quality, without writing any main user settings.
    saved = MAIN/'Saved/Config/WindowsEditor'
    if saved.exists(): shutil.copytree(saved, WORK/'Saved/Config/WindowsEditor')
    write(OUT/'Baseline.json', {'main':str(MAIN),'work':str(WORK),'files':baseline,
        'native_manifest':json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text()),
        'native_sha':sha(MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll'),
        'source_config':{p.relative_to(MAIN).as_posix():sha(p) for d in ['Source','Config'] for p in (MAIN/d).rglob('*') if p.is_file()},
        'utc':datetime.now(timezone.utc).isoformat()})
    print('STAGED_MAPS',len(baseline),flush=True)

def writable(rel):
    """Expand only workspace junctions on the path; never remove target contents."""
    assert rel.startswith('Content/') and '..' not in Path(rel).parts
    cursor=WORK
    for part in Path(rel).parts:
        cursor=cursor/part
        assert cursor.absolute().is_relative_to(WORK.absolute())
        if cursor.exists() and (cursor.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            target=cursor.resolve()
            assert target.is_relative_to(MAIN/'Content'), target
            entries=list(target.iterdir())
            os.rmdir(cursor)  # removes only the junction itself, never recursively
            cursor.mkdir()
            for child in entries:
                dest=cursor/child.name
                if child.is_dir():
                    subprocess.run(['powershell','-NoProfile','-Command','New-Item -ItemType Junction -Path "'+str(dest)+'" -Target "'+str(child)+'" | Out-Null'],check=True)
                else:shutil.copy2(child,dest)
        elif not cursor.exists():cursor.mkdir()

def stage_masks():
    rows=json.loads((OUT/'HeinAuthor01/Authoring.json').read_text())['masked_usd']
    parents={}
    for row in rows:
        rel='Content/'+row['material'].split('.')[0].removeprefix('/Game/')+'.uasset'
        parents[str(Path(rel).parent).replace('\\','/')]=True
        dst=OUT/'Before'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():shutil.copy2(MAIN/rel,dst)
    for rel in parents:writable(rel)
    writable('Content/_Art/Player/Environment/Rendering/SceneLook')
    write(OUT/'MaskBaseline.json',{'files':{p.relative_to(OUT/'Before').as_posix():sha(p) for p in (OUT/'Before/Content').rglob('*.uasset')},'targets':rows})
    print('STAGED_MASK_TARGETS',len(rows),flush=True)

def run(mode, name, level, entry='Scripts/Art/scene_look_capture_20261012.py'):
    directory=OUT/name;directory.mkdir(exist_ok=False)
    project=MAIN if mode.startswith('main_') else WORK
    mode=mode.removeprefix('main_')
    commandlet=mode=='author'
    cmd=[str(ENGINE/'Binaries/Win64'/('UnrealEditor-Cmd.exe' if commandlet else 'UnrealEditor.exe')),
        str(project/'Khazan.uproject'), '-unattended','-nosplash','-nosound','-NoSourceControl',
        '-NoLiveCoding','-NoAutoSave','-EnablePlugins=GameFeatures,CascadeToNiagaraConverter',
        '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-abslog='+str(directory/'Editor.log')]
    if commandlet: cmd+=['-NullRHI','-run=pythonscript','-script='+str(MAIN/entry)]
    else: cmd+=['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-ExecCmds=py '+str(MAIN/entry)]
    env=dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1',PYTHONUTF8='1', KZ_LOOK_OUT=str(directory),
        KZ_LOOK_MAIN=str(MAIN),KZ_LOOK_LEVEL=level,KZ_LOOK_MODE=mode)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    started=time.monotonic()
    with (directory/'stdout.txt').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
        write(directory/'Launch.json',{'pid':proc.pid,'args':cmd,'project':str(project),'utc':datetime.now(timezone.utc).isoformat(),
            'maps':{rel:sha(project/rel) for rel in MAP_FILES},'native_sha':sha(project/'Binaries/Win64/UnrealEditor-Khazan.dll')})
        print('OWNED_LOOK_PROCESS',proc.pid,flush=True)
        try: code=proc.wait(timeout=900)
        except subprocess.TimeoutExpired: proc.terminate();code=proc.wait(timeout=30)
    write(directory/'Exit.json',{'pid':proc.pid,'exit':code,'seconds':time.monotonic()-started})
    print('OWNED_LOOK_EXIT',code,flush=True)
    return code

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    if sys.argv[1]=='stage':stage()
    elif sys.argv[1]=='stage_masks':stage_masks()
    else:sys.exit(run(*sys.argv[1:]))
