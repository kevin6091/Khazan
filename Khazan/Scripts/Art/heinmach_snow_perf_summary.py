"""Summarize measured SnowTick time; no shipping FPS claim."""
from pathlib import Path
import csv
import json
import statistics
import sys
p=Path(sys.argv[1])
with p.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.DictReader(f)
    key=next(k for k in reader.fieldnames if k.endswith('/SnowTick'))
    values=[]
    for row in reader:
        try:value=float(row[key])
        except (ValueError,TypeError,KeyError):continue
        if value>0:values.append(value)
assert values
values.sort()
out=Path(__file__).resolve().parents[2]/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007'
report=dict(csv=str(p),column=key,active_samples=len(values),mean_ms=statistics.mean(values),
    p95_ms=values[int((len(values)-1)*.95)],max_ms=max(values),
    scope='Background Development Editor, HeinMach PIE Player run/dodge, weapon sweep, four Monster families and lying torso fixtures; includes cold asset/cache work and other editor contention; not shipping FPS or GPU cost')
(out/(p.stem+'_SnowTick.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
