"""Summarize the actual viewport CSVs without exposing machine identifiers."""
from pathlib import Path
import csv
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[2]
META = ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'


def summarize(name):
    path = ROOT/'Saved/Profiling/CSV'/('HM_Snow_'+name+'_20261006.csv')
    rows = list(csv.reader(path.open(encoding='utf-8-sig', newline='')))
    # CSV may discover new stats mid-capture and append those columns. The
    # trailing header is authoritative; shorter initial rows have zero values
    # for counters that have not appeared yet.
    header = rows[-2] if rows[-2][0] == 'EVENTS' else rows[0]
    values = []
    for row in rows[1:]:
        if len(row) > len(header) or not row or row[0] == 'EVENTS':
            continue
        try:
            values.append([float(v or 0) for v in row[1:]]+[0.0]*(len(header)-len(row)))
        except ValueError:
            continue
    metadata = rows[-1]
    md = dict(zip(metadata[::2], metadata[1::2]))
    timing = {}
    counts = {}
    for index, key in enumerate(header[1:]):
        if key.startswith('NiagaraGpuCompute/') or key.startswith('Ticks/'):
            xs = [r[index] for r in values]
            counts[key] = {'median_count': statistics.median(xs), 'max_count': max(xs)}
        if (key.startswith('GPU/') or key == 'FrameTime'
                or key.startswith('Particles/GameThread')):
            xs = [r[index] for r in values]
            timing[key] = {'median_ms': round(statistics.median(xs), 5),
                           'p95_ms': round(sorted(xs)[math.ceil(len(xs)*.95)-1], 5),
                           'mean_ms': round(statistics.fmean(xs), 5)}
    return {'csv': str(path), 'numeric_frames': len(values), 'units': 'milliseconds',
            'hardware': {k: md.get('['+k+']') for k in ('cpu','gpu','rhiname','rhifeaturelevel','systemresolution.resx','systemresolution.resy')},
            'timings': timing, 'counters': counts}


on, off = summarize('On'), summarize('Off')
result = {'snow_on': on, 'snow_off': off,
          'measurement_limits': 'Development offscreen actual game, 1280x720, stationary preserved PlayerStart. t.MaxFPS=30. User Rider editor concurrently running. Sequential samples, not an isolated production benchmark; frame rate is capped and total GPU differences include background variance.'}
for key in on['timings'].keys() & off['timings'].keys():
    if key in ('GPU/Total','GPU/Translucency','GPU/TranslucencyAfterDOF'):
        result.setdefault('median_differences_ms',{})[key] = round(on['timings'][key]['median_ms']-off['timings'][key]['median_ms'], 5)
(META/'PerformanceVerification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'frames': [on['numeric_frames'], off['numeric_frames']],
                  'snow_compute': {k:v for k,v in on['timings'].items() if 'Niagara' in k},
                  'differences': result.get('median_differences_ms')}, indent=2))
