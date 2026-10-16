"""Real HeinMach ambience/routing captures in an owned, hidden editor. No saves."""
from pathlib import Path
from collections import Counter
import array
import json
import math
import os
import time
import traceback
import wave
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
RUN=Path(os.environ['KZ_AUDIO_OUTPUT']);editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
REPORT={'status':'running','package_saves':0,'captures':[],'errors':[]}
START=time.monotonic();BUSY=False;PHASE=0;INDEX=0;SINCE=0.;WORLD=None;PC=None;SUBMIX=None
SUBMIX=u.EditorAssetLibrary.load_asset('/Game/Audio/Original/Settings/SM_Original');assert SUBMIX
editor.load_level('/Game/Maps/L_HeinMach_Environment')
all_actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
baseline=read(OUT/'EnvironmentAuthor01/BeforeActors.json')
protected={a.get_path_name():{'class':a.get_class().get_name(),'label':a.get_actor_label(),'transform':a.get_actor_transform().export_text()}
           for a in all_actors if 'KZOriginalHeinMachAudio' not in [str(t) for t in a.get_editor_property('tags')]}
assert protected==baseline,'Existing level actors differ from the audio author baseline'
ambient=[a for a in all_actors if isinstance(a,u.AmbientSound) and 'KZOriginalHeinMachAudio' in [str(t) for t in a.get_editor_property('tags')]]
reverb=[a for a in all_actors if isinstance(a,u.AudioVolume) and 'KZOriginalHeinMachAudio' in [str(t) for t in a.get_editor_property('tags')]]
assert len(ambient)==134 and len(reverb)==13,(len(ambient),len(reverb))
assert not any(isinstance(a,u.PostProcessVolume) for a in all_actors)
REPORT['saved_level']={'ambient':len(ambient),'reverb':len(reverb),'protected_actors':len(protected),'postprocess_volumes':0}
source=read(OUT/'EnvironmentAuthoringPlan01.json')['actors']
CASES=[]
for name in ['xxAmb_Heinmach_Forest01_1','xxAmb_Heinmach_Cliff_Upper','xxAmb_Heinmach_Cave01',
             'xxAmb_Heinmach_Forest02','xxsav_heinmach_m_forest02_cave_audio','xxAmb_Heinmach_BossRoom']:
    r=next(r for r in source if r['source_actor']==name)
    CASES.append({'name':name,'location':[r['location'][k] for k in ('X','Y','Z')],
                  'source_aux':r['source_aux_bus'],'source_reverb_enabled':not r['source_reverb_components'] or r['source_reverb_components'][0].get('Properties',{}).get('bEnable',True)})
fire=read(OUT/'EnvironmentAuthor01/Environment.json')['fire'][0]
CASES.append({'name':'PlacedFire','location':fire['location'],'source_aux':'','source_reverb_enabled':False})

def finish(error=None):
    if error:REPORT['errors'].append(error);u.log_error(error)
    REPORT['status']='passed' if not REPORT['errors'] else 'failed'
    (RUN/'EnvironmentPIE.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    if PC:PC.clear_audio_listener_override()
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.AllowBackground restore')
    u.unregister_slate_post_tick_callback(HANDLE);editor.editor_request_end_play();u.SystemLibrary.quit_editor()

def tick(delta):
    global BUSY,PHASE,INDEX,SINCE,WORLD,PC,SUBMIX
    if BUSY:return
    BUSY=True
    try:
        now=time.monotonic()
        if now-START>240:finish('HeinMach mixer fixture timeout');return
        if PHASE==0:
            if now-START<3:return
            u.SystemLibrary.execute_console_command(None,'KZ.Audio.AllowBackground 1')
            editor.editor_request_begin_play();PHASE=1;return
        if PHASE==1:
            WORLD=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if not WORLD:return
            PC=u.GameplayStatics.get_player_controller(WORLD,0)
            if not PC:return
            REPORT['playing_ambient']=sum(a.get_editor_property('audio_component').is_playing() for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.AmbientSound))
            assert REPORT['playing_ambient']>0
            PHASE=2
        if PHASE==2:
            if INDEX>=len(CASES):finish();return
            case=CASES[INDEX];PC.set_audio_listener_override(None,u.Vector(*case['location']),u.Rotator())
            SINCE=now;PHASE=3;return
        if PHASE==3:
            if now-SINCE<2:return # listener/room transition settles, QA margin
            SUBMIX.start_recording_output(WORLD,8.)
            u.SystemLibrary.execute_console_command(None,'KZ.Audio.InspectDevice "'+str(RUN/('Device'+str(INDEX)+'.json'))+'"')
            SINCE=now;PHASE=4;return
        if PHASE==4:
            if now-SINCE<4:return
            SUBMIX.stop_recording_output(WORLD,u.AudioRecordingExportType.WAV_FILE,'Ambient'+str(INDEX),str(RUN))
            SINCE=now;PHASE=5;return
        if PHASE==5:
            file=RUN/('Ambient'+str(INDEX)+'.wav')
            if now-SINCE<2 or not file.exists():return
            with wave.open(str(file)) as f:
                pcm=array.array('h',f.readframes(f.getnframes()))
                result={'case':CASES[INDEX],'seconds':f.getnframes()/f.getframerate(),
                        'peak':max((abs(x) for x in pcm),default=0)/32768.,
                        'rms':math.sqrt(sum((x/32768.)**2 for x in pcm)/max(1,len(pcm))),
                        'clipped_samples':sum(abs(x)>=32767 for x in pcm),'wave':str(file),
                        'device':read(RUN/('Device'+str(INDEX)+'.json'))}
            REPORT['captures'].append(result)
            assert result['peak']>0 and result['clipped_samples']==0,result
            assert not result['device']['muted'] and result['device']['primary_gain']>0,result
            if CASES[INDEX]['source_aux'] and CASES[INDEX]['source_reverb_enabled']:
                assert result['device']['reverb_effect'],result
            INDEX+=1;PHASE=2
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

HANDLE=u.register_slate_post_tick_callback(tick)
