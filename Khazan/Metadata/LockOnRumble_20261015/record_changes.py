from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
changes, patch = [], []
for before in sorted((OUT / 'Before').rglob('*')):
    if not before.is_file():
        continue
    relative = before.relative_to(OUT / 'Before')
    current = ROOT / relative
    old, new = before.read_bytes(), current.read_bytes()
    if old == new:
        continue
    lines = list(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),
                                    new.decode('utf-8-sig').splitlines(True),
                                    fromfile='before/' + relative.as_posix(),
                                    tofile='after/' + relative.as_posix()))
    patch.extend(lines)
    changes.append(dict(path=relative.as_posix(), before_sha256=hashlib.sha256(old).hexdigest(),
                        current_sha256=hashlib.sha256(new).hexdigest(),
                        added_lines=sum(x.startswith('+') and not x.startswith('+++') for x in lines),
                        removed_lines=sum(x.startswith('-') and not x.startswith('---') for x in lines)))
(OUT / 'Changes.patch').write_text(''.join(patch), encoding='utf-8')
(OUT / 'ChangedFiles.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
print(json.dumps(changes, indent=2))
