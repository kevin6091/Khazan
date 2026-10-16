"""Wait for native Recast completion, then reuse the existing read-only route checks."""
from pathlib import Path
import ast
import datetime
import json
import time
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007'
source=MAIN/'Scripts/HeinMach/build_and_verify_heinmach_playability.py'
tree=ast.parse(source.read_text(encoding='utf-8-sig'))
# Reuse existing functions without its unguarded startup, PIE, editor quit or save.
safe=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign))],type_ignores=[])
namespace=dict(__file__=str(source))
exec(compile(safe,str(source),'exec'),namespace)
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
state=dict(stable=0,next=0,deadline=time.monotonic()+300)
unreal.SystemLibrary.execute_console_command(W,'RebuildNavigation')
def verify_tick(delta):
    if time.monotonic()<state['next']:return
    state['next']=time.monotonic()+.5
    state['stable']=0 if unreal.NavigationSystemV1.is_navigation_being_built_or_locked(W) else state['stable']+1
    if state['stable']<10:
        if time.monotonic()<state['deadline']:return
        unreal.unregister_slate_post_tick_callback(HANDLE)
        raise RuntimeError('Own Recast build did not finish; map not saved as verified')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    report=namespace['verify_original_automation_route'](W)
    report['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT/'NavigationFinal.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['passed'],report
    assert unreal.EditorLoadingAndSavingUtils.save_map(W,'/Game/Maps/L_HeinMach_Environment')
    print('SNOW_RECAST_ROUTES_VERIFIED',report.get('move_to_action_count'),report.get('projected_point_count'),report.get('valid_segment_count'))
HANDLE=unreal.register_slate_post_tick_callback(verify_tick)
print('SNOW_RECAST_WAIT_ARMED')
