"""Run only the affected gameplay contracts, with a clean PIE between tests."""
from pathlib import Path
import ctypes,hashlib,json,os,time,traceback
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
assert ROOT in [Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')]
os.environ['KZ_COMBAT_UI_OUTPUT']=str(OUT)
os.environ['KZ_PARRY_OUT']=str(OUT)
tests=['Khazan.Combat.PlayerAttackCollision.PIE','Khazan.Parry.PIE','Khazan.CombatImpact.Plunge.PIE']
module=ROOT/'Binaries/Win64'/json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']
k=ctypes.WinDLL('kernel32');k.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];k.GetModuleHandleW.restype=ctypes.c_void_p
assert k.GetModuleHandleW(module.name)
report={'status':'running','project':str(ROOT),'module':str(module),'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'tests':[]}
u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
LEVEL=u.get_editor_subsystem(u.LevelEditorSubsystem);assert LEVEL.load_level('/Game/Maps/DevMap')
START=time.monotonic();phase=0;index=0;mark=0;requested=False;busy=False;finished=False;changed=START
def finish(error=None):
 global finished
 if finished:return
 finished=True;u.unregister_slate_post_tick_callback(handle);report['status']='failed' if error else 'passed'
 if error:report['error']=error;u.log_error(error)
 (OUT/'Driver.json').write_text(json.dumps(report,indent=2),encoding='utf-8');LEVEL.editor_request_end_play();u.SystemLibrary.quit_editor()
def tick(delta):
 global phase,index,mark,requested,busy,changed
 if busy or finished:return
 busy=True
 try:
  now=time.monotonic()
  if now-START>1000:finish('Owned batch timeout');return
  if now-START<8:return
  log=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
  if phase==0:
   if index==len(tests):finish();return
   if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():LEVEL.editor_request_end_play();return
   mark=len(log);requested=False;u.SystemLibrary.execute_console_command(None,'Automation RunTests '+tests[index]);phase=1;changed=now
  else:
   tail=log[mark:]
   done=[l for l in tail.splitlines() if 'Test Completed' in l and tests[index] in l]
   if done:
    report['tests'].append({'name':tests[index],'result':done[-1]})
    if 'Success' not in done[-1]:finish(done[-1]);return
    LEVEL.editor_request_end_play();index+=1;phase=0;changed=now;return
   if not requested and 'Test Started' in tail and tests[index]!='Khazan.Parry.PIE':
    requested=True;LEVEL.editor_request_begin_play()
 except Exception:finish(traceback.format_exc())
 finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
