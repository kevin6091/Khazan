"""Existing actual attack/damage/projectile/paired regression, with live mixer proof."""
from pathlib import Path
import array
import json
import math
import os
import time
import traceback
import wave
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
editor=u.get_editor_subsystem(u.LevelEditorSubsystem);editor.load_level('/Game/Maps/DevMap')
TESTS=['Khazan.CombatEffect.PIE','Khazan.Combat.PlayerAttackCollision.PIE','Khazan.GiantFall.PIE','Khazan.Guard.PIE']
if os.environ.get('KZ_AUDIO_REGRESSION_TESTS'):TESTS=json.loads(os.environ['KZ_AUDIO_REGRESSION_TESTS'])
REPORT={'status':'running','package_saves':0,'tests':[],'observed_sounds':[],'errors':[]}
START=time.monotonic();BUSY=False;PHASE=0;INDEX=0;REQUESTED=False;SINCE=0.;NEXT_PROBE=0.;SUBMIX=None;WORLD=None;SEEN=set()
SUBMIX=u.EditorAssetLibrary.load_asset('/Game/Audio/Original/Settings/SM_Original');assert SUBMIX

def finish(error=None):
    if error:REPORT['errors'].append(error);u.log_error(error)
    REPORT['status']='passed' if not REPORT['errors'] else 'failed';REPORT['observed_sounds']=sorted(SEEN)
    (RUN/'Regression.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    if PHASE==3:u.SystemLibrary.execute_console_command(None,'KZ.Audio.Capture stop Interrupted "'+str(RUN)+'"')
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.AllowBackground restore')
    u.unregister_slate_post_tick_callback(HANDLE);editor.editor_request_end_play();u.SystemLibrary.quit_editor()

def tick(delta):
    global BUSY,PHASE,INDEX,REQUESTED,SINCE,NEXT_PROBE,SUBMIX,WORLD
    if BUSY:return
    BUSY=True
    try:
        now=time.monotonic()
        if now-START>660:finish('Actual audio/regression timeout');return
        log=(RUN/'Editor.log').read_text(encoding='utf-8',errors='replace')
        if PHASE==0:
            if now-START<4:return
            u.SystemLibrary.execute_console_command(None,'KZ.Audio.AllowBackground 1')
            u.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
            PHASE=1
        if PHASE==1:
            u.SystemLibrary.execute_console_command(None,'Automation RunTests '+TESTS[INDEX]);PHASE=2;return
        if PHASE==2:
            if not REQUESTED and any('Test Started' in l and TESTS[INDEX] in l for l in log.splitlines()):
                editor.editor_request_begin_play();REQUESTED=True
            WORLD=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if not WORLD:return
            if not u.GameplayStatics.get_player_pawn(WORLD,0):return
            u.SystemLibrary.execute_console_command(None,'KZ.Audio.Capture start Regression'+str(INDEX)+' "'+str(RUN)+'"');PHASE=3;return
        if PHASE==3:
            if now>=NEXT_PROBE:
                live=RUN/'LiveDevice.json'
                if live.exists():
                    try:SEEN.update(json.loads(live.read_text(encoding='utf-8-sig')).get('sound_paths',[]))
                    except json.JSONDecodeError:pass # async writer, retry next tick
                u.SystemLibrary.execute_console_command(None,'KZ.Audio.InspectDevice "'+str(live)+'"');NEXT_PROBE=now+.1
            lines=[l for l in log.splitlines() if 'Test Completed' in l and TESTS[INDEX] in l]
            if not lines:return
            REPORT['tests'].append({'test':TESTS[INDEX],'completion':lines[-1]})
            assert 'Success' in lines[-1],lines[-1]
            u.SystemLibrary.execute_console_command(None,'KZ.Audio.Capture stop Regression'+str(INDEX)+' "'+str(RUN)+'"')
            SINCE=now;PHASE=4;return
        if PHASE==4:
            file=RUN/('Regression'+str(INDEX)+'.wav')
            if now-SINCE<2 or not file.exists():return
            with wave.open(str(file)) as f:
                pcm=array.array('h',f.readframes(f.getnframes()))
                proof={'seconds':f.getnframes()/f.getframerate(),'peak':max((abs(x) for x in pcm),default=0)/32768.,
                       'clipped_samples':sum(abs(x)>=32767 for x in pcm),'wave':str(file)}
            REPORT['tests'][-1]['output']=proof
            assert proof['peak']>0 and proof['clipped_samples']==0,proof
            INDEX+=1
            if INDEX>=len(TESTS):
                assert any('SC_efx_pc_enemy_hit_' in p for p in SEEN),'Accepted body-hit sound not observed in actual audio device'
                finish();return
            # Automation StopTestSession ends PIE. Each subsequent fixture needs
            # its own fresh PIE requested after that test's Started event.
            REQUESTED=False;WORLD=None;PHASE=1
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

HANDLE=u.register_slate_post_tick_callback(tick)
