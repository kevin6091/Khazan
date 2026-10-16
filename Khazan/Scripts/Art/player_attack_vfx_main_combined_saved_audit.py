"""Read only: fresh task-owned Main process after delivery, never the user's editor."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
assert Path(unreal.Paths.project_dir()).resolve() == MAIN
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
command_line = unreal.SystemLibrary.get_command_line().replace('\\', '/').lower()
assert '-run=pythonscript' in command_line and Path(__file__).resolve().as_posix().lower() in command_line
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
delivery_path = OUT / 'MainDelivery/Delivered.json'
delivered = read(delivery_path)
prepared = read(OUT / 'MainDelivery/Prepared.json')
assert delivered['status'] == 'SourceContentAndNativeAliasDelivered'
assert os.getpid() != prepared['main_pid'], 'Never run in the existing user process'
assert delivered['prepared_sha256'] == sha(OUT / 'MainDelivery/Prepared.json')
manifest = MAIN / 'Binaries/Win64/UnrealEditor.modules'
assert sha(manifest) == delivered['module_manifest_sha256']
assert read(manifest)['Modules']['Khazan'] == delivered['module']
module = MAIN / 'Binaries/Win64' / delivered['module']
native = next(r for r in delivered['native_files'] if r['destination'].endswith('.dll'))
assert sha(module) == native['sha256']
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = (ctypes.c_wchar_p,)
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32)
kernel.GetModuleFileNameW.restype = ctypes.c_uint32
handle = kernel.GetModuleHandleW(delivered['module'])
assert handle, 'The delivered unique native alias must actually be loaded'
buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(handle, buffer, len(buffer))
assert Path(buffer.value).resolve() == module.resolve()
selected = {r['file']: r['after'] for r in delivered['files']}
assert all(sha(MAIN / relative) == digest for relative, digest in selected.items())
author = read(OUT / 'Authoring/CombinedPrivateAuthoring.json')
assert author['status'] == 'passed' and len(author['montages']) == 8 and len(author['events']) == 401
source = MAIN / 'Scripts/Art/player_attack_vfx_saved_audit.py'
code = source.read_text(encoding='utf-8-sig')
replacements = {
    "EXPECTED_WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')": 'EXPECTED_WORK = MAIN',
    "'PreparedPlaybackPlan.json'": "'CombinedPreparedPlaybackPlan.json'",
    "'Authoring/PrivateAuthoring.json'": "'Authoring/CombinedPrivateAuthoring.json'",
    "len(paths) == 6 and len(PLAN['events']) == 347": "len(paths) == 8 and len(PLAN['events']) == 401",
    'six authored montages and 347 source windows': 'eight authored montages and 401 source windows',
    "REPORT['checked_event_ids'] == 347": "REPORT['checked_event_ids'] == 401",
    "'SavedAssetAuditExports'": "'MainCombinedSavedAssetAuditExports'",
    "'SavedAssetAudit.json'": "'MainCombinedSavedAssetAudit.json'",
    "OUT / 'Authoring' / (name + '_Before.t3d')": "OUT / AUTHOR['before_export_directories'][path] / (name + '_Before.t3d')",
    "OUT / 'Authoring' / (name + '_After.t3d')": "OUT / AUTHOR['before_export_directories'][path] / (name + '_After.t3d')",
    'Only the private AttackVFX Work project is authorized': 'Only a fresh task-owned Main project process is authorized'}
for before, after in replacements.items():
    assert code.count(before) == 1, before
    code = code.replace(before, after)
scope = {'__name__': '__main__', '__file__': str(source)}
exec(compile(code, str(source), 'exec'), scope)
assert all(sha(MAIN / relative) == digest for relative, digest in selected.items())
assert sha(manifest) == delivered['module_manifest_sha256'] and sha(module) == native['sha256']
report_path = OUT / 'MainCombinedSavedAssetAudit.json'
report = read(report_path)
report.update(task_owned_process=True, user_editor_controlled=False,
    delivery_sha256=sha(delivery_path), actual_loaded_module={'path': str(module), 'sha256': sha(module), 'pid': os.getpid()},
    selected_source_assets_unchanged=True, all_original_private_saved_checks_reused=True,
    read_only_main_command_line=unreal.SystemLibrary.get_command_line())
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KZ_PLAYER_ATTACK_VFX_MAIN_COMBINED_SAVED_AUDIT_' + report['status'].upper(), flush=True)
