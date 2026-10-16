"""Root launch only: own hidden real-RHI Yetuga QA; no product edits."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

MAIN = Path(__file__).resolve().parents[2]
VERIFY_MAIN = '--main' in sys.argv[1:]
DIAGNOSTIC_LATE_RECOVERY = '--diagnostic-late' in sys.argv[1:]
DIAGNOSTIC = '--diagnostic' in sys.argv[1:] or DIAGNOSTIC_LATE_RECOVERY
WORK = MAIN if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
PARENT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008' / ('MainYetugaQA' if VERIFY_MAIN else 'PrivateYetugaQA')
if DIAGNOSTIC:
    # Preserve the default regular supplemental Latest.json/evidence contract.
    PARENT = PARENT / 'Diagnostics'
PARENT.mkdir(parents=True, exist_ok=True)
attempt = 1
while (PARENT / ('Attempt' + str(attempt))).exists():
    attempt += 1
OUT = PARENT / ('Attempt' + str(attempt))
OUT.mkdir()
ARGS = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe', str(WORK / 'Khazan.uproject'),
    '/Game/Maps/DevMap', '-skipcompile', '-NoSplash', '-NoSound', '-Unattended', '-RenderOffscreen',
    '-NoLiveCoding', '-NoSourceControl', '-NoAutoSave', '-EnablePlugins=GameFeatures',
    '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT / 'PrivatePIE.log'),
    '-ExecCmds=py ' + str(MAIN / 'Scripts/Art/monster_vfx_yetuga_pie_20261010.py')]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
env['KZ_MONSTER_VFX_YETUGA_REPORT'] = str(OUT)
env['KZ_MONSTER_VFX_YETUGA_VERIFY_MAIN'] = '1' if VERIFY_MAIN else '0'
env['KZ_MONSTER_VFX_YETUGA_DIAGNOSTIC'] = '1' if DIAGNOSTIC else '0'
env['KZ_MONSTER_VFX_YETUGA_DIAGNOSTIC_LATE_RECOVERY'] = '1' if DIAGNOSTIC_LATE_RECOVERY else '0'
start = time.monotonic()
with (OUT / 'PrivatePIE.stdout.txt').open('w', encoding='utf-8') as stream:
    process = subprocess.Popen(ARGS, stdout=stream, stderr=subprocess.STDOUT, env=env, startupinfo=startup,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': ARGS,
        'test': 'TargetedYetugaDiagnosticIsolation' if DIAGNOSTIC else 'TargetedYetugaActualPlayback',
        'diagnostic_mode': DIAGNOSTIC,
        'diagnostic_late_recovery': DIAGNOSTIC_LATE_RECOVERY}, indent=2), encoding='utf-8')
    code = process.wait()
result = {'pid': process.pid, 'exit_code': code, 'elapsed_seconds': time.monotonic()-start}
(OUT / 'Exit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
(PARENT / 'Latest.json').write_text(json.dumps({'attempt': str(OUT), 'exit_code': code}, indent=2), encoding='utf-8')
print(json.dumps(result), flush=True)
raise SystemExit(code)
