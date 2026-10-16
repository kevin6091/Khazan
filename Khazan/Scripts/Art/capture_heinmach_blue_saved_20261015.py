"""Capture saved blue lighting from existing route cameras; no transient retuning."""
from pathlib import Path
import ctypes,hashlib,json,os
main=Path(os.environ['KZ_LOOKSPIN_MAIN'])
os.environ.update(KZ_LOOK_OUT=os.environ['KZ_LOOKSPIN_OUT'],KZ_LOOK_MAIN=str(main),
                  KZ_LOOK_LEVEL='HeinMach',KZ_LOOK_MODE='capture')
source=(main/'Scripts/Art/scene_look_capture_20261012.py').read_text(encoding='utf-8')
old="unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename=\"'+str(target)+'\" -nosuffix')"
assert source.count(old)==1
source=source.replace(old,"unreal.SystemLibrary.execute_console_command(WORLD,'KZ.QA.ColourShot \"'+str(target)+'\"')")
exec(compile(source,__file__,'exec'),globals())
VIEWS=[view for view in VIEWS if view[0] in ('Entry','ReferenceStart','OpenSky')]
report['scope']='Saved map, existing route cameras, native game viewport. No asset saves or lighting overrides.'
unreal.SystemLibrary.execute_console_command(world,'DisableAllScreenMessages')
project=Path(unreal.Paths.project_dir()).resolve()
manifest=json.loads((project/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768)
module_handle=kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert module_handle and kernel.GetModuleFileNameW(module_handle,buffer,len(buffer))
module=Path(buffer.value).resolve();assert module.is_relative_to(project/'Binaries')
report['actual_module']=str(module);report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
