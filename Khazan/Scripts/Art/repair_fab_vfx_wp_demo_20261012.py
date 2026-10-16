"""Use the dedicated UE World Partition builder in staging, preserving all demo actors."""
from pathlib import Path
import json
import os
import runpy
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']
receipt = json.loads((META / 'PublishReceipt.json').read_text())
for row in receipt['files']:
    target = STAGE / 'Content' / row['relative_path']
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(row['target'], target)
    if row['relative_path'] != 'VFX/05_CursedMagic/Demo/Cursed_Magic.umap' and not row['relative_path'].startswith(('__ExternalActors__/VFX/05_CursedMagic/Demo/Cursed_Magic/', '__ExternalObjects__/VFX/05_CursedMagic/Demo/Cursed_Magic/')):
        assert SHA(target) == row['sha256'], target
old_map = STAGE / 'Content/Cursed_Magic/Maps/Cursed_Magic.umap'
backup_map = META / 'Before/Content/Cursed_Magic/Maps/Cursed_Magic.umap'
assert SHA(backup_map) == next(r['sha256'] for r in json.loads((META / 'InputManifest.json').read_text()) if r['relative_path'] == 'Cursed_Magic/Maps/Cursed_Magic.umap')
shutil.copy2(backup_map, old_map)
for extra in ('__ExternalActors__', '__ExternalObjects__'):
    original = META / 'Before/Content' / extra / 'Cursed_Magic'
    for file in original.rglob('*.uasset'):
        target = STAGE / 'Content' / file.relative_to(META / 'Before/Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
number = len(list(META.glob('WPBuilder[0-9][0-9]'))) + 1
OUT = META / ('WPBuilder%02d' % number)
OUT.mkdir(parents=True, exist_ok=True)
args = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe', str(STAGE / 'FabVFXComplete.uproject'), '/Game/Cursed_Magic/Maps/Cursed_Magic', '-run=WorldPartitionBuilderCommandlet', '-SCCProvider=None', '-builder=WorldPartitionRenameDuplicateBuilder', '-NewPackage=/Game/VFX/05_CursedMagic/Demo/Cursed_Magic', '-unattended', '-nosound', '-nosplash', '-NoSourceControl', '-NoAutoSave', '-NoLiveCoding', '-NullRHI', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT / 'Editor.log')]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
start = time.monotonic()
with (OUT / 'stdout.txt').open('w', encoding='utf-8') as output:
    process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': args}, indent=2), encoding='utf-8')
    print('VFX_WP_BUILDER_START ' + str(process.pid), flush=True)
    code = process.wait()
(OUT / 'Exit.json').write_text(json.dumps({'exit_code': code, 'elapsed_seconds': time.monotonic()-start}, indent=2), encoding='utf-8')
print('VFX_WP_BUILDER_EXIT ' + str(code), flush=True)
raise SystemExit(code)
