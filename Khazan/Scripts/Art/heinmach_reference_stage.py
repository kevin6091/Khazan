"""Isolated HeinMach art workspace; shared assets are read-only directory junctions."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'Saved/ArtStaging/HeinMachReference_20261006'
OUT = ROOT / 'Saved/ImportReports/HeinMachReference_20261006'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
MUTABLE = ('Maps', '_Art/Player/Environment/Rendering',
           '_Art/Player/Environment/HeinMach/Reconstructed/Materials',
           '_Art/Player/Environment/HeinMach/Reconstructed/OverrideMaterials',
           '_Art/Player/Environment/HeinMach/Reconstructed/RecoveredMaterials',
           '_Art/Player/Environment/HeinMach/Reconstructed/TerrainPreview')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def junction(source, destination):
    # Native PowerShell only; paths are explicit literals, never passed to cmd.
    if destination.exists():
        return
    command = "New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null" % (
        str(destination).replace("'", "''"), str(source).replace("'", "''"))
    subprocess.run(['powershell', '-NoProfile', '-Command', command], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def content_tree(source, destination, relative=''):
    mutable = any(relative == m or m.startswith(relative + '/') or relative.startswith(m + '/')
                  for m in MUTABLE) or not relative
    if not mutable:
        junction(source, destination)
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        child = (relative + '/' + item.name).lstrip('/')
        target = destination / item.name
        if item.is_dir():
            content_tree(item, target, child)
        elif not target.exists():
            shutil.copy2(item, target)


def setup():
    assert STAGE.is_relative_to(ROOT / 'Saved/ArtStaging')
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'StageSetup.json').exists():
        print('Existing stage preserved:', STAGE)
        return
    STAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'Khazan.uproject', STAGE / 'Khazan.uproject')
    for name in ('Config', 'Binaries', 'Scripts/Art', 'Scripts/StormPass'):
        shutil.copytree(ROOT / name, STAGE / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.pdb', '__pycache__'))
    for name in ('Plugins', 'Source'):
        junction(ROOT / name, STAGE / name)
    content_tree(ROOT / 'Content', STAGE / 'Content')
    extracted = STAGE / 'Saved/Extracted'
    extracted.mkdir(parents=True, exist_ok=True)
    for name in ('HeinMachWeather_20261006', 'LookRestoration_20261002'):
        if (ROOT / 'Saved/Extracted' / name).exists():
            shutil.copytree(ROOT / 'Saved/Extracted' / name, extracted / name, dirs_exist_ok=True)
    copied = []
    for branch in MUTABLE:
        for path in (ROOT / 'Content' / branch).rglob('*'):
            if path.is_file() and path.suffix in ('.uasset', '.umap'):
                rel = path.relative_to(ROOT)
                assert sha(path) == sha(STAGE / rel)
                copied.append({'path': str(rel), 'sha256': sha(path)})
    (OUT / 'StageSetup.json').write_text(json.dumps({
        'stage': str(STAGE), 'main_assets_untouched': True,
        'mutable_branches_copied': MUTABLE, 'baseline_packages': copied,
        'baseline_map_sha256': sha(ROOT / 'Content/Maps/L_HeinMach_Environment.umap')}, indent=2)+'\n')
    print(json.dumps({'stage': str(STAGE), 'copied_packages': len(copied)}))


def run(kind):
    main_project='-HMReferenceMain' in sys.argv
    if main_project:
        assert kind in ('capture','audit'),'Main verification is read-only'
        assert json.loads((OUT/'InstallManifest.json').read_text())['status']=='Applied'
    project=ROOT if main_project else STAGE
    render = kind in ('capture', 'compile', 'motion', 'performance')
    game = kind in ('capture','motion','performance')
    if not main_project:
        shutil.copytree(ROOT / 'Scripts/Art', STAGE / 'Scripts/Art', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
    script = project / 'Scripts/Art' / ('heinmach_reference_' + kind + '.py')
    assert script.is_file(), script
    label='particle_readback' if '-HMReferenceParticleReadback' in sys.argv else kind
    prefix=('main_' if main_project else '')+label
    log = OUT / (prefix + '.log')
    args = [str(ENGINE / ('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')),
            str(project / 'Khazan.uproject'), '-unattended', '-nosound', '-nosplash',
            '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol',
            '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter', '-abslog=' + str(log)]
    if render:
        args += ['/Game/Maps/L_HeinMach_Environment', '-RenderOffscreen', '-windowed',
                 '-ResX=1280', '-ResY=720', '-ExecCmds=py ' + str(script)]
        if game:
            args += ['-game', '-EnablePlugins=GameFeatures,PythonScriptPlugin']
    else:
        args += ['-nullrhi', '-run=pythonscript', '-script=' + str(script)]
    args += [argument for argument in sys.argv[2:] if argument.startswith('-HM')]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    started = time.monotonic()
    with log.with_suffix('.stdout.txt').open('w', encoding='utf-8') as stdout:
        process = subprocess.run(args, stdout=stdout, stderr=subprocess.STDOUT,
                                 startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    marker = 'KZ_HEINMACH_REFERENCE_' + kind.upper() + '_PASSED'
    passed = process.returncode == 0 and marker in log.read_text(encoding='utf-8', errors='replace')
    log_text=log.read_text(encoding='utf-8',errors='replace')
    if render and 'Default Material will be used in game' in log_text:
        passed=False
    report = {'stage': kind, 'project':str(project), 'passed': passed, 'exit_code': process.returncode,
              'elapsed_seconds': time.monotonic()-started, 'isolated_background': True, 'log': str(log)}
    (OUT / (prefix+'Process.json')).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    setup() if sys.argv[1] == 'setup' else run(sys.argv[1])
