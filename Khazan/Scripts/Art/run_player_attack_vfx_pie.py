"""Launch a private hidden RHI editor, leaving all other editors untouched."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
VERIFY_MAIN = '--main' in sys.argv[1:]
WORK = ROOT if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008' / ('MainRuntimePIE' if VERIFY_MAIN else 'RuntimePIE')
OUT.mkdir(parents=True, exist_ok=True)
args = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',
        str(WORK / 'Khazan.uproject'), '/Game/Maps/DevMap', '-skipcompile', '-NoSplash', '-NoSound',
        '-Unattended', '-RenderOffscreen', '-NoLiveCoding', '-NoSourceControl',
        '-EnablePlugins=GameFeatures', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
        '-abslog=' + str(OUT / 'PrivatePIE.log'),
        '-ExecCmds=py ' + str(ROOT / 'Scripts/Art/player_attack_vfx_pie.py')]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
env['KZ_ATTACK_VFX_VERIFY_MAIN'] = '1' if VERIFY_MAIN else '0'
started = time.monotonic()
with (OUT / 'PrivatePIE.stdout.txt').open('w', encoding='utf-8') as stream:
    process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, env=env,
                               startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': args}, indent=2), encoding='utf-8')
    rc = process.wait()
(OUT / 'Exit.json').write_text(json.dumps({'pid': process.pid, 'exit_code': rc,
                                         'elapsed_seconds': time.monotonic() - started}, indent=2), encoding='utf-8')
print(json.dumps({'exit_code': rc, 'elapsed_seconds': time.monotonic() - started}), flush=True)
raise SystemExit(rc)
