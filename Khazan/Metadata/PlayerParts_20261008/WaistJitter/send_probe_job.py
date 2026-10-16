"""Send a guarded job only to the isolated player-parts mailbox."""
import argparse, json
from pathlib import Path

work = Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan').resolve()
mail = work / 'Saved/PlayerPartsMailbox'
p = argparse.ArgumentParser()
p.add_argument('number', type=int)
p.add_argument('pid', type=int)
p.add_argument('action', choices=['python', 'console', 'quit'])
p.add_argument('payload', nargs='?', default='')
a = p.parse_args()
ready = json.loads((mail / 'Ready.json').read_text(encoding='utf-8-sig'))
assert ready['pid'] == a.pid and Path(ready['project']).resolve() == work, ready
request = mail / f'{a.number:03}.request.json'
assert not request.exists(), request
job = dict(project=str(work), action=a.action)
if a.action == 'python':
    job['script'] = f'assert os.getpid() == {a.pid}\n' + Path(a.payload).read_text(encoding='utf-8-sig')
elif a.action == 'console':
    # project identity is enforced by the work mailbox before any console action.
    job['command'] = a.payload
request.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
print(request)
