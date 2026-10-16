"""Fresh two-family workspace; preserve current Main and shared alpha/physics work."""
from pathlib import Path
import json, hashlib, shutil, subprocess
from datetime import datetime

main = Path(__file__).resolve().parents[2]
out = main/'Metadata/GiantVFX_20261013'
work = main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
assert not work.exists() and not out.exists()
out.mkdir(); work.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for directory in ['Source', 'Config', 'Binaries']:
    shutil.copytree(main/directory, work/directory)
shutil.copy2(main/'Khazan.uproject', work/'Khazan.uproject')
owned = {'Content/Monsters/Yetuga', 'Content/Monsters/ApesStoneHandElite',
         'Content/_Art/Effects/Monsters/ApesYetuga',
         'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations',
         'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations'}
def stage(source, dest):
    relative = source.relative_to(main).as_posix()
    if relative in owned:
        shutil.copytree(source, dest)
    elif any(p.startswith(relative+'/') for p in owned):
        dest.mkdir()
        for child in source.iterdir():
            if child.is_dir(): stage(child, dest/child.name)
            else: shutil.copy2(child, dest/child.name)
    elif source.is_dir():
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(dest), str(source)], capture_output=True)
        assert result.returncode == 0, result.stderr
    else:
        shutil.copy2(source, dest)
stage(main/'Content', work/'Content')
shutil.copytree(main/'Plugins', work/'Plugins', ignore=shutil.ignore_patterns('Intermediate','Saved','.git'))
baseline = {'date': datetime.now().astimezone().isoformat(), 'main': str(main), 'work': str(work),
    'owned_folders': sorted(owned), 'main_writes': 0,
    'source_sha256': {p.relative_to(main).as_posix(): sha(p) for p in (main/'Source').rglob('*') if p.is_file()},
    'assets': {p.relative_to(main).as_posix(): sha(p) for folder in owned for p in (main/folder).rglob('*') if p.is_file()}}
(out/'Baseline.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
plan = json.loads((main/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
families = {'Yetuga', 'ApesStoneHandElite', 'YetugaRock'}
events = [e for e in plan['events'] if e.get('family') in families]
filtered = {'clips': [c for c in plan['clips'] if c.get('Family') in families], 'events': events,
            'skipped': [e for e in plan.get('skipped_source_windows', []) if e.get('family') in families],
            'unsupported': [e for e in plan.get('unsupported_source_windows', []) if e.get('family') in families]}
(out/'ExistingOriginalPlan.json').write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding='utf-8')
print('Prepared current Main snapshot:', work, 'owned assets:', len(baseline['assets']), 'original events:', len(events))
print('Event keys:', list(events[0]) if events else [])
