"""Submit work only to the isolated snow editor; never connect to the user editor."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
MAIL=STAGE/'Saved/SnowMailbox'
ROOT=Path(__file__).resolve().parents[2]
ready=json.loads((MAIL/'Ready.json').read_text(encoding='utf-8'))
assert ready.get('session'),'Wait for the fresh isolated editor Ready.json'
job=dict(project=str(STAGE),action=sys.argv[1],editor_pid=ready['pid'],session=ready['session'])
if job['action']=='python':job['script']=Path(sys.argv[2]).read_text(encoding='utf-8-sig')
elif job['action']=='console':job['command']=sys.argv[2]
elif job['action']!='quit':raise ValueError(job['action'])
name=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
path=MAIL/(name+'.request.json')
path.write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
print(path.with_name(name+'.response.json'))
