"""Build/cook/stage the current main project into one Windows release directory."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(os.environ.get('KZ_RELEASE_TASK', str(ROOT / 'Metadata/Release_20261015')))
RUN = TASK / (sys.argv[1] if len(sys.argv) > 1 else 'Package01')
RUN.mkdir(parents=True, exist_ok=False)
DEST = Path(os.environ.get('KZ_RELEASE_DEST', 'C:/Users/user/Desktop/Khazan_Release_20261015'))
UAT = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/RunUAT.bat')
args = [str(UAT), 'BuildCookRun', '-project=' + str(ROOT / 'Khazan.uproject'),
        '-target=Khazan', '-platform=Win64', '-clientconfig=Shipping',
        '-build', '-cook', '-stage', '-pak', '-iostore', '-compressed', '-package',
        '-prereqs', '-distribution', '-nodebuginfo', '-utf8output', '-unattended',
        '-nop4', '-nocompileeditor', '-stagingdirectory=' + str(DEST),
        '-map=/Game/Maps/L_HeinMach_Environment',
        '-UbtArgs=-NoXGE -MaxParallelActions=4',
        '-AdditionalCookerOptions=-NoLiveCoding -NoSourceControl -DisablePlugins=RiderLink,ModelContextProtocol,XGEController']
if '--skipbuild' in sys.argv:
    args.remove('-build')
    args.append('-skipbuild')
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
begin = datetime.datetime.now(datetime.timezone.utc)
with (RUN / 'UAT.log').open('w', encoding='utf-8') as stream:
    proc = subprocess.Popen(args, cwd=str(ROOT), stdout=stream, stderr=subprocess.STDOUT,
                            startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (RUN / 'Launch.json').write_text(json.dumps(dict(pid=proc.pid, args=args,
        utc=begin.isoformat(), destination=str(DEST)), indent=2), encoding='utf-8')
    code = proc.wait()
(RUN / 'Exit.json').write_text(json.dumps(dict(pid=proc.pid, exit_code=code,
    seconds=(datetime.datetime.now(datetime.timezone.utc)-begin).total_seconds()), indent=2), encoding='utf-8')
print(json.dumps(dict(run=str(RUN), exit_code=code, output=str(DEST))), flush=True)
raise SystemExit(code)
