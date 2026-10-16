"""Startup verifier for an explicitly owned fresh Main editor; never saves assets.

Launch separately on /Game/Maps/DevMap with -EnablePlugins=GameFeatures,
-abslog=<Main>/Metadata/MonsterMotion_20261008/MainFresh.log, and
-ExecCmds="py <Main>/Scripts/Engineering/verify_monster_facing_main_20261008.py".
This file is an Unreal Python entry point, not a launch/process-control helper.
Only this process may receive native Automation/PIE/quit commands. PIDs 3528/24260/13700 are protected.
"""
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
import uuid

import unreal


ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT = ROOT / 'Metadata/MonsterMotion_20261008'
LOG = OUT / 'MainFresh.log'
SCRIPT = ROOT / 'Scripts/Engineering/verify_monster_facing_main_20261008.py'
ALIAS = 'UnrealEditor-KhazanMonsterFacing20261008.dll'
PROTECTED_PID = 3528
PROTECTED_PIDS = (PROTECTED_PID, 24260, 13700)
MAP = '/Game/Maps/DevMap'
FAMILIES = (('Swordsman', 6.0), ('SwordShield', 10.0),
            ('HeavySwordsman', 10.0), ('HalberdElite', 5.0))
TESTS = ('Khazan.Monster.FacingPIE', 'Khazan.Monster.CombatPolicyPIE',
         'Khazan.Heal.PIE', 'Khazan.Guard.PIE')
SOURCE_FILES = ('Source/Khazan/AI/KZMonsterAIController.h',
                'Source/Khazan/AI/KZMonsterAIController.cpp',
                'Source/Khazan/Character/KZMonster.h',
                'Source/Khazan/Character/KZMonster.cpp',
                'Source/Khazan/Ability/Combo/KZComboActionAbility.h',
                'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
                'Source/Khazan/Tests/KZMonsterAIPIETest.cpp',
                'Source/Khazan/Tests/KZHealAbilityPIETest.cpp')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def command_line_args():
    # These calls inspect only the current process; no OpenProcess/PID lookup is used.
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCommandLineW.restype = wintypes.LPCWSTR
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(kernel.GetCommandLineW(), ctypes.byref(count))
    if not pointer:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [pointer[index] for index in range(count.value)]
    finally:
        kernel.LocalFree(ctypes.cast(pointer, wintypes.HLOCAL))


def own_module_paths():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    psapi.EnumProcessModulesEx.restype = wintypes.BOOL
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                          wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD
    process = kernel.GetCurrentProcess()
    count = 1024
    while True:
        modules = (wintypes.HMODULE * count)()
        needed = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(process, modules, ctypes.sizeof(modules),
                                         ctypes.byref(needed), 3):  # LIST_MODULES_ALL
            raise ctypes.WinError(ctypes.get_last_error())
        actual_count = needed.value // ctypes.sizeof(wintypes.HMODULE)
        if actual_count <= count:
            break
        count = actual_count + 64
    paths = []
    for index in range(actual_count):
        buffer = ctypes.create_unicode_buffer(32768)
        if not psapi.GetModuleFileNameExW(process, modules[index], buffer, len(buffer)):
            raise ctypes.WinError(ctypes.get_last_error())
        paths.append(str(Path(buffer.value).resolve()))
    return paths


def delivery_guard():
    receipt = read(OUT / 'Delivery.json')
    assert receipt['success'] is True, 'Delivery did not complete successfully'
    assert receipt['restart_required_for_previously_running_editor'] is True
    module = Path(receipt['module']).resolve()
    assert module == (ROOT / 'Binaries/Win64' / ALIAS).resolve(), str(module)
    assert sha(module) == receipt['module_sha256'].lower(), 'Alias DLL hash differs from delivery'
    manifest = read(ROOT / 'Binaries/Win64/UnrealEditor.modules')
    assert manifest['Modules']['Khazan'] == ALIAS, 'Main manifest selects a different DLL'
    hashes = receipt['hashes']
    assert isinstance(hashes, dict) and hashes, 'Missing delivery file hashes'
    normalized = {Path(name.replace('\\', '/')).as_posix(): value for name, value in hashes.items()}
    required = set(SOURCE_FILES) | {'Binaries/Win64/UnrealEditor.modules', 'Binaries/Win64/' + ALIAS}
    required.update('Content/Monsters/' + family + '/Animations/BS_Combat_' + family + '.uasset'
                    for family, _ in FAMILIES)
    assert required <= normalized.keys(), 'Required delivery hashes missing: ' + str(required - normalized.keys())
    checked = {}
    for relative, expected in normalized.items():
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT), 'Delivery hash path escapes Main: ' + relative
        assert isinstance(expected, str) and len(expected) == 64
        actual = sha(path)
        assert actual == expected.lower(), 'Delivered file hash mismatch: ' + relative
        checked[relative] = actual
    paths = own_module_paths()
    loaded = [path for path in paths if Path(path).name.lower().startswith('unrealeditor-khazan')
              and Path(path).suffix.lower() == '.dll']
    assert len(loaded) == 1 and Path(loaded[0]) == module, 'Unexpected loaded Khazan DLLs in this own process: ' + str(loaded)
    return {'delivery_sha256': sha(OUT / 'Delivery.json'), 'checked_hashes': checked,
            'module_path': str(module), 'module_sha256': sha(module),
            'manifest_build_id': manifest.get('BuildId'),
            'module_paths': paths, 'loaded_khazan_modules': loaded}


def dirty_packages():
    return {'content': [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
            'maps': [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}


def asset_readback(rows=None):
    # Caller-owned rows preserve successful/partial readbacks when a later assertion fails.
    rows = [] if rows is None else rows
    for family, speed in FAMILIES:
        base = '/Game/Monsters/' + family + '/Animations/'
        bp_path = '/Game/Bluprints/Monsters/BP_Monster_' + family
        bp = unreal.load_asset(bp_path)
        abp = unreal.load_asset(base + 'ABP_' + family)
        space = unreal.load_asset(base + 'BS_Combat_' + family)
        assert bp and abp and space, 'Missing four-family asset: ' + family
        row = {'family': family, 'bp': bp.get_path_name(), 'abp': abp.get_path_name(),
               'bp_status': str(bp.get_editor_property('status')),
               'abp_status': str(abp.get_editor_property('status')),
               'blendspace': space.get_path_name(),
               'weight_speed': float(space.get_editor_property('target_weight_interpolation_speed_per_sec'))}
        rows.append(row)
        assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, row
        assert abp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, row
        assert row['weight_speed'] == speed, row
        generated = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
        assert generated and generated.get_path_name() == bp_path + '.BP_Monster_' + family + '_C'
        cdo = unreal.get_default_object(generated)
        row['cdo_class'] = generated.get_path_name()
        cmc = cdo.get_editor_property('CharacterMovement')
        assert cmc, 'Missing CharacterMovement CDO component: ' + family
        row['allow_physics_rotation_during_anim_root_motion'] = bool(
            cmc.get_editor_property('bAllowPhysicsRotationDuringAnimRootMotion'))
        assert row['allow_physics_rotation_during_anim_root_motion'] is True, row
        settings = cdo.get_editor_property('AISettings')
        expected = {'AttackTrackingYawRate': 60.0, 'ComboReaimYawRate': 180.0,
                    'AttackPreparationSeconds': 0.15}
        row['ai_settings'] = {}
        for field, value in expected.items():
            actual = float(settings.get_editor_property(field))
            row['ai_settings'][field] = actual
            assert math.isfinite(actual) and actual > 0 and abs(actual - value) < 1e-6, (family, field, actual)
    return rows


class MainVerifier:
    def __init__(self, args):
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.perf = None
        self.saved_throttle = None
        self.callback = None
        self.busy = False
        self.phase = 'startup'
        self.index = -1
        self.deadline = 0.0
        self.drain_started = 0.0
        self.offset = 0
        self.current = None
        self.final_success = False
        self.final_error = None
        self.identity_seen = False
        self.identity_tail = ''
        self.identity = 'KZ_MONSTER_MAIN_FRESH_OWN_PID=' + str(os.getpid()) + '_' + uuid.uuid4().hex
        self.report = {'success': False, 'pid': os.getpid(), 'protected_editor_pid': PROTECTED_PID,
                       'protected_editor_pids': list(PROTECTED_PIDS),
                       'project': str(ROOT), 'map_asset': MAP, 'log': str(LOG), 'command_line_args': args,
                       'script': str(SCRIPT), 'script_sha256': sha(SCRIPT),
                       'module_alias': ALIAS, 'module_path': None,
                       'expected_module_path': str(ROOT / 'Binaries/Win64' / ALIAS),
                       'identity_marker': self.identity, 'package_save': False, 'map_save': False,
                       'blueprint_compile': False, 'python_body_movement': False,
                       'tests': [], 'utc_started': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def console(self, command):
        unreal.SystemLibrary.execute_console_command(
            self.editor.get_game_world() or self.editor.get_editor_world(), command)

    def start(self):
        try:
            self.report['delivery'] = delivery_guard()
            self.report['module_path'] = self.report['delivery']['module_path']
            self.report['module_sha256'] = self.report['delivery']['module_sha256']
            assert not self.editor.get_game_world(), 'Fresh editor already in PIE'
            world = self.editor.get_editor_world()
            assert world and world.get_path_name().split('.')[0] == MAP, 'Fresh editor must launch on DevMap'
            self.report['editor_world'] = world.get_path_name()
            self.report['assets_before'] = []
            asset_readback(self.report['assets_before'])
            self.report['dirty_before'] = dirty_packages()
            assert not any(self.report['dirty_before'].values()), 'Fresh saved readback has dirty packages'
            self.perf = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
            self.saved_throttle = bool(self.perf.get_editor_property('bThrottleCPUWhenNotForeground'))
            self.perf.set_editor_property('bThrottleCPUWhenNotForeground', False,
                                         notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            self.report['original_throttle'] = self.saved_throttle
            self.offset = LOG.stat().st_size
            self.callback = unreal.register_slate_post_tick_callback(self.tick)
            write('ownReady.json', dict(self.report, ready=True, saved_readback_passed=True))
            print(self.identity)
            self.next_test()
        except Exception:
            self.report['startup_error'] = traceback.format_exc()
            self.finish_now(False, self.report['startup_error'])

    def next_test(self):
        assert not self.editor.get_game_world(), 'Previous PIE has not stopped'
        self.index += 1
        if self.index == len(TESTS):
            self.begin_finish(True)
            return
        path = TESTS[self.index]
        self.current = {'path': path, 'started': False, 'pie_begin_requested': False,
                        'completed': False, 'success': False, 'native_log': '',
                        'request_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        self.report['tests'].append(self.current)
        self.phase = 'running'
        self.deadline = time.monotonic() + 420.0  # Wrapper timeout; no gameplay setting is changed.
        self.console('Automation RunTests ' + path)

    def begin_finish(self, success, error=None):
        if self.phase == 'finish':
            self.final_success = False
            self.final_error = (self.final_error + '\n' if self.final_error else '') + (error or 'Repeated finish failure')
            return
        self.final_success, self.final_error = success, error
        self.phase = 'finish'
        self.deadline = time.monotonic() + 30.0
        if self.editor.get_game_world():
            try:
                self.level.editor_request_end_play()
            except Exception:
                self.finish_now(False, (error + '\n' if error else '') + traceback.format_exc())

    def finish_now(self, success, error=None):
        # This method is reachable only after the own-process entry guard has passed.
        try:
            current_delivery = delivery_guard()
            assert sha(SCRIPT) == self.report['script_sha256'], 'Verifier script changed during verification'
            initial = self.report.get('delivery')
            if initial:
                assert current_delivery['delivery_sha256'] == initial['delivery_sha256'], 'Delivery changed during verification'
            self.report['delivery_after'] = current_delivery
            self.report['dirty_after'] = dirty_packages()
            assert not any(self.report['dirty_after'].values()), 'Verification left dirty packages; none will be saved'
            assert not self.editor.get_game_world(), 'PIE did not stop'
            if success:
                assert len(self.report['tests']) == len(TESTS) and all(test['success'] for test in self.report['tests'])
                assert self.identity_seen, 'Own process identity marker was not observed in its native log'
                self.report['assets_after'] = []
                asset_readback(self.report['assets_after'])
        except Exception:
            success = False
            error = (error + '\n' if error else '') + traceback.format_exc()
        if self.perf is not None and self.saved_throttle is not None:
            try:
                self.perf.set_editor_property('bThrottleCPUWhenNotForeground', self.saved_throttle,
                                             notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                self.report['throttle_restored'] = (
                    self.perf.get_editor_property('bThrottleCPUWhenNotForeground') == self.saved_throttle)
                assert self.report['throttle_restored']
            except Exception:
                success = False
                error = (error + '\n' if error else '') + traceback.format_exc()
        if self.callback is not None:
            unreal.unregister_slate_post_tick_callback(self.callback)
            self.callback = None
        self.phase = 'done'
        self.report.update(success=bool(success), error=error,
                           identity_seen_in_own_log=self.identity_seen,
                           native_main_pie_verified=bool(success),
                           utc_completed=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write('MainFreshVerification.json', self.report)
        if 'startup_error' in self.report:
            write('ownReady.json', dict(self.report, ready=False))
        print('KZ_MONSTER_MAIN_FRESH_VERIFICATION', os.getpid(), bool(success), error or '')
        unreal.SystemLibrary.quit_editor()

    def tick(self, delta):
        if self.busy or self.phase == 'done':
            return
        self.busy = True  # PIE creation/destruction can reenter a Slate callback.
        try:
            now = time.monotonic()
            # Finish/restore/quit must still work if the native log becomes unreadable.
            if self.phase == 'finish':
                if not self.editor.get_game_world():
                    self.finish_now(self.final_success, self.final_error)
                elif now > self.deadline:
                    self.finish_now(False, (self.final_error or '') + '\nPIE cleanup deadline exceeded')
                return
            assert LOG.stat().st_size >= self.offset, 'Own native log was truncated during verification'
            with LOG.open('rb') as stream:
                stream.seek(self.offset)
                chunk = stream.read().decode('utf-8', errors='replace')
                self.offset = stream.tell()
            identity_text = self.identity_tail + chunk
            self.identity_seen = self.identity_seen or self.identity in identity_text
            self.identity_tail = identity_text[-len(self.identity):]
            if self.current:
                self.current['native_log'] += chunk
            if now > self.deadline:
                self.begin_finish(False, 'Owned native test/cleanup deadline exceeded: ' + self.phase)
                return
            if self.phase == 'drain':
                if not self.editor.get_game_world() and now - self.drain_started >= 0.5:
                    self.next_test()
                return
            if self.phase != 'running':
                return
            path_marker = 'Path={' + self.current['path'] + '}'
            lines = self.current['native_log'].splitlines()
            started = [line for line in lines if 'Test Started.' in line and path_marker in line]
            if started:
                self.current['started'] = True
                self.current['start_line'] = started[0]
            if self.current['started'] and not self.current['pie_begin_requested']:
                assert not self.editor.get_game_world(), 'Unexpected PIE before own begin request'
                self.current['pie_begin_requested'] = True
                self.level.editor_request_begin_play()
            completed = [line for line in lines if 'Test Completed.' in line and path_marker in line]
            if completed:
                self.current['completed'] = True
                self.current['completion_line'] = completed[-1]
                self.current['success'] = (self.current['started'] and self.current['pie_begin_requested']
                                           and 'Result={Success}' in completed[-1])
                if not self.current['success']:
                    self.begin_finish(False, 'Native Automation failed: ' + completed[-1])
                    return
                if self.editor.get_game_world():
                    self.level.editor_request_end_play()
                self.phase = 'drain'
                self.drain_started = now
                self.deadline = now + 30.0
        except Exception:
            self.begin_finish(False, traceback.format_exc())
        finally:
            self.busy = False


# Do not write, alter settings, request PIE, issue console commands, or quit until
# these guards establish this uniquely launched process. In particular PID3528/24260
# is rejected here, before a MainVerifier object can act on the editor.
assert os.getpid() not in PROTECTED_PIDS, 'Protected user editor PID3528/24260: verifier must not run here'
actual_root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
assert actual_root == ROOT, 'Verifier accepts only the exact Main project root'
arguments = command_line_args()
log_args = [arg.split('=', 1)[1] for arg in arguments if arg.lower().startswith('-abslog=')]
assert len(log_args) == 1 and Path(log_args[0]).resolve() == LOG.resolve(), 'Own MainFresh absolute log is required'
exec_args = [arg.split('=', 1)[1] for arg in arguments if arg.lower().startswith('-execcmds=')]
normalized_script = SCRIPT.as_posix().lower()
assert len(exec_args) == 1 and normalized_script in exec_args[0].replace('\\', '/').lower(), 'Own startup verifier ExecCmds is required'
assert LOG.is_file(), 'Own fresh editor log must exist before verification'
OWN_VERIFIER = MainVerifier(arguments)
OWN_VERIFIER.start()
