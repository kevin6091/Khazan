import os,json
from pathlib import Path
ready=json.loads((ROOT/'Saved/ImportReports/PlayerComboRepair_20261008/Mailbox/Ready.json').read_text())
assert os.getpid() == ready['pid'] == globals().get('EXPECTED_CLOSE_PID',26104)
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
perf=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
perf.set_editor_property('bThrottleCPUWhenNotForeground', ready['throttle'], notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
print('NORMAL_OWNED_EDITOR_EXIT',os.getpid())
console('QUIT_EDITOR')
