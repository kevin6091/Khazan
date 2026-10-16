"""Human-readable source-backed timing export; not a runtime verification receipt."""
from pathlib import Path
import csv
import json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008'
plan = json.loads((OUT / 'PreparedPlaybackPlan.json').read_text(encoding='utf-8'))
rows = []
for event in plan['events']:
    fields = event['notify_fields']
    routes = fields.get('SurfaceRoutes', [])
    templates = [fields[k] for k in ('ParticleTemplate', 'DecalMaterial') if fields.get(k)]
    templates += [str(route['Surface']) + ':' + route['ParticleTemplate'] for route in routes]
    raw = event['source']['raw_event']
    rows.append({'Montage': event['montage'], 'Sequence': event['sequence'], 'Segment': event['segment_index'],
        'EventId': event['event_id'], 'Type': event['notify_type'],
        'StartSeconds': event['start_time'], 'EndSeconds': event['end_time'],
        'WindowSeconds': event['end_time'] - event['start_time'],
        'DecalLifeSpanSeconds': fields.get('DecalLifeSpan', ''),
        'RequiresConfirmedHit': fields.get('bOnAttackSuccessed', False),
        'EndDestroysEmission': fields.get('bDestroyOnNotifyEnd', False),
        'DeactivateInsteadOfDestroy': fields.get('bDestroyOnNotifyEndDeactived', False),
        'Attached': fields.get('bAttached', False), 'Socket': fields.get('SourceSocket', ''),
        'TemplatesAndSurfaceRoutes': ' | '.join(templates), 'SourcePackage': event['source']['package'],
        'SourceField': event['source']['field'], 'RawLinkValueSeconds': raw.get('LinkValue', ''),
        'RawDurationSeconds': raw.get('Duration', ''),
        'DurationMeaning': 'Notify emission/eligibility window; surviving particle lifetime remains the source emitter definition.'})
with (OUT / 'AttackEffectPlayback.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps({'event_rows': len(rows), 'csv': str(OUT / 'AttackEffectPlayback.csv')}))
