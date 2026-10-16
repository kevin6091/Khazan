"""Send UTF-8 QA code only to the isolated, session-identified ghosting game."""
from pathlib import Path
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
MAIL = ROOT / 'Saved/ImportReports/HeinMachGhosting_20261008/Mailbox'
ready = json.loads((MAIL / 'Ready.json').read_text(encoding='utf-8'))
script = Path(sys.argv[1]).read_text(encoding='utf-8')
request = MAIL / (uuid.uuid4().hex + '.request.json')
request.write_text(json.dumps(dict(pid=ready['pid'], session=ready['session'], script=script)), encoding='utf-8')
print(request.with_name(request.name.replace('.request.json', '.response.json')))
