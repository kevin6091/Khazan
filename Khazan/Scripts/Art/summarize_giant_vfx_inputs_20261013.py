"""Compact reusable summary of cached original events and actual particle modules."""
from pathlib import Path
from collections import Counter
import json, re

main = Path(__file__).resolve().parents[2];out=main/'Metadata/GiantVFX_20261013'
original=json.loads((main/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
skipped=[e for e in original['skipped_source_windows'] if e.get('source',{}).get('family') in {'Yetuga','ApesStoneHandElite'}]
(out/'SkippedOriginalEvents.json').write_text(json.dumps(skipped,ensure_ascii=False,indent=2),encoding='utf-8')
print('Skipped types:',Counter(e.get('notify_type') for e in skipped))
if skipped:
    e=next((e for e in skipped if 'DeepSnow' in str(e.get('notify_type'))),skipped[0])
    print(json.dumps({k:e.get(k) for k in ['asset','notify_type','start_time','end_time','reason']},ensure_ascii=False))
    print('Properties:',json.dumps(e.get('source',{}).get('properties',{}),ensure_ascii=False))
summary=[]
for file in sorted((out/'ParticleExports01/Exports').glob('*.t3d')):
    data=file.read_bytes();text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    row={'file':file.name,'classes':dict(Counter(re.findall(r'Begin Object Class=/Script/Engine\.([^\s]+)',text))),
         'materials':sorted(set(re.findall(r'Material(?:s\(\d+\))?=.*?\'(/Game/[^\']+)',text))),
         'mesh_refs':sorted(set(re.findall(r'(?:Mesh|StaticMesh)=.*?\'(/Game/[^\']+)',text))),
         'constants':re.findall(r'^\s*(?:Constant|Min|Max|StartSize|StartVelocity|Rate|BurstList\(\d+\)|EmitterDuration|EmitterLoops|bUseLocalSpace)=.*',text,re.M)}
    summary.append(row)
(out/'ParticleModuleSummary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for row in summary:
    if any(k in row['file'] for k in ['Mouth','Smash_normal','FastBall','Foot','IceBreath','Rock_']):
        print(row['file'],row['classes'].get('ParticleModuleRequired',0),'emitters',row['mesh_refs'])
