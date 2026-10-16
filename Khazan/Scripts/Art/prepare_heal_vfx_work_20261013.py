"""Fresh recovery-only work tree. All borrowed Content is read-only."""
from pathlib import Path
import hashlib, json, shutil, subprocess
from datetime import datetime

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_HealVFXWork_20261013/Khazan'
OUT = MAIN / 'Metadata/HealVFX_20261013'
assert not WORK.exists()
WORK.mkdir(parents=True)
for folder in ('Source', 'Config', 'Binaries', 'Plugins'):
    shutil.copytree(MAIN/folder, WORK/folder,
                    ignore=shutil.ignore_patterns('Intermediate', 'Saved', '.git'))
shutil.copy2(MAIN/'Khazan.uproject', WORK/'Khazan.uproject')
PRIVATE = {'Content/_Art/Player/Animation/InGame/DAS/Heal'}

def stage(src, dst):
    rel = src.relative_to(MAIN).as_posix()
    if rel in PRIVATE:
        shutil.copytree(src, dst)
    elif any(p.startswith(rel+'/') for p in PRIVATE):
        dst.mkdir()
        for p in src.iterdir(): stage(p, dst/p.name)
    elif src.is_dir():
        # One PowerShell process, literal paths, no cross-shell file operations.
        command = "New-Item -ItemType Junction -Path '" + str(dst).replace("'", "''") + "' -Target '" + str(src).replace("'", "''") + "' | Out-Null"
        subprocess.run(['powershell', '-NoProfile', '-Command', command], check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        shutil.copy2(src, dst)

stage(MAIN/'Content', WORK/'Content')
# A separate physical root for newly authored effects; never save a borrowed path.
(WORK/'Content/HealVFX').mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = dict(date=datetime.now().astimezone().isoformat(), main=str(MAIN), work=str(WORK),
                source={p.relative_to(MAIN).as_posix(): sha(p) for p in (MAIN/'Source').rglob('*') if p.is_file()},
                config={p.relative_to(MAIN).as_posix(): sha(p) for p in (MAIN/'Config').rglob('*') if p.is_file()},
                assets={p.relative_to(MAIN).as_posix(): sha(p) for folder in PRIVATE for p in (MAIN/folder).rglob('*') if p.is_file()})
(OUT/'Baseline.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
print('Prepared recovery workspace', WORK, flush=True)
