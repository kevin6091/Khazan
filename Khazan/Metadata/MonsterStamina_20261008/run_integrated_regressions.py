import datetime, json, pathlib, shutil, subprocess, sys, time
OUT = pathlib.Path(__file__).resolve().parent
WORK = OUT.parents[2].parent.parent / 'Khazan_MonsterWork_20261006' / 'Khazan'
# Keep the project literal authoritative; no discovery of unrelated editor sessions.
WORK = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
PID = 30028
LOG = WORK / 'Saved/Logs/MonsterWorkEditor.log'
TESTS = ['Khazan.Monster.FacingPIE', 'Khazan.Monster.CombatPolicyPIE', 'Khazan.Guard.PIE',
         'Khazan.Heal.PIE', 'Khazan.Combat.PlayerAttackCollision.PIE']
result = dict(pid=PID, project=str(WORK), started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), tests=[], success=False)
def save():
    (OUT / 'IntegratedRegression.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
def mail(*args):
    p = subprocess.run([sys.executable, str(OUT / 'mail_job.py'), '--pid', str(PID), *args], check=True, capture_output=True, text=True)
    return pathlib.Path(p.stdout.strip()).with_name(pathlib.Path(p.stdout.strip()).name.replace('.request.json', '.response.json'))
def await_response(path):
    until = time.monotonic() + 30
    while not path.exists():
        if time.monotonic() > until: raise RuntimeError('Owned mailbox response timeout')
        time.sleep(.25)
    r = json.loads(path.read_text(encoding='utf-8'))
    if r['pid'] != PID or not r['success']: raise RuntimeError('Owned mailbox failed: ' + str(r.get('error')))
try:
    for name in TESTS:
        start = len(LOG.read_text(encoding='utf-8', errors='replace'))
        await_response(mail('--console', 'Automation RunTests ' + name))
        print('Started', name, flush=True)
        deadline = time.monotonic() + 1100
        while True:
            text = LOG.read_text(encoding='utf-8', errors='replace')[start:]
            completed = [l for l in text.splitlines() if 'Test Completed.' in l and 'Path={' + name + '}' in l]
            if completed: break
            if time.monotonic() > deadline: raise RuntimeError('Native regression timeout: ' + name)
            time.sleep(1)
        ok = 'Result={Success}' in completed[-1]
        dest = OUT / ('Regression_' + name.replace('.', '_') + '.log')
        dest.write_text(text, encoding='utf-8')
        result['tests'].append(dict(test=name, success=ok, completed_line=completed[-1], log=str(dest)))
        save(); print('Completed', name, ok, flush=True)
        await_response(mail('--script', str(OUT / 'end_owned_pie.py')))
        time.sleep(2)
        if not ok: raise RuntimeError('Native regression failed: ' + name)
    result['success'] = True
    result['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
except Exception as error:
    result['error'] = str(error); save(); raise
