"""Real-RHI mailbox and PIE lifecycle, exclusively in the task-owned snow editor."""
from pathlib import Path
import contextlib
import datetime
import io
import json
import os
import time
import traceback
import uuid
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006')
MAIL=ROOT/'Saved/SnowMailbox';MAIL.mkdir(parents=True,exist_ok=True)
SESSION=uuid.uuid4().hex
PERF=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
THROTTLE=PERF.get_editor_property('bThrottleCPUWhenNotForeground')
PERF.set_editor_property('bThrottleCPUWhenNotForeground',False,
    notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
SEEN=set()
BUSY=False
AUTOMATION_PENDING=None
# QA scheduling only. Three concurrent editors can fall below UE's interactive
# 20-FPS startup gate; this is not a runtime performance acceptance threshold.
TEST_SETTINGS=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.AutomationTestSettings'))
QA_SETTINGS={}
for key in ('DefaultInteractiveFramerate','DefaultInteractiveFramerateDuration'):
    try:
        QA_SETTINGS[key]=TEST_SETTINGS.get_editor_property(key)
        TEST_SETTINGS.set_editor_property(key,1.0)
    except Exception as error:print('QA_SCHEDULING_SETTING_UNAVAILABLE',key,str(error))

def write(path,data):
    data.update(pid=os.getpid(),project=str(ROOT),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8');tmp.replace(path)

def console(command):
    u=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world=u.get_game_world() or u.get_editor_world()
    unreal.SystemLibrary.execute_console_command(
        world,command)

def tick_impl(delta):
    global AUTOMATION_PENDING
    if AUTOMATION_PENDING:
        log=OUT/'verify.log'
        with log.open(encoding='utf-8',errors='replace') as stream:
            stream.seek(AUTOMATION_PENDING['offset']);chunk=stream.read();AUTOMATION_PENDING['offset']=stream.tell()
        if 'Test Started. Name={PIE} Path={Khazan.Snow.PIE}' in chunk:AUTOMATION_PENDING['started']=True
        if AUTOMATION_PENDING['started'] and not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            AUTOMATION_PENDING=None
    for request in sorted(MAIL.glob('*.request.json')):
        response=request.with_name(request.name.replace('.request.json','.response.json'))
        if response.exists():continue
        output=io.StringIO()
        try:
            job=json.loads(request.read_text(encoding='utf-8-sig'))
            assert job['project']==str(ROOT),'Wrong project mailbox'
            assert job.get('editor_pid')==os.getpid() and job.get('session')==SESSION,'Stale editor request; not executed'
            if job['action']=='console':
                if job['command'].startswith('Automation RunTests Khazan.Snow.'):
                    AUTOMATION_PENDING=dict(offset=(OUT/'verify.log').stat().st_size,started=False)
                console(job['command'])
            elif job['action']=='python':
                namespace=dict(__name__='snow_task',__file__=str(request),unreal=unreal)
                with contextlib.redirect_stdout(output):exec(compile(job['script'],str(request),'exec'),namespace)
            elif job['action']=='quit':
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
                PERF.set_editor_property('bThrottleCPUWhenNotForeground',THROTTLE,
                    notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                for key,value in QA_SETTINGS.items():TEST_SETTINGS.set_editor_property(key,value)
                write(response,dict(success=True,throttle_restored=THROTTLE));console('QUIT_EDITOR');return
            else:raise RuntimeError('Unknown action')
            write(response,dict(success=True,output=output.getvalue()))
        except Exception:write(response,dict(success=False,output=output.getvalue(),error=traceback.format_exc()))

def tick(delta):
    global BUSY
    if BUSY:return
    BUSY=True
    try:tick_impl(delta)
    finally:BUSY=False

for request in MAIL.glob('*.request.json'):
    response=request.with_name(request.name.replace('.request.json','.response.json'))
    if not response.exists():write(response,dict(success=False,error='Previous editor session request; not executed'))
HANDLE=unreal.register_slate_post_tick_callback(tick)
write(MAIL/'Ready.json',dict(success=True,original_throttle=THROTTLE,session=SESSION))
print('SNOW_VERIFY_READY',os.getpid())
