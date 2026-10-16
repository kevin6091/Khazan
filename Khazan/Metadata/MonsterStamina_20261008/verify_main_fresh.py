import ast, ctypes, hashlib, json, os, pathlib, runpy, unreal
MAIN = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
assert pathlib.Path(unreal.Paths.project_dir()).resolve() == MAIN
OUT = MAIN/'Metadata/MonsterStamina_20261008'
manifest = json.loads((OUT/'PreparedDeliveryManifest.json').read_text(encoding='utf-8'))
receipt = json.loads((OUT/'DeliveryReceipt.json').read_text(encoding='utf-8'))
assert receipt['complete']
scope = runpy.run_path(str(MAIN/'Scripts/Engineering/verify_monster_stamina_saved_20261008.py'))
report = scope['REPORT']
assert report['success'], report.get('error')
kernel = ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p]; kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint]
current_build = OUT/'ConcurrentMainRebuild.json'
current_proof = json.loads(current_build.read_text(encoding='utf-8')) if current_build.exists() else None
selected_module = current_proof['module'] if current_proof else manifest['alias']
selected_digest = current_proof['module_sha256'] if current_proof else manifest['dll_sha256']
handle = kernel.GetModuleHandleW(selected_module); assert handle
buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(handle,buffer,len(buffer))
loaded = pathlib.Path(buffer.value).resolve()
digest = hashlib.sha256(loaded.read_bytes()).hexdigest()
assert loaded == (MAIN/'Binaries/Win64'/selected_module).resolve() and digest == selected_digest
report['loaded_module'] = dict(path=str(loaded),sha256=digest,pid=os.getpid())
# Reuse only the existing read-only four-family check; do not execute its editor/PIE controller.
facing_script = MAIN/'Scripts/Engineering/verify_monster_facing_main_20261008.py'
parsed = ast.parse(facing_script.read_text(encoding='utf-8'))
function = next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='asset_readback')
facing_scope = dict(unreal=unreal, math=__import__('math'), FAMILIES=(('Swordsman',6.0),('SwordShield',10.0),('HeavySwordsman',10.0),('HalberdElite',5.0)))
exec(compile(ast.Module(body=[function],type_ignores=[]),str(facing_script),'exec'),facing_scope)
report['facing_saved_readback'] = facing_scope['asset_readback']()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
report_name = 'MainSavedReload_ConcurrentBuild.json' if current_proof else 'MainSavedReload.json'
(OUT/report_name).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MonsterStaminaMainFreshComplete='+json.dumps(dict(success=True,pid=os.getpid(),loaded_module=str(loaded),dirty_content=report.get('dirty_content'),dirty_map=report.get('dirty_map'))))
