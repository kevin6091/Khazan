from pathlib import Path
from collections import Counter
import json

root = Path(__file__).resolve().parents[2]
task = root / 'Saved/Extracted/GameplayAudio_20261011'
rows = json.loads((task / 'Index03/AudioPackageIndex.json').read_text(encoding='utf-8'))
groups = Counter((r['archive'], Path(r['path']).suffix) for r in rows)
packages = [r for r in rows if r['path'].endswith('.uasset')]
folders = Counter('/'.join(r['path'].split('/')[:6]) for r in packages)
report = {'files': len(rows), 'packages': len(packages),
          'archive_filetypes': [{'archive': k[0], 'extension': k[1], 'count': v} for k, v in sorted(groups.items())],
          'folders': dict(folders.most_common()), 'examples': {}}
for category, terms in {'player': ['/Sound/Player/'], 'monster': ['/Sound/Monster/', '/Sound/Enemy/'],
                       'heinmach': ['HeinMach', 'Heinmac', '/Sound/Amb', '/Sound/Env'],
                       'bank': ['Init', 'SoundBank', 'Soundbanks'], 'media': ['/Media/']}.items():
    selected = [r['path'] for r in packages if any(t.lower() in r['path'].lower() for t in terms)]
    report['examples'][category] = {'count': len(selected), 'first': selected[:12]}
samples = ['BBQ/Content/_Kazan_/Sound/Player/Player_Common/Player_VO/Play_PLYR_VO_Dmg']
for category in ['player', 'monster', 'heinmach', 'bank', 'media']:
    samples += [p.removesuffix('.uasset') for p in report['examples'][category]['first'][:3]]
samples = list(dict.fromkeys(samples))
(task / 'SampleRequests.json').write_text(json.dumps(samples, indent=2), encoding='utf-8')
(task / 'InventorySummary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Audio files', len(rows), 'packages', len(packages))
print(json.dumps(report['archive_filetypes'], indent=2))
for name, data in report['examples'].items():
    print(name, data['count'], json.dumps(data['first'][:3]))
print('Top folders', json.dumps(folders.most_common(9)))
