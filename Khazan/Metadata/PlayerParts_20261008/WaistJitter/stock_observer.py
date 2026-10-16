"""Read-only idle Iron observation in the isolated project with Main's selected DLL."""
import ctypes, datetime, hashlib, json, math, os, time
from ctypes import wintypes
from pathlib import Path
import unreal

# Check before rebinding any callback globals, including a repeated exec in the same scope.
if getattr(unreal, '_khazan_waist_stock_callback', {}).get('handle') is not None:
    _guard_root = Path(unreal.Paths.project_dir()).resolve()
    if _guard_root == Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan').resolve():
        (_guard_root/'Saved/PlayerWaistStockObservation.failure.json').write_text(json.dumps({'pid':os.getpid(), 'success':False, 'error':'Duplicate callback registration rejected; existing callback and PIE preserved'}), encoding='utf-8')
    raise RuntimeError('A waist stock callback is already registered; preserve its handle/PIE')

_stock_root = Path(unreal.Paths.project_dir()).resolve()
_stock_main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
_stock_report = _stock_main / 'Metadata/PlayerParts_20261008/WaistJitter'
_stock_work = Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan').resolve()
_stock_ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_stock_state = {'start': None, 'last_time': None, 'previous': {}, 'samples': {}, 'done': False,
                'wallStart': time.monotonic(), 'handle': None, 'ownsPIE': False}
_stock_bones = ('B_Iron_01_01_R_Pelvis', 'B_Iron_01_01_L_Pelvis')

def _stock_mapped_modules():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    handles = (wintypes.HMODULE * 4096)(); needed = wintypes.DWORD(); process = kernel.GetCurrentProcess()
    assert psapi.EnumProcessModulesEx(process, handles, ctypes.sizeof(handles), ctypes.byref(needed), 3)
    assert needed.value <= ctypes.sizeof(handles)
    paths = set()
    for handle in handles[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        buffer = ctypes.create_unicode_buffer(32768)
        assert psapi.GetModuleFileNameExW(process, handle, buffer, len(buffer))
        path = Path(buffer.value).resolve()
        if path.is_relative_to(_stock_root / 'Binaries/Win64') and path.name.lower().startswith('unrealeditor-khazan'):
            paths.add(path)
    return sorted(paths)

def _stock_cleanup():
    errors = []
    if _stock_state['handle'] is not None:
        try:
            unreal.unregister_slate_post_tick_callback(_stock_state['handle'])
            _stock_state['handle'] = None
        except Exception as error: errors.append('unregister: ' + repr(error))
    if _stock_state['ownsPIE']:
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            _stock_state['ownsPIE'] = False
        except Exception as error: errors.append('end own PIE: ' + repr(error))
    return errors

def _stock_fail(error):
    _stock_state['done'] = True
    output = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'pid': os.getpid(),
              'project': str(_stock_root), 'success': False, 'error': repr(error),
              'cleanupErrors': _stock_cleanup(), 'wallSeconds': time.monotonic() - _stock_state['wallStart'],
              'watchdogScope': '90 wall seconds checked at Slate post-tick; a blocked Slate loop cannot run the watchdog.'}
    if _stock_root == _stock_work:
        (_stock_root / 'Saved/PlayerWaistStockObservation.failure.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    unreal.log_error('Stock waist observation failed: ' + repr(error))

def _stock_quat(q):
    v = (q.x, q.y, q.z, q.w)
    length = math.sqrt(sum(x*x for x in v))
    assert math.isfinite(length) and length > 0
    return tuple(x/length for x in v)

def _stock_multiply(a, b):
    x,y,z,w = a; X,Y,Z,W = b
    return (w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z)

def _stock_observe(delta):
    if _stock_state['done']: return
    assert time.monotonic() - _stock_state['wallStart'] < 90, 'Stock observer 90-wall-second watchdog'
    world = _stock_ed.get_game_world()
    if not world: return
    t = unreal.GameplayStatics.get_time_seconds(world)
    if _stock_state['start'] is None: _stock_state['start'] = t
    elapsed = t - _stock_state['start']
    if elapsed < 3: return  # Technical settling window, not an asset/gameplay value.
    if _stock_state['last_time'] is not None and t <= _stock_state['last_time']: return
    dt = t - _stock_state['last_time'] if _stock_state['last_time'] is not None else None
    players = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/_Art/Player/Character/Bluprints/BP_Player.BP_Player_C'))
    assert len(players) == 1
    parts = players[0].get_components_by_class(unreal.SkeletalMeshComponent)
    leg = next(c for c in parts if c.get_name() == 'Leg')
    parent = _stock_quat(leg.get_socket_transform('Bip001-Pelvis', unreal.RelativeTransformSpace.RTS_WORLD).rotation)
    inverse = (-parent[0], -parent[1], -parent[2], parent[3])
    for bone in _stock_bones:
        child = _stock_quat(leg.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD).rotation)
        q = _stock_multiply(inverse, child)
        old = _stock_state['previous'].get(bone)
        if old is not None and dt is not None and dt > 0:
            dot = min(1., abs(sum(a*b for a,b in zip(old,q))))
            step = math.degrees(2*math.acos(dot))
            _stock_state['samples'].setdefault(bone, []).append({'time':t, 'deltaSeconds':dt, 'stepDegrees':step, 'speedDegreesPerSecond':step/dt})
        _stock_state['previous'][bone] = q
    _stock_state['last_time'] = t
    if elapsed < 8: return
    _stock_state['done'] = True
    scope = {'cloth_report_directory': _stock_report}
    path = _stock_main / 'Scripts/Engineering/player_cloth_stock_readback.py'
    exec(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec'), scope)
    assert hashlib.sha256(_stock_bound_dll.read_bytes()).hexdigest().upper() == _stock_binding['selectedMainSHA'], 'Bound DLL changed during observation'
    output = {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'pid':os.getpid(), 'success':True, 'phase':'Published idle pose after 3 game seconds until >=8; first quaternion excluded', 'project':str(_stock_root), 'selectedMainSHA':_stock_binding['selectedMainSHA'], 'mappedProjectModules':[str(p) for p in _stock_mapped], 'mainLivePatchEquivalent':False, 'native_contact_flags_measured':False, 'samples':_stock_state['samples'], 'metrics':{}}
    assert set(_stock_state['samples']) == set(_stock_bones)
    for bone, rows in _stock_state['samples'].items():
        assert len(rows) > 1
        output['metrics'][bone] = {'samples':len(rows), 'observedDeltaSeconds':sum(r['deltaSeconds'] for r in rows), 'stepRmsDegrees':math.sqrt(sum(r['stepDegrees']**2 for r in rows)/len(rows)), 'stepPeakDegrees':max(r['stepDegrees'] for r in rows), 'speedRmsDegreesPerSecond':math.sqrt(sum(r['speedDegreesPerSecond']**2 for r in rows)/len(rows))}
    output['cleanupErrors'] = _stock_cleanup()
    assert not output['cleanupErrors'], output['cleanupErrors']
    (_stock_root/'Saved/PlayerWaistStockObservation.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print('Stock idle Iron observation completed:', output['metrics'])
def _stock_tick(delta):
    if _stock_state['done']: return
    try: _stock_observe(delta)
    except Exception as error: _stock_fail(error)

try:
    assert _stock_root == _stock_work, 'Observer requires exact isolated Work project'
    assert isinstance(globals().get('stock_expected_pid'), int) and os.getpid() == stock_expected_pid, 'Supply exact stock_expected_pid'
    assert _stock_ed.get_game_world() is None, 'Observer starts/ends only its own PIE'
    assert unreal.SystemLibrary.get_console_variable_int_value('p.RigidBodyNode.EnableSimulation') == 1
    _stock_binding = json.loads((_stock_report/'StockBinding.json').read_text(encoding='utf-8-sig'))
    assert _stock_binding['status'] == 'Bound' and _stock_binding['bindingPhase'] == 'Complete' and Path(_stock_binding['workRoot']).resolve() == _stock_root
    _stock_bound_dll = Path(_stock_binding['selectedWorkPath']).resolve()
    assert _stock_bound_dll.is_relative_to(_stock_root/'Binaries/Win64')
    _stock_mapped = _stock_mapped_modules()
    assert _stock_mapped == [_stock_bound_dll], ('Unexpected project DLL or live patch mapped', _stock_mapped)
    assert hashlib.sha256(_stock_bound_dll.read_bytes()).hexdigest().upper() == _stock_binding['selectedMainSHA'], 'Mapped Work DLL SHA differs from selected Main base DLL'
    _stock_modules = json.loads((_stock_root/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
    assert _stock_modules['BuildId'] == _stock_binding['buildId'] and _stock_modules['Modules']['Khazan'] == _stock_bound_dll.name
    unreal._khazan_waist_stock_callback = _stock_state
    _stock_state['handle'] = unreal.register_slate_post_tick_callback(_stock_tick)
    _stock_state['ownsPIE'] = True
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
except Exception as error:
    _stock_fail(error)
    raise
