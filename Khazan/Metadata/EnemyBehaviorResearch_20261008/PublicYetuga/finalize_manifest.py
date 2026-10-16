import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
records = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
for record in records:
    for field in ("file", "sheet"):
        record[field] = str(root / Path(record[field]).name)
    record["sha256"] = hashlib.sha256(Path(record["file"]).read_bytes()).hexdigest()
    record["observation_method"] = "sampled contact-sheet inspection; not continuous playback"
(root / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"entries": len(records), "files_verified": all(Path(r["file"]).exists() and Path(r["sheet"]).exists() for r in records)}, ensure_ascii=False))
