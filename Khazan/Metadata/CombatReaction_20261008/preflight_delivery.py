from pathlib import Path
import json, hashlib, datetime
main = Path(__file__).resolve().parents[2]
out = main / 'Metadata/CombatReaction_20261008'
baseline = json.loads((out/'StageBaseline.json').read_text(encoding='utf8'))
work = Path(baseline['work'])
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
conflicts = [r['relative'] for r in baseline['rows'] if sha(main/r['relative']) != r['main']]
changes = [r['relative'] for r in baseline['rows'] if r['relative'].startswith('Source/') and sha(work/r['relative']) != r['main']]
known = {r['relative'] for r in baseline['rows']}
new = [p.relative_to(work).as_posix() for p in (work/'Source').rglob('*') if p.is_file() and p.relative_to(work).as_posix() not in known]
result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), main_conflicts=conflicts, source_changes=changes, work_new_source=new)
(out/'DeliveryPreflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))
