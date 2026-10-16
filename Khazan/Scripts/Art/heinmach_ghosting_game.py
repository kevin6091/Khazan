"""Private game mailbox for actual ABP/input/velocity captures; no asset saves."""
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
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert ROOT==MAIN/'Saved/ArtStaging/HeinMachGhosting_20261008'
OUT=MAIN/'Saved/ImportReports/HeinMachGhosting_20261008'
MAIL=OUT/'Mailbox';MAIL.mkdir(parents=True,exist_ok=True)
SESSION=uuid.uuid4().hex;WORLD=None;BUSY=False;NAMESPACE=dict(__name__='ghost_task',unreal=unreal)
START=time.monotonic()

def write(path,data):
    data.update(pid=os.getpid(),session=SESSION,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    path.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8')

def tick(delta):
    global WORLD,BUSY
    if BUSY:return
    BUSY=True
    try:
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            if not WORLD or not unreal.GameplayStatics.get_player_pawn(WORLD,0):WORLD=None;return
            NAMESPACE.update(WORLD=WORLD,OUT=OUT,ROOT=ROOT)
            unreal.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
            write(MAIL/'Ready.json',dict(success=True,world=WORLD.get_path_name()))
        for request in sorted(MAIL.glob('*.request.json')):
            response=request.with_name(request.name.replace('.request.json','.response.json'))
            if response.exists():continue
            output=io.StringIO()
            try:
                job=json.loads(request.read_text(encoding='utf-8'))
                assert job['pid']==os.getpid() and job['session']==SESSION
                with contextlib.redirect_stdout(output):exec(compile(job['script'],str(request),'exec'),NAMESPACE)
                write(response,dict(success=True,output=output.getvalue()))
            except Exception:write(response,dict(success=False,output=output.getvalue(),error=traceback.format_exc()))
        if time.monotonic()-START>2400:unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')
    finally:BUSY=False

HANDLE=unreal.register_slate_post_tick_callback(tick)
