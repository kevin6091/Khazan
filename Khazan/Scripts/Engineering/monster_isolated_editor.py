"""File mailbox for the explicitly isolated Monster editor; never injects player input.

All asset edits and native tests run in the copied project. No Rider connection is
used, so an unrelated open editor cannot receive these commands.
"""
import contextlib
import datetime
import io
import json
import os
import pathlib
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
EXPECTED = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
if ROOT != EXPECTED:
    raise RuntimeError('Monster editor mailbox must run only in the isolated project')
MAIL = ROOT / 'Saved/MonsterMailbox'
MAIL.mkdir(parents=True, exist_ok=True)
PERF = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
ORIGINAL_THROTTLE = PERF.get_editor_property('bThrottleCPUWhenNotForeground')
PERF.set_editor_property('bThrottleCPUWhenNotForeground', False, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
_seen_test_start = set()
_scope = globals()


def _write(path, data):
    data.update(pid=os.getpid(), project=str(ROOT), utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    temp.replace(path)


def _console(command):
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = subsystem.get_game_world() or subsystem.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, command)


def _process_tick(delta):
    # Keep Automation preparation and PIE in this same work process. No input injection.
    log = ROOT / 'Saved/Logs/MonsterWorkEditor.log'
    if log.exists():
        text = log.read_text(encoding='utf-8', errors='replace')
        starts = [line for line in text.splitlines() if 'Test Started.' in line and
                  ('Path={Khazan.Monster.PIE}' in line or 'Path={Khazan.Monster.StaminaPIE}' in line or 'Path={Khazan.Monster.FacingPIE}' in line or 'Path={Khazan.Combat.PlayerAttackCollision.PIE}' in line or 'Path={Khazan.Monster.AttackPatternsPIE}' in line or 'Path={Khazan.Monster.CombatPolicyPIE}' in line or 'Path={Khazan.Monster.HalberdPIE}' in line or 'Path={Khazan.Monster.WaitingPIE}' in line or 'Path={Khazan.Heal.PIE}' in line or 'Path={Khazan.Guard.PIE}' in line)]
        for line in starts:
            if line not in _seen_test_start:
                _seen_test_start.add(line)
                if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None:
                    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    for request in sorted(MAIL.glob('*.request.json')):
        response = request.with_name(request.name.replace('.request.json', '.response.json'))
        if response.exists():
            continue
        output = io.StringIO()
        try:
            job = json.loads(request.read_text(encoding='utf-8-sig'))
            if job.get('project') != str(ROOT):
                raise RuntimeError('Mailbox project identity mismatch')
            if job['action'] == 'console':
                _console(job['command'])
            elif job['action'] == 'python':
                with contextlib.redirect_stdout(output):
                    exec(compile(job['script'], str(request), 'exec'), _scope)
            elif job['action'] == 'quit':
                PERF.set_editor_property('bThrottleCPUWhenNotForeground', ORIGINAL_THROTTLE,
                                         notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                _write(response, dict(success=True, throttle_restored=ORIGINAL_THROTTLE))
                _console('QUIT_EDITOR')
                return
            else:
                raise RuntimeError('Unknown mailbox action')
            _write(response, dict(success=True, output=output.getvalue()))
        except Exception:
            _write(response, dict(success=False, output=output.getvalue(), error=traceback.format_exc()))


_processing = False
def _tick(delta):
    # Asset save/load can pump Slate recursively; consume a mailbox request only once.
    global _processing
    if _processing:
        return
    _processing = True
    try:
        _process_tick(delta)
    finally:
        _processing = False

HANDLE = unreal.register_slate_post_tick_callback(_tick)
_write(MAIL / 'Ready.json', dict(success=True, original_throttle=ORIGINAL_THROTTLE))
print('Monster isolated mailbox ready:', os.getpid(), ROOT)

