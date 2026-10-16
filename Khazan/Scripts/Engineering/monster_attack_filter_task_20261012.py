"""Isolate the two humanoid attack policies; deliver only changed, hash-guarded assets."""
from pathlib import Path
from datetime import datetime, timezone
import ctypes, hashlib, json, os, shutil, subprocess, sys, time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackFilterWork_20261012/Khazan'
OUT = MAIN / 'Metadata/MonsterAttackFilter_20261012'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
FILES = ['Content/Bluprints/Monsters/BP_Monster_' + family + '.uasset' for family in ['Swordsman', 'SwordShield']]
FILES += ['Content/Monsters/' + family + '/Data/DA_Character_' + family + '.uasset' for family in ['Swordsman', 'SwordShield']]

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def junction(source, target):
    subprocess.run(['powershell', '-NoProfile', '-Command',
        'New-Item -ItemType Junction -Path "' + str(target) + '" -Target "' + str(source) + '" | Out-Null'], check=True)

def stage():
    assert not WORK.exists(), 'Preserve the existing task snapshot'
    WORK.mkdir(parents=True)
    selected = set(FILES)
    def tree(source, target, rel):
        if not any(p.startswith(rel + '/') for p in selected):
            junction(source, target); return
        target.mkdir()
        for child in source.iterdir():
            child_rel = rel + '/' + child.name
            if child.is_dir(): tree(child, target / child.name, child_rel)
            else: shutil.copy2(child, target / child.name)
    tree(MAIN / 'Content', WORK / 'Content', 'Content')
    for rel in FILES:
        target = OUT / 'Before' / rel; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MAIN / rel, target)
    shutil.copy2(MAIN / 'Khazan.uproject', WORK / 'Khazan.uproject')
    shutil.copytree(MAIN / 'Config', WORK / 'Config')
    shutil.copytree(MAIN / 'Binaries', WORK / 'Binaries', ignore=shutil.ignore_patterns('*.pdb'))
    for name in ['Source', 'Plugins']: junction(MAIN / name, WORK / name)
    write(OUT / 'Baseline.json', {'main':str(MAIN), 'work':str(WORK), 'files':{p:sha(MAIN / p) for p in FILES},
        'module':json.loads((MAIN / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig')),
        'utc':datetime.now(timezone.utc).isoformat()})
    print('STAGED_SELECTED', len(FILES), flush=True)

def run(name, project, mode):
    directory = OUT / name; directory.mkdir(exist_ok=False)
    root = MAIN if project == 'main' else WORK
    script = MAIN / 'Scripts/Engineering/monster_attack_filter_editor_20261012.py'
    cmd = [str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),
        str(root / 'Khazan.uproject'), '-unattended', '-nosplash', '-nosound', '-NoSourceControl', '-NoLiveCoding', '-NoAutoSave',
        '-EnablePlugins=GameFeatures', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(directory / 'Editor.log')]
    cmd += ['-NullRHI', '-run=pythonscript', '-script=' + str(script)]
    env = dict(os.environ, PYTHONUTF8='1', UE_SKIP_UBT_SDK_SETUP='1', KZ_ATTACK_FILTER_OUT=str(directory),
        KZ_ATTACK_FILTER_MODE=mode, KZ_ATTACK_FILTER_MAIN=str(MAIN))
    startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    started = time.monotonic()
    with (directory / 'stdout.txt').open('wb') as log:
        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
        write(directory / 'Launch.json', {'pid':proc.pid, 'command':cmd, 'mode':mode, 'project':str(root)})
        print('OWNED_ATTACK_FILTER_PROCESS', proc.pid, flush=True)
        try: code = proc.wait(timeout=900)
        except subprocess.TimeoutExpired: proc.terminate(); code = proc.wait(timeout=30)
    write(directory / 'Exit.json', {'exit':code, 'seconds':time.monotonic()-started})
    print('OWNED_ATTACK_FILTER_EXIT', code, flush=True)
    return code

def install():
    baseline = json.loads((OUT / 'Baseline.json').read_text(encoding='utf-8'))['files']
    assert json.loads((OUT / 'Prepared02/Report.json').read_text(encoding='utf-8'))['success']
    changed = [p for p in FILES if sha(WORK / p) != baseline[p]]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    for rel in changed:
        target = MAIN / rel
        assert target.resolve().is_relative_to((MAIN / 'Content').resolve())
        assert (WORK / rel).resolve().is_relative_to(WORK.resolve())
        assert sha(target) in [baseline[rel], sha(WORK / rel)], ('Concurrent Main change', rel)
        handle = kernel.CreateFileW(str(target), 0x10000, 0x7, None, 3, 0x80, None)
        if handle == ctypes.c_void_p(-1).value: raise OSError(ctypes.get_last_error(), 'Selected package locked', str(target))
        kernel.CloseHandle(handle)
    for rel in changed:
        target = MAIN / rel; temp = target.with_name(target.name + '.attack_filter.tmp')
        if sha(target) == sha(WORK / rel): continue
        shutil.copyfile(WORK / rel, temp); assert sha(temp) == sha(WORK / rel)
        os.replace(temp, target)
    write(OUT / 'Delivery.json', {'status':'MainDeliveredPendingFreshVerification',
        'files':[{'file':p, 'before':baseline[p], 'after':sha(MAIN/p)} for p in changed], 'runtime_source_changes':0, 'native_delivery':0})
    print('MAIN_ATTACK_FILTER_DELIVERED', len(changed), flush=True)

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == 'stage': stage()
    elif sys.argv[1] == 'install': install()
    else: sys.exit(run(*sys.argv[1:]))
