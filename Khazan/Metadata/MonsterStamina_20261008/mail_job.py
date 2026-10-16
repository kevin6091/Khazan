import argparse, ctypes, datetime, json, pathlib
p = argparse.ArgumentParser()
p.add_argument('--pid', type=int, required=True)
g = p.add_mutually_exclusive_group(required=True)
g.add_argument('--console'); g.add_argument('--script', type=pathlib.Path); g.add_argument('--quit', action='store_true')
a = p.parse_args()
root = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
mail = root / 'Saved/MonsterMailbox'
ready = json.loads((mail / 'Ready.json').read_text(encoding='utf-8'))
if ready['pid'] != a.pid or pathlib.Path(ready['project']).resolve() != root.resolve():
    raise RuntimeError('Own editor identity mismatch')
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.restype = ctypes.c_void_p
k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
k.CloseHandle.argtypes = [ctypes.c_void_p]
h = k.OpenProcess(0x1000, False, a.pid)
if not h:
    raise RuntimeError('Owned process no longer exists')
code = ctypes.c_ulong()
try:
    if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:
        raise RuntimeError('Owned process is not running')
finally:
    k.CloseHandle(h)
job = dict(project=str(root))
if a.console: job.update(action='console', command=a.console)
elif a.script: job.update(action='python', script=a.script.read_text(encoding='utf-8'))
else: job.update(action='quit')
name = 'Stamina_' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')
target = mail / (name + '.request.json')
target.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
print(target)
