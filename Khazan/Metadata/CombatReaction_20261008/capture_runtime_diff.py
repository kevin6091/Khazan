"""Readonly final review diff; no project writes."""
from pathlib import Path
import difflib, json, hashlib
main = Path(__file__).resolve().parents[2]
meta = main / 'Metadata/CombatReaction_20261008'
base = json.loads((meta/'StageBaseline.json').read_text(encoding='utf-8-sig'))
work = Path(base['work'])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
rows = [r for r in base['rows'] if r['relative'].startswith('Source/') and r['relative'] != 'Source/Khazan/Khazan.Build.cs' and sha(work/r['relative']) != r['main']]
rows += [dict(relative='Source/Khazan/Ability/KZHitReactionAbility.'+ext, main=None) for ext in ('h','cpp')]
assert len(rows)==16
target = meta / 'RuntimeChanges.patch'
assert not target.exists()
patch = []
for row in rows:
    rel=row['relative']; before=main/rel; after=work/rel
    assert sha(before)==row['main'], 'Main changed: '+rel
    old = before.read_text(encoding='utf-8-sig').splitlines(keepends=True) if before.exists() else []
    patch.extend(difflib.unified_diff(old,after.read_text(encoding='utf-8-sig').splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
target.write_text(''.join(patch),encoding='utf8')
print('Runtime diff:',len(rows),'files')
