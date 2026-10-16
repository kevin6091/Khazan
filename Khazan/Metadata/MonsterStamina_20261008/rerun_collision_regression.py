import argparse, datetime, json, pathlib, subprocess, sys, time
OUT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
p = argparse.ArgumentParser(); p.add_argument('--pid', type=int, required=True); PID = p.parse_args().pid
LOG = WORK / 'Saved/Logs/MonsterWorkEditor.log'
NAME = 'Khazan.Combat.PlayerAttackCollision.PIE'
def mail(*args):
    r = subprocess.run([sys.executable, str(OUT/'mail_job.py'), '--pid', str(PID), *args], check=True, capture_output=True, text=True)
    path = pathlib.Path(r.stdout.strip()); response = path.with_name(path.name.replace('.request.json','.response.json'))
    deadline = time.monotonic()+30
    while not response.exists():
        if time.monotonic()>deadline: raise RuntimeError('Mailbox timeout')
        time.sleep(.25)
    row = json.loads(response.read_text(encoding='utf-8'))
    assert row['pid']==PID and row['success'], row
start = len(LOG.read_text(encoding='utf-8',errors='replace'))
mail('--console','Automation RunTests '+NAME)
print('Started corrected isolated collision regression', PID, flush=True)
deadline = time.monotonic()+600
while True:
    text = LOG.read_text(encoding='utf-8', errors='replace')[start:]
    completed = [l for l in text.splitlines() if 'Test Completed.' in l and 'Path={'+NAME+'}' in l]
    if completed: break
    if time.monotonic()>deadline: raise RuntimeError('Native collision test timeout')
    time.sleep(1)
ok = 'Result={Success}' in completed[-1]
dest = OUT/'Regression_Khazan_Combat_PlayerAttackCollision_PIE_LatestClips.log'
dest.write_text(text,encoding='utf-8')
result_path = OUT/'IntegratedRegression.json'
result = json.loads(result_path.read_text(encoding='utf-8'))
result.setdefault('historical_failed_attempts',[]).extend(r for r in result['tests'] if r['test']==NAME and not r['success'])
result['tests'] = [r for r in result['tests'] if r['test']!=NAME]
result['tests'].append(dict(test=NAME,success=ok,pid=PID,completed_line=completed[-1],log=str(dest),asset_intake='LatestCollisionClipIntake.json'))
result['success'] = all(r['success'] for r in result['tests']) and len(result['tests'])==5
result['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
if result['success']: result.pop('error',None)
result_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
mail('--script',str(OUT/'end_owned_pie.py'))
print('Collision regression success:',ok,flush=True)
if not ok: raise RuntimeError('Collision regression failed')
