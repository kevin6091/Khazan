"""Task-owned snow workspace. Shared Content branches and Plugins are read only."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT = ROOT / 'Saved/ImportReports/HeinMachSnow_20261006'
EXTRACT = ROOT / 'Saved/Extracted/HeinMachSnow_20261006'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
PYTHON = ENGINE / 'Binaries/ThirdParty/Python3/Win64/python.exe'
MUTABLE = ('Maps', '_Art/Player/Environment/Rendering')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def junction(source, destination):
    if destination.exists():
        return
    command = "New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null" % (
        str(destination).replace("'", "''"), str(source).replace("'", "''"))
    subprocess.run(['powershell', '-NoProfile', '-Command', command], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)

def content_tree(source, destination, relative=''):
    mutable = not relative or any(relative == m or m.startswith(relative + '/') or
        relative.startswith(m + '/') for m in MUTABLE)
    if not mutable:
        junction(source, destination)
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            content_tree(item, target, (relative + '/' + item.name).lstrip('/'))
        else:
            shutil.copy2(item, target)

def setup():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'StageSetup.json').exists():
        print('Existing snow stage preserved')
        return
    STAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'Khazan.uproject', STAGE / 'Khazan.uproject')
    for name in ('Source', 'Config', 'Binaries', 'Plugins', 'Scripts/Art', 'Scripts/Engineering'):
        shutil.copytree(ROOT / name, STAGE / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.pdb', '__pycache__', 'Intermediate'))
    content_tree(ROOT / 'Content', STAGE / 'Content')
    baseline = []
    for branch in MUTABLE + ('Source', 'Config'):
        base = ROOT / branch if branch in ('Source', 'Config') else ROOT / 'Content' / branch
        for path in base.rglob('*'):
            if path.is_file():
                rel = path.relative_to(ROOT)
                baseline.append({'path':rel.as_posix(), 'sha256':sha(path)})
    (OUT / 'StageSetup.json').write_text(json.dumps({'stage':str(STAGE),
        'mutable_content':MUTABLE, 'baseline':baseline}, indent=2), encoding='utf-8')
    print(json.dumps({'stage':str(STAGE), 'baseline_files':len(baseline)}), flush=True)

def requests():
    EXTRACT.mkdir(parents=True, exist_ok=True)
    index = json.loads((EXTRACT / 'Index/TargetedPackageIndex.json').read_text(encoding='utf-8-sig'))
    paths = [p.removesuffix('.uasset') for p in index if '/BaseMaterials/VT_SnowField/' in p]
    paths += ['BBQ/Content/_Common/Constants/FoliageInteractionConstants',
      'BBQ/Content/_Kazan_/Art/Terrain/Terrain_Material/Landscape_Material/WLM_HeinMach',
      'BBQ/Content/_Kazan_/Art/Terrain/Terrain_Material/Landscape_Material/WLM_HeinMach2',
      'BBQ/Content/_Kazan_/Art/Terrain/Terrain_Data/LandscapeInfo/HeinMach/WLI_HeinMach_DeepSnow',
      'BBQ/Content/_Kazan_/Art/Terrain/Terrain_Data/LandscapeInfo/HeinMach/WLI_HeinMach_DeepSnow2',
      'BBQ/Content/_Kazan_/Art/VFX/VFX_Data/DeepSnowMesh']
    (EXTRACT / 'RootRequests.json').write_text(json.dumps(sorted(set(paths)),indent=2),encoding='utf-8')
    print(json.dumps({'requests':len(set(paths))}),flush=True)

def run(kind):
    script = STAGE / 'Scripts/Art' / ('heinmach_snow_' + kind + '.py')
    shutil.copy2(ROOT / 'Scripts/Art' / script.name, script)
    log = OUT / (kind + '.log')
    if log.exists():
        shutil.copy2(log,OUT/(kind+'_'+time.strftime('%H%M%S')+'.log'))
    null_rhi = kind in ('probe','ground_probe')
    executable = ENGINE / ('Binaries/Win64/UnrealEditor-Cmd.exe' if null_rhi else 'Binaries/Win64/UnrealEditor.exe')
    args = [str(executable), str(STAGE / 'Khazan.uproject'), '/Engine/Maps/Entry', '-unattended', '-nosound',
      '-nosplash', '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
      '-EnablePlugins=GameFeatures', '-abslog='+str(log)]
    if kind=='verify':
        args += ['-ini:Engine:[/Script/Engine.AutomationTestSettings]:DefaultInteractiveFramerate=1.0',
                 '-ini:Engine:[/Script/Engine.AutomationTestSettings]:DefaultInteractiveFramerateDuration=1.0']
    if null_rhi:
        args += ['-nullrhi', '-run=pythonscript', '-script='+str(script)]
    else:
        args += ['-RenderOffscreen', '-windowed', '-ResX=1280', '-ResY=720', '-ExecCmds=py '+str(script)]
    env = dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1', PYTHONUTF8='1')
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow=0
    started=time.monotonic()
    process=subprocess.Popen(args,env=env,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps({'pid':process.pid,'phase':kind,'log':str(log)}),flush=True)
    process.wait()
    print(json.dumps({'exit_code':process.returncode,'seconds':time.monotonic()-started}),flush=True)

if __name__ == '__main__':
    {'setup':setup,'requests':requests}.get(sys.argv[1],lambda:run(sys.argv[1]))()
