"""Read the built containers and observe a task-owned Shipping startup."""
from pathlib import Path
import csv
import datetime
import hashlib
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RELEASE = Path(json.loads((OUT/'Baseline.json').read_text(encoding='utf-8'))['release']) / 'Windows'
PAKS = RELEASE / 'Khazan/Content/Paks'
UNREALPAK = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealPak.exe')
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE

def run(args, log):
    with (OUT / log).open('wb') as stream:
        result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, startupinfo=startup,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, (log, result.returncode)

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

run([str(UNREALPAK), 'IoStore', '-List=' + str(PAKS / 'Khazan-Windows.utoc'),
     '-CSV=' + str(OUT / 'IoStoreContents.csv')], 'IoStoreList.log')
run([str(UNREALPAK), str(PAKS / 'Khazan-Windows.pak'), '-Extract',
     str(OUT / 'PackagedConfig'), '-Filter=*.ini'], 'PakConfigExtract.log')
with (OUT / 'IoStoreContents.csv').open(encoding='utf-8-sig', newline='') as stream:
    rows = [{k.strip(): v.strip() for k, v in r.items()} for r in csv.DictReader(stream, skipinitialspace=True)]
maps = sorted(set(r['Filename'] for r in rows if r['Filename'].lower().endswith('.umap')))
game_maps = [p for p in maps if '/Khazan/Content/' in p]
assert game_maps == ['../../../Khazan/Content/Maps/L_HeinMach_Environment.umap'], game_maps
baseline = json.loads((OUT / 'Baseline.json').read_text(encoding='utf-8'))
input_changes = [name for name, value in baseline['input_sha'].items() if not (ROOT / name).is_file() or sha(ROOT / name) != value]
assert not input_changes, input_changes
music = sorted(set(r['Filename'] for r in rows if '/Audio/Original/Music/Yetuga/' in r['Filename'] and r['Filename'].endswith('.uasset')))
assert len(music) == 4, music
map_rows = [r for r in rows if r['Filename'] in game_maps]
(OUT/'CookedMapRows.json').write_text(json.dumps(map_rows,indent=2),encoding='utf-8')
assert map_rows
previous_path = ROOT / 'Metadata/LockOnRumble_20261015/IoStoreContents.csv'
with previous_path.open(encoding='utf-8-sig',newline='') as previous_stream:
    old_rows = [{k.strip():v.strip() for k,v in r.items()} for r in csv.DictReader(previous_stream,skipinitialspace=True)]
old_map = [r for r in old_rows if r['Filename'] in game_maps]
assert {r['Hash'] for r in map_rows} != {r['Hash'] for r in old_map}, 'Old map chunk must not be reused after pruning'
assert sum(int(r['Size']) for r in map_rows) < sum(int(r['Size']) for r in old_map), 'Expected cooked map reduction'

config = OUT / 'PackagedConfig/Khazan/Config'
game_ini = (config / 'DefaultGame.ini').read_text(encoding='utf-8-sig')
engine_ini = (config / 'DefaultEngine.ini').read_text(encoding='utf-8-sig')
assert 'ForceFeedbackScale=2.0' in game_ini
assert 'GameDefaultMap=/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment' in engine_ini
quality = dict(line.strip().split('=', 1) for line in
               (config / 'DefaultGameUserSettings.ini').read_text(encoding='utf-8-sig').splitlines()
               if line.strip().startswith('sg.') and '=' in line)
assert quality.get('sg.ResolutionQuality') == '100.000000'
assert len(quality) == 12 and all(v == '3' for k, v in quality.items() if k != 'sg.ResolutionQuality'), quality
binary = RELEASE / 'Khazan/Binaries/Win64/Khazan-Win64-Shipping.exe'
assert sha(binary) == sha(ROOT / 'Binaries/Win64/Khazan-Win64-Shipping.exe')
assert (RELEASE / 'Khazan.exe').is_file()
assert (RELEASE / 'Engine/Extras/Redist/en-us/vc_redist.x64.exe').is_file()
manifest = [dict(path=p.relative_to(RELEASE).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(RELEASE.rglob('*')) if p.is_file()]
(OUT / 'ReleaseFiles.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
receipt = dict(maps=maps, game_maps=game_maps, force_feedback_scale=2.0, source_map_sha=baseline['map_sha'], input_changes=input_changes, yetuga_music=music, cooked_map_bytes=sum(int(r['Size']) for r in map_rows), previous_cooked_map_bytes=sum(int(r['Size']) for r in old_map),
               quality=quality,
               shipping_binary_sha256=sha(binary), file_count=len(manifest),
               size_bytes=sum(p['bytes'] for p in manifest))
(OUT / 'PackageReadback.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('Container/config/binary verification passed', flush=True)

smoke = OUT / 'Smoke01'
smoke.mkdir(exist_ok=False)
args = [str(binary), '-RenderOffscreen', '-unattended', '-NoSplash', '-nosound', '-windowed',
        '-ResX=1280', '-ResY=720', '-UserDir=' + str(smoke / 'UserData')]
begin = time.monotonic()
proc = subprocess.Popen(args, cwd=binary.parent, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
(smoke / 'Launch.json').write_text(json.dumps(dict(pid=proc.pid, args=args,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()), indent=2), encoding='utf-8')
print('Shipping smoke PID', proc.pid, flush=True)
try:
    while time.monotonic() - begin < 90:
        assert proc.poll() is None, ('Shipping exited during startup', proc.returncode)
        time.sleep(1)
    crashes = [str(p) for p in smoke.rglob('*') if p.is_file() and
               (p.suffix.lower() == '.dmp' or 'CrashContext' in p.name)]
    assert not crashes, crashes
    (smoke / 'Result.json').write_text(json.dumps(dict(status='StartupObserved', pid=proc.pid,
        seconds=time.monotonic() - begin, crashes=crashes, sound=False,
        scope='Offscreen process survival only; no combat, visual/FPS or physical controller validation.'), indent=2), encoding='utf-8')
finally:
    if proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=30)
print('Shipping startup observation passed; task-owned process stopped', flush=True)
