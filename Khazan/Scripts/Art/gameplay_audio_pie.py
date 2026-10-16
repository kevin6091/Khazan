"""Owned editor, actual audio mixer, native gameplay notify/cleanup fixture."""
from pathlib import Path
import json
import os
import time
import traceback
import array
import wave
import math
import shutil
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=Path(os.environ['KZ_AUDIO_OUTPUT'])
PLAN=json.loads(Path(os.environ.get('KZ_AUDIO_SAMPLE_PLAN',str(ROOT/'Saved/ImportReports/GameplayAudio_20261011/RuntimeSamples01.json'))).read_text(encoding='utf-8-sig'))
assert Path(u.Paths.project_dir()).resolve()==ROOT.resolve()
REPORT={'status':'running','package_saves':0,'audio_mixer':True,'project':str(ROOT)}
copies=os.environ.get('KZ_AUDIO_BINDING_COPIES')
REPORT['binding_source']='prepared' if copies else 'main'
if copies:u.SystemLibrary.execute_console_command(None,'KZ.Audio.MountBindingCopies "'+copies+'"')
if os.environ.get('KZ_AUDIO_VERBOSE_NOTIFY')=='1':
    u.SystemLibrary.execute_console_command(None,'log LogTemp Verbose')
START=time.monotonic();STARTED=REQUESTED=BUSY=False;DONE_AT=None
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')

def finish(error=None):
    REPORT['status']='failed' if error else 'passed'
    if error:REPORT['error']=error;u.log_error(error)
    (OUT/'Driver.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(HANDLE)
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.SystemLibrary.quit_editor()

def tick(delta):
    global STARTED,REQUESTED,BUSY,DONE_AT
    if BUSY:return
    BUSY=True
    try:
        elapsed=time.monotonic()-START
        if elapsed>PLAN.get('timeout_seconds',120)+120:finish('Actual audio PIE timeout');return
        if elapsed<5:return
        if os.environ.get('KZ_AUDIO_DEBUG_GATE')=='1' and not (OUT/'Continue.txt').exists():return
        if not STARTED:
            u.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
            u.SystemLibrary.execute_console_command(None,'au.UnfocusedVolumeMultiplier 1')
            u.SystemLibrary.execute_console_command(None,'Automation RunTests Khazan.Audio.PIE')
            STARTED=True;return
        log=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
        if 'Test Started' in log and 'Khazan.Audio.PIE' in log and not REQUESTED:
            REQUESTED=True;u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        lines=[x for x in log.splitlines() if 'Test Completed' in x and 'Khazan.Audio.PIE' in x]
        if lines:
            if DONE_AT is None:DONE_AT=time.monotonic();return
            if time.monotonic()-DONE_AT<3:return # finish async WAV export
            REPORT['native_completion']=lines[-1]
            REPORT['observations']=[x for x in log.splitlines() if 'KZAUDIO_ACTUAL' in x]
            REPORT['audio_errors']=[x for x in log.splitlines() if ('LogAudio' in x and 'Error:' in x) or 'SoundNodeRandom' in x and 'Error' in x]
            file=Path(PLAN['output'])/'ActualGameplayAudio.wav'
            with wave.open(str(file)) as f:
                values=array.array('h',f.readframes(f.getnframes()))
                peak=max((abs(x) for x in values),default=0)/32768.
                REPORT['output']={'wave':str(file),'seconds':f.getnframes()/f.getframerate(),'peak':peak,
                    'rms':math.sqrt(sum((x/32768.)**2 for x in values)/max(1,len(values))),
                    'clipped_samples':sum(abs(x)>=32767 for x in values)}
            error=None if 'Success' in lines[-1] and not REPORT['audio_errors'] else lines[-1]
            if peak<=0.:error='Actual captured mixer output is silent'
            if REPORT['output']['clipped_samples']:error='Actual mixed PCM output clips'
            REPORT['family_captures']=[]
            for i,row in enumerate(PLAN['samples']):
                segment=file.parent/(row['family']+'_'+str(i)+'.wav')
                with wave.open(str(segment)) as f:
                    pcm=array.array('h',f.readframes(f.getnframes()))
                    proof={'family':row['family'],'cancel':bool(row.get('cancel')),'wave':str(segment),'seconds':f.getnframes()/f.getframerate(),
                           'peak':max((abs(x) for x in pcm),default=0)/32768.,'clipped_samples':sum(abs(x)>=32767 for x in pcm)}
                REPORT['family_captures'].append(proof)
                if proof['peak']<=0 or proof['clipped_samples']:error='Family actual output silent or clips: '+row['family']
            REPORT['projectile_captures']=[]
            for i,family in enumerate(('ApesStoneHandElite','Yetuga')[:PLAN.get('projectile_count',2)]):
                segment=file.parent/('Projectile_'+str(i)+'.wav')
                with wave.open(str(segment)) as f:
                    pcm=array.array('h',f.readframes(f.getnframes()))
                    proof={'family':family,'wave':str(segment),'seconds':f.getnframes()/f.getframerate(),
                           'peak':max((abs(x) for x in pcm),default=0)/32768.,'clipped_samples':sum(abs(x)>=32767 for x in pcm)}
                REPORT['projectile_captures'].append(proof)
                if proof['peak']<=0 or proof['clipped_samples']:error='Projectile actual output silent or clips: '+family
            # Keep per-run evidence independent of the fixture's shared export path.
            for proof in [REPORT['output']]+REPORT['family_captures']+REPORT['projectile_captures']:
                source=Path(proof['wave']);target=OUT/source.name;shutil.copy2(source,target)
                proof['wave']=str(target)
            if PLAN.get('tail_sound'):
                source=file.parent/'DestroyedOwnerTail.wav';target=OUT/source.name;shutil.copy2(source,target)
                with wave.open(str(target)) as f:
                    pcm=array.array('h',f.readframes(f.getnframes()))
                    # Owner is destroyed after 100ms; use a conservative 350ms
                    # margin for actual GT/audio scheduling before measuring.
                    after=pcm[int(.35*f.getframerate())*f.getnchannels():]
                    REPORT['destroyed_owner_tail']={'wave':str(target),'after_destroy_peak':max((abs(x) for x in after),default=0)/32768.,
                        'seconds':f.getnframes()/f.getframerate(),'clipped_samples':sum(abs(x)>=32767 for x in pcm)}
                if REPORT['destroyed_owner_tail']['after_destroy_peak']<=0:error='Finite source tail is silent after actor destruction'
            finish(error);return
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

HANDLE=u.register_slate_post_tick_callback(tick)
