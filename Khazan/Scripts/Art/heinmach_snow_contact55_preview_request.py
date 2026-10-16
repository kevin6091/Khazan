from pathlib import Path
import hashlib
import json
import os
import unreal

stage=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007')
assert Path(unreal.Paths.project_dir()).resolve()==stage
ready=json.loads((stage/'Saved/SnowMailbox/Ready.json').read_text())
assert ready['pid']==os.getpid()
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world()
canonical=stage/'Content/Maps/L_HeinMach_Environment.umap'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(canonical)
assert before==json.loads((out/'SavedSettings.json').read_text())['asset_sha256']['Content/Maps/L_HeinMach_Environment.umap']
preview='/Game/Maps/L_HeinMach_Environment_Contact55_20261007'
assert unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(),preview)
assert sha(canonical)==before,'Save As must preserve the validated canonical work copy'
assert len(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())==9869
path=stage/'Content/Maps/L_HeinMach_Environment_Contact55_20261007.umap'
(out/'PreviewMapSaved.json').write_text(json.dumps(dict(success=True,pid=os.getpid(),asset=preview,path=str(path),sha256=sha(path),canonical_sha256=before),indent=2),encoding='utf-8')
print('CONTACT55_PREVIEW_SAVEAS_PASSED',preview)
