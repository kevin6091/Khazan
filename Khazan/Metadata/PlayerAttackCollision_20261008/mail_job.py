"""Send a reviewed script only to the task-owned, PID/session-bound ComboWork mailbox."""
from pathlib import Path
import argparse, json, time, uuid
p=argparse.ArgumentParser();p.add_argument('pid',type=int);p.add_argument('script');p.add_argument('--timeout',type=float,default=45);a=p.parse_args()
root=Path('C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan')
mail=root/'Saved/ImportReports/PlayerComboRepair_20261008/Mailbox'
ready=json.loads((mail/'Ready.json').read_text(encoding='utf-8-sig'))
assert ready['pid']==a.pid and Path(ready['project']).resolve()==root.resolve(),ready
name=uuid.uuid4().hex
req=mail/(name+'.request.json');response=mail/(name+'.response.json')
req.write_text(json.dumps(dict(pid=a.pid,session=ready['session'],script=Path(a.script).read_text(encoding='utf-8-sig'))),encoding='utf-8')
deadline=time.monotonic()+a.timeout
while not response.exists() and time.monotonic()<deadline:time.sleep(.25)
if not response.exists():raise TimeoutError(str(response))
r=json.loads(response.read_text(encoding='utf-8'));print(json.dumps(r,ensure_ascii=False,indent=2))
if not r['success']:raise SystemExit(1)
